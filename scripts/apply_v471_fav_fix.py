from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MARKER = "V4.7.1-FAV-KEYBOARD-FIX"

if not INDEX.exists():
    print("ERROR: index.html tidak dijumpai.")
    sys.exit(1)

text = INDEX.read_text(encoding="utf-8")

if MARKER in text:
    print("V4.7.1 Favourite Keyboard Fix sudah dipasang.")
    sys.exit(0)

css = r"""
/* V4.7.1-FAV-KEYBOARD-FIX */
@media(max-width:1100px){
  body.v46-ui #favBody tr.v47-edit-row{
    display:grid!important;
  }

  body.v46-ui #favBody tr.v47-edit-row .fav-input{
    border-color:#ffc62e!important;
    box-shadow:0 0 0 2px rgba(255,198,46,.10)!important;
  }
}
"""

js = r"""
<script>
/* V4.7.1-FAV-KEYBOARD-FIX */
document.addEventListener("DOMContentLoaded",function(){

  function prepareFavInputs(){
    document.querySelectorAll("#favBody .fav-input").forEach(input=>{
      input.setAttribute("inputmode","numeric");
      input.setAttribute("pattern","[0-9]*");
      input.setAttribute("autocomplete","off");
      input.setAttribute("maxlength","4");
    });
  }

  function refreshFavRowsSafe(){
    document.querySelectorAll("#favBody tr").forEach(tr=>{
      const input=tr.querySelector(".fav-input");
      if(!input) return;

      const value=(input.value||"").trim();
      const isEditing=tr.classList.contains("v47-edit-row");
      const isFocused=document.activeElement===input;
      const hasValue=value.length>0;

      tr.classList.toggle(
        "v47-filled-row",
        hasValue || isEditing || isFocused
      );
    });
  }

  prepareFavInputs();
  refreshFavRowsSafe();

  /* Replace V4.7 add-button behaviour with keyboard-safe behaviour. */
  const addBtn=document.querySelector(".v47-add-btn");

  if(addBtn){
    const cleanBtn=addBtn.cloneNode(true);
    addBtn.replaceWith(cleanBtn);

    cleanBtn.addEventListener("click",function(){
      const rows=[...document.querySelectorAll("#favBody tr")];

      const target=rows.find(tr=>{
        const input=tr.querySelector(".fav-input");
        if(!input) return false;
        return !(input.value||"").trim();
      });

      if(!target){
        alert("Semua slot favourite sudah digunakan.");
        return;
      }

      target.classList.add("v47-edit-row","v47-filled-row");

      const input=target.querySelector(".fav-input");

      if(input){
        input.setAttribute("inputmode","numeric");
        input.setAttribute("pattern","[0-9]*");
        input.setAttribute("maxlength","4");

        requestAnimationFrame(()=>{
          input.scrollIntoView({
            behavior:"smooth",
            block:"center"
          });

          setTimeout(()=>{
            try{
              input.focus({preventScroll:true});
            }catch(e){
              input.focus();
            }
          },220);
        });
      }
    });
  }

  document.addEventListener("input",function(e){
    const input=e.target;
    if(!input || !input.classList.contains("fav-input")) return;

    /* Digits only, max 4. */
    const cleaned=(input.value||"")
      .replace(/\D/g,"")
      .slice(0,4);

    if(input.value!==cleaned){
      input.value=cleaned;
    }

    const row=input.closest("tr");
    if(row){
      row.classList.add("v47-filled-row");

      if(cleaned.length===4){
        row.classList.remove("v47-edit-row");
      }
    }
  },true);

  document.addEventListener("focusin",function(e){
    if(e.target && e.target.classList.contains("fav-input")){
      const row=e.target.closest("tr");
      if(row){
        row.classList.add("v47-filled-row","v47-edit-row");
      }
    }
  });

  document.addEventListener("focusout",function(e){
    if(e.target && e.target.classList.contains("fav-input")){
      const input=e.target;
      const row=input.closest("tr");

      setTimeout(()=>{
        if(!row) return;

        const value=(input.value||"").trim();
        row.classList.remove("v47-edit-row");

        if(!value){
          row.classList.remove("v47-filled-row");
        }else{
          row.classList.add("v47-filled-row");
        }
      },120);
    }
  });

  /* Keep inputs prepared even if app rerenders rows. */
  const favBody=document.getElementById("favBody");

  if(favBody){
    const observer=new MutationObserver(function(){
      prepareFavInputs();
      refreshFavRowsSafe();
    });

    observer.observe(favBody,{
      childList:true,
      subtree:true
    });
  }

  const version=document.querySelector(".version");
  if(version){
    version.textContent="V4.7.1 • MINIMAL MOBILE";
  }

  console.log("V4.7.1 Favourite keyboard fix loaded ✓");
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

text = text.replace("<title>4D Charta Analyzer V4.7</title>",
                    "<title>4D Charta Analyzer V4.7.1</title>")

INDEX.write_text(text, encoding="utf-8")

print("V4.7.1 FAVOURITE KEYBOARD FIX APPLIED ✓")
print("- + ADD NUMBER row stays visible while typing")
print("- numeric keyboard requested")
print("- digits only, max 4")
print("- empty row hides again only after leaving it")
print("- database/history/updater/settings untouched")
