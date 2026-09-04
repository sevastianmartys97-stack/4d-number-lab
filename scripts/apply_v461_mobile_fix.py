from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MARKER = "V4.6.1-MOBILE-FORCE-FIX"

if not INDEX.exists():
    print("ERROR: index.html tidak dijumpai.")
    sys.exit(1)

text = INDEX.read_text(encoding="utf-8")

if MARKER in text:
    print("V4.6.1 sudah dipasang. Tiada perubahan.")
    sys.exit(0)

# Ensure proper mobile viewport.
viewport = '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
if 'name="viewport"' not in text.lower():
    text = text.replace("<head>", "<head>\n  " + viewport, 1)
else:
    text = re.sub(
        r'<meta\s+name=["\']viewport["\'][^>]*>',
        viewport,
        text,
        count=1,
        flags=re.I
    )

# Make V4.6 mobile/tablet mode activate up to 1100 CSS px.
text = text.replace("@media(max-width:680px)", "@media(max-width:1100px)")
text = text.replace("window.innerWidth>680", "window.innerWidth>1100")

# Add hard mobile/tablet width safety.
fix_css = r"""
/* V4.6.1-MOBILE-FORCE-FIX */
@media(max-width:1100px){
  html{
    width:100%;
    max-width:100%;
    overflow-x:hidden;
  }

  body.v46-ui{
    width:100%;
    max-width:100%;
    min-width:0!important;
    margin:0!important;
    box-sizing:border-box;
  }

  body.v46-ui .app{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    margin:0 auto!important;
    padding:0!important;
  }

  body.v46-ui .container,
  body.v46-ui .card,
  body.v46-ui .bottom-grid,
  body.v46-ui .history-card,
  body.v46-ui .analysis-card,
  body.v46-ui .permutation-card{
    width:100%!important;
    max-width:100%!important;
    min-width:0!important;
    box-sizing:border-box;
  }

  body.v46-ui .bottom-grid{
    display:block!important;
  }

  body.v46-ui .analysis-card,
  body.v46-ui .history-card{
    width:100%!important;
  }
}
"""

if "</style>" not in text:
    print("ERROR: </style> tidak dijumpai.")
    sys.exit(1)

text = text.replace("</style>", fix_css + "\n</style>", 1)

# Add marker + version label.
marker_js = r"""
<script>
/* V4.6.1-MOBILE-FORCE-FIX */
document.addEventListener("DOMContentLoaded",function(){
  const v=document.querySelector(".version");
  if(v) v.textContent="V4.6.1 • PREMIUM GLASS MOBILE FIX";
});
</script>
"""

text = text.replace("</body>", marker_js + "\n</body>", 1)
text = text.replace("<title>4D Charta Analyzer V4.6</title>",
                    "<title>4D Charta Analyzer V4.6.1</title>")

INDEX.write_text(text, encoding="utf-8")

print("V4.6.1 MOBILE FORCE FIX APPLIED ✓")
print("Fixes:")
print("- viewport mobile")
print("- breakpoint 680px -> 1100px")
print("- tablet/smartphone gets mobile layout")
print("- database/settings/history logic untouched")
