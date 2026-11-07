# Choose a complete Anas Al-Miman mushaf, check that file N is surah N (durations against a
# (rerun: patient downloads)
# reference reciter), re-encode for phones and write audio/miman/NNN.mp3.
import json, os, re, subprocess, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from align import get
ITEMS = ['anas-almyman', 'alfirdwsiy1433_22_201812']
ref = json.load(open('out/mq_282.json'))
refdur = {s: ref[str(s)][-1][1] / 1000 for s in range(1, 115)}
def files(item):
    m = json.loads(get('https://archive.org/metadata/' + item))
    fs = {}
    for f in m['files']:
        n = f['name']
        if not n.lower().endswith('.mp3'): continue
        k = re.findall(r'(\d{1,3})', os.path.basename(n))
        if not k: continue
        s = int(k[0])
        if 1 <= s <= 114 and s not in fs: fs[s] = (n, float(f.get('length') or 0))
    return fs
best = None
for it in ITEMS:
    try: fs = files(it)
    except Exception as e: print(it, 'metadata failed', e); continue
    ok = [s for s in range(1, 115) if s in fs]
    rat = [fs[s][1] / refdur[s] for s in ok if fs[s][1] > 0 and refdur[s] > 120]
    rat.sort()
    med = rat[len(rat) // 2] if rat else 0
    bad = [s for s in ok if fs[s][1] > 0 and refdur[s] > 120 and not (0.6 * med < fs[s][1] / refdur[s] < 1.6 * med)]
    print(it, 'files', len(ok), 'median ratio %.2f' % med, 'outliers', bad[:20], flush=True)
    if len(ok) == 114 and len(bad) <= 2 and best is None: best = (it, fs)
if not best: sys.exit('no complete item')
it, fs = best; print('USING', it, flush=True)
os.makedirs('site/audio/miman', exist_ok=True)
for s in range(1, 115):
    n = fs[s][0]
    url = 'https://archive.org/download/%s/%s' % (it, urllib.request.quote(n))
    get(url, '/tmp/in.mp3')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', '/tmp/in.mp3', '-map', '0:a:0', '-map_metadata', '-1', '-ac', '1', '-ar', '22050', '-b:a', '48k', 'site/audio/miman/%03d.mp3' % s], check=True)
    print(s, n, os.path.getsize('site/audio/miman/%03d.mp3' % s), flush=True)
