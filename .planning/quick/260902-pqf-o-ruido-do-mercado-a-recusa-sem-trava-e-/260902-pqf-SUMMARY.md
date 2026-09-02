---
phase: quick-260902-pqf
plan: 01
quick_id: 260902-pqf
subsystem: mercado
status: complete
tags: [mercado, ruido, log-rotativo, trava, mediana, anal-02, leit-04]
requires:
  - "l2scanner/mercado_leitura.py::TravaDaObservacao (o molde da trava nova)"
  - "l2scanner/mercado_console.py::TravaDoDestaque (a doutrina em prosa)"
provides:
  - "l2scanner/mercado_leitura.py::TravaDaRecusa"
  - "l2scanner/mercado_analise.py::ModeloDeMercado.vereditos_da_pagina"
  - "l2scanner/mercado_modo.py::processar_a_pagina_aceita"
affects:
  - "l2scanner/mercado_leitura.py::ler_linha (keyword-only trava_da_recusa, sem default)"
  - "l2scanner/mercado_leitura.py::ler_linha_de_adena (idem)"
  - "l2scanner/mercado_leitura.py::_recusar (quarto parametro posicional)"
  - "l2scanner/mercado_pagina.py::LeitorDePagina (a quinta trava do leitor)"
  - "l2scanner/mercado_modo.py::laco_do_mercado (o for virou chamada)"
tech-stack:
  added: []
  patterns:
    - "trava-de-anuncio-da-sessao: conjunto publico + anunciar() devolvendo TEXTO ou None"
    - "referencia-congelada-por-pagina: julgar a pagina inteira antes de mover a populacao"
    - "funcao-pura-devolve-texto: o laco imprime, a funcao acumula e devolve"
key-files:
  created: []
  modified:
    - l2scanner/mercado_leitura.py
    - l2scanner/mercado_pagina.py
    - l2scanner/mercado_analise.py
    - l2scanner/mercado_modo.py
    - tests/test_mercado_leitura.py
    - tests/test_mercado_adena.py
    - tests/test_mercado_ciano.py
    - tests/test_mercado_modo.py
    - tests/test_mercado_console.py
decisions:
  - "O INDICE ENTRA na chave de TravaDaRecusa e SAI na de TravaDaObservacao — divergencia deliberada, com o custo medido e limitado a dez linhas por rolagem contra 3.600/hora"
  - "A referencia do destaque e CONGELADA por PAGINA, e o custo aceito (uma pagina de ofertas baratas anuncia todas contra a referencia congelada) esta escrito na docstring"
  - "A contagem do log saiu do criterio do Teste 2 da Task 1: duplicar a conta do Teste 1 destruia o valor diagnostico do teste sob mutacao"
metrics:
  duration: "~55 min"
  completed: 2026-09-02
  tasks: 2
  commits: 2
actuals:
  tokens: 41000
  tasks: 2
  commits: 2
---

# Quick 260902-pqf: O ruido do mercado — a recusa sem trava e a mediana que anda Summary

Duas mensagens de producao pararam de mentir: a recusa de linha ganhou a setima
trava do modo (uma linha de log por oferta e por sessao, em vez de ~3.600 por
hora) e o veredito do destaque passou a ser julgado contra uma referencia
CONGELADA por pagina, deixando de depender de onde a linha calhou de estar na
grade.

## O que foi feito

### Task 1 — `TravaDaRecusa`, a setima trava (commit `e162b01`)

`TravaDaRecusa` entrou em `l2scanner/mercado_leitura.py`, colada a
`TravaDaObservacao` e no mesmo molde: conjunto publico `ja_recusadas`,
`anunciar()` devolvendo o TEXTO (nunca booleano, nunca string vazia), escopo de
SESSAO, conjunto nao podado. O texto e byte-identico ao que `log.warning`
renderizava antes — ha teste vivo lendo essa string, e mudar a forma quebraria
forense de campo por nada.

`_recusar` ganhou o quarto parametro posicional e obrigatorio, e o corpo virou:
pedir o texto a trava, `log.warning` so quando o texto nao for `None`, e
devolver o `Descarte` SEMPRE. A trava desce por `ler_linha`,
`ler_linha_de_adena` e `_ler_o_nome` como keyword-only sem valor de fabrica, e
`LeitorDePagina` a constroi uma vez e a passa nos DOIS ramos de `_ler_a_pagina`.

### Task 2 — a mediana congelada por pagina (commit `857273c`)

`ModeloDeMercado.vereditos_da_pagina` julga todas as linhas contra o modelo como
ele esta AGORA e devolve a tupla alinhada com `linhas`. Continua pura.
`processar_a_pagina_aceita` e a extracao literal do corpo do `for linha in
pagina.linhas:` — os quatro passos numerados e os comentarios do ANAL-02 vieram
juntos — com duas mudancas de comportamento: o congelamento como primeira linha
da funcao, e os anuncios acumulados numa lista devolvida em vez de `log.info` no
lugar.

## As duas provas por mutacao

Ambas rodadas, ambas com o resumo do pytest copiado verbatim para o corpo do
commit.

**Task 1** — apagado o portao `if chave in self.ja_recusadas: return None`:

```
FAILED tests/test_mercado_leitura.py::TestATravaDaRecusa::test_cinco_ticks_da_MESMA_recusa_dao_UM_registro_e_cinco_dao_CINCO
FAILED tests/test_mercado_leitura.py::TestATravaDaRecusa::test_o_INDICE_esta_na_chave_e_e_DELIBERADO
2 failed, 5 passed, 5276 deselected in 4.48s
```

Vermelho nos Testes 1 e 3, VERDE no Teste 2 — o dado nunca dependeu da trava.

**Task 2** — apagado o congelamento, devolvido o julgamento para dentro do laco:

```
FAILED tests/test_mercado_modo.py::TestAMedianaNaoSeMoveDebaixoDaPagina::test_a_MESMA_pagina_em_DUAS_ORDENS_anuncia_os_MESMOS_textos
FAILED tests/test_mercado_modo.py::TestAMedianaNaoSeMoveDebaixoDaPagina::test_os_QUATRO_anuncios_citam_a_MESMA_mediana_e_o_MESMO_n
2 failed, 2 passed, 5283 deselected in 1.41s
```

Vermelho nos Testes 1 e 2, VERDE no Teste 3. **E o mutante reproduziu o defeito
de campo caractere por caractere:**

```
E       AssertionError: {'10', '7', '8', '9'}
E       assert {'10', '7', '8', '9'} == {'7'}
```

`n=7 -> 8 -> 9 -> 10` — a mesma escada que o usuario viu na tela ontem.

## Achados

### 1. O Teste 2 da Task 1 estava se sabotando (encontrado PELA prova por mutacao)

Na primeira rodada da mutacao da Task 1 o Teste 2 tambem ficou vermelho — o que
o plano dizia significar "a implementacao esta engolindo `Descarte`, e isso e um
segundo defeito". **Nao era.** Ele caiu em `assert 5 == 1` sobre a contagem do
LOG, com os cinco `Descarte` INTACTOS.

A causa era o teste, e nao o codigo: eu havia escrito nele `len(registros) == 1`,
duplicando a conta que e do Teste 1. Isso destruia o proprio valor diagnostico do
Teste 2 — sob a mutacao, "vermelho" deixava de distinguir "a trava quebrou" de "o
`Descarte` foi engolido", que e exatamente a ambiguidade que o plano o desenhou
para eliminar. A contagem do log saiu do criterio e ficou so na mensagem de
falha, com a medicao escrita na docstring. Refeita a mutacao, o resultado passou
a ser o previsto pelo plano.

O plano se contradiz nesse ponto (o `<behavior>` pede "enquanto o log tem 1", a
`<prova_por_mutacao>` exige VERDE sob a mutacao). Resolvi a favor da prova por
mutacao, que e quem nomeia o valor diagnostico do teste. **Fica registrado para
quem reler o plano.**

### 2. O criterio 4 da `<verification>` do plano e CEGO

`grep -rn "mercado_tolerancia_do_cruzamento" l2scanner/ | grep -v "None"`
devolve nove linhas na arvore PRISTINA — sao docstrings, encanamento de
`calibracao.py` e o `self._tolerancia_do_cruzamento = cal....` de
`mercado_pagina.py`. Nenhuma delas LIGA a guarda. O criterio nao discrimina.

O que discrimina, e que rodei no lugar:
`git diff 33ebb56 -- l2scanner/ | grep -E "^[+-].*tolerancia_do_cruzamento"` —
**saida vazia**, ou seja o meu diff nao tocou uma linha sequer sobre a
tolerancia. A guarda continua desligada. E o mesmo padrao de criterio cego que o
04-05 ja registrou no STATE.md.

## Testes que mudaram de lado (nenhum apagado, todos com a razao no lugar)

| Teste | Antes | Agora | Razao |
|---|---|---|---|
| `test_mercado_leitura.py::TestOLogDaRecusa::test_NAO_ha_limitacao_de_repeticao` | `2 x descartadas` linhas em dois ticks | `test_HA_limitacao_de_repeticao_desde_2026_09_02`: primeiro tick = `descartadas`, segundo = ZERO, e o dado nao se move | O argumento antigo (o log rotativo e a unica forense) continua certo sobre o VALOR do log e estava errado sobre o EFEITO — o rodizio apagava a forense que a ausencia de trava existia para preservar. O numero continua DERIVADO de `ultima_leitura.descartadas`, nunca literal. |
| `test_mercado_adena.py::TestNadaAquiLeNome` (lista de parametros) | 13 nomes | 14, com `trava_da_recusa` antes de `catalogo` | O teste mudou porque o codigo mudou. A afirmacao da classe nao afrouxou: uma trava de LOG nao e uma leitora, e continua nao havendo por onde um `ler_texto` entrar. |
| `test_mercado_console.py::TestOLacoCONSULTA_A_TRAVA::test_o_laco_nao_chama_destaque_ao_vivo_direto` | janela = `laco_do_mercado` | janela = `laco_do_mercado` + `processar_a_pagina_aceita` | A extracao mudou o ENDERECO da chamada, nao a propriedade. Uma janela so no laco ficaria CEGA justamente para a funcao que faz o anuncio. `destaque_ao_vivo(` continua proibido nas duas. |

## Refactor puro — a prova

```
$ git diff 33ebb56 -- tests/test_mercado_modo.py | grep '^-' | grep -v '^---' | wc -l
0
```

**Zero linhas removidas** de `tests/test_mercado_modo.py`. Os testes ponta a
ponta de `laco_do_mercado` seguiram verdes sem uma edicao de expectativa, no
precedente ja registrado do 04-02.

## Suite

| Momento | Resultado |
|---|---|
| Base deste worktree (`56b998a`) | **5191 passed, 85 skipped** |
| Depois da Task 1 | 5198 passed, 85 skipped (+7) |
| Depois da Task 2 | **5202 passed, 85 skipped** (+11 no total) |

**Zero regressoes. A contagem de skips NAO mudou.**

Os numeros do plano (**4865 passed, 29 skipped**) sao de `33ebb56`; este worktree
nasceu de `56b998a`, que ja carrega o trabalho merjado de outros agentes. Os
numeros acima sao os que EU medi nesta arvore, como pedido. Comando usado em
todas as rodadas: `python -m pytest -q --ignore=tests/test_agenda.py`.

## Restricoes conferidas

- `git status --porcelain -- calibration.json .mercado/` — **vazio**. O
  `calibration.json` nao foi tocado nem commitado; nada foi escrito em
  `.mercado/`, e o vigia do usuario nao foi tocado. Todo teste novo usa
  `tmp_path`.
- `git diff 33ebb56 --name-only` nao lista `rastreador.py`, `visao.py`,
  `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`, `identidade.py`,
  `dashboard.py`, nem nada em `discord/` ou `renda*`.
- `git diff 33ebb56 -- l2scanner/ | grep -cE "pyautogui|pynput|keyboard|mouse"` = **0**.
- Nenhuma dependencia nova. `median_low`, `mercado_minimo_de_linhas_comparadas`
  (7), o corte 0,8947, o piso 0,8837, D-03, D-09, a letra de grade e
  `VERSAO_DO_ESQUEMA` (2) intocados.
- `recordings/` nao foi lido. Nenhum `git commit --amend`, nenhum `git stash`.
- Comentarios e mensagens de commit em portugues, na voz do modulo vizinho.

## Known Stubs

Nenhum. As duas funcoes novas estao ligadas ao caminho de producao e cada uma
tem um teste que afirma que ela foi CHAMADA (por identidade, no caso da trava;
por texto anunciado, no caso da referencia congelada) — nenhum criterio afirma
que um simbolo existe.

## Deferred Issues

- `python -m ruff check l2scanner/ tests/` aponta 3 `E741` (nome de variavel
  ambiguo `l`) em `l2scanner/visao.py:184`, `l2scanner/visao.py:749` e
  `tests/test_mercado_modo.py:559`. **Todos PRE-EXISTENTES e fora do escopo**
  — `visao.py` e arquivo proibido por este plano, e a linha 559 do teste nao foi
  tocada. Nao consertados de proposito.

## Self-Check: PASSED

- `.planning/quick/260902-pqf-.../260902-pqf-SUMMARY.md` — este arquivo.
- Commit `e162b01` — encontrado em `git log`.
- Commit `857273c` — encontrado em `git log`.
- `l2scanner.mercado_leitura.TravaDaRecusa` — importa e responde.
- `ModeloDeMercado.vereditos_da_pagina` — existe e a docstring cita `congelada` e `grade`.
- `mercado_modo.processar_a_pagina_aceita` — existe e e chamada pelo laco.

---

## Verificacao independente do orquestrador

Refeita em worktree isolado sobre o merge, com uma mutacao A MAIS do que o plano pedia — a de
CONTROLE, que existe para provar que o teste nao e sensivel a refatoracao:

| mutacao aplicada | resultado medido |
|---|---|
| (linha de base) | `232 passed in 18.42s` |
| A trava da recusa deixa de travar (some o `if chave in self.ja_recusadas: return None`) | `3 failed, 168 passed` |
| **CONTROLE:** trocar `vereditos_da_pagina(linhas)` por uma list comprehension de `veredito_do_destaque` — MESMA semantica, base ainda congelada | `61 passed` — **passa, e passar aqui e o correto** |
| B real: mover o veredito para DENTRO do laco que chama `acrescentar` | `2 failed, 59 passed` |

O controle e a parte que importa. Um teste que caisse tambem na terceira linha estaria preso a
FORMA do codigo, e nao ao comportamento — passaria a quebrar em toda refatoracao inocente e
seria desligado pela primeira pessoa apressada. Ele cai so quando a base volta a se mover.

## O sha do calibration.json mudou, e nao foi por esta tarefa

Ao conferir apos o merge, `calibration.json` saiu de `c41e665b8eac1669` para `93128e524e2160ff`.
Investigado por diff contra o backup `calibration.antes-de-ligar-a-guarda-20260902-070422.json`:
as duas unicas chaves alteradas sao `renda_moldes_da_barra` e `renda_por_personagem`, ambas de
`None` para conteudo, gravadas pelo agente paralelo do workstream `renda`. Os **13 moldes
acromaticos e os 13 cromaticos do mercado saem IDENTICOS** na comparacao elemento a elemento, e
`mercado_tolerancia_do_cruzamento` continua `None`.

Vale registrar o que isso confirma: a disciplina de load-mutate-save que a ferramenta de
calibracao adotou depois da janela quebrada 13 (2026-08-30) fez o que prometia — outro agente
escreveu no mesmo arquivo, no mesmo dia, e nao levou nada junto.
