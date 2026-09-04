from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MARKER = "V4.7.5-AUTO-PATTERN-EXPANSION"

if not INDEX.exists():
    raise SystemExit("ERROR: index.html tidak dijumpai")

text = INDEX.read_text(encoding="utf-8")

if MARKER in text:
    raise SystemExit("V4.7.5 sudah dipasang")

addon = r"""
<style>
/* V4.7.5-AUTO-PATTERN-EXPANSION */
.v475-perm-badge{
  display:inline-block;
  margin-left:6px;
  padding:2px 7px;
  border-radius:999px;
  font-size:10px;
  font-weight:900;
  vertical-align:2px;
  border:1px solid rgba(255,255,255,.08);
}
.v475-x24{background:rgba(78,200,255,.12);color:#66d4ff}
.v475-x12{background:rgba(246,200,76,.14);color:#ffd85e}
.v475-x6{background:rgba(66,223,135,.13);color:#6ef0a5}
.v475-x4{background:rgba(255,119,119,.13);color:#ff8a8a}

#v475RepeatBox{
  margin-top:12px;
  padding:12px;
  border:1px solid rgba(246,200,76,.26);
  border-radius:14px;
  background:rgba(4,19,31,.56);
}
#v475RepeatBox .v475-title{
  color:#eaf4fb;
  font-size:12px;
  font-weight:900;
  margin-bottom:4px;
}
#v475RepeatBox .v475-note{
  color:#829daf;
  font-size:10px;
  margin-bottom:10px;
  line-height:1.35;
}
#v475RepeatBox .v475-grid{
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:8px;
}
#v475RepeatBox .v475-item{
  background:rgba(7,27,42,.86);
  border:1px solid rgba(255,255,255,.05);
  border-radius:11px;
  padding:9px;
}
#v475RepeatBox .v475-item small{
  display:block;
  color:#829daf;
  margin-bottom:3px;
  font-size:9px;
}
#v475RepeatBox .v475-num{
  color:#f6c84c;
  font-weight:900;
  font-size:18px;
}
@media(max-width:700px){
  #v475RepeatBox .v475-grid{grid-template-columns:1fr 1fr 1fr}
  #v475RepeatBox .v475-num{font-size:16px}
}
</style>

<script>
/* V4.7.5-AUTO-PATTERN-EXPANSION */
(function(){
"use strict";

function clean(v){
  return (v||"").replace(/\s+/g," ").trim();
}

function fact(n){
  let r=1;
  for(let i=2;i<=n;i++) r*=i;
  return r;
}

function permCount(num){
  const f={};
  [...String(num)].forEach(d=>f[d]=(f[d]||0)+1);
  let den=1;
  Object.values(f).forEach(v=>den*=fact(v));
  return 24/den;
}

function badgeHtml(n){
  const c=permCount(n);
  return '<span class="v475-perm-badge v475-x'+c+'">×'+c+'</span>';
}

function findAutoPatternSection(){
  const all=[...document.querySelectorAll("div,section,article")];
  let best=null;

  for(const el of all){
    const t=clean(el.textContent).toUpperCase();
    if(!t.includes("AUTO CHART PATTERN")) continue;

    const nums=[...el.querySelectorAll("*")].filter(x=>{
      if(x.children.length) return false;
      return /^\d{4}$/.test(clean(x.textContent));
    });

    if(nums.length>=8 && (!best || el.textContent.length < best.textContent.length)){
      best=el;
    }
  }
  return best;
}

function labelDirectPatterns(section){
  if(!section) return;

  const leaves=[...section.querySelectorAll("*")].filter(el=>{
    if(el.children.length) return false;
    return /^\d{4}$/.test(clean(el.textContent));
  });

  const seen=new Set();

  for(const el of leaves){
    const n=clean(el.textContent);
    if(seen.has(el)) continue;
    seen.add(el);

    let parent=el.parentElement;
    if(!parent) continue;

    if(parent.querySelector(":scope > .v475-perm-badge")) continue;

    el.insertAdjacentHTML("afterend",badgeHtml(n));
  }
}

function getChartDigits(){
  const inputs=[...document.querySelectorAll("input")].filter(i=>{
    const v=String(i.value||"").trim();
    return /^\d$/.test(v) && (i.maxLength===1 || i.getAttribute("maxlength")==="1");
  });

  if(inputs.length>=16){
    return inputs.slice(0,16).map(i=>String(i.value).trim());
  }

  const possible=[...document.querySelectorAll(".chart-input")].map(i=>String(i.value||"").trim()).filter(v=>/^\d$/.test(v));
  if(possible.length>=16) return possible.slice(0,16);

  return [];
}

function buildCandidates(digits){
  if(digits.length<4) return null;

  const freq={};
  digits.forEach(d=>freq[d]=(freq[d]||0)+1);

  const ranked=Object.entries(freq)
    .sort((a,b)=>b[1]-a[1] || Number(a[0])-Number(b[0]))
    .map(x=>x[0]);

  if(ranked.length<3) return null;

  const a=ranked[0];
  const b=ranked[1];
  const c=ranked[2];

  return [
    {label:"×12 • AABC", number:a+a+b+c, desc:"1 pair sama"},
    {label:"×6 • AABB", number:a+a+b+b, desc:"2 pair"},
    {label:"×4 • AAAB", number:a+a+a+b, desc:"3 digit sama"}
  ];
}

function renderRepeatBox(section){
  if(!section) return;

  let box=document.getElementById("v475RepeatBox");
  if(!box){
    box=document.createElement("div");
    box.id="v475RepeatBox";
    section.appendChild(box);
  }

  const candidates=buildCandidates(getChartDigits());

  if(!candidates){
    box.innerHTML=
      '<div class="v475-title">REPEAT DIGIT EXPANSION</div>'+
      '<div class="v475-note">Isi penuh Charta 4×4 untuk jana contoh ×12 / ×6 / ×4.</div>';
    return;
  }

  box.innerHTML=
    '<div class="v475-title">REPEAT DIGIT EXPANSION</div>'+
    '<div class="v475-note">Berdasarkan digit paling kerap dalam Charta. Ini klasifikasi unique permutation, bukan probability menang.</div>'+
    '<div class="v475-grid">'+
    candidates.map(x=>
      '<div class="v475-item">'+
        '<small>'+x.label+' • '+x.desc+'</small>'+
        '<span class="v475-num">'+x.number+'</span>'+
        badgeHtml(x.number)+
      '</div>'
    ).join("")+
    '</div>';
}

function apply(){
  const section=findAutoPatternSection();
  if(!section) return;

  labelDirectPatterns(section);
  renderRepeatBox(section);

  const v=document.querySelector(".version");
  if(v) v.textContent="V4.7.5 • AUTO PATTERN EXPANSION";
  document.title="4D Charta Analyzer V4.7.5";
}

document.addEventListener("DOMContentLoaded",function(){
  setTimeout(apply,250);

  let timer=null;
  const mo=new MutationObserver(function(){
    clearTimeout(timer);
    timer=setTimeout(apply,180);
  });

  mo.observe(document.body,{
    childList:true,
    subtree:true,
    characterData:true
  });
});
})();
</script>
"""

if "</body>" not in text:
    raise SystemExit("ERROR: </body> tidak dijumpai")

text = text.replace("</body>", addon + "\n</body>", 1)
INDEX.write_text(text, encoding="utf-8")

print("V4.7.5 AUTO PATTERN EXPANSION APPLIED ✓")
print("- Direct Auto Chart Pattern now shows ×24/×12/×6/×4 badges")
print("- Repeat Digit Expansion adds example ×12/×6/×4 candidates")
print("- Existing Charta/Favourite/History/PWA/database/updater untouched")
