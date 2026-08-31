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

## series-duplicadas-por-catalogo-sem-estado — o catalogo nao valia para as linhas ABAIXO na mesma pagina
- **Date:** 2026-08-31
- **Error patterns:** duas series para o mesmo item, `primeira_vez` byte a byte identico entre duas chaves, `4-hunter-s-stockings#4` x `4-hunter-s-st-kings#4`, `n` da mediana pela metade sem aviso, agrupamento correto em isolamento e errado em producao
- **Root cause:** `_ler_a_pagina` (mercado_pagina.py:681) entregava a MESMA referencia `self._catalogo` para todas as linhas (`:725`), e quem escreve nele — `_gravar_no_catalogo` (`:785`) — so roda em `:503`, depois da pagina INTEIRA. Serie criada pela linha i invisivel para a linha j>i da mesma passada. AND de duas condicoes: o catalogo estagnado E duas ofertas do mesmo item na MESMA pagina (atraves de paginas o estado acumulava certo, e por isso nunca apareceu antes).
- **Fix:** catalogo PROVISORIO da pagina (`dict(self._catalogo)`), estendido por `_acrescentar_serie` a cada linha aceita — a mesma mecanica de entrada provisoria que `_ler_o_nome` ja usava um nivel abaixo, levantada para o nivel da pagina. A copia preserva a garantia de dois frames.
- **Files changed:** l2scanner/mercado_pagina.py, tests/test_mercado_leitura.py
- **Why not caught:** Nenhum portao pegava. `tests/test_mercado_pagina.py` nao tinha NENHUMA mencao a `catalogo`, e todo teste de pagina injetava um nome CONSTANTE para todas as linhas — com todas lendo a mesma string, todas derivam a mesma chave e a divisao dentro da pagina era ESTRUTURALMENTE invisivel. A fixtura mascarava o defeito.
- **Recurrence guard:** `tests/test_mercado_leitura.py::TestOTracerPontaAPonta::test_duas_ofertas_do_MESMO_item_na_MESMA_pagina_viram_UMA_serie`, com a leitora `LeitoraPorLinhaDaPagina` que da nome POR LINHA e quebra a fixtura de nome constante. As duas metades do conserto sao mortas por testes diferentes (mutacao verificada).
- **Sinal diagnostico que vale ouro:** quando o algoritmo esta CORRETO medido em isolamento e errado em producao, pare de mexer no algoritmo — o defeito e o ESTADO com que ele foi chamado. E quando duas linhas de dado nascem com carimbo de tempo byte a byte identico, elas vieram do mesmo lote; a pergunta deixa de ser "por que a segunda nao viu a primeira depois" e vira "o que a segunda enxergava ENQUANTO a primeira nascia".
- **A decima vez do padrao:** mecanismo instalado que nunca roda com o estado certo, com tudo verde porque o estado degenerado e indistinguivel do valido. Aqui o agrupamento EXISTIA, estava CORRETO, e nao era CONSULTADO com o catalogo atualizado. Procure sempre: o teste exercita a funcao pura, ou a FIACAO dela?
---
