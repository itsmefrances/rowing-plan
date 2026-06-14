import json

# Nutrition helper (130 lb, lean deficit, 150g protein floor)
def nut(kcal, carb, fat, pre, pre_when, post, post_when, tip):
    return {"kcal":kcal,"protein_g":150,"carb_g":carb,"fat_g":fat,
            "pre":pre,"pre_when":pre_when,"post":post,"post_when":post_when,"tip":tip}

REST_NUT = nut(1450,111,45,"—","","—","","Rest day (lowest cals). Spread protein ~35-40g x4 meals. Anti-inflammatory foods, hydration.")

# ---- Wednesday squat/power progression (wks 3-6) ----
squat_days = [
 {"date":"2026-06-17","week":3,"phase":"Accumulate",
  "summary":"Box jumps → Back Squat 4×5 @ 185 → jump squats → posterior accessory + core",
  "blocks":[
    "Warm-up: 5 min bike/row + leg swings, walking lunges, 10 air squats; squat ramp bar→95→135→155→170",
    "A. POWER — Box Jumps 5×3, step down, tallest box you land solid. Rest 90s. (RFD focus)",
    "B. STRENGTH — Back Squat 4×5 @ 185 lb (80%), drive up FAST, 1-2 reps in reserve. Rest 2:30-3:00",
    "C. SPEED — Jump Squats 4×4, empty bar or 2×15-25 lb DBs, explosive, full reset. Rest 90s",
    "D. ACCESSORY — DB Walking Lunge 3×10/leg · DB RDL 3×10 (light, ~35 lb) · Calf Raise 3×15",
    "CORE — Hollow hold 3×30s + Pallof press 3×10/side",
    "ZONE 2 COOLDOWN — 8-10 min easy row, conversational (~2:20+/500m), nasal breathing",
    "Power test (log it): best box jump height + a single max broad jump at the end — track weekly"],
  "nut":nut(1750,175,50,"45g carb / 25g protein","~90 min before (+5g creatine)","45g carb / 35g protein / 10g fat","within 45 min","Highest-cal day — fuel the power work.")},
 {"date":"2026-06-24","week":4,"phase":"Accumulate +",
  "summary":"Box jumps → Back Squat 5×4 @ 190 → loaded jump squats → accessory + core",
  "blocks":[
    "Warm-up: same flow; squat ramp bar→95→135→160→175",
    "A. POWER — Box Jumps 5×3, aim 1-2\" higher than last week. Rest 90s",
    "B. STRENGTH — Back Squat 5×4 @ 190 lb (83%), fast concentric, 1-2 RIR. Rest 2:30-3:00",
    "C. SPEED — Jump Squats 4×4 @ 2×20-30 lb DBs, explosive. Rest 90s",
    "D. ACCESSORY — Bulgarian Split Squat 3×8/leg · DB RDL 3×10 · Calf Raise 3×15",
    "CORE — Hollow rock 3×12 + Side plank 3×30s/side",
    "ZONE 2 COOLDOWN — 10 min easy row",
    "Power test: log box jump height + broad jump (expect equal or better than wk3)"],
  "nut":nut(1750,175,50,"45g carb / 25g protein","~90 min before (+5g creatine)","45g carb / 35g protein / 10g fat","within 45 min","Volume creeps up — keep carbs around the session.")},
 {"date":"2026-07-01","week":5,"phase":"Intensify",
  "summary":"Depth jumps → Back Squat 4×3 @ 200 → speed squats 5×3 @ 115 → accessory + core",
  "blocks":[
    "Warm-up: thorough; squat ramp bar→95→135→170→180",
    "A. POWER — Depth Jumps 4×3 from a 12-18\" box: step off, land + rebound instantly (reactive RFD). Rest 2 min. Skip if joints cranky → sub box jumps",
    "B. STRENGTH — Back Squat 4×3 @ 200 lb (87%), max-intent up, 1 RIR. Rest 3:00",
    "C. CONTRAST SPEED — Speed Squats 5×3 @ 115 lb (50%), as fast as possible. Rest 90s",
    "D. ACCESSORY — Walking Lunge 3×10/leg · DB RDL 3×8 · Calf Raise 3×15",
    "CORE — Weighted hollow hold 3×30s + Pallof press 3×10/side",
    "ZONE 2 COOLDOWN — 10 min easy row",
    "Power test: box/broad jump — this is the week explosiveness should pop"],
  "nut":nut(1750,175,50,"45g carb / 25g protein","~90 min before (+5g creatine)","50g carb / 35g protein / 10g fat","within 45 min","Heavier triples — prioritize the pre-carb + full warm-up.")},
 {"date":"2026-07-08","week":6,"phase":"Peak / express power",
  "summary":"Max-intent jumps → Back Squat 3×2 @ 205 (fast) → broad jumps → light core",
  "blocks":[
    "Warm-up: extra thorough, low volume; squat ramp bar→95→135→175→185",
    "A. POWER — Max-intent Jump Squats 5×3 (bodyweight or light), every rep maximal height. Rest 2 min",
    "B. STRENGTH — Back Squat 3×2 @ 205 lb (90%), move FAST, leave 2 RIR (this is speed-strength, not a grind). Rest 3:00",
    "C. EXPRESS — Standing Broad Jumps 5×2, max distance, full recovery. Rest 90s",
    "D. ACCESSORY (light) — DB RDL 2×10 · Calf Raise 2×15 (low volume — you're peaking)",
    "CORE — Hollow hold 2×30s",
    "ZONE 2 COOLDOWN — 8 min very easy row",
    "Peak week: volume is low on purpose so power is fresh and expressed. Log your best jumps — compare to wk3."],
  "nut":nut(1700,162,50,"45g carb / 25g protein","~90 min before","45g carb / 35g protein / 10g fat","within 45 min","Peak week, lower volume — slightly fewer carbs than heavy weeks.")},
]

# ---- Mon/Fri: week 3 real, weeks 4-6 templates ----
mondays = {
 3:{"date":"2026-06-15","name":"CFNYC — Deadlift","template":False,
    "summary":"Deadlift 5-5-5 building, 5-5 across + metcon",
    "blocks":["Strength: Deadlift 5-5-5 building, then 5-5 across (1-2 reps in reserve)",
              "Conditioning: 3 RFT — 10 strict pull-ups, 10 power cleans (75/105), 20/16 cal row",
              "Note: heavy posterior-chain + grip; pace the metcon"],
    "nut":nut(1700,162,50,"45g carb / 25g protein","~90 min before","45g carb / 35g protein / 10g fat","within 45 min","Highest-carb day — heavy pull + grippy metcon. Electrolytes intra.")},
 4:{"date":"2026-06-22","template":True},
 5:{"date":"2026-06-29","template":True},
 6:{"date":"2026-07-06","template":True},
}
fridays = {
 3:{"date":"2026-06-19","name":"CFNYC — Bench Press","template":False,
    "summary":"Bench 5-4-3 + back-off, DB row + metcon",
    "blocks":["Strength: A1 Bench Press 5-4-3 building + back-off (-20%); A2 3-pt DB Row 4×8-10/side",
              "Conditioning: 12-min AMRAP, 6-9-12 ring dips / toes-to-bar / cal row",
              "Note: upper body — no leg conflict; row the AMRAP smooth"],
    "nut":nut(1600,149,45,"45g carb / 25g protein","~90 min before","45g carb / 35g protein / 10g fat","within 45 min","Upper-body day. Prioritize veggies/fiber + hydration.")},
 4:{"date":"2026-06-26","template":True},
 5:{"date":"2026-07-03","template":True},
 6:{"date":"2026-07-10","template":True},
}
sundays = {3:"2026-06-21",4:"2026-06-28",5:"2026-07-05",6:"2026-07-12"}

def mf_entry(d, kind_label):
    if d.get("template"):
        return {"date":d["date"],"name":f"CFNYC — {kind_label}","kind":"cfnyc","template":True,
                "summary":"Awaiting CrossFit NYC newsletter (auto-fills Sunday)",
                "blocks":[f"⏳ {kind_label} day — the Sunday job will pull this week's programming from the CFNYC newsletter and fill it in here.",
                          "Fixed slot: this day stays put; rowing + squat work are scheduled around it."],
                "nut":nut(1650,153,48,"45g carb / 25g protein","~90 min before","45g carb / 35g protein / 10g fat","within 45 min","Strength day — final macros set when the workout is known.")}
    e={"date":d["date"],"name":d["name"],"kind":"cfnyc","template":False,
       "summary":d["summary"],"blocks":d["blocks"],"nutrition":d["nut"]}
    return e

out=[]
# Mondays
for wk,d in mondays.items():
    out.append(mf_entry(d, "Deadlift" if wk!=3 else "Deadlift"))
# Fridays
for wk,d in fridays.items():
    out.append(mf_entry(d, "Bench Press"))
# Wednesdays (squat)
for s in squat_days:
    out.append({"date":s["date"],"name":"Back Squat + Power","kind":"squat","template":False,
                "phase":s["phase"],"summary":s["summary"],"blocks":s["blocks"],"nutrition":s["nut"]})
# Sundays (rest)
for wk,dt in sundays.items():
    out.append({"date":dt,"name":"Rest / Mobility","kind":"rest","template":False,
                "summary":"Full recovery + light mobility",
                "blocks":["Full rest, or 20-30 min easy walk + mobility (hips, ankles, T-spine, lats)",
                          "Optional: 10-15 min rowing technique drills (legs-only, arms-only), no intensity",
                          "CORE (optional): dead bug 3×10 + bird dog 3×10/side"],
                "nutrition":REST_NUT})

# normalize template entries that used 'nut' key
for e in out:
    if "nut" in e and "nutrition" not in e:
        e["nutrition"]=e.pop("nut")
    e.pop("nut",None)

out.sort(key=lambda x:x["date"])
json.dump({"strength_days":out}, open("strength.json","w"), ensure_ascii=False, indent=1)
print("wrote strength.json with", len(out), "entries across wks 3-6")
import collections
print("by kind:", dict(collections.Counter(e["kind"] for e in out)))
print("templates (awaiting newsletter):", sum(1 for e in out if e.get("template")))
