import numpy as np, soundfile as sf, os, sys, json
from kokoro_onnx import Kokoro
K = Kokoro("kmodel/kokoro-v1.0.onnx", "kmodel/voices-v1.0.bin")
VOICE = "af_heart"
SR = 24000
FR = 240  # 10 ms
OUT = "snd"; os.makedirs(OUT, exist_ok=True)

def synth(ph, speed=1.0):
    a, sr = K.create(ph, voice=VOICE, speed=speed, is_phonemes=True)
    return np.asarray(a, dtype=np.float32)

def frames(a):
    n = len(a) // FR
    feats = []
    for i in range(n):
        x = a[i*FR:(i+1)*FR]
        r = float(np.sqrt(np.mean(x**2)))
        S = np.abs(np.fft.rfft(x * np.hanning(len(x)))) + 1e-9
        f = np.fft.rfftfreq(len(x), 1/SR)
        hi = S[f > 3000].sum() / S.sum()
        lo = S[f < 450].sum() / S[f < 4000].sum()
        feats.append((r, hi, lo))
    return feats

def pattern(a):
    fs = frames(a); m = max(f[0] for f in fs)
    s = ""
    for r, hi, lo in fs:
        if r < m*0.04: s += "."
        elif hi > 0.5: s += "N"
        elif lo > 0.55: s += "n"
        else: s += "V"
    return s

def fade(a, fin=0.015, fout=0.04):
    a = a.copy(); i = int(fin*SR); o = int(fout*SR)
    if i: a[:i] *= np.linspace(0, 1, i)
    if o: a[-o:] *= np.linspace(1, 0, o)
    return a

def stretch(seg, target):
    print("   stretch src", round(len(seg)/SR*1000), "ms", file=sys.stderr)
    if len(seg) >= target: return seg[:target]
    if len(seg) < int(0.05*SR): raise ValueError("segment too short: %d ms" % (len(seg)/SR*1000))
    core = seg[int(len(seg)*.2):int(len(seg)*.8)]
    xf = min(int(0.02*SR), len(core)//3)
    out = seg[:int(len(seg)*.8)].copy()
    while len(out) < target:
        w = np.linspace(0, 1, xf)
        out[-xf:] = out[-xf:]*(1-w) + core[:xf]*w
        out = np.concatenate([out, core[xf:]])
    return out[:target]

def norm(a, peak=0.8):
    m = np.max(np.abs(a)) or 1
    return a * (peak/m)

def active(a, th=0.04):
    fs = frames(a); m = max(f[0] for f in fs)
    on = [i for i, f in enumerate(fs) if f[0] > m*th]
    return on[0]*FR, (on[-1]+1)*FR

def main_run(a, th=0.12, gap=2):
    """longest stretch of loud frames (ignores the engine's quiet pre-roll)"""
    fs = frames(a); m = max(f[0] for f in fs)
    on = [f[0] > m*th for f in fs]
    best = (0, 0); i = 0
    while i < len(on):
        if on[i]:
            j = i; miss = 0
            while j < len(on) and (on[j] or miss < gap):
                miss = 0 if on[j] else miss+1; j += 1
            j -= miss
            if j-i > best[1]-best[0]: best = (i, j)
            i = j
        else: i += 1
    return best[0]*FR, best[1]*FR

def vowel(ph):
    a = synth("ˈ"+ph, 0.85); s, e = main_run(a, 0.1)
    return fade(a[s:e+int(.03*SR)], 0.01, 0.07)

def v_sound():
    a = synth("ˈɛv", 0.8); fs = frames(a); m = max(f[0] for f in fs)
    s, e = main_run(a, 0.1)
    loud = [i for i in range(s//FR, e//FR) if fs[i][0] > m*0.5]
    st = (loud[-1]+2)*FR
    _, end = main_run(a[st:], 0.05)
    return a[st:st+end]

def tail_after_vowel(ph, carrier="ɑ", skip=0.03, rel=0.55):
    a = synth("ˈ"+carrier+ph, 0.8); fs = frames(a); m = max(f[0] for f in fs)
    loud = [i for i, f in enumerate(fs) if f[0] > m*rel]
    st = (loud[-1]+1)*FR + int(skip*SR)
    _, e = active(a, 0.03)
    return a[st:e]

def stop(ph, keep=0.09):
    a = synth(ph, 1.0); s, e = main_run(a, 0.1)
    print("   stop", ph, pattern(a), file=sys.stderr)
    seg = a[max(0, s-int(.01*SR)): s+int(keep*SR)]
    return fade(seg, 0.003, 0.03)

def onset_before_vowel(ph, keep_after=0.05, vowel="ʌ"):
    a = synth(ph+vowel, 0.9); s, e = active(a, 0.04)
    fs = frames(a); m = max(f[0] for f in fs)
    v = next(i for i, f in enumerate(fs) if f[0] > m*0.6)
    seg = a[s: v*FR + int(keep_after*SR)]
    return fade(seg, 0.005, 0.04)

def noise_run(ph, carrier="ɑ", want="N"):
    """longest contiguous run of frication frames in 'ɑX'"""
    a = synth("ˈ"+carrier+ph+ph, 0.7); fs = frames(a); m = max(f[0] for f in fs)
    lab = [("N" if hi > 0.5 else "x") if r > m*0.04 else "." for r, hi, lo in fs]
    best = (0, 0); i = 0
    while i < len(lab):
        if lab[i] == want:
            j = i
            while j < len(lab) and lab[j] == want: j += 1
            if j-i > best[1]-best[0]: best = (i, j)
            i = j
        else: i += 1
    s, e = best
    return a[(s+1)*FR:(e-1)*FR]

def voiced_fric(ph):
    """voiced fricative: frames after the vowel that keep high-frequency noise"""
    a = synth("ˈɑ"+ph+ph, 0.7); fs = frames(a); m = max(f[0] for f in fs)
    loud = [i for i, f in enumerate(fs) if f[0] > m*0.5]
    ok = [loud[-1] < i and m*0.08 < fs[i][0] < m*0.45 and fs[i][1] > 0.35 for i in range(len(fs))]
    best = (0, 0); i = 0
    while i < len(ok):
        if ok[i]:
            j = i
            while j < len(ok) and ok[j]: j += 1
            if j-i > best[1]-best[0]: best = (i, j)
            i = j
        else: i += 1
    s, e = best
    return a[(s+1)*FR:(e-1)*FR]

CONT = 0.5
def build():
    P = {}
    for v in ["æ", "ɛ", "ɪ", "ɑ", "ʌ"]:
        P[v] = vowel(v)
    for c in ["s", "ʃ", "f", "θ"]:
        P[c] = fade(stretch(noise_run(c), int(CONT*SR)), 0.04, 0.08)
    for c in ["m", "n", "l"]:
        P[c] = fade(stretch(tail_after_vowel(c, skip=0.04, rel=0.7), int(CONT*SR)), 0.03, 0.08)
    P["z"] = fade(stretch(voiced_fric("z"), int(CONT*SR)), 0.04, 0.08)
    P["v"] = fade(stretch(v_sound(), int(CONT*SR)), 0.04, 0.08)
    a = synth("ˈɝ", 1.0); s, e = main_run(a, 0.1); P["ɹ"] = fade(stretch(a[s:e], int(0.42*SR)), 0.02, 0.08)
    for c in ["t", "k"]:
        P[c] = stop(c, 0.06)
    a = synth("pˈɑ", 0.9); fs = frames(a); m = max(f[0] for f in fs)
    n0 = next(i for i, f in enumerate(fs) if f[0] > m*0.04 and f[1] > 0.5)
    n1 = n0
    while fs[n1][1] > 0.5: n1 += 1
    P["p"] = fade(a[n0*FR - int(.01*SR): n1*FR + int(.02*SR)], 0.003, 0.025)
    for c in ["b", "d", "ɡ"]:
        P[c] = stop(c, 0.085)
    P["ʧ"] = stop("ʧ", 0.13)
    P["ʤ"] = stop("ʤ", 0.13)
    P["h"] = onset_before_vowel("h", 0.03, "ʌ")
    P["w"] = onset_before_vowel("w", 0.07, "ʌ")
    P["j"] = onset_before_vowel("j", 0.07, "ʌ")
    return P

if __name__ == "__main__":
    P = build()
    for k, a in P.items():
        a = norm(a)
        sf.write(f"{OUT}/ph_{ord(k[0]):x}.wav", a, SR)
        print(k.ljust(3), f"{len(a)/SR*1000:4.0f}ms", pattern(a))
