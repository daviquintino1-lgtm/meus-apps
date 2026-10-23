import json, base64, io, os, subprocess, sys
import numpy as np, soundfile as sf
import phon
from phon import K, SR, synth, norm, main_run, fade

G2P = {"a":"æ","e":"ɛ","i":"ɪ","o":"ɑ","u":"ʌ","b":"b","c":"k","d":"d","f":"f","g":"ɡ","h":"h","j":"ʤ","k":"k",
       "l":"l","m":"m","n":"n","p":"p","r":"ɹ","s":"s","t":"t","v":"v","w":"w","y":"j","z":"z",
       "sh":"ʃ","ch":"ʧ","th":"θ","ck":"k","ll":"l","x":"ks"}

LEVELS = [
 ["cat","hat","bat","map","van","rat","cap","pan"],
 ["pig","pin","lip","kid","dog","hot","log","fox"],
 ["bed","hen","web","ten","bus","sun","cup","bug"],
 ["fish","ship","shell","chick","duck","sock","bath","lock"],
 ["stop","crab","drum","flag","sled","frog","tent","gift"],
]
SPLIT = {"fish":["f","i","sh"],"ship":["sh","i","p"],"shell":["sh","e","ll"],"chick":["ch","i","ck"],
         "duck":["d","u","ck"],"sock":["s","o","ck"],"bath":["b","a","th"],"lock":["l","o","ck"]}

PHRASES = {
 "hello": "Hi! I'm Miss Lua. Let's read some words, win stars, and play games!",
 "listen": "Listen to the sounds.",
 "blend": "Now push the sounds together. What word is it?",
 "read": "Your turn! Read this word. Tap a letter if you need help.",
 "wrong": "Oops, not that one. Let's listen again.",
 "slowly": "Let's stretch it out.",
 "say": "Now you say it!",
 "p1": "Great job!", "p2": "You did it!", "p3": "Super reader!", "p4": "Awesome!", "p5": "Wow, well done!", "p6": "Yes! You're a star!",
 "break": "Wow, three words! You earned a game!",
 "level": "You finished the level! Here's a brand new sticker. Amazing reading!",
 "locked": "Finish the level before this one to open it.",
 "gameend": "Great playing! Let's read more words.",
 "buy": "Ooh, great choice!",
 "need": "You need more stars for that one. Let's read more words!",
 "newgame": "Surprise! You unlocked a brand new game!",
 "pick": "Which picture is it?",
}

def tts(text, speed=0.92):
    a, sr = K.create(text, voice=phon.VOICE, speed=speed, lang="en-us")
    a = np.asarray(a, np.float32); fs = phon.frames(a); m = max(f[0] for f in fs)
    s = next(i for i, f in enumerate(fs) if f[0] > m*0.15)
    e = max(i for i, f in enumerate(fs) if f[0] > m*0.02) + 1
    return fade(a[max(0, s*phon.FR-int(.04*SR)):e*phon.FR+int(.05*SR)], 0.01, 0.05)

def mp3(a):
    buf = io.BytesIO(); sf.write(buf, norm(a, 0.85), SR, format="WAV"); wav = buf.getvalue()
    p = subprocess.run(["ffmpeg","-loglevel","error","-f","wav","-i","pipe:0","-ac","1","-ar","24000","-b:a","48k","-f","mp3","pipe:1"],
                       input=wav, capture_output=True, check=True)
    return base64.b64encode(p.stdout).decode()

def main():
    out = {}
    P = phon.build()
    P["ks"] = np.concatenate([P["k"], np.zeros(int(.02*SR), np.float32), P["s"][:int(.3*SR)]])
    for ph, a in P.items():
        out["ph:"+ph] = mp3(a)
        sf.write(f"snd/check_{ord(ph[0]):x}_{len(ph)}.wav", norm(a), SR)
    words = {}
    for lv in LEVELS:
        for w in lv:
            g = SPLIT.get(w) or list(w)
            words[w] = {"g": g, "p": [G2P[x] for x in g]}
            out["w:"+w] = mp3(tts(w, 0.85))
            out["ws:"+w] = mp3(tts(w, 0.5))
    for k, t in PHRASES.items():
        out["t:"+k] = mp3(tts(t))
    js = "window.AUDIO=" + json.dumps(out) + ";window.PHON=" + json.dumps(words, ensure_ascii=False) + ";"
    open("audio.js","w").write(js)
    json.dump(words, open("phonemes.json","w"), ensure_ascii=False)
    print("clips", len(out), "size KB", len(js)//1024)

if __name__ == "__main__":
    main()
