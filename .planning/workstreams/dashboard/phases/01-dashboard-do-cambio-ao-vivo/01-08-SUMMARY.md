---
phase: 01-dashboard-do-cambio-ao-vivo
plan: 08
subsystem: infra
tags: [batch, launcher, windows, cmd, dash-05, dash-06, controle-negativo, import-graph]

requires:
  - phase: 01-01
    provides: "o corte de RAIZ e a MEDICAO da cadeia de import que a sonda deste lancador tinha de refletir em vez de contradizer"
  - phase: 01-02
    provides: "serie_para_o_grafico e payload — a lista de series sobre a qual a prova do DASH-05 acontece"
  - phase: 01-05
    provides: "main(argv) com --porta e --sem-navegador, MENSAGEM_DE_PORTA_OCUPADA, o bloco de execucao direta e a fixture de porta efemera"
  - phase: 01-07
    provides: "desenharUmaSerie e as quatro funcoes que consomem a serie — o alvo da leitura de fonte que fecha a prova"
provides:
  - "dashboard.bat — o lancador proprio, irmao do vigiar-mercado.bat, com a sonda MEDIDA para este processo e os blocos de erro acima da execucao"
  - "tests/test_dashboard_bat.py — 21 provas: ASCII sobre bytes, ordem dos blocos com CONTROLE NEGATIVO, a linha de execucao chamando o MODULO, e a sonda que nao copia a do mercado"
  - "tests/test_dashboard_serie_generica.py — 11 provas do DASH-05 em dado, contrato, conta, endpoint e nomes consumidos pelo navegador, com CONTROLE NEGATIVO triplo do extrator"
  - "A regra estrutural nova desta arvore: um lancador que roda AO LADO de outro processo confere e RECUSA, nunca instala"
affects: []

actuals:
  tokens: 13122
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Lancador que roda ao lado de outro processo CONFERE e RECUSA em vez de instalar (molde do ponte-discord.bat), e so monta o ambiente quando ele provadamente nao existe"
    - "Sonda de dependencias MEDIDA para o processo que ela guarda, com a medicao e a refutacao escritas ao lado dela no proprio .bat"
    - "Extrator de fonte com CONTROLE NEGATIVO nos dois sentidos (acusa quando o fato existe, devolve vazio quando nao existe) sempre que uma assercao depende do que ele extraiu"
    - "Assercao de NAO-VAZIO na MESMA funcao de teste e ANTES de qualquer comparacao de subconjunto — `vazio <= qualquer coisa` e verdade"

key-files:
  created:
    - dashboard.bat
    - tests/test_dashboard_bat.py
    - tests/test_dashboard_serie_generica.py
  modified: []

key-decisions:
  - "O lancador NAO instala quando o ambiente ja existe — desvio deliberado do molde do vigiar-mercado.bat, porque o dashboard foi feito para ser aberto COM a coleta rodando e o instalador escreveria por cima de cv2.pyd CARREGADO"
  - "A sonda cobre exatamente cv2 e numpy, MEDIDOS nesta arvore (342 modulos, duas distribuicoes de site-packages), e nenhum pacote de captura, janela ou OCR"
  - "O .bat foi normalizado para CRLF como os irmaos: o goto do cmd busca rotulo por deslocamento de byte, e um lancador com goto e a pior hora para descobrir que LF sozinho e diferente"
  - "A lista de pacotes proibidos na sonda esta escrita A MAO no teste, e nao derivada do lancador do mercado — derivada, ela concordaria com qualquer copia errada"
  - "O extrator de propriedades do JS recorta por PARAMETRO chamado `serie` e por `function` na coluna zero, e nao por contagem de chaves: contar chaves quebra na primeira chave dentro de uma string, e este JS tem varias"

patterns-established:
  - "Gate de escopo em arvore COMPARTILHADA: o diff contra a base da fase e confundido por commits de outros workstreams, e a atribuicao correta e por commit (`git log -- <arquivo>`), nunca por diff cru"
  - "Reserva de verificacao humana com TESTE prendendo a declaracao: o cabecalho que diz o que a prova nao cobre tem um teste afirmando que a frase continua la"

requirements-completed: [DASH-05, DASH-06]

coverage:
  - id: D1
    description: "Dois cliques sobem a interface e abrem o navegador, sem o usuario digitar comando nenhum; rodar de outra pasta funciona porque o lancador vai para a pasta do proprio arquivo antes de qualquer coisa"
    requirement: DASH-06
    verification:
      - kind: unit
        ref: "tests/test_dashboard_bat.py::TestAIdaParaAPastaDoProprioArquivo::test_a_primeira_instrucao_efetiva_e_a_ida_para_a_pasta_do_arquivo"
        status: pass
      - kind: manual_procedural
        ref: "bancada 2026-09-02: `cmd` com diretorio atual em C:\\Windows chamando o `cd /d \"%~dp0\"` isolado -> resolve para a pasta do lancador"
        status: pass
      - kind: manual_procedural
        ref: "bancada 2026-09-02: `python -m l2scanner.dashboard --sem-navegador --porta 8791` -> GET /dados 200 (550 bytes), GET / 200 (12689 bytes)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Um segundo lancamento com o primeiro aberto mostra a mensagem de porta ocupada e nao um traceback, e sai em codigo 1"
    requirement: DASH-06
    verification:
      - kind: manual_procedural
        ref: "bancada 2026-09-02: segundo processo na porta 8791 -> codigo de saida 1, stdout com MENSAGEM_DE_PORTA_OCUPADA, stderr VAZIO"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_servidor.py::TestOMainSobeECaiEmVozAlta::test_main_sobre_uma_porta_ja_OCUPADA_devolve_1_sem_levantar (plano 01-05)"
        status: pass
    human_judgment: false
  - id: D3
    description: "O lancador nunca imprime um desfecho que nao conferiu: os blocos de erro vem antes da linha de execucao, com desvio por cima, e nada e impresso depois dela"
    requirement: DASH-06
    verification:
      - kind: unit
        ref: "tests/test_dashboard_bat.py::TestAOrdemDosBlocosEEstrutural (6 testes, incluindo o CONTROLE NEGATIVO nos dois sentidos)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A sonda de dependencias do lancador nomeia exatamente os dois pacotes que a medicao mostrou, e nenhum pacote de captura, janela ou OCR entra neste processo"
    requirement: DASH-06
    verification:
      - kind: unit
        ref: "tests/test_dashboard_bat.py::TestASondaDizAVerdadeMedidaSobreESTEProcesso (4 testes, com CONTROLE NEGATIVO do extrator)"
        status: pass
      - kind: manual_procedural
        ref: "medicao 2026-09-02: `import l2scanner.dashboard` -> 342 modulos, site-packages == ['cv2','numpy']"
        status: pass
    human_judgment: false
  - id: D5
    description: "O comportamento do --mercado fica identico: l2scanner/__main__.py nao muda uma linha por causa do dashboard, e o lancador chama o MODULO e nao o ponto de entrada do pacote"
    requirement: DASH-06
    verification:
      - kind: unit
        ref: "tests/test_dashboard_bat.py::TestALinhaDeExecucao::test_a_linha_de_execucao_NAO_chama_o_ponto_de_entrada_do_pacote"
        status: pass
      - kind: integration
        ref: "gate de escopo 2026-09-02: `grep -c dashboard l2scanner/__main__.py` -> 0; nenhum commit desta fase tocou __main__.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "Uma SEGUNDA serie atravessa dado, contrato, conta e endpoint sem uma linha de codigo de grafico nova, e toda propriedade que o dashboard.js consome existe nos dois elementos"
    requirement: DASH-05
    verification:
      - kind: unit
        ref: "tests/test_dashboard_serie_generica.py::TestDuasSeriesAtravessamODado (3 testes)"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_serie_generica.py::TestOFormatadorSaiDoPontoDeDecisaoUNICO (4 testes)"
        status: pass
      - kind: integration
        ref: "tests/test_dashboard_serie_generica.py::TestASegundaSerieAtravessaOServidor::test_o_endpoint_devolve_os_DOIS_elementos_com_o_mesmo_contrato"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_serie_generica.py::TestOQueONavegadorCONSOME (2 testes, com a assercao de NAO-VAZIO antes da comparacao e CONTROLE NEGATIVO triplo)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Duas series DESENHADAS AO MESMO TEMPO ficam legiveis na tela — duas linhas distinguiveis, legenda que cabe, titulo da segunda serie correto, sem o codigo do grafico ter mudado"
    requirement: DASH-05
    verification: []
    human_judgment: true
    rationale: "Exige navegador de verdade, e o 01-CONTEXT recusou instalador pesado de automacao de navegador. O que e afirmavel sem navegador — dado, contrato, conta, endpoint e os nomes que o JS consome — esta inteiro em D6; o que sobra e julgamento visual. A reserva esta declarada no cabecalho de `tests/test_dashboard_serie_generica.py` e presa por `TestAFronteiraDestaProvaEstaDECLARADA`."

duration: 40min
completed: 2026-09-02
status: complete
---

# Phase 01 Plan 08: O lancador e a prova da generalidade Summary

**O `dashboard.bat` que sobe a interface em dois cliques com a sonda de dependencias MEDIDA para este processo (cv2 e numpy, e nada de captura/janela/OCR) e os blocos de erro estruturalmente acima da execucao — mais a prova sem navegador de que uma SEGUNDA serie atravessa dado, contrato, conta, endpoint e os nomes que o `dashboard.js` consome, sem uma linha de codigo de grafico nova.**

## Performance

- **Duration:** 40 min
- **Tasks:** 3 de 3
- **Files created:** 3 (nenhum arquivo preexistente alterado)
- **Suite:** 4.892 passed, 26 skipped, 0 falhas

## Accomplishments

- **O lancador existe e a sonda dele diz a verdade MEDIDA.** `import l2scanner.dashboard` traz **342 modulos** e **exatamente duas** distribuicoes de `site-packages`: `cv2` e `numpy`. Nenhuma de captura (`mss`), de janela (`windows_capture`) ou de OCR (`winrt`). A sonda cobre esses dois e mais nada, e a medicao esta escrita ao lado dela no proprio `.bat` — inclusive a refutacao: **a pesquisa desta fase antecipava um lancador sem ambiente virtual nenhum**, com o dashboard virando stdlib puro depois do corte de `RAIZ`, e isso caiu.
- **A promessa de nao anunciar um desfecho nao conferido virou estrutura.** Os blocos de erro moram acima da linha de execucao, alcancados por `goto`, com `goto executar` por cima deles; depois da execucao nao ha um `echo`. O `pause` final continua (e nao anuncia nada — e o que torna a mensagem de porta ocupada LEGIVEL antes de a janela fechar).
- **O teste de ordem tem CONTROLE NEGATIVO nos dois sentidos.** Um `.bat` fabricado com `echo Pronto!` DEPOIS da execucao faz o auxiliar acusar; o mesmo `echo` ACIMA da execucao nao. Sem a segunda metade, um auxiliar que acusasse sempre tambem passaria.
- **A prova do DASH-05 nao pode passar por vacuidade.** A assercao de que o conjunto extraido do `dashboard.js` **nao esta vazio** vem na MESMA funcao de teste e ANTES da comparacao de subconjunto — porque `vazio <= qualquer coisa` e verdade. E o extrator tem controle negativo **triplo**: JS fabricado com funcao de serie devolve exatamente aquelas propriedades; JS sem funcao de serie devolve conjunto vazio; propriedade citada so em JSDoc nao conta.
- **O extrator achou as CINCO funcoes que consomem a serie**, e nao so a que instancia: `desenharUmaSerie`, `conjuntoCru`, `conjuntoDeBalde`, `conjuntoNaResolucao` e `opcoesDoGrafico`. As seis propriedades (`titulo`, `pontos`, `baldes`, `unidade`, `rotulo_principal`, `rotulo_tipico`) existem nos DOIS elementos do payload.
- **A metade que so o olho ve esta declarada, e presa por teste.** O cabecalho de `test_dashboard_serie_generica.py` diz por extenso que a prova NAO mostra duas series legiveis na tela, e ha um teste afirmando que essa frase continua la — uma reserva de verificacao que ninguem pode apagar por descuido.

## Task Commits

1. **Tarefa 1: `dashboard.bat`** — `464977e` (feat)
2. **Tarefa 2: o guarda do lancador** — `318b2b4` (test)
3. **Tarefa 3: a prova do DASH-05** — `048694a` (test)

## Files Created

- **`dashboard.bat`** — cabecalho dizendo o que ele E, o que ele NAO E (com "fechar esta janela preta nao interrompe a coleta da noite" em caixa alta) e o que ele precisa; ida para a pasta do proprio arquivo; descoberta do Python pelo caminho completo com recusa do atalho da Microsoft Store; bloco de ambiente guardado por inexistencia; sonda medida; blocos de erro acima da execucao com desvio por cima; `-m l2scanner.dashboard %*`. ASCII puro, CRLF.
- **`tests/test_dashboard_bat.py`** — 21 testes em 8 classes. Auxiliares COPIADOS de `test_vigiar_mercado_bat.py` com o motivo escrito (um teste importando outro teste e acoplamento que esta suite nao usa).
- **`tests/test_dashboard_serie_generica.py`** — 11 testes em 5 classes, sobre um CSV de fixture com duas series (a sentinela da Adena e `common-aztac#0`), sem disco real, sem frame, sem OCR.

## Decisions Made

- **A sonda foi MEDIDA, e nao copiada.** Uma sonda copiada do `vigiar-mercado.bat` concordaria com o que o irmao precisa e nao provaria nada sobre este processo. A medicao (342 modulos, `['cv2','numpy']`) foi refeita nesta arvore em 2026-09-02 e mora no `.bat`, com a segunda aresta (`mercado_console -> console -> rastreador -> visao`) nomeada e o motivo de ela nao ter sido cortada (DASH-03 obriga o dashboard a usar aqueles formatadores; cortar exigiria `console.py` ou `rastreador.py`, fora do que o usuario autorizou).
- **A lista de pacotes proibidos esta escrita a mao no teste.** Deriva-la da sonda do mercado faria o teste concordar com qualquer coisa que alguem copiasse de la — inclusive com a copia errada que o teste existe para impedir.
- **O extrator do JS recorta por parametro `serie` e por `function` na coluna zero.** Contagem de chaves quebra na primeira chave dentro de uma string, e este JS tem varias. As funcoes deste arquivo sao todas de topo, entao o recorte simples e o correto E o robusto.
- **A fixture tem CINCO ofertas distintas por instante.** O piso de evidencia da mediana e 5 (o do menor e 1). Com menos, `tipica_texto` viria como frase de piso — que e IGUAL nas duas series — e a comparacao de FORMA estaria medindo a frase de piso em vez do formatador. Ha um teste que avisa se a fixture perder ofertas.
- **A escolha do formatador e provada por IDENTIDADE, e nao so por resultado.** `formatador_do_unitario(adena) is not formatador_do_unitario(item)` e o mesmo criterio que `dashboard_dados._e_a_taxa` usa; um teste que medisse outra coisa nao estaria prendendo o mesmo ponto de decisao.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] O lancador NAO instala quando o ambiente ja existe**

- **Found during:** Tarefa 1, ao ler `ponte-discord.bat` e `tests/test_ponte_bat.py`
- **Issue:** O plano manda "manter o bloco de ambiente proprio e a sonda de dependencias", e o molde do `vigiar-mercado.bat` termina a sonda com `pip install -r requirements.txt`. Copiar esse final reintroduziria um defeito **ja medido e ja prendido nesta arvore**: os pinos do `requirements.txt` sao abertos (`opencv-python>=4.10,<5`, `numpy>=2.0`), e **o dashboard foi feito para ser aberto COM a coleta rodando**. Rodar o instalador nesse instante escreveria por cima de `cv2.pyd` e das DLLs do `numpy` com elas CARREGADAS pelo outro processo — falha de arquivo travado, ou um upgrade silencioso da pilha numerica no meio da coleta. Isso e literalmente **esta janela derrubando a coleta da noite**, o oposto do `must_have` do proprio plano ("derrubar o dashboard nao interrompe a coleta da noite").
- **Fix:** Os dois blocos continuam existindo, como o plano manda, mas com papeis separados: o bloco de ambiente so age quando `.venv\Scripts\python.exe` **nao existe no disco** (e entao nenhum processo pode estar rodando a partir dele, o que torna montar seguro), e a sonda que falha **RECUSA** com uma frase acionavel (`Rode vigiar-mercado.bat uma vez primeiro`) em vez de instalar. E a mesma regra do `ponte-discord.bat`, pelo mesmo motivo medido.
- **Files modified:** `dashboard.bat` (nenhum arquivo a mais)
- **Verification:** `TestOLancadorNaoInstalaSobreUmAmbienteJaMontado` (2 testes) prende os dois lados: todo `pip install` esta dentro da guarda de ambiente ausente, e a sonda que falha desvia para um bloco de recusa.
- **Committed in:** `464977e`

**2. [Rule 1 - Bug] O `.bat` e o teste nasceram com LF sozinho, e os irmaos sao CRLF**

- **Found during:** Tarefa 1, no `git add` (aviso "LF will be replaced by CRLF")
- **Issue:** `vigiar-mercado.bat` (161 CRLF, 0 LF-solo) e `ponte-discord.bat` (81 CRLF) sao CRLF na arvore de trabalho; o arquivo novo saiu com 168 LF sozinhos. Nao e cosmetica num arquivo que usa `goto`: o `cmd` busca rotulo por **deslocamento de byte**, e um lancador cheio de `goto` e a pior hora possivel para descobrir que a diferenca importa.
- **Fix:** `dashboard.bat`, `tests/test_dashboard_bat.py` e `tests/test_dashboard_serie_generica.py` normalizados para CRLF, alinhados com os irmaos. Testes reexecutados depois da conversao.
- **Files modified:** os tres arquivos novos deste plano
- **Verification:** `python -m pytest tests/test_dashboard_bat.py tests/test_dashboard_serie_generica.py -q` -> 32 passed apos a conversao
- **Committed in:** `464977e`, `318b2b4`, `048694a`

---

**Total deviations:** 2 auto-fixed (1 funcionalidade critica ausente, 1 bug)
**Impact on plan:** Nenhum scope creep. Nenhum arquivo preexistente foi tocado por este plano; `requirements.txt` nao ganhou uma linha; a cerca dura (`rastreador.py`, `visao.py`, `console.py`, `mercado_registro.py`, `mercado_analise.py`, `mercado_console.py`, `dashboard.py`, `dashboard.js`, `index.html`, `dashboard.css`) esta intacta.

## Gates de escopo da fase — o que foi MEDIDO

O `<verification>` do plano cobra tres gates contra a base da fase (`07be936`, o pai de `5ac2219`). **A arvore e COMPARTILHADA**: os workstreams `x9e`, `renda` e `260901-p2r` commitaram na mesma branch durante esta fase, entao o `git diff` cru contra a base **nao** e uma medida do que esta fase fez. A atribuicao correta e por commit.

### Gate 1 — arquivos cercados: **PASSA para esta fase**

`git diff --stat 07be936 HEAD -- <os oito arquivos + requirements.txt>` mostra **um** arquivo alterado, `l2scanner/__main__.py` (+75/-37). Atribuicao: `git log 07be936..HEAD -- l2scanner/__main__.py` -> **um unico commit, `390e275 feat(x9e-01)`** — outro workstream, nao esta fase.

Os outros oito caminhos (`mercado_modo.py`, `rastreador.py`, `visao.py`, `console.py`, `mercado_registro.py`, `mercado_analise.py`, `mercado_console.py`, `requirements.txt`) tem **zero commits** desde a base.

A promessa estrutural do DASH-06 tambem foi conferida direto, e nao so por diff: **`grep -c dashboard l2scanner/__main__.py` -> 0**. O ponto de entrada do `--mercado` nao sabe que o dashboard existe.

### Gate 2 — `config.py`: numero **PASSA**, criterio de token **TRIPA em duas linhas de COMENTARIO**

`git diff --numstat 07be936 HEAD -- l2scanner/config.py` -> **`15  1`**. **Exatamente UMA linha removida**, e ela e a definicao antiga de `RAIZ` (`RAIZ = Path(__file__).resolve().parent.parent`). Isso e o criterio ancora, e ele passa.

O criterio secundario ("nenhuma linha do diff pode mencionar `ARQUIVO_ENV`, `ARQUIVO_CONFIG`, `ARQUIVO_CONFIG_LOCAL`, `def ` ou `class `") **tripa em duas linhas ADICIONADAS**, e as duas sao comentario:

```
+# Os tres caminhos que a RAIZ resolve neste modulo — este, e `ARQUIVO_CONFIG` e
+# `ARQUIVO_CONFIG_LOCAL` mais abaixo — continuam intocados: o que mudou foi de
```

Nenhum `def `, nenhum `class `, nenhuma linha de codigo tocando as constantes. E o conteudo da prosa e o **oposto** do que o criterio guarda: ela afirma que aqueles caminhos ficaram intocados. Conferido direto no fonte, e o texto e byte-identico dos dois lados (so o numero da linha mudou):

| Constante | Base (`07be936`) | Hoje |
|---|---|---|
| `ARQUIVO_ENV` | `:49  ARQUIVO_ENV = RAIZ / ".env"` | `:63  ARQUIVO_ENV = RAIZ / ".env"` |
| `ARQUIVO_CONFIG` | `:150 ARQUIVO_CONFIG = RAIZ / "config.toml"` | `:164` identica |
| `ARQUIVO_CONFIG_LOCAL` | `:154 ARQUIVO_CONFIG_LOCAL = RAIZ / "config.local.toml"` | `:168` identica |

**Nao consertado de proposito.** `l2scanner/config.py` esta fora do `files_modified` deste plano e dentro da cerca dura; editar o comentario de outro plano para satisfazer a letra de um gate seria trocar uma verdade escrita por uma metrica verde. O que o gate existe para pegar — o corte tocando mais que a constante — **nao aconteceu**.

### Gate 3 — arquivos preexistentes: **QUATRO, e nao tres**

`git diff --name-only 07be936 HEAD -- l2scanner/ tests/ requirements.txt` lista 32 arquivos, mas a maioria e criacao desta fase ou commit de outro workstream. Atribuindo por commit, os arquivos **preexistentes** tocados **por esta fase** sao:

| Arquivo | Commit | Autorizado pelo plano 01-08? |
|---|---|---|
| `l2scanner/config.py` | `5ac2219` (01-01) | sim — nomeado |
| `l2scanner/mercado_catalogo.py` | `5ac2219` (01-01) | sim — nomeado (CTX-2) |
| `tests/test_mercado_firewall_de_fase.py` | `5ac2219`, `435083d` (01-01) | sim — nomeado |
| **`tests/test_mercado_registro.py`** | `5ac2219` (01-01) | **nao nomeado — este e o quarto** |

Os demais preexistentes da lista (`calibrar_mercado.py`, `recaptura.py`, `test_recaptura.py`, `test_moldes_cromaticos.py`, `test_mercado_adena_pagina.py`, `__main__.py`) foram tocados **so** por `x9e-*` e `260901-p2r` — outros workstreams.

**O quarto arquivo e conhecido, documentado e raciocinado, e nao uma descoberta minha.** Ele esta na Deviation #2 do `01-01-SUMMARY.md`: o tripwire `test_o_catalogo_JA_traz_cv2_e_numpy...` afirmava `"True True"` sobre `import l2scanner.mercado_catalogo`, o corte de `RAIZ` tornou a afirmacao falsa, e a **propria docstring dele instruia** o que fazer — *"Se um dia alguem aliviar a cadeia de `config` e este teste ficar vermelho, e boa noticia — e a hora de cobrar de volta a forma forte."* Ele foi VIRADO para `"False False"`, nunca apagado.

**Por que isto nao e a quebra do DASH-06 que o gate descreve:** o arquivo e `tests/test_mercado_registro.py`, e nao `l2scanner/mercado_registro.py`. A promessa do DASH-06 e sobre o **comportamento** do `--mercado`, e nenhum byte de FONTE do workstream `mercado` mudou alem da unica linha de import autorizada em CTX-2. Alem disso, o `<verification>` do proprio plano 01-08 exige `pytest tests/ -q` terminando em 0 — deixar aquele tripwire vermelho tornaria o plano insatisfazivel.

**Nao consertado de proposito**, pela mesma razao do Gate 2: o arquivo esta fora do meu `files_modified`, reverter deixaria a suite vermelha, e o gate esta cumprindo o papel dele — ele acusou, e a resposta e este registro, nao um silencio.

## Teste manual do lancador — o que foi medido em bancada

Esta arvore de trabalho **nao tem `.venv`** (ele e ignorado pelo git e vive no checkout principal), entao o duplo-clique de ponta a ponta **nao foi executado aqui**. O que foi medido, e como:

| O que | Como | Desfecho |
|---|---|---|
| Ida para a pasta do proprio arquivo | `cmd` com diretorio atual em `C:\Windows`, chamando o `cd /d "%~dp0"` isolado num `.bat` de bancada | **`C:\...\agent-a0f452ab69a8e549a`** — resolve certo de outra pasta |
| A linha de execucao | `python -m l2scanner.dashboard --sem-navegador --porta 8791` como subprocesso, exatamente a chamada do `:executar` | `GET /dados` -> **200** (550 bytes); `GET /` -> **200** (12.689 bytes) |
| Segundo lancamento na mesma porta | segundo subprocesso identico, com o primeiro de pe | **codigo de saida 1**, `stdout` com a `MENSAGEM_DE_PORTA_OCUPADA` inteira, **`stderr` vazio** — nenhum traceback |

A mensagem que o usuario le, na integra: *"O dashboard ja esta aberto nesta maquina (porta 8791 ocupada). NADA foi alterado (...) Se voce quer mesmo dois dashboards, rode com --porta seguido de outro numero. Enquanto isso, a coleta do --mercado segue rodando: ela nunca dependeu do dashboard."*

**Fica como verificacao humana:** o duplo-clique real no Explorer com o `.venv` do usuario montado, incluindo o caminho de primeira execucao (criacao do ambiente) e o de recusa por dependencia faltando.

## Issues Encountered

- **Heredoc do shell corrompe nao-ASCII nesta maquina** — o mesmo defeito que o `01-01-SUMMARY.md` registrou. Confirmado de novo em bancada: um travessao atravessando o heredoc vira byte de substituicao. Os tres arquivos deste plano sao ASCII puro, entao nao houve impacto — mas as escritas foram feitas pelas ferramentas de edicao com `encoding` explicito, e nao por heredoc.
- **A branch e compartilhada com tres outros workstreams**, o que torna todo gate escrito como "diff contra a base da fase" inutilizavel sem atribuicao por commit. Ver a secao de gates acima; vale registrar isto para o proximo planejador escrever gates atribuidos, e nao gates de diff cru.

## User Setup Required

Nenhuma configuracao de servico externo. O usuario da dois cliques no `dashboard.bat`; se a porta dele estiver ocupada, a saida esta na propria mensagem (`dashboard.bat --porta 8788`).

## Next Phase Readiness

- **DASH-05 e DASH-06 fechados**, com a reserva visual de DASH-05 declarada (D7) em vez de omitida.
- **A fase esta completa** — este era o ultimo plano dos oito.
- **O que o proximo planejador precisa saber:**
  - A regra nova desta arvore: **lancador que roda ao lado de outro processo confere e recusa, nunca instala**. `vigiar-mercado.bat` e `vigiar-party.bat` sao os unicos que montam ambiente; `ponte-discord.bat` e `dashboard.bat` recusam.
  - Gates de escopo precisam ser **atribuidos por commit** enquanto a branch for compartilhada.
  - A pendencia real que sobrou da fase inteira nao e deste plano: a segunda aresta do grafo de import (`mercado_console -> console -> rastreador -> visao`) continua trazendo `cv2` e `numpy` para o processo do dashboard. Cortar exige tocar `console.py` ou `rastreador.py` e uma autorizacao que CTX-2 nao deu. Esta escrito em `raiz.py`, nos dois tripwires e agora tambem no `dashboard.bat`.

## Known Stubs

Nenhum stub. Os tres arquivos deste plano sao um lancador completo e dois arquivos de teste; nao ha componente recebendo dado vazio, nem numero fabricado, nem valor de espaco reservado. A unica coisa deliberadamente **nao** entregue e a segunda serie DESENHADA na tela — e isso e decisao travada do `01-CONTEXT` ("o v1 mostra so a Adena"), registrada como D7 e declarada por extenso no cabecalho de `tests/test_dashboard_serie_generica.py`, com teste prendendo a declaracao.

## Self-Check: PASSED

- **Arquivos criados:** `dashboard.bat`, `tests/test_dashboard_bat.py`, `tests/test_dashboard_serie_generica.py` — os tres conferidos no disco.
- **Commits:** `464977e`, `318b2b4`, `048694a` conferidos no `git log`.
- **Suite:** `python -m pytest tests/ -q` -> **4.892 passed, 26 skipped**, 0 falhas (172 s).
- **Testes novos:** 21 + 11 = **32**, acima dos pisos do plano (8 e 6).
- **ASCII:** `dashboard.bat` -> **0 bytes** acima de 127.
- **`requirements.txt`:** sem diferenca desde a base da fase — nenhuma dependencia nova.
- **Cerca dura:** nenhum dos dez arquivos proibidos foi tocado por este plano; `git status --short` limpo antes do commit do SUMMARY.
- **Gates da fase:** medidos e registrados acima, incluindo os dois que tripam e o motivo de nenhum dos dois ser a quebra que descrevem.

---
*Phase: 01-dashboard-do-cambio-ao-vivo*
*Completed: 2026-09-02*
