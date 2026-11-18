#!/usr/bin/env python3
"""يبني idx/ighatha.idx مشفّرًا بنفس كلمة سر الكتاب (WQ1: PBKDF2-SHA256 600000 + AES-GCM).
python3 tools/build_ighatha_idx.py <مجلد نصوص p-###.txt> <كلمة السر>"""
import sys,os,re,glob,json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
MARKS=re.compile('[ؐ-ًؚ-ٰٟۖ-ۭـ]')
def norm(s):
    s=MARKS.sub('',s);s=re.sub('[أإآٱ]','ا',s).replace('ى','ي').replace('ة','ه').replace('ؤ','و').replace('ئ','ي')
    s=re.sub('[^ء-ي0-9٠-٩ ]',' ',s);return re.sub('\\s+',' ',s).strip()
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P=[];N=[]
for f in sorted(glob.glob(sys.argv[1]+'/p-*.txt')):
    t=norm(open(f,encoding='utf8').read())
    if len(t)>=20:P.append(t);N.append(int(re.search(r'p-(\d+)',f).group(1)))
raw=json.dumps({'id':'ighatha','p':P,'n':N},ensure_ascii=False,separators=(',',':')).encode()
salt=os.urandom(16);iv=os.urandom(12)
k=PBKDF2HMAC(hashes.SHA256(),32,salt,600000).derive(sys.argv[2].encode())
open(ROOT+'/idx/ighatha.idx','wb').write(b'WQ1'+salt+iv+AESGCM(k).encrypt(iv,raw,None))
print(len(P),'pages',len(raw)//1024,'KB')
