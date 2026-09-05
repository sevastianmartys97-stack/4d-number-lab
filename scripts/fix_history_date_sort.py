from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MARKER = "HISTORY-DATE-SORT-FIX-V1"

if not INDEX.exists():
    raise SystemExit("ERROR: index.html tidak dijumpai")

s = INDEX.read_text(encoding="utf-8")

if MARKER in s:
    raise SystemExit("History Date Sort Fix sudah dipasang")

addon = r'''
<script>
/* HISTORY-DATE-SORT-FIX-V1 */
(function(){
"use strict";

function clean(v){
  return (v||"").replace(/\s+/g," ").trim();
}

function parseDateText(v){
  const t=clean(v);

  // yyyy-mm-dd
  let m=t.match(/(20\d{2})-(\d{2})-(\d{2})/);
  if(m) return new Date(+m[1],+m[2]-1,+m[3]).getTime();

  // dd/mm/yyyy
  m=t.match(/(\d{1,2})\/(\d{1,2})\/(20\d{2})/);
  if(m) return new Date(+m[3],+m[2]-1,+m[1]).getTime();

  return 0;
}

function sortHistoryTable(table){
  if(!table || table.dataset.historySortDone==="1") return;

  const head=table.querySelector("thead tr");
  if(!head) return;

  const headers=[...head.children].map(th=>clean(th.textContent).toUpperCase());
  const dateIndex=headers.findIndex(h=>h==="DATE" || h==="LATEST DATE");
  if(dateIndex<0) return;

  // Avoid top summary table; only detailed history tables.
  if(headers.includes("MARKET") && headers.includes("HIT NO.")) return;

  const tbody=table.querySelector("tbody");
  if(!tbody) return;

  const rows=[...tbody.querySelectorAll(":scope > tr")];
  if(rows.length<2) return;

  rows.sort((a,b)=>{
    const ad=parseDateText(a.children[dateIndex]?.textContent||"");
    const bd=parseDateText(b.children[dateIndex]?.textContent||"");
    return bd-ad;
  });

  rows.forEach(r=>tbody.appendChild(r));
  table.dataset.historySortDone="1";
}

function sortHistoryCards(){
  document.querySelectorAll("table").forEach(sortHistoryTable);
}

function sortLooseHistoryRows(){
  // Fallback for history lists that are not real <table>.
  const containers=[...document.querySelectorAll(".history-list,.history-results,.market-history,.history-card")];

  containers.forEach(box=>{
    if(box.dataset.historyLooseSort==="1") return;

    const kids=[...box.children];
    const dated=kids.filter(el=>parseDateText(el.textContent)>0);

    if(dated.length<2) return;

    dated.sort((a,b)=>parseDateText(b.textContent)-parseDateText(a.textContent));
    dated.forEach(el=>box.appendChild(el));
    box.dataset.historyLooseSort="1";
  });
}

function apply(){
  sortHistoryCards();
  sortLooseHistoryRows();
}

document.addEventListener("DOMContentLoaded",function(){
  setTimeout(apply,250);

  let timer=null;
  const mo=new MutationObserver(function(){
    clearTimeout(timer);
    timer=setTimeout(function(){
      // allow re-sort after rerender
      document.querySelectorAll("table[data-history-sort-done='1']").forEach(t=>t.removeAttribute("data-history-sort-done"));
      document.querySelectorAll("[data-history-loose-sort='1']").forEach(t=>t.removeAttribute("data-history-loose-sort"));
      apply();
    },180);
  });

  mo.observe(document.body,{
    childList:true,
    subtree:true
  });
});
})();
</script>
'''

if "</body>" not in s:
    raise SystemExit("ERROR: </body> tidak dijumpai")

s = s.replace("</body>", addon + "\n</body>", 1)
INDEX.write_text(s, encoding="utf-8")

print("History date sort fix applied ✓")
print("Version label/title unchanged.")
print("Only detailed history display order is affected.")
print("Newest date will appear first.")
