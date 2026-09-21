/* Shared by block.html (the daily console) and coach.html (the programming
   overview). Two copies of a training plan is how a coach ends up reading a
   week the athlete is not running, so the schedule lives here once.
   applyPlyoTo(map) takes either page's sessions object, keyed by ISO date,
   and is safe to call twice. */

/* ---------- plyometric block · six weeks from her jump coach ----------
   Intensive days are paired with the week's other maximal work, on the
   coach's instruction: "the high intensity jumps should be paired with other
   CNS intensive movements, so either Olympic lifting or true sprint efforts."
   She does no Olympic lifting, so the pairing is Monday's sprint erg - jumps
   first, fresh off a rest day, then the piece. That also removes the reason
   they were first moved off Tuesday: both Tuesdays on record after a maximal
   Monday erg were her two lowest CMJ sessions (17.90 and 18.87 in, against
   19.50-19.80 on other days).

   Week 3 stays on the Thursday it was already set for, as the bridge; the
   Monday pattern starts 28 Sep. Extensive work sits on Thursday, three days
   after, close to the coach's original Tuesday-to-Thursday spacing.

   Coach weeks 1-2 were not run, so weeks 3-4 take the low end of every range
   and the broad jumps start lower still - they load a healing proximal
   hamstring tendon directly and are titrated on their own.

   Two Mondays are erg tests (5 and 19 Oct): the jumps drop to two sets and
   still go first, as a primer. Thursday 8 Oct is 48 hours before ATHX, so the
   extensive track pauses there and resumes where it left off. */

function px(s, n, rx, sets, reps, rir, rest, mode){
  return {s:s, n:n, rx:rx, tier:2, plyo:mode,
          meta:{sets:sets, reps:reps, rir:rir, rest:rest, tier:2}};
}
var PLYO_INT_REST = "2:00–4:00";
var PLYO = {
  /* ---- intensive ---- */
  "2026-09-24": {mode:"int", wk:3, ex:[
    px("A","Seated box jump","3 × 5 · seat above 90° · jump for height, do not tuck — float to the box · box height (in) in Height",3,5,"max intent",PLYO_INT_REST,"int"),
    px("B","Seated vertical jump","5 × 3 · on the mat, no countermovement · shake out between reps · height (in) in Height",5,3,"max intent",PLYO_INT_REST,"int")
  ]},
  "2026-09-28": {mode:"int", wk:4, ex:[
    px("A","Seated box jump","3 × 5 · seat above 90° · float to the box · box height (in) in Height",3,5,"max intent",PLYO_INT_REST,"int"),
    px("B","Seated vertical jump","3 × 5 · on the mat · shake out between reps · height (in) in Height",3,5,"max intent",PLYO_INT_REST,"int")
  ]},
  "2026-10-05": {mode:"int", wk:5, ex:[
    px("A","Broad box jump","2 × 5 · vary distance from the box and box height rep to rep · trimmed — erg test today",2,5,"max intent",PLYO_INT_REST,"int"),
    px("B","Vertical jump","2 × 3 · on the mat, full countermovement · height (in) in Height · trimmed — erg test today",2,3,"max intent",PLYO_INT_REST,"int")
  ]},
  "2026-10-12": {mode:"int", wk:6, ex:[
    px("A","Broad box jump","3 × 5 · vary distance from the box and box height rep to rep",3,5,"max intent",PLYO_INT_REST,"int"),
    px("B","Vertical jump","3 × 3 · on the mat, full countermovement · height (in) in Height",3,3,"max intent",PLYO_INT_REST,"int")
  ]},
  "2026-10-19": {mode:"int", wk:7, ex:[
    px("A","Broad jump","2 × 3 · single efforts, full reset between reps · distance (cm) in Height · trimmed — erg test today",2,3,"max intent",PLYO_INT_REST,"int"),
    px("B","Consecutive vertical jump","2 × 5 · continuous, no reset between reps · best height (in) in Height · trimmed — erg test today",2,5,"continuous",PLYO_INT_REST,"int")
  ]},
  "2026-10-26": {mode:"int", wk:8, ex:[
    px("A","Broad jump","5 × 3 · single efforts, full reset between reps · distance (cm) in Height",5,3,"max intent",PLYO_INT_REST,"int"),
    px("B","Consecutive vertical jump","3 × 5 · continuous, no reset between reps · best height (in) in Height",3,5,"continuous",PLYO_INT_REST,"int")
  ]},

  /* ---- extensive. Thu 8 Oct is two days before ATHX and has no entry. ---- */
  "2026-09-26": {mode:"ext", wk:3, ex:[
    px("A","Pogo hop","3 × 10 · stiff ankles, minimal knee bend, off the floor fast",3,10,"rhythmic","1:00","ext"),
    px("B","Consecutive jump squat","3 × 5 · bodyweight · bend generously, absorb and redirect",3,5,"rhythmic","1:30","ext"),
    px("C","Consecutive broad jump","2 × 5 · low effort, bounce rep to rep · turn around when you run out of room",2,5,"low effort","1:30","ext")
  ]},
  "2026-10-01": {mode:"ext", wk:4, ex:[
    px("A","Pogo hop","3 × 10 · stiff ankles, off the floor fast",3,10,"rhythmic","1:00","ext"),
    px("B","Consecutive jump squat","3 × 8 · bodyweight · rhythmic, no pause between reps",3,8,"rhythmic","1:30","ext"),
    px("C","Consecutive broad jump","3 × 5 · low effort, bounce rep to rep",3,5,"low effort","1:30","ext")
  ]},
  "2026-10-15": {mode:"ext", wk:5, ex:[
    px("A","Lateral pogo hop","3 × 5/side · over a plate, parallette or PVC on the floor",3,5,"rhythmic","1:00","ext"),
    px("B","Consecutive jump squat","3 × 5 · DBs at the sides or a bar on the back · still rhythmic",3,5,"rhythmic","1:30","ext"),
    px("C","Consecutive broad jump","2 × 10 · low effort, bounce rep to rep",2,10,"low effort","1:30","ext")
  ]},
  "2026-10-22": {mode:"ext", wk:6, ex:[
    px("A","Lateral pogo hop","4 × 5/side · over a plate, parallette or PVC on the floor",4,5,"rhythmic","1:00","ext"),
    px("B","Consecutive jump squat","3 × 5 · DBs at the sides or a bar on the back",3,5,"rhythmic","1:30","ext"),
    px("C","Consecutive broad jump","2 × 10 · low effort, bounce rep to rep",2,10,"low effort","1:30","ext")
  ]},
  "2026-10-29": {mode:"ext", wk:7, ex:[
    px("A","Consecutive forward hurdle hop","5 × 5 · low hurdle — a PVC pipe on the floor is enough",5,5,"rhythmic","1:30","ext")
  ]},
  "2026-11-05": {mode:"ext", wk:8, ex:[
    px("A","Consecutive forward hurdle hop","3 × 7 · low hurdle, continuous",3,7,"rhythmic","1:30","ext")
  ]}
};

/* What her own programming gives up. Tuesday's box jump is non-reactive and
   now sits the day after the week's max-intent jumping. The Tuesday contrast
   pair (pin squat into trap bar jumps, 12 loaded jumps) would make a second
   maximal jump day 24 hours after Monday. The transformer bar squat goes only
   on the one Saturday that still carries extensive volume. */
var PLYO_DROP = {
  "Box jump, step down": ["2026-09-22","2026-09-29"],
  "Transformer bar squat": ["2026-09-26"],
  "Contrast pair": ["2026-10-06","2026-10-13","2026-10-20","2026-10-27"]
};

var PLYO_NOTE = {
  int: "Intensive jump day. The CMJ at the top is the readiness test, not training — three jumps, fresh, before anything else touches your legs, and a few low-effort jumps before those three so the test reads your readiness and not your warm-up. Working jumps log under their own names, which keeps the jump history a clean fresh-state series: numbers go in Height (inches for vertical and box, cm for broad), Weight stays empty unless you loaded it. Rest 2–4 minutes between sets and treat every rep as a single — a jump more than 10% off your best for the day means the set is over.",
  ext: "Extensive jump day. Volume, not intensity — rhythmic and fluid, no stutter between reps, knees bending generously to absorb and redirect. Nothing here should feel maximal. Log reps only and leave Height and Weight empty unless you loaded the jump squats. Broad jumps are the item to titrate against the hamstring: hold the low end until a week passes with no next-morning soreness at the origin."
};
var PLYO_ERG_LEAD = "Jumps first, then the sprint piece — the pairing is the point: the week's max-intent work on one fresh day. Finish the last jump 10–15 minutes before the first hard stroke and run the normal erg warm-up in between. ";

/* Letters are positional, so anything inserted has to renumber what follows.
   The special markers — the star single, the tests, the hang challenge — are
   not letters and keep whatever they carry. */
function plyoRelabel(ex){
  var alpha = "ABCDEFGHIJKLMN", i = 0;
  ex.forEach(function(x){
    if(!/^[A-N]$/.test(x.s || "")) return;
    x.s = alpha.charAt(i++) || "-";
  });
}
function plyoDrop(S, dt, name){
  var s = S[dt];
  if(!s || !s.ex) return false;
  var before = s.ex.length;
  s.ex = s.ex.filter(function(x){ return x.n !== name; });
  if(s.ex.length === before) return false;
  plyoRelabel(s.ex);
  return true;
}
function applyPlyoTo(S){
  Object.keys(PLYO).forEach(function(dt){
    var s = S[dt], p = PLYO[dt];
    if(!s || s.plyo) return;
    if(s.kind !== "lift" && s.kind !== "erg") return;
    var base = s.ex || [];
    /* a test goes first or it is not a test */
    var at = 0;
    while(at < base.length && (base[at].test || base[at].s === "—")) at++;
    s.ex = base.slice(0, at).concat(p.ex, base.slice(at));
    /* one set off the hip thrust pays for the jumps that now share the day;
       the prescription changes shape across the block, so take a set off
       whatever it currently says */
    s.ex.forEach(function(x){
      if(x.n === "Hip thrust") x.rx = x.rx.replace(/^([0-9]+)/, function(m){
        return String(Math.max(2, Number(m) - 1));
      });
    });
    plyoRelabel(s.ex);
    s.plyo = p.mode;
    s.plyoWk = p.wk;
    if(p.mode === "int") s.gate = true;
    s.note = (s.note ? s.note + "  " : "") + (s.kind === "erg" ? PLYO_ERG_LEAD : "") +
             PLYO_NOTE[p.mode] + " (coach week " + p.wk + " of 8.)";
  });
  Object.keys(PLYO_DROP).forEach(function(name){
    PLYO_DROP[name].forEach(function(dt){
      var s = S[dt];
      if(!s || s.plyoDropped && s.plyoDropped[name]) return;
      if(plyoDrop(S, dt, name)){
        if(!s.plyoDropped) s.plyoDropped = {};
        s.plyoDropped[name] = true;
      }
    });
  });
}
