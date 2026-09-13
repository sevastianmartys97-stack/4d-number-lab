from pathlib import Path
import re, json, io, html as htmlmod
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import numpy as np
import cv2
from PIL import Image
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

def large_blogger_image(url):
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

        src = large_blogger_image(urljoin(base, src))
        meta = " ".join([
            str(img.get("alt") or ""),
            str(img.get("title") or ""),
            str(img.get("class") or "")
        ]).lower()

        score = 0
        if "mtp" in meta: score += 12
        if "carta" in meta: score += 12
        if "ramalan" in meta: score += 4
        scored.append((score, src))

    out = []
    for _, src in sorted(scored, key=lambda x:x[0], reverse=True):
        if src not in out:
            out.append(src)
    return out

def discover_feed_direct():
    for base in BASES:
        feeds = [
            base + "/feeds/posts/default?alt=json&max-results=10",
            base + "/feeds/posts/default/-/MTP?alt=json&max-results=10",
        ]
        for feed_url in feeds:
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

                chunks = []
                for key in ("content", "summary"):
                    obj = e.get(key, {})
                    if isinstance(obj, dict):
                        chunks.append(obj.get("$t", "") or "")

                imgs = []
                for chunk in chunks:
                    imgs.extend(images_from_html(chunk, post_url or base))

                media = e.get("media$thumbnail", {})
                if isinstance(media, dict) and media.get("url"):
                    imgs.append(large_blogger_image(media["url"]))

                unique = []
                for u in imgs:
                    if u and u not in unique:
                        unique.append(u)

                found.append((date, post_url, unique))

            if found:
                date, post_url, imgs = sorted(found, key=lambda x:x[0], reverse=True)[0]
                print("FEED DIRECT FOUND:", date)
                print("FEED IMAGE CANDIDATES:", len(imgs))
                return date, post_url, imgs[:4]

    return None, None, []

def pil_to_cv(raw):
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("image decode failed")
    return img

def candidate_crops(img):
    h, w = img.shape[:2]
    out = []

    # Full image and central crops first.
    out.append(("full", img))
    out.append(("center90", img[int(h*.05):int(h*.95), int(w*.05):int(w*.95)]))
    out.append(("center80", img[int(h*.10):int(h*.90), int(w*.10):int(w*.90)]))

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)

    for mode, thr in [("otsu", None), ("t150", 150), ("t180", 180)]:
        if thr is None:
            _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        else:
            _, bw = cv2.threshold(blur, thr, 255, cv2.THRESH_BINARY_INV)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
        bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel, iterations=2)

        cnts, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in cnts:
            x,y,cw,ch = cv2.boundingRect(c)
            area = cw*ch
            if area < (w*h)*0.05 or area > (w*h)*0.95:
                continue
            ratio = cw/max(ch,1)
            if not (0.55 <= ratio <= 1.8):
                continue
            boxes.append((area,x,y,cw,ch))

        for idx, (_,x,y,cw,ch) in enumerate(sorted(boxes, reverse=True)[:6]):
            pad = int(min(cw,ch)*0.03)
            x0=max(0,x-pad); y0=max(0,y-pad)
            x1=min(w,x+cw+pad); y1=min(h,y+ch+pad)
            crop = img[y0:y1, x0:x1]
            if crop.size:
                out.append((f"{mode}_box{idx}", crop))

    # Remove near-duplicate crops by size.
    unique = []
    seen = set()
    for name,crop in out:
        key = (crop.shape[1]//20, crop.shape[0]//20)
        if key in seen:
            continue
        seen.add(key)
        unique.append((name,crop))
    return unique[:12]

def ocr_single_cell(cell):
    if cell.size == 0:
        return None, -1

    gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY) if len(cell.shape)==3 else cell

    # Remove cell borders.
    h,w = gray.shape[:2]
    mx = max(2, int(w*.13))
    my = max(2, int(h*.13))
    core = gray[my:h-my, mx:w-mx] if h>2*my and w>2*mx else gray

    scale = max(2.0, 180/max(core.shape[:2]))
    core = cv2.resize(core, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    core = cv2.GaussianBlur(core, (3,3), 0)

    variants = []
    variants.append(core)
    _, a = cv2.threshold(core, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(a)
    _, b = cv2.threshold(core, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    variants.append(b)

    best_digit = None
    best_conf = -1

    for v in variants:
        data = pytesseract.image_to_data(
            v,
            config="--psm 10 -c tessedit_char_whitelist=0123456789",
            output_type=pytesseract.Output.DICT
        )
        for i, txt in enumerate(data.get("text", [])):
            ds = re.findall(r"\d", str(txt))
            if len(ds) != 1:
                continue
            try:
                conf = float(data["conf"][i])
            except Exception:
                conf = -1
            if conf > best_conf:
                best_conf = conf
                best_digit = ds[0]

    return best_digit, best_conf

def read_equal_grid(crop):
    h,w = crop.shape[:2]
    if min(h,w) < 180:
        return None

    # Try slight trims because outer poster decoration may surround grid.
    trim_sets = [0.00, 0.03, 0.06, 0.10]
    best = None

    for trim in trim_sets:
        x0=int(w*trim); x1=int(w*(1-trim))
        y0=int(h*trim); y1=int(h*(1-trim))
        g = crop[y0:y1, x0:x1]
        gh,gw = g.shape[:2]
        if min(gh,gw) < 160:
            continue

        digits=[]
        confs=[]
        ok=True

        for r in range(4):
            for c in range(4):
                cy0=round(r*gh/4); cy1=round((r+1)*gh/4)
                cx0=round(c*gw/4); cx1=round((c+1)*gw/4)
                cell=g[cy0:cy1, cx0:cx1]
                d,conf=ocr_single_cell(cell)
                if d is None:
                    ok=False
                    break
                digits.append(d)
                confs.append(conf)
            if not ok:
                break

        if ok and len(digits)==16:
            avg=sum(confs)/16
            low=sum(1 for x in confs if x < 20)
            score=avg - low*3
            candidate=("".join(digits), avg, low, trim, score)
            if best is None or candidate[4] > best[4]:
                best=candidate

    return best

def read_grid(raw):
    img = pil_to_cv(raw)
    results = []

    for name,crop in candidate_crops(img):
        res = read_equal_grid(crop)
        if res:
            digits, avg, low, trim, score = res
            print(f"GRID CANDIDATE {name} trim={trim:.2f} avg={avg:.1f} low={low}: {digits}")
            results.append((score, avg, low, digits, name))

    if not results:
        return None

    results.sort(reverse=True)
    best = results[0]
    score, avg, low, digits, name = best

    # Conservative acceptance: all 16 cells read, decent overall confidence,
    # and not too many weak cells.
    if avg >= 35 and low <= 5:
        print(f"GRID ACCEPTED {name}: {digits} avg={avg:.1f}")
        return list(digits)

    # Agreement fallback: same 16 digits independently from >=2 crop hypotheses.
    counts = {}
    for _,avg2,low2,dig2,name2 in results:
        if avg2 >= 20:
            counts.setdefault(dig2, []).append((avg2,low2,name2))
    agreed = sorted(counts.items(), key=lambda kv: len(kv[1]), reverse=True)
    if agreed and len(agreed[0][1]) >= 2:
        dig = agreed[0][0]
        print("GRID ACCEPTED BY AGREEMENT:", dig, "votes=", len(agreed[0][1]))
        return list(dig)

    print("GRID REJECTED: confidence/agreement not enough")
    return None

def main():
    existing = load_existing()
    date, post_url, images = discover_feed_direct()

    if not date:
        print("NO FEED DISCOVERY; KEEP EXISTING DB")
        save(existing)
        return

    if date in existing:
        print("ALREADY SAVED:", date)
        save(existing)
        return

    print("NEW MTP:", date)

    nums = None
    for idx, image_url in enumerate(images, 1):
        try:
            print("IMAGE TRY:", idx, image_url)
            raw = req(image_url).content
            nums = read_grid(raw)
            if nums:
                print("OCR GRID:", "".join(nums))
                break
        except Exception as e:
            print("IMAGE FAILED:", idx, e)

    if nums and len(nums) == 16:
        existing[date] = {
            "date": date,
            "numbers": [str(x) for x in nums],
            "source": "MTP-GRID-OCR-V6.2",
            "url": post_url,
            "auto": True
        }
        print("AUTO SAVED:", date, "".join(nums))
    else:
        print("OCR NOT CONFIDENT:", date)
        print("NO FALLBACK / NO WRONG DATA INSERTED")

    save(existing)

if __name__ == "__main__":
    main()
