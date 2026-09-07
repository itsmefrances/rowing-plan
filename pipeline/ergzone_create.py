#!/usr/bin/env python3
"""Create the Rowfit block's ErgZone workouts through the admin GraphQL API.

Reads the plan from ergzone_plan.json and calls workoutUpsert once per workout.
Idempotent: a workout whose (date, title) already exists in the track is skipped,
so this can be re-run safely after a partial failure.

  python pipeline/ergzone_create.py --probe   # connection check + one payload
  python pipeline/ergzone_create.py --dry     # list what would be created
  python pipeline/ergzone_create.py --apply   # create the missing workouts
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
  workout: workoutUpsert(workout: $workout) { id title }
}"""

PREFIX = None


def call(query, variables=None, prefix="Bearer "):
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


def existing():
    q = "query T($id: ID!){ track(id:$id){ workouts { id title publishedAt } } }"
    r = call(q, {"id": TRACK}, prefix=PREFIX)
    if not r.get("data") or not r["data"].get("track"):
        print("  could not list track workouts:", json.dumps(r)[:400])
        return None
    out = set()
    for w in r["data"]["track"].get("workouts") or []:
        out.add(((w.get("publishedAt") or "")[:10], (w.get("title") or "").strip()))
    return out


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


def payload(p):
    ivs = expand(p)
    for d in ivs:
        if p.get("offset") is not None:
            d["suggestedPace"] = p["offset"]
            d["suggestedInterval"] = 500
            d["suggestedOperator"] = "pace"
            d["suggestedPaceBenchmarkGroup"] = "row"
    return {"trackId": TRACK, "title": p["title"], "description": p["description"],
            "workoutType": "row", "status": "published", "hasLeaderboard": True,
            "publishedAt": p["date"], "intervals": ivs}


def main():
    plan = json.load(open(PLAN, encoding="utf-8"))
    mode = "probe"
    if "--dry" in sys.argv:
        mode = "dry"
    if "--apply" in sys.argv:
        mode = "apply"

    who = pick_prefix()
    print("track:", who or "NOT REACHED - value rejected or query shape wrong")
    if not who:
        print(json.dumps(call("query T($id: ID!){ track(id:$id){ id } }", {"id": TRACK}))[:400])
        sys.exit(1)

    have = existing() or set()
    print("workouts already in track:", len(have))
    todo = [p for p in plan if (p["date"], p["title"]) not in have]
    print("plan: %d total, %d to create" % (len(plan), len(todo)))

    if mode == "probe":
        print(json.dumps(payload(todo[0]) if todo else {}, indent=1, ensure_ascii=False)[:1400])
        return
    if mode == "dry":
        for p in todo:
            print("  would create %s  %s  (%d intervals)" % (p["date"], p["title"], sum(g["count"] for g in p["groups"])))
        return

    made = 0
    for p in todo:
        r = call(CREATE, {"workout": payload(p)}, prefix=PREFIX)
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
