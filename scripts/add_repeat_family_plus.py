from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MARKER = "REPEAT-FAMILY-PLUS-V1"

if not INDEX.exists():
    raise SystemExit("ERROR: index.html tidak dijumpai")

s = INDEX.read_text(encoding="utf-8")
if MARKER in s:
    raise SystemExit("Repeat Family+ sudah dipasang")

addon = r"""
<style>
/* REPEAT-FAMILY-PLUS-V1 */
#repeatFamilyPlus{
  margin-top:10px;padding:12px;border:1px solid rgba(218,177,57,.38);
  border-radius:14px;background:rgba(7,25,38,.72)
}
#repeatFamilyPlus .rf-head{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:4px}
#repeatFamilyPlus .rf-title{font-size:12px;font-weight:800;letter-spacing:.5px;color:#f0c44c}
#repeatFamilyPlus .rf-sub{font-size:10px;color:#8095a6;margin-bottom:9px}
#repeatFamilyPlus .rf-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}
#repeatFamilyPlus .rf-card{min-width:0;padding:9px;border:1px solid #24445a;border-radius:11px;background:#091e2c}
#repeatFamilyPlus .rf-card.primary{border-color:rgba(218,177,57,.48)}
#repeatFamilyPlus .rf-type{font-size:9px;color:#7f96a7}
#repeatFamilyPlus .rf-num{font-size:19px;font-weight:900;color:#f1c348;margin:3px 0}
#repeatFamilyPlus .rf-meta{font-size:9px;color:#8ea3b2}
#repeatFamilyPlus details{margin-top:7px}
#repeatFamilyPlus summary{cursor:pointer;font-size:9px;color:#8eacc0;list-style:none}
#repeatFamilyPlus summary::-webkit-details-marker{display:none}
#repeatFamilyPlus .rf-perms{display:flex;flex-wrap:wrap;gap:4px;margin-top:6px}
#repeatFamilyPlus .rf-chip{font-size:9px;padding:3px 6px;border-radius:7px;background:#102b3d;color:#c8dbe7;border:1px solid #21455c}
@media(max-width:520px){
  #repeatFamilyPlus .rf-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:5px}
  #repeatFamilyPlus{padding:10px}
  #repeatFamilyPlus .rf-card{padding:7px}
  #repeatFamilyPlus .rf-num{font-size:17px}
}
</style>

<script>
/* REPEAT-FAMILY-PLUS-V1 */
(function(){
"use strict";

function perms4(v){
  const out=new Set();
  function go(pre,rest){
    if(!rest.length){out.add(pre);return;}
    for(let i=0;i<rest.length;i++){
      go(pre+rest[i],rest.slice(0,i)+rest.slice(i+1));
    }
  }
  go("",v);
  return [...out];
}

function readChartDigits(){
  // Preferred: same persistent Charta used by the app.
  try{
    const raw=localStorage.getItem("4dChartaV42");
    if(raw){
      let v;
      try{ v=JSON.parse(raw); }catch(e){ v=raw; }
      let flat=[];
      if(Array.isArray(v)) flat=v.flat(Infinity);
      else if(v && typeof v==="object") flat=Object.values(v).flat(Infinity);
      else flat=String(v).split("");
      const ds=flat.map(x=>String(x)).join("").match(/\d/g)||[];
      if(ds.length>=16) return ds.slice(0,16);
    }
  }catch(e){}

  // Fallback: visible one-digit chart inputs.
  const inputs=[...document.querySelectorAll("input")]
    .filter(i=>i.offsetParent!==null && /^\d$/.test((i.value||"").trim()));
  if(inputs.length>=16) return inputs.slice(0,16).map(i=>i.value.trim());
  return [];
}

function getTopRepeats(ds){
  const c={};
  ds.forEach(d=>c[d]=(c[d]||0)+1);
  return Object.entries(c)
    .filter(([,n])=>n>=2)
    .sort((a,b)=>b[1]-a[1] || Number(a[0])-Number(b[0]));
}

function locateExpansion(){
  const els=[...document.querySelectorAll("div,section,h2,h3,h4,p,span")];
  return els.find(el=>{
    const t=(el.textContent||"").trim().toUpperCase();
    return t==="REPEAT DIGIT EXPANSION";
  });
}

function cardHTML(num,type,primary){
  const ps=perms4(num);
  return `<div class="rf-card ${primary?"primary":""}">
    <div class="rf-type">${type}</div>
    <div class="rf-num">${num}</div>
    <div class="rf-meta">${ps.length} pusingan unik</div>
    <details><summary>LIHAT PUSINGAN ›</summary>
      <div class="rf-perms">${ps.map(x=>`<span class="rf-chip">${x}</span>`).join("")}</div>
    </details>
  </div>`;
}

function render(){
  const anchor=locateExpansion();
  if(!anchor) return;

  let host=document.getElementById("repeatFamilyPlus");
  if(!host){
    host=document.createElement("div");
    host.id="repeatFamilyPlus";

    // Put directly after the existing Expansion container when possible.
    const box=anchor.closest("section, .card, .panel, .glass-card, .expansion, div");
    const target=(box && box!==document.body) ? box : anchor;
    target.insertAdjacentElement("afterend",host);
  }

  const ds=readChartDigits();
  const reps=getTopRepeats(ds);

  if(reps.length<2){
    host.innerHTML=`<div class="rf-head"><div class="rf-title">REPEAT FAMILY+</div></div>
      <div class="rf-sub">Perlu sekurang-kurangnya 2 digit berulang untuk bina keluarga repeat.</div>`;
    return;
  }

  // Use the two strongest repeat digits only: compact and easy to read.
  const [a,ca]=reps[0], [b,cb]=reps[1];
  const cards=[];

  if(ca>=3) cards.push(cardHTML(a+a+a+b,`TRIPLE ${a} • AAAB`,true));
  if(cb>=3) cards.push(cardHTML(b+b+b+a,`TRIPLE ${b} • AAAB`,true));

  // Always show the balanced family for the two strongest repeat digits.
  cards.push(cardHTML(a+a+b+b,`DOUBLE + DOUBLE • AABB`,false));

  host.innerHTML=`
    <div class="rf-head">
      <div class="rf-title">REPEAT FAMILY+</div>
      <div class="rf-meta">${a} ×${ca} • ${b} ×${cb}</div>
    </div>
    <div class="rf-sub">Tambahan keluarga repeat. Repeat Digit Expansion asal tidak diubah.</div>
    <div class="rf-grid">${cards.slice(0,3).join("")}</div>`;
}

document.addEventListener("DOMContentLoaded",function(){
  setTimeout(render,350);
  let tm=null;
  new MutationObserver(function(){
    clearTimeout(tm); tm=setTimeout(render,180);
  }).observe(document.body,{childList:true,subtree:true});
  document.addEventListener("input",function(){clearTimeout(tm);tm=setTimeout(render,120)},true);
});
})();
</script>
"""

if "</body>" not in s:
    raise SystemExit("ERROR: </body> tidak dijumpai")

s = s.replace("</body>", addon + "\n</body>", 1)
INDEX.write_text(s, encoding="utf-8")

print("Repeat Family+ installed ✓")
print("Existing Repeat Digit Expansion preserved ✓")
print("Version label unchanged ✓")
