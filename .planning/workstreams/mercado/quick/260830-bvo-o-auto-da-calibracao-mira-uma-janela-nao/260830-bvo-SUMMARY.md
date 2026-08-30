---
phase: quick-260830-bvo
plan: 01
subsystem: calibracao
tags: [win32, wgc, tomllib, config, calibracao, party]

requires:
  - phase: quick-0c9038c
    provides: "fundir_com_a_calibracao_em_disco — o seam load-mutate-save que esta tarefa nao pode desfazer"
provides:
  - "Mira de janela para o --auto e o --selecionar da calibracao de party: com dois clientes abertos, os pixels do outro nunca entram na imagem analisada"
  - "config.ler_personagem_do_jogo — a chave [jogo] personagem, com config.local.toml vencendo e aviso quando os dois tem"
  - "calibrar.escolher_janela_do_jogo — funcao pura, quatro recusas nomeadas, zero nome de personagem no fonte"
  - "calibrar.capturar_a_janela_mirada — drop-in de capturar_tela(), mesma trinca (pixels, ox, oy)"
  - "cal.janela recebe o ALVO quando ha mira: o palpite geometrico de janela_que_contem nao e consultado"
  - "tests/test_calibrar_nao_apaga_mercado.py deixou de depender do config.toml da maquina de quem roda a suite"
affects: [calibracao de party, scanner em producao (segue cal.janela), calibracao de mercado (herda a mesma janela)]

actuals:
  tokens: 12105    # chars/4 sobre o diff realizado (48.419 chars em 5 arquivos)
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Mira declarada + falha fechada: quem pede alvo e recusado quando o alvo nao resolve para exatamente um, e nunca cai para o caminho generico"
    - "Constante de modulo como ancora de guarda de deriva: documento e leitor indexados pela MESMA constante, montada em tempo de teste"
    - "Parametro sem valor padrao como prova estrutural de ausencia de constante magica"

key-files:
  created:
    - tests/test_mira_da_janela.py
  modified:
    - l2scanner/config.py
    - l2scanner/calibrar.py
    - config.toml
    - tests/test_calibrar_nao_apaga_mercado.py

key-decisions:
  - "A mira vale tambem para --selecionar: main() tem UM ponto de captura, e isentar um ramo criaria um segundo conjunto de regras de coordenada para uma diferenca que o usuario nao ve (D-04)"
  - "Com mira ativa, _tentar_pelas_janelas_do_jogo NAO roda: ler a janela mirada por dentro ja E o que o fallback faz, e o que sobraria dele seria so a parte errada — a primeira que funcionar (D-05)"
  - "Com mira ativa, cal.janela = alvo e janela_que_contem nao e consultada: com os clientes sobrepostos ela devolveria o de cima, e o scanner em producao herdaria o cliente errado, gravado calado (D-09)"
  - "main() so enumera janelas quando alguem pediu alvo: sem o curto-circuito, o caminho SEM mira passaria a fazer um EnumWindows que hoje nao acontece, prendendo a suite as janelas da maquina"
  - "A nota de tela de login entra tambem na recusa por titulo exato, e nao so na recusa por personagem: a mentira por omissao e a mesma nos dois casos"

patterns-established:
  - "Falha fechada com listagem: toda recusa nomeia o que foi pedido, lista o que existe, e imprime a linha --janela \"TITULO\" pronta para copiar — o formato que calibrar_so_a_propria_barra ja usava"
  - "Guarda de deriva ancorado em constante: tomllib nao le comentario, entao o assert sobre o comentario se ancora no TEXTO do arquivo, com as duas pontas saindo da mesma constante"
  - "Neutralizacao de configuracao em helper de teste: _dirigir zera a mira para que a suite nunca leia o config.toml da maquina de quem a roda"

requirements-completed: [MIRA-01, MIRA-02]

coverage:
  - id: D1
    description: "Com a mira configurada, --auto le SO o frame da janela mirada: capturar_tela nao e chamada nenhuma vez e _tentar_pelas_janelas_do_jogo nao roda"
    requirement: "MIRA-01"
    verification:
      - kind: unit
        ref: "tests/test_mira_da_janela.py#TestAMiraLeUmaJanelaSo::test_auto_com_mira_le_so_a_janela_mirada"
        status: pass
      - kind: unit
        ref: "tests/test_mira_da_janela.py#TestAMiraLeUmaJanelaSo::test_o_automatico_recebe_a_origem_da_janela_e_nao_a_do_desktop"
        status: pass
    human_judgment: false
  - id: D2
    description: "O nome do personagem vem do config.toml e so de la (ou do --janela); nao existe nome de personagem no fonte"
    requirement: "MIRA-01"
    verification:
      - kind: unit
        ref: "tests/test_mira_da_janela.py#TestALeituraDaChave (7 casos)"
        status: pass
      - kind: unit
        ref: "tests/test_mira_da_janela.py#TestAEscolhaDaJanela::test_nenhum_personagem_escrito_no_fonte"
        status: pass
    human_judgment: false
  - id: D3
    description: "Mira que nao resolve para exatamente uma janela RECUSA com codigo 1, nomeia o que encontrou, e nao grava nada"
    requirement: "MIRA-02"
    verification:
      - kind: unit
        ref: "tests/test_mira_da_janela.py#TestARecusaEFechada (9 casos, cada recusa inspecionada com capsys)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Com mira ativa o campo janela gravado e o ALVO, e nao o palpite geometrico de janela_que_contem"
    requirement: "MIRA-01"
    verification:
      - kind: unit
        ref: "tests/test_mira_da_janela.py#TestOCampoJanelaGravado::test_com_mira_o_campo_janela_e_o_alvo_e_nao_o_palpite_geometrico"
        status: pass
      - kind: unit
        ref: "tests/test_mira_da_janela.py#TestOCampoJanelaGravado::test_sem_mira_janela_que_contem_continua_decidindo"
        status: pass
    human_judgment: false
  - id: D5
    description: "Sem chave e sem --janela o comportamento de hoje esta intacto, fallback incluido"
    requirement: "MIRA-02"
    verification:
      - kind: unit
        ref: "tests/test_mira_da_janela.py#TestSemMiraNadaMuda::test_sem_chave_e_sem_janela_o_desktop_e_o_fallback_continuam"
        status: pass
      - kind: unit
        ref: "tests/test_calibrar_nao_apaga_mercado.py (6 casos pre-existentes, sem alteracao de logica)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Conferencia de campo com os DOIS clientes abertos: preencher a chave, rodar calibrar.bat, confirmar que o console nomeia a janela certa e que a imagem de conferencia mostra a party window do cliente pretendido"
    verification: []
    human_judgment: true
    rationale: "Exige dois clientes do jogo abertos na maquina do usuario. Nenhum teste pode afirmar que a janela mirada corresponde ao cliente que o humano queria — a suite prova a fiacao, nao a intencao."

duration: 20min
completed: 2026-08-30
status: complete
---

# Quick 260830-bvo: A mira da janela na calibracao de party — Summary

**O `--auto` e o `--selecionar` da calibracao passam a ler SO a janela do cliente mirado — mira que nasce do `config.toml`, e vencida pelo `--janela`, e que RECUSA em vez de adivinhar.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-08-30T11:54:56Z
- **Completed:** 2026-08-30T12:14:45Z
- **Tasks:** 3
- **Files modified:** 5 (1 criado, 4 alterados)

## Accomplishments

- **Os pixels do outro cliente nao entram mais na conta.** Com a chave configurada, `main()` captura o frame de UMA janela por `capturar_a_janela_mirada`, e `capturar_tela` nao e chamada nenhuma vez. `calibrar_automatico` deixa de poder agrupar barras de duas party windows e deduzir uma geometria que nao e de nenhum cliente — que era gravada CALADA, porque cada passo interno parecia bem-sucedido.
- **`cal.janela` recebe o alvo, e nao um palpite geometrico (D-09).** No cenario que a mira anuncia como ganho — dois clientes SOBREPOSTOS — `janela_que_contem` devolveria o cliente de CIMA, e dali para baixo `party_window_na_janela`, `nome_proprio`, o `origem` de `achar_barra_do_proprio` e o SCANNER EM PRODUCAO herdariam o cliente errado. Provado por mutacao: revertendo so este bloco, o caso fica vermelho (saida literal abaixo).
- **Falha fechada, com quatro recusas de frase propria.** Sem janela do jogo, personagem que nao casa, titulo exato inexistente, e duas ou mais casando. Cada uma nomeia o que foi pedido e imprime a linha `--janela "TITULO"` pronta para copiar. Nenhuma sugere tentar o desktop, e o codigo nao tem caminho para isso.
- **A recusa parou de mentir por omissao sobre a tela de login.** Havia cliente do jogo aberto, e a mensagem dizia "nao achei" — mandando o usuario conferir a grafia do nick de um cliente que nem entrou no mundo.
- **A suite deixou de depender do `config.toml` da maquina.** `_dirigir` de `tests/test_calibrar_nao_apaga_mercado.py` neutraliza a mira; no dia em que o usuario preencher a chave, aqueles 6 casos nao passam a exigir jogo aberto.

## Task Commits

1. **Task 1 (tracer, TDD) — RED: a mira afirmada antes de existir** — `6f149d9` (test)
2. **Task 1 (tracer, TDD) — GREEN: `ler_personagem_do_jogo`, `escolher_janela_do_jogo`, `capturar_a_janela_mirada`, fiacao em `main()`** — `75605b6` (feat)
3. **Task 2 (TDD) — RED: as quatro recusas, uma a uma** — `b77d90d` (test)
4. **Task 2 (TDD) — GREEN: as frases das recusas, a nota de login, e a neutralizacao em `_dirigir`** — `452ed53` (feat)
5. **Task 3 — o bloco `[jogo]` no `config.toml`, as constantes e o guarda de deriva** — `465ae22` (docs)

_Nao houve commit de REFACTOR: nenhuma das duas voltas pediu limpeza._

## Portao vermelho — a saida REAL

**Task 1, RED** (`python -m pytest tests/test_mira_da_janela.py -q`, antes de qualquer implementacao):

```
17 failed, 1 warning in 0.69s
```

Os 17 casos do arquivo, todos vermelhos.

**Task 2, RED** (`python -m pytest tests/test_mira_da_janela.py -q`):

```
FAILED tests/test_mira_da_janela.py::TestARecusaEFechada::test_janela_no_login_e_apontada_como_login_e_nao_so_como_nao_achei
1 failed, 29 passed, 1 warning in 0.31s
```

**O VERMELHO DISCRIMINANTE DE D-09, por mutacao.** O plan-checker avisou que este caso tem de falhar no codigo de hoje, e que passar antes do conserto seria sinal de que algo esta errado. Revertendo APENAS o bloco `if alvo: cal.janela = alvo` para a linha original (`cal.janela = janela_que_contem(...)`) e rodando o caso isolado:

```
FAILED tests/test_mira_da_janela.py::TestOCampoJanelaGravado::test_com_mira_o_campo_janela_e_o_alvo_e_nao_o_palpite_geometrico
1 failed, 29 deselected, 1 warning in 0.24s
```

O arquivo foi restaurado byte a byte em seguida (`git status` limpo antes do commit).

**O GUARDA DE DERIVA MORDE, por mutacao.** Renomeando `SECAO_DO_JOGO` de `"jogo"` para `"cliente"` em `l2scanner/config.py` — mexendo em UM dos dois lados:

```
E       assert '[cliente]' in '# Agenda de eventos do jogo ... '
FAILED tests/test_mira_da_janela.py::TestOConfigDoRepositorio::test_a_secao_e_a_chave_documentadas_sao_as_que_o_codigo_le
1 failed, 1 passed, 30 deselected in 0.22s
```

Tambem restaurado em seguida.

## Suite completa

Baseline neste worktree, medido ANTES de qualquer alteracao:

```
1869 passed, 14 skipped, 1 warning in 33.60s
```

Final:

```
1901 passed, 14 skipped, 2 warnings in 29.23s
```

`1869 + 32 casos novos = 1901`, sem regressao. Nenhum aborto por `KeyboardInterrupt` — o flake conhecido de `tests/test_agenda.py` nao apareceu em nenhuma das tres rodadas completas.

**Nota sobre o baseline anunciado no plano (1830 passed, 2 skipped):** neste worktree o baseline e `1869 passed, 14 skipped`. A diferenca de skips e esperada e esta escrita no proprio briefing — `recordings/` e `calibration.json` nao existem aqui (gitignored), entao os casos que os referenciam pulam. A diferenca de passed vem do worktree ter sido criado de `efcde50`, adiante do commit em que o numero do plano foi medido.

## Files Created/Modified

- `l2scanner/config.py` — `ler_personagem_do_jogo` (precedencia `config.local.toml` > `config.toml`, com aviso quando os dois tem a chave), o helper `_personagem_do_arquivo`, e as constantes `SECAO_DO_JOGO` / `CHAVE_DO_PERSONAGEM`
- `l2scanner/calibrar.py` — `MiraNaoResolvida`, `escolher_janela_do_jogo` (pura), `capturar_a_janela_mirada`, `_linhas_de_janela`, `_nota_de_login`, a fiacao em `main()` (resolucao + captura num unico `try`, curto-circuito da enumeracao, `cal.janela = alvo`, fallback so sem mira), docstring do modulo e ajuda do `--janela`
- `config.toml` — a secao `[jogo]` COMENTADA (44 linhas acrescentadas; **nenhuma linha existente do arquivo mudou**)
- `tests/test_mira_da_janela.py` — 32 casos novos
- `tests/test_calibrar_nao_apaga_mercado.py` — `_dirigir` ganhou as duas neutralizacoes (18 linhas acrescentadas; **nenhuma alteracao de logica nos 6 casos**)

## Decisions Made

Todas as decisoes de projeto ja vinham travadas no plano (D-01 a D-09) e foram seguidas sem reabertura. As decisoes de EXECUCAO que sobraram:

- **A nota de tela de login entra nas DUAS recusas de "nao casou", e nao so na (b).** O plano a especifica para a recusa por personagem. Ela foi extraida para `_nota_de_login` e aplicada tambem a recusa (c), por titulo exato: um usuario que digita `--janela "Alfa - XM Essence"` com o cliente no login recebe exatamente a mesma mentira por omissao — a janela existe, e do jogo, e so nao tem personagem no titulo. Restringir a nota a (b) deixaria metade do problema aberto sem nenhuma razao a favor.
- **`capturar_a_janela_mirada` embrulha as falhas de abertura em `MiraNaoResolvida`.** `achar_janela` levanta `JanelaNaoEncontrada` e `JanelaSource.__init__` levanta `RuntimeError` quando nenhum frame chega (o caso da janela minimizada, `captura_janela.py:299`). Deixar as duas subirem cruas faria a mensagem mais provavel de todas — o usuario esqueceu o cliente minimizado — sair como traceback, que e o oposto do contrato escrito na propria docstring de `MiraNaoResolvida`. O texto original do erro e preservado dentro da mensagem.

## Deviations from Plan

Nenhuma deviation de regra 1-4. Duas notas de execucao que valem registro, ambas acima em "Decisions Made" (a nota de login estendida a recusa (c), e o embrulho das falhas de abertura).

## Issues Encountered

**O RED da Task 2 veio quase todo verde, e isso tem explicacao — nao e teste que nao afirma nada.** Dos casos que a Task 2 acrescentou, so um falhou: a nota de tela de login. Os outros ja passavam porque o GREEN da Task 1 escreveu as mensagens de recusa COMPLETAS em vez de deixa-las como esbocos — o plano atribui o texto das mensagens a Task 2, mas uma excecao precisa carregar alguma mensagem para o GREEN da Task 1 fechar, e escrever uma mensagem pela metade so para produzir vermelho depois seria teatro.

Foi investigado antes de seguir, como o protocolo manda: a causa e sobreposicao entre as duas tasks, e nao um teste que passa por acidente. A prova de que os casos discriminam esta nas duas mutacoes registradas acima — o de D-09 e o do guarda de deriva ficam vermelhos quando o codigo correspondente e revertido.

## User Setup Required

Nenhuma configuracao externa. Para LIGAR a mira, o usuario descomenta duas linhas no `config.toml`:

```toml
[jogo]
personagem = "Yazalaque"
```

O bloco no arquivo explica o porque, o que acontece sem a chave, o que acontece quando ela aponta para uma janela que nao existe, e que `--janela "TITULO"` na linha de comando vence.

## Next Phase Readiness

- **Falta a conferencia de campo (D6 na tabela de coverage), e ela e o unico passo que exige o jogo aberto:** com os DOIS clientes ligados, preencher a chave, rodar `calibrar.bat`, e confirmar que o console nomeia a janela certa e que a imagem de conferencia mostra a party window do cliente pretendido. Nenhum teste pode afirmar isso — a suite prova a fiacao, nao a intencao.
- `fundir_com_a_calibracao_em_disco` (commit `0c9038c`) ficou INTOCADA, e a ordem `fundir` -> `salvar` esta preservada. A recusa retorna `1` antes de qualquer `salvar`, com caso afirmando que o arquivo apontado por `ARQUIVO_CALIBRACAO` fica byte a byte igual.
- `VERSAO_DO_ESQUEMA` inalterada; `l2scanner/calibracao.py`, `l2scanner/rastreador.py` e `l2scanner/visao.py` fora do diff; `requirements.txt` fora do diff (FIRE-01 respeitada, nenhuma dependencia nova — tudo usado ja estava no projeto).
- Nenhum dos 6 arquivos do agente paralelo foi tocado: `calibration.json`, `l2scanner/mercado_geometria.py`, `tools/medir_oclusao.py`, `tools/medir_leitura_de_glifo.py`, `tests/test_mercado_geometria.py`, `tests/test_medir_leitura_de_glifo.py`.
- `calibration.json` nao existe neste worktree (gitignored) e nao aparece em `git status`.

## Self-Check: PASSED

Arquivos conferidos em disco: `tests/test_mira_da_janela.py`, `l2scanner/config.py`,
`l2scanner/calibrar.py`, `config.toml`, `tests/test_calibrar_nao_apaga_mercado.py`,
`260830-bvo-SUMMARY.md` — todos FOUND.

Commits conferidos no `git log`: `6f149d9`, `75605b6`, `b77d90d`, `452ed53`, `465ae22`
— todos FOUND, todos descendentes de `efcde50`.

---
*Quick task: 260830-bvo*
*Completed: 2026-08-30*
