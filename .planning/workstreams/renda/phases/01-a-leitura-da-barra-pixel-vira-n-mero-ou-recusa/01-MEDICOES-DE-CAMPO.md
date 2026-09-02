# Medições de campo — 2026-09-02, madrugada, com as DUAS instâncias vivas

**Como isto foi obtido:** captura por `JanelaSource` (Windows Graphics Capture), com o jogo
**coberto pelo navegador** — o `mss` devolvia a tela do browser e o OCR devolvia vazio nas três
regiões. A WGC enxergou as duas janelas normalmente. Isto é a primeira confirmação em campo,
nesta árvore, de que a captura por janela lê o jogo ocluído.

**Fixtures gravadas** (não são sintéticas — são a tela do usuário naquele instante):

    recordings/20260902-004500-renda-duas-instancias/frame_000000_faerlina.png   1720x1392
    recordings/20260902-004500-renda-duas-instancias/frame_000001_yazalaque.png  1720x1392

**Verdade de campo, lida a olho nos recortes ampliados:**

| campo | Faerlina | Yazalaque |
|---|---|---|
| nível | **67** | **69** |
| EXP | **8,0012%** | **76,6646%** |
| bônus | 592% | 612% |
| XM | 0,00 | 70,22 |
| L-Coin | 13.091 | 9.790 |
| adena | **13.160.684** | **1.696.020** |

---

## M-A — As coordenadas do spike sobrevivem ao espaço da janela

O frame da `JanelaSource` é **relativo à janela** e mede 1720x1392, e os retângulos do spike
caem no lugar certo sem tradução nenhuma. A pesquisa tinha previsto isto por aritmética
(`1230+470 = 1700`, `1368+26 ≈ 1392`); agora está medido.

## M-B — A Faerlina SUBIU DE NÍVEL entre o spike e esta medição

O spike (2026-09-01, ~23h50) leu `nível 66, EXP 68,5632%, adena 10.673.628`. Esta medição
(2026-09-02, ~00h45) lê `nível 67, EXP 8,0012%, adena 13.160.684`.

Isto não é curiosidade: é **o caso de REND-03 capturado em dado real**, com as duas pontas
gravadas em disco. A conta correta é `(100 − 68,5632) + 8,0012 = 39,438` pontos percentuais
ganhos, e um nível a mais — não `8,0012 − 68,5632 = −60,562`. Quem for implementar REND-03 tem
agora um par de amostras verdadeiro para testar contra, em vez de um par inventado.

## M-C — O cruzamento 2x×3x É necessário, e a prova saiu de graça

Recorte cru do EXP da Faerlina:

    2x: '76 EXP 80012% 592%'      ← o ponto decimal SUMIU
    3x: 'EXP 8.0012% 592% 76'     ← correto

`80012%` é gramática inválida e seria recusado. Mas o valor certo (`8,0012%`) só existe no 3x.
**Uma leitura de escala única teria recusado esta amostra**, e recusar 100% das amostras é o
mesmo que não ter medidor.

## M-D — E o cruzamento como eu o especifiquei ESTÁ ERRADO

Este é o achado mais importante da noite, e ele **corrige a Área 2 do `01-CONTEXT.md`**.

Eu escrevi "as duas leituras têm que dar o mesmo número; divergiram → recusa". Medido, as duas
escalas quase nunca **concordam** — elas se **revezam**:

| região | quem acerta |
|---|---|
| nível (Faerlina) | **só 3x** (`67`); 2x devolve vazio em toda a banda útil |
| adena (Faerlina) | **só 2x** (`13.160.684` em vmin=150); 3x devolve vazio ou lixo |
| nível (Yazalaque) | ambas (`69`) |
| L-Coin | ambas |

Com a regra "divergiu → recusa", o nível da Faerlina e a adena da Faerlina seriam **recusados
para sempre**, porque uma das escalas abstém sempre.

**A regra correta é a que o `ocr.py` já documenta para o 1x: abstenção não é discordância.**
O cruzamento tem que ser: *entre as leituras de gramática VÁLIDA, todas têm que dar o mesmo
inteiro; vazio e lixo abstêm.* Zero leituras válidas → recusa por ilegibilidade. Duas válidas e
diferentes → recusa por discordância, que é o caso perigoso. Uma válida e uma abstenção →
**aceita**, e é o caso comum.

## M-E — Não existe um piso de brilho único. Nem por barra, nem por instância.

Varredura `inRange(HSV, (0,0,vmin), (179,80,255))` invertida, `vmin` de 100 a 250 de 10 em 10,
nas duas instâncias. Banda em que a leitura sai **correta**:

| região | Faerlina | Yazalaque |
|---|---|---|
| EXP | 150–170 (2x) | 130–170 (ambas) |
| adena | **150 (2x), ponto** | 110 (3x), 150 (2x) |
| L-Coin | 160 (2x), 130–150 (3x) | 100–160 (ambas) |
| nível | 190–220 (**só 3x**) | 170–210 (ambas) |

Três coisas caem daqui:

1. **O piso do nível (190+) e o piso da adena (150) não têm interseção.** Um campo
   `renda_piso_de_brilho` único é impossível. Cada região precisa do seu.
2. **A adena da Faerlina tem banda de UM valor.** Não é margem de segurança, é sorte. O motivo
   está visível no recorte: a barra é semitransparente e naquele instante o fundo atrás da adena
   era **grama clara**, não o fundo escuro do spike. O contraste do texto branco despenca. Isto
   significa que a banda útil **muda com o cenário**, e que um `vmin` calibrado num lugar pode
   não valer em outro. O calibrador tem que dizer a **largura** da banda, não só o valor, e uma
   banda de largura 1 tem que sair como aviso.
3. **O recorte cru NÃO lê a adena.** `2x=''` e `3x=''`. A premissa do LEIT-03 ("o OCR já devolve
   a adena do recorte cru, sem pré-processamento") veio do spike, onde o fundo estava escuro.
   **Ela é falsa no caso geral.** A máscara é obrigatória para a adena, não opcional.

## M-F — A janela de status fica em lugar DIFERENTE em cada instância

| personagem | retângulo do nível (janela-relativo) | lê |
|---|---|---|
| Faerlina | `246,736 30x20` | `67`, só 3x, vmin 190–220 |
| Yazalaque | `236,750 30x20` | `69`, ambas as escalas, vmin 170–210 |

**14 pixels de diferença na vertical e 10 na horizontal.** O usuário posicionou a UI de cada
cliente à mão, e não há razão para eles coincidirem — nem hoje, nem depois de ele arrastar
qualquer painel.

Consequência para o desenho, e ela é estrutural: **a calibração da renda é POR PERSONAGEM.**
Um `renda_nivel` único no `calibration.json` lê o nível certo de uma instância e lixo da outra —
e "lixo" aqui é o pior caso possível, porque a região vizinha (`349` / `112`, o número sob o
nível) é um número plausível que passaria em `numero_valido`.

Isto conversa direto com o REG-04, que o roadmap acrescentou pelo mesmo motivo pelo outro lado:
o registro precisa dizer de quem é a renda. Agora também **a leitura** precisa saber de quem
ela é, antes de ler.

---

## O que isto obriga a mudar nos planos já escritos

| # | O que muda | Onde |
|---|---|---|
| 1 | Cruzamento vira "válidas concordam, abstenção não conta" — não "iguais ou recusa" | `01-01` (tracer do EXP), `01-04` (os três campos) |
| 2 | Piso de brilho é **por região**, nunca único | `01-03` Tarefa 2 já previa recusar o piso único; agora está **medido** que não existe |
| 3 | A adena **exige** máscara; o recorte cru não a lê com fundo claro | `01-04` Tarefa 1 |
| 4 | Retângulos e pisos são **por personagem** | `01-03` (calibrador), e o esquema de chaves do `01-01` |
| 5 | O calibrador reporta a **largura da banda** e avisa quando ela tem largura 1 | `01-03` Tarefa 2 |
| 6 | A precondição do `01-04` (frame ao vivo com o nível visível) **está satisfeita** — as duas fixtures existem | `01-04` Tarefa 1 |

O item 4 é o único que mexe em requisito e não só em plano: `LEIT-05` diz "todas as regiões e
todos os limiares moram no `calibration.json`" e continua verdadeiro, mas agora com uma dimensão
a mais. Fica registrado aqui e propagado para o `REQUIREMENTS.md`.

---

# Adendo — a adena não sai por OCR, e o motivo tem número

Feito depois da revisão dos planos, contra as mesmas duas fixtures. **Este adendo derruba a
decisão de leitor da adena que estava no `01-04`.**

## M-G — A regra da abstenção ACEITA número errado, medido nas duas instâncias

Recorte `1500,1360 200x32`, varredura de piso de 5 em 5. Verdade: 13.160.684 e 1.696.020.

| piso | Faerlina 2x / 3x | veredito | Yazalaque 2x / 3x | veredito |
|---|---|---|---|---|
| 150 | — / — | ambas abstêm | **106020** / — | **uma só → ERRADO E ACEITO** |
| 155 | — / — | ambas abstêm | 1696020 / 1696020 | concordam → certo |
| 160 | — / **91** | **uma só → ERRADO E ACEITO** | — / — | ambas abstêm |
| 165 | — / 13160684 | uma só → certo | — / — | ambas abstêm |

`106.020` e `91` **passam em `numero_valido`**. São gramaticalmente válidos, plausíveis, e
errados por seis ordens de grandeza. A regra "uma válida + uma abstenção → aceita" que eu
mesmo escrevi em M-D os aceitaria — e isto não é hipótese, saiu de dado real.

A banda correta tem **largura 1 passo de 5** nas duas, e o passo vizinho devolve lixo válido.
A varredura de 10 em 10 do M-E **pulou o 155** e por isso concluiu que a Yazalaque não lia.

## M-H — E "as duas escalas concordam" também não salva: elas concordam na L-COIN

Busca exaustiva sobre 4 topos × 4 alturas × 4 esquerdas × 4 direitas × 12 pisos:

| personagem | concordâncias | certas | **erradas** |
|---|---|---|---|
| Faerlina | 173 | **0** | **173** — todas leem `13091`, que é a **L-Coin** |
| Yazalaque | 110 | 40 | 70 — as erradas leem `9790`, a L-Coin |

Quando o recorte encosta na L-Coin e a adena não renderiza no OCR, **as duas escalas concordam
na moeda errada**. Concordância não é evidência de campo certo — é evidência de que as duas
leram a mesma coisa, e a mesma coisa pode ser o campo do lado. Isto confirma o M18 do
planejamento (a L-Coin passa a gramática de milhar inteira) com dado, e mostra que nem a
posição do recorte resolve sozinha: a Faerlina não tem **nenhum** recorte, em 173 tentativas,
onde as duas escalas concordem no valor certo.

## M-I — A fonte da barra tem glifo de 17 px. Os moldes do mercado têm 9.

`segmentar_glifos_no_brilho` sobre o recorte da adena, nas duas fixtures, em todo piso:
`faixa=(9, 25)`, **altura 17**, invariável. Os 13 moldes de
`mercado_templates_de_digito` têm `altura: 9`. **Eles não transferem** — esta é a resposta
medida à primeira pergunta em aberto que a pesquisa deixou, e ela é "não".

## M-J — Mas a SEGMENTAÇÃO por glifo é perfeita, e justo onde o OCR falha

Mesmo recorte, `vmin=180` e `vmin=190` (onde o OCR devolve vazio nas duas escalas):

    Yazalaque  larguras = [15, 5, 2, 5, 5, 5, 2, 5, 5, 5, 16]
                            ^^                                 icone da moeda
                                5  2  5  5  5  2  5  5  5      1 , 6 9 6 , 0 2 0
                                                          ^^   icone seguinte

    Faerlina   larguras = [15, 5, 5, 2, 5, 5, 5, 2, 5, 5, 7, 16]
                                5  5  2  5  5  5  2  5  5  7   1 3 , 1 6 0 , 6 8 4

Sete e oito dígitos de **largura 5**, vírgulas de **largura 2**, ícones de 15/16 nas pontas.
A contagem bate com a verdade de campo nas duas, e é **estável** entre 180 e 190 — uma banda
larga, ao contrário da banda de largura 1 do OCR.

## O que este adendo obriga

1. **A adena da barra é lida por GLIFO, não por OCR.** O `01-04` decide OCR mascarado a partir
   do M-E; M-G e M-H mostram que OCR ali aceita número errado e que nenhuma regra de
   cruzamento entre escalas conserta isso. `ler_glifos` recusa TUDO OU NADA por pontuação — é o
   modo de falha certo para o campo que envenena a taxa.
2. **Os moldes precisam ser construídos para esta fonte** (17 px), e isso é trabalho novo do
   calibrador — `mercado_templates_de_digito` não serve. As duas fixtures já dão os dígitos
   0, 1, 2, 3, 4, 6, 8 e 9; faltam **5 e 7**, que aparecem sozinhos com o tempo. O caminho é o
   do `calibrar_mercado.propor_rotulo`: a máquina propõe, o humano confirma.
3. **Os ícones das pontas (largura 15/16) têm que ser descartados por largura**, não por
   recorte apertado — apertar o recorte foi o que fez as 173 concordâncias erradas da Faerlina.
   `limite_de_glifo_unico` e `larguras_com_folga` já existem para exatamente isso.
4. **O EXP continua por OCR.** Ele lê numa banda larga (130–170) nas duas instâncias, e a
   gramática dele (`\d+[.,]\d{4}%`) não colide com nenhum campo vizinho — o problema da adena é
   ter um sósia gramatical ao lado, e o EXP não tem.
5. **A varredura de piso do calibrador anda de 5 em 5, não de 10 em 10.** O M-E concluiu
   "a Yazalaque não lê" porque pulou o 155. Um passo grosso não erra para o lado seguro.

---

# Correção ao adendo — o dígito da barra é 5x10, e o "17" era o ícone junto

## M-K — A altura 17 do M-I estava contaminada

O M-I mediu `faixa=(9,25)`, altura 17, sobre um recorte da adena que **incluía os ícones de
moeda das duas pontas**. `segmentar_glifos` devolve UMA faixa para o retângulo inteiro — é
decisão de projeto dela, documentada — então o ícone, que é mais alto, empurrou o topo e a base.

Recorte da **L-Coin sem ícone nenhum** (`1440,1355 90x40` na Faerlina), `vmin=180` e `190`:

    faixa = (17, 26)   ALTURA = 10   larguras = [5, 5, 2, 5, 5, 5]   →  1 3 , 0 9 1

E na Yazalaque, `[5, 2, 5, 5, 5]` → `9 , 7 9 0`. Contagem exata, nas duas.

**O dígito da barra é 5 de largura por 10 de altura.** A vírgula é 2 de largura.

Compare com `mercado_templates_de_digito`: `altura: 9, largura: 4`.

## O que muda em relação ao adendo

1. **A conclusão do M-I sobrevive, o número não.** Os moldes do mercado continuam sem servir —
   4x9 contra 5x10 —, mas a diferença é de **um pixel em cada eixo**, não de 9 contra 17. Quem
   escrever a guarda de altura do cortador tem que compará-la contra **10**. Uma guarda escrita
   contra 17 recusaria todo molde legítimo desta barra, e o modo de falha seria um cortador que
   nunca corta nada.
2. **O recorte da adena precisa terminar antes do ícone seguinte.** Em `1560:1690` ainda entra
   um run de largura 9 no fim, e é ele que estica a faixa de 10 para 17. Isso não invalida o
   descarte por largura (o run de 9 é descartável), mas mostra que a faixa compartilhada é
   sensível ao ícone mesmo quando o dígito não é.

## M-L — Os dígitos 5 e 7 JÁ ESTÃO nas duas fixtures, e o bloqueio não é o tempo

O adendo disse que faltam `5` e `7` e que eles "aparecem sozinhos com o tempo". Medido, eles
estão na tela agora, em outros campos **da mesma barra**:

| campo | personagem | valor | dígitos que ele entrega |
|---|---|---|---|
| bônus | Faerlina | `592%` | **5**, 9, 2 |
| EXP | Yazalaque | `76.6646%` | **7**, 6, 4 |
| bônus | Yazalaque | `612%` | 6, 1, 2 |
| L-Coin | Faerlina | `13.091` | 1, 3, 0, 9 |
| adena | Faerlina | `13.160.684` | 1, 3, 6, 0, 8, 4 |

Largura 5 confirmada por segmentação em **todos** eles (bônus da Faerlina em `vmin=180`:
`[2, 11, 2, 5, 5]`; bônus da Yazalaque: `[2, 11, 2, 5, 5, 5]`; EXP da Yazalaque:
`[5, 5, 2, 5, ...]`). É uma fonte só na barra inteira.

**Consequência:** o conjunto 0–9 fecha com as duas fixtures que já existem, se o cortador puder
colher de **qualquer campo da barra**, não só da região da adena. O bloqueio que o plano
registrou como "esperar o farm produzir um 5 e um 7" não existe — ele era um artefato de
restringir a colheita a uma região.

**Ressalva medida, e ela é real:** a região do EXP da Yazalaque, em `vmin` alto e recorte largo,
cola tudo num run único de 141 px, porque a **barra verde de progresso** atrás do texto entra na
máscara. Colher dali exige recorte vertical apertado (`1366:1386` funcionou) ou piso mais alto.
O bônus não tem esse problema e sozinho já entrega o `5`.

---

# Segunda rodada de campo — 2026-09-02, 09h30, e o retângulo do B1 ainda estava errado

Duas fixtures novas, mesmas duas instâncias, **oito horas e meia depois**, com outro cenário
atrás da barra semitransparente:

    recordings/20260902-093000-renda-segundo-cenario/frame_faerlina.png    1720x1392
    recordings/20260902-093000-renda-segundo-cenario/frame_yazalaque.png   1720x1392

| campo | Faerlina 00h45 | Faerlina 09h30 |
|---|---|---|
| adena | 13.160.684 | **15.134.779** |
| L-Coin | 13.091 | 14.465 |
| EXP | 8,0012% | (ilegível no cru; a Yazalaque foi de 76,6646% para **85,2845%**) |

## M-M — A primeira taxa real medida deste projeto

A adena da Faerlina subiu **1.974.095** em ~8,5 horas: **≈ 232 mil adena por hora**. Não é
requisito de fase nenhuma, mas é o primeiro número que responde à pergunta que o usuário fez, e
ele serve de ordem de grandeza para os testes da Fase 2: um salto de ordem de grandeza (REND-04)
tem que ser calibrado contra isto, não contra um número inventado.

## M-N — O retângulo `1500,1360 200x32` que o conserto do B1 escolheu está ERRADO

Ele veio do M-G, que o mediu **na Yazalaque**, cuja L-Coin naquela hora era `9.790` — cinco
caracteres, curta o bastante para terminar antes de `x=1500`. Não era segurança, era o mesmo
tipo de sorte que o M-E flagrou na banda de largura 1.

Na Faerlina de 09h30, com L-Coin `14.465`, o mesmo recorte pega a **cauda da L-Coin, depois o
ícone da moeda de ouro, e só então a adena** — produzindo uma corrida larga **no meio**
(`[2, 7, 6, 5, 18, 5, 5, 2, 5, 5, 7, ...]`, o `18` é o ícone). A regra 3 da peneira recusa forma
com corrida larga no meio, então `adena_da_barra` recusaria **sempre**, em todas as fixtures
dessa hora — exatamente o modo de falha que o B1 existia para consertar, reintroduzido com
outro número.

## M-O — O retângulo que sobrevive às QUATRO fixtures: `1540, 1358, 160x34`

Busca sobre 4 esquerdas × 3 direitas × 4 pisos, com a regra de forma
(*uma corrida larga em cada ponta, e no meio só larguras de dígito e de vírgula*):

| recorte | 00h45 faer | 00h45 yaza | 09h30 faer | 09h30 yaza |
|---|---|---|---|---|
| 1540..1700 | 180, 190 | 170–200 | 180–200 | 180–200 |
| 1500..1700 (do B1) | — | — | **recusa** | **recusa** |
| 1548/1556/1564..* | — | — | — | — |

**`x = 1540..1700`, `y = 1358..1392`, com piso na banda 180–190**, é o único que passa nas
quatro. E a contagem bate com a verdade de campo, dígito por dígito:

| fixture | pontas | meio | n | verdade |
|---|---|---|---|---|
| 00h45 faerlina | (15, 16) | `5 5 2 5 5 5 2 5 5 7` | 10 | `13,160,684` → 10 caracteres |
| 00h45 yazalaque | (15, 16) | `5 2 5 5 5 2 5 5 5` | 9 | `1,696,020` → 9 |
| 09h30 faerlina | (15, 16) | `5 5 2 5 5 7 2 6 6 6` | 10 | `15,134,779` → 10 |
| 09h30 yazalaque | (15, 16) | `7 2 7 5 5 2 5 5 5` | 9 | — |

## Duas coisas que isto obriga

1. **O retângulo do `01-01` vira `1540, 1358, 160x34`**, e o piso de partida da adena vira
   **185** (centro da banda 180–190, que é comum às quatro). O `1500,1360 200x32` fica escrito
   como refutado, com o motivo — ele era o retângulo de UMA fixture.

2. **A peneira aceita dígito de largura 5, 6 OU 7 — não só 5.** Medido: o `4` e o `7` e o `9`
   saem com 6 e 7 px. Uma peneira que exigisse exatamente 5 recusaria `15,134,779` inteiro. A
   vírgula continua 2. Os ícones das pontas são 15 e 16, estáveis nas quatro.

A altura da faixa continua saindo **17** porque os ícones estão dentro do recorte — e isso está
correto e previsto: a regra 1 descarta as pontas por largura e **só então** a faixa é
recomputada, que é o que o `01-05` já especifica.
