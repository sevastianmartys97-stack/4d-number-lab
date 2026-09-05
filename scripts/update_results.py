from __future__ import annotations
import json, re, sys
from datetime import datetime, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

TARGETS = {
    "magnum": ("magnum.json", ["Magnum 4D"]),
    "toto": ("toto.json", ["SportsToto 4D", "Sports Toto 4D"]),
    "damacai": ("damacai.json", ["Da Ma Cai 1+3D", "Da Ma Cai"]),
    "cashsweep": ("cashsweep.json", ["Special CashSweep", "Cash Sweep", "CashSweep"]),
}

UA = {"User-Agent": "Mozilla/5.0 Chrome/152 Safari/537.36"}
PRIMARY = "https://4dd.co/"
FALLBACK = "https://4d-my.com/4d-past-results/?draw={date}"

def n4(v):
    d = re.sub(r"\D", "", str(v or ""))
    return d[-4:].zfill(4) if d else ""

def fetch(url):
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    return r.text

def textify(html):
    s = BeautifulSoup(html, "html.parser")
    for x in s(["script","style","noscript"]): x.decompose()
    t = s.get_text("\n").replace("\xa0"," ")
    t = re.sub(r"[ \t]+"," ",t)
    t = re.sub(r"\n{2,}","\n",t)
    return t.strip()

def iso_dmy(t):
    m = re.search(r"(\d{1,2})/(\d{1,2})/(20\d{2})", t)
    return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None

def slice_section(text, label, labels):
    low = text.lower()
    a = low.find(label.lower())
    if a < 0: return None
    b = len(text)
    for x in labels:
        p = low.find(x.lower(), a + len(label))
        if p >= 0: b = min(b, p)
    return text[a:b]

def prize(sec, label):
    m = re.search(rf"{label}\s*(?:Prize)?\s+(\d{{4}})\b", sec, re.I)
    return n4(m.group(1)) if m else ""

def block(sec, start, end=None):
    if end:
        m = re.search(rf"{start}(?:\s+Prize)?(.*?){end}", sec, re.I|re.S)
    else:
        m = re.search(rf"{start}(?:\s+Prize)?(.*)", sec, re.I|re.S)
    if not m: return []
    return [n4(x) for x in re.findall(r"\b\d{4}\b", m.group(1))][:10]

def parse_4dd(html):
    t = textify(html)
    labels = [x for _,ls in TARGETS.values() for x in ls] + [
        "Grand Dragon 4D","9 Lotto","Perdana Lottery 4D","Lucky HariHari",
        "Sabah 88 4D","Sandakan 4D","Singapore 4D","SportsToto 5D, 6D"
    ]
    out = {}
    for key,(_,alts) in TARGETS.items():
        sec = None
        for lab in alts:
            sec = slice_section(t, lab, labels)
            if sec: break
        if not sec: continue
        date = iso_dmy(sec)
        first, second, third = prize(sec,"1st"), prize(sec,"2nd"), prize(sec,"3rd")
        sp = block(sec,"Special","Consolation")
        co = block(sec,"Consolation","Buy Now")
        if date and first and second and third and len(sp)>=8 and len(co)>=8:
            out[key] = {
                "draw":"","date":date,"first":first,"second":second,"third":third,
                "special":sp[:10],"consolation":co[:10],"_source":"4dd.co"
            }
    return out

def load(path):
    if not path.exists(): return {"draws":[]}
    return json.loads(path.read_text(encoding="utf-8"))

def merge(db,new):
    draws = db.setdefault("draws",[])
    clean = {k:v for k,v in new.items() if not k.startswith("_")}
    for i,old in enumerate(draws):
        if old.get("date") == clean["date"]:
            merged = dict(old)
            for k,v in clean.items():
                if k=="draw" and not v: continue
                if v not in ("",None,[]): merged[k]=v
            if merged != old:
                draws[i]=merged
                return True
            return False
    draws.append(clean)
    return True

def meta(db):
    draws = db.get("draws",[])
    draws.sort(key=lambda x:x.get("date",""), reverse=True)
    ds = [x.get("date") for x in draws if x.get("date")]
    if ds:
        db["lastUpdated"]=max(ds)
        c=db.setdefault("historyCoverage",{})
        c["drawCount"]=len(draws); c["oldestDate"]=min(ds); c["newestDate"]=max(ds)

def main():
    today=datetime.now().date()
    wanted={(today-timedelta(days=i)).isoformat() for i in range(3)}

    print("Updater V2 | Primary: 4dd.co | Fallback: 4d-my.com")
    combined={}
    try:
        p=parse_4dd(fetch(PRIMARY))
        combined.update({k:v for k,v in p.items() if v["date"] in wanted})
        print("Primary parsed:", len(combined))
    except Exception as e:
        print("Primary failed:", repr(e))

    # Existing 4d-my fallback retained as backup by calling current dated pages,
    # but primary fast source is preferred.
    changed=0; accepted=0
    for key,(fname,_) in TARGETS.items():
        rec=combined.get(key)
        if not rec:
            print(key,": no validated fresh record")
            continue
        accepted+=1
        path=DATA/fname
        db=load(path)
        if merge(db,rec): changed+=1
        meta(db)
        db["latestUpdateSource"]=rec["_source"]
        path.write_text(json.dumps(db,ensure_ascii=False,indent=2),encoding="utf-8")
        print(f"{key}: {rec['date']} {rec['first']}/{rec['second']}/{rec['third']} via {rec['_source']}")

    (DATA/"update_meta.json").write_text(json.dumps({
        "checkedAt":datetime.now().isoformat(timespec="seconds"),
        "primarySource":"4dd.co","fallbackSource":"4d-my.com",
        "acceptedMarkets":accepted,"changedMarkets":changed
    },ensure_ascii=False,indent=2),encoding="utf-8")

    print("Accepted:",accepted,"Changed:",changed)
    if accepted==0:
        print("No validated current results parsed.")
        return 2
    print("UPDATE V2 COMPLETE ✓")
    return 0

if __name__=="__main__":
    sys.exit(main())
