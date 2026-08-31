---
phase: 04-modo-mercado-an-lise-e-console
plan: 05
subsystem: lancadores
tags: [bat, lancador, dois-cliques, mira-da-janela, ocr, receita, toml, config-disputado]
status: complete

requires:
  - phase: 04-modo-mercado-an-lise-e-console
    plan: 04
    provides: "`ler_receitas`, `Receita`, `ComponenteDaReceita` e `_EXEMPLO_DA_RECEITA` (a forma de tabela inline) no fim de `l2scanner/config.py`"
  - phase: 04-modo-mercado-an-lise-e-console
    plan: 01
    provides: "`--mercado` no `__main__.py`, com a recusa `--mercado exige --janela`, e `laco_do_mercado`"
provides:
  - "`vigiar-mercado.bat` — a terceira invocacao com dois cliques, com mira por personagem e sem nenhum echo depois da execucao"
  - "`tests/test_vigiar_mercado_bat.py` — 11 guardas sobre o texto do `.bat`, todos com controle negativo medido"
  - "O bloco `[[receita]]` comentado no FIM do `config.toml`, com as cinco limitacoes da margem por escrito"
affects: [DETC-02, ANAL-04]

actuals:
  tokens: 5001
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Bloco de erro ACIMA da linha de execucao, com `goto` por cima: torna ESTRUTURAL (e nao dependente de guarda) a promessa de nao imprimir nada depois de o programa rodar"
    - "`for /f` sem uma unica aspa simples dentro do `-c`: o cmd recorta o comando entre aspas simples, e um apostrofo no fonte Python encerraria o comando no meio. O valor variavel entra por `sys.argv[1]`"
    - "Controle negativo por mutacao para cada guarda de texto: oito mutantes, cada um morto pelo teste que o descreve"
    - "Diff puramente aditivo no fim de arquivo disputado, com a checagem de zero remocoes calibrada por controle negativo antes de confiar nela"

key-files:
  created:
    - vigiar-mercado.bat
    - tests/test_vigiar_mercado_bat.py
  modified:
    - config.toml

key-decisions:
  - "A MIRA DO `.bat` VEM DA CHAVE `[jogo] personagem`, e nao de `--janela` pelado. NAO ESTAVA NO PLANO, que dizia 'na mesma forma que o lancador da party usa --janela'. A razao e medida: esta maquina roda DUAS instancias do jogo, e `--janela` sem valor so resolve sozinho quando ha UMA janela aberta (fora isso ele depende de `cal.janela` estar gravado). Com duas janelas e sem `cal.janela`, o `__main__` enumera, acha duas e RECUSA — e um lancador de dois cliques que morre pedindo uma linha de comando nao e um lancador"
  - "O SUFIXO DO TITULO NAO E ESCRITO NO `.bat`: ele vem de `cliente.SEPARADOR` e `cliente.NOME_DO_CLIENTE`, no mesmo processo que le a chave. Uma segunda copia de ' - XM Essence' num arquivo que ninguem testa envelheceria sozinha"
  - "O `PERSONAGEM_PADRAO` E UMA LINHA VISIVEL E EDITAVEL no topo do `.bat`, e PERDE para a chave do `config.toml`. O usuario pediu 'padrao Yazalaque' explicitamente; a doutrina do projeto (`escolher_janela_do_jogo` sem valor padrao, `config.toml` do repositorio sem personagem de ninguem) e sobre o FONTE e sobre o `config.toml`, e continua intacta — `test_o_arquivo_do_repositorio_nao_carrega_o_personagem_de_ninguem` segue verde"
  - "SEM TITULO RESOLVIDO O LANCADOR RECUSA, e nao roda pelado. Medido em bancada `cmd`: com o TOML quebrado o `for /f` nao produz linha nenhuma e a variavel fica indefinida. Rodar assim passaria um `--janela` vazio adiante"
  - "OS BLOCOS DE ERRO FICAM ACIMA DA LINHA DE EXECUCAO, com um `goto executar` por cima. Nao e estilo: e o que faz o `.bat` satisfazer 'nada e impresso depois da execucao' por ESTRUTURA em vez de por disciplina. O `calibrar-mercado.bat` precisou de uma guarda `if errorlevel` porque tinha bloco de sucesso; este nao tem bloco de sucesso nenhum, porque o resumo da sessao sai do proprio programa, que e quem sabe o que aconteceu"
  - "A SONDA DE DEPENDENCIAS INCLUI O OCR (`winrt.windows.media.ocr`, `winrt.windows.graphics.imaging`), copiada do `vigiar-party.bat`. E o buraco medido em campo em 2026-08-31: o modo rodado pelo Python global recusou por falta de OCR. Sem OCR o modo mercado nao sobe, entao a sonda que ja existia na party e exatamente a sonda certa aqui"
  - "O BLOCO DO `config.toml` E CONTIGUO, separado por linhas `#` e nao por linha em branco — o padrao literal do `[mercado] watchlist` e do `[jogo] personagem` logo acima. Comentado, ele se descomenta como UMA unidade; a forma com sub-blocos `[[receita.componente]]` viraria quatro pedacos soltos que o usuario descomenta pela metade sem perceber"
  - "O EXEMPLO E O `_EXEMPLO_DA_RECEITA` do 04-04, literal. Inventar um segundo formato criaria duas verdades sobre a mesma sintaxe — uma na mensagem de recusa e outra no arquivo que o usuario edita"

patterns-established:
  - "Quando um criterio de verificacao usa `git diff -- X` (working tree), ele fica CEGO depois do commit. Medir o controle negativo ANTES de confiar no rc, e acrescentar a comparacao contra a base do plano (`git diff <base>..HEAD -- X`), que e a unica que sobrevive ao commit"
---

# Fase 4 Plano 5: `vigiar-mercado.bat` e o `[[receita]]` comentado — Summary

A terceira invocacao ganhou lancador de dois cliques que mira o personagem certo entre as
duas instancias, e o `config.toml` ganhou o formato do `[[receita]]` documentado onde o
usuario o escreve — 61 linhas acrescentadas, zero removidas, num arquivo disputado.

## O que foi entregue

### Task 1 — `vigiar-mercado.bat` (commit `2fb5d34`)

O lancador do mercado, no molde do `vigiar-party.bat`: busca do Python pelo **caminho
completo** (nunca o nome do comando), recusa do stub da Microsoft Store por substituicao de
string nativa do cmd, montagem do `.venv` na primeira execucao, sonda de dependencias novas
por import, e o `%*` no fim.

**Tres coisas que ele faz diferente do lancador da party, e todas por um motivo medido:**

1. **A sonda de dependencias inclui o OCR.** `winrt.windows.media.ocr` e
   `winrt.windows.graphics.imaging` entram na linha de import. Sem OCR o modo mercado **nao
   sobe** (`mercado_modo.py:245-252`), e foi exatamente esse o tropeço de campo de
   2026-08-31.
2. **A mira vem da chave `[jogo] personagem`.** Um `for /f` chama
   `ler_personagem_do_jogo()` pelo `.venv` (o `config.local.toml` vence, como sempre) e
   compoe o titulo com `cliente.SEPARADOR` + `cliente.NOME_DO_CLIENTE`. Sem a chave, cai no
   `PERSONAGEM_PADRAO` escrito em uma linha visivel no topo do arquivo.
3. **Nenhum `echo` depois da linha de execucao.** Os blocos `:erro_venv` e `:erro_deps`
   moram **acima** dela, com um `goto executar` por cima.

**Medido em bancada `cmd`** (um `.bat` de bancada, apagado depois) — os tres desfechos da
mira:

| Estado do `config` | `%JANELA%` resolvido |
|---|---|
| sem a chave `[jogo] personagem` | `Yazalaque - XM Essence` (o padrao) |
| `config.local.toml` com `personagem = "Faerlina"` | `Faerlina - XM Essence` (a chave vence) |
| TOML quebrado | vazio -> o lancador **recusa** com `exit /b 1` |

### Task 2 — o `[[receita]]` comentado no fim do `config.toml` (commit `a202f10`)

61 linhas acrescentadas, **zero removidas**, todas comentadas ou em branco, no fim do
arquivo. Cabecalho explicativo + exemplo, contiguos, no padrao literal do `[mercado]
watchlist` e do `[jogo] personagem`.

**As cinco limitacoes da margem estao por escrito**, porque nenhuma delas e visivel no
numero: os dois lados sao **pedidos** e nao transacoes; o numero e **bruto** (ignora a
comissao do World Exchange e a chance de falha do craft); a conta usa o **unitario** e nao
lida com lote minimo; **a oferta pode ja ter sido comprada**; e o programa **nao conhece o
crafting do jogo**, entao receita errada produz numero bem formatado e falso. Mais: `rende` e
obrigatorio (e por que), o nome tem de ser exatamente o da tela, um nome ambiguo quebra a
margem listando as candidatas, e **sem bloco nenhum a margem simplesmente nao aparece**.

## Cada `<automated>` do plano, com o resultado real

### Task 1

| Criterio | Como escrito | Resultado real |
|---|---|---|
| `pytest tests/test_vigiar_mercado_bat.py tests/test_calibrar_mercado_bat.py -x -q` | literal | **17 passed** (11 novos + 6 do irmao) |
| `test -z "$(git diff --stat -- vigiar-party.bat)" \|\| REPROVADO` | literal | **rc=0** |
| `test -f vigiar-mercado.bat` | literal | **rc=0** |
| `test -z "$(git diff -- requirements.txt)" \|\| REPROVADO` | literal | **rc=0** |

### Task 2

| Criterio | Como escrito | Resultado real |
|---|---|---|
| `pytest tests/test_bosses.py tests/test_mira_da_janela.py tests/test_calibracao_generica.py -x -q` | literal | **145 passed** |
| `tomllib.loads(config.toml)` | literal | **rc=0**, "config.toml parseia" |
| `test "$(git diff --numstat -- config.toml \| cut -f2)" = "0" \|\| REPROVADO` | literal, **antes do commit** | `numstat = 61 0` -> **rc=0** |
| toda linha `+` comentada ou em branco | literal | **rc=0** |
| exemplo descomentado -> `tomllib` -> `ler_receitas` | comando escrito para o criterio | **1 receita**: `Dragon Belt`, `rende=1`, `Common Aztac x5`, `Leonard x20` |
| `grep -c 'receita' config.toml` | literal | **7** |
| `test -z "$(git diff --stat -- l2scanner/)" \|\| REPROVADO` | literal | **rc=0** |

### O bloco `<verification>` final

| # | Como escrito | Resultado real |
|---|---|---|
| 1 | `pytest test_vigiar_mercado_bat + test_bosses + test_mira_da_janela + test_calibracao_generica -x -q` | **156 passed** |
| 2 | suite inteira, Python global | **3114 passed, 23 skipped** |
| 3 | `test "$(git diff --numstat -- config.toml \| cut -f2)" = "0"` | **rc=1 — FALSO NEGATIVO**, ver abaixo |
| 4 | `test -z "$(git diff --stat -- rastreador.py visao.py vigiar-party.bat)"` | **rc=0** |
| 5 | `test -z "$(git status --porcelain calibration.json)"` | **rc=0** (o arquivo nem existe nesta arvore) |
| 6 | `test -z "$(git diff -- requirements.txt)"` | **rc=0** |

## Criterios que se revelaram cegos ou insatisfaziveis, e o discriminante que entrou ao lado

Nenhum criterio foi trocado. Cada um foi rodado **como escrito**, o resultado real esta na
tabela acima, e o discriminante entrou **ao lado**, com controle negativo medido.

### 1. O criterio de zero remocoes vira FALSO NEGATIVO depois do commit

`test "$(git diff --numstat -- config.toml | cut -f2)" = "0"` compara a **working tree**.
Com o `config.toml` ja commitado, `git diff --numstat` sai **vazio**, `cut -f2` sai
**vazio**, e `test "" = "0"` e **falso** — o criterio grita `REPROVADO: config.toml teve
linhas removidas` justamente quando nada foi removido.

- **Rodado antes do commit (o momento em que ele mede o que diz medir): `numstat = 61 0`,
  rc=0.**
- **Discriminante que sobrevive ao commit:**
  `test "$(git diff --numstat 460d1bc..HEAD -- config.toml | cut -f2)" = "0"` -> `61 0`,
  **rc=0**.
- **Controle negativo medido:** com uma linha existente removida a mao, o mesmo comando
  reprovou com rc=1 e a mensagem certa. **O criterio nao e vacuo — ele so e cego depois do
  commit.** No mesmo estado, o criterio de "toda linha acrescentada esta comentada" saiu
  rc=0 e o `tomllib.loads` saiu rc=0: os dois sao cegos a remocao exatamente como o plano
  avisou.

### 2. Os criterios `test -z "$(git diff -- X)"` sao cegos depois do commit

Vale para `vigiar-party.bat`, `requirements.txt`, `l2scanner/` e os arquivos proibidos do
bloco final. Todos saem rc=0 com a arvore limpa, tendo mudado ou nao. **A comparacao contra
a base do plano entrou ao lado de cada um** (`git diff --stat 460d1bc..HEAD -- X`), e as
cinco sairam vazias.

**Controle negativo medido:** acrescentei uma linha ao `vigiar-party.bat` e rodei o criterio
literal — ele reprovou com rc=1. Restaurado em seguida (`git status` limpo).

### 3. Nenhum guarda novo e vacuo — oito mutantes, oito mortes

Todo guarda de `tests/test_vigiar_mercado_bat.py` foi calibrado por mutacao do proprio
`.bat`, com o original restaurado byte a byte ao fim:

| Mutante | Quem o matou |
|---|---|
| `echo` acrescentado depois da execucao | `test_nenhum_echo_depois_da_execucao_fica_fora_de_guarda_de_errorlevel` |
| `--mercado` tirado da linha de execucao | 6 testes (a ancora inteira cai) |
| `--janela` pelado | `test_o_janela_vai_com_valor_e_nao_pelado` |
| `--replay` entrando pelo lancador | `test_o_bat_nao_carrega_flag_de_destino_de_arquivo` + o da linha de execucao |
| `echo` mandando rodar a party | `test_nenhum_echo_manda_rodar_o_lancador_da_party` |
| acento no texto | `test_o_bat_e_ascii_puro` |
| mira por nome escrito a mao | `test_a_mira_vem_da_chave_do_config_e_nao_so_de_um_nome_escrito_aqui` |
| recusa por mira nao resolvida removida | `test_o_lancador_recusa_quando_nao_consegue_montar_a_mira` |

**GUARDAS VACUOS: nenhum.**

## A suite, com a base deste worktree

| Momento | Resultado |
|---|---|
| **Base do worktree, antes de tocar em nada** (`460d1bc`) | **3103 passed, 23 skipped** |
| Depois das duas tasks | **3114 passed, 23 skipped** |
| **Delta** | **+11 passed, 0 regressao** |

Os +11 sao exatamente os testes de `tests/test_vigiar_mercado_bat.py`. O absoluto diverge do
`3026 passed, 2 skipped` citado como referencia da `main` porque este worktree ja carrega o
04-04 mesclado e os commits que o outro agente pousou na `main`; o que importa e o **delta**.

`tests/test_bosses.py` **passou** — nao foi preciso investigar autoria.
`tests/test_agenda.py` continua fora da corrida pelo `KeyboardInterrupt` proposital da linha
1141.

## Numeros que o briefing pediu explicitamente

- **Linhas REMOVIDAS do `config.toml`: `0`.** (`git diff --numstat 460d1bc..HEAD --
  config.toml` -> `61	0	config.toml`.) A checagem de remocao foi calibrada com controle
  negativo antes de eu confiar nela.
- **Pytest:** base do worktree **3103 passed, 23 skipped** -> **3114 passed, 23 skipped**
  (**+11**).
- **Diff total do plano contra a base:** 3 arquivos, **482 insercoes, 0 delecoes**.

## Deviations from Plan

### 1. [Rule 2 — funcionalidade critica ausente] A mira por personagem no `.bat`

- **Onde:** Task 1.
- **O que o plano dizia:** "A linha de execucao chama o modulo com `--janela` e `--mercado`,
  na mesma forma que o lancador da party usa `--janela`" — ou seja, `--janela` pelado.
- **Por que isso nao serve:** `__main__.py:2506-2534` so resolve `--janela` pelado por
  `cal.janela`; sem ele, enumera as janelas do jogo e **recusa quando ha mais de uma**. Esta
  maquina roda **duas** instancias. Um lancador de dois cliques que morre pedindo uma linha
  de comando nao entrega DETC-02.
- **O que foi feito:** o `.bat` resolve o titulo pela chave `[jogo] personagem` (o mesmo
  precedente do `calibrar --auto`), com `PERSONAGEM_PADRAO` como ultimo recurso e o `%*` no
  fim como saida de emergencia (o ultimo `--janela` vence no argparse).
- **Arquivos:** `vigiar-mercado.bat`, `tests/test_vigiar_mercado_bat.py`.
- **Commit:** `2fb5d34`.

### 2. [Rule 2] Os blocos de erro subiram para ACIMA da linha de execucao

- **Onde:** Task 1.
- **Por que:** copiar a ordem do `vigiar-party.bat` (blocos `:erro_*` depois da execucao)
  deixaria `echo`s textualmente posteriores a linha de execucao, e o criterio de aceitacao
  pede que **nenhum** `echo` posterior fique fora de guarda de `errorlevel`. Subir os blocos
  torna a promessa **estrutural** em vez de dependente de leitura.
- **Commit:** `2fb5d34`.

### 3. [Rule 2] Guardas alem dos quatro criterios de aceitacao

Entraram tres testes que o plano nao pediu, todos com controle negativo: `.bat` em ASCII
puro (acento sai como lixo na codepage do cmd), a linha de execucao carregando **so** as duas
flags do modo, e nenhum `echo` mandando rodar o `vigiar-party.bat` — este ultimo prende, no
lancador certo, o conselho torto medido em campo.

### 4. NAO FEITO, de proposito: a mensagem de recusa por OCR continua apontando o `.bat` errado

`l2scanner/mercado_modo.py:248` ainda diz *"Rode pelo .venv (vigiar-party.bat ja faz
isso)"*. **Consertar isso esta fora do `files_modified` deste plano**, e o proprio criterio de
aceitacao da Task 2 (`git diff --stat -- l2scanner/` vazio) proibe tocar em `l2scanner/`.
Registrado em `deferred-items.md`; e um `/gsd-quick` de uma linha.

## Auth Gates

Nenhum.

## Known Stubs

Nenhum. Os dois artefatos sao completos e o bloco do `config.toml` e documentacao inteira.

## Deferred Issues

1. **A recusa por OCR do `mercado_modo.py` aponta o `vigiar-party.bat`** — ver Desvio 4.
2. **O criterio "o exemplo comentado parseia quando descomentado" e um comando de uma vez
   so, e nao um teste duravel.** O plano o especificou como comando e o `files_modified` nao
   inclui `tests/test_mercado_receitas.py`, entao ele foi rodado e reportado, nao codificado.
   Se alguem reescrever o comentario do `config.toml` e quebrar o exemplo, nada cai.

## Threat Flags

Nenhuma superficie nova. O `.bat` nao abre porta de arquivo (ha guarda prendendo a ausencia
de flag de destino), nao instala nada alem do `requirements.txt` inalterado, e nao envia
input ao jogo. O `config.toml` ganhou so comentario.

## Restricoes da fase — conferidas

| Restricao | Estado |
|---|---|
| `rastreador.py` e o gate de brilho em `visao.py` intocados | **vazio** contra a base |
| `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`, `__main__.py`, `tests/test_bosses.py` intocados | **vazio** contra a base |
| FIRE-01: nenhuma dependencia nova, `rich` fora | `requirements.txt` **vazio** contra a base |
| `calibration.json` nunca commitado | nao existe nesta arvore; **vazio** contra a base |
| `.mercado/` nao escrita | nenhum teste novo escreve em disco fora de arquivo temporario proprio |
| `recordings/` somente-leitura, sem glob | nao foi tocada |
| `git commit --amend` | nunca usado |
| Varredura do censo | nao rodada |

## Self-Check: PASSED

- `vigiar-mercado.bat` — FOUND
- `tests/test_vigiar_mercado_bat.py` — FOUND
- `config.toml` com o bloco `[[receita]]` — FOUND (`grep -c 'receita'` = 7)
- commit `2fb5d34` — FOUND
- commit `a202f10` — FOUND
