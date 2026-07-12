#!/usr/bin/env python3
"""Concept2 logbook -> site sync.

Fetches the public logbook (profile 2198296), finds workouts not yet in
sync/results.json, matches each to a rowing day in the plan (index.html),
computes an in/above/below verdict against that day's target band, then
regenerates the RESULTS block baked into index.html.

Runs in GitHub Actions daily (see .github/workflows/c2sync.yml).

Page layout facts (from a live debug run against the real logbook):
  - hero stats are VALUE-then-LABEL   (1,420 / Meters · 15:00.0 / Time · 5:16.9 / Pace · 87 / Calories)
  - detail stats are LABEL-then-VALUE (Average Watts / 11 · Stroke Rate / 10 · Drag Factor / 118)
  - interval workouts have an "Intervals" table; continuous rows have a
    "Splits" table which must NOT be read as work intervals
  - the same calendar day can hold warm-up paddles AND the real workout, so
    candidates are scored per plan day (intervals + band proximity + size)
"""
import json, re, sys, datetime, urllib.request

PROFILE = "2198296"
BASE = f"https://log.concept2.com/profile/{PROFILE}/log"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
ROOT = __file__.rsplit("/", 2)[0]
RESULTS_JSON = f"{ROOT}/sync/results.json"
INDEX = f"{ROOT}/index.html"
MAX_NEW = 15
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
    m = re.match(r"^(\d+):(\d\d(?:\.\d)?)$", str(p).strip())
    return int(m.group(1)) * 60 + float(m.group(2)) if m else None


def fmt_pace(sec):
    m = int(sec // 60)
    s = sec - 60 * m
    return f"{m}:{s:04.1f}"


def time_secs(t):
    parts = [float(x) for x in t.split(":")]
    return sum(x * 60 ** (len(parts) - 1 - i) for i, x in enumerate(parts))


def parse_workout(html):
    lines = strip_tags(html)
    out = {}
    for ln in lines:
        m = re.search(r"\b([A-Z][a-z]{2,8})\.?\s+(\d{1,2}),\s+(20\d\d)\b", ln)
        if m and m.group(1) in MONTHS:
            out["date"] = f"{m.group(3)}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}"
            break

    def stat(label_re, value_re, conv=lambda x: x, valid=lambda v: True):
        # check the line BEFORE the label first (hero stats), then the two after
        for i, ln in enumerate(lines):
            if re.fullmatch(label_re, ln, re.I):
                cands = ([lines[i - 1]] if i else []) + lines[i + 1:i + 3]
                for c in cands:
                    vm = re.fullmatch(value_re, c)
                    if vm:
                        v = conv(vm.group(1))
                        if valid(v):
                            return v
        return None

    out["dist"] = stat(r"Meters", r"([\d,]+)", lambda v: int(v.replace(",", "")), lambda v: v >= 50)
    out["time"] = stat(r"Time", r"((?:\d+:)?\d{1,2}:\d\d(?:\.\d)?)")
    out["pace"] = stat(r"Pace", r"(\d+:\d\d(?:\.\d)?)")
    out["rate"] = stat(r"(?:Average\s+)?Stroke\s*Rate", r"(\d+)", int, lambda v: 10 <= v <= 60)
    out["cal"] = stat(r"Calories", r"([\d,]+)", lambda v: int(v.replace(",", "")))

    # work intervals: only inside the "Intervals" section, never "Splits"
    intervals = []
    if "Intervals" in lines:
        start = lines.index("Intervals") + 1
        end = len(lines)
        for s in ("Splits", "Workout Graph", "Quick Links",
                  "Click on an interval to see the workout graph."):
            if s in lines[start:]:
                end = min(end, lines.index(s, start))
        i = start
        while i <= end - 3:
            t = re.fullmatch(r"((?:\d+:)?\d{1,2}:\d\d\.\d)", lines[i])
            d = re.fullmatch(r"([\d,]+)", lines[i + 1]) if t else None
            p = re.fullmatch(r"(\d+:\d\d\.\d)", lines[i + 2]) if d else None
            if t and d and p and int(d.group(1).replace(",", "")) > 0:
                intervals.append({"time": t.group(1),
                                  "dist": int(d.group(1).replace(",", "")),
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


def work_pace(w):
    """Average pace across work intervals when available (rest excluded)."""
    iv = w.get("intervals") or []
    if len(iv) >= 2:
        tot_t = sum(time_secs(x["time"]) for x in iv)
        tot_d = sum(x["dist"] for x in iv)
        if tot_d:
            return fmt_pace(tot_t / tot_d * 500), len(iv)
    return w.get("pace"), 0


def band_ends(band):
    bm = re.findall(r"(\d+:\d\d(?:\.\d)?)", band or "")
    if len(bm) >= 2:
        return tuple(sorted(pace_secs(x) for x in bm[:2]))
    return None


def score(w, band):
    """Rank same-day candidates: real workouts beat warm-up paddles."""
    s = 0.0
    if len(w.get("intervals") or []) >= 2:
        s += 4
    wp, _ = work_pace(w)
    ends, ps = band_ends(band), pace_secs(wp) if wp else None
    if ends and ps is not None:
        fast, slow = ends
        if fast - 10 <= ps <= slow + 10:
            s += 3
    s += min(w.get("dist") or 0, 20000) / 20000.0
    return s


def main():
    results = json.load(open(RESULTS_JSON))
    used_ids = {v["id"] for v in results.values()}
    index = open(INDEX).read()

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

    # gather all parseable candidates first
    workouts = []
    for wid in ids[:MAX_NEW]:
        url = f"{BASE}/{wid}"
        try:
            status, page = fetch(url)
        except Exception as e:
            print(f"  {wid}: fetch failed: {e}")
            continue
        w = parse_workout(page)
        if not w.get("date") or not w.get("dist") or not w.get("time"):
            print(f"  {wid}: incomplete parse (date={w.get('date')}, dist={w.get('dist')}, time={w.get('time')}) — skipping")
            continue
        w["id"], w["url"] = wid, url
        workouts.append(w)
        print(f"  parsed {wid}: {w['date']} {w['dist']}m {w['time']} intervals={len(w.get('intervals') or [])}")

    # candidate (plan_date, workout) pairs: exact date first, then ±1 day
    cands = []
    for w in workouts:
        d = datetime.date.fromisoformat(w["date"])
        for rank, pd in enumerate([w["date"],
                                   (d + datetime.timedelta(days=1)).isoformat(),
                                   (d - datetime.timedelta(days=1)).isoformat()]):
            if pd in bands and pd not in results:
                cands.append((pd, rank, -score(w, bands[pd]), w))
    cands.sort(key=lambda c: (c[0], c[1], c[2]))

    added, taken = 0, set()
    for pd, rank, negs, w in cands:
        if pd in results or w["id"] in taken:
            continue
        band = bands[pd]
        wp, n_iv = work_pace(w)
        verdict, vtxt = "na", "logged"
        ends, ps = band_ends(band), pace_secs(wp) if wp else None
        if ends and ps is not None:
            fast, slow = ends
            if ps < fast - 0.5:
                verdict, vtxt = "above", "faster than target (above zone)"
            elif ps > slow + 0.5:
                verdict, vtxt = "below", "slower than target (below zone)"
            else:
                verdict, vtxt = "in", "in zone"
        d = datetime.date.fromisoformat(w["date"])
        late = "" if pd == w["date"] else f" (logged {d.strftime('%b %-d')})"
        rate_txt = f" Rate {w['rate']} s/m." if w.get("rate") else ""
        if n_iv:
            note = (f"{n_iv} work intervals{late} — avg work pace {wp} /500m vs "
                    f"{band} target: {vtxt}.{rate_txt}")
        else:
            note = (f"{w['dist']:,}m in {w['time']}{late} — avg {wp or '—'} /500m vs "
                    f"{band} target: {vtxt}.{rate_txt}")
        results[pd] = {
            "id": w["id"], "link": w["url"], "dist": w["dist"], "time": w["time"] or "",
            "pace": wp or w.get("pace") or "", "rate": w.get("rate") or 0,
            "band": band, "verdict": verdict, "note": note,
        }
        taken.add(w["id"])
        print(f"  + {pd}: id {w['id']}, {w['dist']}m, pace {wp}, verdict {verdict}")
        added += 1

    unmatched = [w["id"] for w in workouts if w["id"] not in taken]
    if unmatched:
        print("not matched to any open plan day (warm-ups / extras):", unmatched)
    if not added:
        print("Nothing new to sync.")
        return

    json.dump(dict(sorted(results.items())), open(RESULTS_JSON, "w"),
              ensure_ascii=False, indent=1)

    def js_str(s):
        return '"' + str(s or "").replace("\\", "\\\\").replace('"', '\\"') + '"'
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
