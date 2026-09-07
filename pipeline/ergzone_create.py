#!/usr/bin/env python3
"""Create / re-date the Rowfit block's ErgZone workouts through the admin API.

The plan lives in ergzone_plan.json. Each entry may carry a "wid" (the id of the
workout already in the track) and "skip": true (never touch it - Frances has
logged results against it).

  --probe    connection check + one payload
  --index    list what the track returns (only the most recent 15 come back)
  --find     hunt for a query shape that returns ALL the track's workouts
  --dry      list what --apply would create
  --apply    create the entries that have no wid and are not already in the track
  --redate   re-send the full payload for every entry that has a wid, so the
             workout's date (and intervals, pace, description) match the plan.
             Aborts the moment the API hands back an id other than the one sent,
             because that would mean it created a copy instead of updating.
"""
import json, os, sys, urllib.request, urllib.error

API = "https://production.erg.zone/api"
TRACK = "68afa180-10d1-4ca1-8d3a-dff940e147b2"
ROOT = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.join(ROOT, "ergzone_plan.json")

CRED = os.environ.get("ERGZONE_TOKEN", "").strip()
if not CRED:
    sys.exit("ERGZONE_TOKEN is not set")

CREATE = """mutation CreateWorkout($workout: WorkoutInput!) {
  workout: workoutUpsert(workout: $workout) { id title publishedAt }
}"""

PREFIX = None


def call(query, variables=None, prefix=None):
    if prefix is None:
        prefix = PREFIX if PREFIX is not None else "Bearer "
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    hdr = {"content-type": "application/json", "authorization": prefix + CRED}
    req = urllib.request.Request(API, data=body, headers=hdr)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:400]}


def pick_prefix():
    """The admin sends either 'Bearer <value>' or the bare value; find which."""
    global PREFIX
    q = "query T($id: ID!){ track(id:$id){ id name } }"
    for p in ("Bearer ", ""):
        r = call(q, {"id": TRACK}, prefix=p)
        if r.get("data") and r["data"].get("track"):
            PREFIX = p
            return r["data"]["track"].get("name") or "ok"
    return None


def track_workouts():
    q = "query T($id: ID!){ track(id:$id){ workouts { id title publishedAt } } }"
    r = call(q, {"id": TRACK})
    if not r.get("data") or not r["data"].get("track"):
        print("  could not list track workouts:", json.dumps(r)[:400])
        return None
    return r["data"]["track"].get("workouts") or []


def existing():
    ws = track_workouts()
    if ws is None:
        return None
    return set(((w.get("publishedAt") or "")[:10], (w.get("title") or "").strip()) for w in ws)


def find():
    """The plain workouts field caps at 15. Try to find one that doesn't."""
    shapes = [
        ("workouts(first:200)", 'query T($id: ID!){ track(id:$id){ workouts(first:200){ id title publishedAt } } }'),
        ("workouts(limit:200)", 'query T($id: ID!){ track(id:$id){ workouts(limit:200){ id title publishedAt } } }'),
        ("workouts(offset:15)", 'query T($id: ID!){ track(id:$id){ workouts(offset:15){ id title publishedAt } } }'),
        ("workouts(skip:15)", 'query T($id: ID!){ track(id:$id){ workouts(skip:15){ id title publishedAt } } }'),
        ("workouts(page:2)", 'query T($id: ID!){ track(id:$id){ workouts(page:2){ id title publishedAt } } }'),
        ("workouts(count:200)", 'query T($id: ID!){ track(id:$id){ workouts(count:200){ id title publishedAt } } }'),
        ("workouts(startDate,endDate)", 'query T($id: ID!){ track(id:$id){ workouts(startDate:"2026-09-01", endDate:"2026-10-05"){ id title publishedAt } } }'),
        ("workouts(from,to)", 'query T($id: ID!){ track(id:$id){ workouts(from:"2026-09-01", to:"2026-10-05"){ id title publishedAt } } }'),
        ("workouts(before)", 'query T($id: ID!){ track(id:$id){ workouts(before:"2026-10-05"){ id title publishedAt } } }'),
        ("track.allWorkouts", 'query T($id: ID!){ track(id:$id){ allWorkouts { id title publishedAt } } }'),
        ("track.workoutCount", 'query T($id: ID!){ track(id:$id){ workoutCount } }'),
        ("trackWorkouts(trackId)", 'query T($id: ID!){ trackWorkouts(trackId:$id){ id title publishedAt } }'),
        ("workouts(trackId)", 'query T($id: ID!){ workouts(trackId:$id){ id title publishedAt } }'),
        ("workoutsConnection", 'query T($id: ID!){ track(id:$id){ workoutsConnection(first:200){ edges { node { id title publishedAt } } } } }'),
    ]
    for name, q in shapes:
        r = call(q, {"id": TRACK})
        if r.get("errors"):
            print("  x %-28s %s" % (name, r["errors"][0].get("message", "")[:150]))
            continue
        if r.get("http_error"):
            print("  x %-28s HTTP %s" % (name, r["http_error"]))
            continue
        d = r.get("data") or {}
        blob = json.dumps(d, ensure_ascii=False)
        n = blob.count('"id"')
        print("  OK %-28s ids=%d  %s" % (name, n, blob[:200]))


def expand(p):
    """groups -> one entry per rep; the final rep always has undefined rest."""
    ivs = []
    for g in p["groups"]:
        for _ in range(g["count"]):
            d = {"type": g["type"], "value": g["value"]}
            if g.get("rest") is not None:
                d["rest"] = g["rest"]
            for k in ("spm", "spmMax", "notes"):
                if g.get(k) is not None:
                    d[k] = g[k]
            ivs.append(d)
    if ivs:
        ivs[-1].pop("rest", None)
        ivs[-1]["undefRest"] = True
    return ivs


def payload(p, with_id=False):
    ivs = expand(p)
    for d in ivs:
        if p.get("offset") is not None:
            # values copied off a workout built by hand in the admin UI:
            # benchmark group "D" (the 500m distance benchmark), operator "+",
            # and the offset in seconds. suggestedInterval stays unset.
            d["suggestedPace"] = p["offset"]
            d["suggestedOperator"] = "+"
            d["suggestedPaceBenchmarkGroup"] = "D"
    w = {"trackId": TRACK, "title": p["title"], "description": p["description"],
         "workoutType": "row", "status": "published", "hasLeaderboard": True,
         "publishedAt": p["date"], "intervals": ivs}
    if with_id and p.get("wid"):
        w["id"] = p["wid"]
    return w


def redate(plan):
    todo = [p for p in plan if p.get("wid") and not p.get("skip")]
    print("re-dating %d workout(s); %d skipped, %d have no id yet"
          % (len(todo), sum(1 for p in plan if p.get("skip")),
             sum(1 for p in plan if not p.get("wid"))))
    ok = 0
    for p in todo:
        r = call(CREATE, {"workout": payload(p, with_id=True)})
        w = (r.get("data") or {}).get("workout")
        if not w:
            print("  ! %s  %s  -> %s" % (p["date"], p["title"], json.dumps(r)[:400]))
            print("stopping"); sys.exit(1)
        if w["id"] != p["wid"]:
            print("  !! %s  %s  sent id %s but got back %s"
                  % (p["date"], p["title"], p["wid"], w["id"]))
            print("the API created a copy instead of updating - STOPPING NOW."
                  " one stray workout to clean up, no more.")
            sys.exit(1)
        print("  = %s  %s  -> %s" % ((w.get("publishedAt") or "?")[:10], p["title"], w["id"]))
        ok += 1
    print("re-dated %d workout(s)" % ok)


def main():
    plan = json.load(open(PLAN, encoding="utf-8"))
    mode = "probe"
    for m in ("dry", "apply", "index", "find", "redate"):
        if "--" + m in sys.argv:
            mode = m

    who = pick_prefix()
    print("track:", who or "NOT REACHED - value rejected or query shape wrong")
    if not who:
        print(json.dumps(call("query T($id: ID!){ track(id:$id){ id } }", {"id": TRACK}))[:400])
        sys.exit(1)

    if mode == "find":
        find()
        return

    if mode == "redate":
        redate(plan)
        return

    have = existing() or set()
    print("workouts the track returns:", len(have))
    # only entries with no id of their own are candidates for creation, and the
    # (date, title) check is a second guard - the track listing is capped at 15
    # so it cannot be trusted on its own.
    todo = [p for p in plan if not p.get("wid") and (p["date"], p["title"]) not in have]
    print("plan: %d total, %d without an id, %d to create"
          % (len(plan), sum(1 for p in plan if not p.get("wid")), len(todo)))

    if mode == "index":
        q = ("query T($id: ID!){ track(id:$id){ workouts { id title publishedAt "
             "lookupKey intervalsLength } } }")
        r = call(q, {"id": TRACK})
        ws = sorted((r.get("data", {}).get("track", {}) or {}).get("workouts") or [],
                    key=lambda w: ((w.get("publishedAt") or ""), w.get("title") or ""))
        for w in ws:
            print("%s | %s | %s | %s | %s" % ((w.get("publishedAt") or "")[:10], w.get("title"),
                                              w.get("lookupKey"), w.get("intervalsLength"), w.get("id")))
        print("total", len(ws))
        return

    if mode == "probe":
        q = ("query T($id: ID!){ track(id:$id){ workouts { id title publishedAt "
             "intervals { type value rest undefRest spm spmMax suggestedPace "
             "suggestedPaceBenchmarkGroup suggestedOperator suggestedInterval } } } }")
        r = call(q, {"id": TRACK})
        for w in (r.get("data", {}).get("track", {}) or {}).get("workouts") or []:
            ivs = w.get("intervals") or []
            if ivs and ivs[0].get("suggestedPace") is not None:
                print("reference workout:", w["title"], w.get("publishedAt"))
                print(json.dumps(ivs[0], indent=1, ensure_ascii=False))
                break
        else:
            print("no existing workout carries a suggested pace")
        print(json.dumps(payload(todo[0]) if todo else {}, indent=1, ensure_ascii=False)[:600])
        return

    if mode == "dry":
        for p in todo:
            print("  would create %s  %s  (%d intervals)"
                  % (p["date"], p["title"], sum(g["count"] for g in p["groups"])))
        return

    made = 0
    for p in todo:
        r = call(CREATE, {"workout": payload(p)})
        if r.get("data") and r["data"].get("workout"):
            print("  + %s  %s  -> %s" % (p["date"], p["title"], r["data"]["workout"]["id"]))
            made += 1
        else:
            print("  ! %s  %s  -> %s" % (p["date"], p["title"], json.dumps(r)[:500]))
            if made == 0:
                print("first create failed; stopping so the payload can be fixed")
                sys.exit(1)
    print("created %d workout(s)" % made)


if __name__ == "__main__":
    main()
