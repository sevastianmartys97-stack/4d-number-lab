from pathlib import Path
import sys
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
MANIFEST = ROOT / "manifest.webmanifest"
SW = ROOT / "sw.js"
ICON_DIR = ROOT / "icons"
MARKER = "V4.7.4-PWA"

if not INDEX.exists():
    raise SystemExit("ERROR: index.html tidak dijumpai")

ICON_DIR.mkdir(exist_ok=True)

def make_icon(size, path):
    img = Image.new("RGBA", (size, size), (3, 15, 28, 255))
    d = ImageDraw.Draw(img)

    gold = (246, 200, 76, 255)
    gold2 = (255, 222, 112, 255)

    pad = int(size * 0.16)
    top = int(size * 0.22)
    base_y = int(size * 0.70)
    left = pad
    right = size - pad
    mid = size // 2

    pts = [
        (left, base_y),
        (left + int(size*0.04), top + int(size*0.12)),
        (left + int(size*0.20), top + int(size*0.27)),
        (mid, top),
        (right - int(size*0.20), top + int(size*0.27)),
        (right - int(size*0.04), top + int(size*0.12)),
        (right, base_y),
    ]
    d.polygon(pts, fill=gold)
    d.rounded_rectangle(
        (left, base_y-int(size*0.08), right, base_y+int(size*0.08)),
        radius=int(size*0.035), fill=gold2
    )

    gem_r = max(2, int(size*0.035))
    gems = [
        (left + int(size*0.18), base_y-int(size*0.02), (41,182,246,255)),
        (mid, base_y-int(size*0.02), (255,82,82,255)),
        (right - int(size*0.18), base_y-int(size*0.02), (46,204,113,255)),
    ]
    for x,y,c in gems:
        d.ellipse((x-gem_r,y-gem_r,x+gem_r,y+gem_r), fill=c)

    for x,y in [
        (left + int(size*0.04), top + int(size*0.12)),
        (mid, top),
        (right - int(size*0.04), top + int(size*0.12))
    ]:
        rr=max(2,int(size*0.028))
        d.ellipse((x-rr,y-rr,x+rr,y+rr), fill=gold2)

    d.rounded_rectangle(
        (int(size*0.04), int(size*0.04), int(size*0.96), int(size*0.96)),
        radius=int(size*0.12),
        outline=(246,200,76,120),
        width=max(1,int(size*0.01))
    )
    img.save(path, "PNG")

make_icon(192, ICON_DIR / "icon-192.png")
make_icon(512, ICON_DIR / "icon-512.png")

MANIFEST.write_text("""{
  "name": "4D Charta Analyzer",
  "short_name": "4D Charta",
  "description": "4D Charta Analyzer - chart, pattern, favourite and market history.",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#030f1c",
  "theme_color": "#030f1c",
  "icons": [
    {
      "src": "icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ]
}
""", encoding="utf-8")

SW.write_text("""const CACHE = "4d-charta-v474";
const CORE = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(CORE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  if (url.pathname.includes("/data/") && url.pathname.endsWith(".json")) {
    event.respondWith(fetch(req).catch(() => caches.match(req)));
    return;
  }

  event.respondWith(
    fetch(req)
      .then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(cache => cache.put(req, clone));
        return res;
      })
      .catch(() => caches.match(req))
  );
});
""", encoding="utf-8")

text = INDEX.read_text(encoding="utf-8")

if MARKER not in text:
    head_add = """
<!-- V4.7.4-PWA -->
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#030f1c">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="4D Charta">
<link rel="apple-touch-icon" href="icons/icon-192.png">
"""
    text = text.replace("</head>", head_add + "\n</head>", 1)

    body_add = r"""
<style>
/* V4.7.4-PWA */
#pwaInstallBtn{
  display:none;
  position:fixed;
  right:14px;
  bottom:82px;
  z-index:9998;
  border:1px solid rgba(246,200,76,.55);
  background:rgba(3,20,35,.96);
  color:#f6c84c;
  border-radius:14px;
  padding:10px 13px;
  font-weight:800;
  font-size:12px;
  box-shadow:0 10px 30px rgba(0,0,0,.28);
}
#pwaInstallBtn.show{display:block}
@media (display-mode: standalone){
  #pwaInstallBtn{display:none!important}
}
</style>

<button id="pwaInstallBtn" type="button">👑 INSTALL APP</button>

<script>
/* V4.7.4-PWA */
(function(){
  let deferredPrompt=null;
  const btn=document.getElementById("pwaInstallBtn");

  if("serviceWorker" in navigator){
    window.addEventListener("load",()=>{
      navigator.serviceWorker.register("./sw.js").catch(()=>{});
    });
  }

  window.addEventListener("beforeinstallprompt",e=>{
    e.preventDefault();
    deferredPrompt=e;
    if(btn) btn.classList.add("show");
  });

  if(btn){
    btn.addEventListener("click",async()=>{
      if(!deferredPrompt) return;
      deferredPrompt.prompt();
      try{ await deferredPrompt.userChoice; }catch(e){}
      deferredPrompt=null;
      btn.classList.remove("show");
    });
  }

  window.addEventListener("appinstalled",()=>{
    if(btn) btn.classList.remove("show");
    deferredPrompt=null;
  });

  document.addEventListener("DOMContentLoaded",()=>{
    const v=document.querySelector(".version");
    if(v) v.textContent="V4.7.4 • PWA READY";
    document.title="4D Charta Analyzer";
  });
})();
</script>
"""
    text = text.replace("</body>", body_add + "\n</body>", 1)

INDEX.write_text(text, encoding="utf-8")

print("V4.7.4 PWA APPLIED ✓")
print("- Crown app icons generated")
print("- manifest.webmanifest created")
print("- sw.js created")
print("- install button added")
print("- Core app engine/database logic untouched")
