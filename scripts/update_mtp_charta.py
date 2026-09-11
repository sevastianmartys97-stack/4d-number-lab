from pathlib import Path
import re, json
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta
import requests
import numpy as np
import cv2
import pytesseract
from bs4 import BeautifulSoup

BASE='https://cartaplanbee.blogspot.com'
MYT=timezone(timedelta(hours=8))
YEAR=datetime.now(MYT).year
OUT=Path('data/mtp-charta.json')
UA={'User-Agent':'Mozilla/5.0 Chrome/124 Safari/537.36'}
VERIFIED={'2026-09-09':['1','9','9','7','2','5','7','8','0','4','6','8','1','9','3','1']}

def get(url):
    r=requests.get(url,headers=UA,timeout=30)
    r.raise_for_status(); return r

def discover_posts():
    soup=BeautifulSoup(get(f'{BASE}/{YEAR}/').text,'html.parser')
    found={}
    for a in soup.find_all('a',href=True):
        title=' '.join(a.get_text(' ',strip=True).split())
        m=re.match(r'^MTP\s+(\d{2})\.(\d{2})\.(\d{4})\s+CARTA\b',title,re.I)
        if m:
            d=f'{m.group(3)}-{m.group(2)}-{m.group(1)}'
            found[d]=urljoin(BASE,a['href'])
    return sorted(found.items(),reverse=True)

def image_candidates(url):
    soup=BeautifulSoup(get(url).text,'html.parser')
    body=soup.select_one('.post-body') or soup
    imgs=[]
    for img in body.find_all('img'):
        src=img.get('src') or img.get('data-src')
        if src:
            src=re.sub(r'/s\d+(-c)?/','/s1600/',src)
            imgs.append(urljoin(url,src))
    return imgs[:6]

def read_digit(cell):
    cell=cv2.resize(cell,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
    cell=cv2.GaussianBlur(cell,(3,3),0)
    _,th=cv2.threshold(cell,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    txt=pytesseract.image_to_string(th,config='--psm 10 -c tessedit_char_whitelist=0123456789')
    ds=re.findall(r'\d',txt)
    return ds[0] if len(ds)==1 else None

def extract_grid(image_bytes):
    arr=np.frombuffer(image_bytes,np.uint8)
    im=cv2.imdecode(arr,cv2.IMREAD_COLOR)
    if im is None: return None
    gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    h,w=gray.shape[:2]
    rects=[]
    for threshold in (140,160,180,200,220):
        _,bw=cv2.threshold(gray,threshold,255,cv2.THRESH_BINARY)
        contours,_=cv2.findContours(bw,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            x,y,cw,ch=cv2.boundingRect(c)
            if not (0.035*w <= cw <= 0.22*w and 0.025*h <= ch <= 0.16*h): continue
            if not (0.55 <= cw/max(ch,1) <= 1.9): continue
            if cw*ch < 0.0015*w*h: continue
            rects.append((x,y,cw,ch))
    # deduplicate boxes
    uniq=[]
    for r in sorted(rects,key=lambda z:z[2]*z[3],reverse=True):
        x,y,cw,ch=r; cx=x+cw/2; cy=y+ch/2
        if any(abs(cx-(u[0]+u[2]/2))<min(cw,u[2])*.35 and abs(cy-(u[1]+u[3]/2))<min(ch,u[3])*.35 for u in uniq):
            continue
        uniq.append(r)
    # cluster into rows
    items=sorted([(x+cw/2,y+ch/2,x,y,cw,ch) for x,y,cw,ch in uniq],key=lambda z:z[1])
    rows=[]
    for item in items:
        placed=False
        for row in rows:
            if abs(item[1]-np.median([z[1] for z in row])) < np.mean([z[5] for z in row])*.55:
                row.append(item); placed=True; break
        if not placed: rows.append([item])
    candidates=[]
    for row in rows:
        row=sorted(row,key=lambda z:z[0])
        for i in range(max(0,len(row)-3)):
            q=row[i:i+4]
            if len(q)!=4: continue
            gaps=np.diff([z[0] for z in q])
            if min(gaps)<=0 or max(gaps)/max(min(gaps),1)>1.8: continue
            candidates.append(q)
    candidates.sort(key=lambda q:np.mean([z[1] for z in q]))
    for i in range(len(candidates)):
        chosen=[candidates[i]]
        for q in candidates[i+1:]:
            if np.mean([z[1] for z in q])-np.mean([z[1] for z in chosen[-1]]) > np.mean([z[5] for z in q])*.65:
                chosen.append(q)
                if len(chosen)==4: break
        if len(chosen)!=4: continue
        digits=[]; ok=True
        for q in chosen:
            for z in sorted(q,key=lambda z:z[0]):
                _,_,x,y,cw,ch=z; pad=max(1,int(min(cw,ch)*.08))
                d=read_digit(gray[y+pad:y+ch-pad,x+pad:x+cw-pad])
                if d is None: ok=False; break
                digits.append(d)
            if not ok: break
        if ok and len(digits)==16: return digits
    return None

def load_existing():
    if not OUT.exists(): return {}
    try: data=json.loads(OUT.read_text(encoding='utf-8'))
    except Exception: return {}
    return {e['date']:e for e in data.get('entries',[]) if e.get('date') and len(e.get('numbers',[]))==16}

def main():
    existing=load_existing()
    for d,nums in VERIFIED.items():
        existing.setdefault(d,{'date':d,'numbers':nums,'source':'MTP','url':''})
    try: posts=discover_posts()
    except Exception as e:
        print('Discover failed:',e); posts=[]
    for date,url in posts[:14]:
        if date in existing: continue
        nums=None
        for img in image_candidates(url):
            try:
                nums=extract_grid(get(img).content)
                if nums: break
            except Exception as e:
                print('Image skipped',e)
        if nums and len(nums)==16:
            existing[date]={'date':date,'numbers':nums,'source':'MTP','url':url}
            print('Saved',date,''.join(nums))
        else:
            print('No safe 16-digit extraction for',date,'— keeping previous latest')
    entries=sorted(existing.values(),key=lambda e:e['date'],reverse=True)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'source':'CARTAPLANBEE MTP ONLY','updated_at':datetime.now(MYT).isoformat(timespec='seconds'),'entries':entries},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Total MTP:',len(entries))

if __name__=='__main__': main()
