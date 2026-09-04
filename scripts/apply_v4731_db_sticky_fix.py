from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

if not INDEX.exists():
    raise SystemExit("ERROR: index.html tidak dijumpai")

text = INDEX.read_text(encoding="utf-8")

if "V4.7.3-SAFE-FINISHING" not in text:
    raise SystemExit("ERROR: V4.7.3 Safe Finishing belum dijumpai dalam index.html")

if "V4.7.3.1-DB-STICKY-FIX" in text:
    raise SystemExit("V4.7.3.1 sudah dipasang")

fix = r'''
<script>
/* V4.7.3.1-DB-STICKY-FIX */
(function(){
"use strict";

function clean(v){
  return (v || "").replace(/\s+/g," ").trim();
}

function fmtISO(v){
  if(!v) return null;
  const m=String(v).match(/(20\d{2})[-\/](\d{2})[-\/](\d{2})/);
  if(!m) return null;
  return m[3]+"/"+m[2]+"/"+m[1];
}

async function loadRealDbDate(){
  const badge=document.getElementById("v473date");
  if(!badge) return;

  const files=[
    "data/magnum.json",
    "data/toto.json",
    "data/damacai.json",
    "data/cashsweep.json"
  ];

  let best=null;

  for(const file of files){
    try{
      const res=await fetch(file+"?v="+Date.now(),{cache:"no-store"});
      if(!res.ok) continue;
      const db=await res.json();

      const candidates=[
        db.lastUpdated,
        db.historyCoverage && db.historyCoverage.newestDate
      ].filter(Boolean);

      for(const raw of candidates){
        const m=String(raw).match(/(20\d{2})[-\/](\d{2})[-\/](\d{2})/);
        if(!m) continue;
        const iso=m[1]+"-"+m[2]+"-"+m[3];
        if(!best || iso>best) best=iso;
      }
    }catch(e){}
  }

  badge.textContent=best ? fmtISO(best) : "ready";
}

function findAnalysisContainer(){
  const all=[...document.querySelectorAll("h1,h2,h3,h4,h5,h6,div,span,strong,b")];

  const title=all.find(el=>{
    const t=clean(el.textContent).toUpperCase();
    return t==="CHARTA HIT ANALYSIS" || t.startsWith("CHARTA HIT ANALYSIS ");
  });

  if(!title) return null;

  let box=title;
  for(let i=0;i<6 && box;i++,box=box.parentElement){
    const t=clean(box.textContent).toUpperCase();
    if(
      t.includes("CHARTA HIT ANALYSIS") &&
      (t.includes("EXACT") || t.includes("PUSINGAN") || t.includes("NO MATCH"))
    ){
      return box;
    }
  }

  return title.parentElement;
}

function updateStickyFromRealAnalysis(){
  const target=document.getElementById("v473res");
  if(!target) return;

  const box=findAnalysisContainer();

  if(!box){
    target.textContent="Ready";
    return;
  }

  const t=clean(box.textContent);
  const upper=t.toUpperCase();

  if(upper.includes("NO MATCH")){
    target.textContent="★ NO MATCH";
    return;
  }

  const typeMatch=upper.match(/\b(EXACT|PUSINGAN)\b/);
  if(!typeMatch){
    target.textContent="Ready";
    return;
  }

  let number=null;
  const patterns=[
    /BEST MATCH\s*[:\-]?\s*(\d{4})/i,
    /HIT NO\.?\s*[:\-]?\s*(\d{4})/i,
    /MATCH\s*[:\-]?\s*(\d{4})/i,
    /\b(\d{4})\b/
  ];

  for(const p of patterns){
    const m=t.match(p);
    if(m){ number=m[1]; break; }
  }

  if(!number){
    target.textContent="★ "+typeMatch[1].toUpperCase();
    return;
  }

  let pattern="";
  const pm=upper.match(/\b(STRAIGHT|ZIGZAG|BOX\/CORNER|L-SHAPE|REPEAT DIGIT PATH|SNAKE\/PATH)\b/);
  if(pm) pattern=" • "+pm[1];

  target.textContent="★ "+number+" • "+typeMatch[1].toUpperCase()+pattern;
}

function setVersion(){
  const v=document.querySelector(".version");
  if(v) v.textContent="V4.7.3.1 • STABLE FIX";
  document.title="4D Charta Analyzer V4.7.3.1";
}

document.addEventListener("DOMContentLoaded",function(){
  setTimeout(loadRealDbDate,100);
  setTimeout(updateStickyFromRealAnalysis,150);
  setVersion();

  let timer=null;
  const observer=new MutationObserver(function(){
    clearTimeout(timer);
    timer=setTimeout(function(){
      updateStickyFromRealAnalysis();
      setVersion();
    },160);
  });

  observer.observe(document.body,{
    childList:true,
    subtree:true,
    characterData:true
  });
});
})();
</script>
'''

if "</body>" not in text:
    raise SystemExit("ERROR: </body> tidak dijumpai")

text = text.replace("</body>", fix + "\n</body>", 1)
INDEX.write_text(text, encoding="utf-8")

print("V4.7.3.1 DB + STICKY FIX APPLIED ✓")
print("- DB badge now reads actual JSON lastUpdated/newestDate")
print("- Sticky result now reads only Charta Hit Analysis section")
print("- Auto Chart Pattern numbers will no longer be used")
print("- Core Charta/Pattern/Favourite/History/Updater untouched")
