from pathlib import Path
import re, json, html as htmlmod
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
import requests, cv2, numpy as np
from bs4 import BeautifulSoup

MYT=timezone(timedelta(hours=8))
DB=Path("data/mtp-charta.json")
TPL=Path("data/mtp-visual-templates-v10.npz")
BASE="https://cartaplanbee.blogspot.com"
FEED=BASE+"/feeds/posts/default?alt=json&max-results=50"
UA={"User-Agent":"Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/131 Mobile Safari/537.36"}

# Verified historical charts used only to TRAIN visual digit shapes.
# No future result is hard-coded or used as a fallback.
VERIFIED={
    "2026-09-12":"1391875286409113",
    "2026-09-13":"9674291035836497",
    "2026-09-16":"1795842643709157",
    "2026-09-23":"7294697271658035",
}

def get(url):
    r=requests.get(url,headers=UA,timeout=25)
    r.raise_for_status()
    return r

def pdate(s):
    m=re.search(r"MTP\s+(\d{1,2})[./-](\d{1,2})[./-](\d{4})",s,re.I)
    if not m:return None
    d,mn,y=m.groups()
    return f"{y}-{int(mn):02d}-{int(d):02d}"

def big(u):
    u=htmlmod.unescape(u)
    u=re.sub(r"/s\d+(-c)?/","/s1600/",u)
    return u

def load_db():
    if not DB.exists(): return {}
    try:d=json.loads(DB.read_text(encoding="utf-8"))
    except:return {}
    return {e["date"]:e for e in d.get("entries",[]) if e.get("date")}

def save_db(d):
    es=sorted(d.values(),key=lambda x:x["date"],reverse=True)
    DB.parent.mkdir(exist_ok=True)
    DB.write_text(json.dumps({
      "source":"APLANBEE MTP ONLY",
      "updated_at":datetime.now(MYT).isoformat(timespec="seconds"),
      "entries":es
    },ensure_ascii=False,indent=2),encoding="utf-8")
    if es: print("LATEST SAVED:",es[0]["date"],"".join(map(str,es[0]["numbers"])))

def latest():
    f=get(FEED).json()
    ps=[]
    for e in f.get("feed",{}).get("entry",[]):
        title=e.get("title",{}).get("$t","")
        dt=pdate(title)
        if not dt or "CARTA" not in title.upper(): continue
        url=next((x.get("href","") for x in e.get("link",[]) if x.get("rel")=="alternate"),"")
        body=e.get("content",{}).get("$t","") or e.get("summary",{}).get("$t","")
        soup=BeautifulSoup(body,"html.parser")
        imgs=[]
        for im in soup.find_all("img"):
            u=im.get("data-original") or im.get("data-src") or im.get("src")
            if u: imgs.append(big(urljoin(url or BASE,u)))
        if imgs: ps.append((dt,title,url,imgs[0]))
    if not ps: raise RuntimeError("No MTP carta found")
    x=sorted(ps,key=lambda z:z[0],reverse=True)[0]
    print("LATEST MTP:",x[0],x[1])
    print("ONE CARTA IMAGE:",x[3])
    return x

def feed_entries():
    return get(FEED).json().get("feed",{}).get("entry",[])

def image_for_date(want):
    for e in feed_entries():
        title=e.get("title",{}).get("$t","")
        if pdate(title)!=want: continue
        body=e.get("content",{}).get("$t","") or e.get("summary",{}).get("$t","")
        soup=BeautifulSoup(body,"html.parser")
        for im in soup.find_all("img"):
            u=im.get("data-original") or im.get("data-src") or im.get("src")
            if u: return big(urljoin(BASE,u))
    return None

def decode(raw):
    a=np.frombuffer(raw,np.uint8)
    im=cv2.imdecode(a,cv2.IMREAD_COLOR)
    if im is None: raise RuntimeError("image decode failed")
    return im

def cell_feature(cell):
    g=cv2.cvtColor(cell,cv2.COLOR_BGR2GRAY)
    g=cv2.resize(g,(48,64),interpolation=cv2.INTER_AREA)
    # isolate bright digit strokes; normalize away poster/cell colour
    g=cv2.GaussianBlur(g,(3,3),0)
    _,b=cv2.threshold(g,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    # choose polarity with smaller foreground
    if np.mean(b>0) > .55: b=255-b
    # centralize glyph bounding box
    ys,xs=np.where(b>0)
    if len(xs)>20:
        x0,x1=xs.min(),xs.max()+1; y0,y1=ys.min(),ys.max()+1
        glyph=b[y0:y1,x0:x1]
        canvas=np.zeros((64,48),np.uint8)
        scale=min(42/max(glyph.shape[1],1),56/max(glyph.shape[0],1))
        nw=max(1,int(glyph.shape[1]*scale)); nh=max(1,int(glyph.shape[0]*scale))
        glyph=cv2.resize(glyph,(nw,nh),interpolation=cv2.INTER_AREA)
        yy=(64-nh)//2; xx=(48-nw)//2
        canvas[yy:yy+nh,xx:xx+nw]=glyph
        b=canvas
    return (b.astype(np.float32)/255.0).reshape(-1)

def detect_16_cells(im):
    h,w=im.shape[:2]
    # only chart side; excludes weekday/date on right
    roi=im[int(h*.35):int(h*.93), :int(w*.67)]
    hsv=cv2.cvtColor(roi,cv2.COLOR_BGR2HSV)

    # coloured chart boxes are highly saturated compared with white digits.
    mask=cv2.inRange(hsv,np.array([0,90,70]),np.array([179,255,255]))
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
    cnts,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

    rh,rw=roi.shape[:2]
    boxes=[]
    for c in cnts:
        x,y,bw,bh=cv2.boundingRect(c)
        ar=bw/max(bh,1)
        area=bw*bh
        if area>rh*rw*.006 and .55<ar<2.0 and bh>rh*.09 and bh<rh*.32:
            boxes.append((x,y,bw,bh))

    # If touching cells merge, use line/geometry fallback:
    if len(boxes)!=16:
        # find row bands from saturated pixels, then split each row into 4
        proj=(mask>0).sum(axis=1)
        active=proj>max(10,rw*.12)
        bands=[]; st=None
        for i,v in enumerate(active):
            if v and st is None: st=i
            if st is not None and (not v or i==len(active)-1):
                en=i if not v else i+1
                if en-st>rh*.07: bands.append((st,en))
                st=None
        # choose 4 largest plausible bands in vertical order
        bands=sorted(bands,key=lambda b:b[1]-b[0],reverse=True)[:4]
        bands=sorted(bands)
        rebuilt=[]
        for y0,y1 in bands:
            sub=mask[y0:y1]
            xp=(sub>0).sum(axis=0)
            act=xp>max(5,(y1-y0)*.15)
            xs=np.where(act)[0]
            if len(xs)<20: continue
            left,right=xs.min(),xs.max()+1
            width=(right-left)/4
            for j in range(4):
                x0=int(left+j*width); x1=int(left+(j+1)*width)
                rebuilt.append((x0,y0,x1-x0,y1-y0))
        boxes=rebuilt

    # V8.4 GEOMETRY FIX:
    # Previous versions misread four tall detected strips as four ROWS.
    # Logs proved the boxes were x=0/180/361/542, y=0, h=626:
    # they are FOUR COLUMNS spanning the chart height.
    # Split each column vertically into four cells, then transpose to
    # row-major order: row1 col1..4, row2 col1..4, etc.
    if len(boxes)==4:
        colboxes=sorted(boxes,key=lambda b:b[0]+b[2]/2)
        # Require tall column geometry; never silently treat columns as rows.
        if all(bh > bw*1.8 for x,y,bw,bh in colboxes):
            grid=[[None]*4 for _ in range(4)]
            for ci,(x,y,bw,bh) in enumerate(colboxes):
                px=max(2,int(bw*.07))
                py=max(1,int(bh*.01))
                x0=x+px; x1=x+bw-px
                y0=y+py; y1=y+bh-py
                usable=y1-y0
                print("COLUMN BLOCK",ci+1,":",x,y,bw,bh)
                for ri in range(4):
                    a=y0+round(ri*usable/4)
                    b=y0+round((ri+1)*usable/4)
                    gap=max(1,int((b-a)*.035))
                    cell=roi[a+gap:b-gap,x0:x1]
                    if cell.size==0:
                        return None
                    grid[ri][ci]=cell
            cells=[grid[r][c] for r in range(4) for c in range(4)]
            print("GEOMETRY FIX SUCCESS: 4 columns x 4 rows -> 16 cells")
            return cells

        # Support genuine four horizontal row blocks if poster layout changes.
        if all(bw > bh*1.8 for x,y,bw,bh in colboxes):
            rowboxes=sorted(colboxes,key=lambda b:b[1]+b[3]/2)
            cells=[]
            for ri,(x,y,bw,bh) in enumerate(rowboxes,1):
                px=max(1,int(bw*.01)); py=max(2,int(bh*.07))
                x0=x+px; x1=x+bw-px; y0=y+py; y1=y+bh-py
                usable=x1-x0
                print("ROW BLOCK",ri,":",x,y,bw,bh)
                for j in range(4):
                    a=x0+round(j*usable/4); b=x0+round((j+1)*usable/4)
                    gap=max(1,int((b-a)*.035))
                    cell=roi[y0:y1,a+gap:b-gap]
                    if cell.size==0: return None
                    cells.append(cell)
            print("ROW SPLIT SUCCESS: 4 rows x 4 columns -> 16 cells")
            return cells

        print("4 BLOCKS FOUND BUT GEOMETRY UNKNOWN - NO SAVE")
        return None

    if len(boxes)!=16:
        print("ROW/CELL DETECTION:",len(boxes),"blocks - expected 4 rows or 16 cells")
        return None

    # Also support posters where all 16 cells are individually separated.
    boxes=sorted(boxes,key=lambda b:b[1]+b[3]/2)
    rows=[]
    for b in boxes:
        cy=b[1]+b[3]/2
        placed=False
        for r in rows:
            rcy=np.mean([q[1]+q[3]/2 for q in r])
            if abs(cy-rcy)<rh*.10:
                r.append(b); placed=True; break
        if not placed: rows.append([b])
    rows=[sorted(r,key=lambda b:b[0]) for r in rows if len(r)==4]
    rows=sorted(rows,key=lambda r:np.mean([b[1] for b in r]))
    if len(rows)!=4:
        print("VISUAL ROW DETECTION:",[len(r) for r in rows])
        return None

    cells=[]
    for r in rows:
        for x,y,bw,bh in r:
            px=max(2,int(bw*.08)); py=max(2,int(bh*.08))
            cells.append(roi[y+py:y+bh-py,x+px:x+bw-px])
    print("VISUAL GRID SUCCESS: 16 separate cells")
    return cells

def load_templates():
    if not TPL.exists(): return None,None
    z=np.load(TPL)
    return z["X"],z["y"].astype(str)

def save_templates_multi():
    feats=[]; labels=[]; used=[]
    for day,digits in VERIFIED.items():
        u=image_for_date(day)
        if not u:
            print("TRAIN SKIP - image not in feed:",day)
            continue
        try:
            im=decode(get(u).content)
            cells=detect_16_cells(im)
        except Exception as e:
            print("TRAIN SKIP:",day,e); continue
        if cells is None or len(cells)!=16:
            print("TRAIN SKIP - grid failed:",day); continue
        for c,d in zip(cells,digits):
            # Store all four normalized visual variants per verified cell.
            for f in adaptive_features(c):
                feats.append(f); labels.append(d)
        used.append(day)
    if not feats:
        return None,None
    X=np.stack(feats); y=np.array(labels)
    np.savez_compressed(TPL,X=X,y=y)
    print("MULTI TEMPLATES TRAINED:",len(y),"samples from",used)
    print("DIGIT COUNTS:",{d:int(np.sum(y==d)) for d in sorted(set(y))})
    return X,y

def adaptive_features(cell):
    # V8.3: compare several illumination/threshold variants so changes
    # in poster colour/background do not depend on one Otsu result.
    g=cv2.cvtColor(cell,cv2.COLOR_BGR2GRAY)
    variants=[]
    for mode in range(4):
        z=g.copy()
        if mode==1:
            z=cv2.equalizeHist(z)
        elif mode==2:
            z=cv2.GaussianBlur(z,(5,5),0)
        elif mode==3:
            z=cv2.normalize(z,None,0,255,cv2.NORM_MINMAX)
        # Reuse the same centering pipeline by converting back to BGR.
        variants.append(cell_feature(cv2.cvtColor(z,cv2.COLOR_GRAY2BGR)))
    return variants

def classify(cells,X,y):
    out=[]; ratios=[]; agreements=[]
    digits=sorted(set(map(str,y)))
    for ci,c in enumerate(cells,1):
        variant_votes=[]
        variant_ratios=[]
        for f in adaptive_features(c):
            # Score each digit by its 3 nearest verified templates.
            scores={}
            for d in digits:
                idx=np.where(y==d)[0]
                ds=np.mean((X[idx]-f)**2,axis=1)
                k=min(3,len(ds))
                scores[d]=float(np.mean(np.partition(ds,k-1)[:k]))
            ranked=sorted(scores.items(),key=lambda z:z[1])
            best,bd=ranked[0]; second,sd=ranked[1]
            variant_votes.append(best)
            variant_ratios.append(sd/max(bd,1e-7))
        counts={d:variant_votes.count(d) for d in set(variant_votes)}
        pred=max(counts,key=lambda d:(counts[d],sum(r for v,r in zip(variant_votes,variant_ratios) if v==d)))
        agree=counts[pred]
        good=[r for v,r in zip(variant_votes,variant_ratios) if v==pred]
        ratio=max(good) if good else 1.0
        out.append(pred); agreements.append(agree); ratios.append(ratio)
        print(f"CELL {ci:02d}: {pred} agreement={agree}/4 separation={ratio:.3f}")

    print("MULTI VISUAL RESULT:","".join(out))
    print("MULTI AGREEMENT:",agreements)
    print("MULTI MIN SEPARATION:",round(min(ratios),3))
    # Majority across variants + nearest-class separation.
    cell_ok=[(a>=3 and r>=1.015) or (a>=2 and r>=1.18) for a,r in zip(agreements,ratios)]
    confident=all(cell_ok)
    print("CELL VALID:",cell_ok)
    return out,confident

def main():
    db=load_db()
    try:dt,title,url,imgurl=latest()
    except Exception as e:
        print("DISCOVERY FAILED:",e); save_db(db); return

    try:
        im=decode(get(imgurl).content)
        cells=detect_16_cells(im)
    except Exception as e:
        print("VISUAL FETCH/GRID FAILED:",e); cells=None

    if cells is None:
        print("NO SAVE - clean DB kept"); save_db(db); return

    X,y=load_templates()

    # Train from several verified historical charts, not one poster.
    if X is None:
        X,y=save_templates_multi()
        if X is None:
            print("MULTI TEMPLATE TRAINING FAILED - NO SAVE")
            save_db(db); return

    if dt in VERIFIED:
        nums=list(VERIFIED[dt])
        print("VERIFIED HISTORICAL DATE:",dt,"".join(nums))
    else:
        nums,confident=classify(cells,X,y)
        if not confident:
            print("MULTI MATCH AMBIGUOUS - NO SAVE")
            save_db(db); return

    if dt in db:
        if dt in VERIFIED:
            old="".join(map(str,db[dt].get("numbers",[]))); good="".join(nums)
            if old!=good:
                print("REPAIR VERIFIED DATE:",dt,old,"->",good)
                db[dt]={"date":dt,"numbers":list(nums),"source":"MTP-CLEAN-LEARNING-V10-VERIFIED","url":url,"auto":True}
                save_db(db)
            else:
                print("VERIFIED DATE ALREADY CORRECT:",dt); save_db(db)
            return
        print("DATE ALREADY SAVED - NO OVERWRITE:",dt)
        save_db(db); return

    db[dt]={
        "date":dt,"numbers":list(nums),
        "source":"MTP-CLEAN-LEARNING-V10",
        "url":url,"auto":True
    }
    print("AUTO SAVED:",dt,"".join(nums))
    print("CLEAN MODE: prediction NOT added to training templates")
    save_db(db)

if __name__=="__main__": main()
