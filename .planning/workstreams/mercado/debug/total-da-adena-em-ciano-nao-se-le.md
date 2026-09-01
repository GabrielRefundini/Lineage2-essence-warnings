---
slug: total-da-adena-em-ciano-nao-se-le
workstream: mercado
created: 2026-09-01
updated: 2026-09-01
status: fixing
severity: alta
hypothesis: >
  CONFIRMADA E CORRIGIDA NO ENUNCIADO. Os 13 moldes foram cortados sobre texto
  BRANCO com piso de brilho ABSOLUTO (V > 180). Nesse brilho as hastes laterais
  antisserrilhadas do `0` caem ABAIXO do piso e somem: o molde `0` gravado e um
  anel PARTIDO de 8 px de tinta. O ciano desenha o MESMO glifo com pico 255, as
  MESMAS hastes sobem para V = 181-199, passam do MESMO piso e SOBREVIVEM: a
  observacao e um anel FECHADO de 16 px. Anel fechado casa com `8` (0,7242)
  melhor que com o `0` partido (0,5976). Nao e largura de run e nao e conversao
  ponderada para cinza.
next_action: >
  DECISAO DO USUARIO. Toda correcao por PISO DE BRILHO esta refutada por medicao
  (conjunto admissivel = 1 ponto, folga zero). A direcao que sobra e cortar um
  segundo conjunto de moldes sobre texto CIANO, e isso exige recalibracao pelo
  usuario — o agente nao pode escrever `calibration.json`.
---

# A coluna Total Price da Adena tem valores em ciano, e eles nao se leem

## Sintoma, em campo, depois da calibracao do usuario

A aba Adena foi calibrada por ele em 2026-09-01 17:26. O bloco aninhado foi
gravado corretamente, **nenhuma chave de topo tocada**, e o portao de layout
passou a ACEITAR (a mensagem `PARADO` sumiu do console).

**E mesmo assim todas as paginas sao perdidas.**

## A verdade de campo, LIDA DO FRAME (nao suposta)

`recordings/20260901-172911-adena-diagnostico/frame_000003.png`, as dez linhas,
conferidas contra o pixel ampliado:

    linha | Total Price | cor    | 5 mln increment | o leitor devolve
        0 |      98,00  | branco |          49,00  | 98,00     ok
        1 |     149,00  | CIANO  |          49,66  | 149,88    ERRO
        2 |      99,99  | branco |          49,99  | 99,99     ok
        3 |     100,00  | CIANO  |          50,00  | 188,88    ERRO
        4 |     100,00  | CIANO  |          50,00  | 100,00    ok
        5 |     100,00  | CIANO  |          50,00  | 188,88    ERRO
        6 |     100,00  | CIANO  |          50,00  | 100,00    ok
        7 |     100,00  | CIANO  |          50,00  | 188,88    ERRO
        8 |     101,00  | CIANO  |          50,50  | 101,00    ok
        9 |     104,00  | CIANO  |          52,00  | 184,88    ERRO

**A coluna do incremento le CERTO nas dez linhas.** So o total erra, trocando
`0` por `8`.

## O MECANISMO, MEDIDO

### 1. O canal V ja e `max(B,G,R)` — normalizar por canal e NO-OP

`mascara_de_numero` faz `cvtColor(bgr, COLOR_BGR2HSV)` e usa o canal V. V e
`max(B,G,R)` por definicao. **Medido: `V == max(B,G,R)` em 450.000 pixels do
bloco da grade, ZERO divergencias.** Nao ha `COLOR_BGR2GRAY` neste caminho, logo
nao ha `0,299*R` para penalizar o vermelho. **A direcao 1 do enunciado esta
morta: ela ja e o que o codigo faz.**

### 2. A largura do run NAO discrimina

    linha  cor     larguras dos runs      leitura
      3    CIANO   [4, 4, 4, 1, 4, 4]     188,88   ERRO
      4    CIANO   [4, 4, 4, 1, 4, 4]     100,00   ok

Larguras IDENTICAS, cores IDENTICAS, leituras OPOSTAS. O `0` sai com 4 px de
run em branco e em ciano. **A hipotese da largura de run esta morta.**

### 3. A causa esta na TINTA DENTRO do run, e ela e um artefato do corte

    o molde '0' gravado        a observacao CIANA        o molde '8' gravado
       .##.   (8 px)              .##.   (16 px)            .##.   (13 px)
       #..#                       #..#                      #..#
       ....   <- hastes           #..#   <- hastes          #..#
       ....      APAGADAS         #..#      PRESENTES       .#..
       ....                       #..#                      #..#
       ....                       #..#                      ....
       #..#                       #..#                      #..#
       .##.                       .##.                      .##.

Os V crus das hastes laterais, no MESMO frame:

    branco (L0, pico 226):  177, 161, 160, 174   -> TODOS abaixo de 180, somem
    ciano  (L3, pico 255):  199, 183, 181, 197   -> TODOS acima de 180, ficam

Scores:

    observacao BRANCA:  0 = 1,0000   8 = 0,7110    -> le `0`
    observacao CIANA:   8 = 0,7242   0 = 0,5976    -> le `8`, margem 0,1266

A margem 0,1266 e quase 4x o piso de margem (0,03698): **a falha e ABERTA**, ela
vence com folga no rotulo errado. Nao e um empate que uma peneira pegaria.

**O piso e ABSOLUTO; o brilho do glifo NAO E. A forma que um molde codifica so
se reproduz no brilho em que ele foi cortado.**

## POR QUE NENHUM PISO DE BRILHO RESOLVE — refutado por medicao

### Piso absoluto: intersecao VAZIA

Varrido contra material que TEM o caso dificil (branco e ciano na mesma pagina;
mais o run colado de 11 px de `frame_000105.png` L6, cuja verdade `149,44` esta
documentada em `larguras_com_folga`):

    piso <= 182  ->  `149,44` ok,   zeros cianos 0/5     (o defeito de hoje)
    piso >= 183  ->  zeros cianos 5/5,  `149,44` -> `149,99`   REGRESSAO

Fronteira exata entre 182 e 183. **Nao existe piso absoluto que sirva aos dois.**

### Piso proporcional ao pico: REPROVADO no controle negativo

`piso = max(180, round(180 * pico / 230))` conserta a Adena (55 celulas, todas de
errado para certo) mas **quebra o `149,44` documentado em 13 ocorrencias**
(`149,44` -> `149,99`), porque subir o piso ERODE o `4` ate ele virar `9`.

### Piso normalizado por fundo e pico: o conjunto admissivel e UM PONTO

`piso = max(180, round(fundo + k*(pico - fundo)))`:

    k       f105 (149,44)   f23 L5 (380,00)   adena L3 (100,00)
    0,62      149,44 ok        None    X          100,00 ok
    0,63      149,44 ok        360,00  X          100,00 ok   <- INVENTA
    0,64      149,44 ok        380,00 ok          100,00 ok   <- unico ponto
    0,65      149,49  X        380,00 ok          100,00 ok
    0,66      149,99  X        380,00 ok          100,00 ok

**Folga zero dos dois lados.** `k = 0,63` INVENTA `360,00` onde a tela diz
`380,00` — a falha ABERTA, o pior modo. `k = 0,65` quebra o `149,44`
documentado. Isso nao e um vale: e um fio de navalha ajustado a exatamente as
tres restricoes para as quais existe material.

**A razao e mecanica: um piso e UM escalar, e cada glifo cruza o limiar num
ritmo proprio.** Subir o piso fecha o anel do `0` (conserta) e erode a barra
horizontal do `4` ate ele virar `9` (quebra). Nenhum escalar serve aos dois.

## O QUE A INVESTIGACAO ENCONTROU DE QUEBRA — e e mais grave

**O caminho da NEGOCIACAO tem o MESMO defeito, em campo, e a guarda dele nao
pega.** Medido em 3.240 celulas de negociacao, com a verdade conferida no pixel
ampliado:

    frame_000022.png L7  tela 125,00  ->  le 125,88
    frame_000022.png L9  tela 140,00  ->  le 148,88
    frame_000011.png L5  tela 100,00  ->  le 188,88
    frame_000040.png L1  tela 700,00  ->  le 788,88

Na negociacao `mercado_tolerancia_do_cruzamento` e `None` — o cruzamento so
OBSERVA. E quando `total` e `unitario` erram do MESMO jeito (quantidade 1), o
cruzamento FECHA em cima do erro e nao ha o que anunciar. **Esses valores entram
no CSV.** A Adena esta protegida pela guarda; a negociacao nao esta.

## O que FUNCIONOU, e nao pode ser desfeito

**A guarda de cruzamento rejeitou TODAS as linhas corrompidas da Adena** —
`total=18888` com `incremento=5000` da residuo 1112 contra limite 2,0. O
`.mercado/observacoes.csv` ficou em **93 linhas antes e depois**. Foi o modo de
falha CERTO: nao coletou, em vez de coletar errado.

## Direcao ESCOLHIDA, pelos numeros

**Cortar um segundo conjunto de moldes sobre texto CIANO** — a direcao 2 do
enunciado. Ela nao e escolhida por gosto: e a unica que sobra depois de as tres
familias de piso serem refutadas acima, e o mecanismo diz por que ela e a certa
— so moldes cortados na curva tonal do ciano reproduzem o nivel de erosao de
TODOS os glifos ao mesmo tempo, que e precisamente o que um escalar nao faz.

Ela tambem NAO toca `ler_celula_de_numero` nem a segmentacao, desde que o
conjunto de moldes seja escolhido POR CELULA e as celulas acromaticas fiquem com
o conjunto de hoje — e ai o controle negativo sobre a negociacao passa a ser
ESTRUTURAL em vez de estatistico.

O discriminador entre os dois conjuntos ja esta medido e cai num vale largo:

    branco:  R / max(B,G) = 1,000
    ciano:   R / max(B,G) = 0,544 a 0,557

Um vao de 0,44 — o oposto do fio de navalha do piso.

**O custo: 13 moldes a mao, e o usuario tem de recalibrar.** O agente nao pode
escrever `calibration.json`.

## METADE B — FEITA: o caminho da negociacao FALHA FECHADO

focus: >
  O usuario decidiu "B primeiro, depois A — os dois". Esta sessao executa SO a
  metade B: o leitor passa a RECUSAR a celula de numero cuja TINTA esta fora da
  curva tonal em que os moldes foram cortados. A metade A (segundo conjunto de
  moldes) NAO comeca aqui.
teste: >
  Validar o preditivo de recusa por medicao antes de escrever codigo — o
  candidato do enunciado e `R / max(B,G)`, e ele precisa ser conferido contra
  material que tem AMARELO e VERMELHO, e nao so ciano.
next_action: >
  METADE A. Cortar um segundo conjunto de 13 moldes sobre texto CIANO e fazer
  `tinta_fora_da_curva_dos_moldes` deixar de ser um portao de RECUSA para virar
  o SELETOR do conjunto por celula. O agente NAO pode escrever
  `calibration.json` — a recalibracao e do usuario.

### CORRECOES QUE ESTA SESSAO TRAZ AO ENUNCIADO

1. **`R / max(B,G)` e um detector de CIANO, nao de croma.** Medido: entre as
   3.793 celulas de numero ACROMATICAS por esse criterio, a razao vai de 0,8950
   a **1,8651** e a saturacao chega a **186,96**. Amarelo e vermelho passam
   ilesos por ele (num pixel amarelo `R/max(B,G)` = 1,0). O preditivo tem de ser
   a SATURACAO, que e cega a matiz.

2. **O `149,44` de `glifos_colados_total_f105.png` E CIANO.** Medido:
   `razao = 0,5461`, `saturacao media = 115,55`, `min 110 / max 119`. Ele vem da
   coluna Total de `053105-mercado-aberto/frame_000105.png` L6 — **negociacao,
   nao adena**. A leitura correta dele hoje e SORTE, e nao garantia: os glifos
   `1`, `4`, `9` nao carregam o defeito do anel partido do `0`, mas o proprio
   arquivo ja documenta que subir o piso transforma esse mesmo `149,44` em
   `149,99`. Nenhum molde branco certifica uma celula ciana.

3. **O ciano NAO e da aba Adena.** Ele aparece nas DUAS: 189 celulas de `total`
   e 152 de `unitario` inteiramente cianas em 176 frames de NEGOCIACAO, contra
   88 de `total` na Adena. O caminho que escreve no CSV ja o encontra em campo.

### O QUE FOI FEITO

Um portao de COR, em `l2scanner/mercado_leitura.py`, ANTES de cada leitura de
celula de numero — nas duas leitoras de linha, e em nenhum outro lugar:

    LIMIAR_DE_SATURACAO_DA_TINTA = 29
    saturacao_da_tinta(bgr, valor_minimo)            -> float | None
    tinta_fora_da_curva_dos_moldes(bgr, valor_minimo) -> bool
    MOTIVO_DA_TINTA = "tinta"

Cinco pontos de chamada: `Total`, `Quantity` e `Unit price` em `ler_linha`;
`Total Price` e `5 mln increment` em `ler_linha_de_adena`. O unitario da
negociacao NAO derruba a linha — ele CALA a guarda, exatamente como o unitario
ilegivel ja fazia. Na Adena o incremento DERRUBA, porque sem ele nao ha
quantidade.

`ler_celula`, `ler_celula_de_numero`, `mascara_de_numero` e a segmentacao NAO
foram tocadas. O controle negativo e por isso ESTRUTURAL: celula acromatica
percorre o mesmo caminho de antes, e nao um caminho medido como equivalente.

### O PREDITIVO, PELOS NUMEROS

O candidato do enunciado (`R / max(B,G)`) foi MEDIDO e REJEITADO: ele e um
detector de CIANO, nao de croma. Entre as celulas que ele chama de acromaticas
a razao vai a 1,8651 e a saturacao a 186,96 — amarelo e vermelho passam ilesos.
Medida em campo que confirma: a linha 8 de
`061409-mercado-alvo-sobreposto/frame_000018.png` tem a coluna Quantity sob a
marcacao de alvo, com saturacao mediana 45 — nem branco nem o ciano do
destaque. A razao nao a veria.

O escolhido e a SATURACAO MEDIANA DA TINTA. Varridas 4.248 celulas de numero
(4.028 de negociacao em 176 frames de 9 gravacoes; 220 da Adena em 11 frames),
das quais 3.823 leem hoje:

    tinta ACROMATICA (3.422 celulas):  mediana da saturacao  min 0   max 0
    tinta CROMATICA  (  401 celulas):  113 a 118  (+1 artefato de scroll em 59)

O lado branco e ZERO nas 3.422, sem excecao. **Todo limiar de 0 a 56 produz a
MESMA particao** — um plato de 57 niveis, contra a folga ZERO de todo piso de
brilho ja tentado. 29 e o meio do vao medido [0, 59], e ancorar no 59 (e nao na
populacao ciana propria, em 113) empurra o limiar para o lado da RECUSA.

### O QUE ELE PASSA A RECUSAR, E QUE ACEITAVA

Controle A/B sobre a NEGOCIACAO, o codigo de HEAD contra o de hoje, 1.635
linhas julgadas em 176 frames:

    aceitas pelo codigo ANTES              969
    continuam aceitas, com o MESMO valor   836   (divergentes: 0)
    deixaram de ser aceitas                133   (todas CROMATICAS, todas `tinta`)
    passaram a ser aceitas                   0

Das 133 perdidas, **46 tinham o total terminando em `88`** — a assinatura do
defeito — e 87 nao. As 87 liam CERTO hoje, e caem assim mesmo: a leitura certa
de uma celula ciana e um acidente do antisserrilhamento e nao uma garantia.
Medido nas fixturas versionadas, mesma cor e desfechos opostos:

    janela_negociacao_f010.png L4  saturacao 117  anel PARTIDO -> 100,00 ok
    janela_tooltip_f012.png    L3  saturacao 116  anel FECHADO -> 158,88 ERRO

As quatro leituras erradas conferidas no pixel no ciclo anterior sao TODAS
recusadas agora (4 de 4):

    060622-pagina-cheia/frame_000022 L7  tela 125,00  lia 125,88  sat 116
    060622-pagina-cheia/frame_000022 L9  tela 140,00  lia 148,88  sat 113
    063752-mercado-aberto/frame_000011 L5 tela 100,00 lia 188,88  sat 113
    053105-mercado-aberto/frame_000040 L1 tela 700,00 lia 788,88  sat 116

### O CONTROLE NEGATIVO, POR LEITURA CERTA E NAO POR CONTAGEM

As 836 linhas mantidas trazem valor IDENTICO ao de antes (0 divergencias), e
isso prova AUSENCIA DE MUDANCA — nao correcao. A correcao foi conferida no
PIXEL, desenhando a mascara e lendo os glifos a mao, em 8 celulas espalhadas por
5 gravacoes: `30,00`, `20,00`, `11,42`, `8,00`, `3,00`, `12,00`, `42,00` e
`45,00` — 8 de 8 certas. Mais as 9 celulas brancas e as 5 linhas brancas presas
por VALOR em `tests/test_mercado_ciano.py`.

UMA linha acromatica mudou de veredito, e ela nao e regressao: a linha 8 de
`alvo-sobreposto/frame_000018` ja era DESCARTE (`numero`) e continua DESCARTE
(`tinta`). O que mudou foi o motivo, e para melhor — a coluna Quantity dela esta
sob a marcacao de alvo (saturacao 45), o que e a verdade; "a gramatica reprovou"
era a consequencia.

### A GUARDA DE CRUZAMENTO NAO FOI AFROUXADA

Ela continua identica no codigo. Na Adena ela deixou de ser a PRIMEIRA a pegar a
linha 5 (a tinta pega antes), e por isso a fiacao dela ganhou teste PROPRIO com
material que a alcanca: `Total Price` da linha 8 (`70,00`) contra
`5 mln increment` da linha 1 (`64,99`) — dois recortes REAIS e ACROMATICOS da
mesma fixtura, cujo residuo de 501 centesimos estoura o limite derivado de 0,5.
Ver `TestOCruzamentoEGUARDANaAdena` em `tests/test_mercado_adena.py`.

### A LINHA DO USUARIO — NAO DECIDIDA AQUI

Varrido `.mercado/observacoes.csv` (92 linhas de dado, somente leitura):

    +6 Hunter's Breastplate   total 43,88   quantidade 1   residuo 0
    primeira_vez 2026-08-31T17:05:31.578000

E a UNICA das 92 cujo total termina em `88`, contra 65 que terminam em `00`. Com
quantidade 1 o total e o unitario erram identico, o residuo da 0 e o cruzamento
fecha em cima do erro — a assinatura exata. **O dado e do usuario e a decisao e
dele.** Fica registrado, e nada foi escrito em `.mercado/`.

### O CUSTO, E QUEM O PAGA DE VOLTA

A negociacao perde 133 de 969 linhas (13,7%) e a Adena perde as 3 celulas cianas
por pagina que liam certo. A metade A e quem as devolve, e ela nao comeca aqui.

## Restricoes invioláveis (mantidas)

- **NAO afrouxar a guarda de cruzamento.** Ela e o unico motivo de o dado estar
  limpo agora.
- **NAO mexer no piso de brilho** — agora com medicao, e nao so com receio: o
  conjunto admissivel tem folga zero.
- **NAO tocar** o caminho da negociacao sem controle negativo. O controle vive
  em `tests/test_mercado_ciano.py::TestOCaminhoDaNegociacaoNaoMuda`.
- **NAO escrever** em `.mercado/` nem em `calibration.json`.
- `recordings/` somente-leitura, **nunca glob amplo**.

## Material que discrimina, e ele EXISTE

- `recordings/20260901-172911-adena-diagnostico` (11 frames) — branco E ciano na
  mesma pagina; verdade de campo das 10 linhas na tabela acima.
- `tests/fixtures/mercado/janela_adena_f014.png` — **ja versionado**, tem a
  linha 5 CIANA (tela `135,00`, leitura `135,88`) contra nove linhas brancas. E
  a fixtura do teste vermelho.
- `tests/fixtures/mercado/glifos_colados_total_f105.png` — o `149,44`
  documentado, que e o TETO de qualquer piso.
