# Fetch the Saudi Center recording of Anas Al-Miman (114 surahs) and re-encode for phones.
import json, os, re, subprocess, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
NAMES = json.load(open(os.path.join(os.path.dirname(__file__), 'surah_names.json')))
def norm(t):
    t = re.sub(r'[ً-ْٰـ]', '', t)
    for a, b in (('أ', 'ا'), ('إ', 'ا'), ('آ', 'ا'), ('ٱ', 'ا'), ('ة', 'ه'), ('ى', 'ي'), ('ؤ', 'و'), ('ئ', 'ي')): t = t.replace(a, b)
    return re.sub(r'\s+', '', t)
NN = {norm(n): i + 1 for i, n in enumerate(NAMES)}
ALIAS = {'الاسراء': 17, 'غافر': 40, 'فصلت': 41, 'محمد': 47, 'الانسان': 76, 'المسد': 111, 'التوبه': 9, 'الملك': 67, 'النبا': 78, 'الشرح': 94, 'تبارك': 67, 'عم': 78, 'الدهر': 76, 'المومن': 40, 'بنياسراييل': 17, 'القتال': 47, 'اللهب': 111, 'الانشراح': 94, 'براءه': 9}
def get(u, t=60):
    r = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(r, timeout=t).read()
vids = {}
for l in open('out/qhc_videos.txt', encoding='utf-8'):
    if 'أنس الميمان' not in l or 'سورة' not in l: continue
    p = [x.strip() for x in l.split('|')]
    if len(p) < 3: continue
    nm = norm(p[1].replace('سورة', ''))
    s = NN.get(nm) or ALIAS.get(nm)
    if not s:
        for k, v in NN.items():
            if k.replace('ال', '', 1) == nm.replace('ال', '', 1): s = v
    if s and s not in vids: vids[s] = p[2]
    elif not s: print('UNMAPPED', p[1], flush=True)
print('mapped', len(vids), 'missing', [s for s in range(1, 115) if s not in vids], flush=True)
try: inst = [x[1]['uri'] for x in json.loads(get('https://api.invidious.io/instances.json?sort_by=health', 20)) if x[1].get('type') == 'https']
except Exception as e: inst = []
inst = ['https://yt.chocolatemoo53.com'] + [i for i in inst if 'chocolatemoo' not in i]
ref = json.load(open('out/mq_282.json'))
refdur = {s: ref[str(s)][-1][1] / 1000 for s in range(1, 115)}
os.makedirs('site/audio/miman', exist_ok=True)
def fetch(v, out):
    for rnd in range(4):
        for i in inst:
            try:
                j = json.loads(get(i + '/api/v1/videos/' + v + '?local=true', 30))
                af = [f for f in j.get('adaptiveFormats', []) if 'audio' in f.get('type', '')]
                if not af: continue
                af.sort(key=lambda f: -int(f.get('bitrate') or 0))
                u = af[0]['url']; u = u if u.startswith('http') else i + u
                d = get(u, 600)
                if len(d) < 20000: continue
                open(out, 'wb').write(d); return i
            except Exception as e:
                print('  retry', i, str(e)[:60], flush=True)
        time.sleep(20 * (rnd + 1))
    return None
bad = []
for s in range(1, 115):
    if s not in vids: bad.append(s); continue
    src = fetch(vids[s], '/tmp/in.bin')
    if not src: bad.append(s); print(s, 'FAILED', flush=True); continue
    o = 'site/audio/miman/%03d.mp3' % s
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', '/tmp/in.bin', '-map', '0:a:0', '-map_metadata', '-1', '-ac', '1', '-ar', '22050', '-b:a', '48k', o], check=True)
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', o], capture_output=True, text=True).stdout.strip() or 0)
    print(s, vids[s], os.path.getsize(o), 'dur %.0f ratio %.2f' % (dur, dur / refdur[s]), src, flush=True)
    if not (0.45 < dur / refdur[s] < 2.6): bad.append(s); print('  SUSPECT DURATION', flush=True)
    time.sleep(1.5)
json.dump({'bad': bad, 'vids': vids}, open('out/miman_yt.json', 'w'))
print('BAD', bad, flush=True)
if bad: sys.exit('incomplete: %s' % bad)
