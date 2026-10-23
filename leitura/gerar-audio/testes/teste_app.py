"""Checks audio.js against an older copy: python3 teste_app.py <old audio.js>  (e.g. from git show HEAD~1:leitura/audio.js)"""
import json, re, sys, base64, subprocess, threading, http.server, functools
from playwright.sync_api import sync_playwright
import os; APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
def load(p):
    s = open(p).read()
    a = json.loads(re.search(r"window.AUDIO=(\{.*?\});window.PHON", s, re.S).group(1))
    ph = json.loads(re.search(r"window.PHON=(\{.*\});", s, re.S).group(1))
    return a, ph
old_a, old_p = load(sys.argv[1]); new_a, new_p = load(APP + "/audio.js")
print("chaves faltando:", sorted(set(old_a) - set(new_a))[:10], "| palavras PHON faltando:", sorted(set(old_p) - set(new_p)))
for w, d in new_p.items():
    assert set(d) >= {"g","p","t","tb","tw","db"}, w
bad = []
for k, v in new_a.items():
    r = subprocess.run(["ffmpeg","-loglevel","error","-i","pipe:0","-ac","1","-ar","8000","-f","s16le","pipe:1"], input=base64.b64decode(v), capture_output=True)
    d = len(r.stdout)/16000
    if d < 0.25 or (k.startswith(("w:","ws:")) and d > 3.5) or d > 15: bad.append((k, round(d, 2)))
print("clipes suspeitos:", bad or "nenhum", "| total", len(new_a))
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=APP)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8765), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
FAKE = """class FR{constructor(){this.lang='';}start(){setTimeout(()=>{this.onresult&&this.onresult({results:[[{transcript:'cat',confidence:.9}]],resultIndex:0});this.onend&&this.onend();},300)}stop(){} abort(){}}
window.SpeechRecognition=FR; window.webkitSpeechRecognition=FR;"""
with sync_playwright() as p:
    b = p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
    pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.add_init_script(FAKE); pg.goto("http://127.0.0.1:8765/index.html"); pg.wait_for_timeout(1500)
    pg.click("#startBtn"); pg.wait_for_timeout(700)
    print("voz tocando logo após Start:", pg.evaluate("voiceEl.paused===false"))
    pg.wait_for_timeout(4000); print("erros na página:", errs or "nenhum")
    b.close()
srv.shutdown()
