#!/usr/bin/env python3
"""ErgZone admin track — API recon (token auth, READ-ONLY).

Authenticates to admin.erg.zone with ERGZONE_TOKEN (a short-lived session
token grabbed from the logged-in browser — no password) and captures the
list/detail API shapes for the track, so a create step can be written
against reality. Creates/edits nothing.

Runs only in GitHub Actions (dev sandbox can't reach erg.zone). The token
is scrubbed from all output on top of GitHub's secret masking.
"""
import os, re, json
from playwright.sync_api import sync_playwright

TRACK = "68afa180-10d1-4ca1-8d3a-dff940e147b2"
TRACK_URL = f"https://admin.erg.zone/tracks/{TRACK}/workouts"
TOKEN = os.environ.get("ERGZONE_TOKEN", "").strip()
OUT = "recon_out"; os.makedirs(OUT, exist_ok=True)

def scrub(s):
    s = str(s)
    if TOKEN: s = s.replace(TOKEN, "***")
    s = re.sub(r'(SFMyNTY\.[A-Za-z0-9_.-]{20,})', "***", s)  # phoenix tokens
    s = re.sub(r'((?:token|access_token|authorization)["\s:=]+)[A-Za-z0-9._-]{20,}', r"\1***", s, flags=re.I)
    return s

api = []
def on_resp(r):
    try:
        if "erg.zone" in r.url and "json" in r.headers.get("content-type","") and len(api) < 80:
            api.append((r.request.method, r.status, r.url, r.text()[:8000]))
    except Exception: pass

with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={"width":1400,"height":1800}); pg = ctx.new_page()
    pg.on("response", on_resp)

    # land on the origin so we can seed auth
    pg.goto("https://admin.erg.zone/", wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(1500)

    if TOKEN:
        # try the token in every plausible slot: localStorage keys + a cookie + auth header
        pg.evaluate("""t => {
          const keys = ['token','authToken','auth_token','access_token','ergzone_token','session','userToken','jwt'];
          for (const k of keys) { try { localStorage.setItem(k, t); } catch(e){} }
          try { localStorage.setItem('phx:token', t); } catch(e){}
        }""", TOKEN)
        try:
            ctx.add_cookies([
                {"name":"_ergzone_admin_key","value":TOKEN,"domain":"admin.erg.zone","path":"/"},
                {"name":"token","value":TOKEN,"domain":".erg.zone","path":"/"},
            ])
        except Exception as e:
            print("cookie set failed:", scrub(e))
        # also send it as a default header for API calls
        try:
            ctx.set_extra_http_headers({"authorization": "Bearer " + TOKEN, "x-access-token": TOKEN})
        except Exception as e:
            print("header set failed:", scrub(e))

    pg.goto(TRACK_URL, wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(4000)
    pg.screenshot(path=f"{OUT}/track.png", full_page=True)

    print("final url:", scrub(pg.url))
    try:
        body = pg.inner_text("body", timeout=5000)
        lines = [l.strip() for l in body.split("\n") if l.strip()]
        print(f"\n===== TRACK PAGE ({len(lines)} lines) =====")
        for l in lines[:120]: print("  |", scrub(l))
    except Exception as e:
        print("no body:", scrub(e))

    print("\n===== ERGZONE API TRAFFIC =====")
    for meth, st, url, body in api:
        print(f"\n[{meth} {st}] {scrub(url)}")
        print("   ", scrub(body).replace("\n"," ")[:2500])
    if not api:
        print("(no erg.zone JSON API calls captured — auth slot likely wrong; see body dump above)")

    b.close()
print("\nrecon complete")
