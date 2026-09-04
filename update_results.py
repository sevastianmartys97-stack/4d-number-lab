from __future__ import annotations
import json, re, time
from datetime import datetime, timedelta
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
URL = "https://4d-my.com/4d-past-results/?draw={date}"

MARKETS = {
    "toto": ("toto.json", ["SportsToto 4D","Sports Toto 4D","Sports Toto"]),
    "magnum": ("magnum.json", ["Magnum 4D","Magnum4D","Magnum"]),
    "damacai": ("damacai.json", ["Da Ma Cai 1+3D","Da Ma Cai","Damacai"]),
    "cashsweep": ("cashsweep.json", ["Cash Sweep","Sarawak Cash Sweep"]),
}
HEADERS = {"User-Agent":"Mozilla/5.0"}

def parse_date(s):
    s=(s or "").strip()
    for f in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%d-%b-%Y","%d %b %Y"):
        try:return datetime.strptime(s,f)
        except:pass
    return None

def iso_date(s):
    d=parse_date(s)
    return d.strftime("%Y-%m-%d") if d else s

def load_db(path, name):
    try:
        obj=json.loads(path.read_text(encoding="utf-8"))
        obj.setdefault("market",name); obj.setdefault("draws",[])
        return obj
    except:
        return {"market":name,"lastUpdated":"","draws":[]}

def save_db(path, db):
    db["draws"].sort(key=lambda x: parse_date(str(x.get("date",""))) or datetime.min, reverse=True)
    if db["draws"]:
        db["lastUpdated"]=iso_date(str(db["draws"][0].get("date","")))
    path.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def text_of(html):
    s=BeautifulSoup(html,"html.parser")
    return "\n".join(x.strip() for x in s.get_text("\n",strip=True).splitlines() if x.strip())

def block_for(text, aliases, all_aliases):
    low=text.lower()
    starts=[low.find(a.lower()) for a in aliases if low.find(a.lower())>=0]
    if not starts:return None
    start=min(starts)
    ends=[]
    for a in all_aliases:
        p=low.find(a.lower(),start+1)
        if p>start:ends.append(p)
    return text[start:min(ends) if ends else len(text)]

def prize(block, patterns):
    for p in patterns:
        m=re.search(p,block,re.I)
        if m:return m.group(1)
    return None

def section_nums(block,start_label,end_label=None):
    low=block.lower(); s=low.find(start_label.lower())
    if s<0:return []
    s+=len(start_label)
    e=low.find(end_label.lower(),s) if end_label else len(block)
    if e<0:e=len(block)
    nums=re.findall(r"(?<!\d)(\d{4})(?!\d)",block[s:e])
    out=[]
    for n in nums:
        if n not in out:out.append(n)
        if len(out)==10:break
    return out

def parse_market(block):
    m=re.search(r"#?\s*([0-9]{2,6}/[0-9]{2})\s*(?:\([A-Za-z]{3}\))?\s*([0-9]{1,2}[-/ ][A-Za-z0-9]{2,9}[-/ ][0-9]{4})",block,re.I)
    if not m:return None
    draw=m.group(1); raw=m.group(2)
    date=iso_date(raw)
    first=prize(block,[r"1st\s*Prize\s*([0-9]{4})",r"First\s*Prize\s*([0-9]{4})"])
    second=prize(block,[r"2nd(?:\s*Prize)?\s*([0-9]{4})",r"Second\s*Prize\s*([0-9]{4})"])
    third=prize(block,[r"3rd(?:\s*Prize)?\s*([0-9]{4})",r"Third\s*Prize\s*([0-9]{4})"])
    if not (date and first and second and third):return None
    return {
        "date":date,"draw":draw,"first":first,"second":second,"third":third,
        "special":section_nums(block,"Special","Consolation"),
        "consolation":section_nums(block,"Consolation",None)
    }

def merge(db, rec):
    key=(rec["date"],rec["draw"])
    for i,old in enumerate(db["draws"]):
        if (str(old.get("date","")),str(old.get("draw","")))==key:
            if old!=rec:
                db["draws"][i]=rec
                return True
            return False
    db["draws"].append(rec); return True

def main():
    DATA.mkdir(exist_ok=True)
    dbs={k:load_db(DATA/f,aliases[0]) for k,(f,aliases) in MARKETS.items()}
    all_aliases=[a for _,aliases in MARKETS.values() for a in aliases]
    sess=requests.Session()
    for i in range(10):
        dt=datetime.now()-timedelta(days=i)
        try:
            r=sess.get(URL.format(date=dt.strftime("%Y-%m-%d")),headers=HEADERS,timeout=25)
            r.raise_for_status()
            text=text_of(r.text)
            for k,(_,aliases) in MARKETS.items():
                b=block_for(text,aliases,all_aliases)
                if not b:continue
                rec=parse_market(b)
                if rec:merge(dbs[k],rec)
        except Exception as e:
            print("WARN",dt.date(),e)
        time.sleep(0.4)
    for k,(f,_) in MARKETS.items():
        save_db(DATA/f,dbs[k])
        print(k,len(dbs[k]["draws"]))

if __name__=="__main__":
    main()
