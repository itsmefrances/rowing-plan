/* Shared by block.html (the daily console) and coach.html (the programming
   overview). It was inline in block.html until the coach page needed the same
   schedule: two copies of a training plan is how a coach ends up reading a week
   the athlete is not running. applyPlyoTo(map) takes either page's sessions
   object, keyed by ISO date, each with an ex[] array. Safe to call twice. */
/* ---------- plyometric block · six weeks from her coach ----------
   The coach wrote this Tuesday-intensive / Thursday-extensive. It runs here as
   THURSDAY-intensive / SATURDAY-extensive instead, for one reason: Monday is a
   maximal erg, and both Tuesdays on record after one are her two lowest CMJ
   sessions of the block (17.90 and 18.87 against 19.50-19.80 on Thursdays and
   Saturdays). The erg cannot move - the squad runs it - so the jumps did.

   Coach weeks 1-2 are skipped, so weeks 3-4 run at the bottom of every range
   and the broad jumps start lower still. Broad jumps are the one item that
   loads a healing proximal hamstring tendon directly; they are titrated on
   their own, independent of everything else here.

   The extensive track pauses for ATHX on Oct 10 and resumes where it left off
   rather than skipping a step and landing on the heaviest week cold. */

function px(s, n, rx, sets, reps, rir, rest, mode){
  return {s:s, n:n, rx:rx, tier:2, plyo:mode,
          meta:{sets:sets, reps:reps, rir:rir, rest:rest, tier:2}};
}
var PLYO_INT_REST = "2:00–4:00";
var PLYO = {
  /* ---- intensive · Thursdays ---- */
  "2026-09-24": {mode:"int", wk:3, ex:[
    px("A","Seated box jump","3 × 5 · seat above 90° · jump for height, do not tuck — float to the box · box height (in) in Height",3,5,"max intent",PLYO_INT_REST,"int"),
    px("B","Seated vertical jump","5 × 3 · on the mat, no countermovement · shake out between reps · height (in) in Height",5,3,"max intent",PLYO_INT_REST,"int")
  ]},
  "2026-10-01": {mode:"int", wk:4, ex:[
    px("A","Seated box jump","3 × 5 · seat above 90° · float to the box · box height (in) in Height",3,5,"max intent",PLYO_INT_REST,"int"),
    px("B","Seated vertical jump","3 × 5 · on the mat · shake out between reps · height (in) in Height",3,5,"max intent",PLYO_INT_REST,"int")
  ]},
  "2026-10-08": {mode:"int", wk:5, ex:[
    px("A","Broad box jump","2 × 5 · vary distance from the box and box height rep to rep · trimmed — ATHX is Saturday",2,5,"max intent",PLYO_INT_REST,"int"),
    px("B","Vertical jump","2 × 3 · on the mat, full countermovement · height (in) in Height",2,3,"max intent",PLYO_INT_REST,"int")
  ]},
  "2026-10-15": {mode:"int", wk:6, ex:[
    px("A","Broad box jump","3 × 5 · vary distance from the box and box height rep to rep",3,5,"max intent",PLYO_INT_REST,"int"),
    px("B","Vertical jump","3 × 3 · on the mat, full countermovement · height (in) in Height",3,3,"max intent",PLYO_INT_REST,"int")
  ]},
  "2026-10-22": {mode:"int", wk:7, ex:[
    px("A","Broad jump","4 × 3 · single efforts, full reset between reps · distance (cm) in Height",4,3,"max intent",PLYO_INT_REST,"int"),
    px("B","Consecutive vertical jump","3 × 5 · continuous, no reset between reps · best height (in) in Height",3,5,"continuous",PLYO_INT_REST,"int")
  ]},
  "2026-10-29": {mode:"int", wk:8, ex:[
    px("A","Broad jump","5 × 3 · single efforts, full reset between reps · distance (cm) in Height",5,3,"max intent",PLYO_INT_REST,"int"),
    px("B","Consecutive vertical jump","3 × 5 · continuous, no reset between reps · best height (in) in Height",3,5,"continuous",PLYO_INT_REST,"int")
  ]},

  /* ---- extensive · Saturdays. Oct 10 is ATHX and has no entry. ---- */
  "2026-09-26": {mode:"ext", wk:3, ex:[
    px("A","Pogo hop","3 × 10 · stiff ankles, minimal knee bend, off the floor fast",3,10,"rhythmic","1:00","ext"),
    px("B","Consecutive jump squat","3 × 5 · bodyweight · bend generously, absorb and redirect",3,5,"rhythmic","1:30","ext"),
    px("C","Consecutive broad jump","2 × 5 · low effort, bounce rep to rep · turn around when you run out of room",2,5,"low effort","1:30","ext")
  ]},
  "2026-10-03": {mode:"ext", wk:4, ex:[
    px("A","Pogo hop","3 × 10 · stiff ankles, off the floor fast",3,10,"rhythmic","1:00","ext"),
    px("B","Consecutive jump squat","3 × 8 · bodyweight · rhythmic, no pause between reps",3,8,"rhythmic","1:30","ext"),
    px("C","Consecutive broad jump","3 × 5 · low effort, bounce rep to rep",3,5,"low effort","1:30","ext")
  ]},
  "2026-10-17": {mode:"ext", wk:5, ex:[
    px("A","Lateral pogo hop","3 × 5/side · over a plate, parallette or PVC on the floor",3,5,"rhythmic","1:00","ext"),
    px("B","Consecutive jump squat","3 × 5 · DBs at the sides or a bar on the back · still rhythmic",3,5,"rhythmic","1:30","ext"),
    px("C","Consecutive broad jump","2 × 10 · low effort, bounce rep to rep",2,10,"low effort","1:30","ext")
  ]},
  "2026-10-24": {mode:"ext", wk:6, ex:[
    px("A","Lateral pogo hop","4 × 5/side · over a plate, parallette or PVC on the floor",4,5,"rhythmic","1:00","ext"),
    px("B","Consecutive jump squat","3 × 5 · DBs at the sides or a bar on the back",3,5,"rhythmic","1:30","ext"),
    px("C","Consecutive broad jump","2 × 10 · low effort, bounce rep to rep",2,10,"low effort","1:30","ext")
  ]},
  "2026-10-31": {mode:"ext", wk:7, ex:[
    px("A","Consecutive forward hurdle hop","5 × 5 · low hurdle — a PVC pipe on the floor is enough",5,5,"rhythmic","1:30","ext")
  ]},
  "2026-11-07": {mode:"ext", wk:8, ex:[
    px("A","Consecutive forward hurdle hop","3 × 7 · low hurdle, continuous",3,7,"rhythmic","1:30","ext")
  ]}
};

/* Tuesdays lose the box jump: it is non-reactive, it is the same slot the new
   block occupies better, and Tuesday is the day she is least able to jump.
   Saturdays lose the transformer bar squat while extensive volume is high -
   bracing is the one thing that day has six other ways to buy. */
var PLYO_DROP = {
  "Box jump, step down": ["2026-09-22","2026-09-29","2026-10-06","2026-10-13",
                          "2026-10-20","2026-10-27","2026-11-03"],
  "Transformer bar squat": ["2026-09-26","2026-10-03","2026-10-17","2026-10-24"],
  /* From Oct 6 her own block opens Tuesday with a PAP contrast pair - pin squat
     at 80% into trap bar jumps, 12 loaded jumps a session. Running that beside
     the coach's Thursday would be two maximal jump days a week, one of them on
     the day she is least able to jump. Thursday keeps the jumping. */
  "Contrast pair": ["2026-10-06","2026-10-13","2026-10-20","2026-10-27"]
};

var PLYO_NOTE = {
  int: "Intensive jump day. The CMJ at the top is the readiness test, not training — three jumps, fresh, before anything else touches your legs, and a few low-effort jumps before those three so the test reads your readiness and not your warm-up. Working jumps log under their own names, which keeps the jump history a clean fresh-state series: numbers go in Height (inches for vertical and box, cm for broad), Weight stays empty unless you loaded it. Rest 2–4 minutes between sets and treat every rep as a single — a jump more than 10% off your best for the day means the set is over.",
  ext: "Extensive jump day. Volume, not intensity — rhythmic and fluid, no stutter between reps, knees bending generously to absorb and redirect. Nothing here should feel maximal. Log reps only and leave Height and Weight empty unless you loaded the jump squats. Broad jumps are the item to titrate against the hamstring: hold the low end until a week passes with no next-morning soreness at the origin."
};

/* Letters are positional, so anything inserted at the front has to renumber
   what follows. The special markers — the star single, the tests, the hang
   challenge — are not letters and keep whatever they carry. */
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
/* Runs after every block-plan merge, so it has to be safe to run twice. */
function applyPlyoTo(S){
  Object.keys(PLYO).forEach(function(dt){
    var s = S[dt], p = PLYO[dt];
    if(!s || !s.ex || s.plyo) return;
    /* A test goes first or it is not a test. The 7-stroke retest sits at the
       top of two of these Saturdays, and 25 hurdle hops in front of it would
       measure the hurdle hops. */
    var at = 0;
    while(at < s.ex.length && (s.ex[at].test || s.ex[at].s === "—")) at++;
    s.ex = s.ex.slice(0, at).concat(p.ex, s.ex.slice(at));
    if(p.mode === "int"){
      s.ex.forEach(function(x){
        /* One set off the hip thrust pays for the jumps that now open the day.
           The prescription changes shape across the block (3 × 10 in September,
           4 × 8 from October), so take a set off whatever it currently says
           rather than matching one spelling of it. */
        if(x.n === "Hip thrust") x.rx = x.rx.replace(/^([0-9]+)/, function(m){
          return String(Math.max(2, Number(m) - 1));
        });
      });
    }
    plyoRelabel(s.ex);
    s.plyo = p.mode;
    s.plyoWk = p.wk;
    s.note = (s.note ? s.note + "  " : "") + PLYO_NOTE[p.mode] +
             " (coach week " + p.wk + " of 8.)";
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
