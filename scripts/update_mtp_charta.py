from pathlib import Path
import re, json, time, io
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import pytesseract

BASES = [
    "https://aplanbee.blogspot.com",
    "https://cartaplanbee.blogspot.com",
]

MYT = timezone(timedelta(hours=8))
NOW = datetime.now(MYT)
YEAR, MONTH = NOW.year, NOW.month
OUT = Path("data/mtp-charta.json")

UA = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/131 Mobile Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def get(url, retries=2):
    last=None
    for n in range(retries):
        try:
            r=requests.get(url,headers=UA,timeout=20,allow_redirects=True)
            if r.status_code == 429 or "google.com/sorry" in r.url:
                raise RuntimeError("rate limited")
            r.raise_for_status()
            return r
        except Exception as e:
            last=e
            print("REQUEST RETRY:",url,e)
            if n+1 < retries:
                time.sleep(3)
    raise last

def date_from_title(title):
    m=re.search(r"\bMTP\s+(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b",title,re.I)
    if not m:
        return None
    dd,mm,yy=m.groups()
    return f"{yy}-{int(mm):02d}-{int(dd):02d}"

def discover_latest():
    found={}
    for base in BASES:
        # Homepage first; archive only if homepage gives nothing.
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
                if d:
                    found[d]=urljoin(url,a["href"])

            if found:
                break
        if found:
            break

    if not found:
        return None,None

    date,url=sorted(found.items(),key=lambda x:x[0],reverse=True)[0]
    print("LATEST POST:",date,url)
    return date,url

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

def save(existing):
    entries=sorted(existing.values(),key=lambda e:e["date"],reverse=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "source":"APLANBEE MTP ONLY",
        "updated_at":datetime.now(MYT).isoformat(timespec="seconds"),
        "entries":entries
    },ensure_ascii=False,indent=2),encoding="utf-8")
    if entries:
        print("LATEST SAVED:",entries[0]["date"],"".join(map(str,entries[0]["numbers"])))

def image_candidates(post_url):
    soup=BeautifulSoup(get(post_url).text,"html.parser")
    body=soup.select_one(".post-body") or soup
    scored=[]

    for img in body.find_all("img"):
        src=img.get("data-original") or img.get("data-src") or img.get("src")
        if not src:
            continue

        src=urljoin(post_url,src)
        # Blogger often serves resized copies; request a larger copy.
        src=re.sub(r"/s\d+(-c)?/", "/s1600/", src)
        src=re.sub(r"=w\d+(-h\d+)?(-no)?$", "=s1600", src)

        meta=(" ".join([
            str(img.get("alt") or ""),
            str(img.get("title") or ""),
            str(img.get("class") or "")
        ])).lower()

        score=0
        if "mtp" in meta: score+=8
        if "carta" in meta: score+=8
        if "ramalan" in meta: score+=3

        try:
            w=int(img.get("width") or 0)
            h=int(img.get("height") or 0)
            if w>=300 and h>=300: score+=2
        except Exception:
            pass

        scored.append((score,src))

    out=[]
    for _,src in sorted(scored,key=lambda x:x[0],reverse=True):
        if src not in out:
            out.append(src)
    return out[:3]

def normalize(img):
    img=ImageOps.exif_transpose(img).convert("L")
    if max(img.size)<1800:
        scale=1800/max(img.size)
        img=img.resize((int(img.width*scale),int(img.height*scale)))
    img=ImageOps.autocontrast(img)
    img=ImageEnhance.Contrast(img).enhance(1.8)
    img=img.filter(ImageFilter.SHARPEN)
    return img

def rows_from_data(data):
    tokens=[]
    n=len(data.get("text",[]))
    for i in range(n):
        text=str(data["text"][i]).strip()
        ds=re.findall(r"\d",text)
        if len(ds)!=1:
            continue
        try:
            conf=float(data["conf"][i])
        except Exception:
            conf=-1
        if conf<15:
            continue

        x=int(data["left"][i]); y=int(data["top"][i])
        w=int(data["width"][i]); h=int(data["height"][i])
        if w<=0 or h<=0:
            continue
        tokens.append((ds[0],x+w/2,y+h/2,w,h,conf))

    rows=[]
    for t in sorted(tokens,key=lambda z:z[2]):
        placed=False
        for row in rows:
            ys=[z[2] for z in row]
            hs=[z[4] for z in row]
            medy=sorted(ys)[len(ys)//2]
            medh=sorted(hs)[len(hs)//2]
            if abs(t[2]-medy)<=max(18,medh*.75):
                row.append(t); placed=True; break
        if not placed:
            rows.append([t])

    candidates=[]
    for row in rows:
        row=sorted(row,key=lambda z:z[1])
        if len(row)<4:
            continue
        for i in range(len(row)-3):
            q=row[i:i+4]
            xs=[z[1] for z in q]
            gaps=[xs[j+1]-xs[j] for j in range(3)]
            if min(gaps)<=0:
                continue
            if max(gaps)/max(min(gaps),1)>1.9:
                continue
            candidates.append(q)

    candidates.sort(key=lambda q:sum(z[2] for z in q)/4)

    for i in range(len(candidates)):
        chosen=[candidates[i]]
        base=[z[1] for z in candidates[i]]
        spacing=max(1,sum(base[j+1]-base[j] for j in range(3))/3)

        for q in candidates[i+1:]:
            qx=[z[1] for z in q]
            if sum(abs(qx[j]-base[j]) for j in range(4))/4 > spacing*.35:
                continue

            prev=sum(z[2] for z in chosen[-1])/4
            cur=sum(z[2] for z in q)/4
            mh=sum(z[4] for z in q)/4
            if cur-prev < mh*.75:
                continue

            chosen.append(q)
            if len(chosen)==4:
                digits=[z[0] for rr in chosen for z in sorted(rr,key=lambda a:a[1])]
                if len(digits)==16:
                    return digits
                break
    return None

def extract_grid(image_bytes):
    img=normalize(Image.open(io.BytesIO(image_bytes)))

    variants=[
        img,
        img.point(lambda p: 255 if p>150 else 0),
        img.point(lambda p: 255 if p>180 else 0),
        ImageOps.invert(img).point(lambda p: 255 if p>120 else 0),
    ]

    for variant in variants:
        for psm in (6,11,12):
            data=pytesseract.image_to_data(
                variant,
                config=f"--psm {psm} -c tessedit_char_whitelist=0123456789",
                output_type=pytesseract.Output.DICT
            )
            nums=rows_from_data(data)
            if nums:
                return nums

    # Last OCR fallback: crop central portions because chart is
    # usually the dominant central object in the post image.
    W,H=img.size
    crops=[
        img.crop((0,int(H*.10),W,int(H*.90))),
        img.crop((int(W*.05),int(H*.15),int(W*.95),int(H*.85))),
        img.crop((int(W*.10),int(H*.20),int(W*.90),int(H*.80))),
    ]

    for crop in crops:
        data=pytesseract.image_to_data(
            crop,
            config="--psm 11 -c tessedit_char_whitelist=0123456789",
            output_type=pytesseract.Output.DICT
        )
        nums=rows_from_data(data)
        if nums:
            return nums

    return None

def main():
    existing=load_existing()
    date,url=discover_latest()

    if not date:
        print("No latest MTP post found. Keep existing data.")
        save(existing)
        return

    if date in existing:
        print("Already saved:",date)
        save(existing)
        return

    nums=None
    try:
        images=image_candidates(url)
        print("IMAGE CANDIDATES:",len(images))
    except Exception as e:
        print("POST IMAGE ERROR:",e)
        images=[]

    for idx,img_url in enumerate(images,1):
        try:
            print("TRY IMAGE",idx)
            r=get(img_url)
            nums=extract_grid(r.content)
            if nums:
                print("OCR GRID:",date,"".join(nums))
                break
        except Exception as e:
            print("IMAGE SKIP:",e)

    if nums and len(nums)==16:
        existing[date]={
            "date":date,
            "numbers":[str(x) for x in nums],
            "source":"MTP",
            "url":url,
            "auto":True
        }
        print("AUTO SAVED:",date,"".join(nums))
    else:
        # Important: no hardcoded/fallback numbers.
        print("NEW MTP FOUND, OCR NOT CONFIDENT:",date)
        print("No fallback inserted; existing DB kept safely.")

    save(existing)

if __name__=="__main__":
    main()
