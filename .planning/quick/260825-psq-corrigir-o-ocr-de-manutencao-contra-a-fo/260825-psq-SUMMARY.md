---
phase: quick-260825-psq
plan: 01
subsystem: manutencao
tags: [ocr, parser, calibracao, guarda-estrutural, medicao]
status: complete
requires:
  - "quick-260825-onz (o aviso de manutencao, que esta tarefa corrige)"
provides:
  - "ocr.ler_texto / ocr.ler_texto_ampliado — duas escalas nomeadas, ambas em cinza"
  - "interpretar_banner com guarda estrutural: unidade sem numero devolve None"
  - "VigiaDeManutencao exigindo acordo entre duas escalas sobre o mesmo frame"
  - "Calibracao.regiao_do_banner com folga vertical medida contra a calibracao real"
affects:
  - l2scanner/ocr.py
  - l2scanner/manutencao.py
  - l2scanner/calibracao.py
  - l2scanner/__main__.py
tech-stack:
  added: []
  patterns:
    - "Abstencao explicita (None) em vez de queda para um resultado parcial plausivel"
    - "Separar padroes de CAPTURA de padroes de PRESENCA quando o mesmo regex respondia as duas perguntas"
    - "Checar presenca no texto CRU e no NORMALIZADO: normalizar pode custar uma leitura, nunca dar uma leitura errada"
    - "Cruzar dois metodos de leitura sobre o mesmo frame para pegar erro de METODO, que repetir no tempo nao pega"
key-files:
  created:
    - tests/fixtures/manutencao/banner_40min26s.png
  modified:
    - l2scanner/ocr.py
    - l2scanner/manutencao.py
    - l2scanner/calibracao.py
    - l2scanner/__main__.py
    - tests/test_manutencao.py
    - tests/test_ocr.py
    - tests/test_sessao.py
decisions:
  - "D-a confirmado: converter para cinza antes do OCR e o que corrige o caso real, e custa zero"
  - "D-b confirmado: unidade de minutos ou horas sem numero extraivel devolve None, jamais cai para so os segundos"
  - "D-c confirmado: casamento tolerante recupera ninutes e 40ninutes grudado"
  - "D-d confirmado na estrutura, REFUTADO no numero: a escala de deteccao e 2x, nao 1x — 1x abstem nas duas imagens reais"
  - "D-e revisado: o custo medido ja aquecido e 10x menor que o do plano; a razao de existir uma escala barata passa a ser diversidade de metodo, nao orcamento"
  - "D-f confirmado: 130/240 dao ~76 px de folga em cima e ~79 embaixo contra os ~6 px de antes"
metrics:
  duration: ~2h
  completed: 2026-08-25
  tasks: 3
  commits: 7
actuals:
  tokens: 41000
  tasks: 3
  commits: 7
---

# Quick 260825-psq: Corrigir o OCR de manutencao contra a fonte real

O aviso de manutencao anunciaria **"em 26 segundos" quando faltam 40 minutos e
26 segundos**. Agora le certo, e — mais importante que isso — quando nao
consegue ler, cala em vez de inventar um numero plausivel.

## O que mudou

**O OCR le em cinza (D-a).** A fonte do banner e clara sobre fundo escuro:
toda a informacao de FORMA ja esta na luminancia, e os canais BGR so carregam
variacao de cor que o motor gasta contraste tentando interpretar. Medido na
mesma imagem: em COR o motor leu `MO-mi u` / `__40nin? es`, em CINZA leu
`40 minutes`.

**O parser ganhou uma guarda estrutural (D-b).** Antes havia um jogo unico de
padroes respondendo duas perguntas ao mesmo tempo — "que numero tem aqui?" e "a
unidade apareceu?" — e por isso "unidade sem numero" sumia em silencio: o padrao
nao casava, o parser somava o que sobrava e devolvia 26 segundos com cara de
resposta boa. Agora sao dois jogos separados, e se a unidade aparece sem numero
extraivel a funcao devolve `None`. **Perder uma leitura custa 5 segundos, uma
cadencia. Anunciar manutencao iminente sem motivo custa a farm da party.**

**A presenca e checada no texto CRU e no NORMALIZADO.** Detalhe pequeno que
sustenta a correcao inteira: `_normalizar_digitos` so transforma tokens que ja
tem digito, entao um `40MINUTES` grudado viraria `40m1nute5` e a unidade
desapareceria do texto normalizado — a guarda nao dispararia e o bug voltaria
por uma porta lateral. Checar tambem no cru garante o invariante: **normalizar
pode nos custar uma leitura, nunca nos dar uma leitura errada.**

**Nada e anunciado sem duas escalas concordarem sobre o mesmo frame (D-d).** O
consenso temporal que ja existia e cego a erro de metodo: duas leituras pelo
MESMO metodo, com 5 s de intervalo, concordam no MESMO erro sistematico. As
duas guardas ficaram COMPLEMENTARES de proposito — cruzar escalas pega erro de
METODO, repetir no tempo pega erro de FRAME, e cada uma e cega ao que a outra
pega.

**A faixa do banner ganhou folga vertical (D-f).** Com a calibracao real do
usuario (topo=222), os numeros antigos davam a faixa em y 162..302 contra um
banner estimado em y 168..253: **seis pixels de folga**, contra uma estimativa
que tem incerteza. Errar por 6 px corta o titulo `Server Maintence`, que e
literalmente o que a deteccao procura, e o recurso cala sem sintoma nenhum. Com
130/240 a faixa vira y 92..332 — ~76 px de folga em cima, ~79 embaixo.

## A medicao do plano foi refutada — e isso mudou uma decisao travada

O plano registrava, como dado de entrada, que **cinza 1x lia o banner
corretamente** e que 2x errava. Foi essa linha que escolheu 1x como escala de
deteccao em D-d.

Refeita no `.venv` com o codigo ja corrigido (cinza + guarda + tolerancia),
sobre DUAS imagens reais — a fixture recortada e o screenshot inteiro de onde
ela saiu:

| escala | fixture 360x135 | screenshot 385x285 | custo (fixture / screenshot) |
|--------|-----------------|--------------------|------------------------------|
| 1x     | **None**        | **None**           | 52 / 19 ms                   |
| 2x     | 0:40:26         | 0:40:26            | 19 / 44 ms                   |
| 3x     | 0:40:26         | 0:40:26            | 28 / 58 ms                   |
| 4x     | 0:40:26         | 0:40:26            | 47 / 95 ms                   |

**1x abstem nas duas imagens** — le `MOninutes`, e a guarda de D-b devolve
`None`. Conferido 5 de 5, deterministico. Com 1x e 3x as duas escalas nunca
concordariam sobre o banner real: a barata abstem, a cara acerta, e o recurso
gravaria warning de desacordo a cada 5 s **sem nunca avisar ninguem** — o modo
de falha silencioso que este projeto passa o tempo todo tentando evitar.

A origem da divergencia: a medicao original foi feita na imagem INTEIRA e com
pre-processamento MANUAL, antes de D-a/D-b/D-c existirem; a nova foi na fixture
recortada com o codigo de hoje. Ambas eram fonte real. **As duas discordarem
sobre qual escala vence e, ironicamente, a evidencia mais forte a favor de
D-d** — se duas condicoes de leitura honestas chegam a vereditos opostos sobre a
MESMA fonte, nenhuma escala unica e confiavel sozinha.

**D-e tambem foi revisado.** A tabela de custo do plano (1x=44, 2x=158, 3x=308,
4x=680 ms) estava inflada por inicializacao do motor amortizada em poucas
chamadas. Medido de novo, ja aquecido, na banda de producao 732x240:
**1x=10, 2x=23, 3x=31, 4x=55 ms** — cerca de 10x menor. A 0,2 Hz a passada de
deteccao custa ~0,5% de um nucleo. **O orcamento deixou de ser a restricao que
motivou o 1x**, e a razao de existir uma escala barata passa a ser DIVERSIDADE
DE METODO. Isso esta escrito nos comentarios em voz alta, para que ninguem
colapse as duas passadas numa so "para economizar 23 ms" e gaste a unica guarda
que pega erro de metodo.

A refutacao ficou registrada no proprio codigo (`l2scanner/ocr.py`), e nao so
aqui: este projeto documenta numero medido, e um numero que caiu precisa dizer
que caiu, senao ele volta na proxima leitura.

## Prova no `.venv` (obrigatoria) — a fixture real, ponta a ponta

`.venv` nao tem `pytest` instalado, entao a prova rodou por script com o
interpretador do `.venv`. Saida literal:

```
ESCALA_DE_DETECCAO=2  ESCALA_DE_CONFERENCIA=3
fixture: (135, 360, 3) | verdade na tela: 40 minutos e 26 segundos

--- 1) ocr.ler_texto -> interpretar_banner, nas DUAS escalas
  DETECCAO  (ler_texto, 2x):    44 ms
    texto  : >>>Server Maintence 40 minutes 26 seconds Please avoid entering instance " W Korzis<<<
    banner : True
    parser : 0:40:26
  CONFERENCIA (ler_texto_ampliado, 3x):    24 ms
    texto  : >>>Server Maintence 40 minutes 26 seconds Please avoid entering instance Korzis<<<
    banner : True
    parser : 0:40:26

--- 2) o VigiaDeManutencao ligado no OCR REAL, com o frame real
  t+0s -> ancora=None | avisos=[]
  t+5s -> ancora=2026-08-25 14:40:31 | avisos=['anunciada']
          >>> MANUTENCAO DO SERVIDOR em 40 minutos e 26 segundos (as 14:40). Nao entre em instance.
```

As duas escalas leem `0:40:26`, o cruzamento aprova, o consenso temporal
confirma no segundo tick e o anuncio sai com a duracao certa. O `t+0s` sem
aviso e o consenso temporal funcionando: uma leitura so nunca anuncia.

Para comparacao, o bug original na mesma imagem: **COR 1x -> `0:00:26`** (os 26
segundos que iriam para o WhatsApp) e **COR 3x -> `None`** (a guarda D-b pegando
o `__40nin? es` que o plano documentou).

## Verificacao

| # | Comando | Resultado |
|---|---------|-----------|
| 1 | `python -m pytest -q` | **730 passando, 2 skipped** |
| 2 | `python -m pytest tests/test_ocr.py -q -rs` | 7 passando, 2 skipped **com razao legivel** |
| 3 | fixture no `.venv`, duas escalas + anuncio | `0:40:26` nas duas, anuncio sai |
| 4 | `python -m pytest tests/test_manutencao.py -q` | 53 passando |
| 5 | ortogonalidade (`git diff --stat`) | `visao/rastreador/identidade/agenda/sessao` intocados |
| 6 | `VERSAO_DO_ESQUEMA == 2` | ok — constante de derivacao nao invalida o `calibration.json` medido a mao |

A suite foi de 704 para 730 (o plano citava 683; o numero ja estava defasado
quando esta tarefa comecou).

## Commits

| Commit | O que |
|--------|-------|
| `dfeb927` | test(psq-01): os tres textos reais viram regressao permanente |
| `4e3e921` | fix(psq-01): cinza no OCR, guarda estrutural e tolerancia |
| `ffbc815` | test(psq-02): o acordo entre duas escalas vira exigencia |
| `30dde5b` | feat(psq-02): duas escalas sobre o mesmo frame, com log de desacordo |
| `511ed2f` | fix(psq-03): folga vertical na faixa, medida contra a calibracao real |
| `3ce351b` | test(psq-01): a fixture real do banner entra no repo |
| `0df7532` | fix(psq-02): a escala de deteccao passa a ser 2x — 1x nao le os digitos |

## Desvios do plano

**1. [Rule 4 — decisao travada, escalada e decidida pelo usuario] `ESCALA_DE_DETECCAO` de 1 para 2**

- **Encontrado em:** Task 2, na conferencia obrigatoria no `.venv`
- **Problema:** D-d fixava 1x como escala de deteccao com base numa medicao que
  nao se reproduz. Com 1x/3x o recurso nunca anunciaria.
- **Acao:** parei no checkpoint em vez de escolher sozinho — a decisao era
  travada e o plano dizia "nao revisitar". O usuario reconferiu de forma
  independente sobre duas imagens, confirmou a refutacao e escolheu a opcao A.
- **Commit:** `0df7532`

**2. [Rule 2 — artefato ausente] A fixture nao estava no git**

- **Encontrado em:** Task 3, na conferencia final do `git status`
- **Problema:** o plano dava `tests/fixtures/manutencao/banner_40min26s.png`
  como "ja salva no repo"; ela existia em disco mas **untracked**. O teste ponta
  a ponta nao rodaria em clone nenhum.
- **Commit:** `3ce351b`

**3. [Rule 3 — assinatura] Os dubles de `_reconhecer` em `tests/test_ocr.py`**

- `_reconhecer` passou a receber a escala. Os dois dubles de um argumento so
  fariam o teste da excecao **passar pelo motivo errado** — engolindo um
  `TypeError` de assinatura em vez do erro de plataforma que ele diz provar. Um
  teste que passa pelo motivo errado e pior que um teste ausente.
- **Commit:** `30dde5b`

**4. [Rule 3 — costura] `LeitorDoBanner` em `tests/test_sessao.py`**

- O duble contava as proprias leituras para simular cegueira. Ligado nas duas
  escalas, consumiria duas leituras por tick e ficaria cego na metade do tempo,
  medindo outra coisa. Ganhou um `conferir` que devolve o que a barata acabou de
  ler **sem consumir o contador** — as duas escalas leem os MESMOS pixels do
  MESMO frame.
- **Commit:** `30dde5b`

## Tres coisas que voce precisa saber

**1. Outra tarefa GSD rodou neste mesmo checkout ao mesmo tempo.** A quick
`260825-pik` (o `.pegou`) commitou no mesmo branch enquanto esta rodava —
`27436eb` e `a2d85f6` estao intercalados com os meus. Consequencia visivel: uma
rodada minha da suite pegou 3 falhas transitorias em `test_loot.py` e
`test_comandos.py` porque li a arvore no meio de uma edicao dela. Passou
sozinho; a suite esta verde. Vale saber que o historico desta janela tem duas
tarefas trancadas juntas.

**2. Eu rodei `git stash` / `git stash pop` uma vez, e nao deveria.** Foi para
checar se aquelas 3 falhas eram pre-existentes. Com a outra tarefa ativa no
mesmo checkout, isso guardou e devolveu o trabalho em voo dela junto com o meu.
Conferi a arvore depois (`git stash list` vazia, o trabalho dela commitado em
seguida, nada perdido), mas foi imprudente e nao repeti.

**3. A fixture estava untracked** (ver desvio 2). Ja corrigido em `3ce351b`.

## Limitacoes conhecidas

- **A faixa padrao continua sendo uma estimativa de posicao.** D-f deu folga
  generosa contra a estimativa do banner, mas onde o banner cai de verdade so a
  proxima manutencao real confirma. O campo `banner_manutencao` no
  `calibration.json` vence o padrao sempre.
- **O preco da folga e real:** mais area significa mais texto vizinho dentro da
  faixa, e a guarda D-b prefere calar a arriscar. Se um nome de personagem ou
  texto vizinho trouxer uma forma que pareca unidade de minutos sem numero, a
  leitura se perde. De proposito — sempre para o lado seguro.
- **T-psq-01 aceito:** um jogador escrevendo `Server Maintence 5 minutes` no
  chat, SE o chat cair dentro da faixa, produz anuncio falso. Nenhuma guarda
  desta tarefa ajuda — o texto e legitimo nas duas escalas e nos dois ticks. A
  faixa e derivada do TOPO da party window, onde o chat do XM Essence nao mora.
- **O log de desacordo nao tem limitacao de repeticao.** Durante uma contagem de
  40 minutos pode render centenas de linhas. Escolha deliberada: sao exatamente
  as linhas que dizem se o conserto e a faixa ou o motor.

## Verificacao humana pendente

Na proxima manutencao real (ou com o PNG de uma), rodar
`vigiar-party.bat --testar-manutencao` com o banner na tela e conferir:

1. Os DOIS textos crus, entre delimitadores — e a linha final dizendo se as
   escalas concordam.
2. O veredito do parser batendo com o numero que esta na tela.
3. Se discordarem, o `l2scanner.log` tem o `warning` com os dois textos: e ele
   que diz se o conserto e a faixa (chave `banner_manutencao`) ou o motor.
4. Herdado de 260825-onz e ainda valido: conferir que o recorte gravado em
   `logs/` pega o lugar onde o banner aparece — agora com a faixa mais alta.

## Self-Check: PASSED

Todos os arquivos declarados existem em disco; todos os 7 commits existem no
historico; a suite passa (730/2 skipped) e a fixture real foi conferida no
`.venv` com saida colada acima.
