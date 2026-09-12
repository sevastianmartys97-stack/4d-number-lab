from pathlib import Path
import re, json, time, random
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta
import requests
import numpy as np
import cv2
import pytesseract
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

def get(url, retries=4):
    last=None
    for attempt in range(retries):
        try:
            r=requests.get(url,headers=UA,timeout=35,allow_redirects=True)
            if r.status_code==429 or "google.com/sorry" in r.url:
                wait=8+attempt*12+random.randint(0,4)
                print("Rate limited:",url,"wait",wait)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except Exception as e:
            last=e
            if attempt<retries-1:
                time.sleep(4+attempt*6)
    raise last or RuntimeError("request failed")

def date_from_title(title):
    pats = [
        r"\bMTP\s+(\d{2})[./-](\d{2})[./-](\d{4})\b",
        r"\bMTP\s+(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b",
    ]
    for p in pats:
        m=re.search(p,title,re.I)
        if m:
            dd,mm,yy=m.groups()
            return f"{yy}-{int(mm):02d}-{int(dd):02d}"
    return None

def discover_posts():
    found={}
    urls=[]
    for base in BASES:
        urls += [
            base + "/",
            f"{base}/{YEAR}/",
            f"{base}/{YEAR}/{MONTH:02d}/",
            f"{base}/search?max-results=50",
        ]

    for u in urls:
        try:
            soup=BeautifulSoup(get(u).text,"html.parser")
        except Exception as e:
            print("Skip discovery:",u,e)
            continue

        for a in soup.find_all("a",href=True):
            title=" ".join(a.get_text(" ",strip=True).split())
            if not title:
                continue
            if not re.search(r"\bMTP\b",title,re.I):
                continue
            if not re.search(r"\bCARTA\b",title,re.I):
                continue
            d=date_from_title(title)
            if not d:
                continue
            found[d]=urljoin(u,a["href"])
            print("Found MTP post:",d,title[:80])

    return sorted(found.items(),key=lambda x:x[0],reverse=True)

def image_candidates(post_url):
    soup=BeautifulSoup(get(post_url).text,"html.parser")
    body=soup.select_one(".post-body") or soup
    out=[]
    for img in body.find_all("img"):
        src=img.get("src") or img.get("data-src") or img.get("data-original")
        if not src:
            continue
        src=re.sub(r"/s\d+(-c)?/", "/s1600/", src)
        src=urljoin(post_url,src)
        if src not in out:
            out.append(src)
    return out[:10]

def read_digit(cell):
    cell=cv2.resize(cell,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
    cell=cv2.GaussianBlur(cell,(3,3),0)
    for inv in (False,True):
        typ=cv2.THRESH_BINARY_INV if inv else cv2.THRESH_BINARY
        _,th=cv2.threshold(cell,0,255,typ+cv2.THRESH_OTSU)
        txt=pytesseract.image_to_string(
            th,
            config="--psm 10 -c tessedit_char_whitelist=0123456789"
        )
        ds=re.findall(r"\d",txt)
        if len(ds)==1:
            return ds[0]
    return None

def extract_grid(image_bytes):
    arr=np.frombuffer(image_bytes,np.uint8)
    im=cv2.imdecode(arr,cv2.IMREAD_COLOR)
    if im is None:
        return None

    gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    h,w=gray.shape[:2]

    rects=[]
    for threshold in (110,130,150,170,190,210,230):
        _,bw=cv2.threshold(gray,threshold,255,cv2.THRESH_BINARY)
        contours,_=cv2.findContours(bw,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            x,y,cw,ch=cv2.boundingRect(c)
            if not (0.035*w <= cw <= 0.24*w and 0.025*h <= ch <= 0.18*h):
                continue
            ratio=cw/max(ch,1)
            if not 0.55 <= ratio <= 2.1:
                continue
            if cw*ch < 0.001*w*h:
                continue
            rects.append((x,y,cw,ch))

    uniq=[]
    for r in sorted(rects,key=lambda z:z[2]*z[3],reverse=True):
        x,y,cw,ch=r
        cx,cy=x+cw/2,y+ch/2
        if any(abs(cx-(u[0]+u[2]/2))<min(cw,u[2])*.35 and
               abs(cy-(u[1]+u[3]/2))<min(ch,u[3])*.35 for u in uniq):
            continue
        uniq.append(r)

    items=sorted([(x+cw/2,y+ch/2,x,y,cw,ch) for x,y,cw,ch in uniq],key=lambda z:z[1])
    rows=[]
    for item in items:
        placed=False
        for row in rows:
            tol=max(12,np.median([z[5] for z in row])*.55)
            if abs(item[1]-np.median([z[1] for z in row])) <= tol:
                row.append(item); placed=True; break
        if not placed:
            rows.append([item])

    candidates=[]
    for row in rows:
        row=sorted(row,key=lambda z:z[0])
        for i in range(max(0,len(row)-3)):
            q=row[i:i+4]
            if len(q)!=4: continue
            gaps=np.diff([z[0] for z in q])
            if len(gaps)!=3 or min(gaps)<=0: continue
            if max(gaps)/max(min(gaps),1)>2.0: continue
            candidates.append(q)

    candidates.sort(key=lambda q:np.mean([z[1] for z in q]))
    for i in range(len(candidates)):
        chosen=[candidates[i]]
        for q in candidates[i+1:]:
            if np.mean([z[1] for z in q])-np.mean([z[1] for z in chosen[-1]]) > np.mean([z[5] for z in q])*.65:
                chosen.append(q)
                if len(chosen)==4: break
        if len(chosen)!=4: continue

        digits=[]
        ok=True
        for q in chosen:
            for z in sorted(q,key=lambda a:a[0]):
                _,_,x,y,cw,ch=z
                pad=max(1,int(min(cw,ch)*.08))
                cell=gray[y+pad:y+ch-pad,x+pad:x+cw-pad]
                d=read_digit(cell)
                if d is None:
                    ok=False; break
                digits.append(d)
            if not ok: break

        if ok and len(digits)==16:
            return digits
    return None

def load_existing():
    if not OUT.exists():
        return {}
    try:
        d=json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {
        e["date"]:e for e in d.get("entries",[])
        if e.get("date") and len(e.get("numbers",[]))==16
    }

def main():
    existing=load_existing()
    posts=discover_posts()
    print("Discovered:",len(posts))

    for date,url in posts[:20]:
        if date in existing:
            continue

        nums=None
        for img in image_candidates(url):
            try:
                r=get(img)
                nums=extract_grid(r.content)
                if nums:
                    print("Grid extracted:",date,"".join(nums))
                    break
            except Exception as e:
                print("Image skipped:",e)

        if nums and len(nums)==16:
            existing[date]={
                "date":date,
                "numbers":nums,
                "source":"MTP",
                "url":url
            }
            print("SAVED:",date,"".join(nums))
        else:
            print("No safe 16-digit extraction:",date)

    entries=sorted(existing.values(),key=lambda e:e["date"],reverse=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "source":"APLANBEE MTP ONLY",
        "updated_at":datetime.now(MYT).isoformat(timespec="seconds"),
        "entries":entries
    },ensure_ascii=False,indent=2),encoding="utf-8")

    if entries:
        print("LATEST:",entries[0]["date"],"".join(map(str,entries[0]["numbers"])))

if __name__=="__main__":
    main()
