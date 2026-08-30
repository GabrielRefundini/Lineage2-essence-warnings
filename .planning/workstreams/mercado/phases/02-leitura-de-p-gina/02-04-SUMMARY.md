---
phase: 02-leitura-de-p-gina
plan: 04
subsystem: api
tags: [opencv, numpy, template-matching, ocr, tracer, promocao, pipeline, falha-fechada]

requires:
  - phase: 02-leitura-de-p-gina
    provides: "a grade de negociacao, as 4 colunas e o molde do cabecalho do 02-01"
  - phase: 02-leitura-de-p-gina
    provides: "a sonda de oclusao, o limiar de dispersao, o piso e a margem de LEITURA do 02-02"
  - phase: 02-leitura-de-p-gina
    provides: "os predicados de agrupamento, o corte/piso de similaridade e a fonte `ocr-estrito` do 02-03"
  - phase: 01-funda-o-firewall-gravador-e-spike-de-campo
    provides: "as 8 gravacoes de campo, os 13 moldes de glifo e as 3 ancoras"
provides:
  - "`l2scanner/mercado_leitura.py` — o transform PURO pixels -> `LinhaLida | Descarte | None`"
  - "`l2scanner/mercado_pagina.py` — `LeitorDePagina`, a maquina de estado da pagina"
  - "a PROMOCAO de 9 primitivas de ferramenta para producao, sem duplicar nenhuma"
  - "o ACORDO entre as duas escalas CONSTRUIDO, com a mecanica '3x manda, 2x confere' do 02-03"
  - "a ordem do pipeline PRESA POR TESTE: layout -> vazia -> sonda -> numeros -> OCR"
  - "a REFUTACAO de tres fixturas que o plano nomeou, cada uma com o numero que a derrubou"
  - "a REFUTACAO de A7: o digito `1` da coluna Quantity nao se le (V=177 contra piso 180)"
  - "6 fixturas de janela/banda versionadas novas, e a calibracao de fixtura"
affects: [02-05, 02-06, Fase 3, Fase 4, catalogo de series, CSV de observacoes]

actuals:
  tokens: 34000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "promocao de primitiva de FERRAMENTA para PRODUCAO movendo o codigo com a docstring inteira, e fazendo a ferramenta importar de volta — a seta aponta sempre tool -> puro"
    - "a ordem do pipeline como decisao documentada e PRESA POR CONTAGEM DE CHAMADAS, nao por comentario"
    - "o mecanismo caro (a segunda leitora) provado pela CHAMADA e nao pela existencia: contador injetado sobre fixtura conhecida"
    - "peneiras em cascata com MOTIVOS distintos, uma por causa, porque os consertos sao diferentes"
    - "tres estados no retorno (lida, descartada, vazia) em vez de dois, para a contagem do console nunca chamar fim de pagina de perda"
    - "latch em vez de rate-limit para log de ESTADO (o portao de layout), e sem limite nenhum para log de EVENTO (a recusa de linha)"

key-files:
  created:
    - l2scanner/mercado_leitura.py
    - l2scanner/mercado_pagina.py
    - tests/test_mercado_leitura.py
    - tests/test_mercado_pagina.py
    - tests/fixtures/mercado/calibracao_de_fixture.json
    - tests/fixtures/mercado/janela_negociacao_f005.png
    - tests/fixtures/mercado/janela_negociacao_f005_repetida.png
    - tests/fixtures/mercado/janela_tooltip_f012.png
    - tests/fixtures/mercado/janela_com_linhas_vazias.png
    - tests/fixtures/mercado/janela_adena_f014.png
    - tests/fixtures/mercado/cabecalho_adena.png
    - tests/fixtures/mercado/cabecalho_busca.png
    - tests/fixtures/mercado/linha_vazia_par.png
    - tests/fixtures/mercado/linha_vazia_impar.png
  modified:
    - l2scanner/calibrar_mercado.py
    - tools/medir_leitura_de_glifo.py
    - tests/test_mercado_glifos.py
    - tests/test_medir_leitura_de_glifo.py

key-decisions:
  - "A ordem do pipeline e layout -> linha vazia -> sonda de oclusao -> as duas colunas de NUMERO -> o OCR do nome. Os numeros vem ANTES do OCR porque custam 13 casamentos por run contra ~7 ms de OCR, e uma linha cujo preco nao se le nao vira dado de jeito nenhum. Essa ordem e o que torna o criterio central verdadeiro: sobre `janela_negociacao_f010.png`, as linhas em que AMBAS as leitoras foram chamadas sao EXATAMENTE as 2 que viraram `LinhaLida`."
  - "O acordo entre as escalas usa a mecanica '3x MANDA, 2x CONFERE com entrada PROVISORIA' que `tools/medir_agrupamento_de_nome.py` mediu — reproduzida, nao reinventada. Sem a provisoria, a primeira aparicao de um item cujas escalas discordem num caractere criaria DUAS series de chaves diferentes e a linha morreria: o predicado teria virado igualdade de string pela porta dos fundos, que e a rota `ocr-igualdade` que o 02-03 recusou."
  - "A serie so NASCE quando a pagina foi ACEITA por dois frames. Gravar no primeiro criaria serie a partir de uma leitura que o segundo ainda pode desmentir, e a Fase 3 referencia a chave em cada observacao do CSV."
  - "O `nome_exibido` vem SEMPRE da escala de conferencia (3x), por regra escrita: duas execucoes sobre o mesmo frame tem de gravar o mesmo rotulo."
  - "`linha_vazia` NAO recebe os moldes que o plano previa: nenhum molde participa da decisao, e um parametro que a funcao nao usa e uma promessa que ela nao cumpre. O piso e o do SUFIXO (V > 120), o mais permissivo dos dois medidos, porque a afirmacao e a mais forte possivel."
  - "`layout_confere` recebe o `dx_da_grade` por parametro: ele NAO esta no dict do cabecalho, e a ausencia e deliberada — a banda tem a largura da grade e comeca onde ela comeca, e gravar o `dx` duas vezes criaria duas verdades para uma geometria."
  - "O log do portao de layout tem LATCH (registra quando o veredito MUDA) enquanto o da recusa de linha nao tem limite nenhum. A diferenca: a recusa de linha e um EVENTO episodico e o layout errado e um ESTADO — com a aba Adena aberta, uma linha por captura, para sempre, sem forense nova."
  - "A calibracao de fixtura copia VERBATIM as chaves `mercado_*` da de producao (a alternativa, um layout de brinquedo, foi recusada pelo usuario) e substitui APENAS as chaves de party por valores neutros, para nao versionar nome e recorte de tela de gente real."
  - "As primitivas de gramatica de numero (`centesimos_de_moeda`, `inteiro_de_quantidade`, `pontuar_celula`) foram promovidas de `tools/medir_leitura_de_glifo.py` junto com as de `calibrar_mercado.py`. Duplica-las teria feito a ferramenta MEDIR com uma convencao e a producao DECIDIR com outra."

patterns-established:
  - "Uma medicao que refuta o plano vira teste com o numero na docstring, e o plano nao e obedecido contra a medicao: este plano refutou TRES fixturas nomeadas e UMA suposicao ja declarada fechada."
  - "Teste de ordem por CONTAGEM DE CHAMADAS, sempre com o controle que o torna nao-vacuo: 'zero chamadas na linha coberta' so vale acompanhado de 'duas chamadas na linha que atravessa'."
  - "Teste de igualdade entre fixturas acompanhado da prova de que elas sao DIFERENTES: as duas linhas vazias dao o mesmo veredito, e os fundos delas tem V maximo 55 contra 68."

requirements-completed: [LEIT-02, LEIT-05, LEIT-01]

coverage:
  - id: D1
    description: "Uma linha da grade de negociacao atravessa janela -> painel -> portao de layout -> fatia -> sonda -> colunas -> catalogo -> estabilizador e sai como `PaginaAceita`, contra fixtura VERSIONADA"
    requirement: LEIT-02
    verification:
      - kind: integration
        ref: "tests/test_mercado_leitura.py::TestOTracerPontaAPonta::test_dois_frames_da_MESMA_pagina_produzem_pagina_aceita"
        status: pass
      - kind: integration
        ref: "tests/test_mercado_leitura.py::TestOTracerPontaAPonta::test_um_frame_sozinho_NUNCA_produz_pagina_aceita"
        status: pass
    human_judgment: false
  - id: D2
    description: "O acordo entre as DUAS escalas e CONSTRUIDO, nao implicado: as duas sao chamadas em toda linha que vira `LinhaLida`, e discordancia de serie derruba a linha"
    requirement: LEIT-01
    verification:
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestOAcordoEntreAsDuasEscalas::test_as_duas_leitoras_sao_CHAMADAS_em_toda_linha_que_vira_LinhaLida"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestOAcordoEntreAsDuasEscalas::test_discordancia_de_serie_derruba_a_linha"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestOAcordoEntreAsDuasEscalas::test_ruido_SEM_digito_e_absorvido_e_a_linha_PASSA"
        status: pass
    human_judgment: false
  - id: D3
    description: "A leitura de numero e tudo-ou-nada e a gramatica e trava: `5,00,000` e `1234` caem, e a celula coberta devolve `None` em vez de numero parcial"
    requirement: LEIT-02
    verification:
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestAGramaticaDoNumero"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestALeituraDeCelula"
        status: pass
    human_judgment: false
  - id: D4
    description: "A sonda de oclusao roda ANTES do OCR e a recusa e por LINHA: zero chamadas de OCR na linha coberta, e as descobertas do mesmo frame caem por outra peneira"
    requirement: LEIT-05
    verification:
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestAOrdemDoPipeline"
        status: pass
      - kind: integration
        ref: "tests/test_mercado_leitura.py::TestARecusaEPorLinhaNuncaPorPagina"
        status: pass
    human_judgment: false
  - id: D5
    description: "A linha vazia e decidida por ausencia de conteudo e marca o fim da pagina; as duas paridades de banda dao o mesmo veredito"
    requirement: LEIT-05
    verification:
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestALinhaVazia"
        status: pass
    human_judgment: false
  - id: D6
    description: "O portao de layout casa negociacao nas duas ordenacoes e recusa Adena e busca; pagina recusada produz zero linha e zero chamada de OCR"
    requirement: LEIT-05
    verification:
      - kind: unit
        ref: "tests/test_mercado_pagina.py::TestOCasamentoDoCabecalho"
        status: pass
      - kind: integration
        ref: "tests/test_mercado_pagina.py::TestAPaginaRecusadaPorLayout"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_pagina.py::TestFeatureOFFQuandoFaltaCalibracao"
        status: pass
    human_judgment: false
  - id: D7
    description: "As primitivas FORAM MOVIDAS e nao copiadas: a ferramenta importa do modulo puro e nenhum modulo de producao carrega `calibrar_mercado`"
    verification:
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestOCharterDoModuloPuro"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_glifos.py (detector de regressao do movimento, 47 testes)"
        status: pass
      - kind: unit
        ref: "tests/test_medir_leitura_de_glifo.py (detector do movimento da gramatica, 35 testes)"
        status: pass
    human_judgment: false
  - id: D8
    description: "O tracer atravessa com OCR de verdade, sobre o jogo aberto, com Windows.Media.Ocr lendo a coluna do nome calibrada"
    verification: []
    human_judgment: true
    rationale: "O pytest roda no Python GLOBAL, que nao tem as bindings WinRT — toda a suite injeta as duas leitoras. A leitura de nome ponta a ponta com o motor real nunca foi observada, e ela e a unica peca do tracer que fixtura nenhuma alcanca. Portao humano de fim de fase (`human_verify_mode: end-of-phase`). Registrado em WINDOWS.md #19."
  - id: D9
    description: "A coluna Quantity le em producao com volume util"
    verification:
      - kind: unit
        ref: "tests/test_mercado_leitura.py::TestALeituraDeCelula::test_le_a_quantidade_da_linha_6_da_fixtura"
        status: pass
    human_judgment: true
    rationale: "MEDIDO E REPROVADO NO VOLUME: o digito `1` da coluna Quantity nao se le (V=177 contra o piso 180), e a maioria das linhas do mercado tem quantidade 1. A leitura funciona para 2..9 e falha FECHADA para 1, entao nada errado e gravado — mas o rendimento em campo e baixo e so um humano decide se isso basta para a Fase 3 comecar. Registrado em WINDOWS.md #17."

duration: 3h 25m
completed: 2026-08-30
status: complete
---

# Phase 02 Plan 04: O tracer da leitura de pagina Summary

**Uma linha da grade de negociacao atravessa janela, painel, portao de layout, fatia, sonda de oclusao, duas colunas de numero, catalogo e estabilizador e sai como `PaginaAceita` — com o acordo entre as duas escalas CONSTRUIDO (as duas sao chamadas em exatamente as linhas que viram dado), nove primitivas MOVIDAS de ferramenta para producao sem duplicar nenhuma, e quatro medicoes que refutaram o plano e ficaram escritas onde nao voltam.**

## Performance

- **Duration:** 3h 25m
- **Started:** 2026-08-30T13:05:00Z
- **Completed:** 2026-08-30T16:30:00Z
- **Tasks:** 3 de 3
- **Files modified:** 18 (2 modulos de producao novos, 2 arquivos de teste novos, 10 fixturas, 4 modificados)

## Accomplishments

- **O TRACER ATRAVESSA.** Sobre `janela_negociacao_f005.png` + o frame vizinho da mesma pagina parada, quatro linhas saem lidas: `(1, 3666, 3)`, `(3, 1500, 3)`, `(5, 1139, 6)`, `(6, 500, 2)`. Um frame sozinho nunca produz pagina.
- **O acordo entre as duas escalas e MECANISMO, nao assinatura de construtor.** O criterio central conta as linhas em que AMBAS as leitoras foram chamadas e exige que seja igual a contagem de `LinhaLida` — sobre `f010`, 2 e 2. Um `ler_linha` que lesse com uma escala so faz esse teste falhar, e nenhum outro criterio o pegaria.
- **Nove primitivas PROMOVIDAS, nenhuma copiada.** `segmentar_glifos`, `mascara_do_sufixo`, `recortar_sufixo`, `_alinhar_por_preenchimento`, `_par_incalculavel`, `MARGEM_DO_RETANGULO_DE_PRECO` de `calibrar_mercado.py`; `centesimos_de_moeda`, `inteiro_de_quantidade` e a mecanica de `pontuar_celula` de `tools/medir_leitura_de_glifo.py`. As duas ferramentas passaram a importar de volta, e os dois arquivos de teste delas (82 testes) sao o detector de regressao do movimento.
- **A ordem do pipeline esta presa por CONTAGEM.** Linha coberta: 0 chamadas de OCR. Linha que atravessa: 2. Linha cujo numero nao se le: 0. Pagina de layout errado: 0 linhas e 0 chamadas.
- **QUATRO medicoes refutaram decisoes travadas** — tres fixturas que o plano nomeou e uma suposicao que o 02-02 declarara fechada. Todas com o numero ao lado, no fonte e no ledger.

## Task Commits

1. **Task 1 RED: o tracer afirmado antes de existir** — `1e78991` (test)
2. **Task 1 GREEN: `mercado_leitura` e `mercado_pagina` nascem, e as primitivas mudam de casa** — `a9294c8` (feat)
3. **Task 2: a sonda de oclusao no lugar certo, e a linha vazia por ausencia** — `3da3125` (test)
4. **Task 3: o portao de layout — negociacao passa, Adena e busca caem** — `b344a49` (test)

## Files Created/Modified

- `l2scanner/mercado_leitura.py` (1.051 linhas) — o transform puro. As primitivas promovidas, `ler_glifos`, `ler_celula`, `ler_celula_de_numero`, `ler_celula_de_quantidade`, `numero_valido`, `linha_ocluida`, `linha_vazia`, `mascara_do_cabecalho`, `casamento_do_cabecalho`, `layout_confere`, `LinhaLida`, `Descarte`, `ler_linha`
- `l2scanner/mercado_pagina.py` (438 linhas) — `LeituraDaPagina`, `PaginaAceita`, `LeitorDePagina`
- `l2scanner/calibrar_mercado.py` — 211 linhas a MENOS; passa a importar as seis primitivas do modulo puro
- `tools/medir_leitura_de_glifo.py` — a gramatica saiu; `pontuar_celula` virou casca fina sobre `pontuar_glifos`
- `tests/test_mercado_leitura.py` (73 testes), `tests/test_mercado_pagina.py` (28 testes)
- 9 fixturas de imagem novas + `calibracao_de_fixture.json` (15,6 MB versionados)

---

# AS QUATRO REFUTACOES

## 1. A linha 0 de `janela_negociacao_f010.png` NAO vira `LinhaLida`

O plano afirmava, no `<behavior>` da Task 1, que ela sairia com nome, total e quantidade. Medido, ela cai — e o mecanismo importa:

```
frame_000010, sonda de oclusao (dx 207..417 a partir de gx):
  linha 0  moda 48  dispersao 0,0000     linha 5  moda 66  dispersao 0,0000
  linha 1  moda 66  dispersao 0,0000     linha 6  moda 48  dispersao 0,0000
  linha 2  moda 48  dispersao 0,0000     linha 7  moda 66  dispersao 0,0000
  linha 3  moda 66  dispersao 0,0000     linha 8  moda 48  dispersao 0,0000
  linha 4  moda 48  dispersao 0,0000     linha 9  moda 66  dispersao 0,0000
```

**A tooltip cobre a coluna Total das linhas 0 a 3 e a sonda nao a ve.** A sonda mede o trecho `dx 207..417` da grade — a metade ESQUERDA, entre o fim dos nomes e o inicio dos numeros —, e esta tooltip esta inteiramente a direita dela. Dispersao 0,0000 nas dez linhas.

Quem pega o buraco e a peneira seguinte: os 23 runs que a coluna coberta produz na linha 0 nao passam no piso 0,4698, a celula cai inteira (tudo-ou-nada de LEIT-02) e a linha vira `Descarte` com motivo `numero`. **A falha fechada funcionou exatamente onde a sonda nao alcanca — e e por isso que ha tres peneiras e nao uma.**

As linhas que atravessam de verdade em `f010` sao a **6** (`18,90` x 2) e a **8** (`18,00` x 3).

Registrado em `WINDOWS.md #18`, e a lacuna da sonda em `#18` complementa o `#15` que o 02-03 abriu para o lado esquerdo.

## 2. `janela_negociacao_f010_repetida.png` nao existe — `f010` nao e pagina parada

O plano pedia "o frame vizinho da mesma pagina parada". Medido, os vizinhos mostram paginas DIFERENTES:

```
frame_000009  lidas [(4, 500, 2)]
frame_000010  lidas [(6, 1890, 2), (8, 1800, 3)]     <- a fixtura do plano
frame_000011  lidas [(8, 900, 2), (9, 2200, 2)]
```

Os pares parados MEDIDOS na gravacao inteira sao `f005`/`f006` (4 linhas lidas, identicas) e `f018`/`f019`/`f020` (1 linha). Foram versionados `janela_negociacao_f005.png` e `janela_negociacao_f005_repetida.png` (o `f006`), e o acordo entre frames e provado com eles — **com dois arquivos de pixels DIFERENTES**, o que um par degenerado (o mesmo array duas vezes) nunca provaria.

## 3. `tooltip/frame_000015` nao serve para provar recusa por linha

O plano nomeava `tooltip/frame_000015` para a fixtura de oclusao. Medido, naquele frame a tooltip cobre TAMBEM o cabecalho, e o portao de layout — que roda ANTES da sonda, por decisao da propria Task 3 — recusa a pagina inteira:

```
frame_000014  cabecalho 0,9196  PASSA   cobertas [0..7]
frame_000015  cabecalho 0,4469  recusa  cobertas [0..7]   <- o frame do plano
```

Com o `f015` nao ha uma linha para recusar por oclusao: a pagina nem chega a ser fatiada. O frame que serve e o **`frame_000012`** (cabecalho 0,9196, 8 linhas cobertas e 2 nao), e ele e literalmente o frame que D-15 descreve — "a tooltip cobriu 8 linhas seguidas num frame medido e as outras 2 seguem sendo lidas".

## 4. A suposicao A7 volta a ficar ABERTA: o digito `1` da coluna Quantity nao se le

O `02-RESEARCH.md` listava A7 ("a coluna Quantity le pelo mesmo pipeline do preco") como **fechada pela Task 2 do 02-02**, contra o gabarito 10/48/5. Ela nao esta fechada, e o contraexemplo esta medido pixel a pixel.

O canal V da regiao do `1` da quantidade, `frame_000010`, linha 1:

```
 66  66  66  66  66  66  66     fundo
 66  66  66  70 135 177  66
 66  66  66 187 215 177  28     <- serifa: 187, 215  |  tronco: 177
 66  66  66  66 123 177  28
 66  66  66  66 123 177  28     <- o TRONCO inteiro a 177
 66  66  66  66 123 177  28
 66  66  66  66 123 177  28
 66  66  66 187 215 215 215     <- base
```

`identidade.mascara_de_texto` usa **V > 180**. O tronco esta a **177** — tres niveis abaixo. A mascara fica so com a serifa e a base:

```
[[1 1 0 0]
 [0 0 0 0]      o `1` da quantidade, depois da mascara
 [0 0 0 0]
 [0 0 0 0]
 [0 0 0 0]
 [0 0 0 0]
 [1 1 1 1]]
```

O casamento com o molde `1` devolve **-0,1810**; o melhor casamento e `0` a **0,2988**, bem abaixo do piso de leitura 0,4698. **A celula cai inteira — falha FECHADA, comportamento certo.**

**Nao e um problema da coluna Total:** ali o mesmo `1` do `100,00` tem tronco a **V = 205** e le sem esforco. E uma diferenca de BRILHO entre colunas, exatamente a mesma classe de problema que `calibrar_mercado.VALOR_MINIMO_DO_SUFIXO = 120` ja resolveu para `XM Coin` e `Adena` (que ficam inteiras abaixo de 180).

**O custo medido e alto.** Varrendo as gravacoes de tooltip e alvo-sobreposto inteiras, com o portao de layout e a sonda ligados: **ZERO linhas atravessam**, porque todas as quantidades daquelas paginas sao `1`. Em `pagina-cheia` atravessam 1 a 4 linhas por frame — sempre as de quantidade 2 ou mais.

**O conserto tem forma conhecida e falta um numero:** um piso de brilho PROPRIO da coluna Quantity, MEDIDO por varredura sobre as 8 gravacoes e gravado no `calibration.json` (chave nova, algo como `mercado_limiar_de_brilho_da_quantidade`). Ele NAO foi inventado aqui: escrever um numero novo sem medi-lo e a constante magica que este projeto recusa, e a medicao e uma onda, nao um `if`. Registrado em `WINDOWS.md #17`.

---

## Decisions Made

Todas na frontmatter `key-decisions`. As tres que mais mudam o codigo de quem vier depois:

**Os numeros vem ANTES do OCR.** Uma celula custa 13 casamentos por run; o OCR custa ~7 ms. Uma linha cujo preco nao se le nao vira dado de jeito nenhum. Alem da economia, e essa ordem que torna o criterio central VERDADEIRO: as linhas em que ambas as leitoras foram chamadas sao exatamente as que viraram `LinhaLida`, e nao um superconjunto delas.

**A 3x manda e a 2x confere, com entrada PROVISORIA.** Resolvidas as duas contra o mesmo catalogo antigo, a primeira aparicao de um item cujas escalas discordem num caractere criaria DUAS series novas de chaves diferentes e a linha morreria — nenhum item novo entraria jamais no catalogo com ruido, e a faixa que D-02 existe para absorver nunca seria exercitada. A mecanica veio de `tools/medir_agrupamento_de_nome.py`, onde ela foi MEDIDA no 02-03.

**A serie so nasce quando a pagina foi aceita.** Um frame sozinho nao cria serie, porque o segundo pode desmentir a leitura e a chave e irreversivel do ponto de vista do CSV.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_ler_o_nome` sem a entrada provisoria degenerava para igualdade de string**
- **Found during:** Task 1 (GREEN)
- **Issue:** Com as duas leituras agrupadas contra o mesmo catalogo antigo, um item NOVO cujas escalas lessem `Chll` e `Doll` produzia duas chaves novas diferentes e a linha caia. O predicado "mesma serie" virava igualdade de string exatamente para a primeira aparicao — que e quando ele mais importa.
- **Fix:** Reproduzida a mecanica de `rendimento_de_uma_rota` do 02-03: a 3x resolve primeiro e, se abrir serie nova, ela entra PROVISORIA na lista contra a qual a 2x e resolvida.
- **Verification:** `test_ruido_SEM_digito_e_absorvido_e_a_linha_PASSA`
- **Committed in:** `a9294c8`

**2. [Rule 2 - Missing Critical] Portao de carga por AUSENCIA em `LeitorDePagina`**
- **Found during:** Task 3
- **Issue:** O plano previa feature OFF so para o cabecalho ausente. Faltando qualquer outra peca (sonda, piso, margem, corte, moldes) o leitor levantaria `TypeError` no meio do tick — e o tick e o mesmo laco que vigia a party.
- **Fix:** `_calibrado()` confere as nove chaves por ausencia, avisa alto uma vez e a leitura nao acontece. Preso por teste parametrizado nas oito chaves.
- **Verification:** `TestFeatureOFFQuandoFaltaCalibracao`
- **Committed in:** `b344a49`

**3. [Rule 2 - Missing Critical] Molde de cabecalho CORROMPIDO tambem e feature OFF**
- **Found during:** Task 3
- **Issue:** `cabecalho_de_calibracao` levanta `ValueError` por design (entrada nao confiavel). Sem tratamento, um `bytes` corrompido derrubaria o scanner no arranque — e a docstring dela avisa que o preco do erro aqui e recusar TODA pagina, para sempre, sem dizer por que.
- **Fix:** Decodificacao UMA VEZ no `__init__`, dentro de `try`, com aviso alto e feature OFF.
- **Verification:** `test_um_molde_de_cabecalho_CORROMPIDO_tambem_e_feature_OFF`
- **Committed in:** `b344a49`

**4. [Rule 3 - Blocking] `linha_ocluida` sem sonda utilizavel recusa em vez de aceitar**
- **Found during:** Task 2
- **Issue:** `nivel_de_fundo_da_linha` devolve `None` para geometria impossivel, e a docstring dela e explicita: "nao da para medir" NAO e "esta limpa". Sem tratamento, `None` seria falsy e a linha passaria.
- **Fix:** `None`, sonda ausente ou sonda sem `dx0`/`dx1`/`folga` devolvem `True` (recusa).
- **Verification:** `test_sem_sonda_calibrada_a_resposta_e_RECUSA`, `test_sonda_impossivel_de_medir_e_RECUSA`
- **Committed in:** `a9294c8`

### Divergencias deliberadas da letra do plano

**5. `linha_vazia(bgr)` em vez de `linha_vazia(bgr, moldes)`** — nenhum molde participa da decisao (a pergunta e "ha pixel de conteudo", nao "ha glifo conhecido"), e um parametro nao usado e uma promessa nao cumprida.

**6. `layout_confere` recebe `dx_da_grade` e o `molde` ja decodificado** — o plano dava 4 parametros; o `dx` nao esta no dict do cabecalho por decisao explicita do calibrador, e decodificar 28 KB de hex a cada tick seria trabalho puro.

**7. `ler_celula_de_quantidade` nasceu ao lado de `ler_celula_de_numero`** — a coluna Quantity nao tem casa decimal, e ler as duas pela mesma funcao dividiria a quantidade por cem, calado.

**8. As tres fixturas trocadas** — documentadas em "AS QUATRO REFUTACOES" 1, 2 e 3.

---

**Total deviations:** 4 auto-fixed (1 bug, 2 missing critical, 1 blocking) + 4 divergencias deliberadas documentadas
**Impact on plan:** Nenhuma amplia escopo. As quatro correcoes fecham caminhos em que o scanner levantaria dentro do tick ou aceitaria pixel adulterado. As quatro divergencias sao consequencia de medicao ou de a assinatura do plano nao caber na geometria real.

## Issues Encountered

- **O rendimento em campo e baixo por causa do `1` da coluna Quantity** (refutacao 4). Nao e defeito de codigo: a falha e fechada e nada errado e gravado. Mas a Fase 3 vai gravar menos linhas do que o usuario ve na tela, e ele precisa saber disso antes de olhar o CSV.
- **A guarda de cruzamento continua REPROVADA** (`mercado_tolerancia_do_cruzamento = None`, do 02-02). O par `0`x`8`, margem 0,0370, segue sem segunda opiniao independente. A gramatica NAO alcanca substituicao — esta escrito na docstring de `numero_valido`, para ninguem confundir o alcance dela.

## User Setup Required

None — nenhuma configuracao de servico externo.

## Next Phase Readiness

**Pronto para o 02-05:** `LeitorDePagina.observar` tem o acordo minimo entre dois frames e o gancho para o congelamento e o `mercado_minimo_de_linhas_comparadas = 7`; `LeituraDaPagina` ja separa lida / descartada / vazia, que e o que a contagem do console precisa. O catalogo e um `dict` injetado — trocar por arquivo e trocar o objeto, nao o codigo.

**Pronto para o 02-06:** `ler_linha` sai daqui lendo DUAS colunas de numero. A terceira (`mercado_coluna_do_unitario`, ja calibrada desde o 02-01) e a guarda de cruzamento entram la, e `LinhaLida` recebe `residuo_do_cruzamento`. `mercado_pagina.py` NAO menciona `mercado_coluna_do_unitario` em lugar nenhum — preso por teste, para a coluna nao ser lida antes de ter consumidor.

**Bloqueios e preocupacoes:**
1. **O piso de brilho da coluna Quantity precisa ser MEDIDO** antes de a Fase 3 valer a pena em volume. E uma varredura como as do 02-02/02-03, com portao humano no fim.
2. **O tracer nunca rodou com OCR de verdade** — o Python global nao tem WinRT. Portao humano de fim de fase (`WINDOWS.md #19`).
3. **A sonda de oclusao tem dois pontos cegos medidos** — o inicio do nome (`#15`) e a metade direita da grade (`#18`). A guarda de cruzamento do 02-06 e o que mais se aproxima de fechar os dois.

---
*Phase: 02-leitura-de-p-gina*
*Completed: 2026-08-30*

## Self-Check: PASSED

- 14 arquivos declarados em `key-files.created` conferidos com `[ -f ]`: todos presentes
- 4 hashes de commit conferidos com `git log --oneline --all`: todos presentes
- `tests/test_mercado_leitura.py` + `tests/test_mercado_pagina.py` + `tests/test_mercado_glifos.py` + `tests/test_calibrar_mercado.py`: **287 passed**
- `tests/test_mercado_27x.py`: **22 passed** (o detector de morte segue intocado)
- `tests/test_firewall_escopo.py`: **18 passed** (nenhuma dependencia nova entrou)
- Suite: **2023 passed, 2 skipped** (baseline antes desta onda: 1922) + **132 passed** em `tests/test_agenda.py`
- `calibration.json` NAO commitado (gitignored, conferido com `git log --name-only`)
- `l2scanner/rastreador.py` e `l2scanner/visao.py` NAO tocados (conferido com `git diff --name-only`)
