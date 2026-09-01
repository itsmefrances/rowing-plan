#!/usr/bin/env python3
"""rowing — one portable MCP server for the whole training loop.

Four capabilities, callable from any Claude session that loads this server
(built for Cowork). It runs in YOUR environment and uses YOUR tokens, so
there is no sandbox-reachability problem and nothing is stored in a repo:

  1. HubFit      – read your training calendar / workouts (private API).
  2. Concept2    – read your public logbook results + per-interval splits.
  3. ErgZone     – translate a workout (plain text OR a HubFit workout, with
                   its variable per-interval pacing) into an ErgZone workout
                   spec, and create it in your coach track.
  4. Plan        – render workouts into portable shapes to drop into your
                   personal plan (site-agnostic; adapters per target).

Pace model (source of truth: https://conkers.eatonrise.com/rowcalc/ ):
  linear off the 500 m PB — 100 % = PB (1:39.9), each 1 % below adds 1 s
  to the /500 m split. One constant, PB_500, drives every pace.

Environment variables (set the ones you use):
  HUBFIT_TOKEN       JWT from the logged-in browser: localStorage
                     'persist:root' -> clientAccess.token  (expires; re-grab
                     when calls return invalidToken).
  HUBFIT_CLIENT_ID   clientAccess.clientId  (for history).
  ERGZONE_TOKEN      session token from admin.erg.zone (Authorization / a
                     cookie). Only needed to CREATE workouts.
  ERGZONE_TRACK      your coach track id (default below).
  ERGZONE_CREATE_URL optional: the exact admin.erg.zone create-workout
                     endpoint once captured (see README). When unset,
                     ergzone_create returns the ready-to-enter spec instead
                     of posting, so Cowork can enter it via the browser.
  C2_PROFILE         Concept2 profile id (default 2198296).
"""
import os, re, json, ssl, datetime, urllib.request, urllib.parse, urllib.error
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("rowing")

HUBFIT_BASE   = "https://app.hubfit.com"
HUBFIT_TOKEN  = os.environ.get("HUBFIT_TOKEN", "").strip()
HUBFIT_CLIENT = os.environ.get("HUBFIT_CLIENT_ID", "").strip()
ERGZONE_BASE  = "https://admin.erg.zone"
ERGZONE_TOKEN = os.environ.get("ERGZONE_TOKEN", "").strip()
ERGZONE_TRACK = os.environ.get("ERGZONE_TRACK", "68afa180-10d1-4ca1-8d3a-dff940e147b2").strip()
ERGZONE_CREATE_URL = os.environ.get("ERGZONE_CREATE_URL", "").strip()
C2_PROFILE    = os.environ.get("C2_PROFILE", "2198296").strip()
PB_500        = float(os.environ.get("PB_500", "99.9"))

try:
    import certifi
    _SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL = ssl.create_default_context()

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


class ApiError(Exception):
    pass


# --------------------------------------------------------------------------- #
# Pace model
# --------------------------------------------------------------------------- #
def _split(pct: float) -> str:
    s = round(PB_500 + (100 - pct))
    return f"{s // 60}:{s % 60:02d}"


def _pct_from_split(text: str):
    m = re.match(r"^(\d+):(\d\d(?:\.\d)?)$", text.strip())
    if not m:
        return None
    sec = int(m.group(1)) * 60 + float(m.group(2))
    return round(100 - (sec - PB_500))


@mcp.tool()
def pace_split(pct: float) -> str:
    """/500 m split for a percentage of the 500 m PB (linear model). e.g. 90 -> '1:50'."""
    return _split(pct)


@mcp.tool()
def pace_band(pct_lo: float, pct_hi: float) -> str:
    """Rendered pace band for a %-range, fast end first: split(hi)-split(lo). e.g. (70,75) -> '2:05-2:10'."""
    return f"{_split(pct_hi)}\u2013{_split(pct_lo)}"


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def _http(url: str, headers: dict, method: str = "GET", data: bytes | None = None) -> str:
    req = urllib.request.Request(url, headers=headers, method=method, data=data)
    try:
        with urllib.request.urlopen(req, timeout=30, context=_SSL) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise ApiError(f"HTTP {e.code} for {url}: {e.read().decode('utf-8','replace')[:200]}")
    except urllib.error.URLError as e:
        raise ApiError(f"Network error for {url}: {e}")


# --------------------------------------------------------------------------- #
# 1. HubFit  (private API — x-access-token)
# --------------------------------------------------------------------------- #
def _hubfit_get(path: str, params: dict | None = None) -> dict:
    if not HUBFIT_TOKEN:
        raise ApiError("HUBFIT_TOKEN not set (persist:root -> clientAccess.token).")
    url = HUBFIT_BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    body = _http(url, {"x-access-token": HUBFIT_TOKEN, "Accept": "application/json", "User-Agent": "rowing-mcp/1.0"})
    data = json.loads(body)
    if isinstance(data, dict) and data.get("invalidToken"):
        raise ApiError("HubFit token expired — re-grab HUBFIT_TOKEN from the browser.")
    if isinstance(data, dict) and data.get("success") is False:
        raise ApiError(f"HubFit error: {data.get('message', '?')}")
    return data


def _hubfit_meta() -> dict:
    return _hubfit_get("/api/training/program/calendar/client/metadata")


def _flatten_exercise(ex: dict) -> dict:
    fields = {}
    for i in (1, 2, 3, 4):
        n = (ex.get(f"field{i}Name") or "").strip()
        v = (ex.get(f"field{i}Value") or "").strip()
        if n or v:
            fields[n or f"field{i}"] = v
    out = {"name": ex.get("name", ""), "sets": ex.get("sets", ""), "fields": fields}
    if (ex.get("customNote") or "").strip():
        out["note"] = ex["customNote"].strip()
    return out


def _shape_workout(det: dict) -> dict:
    sections = []
    for sec in det.get("sections", []):
        ses = [{"name": se.get("name", ""), "exercises": [_flatten_exercise(e) for e in se.get("exercises", [])]}
               for se in sec.get("sectionExercises", [])]
        sections.append({"name": sec.get("name", ""), "type": sec.get("type", ""),
                         "rounds": sec.get("rounds", 0), "duration": sec.get("duration", 0), "exercises": ses})
    wm = det.get("workout", {}) or {}
    return {"id": det.get("_id"), "name": det.get("name", ""), "description": det.get("description", ""),
            "date": wm.get("date"), "totalExercises": wm.get("totalExercises"),
            "completed": bool(wm.get("completedWorkoutId")), "sections": sections}


@mcp.tool()
def hubfit_list_workouts(start_date: str = "", end_date: str = "", include_strength: bool = True) -> str:
    """List every workout in your HubFit program (id, name, date, completed). Dates are ISO 'YYYY-MM-DD'."""
    meta = _hubfit_meta()
    rows = []
    for w in meta.get("workouts", []):
        d = w.get("date", "")
        if start_date and d < start_date:
            continue
        if end_date and d > end_date:
            continue
        if not include_strength and "strength" in (w.get("name", "").lower()):
            continue
        rows.append({"id": w.get("_id"), "name": w.get("name", ""), "date": d,
                     "totalExercises": w.get("totalExercises"), "completed": bool(w.get("completedWorkoutId"))})
    rows.sort(key=lambda r: r["date"] or "")
    return json.dumps({"trainingProgramId": meta.get("trainingProgramId"), "count": len(rows), "workouts": rows},
                      ensure_ascii=False, indent=2)


@mcp.tool()
def hubfit_get_workout(workout_id: str) -> str:
    """Full detail for one HubFit workout — sections, exercises, and the field pairs that carry the variable pacing."""
    meta = _hubfit_meta()
    det = _hubfit_get("/api/training/program/workout",
                      {"trainingProgramId": meta.get("trainingProgramId"), "workoutId": workout_id})
    return json.dumps(_shape_workout(det), ensure_ascii=False, indent=2)


@mcp.tool()
def hubfit_export_workouts(start_date: str = "", end_date: str = "",
                           include_strength: bool = False, future_only: bool = True) -> str:
    """Batch-export full detail for a date range (monthly planning). Excludes strength by default."""
    meta = _hubfit_meta()
    pid = meta.get("trainingProgramId")
    lo = start_date or (datetime.date.today().isoformat() if future_only else "")
    out, errors = [], []
    for w in sorted(meta.get("workouts", []), key=lambda w: w.get("date") or ""):
        d = w.get("date", "")
        if lo and d < lo:
            continue
        if end_date and d > end_date:
            continue
        if not include_strength and "strength" in (w.get("name", "").lower()):
            continue
        try:
            det = _hubfit_get("/api/training/program/workout", {"trainingProgramId": pid, "workoutId": w.get("_id")})
            shaped = _shape_workout(det)
            shaped["date"] = w.get("date") or shaped.get("date")
            out.append(shaped)
        except ApiError as e:
            errors.append({"id": w.get("_id"), "name": w.get("name"), "error": str(e)})
    res = {"count": len(out), "workouts": out}
    if errors:
        res["errors"] = errors
    return json.dumps(res, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# 2. Concept2  (public logbook — no auth)
# --------------------------------------------------------------------------- #
def _c2_fetch(url: str) -> str:
    return _http(url, {"User-Agent": UA})


def _strip_tags(html: str):
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", html).replace("&nbsp;", " ").replace("&amp;", "&").replace("&#039;", "'")
    return [ln.strip() for ln in text.split("\n") if ln.strip()]


def _time_secs(t):
    parts = [float(x) for x in t.split(":")]
    return sum(x * 60 ** (len(parts) - 1 - i) for i, x in enumerate(parts))


def _parse_c2_workout(html: str) -> dict:
    lines = _strip_tags(html)
    months = {m: i + 1 for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"])}
    months.update({m[:3]: v for m, v in list(months.items())})
    out = {}
    for ln in lines:
        m = re.search(r"\b([A-Z][a-z]{2,8})\.?\s+(\d{1,2}),\s+(20\d\d)\b", ln)
        if m and m.group(1) in months:
            out["date"] = f"{m.group(3)}-{months[m.group(1)]:02d}-{int(m.group(2)):02d}"
            break

    def stat(label_re, value_re, conv=lambda x: x, valid=lambda v: True):
        for i, ln in enumerate(lines):
            if re.fullmatch(label_re, ln, re.I):
                for c in ([lines[i - 1]] if i else []) + lines[i + 1:i + 3]:
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
    intervals = []
    if "Intervals" in lines:
        start = lines.index("Intervals") + 1
        end = len(lines)
        for s in ("Splits", "Workout Graph", "Quick Links", "Click on an interval to see the workout graph."):
            if s in lines[start:]:
                end = min(end, lines.index(s, start))
        i = start
        while i <= end - 3:
            t = re.fullmatch(r"((?:\d+:)?\d{1,2}:\d\d\.\d)", lines[i])
            d = re.fullmatch(r"([\d,]+)", lines[i + 1]) if t else None
            pc = re.fullmatch(r"(\d+:\d\d\.\d)", lines[i + 2]) if d else None
            if t and d and pc and int(d.group(1).replace(",", "")) > 0:
                intervals.append({"time": t.group(1), "dist": int(d.group(1).replace(",", "")), "pace": pc.group(1)})
                i += 3
            else:
                i += 1
    if intervals:
        out["intervals"] = intervals
    return out


@mcp.tool()
def concept2_list_results(limit: int = 15, profile_id: str = "") -> str:
    """Recent Concept2 logbook workouts for the profile (id, date, distance, time, pace). Public data, no auth."""
    pid = profile_id or C2_PROFILE
    listing = _c2_fetch(f"https://log.concept2.com/profile/{pid}/log")
    ids, seen = [], set()
    for m in re.finditer(rf"/profile/{pid}/log/(\d+)", listing):
        wid = m.group(1)
        if wid not in seen:
            seen.add(wid); ids.append(wid)
    rows = []
    for wid in ids[:limit]:
        try:
            w = _parse_c2_workout(_c2_fetch(f"https://log.concept2.com/profile/{pid}/log/{wid}"))
            rows.append({"id": wid, "link": f"https://log.concept2.com/profile/{pid}/log/{wid}",
                         "date": w.get("date"), "dist": w.get("dist"), "time": w.get("time"),
                         "pace": w.get("pace"), "rate": w.get("rate"), "intervals": len(w.get("intervals") or [])})
        except ApiError:
            continue
    return json.dumps({"profile": pid, "count": len(rows), "workouts": rows}, ensure_ascii=False, indent=2)


@mcp.tool()
def concept2_get_workout(workout_id: str, profile_id: str = "") -> str:
    """Full detail for one logbook workout, including per-interval splits (time / meters / pace per rep)."""
    pid = profile_id or C2_PROFILE
    w = _parse_c2_workout(_c2_fetch(f"https://log.concept2.com/profile/{pid}/log/{workout_id}"))
    w["id"] = workout_id
    w["link"] = f"https://log.concept2.com/profile/{pid}/log/{workout_id}"
    return json.dumps(w, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# 3. ErgZone  (build spec from text / HubFit, then create)
# --------------------------------------------------------------------------- #
def _interval_from_text(seg: str) -> dict | None:
    """Parse one interval clause like '250m @95%' or '20:00 @ 2:25' or '4 min @ 75%'."""
    seg = seg.strip()
    iv = {}
    d = re.search(r"(\d[\d,]*)\s*m\b", seg)
    t = re.search(r"\b(\d{1,3}:\d\d)\b", seg)
    mn = re.search(r"(\d+)\s*min\b", seg, re.I)
    if d:
        iv["type"] = "distance"; iv["meters"] = int(d.group(1).replace(",", ""))
    elif mn:
        iv["type"] = "time"; iv["seconds"] = int(mn.group(1)) * 60
    elif t and "@" not in seg.split(t.group(1))[0][-3:]:
        iv["type"] = "time"; iv["seconds"] = int(_time_secs(t.group(1)))
    else:
        return None
    # target: explicit split, else % of PB
    ps = re.search(r"@?\s*(\d:\d\d)\s*(?:/500|split)?", seg)
    pc = re.search(r"(\d{2,3})\s*%", seg)
    if pc:
        iv["pct"] = int(pc.group(1)); iv["target"] = _split(int(pc.group(1)))
    elif ps and ps.group(1) != (t.group(1) if t and iv.get("type") == "time" else None):
        iv["target"] = ps.group(1)
    r = re.search(r"(\d{2})\s*(?:s/m|spm|s\.?p\.?m)", seg, re.I)
    if r:
        iv["rate"] = int(r.group(1))
    rest = re.search(r"(\d{1,2}:\d\d)\s*(?:rest|off|r\b)|rest\s*(\d{1,2}:\d\d)", seg, re.I)
    if rest:
        iv["rest"] = rest.group(1) or rest.group(2)
    return iv


@mcp.tool()
def ergzone_build_workout(source: str, name: str = "", reps: int = 0) -> str:
    """Translate a workout into an ErgZone spec, preserving VARIABLE per-interval pacing.

    `source` is either plain text (e.g. '6 × 250m @95% rest 3:00' or a multi-line
    variable-interval prescription, one clause per line) OR the JSON string of a
    HubFit workout (from hubfit_get_workout) — its section/exercise field pairs
    are read for the interval structure. Percentages convert to /500 m splits via
    the linear PB model. Returns {name, intervals:[...]} ready for ergzone_create
    or manual entry.
    """
    # HubFit workout JSON?
    try:
        obj = json.loads(source)
        if isinstance(obj, dict) and ("sections" in obj or "name" in obj):
            name = name or obj.get("name", "Workout")
            text = obj.get("description", "")
            for sec in obj.get("sections", []):
                for se in sec.get("exercises", []):
                    for ex in se.get("exercises", []):
                        parts = [ex.get("name", "")] + [f"{k} {v}" for k, v in (ex.get("fields") or {}).items()]
                        if ex.get("note"):
                            parts.append(ex["note"])
                        text += "\n" + " · ".join(p for p in parts if p)
            source = text
    except (json.JSONDecodeError, TypeError):
        pass

    lines = [ln for ln in re.split(r"[\n;]|\bthen\b|\+(?=\s*\d)", source) if ln.strip()]
    intervals = []
    for ln in lines:
        rep_m = re.search(r"(\d+)\s*[x×]\s*", ln)
        n = int(rep_m.group(1)) if rep_m else 1
        iv = _interval_from_text(ln)
        if iv:
            for _ in range(n):
                intervals.append(dict(iv))
    if reps and len(intervals) == 1:
        intervals = [dict(intervals[0]) for _ in range(reps)]
    spec = {"name": name or "Untitled workout", "track": ERGZONE_TRACK, "intervals": intervals}
    if not intervals:
        spec["warning"] = "No intervals parsed — pass clearer clauses (e.g. '250m @95% rest 3:00')."
    return json.dumps(spec, ensure_ascii=False, indent=2)


@mcp.tool()
def ergzone_create(spec_json: str) -> str:
    """Create a workout in your ErgZone track from a spec (from ergzone_build_workout).

    If ERGZONE_CREATE_URL + ERGZONE_TOKEN are set, POSTs the spec and returns the
    response (including the w/… share link if present). If not, returns the spec
    plus entry instructions so it can be created in the browser (Cowork) — see the
    README for capturing the create endpoint once to enable direct posting.
    """
    spec = json.loads(spec_json)
    if ERGZONE_CREATE_URL and ERGZONE_TOKEN:
        body = json.dumps(spec).encode()
        headers = {"Content-Type": "application/json", "Accept": "application/json",
                   "Authorization": "Bearer " + ERGZONE_TOKEN, "x-access-token": ERGZONE_TOKEN}
        try:
            resp = _http(ERGZONE_CREATE_URL, headers, method="POST", data=body)
            return json.dumps({"status": "created", "response": json.loads(resp)}, ensure_ascii=False, indent=2)
        except (ApiError, json.JSONDecodeError) as e:
            return json.dumps({"status": "post_failed", "error": str(e), "spec": spec}, ensure_ascii=False, indent=2)
    steps = []
    for i, iv in enumerate(spec.get("intervals", []), 1):
        unit = f"{iv.get('meters')}m" if iv.get("type") == "distance" else f"{iv.get('seconds', 0)//60}:{iv.get('seconds',0)%60:02d}"
        steps.append(f"  rep {i}: {unit}"
                     + (f" @ {iv['target']}/500" if iv.get("target") else "")
                     + (f" · rate {iv['rate']}" if iv.get("rate") else "")
                     + (f" · rest {iv['rest']}" if iv.get("rest") else ""))
    return json.dumps({"status": "manual",
                       "instructions": f"In admin.erg.zone track {spec.get('track')}, create '{spec.get('name')}':",
                       "steps": steps, "spec": spec}, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
# 4. Plan  (portable output — site-agnostic)
# --------------------------------------------------------------------------- #
@mcp.tool()
def plan_to_rows(workouts_json: str) -> str:
    """Render workouts into the rowing-plan row-item shape ({t:row,n,pctLo,pctHi,rest}).

    Input: JSON list of {date, name, pct_lo, pct_hi, rest} (or an ergzone spec list).
    Bands stay DERIVED — pctLo/pctHi are stored, the /500 m split is computed at
    render time so a PB change recomputes everything.
    """
    items = json.loads(workouts_json)
    rows = []
    for w in items:
        rows.append({"date": w.get("date"), "t": "row", "n": w.get("name", ""),
                     "pctLo": w.get("pct_lo"), "pctHi": w.get("pct_hi"), "rest": w.get("rest", "")})
    return json.dumps(rows, ensure_ascii=False, indent=2)


@mcp.tool()
def plan_to_markdown(workouts_json: str) -> str:
    """Render workouts as a portable Markdown table (date · workout · pace band · rate) for any plan site."""
    items = json.loads(workouts_json)
    out = ["| Date | Workout | Pace /500m | Rate |", "|---|---|---|---|"]
    for w in items:
        band = pace_band(w["pct_lo"], w["pct_hi"]) if w.get("pct_lo") is not None else (w.get("pace", ""))
        out.append(f"| {w.get('date','')} | {w.get('name','')} | {band} | {w.get('rate','')} |")
    return "\n".join(out)


if __name__ == "__main__":
    mcp.run()
