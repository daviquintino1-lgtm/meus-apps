# Como o áudio da Miss Lua é feito

- **Frases e palavras:** voz Chatterbox (MIT) clonada do timbre `ref_heart.wav` ("Heart", escolhida pelo pai em 23/10/2026). Quando a Chatterbox pronuncia uma palavra solta errado, a palavra vem do Kokoro `af_heart` (mesmo timbre, pronúncia de dicionário).
- **Sons das letras (`ph:`):** **gravações humanas reais**, recortadas exatamente como a pessoa fala, sem cortar o "uh" e sem esticar. A, b, c… vêm de um vídeo de alfabeto; ch, sh e th de um vídeo de digraphs. Só o "ing" é da Miss Lua. Ficam em `sons.npz`. **Nunca gere sons de letras por voz sintética**: soa como bateria e confunde a criança.
- **No app:** a criança toca numa letra para ouvir o som dela. "Hear it" fala a palavra inteira. Não existe soletrar automático.

## Passo a passo (palavras novas da semana)

```
cd leitura/gerar-audio
python3 build_audio.py          # grava só o que não está em cache/ (~30 s por fala)
python3 conferir_palavras.py    # "ouve" cada palavra e corrige as erradas
python3 limpar_palavras.py      # tira sons soltos antes/depois das palavras
python3 build_audio.py          # monta audio.js de novo (agora tudo do cache)
cp audio.js ../audio.js
python3 testes/teste_app.py <audio.js antigo>; python3 testes/teste_fluxo.py
cd ../.. && TZ=America/New_York python3 publicar.py
```

- `cache/` guarda cada fala já gravada (chave = md5 do texto) e vai para o git, então só as palavras novas são gravadas. `cache/orig_*` é a gravação antes da limpeza.
- `conferencia.json` e `limpeza.json` mostram o que o reconhecedor ouviu em cada palavra. Ele ouve "th" como "s" e erra vogais curtas, então isso não é defeito da gravação.
- Requer `huggingface.co` e `*.hf.co` liberados (modelos Chatterbox, wav2vec2).
- `phon.py`, `sons_chatterbox.py` e `sons_fix.py` são tentativas antigas de sons sintéticos e ficam só como histórico.
