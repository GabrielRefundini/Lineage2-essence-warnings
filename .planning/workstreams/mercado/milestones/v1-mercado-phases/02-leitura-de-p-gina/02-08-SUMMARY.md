---
phase: 02-leitura-de-p-gina
plan: 08
subsystem: leitura-de-mercado
tags: [opencv, segmentacao, programacao-dinamica, calibracao, medicao, LEIT-02]

requires:
  - phase: 02-04
    provides: "o tracer `ler_linha` -> `LeitorDePagina`, o portao de layout e as fixturas de janela"
  - phase: 02-06
    provides: "a terceira coluna (`Unit price`), `limite_derivado_do_cruzamento` e a aritmetica do arredondamento"
  - phase: 02-07
    provides: "`quantidade_derivada` (o rotulo nao circular), a disciplina dos tres baldes, o load-mutate-save e `ler_celula(valor_minimo=)` sem valor de fabrica"
provides:
  - "`tools/medir_largura_de_run.py`: a varredura que mede o vale, o custo da guarda por celula/linha/pagina, a folga de cola nos tres baldes contra DOIS rotulos nao circulares, e o relogio da particao dentro do tick"
  - "`larguras_de_molde`, `limite_de_glifo_unico`, `larguras_com_folga` e `particionar_run` em `l2scanner/mercado_leitura.py` — a geometria do glifo DERIVADA dos moldes"
  - "a GUARDA e a PARTICAO dentro de `ler_glifos`: um run mais largo que o maior molde nunca mais vira UM digito"
  - "`mercado_folga_de_cola_do_glifo` = 1, MEDIDA, no `calibration.json` da maquina do usuario"
  - "tres fixturas versionadas de glifo COLADO, com proveniencia declarada e presas por VALOR"
affects: [02-05, 02-07, fase-3-persistencia]

actuals:
  tokens: 36563
  tasks: 2
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Geometria DERIVADA em vez de gravada: o limite de glifo unico e `max(largura)` sobre os moldes, e nao uma chave — uma copia criaria duas verdades sobre uma so geometria"
    - "Rotulo de INTERVALO como inversa do rotulo derivado: `total_no_intervalo` rejeita um total inventado sem fixar o certo, e so existe quando as OUTRAS duas colunas leem LIMPO"
    - "Programacao dinamica com poda por piso e margem, escolhendo pelo PIOR segmento do corte — o elo mais fraco decide, porque a celula e tudo-ou-nada"
    - "Censo lido UMA VEZ e reclassificado em memoria: a segmentacao nao depende do parametro varrido, so a particao depende"
    - "Portao por AUSENCIA que degrada para MAIS SEGURO, e por isso NAO entra em `_calibrado`"

key-files:
  created:
    - tools/medir_largura_de_run.py
    - tests/test_medir_largura_de_run.py
    - tests/fixtures/mercado/glifos_colados_quantidade_f078.png
    - tests/fixtures/mercado/glifos_colados_total_f105.png
    - tests/fixtures/mercado/glifos_colados_total_f054.png
  modified:
    - l2scanner/mercado_leitura.py
    - l2scanner/calibracao.py
    - l2scanner/mercado_pagina.py
    - tools/medir_brilho_da_quantidade.py
    - tests/test_mercado_leitura.py
    - tests/test_mercado_pagina.py
    - tests/test_calibracao_mercado.py
    - tests/test_medir_leitura_de_glifo.py
    - tests/fixtures/mercado/calibracao_de_fixture.json

key-decisions:
  - "A folga de cola foi MEDIDA em 1 e PROPOSTA: 82 LE CERTO, 42 NAO LE, ZERO LE ERRADO sobre 124 celulas com run largo e rotulo"
  - "O limite de glifo unico NAO virou chave do calibration.json — ele e derivado dos moldes, e o vale medido (7 a 10 px, ZERO celulas aceitas) mostra que a escolha dentro dele nao muda nada"
  - "A guarda e o ramo de FALLBACK e nao o produto: a ausencia da chave liga a guarda, com aviso alto e sem `raise`, e por isso ela nao entra em `_calibrado`"
  - "Empate de LE CERTO escolhe a MENOR folga: entre duas que rendem o mesmo, a menor amplia menos o espaco de cortes possiveis"
  - "A DP escolhe pelo PIOR segmento do corte, e foi isso que a fez preferir `7+4` a `6+5` sem consultar rotulo nenhum"

patterns-established:
  - "Toda largura de run e `fim - inicio` (convencao SEMI-ABERTA), presa por teste contra `glifos_unitario_f010.png`"
  - "Um numero livre vai para o calibration.json; um numero derivado nunca vai"
  - "Uma proposta so sai com o balde LE ERRADO VAZIO, e a folga proposta tem a PROPRIA linha na tabela"

requirements-completed: [LEIT-02]

coverage:
  - id: D1
    description: "A varredura mede o VALE: das celulas que a producao aceita hoje nas tres colunas, ZERO tem run entre o limite derivado (6) e o menor run largo observado (11)"
    requirement: "LEIT-02"
    verification:
      - kind: integration
        ref: "tools/medir_largura_de_run.py --gravacoes recordings --calibracao calibration.json (RELATORIO 1)"
        status: pass
      - kind: unit
        ref: "tests/test_medir_largura_de_run.py#TestAsLargurasDosMoldes"
        status: pass
    human_judgment: false
  - id: D2
    description: "A folga de cola foi medida e proposta em 1, com o balde LE ERRADO VAZIO nas DUAS populacoes rotuladas (Quantity pelo rotulo derivado, colunas de moeda pelo rotulo de intervalo)"
    requirement: "LEIT-02"
    verification:
      - kind: integration
        ref: "tools/medir_largura_de_run.py (RELATORIO 3, tres baldes separados por populacao)"
        status: pass
      - kind: unit
        ref: "tests/test_medir_largura_de_run.py#TestAPropostaDaFolga"
        status: pass
    human_judgment: false
  - id: D3
    description: "Um run mais largo que o maior molde nunca mais vira UM digito: ou se parte em glifos que todos passam no piso e na margem, ou a celula cai FECHADA"
    requirement: "LEIT-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_leitura.py#TestOsGlifosCOLADOS"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_leitura.py#TestAParticaoDeUmRun"
        status: pass
      - kind: integration
        ref: "tools/medir_largura_de_run.py — 69 leituras ERRADAS hoje viram ZERO com a folga gravada"
        status: pass
    human_judgment: false
  - id: D4
    description: "As celulas que hoje leem sem run largo leem EXATAMENTE o mesmo, preso por valor sobre as fixturas de controle versionadas"
    requirement: "LEIT-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_leitura.py#TestAsCelulasESTREITASNaoMudamUmPixel"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_pagina.py#TestAFolgaDeColaChegaAProducaoPeloPORTAO_POR_AUSENCIA::test_as_colunas_de_MOEDA_leem_o_MESMO_com_e_sem_a_chave"
        status: pass
    human_judgment: false
  - id: D5
    description: "Os dois parametros novos chegam sem valor de fabrica pelos seis pontos da cadeia, e as assinaturas de segmentacao ficam intactas"
    requirement: "LEIT-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_leitura.py#TestOsDoisParametrosNovosNaoTemValorDeFabrica"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_leitura.py#TestAsAssinaturasDeSegmentacaoEstaoINTACTAS"
        status: pass
    human_judgment: false
  - id: D6
    description: "A chave e opcional em calibracao.py, com faixa conferida no arranque, e a AUSENCIA liga a guarda sem derrubar a leitura de pagina"
    requirement: "LEIT-02"
    verification:
      - kind: unit
        ref: "tests/test_calibracao_mercado.py#TestAFolgaDeColaDoGlifoEConferidaNoARRANQUE"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_pagina.py#TestAFolgaDeColaChegaAProducaoPeloPORTAO_POR_AUSENCIA"
        status: pass
    human_judgment: false
  - id: D7
    description: "O custo da particao cabe no tick de 1 Hz: 9,0 ms medio e 60,2 ms no pior caso do censo, contra o teto de 200 ms"
    verification:
      - kind: integration
        ref: "tools/medir_largura_de_run.py (RELATORIO 4)"
        status: pass
    human_judgment: true
    rationale: "O numero medido PASSA no teto declarado, mas ele e 17x abaixo do tick e nao as tres ordens de grandeza que o plano afirmava. A folga real e menor do que o plano supunha, e um humano precisa decidir se 17x basta antes de a particao ganhar mais largura."

duration: 95 min
completed: 2026-08-30
status: complete
---

# Phase 02 Plan 08: A guarda e a particao do glifo colado — Summary

**Um run mais largo que o maior molde deixou de virar UM digito: a particao por programacao dinamica dentro de `ler_glifos`, com a folga de cola MEDIDA em 1, zerou as 69 leituras erradas e plausiveis do censo e ainda subiu o rendimento de 1.135 para 1.148 linhas completas.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 2 de 2
- **Files modified:** 14 (5 criados, 9 modificados)
- **Commits:** 5 (2 pares TDD + 1 de ledger)

## Accomplishments

- **A falha ABERTA fechou.** Era o unico defeito conhecido da Fase 2 que produzia numero errado e PLAUSIVEL em vez de descartar a linha: `44` lia `4`, `149,44` lia `14,44`, e a gramatica aceitava os dois. Medido no censo, 69 das 124 celulas com run largo e rotulo liam errado; agora sao ZERO.
- **A ferramenta mediu, e nao supos.** `tools/medir_largura_de_run.py` varre as 8 gravacoes NOMEADAS do censo — 347 paginas, 3.458 linhas, 10.374 celulas, portao de layout LIGADO — numa passagem UNICA pelos PNGs, e emite quatro relatorios com `PROPOSTO` ou `REPROVADO` na ultima linha.
- **O VALE existe e esta VAZIO**, o que torna o limite derivado bem posto: das celulas que a producao ACEITA hoje, ZERO tem run de 7, 8, 9 ou 10 px. As larguras aceitas sao {4, 5, 6} de um lado e {11, 12} do outro.
- **O rendimento SUBIU.** A guarda pura custaria 69 linhas (−6,08%); a particao devolve essas e mais 13: 1.135 → **1.148** linhas completas, 155 → **156** paginas.
- **A causa da REPROVA do 02-07 saiu**, sem re-rodar a varredura de 10 minutos daquele plano.

## Task Commits

1. **Task 1 (tracer, TDD) — a varredura**
   - `32d4db0` (test) — as tres fixturas coladas + a convencao semi-aberta + a DP + a proposta, afirmadas antes de existir (35 testes, RED por `FileNotFoundError`)
   - `303feed` (feat) — `tools/medir_largura_de_run.py` e os quatro relatorios
2. **Task 2 (auto, TDD) — a guarda e a particao em producao**
   - `8795b99` (test) — os dois parametros sem valor de fabrica, as assinaturas intactas, as celulas estreitas por valor, as coladas por valor, a chave opcional e o portao por ausencia (RED por `ImportError`)
   - `31cd0ba` (feat) — a promocao das primitivas, `particionar_run`, a cadeia inteira e a chave nova
3. **Ledger** — `1b8d8fc` (docs) — `#21` marcada FIXED, duas entradas novas

## Os numeros medidos

### RELATORIO 1 — o vale (largura MAXIMA por celula ACEITA)

| coluna | 4 | 5 | 6 | **7..10** | 11 | 12 |
|---|---|---|---|---|---|---|
| total | 2.011 | 66 | 754 | **0** | 65 | 10 |
| quantidade | 1.053 | 107 | 42 | **0** | 0 | 14 |
| unitario | 2.115 | 64 | 779 | **0** | 11 | 8 |

O vale vai de 7 a 10 (quatro niveis) e tem **0 celulas aceitas**. O portao passou e a Task 2 comecou.

### RELATORIO 2 — o custo da GUARDA pura

| | hoje | com a guarda | delta |
|---|---|---|---|
| celulas de total aceitas | 2.906 | 2.831 | −75 (−2,58%) |
| celulas de quantidade aceitas | 1.216 | 1.202 | −14 (−1,15%) |
| celulas de unitario aceitas | 2.977 | 2.958 | −19 (−0,64%) |
| **linhas com as 3 colunas aceitas** | **1.135** | **1.066** | **−69 (−6,08%)** |
| paginas com >= 1 linha | 155 | 155 | **0** |
| paginas com ZERO linha | — | **0** | — |

Os textos que a guarda descarta, agrupados: `total '14,44'` x65, `quantidade '4'` x14, `unitario '14,44'` x11, `total '4,00'` x9, `unitario '4,00'` x8, `total '4,70'` x1.

### RELATORIO 3 — a folga de cola, tres baldes, DOIS rotulos

Populacao rotulada: **124** celulas com run largo (de 524 com run largo) — 59 de `total` e 11 de `unitario` pelo rotulo de INTERVALO, 54 de `quantidade` pelo rotulo DERIVADO.

**As tres causas, EM SEPARADO:**

| regime | LE CERTO | NAO LE | **LE ERRADO** |
|---|---|---|---|
| HOJE (sem guarda, sem particao) | 0 | 55 | **69** |
| GUARDA PURA | 0 | 124 | **0** |
| FOLGA 0 (larguras de molde) | 28 | 96 | **0** |

**A tabela de candidatas (passo 1, sem saltos):**

| folga | larguras permitidas | CERTO | NAO LE | ERRADO | mudaram |
|---|---|---|---|---|---|
| 0 | (1, 4, 6) | 28 | 96 | 0 | — |
| **1** | **(1, 2, 4, 5, 6, 7)** | **82** | **42** | **0** | **76** |
| 2 | (1, 2, 3, 4, 5, 6, 7, 8) | 82 | 42 | 0 | 0 |
| 3 | (1, ..., 9) | 82 | 42 | 0 | 0 |
| 4 | (1, ..., 10) | 82 | 42 | 0 | 0 |

**Os tres baldes da folga escolhida, separados por populacao:**

| coluna | rotulo | LE CERTO | NAO LE | **LE ERRADO** |
|---|---|---|---|---|
| total | intervalo | 58 | 1 | **0** |
| quantidade | derivado | 14 | 40 | **0** |
| unitario | intervalo | 10 | 1 | **0** |

**Veredito:** `PROPOSTO mercado_folga_de_cola_do_glifo = 1`

### RELATORIO 4 — o relogio dentro do tick

- linhas com run largo: **362 de 3.458 (10,5%)**
- custo MEDIO por linha larga: **9,02 ms**
- custo do PIOR caso: **60,16 ms** (teto declarado: 200 ms)
- folga contra o tick de 1 Hz: **17x**

### O relogio da FERRAMENTA, nas duas metades

- passagem UNICA pelo censo: **43,8 s**
- reclassificacao das 5 folgas: **17,4 s** (3,5 s por folga)
- **TOTAL: 64,4 s** — teto 300 s

O censo e aberto UMA VEZ. A varredura irma do 02-07 varre o censo por piso candidato e passa de 10 minutos; aqui a segmentacao nao depende da folga, so a particao depende.

## O portao do `calibration.json` — PRESENCA e IDENTIDADE, nas duas pontas

| conferencia | antes | depois |
|---|---|---|
| presenca — `len(mercado_templates_de_digito)` | **13** | **13** |
| presenca — `len(mercado_ancoras)` | **3** | **3** |
| identidade — md5 dos 13 moldes | `f3fc93a0b961292d0e0bc562d02b43e9` | `f3fc93a0b961292d0e0bc562d02b43e9` |
| identidade — md5 das 3 ancoras | `e1247779081b7d412783741761c8513a` | `e1247779081b7d412783741761c8513a` |

`git status --short` **nao lista** `calibration.json` — ele e gitignored e nao foi commitado. `VERSAO_DO_ESQUEMA` segue em **2**. A unica chave mutada foi `mercado_folga_de_cola_do_glifo`, por load-mutate-save com `NamedTemporaryFile` + `os.replace`.

## Files Created/Modified

- `tools/medir_largura_de_run.py` — a varredura, os quatro relatorios, a proposta e a gravacao
- `tests/test_medir_largura_de_run.py` — 35 testes sobre fixturas versionadas e populacoes construidas
- `tests/fixtures/mercado/glifos_colados_{quantidade_f078,total_f105,total_f054}.png` — os tres casos, com proveniencia declarada no cabecalho do teste
- `l2scanner/mercado_leitura.py` — `larguras_de_molde`, `limite_de_glifo_unico`, `larguras_com_folga`, `particionar_run`, e a guarda + particao em `ler_glifos`; propagacao por `ler_celula`, as duas leituras de coluna e `ler_linha`
- `l2scanner/calibracao.py` — `TETO_DA_FOLGA_DE_COLA = 4`, o campo por `.get`, e `_conferir_a_folga_de_cola_do_glifo`
- `l2scanner/mercado_pagina.py` — o portao por AUSENCIA, com aviso alto e sem `raise`
- `tools/medir_brilho_da_quantidade.py` — os 5 pontos de chamada de `ler_celula` recebem a folga da calibracao
- `tests/test_mercado_leitura.py` (+27 testes), `tests/test_mercado_pagina.py` (+6), `tests/test_calibracao_mercado.py` (+10), `tests/test_medir_leitura_de_glifo.py` (pontos de chamada)
- `tests/fixtures/mercado/calibracao_de_fixture.json` — a chave copiada VERBATIM da producao (`1`)

## Decisions Made

- **O limite ficou DERIVADO e nao virou chave.** `max(largura)` sobre os moldes de um caractere. O vale medido de quatro niveis prova que a escolha dentro dele nao muda nada — o custo da guarda e identico em 6, 7, 8, 9 e 10.
- **A folga entrou como a UNICA chave nova**, com `TETO_DA_FOLGA_DE_COLA = 4` declarado em `calibracao.py` (onde a faixa e COBRADA) e IMPORTADO pela varredura. Duas declaracoes deixariam a ferramenta propor um valor que o arranque recusa.
- **O `0` e legitimo nesta chave**, diferente da irma: no piso de brilho o `0` desligava a leitura calado; aqui ele e a particao com larguras de molde puras. Quem desliga e a AUSENCIA.
- **O portao por ausencia NAO entra em `_calibrado`.** E a unica ausencia da fase que nao desliga a leitura, porque aqui ela degrada para MAIS SEGURO.
- **A DP escolhe pelo PIOR segmento.** A celula e tudo-ou-nada, entao o que separa dois cortes validos e o elo mais fraco de cada um.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Os pontos de chamada de `ler_celula` fora do `files_modified` do plano**

- **Found during:** Task 2
- **Issue:** Acrescentar um parametro somente-nomeado obrigatorio a `ler_celula` quebra TODOS os chamadores. Dois arquivos fora do `files_modified` do plano chamam: `tools/medir_brilho_da_quantidade.py` (5 pontos) e `tests/test_medir_leitura_de_glifo.py` (7 pontos, via o alias `classificar_celula`).
- **Fix:** A ferramenta passa `folga_de_cola=cal.mercado_folga_de_cola_do_glifo` — ela ja carrega a calibracao, e assim ela mede com o mesmo regime que a producao decide. A suite irma passa `None` (a GUARDA) com a razao escrita: nenhuma das fixturas dela tem run largo, entao a folga nao muda um pixel, e escolher um numero ali seria inventar.
- **Verification:** `python -m pytest --ignore=tests/test_agenda.py -q` → 2434 passed, 2 skipped.
- **Committed in:** `31cd0ba`

**2. [Rule 1 - Bug] O rendimento estava sendo SUBESTIMADO pela propria ferramenta**

- **Found during:** Task 1, na primeira passagem completa
- **Issue:** `rendimento_com_a_folga` so contava celulas que ja eram `aceita_hoje`, e por isso a particao aparecia devolvendo exatamente o que a guarda perderia (1.135) em vez de RENDER. Uma celula que hoje NAO le e que a particao recupera era invisivel. `reclassificar` tambem so lia as 124 celulas ROTULADAS, entao o material do rendimento nem existia.
- **Fix:** `reclassificar` passou a ler TODAS as 524 celulas com run largo (os tres baldes seguem olhando so as rotuladas — um rotulo que nao existe nao mede nada), e `rendimento_com_a_folga` conta uma celula larga quando a particao devolveu valor naquela folga.
- **Verification:** o rendimento passou de 1.135 (falso) para **1.148**, e as paginas de 155 para 156 — exatamente a previsao independente do planejador.
- **Committed in:** `303feed`

**3. [Rule 1 - Bug] O teste de IDENTIDADE do censo dependia da ORDEM DE COLETA do pytest**

- **Found during:** Task 2, na suite completa
- **Issue:** `test_e_o_MESMO_OBJETO_de_medir_oclusao` passava isolado e falhava na suite inteira. Quatro suites carregam `medir_oclusao` pelo proprio `importlib`, e cada carga registra um objeto NOVO em `sys.modules` — quem registra por ULTIMO e quem `sys.modules` devolve. O teste media a ordem de coleta, e nao a proveniencia da lista.
- **Fix:** o teste recarrega a ferramenta dentro dele, para que a ultima carga seja a NOSSA. A afirmacao continua sendo de IDENTIDADE (uma copia passaria na igualdade), com a razao escrita na docstring.
- **Verification:** verde isolado E na suite completa.
- **Committed in:** `31cd0ba`

### Desvios de ESCOPO declarados

**4. As tres causas viraram TRES linhas, e nao duas.** O plano pedia "o balde LE ERRADO de HOJE e o da folga 0 (a guarda pura)" em separado — mas folga 0 **nao e** a guarda pura: ela e a particao com as larguras de MOLDE, e as duas dao numeros diferentes (28 CERTO contra 0). O relatorio imprime as TRES separadas (HOJE, GUARDA PURA, FOLGA 0), que satisfaz o criterio literalmente e desfaz a ambiguidade em vez de escolher um lado dela.

**5. O portao do tracer foi o portao do VALE.** O plano marca a Task 1 como `type="tracer"` e o executor, em modo interativo, pararia num `checkpoint:human-verify` depois dela. O plano tem `autonomous: true` e codifica o proprio portao de integracao — a parada explicita do RELATORIO 1 ("se o intervalo NAO estiver vazio, a Task 2 NAO comeca"). O vale foi medido VAZIO, o `<verify>` do tracer foi re-rodado ponta a ponta (os dois `<automated>` verdes, a ferramenta saindo com codigo 0 e `PROPOSTO`), e a Task 2 comecou. Registrado aqui porque a substituicao foi uma decisao, e nao uma omissao.

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking) + 2 desvios de escopo declarados
**Impact on plan:** Os tres auto-fixes eram necessarios para a correcao da medicao e da suite. Nenhum escopo extra: os 14 arquivos tocados sao os 13 do plano mais `tools/medir_brilho_da_quantidade.py`, que so podia ficar de fora se o parametro novo tivesse valor de fabrica — que e exatamente o que o plano proibe.

## Duas afirmacoes do plano que a MEDICAO REFUTOU

O plano manda: *"onde a medicao da fase contradisser esta sondagem, a medicao manda, e a contradicao vira registro no SUMMARY com o numero que a derrubou."* Duas contradicoes:

**1. Afrouxar a folga NAO inventa numero — ele nao muda NADA.** O plano afirma que a variante D ("toda largura de 1 a 6") inventa **54 numeros**, e trata isso como o achado que dimensiona o risco. Medido: as folgas 2, 3 e 4 produzem leitura **IDENTICA** a folga 1 — **0 celulas mudam de leitura**, e o balde LE ERRADO segue vazio em todas.

A causa esta no criterio de escolha, e nao na largura: `particionar_run` escolhe pelo **PIOR segmento do corte**, entao acrescentar larguras permitidas so acrescenta candidatos PIORES, que perdem. O `6+5` de `frame_000105.png` L6 tem pior score 0,470 contra 0,791 do `7+4`, e por isso ele nunca vence — nem quando esta disponivel. A sondagem do planejador mediu outra regra de escolha (provavelmente a primeira composicao valida, ou a enumeracao que ele proprio abortou por custo).

**Consequencia pratica: nenhuma.** A folga proposta continua sendo `1` — o desempate por MENOR folga entre as que empatam em LE CERTO faz o trabalho que o plano esperava da degradacao. Mas a afirmacao "a largura de corte decide entre conserto e invencao" e verdadeira sobre a ESCOLHA DO CORTE e falsa sobre a LARGURA PERMITIDA, e essa distincao importa para quem for mexer no criterio da DP.

**2. A folga contra o tick e de 17x, e nao de tres ordens de grandeza.** O plano afirma "11,7 ms por linha larga — dentro de um tick de 1 Hz com folga de **tres ordens de grandeza**". Medido: **9,02 ms** no medio (proximo do sondado, ✓) mas **60,16 ms no PIOR caso** do censo, que da **17x** e nao 1.000x. O criterio declarado (teto de 200 ms) passa com folga confortavel, mas a margem real e menor do que o plano supunha — o pior caso vem dos runs muito largos (ate 61 px) das celulas cobertas por tooltip, que a DP tenta partir antes de desistir.

## Issues Encountered

- **O flake conhecido de `tests/test_agenda.py:1141`** derrubou a sessao uma vez com `KeyboardInterrupt` levantado de proposito (87 passed e aborta). Re-rodado duas vezes: **144 passed** nas duas. Abortar nao e falhar.
- **26 erros de lint PRE-EXISTENTES** em `tests/test_identidade.py`, `test_party_estavel.py`, `test_console.py`, `test_visao.py`, `l2scanner/visao.py` e outros tres — nenhum em arquivo tocado por este plano. Fora do escopo (regra de fronteira), nao consertados.

## Suite

- `python -m pytest --ignore=tests/test_agenda.py -q` → **2434 passed, 2 skipped**
- `python -m pytest tests/test_agenda.py -q` → **144 passed**
- `python -m ruff check` sobre os arquivos deste plano → **All checks passed**

## Known Stubs

Nenhum. Nao ha valor vazio, placeholder nem TODO introduzido por este plano.

## Threat Flags

Nenhuma superficie de seguranca nova. O plano nao instala pacote nenhum, nao abre porta, nao le memoria e nao envia input ao jogo. `recordings/` foi lida com as 8 pastas NOMEADAS (nunca por glob) e nunca escrita; a unica escrita foi o load-mutate-save de UMA chave do `calibration.json`.

## Next Phase Readiness

- **O 02-05 pode comecar, e agora ele mede rendimento VERDADEIRO.** Antes deste plano o replay contaria as 14 quantidades erradas e os 55 totais inventados como ACERTO — o criterio 2 da fase ("os precos e quantidades lidos batem digito a digito com o que o usuario ve no frame") passaria justamente por nao olhar as celulas que o derrubam. O `02-05` precisa somar `02-08` ao `depends_on` e passar para a wave 8.
- **O 02-07 volta a ser proponivel, e isso e item de ledger e nao task deste plano.** O balde LE ERRADO do piso compartilhado eram as 14 celulas de glifo colado; com a particao elas leem CERTO. `tools/medir_brilho_da_quantidade.py` chama `ler_celula` e ja recebe a folga, entao ele pega o beneficio de graca. **Nao foi re-rodado aqui de proposito** — a varredura passa de 10 minutos e ja custou uma sessao a um executor. Quem fechar o 02-07 deve encontrar o passo ZERO limpo, com os pisos 173..161 seguros, o ultimo seguro em 161, e rendimento previsto de 463 → 2.045 em 2.170.
- **A Fase 3 pode gravar o CSV com o preco confiavel.** A fronteira que este plano existia para proteger — o que atravessa vira dado permanente que o usuario entrega a outra IA — nao carrega mais numero inventado sobre as celulas rotuladas do censo.

---
*Phase: 02-leitura-de-p-gina*
*Completed: 2026-08-30*

## Self-Check: PASSED

Os 5 arquivos criados conferidos com `[ -f ]` no disco; os 5 hashes de commit
conferidos com `git log --oneline --all`. O portao do `calibration.json`
conferido por PRESENCA e por IDENTIDADE nas duas pontas de cada task.
