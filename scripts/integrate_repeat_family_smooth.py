from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

OLD_MARKER = "REPEAT-FAMILY-PLUS-V1"
NEW_MARKER = "REPEAT-FAMILY-INTEGRATED-V2"

if not INDEX.exists():
    raise SystemExit("ERROR: index.html tidak dijumpai")

s = INDEX.read_text(encoding="utf-8")

if NEW_MARKER in s:
    raise SystemExit("Integrated Repeat Family V2 sudah dipasang")

s = re.sub(
    r'<style>\s*/\*\s*REPEAT-FAMILY-PLUS-V1\s*\*/.*?</style>\s*',
    '',
    s,
    flags=re.S
)
s = re.sub(
    r'<script>\s*/\*\s*REPEAT-FAMILY-PLUS-V1\s*\*/.*?</script>\s*',
    '',
    s,
    flags=re.S
)

addon = r'''
<style>
/* REPEAT-FAMILY-INTEGRATED-V2 */
#repeatFamilyIntegrated{
  margin-top:10px;padding:11px;border:1px solid rgba(218,177,57,.34);
  border-radius:12px;background:rgba(7,25,38,.66)
}
#repeatFamilyIntegrated .rfi-head{
  display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:4px
}
#repeatFamilyIntegrated .rfi-title{
  font-size:11px;font-weight:800;letter-spacing:.45px;color:#f0c44c
}
#repeatFamilyIntegrated .rfi-count{font-size:9px;color:#7f96a7}
#repeatFamilyIntegrated .rfi-sub{font-size:9px;color:#8095a6;margin-bottom:8px}
#repeatFamilyIntegrated .rfi-grid{
  display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px
}
#repeatFamilyIntegrated .rfi-card{
  min-width:0;padding:8px;border:1px solid #234258;border-radius:10px;background:#091e2c
}
#repeatFamilyIntegrated .rfi-card.hot{border-color:rgba(218,177,57,.46)}
#repeatFamilyIntegrated .rfi-type{
  font-size:8px;color:#7f96a7;white-space:nowrap;overflow:hidden;text-overflow:ellipsis
}
#repeatFamilyIntegrated .rfi-num{
  font-size:18px;font-weight:900;color:#f1c348;margin:3px 0
}
#repeatFamilyIntegrated .rfi-meta{font-size:8px;color:#8ea3b2}
#repeatFamilyIntegrated details{margin-top:6px}
#repeatFamilyIntegrated summary{
  cursor:pointer;font-size:8px;color:#8eacc0;list-style:none
}
#repeatFamilyIntegrated summary::-webkit-details-marker{display:none}
#repeatFamilyIntegrated .rfi-perms{
  display:flex;flex-wrap:wrap;gap:3px;margin-top:5px
}
#repeatFamilyIntegrated .rfi-chip{
  font-size:8px;padding:3px 5px;border-radius:6px;
  background:#102b3d;color:#c8dbe7;border:1px solid #21455c
}
@media(max-width:520px){
  #repeatFamilyIntegrated{padding:9px}
  #repeatFamilyIntegrated .rfi-grid{gap:4px}
  #repeatFamilyIntegrated .rfi-card{padding:7px}
  #repeatFamilyIntegrated .rfi-num{font-size:16px}
}
</style>

<script>
/* REPEAT-FAMILY-INTEGRATED-V2 */
(function(){
"use strict";

let mountedHost = null;
let lastSig = "";

function perms4(v){
  const out = new Set();
  function go(pre, rest){
    if(!rest.length){ out.add(pre); return; }
    for(let i=0;i<rest.length;i++){
      go(pre + rest[i], rest.slice(0,i) + rest.slice(i+1));
    }
  }
  go("", v);
  return [...out];
}

function chartDigits(){
  try{
    const raw = localStorage.getItem("4dChartaV42");
    if(raw){
      let parsed;
      try{ parsed = JSON.parse(raw); }catch(e){ parsed = raw; }

      let flat = [];
      if(Array.isArray(parsed)) flat = parsed.flat(Infinity);
      else if(parsed && typeof parsed === "object") flat = Object.values(parsed).flat(Infinity);
      else flat = String(parsed).split("");

      const ds = flat.map(x=>String(x)).join("").match(/\d/g) || [];
      if(ds.length >= 16) return ds.slice(0,16);
    }
  }catch(e){}

  const visible = [...document.querySelectorAll("input")]
    .filter(i => i.offsetParent !== null && /^\d$/.test((i.value||"").trim()));

  if(visible.length >= 16){
    return visible.slice(0,16).map(i => i.value.trim());
  }

  return [];
}

function repeats(ds){
  const count = {};
  ds.forEach(d => count[d] = (count[d]||0)+1);
  return Object.entries(count)
    .filter(([,n]) => n >= 2)
    .sort((a,b) => b[1]-a[1] || Number(a[0])-Number(b[0]));
}

function findExpansionTitle(){
  const nodes = [...document.querySelectorAll("h1,h2,h3,h4,h5,p,span,div")];
  return nodes.find(el => (el.textContent||"").trim().toUpperCase() === "REPEAT DIGIT EXPANSION");
}

function findExpansionBox(title){
  if(!title) return null;
  let node = title;
  for(let i=0;i<5 && node;i++,node=node.parentElement){
    if(!node || node === document.body) break;
    const text = (node.textContent||"").toUpperCase();
    if(text.includes("REPEAT DIGIT EXPANSION") && node.children.length >= 2){
      return node;
    }
  }
  return title.parentElement || title;
}

function ensureHost(){
  if(mountedHost && document.body.contains(mountedHost)) return mountedHost;

  const existing = document.getElementById("repeatFamilyIntegrated");
  if(existing){
    mountedHost = existing;
    return mountedHost;
  }

  const title = findExpansionTitle();
  if(!title) return null;

  const box = findExpansionBox(title);
  if(!box) return null;

  const host = document.createElement("div");
  host.id = "repeatFamilyIntegrated";
  box.appendChild(host);

  mountedHost = host;
  return host;
}

function card(num, type, hot){
  const ps = perms4(num);
  return `<div class="rfi-card ${hot?"hot":""}">
    <div class="rfi-type">${type}</div>
    <div class="rfi-num">${num}</div>
    <div class="rfi-meta">${ps.length} pusingan unik</div>
    <details>
      <summary>LIHAT PUSINGAN ›</summary>
      <div class="rfi-perms">${ps.map(x=>`<span class="rfi-chip">${x}</span>`).join("")}</div>
    </details>
  </div>`;
}

function render(force){
  const host = ensureHost();
  if(!host) return false;

  const ds = chartDigits();
  const sig = ds.join("");

  if(!force && sig === lastSig) return true;
  lastSig = sig;

  const rs = repeats(ds);

  if(rs.length < 2){
    host.innerHTML = `
      <div class="rfi-head">
        <div class="rfi-title">REPEAT FAMILY+</div>
      </div>
      <div class="rfi-sub">Menunggu sekurang-kurangnya 2 digit berulang dalam Charta.</div>`;
    return true;
  }

  const [a,ca] = rs[0];
  const [b,cb] = rs[1];
  const cards = [];

  if(ca >= 3) cards.push(card(a+a+a+b, `TRIPLE ${a} • AAAB`, true));
  if(cb >= 3) cards.push(card(b+b+b+a, `TRIPLE ${b} • AAAB`, true));
  cards.push(card(a+a+b+b, `DOUBLE + DOUBLE • AABB`, false));

  host.innerHTML = `
    <div class="rfi-head">
      <div class="rfi-title">REPEAT FAMILY+</div>
      <div class="rfi-count">${a} ×${ca} • ${b} ×${cb}</div>
    </div>
    <div class="rfi-sub">Auto ikut digit berulang dalam Charta. Expansion asal kekal.</div>
    <div class="rfi-grid">${cards.slice(0,3).join("")}</div>`;

  return true;
}

function boot(){
  let tries = 0;
  const starter = setInterval(function(){
    tries++;
    if(render(true) || tries >= 20){
      clearInterval(starter);
    }
  }, 50);

  document.addEventListener("input", function(){
    requestAnimationFrame(()=>render(false));
  }, true);

  document.addEventListener("change", function(){
    requestAnimationFrame(()=>render(false));
  }, true);

  window.addEventListener("storage", function(e){
    if(e.key === "4dChartaV42") requestAnimationFrame(()=>render(true));
  });

  setInterval(function(){
    render(false);
  }, 1200);
}

if(document.readyState === "loading"){
  document.addEventListener("DOMContentLoaded", boot, {once:true});
}else{
  boot();
}
})();
</script>
'''

if "</body>" not in s:
    raise SystemExit("ERROR: </body> tidak dijumpai")

s = s.replace("</body>", addon + "\n</body>", 1)
INDEX.write_text(s, encoding="utf-8")

print("Integrated Repeat Family V2 applied ✓")
print("Old Family+ observer patch removed ✓")
print("Repeat Digit Expansion asal dikekalkan ✓")
print("No heavy MutationObserver ✓")
print("Version label unchanged ✓")
