---
phase: 02-leitura-de-p-gina
plan: 07
subsystem: leitura-de-mercado
tags: [opencv, hsv, brilho, calibracao, medicao, varredura, LEIT-02]

requires:
  - phase: 02-04
    provides: "o tracer `ler_linha` -> `LeitorDePagina`, o portao de layout, as fixturas de janela e a REFUTACAO 4 (o `1` da Quantity nao se le)"
  - phase: 02-06
    provides: "a terceira coluna (`Unit price`), `limite_derivado_do_cruzamento` e `residuo_do_cruzamento` — a aritmetica que vira o ROTULO nao circular"
  - phase: 02-08
    provides: "a particao do glifo COLADO, que REMOVEU a causa da REPROVA desta medicao"
provides:
  - "`tools/medir_brilho_da_quantidade.py`: a varredura que deriva o rotulo de Total/Unit price, classifica cada piso em tres baldes, recusa propor nos quatro casos e grava por load-mutate-save"
  - "`mercado_limiar_de_brilho_da_quantidade` = 161, MEDIDA, no `calibration.json` da maquina do usuario"
  - "`mascara_de_numero` e `segmentar_glifos_no_brilho` como primitivas IRMAS em `l2scanner/mercado_leitura.py`"
  - "o `valor_minimo` sem valor de fabrica em `ler_celula`, `ler_celula_de_numero`, `ler_celula_de_quantidade`, e os dois pisos em `ler_linha`"
  - "a decima chave no portao por AUSENCIA de `LeitorDePagina._calibrado()`"
  - "o rendimento da coluna Quantity medido no censo: 541 -> 2133 de 2247 celulas rotuladas"
affects: [02-05, fase-3-persistencia]

actuals:
  tokens: 61000
  tasks: 2
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Piso de brilho PROPRIO DA COLUNA, medido por varredura de passo 1 sobre o censo — o mesmo padrao que `VALOR_MINIMO_DO_SUFIXO = 120` ja tinha aberto, agora com o numero vindo de medicao e nao de sondagem"
    - "Primitiva IRMA em vez de assinatura quebrada: `segmentar_glifos_no_brilho(recorte, valor_minimo)` carrega o corpo e `segmentar_glifos(recorte)` vira a casca fina que nomeia o piso compartilhado — os 35 pontos de chamada continuam inteiros"
    - "Rotulo NAO CIRCULAR: a quantidade esperada e derivada de `Total` e `Unit price`, duas colunas que a Quantity nao toca"
    - "O piso gravado e o ULTIMO PISO SEGURO e nunca uma media: com passo 1 os dois sao inteiros adjacentes, e a media para baixo escolheria justamente o que erra"
    - "Teste que DERIVA o ramo em vez de escolhe-lo: comparar o valor gravado com o piso compartilhado decide se o criterio e desigualdade (PROPOSTO) ou igualdade (REPROVADO)"

key-files:
  created:
    - tools/medir_brilho_da_quantidade.py
    - tests/test_medir_brilho_da_quantidade.py
  modified:
    - l2scanner/mercado_leitura.py
    - l2scanner/mercado_pagina.py
    - l2scanner/calibracao.py
    - tests/test_mercado_leitura.py
    - tests/test_mercado_pagina.py
    - tests/test_calibracao_mercado.py
    - tests/test_medir_leitura_de_glifo.py
    - tests/fixtures/mercado/calibracao_de_fixture.json

key-decisions:
  - "O piso foi MEDIDO em 161 e PROPOSTO: LE CERTO 2133, NAO LE 114, LE ERRADO ZERO sobre 2247 celulas rotuladas — e o ULTIMO PISO SEGURO, com a propria linha na tabela de candidatos"
  - "A REPROVA de 2026-08-30 caiu por REMOCAO DA CAUSA e nao por mudanca de regra: as 14 celulas que sujavam o balde do piso compartilhado eram o glifo COLADO (windows #21), e a particao do 02-08 as fez ler CERTO"
  - "O tronco do `1` foi REMEDIDO no censo em 174, e nao nos 177 que a sondagem de 3 frames do plano afirmava — a folga (b) vale 13 e nao 16"
  - "Nao existe piso global, e agora com numero de censo: o mesmo 161 nas colunas de moeda faria 4697 celulas deixarem de ler e 1029 lerem OUTRA COISA"
  - "Um piso FIXO serve: a dispersao da MEDIANA do pico da Quantity entre as 8 gravacoes e 0,0 niveis de V"
  - "Oito testes que codificavam o DEFEITO foram reescritos contra a medicao, e nao 'consertados' — as linhas que ja liam mantem os MESMOS digitos"

patterns-established:
  - "Medicao que se recusa a propor: quatro causas de REPROVA, cada uma com mensagem propria, e a do piso compartilhado impressa em SEPARADO para o numero nao ser atribuido ao piso novo"
  - "Constante de teste com a variante ANTES ao lado da variante DEPOIS (`LINHAS_QUE_ATRAVESSAM_F005_ANTES_DO_PISO_PROPRIO`), para o ganho ficar legivel no proprio arquivo"
  - "Contagem DERIVADA da leitura em vez de gravada: `len(recusas) == 2 * len(descartadas)` sobrevive a proxima medicao; um `== 20` nao sobreviveria"

requirements-completed: [LEIT-02]

coverage:
  - id: D1
    description: "O piso de brilho proprio da coluna Quantity foi MEDIDO por varredura de passo 1 sobre as 8 gravacoes NOMEADAS do censo, com portao de layout ligado, e PROPOSTO em 161"
    requirement: "LEIT-02"
    verification:
      - kind: other
        ref: "tools/medir_brilho_da_quantidade.py --gravacoes recordings --calibracao calibration.json --gravar (exit 0, 30m24s, ultima linha PROPOSTO piso=161)"
        status: pass
      - kind: unit
        ref: "tests/test_medir_brilho_da_quantidade.py (34 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "O rotulo da medicao e NAO CIRCULAR — derivado de Total e Unit price, sem tocar um pixel da coluna Quantity"
    requirement: "LEIT-02"
    verification:
      - kind: unit
        ref: "tests/test_medir_brilho_da_quantidade.py::quantidade_derivada (os quatro casos da behavior)"
        status: pass
    human_judgment: false
  - id: D3
    description: "O piso chega a `ler_celula_de_quantidade` por parametro SEM valor de fabrica, e a chave entra por `.get` com `VERSAO_DO_ESQUEMA` em 2"
    requirement: "LEIT-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_leitura.py + tests/test_calibracao_mercado.py (inspect.signature, esquema 2)"
        status: pass
    human_judgment: false
  - id: D4
    description: "As colunas de MOEDA leem EXATAMENTE os mesmos digitos de antes, preso por valor sobre fixtura versionada"
    requirement: "LEIT-02"
    verification:
      - kind: integration
        ref: "tests/test_mercado_pagina.py::TestOPisoDeBrilhoDaQuantidadeChegaAProducao::test_as_colunas_de_MOEDA_leem_EXATAMENTE_os_mesmos_digitos"
        status: pass
    human_judgment: false
  - id: D5
    description: "RAMO PROPOSTO cobrado: sobre janela_tooltip_f012.png a coluna Quantity le ESTRITAMENTE MAIS linhas do que sob o piso compartilhado, e as que atravessam leem `1`"
    requirement: "LEIT-02"
    verification:
      - kind: integration
        ref: "tests/test_mercado_pagina.py::TestOPisoDeBrilhoDaQuantidadeChegaAProducao::test_o_rendimento_da_coluna_Quantity_cobra_o_ramo_CERTO"
        status: pass
    human_judgment: false
  - id: D6
    description: "O portao de digest do calibration.json — PRESENCA (13 moldes, 3 ancoras) e IDENTIDADE (md5) — confere identico antes e depois do --gravar"
    requirement: "LEIT-02"
    verification:
      - kind: other
        ref: "md5 templates f3fc93a0b961292d0e0bc562d02b43e9 e ancoras e1247779081b7d412783741761c8513a, iguais nas duas pontas"
        status: pass
    human_judgment: false
  - id: D7
    description: "O usuario ve na tela que as quantidades exibidas — inclusive as linhas de quantidade `1` — batem com o que o console mostra"
    requirement: "LEIT-02"
    verification: []
    human_judgment: true
    rationale: "Portao humano de fim de fase (human_verify_mode: end-of-phase). O pytest roda no Python global e injeta as duas leitoras de OCR; nenhuma fixtura alcanca a leitura ao vivo com Windows.Media.Ocr e o jogo aberto."

duration: 1h 8m
completed: 2026-08-31
status: complete
---

# Phase 02 Plan 07: O piso de brilho proprio da coluna Quantity Summary

**O `1` da coluna Quantity voltou a se ler: o piso de brilho PROPRIO da coluna foi MEDIDO em 161 por varredura de passo 1 sobre 2247 celulas rotuladas do censo, com o balde LE ERRADO VAZIO, e o rendimento saltou de 541 para 2133 leituras certas.**

## Performance

- **Duration:** 1h 8m (a varredura sozinha levou 30m24s)
- **Started:** 2026-08-30T23:35:00Z (retomada; as duas tasks ja tinham commitado antes da interrupcao)
- **Completed:** 2026-08-31T00:43:00Z
- **Tasks:** 2 de 2 (as duas ja commitadas; esta sessao rodou a varredura, registrou o veredito e fechou)
- **Files modified:** 2 nesta sessao (10 na onda inteira)

## Accomplishments

- **O veredito virou: REPROVADO -> PROPOSTO**, e virou por REMOCAO DA CAUSA. A rodada anterior reprovou pela quarta causa (o piso compartilhado ja errava em 14 celulas). O 02-08 consertou a segmentacao do glifo COLADO, e o balde LE ERRADO do piso 180 esta agora VAZIO.
- **`mercado_limiar_de_brilho_da_quantidade` = 161** gravado no `calibration.json` da maquina, por load-mutate-save, com os 13 moldes e as 3 ancoras intactos por md5.
- **O rendimento da coluna Quantity foi de 541 para 2133** de 2247 celulas rotuladas. As tres gravacoes que liam ZERO passam a ler.
- **As colunas de moeda nao se mexeram um digito**, preso por valor sobre fixtura versionada.
- **Oito testes que codificavam o DEFEITO** foram reescritos contra a medicao.

## O VEREDITO

```
PROPOSTO piso=161, folga ate o primeiro que erra=1, folga ate o tronco medido do `1`=13
(tronco=174), balde LE ERRADO do proprio piso VAZIO sobre 2247 celulas rotuladas
```

| | |
|---|---|
| piso proposto | **161** — o ULTIMO PISO SEGURO, com `PASSO_DA_VARREDURA = 1` |
| **folga (a)** ate o primeiro piso que ERRA | **1** (vale 1 por construcao com passo 1; diz so quao no limite a escolha esta) |
| **folga (b)** ate o TRONCO MEDIDO do `1` | **13** (tronco remedido no censo = **174**) — **e ela que dimensiona a confianca**, e ela e POSITIVA e folgada: o piso captura o `1` com 13 niveis de V de margem |
| balde LE ERRADO do proprio 161 | **VAZIO** (0 de 2247) |
| celulas de grade varridas | 3458 |
| celulas ROTULADAS | 2247 |
| relogio da varredura | **30m24s** (00:06:59Z -> 00:37:23Z) |

**As duas populacoes que definiram o piso:** de um lado os pisos 180..161, todos com o balde LE
ERRADO vazio (a REGIAO SEGURA, contigua a partir do compartilhado); do outro o piso 160, o
primeiro a acrescentar erro NOVO (2 celulas). Nao ha piso seguro ABAIXO do primeiro que erra —
o conjunto seguro e contiguo, e a quarta causa de reprova (descontinuidade / vao invertido) nao
disparou.

## RELATORIO 1 — o pico de V por coluna, e o tronco do `1`

| coluna | n | min | p5 | mediana | p95 | max |
|---|---|---|---|---|---|---|
| quantidade | 3458 | 53 | 66 | **215** | 219 | 255 |
| total | 3458 | 53 | 66 | **230** | 255 | 255 |
| unitario | 3458 | 53 | 66 | **230** | 255 | 255 |

**O TRONCO DO `1`** (linha do meio do glifo, so o traco vertical), n=1588:
min **174**, p5 174, mediana 174, p95 177, max 178.

**A dispersao da MEDIANA do pico da Quantity entre as 8 gravacoes: 0,0 niveis de V.** Todas as
oito dao mediana 215,0. **Um piso FIXO serve** — a pergunta 2 do plano esta respondida no censo,
e a resposta e a mesma que a sondagem dava: a diferenca de brilho e propriedade do desenho da UI
e da geometria da fonte, nao do conteudo do frame.

O residuo dos 2247 rotulos aceitos contra o limite derivado do arredondamento: **2133 de 2247
(94,9%)** cabem. O que nao cabe e a assinatura do TRUNCAMENTO.

## RELATORIO 2 — todos os pisos candidatos, com os tres baldes

`PASSO_DA_VARREDURA = 1`, faixa 180 ate 145, **36 niveis de V, uma linha por nivel, sem saltos**.
2247 celulas rotuladas.

| piso | LE CERTO | NAO LE | LE ERRADO | veredito |
|---|---|---|---|---|
| **180** | 541 | 1706 | **0** | seguro (PISO COMPARTILHADO, o comportamento de HOJE) |
| 179–178 | 541 | 1706 | 0 | seguro |
| 177 | 549 | 1698 | 0 | seguro |
| 176–174 | 1323 | 924 | 0 | seguro |
| 173–162 | 2133 | 114 | 0 | seguro |
| **161** | **2133** | **114** | **0** | seguro **<== ESCOLHIDO** |
| 160–158 | 2131 | 114 | **2** | ERRA |
| 157 | 2094 | 119 | **34** | ERRA |
| 156 | 2094 | 150 | 3 | ERRA |
| 155 | 2094 | 119 | 34 | ERRA |
| 154–153 | 2094 | 120 | 33 | ERRA |
| 152 | 2094 | 150 | 3 | ERRA |
| 151 | 1985 | 164 | **98** | ERRA |
| 150–149 | 1985 | 157 | **105** | ERRA |
| 148 | 1985 | 158 | 104 | ERRA |
| 147 | 1985 | 163 | 99 | ERRA |
| 146 | 1985 | 243 | 19 | ERRA |
| 145 | 1984 | 250 | 13 | ERRA |

**O BALDE DO PISO COMPARTILHADO, EM SEPARADO:** LE CERTO 541, NAO LE 1706, **LE ERRADO 0**.
Esta linha e a que mudou tudo — em 2026-08-30 ela dizia **LE ERRADO 14**, e era essa a causa da
REPROVA.

O piso 161 tem a **PROPRIA linha** na tabela, com os proprios tres baldes preenchidos e o balde
LE ERRADO vazio. Ele foi MEDIDO, nao interpolado.

## RELATORIO 3 — o custo de um piso GLOBAL na coluna de moeda

**Nao existe piso global, e agora o numero e do censo:**

| piso aplicado as colunas de moeda | deixaram de ler | passaram a ler OUTRA COISA |
|---|---|---|
| 180 (compartilhado) | 0 | 0 (zero por construcao — a conferencia da conta) |
| 175 | 426 | 284 |
| 170 | 3281 | 212 |
| 165 | 4441 | 356 |
| **161 (o proposto para a Quantity)** | **4697** | **1029** |
| 160 | 5600 | 126 |
| 155 | 5759 | 17 |
| 150 | 5870 | 4 |

Exemplo medido em `053105-mercado-aberto/frame_000039.png`: no piso 175 a L0 total `500,00` vira
**`588,88`** — numero plausivel e ERRADO. E o mecanismo que o plano previu (a palavra de sufixo,
que vive entre V=120 e V=173, entrando na celula) e a razao de as duas colunas pedirem faixas
DISJUNTAS.

### O rendimento da coluna Quantity, por gravacao (antes -> depois)

| gravacao | antes | depois | de rotuladas |
|---|---|---|---|
| 053105-mercado-aberto | 366 | **788** | 807 |
| 055323-mercado-scroll | 85 | **229** | 269 |
| 060622-mercado-pagina-cheia | 34 | **143** | 143 |
| 061253-mercado-tooltip | **0** | **199** | 241 |
| 061409-mercado-alvo-sobreposto | **0** | **215** | 224 |
| 063240-mercado-farm-com-party | **0** | **327** | 329 |
| 063409-mercado-scroll-transicao | 56 | **82** | 82 |
| 063752-mercado-aberto | **0** | **150** | 152 |
| **TOTAL** | **541** | **2133** | **2247** |

As **tres gravacoes que liam ZERO** — tooltip, alvo-sobreposto e farm-com-party — passam a ler.
Era exatamente a refutacao 4 do tracer, e ela esta fechada por medicao.

### A taxa de leitura por DIGITO do rotulo (antes -> depois)

| rotulo | n | antes | depois |
|---|---|---|---|
| **1** | **1680** | **0** | **1590** |
| 2 | 53 | 49 | 49 |
| 3 | 45 | 40 | 40 |
| 4 | 21 | 21 | 21 |
| 5 | 142 | 139 | 139 |
| 6 | 6 | 5 | 5 |
| 8 | 7 | 5 | 5 |
| 10 | 51 | 47 | 47 |
| **11** | 2 | **0** | **2** |
| 14 | 54 | 54 | 54 |
| 44 | 14 | 14 | 14 |
| 50 | 55 | 55 | 55 |
| (os demais 19 rotulos) | — | inalterados | inalterados |

**A pergunta 3 do plano esta respondida no censo:** so o `1` (e o `11`, que e feito de dois `1`)
morria. **Nenhum outro rotulo perdeu leitura** — a coluna "depois" nunca e menor que a "antes".
O ganho e inteiro e o custo e zero dentro da coluna.

## O PORTAO DE DIGEST DO `calibration.json`

Conferido em DUAS partes, nas DUAS pontas, porque **igualdade nao e presenca** — a janela #13
(a calibracao de party apagando a de mercado) esta ABERTA e ja custou os 13 moldes ao usuario.

| conferencia | ANTES do `--gravar` | DEPOIS do `--gravar` |
|---|---|---|
| PRESENCA `len(mercado_templates_de_digito)` | **13** | **13** |
| PRESENCA `len(mercado_ancoras)` | **3** | **3** |
| IDENTIDADE md5 dos 13 moldes | `f3fc93a0b961292d0e0bc562d02b43e9` | `f3fc93a0b961292d0e0bc562d02b43e9` |
| IDENTIDADE md5 das 3 ancoras | `e1247779081b7d412783741761c8513a` | `e1247779081b7d412783741761c8513a` |

As quatro conferencias passaram. `versao` segue em **2**. A unica chave mutada foi
`mercado_limiar_de_brilho_da_quantidade`: **180 -> 161**.

`git status --short | grep -c calibration.json` devolve **0**, e `git log --name-only` dos
commits desta onda nao o menciona: **0 ocorrencias**. Uma copia de seguranca ficou em
`calibration.antes-do-02-07-remedicao.bak`, tambem fora do git.

## O que a MEDICAO CONTRADISSE

O plano avisava que onde a medicao em escala contradissesse a sondagem de 3 frames, a medicao
manda. Contradisse em tres pontos, e os tres ficam registrados com o numero:

1. **O tronco do `1` nao esta em 177 — esta em 174.** A sondagem media um glifo em um frame; o
   censo mediu 1588 troncos e o MAIS ESCURO e 174 (p5 174, mediana 174, p95 177, max 178). A
   consequencia e direta: a folga (b) do piso 161 vale **13** e nao os 16 que 177 daria. O
   numero e menor, e por isso ele e o que vale.
2. **A previsao de rendimento da janela #25 errou para menos.** Ela previa `463 -> 2045 em
   2170`; o medido foi **`541 -> 2133 em 2247`**. A previsao foi feita com a classificacao
   ANTERIOR a particao do 02-08, e a particao mudou tanto o denominador (mais celulas ganham
   rotulo derivado) quanto o numerador. A direcao estava certa; a magnitude nao.
3. **O piso 175 nao e neutro para a coluna de moeda.** A sondagem do plano so mostrava quebra a
   partir de 170 (`18,90` -> `18,907`). O censo mostra que ja em **175** ha 426 celulas que
   deixam de ler e 284 que leem OUTRA COISA (`500,00` -> `588,88`). A faixa segura da coluna de
   moeda e mais estreita do que a sondagem sugeria, o que REFORCA a conclusao de faixas
   disjuntas.

O que a medicao **CONFIRMOU**: a dispersao nula do pico entre gravacoes (piso fixo serve), a
existencia do teto (abaixo de 161 a leitura passa a falhar ABERTA, com 2 erros em 160 e 105 em
150-149), e a hipotese que motivou esta re-rodada — o balde LE ERRADO do piso compartilhado
esvaziou depois do 02-08.

## Task Commits

1. **Task 1: a varredura que MEDE o piso** — `e0e0083` (test, RED) + `d8c4711` (feat, GREEN)
2. **Task 2: o piso chega a producao por parametro obrigatorio** — `d3fb336` (test, RED) + `e513219` (feat, GREEN)
3. **A MEDICAO em si, e os testes reescritos contra ela** — `61a339d` (feat)

**Plan metadata:** ver commit `docs(02-07)` desta sessao.

_Os quatro primeiros commits sao de sessoes anteriores; esta sessao retomou apos a interrupcao
por limite de sessao no meio da varredura._

## Files Created/Modified

- `tools/medir_brilho_da_quantidade.py` — a varredura (1274 linhas), com os tres relatorios, as quatro causas de reprova e o `--gravar` por load-mutate-save
- `tests/test_medir_brilho_da_quantidade.py` — 34 testes sobre fixturas versionadas
- `l2scanner/mercado_leitura.py` — `mascara_de_numero`, `segmentar_glifos_no_brilho`, e o `valor_minimo` obrigatorio nas tres leitoras e em `ler_linha`
- `l2scanner/calibracao.py` — o campo novo, lido por `.get`, com faixa `[1, 254]` conferida no arranque
- `l2scanner/mercado_pagina.py` — a decima chave no portao por AUSENCIA
- `tests/fixtures/mercado/calibracao_de_fixture.json` — `161` copiado VERBATIM da producao
- `tests/test_mercado_leitura.py` — as constantes e oito testes reescritos contra a medicao

## Decisions Made

Ver `key-decisions` no frontmatter. O que merece repeticao: **o ramo nao foi escolhido pelo
executor.** O teste `test_o_rendimento_da_coluna_Quantity_cobra_o_ramo_CERTO` compara o valor
gravado com o piso compartilhado e DERIVA se cobra desigualdade (PROPOSTO) ou igualdade
(REPROVADO). Como 161 != 180, ele cobrou desigualdade estrita — e passou.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Oito testes cobravam contagens que codificavam o DEFEITO**

- **Found during:** a re-rodada da varredura (fechamento da Task 2)
- **Issue:** `tests/test_mercado_leitura.py` fixava, em constante e em assert, o conjunto de
  linhas que atravessavam SOB O DEFEITO — 2 linhas em `f010`, 4 em `f005`, zero na tooltip. Com o
  piso medido em 161, as linhas de quantidade `1` passam a atravessar e as oito afirmacoes viram
  falsas. Nao e regressao: e o ganho que o plano existe para produzir.
- **Fix:** as constantes passaram a carregar o conjunto MEDIDO, com a variante
  `*_ANTES_DO_PISO_PROPRIO` preservada ao lado para o ganho ficar legivel no proprio arquivo.
  Cinco testes foram reescritos para afirmar a INVARIANTE em vez da contagem: a soma
  `descartadas + linhas` continua sendo `linhas_por_pagina`; as descobertas da tooltip nao
  aparecem entre as descartadas e leem `1`; a pagina aceita contem exatamente as descobertas e
  nenhuma coberta; o log de recusa e `2 * len(descartadas)` e nao um `20` gravado.
- **Verificacao de que o ganho e CERTO e nao apenas MAIOR:** as linhas que ja atravessavam
  mantem os MESMOS digitos (`f005` 1/3/5/6 = 3666,3 / 1500,3 / 1139,6 / 500,2 e `f010` 6/8 =
  1890,2 / 1800,3), e as linhas NOVAS tem todas `residuo_do_cruzamento = 0` — o cruzamento
  `Total / Unit price`, que nao toca a coluna Quantity, concorda com o `1` lido.
- **Files modified:** `tests/test_mercado_leitura.py`
- **Committed in:** `61a339d`

**2. [Rule 2 - Missing critical] A calibracao de fixtura ainda carregava o piso REPROVADO**

- **Found during:** o fechamento da Task 2
- **Issue:** `tests/fixtures/mercado/calibracao_de_fixture.json` tinha `180`, gravado quando a
  medicao anterior REPROVOU. Deixado assim, o teste que DERIVA o ramo cobraria o criterio de
  IGUALDADE sobre um produto que agora usa 161 — teste e producao mediriam coisas diferentes.
- **Fix:** `161` copiado VERBATIM da producao, como as outras chaves `mercado_*`.
- **Files modified:** `tests/fixtures/mercado/calibracao_de_fixture.json`
- **Committed in:** `61a339d`

---

**Total deviations:** 2 auto-fixed (1x Rule 1, 1x Rule 2).
**Impact on plan:** nenhum desvio de escopo. As duas correcoes sao consequencia direta do
veredito PROPOSTO, previsto pelo proprio plano no ramo correspondente.

## Issues Encountered

**A varredura passa de 10 minutos e ja matou um executor.** Ela levou **30m24s** nesta rodada.
Foi lancada em segundo plano no inicio da sessao e o resultado foi commitado assim que voltou,
sem trabalho acumulado depois dela. Se ela precisar rodar de novo, rode-a primeiro.

**Duas falhas PRE-EXISTENTES e FORA DO ESCOPO na suite completa:**
`tests/test_bosses.py::TestOConfigDoRepositorioProduzOAviso::test_o_arquivo_do_repositorio_tem_os_dois_tiat_com_6_e_8`
e `...TestOEsquemaDoBlocoBossEstaCompletoParaAFase2::test_os_dois_tiat_do_repositorio_tem_6_e_8`.
Sao do workstream **tiat**, nao do mercado: o commit `c4175da` mudou o `config.toml` para "Tiat
8h + 2 random (o servidor mudou a regra)" e os dois testes seguem cobrando 6 e 8. Nenhum arquivo
desta onda os toca. Registradas em `.planning/WINDOWS.md` como janela **#27**, ABERTA, e NAO
consertadas aqui — a fronteira de escopo do executor proibe.

**E a origem foi rastreada, e ela e desconfortavel:** o commit RED desta propria onda,
`e0e0083`, carregou junto **quatro arquivos do workstream tiat** que nao pertencem ao 02-07 —
`l2scanner/bosses.py`, `tests/test_bosses.py`, `tests/test_presenca.py` e um `01-03-SUMMARY.md`
do tiat. Foi um executor concorrente com arquivos ja no index. **Nada foi desfeito:** reverter
arrastaria trabalho legitimo do tiat, e o commit `c4175da` (posterior, o que mudou a regra do
Tiat para 8h+2) ja construiu por cima. Registrado como janela **#28**, para que a regra da casa
— *`git add` por arquivo, nunca `git add -A`* — passe a ter um caso concreto atras dela.

**O flake conhecido do `test_agenda.py`:** a linha 1141 levanta `KeyboardInterrupt` de proposito
e derrubou a primeira sessao em 87 passed. Rodado de novo com `-p no:randomly`: **144 passed**.
Abortar nao e falhar.

## Verificacao

| # | verificacao | resultado |
|---|---|---|
| 1 | `pytest tests/test_medir_brilho_da_quantidade.py tests/test_mercado_leitura.py tests/test_mercado_pagina.py` | **verde** |
| 2 | os cinco detectores de regressao (`glifos`, `calibrar_mercado`, `calibracao_mercado`, `medir_leitura_de_glifo`, `medir_agrupamento_de_nome`) | **508 passed** (com `medir_largura_de_run` e `medir_brilho_da_quantidade` juntos) |
| 3 | o detector de morte intocado — `test_mercado_27x.py` + `test_visao.py`, e `rastreador.py`/`visao.py` fora do diff | **96 passed**, os dois arquivos AUSENTES do diff da onda |
| 4 | o firewall de escopo — `test_firewall_escopo.py` | **verde**, `rapidfuzz` continua fora |
| 5 | a suite completa, Python GLOBAL | **2501 passed, 2 skipped, 2 failed** (as duas de `test_bosses.py`, pre-existentes e fora do escopo) sem `test_agenda.py`; **144 passed** so com ele |
| 6a | gate de producao de dado: a varredura com caminhos absolutos | **exit 0**, 30m24s, tres relatorios, 8 gravacoes com contagem de PNG, 8 pastas ignoradas com motivo |
| 6b | gate: diretorio com UMA pasta so | **exit 3**, nomeando as **7** que faltam |
| 6c | gate: digest md5 antes e depois do `--gravar` | **identico nas duas pontas**, presenca 13/3 nas duas |
| 7 | `calibration.json` fora do git | `git status --short \| grep -c` = **0**; `git log --name-only` da onda = **0** |
| 8 | portao humano de fim de fase | **PENDENTE** — windows #19, com o jogo aberto |

## `.planning/WINDOWS.md`

| janela | antes | agora |
|---|---|---|
| **#16** — o digito `1` da Quantity nao se le | ABERTA | **FIXED** — fechada por medicao, piso 161 |
| **#22** — o 02-07 MEDIU e REPROVOU | ABERTA | **FIXED** — a reprova foi superada pela re-rodada |
| **#25** — a causa da reprova esta REMOVIDA, re-rodar | ABERTA | **FIXED** — re-rodada feita, hipotese confirmada |
| **#26** (nova) — o registro do fechamento com os numeros | — | **FIXED** (registro, nao defeito) |
| **#27** (nova) — as 2 falhas de `test_bosses.py` do tiat | — | **ABERTA**, fora do escopo |

## Next Phase Readiness

**O 02-05 esta desbloqueado e agora mede o que deve medir.** Ele e o replay que afirma a fase, e
a razao de ele depender desta onda esta cumprida: se tivesse rodado antes, teria medido um
rendimento ARTEFATO — um conjunto de linhas do qual o caso mais comum do mercado (quantidade
`1`, 1680 das 2247 celulas rotuladas, **75%**) estava sistematicamente excluido. Agora 1590
dessas 1680 leem.

**O que segue aberto para a Fase 3:** as 114 celulas que ainda nao leem no piso 161 (5,1% das
rotuladas) continuam falhando FECHADAS — nada errado e gravado. E o portao humano de fim de fase
(windows #19) segue pendente: nenhuma fixtura alcanca a leitura ao vivo com `Windows.Media.Ocr`.

---
*Phase: 02-leitura-de-p-gina*
*Completed: 2026-08-31*

## Self-Check: PASSED

- `tools/medir_brilho_da_quantidade.py` — FOUND
- `tests/test_medir_brilho_da_quantidade.py` — FOUND
- `.planning/workstreams/mercado/phases/02-leitura-de-p-gina/02-07-SUMMARY.md` — FOUND
- commits `e0e0083`, `d8c4711`, `d3fb336`, `e513219`, `61a339d`, `2aeb2bf`, `2cf27f2` — todos FOUND
- `calibration.json` fora do git: `git status --short | grep -c` = 0, e ZERO ocorrencias em
  `git log --name-only` de toda a onda
