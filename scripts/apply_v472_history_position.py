from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MARKER = "V4.7.2-HISTORY-POSITION-FIRST"

if not INDEX.exists():
    print("ERROR: index.html tidak dijumpai.")
    sys.exit(1)

text = INDEX.read_text(encoding="utf-8")

if MARKER in text:
    print("V4.7.2 History Position First sudah dipasang.")
    sys.exit(0)

js = r"""
<script>
/* V4.7.2-HISTORY-POSITION-FIRST
   UI only: swap POSITION with LATEST DATE in MARKET HISTORY CHECK.
   Data/history engine unchanged.
*/
document.addEventListener("DOMContentLoaded",function(){

  function normalizeHeader(txt){
    return (txt || "")
      .replace(/\s+/g," ")
      .trim()
      .toUpperCase();
  }

  function swapCells(row,a,b){
    const cells=[...row.children];
    if(a<0 || b<0 || a>=cells.length || b>=cells.length) return;

    const A=cells[a];
    const B=cells[b];

    const marker=document.createComment("swap-marker");
    row.insertBefore(marker,A);
    row.insertBefore(A,B);
    row.insertBefore(B,marker);
    marker.remove();
  }

  function reorderMarketHistoryCheck(){
    const tables=[...document.querySelectorAll("table")];

    for(const table of tables){
      const headers=[...table.querySelectorAll("thead th")];
      if(!headers.length) continue;

      const names=headers.map(h=>normalizeHeader(h.textContent));

      const latestIndex=names.findIndex(x=>x==="LATEST DATE");
      const positionIndex=names.findIndex(x=>x==="POSITION");

      if(latestIndex===-1 || positionIndex===-1) continue;

      /* Target only the MARKET HISTORY CHECK summary table.
         It normally also contains HIT NO. and TYPE. */
      const hasHit=names.some(x=>x==="HIT NO." || x==="HIT NO");
      const hasType=names.some(x=>x==="TYPE");

      if(!hasHit || !hasType) continue;

      if(table.dataset.v472Done==="1") continue;

      /* swap header */
      swapCells(table.querySelector("thead tr"), latestIndex, positionIndex);

      /* swap every body row */
      table.querySelectorAll("tbody tr").forEach(row=>{
        swapCells(row, latestIndex, positionIndex);
      });

      table.dataset.v472Done="1";
    }
  }

  reorderMarketHistoryCheck();

  const observer=new MutationObserver(function(){
    reorderMarketHistoryCheck();
  });

  observer.observe(document.body,{
    childList:true,
    subtree:true
  });

  const version=document.querySelector(".version");
  if(version){
    version.textContent="V4.7.2 • POSITION FIRST";
  }

  console.log("V4.7.2 Market History Position First loaded ✓");
});
</script>
"""

if "</body>" not in text:
    print("ERROR: </body> tidak dijumpai.")
    sys.exit(1)

text = text.replace("</body>", js + "\n</body>", 1)

text = text.replace("<title>4D Charta Analyzer V4.7.1</title>",
                    "<title>4D Charta Analyzer V4.7.2</title>")
text = text.replace("<title>4D Charta Analyzer V4.7</title>",
                    "<title>4D Charta Analyzer V4.7.2</title>")

INDEX.write_text(text, encoding="utf-8")

print("V4.7.2 HISTORY POSITION FIRST APPLIED ✓")
print("New MARKET HISTORY CHECK order:")
print("MARKET | POSITION | HIT NO. | TYPE | LATEST DATE")
print("Database/history/updater/settings untouched.")
