#!/usr/bin/env python3
"""Concept2 stroke data -> sync/strokes/ (runs in GitHub Actions, no local machine).

For every workout in sync/results.json that has no sync/strokes/<id>.json yet,
pulls the result detail and the stroke-by-stroke data from the Concept2
logbook API and writes one file per workout. Also backfills the per-interval
rows in sync/intervals.json and the pillar in sync/pillars.json for any day
the page scrape missed.

Auth: a Concept2 logbook API token in the C2_TOKEN environment variable
(repo secret C2_TOKEN). Missing token -> warning, exit 0 (the results sync
still runs). Rejected token -> exit 1, so the workflow goes red and GitHub
emails you.

Stroke units from the API: t = tenths of a second, d = tenths of a metre,
p = tenths of a second per 500 m. In interval workouts t and d restart at
each interval, which is how strokes are split into work intervals here.

Output, sync/strokes/<id>.json:
  {id, date, drag, spm, hr_avg, intervals: [[dist, pace_s, watts, spm, hr], ...],
   segments: [{n, strokes, dist, secs, pace_s, watts, spm, m_per_stroke, hr}],
   strokes: [[t_s, d_m, pace_s, watts, spm, hr], ...]}
plus sync/strokes/index.json mapping date -> workout id.
"""
import json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC = os.path.join(ROOT, "sync")
STROKES = os.path.join(SYNC, "strokes")
API = "https://log.concept2.com/api"
MAX_PER_RUN = 60          # first run backfills the whole block; later runs fetch 1-2
TOKEN = os.environ.get("C2_TOKEN", "").strip()


class Rejected(Exception):
    pass


def get(path):
    req = urllib.request.Request(API + path, headers={
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/vnd.c2logbook.v1+json",
        "User-Agent": "rowing-plan-sync/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise Rejected(f"HTTP {e.code} on {path}")
        if e.code == 404:
            return None
        raise


def watts(pace_s):
    return round(2.8 / (pace_s / 500.0) ** 3) if pace_s and pace_s > 0 else 0


def load(name, default):
    try:
        with open(os.path.join(SYNC, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def interval_rows(detail):
    """[distance, pace seconds, watts, stroke rate, heart rate] per work interval,
    the same shape the page scrape writes to intervals.json."""
    rows = []
    for iv in ((detail.get("workout") or {}).get("intervals") or []):
        dist, t = iv.get("distance") or 0, (iv.get("time") or 0) / 10.0
        if dist <= 0 or t <= 0:
            continue
        pace = round(t * 500.0 / dist, 1)
        hr = (iv.get("heart_rate") or {}).get("average") or 0
        rows.append([dist, pace, watts(pace), iv.get("stroke_rate") or 0, hr])
    return rows


def segments(strokes):
    """Split strokes wherever time or distance restarts (a new interval)."""
    segs, cur, prev = [], [], None
    for s in strokes:
        if prev and (s["t"] < prev["t"] or s["d"] < prev["d"]):
            segs.append(cur)
            cur = []
        cur.append(s)
        prev = s
    if cur:
        segs.append(cur)
    out = []
    for i, seg in enumerate(segs, 1):
        dist = seg[-1]["d"] / 10.0
        secs = seg[-1]["t"] / 10.0
        if dist <= 0 or secs <= 0:
            continue
        pace = round(secs * 500.0 / dist, 1)
        spms = [s.get("spm") or 0 for s in seg if s.get("spm")]
        hrs = [s.get("hr") or 0 for s in seg if s.get("hr")]
        out.append({
            "n": i, "strokes": len(seg), "dist": round(dist, 1), "secs": round(secs, 1),
            "pace_s": pace, "watts": watts(pace),
            "spm": round(sum(spms) / len(spms), 1) if spms else 0,
            "m_per_stroke": round(dist / len(seg), 2),
            "hr": round(sum(hrs) / len(hrs)) if hrs else 0})
    return out


def build(wid, date, detail, strokes):
    rows = []
    for s in strokes:
        p = (s.get("p") or 0) / 10.0
        rows.append([round((s.get("t") or 0) / 10.0, 1), round((s.get("d") or 0) / 10.0, 1),
                     p, watts(p), s.get("spm") or 0, s.get("hr") or 0])
    hr = (detail.get("heart_rate") or {}).get("average") or 0
    return {"id": wid, "date": date, "drag": detail.get("drag_factor"),
            "spm": detail.get("stroke_rate"), "hr_avg": hr,
            "intervals": interval_rows(detail), "segments": segments(strokes),
            "strokes": rows}


def main():
    if not TOKEN:
        print("::warning::C2_TOKEN secret not set - stroke data skipped. "
              "Add it under Settings > Secrets and variables > Actions.")
        return 0
    try:
        me = get("/users/me")
    except Rejected as e:
        print(f"::error::Concept2 rejected C2_TOKEN ({e}). Issue a new token and update the repo secret.")
        return 1
    print("Concept2 token OK for", ((me or {}).get("data") or {}).get("username", "?"))

    os.makedirs(STROKES, exist_ok=True)
    results = load("results.json", {})
    results = results.get("results", results)
    intervals = load("intervals.json", {})
    pillars = load("pillars.json", {})
    index = load("strokes/index.json", {})
    block = {}
    try:
        with open(os.path.join(ROOT, "block-plan.json"), encoding="utf-8") as f:
            block = json.load(f)
    except (OSError, ValueError):
        pass
    sys.path.insert(0, SYNC)
    from sync_c2 import pillar_of

    fetched = 0
    for date, v in sorted(results.items(), reverse=True):    # newest first
        wid = str(v.get("id") or "")
        path = os.path.join(STROKES, f"{wid}.json")
        if not wid or os.path.exists(path):
            index.setdefault(date, wid) if wid else None
            continue
        if fetched >= MAX_PER_RUN:
            break
        try:
            detail = (get(f"/users/me/results/{wid}") or {}).get("data")
            if not detail:
                print(f"  {date} {wid}: not found in API, skipped")
                continue
            strokes = (get(f"/users/me/results/{wid}/strokes") or {}).get("data") or []
        except Rejected as e:
            print(f"::error::Concept2 rejected the token mid-run ({e}).")
            return 1
        doc = build(wid, date, detail, strokes)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, separators=(",", ":"))
        index[date] = wid
        if doc["intervals"] and not intervals.get(date):
            intervals[date] = doc["intervals"]
        if not pillars.get(date):
            work = doc["intervals"] or [[0, None]]
            paces = [r[1] for r in work if r[1]]
            day = block.get(date) or {}
            pil = pillar_of(day.get("title"), sum(paces) / len(paces) if paces else None,
                            day.get("pillar"))
            if pil:
                pillars[date] = pil
        fetched += 1
        print(f"  + {date} {wid}: {len(strokes)} strokes, {len(doc['segments'])} segments")
        time.sleep(0.5)

    for name, data in (("intervals.json", intervals), ("pillars.json", pillars)):
        with open(os.path.join(SYNC, name), "w", encoding="utf-8") as f:
            json.dump(dict(sorted(data.items())), f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(STROKES, "index.json"), "w", encoding="utf-8") as f:
        json.dump(dict(sorted(index.items())), f, indent=1)
    print(f"Fetched stroke data for {fetched} workout(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
