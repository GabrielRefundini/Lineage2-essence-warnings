---
phase: 01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa
plan: 01
workstream: renda
subsystem: leitura-da-renda
status: complete
tags: [ocr, calibracao, glifos, tracer, gramatica]
requires: []
provides:
  - l2scanner.renda_leitura (RecusaDaRenda, ValorDaRenda, MOTIVO_*, _recusar, recortar, decimos_de_milesimo, _cruzar_as_escalas, exp_da_barra)
  - l2scanner.renda_modo (leitura unica por --imagem ou --janela)
  - Calibracao.renda_por_personagem, Calibracao.renda_moldes_da_barra, Calibracao.renda_do_personagem
  - tests/fixtures/renda/ (13 PNGs resgatados + calibracao_de_fixture.json)
affects:
  - l2scanner/calibracao.py
tech-stack:
  added: []
  patterns:
    - "modulo puro + modulo de modo: a seta aponta ferramenta -> puro"
    - "recusa nomeada com detalhe no dado, e nao so no log"
    - "cruzamento de escalas por ABSTENCAO, com o numero de escalas viajando junto do valor"
key-files:
  created:
    - l2scanner/renda_leitura.py
    - l2scanner/renda_modo.py
    - tools/resgatar_fixturas_da_renda.py
    - tests/test_renda_tracer.py
    - tests/test_calibracao_renda.py
    - tests/fixtures/renda/
  modified:
    - l2scanner/calibracao.py
decisions:
  - "O retangulo da adena do plano (1500,1360 200x32) foi REFUTADO por medicao antes do primeiro commit; vale 1540,1358 160x34"
  - "O digito da barra NAO tem uma largura so: 4, 5 ou 6 px na convencao de larguras_de_molde"
  - "A gramatica do EXP e ancorada dos DOIS lados, e ambiguidade (duas candidatas) recusa"
  - "A suite roda no Python global com o site-packages do .venv no PYTHONPATH: o .venv nao tem pytest"
metrics:
  duration: ~1 sessao
  completed: 2026-09-02
actuals:
  tokens: 78000
  tasks: 3
  commits: 4
---

# Phase 01 Plan 01: A fatia fina da leitura da renda — Summary

Um PNG resgatado de uma gravacao real entra e o EXP com quatro casas sai impresso, atravessando
calibracao validada, recorte com guarda, mascara de brilho com piso calibrado, duas escalas de
OCR, gramatica com trava e recusa nomeada — sem o jogo aberto.

## O que foi construido

### `l2scanner/renda_leitura.py` — o modulo puro

`RecusaDaRenda` (campo, motivo, detalhe), `ValorDaRenda` (campo, valor, escalas, texto), cinco
constantes `MOTIVO_*`, `_recusar`, `recortar`, `decimos_de_milesimo`, `_cruzar_as_escalas` e
`exp_da_barra`.

- **`recortar` confere antes de fatiar.** A armadilha esta presa por teste com a medicao ao lado:
  numa janela de altura 1392, `frame[1368 : 1368+26]` devolve **24 linhas**, sem levantar e sem
  avisar. Um EXP lido de 24 linhas e plausivel e errado.
- **`_cruzar_as_escalas` decide por ABSTENCAO**, com os quatro desfechos separados. A docstring
  carrega a refutacao inteira: por que a regra antiga (igualdade obrigatoria) recusaria o nivel de
  uma das instancias para sempre, **e** onde esta regra ja falhou — na adena, aceitando `106020` no
  lugar de `1.696.020` e `91` no lugar de `13.160.684`. Uma guarda que falhou uma vez e nao diz onde
  falhou e uma guarda que sera aplicada de novo no mesmo lugar.
- **O valor aceito carrega `escalas`**, e o comando marca visivelmente a leitura de uma escala so.

### `l2scanner/renda_modo.py` — a leitura unica

`--imagem` (que e o que torna a fatia verificavel sem o jogo) ou `--janela`, com `--personagem`
**obrigatorio** junto de `--imagem`. Codigos de saida com tabela escrita no topo: `0` leu, `1`
falha operacional, `3` recusa nomeada — porque "recusou" e "quebrou" precisam ser distinguiveis de
fora, e quem vai olhar o codigo de saida e a fase seguinte, nao um humano.

### `l2scanner/calibracao.py` — as duas chaves

`renda_por_personagem` e `renda_moldes_da_barra`, ambas opcionais com a `VERSAO_DO_ESQUEMA` intacta
em 2, mais `_conferir_as_chaves_da_renda` no arranque e o acessor `renda_do_personagem`, que
devolve a entrada daquele personagem ou **nada** — nunca a do vizinho.

O conjunto de moldes tem **tres** posicoes legitimas: ausente, completo e **incompleto**. O
arranque confere FORMA e nunca COMPLETUDE; quem confere completude e a leitura.

## Deviations from Plan

### 1. [Rule 1 — Bug medido] O retangulo da adena do plano estava errado, e caiu antes do primeiro commit

**Achado durante:** Tarefa 1, por correcao vinda do coordenador e **reconferida nesta arvore**.

O plano manda `barra_direita = 1500,1360 200x32`. Esse retangulo foi medido em **uma** fixtura,
cuja L-Coin era `9.790` — curta o bastante para terminar antes de `x=1500`. Isso nao era margem,
era sorte, o mesmo tipo de sorte que a banda de brilho de largura 1 ja tinha flagrado.

**Reconferido aqui**, com `segmentar_glifos_no_brilho` sobre as **quatro** fixturas de campo, nos
pisos 180/185/190 — e o resultado e **pior** do que o reportado: o retangulo antigo devolve um run
de largura **17 no MEIO** nas quatro, e nao apenas nas duas novas. E o icone da moeda de ouro
dentro do numero, e a peneira de forma da leitura por glifo recusaria em **todas**.

O que vale e `1540,1358 160x34`, e a contagem do meio bate com a verdade caractere por caractere:

| fixtura | larguras | meio | verdade |
| ------- | -------- | ---- | ------- |
| 00h45 faerlina | `[14, 4, 4, 1, 4, 4, 4, 1, 4, 4, 6, 15]` | 10 | `13,160,684` (10) |
| 00h45 yazalaque | `[14, 4, 1, 4, 4, 4, 1, 4, 4, 4, 15]` | 9 | `1,696,020` (9) |
| 09h30 faerlina | `[14, 4, 4, 1, 4, 4, 6, 1, 5, 4, 4, 15]` | 10 | `15,134,779` (10) |
| 09h30 yazalaque | `[14, 6, 1, 6, 4, 4, 1, 4, 4, 4, 15]` | 9 | — |

**Aplicado em:** `tools/resgatar_fixturas_da_renda.py`, `tests/fixtures/renda/calibracao_de_fixture.json`,
o bloco de comentario do campo em `l2scanner/calibracao.py` e um teste que afirma que o retangulo
**nao** e nenhum dos dois refutados. **Commit:** `7421323`.

### 2. [Rule 1 — Bug medido] O "digito de largura 5" tambem caiu, e as convencoes divergem

O digito desta fonte **nao tem uma largura so**: o `4`, o `7` e o `9` saem mais largos. Uma peneira
que exigisse UMA largura recusaria `15,134,779` inteiro.

**E ha uma divergencia de CONVENCAO que precisa ficar registrada, porque ja custou uma refutacao a
esta fase.** Medido aqui na convencao de `segmentar_glifos_no_brilho` (`fim - inicio`, a **mesma**
de `larguras_de_molde`, e portanto a que a peneira do `01-05` vai usar): **digito 4, 5 ou 6;
virgula 1; icones de ponta 14 e 15**. O `01-MEDICOES-DE-CAMPO.md` relata os mesmos runs numa
convencao **inclusiva** (5/6/7, 2, 15/16). As duas descrevem a mesma tela e diferem por um pixel.

Foi exatamente um numero sem convencao declarada — o `17` do M-I — que ja produziu uma refutacao
aqui. **Quem escrever a guarda do `01-05` precisa dizer em qual convencao esta.** Registrado no
comentario do campo em `calibracao.py`, no cabecalho do resgate e num teste
(`test_O_DIGITO_DESTA_FONTE_NAO_TEM_UMA_LARGURA_SO`) que falha se as larguras colapsarem num valor
so — para que a refutacao seja reescrita, e nao apagada.

### 3. [Rule 1 — Bug] Dois numeros que nunca estiveram na tela, achados pela Tarefa 3

Medidos contra a implementacao da fatia:

    decimos_de_milesimo("1234.5678%")            -> 2345678
    decimos_de_milesimo("EXP 8.0012% e 9.0012%") -> 80012

O primeiro e a gramatica casando **dentro** de um numero maior; o padrao nao e hipotetico, porque o
OCR desta arvore cola numero vizinho na frente o tempo todo (`76 EXP 80012% 592%` e leitura real).
O segundo e ambiguidade tratada como escolha: `re.search` devolve a primeira, e "a primeira" e uma
decisao tomada pela ordem em que o motor devolveu as palavras.

**Consertado** com ancora dos dois lados (`(?<!\d)` e `(?![\d.,])`) e `findall` sobre um conjunto.
**Commits:** `c43c950` (RED), `15e9496` (GREEN).

### 4. [Rule 3 — Ambiente] O `.venv` nao tem `pytest`, e a verificacao do plano nao roda como escrita

**Este e o unico ponto em que um comando do plano nao pode ser executado literalmente, e ele fica
escrito em vez de contornado em silencio.**

O plano manda `PYTHONPATH=. .venv/Scripts/python.exe -m pytest ...`. Medido:

    .venv/Scripts/python.exe -m pytest --version  ->  No module named pytest

O `.venv` de producao tem 15 distribuicoes (cv2, numpy, mss, winrt, windows-capture, discord) e
**nao** tem pytest — o que o proprio `tests/test_firewall_escopo.py` ja documenta: "o pytest deste
repo roda no Python GLOBAL, nao no .venv de producao". O global tem pytest 9.1.1 e **nao** tem as
bindings de OCR.

**Nada foi instalado no `.venv` do usuario.** Os dois interpretadores sao 3.12, entao a ponte
resolve sem tocar em nada:

    PYTHONPATH=".;<repo>/.venv/Lib/site-packages" python -m pytest tests/test_renda_tracer.py

Isso da pytest **e** OCR na mesma rodada, e e com ela que os **0 skipped** deste plano foram
obtidos. Sem a ponte, no Python global puro, as classes de OCR pulam pelo idioma de skip da casa —
e a razao do skip carrega o comando acima. O comando esta escrito no `RAZAO_DO_SKIP` do proprio
arquivo de teste, que e onde quem ve `skipped` vai procurar.

## Como cada criterio de aceitacao foi verificado

| criterio | resultado |
| -------- | --------- |
| tracer verde, **0 skipped** | `103 passed` (tracer + calibracao_renda), 0 skipped |
| comando com `--personagem` imprime EXP de 4 casas, sai 0 | `Faerlina  EXP 8,0012%`, exit 0 |
| comando **sem** `--personagem` sai != 0, sem traceback | exit 1, mensagem com o conserto |
| EXP do frame de campo da Faerlina == `80012` | verde |
| escalas 1 (abstencao) e 2 (acordo), no MESMO recorte | verde (pisos 150 e 160) |
| recorte fora do frame recusa + controle negativo | verde, mais o teste que prende a medicao do numpy |
| `renda_por_personagem` ausente carrega, versao intacta | verde |
| `renda_moldes_da_barra` nas TRES posicoes + malformado recusa | verde |
| piso de `barra_direita` na banda de GLIFO (180-190) | verde |
| dois personagens com retangulos de nivel distintos | verde |
| personagem ausente recusa e **nao** e a entrada de outro | verde |
| `ast.parse` + portao de pureza == 0 | verde |
| `ls tests/fixtures/renda/*.png` >= 10 | **13** |
| `recordings/` e o resgate ausentes do arquivo de teste | 0 e 0 |
| `fields(Calibracao)` no teste estrutural >= 2 | **5** |
| `test_calibracao_renda.py` >= 8 testes | **19** |
| `centesimos_de_moeda` ausente do modulo puro | 0 |
| `git diff --stat requirements.txt` vazio | vazio |
| `calibration.json` real intocado | intocado |
| suite completa | **4998 passed, 24 skipped** |

## A amarra estrutural foi MEDIDA, e nao apenas escrita

O plano pedia a amarra e o controle positivo. Como os dois passaram na primeira rodada (a
implementacao veio da Tarefa 1), a regra de fail-fast do TDD obrigou a investigar em vez de aceitar:
**a linha `"renda_por_personagem"` foi removida do `salvar`** e a suite rodou de novo.

- `tests/test_calibracao_renda.py` -> **6 vermelhos**
- `tests/test_calibracao_mercado.py` + `tests/test_calibracao_generica.py` -> **145 verdes**, com o
  campo sumindo em silencio

E exatamente a cegueira que a amarra existe para fechar, agora com numero. A linha foi restaurada
por `git checkout -- l2scanner/calibracao.py`.

## TDD Gate Compliance

- **Tarefa 2** (`tdd="true"`): o RED nao veio do teste, porque a implementacao e da Tarefa 1 por
  desenho do plano — ela e uma **amarra**, e a prova de que ela nao e vacua foi feita por injecao de
  defeito (acima). Commit `test(01-01)` sem `feat` par, o que e correto para um tripwire.
- **Tarefa 3** (`tdd="true"`): RED (`c43c950`, 2 vermelhos reais) -> GREEN (`15e9496`). Gate
  completo.

## Known Stubs

Nenhum. Nada nesta onda devolve valor fixo, lista vazia ou placeholder: todo caminho ou le pixel
real ou recusa com motivo nomeado.

## Deferred Issues (fora do escopo deste plano)

- **`tests/test_agenda.py` aborta a sessao do pytest de forma intermitente.** Ele levanta
  `KeyboardInterrupt` de proposito para sair do laco (`uma_volta_so`), e o pytest as vezes trata
  isso como parada de sessao — numa rodada parou em `188 passed`, noutra o arquivo passou inteiro
  (`145 passed`). **Pre-existente e sem relacao com esta fase**: reproduzido no Python global puro,
  sem nenhum import de `renda`. Enquanto durar, a suite completa se roda em duas partes.

## O que a onda 2 herda como contrato

- `renda_leitura._cruzar_as_escalas`, `decimos_de_milesimo`, `recortar(frame, regiao, *, campo=...)`
  e as constantes `MOTIVO_*` — o `01-02` e o `01-03` importam **estas** e nao escrevem uma segunda
  particao de desfechos.
- `Calibracao.renda_do_personagem(nome)` — o acessor unico, que devolve a entrada dele ou nada.
- O esquema das duas chaves, com `barra_esquerda` = EXP e `barra_direita` = adena (os nomes mentem;
  a mentira esta documentada em tres lugares, e quem renomear renomeia **as duas**).
- `tests/fixtures/renda/calibracao_de_fixture.json` **sem** `renda_moldes_da_barra`: quem funde os
  moldes nela e o `01-04`, na Tarefa 1 dele. O endereco esta escrito em
  `tests/fixtures/renda/LEIA-ME.md`.
- `l2scanner/renda_leitura.py` **nao** tem `_glifos_do_numero`: ela e do `01-05`, e o grep daquele
  plano continua devolvendo 0 aqui.

## Self-Check: PASSED

Arquivos criados conferidos em disco: `l2scanner/renda_leitura.py`, `l2scanner/renda_modo.py`,
`tools/resgatar_fixturas_da_renda.py`, `tests/test_renda_tracer.py`,
`tests/test_calibracao_renda.py`, `tests/fixtures/renda/` (13 PNGs + JSON + LEIA-ME).

Commits conferidos em `git log`: `7421323`, `b96ecd4`, `c43c950`, `15e9496`.
