"""Second pass on the weak letter sounds from sons_chatterbox.py (reads/writes sons.npz)."""
import sys, subprocess, numpy as np, soundfile as sf
import sons_chatterbox as S
from sons_chatterbox import say, frames, labels, fade, norm, trim, runs, SR, FR

P = dict(np.load("sons.npz"))
log = lambda *a: print(*a, file=sys.stderr, flush=True)

def loop_to(seg, target):
    """lengthen a steady sound (noise or hum) with crossfaded loops"""
    if len(seg) >= target: return seg[:target]
    xf = min(int(.03*SR), len(seg)//3); core = seg[len(seg)//5: len(seg)*4//5]
    out = seg[:len(seg)*4//5].copy()
    while len(out) < target:
        w = np.linspace(0, 1, xf); out[-xf:] = out[-xf:]*(1-w) + core[:xf]*w
        out = np.concatenate([out, core[xf:]])
    return out[:target]

def burst(ph, syl, voiced, seed=2):
    a = say(syl + ".", seed); fs = frames(a); m = max(f[0] for f in fs)
    st = next(i for i, f in enumerate(fs) if f[0] > m*.015)
    vo = next(i for i in range(st, len(fs)) if fs[i][0] > m*.35 and fs[i][1] < .3)
    end = vo + (4 if voiced else 0)
    end = max(end, st + (5 if voiced else 6)); end = min(end, st + 12)
    seg = a[max(0, st-1)*FR: end*FR]
    log(f"  {ph} {len(seg)/SR*1000:.0f}ms {labels(seg)}")
    return fade(seg, .003, .025)

# short e: vowel of "Ed", cut at the d closure
a = trim(say("Ed.", 4)); s, e = runs(labels(a), "Vn"); P["ɛ"] = fade(a[s*FR:e*FR][:int(.4*SR)], .01, .08)
log("  ɛ", round((e-s)*FR/SR, 2), labels(P["ɛ"]))
# f: keep the pure noise and hold it like the other fricatives
s, e = runs(labels(P["f"]), "N"); P["f"] = fade(loop_to(P["f"][s*FR:e*FR], int(.5*SR)), .04, .1)
# l: try a few takes, keep one with no gaps
best = None
for seed in range(5, 9):
    a = trim(say("Llllll.", seed)); s, e = runs(labels(a), "nV")
    log(f"  l seed{seed} {(e-s)*FR/SR:.2f}s {labels(a[s*FR:e*FR])[:50]}")
    if best is None or e-s > best[1]-best[0]: best = (s, e, a)
s, e, a = best; P["l"] = fade(loop_to(a[s*FR:e*FR], int(.5*SR)), .04, .1)
for ph, syl in [("p","pah"),("t","tah"),("k","kah")]: P[ph] = burst(ph, syl, False)
for ph, syl in [("b","bah"),("d","dah"),("ɡ","gah")]: P[ph] = burst(ph, syl, True)
a = say("hah.", 2); fs = frames(a); m = max(f[0] for f in fs)
st = next(i for i, f in enumerate(fs) if f[0] > m*.015)
vo = next(i for i in range(st, len(fs)) if fs[i][0] > m*.35)
P["h"] = fade(a[st*FR:(vo+2)*FR], .01, .03); log("  h", labels(P["h"]))
P = {k: norm(v) for k, v in P.items()}
np.savez("sons.npz", **P)

order = ["æ","ɛ","ɪ","ɑ","ʌ","m","s","f","ʃ","θ","n","l","v","z","ɹ","t","k","p","b","d","ɡ","ʧ","ʤ","h","w","j","ɪŋ"]
parts = []
for k in order: parts += [P[k], np.zeros(int(.7*SR), np.float32)]
sf.write("amostra_sons.wav", np.concatenate(parts), SR)
subprocess.run(["ffmpeg","-y","-loglevel","error","-i","amostra_sons.wav","-ac","1","-ar","24000","-b:a","96k","amostra_sons.mp3"], check=True)
for k in order: log(k.ljust(3), f"{len(P[k])/SR*1000:4.0f}ms", labels(P[k])[:50])
print("ok")
