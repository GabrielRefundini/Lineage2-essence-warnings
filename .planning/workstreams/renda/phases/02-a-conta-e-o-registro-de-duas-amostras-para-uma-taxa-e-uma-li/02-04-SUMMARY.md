---
phase: 02-a-conta-e-o-registro-de-duas-amostras-para-uma-taxa-e-uma-li
plan: 04
subsystem: renda
tags: [renda, calibracao, ponte-xp, procedencia, fraction, ast-gate, tdd, rend-08, rend-09]
status: complete

requires:
  - phase: 01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa
    provides: "`DECIMOS_DE_MILESIMO_POR_PONTO` (a unidade do EXP), o molde de campo opcional do `calibration.json` (`renda_por_personagem`, `renda_moldes_da_barra`) e o portao estrutural derivado de `fields(Calibracao)`"
  - phase: 02-a-conta-e-o-registro-de-duas-amostras-para-uma-taxa-e-uma-li
    plan: 01
    provides: "a suite verde depois da inversao do portao de `tests/test_renda_par.py` — o acoplamento era TEMPORAL e nao de arquivo"
provides:
  - "`Calibracao.renda_ponte_de_xp` — a terceira chave da renda, por personagem E POR NIVEL, com validador de FORMA e de PROCEDENCIA no arranque"
  - "`Calibracao.ponte_do_nivel(nome, nivel)` — o acessor que devolve o nivel PEDIDO ou NADA, delegando a busca para `renda_ponte.constante_do_nivel`"
  - "`l2scanner/renda_ponte.py` — `XpAbsoluto`, `xp_do_ganho`, `xp_acumulado_no_nivel`, `xp_por_hora`, `constante_do_nivel`, e os tres motivos de ausencia distinguiveis"
  - "`total_do_xp_da_linha` e `multiplicador_em_centesimos` — REND-09 como funcao pura testada, com a banda 562-567% presa sobre as quatro linhas versionadas"
  - "`l2scanner/renda_semeadura.py` — `semear(calibracao, entrada, *, confirmar)` e `ENTRADA_MEDIDA` com a procedencia inteira"
  - "`tools/semear_a_ponte_de_xp.py` — `argparse`, `carregar`, `semear`, `salvar`. Nada mais"
affects: [Fase 3 (a ferramenta que MEDE a ponte), o painel que exibe XP absoluto]

actuals:
  tokens: 24000
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Banda de multiplicador em CENTESIMOS INTEIROS por divisao inteira (`total*100 // resto`), para que uma afirmacao sobre a tela nao passe por ponto flutuante"
    - "Portao de ferramenta de bancada por ARVORE em duas camadas: imports, e textos que sao ARGUMENTO DE CHAMADA — a docstring pode nomear a ferramenta sem derrubar o portao"
    - "Extracao da decisao de `tools/` para `l2scanner/` quando dois criterios de aceitacao se tornam mutuamente impossiveis"

key-files:
  created:
    - l2scanner/renda_ponte.py
    - l2scanner/renda_semeadura.py
    - tools/semear_a_ponte_de_xp.py
    - tests/test_renda_ponte.py
    - tests/test_renda_semeadura.py
  modified:
    - l2scanner/calibracao.py
    - tests/test_calibracao_renda.py

key-decisions:
  - "A busca da constante mora em UM lugar so — `renda_ponte.constante_do_nivel` — e `Calibracao.ponte_do_nivel` DELEGA para la. Duas normalizacoes da chave de nivel seriam duas verdades sobre a mesma forma, e na primeira mudanca de formato uma delas envelheceria calada"
  - "A PROCEDENCIA e obrigatoria no validador, e nao opcional: `medido_em`, `n_abates`, `n_linhas_de_chat` e `janela_em_segundos` ausentes ou nao-positivos derrubam o arranque. Uma constante sem denominador e um chute com cara de medicao"
  - "A banda do multiplicador do REND-09 e em CENTESIMOS INTEIROS: `363*100 // 64 = 567` cai exatamente no teto declarado, enquanto `Fraction(363,64) = 5,671875` estouraria uma banda escrita como `5,62 <= x <= 5,67`. A divisao inteira e o que faz o numero do requisito e o numero do teste serem o mesmo"
  - "`renda_ponte` nao importa `calibracao` nem `renda_conta`, e recebe a chave `renda_ponte_de_xp` INTEIRA por parametro — e o que permite distinguir as TRES ausencias sem conhecer disco"
  - "O import de `DECIMOS_DE_MILESIMO_POR_PONTO` e DIFERIDO dentro de `_pontos_percentuais`, pelo numero ja medido no `renda_conta` (334 modulos com cv2 e numpy). Medido de novo aqui: `import l2scanner.renda_ponte` traz 47 modulos, sem cv2 e sem numpy"
  - "A chave INTEIRA e a de TEXTO sao a MESMA entrada, e o `semear` remove a inteira ao gravar a de texto — deixar as duas daria duas constantes para um nivel so, com a leitura escolhendo por ordem"
  - "O `calibration.json` real NAO foi semeado por este plano: ele e gitignored, nao existe no worktree, e a semeadura e uma acao humana deliberada (`--confirmar` para trocar). A constante e a procedencia moram em `ENTRADA_MEDIDA` e atravessam uma ida e volta REAL em `tmp_path`"

requirements-completed: [REND-08, REND-09]
---

# Phase 02 Plan 04: A ponte XP↔porcentagem Summary

A constante que converte pontos percentuais do nível em XP absoluto entrou no
`calibration.json` **por personagem e por nível**, carregando a procedência que a
torna auditável — e o consumo recusa converter, com motivo nomeado, sempre que
não há constante para o **nível atual**.

## O que foi construído

### Tarefa 1 — a terceira chave da renda, nos cinco lugares

`renda_ponte_de_xp` entrou no dataclass, no `salvar` (dict **cru**, sem
reconstrução), no `carregar` (`.get`, campo em `None` quando ausente), no
validador de arranque, **e em `VALORES_ESPECIAIS` do teste estrutural** — o
quinto lugar, que é o que some do radar. `VERSAO_DO_ESQUEMA` continua em **2**:
a chave é opcional e ninguém é obrigado a recalibrar.

O validador confere **forma e procedência, nunca plausibilidade**:
`xp_por_ponto` inteiro positivo com `bool` recusado *antes* do teste de inteiro
(`True` é um `int` de valor 1, e uma ponte de 1 XP por ponto passaria calada), e
`medido_em`, `n_abates`, `n_linhas_de_chat` e `janela_em_segundos` obrigatórios.
Toda mensagem nomeia o personagem, o nível e o conserto.

`Calibracao.ponte_do_nivel(nome, nivel)` devolve a entrada **daquele** nível
**daquele** personagem, ou nada. Nunca a do nível anterior.

### Tarefa 2 — o consumo, com a recusa como produto

`l2scanner/renda_ponte.py` é aritmética pura: sem disco, sem OpenCV, sem laço,
sem relógio. `XpAbsoluto` copia a forma de `Tendencia` — `valor` ou
`motivo_da_ausencia`, nunca os dois — e carrega a **procedência crua** da
constante que usou, para que quem exibe possa dizer que o número veio de um
censo com 114 abates e 240 linhas de chat, e não de um chute.

As três ausências têm três textos diferentes porque o conserto de cada uma é
outro: nunca mediram a ponte, não mediram **deste personagem**, não mediram
**deste nível**. A conversão é inteira (`Fraction` quando não é exata) e a
unidade sai de `DECIMOS_DE_MILESIMO_POR_PONTO`, nunca de um literal.

**REND-09 fechou como função testada**, e não como prosa: `total_do_xp_da_linha`
devolve o **total** — o parênteses é a *parte* que veio de bônus —, e
`multiplicador_em_centesimos` prova por medição que as quatro linhas versionadas
caem entre **562% e 567%**, que é o que a própria barra exibe. Se fosse soma, o
multiplicador seria 10,34× e nada na tela corresponderia a ele.

### Tarefa 3 — a semeadura, com a decisão fora do `argparse`

`semear(calibracao, entrada, *, confirmar)` recebe uma `Calibracao` já carregada
e devolve outra. **Não lê nem escreve arquivo** — e é exatamente isso que faz as
duas garantias serem testáveis sem `runpy`, sem `subprocess` e sem nomear a
ferramenta, ao mesmo tempo em que o portão "nenhum teste importa a ferramenta"
continua verdadeiro (agora porque não há o que importar de lá).

`tools/semear_a_ponte_de_xp.py` tem quatro passos: ler argumentos, `carregar`,
`semear`, `salvar`. A escrita passa pelo `.tmp` + troca atômica que já existia,
porque um JSON truncado por Ctrl-C mata o **scanner de party inteiro**, que é o
produto.

## A constante semeada, e onde ela está

`ENTRADA_MEDIDA` — Faerlina, nível 67, **388.700 XP por ponto percentual**,
medida em 2026-09-02 a 55 Hz — mora em `l2scanner/renda_semeadura.py` com a
procedência inteira na `observacao`: censo **completo** (188 degraus somando
1903 unidades contra 1903 de avanço da barra, zero leituras negativas em 8.555
amostras), 114 eventos de abate, 240 linhas de chat, a segunda medição
independente a 1,5% (383.124) e o aglomerado de ~3 unidades que ninguém explica
— **registrado e não escondido**, com a razão de ele não afetar a constante.

**O `calibration.json` real não foi tocado.** Ele é `gitignore`d (`.gitignore:57`)
e não existe neste worktree; a semeadura é uma ação humana deliberada, e o
critério de verificação do plano exige justamente que `git status --porcelain
calibration.json` saia vazio. O caminho foi exercitado de ponta a ponta contra o
arquivo real do formato, em `tmp_path`: `carregar → semear → salvar → carregar →
consumir`, com o XP absoluto afirmado no fim. **É isso que fecha a C-8** — o
caminho "XP disponível" rodou contra o número de verdade, e o caminho "XP
indisponível" rodou ao lado dele, no mesmo arquivo.

Para semear no arquivo do usuário:

    PYTHONPATH=. .venv/Scripts/python.exe tools/semear_a_ponte_de_xp.py

## Verificação

| Portão | Resultado |
|---|---|
| `pytest tests/test_renda_semeadura.py tests/test_renda_ponte.py tests/test_calibracao_renda.py tests/test_calibrar_renda_nao_apaga_nada.py -q` | **122 passed, 0 skipped** |
| Suíte inteira (`--ignore=tests/test_agenda.py`) | **5595 passed, 24 skipped** (linha de base neste worktree: 5508) |
| `renda_ponte_de_xp` em `fields(Calibracao)` / `VERSAO_DO_ESQUEMA` | `True 2` |
| `float`/`round` em `renda_ponte.py` (AST) | `[]` |
| `calibracao`/`renda_conta` importados em `renda_ponte.py` (AST) | `[]` |
| Literal `10000` em `renda_ponte.py` (AST) | `[]` |
| `import l2scanner.renda_ponte` traz cv2/numpy | `False False` (47 módulos) |
| Nenhum teste **importa** a ferramenta (AST) | `[]` |
| Nenhum teste a **executa por caminho** (AST, só argumentos de chamada) | `[]` |
| Ferramenta fina: funções de módulo / importa `renda_semeadura` | `['_argumentos', 'main'] True` |
| Ferramenta redefine `ENTRADA_MEDIDA` | `[]` |
| Disco dentro de `renda_semeadura.py` (AST) | `[]` |
| Escrita direta na ferramenta (AST) | `[]` |
| `git diff --stat requirements.txt` | vazio |
| `git status --porcelain calibration.json` | vazio |
| `renda_conta.py`, `renda_registro.py`, `config.py`, `config.toml`, `.gitignore`, `dashboard*` | **não tocados** |

Os portões de AST não ficaram só como comandos de aceitação: eles viraram
**testes** em `tests/test_renda_semeadura.py`, e por isso continuam valendo
depois que este plano sair de vista.

## Desvios do plano

### Ajustes de desenho aplicados durante a execução

**1. [Regra 2 — funcionalidade crítica ausente] `Calibracao.ponte_do_nivel`
passou a DELEGAR para `renda_ponte.constante_do_nivel`.**

- **Encontrado durante:** Tarefa 2.
- **Problema:** a Tarefa 1 escreveu a normalização da chave de nível (texto ×
  inteiro) dentro do acessor, e a Tarefa 2 precisava da *mesma* busca para
  distinguir as três ausências. Duas implementações da mesma normalização são
  duas verdades sobre uma só forma — exatamente o defeito que a docstring de
  `mercado_leitura.limite_de_glifo_unico` já proíbe com essas palavras nesta
  árvore.
- **Correção:** a busca mora em `renda_ponte.constante_do_nivel`, que devolve
  `(entrada, motivo)`; o acessor da `Calibracao` delega e descarta o motivo. O
  import é local e barato (`renda_ponte` é aritmética pura, 47 módulos).
- **Arquivos:** `l2scanner/calibracao.py`, `l2scanner/renda_ponte.py`.
- **Commit:** `a3f2032`.

**2. [Regra 2] A banda do multiplicador do REND-09 é em centésimos inteiros.**

- **Encontrado durante:** Tarefa 2.
- **Problema:** o plano pede "todas caem entre 5,62 e 5,67", mas
  `363/64 = 5,671875` **estoura** 5,67 como fração exata. Escrever a banda como
  `Fraction(567,100)` faria o teste falhar contra o número que o próprio
  `REQUIREMENTS.md` versiona; alargar a banda para 5,68 faria o teste deixar de
  afirmar o que o requisito afirma.
- **Correção:** `multiplicador_em_centesimos(total, bonus) = total * 100 //
  resto`, que é o truncamento para centésimos que o requisito já usa ao escrever
  "5,67". Assim `363→567`, `388→562`, `405→562`, `439→562`, e a banda `[562,
  567]` do requisito é literalmente a banda do teste — sem ponto flutuante numa
  conta que é uma afirmação sobre a tela.
- **Arquivos:** `l2scanner/renda_ponte.py`, `tests/test_renda_ponte.py`.
- **Commit:** `a3f2032`.

**3. [Regra 2] `medido_em` entrou como quarto campo obrigatório de procedência.**

- **Encontrado durante:** Tarefa 1.
- **Problema:** os critérios de aceitação nomeiam três campos de procedência,
  mas a verdade travada do plano exige "quantas linhas de chat, quantos abates,
  que janela, **e quando foi medida**". Uma ponte de três *level ups* atrás
  descreve outro personagem, e sem a data ninguém sabe disso.
- **Correção:** `medido_em` é exigido como texto não vazio, com teste próprio. Os
  três testes por campo de procedência continuam existindo exatamente como o
  plano pede.
- **Arquivos:** `l2scanner/calibracao.py`, `tests/test_calibracao_renda.py`.
- **Commit:** `4a5118c`.

**4. Cosmético — dois travessões removidos da `observacao`.**

- **Encontrado durante:** o teste de fumaça da ferramenta.
- **Problema:** o console do Windows (codepage 850) renderiza `—` como `?` ao
  imprimir a entrada existente na recusa. O JSON em disco está correto (UTF-8,
  `ensure_ascii=False`); o dano é só na saída que o usuário lê.
- **Correção:** os dois travessões viraram parênteses e dois-pontos.
- **Commit:** `db66f4a`.

### Nenhum portão foi enfraquecido

A preservação contra os outros três calibradores continua sendo por **subtração**
de `fields(Calibracao)` e não por lista escrita à mão; os controles positivos das
duas direções continuam onde estavam; e a prova de não-destruição da Fase 1
(`tests/test_calibrar_renda_nao_apaga_nada.py`) passa sem uma linha alterada.

## Portas de checkpoint

Nenhuma. As três tarefas eram `type="auto"` e o plano é autônomo.

## Conhecimentos que a próxima fase herda

- **A ferramenta que MEDE a ponte continua deferida** (Fase 3 ou tarefa própria),
  e ela é quem vai consumir `total_do_xp_da_linha` ao parsear o chat. A convenção
  está presa por teste justamente para que quem escrever o parser **não some o
  parênteses**.
- **O aglomerado de ~3 unidades continua sem identificação** — 50 eventos, 20 por
  minuto, 7,9% do XP da janela. Está registrado na `observacao` da entrada
  semeada e não afeta a constante, mas é a próxima pergunta aberta da medição.
- **A ponte é por nível e precisa ser remedida a cada level up.** Até lá, o painel
  mostra pontos percentuais e diz que o absoluto está indisponível — que é o
  comportamento correto, e não uma lacuna.

## Known Stubs

Nenhum. Não há valor vazio codificado, texto de "em breve", nem componente sem
fonte de dados: os dois caminhos (com constante e sem) estão implementados e
exercitados contra dado real.

## Self-Check: PASSED

Arquivos afirmados, conferidos em disco:

- `l2scanner/renda_ponte.py` — FOUND
- `l2scanner/renda_semeadura.py` — FOUND
- `tools/semear_a_ponte_de_xp.py` — FOUND
- `tests/test_renda_ponte.py` — FOUND
- `tests/test_renda_semeadura.py` — FOUND
- `l2scanner/calibracao.py` — FOUND (modificado)
- `tests/test_calibracao_renda.py` — FOUND (modificado)

Commits afirmados, conferidos em `git log`:

- `6292219` — FOUND
- `4a5118c` — FOUND
- `d098186` — FOUND
- `a3f2032` — FOUND
- `9c13acc` — FOUND
- `db66f4a` — FOUND
