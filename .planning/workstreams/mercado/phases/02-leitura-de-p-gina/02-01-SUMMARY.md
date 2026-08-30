---
phase: 02-leitura-de-p-gina
plan: 01
subsystem: config
tags: [calibracao, opencv, hsv, saturacao, ocr, template-matching, json]

requires:
  - phase: 01-funda-o-firewall-gravador-e-spike-de-campo
    provides: as 8 gravacoes de campo, os 13 moldes de glifo, as 3 ancoras do painel e o fluxo propor-e-confirmar de `calibrar_mercado.py`
provides:
  - 14 chaves novas em `calibration.json` (opcionais, por `.get`, validadas no portao de carga, VERSAO_DO_ESQUEMA intacta em 2)
  - "`mercado_visao.cabecalho_de_calibracao` — desserializacao NAO CONFIAVEL do molde do cabecalho"
  - marcacao propor-e-confirmar das quatro colunas (nome, Quantity, Total, Unit price) em `calibrar_mercado.py`
  - "corte do molde do cabecalho com corte de brilho MEDIDO no frame (222), sem a seta de ordenacao"
  - "`sugerir_as_colunas`, `sugerir_a_coluna_do_nome`, `medir_o_corte_de_brilho_do_cabecalho`, `grupos_do_cabecalho`, `conferir_a_coluna_na_grade`"
  - 3 fixtures versionadas de negociacao que os planos 02-02..02-06 consomem
  - "`calibration.json` da maquina do usuario recalibrado para a GRADE DE NEGOCIACAO pela mao dele"
affects: [02-02, 02-03, 02-04, 02-05, 02-06, leitura de pagina, portao de layout, estabilizador]

actuals:
  tokens: 28595
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "corte de limiar pelo MAIOR VAO entre os picos do proprio frame (`_corte_pelo_maior_vao`) — nenhuma constante de brilho no fonte"
    - "saturacao como avesso de `mascara_de_texto`: brilho acha TEXTO, saturacao acha ARTE"
    - "cruzamento de duas medicoes independentes (rotulos do cabecalho x conteudo das linhas) como condicao para PROPOR"
    - "colunas contadas A PARTIR DA DIREITA, com `Buy` de ancora"
    - "voto na borda DIREITA + esquerda minima entre os votantes (herdado de `sugerir_a_coluna_de_preco`)"

key-files:
  created:
    - l2scanner/mercado_visao.py::cabecalho_de_calibracao
    - tests/test_mercado_visao.py
    - tests/fixtures/mercado/janela_negociacao_f010.png
    - tests/fixtures/mercado/cabecalho_negociacao_goods.png
    - tests/fixtures/mercado/cabecalho_negociacao_unitprice.png
  modified:
    - l2scanner/calibracao.py
    - l2scanner/calibrar_mercado.py
    - l2scanner/mercado_visao.py
    - tests/test_calibracao_mercado.py
    - tests/test_calibrar_mercado.py

key-decisions:
  - "A largura da coluna do nome NAO e 270 px: 270 virou PISO afirmado em teste, e o limite direito real e o comeco do rotulo `Quantity` no cabecalho (324 px medidos). Medir pelo texto da pagina daria 263 px e truncaria nome longo."
  - "O fim do icone sai da SATURACAO, com referencia medida nas colunas de numero da mesma linha. Maior-vao e Otsu foram TENTADOS e caem no miolo escuro do icone (84-107 entre bordas de 193-255), devolvendo 22 onde a resposta e 42."
  - "As colunas de numero sao contadas a partir da DIREITA, porque o icone e o nome se fundem num grupo so quando o vao entre eles tem 5 px (medido em 063752/frame_000000) e se separam quando tem 13 px (pagina-cheia/frame_000010)."
  - "O corte de brilho do cabecalho e medido pelo MAIOR VAO entre os picos dos grupos da propria banda: 222 nas duas fixtures, entre a seta (190) e os rotulos (237)."
  - "`mercado_templates_de_nome` e `mercado_limiar_de_template` deixaram de ser ESCRITOS por `calibrar()`. A guarda do CR-04 virou omissao, que e mais forte: nao se sobrescreve o que nao se atribui."
  - "As 3 ancoras gravadas sao NOVAS, recortadas de `063752/frame_000000`, porque as originais do usuario foram apagadas pelo incidente da janela quebrada 13. Ele conferiu na imagem e aprovou."

patterns-established:
  - "Limiar medido pelo maior vao: `_corte_pelo_maior_vao(picos)` devolve o meio do maior vao entre valores consecutivos, ou `None` quando o corte nao ficaria estritamente dentro dele."
  - "Proposta so com cruzamento: `sugerir_as_colunas` devolve `{}` quando cabecalho e linhas discordam. Sugestao errada e pior que sugestao nenhuma."
  - "Medicao refutada preservada ao lado da que a substituiu (`ocr.py:36-39`): maior-vao e Otsu para o icone, e o 0,8555 como piso de leitura de glifo."

requirements-completed: [LEIT-05, LEIT-02]

coverage:
  - id: D1
    description: "As 14 chaves novas de mercado existem, serializam, carregam por `.get` e sao conferidas no portao de carga, com VERSAO_DO_ESQUEMA intacta em 2"
    requirement: LEIT-02
    verification:
      - kind: unit
        ref: "tests/test_calibracao_mercado.py::TestAsQuatorzeChavesNovasSaoOPCIONAIS"
        status: pass
      - kind: unit
        ref: "tests/test_calibracao_mercado.py::TestAsQuatorzeSaoENTRADA_NAO_CONFIAVEL"
        status: pass
    human_judgment: false
  - id: D2
    description: "`cabecalho_de_calibracao` desserializa o molde do cabecalho como entrada nao confiavel, com a contagem de bytes conferida ANTES do reshape"
    requirement: LEIT-02
    verification:
      - kind: unit
        ref: "tests/test_mercado_visao.py::TestAsRecusas"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_visao.py::TestAAusenciaEFeatureOFF"
        status: pass
    human_judgment: false
  - id: D3
    description: "A ferramenta propoe e persiste as quatro colunas (nome, Quantity, Total, Unit price) por propor-e-confirmar, em deslocamento relativo a origem do painel"
    requirement: LEIT-05
    verification:
      - kind: unit
        ref: "tests/test_calibrar_mercado.py::TestAsColunasDeNumero"
        status: pass
      - kind: unit
        ref: "tests/test_calibrar_mercado.py::TestASugestaoDaColunaDoNome"
        status: pass
      - kind: unit
        ref: "tests/test_calibrar_mercado.py::TestRodarSemWatchlistNaoApagaOsMoldes::test_as_quatro_colunas_sao_gravadas_em_DESLOCAMENTO"
        status: pass
    human_judgment: false
  - id: D4
    description: "O molde do cabecalho e cortado de uma mascara de brilho cujo corte foi MEDIDO no frame; a seta de ordenacao fica de fora e o molde casa a mesma coluna nas duas ordenacoes"
    verification:
      - kind: unit
        ref: "tests/test_calibrar_mercado.py::TestOMoldeDoCabecalhoCasaAsDuasORDENACOES"
        status: pass
      - kind: unit
        ref: "tests/test_calibrar_mercado.py::TestOCorteDeBrilhoDoCabecalho"
        status: pass
    human_judgment: false
  - id: D5
    description: "O passo da watchlist saiu do fluxo principal e nenhuma instrucao de preencher lista de itens e impressa"
    verification:
      - kind: unit
        ref: "tests/test_calibrar_mercado.py::TestOPassoDaWatchlistFoiAPOSENTADO"
        status: pass
      - kind: unit
        ref: "tests/test_calibrar_mercado.py::TestRodarSemWatchlistNaoApagaOsMoldes::test_nenhuma_instrucao_de_preencher_watchlist_e_impressa"
        status: pass
    human_judgment: false
  - id: D6
    description: "Um retangulo de coluna marcado fora dos limites da grade e recusado na hora, com o conserto na mensagem, e antes de gravar"
    verification:
      - kind: unit
        ref: "tests/test_calibrar_mercado.py::TestARecusaDeColunaForaDaGrade"
        status: pass
      - kind: unit
        ref: "tests/test_calibrar_mercado.py::TestRodarSemWatchlistNaoApagaOsMoldes::test_uma_coluna_fora_da_grade_recusa_ANTES_de_gravar"
        status: pass
    human_judgment: false
  - id: D7
    description: "As tres fixtures de negociacao existem versionadas e os planos seguintes as consomem sem cortar de novo"
    verification:
      - kind: unit
        ref: "tests/test_calibrar_mercado.py::TestAsTresFixturesDeNegociacaoExistem"
        status: pass
    human_judgment: false
  - id: D8
    description: "O `calibration.json` da maquina do usuario descreve a GRADE DE NEGOCIACAO com as quatro colunas e o cabecalho marcados, sem perder os 13 moldes de glifo nem as 3 ancoras"
    requirement: LEIT-05
    verification:
      - kind: manual_procedural
        ref: "python -c \"import json;d=json.load(open('calibration.json'));g=d['mercado_grade'];assert g['layout']=='negociacao';assert g['linhas_por_pagina']==10;...\""
        status: pass
      - kind: unit
        ref: "tests/test_calibracao_mercado.py::TestACalibracaoREALDoUsuarioContinuaCarregando::test_os_13_moldes_e_as_3_ancoras_sobrevivem"
        status: pass
    human_judgment: true
    rationale: "O portao D-10 e humano por decisao travada: so o usuario sabe se o retangulo verde cai onde ele espera. Ele olhou o recorte ampliado das quatro colunas e respondeu por escrito: 'na verdade esse molde esta perfeito'. A pergunta feita foi explicita — se ele acompanha item com nome maior que `+6 Agathion Alpha Hunter Sealed` (31 caracteres) — e a resposta foi que esta perfeito."
  - id: D9
    description: "`mercado_limiar_do_cabecalho` gravado em 0.73, proposto pelo precedente `CASAMENTO_MINIMO_DA_ANCORA`"
    verification: []
    human_judgment: true
    rationale: "PROVISORIO por construcao. A confirmacao desta rodada e AUTORREFERENTE — o molde casou 1.0000 contra o proprio frame de onde foi cortado, o que da ~1,0 por construcao e nao prova nada sobre casar OUTRO frame. A confirmacao real e o portao de layout do 02-04 Task 3, rodando o molde contra bandas de negociacao em duas ordenacoes e contra Adena e busca. Se nao separar la, volta para ca."

duration: 8h 14m
completed: 2026-08-30
status: complete
---

# Phase 02 Plan 01: A superficie de calibracao da leitura de pagina Summary

**14 chaves opcionais em `calibration.json` sem bump de esquema, quatro colunas propostas por cruzamento de duas medicoes independentes, molde de cabecalho sem a seta de ordenacao com corte de brilho medido em 222 — e o `calibration.json` da maquina do usuario recalibrado para a grade de negociacao pela mao dele**

## Performance

- **Duration:** 8h 14m de relogio, dos quais ~55 min de trabalho e o resto parado no portao humano da Task 3
- **Started:** 2026-08-30T02:25:04Z
- **Completed:** 2026-08-30T10:39:00Z
- **Tasks:** 3 (2 auto/TDD + 1 checkpoint human-action)
- **Files modified:** 9 (3 de producao, 3 de teste, 3 fixtures)

## Accomplishments

- **As 14 chaves novas entram sem uma linha de migracao.** Todas por `.get`, todas opcionais, `VERSAO_DO_ESQUEMA` intacta em 2 — o `calibration.json` do usuario, com 13 moldes de glifo e 3 ancoras que so a mao dele produz, carrega igual. Cada uma e conferida no portao de carga em tipo e faixa, com `bool` excluido do `int` e toda mensagem terminando no conserto.
- **A ferramenta propoe as quatro colunas e o usuario confirma.** A proposta so existe quando DUAS medicoes independentes concordam: os rotulos do cabecalho (depois de a seta sair pelo corte de brilho) dizem onde cada coluna comeca, e o conteudo das linhas diz onde cada numero esta. Discordando, `sugerir_as_colunas` devolve `{}` e a janela abre vazia.
- **O molde do cabecalho sai sem a seta de ordenacao, e o corte que a remove foi medido no frame.** 222 nas duas fixtures, entre a seta (190) e os rotulos (237). Rodado contra o mesmo painel ordenado por `Goods` e por `Unit price`, o conjunto de grupos e IDENTICO — que e a propriedade que D-11 pede.
- **O passo da watchlist saiu do fluxo.** `ler_watchlist` e `matriz_de_confusao` ficam no arquivo como precedente medido, sem chamador. No lugar, uma linha de resumo dizendo que o nome do item passou a ser lido por OCR.
- **Tres fixtures de negociacao nascem aqui**, cortadas de `recordings/` e versionadas, porque e aqui que sao afirmadas pela primeira vez. Os planos 02-02..02-06 consomem estas; nenhum outro as corta de novo.
- **O `calibration.json` do usuario descreve a grade de negociacao**, com `linhas_por_pagina == 10` e `altura == 450 == 10 x 45` exatos.

## Task Commits

1. **Task 1 (RED): as 14 chaves de mercado, afirmadas antes de existirem** - `4d3dfe6` (test)
2. **Task 1 (GREEN): as 14 chaves entram por `.get`, sem migracao** - `635c365` (feat)
3. **Task 2 (RED): as quatro colunas e o molde do cabecalho, afirmados antes de existirem** - `b5d6173` (test)
4. **Task 2 (GREEN): a ferramenta marca as quatro colunas e corta o molde do cabecalho** - `3e019f1` (feat)
5. **Task 2 (fix): o fim do icone sai da SATURACAO, e nao de um corte no perfil** - `e4715f4` (fix)

**Task 3** nao tem commit de codigo: e o portao humano. O que ela produziu foi o `calibration.json` da maquina do usuario, que e **gitignored e nunca entra em commit**.

## Files Created/Modified

- `l2scanner/calibracao.py` - os 14 campos na dataclass, serializacao em `salvar`, `.get` em `carregar`, e `_conferir_as_chaves_da_leitura_de_pagina` com os helpers de faixa
- `l2scanner/mercado_visao.py` - `cabecalho_de_calibracao`, no molde inteiro de `glifos_de_calibracao`
- `l2scanner/calibrar_mercado.py` - `_corte_pelo_maior_vao`, `retangulo_da_banda_do_cabecalho`, `grupos_do_cabecalho`, `medir_o_corte_de_brilho_do_cabecalho`, `sugerir_o_molde_do_cabecalho`, `_fim_do_icone`, `_borda_votada`, `sugerir_as_colunas`, `sugerir_a_coluna_do_nome`, `conferir_a_coluna_na_grade`, `_grade_do_desenho`, `_cortar_o_cabecalho`; fluxo de `calibrar()` com 10 marcacoes; watchlist aposentada
- `tests/test_calibracao_mercado.py` - 112 asserções para as 14 chaves, incluindo a calibracao REAL do usuario atras de `pytest.skip`
- `tests/test_mercado_visao.py` - o desempacotamento do molde de cabecalho como entrada nao confiavel
- `tests/test_calibrar_mercado.py` - as colunas, o corte de brilho, o par de ordenacoes, a recusa fora da grade e a aposentadoria da watchlist
- `tests/fixtures/mercado/janela_negociacao_f010.png` - a janela inteira de `pagina-cheia/frame_000010` (tooltip sobre 4 linhas, de proposito)
- `tests/fixtures/mercado/cabecalho_negociacao_goods.png` - a banda de `063752/frame_000000`, ordenada por `Goods`
- `tests/fixtures/mercado/cabecalho_negociacao_unitprice.png` - a banda de `063752/frame_000020`, ordenada por `Unit price`

## Decisions Made

- **A coluna do nome termina no rotulo `Quantity`, nao no texto.** Medir pela pagina daria 263 px — os dez nomes deste frame sao o mesmo item. O 270 px do plano virou PISO afirmado em teste; o valor medido e 324 px, com 157 px de sobra a direita do nome mais longo da pagina.
- **O fim do icone sai da saturacao.** Brilho acha TEXTO; saturacao acha ARTE. Icone 84–255, texto do painel 0–12. Duas medianas entre as linhas, cada uma contra um ruido da tooltip.
- **Colunas contadas a partir da DIREITA.** Da esquerda a contagem quebra quando o icone e o nome se fundem; da direita as quatro colunas de numero sao sempre as mesmas.
- **`VERSAO_DO_ESQUEMA` nao subiu, e isso e a decisao mais cara do plano** — um bump teria feito o portao de versao recusar o arquivo do usuario.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Os arquivos de teste que o plano nomeia nao existem com aqueles nomes**
- **Found during:** Task 1
- **Issue:** O plano manda escrever em `tests/test_calibracao.py`; esse arquivo nao existe. O `read_first` dele o descreve como "onde os testes das chaves irmas ja moram" — e esse arquivo e `tests/test_calibracao_mercado.py`. `tests/test_mercado_visao.py`, citado no `<verify>`, tambem nao existia.
- **Fix:** Os testes das 14 chaves foram para `tests/test_calibracao_mercado.py`, ao lado das irmas; `tests/test_mercado_visao.py` foi criado, exatamente como o `<verify>` do plano espera.
- **Files modified:** tests/test_calibracao_mercado.py, tests/test_mercado_visao.py
- **Verification:** `pytest tests/test_calibracao_mercado.py tests/test_mercado_visao.py -q` — 126 passed
- **Committed in:** `4d3dfe6`, `635c365`

**2. [Rule 1 - Bug] A largura da coluna do nome nao podia ser 270 px fixos**
- **Found during:** Task 2
- **Issue:** O plano pede "cobre 270 px de largura no frame de pagina cheia". Medir a coluna pelo TEXTO desta pagina da 263 px — todos os dez nomes sao o mesmo `Earth Spirit Evolution Stone`, e nome e alinhado a esquerda e de comprimento variavel. Prender 270 px teria reproduzido o modo de falha que o proprio plano cita: nome longo truncado.
- **Fix:** 270 px virou PISO afirmado em teste (`assert largura >= 270`), e o limite direito real e o comeco do rotulo `Quantity` no cabecalho — o pixel mais a esquerda que aquela coluna chega a desenhar. Medido: 324 px nas tres fixtures.
- **Files modified:** l2scanner/calibrar_mercado.py, tests/test_calibrar_mercado.py
- **Verification:** `TestASugestaoDaColunaDoNome` — largura 324, `x + largura <= grade + 428` (onde a quantidade comeca)
- **Committed in:** `3e019f1`

**3. [Rule 1 - Bug] O cruzamento por contagem de grupos recusava frames validos**
- **Found during:** Task 2, rodando a ferramenta de ponta a ponta contra um frame real
- **Issue:** A primeira versao exigia `len(grupos_da_linha) == len(rotulos) + 1` (o icone mais uma coluna por rotulo). Em `063752/frame_000000` o icone e o nome se FUNDEM num grupo so — o vao entre eles tem 5 px, contra 13 px em `pagina-cheia/frame_000010` — e a ferramenta recusava propor qualquer coisa. Depois, medir o fim do icone por corte automatico no perfil de saturacao (maior vao e Otsu, os dois tentados) pousava no miolo escuro do icone (84–107 entre bordas de 193–255) e devolvia 22 onde a resposta e 42, deixando metade do icone dentro do recorte que vai para o OCR.
- **Fix:** Colunas de numero contadas a partir da DIREITA, com `Buy` de ancora; cruzamento passou a ser "cada numero cai depois do SEU rotulo e antes do seguinte"; e o fim do icone passou a sair da saturacao, com referencia medida nas colunas de numero da mesma linha (texto puro, sem arte) e mediana entre as linhas contra o ruido da tooltip. As duas refutacoes ficaram escritas na docstring de `_fim_do_icone`, no padrao de `ocr.py:36-39`.
- **Files modified:** l2scanner/calibrar_mercado.py, tests/test_calibrar_mercado.py
- **Verification:** medido em 3 frames de 2 gravacoes; nome com 324 px nos tres. `assert x >= grade + 43` prende a regressao do miolo do icone.
- **Committed in:** `e4715f4`

**4. [Rule 2 - Missing Critical] O texto final da conferencia descrevia uma imagem que nao era mais a gravada**
- **Found during:** Task 2
- **Issue:** `_texto_final_da_conferencia` mandava o usuario conferir "a faixa de titulo, o X de fechar, a seta de rolagem, a area da lista e a primeira linha" — cinco regioes, quando a imagem passou a ter dez. E o defeito exato que o STATE.md ja registra como encontrado em campo em 2026-08-29 ("a mensagem final descrevendo uma imagem que nao era a gravada").
- **Fix:** O texto passa a citar as quatro colunas e o cabecalho, e diz o que mais importa olhar: a coluna do nome cobrindo o nome mais longo inteiro.
- **Files modified:** l2scanner/calibrar_mercado.py
- **Verification:** `TestOTextoFinalDaConferencia` segue verde
- **Committed in:** `e4715f4`

### Fora de escopo — registrado e NAO corrigido

**5. `ruff` acusa 24 erros pre-existentes** em arquivos que este plano nao toca (`l2scanner/visao.py` com `E741`, `tests/test_voce_na_party.py` com `F401`, entre outros). Os seis arquivos deste plano passam limpos. Nao foram corrigidos por disciplina de escopo.

## Issues Encountered

### O INCIDENTE: `calibrar.bat` apagou toda a calibracao de mercado (janela quebrada 13)

Durante a execucao deste plano, o `calibration.json` real foi **sobrescrito as 00:08:24** por uma execucao da calibracao de **PARTY**. Perderam-se `mercado_templates_de_digito` (13 moldes), `mercado_ancoras` (3), `mercado_grade` e `mercado_limiar_de_glifo` — todos viraram `null`. A party ficou intacta e recem-remedida.

**Causa, e ela e PRE-EXISTENTE e FORA DO ESCOPO deste plano:** `l2scanner/calibrar.py::calibrar_selecionando` monta uma `Calibracao` do ZERO (`calibrar.py:353`, sem nenhum campo `mercado_*`) e o fluxo a grava por cima do arquivo inteiro (`calibrar.py:1244`). E a gemea exata do CR-04 — o unico caminho do projeto que apagava calibracao sem perguntar —, ja consertado do lado do mercado e nunca do lado da party. `l2scanner/calibrar.py` nao foi tocado por este plano (ultimo commit dele: `05696e5`, anterior ao primeiro commit desta execucao).

**Como foi descartado que a suite ou este plano causaram:** o arquivo danificado foi restaurado como canario, a suite inteira foi rodada e o md5 nao mudou (`f603100e540b5522c6b0e6ba6008bb04` antes e depois). Todas as execucoes deste plano passaram `calibracao=<caminho temporario>`.

**Registrado como janela quebrada 13** em `.planning/WINDOWS.md`, com chip aberto para o conserto.

**Recuperacao feita:** os 13 moldes originais foram resgatados e reinstalados. Dois arquivos de resgate ficaram na raiz do repositorio, **nao versionados**, e podem ser apagados agora que a recuperacao esta feita — **a decisao e do usuario, nao foram apagados por este plano**:

- `calibration.RESGATE-13-glifos.json` — os 13 moldes originais e o `mercado_limiar_de_glifo = 0.8554906845`
- `calibration.ANTES-DA-INSTALACAO.json` — o estado danificado, antes da instalacao da proposta
- `conferencia-ensaio-negociacao.png` — a imagem que o usuario olhou para aprovar

### As 3 ancoras gravadas sao NOVAS

As ancoras originais do usuario foram apagadas no incidente e nao havia copia delas. As tres gravadas agora (`titulo`, `botao_fechar`, `canto_inf_dir`) foram **recortadas automaticamente de `063752/frame_000000`**, e casaram 1.0000 naquele frame. **O usuario conferiu na imagem de conferencia e aprovou.** Sao mais baratas de refazer que os moldes de glifo — nao carregam rotulo digitado —, mas o fato de nao serem as dele fica registrado aqui.

### FLAKE conhecido e pre-existente

`tests/test_agenda.py` vazou um `KeyboardInterrupt` que abortou a sessao do pytest perto de ~88 testes em 3 das rodadas desta execucao. **Abortar nao e falhar** — nas rodadas completas o resultado foi 1824 passed, 2 skipped, duas vezes seguidas.

## Deferred Issues

- **`mercado_limiar_do_cabecalho = 0.73 e PROVISORIO.** Confirmado de forma AUTORREFERENTE nesta rodada (o molde casou 1.0000 contra o proprio frame de onde foi cortado, o que da ~1,0 por construcao). A confirmacao real e o portao de layout do **02-04 Task 3**, que o roda contra bandas de negociacao em duas ordenacoes e contra Adena e busca. Se nao separar la, volta para ca.
- **As 12 chaves ainda em `None`** (`mercado_sonda_do_fundo`, os quatro limiares de leitura, o corte e o piso de similaridade, `mercado_tolerancia_do_cruzamento`, `mercado_minimo_de_linhas_comparadas`) sao FEATURE OFF de proposito. Elas so recebem valor quando a ferramenta de medicao do **02-02** as medir. Nenhuma delas foi escolhida por este plano, e nenhuma pode ser.
- **`ruff`: 24 erros pre-existentes** fora dos arquivos deste plano.

## Verification

Rodado no checkout principal, contra o `calibration.json` REAL:

| criterio | comando | resultado |
|---|---|---|
| `<verify>` automated da Task 3 (literal do plano) | o `python -c` de 11 asserts do plano | **OK** `{'layout': 'negociacao', ..., 'linhas_por_pagina': 10}` |
| layout | leitura | `negociacao` |
| linhas_por_pagina | leitura | **10** |
| altura da grade | leitura | **450 = 10 x 45**, exato |
| as quatro colunas | `Calibracao.carregar` | nome `{dx:-385, largura:324}`, quantidade `{dx:-61, largura:123}`, total `{dx:62, largura:209}`, unitario `{dx:271, largura:174}` |
| cabecalho | `cabecalho_de_calibracao` | `30x944`, corte de brilho **222**, layout `negociacao`, dy 224, 28320 bytes — desserializa em `(30, 944)` |
| 13 moldes de glifo | `glifos_de_calibracao` | **13**: `0-9`, `,`, `XM Coin`, `Adena`; limiar 0.8554906845 |
| 3 ancoras | `ancoras_de_calibracao` | **3**: titulo, botao_fechar, canto_inf_dir |
| `mercado_templates_de_nome` | leitura | `None` |
| `VERSAO_DO_ESQUEMA` | leitura | **2** |
| bloco 1 do `<verification>` | `pytest test_calibracao_mercado test_mercado_visao test_calibrar_mercado test_mercado_glifos -q` | **312 passed** |
| FIRE-01 | `pytest tests/test_firewall_escopo.py -q` | **18 passed** — nenhuma dependencia nova |
| suite completa | `pytest -q` | **1824 passed, 2 skipped** (baseline 1704 + 120 novos), duas rodadas seguidas |

## User Setup Required

None - nenhuma configuracao de servico externo. O portao humano da Task 3 foi cumprido pelo usuario nesta execucao.

## Next Phase Readiness

**Pronto para o 02-02.** A superficie que a onda de medicao precisa existe e esta calibrada:

- as quatro colunas em deslocamento, para recortar contra o frame certo
- o molde do cabecalho com o corte de brilho, para o portao de layout do 02-04
- as 3 fixtures de negociacao versionadas, que os planos seguintes consomem sem cortar de novo
- as 12 chaves de limiar declaradas e validadas, esperando os numeros que so a medicao do 02-02 pode produzir

**Concerns:**

- `mercado_limiar_do_cabecalho` so se confirma no 02-04.
- A janela quebrada 13 (`calibrar.py` apagando o mercado) continua **aberta**: se o usuario recalibrar a party de novo antes do conserto, ele perde a calibracao de mercado outra vez. O resgate agora existe (`calibration.RESGATE-13-glifos.json`), mas ele nao e uma correcao.

## Self-Check: PASSED

Arquivos criados, conferidos com `[ -f ]`:
- `tests/test_mercado_visao.py` FOUND
- `tests/fixtures/mercado/janela_negociacao_f010.png` FOUND
- `tests/fixtures/mercado/cabecalho_negociacao_goods.png` FOUND
- `tests/fixtures/mercado/cabecalho_negociacao_unitprice.png` FOUND

Commits, conferidos com `git log --oneline --all`:
- `4d3dfe6` FOUND
- `635c365` FOUND
- `b5d6173` FOUND
- `3e019f1` FOUND
- `e4715f4` FOUND

Criterios de aceitacao das tres tasks: re-rodados nesta sessao, todos PASS (tabela acima).

---
*Phase: 02-leitura-de-p-gina*
*Completed: 2026-08-30*
