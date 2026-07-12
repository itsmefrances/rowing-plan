#!/usr/bin/env python3
"""Concept2 logbook -> site sync.

Fetches the public logbook (profile 2198296), finds workouts not yet in
sync/results.json, matches each to a rowing day in the plan (index.html),
computes an in/above/below verdict against that day's target band, then
regenerates the RESULTS block baked into index.html.

Runs in GitHub Actions daily (see .github/workflows/c2sync.yml).
"""
import json, re, sys, datetime, urllib.request

PROFILE = "2198296"
BASE = f"https://log.concept2.com/profile/{PROFILE}/log"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
ROOT = __file__.rsplit("/", 2)[0]
RESULTS_JSON = f"{ROOT}/sync/results.json"
INDEX = f"{ROOT}/index.html"
MAX_NEW = 12
DEBUG = "--debug" in sys.argv

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}
MONTHS.update({m[:3]: v for m, v in list(MONTHS.items())})


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


def strip_tags(html):
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#039;", "'")
    return [ln.strip() for ln in text.split("\n") if ln.strip()]


def pace_secs(p):
    m = re.match(r"^(\d+):(\d\d(?:\.\d)?)$", p.strip())
    return int(m.group(1)) * 60 + float(m.group(2)) if m else None


def fmt_pace(sec):
    m = int(sec // 60)
    s = sec - 60 * m
    return f"{m}:{s:04.1f}"


def parse_workout(html):
    """Extract date/dist/time/pace/rate/cal + intervals from a workout page."""
    lines = strip_tags(html)
    out = {}
    # date: first "Month D, YYYY"
    for ln in lines:
        m = re.search(r"\b([A-Z][a-z]{2,8})\.?\s+(\d{1,2}),\s+(20\d\d)\b", ln)
        if m and m.group(1) in MONTHS:
            out["date"] = f"{m.group(3)}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}"
            break
    # labeled stats: value usually on the line after (or same line as) its label
    def labeled(label_re, value_re, conv=lambda x: x):
        for i, ln in enumerate(lines):
            if re.fullmatch(label_re, ln, re.I):
                for j in range(i + 1, min(i + 4, len(lines))):
                    vm = re.fullmatch(value_re, lines[j])
                    if vm:
                        return conv(vm.group(1))
            m = re.fullmatch(label_re + r"[:\s]+" + value_re, ln, re.I)
            if m:
                return conv(m.group(1))
        return None

    out["dist"] = labeled(r"(?:Total\s+)?(?:Distance|Meters)", r"([\d,]+)\s*m?", lambda v: int(v.replace(",", "")))
    out["time"] = labeled(r"(?:Total\s+)?(?:Work\s+)?Time", r"((?:\d+:)?\d{1,2}:\d\d(?:\.\d)?)")
    out["pace"] = labeled(r"(?:Average\s+)?Pace(?:\s*/500m?)?", r"(\d+:\d\d(?:\.\d)?)")
    out["rate"] = labeled(r"(?:Average\s+)?(?:Stroke\s+Rate|SPM|s/m)", r"(\d+)", int)
    out["cal"] = labeled(r"Calories(?:\s+Burned)?", r"([\d,]+)", lambda v: int(v.replace(",", "")))
    # interval rows: sequences like  time / meters / pace / (watts/cal) / rate
    intervals = []
    i = 0
    while i <= len(lines) - 3:
        t = re.fullmatch(r"((?:\d+:)?\d{1,2}:\d\d\.\d)", lines[i])
        d = re.fullmatch(r"([\d,]+)", lines[i + 1]) if t else None
        p = re.fullmatch(r"(\d+:\d\d\.\d)", lines[i + 2]) if d else None
        if t and d and p:
            intervals.append({"time": t.group(1), "dist": int(d.group(1).replace(",", "")),
                              "pace": p.group(1)})
            i += 3
        else:
            i += 1
    if intervals:
        out["intervals"] = intervals
    if DEBUG:
        print("---- page text (first 160 lines) ----")
        for ln in lines[:160]:
            print("  |", ln)
        print("---- parsed:", {k: v for k, v in out.items() if k != "intervals"},
              "intervals:", len(intervals))
    return out


def time_secs(t):
    parts = t.split(":")
    parts = [float(x) for x in parts]
    return sum(x * 60 ** (len(parts) - 1 - i) for i, x in enumerate(parts))


def work_pace(w):
    """Average pace across work intervals when available (rest excluded)."""
    iv = w.get("intervals") or []
    iv = [x for x in iv if x["dist"] > 0]
    # heuristic: interval workouts repeat similar distances; drop rest rows
    # (rest rows on C2 pages usually show as separate small-meter rows; the
    #  3-line matcher above only catches rows with all three fields anyway)
    if len(iv) >= 2:
        tot_t = sum(time_secs(x["time"]) for x in iv)
        tot_d = sum(x["dist"] for x in iv)
        if tot_d:
            return fmt_pace(tot_t / tot_d * 500), len(iv)
    return w.get("pace"), 0


def main():
    results = json.load(open(RESULTS_JSON))
    used_ids = {v["id"] for v in results.values()}
    index = open(INDEX).read()

    # plan rowing days: date -> target band
    bands = dict(re.findall(
        r'\{"date":"(\d{4}-\d\d-\d\d)","dow":"[^"]+","type":"[^"]+","title":"[^"]*","items":\[\{"t":"row"[^}]*?"pace":"([^"]+)"',
        index))
    print(f"plan rowing days: {len(bands)}  |  existing results: {len(results)}")

    status, listing = fetch(BASE)
    print("list page HTTP", status, "bytes", len(listing))
    ids = []
    for m in re.finditer(rf"/profile/{PROFILE}/log/(\d+)", listing):
        wid = int(m.group(1))
        if wid not in used_ids and wid not in ids:
            ids.append(wid)
    print("unseen workout ids:", ids[:MAX_NEW])

    added = 0
    for wid in ids[:MAX_NEW]:
        url = f"{BASE}/{wid}"
        try:
            status, page = fetch(url)
        except Exception as e:
            print(f"  {wid}: fetch failed: {e}")
            continue
        w = parse_workout(page)
        if not w.get("date") or not w.get("dist"):
            print(f"  {wid}: could not parse (date={w.get('date')}, dist={w.get('dist')}) — skipping")
            continue
        d = datetime.date.fromisoformat(w["date"])
        cand = [w["date"],
                (d + datetime.timedelta(days=1)).isoformat(),
                (d - datetime.timedelta(days=1)).isoformat()]
        plan_date = next((c for c in cand if c in bands and c not in results), None)
        if not plan_date:
            print(f"  {wid}: {w['date']} {w['dist']}m — no unmatched plan rowing day nearby, skipping")
            continue
        band = bands[plan_date]
        wp, n_iv = work_pace(w)
        verdict, vtxt = "na", "logged"
        bm = re.findall(r"(\d+:\d\d(?:\.\d)?)", band)
        ps = pace_secs(wp) if wp else None
        if len(bm) >= 2 and ps:
            fast, slow = sorted(pace_secs(x) for x in bm[:2])
            if ps < fast - 0.5:
                verdict, vtxt = "above", "faster than target (above zone)"
            elif ps > slow + 0.5:
                verdict, vtxt = "below", "slower than target (below zone)"
            else:
                verdict, vtxt = "in", "in zone"
        late = "" if plan_date == w["date"] else f" (logged {d.strftime('%b %-d')})"
        if n_iv:
            note = (f"{n_iv} work intervals{late} — avg work pace {wp} /500m vs "
                    f"{band} target: {vtxt}." + (f" Rate {w['rate']} s/m." if w.get("rate") else ""))
        else:
            note = (f"{w['dist']:,}m in {w.get('time','—')}{late} — avg {wp or '—'} /500m vs "
                    f"{band} target: {vtxt}." + (f" Rate {w['rate']} s/m." if w.get("rate") else ""))
        results[plan_date] = {
            "id": wid, "link": url, "dist": w["dist"], "time": w.get("time", ""),
            "pace": wp or w.get("pace", ""), "rate": w.get("rate", 0),
            "band": band, "verdict": verdict, "note": note,
        }
        print(f"  + {plan_date}: id {wid}, {w['dist']}m, pace {wp}, verdict {verdict}")
        added += 1

    if not added:
        print("Nothing new to sync.")
        return

    json.dump(dict(sorted(results.items())), open(RESULTS_JSON, "w"),
              ensure_ascii=False, indent=1)

    def js_str(s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    entries = []
    for date, v in sorted(results.items()):
        entries.append(
            f'  "{date}": {{id:{v["id"]}, link:{js_str(v["link"])},\n'
            f'    dist:{v["dist"]}, time:{js_str(v["time"])}, pace:{js_str(v["pace"])}, rate:{v["rate"]},\n'
            f'    band:{js_str(v["band"])}, verdict:{js_str(v["verdict"])}, note:{js_str(v["note"])}}}')
    block = "const RESULTS = {\n" + ",\n".join(entries) + "\n};"
    index = re.sub(r"const RESULTS = \{.*?\n\};", lambda _: block, index, count=1, flags=re.S)
    today = datetime.date.today().isoformat()
    index = re.sub(r"/\* Updated: \d{4}-\d\d-\d\d \*/", f"/* Updated: {today} */", index, count=1)
    open(INDEX, "w").write(index)
    print(f"Baked {added} new result(s) into index.html ({len(results)} total).")


if __name__ == "__main__":
    main()
