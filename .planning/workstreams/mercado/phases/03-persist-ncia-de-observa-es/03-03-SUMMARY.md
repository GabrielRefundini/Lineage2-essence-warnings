---
phase: 03-persist-ncia-de-observa-es
plan: 03
subsystem: testing
tags: [replay, tools, csv, google-sheets, guarda-de-caminho, argparse, windows, normcase]

requires:
  - phase: 03-persist-ncia-de-observa-es
    provides: "`RegistroDeObservacoes` e a dedup por chave de conteudo (03-01), e `montar_registro_de_mercado` + `configurar_log` (03-02)"
  - phase: 02-leitura-de-p-gina
    provides: "`LeitorDePagina`, `PaginaAceita`, `LinhaLida` e o caminho publico do OCR (`ler_texto` / `ler_texto_ampliado`)"
  - phase: 01-funda-o-firewall-gravador-e-spike-de-campo
    provides: "`Relogio` ancorado, e o molde de `tools/` que passa gravacao real pelo pipeline para PRODUZIR DADO"
provides:
  - "`tools/gerar_observacoes_do_censo.py`: o replay que transforma as 8 gravacoes do censo num `observacoes.csv` com dado real, com relatorio no fim"
  - "`razao_para_recusar_a_saida`: a guarda MECANICA que recusa a pasta de producao (e qualquer subpasta dela) por comparacao de caminhos RESOLVIDOS, antes de qualquer `mkdir`"
  - "`gravar_as_paginas` + `Contagem`: a costura testavel sem OCR e sem `recordings/`, com `duplicadas` e `perdidas` como campos SEPARADOS"
  - "Os dois roteiros de conferencia humana da fase, com o passo do sinal de mais explicito"
affects: [fase-4-modo-mercado, DETC-02, ANAL-*, portao-humano-fase-3]

actuals:
  tokens: 10766
  tasks: 2
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Guarda de caminho por `resolve()` + `os.path.normcase`, nunca por comparacao de texto"
    - "Guarda pura que NAO imprime e NAO cria nada — quem chama decide, e por isso ela pode rodar antes do primeiro `mkdir`"
    - "Contagem que separa os dois motivos de um `False`: chave repetida e feature desligada"
    - "Ferramenta de bancada com saida OBRIGATORIA e sem padrao, quando o padrao natural seria a pasta de producao"

key-files:
  created:
    - tools/gerar_observacoes_do_censo.py
    - tests/test_gerar_observacoes_do_censo.py
  modified: []

key-decisions:
  - "A comparacao de caminhos e `Path.resolve()` + `os.path.normcase`, e nao `Path.parents` nem comparacao de string. MEDIDO nesta maquina: as tres grafias (separador `/`, caixa alta, `..` no meio) colapsam na MESMA string mesmo quando o caminho NAO EXISTE — que e o caso normal, porque a guarda roda antes de a pasta ser criada"
  - "A guarda da saida roda ANTES ATE da conferencia de `recordings/`. Conferido a mao: `--saida .mercado` num worktree sem `recordings/` sai com codigo 2 pela RECUSA, e nao pela pasta ausente. Uma guarda que rodasse depois do `mkdir` ja teria deixado a marca do replay dentro da pasta que ela existe para proteger"
  - "`Contagem` ganhou um TERCEIRO campo, `perdidas`, contra a letra do plano (que pedia dois). `registrar` devolve `False` por DOIS motivos — chave ja conhecida e registro desligado — e somar os dois faria o relatorio dizer 'descartei 300 duplicadas' sobre uma sessao em que o disco encheu na terceira linha"
  - "O codigo de saida e ZERO quando a ferramenta VIU observacao, nova ou ja conhecida, e diferente de zero so quando nao viu nenhuma. A leitura literal do plano ('diferente de zero quando nao gravou') faria a SEGUNDA rodada — que e a prova de campo do PERS-02, passo 6 do roteiro — sair com erro exatamente quando ela deu certo, ensinando o usuario a ignorar o codigo de saida"
  - "A conferencia de que `l2scanner/` nao foi tocado e contra o COMMIT DE FECHAMENTO do 03-02 (`61d789f`), e nao contra `--grep='03-02'`: o grep casa com o CORPO das mensagens do proprio 03-03, que citam o 03-02, e devolveria o commit errado"
  - "`ruff format` NAO foi rodado: 37 dos 46 arquivos do repositorio nao estao formatados por ele, entao formatar os dois arquivos novos seria adotar uma convencao que a arvore nao segue. `ruff check` esta limpo, e e essa a barra que o repositorio de fato mantem"

patterns-established:
  - "Guarda de caminho no Windows: `resolve()` desfaz o `..` e o relativo, `os.path.normcase` desfaz o separador e a caixa. Comparacao de string sozinha aprovaria duas das tres grafias"
  - "Guarda pura + chamador que imprime: a funcao devolve a RAZAO ou `None`, o que a torna testavel contra o alvo REAL sem efeito colateral nenhum"
  - "Quando um `False` tem dois significados, a contagem tem dois campos — nunca um so"
  - "Skip condicional por plataforma quando a asserção seria FALSA na outra: a caixa insensivel e fato do Windows, e afirma-la no POSIX seria afirmar uma mentira"

requirements-completed: [PERS-01, PERS-02, PERS-03]

coverage:
  - id: D1
    description: "A costura de gravacao leva paginas aceitas ao CSV em disco: duas paginas identicas dao UMA observacao e UMA duplicada, e a contagem de series conta serie e nao linha"
    requirement: "PERS-01"
    verification:
      - kind: unit
        ref: "tests/test_gerar_observacoes_do_censo.py::TestACosturaDeGravacao::test_duas_paginas_IDENTICAS_dao_uma_observacao_e_uma_duplicada"
        status: pass
      - kind: unit
        ref: "tests/test_gerar_observacoes_do_censo.py::TestACosturaDeGravacao::test_a_contagem_de_SERIES_DISTINTAS_conta_serie_e_nao_linha"
        status: pass
    human_judgment: false
  - id: D2
    description: "Rodar a ferramenta duas vezes sobre a mesma saida nao aumenta a contagem de linhas — inclusive numa SESSAO NOVA, com o indice reconstruido do proprio disco"
    requirement: "PERS-02"
    verification:
      - kind: unit
        ref: "tests/test_gerar_observacoes_do_censo.py::TestACosturaDeGravacao::test_a_costura_rodada_DUAS_VEZES_nao_aumenta_as_linhas_do_arquivo"
        status: pass
      - kind: unit
        ref: "tests/test_gerar_observacoes_do_censo.py::TestACosturaDeGravacao::test_uma_SESSAO_NOVA_sobre_o_mesmo_arquivo_tambem_nao_duplica"
        status: pass
    human_judgment: false
  - id: D3
    description: "A pasta de producao do registro e RECUSADA como saida nas tres grafias do mesmo caminho, e uma subpasta dela tambem — sempre antes de qualquer `mkdir`"
    requirement: "PERS-01"
    verification:
      - kind: unit
        ref: "tests/test_gerar_observacoes_do_censo.py::TestAGuardaDaSaida::test_a_pasta_de_PRODUCAO_e_recusada_em_qualquer_grafia"
        status: pass
      - kind: unit
        ref: "tests/test_gerar_observacoes_do_censo.py::TestAGuardaDaSaida::test_uma_saida_DENTRO_da_pasta_de_producao_tambem_e_recusada"
        status: pass
      - kind: unit
        ref: "tests/test_gerar_observacoes_do_censo.py::TestAGuardaDaSaida::test_a_pasta_de_producao_REAL_e_recusada"
        status: pass
    human_judgment: false
  - id: D4
    description: "Com a saida quebrada de proposito a ferramenta desliga ALTO: `ERROR` no logger do projeto, com o texto da MONTAGEM do 03-02 (nao um texto proprio), sem traceback e com codigo diferente de zero"
    requirement: "PERS-03"
    verification:
      - kind: unit
        ref: "tests/test_gerar_observacoes_do_censo.py::TestOCaminhoDeFalhaQueOUsuarioVE::test_um_ARQUIVO_ocupando_o_nome_da_saida_desliga_alto_sem_traceback"
        status: pass
      - kind: unit
        ref: "tests/test_gerar_observacoes_do_censo.py::TestOCaminhoDeFalhaQueOUsuarioVE::test_o_aviso_e_o_TEXTO_DA_MONTAGEM_e_nao_um_texto_proprio"
        status: pass
      - kind: unit
        ref: "tests/test_gerar_observacoes_do_censo.py::TestOCaminhoDeFalhaQueOUsuarioVE::test_o_log_do_projeto_e_instalado_ANTES_de_montar_o_registro"
        status: pass
    human_judgment: false
  - id: D5
    description: "O conjunto de medicao e FECHADO: a lista das 8 e a MESMA tupla objeto de `medir_oclusao.GRAVACOES_DO_CENSO`, e `--gravacao` recusa nome de fora do censo"
    requirement: "PERS-01"
    verification:
      - kind: unit
        ref: "tests/test_gerar_observacoes_do_censo.py::TestOConjuntoDeMEDICAOEFechado::test_a_lista_da_ferramenta_e_a_MESMA_TUPLA_das_ferramentas_de_medicao"
        status: pass
      - kind: unit
        ref: "tests/test_gerar_observacoes_do_censo.py::TestAsSaidasDeErroLegiveis::test_um_SUBCONJUNTO_fora_do_censo_e_recusado"
        status: pass
    human_judgment: false
  - id: D6
    description: "O `observacoes.csv` produzido do material REAL do censo abre legivel no editor, importa no Google Sheets com separador Personalizado `;`, e a contagem antes/depois da segunda rodada bate"
    requirement: "PERS-01"
    verification: []
    human_judgment: true
    rationale: "O Google Sheets nao tem linha de comando, e o criterio 2 do ROADMAP exige 'importacao real, nao presumido'. Alem disso o material real (`recordings/`, `calibration.json`, motor de OCR) so existe no checkout PRINCIPAL do usuario — nao vem de clone limpo e nao se materializa em worktree. Roteiro 1 abaixo"
  - id: D7
    description: "O usuario VE, no console e no log, as duas mensagens exatas do desligamento alto, com a saida quebrada de proposito"
    requirement: "PERS-03"
    verification: []
    human_judgment: true
    rationale: "A metade console do D-13 so se prova olhando o console. O teste automatizado prova que os registros `ERROR` existem e que o texto e o da montagem; que eles CHEGAM aos olhos do usuario e o que o roteiro 2 confere. O passo do arquivo somente-leitura tambem depende das propriedades do Windows"

duration: 9min
completed: 2026-08-31
status: complete
---

# Phase 03 Plan 03: Replay do Censo Summary

**A ferramenta de bancada que transforma as 8 gravacoes do censo num `observacoes.csv` real — com a pasta de producao recusada mecanicamente por caminho resolvido, e o desligamento alto do 03-02 visivel no console pela primeira vez.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-08-31T04:56:00Z
- **Completed:** 2026-08-31T05:05:00Z
- **Tasks:** 2 (TDD, 4 commits de codigo)
- **Files modified:** 2 (ambos novos)

## Accomplishments

- **Existe um caminho real para o usuario produzir dado sem esperar a Fase 4.** `tools/gerar_observacoes_do_censo.py` passa as gravacoes pelo `LeitorDePagina` da Fase 2 e grava pelo `RegistroDeObservacoes` da Fase 3. Sem ela, quatro dos cinco criterios do ROADMAP ficariam sem material.
- **A recusa da pasta de producao e MECANICA, nao documental.** `resolve()` + `os.path.normcase` fazem as tres grafias do mesmo caminho no Windows colapsarem numa string so, e a guarda roda antes do primeiro `mkdir` — conferido a mao, `--saida .mercado` sai com 2 sem criar a pasta.
- **O aviso alto do PERS-03 ganhou um lugar onde acontecer.** A ferramenta monta pela `montar_registro_de_mercado` do 03-02 e instala `configurar_log` antes: o texto que o usuario ve aqui e byte a byte o que a Fase 4 vai mostrar.
- **O conjunto de medicao continua fechado.** A lista das 8 e a MESMA tupla objeto de `medir_oclusao.GRAVACOES_DO_CENSO` — provado por identidade, nao por igualdade — e `--gravacao` recusa qualquer nome de fora.
- **Nenhuma dependencia nova e nenhuma linha em `l2scanner/`.** Conferido contra o commit de fechamento do 03-02.

## Task Commits

1. **Task 1 (RED): a costura de gravacao** — `bf18970` (test)
2. **Task 1 (GREEN): o replay que produz o CSV real** — `233fb04` (feat)
3. **Task 2 (RED): as guardas da saida e o aviso alto** — `6099b22` (test)
4. **Task 2 (GREEN): a recusa mecanica e o log antes da montagem** — `0535bb6` (feat)

Nenhum passo de REFACTOR foi necessario: o GREEN de cada task ja saiu na forma final, e um commit de refactor sem mudanca seria ruido no historico.

## Files Created/Modified

- `tools/gerar_observacoes_do_censo.py` — o replay: `main(argv)`, a guarda `razao_para_recusar_a_saida`, a costura `gravar_as_paginas`, a `Contagem` de tres campos, e `varrer_uma_gravacao` com um leitor POR GRAVACAO
- `tests/test_gerar_observacoes_do_censo.py` — 25 testes sobre paginas construidas a mao e `tmp_path`, sem tocar `recordings/`, sem chamar OCR e sem rodar o censo

## Decisions Made

Ver `key-decisions` no frontmatter. As duas que mais mudam comportamento:

**O terceiro campo da `Contagem`.** O plano pedia "observacoes gravadas, duplicadas e series distintas". Implementado com um quarto numero, `perdidas`, porque `registro.registrar` devolve `False` tanto para chave repetida quanto para registro desligado. Sem separar, uma sessao em que o disco encheu apareceria no relatorio como uma sessao de dedup bem-sucedida — que e exatamente o tipo de silencio que o PERS-03 existe para proibir.

**O codigo de saida da segunda rodada.** O plano diz "diferente de zero quando nao gravou". Tomado ao pe da letra, o passo 6 do roteiro humano — rodar de novo e ver ZERO observacoes novas, que e a prova de campo do PERS-02 — sairia com erro no momento em que deu certo. A regra implementada e: diferente de zero quando a ferramenta nao VIU observacao nenhuma (arquivo vazio, que era a preocupacao real escrita no plano), e zero quando viu, nova ou ja conhecida. A segunda rodada imprime uma frase dizendo que aquele e o desfecho esperado.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `Contagem.perdidas` acrescentada ao par pedido**
- **Found during:** Task 1 (a costura de gravacao)
- **Issue:** `registrar` devolve `False` por dois motivos distintos; contar os dois como "duplicada" faria o relatorio afirmar dedup sobre uma feature morta
- **Fix:** terceiro campo `perdidas`, contado quando `not registro.ligado`, impresso no relatorio so quando nao e zero, e `main` sai com codigo diferente de zero se o registro desligou no meio
- **Files modified:** `tools/gerar_observacoes_do_censo.py`
- **Verification:** `TestACosturaDeGravacao::test_o_registro_DESLIGADO_conta_perdida_e_nunca_duplicada`
- **Committed in:** `233fb04`

**2. [Rule 1 - Bug] O codigo de saida da rodada sem observacao NOVA**
- **Found during:** Task 1, ao cruzar o `<action>` com o passo 6 do proprio `<human-check>` do plano
- **Issue:** "diferente de zero quando nao gravou" faria a prova de campo do PERS-02 reportar falha ao ter sucesso
- **Fix:** o codigo diferente de zero passa a significar "nao viu observacao nenhuma"; a rodada de zero NOVAS sai com 0 e imprime que este e o desfecho esperado
- **Files modified:** `tools/gerar_observacoes_do_censo.py`
- **Verification:** `TestOCaminhoDeFalhaQueOUsuarioVE::test_uma_varredura_SEM_OBSERVACAO_NENHUMA_sai_diferente_de_zero`
- **Committed in:** `233fb04` / `0535bb6`

**3. [Rule 3 - Blocking] O criterio de aceitacao do `git diff` do plano devolve o commit errado**
- **Found during:** verificacao final
- **Issue:** `git log -1 --format=%H --grep='03-02'` casa com o CORPO das mensagens do proprio 03-03 (que citam o 03-02) e devolveu `0535bb6`, um commit deste plano
- **Fix:** a conferencia foi feita contra o commit de fechamento do 03-02 pelo hash, `git diff --name-only 61d789f -- l2scanner/`, e tambem contra a arvore (`HEAD`). As duas vazias
- **Files modified:** nenhum — e uma correcao de procedimento de verificacao
- **Verification:** ambas as saidas vazias; `git diff --name-only <base> HEAD` lista exatamente os dois arquivos declarados no plano
- **Committed in:** n/a

---

**Total deviations:** 3 auto-corrigidas (1 funcionalidade critica ausente, 1 bug de contrato de saida, 1 procedimento de verificacao). **Impacto:** nenhuma alarga o escopo; as tres apertam a honestidade do que a ferramenta reporta.

### Decisao do plano REFUTADA

Nenhuma. As duas divergencias de comportamento acima estao dentro da intencao escrita do plano — a segunda, inclusive, existe para o `<action>` nao contradizer o `<human-check>` do mesmo plano.

## Issues Encountered

- **`ruff format` reformataria 37 dos 46 arquivos do repositorio.** A arvore nao segue o formatador. Rodei apenas `ruff check` (limpo, incluindo `--fix` para tres imports que so a Task 2 usaria) e deixei o formatador de fora, para nao introduzir uma convencao que o resto do projeto nao mantem.
- **O skip condicional em `test_a_pasta_de_PRODUCAO_e_recusada_em_qualquer_grafia[caixa-trocada]` NAO dispara nesta plataforma** (conferido com `-rs`: 25 passed, 0 skipped). Ele existe porque em sistema de arquivos sensivel a caixa `.MERCADO` E outra pasta, e afirmar a recusa la seria afirmar uma mentira. Nao e uma janela quebrada: no unico sistema que este projeto suporta, o teste roda.

## Known Stubs

Nenhum. Nenhum valor fixo, nenhum `TODO`, nenhum caminho de dado nao ligado.

## Threat Flags

Nenhuma superficie nova alem da ja registrada no `<threat_model>` do plano. `T-03-18` (injecao de formula por nome comecando em `+`) continua com disposicao **accept** e virou o passo 4 do roteiro 1 — o nome NAO e saneado no arquivo, de proposito.

---

# OS DOIS ROTEIROS DE CONFERENCIA HUMANA

Os dois rodam no **checkout PRINCIPAL**, nunca num worktree: `recordings/` e `calibration.json` sao gitignored e nao se materializam la. Use o interpretador que tem o motor de OCR (`.venv/Scripts/python.exe`).

## Roteiro 1 — o arquivo, a importacao e a contagem (criterios 1, 2 e 3)

**Passo 1 — produzir o arquivo.** Aponte a saida para uma pasta de rascunho, **nunca** para `.mercado/` (a ferramenta recusa, mas o habito e o que importa):

```
.venv/Scripts/python.exe tools/gerar_observacoes_do_censo.py --saida C:/temp/portao-fase3
```

Se dez minutos for demais, acrescente `--gravacao 20260828-053105-mercado-aberto` para rodar so uma. **Anote o numero de "observacoes GRAVADAS" do relatorio final.**

**Passo 2 — abrir no editor (criterio 1).** Abra `C:/temp/portao-fase3/observacoes.csv` no Bloco de Notas ou no VS Code. Voce deve conseguir dizer, so lendo: o que e cada coluna, qual e o preco total, qual e a quantidade, e quando aquilo foi visto. **O preco esta em CENTESIMOS — `6200` e `62,00`.** Confirme que **nao existe** coluna de preco unitario. Se alguma coluna te obrigar a adivinhar, diga qual.

**Passo 3 — a importacao real (criterio 2).** No Google Sheets: **Arquivo > Importar > Enviar**, escolha o arquivo. No dialogo, em separador, escolha **Personalizado** e digite `;`. **Nao existe opcao pronta de ponto-e-virgula na lista** — o dialogo oferece so *Detectar automaticamente / Tabulacao / Virgula / Personalizado*. Se voce procurar por "Ponto e virgula", nao vai achar, e e por isso que o roteiro manda usar Personalizado. Confira que as colunas cairam uma por coluna, e nao tudo colapsado numa so.

**Passo 4 — a pergunta do sinal de mais (o unico risco ALTO, e NAO MEDIDO).** Ainda no Sheets, procure uma linha cujo nome comece com `+` — o material do censo tem 15 nomes assim, como `+6 Agathion Alpha Hunter Sealed`. O Sheets trata celula iniciada em `+` como **formula**. **A celula mostra o nome, ou mostra um erro?** Se aparecer erro, diga qual. A correcao sera na planilha ou numa coluna extra — **nunca sujando o nome dentro do arquivo**, porque sanear o dado para agradar um importador e o oposto do que o criterio 1 pede.

**Passo 5 — a coluna do residuo.** Confira que existem celulas **VAZIAS** e celulas com **`0`** nessa coluna, e que elas nao viraram a mesma coisa. Vazio quer dizer "nao deu para medir"; zero quer dizer "conferi a aritmetica e bateu".

**Passo 6 — a contagem (criterio 3).** Rode a **mesma** ferramenta uma segunda vez, com a **mesma** saida e o **mesmo** subconjunto. O relatorio deve dizer **zero observacoes GRAVADAS** e todas descartadas como duplicadas, e imprimir a frase dizendo que este e o desfecho esperado. O comando sai com **codigo 0** — isso e correto, e nao erro. Conte as linhas do arquivo antes e depois: o numero nao pode mudar.

**O que reportar:** "aprovado" se os seis passos deram certo. Se algum falhou, diga qual passo, o que voce viu, e — no passo 4 — como a celula do nome com `+` apareceu.

## Roteiro 2 — o desligamento alto (criterio 5)

**Declaracao honesta do que esta fase pode e nao pode provar aqui:** nesta fase o mercado **nao tem chamador dentro do scanner** — o modo `--mercado` e DETC-02, Fase 4. Entao "os alertas de party continuam" e verdadeiro por **ausencia de acoplamento**: o scanner nem sabe que o registro existe. O que da para ver hoje e a outra metade, que e a que costuma falhar: o aviso alto, com o texto exato que a Fase 4 vai mostrar, saindo no console.

**Passo 1 — a pasta ocupada.** Crie um **arquivo** com o nome da pasta de saida (um `.txt` renomeado para `portao-quebrado`, sem extensao) e rode:

```
.venv/Scripts/python.exe tools/gerar_observacoes_do_censo.py --saida C:/temp/portao-quebrado
```

Voce deve ver, no console, **duas linhas de erro**: a primeira dizendo que o registro de mercado desligou e por que, a segunda dizendo que **morte, saida e ressurreicao seguem sendo detectadas e entregues**. Depois delas, uma terceira linha da propria ferramenta dizendo que nenhum arquivo vai ser produzido. **Nao deve aparecer traceback**, e o comando termina com codigo diferente de zero.

**Passo 2 — o arquivo somente-leitura.** Numa pasta de saida que ja tem um `observacoes.csv` produzido antes, marque o **arquivo** como somente-leitura pelas propriedades do Windows e rode a ferramenta de novo. Mesmo resultado: aviso alto, sem traceback. **Desmarque a permissao no fim.**

**Passo 3 — o cabecalho quebrado.** Abra um `observacoes.csv` produzido antes, troque o nome de uma coluna do cabecalho a mao, salve, e rode de novo. O mercado deve **desligar alto em vez de escrever desalinhado**. Confira depois, no editor, que **o arquivo nao foi alterado** — nenhuma linha nova entrou.

**Passo 4 — o log.** Abra `logs/scanner.log` e confirme que as mesmas duas mensagens estao la. O criterio diz **console E log**, e as duas metades contam.

**Passo 5 — o scanner de pe.** Rode o scanner normalmente, como voce ja faz, e confirme que nada mudou: ele sobe, detecta e entrega igual. Nesta fase isso e esperado **por construcao** — o passo existe para pegar uma regressao acidental, nao para provar a fiacao, que e da Fase 4.

**O que reportar:** "aprovado" se os cinco passos deram certo. Se algum falhou, diga qual, e cole as linhas que apareceram no console.

---

## Next Phase Readiness

- A Fase 4 (DETC-02, modo `--mercado`) encontra `montar_registro_de_mercado` pronta e no trilho, e agora com um consumidor de referencia mostrando a fiacao completa: leitor por gravacao, catalogo em memoria, carimbo por `Relogio`, e `registrar` por linha de pagina aceita.
- A resposta do passo 4 do roteiro 1 (o sinal de mais no Sheets) decide se uma coluna extra volta a mesa — **com medicao**, nunca por presuncao.
- Bloqueio nenhum. A fase so aguarda os dois portoes humanos.

## Self-Check: PASSED

**Arquivos afirmados, conferidos em disco:**
- `tools/gerar_observacoes_do_censo.py` — FOUND
- `tests/test_gerar_observacoes_do_censo.py` — FOUND
- `.planning/workstreams/mercado/phases/03-persist-ncia-de-observa-es/03-03-SUMMARY.md` — FOUND

**Commits afirmados, conferidos no historico:** `bf18970`, `233fb04`, `6099b22`, `0535bb6` — todos presentes. O `61d789f` citado como base da conferencia de `l2scanner/` existe e e um commit.

**Suite, medida neste worktree:**
- `tests/test_gerar_observacoes_do_censo.py` — **25 passed**, 0 skipped (`-rs`)
- `pytest -q --ignore=tests/test_agenda.py` — **2798 passed, 23 skipped**
- `pytest tests/test_agenda.py -q` — **145 passed** (o flake conhecido da linha 1141 nao disparou)
- Baseline do worktree SEM este plano: **2773 passed, 23 skipped**. `2773 + 25 = 2798` fecha exatamente. Os 21 skips a mais que a baseline do checkout principal (2794/2) sao os testes que dependem de `recordings/`, que o plano declarou tres vezes nao se materializar em worktree.
- **Zero falhas.**

**Escopo:** `git diff --name-only a705036 HEAD` lista exatamente os dois arquivos declarados no plano. `git diff --name-only 61d789f -- l2scanner/` e `git diff --name-only HEAD -- l2scanner/` sao ambos vazios. Nenhum arquivo de `tiat`/`identidade` tocado; `calibration.json` e `recordings/` intocados e ausentes de `git status`.

---
*Phase: 03-persist-ncia-de-observa-es*
*Completed: 2026-08-31*
