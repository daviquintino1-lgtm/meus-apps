# Como a voz da Miss Lua foi gerada

A voz é a **Kokoro** (voz `af_heart`, inglês americano, licença Apache-2.0), rodando no computador — sem internet no app.

- `phon.py` gera os **sons puros** das letras. Consoantes sozinhas saem com vogal grudada, então cada som é recortado de dentro de uma sílaba ("ɑs" → só o chiado do /s/) e conferido pela análise do áudio: /s/ /f/ /sh/ /th/ só ruído, /m/ /n/ só murmúrio nasal, /p/ /t/ /k/ curtinhos, sem "uh".
- `build_audio.py` gera as palavras (normal e esticada), as falas da tutora e junta tudo em `../audio.js`.

Para regerar (ex.: palavras novas):

```
pip install kokoro-onnx soundfile
# modelos: github.com/thewh1teagle/kokoro-onnx/releases (model-files-v1.0) em ./kmodel/
python3 build_audio.py
```
