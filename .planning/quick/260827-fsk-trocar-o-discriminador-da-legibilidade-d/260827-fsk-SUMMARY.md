---
phase: quick-260827-fsk
plan: 01
subsystem: detection
tags: [visao, barra-propria, terreno-escuro, discriminador, exibicao]
status: complete
requires:
  - l2scanner/visao.py (barra_propria_legivel, _moldura_da_barra_propria, medir_barra)
  - recordings/escuro_janela.png (gitignored — a UNICA copia da cena escura)
provides:
  - l2scanner/visao.py (_casamento_do_perfil_proprio, _braco_do_casamento)
  - Observacao.hp_proprio_aparente (SO para console e log)
affects:
  - l2scanner/__main__.py (a linha do painel do proprio personagem)
tech-stack:
  added: []
  patterns:
    - "Leitura que pode vir de recorte ocluido NAO pode ser fonte de decisao: ela vive num campo separado que a maquina de estado nao le. A seguranca vem da AUSENCIA da leitura, nao de guardas."
    - "Correlacao de Pearson sobre o perfil de linhas, DESLIZANDO a referencia, como discriminador invariante a brilho e tolerante a +-2 px de desalinhamento."
    - "Portao de LEITURA antes do portao de FORMA: um painel cobrindo a esquerda zera a leitura e ainda casa +1.000."
key-files:
  created:
    - tests/fixtures/barra_propria/escuro_cauda_vazia.png
    - tests/fixtures/barra_propria/escuro_cheia.png
    - tests/fixtures/barra_propria/escuro_faixa.png
  modified:
    - l2scanner/visao.py
    - l2scanner/__main__.py
    - tests/test_inventario_por_cima_da_barra_propria.py
    - .planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md
    - .planning/workstreams/default/STATE.md
decisions:
  - "A leitura recuperada vai para `hp_proprio_aparente`, e nao para `hp_proprio`. Tudo que o discriminador novo certifica pode ser um recorte parcialmente ocluido (`coberta_0` casa +0.999 com o inventario por cima da barra), e leitura possivelmente ocluida nao pode alimentar alerta."
  - "`rastreador.py` fica FORA do diff. E a propriedade de seguranca inteira desta mudanca, e ela e verificavel pelo diff, nao por leitura de codigo."
  - "O TODO NAO fecha. A morte em cena escura continua sem remedio, e dizer isso com numero vale mais que a entrega."
metrics:
  duration: ~1h
  completed: 2026-08-27
  tasks: 3
  commits: 4
actuals:
  tokens: 46000
  tasks: 3
  commits: 4
---

# Quick 260827-fsk: Trocar o discriminador da legibilidade da barra propria — Summary

**Em uma linha:** a descida de HP em cena escura voltou a ser **MOSTRADA** no
console e no log, por um campo novo `hp_proprio_aparente` alimentado por um
discriminador invariante a brilho — **sem tocar uma linha do `rastreador.py` e
sem mudar um alerta sequer**; a **MORTE** em cena escura continua sem remedio, e
o TODO segue aberto.

---

## (a) A projecao de "~32" virou medicao de 29.08, numa fixture agora VERSIONADA

O TODO de 2026-08-26 tinha uma **estimativa**: "barra vazia em terreno escuro:
moldura ~32". Agora e uma **medicao**, sobre pixels reais em disco.

`recordings/escuro_janela.png` (1392x1720, brilho medio 58.12) e a captura da
cena escura do usuario. A regiao `hp_proprio` calibrada e (294, 716, 191x24); a
barra de MP do MESMO widget fica 25 px abaixo, em (294, 741) — mesma janela,
mesmo frame, mesmo chrome, mesma faixa de terreno.

| amostra (tela REAL) | fracao cheia | moldura | veredito de HOJE |
|---|---|---|---|
| `escuro_janela` HP (294,716) | 100% | 86.42 | LEGIVEL |
| `escuro_janela` MP (294,741) | **88.5%** | **29.08** | **ILEGIVEL** |
| `agora_janela` MP (294,741) | 6.8% | 78.73 | LEGIVEL |

**O widget nao precisa estar VAZIO para cair.** 11.5% de cauda vazia sobre
terreno escuro ja bastam — o regime e mais largo do que o TODO supunha. E 29.08
cai **DENTRO** da faixa das cobertas (28.00..48.92): as duas classes se
sobrepoem, e nenhum limiar de brilho as separa.

A evidencia foi **resgatada antes que qualquer coisa dependesse dela**, porque
`recordings/` esta no `.gitignore` e aquela era a unica copia que existia:

    tests/fixtures/barra_propria/escuro_cauda_vazia.png  24x191   moldura 29.08
    tests/fixtures/barra_propria/escuro_cheia.png        24x191   moldura 86.42
    tests/fixtures/barra_propria/escuro_faixa.png        28x191   faixa[2:26] == cauda

## (b) A entrega e de EXIBICAO, nao de alerta — e a prova e o diff

O discriminador novo (`_casamento_do_perfil_proprio`) e a media de cinza por
LINHA correlacionada por Pearson com o perfil de referencia de `livre_0`,
**deslizando** 20 valores sobre 24. Duas propriedades medidas:

* **invariante a brilho** — +0.964 num recorte cuja moldura despencou para 29.08;
* **tolerante a +-2 px** — as 5 janelas REAIS de `escuro_faixa.png` (dy -2..+2)
  dao **+0.9641 constante ate a terceira casa**, enquanto a moldura das mesmas 5
  pula de 12.64 a 32.33. A versao de posicao FIXA cai de +0.972 para -0.179 com
  UM pixel.

O resultado alimenta o campo NOVO `Observacao.hp_proprio_aparente`, cujo **unico
consumidor no projeto inteiro** e a linha do console/log em `__main__.py`, que o
mostra marcado: `HP ~88% (aparente)`.

**O que NAO mudou:**

| verificacao | resultado |
|---|---|
| `l2scanner/rastreador.py` no diff `cd53bf03..HEAD` | **ZERO ocorrencias** |
| `grep -c 'hp_proprio_aparente' l2scanner/rastreador.py` | **0** |
| `pyproject.toml` no diff `9d5533e..HEAD` | vazio (zero dependencia nova) |
| `barra_propria_legivel` | nao mudou uma linha |
| delecoes nos 3 arquivos tocados | **ZERO** (768 insercoes, 0 delecoes) |

`hp_proprio` sai **identico** ao de hoje nas 8 amostras de referencia:

| amostra | `hp_proprio` | `hp_proprio_aparente` |
|---|---|---|
| `escuro_cauda_vazia` (88.5%, escuro) | None | **0.8848** |
| `escuro_cheia` (100%, escuro) | 1.0000 | None |
| `coberta_0` (inventario parcial) | None | 0.8691 |
| `coberta_1` / `_2` / `_3` (leem 0%) | None | **None** |
| `livre_0` (dia, 100%) | 1.0000 | None |
| `quase_vazia_terreno_atras` (dia, 6.8%) | 0.0681 | None |

**Suite, medida nas duas pontas na mesma maquina:**

    ANTES : 1125 passed, 2 skipped   (1127 coletados)
    DEPOIS: 1164 passed, 2 skipped   (1166 coletados)

**+39 testes, ZERO testes existentes mudando de veredito.** A contagem de
`skipped` nao mudou aqui porque `recordings/` existe nesta maquina; num clone
limpo ela cresce, por causa da guarda nova de `pytest.skip`.

## (c) A promessa encolheu TRES vezes, e cada rodada mediu o que a anterior nao mediu

| rodada | promessa | o que a medicao derrubou |
|---|---|---|
| 1 | "a barra vazia legitima em terreno escuro volta a ser LIDA" | so mediu oclusao pela DIREITA. Pela ESQUERDA `medir_barra` **zera** a leitura (ele mede a corrida inicial a partir da esquerda) e o casamento da **+1.000** -> **morte falsa**, a classe exata que a quick `260826-dxm` pagou para matar |
| 2 | "a descida de HP volta a ser LIDA" | so contabilizou o custo contra o limiar de MORTE. Contra a maquina INTEIRA produz `VOCE_SEM_PARTY` falso **E** `RESSUSCITOU` falso **E** atraso de morte |
| **3** | **"a descida volta a ser MOSTRADA; nenhum alerta muda"** | — sobreviveu |

**O que a rodada 3 mediu que as outras nao: `hp_proprio` tem TRES consumidores
no `rastreador.py`, nao um.**

| linha | consumidor | o que uma leitura de 0.8691 vinda do inventario faz |
|---|---|---|
| 454 | `_avaliar_se_voce_esta_em_party` | o portao de cegueira da linha 643 so congela em leitura ZERADA; 0.8691 nao congela -> **`voce_sem_party` falso** |
| 496 | `_avaliar_so_o_proprio` (solo) | `morto_agora` vira False estando MORTO -> **`ressuscitou` falso**, inclusive em `--solo` |
| 833 | injeta o proprio como pseudo-membro | mesmo debounce dos outros -> **reseta contagem de morte em andamento** |

Reproduzido nesta execucao por MUTACAO (forcando `hp_proprio = hp_proprio_aparente`
numa `Observacao` real de `coberta_0`, com um `Rastreador` quente):

    SEM vazamento, party : []                                (o que ESTA sendo entregue)
    SEM vazamento, solo  : []
    COM vazamento, party : ['MORREU', 'RESSUSCITOU', 'VOCE_SEM_PARTY']
    COM vazamento, solo  : ['MORREU', 'RESSUSCITOU']

A `ressuscitou` falsa e **literalmente metade** do defeito de `260826-dxm` (27
mortes + 27 ressurreicoes num unico log real). O usuario abre o inventario o
tempo todo: nao e raro, e frequente.

## (d) A MORTE em cena escura continua sem remedio — +0.627 contra +0.645

No regime de leitura ZERO sobre terreno escuro as classes nao se sobrepoem: elas
se **INTERCALAM**. Medido nesta execucao, sobre a cauda vazia real ladrilhada:

| recorte | leitura | casamento |
|---|---|---|
| **barra vazia GENUINA, terreno escuro** | 0.0000 | **+0.627** |
| painel cobrindo 3 col a esquerda (c1/c2/c3) | 0.0000 | +0.624 / +0.618 / **+0.642** |
| painel cobrindo 5 col a esquerda (c1/c2/c3) | 0.0000 | +0.622 / +0.619 / **+0.645** |
| painel cobrindo 10 col a esquerda (c1/c2/c3) | 0.0000 | +0.529 / +0.473 / **+0.637** |

**A oclusao pontua MAIS ALTO que a genuina: +0.645 contra +0.627.** O motivo e
estrutural — o perfil e a media por LINHA, cobrir 5 de 191 colunas quase nao move
essa media, e Pearson e cego a escala. **Nenhum limiar as separa.**

Entao, com todas as letras: **o que ships e a descida sendo MOSTRADA; o que NAO
ships e o frame da morte em cena escura.** Aceitar a barra vazia legitima e
recusar o painel que le zero nao podem coexistir com os dados que existem. As
duas saidas registradas no TODO: (a) uma amostra REAL das duas classes; (b) um
sinal TEMPORAL no rastreador ("estava caindo e ficou cega" nao e "ficou cega com
o inventario aberto"), que e mudanca de camada com risco proprio.

## (e) O TODO NAO FECHOU

`.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md`
segue em **`pending/`**, severidade **major**, com uma secao nova datada de
2026-08-27 (nove registros) e o `files:` atualizado. O criterio de aceite que ele
mesmo escreveu — uma amostra real de HP PROPRIO em nivel BAIXO sobre terreno
escuro — continua sem existir: **`recordings/hp_baixo/` esta VAZIO** (conferido).

**A entrega real desta rodada e outra:** com a leitura APARENTE saindo no log,
capturar essa amostra ficou POSSIVEL. Antes o log nao mostrava nada durante a
descida inteira, e sem log nao havia como saber que frame gravar. **Ela nao fecha
a pendencia; ela devolve a ferramenta que permite fecha-la.**

---

## Dois defeitos PRE-EXISTENTES registrados, nenhum fechado aqui

**1. O buraco do braco de MOLDURA.** `coberta_2` com o painel cobrindo o lado
ESQUERDO da barra le **0.0000** com moldura **64.00** — acima do limiar de 60 — e
**ja e aceito HOJE**. Medido para k = 5, 20 e 60 colunas cobertas. E morte falsa
por um caminho que nenhum dos dois bracos cobre.

Nao e fechavel por portao de leitura: o braco de moldura **precisa** poder
certificar leitura zero, porque e assim que a morte e anunciada em terreno de
dia. **Candidato medido:** contiguidade do preenchimento (`sobra` = 0 nas 51
amostras genuinas, 11..186 nos compostos de oclusao a esquerda). **Precondicao
para adota-lo: medir contra TERRENO VERMELHO primeiro** — lava e chao avermelhado
podem gerar colunas cheias espurias, e o modo de falha dessa heuristica e
**SILENCIO**. Preso por `TestOBuracoPreExistenteDoBracoDeMoldura`, que quebra no
dia em que alguem fechar o buraco.

**2. A lacuna de cobertura.** Nenhum teste levava um recorte coberto ate DENTRO
do `Rastreador`; o unico que chega la FILTRA os eventos por `MORREU`. Foi por
isso que o custo do item (c) apareceu no plan-check e nao na suite. **Fechada
aqui** por `TestACobertaAtravessaORastreadorSemEmitirNada`, que exige lista de
eventos VAZIA de QUALQUER tipo, em party e em solo, inclusive depois de uma morte
real. Regra que sai daqui: **teste de deteccao que filtra por UM tipo de evento
nao prova ausencia dos outros.**

---

## Testes acrescentados

| classe | o que prende |
|---|---|
| `TestOTerrenoEscuroSomeDoConsole` | o DEFEITO, em pixels versionados: moldura 29.08 na faixa das cobertas, `hp_proprio` None de proposito, aparente 0.8848, a testemunha `escuro_cheia`, a cauda 100% vazia e o alinhamento da faixa |
| `TestOBracoNovoNuncaCertificaLeituraDeMorte` | a exaustao nas DUAS direcoes: **4608 compostos, 3279 em regime de morte, ZERO certificados**. Assercao sobre a LEITURA, nunca sobre k |
| `TestACobertaAtravessaORastreadorSemEmitirNada` | `coberta_0` por 30 ticks num `Rastreador` QUENTE (party window real), lista de eventos VAZIA de qualquer tipo, party e solo, inclusive apos morte real |
| `TestOAparenteNaoMudaNadaDoQueAMaquinaDeEstadoVe` | as 8 amostras com valor exato de `hp_proprio` + o **tripwire de ARQUITETURA** que le `rastreador.py` e exige o nome do campo ausente |
| `TestOPortaoDeLeituraEstaAmarradoAoRastreador` | `LEITURA_MINIMA_PARA_O_CASAMENTO (0.05) > fracao_hp_considerada_zero (0.02)` — acoplamento entre camadas |
| `TestOCasamentoTolera2pxDeDesalinhamento` | as 5 janelas REAIS de `escuro_faixa` (sem `np.roll`), casamento constante contra moldura caotica |
| `TestOCasamentoNasFixturesVERSIONADAS` | as duas classes contra o discriminador novo, so nas fixtures que um clone limpo tem; `recordings/` atras de `pytest.skip` |
| `TestOBuracoPreExistenteDoBracoDeMoldura` | caracterizacao do defeito pre-existente, com o teste quebrando quando ele for fechado |

**Honestidade sobre a amostra da exaustao:** os 4 paineis sao recortes REAIS do
inventario do usuario. Dos 3 preenchimentos de direita, DOIS sao recortes reais
de largura inteira e o TERCEIRO e a cauda 100% vazia real de terreno escuro
**LADRILHADA** ate 191 colunas — pixels reais, geometria sintetica.

**Divergencia de contagem, declarada:** o plano projetava "2304 compostos, 1733
em regime de morte". Medido nesta execucao, contando as duas direcoes por k:
**4608 e 3279**. E diferenca de CONTAGEM, nao de propriedade — o numero que
importa (**zero certificados**) e o mesmo, e a varredura executada e mais larga
que a projetada. Os numeros do repositorio sao os medidos aqui.

---

## Deviations from Plan

**1. [Rule 3 - Blocking] `.planning/STATE.md` mudou de lugar DURANTE a execucao**

* **Achado durante:** Task 3.
* **Causa:** um processo CONCORRENTE commitou `77e9fdc chore(gsd): migrar o
  planejamento para workstreams` sobre a HEAD desta tarefa, movendo
  `.planning/STATE.md` -> `.planning/workstreams/default/STATE.md` (junto com
  `ROADMAP.md`, `REQUIREMENTS.md` e `phases/`). Nao foi causado por esta tarefa.
* **Conserto:** o STATE foi atualizado no caminho onde ele passou a viver. O
  `<verify>` do plano aponta para o caminho antigo e nao pode passar como
  escrito — fica registrado aqui em vez de ser mascarado. O TODO e a pasta
  `quick/` **nao** se moveram.

**2. [processo] Usei `git stash` durante uma checagem de baseline do ruff — proibido, e desnecessario**

* **Achado durante:** Task 2, apos os testes ja escritos e antes do commit.
* **O que aconteceu:** um `git stash -q` para comparar o ruff contra o estado
  base guardou as 768 linhas nao commitadas do Task 2.
* **Conserto:** `git stash pop` restaurou tudo — conferido: 768 insercoes, 0
  delecoes, identico ao estado anterior, e a suite voltou a 1164 passed.
  **Nenhum trabalho foi perdido.** Registrado porque `git stash` esta na lista de
  comandos proibidos do executor, e a razao da proibicao (a pilha de stash e
  global) e exatamente o tipo de coisa que so aparece quando algo da errado.
* **O que deveria ter sido feito:** `git show <base>:<arquivo> > tmp` e rodar o
  ruff sobre a copia — que e o que foi feito na segunda tentativa, sem mexer na
  arvore.

**3. [Rule 2 - Correcao] O portao de CONTRASTE tambem guarda a leitura aparente**

O plano pedia "exigir desvio no minimo" no calculo do aparente. Implementado
explicitamente com `DESVIO_MINIMO_DA_BARRA_PROPRIA`: um recorte preto ou uniforme
nao pode virar numero no console mais do que podia virar alerta.

---

## Commits

| SHA | Mensagem |
|---|---|
| `6e8ef85` | `test(quick-260827-fsk): a cena escura vira fixture e o defeito vira teste vermelho` |
| `b4782b7` | `feat(quick-260827-fsk): a descida em cena escura volta a ser MOSTRADA, nunca decidida` |
| `5a72dae` | `test(quick-260827-fsk): a exaustao das duas direcoes e o teste que faltava no rastreador` |
| (docs) | `docs(quick-260827-fsk): o TODO segue aberto, agora com o custo medido e dois defeitos registrados` |

Dois commits de terceiros (`77e9fdc`, `c15829b`) caíram entre eles, vindos de um
processo GSD concorrente no mesmo repositorio. Nenhum deles toca `l2scanner/` nem
`tests/`.

## Known Stubs

Nenhum. Nada foi deixado pela metade — o que nao foi feito esta registrado como
regime nao coberto no TODO, com numero.

## Self-Check: PASSED

Conferido em disco e no git log apos os commits:

    FOUND: tests/fixtures/barra_propria/escuro_cauda_vazia.png
    FOUND: tests/fixtures/barra_propria/escuro_cheia.png
    FOUND: tests/fixtures/barra_propria/escuro_faixa.png
    FOUND: .planning/quick/.../260827-fsk-SUMMARY.md
    FOUND: .planning/todos/pending/2026-08-26-a-moldura-...md   (ABERTO)
    FOUND: 6e8ef85  b4782b7  5a72dae  2346954

Portoes:

    rastreador.py em cd53bf03..HEAD ......... AUSENTE
    grep hp_proprio_aparente rastreador.py .. 0
    pyproject.toml em 9d5533e..HEAD ......... 0 arquivos
    TODO em done/ ........................... nao existe
    pytest tests/ -q ........................ 1164 passed, 2 skipped (exit 0)
    pytest --collect-only ................... 1166 (baseline 1127)
