from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MARKER = "V4.7-MINIMAL-MOBILE"

if not INDEX.exists():
    print("ERROR: index.html tidak dijumpai.")
    sys.exit(1)

text = INDEX.read_text(encoding="utf-8")

if MARKER in text:
    print("V4.7 Minimal Mobile sudah dipasang. Tiada perubahan.")
    sys.exit(0)

css = r"""
/* =========================================================
   V4.7-MINIMAL-MOBILE
   UI ONLY — database/history/updater/settings untouched
   ========================================================= */

@media(max-width:1100px){

  body.v46-ui{
    padding-bottom:74px!important;
  }

  body.v46-ui .header{
    padding:10px 12px!important;
    margin-bottom:7px!important;
  }

  body.v46-ui .header h1{
    font-size:16px!important;
  }

  body.v46-ui .version{
    font-size:7px!important;
  }

  body.v46-ui .card,
  body.v46-ui .analysis-card,
  body.v46-ui .permutation-card,
  body.v46-ui .history-card{
    padding:8px!important;
    margin-bottom:7px!important;
    border-radius:12px!important;
  }

  body.v46-ui .chart-input{
    height:43px!important;
    font-size:20px!important;
  }

  body.v46-ui .charta-grid{
    gap:4px!important;
  }

  /* favourite list: compact, show only filled rows */
  body.v46-ui #favBody tr{
    padding:5px 6px!important;
    margin-bottom:4px!important;
    grid-template-columns:24px minmax(92px,1fr) 56px 26px!important;
  }

  body.v46-ui #favBody tr:not(.v47-filled-row){
    display:none!important;
  }

  body.v46-ui .fav-input{
    height:36px!important;
    font-size:17px!important;
  }

  /* add favourite control */
  .v47-add-wrap{
    display:flex;
    justify-content:center;
    margin-top:6px;
  }

  .v47-add-btn{
    min-height:34px;
    border-radius:9px;
    border:1px solid rgba(255,198,46,.42);
    background:rgba(255,198,46,.08);
    color:#ffd45c;
    padding:7px 13px;
    font-size:9px;
    font-weight:bold;
  }

  /* compact result */
  body.v46-ui .analysis-stack{
    grid-template-columns:repeat(3,1fr)!important;
    gap:4px!important;
  }

  body.v46-ui .analysis-box{
    min-height:55px!important;
    padding:6px 4px!important;
  }

  body.v46-ui .analysis-box:first-child{
    min-height:58px!important;
  }

  body.v46-ui .analysis-value.big{
    font-size:21px!important;
  }

  body.v46-ui .analysis-value{
    font-size:12px!important;
  }

  body.v46-ui .analysis-label{
    font-size:6px!important;
  }

  /* Pattern collapsed by default */
  body.v46-ui .pattern-panel{
    padding:8px!important;
    margin-top:6px!important;
  }

  .v47-pattern-toggle{
    width:100%;
    min-height:34px;
    border-radius:9px;
    border:1px solid rgba(255,198,46,.38);
    background:rgba(255,198,46,.07);
    color:#ffd75d;
    font-size:9px;
    font-weight:bold;
    margin-bottom:6px;
  }

  .v47-pattern-collapsed .pattern-grid-mini,
  .v47-pattern-collapsed .pattern-info{
    display:none!important;
  }

  /* permutation collapsed */
  .v47-collapsible-head{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:8px;
    min-height:34px;
    border-radius:9px;
    border:1px solid rgba(57,159,219,.28);
    background:rgba(7,27,43,.90);
    padding:6px 9px;
    color:#cde7f8;
    font-size:9px;
    font-weight:bold;
    margin-bottom:6px;
  }

  .v47-collapsible-head .state{
    color:#ffd45d;
  }

  body.v46-ui .permutation-card.v47-collapsed .permutation-list,
  body.v46-ui .permutation-card.v47-collapsed .big-number,
  body.v46-ui .permutation-card.v47-collapsed .copy-btn,
  body.v46-ui .permutation-card.v47-collapsed .subtitle{
    display:none!important;
  }

  /* History home summary only */
  body.v46-ui .history-card.v47-collapsed .market-wrap,
  body.v46-ui .history-card.v47-collapsed .table-scroll,
  body.v46-ui .history-card.v47-collapsed .history-market{
    display:none!important;
  }

  .v47-history-summary{
    display:grid;
    grid-template-columns:repeat(2,1fr);
    gap:5px;
    margin-top:6px;
  }

  .v47-history-chip{
    background:rgba(4,20,33,.9);
    border:1px solid rgba(68,155,212,.25);
    border-radius:8px;
    padding:7px;
    min-height:46px;
  }

  .v47-history-chip strong{
    display:block;
    color:#d8edf9;
    font-size:8px;
    margin-bottom:4px;
  }

  .v47-history-chip span{
    color:#38e77e;
    font-size:8px;
  }

  /* make Home short */
  body.v46-ui .coverage{
    display:none!important;
  }

  body.v46-ui .footer{
    margin-top:8px!important;
  }
}
"""

js = r"""
<script>
/* V4.7-MINIMAL-MOBILE */
document.addEventListener("DOMContentLoaded",function(){

  const version=document.querySelector(".version");
  if(version) version.textContent="V4.7 • MINIMAL MOBILE";

  const brand=document.querySelector(".footer-brand");
  if(brand) brand.textContent="4D CHARTA ANALYZER V4.7";

  function refreshFilledRows(){
    document.querySelectorAll("#favBody tr").forEach(tr=>{
      const input=tr.querySelector(".fav-input");
      if(!input) return;
      const filled=/^\d{1,4}$/.test((input.value||"").trim());
      tr.classList.toggle("v47-filled-row",filled);
    });
  }

  refreshFilledRows();

  document.addEventListener("input",function(e){
    if(e.target && e.target.classList.contains("fav-input")){
      refreshFilledRows();
    }
  });

  /* add favourite button */
  const favBody=document.getElementById("favBody");
  const favCard=favBody ? favBody.closest(".card") : null;

  if(favCard && !favCard.querySelector(".v47-add-wrap")){
    const wrap=document.createElement("div");
    wrap.className="v47-add-wrap";
    wrap.innerHTML='<button type="button" class="v47-add-btn">＋ ADD NUMBER</button>';

    const tableWrap=favBody.closest(".table-scroll") || favBody.parentElement;
    tableWrap.insertAdjacentElement("afterend",wrap);

    wrap.querySelector("button").addEventListener("click",function(){
      const rows=[...document.querySelectorAll("#favBody tr")];
      const hidden=rows.find(tr=>!tr.classList.contains("v47-filled-row"));

      if(!hidden){
        alert("Semua slot favourite sudah digunakan.");
        return;
      }

      hidden.classList.add("v47-filled-row");

      const input=hidden.querySelector(".fav-input");
      if(input){
        input.focus();
        hidden.scrollIntoView({behavior:"smooth",block:"center"});
      }
    });
  }

  /* pattern collapse */
  function setupPatternPanel(){
    const panel=document.querySelector(".pattern-panel");
    if(!panel || panel.querySelector(".v47-pattern-toggle")) return;

    const btn=document.createElement("button");
    btn.type="button";
    btn.className="v47-pattern-toggle";
    btn.textContent="LIHAT PATTERN ▼";

    panel.insertBefore(btn,panel.firstChild);
    panel.classList.add("v47-pattern-collapsed");

    btn.addEventListener("click",function(){
      const collapsed=panel.classList.toggle("v47-pattern-collapsed");
      btn.textContent=collapsed ? "LIHAT PATTERN ▼" : "TUTUP PATTERN ▲";
    });
  }

  setupPatternPanel();

  const observer=new MutationObserver(function(){
    refreshFilledRows();
    setupPatternPanel();
  });

  observer.observe(document.body,{
    childList:true,
    subtree:true
  });

  /* permutation collapse */
  const perm=document.querySelector(".permutation-card");

  if(perm && !perm.querySelector(".v47-collapsible-head")){
    const head=document.createElement("button");
    head.type="button";
    head.className="v47-collapsible-head";
    head.innerHTML='<span>PERMUTATION</span><span class="state">SHOW ▼</span>';

    perm.insertBefore(head,perm.firstChild);
    perm.classList.add("v47-collapsed");

    head.addEventListener("click",function(){
      const collapsed=perm.classList.toggle("v47-collapsed");
      head.querySelector(".state").textContent=collapsed ? "SHOW ▼" : "HIDE ▲";
    });
  }

  /* history summary / collapse */
  const history=document.querySelector(".history-card");

  if(history && !history.querySelector(".v47-collapsible-head")){
    const head=document.createElement("button");
    head.type="button";
    head.className="v47-collapsible-head";
    head.innerHTML='<span>MARKET HISTORY</span><span class="state">SHOW ▼</span>';

    history.insertBefore(head,history.firstChild);
    history.classList.add("v47-collapsed");

    const summary=document.createElement("div");
    summary.className="v47-history-summary";

    const names=["Sports Toto","Magnum","Da Ma Cai","Cash Sweep"];
    const coverage=[...document.querySelectorAll(".coverage-item")];

    names.forEach((name,i)=>{
      let txt="History available";
      if(coverage[i]){
        txt=coverage[i].textContent.replace(/\s+/g," ").trim();
      }

      const chip=document.createElement("div");
      chip.className="v47-history-chip";
      chip.innerHTML="<strong>"+name+"</strong><span>"+txt+"</span>";
      summary.appendChild(chip);
    });

    head.insertAdjacentElement("afterend",summary);

    head.addEventListener("click",function(){
      const collapsed=history.classList.toggle("v47-collapsed");
      head.querySelector(".state").textContent=collapsed ? "SHOW ▼" : "HIDE ▲";
      summary.style.display=collapsed ? "grid" : "none";
    });
  }

  console.log("4D Charta Analyzer V4.7 Minimal Mobile UI loaded ✓");
});
</script>
"""

if "</style>" not in text:
    print("ERROR: </style> tidak dijumpai.")
    sys.exit(1)

text = text.replace("</style>", css + "\n</style>", 1)

if "</body>" not in text:
    print("ERROR: </body> tidak dijumpai.")
    sys.exit(1)

text = text.replace("</body>", js + "\n</body>", 1)

text = text.replace("<title>4D Charta Analyzer V4.6.1</title>",
                    "<title>4D Charta Analyzer V4.7</title>")
text = text.replace("<title>4D Charta Analyzer V4.6</title>",
                    "<title>4D Charta Analyzer V4.7</title>")

INDEX.write_text(text, encoding="utf-8")

print("V4.7 MINIMAL MOBILE APPLIED ✓")
print("UI only.")
print("Database/history/updater/localStorage logic untouched.")
