---
phase: quick-260826-vtt
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_sessao.py
  - .planning/phases/10-lista-de-presenca-do-solo-boss-pelo-whatsapp/deferred-items.md
  - .planning/milestone.lock
  - .planning/STATE.md
autonomous: true
requirements: [QUICK-260826-vtt]

estimate:
  tokens: 20000
  raw_tokens: 20000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "`python -m ruff check tests/test_sessao.py` devolve `All checks passed!` — os dois F401 de `VigiaDeManutencao` sairam, e sairam pelo `--fix` do ruff, nao por edicao a mao (D-01)."
    - "O nome que ERA usado sobreviveu: `TipoDeAvisoDeManutencao` continua importado dentro de `test_o_faltam5_tambem_atravessa_a_costura`, porque o `assert tipos == [...]` depende dele. Aquela linha tinha DOIS nomes e so um saiu (D-02)."
    - "Os dois imports LEGITIMOS de `VigiaDeManutencao` continuam de pe: a contagem `grep -c 'import.*VigiaDeManutencao' tests/test_sessao.py` cai de 4 para exatamente 2, nunca para 0 (D-02)."
    - "A suite nao piorou: `python -m pytest tests/ -q` continua em `1077 passed, 2 skipped`. Mesmo numero de testes — nenhum teste removido, enfraquecido ou marcado para pular (D-03)."
    - "O diff versionado de codigo desta tarefa e de DUAS linhas em UM arquivo: 1 insercao, 2 delecoes. `ruff format` nao foi rodado e nenhum outro lint do repo foi consertado — o repo tem 31 erros de ruff no total e 29 seguem la de proposito (D-04)."
    - "`.planning/milestone.lock` nao existe mais: a fase 10 deixou de carregar a reivindicacao de uma sessao morta (pid 28896 inexistente, `updated_at` de 11h atras contra um TTL de 4h) (D-05)."
    - "O registro do item adiado do plano 10-04 esta fechado no lugar onde ele e lido: `deferred-items.md` diz que o item 1 foi resolvido, por qual quick task, e que os numeros de linha do registro tinham envelhecido (D-06)."
    - "O commit carrega SO o que esta tarefa mudou: `git show --name-only --format= HEAD` lista o teste, o `deferred-items.md` e os artefatos de planejamento, e nenhum caminho sob `.gsd/` — o `git add` foi por caminho explicito (D-07)."
  artifacts:
    - "tests/test_sessao.py — sem os dois F401, 1167 linhas (era 1168)"
    - ".planning/phases/10-lista-de-presenca-do-solo-boss-pelo-whatsapp/deferred-items.md — item 1 marcado como resolvido"
    - ".planning/quick/260826-vtt-fechar-as-duas-pendencias-mecanicas-da-f/260826-vtt-SUMMARY.md"
  key_links:
    - "A linha `from l2scanner.manutencao import TipoDeAvisoDeManutencao, VigiaDeManutencao` e o unico ponto onde este conserto pode destruir algo: apagar a linha inteira em vez de encurta-la quebra `test_o_faltam5_tambem_atravessa_a_costura` com NameError. E por isso que o conserto e `ruff --fix` e nao `sed`."
    - "O `git add` desta tarefa tem que ser POR ARQUIVO. `.gsd/` e `.planning/milestone.lock` sao nao-rastreados e NAO estao no `.gitignore` (`git check-ignore` sai com 1 nos dois) — um `git add -A` varreria `.gsd/` inteiro para dentro do commit."
---

<objective>
Fechar as duas pendencias mecanicas que sobraram da Fase 10: os dois `F401` de
`VigiaDeManutencao` em `tests/test_sessao.py`, registrados como item adiado do
plano 10-04, e o `.planning/milestone.lock` deixado por uma sessao que morreu
sem soltar a reivindicacao da fase.

Purpose: as duas ja foram diagnosticadas e escritas — o `deferred-items.md` ate
indica o comando do conserto ("Cabe num `/gsd-quick`"). Enquanto ficam abertas,
`ruff check` sobre o arquivo de teste devolve erro (e ensina a suite a conviver
com lint quebrado) e o lock morto continua sujando o estado da fase.

Output: dois F401 a menos, um lock a menos, o registro do item adiado fechado.
Nenhuma linha de `l2scanner/` tocada.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@.planning/phases/10-lista-de-presenca-do-solo-boss-pelo-whatsapp/deferred-items.md
</context>

## O estado medido agora, antes de mexer

Tudo abaixo foi conferido no momento do planejamento, no branch
`feat/solo-boss-join`. Sao os numeros contra os quais o conserto se prova.

**Os dois F401 continuam la — e NAO nas linhas que o registro diz:**

```
F401 [*] `l2scanner.manutencao.VigiaDeManutencao` imported but unused
   --> tests/test_sessao.py:1037   (em test_as_duas_instancias_competem_pelo_mesmo_marcador)
   --> tests/test_sessao.py:1069   (em test_o_faltam5_tambem_atravessa_a_costura)
Found 2 errors. [*] 2 fixable with the `--fix` option.
```

O `deferred-items.md` fala em **897 e 929**. Esses numeros envelheceram — o
arquivo cresceu para 1168 linhas depois que o registro foi escrito. **Localizar
pelo `ruff`, nunca pelo numero de linha**: o registro esta certo no diagnostico e
desatualizado na coordenada.

**Ha QUATRO imports de `VigiaDeManutencao` no arquivo, e so dois estao errados:**

| Linha | Situacao |
|---|---|
| 961 | **USADO** — `return VigiaDeManutencao(...)` na 963, dentro do ajudante `_vigia_das_duas_escalas` |
| 989 | **USADO** — `return VigiaDeManutencao(ler_texto=ler, ...)` na 992 |
| 1037 | **F401** — o teste constroi o vigia pelo ajudante, nunca pela classe |
| 1069 | **F401 parcial** — a linha importa dois nomes, e `TipoDeAvisoDeManutencao` E usado no `assert tipos == [...]` |

A 1069 e a unica armadilha do plano: dois nomes, so um sai. O `ruff --fix` ja faz
a coisa certa — o diff foi pre-visualizado com `--fix --diff` e e exatamente
este, duas linhas e nada mais:

```
@@ -1034,7 +1034,6 @@
-        from l2scanner.manutencao import VigiaDeManutencao
@@ -1066,7 +1065,7 @@
-        from l2scanner.manutencao import TipoDeAvisoDeManutencao, VigiaDeManutencao
+        from l2scanner.manutencao import TipoDeAvisoDeManutencao
```

Um diff maior que isso e sinal de que algo saiu do trilho.

**O lock aponta para um processo que nao existe:**

```json
{ "phase": "10", "session": "claude-code-session-id-f04eb967-...", "pid": 28896,
  "updated_at": 1787755731307 }
```

`tasklist /FI "PID eq 28896"` nao acha o processo. O `updated_at` traduz para
`2026-08-26T14:48:51Z` — **11,15 h atras**, contra um `MILESTONE_LOCK_TTL_MS` de
**4 h**. Por duas contas independentes (pid morto, TTL estourado) a reivindicacao
esta morta. O arquivo e **nao-rastreado** (`?? .planning/milestone.lock`), entao
apaga-lo nao produz diff de conteudo versionado.

Nada no fluxo `/gsd-quick` reescreve o arquivo: quem grava reivindicacao e
`state.begin-phase` (`state.cjs:3428`), e esta tarefa nao roda begin-phase.

**Baseline da suite, a nao piorar:** `python -m pytest tests/ -q` ->
`1077 passed, 2 skipped in 23.80s`. Os 2 skips sao de OCR e sao pre-existentes.

## Tarefas

<tasks>

<task type="auto">
  <name>Tarefa 1: os dois F401 saem do arquivo de teste, e o item adiado fecha</name>
  <files>tests/test_sessao.py, .planning/phases/10-lista-de-presenca-do-solo-boss-pelo-whatsapp/deferred-items.md</files>

  <read_first>
- `tests/test_sessao.py` linhas 955-1000 — os DOIS imports legitimos, para ver
  com os proprios olhos por que eles ficam
- `tests/test_sessao.py` linhas 1026-1090 — os dois testes que carregam os F401
- `.planning/phases/10-lista-de-presenca-do-solo-boss-pelo-whatsapp/deferred-items.md`
  </read_first>

  <action>
Rodar o conserto pelo comando que o proprio registro indicou (D-01):
`python -m ruff check tests/test_sessao.py --fix`. Escopo no ARQUIVO, nunca no
diretorio nem no ponto — `python -m ruff check .` acusa 31 erros no repo inteiro
e 29 deles nao pertencem a esta tarefa (D-04).

Nao rodar `ruff format`. `python -m ruff format --check tests/test_sessao.py` ja
falha hoje, ANTES de qualquer mudanca ("Would reformat"), entao formatar aqui
trocaria um diff de duas linhas por uma reformatacao do arquivo inteiro — que e
exatamente a mistura que fez este item ser adiado em vez de consertado dentro do
plano 10-04 (D-04).

Conferir o resultado com `git diff --numstat tests/test_sessao.py`: tem que dar
`1  2  tests/test_sessao.py` (1 insercao, 2 delecoes). Se der outra coisa,
desfazer com `git checkout -- tests/test_sessao.py` e refazer com escopo certo,
em vez de commitar um diff que ninguem consegue ler depois.

Depois, no `deferred-items.md`: marcar o item 1 como RESOLVIDO no titulo da
secao, dizendo por qual quick task (`260826-vtt`) e o que exatamente foi feito —
duas linhas, sendo que uma foi ENCURTADA e nao apagada, porque ela trazia um
segundo nome que o teste usa (D-06). Registrar tambem, em uma frase, que os
numeros de linha do registro (897 e 929) tinham envelhecido para 1037 e 1069: e
o unico detalhe do item capaz de mandar a proxima pessoa para o lugar errado, e
custa uma linha prevenir.
  </action>

  <verify>
    <automated>python -m ruff check tests/test_sessao.py</automated>
    <automated>test "$(grep -c 'import.*VigiaDeManutencao' tests/test_sessao.py)" = "2"</automated>
    <automated>test "$(grep -c 'TipoDeAvisoDeManutencao' tests/test_sessao.py)" = "5"</automated>
    <automated>git diff --numstat tests/test_sessao.py</automated>
    <automated>python -m pytest tests/ -q</automated>
  </verify>

  <acceptance_criteria>
- `ruff check` sobre o arquivo devolve `All checks passed!`
- A contagem de imports de `VigiaDeManutencao` no arquivo e exatamente **2** (era
  4): os dois ajudantes sobrevivem, os dois testes perdem o seu
- A contagem de `TipoDeAvisoDeManutencao` no arquivo segue **5**, inalterada — a
  linha 1069 encolheu, nao sumiu
- `git diff --numstat tests/test_sessao.py` -> `1  2` (mais que isso reprova)
- `python -m pytest tests/ -q` -> **1077 passed, 2 skipped**. Nem um teste a
  menos, nem um skip a mais
- `deferred-items.md` diz que o item 1 esta resolvido, cita `260826-vtt`, e
  corrige as coordenadas 897/929 -> 1037/1069
  </acceptance_criteria>

  <done>
Os dois F401 sairam pelo `--fix`, os dois imports que o codigo usa continuam
la, a suite fechou no mesmo 1077/2 do baseline, e o registro do item adiado
deixou de estar aberto.
  </done>
</task>

<task type="auto">
  <name>Tarefa 2: a reivindicacao morta sai do .planning/, e o commit sai por arquivo</name>
  <files>.planning/milestone.lock (removido), tests/test_sessao.py, .planning/phases/10-lista-de-presenca-do-solo-boss-pelo-whatsapp/deferred-items.md</files>

  <precondition>O pid registrado no lock (28896) nao esta rodando — reconferir com `tasklist /FI "PID eq 28896"` antes de apagar; se o processo existir, PARAR e avisar, porque ai ha uma segunda sessao viva na mesma arvore.</precondition>

  <action>
Apagar `.planning/milestone.lock` (D-05). O arquivo e nao-rastreado, entao a
remocao nao entra no diff — e por isso ela NAO e "uma mudanca do commit", e sim
uma limpeza que o commit precisa nao atrapalhar.

Commitar em seguida, e **por arquivo**:

`git add tests/test_sessao.py` e o caminho do `deferred-items.md`, mais os
artefatos de planejamento desta quick task. **Nunca `git add -A` nem `git add .`**
(D-07): `.gsd/` e `.planning/milestone.lock` aparecem como `??` no status e
`git check-ignore` sai com codigo 1 nos dois — ou seja, nao estao ignorados, so
nao rastreados. Um add abrangente arrastaria `.gsd/` inteiro para dentro do
commit desta tarefa.

Sem branch nova: o trabalho fica em `feat/solo-boss-join`, que ja e o branch
corrente (`git.branching_strategy = "none"`, `quick_branch_template = null`).

Mensagem no idioma do log do projeto — portugues sem acento, escopo `quick-`:
`fix(quick-260826-vtt): os dois imports mortos saem do teste e o lock morto sai do .planning`

Conferir depois do commit que `git status --porcelain` nao lista mais
`.planning/milestone.lock` e que `.gsd/` continua fora do commit
(`git show --stat --name-only HEAD` nao pode citar `.gsd/`).
  </action>

  <verify>
    <automated>test ! -e .planning/milestone.lock</automated>
    <automated>test -z "$(git status --porcelain .planning/milestone.lock)"</automated>
    <automated>git show --name-only --format= HEAD</automated>
    <automated>git rev-parse --abbrev-ref HEAD</automated>
  </verify>

  <acceptance_criteria>
- `.planning/milestone.lock` nao existe no disco e nao aparece em
  `git status --porcelain`
- `git show --name-only --format= HEAD` lista `tests/test_sessao.py`,
  `deferred-items.md` e os artefatos de planejamento — e **nenhum caminho sob
  `.gsd/`**
- O branch corrente continua sendo `feat/solo-boss-join`; nenhuma branch nova foi
  criada
- A mensagem do commit esta em portugues sem acento, no formato
  `fix(quick-260826-vtt): ...`, igual ao resto do log
  </acceptance_criteria>

  <done>
O lock morto sumiu, o commit carrega so o que esta tarefa mudou de verdade, e a
arvore de trabalho voltou a ter apenas `.gsd/` como nao-rastreado.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ferramenta -> arvore de trabalho | `ruff --fix` e `rm` escrevem no repo sem revisao previa linha a linha |
| executor -> indice do git | `git add` decide o que entra no historico; `.gsd/` e o lock estao ao alcance de um add abrangente |

Nenhuma superficie de rede, entrada de usuario ou credencial e tocada: a tarefa
mexe em um arquivo de teste e apaga um arquivo de estado local. O modelo de
ameaca real aqui e **perda de dado no repo**, nao ataque.

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-vtt-01 | Tampering | `ruff --fix` com escopo largo (`.` em vez do arquivo) | medium | mitigate | Comando fixado no arquivo unico; portao `git diff --numstat` exige exatamente `1 2`, e qualquer coisa alem disso reprova a tarefa |
| T-vtt-02 | Tampering | Import de dois nomes na linha 1069 | high | mitigate | Conserto por `ruff --fix` (que preserva `TipoDeAvisoDeManutencao`), mais o portao de contagem `== 5` e a suite inteira |
| T-vtt-03 | Tampering | `git add -A` varrendo `.gsd/` para o historico | medium | mitigate | `git add` por caminho explicito; portao le `git show --name-only` e reprova se citar `.gsd/` |
| T-vtt-04 | Denial of Service | Apagar um lock de uma sessao VIVA | low | mitigate | `<precondition>` reconfere o pid 28896 antes de apagar; o lock e advisory (avisa, nao bloqueia) e ja passou do TTL de 4h |
| T-vtt-05 | Repudiation | Conserto sem registro, item adiado reaberto por engano no futuro | low | mitigate | `deferred-items.md` fecha o item citando a quick task e corrige as coordenadas envelhecidas |
| T-vtt-SC | Tampering | npm/pip/cargo installs | n/a | accept | Nenhuma dependencia nova, nenhum instalador rodado — `ruff` e `pytest` ja estao instalados no `python` do sistema |
</threat_model>

## Fora de escopo

- **Os outros 29 erros de ruff do repo.** `python -m ruff check .` acusa 31 no
  total; so os 2 deste arquivo estao registrados como item adiado e so eles saem.
- **`ruff format`.** O arquivo ja falha o `--check` antes de qualquer mudanca;
  formatar aqui esconderia o conserto de duas linhas dentro de uma reformatacao.
- **Qualquer arquivo de `l2scanner/`.** A tarefa nao toca em codigo de producao.
- **A validacao em campo da Fase 10.** Os 6 itens de UAT que exigem a ponte
  Baileys real seguem abertos e sao de `/gsd-verify-work 10`, nao daqui.
- **Por `milestone.lock` no `.gitignore`.** E uma decisao sobre o que o GSD
  gera, vale para todo projeto, e nao se resolve de passagem numa quick task.
- **Os 2 skips de OCR da suite.** Pre-existentes; a tarefa os preserva, nao os
  investiga.

## Restricoes do projeto

- Branch: continuar em `feat/solo-boss-join`, sem criar branch nova
  (`git.branching_strategy = "none"`, `quick_branch_template = null`)
- Portugues SEM acento em identificador, docstring, comentario e mensagem de
  commit; assunto do commit no formato `fix(quick-260826-vtt): ...`
- Nenhuma dependencia nova
- Usar o `python` do sistema para `pytest` e `ruff` (o `.venv` nao tem pytest)
- Baseline a preservar: **1077 passed, 2 skipped**. Nenhum teste enfraquecido,
  removido ou pulado

<verification>
1. `python -m ruff check tests/test_sessao.py` -> `All checks passed!`
2. `python -m pytest tests/ -q` -> `1077 passed, 2 skipped`
3. `git diff --numstat` do commit toca **um** arquivo de codigo, com `1 2`
4. `.planning/milestone.lock` ausente do disco e do `git status`
5. `git show --name-only --format= HEAD` sem nenhum caminho sob `.gsd/`
</verification>

<success_criteria>
As duas pendencias mecanicas da Fase 10 estao fechadas com o menor diff possivel:
`ruff check` limpo no arquivo de teste, suite no mesmo 1077/2 do baseline, lock
morto removido, item adiado marcado como resolvido no lugar onde ele e lido — e
zero linha de `l2scanner/` tocada.
</success_criteria>

<output>
Criar `.planning/quick/260826-vtt-fechar-as-duas-pendencias-mecanicas-da-f/260826-vtt-SUMMARY.md`
ao terminar, registrando: o diff real (numstat), o antes/depois da suite, e a
correcao das coordenadas do item adiado.
</output>
