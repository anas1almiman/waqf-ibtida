# Ayah timings for whole-surah recitations: pauses in the recording, chosen by dynamic
# programming so that ayah durations follow a reference reciter whose timings are exact.
import json, subprocess, sys, os, urllib.request, time
import numpy as np

def get(url, path=None, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'waqf-ibtida-timing/1.0'})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if path:
                open(path, 'wb').write(data)
            return data
        except Exception as e:
            print('retry', url, e, flush=True); time.sleep(3 + 5 * i)
    raise RuntimeError('failed ' + url)

def mq_timing(read, s):
    j = json.loads(get('https://mp3quran.net/api/v3/ayat_timing?surah=%d&read=%d' % (s, read)))
    out = {}
    for x in j:
        a = int(x['ayah'])
        if a >= 1:
            out[a] = [int(x['start_time']), int(x['end_time'])]
    n = max(out)
    return [out[a] for a in range(1, n + 1)]

def envelope(path):
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', '8000', '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    hop = 80  # 10 ms
    m = len(x) // hop
    fr = x[:m * hop].reshape(m, hop)
    db = 10 * np.log10((fr ** 2).mean(1) + 1.0)
    k = 5
    pad = np.pad(db, (k // 2, k // 2), mode='edge')
    db = np.median(np.lib.stride_tricks.sliding_window_view(pad, k), axis=1)
    return db  # one value per 10 ms

def pauses(db, min_len=18):
    lo, hi = np.percentile(db, 4), np.percentile(db, 70)
    thr = lo + 0.33 * (hi - lo)
    q = db < thr
    sound = np.where(~q)[0]
    first, last = (sound[0], sound[-1]) if len(sound) else (0, len(db) - 1)
    c = []
    i = first
    while i <= last:
        if q[i]:
            j = i
            while j <= last and q[j]:
                j += 1
            if j - i >= min_len:
                c.append((i / 100.0, j / 100.0))
            i = j
        else:
            i += 1
    return c, first / 100.0, (last + 1) / 100.0

def align(ref, db, n):
    """ref: [[start_ms,end_ms]]*n exact timings of the reference; returns [[start_ms,end_ms]]*n for this audio."""
    cand, t0, t1 = pauses(db)
    R = np.array(ref, dtype=float) / 1000.0
    rs, re_ = R[0, 0], R[-1, 1]
    lead = rs > 1.2  # basmala/isti'adha before ayah 1 in the reference
    # reference boundaries (midpoints of the gaps), as fractions of the reference reading
    rb = []
    if lead:
        rb.append(rs - 0.15)
    for k in range(n - 1):
        rb.append((R[k, 1] + R[k + 1, 0]) / 2)
    rb = np.array(rb)
    span_r = re_ - 0.0
    span_t = t1 - t0
    E = t0 + rb / span_r * span_t                       # expected boundary times
    if not len(rb):
        return [[int(t0 * 1000), int(t1 * 1000)]]
    ct = np.array([(a + b) / 2 for a, b in cand]) if cand else np.zeros(0)
    cd = np.array([b - a for a, b in cand]) if cand else np.zeros(0)
    # virtual candidates (reciter joined two ayat): at each expected point, with a penalty
    vt = E.copy()
    allt = np.concatenate([ct, vt]); alld = np.concatenate([cd, np.full(len(vt), -1.0)])
    order = np.argsort(allt); allt = allt[order]; alld = alld[order]
    B = len(rb)
    seg = np.diff(np.concatenate([[0.0], rb])) / span_r * span_t   # expected durations between boundaries
    win = max(25.0, 0.12 * span_t)
    prev_idx = None; prev_cost = None; prev_t = np.array([t0]); back = []
    for k in range(B):
        lo = np.searchsorted(allt, E[k] - win); hi = np.searchsorted(allt, E[k] + win)
        idx = np.arange(lo, hi)
        if not len(idx):
            idx = np.array([np.argmin(abs(allt - E[k]))])
        tt = allt[idx]; dd = alld[idx]
        node = np.where(dd < 0, 2.5, -1.6 * np.log1p(np.minimum(dd, 1.5) / 0.25)) + ((tt - E[k]) / (0.08 * span_t + 4)) ** 2
        D = seg[k]; sig = 0.28 * D + 0.9
        if k == 0:
            pair = ((tt - t0) - D) / sig
            cost = node + pair ** 2; bp = np.zeros(len(idx), dtype=int)
        else:
            dt = tt[None, :] - prev_t[:, None]
            pc = ((dt - D) / sig) ** 2
            pc[dt <= 0.4] = np.inf
            tot = prev_cost[:, None] + pc
            bp = np.argmin(tot, axis=0); cost = tot[bp, np.arange(len(idx))] + node
        back.append((idx, bp)); prev_cost = cost; prev_t = tt; prev_idx = idx
    # final: last ayah should end near t1
    D = (span_r - rb[-1]) / span_r * span_t
    fin = prev_cost + (((t1 - prev_t) - D) / (0.28 * D + 0.9)) ** 2
    j = int(np.argmin(fin)); sel = []
    for k in range(B - 1, -1, -1):
        idx, bp = back[k]; sel.append(idx[j]); j = bp[j]
    sel = sel[::-1]
    # boundary → end of the earlier ayah and start of the next
    def edges(i):
        t = allt[i]; d = alld[i]
        if d < 0:
            return t, t
        # find the pause interval
        a, b = min(cand, key=lambda p: abs((p[0] + p[1]) / 2 - t))
        return a + 0.06, max(a + 0.06, b - 0.10)
    out = []; cur = t0
    bi = 0
    if lead:
        e0, s1 = edges(sel[0]); cur = s1; bi = 1
    for a in range(n):
        if a < n - 1:
            e, nx = edges(sel[bi]); bi += 1
        else:
            e, nx = t1, t1
        out.append([int(round(cur * 1000)), int(round(e * 1000))]); cur = nx
    return out

def errstats(pred, true):
    p = np.array([x[0] for x in pred]); t = np.array([x[0] for x in true])
    return np.abs(p - t)

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'ref':
        reads = [int(x) for x in sys.argv[2].split(',')]
        os.makedirs('out', exist_ok=True)
        for r in reads:
            d = {}
            for s in range(1, 115):
                d[s] = mq_timing(r, s)
            json.dump(d, open('out/mq_%d.json' % r, 'w'), separators=(',', ':'))
            print('ref', r, 'ok', flush=True)
    elif mode == 'align':
        name, base, refread = sys.argv[2], sys.argv[3], int(sys.argv[4])
        truth = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        surahs = range(1, 115) if len(sys.argv) <= 6 else [int(x) for x in sys.argv[6].split(',')]
        ref = json.load(open('out/mq_%d.json' % refread))
        tru = json.load(open('out/mq_%d.json' % truth)) if truth else None
        res = {}; errs = []
        for s in surahs:
            f = '/tmp/a.mp3'
            get(base + '%03d.mp3' % s, f)
            db = envelope(f)
            n = len(ref[str(s)])
            res[s] = align(ref[str(s)], db, n)
            if tru:
                e = errstats(res[s], tru[str(s)]); errs.extend(e.tolist())
                print(s, 'n', n, 'median', int(np.median(e)), 'p90', int(np.percentile(e, 90)), 'within1s', round(float((e < 1000).mean()), 3), flush=True)
            else:
                print(s, 'n', n, 'ok', flush=True)
        os.makedirs('out', exist_ok=True)
        json.dump(res, open('out/al_%s.json' % name, 'w'), separators=(',', ':'))
        if errs:
            e = np.array(errs)
            print('ALL median', int(np.median(e)), 'p90', int(np.percentile(e, 90)), 'within0.5s', round(float((e < 500).mean()), 3), 'within1s', round(float((e < 1000).mean()), 3), 'within2s', round(float((e < 2000).mean()), 3))
