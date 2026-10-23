"""Carimba uma versão nova em cada app antes de publicar.

Cada index.html recebe um pequeno script que, ao abrir ou voltar para o app,
confere version.txt no servidor; se a versão mudou, recarrega a página nova.
Assim o app salvo na Tela de Início do iPad se atualiza sozinho.

Uso: python3 publicar.py   (depois: git add -A, commit e push)
"""
import re, time, pathlib

ROOT = pathlib.Path(__file__).parent
VERSION = time.strftime("%Y%m%d%H%M%S")

CHECKER = """<script id="auto-update">
(function(){
  var V="%s";
  function check(){
    fetch("version.txt?t="+Date.now(),{cache:"no-store"}).then(function(r){return r.ok?r.text():""}).then(function(t){
      t=(t||"").trim();
      if(t&&t!==V){location.replace(location.pathname+"?v="+t)}
    }).catch(function(){});
  }
  document.addEventListener("visibilitychange",function(){if(!document.hidden)check()});
  window.addEventListener("pageshow",check);
  check();
})();
</script>"""

HEAD_META = ('<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">'
             '<meta http-equiv="Pragma" content="no-cache"><meta http-equiv="Expires" content="0">')

for index in sorted(ROOT.glob("*/index.html")):
    html = index.read_text()
    html = re.sub(r'<script id="auto-update">.*?</script>', "", html, flags=re.S)
    if 'http-equiv="Cache-Control"' not in html:
        html = html.replace("<head>", "<head>" + HEAD_META, 1)
    html = html.replace("</body>", CHECKER % VERSION + "</body>", 1)
    index.write_text(html)
    (index.parent / "version.txt").write_text(VERSION + "\n")
    print(f"{index.parent.name}: versão {VERSION}")
