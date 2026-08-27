---
created: 2026-08-26T00:00:00.000Z
title: A moldura da barra própria em terreno escuro
area: detection
severity: major
files:
  - l2scanner/visao.py (BRILHO_MINIMO_DA_MOLDURA_PROPRIA = 60.0)
  - l2scanner/visao.py (_moldura_da_barra_propria, barra_propria_legivel)
  - l2scanner/visao.py (_casamento_do_perfil_proprio, _braco_do_casamento, hp_proprio_aparente)
  - l2scanner/__main__.py (a linha do console que mostra a leitura APARENTE)
  - tests/fixtures/barra_propria/quase_vazia_terreno_atras.png (o proxy de dia, 191x24)
  - tests/fixtures/barra_propria/escuro_cauda_vazia.png (a cena ESCURA, moldura 29.08)
  - tests/fixtures/barra_propria/escuro_cheia.png (a testemunha, moldura 86.42)
  - tests/fixtures/barra_propria/escuro_faixa.png (28 linhas, para os +-2 px)
  - tests/test_inventario_por_cima_da_barra_propria.py (TestAMorteDeVerdadeContinuaSaindo)
  - tests/test_inventario_por_cima_da_barra_propria.py (TestOTerrenoEscuroSomeDoConsole)
  - tests/test_inventario_por_cima_da_barra_propria.py (TestOBuracoPreExistenteDoBracoDeMoldura)
---

## Problem

A quick task `260826-dxm` fechou o falso positivo do inventário: um recorte da
barra própria cuja **moldura** (menor média de cinza entre as quatro bordas)
fica abaixo de **60.0** é declarado ILEGÍVEL, e `hp_proprio` sai `None` em vez
de `0.0`. Isso apagou as 27 mortes falsas + 27 ressurreições falsas que estavam
no `logs/scanner.log` real.

**O portão SUPÕE uma coisa que só foi medida num cenário:** que a parte vazia da
barra mostra terreno mais claro que 60. A região `hp_proprio` calibrada
(esquerda 294, topo 716, 191x24) não tem margem sobrando — as quatro bordas do
recorte caem DENTRO do campo da barra. Quando a barra está cheia, o campo é
vermelho e claro; quando está vazia, o campo é **transparente e mostra o
terreno do jogo**.

**A DIREÇÃO DO DANO é a ruim.** Este não é um risco de alarme falso — é um
risco de SILÊNCIO:

    terreno escuro atrás da barra vazia
      -> moldura abaixo de 60
      -> barra própria declarada ILEGÍVEL
      -> hp_proprio = None
      -> o rastreador CONGELA o estado em vez de concluir
      -> MORTE REAL NÃO É ANUNCIADA

O roadmap chama isso pelo nome: *"morrer calado enquanto a party acha que está
coberta"*. É o pior desfecho declarado deste projeto, e o remédio de hoje é
exatamente o tipo de mudança que pode causá-lo.

**O que foi medido, e onde:**

| Amostra | moldura | Ambiente |
|---|---|---|
| barra de MP a 6.6% (`quase_vazia_terreno_atras.png`) | **78.73** | grama, luz do dia (cinza ~95) |
| as 4 `livre_*.png` | 86.42 | mesma sessão |
| as 4 `coberta_*.png` | 28.00 a 48.92 | inventário aberto |

Folga real da barra vazia até o limiar: **18.73 pontos**. Foi por causa dessa
folga estreita que o limiar ficou no **pé** da faixa medida (60) e não no meio
do vão (63.8) — cada ponto a mais no limiar é folga tirada do lado que não pode
falhar.

**O que NÃO foi medido:** a mesma barra vazia sobre terreno escuro — masmorra,
caverna, à noite, chão de pedra escura. Se o terreno atrás da parte vazia cair
abaixo de 60, a barra vazia de verdade vira "não consigo ler".

**Agravante:** o único proxy de barra vazia que o repositório tem é a barra de
**MP**, não a de HP. Nenhuma amostra alinhada de HP próprio em nível baixo
existe — as 8 fixtures, as 4 `*__hp_proprio*.png` e todos os frames de janela em
`recordings/` estão a 100%. O `recordings/base_janela.png`, que parecia HP
baixo, é na verdade a região DESALINHADA depois da janela ser movida.

## Solution

O que fecha a pendência é uma MEDIÇÃO que hoje não existe, não um ajuste de
número:

1. **Gravar a própria barra com HP baixo em ambiente escuro.** Com o scanner
   rodando, entrar numa masmorra/caverna (ou jogar à noite), deixar o HP cair
   e disparar o gravador de frames. O recorte precisa ser da região
   `hp_proprio` calibrada, alinhada — um recorte desalinhado não serve, como o
   `base_janela.png` já provou.

2. **Rodar `_moldura_da_barra_propria` sobre esse recorte e anotar o número.**

3. **Critério de aceite:** moldura > 70 (10 pontos de folga até o limiar). Se
   ficar entre 60 e 70, a folga é fina demais e o limiar precisa descer. Se
   ficar abaixo de 60, o portão de moldura **está suprimindo morte real hoje** e
   precisa de outro discriminador — não de outro limiar.

4. ~~**Se o limiar não puder separar os dois casos**, o caminho é o mesmo que a
   party já usa: olhar chrome que existe FORA do campo da barra, onde o terreno
   não entra. Isso exige recalibrar a região `hp_proprio` com 1-2 px de margem
   sobrando, o que hoje ela não tem.~~ **REFUTADO — ver abaixo.**

   > **IDEIA REFUTADA (medido em 2026-08-26)** — amostrar o chrome FORA da
   > região calibrada, como `_bordas_da_barra_intactas` faz para as barras da
   > party. Medido num anel de 3 px em volta da região `hp_proprio`:
   >
   > | Amostra | anel de 3 px |
   > |---|---|
   > | barra livre | média **70.7** |
   > | coberta (n=9) | média **36.4 a 63.8** |
   >
   > Isso separa **PIOR** que o teste atual, que fica em 73.7 contra 48.9 — o
   > anel deixa **25 pontos** de separação na mesa.
   >
   > **Motivo, e é estrutural:** quando uma janela grande do jogo cobre a barra,
   > ela cobre a **vizinhança junto**. O inventário e o mercado do XM Essence são
   > painéis grandes, não recortes do tamanho exato da barra — o anel de fora não
   > é refúgio nenhum, é a mesma região coberta pela mesma janela.
   >
   > Quem chegar aqui pelo passo 3 precisa de **outro discriminador**, não de
   > outra região para amostrar o mesmo discriminador. Recalibrar `hp_proprio`
   > com margem sobrando não compra o que este passo prometia.

5. Guardar o recorte como fixture e travar com teste, ao lado de
   `quase_vazia_terreno_atras.png`.

**Enquanto isso não é feito:** o risco é assimétrico e conhecido. O defeito que
o portão corrigiu era CONSTANTE (o usuário abre o inventário o tempo todo, e a
prova são 27 ocorrências num único log); o risco que ele abriu é
CONDICIONAL (exige terreno escuro E barra quase vazia ao mesmo tempo) e nunca
foi observado. A troca vale, mas não é de graça, e o preço está escrito aqui
para não ser esquecido.

**Sinal de que a pendência virou defeito:** aparecer no `scanner.log` uma
sequência de leituras da barra própria ILEGÍVEL durante combate em ambiente
escuro. Ilegibilidade que aparece só ao morrer, e não ao abrir o inventário, é
esta pendência se realizando.

## Medido em 2026-08-26 (tela real, terreno mais escuro) — O RISCO E REAL E A ABORDAGEM NAO TEM CONSERTO POR LIMIAR

Capturada a janela do usuario num cenario mais escuro que a grama do meio-dia.

    brilho medio da janela      dia 99.2   |  escuro 62.6
    terreno atras da barra      dia 96.2   |  escuro 39.2

A moldura da barra VAZIA escala com o terreno (e o terreno que aparece atras da
parte vazia). Projetando a unica amostra real de barra vazia que existe:

    barra vazia, dia    : moldura 78.73  (terreno 96.2)
    barra vazia, escuro : ~32            (terreno 39.2)

CLASSES MEDIDAS, contra o limiar atual de 60:

    coberta pelo inventario     28.0 .. 48.9    (n=9, real)
    livre, cheia, dia           73.7 .. 86.4    (n=45, real)
    livre, vazia, dia           78.7            (n=1, proxy MP real)
    livre, vazia, ESCURO        ~32             (estimado)

**A barra vazia no escuro cai DENTRO da faixa das cobertas.** As duas classes se
sobrepoem nesse regime, entao NENHUM limiar de brilho as separa. Isto deixa de
ser "calibrar melhor o numero" e passa a ser "trocar o discriminador".

## Pistas ja medidas para o substituto (nao decidido)

Testados tres discriminadores independentes de brilho, nas 8 fixtures + o proxy:

1. densidade de bordas verticais  — NAO separa (coberta_0 da 36, livres dao 39)
2. desvio das medias por linha    — NAO separa (coberta 3.0..26.4, livre ~14.5)
3. **casamento do CANTO ESQUERDO da barra** — o mais promissor:
       livres          0.98 .. 1.00
       cobertas       -0.10 .. 0.03   (exceto coberta_0, que da 0.993)
   e, o que mais importa, ele SOBREVIVE a barra esvaziar: comparando a barra de
   MP cheia (88%) contra a mesma barra quase vazia (6.6%), o canto esquerdo
   casa 0.89..0.99 para larguras de 2 a 12 px. O canto DIREITO nao serve — com
   a barra vazia ele mostra terreno, que muda de cena para cena.

O canto esquerdo sozinho deixa passar a `coberta_0` (a unica das cobertas que
nao produz morte: ela le 86.9%, nao 0%). Um portao combinado precisa ser
desenhado e medido.

## O que AINDA falta, e por que

Uma amostra real da barra de HP PROPRIA visivelmente baixa (abaixo de ~60%) em
terreno escuro. Tentativa de captura oportunista em 2026-08-26: 90 segundos
gravando durante farm, o HP nunca saiu de 100%. O proxy de MP cobre "barra
vazia" mas NAO serve para casamento de canto, porque e outra barra (azul, chrome
proprio) — medido: -0.127 contra a referencia de HP.

## Medido e ENTREGUE em 2026-08-27 (quick `260827-fsk`) — a pendencia CONTINUA ABERTA

Esta secao registra o que virou fato, o que mudou no produto, e — principalmente
— **o que continua sem remedio e por que**. O TODO fica em `pending/` porque o
criterio de aceite que ele mesmo escreveu (uma amostra real de HP proprio BAIXO
em terreno escuro) continua sem existir, e porque a medicao desta rodada mostrou
que o alvo e MAIOR do que ele supunha.

### (1) O que virou FATO — a projecao de "~32" virou medicao de 29.08

`recordings/escuro_janela.png` (1392x1720, brilho medio 58.12) e a captura da
cena escura de 2026-08-26. A regiao `hp_proprio` calibrada e (294, 716, 191x24);
a barra de MP do MESMO widget fica 25 px abaixo, em (294, 741, 191x24) — mesma
janela, mesmo frame, mesmo chrome, mesma faixa de terreno.

| amostra (tela REAL) | fracao cheia | moldura | veredito de HOJE |
|---|---|---|---|
| `escuro_janela` HP (294,716) | 100% | 86.42 | LEGIVEL |
| `escuro_janela` MP (294,741) | **88.5%** | **29.08** | **ILEGIVEL** |
| `agora_janela` MP (294,741) | 6.8% | 78.73 | LEGIVEL |

**O widget nao precisa estar VAZIO para cair.** 11.5% de cauda vazia sobre
terreno escuro ja bastam. O regime e mais largo do que este TODO supunha: nao e
"barra quase vazia em masmorra", e "qualquer cauda vazia em cena escura".

A amostra foi RESGATADA para o controle de versao, porque `recordings/` esta no
`.gitignore` e ela era a UNICA copia que existia:

    tests/fixtures/barra_propria/escuro_cauda_vazia.png  (24x191)  moldura 29.08
    tests/fixtures/barra_propria/escuro_cheia.png        (24x191)  moldura 86.42
    tests/fixtures/barra_propria/escuro_faixa.png        (28x191)  faixa[2:26] == cauda

### (2) O que mudou no produto, e o que NAO mudou

Um campo novo `Observacao.hp_proprio_aparente` passou a carregar a leitura que o
portao de hoje descarta, e o console e o `scanner.log` a mostram **MARCADA COMO
APARENTE** (`HP ~88% (aparente)`). Medido: `escuro_cauda_vazia` sai
`hp_proprio=None` / `aparente=0.8848` — hoje as duas seriam NADA.

O que **NAO** mudou, e a prova e o diff:

* `hp_proprio` sai byte a byte como hoje nas 8 amostras de referencia;
* `barra_propria_legivel` nao mudou uma linha;
* **`l2scanner/rastreador.py` ficou FORA DO DIFF**;
* a suite passou de 1125 para 1164 testes **sem um unico teste existente mudando
  de veredito** (768 insercoes, ZERO delecoes nos tres arquivos tocados).

**A descida em cena escura voltou a ser MOSTRADA, nao a ser DECIDIDA.** Nenhum
alerta foi restaurado por esta tarefa.

### (3) Por que a leitura nova NAO PODE virar alerta

`coberta_0` (o inventario cobrindo parte da barra) casa **+0.999** e le 86.91%.
`escuro_cauda_vazia` (legitima) casa +0.964 e le 88.48%. As duas so se ordenam
pela MOLDURA — 48.00 contra 29.08 — e nessa ordem a classe coberta fica dos
**dois lados** do unico ponto legitimo que existe: `coberta_2` da 28.00 e
`coberta_3` da 29.00, **abaixo** dos 29.08 da barra legitima.

Uma banda de moldura seria um limiar ajustado entre n=1 e n=1, com a classe
errada dos dois lados, falhando na direcao do SILENCIO. Tudo que o braco novo
certifica **pode ser um recorte parcialmente ocluido** — e uma leitura que pode
estar ocluida nao pode alimentar alerta nenhum.

### (4) O CUSTO MEDIDO contra a maquina de estado — o achado desta rodada

`hp_proprio` tem **TRES** consumidores no `rastreador.py`, nao um. As duas
versoes anteriores deste plano so tinham olhado para o limiar de MORTE.

| linha | consumidor | o que uma leitura de 0.8691 vinda do inventario faz |
|---|---|---|
| 454 | `_avaliar_se_voce_esta_em_party` | o portao de cegueira da linha 643 so congela em leitura ZERADA; 0.8691 nao congela, entao conta "sem party" -> **`voce_sem_party` falso** |
| 496 | `_avaliar_so_o_proprio` (solo) | `morto_agora` vira False estando MORTO -> **`ressuscitou` falso**, inclusive em `--solo` |
| 833 | injeta o proprio como pseudo-membro | mesmo debounce dos outros -> **reseta contagem de morte em andamento** |

Simulado com `Ajustes()` de producao (`confirmacoes_para_voce_sem_party = 8`,
`confirmacoes_para_morte = 3`):

| cenario | HOJE (`hp_proprio=None`) | se a leitura entrasse na maquina |
|---|---|---|
| quente com party, inventario 30 ticks | nenhum evento | `voce_sem_party` no tick 27 |
| morre, depois abre o inventario | `morreu` (22) | `morreu` (22), **`ressuscitou` (34)**, **`voce_sem_party` (37)** |
| SOLO: morre, depois abre o inventario | `morreu` (22) | `morreu` (22), **`ressuscitou` (34)** |
| morrendo (2 de 3), abre e fecha o inventario | `morreu` no tick **18** | `morreu` no tick **20** (contagem resetada) |

Duas classes de alerta falso e um atraso de morte. A `ressuscitou` falsa e
literalmente metade do defeito que a quick `260826-dxm` pagou para matar (27
mortes + 27 ressurreicoes). O usuario abre o inventario o tempo todo: nao e
raro, e frequente.

**Foi por isso que a leitura foi para um campo SEPARADO.** A seguranca nao vem
de guardas novas no rastreador — vem de a leitura **nao existir** para ele.

### (5) O REGIME QUE CONTINUA SEM REMEDIO — a morte em cena escura

No regime de leitura ZERO sobre terreno escuro as duas classes nao se sobrepoem:
elas se **INTERCALAM**. Medido sobre a cauda vazia real de terreno escuro,
ladrilhada ate 191 colunas:

| recorte | leitura | casamento |
|---|---|---|
| **barra vazia GENUINA, terreno escuro** | 0.0000 | **+0.627** |
| painel cobrindo 3 col a esquerda (c1/c2/c3) | 0.0000 | +0.624 / +0.618 / **+0.642** |
| painel cobrindo 5 col a esquerda (c1/c2/c3) | 0.0000 | +0.622 / +0.619 / **+0.645** |
| painel cobrindo 10 col a esquerda (c1/c2/c3) | 0.0000 | +0.529 / +0.473 / **+0.637** |

**A oclusao pontua MAIS ALTO que a genuina: +0.645 contra +0.627.** O motivo e
estrutural: o perfil e a media por LINHA, cobrir 5 de 191 colunas quase nao move
essa media, e Pearson e cego a escala. **Nenhum limiar separa as duas classes**,
entao aceitar a barra vazia legitima em cena escura e recusar o painel que le
zero NAO PODEM coexistir com os dados que existem.

**A MORTE em cena escura continua sem remedio.** As duas saidas possiveis:

  (a) uma amostra REAL das duas classes — o passo 1 deste TODO, ainda pendente;
  (b) um sinal TEMPORAL no rastreador: "estava caindo e ficou cega" nao e
      "ficou cega com o inventario aberto". E mudanca de CAMADA, com risco
      proprio de falso positivo, e nao cabe numa quick.

### (6) DEFEITO PRE-EXISTENTE encontrado no caminho: o braco de MOLDURA

`coberta_2` com o painel cobrindo o lado ESQUERDO da barra le **0.0000** com
moldura **64.00** — acima do limiar de 60 — e **ja e aceito HOJE**. Medido para
k = 5, 20 e 60 colunas cobertas. E uma morte falsa por um caminho que NENHUM dos
dois bracos cobre.

Nao foi criado nem fechado por esta tarefa, e **nao e fechavel por portao de
leitura**, porque o braco de moldura PRECISA poder certificar leitura zero — e
assim que a morte e anunciada em terreno de dia.

**Candidato MEDIDO:** contiguidade do preenchimento (`sobra` = 0 nas 51 amostras
genuinas, 11..186 nos compostos de oclusao a esquerda). **PRECONDICAO para
adota-lo:** medir contra **TERRENO VERMELHO** primeiro — lava e chao avermelhado
podem gerar colunas cheias espurias, e o modo de falha dessa heuristica e
SILENCIO, que e o pior desfecho declarado deste projeto.

Preso por `TestOBuracoPreExistenteDoBracoDeMoldura`, que QUEBRA no dia em que
alguem fechar o buraco — de proposito, para obrigar a atualizar este registro.

### (7) A LACUNA DE COBERTURA que deixou isto escapar

**Nenhum teste deste repositorio levava um recorte coberto ate DENTRO do
`Rastreador`.** O unico que chega la
(`test_trinta_frames_de_inventario_aberto_nao_emitem_morte`) **FILTRA os eventos
por `MORREU`** — entao um `voce_sem_party` ou um `ressuscitou` falso passaria
despercebido. Foi por isso que o risco do item (4) apareceu no plan-check e nao
na suite.

Fechada nesta tarefa por `TestACobertaAtravessaORastreadorSemEmitirNada`, e vale
como **regra geral**: teste de deteccao que filtra por UM tipo de evento nao
prova ausencia dos outros.

### (8) +-2 px e a tolerancia INTEIRA, sem rede alem dela

O casamento desliza a referencia de 20 valores sobre o perfil de 24, e por isso
sobrevive a desalinhamento vertical — mas so ate +-2 px:

| dy | moldura (portao de HOJE) | casamento |
|---|---|---|
| -4 | 37.67 | +0.293 |
| -3 | 35.04 | +0.293 |
| **-2 a +2** | **12.64 .. 32.33** | **+0.964 (constante ate a 3a casa)** |
| +3 | 30.29 | +0.364 |
| +4 | 30.58 | +0.340 |

Em +-3 px o casamento (0.293/0.364) E a moldura (35.04/30.29) reprovam JUNTOS:
silencio. O `recordings/base_janela.png` ja e um caso real de desalinhamento por
janela movida. Isto **nao e regressao** — hoje dy=+1 ja reprova — mas tambem nao
e robustez resolvida, e fica registrado como segundo regime nao coberto.

### (9) O sinal de que a pendencia virou defeito — ATUALIZADO

O sinal antigo ("barra propria ILEGIVEL durante combate em ambiente escuro")
deixa de servir sozinho, porque agora a linha APARECE no log com a marca de
aparente. O sinal novo:

> **barra propria saindo no `scanner.log` como APARENTE durante combate escuro,
> com a descida sendo mostrada e NENHUMA morte sendo anunciada.**

Isso aponta exatamente para o regime de leitura zero do item (5): a barra chegou
a zero, o casamento nao consegue distinguir "vazia genuina" de "coberta", e o
scanner cala. **E o pior desfecho declarado do projeto, e ele continua possivel.**

### O que AINDA falta — inalterado, e agora com mais razao

O passo 1 deste TODO continua valendo palavra por palavra: **gravar a propria
barra de HP com nivel BAIXO em ambiente escuro**, alinhada com a regiao
`hp_proprio` calibrada. `recordings/hp_baixo/` continua VAZIO (conferido em
2026-08-27). Toda a evidencia de terreno escuro que existe vem do widget de MP
do mesmo frame, 25 px abaixo.

Com a leitura APARENTE agora saindo no log, capturar essa amostra ficou
POSSIVEL — antes o log nao mostrava nada durante a descida inteira, e sem log
nao havia como saber que frame gravar. **Essa e a entrega real desta rodada: ela
nao fecha a pendencia, ela devolve a ferramenta que permite fecha-la.**
