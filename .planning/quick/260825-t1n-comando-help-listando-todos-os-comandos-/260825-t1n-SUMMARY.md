---
phase: quick-260825-t1n
plan: 01
subsystem: api
tags: [whatsapp, chatwoot, comandos, ajuda, tripwire, enum, cli]

requires:
  - phase: quick-260825-pik
    provides: "`Comando.LOOT_ATRIBUIR` e o `.pegou <hora> <nick>` — o quinto comando nascido no mesmo dia, e o gatilho desta tarefa"
  - phase: quick-260825-cou
    provides: "`interpretar_dinamico` e a superficie dinamica (`.loot-<nick>`, `.<nick>`) que nao mora no `_VOCABULARIO`"
provides:
  - "`Comando.AJUDA` e o comando `.help` (tambem `.ajuda`, `.comandos`, `.?`)"
  - "Tabela `_AJUDA: dict[Comando, LinhaDeAjuda]` — a unica fonte da lista de comandos"
  - "`texto_de_ajuda()` — a lista montada da tabela, sem moldura e sem ANSI"
  - "Tripwire `set(_AJUDA) == set(Comando)`: comando novo sem ajuda quebra a suite"
  - "`_para_o_console()` — resposta de varias linhas nunca e moldurada no log"
affects: [comandos, whatsapp, console, documentacao]

actuals:
  tokens: 40400
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Texto de interface DERIVADO de uma tabela chaveada pelo enum, com tripwire de cobertura"
    - "Regra de formatacao do console decidida pela FORMA do texto (uma linha vs varias), nao pelo comando de origem"

key-files:
  created: []
  modified:
    - l2scanner/comandos.py
    - l2scanner/__main__.py
    - tests/test_comandos.py
    - README.md

key-decisions:
  - "A ajuda e DERIVADA da tabela `_AJUDA`, nunca escrita a mao — cinco comandos nasceram em um dia e ajuda desatualizada ensina sintaxe que nao funciona"
  - "A tabela e chaveada pelo ENUM e nao pelo `_VOCABULARIO`, porque os cinco comandos dinamicos nao moram no vocabulario — um tripwire contra o vocabulario nao os enxergaria"
  - "O tripwire foi provado por MUTACAO, nao por leitura: um membro descartavel no enum fez o teste falhar nomeando-o"
  - "O round-trip de sintaxe atravessa `comandos_novos` real, com as cinco travas ligadas — um parser paralelo no teste provaria que o teste concorda consigo mesmo"
  - "A ajuda nao e moldurada em NENHUM dos dois destinos, e a regra do console vale para qualquer resposta multilinha — nao e caso especial do `.help`"
  - "Nenhum portao novo: a ajuda atravessa as cinco travas que todo comando ja atravessa (D-07)"

patterns-established:
  - "Tripwire de cobertura enum->tabela: crescer o enum sem crescer a tabela quebra a suite de proposito"
  - "Round-trip de sintaxe: tudo que a interface ANUNCIA volta pelo caminho real de leitura como o que ela prometeu"

requirements-completed: [QUICK-260825-t1n]

coverage:
  - id: D1
    description: "`.help` (e `.ajuda`, `.comandos`, `.?`) responde com a lista completa dos comandos, derivada da tabela"
    requirement: QUICK-260825-t1n
    verification:
      - kind: unit
        ref: "tests/test_comandos.py#TestAjuda::test_as_formas_escritas_da_ajuda"
        status: pass
      - kind: integration
        ref: "tests/test_comandos.py#TestAjudaNaCostura::test_o_que_e_despachado_e_a_tabela_INTEIRA"
        status: pass
    human_judgment: false
  - id: D2
    description: "Comando novo sem entrada na tabela de ajuda quebra a suite"
    requirement: QUICK-260825-t1n
    verification:
      - kind: unit
        ref: "tests/test_comandos.py#TestAjuda::test_todo_comando_tem_linha_na_tabela_de_ajuda"
        status: pass
      - kind: other
        ref: "mutacao: membro MUTANTE_DESCARTAVEL no enum -> tripwire falha nomeando-o (transcrito abaixo)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Toda sintaxe anunciada pela ajuda volta pelo `comandos_novos` como o comando certo"
    requirement: QUICK-260825-t1n
    verification:
      - kind: integration
        ref: "tests/test_comandos.py#TestAjuda::test_toda_sintaxe_anunciada_volta_como_o_comando_certo"
        status: pass
    human_judgment: false
  - id: D4
    description: "Resposta so na conversa de origem, sem moldura no WhatsApp nem no console"
    requirement: QUICK-260825-t1n
    verification:
      - kind: integration
        ref: "tests/test_comandos.py#TestAjudaNaCostura::test_responde_SO_na_conversa_de_origem"
        status: pass
      - kind: integration
        ref: "tests/test_comandos.py#TestAjudaNaCostura::test_a_ajuda_no_LOG_tambem_sai_sem_moldura"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py#TestMolduraDoConsole::test_resposta_de_varias_linhas_sai_CRUA"
        status: pass
    human_judgment: false
  - id: D5
    description: "Telefone fora da allowlist continua sem resposta nenhuma"
    requirement: QUICK-260825-t1n
    verification:
      - kind: integration
        ref: "tests/test_comandos.py#TestAjudaNaCostura::test_telefone_FORA_da_allowlist_e_ignorado"
        status: pass
      - kind: integration
        ref: "tests/test_comandos.py#TestAjudaNaCostura::test_o_dono_na_allowlist_continua_recebendo"
        status: pass
    human_judgment: false
  - id: D6
    description: "O texto como ele chega no celular: familias na ordem combinada, linhas curtas o bastante para a tela do telefone"
    verification:
      - kind: unit
        ref: "tests/test_comandos.py#TestAjuda::test_as_familias_saem_na_ordem_combinada"
        status: pass
    human_judgment: true
    rationale: "A ordem e o comprimento sao testados, mas se o texto LE BEM no WhatsApp do usuario — quebra de linha, legibilidade no celular — so quem manda um `.help` de verdade sabe."

duration: 12min
completed: 2026-08-25
status: complete
---

# Quick 260825-t1n: comando `.help` Summary

**`.help` responde com a lista de todos os comandos que o scanner obedece — e a lista e DERIVADA de uma tabela chaveada pelo enum `Comando`, com um tripwire que quebra a suite quando alguem acrescenta um comando sem documenta-lo.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-08-25T21:00:00-03:00
- **Completed:** 2026-08-25T21:12:00-03:00
- **Tasks:** 2 de 2
- **Files modified:** 4
- **Testes:** 730 passando + 2 skipped -> **746 passando + 2 skipped**

## Accomplishments

- **A ajuda nao pode envelhecer.** O texto sai da tabela `_AJUDA`, e o tripwire
  `set(_AJUDA) == set(Comando)` quebra a suite no dia em que alguem acrescentar
  um comando sem documenta-lo. O projeto ganhou CINCO comandos em UM dia; uma
  lista escrita a mao estaria desatualizada antes do fim da semana — e ajuda
  desatualizada e pior que ajuda nenhuma, porque ensina sintaxe que nao funciona
  e faz o usuario concluir que o bot esta quebrado.
- **A ajuda nao tem como ensinar sintaxe que nao funciona.** Cada sintaxe da
  tabela e passada de volta pelo caminho REAL de leitura
  (`comandos_novos` -> `interpretar` -> `interpretar_dinamico`), com as cinco
  travas ligadas, e tem que voltar como o `Comando` que a ajuda diz.
- **Um defeito real consertado de passagem.** `atender_comandos` registrava
  `destacar(resposta)` no log, e `destacar` chama `moldurar`, cuja largura e
  `max(LARGURA, len(miolo) + len(carimbo))` sobre a string INTEIRA. Uma resposta
  de dezenove linhas sairia no console e no `scanner.log` com uma borda de
  **725 caracteres** — medido pelo teste `test_a_conta_de_moldurar_e_o_motivo`.
  O desvio vale para qualquer resposta multilinha, nao so para o `.help`.
- **`.solo` e `.party` entraram no README.** Existiam desde a quick de 24/08 e
  nunca tinham sido documentados — exatamente o envelhecimento que a tabela
  derivada previne do lado do bot, agora consertado do lado do README.

## Task Commits

1. **Task 1 (tracer): a tabela de ajuda, o tripwire e o texto que sai dela** — `ab2d6a7` (feat)
2. **Task 2: a costura — responder onde perguntaram, sem moldura, e a linha do README** — `ee86740` (feat)

_Os testes foram escritos ANTES do codigo nos dois casos (RED observado e transcrito
abaixo), mas test e feat foram para o MESMO commit por instrucao explicita do
orquestrador: "rode `python -m pytest` a partir da raiz antes de cada commit"._

## A prova do tripwire por MUTACAO

Nao e opcional, e nao foi feita por leitura. Um membro descartavel entrou no
enum `Comando` **sem tocar na tabela `_AJUDA`**:

```
membro descartavel acrescentado ao enum, SEM tocar na tabela _AJUDA
=============== MUTACAO: pytest tests/test_comandos.py -q ===============
E         <Comando.MUTANTE_DESCARTAVEL: 'mutante_descartavel'>
            "comando novo sem entrada na tabela de ajuda: "
E       AssertionError: comando novo sem entrada na tabela de ajuda: MUTANTE_DESCARTAVEL
E       assert not {<Comando.MUTANTE_DESCARTAVEL: 'mutante_descartavel'>}
=========================== short test summary item ===========================
2 failed, 92 passed in 0.72s
```

O tripwire FALHOU **nomeando o membro esquecido**, que e o ponto: a mensagem
diz o que fazer, nao so que algo esta errado. Os dois testes que falharam foram
`TestAjuda::test_todo_comando_tem_linha_na_tabela_de_ajuda` (o tripwire novo) e
`TestInterpretar::test_o_vocabulario_e_fechado` (o tripwire que ja existia) —
duas redes independentes pegando o mesmo esquecimento.

A mutacao foi desfeita e o arquivo conferido byte a byte contra a copia de
antes (`diff` limpo), com a suite de volta em verde.

## O texto como ele chega no celular

```
Comandos do scanner — sempre com ponto na frente:

Vigilancia:
  .status — Digo se estou vigiando ou calado, e qual o proximo evento
  .solo — Vigio so o seu personagem e paro de reclamar de party
  .party (.pt) — Volto a vigiar a party inteira

Silencio:
  .cancelar — Tira o silencio de TvT/Prime que estiver rolando

Loot do Solo Boss:
  .loot-<nick> — Marca quem pega o loot do proximo boss
  .loot- — Desmarca: o proximo boss volta a ser de ninguem
  .<nick> — Quantos loots o char ja pegou, e quando foi o ultimo
  .corrigir-<nick> — Troca o dono do ultimo loot ja registrado
  .pegou <hora> <nick> — Registra loot de um boss que ja passou (ex.: 18:00 Korzis)

Ajuda:
  .help (.ajuda, .comandos) — Esta lista
```

Dezenove linhas, a mais longa com 83 caracteres. Familias na ordem de D-05:
vigilancia, silencio, loot, ajuda.

## Files Created/Modified

- `l2scanner/comandos.py` — `Comando.AJUDA`; as chaves `help`/`ajuda`/`comandos`/`?`
  no `_VOCABULARIO`; o dataclass `LinhaDeAjuda`; a tabela `_AJUDA` chaveada pelo
  enum e escrita na ordem de exibicao; `texto_de_ajuda()`.
- `l2scanner/__main__.py` — ramo `Comando.AJUDA` em `atender_comandos` com
  `avisar_o_grupo=False`; a funcao `_para_o_console()` e a troca de
  `log.info(destacar(resposta))` por ela.
- `tests/test_comandos.py` — `TestAjuda` (tripwire, round-trip, formas escritas,
  ordem das familias, ausencia de moldura), `TestAjudaNaCostura` (destino unico,
  texto integral, sem borda no WhatsApp nem no log, allowlist nas duas direcoes),
  `TestMolduraDoConsole` (a regra do desvio como funcao pura, e a medicao do
  estrago que ela evita); `Comando.AJUDA` acrescentado ao
  `test_o_vocabulario_e_fechado`; auxiliar `_tem_borda`.
- `README.md` — `.help`, `.solo` e `.party` na tabela de comandos, e o paragrafo
  explicando que a lista e gerada a partir do proprio codigo.

## Decisions Made

Todas as decisoes travadas do plano (D-01 a D-07) foram seguidas sem reabertura.
Duas escolhas menores dentro da margem que o plano deixou:

- **O achado 1 (`.?`) foi CONFIRMADO na execucao**, nao assumido. Verificado
  contra o codigo rodando: `interpretar(".?")` devolvia `None` antes da chave
  existir (nenhum caminho paralelo interceptava), e `"?"` nao casa
  `_NICK_VALIDO`, entao nao ha colisao com o ramo de consulta por nick. A chave
  entrou, com teste. O plano mandava tirar e comentar o porque se algo
  desmentisse — nada desmentiu.
- **Os apelidos de `.?` ficaram FORA do texto da ajuda**, seguindo D-05 ao pe da
  letra (`.help` com apelidos `.ajuda` e `.comandos`). O `.?` funciona e esta
  documentado no README; despejar quatro formas para um comando so contraria o
  proprio criterio de "uma forma canonica cada".

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] O `.venv` do projeto nao tem `pytest`**

- **Found during:** Task 1 (primeira execucao da verificacao)
- **Issue:** O plano manda rodar `.venv\Scripts\python -m pytest`, mas esse
  interpretador responde `No module named pytest`. O `.venv` so tem numpy, mss e
  coverage.
- **Fix:** Usado o `python` do sistema (Python 3.12, pytest 9.1.1), que e o que a
  instrucao do orquestrador ja pedia (`python -m pytest` a partir da raiz).
  Nenhuma instalacao de pacote foi feita — nao houve portao de legitimidade a
  atravessar.
- **Files modified:** nenhum
- **Verification:** `python -m pytest -q` -> 746 passed, 2 skipped
- **Committed in:** n/a (mudanca de procedimento, nao de codigo)

**2. [Rule 1 - Bug] `ruff format` regrediu em `l2scanner/comandos.py`**

- **Found during:** Task 1 (verificacao de lint)
- **Issue:** `comandos.py` estava formatado em `HEAD` (conferido rodando
  `ruff format --check` sobre `git show HEAD:l2scanner/comandos.py`), e a tabela
  `_AJUDA` como eu a escrevi deixou o arquivo fora do formato.
- **Fix:** `ruff format l2scanner/comandos.py`. So esse arquivo — `__main__.py` e
  `tests/test_comandos.py` **ja estavam** fora do formato em `HEAD`, entao
  reformata-los seria ruido fora de escopo (34 dos 43 arquivos do projeto estao
  nessa situacao).
- **Files modified:** `l2scanner/comandos.py`
- **Verification:** `ruff format --check l2scanner/comandos.py` -> already formatted
- **Committed in:** `ab2d6a7`

**3. [Rule 1 - Bug] `E741` introduzido por mim no teste novo**

- **Found during:** Task 2 (verificacao de lint)
- **Issue:** `max(len(l) for l in ...)` — nome de variavel ambiguo. `ruff check`
  saiu de 26 erros (baseline) para 27.
- **Fix:** renomeado para `linha`, com a largura medida numa variavel
  `mais_larga`. De volta aos 26 pre-existentes, que sao de outros arquivos e
  ficam fora de escopo.
- **Files modified:** `tests/test_comandos.py`
- **Verification:** `python -m ruff check l2scanner tests` -> 26 errors (baseline)
- **Committed in:** `ee86740`

---

**Total deviations:** 3 auto-fixed (1 x Rule 3, 2 x Rule 1)
**Impact on plan:** Nenhum desvio de escopo. Os tres sao higiene de ferramenta;
nenhum toca comportamento.

## Issues Encountered

- **O `\n` nao sobrevivia ao caminho de escrita dos arquivos.** Duas vezes, uma
  string `"\n"` escrita por script virou uma quebra de linha REAL dentro do
  literal, produzindo `SyntaxError: unterminated string literal`. Pego pelo
  proprio interpretador nas duas vezes e consertado montando o literal por
  `chr(92)`. Vale registrar porque e uma armadilha de FERRAMENTA, nao de codigo,
  e ela vai reaparecer na proxima vez que alguem gerar Python por script.
- **`test_o_vocabulario_e_fechado` falhou ao acrescentar `Comando.AJUDA`** — e
  isso e o teste funcionando. Ele e o tripwire que ja existia; a lista cresceu
  DE PROPOSITO e o crescimento foi registrado ali com o comentario que explica o
  porque. E a mesma disciplina que o tripwire novo institucionaliza para a
  tabela de ajuda.

## User Setup Required

None — nenhum pacote novo, nenhuma configuracao nova. O `.help` funciona no
mesmo canal de comandos que ja estava configurado.

## Next Phase Readiness

Pronto. O unico jeito de fechar o D6 e mandar um `.help` do telefone autorizado
e olhar como a lista chega no WhatsApp — o scanner precisa ser reiniciado para
carregar o comando.

Uma nota para quem planejar a proxima quick: **o padrao "tabela derivada +
tripwire" agora tem um segundo candidato obvio** — a tabela de comandos do
`README.md`, que continua sendo copia manual do `_AJUDA` e envelheceu duas vezes
(`.solo` e `.party`). Um teste que compare as duas fecharia o ciclo, ao custo de
acoplar a suite ao markdown.

## Self-Check: PASSED

Conferido contra o disco e contra o git, nao contra a memoria:

| Afirmacao | Como foi conferida | Resultado |
|---|---|---|
| Os 4 arquivos existem | `[ -f ... ]` em cada um | FOUND x4 |
| Os 2 commits existem | `git log --oneline --all \| grep` | FOUND ab2d6a7, ee86740 |
| Suite verde | `python -m pytest -q` | 746 passed, 2 skipped |
| Lint sem regressao | `python -m ruff check l2scanner tests` | 26 errors (o mesmo baseline) |
| Nenhum arquivo apagado | `git diff --diff-filter=D HEAD~2 HEAD` | vazio |
| A borda de 725 caracteres | `moldurar(texto_de_ajuda(), '20:30')` medido | 725 |

**Uma correcao saiu desta conferencia:** eu tinha escrito "1071 caracteres" para
a borda que o desvio de moldura evita. Medido, sao **725**. O numero errado foi
estimado, nao medido — e por isso que a conferencia existe.

---
*Phase: quick-260825-t1n*
*Completed: 2026-08-25*
