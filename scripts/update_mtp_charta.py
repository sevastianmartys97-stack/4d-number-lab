from pathlib import Path
import re, json, io, html as htmlmod, statistics
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import numpy as np
import cv2
import pytesseract

MYT = timezone(timedelta(hours=8))
OUT = Path("data/mtp-charta.json")

BASES = [
    "https://aplanbee.blogspot.com",
    "https://cartaplanbee.blogspot.com",
]

UA = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/131 Mobile Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def req(url, timeout=25):
    r = requests.get(url, headers=UA, timeout=timeout, allow_redirects=True)
    if r.status_code == 429 or "google.com/sorry" in r.url:
        raise RuntimeError("rate limited")
    r.raise_for_status()
    return r

def parse_date(text):
    m = re.search(r"\bMTP\s+(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b", text, re.I)
    if not m:
        return None
    dd, mm, yy = m.groups()
    return f"{yy}-{int(mm):02d}-{int(dd):02d}"

def load_existing():
    if not OUT.exists():
        return {}
    try:
        d = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {
        e["date"]: e for e in d.get("entries", [])
        if e.get("date") and len(e.get("numbers", [])) == 16
    }

def save(existing):
    entries = sorted(existing.values(), key=lambda e:e["date"], reverse=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({
        "source": "APLANBEE MTP ONLY",
        "updated_at": datetime.now(MYT).isoformat(timespec="seconds"),
        "entries": entries
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    if entries:
        print("LATEST SAVED:", entries[0]["date"], "".join(map(str, entries[0]["numbers"])))

def large_image(url):
    url = htmlmod.unescape(url)
    url = re.sub(r"/s\d+(-c)?/", "/s1600/", url)
    url = re.sub(r"=w\d+(-h\d+)?(-no)?$", "=s1600", url)
    return url

def images_from_html(raw_html, base):
    soup = BeautifulSoup(raw_html or "", "html.parser")
    scored = []
    for img in soup.find_all("img"):
        src = img.get("data-original") or img.get("data-src") or img.get("src")
        if not src:
            continue
        src = large_image(urljoin(base, src))
        meta = " ".join([
            str(img.get("alt") or ""),
            str(img.get("title") or ""),
            str(img.get("class") or "")
        ]).lower()
        score = 0
        if "mtp" in meta: score += 20
        if "carta" in meta: score += 20
        if "ramalan" in meta: score += 5
        scored.append((score, src))

    out = []
    for _, src in sorted(scored, key=lambda x:x[0], reverse=True):
        if src not in out:
            out.append(src)
    return out

def discover_feed():
    for base in BASES:
        for feed_url in (
            base + "/feeds/posts/default?alt=json&max-results=10",
            base + "/feeds/posts/default/-/MTP?alt=json&max-results=10",
        ):
            try:
                data = req(feed_url).json()
            except Exception as e:
                print("FEED SKIP:", feed_url, e)
                continue

            found = []
            for e in data.get("feed", {}).get("entry", []):
                title = e.get("title", {}).get("$t", "")
                if "MTP" not in title.upper() or "CARTA" not in title.upper():
                    continue

                date = parse_date(title)
                if not date:
                    continue

                post_url = ""
                for l in e.get("link", []):
                    if l.get("rel") == "alternate":
                        post_url = l.get("href") or ""
                        break

                imgs = []
                for key in ("content", "summary"):
                    obj = e.get(key, {})
                    if isinstance(obj, dict):
                        imgs.extend(images_from_html(obj.get("$t", "") or "", post_url or base))

                media = e.get("media$thumbnail", {})
                if isinstance(media, dict) and media.get("url"):
                    imgs.append(large_image(media["url"]))

                uniq = []
                for u in imgs:
                    if u and u not in uniq:
                        uniq.append(u)

                found.append((date, post_url, uniq))

            if found:
                date, post_url, imgs = sorted(found, key=lambda x:x[0], reverse=True)[0]
                print("FEED DIRECT FOUND:", date)
                print("IMAGE CANDIDATES:", len(imgs))
                return date, post_url, imgs[:4]

    return None, None, []

def decode(raw):
    arr = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("decode failed")
    return img

def preprocess_variants(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    scale = 1.0
    if max(gray.shape[:2]) < 1800:
        scale = 1800 / max(gray.shape[:2])
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    gray = cv2.equalizeHist(gray)
    variants = [("gray", gray)]
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(("otsu", otsu))
    adap = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY,41,11)
    variants.append(("adaptive", adap))
    return variants

def ocr_tokens(img, psm):
    data = pytesseract.image_to_data(
        img,
        config=f"--psm {psm} -c tessedit_char_whitelist=0123456789",
        output_type=pytesseract.Output.DICT
    )
    out=[]
    for i,txt in enumerate(data.get("text",[])):
        ds=re.findall(r"\d",str(txt))
        if len(ds)!=1:
            continue
        try:
            conf=float(data["conf"][i])
        except:
            conf=-1
        if conf < 5:
            continue
        x=int(data["left"][i]); y=int(data["top"][i])
        w=int(data["width"][i]); h=int(data["height"][i])
        if w<4 or h<8:
            continue
        out.append({
            "d":ds[0],"x":x+w/2,"y":y+h/2,"w":w,"h":h,"c":conf
        })
    return out

def cluster_rows(tokens):
    if len(tokens) < 16:
        return []

    medh = statistics.median([t["h"] for t in tokens])
    rows=[]
    for t in sorted(tokens,key=lambda z:z["y"]):
        best=None
        bestdy=1e9
        for row in rows:
            ry=sum(z["y"] for z in row)/len(row)
            dy=abs(t["y"]-ry)
            if dy < bestdy and dy <= max(18, medh*0.8):
                best=row; bestdy=dy
        if best is None:
            rows.append([t])
        else:
            best.append(t)

    candidates=[]
    for row in rows:
        row=sorted(row,key=lambda z:z["x"])
        if len(row) < 4:
            continue
        for i in range(len(row)-3):
            q=row[i:i+4]
            xs=[z["x"] for z in q]
            gaps=[xs[j+1]-xs[j] for j in range(3)]
            if min(gaps)<=0:
                continue
            if max(gaps)/max(min(gaps),1) > 2.0:
                continue
            candidates.append(q)
    return candidates

def find_4x4(tokens):
    rows=cluster_rows(tokens)
    if len(rows)<4:
        return []

    rows=sorted(rows,key=lambda r:sum(z["y"] for z in r)/4)
    results=[]

    for i in range(len(rows)):
        base=rows[i]
        bx=[z["x"] for z in base]
        gap=statistics.median([bx[j+1]-bx[j] for j in range(3)])
        chosen=[base]

        for q in rows[i+1:]:
            qx=[z["x"] for z in q]
            align=sum(abs(qx[j]-bx[j]) for j in range(4))/4
            if align > max(22,gap*0.35):
                continue

            lasty=sum(z["y"] for z in chosen[-1])/4
            qy=sum(z["y"] for z in q)/4
            if qy-lasty < 15:
                continue

            chosen.append(q)
            if len(chosen)==4:
                digits="".join(z["d"] for rr in chosen for z in sorted(rr,key=lambda z:z["x"]))
                confs=[z["c"] for rr in chosen for z in rr]
                av=sum(confs)/16
                low=sum(1 for c in confs if c<20)

                ys=[sum(z["y"] for z in rr)/4 for rr in chosen]
                ygaps=[ys[j+1]-ys[j] for j in range(3)]
                uniform=max(ygaps)/max(min(ygaps),1) if min(ygaps)>0 else 99

                if len(digits)==16 and uniform<2.1:
                    score=av-low*2
                    results.append((score,av,low,digits))
                break
    return results

def line_grid(img):
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    if max(gray.shape[:2])<1800:
        s=1800/max(gray.shape[:2])
        gray=cv2.resize(gray,None,fx=s,fy=s,interpolation=cv2.INTER_CUBIC)

    inv=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_MEAN_C,
                              cv2.THRESH_BINARY_INV,31,9)

    h,w=inv.shape
    horiz=cv2.morphologyEx(
        inv,cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT,(max(30,w//18),1))
    )
    vert=cv2.morphologyEx(
        inv,cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT,(1,max(30,h//18)))
    )

    mask=cv2.bitwise_or(horiz,vert)
    cnts,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    boxes=[]
    for c in cnts:
        x,y,cw,ch=cv2.boundingRect(c)
        area=cw*ch
        if area < w*h*0.03:
            continue
        ratio=cw/max(ch,1)
        if 0.45 <= ratio <= 2.2 and cw>120 and ch>120:
            boxes.append((area,x,y,cw,ch))

    results=[]
    for _,x,y,cw,ch in sorted(boxes,reverse=True)[:8]:
        crop=gray[y:y+ch,x:x+cw]
        digits=[]
        confs=[]
        ok=True
        for r in range(4):
            for c in range(4):
                y0=round(r*ch/4); y1=round((r+1)*ch/4)
                x0=round(c*cw/4); x1=round((c+1)*cw/4)
                cell=crop[y0:y1,x0:x1]
                mh=max(2,int(cell.shape[0]*.12))
                mw=max(2,int(cell.shape[1]*.12))
                cell=cell[mh:-mh,mw:-mw] if cell.shape[0]>2*mh and cell.shape[1]>2*mw else cell
                cell=cv2.resize(cell,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
                data=pytesseract.image_to_data(
                    cell,
                    config="--psm 10 -c tessedit_char_whitelist=0123456789",
                    output_type=pytesseract.Output.DICT
                )
                best=None
                for i,txt in enumerate(data.get("text",[])):
                    ds=re.findall(r"\d",str(txt))
                    if len(ds)!=1:
                        continue
                    try: cf=float(data["conf"][i])
                    except: cf=-1
                    if best is None or cf>best[1]:
                        best=(ds[0],cf)
                if best is None:
                    ok=False; break
                digits.append(best[0]); confs.append(best[1])
            if not ok:
                break
        if ok and len(digits)==16:
            av=sum(confs)/16
            low=sum(1 for c in confs if c<20)
            results.append((av-low*2,av,low,"".join(digits)))
    return results

def smart_read(raw):
    img=decode(raw)
    all_results=[]

    for name,v in preprocess_variants(img):
        for psm in (6,11,12):
            toks=ocr_tokens(v,psm)
            rs=find_4x4(toks)
            for r in rs:
                print(f"TOKEN GRID {name}/psm{psm}: {r[3]} avg={r[1]:.1f} low={r[2]}")
                all_results.append(r)

    for r in line_grid(img):
        print(f"LINE GRID: {r[3]} avg={r[1]:.1f} low={r[2]}")
        all_results.append(r)

    if not all_results:
        return None

    all_results.sort(reverse=True)
    best=all_results[0]

    # Strong single result
    if best[1] >= 45 and best[2] <= 4:
        print("ACCEPT STRONG:", best[3])
        return list(best[3])

    # Agreement across independent attempts
    votes={}
    for r in all_results:
        if r[1] >= 20:
            votes[r[3]]=votes.get(r[3],0)+1
    if votes:
        dig,count=max(votes.items(),key=lambda kv:kv[1])
        if count>=2:
            print("ACCEPT AGREEMENT:",dig,"votes=",count)
            return list(dig)

    print("REJECT: no reliable 16-digit agreement")
    return None

def main():
    existing=load_existing()
    date,post_url,images=discover_feed()

    if not date:
        print("NO FEED DISCOVERY")
        save(existing)
        return

    if date in existing:
        print("ALREADY SAVED:",date)
        save(existing)
        return

    print("NEW MTP:",date)
    nums=None

    # Try likely chart images in reverse too because feed order can place promo first.
    ordered=list(images)
    if len(ordered)>1:
        ordered=[ordered[1],ordered[0]]+ordered[2:]

    for idx,image_url in enumerate(ordered,1):
        try:
            print("SMART IMAGE TRY:",idx)
            nums=smart_read(req(image_url).content)
            if nums:
                print("OCR GRID:", "".join(nums))
                break
        except Exception as e:
            print("IMAGE FAILED:",idx,e)

    if nums and len(nums)==16:
        existing[date]={
            "date":date,
            "numbers":[str(x) for x in nums],
            "source":"MTP-SMART-GRID-V6.3",
            "url":post_url,
            "auto":True
        }
        print("AUTO SAVED:",date,"".join(nums))
    else:
        print("OCR NOT CONFIDENT:",date)
        print("CLEAN DATA KEPT - NO FALLBACK")

    save(existing)

if __name__=="__main__":
    main()
