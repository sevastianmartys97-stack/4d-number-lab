from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MARKER = "V4.6-PREMIUM-GLASS-MOBILE"

if not INDEX.exists():
    print("ERROR: index.html tidak dijumpai.")
    sys.exit(1)

text = INDEX.read_text(encoding="utf-8")

if MARKER in text:
    print("V4.6 Premium Glass Mobile sudah dipasang. Tiada perubahan.")
    sys.exit(0)

css = r"""
/* =========================================================
   V4.6-PREMIUM-GLASS-MOBILE
   UI ONLY — database, history, settings & analysis logic
   remain untouched.
   ========================================================= */

:root{
  --v46-glass:rgba(8,25,40,.78);
  --v46-glass2:rgba(5,18,31,.90);
  --v46-line:rgba(77,186,255,.38);
  --v46-gold:#ffc62e;
  --v46-cyan:#35cfff;
  --v46-green:#38e77e;
  --v46-purple:#c56cff;
}

body.v46-ui{
  background:
    radial-gradient(circle at 10% 0%,rgba(255,198,46,.08),transparent 24%),
    radial-gradient(circle at 90% 15%,rgba(91,84,255,.09),transparent 28%),
    linear-gradient(180deg,#03101a 0%,#020b13 100%);
}

body.v46-ui .app{
  max-width:980px;
}

body.v46-ui .header{
  position:relative;
  overflow:hidden;
  border:1px solid rgba(255,198,46,.18);
  border-radius:18px;
  padding:18px 14px;
  margin-bottom:12px;
  background:
    linear-gradient(135deg,rgba(255,198,46,.08),transparent 28%),
    linear-gradient(180deg,rgba(8,29,47,.96),rgba(4,15,26,.96));
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.04),
    0 16px 35px rgba(0,0,0,.22);
}

body.v46-ui .header h1{
  color:#fff0bd;
  text-shadow:0 0 18px rgba(255,198,46,.24);
  letter-spacing:.6px;
}

body.v46-ui .version{
  color:var(--v46-cyan);
}

body.v46-ui .card,
body.v46-ui .permutation-card,
body.v46-ui .analysis-card,
body.v46-ui .history-card{
  background:
    linear-gradient(145deg,rgba(255,255,255,.025),transparent 28%),
    linear-gradient(180deg,var(--v46-glass),var(--v46-glass2));
  border:1px solid var(--v46-line);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,.04),
    0 12px 32px rgba(0,0,0,.20);
  backdrop-filter:blur(10px);
  -webkit-backdrop-filter:blur(10px);
}

body.v46-ui .small-btn,
body.v46-ui .slot-btn,
body.v46-ui .copy-btn{
  min-height:38px;
  border-radius:10px;
}

body.v46-ui .chart-input{
  background:
    linear-gradient(180deg,rgba(52,22,18,.96),rgba(28,16,17,.98));
  border:1px solid rgba(255,106,66,.58);
  box-shadow:inset 0 0 14px rgba(255,112,55,.05);
}

body.v46-ui .chart-input:focus,
body.v46-ui .fav-input:focus{
  border-color:var(--v46-gold);
  box-shadow:
    0 0 0 2px rgba(255,198,46,.12),
    0 0 20px rgba(255,198,46,.10);
}

body.v46-ui .line-item,
body.v46-ui .analysis-box,
body.v46-ui .history-market,
body.v46-ui .coverage-item{
  border-color:rgba(68,166,225,.24);
}

body.v46-ui .analysis-card{
  border-color:rgba(56,231,126,.42);
}

body.v46-ui .pattern-panel{
  border-color:rgba(255,198,46,.42)!important;
  background:
    linear-gradient(135deg,rgba(255,198,46,.05),transparent 30%),
    rgba(3,17,29,.90)!important;
}

.v46-auto-toggle{
  display:none;
}

.v46-bottom-nav{
  display:none;
}

.v46-mobile-title{
  display:none;
}

.v46-hidden-mobile{
  display:none!important;
}

@media(max-width:680px){

  html,body{
    overflow-x:hidden;
  }

  body.v46-ui{
    padding:6px 6px 82px;
  }

  body.v46-ui .app{
    width:100%;
    max-width:none;
  }

  body.v46-ui .header{
    text-align:left;
    padding:13px 14px;
    margin-bottom:8px;
    border-radius:14px;
  }

  body.v46-ui .header h1{
    font-size:19px;
    line-height:1.1;
    padding-right:2px;
  }

  body.v46-ui .version{
    font-size:8px;
    margin-top:5px;
  }

  body.v46-ui .subtitle{
    display:none;
  }

  body.v46-ui .card,
  body.v46-ui .permutation-card,
  body.v46-ui .analysis-card,
  body.v46-ui .history-card{
    padding:10px;
    border-radius:14px;
    margin-bottom:9px;
  }

  /* HOME: input chart first */
  body.v46-ui .flex{
    display:block;
  }

  body.v46-ui .charta-section,
  body.v46-ui .lines-section{
    width:100%;
  }

  body.v46-ui .charta-grid{
    gap:5px;
  }

  body.v46-ui .chart-input{
    height:53px;
    font-size:24px;
    border-radius:10px;
  }

  /* AUTO CHART remains, but compact/collapsible */
  body.v46-ui .lines-section{
    margin-top:8px;
    border-top:1px solid rgba(83,162,214,.18);
    padding-top:8px;
  }

  body.v46-ui .lines-section>.title{
    display:none;
  }

  .v46-auto-toggle{
    display:flex;
    width:100%;
    align-items:center;
    justify-content:space-between;
    gap:8px;
    background:rgba(6,28,45,.92);
    color:#cfe8f8;
    border:1px solid rgba(66,169,235,.34);
    border-radius:10px;
    min-height:42px;
    padding:8px 10px;
    font-size:10px;
    font-weight:bold;
    margin-bottom:7px;
  }

  .v46-auto-toggle .v46-toggle-state{
    color:var(--v46-gold);
  }

  body.v46-ui .lines-section.v46-collapsed #chartaLines{
    display:none;
  }

  body.v46-ui .lines-grid{
    grid-template-columns:repeat(3,1fr);
    gap:4px;
  }

  body.v46-ui .line-item{
    min-height:42px;
    padding:6px;
    border-radius:7px;
  }

  body.v46-ui .line-item span{
    font-size:6px;
  }

  body.v46-ui .line-item strong{
    font-size:10px;
  }

  /* Favourite area: no horizontal zoom */
  body.v46-ui .slot-controls{
    align-items:flex-start;
  }

  body.v46-ui .slot-controls .title{
    max-width:68%;
    font-size:9px;
    line-height:1.35;
  }

  body.v46-ui .slot-btn{
    padding:7px 11px;
    min-height:32px;
  }

  body.v46-ui .table-scroll{
    overflow-x:hidden;
  }

  body.v46-ui #favBody{
    display:block;
  }

  body.v46-ui #favBody tr{
    display:grid;
    grid-template-columns:28px minmax(86px,1fr) 72px 30px;
    gap:6px;
    align-items:center;
    border:1px solid rgba(62,137,186,.20);
    background:rgba(4,18,30,.75);
    border-radius:10px;
    padding:7px;
    margin-bottom:6px;
  }

  body.v46-ui #favBody tr.selected-row{
    border-color:rgba(255,198,46,.60);
    background:
      linear-gradient(90deg,rgba(255,198,46,.07),transparent 55%),
      rgba(7,31,48,.90);
  }

  body.v46-ui #favBody td{
    border:0!important;
    padding:0!important;
    min-width:0;
    font-size:8px;
  }

  body.v46-ui .fav-input{
    width:100%;
    min-width:0;
    height:40px;
    font-size:19px;
    letter-spacing:3px;
  }

  /* Keep just #, favourite, hit and delete on mobile rows.
     Full details appear below in analysis/pattern panel. */
  body.v46-ui #favBody td:nth-child(3),
  body.v46-ui #favBody td:nth-child(5),
  body.v46-ui #favBody td:nth-child(6),
  body.v46-ui #favBody td:nth-child(7){
    display:none;
  }

  body.v46-ui .table-scroll table,
  body.v46-ui .table-scroll tbody{
    display:block;
    width:100%;
  }

  body.v46-ui .table-scroll thead{
    display:none;
  }

  body.v46-ui .coverage{
    grid-template-columns:repeat(2,1fr);
    gap:5px;
  }

  /* CHARTA HIT + Pattern becomes the key result card */
  body.v46-ui .analysis-card{
    order:0;
    margin-bottom:9px;
  }

  body.v46-ui .analysis-stack{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:5px;
  }

  body.v46-ui .analysis-box{
    display:block;
    text-align:center;
    padding:8px 5px;
    min-height:70px;
  }

  body.v46-ui .analysis-box:first-child{
    grid-column:1/-1;
    display:flex;
    text-align:left;
    min-height:75px;
    border-color:rgba(56,231,126,.38);
    background:
      linear-gradient(90deg,rgba(56,231,126,.10),transparent 65%),
      rgba(3,20,31,.92);
  }

  body.v46-ui .analysis-icon{
    margin:0 auto 4px;
  }

  body.v46-ui .analysis-box:first-child .analysis-icon{
    margin:0 9px 0 0;
  }

  body.v46-ui .analysis-label{
    font-size:7px;
  }

  body.v46-ui .analysis-value{
    font-size:14px;
  }

  body.v46-ui .analysis-value.big{
    font-size:25px;
  }

  body.v46-ui .pattern-panel{
    margin-top:8px!important;
    padding:10px!important;
  }

  body.v46-ui .pattern-grid-mini{
    max-width:none!important;
    gap:5px!important;
  }

  body.v46-ui .pattern-cell{
    height:48px!important;
    font-size:20px!important;
  }

  body.v46-ui .pattern-info{
    font-size:9px!important;
  }

  body.v46-ui .pattern-path{
    font-size:10px!important;
    line-height:1.55;
  }

  body.v46-ui .pattern-badge{
    font-size:9px!important;
    padding:6px 9px!important;
  }

  /* Permutations compact */
  body.v46-ui .permutation-card{
    padding:10px;
  }

  body.v46-ui .big-number{
    font-size:31px;
    letter-spacing:5px;
  }

  body.v46-ui .permutation-list{
    grid-template-columns:repeat(4,1fr);
    gap:4px;
  }

  body.v46-ui .perm{
    min-height:36px;
    font-size:10px;
    border-radius:7px;
  }

  /* History tab - no whole-page horizontal scrolling */
  body.v46-ui .history-card .market-wrap,
  body.v46-ui .history-card .table-scroll{
    overflow-x:auto;
    -webkit-overflow-scrolling:touch;
  }

  body.v46-ui .market-table{
    min-width:560px;
  }

  body.v46-ui .footer{
    padding-bottom:18px;
  }

  /* fixed mobile navigation */
  .v46-bottom-nav{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    position:fixed;
    z-index:9999;
    left:6px;
    right:6px;
    bottom:6px;
    min-height:62px;
    background:rgba(3,15,27,.94);
    border:1px solid rgba(75,170,232,.34);
    border-radius:18px;
    overflow:hidden;
    box-shadow:0 12px 34px rgba(0,0,0,.50);
    backdrop-filter:blur(16px);
    -webkit-backdrop-filter:blur(16px);
  }

  .v46-nav-btn{
    appearance:none;
    border:0;
    border-right:1px solid rgba(58,120,165,.18);
    background:transparent;
    color:#9cb3c6;
    min-width:0;
    padding:7px 3px 6px;
    font-size:8px;
  }

  .v46-nav-btn:last-child{
    border-right:0;
  }

  .v46-nav-icon{
    display:block;
    font-size:20px;
    line-height:1;
    margin-bottom:5px;
  }

  .v46-nav-btn.active{
    color:#ffe075;
    background:
      radial-gradient(circle at 50% 100%,rgba(255,198,46,.16),transparent 67%);
  }

  .v46-mobile-title{
    display:block;
    font-size:10px;
    font-weight:bold;
    color:#cce4f4;
    margin:2px 0 8px;
  }
}
"""

js = r"""
<script>
/* =========================================================
   V4.6-PREMIUM-GLASS-MOBILE
   PRESENTATION LAYER ONLY
   ========================================================= */
(function(){
  function ready(fn){
    if(document.readyState==="loading"){
      document.addEventListener("DOMContentLoaded",fn);
    }else{
      fn();
    }
  }

  ready(function(){
    document.body.classList.add("v46-ui");

    /* Update visible version text only. */
    const version=document.querySelector(".version");
    if(version){
      version.textContent="V4.6 • PREMIUM GLASS MOBILE";
    }

    const brand=document.querySelector(".footer-brand");
    if(brand){
      brand.textContent="4D CHARTA ANALYZER V4.6";
    }

    const h1=document.querySelector(".header h1");
    if(h1 && !h1.textContent.includes("👑")){
      h1.textContent="👑 " + h1.textContent.trim();
    }

    /* Keep Auto Charta Lines, but make it collapsible on phone. */
    const lines=document.querySelector(".lines-section");
    if(lines && !lines.querySelector(".v46-auto-toggle")){
      const btn=document.createElement("button");
      btn.type="button";
      btn.className="v46-auto-toggle";
      btn.innerHTML='<span>⚡ AUTO CHART PATTERN</span><span class="v46-toggle-state">SHOW ▼</span>';
      lines.insertBefore(btn,lines.firstChild);
      lines.classList.add("v46-collapsed");

      btn.addEventListener("click",function(){
        const collapsed=lines.classList.toggle("v46-collapsed");
        const state=btn.querySelector(".v46-toggle-state");
        state.textContent=collapsed ? "SHOW ▼" : "HIDE ▲";
      });
    }

    const app=document.querySelector(".app");
    const cards=app ? Array.from(app.children) : [];

    const inputCard=document.querySelector(".charta-section")?.closest(".card") || null;
    const favBody=document.getElementById("favBody");
    const favCard=favBody ? favBody.closest(".card") : null;
    const permCard=document.querySelector(".permutation-card");
    const analysis=document.querySelector(".analysis-card");
    const history=document.querySelector(".history-card");
    const bottomGrid=document.querySelector(".bottom-grid");
    const footer=document.querySelector(".footer");

    /* On mobile, make CHARTA HIT/PATTERN appear immediately after favourites.
       Move existing nodes only — do not recreate or alter their logic. */
    function arrangeMobile(){
      if(!app || window.innerWidth>680){
        return;
      }

      if(analysis && favCard && analysis.parentNode!==app){
        app.insertBefore(analysis, favCard.nextSibling);
      }else if(analysis && favCard){
        app.insertBefore(analysis, favCard.nextSibling);
      }

      if(permCard && analysis){
        app.insertBefore(permCard, analysis.nextSibling);
      }

      if(history && permCard){
        app.insertBefore(history, permCard.nextSibling);
      }

      if(bottomGrid && bottomGrid.children.length===0){
        bottomGrid.style.display="none";
      }
    }

    arrangeMobile();

    /* Mobile tabs: Home keeps input/result together.
       Pattern shows result + permutations.
       History isolates large history tables.
       All uses existing DOM and live data. */
    if(!document.querySelector(".v46-bottom-nav")){
      const nav=document.createElement("div");
      nav.className="v46-bottom-nav";
      nav.innerHTML=
        '<button class="v46-nav-btn active" data-tab="home"><span class="v46-nav-icon">⌂</span>Home</button>'+
        '<button class="v46-nav-btn" data-tab="pattern"><span class="v46-nav-icon">⌘</span>Pattern</button>'+
        '<button class="v46-nav-btn" data-tab="history"><span class="v46-nav-icon">◷</span>History</button>'+
        '<button class="v46-nav-btn" data-tab="all"><span class="v46-nav-icon">•••</span>All</button>';

      document.body.appendChild(nav);

      const showTab=function(tab){
        if(window.innerWidth>680){
          [inputCard,favCard,analysis,permCard,history,footer].forEach(el=>{
            if(el) el.classList.remove("v46-hidden-mobile");
          });
          return;
        }

        const all=[inputCard,favCard,analysis,permCard,history,footer];
        all.forEach(el=>{
          if(el) el.classList.add("v46-hidden-mobile");
        });

        if(tab==="home"){
          [inputCard,favCard,analysis].forEach(el=>{
            if(el) el.classList.remove("v46-hidden-mobile");
          });
        }

        if(tab==="pattern"){
          [analysis,permCard].forEach(el=>{
            if(el) el.classList.remove("v46-hidden-mobile");
          });
        }

        if(tab==="history"){
          [history].forEach(el=>{
            if(el) el.classList.remove("v46-hidden-mobile");
          });
        }

        if(tab==="all"){
          all.forEach(el=>{
            if(el) el.classList.remove("v46-hidden-mobile");
          });
        }

        window.scrollTo({top:0,behavior:"smooth"});
      };

      nav.querySelectorAll(".v46-nav-btn").forEach(btn=>{
        btn.addEventListener("click",function(){
          nav.querySelectorAll(".v46-nav-btn").forEach(x=>x.classList.remove("active"));
          btn.classList.add("active");
          showTab(btn.dataset.tab);
        });
      });

      showTab("home");
    }

    window.addEventListener("resize",function(){
      arrangeMobile();
      if(window.innerWidth>680){
        document.querySelectorAll(".v46-hidden-mobile").forEach(el=>{
          el.classList.remove("v46-hidden-mobile");
        });
      }
    });

    console.log("4D Charta Analyzer V4.6 Premium Glass Mobile UI loaded ✓");
  });
})();
</script>
"""

# Insert CSS before the first closing style tag.
if "</style>" not in text:
    print("ERROR: </style> tidak dijumpai.")
    sys.exit(1)

text = text.replace("</style>", css + "\n</style>", 1)

# Insert presentation JS before closing body.
if "</body>" not in text:
    print("ERROR: </body> tidak dijumpai.")
    sys.exit(1)

text = text.replace("</body>", js + "\n</body>", 1)

# Update only visible title strings if present; harmless if already V4.5.
text = text.replace("<title>4D Charta Analyzer V4.4</title>",
                    "<title>4D Charta Analyzer V4.6</title>")
text = text.replace("<title>4D Charta Analyzer V4.5</title>",
                    "<title>4D Charta Analyzer V4.6</title>")

INDEX.write_text(text, encoding="utf-8")

print("V4.6 PREMIUM GLASS MOBILE APPLIED ✓")
print("Changed: index.html presentation layer only")
print("NOT changed: data/*.json")
print("NOT changed: scripts/update_results.py")
print("NOT changed: workflows for database/update")
print("NOT changed: localStorage keys/settings")
