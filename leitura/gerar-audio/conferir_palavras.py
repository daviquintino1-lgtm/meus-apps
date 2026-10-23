"""Checks every single word the Miss Lua voice says (w: clips) and re-records the wrong ones.

A phoneme recognizer (wav2vec2 espeak) "listens" to each cached word and compares it with the
dictionary pronunciation (espeak-ng). Wrong words are re-generated with other seeds / punctuation
and the closest take replaces the cached one. Run before build_audio.py.
Writes conferencia.json with the result for each word.
"""
import re, os, json, sys, hashlib, numpy as np, torch, librosa
import espeakng_loader
from phonemizer.backend.espeak.wrapper import EspeakWrapper
EspeakWrapper.set_library(espeakng_loader.get_library_path()); EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
from phonemizer import phonemize
from transformers import AutoFeatureExtractor, Wav2Vec2PhonemeCTCTokenizer, AutoModelForCTC
import build_audio as B           # loads Chatterbox (Heart voice) + word lists
from sons_chatterbox import SR

M = "facebook/wav2vec2-lv-60-espeak-cv-ft"
fe = AutoFeatureExtractor.from_pretrained(M); tok = Wav2Vec2PhonemeCTCTokenizer.from_pretrained(M, do_phonemize=False)
mod = AutoModelForCTC.from_pretrained(M).eval()

def heard(x):
    x = librosa.resample(np.asarray(x, np.float32), orig_sr=SR, target_sr=16000)
    x = np.concatenate([np.zeros(1600, np.float32), x, np.zeros(1600, np.float32)])
    with torch.no_grad(): ids = mod(fe(x, sampling_rate=16000, return_tensors="pt").input_values).logits.argmax(-1)
    return tok.batch_decode(ids)[0]

EQ = [("tʃ","C"),("dʒ","J"),("oʊ","O"),("aɪ","I"),("aʊ","W"),("eɪ","E"),("ɔɪ","Y"),
      ("æ","a"),("ɑ","o"),("ɔ","o"),("ɒ","o"),("ʌ","ə"),("ɐ","ə"),("ɛ","e"),("ᵻ","i"),("ɪ","i"),
      ("ʊ","u"),("ʉ","u"),("ɚ","R"),("ɜ","R"),("ɝ","R"),("r","ɹ"),("ɡ","g"),("ɾ","t"),("th","t"),("ʔ","")]
def simple(p):
    p = re.sub(r"[ˈˌː\d. ]", "", p)
    for a, b in EQ: p = p.replace(a, b)
    return p
def dist(a, b):
    d = list(range(len(b)+1))
    """weighted edit distance: a wrong consonant costs 1, a wrong vowel 0.5 (the recognizer blurs short vowels)"""
    a = a.lstrip("əi"); V = set("aeiouəoREIOWY")
    c = lambda x: .5 if x in V else 1
    d = [0.0]
    for y in b: d.append(d[-1] + c(y))
    for x in a:
        prev, d[0] = d[0], d[0] + c(x)
        for j, y in enumerate(b, 1):
            sub = 0 if x == y else (.5 if x in V and y in V else 1)
            prev, d[j] = d[j], min(d[j] + c(x), d[j-1] + c(y), prev + sub)
    return d[-1]

KDIR = "/home/claude/vozes" if os.path.exists("/home/claude/vozes/kokoro-v1.0.onnx") else "kmodel"
from kokoro_onnx import Kokoro
K = Kokoro(f"{KDIR}/kokoro-v1.0.onnx", f"{KDIR}/voices-v1.0.bin")   # same Heart timbre, dictionary pronunciation

words = []
for lv in B.LEVELS: words += lv
words += B.SIGHT + B.VOCAB
for s in B.STORY: words += [w.lower() for w in re.findall(r"[A-Za-z]+", s)]
words = list(dict.fromkeys(words))
want = dict(zip(words, phonemize(words, language="en-us", backend="espeak", strip=True)))
OK = 0.5   # at most one blurred vowel; any wrong consonant fails

report = json.load(open("conferencia.json")) if os.path.exists("conferencia.json") else {}
for w in words:
    if w in report and report[w]["dist"] <= OK: continue
    t = w + "."; f = f"{B.CACHE}/{hashlib.md5(t.encode()).hexdigest()[:12]}.npy"
    target = simple(want[w])
    cands = []
    def add(src, y):
        h = heard(y); cands.append((dist(simple(h), target), src, y, h))
        print(f"   {w:9s} {src:16s} [{h}] d={cands[-1][0]}", file=sys.stderr, flush=True)
    add("natural", B.tts(w))
    if cands[-1][0] > OK:
        for sp in (0.9, 1.0):
            a, _ = K.create(w, voice="af_heart", speed=sp, lang="en-us"); add(f"kokoro{sp}", B.cut(np.asarray(a, np.float32)))
    tries = 0
    while min(c[0] for c in cands) > OK and tries < 3:
        txt = [w + "!", w.capitalize() + ".", w + "?"][tries]
        add(f"natural:{txt}", B.cut(B.V.say(txt, 20 + tries, 0.6))); tries += 1
    best = min(cands, key=lambda c: (c[0], not c[1].startswith("natural")))
    if best[1] != "natural": np.save(f, best[2])
    report[w] = {"want": want[w], "heard": best[3], "dist": best[0], "source": best[1]}
    print(f"{'OK' if best[0] <= OK else 'XX'} {w:10s} want {want[w]:10s} heard [{best[3]}] d={best[0]} from {best[1]}", flush=True)
    json.dump(report, open("conferencia.json", "w"), ensure_ascii=False, indent=1)
print("still wrong:", [w for w, r in report.items() if r["dist"] > OK])
