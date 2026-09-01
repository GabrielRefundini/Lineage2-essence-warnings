---
phase: 05-a-aba-adena-e-a-taxa-de-cambio
plan: 02
subsystem: mercado
tags: [adena, portao-de-layout, calibracao-opcional, matriz-de-casamento, taxa-de-cambio]

requires:
  - phase: 05-01
    provides: "`ler_linha_de_adena`, `quantidade_de_adena`, `CHAVE_DA_SERIE_DA_ADENA` — consumidos SEM mudanca"
  - phase: 02-leitura-de-linha
    provides: "`casamento_do_cabecalho`, `cabecalho_de_calibracao`, `ler_linha`, `_conferir_uma_coluna`, `_conferir_o_cabecalho_de_coluna`"
provides:
  - "`Calibracao.mercado_layouts` — a chave OPCIONAL e aninhada dos layouts alem da negociacao, com `VERSAO_DO_ESQUEMA` intacta em 2"
  - "`calibracao._conferir_os_layouts_de_mercado` — validacao de ARRANQUE do bloco aninhado (T-05-04)"
  - "`calibracao._conferir_a_forma_de_uma_coluna` e `_conferir_um_molde_de_cabecalho` — corpos comuns EXTRAIDOS, nao copiados"
  - "`mercado_pagina.modelo_de_layout(cal, nome)` — a geometria de UM layout, com heranca de grade (D-D)"
  - "`mercado_pagina.LEITORAS_DE_LINHA_POR_LAYOUT` / `LAYOUTS_COM_LEITORA` / `leitora_de_linha` — o conjunto FECHADO de candidatos, derivado das leitoras que existem"
  - "`LeitorDePagina._casamento_do_layout` -> `str | None` — o portao ESCOLHE, e empate nao e veredito (T-05-05)"
  - "A matriz de casamento MEDIDA nos dois sentidos, no fonte e em teste"
affects: [05-03 registro e console da taxa, 05-04 calibracao da aba adena]

actuals:
  # Mesma escala do `estimate` do plano (chars/4 sobre `files_modified` inteiros).
  # Sobre o DIFF realizado apenas (1.456 insercoes / 121 delecoes) seriam ~14.500.
  tokens: 79117
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Matriz de casamento medida nos DOIS sentidos e reafirmada por teste contra os pixels versionados"
    - "Conjunto de candidatos DERIVADO do registro de leitoras, nunca uma segunda lista a mao"
    - "Registro que guarda o NOME e resolve tarde, para o despacho continuar observavel por monkeypatch"
    - "Retarget de teste com controle negativo quando o EXEMPLO envelhece mas a VERDADE nao"

key-files:
  created: []
  modified:
    - l2scanner/calibracao.py
    - l2scanner/mercado_pagina.py
    - tests/fixtures/mercado/calibracao_de_fixture.json
    - tests/test_mercado_adena_pagina.py
    - tests/test_mercado_pagina.py
    - tests/test_mercado_replay.py

key-decisions:
  - "O VAO ENTRE OS MOLDES E SIMETRICO (0,1331 nos dois sentidos), e isso CORRIGE a suposicao A1 da pesquisa, que esperava assimetria. `casamento_da_ancora` e correlacao normalizada, e correlacao normalizada e simetrica nos seus dois argumentos."
  - "`mercado_layouts` entra por `.get`, opcional, com `VERSAO_DO_ESQUEMA` em 2: TODO calibration.json que existe hoje esta sem ela."
  - "O conjunto de candidatos e derivado de `LEITORAS_DE_LINHA_POR_LAYOUT` e `busca` fica FORA — medido por mutacao: reintroduzi-la faz o veredito da janela de negociacao virar de 'negociacao' para None."
  - "O registro guarda o NOME da leitora, nao o objeto: guardar o objeto congela a ligacao no import e apaga a prova de CHAMADA da trava."
  - "Vencer e passar o PROPRIO limiar E ter o maior score; empate devolve None, para o veredito nao depender da ordem em que o usuario calibrou."
  - "A Adena tem DOIS recortes e nenhum outro, afirmados por IGUALDADE de conjunto: com continencia um terceiro recorte sobre a `Auction List` passaria calado."

requirements-completed: [ADEN-01, ADEN-02]

duration: 41min
completed: 2026-09-01
status: complete
---

# Phase 5 Plan 02: As duas grades convivem, e o portao ESCOLHE — Summary

**O portao de layout deixou de so RECUSAR e passou a ESCOLHER entre dois moldes medidos, com a chave nova entrando opcional para nao matar o arranque de ninguem — e `janela_adena_f014.png` agora atravessa de pixels a nove linhas de taxa, derrubando a decima pela guarda de cruzamento.**

## O PORTAO DE PARADA — as OITO casas medidas, com os numeros

**Medido ANTES de escrever uma linha de codigo**, com o codigo de producao (`sugerir_o_molde_do_cabecalho` sobre `cabecalho_adena.png`, corte de brilho MEDIDO em **222**), contra as quatro bandas versionadas. Limiar: **0,73** (`CASAMENTO_MINIMO_DA_ANCORA`).

| banda | molde = **negociacao** | molde = **adena** |
|---|---|---|
| `cabecalho_negociacao_goods.png` | **1,0000000000** PASSA | 0,1330654919 recusa |
| `cabecalho_negociacao_unitprice.png` | **1,0000000000** PASSA | 0,1330654919 recusa |
| `cabecalho_adena.png` | 0,1330654919 recusa | **1,0000000000** PASSA |
| `cabecalho_busca.png` | -0,0026558696 recusa | -0,0029105034 recusa |

**Vencedor por banda:** goods → `negociacao` · unitprice → `negociacao` · adena → `adena` · busca → **NENHUM**.

### As quatro condicoes de parada, uma a uma

| # | Condicao | Medido | Disparou? |
|---|---|---|---|
| 1 | molde adena passa contra `goods` **ou** `unitprice` | 0,1331 e 0,1331, ambos < 0,73 | **NAO** |
| 2 | molde negociacao passa contra `adena` | 0,1331 < 0,73 — **identico ao 0,1331 que a pesquisa registrou** | **NAO** |
| 3 | **qualquer um** passa contra `busca` | -0,0027 e -0,0029, ambos < 0,73 | **NAO** |
| 4 | molde adena **NAO** passa contra `adena` | 1,0000 ≥ 0,73 — passa | **NAO** |

**Nenhuma das quatro disparou. Nenhum limiar foi ajustado** — o `0,73` e o que ja estava na fixtura e em `CASAMENTO_MINIMO_DA_ANCORA`, e ele cai no meio de um vao de oito decimos e meio.

### O achado que o plano nao previa: **o vao e SIMETRICO**

A pesquisa registrava o vao como **assimetrico (A1)**. Medido nos dois sentidos, ele e **simetrico**: `0,1330654919` tanto de adena→negociacao quanto de negociacao→adena, ate a decima casa. Faz sentido depois de medido — `casamento_da_ancora` e uma **correlacao normalizada**, que e simetrica nos seus dois argumentos. Isto esta escrito na docstring de `_casamento_do_layout`, no comentario da `MATRIZ_MEDIDA` do teste, e afirmado por `test_o_vao_e_SIMETRICO_e_isso_corrige_a_suposicao_A1`.

## Verificacao — CADA `<automated>` com o resultado REAL

| Criterio | Comando exato | Resultado real |
|---|---|---|
| Task 1 `<automated>` | `pytest tests/test_mercado_adena_pagina.py tests/test_calibracao_mercado.py tests/test_calibracao_generica.py -x -q` | **163 passed, 1 skipped** |
| Task 2 `<automated>` | `pytest tests/test_mercado_adena_pagina.py tests/test_mercado_pagina.py -x -q` | **120 passed** |
| Task 3 `<automated>` | `pytest tests/test_mercado_adena_pagina.py tests/test_mercado_replay.py -x -q` | **96 passed, 9 skipped** |
| `<verification>` linha 1 | `pytest tests/test_mercado_adena_pagina.py -q` | **63 passed** |
| `<verification>` linha 2 | `pytest tests/test_mercado_pagina.py tests/test_mercado_replay.py tests/test_calibracao_mercado.py tests/test_mercado_modo.py -q` | **295 passed, 10 skipped** |

### Pytest — base do worktree e DELTA

- **Base deste worktree, medida ANTES de tocar em nada:** `4077 passed, 24 skipped`
- **Depois:** `4144 passed, 24 skipped`
- **Delta: +67 passed, +0 skipped, 0 falhas.**

A referencia da main citada no briefing e `4099 passed, 2 skipped`; este worktree pula **22 a mais** (fixturas gitignored), e `4077 + 22 = 4099` — consistente, mesma explicacao que o 05-01 registrou.

### `<success_criteria>` do plano, um a um

- [x] A matriz de 8 numeros esta no fonte (docstring de `_casamento_do_layout`) **E** afirmada por teste, com o vencedor por banda.
- [x] `pecas_de_calibracao_de_mercado_faltando` devolve exatamente **15** nomes numa `Calibracao` vazia de mercado — com controle negativo que prova que a lista reage a uma peca de verdade.
- [x] `janela_adena_f014.png` produz **9 linhas** de taxa; a **linha 5** cai por `cruzamento`.
- [x] `janela_negociacao_f005.png` le **igual** com e sem `mercado_layouts`, campo a campo.
- [x] `VERSAO_DO_ESQUEMA` continua **2** (`grep` no fonte).
- [x] Nada foi escrito em `.mercado/` nem no `calibration.json` da maquina — `git status --short .mercado calibration.json` **vazio**; o diff dos 4 commits lista **exatamente 6 arquivos**, todos do plano.

## Restricoes invioláveis, conferidas

| Restricao | Como foi conferida | Resultado |
|---|---|---|
| `busca` fora dos candidatos | mutacao medida (abaixo) | **fora**, e a exclusao e load-bearing |
| chave nova OPCIONAL (`.get`) | `test_ausente_carrega_sem_erro_e_chega_como_None` | OK |
| `VERSAO_DO_ESQUEMA` nunca bumpada | `grep -n "^VERSAO_DO_ESQUEMA"` → `= 2` | OK |
| nao tocar `rastreador.py` / gate de brilho em `visao.py` | `git diff --name-only` | **nao aparecem** |
| nao tocar `respawn/bosses/agenda/sessao/test_bosses` | `git diff --name-only` | **nao aparecem** |
| nao escrever em `.mercado/` nem `calibration.json` | `git status --short` daqueles caminhos | **vazio** |
| `recordings/` somente-leitura, sem glob amplo | nao foi lido em momento nenhum | OK |
| nenhuma dependencia nova (FIRE-01) | `requirements`/`pyproject` fora do diff; `test_mercado_firewall_de_fase.py` | **17 passed** |
| nenhum `--amend`, nunca `git stash` | — | nenhum dos dois foi usado |

## Os CONTROLES NEGATIVOS medidos, e nao supostos

Tres propriedades desta onda seriam indistinguiveis de acidente sem uma medicao no sentido oposto. As tres foram medidas:

**1. A exclusao da `busca` (a restricao mais importante do briefing).**

```
COMO ESTA        candidatos=['adena', 'negociacao']          vencedor='negociacao'
COM A MUTACAO    candidatos=['adena', 'busca', 'negociacao'] vencedor=None
```

Reintroduzindo `busca` como candidato elegivel, o veredito da **janela de negociacao** vira de `'negociacao'` para `None` — a pagina e RECUSADA. E exatamente a perda que o ADEN-01 proibe (353 paginas lidas contra 2 perdidas em campo), e ela acontece porque `busca` empata 1,0000 com `negociacao` e empate nao e veredito.

**2. A conferencia de faixa do limiar aninhado.** Simulando o bug (procurar pela chave pontuada em vez do campo), `limiar_do_cabecalho: 0.0` **passa calado**. Com o `campo` correto, levanta `mercado_layouts.adena.limiar_do_cabecalho=0.0 esta fora de (0.0, 1.0]`.

**3. A ligacao tardia da leitora.** Com a funcao congelada no import, `TestOLeitorDePaginaCONSULTA_A_TRAVA` falha na propria guarda de vacuidade. Ver os Desvios.

## Accomplishments

- **`mercado_layouts` entra ANINHADA e OPCIONAL**, com `VERSAO_DO_ESQUEMA` em 2. A lista das quinze **nao cresceu**: quem nunca calibrou a Adena continua com o `--mercado` subindo.
- **Validacao de arranque** (`_conferir_os_layouts_de_mercado`, T-05-04): tipo, faixa e contagem de bytes contra `altura * largura`, com `negociacao` recusada como chave aninhada. Um hex torto levanta onde o usuario ainda le "recalibre", em vez de virar feature OFF sem causa legivel.
- **Os corpos comuns foram EXTRAIDOS, nao copiados** — `_conferir_a_forma_de_uma_coluna` e `_conferir_um_molde_de_cabecalho`. A conferencia contra a grade ficou deliberadamente **fora** da forma da coluna: a de topo se confere contra `mercado_grade` e a aninhada contra a grade DELA, que pode ser herdada.
- **O portao ESCOLHE**, devolvendo `str | None`. Cada layout traz o **proprio** limiar; empate devolve `None`.
- **`modelo_de_layout`: uma montagem so** para os dois casos, com a heranca de grade acontecendo num lugar so. O bloco da Adena na fixtura sai **sem `grade` nenhuma** — hoje as geometrias sao identicas, e a copia so criaria dois numeros para envelhecerem separados.
- **A pagina da Adena, ponta a ponta:** 9 linhas com a sentinela `adena#`, a linha 5 derrubada por `cruzamento` (o `13588` que a tela mostra como `135,00`), quantidades em `{5.000.000, 10.000.000}` e **zero chamadas de OCR**.
- **A `Auction List` nao e tocada**, e isso e afirmado por **igualdade** de conjunto (`== {"total","unitario"}`) — o W4 do checker. Com continencia, um terceiro recorte inutil passaria e as 9 linhas continuariam saindo.
- **Zero mudanca em `mercado_registro` e `mercado_analise`.** A `LinhaLida` da Adena atravessa o acordo entre dois frames, a dedup e o CSV pelo caminho que ja existe (ADEN-03).

## Task Commits

| Task | Commit | O que entrou |
|---|---|---|
| 1 | `7748110` | `mercado_layouts` opcional, validacao de arranque, corpos comuns extraidos |
| 2 | `7c72809` | a matriz medida, `modelo_de_layout`, o portao que escolhe, o registro de leitoras |
| 3 | `96e13b9` | os recortes por modelo, o despacho por layout, a pagina da Adena ponta a ponta |
| — | `2496332` | **[Rule 1]** a leitora resolvida na hora, e nao congelada no import |

## Deviations from Plan

### 1. [Rule 1 — Bug introduzido por mim, pego pela suite cheia] O registro congelava a leitora no import

- **Encontrado:** ao rodar a suite cheia depois da Task 3.
- **O que quebrou:** `tests/test_mercado_leitura.py::TestOLeitorDePaginaCONSULTA_A_TRAVA::test_o_leitor_PASSA_A_SUA_trava_a_cada_ler_linha` falhou na **sua propria guarda de vacuidade** — `"ler_linha nao foi chamada: o teste nao cobre nada"`. Ele monkeypatcha `mercado_pagina.ler_linha`; meu `LEITORAS_DE_LINHA_POR_LAYOUT` guardava o **objeto** da funcao, capturado no import, entao o patch deixou de alcancar o despacho.
- **Por que importa alem do teste:** aquele criterio prova **CHAMADA** — que o leitor passa **A SUA** trava, a mesma em todos os ticks (uma construida por tick nasceria vazia e nao travaria nada). Congelar a referencia teria apagado essa prova em silencio. E criava duas referencias ao mesmo leitor, que divergiriam no dia em que uma fosse trocada.
- **Fix:** o registro passa a guardar o **NOME**, e `leitora_de_linha` resolve por `globals()` na hora da chamada. Dois testes novos prendem a propriedade, com controle negativo no sentido oposto.
- **Commit:** `2496332`.

### 2. [Rule 2 — funcionalidade critica antecipada] O conjunto fechado de candidatos entrou na Task 2, nao na Task 3

- **O plano** poe `LEITORAS_DE_LINHA_POR_LAYOUT` e a exclusao da `busca` no `<action>` da **Task 3**, e o portao que escolhe na **Task 2**.
- **O problema:** isso deixaria o commit da Task 2 numa janela em que um `busca` calibrado **poderia vencer** o portao e recusar a pagina — a perda exata que o briefing chama de inviolavel. Commits atomicos devem ser seguros isoladamente.
- **O que foi feito:** o registro e a derivacao do conjunto entraram na **Task 2** (onde o portao vive); o **despacho** da leitora dentro de `_ler_a_pagina` ficou na Task 3, como o plano manda. Nenhum commit desta onda tem a janela insegura.

### 3. [Rule 1 — testes cujo EXEMPLO envelheceu] Quatro testes de negociacao foram retargetados

Quatro testes em `test_mercado_pagina.py` (3) e `test_mercado_replay.py` (1) usavam **"a aba Adena"** como exemplo de aba nao-lida. Esta fase existe justamente para torna-la lida, entao eles passaram a medir a ausencia de um recurso que passou a existir.

- **A verdade prendida NAO mudou:** "uma aba cujo layout nao esta calibrado e recusada, com zero linhas e zero OCR".
- **O sujeito mudou** para uma calibracao **sem `mercado_layouts`** — o clone que nunca calibrou a Adena, que e literalmente a instalacao de todo usuario hoje, e portanto um exemplo **mais forte** que o antigo.
- **Um controle negativo foi ACRESCENTADO em cada arquivo:** a MESMA janela, com a chave a mais, deixa de ser recusada. Sem ele, "recusada" nao distinguiria a falta da chave de um painel nao localizado ou de uma fixtura ilegivel.
- **Um teste afirmava a mensagem ANTIGA** (`"SOMENTE o layout calibrado"`), que o `<action>` da Task 2 manda reescrever por ser meia-verdade depois desta fase. Ele passou a afirmar a nova **e** a **ausencia** da antiga.
- Commits: `7c72809` e `96e13b9`, com a razao na mensagem de cada um.

### 4. [Rule 3 — bug em codigo que eu mesmo acabara de escrever] `_numero_de_mercado` procurava pela chave pontuada

Ao reusar `_numero_de_mercado` para o limiar aninhado, passei o nome pontuado como chave de **busca**. O `.get` devolveria `None` e a conferencia **passaria sempre, calada** — uma validacao vacua nascendo pronta. Pego antes do commit; corrigido com o parametro `campo`, que separa o que se PROCURA de como se CHAMA na mensagem. **Medido por mutacao** (secao dos controles negativos). Entrou no commit `7748110`.

---

**Total deviations:** 4 (2 bugs auto-corrigidos, 1 antecipacao deliberada por seguranca, 1 retarget de teste com controle negativo acrescentado).
**Impact on plan:** nenhum desvio de escopo. O codigo entregue e o que o `<action>` das tres tasks descreve.

## Criterios que se revelaram vacuos

**Nenhum dos `<automated>` do plano.** Os tres foram rodados **exatamente como escritos** e os tres discriminam.

Dois criterios que **eu** escrevi quase nasceram vacuos e foram corrigidos antes de commitar — o `_numero_de_mercado` do Desvio 4 (uma validacao que passaria sempre) e a exclusao da `busca`, que so virou prova depois da mutacao medida. Ambos estao acima com o numero real.

Sobre o **W4 do checker**: mantido como pedido — o conjunto de recortes do layout adena e verificado por **igualdade** (`== {"total","unitario"}`), nunca continencia, e a razao esta escrita na docstring da classe de teste.

## Issues Encountered

Nenhum bloqueio. O portao de parada nao disparou, entao a fase seguiu sem checkpoint.

## Known Stubs

Nenhum. Nenhum valor vazio codificado, texto de placeholder, `TODO` ou `FIXME` no codigo desta onda. Todo simbolo novo tem consumidor imediato: `modelo_de_layout` e `leitora_de_linha` sao chamados por `_ler_a_pagina` e pelo construtor; `mercado_layouts` e lido pelo portao; e a suite os exercita contra pixels reais.

**Nota de honestidade sobre a `grade` da Adena:** ela sai **ausente** da fixtura e herda tudo de `mercado_grade`. Isto e uma decisao (D-D), nao um stub — mas vale dizer em voz alta que **`linhas_por_pagina` herdado vale 10**, e o `LINHAS_ESPERADAS` do calibrador diz **9** para a aba adena. Nao ha conflito medido: `janela_adena_f014.png` tem 10 linhas materiais (9 boas + a que cai por cruzamento) e o teste ponta a ponta confirma. Se uma gravacao futura mostrar 9 linhas materiais, o campo proprio ja e suportado e testado (`test_um_campo_PROPRIO_vence_a_heranca`). Fica registrado para o **05-04**, que e quem calibra a aba.

## Threat Flags

Nenhuma superficie nova alem da que o `<threat_model>` do plano ja registrava.

- **T-05-04** (tampering em `mercado_layouts`) — **mitigado**: `_conferir_os_layouts_de_mercado` roda no arranque, e a contagem de bytes e afirmada por teste com controle negativo.
- **T-05-05** (portao escolhendo errado) — **mitigado e MEDIDO**: matriz nos dois sentidos, limiar proprio por layout, empate → `None`, e a mutacao da `busca` acima.
- **T-05-06** (bloco corrompido derrubando o leitor) — **mitigado**: molde recusado entra como ausente com aviso; `test_a_negociacao_continua_lida_com_o_bloco_torto` prova que o leitor segue.

Sem instalacao de pacote nesta fase (FIRE-01), conferido.

## Next Phase Readiness

**Pronto para o 05-03.** O que ele encontra construido:

- A `LinhaLida` da Adena ja **chega** ao registro e a analise pelo caminho existente, com `chave_da_serie == 'adena#'`. Nada em `mercado_registro`/`mercado_analise` foi tocado — o 05-03 encontra o terreno como o 05-01 o deixou.
- `LeitorDePagina._layout_atual` expoe qual aba esta na tela, se o console quiser exibir.
- **`requirements.mark-complete` NAO foi executado**, pela mesma razao que o 05-01 documentou: `ADEN-01`/`ADEN-02` tambem sao reivindicados pelo `05-04`, que ainda nao rodou. `requirements-completed` no frontmatter deste summary registra a contribuicao **desta** onda, que e verdadeira. Quem fechar a fase marca de uma vez.
- **Pendencia herdada do 05-01, nao resolvida aqui** (e nao era escopo): o ramo que aceita arredondamento (`133,33 / 66,66`) segue sem um pixel no repositorio. As 9 linhas boas de `janela_adena_f014.png` dividem todas exato.

## Self-Check: PASSED

Arquivos afirmados, conferidos em disco:

- FOUND `l2scanner/calibracao.py`
- FOUND `l2scanner/mercado_pagina.py`
- FOUND `tests/fixtures/mercado/calibracao_de_fixture.json`
- FOUND `tests/test_mercado_adena_pagina.py`
- FOUND `tests/test_mercado_pagina.py`
- FOUND `tests/test_mercado_replay.py`

Commits afirmados, conferidos em `git log`:

- FOUND `7748110`, `7c72809`, `96e13b9`, `2496332`

---
*Phase: 05-a-aba-adena-e-a-taxa-de-cambio*
*Plan: 02*
*Completed: 2026-09-01*
