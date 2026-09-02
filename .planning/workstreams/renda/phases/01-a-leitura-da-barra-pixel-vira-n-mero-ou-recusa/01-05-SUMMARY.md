---
phase: 01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa
plan: 05
workstream: renda
subsystem: leitura-da-renda
status: complete
tags: [glifos, calibracao, moldes, peneira, checkpoint]
requires:
  - l2scanner.renda_leitura (01-01)
  - Calibracao.renda_moldes_da_barra (01-01)
  - tests/fixtures/renda/ (01-01)
provides:
  - l2scanner.renda_leitura._glifos_do_numero (a peneira de forma UNICA da fase)
  - l2scanner.renda_leitura.GlifosDoNumero, RecusaDeForma, MOTIVO_DA_FORMA, MOTIVO_DO_RUN_ANORMAL
  - l2scanner.calibrar_renda_moldes (cortador de moldes da fonte da barra)
  - calibrar-renda-moldes.bat
affects:
  - tests/test_calibrar_nao_apaga_identidades.py (portao de escritores da calibracao)
tech-stack:
  added: []
  patterns:
    - "peneira de forma UNICA no modulo puro, consumida pela ferramenta e pela leitura"
    - "limite derivado dos moldes por parametro, sem default; None recusa em vez de adivinhar"
    - "guarda de geometria contra a DOMINANTE do conjunto gravado, nunca contra literal"
    - "conjunto incompleto grava e ANUNCIA por nome, com o campo onde procurar"
key-files:
  created:
    - l2scanner/calibrar_renda_moldes.py
    - calibrar-renda-moldes.bat
    - tests/test_renda_glifos.py
    - tests/test_calibrar_renda_moldes.py
  modified:
    - l2scanner/renda_leitura.py
    - tests/test_calibrar_nao_apaga_identidades.py
decisions:
  - "A faixa da fonte da barra e 9 e a bruta e 16 na convencao do codigo (faixa[1]-faixa[0]); o 10/17 do M-K e o mesmo pixel de convencao do M-P, agora na ALTURA"
  - "A geometria sozinha NAO separa mais os moldes do mercado dos da barra: ambos altura 9, larguras (1,4,6) contra (1,4,5,6). O que separa e a curva tonal"
  - "O limite de glifo unico da PRIMEIRA rodada vem de limite_de_arranque(runs) — a maior largura fora das pontas — e nunca de uma constante"
  - "O multiplicador do run anormal e uma CONTAGEM DE GLIFOS em unidades do limite recebido, e nao um pixel"
  - "piso_de_leitura e margem_de_leitura sao resolvidos por ordem (CLI > rodada anterior > par medido do mercado, EMPRESTADO e anunciado) e nunca inventados"
  - "O conjunto 0-9 fecha com as QUATRO fixturas de adena ja versionadas: o `5` e o `7` estao em `15.134.779` (M-O). Nao e preciso recordings/ nem outro campo"
metrics:
  duration: ~1 sessao
  completed: 2026-09-02
actuals:
  tokens: 35800
  tasks: 2
  commits: 5
---

# Phase 01 Plan 05: A peneira de glifos e o cortador de moldes — Summary

A peneira de forma da barra existe uma vez so, no modulo puro, e devolve as corridas do numero
entre os dois icones com a faixa de linhas **recomputada depois do descarte**; e existe um cortador
que colhe de qualquer campo da barra, propoe ao humano, recusa geometria errada nos dois sentidos e
grava um conjunto incompleto **anunciando por nome** o que falta e onde procurar — sem nunca
inventar, copiar ou completar um molde.

**As Tarefas 1 e 2 estao completas. A Tarefa 3 e um `checkpoint:human-action` com gate
`blocking-human` e continua ABERTA** — ver a secao final.

## O que foi construido

### Tarefa 1 — `renda_leitura._glifos_do_numero`, a peneira de forma UNICA da fase

`_glifos_do_numero(mascara, faixa, runs, *, limite)` -> `GlifosDoNumero | RecusaDeForma`.

- **Tres regras posicionais.** Um run largo em cada PONTA e icone e sai; um run largo no MEIO
  **derruba o recorte** com o motivo nomeado, em vez de ser descartado (descartar apagaria um digito
  e devolveria um numero mais curto e plausivel); zero ou dois numa ponta e recusa de forma.
- **A quarta regra, que e o M-K virado codigo:** a faixa devolvida e **recomputada sobre as colunas
  sobreviventes** ao descarte. `segmentar_glifos_no_brilho` devolve UMA faixa para o retangulo
  inteiro, e foi o icone dentro do recorte que contaminou a altura do M-I.
- **A guarda do run anormalmente largo.** Um run que caberia `SIMBOLOS_POR_RUN_ANORMAL` glifos da
  largura maxima e recusado com a largura nomeada e **nunca fatiado**. O multiplicador e uma
  **contagem de glifos** medida em unidades do `limite` recebido — nenhum pixel desta fonte entra
  como constante.
- **`limite` e somente-nomeado e sem default.** `None` (o que `limite_de_glifo_unico` devolve sobre
  um conjunto vazio) **recusa com motivo nomeado** em vez de adivinhar.
- A convencao de largura vai **declarada** como EXCLUSIVA no cabecalho, com a tabela de traducao do
  M-P ao lado.

### Tarefa 2 — `calibrar_renda_moldes`, o cortador dos moldes da barra

- `--campo adena|lcoin|bonus|exp`; `adena` e `exp` usam o retangulo calibrado por personagem,
  `lcoin` e `bonus` exigem `--recorte` e `--piso` (inventar um retangulo para eles seria plantar
  coordenada no fonte).
- `--recorte inteiro` trata o arquivo como ja sendo o recorte — e o que torna a ferramenta
  verificavel contra as **fixturas versionadas**, sem `recordings/`.
- A peneira e **importada** (`grep -c "def _glifos_do_numero"` no cortador = **0**; referencias = 3),
  e o recorte que ela recusa e **pulado com o frame e o motivo nomeados**.
- **A guarda de altura compara contra a altura DOMINANTE dos moldes ja gravados**, nunca contra um
  literal — e e por isso que a correcao de numero descrita abaixo custou uma docstring e nao uma
  reescrita. Sem moldes, a guarda se cala (inventar uma altura de referencia fixaria a geometria por
  adivinhacao).
- `limite_de_arranque(runs)` resolve a primeira rodada — um cortador que exigisse moldes para cortar
  moldes nunca sairia do zero. O ponto cego dele vai escrito na docstring.
- A cobertura sai **por nome** e diz **em que campo da barra** cada faltante foi medido
  (`ONDE_CADA_ROTULO_FOI_MEDIDO`, tabela do M-J/M-K/M-L/M-O). `cobertura_da_barra` delega a
  `cobertura_dos_glifos` e tira as duas PALAVRAS de sufixo, que sao da grade do mercado e nao
  existem nesta barra.
- Conjunto incompleto **grava e anuncia**, com a consequencia (a adena vai RECUSAR) e o conserto
  NOVO (varrer outro campo), nunca "esperar o farm".
- Matriz de confusao antes de gravar; nao separaveis -> `RendaNaoCalibravel("nada foi gravado: os
  glifos precisam ser separaveis primeiro")`, com o par nomeado.
- `gravar_os_moldes` faz load-mutate-save de **uma** chave de topo, com `folga_de_cola: null`.
- `--propor` roda a varredura, imprime frame a frame e **nao escreve**.

### `calibrar-renda-moldes.bat`

Dialeto B. O cabecalho `REM` diz **quando rodar**, e o texto e diferente de todos os outros `.bat`
desta casa: *rode de novo, apontando outro `--campo`, quando a saida disser que faltam rotulos*.

## A medicao que este plano produziu, e ela derruba um numero do proprio plano

### A altura da fonte cai mais UM pixel — e e a mesma armadilha do M-P, agora na ALTURA

Reconferido sobre as **quatro fixturas versionadas** (`tests/fixtures/renda/*__barra_direita.png`),
nos pisos **180, 185 e 190** — doze medicoes, resultado **invariavel**:

| grandeza | medido aqui (`faixa[1] - faixa[0]`) | publicado no M-K (inclusiva) |
| --- | --- | --- |
| faixa BRUTA (com os icones dentro) | **16** | 17 |
| faixa PENEIRADA (depois do descarte) | **9** | 10 |
| larguras de run no meio | **{1, 4, 5, 6}** | {2, 5, 6, 7} |

Sao os mesmos pixels. O comportamento que o M-K descreve — a faixa encolhendo do icone para a
fonte — esta **integralmente confirmado**; o que caiu foi o valor absoluto, pelo mesmo pixel de
convencao que o M-P ja tinha achado nas larguras.

**Consequencia, e ela e maior que a correcao.** O plano manda "a guarda de altura compara contra
10". Uma guarda escrita contra 10 recusaria **todo** molde legitimo desta barra — que e, ao pixel,
o modo de falha que o M-K existia para evitar. Aqui isso nao acontece porque **nenhuma guarda desta
onda compara contra um literal**: `conferir_a_altura` compara contra a dominante do conjunto
gravado, e `_glifos_do_numero` recomputa em vez de conferir. A correcao custou docstring.

**E ela enfraquece o argumento do M-I, o que precisa ficar escrito.** Os moldes de digito do
mercado sao `altura: 9` e `larguras_de_molde` sobre eles da `(1, 4, 6)`. A barra da **9** e
`{1, 4, 5, 6}`. **A geometria sozinha nao separa mais os dois conjuntos.** O que continua separando
esta medido e ja estava escrito no repositorio: a **curva tonal** em que cada conjunto foi cortado
(bloco "A COR DA TINTA" de `mercado_leitura` — o mesmo `0` desenhado com pico mais alto vira anel
FECHADO e casa com o `8` a 0,7242 contra 0,5976, falha ABERTA). A proibicao de reusar continua
valendo; o argumento dela mudou de eixo, e isso vai registrado no fonte do cortador em vez de o
numero ser trocado em silencio.

### A prova de campo do caminho inteiro, sem `recordings/`

`--propor` sobre as cinco fixturas de adena, piso 185, com a calibracao de fixtura:

| fixtura | glifos peneirados | verdade de campo (M-O) |
| --- | --- | --- |
| `campo_faerlina_f000__barra_direita.png` | **10** | `13.160.684` -> 10 |
| `campo_yazalaque_f001__barra_direita.png` | **9** | `1.696.020` -> 9 |
| `segundo_cenario_faerlina__barra_direita.png` | **10** | `15.134.779` -> 10 |
| `segundo_cenario_yazalaque__barra_direita.png` | **9** | — |
| `aba_para_calibrar_f000__barra_direita.png` | **9** | — |

Codigo de saida 0, e o `calibration.json` alvo **identico** depois da rodada.

### O conjunto 0-9 fecha com as QUATRO fixturas de ADENA — sem outro campo e sem farm

O M-L derrubou o bloqueio apontando bonus e L-Coin. Medido aqui, o caminho e ainda mais curto: a
adena da Faerlina de 09h30 e **`15.134.779`**, que entrega **`5`** e **`7`** de uma vez. Uniao das
quatro fixturas de adena ja versionadas:

    13.160.684 -> 1 3 6 0 8 4
     1.696.020 -> 1 6 9 0 2
    15.134.779 -> 1 5 3 4 7 9
    (yazalaque 09h30, verdade nao registrada no M-O)

= **0 1 2 3 4 5 6 7 8 9** e a virgula. **Os onze, de um campo so, com pixels que vem de qualquer
clone.** O ramo de gravacao antiga continua inexistente e agora nem `recordings/` e necessario.

## Deviations from Plan

### 1. [Rule 1 — Bug medido] A altura de referencia do plano estava um pixel acima

**Achado durante:** Tarefa 2, ao medir as fixturas reais para a prova de campo.

O plano manda, em `must_haves.truths`, *"A guarda de altura do cortador compara contra 10"*. Medido
na convencao do codigo, a faixa da fonte e **9**. Uma guarda contra 10 recusaria todo molde
legitimo — literalmente o modo de falha do M-K, deslocado um pixel.

**Como foi tratado:** a guarda **nao usa numero nenhum** — compara contra a dominante do conjunto
gravado. A refutacao foi escrita nas docstrings de `_glifos_do_numero`, do modulo do cortador e no
cabecalho de `tests/test_renda_glifos.py`, e virou **teste sobre pixel real**
(`test_a_geometria_MEDIDA_desta_fonte_e_faixa_bruta_16_e_peneirada_9`).
**Commit:** `2abf9dc`.

### 2. [Rule 3 — Bloqueio estrutural] O portao de escritores da calibracao quebrou, como devia

**Achado durante:** a suite completa, depois da Tarefa 2.

`tests/test_calibrar_nao_apaga_identidades.py` mantem `MODULOS_QUE_GRAVAM` como tripwire: *"um
escritor novo do calibration.json precisa de olhos humanos, porque foi um escritor que apagou 13
moldes de glifo em 2026-08-30"*. O cortador e um escritor novo, e o portao fez exatamente o que
existe para fazer.

**Conferido antes de admitir:** carrega na primeira linha util e muta so `renda_moldes_da_barra`;
nao nomeia a chave de digitos do mercado em lugar nenhum do fonte (`grep` = 0), com teste afirmando
que aquela chave volta identica com os 13 moldes contados antes; e nao conhece o acervo, que e o
que o caso confere de verdade. O motivo ficou escrito ao lado da constante.
**Commit:** `5d5d36b`.

**Atencao para o merge da onda 2:** o `01-03` cria `l2scanner/calibrar_renda.py`, que provavelmente
tambem grava a calibracao e vai bater no MESMO tripwire, na MESMA linha. O conflito, se houver, e
de uma linha e a resolucao e a uniao dos dois nomes.

### 3. [Rule 2 — Funcionalidade critica ausente] O limite da PRIMEIRA rodada

O plano exige `limite` derivado dos moldes e sem default. Na primeira rodada nao ha moldes:
`limite_de_glifo_unico({})` e `None`, e a peneira recusa. Um cortador que exigisse moldes para
cortar moldes nunca sairia do zero.

**Conserto:** `limite_de_arranque(runs)` no **cortador** (nunca na peneira) — a maior largura que
nao esta numa ponta, com o ponto cego escrito na docstring: num recorte com icone NO MEIO ele
adotaria a largura daquele icone. Isso nao passa em silencio, porque o rotulo daquele recorte vai
para o olho humano ampliado. Assim que o primeiro molde existir, o limite passa a sair dos moldes.

### 4. [Rule 2] De onde saem `piso_de_leitura` e `margem_de_leitura`

O esquema do `01-01` exige as duas quando ha moldes, e nenhum plano desta fase diz de onde elas
vem. Elas **nao sao derivaveis dos moldes** — um piso de separabilidade entre MOLDES nao e um piso
medido contra glifo de TELA, e a refutacao esta em `calibracao.py:440-464` com numero.

**Conserto:** `_soleiras` resolve por ordem — linha de comando, depois o que a rodada anterior
gravou, depois o par **medido** do mercado (sobre 2.057 glifos de campo deste cliente), emprestado
e **anunciado como emprestimo** na saida. Sem nenhum dos tres, a ferramenta **recusa** e nomeia as
opcoes. Inventar uma soleira seria escolher, por omissao, entre uma leitura que recusa tudo e uma
que aceita qualquer coisa.

### 5. [Desvio de escopo declarado] `tests/test_renda_glifos.py` le disco no ultimo bloco

O plano manda o arquivo ser sintetico, "sem disco". As doze medicoes de geometria real leem as
**fixturas versionadas** de `tests/fixtures/renda/` — nunca `recordings/`, que e gitignored
(precedente literal citado no arquivo: `tests/test_mercado_glifos.py:4-8`).

**Motivo:** os numeros da fonte nao podem sair de um bloco que o proprio teste desenhou — isso e
afirmar a propria suposicao, e foi assim que o 17 sobreviveu a uma revisao inteira. Ha um controle
(`test_ha_fixturas_de_campo_versionadas_para_medir`) para que um `glob` vazio nao faca o laco passar
sem medir nada.

### 6. [Ambiente] O comando de verificacao do plano nao roda como escrito

Duas razoes, e as duas ficam escritas em vez de contornadas:

1. O `.venv` **nao tem pytest** (ja registrado no `01-01`, desvio 4). A ponte usada foi
   `PYTHONPATH=".;<repo>/.venv/Lib/site-packages" python -m pytest`. **Nada foi instalado no
   ambiente do usuario.**
2. **`recordings/` nao existe neste worktree** — a pasta e gitignored. O criterio que manda rodar
   `--propor` sobre `recordings/20260902-004500-renda-duas-instancias` foi cumprido **contra as
   fixturas versionadas equivalentes**, que sao recortes daquelas mesmas gravacoes, com o mesmo
   resultado verificavel (tabela acima) e a mesma asserção de que nada foi escrito.

## Como cada criterio de aceitacao foi verificado

| criterio | resultado |
| --- | --- |
| `pytest tests/test_renda_glifos.py -q -rs` em 0, **0 skipped** | **22 passed**, 0 skipped |
| `pytest tests/test_calibrar_renda_moldes.py -q -rs` em 0, **0 skipped** | **30 passed**, 0 skipped |
| `grep -c "def _glifos_do_numero" l2scanner/renda_leitura.py` == 1 | **1** |
| o mesmo grep no cortador == 0 | **0** |
| peneira IMPORTADA: referencias no cortador >= 1 | **3**, e teste de identidade de objeto |
| `grep -E "^(from\|import) +l2scanner\.calibrar" no modulo puro` | **0** (mais portao de AST) |
| caso da FAIXA RECOMPUTADA citando o M-K | verde, sintetico **e** sobre pixel real |
| run largo no MEIO recusando | verde (largura 17 do icone do M-N na mensagem) |
| zero / dois runs largos numa ponta recusando | verde, dois casos |
| run de 141 px recusado, largura nomeada, **nenhum** glifo devolvido | verde |
| `limite` somente-nomeado, sem default, `TypeError` na omissao | verde (mais o caso posicional) |
| guarda de altura nos DOIS sentidos (recusa a errada **e** aceita a certa) | verde |
| `grep -n "17"` no cortador so em linha com `M-K`/`refutad` | **1 linha**, e ela e a refutacao |
| `grep -c "mercado_templates_de_digito"` no cortador == 0 | **0** |
| chave do mercado identica depois da rodada, 13 moldes contados ANTES | verde |
| toda outra chave de topo identica + controle positivo | verde |
| conjunto incompleto: grava, `conjunto_descreve_numeros` False, faltantes por NOME | verde |
| nenhum molde alem dos confirmados gravado | verde |
| `--propor` sai 0 e nao escreve | verde (CLI real, mais teste) |
| os QUATRO campos aceitos, `bonus` e `lcoin` propoem | verde (parametrizado) |
| `ls tests/fixtures/renda/moldes_da_barra.json` FALHA aqui | **falha** — como manda o criterio |
| `git diff --stat` em mercado_leitura/mercado_visao/calibrar_mercado | **vazio** |
| `git diff --stat` em calibracao.py / calibrar_renda.py | **vazio** |
| `git diff --stat requirements.txt` | **vazio** |
| `calibracao_de_fixture.json` intocada (o `01-03` corre nesta onda) | **vazia** no diff |
| suite completa | ver abaixo |

Suite completa: `4922 passed, 24 skipped` com `--ignore=tests/test_agenda.py`, mais `87 passed` em
`tests/test_agenda.py` rodado a parte. A separacao e o defeito **pre-existente** registrado no
`01-01`: aquele arquivo levanta `KeyboardInterrupt` de proposito para sair do laco e o pytest as
vezes trata isso como parada de sessao. Reproduzido sem nenhum import de `renda`.

## Known Stubs

Nenhum. Nenhum caminho devolve valor fixo, lista vazia ou placeholder: todo caminho ou peneira pixel
real, ou recusa com motivo nomeado. **A fixtura de moldes ausente NAO e um stub** — e o artefato do
checkpoint, e a ausencia dela e criterio de aceitacao da Tarefa 2.

## Threat Flags

Nenhuma superficie nova alem da prevista no `<threat_model>` do plano. O escritor novo do
`calibration.json` (T-01-51/T-01-52) passou pelo portao estrutural que existe para ele, e a
admissao esta documentada no proprio portao.

## O CHECKPOINT QUE CONTINUA ABERTO — Tarefa 3

**Tipo:** `checkpoint:human-action`, gate **`blocking-human`**. Nenhum modo automatico o aprova: nao
ha CLI que olhe um recorte ampliado de um digito e diga se aquilo e um `6` ou um `8`. Um rotulo
confirmado errado nao produz meia leitura — produz a leitura errada com a confianca da certa.

**O artefato que falta:** `tests/fixtures/renda/moldes_da_barra.json`. O `01-04` inteiro pende dele.

**O comando, e ele mudou para melhor com a medicao desta rodada** — os onze rotulos fecham com as
fixturas de adena ja versionadas, sem `recordings/` e sem outro campo:

    calibrar-renda-moldes.bat --gravacoes tests\fixtures\renda ^
        --campo adena --filtro barra_direita --recorte inteiro --piso 185 --propor

Rode primeiro **com** `--propor` (ensaio, nao escreve nada); depois o mesmo comando **sem** ele.
Na primeira volta nao ha molde e nao ha proposta: voce digita o numero inteiro olhando o recorte
ampliado. ENTER aceita a proposta a partir da segunda; o que voce digitar sempre vence.

Os cinco recortes ja foram medidos e a contagem bate com a verdade de campo: 9, 10, 9, 10, 9
glifos. O que **so voce** pode fazer e dizer qual glifo e qual.

**O que NAO fazer:** nao complete o conjunto a mao, nao copie molde do mercado (o argumento mudou de
eixo mas a proibicao nao — ver acima), e nao aceite um rotulo que voce nao conseguiu ler no recorte.
Um conjunto incompleto e um desfecho **legitimo**: ele e gravado, anunciado por nome, e a adena
recusa ate ele fechar. Um conjunto **completado** e a falha aberta do LEIT-09.

**Se os onze nao fecharem:** diga quais rotulos faltaram. O esperado, depois desta medicao, e que
fechem com `--campo adena` sozinho.

**Uma advertencia medida para quem for a outro campo.** A peneira e UMA so e exige um run largo em
cada ponta. Os recortes de L-Coin e bonus publicados no M-K/M-L foram enquadrados **sem** icone —
a peneira os recusaria. Enquadre de icone a icone. Isso nao e contorno: moldes cortados de um
recorte que a leitura recusa seriam cortados de um conjunto de corridas e lidos de outro.

## Self-Check: PASSED

Arquivos conferidos em disco: `l2scanner/renda_leitura.py`, `l2scanner/calibrar_renda_moldes.py`,
`calibrar-renda-moldes.bat`, `tests/test_renda_glifos.py`, `tests/test_calibrar_renda_moldes.py`.
`tests/fixtures/renda/moldes_da_barra.json` conferido **ausente**, como o criterio manda.

Commits conferidos em `git log`: `6900398`, `834d482`, `812bea1`, `2abf9dc`, `5d5d36b`.
