---
phase: 01-dashboard-do-cambio-ao-vivo
plan: 07
subsystem: ui
tags: [javascript, polling, uplot, csp, zoom, tripwire-de-fonte, dash-05]

requires:
  - phase: 01-02
    provides: "o payload: precedencia fechada dos cinco estados, `series` como lista, `pontos` por instante e `baldes` nas tres larguras, e a mediana ausente como `null` e nunca `0.0`"
  - phase: 01-04
    provides: "a biblioteca de grafico vendorizada com VEND-1..3 fechados, e a nota que ja registrava a refutacao do zoom por roda"
  - phase: 01-05
    provides: "`intervalo_de_polling_ms` dentro do payload, o contrato do `POST /cambio` com as cinco recusas distintas, e a CSP que torna o submit nativo impossivel"
  - phase: 01-06
    provides: "os quatro atributos de estado no `<body>`, os identificadores travados, os dois rotulos do botao na marcacao e todos os tokens de cor nomeados"
provides:
  - "o laco de polling com o intervalo LIDO do payload, e o rescheduling depois de assentar (sem fila de consultas com o servidor morto)"
  - "a pintura por atribuicao da chave de estado que o servidor decidiu — nenhuma comparacao de contagem com piso existe no navegador"
  - "o componente de serie generico: um elemento de `series` entra, um grafico sai, e o nome da serie de hoje nao aparece no JS nem no CSS"
  - "as quatro cores pedidas ao CSS por nome de token, e a fonte dos rotulos LIDA de um elemento que o CSS ja dimensionou"
  - "o zoom por roda em torno do cursor e o deslocamento por arrasto, escritos por nos, com a medicao que os obrigou ao lado"
  - "o envio do cambio interceptado, com o valor preservado no campo em toda recusa"
  - "tests/test_dashboard_js.py — 41 tripwires de fonte, cada sonda de ausencia com controle, mais um portao de sintaxe de verdade"
affects: [01-08, verificacao-da-fase-1]

actuals:
  tokens: 22250
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Sonda de fonte que le SO O CODIGO: comentarios sao removidos antes de julgar, porque uma sonda que pune o arquivo por NOMEAR o defeito que ele evita ensina a apagar a explicacao"
    - "Regiao delimitada por sentinela no fonte para dar fronteira DECIDIVEL a uma assercao de contrato (`<<< COMPONENTE-DE-SERIE`)"
    - "Acoplamento por posicao ASSUMIDO no fonte e PRESO por teste sobre payloads reais, em vez de escondido ou de resolvido com uma segunda copia das frases"
    - "Numero de apresentacao que mora num lugar so, sem repeticao no outro: a duracao do pulso fica no CSS e quem apaga o atributo e o fim da animacao"
    - "Portao de sintaxe com pulo NOMEADO: `node --check` roda quando a ferramenta existe e pula com a razao dita quando nao existe"

key-files:
  created:
    - tests/test_dashboard_js.py
  modified:
    - l2scanner/recursos/dashboard/dashboard.js

key-decisions:
  - "A biblioteca de grafico passou a ser carregada PELO `dashboard.js`: o `index.html` nunca ganhou a linha que carrega o codigo dela (so a folha de estilo), e o `index.html` esta fora do alcance deste plano. A carga por codigo e legitima sob `script-src 'self'`, e o caminho e constante deste arquivo — nunca vem do payload"
  - "Os vaos de unidade da marcacao ficam VAZIOS: o payload dobra a unidade dentro de `destaque.xm.texto`, e parti-la no navegador seria o segundo formatador. A string vai inteira para onde ela cabe"
  - "A resolucao do desenho troca por um gancho unico de mudanca de escala, e nao por uma chamada repetida em cada manipulador: caminhos que se esquecem de avisar sao como a resolucao passa a discordar da janela"
  - "O deslocamento mora na tecla de maiusculas e no botao do meio, porque o arrasto simples ja e o zoom por selecao NATIVO e o plano manda nao reescreve-lo"
  - "Nenhuma validacao de cambio no navegador: o julgamento e inteiro do servidor, e um 'e numero positivo?' aqui seria um SEGUNDO validador com a mesma doenca do segundo formatador"
  - "A instancia do grafico e reaproveitada entre voltas: recria-la a cada resposta jogaria fora o zoom do usuario de dois em dois segundos, sem quebrar nada em voz alta"

patterns-established:
  - "Sonda de codigo x sonda de prosa: as de codigo leem o fonte sem comentarios, as de prosa (refutacao) leem o texto inteiro — e a premissa do removedor tem teste proprio"
  - "Toda propriedade a MAIS ou a MENOS em relacao a um contrato escrito e nomeada no fonte com a razao, e presa por igualdade de conjunto no teste"
  - "Refutacao com o NUMERO e a citacao, e nao so a conclusao: quem for atualizar a biblioteca pode REFAZER a medicao e comparar"

requirements-completed: [DASH-02, DASH-03, DASH-04, DASH-05]

coverage:
  - id: D1
    description: "A tela se atualiza sozinha obedecendo o intervalo que o servidor manda, e o navegador nao tem um segundo numero proprio"
    requirement: DASH-02
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOPollingObedeceOIntervaloDoSERVIDOR::test_o_numero_do_servidor_NAO_aparece_como_literal_no_js"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOPollingObedeceOIntervaloDoSERVIDOR::test_o_js_LE_a_chave_do_intervalo_que_vem_no_payload"
        status: pass
    human_judgment: false
  - id: D2
    description: "O polling nunca reintroduz estado de carregamento, e nao existe indicador giratorio na tela"
    requirement: DASH-02
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOPollingObedeceOIntervaloDoSERVIDOR::test_o_polling_NAO_reintroduz_o_estado_de_carregamento"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOPollingObedeceOIntervaloDoSERVIDOR::test_nao_existe_indicador_giratorio_em_lugar_nenhum"
        status: pass
    human_judgment: false
  - id: D3
    description: "Nenhuma string do Python e reescrita no navegador — sem arredondamento de casas fixas, sem numero local, sem substituicao de virgula"
    requirement: DASH-03
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOJSNaoEUmSegundoFormatador::test_nenhuma_reformatacao_de_numero_ou_de_texto_vinda_do_payload"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOJSNaoEUmSegundoFormatador::test_CONTROLE_as_sondas_ACUSAM_um_segundo_formatador_de_verdade"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOJSNaoEUmSegundoFormatador::test_o_paragrafo_de_refutacao_esta_no_TOPO_do_arquivo"
        status: pass
    human_judgment: false
  - id: D4
    description: "Todo texto do servidor entra por propriedade de TEXTO, e nunca por marcacao (T-01-22: o nome exibido atravessa o OCR)"
    requirement: DASH-04
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOJSInsereTEXTOeNaoMARCACAO::test_a_contagem_de_atribuicoes_a_propriedade_de_MARCACAO_e_zero"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOJSInsereTEXTOeNaoMARCACAO::test_CONTROLE_as_sondas_ACUSAM_uma_insercao_de_marcacao_de_verdade"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOJSInsereTEXTOeNaoMARCACAO::test_o_texto_do_servidor_entra_por_propriedade_de_TEXTO"
        status: pass
    human_judgment: false
  - id: D5
    description: "A chave de estado e apenas LIDA: nenhuma comparacao de contagem com piso de evidencia existe no navegador"
    requirement: DASH-04
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOEstadoEhLIDOeNaoRECALCULADO::test_nenhuma_comparacao_de_contagem_com_um_piso_dentro_do_js"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOEstadoEhLIDOeNaoRECALCULADO::test_nenhum_dos_tres_pisos_aparece_como_comparacao_no_js"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOEstadoEhLIDOeNaoRECALCULADO::test_CONTROLE_a_sonda_ACUSA_uma_comparacao_de_verdade"
        status: pass
    human_judgment: false
  - id: D6
    description: "A ordem dos avisos, de que a pintura depende por posicao, e contrato preso por teste sobre payloads REAIS"
    requirement: DASH-04
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestAOrdemDosAvisosEhOCONTRATO::test_o_bloco_do_estado_vazio_tem_TRES_avisos_e_a_prova_e_o_TERCEIRO"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestAOrdemDosAvisosEhOCONTRATO::test_o_aviso_de_dado_velho_vem_LOGO_DEPOIS_da_nota_de_linha_parcial"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestAOrdemDosAvisosEhOCONTRATO::test_a_linha_de_reais_e_SEMPRE_o_ultimo_aviso"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestAOrdemDosAvisosEhOCONTRATO::test_a_recencia_fresca_NAO_produz_aviso_de_dado_velho"
        status: pass
    human_judgment: false
  - id: D7
    description: "O componente de serie e generico: a palavra que nomeia a serie de hoje nao esta no JS nem no CSS, e ESTA no payload servido"
    requirement: DASH-05
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOComponenteDeSerieEGenerico::test_a_palavra_que_nomeia_a_serie_NAO_esta_no_js_nem_no_css"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOComponenteDeSerieEGenerico::test_a_funcao_de_serie_usa_EXATAMENTE_as_propriedades_do_contrato"
        status: pass
    human_judgment: false
  - id: D8
    description: "A paleta mora num lugar so: zero hexadecimal no JS, e as quatro cores pedidas por nome de token que o CSS de fato declara"
    requirement: DASH-05
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOComponenteDeSerieEGenerico::test_a_contagem_de_hexadecimais_de_cor_no_js_e_zero"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOComponenteDeSerieEGenerico::test_a_cor_e_PEDIDA_ao_css_por_nome_de_token"
        status: pass
    human_judgment: false
  - id: D9
    description: "As duas linhas se distinguem por TRACO alem de por cor, e o vao da mediana ausente e vao e nunca zero"
    requirement: DASH-03
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOComponenteDeSerieEGenerico::test_as_duas_linhas_diferem_em_TRACO_alem_de_diferir_em_COR"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOComponenteDeSerieEGenerico::test_o_vao_da_mediana_ausente_e_VAO_e_nunca_zero"
        status: pass
    human_judgment: false
  - id: D10
    description: "A dica sob o cursor e montada das chaves de TEXTO do ponto, e nao das numericas (o float e o pixel, a string e a verdade)"
    requirement: DASH-03
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOComponenteDeSerieEGenerico::test_a_dica_sob_o_cursor_vem_das_chaves_de_TEXTO"
        status: pass
    human_judgment: false
  - id: D11
    description: "O zoom por roda existe, e escrito por nos sobre a sobreposicao, e a refutacao ao lado traz a MEDICAO e nao so a conclusao"
    requirement: DASH-02
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOZoomEDeNosEDizPorQue::test_a_roda_e_registrada_sobre_a_SOBREPOSICAO_do_grafico"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOZoomEDeNosEDizPorQue::test_a_roda_chama_o_metodo_de_definicao_de_ESCALA"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOZoomEDeNosEDizPorQue::test_o_bloco_de_refutacao_traz_a_MEDICAO_e_nao_so_a_conclusao"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOZoomEDeNosEDizPorQue::test_o_pedido_de_nao_rolar_a_pagina_e_REGISTRADO_como_nao_passivo"
        status: pass
    human_judgment: false
  - id: D12
    description: "O zoom das horas do dia ate dias atras FUNCIONA na tela: a roda aproxima em torno do cursor, o arrasto desloca a janela, e o botao devolve o periodo inteiro"
    verification:
      - kind: manual_procedural
        ref: "roteiro do <human-check> da Tarefa 3 do 01-07-PLAN.md"
        status: unknown
    human_judgment: true
    rationale: "Assercao de fonte cai numa implementacao vazia, num evento errado ou numa API errada — mas NAO distingue um zoom que funciona de um registrador que faz a coisa errada. Nenhuma assercao sobre texto consegue, e a casa recusou instalador pesado de automacao de navegador por doutrina. O criterio 5 do ROADMAP repousa aqui, e isso esta dito por extenso no <success_criteria> do proprio plano."
  - id: D13
    description: "O envio do cambio e interceptado e salva sem recarregar; na recusa a frase vem do servidor e o valor digitado permanece no campo"
    requirement: DASH-04
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOEnvioDoCambioEInterceptado::test_o_manipulador_de_envio_IMPEDE_o_comportamento_padrao"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOEnvioDoCambioEInterceptado::test_no_caminho_de_ERRO_o_valor_digitado_PERMANECE_no_campo"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOEnvioDoCambioEInterceptado::test_a_frase_da_recusa_vem_do_SERVIDOR_e_nao_daqui"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOEnvioDoCambioEInterceptado::test_o_botao_e_desabilitado_durante_o_envio_e_volta_DEPOIS"
        status: pass
    human_judgment: false
  - id: D14
    description: "O arquivo ANALISA: nenhuma sonda de texto ve um erro de sintaxe, e um arquivo que nao analisa deixa a pagina inteira parada"
    verification:
      - kind: unit
        ref: "tests/test_dashboard_js.py#TestOArquivoAoMenosANALISA::test_o_dashboard_js_ANALISA_sem_erro"
        status: pass
    human_judgment: false

duration: 34min
completed: 2026-09-02
status: complete
---

# Phase 01 Plan 07: O codigo do navegador Summary

**A tela virou viva: o polling obedece o intervalo que vem dentro do payload, a pintura apenas ATRIBUI a precedencia que o servidor ja decidiu, o grafico e desenhado por uma funcao que nao sabe qual serie esta desenhando, e o zoom por roda — que a medicao provou que a biblioteca nao tem — foi escrito por nos com a contagem e a citacao oficial ao lado do codigo.**

## Performance

- **Duration:** 34 min
- **Started:** 2026-09-02T00:12:00-03:00
- **Completed:** 2026-09-02T00:46:00-03:00
- **Tasks:** 3 de 3
- **Files modified:** 2 (1 criado, 1 reescrito)

## Accomplishments

- **O laco de polling nao tem um numero proprio.** O intervalo vem de `intervalo_de_polling_ms`, dentro da resposta, e ha teste afirmando que o numero do servidor nao aparece como literal no JS. Se a cadencia mudar no `dashboard.py`, o navegador acompanha sozinho.
- **O estado e lido, e nunca recalculado.** A pintura e uma ATRIBUICAO: os nomes de `data-estado` sao exatamente os de `dashboard_dados.ESTADOS`. Tres sondas afirmam que nenhuma comparacao de contagem com piso de evidencia existe no arquivo — nem `.n <`, nem `n < 5`, nem os tres pisos importados de onde eles moram.
- **O componente de serie e generico por construcao.** Ele recebe um elemento de `series` e mais nada; o conjunto de propriedades que ele le e afirmado por IGUALDADE de conjunto contra o contrato, e a palavra que nomeia a serie de hoje nao aparece no JS nem no CSS — enquanto APARECE, viva, no payload servido. Instanciar a segunda serie e passar `dados.series[1]`.
- **O zoom e nosso, e o fonte diz por que com numero.** A refutacao esta escrita acima do codigo: ZERO registradores de roda em duas das tres candidatas, `2x wheel` na terceira, a citacao textual *"No built-in drag scrolling/panning"* da documentacao oficial, e os tres motivos pelos quais a candidata que trazia o evento pronto foi recusada mesmo assim.
- **O cambio salva sem recarregar, e uma recusa nao apaga nada.** O envio e interceptado (sem isso a diretiva de destino de formulario o bloquearia em silencio), a frase da recusa vem pronta do servidor, e nao existe atribuicao de valor vazio ao campo em caminho nenhum do arquivo.
- **41 testes, e cada sonda de ausencia tem controle.** Mais um portao que nenhuma sonda de texto substitui: `node --check` sobre o arquivo, com pulo nomeado quando a ferramenta nao existe na maquina.

## Task Commits

1. **Tarefa 1: O polling e a maquina de estados** — `3184f0a` (feat)
2. **Tarefa 2: O componente de serie generico e a instanciacao do grafico** — `2202376` (feat)
3. **Tarefa 3: O zoom escrito por nos, e o envio do cambio sem recarregar** — `37d7f34` (feat)

## Files Created/Modified

- `l2scanner/recursos/dashboard/dashboard.js` — o laco de polling, a pintura por atributo de estado, o estado de servidor mudo, o pulso de valor mudado, o componente de serie generico, a leitura de cores por token, o zoom por roda e o deslocamento por arrasto, o botao de alcance total e o envio do cambio interceptado
- `tests/test_dashboard_js.py` — 41 tripwires: nenhum segundo formatador, nenhuma insercao de marcacao, nenhum literal de cor, nenhuma mencao da serie no codigo do grafico, a refutacao presente com a medicao, a prevencao do comportamento padrao no envio, e a ordem dos avisos presa sobre payloads reais

## Decisions Made

### 1. A biblioteca de grafico e carregada pelo `dashboard.js`, e nao pela marcacao

**Achado durante a Tarefa 2.** O `index.html` carrega a FOLHA DE ESTILO da biblioteca (`vendor/uPlot.min.css`) e o `dashboard.css` retematiza o que ela desenha — mas a marcacao **nunca ganhou a linha que carrega o CODIGO dela**. Sem essa linha o objeto global nao existe, e o grafico nao poderia ser instanciado de jeito nenhum: a Tarefa 2 inteira entregaria codigo morto.

O conserto mais simples e uma linha de `<script src>` no `index.html`, ao lado da que ja carrega o `dashboard.js` — e o teste de marcacao da fase **aceita varios scripts**, desde que todos carreguem por arquivo (`test_todo_script_carrega_por_ARQUIVO` usa `all("src" in ...)`, nao uma contagem). Esse conserto **nao foi feito** porque o `index.html` esta na cerca de alcance declarada deste plano.

A carga por codigo e legitima e nao afrouxa nada: `script-src 'self'` proibe a forma EMBUTIDA e a origem de fora, nao a criacao de um elemento com origem propria; e o caminho e uma constante do arquivo, nunca um valor vindo do payload. Nos dois desfechos — carregou ou nao — o destaque, a procedencia e o campo do cambio continuam funcionando: perder o grafico nao pode custar a metade da tela que responde "quanto vale agora".

**Registrado no ledger de defeitos como `deviation`**, com o conserto de uma linha nomeado.

### 2. Os vaos de unidade da marcacao ficam vazios

A marcacao reservou `xm-unidade` e `reais-unidade` esperando receber a unidade separada do numero. O payload nao entrega os dois separados: ele entrega UMA string pronta de `formatar_taxa_derivada`. Partir essa string no navegador — num espaco, numa virgula — seria dar ao navegador uma opiniao sobre onde termina o numero e comeca a unidade, e essa opiniao erraria no dia em que o formatador do Python mudasse. **A string vai inteira para onde ela cabe, e o vao fica vazio.** O conserto certo e do lado do Python, e esta registrado.

### 3. O deslocamento nao mora no arrasto simples

O arrasto com o botao principal ja e o zoom por selecao NATIVO da biblioteca, e o plano manda nao reescreve-lo. Os dois gestos colidem, entao o deslocamento mora no arrasto com a tecla de maiusculas pressionada e no arrasto com o botao do meio. **Isso muda o roteiro de verificacao humana** — ver a secao de pendencias abaixo.

### 4. Nenhuma validacao de cambio no navegador

As unicas conveniencias do lado do cliente sao o comprimento maximo e o tipo de teclado, e as duas ja moram na marcacao. O JULGAMENTO e inteiro do servidor: escrever aqui um "e numero positivo?" seria um SEGUNDO validador, com a mesma doenca do segundo formatador — duas opinioes sobre a mesma pergunta, divergindo em silencio.

### 5. A ordem dos avisos virou contrato, em vez de virar uma segunda copia das frases

`avisos` e uma lista de strings sem rotulo, e tres delas tem lugar proprio na tela. Achar cada uma pelo TEXTO exigiria copiar as frases do Python para dentro do JS — a segunda copia que o DASH-03 recusa. Entao a posicao e derivada dos fatos estruturais que o payload ja carrega, o acoplamento esta **escrito** no fonte, e quatro testes o prendem sobre payloads REAIS: se alguem reordenar os avisos no Python, eles ficam vermelhos.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] A biblioteca de grafico nunca era carregada pela pagina**

- **Found during:** Tarefa 2 (o componente de serie)
- **Issue:** `index.html` carrega `vendor/uPlot.min.css` mas nao `vendor/uPlot.iife.min.js`. O objeto global nao existiria no navegador, e toda a Tarefa 2 seria codigo morto.
- **Fix:** `dashboard.js` carrega a biblioteca na partida, por criacao de elemento com origem propria (permitido por `script-src 'self'`), e chama o laco depois — em sucesso ou em falha, para a metade nao-grafica da pagina continuar viva. A cerca de alcance deste plano proibe tocar o `index.html`, entao o conserto de uma linha na marcacao ficou **nomeado** em vez de feito.
- **Files modified:** `l2scanner/recursos/dashboard/dashboard.js`
- **Verification:** `node --check` passa; `tests/test_dashboard_js.py` verde; ledger de defeitos com a entrada e o conserto.
- **Committed in:** `2202376`

**2. [Rule 2 - Missing critical] Um portao de sintaxe de verdade**

- **Found during:** Tarefa 2
- **Issue:** Nenhuma das 40 assercoes sobre TEXTO ve um erro de sintaxe — e um arquivo que nao analisa nao executa NADA: a pagina fica parada no rotulo de leitura em curso, sem numero, sem grafico e sem formulario. Era o modo de falha mais caro possivel e o mais barato de pegar.
- **Fix:** `TestOArquivoAoMenosANALISA` roda `node --check` sobre o arquivo. O `node` nao virou dependencia (nada foi acrescentado ao `requirements.txt`): quando ele existe, o teste roda; quando nao existe, ele pula com a razao dita, para nao virar um silencio com cara de verde.
- **Files modified:** `tests/test_dashboard_js.py`
- **Verification:** o teste roda e passa nesta maquina.
- **Committed in:** `2202376`

**3. [Rule 1 - Bug na propria sonda] As sondas de codigo acusavam os comentarios**

- **Found during:** Tarefa 1
- **Issue:** Medido: a primeira versao das sondas rodava sobre o arquivo inteiro e acusou o proprio `dashboard.js` quatro vezes — todas dentro de comentarios que explicam por que o defeito NAO esta ali (o paragrafo sobre os pisos morarem no Python, e o que diz que nao existe indicador giratorio).
- **Fix:** `_so_o_codigo()` remove os comentarios antes das sondas de CODIGO; as de PROSA (a refutacao no topo) seguem lendo o texto inteiro, de proposito. Uma sonda que pune o arquivo por NOMEAR o defeito que ele evita ensina a apagar a explicacao. A premissa do removedor — nenhum comentario no fim de linha de codigo — ganhou teste proprio, para nao virar silenciosamente errada.
- **Files modified:** `tests/test_dashboard_js.py`
- **Verification:** `test_o_removedor_de_comentarios_CONTINUA_correto`
- **Committed in:** `3184f0a`

---

**Total deviations:** 3 auto-fixed (1x Rule 3, 1x Rule 2, 1x Rule 1)
**Impact on plan:** Nenhum aumento de escopo. A cerca de alcance foi respeitada: `dashboard.py`, `index.html`, `dashboard.css`, os modulos do mercado e o `requirements.txt` seguem intocados (`git diff --stat requirements.txt` sai vazio).

## Issues Encountered

**O `n` por instante nao aparece na dica em toda resolucao.** O `01-UI-SPEC.md` pede que a dica mostre instante, os dois valores e `n`. Na resolucao crua o `n` viaja junto do instante; nas resolucoes de balde ele **nao existe** — e isso e honestidade, nao esquecimento: `n` e a contagem de ofertas de UM instante, e um balde e varios instantes; somar as contagens produziria um numero que nao qualifica o valor exibido, que e o de um instante so, escolhido por mediana inferior entre os do balde. A alternativa (uma terceira serie so para a legenda, com escala propria) foi recusada por ser um floreio nao verificavel nesta arvore: se ela quebrasse, derrubaria o grafico inteiro. Registrado no ledger.

## User Setup Required

Nenhuma. Nenhuma dependencia nova, nenhuma etapa de build, nenhum servico externo. O `node` e usado por UM teste e pula quando ausente.

## Known Stubs

Nenhum stub no sentido de "valor vazio codificado que chega a UI e finge ser dado". Nao ha valor fabricado, padrao chutado nem caminho que responda com espaco reservado — a ausencia continua sendo escrita com palavra vinda do Python, e a mediana ausente continua sendo vao e nunca zero.

As tres pendencias declaradas estao no ledger de defeitos da fase, e nenhuma delas produz numero falso na tela:

| Item | Arquivo | Natureza |
|---|---|---|
| `index.html` nao carrega o codigo da biblioteca | `l2scanner/recursos/dashboard/index.html` | costura entre planos; contornada em tempo de execucao, conserto de uma linha nomeado |
| Os vaos de unidade ficam vazios | `l2scanner/recursos/dashboard/dashboard.js` | o payload dobra a unidade dentro do texto; partir a string seria o segundo formatador |
| `n` ausente na dica das resolucoes de balde | `l2scanner/recursos/dashboard/dashboard.js` | somar contagens de instantes distintos nao qualificaria o valor exibido |

## A fronteira desta prova, dita por extenso

Os criterios de zoom sao **assercoes sobre o TEXTO** do `dashboard.js`. Elas caem se a implementacao estiver vazia, se o evento errado for registrado, se ele for pendurado no elemento errado ou se a API de escala nao for chamada — mas elas **nao distinguem um zoom por roda que funciona de um registrador que faz a coisa errada**. Nenhuma assercao de fonte consegue, e a casa recusou instalador pesado de automacao de navegador por doutrina.

**Portanto: o criterio 5 do ROADMAP — zoom das horas do dia ate dias atras — repousa no roteiro de verificacao humana da Tarefa 3, e isso e verificacao humana DECLARADA, e nao cobertura automatica.** O que o automatico garante e o piso (existe codigo, ele registra o evento certo no elemento certo, e chama a API certa); o teto e o olho, no fim da fase.

**O roteiro humano mudou num ponto, por causa da colisao de gestos:** o arrasto **simples** continua sendo o zoom por selecao nativo da biblioteca; **o deslocamento e com a tecla de maiusculas pressionada, ou com o botao do meio**. Quem for conferir precisa saber disso, ou vai concluir que o deslocamento nao funciona.

## Next Phase Readiness

**Pronto para o `01-08` (o `.bat`) e para a verificacao da fase:**

- A pagina esta completa: ela consulta, pinta, desenha, da zoom e salva o cambio. Nada mais do lado do navegador esta pendente.
- Nenhum arquivo Python foi tocado por este plano, e a cerca de alcance foi respeitada inteira.
- `python -m pytest tests/ -q` termina em 0: **4827 passed, 26 skipped**.

**O que o proximo precisa saber:**

- **A linha que falta no `index.html`** e a primeira coisa a fechar na verificacao da fase. Enquanto ela nao existir, a biblioteca e carregada em tempo de execucao — funciona, mas o caminho estatico e melhor e custa uma linha.
- **O roteiro de verificacao humana** esta acima, com a correcao do gesto de deslocamento.
- **A ordem dos avisos e contrato agora.** Qualquer mudanca em `dashboard_dados.payload` que reordene `avisos` quebra quatro testes de proposito — e a mensagem deles aponta para o acoplamento por posicao no `dashboard.js`.

## Self-Check: PASSED

Cada afirmacao deste documento foi conferida contra o disco e contra o historico:

- **Arquivos:** `l2scanner/recursos/dashboard/dashboard.js` (50022 B), `tests/test_dashboard_js.py` (38978 B) e este SUMMARY — os tres existem.
- **Commits:** `3184f0a`, `2202376`, `37d7f34` — os tres existem no historico deste worktree.
- **Testes:** `python -m pytest tests/test_dashboard_js.py -q` -> **41 passed**; `python -m pytest tests/test_dashboard_js.py tests/test_dashboard_pagina.py -q` -> **118 passed**; `python -m pytest tests/ -q` -> **4827 passed, 26 skipped**.
- **Cerca de alcance:** `git diff --stat requirements.txt` sai vazio; `git status --short` nao lista `dashboard.py`, `index.html`, `dashboard.css` nem nenhum modulo do mercado.
- **Sintaxe:** `node --check l2scanner/recursos/dashboard/dashboard.js` sai 0.
