import json, datetime

d = json.load(open("computed.json"))
comp = json.load(open("completions.json"))
COMPLETED = comp.get("completed", {})
LAST_SYNCED = comp.get("last_synced", "")
TODAY = datetime.date.fromisoformat(comp.get("today", datetime.date.today().isoformat()))

for w in d:
    dt = datetime.date.fromisoformat(w["date"])
    iso = dt.isocalendar()
    w["_isoweek"] = (iso[0], iso[1])
    w["_dow"] = dt.strftime("%a")
    w["_nice"] = dt.strftime("%b %-d")

weeks = sorted(set(w["_isoweek"] for w in d))
wkmap = {wk: i + 1 for i, wk in enumerate(weeks)}

today_iso = TODAY.isocalendar()
CURRENT_ISO = (today_iso[0], today_iso[1])

TYPE_COLORS = {
    "Sprint Training":      ("#ef4444", "Sprint"),
    "VO₂ Max Training":     ("#f59e0b", "VO₂ Max"),
    "Threshold Training":   ("#3b82f6", "Threshold"),
    "Summer Solstice Challenge": ("#8b5cf6", "Endurance"),
    "Rowfit Games – Virtual Race: 1-Minute Test": ("#10b981", "Test"),
    "Rowfit Games – Virtual Race: 2000m Test": ("#10b981", "Test"),
}
def meta(name):
    for k, v in TYPE_COLORS.items():
        if name.startswith(k) or k.startswith(name):
            return v
    return ("#64748b", "Other")

def status_for(w):
    if w["_isoweek"] == CURRENT_ISO:
        return "current"
    return "past" if w["_isoweek"] < CURRENT_ISO else "future"

records = []
for w in d:
    c = COMPLETED.get(w["date"])
    records.append({
        "date": w["date"], "dow": w["_dow"], "nice": w["_nice"],
        "week": wkmap[w["_isoweek"]], "section": status_for(w),
        "name": w["name"], "type": meta(w["name"])[1], "color": meta(w["name"])[0],
        "intensity": w["intensity"], "splitRange": w["split_range"],
        "repRange": w.get("rep_time_range", ""), "dist": w.get("dist"),
        "dur": w.get("dur", ""), "reps": w.get("reps"), "rate": w.get("rate", ""),
        "rest": w.get("rest", ""), "desc": w["desc"], "test": w.get("test", False),
        "done": c if c else None,
    })

js_data = json.dumps(records, ensure_ascii=False)

def split_at(pct):
    s = 99.9 + (100 - pct); m = int(s // 60); return f"{m}:{(s-60*m):04.1f}"
zone_rows = "".join(f'<tr><td>{p}%</td><td>{split_at(p)}</td></tr>' for p in range(50, 121, 5))

synced_label = ("Last synced " + datetime.date.fromisoformat(LAST_SYNCED).strftime("%b %-d")) if LAST_SYNCED else "Not synced yet"

HTML = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rowing Plan · Pace Targets</title>
<style>
:root{{
  --bg:#0f172a; --panel:#1e293b; --panel2:#273449; --text:#e2e8f0; --muted:#94a3b8;
  --line:#334155; --accent:#38bdf8; --good:#22c55e;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:var(--bg);color:var(--text);line-height:1.5;padding:0 0 80px}}
header{{background:linear-gradient(135deg,#1e3a8a,#0c4a6e);padding:28px 24px;border-bottom:1px solid var(--line)}}
.wrap{{max-width:1100px;margin:0 auto;padding:0 20px}}
h1{{font-size:26px;font-weight:700;letter-spacing:-.3px}}
.sub{{color:#bae6fd;margin-top:6px;font-size:14px}}
.pbbar{{display:flex;gap:24px;flex-wrap:wrap;margin-top:16px;font-size:13px;color:#e0f2fe}}
.pbbar b{{color:#fff}}
.synced{{margin-top:14px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
.syncbtn{{background:var(--accent);color:#06283d;border:none;border-radius:9px;padding:9px 16px;
  font-weight:700;font-size:13px;cursor:pointer;display:inline-flex;align-items:center;gap:7px}}
.syncbtn:hover{{filter:brightness(1.08)}}
.synced .stamp{{font-size:12px;color:#bae6fd}}
.synchint{{font-size:11px;color:#7dd3fc;max-width:360px;margin-top:6px}}

.controls{{position:sticky;top:0;z-index:20;background:rgba(15,23,42,.92);backdrop-filter:blur(8px);
  border-bottom:1px solid var(--line);padding:12px 0}}
.filters{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
.chip{{border:1px solid var(--line);background:var(--panel);color:var(--text);padding:6px 13px;
  border-radius:999px;font-size:13px;cursor:pointer;transition:.15s;user-select:none}}
.chip:hover{{border-color:var(--accent)}}
.chip.active{{background:var(--accent);color:#0f172a;border-color:var(--accent);font-weight:600}}
.chip .dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}}

.week{{margin-top:26px}}
.wk-head{{display:flex;align-items:baseline;gap:12px;padding:0 0 10px;border-bottom:2px solid var(--line);margin-bottom:14px}}
.wk-num{{font-size:18px;font-weight:700;color:var(--accent)}}
.wk-dates{{color:var(--muted);font-size:14px}}
.wk-count{{margin-left:auto;color:var(--muted);font-size:13px}}
.now-pill{{background:var(--accent);color:#06283d;font-size:11px;font-weight:700;padding:2px 9px;border-radius:999px;text-transform:uppercase;letter-spacing:.4px}}

.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;
  border-left:5px solid var(--c);transition:.15s}}
.card:hover{{transform:translateY(-2px);border-color:var(--c)}}
.card.done{{border-left-color:var(--good)}}
.c-top{{padding:14px 16px 10px;position:relative}}
.c-day{{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}}
.c-name{{font-size:17px;font-weight:650;margin:3px 0 2px}}
.badge{{display:inline-block;font-size:11px;font-weight:600;padding:2px 9px;border-radius:999px;
  background:var(--c);color:#fff;margin-top:4px}}
.check{{position:absolute;top:14px;right:14px;width:26px;height:26px;border-radius:50%;
  background:var(--good);color:#06281a;display:flex;align-items:center;justify-content:center;
  font-weight:800;font-size:15px}}
.paces{{display:flex;gap:10px;padding:0 16px 14px;flex-wrap:wrap}}
.pace-box{{background:var(--panel2);border-radius:10px;padding:9px 12px;flex:1;min-width:120px}}
.pace-lbl{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px}}
.pace-val{{font-size:19px;font-weight:700;color:#fff;font-variant-numeric:tabular-nums;margin-top:2px}}
.pace-sub{{font-size:11px;color:var(--muted);margin-top:1px}}
.c-meta{{display:flex;gap:14px;padding:0 16px 12px;font-size:12px;color:var(--muted);flex-wrap:wrap}}
.c-meta b{{color:var(--text)}}

.result{{margin:0 16px 14px;background:rgba(34,197,94,.10);border:1px solid rgba(34,197,94,.35);
  border-radius:11px;padding:11px 13px}}
.result-hd{{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:700;color:var(--good);
  text-transform:uppercase;letter-spacing:.4px;margin-bottom:8px}}
.result-row{{display:flex;gap:10px;flex-wrap:wrap}}
.r-box{{flex:1;min-width:92px}}
.r-lbl{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.3px}}
.r-val{{font-size:17px;font-weight:700;color:#fff;font-variant-numeric:tabular-nums}}
.r-val.zone-in{{color:var(--good)}}
.r-extra{{margin-top:8px;font-size:12px;color:var(--muted)}}
.r-extra b{{color:var(--text)}}

.c-foot{{border-top:1px solid var(--line);padding:11px 16px 14px}}
.c-foot-lbl{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:5px}}
.c-desc{{font-size:13px;color:var(--muted);line-height:1.55}}

.archive-toggle{{margin-top:34px;width:100%;background:var(--panel);border:1px solid var(--line);
  color:var(--text);border-radius:12px;padding:14px 18px;font-size:15px;font-weight:600;cursor:pointer;
  display:flex;align-items:center;justify-content:space-between}}
.archive-toggle:hover{{border-color:var(--accent)}}
.archive-toggle .meta{{font-size:13px;color:var(--muted);font-weight:400}}
.archive-body{{display:none}}
.archive-body.open{{display:block}}
.arrow{{display:inline-block;transition:transform .2s}}
.arrow.up{{transform:rotate(180deg)}}

.aside{{position:fixed;right:18px;bottom:18px;z-index:30}}
.zonebtn{{background:var(--accent);color:#0f172a;border:none;border-radius:999px;padding:11px 18px;
  font-weight:700;font-size:14px;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.4)}}
.modal{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:40;align-items:center;justify-content:center;padding:20px}}
.modal.show{{display:flex}}
.modal-card{{background:var(--panel);border:1px solid var(--line);border-radius:16px;max-width:380px;width:100%;padding:22px;max-height:85vh;overflow:auto}}
.modal-card h3{{font-size:18px;margin-bottom:4px}}
.modal-card p{{color:var(--muted);font-size:13px;margin-bottom:14px}}
table.zone{{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}}
table.zone th,table.zone td{{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);font-size:14px}}
table.zone th{{color:var(--muted);font-size:12px;text-transform:uppercase}}
.closex{{float:right;color:var(--muted);cursor:pointer;font-size:20px;line-height:1}}
.empty{{text-align:center;color:var(--muted);padding:40px;font-size:15px}}
@media(max-width:560px){{ .grid{{grid-template-columns:1fr}} h1{{font-size:22px}} }}
</style></head>
<body>
<header><div class="wrap">
  <h1>🚣 Rowing Plan — Pace Targets</h1>
  <div class="sub">Non-strength sessions from HubFit, with target splits from your 500m PB, synced to your Concept2 logbook.</div>
  <div class="pbbar">
    <span>500m PB <b>1:39.9</b></span>
    <span><b>37</b> workouts</span>
    <span><b>12</b> weeks · Jun 8 – Aug 30</span>
    <span>Pace model: <b>conkers rowcalc</b></span>
  </div>
  <div class="synced">
    <button class="syncbtn" id="syncBtn"><span>⟳</span> Sync Concept2</button>
    <span class="stamp" id="syncStamp">{synced_label}</span>
  </div>
  <div class="synchint" id="syncHint"></div>
</div></header>

<div class="controls"><div class="wrap"><div class="filters" id="filters"></div></div></div>

<div class="wrap" id="current"></div>
<div class="wrap" id="upcoming"></div>
<div class="wrap" id="archiveWrap"></div>

<div class="aside"><button class="zonebtn" onclick="document.getElementById('zoneModal').classList.add('show')">Pace zones ⚡</button></div>
<div class="modal" id="zoneModal" onclick="if(event.target===this)this.classList.remove('show')">
  <div class="modal-card">
    <span class="closex" onclick="document.getElementById('zoneModal').classList.remove('show')">✕</span>
    <h3>Pace Zone Reference</h3>
    <p>Target 500m split at each % of your 1:39.9 PB. Higher % = harder/faster.</p>
    <table class="zone"><thead><tr><th>% of PB</th><th>500m split</th></tr></thead>
    <tbody>{zone_rows}</tbody></table>
  </div>
</div>

<script>
const DATA = {js_data};
const TYPES = [...new Set(DATA.map(d=>d.type))];
const TYPECOLOR = {{}}; DATA.forEach(d=>TYPECOLOR[d.type]=d.color);
let active = new Set(TYPES);

function renderFilters(){{
  const f=document.getElementById('filters'); f.innerHTML='';
  const all=document.createElement('div');
  all.className='chip'+(active.size===TYPES.length?' active':'');
  all.textContent='All';
  all.onclick=()=>{{active=new Set(TYPES);renderFilters();renderAll();}};
  f.appendChild(all);
  TYPES.forEach(t=>{{
    const c=document.createElement('div');
    c.className='chip'+(active.has(t)?' active':'');
    c.innerHTML=`<span class="dot" style="background:${{TYPECOLOR[t]}}"></span>${{t}}`;
    c.onclick=()=>{{ if(active.has(t)&&active.size===TYPES.length){{active=new Set([t]);}}
      else if(active.has(t)){{active.delete(t);}} else {{active.add(t);}}
      if(active.size===0)active=new Set(TYPES);
      renderFilters();renderAll();}};
    f.appendChild(c);
  }});
}}

function weekBlock(wk, items, isCurrent){{
  const sec=document.createElement('div'); sec.className='week';
  const all=DATA.filter(d=>d.week===wk);
  const nowPill = isCurrent?'<span class="now-pill">This week</span>':'';
  sec.innerHTML=`<div class="wk-head"><span class="wk-num">Week ${{wk}}</span> ${{nowPill}}
    <span class="wk-dates">${{all[0].nice}} – ${{all[all.length-1].nice}}</span>
    <span class="wk-count">${{items.length}} session${{items.length>1?'s':''}}</span></div>`;
  const grid=document.createElement('div'); grid.className='grid';
  items.forEach(w=>grid.appendChild(card(w)));
  sec.appendChild(grid);
  return sec;
}}

function renderSection(hostId, sectionName, currentFlag){{
  const host=document.getElementById(hostId); host.innerHTML='';
  const weeks=[...new Set(DATA.filter(d=>d.section===sectionName).map(d=>d.week))].sort((a,b)=>a-b);
  let shown=0;
  weeks.forEach(wk=>{{
    const items=DATA.filter(d=>d.week===wk && active.has(d.type));
    if(!items.length) return;
    shown+=items.length;
    host.appendChild(weekBlock(wk, items, currentFlag));
  }});
  return shown;
}}

function renderArchive(){{
  const host=document.getElementById('archiveWrap'); host.innerHTML='';
  const pastWeeks=[...new Set(DATA.filter(d=>d.section==='past').map(d=>d.week))].sort((a,b)=>b-a);
  const pastItems=DATA.filter(d=>d.section==='past');
  if(!pastItems.length) return;
  const doneCount=pastItems.filter(d=>d.done).length;
  const btn=document.createElement('button'); btn.className='archive-toggle';
  btn.innerHTML=`<span>📁 Archive · ${{pastWeeks.length}} past week${{pastWeeks.length>1?'s':''}}
    <span class="meta">(${{doneCount}}/${{pastItems.length}} completed)</span></span>
    <span class="arrow" id="archArrow">▾</span>`;
  const body=document.createElement('div'); body.className='archive-body'; body.id='archBody';
  pastWeeks.forEach(wk=>{{
    const items=DATA.filter(d=>d.week===wk && active.has(d.type));
    if(items.length) body.appendChild(weekBlock(wk, items, false));
  }});
  btn.onclick=()=>{{ body.classList.toggle('open'); document.getElementById('archArrow').classList.toggle('up'); }};
  host.appendChild(btn); host.appendChild(body);
}}

function renderAll(){{
  const c=renderSection('current','current',true);
  const u=renderSection('upcoming','future',false);
  renderArchive();
  if(c+u===0 && !DATA.some(d=>d.section==='past'&&active.has(d.type)))
    document.getElementById('upcoming').innerHTML='<div class="empty">No workouts match this filter.</div>';
}}

function card(w){{
  const el=document.createElement('div'); el.className='card'+(w.done?' done':''); el.style.setProperty('--c',w.color);
  const check = w.done?'<div class="check">✓</div>':'';
  const repBox = w.repRange ? `<div class="pace-box"><div class="pace-lbl">Per rep ${{w.dist?('· '+w.dist+'m'):''}}</div>
      <div class="pace-val">${{w.repRange}}</div><div class="pace-sub">target / interval</div></div>` : '';
  const structure = [
    w.reps?`<span><b>${{w.reps}}</b> ${{w.dist?('× '+w.dist+'m'):(w.dur?('× '+w.dur):'reps')}}</span>`:'',
    w.rate?`<span>Rate <b>${{w.rate}}</b> s/m</span>`:'',
    (w.rest && w.rest!=='—')?`<span>Rest <b>${{w.rest}}</b></span>`:'',
    `<span>Intensity <b>${{w.intensity[0]}}–${{w.intensity[1]}}%</b></span>`
  ].filter(Boolean).join('');

  let resultHtml='';
  if(w.done){{
    const dn=w.done;
    const zoneCls = dn.in_zone?'zone-in':'';
    const dateNice = new Date(dn.date_done+'T00:00').toLocaleDateString('en-US',{{month:'short',day:'numeric'}});
    resultHtml = `<div class="result">
      <div class="result-hd">✓ Completed · ${{dateNice}}</div>
      <div class="result-row">
        <div class="r-box"><div class="r-lbl">Actual split</div><div class="r-val ${{zoneCls}}">${{dn.actual_split}}</div></div>
        <div class="r-box"><div class="r-lbl">Target</div><div class="r-val">${{w.splitRange}}</div></div>
        <div class="r-box"><div class="r-lbl">Zone</div><div class="r-val ${{zoneCls}}">${{dn.in_zone?'In ✓':'Off'}}</div></div>
      </div>
      <div class="r-extra"><b>${{(dn.distance_m||0).toLocaleString()}}m</b> · <b>${{dn.time}}</b> · rate <b>${{dn.avg_rate}}</b> · <b>${{dn.calories}}</b> cal${{dn.actual_split_note?(' · '+dn.actual_split_note):''}}</div>
    </div>`;
  }}

  el.innerHTML=`
    <div class="c-top">${{check}}
      <div class="c-day">${{w.dow}} · ${{w.nice}}</div>
      <div class="c-name">${{w.name}}</div>
      <span class="badge">${{w.type}}</span>
    </div>
    <div class="paces">
      <div class="pace-box"><div class="pace-lbl">500m split</div>
        <div class="pace-val">${{w.splitRange}}</div><div class="pace-sub">${{w.intensity[1]}}% → ${{w.intensity[0]}}%</div></div>
      ${{repBox}}
    </div>
    <div class="c-meta">${{structure}}</div>
    ${{resultHtml}}
    <div class="c-foot"><div class="c-foot-lbl">Full workout</div><div class="c-desc">${{w.desc}}</div></div>`;
  return el;
}}

document.getElementById('syncBtn').onclick=function(){{
  if(typeof sendPrompt==='function'){{
    sendPrompt('Sync my rowing plan with my Concept2 logbook for this week, update the page, and re-push to GitHub.');
  }} else {{
    document.getElementById('syncHint').textContent='To sync: open this page inside Claude and say "sync my rowing plan". Your Concept2 results get matched, baked into the page, and re-published here.';
  }}
}};

renderFilters(); renderAll();
</script>
</body></html>"""

open("rowing_plan.html", "w").write(HTML)
print("wrote rowing_plan.html", len(HTML), "bytes")
