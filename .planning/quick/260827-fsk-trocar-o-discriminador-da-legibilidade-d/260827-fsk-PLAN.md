---
phase: quick-260827-fsk
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - l2scanner/visao.py
  - tests/fixtures/barra_propria/escuro_cauda_vazia.png
  - tests/fixtures/barra_propria/escuro_cheia.png
  - tests/fixtures/barra_propria/escuro_faixa.png
  - tests/test_inventario_por_cima_da_barra_propria.py
  - .planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md
  - .planning/STATE.md
autonomous: true
requirements: [QUICK-260827-fsk]

estimate:
  tokens: 75000
  raw_tokens: 58000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "O DEFEITO VIROU FIXTURE. `tests/fixtures/barra_propria/escuro_cauda_vazia.png` e captura REAL da tela do usuario em cena escura: a barra do proprio personagem, 88.5% cheia, com a cauda vazia mostrando terreno escuro. Mede moldura 29.08 — DENTRO da faixa das cobertas (28.00..48.92) — e o portao de hoje a declara ILEGIVEL."
    - "A DESCIDA DE HP VOLTA A SER LIDA EM CENA ESCURA. Ponta a ponta por `extrair`: hoje `hp_proprio` sai `None`, depois sai `0.8848`. Hoje, em cena escura, a barra propria fica ilegivel assim que QUALQUER cauda vazia aparece — o rastreador congela em 100% durante a descida inteira. Depois, a descida e lida ate 5%."
    - "O BRACO NOVO NAO PODE, POR CONSTRUCAO, PRODUZIR MORTE FALSA. Ele so certifica leitura ACIMA de `LEITURA_MINIMA_PARA_O_CASAMENTO = 0.05`, que e 2.5x o `fracao_hp_considerada_zero = 0.02` do rastreador. Verificado por exaustao, nao por amostra: 2304 compostos de painel real nas DUAS direcoes de oclusao e com tres preenchimentos de direita; dos 1733 que leem em ou abaixo do limiar de morte, o braco novo aceita ZERO."
    - "AS 27 MORTES FALSAS CONTINUAM SUPRIMIDAS. As 3 fixtures de coberta que leem 0% seguem ILEGIVEIS, e as 4 cobertas parametrizadas do arquivo seguem ILEGIVEIS na chamada estrutural (sem leitura). Nenhuma oclusao — pela esquerda, pela direita ou total — passa a produzir morte."
    - "AS 45 LIVRES REAIS CONTINUAM LEGIVEIS, 45 de 45, e a legibilidade e MONOTONA: o braco novo entra em OR com o de moldura, entao nenhum recorte que hoje produz leitura para de produzir."
    - "O DISCRIMINADOR NOVO E INVARIANTE A BRILHO — e por isso resolve o que nenhum limiar de brilho resolve: +0.964 num recorte cuja moldura despencou para 29.08. E TOLERA ±2 px de desalinhamento vertical: a versao de posicao fixa cai de +0.972 para -0.179 com UM pixel, o que seria uma segunda bomba de silencio."
    - "O QUE NAO FECHA ESTA DITO, COM NUMERO, E NAO ESTA ESCONDIDO. No regime de morte (leitura 0) sobre terreno escuro as duas classes se INTERCALAM: barra vazia genuina da casamento +0.627, e o mesmo recorte com um painel cobrindo 5 colunas a esquerda da +0.645 — a oclusao pontua MAIS ALTO que a genuina. Nenhum limiar as separa, e por isso o frame da morte em cena escura continua sem remedio nos dados que existem."
    - "O BURACO PRE-EXISTENTE FOI ENCONTRADO E REGISTRADO, nao herdado em silencio: `coberta_2` com o painel cobrindo a esquerda le 0.0000 e ja passa HOJE pelo braco de moldura (64.00, acima de 60). Nao e causado por esta mudanca e nao e fechado por ela — vai para o TODO com a medicao."
    - "A suite nao regrediu: `python -m pytest tests/ -q` sai com pelo menos `1125 passed, 2 skipped`, e `--collect-only` conta MAIS testes que o baseline de 1127. Verificado por comando, nao por afirmacao."
    - "Zero dependencia nova: `numpy` e `cv2` ja sao usados em `l2scanner/visao.py`, e `pyproject.toml` nao muda desde o commit do plano (`9d5533e`)."
  artifacts:
    - "l2scanner/visao.py com `PERFIL_DE_REFERENCIA_DA_BARRA_PROPRIA`, `CASAMENTO_MINIMO_DO_PERFIL_PROPRIO`, `LEITURA_MINIMA_PARA_O_CASAMENTO`, `_casamento_do_perfil_proprio` e `_braco_do_casamento`"
    - "tests/fixtures/barra_propria/escuro_cauda_vazia.png (191x24, resgatada de recordings/ que e gitignored)"
    - "tests/fixtures/barra_propria/escuro_cheia.png (191x24, idem)"
    - "tests/fixtures/barra_propria/escuro_faixa.png (191x28, com 2 px de margem — o unico artefato versionado capaz de provar a tolerancia a ±2 px sobre pixels REAIS)"
    - "tests/test_inventario_por_cima_da_barra_propria.py com a classe de terreno escuro, a varredura EXAUSTIVA nas duas direcoes e a caracterizacao do buraco pre-existente"
    - ".planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md atualizado e AINDA EM pending/"
  key_links:
    - "`barra_propria_legivel` -> `extrair` -> `Observacao.hp_proprio` -> `Rastreador._avaliar_proprio` -> evento MORREU. E o unico caminho pelo qual a morte do usuario e anunciada."
    - "`LEITURA_MINIMA_PARA_O_CASAMENTO` (0.05, em visao.py) -> `Ajustes.fracao_hp_considerada_zero` (0.02, em rastreador.py). Duas camadas, um acoplamento numerico: um tripwire de teste amarra os dois, senao baixar o limiar do rastreador reabre o buraco pela porta dos fundos."
    - "`_moldura_da_barra_propria` PERMANECE como primeiro braco do OR. E o que torna a legibilidade monotona — e e tambem onde mora o buraco pre-existente, porque ele certifica leitura ZERO (e precisa: e assim que a morte e anunciada em terreno de dia)."
    - "`recordings/escuro_janela.png` -> as tres fixtures novas. `recordings/` esta no `.gitignore`: esta e a UNICA evidencia de cena escura que existe e ela esta FORA do controle de versao."
---

<objective>
Trocar o discriminador da legibilidade da barra PROPRIA de BRILHO DE MOLDURA
para CASAMENTO DE PERFIL DE LINHAS — invariante a brilho — e prender o braco
novo atras de um PORTAO DE LEITURA, para que ele nao possa certificar um recorte
que le zero.

Purpose: hoje, em cena escura, a barra propria e declarada ILEGIVEL assim que
qualquer cauda vazia aparece — medido com a barra ainda 88.5% cheia. `hp_proprio`
sai `None` e o rastreador congela em 100% durante a descida inteira.

Output: a descida de HP volta a ser lida em cena escura, com prova de que nenhuma
oclusao — pela esquerda, pela direita ou total — passa a produzir morte falsa; e
o registro honesto de que o FRAME DA MORTE em cena escura continua sem remedio,
porque no regime de leitura zero as duas classes se intercalam nos dados que
existem.
</objective>

<revisao>
## Revisao 2 — o que mudou depois do PLAN-CHECK, e por que

O check BLOQUEOU a revisao 1 com dois blockers, e os dois estavam certos. Este
plano nao ajusta o texto: ele muda o DESENHO e ENCOLHE a promessa.

**O erro:** a revisao 1 mediu a varredura de painel numa direcao so —
`livre_0[:, :k]` + `coberta[:, k:]`, o painel cobrindo a DIREITA — e concluiu
sobre as duas. Mas `medir_barra` le a CORRIDA INICIAL a partir da esquerda, entao
a direcao que zera a leitura e exatamente a que nao foi medida. Medida agora, a
"folga de 5.2x" reivindicada e NEGATIVA: com o painel cobrindo 5 colunas a
esquerda e a barra cheia a direita, a leitura e 0.0000 e o casamento e +1.000.
O maximo da classe coberta-que-le-zero nao e +0.236; e +1.000. Nenhum limiar de
casamento separa — a mesma critica que o plano fazia a moldura.

**O que mudou no desenho:** o braco novo passou a exigir `leitura > 0.05` alem do
casamento. Isso torna a propriedade de seguranca VERDADEIRA POR CONSTRUCAO em
vez de por limiar, e ela foi verificada por exaustao (2304 compostos, 1733 no
regime de morte, zero aceitos).

**O que mudou na promessa:** a revisao 1 dizia que a barra vazia legitima em
terreno escuro voltaria a ser lida. Isso NAO E ALCANCAVEL com os dados que
existem, e agora esta medido — ver a secao 4. O que este plano entrega e a
DESCIDA (leitura acima de 5%), nao o frame da morte. A promessa encolheu para o
tamanho da prova.

**O que sobreviveu, porque o check confirmou:** o tracer da Task 1 resgatando a
evidencia gitignored antes que algo dependa dela; `escuro_faixa[2:26]` provando
o proprio alinhamento; o `test $? -eq 1` distinguindo "falhou" de "nao coletou";
a invariancia a brilho como o discriminador certo; e o TODO seguindo em
`pending/` com verify que falha se ele for movido para `done/`.
</revisao>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md
@.planning/quick/260827-fsk-trocar-o-discriminador-da-legibilidade-d/260827-fsk-PLAN-CHECK.md
@l2scanner/visao.py
@tests/test_inventario_por_cima_da_barra_propria.py
@./.claude/CLAUDE.md
</context>

<measured>

## Tudo abaixo foi MEDIDO em 2026-08-27 sobre pixels reais deste repositorio. Nenhum numero e escolhido.

### 1. O portao de hoje REPROVA uma barra legitima — a prova esta em disco

`recordings/escuro_janela.png` (1392x1720, brilho medio 58.12) e a captura da
cena escura de 2026-08-26. A regiao `hp_proprio` calibrada e (294, 716, 191x24);
a barra de MP do MESMO widget fica 25 px abaixo, em (294, 741, 191x24) — mesma
janela, mesmo frame, mesmo chrome, mesma faixa de terreno.

| amostra (tela REAL) | fracao cheia | moldura | veredito de HOJE |
|---|---|---|---|
| `escuro_janela` HP (294,716) | 100% | 86.42 | LEGIVEL |
| `escuro_janela` MP (294,741) | **88.5%** | **29.08** | **ILEGIVEL** |
| `agora_janela` MP (294,741) | 6.8% | 78.73 | LEGIVEL |

O widget nao precisa estar vazio para cair. 11.5% de cauda vazia sobre terreno
escuro basta. O "~32 estimado" do TODO agora e **29.08 medido**.

### 2. As duas classes, contra os dois discriminadores

| classe | n | fonte | moldura | casamento |
|---|---|---|---|---|
| livre, cheia, dia | 45 | `recordings/inv2/*_propria.png` | 73.67 .. 86.42 | +0.993 .. +1.000 |
| livre, cheia, ESCURO | 1 | `escuro_janela` HP | 86.42 | +0.944 |
| livre, 88.5% cheia, ESCURO | 1 | `escuro_janela` MP | **29.08** | **+0.964** |
| livre, 6.8% cheia, dia | 1 | `quase_vazia_terreno_atras.png` | 78.73 | +0.979 |
| coberta TOTAL, le 0% | 8 | `recordings/inv3/*_JANELA.png` | 28.00 .. 48.92 | -0.059 .. +0.236 |
| coberta parcial, le 86.91% | 1 | `coberta_0` | 48.00 | +0.999 |

MOLDURA: livre minimo 29.08 **abaixo** de coberta maximo 48.92 — as classes se
sobrepoem em 19.8 pontos e nenhum limiar de brilho as separa.

### 3. A varredura de painel, agora nas DUAS direcoes — o erro da revisao 1

`medir_barra` mede a corrida inicial DA ESQUERDA. Cobrir a direita understates a
leitura; cobrir a esquerda **zera** a leitura. A revisao 1 mediu so a primeira.

**3a — painel a DIREITA (`livre_0[:, :k]` + `coberta[:, k:]`), leitura = k/191:**

| k | leitura | pior casamento das 3 |
|---|---|---|
| 5 | 2.62% | +0.324 |
| 15 | 7.85% | +0.371 |
| 20 | 10.47% | +0.675 |
| 60 | 31.41% | +0.933 |

**3b — painel a ESQUERDA (`coberta[:, :k]` + `livre_0[:, k:]`), leitura = 0.0000
em TODO k > 0:**

| k coberto | leitura | moldura | casamento c1 / c2 / c3 | veredito HOJE |
|---|---|---|---|---|
| 5 | **0.0000** | 48.92 / 64.00 / 55.42 | **+1.000 / +1.000 / +0.999** | c2 ja PASSA hoje |
| 20 | **0.0000** | idem | +0.956 / +0.972 / +0.967 | c2 ja PASSA hoje |
| 60 | **0.0000** | idem | +0.573 / +0.938 / +0.723 | c2 ja PASSA hoje |
| 120 | **0.0000** | idem | +0.017 / +0.451 / +0.193 | c2 ja PASSA hoje |

**3c — painel a ESQUERDA com a direita VAZIA (o caso realista), leitura 0.0000:**

| k | direita vazia DIA | direita vazia ESCURO |
|---|---|---|
| 5 | +0.979 / +0.977 / +0.977 | +0.622 / +0.619 / **+0.645** |
| 20 | +0.917 / +0.935 / +0.935 | +0.358 / +0.454 / +0.542 |
| 60 | +0.421 / +0.879 / +0.566 | +0.063 / +0.408 / +0.238 |

**Conclusao: o casamento sozinho NAO separa.** Um limiar de 0.40 aceitaria
compostos que leem 0.0000 — a classe de morte falsa que a quick `260826-dxm`
pagou para matar.

### 4. A COLISAO no regime de morte — por que a promessa encolheu

Terreno ESCURO, leitura 0.0000 dos dois lados:

| recorte | leitura | casamento |
|---|---|---|
| **barra vazia GENUINA, terreno escuro** | 0.000 | **+0.627** |
| painel cobrindo 3 col a esquerda (c1/c2/c3) | 0.000 | +0.624 / +0.618 / **+0.642** |
| painel cobrindo 5 col a esquerda (c1/c2/c3) | 0.000 | +0.622 / +0.619 / **+0.645** |
| painel cobrindo 10 col a esquerda (c1/c2/c3) | 0.000 | +0.529 / +0.473 / **+0.637** |

**A oclusao pontua MAIS ALTO que a genuina: +0.645 contra +0.627.** As classes
nao se sobrepoem — elas se INTERCALAM. Nenhum limiar as separa, e o motivo e
estrutural: cobrir 5 de 191 colunas quase nao move a media de cada linha, e
Pearson e cego a escala. O discriminador e insensivel a oclusao pontual pela
esquerda, que e justamente a oclusao que zera a leitura.

**Portanto: aceitar a barra vazia legitima em terreno escuro e recusar o painel
que le zero NAO PODEM coexistir com os dados que existem.** Isto nao e um limiar
mal escolhido; e ausencia de informacao no recorte. O que falta esta na secao 10.

### 5. O portao proposto — o braco novo atras de um portao de LEITURA

    legivel(recorte, leitura) =
        desvio >= 3.0
        E ( moldura >= 60.0                                    # braco de HOJE, intocado
            OU ( leitura is not None
                 E leitura > 0.05                              # PORTAO DE LEITURA
                 E casamento >= 0.40 ) )                       # braco novo

`leitura = None` desliga o braco novo. Quem nao sabe a leitura nao pode usar o
braco cuja seguranca DEPENDE dela — e isso preserva o significado de todas as
chamadas de um argumento que ja existem em `tests/test_modo_solo.py`.

**A propriedade de seguranca e por CONSTRUCAO, nao por limiar:** o braco novo
nunca certifica leitura em regime de morte, porque `0.05 > 0.02`. Verificado por
exaustao: **2304 compostos** (4 paineis reais x 3 preenchimentos de direita x
k de 0 a 191), dos quais **1733 leem em ou abaixo de `fracao_hp_considerada_zero`**
— e o braco novo aceita **ZERO** deles. Custo em tempo de suite: **0.06 s**.

### 6. Escolha de `LEITURA_MINIMA_PARA_O_CASAMENTO = 0.05`

- `Ajustes().fracao_hp_considerada_zero = 0.02`. 0.05 e **2.5x** isso.
- 0.05 de 191 colunas sao ~9.5 colunas: um painel precisaria deixar 10 colunas de
  barra a mostra para produzir leitura aceitavel, e a essa altura a leitura ja
  nao e morte.
- As duas amostras genuinas que o braco novo precisa aceitar leem 0.8848 e 1.0000
  — 17x acima do portao.
- Erra-se para CIMA de proposito: cada ponto a mais e leitura recusada (silencio
  parcial na descida), cada ponto a menos e leitura certificada perto da morte.

### 7. Escolha de `CASAMENTO_MINIMO_DO_PERFIL_PROPRIO = 0.40`

Com o portao de leitura no lugar, o casamento **deixa de ser a propriedade de
seguranca** e passa a ser o segundo braco: impedir que um recorte totalmente
coberto invente leitura.

- coberta TOTAL (n=8, tela real), maximo: +0.236 -> folga de 0.164
- as duas genuinas de cena escura: +0.944 e +0.964 -> folga de 0.544
- ponto medio das duas classes: 0.590. O limiar fica **abaixo** dele, porque
  errar para cima recusa barra legitima.

### 8. Sensibilidade a deslocamento vertical — por que o casamento DESLIZA

Medido sobre o recorte de MP da janela real, dy de -4 a +4:

| dy | moldura (portao de HOJE) | casamento (proposto) |
|---|---|---|
| -4 | 37.67 | +0.293 |
| -3 | 35.04 | +0.293 |
| **-2 a +2** | **12.64 .. 32.33** | **+0.964 (constante)** |
| +3 | 30.29 | +0.364 |
| +4 | 30.58 | +0.340 |

O casamento e constante ate a terceira casa em ±2 px, enquanto a moldura pula de
12.64 a 32.33 — caotica exatamente onde a outra e estavel. Em ±3 px o casamento
cai para +0.293/+0.364, **ambos abaixo do limiar de 0.40**, e o recorte volta a
ser recusado.

> CORRECAO DA REVISAO 1: ela dizia "+0.376/+0.435 ... recusado", e 0.435 e MAIOR
> que 0.40 — o texto descrevia um caso ACEITO chamando-o de recusado. Os numeros
> daquela linha vinham do recorte de HP, nao do de MP que a fixture representa.
> Os corretos sao os da tabela acima. A conclusao se manteve; o numero nao.

### 9. Pre-voo do impacto na suite — JA EXECUTADO com o desenho CORRIGIDO

O portao da secao 5, incluindo a reestruturacao de `extrair`, foi rodado contra a
suite inteira por plugin, sem tocar no repo: **1 failed, 1124 passed, 2 skipped**.

A unica falha e `TestOInventarioNaoViraMorte::test_nenhum_recorte_coberto_produz_leitura[coberta_0]`
— `coberta_0` passa a ler 86.91% por `extrair` em vez de `None`.

Os outros dois testes que a revisao 1 quebrava (`test_coberta_pelo_inventario_e_ILEGIVEL[coberta_0]`
e `test_o_desvio_SOZINHO_deixaria_a_coberta_passar`) **passam intactos**, porque
chamam `barra_propria_legivel` com UM argumento e o braco novo fica desligado.

Baseline a bater: `1127 tests collected`, `1125 passed, 2 skipped`.

### 10. O que NAO foi medido, e o que falta para fechar

1. **Nenhuma amostra de HP PROPRIO em nivel baixo, em terreno escuro.**
   `recordings/hp_baixo/` esta VAZIO — conferido. Toda a evidencia de terreno
   escuro vem do widget de MP do mesmo frame, 25 px abaixo.
2. **O frame da morte em cena escura continua sem remedio** — secao 4. Fechar
   exige distinguir "barra vazia sobre terreno escuro" de "painel cobrindo as
   primeiras colunas", e no recorte inteiro nao ha informacao que os separe.
   O que poderia fechar, e que NAO cabe nesta tarefa: (a) uma amostra real das
   duas classes para procurar um discriminador com dado de verdade em vez de
   composto sintetico; (b) um sinal TEMPORAL no rastreador — "a barra estava
   caindo e ficou cega" nao e a mesma coisa que "ficou cega com o inventario
   aberto" —, o que e mudanca de camada e traz risco proprio de falso positivo.
3. **O buraco pre-existente do braco de moldura** (secao 3b, `coberta_2`):
   le 0.0000 com moldura 64.00 e ja e aceito HOJE. Nao e criado nem fechado por
   esta mudanca. Nao pode ser fechado pelo portao de leitura, porque o braco de
   moldura PRECISA certificar leitura zero — e assim que a morte e anunciada em
   terreno de dia. Fechar exige uma checagem de contiguidade do preenchimento
   (`sobra` = colunas cheias depois da corrida inicial, medida em 0 nas 51
   amostras genuinas e em 11..186 nos compostos de oclusao a esquerda), e essa
   checagem so pode entrar depois de medida contra TERRENO VERMELHO — lava e chao
   avermelhado podem produzir colunas cheias espurias, e o modo de falha dela e
   silencio.
4. **±2 px e a tolerancia inteira**, sem rede alem disso: em ±3 px o casamento
   (0.293/0.364) e a moldura (35.04/30.29) reprovam juntos. Nao e regressao — hoje
   dy=+1 ja reprova — mas nao deve ser vendido como robustez resolvida.

### 11. Constantes a embutir

`PERFIL_DE_REFERENCIA_DA_BARRA_PROPRIA` — media de cinza por linha de
`livre_0.png`, linhas 2 a 21 (20 valores, deixando 2 px de folga para o
deslizamento):

    72.81, 72.57, 72.31, 72.33, 59.71, 104.48, 85.23, 88.60, 88.44, 94.38,
    85.98, 87.73, 86.40, 89.79, 64.02, 72.60, 72.48, 72.69, 72.69, 72.38

`LINHAS_DO_PERFIL_PROPRIO = 24`
`CASAMENTO_MINIMO_DO_PERFIL_PROPRIO = 0.40`
`LEITURA_MINIMA_PARA_O_CASAMENTO = 0.05`

</measured>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Resgatar a evidencia perecivel e prender o defeito num teste VERMELHO</name>
  <precondition>`recordings/escuro_janela.png` existe no disco (1392x1720). Ele esta em `.gitignore` e e a UNICA gravacao de cena escura que existe. Se o arquivo nao estiver la, PARE e reporte: a evidencia sumiu e o plano nao pode ser executado.</precondition>
  <files>tests/fixtures/barra_propria/escuro_cauda_vazia.png, tests/fixtures/barra_propria/escuro_cheia.png, tests/fixtures/barra_propria/escuro_faixa.png, tests/test_inventario_por_cima_da_barra_propria.py</files>
  <behavior>
    - `escuro_cauda_vazia.png` mede moldura 29.08 e e declarada ILEGIVEL pelo portao de hoje — e e uma barra LEGITIMA, 88.5% cheia. Este e o defeito.
    - Ponta a ponta por `extrair`, com a calibracao apontando para as cores DO WIDGET da fixture: hoje `hp_proprio` sai `None`; depois da Task 2 sai `0.8848`.
    - `escuro_cheia.png` (HP 100%, mesma cena escura) mede moldura 86.42 e ja e legivel hoje — a testemunha de que a cena escura por si nao derruba nada; o que derruba e a CAUDA VAZIA.
    - `escuro_faixa.png` tem 28 linhas e `escuro_faixa[2:26]` e igual a `escuro_cauda_vazia` — a fixture carrega a prova do proprio alinhamento.
  </behavior>
  <action>
Extrair TRES fixtures de `recordings/escuro_janela.png`, que e gitignored e portanto a unica copia. Recortes exatos, em linhas e colunas do arquivo: `escuro_cheia.png` = linhas 716 a 740, colunas 294 a 485 (a regiao `hp_proprio` calibrada, HP em 100%); `escuro_cauda_vazia.png` = linhas 741 a 765, mesmas colunas (o widget de MP, 25 px abaixo, 88.5% cheio, com a cauda mostrando terreno escuro); `escuro_faixa.png` = linhas 739 a 767, mesmas colunas (a mesma cauda vazia com 2 px de margem em cima e embaixo, que e o que permite provar tolerancia a desalinhamento sobre pixels reais). Gravar as tres em `tests/fixtures/barra_propria/` com `cv2.imwrite`; conferir que as duas primeiras sairam 24x191x3 e a faixa 28x191x3, e que `escuro_faixa[2:26]` e igual a `escuro_cauda_vazia`.

Escrever, em `tests/test_inventario_por_cima_da_barra_propria.py`, a classe `TestOTerrenoEscuroNaoPodeCalarAMorte`, com docstring trazendo os numeros da secao 1 do plano e dizendo que as duas classes se sobrepoem NESTE ARQUIVO e nao em teoria. Ela afirma o comportamento DESEJADO, entao nasce VERMELHA — ordem proposital, a mesma das quicks anteriores deste repo (commit `test(...)` antes do `feat(...)`).

Asercoes:
(1) `_moldura_da_barra_propria(recorte("escuro_cauda_vazia"))` fica abaixo de `BRILHO_MINIMO_DA_MOLDURA_PROPRIA` e portanto dentro da faixa das cobertas. Passa desde ja e deve continuar passando: documenta a sobreposicao, nao o remedio.
(2) `barra_propria_legivel(recorte("escuro_cauda_vazia"), leitura=0.8848)` e `True`. VERMELHA hoje — a funcao ainda nem aceita o segundo argumento, e o `TypeError` conta como vermelho.
(3) Ponta a ponta: `extrair(frame_solo("escuro_cauda_vazia"), calibracao_do_widget).hp_proprio` nao e `None`. **A fixture e o widget de MP (azul), entao a mascara de HP nao a enxerga** — por isso a calibracao passada a `extrair` tem que ser `dataclasses.replace(calibracao, limiares_hp=calibracao.limiares_mp)`. Isto NAO e sintetizar pixel nenhum: e apontar o detector para as cores do widget que a fixture contem, e todo o resto do caminho de `extrair` fica intocado. Escrever essa razao na docstring do teste, porque e o detalhe que faz alguem achar que o teste esta trapaceando.
(4) `barra_propria_legivel(recorte("escuro_cheia"))` e `True` — a testemunha; passa hoje e depois.
(5) a cauda 100% vazia, `recorte("escuro_cauda_vazia")[:, 169:]`, tem `medir_barra` com os limiares de MP igual a 0.0, e moldura abaixo do limiar. Afirmar os dois juntos: o primeiro prova que a derivacao do recorte esta certa, o segundo prova que o terreno escuro sozinho reprova no portao de hoje. A coluna 169 vem da medicao — 88.48% de 191 px termina o preenchimento ali.

Nao tocar em `l2scanner/visao.py` nesta task. Nao alterar nenhum teste existente nesta task.
  </action>
  <verify>
    <automated>python -c "import cv2,sys; sys.path.insert(0,'.'); from l2scanner.visao import _moldura_da_barra_propria as m; d='tests/fixtures/barra_propria/'; a=cv2.imread(d+'escuro_cauda_vazia.png'); b=cv2.imread(d+'escuro_cheia.png'); f=cv2.imread(d+'escuro_faixa.png'); assert a.shape==(24,191,3) and b.shape==(24,191,3) and f.shape==(28,191,3), (a.shape,b.shape,f.shape); assert (f[2:26]==a).all(), 'a faixa nao esta alinhada com a cauda vazia'; print('cauda_vazia moldura', round(m(a),2), '| cheia moldura', round(m(b),2)); assert abs(m(a)-29.08)<0.05 and abs(m(b)-86.42)<0.05"</automated>
    <automated>python -m pytest "tests/test_inventario_por_cima_da_barra_propria.py::TestOTerrenoEscuroNaoPodeCalarAMorte" -q; test $? -eq 1 && echo "VERMELHO confirmado — o defeito esta preso no teste"</automated>
  </verify>
  <done>As tres fixtures existem, com as formas certas, com `escuro_faixa[2:26]` igual a `escuro_cauda_vazia`, e conferindo 29.08 e 86.42. A classe `TestOTerrenoEscuroNaoPodeCalarAMorte` existe e falha nas asercoes 2 e 3. O `test $? -eq 1` e proposital e nao e frouxo: pytest devolve 1 para "teste falhou" e 4 para "nao coletou nada", entao esquecer de escrever a classe REPROVA o verify em vez de passar por engano. Commit `test(quick-260827-fsk): ...` com fixtures e teste juntos.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Casamento de perfil atras de um portao de leitura, e a varredura exaustiva nas duas direcoes</name>
  <files>l2scanner/visao.py, tests/test_inventario_por_cima_da_barra_propria.py</files>
  <behavior>
    - `_casamento_do_perfil_proprio`: `escuro_cauda_vazia` +0.964, `escuro_cheia` +0.944, `livre_0` +1.000, `quase_vazia_terreno_atras` +0.979, cobertas totais -0.059..+0.236, `coberta_0` +0.999.
    - As 5 janelas de 24 linhas dentro de `escuro_faixa.png` (dy de -2 a +2) dao TODAS +0.964, enquanto a moldura das mesmas 5 varia de 12.64 a 32.33.
    - `_braco_do_casamento(recorte, leitura)` e `False` para TODOS os 1733 compostos que leem em ou abaixo de `Ajustes().fracao_hp_considerada_zero`, nas duas direcoes de oclusao.
    - `barra_propria_legivel(recorte)` com UM argumento continua dando exatamente o veredito de hoje — o braco novo fica desligado sem leitura.
    - `extrair` passa a devolver 0.8848 para `escuro_cauda_vazia` (com a calibracao do widget) e 0.8691 para `coberta_0`.
    - Recorte uniforme `np.full((8,120,3), 60)` continua ILEGIVEL.
  </behavior>
  <action>
Em `l2scanner/visao.py`, ao lado das constantes de moldura, acrescentar `PERFIL_DE_REFERENCIA_DA_BARRA_PROPRIA` (os 20 valores da secao 11, como tupla de float), `LINHAS_DO_PERFIL_PROPRIO = 24`, `CASAMENTO_MINIMO_DO_PERFIL_PROPRIO = 0.40` e `LEITURA_MINIMA_PARA_O_CASAMENTO = 0.05`. Documentar em comentario, com as tabelas das secoes 2, 3, 4, 6, 7 e 8, de onde cada numero saiu.

Implementar `_casamento_do_perfil_proprio(recorte) -> float`: converter para cinza, tirar a media por LINHA (`axis=1`); se o perfil nao tiver `LINHAS_DO_PERFIL_PROPRIO` valores, reamostrar para esse comprimento com `np.interp`; deslizar a referencia de 20 valores sobre o perfil de 24 em todas as posicoes possiveis, calcular a correlacao de Pearson em cada uma e devolver a MAIOR. Quando qualquer um dos dois vetores nao tiver variancia o denominador e zero e a funcao devolve 0.0 — nunca divide por zero e nunca aprova o degenerado.

Implementar `_braco_do_casamento(recorte, leitura) -> bool`: `False` quando `leitura` e `None` ou `<= LEITURA_MINIMA_PARA_O_CASAMENTO`; caso contrario `_casamento_do_perfil_proprio(recorte) >= CASAMENTO_MINIMO_DO_PERFIL_PROPRIO`. Esta funcao existe separada de propriedade: e ELA que carrega a propriedade de seguranca, e o teste exaustivo precisa poder mira-la direto em vez de inferi-la do portao inteiro.

Alterar a assinatura para `barra_propria_legivel(recorte, leitura=None)` e o corpo para: desvio abaixo do minimo devolve `False`; moldura no minimo ou acima devolve `True`; senao devolve `_braco_do_casamento(recorte, leitura)`. O padrao `leitura=None` desliga o braco novo, e isso e uma decisao e nao um descuido — quem nao sabe a leitura nao pode usar o braco cuja seguranca depende dela. Escrever isso no codigo.

Reestruturar o bloco da barra propria em `extrair`: hoje ele pergunta a legibilidade e so depois mede. Passa a MEDIR primeiro, com `cal.limiares_hp` sobre a regiao inteira do recorte, e so entao perguntar `barra_propria_legivel(recorte_proprio, leitura)`; `hp_proprio` recebe a leitura quando legivel e `None` quando nao. Manter a guarda de `recorte_proprio` ausente ou vazio antes de medir, e manter o comentario existente sobre `None` e `0.0` serem coisas diferentes.

Escrever na docstring de `barra_propria_legivel` as tres razoes de forma, que sao o miolo da tarefa:
  (a) o segundo braco e CORRELACAO e nao brilho, porque Pearson e cego a escala do cinza — a mesma estrutura le +0.964 num recorte cuja moldura despencou de 86.42 para 29.08, e nenhum limiar de brilho separa as classes nesse regime (livre minimo 29.08 CONTRA coberta maximo 48.92);
  (b) ele DESLIZA e nao compara posicao fixa, porque a versao de posicao fixa cai de +0.972 para -0.179 com UM pixel de desalinhamento vertical — trocaria uma bomba de silencio por outra;
  (c) ele so vale ACIMA de `LEITURA_MINIMA_PARA_O_CASAMENTO`, e este e o ponto mais importante do arquivo: o casamento e insensivel a oclusao pontual pela esquerda, que e exatamente a oclusao que ZERA a leitura. Registrar a colisao medida — barra vazia genuina em terreno escuro da +0.627 e o mesmo recorte com 5 colunas cobertas a esquerda da +0.645, a oclusao pontuando MAIS ALTO que a genuina. Sem o portao de leitura, o braco novo reabriria as 27 mortes falsas da quick `260826-dxm`.

Preservar integralmente o paragrafo existente sobre a POLARIDADE INVERTIDA em relacao a `_bordas_da_barra_intactas`, e registrar que a moldura permanece como primeiro braco do OR de proposito, porque isso mantem a legibilidade MONOTONA.

Nos testes, o pre-voo da secao 9 diz que **exatamente um** teste existente quebra: `test_nenhum_recorte_coberto_produz_leitura[coberta_0]`. Restringir a parametrizacao dele as 3 que leem 0%, escrevendo em `COBERTAS_QUE_LIAM_ZERO` a razao medida. Em `test_coberta_pelo_inventario_e_ILEGIVEL`, que continua verde porque chama com um argumento so, acrescentar a docstring que ela afirma o portao ESTRUTURAL (sem leitura) e que o veredito ponta-a-ponta de `coberta_0` esta no teste dedicado — senao a asercao vira meia-verdade sem aviso.

Acrescentar as classes novas, todas com o numero medido na mensagem de falha:
  - `TestOBracoNovoNuncaCertificaLeituraDeMorte`: a varredura EXAUSTIVA nas DUAS direcoes. Para cada preenchimento de direita em {`livre_0`, a cauda escura de `escuro_cauda_vazia[:, 169:]` ladrilhada ate 191 colunas, `quase_vazia_terreno_atras`}, para cada painel em `coberta_0..3`, para k de 0 a 191: montar o composto `painel[:, :k]` + `direita[:, k:]`, medir a leitura com `cal.limiares_hp`, e — quando a leitura ficar em ou abaixo de `Ajustes().fracao_hp_considerada_zero` — exigir `not _braco_do_casamento(composto, leitura)`. Ler as fixtures UMA vez fora do laco: medido, a varredura inteira custa 0.06 s em cache contra 0.39 s relendo disco. Afirmar tambem, na mesma classe, que o numero de compostos no regime de morte e maior que zero — senao um erro de montagem tornaria a varredura vacua e ela passaria verde sem testar nada.
  - `TestOPortaoDeLeituraEstaAmarradoAoRastreador`: `LEITURA_MINIMA_PARA_O_CASAMENTO > Ajustes().fracao_hp_considerada_zero`. Sao duas camadas e um acoplamento numerico; sem este tripwire, baixar o limiar do rastreador reabre o buraco pela porta dos fundos, longe deste arquivo.
  - `TestOCasamentoTolera2pxDeDesalinhamento`: percorrer as 5 janelas de 24 linhas dentro de `escuro_faixa.png` (dy de -2 a +2) e exigir que o casamento de todas fique acima do limiar. Nada de `np.roll` — rolar inventa linhas, e a faixa existe para que cada deslocamento venha de pixels reais. Afirmar no mesmo teste que a moldura das mesmas 5 janelas varia de ~12.6 a ~32.3, isto e, que o discriminador ANTIGO e caotico onde o novo e estavel. Fechar com `escuro_faixa[2:26] == escuro_cauda_vazia`, para o teste provar o proprio alinhamento em vez de confiar num indice escrito a mao.
  - `TestOCustoDeAceitarACobertaParcial`: por `extrair`, `coberta_0` passa a devolver ~0.8691 em vez de `None`; afirmar que a leitura fica muito acima de `Ajustes().fracao_hp_considerada_zero`, ou seja que ela nao pode virar morte.
  - `TestOBuracoPreExistenteDoBracoDeMoldura`: CARACTERIZACAO, nao remedio. `coberta_2[:, :k]` + `livre_0[:, k:]` para k em {5, 20, 60} le 0.0000 com moldura 64.00 e ja e aceito HOJE pelo braco de moldura. Afirmar que o buraco EXISTE e apontar, na docstring, para o TODO — assim, no dia em que alguem o fechar, este teste quebra e obriga a atualizar o registro. Escrever que ele nao e criado por esta mudanca e nao e fechado por ela, porque o braco de moldura PRECISA certificar leitura zero: e assim que a morte e anunciada em terreno de dia.
  - `TestAsQuarentaECincoLivresContinuamLegiveis`: se `recordings/inv2/` existir, afirmar 45 de 45; senao `pytest.skip` com a razao. Aplicar o MESMO cuidado a qualquer teste que fale em "8 cobertas": as 4 fixtures versionadas sao afirmadas sempre, as 4 de `recordings/inv3/` so quando o diretorio existir, porque `recordings/` e gitignored e um clone limpo nao consegue prova-las.

Nao acrescentar dependencia nenhuma.
  </action>
  <verify>
    <automated>python -m pytest tests/test_inventario_por_cima_da_barra_propria.py -q</automated>
    <automated>python -m pytest tests/ -q 2>&1 | tail -3</automated>
    <automated>python -m pytest tests/ --collect-only -q 2>/dev/null | tail -1 | awk '{print "coletados:", $1} $1<=1127 {print "FALHOU: a suite nao cresceu (baseline 1127)"; exit 1}'</automated>
    <automated>python -c "import cv2,sys; sys.path.insert(0,'.'); from l2scanner.visao import barra_propria_legivel as ok, _casamento_do_perfil_proprio as c; r=lambda n: cv2.imread('tests/fixtures/barra_propria/'+n+'.png'); [print(n, round(c(r(n)),3)) for n in ['escuro_cauda_vazia','escuro_cheia','livre_0','coberta_0','coberta_1','coberta_2','coberta_3']]; assert ok(r('escuro_cauda_vazia'), 0.8848); assert not ok(r('escuro_cauda_vazia')); assert not ok(r('coberta_1'), 0.0) and not ok(r('coberta_2'), 0.0) and not ok(r('coberta_3'), 0.0)"</automated>
    <automated>python -c "import sys; sys.path.insert(0,'.'); import numpy as np; from l2scanner.visao import barra_propria_legivel; assert not barra_propria_legivel(np.full((8,120,3),60,dtype=np.uint8), 1.0); print('degenerado uniforme segue ILEGIVEL')"</automated>
    <automated>test -z "$(git diff --name-only 9d5533e..HEAD -- pyproject.toml)" && echo "pyproject intocado desde o commit do plano"</automated>
  </verify>
  <done>`python -m pytest tests/ -q` sai com pelo menos `1125 passed, 2 skipped` e `--collect-only` conta mais de 1127. `escuro_cauda_vazia` e legivel COM leitura e ilegivel SEM. A varredura exaustiva das duas direcoes passa e nao e vazia. O tripwire que amarra `LEITURA_MINIMA_PARA_O_CASAMENTO` ao `fracao_hp_considerada_zero` esta no lugar. `pyproject.toml` nao mudou desde `9d5533e`. Commits `feat(quick-260827-fsk): ...` para `visao.py` e `test(quick-260827-fsk): ...` para os testes.</done>
</task>

<task type="auto">
  <name>Task 3: Registrar o que NAO fechou — o TODO continua ABERTO, e agora com tres regimes</name>
  <files>.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md, .planning/STATE.md</files>
  <action>
Atualizar o TODO **sem move-lo para `done/`**. Ele permanece em
`.planning/todos/pending/` porque o criterio de aceite que ele mesmo escreveu
continua sem amostra, e porque esta tarefa DESCOBRIU que o alvo e maior do que
ele supunha.

Acrescentar uma secao datada de 2026-08-27 com, nesta ordem:

(1) **O que virou fato.** A projecao de "~32" virou medicao: 29.08, no widget de
MP de `recordings/escuro_janela.png`, com a barra apenas 88.5% cheia — o regime
nao precisa de barra vazia, 11.5% de cauda basta. A amostra foi resgatada para
`tests/fixtures/barra_propria/escuro_cauda_vazia.png`, porque `recordings/` esta
no `.gitignore` e ela era a unica copia.

(2) **O que mudou no produto.** O segundo braco do portao passou a ser o
casamento do perfil de linhas, invariante a brilho e deslizante em ±2 px, atras
de um portao de leitura de 0.05. A descida de HP em cena escura volta a ser lida
de 100% ate 5%; hoje ela e cega desde 99%.

(3) **A pista do canto esquerdo, resolvida por medicao.** Registrar que o canto
esquerdo citado no TODO nao foi adotado, e a razao: ele so casa enquanto as
primeiras colunas ainda tem preenchimento, entao com a barra em 0% — o frame da
morte — nao tem o que casar.

(4) **O REGIME QUE CONTINUA SEM REMEDIO, com o numero que o prova.** No regime de
leitura zero sobre terreno escuro as duas classes se INTERCALAM: barra vazia
genuina da casamento +0.627, e o mesmo recorte com um painel cobrindo 5 colunas a
esquerda da +0.645 — a oclusao pontua MAIS ALTO. Nenhum limiar separa, e o motivo
e estrutural: cobrir 5 de 191 colunas quase nao move a media por linha, e Pearson
e cego a escala. Escrever que este e o motivo de o plano ter ENCOLHIDO a promessa
para a descida, e listar as duas saidas possiveis: uma amostra real das duas
classes, ou um sinal TEMPORAL no rastreador ("estava caindo e ficou cega" nao e
"ficou cega com o inventario aberto"), que e mudanca de camada e traz risco
proprio de falso positivo.

(5) **O BURACO PRE-EXISTENTE, novo neste registro.** `coberta_2` com o painel
cobrindo a esquerda le 0.0000 e ja e aceito HOJE pelo braco de moldura (64.00,
acima de 60) — morte falsa por um caminho que nenhum dos dois portoes cobre. Nao
e criado nem fechado por esta tarefa. Nao pode ser fechado pelo portao de
leitura, porque o braco de moldura PRECISA certificar leitura zero: e assim que a
morte e anunciada em terreno de dia. O candidato medido e a contiguidade do
preenchimento — `sobra`, colunas cheias depois da corrida inicial, medida em 0
nas 51 amostras genuinas e em 11..186 nos compostos de oclusao a esquerda —, e
ela so pode entrar depois de medida contra TERRENO VERMELHO, porque lava e chao
avermelhado podem gerar colunas cheias espurias e o modo de falha dela e
SILENCIO. Ha um teste de caracterizacao prendendo este buraco.

(6) **±2 px e a tolerancia inteira**, sem rede alem disso: em ±3 px o casamento
(0.293/0.364) e a moldura (35.04/30.29) reprovam juntos. Nao e regressao, mas nao
e robustez resolvida, e o proprio TODO ja registra um caso real de janela movida.

(7) **O custo aceito**, com numero: `coberta_0` passa a ler 86.91% por `extrair`
em vez de `None`, e nao pode virar morte porque a leitura fica 43x acima do
limiar de morte.

(8) **O sinal de que a pendencia virou defeito**, atualizado: agora seria barra
propria ILEGIVEL em combate escuro APESAR do portao novo, o que apontaria para o
regime de leitura zero do item 4 — nao mais para o brilho.

Atualizar o front-matter `files:` do TODO para citar os arquivos que agora
importam, incluindo as tres fixtures novas.

Em `.planning/STATE.md`: manter a linha do todo em `## Pending Todos` (segue
aberto, severidade major), acrescentar a linha da quick em `## Quick Tasks
Completed` no estilo das anteriores — o que foi medido, o que mudou, **o que NAO
fechou e por que**, e a contagem da suite nas duas pontas — e atualizar
`## Session Continuity`.
  </action>
  <verify>
    <automated>test -f ".planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md" && echo "TODO segue em pending/"</automated>
    <automated>test ! -f ".planning/todos/done/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md" && echo "TODO nao foi fechado"</automated>
    <automated>python -c "import io,sys; t=io.open('.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md',encoding='utf-8').read(); [sys.exit('FALTA no TODO: '+n) for n in ['2026-08-27','29.08','0.627','0.645','escuro_cauda_vazia','coberta_2'] if n not in t]; print('o TODO registra a medicao, a colisao, a fixture e o buraco pre-existente')"</automated>
    <automated>python -c "import io,sys; s=io.open('.planning/STATE.md',encoding='utf-8').read(); assert '260827-fsk' in s, 'STATE nao cita a quick'; assert 'moldura-da-barra-propria-em-terreno-escuro' in s, 'STATE perdeu o todo aberto'; print('STATE atualizado e o todo segue listado')"</automated>
    <automated>python -m pytest tests/ -q 2>&1 | tail -2</automated>
  </verify>
  <done>O TODO continua em `pending/`, datado de 2026-08-27, com os oito registros acima — em especial o regime que NAO fecha (a colisao +0.627 contra +0.645) e o buraco pre-existente do braco de moldura — e com o `files:` atualizado. STATE.md cita a quick em `Quick Tasks Completed` dizendo o que nao fechou, mantem o todo em `Pending Todos` e tem a continuidade de sessao atualizada. Commit `docs(quick-260827-fsk): ...`.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pixels da tela do jogo -> `barra_propria_legivel` | entrada NAO CONFIAVEL: qualquer janela do jogo, qualquer terreno, qualquer overlay pode estar naqueles 191x24 px |
| `l2scanner/visao.py` -> `l2scanner/rastreador.py` | `LEITURA_MINIMA_PARA_O_CASAMENTO` so e seguro enquanto for maior que `Ajustes.fracao_hp_considerada_zero`; o acoplamento atravessa duas camadas |
| `recordings/` (gitignored) -> `tests/fixtures/` (versionado) | promocao de artefato local nao versionado para evidencia permanente |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-fsk-01 | Spoofing | painel de inventario se passando por barra que le ZERO | critical | mitigate | E o defeito que a revisao 1 teria reintroduzido. Mitigado por CONSTRUCAO com o portao de leitura: o braco novo so certifica leitura acima de 0.05, contra um limiar de morte de 0.02. Verificado por EXAUSTAO nas duas direcoes de oclusao — 2304 compostos, 1733 no regime de morte, zero aceitos. Teste `TestOBracoNovoNuncaCertificaLeituraDeMorte`. |
| T-fsk-02 | Denial of Service | `barra_propria_legivel` recusando recorte legitimo | critical | mitigate | Recusa -> `hp_proprio=None` -> rastreador congela -> morte calada. Mitigado por monotonia: o braco de moldura fica no OR, entao nada que hoje passa deixa de passar; e 45/45 livres reais seguem legiveis. Teste `TestOTerrenoEscuroNaoPodeCalarAMorte`. |
| T-fsk-03 | Elevation of Privilege | `fracao_hp_considerada_zero` baixado no rastreador | high | mitigate | Baixar o limiar de morte para 0.05 ou mais anularia o portao de leitura a distancia, sem tocar em `visao.py`. Mitigado pelo tripwire `TestOPortaoDeLeituraEstaAmarradoAoRastreador`, que quebra a suite se a ordem entre os dois numeros se inverter. |
| T-fsk-04 | Tampering | perfil de referencia e os dois limiares | medium | mitigate | Constantes ajustadas no escuro reabrem o defeito em silencio. Mitigado prendendo as classes em testes com o numero medido na mensagem de falha. |
| T-fsk-05 | Spoofing | oclusao pela esquerda passando pelo braco de MOLDURA | high | transfer | Buraco PRE-EXISTENTE (`coberta_2`, moldura 64.00, leitura 0.0000), nao criado nem fechado aqui, e nao fechavel pelo portao de leitura porque o braco de moldura precisa certificar leitura zero. Transferido para o TODO com a medicao e com o candidato (`sobra`) e a condicao para adota-lo (medir contra terreno vermelho). Preso por `TestOBuracoPreExistenteDoBracoDeMoldura`. |
| T-fsk-06 | Tampering | fixtures PNG novas | low | accept | Arquivos versionados; alteracao aparece no diff e derruba as asercoes de 29.08 / 86.42 da Task 1. |
| T-fsk-07 | Information Disclosure | fixtures resgatadas de captura de tela real | low | accept | Recortes de 191x24 px de barras de HP/MP. Sem nome de conta, telefone, token ou texto de chat. |
| T-fsk-SC | Tampering | instalacao de pacotes (npm/pip/cargo) | n/a | accept | Zero instalacao: `numpy` e `cv2` ja sao importados por `l2scanner/visao.py`. Sem task de install, o portao de legitimidade de pacote nao se aplica. `pyproject.toml` verificado contra `9d5533e` na Task 2. |
</threat_model>

<verification>
1. `python -m pytest tests/ -q` sai com pelo menos `1125 passed, 2 skipped`, e `--collect-only` conta mais que o baseline de `1127`.
2. `barra_propria_legivel(escuro_cauda_vazia, leitura=0.8848)` e `True`; com um argumento so, e `False` — o braco novo depende da leitura.
3. Ponta a ponta: `extrair` devolve `0.8848` para `escuro_cauda_vazia` com a calibracao apontada para as cores do widget, contra `None` hoje.
4. A varredura exaustiva das DUAS direcoes passa, e nao e vazia: existem compostos no regime de morte e o braco novo recusa todos.
5. `LEITURA_MINIMA_PARA_O_CASAMENTO > Ajustes().fracao_hp_considerada_zero`.
6. As 5 janelas de `escuro_faixa.png` (dy -2..+2) sao todas legiveis.
7. Recorte uniforme `np.full((8,120,3), 60)` segue ILEGIVEL.
8. `pyproject.toml` sem mudanca desde `9d5533e`.
9. O TODO segue em `.planning/todos/pending/` e registra a medicao, a COLISAO do regime de morte e o buraco pre-existente.
</verification>

<success_criteria>
- A descida de HP em cena escura volta a ser lida — medido ponta a ponta na fixture `escuro_cauda_vazia.png`, que hoje sai `None`.
- Nenhuma oclusao passa a produzir morte falsa, provado por exaustao nas duas direcoes e nao por amostra de uma direcao so.
- As 27 mortes falsas do inventario continuam suprimidas e a legibilidade continua monotona (45/45 livres reais).
- Todo limiar do diff vem de uma medicao registrada neste plano e repetida em comentario no codigo.
- O que NAO fecha esta dito com numero: o frame da morte em cena escura, o buraco pre-existente do braco de moldura e o teto de ±2 px — os tres no TODO, que permanece ABERTO.
</success_criteria>

<output>
Create `.planning/quick/260827-fsk-trocar-o-discriminador-da-legibilidade-d/260827-fsk-SUMMARY.md` when done.

O SUMMARY precisa dizer, explicitamente e com numero: (a) que a projecao de "~32"
virou medicao de 29.08 numa fixture agora versionada; (b) que o discriminador
novo e invariante a brilho e fica atras de um portao de LEITURA, e que e o portao
de leitura — nao o limiar de casamento — que impede morte falsa, verificado por
exaustao nas duas direcoes; (c) que a promessa ENCOLHEU em relacao a primeira
versao do plano, e por que: no regime de leitura zero as classes se intercalam
(+0.627 genuina contra +0.645 ocluida); (d) que o buraco pre-existente do braco
de moldura foi descoberto e registrado; e (e) que o TODO NAO FECHOU.
</output>