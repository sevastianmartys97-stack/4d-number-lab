from pathlib import Path
import sys

p=Path(__file__).resolve().parents[1]/"index.html"
marker="V4.7.3-SAFE-FINISHING"
if not p.exists():
    raise SystemExit("ERROR: index.html not found")
s=p.read_text(encoding="utf-8")
if marker in s:
    raise SystemExit("V4.7.3 already installed")

addon=r"""
<style>
/* V4.7.3-SAFE-FINISHING */
#v473bar{position:sticky;top:0;z-index:9000;display:flex;gap:8px;align-items:center;justify-content:space-between;padding:7px 9px;margin-bottom:8px;border:1px solid rgba(255,193,7,.3);border-radius:12px;background:rgba(3,15,28,.94);backdrop-filter:blur(10px);font-size:11px}
#v473bar .db{color:#9fb5c5;white-space:nowrap} #v473bar .res{color:#f6c84c;font-weight:800;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#v473load{display:none;position:fixed;inset:0;z-index:99999;align-items:center;justify-content:center;background:rgba(0,8,18,.38);pointer-events:none}
#v473load.on{display:flex} #v473load .box{padding:16px 20px;border-radius:16px;border:1px solid rgba(41,182,246,.45);background:rgba(3,20,35,.97);text-align:center}
#v473load .spin{width:27px;height:27px;margin:0 auto 9px;border:3px solid rgba(41,182,246,.18);border-top-color:#29b6f6;border-radius:50%;animation:v473s .8s linear infinite}
@keyframes v473s{to{transform:rotate(360deg)}} #v473load b{color:#e8f5ff} #v473load small{display:block;color:#8faabd;margin-top:4px}
#v473reset{border:1px solid rgba(255,82,82,.5);background:rgba(255,82,82,.1);color:#ff7777;border-radius:9px;padding:6px 8px;font-weight:800;font-size:10px}
</style>
<div id="v473load"><div class="box"><div class="spin"></div><b>Checking history...</b><small>Scanning market database</small></div></div>
<script>
(function(){
"use strict";
function T(e){return(e&&e.textContent||"").replace(/\s+/g," ").trim()}
function bar(){
 if(document.getElementById("v473bar"))return;
 var x=document.createElement("div");x.id="v473bar";
 x.innerHTML='<span class="db">DB: <b id="v473date">ready</b></span><span class="res" id="v473res">Ready</span><button id="v473reset" type="button">RESET</button>';
 var h=document.querySelector("header,.header,.app-header,.topbar");
 (h&&h.parentNode?h.parentNode:document.body).insertBefore(x,h?h.nextSibling:document.body.firstChild);
 document.getElementById("v473reset").onclick=function(){
  if(!confirm("Kosongkan Charta dan Favourite?"))return;
  document.querySelectorAll("input").forEach(function(i){
   if(i.maxLength===1||i.maxLength===4){i.value="";i.dispatchEvent(new Event("input",{bubbles:true}));i.dispatchEvent(new Event("change",{bubbles:true}))}
  });
  Array.from(document.querySelectorAll("button")).forEach(function(b){if(T(b).toUpperCase()==="CLEAR"&&b.id!=="v473reset")try{b.click()}catch(e){}})
 };
}
function update(){
 var d=document.getElementById("v473date"),r=document.getElementById("v473res");if(!d||!r)return;
 var dates=T(document.body).match(/20\d{2}[-\/]\d{2}[-\/]\d{2}/g)||[],best=null;
 dates.forEach(function(z){var m=z.match(/(20\d{2})[-\/](\d{2})[-\/](\d{2})/);if(m){var q=new Date(+m[1],+m[2]-1,+m[3]);if(!best||q>best)best=q}});
 d.textContent=best?String(best.getDate()).padStart(2,"0")+"/"+String(best.getMonth()+1).padStart(2,"0")+"/"+best.getFullYear():"ready";
 var body=T(document.body),hit=body.match(/\b(\d{4})\b[\s\S]{0,80}\b(EXACT|PUSINGAN)\b/i);
 r.textContent=hit?"★ "+hit[1]+" • "+hit[2].toUpperCase():"Ready";
 var v=document.querySelector(".version");if(v)v.textContent="V4.7.3 • STABLE FINISHING";
 document.title="4D Charta Analyzer V4.7.3";
}
function show(){var l=document.getElementById("v473load");if(!l)return;l.classList.add("on");clearTimeout(window.__v473);window.__v473=setTimeout(function(){l.classList.remove("on")},1000)}
document.addEventListener("DOMContentLoaded",function(){
 bar();update();
 document.addEventListener("input",function(e){if(e.target&&e.target.tagName==="INPUT"&&e.target.maxLength===4&&e.target.value.length===4)show()},true);
 var tm,mo=new MutationObserver(function(){clearTimeout(tm);tm=setTimeout(function(){update();var l=document.getElementById("v473load");if(l)l.classList.remove("on")},120)});
 mo.observe(document.body,{childList:true,subtree:true,characterData:true});
});
})();
</script>
"""
if "</body>" not in s: raise SystemExit("ERROR: closing body not found")
p.write_text(s.replace("</body>",addon+"\n</body>",1),encoding="utf-8")
print("V4.7.3 SAFE FINISHING APPLIED")
print("Core engines/data/updater were not replaced.")
