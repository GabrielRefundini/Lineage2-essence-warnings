---
phase: quick-260827-fsk
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - l2scanner/visao.py
  - l2scanner/__main__.py
  - tests/fixtures/barra_propria/escuro_cauda_vazia.png
  - tests/fixtures/barra_propria/escuro_cheia.png
  - tests/fixtures/barra_propria/escuro_faixa.png
  - tests/test_inventario_por_cima_da_barra_propria.py
  - .planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md
  - .planning/STATE.md
autonomous: true
requirements: [QUICK-260827-fsk]

estimate:
  tokens: 80000
  raw_tokens: 60000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "O DEFEITO VIROU FIXTURE. `tests/fixtures/barra_propria/escuro_cauda_vazia.png` e captura REAL da tela do usuario em cena escura: a barra do proprio personagem, 88.5% cheia, com a cauda vazia mostrando terreno escuro. Mede moldura 29.08 — DENTRO da faixa das cobertas (28.00..48.92) — e o portao de hoje a declara ILEGIVEL, entao o console e o log nao mostram NADA da barra propria durante a descida inteira."
    - "NENHUM ALERTA MUDA, E ISSO E PROVAVEL PELO DIFF: `l2scanner/rastreador.py` fica FORA do diff e `Observacao.hp_proprio` sai byte a byte como hoje em todas as 8 amostras. A suite inteira passa SEM UM UNICO teste mudando de veredito — pre-voo: 1125 passed, 2 skipped, zero falhas."
    - "A DESCIDA VOLTA A SER MOSTRADA. Um campo novo `hp_proprio_aparente` carrega a leitura que o portao de hoje descarta, e o console e o log passam a exibi-la MARCADA COMO APARENTE. Medido: `escuro_cauda_vazia` sai `hp_proprio=None` / `aparente=0.8848` — hoje as duas seriam nada."
    - "A LEITURA APARENTE NUNCA ENTRA NA MAQUINA DE ESTADO, e por construcao: ela vive num campo que `rastreador.py` nao le. Os TRES consumidores de `hp_proprio` — a avaliacao de party (linha 454), o caminho solo (linha 496) e a injecao do proprio como pseudo-membro (linha 833) — continuam vendo exatamente o que veem hoje."
    - "AS 27 MORTES FALSAS CONTINUAM SUPRIMIDAS e nenhuma classe nova de alerta falso e criada. Teste que carrega `coberta_0` ATE DENTRO do `Rastreador` e exige lista de eventos VAZIA de QUALQUER tipo — nao so de morte — em party e em solo, inclusive depois de uma morte real."
    - "A leitura aparente so existe ACIMA de `LEITURA_MINIMA_PARA_O_CASAMENTO = 0.05`, 2.5x o `fracao_hp_considerada_zero = 0.02`. Verificado por exaustao: 2304 compostos nas DUAS direcoes de oclusao, 1733 no regime de morte, ZERO aceitos."
    - "O discriminador e INVARIANTE A BRILHO (+0.964 num recorte cuja moldura despencou para 29.08) e TOLERA ±2 px de desalinhamento vertical (a versao de posicao fixa cai de +0.972 para -0.179 com UM pixel)."
    - "O QUE NAO FECHA ESTA DITO COM NUMERO. No regime de leitura zero sobre terreno escuro as classes se INTERCALAM: barra vazia genuina da +0.627 e o mesmo recorte com 5 colunas cobertas a esquerda da +0.645 — a oclusao pontua MAIS ALTO. Nenhum limiar as separa, entao a MORTE em cena escura continua sem remedio, e esta tarefa nao finge o contrario."
    - "DOIS DEFEITOS PRE-EXISTENTES FORAM ENCONTRADOS E REGISTRADOS, nao herdados em silencio: (i) `coberta_2` com o painel a esquerda le 0.0000 e ja passa HOJE pelo braco de moldura (64.00); (ii) `hp_proprio` tem TRES consumidores no rastreador e a suite nunca carregou um recorte coberto ate nenhum deles — foi por isso que o plan-check, e nao a suite, achou o risco."
    - "A suite nao regrediu: `python -m pytest tests/ -q` sai com codigo 0 e `--collect-only` conta MAIS que o baseline de 1127. A contagem de `skipped` NAO e afirmada como constante, porque as guardas novas de `pytest.skip` a fazem crescer num clone limpo."
    - "Zero dependencia nova: `numpy` e `cv2` ja sao usados em `l2scanner/visao.py`, e `pyproject.toml` nao muda desde o commit do plano (`9d5533e`)."
  artifacts:
    - "l2scanner/visao.py com `PERFIL_DE_REFERENCIA_DA_BARRA_PROPRIA`, `CASAMENTO_MINIMO_DO_PERFIL_PROPRIO`, `LEITURA_MINIMA_PARA_O_CASAMENTO`, `_casamento_do_perfil_proprio`, `_braco_do_casamento` e o campo `Observacao.hp_proprio_aparente`"
    - "l2scanner/__main__.py com a linha do console mostrando a leitura APARENTE marcada como tal"
    - "tests/fixtures/barra_propria/escuro_cauda_vazia.png, escuro_cheia.png (191x24) e escuro_faixa.png (191x28), resgatadas de recordings/ que e gitignored"
    - "tests/test_inventario_por_cima_da_barra_propria.py com a classe de terreno escuro, a varredura EXAUSTIVA nas duas direcoes, o teste que atravessa o Rastreador e a caracterizacao dos dois defeitos pre-existentes"
    - ".planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md atualizado e AINDA EM pending/"
  key_links:
    - "`hp_proprio_aparente` (visao.py) -> `__main__.py:395` (console e log). E o UNICO consumidor, e e o que torna a mudanca inofensiva para os alertas."
    - "`hp_proprio` -> `rastreador.py` linhas 454, 496 e 833 — TRES consumidores, todos intocados. A linha 833 injeta o proprio como pseudo-membro e e a que o pre-voo mostrou capaz de RESETAR uma contagem de morte em andamento."
    - "`LEITURA_MINIMA_PARA_O_CASAMENTO` (0.05) -> `Ajustes.fracao_hp_considerada_zero` (0.02): acoplamento entre camadas, preso por tripwire."
    - "`recordings/escuro_janela.png` -> as tres fixtures novas. `recordings/` esta no `.gitignore`: esta e a UNICA evidencia de cena escura que existe e ela esta FORA do controle de versao."
---

<objective>
Fazer o console e o log pararem de nao mostrar NADA da barra propria durante um
combate em cena escura — sem tocar em uma linha do `rastreador.py` e sem mudar
um alerta sequer.

Purpose: hoje, em cena escura, a barra propria e declarada ILEGIVEL assim que
qualquer cauda vazia aparece — medido com a barra ainda 88.5% cheia. Some do
console, some do log, e some justamente da unica ferramenta de depuracao
pos-farm que o projeto tem. Sem log nao ha como capturar a amostra que fecharia
a pendencia.

Output: um campo `hp_proprio_aparente` alimentado por um discriminador
invariante a brilho, exibido MARCADO COMO APARENTE, e que a maquina de estado
nao le. Mais o registro honesto de que a MORTE em cena escura continua sem
remedio, e de dois defeitos pre-existentes encontrados no caminho.
</objective>

<revisao>
## Revisao 3 — a promessa encolheu pela terceira vez, e a terceira e a certa

Tres rodadas de plan-check, tres blockers, todos procedentes. O registro fica
aqui porque a forma do erro se repetiu e e ela que importa: **as tres versoes
mediram o portao e nao mediram o que fica DEPOIS dele.**

| rodada | promessa | o que a medicao derrubou |
|---|---|---|
| 1 | "a barra vazia legitima em terreno escuro volta a ser lida" | so mediu oclusao pela DIREITA; pela esquerda a leitura zera e o casamento da +1.000 -> morte falsa |
| 2 | "a descida de HP volta a ser lida" | so contabilizou o custo contra o limiar de MORTE; contra a maquina inteira produz `VOCE_SEM_PARTY` falso E `RESSUSCITOU` falso |
| **3** | **"a descida volta a ser MOSTRADA; nenhum alerta muda"** | — |

**O que a rodada 3 mediu que as outras nao:** `hp_proprio` tem **TRES**
consumidores no `rastreador.py` (linhas 454, 496 e 833), nao um. A linha 833
injeta o proprio personagem como pseudo-membro e passa pelo mesmo debounce dos
outros — e e por ela que uma leitura de 0.8691 vinda do inventario **reseta uma
contagem de morte em andamento** (medido: morte anunciada no tick 18 passa para
o tick 20). Nenhuma das duas versoes anteriores tinha olhado para essa linha.

**A conclusao que fecha o assunto:** o braco novo nao consegue produzir uma
leitura CONFIAVEL, porque tudo que ele certifica pode ser um recorte
parcialmente ocluido — `coberta_0` (moldura 48.00, casamento 0.999, leitura
0.8691) e `escuro_cauda_vazia` (29.08 / 0.964 / 0.8848) so se ordenam pela
moldura, e nessa ordem a classe coberta (28.00..48.92) fica dos DOIS lados do
unico ponto legitimo que existe. Uma leitura que pode estar ocluida nao pode
alimentar alerta nenhum. Entao ela nao alimenta: vai para um campo separado que
so o console le.

**O que sobreviveu das rodadas anteriores, porque o checker confirmou:** o
tracer resgatando a evidencia gitignored antes que algo dependa dela;
`escuro_faixa[2:26]` provando o proprio alinhamento; o `test $? -eq 1`
distinguindo "falhou" de "nao coletou"; o portao de leitura de 0.05 verificado
por exaustao; a invariancia a brilho; e o TODO seguindo em `pending/`.
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

## Tudo abaixo foi MEDIDO em 2026-08-27 sobre pixels reais deste repositorio.

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

MOLDURA: livre minimo 29.08 **abaixo** de coberta maximo 48.92 — sobreposicao de
19.8 pontos, nenhum limiar de brilho separa.

### 3. Por que a leitura do braco novo NAO PODE ser confiavel

`coberta_0` e `escuro_cauda_vazia` so se ordenam pela moldura — 48.00 contra
29.08 — e nessa ordem a classe coberta fica dos **dois lados** do unico ponto
legitimo que existe: `coberta_2` da 28.00 e `coberta_3` da 29.00, **abaixo** dos
29.08 da barra legitima. Uma banda de moldura seria um limiar ajustado entre
n=1 e n=1, com a classe errada dos dois lados, falhando na direcao do SILENCIO.
Por isso a leitura do braco novo e tratada como APARENTE, e nao como um
`hp_proprio` mais permissivo.

### 4. A COLISAO no regime de morte (leitura = 0, terreno ESCURO)

| recorte | leitura | casamento |
|---|---|---|
| **barra vazia GENUINA, terreno escuro** | 0.000 | **+0.627** |
| painel cobrindo 3 col a esquerda (c1/c2/c3) | 0.000 | +0.624 / +0.618 / **+0.642** |
| painel cobrindo 5 col a esquerda (c1/c2/c3) | 0.000 | +0.622 / +0.619 / **+0.645** |
| painel cobrindo 10 col a esquerda (c1/c2/c3) | 0.000 | +0.529 / +0.473 / **+0.637** |

**A oclusao pontua MAIS ALTO que a genuina: +0.645 contra +0.627.** As classes
nao se sobrepoem — elas se INTERCALAM. O motivo e estrutural: cobrir 5 de 191
colunas quase nao move a media de cada linha, e Pearson e cego a escala.
**Aceitar a barra vazia legitima em terreno escuro e recusar o painel que le
zero NAO PODEM coexistir com os dados que existem.**

### 5. A varredura de painel nas DUAS direcoes

`medir_barra` mede a corrida inicial DA ESQUERDA: cobrir a direita *subestima* a
leitura, cobrir a esquerda a **zera**.

**5a — painel a DIREITA (`livre_0[:, :k]` + `coberta[:, k:]`), leitura = k/191:**

| k | leitura | pior casamento das 3 |
|---|---|---|
| 5 | 2.62% | +0.324 |
| 15 | 7.85% | +0.371 |
| 20 | 10.47% | +0.675 |
| 60 | 31.41% | +0.933 |

**5b — painel a ESQUERDA (`coberta[:, :k]` + `livre_0[:, k:]`), leitura 0.0000:**

| k coberto | moldura c1 / c2 / c3 | casamento c1 / c2 / c3 |
|---|---|---|
| 5 | 48.92 / **64.00** / 55.42 | +1.000 / +1.000 / +0.999 |
| 20 | 48.92 / **64.00** / 55.42 | +0.956 / +0.972 / +0.967 |
| 60 | 48.92 / **64.00** / 55.42 | +0.573 / +0.938 / +0.723 |

### 6. O CUSTO CONTRA A MAQUINA DE ESTADO — o que a rodada 2 nao mediu

`hp_proprio` tem **TRES** consumidores no `rastreador.py`:

| linha | consumidor | o que uma leitura de 0.8691 vinda do inventario faz |
|---|---|---|
| 454 | `_avaliar_se_voce_esta_em_party` | o portao de cegueira da linha 643 so congela em leitura ZERADA; 0.8691 nao congela, entao conta "sem party" -> **`VOCE_SEM_PARTY` falso** |
| 496 | `_avaliar_so_o_proprio` (solo) | `morto_agora` vira False estando MORTO -> **`RESSUSCITOU` falso**, inclusive em `--solo` |
| 833 | injeta o proprio como pseudo-membro | mesmo debounce dos outros -> **reseta contagem de morte em andamento** |

Simulado com `Ajustes()` de producao (`confirmacoes_para_voce_sem_party = 8`,
`confirmacoes_para_morte = 3`):

| cenario | HOJE (`hp_proprio=None`) | se a leitura entrasse na maquina |
|---|---|---|
| quente com party, inventario 30 ticks | nenhum evento | `voce_sem_party` no tick 27 |
| morre, depois abre o inventario | `morreu` (22) | `morreu` (22), **`ressuscitou` (34)**, **`voce_sem_party` (37)** |
| SOLO: morre, depois abre o inventario | `morreu` (22) | `morreu` (22), **`ressuscitou` (34)** |
| morrendo (2 de 3), abre e fecha o inventario | `morreu` no tick **18** | `morreu` no tick **20** (contagem resetada) |

**Duas classes de alerta falso e um atraso de morte** — e a `ressuscitou` falsa e
literalmente metade do defeito que a quick `260826-dxm` pagou para matar (27
mortes + 27 ressurreicoes). O usuario abre o inventario o tempo todo: nao e raro,
e frequente.

### 7. O desenho escolhido, e por que ele custa menos que a alternativa

    hp_proprio            = INTOCADO (so o portao de moldura, como hoje)
    hp_proprio_aparente   = leitura quando  desvio >= 3.0
                                       E  o portao de hoje RECUSOU
                                       E  leitura > 0.05
                                       E  casamento >= 0.40

O campo aparente e lido **so pelo console/log** (`__main__.py:395`).
`rastreador.py` fica FORA do diff — a seguranca nao vem de guardas novas, vem de
a leitura nao existir para a maquina de estado.

**Comparacao medida das duas saidas que o check pediu:**

| remedio | custo medido | veredito |
|---|---|---|
| (A) recusar a `coberta_0` no portao | exige banda de moldura entre 29.08 e 48.00: limiar entre n=1 e n=1, com `coberta_2` (28.00) e `coberta_3` (29.00) **abaixo** do ponto legitimo. Falha na direcao do SILENCIO | rejeitado |
| (B) aceitar e ajustar o portao de cegueira do rastreador | 1 campo + **3** guardas em `rastreador.py`, a funcao mais critica do projeto; e para preservar o console ainda exigiria cirurgia na injecao de pseudo-membro da linha 833 | rejeitado |
| **(C) leitura APARENTE, `rastreador.py` fora do diff** | 1 campo + ~6 linhas em `extrair` + 1 ramo de console. **Pre-voo: 1125 passed, 2 skipped, ZERO testes mudam de veredito** | **escolhido** |

Verificacao do desenho (C) por `extrair`, com a calibracao apontada para as
cores do widget de cada fixture:

| amostra | `hp_proprio` | `hp_proprio_aparente` |
|---|---|---|
| `escuro_cauda_vazia` (88.5%, escuro) | None | **0.8848** |
| `escuro_cheia` (100%, escuro) | 1.0000 | None |
| `coberta_0` (inventario) | None | 0.8691 |
| `coberta_1` / `_2` / `_3` (leem 0%) | None | **None** |
| `livre_0` (dia, 100%) | 1.0000 | None |
| `quase_vazia` (dia, 6.8%) | 0.0681 | None |

`hp_proprio` sai identico a hoje nas 8. O aparente so aparece onde hoje nao ha
absolutamente nada.

### 8. O portao de leitura de 0.05, verificado por exaustao

- `Ajustes().fracao_hp_considerada_zero = 0.02`; 0.05 e **2.5x** isso, ~9.5 de
  191 colunas.
- **2304 compostos**: 4 paineis REAIS (`coberta_0..3`) x 3 preenchimentos de
  direita x k de 0 a 191, nas duas direcoes de oclusao. **1733 leem em ou abaixo
  do limiar de morte e ZERO produzem leitura aparente.** Custo: 0.06 s.
- **Honestidade sobre a amostra:** dos 3 preenchimentos de direita, DOIS sao
  recortes reais de largura inteira (`livre_0`, `quase_vazia_terreno_atras`) e o
  TERCEIRO e a cauda 100% vazia real de terreno escuro
  (`escuro_cauda_vazia[:, 169:]`, 22 colunas) **ladrilhada** ate 191 colunas —
  pixels reais, geometria sintetica. Os 4 paineis sao reais em todos os casos.

### 9. Limiar do casamento = 0.40

- coberta TOTAL (n=8, tela real), maximo: +0.236 -> folga de 0.164
- as duas genuinas de cena escura: +0.944 e +0.964 -> folga de 0.544
- ponto medio 0.590; o limiar fica **abaixo** dele porque errar para cima recusa
  barra legitima.

### 10. Tolerancia a deslocamento vertical

| dy | moldura (portao de HOJE) | casamento |
|---|---|---|
| -4 | 37.67 | +0.293 |
| -3 | 35.04 | +0.293 |
| **-2 a +2** | **12.64 .. 32.33** | **+0.964 (constante)** |
| +3 | 30.29 | +0.364 |
| +4 | 30.58 | +0.340 |

Constante ate a terceira casa em ±2 px, enquanto a moldura pula de 12.64 a
32.33. Em ±3 px cai para +0.293/+0.364, ambos abaixo de 0.40. A versao de
posicao FIXA cai de +0.972 para -0.179 com UM pixel — por isso o casamento
desliza.

### 11. Pre-voo do impacto na suite — JA EXECUTADO com o desenho (C)

`1125 passed, 2 skipped, 0 failed`. **Nenhum teste existente muda de veredito**,
porque `hp_proprio` nao muda. Baseline a bater: `1127 tests collected`.

### 12. O que NAO fecha, e o que falta

1. **Nenhuma amostra de HP PROPRIO em nivel baixo, em terreno escuro.**
   `recordings/hp_baixo/` esta VAZIO — conferido. Toda a evidencia de terreno
   escuro vem do widget de MP do mesmo frame, 25 px abaixo.
2. **A MORTE em cena escura continua sem remedio** — secao 4. Nenhum alerta e
   restaurado por esta tarefa. O que poderia fechar: (a) uma amostra real das
   duas classes; (b) um sinal TEMPORAL no rastreador — "estava caindo e ficou
   cega" nao e "ficou cega com o inventario aberto" —, que e mudanca de camada
   com risco proprio de falso positivo.
3. **Defeito pre-existente do braco de moldura:** `coberta_2` com o painel a
   esquerda le 0.0000 com moldura 64.00 e ja e aceito HOJE. Nao e criado nem
   fechado aqui, e nao e fechavel por portao de leitura, porque o braco de
   moldura PRECISA certificar leitura zero — e assim que a morte e anunciada em
   terreno de dia. Candidato medido: contiguidade do preenchimento (`sobra` = 0
   nas 51 amostras genuinas, 11..186 nos compostos de oclusao a esquerda), que so
   pode entrar depois de medida contra TERRENO VERMELHO, porque lava e chao
   avermelhado podem gerar colunas cheias espurias e o modo de falha dela e
   SILENCIO.
4. **Lacuna de cobertura pre-existente:** nenhum teste carregava um recorte
   coberto ate DENTRO do `Rastreador`. O unico que chega la
   (`test_trinta_frames_de_inventario_aberto_nao_emitem_morte`) FILTRA os eventos
   por `MORREU`, entao um `VOCE_SEM_PARTY` ou um `RESSUSCITOU` falso passaria
   despercebido. Foi por isso que o risco da secao 6 apareceu no plan-check e nao
   na suite. Esta tarefa fecha a lacuna.
5. **±2 px e a tolerancia inteira**, sem rede alem dela.

### 13. Constantes a embutir

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
    - `escuro_cauda_vazia.png` mede moldura 29.08 e e recusada pelo portao de hoje — e e uma barra LEGITIMA, 88.5% cheia. Este e o defeito.
    - Ponta a ponta por `extrair`, com a calibracao apontada para as cores do widget da fixture: `hp_proprio` sai `None` hoje E DEPOIS — e isso e proposital. O que muda e `hp_proprio_aparente`, que hoje nem existe e depois sai `0.8848`.
    - `escuro_cheia.png` (HP 100%, mesma cena escura) mede moldura 86.42 e ja e legivel hoje — a testemunha de que a cena escura por si nao derruba nada; o que derruba e a CAUDA VAZIA.
    - `escuro_faixa.png` tem 28 linhas e `escuro_faixa[2:26]` e igual a `escuro_cauda_vazia` — a fixture carrega a prova do proprio alinhamento.
  </behavior>
  <action>
Extrair TRES fixtures de `recordings/escuro_janela.png`, que e gitignored e portanto a unica copia. Recortes exatos, em linhas e colunas do arquivo: `escuro_cheia.png` = linhas 716 a 740, colunas 294 a 485 (a regiao `hp_proprio` calibrada, HP em 100%); `escuro_cauda_vazia.png` = linhas 741 a 765, mesmas colunas (o widget de MP, 25 px abaixo, 88.5% cheio, com a cauda mostrando terreno escuro); `escuro_faixa.png` = linhas 739 a 767, mesmas colunas (a mesma cauda vazia com 2 px de margem em cima e embaixo, que e o que permite provar tolerancia a desalinhamento sobre pixels reais). Gravar as tres em `tests/fixtures/barra_propria/` com `cv2.imwrite`; conferir 24x191x3, 24x191x3 e 28x191x3, e que `escuro_faixa[2:26]` e igual a `escuro_cauda_vazia`.

Escrever, em `tests/test_inventario_por_cima_da_barra_propria.py`, a classe `TestOTerrenoEscuroSomeDoConsole`, com docstring trazendo os numeros da secao 1 e dizendo que as duas classes se sobrepoem NESTE ARQUIVO e nao em teoria. Ela afirma o comportamento DESEJADO, entao nasce VERMELHA — ordem proposital, a mesma das quicks anteriores deste repo.

Asercoes:
(1) `_moldura_da_barra_propria(recorte("escuro_cauda_vazia"))` fica abaixo de `BRILHO_MINIMO_DA_MOLDURA_PROPRIA`, ou seja dentro da faixa das cobertas. Passa desde ja e deve continuar passando: documenta a sobreposicao, nao o remedio.
(2) `extrair(frame_solo("escuro_cauda_vazia"), calibracao_do_widget).hp_proprio` E `None` — e vai continuar `None` depois da Task 2. Escrever na docstring que esta asercao existe para provar que a mudanca NAO mexe no que alimenta a maquina de estado.
(3) `extrair(...).hp_proprio_aparente` nao e `None` e vale ~0.8848. VERMELHA hoje: o campo ainda nao existe, e o `AttributeError` conta como vermelho.
(4) A calibracao usada em (2) e (3) e `dataclasses.replace(calibracao, limiares_hp=calibracao.limiares_mp)`. **A fixture e o widget de MP (azul), entao a mascara de HP nao a enxerga.** Isto NAO e sintetizar pixel nenhum: e apontar o detector para as cores do widget que a fixture contem, e todo o resto do caminho de `extrair` fica intocado. Escrever essa razao na docstring, porque e o detalhe que faz alguem achar que o teste esta trapaceando.
(5) `barra_propria_legivel(recorte("escuro_cheia"))` e `True` — a testemunha; passa hoje e depois.
(6) a cauda 100% vazia, `recorte("escuro_cauda_vazia")[:, 169:]`, tem `medir_barra` com limiares de MP igual a 0.0 e moldura abaixo do limiar. Afirmar os dois juntos: o primeiro prova que a derivacao do recorte esta certa, o segundo prova que o terreno escuro sozinho reprova no portao de hoje. A coluna 169 vem da medicao — 88.48% de 191 px termina o preenchimento ali.

Nao tocar em `l2scanner/` nesta task. Nao alterar nenhum teste existente nesta task.
  </action>
  <verify>
    <automated>python -c "import cv2,sys; sys.path.insert(0,'.'); from l2scanner.visao import _moldura_da_barra_propria as m; d='tests/fixtures/barra_propria/'; a=cv2.imread(d+'escuro_cauda_vazia.png'); b=cv2.imread(d+'escuro_cheia.png'); f=cv2.imread(d+'escuro_faixa.png'); assert a.shape==(24,191,3) and b.shape==(24,191,3) and f.shape==(28,191,3), (a.shape,b.shape,f.shape); assert (f[2:26]==a).all(), 'a faixa nao esta alinhada com a cauda vazia'; print('cauda_vazia moldura', round(m(a),2), '| cheia moldura', round(m(b),2)); assert abs(m(a)-29.08)<0.05 and abs(m(b)-86.42)<0.05"</automated>
    <automated>python -m pytest "tests/test_inventario_por_cima_da_barra_propria.py::TestOTerrenoEscuroSomeDoConsole" -q; test $? -eq 1 && echo "VERMELHO confirmado — o defeito esta preso no teste"</automated>
  </verify>
  <done>As tres fixtures existem, com as formas certas, com `escuro_faixa[2:26]` igual a `escuro_cauda_vazia`, e conferindo 29.08 e 86.42. A classe `TestOTerrenoEscuroSomeDoConsole` existe e falha — e falha na asercao (3), a do campo aparente, com a (2) ja verde. O `test $? -eq 1` e proposital: pytest devolve 1 para "teste falhou" e 4 para "nao coletou nada", entao esquecer de escrever a classe REPROVA o verify em vez de passar por engano. Commit `test(quick-260827-fsk): ...` com fixtures e teste juntos.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Leitura APARENTE em visao.py e no console — com rastreador.py fora do diff</name>
  <files>l2scanner/visao.py, l2scanner/__main__.py, tests/test_inventario_por_cima_da_barra_propria.py</files>
  <behavior>
    - `_casamento_do_perfil_proprio`: `escuro_cauda_vazia` +0.964, `escuro_cheia` +0.944, `livre_0` +1.000, `quase_vazia_terreno_atras` +0.979, cobertas totais -0.059..+0.236, `coberta_0` +0.999.
    - `Observacao.hp_proprio` sai IDENTICO a hoje nas 8 amostras da tabela da secao 7.
    - `Observacao.hp_proprio_aparente` sai `0.8848` para `escuro_cauda_vazia`, `0.8691` para `coberta_0`, e `None` para todas as outras 6.
    - As 5 janelas de 24 linhas dentro de `escuro_faixa.png` (dy -2..+2) dao TODAS +0.964; a moldura das mesmas 5 varia de 12.64 a 32.33.
    - `_braco_do_casamento(recorte, leitura)` e `False` para TODOS os 1733 compostos que leem em ou abaixo de `Ajustes().fracao_hp_considerada_zero`, nas duas direcoes de oclusao.
    - Alimentado 30 ticks de `coberta_0` por `extrair`, um `Rastreador` quente emite lista de eventos VAZIA — de qualquer tipo, em party e em solo, inclusive depois de uma morte real.
  </behavior>
  <action>
Em `l2scanner/visao.py`, ao lado das constantes de moldura, acrescentar `PERFIL_DE_REFERENCIA_DA_BARRA_PROPRIA` (os 20 valores da secao 13, como tupla de float), `LINHAS_DO_PERFIL_PROPRIO = 24`, `CASAMENTO_MINIMO_DO_PERFIL_PROPRIO = 0.40` e `LEITURA_MINIMA_PARA_O_CASAMENTO = 0.05`, documentando com as tabelas das secoes 2, 3, 4, 5, 8, 9 e 10 de onde cada numero saiu.

Implementar `_casamento_do_perfil_proprio(recorte) -> float`: cinza, media por LINHA (`axis=1`); se o perfil nao tiver `LINHAS_DO_PERFIL_PROPRIO` valores, reamostrar com `np.interp`; deslizar a referencia de 20 valores sobre o perfil de 24 em todas as posicoes e devolver a MAIOR correlacao de Pearson. Sem variancia em qualquer um dos vetores o denominador e zero e a funcao devolve 0.0 — nunca divide por zero, nunca aprova o degenerado.

Implementar `_braco_do_casamento(recorte, leitura) -> bool`: `False` quando `leitura` e `None` ou menor ou igual a `LEITURA_MINIMA_PARA_O_CASAMENTO`; senao `_casamento_do_perfil_proprio(recorte) >= CASAMENTO_MINIMO_DO_PERFIL_PROPRIO`. Separada de proposito: e ELA que carrega a propriedade de seguranca e o teste exaustivo precisa mira-la direto.

**NAO alterar `barra_propria_legivel`.** Ela continua com um argumento e com o mesmo corpo. Este e o ponto do desenho: o que alimenta `hp_proprio` nao muda, entao a maquina de estado nao pode mudar.

Acrescentar a `Observacao` o campo `hp_proprio_aparente: float | None = None`, com o padrao `None` para que toda construcao existente siga valida. Documentar no campo, em uma frase que o proximo leitor nao consiga ignorar, que ele e SO PARA MOSTRAR: pode vir de um recorte parcialmente coberto e por isso nenhuma decisao pode sair dele. Citar os numeros da secao 6 — as duas classes de alerta falso e o atraso de morte que sairiam se ele fosse tratado como leitura de verdade.

Em `extrair`, depois do bloco existente da barra propria e SEM MEXER nele, calcular o aparente: so quando `hp_proprio` ficou `None`, e o recorte existe e nao e vazio, medir a leitura com `cal.limiares_hp` sobre a regiao inteira, exigir desvio no minimo e `_braco_do_casamento(recorte, leitura)`; se passar, o aparente e a leitura, senao `None`.

Em `l2scanner/__main__.py`, na linha que monta o painel do proprio personagem (hoje `if obs.hp_proprio is not None and cal.nome_proprio:`, por volta da linha 395), acrescentar um ramo: quando `hp_proprio` e `None` mas `hp_proprio_aparente` nao e, montar a mesma linha com a leitura aparente e uma MARCA visivel de que ela e aparente e nao confirmada — um til antes do numero mais um sufixo curto. O simbolo de estado continua vindo do rastreador, que nao viu essa leitura; se isso ficar confuso, preferir um rotulo neutro a inventar um estado. Escrever no codigo que esta linha e a UNICA consumidora do campo, porque e essa unicidade que mantem a mudanca inofensiva.
  </action>
  <tests_a_acrescentar>
Nenhum teste existente precisa mudar — o pre-voo da secao 11 saiu com zero falhas. Acrescentar:

  - `TestOBracoNovoNuncaCertificaLeituraDeMorte`: a varredura EXAUSTIVA nas DUAS direcoes. Para cada preenchimento de direita em {`livre_0`, `quase_vazia_terreno_atras`, e a cauda 100% vazia real `escuro_cauda_vazia[:, 169:]` LADRILHADA ate 191 colunas}, para cada painel real em `coberta_0..3`, para k de 0 a 191: montar `painel[:, :k]` + `direita[:, k:]`, medir com `cal.limiares_hp`, e quando a leitura ficar em ou abaixo de `Ajustes().fracao_hp_considerada_zero` exigir `not _braco_do_casamento(composto, leitura)`. Ler as fixtures UMA vez fora do laco: medido, 0.06 s em cache contra 0.39 s relendo disco. Afirmar tambem que a contagem de compostos no regime de morte e maior que zero — senao um erro de montagem tornaria a varredura vacua e ela passaria verde sem testar nada. Dizer na docstring que dois dos tres preenchimentos sao recortes reais de largura inteira e o terceiro e real LADRILHADO: pixels reais, geometria sintetica.

  - `TestACobertaAtravessaORastreadorSemEmitirNada`: **o teste que faltava, e cuja ausencia e a razao de isto so ter aparecido no plan-check.** Aquecer um `Rastreador` com party visivel, depois alimenta-lo por 30 ticks com `extrair(frame_solo("coberta_0"), calibracao)` e exigir lista de eventos VAZIA — de QUALQUER tipo, sem filtrar por `MORREU`. Repetir em `modo_solo=True`. Repetir uma terceira vez com uma morte REAL antes do inventario, exigindo que o unico evento seja o `MORREU` verdadeiro e que nao venha `RESSUSCITOU` nem `VOCE_SEM_PARTY` depois. Na docstring: `test_trinta_frames_de_inventario_aberto_nao_emitem_morte` FILTRA por morte e por isso nao pegava isto; citar os ticks 27, 34 e 37 medidos na secao 6 como o que aconteceria se a leitura aparente vazasse para `hp_proprio`.

  - `TestOAparenteNaoMudaNadaDoQueAMaquinaDeEstadoVe`: para as 8 amostras da tabela da secao 7, afirmar o valor exato de `hp_proprio`. E afirmar que `l2scanner/rastreador.py` nao le o campo aparente, lendo o fonte e exigindo que o nome do campo nao apareca la. E grosseiro de proposito: e um tripwire de ARQUITETURA, e a mensagem de falha deve dizer que a maquina de estado passou a depender de uma leitura que pode estar ocluida.

  - `TestOPortaoDeLeituraEstaAmarradoAoRastreador`: `LEITURA_MINIMA_PARA_O_CASAMENTO > Ajustes().fracao_hp_considerada_zero`. Duas camadas, um acoplamento numerico; sem o tripwire, baixar o limiar do rastreador reabre o buraco pela porta dos fundos.

  - `TestOCasamentoTolera2pxDeDesalinhamento`: percorrer as 5 janelas de 24 linhas de `escuro_faixa.png` (dy -2..+2) e exigir casamento acima do limiar em todas. Nada de `np.roll` — rolar inventa linhas, e a faixa existe para que cada deslocamento venha de pixels reais. Afirmar tambem que a moldura das mesmas 5 varia de ~12.6 a ~32.3, isto e, que o discriminador ANTIGO e caotico onde o novo e estavel. Fechar com `escuro_faixa[2:26]` igual a `escuro_cauda_vazia`.

  - `TestOBuracoPreExistenteDoBracoDeMoldura`: CARACTERIZACAO, nao remedio. `coberta_2[:, :k]` + `livre_0[:, k:]` para k em {5, 20, 60} le 0.0000 com moldura 64.00 e ja e aceito HOJE. Afirmar que o buraco EXISTE e apontar, na docstring, para o TODO — assim, no dia em que alguem o fechar, este teste quebra e obriga a atualizar o registro.

  - Guardas de populacao: qualquer teste que fale em "as 45 livres" ou "as 8 cobertas" so pode AFIRMAR sobre as 4 fixtures VERSIONADAS; a parte que vem de `recordings/inv2/` ou `recordings/inv3/` fica atras de `pytest.skip` com a razao, porque `recordings/` e gitignored e um clone limpo nao consegue prova-las.

Nao acrescentar dependencia nenhuma.
  </tests_a_acrescentar>
  <verify>
    <automated>python -m pytest tests/test_inventario_por_cima_da_barra_propria.py -q</automated>
    <automated>python -m pytest tests/ -q; test $? -eq 0 && echo "suite verde"</automated>
    <automated>python -m pytest tests/ --collect-only -q 2>/dev/null | tail -1 | awk '{print "coletados:", $1} $1<=1127 {print "FALHOU: a suite nao cresceu (baseline 1127)"; exit 1}'</automated>
    <automated>test -z "$(git diff --name-only 9d5533e..HEAD -- l2scanner/rastreador.py)" && echo "rastreador.py FORA do diff — a maquina de estado nao foi tocada"</automated>
    <!-- planner-discipline-allow: hp_proprio_aparente -->
    <!-- O eco e intencional: o <action> PRECISA nomear o campo para cria-lo em visao.py,
         e o portao nega a presenca dele em rastreador.py, que e OUTRO arquivo. -->
    <automated>test "$(grep -c 'hp_proprio_aparente' l2scanner/rastreador.py)" -eq 0 && echo "a maquina de estado nao le a leitura aparente"</automated>
    <automated>test -z "$(git diff --name-only 9d5533e..HEAD -- pyproject.toml)" && echo "pyproject intocado desde o commit do plano"</automated>
  </verify>
  <done>`python -m pytest tests/ -q` sai com codigo 0 e `--collect-only` conta mais de 1127. `hp_proprio` sai identico a hoje nas 8 amostras; `hp_proprio_aparente` sai 0.8848 e 0.8691 e `None` nas outras seis. A varredura exaustiva passa e nao e vazia. `coberta_0` atravessa o `Rastreador` sem emitir evento de tipo nenhum, em party e em solo. `l2scanner/rastreador.py` e `pyproject.toml` ficam fora do diff. Commits `feat(quick-260827-fsk): ...` e `test(quick-260827-fsk): ...`.</done>
</task>

<task type="auto">
  <name>Task 3: Registrar o que NAO fechou — o TODO continua ABERTO, agora com quatro regimes</name>
  <files>.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md, .planning/STATE.md</files>
  <action>
Atualizar o TODO **sem move-lo para `done/`**. Ele permanece em `pending/` porque o criterio de aceite que ele mesmo escreveu continua sem amostra, e porque esta tarefa descobriu que o alvo e maior do que ele supunha.

Acrescentar uma secao datada de 2026-08-27 com, nesta ordem:

(1) **O que virou fato.** A projecao de "~32" virou medicao: 29.08, no widget de MP de `recordings/escuro_janela.png`, com a barra apenas 88.5% cheia — o regime nao precisa de barra vazia, 11.5% de cauda basta. A amostra foi resgatada para `tests/fixtures/barra_propria/escuro_cauda_vazia.png`, porque `recordings/` esta no `.gitignore` e ela era a unica copia.

(2) **O que mudou no produto, e o que NAO mudou.** Um campo `hp_proprio_aparente` passou a carregar a leitura que o portao de hoje descarta, e o console e o log a mostram MARCADA COMO APARENTE. `hp_proprio` nao mudou, `rastreador.py` nao foi tocado e **nenhum alerta mudou**. A descida em cena escura voltou a ser MOSTRADA, nao a ser decidida.

(3) **Por que a leitura nova nao pode virar alerta.** `coberta_0` (moldura 48.00) e `escuro_cauda_vazia` (29.08) so se ordenam pela moldura, e nessa ordem `coberta_2` (28.00) e `coberta_3` (29.00) ficam ABAIXO do ponto legitimo — a classe errada dos dois lados. Tudo que o braco novo certifica pode ser um recorte parcialmente coberto.

(4) **O CUSTO MEDIDO contra a maquina de estado**, que e o achado desta rodada. `hp_proprio` tem TRES consumidores (`rastreador.py` 454, 496 e 833). Se a leitura aparente virasse `hp_proprio`, um inventario aberto produziria `VOCE_SEM_PARTY` falso no tick 27, `RESSUSCITOU` falso no tick 34 (inclusive em `--solo`) e atrasaria uma morte em andamento do tick 18 para o 20. Registrar a tabela inteira da secao 6.

(5) **O REGIME QUE CONTINUA SEM REMEDIO.** No regime de leitura zero sobre terreno escuro as classes se INTERCALAM: genuina +0.627 contra ocluida +0.645. Nenhum limiar separa; o motivo e estrutural. Listar as duas saidas possiveis: uma amostra real das duas classes, ou um sinal TEMPORAL no rastreador — mudanca de camada, com risco proprio de falso positivo.

(6) **O DEFEITO PRE-EXISTENTE do braco de moldura.** `coberta_2` com o painel a esquerda le 0.0000 e ja e aceito HOJE (moldura 64.00) — morte falsa por um caminho que nenhum dos dois bracos cobre. Nao e criado nem fechado aqui, e nao e fechavel por portao de leitura, porque o braco de moldura PRECISA certificar leitura zero: e assim que a morte e anunciada em terreno de dia. Candidato medido: contiguidade do preenchimento (`sobra` = 0 nas 51 amostras genuinas, 11..186 nos compostos de oclusao a esquerda), que so pode entrar depois de medida contra TERRENO VERMELHO, porque lava e chao avermelhado podem gerar colunas cheias espurias e o modo de falha dela e SILENCIO.

(7) **A LACUNA DE COBERTURA que deixou isto escapar.** Nenhum teste levava um recorte coberto ate dentro do `Rastreador`; o unico que chega la filtra os eventos por `MORREU`. Fechada nesta tarefa, e vale como regra: teste de deteccao que filtra por um tipo de evento nao prova ausencia dos outros.

(8) **±2 px e a tolerancia inteira**, sem rede alem dela: em ±3 px o casamento (0.293/0.364) e a moldura (35.04/30.29) reprovam juntos.

(9) **O sinal de que a pendencia virou defeito**, atualizado: barra propria aparecendo no log como APARENTE durante combate escuro e a descida sendo mostrada sem que morte nenhuma seja anunciada — isso aponta para o regime de leitura zero do item 5.

Atualizar o front-matter `files:` do TODO para citar os arquivos que agora importam, incluindo as tres fixtures novas e `l2scanner/__main__.py`.

Em `.planning/STATE.md`: manter a linha do todo em `## Pending Todos` (segue aberto, severidade major), acrescentar a linha da quick em `## Quick Tasks Completed` no estilo das anteriores — o que foi medido, o que mudou, **o que NAO fechou e por que**, e a contagem da suite nas duas pontas — e atualizar `## Session Continuity`.
  </action>
  <verify>
    <automated>test -f ".planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md" && echo "TODO segue em pending/"</automated>
    <automated>test ! -f ".planning/todos/done/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md" && echo "TODO nao foi fechado"</automated>
    <automated>python -c "import io,sys; t=io.open('.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md',encoding='utf-8').read(); [sys.exit('FALTA no TODO: '+n) for n in ['2026-08-27','29.08','0.627','0.645','escuro_cauda_vazia','coberta_2','voce_sem_party','ressuscitou'] if n not in t]; print('o TODO registra a medicao, a colisao, o custo na maquina de estado e o buraco pre-existente')"</automated>
    <automated>python -c "import io; s=io.open('.planning/STATE.md',encoding='utf-8').read(); assert '260827-fsk' in s, 'STATE nao cita a quick'; assert 'moldura-da-barra-propria-em-terreno-escuro' in s, 'STATE perdeu o todo aberto'; print('STATE atualizado e o todo segue listado')"</automated>
    <automated>python -m pytest tests/ -q; test $? -eq 0 && echo "suite verde"</automated>
  </verify>
  <done>O TODO continua em `pending/`, datado de 2026-08-27, com os nove registros acima — em especial o custo medido contra a maquina de estado, o regime que nao fecha e os dois defeitos pre-existentes — e com o `files:` atualizado. STATE.md cita a quick dizendo o que NAO fechou, mantem o todo em `Pending Todos` e tem a continuidade de sessao atualizada. Commit `docs(quick-260827-fsk): ...`.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pixels da tela do jogo -> `extrair` | entrada NAO CONFIAVEL: qualquer janela do jogo, qualquer terreno, qualquer overlay pode estar naqueles 191x24 px |
| `Observacao.hp_proprio_aparente` -> `__main__.py` (console/log) | fronteira de EXIBICAO. A leitura pode vir de recorte ocluido; nada alem de texto pode sair dela |
| `Observacao.hp_proprio` -> `rastreador.py` (linhas 454, 496, 833) | fronteira de DECISAO. Intocada nesta tarefa, e a verificacao e o diff |
| `recordings/` (gitignored) -> `tests/fixtures/` (versionado) | promocao de artefato local nao versionado para evidencia permanente |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-fsk-01 | Spoofing | recorte ocluido virando alerta | critical | mitigate | Duas versoes anteriores deste plano teriam produzido `VOCE_SEM_PARTY` falso (tick 27), `RESSUSCITOU` falso (tick 34) e atraso de morte (18 -> 20). Mitigado por CONSTRUCAO: a leitura vive em `hp_proprio_aparente`, que `rastreador.py` nao le. Provado por `TestACobertaAtravessaORastreadorSemEmitirNada` (lista de eventos vazia, qualquer tipo, party e solo) e pelo tripwire de arquitetura que exige o campo ausente do fonte do rastreador. |
| T-fsk-02 | Spoofing | painel de inventario virando MORTE | critical | mitigate | Portao de leitura de 0.05 contra limiar de morte de 0.02, verificado por EXAUSTAO nas duas direcoes de oclusao: 2304 compostos, 1733 no regime de morte, zero aceitos. Teste `TestOBracoNovoNuncaCertificaLeituraDeMorte`. |
| T-fsk-03 | Denial of Service | portao recusando recorte legitimo | high | accept | `hp_proprio` nao muda, entao esta tarefa nao acrescenta nem remove silencio. O silencio EXISTENTE em cena escura (morte nao anunciada) continua e esta registrado no TODO como o regime que nao fecha. |
| T-fsk-04 | Elevation of Privilege | `fracao_hp_considerada_zero` baixado no rastreador | high | mitigate | Baixar o limiar de morte anularia o portao de leitura a distancia, sem tocar em `visao.py`. Tripwire `TestOPortaoDeLeituraEstaAmarradoAoRastreador`. |
| T-fsk-05 | Spoofing | oclusao pela esquerda passando pelo braco de MOLDURA | high | transfer | Defeito PRE-EXISTENTE (`coberta_2`, moldura 64.00, leitura 0.0000). Nao criado nem fechado aqui, e nao fechavel por portao de leitura. Transferido para o TODO com a medicao, o candidato (`sobra`) e a condicao para adota-lo. Preso por `TestOBuracoPreExistenteDoBracoDeMoldura`. |
| T-fsk-06 | Repudiation | log mostrando leitura aparente como se fosse confirmada | medium | mitigate | Um numero no log sem marca vira evidencia falsa numa investigacao pos-farm. Mitigado pela MARCA visivel exigida na Task 2 e pelo simbolo de estado continuar vindo do rastreador. |
| T-fsk-07 | Tampering | perfil de referencia e os dois limiares | medium | mitigate | Constantes ajustadas no escuro reabrem o defeito em silencio. Classes presas em testes com o numero medido na mensagem de falha. |
| T-fsk-08 | Tampering | fixtures PNG novas | low | accept | Arquivos versionados; alteracao aparece no diff e derruba as asercoes de 29.08 / 86.42 da Task 1. |
| T-fsk-09 | Information Disclosure | fixtures resgatadas de captura de tela real | low | accept | Recortes de 191x24 px de barras de HP/MP. Sem nome de conta, telefone, token ou texto de chat. |
| T-fsk-SC | Tampering | instalacao de pacotes (npm/pip/cargo) | n/a | accept | Zero instalacao: `numpy` e `cv2` ja sao importados por `l2scanner/visao.py`. Sem task de install, o portao de legitimidade de pacote nao se aplica. `pyproject.toml` verificado contra `9d5533e` na Task 2. |
</threat_model>

<verification>
1. `python -m pytest tests/ -q` sai com **codigo 0**, e `--collect-only` conta mais que o baseline de `1127`. A contagem de `skipped` NAO e afirmada, porque as guardas novas de `pytest.skip` a fazem crescer num clone limpo.
2. `Observacao.hp_proprio` sai identico a hoje nas 8 amostras da tabela da secao 7.
3. `hp_proprio_aparente` sai `0.8848` para `escuro_cauda_vazia`, `0.8691` para `coberta_0` e `None` para as outras seis.
4. `coberta_0` atravessa o `Rastreador` por 30 ticks sem emitir evento de tipo NENHUM, em party e em solo, e depois de uma morte real nao produz `RESSUSCITOU` nem `VOCE_SEM_PARTY`.
5. A varredura exaustiva das duas direcoes passa e nao e vazia.
6. `LEITURA_MINIMA_PARA_O_CASAMENTO > Ajustes().fracao_hp_considerada_zero`.
7. As 5 janelas de `escuro_faixa.png` (dy -2..+2) casam acima do limiar.
8. `l2scanner/rastreador.py` e `pyproject.toml` fora do diff desde `9d5533e`, e o nome do campo aparente nao aparece no fonte do rastreador.
9. O TODO segue em `pending/` e registra a medicao, a colisao, o custo contra a maquina de estado e os dois defeitos pre-existentes.
</verification>

<success_criteria>
- O console e o log param de nao mostrar nada da barra propria em cena escura — medido na fixture `escuro_cauda_vazia.png`, que hoje nao produz linha nenhuma.
- NENHUM alerta muda, e a prova e o diff: `rastreador.py` fora dele e a suite verde sem um unico teste mudando de veredito.
- Nenhuma classe nova de alerta falso e criada, e a antiga continua suprimida — provado por um teste que atravessa o `Rastreador` e olha TODOS os tipos de evento, nao so morte.
- Todo limiar do diff vem de uma medicao registrada neste plano e repetida em comentario no codigo.
- O que NAO fecha esta dito com numero: a morte em cena escura, o defeito pre-existente do braco de moldura, a lacuna de cobertura e o teto de ±2 px — os quatro no TODO, que permanece ABERTO.
</success_criteria>

<output>
Create `.planning/quick/260827-fsk-trocar-o-discriminador-da-legibilidade-d/260827-fsk-SUMMARY.md` when done.

O SUMMARY precisa dizer, explicitamente e com numero: (a) que a projecao de "~32"
virou medicao de 29.08 numa fixture agora versionada; (b) que a entrega e de
EXIBICAO e nao de alerta — `hp_proprio` intocado, `rastreador.py` fora do diff,
suite verde sem um teste mudando de veredito; (c) que a promessa encolheu TRES
vezes ao longo do planejamento, e o que cada rodada mediu que derrubou a
anterior — em especial os TRES consumidores de `hp_proprio` e os alertas falsos
que sairiam deles; (d) que a morte em cena escura continua sem remedio, com a
intercalacao +0.627 contra +0.645; e (e) que o TODO NAO FECHOU.
</output>
