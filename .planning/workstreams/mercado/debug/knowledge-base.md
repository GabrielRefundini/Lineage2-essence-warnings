# GSD Debug Knowledge Base — workstream `mercado`

Sessoes de depuracao resolvidas. O `gsd-debugger` le este arquivo no inicio de
cada investigacao para levantar hipoteses de padrao conhecido.

O registro LONGO de cada caso vive no ledger `.planning/WINDOWS.md`; aqui fica
so o bastante para reconhecer o padrao de novo.

---

## mercado-duas-leitoras-ocr — `id()` reciclado derruba um teste que conta objetos
- **Date:** 2026-08-31
- **Error patterns:** `assert 5 == 6`, `len(ambas) == len(leitura.linhas)`, `set(vistos_2x) & set(vistos_3x)`, `RECUSADA (numero)`, teste verde em isolamento e vermelho no arquivo inteiro, teste que fica verde quando instrumentado
- **Root cause:** O teste usava `id(pixels)` de recortes numpy TRANSITORIOS como identidade estavel e depois deduplicava com `set()`. O CPython recicla o endereco assim que o recorte de uma linha e liberado, entao recortes diferentes apareciam com o mesmo `id`. AND de duas condicoes: identidade insegura E um padrao de alocacao que recicle. `efcd73a` (o estabilizador do 02-05) foi GATILHO, nao causa — mudou a alocacao, e o corpo do teste e byte-identico antes e depois.
- **Fix:** `LeitoraContadora` segura referencia forte a cada recorte (`self._vivos`); nenhuma afirmacao tocada.
- **Files changed:** tests/test_mercado_leitura.py
- **Why not caught:** Nenhum portao pega isto. O teste era NAO-DETERMINISTICO por construcao e ficou verde por sorte de alocacao desde que nasceu; a contagem de fechamento da fase, que teria pego, foi medida antes do commit que fechou a fase (janela #38).
- **Recurrence guard:** Comentario no proprio `LeitoraContadora` explicando por que a referencia e segurada; janelas #37 e #38 no ledger; e esta entrada. **Regra geral: `id()` so e identidade enquanto o objeto VIVE — nunca use `id()` de objeto transitorio como chave de `set`/`dict` para contar coisas.**
- **Sinal diagnostico que vale ouro:** se instrumentar o caso o faz sumir (um wrapper vazio deixa a suite verde), a causa esta no layout do heap, nao na logica. Meca so o que NAO depende do alocador — contadores e comprimentos de lista, nunca `len(set(...))` de enderecos.
---
