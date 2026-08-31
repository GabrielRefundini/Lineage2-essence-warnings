---
phase: 04-modo-mercado-an-lise-e-console
plan: 01
subsystem: infra
tags: [modo-mercado, laco-de-producao, console, wgc, orcamento-de-tick, tripwire, detc-02, leit-04]

requires:
  - phase: 02-leitura-da-p-gina-do-world-exchange
    provides: "`LeitorDePagina`, `PaginaAceita`, os SETE contadores publicos e `Catalogo` — todos sem chamador de producao"
  - phase: 03-persist-ncia-de-observa-es
    provides: "`RegistroDeObservacoes` e `montar_registro_de_mercado`, deliberadamente sem chamador"
  - phase: 01-funda-o-firewall-gravador-e-spike-de-campo
    provides: "`JanelaSource` (WGC), `configurar_log`, e o padrao de montagem que falha para o lado certo"
provides:
  - "`l2scanner/mercado_modo.py` com `laco_do_mercado(args, cal, *, fonte, ler_texto, ler_texto_conferencia, relogio, pasta, ticks_maximos)`: os portoes de arranque que RECUSAM a subir (codigo 2), a fiacao dos tres fios, o tick com cadencia compensada e o desligamento com gravacao atomica"
  - "`l2scanner/mercado_console.py`: `linha_ao_vivo`, `resumo_da_sessao`, `transicao_do_painel`, `acumular_motivos` e `OrcamentoDoTick` — todas DEVOLVEM texto e nenhuma imprime"
  - "`pecas_de_calibracao_de_mercado_faltando(cal)` em `l2scanner/mercado_pagina.py`: a verdade UNICA sobre 'calibrado para mercado', 15 chaves num lugar so"
  - "`montar_catalogo_de_mercado(pasta=None)` em `l2scanner/__main__.py`, no trilho de `montar_registro_de_mercado`"
  - "`minimum_update_interval` opcional em `JanelaSource`, padrao `None` — a unica alavanca real de DETC-02"
  - "A flag `--mercado` no `__main__.py`, com `parser.error` exigindo `--janela`"
  - "`tests/test_mercado_firewall_de_fase.py`: o tripwire simetrico ao de `test_mercado_27x.py`"
affects: [04-02, 04-03, 04-04, 04-05, DETC-02, LEIT-04, ANAL-01, ANAL-02, ANAL-03, ANAL-04]

actuals:
  tokens: 22560
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Portao de arranque que RECUSA a subir quando a feature E o produto, em contraste com a montagem que degrada quando a feature e opcional"
    - "Estado derivado de contador publico (`ticks_com_painel_aberto` entre duas voltas) em vez de espiar atributo privado do colaborador"
    - "Funcoes de console que DEVOLVEM texto, afirmaveis sem capturar stdout"
    - "Assercao de arquitetura sobre o AST (imports, docstrings arrancadas) em vez de varredura de substring sobre o fonte cru"

key-files:
  created:
    - l2scanner/mercado_modo.py
    - l2scanner/mercado_console.py
    - tests/test_mercado_modo.py
    - tests/test_mercado_firewall_de_fase.py
    - .planning/workstreams/mercado/phases/04-modo-mercado-an-lise-e-console/deferred-items.md
  modified:
    - l2scanner/mercado_pagina.py
    - l2scanner/__main__.py
    - l2scanner/captura_janela.py
    - tests/test_gerar_observacoes_do_censo.py

key-decisions:
  - "`_modulo_do_arranque()` resolve as montadoras por `sys.modules['__main__']` antes de cair no import de `l2scanner.__main__`. Por `python -m l2scanner` o arquivo do arranque JA esta carregado sob o nome `__main__`, e um `from .__main__ import ...` o executaria uma SEGUNDA vez sob outro nome de logger — as duas mensagens de erro que o PERS-03 exige que o usuario VEJA sairiam num logger sem manipulador nenhum"
  - "`_garantir_log` e CONDICIONAL, contra a letra do plano: `main()` ja chamou `configurar_log(args.verboso)` antes de chegar ao `if args.mercado`, e chamar de novo acrescentaria um segundo `RotatingFileHandler` e um segundo `StreamHandler` — toda linha da sessao sairia duas vezes"
  - "`relogio=None` entrou na assinatura, alem dos parametros que o plano listou. Sem ele o teste ponta a ponta chamaria `montar_relogio(args)`, que le o `.env` do usuario e, quando ele existe, faz round-trip HTTP no Chatwoot dentro da suite"
  - "`pecas_de_calibracao_de_mercado_faltando` carrega QUINZE chaves, e nao quatorze: `_calibrado` sempre conferiu DOZE e nao onze. Os comentarios do 02-05 e do 02-07 numeram a 'decima' e a 'decima primeira' sem contar `mercado_grade`, e o plano herdou a conta errada. A correcao esta escrita na docstring da funcao"
  - "`_calibrado` continua conferindo as duas pecas DECODIFICADAS (`_moldes` e `_molde_do_cabecalho`) por cima da funcao de modulo: a funcao le o `calibration.json` cru, e um molde de cabecalho presente mas com hex CORROMPIDO passa por ela e chega ao leitor como `None`"
  - "O estado do painel sai da DIFERENCA de `leitor.ticks_com_painel_aberto` entre duas voltas, em vez de um atributo privado do leitor. O latch de transicao trata a primeira volta como transicao, para o usuario ver que o modo esta vivo e nao esta achando nada — silencio e indistinguivel de travamento"
  - "Os motivos sao acumulados TODO TICK a partir de `leitor.ultima_leitura`, e nao so quando a pagina e aceita: a leitura recusada e justamente a que carrega o motivo, e ler so as aceitas esconderia a metade perdida do LEIT-04"
  - "O `rich` continua fora por DOUTRINA DE ZERO-INSTALL, e a justificativa errada do CONTEXT (que o FIRE-01 o barraria) esta corrigida por escrito no cabecalho de `mercado_console.py`: a banlist do FIRE-01 e so de sintese de input e nao alcanca uma biblioteca de console"

patterns-established:
  - "Quando um modulo do pacote precisa de uma funcao do `__main__.py`, resolve-la por `sys.modules['__main__']` com fallback de import — nunca `from .__main__ import`, que duplica o modulo sob `python -m`"
  - "Tripwire de arquitetura por AST: imports lidos da arvore (inclusive os adiados dentro de funcao), `__module__` dos nomes do namespace, e substring so sobre o CODIGO com as docstrings arrancadas"
  - "Assercao de valor em texto com fronteira de palavra (`\\b7\\b`), depois que 7 e 17 na mesma tela mostraram que `str(valor) in texto` aprova por engano"

requirements-completed: [DETC-02, LEIT-04]

coverage:
  - id: D1
    description: "`--mercado` sobe como TERCEIRA invocacao, exige `--janela`, e nao vigia party nem envia alerta"
    requirement: "DETC-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestOsTresFiosLigados::test_a_linha_de_arranque_diz_o_orcamento_e_a_separacao"
        status: pass
      - kind: manual
        ref: "`python -m l2scanner --mercado` sem `--janela` sai pelo `parser.error` com a razao por extenso"
        status: pass
    human_judgment: false
  - id: D2
    description: "Sem OCR ou sem calibracao de mercado o modo NAO SOBE: sai com codigo 2, nomeia a chave que falta e manda rodar `calibrar-mercado.bat`. Sem calibracao ele nem toca o disco"
    requirement: "DETC-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestORecusaDeSubir::test_sem_calibracao_de_mercado_o_modo_devolve_2_e_diz_o_que_falta"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestORecusaDeSubir::test_sem_calibracao_o_modo_nao_escreve_arquivo_nenhum"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestORecusaDeSubir::test_layout_de_outra_aba_devolve_2_e_diz_qual_esta_gravado"
        status: pass
    human_judgment: false
  - id: D3
    description: "Uma pagina aceita produz linha no `.mercado/observacoes.csv` E linha no `.mercado/catalogo-de-nomes.csv` na MESMA sessao — os tres fios ligados"
    requirement: "DETC-02"
    verification:
      - kind: integration
        ref: "tests/test_mercado_modo.py::TestOsTresFiosLigados::test_uma_sessao_grava_nos_DOIS_arquivos"
        status: pass
    human_judgment: false
  - id: D4
    description: "A verdade UNICA sobre 'calibrado para mercado': as quinze chaves num lugar so, cada uma sozinha detectada, e a folga de cola deliberadamente FORA"
    requirement: "DETC-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestAsPecasDeCalibracao"
        status: pass
    human_judgment: false
  - id: D5
    description: "`montar_catalogo_de_mercado` devolve `None` e NAO levanta com a pasta ocupada por um ARQUIVO, com DUAS mensagens em ERROR"
    requirement: "DETC-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestMontarCatalogoDeMercado::test_a_pasta_ocupada_por_um_ARQUIVO_devolve_None_e_nao_levanta"
        status: pass
    human_judgment: false
  - id: D6
    description: "`minimum_update_interval` padrao `None` mantem o caminho da party byte-identico, e `250` chega mesmo a `WindowsCapture`"
    requirement: "DETC-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_firewall_de_fase.py::TestAAlavancaDeDETC02"
        status: pass
    human_judgment: false
  - id: D7
    description: "O acoplamento esta preso nas DUAS direcoes: o rastreador nao conhece o mercado (02) e o mercado nao USA a party — por import lido do AST, por namespace em memoria, e por execucao com `Rastreador` substituido por um objeto que levanta"
    requirement: "DETC-02"
    verification:
      - kind: unit
        ref: "tests/test_mercado_firewall_de_fase.py::TestOMercadoNaoConheceORastreador"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_27x.py::TestORastreadorNaoLeOMercado"
        status: pass
    human_judgment: false
  - id: D8
    description: "O console mostra ao vivo as DUAS metades e o ultimo item, e continua mostrando a perdida quando a lida e zero"
    requirement: "LEIT-04"
    verification:
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestALinhaAoVivo"
        status: pass
    human_judgment: false
  - id: D9
    description: "O resumo final conta as duas metades, os sete contadores, as tres contagens de escrita que nao se somam, e os motivos agregados por SESSAO com as CONSTANTES de `mercado_leitura`"
    requirement: "LEIT-04"
    verification:
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestOResumoDaSessao"
        status: pass
    human_judgment: false
  - id: D10
    description: "O resumo imprime p50/p95/maximo do tempo de tick e quantos ticks estouraram o orcamento, medidos pela MESMA conta que compensa a deriva da cadencia"
    requirement: "LEIT-04"
    verification:
      - kind: unit
        ref: "tests/test_mercado_modo.py::TestOResumoDaSessao::test_o_orcamento_traz_p50_p95_maximo_e_estouros"
        status: pass
    human_judgment: false
  - id: D11
    description: "Painel fechado por seis ticks produz EXATAMENTE uma linha de transicao — nem seis (spam) nem zero (silencio indistinguivel de travamento)"
    requirement: "LEIT-04"
    verification:
      - kind: integration
        ref: "tests/test_mercado_modo.py::TestOAntiSpamDoPainelFechado::test_painel_fechado_por_varios_ticks_da_UMA_linha_de_transicao"
        status: pass
    human_judgment: false
  - id: D12
    description: "`l2scanner/rastreador.py` e `l2scanner/visao.py` continuam sem uma linha de diff, e `requirements.txt` nao mudou"
    requirement: "DETC-02"
    verification:
      - kind: manual
        ref: "`test -z \"$(git diff --stat 3ff6869 -- l2scanner/rastreador.py l2scanner/visao.py)\" || { echo REPROVADO; exit 1; }` — exit 0"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_firewall_de_fase.py::TestNenhumaDependenciaNova::test_o_requirements_nao_ganhou_linha_nesta_fase"
        status: pass
    human_judgment: false
  - id: D13
    description: "Contencao real entre TRES processos (duas partys mais `--mercado`) por 10 minutos com o mercado aberto: CPU aceitavel, nenhuma linha nova de falha de captura nos dois `scanner.log` de party, nenhuma borda amarela na janela do jogo"
    requirement: "DETC-02"
    verification: []
    human_judgment: true
    rationale: "Contencao entre processos e propriedade do SISTEMA (CPU, GPU, sessoes WGC, agendador do Windows) e nenhum teste automatizado a alcanca. O que o programa pode afirmar sobre si mesmo — o orcamento de tick auto-medido — foi entregue em D10, e o resumo diz por escrito que ele nao fecha este criterio."
  - id: D14
    description: "O OCR REAL rodando DENTRO do tick, e o congelamento provocado (cobrir ou pausar a janela e ver o aviso aparecer e sumir) — as duas conferencias humanas herdadas da Fase 2"
    requirement: "LEIT-04"
    verification: []
    human_judgment: true
    rationale: "A suite roda no Python GLOBAL, que nao tem as bindings WinRT, e o replay usa OCR REPRODUZIDO de `leituras_de_nome.json`. O motor de verdade dentro do laco e o congelamento de captura de verdade so existem ao vivo."

duration: 16min
completed: 2026-08-31
status: complete
---

# Phase 04 Plan 01: O modo `--mercado` Summary

**Os tres fios que as Fases 2 e 3 deixaram sem chamador ganharam um processo que os liga: `--mercado` sobe como terceira invocacao, recusa a subir sem OCR ou sem calibracao dizendo exatamente qual chave falta, le a pagina do World Exchange a 1 Hz, grava a serie no catalogo de nomes E a observacao no CSV na mesma sessao, e conta honestamente as duas metades do que viu — com o orcamento de tick que ele mesmo mediu.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-08-31T03:30:00-03:00
- **Completed:** 2026-08-31T03:46:00-03:00
- **Tasks:** 3 (1 tracer + 2 TDD, RED -> GREEN cada)
- **Commits:** 5
- **Files:** 5 criados, 4 modificados

## Accomplishments

### Task 1 — o caminho unico (tracer), commit `c7932e2`

- **`pecas_de_calibracao_de_mercado_faltando(cal)`** virou a verdade UNICA sobre
  "calibrado para mercado". Antes havia duas: as doze chaves que
  `LeitorDePagina._calibrado` conferia por tick, e outras tres que so o arranque
  do scanner conferia, em tres lugares diferentes do `__main__.py`. Agora sao
  quinze num lugar so, com a razao de cada uma na docstring. `_calibrado` chama a
  funcao e mantem intactos o latch `_falta_ja_avisada` e o texto do aviso — mais
  a conferencia das duas pecas DECODIFICADAS, que a funcao (que le o JSON cru)
  nao alcanca.
- **`montar_catalogo_de_mercado(pasta=None)`** no `__main__.py`, no trilho
  identico ao de `montar_registro_de_mercado`: `try` em volta do construtor
  INTEIRO (o `mkdir` do `Catalogo.__init__` roda fora de qualquer rede e levanta
  `FileExistsError` com o nome ocupado por arquivo), `except OSError` estreito,
  duas mensagens em ERROR, `return None`, nunca `raise`.
- **`l2scanner/mercado_modo.py`** com `laco_do_mercado`: portoes de arranque que
  RECUSAM a subir com codigo 2, linha de arranque contando o orcamento, fiacao na
  ordem em que os destinos de escrita vem antes da captura, tick com cadencia
  compensada, e `finally` com `fonte.fechar()` mais a gravacao ATOMICA do
  catalogo (tambem a cada 20 paginas, porque um `taskkill` nao roda `finally`).
- **`--mercado` no `__main__.py` disputado**, em 54 linhas acrescentadas e ZERO
  removidas — teto do plano era 70.

### Task 2 — a alavanca de DETC-02, commits `eef6f9d` (RED) e `4981539` (GREEN)

- **`minimum_update_interval` opcional em `JanelaSource`**, padrao `None`. O
  padrao E o contrato: o caminho da party continua byte-identico, e ha teste
  prendendo a assinatura e — pelo AST — a passagem do parametro na chamada de
  `WindowsCapture`.
- **`MS_ENTRE_FRAMES_DO_MERCADO = 250`**, usada so na `JanelaSource` do mercado.
  A constante carrega as duas razoes por extenso: os ~9,5x menos copia que ela
  compra (273 MB/s DERIVADO de 38 fps x 7,2 MB, e escrito que e derivado), e o
  motivo de nao ser 1000 — com atualizacao e leitura ambas a ~1000 ms a deriva de
  fase entregaria o mesmo buffer tres vezes, `JANELAS_IGUAIS_PARA_CONGELAR`
  dispararia e o console anunciaria captura congelada com o jogo vivo.
- **`tests/test_mercado_firewall_de_fase.py`**, o tripwire simetrico ao de
  `test_mercado_27x.py`, com a docstring dizendo o que ele NAO consegue afirmar.

### Task 3 — LEIT-04 inteiro, commits `1602b8a` (RED) e `b8e8f8b` (GREEN)

- **`l2scanner/mercado_console.py`**, texto puro, sem dependencia nova. As
  funcoes devolvem texto e nunca imprimem.
- **`linha_ao_vivo`**: lidas, perdidas, gravadas e o ultimo item. Nunca so a
  metade boa. NAO mostra `residuo_do_cruzamento` — a guarda esta desligada por
  medicao, o residuo e observacao e nao veredito, e ele ja esta em coluna propria
  no CSV.
- **`resumo_da_sessao`**: os sete contadores do leitor, as tres contagens de
  escrita que NAO se somam, os motivos agregados por SESSAO com as CONSTANTES de
  `mercado_leitura.py` (nunca a palavra "gramatica" do CONTEXT), e o orcamento
  auto-medido — com o paragrafo dizendo que contencao entre tres processos e
  propriedade do SISTEMA.
- **Anti-spam por LATCH**: painel fechado e o estado normal e majoritario de um
  farm; uma linha por tick seriam 3.600 por hora.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `from .__main__ import` executaria o arranque duas vezes**

- **Found during:** Task 1, ao fiar `montar_registro_de_mercado`.
- **Issue:** por `python -m l2scanner`, o arquivo do arranque esta em
  `sys.modules` sob o nome `__main__`. Um `from .__main__ import ...` faria o
  Python importa-lo de novo como `l2scanner.__main__`, reexecutando o arquivo
  inteiro. O `log` da copia tem OUTRO nome de logger e nenhum dos manipuladores
  que `configurar_log` instalou — as duas mensagens de erro que o PERS-03 exige
  que o usuario VEJA sairiam para lugar nenhum.
- **Fix:** `_modulo_do_arranque()` pergunta por CAPACIDADE
  (`hasattr(sys.modules['__main__'], 'montar_registro_de_mercado')`) e so cai no
  import quando o `__main__` e outro programa (teste, ferramenta de bancada).
- **Commit:** `c7932e2`

**2. [Rule 2 - Faltava] `configurar_log` incondicional duplicaria toda linha**

- **Found during:** Task 3, item (f) do plano.
- **Issue:** o plano mandava chamar `configurar_log` antes de qualquer log do
  modo, copiando `gerar_observacoes_do_censo.py`. Mas la a ferramenta e o ponto
  de entrada; aqui o ponto de entrada e `main()`, que JA chamou
  `configurar_log(args.verboso)` antes do `if args.mercado`. A segunda chamada
  acrescentaria um `RotatingFileHandler` e um `StreamHandler` a mais, e toda
  linha da sessao sairia duas vezes no console e duas no arquivo.
- **Fix:** `_garantir_log(principal)` so configura quando nao ha manipulador nem
  na raiz nem no logger do arranque. A intencao do item (f) — nenhuma mensagem
  sem manipulador — fica intacta.
- **Commit:** `b8e8f8b`

**3. [Rule 3 - Bloqueio] `montar_relogio(args)` faria a suite bater na rede**

- **Found during:** Task 1, ao escrever o teste ponta a ponta.
- **Issue:** sem `.env` a montagem degrada offline; COM `.env` (o caso da maquina
  do usuario) ela monta `fonte_chatwoot` e faz `sincronizar()`, que e round-trip
  HTTP dentro do teste.
- **Fix:** `relogio=None` entrou na assinatura, na mesma disciplina de injecao
  que o plano ja adotara para `fonte`, `pasta` e as leitoras. Producao nao passa.
- **Commit:** `c7932e2`

**4. [Rule 1 - Bug] `test_a_ferramenta_nao_acrescenta_flag_ao_scanner` afirmava o calendario**

- **Found during:** Task 2, na suite completa.
- **Issue:** o teste do 03-03 afirmava que `"--mercado"` NAO aparecia no
  `__main__.py`, porque quando foi escrito o modo era Fase 4 e nao existia. A
  Task 1 o criou, e o teste ficou vermelho afirmando uma verdade sobre a data e
  nao sobre a ferramenta.
- **Fix:** trocado pelo que ele sempre quis dizer — a flag desce para o LACO DE
  PRODUCAO e nunca para a ferramenta de bancada — mais um teste novo prendendo a
  assimetria que importa: `--saida` continua obrigatorio na ferramenta, e o modo
  ao vivo nao tem `add_argument` nenhum.
- **Files modified:** `tests/test_gerar_observacoes_do_censo.py`
- **Commit:** `4981539`

### Correcoes de criterio do plano (nao sao bugs — sao criterios que caem)

**5. A contagem de chaves: sao QUINZE, nao quatorze**

O plano dizia "as onze chaves que `_calibrado` ja confere" mais tres = quatorze.
`_calibrado` sempre conferiu DOZE: os comentarios do 02-05 e do 02-07 numeram a
"decima" e a "decima primeira" sem contar `mercado_grade`, que entra na
conferencia assim mesmo, e o plano herdou a conta. A funcao carrega quinze e a
correcao esta escrita na docstring dela.

**6. `inspect.getsource(mercado_modo)` nao pode banir as quatro palavras**

O criterio literal e insatisfazivel por TRES colisoes, nao uma: `mercado_visao` e
um modulo DO MERCADO e e de onde vem `RastreioDoPainel`; `sessao` aparece na
prosa obrigatoria do proprio plano e no nome `resumo_da_sessao`; e o cabecalho de
`mercado_modo.py` EXPLICA o firewall nomeando os quatro modulos — um teste de
substring reprovaria a documentacao do firewall. A prova virou tres camadas, cada
uma mais forte que a varredura de texto: imports lidos do AST (inclusive os
adiados dentro de funcao), `__module__` de cada nome do namespace, e substring
sobre o CODIGO com as docstrings arrancadas, para `rastreador` e `presenca`, que
nao tem homonimo. A mesma tecnica resolveu o `grep -n "residuo"` de
`linha_ao_vivo`: o codigo nao o cita, a docstring explica por que.

**7. "importar o mercado nao traz `rastreador` para `sys.modules`" e FALSO hoje**

E nao por culpa desta fase. A cadeia e `mercado_pagina` -> `mercado_catalogo` ->
`config` (uma linha, so para pegar `RAIZ`) -> `notificador` -> `rastreador` ->
`visao`, e existe desde a Fase 2. Corta-la exigiria mexer em `config.py` e
`notificador.py` (fora do escopo deste plano) e em `rastreador.py` (intocavel).
O teste foi INVERTIDO: ele agora PRENDE a cadeia preexistente, com a explicacao
no corpo, para que quem a cortar um dia atualize a historia. Registrado em
`deferred-items.md` com o conserto plausivel e o "o que NAO fazer".

## Known Stubs

Nenhum. Nao ha valor vazio codificado, texto de "coming soon" nem componente sem
fonte de dado: o laco escreve nos dois arquivos de verdade, e ha teste ponta a
ponta lendo as linhas do disco.

## Threat Flags

Nenhuma superficie nova alem da que o `<threat_model>` do plano ja previu. O modo
nao abre porta de rede, nao le entrada do usuario alem do `calibration.json` (que
ja era fronteira mapeada, T-04-01) e escreve so nos dois arquivos de `.mercado/`,
pela pasta de producao resolvida em tempo de chamada e sem flag de destino
(T-04-03, conferido por teste: `add_argument` nao aparece em `mercado_modo.py`).

## Verification Results

| Criterio `<automated>` | Resultado |
|---|---|
| `pytest tests/test_mercado_modo.py tests/test_mercado_pagina.py -x -q` | 96 passed |
| `pytest tests/test_mercado_replay.py tests/test_mercado_27x.py tests/test_mercado_registro.py tests/test_mercado_catalogo.py -x -q` | 243 passed, 10 skipped |
| `test -z "$(git diff --stat -- rastreador.py visao.py)" \|\| REPROVADO` | exit 0 — APROVADO |
| `pytest tests/test_mercado_firewall_de_fase.py tests/test_mercado_27x.py tests/test_firewall_escopo.py -x -q` | 52 passed, 2 skipped |
| `pytest tests/test_rastreador.py tests/test_party_estavel.py -x -q` | 56 passed |
| `test -z "$(git diff -- requirements.txt)" \|\| REPROVADO` | exit 0 — APROVADO |
| `pytest tests/test_mercado_modo.py -x -q` | 38 passed |
| `pytest tests/test_mercado_pagina.py tests/test_mercado_leitura.py -x -q` | 214 passed |
| `test -z "$(git status --porcelain calibration.json)" \|\| REPROVADO` | exit 0 — APROVADO |
| `test "$(git diff --numstat -- __main__.py \| cut -f1)" -le 70` | 54 <= 70 — APROVADO |
| `python -c "...JanelaSource...minimum_update_interval...default is None"` | exit 0 — APROVADO |
| `python -c "...linha_ao_vivo.__doc__..."` | exit 0 — APROVADO |
| `grep -n "saida" mercado_modo.py` | nenhum `add_argument`, nenhum destino de linha de comando |
| `grep -n "residuo" mercado_console.py` | so na docstring de `linha_ao_vivo`, explicando a ausencia |

**Suite completa:** `pytest tests/ --ignore=tests/test_agenda.py -q` -> **2851
passed, 23 skipped**. `pytest tests/test_agenda.py -q` -> **145 passed**, sem o
`KeyboardInterrupt` conhecido nesta rodada.

A conta fecha com o verde de referencia do plano (2819 passed, 2 skipped): esta
arvore e um WORKTREE, onde `recordings/` nao se materializa, entao 21 testes que
la passam aqui pulam (2 + 21 = 23). Base desta arvore = 2851 - 53 novos = 2798;
2798 + 21 = 2819. Os 53 novos sao 52 nos dois arquivos desta fase mais 1 no
`test_gerar_observacoes_do_censo.py`.

## Human Gates Still Open

1. **Portao de campo do DETC-02** — as duas instancias de party mais `--mercado`
   por 10 minutos com o mercado aberto, conferindo CPU dos tres `python.exe`,
   ausencia de linha nova de falha de captura nos dois `scanner.log` de party, e
   ausencia de borda amarela na janela do jogo.
2. **As duas conferencias herdadas da Fase 2** — o OCR real DENTRO do tick (a
   suite usa OCR REPRODUZIDO), e o congelamento provocado: cobrir ou pausar a
   janela e ver o aviso aparecer, e sumir quando ela volta.

## Self-Check: PASSED

Dez arquivos afirmados, dez encontrados no disco. Cinco commits afirmados, cinco
encontrados em `git log`.
