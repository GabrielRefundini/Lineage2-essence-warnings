---
phase: quick-260902-ca4
plan: 01
subsystem: mercado
tags: [mercado, leitura-de-glifo, guarda-de-cruzamento, calibracao, medicao]
status: complete
requires:
  - "l2scanner.mercado_pagina.LeitorDePagina._casamento_do_layout (o portao de layout de producao)"
  - "as 8 gravacoes NOMEADAS do censo em recordings/ (checkout principal)"
  - "calibration.json com mercado_layouts e mercado_cabecalho_de_coluna"
provides:
  - "LIMITE_DERIVADO_POR_UNIDADE = 1.0, derivado do TRUNCAMENTO e nao do arredondamento"
  - "o custo da dobra medido e preso por teste nos dois lados da fronteira (n=7 pega, n=8 escapa)"
  - "o portao de layout de PRODUCAO dentro da varredura que julga a guarda, chamado e nao copiado"
  - "a quebra por layout no relatorio da ferramenta (frames e linhas por veredito do portao)"
  - "a refutacao datada do veredito do 02-02, com a remedicao completa"
affects:
  - "l2scanner.mercado_leitura.quantidade_de_adena (GUARDA: descarta linha na aba Adena)"
  - "l2scanner.mercado_leitura._observar_o_cruzamento (OBSERVACAO: limiar do log)"
  - "tools/medir_leitura_de_glifo.py (o veredito da guarda e o par piso/margem proposto)"
  - "tools/medir_brilho_da_quantidade.py (o rotulo do limite no relatorio)"
tech-stack:
  added: []
  patterns:
    - "numero medido escrito no fonte com procedencia (padrao de ocr.py:34-52)"
    - "refutacao que ACRESCENTA e nunca apaga o registro anterior"
    - "prova por CONTAGEM DE CHAMADAS sobre a classe de producao, com controle negativo"
    - "teste que afirma o PRODUTO de dois fatores, e nao os fatores isolados"
key-files:
  created: []
  modified:
    - l2scanner/mercado_leitura.py
    - tools/medir_leitura_de_glifo.py
    - tools/medir_brilho_da_quantidade.py
    - tests/test_mercado_adena.py
    - tests/test_mercado_leitura.py
    - tests/test_medir_leitura_de_glifo.py
decisions:
  - "O limite derivado passa de 0,5 para 1,0 centesimo por unidade: a tela TRUNCA total/quantidade, medido contra um gabarito de dez linhas declarado ANTES da leitura, com quatro linhas discriminantes truncando as quatro"
  - "FATOR_MAXIMO_SOBRE_O_LIMITE_DERIVADO cai de 2,0 para 1,0 no MESMO commit, para o teto absoluto (1,0 centesimo por unidade) nao subir como efeito colateral. A alternativa de manter 2,0 fica RECUSADA por escrito"
  - "O portao de layout filtra a populacao do CRUZAMENTO e nao a de score/margem, porque a producao le as duas colunas de moeda da Adena com os MESMOS retangulos de negociacao. Filtrar a varredura inteira fica RECUSADO por escrito"
  - "A hipotese de contaminacao pela aba Adena esta DESMONTADA por medicao: o portao tirou 71 linhas e ZERO delas eram de adena"
  - "A guarda continua DESLIGADA. O dry-run reprovou de novo por tolerancia (1273 contra o maximo 1,0) e a deteccao de 0,0178 tambem cairia"
metrics:
  duration: ~2h
  completed: 2026-09-02
actuals:
  tokens: 178000
  tasks: 3
  commits: 3
---

# Quick 260902-ca4: O limite derivado do cruzamento passa de meio para um centesimo por unidade — Summary

A tela do jogo TRUNCA `total / quantidade`; o codigo supunha que ela ARREDONDA. `LIMITE_DERIVADO_POR_UNIDADE` valia metade do que a aritmetica da tela permite, e a guarda de cruzamento foi reprovada contra essa regua curta. Agora vale 1,0, com a prova de campo escrita ao lado, o custo da dobra medido nos dois lados, o portao de layout de producao dentro da varredura, e a remedicao rodada — que manteve a guarda DESLIGADA.

## O QUE MUDOU, EM UMA LINHA CADA

| # | Commit | O que |
|---|--------|-------|
| 1 | `5bbff41` | `LIMITE_DERIVADO_POR_UNIDADE` 0,5 → 1,0; `FATOR_MAXIMO_SOBRE_O_LIMITE_DERIVADO` 2,0 → 1,0; a frase do 02-02 marcada como REFUTADA; o custo da dobra medido e preso |
| 2 | `d0ceff5` | `LeitorDePagina._casamento_do_layout` CHAMADO na varredura; filtro de layout no cruzamento; quebra por layout no relatorio; prova por contagem de chamadas + controle negativo |
| 3 | `f211e1c` | O dry-run sobre o censo, com os numeros no bloco de refutacao; conserto da fronteira Fase 2/Fase 3 que a Tarefa 1 tinha quebrado |

## O VEREDITO DO DRY-RUN, INTEGRAL

Rodado com `.venv/Scripts/python.exe tools/medir_leitura_de_glifo.py --gravacoes <principal>/recordings --calibracao <principal>/calibration.json`, **SEM `--gravar`**, exit code 0. Saida integral preservada em `260902-ca4-DRY-RUN.txt`.

```
==============================================================================
RELATORIO 3 - O VEREDITO DA GUARDA DE CRUZAMENTO
==============================================================================
  linhas com as tres colunas lidas e na gramatica: 1201
  dessas, as que passam no piso 0.4698 e na margem 0.0370: 1172
  (populacao CRUA, para conferencia: GUARDA REPROVADA por tolerancia, 2000.0000 centesimos por unidade (maximo 1.0))
  residuo por unidade: mediana 0.2500, p95 270.1200, max 1333.3333
  fechamento no LIMITE DERIVADO (1.0/unidade): 0.9377
  criterios: fechamento >= 0.99, tolerancia <= 1.0, deteccao >= 0.9
  medido: fechamento=0.9991, tolerancia=1273.0, deteccao=0.0178 sobre 1741 substituicoes injetadas

  O PORTAO DE LAYOUT DE PRODUCAO, CHAMADO UMA VEZ POR FRAME ABERTO:
    NENHUM (nao casou, ou empate)      106 frames
    adena                               25 frames
    negociacao                         347 frames
    TOTAL com painel aberto            478 frames

  LINHAS COMPLETAS DO CRUZAMENTO, POR LAYOUT (apos piso e margem):
    NENHUM (nao casou, ou empate)       71 linhas
    negociacao                        1172 linhas
    -> o portao TIROU 71 linhas da populacao do cruzamento e deixou 1172.

  FECHAMENTO NO LIMITE DERIVADO, POR GRAVACAO:
  (so linhas de `negociacao`: o portao de PRODUCAO `LeitorDePagina._casamento_do_layout` ja filtrou a populacao. Na aba Adena a terceira coluna e `5 mln increment`, normalizada por 5 milhoes de adena e NAO por unidade - ali a relacao `total = unitario x quantidade` nao vale, e por construcao, nao por erro de leitura.)
    053105-mercado-aberto                847 de   917  ( 92.4%)
    055323-mercado-scroll                102 de   103  ( 99.0%)
    060622-mercado-pagina-cheia           33 de    34  ( 97.1%)
    061253-mercado-tooltip             (nenhuma linha)
    061409-mercado-alvo-sobreposto     (nenhuma linha)
    063240-mercado-farm-com-party      (nenhuma linha)
    063409-mercado-scroll-transicao      117 de   118  ( 99.2%)
    063752-mercado-aberto              (nenhuma linha)

  GUARDA REPROVADA por tolerancia, 1273.0000 centesimos por unidade (maximo 1.0)

O QUE VAI PARA O calibration.json:
  mercado_limiar_de_leitura_de_glifo = 0.469831
  mercado_margem_de_leitura_de_glifo = 0.036984
  mercado_tolerancia_do_cruzamento   = None

(nada gravado - rode de novo com --gravar para persistir)
```

Cabecalho da varredura, para conferencia da populacao:

```
Varrendo... (tres colunas calibradas, linha a linha)
  celulas com leitura: 4374 linhas de grade
  runs classificados : 55342
```

### QUAL CRITERIO CAIU, COM O NUMERO

**`tolerancia`.** A tolerancia que fecharia 0,99 e **1273,0 centesimos por unidade** contra o teto de **1,0** — 1.273 vezes o limite derivado. A `deteccao` tambem cairia: **0,0178** contra o minimo de **0,90**, sobre **1.741** substituicoes `0`<->`8` injetadas. O `fechamento` de 0,9991 so existe *com* aquela tolerancia de 1273; contra o limite derivado honesto ele e **0,9377**, ainda abaixo do 0,99 exigido.

**A guarda continua DESLIGADA, e nao foi ligada por esta tarefa.** `mercado_tolerancia_do_cruzamento` segue `None` no disco por construcao — a ferramenta so escreve com `--gravar`, e ela rodou sem ele.

## OS TRES ACHADOS

### 1. A hipotese de contaminacao pela aba Adena esta DESMONTADA — por um numero que saiu ZERO

O bloco do 02-02 explicava a queda dizendo que a varredura media sobre frames de todos os layouts, e que as linhas de Adena (onde `total = unitario x quantidade` nao vale) puxavam o fechamento para baixo. Com o portao instalado, o efeito medido e:

- o portao tirou **71 linhas** de 1.243, deixando 1.172;
- **ZERO** delas eram de `adena`. As 71 vieram de frames em que o portao **nao opinou** (nenhum layout passou o proprio limiar, ou houve empate).

A razao e estrutural: na aba Adena a coluna `Quantity` de negociacao cai sobre vazio e le `None`, entao aquelas linhas **nunca foram completas** e nunca chegaram ao cruzamento. A contaminacao que se supunha nao estava la. O que estava era o limite valendo metade.

### 2. Quase toda a queda era a regua, e a `pagina-cheia` prova isso sozinha

O fechamento no limite derivado subiu de **0,6525** para **0,9377**, e o portao respondeu por 71 linhas disso. O resto foi a constante.

O paragrafo do 02-02 usou a `pagina-cheia` — negociacao pura, sem Adena para culpar — como prova de que a queda nao era so de layout: *"para em 84,2%"*. Contra a regua certa ela fecha **33 de 34, 97,1%**.

### 3. O que AINDA falta (e nao se conserta mexendo no limite de novo)

Sobram **6,2%** de linhas de negociacao que nao fecham nem com um centesimo por unidade, e a `053105-mercado-aberto` responde por quase todas (847 de 917, 92,4%, contra 97-99% das outras tres). A proxima remedicao comeca por olhar aquela gravacao. Um limite que se mexe ate o numero fechar nao e derivacao, e ajuste de curva — e isso esta escrito no fonte.

## AS PROVAS DE MUTACAO (obrigatorias, todas rodadas)

### Tarefa 1 — `LIMITE_DERIVADO_POR_UNIDADE` de volta em `0.5`

```
6 failed, 69 passed in 2.10s
```

Asserts que quebraram, verbatim:

```
E   assert 3.5 == 7.0
     +  where 3.5 = limite_derivado_do_cruzamento(7)
tests/test_mercado_adena.py:311: assert 3.5 == 7.0
E   assert 4.0 == 8.0
     +  where 4.0 = limite_derivado_do_cruzamento(8)
tests/test_mercado_adena.py:325: assert 4.0 == 8.0
E   assert 15 == 7
     +  where 15 = max([1, 2, 3, 4, 5, 6, ...])
tests/test_mercado_adena.py:349: assert 15 == 7
E   AssertionError: a pagina verificada fecha 10 de 10
    assert 7 == 10
     +  where 7 = len([(8, 2000, 250), (6, 1800, 300), (3, 1000, 333), (4, 1360, 340), (3, 1050, 350), (8, 3100, 387), ...])
tests/test_mercado_adena.py:395: AssertionError: a pagina verificada fecha 10 de 10
```

Os seis que cairam:

```
FAILED tests/test_mercado_adena.py::TestOsDoisCasosDificeis::test_a_aceitacao_do_caso_bom_e_por_FOLGA_desde_a_medicao_de_02_09
FAILED tests/test_mercado_adena.py::TestOsDoisCasosDificeis::test_a_recusa_do_caso_ruim_e_por_88_contra_2
FAILED tests/test_mercado_adena.py::TestAFronteiraDeDeteccaoDaDobraDoLimite::test_com_n_igual_a_7_a_troca_ainda_e_PEGA
FAILED tests/test_mercado_adena.py::TestAFronteiraDeDeteccaoDaDobraDoLimite::test_com_n_igual_a_8_a_troca_ESCAPA_e_esse_e_o_custo
FAILED tests/test_mercado_adena.py::TestAFronteiraDeDeteccaoDaDobraDoLimite::test_a_conta_de_ate_quanto_cada_limite_pega
FAILED tests/test_mercado_adena.py::TestOGabaritoDeCampoDe20260902::test_as_dez_linhas_fecham_contra_o_limite_de_hoje
```

Mutacao desfeita, re-rodado: `277 passed in 14.35s`.

### Tarefa 2, mutacao A — descarte por layout removido de `linhas_do_cruzamento`

```
1 failed, 43 passed in 6.80s
```

```
_ TestOPortaoDeLayoutDaPRODUCAO_E_CHAMADO.test_CONTROLE_NEGATIVO_o_portao_forcado_a_adena_ZERA_o_cruzamento _
tests\test_medir_leitura_de_glifo.py:531: in test_CONTROLE_NEGATIVO_o_portao_forcado_a_adena_ZERA_o_cruzamento
    assert ferramenta.linhas_do_cruzamento(falso) == []
E   AssertionError: assert [LinhaMedida(...rio=189), ...] == []
E
E     Left contains 10 more items, first extra item: LinhaMedida(gravacao='20260828-000000-sintetica', arquivo='frame_000001.png', linha=0, total=300, quantidade=0, unitario=300)
```

Desfeita, re-rodado: `44 passed`.

### Tarefa 2, mutacao B — chamada do portao trocada pela constante local `"negociacao"`

```
4 failed, 40 passed in 6.69s
```

O assert da CONTAGEM DE CHAMADAS, que e o criterio central da tarefa:

```
_ TestOPortaoDeLayoutDaPRODUCAO_E_CHAMADO.test_o_portao_e_chamado_UMA_VEZ_POR_FRAME_ABERTO _
tests\test_medir_leitura_de_glifo.py:490: in test_o_portao_e_chamado_UMA_VEZ_POR_FRAME_ABERTO
    assert len(respostas) == abertos
E   assert 0 == 2
E    +  where 0 = len([])
```

E os outros tres:

```
E   AssertionError: frame_000002.png
E   assert 'negociacao' == 'adena'
E     - adena
E     + negociacao

E   AssertionError: assert set() == {'adena'}
E     Extra items in the right set:
E     'adena'

E   assert '_casamento_do_layout(' in '"""A varredura que MEDE o piso e a margem de LEITURA, e julga a guarda...'
```

Desfeita, re-rodado: `44 passed`. Depois, com `tests/test_mercado_pagina.py` junto: `114 passed in 25.35s`.

**As tres mutacoes fizeram os testes falhar. Nenhuma passou em silencio.**

## COMO A PROVA DO PORTAO E FEITA (e por que ela nao e a decima terceira do padrao ruim)

O criterio da Tarefa 2 **nao afirma que uma funcao existe**. Ele:

1. Embrulha `LeitorDePagina._casamento_do_layout` **na classe de PRODUCAO** com um contador que delega ao metodo original.
2. Afirma que o contador == numero de frames com painel aberto, **e que esse numero e maior que zero** (`test_as_duas_fixturas_ABREM_o_painel` existe so para o teste nao passar por medir vacuo).
3. Afirma os vereditos `negociacao` e `adena` sobre **duas fixturas REAIS** (`janela_negociacao_f005.png`, `janela_adena_f014.png`).
4. **Controle negativo:** com o portao forcado a responder `adena` para todo frame, a populacao do CRUZAMENTO vai a **zero** enquanto `resultado.amostras` fica **identica** a do caso real e maior que zero. Isso separa *"o portao foi chamado"* de *"a resposta do portao decide alguma coisa"*, e separa as duas populacoes de proposito.
5. Uma inspecao de fonte confirma que `casamento_do_cabecalho` e `def _banda_do_cabecalho` **nao aparecem** na ferramenta — se alguem copiar o portao para dentro dela, o teste cai.

A mutacao B (trocar a chamada por uma constante) derruba (2), (3), (4) e (5). Uma reimplementacao local seria pega por (5).

## O CUSTO DA DOBRA, MEDIDO E ESCRITO

Uma troca `0`<->`8` mexe o total em no **minimo 8 centesimos**. A guarda so a pega enquanto `quantidade x limite` for menor que 8:

| limite | pega ate |
|--------|----------|
| 0,5/unidade (antes) | 15 unidades ou incrementos de escala |
| 1,0/unidade (agora) | **7** |

Preso nos dois lados, com residuo 8 identico e so a escala mudando:

- `quantidade_de_adena(1000, 144)` → n=7, residuo 8 contra limite 7,0 → **RECUSA**
- `quantidade_de_adena(1000, 126)` → n=8, residuo 8 contra limite 8,0 → **ACEITA** (escapa)
- com `LIMITE_DERIVADO_POR_UNIDADE` injetado de volta em 0,5, esse mesmo n=8 era **recusado** (limite 4,0)

**O caso de campo continua coberto:** as ofertas reais da aba Adena sao de 1 a 3 incrementos (5M/10M/15M), limites 1,0 / 2,0 / 3,0 — todos bem abaixo de 8. Na negociacao a guarda esta desligada e o efeito e so no limiar do log de observacao.

## O TETO QUE NAO SE MOVEU

`LIMITE_POR_UNIDADE x FATOR_MAXIMO_SOBRE_O_LIMITE_DERIVADO` valia `0,5 x 2,0 = 1,0` e vale `1,0 x 1,0 = 1,0`. O 2x existia para deixar espaco para a hipotese do truncamento; com o truncamento virando a propria derivacao, mante-lo empilharia a mesma folga duas vezes. A alternativa (manter 2,0, teto virando 2,0) esta **RECUSADA por escrito** ao lado da constante.

`TestOTetoAbsolutoDaTolerancia` afirma o **PRODUTO** e nao os fatores, com a razao na docstring: um teste que afirmasse `FATOR == 1.0` ficaria verde no dia em que alguem dobrasse a outra constante, e o teto subiria em silencio. A linha de veredito continua dizendo `(maximo 1.0)`, e o 02-02 continua reprovado pelo MESMO numero contra o MESMO teto.

## O REGISTRO ANTERIOR SOBREVIVEU INTEIRO

A refutacao **acrescenta e nunca apaga**. No fonte de `mercado_leitura.py`: `1273` aparece 9 vezes, `0,6525` 4 vezes, `0,0164` 2 vezes, e a linha `1273.0000 centesimos por unidade` 2 vezes. Os dois testes de inspecao que os prendem (`test_o_fonte_registra_a_medicao_REFUTADA_com_os_numeros` e `test_o_veredito_do_02_02_esta_transcrito_no_fonte`) seguem **verdes sem uma edicao**.

## TESTES ATUALIZADOS COM A RAZAO (nunca apagados)

| Teste | O que mudou, e por que esta escrito |
|-------|--------------------------------------|
| `TestOsDoisCasosDificeis` | Perdeu o proposito de testemunhar o sinal `<=`: o caso-bandeira `133,33/66,66` passava por IGUALDADE contra 1,0 e agora passa com FOLGA contra 2,0. A inversao esta na docstring da classe, e o teste `..._por_IGUALDADE_e_nao_por_folga` foi **renomeado** para `..._por_FOLGA_desde_a_medicao_de_02_09` — deixar o nome antigo verde seria manter no repositorio uma afirmacao que a constante desmentiu |
| `TestOSinalDaComparacao` | Passa a ser a **unica** testemunha do sinal, e sempre foi a certa: ela INJETA o limite (1,0 e 0,99 sobre o mesmo residuo 1) e nao depende da constante |
| `TestOLimiteDerivadoDoCruzamento` | Spike 24 → 48; crescimento 5/0,5 → 10/1,0; docstring reescrita para o truncamento |
| `test_o_caso_conhecido_do_spike_fecha` | `limite_derivado_do_cruzamento(48)` de 24 para 48, com a nota de que o residuo 16 **nao** mudou |
| `tolerancia_de_ensaio` | Docstring: a derivacao sai do truncamento, e ela vale o dobro sem deixar de ser consequencia |
| `test_reprova_quando_a_TOLERANCIA_estoura_o_limite_derivado` | Limite derivado do caso de 5 para 10; a docstring registra que o **teto** e o mesmo dos dois lados |

## TESTES NOVOS

| Classe | Arquivo | O que mede |
|--------|---------|------------|
| `TestAFronteiraDeDeteccaoDaDobraDoLimite` (5) | `test_mercado_adena.py` | O custo da dobra nos dois lados, com o controle que injeta 0,5 de volta, a conta 15-contra-7, e as ofertas reais continuando cobertas |
| `TestOGabaritoDeCampoDe20260902` (3) | `test_mercado_adena.py` | As dez linhas do gabarito fecham 10/10 hoje e 7/10 com 0,5 injetado (as tres que caem estao nomeadas); e as quatro discriminantes truncam as quatro |
| `TestOPortaoDeLayoutDaPRODUCAO_E_CHAMADO` (6) | `test_medir_leitura_de_glifo.py` | Contagem de chamadas ao portao de producao + controle negativo + inspecao anti-copia |
| `TestOTetoAbsolutoDaTolerancia` (3) | `test_medir_leitura_de_glifo.py` | O PRODUTO dos dois fatores, o teto publicado no veredito, e o 02-02 caindo contra o mesmo teto |

## O QUE NAO FOI TOCADO

- **`calibration.json`**: sha256 `c41e665b8eac1669...` antes **e** depois do dry-run. `mercado_tolerancia_do_cruzamento` = `None`, `mercado_limiar_de_leitura_de_glifo` = `0.4698309302330017`, `mercado_margem_de_leitura_de_glifo` = `0.03698354959487915` — asserts rodados e verdes. Nunca commitado.
- **`.mercado/observacoes.csv`**: sha256 `d107dbc1ab462ba3...` antes **e** depois. Nenhum teste escreve fora de `tmp_path`.
- **`recordings/`**: somente leitura, e so pela logica de 8 pastas NOMEADAS que a ferramenta ja tinha. Nenhum glob amplo acrescentado. Os testes novos copiam **duas fixturas versionadas** para `tmp_path`.
- **`VERSAO_DO_ESQUEMA`** continua `2` (`l2scanner/calibracao.py:23`). Nenhuma chave de calibracao nova ou alterada.
- `l2scanner/rastreador.py`, `l2scanner/visao.py` e os arquivos do agente paralelo (`respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`, `test_bosses.py`, `identidade.py`, `discord/`, `dashboard.py`) — `git status --porcelain` sobre eles sai **vazio**, e `git diff --name-only 74f7caa HEAD` nao lista nenhum.
- Zero dependencia nova. Nenhuma biblioteca de sintese de input.
- Nenhuma delecao de arquivo em nenhum dos tres commits (`git diff --diff-filter=D` vazio).

## DESVIOS DO PLANO

### 1. [Rule 1 - Bug] A fronteira Fase 2/Fase 3 quebrada pela Tarefa 1, e consertada

- **Encontrado em:** a suite completa, depois da Tarefa 2
- **Problema:** o paragrafo da prova limpa que a Tarefa 1 escreveu em `mercado_leitura.py` nomeava o CSV de observacoes. `tests/test_mercado_replay.py::TestAFronteiraComAFase3::test_nenhum_modulo_desta_fase_nomeia_o_CSV_de_observacoes` proibe os tres modulos desta fase de nomear aquele arquivo — a Fase 2 escreve o catalogo de nomes e nada mais.
- **Falha:** `FAILED tests/test_mercado_replay.py::TestAFronteiraComAFase3::test_nenhum_modulo_desta_fase_nomeia_o_CSV_de_observacoes` (`1 failed, 4764 passed, 26 skipped`)
- **Conserto:** o fato foi reescrito sem o nome do arquivo, apontando para a fronteira que o proibe. **O teste nao foi tocado** — a regra e arquitetural e vale mais que a comodidade da minha prosa.
- **Commit:** `f211e1c`

### 2. [Rule 1 - Bug] Um numero derivado escrito errado em `tools/medir_brilho_da_quantidade.py`

- **Encontrado em:** Tarefa 1, varrendo quem mais repetia a derivacao antiga
- **Problema:** o relatorio imprimia o rotulo `DERIVADO do arredondamento (quantidade/2 centesimos)` com um numero repetido a mao. Depois da dobra ele anunciaria `quantidade/2` sobre uma conta que ja vale `quantidade`.
- **Conserto:** o rotulo passa a derivar de `LIMITE_DERIVADO_POR_UNIDADE`. As duas mencoes **historicas** a `quantidade/2` no mesmo arquivo (linhas 233 e 1048, que narram por que o rotulo por INTERVALO nasceu) ficaram intactas — elas descrevem o passado corretamente.
- **Arquivo fora do `files_modified` do plano**, acrescentado por ser um numero derivado escrito errado. `tests/test_medir_brilho_da_quantidade.py`: `34 passed`.
- **Commit:** `5bbff41`

### 3. [Achado, nao desvio] A linha de base da suite neste worktree e outra

O plano declara `4698 passed, 2 skipped`. Medido em `74f7caa` **antes de qualquer edicao minha**: **`4748 passed, 26 skipped`**, exit 0.

A causa provavel dos 24 skips a mais e que **este worktree nao materializa `recordings/`, `calibration.json` nem `.mercado/`** — os tres sao gitignored e existem so no checkout principal. Os testes que dependem deles pulam aqui e rodam la. A diferenca de `passed` (+50) e de outros agentes que commitaram testes entre a medicao do plano e este commit. Nada disso e regressao, e o criterio real (`passed` acima da linha de base, exit 0) foi comparado contra a linha medida **nesta arvore**, que e a unica comparacao valida.

### 4. [Achado] Um teste INTERMITENTE fora da minha area, registrado e nao escondido

Numa das rodadas da suite completa caiu
`tests/test_janela_de_selecao.py::TestODrenoDaFilaDeTeclas::test_dreno_por_tempo_e_nao_por_numero_de_sondagens`
(`1 failed, 4764 passed, 26 skipped`). Ele **nao tem relacao com este diff** — mede
o RELOGIO com `perf_counter` numa espera ocupada, e meus seis arquivos sao todos de
mercado. Em isolamento: `9 passed in 1.66s`. Na rodada final da suite inteira ele
passou junto com todo o resto.

Diagnostico: teste de tempo de parede sob carga (a maquina rodava outra suite em
paralelo). **Nao foi consertado nem silenciado** — e area de outro agente, e um
teste de relogio que falha sob carga e um achado que o dono dele precisa ver, nao
um item para eu mexer. Fica registrado aqui.

### 5. [Nota de execucao] O dry-run rodou contra o checkout PRINCIPAL

`recordings/` e `calibration.json` nao existem no worktree. A ferramenta aceita `--gravacoes` e `--calibracao`, entao ela rodou com o **codigo do worktree** e o **material do principal**, exatamente como a docstring dela ja instruia. Sem isso a ferramenta sairia com codigo 3 (pasta do censo ausente), que e o comportamento correto dela.

## VERIFICACAO CONTRA O PLANO

| # | Criterio | Resultado |
|---|----------|-----------|
| 1 | Suite exit 0, `passed` acima da linha de base | **4765 passed, 26 skipped, exit 0** contra a linha de 4748 medida nesta arvore |
| 2 | `limite_derivado_do_cruzamento` → 1,0 / 2,0 / 4,0 / 6,0 / 9,0 / 48 | `[1.0, 2.0, 4.0, 6.0, 9.0, 48.0]` |
| 2b | As dez linhas do gabarito fecham | `fechamento do gabarito: 10 de 10` |
| 3 | As mutacoes obrigatorias aplicadas, medidas, copiadas e desfeitas | 3 de 3, transcritas acima |
| 4 | sha256 de `calibration.json` e do CSV da prova | `c41e665b8eac1669...` e `d107dbc1ab462ba3...`, iguais antes e depois |
| 5 | `mercado_tolerancia_do_cruzamento` `None`, piso `0.4698309302330017` | asserts verdes |
| 6 | Dry-run preservado e transcrito no fonte | `260902-ca4-DRY-RUN.txt` (8.735 bytes), numeros no bloco de refutacao |
| 7 | `git diff --name-only` sem `rastreador.py`, `visao.py` nem arquivos do agente paralelo | confirmado, 6 arquivos so |
| — | `quantidade_de_adena(13588, 6750)` | `None` |
| — | `quantidade_de_adena(13333, 6666)` | `(10000000, 2)` |
| — | `LIMITE_POR_UNIDADE x FATOR` | `1.0` |
| — | `grep -c "GUARDA " DRY-RUN.txt` | `3` |

## PENDENCIA PARA O ORQUESTRADOR

`.planning/quick/260902-ca4-.../260902-ca4-DRY-RUN.txt` esta **no disco e NAO commitado**, por instrucao de nao commitar artefatos de docs. Ele e a evidencia integral do veredito e o bloco de refutacao do fonte aponta para ele — precisa entrar no commit de docs.

## Known Stubs

Nenhum. Nenhum valor vazio, texto de placeholder ou componente sem fonte de dados foi introduzido.

## Self-Check: PASSED

Arquivos afirmados, conferidos no disco:

```
FOUND: l2scanner/mercado_leitura.py
FOUND: tools/medir_leitura_de_glifo.py
FOUND: tools/medir_brilho_da_quantidade.py
FOUND: tests/test_mercado_adena.py
FOUND: tests/test_mercado_leitura.py
FOUND: tests/test_medir_leitura_de_glifo.py
FOUND: .planning/quick/260902-ca4-o-limite-derivado-do-cruzamento-passa-de/260902-ca4-DRY-RUN.txt
```

Commits afirmados, conferidos em `git log`:

```
FOUND: 5bbff41
FOUND: d0ceff5
FOUND: f211e1c
```

---

## Verificacao independente do orquestrador

A prova de mutacao foi refeita por conta propria, em worktree isolado sobre o merge, e o
resultado bate com o relatado:

| mutacao aplicada | resultado medido |
|---|---|
| (linha de base) | `44 passed in 7.72s` |
| trocar `leitor._casamento_do_layout(...)` por `layout = "negociacao"` | `4 failed, 40 passed in 4.80s` |

Os quatro que caem incluem `test_o_fonte_CHAMA_o_portao_e_nao_reimplementa_o_casamento` e o
controle negativo `test_CONTROLE_NEGATIVO_o_portao_forcado_a_adena_ZERA_o_cruzamento`. O
criterio mede CHAMADA, e nao existencia.

Arquivos protegidos conferidos apos o merge: `calibration.json` sha `c41e665b8eac1669` e
`.mercado/observacoes.csv` sha `d107dbc1ab462ba3`, ambos identicos aos de antes da tarefa, e
nenhum dos dois sob controle de versao.

## A hipotese do orquestrador que a medicao REFUTOU

Ao propor esta tarefa eu afirmei que a populacao que julga a guarda estava "contaminada com
linhas onde a aritmetica simplesmente nao se aplica", apontando a aba Adena, e citei como apoio
a propria nota da ferramenta. **Estava errado, e o portao provou por um zero:** das 71 linhas
que ele tirou da populacao do cruzamento, NENHUMA era de `adena`. Na aba Adena a coluna
`Quantity` cai sobre vazio, entao aquelas 25 paginas nunca produziram linha COMPLETA e nunca
chegaram ao cruzamento. As 71 vieram todas de frames em que o portao nao casou layout nenhum.

O portao continua sendo a coisa certa a ter na varredura — ele fecha por construcao uma porta
que estava aberta, e o custo e uma chamada por frame. Mas o merito do salto e de outro numero:
o fechamento no limite derivado subiu de 0,6525 para 0,9377, e disso quase tudo e a regua,
nao o filtro.
