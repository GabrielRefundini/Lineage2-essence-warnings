---
phase: 01-dashboard-do-cambio-ao-vivo
plan: 01
subsystem: ui
tags: [http.server, csp, stdlib, csv, tracer, import-graph, tdd]

requires: []
provides:
  - "l2scanner/raiz.py — modulo FOLHA com RAIZ, que corta a aresta mercado_catalogo -> config"
  - "l2scanner/dashboard_dados.py — ArquivoRecortado, LeituraAoVivo, observacoes_ao_vivo, payload"
  - "l2scanner/dashboard.py — CSP, PASTA_DOS_ESTATICOS, CAMINHO_DOS_DADOS, Manipulador, Servidor, montar_servidor"
  - "Os tres estaticos minimos com o bloco de tokens de cor COMPLETO em :root"
  - "A fixture de servidor com porta efemera e poll_interval=0.01, pronta para os planos 01-04 e 01-05"
  - "O tripwire do grafo de import consertado, com controle negativo ao lado"
affects: [01-02, 01-03, 01-04, 01-05, 01-06, 01-07, 01-08]

actuals:
  tokens: 18030
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Adaptador com forma de Path (ArquivoRecortado) para reusar um parser sem tocar no arquivo dele"
    - "Cabecalhos de seguranca em end_headers, e nao por rota — cobre tambem as respostas de erro da stdlib"
    - "Tokens de cor completos no CSS desde o primeiro commit, para nenhum plano seguinte precisar de um hexadecimal novo"
    - "Guarda com CONTROLE NEGATIVO ao lado, sempre que a assercao e de ausencia"

key-files:
  created:
    - l2scanner/raiz.py
    - l2scanner/dashboard_dados.py
    - l2scanner/dashboard.py
    - l2scanner/recursos/dashboard/index.html
    - l2scanner/recursos/dashboard/dashboard.css
    - l2scanner/recursos/dashboard/dashboard.js
    - tests/test_dashboard_tracer.py
  modified:
    - l2scanner/config.py
    - l2scanner/mercado_catalogo.py
    - tests/test_mercado_firewall_de_fase.py
    - tests/test_mercado_registro.py

key-decisions:
  - "Rota (d) para ler ate a ultima linha completa: um adaptador com forma de Path, e nao a rota (a) recomendada pela pesquisa — (a) mexeria em mercado_registro.py, que CTX-2 nao autoriza"
  - "A Tarefa 2 (corte de RAIZ) foi executada ANTES da Tarefa 1, porque dashboard.py deriva PASTA_DOS_ESTATICOS de raiz.RAIZ"
  - "_recencia_em_duas_formas e importado apesar do underscore: reescreve-lo seria o segundo formatador que o DASH-03 proibe, e promove-lo mexeria em mercado_console.py, fora de CTX-2"
  - "O payload NAO captura ContratoDoArquivoQuebrado — o portao do cabecalho continua desligando alto"
  - "A promessa do DASH-06 de que o dashboard nao carregaria OpenCV CAIU, e a queda esta medida e escrita no fonte"

patterns-established:
  - "Refutacao com MEDICAO no fonte: a premissa da linha parcial (0 em 22.970) e a segunda aresta do grafo (350 modulos) moram ao lado do codigo que elas explicam"
  - "Tripwire que avisou deve ser VIRADO, nunca apagado — o de test_mercado_registro.py pedia isso por escrito e foi atendido"

requirements-completed: [DASH-01, DASH-03, DASH-04, DASH-06]

coverage:
  - id: D1
    description: "GET /dados devolve o texto do XM por milhao IDENTICO ao que mercado_console.formatar_taxa_derivada produz sobre o mesmo CSV"
    requirement: DASH-03
    verification:
      - kind: integration
        ref: "tests/test_dashboard_tracer.py#TestUmaFonteUmaConta::test_o_texto_do_destaque_e_IDENTICO_ao_que_o_console_imprime"
        status: pass
    human_judgment: false
  - id: D2
    description: "Toda resposta do servidor carrega a CSP do VEND-4 com default-src 'none' e connect-src 'self'"
    requirement: DASH-04
    verification:
      - kind: integration
        ref: "tests/test_dashboard_tracer.py#TestOServidorEAPagina::test_a_CSP_do_VEND_4_viaja_em_TODA_resposta"
        status: pass
    human_judgment: false
  - id: D3
    description: "O CSV e aberto so em modo leitura: tamanho, mtime_ns e sha256 identicos depois de 50 leituras"
    requirement: DASH-01
    verification:
      - kind: unit
        ref: "tests/test_dashboard_tracer.py#TestALeituraAoVivo::test_cinquenta_leituras_nao_mudam_um_BYTE_do_arquivo"
        status: pass
    human_judgment: false
  - id: D4
    description: "CSV cortado no meio da ultima linha produz a serie ate a ultima linha completa; cabecalho trocado levanta nomeando o arquivo REAL"
    requirement: DASH-01
    verification:
      - kind: unit
        ref: "tests/test_dashboard_tracer.py#TestALeituraAoVivo::test_a_cauda_cortada_no_MEIO_da_ultima_linha_nao_derruba_a_serie"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_tracer.py#TestALeituraAoVivo::test_o_cabecalho_trocado_LEVANTA_nomeando_o_arquivo_REAL"
        status: pass
    human_judgment: false
  - id: D5
    description: "Um interpretador limpo que importa so l2scanner.mercado_catalogo nao traz config, rastreador nem cv2"
    requirement: DASH-06
    verification:
      - kind: integration
        ref: "tests/test_mercado_firewall_de_fase.py#test_o_catalogo_NAO_alcanca_MAIS_o_config_nem_o_rastreador"
        status: pass
      - kind: integration
        ref: "tests/test_mercado_firewall_de_fase.py#test_a_guarda_REPROVA_quando_a_cadeia_do_config_e_percorrida"
        status: pass
      - kind: integration
        ref: "tests/test_mercado_registro.py#test_o_catalogo_NAO_traz_MAIS_cv2_nem_numpy_a_forma_forte_de_volta"
        status: pass
    human_judgment: false
  - id: D6
    description: "A pagina servida em / carrega os estaticos por ARQUIVO (sem script/estilo inline) e o JS nao tem paleta propria"
    requirement: DASH-04
    verification:
      - kind: unit
        ref: "tests/test_dashboard_tracer.py#TestOServidorEAPagina::test_o_index_so_carrega_script_e_estilo_por_ARQUIVO"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_tracer.py#TestOServidorEAPagina::test_o_js_nao_carrega_paleta_PROPRIA"
        status: pass
    human_judgment: false
  - id: D7
    description: "A pagina, desenhada num navegador de verdade: o numero em destaque legivel, o relevo dos paineis, o tema de L2 sem custar contraste"
    verification: []
    human_judgment: true
    rationale: "O desenho na tela e verificacao humana declarada por decisao do 01-CONTEXT (Playwright foi recusado por instalador pesado). O que e afirmavel sem navegador — CSP, ausencia de inline, ausencia de hexadecimal no JS — ja esta coberto por D2 e D6; o que sobra e julgamento visual."

duration: 41min
completed: 2026-09-01
status: complete
---

# Phase 01 Plan 01: Tracer do dashboard Summary

**A fatia fina que vai do byte do `.mercado/observacoes.csv` ate um numero na tela do navegador — leitura ao vivo com corte antes do portao, o parser e o formatador UNICOS do mercado, `http.server` da stdlib com CSP em toda resposta — mais o corte de `RAIZ` para um modulo folha e o conserto do tripwire tautologico do grafo de import.**

## Performance

- **Duration:** 41 min
- **Tasks:** 3 de 3
- **Files modified:** 11 (7 criados, 4 alterados)
- **Suite:** 4.517 passed, 25 skipped (era 4.504 antes do plano)

## Accomplishments

- **A travessia inteira existe e esta presa por igualdade de STRING.** `GET /dados` devolve `"11,60 XM por milhao de adena (derivado)"`, byte a byte igual ao que `mercado_console.formatar_taxa_derivada` produz sobre as mesmas observacoes. A assercao falha no instante em que alguem reformatar o numero no caminho — que e o "segundo formatador" que o DASH-03 proibe.
- **A leitura ao vivo nao toca um byte do CSV**, provado por impressao digital de tres componentes (tamanho, `mtime_ns`, sha256) antes e depois de 50 leituras.
- **O corte de `RAIZ` foi feito e medido:** `import l2scanner.mercado_catalogo` caiu de **341 para 108 modulos** em `sys.modules`, e `cv2`/`numpy` sairam dele. O tempo de import acumulado caiu de **765 ms para 424 ms**.
- **O tripwire que nao podia cair passou a poder.** A versao antiga tinha uma assercao tautologica e passava identica nas duas arvores; a nova reprova a arvore antiga (`1 failed / 17 passed`) e aprova a nova (`18 passed`), com controle negativo ao lado.
- **Duas refutacoes viraram texto medido no fonte**, e nao so linha em documento de planejamento — ver "Decisoes Made" abaixo.

## Task Commits

1. **Tarefa 2: O corte de RAIZ** — `5ac2219` (refactor)
2. **Tarefa 1: TRACER — RED** — `9b0d266` (test)
3. **Tarefa 1: TRACER — GREEN** — `5db7e85` (feat)
4. **Tarefa 3: O tripwire consertado** — `435083d` (test)

_A Tarefa 1 e `tdd="true"` e por isso tem dois commits (RED e GREEN). Nao houve REFACTOR: o codigo saiu do GREEN sem duplicacao a remover._

## Files Created/Modified

**Criados**
- `l2scanner/raiz.py` — `RAIZ` num modulo folha (zero import do pacote), com a cadeia cortada, as quatro metricas da pesquisa, a remedicao nesta arvore e a refutacao do que o corte NAO compra
- `l2scanner/dashboard_dados.py` — `ArquivoRecortado` (as quatro rotas da §2 e o motivo de cada recusa), `LeituraAoVivo`, `observacoes_ao_vivo` (a refutacao da premissa da linha parcial, com a medicao) e `payload`
- `l2scanner/dashboard.py` — `CSP` (diretiva por diretiva comentada), `PASTA_DOS_ESTATICOS`, `CAMINHO_DOS_DADOS`, `Manipulador`, `Servidor`, `montar_servidor`
- `l2scanner/recursos/dashboard/index.html` — as tres regioes, sem `<script>` e sem `<style>` inline
- `l2scanner/recursos/dashboard/dashboard.css` — o bloco de tokens COMPLETO em `:root` (a unica declaracao de cor do projeto), espacamento, as tres familias de fonte e a receita de relevo
- `l2scanner/recursos/dashboard/dashboard.js` — um `fetch` unico, exibindo a string como recebeu, sem um hexadecimal
- `tests/test_dashboard_tracer.py` — 12 testes, entre eles os 7 exigidos pelo criterio de aceitacao

**Alterados**
- `l2scanner/config.py` — `RAIZ` passa a ser RE-EXPORTADO de `raiz`; nenhum chamador existente mudou
- `l2scanner/mercado_catalogo.py` — `from .raiz import RAIZ` (o unico arquivo do workstream `mercado` alterado no fonte)
- `tests/test_mercado_firewall_de_fase.py` — o tripwire consertado, o controle negativo acrescentado, e o paragrafo (2) do cabecalho reescrito
- `tests/test_mercado_registro.py` — o tripwire irmao, VIRADO conforme a instrucao escrita na propria docstring dele

## Decisions Made

- **A rota (d) para a leitura ao vivo, contra a recomendacao da pesquisa.** A pesquisa recomendava a (a) — extrair `observacoes_do_texto` de `mercado_registro.py`. Ela e a rota mais limpa e continua sendo a certa quando o workstream `mercado` reabrir, mas **mexe em `mercado_registro.py`**, e CTX-2 nomeia `mercado_catalogo.py` como o unico arquivo daquele workstream que esta fase pode tocar. A (b) faria a mensagem de contrato nomear um temporario que o usuario nao consegue abrir; a (c) e literalmente o segundo parser. A escolhida — o adaptador com forma de `Path` — custa um acoplamento de forma, e o antidoto e o teste de equivalencia que ja esta preso.
- **Duas refutacoes escritas no fonte, com o numero e nao so a conclusao:**
  1. *A premissa da linha parcial estava superestimada.* `csv.writer.writerow` + `flush` e uma unica chamada de escrita: **0 leituras parciais em 22.970 leituras de cauda** durante 200.000 appends concorrentes, com controle positivo acusando **3.252 de 4.079** — o zero e resultado, nao cegueira da sonda. A degradacao continua existindo como REDE DE SEGURANCA (arquivo editado no Sheets, queda de energia), e nao como caminho normal.
  2. *A promessa do DASH-06 sobre OpenCV caiu.* Medido nesta arvore hoje: `import l2scanner.dashboard` traz **333 modulos, com `cv2` e `numpy`**, pela segunda aresta `mercado_console -> console -> rastreador -> visao`. Corta-la exigiria tocar `console.py` ou `rastreador.py`, fora de CTX-2, e o dashboard e obrigado a usar os formatadores de `mercado_console` (DASH-03). O corte de `RAIZ` continua valendo pelo que ele de fato compra — o catalogo fora da cadeia de `config` — e o exagero esta corrigido no fonte, no tripwire e neste resumo.
- **`_recencia_em_duas_formas` e importado apesar do underscore.** A alternativa e reescrever a logica, que seria o segundo formatador que o DASH-03 proibe; promove-lo a nome publico mexeria em `mercado_console.py`, fora de CTX-2. O underscore fica como o aviso correto: nao ha promessa de estabilidade nessa assinatura, e quem a mudar tem dois chamadores para olhar.
- **O tracer nao antecipa o endurecimento.** `allow_reuse_address = False`, listagem desligada, `POST /cambio`, portao de origem, cache por `(tamanho, mtime_ns)` e `main` ficaram para os planos 01-04 e 01-05, cada um com o teste que o cobra. Codigo de seguranca sem o teste ao lado e o mesmo que nao ter escrito.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tarefa 2 executada antes da Tarefa 1**
- **Found during:** Tarefa 1, antes da primeira linha de codigo
- **Issue:** O plano manda `dashboard.py` derivar `PASTA_DOS_ESTATICOS` "a partir de `raiz.RAIZ`", mas `l2scanner/raiz.py` so nasce na Tarefa 2. Executar na ordem escrita exigiria ou um import de um modulo inexistente, ou criar `raiz.py` pela metade dentro da Tarefa 1 — partindo em dois o artefato de outra tarefa.
- **Fix:** As tarefas 2 → 1 → 3 foram executadas nessa ordem. A propriedade do tracer esta preservada: ele continua sendo a primeira fatia de ponta a ponta, e o portao de feedback foi honrado (o `<verify>` foi re-executado depois do commit, verde, antes de qualquer expansao). A Tarefa 2 nao e expansao do tracer — e um corte independente no grafo de import.
- **Files modified:** nenhum a mais; so a ordem dos commits
- **Verification:** `python -m pytest tests/test_dashboard_tracer.py -x -q` → 12 passed, re-executado apos o commit do tracer
- **Committed in:** `5ac2219` antes de `9b0d266`/`5db7e85`

**2. [Rule 1 - Bug] `tests/test_mercado_registro.py` afirmava a presenca de `cv2` e ficou vermelho**
- **Found during:** Tarefa 2, na suite de verificacao
- **Issue:** `test_o_catalogo_JA_traz_cv2_e_numpy_e_por_isso_o_criterio_original_caiu` afirmava `"True True"` sobre `import l2scanner.mercado_catalogo`. O corte de `RAIZ` tornou essa afirmacao falsa e a suite ficou `1 failed`. O arquivo esta fora da lista de tres arquivos pre-existentes que o plano nomeia.
- **Fix:** O teste foi **virado**, de `"True True"` para `"False False"`, e renomeado. Nao foi uma escolha livre: **a docstring dele instruia exatamente isso** — *"Se um dia alguem aliviar a cadeia de `config` e este teste ficar vermelho, e boa noticia — e a hora de cobrar de volta a forma forte."* O tripwire fez o trabalho para o qual foi escrito; apaga-lo teria jogado fora a unica prova de que o corte pegou. A docstring da classe ganhou o terceiro tempo da historia, e a nova docstring do teste registra que ele ja foi o oposto de si mesmo.
- **Nota de escopo, dita em voz alta:** o arquivo e `tests/test_mercado_registro.py`, e nao `l2scanner/mercado_registro.py`. A cerca dura do plano protege o FONTE do workstream `mercado` (comportamento do `--mercado`), e nenhum byte de fonte daquele workstream alem da linha autorizada foi tocado. Alem disso, o `<verification>` do proprio plano exige `pytest tests/ -q` terminando em 0 — deixar o teste vermelho tornaria o plano insatisfazivel.
- **Files modified:** `tests/test_mercado_registro.py`
- **Verification:** `python -m pytest tests/ -q` → 4.517 passed
- **Committed in:** `5ac2219` (commit da Tarefa 2)

**3. [Rule 1 - Bug] O paragrafo (2) do cabecalho de `test_mercado_firewall_de_fase.py` virou mentira**
- **Found during:** Tarefa 3
- **Issue:** O plano manda "manter o resto do arquivo intocado", mas a docstring do modulo declarava, em caixa alta, que a exigencia "importar o modulo de mercado nao traz `rastreador` para `sys.modules`" era **"FALSO HOJE"** e que cortar a cadeia estaria fora de escopo. Depois do corte, as duas frases sao falsas. Deixar como estava seria exatamente o "comentario mentindo" que o teste logo abaixo existe para impedir.
- **Fix:** O paragrafo foi reescrito com os tres tempos (existia / foi cortada / e verdade hoje) e com as duas ressalvas que precisam viajar junto: `import l2scanner.config` direto continua trazendo `cv2`, e o processo do dashboard tambem, pela segunda aresta.
- **Files modified:** `tests/test_mercado_firewall_de_fase.py` (arquivo ja autorizado pelo plano)
- **Verification:** `python -m pytest tests/test_mercado_firewall_de_fase.py -q` → 18 passed
- **Committed in:** `435083d`

**4. [Rule 3 - Blocking] `Path.read_text(newline=...)` nao existe no Python 3.12**
- **Found during:** Tarefa 1, portao GREEN (2 testes falharam com `TypeError`)
- **Issue:** O parametro `newline` de `Path.read_text` so entrou no 3.13; esta arvore roda **3.12.10**. (O `CLAUDE.md` prescreve 3.13 — a arvore real diverge disso, e o codigo tem de rodar na arvore real.)
- **Fix:** Um helper `_ler` no arquivo de teste, com `arquivo.open("r", encoding="utf-8", newline="")` e o motivo escrito ao lado. Nenhuma mudanca no codigo de producao.
- **Files modified:** `tests/test_dashboard_tracer.py`
- **Verification:** 12 passed
- **Committed in:** `5db7e85`

---

**Total deviations:** 4 auto-fixed (2 blocking, 2 bug)
**Impact on plan:** Nenhum scope creep. Dois consertos sao consequencia direta e prevista do corte autorizado por CTX-2 — um deles pedido por escrito pelo proprio teste que caiu. Nenhum arquivo de FONTE do workstream `mercado` alem da linha autorizada foi tocado, e `requirements.txt` nao ganhou uma linha.

## Issues Encountered

- **`01-PATTERNS.md` nao existe.** O bloco `<required_reading>` e cinco blocos `<read_first>` do plano referenciam `.planning/workstreams/dashboard/phases/01-dashboard-do-cambio-ao-vivo/01-PATTERNS.md`, e o arquivo nao esta no diretorio da fase (que tem apenas os oito planos, `01-CONTEXT.md`, `01-RESEARCH.md` e `01-UI-SPEC.md`). Nao foi bloqueante: todo excerto que o plano atribui ao PATTERNS aparece tambem no `01-RESEARCH.md` (a forma do servidor, o molde da fixture, a cadeia de import) ou no `01-UI-SPEC.md` (a CSP, os tokens), e os arquivos-analogo foram lidos direto no fonte. **Vale conferir antes do plano 01-02**, que tambem o referencia.
- **O heredoc do shell corrompe caracteres nao-ASCII** nesta maquina (o travessao vira `?` ao atravessar o stdin do Python). Detectado por um `replace` que nao casou. Todas as edicoes de texto em portugues passaram a ir pelas ferramentas de edicao, com `encoding="utf-8"` explicito. Sem impacto no que foi commitado.

## User Setup Required

None — nenhuma configuracao de servico externo. O servidor sobe em `127.0.0.1` numa porta efemera nos testes; o lancador `dashboard.bat` e a porta fixa sao do plano 01-08.

## Next Phase Readiness

**Pronto para os planos seguintes:**
- `montar_servidor(porta, pasta_do_mercado)` e a fixture de servidor com `poll_interval=0.01` estao prontos e sao o molde direto para 01-04 (travessia de caminho) e 01-05 (endpoint, cache, `POST /cambio`).
- O bloco de tokens de cor esta COMPLETO no `:root`, incluindo `--cor-serie-tipica`, `--cor-frio` e `--cor-grade`, que so 01-06 e 01-07 vao usar. **Nenhum plano seguinte precisa introduzir um hexadecimal** — e ha teste com controle negativo prendendo isso do lado do JS.
- `payload` esta na forma minima do tracer: so o destaque em XM. A tabela de PRECEDENCIA entre `ok`, vazio, velho, cambio ausente e contrato quebrado e do 01-02, e o campo `estado` ja existe para receber.

**O que o proximo planejador precisa saber:**
- **O processo do dashboard carrega `cv2` e `numpy`** (333 modulos, ~800 ms de import). Isso e fato medido, nao pendencia escondida; a sonda do `dashboard.bat` prevista no 01-07/01-08 deve refletir isso em vez de prometer o contrario.
- `payload` recebe o cambio por PARAMETRO quando o 01-03 chegar — nao importando `dashboard_cambio`. Quem junta os dois e o servidor, e e isso que mantem `dashboard_dados` testavel sem disco.
- A frase de piso de evidencia esta duplicada em `payload` (o texto `"sem evidencia - N de M ofertas distintas"`, hoje montado ali). Se o 01-02 precisar dela em mais de um lugar, ela deve virar um ponto de decisao unico antes de ganhar o segundo chamador.

## Self-Check: PASSED

- **Arquivos criados:** os 7 artefatos e o proprio SUMMARY conferidos no disco — todos presentes.
- **Commits:** `5ac2219`, `9b0d266`, `5db7e85`, `435083d` e `79bc8b9` conferidos no `git log`.
- **Arvore limpa:** `git status --short` vazio depois do commit do SUMMARY.
- **Suite:** `python -m pytest tests/ -q` → **4.517 passed, 25 skipped**, 0 falhas.
- **Cerca de escopo:** `git diff --stat` contra a base mostra **um unico arquivo de fonte do workstream `mercado`** alterado (`l2scanner/mercado_catalogo.py`), com uma linha de import trocada. `rastreador.py`, `visao.py`, `console.py`, `mercado_registro.py`, `mercado_analise.py` e `mercado_console.py` intocados.
- **`requirements.txt`:** sem diferenca — nenhuma dependencia nova.

## Known Stubs

Nenhum stub. As duas regioes `#serie` e `#procedencia` do `index.html` trazem texto que descreve o que vao mostrar — **conteudo declarado, e nao placeholder**: nao ha componente recebendo dado vazio, nem numero fabricado, nem `0,00` de espaco reservado. O `payload` cobre so o destaque em XM porque essa e a fatia do tracer, e o campo `estado` ja existe para a tabela de precedencia do plano 01-02.

---
*Phase: 01-dashboard-do-cambio-ao-vivo*
*Completed: 2026-09-01*
