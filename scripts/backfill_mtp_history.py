from pathlib import Path
import re
import json
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta

import requests
import numpy as np
import cv2
import pytesseract
from bs4 import BeautifulSoup

BASE = "https://cartaplanbee.blogspot.com"
MYT = timezone(timedelta(hours=8))
OUT = Path("data/mtp-charta.json")
UA = {
    "User-Agent":
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 Chrome/124 Safari/537.36"
}

# Charta yang sudah disahkan daripada screenshot/user.
VERIFIED = {
    "2026-09-09": [
        "1","9","9","7",
        "2","5","7","8",
        "0","4","6","8",
        "1","9","3","1"
    ],
    "2026-09-06": [
        "3","7","8","2",
        "3","4","9","5",
        "2","3","9","4",
        "6","1","0","5"
    ]
}

def get(url):
    r = requests.get(url, headers=UA, timeout=35)
    r.raise_for_status()
    return r

def date_from_title(title):
    m = re.search(
        r"\bMTP\s+(\d{2})\.(\d{2})\.(\d{4})\b",
        title,
        re.I
    )
    if not m:
        return None
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

def discover_posts():
    found = {}

    # Scan 2026 monthly archives. Only titles beginning MTP are accepted.
    for month in range(1, 13):
        url = f"{BASE}/2026/{month:02d}/"
        try:
            soup = BeautifulSoup(get(url).text, "html.parser")
        except Exception as e:
            print("Archive skipped:", url, e)
            continue

        for a in soup.find_all("a", href=True):
            title = " ".join(a.get_text(" ", strip=True).split())

            if not re.match(
                r"^MTP\s+\d{2}\.\d{2}\.\d{4}\s+CARTA\b",
                title,
                re.I
            ):
                continue

            d = date_from_title(title)
            if not d:
                continue

            href = urljoin(BASE, a["href"])
            found[d] = href

    return sorted(found.items(), key=lambda x: x[0], reverse=True)

def image_candidates(post_url):
    soup = BeautifulSoup(get(post_url).text, "html.parser")
    body = soup.select_one(".post-body") or soup

    images = []
    review_seen = False

    for node in body.descendants:
        name = getattr(node, "name", None)

        if name in ("h2","h3","h4","b","strong","div","p"):
            txt = " ".join(node.get_text(" ", strip=True).split())
            if txt.upper().startswith("REVIEW CARTA"):
                review_seen = True

        if review_seen:
            continue

        if name == "img":
            src = node.get("src") or node.get("data-src")
            if not src:
                continue
            src = re.sub(r"/s\d+(-c)?/", "/s1600/", src)
            images.append(urljoin(post_url, src))

    # Fallback: first few post images.
    if not images:
        for img in body.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src:
                src = re.sub(r"/s\d+(-c)?/", "/s1600/", src)
                images.append(urljoin(post_url, src))

    # Keep unique order.
    seen = set()
    out = []
    for x in images:
        if x not in seen:
            seen.add(x)
            out.append(x)

    return out[:5]

def ocr_tokens(image_bytes):
    arr = np.frombuffer(image_bytes, np.uint8)
    im = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if im is None:
        return []

    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

    # Upscale to make blue/red chart digits easier for tesseract.
    scale = 2.0
    gray = cv2.resize(
        gray, None,
        fx=scale, fy=scale,
        interpolation=cv2.INTER_CUBIC
    )

    data = pytesseract.image_to_data(
        gray,
        config="--psm 11 -c tessedit_char_whitelist=0123456789",
        output_type=pytesseract.Output.DICT
    )

    tokens = []

    for i, txt in enumerate(data.get("text", [])):
        txt = re.sub(r"\D", "", str(txt))

        if len(txt) != 1:
            continue

        try:
            conf = float(data["conf"][i])
        except Exception:
            conf = -1

        if conf < 30:
            continue

        x = int(data["left"][i])
        y = int(data["top"][i])
        w = int(data["width"][i])
        h = int(data["height"][i])

        if w <= 0 or h <= 0:
            continue

        tokens.append({
            "d": txt,
            "x": x + w/2,
            "y": y + h/2,
            "w": w,
            "h": h,
            "conf": conf
        })

    return tokens

def group_rows(tokens):
    if len(tokens) < 16:
        return None

    tokens = sorted(tokens, key=lambda t: t["y"])
    rows = []

    for t in tokens:
        placed = False

        for row in rows:
            ys = [r["y"] for r in row]
            hs = [r["h"] for r in row]
            tol = max(14.0, float(np.median(hs)) * 0.75)

            if abs(t["y"] - float(np.median(ys))) <= tol:
                row.append(t)
                placed = True
                break

        if not placed:
            rows.append([t])

    # Candidate rows with at least 4 digits.
    candidates = [
        sorted(r, key=lambda t: t["x"])
        for r in rows
        if len(r) >= 4
    ]

    if len(candidates) < 4:
        return None

    # Try 4 consecutive row groups.
    for start in range(len(candidates)-3):
        block = candidates[start:start+4]

        # Pick a best 4-token run from each row.
        picked = []
        valid = True

        for row in block:
            best = None
            best_score = None

            for i in range(len(row)-3):
                q = row[i:i+4]
                xs = [z["x"] for z in q]
                gaps = np.diff(xs)

                if min(gaps) <= 0:
                    continue

                # Grid cells should be fairly evenly spaced.
                gap_ratio = max(gaps) / max(min(gaps), 1)
                if gap_ratio > 2.1:
                    continue

                conf = sum(z["conf"] for z in q)
                score = conf - (gap_ratio-1.0)*20

                if best_score is None or score > best_score:
                    best = q
                    best_score = score

            if best is None:
                valid = False
                break

            picked.append(best)

        if not valid:
            continue

        # X positions should align across 4 rows.
        ref = np.array([z["x"] for z in picked[0]])

        aligned = True
        for row in picked[1:]:
            xs = np.array([z["x"] for z in row])
            spacing = max(np.mean(np.diff(ref)), 1)
            if np.mean(np.abs(xs-ref)) > spacing * 0.55:
                aligned = False
                break

        if not aligned:
            continue

        digits = []
        for row in picked:
            digits.extend([z["d"] for z in row])

        if len(digits) == 16:
            return digits

    return None

def extract_chart(post_url):
    for img_url in image_candidates(post_url):
        try:
            content = get(img_url).content
            digits = group_rows(ocr_tokens(content))

            if digits and len(digits) == 16:
                return digits, img_url

        except Exception as e:
            print("Image skipped:", img_url, e)

    return None, None

def load_existing():
    if not OUT.exists():
        return {}

    try:
        payload = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {}

    out = {}

    for e in payload.get("entries", []):
        nums = e.get("numbers", [])

        if (
            e.get("date")
            and isinstance(nums, list)
            and len(nums) == 16
            and all(str(x).isdigit() and len(str(x)) == 1 for x in nums)
        ):
            out[e["date"]] = e

    return out

def main():
    existing = load_existing()

    # Always preserve known verified charts.
    for date, nums in VERIFIED.items():
        existing[date] = {
            "date": date,
            "numbers": nums,
            "source": "MTP",
            "url": existing.get(date, {}).get("url", ""),
            "verified": True
        }

    posts = discover_posts()
    print("MTP posts discovered:", len(posts))

    added = 0

    for date, url in posts:
        if date in existing:
            # Add URL if older seed did not have one.
            if not existing[date].get("url"):
                existing[date]["url"] = url
            continue

        digits, image_url = extract_chart(url)

        if not digits:
            print("Skipped (not confident):", date)
            continue

        existing[date] = {
            "date": date,
            "numbers": digits,
            "source": "MTP",
            "url": url,
            "image": image_url,
            "verified": False
        }

        added += 1
        print("Added:", date, "".join(digits))

    entries = sorted(
        existing.values(),
        key=lambda e: e["date"],
        reverse=True
    )

    payload = {
        "source": "CARTAPLANBEE MTP ONLY",
        "updated_at": datetime.now(MYT).isoformat(timespec="seconds"),
        "entries": entries
    }

    OUT.parent.mkdir(exist_ok=True)

    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("New history added:", added)
    print("Total MTP history:", len(entries))

if __name__ == "__main__":
    main()
