---
phase: 01-reconhecimento-preciso-e-lista-de-bosses-no-config
workstream: tiat
plan: 02
subsystem: calibracao
tags: [oper-01, texto-de-console, guarda-ast, bat, calibracao]

requires:
  - phase: 01-01
    provides: "l2scanner.config.ler_bosses e os dois blocos [[boss]] do config.toml — a fonte dos termos que o guarda procura"
provides:
  - "tests/test_calibracao_generica.py — termos_procurados, primeiro_token, sem_tokens_estaveis, literais_da_funcao, acusacoes"
  - "l2scanner/calibrar.py — o texto de calibrar_tiat e a string de help do argumento, sem nome de mob"
  - "calibrar-tiat.bat — cabecalho REM sem nome de mob"
affects: [01-04, "Fase 2 (janela de respawn)"]

actuals:
  tokens: 4905
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Guarda de texto por AST restrito a UMA funcao, com remocao dos tokens de entrada estaveis ANTES da busca"
    - "Termos de busca derivados do config.toml do repositorio (nome completo MAIS cada token de 3+ caracteres), e nunca literais no teste"
    - "Prova-vazia bidirecional: o detector ACUSA o token curto e NAO acusa a flag de linha de comando"

key-files:
  created:
    - tests/test_calibracao_generica.py
  modified:
    - l2scanner/calibrar.py
    - calibrar-tiat.bat
  deleted: []

key-decisions:
  - "O TEXTO ficou generico; os NOMES DE ENTRADA (campos da Calibracao, flag --tiat, calibrar-tiat.bat) continuam como estavam — renomear os campos desligaria a vigilancia de boss em silencio em todo calibration.json ja gravado"
  - "Os termos do guarda sao o nome completo MAIS cada token de 3+ caracteres; so os nomes completos deixariam o guarda VERDE sobre as oito strings que a Task 1 removeu"
  - "A prova-vazia usa o TOKEN CURTO; escrita com o nome completo, ela reproduziria o defeito dentro do proprio guarda"
  - "A razao da nao-renomeacao (T-02-01) mora num comentario acima da funcao, e nao na docstring — a docstring e varrida pelo guarda e citar `tiat_chat` la faria o guarda acusar a propria explicacao"

requirements-completed: [OPER-01]

coverage:
  - id: D1
    description: "Nenhum literal de string de calibrar_tiat nomeia um mob da lista do config.toml"
    requirement: OPER-01
    verification:
      - kind: unit
        ref: "tests/test_calibracao_generica.py::TestOTextoDaCalibracaoNaoNomeiaUmMob::test_nenhum_literal_da_funcao_nomeia_um_mob"
        status: pass
    human_judgment: false
  - id: D2
    description: "Nenhuma linha do calibrar-tiat.bat nomeia um mob, depois de removidos os tokens de entrada estaveis"
    requirement: OPER-01
    verification:
      - kind: unit
        ref: "tests/test_calibracao_generica.py::TestOTextoDaCalibracaoNaoNomeiaUmMob::test_nenhuma_linha_do_bat_nomeia_um_mob"
        status: pass
    human_judgment: false
  - id: D3
    description: "A ferramenta AFIRMA que a mesma calibracao vale para qualquer boss da lista"
    requirement: OPER-01
    verification:
      - kind: unit
        ref: "tests/test_calibracao_generica.py::TestOTextoDaCalibracaoNaoNomeiaUmMob::test_a_funcao_afirma_que_a_calibracao_serve_para_qualquer_boss"
        status: pass
    human_judgment: false
  - id: D4
    description: "O guarda enxerga: uma fonte cujo unico sinal e o TOKEN CURTO e acusada, no fonte e no .bat"
    verification:
      - kind: unit
        ref: "tests/test_calibracao_generica.py::TestOGuardaPegaDeVerdade"
        status: pass
    human_judgment: false
  - id: D5
    description: "O caso simetrico: uma fonte cuja unica ocorrencia esta dentro da flag ou do nome do .bat NAO e acusada"
    verification:
      - kind: unit
        ref: "tests/test_calibracao_generica.py::TestOsTokensDeEntradaNaoSaoAcusados"
        status: pass
    human_judgment: false
  - id: D6
    description: "O guarda fica VERMELHO contra o l2scanner/calibrar.py e o calibrar-tiat.bat anteriores a Task 1"
    verification:
      - kind: manual
        ref: "git checkout 5e83a17 -- l2scanner/calibrar.py calibrar-tiat.bat && python -m pytest tests/test_calibracao_generica.py -q -> 3 failed, 7 passed"
        status: pass
    human_judgment: false
  - id: D7
    description: "A ferramenta continua produzindo as duas selecoes, na mesma ordem, gravando nos mesmos dois campos e na mesma imagem de conferencia"
    verification: []
    human_judgment: true
    rationale: "`calibrar_tiat` abre janelas do OpenCV e espera arrasto de mouse; nao ha caminho automatizado com o jogo fechado. A prova disponivel e estrutural: o `git diff` da funcao nao tem uma unica linha de fluxo — so literais de string trocados, mesmas chamadas, mesma ordem, mesmos `setattr`. Quem for verificar em campo roda `calibrar-tiat.bat`, marca as duas regioes e confere que `calibracao-conferencia.png` sai com os retangulos amarelo (CHAT) e verde (ALVO) onde esperava."

duration: 13min
completed: 2026-08-30
status: complete
---

# Phase 1 Plan 02: A calibracao para de falar de um mob e passa a falar das regioes — Summary

**O texto de `calibrar-tiat.bat` e de `calibrar_tiat` parou de nomear um mob e passou a nomear o que realmente marca — o CHAT e o ALVO — e um guarda por AST, cujos termos saem do `config.toml` e incluem CADA TOKEN do nome do boss, impede a mentira de voltar. Zero linhas de comportamento mudaram.**

## Performance

- **Duration:** ~13 min (`5e83a17` 14:07:35-03 -> `4af5b5a` 14:18:14-03, relogio do commit)
- **Tasks:** 2 de 2
- **Commits:** 2
- **Files:** 1 criado, 2 modificados, 0 apagados
- **Suite:** 2197 passed / 14 skipped (baseline **medido neste worktree**) -> **2207 passed / 14 skipped**. +10 testes, zero testes existentes editados, zero enfraquecidos.

## Task Commits

| # | Tarefa | Commit | Tipo |
|---|--------|--------|------|
| 1 | O texto da calibracao passa a nomear as regioes, nao um mob | `6083c15` | docs |
| 2 | O guarda que impede o nome do mob de voltar para o texto | `4af5b5a` | test |

## 1. A EVIDENCIA DECISIVA: o guarda fica VERMELHO contra o texto antigo

Este e o criterio que separa este guarda de um decorativo, e a razao de o plano exigir a prova por escrito. Executado restaurando os dois arquivos do commit base e rodando o guarda novo contra eles:

```
git checkout 5e83a17d015433477f9a8d18b39acd9a41546f0c -- l2scanner/calibrar.py calibrar-tiat.bat
python -m pytest tests/test_calibracao_generica.py -q
-> 3 failed, 7 passed in 0.25s
```

As tres falhas, com os achados literais:

**(a) `test_nenhum_literal_da_funcao_nomeia_um_mob` — OITO acusacoes, TODAS pelo token curto:**

```
termos = {'north', 'south', 'tiat', 'tiat north', 'tiat south'}

o texto de calibrar_tiat voltou a nomear um mob:
  ('tiat', 'Marca, na janela do jogo, o chat e/ou o texto do alvo para o Tiat....')
  ('tiat', '1/2 - marque as linhas do CHAT onde aparece o anuncio de Tiat.')
  ('tiat', 'Tiat: chat')
  ('tiat', 'Tiat: alvo')
  ('tiat', 'TIAT CHAT')
  ('tiat', 'TIAT ALVO')
  ('tiat', 'Aviso de Tiat calibrado para ')
  ('tiat', 'Nao sei qual janela do jogo calibrar para o Tiat.')
```

**(b) `test_nenhuma_linha_do_bat_nomeia_um_mob` — TRES acusacoes:**

```
  ('tiat', 'REM  Calibrar aviso de TIAT')
  ('tiat', 'REM  Pode marcar apenas uma. O scanner avisa se Tiat aparecer')
  ('tiat', 'REM  no chat OU se o seu alvo virar Tiat.')
```

**(c) `test_a_funcao_afirma_que_a_calibracao_serve_para_qualquer_boss`** — a docstring antiga nao continha `"qualquer boss"` em lugar nenhum.

**As onze acusacoes vieram pelo termo `'tiat'`, e NENHUMA pelos nomes completos.** Um conjunto de termos com so `Tiat North` e `Tiat South` teria passado VERDE sobre as onze — exatamente o guarda decorativo que o plano-checker antecipou. Isso esta congelado como teste permanente em `test_um_conjunto_so_com_nomes_completos_ficaria_cego`, que monta a mesma fonte sintetica e afirma as duas metades: o conjunto so-com-nomes-completos NAO acusa, e o conjunto real acusa.

**O caso simetrico apareceu de graca na mesma rodada, sobre dados reais:** o literal `'Use: python -m l2scanner.calibrar --tiat --janela "TITULO"'` estava no fonte antigo e **nao foi acusado** — a remocao dos tokens estaveis funcionou contra a fonte historica, e nao so contra as fontes sinteticas dos testes.

Os dois arquivos foram devolvidos com `git checkout HEAD -- l2scanner/calibrar.py calibrar-tiat.bat` e `git diff HEAD --stat` voltou vazio antes de qualquer commit.

### A verificacao pedida pelos outros dois criterios

Reintroduzi o token curto nos dois lugares ao mesmo tempo — um `print` novo dentro de `calibrar_tiat` (`"(o anuncio do Tiat sai nessa area)"`) e uma linha `REM  (por exemplo, o Tiat)` no `.bat` — e rodei:

```
2 failed, 8 passed
  FAILED ...::test_nenhum_literal_da_funcao_nomeia_um_mob
  FAILED ...::test_nenhuma_linha_do_bat_nomeia_um_mob
```

Desfeito por `git checkout HEAD -- ...`; suite verde de novo. Manter a flag `--tiat` e o nome `calibrar-tiat.bat` como estao **nao** deixa o guarda vermelho: eles continuam nos dois arquivos e a suite fica verde.

## 2. A ASSIMETRIA DELIBERADA — o que ficou generico e o que NAO mudou

O plano pediu isto por escrito, porque e exatamente o tipo de coisa que o proximo leitor vai querer "consertar".

| Superficie | Mudou? | Razao |
|---|---|---|
| Texto impresso por `calibrar_tiat` | **Sim** | E o que o usuario le enquanto calibra. |
| Docstring de `calibrar_tiat` | **Sim** | E o que o proximo programador le. |
| Titulos das janelas de selecao (`Regiao do chat` / `Regiao do alvo`) | **Sim** | Aparecem na tela durante o arrasto. |
| Rotulos da imagem de conferencia (`CHAT` / `ALVO`) | **Sim** | Ficam gravados no `.png` que o usuario abre. |
| Cabecalho `REM` do `calibrar-tiat.bat` | **Sim** | E a primeira coisa que se le ao abrir o arquivo. |
| String de `help` do argumento no `argparse` | **Sim** | Sai no `--help`. |
| `Calibracao.tiat_chat` / `Calibracao.tiat_alvo` | **NAO** | Ver abaixo. |
| Chaves de mesmo nome no `calibration.json` | **NAO** | Ver abaixo. |
| Flag de linha de comando `--tiat` | **NAO** | Porta de entrada que o usuario ja tem no dedo e que o README documenta. |
| Nome do arquivo `calibrar-tiat.bat` | **NAO** | Idem — e o atalho que ele clica. |
| Qualquer linha de fluxo | **NAO** | Mesma ordem de selecao, mesmo `ESC`, mesma recusa, mesma imagem. |

**Por que os campos NAO foram renomeados (T-02-01, `high`), e por que isso NAO e inercia.** `Calibracao.de_dict` le cada chave com `dados.get(...)` e devolve `None` quando ela falta. Renomear `tiat_chat` / `tiat_alvo` faria todo `calibration.json` ja gravado na maquina do usuario passar a devolver `None` nas duas regioes: a ferramenta subiria normalmente, a vigilancia de party continuaria funcionando, e **o aviso de boss simplesmente nunca mais sairia — sem uma linha de erro, sem um aviso no console, sem nada que o usuario pudesse notar antes de perder um nascimento**. O arquivo e gitignored, entao nem `git checkout` traria de volta. OPER-01 e sobre o TEXTO nao nomear um mob, e nao sobre mudar o formato da calibracao; esta escrito assim no CONTEXT e no plano.

A razao mora em **duas** superficies, como o registro de ameacas exige: neste SUMMARY e num bloco de comentario imediatamente acima de `def calibrar_tiat` em `l2scanner/calibrar.py`.

**Por que num comentario e nao na docstring, apesar de o `<threat_model>` dizer "docstring".** A docstring da funcao e varrida pelo proprio guarda da Task 2. Escrever `tiat_chat` la dentro faria o guarda acusar exatamente a explicacao de por que aquele nome existe — e a saida seria acrescentar `tiat_chat` a lista de tokens perdoados, o que abriria um buraco por onde qualquer string com o token curto poderia voltar. O comentario fica a duas linhas de distancia, no caminho de quem abre a funcao, e a docstring aponta para ele em voz alta ("ver o comentario logo acima desta funcao"). E registrado abaixo como desvio.

## 3. Como o guarda funciona, e onde ele quase nasceu decorativo

`tests/test_calibracao_generica.py`:

1. **`termos_procurados(bosses)`** — para cada `Boss` do `config.toml`, o `nome` inteiro MAIS cada token separado por espaco, todos com 3+ caracteres, tudo em `casefold`. Sobre o config do repositorio: `{'tiat north', 'tiat south', 'tiat', 'north', 'south'}`. **Este e o ponto em que o guarda decide se guarda ou decora**, e a razao esta escrita na docstring da propria funcao.
2. **`sem_tokens_estaveis(texto)`** — remove `calibrar-tiat.bat` e `--tiat` por `re.sub` com `IGNORECASE`, **antes** da busca. O mais longo primeiro. Remover depois faria a comparacao acusar a propria flag e so entao perdoa-la, o que daria no mesmo que nao ter o caso simetrico.
3. **`literais_da_funcao(fonte)`** — `ast.parse`, acha o `FunctionDef` chamado `calibrar_tiat`, colhe todo `ast.Constant` de tipo `str` dentro dele (docstring e partes constantes de f-string inclusive). **AST e nunca `grep`**, porque `calibrar.py` legitimamente carrega a palavra em `calibrar_tiat`, em `cal.tiat_chat`, e nos comentarios que explicam por que aqueles nomes nao mudaram — um `grep` cru viraria ruido e o proximo a passar por aqui afrouxaria o guarda ate ele parar de guardar. Mesma razao escrita em `tests/test_presenca.py::TestSemRelogioProprio`.
4. **Fixture `bosses`** — lista vazia PULA o arquivo inteiro com `pytest.skip`, dizendo por que. Um teste que passa por falta de dado e pior do que um teste que nao existe.
5. **`primeiro_token(bosses)`** — o primeiro token de 3+ caracteres do primeiro boss. E o que as provas-vazias usam: escritas com o nome completo, elas passariam enquanto o detector continuasse cego para o token curto, reproduzindo o defeito dentro do guarda que existe para preveni-lo.

**Os 10 testes:** 3 sobre os artefatos reais (fonte, `.bat`, e a afirmacao positiva de que a calibracao vale para qualquer boss), 4 de prova-vazia / anti-cegueira, 3 do caso simetrico (flag sozinha, nome do `.bat` sozinho, e a insensibilidade a caixa da remocao).

## 4. O que o usuario le agora

```
As duas regioes valem para QUALQUER boss da sua lista do
config.toml. Acrescentar um mob novo la nao pede recalibracao.

1/2 - marque as linhas do CHAT onde sai o anuncio de nascimento.
      ENTER confirma; ESC deixa este sinal desligado.
2/2 - marque APENAS o NOME do alvo selecionado (nao a barra inteira).
      ENTER confirma; ESC deixa este sinal desligado.
Regioes do chat e do alvo calibradas na janela 'Lineage II'.
CONFIRA calibracao-conferencia.png: amarelo = chat; verde = nome do alvo.
```

E no `--help`, medido:

```
  --tiat           marca as regioes do chat e do alvo para o aviso de boss; a
                   mesma calibracao vale para qualquer boss do config.toml e
                   nao altera a calibracao da party
```

A frase "a mesma calibracao vale para qualquer boss" e o pedaco que fecha OPER-01 de verdade: parar de mentir nao basta, a ferramenta tem de dizer a verdade em voz alta, senao o usuario continua sem saber que acrescentar um `[[boss]]` nao pede recalibracao. `test_a_funcao_afirma_que_a_calibracao_serve_para_qualquer_boss` guarda essa afirmacao.

## Files Created/Modified

- **`tests/test_calibracao_generica.py`** (criado, 296 linhas) — o guarda por AST, os termos derivados do `config.toml`, a prova-vazia com o token curto e o caso simetrico.
- **`l2scanner/calibrar.py`** — bloco de comentario novo acima de `calibrar_tiat` (T-02-01); docstring reescrita; 8 literais trocados dentro da funcao; a string de `help` do argumento correspondente. **Nenhuma linha de fluxo.**
- **`calibrar-tiat.bat`** — cabecalho `REM` reescrito, com duas linhas novas dizendo que a mesma calibracao vale para qualquer boss da lista. CRLF e `cp1252` preservados (a escrita foi por bytes, exatamente por isso).

**NAO tocados** (pertencem a planos irmaos da mesma wave ou a outros workstreams): `l2scanner/bosses.py`, `l2scanner/config.py`, `tools/`, `README.md`, `l2scanner/ponte_*.py`, `l2scanner/mercado_*.py`, `l2scanner/calibrar_mercado.py`, `.planning/STATE.md`, `.planning/**/ROADMAP.md`. Verificado por `git diff --stat` contra o commit base: saida vazia.

## Decisions Made

1. **Os termos sao nome completo MAIS cada token de 3+ caracteres.** So os nomes completos deixariam o guarda verde sobre as onze strings reais; so os tokens perderia um eventual nome de mob de uma palavra so.
2. **`TAMANHO_MINIMO_DO_TOKEN = 3`**, com a razao na constante: uma particula de duas letras dentro de um nome composto viraria falso positivo em quase qualquer frase em portugues.
3. **A remocao dos tokens estaveis ignora a caixa** (`re.IGNORECASE`), porque um `.bat` e frequentemente escrito em maiusculas e `CALIBRAR-TIAT.BAT` e a mesma porta de entrada. Ha teste para isso.
4. **Os em-dashes sairam das duas linhas de instrucao** que a Task 1 reescreveu (`1/2 —` -> `1/2 -`), seguindo a convencao do CLAUDE.md de nao usar em-dash em texto que o usuario le. So nas linhas ja tocadas; os outros 50+ em-dashes do arquivo, todos em comentario e docstring, ficaram como estavam (fora de escopo).
5. **A prova-vazia do `.bat` tambem usa o token curto**, e nao so a do fonte. Sem ela, a leitura do `.bat` poderia estar quebrada (encoding errado, arquivo vazio) e os dois testes de `.bat` passariam por leitura vazia — por isso ha tambem um `assert linhas` antes da busca.

## Deviations from Plan

### 1. [Rule 2 - correcao necessaria] A razao de T-02-01 foi para um comentario, e nao para a docstring

- **Encontrado durante:** Task 1, confirmado na Task 2.
- **O que o plano pedia:** o `<threat_model>` diz que a razao da nao-renomeacao fica escrita "no SUMMARY e na docstring da funcao".
- **O problema:** a docstring de `calibrar_tiat` e varrida pelo guarda da Task 2. Citar `tiat_chat` / `tiat_alvo` la dentro faria o guarda acusar a propria explicacao de por que aqueles nomes existem, e a saida obvia seria perdoar mais tokens — abrindo um buraco por onde o token curto poderia voltar em qualquer string.
- **Solucao:** a razao completa, com os nomes dos campos, mora num bloco de comentario `#` imediatamente acima de `def calibrar_tiat` (comentario nao e `ast.Constant`, entao o guarda nao o ve). A docstring mantem a substancia — "OS DOIS CAMPOS GRAVADOS NAO MUDAM DE NOME, e a assimetria com o texto e deliberada" — e aponta para o comentario. As duas superficies exigidas pelo registro de ameacas continuam sendo duas, e a mais detalhada esta a duas linhas do leitor.
- **Commit:** `6083c15`

### 2. [Rule 2 - funcionalidade critica ausente] Um teste a mais: a afirmacao positiva

- **Encontrado durante:** Task 2.
- **O que faltava:** o plano especificava tres tipos de teste (fonte, `.bat`, prova-vazia + simetrico). Nenhum deles falharia se a ferramenta simplesmente parasse de dizer qualquer coisa sobre a lista de bosses.
- **Por que importa:** o criterio de aceite da Task 1 exige que "uma delas afirma que a mesma calibracao vale para qualquer boss da lista", e o `<done>` da Task 1 e sobre o usuario NAO concluir que precisa recalibrar por mob. Parar de mentir nao produz esse resultado sozinho — a afirmacao positiva produz. Sem guarda, ela e a primeira coisa que alguem apaga por achar verbosa.
- **Solucao:** `test_a_funcao_afirma_que_a_calibracao_serve_para_qualquer_boss`, que procura `"qualquer boss"` no conjunto dos literais da funcao. Fica VERMELHO contra o texto antigo (foi a terceira falha da prova de RED).
- **Commit:** `4af5b5a`

### 3. [Estrutura TDD] O ciclo RED/GREEN nao virou dois commits

- **Encontrado durante:** Task 2, que e `tdd="true"`.
- **O problema:** o sujeito deste guarda e a Task 1, do MESMO plano, e ela precisa vir antes (o `.bat` e o fonte tem de estar limpos para o teste ser escrito contra a realidade). Um commit `test(...)` vermelho seguido de um `feat(...)` verde exigiria inverter a ordem das tarefas do plano.
- **Solucao:** o gate RED foi demonstrado e MEDIDO contra o fonte anterior a Task 1 (`5e83a17`), com a saida completa transcrita na secao 1 acima — 3 falhas, 11 acusacoes nomeadas. E a mesma prova que dois commits dariam, contra o mesmo codigo, com a evidencia preservada por escrito em vez de so no `git log`. Alem disso, a prova-vazia permanente (`TestOGuardaPegaDeVerdade`, 4 testes) mantem o RED reprodutivel para sempre, sem depender de um sha historico.

## TDD Gate Compliance

O plano marca a Task 2 como `tdd="true"`. A sequencia de commits e `docs(...)` -> `test(...)`, e nao `test(...)` -> `feat(...)`.

**Isso e deliberado e esta justificado no desvio 3 acima:** o guarda vigia o texto que a Task 1 do mesmo plano produziu, entao um commit `test` anterior a Task 1 seria um teste escrito contra um alvo que ainda nao existe. O gate RED foi cumprido em substancia — medido contra `5e83a17` com a saida transcrita — e nao em forma de commit. Nenhum teste foi enfraquecido e nenhum passou sem antes ser visto falhar.

## Known Stubs

Nenhum. Nenhum valor codificado chegando a UI, nenhum componente sem fonte de dados, nenhum `TODO` ou `FIXME` introduzido. Os termos do guarda vem do `config.toml` real; nao ha literal de nome de mob no arquivo de teste.

## Threat Flags

Nenhuma superficie nova. Este plano nao acrescentou endpoint, caminho de auth, acesso a arquivo novo nem mudanca de esquema. As duas mitigacoes `mitigate` do registro estao implementadas e afirmadas:

| Ameaca | Mitigacao implementada | Onde esta provado |
|---|---|---|
| T-02-01 (degradacao silenciosa por renomeacao) | Os campos NAO foram renomeados; a razao esta no comentario acima de `calibrar_tiat` e neste SUMMARY | `git diff` de `l2scanner/calibracao.py` vazio; `git diff` da funcao sem linha de fluxo |
| T-02-03 (guarda que para de guardar) | AST restrito a funcao, remocao explicita dos tokens estaveis, prova-vazia com o TOKEN CURTO, caso simetrico | `TestOGuardaPegaDeVerdade` (4) + `TestOsTokensDeEntradaNaoSaoAcusados` (3) + a prova de RED contra `5e83a17` |

T-02-02 segue `accept`, como o plano decidiu: nenhuma linha de fluxo mudou e `tests/test_calibrar_nao_apaga_mercado.py` continua verde.

## Verification

| Comando | Resultado |
|---|---|
| `python -m pytest tests/ -q` | **2207 passed, 14 skipped** (baseline neste worktree: 2197 / 14) |
| `python -m pytest tests/test_calibracao_generica.py -q` | **10 passed** |
| `python -m pytest tests/test_calibrar_nao_apaga_mercado.py -q` | 6 passed |
| `python -c "import l2scanner.calibrar"` | OK |
| `python -m l2scanner.calibrar --help` | a linha do argumento descreve as duas regioes (transcrita na secao 4) |
| `python -m ruff check tests/test_calibracao_generica.py l2scanner/calibrar.py` | All checks passed |
| guarda contra `5e83a17` (fonte + `.bat` antigos) | **3 failed, 7 passed** — a prova de RED |
| token curto reintroduzido no `print` e no `REM` | **2 failed, 8 passed**; desfeito, verde de novo |
| `git diff --stat 5e83a17 HEAD -- l2scanner/bosses.py l2scanner/config.py tools README.md .planning requirements.txt` | vazio — nenhum arquivo de plano irmao ou de workstream paralelo tocado |
| `git diff --diff-filter=D --name-only` nos dois commits | vazio — nenhuma delecao |

**Nota sobre o baseline.** O briefing anunciava 2209 passed / 2 skipped no checkout principal; aqui mediu 2197 / 14. A diferenca sao 12 testes que dependem das bindings de OCR do Windows, ausentes neste worktree — o mesmo desvio que o `01-01-SUMMARY.md` ja registrou. `2197 + 12 = 2209`: os dois numeros descrevem a mesma suite em ambientes diferentes. A comparacao valida e 2197 -> 2207 na mesma maquina.

## Self-Check

Executado antes de escrever esta secao.

**Arquivos afirmados como criados:**
- `tests/test_calibracao_generica.py` — FOUND

**Arquivos afirmados como modificados:**
- `l2scanner/calibrar.py` — FOUND, modificado em `6083c15`
- `calibrar-tiat.bat` — FOUND, modificado em `6083c15`

**Commits afirmados:** `6083c15`, `4af5b5a` — ambos FOUND em `git log`.

## Self-Check: PASSED
