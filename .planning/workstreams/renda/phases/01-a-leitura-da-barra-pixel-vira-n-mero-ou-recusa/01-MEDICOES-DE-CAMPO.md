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
