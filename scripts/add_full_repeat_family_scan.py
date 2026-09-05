from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
SW = ROOT / "sw.js"

if not INDEX.exists():
    raise SystemExit("ERROR: index.html tidak dijumpai")

s = INDEX.read_text(encoding="utf-8")

if "FULL-REPEAT-FAMILY-SCAN-V1" in s:
    print("Full Repeat Family Scan sudah dipasang.")
    raise SystemExit(0)

old = '''  box.innerHTML='<div class="ttl">REPEAT DIGIT EXPANSION</div><div class="note">Berdasarkan digit paling kerap dalam Charta. Unique permutation, bukan probability menang.</div><div class="grid">'+rows.map(x=>'<div class="item"><small>'+x[0]+' • '+x[2]+'</small><span class="num">'+x[1]+'</span>'+badge(x[1])+'</div>').join("")+'</div>';
'''

new = '''  /* FULL-REPEAT-FAMILY-SCAN-V1 */
  const repeatDigits=Object.entries(f).filter(([,count])=>count>=3).sort((x,y)=>y[1]-x[1]||Number(x[0])-Number(y[0])).map(x=>x[0]);
  const partners=Object.entries(f).filter(([,count])=>count>=2).sort((x,y)=>y[1]-x[1]||Number(x[0])-Number(y[0])).map(x=>x[0]);
  const families=[];
  repeatDigits.forEach(rep=>{
    partners.forEach(partner=>{
      if(partner===rep)return;
      const base=rep+rep+rep+partner;
      families.push({base,rep,partner,perms:getPermutations(base)});
    });
  });
  const familyHtml=families.length
    ? '<details class="v5FullRepeat"><summary><span>FULL REPEAT FAMILY SCAN</span><b>SHOW ▼</b></summary><div class="v5FullRepeatBody">'+
      families.map(fam=>'<details class="v5FamilyRow"><summary><span class="v5FamilyNum">'+fam.base+'</span><span class="v5FamilyMeta">TRIPLE '+fam.rep+' + '+fam.partner+' • ×'+fam.perms.length+' ›</span></summary><div class="v5FamilyPerms">'+fam.perms.map(p=>'<span>'+p+'</span>').join("")+'</div></details>').join("")+
      '</div></details>'
    : '';
  box.innerHTML='<div class="ttl">REPEAT DIGIT EXPANSION</div><div class="note">Berdasarkan digit paling kerap dalam Charta. Unique permutation, bukan probability menang.</div><div class="grid">'+rows.map(x=>'<div class="item"><small>'+x[0]+' • '+x[2]+'</small><span class="num">'+x[1]+'</span>'+badge(x[1])+'</div>').join("")+'</div>'+familyHtml;
'''

if old not in s:
    raise SystemExit("ERROR: blok Repeat Digit Expansion semasa tidak dijumpai. Tiada perubahan dibuat.")

s = s.replace(old, new, 1)

css = '''
<style>
/* FULL-REPEAT-FAMILY-SCAN-V1 */
#v5Repeat .v5FullRepeat{margin-top:7px;border:1px solid rgba(66,169,235,.30);border-radius:9px;background:rgba(6,28,45,.82);overflow:hidden}
#v5Repeat .v5FullRepeat>summary{min-height:36px;padding:8px 9px;display:flex;align-items:center;justify-content:space-between;gap:8px;cursor:pointer;list-style:none;color:#cfe8f8;font-size:9px;font-weight:bold}
#v5Repeat .v5FullRepeat>summary::-webkit-details-marker,#v5Repeat .v5FamilyRow>summary::-webkit-details-marker{display:none}
#v5Repeat .v5FullRepeat>summary b{color:#ffc62e;font-size:8px}
#v5Repeat .v5FullRepeat[open]>summary b{font-size:0}
#v5Repeat .v5FullRepeat[open]>summary b:after{content:"HIDE ▲";font-size:8px}
#v5Repeat .v5FullRepeatBody{padding:0 7px 7px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px}
#v5Repeat .v5FamilyRow{border:1px solid rgba(52,101,132,.48);border-radius:8px;background:#061522;overflow:hidden}
#v5Repeat .v5FamilyRow>summary{padding:7px;cursor:pointer;list-style:none}
#v5Repeat .v5FamilyNum{display:block;color:#ffc62e;font-size:14px;font-weight:bold}
#v5Repeat .v5FamilyMeta{display:block;color:#8299aa;font-size:7px;margin-top:2px}
#v5Repeat .v5FamilyPerms{display:flex;flex-wrap:wrap;gap:3px;padding:0 6px 6px}
#v5Repeat .v5FamilyPerms span{padding:3px 4px;border-radius:5px;border:1px solid #21445b;background:#0a2232;color:#d9e8f1;font-size:7px}
</style>
'''

if "</head>" not in s:
    raise SystemExit("ERROR: </head> tidak dijumpai.")

s = s.replace("</head>", css + "\n</head>", 1)
INDEX.write_text(s, encoding="utf-8")

print("Full Repeat Family Scan dipasang di bawah Repeat Digit Expansion ✓")
print("Default CLOSED dengan SHOW ▼ ✓")
print("Setiap family boleh dibuka untuk lihat pusingan ✓")
print("Repeat Digit Expansion asal kekal ✓")
print("V5.0 STABLE label unchanged ✓")

if SW.exists():
    sw = SW.read_text(encoding="utf-8")
    new_sw, n = re.subn(r'const CACHE = "4d-charta-v500[^"]*";','const CACHE = "4d-charta-v500-fullrepeat1";',sw,count=1)
    if n:
        SW.write_text(new_sw, encoding="utf-8")
        print("PWA cache bumped ✓")
    else:
        print("Cache constant tidak dijumpai; sw.js tidak diubah.")
