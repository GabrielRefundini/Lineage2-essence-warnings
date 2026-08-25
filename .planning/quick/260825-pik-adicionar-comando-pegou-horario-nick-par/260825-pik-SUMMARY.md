---
phase: quick-260825-pik
plan: 01
subsystem: loot
tags: [whatsapp, comandos, agenda, parser, estatistica-duravel, tdd]

requires:
  - phase: quick-260825-cou
    provides: "RegistroDeLoot, a pasta .loot/ sem poda, e o consumo automatico no horario do boss"
  - phase: quick-260825-ehc
    provides: "corrigir(), o tri-estado de Correcao e a ordem criar-antes-de-apagar que atribuir() espelha"
  - phase: 06-a-agenda-como-fonte-de-eventos
    provides: "EventoAgendado e a enumeracao por dia que o encaixe do horario reusa"
provides:
  - "`.pegou [data] <hora> <nick>` — registra quem pegou o loot de um Solo Boss que ja passou, mesmo sem nunca ter havido designacao"
  - "`RegistroDeLoot.atribuir(nick, alvo)` — cria quando nao havia dono, troca quando havia, com a invariante de nunca perder o loot"
  - "`encaixar_na_agenda` — casa um horario digitado numa ocorrencia REAL do Solo Boss, ou recusa"
  - "`agenda.ocorrencias_do_dia` — a enumeracao por dia, agora publica"
  - "`loot.NICK_VALIDO` — o charset de nick, agora com casa unica"
affects: [loot, comandos, agenda, README]

actuals:
  tokens: 15300
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Gramatica unica: a mesma funcao pura valida no parser e le no responder"
    - "Encaixe obrigatorio na agenda antes de escrever estado permanente"
    - "Leitura de calendario mais proxima para resolver data sem ano"

key-files:
  created: []
  modified:
    - l2scanner/loot.py
    - l2scanner/comandos.py
    - l2scanner/agenda.py
    - l2scanner/__main__.py
    - tests/test_loot.py
    - tests/test_comandos.py
    - README.md

key-decisions:
  - "Tolerancia de encaixe de 30 minutos, com desempate pela ocorrencia mais cedo: 60 nunca recusaria nada num boss de duas em duas horas"
  - "A gramatica do `.pegou` mora em loot.py e e importada por comandos.py — uma so, porque duas divergiriam no primeiro ajuste"
  - "`NICK_VALIDO` mudou de comandos.py para loot.py; `_NICK_VALIDO` sobrevive como alias, zero mudanca de comportamento"
  - "`_ocorrencias` virou publica `ocorrencias_do_dia` — o encaixe precisa enumerar ocorrencias PASSADAS"
  - "`atribuir` solta a designacao pendente somente quando o alvo dela bate exatamente, senao o proximo consumir() criaria um segundo dono"
  - "Data sem ano resolve para a leitura de calendario MAIS PROXIMA e so entao exige que ela tenha passado — corrige o recuo de ano irrestrito, que gravaria em dezembro do ano anterior um `.pegou 30/12` digitado em agosto"

patterns-established:
  - "Portao de parser por funcao pura: `interpretar_dinamico` so reconhece o comando quando `interpretar_pegou` aceita o argumento inteiro"
  - "Verificacao por MUTACAO das linhas que podem destruir dado, antes de considerar a task pronta"

requirements-completed: [QUICK-260825-pik]

coverage:
  - id: D1
    description: "`.pegou 18:00 Korzis` registra o loot de um Solo Boss que ja passou mesmo quando nao havia registro nenhum"
    requirement: QUICK-260825-pik
    verification:
      - kind: unit
        ref: "tests/test_loot.py::TestAtribuicaoEnderecada::test_registra_um_boss_que_nao_tinha_registro_NENHUM"
        status: pass
      - kind: integration
        ref: "tests/test_comandos.py::TestLootNaCostura::test_pegou_atravessa_parser_dispatch_e_disco"
        status: pass
    human_judgment: false
  - id: D2
    description: "Sem data, o horario resolve para a ocorrencia mais recente que JA PASSOU, e a resposta diz o dia de volta"
    requirement: QUICK-260825-pik
    verification:
      - kind: unit
        ref: "tests/test_loot.py::TestAtribuicaoEnderecada::test_as_02h_o_horario_de_18h_e_de_ONTEM"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py::TestAtribuicaoEnderecada::test_nunca_resolve_para_o_FUTURO"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py::TestAtribuicaoEnderecada::test_a_virada_da_meia_noite_no_sentido_CONTRARIO"
        status: pass
    human_judgment: false
  - id: D3
    description: "O horario e encaixado numa ocorrencia real do Solo Boss; sem boss por perto o comando recusa e lista os horarios"
    requirement: QUICK-260825-pik
    verification:
      - kind: unit
        ref: "tests/test_loot.py::TestAtribuicaoEnderecada::test_o_horario_gravado_e_o_do_BOSS_nao_o_digitado"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py::TestAtribuicaoEnderecada::test_a_recusa_LISTA_os_horarios_que_existem"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py::TestAtribuicaoEnderecada::test_o_boss_que_AINDA_NAO_NASCEU_nao_pode_ser_encaixado"
        status: pass
    human_judgment: false
  - id: D4
    description: "A estatistica nunca encolhe: em todos os desfechos de `atribuir` sobra pelo menos um dono para o alvo"
    requirement: QUICK-260825-pik
    verification:
      - kind: unit
        ref: "tests/test_loot.py::TestAtribuicaoEnderecada::test_sobra_sempre_um_pegou_para_o_alvo_em_TODOS_os_desfechos"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py::TestAtribuicaoEnderecada::test_falha_de_disco_NAO_apaga_o_velho"
        status: pass
      - kind: unit
        ref: "tests/test_loot.py::TestAtribuicaoEnderecada::test_atribuir_ao_dono_que_JA_e_o_dono_nao_apaga_nada"
        status: pass
    human_judgment: false
  - id: D5
    description: "As duas sintaxes (espaco e hifen) registram; `.pegou` sozinho nao faz nada nem vira consulta de nick homonimo"
    requirement: QUICK-260825-pik
    verification:
      - kind: unit
        ref: "tests/test_comandos.py::TestInterpretarDinamico::test_pegou_com_hifen_faz_a_MESMA_coisa"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py::TestInterpretarDinamico::test_pegou_nao_vira_consulta_nem_com_nick_homonimo"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py::TestInterpretarDinamico::test_as_formas_que_NAO_registram"
        status: pass
    human_judgment: false
  - id: D6
    description: "O comando funciona de verdade contra o Chatwoot do usuario, com o WhatsApp no meio"
    verification: []
    human_judgment: true
    rationale: "Toda a logica e pura e testada sem rede, mas o caminho WhatsApp -> Chatwoot -> comandos_novos so pode ser confirmado mandando `.pegou` de verdade do celular. E a mesma milha que os outros quatro comandos de loot deixaram em aberto."

duration: 47min
completed: 2026-08-25
status: complete
---

# Quick 260825-pik: o `.pegou` que registra o loot de um boss que ja passou

**`.pegou 18:00 Korzis` cria o registro de loot de um Solo Boss que ja aconteceu — mesmo quando ninguem tinha marcado nada e nao existia registro algum para corrigir —, encaixando o horario digitado numa ocorrencia real da agenda e recusando quando nao ha boss por perto.**

## Performance

- **Duration:** ~47 min
- **Tasks:** 3 de 3
- **Files modified:** 7
- **Testes:** 683 -> 715 (32 novos), todos verdes sem o jogo aberto e sem rede

## Accomplishments

- **O buraco que o usuario relatou fechou.** *"Nao consegui atribuir o loot do boss das 18h e a Korzis pegou"* era impossivel por construcao: um `pegou_*` so nascia de uma designacao previa consumida, e o `.corrigir` so troca o dono do registro mais recente. Sem designacao previa nao havia registro nenhum, e o unico conserto era criar arquivo a mao no Explorer.
- **O horario digitado nunca vira registro direto.** Ele e ENCAIXADO numa ocorrencia real do Solo Boss (tolerancia de 30 min) e o registro usa o horario da ocorrencia. `.pegou 18h20` grava o boss das 18:00; `.pegou 19:00` — ambiguo entre 18:00 e 20:00 — recusa e diz quais horarios existem. Registro orfao numa pasta que nunca e podada seria permanente e inalcancavel.
- **A resposta sempre diz o dia.** As 02h da manha `.pegou 18:00` fala do boss de ONTEM, e "de ontem as 18:00" e a unica rede entre acertar e reescrever o boss errado num comando que alcanca horario arbitrario.
- **A estatistica nao encolhe em desfecho nenhum.** Criado, corrigido, mesmo_dono e falhou: em todos, o alvo continua com pelo menos um dono. Provado por teste e conferido por mutacao.
- **Uma gramatica so.** `interpretar_pegou` mora em `loot.py`, valida no parser e le no responder. Duas gramaticas divergiriam no primeiro ajuste e o comando passaria a aceitar o que nao sabe executar.

## Task Commits

1. **Task 1 (tracer): o caminho inteiro do `.pegou <hora> <nick>`, de ponta a ponta**
   - `fb9b04c` (test) — RED: o boss sem registro, o horario do boss, a recusa, a gramatica e a costura
   - `2bfdc0f` (feat) — GREEN: agenda publicada, `NICK_VALIDO` mudou de casa, `interpretar_pegou`, `momento_desejado`, `encaixar_na_agenda`, `atribuir`, `_soltar_designacao`, `responder_atribuicao`, o enum, o ramo do parser e o dispatch
2. **Task 2: as invariantes que protegem a estatistica, e a virada da meia-noite**
   - `072cbab` (test) — as 15 invariantes; nenhuma exigiu mudanca de codigo (o Task 1 ja as satisfazia), e uma delas nasceu de uma mutacao que sobreviveu
3. **Task 3: a gramatica completa, as portas dos fundos, e o README**
   - `0750f68` (test) — RED: data explicita, virada do ano, grafias de horario, forma com hifen, formas invalidas e regressao dos ramos vizinhos
   - `27436eb` (feat) — GREEN: a gramatica completa, o recuo de ano corrigido, o ramo com hifen e o README

**Plan metadata:** commitado pelo orquestrador.

## Files Created/Modified

- `l2scanner/loot.py` — `NICK_VALIDO`, `TOLERANCIA_DE_ENCAIXE`, `PedidoDePegou`, o quinto estado `criado` em `Correcao`, `interpretar_pegou`, `momento_desejado`, `encaixar_na_agenda`, `horarios_do_solo_boss`, `RegistroDeLoot.atribuir`, `RegistroDeLoot._soltar_designacao` e `responder_atribuicao`
- `l2scanner/comandos.py` — `Comando.LOOT_ATRIBUIR` e os dois ramos de `.pegou` em `interpretar_dinamico`; `_NICK_VALIDO` virou alias de `loot.NICK_VALIDO`; o `import re` saiu junto com a constante
- `l2scanner/agenda.py` — `_ocorrencias` virou publica `ocorrencias_do_dia` (4 chamadas internas atualizadas, corpo intacto)
- `l2scanner/__main__.py` — o ramo `Comando.LOOT_ATRIBUIR` em `atender_comandos`, com `avisar_o_grupo = False`
- `tests/test_loot.py` — `TestAtribuicaoEnderecada`, 23 testes
- `tests/test_comandos.py` — 9 testes de gramatica e costura, mais o vocabulario fechado que cresceu de proposito
- `README.md` — a familia inteira de comandos de loot na tabela, mais quando usar `.pegou` e quando usar `.corrigir`

## Decisions Made

As quatro decisoes ja aprovadas pelo orquestrador foram implementadas como escritas: tolerancia de 30 min com desempate pela ocorrencia mais cedo; `NICK_VALIDO` mudando de casa com alias de volta; `_ocorrencias` publicada; e `atribuir` soltando a designacao pendente so quando o `alvo` bate exatamente.

Uma decisao nova, forcada por um conflito interno do plano (ver Deviations): **data sem ano resolve para a leitura de calendario mais proxima, e so entao precisa ter passado.** Nao ha numero magico — e a mesma regra do caso sem data, aplicada a escala do ano.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] O recuo de ano irrestrito gravava um loot oito meses no passado**

- **Found during:** Task 3
- **Issue:** O `<action>` do Task 3 mandava, para data sem ano, "tente `agora.year` e, se o instante ficar DEPOIS de `agora`, tente `agora.year - 1`". Implementado ao pe da letra, `.pegou 30/12 18:00 Korzis` digitado em 25/08/2026 resolvia para **30/12/2025** e gravava — enquanto o `<behavior>` do MESMO task exige que essa entrada RECUSE e nao grave nada. As duas metades do plano se contradiziam, e o teste (o contrato) pegou.
- **Fix:** `momento_desejado` passa a montar as duas leituras possiveis (`agora.year` e `agora.year - 1`), escolher a **mais proxima de `agora`** e so entao exigir que ela tenha passado. Em 03/01/2027 "30/12" fica a 4 dias no passado contra 361 dias no futuro -> vira dezembro de 2026 (a virada do ano continua funcionando). Em 25/08/2026 fica a 127 dias no futuro contra 238 no passado -> recusa. Sem constante nova e sem heuristica: e a mesma regra do caso sem data, uma escala acima.
- **Files modified:** `l2scanner/loot.py`
- **Verification:** `test_a_virada_do_ANO` e `test_data_no_FUTURO_ou_IMPOSSIVEL_recusa_e_nao_grava` passam juntos, o que antes era impossivel.
- **Committed in:** `27436eb`

**2. [Rule 2 - Missing critical test] A linha que descarta ocorrencia FUTURA no encaixe nao tinha teste que a prendesse**

- **Found during:** Task 2 (na conferencia por mutacao)
- **Issue:** Apagar o filtro `alvo <= agora` de `encaixar_na_agenda` deixava os 17 testes de entao **todos verdes**. Nos casos testados a ocorrencia passada ja era a mais proxima, entao a linha nunca era exercida — e ela e o que impede D-01 de ser violado (registrar loot de um boss que ainda nao nasceu).
- **Fix:** teste novo `test_o_boss_que_AINDA_NAO_NASCEU_nao_pode_ser_encaixado`: as 17:55, `.pegou 17:50` tem a ocorrencia das 18:00 a 10 minutos (futura) e a das 16:00 a 110 minutos (passada). Sem o filtro o scanner gravaria um boss que ainda vai acontecer — e o `consumir()` depois criaria um segundo dono. Com o filtro, recusa.
- **Files modified:** `tests/test_loot.py`
- **Verification:** o mutante que remove o filtro agora derruba exatamente este teste.
- **Committed in:** `072cbab`

**3. [Rule 3 - Blocking] `import re` orfao em `comandos.py`**

- **Found during:** Task 1
- **Issue:** Mover `NICK_VALIDO` para `loot.py` deixou `re` sem uso em `comandos.py`, e o `ruff` falhava (F401).
- **Fix:** o import saiu junto com a constante.
- **Files modified:** `l2scanner/comandos.py`
- **Verification:** `ruff check` limpo nos quatro arquivos de codigo tocados.
- **Committed in:** `2bfdc0f`

**4. [Rule 2 - Missing critical functionality] O vocabulario fechado precisava crescer de proposito**

- **Found during:** Task 1
- **Issue:** `test_o_vocabulario_e_fechado` guarda o enum `Comando` inteiro contra crescimento acidental. `LOOT_ATRIBUIR` fez o teste falhar — que e exatamente o que ele existe para fazer.
- **Fix:** o membro novo entrou no teste com o comentario que justifica por que ele merece existir e como o limite dele difere do `.corrigir`.
- **Files modified:** `tests/test_comandos.py`
- **Verification:** o teste voltou a verde sem afrouxar a assercao (continua exigindo igualdade exata do conjunto).
- **Committed in:** `2bfdc0f`

---

**Total deviations:** 4 auto-fixed (1x Rule 1, 2x Rule 2, 1x Rule 3)
**Impact on plan:** Nenhum scope creep. A deviation 1 e a unica com efeito sobre o comportamento visivel, e ela resolve uma contradicao interna do plano na direcao mais segura — a que nao grava estado permanente por engano.

## Issues Encountered

**Conferencia por MUTACAO das linhas que podem destruir dado.** O item 3 da `<verification>` do plano pedia leitura do diff; em vez disso as quatro linhas foram mutadas e a suite rodada contra cada mutante:

| Mutacao | Desfecho |
|---|---|
| inverter criar/apagar em `atribuir` (guarda da lista -> `donos[0]`) | 1 teste falha |
| encolher a varredura do encaixe de 3 dias para 1 | 1 teste falha |
| afrouxar `_soltar_designacao` (sem comparar o alvo) | 1 teste falha |
| remover o descarte de ocorrencia futura | **sobreviveu** -> virou a deviation 2 |

Tres das quatro ja estavam presas; a quarta so ficou depois do teste novo.

**Trabalho concorrente na mesma arvore.** Durante a execucao, outro agente rodou a quick task `psq` (OCR de manutencao) neste mesmo repositorio: os commits `55eaf35`, `dfeb927` e `4e3e921` estao intercalados com os meus no historico. Consequencias registradas:

- `tests/test_manutencao.py` termina com falhas (`VigiaDeManutencao.__init__() got an unexpected keyword argument 'ler_texto_conferencia'`) — e a fase RED **daquela** task, nao regressao desta. Os tres modulos deste trabalho (`test_loot`, `test_comandos`, `test_agenda`) somam 237 testes, todos verdes.
- Todo `git add` foi feito arquivo a arquivo. Nenhum `git add .`, nenhum `git add -A`.

**A pasta `tests/fixtures/manutencao/` esta sem rastreamento** e pertence a task `psq` — nao foi tocada nem commitada aqui. Ela adiciona 8 testes de OCR a coleta local (7 passam, 1 pula por falta das bindings do WinRT neste Python), o que explica a diferenca entre os 715 testes rastreados e os 723 coletados na maquina.

**`.gsd/` continua sem rastreamento e fora de todo commit**, como o plano exigiu.

## Known Stubs

Nenhum. Nao ha valor vazio, texto de espera nem caminho pendente no codigo entregue — o ramo de data explicita que o Task 1 deixou apontando para o Task 3 foi substituido pela implementacao real, e nao sobrou nenhum `TODO`/`FIXME` nos arquivos tocados.

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano. Nenhum endpoint, nenhuma dependencia, nenhum caminho de entrada novo: o `.pegou` atravessa exatamente as mesmas cinco travas de `comandos_novos` que os quatro comandos de loot ja existentes.

As mitigacoes do registro foram implementadas como planejadas:

| Threat ID | Mitigacao entregue |
|---|---|
| T-pik-01 | `encaixar_na_agenda` exige ocorrencia real e `alvo <= agora`; cada `.pegou` move ou cria um registro so |
| T-pik-02 | Encaixe fora da tolerancia RECUSA sem gravar (3 testes) |
| T-pik-03 | Criar-antes-de-apagar, guarda da lista inteira, `try/except OSError`, e a invariante testada nos quatro desfechos |
| T-pik-04 | `NICK_VALIDO` no portao do parser e `apelido()` antes de qualquer nome de arquivo |
| T-pik-05 | Nenhum caminho de entrada novo |
| T-pik-06 | Varredura de custo constante (3 dias), independente do que foi digitado |
| T-pik-07 | Zero dependencia nova — so `re`, `datetime` e o que ja existia |

## Self-Check: PASSED

- Os 5 commits existem no historico: `fb9b04c`, `2bfdc0f`, `072cbab`, `0750f68`, `27436eb`.
- Os 7 arquivos declarados existem e contem os simbolos do plano (`ocorrencias_do_dia`, `NICK_VALIDO`, `TOLERANCIA_DE_ENCAIXE`, `PedidoDePegou`, `interpretar_pegou`, `momento_desejado`, `encaixar_na_agenda`, `horarios_do_solo_boss`, `RegistroDeLoot.atribuir`, `RegistroDeLoot._soltar_designacao`, `responder_atribuicao`, `Comando.LOOT_ATRIBUIR`) — verificado por import.
- `ruff check` limpo nos quatro arquivos de codigo tocados.
- Baseline reconstruida num checkout limpo do commit anterior ao trabalho: **683 passando**. Com este trabalho: **715 passando** (32 novos), sem regressao.
