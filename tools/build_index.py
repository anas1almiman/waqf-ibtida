#!/usr/bin/env python3
"""يبني فهرس البحث الذكي لكتاب مصوّر.
الاستعمال:  python3 tools/build_index.py <book_id>
يقرأ صور books/<id>/ ويستخرج نصها (Tesseract ara) ثم يكتب idx/<id>.json
ويحدّث idx/manifest.json. أعد تشغيله لأي كتاب جديد يُضاف للمكتبة."""
import sys,os,re,glob,json,subprocess
from multiprocessing import Pool
from PIL import Image
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKS=re.compile('[ؐ-ًؚ-ٰٟۖ-ۭـ]')
def norm(s):
    s=MARKS.sub('',s)
    s=re.sub('[أإآٱ]','ا',s).replace('ى','ي').replace('ة','ه').replace('ؤ','و').replace('ئ','ي')
    s=re.sub('[^ء-ي0-9٠-٩ \n]',' ',s)
    return re.sub('\\s+',' ',s).strip()
def ocr(f):
    t='/tmp/_ocr_%d.png'%os.getpid();Image.open(f).convert('L').save(t)
    return subprocess.run(['tesseract',t,'stdout','-l','ara','--psm','6'],capture_output=True,text=True).stdout
if __name__=='__main__':
    bid=sys.argv[1];fs=sorted(glob.glob(f'{ROOT}/books/{bid}/p*.*'))
    cache=sys.argv[2] if len(sys.argv)>2 else None  # مجلد نصوص جاهزة p####.txt
    def get(f):
        if cache:
            c=os.path.join(cache,os.path.basename(f).split('.')[0]+'.txt')
            if os.path.exists(c):return open(c,encoding='utf8').read()
        return None
    raw=[get(f) for f in fs]
    miss=[f for f,r in zip(fs,raw) if r is None]
    if miss:
        with Pool(2) as p:out=p.map(ocr,miss)
        it=iter(out);raw=[r if r is not None else next(it) for r in raw]
    pages=[norm(r) for r in raw]
    os.makedirs(f'{ROOT}/idx',exist_ok=True)
    json.dump({'id':bid,'p':pages},open(f'{ROOT}/idx/{bid}.json','w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
    mf=f'{ROOT}/idx/manifest.json';m=json.load(open(mf)) if os.path.exists(mf) else {}
    m[bid]=len(pages);json.dump(m,open(mf,'w'),sort_keys=True)
    print(bid,len(pages),'pages',sum(len(p) for p in pages)//1024,'KB')
