import json

PB = 99.9  # 1:39.9 in seconds (500m PB)

def split_at_pct(pct):
    """Confirmed rowcalc model: each 1% above/below 100% = 1 sec off the 500m split.
       100% -> PB. split = PB + (100 - pct)."""
    return PB + (100 - pct)

def fmt(sec):
    m=int(sec//60); s=sec-60*m
    return f"{m}:{s:04.1f}" if s<10 else f"{m}:{s:.1f}"

def fmt_clean(sec):
    sec=int(round(sec))          # round first, then split, so 119.9 -> 120 -> 2:00
    m=sec//60; s=sec%60
    return f"{m}:{s:02d}"

# --- VERIFY against the calculator's published table ---
expected = {50:"2:29.9",60:"2:19.9",70:"2:09.9",80:"1:59.9",90:"1:49.9",100:"1:39.9",110:"1:29.9",120:"1:19.9"}
print("=== Verifying pace model vs rowcalc table ===")
ok=True
for pct,exp in expected.items():
    got=fmt(split_at_pct(pct))
    match = got==exp
    ok = ok and match
    print(f"  {pct}% -> {got}  (calc: {exp})  {'OK' if match else 'MISMATCH'}")
print("MODEL VERIFIED" if ok else "MODEL ERROR")
print()

# --- Compute per-workout targets ---
data=json.load(open("workouts.json"))
out=[]
for w in data:
    lo,hi=w["intensity"]
    # split is faster (smaller) at higher %, so high% -> fast split (lower time)
    split_fast=split_at_pct(hi)   # at the harder end of the zone
    split_slow=split_at_pct(lo)
    rec={**w}
    rec["split_low_pct"]=fmt_clean(split_slow)   # easier end
    rec["split_high_pct"]=fmt_clean(split_fast)  # harder end
    rec["split_range"]=f"{fmt_clean(split_fast)}–{fmt_clean(split_slow)}"
    # If a distance is given, compute target finish time per rep at both ends
    if w.get("dist"):
        d=w["dist"]
        t_fast=split_fast*(d/500.0)
        t_slow=split_slow*(d/500.0)
        rec["rep_time_range"]=f"{fmt_clean(t_fast)}–{fmt_clean(t_slow)}"
        rec["rep_time_fast"]=fmt_clean(t_fast)
        rec["rep_time_slow"]=fmt_clean(t_slow)
    out.append(rec)

json.dump(out, open("computed.json","w"), ensure_ascii=False, indent=1)
print(f"=== Computed targets for {len(out)} workouts (sample) ===")
for r in out[:6]:
    extra = f" | rep {r['rep_time_range']}" if r.get('rep_time_range') else ""
    print(f"  {r['date']} {r['name'][:22]:22} {r['intensity'][0]}-{r['intensity'][1]}% -> split {r['split_range']}/500m{extra}")
