---
phase: 02-leitura-de-p-gina
plan: 02
subsystem: config
tags: [calibracao, opencv, numpy, oclusao, template-matching, medicao, json]

requires:
  - phase: 02-leitura-de-p-gina
    provides: "as 14 chaves opcionais do calibration.json, as quatro colunas calibradas e as fixtures de negociacao do 02-01"
  - phase: 01-funda-o-firewall-gravador-e-spike-de-campo
    provides: "as 8 gravacoes de campo, os 13 moldes de glifo, as 3 ancoras e o gabarito do SPIKE-RESPOSTAS"
provides:
  - "`mercado_geometria.nivel_de_fundo_da_linha` — a sonda de fundo como primitiva PURA, sem limiar dentro"
  - "`tools/medir_oclusao.py` — varredura que PROPOE e grava a sonda, o limiar de dispersao e o piso de linhas comparadas"
  - "`tools/medir_leitura_de_glifo.py` — varredura que PROPOE e grava o piso e a margem de LEITURA, e produz o veredito DECIDIVEL da guarda de cruzamento"
  - "6 chaves preenchidas no calibration.json da maquina do usuario, todas MEDIDAS"
  - "o veredito da guarda de cruzamento: REPROVADA por tolerancia, com o numero — input de plano para o 02-04 Task 4"
  - "7 fixtures versionadas novas em tests/fixtures/mercado/"
affects: [02-04, 02-05, 02-06, leitura de pagina, estabilizador, guarda de cruzamento]

actuals:
  tokens: 27491
  tasks: 2
  commits: 5

tech-stack:
  added: []
  patterns:
    - "gabarito de campo NOMEADO (frame + linha) como unico rotulo nao circular para medir limiar de oclusao"
    - "escolha de trecho por MAIOR FOLGA RELATIVA contra o gabarito, com descarte do candidato cuja folga so se expressa como infinita"
    - "populacao de par classificada pela MEDIDA (frames inteiros / maioria recusada), nunca pela pasta de origem"
    - "guarda julgada sobre a populacao que ela VE em producao (pos piso e margem), com a populacao crua reportada ao lado"
    - "load-mutate-save por NamedTemporaryFile + os.replace nas duas ferramentas que escrevem no calibration.json"

key-files:
  created:
    - tools/medir_oclusao.py
    - tools/medir_leitura_de_glifo.py
    - tests/test_mercado_geometria.py
    - tests/test_medir_leitura_de_glifo.py
    - tests/fixtures/mercado/linha_limpa_par_f010.png
    - tests/fixtures/mercado/linha_limpa_impar_f010.png
    - tests/fixtures/mercado/linha_sob_tooltip_f015.png
    - tests/fixtures/mercado/linha_limpa_no_frame_do_tooltip_f015.png
    - tests/fixtures/mercado/linha_sob_alvo_f024.png
    - tests/fixtures/mercado/linha_limpa_no_frame_do_alvo_f024.png
    - tests/fixtures/mercado/glifos_quantidade_f012.png
  modified:
    - l2scanner/mercado_geometria.py

key-decisions:
  - "Rotular linha limpa/coberta pela PASTA de origem foi REFUTADO por medicao: as seis gravacoes 'sem oclusao deliberada' contem tooltip, e com esse rotulo as populacoes se sobrepoem nos 214 trechos candidatos varridos. O rotulo passou a ser o GABARITO DE CAMPO nomeado frame a frame."
  - "Escolher o trecho por 'menor dispersao mediana' tambem foi REFUTADO: o trecho de mediana zero rejeita 22,4% de todas as linhas de campo. A escolha passou a ser a MAIOR FOLGA RELATIVA contra o gabarito, e um candidato cuja pior limpa e exatamente 0 e DESCARTADO porque a razao contra zero nao e medicao."
  - "O vao literal entre a coluna do nome e a Quantity tem largura ZERO nesta calibracao (elas sao adjacentes por construcao desde o 02-01). A janela de busca virou a UNIAO das duas colunas, com a divergencia impressa no relatorio."
  - "`mercado_tolerancia_do_cruzamento` ficou `None`: a guarda REPROVOU por tolerancia (1273 centesimos por unidade contra o maximo 1,0). Falha fechada vale para a guarda tambem — uma guarda que nao se provou nao pode descartar dado."
  - "O piso de LEITURA medido (0,4698) e a margem (0,0370) sao numeros PROPRIOS: o limiar de colisao 0,8555 rejeitaria 39,4% dos 55.342 glifos reais medidos, e a margem 0,12 herdada rejeitaria 26,7%."

patterns-established:
  - "Gabarito de campo como constante da ferramenta: o rotulo vem de observacao humana registrada na pesquisa, nao do limiar que se quer justificar."
  - "Relatorio que imprime TODOS os candidatos com o veredito de cada um, para que a escolha possa ser conferida em vez de acreditada."
  - "Conjunto de medicao FECHADO por constante, com as pastas ignoradas nomeadas com o motivo e parada dura quando uma esperada falta."

requirements-completed: [LEIT-02]

coverage:
  - id: D1
    description: "A sonda de fundo existe como primitiva PURA em mercado_geometria.py, mede DISPERSAO (nunca a moda), e devolve None em vez de levantar quando a geometria nao da"
    requirement: LEIT-02
    verification:
      - kind: unit
        ref: "tests/test_mercado_geometria.py::TestALinhaLimpa"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_geometria.py::TestALinhaCOBERTA"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_geometria.py::TestOQueNaoDaPARA_MEDIR"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_geometria.py::TestOCharterDoModulo::test_nenhum_limiar_de_oclusao_no_fonte"
        status: pass
    human_judgment: false
  - id: D2
    description: "A sonda, o limiar de dispersao e o piso de linhas comparadas foram MEDIDOS por varredura sobre as 8 gravacoes nomeadas e gravados no calibration.json"
    requirement: LEIT-02
    verification:
      - kind: manual_procedural
        ref: ".venv/Scripts/python.exe tools/medir_oclusao.py --gravacoes <abs>/recordings --calibracao <abs>/calibration.json (exit 0)"
        status: pass
      - kind: unit
        ref: "tests/test_mercado_geometria.py::TestNoTrechoQueAVarreduraESCOLHEU"
        status: pass
    human_judgment: false
  - id: D3
    description: "A varredura PARA com codigo != 0 quando uma pasta esperada do censo falta, e imprime as pastas ignoradas com o motivo de cada uma"
    verification:
      - kind: manual_procedural
        ref: "tools/medir_oclusao.py --gravacoes <pasta com 1 das 8> (exit 3, 7 pastas nomeadas)"
        status: pass
    human_judgment: false
  - id: D4
    description: "O piso e a margem de LEITURA sao numeros proprios, medidos sobre glifos reais das colunas calibradas, e o limiar de COLISAO 0,8555 nao serve de piso"
    requirement: LEIT-02
    verification:
      - kind: unit
        ref: "tests/test_medir_leitura_de_glifo.py::TestOLimiarDeCOLISAONaoServeDePiso"
        status: pass
      - kind: unit
        ref: "tests/test_medir_leitura_de_glifo.py::TestALeituraDosSeisPrecos"
        status: pass
      - kind: unit
        ref: "tests/test_medir_leitura_de_glifo.py::TestTudoOuNada"
        status: pass
      - kind: manual_procedural
        ref: ".venv/Scripts/python.exe tools/medir_leitura_de_glifo.py --gravacoes <abs>/recordings --calibracao <abs>/calibration.json (exit 0)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A coluna Quantity deixou de ser deducao: 3.705 celulas medidas e o gabarito 10/48/5 batendo 3 de 3"
    verification:
      - kind: unit
        ref: "tests/test_medir_leitura_de_glifo.py::TestALeituraDosSeisPrecos::test_le_as_tres_quantidades"
        status: pass
      - kind: manual_procedural
        ref: "RELATORIO 2 de tools/medir_leitura_de_glifo.py — 3 de 3 contra o gabarito da secao 4 do SPIKE-RESPOSTAS"
        status: pass
    human_judgment: false
  - id: D6
    description: "A guarda de cruzamento tem veredito DECIDIVEL, gravado, com os dois criterios medidos e a tolerancia em None quando reprova"
    verification:
      - kind: unit
        ref: "tests/test_medir_leitura_de_glifo.py::TestOVereditoDaGuarda"
        status: pass
      - kind: unit
        ref: "tests/test_medir_leitura_de_glifo.py::TestOLimiteDerivadoDoCruzamento"
        status: pass
      - kind: manual_procedural
        ref: "RELATORIO 3 — GUARDA REPROVADA por tolerancia, 1273.0000 centesimos por unidade (maximo 1.0)"
        status: pass
    human_judgment: false
  - id: D7
    description: "O veredito REPROVADO da guarda e a decisao certa para o produto, e nao um sintoma de medicao mal feita"
    verification: []
    human_judgment: true
    rationale: "O fechamento no limite derivado ficou em 0,6525 mesmo depois de filtrar pelo piso e pela margem, e mesmo na gravacao mais limpa (pagina-cheia) ele para em 84,2%. Parte da explicacao e estrutural e esta escrita no relatorio (o portao de LAYOUT so nasce no 02-04 Task 3, entao a varredura mede sobre frames da aba Adena, onde a terceira coluna e `5 mln increment` e a relacao nao vale por construcao). Se a guarda deve ser REMEDIDA depois do portao de layout, ou abandonada, e uma decisao de escopo que o usuario tem de tomar — a ferramenta entrega o numero, nao a decisao."

duration: 1h 25m
completed: 2026-08-30
status: complete
---

# Phase 02 Plan 02: A sonda de oclusao e o piso de leitura, MEDIDOS Summary

**Seis numeros produzidos por varredura sobre 478 frames de campo e 55.342 glifos reais — e duas refutacoes medidas que derrubaram o desenho original de rotulagem, mais um veredito de guarda REPROVADO com o numero por escrito**

## Performance

- **Duration:** 1h 25m
- **Started:** 2026-08-30T11:20Z (aproximado — primeira leitura do plano)
- **Completed:** 2026-08-30T12:45Z
- **Tasks:** 2 (as duas `auto` com `tdd="true"`)
- **Files modified:** 12 (1 de producao, 2 ferramentas, 2 de teste, 7 fixtures)

## Accomplishments

- **A sonda de fundo virou primitiva pura, e o limiar NAO mora nela.** `nivel_de_fundo_da_linha(cinza, retangulo, folga)` devolve `(moda, dispersao)` ou `None`. A docstring carrega a refutacao medida que decide o desenho: em `tooltip/frame_000015` as linhas 2, 4 e 6 continuam com moda 48 mesmo cobertas, entao testar a moda aprovaria tres linhas cobertas — so a dispersao separa, e ela e auto-referente.
- **Os tres numeros da oclusao foram medidos sobre 478 frames com painel aberto das 8 gravacoes NOMEADAS**, com as outras 8 pastas ignoradas e o motivo de cada uma impresso. A ferramenta para com codigo 3 se uma pasta esperada falta.
- **Os dois numeros da leitura foram medidos sobre 55.342 runs de glifo** em 4.374 linhas de grade, com a MESMA mecanica de `propor_rotulo` — nenhuma reescrita.
- **A margem medida confirma a pesquisa de forma independente:** 0,036984 contra os 0,0370 que a pesquisa mediu para o par `0`x`8`, o mais estreito do sistema. Duas medicoes separadas, mesmo numero.
- **A coluna Quantity deixou de ser deducao** (A7 da pesquisa era deducao, nao medicao): 3.705 celulas lidas, e o gabarito 10/48/5 da secao 4 do `SPIKE-RESPOSTAS.md` bate 3 de 3.
- **A guarda de cruzamento tem veredito decidivel, e ele REPROVOU** — com a tolerancia gravada como `None` e a razao com numero. Falha fechada.

## Os numeros MEDIDOS

### Task 1 — a sonda de oclusao

| chave | valor MEDIDO | como |
|---|---|---|
| `mercado_sonda_do_fundo` | `{dx0: 207, dx1: 417, folga: 2}` | melhor de 16 candidatos de 210 px deslizando na janela derivada `x em [42, 489)` |
| `mercado_limiar_de_dispersao_do_fundo` | **0.026377** | media geometrica entre a pior limpa (0,0095) e a melhor coberta (0,0731) |
| `mercado_minimo_de_linhas_comparadas` | **7** | teto dos pares cobertos 4, p5 dos pares normais 10, folga 3 e 3 |

**A folga do caso apertado, nomeada como o plano pede:** a marcacao de alvo e o caso apertado, e a folga dela e **7,7x** — melhor coberta 0,0731 contra pior limpa 0,0095. Nao ha caso mais apertado no gabarito: a tooltip separa por 34,7x (0,3293 contra 0,0095), entao o 7,7x da marcacao de alvo E a folga que dimensiona o limiar.

**A tabela dos 16 candidatos, do relatorio** (o `->` e o escolhido):

```
  trecho            pior LIMPA  melhor COBERTA     folga  veredito
  [42,252)              0.1311          0.3530     2.69x  apto
  [117,327)             0.0712          0.1240     1.74x  apto
  [177,387)             0.0307          0.1358     4.43x  apto
  [192,402)             0.0197          0.1071     5.42x  apto
->[207,417)             0.0095          0.0731     7.67x  apto
  [222,432)             0.0106          0.0465     4.40x  apto
  [252,462)             0.0113          0.0135     1.20x  apto
  [267,477)             0.0113          0.0037     0.33x  NAO SEPARA
```

**O custo do corte, que a ferramenta imprime porque descarte nao e de graca:** 951 de 4.768 linhas recusadas (19,9%), concentradas onde se espera — tooltip 41,8%, scroll 31,2%, aberto 21,5%, contra 0,0% em `scroll-transicao` e 2,2% em `pagina-cheia`.

**A INTERSECAO entre frames vizinhos, que e a grandeza que o 02-05 julga:**

| populacao | n | min | p5 | mediana | max |
|---|---|---|---|---|---|
| pares normais (os dois frames inteiros) | 269 | 5 | 10 | 10 | 10 |
| pares majoritariamente cobertos | 94 | 0 | 0 | 0 | 4 |
| pares parcialmente cobertos | 107 | 5 | 5 | 8 | 9 |

**Achado registrado:** a diferenca de mediana entre "sobreviventes por frame isolado" e "intersecao entre vizinhos" e **+0,00 linhas**. Isso significa que a oclusao e ESTAVEL entre frames vizinhos — o que a tooltip cobre num frame ela cobre no seguinte. A grandeza certa continua sendo a intersecao (ela e menor ou igual por definicao, e o minimo delas difere: 0 contra 0, mas as caudas nao coincidem), mas o risco de superestimar sistematicamente que motivou a escolha nao se materializou neste material.

### Task 2 — o piso e a margem de LEITURA

| chave | valor MEDIDO |
|---|---|
| `mercado_limiar_de_leitura_de_glifo` | **0.469831** |
| `mercado_margem_de_leitura_de_glifo` | **0.036984** |
| `mercado_tolerancia_do_cruzamento` | **None** (guarda DESLIGADA) |

O par e o maior que ainda aceita os **8.788 glifos das 811 linhas confirmadas pelo cruzamento** — linhas cujas tres colunas leram, respeitam a gramatica do numero, e fecham `total = unitario x quantidade` dentro do limite DERIVADO do arredondamento. Tres leituras independentes que concordam aritmeticamente nao concordam por acaso.

**Por que o 0,8555 nao serve de piso, agora com o nosso numero:**

```
  O LIMIAR DE COLISAO 0.8555 rejeitaria 21785 de 55342 glifos reais (39.4%).
  A MARGEM 0,12 herdada de identidade.py rejeitaria 14772 de 55342 (26.7%).
```

A pesquisa mediu 18,0% sobre 2.057 glifos; medimos 39,4% sobre 55.342. A diferenca de proporcao vem da populacao (a nossa inclui celula coberta e celula de outro layout), mas a conclusao e a mesma e mais forte.

**A distribuicao, e o pior por rotulo** (extrato do relatorio):

```
  score  n= 55342  min=-0.1292  p1=-0.0633  p5=-0.0299  mediana=0.9258  max=1.0000
  margem n= 55342  min=0.0000   p1=0.0000   p5=0.0088   mediana=0.2890  max=0.9337

    '8'  n=  4097  pior score -0.0454  mediana do score 0.7242
    '0'  n= 14224  pior score -0.0493  mediana do score 0.9258
    '4'  n=  5170  pior score -0.1292  mediana do score 0.4698
    '6'  n=  2440  pior score -0.0146  mediana do score 0.4679
```

A mediana 0,7242 do `8` reproduz EXATAMENTE a medicao da pesquisa. O `4` e o `6` tem mediana perto de 0,47 e sao quem dimensiona o piso.

**A coluna Quantity (Relatorio 2):** 3.705 celulas lidas; a esmagadora maioria com 1 ou 2 runs (2.332 e 809 celulas); 264 leituras com virgula, todas de celula coberta ou de outro layout (os exemplos impressos sao lixo do tipo `,,,,,9,,,,,63,,,,`, nao numero com separador de milhar). Contra o gabarito da secao 4 do `SPIKE-RESPOSTAS.md`, **3 de 3**: linha 5 `10`, linha 6 `48`, linha 7 `5`. O carimbo de quantidade desenhado sobre o ICONE fica fora do retangulo calibrado, porque a coluna Quantity comeca depois da coluna do nome e o icone fica antes dela.

### O VEREDITO DA GUARDA, na linha que o 02-06 le literalmente

```
GUARDA REPROVADA por tolerancia, 1273.0000 centesimos por unidade (maximo 1.0)
```

Os dois criterios, medidos:

| criterio | exigido | medido |
|---|---|---|
| fechamento | >= 0,99 | 0,9992 — **mas so com tolerancia 1273** |
| tolerancia | <= 1,0 centesimo por unidade (2x o limite derivado) | **1273,0** — CAIU |
| deteccao | >= 0,90 | **0,0164** sobre 1.893 substituicoes `0`<->`8` injetadas — tambem cairia |

O fechamento no LIMITE DERIVADO (0,5 por unidade, o que a aritmetica do arredondamento permite) e de apenas **0,6525**. Para chegar a 0,99 a tolerancia precisaria de 1273 centesimos por unidade — 2.546 vezes o limite derivado. Com uma peneira dessas a guarda aprovaria tambem a substituicao que ela existe para pegar, e a deteccao de 0,0164 confirma isso diretamente.

**`mercado_tolerancia_do_cruzamento` foi gravado como `None`.** A guarda fica DESLIGADA. Falha fechada vale para a guarda tambem: uma guarda que nao se provou nao pode descartar dado, porque ai ela e o defeito.

**A explicacao estrutural, que o relatorio imprime junto** — o fechamento por gravacao:

```
    053105-mercado-aberto                551 de   917  ( 60.1%)
    055323-mercado-scroll                108 de   138  ( 78.3%)
    060622-mercado-pagina-cheia           32 de    38  ( 84.2%)
    063409-mercado-scroll-transicao      120 de   150  ( 80.0%)
```

O portao de LAYOUT so nasce no **02-04 Task 3**, entao esta varredura mede necessariamente sobre frames de todos os layouts. Na aba Adena a terceira coluna e `5 mln increment`, normalizada por 5 milhoes de adena e **nao** por unidade — ali a relacao nao vale por construcao, nao por erro de leitura. Isso explica parte da queda, mas **nao toda**: mesmo `pagina-cheia`, que e negociacao pura, para em 84,2%. O veredito e robusto.

## Task Commits

1. **Task 1 (RED): a sonda de fundo, afirmada antes de existir** — `80d0527` (test)
2. **Task 1 (GREEN): a sonda mede DISPERSAO, e o limiar nao mora nela** — `011b12c` (feat)
3. **Task 1 (ferramenta): a sonda, o limiar e o piso, MEDIDOS por varredura** — `cf9af32` (feat)
4. **Task 2 (RED): o piso de LEITURA e a guarda, afirmados antes de existirem** — `ddde84c` (test)
5. **Task 2 (GREEN): o piso, a margem e o veredito da guarda** — `86e8dcd` (feat)

O `calibration.json` **nao tem commit e nunca podera ter**: ele e gitignored e carrega os 13 moldes de glifo do usuario. Conferido antes e depois de cada uma das duas escritas — md5 dos 13 moldes `f3fc93a0b961292d0e0bc562d02b43e9` e das 3 ancoras `e1247779081b7d412783741761c8513a`, IDENTICOS nas duas pontas.

## Files Created/Modified

- `l2scanner/mercado_geometria.py` — `nivel_de_fundo_da_linha`, com a refutacao da moda escrita na docstring
- `tools/medir_oclusao.py` — a varredura da oclusao; `GRAVACOES_DO_CENSO`, `MOTIVO_PARA_IGNORAR`, `GABARITO_COBERTAS`/`GABARITO_LIMPAS`, `janela_de_busca`, `candidatos_de_sonda`, `varrer`, `escolher_o_trecho_sem_texto`, `separar_as_populacoes`, `propor_o_limiar`, `descarte_por_gravacao`, `distribuicao_de_linhas_sobreviventes`, `intersecao_entre_frames_vizinhos`, `pares_vizinhos_detalhados`, `propor_o_minimo_comparado`, `gravar`, `main`
- `tools/medir_leitura_de_glifo.py` — a varredura da leitura; `centesimos_de_moeda`, `inteiro_de_quantidade`, `pontuar_celula`, `classificar_celula`, `limite_derivado_do_cruzamento`, `residuo_do_cruzamento`, `medir_o_cruzamento_do_unitario`, `poder_de_deteccao_do_cruzamento`, `veredito_da_guarda`, `varrer`, `linhas_do_cruzamento`, `propor_piso_e_margem`, `gravar`, `main`
- `tests/test_mercado_geometria.py` — 18 testes; relacao e faixa, nunca valor exato preso
- `tests/test_medir_leitura_de_glifo.py` — 35 testes; leitura digito a digito, tudo-ou-nada, gramatica, limite derivado, os dois modos de reprovacao da guarda, e T-02-08 por inspecao de fonte nas DUAS ferramentas
- 7 fixtures novas em `tests/fixtures/mercado/` — 6 linhas de grade inteiras (944x45) e a coluna Quantity de `frame_000012`

## Decisions Made

Ver `key-decisions` no frontmatter. As duas que mais importam para quem vier depois:

1. **O rotulo de "linha coberta" nao pode vir da pasta.** Ele vem do gabarito de campo nomeado frame a frame, porque as gravacoes "limpas" contem tooltip — a propria pesquisa nomeia `scroll/frame_000084` como um frame com tooltip.
2. **A guarda de cruzamento esta DESLIGADA, e isso e um resultado, nao um silencio.** O 02-04 Task 4 le a linha `GUARDA REPROVADA por tolerancia, 1273.0000 centesimos por unidade (maximo 1.0)` e registra a refutacao em vez de ligar o mecanismo.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Rotular linha limpa/coberta pela PASTA de origem nao separa as populacoes**
- **Found during:** Task 1, na primeira rodada da varredura
- **Issue:** O plano trata "gravacao limpa" e "gravacao com oclusao" como as duas populacoes. Medido: as seis gravacoes sem oclusao deliberada CONTEM tooltip — a propria pesquisa nomeia `scroll/frame_000084`. Com esse rotulo, a pior linha "limpa" le 0,58–0,72 em **todos os 214 trechos candidatos varridos**, contra 0,30–0,47 da menor coberta conhecida: as populacoes se sobrepoem em todo lugar, e a sobreposicao e do ROTULO, nao do trecho. A ferramenta saia com codigo 6 sem propor nada.
- **Fix:** As populacoes passaram a vir de um `GABARITO_COBERTAS`/`GABARITO_LIMPAS` nomeado frame a frame e linha a linha, tirado da pergunta 4 do `02-RESEARCH.md` e dos frames de referencia do `02-CONTEXT.md`. O gabarito LIMPO inclui de proposito `scroll-transicao/frame_000016` e `frame_000017`, onde estao os nomes longos — sem eles a escolha do trecho seria enganada por um recorte que so parece vazio.
- **Files modified:** tools/medir_oclusao.py
- **Verification:** a varredura passou a sair com codigo 0, e 50 dos 214 trechos diagnosticados respeitam o gabarito
- **Committed in:** `cf9af32`

**2. [Rule 1 - Bug] Escolher o trecho por "menor dispersao mediana" escolhe um trecho que rejeita 22,4% do campo**
- **Found during:** Task 1
- **Issue:** O plano manda escolher o trecho que "minimiza a dispersao mediana em todas as linhas de todos os frames limpos". Medido: tres trechos dao mediana e pior-limpa exatamente 0,0000 sobre as seis paginas do gabarito, o que faz a folga virar uma divisao por zero; o corte cai em 0,0002 e passa a **rejeitar 22,4% de TODAS as linhas de campo**. As seis paginas do gabarito nao exercitaram aquele recorte, e o resto do material exercitou.
- **Fix:** A escolha passou a ser a MAIOR FOLGA RELATIVA contra o gabarito (que e o mesmo criterio que o plano ja usa para o limiar, aplicado tambem ao trecho), e um candidato cuja pior limpa e exatamente 0 e DESCARTADO com o veredito impresso: "a razao contra zero nao e medicao". A tabela com os 16 candidatos e o veredito de cada um entra no relatorio para que a escolha seja conferivel.
- **Files modified:** tools/medir_oclusao.py
- **Verification:** trecho escolhido `[207,417)` com folga 7,67x e 19,9% de descarte, contra 22,4% do trecho degenerado
- **Committed in:** `cf9af32`

**3. [Rule 1 - Bug] O vao entre a coluna do nome e a Quantity tem largura ZERO**
- **Found during:** Task 1
- **Issue:** O plano deriva a janela de busca do "vao entre o fim da coluna do nome e o comeco da coluna Quantity". Nesta calibracao esse vao tem largura **0**: o 02-01 definiu a coluna do nome como terminando exatamente no rotulo `Quantity` do cabecalho, entao as duas sao adjacentes por construcao.
- **Fix:** A janela virou a UNIAO das duas colunas (`x em [42, 489)` relativo a esquerda da grade), com a divergencia impressa no relatorio em vez de sumir. O icone fica de fora de proposito: e arte texturada e opaca, e uma sonda pousada nele mediria o icone.
- **Files modified:** tools/medir_oclusao.py
- **Verification:** a linha `DIVERGENCIA: ... tem largura 0` sai no relatorio de toda rodada
- **Committed in:** `cf9af32`

**4. [Rule 1 - Bug] Classificar par vizinho "normal" pela pasta zerava o p5 e impedia qualquer piso**
- **Found during:** Task 1
- **Issue:** Com "par normal = par de gravacao sem oclusao deliberada", o `mercado-aberto` sozinho traz pares de intersecao ZERO (paginas totalmente cobertas), o p5 dos normais caia para 0,0 e nao havia inteiro possivel entre o teto coberto e o p5. A ferramenta saia com codigo 7.
- **Fix:** As populacoes de par passaram a ser definidas pela MEDIDA: **normal** = os dois frames com todas as linhas medidas aceitas; **coberto** = pelo menos um dos dois com mais da metade recusada; e os parciais sao contados e reportados sem definir limite.
- **Files modified:** tools/medir_oclusao.py
- **Verification:** piso 7 proposto, com p5 normais 10 (n=269) e teto coberto 4 (n=94)
- **Committed in:** `cf9af32`

**5. [Rule 2 - Missing Critical] A guarda era julgada sobre uma populacao que ela nunca vai ver**
- **Found during:** Task 2
- **Issue:** Em producao a guarda so recebe linha que ja passou pelo piso e pela margem de leitura. Julga-la sobre a populacao crua mede a LEITURA, nao a guarda — a populacao crua traz linha coberta que virou numero plausivel, que e exatamente o que o piso existe para tirar do caminho antes.
- **Fix:** `linhas_do_cruzamento` ganhou o filtro opcional por `(piso, margem)`, com o mesmo tudo-ou-nada de `classificar_celula`, e o veredito passou a ser julgado sobre a populacao filtrada. A populacao CRUA continua sendo reportada ao lado, para conferencia.
- **Files modified:** tools/medir_leitura_de_glifo.py
- **Verification:** filtrada 1.243 de 1.278 linhas; o veredito e o MESMO nas duas populacoes (reprovada por tolerancia, 1273 contra 4555), o que torna o resultado robusto em vez de artefato do filtro
- **Committed in:** `86e8dcd`

**6. [Rule 3 - Blocking] `tests/test_mercado_geometria.py` nao existia**
- **Found during:** Task 1
- **Issue:** O plano lista o arquivo em `files_modified` e diz "testes novos em `tests/test_mercado_geometria.py`". O arquivo nao existe no repositorio — os testes de `mercado_geometria` moram espalhados em `test_calibracao_mercado.py`, `test_calibrar_mercado.py` e `test_sugestao_de_calibracao.py`.
- **Fix:** Criado, com o cabecalho declarando de onde veio cada uma das seis fixtures, no padrao de `test_mercado_glifos.py:1-16`.
- **Files modified:** tests/test_mercado_geometria.py
- **Verification:** 18 passed
- **Committed in:** `80d0527`

**7. [Rule 3 - Blocking] Os testes nao podem ler os 13 moldes do `calibration.json`**
- **Found during:** Task 2
- **Issue:** A `<behavior>` do plano diz "com os 13 moldes do calibration.json". Aquele arquivo e gitignored e nao vem de clone limpo — um teste que dependesse dele ficaria verde nesta maquina e amarelo em toda outra, que e o defeito que o proprio plano proibe.
- **Fix:** Os 11 glifos de um caractere sao recortados das PROPRIAS fixtures pelos rotulos conhecidos, exatamente como `test_mercado_glifos.py` ja faz. Nao e circular: o molde do `8` sai de `18,90` (banda de fundo PAR) e e cobrado contra o `8` de `18,00` (banda IMPAR), que e o par que `calibrar_mercado.py:1364-1375` mediu NAO casar 1,000.
- **Files modified:** tests/test_medir_leitura_de_glifo.py
- **Verification:** pior score sobre as fixtures 0,5948 e pior margem 0,0449, ambos reproduzindo o fenomeno de banda oposta que a producao vai enfrentar
- **Committed in:** `ddde84c`, `86e8dcd`

---

**Total deviations:** 7 auto-fixed (4 Rule 1 - bug, 1 Rule 2 - missing critical, 2 Rule 3 - blocking)
**Impact on plan:** Nenhum aumento de escopo. As quatro do Rule 1 sao refutacoes MEDIDAS do desenho de rotulagem e de escolha do plano, e as tres ficaram registradas no fonte ao lado do que as substituiu, no padrao de `ocr.py:36-39`. A do Rule 2 mudou a populacao sobre a qual a guarda e julgada e o veredito **nao mudou**, o que e a melhor evidencia de que a mudanca foi honesta.

## Issues Encountered

- **A rotulagem por pasta consumiu duas rodadas completas de varredura** antes de a medicao mostrar que o problema era o rotulo e nao o trecho. O diagnostico so fechou depois de varrer 214 trechos candidatos sobre todo o material e ver a sobreposicao em TODOS eles — uma sobreposicao universal e assinatura de rotulo errado, nao de geometria errada.
- **Um erro meu, corrigido:** um script de conserto automatico que eu escrevi para reparar literais de string quebradas danificou `tools/medir_oclusao.py` (ele tratou `"""` de fim de docstring como aspa desbalanceada). O arqualquer ainda nao estava versionado, entao nao havia copia em git; reescrevi o arquivo inteiro. Nenhum arquivo versionado foi afetado, e a suite completa confirma.

## Fora de escopo — registrado e NAO corrigido

- **`calibration.rascunho.json` apareceu na raiz do repositorio as 08:28** desta sessao. Nenhum codigo deste repositorio produz esse nome (`grep -rn "rascunho" l2scanner/ tools/ tests/` so acha uma palavra em prosa numa docstring), e este plano nao o criou. Nao foi tocado nem apagado — a decisao e do usuario.
- **`calibration.ANTES-DA-INSTALACAO.json` e `calibration.RESGATE-13-glifos.json`** continuam na raiz, nao versionados, herdados do incidente da janela quebrada 13 registrado no 02-01. Nao tocados.
- **A janela quebrada 13** (`l2scanner/calibrar.py` apagando a calibracao de mercado) continua fora do escopo deste plano; a quick task `260830-bvo` esta em voo sobre aquele arquivo.

## Verification

Rodado no checkout PRINCIPAL, contra o `calibration.json` REAL:

| criterio | comando | resultado |
|---|---|---|
| `<verify>` Task 1 | `pytest tests/test_mercado_geometria.py -x -q` | **18 passed** |
| `<verify>` Task 2 | `pytest tests/test_medir_leitura_de_glifo.py -x -q` | **35 passed** |
| charter do modulo | o `python -c` de `inspect.getsource` do plano | **`charter ok`** |
| GATE Task 1 | `tools/medir_oclusao.py --gravacoes <abs> --calibracao <abs>` | **exit 0**, 478 frames, 16 candidatos tabelados, 8 pastas ignoradas nomeadas |
| pasta ausente para a ferramenta | `--gravacoes <pasta com 1 das 8>` | **exit 3**, as 7 faltantes nomeadas |
| GATE Task 2 | `tools/medir_leitura_de_glifo.py --gravacoes <abs> --calibracao <abs>` | **exit 0**, 3 relatorios, 55.342 runs |
| `--gravar` e o portao de digest | md5 dos 13 moldes e das 3 ancoras antes/depois das DUAS escritas | **IDENTICOS** (`f3fc93a0...`, `e1247779...`) |
| `Calibracao.carregar` aceita as 6 chaves | leitura direta | **sim** — sonda, 0.026377, 7, 0.469831, 0.036984, `None` |
| `calibration.json` fora do git | `git status --short \| grep -c calibration.json` | **0** |
| bloco 1 do `<verification>` | `pytest test_mercado_geometria test_medir_leitura_de_glifo test_mercado_glifos -q` | **100 passed** |
| FIRE-01 | `pytest tests/test_firewall_escopo.py -q` | **18 passed** — nenhuma dependencia nova |
| suite completa | `python -m pytest -q` | **1934 passed, 2 skipped** |

**Sobre o numero da suite:** o prompt desta execucao deu 1830 como baseline. O baseline REAL desta arvore, medido agora com os meus dois arquivos de teste ignorados, e **1881 passed, 2 skipped** — a diferenca vem do commit `efcde50` (quick `260830-bvo`, do outro agente) que entrou nesta branch as 08:50, antes do meu primeiro commit. Os meus 53 testes (18 + 35) levam 1881 para 1934, exatamente. Nenhuma falha, e nenhum aborto por `KeyboardInterrupt` nesta rodada.

**Os cinco arquivos do outro agente:** `git diff --name-only 80d0527^..HEAD` nao lista nenhum de `l2scanner/config.py`, `l2scanner/calibrar.py`, `config.toml`, `tests/test_mira_da_janela.py`, `tests/test_calibrar_nao_apaga_mercado.py`. `tests/test_mira_da_janela.py` ainda nao existe nesta arvore; `tests/test_calibrar_nao_apaga_mercado.py` passa na suite completa.

## Known Stubs

Nenhum. `mercado_tolerancia_do_cruzamento = None` **nao e stub**: e o resultado medido de um veredito que reprovou, gravado de proposito como feature OFF, com os dois numeros e o criterio que caiu por escrito no SUMMARY e no relatorio da ferramenta. E exatamente o que o plano manda fazer quando a guarda nao se prova.

## Deferred Issues

- **A guarda de cruzamento fica DESLIGADA ate ser remedida.** O fechamento no limite derivado (0,6525) e explicado em parte pela ausencia do portao de LAYOUT, que so nasce no **02-04 Task 3**. Depois que ele existir, vale rodar `tools/medir_leitura_de_glifo.py` de novo sobre frames so de negociacao e ver se o fechamento sobe. Mesmo assim `pagina-cheia` — negociacao pura — para em 84,2%, entao a expectativa e que a guarda continue reprovando; o que muda e o tamanho da explicacao.
- **O piso 0,4698 e baixo, e isso e a medicao, nao um afrouxamento.** Quem carrega a decisao e a MARGEM (0,0370), que e o desenho que a pesquisa ja recomendava (argmax + margem, nunca piso absoluto). O 02-04 precisa saber disso: apertar o piso sem remedir mataria leitura boa em volume.
- **`mercado_corte_de_similaridade` e `mercado_piso_de_similaridade` continuam `None`** — sao do agrupamento de nomes, e nao deste plano.

## User Setup Required

None - nenhuma configuracao de servico externo.

## Next Phase Readiness

**Pronto para o 02-03 e para a onda de leitura.** As seis chaves que o 02-04 e o 02-05 consomem estao preenchidas e carregam pelo portao do 02-01:

- a sonda e o limiar de dispersao, para o 02-04 recusar linha coberta
- o piso e a margem de leitura, para o 02-04 ler digito
- o piso de linhas comparadas, para o 02-05 impedir o acordo trivial
- o veredito da guarda, na linha literal que o 02-04 Task 4 le

**Concerns:**

- A guarda de cruzamento reprovou. O 02-04 Task 4 tem de registrar a refutacao em vez de ligar o mecanismo, e o plano dele ja preve as duas saidas.
- A janela quebrada 13 continua aberta: recalibrar a party de novo antes do conserto custa a calibracao de mercado — e agora custaria tambem os seis numeros medidos aqui.

## Self-Check: PASSED

Arquivos criados, conferidos com `[ -f ]`:
- `tools/medir_oclusao.py` FOUND
- `tools/medir_leitura_de_glifo.py` FOUND
- `tests/test_mercado_geometria.py` FOUND
- `tests/test_medir_leitura_de_glifo.py` FOUND
- as 7 fixtures em `tests/fixtures/mercado/` FOUND

Commits, conferidos com `git log --oneline --all`:
- `80d0527` FOUND
- `011b12c` FOUND
- `cf9af32` FOUND
- `ddde84c` FOUND
- `86e8dcd` FOUND

Criterios de aceitacao das duas tasks: re-rodados nesta sessao, todos PASS (tabela em Verification).

---
*Phase: 02-leitura-de-p-gina*
*Workstream: mercado*
*Completed: 2026-08-30*
