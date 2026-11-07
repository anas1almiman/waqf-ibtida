# Ayah timings by aligning a recitation to a reference recitation of the same surah whose
# ayah timings are exact (MP3Quran): log-mel features, banded DTW, then snapping each
# boundary to the nearest pause in the recitation.
import json, subprocess, sys, os, time
import numpy as np
from numba import njit
sys.path.insert(0, os.path.dirname(__file__))
from align import get, envelope, pauses, errstats

SR = 16000; HOP = 160; POOL = 10   # 10 ms frames pooled to 100 ms

def load(path):
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

def feats(y):
    import librosa
    m = librosa.feature.melspectrogram(y=y, sr=SR, n_fft=400, hop_length=HOP, n_mels=40, fmin=60, fmax=7600)
    l = np.log(m + 1e-6)
    n = l.shape[1] // POOL
    l = l[:, :n * POOL].reshape(40, n, POOL).mean(2)
    mf = librosa.feature.mfcc(S=l, n_mfcc=20)[1:]
    d = librosa.feature.delta(mf)
    f = np.vstack([mf, d]).T
    f = (f - f.mean(0)) / (f.std(0) + 1e-6)
    f /= np.linalg.norm(f, axis=1, keepdims=True) + 1e-6
    return f.astype(np.float32)

@njit(cache=True)
def banded_dtw(A, B, band):
    n, m = A.shape[0], B.shape[0]
    INF = 1e18
    W = 2 * band + 1
    D = np.full((n, W), INF)
    P = np.zeros((n, W), dtype=np.int8)
    for i in range(n):
        c = int(i * (m - 1) / max(1, n - 1))
        for w in range(W):
            j = c - band + w
            if j < 0 or j >= m:
                continue
            d = 1.0
            for k in range(A.shape[1]):
                d -= A[i, k] * B[j, k]
            if i == 0 and j == 0:
                D[i, w] = d; continue
            best = INF; bp = 0
            # (i-1, j-1)
            if i > 0:
                cp = int((i - 1) * (m - 1) / max(1, n - 1))
                wp = j - 1 - (cp - band)
                if 0 <= wp < W and D[i - 1, wp] < best:
                    best = D[i - 1, wp]; bp = 1
                wp2 = j - (cp - band)
                if 0 <= wp2 < W and D[i - 1, wp2] + 0.15 < best:
                    best = D[i - 1, wp2] + 0.15; bp = 2
            if w > 0 and D[i, w - 1] + 0.15 < best:
                best = D[i, w - 1] + 0.15; bp = 3
            D[i, w] = best + d; P[i, w] = bp
    # backtrack from (n-1, m-1)
    path_j = np.full(n, -1)
    i = n - 1; j = m - 1
    while i >= 0 and j >= 0:
        c = int(i * (m - 1) / max(1, n - 1)); w = j - (c - band)
        if path_j[i] < 0:
            path_j[i] = j
        if w < 0 or w >= W:
            break
        bp = P[i, w]
        if bp == 1:
            i -= 1; j -= 1
        elif bp == 2:
            i -= 1
        elif bp == 3:
            j -= 1
        else:
            break
    return path_j

def align_dtw(ref_y, ref_t, y):
    """ref_t: [[start_ms,end_ms]] exact for ref audio; returns same for y."""
    A = feats(ref_y); B = feats(y)
    n, m = len(A), len(B)
    band = int(max(60, 0.12 * max(n, m)))
    pj = banded_dtw(A, B, band)
    fps = SR / HOP / POOL  # 10
    def map_t(sec):
        i = min(n - 1, max(0, int(round(sec * fps))))
        return pj[i] / fps
    db = envelope_from(y)
    cand, t0, t1 = pauses(db, min_len=12)
    out = []
    for k, (s, e) in enumerate(ref_t):
        out.append([map_t(s / 1000.0), map_t(e / 1000.0)])
    # snap boundaries (end of ayah k / start of k+1) into the pause between them
    for k in range(len(out)):
        if k == 0:
            st = out[0][0]
            near = [p for p in cand if abs(p[1] - st) < 1.6]
            if near:
                out[0][0] = min(near, key=lambda p: abs(p[1] - st))[1] - 0.08
        if k < len(out) - 1:
            mid = (out[k][1] + out[k + 1][0]) / 2
            near = [p for p in cand if abs((p[0] + p[1]) / 2 - mid) < 1.8]
            if near:
                p = max(near, key=lambda p: (p[1] - p[0]) - 0.35 * abs((p[0] + p[1]) / 2 - mid))
                out[k][1] = p[0] + 0.06; out[k + 1][0] = max(out[k][1], p[1] - 0.08)
        else:
            out[k][1] = min(t1 + 0.1, max(out[k][1], out[k][0] + 0.5))
    return [[int(round(a * 1000)), int(round(b * 1000))] for a, b in out]

def envelope_from(y):
    x = (y * 32768).astype(np.float32)
    hop = SR // 100
    m = len(x) // hop
    fr = x[:m * hop].reshape(m, hop)
    db = 10 * np.log10((fr ** 2).mean(1) + 1.0)
    k = 5
    pad = np.pad(db, (k // 2, k // 2), mode='edge')
    return np.median(np.lib.stride_tricks.sliding_window_view(pad, k), axis=1)

if __name__ == '__main__':
    name, base, refbase, refread = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    truth = int(sys.argv[5]); surahs = [int(x) for x in sys.argv[6].split(',')] if len(sys.argv) > 6 and sys.argv[6] != 'all' else range(1, 115)
    ref = json.load(open('out/mq_%d.json' % refread))
    tru = json.load(open('out/mq_%d.json' % truth)) if truth else None
    res = {}; errs = []
    os.makedirs('out', exist_ok=True)
    for s in surahs:
        t0 = time.time()
        get(refbase + '%03d.mp3' % s, '/tmp/r.mp3'); get(base + '%03d.mp3' % s, '/tmp/a.mp3')
        res[s] = align_dtw(load('/tmp/r.mp3'), ref[str(s)], load('/tmp/a.mp3'))
        msg = '%d n %d %.0fs' % (s, len(res[s]), time.time() - t0)
        if tru:
            e = errstats(res[s], tru[str(s)]); errs.extend(e.tolist())
            msg += ' median %d p90 %d within1s %.3f' % (np.median(e), np.percentile(e, 90), (e < 1000).mean())
        print(msg, flush=True)
        json.dump(res, open('out/al_%s.json' % name, 'w'), separators=(',', ':'))
    if errs:
        e = np.array(errs)
        print('ALL median', int(np.median(e)), 'p90', int(np.percentile(e, 90)), 'within0.5s', round(float((e < 500).mean()), 3), 'within1s', round(float((e < 1000).mean()), 3), 'within2s', round(float((e < 2000).mean()), 3))
