# Como a voz da Miss Lua foi gerada

A voz é a **Chatterbox** (Resemble AI, licença MIT), clonada do timbre `ref_heart.wav` (a voz "Heart", escolhida pelo pai em 23/10/2026). O áudio fica todo dentro do app, sem internet.

- `sons_chatterbox.py` grava os **sons puros** das letras na mesma voz. Os sons que dá para segurar ("Mmmm", "Ssss", "Shhh") são falados inteiros pela voz e só ficam se a análise do áudio disser que são puros. Vogais, oclusivas e semivogais são recortadas de sílabas ("at", "pah", "wuh"). `sons_fix.py` refaz os que saíram fracos. O resultado aprovado fica em `sons.npz`.
- `build_audio.py` grava as palavras, as frases da história e as falas da tutora, monta a palavra devagar (`ws:`) alongando a palavra normal com rubberband (mesmo tom de voz) e junta tudo em `audio.js`.
- As falas geradas ficam em `cache/` (fora do git). Se a gravação parar no meio, é só rodar de novo que ela continua de onde parou.

Para regerar (ex.: palavras novas da semana):

```
pip install --break-system-packages chatterbox-tts soundfile   # precisa de huggingface.co e *.hf.co liberados
cd leitura/gerar-audio
python3 build_audio.py          # ~30 s por fala num computador de 2 núcleos
cp audio.js ../audio.js
cd ../.. && python3 publicar.py
```

Só rode `sons_chatterbox.py` + `sons_fix.py` se quiser gravar os sons das letras de novo, porque eles mudam a cada gravação.
`phon.py` é a versão antiga (Kokoro) dos sons e fica só como referência.
