---
phase: quick-260826-es0
plan: 01
subsystem: testing
tags: [opencv, matchTemplate, fixture, tripwire, ledger, todos]

requires:
  - phase: quick-260826-dxm
    provides: "o portão da moldura da barra própria, e a pendência do terreno escuro que ele abriu"
  - phase: quick-260825-pik
    provides: "`momento_desejado` e a divergência 1 do ledger de janelas quebradas"
provides:
  - "`TestOTemplateContraGameplayNormal` — o primeiro negativo de gameplay REAL do template do diálogo, travado por teste"
  - "tripwire da geometria: alargar `FAIXA_DO_DIALOGO` sem remedir quebra a suíte"
  - "a armadilha da faixa-da-faixa registrada como teste, não como prosa"
  - "veredito raciocinado da divergência 1 do ledger — `open_count` 1 -> 0"
  - "a pendência do template arquivada em `.planning/todos/completed/` com a medição no corpo"
  - "a ideia do anel de chrome marcada como REFUTADA no passo que a propunha"
affects: [cliente, deteccao-de-desconexao, loot, terreno-escuro]

actuals:
  tokens: 4260
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "tripwire de geometria: um teste refaz a conta da região a partir da constante de produção e exige a dimensão da fixture"

key-files:
  created:
    - tests/fixtures/gameplay/faixa_com_inventario.png
    - .planning/todos/completed/2026-08-24-medir-o-template-do-dialogo-contra-gameplay-normal.md
  modified:
    - tests/test_cliente.py
    - .planning/WINDOWS.md
    - .planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md
    - .planning/STATE.md

key-decisions:
  - "A medição fica travada por `cv2.matchTemplate` DIRETO, não por `casar_dialogo`: a fixture já é a faixa, e `casar_dialogo` recortaria uma faixa da faixa (0.3586 contra 0.4618) — um número otimista por acidente."
  - "Só a faixa foi versionada, não a janela inteira: o score é idêntico (0.4618), custa 464 KB em vez de 3,6 MB, e o chat com nomes de terceiros cai fora do recorte."
  - "A divergência 1 do ledger foi arquivada como `waived`, não `fixed`: o comportamento implementado está CERTO, e a razão gravada cita o exemplo datado, o custo do estado permanente e os dois testes que puxam a regra em sentidos opostos."
  - "A ideia refutada do anel de chrome entra RISCADA no passo 4 da Solution, não numa seção nova no fim: quem for atacar a pendência lê o passo, não o rodapé."

patterns-established:
  - "Tripwire de geometria: quando um teste trava um número medido sobre uma região, um segundo teste trava a REGIÃO — senão mudar a região deixa o primeiro verde medindo outra coisa."
  - "Divergência de ledger se julga com o código aberto e com as duas regras medidas LADO A LADO na mesma entrada, não por leitura da descrição."

requirements-completed: [QUICK-260826-es0]

coverage:
  - id: D1
    description: "O template do diálogo tem um negativo de gameplay real travado: matchTemplate sobre a faixa com inventário e mercado abertos fica em 0.4618, abaixo do critério de aceite de 0.70"
    requirement: QUICK-260826-es0
    verification:
      - kind: unit
        ref: "tests/test_cliente.py::TestOTemplateContraGameplayNormal::test_gameplay_normal_com_inventario_aberto_nao_casa"
        status: pass
    human_judgment: false
  - id: D2
    description: "Alargar FAIXA_DO_DIALOGO sem remedir passa a quebrar a suíte (tripwire da geometria, provado por mutação)"
    requirement: QUICK-260826-es0
    verification:
      - kind: unit
        ref: "tests/test_cliente.py::TestOTemplateContraGameplayNormal::test_a_fixture_e_exatamente_a_faixa_de_busca"
        status: pass
      - kind: other
        ref: "mutação: FAIXA_DO_DIALOGO = (0.10, 0.30, 0.80, 0.80) -> 1 failed, 38 passed, com a mensagem (696, 1032) contra (696, 1204)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A armadilha da faixa-da-faixa está registrada no teste: casar_dialogo mede 0.3586 contra 0.4618 do matchTemplate direto, e a relação entre os dois é afirmada"
    requirement: QUICK-260826-es0
    verification:
      - kind: unit
        ref: "tests/test_cliente.py::TestOTemplateContraGameplayNormal::test_casar_dialogo_sobre_a_faixa_mede_uma_regiao_menor"
        status: pass
    human_judgment: false
  - id: D4
    description: "A fixture versionada não contém chat, nome de terceiro nem dado pessoal"
    verification:
      - kind: manual_procedural
        ref: "revisão visual de tests/fixtures/gameplay/faixa_com_inventario.png, feita pelo ORQUESTRADOR do /gsd-quick antes do dispatch"
        status: pass
    human_judgment: true
    rationale: "Imagem no git é permanente; nenhum teste automático distingue o nome de um mob do nome de um jogador. A inspeção foi feita por um humano-no-laço (o orquestrador) e o executor não a repetiu, por instrução explícita."
  - id: D5
    description: "A divergência 1 do ledger saiu de open com um veredito que cita código e testes; open_count 1 -> 0"
    requirement: QUICK-260826-es0
    verification:
      - kind: other
        ref: "node gsd-tools.cjs windows status -> open_count: 0, waived_count: 1"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py (80 passed) — nenhum teste mudou de veredito"
        status: pass
    human_judgment: false
  - id: D6
    description: "A pendência A está em .planning/todos/completed/ com a medição no corpo, e a do terreno escuro tem a ideia do anel de chrome marcada como REFUTADA no passo 4"
    requirement: QUICK-260826-es0
    verification:
      - kind: other
        ref: "ls .planning/todos/pending/ -> 1 arquivo; ls .planning/todos/completed/ -> 1 arquivo; grep IDEIA REFUTADA -> 1"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-08-26
status: complete
---

# Quick 260826-es0: Fechar as pendências (template do diálogo + ledger) Summary

**Duas afirmações que o projeto carregava sem medição por trás viraram evidência travada: o template do diálogo tem, pela primeira vez, um negativo de gameplay REAL preso por teste (0.4618 contra um limiar de 0.90), e a divergência 1 do ledger foi julgada com o código aberto e as duas regras medidas lado a lado, em vez de carimbada.**

## Performance

- **Duração:** ~20 min
- **Tasks:** 3 de 3
- **Commits:** 3
- **Suíte:** 780 passando + 2 skipped -> **783 passando + 2 skipped**, sem o jogo aberto e sem rede
- **Código de produção alterado:** nenhuma linha (`git diff 214ded4 HEAD -- l2scanner/ tools/` vazio)

## Accomplishments

### Task 1 — A medição do template, travada (`d9e7fd0`)

O template do diálogo de desconexão só tinha sido medido contra o positivo real
(0.9997) e contra a tela de login (0.5051). O frame contra o qual o scanner roda
**99% do tempo** — o jogo rodando normal — nunca tinha sido medido, e a frase que
o projeto vinha repetindo ("o risco é baixo porque terreno com textura não se
parece com uma caixa cinza") era **inferência**, não medição.

**MEDIDO** — n=10 frames de janela inteira 1720x1392, capturados da tela do
usuário (dado de entrada, D-01; não foram recapturados aqui):

| Métrica | Valor |
|---|---|
| score mínimo | 0.3068 |
| score máximo | **0.4662** |
| limiar de produção | 0.90 |
| margem no pior frame | **0.4338** |
| critério de aceite da pendência | < 0.70 — **atendido com folga de 0.2338** |

Os 10 frames incluem o pior negativo que o jogo produz naturalmente:
**inventário E mercado abertos ao mesmo tempo**, que são literalmente caixas
cinzas com botões. Mesmo esse ficou na **metade** do limiar.

**Medido neste executor, contra a fixture versionada:**

| Chamada | Score |
|---|---|
| `cv2.matchTemplate` direto sobre a faixa | **0.4618** |
| `casar_dialogo(faixa, template)` (faixa da faixa) | **0.3586** |
| geometria da fixture | **(696, 1032)** — bate exatamente com `FAIXA_DO_DIALOGO` sobre 1392x1720 |

Três testes novos em `TestOTemplateContraGameplayNormal`, ao lado do positivo:

1. **a medição** (< 0.70, e folga até 0.90 maior que 0.40);
2. **o tripwire da geometria** — recalcula a faixa a partir de
   `FAIXA_DO_DIALOGO` e de `JANELA_MEDIDA = (1392, 1720)` e exige que bata com
   `fixture.shape[:2]`. Sem ele, alargar a faixa deixaria o teste 1 **verde
   mentindo**, medindo uma região que o scanner não usa mais;
3. **a armadilha da faixa-da-faixa** — `casar_dialogo` recorta a faixa *a partir
   do que recebe*, então entregar a faixa já recortada reduz o conjunto de
   posições candidatas a um subconjunto e o máximo **só pode cair**. O teste
   afirma `faixa_da_faixa <= direto` e que ambos ficam abaixo de 0.70.

**Tripwire provado por MUTAÇÃO** (um tripwire que nunca falhou não foi provado):

```
FAIXA_DO_DIALOGO = (0.10, 0.30, 0.80, 0.80)
-> 1 failed, 38 passed
-> AssertionError: a fixture e (696, 1032), mas FAIXA_DO_DIALOGO sobre
   (1392, 1720) da (696, 1204) — remedir antes de mexer na faixa
```

Exatamente **um** teste falhou — o tripwire — e a mensagem nomeou as duas
dimensões. Revertido em seguida; `git diff -- l2scanner/` vazio.

**Fixture:** `tests/fixtures/gameplay/faixa_com_inventario.png`, 1032x696,
464 KB. Só a **faixa de busca**, não a janela inteira — o score é **preservado**
(0.4618, idêntico ao da janela), custa 3,6 MB a menos (as outras fixtures do
projeto ficam entre 76 KB e 192 KB), e o chat com nomes de terceiros cai fora do
recorte.

### Task 2 — A divergência 1 do ledger, julgada (`409861c`)

A entrada dizia que "o teste do futuro venceu", sem que ninguém tivesse voltado
ao código para dizer se venceu **com razão**. Lido antes de julgar (D-04):
`loot.py:641-706` (`momento_desejado`, docstring inclusa), `loot.py:581`
(`interpretar_pegou`), `loot.py:989` (a recusa), e os três testes:
`tests/test_loot.py:1095`, `:1120` e `:1135`.

**As duas regras, medidas lado a lado com a mesma digitação** (não lidas — rodadas):

| `agora` | `.pegou 30/12 18:00 Korzis` — implementado | recuo de ano irrestrito (o que o plano descrevia) |
|---|---|---|
| 25/08/2026 10:00 | **recusa** (`None`) | **grava 30/12/2025 18:00** |
| 03/01/2027 10:00 | 30/12/2026 18:00 | 30/12/2026 18:00 |

Esse é o argumento inteiro, e ele é mais forte do que "está certo": as duas
regras **concordam** onde o recuo estava certo (a virada do ano, que é a semana
em que o comando mais é usado) e **divergem só onde o recuo gravaria estado
permanente que o usuário não quis**. A regra implementada não perde nada; ela
fecha a porta destrutiva.

O custo que faz isso pesar: `.loot/` **nunca é podada** e `.corrigir-<nick>` só
alcança o registro **mais recente** — um `pegou_` gravado em dezembro do ano
passado por um dedo escorregado em agosto seria permanente e inalcançável.

A recusa também **não vira silêncio**: `responder_atribuicao` devolve
`"Essa data nao aponta para nenhum momento que ja passou — ..."`
(`loot.py:989`), afirmado em `tests/test_loot.py:1131`.

E `STATE.md ## Decisions` já traz `[Phase 4]: [loot]: Data sem ano resolve para
a leitura de calendario MAIS PROXIMA` — o ledger registrava divergência contra
um plano que o próprio projeto **já havia substituído**.

**Veredito: CERTO.** Arquivado como `waived` com a razão acima gravada na
entrada. `open_count` **1 -> 0**. Nenhum dos três testes existentes precisou
mudar de veredito; `tests/test_loot.py` segue com 80 passando.

### Task 3 — Registros (`805a86c`)

**(a)** A pendência de 2026-08-24 ganhou uma seção `## Resolution` com a tabela
da medição, o critério de aceite e o veredito, a justificativa do recorte e os
nomes dos três testes — e então foi movida com a ferramenta do projeto
(`gsd-tools todo complete`, não `mv`) para `.planning/todos/completed/`. O git
registrou a operação como **rename**, não como delete+add.

**(b)** O passo 4 da `## Solution` do todo do terreno escuro propunha
**exatamente** a ideia que já foi medida e falhou. Ele está agora riscado e
marcado **REFUTADO**, com o bloco medido logo abaixo, **no lugar onde ele é
lido**:

```
anel de 3 px em volta da região hp_proprio
  barra livre     média 70.7
  coberta (n=9)   média 36.4 .. 63.8
contra o teste atual: 73.7 vs 48.9  ->  25 pontos de separação a menos
```

Com o motivo, que é estrutural e não numérico: quando uma janela grande do jogo
cobre a barra, ela **cobre a vizinhança junto** — o anel de fora não é refúgio
nenhum. Quem chegar ali pelo passo 3 precisa de outro **discriminador**, não de
outra região para amostrar o mesmo discriminador.

A pendência **continua aberta e continua major**: ela espera uma gravação em
ambiente escuro que só o usuário pode produzir. `## Problem` e passos 1-3 e 5
intactos, e **`l2scanner/visao.py` sem uma linha tocada** (D-05, verificado por
`git diff --name-only -- l2scanner/visao.py` vazio).

**(c)** `STATE.md`: a linha da pendência fechada foi trocada pela que segue
aberta (`major | A moldura da barra própria em terreno escuro | detection`).
Sair com a tabela vazia anunciaria que o projeto não tem pendência nenhuma, que
é o oposto da verdade. `## Quick Tasks Completed` não foi tocado — essa linha é
do encerramento do `/gsd-quick`.

## Verificação

| # | Verificação | Resultado |
|---|---|---|
| 1 | `python -m pytest tests/ -q` | **783 passed, 2 skipped** (era 780 + 2) |
| 2 | `windows status` | `open_count: 0`, `waived_count: 1` |
| 3 | `ls .planning/todos/pending/` | 1 arquivo (terreno escuro) |
| 4 | `ls .planning/todos/completed/` | 1 arquivo (template) |
| 5 | fixture rastreada pelo git | `git ls-files` a lista |
| 6 | `l2scanner/` intocado | `git diff --stat 214ded4 HEAD -- l2scanner/ tools/` vazio |
| 7 | tripwire provado por mutação | 1 failed / 38 passed, com as dimensões na mensagem |

## Deviations from Plan

### Auto-fixed

**1. [Regra 3 — comando de verificação do plano estava errado] `git check-ignore -v` não devolve 1**

- **Encontrado em:** Task 1
- **Problema:** a verificação do plano era
  `git check-ignore -v <fixture>; test $? -eq 1`. Medido: com `-v`, o git
  devolve **0**, porque ele reporta o último padrão que casou **incluindo
  padrões de negação** — e a linha impressa é
  `.gitignore:17:!tests/fixtures/**/*.png`, ou seja, a negação que **reabre** o
  arquivo. O plano leu o exit code de `-v` como se fosse o de "está ignorado".
- **Correção:** usada a forma sem `-v`, que é a que carrega a semântica de
  ignorado/não-ignorado — `git check-ignore <fixture>` devolve **1**
  (não ignorado). Confirmado pela prova definitiva: `git add` sem `-f` rastreou
  o arquivo, e `git ls-files` o lista.
- **Arquivos:** nenhum (correção de procedimento de verificação)
- **Nota:** não foi registrado no ledger de janelas quebradas de propósito. O
  defeito é no **texto de um comando do plano**, não no produto; a verificação
  foi executada e passou na forma corrigida, então não é `unrun-verify`.
  Registrar como `open` levaria `open_count` de volta a 1 e derrubaria uma das
  verdades que esta própria quick entregou (D-04), em troca de um typo de plano.
  A decisão está aqui, por escrito, em vez de ser uma omissão.

**2. [Contexto do dispatch estava desatualizado] o branch não é `master`**

- **Encontrado em:** verificação final
- **Problema:** o briefing dizia "branch master" e o snapshot de git do ambiente
  apontava `69e4716` como HEAD. Ambos estavam **stale**: o HEAD real era
  `214ded4` e o branch corrente é **`feat/solo-boss-join`**. Entre o snapshot e o
  dispatch entraram a quick `260826-dxm` (4 commits) e o plano desta quick.
- **Ação:** nenhuma. Os três commits foram feitos no branch que estava em check-out
  (`feat/solo-boss-join`), sem trocar de branch — que é o comportamento correto.
  `master` está em `cd54106`, 4 commits atrás (`214ded4` + os três desta quick).
  **A divergência entre `master` e `feat/solo-boss-join` precede este trabalho**
  e é do estado de trabalho do usuário; está registrada aqui para não virar
  surpresa no `/gsd-ship`.

**3. [Fora de escopo — NÃO tocado] `.planning/ROADMAP.md` apareceu modificado durante a execução**

- **Encontrado em:** verificação final
- **Problema:** `git status` no fim mostra `M .planning/ROADMAP.md`. No início da
  execução o working tree tinha **apenas** `?? .gsd/` e `?? tests/fixtures/gameplay/`.
  O diff é da **Fase 10 (lista de presença do Solo Boss)** — a correção de que a
  descoberta de conversa por etiqueta já existe em `comandos.py`, e que o que
  falta é o nível de autorização. **Nada a ver com esta quick.**
- **Ação:** nenhuma, de propósito. A restrição do dispatch é explícita
  (*"Do NOT update ROADMAP.md"*), e nenhum dos três commits o inclui — conferido
  em `git diff --stat 214ded4 HEAD`, que lista 5 arquivos e nenhum deles é o
  ROADMAP. A mudança foi deixada **intacta e não-staged**.
- **Atenção para quem fizer o commit de docs:** essa alteração **não é desta
  tarefa**. Ela veio de fora da execução (orquestrador, outra sessão, ou edição
  do usuário) e não deve ser varrida junto por um `git add .planning/` sem
  leitura.

### Não houve

- Nenhum defeito encontrado na Task 2 — o caminho "teste que falha primeiro,
  depois correção, depois `windows fixed`" não foi acionado.
- Nenhum stub, nenhum teste pulado novo (os 2 skipped são pré-existentes),
  nenhum `<verify>` deixado sem rodar.
- Nenhuma dependência instalada (T-es0-SC: aceito, e cumprido).

## Threat Model — dispositions

| Threat | Disposição | O que de fato aconteceu |
|---|---|---|
| **T-es0-01** — vazamento de dado pessoal pela fixture | **mitigado** | A revisão visual da imagem **foi feita pelo ORQUESTRADOR do `/gsd-quick`**, antes do dispatch, e o resultado veio no briefing: a fixture mostra a janela do XM Market (itens e preços públicos do jogo), nomes de mobs, e "TioMad" — que já está no `calibration.json` e em fixtures existentes do repo. **Sem chat, sem nome de terceiro, sem dado pessoal.** Aprovada para commit. O executor **não repetiu** a inspeção, por instrução explícita, e registra aqui quem a fez. A geometria colabora: a faixa é y 0.30-0.80 e x 0.20-0.80, e o chat do jogo fica embaixo à esquerda, fora dela. |
| **T-es0-02** — carimbar o ledger sem evidência | **mitigado** | O `waive` só saiu depois de ler `loot.py:641-706`, `:581`, `:989` e os três testes nominais, e a razão gravada cita o exemplo datado (30/12/2025 em 25/08/2026), o motivo do estado ser permanente e inalcançável, e os dois testes que puxam a regra em sentidos opostos. |
| **T-es0-03** — mexer no portão da barra própria | **mitigado** | `git diff --name-only -- l2scanner/visao.py` vazio. Nenhuma linha de produção alterada em toda a quick. |
| **T-es0-SC** — instalação de pacote | **aceito, e nulo** | Nenhum `pip install`, nenhuma dependência nova. |

## Lições

- **Um número medido só vale com a região travada junto.** O teste da medição e
  o tripwire da geometria são um par: separados, o primeiro fica verde medindo
  outra coisa no dia em que a constante mudar. Isso é o mesmo padrão do tripwire
  `set(_AJUDA) == set(Comando)` da quick `260825-t1n`, aplicado a geometria em
  vez de a vocabulário — terceira aparição do padrão no projeto.
- **A função que recorta "a partir do que recebe" é uma armadilha de medição.**
  `casar_dialogo(faixa)` mede 0.3586 e `matchTemplate(faixa)` mede 0.4618 — quem
  usasse o primeiro como "a medição" travaria um número **otimista** por
  acidente, e otimismo do lado do negativo é exatamente o lado errado. A
  armadilha virou teste, não comentário.
- **Divergência de ledger se julga rodando as duas regras, não lendo a
  descrição.** Rodar o recuo irrestrito ao lado do implementado, na mesma
  entrada, transformou "está certo" num argumento: elas concordam onde o plano
  acertou e divergem só onde ele gravaria estado permanente. Nenhuma leitura da
  descrição da entrada teria produzido isso.
- **Ideia refutada tem que morar onde a ideia é lida.** Uma seção "coisas que
  tentamos" no fim do documento não impede ninguém — o passo 4 riscado, com os
  números logo abaixo, impede.

## Self-Check: PASSED

Arquivos criados, conferidos no disco:

- `tests/fixtures/gameplay/faixa_com_inventario.png` — FOUND (rastreado por `git ls-files`)
- `.planning/todos/completed/2026-08-24-medir-o-template-do-dialogo-contra-gameplay-normal.md` — FOUND

Commits, conferidos em `git log`:

- `d9e7fd0` — FOUND — `test(es0-01): o template do dialogo, medido contra gameplay real`
- `409861c` — FOUND — `docs(es0-02): a divergencia do ledger julgada contra o codigo, nao carimbada`
- `805a86c` — FOUND — `docs(es0-03): a pendencia do template fechada, e uma saida a menos no terreno escuro`

`.planning/STATE.md` foi editado (troca da linha da pendência) e **deixado sem
commit de propósito**: o encerramento do `/gsd-quick` faz o commit de docs.
