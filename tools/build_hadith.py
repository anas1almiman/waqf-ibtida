#!/usr/bin/env python3
"""يبني فهارس الكتب الستة من مستودع hadith-api (ara-*.min.json).
الاستعمال: python3 tools/build_hadith.py <مجلد editions>"""
import sys,os,re,json
MARKS=re.compile('[ؐ-ًؚ-ٰٟۖ-ۭـ]')
def norm(s):
    s=MARKS.sub('',s);s=re.sub('[أإآٱ]','ا',s).replace('ى','ي').replace('ة','ه').replace('ؤ','و').replace('ئ','ي')
    s=re.sub('[^ء-ي0-9٠-٩ ]',' ',s);return re.sub('\\s+',' ',s).strip()
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));src=sys.argv[1]
mf=json.load(open(f'{ROOT}/idx/manifest.json'))
for b in ['bukhari','muslim','abudawud','tirmidhi','nasai','ibnmajah']:
    hs=json.load(open(f'{src}/ara-{b}.min.json'))['hadiths']
    P=[];N=[]
    for h in hs:
        t=norm(h.get('text') or '')
        if len(t)<8:continue
        P.append(t);N.append(h['hadithnumber'])
    json.dump({'id':'h_'+b,'p':P,'n':N},open(f'{ROOT}/idx/h_{b}.json','w',encoding='utf8'),ensure_ascii=False,separators=(',',':'))
    mf['h_'+b]=len(P);print(b,len(P))
json.dump(mf,open(f'{ROOT}/idx/manifest.json','w'),sort_keys=True)
