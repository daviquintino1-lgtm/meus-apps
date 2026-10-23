"""Plays one lesson in a headless browser and prints every sound the app plays (no auto sound-out, tap = letter sound, Hear it = word)."""
import threading, http.server, functools
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(("127.0.0.1",8766),functools.partial(Q,directory=__import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__),"..","..")))); threading.Thread(target=srv.serve_forever,daemon=True).start()
with sync_playwright() as p:
    b=p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"]); pg=b.new_page(); errs=[]
    pg.on("pageerror",lambda e:errs.append(str(e)))
    pg.goto("http://127.0.0.1:8766/index.html"); pg.wait_for_timeout(1200)
    pg.evaluate("window.LOG=[];const _p=play;window.play=function(k,...r){LOG.push(k);return _p(k,...r)}")
    pg.click("#startBtn"); pg.wait_for_timeout(1500)
    pg.evaluate("LOG.length=0; startLevel(1)"); pg.wait_for_timeout(6000)
    w=pg.evaluate("L.queue[L.idx][0]"); print("palavra:",w,"| ao abrir tocou:",pg.evaluate("LOG.slice()"))
    pg.evaluate("LOG.length=0"); pg.click("#word .tile >> nth=0"); pg.wait_for_timeout(1500); print("tocar 1a letra:",pg.evaluate("LOG.slice()"))
    pg.evaluate("LOG.length=0"); pg.click("#replay"); pg.wait_for_timeout(1500); print("Hear it:",pg.evaluate("LOG.slice()"))
    pg.evaluate("LOG.length=0"); pg.click(f".choice:not([data-w='{w}']) >> nth=0"); pg.wait_for_timeout(5000); print("figura errada:",pg.evaluate("LOG.slice()"))
    pg.evaluate("LOG.length=0"); pg.click(f".choice[data-w='{w}']"); pg.wait_for_timeout(7000); print("figura certa:",pg.evaluate("LOG.slice()"),"| vez dele aberta:",pg.evaluate("!$('sayItOv').hidden"))
    print("erros:",errs or "nenhum"); b.close()
srv.shutdown()
