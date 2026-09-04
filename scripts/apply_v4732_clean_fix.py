from pathlib import Path
import re

INDEX = Path(__file__).resolve().parents[1] / "index.html"
if not INDEX.exists():
    raise SystemExit("ERROR: index.html tidak dijumpai")

s = INDEX.read_text(encoding="utf-8")

# Remove old V4.7.3 finishing pieces if they exist.
s = re.sub(r'<style>\s*/\*\s*V4\.7\.3-SAFE-FINISHING\s*\*/.*?</style>', '', s, flags=re.S)
s = re.sub(r'<script>\s*/\*\s*V4\.7\.3\.1-DB-STICKY-FIX\s*\*/.*?</script>', '', s, flags=re.S)
s = re.sub(r'<div id="v473load".*?</div>\s*</div>', '', s, flags=re.S)
s = re.sub(r'<script>\s*\(function\(\)\{\s*"use strict";.*?V4\.7\.3.*?</script>', '', s, count=1, flags=re.S)

if "V4.7.3.2-CLEAN-FIX" in s:
    raise SystemExit("V4.7.3.2 sudah dipasang")

addon = r'''
<style>
/* V4.7.3.2-CLEAN-FIX */
#v473bar{
  position:sticky;top:0;z-index:9000;
  display:flex;align-items:center;justify-content:space-between;
  gap:8px;padding:7px 10px;margin-bottom:8px;
  border:1px solid rgba(255,193,7,.30);border-radius:12px;
  background:rgba(3,15,28,.94);backdrop-filter:blur(10px);
  font-size:11px
}
#v473bar .db{color:#9fb5c5;white-space:nowrap}
#v473bar .res{color:#f6c84c;font-weight:800;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v473reset{
  border:1px solid rgba(255,82,82,.5);
  background:rgba(255,82,82,.10);color:#ff7777;
  border-radius:9px;padding:6px 8px;font-weight:800;font-size:10px
}
</style>

<script>
/* V4.7.3.2-CLEAN-FIX */
(function(){
"use strict";

function clean(v){return (v||"").replace(/\s+/g," ").trim();}

function ensureBar(){
  if(document.getElementById("v473bar")) return;

  const bar=document.createElement("div");
  bar.id="v473bar";
  bar.innerHTML=
    '<span class="db">DB: <b id="v473date">loading...</b></span>'+
    '<span class="res" id="v473res">Ready</span>'+
    '<button id="v473reset" type="button">RESET</button>';

  const app=document.querySelector(".app");
  const header=document.querySelector(".header");

  if(app && header) app.insertBefore(bar,header.nextSibling);
  else if(app) app.insertBefore(bar,app.firstChild);
  else document.body.insertBefore(bar,document.body.firstChild);

  document.getElementById("v473reset").addEventListener("click",function(){
    if(!confirm("Kosongkan Charta dan Favourite?")) return;

    document.querySelectorAll(".chart-input,.fav-input").forEach(function(i){
      i.value="";
      i.dispatchEvent(new Event("input",{bubbles:true}));
      i.dispatchEvent(new Event("change",{bubbles:true}));
    });

    const clear=[...document.querySelectorAll("button")].find(function(b){
      return clean(b.textContent).toUpperCase()==="CLEAR";
    });
    if(clear) try{clear.click()}catch(e){}
  });
}

function formatDate(raw){
  const m=String(raw||"").match(/(20\d{2})[-\/](\d{2})[-\/](\d{2})/);
  return m ? m[3]+"/"+m[2]+"/"+m[1] : null;
}

async function updateDb(){
  const el=document.getElementById("v473date");
  if(!el) return;

  const files=[
    "data/magnum.json",
    "data/toto.json",
    "data/damacai.json",
    "data/cashsweep.json"
  ];

  let latest="";

  for(const file of files){
    try{
      const r=await fetch(file,{cache:"no-store"});
      if(!r.ok) continue;
      const db=await r.json();

      const candidates=[
        db.lastUpdated,
        db.historyCoverage && db.historyCoverage.newestDate
      ].filter(Boolean);

      candidates.forEach(function(raw){
        const m=String(raw).match(/(20\d{2})[-\/](\d{2})[-\/](\d{2})/);
        if(!m) return;
        const iso=m[1]+"-"+m[2]+"-"+m[3];
        if(!latest || iso>latest) latest=iso;
      });
    }catch(e){}
  }

  el.textContent=latest ? formatDate(latest) : "unavailable";
}

function getAnalysisCard(){
  const cards=[...document.querySelectorAll(".analysis-card,.card")];
  for(const card of cards){
    const t=clean(card.textContent).toUpperCase();
    if(t.includes("CHARTA HIT ANALYSIS")) return card;
  }
  return null;
}

function updateResult(){
  const out=document.getElementById("v473res");
  if(!out) return;

  const card=getAnalysisCard();
  if(!card){
    out.textContent="Ready";
    return;
  }

  const t=clean(card.textContent);
  const u=t.toUpperCase();

  if(u.includes("NO MATCH")){
    out.textContent="★ NO MATCH";
    return;
  }

  const type=(u.match(/\b(EXACT|PUSINGAN)\b/)||[])[1];
  if(!type){
    out.textContent="Ready";
    return;
  }

  let number=null;
  const best=card.querySelector(".best,.analysis-value.big");

  if(best){
    const m=clean(best.textContent).match(/\b\d{4}\b/);
    if(m) number=m[0];
  }

  if(!number){
    const m=t.match(/BEST MATCH\s*[:\-]?\s*(\d{4})/i);
    if(m) number=m[1];
  }

  out.textContent=number ? "★ "+number+" • "+type : "★ "+type;
}

function setVersion(){
  const v=document.querySelector(".version");
  if(v) v.textContent="V4.7.3.2 • CLEAN FIX";
  document.title="4D Charta Analyzer V4.7.3.2";
}

document.addEventListener("DOMContentLoaded",function(){
  ensureBar();
  setVersion();
  updateDb();
  updateResult();

  let timer=null;
  const mo=new MutationObserver(function(){
    clearTimeout(timer);
    timer=setTimeout(function(){
      updateResult();
      setVersion();
    },120);
  });
  mo.observe(document.body,{childList:true,subtree:true,characterData:true});
});
})();
</script>
'''

if "</body>" not in s:
    raise SystemExit("ERROR: </body> tidak dijumpai")

s = s.replace("</body>", addon + "\n</body>", 1)
INDEX.write_text(s, encoding="utf-8")

print("V4.7.3.2 CLEAN FIX APPLIED ✓")
print("Old V4.7.3 bug layer removed where found.")
print("DB badge reads JSON directly.")
print("Sticky result reads Charta Hit Analysis only.")
print("Core engine/history/database/updater untouched.")
