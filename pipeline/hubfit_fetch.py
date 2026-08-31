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
        if "json" in ct and len(api_calls) < 40:
            body = resp.text()[:1200]
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
            fields = [f for f in page.query_selector_all("input")
                      if (f.get_attribute("type") or "text") not in ("hidden", "checkbox", "submit")]
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
            dump_text(page, "AFTER LOGIN", limit=350)
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
