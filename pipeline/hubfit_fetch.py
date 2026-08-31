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
def on_response(resp):
    try:
        ct = resp.headers.get("content-type", "")
        if "json" in ct and len(api_calls) < 60:
            cap = 4000 if "hubfit.com/api" in resp.url else 400
            body = resp.text()[:cap]
            api_calls.append((resp.status, resp.url, body))
    except Exception:
        pass

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 430, "height": 1400})
    page = ctx.new_page()
    page.on("response", on_response)

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
                # talk to the API directly from inside the authenticated page
                print("\n===== IN-PAGE API PROBE =====")
                keys = page.evaluate("() => Object.keys(localStorage).concat(Object.keys(sessionStorage).map(k => 'session:'+k))")
                print("storage keys:", keys)
                probe = page.evaluate("""async () => {
                  const cid = '6a194933c0dbc1a3577469cd';
                  let token = '';
                  for (const store of [localStorage, sessionStorage])
                    for (const k of Object.keys(store))
                      if (/token|auth/i.test(k) && (store.getItem(k)||'').length > 20) token = store.getItem(k);
                  const hs = token ? [{}, {Authorization: 'Bearer '+token}, {'x-access-token': token}, {token: token}] : [{}];
                  const get = async (u) => {
                    for (const h of hs) {
                      try {
                        const r = await fetch(u, {headers: h, credentials: 'include'});
                        const j = await r.json();
                        if (j && j.success !== false) return {status: r.status, hdr: Object.keys(h).join(',')||'none', body: j};
                      } catch (e) {}
                    }
                    return {status: 'all-failed', body: null};
                  };
                  const out = {};
                  out.sep = await get(`/api/training/program/calendar/client/metadata?clientId=${cid}&date=2026-09-15`);
                  // pull a workout id for a detail probe
                  let wid = null, wdate = null;
                  const w = (out.sep.body && out.sep.body.workouts) || [];
                  for (const x of w) if (x.date >= '2026-08-31') { wid = x._id; wdate = x.date; break; }
                  out.probeTarget = {wid, wdate};
                  if (wid) {
                    out.detailA = await get(`/api/training/program/calendar/client/workout?clientId=${cid}&workoutId=${wid}`);
                    out.detailB = await get(`/api/training/program/workout/${wid}?clientId=${cid}`);
                    out.detailC = await get(`/api/training/workout/${wid}?clientId=${cid}`);
                    out.detailD = await get(`/api/training/program/calendar/client/workout/${wid}?clientId=${cid}`);
                  }
                  return out;
                }""")
                blob = json.dumps(probe)
                print(scrub(blob[:9000]))
                open(f"{OUT}/api_probe.json", "w").write(scrub(blob))
                # fallback: force-click a tile so its detail request gets sniffed
                try:
                    n_before = len(api_calls)
                    page.get_by_text("Recovery Workout", exact=False).first.click(timeout=10000, force=True)
                    page.wait_for_timeout(5000)
                    page.screenshot(path=f"{OUT}/4_tile.png", full_page=True)
                    dump_text(page, "AFTER TILE FORCE-CLICK", limit=120)
                    print(f"  (captured {len(api_calls)-n_before} new API calls after click)")
                except Exception as e:
                    print("force-click failed:", scrub(str(e))[:200])
            dump_controls(page, "AFTER LOGIN")
            # try to surface training links
            print("\n----- links containing 'training'/'workout' -----")
            for a in page.query_selector_all("a[href]")[:60]:
                href = a.get_attribute("href") or ""
                if re.search(r"train|workout|program|session", href, re.I):
                    print("  ->", scrub(href))
        except Exception as e:
            print("LOGIN ATTEMPT FAILED:", scrub(str(e))[:300])
    else:
        print("\n(no credentials in env -- landing page recon only)")

    print("\n===== JSON API TRAFFIC =====")
    for status, url, body in api_calls:
        print(f"\n[{status}] {scrub(url)}")
        print("   ", scrub(body).replace("\n", " ")[:800])

    browser.close()
print("\nrecon complete")
