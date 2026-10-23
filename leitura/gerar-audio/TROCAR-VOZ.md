# Trocar a voz da Miss Lua por uma voz natural

> **Feito em 23/10/2026:** voz trocada para Chatterbox com o timbre Heart (escolha do pai), sons das letras regravados na mesma voz. Veja LEIA-ME.md.

Pedido do pai: a voz atual (Kokoro `af_heart`) soa robótica. Ele quer uma voz natural, estilo ElevenLabs, falando como uma professora americana de 1º ano (warm, clear, encouraging). `huggingface.co` foi liberado nas Capacidades da conta em 22/10/2026, então uma sessão nova consegue baixar os modelos.

## O que fazer

1. Confirme o acesso: `curl -s -o /dev/null -w "%{http_code}" https://huggingface.co` deve dar 200.
2. Escolha o motor. Ordem de preferência (todos abertos e gratuitos):
   - **Chatterbox** (`pip install chatterbox-tts`, MIT): o mais natural, com controle de emoção.
   - **VoxCPM2** ou **OmniVoice** (k2-fsa/OmniVoice), que são os usados pelo VoiceStudio.
   Gere 3 frases de teste (`t:hello`, `t:listen`, `w:fishing`), mande os arquivos ao pai pelo chat e pergunte qual voz ele prefere antes de regravar tudo.
3. Regrave com a voz escolhida, editando `build_audio.py`:
   - troque a função `tts()` pelo novo motor (saída a 24 kHz mono; mantenha `pad()`, a margem inicial e o mp3 a 64 kbps);
   - `ws:` (palavra devagar) precisa soar natural: gere a palavra com pausa/alongamento pelo próprio motor, ou estique com time-stretch de qualidade (rubberband), sem robotizar;
   - os **sons das letras** (`ph:` e o início de `so:`) também devem ficar na mesma voz. Grave sílabas portadoras no novo motor ("ahs", "ahm", "pah", "kah"…), recorte o som com as funções de `phon.py` (`noise_run`, `tail_after_vowel`, `stop`…) e confira com `pattern()`: fricativas só ruído, nasais só murmúrio, oclusivas curtas sem "uh".
4. Mantenha as chaves do `audio.js` (`ph:`, `so:`, `w:`, `ws:`, `s:`, `t:`) e o `window.PHON` com `t`, `tb`, `tw`, `db`, porque o app depende delas.
5. Teste com o Playwright (veja a skill `voz-natural`), copie o `audio.js` novo para `leitura/`, rode `python3 publicar.py`, faça commit e push. O Render publica sozinho em leitura-miss-lua.onrender.com.

## Estilo de professora (já implementado no app; mantenha)

- Pergunta: só os sons, com pausas curtas; a criança junta.
- "My turn" depois da resposta ou do erro: sons → junta devagar → palavra.
- Frases curtas e calorosas: "My turn. Watch the letters, and listen." / "Your turn!"
