from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

MARKER = "V4.5-PATTERN-DETECTOR"

CSS = r'''
/* V4.5-PATTERN-DETECTOR */
.pattern-panel{
  margin-top:10px;
  background:linear-gradient(180deg,#071827,#04121e);
  border:1px solid #285878;
  border-radius:10px;
  padding:10px;
}
.pattern-head{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:8px;
  margin-bottom:9px;
}
.pattern-title{
  color:#afc7da;
  font-size:9px;
  font-weight:bold;
}
.pattern-badge{
  display:inline-block;
  border-radius:6px;
  padding:5px 8px;
  font-size:9px;
  font-weight:bold;
  background:#3b310b;
  border:1px solid #c79d19;
  color:#ffd339;
}
.pattern-grid-mini{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:4px;
  margin-top:8px;
  max-width:230px;
}
.pattern-cell{
  height:39px;
  display:flex;
  align-items:center;
  justify-content:center;
  background:#101f2d;
  border:1px solid #24445d;
  border-radius:6px;
  color:#7990a3;
  font-size:15px;
  font-weight:bold;
  position:relative;
}
.pattern-cell.active{
  background:#3a2212;
  border-color:#ffbd2e;
  color:#ffd037;
}
.pattern-step{
  position:absolute;
  top:2px;
  right:3px;
  font-size:7px;
  min-width:13px;
  height:13px;
  border-radius:50%;
  background:#ffc62e;
  color:#201700;
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight:bold;
}
.pattern-info{
  margin-top:9px;
  font-size:8px;
  line-height:1.6;
  color:#a8bdce;
}
.pattern-info strong{color:#eef5fb}
.pattern-path{
  margin-top:6px;
  color:#59baff;
  font-size:9px;
  font-weight:bold;
  word-break:break-word;
}
.pattern-repeat{
  margin-top:7px;
  color:#ffc62e;
  font-size:8px;
}
.pattern-count{
  color:#38e77e;
  font-weight:bold;
}
.pattern-none{
  color:#74899b;
  font-size:8px;
}
@media(max-width:430px){
  .pattern-grid-mini{max-width:none}
  .pattern-cell{height:36px}
}
'''

JS = r'''
/* ==========================================================
   V4.5-PATTERN-DETECTOR
   Advanced connected-path detector
   ========================================================== */

function patternPosKey(p){
  return p.r + "," + p.c;
}

function patternCoord(p){
  return "R" + (p.r+1) + "C" + (p.c+1);
}

function patternDirection(a,b){
  return {
    dr:Math.sign(b.r-a.r),
    dc:Math.sign(b.c-a.c)
  };
}

function patternSameDirection(a,b){
  return a.dr===b.dr && a.dc===b.dc;
}

function patternAdjacent(a,b){
  const dr=Math.abs(a.r-b.r);
  const dc=Math.abs(a.c-b.c);
  return dr<=1 && dc<=1 && !(dr===0 && dc===0);
}

function patternPositionsForDigit(digit){
  const out=[];
  if(!Array.isArray(chartMatrix) || chartMatrix.length!==4){
    return out;
  }

  for(let r=0;r<4;r++){
    for(let c=0;c<4;c++){
      if(String(chartMatrix[r][c])===String(digit)){
        out.push({r,c,digit:String(digit)});
      }
    }
  }
  return out;
}

function findConnectedPaths(number){
  if(!/^\d{4}$/.test(number) || !buildCharta()){
    return [];
  }

  const digits=number.split("");
  const choices=digits.map(patternPositionsForDigit);

  if(choices.some(x=>!x.length)){
    return [];
  }

  const results=[];

  function walk(index,path,used){
    if(index===digits.length){
      results.push(path.map(p=>({...p})));
      return;
    }

    for(const candidate of choices[index]){
      const key=patternPosKey(candidate);

      if(used.has(key)){
        continue;
      }

      if(path.length && !patternAdjacent(path[path.length-1],candidate)){
        continue;
      }

      used.add(key);
      path.push(candidate);
      walk(index+1,path,used);
      path.pop();
      used.delete(key);
    }
  }

  walk(0,[],new Set());
  return results;
}

function classifyConnectedPath(path,number){
  if(!Array.isArray(path) || path.length!==4){
    return {name:"NO DIRECT PATH",short:"NO PATH",rank:0};
  }

  const dirs=[
    patternDirection(path[0],path[1]),
    patternDirection(path[1],path[2]),
    patternDirection(path[2],path[3])
  ];

  if(
    patternSameDirection(dirs[0],dirs[1]) &&
    patternSameDirection(dirs[1],dirs[2])
  ){
    if(dirs[0].dr===0){
      return {name:"STRAIGHT • HORIZONTAL",short:"STRAIGHT",rank:100};
    }
    if(dirs[0].dc===0){
      return {name:"STRAIGHT • VERTICAL",short:"STRAIGHT",rank:100};
    }
    return {name:"STRAIGHT • DIAGONAL",short:"STRAIGHT",rank:100};
  }

  const rows=[...new Set(path.map(p=>p.r))];
  const cols=[...new Set(path.map(p=>p.c))];

  if(rows.length===2 && cols.length===2){
    return {name:"BOX / CORNER",short:"BOX",rank:90};
  }

  const orthogonal=dirs.every(d=>d.dr===0 || d.dc===0);
  let turns=0;

  for(let i=1;i<dirs.length;i++){
    if(!patternSameDirection(dirs[i-1],dirs[i])){
      turns++;
    }
  }

  if(orthogonal && turns===1){
    return {name:"L-SHAPE",short:"L-SHAPE",rank:80};
  }

  if(turns>=2){
    return {name:"ZIGZAG",short:"ZIGZAG",rank:70};
  }

  const repeated=new Set(number.split("")).size<number.length;

  if(repeated){
    return {name:"REPEAT DIGIT PATH",short:"REPEAT PATH",rank:65};
  }

  return {name:"SNAKE / PATH",short:"SNAKE",rank:60};
}

function analyzeChartaPattern(number){
  const paths=findConnectedPaths(number);

  if(!paths.length){
    return {
      found:false,
      number,
      count:0,
      path:null,
      name:"NO DIRECT PATH",
      short:"NO PATH",
      rank:0,
      repeated:new Set(number.split("")).size<number.length
    };
  }

  const classified=paths.map(path=>{
    const type=classifyConnectedPath(path,number);
    return {path,type};
  });

  classified.sort((a,b)=>b.type.rank-a.type.rank);

  const best=classified[0];

  return {
    found:true,
    number,
    count:paths.length,
    path:best.path,
    name:best.type.name,
    short:best.type.short,
    rank:best.type.rank,
    repeated:new Set(number.split("")).size<number.length
  };
}

function checkCharta(number){
  if(!buildCharta()){
    return{
      hit:false,
      best:null,
      type:null,
      pattern:null,
      patternMatch:null
    };
  }

  const exact=chartLines.find(x=>x.number===number);

  if(exact){
    return{
      hit:true,
      best:number,
      type:"EXACT • "+exact.type,
      pattern:analyzeChartaPattern(number),
      patternMatch:"EXACT"
    };
  }

  for(const p of getPermutations(number)){
    const m=chartLines.find(x=>x.number===p);

    if(m){
      return{
        hit:true,
        best:p,
        type:"PUSINGAN • "+m.type,
        pattern:analyzeChartaPattern(p),
        patternMatch:"PUSINGAN"
      };
    }
  }

  const exactPattern=analyzeChartaPattern(number);

  if(exactPattern.found){
    return{
      hit:true,
      best:number,
      type:"EXACT • "+exactPattern.name,
      pattern:exactPattern,
      patternMatch:"EXACT"
    };
  }

  let bestPerm=null;

  for(const p of getPermutations(number)){
    if(p===number){
      continue;
    }

    const result=analyzeChartaPattern(p);

    if(!result.found){
      continue;
    }

    if(!bestPerm || result.rank>bestPerm.result.rank){
      bestPerm={number:p,result};
    }
  }

  if(bestPerm){
    return{
      hit:true,
      best:bestPerm.number,
      type:"PUSINGAN • "+bestPerm.result.name,
      pattern:bestPerm.result,
      patternMatch:"PUSINGAN"
    };
  }

  return{
    hit:false,
    best:null,
    type:null,
    pattern:exactPattern,
    patternMatch:null
  };
}

function renderPatternMiniGrid(pattern){
  if(!pattern || !pattern.found || !pattern.path){
    return '<div class="pattern-none">Tiada laluan sambungan 4 langkah ditemui.</div>';
  }

  const stepMap=new Map();

  pattern.path.forEach((p,index)=>{
    stepMap.set(patternPosKey(p),index+1);
  });

  let html='<div class="pattern-grid-mini">';

  for(let r=0;r<4;r++){
    for(let c=0;c<4;c++){
      const key=r+","+c;
      const active=stepMap.has(key);

      html +=
        '<div class="pattern-cell '+(active?'active':'')+'">' +
        chartMatrix[r][c] +
        (active
          ? '<span class="pattern-step">'+stepMap.get(key)+'</span>'
          : '') +
        '</div>';
    }
  }

  html+='</div>';
  return html;
}

function appendPatternPanel(fav,ch){
  const box=document.getElementById("hitDetail");
  if(!box || !/^\d{4}$/.test(fav)){
    return;
  }

  let pattern=(ch && ch.pattern) ? ch.pattern : null;

  if(!pattern){
    pattern=analyzeChartaPattern((ch && ch.best) ? ch.best : fav);
  }

  if(!pattern || !pattern.found){
    box.insertAdjacentHTML(
      "beforeend",
      '<div class="pattern-panel">' +
        '<div class="pattern-head">' +
          '<div class="pattern-title">ADVANCED PATTERN DETECTOR</div>' +
          '<div class="pattern-badge">NO DIRECT PATH</div>' +
        '</div>' +
        '<div class="pattern-none">' +
          'Digit mungkin ada dalam Charta, tetapi tiada laluan bersambung 4 langkah ditemui.' +
        '</div>' +
      '</div>'
    );
    return;
  }

  const pathText=pattern.path
    .map((p,i)=>pattern.number[i]+" ("+patternCoord(p)+")")
    .join(" → ");

  const matchType=
    (ch && ch.patternMatch) ||
    ((ch && ch.best===fav) ? "EXACT" : "PUSINGAN");

  box.insertAdjacentHTML(
    "beforeend",
    '<div class="pattern-panel">' +
      '<div class="pattern-head">' +
        '<div class="pattern-title">ADVANCED PATTERN DETECTOR</div>' +
        '<div class="pattern-badge">'+pattern.name+'</div>' +
      '</div>' +
      renderPatternMiniGrid(pattern) +
      '<div class="pattern-info">' +
        '<strong>Number:</strong> '+pattern.number+'<br>' +
        '<strong>Match:</strong> '+matchType+'<br>' +
        '<strong>Possible Paths:</strong> <span class="pattern-count">'+pattern.count+'</span>' +
        '<div class="pattern-path">'+pathText+'</div>' +
        (pattern.repeated
          ? '<div class="pattern-repeat">↻ REPEAT DIGIT: detector guna sel berlainan untuk digit berulang apabila tersedia.</div>'
          : '') +
      '</div>' +
    '</div>'
  );
}
'''

def fail(msg):
    print("ERROR:", msg)
    sys.exit(1)

if not INDEX.exists():
    fail("index.html tidak dijumpai.")

text = INDEX.read_text(encoding="utf-8")

if MARKER in text:
    print("V4.5 sudah dipasang. Tiada perubahan diperlukan.")
    sys.exit(0)

backup = ROOT / "index-v44-local-backup.html"
backup.write_text(text, encoding="utf-8")
print("Backup sementara dibuat:", backup.name)

text = text.replace(
    "<title>4D Charta Analyzer V4.4</title>",
    "<title>4D Charta Analyzer V4.5</title>"
)
text = text.replace(
    '<div class="version">V4.4 • HISTORY INDEPENDENT</div>',
    '<div class="version">V4.5 • HISTORY + ADVANCED PATTERN</div>'
)
text = text.replace(
    "4D CHARTA ANALYZER V4.4",
    "4D CHARTA ANALYZER V4.5"
)

if "</style>" not in text:
    fail("</style> tidak dijumpai.")
text = text.replace("</style>", CSS + "\n</style>", 1)

start_marker = "/* CHARTA ONLY */"
end_marker = "/* =========================\nHISTORY ENGINE"

start = text.find(start_marker)
end = text.find(end_marker)

if start == -1:
    fail("Marker CHARTA ONLY tidak dijumpai.")
if end == -1 or end <= start:
    fail("Marker HISTORY ENGINE tidak dijumpai.")

text = text[:start] + JS + "\n\n" + text[end:]

pattern = re.compile(
    r'''(\s*renderHitDetail\(\s*[\r\n]+\s*fav,\s*[\r\n]+\s*ch,\s*[\r\n]+\s*perms\s*[\r\n]+\s*\);\s*)'''
)

m = pattern.search(text)
if not m:
    fail("Panggilan renderHitDetail tidak dijumpai.")

insert = m.group(1) + "\n\n  appendPatternPanel(\n    fav,\n    ch\n  );\n"
text = text[:m.start()] + insert + text[m.end():]

INDEX.write_text(text, encoding="utf-8")

print()
print("V4.5 PATTERN DETECTOR APPLIED ✓")
print("index.html telah dikemas kini.")
print("History JSON dan updater tidak disentuh.")
