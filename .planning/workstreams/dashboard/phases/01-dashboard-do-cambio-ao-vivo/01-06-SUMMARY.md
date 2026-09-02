---
phase: 01-dashboard-do-cambio-ao-vivo
plan: 06
subsystem: ui
tags: [html, css, tema-l2, wcag, contraste, estado-vazio, uplot, csp, sem-dependencia]

requires:
  - phase: 01-01
    provides: "o esqueleto do index.html, o bloco de tokens de cor inicial, o uPlot vendorizado e o teste que ja prendia 'nenhum script embutido'"
  - phase: 01-02
    provides: "os nomes dos cinco estados, as frases de copia como constantes Python, e a forma do payload (tipica_pixel None, destaque None, series [])"
  - phase: 01-04
    provides: "PASTA_DOS_ESTATICOS e o servico de estatico do diretorio inteiro, que e o que torna vendor/uPlot.min.css alcancavel por marcacao"
provides:
  - "As tres regioes do UI-SPEC (#destaque, #serie, #procedencia) com os identificadores travados, afirmadas por parse"
  - "O formulario do cambio de verdade: rotulo vinculado, campo nascendo vazio com o exemplo so como placeholder, limite de comprimento, e SEM destino (a colisao com form-action 'none' e a falha fechada certa)"
  - "O tema de Lineage 2 inteiro em CSS escrito a mao: tokens, relevo, quatro tamanhos, dois pesos, escala de quatro pontos, foco, pulso e movimento reduzido"
  - "Os seis estados desenhados no CSS e ancorados em atributos de estado — nenhuma decisao visual mora no JS"
  - "A placa de estado vazio, a legenda das duas linhas e o lugar da linha de prova, todos NA MARCACAO"
  - "Um bloco nomeado de sobreposicoes da folha da biblioteca, que retematiza o grafico e corrige o peso e o tamanho que ela traz de fora da escala"
  - "tests/test_dashboard_pagina.py — 77 testes: estrutura por parse, copia nos dois sentidos de procedencia, tema por expressao regular com controle em cada guarda, e contraste RECALCULADO a partir dos tokens"
affects: [01-07, 01-08, verificacao-da-fase-1]

actuals:
  tokens: 20214
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Estado em atributo no <body>, desenho no CSS: o JS so troca o valor do atributo"
    - "Copia de interface na marcacao com o CSS escolhendo qual variante aparece (os dois rotulos do botao), para a copia continuar conferivel por teste"
    - "Linhas alimentadas pelo servidor governadas por `:empty`: o JS escreve o texto, o CSS decide se a linha aparece"
    - "Contraste RECALCULADO por teste a partir dos tokens do CSS, em vez de repetido do documento de design"
    - "Todo guarda de expressao regular carrega um controle (negativo ou positivo) que prova que a busca funciona"

key-files:
  created:
    - tests/test_dashboard_pagina.py
  modified:
    - l2scanner/recursos/dashboard/index.html
    - l2scanner/recursos/dashboard/dashboard.css

key-decisions:
  - "O ornamento de canto NAO foi implementado: ele era opcional e condicionado a uma verificacao ('se encostar no numero de 48px em qualquer largura, ele sai') que nao pode ser feita sem navegador. Enviar sob condicao nao verificavel seria decidir por omissao"
  - "O vocabulario de estado do <body> e o MESMO do dashboard_dados (sem_leitura, abaixo_do_piso, serie_presente, ...): dois vocabularios divergem em silencio"
  - "Os dois rotulos do botao moram na marcacao e o CSS escolhe qual aparece — nenhuma copia de interface nasce no JS"
  - "A frase de R$ indisponivel vem ANTES do formulario na ordem do documento, e nao so na tela: um `order` do CSS deixaria a leitura de tela ouvindo o pedido antes da razao dele"
  - "A folha da biblioteca vendorizada e explicitamente ISENTA das assercoes de tema (ela nao assinou o contrato), e o que a tela final mostra e corrigido pelo bloco nomeado de sobreposicoes"
  - "As frases que o Python tambem conhece sao LIDAS das constantes dele no teste, para uma copia julgar a outra; as do Python sao afirmadas AUSENTES do HTML, para nao existir segunda fonte da mesma frase"
  - "Quando um comentario meu continha uma literal que meus proprios testes procuram, a prosa foi reescrita e a assercao NAO foi enfraquecida"

patterns-established:
  - "Ancora de estado: toda condicao de tela e um seletor no CSS, nunca um `if` no JS"
  - "Procedencia de copia afirmada nos dois sentidos: a da moldura TEM de estar no HTML, a do Python NAO PODE estar"
  - "Guarda com controle: `test_o_bloco_de_tokens_TEM_hexadecimais` (negativo) e `test_o_leitor_de_espacamento_ACUSA_um_valor_fora_da_escala` (positivo) provam que os guardas veem o que dizem ver"

requirements-completed: [DASH-02, DASH-04, DASH-05]

coverage:
  - id: D1
    description: "As tres regioes do UI-SPEC existem como elemento, com os identificadores travados"
    requirement: "DASH-04"
    verification:
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestAEstruturaDaPagina::test_as_TRES_regioes_do_contrato_existem_como_ELEMENTO"
        status: pass
    human_judgment: false
  - id: D2
    description: "O envio do cambio e um formulario de verdade, com rotulo vinculado, campo nascendo vazio, limite de comprimento e sem destino declarado"
    requirement: "DASH-02"
    verification:
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestAEstruturaDaPagina::test_o_envio_do_cambio_e_um_FORMULARIO_de_verdade"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestAEstruturaDaPagina::test_o_campo_nasce_VAZIO_com_o_exemplo_so_como_placeholder"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestAEstruturaDaPagina::test_o_formulario_NAO_declara_destino"
        status: pass
    human_judgment: false
  - id: D3
    description: "A pagina nao carrega script nem estilo embutido, e nao tem atributo de evento — as tres formas que a CSP proibe"
    verification:
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestAEstruturaDaPagina::test_todo_script_carrega_por_ARQUIVO"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestAEstruturaDaPagina::test_a_contagem_de_estilos_EMBUTIDOS_e_zero"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestAEstruturaDaPagina::test_a_contagem_de_atributos_de_EVENTO_e_zero"
        status: pass
    human_judgment: false
  - id: D4
    description: "A paleta mora num lugar so: nenhum hexadecimal fora do bloco de tokens, no CSS nem no HTML"
    verification:
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOTemaObedeceOContrato::test_nenhum_hexadecimal_vive_FORA_do_bloco_de_tokens"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOTemaObedeceOContrato::test_o_bloco_de_tokens_TEM_hexadecimais"
        status: pass
    human_judgment: false
  - id: D5
    description: "Quatro tamanhos de fonte, dois pesos, escala de espacamento de quatro pontos com as tres excecoes de traco nomeadas"
    verification:
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOTemaObedeceOContrato::test_a_escala_tipografica_tem_no_maximo_QUATRO_tamanhos"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOTemaObedeceOContrato::test_todo_espacamento_em_px_pertence_a_ESCALA_de_quatro_pontos"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOTemaObedeceOContrato::test_o_leitor_de_espacamento_ACUSA_um_valor_fora_da_escala"
        status: pass
    human_judgment: false
  - id: D6
    description: "Os pisos de contraste sao recalculados a partir dos tokens do CSS, e nao copiados do documento de design"
    verification:
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOContrasteFoiRecalculado::test_o_par_cumpre_o_piso_do_contrato"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOContrasteFoiRecalculado::test_a_formula_de_contraste_conhece_os_DOIS_extremos"
        status: pass
    human_judgment: false
  - id: D7
    description: "Nenhuma requisicao de rede sai da pagina — nenhuma origem externa, nenhuma regra de importacao, nenhuma fonte baixada"
    verification:
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOTemaObedeceOContrato::test_a_pagina_nao_pede_UM_BYTE_a_rede"
        status: pass
    human_judgment: false
  - id: D8
    description: "Os seis estados tem desenho proprio no CSS, ancorado em atributo de estado"
    requirement: "DASH-04"
    verification:
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOsEstadosTemDesenho::test_o_estado_tem_regra_ancorada_no_ATRIBUTO_de_estado"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOsEstadosTemDesenho::test_a_regra_de_dado_velho_troca_a_COR_e_nao_esconde_o_numero"
        status: pass
    human_judgment: false
  - id: D9
    description: "O estado vazio e CONTEUDO: placa, legenda e lugar da linha de prova na marcacao, e grade e eixos desenhados na area do grafico"
    requirement: "DASH-04"
    verification:
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOEstadoVazioEConteudo::test_a_placa_de_estado_vazio_esta_na_MARCACAO_mesmo_escondida"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOEstadoVazioEConteudo::test_a_area_do_grafico_desenha_GRADE_no_estado_vazio"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOEstadoVazioEConteudo::test_a_LEGENDA_das_duas_linhas_esta_na_marcacao"
        status: pass
    human_judgment: false
  - id: D10
    description: "O componente de serie e generico: o nome da serie nao aparece em nenhum lugar do CSS"
    requirement: "DASH-05"
    verification:
      - kind: unit
        ref: "tests/test_dashboard_pagina.py::TestOTemaObedeceOContrato::test_o_CSS_INTEIRO_nao_escreve_o_nome_da_serie"
        status: pass
    human_judgment: false
  - id: D11
    description: "O julgamento visual do tema: nenhum ornamento encosta no numero de 48px em nenhuma largura, o texto sobre o relevo continua legivel, o numero em destaque e a primeira coisa que o olho encontra, e o cartao de R$ realmente SOME sem cambio informado"
    verification: []
    human_judgment: true
    rationale: "E a `<human-check>` declarada na Tarefa 3 do plano. Nao ha teste de layout de navegador nesta arvore, e a doutrina de prova da fase e afirmar sem navegador — entao esta e a parte que honestamente nao da para afirmar assim. Registrada tambem no ledger de defeitos (entrada 45, kind unrun-verify)."

duration: 27min
completed: 2026-09-01
status: complete
---

# Fase 01 Plano 06: A superfície — estrutura, tema e estados Summary

**As três regiões do UI-SPEC em HTML sem nada embutido, o tema de Lineage 2 inteiro em CSS escrito à mão (paleta num lugar só, quatro tamanhos, dois pesos, zero byte de rede) e os seis estados desenhados no CSS — com o contraste RECALCULADO por teste a partir dos tokens em vez de copiado da tabela de design.**

## Performance

- **Duration:** 27 min
- **Started:** 2026-09-02T02:34Z
- **Completed:** 2026-09-02T03:01Z
- **Tasks:** 3
- **Files modified:** 3 (2 modificados, 1 criado)

## Accomplishments

- **As três regiões existem como elemento, e a prova é por parse.** Esta página tem comentários longos que citam os próprios identificadores — uma busca de texto ficaria verde com o identificador dentro de um comentário. O teste monta a árvore com `html.parser` e pergunta a ela.
- **O formulário é de verdade e não tem destino.** A tecla de confirmação submete, e a colisão com `form-action 'none'` da CSP é a falha fechada certa: o caminho normal é o JS interceptar; o caminho anômalo não vai a lugar nenhum.
- **O tema inteiro saiu do contrato, sem um byte de rede.** Três famílias do sistema, quatro tamanhos, dois pesos, escala de quatro pontos, a receita de relevo com o gradiente e as três sombras, o filete dourado sob cada título, o anel de foco, o pulso de 200 ms e a regra de movimento reduzido que zera os dois.
- **O contraste é recalculado, e não repetido.** `TestOContrasteFoiRecalculado` lê os tokens do CSS, refaz a conta da WCAG e cobra o piso de cada par. As oito razões reproduziram exatamente as medições publicadas no UI-SPEC — o documento tinha sido medido, e não estimado.
- **Os seis estados têm desenho próprio, ancorado em atributo.** O JS só troca o valor do atributo; nenhuma decisão visual mora nele.
- **O estado vazio é conteúdo.** A placa, a legenda das duas linhas e o lugar da linha de prova estão na MARCAÇÃO — não são criados pelo JS. E a área do gráfico desenha grade e eixos temáticos, porque um retângulo em branco é indistinguível de "o dashboard quebrou", e esta é a primeira tela que o usuário vai ver.

## Task Commits

1. **Tarefa 1: A estrutura — três regiões, um formulário de verdade, zero embutido** — `f7e0c1e` (feat)
2. **Tarefa 2: O tema — tokens, tipografia, escala e a receita de relevo** — `46a0d5d` (feat)
3. **Tarefa 3: Os estados desenhados — o vazio, o sem-câmbio, o velho e o servidor mudo** — `c29f597` (feat)

## Files Created/Modified

- `l2scanner/recursos/dashboard/index.html` — as três regiões com os identificadores travados, o formulário de verdade, a legenda, a placa de estado vazio, os quatro atributos de estado no `<body>` e as referências por arquivo na ordem certa (1879 → 12445 bytes)
- `l2scanner/recursos/dashboard/dashboard.css` — o bloco de tokens (única declaração de cor da árvore), a escala tipográfica, a escala de espaçamento, a receita de relevo, os seis estados desenhados e o bloco nomeado de sobreposições da folha da biblioteca (5988 → 27705 bytes)
- `tests/test_dashboard_pagina.py` — **novo**, 77 testes: estrutura por parse, cópia nos dois sentidos de procedência, tema por expressão regular com controle em cada guarda, e contraste recalculado a partir dos tokens

## Decisions Made

### 1. O ornamento de canto NÃO foi implementado

O UI-SPEC o declara **opcional e condicionado**: *"se em qualquer largura de tela ele encostar no número de 48px, ele sai"*. Essa condição só é verificável abrindo a página e variando a largura da janela — e a doutrina de prova desta fase é afirmar sem navegador.

Enviá-lo sem poder verificar a condição seria decidir por omissão exatamente a coisa que o usuário travou por escrito: **o tema nunca custa legibilidade do número.** O tema não depende dele — o relevo do painel, o filete dourado, a serifa em maiúsculas com `letter-spacing` e a paleta de bronze já entregam a identidade de L2 inteira em CSS puro. Registrado aqui para que a escolha seja uma decisão consultável, e não um esquecimento.

### 2. O vocabulário de estado é o mesmo dos dois lados

`data-estado` no `<body>` usa exatamente os nomes de `dashboard_dados` (`erro_de_contrato`, `arquivo_ausente`, `sem_leitura`, `abaixo_do_piso`, `serie_presente`), mais `primeira_pintura`. Dois vocabulários para a mesma máquina de estados divergem em silêncio, e a divergência aparece como uma tela que simplesmente não muda.

### 3. Os ortogonais são atributos separados, e não valores do mesmo atributo

`data-cambio`, `data-velho` e `data-servidor` modificam a tela sem tomar a precedência. Vários podem ser verdade ao mesmo tempo — é a definição de ortogonal — e espremê-los num atributo só forçaria uma ordem que o contrato diz não existir.

### 4. A cópia de interface não nasce no JS

Os dois rótulos do botão (`Salvar câmbio` e `Salvando…`) moram na marcação, e o CSS escolhe qual aparece pelo `data-salvando`. Um rótulo escrito pelo JS seria cópia que nenhum teste desta suíte vê. As linhas alimentadas pelo servidor usam `:empty`, de modo que o JS só precisa **escrever o texto** — decidir se a linha aparece continua sendo do CSS.

### 5. A frase de R$ indisponível vem antes do formulário na ordem do documento

O plano pede que ela apareça "logo acima do campo". Resolver isso com `order` do CSS deixaria a leitura visual certa e a de leitor de tela errada — quem depende do leitor ouviria o pedido antes da razão dele. O elemento foi movido na marcação.

### 6. A folha da biblioteca é isenta das asserções de tema — e por isso as sobreposições existem

`vendor/uPlot.min.css` traz hexadecimais, `system-ui` e peso 600. Cobrar dele a nossa escala seria cobrar de quem não assinou o contrato; o portão dele é outro (VEND-1..4). O que se faz é **retematizar o que ele desenha**, e é essa a razão de o bloco nomeado de sobreposições existir e de haver um teste da ORDEM dos dois `<link>`.

### 7. Todo guarda carrega um controle

`test_o_bloco_de_tokens_TEM_hexadecimais` é o controle negativo do caçador de paleta clandestina; `test_o_leitor_de_espacamento_ACUSA_um_valor_fora_da_escala` é o controle positivo do leitor de espaçamento; `test_a_formula_de_contraste_conhece_os_DOIS_extremos` prende a fórmula nos únicos dois valores que ela não pode errar. Um teste que só afirma "não achei nada" é indistinguível de um leitor quebrado que nunca acha nada.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] A folha da biblioteca introduzia um terceiro peso e um quinto tamanho na tela renderizada**

- **Found during:** Tarefa 2 (o tema)
- **Issue:** O plano pede "no máximo quatro tamanhos e dois pesos", e o teste que escrevi julga o `dashboard.css`. Mas `vendor/uPlot.min.css` declara `.u-legend th { font-weight: 600 }` e `.u-title { font-size: 18px }`. A tela FINAL teria três pesos e cinco tamanhos, com os dois testes verdes — porque o excesso vinha de um arquivo que os testes (corretamente) não julgam.
- **Fix:** O bloco de sobreposições passou a corrigir os dois: `.u-legend th { font-weight: 400 }` e `.u-title { display: none }` (o título é nosso, com reticência e o texto completo no atributo de título — o da biblioteca traria o quinto tamanho de volta).
- **Files modified:** `l2scanner/recursos/dashboard/dashboard.css`
- **Verification:** `test_a_escala_tipografica_tem_no_maximo_QUATRO_tamanhos` e `..._DOIS_pesos` passam, e as sobreposições estão no bloco nomeado, depois da folha da biblioteca.
- **Committed in:** `46a0d5d`

**2. [Rule 1 - Bug] Três comentários meus continham literais que meus próprios testes procuram**

- **Found during:** Tarefas 1 e 2
- **Issue:** Um comentário do HTML escrevia a frase proibida de espaço reservado por extenso; um comentário do CSS escrevia o nome da regra de importação; outros dois escreviam o nome da série. Os três testes acusaram — corretamente, porque as três buscas são literais sobre o arquivo inteiro, e essa severidade é a letra do UI-SPEC.
- **Fix:** **A prosa foi reescrita e nenhuma asserção foi enfraquecida.** Cada comentário agora descreve a regra sem escrever a literal, e diz por que não a escreve. Afrouxar a busca (ignorar comentários) teria sido a saída fácil e teria aberto a porta para um `content: "..."` num pseudo-elemento passar batido.
- **Files modified:** `l2scanner/recursos/dashboard/index.html`, `l2scanner/recursos/dashboard/dashboard.css`
- **Verification:** 77 testes verdes com as buscas na forma literal original.
- **Committed in:** `f7e0c1e`, `46a0d5d`

---

**Total deviations:** 2 auto-corrigidas (1 funcionalidade crítica ausente, 1 defeito).
**Impact on plan:** Nenhum desvio de escopo. A primeira é a que importa: sem ela, dois testes ficariam verdes sobre uma tela que viola o contrato que eles existem para prender.

## Issues Encountered

### A tabela de contraste do UI-SPEC tem dois rótulos generosos — os números estão certos

Ao recalcular, as oito razões reproduziram **exatamente** as medições publicadas (14,34 · 13,16 · 9,46 · 8,89 · 7,80 · 6,12 · 5,25 · 9,03). O documento tinha sido medido, e não estimado.

Mas a coluna **"Piso"** rotula `--cor-texto-fraco` sobre `--cor-painel` (6,12:1) como **`AAA (corpo)`**, e AAA para texto de corpo exige **7:1**. `--cor-alerta` (5,25:1) aparece como `AA+`, que não é um nível da norma. **As medições estão certas; os rótulos delas é que são generosos.**

O teste cobra o **número**, com o piso duro que o contrato escreve em prosa e que ambos cumprem com folga — *"nenhum texto da tela fica abaixo de 4,5:1"*. A divergência está escrita por extenso no próprio teste, ao lado da tabela de pares, em vez de copiada e esquecida. Nenhum token foi alterado: 6,12 e 5,25 são legíveis, e mexer na paleta para perseguir um rótulo mal escrito seria trocar uma cor boa por uma etiqueta.

### A suíte completa foi interrompida uma vez por causa do ambiente, e não por defeito

A primeira execução de `pytest tests/` terminou em `KeyboardInterrupt` dentro de `test_agenda.py`. `test_agenda.py` sozinho passa (145 testes), e a re-execução completa passou inteira. Não há relação com este plano — nenhum arquivo Python do pacote foi tocado.

## Known Stubs

Nenhum stub no sentido de "valor vazio codificado que chega à UI e finge ser dado". Há, sim, **lugares reservados que o plano 01-07 preenche**, e eles são a fronteira declarada entre os dois planos e não dívida:

| Elemento | Arquivo | Quem preenche |
|---|---|---|
| `#serie-vazio-prova` (a linha de prova, com os números reais) | `index.html` | 01-07, a partir de `avisos` |
| `#aviso-dado-velho`, `#faixa-erro`, `#nota-linha-parcial`, `#cambio-erro` | `index.html` | 01-07, com as frases prontas do Python |
| `#serie-titulo`, `#fonte-arquivo` (e os atributos de título deles) | `index.html` | 01-07 |
| `#xm-unidade`, `#reais-*`, `#fonte-n`, `#fonte-recencia`, `#cambio-carimbo` | `index.html` | 01-07 |
| `#serie-grafico` (a instanciação do uPlot) | `index.html` | 01-07 |

**Por que isto não deixa a tela muda enquanto 01-07 não chega:** as linhas alimentadas pelo servidor são governadas por `:empty` no CSS, então **não existe linha vazia visível** — elas simplesmente não aparecem até terem texto. E o `dashboard.js` do tracer já pinta `#xm-texto`, `#xm-n` e `#xm-recencia`, cujos identificadores foram **deliberadamente preservados** nesta reescrita: a página hoje já mostra o número em XM.

## Threat Flags

Nenhuma superfície nova. Os quatro itens do registro do plano estão atendidos, cada um com o teste que o prova:

| Threat ID | Mitigação | Prova |
|---|---|---|
| T-01-21 (origem externa de fonte ou imagem) | Só famílias do sistema; nenhuma origem externa, regra de importação ou fonte declarada | `test_a_pagina_nao_pede_UM_BYTE_a_rede` (CSS e HTML) |
| T-01-22 (nome vindo de OCR injetado no HTML) | Título com largura limitada, reticência e o texto completo no atributo de título; a inserção como TEXTO fica presa em 01-07 | `.serie__titulo` no CSS; `title=""` presente na marcação |
| T-01-23 (estilo ou script embutido) | As **três** formas afirmadas por parse: `src` em todo script, zero `<style>` **e zero atributo `style=`**, zero atributo `on*` | `test_todo_script_carrega_por_ARQUIVO`, `test_a_contagem_de_estilos_EMBUTIDOS_e_zero`, `test_a_contagem_de_atributos_de_EVENTO_e_zero` |
| T-01-24 (número longo estourando o painel) | `clamp` com largura tabular, `min-width: 0` no cartão, `maxlength` e largura em `ch` no campo, reticência nos textos longos | `test_todo_numero_da_tela_usa_LARGURA_TABULAR`, `test_o_campo_do_cambio_tem_LIMITE_de_comprimento` |

Sobre T-01-23: a asserção de estilo embutido foi ampliada para cobrir também o **atributo** `style=`, que o plano não pedia nominalmente. Um `style="color: ..."` num elemento seria a segunda paleta do projeto, escondida na marcação — e a CSP o bloquearia calado.

## Verification

| Portão do plano | Resultado |
|---|---|
| `python -m pytest tests/test_dashboard_pagina.py -q` | **77 passed** |
| `python -m pytest tests/ -q` | **4708 passed, 25 skipped** |
| `git diff --stat requirements.txt` | vazio |
| Nenhum `.py` do pacote no diff | confirmado — só `index.html`, `dashboard.css` e o teste novo |
| Pelo menos 20 testes coletados (Tarefa 3) | 77 |

O `dashboard.py` e o `dashboard.js` não foram tocados (cerca de escopo do despacho paralelo respeitada), e o controle negativo do tracer — `test_o_js_nao_carrega_paleta_PROPRIA`, que exige achar hexadecimais no CSS — continua verde.

## User Setup Required

Nenhuma. Nenhuma dependência nova, nenhuma etapa de build, nenhum serviço externo.

## Next Phase Readiness

**Pronto para 01-07 (o JS):**

- Todos os identificadores estão travados e afirmados por parse; o contrato entre a marcação e o JS é conferível.
- Os quatro atributos de estado nascem no `<body>` com o valor mais conservador (`primeira_pintura` / `ausente` / `nao` / `ok`). O JS só troca valores.
- Os nomes de `data-estado` são exatamente os de `dashboard_dados`, então mapear payload → tela é uma atribuição, e não uma tradução.
- As cores estão todas nomeadas como token, então `getPropertyValue` alcança todas — inclusive `--cor-grade` e `--cor-serie-tipica`, que a configuração do gráfico precisa.
- Nenhuma decisão visual precisa ser escrita em JS: o botão troca de rótulo por atributo, e as linhas do servidor aparecem sozinhas quando deixam de estar vazias.

**Pendências declaradas:**

- **A verificação humana da Tarefa 3** (D11) não pôde ser executada — não há teste de layout de navegador nesta árvore. Registrada no ledger de defeitos como `unrun-verify` (entrada 45). É o julgamento visual do tema: o número em destaque é a primeira coisa que o olho encontra, o texto sobre o relevo continua legível, e o cartão de R$ realmente SOME em vez de ficar cinza.
- **O ornamento de canto** fica disponível para uma decisão futura, com a condição de aceitação já escrita no UI-SPEC. Ele não entrou nesta entrega.

## Self-Check: PASSED

Cada afirmação deste documento foi conferida contra o disco e contra o histórico:

- **Arquivos:** `index.html` (12445 B), `dashboard.css` (27705 B), `tests/test_dashboard_pagina.py` (40705 B) e este SUMMARY — os quatro existem.
- **Commits:** `f7e0c1e`, `46a0d5d`, `c29f597` — os três existem no histórico deste worktree.
- **Suíte:** 77 testes no arquivo novo, 4708 na árvore inteira, zero falhas.
- **Cerca de escopo:** `git diff --name-only` sobre a base de conteúdo devolve só os três arquivos deste plano. `dashboard.py`, `dashboard.js` e `requirements.txt` não foram tocados.

---
*Phase: 01-dashboard-do-cambio-ao-vivo*
*Plan: 06*
*Completed: 2026-09-01*
