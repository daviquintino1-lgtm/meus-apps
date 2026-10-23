"""Letter sounds (ph:) in the Chatterbox voice (timbre af_heart).

Continuous sounds are spoken whole by the voice ("Mmmmm.", "Sssss.") and kept only
if the frame labels say they are pure: fricatives = noise only, nasals = murmur only.
Vowels, stops and glides are cut from short carrier syllables ("at", "pah", "wuh").
Run: python3 sons_chatterbox.py  -> snd2/*.wav, sons.npz and amostra_sons.mp3
"""
import os, sys, subprocess, numpy as np, soundfile as sf, torch
from chatterbox.tts import ChatterboxTTS

SR = 24000; FR = 240
REF = os.environ.get("REF", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ref_heart.wav"))
OUT = "snd2"; os.makedirs(OUT, exist_ok=True)
torch.set_num_threads(2)
M = ChatterboxTTS.from_pretrained(device="cpu")

def say(text, seed=0, ex=0.5):
    torch.manual_seed(seed)
    w = M.generate(text, audio_prompt_path=REF, exaggeration=ex, cfg_weight=0.4)
    return w.squeeze().numpy().astype(np.float32)

def frames(a):
    out = []
    for i in range(len(a) // FR):
        x = a[i*FR:(i+1)*FR]; r = float(np.sqrt(np.mean(x**2)))
        S = np.abs(np.fft.rfft(x * np.hanning(len(x)))) + 1e-9; f = np.fft.rfftfreq(len(x), 1/SR)
        out.append((r, S[f > 3000].sum()/S.sum(), S[f < 450].sum()/S[f < 4000].sum()))
    return out

def labels(a):
    fs = frames(a)
    if not fs: return ""
    m = max(f[0] for f in fs) or 1
    return "".join("." if r < m*.04 else "N" if hi > .5 else "n" if lo > .55 else "V" for r, hi, lo in fs)

def fade(a, fin=.01, fout=.05):
    a = a.copy(); i, o = int(fin*SR), int(fout*SR)
    if i and len(a) > i: a[:i] *= np.linspace(0, 1, i)
    if o and len(a) > o: a[-o:] *= np.linspace(1, 0, o)
    return a

def norm(a, p=.8): return a * (p / (np.max(np.abs(a)) or 1))

def trim(a):
    lab = labels(a); on = [i for i, c in enumerate(lab) if c != "."]
    return a[on[0]*FR:(on[-1]+1)*FR] if on else a

def runs(lab, ok):
    best, i = (0, 0), 0
    while i < len(lab):
        if lab[i] in ok:
            j = i
            while j < len(lab) and lab[j] in ok: j += 1
            if j-i > best[1]-best[0]: best = (i, j)
            i = j
        else: i += 1
    return best

# ---- continuous sounds spoken whole -------------------------------------
HOLD = {  # sound: (text, frame classes that count as "pure")
    "s": ("Sssssss.", "N"), "ʃ": ("Shhhhhh.", "N"), "f": ("Ffffff.", "N"), "θ": ("Thhhhhh.", "N"),
    "z": ("Zzzzzzz.", "NnV"), "v": ("Vvvvvvv.", "NnV"),
    "m": ("Mmmmmmm.", "n"), "n": ("Nnnnnnn.", "n"), "l": ("Lllllll.", "nV"), "ɹ": ("Rrrrrrr.", "nV"),
}
def hold(ph):
    text, ok = HOLD[ph]; best = None
    for seed in range(4):
        a = trim(say(text, seed)); lab = labels(a)
        s, e = runs(lab, ok + ".")
        core = a[s*FR:e*FR]
        score = (e-s) / max(1, len(lab))
        dur = len(core)/SR
        print(f"  {ph} seed{seed} {dur:.2f}s pure={score:.2f} {labels(core)[:60]}", file=sys.stderr, flush=True)
        if dur >= .3 and (best is None or score > best[0]): best = (score, core)
        if score > .9 and dur >= .35: break
    core = best[1] if best else core
    return fade(core[:int(.6*SR)], .04, .1)

# ---- vowels: first vowel of a short syllable, cut at the consonant --------
VOW = {"æ": "at", "ɛ": "eh", "ɪ": "it", "ɑ": "ah", "ʌ": "uh"}
def vowel(ph):
    a = trim(say(VOW[ph] + ".", 1)); lab = labels(a)
    s, e = runs(lab, "Vn")
    seg = a[s*FR:e*FR][:int(.42*SR)]
    print(f"  {ph} {len(seg)/SR:.2f}s {labels(seg)}", file=sys.stderr, flush=True)
    return fade(seg, .01, .08)

# ---- stops / affricates / glides: the onset before the vowel -------------
ONSET = {  # sound: (syllable, ms of vowel to keep after the onset)
    "p": ("pah", 0), "t": ("tah", 0), "k": ("kah", 0),
    "b": ("bah", 25), "d": ("dah", 25), "ɡ": ("gah", 25),
    "ʧ": ("chah", 0), "ʤ": ("jah", 20), "h": ("hah", 20), "w": ("wuh", 70), "j": ("yuh", 70),
}
def onset(ph):
    syl, keep = ONSET[ph]
    a = trim(say(syl + ".", 2)); fs = frames(a); m = max(f[0] for f in fs)
    v = next((i for i, f in enumerate(fs) if f[0] > m*.45 and f[1] < .3), 3)
    seg = a[:v*FR + int(keep/1000*SR)]
    print(f"  {ph} {len(seg)/SR*1000:.0f}ms {labels(seg)}", file=sys.stderr, flush=True)
    return fade(seg, .003, .03 if keep else .015)

def ing():
    a = trim(say("ing.", 3)); return fade(a[:int(.6*SR)], .01, .08)

def build():
    P = {}
    for v in VOW: P[v] = vowel(v)
    for c in HOLD: P[c] = hold(c)
    for c in ONSET: P[c] = onset(c)
    P["ɪŋ"] = ing()
    return {k: norm(v) for k, v in P.items()}

if __name__ == "__main__":
    P = build()
    np.savez("sons.npz", **P)
    order = ["æ","ɛ","ɪ","ɑ","ʌ","m","s","f","ʃ","θ","n","l","v","z","ɹ","t","k","p","b","d","ɡ","ʧ","ʤ","h","w","j","ɪŋ"]
    parts = []
    for k in order:
        sf.write(f"{OUT}/ph_{ord(k[0]):x}.wav", P[k], SR)
        parts += [P[k], np.zeros(int(.7*SR), np.float32)]
    sf.write("amostra_sons.wav", np.concatenate(parts), SR)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i","amostra_sons.wav","-ac","1","-ar","24000","-b:a","96k","amostra_sons.mp3"], check=True)
    print("ok", len(P))
