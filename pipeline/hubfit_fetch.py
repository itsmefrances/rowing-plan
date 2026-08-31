#!/usr/bin/env python3
"""HubFit -> repo fetcher (reconnaissance mode).

Logs into app.hubfit.com with HUBFIT_USER / HUBFIT_CODE (GitHub Actions
secrets) using a real browser, dumps the page structure and any JSON API
traffic so the parser can be written against reality. Credentials are
never printed; their values are scrubbed from all output as a belt to
GitHub's automatic secret masking suspenders.

Runs only in GitHub Actions (the dev sandbox cannot reach hubfit.com).
"""
import json, os, re, sys
from playwright.sync_api import sync_playwright

URL = "https://app.hubfit.com/c/training/6a194933c0dbc1a3577469cd"
USER = os.environ.get("HUBFIT_USER", "")
CODE = os.environ.get("HUBFIT_CODE", "")
OUT = "recon_out"
os.makedirs(OUT, exist_ok=True)

def scrub(s):
    for secret in (USER, CODE):
        if secret:
            s = s.replace(secret, "***")
    s = re.sub(r'"token"\s*:\s*"[^"]*"', '"token":"***"', s)
    s = re.sub(r'(Authorization[^A-Za-z0-9]{0,4})[A-Za-z0-9._-]{12,}', r"\1***", s)
    return s

def dump_text(page, label, limit=250):
    print(f"\n===== {label}: {scrub(page.url)} =====")
    try:
        body = page.inner_text("body", timeout=5000)
    except Exception as e:
        print("  (no body text:", e, ")"); return
    lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
    for ln in lines[:limit]:
        print("  |", scrub(ln))
    if len(lines) > limit:
        print(f"  ... ({len(lines)-limit} more lines)")

def dump_controls(page, label):
    print(f"\n----- {label}: form controls -----")
    for el in page.query_selector_all("input, button, select, [role=button]")[:40]:
        try:
            tag = el.evaluate("e => e.tagName.toLowerCase()")
            typ = el.get_attribute("type") or ""
            name = el.get_attribute("name") or el.get_attribute("id") or ""
            ph = el.get_attribute("placeholder") or ""
            txt = (el.inner_text() or "").strip()[:40] if tag != "input" else ""
            print(f"  <{tag}> type={typ!r} name={name!r} placeholder={ph!r} text={scrub(txt)!r}")
        except Exception:
            pass

api_calls = []
auth_header = {"value": None, "name": None}
def on_request(req):
    try:
        if "hubfit.com/api" in req.url and auth_header["value"] is None:
            h = req.headers
            for name in ("authorization", "x-access-token", "token"):
                if h.get(name):
                    auth_header["name"] = name
                    auth_header["value"] = h[name]
                    break
    except Exception:
        pass
def on_response(resp):
    try:
        ct = resp.headers.get("content-type", "")
        if "json" in ct and len(api_calls) < 60:
            cap = 60000 if "calendar/client/metadata" in resp.url else (4000 if "hubfit.com/api" in resp.url else 400)
            body = resp.text()[:cap]
            api_calls.append((resp.status, resp.url, body))
    except Exception:
        pass

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 430, "height": 1400})
    page = ctx.new_page()
    page.on("response", on_response)
    page.on("request", on_request)

    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)
    page.screenshot(path=f"{OUT}/1_landing.png", full_page=True)
    dump_text(page, "LANDING PAGE")
    dump_controls(page, "LANDING PAGE")

    # login attempt (only if credentials provided)
    if USER and CODE:
        try:
            # the login form has a Coach/Client toggle; client accounts use
            # username + access code, so flip to Client first
            try:
                page.get_by_text("Client", exact=True).first.click(timeout=5000)
                page.wait_for_timeout(1500)
                dump_controls(page, "AFTER CLIENT TOGGLE")
                dump_text(page, "AFTER CLIENT TOGGLE", limit=60)
            except Exception as e:
                print("client-toggle click failed:", scrub(str(e))[:200])
            fields = [f for f in page.query_selector_all(
                          "input[type=text], input[type=email], input[type=password], input[type=tel], input[type=number], input:not([type])")
                      if f.is_visible()]
            print(f"fillable fields: {len(fields)}")
            if len(fields) >= 2:
                fields[0].fill(USER); fields[1].fill(CODE)
            elif len(fields) == 1:
                fields[0].fill(USER)
            btn = page.query_selector(
                "button[type=submit], button:has-text('Log'), button:has-text('Sign'), button:has-text('Continue'), button:has-text('Enter')")
            if btn:
                btn.click()
            else:
                page.keyboard.press("Enter")
            page.wait_for_timeout(6000)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            page.screenshot(path=f"{OUT}/2_after_login.png", full_page=True)
            dump_text(page, "AFTER LOGIN", limit=200)
            if "/auth/" not in page.url:
                page.goto(URL, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(3000)
                page.screenshot(path=f"{OUT}/3_training.png", full_page=True)
                dump_text(page, "TRAINING PAGE", limit=350)
                # extract the bearer token from the redux-persist blob too
                token = page.evaluate("""() => {
                  try {
                    const root = JSON.parse(localStorage.getItem('persist:root') || '{}');
                    for (const k of Object.keys(root)) {
                      let v = root[k];
                      try { v = JSON.parse(v); } catch (e) {}
                      const s = JSON.stringify(v);
                      const m = s && s.match(/"(?:token|accessToken|authToken)"\\s*:\\s*"([^"]{16,})"/);
                      if (m) return m[1];
                    }
                  } catch (e) {}
                  return null;
                }""")
                print("\n===== AUTH REPLAY =====")
                print("sniffed header name:", auth_header["name"], "| have sniffed value:", bool(auth_header["value"]), "| token from persist:", bool(token))

                # build header set from whatever we found
                hdrs = {}
                if auth_header["value"]:
                    hdrs[auth_header["name"]] = auth_header["value"]
                elif token:
                    hdrs["Authorization"] = "Bearer " + token

                cid = "6a194933c0dbc1a3577469cd"
                import urllib.parse
                def api_get(path):
                    try:
                        r = ctx.request.get("https://app.hubfit.com" + path, headers=hdrs, timeout=30000)
                        return r.status, r.text()
                    except Exception as e:
                        return "ERR", scrub(str(e))[:200]

                # full program calendar (every workout: name, date, _id)
                st, body = api_get(f"/api/training/program/calendar/client/metadata?clientId={cid}&date=2026-09-15")
                print(f"\n[metadata 2026-09-15] {st}")
                print(scrub(body)[:20000])
                open(f"{OUT}/calendar_sept.json", "w").write(scrub(body))

                # pick a September workout id and probe detail endpoints
                wid = None
                try:
                    import json as _j
                    for w in (_j.loads(body).get("workouts") or []):
                        if w.get("date","") >= "2026-08-31" and (w.get("totalExercises") or 0) >= 1:
                            wid = w["_id"]; wdate = w["date"]; wname = w.get("name"); break
                except Exception as e:
                    print("parse metadata failed:", scrub(str(e))[:200])
                print("\ndetail probe target:", wid, wdate if wid else "", wname if wid else "")
                if wid:
                    for tmpl in (
                        f"/api/training/program/calendar/client/workout?clientId={cid}&workoutId={wid}",
                        f"/api/training/program/calendar/client/workout/{wid}?clientId={cid}",
                        f"/api/training/program/workout/{wid}?clientId={cid}",
                        f"/api/training/workout/{wid}?clientId={cid}",
                        f"/api/training/program/{{}}/workout/{wid}".format("6a194933c0dbc1a357746a0c"),
                        f"/api/workout/{wid}?clientId={cid}",
                    ):
                        st, b = api_get(tmpl)
                        ok = ('"exercises"' in b or '"interval' in b.lower() or '"sets"' in b) and '"invalidToken"' not in b
                        print(f"\n[detail {st} {'HIT' if ok else 'miss'}] {tmpl}")
                        print(scrub(b)[:6000])
                        if ok:
                            open(f"{OUT}/workout_detail.json", "w").write(scrub(b))
                            break
        except Exception as e:
            print("LOGIN/PROBE FAILED:", scrub(str(e))[:400])
    else:
        print("\n(no credentials in env -- landing page recon only)")

    print("\n===== JSON API TRAFFIC =====")
    for status, url, body in api_calls:
        print(f"\n[{status}] {scrub(url)}")
        print("   ", scrub(body).replace("\n", " ")[:800])

    browser.close()
print("\nrecon complete")
