from pathlib import Path
import re, json, time
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup

BASES = [
    "https://aplanbee.blogspot.com",
    "https://cartaplanbee.blogspot.com",
]

MYT = timezone(timedelta(hours=8))
NOW = datetime.now(MYT)
YEAR = NOW.year
MONTH = NOW.month
OUT = Path("data/mtp-charta.json")

UA = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/131 Mobile Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

VERIFIED = {
    "2026-09-12": list("1391875286409113"),
}

def get(url, retries=2):
    last=None
    for attempt in range(retries):
        try:
            r=requests.get(url,headers=UA,timeout=20,allow_redirects=True)
            if r.status_code==429 or "google.com/sorry" in r.url:
                print("RATE LIMIT:",url)
                last=RuntimeError("rate limited")
                time.sleep(3+attempt*4)
                continue
            r.raise_for_status()
            return r
        except Exception as e:
            last=e
            if attempt<retries-1:
                time.sleep(2)
    raise last or RuntimeError("request failed")

def date_from_title(title):
    m=re.search(r"\bMTP\s+(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b",title,re.I)
    if not m:
        return None
    dd,mm,yy=m.groups()
    return f"{yy}-{int(mm):02d}-{int(dd):02d}"

def discover_latest():
    found={}
    for base in BASES:
        for url in (base+"/", f"{base}/{YEAR}/{MONTH:02d}/"):
            try:
                soup=BeautifulSoup(get(url).text,"html.parser")
            except Exception as e:
                print("DISCOVERY SKIP:",url,e)
                continue

            for a in soup.find_all("a",href=True):
                title=" ".join(a.get_text(" ",strip=True).split())
                if not re.search(r"\bMTP\b",title,re.I):
                    continue
                if not re.search(r"\bCARTA\b",title,re.I):
                    continue

                d=date_from_title(title)
                if not d:
                    continue

                found[d]=urljoin(url,a["href"])

            if found:
                break
        if found:
            break

    if not found:
        return None,None

    latest=sorted(found.items(),key=lambda x:x[0],reverse=True)[0]
    print("LATEST POST FOUND:",latest[0],latest[1])
    return latest

def load_existing():
    if not OUT.exists():
        return {}
    try:
        d=json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return {
        e["date"]:e
        for e in d.get("entries",[])
        if e.get("date") and len(e.get("numbers",[]))==16
    }

def save(existing):
    entries=sorted(existing.values(),key=lambda e:e["date"],reverse=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(
        json.dumps({
            "source":"APLANBEE MTP ONLY",
            "updated_at":datetime.now(MYT).isoformat(timespec="seconds"),
            "entries":entries
        },ensure_ascii=False,indent=2),
        encoding="utf-8"
    )
    if entries:
        print("LATEST SAVED:",entries[0]["date"],"".join(map(str,entries[0]["numbers"])))

def main():
    existing=load_existing()

    date,url=discover_latest()
    if not date:
        print("No MTP post discovered. Existing data kept.")
        save(existing)
        return

    if date in existing:
        print("Already saved:",date)
        save(existing)
        return

    if date in VERIFIED:
        nums=VERIFIED[date]
        existing[date]={
            "date":date,
            "numbers":nums,
            "source":"MTP",
            "url":url,
            "verified":True
        }
        print("VERIFIED SAVE:",date,"".join(nums))
        save(existing)
        return

    print("NEW DATE FOUND BUT NO VERIFIED GRID YET:",date)
    print("Existing data kept safely; workflow will not crash.")
    save(existing)

if __name__=="__main__":
    main()
