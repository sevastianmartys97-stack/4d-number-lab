from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
SW = ROOT / "sw.js"
MARKER = "V5.0-STABLE-CONSOLIDATED"

if not INDEX.exists():
    raise SystemExit("ERROR: index.html tidak dijumpai")

s = INDEX.read_text(encoding="utf-8")
if MARKER in s:
    raise SystemExit("V5.0 STABLE sudah dipasang")

# Remove only known temporary/superseded injected blocks.
patterns = [
    r'<script>\s*/\*\s*V4\.7\.2-HISTORY-POSITION-FIRST\s*\*/.*?</script>',
    r'<style>\s*/\*\s*V4\.7\.3-SAFE-FINISHING\s*\*/.*?</style>',
    r'<script>\s*/\*\s*V4\.7\.3\.1-DB-STICKY-FIX\s*\*/.*?</script>',
    r'<style>\s*/\*\s*V4\.7\.3\.2-CLEAN-FIX\s*\*/.*?</style>',
    r'<script>\s*/\*\s*V4\.7\.3\.2-CLEAN-FIX\s*\*/.*?</script>',
    r'<style>\s*/\*\s*V4\.7\.4-PWA\s*\*/.*?</style>',
    r'<script>\s*/\*\s*V4\.7\.4-PWA\s*\*/.*?</script>',
    r'<style>\s*/\*\s*V4\.7\.5-AUTO-PATTERN-EXPANSION\s*\*/.*?</style>',
    r'<script>\s*/\*\s*V4\.7\.5-AUTO-PATTERN-EXPANSION\s*\*/.*?</script>'
]
for pat in patterns:
    s = re.sub(pat, "", s, flags=re.S)

s = re.sub(r'<div id="v473load".*?</div>\s*</div>', '', s, flags=re.S)
s = re.sub(r'<div id="v473bar".*?</div>', '', s, flags=re.S)
s = re.sub(r'<button id="pwaInstallBtn".*?</button>', '', s, flags=re.S)
s = re.sub(r'<div id="v475RepeatBox".*?</div>', '', s, flags=re.S)

# Static title/version to V5.
s = re.sub(r'<title>.*?</title>', '<title>4D Charta Analyzer V5.0</title>', s, count=1, flags=re.S)
s = re.sub(
    r'(<div[^>]*class=["\'][^"\']*\bversion\b[^"\']*["\'][^>]*>).*?(</div>)',
    r'\1V5.0 • STABLE\2',
    s,
    count=1,
    flags=re.S
)

addon = r'''
<style>
/* V5.0-STABLE-CONSOLIDATED */
#v5TopBar{position:sticky;top:0;z-index:9000;display:flex;align-items:center;justify-content:space-between;gap:8px;padding:7px 10px;margin:0 0 8px;border:1px solid rgba(255,193,7,.30);border-radius:12px;background:rgba(3,15,28,.94);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);font-size:11px}
#v5TopBar .db{color:#9fb5c5;white-space:nowrap}
#v5TopBar .res{color:#f6c84c;font-weight:800;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v5Reset{border:1px solid rgba(255,82,82,.50);background:rgba(255,82,82,.10);color:#ff7777;border-radius:9px;padding:6px 8px;font-weight:800;font-size:10px}
#v5Install{display:none;position:fixed;right:14px;bottom:82px;z-index:9998;border:1px solid rgba(246,200,76,.55);background:rgba(3,20,35,.96);color:#f6c84c;border-radius:14px;padding:10px 13px;font-weight:800;font-size:12px;box-shadow:0 10px 30px rgba(0,0,0,.28)}
#v5Install.show{display:block}
@media(display-mode:standalone){#v5Install{display:none!important}}
.v5PermBadge{display:inline-block;margin-left:6px;padding:2px 7px;border-radius:999px;font-size:10px;font-weight:900;vertical-align:2px;border:1px solid rgba(255,255,255,.08)}
.v5x24{background:rgba(78,200,255,.12);color:#66d4ff}.v5x12{background:rgba(246,200,76,.14);color:#ffd85e}.v5x6{background:rgba(66,223,135,.13);color:#6ef0a5}.v5x4{background:rgba(255,119,119,.13);color:#ff8a8a}
#v5Repeat{margin-top:12px;padding:12px;border:1px solid rgba(246,200,76,.26);border-radius:14px;background:rgba(4,19,31,.56)}
#v5Repeat .ttl{font-size:12px;font-weight:900;margin-bottom:4px}
#v5Repeat .note{color:#829daf;font-size:10px;line-height:1.35;margin-bottom:9px}
#v5Repeat .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
#v5Repeat .item{background:rgba(7,27,42,.86);border:1px solid rgba(255,255,255,.05);border-radius:11px;padding:9px}
#v5Repeat small{display:block;color:#829daf;font-size:9px;margin-bottom:3px}
#v5Repeat .num{color:#f6c84c;font-weight:900;font-size:17px}
</style>

<button id="v5Install" type="button">👑 INSTALL APP</button>

<script>
/* V5.0-STABLE-CONSOLIDATED */
(function(){
"use strict";
const VERSION="V5.0 • STABLE";
function clean(v){return(v||"").replace(/\s+/g," ").trim()}
function setVersion(){const v=document.querySelector(".version");if(v)v.textContent=VERSION;document.title="4D Charta Analyzer V5.0"}

function ensureTopBar(){
  if(document.getElementById("v5TopBar"))return;
  const bar=document.createElement("div");
  bar.id="v5TopBar";
  bar.innerHTML='<span class="db">DB: <b id="v5Db">loading...</b></span><span class="res" id="v5Result">Ready</span><button id="v5Reset" type="button">RESET</button>';
  const app=document.querySelector(".app"),header=document.querySelector(".header");
  if(app&&header)app.insertBefore(bar,header.nextSibling);else if(app)app.insertBefore(bar,app.firstChild);else document.body.insertBefore(bar,document.body.firstChild);
  document.getElementById("v5Reset").onclick=function(){
    if(!confirm("Kosongkan Charta dan Favourite?"))return;
    document.querySelectorAll(".chart-input,.fav-input").forEach(i=>{i.value="";i.dispatchEvent(new Event("input",{bubbles:true}));i.dispatchEvent(new Event("change",{bubbles:true}))});
    const clear=[...document.querySelectorAll("button")].find(b=>clean(b.textContent).toUpperCase()==="CLEAR");
    if(clear)try{clear.click()}catch(e){}
  };
}

function formatDate(raw){const m=String(raw||"").match(/(20\d{2})[-\/](\d{2})[-\/](\d{2})/);return m?m[3]+"/"+m[2]+"/"+m[1]:null}
async function loadDbDate(){
  const el=document.getElementById("v5Db");if(!el)return;
  const files=["magnum","toto","damacai","cashsweep"];let latest="";
  for(const name of files){
    try{
      const r=await fetch("data/"+name+".json",{cache:"no-store"});if(!r.ok)continue;
      const db=await r.json();
      [db.lastUpdated,db.historyCoverage&&db.historyCoverage.newestDate].filter(Boolean).forEach(raw=>{
        const m=String(raw).match(/(20\d{2})[-\/](\d{2})[-\/](\d{2})/);if(!m)return;
        const iso=m[1]+"-"+m[2]+"-"+m[3];if(!latest||iso>latest)latest=iso;
      });
    }catch(e){}
  }
  el.textContent=latest?formatDate(latest):"unavailable";
}

function getAnalysisCard(){return [...document.querySelectorAll(".analysis-card,.card")].find(card=>clean(card.textContent).toUpperCase().includes("CHARTA HIT ANALYSIS"))||null}
function updateTopResult(){
  const out=document.getElementById("v5Result");if(!out)return;
  const card=getAnalysisCard();if(!card){out.textContent="Ready";return}
  const t=clean(card.textContent),u=t.toUpperCase();
  if(u.includes("NO MATCH")){out.textContent="★ NO MATCH";return}
  const type=(u.match(/\b(EXACT|PUSINGAN)\b/)||[])[1];if(!type){out.textContent="Ready";return}
  let num=null;const best=card.querySelector(".best,.analysis-value.big");
  if(best){const m=clean(best.textContent).match(/\b\d{4}\b/);if(m)num=m[0]}
  if(!num){const m=t.match(/BEST MATCH\s*[:\-]?\s*(\d{4})/i);if(m)num=m[1]}
  out.textContent=num?"★ "+num+" • "+type:"★ "+type;
}

function fact(n){let r=1;for(let i=2;i<=n;i++)r*=i;return r}
function permCount(n){const f={};[...String(n)].forEach(d=>f[d]=(f[d]||0)+1);let den=1;Object.values(f).forEach(v=>den*=fact(v));return 24/den}
function badge(n){const c=permCount(n);return '<span class="v5PermBadge v5x'+c+'">×'+c+'</span>'}

function autoSection(){
  const all=[...document.querySelectorAll("div,section,article")];let best=null;
  all.forEach(el=>{
    const t=clean(el.textContent).toUpperCase();if(!t.includes("AUTO CHART PATTERN"))return;
    const nums=[...el.querySelectorAll("*")].filter(x=>!x.children.length&&/^\d{4}$/.test(clean(x.textContent)));
    if(nums.length>=8&&(!best||el.textContent.length<best.textContent.length))best=el;
  });
  return best;
}

function chartDigits(){const a=[...document.querySelectorAll(".chart-input")].map(i=>String(i.value||"").trim()).filter(v=>/^\d$/.test(v));return a.length>=16?a.slice(0,16):[]}
function updateAutoExpansion(){
  const sec=autoSection();if(!sec)return;
  [...sec.querySelectorAll("*")].filter(el=>!el.children.length&&/^\d{4}$/.test(clean(el.textContent))).forEach(el=>{
    if(el.nextElementSibling&&el.nextElementSibling.classList.contains("v5PermBadge"))return;
    el.insertAdjacentHTML("afterend",badge(clean(el.textContent)));
  });
  let box=document.getElementById("v5Repeat");if(!box){box=document.createElement("div");box.id="v5Repeat";sec.appendChild(box)}
  const digits=chartDigits();
  if(digits.length<16){box.innerHTML='<div class="ttl">REPEAT DIGIT EXPANSION</div><div class="note">Isi penuh Charta 4×4 untuk jana ×12 / ×6 / ×4.</div>';return}
  const f={};digits.forEach(d=>f[d]=(f[d]||0)+1);
  const ranked=Object.entries(f).sort((a,b)=>b[1]-a[1]||Number(a[0])-Number(b[0])).map(x=>x[0]);if(ranked.length<3)return;
  const a=ranked[0],b=ranked[1],c=ranked[2];
  const rows=[["×12 • AABC",a+a+b+c,"1 pair sama"],["×6 • AABB",a+a+b+b,"2 pair"],["×4 • AAAB",a+a+a+b,"3 digit sama"]];
  box.innerHTML='<div class="ttl">REPEAT DIGIT EXPANSION</div><div class="note">Berdasarkan digit paling kerap dalam Charta. Unique permutation, bukan probability menang.</div><div class="grid">'+rows.map(x=>'<div class="item"><small>'+x[0]+' • '+x[2]+'</small><span class="num">'+x[1]+'</span>'+badge(x[1])+'</div>').join("")+'</div>';
}

function setupPWA(){
  let deferred=null;const btn=document.getElementById("v5Install");
  if("serviceWorker" in navigator)window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js").catch(()=>{}));
  window.addEventListener("beforeinstallprompt",e=>{e.preventDefault();deferred=e;if(btn)btn.classList.add("show")});
  if(btn)btn.onclick=async()=>{if(!deferred)return;deferred.prompt();try{await deferred.userChoice}catch(e){}deferred=null;btn.classList.remove("show")};
  window.addEventListener("appinstalled",()=>{if(btn)btn.classList.remove("show");deferred=null});
}

function apply(){setVersion();ensureTopBar();updateTopResult();updateAutoExpansion()}
document.addEventListener("DOMContentLoaded",()=>{
  apply();loadDbDate();setupPWA();
  let timer=null;
  const mo=new MutationObserver(()=>{clearTimeout(timer);timer=setTimeout(apply,160)});
  mo.observe(document.body,{childList:true,subtree:true,characterData:true});
});
})();
</script>
'''

if "</body>" not in s:
    raise SystemExit("ERROR: </body> tidak dijumpai")
s = s.replace("</body>", addon + "\n</body>", 1)

if 'rel="manifest"' not in s:
    head = '''
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#030f1c">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="4D Charta">
<link rel="apple-touch-icon" href="icons/icon-192.png">
'''
    s = s.replace("</head>", head + "\n</head>", 1)

INDEX.write_text(s, encoding="utf-8")

if SW.exists():
    sw = SW.read_text(encoding="utf-8")
    sw = re.sub(r'const CACHE\s*=\s*["\'][^"\']+["\']', 'const CACHE = "4d-charta-v500"', sw, count=1)
    SW.write_text(sw, encoding="utf-8")

print("V5.0 STABLE CONSOLIDATION COMPLETE ✓")
print("Core engine/database/history/favourite logic preserved.")
print("Known V4.7.2-V4.7.5 add-on layers consolidated into one V5 layer.")
