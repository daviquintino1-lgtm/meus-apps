"""Removes stray sounds the voice makes before/after a word (breaths, "uh", a repeated bit).

For each word in conferencia.json, the phoneme recognizer marks which 20 ms frames hold which
phoneme; the run of phonemes that best matches the dictionary pronunciation is kept (with a little
margin so the first and last sounds are not clipped) and everything else is cut away.
The untouched take is saved once as cache/orig_<key>.npy, so running this again starts from it.
Run after conferir_palavras.py and before build_audio.py.
"""
import os, re, json, sys, hashlib, shutil, numpy as np, torch, librosa
from transformers import AutoFeatureExtractor, Wav2Vec2PhonemeCTCTokenizer, AutoModelForCTC

SR = 24000; CACHE = "cache"
M = "facebook/wav2vec2-lv-60-espeak-cv-ft"
fe = AutoFeatureExtractor.from_pretrained(M); tok = Wav2Vec2PhonemeCTCTokenizer.from_pretrained(M, do_phonemize=False)
mod = AutoModelForCTC.from_pretrained(M).eval(); torch.set_num_threads(2)
src = open("conferir_palavras.py").read(); exec(src[src.index("EQ = ["):src.index("KDIR")])   # simple(), dist()

PAD = 0.1   # s of silence added before recognition (removed again below)
def tokens(x):
    y = librosa.resample(np.asarray(x, np.float32), orig_sr=SR, target_sr=16000)
    y = np.concatenate([np.zeros(int(PAD*16000), np.float32), y, np.zeros(int(PAD*16000), np.float32)])
    with torch.no_grad(): ids = mod(fe(y, sampling_rate=16000, return_tensors="pt").input_values).logits.argmax(-1)[0].tolist()
    out, i = [], 0; step = len(y) / 16000 / len(ids)
    while i < len(ids):
        j = i
        while j < len(ids) and ids[j] == ids[i]: j += 1
        if ids[i] != tok.pad_token_id:
            s = tok.convert_ids_to_tokens(ids[i])
            if s.strip() and s not in ("|", "<unk>"): out.append((s, i*step - PAD, j*step - PAD))
        i = j
    return out

def dist2(a, b):
    """same weighted distance as conferir_palavras.dist, but without forgiving a leading vowel"""
    V = set("aeiouəoREIOWY"); c = lambda x: .5 if x in V else 1
    d = [0.0]
    for y in b: d.append(d[-1] + c(y))
    for x in a:
        prev, d[0] = d[0], d[0] + c(x)
        for k, y in enumerate(b, 1):
            sub = 0 if x == y else (.5 if x in V and y in V else 1)
            prev, d[k] = d[k], min(d[k] + c(x), d[k-1] + c(y), prev + sub)
    return d[-1]

def loud_blobs(x, fr=240, gap=4):
    db = np.array([20*np.log10(np.sqrt(np.mean(x[k:k+fr]**2)) + 1e-9) for k in range(0, len(x)-fr, fr)])
    on = db > db.max() - 30; out, k = [], 0
    while k < len(on):
        if on[k]:
            m = k
            while m < len(on) and on[m:m+gap].any(): m += 1
            out.append((k*fr/SR, m*fr/SR)); k = m
        else: k += 1
    return out

def fade(a, fi=.008, fo=.04):
    a = a.copy(); i, o = int(fi*SR), int(fo*SR); a[:i] *= np.linspace(0, 1, i); a[-o:] *= np.linspace(1, 0, o); return a

rep = json.load(open("conferencia.json")); log = {}
def clean(w, text, want):
    key = hashlib.md5(text.encode()).hexdigest()[:12]
    f, orig = f"{CACHE}/{key}.npy", f"{CACHE}/orig_{key}.npy"
    if not os.path.exists(f): print("missing", w, text); return
    if not os.path.exists(orig): shutil.copy(f, orig)
    x = np.load(orig); T = tokens(x); target = simple(want)
    if not T: return
    # 1) drop a recognized sound at either edge only if the word matches strictly better without it
    i, j = 0, len(T) - 1
    sc = lambda a, b: dist2("".join(simple(t[0]) for t in T[a:b+1]), target)
    changed = True
    while changed and j > i:
        changed = False
        if sc(i+1, j) < sc(i, j): i += 1; changed = True
        elif sc(i, j-1) < sc(i, j): j -= 1; changed = True
    # 2) split the take into sound blobs separated by >= 40 ms of quiet; keep the blobs that hold the word
    blobs = loud_blobs(x)
    keep = [b for b in blobs if b[1] > T[i][1] - 0.03 and b[0] < T[j][2] + 0.03]
    if not keep: keep = blobs
    # never cut into the word itself: CTC marks a sound near its middle, and weak final sounds
    # (th, sh, l, s...) are quieter than the blob threshold, so give them room and follow their tail
    soft = set("ʃθsflnmŋzvð")
    tail = 0.22 if T[j][0][:1] in soft else 0.12
    s = max(0.0, min(keep[0][0] - 0.03, T[i][1] - 0.06))
    e = max(keep[-1][1] + 0.05, T[j][2] + tail)
    FRm = 240; peak = 20*np.log10(np.max(np.abs(x)) + 1e-9)
    while e*SR + FRm < len(x) and 20*np.log10(np.sqrt(np.mean(x[int(e*SR):int(e*SR)+FRm]**2)) + 1e-9) > peak - 45: e += FRm/SR
    later = [b[0] for b in blobs if b[0] > keep[-1][1]]          # a stray bit after the word
    e = min(len(x)/SR, e, (later[0] - 0.01) if later else len(x)/SR)
    y = fade(x[int(s*SR):int(e*SR)])
    cut_before, cut_after = s, len(x)/SR - e
    np.save(f, y)
    log[w] = {"heard": " ".join(t[0] for t in T), "kept": " ".join(t[0] for t in T[i:j+1]),
              "cut_before_ms": round(cut_before*1000), "cut_after_ms": round(cut_after*1000)}
    flag = "  <-- cut" if cut_before > .15 or cut_after > .2 else ""
    print(f"{w:10s} [{log[w]['heard'][:60]}] kept [{log[w]['kept'][:60]}] -{log[w]['cut_before_ms']}ms / -{log[w]['cut_after_ms']}ms{flag}", flush=True)

for w, r in rep.items(): clean(w, w + ".", r["want"])

# tutor phrases (t:) and story sentences (s:) get the same treatment
import ast, espeakng_loader
from phonemizer.backend.espeak.wrapper import EspeakWrapper
EspeakWrapper.set_library(espeakng_loader.get_library_path()); EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
from phonemizer import phonemize
src = open("build_audio.py").read()
grab = lambda name, end: ast.literal_eval(src[src.index(name + " = ") + len(name) + 3: src.index(end, src.index(name + " = ")) + 1])
PH = grab("PHRASES", "}\n"); ST = grab("STORY", "]\n")
items = [("t:" + k, v) for k, v in PH.items()] + [(f"s:{i}", s) for i, s in enumerate(ST)]
texts = [v if v.rstrip()[-1:] in ".!?:\"" else v + "." for _, v in items]
wants = phonemize([re.sub(r"[^A-Za-z' ]", " ", v) for _, v in items], language="en-us", backend="espeak", strip=True)
for (name, _), text, want in zip(items, texts, wants): clean(name, text, want)
json.dump(log, open("limpeza.json", "w"), ensure_ascii=False, indent=1)
