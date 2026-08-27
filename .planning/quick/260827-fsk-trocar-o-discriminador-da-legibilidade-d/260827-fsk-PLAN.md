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
  tokens: 70000
  raw_tokens: 55000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "O DEFEITO DEIXOU DE SER PROJECAO E VIROU FIXTURE. `tests/fixtures/barra_propria/escuro_cauda_vazia.png` e uma captura REAL da tela do usuario em cena escura: a mesma barra do proprio personagem, 88.5% cheia, com a cauda vazia mostrando terreno escuro. Ela mede moldura 29.08 — DENTRO da faixa das cobertas (28.00..48.92) — e o portao de hoje a declara ILEGIVEL. As duas classes nao se sobrepoem em teoria: elas se sobrepoem NESTE ARQUIVO."
    - "A barra legitima sobre terreno escuro volta a ser lida: `barra_propria_legivel(escuro_cauda_vazia)` e `True` e `extrair(...).hp_proprio` sai NUMERO, nunca `None`. Este e o unico objetivo da tarefa — `hp_proprio=None` congela o rastreador e a morte real nao e anunciada."
    - "AS 27 MORTES FALSAS CONTINUAM SUPRIMIDAS. As 8 amostras reais de barra coberta pelo inventario que leem 0% (`inv3/*_JANELA.png`, e as fixtures `coberta_1`, `coberta_2`, `coberta_3`) seguem ILEGIVEIS: casamento medido -0.059..+0.236, todas abaixo do limiar 0.40. Zero das 8 passa."
    - "AS 45 LIVRES REAIS CONTINUAM LEGIVEIS, 45 de 45. A mudanca e MONOTONA por construcao — o portao novo entra em OR com o de moldura, entao nenhum recorte que hoje produz leitura para de produzir."
    - "O portao novo e INVARIANTE A BRILHO, e e por isso que ele resolve o que nenhum limiar de brilho resolve: o casamento e uma correlacao de Pearson, cega a escala e ao deslocamento do cinza. Medido: a mesma estrutura le +0.964 num recorte cuja moldura despencou para 29.08."
    - "O portao novo TOLERA ±2 px de deslocamento vertical do recorte. Medido: a versao ingenua (sem deslizamento) cai de +0.972 para -0.179 com UM pixel de desalinhamento — seria uma bomba de silencio, exatamente o defeito que estamos consertando. A versao deslizante da o MESMO numero em dy de -2 a +2."
    - "O custo esta MEDIDO E LIMITADO, nao presumido: `coberta_0` passa a ser LEGIVEL (casamento 0.999) e le 86.91%. Ela nunca produziu morte falsa e nao pode produzir: a varredura sobre pixels reais mostra que o casamento sobe junto com a fracao visivel da barra, e nenhum composto passa no limiar 0.40 com leitura abaixo de 10.47% — contra `fracao_hp_considerada_zero = 0.02`, uma folga de 5.2x."
    - "A suite nao regrediu: `python -m pytest tests/ -q` sai com pelo menos `1125 passed, 2 skipped` e com MAIS testes do que comecou. Cobertura acrescentada, nunca trocada."
    - "O TODO NAO FOI FECHADO POR DECRETO. Ele continua em `.planning/todos/pending/` e diz, com numero, o que esta provado e o que continua dependendo de uma captura em campo: nenhuma amostra da barra de HP PROPRIA visivelmente baixa em terreno escuro existe no repositorio, e a evidencia de terreno escuro vem do widget de MP da mesma janela."
    - "Zero dependencia nova: `numpy` e `cv2` ja sao usados em `l2scanner/visao.py`. `pyproject.toml` fica fora do diff."
  artifacts:
    - "l2scanner/visao.py com `PERFIL_DE_REFERENCIA_DA_BARRA_PROPRIA`, `CASAMENTO_MINIMO_DO_PERFIL_PROPRIO` e `_casamento_do_perfil_proprio`"
    - "tests/fixtures/barra_propria/escuro_cauda_vazia.png (191x24, resgatada de recordings/ que e gitignored)"
    - "tests/fixtures/barra_propria/escuro_cheia.png (191x24, resgatada de recordings/ que e gitignored)"
    - "tests/fixtures/barra_propria/escuro_faixa.png (191x28, 2 px de margem em cima e embaixo — o unico artefato versionado capaz de provar a tolerancia a ±2 px sobre pixels REAIS)"
    - "tests/test_inventario_por_cima_da_barra_propria.py com a classe de terreno escuro, a varredura de painel e o teste de deslocamento"
    - ".planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md atualizado e AINDA EM pending/"
  key_links:
    - "`barra_propria_legivel` -> `extrair` -> `Observacao.hp_proprio` -> `Rastreador._avaliar_proprio` -> evento MORREU. E o unico caminho pelo qual a morte do usuario e anunciada, e o portao esta na cabeca dele."
    - "`_moldura_da_barra_propria` PERMANECE no portao, em OR com o casamento. E o que torna a mudanca monotona: tudo que hoje passa continua passando pelo mesmo braco de sempre."
    - "`recordings/escuro_janela.png` -> as duas fixtures novas. O `recordings/` esta no `.gitignore`: esta e a UNICA evidencia de cena escura que existe e ela esta FORA do controle de versao. Resgata-la e a parte mais perecivel do trabalho."
---

<objective>
Trocar o discriminador da legibilidade da barra PROPRIA: de BRILHO DE MOLDURA
para CASAMENTO DE PERFIL DE LINHAS, mantendo a moldura em OR para que a mudanca
seja monotona.

Purpose: hoje um recorte legitimo da barra propria sobre terreno escuro e
declarado ILEGIVEL, `hp_proprio` sai `None`, o rastreador CONGELA o estado e a
morte real nao e anunciada. O ROADMAP chama esse desfecho pelo nome — "morrer
calado enquanto a party acha que esta coberta" — e o PROJECT.md o trata como o
unico defeito inaceitavel do produto.

Output: um portao invariante a brilho, medido contra as 54 amostras de tela real
que o repositorio ja tem, mais duas fixtures novas resgatadas de uma gravacao
NAO VERSIONADA; e o TODO atualizado, ainda aberto, com o que continua dependendo
de captura em campo.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md
@l2scanner/visao.py
@tests/test_inventario_por_cima_da_barra_propria.py
@./.claude/CLAUDE.md
</context>

<measured>

## Tudo abaixo foi MEDIDO durante o planejamento, em 2026-08-27, sobre pixels reais deste repositorio. Nenhum numero deste plano e escolhido; todos sao lidos.

### 1. O portao de hoje REPROVA uma barra legitima — e a prova esta em disco

`recordings/escuro_janela.png` (1392x1720, brilho medio 58.12) e a captura da
cena escura de 2026-08-26. A regiao `hp_proprio` calibrada e (294, 716, 191x24);
a barra de MP do MESMO widget fica 25 px abaixo, em (294, 741, 191x24). Mesma
janela, mesmo frame, mesmo chrome, mesma faixa de terreno.

| amostra (tela REAL) | fracao cheia | moldura | veredito de HOJE |
|---|---|---|---|
| `escuro_janela` HP (294,716) | 100% | 86.42 | LEGIVEL |
| `escuro_janela` MP (294,741) | **88.5%** | **29.08** | **ILEGIVEL** |
| `agora_janela` MP (294,741) | 6.8% | 78.73 | LEGIVEL |

O widget nao precisa estar VAZIO para cair. Basta 11.5% de cauda vazia sobre
terreno escuro para a moldura despencar a 29.08 — dentro da faixa das cobertas
(28.00..48.92). O "~32 estimado" do TODO agora e **29.08 medido**.

### 2. As duas classes, contra os dois discriminadores

| classe | n | fonte | moldura | casamento (proposto) |
|---|---|---|---|---|
| livre, cheia, dia | 45 | `recordings/inv2/*_propria.png` | 73.67 .. 86.42 | +0.993 .. +1.000 |
| livre, cheia, ESCURO | 1 | `escuro_janela` HP | 86.42 | +0.944 |
| livre, 88.5% cheia, ESCURO | 1 | `escuro_janela` MP | **29.08** | **+0.964** |
| livre, 6.8% cheia, dia | 1 | `quase_vazia_terreno_atras.png` | 78.73 | +0.979 |
| **coberta que le 0%** | **8** | `recordings/inv3/*_JANELA.png` | 28.00 .. 48.92 | **-0.059 .. +0.236** |
| coberta que le 86.91% (`coberta_0`) | 1 | idem | 48.00 | +0.999 |

**MOLDURA:** livre minimo 29.08 < coberta maximo 48.92. As classes se
**SOBREPOEM em 19.8 pontos** — nenhum limiar as separa. Isso deixou de ser
projecao.

**CASAMENTO:** livre minimo (ver linha 4 abaixo) +0.619 > coberta maximo +0.236.
**Vao de 0.383, sem zona cinzenta.**

### 3. O portao proposto

    legivel = desvio >= 3.0  E  ( moldura >= 60.0  OU  casamento >= 0.40 )

O braco de moldura NAO SAI. Isso torna a mudanca **monotona**: um OR so
acrescenta aprovacao, nunca retira. Nada que hoje produz leitura para de
produzir — e a direcao do dano deste projeto e justamente a leitura que some.

### 4. Barra 100% VAZIA sobre terreno real (recortes so da parte vazia)

| fonte | largura | moldura | casamento |
|---|---|---|---|
| `escuro_cauda_vazia[:, 169:]` — terreno ESCURO | 22 px | 27.41 | **+0.619** |
| `quase_vazia_terreno_atras[:, 14:]` — terreno de DIA | 177 px | 77.33 | **+0.980** |

O widget desenha um brilho SEMI-TRANSPARENTE por cima do terreno: a estrutura de
linhas sobrevive a barra esvaziar, so perde amplitude. Por isso a correlacao
resiste onde o brilho absoluto nao resiste. Recortes ESTREITOS sao ruidosos
(terreno local domina): de dia, 21 px de cauda dao +0.218 e 177 px dao +0.980.
O recorte de producao tem 191 px, o regime largo.

### 5. Sensibilidade a deslocamento vertical — por que o casamento DESLIZA

Medido sobre `escuro_faixa` = `escuro_janela[739:767, 294:485]`, uma faixa de 28
linhas com 2 px de margem em cima e embaixo do recorte de MP. O deslocamento e
REAL — cada janela de 24 linhas sai de pixels de verdade, nada e inventado. O
offset 2 e **bit a bit identico** ao recorte alinhado, o que torna a fixture
auto-verificavel.

| offset na faixa | dy | moldura (portao de HOJE) | casamento (proposto) |
|---|---|---|---|
| 0 | -2 | 32.33 | **+0.964** |
| 1 | -1 | **20.41** | **+0.964** |
| 2 | 0 | 29.08 | **+0.964** |
| 3 | +1 | **12.64** | **+0.964** |
| 4 | +2 | 30.08 | **+0.964** |

O casamento e **constante ate a terceira casa** enquanto a moldura pula de 12.64
a 32.33 — caotica exatamente onde a outra e estavel.

A versao INGENUA do casamento (perfil de 24 comparado em posicao fixa, sem
deslizar) morre com UM pixel: cai de +0.972 para -0.179 em dy=-1, e para -0.020
em dy=+1. Seria trocar uma bomba de silencio por outra. O deslizamento de 20
valores dentro de um perfil de 24 compra exatamente ±2 px; em dy=±3 o casamento
cai para +0.376/+0.435 e o recorte volta a ser recusado, que e o comportamento
certo — a essa altura a calibracao esta errada de verdade.

### 6. O custo: `coberta_0` passa a ser LEGIVEL, e o dano esta LIMITADO

Varredura sobre pixels REAIS dos dois lados — `livre_0[:, :k]` colado no painel
de inventario real `coberta_1/2/3[:, k:]`. Coluna = pior caso das tres:

| k | leitura de HP | melhor casamento das 3 |
|---|---|---|
| 0 | 0.00% | +0.236 |
| 5 | 2.62% | +0.324 |
| 10 | 5.24% | +0.213 |
| 15 | 7.85% | +0.371 |
| **20** | **10.47%** | **+0.675** |
| 30 | 15.71% | +0.693 |
| 60 | 31.41% | +0.933 |
| 100 | 52.36% | +0.998 |

**O casamento sobe junto com a fracao VISIVEL da barra, e a leitura de HP e
exatamente essa fracao.** Um painel so passa no limiar 0.40 quando ja deixou 20
colunas de barra a mostra — leitura 10.47%, contra `fracao_hp_considerada_zero =
0.02`. **Folga de 5.2x. Um painel de inventario nao consegue produzir morte
falsa atraves deste portao.**

### 7. Escolha do limiar 0.40 — de onde vem

- coberta que le 0% (n=8, tela real), maximo: **+0.236** -> folga de **0.164**
- a livre mais magra medida (22 px, 100% vazia, terreno escuro): **+0.619** -> folga de **0.219**
- a livre de recorte inteiro mais magra: **+0.944** -> folga de 0.544
- ponto medio das duas classes: 0.4275. O limiar fica **abaixo** dele, de
  proposito: errar para cima recusa barra legitima, e recusar barra legitima e
  silencio na morte.
- varredura de painel: nada passa com leitura abaixo de 10.47%.

### 8. Constantes a embutir

`PERFIL_DE_REFERENCIA_DA_BARRA_PROPRIA` — media de cinza por linha de
`livre_0.png`, linhas 2 a 21 (20 valores, deixando 2 px de folga em cima e
embaixo para o deslizamento):

    72.81, 72.57, 72.31, 72.33, 59.71, 104.48, 85.23, 88.60, 88.44, 94.38,
    85.98, 87.73, 86.40, 89.79, 64.02, 72.60, 72.48, 72.69, 72.69, 72.38

`LINHAS_DO_PERFIL_PROPRIO = 24` (altura em que o nucleo foi medido)
`CASAMENTO_MINIMO_DO_PERFIL_PROPRIO = 0.40`

### 9. Pre-voo do impacto na suite — JA EXECUTADO

O portao proposto foi rodado contra a suite inteira por plugin, sem tocar no
repo. Resultado: **3 failed, 1122 passed, 2 skipped**. As tres falhas estao no
MESMO arquivo e sao TODAS sobre `coberta_0`:

1. `TestOInventarioNaoViraMorte::test_nenhum_recorte_coberto_produz_leitura[coberta_0]`
2. `TestAsOitoFixturesReaisNosDoisSentidos::test_coberta_pelo_inventario_e_ILEGIVEL[coberta_0]`
3. `TestOTripwireDoDesvioPadrao::test_o_desvio_SOZINHO_deixaria_a_coberta_passar` (ultima asercao)

**Zero dano colateral em qualquer outro arquivo de teste.** O executor sabe
exatamente o que vai quebrar antes de comecar.

### 10. O que NAO foi medido, e por que — a restricao honesta

Nenhuma amostra da barra de **HP PROPRIA** visivelmente baixa em terreno escuro
existe. A tentativa de 2026-08-26 gravou 90 s de farm e o HP nunca saiu de 100%
(`recordings/hp_baixo/` esta VAZIO — conferido). Toda a evidencia de terreno
escuro vem do widget de **MP** da mesma janela, no mesmo frame, 25 px abaixo.
O regime nunca observado continua sendo: recorte INTEIRO de 191 px, HP em 0%,
terreno escuro. As duas ancoras que o cercam sao +0.619 (22 px, escuro) e
+0.980 (177 px, dia). Isso vai para o TODO, nao para debaixo do tapete.

</measured>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Resgatar a evidencia perecivel e prender o defeito num teste VERMELHO</name>
  <precondition>`recordings/escuro_janela.png` existe no disco (1392x1720). Ele esta em `.gitignore` e e a UNICA gravacao de cena escura que existe. Se o arquivo nao estiver la, PARE e reporte: a evidencia sumiu e o plano nao pode ser executado.</precondition>
  <files>tests/fixtures/barra_propria/escuro_cauda_vazia.png, tests/fixtures/barra_propria/escuro_cheia.png, tests/fixtures/barra_propria/escuro_faixa.png, tests/test_inventario_por_cima_da_barra_propria.py</files>
  <behavior>
    - `escuro_cauda_vazia.png` mede moldura 29.08 e e declarada ILEGIVEL pelo portao de hoje — e ela e uma barra LEGITIMA. Este e o defeito.
    - `extrair(frame_solo("escuro_cauda_vazia"), calibracao).hp_proprio` deve ser um NUMERO. Hoje sai `None`.
    - `escuro_cheia.png` (HP 100% na mesma cena escura) mede moldura 86.42 e ja e legivel hoje — a testemunha de que a cena escura por si nao derruba nada; o que derruba e a CAUDA VAZIA.
    - A cauda 100% vazia `escuro_cauda_vazia[:, 169:]` mede MP 0.00% e moldura 27.41 — o recorte auto-verificavel: o teste afirma a propria premissa de que ali nao ha preenchimento nenhum.
    - `escuro_faixa.png` tem 28 linhas e `escuro_faixa[2:26]` e igual a `escuro_cauda_vazia` — a fixture carrega a prova do proprio alinhamento, e e o que a Task 2 usa para provar tolerancia a ±2 px sem inventar um unico pixel.
  </behavior>
  <action>
Extrair TRES fixtures de `recordings/escuro_janela.png`, que e gitignored e portanto a unica copia. Recortes exatos, em linhas e colunas do arquivo: `escuro_cheia.png` = linhas 716 a 740, colunas 294 a 485 (a regiao `hp_proprio` calibrada, HP em 100%); `escuro_cauda_vazia.png` = linhas 741 a 765, colunas 294 a 485 (o widget de MP, 25 px abaixo, 88.5% cheio, com a cauda mostrando terreno escuro); `escuro_faixa.png` = linhas 739 a 767, mesmas colunas — a mesma cauda vazia com 2 px de margem em cima e embaixo, que e o que permite provar tolerancia a desalinhamento sobre pixels reais em vez de pixels inventados. Gravar as tres em `tests/fixtures/barra_propria/` com `cv2.imwrite`; conferir que as duas primeiras sairam 24x191x3 e a faixa 28x191x3, e que `escuro_faixa[2:26]` e IGUAL a `escuro_cauda_vazia` — a faixa carrega a propria prova de alinhamento.

Escrever, em `tests/test_inventario_por_cima_da_barra_propria.py`, uma classe nova `TestOTerrenoEscuroNaoPodeCalarAMorte` com docstring explicando, com os numeros da secao 1 do plano, que as duas classes se sobrepoem NESTE ARQUIVO e nao em teoria. Ela afirma o comportamento DESEJADO, entao nasce VERMELHA — e a ordem e proposital, e a mesma das quicks anteriores deste repo (commit `test(...)` antes do `feat(...)`).

Asercoes da classe:
(1) `_moldura_da_barra_propria(recorte("escuro_cauda_vazia"))` cai dentro da faixa das cobertas, isto e, abaixo de `BRILHO_MINIMO_DA_MOLDURA_PROPRIA` — a prova de que o discriminador de brilho nao separa. Esta asercao passa desde ja e deve continuar passando depois: ela documenta a sobreposicao, nao o remedio.
(2) `barra_propria_legivel(recorte("escuro_cauda_vazia"))` e `True`. VERMELHA hoje.
(3) `extrair(frame_solo("escuro_cauda_vazia"), calibracao).hp_proprio is not None`. VERMELHA hoje. Usar o `frame_solo` que ja existe no arquivo, para atravessar `extrair` de verdade em vez de montar `Observacao` a mao.
(4) `barra_propria_legivel(recorte("escuro_cheia"))` e `True` — a testemunha; passa hoje e depois.
(5) a cauda 100% vazia, `recorte("escuro_cauda_vazia")[:, 169:]`, tem `medir_barra` com os limiares de MP igual a 0.0, e sua moldura fica abaixo do limiar. Afirmar os dois na mesma funcao: o primeiro prova que a derivacao do recorte esta certa (ali nao ha preenchimento), o segundo prova que o terreno escuro sozinho reprova no portao de hoje. A coluna 169 vem da medicao: 88.48% de 191 px termina o preenchimento em 169.

Nao tocar em `l2scanner/visao.py` nesta task. Nao alterar nenhum teste existente nesta task.
  </action>
  <verify>
    <automated>python -c "import cv2,sys; sys.path.insert(0,'.'); from l2scanner.visao import _moldura_da_barra_propria as m; d='tests/fixtures/barra_propria/'; a=cv2.imread(d+'escuro_cauda_vazia.png'); b=cv2.imread(d+'escuro_cheia.png'); f=cv2.imread(d+'escuro_faixa.png'); assert a.shape==(24,191,3) and b.shape==(24,191,3) and f.shape==(28,191,3), (a.shape,b.shape,f.shape); assert (f[2:26]==a).all(), 'a faixa nao esta alinhada com a cauda vazia'; print('cauda_vazia moldura', round(m(a),2), '| cheia moldura', round(m(b),2)); assert abs(m(a)-29.08)<0.05 and abs(m(b)-86.42)<0.05"</automated>
    <automated>python -m pytest "tests/test_inventario_por_cima_da_barra_propria.py::TestOTerrenoEscuroNaoPodeCalarAMorte" -q; test $? -eq 1 && echo "VERMELHO confirmado — o defeito esta preso no teste"</automated>
  </verify>
  <done>As tres fixtures existem em `tests/fixtures/barra_propria/`, com as formas certas, com `escuro_faixa[2:26]` igual a `escuro_cauda_vazia`, e conferindo os numeros medidos (29.08 e 86.42). A classe `TestOTerrenoEscuroNaoPodeCalarAMorte` existe e falha, e falha exatamente nas asercoes 2 e 3 — a barra legitima sobre terreno escuro sendo recusada. O `test $? -eq 1` do verify e proposital e nao e frouxo: pytest devolve 1 para "teste falhou" e 4 para "nao coletou nada", entao esquecer de escrever a classe REPROVA o verify em vez de passar por engano. Commit `test(quick-260827-fsk): ...` com fixtures e teste juntos.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Trocar o discriminador — casamento de perfil em OR com a moldura</name>
  <files>l2scanner/visao.py, tests/test_inventario_por_cima_da_barra_propria.py</files>
  <behavior>
    - `_casamento_do_perfil_proprio(escuro_cauda_vazia)` da +0.964; `(escuro_cheia)` da +0.944; `(livre_0)` da +1.000; `(quase_vazia_terreno_atras)` da +0.979.
    - `_casamento_do_perfil_proprio` das 8 cobertas que leem 0% fica em -0.059..+0.236 — todas abaixo de 0.40.
    - `_casamento_do_perfil_proprio(coberta_0)` da +0.999, e `coberta_0` passa a ser LEGIVEL lendo 86.91% — nunca perto de zero.
    - As 5 janelas de 24 linhas dentro de `escuro_faixa.png` (dy de -2 a +2) dao TODAS +0.964, enquanto a moldura das mesmas 5 varia de 12.64 a 32.33.
    - Um recorte uniforme (`np.full((8,120,3), 60)`) continua ILEGIVEL: perfil sem variancia devolve 0.0.
    - As 45 livres reais continuam legiveis, 45 de 45.
  </behavior>
  <action>
Em `l2scanner/visao.py`, ao lado das constantes de moldura, acrescentar `PERFIL_DE_REFERENCIA_DA_BARRA_PROPRIA` (os 20 valores da secao 8 do plano, como tupla de float), `LINHAS_DO_PERFIL_PROPRIO = 24` e `CASAMENTO_MINIMO_DO_PERFIL_PROPRIO = 0.40`. Documentar em comentario, com as tabelas medidas das secoes 2, 4, 6 e 7 do plano, de onde cada numero saiu e por que o limiar ficou ABAIXO do ponto medio das classes.

Implementar `_casamento_do_perfil_proprio(recorte) -> float`: converter para cinza, tirar a media por LINHA (`axis=1`) obtendo um perfil; se o perfil nao tiver `LINHAS_DO_PERFIL_PROPRIO` valores, reamostrar para esse comprimento com `np.interp`; entao deslizar a referencia de 20 valores sobre o perfil de 24 em todas as posicoes possiveis, calcular a correlacao de Pearson em cada uma e devolver o MAIOR. Quando qualquer um dos dois vetores nao tiver variancia, o denominador e zero e a funcao devolve 0.0 — nunca divide por zero e nunca aprova o degenerado.

Escrever na docstring da funcao as duas razoes de forma, que sao o miolo da tarefa e a coisa mais facil de "consertar" por engano depois:
  (a) e correlacao, e nao brilho, porque Pearson e cego a escala do cinza — e por isso a mesma estrutura le +0.964 num recorte cuja moldura despencou de 86.42 para 29.08. Nenhum limiar de brilho separa as classes nesse regime, e isso esta medido: livre minimo 29.08 CONTRA coberta maximo 48.92.
  (b) DESLIZA, e nao compara posicao fixa, porque a versao de posicao fixa cai de +0.972 para -0.179 com UM pixel de desalinhamento vertical — trocaria uma bomba de silencio por outra. O deslizamento de 20 dentro de 24 compra ±2 px, medido.

Alterar `barra_propria_legivel` para `desvio >= DESVIO_MINIMO_DA_BARRA_PROPRIA` E `(moldura >= BRILHO_MINIMO_DA_MOLDURA_PROPRIA OU casamento >= CASAMENTO_MINIMO_DO_PERFIL_PROPRIO)`. Registrar na docstring que a moldura PERMANECE de proposito, porque o OR torna a mudanca MONOTONA — so acrescenta aprovacao, nunca retira — e que num projeto cuja direcao de dano e a leitura que some, um portao novo nao pode ter poder de recusar nada. Preservar integralmente o paragrafo existente sobre a POLARIDADE INVERTIDA em relacao a `_bordas_da_barra_intactas`: ele continua valendo e continua sendo o detalhe mais facil de reabrir por engano.

Em `tests/test_inventario_por_cima_da_barra_propria.py`, os tres testes que o pre-voo (secao 9) apontou precisam ser reexpressos — nenhum deles apagado:
  - `test_nenhum_recorte_coberto_produz_leitura`: restringir a parametrizacao as 3 que leem 0%, e escrever em `COBERTAS_QUE_LIAM_ZERO` a razao medida. `coberta_0` sai desta lista.
  - `test_coberta_pelo_inventario_e_ILEGIVEL`: idem.
  - `test_o_desvio_SOZINHO_deixaria_a_coberta_passar`: as duas primeiras asercoes (desvio da coberta MAIOR que o da livre, e desvio sozinho aprovaria a coberta) continuam valendo e ficam. A terceira, que exigia `coberta_0` ILEGIVEL, passa a exigir o que agora e verdade e importa: que `coberta_2` — coberta e lendo 0% — siga recusada.

Acrescentar as classes novas, todas com o numero medido na mensagem de falha:
  - `TestOCustoMedidoDeAceitarACobertaParcial`: `coberta_0` e LEGIVEL, seu casamento e ~0.999, e sua leitura de HP e ~86.91% — longe de `Ajustes().fracao_hp_considerada_zero`. Mais a VARREDURA da secao 6 montada com pixels reais (`livre_0[:, :k]` concatenado com `coberta_1/2/3[:, k:]`): para todo k cuja leitura fique em ou abaixo do limiar de morte, o casamento tem que ficar ABAIXO de `CASAMENTO_MINIMO_DO_PERFIL_PROPRIO`. Este e o teste que prende a propriedade de seguranca inteira: painel de inventario nao consegue produzir morte falsa por este portao.
  - `TestOCasamentoTolera2pxDeDesalinhamento`: percorrer as 5 janelas de 24 linhas dentro de `escuro_faixa.png` (offsets 0 a 4, ou seja dy de -2 a +2 em torno do recorte alinhado) e exigir que TODAS sejam LEGIVEIS e que o casamento de todas fique acima do limiar. Nada de `np.roll`: rolar inventa linhas, e a faixa existe justamente para que cada deslocamento venha de pixels reais. No mesmo teste, afirmar o contraste que da sentido a mudanca — que a moldura das mesmas 5 janelas varia de ~12.6 a ~32.3, isto e, que o discriminador ANTIGO e caotico exatamente onde o novo e estavel. Fechar afirmando `escuro_faixa[2:26] == escuro_cauda_vazia`, para que o teste prove o proprio alinhamento em vez de confiar num indice escrito a mao.
  - `TestAsQuarentaECincoLivresContinuamLegiveis`: se `recordings/inv2/` existir, afirmar 45 de 45 legiveis; se nao existir, `pytest.skip` com a razao — `recordings/` e gitignored e nao esta garantido num clone limpo.

Nao acrescentar dependencia nenhuma. `pyproject.toml` fica fora do diff.
  </action>
  <verify>
    <automated>python -m pytest tests/test_inventario_por_cima_da_barra_propria.py -q</automated>
    <automated>python -m pytest tests/ -q 2>&1 | tail -3</automated>
    <automated>python -c "import sys; sys.path.insert(0,'.'); import cv2; from l2scanner.visao import barra_propria_legivel, _casamento_do_perfil_proprio as c; r=lambda n: cv2.imread('tests/fixtures/barra_propria/'+n+'.png'); [print(n, round(c(r(n)),3), barra_propria_legivel(r(n))) for n in ['escuro_cauda_vazia','escuro_cheia','livre_0','quase_vazia_terreno_atras','coberta_0','coberta_1','coberta_2','coberta_3']]; assert barra_propria_legivel(r('escuro_cauda_vazia')); assert not barra_propria_legivel(r('coberta_1')) and not barra_propria_legivel(r('coberta_2')) and not barra_propria_legivel(r('coberta_3'))"</automated>
    <automated>python -c "import sys; sys.path.insert(0,'.'); import numpy as np; from l2scanner.visao import barra_propria_legivel; assert not barra_propria_legivel(np.full((8,120,3),60,dtype=np.uint8)); print('degenerado uniforme segue ILEGIVEL')"</automated>
    <automated>python -c "import cv2,sys; sys.path.insert(0,'.'); from l2scanner.visao import barra_propria_legivel as ok, _casamento_do_perfil_proprio as c, _moldura_da_barra_propria as m; f=cv2.imread('tests/fixtures/barra_propria/escuro_faixa.png'); j=[f[o:o+24] for o in range(5)]; print('casamento', [round(c(x),3) for x in j]); print('moldura  ', [round(m(x),2) for x in j]); assert all(ok(x) for x in j), 'desalinhamento de ate 2 px derruba a leitura'"</automated>
    <automated>git diff --name-only | grep -q pyproject.toml && echo "FALHOU: dependencia nova" && exit 1 || echo "sem dependencia nova"</automated>
  </verify>
  <done>`python -m pytest tests/ -q` sai com pelo menos `1125 passed, 2 skipped` e com MAIS testes do que o baseline. `escuro_cauda_vazia` e LEGIVEL e produz `hp_proprio` numerico por `extrair`. As 3 cobertas que leem 0% seguem ILEGIVEIS. A varredura de painel passa em todo k. `pyproject.toml` fora do diff. Commits `feat(quick-260827-fsk): ...` para `visao.py` e `test(quick-260827-fsk): ...` para os testes.</done>
</task>

<task type="auto">
  <name>Task 3: Registrar o que ficou de pe — o TODO continua ABERTO</name>
  <files>.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md, .planning/STATE.md</files>
  <action>
Atualizar o TODO **sem move-lo para `done/`**. Ele permanece em
`.planning/todos/pending/` porque o criterio de aceite que ele mesmo escreveu —
uma amostra real da barra de HP PROPRIA visivelmente baixa em terreno escuro —
continua sem existir.

Acrescentar uma secao datada de 2026-08-27 dizendo, em ordem:

(1) **O que virou fato.** A projecao de "~32" foi substituida por uma medicao:
29.08, na regiao do widget de MP de `recordings/escuro_janela.png`, com a barra
apenas 88.5% cheia. O regime nao precisa de barra vazia — 11.5% de cauda basta.
E a amostra foi resgatada para `tests/fixtures/barra_propria/escuro_cauda_vazia.png`,
porque `recordings/` esta no `.gitignore` e ela era a unica copia.

(2) **O que mudou no produto.** O discriminador passou a ser o casamento do
perfil de linhas, invariante a brilho, em OR com a moldura. Registrar a tabela
das duas classes contra os dois discriminadores (secao 2 do plano) e o limiar
0.40 com as duas folgas (0.164 para o lado das cobertas, 0.219 para o lado das
livres).

(3) **A pista do canto esquerdo, resolvida.** Registrar que o canto esquerdo
citado no TODO nao foi adotado, e a razao MEDIDA, nao de gosto: ele casa apenas
enquanto as primeiras colunas ainda tem preenchimento, entao com a barra em 0% —
exatamente o frame da morte — ele nao tem o que casar. O casamento do perfil de
linhas nao tem essa fronteira porque o widget desenha um brilho semi-transparente
sobre o terreno: medido +0.980 num recorte de 177 px 100% vazio.

(4) **O que AINDA falta, e por que.** O regime nunca observado continua sendo o
recorte INTEIRO de 191 px com HP em 0% sobre terreno escuro. Toda a evidencia de
terreno escuro vem do widget de MP, no mesmo frame, 25 px abaixo — mesmo widget,
mesma janela, mas nao e a barra de HP. As duas ancoras medidas que cercam o
regime: +0.619 (22 px, escuro) e +0.980 (177 px, dia), ambas acima do limiar
0.40. Repetir que `recordings/hp_baixo/` esta vazio e por que.

(5) **O sinal de que a pendencia virou defeito**, atualizado: agora seria uma
sequencia de barra propria ILEGIVEL em combate escuro APESAR do portao novo — o
que apontaria para o regime de 0% que ninguem mediu, e nao mais para o brilho.

(6) **O custo aceito**, com numero: `coberta_0` passou de ILEGIVEL a LEGIVEL
lendo 86.91%, e a varredura de painel mostra que nada passa no limiar com
leitura abaixo de 10.47%, contra um limiar de morte de 2%.

Atualizar o front-matter `files:` do TODO para citar os arquivos que agora
importam, incluindo as fixtures novas.

Em `.planning/STATE.md`: manter a linha do todo em `## Pending Todos` (ele segue
aberto, severidade major), acrescentar a linha da quick em `## Quick Tasks
Completed` no estilo das anteriores — o que foi medido, o que mudou, o que ficou
aberto, e a contagem da suite nas duas pontas — e atualizar
`## Session Continuity`.
  </action>
  <verify>
    <automated>test -f ".planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md" && echo "TODO segue em pending/"</automated>
    <automated>test ! -f ".planning/todos/done/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md" && echo "TODO nao foi fechado"</automated>
    <automated>python -c "import io; t=io.open('.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md',encoding='utf-8').read(); [__import__('sys').exit('FALTA: '+n) for n in ['2026-08-27','29.08','0.40','escuro_cauda_vazia'] if n not in t]; print('o TODO registra a medicao, o limiar e a fixture')"</automated>
    <automated>python -c "import io; s=io.open('.planning/STATE.md',encoding='utf-8').read(); assert '260827-fsk' in s, 'STATE nao cita a quick'; assert 'moldura-da-barra-propria-em-terreno-escuro' in s, 'STATE perdeu o todo aberto'; print('STATE atualizado e o todo segue listado')"</automated>
    <automated>python -m pytest tests/ -q 2>&1 | tail -2</automated>
  </verify>
  <done>O TODO continua em `pending/`, datado de 2026-08-27, com os seis registros acima e o `files:` atualizado. STATE.md cita a quick em `Quick Tasks Completed`, mantem o todo em `Pending Todos` e tem a continuidade de sessao atualizada. Commit `docs(quick-260827-fsk): ...`.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pixels da tela do jogo -> `barra_propria_legivel` | entrada NAO CONFIAVEL: qualquer janela do jogo, qualquer terreno, qualquer overlay pode estar naqueles 191x24 px |
| `recordings/` (gitignored) -> `tests/fixtures/` (versionado) | promocao de artefato local nao versionado para evidencia permanente |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-fsk-01 | Denial of Service | `barra_propria_legivel` recusando recorte legitimo | critical | mitigate | E o defeito em si: recusa -> `hp_proprio=None` -> rastreador congela -> morte calada. Mitigado por CONSTRUCAO tornando a mudanca monotona (o braco de moldura fica no OR, entao nada que hoje passa deixa de passar) e por MEDICAO: 45/45 livres reais legiveis, mais as fixtures de terreno escuro. Teste `TestOTerrenoEscuroNaoPodeCalarAMorte`. |
| T-fsk-02 | Spoofing | painel de inventario se passando por barra legivel | high | mitigate | Um overlay que passe no portao injeta HP inventado e, no limite, morte falsa. Mitigado pelo casamento de perfil: 8/8 cobertas reais que leem 0% recusadas (max +0.236 contra limiar 0.40). LIMITE PROVADO pela varredura sobre pixels reais: nenhum composto passa com leitura abaixo de 10.47%, contra `fracao_hp_considerada_zero = 0.02` — folga de 5.2x. Teste `TestOCustoMedidoDeAceitarACobertaParcial`. |
| T-fsk-03 | Tampering | `PERFIL_DE_REFERENCIA_DA_BARRA_PROPRIA` e o limiar 0.40 | medium | mitigate | Constantes ajustadas no escuro reabrem o defeito em silencio. Mitigado prendendo as duas classes em testes com o numero medido na mensagem de falha, e mantendo o tripwire de `coberta_2` no lugar do de `coberta_0`. |
| T-fsk-04 | Tampering | fixtures PNG novas | low | accept | Sao arquivos versionados; qualquer alteracao aparece no diff e derruba as asercoes de moldura 29.08 / 86.42 da Task 1. |
| T-fsk-05 | Information Disclosure | fixtures resgatadas de captura de tela real | low | accept | Recortes de 191x24 px de barras de HP/MP. Nao contem nome de conta, telefone, token nem texto de chat. |
| T-fsk-SC | Tampering | instalacao de pacotes (npm/pip/cargo) | n/a | accept | Zero instalacao: `numpy` e `cv2` ja sao importados por `l2scanner/visao.py`. Nao ha task de install, entao o portao de legitimidade de pacote nao se aplica. `pyproject.toml` fora do diff, com verificacao automatizada na Task 2. |
</threat_model>

<verification>
1. `python -m pytest tests/ -q` sai com pelo menos `1125 passed, 2 skipped` e com MAIS testes do que o baseline medido em 2026-08-27 (1125 passed, 2 skipped).
2. `barra_propria_legivel` aprova `escuro_cauda_vazia.png` (moldura 29.08) e `extrair` devolve `hp_proprio` numerico para ela.
3. As 3 fixtures de coberta que leem 0% seguem ILEGIVEIS; `coberta_0` passa a LEGIVEL lendo ~86.91%.
4. A varredura de painel com pixels reais nao produz nenhum caso com casamento acima do limiar e leitura em ou abaixo do limiar de morte.
5. Recorte uniforme `np.full((8,120,3), 60)` segue ILEGIVEL.
6. `pyproject.toml` fora do diff.
7. O TODO segue em `.planning/todos/pending/` e registra a medicao, o limiar, a fixture e o que ainda falta.
</verification>

<success_criteria>
- A barra propria legitima sobre terreno escuro volta a ser lida — medido na fixture `escuro_cauda_vazia.png`, que hoje e recusada.
- As 27 mortes falsas do inventario continuam suprimidas: 8 de 8 cobertas que leem 0% seguem recusadas.
- A mudanca e monotona: 45 de 45 livres reais continuam legiveis, e nenhum recorte que hoje produz leitura para de produzir.
- Todo limiar do diff vem de uma medicao registrada neste plano e repetida em comentario no codigo.
- O TODO permanece ABERTO, atualizado com o que mudou e com o unico regime que continua dependendo de captura em campo.
</success_criteria>

<output>
Create `.planning/quick/260827-fsk-trocar-o-discriminador-da-legibilidade-d/260827-fsk-SUMMARY.md` when done.

O SUMMARY precisa dizer, explicitamente e com numero: (a) que a projecao de "~32"
virou uma medicao de 29.08 numa fixture que agora esta versionada; (b) que o
discriminador trocado e invariante a brilho e por que isso e a diferenca entre
separar e nao separar as classes; (c) que `coberta_0` foi o preco, com o limite
de 10.47% que impede morte falsa; e (d) que o TODO NAO FECHOU — que continua
faltando a barra de HP propria em nivel baixo sobre terreno escuro, e que toda a
evidencia de escuro veio do widget de MP do mesmo frame.
</output>
