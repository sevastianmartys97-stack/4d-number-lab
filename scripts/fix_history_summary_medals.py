from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MARKER = "HISTORY-SUMMARY-SORT-MEDALS-V1"

if not INDEX.exists():
    raise SystemExit("ERROR: index.html tidak dijumpai")

s = INDEX.read_text(encoding="utf-8")

if MARKER in s:
    raise SystemExit("Summary sort + medal fix sudah dipasang")

addon = r"""
<script>
/* HISTORY-SUMMARY-SORT-MEDALS-V1 */
(function(){
"use strict";

function clean(v){
  return (v||"").replace(/\s+/g," ").trim();
}

function parseDateText(v){
  const t = clean(v);

  let m = t.match(/\b(20\d{2})-(\d{2})-(\d{2})\b/);
  if(m) return new Date(+m[1], +m[2]-1, +m[3]).getTime();

  m = t.match(/\b(\d{1,2})\/(\d{1,2})\/(20\d{2})\b/);
  if(m) return new Date(+m[3], +m[2]-1, +m[1]).getTime();

  return 0;
}

function medalForPosition(text){
  const t = clean(text).toLowerCase();
  if(t === "1st" || t === "first" || t === "1") return "🥇 ";
  if(t === "2nd" || t === "second" || t === "2") return "🥉 ";
  if(t === "3rd" || t === "third" || t === "3") return "🥈 ";
  return "";
}

function enhanceSummaryTable(table){
  const head = table.querySelector("thead tr");
  const tbody = table.querySelector("tbody");
  if(!head || !tbody) return;

  const headers = [...head.children].map(th => clean(th.textContent).toUpperCase());

  const marketIndex = headers.indexOf("MARKET");
  const statusIndex = headers.indexOf("STATUS");
  const positionIndex = headers.indexOf("POSITION");
  const hitIndex = headers.indexOf("HIT NO.");
  const typeIndex = headers.indexOf("TYPE");
  const dateIndex = headers.findIndex(h => h === "LATEST DATE" || h === "DATE");

  if(
    marketIndex < 0 ||
    statusIndex < 0 ||
    positionIndex < 0 ||
    hitIndex < 0 ||
    typeIndex < 0 ||
    dateIndex < 0
  ) return;

  const rows = [...tbody.querySelectorAll(":scope > tr")];
  if(rows.length < 1) return;

  rows.forEach(row => {
    const posCell = row.children[positionIndex];
    if(!posCell) return;

    const raw = clean(posCell.textContent).replace(/^[🥇🥈🥉]\s*/u, "");
    const medal = medalForPosition(raw);
    posCell.textContent = medal ? medal + raw : raw;
  });

  rows.sort((a,b) => {
    const ad = parseDateText(a.children[dateIndex]?.textContent || "");
    const bd = parseDateText(b.children[dateIndex]?.textContent || "");
    return bd - ad;
  });

  rows.forEach(r => tbody.appendChild(r));
}

function apply(){
  document.querySelectorAll("table").forEach(enhanceSummaryTable);
}

document.addEventListener("DOMContentLoaded", function(){
  setTimeout(apply, 250);

  let timer = null;
  const observer = new MutationObserver(function(){
    clearTimeout(timer);
    timer = setTimeout(apply, 180);
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
});
})();
</script>
"""

if "</body>" not in s:
    raise SystemExit("ERROR: </body> tidak dijumpai")

s = s.replace("</body>", addon + "\n</body>", 1)
INDEX.write_text(s, encoding="utf-8")

print("Market History Check summary sorted newest -> oldest ✓")
print("Position medals added ✓")
print("1st = 🥇, 2nd = 🥉, 3rd = 🥈")
print("Version label unchanged.")
