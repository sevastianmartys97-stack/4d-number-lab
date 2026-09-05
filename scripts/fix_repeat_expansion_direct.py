from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
SW = ROOT / "sw.js"

if not INDEX.exists():
    raise SystemExit("ERROR: index.html tidak dijumpai")

s = INDEX.read_text(encoding="utf-8")

marker = "REVERSE-TRIPLE-INTEGRATED-V1"
if marker in s:
    print("Fix ini sudah dipasang.")
    raise SystemExit(0)

old = '''  const a=ranked[0],b=ranked[1],c=ranked[2];
  const rows=[["×12 • AABC",a+a+b+c,"1 pair sama"],["×6 • AABB",a+a+b+b,"2 pair"],["×4 • AAAB",a+a+a+b,"3 digit sama"]];
  box.innerHTML='<div class="ttl">REPEAT DIGIT EXPANSION</div><div class="note">Berdasarkan digit paling kerap dalam Charta. Unique permutation, bukan probability menang.</div><div class="grid">'+rows.map(x=>'<div class="item"><small>'+x[0]+' • '+x[2]+'</small><span class="num">'+x[1]+'</span>'+badge(x[1])+'</div>').join("")+'</div>';
'''

new = '''  const a=ranked[0],b=ranked[1],c=ranked[2];
  /* REVERSE-TRIPLE-INTEGRATED-V1 */
  const rows=[
    ["×12 • AABC",a+a+b+c,"1 pair sama"],
    ["×6 • AABB",a+a+b+b,"2 pair"],
    ["×4 • AAAB",a+a+a+b,"3 digit sama"]
  ];
  if((f[b]||0)>=3){
    rows.push(["×4 • REVERSE AAAB",b+b+b+a,"3 digit sama • reverse family"]);
  }
  box.innerHTML='<div class="ttl">REPEAT DIGIT EXPANSION</div><div class="note">Berdasarkan digit paling kerap dalam Charta. Unique permutation, bukan probability menang.</div><div class="grid">'+rows.map(x=>'<div class="item"><small>'+x[0]+' • '+x[2]+'</small><span class="num">'+x[1]+'</span>'+badge(x[1])+'</div>').join("")+'</div>';
'''

if old not in s:
    raise SystemExit("ERROR: blok Repeat Digit Expansion asal tidak dijumpai. Tiada perubahan dibuat.")

s = s.replace(old, new, 1)
INDEX.write_text(s, encoding="utf-8")
print("Reverse triple integrated directly into original Repeat Digit Expansion ✓")
print("No extra panel ✓")
print("No extra MutationObserver ✓")
print("V5.0 STABLE label unchanged ✓")

if SW.exists():
    sw = SW.read_text(encoding="utf-8")
    if 'const CACHE = "4d-charta-v500";' in sw:
        sw = sw.replace(
            'const CACHE = "4d-charta-v500";',
            'const CACHE = "4d-charta-v500-repeatfix1";',
            1
        )
        SW.write_text(sw, encoding="utf-8")
        print("PWA cache bumped ✓")
    else:
        print("PWA cache name already changed; skipped.")
