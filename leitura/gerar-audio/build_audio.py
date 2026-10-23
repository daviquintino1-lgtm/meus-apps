"""Builds audio.js for Read with Miss Lua (Kokoro af_heart voice).

Every clip gets a short silent lead-in so iPad Safari does not swallow the start.
Each word also gets one 'sound-out' clip (all its sounds in a row) with the
start time of each sound, so the app plays one file instead of many tiny ones.
"""
import json, base64, io, subprocess
import numpy as np, soundfile as sf
import phon
from phon import K, SR, norm, main_run, fade

LEAD = 0.14   # seconds of silence before every clip
TAIL = 0.08
GAP = 0.13    # short breath between sounds, like a teacher tapping each letter
CONT = {"s","ʃ","f","θ","m","n","l","v","z"}   # sounds a teacher holds ("fff", "mmm")
CONT_LEN = 0.42

G2P = {"a":"æ","e":"ɛ","i":"ɪ","o":"ɑ","u":"ʌ","b":"b","c":"k","d":"d","f":"f","g":"ɡ","h":"h","j":"ʤ","k":"k",
       "l":"l","m":"m","n":"n","p":"p","r":"ɹ","s":"s","t":"t","v":"v","w":"w","y":"j","z":"z",
       "sh":"ʃ","ch":"ʧ","th":"θ","ck":"k","ll":"l","x":"ks","ing":"ɪŋ"}

LEVELS = [
 ["cat","hat","bat","map","van","rat","cap","pan"],
 ["pig","pin","lip","kid","dog","hot","log","fox"],
 ["bed","hen","web","ten","bus","sun","cup","bug"],
 ["fish","ship","shell","chick","duck","sock","bath","lock"],
 ["stop","crab","drum","flag","sled","frog","tent","gift"],
 # school week Oct 19-23: sh, th, -ing
 ["ship","shop","trash","fish","bath","fishing","splash","wishing","rushing","thin","with","math"],
]
SPLIT = {"fish":["f","i","sh"],"ship":["sh","i","p"],"shell":["sh","e","ll"],"chick":["ch","i","ck"],
         "duck":["d","u","ck"],"sock":["s","o","ck"],"bath":["b","a","th"],"lock":["l","o","ck"],
         "shop":["sh","o","p"],"trash":["t","r","a","sh"],"fishing":["f","i","sh","ing"],
         "splash":["s","p","l","a","sh"],"wishing":["w","i","sh","ing"],"rushing":["r","u","sh","ing"],
         "thin":["th","i","n"],"with":["w","i","th"],"math":["m","a","th"]}

SIGHT = ["all","goes","her","make","too","she","the","this","then","says","is","for","to","said"]
VOCAB = ["eat","dig","sleep","burrow"]

STORY = [
 "Beth is fishing with Seth.",
 "She is wishing for a big fish.",
 "The fish is thrashing and splashing!",
 "Seth is rushing to help.",
 "Beth sees the fish and grins.",
 "\"This is the best thing!\" she says.",
 "Then the fish slips!",
 "Splash! Back in it goes!",
]

PHRASES = {
 "hello": "Hi! I'm Miss Lua. Let's read some words, win stars, and play games!",
 "listen": "My turn. Watch the letters, and listen.",
 "blend": "Your turn! Which picture is it?",
 "read": "Your turn to read! Sound it out. You can tap a letter for help.",
 "wrong": "Hmm, not that one. Let's sound it out together.",
 "slowly": "Let's say it slowly.",
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
 "find": "Find the word:",
 "findintro": "These are words we know by heart. Listen, and find the word!",
 "ing": "I N G says ing, like in fishing.",
 "story": "Let's read the story Fishing! Listen to me first.",
 "storyturn": "Now it's your turn. Read it out loud! Tap any word if you need help.",
 "storydone": "You read the whole story! I'm so proud of you!",
 "week": "These are the words from your school this week!",
 "tapmic": "Tap the microphone, and say the word!",
 "perfect": "Perfect! I heard you say it!",
 "almost": "Almost! Listen carefully, and try again.",
 "practice": "Good try! Let's practice this one together.",
 "readsent": "Tap the microphone, and read this sentence to me.",
 "missed": "Let's practice these words.",
 "nicesent": "Nice reading!",
}

def pad(a, lead=LEAD, tail=TAIL):
    return np.concatenate([np.zeros(int(lead*SR), np.float32), a.astype(np.float32), np.zeros(int(tail*SR), np.float32)])

def tts(text, speed=0.95):
    a, sr = K.create(text, voice=phon.VOICE, speed=speed, lang="en-us")
    a = np.asarray(a, np.float32); fs = phon.frames(a); m = max(f[0] for f in fs)
    s = next(i for i, f in enumerate(fs) if f[0] > m*0.15)
    e = max(i for i, f in enumerate(fs) if f[0] > m*0.02) + 1
    return fade(a[max(0, s*phon.FR-int(.04*SR)):e*phon.FR+int(.06*SR)], 0.01, 0.05)

def mp3(a, peak=0.85):
    buf = io.BytesIO(); sf.write(buf, pad(norm(a, peak)), SR, format="WAV")
    p = subprocess.run(["ffmpeg","-loglevel","error","-f","wav","-i","pipe:0","-ac","1","-ar","24000","-b:a","64k","-f","mp3","pipe:1"],
                       input=buf.getvalue(), capture_output=True, check=True)
    return base64.b64encode(p.stdout).decode()

def ing_sound():
    a = phon.synth("ˈɪŋ", 0.8); s, e = main_run(a, 0.08)
    return fade(a[s:e+int(.04*SR)], 0.01, 0.08)

def main():
    out = {}
    P = phon.build()
    P["ks"] = np.concatenate([P["k"], np.zeros(int(.02*SR), np.float32), P["s"][:int(.3*SR)]])
    P["ɪŋ"] = ing_sound()
    P = {k: norm(v, 0.8) for k, v in P.items()}
    for ph, a in P.items():
        out["ph:"+ph] = mp3(a, 0.8)
    words = {}
    allw = []
    for lv in LEVELS:
        for w in lv:
            if w not in allw: allw.append(w)
    for w in allw:
        g = SPLIT.get(w) or list(w)
        p = [G2P[x] for x in g]
        # teacher model in ONE clip: sounds (short gaps) -> slow blend -> the word
        word = norm(tts(w, 0.9), 0.8); slow = norm(tts(w, 0.72), 0.8)
        parts, times, t = [], [], LEAD
        for i, ph in enumerate(p):
            seg = P[ph]
            if ph in CONT: seg = seg[:int(CONT_LEN*SR)]   # hold, but not forever
            seg = fade(seg, 0.005, 0.03)
            times.append(round(t, 3)); parts.append(seg); t += len(seg)/SR
            if i < len(p)-1:
                parts.append(np.zeros(int(GAP*SR), np.float32)); t += GAP
        parts.append(np.zeros(int(.35*SR), np.float32)); t += .35
        tb = round(t, 3); parts.append(slow); t += len(slow)/SR
        parts.append(np.zeros(int(.25*SR), np.float32)); t += .25
        tw = round(t, 3); parts.append(word)
        out["so:"+w] = mp3(np.concatenate(parts), 0.8)
        words[w] = {"g": g, "p": p, "t": times, "tb": tb, "tw": tw, "db": round(len(slow)/SR, 3)}
        out["w:"+w] = mp3(word)
        out["ws:"+w] = mp3(slow)
    for w in SIGHT + VOCAB:
        if "w:"+w not in out: out["w:"+w] = mp3(tts(w, 0.9))
    # every word of the story, for tap-to-hear
    import re
    for s in STORY:
        for w in re.findall(r"[A-Za-z]+", s):
            k = "w:"+w.lower()
            if k not in out: out[k] = mp3(tts(w.lower(), 0.9))
    for i, s in enumerate(STORY):
        out[f"s:{i}"] = mp3(tts(s, 0.88))
    for k, t in PHRASES.items():
        out["t:"+k] = mp3(tts(t, 0.95))
    js = "window.AUDIO=" + json.dumps(out) + ";window.PHON=" + json.dumps(words, ensure_ascii=False) + ";"
    open("audio.js","w").write(js)
    print("clips", len(out), "size KB", len(js)//1024)

if __name__ == "__main__":
    main()
