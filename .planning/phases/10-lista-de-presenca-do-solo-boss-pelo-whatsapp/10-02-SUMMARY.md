---
phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp
plan: 02
subsystem: agenda
tags: [agenda, chamada, presenca, config, toml, volume, whatsapp]

# Dependency graph
requires:
  - phase: 10-01
    provides: "`Comando.JOIN`/`LEAVE` reconhecidos e autorizados — o que a chamada convida a mandar ja existe no enum"
  - phase: 06-agenda-de-eventos
    provides: "`TipoDeAviso`, `Aviso.chave` com `tipo.value`, `avisar_no_horario` e os tres tripwires de volume"
provides:
  - "`TipoDeAviso.CHAMADA` — o terceiro tipo de aviso da agenda, com chave duravel propria (`..._chamada`)"
  - "`EventoAgendado.chamar_minutos_antes: int = 0` — opt-in por evento, `0` == desligado"
  - "Ramo proprio em `texto_do_aviso`: pergunta quem vai e manda responder no PRIVADO do bot"
  - "Validacao de `chamar_minutos_antes` no arranque, com o buraco do booleano fechado"
  - "`chamar_minutos_antes = 110` no `[[evento]]` do Solo Boss do `config.toml`"
  - "Os tres tripwires de volume rearmados em 36/dia, 72/dois-dias e 24 de Solo Boss"
affects:
  - 10-03-join-leave-que-fazem-alguma-coisa
  - 10-04-lista-em-disco
  - 10-05-fechamento-e-loot

# Actuals (#2632) — pareia com o `estimate` do plano para calibrar estimativas futuras.
# Base: chars/4 sobre o DIFF realizado (27.789 chars), a MESMA escala que o
# plano usou. O plano estimou raw_tokens 31000 / tokens 62000 e o diff real deu
# ~6.9k — uma superestimativa de ~4.5x, na mesma direcao e na mesma ordem de
# grandeza da que o 10-01 registrou (~3x). Duas fases seguidas errando para o
# mesmo lado e o dado util aqui; nao arredondado para parecer mais perto.
actuals:
  tokens: 6947
  tasks: 3
  commits: 6

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Terceiro membro de enum cujo VALOR e nome de arquivo em disco: escolhido uma vez, comentado como imutavel"
    - "Guarda de opt-in irma das existentes, dentro do mesmo `for tipo, devido_em in candidatos`"
    - "Validacao que rejeita `bool` explicitamente porque `isinstance(True, int)` e verdadeiro"
    - "Tripwire de volume com o numero-alvo ESCRITO a partir da conta e depois confirmado — nunca colhido da execucao"
    - "Mutacao deliberada do config para provar que o alarme dispara antes de confiar nele"

key-files:
  created: []
  modified:
    - l2scanner/agenda.py
    - l2scanner/config.py
    - config.toml
    - tests/test_agenda.py

key-decisions:
  - "A CHAMADA e um TIPO novo, nao uma lista de antecedencias: `Aviso.chave` ja carrega `tipo.value`, entao o marcador `_chamada` nasce distinto sem uma linha de codigo e nenhum `_antes`/`_agora` ja gravado em `.agenda/` muda de significado"
  - "A validacao nova recusa `true` explicitamente; a de `avisar_minutos_antes` NAO foi consertada nesta fase — mudar o comportamento de um campo que o usuario ja usa nao pertence a um plano de chamada"
  - "O teste do Solo Boss deixou de afirmar `all(tipo is ANTES)` e passou a afirmar o que sempre protegeu de verdade: nenhum aviso de AGORA, com as duas contagens (12 ANTES + 12 CHAMADA) separadas"
  - "As contagens de ANTES e CHAMADA sao afirmadas SEPARADAS: um total de 24 continuaria batendo se uma subisse e a outra descesse"
  - "A chamada afirma a FORMA dos horarios (`HH:10` em hora par), nao so a quantidade — e ali que a medida de campo dos 110 minutos fica visivel no teste"
  - "O texto diz `PRIVADO` em maiuscula e explica o porque no comentario do codigo: a ponte Baileys desta conta nao ingere mensagem de grupo"

patterns-established:
  - "Alarme de volume nunca e calibrado pela propria saida: o numero vem da conta escrita no plano e a execucao so CONFIRMA"
  - "Antes de confiar num tripwire rearmado, mutar o config de proposito e ver os testes certos caindo"
  - "Opt-in provado nos dois sentidos: o config diz 0 (leitura) E a varredura de um dia nao produz o aviso (comportamento)"

requirements-completed: [PRES-01, PRES-02]

coverage:
  - id: D1
    description: "A 1h50 de cada Solo Boss o grupo recebe uma chamada com o horario do proximo boss"
    requirement: "PRES-01"
    verification:
      - kind: unit
        ref: "tests/test_agenda.py#TestChamada::test_a_chamada_vence_no_minuto_configurado"
        status: pass
      - kind: integration
        ref: "tests/test_agenda.py#TestAgendaRealDoUsuario::test_solo_boss_chama_e_avisa_mas_nunca_fala_no_horario"
        status: pass
    human_judgment: false
  - id: D2
    description: "O aviso de 10 minutos continua saindo, byte a byte igual, com e sem a linha `Loot:` (D-04)"
    requirement: "PRES-01"
    verification:
      - kind: unit
        ref: "tests/test_agenda.py#TestTextoDoAviso::test_os_textos_de_ANTES_e_AGORA_sao_byte_a_byte_os_de_hoje"
        status: pass
      - kind: unit
        ref: "tests/test_agenda.py#TestChamada::test_o_mesmo_evento_continua_avisando_dez_minutos_antes"
        status: pass
    human_judgment: false
  - id: D3
    description: "TvT e Prime nao ganham chamada nenhuma: o campo e opt-in por evento (D-02)"
    requirement: "PRES-02"
    verification:
      - kind: integration
        ref: "tests/test_agenda.py#TestAgendaRealDoUsuario::test_tvt_e_prime_ficaram_exatamente_como_estavam"
        status: pass
      - kind: integration
        ref: "tests/test_agenda.py#TestAgendaRealDoUsuario::test_so_o_solo_boss_tem_chamada_no_arquivo_do_repositorio"
        status: pass
      - kind: unit
        ref: "tests/test_agenda.py#TestChamada::test_sem_o_campo_o_dia_inteiro_nao_produz_chamada_nenhuma"
        status: pass
    human_judgment: false
  - id: D4
    description: "A agenda nunca escreve `Solo Boss` no codigo — quem liga a chamada e o config.toml (D-03)"
    requirement: "PRES-02"
    verification:
      - kind: unit
        ref: "tests/test_agenda.py#TestChamada::test_o_mecanismo_e_generico_e_nao_conhece_nome_de_evento_nenhum"
        status: pass
    human_judgment: false
  - id: D5
    description: "A chave duravel da chamada e distinta das duas ja existentes e nao invalida marcador nenhum"
    requirement: "PRES-01"
    verification:
      - kind: unit
        ref: "tests/test_agenda.py#TestChaveDoAviso::test_a_chave_da_chamada_e_inedita_e_nao_invalida_marcador_nenhum"
        status: pass
      - kind: integration
        ref: "tests/test_agenda.py#TestRegistroEmDisco::test_a_agenda_inteira_com_registro_duravel_nao_duplica"
        status: pass
    human_judgment: false
  - id: D6
    description: "Um `chamar_minutos_antes` sem sentido (-1, texto, booleano, fracionario) derruba o scanner no arranque citando o NOME do evento"
    requirement: "PRES-02"
    verification:
      - kind: unit
        ref: "tests/test_agenda.py#TestChamarMinutosAntesNoToml::test_valor_sem_sentido_derruba_o_arranque_citando_o_evento (4 casos)"
        status: pass
    human_judgment: false
  - id: D7
    description: "O texto da chamada e legivel e util para um humano no grupo do WhatsApp — pergunta clara, horario visivel, instrucao de onde responder"
    verification: []
    human_judgment: true
    rationale: "Se a frase soa natural em portugues e se a party entende que tem que responder no privado sem ninguem explicar nao e verificavel por teste. O teste afirma que o nome, o horario, `.join` e a palavra `privado` estao la; se isso BASTA e julgamento de quem le a mensagem no celular."

# Metrics
duration: 25min
completed: 2026-08-26
status: complete
---

# Phase 10 Plan 02: A chamada de 1h50 na agenda Summary

**A agenda ganhou um terceiro tipo de aviso — `TipoDeAviso.CHAMADA` — que vence `chamar_minutos_antes` do evento, e faz no grupo, sozinho, a pergunta que hoje alguem faz de boca: quem vai no Solo Boss das 20:00.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3 de 3
- **Files modified:** 4
- **Suite:** 811 -> 836 testes (25 novos), nenhum afrouxado

## Accomplishments

- **O terceiro aviso existe e e opt-in.** `chamar_minutos_antes: int = 0` no `EventoAgendado`, com `0` significando desligado — o mesmo idioma de `silenciar_minutos`. A guarda entrou como irma das duas que ja moravam no `for tipo, devido_em in candidatos`, e por isso TvT e Prime nao mudaram de comportamento em um unico minuto do dia.
- **A chave duravel saiu de graca, como o desenho previa.** `Aviso.chave` nao mudou uma linha: `2026-08-24_solo-boss-2000_chamada` nasce distinto de `..._antes` e `..._agora`, e nenhum marcador ja gravado em `.agenda/` foi invalidado. A varredura ponta a ponta de dois dias com duas instancias continua provando zero duplicado — agora cobrindo tambem a chave nova, com uma asserção que EXIGE ver ao menos uma `_chamada` para a prova nao ser vazia.
- **O buraco do booleano foi fechado onde ele nasceu.** `isinstance(True, int)` e verdadeiro em Python, entao uma validacao copiada sem pensar aceitaria `chamar_minutos_antes = true` e trataria como "chamar 1 minuto antes" — uma chamada inutil, 12 vezes por dia, sem uma linha de erro no console. A confusao e provavel justamente porque o campo vizinho (`avisar_no_horario`) E booleano.
- **Os tres tripwires de volume subiram para o patamar certo, e foram CONFIRMADOS, nao descobertos.** Os numeros vieram da conta escrita no plano; a varredura devolveu exatamente `36`, `24` e `72`. Depois disso, o alarme foi mutado de proposito (`chamar_minutos_antes = 60` em TvT) e **seis** testes cairam, incluindo os tres tripwires — so entao ele foi considerado armado.
- **Zero dependencia nova.** `git diff --stat` entre a base e o HEAD toca 4 arquivos e nenhum arquivo de dependencia.

## Task Commits

1. **Tarefa 1 (TDD RED): a chamada que ainda nao existe** — `5db167a` (test)
2. **Tarefa 1 (TDD GREEN): `TipoDeAviso.CHAMADA`** — `7af22c1` (feat)
3. **Tarefa 2 (TDD RED): o campo do config.toml** — `2d2ee01` (test)
4. **Tarefa 2 (TDD GREEN): validacao + `config.toml`** — `9c997ef` (feat)
5. **Tarefa 3: os tripwires de volume no patamar novo** — `954372d` (test)
6. **Ajuste de verificacao: o teste de D-03 diz "generico" no nome** — `2b7bb50` (test)

## Files Created/Modified

- `l2scanner/agenda.py` — `TipoDeAviso.CHAMADA` (com o comentario dizendo que o VALOR e nome de arquivo e por isso nao muda), `EventoAgendado.chamar_minutos_antes` (com a medida de campo dos 110 minutos), o terceiro candidato + guarda em `avisos_devidos`, e o ramo da `CHAMADA` em `texto_do_aviso`. `Aviso.chave` e o `sort` intocados.
- `l2scanner/config.py` — bloco de validacao de `chamar_minutos_antes` em `_evento_de_dict`, na forma do analogo de `avisar_minutos_antes`, com a diferenca do booleano comentada e justificada; o campo passa ao `EventoAgendado(...)`.
- `config.toml` — `chamar_minutos_antes` no cabecalho "Campos de cada [[evento]]"; a frase "Cada evento gera DOIS avisos" virou "ATE TRES", numerados, dizendo qual e opt-in; `chamar_minutos_antes = 110` so no Solo Boss, precedido da razao do numero E do custo (12 mensagens/dia) e de como desligar.
- `tests/test_agenda.py` — `TestChamada` (10 testes), `TestChamarMinutosAntesNoToml` (7), duas asserções novas em `TestChaveDoAviso`/`TestTextoDoAviso` (4), `test_tvt_e_prime_ficaram_exatamente_como_estavam`, `test_so_o_solo_boss_tem_chamada_no_arquivo_do_repositorio`, `test_o_cabecalho_do_arquivo_documenta_o_campo`, e os tres tripwires reescritos.

## Decisions Made

- **O teste do Solo Boss foi renomeado porque o nome tinha deixado de ser verdade.** `test_solo_boss_avisa_de_duas_em_duas_horas_so_com_antecedencia` e o seu `all(tipo is ANTES)` descreviam um estado que a chamada acabou de terminar. O que ele SEMPRE protegeu de verdade e outra coisa: que `avisar_no_horario` continua desligado. Agora ele se chama `test_solo_boss_chama_e_avisa_mas_nunca_fala_no_horario` e afirma exatamente isso — nenhum aviso de `AGORA` — mais as duas contagens **separadas**. Separadas de proposito: um total de 24 continuaria batendo se as antecedencias caissem para 10 e as chamadas subissem para 14.
- **A chamada afirma a FORMA dos horarios, nao so a quantidade.** As chamadas saem em `HH:10` de hora PAR, e as antecedencias em `HH:50` de hora IMPAR. Essa assimetria E a medida de campo dos 110 minutos ficando visivel: 1h50 antes de um boss par cai dez minutos depois do boss par anterior. Um teste que so contasse 12 nao veria a diferenca entre `chamar_minutos_antes = 110` e `= 70`.
- **A validacao velha de `avisar_minutos_antes` NAO foi consertada.** Ela tem o mesmo buraco do booleano. Mudar o comportamento de um campo que o usuario ja usa, dentro de um plano sobre chamada, e a maneira classica de uma fase vazar para fora do seu escopo. Fica anotado abaixo, em Issues.
- **O teste de D-03 prova por comportamento e nao por grep.** O plano ja tinha antecipado a armadilha: `agenda.py` cita "Solo Boss" num comentario de volume desde a Fase 6, entao um gate textual nasceria vermelho. Um evento com nome inventado (`"Raid Qualquer"`, `chamar_minutos_antes=30`) recebe o mesmo tratamento e o nome sai no texto — isso e o que "generico" significa.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] O teste novo do cabecalho do `config.toml` cortava no lugar errado**

- **Found during:** Tarefa 2
- **Issue:** `test_o_cabecalho_do_arquivo_documenta_o_campo` isolava o cabecalho com `texto.split("[[evento]]")[0]`. Mas o proprio cabecalho escreve `# Campos de cada [[evento]]:` em prosa — o split cortava ali, no meio da lista de campos, e o teste falhava mesmo com o campo devidamente documentado duas linhas abaixo.
- **Fix:** Cortar no primeiro bloco de verdade, que comeca em coluna zero: `texto.split("\n[[evento]]")[0]`, com o comentario explicando a armadilha para quem mexer depois.
- **Files modified:** `tests/test_agenda.py`
- **Verification:** o teste passa, e continua falhando se a linha for removida do cabecalho (verificado ao rodar contra o `config.toml` ainda nao editado).
- **Committed in:** `9c997ef`

**2. [Rule 3 - Blocking] A verificacao 4 do plano (`-k "generico"`) selecionava ZERO teste**

- **Found during:** verificacao final
- **Issue:** O plano manda rodar `python -m pytest tests/test_agenda.py -q -k "generico"` como prova de D-03. O teste existia e passava, mas se chamava `test_o_mecanismo_nao_conhece_o_nome_de_evento_nenhum` — sem a palavra. O comando devolvia `95 deselected` e **exit code 0**, que um verificador desatento leria como prova, quando e so um filtro que nao casou. Um comando de verificacao que passa sem rodar nada e pior que um que falha.
- **Fix:** Teste renomeado para `test_o_mecanismo_e_generico_e_nao_conhece_nome_de_evento_nenhum`. O comando do plano agora seleciona 1 teste e ele passa.
- **Files modified:** `tests/test_agenda.py`
- **Committed in:** `2b7bb50`

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Nenhuma mudanca de escopo. As duas foram defeitos em testes escritos nesta fase, nao no codigo de producao.

## Issues Encountered

- **A varredura confirmou os tres numeros do plano na primeira tentativa.** `36` por dia, `24` de Solo Boss, `72` em dois dias — exatamente o que estava escrito antes de rodar. Registrado porque a ordem importa: o numero foi escrito primeiro e a execucao so confirmou. Se tivesse divergido, a instrucao era parar e investigar a Tarefa 1 ou 2, nao ajustar o teste.
- **O tripwire rearmado foi testado contra mutacao antes de ser considerado confiavel.** Com `chamar_minutos_antes = 60` posto em TvT no `config.toml`, cairam **6** testes: os tres de volume, o de leitura do config, o de opt-in por comportamento, e o da ordem de TvT/Prime no dia. `git checkout -- config.toml` devolveu o arquivo, e a suite voltou a 95/95 em `test_agenda.py` antes do commit. Sem esse passo, um alarme rearmado no numero errado passaria despercebido.
- **Debito conhecido e deliberadamente nao pago: `avisar_minutos_antes = true` ainda e aceito.** `isinstance(True, int)` e verdadeiro, entao o campo antigo trata `true` como `1` — o usuario receberia o aviso 1 minuto antes, calado, sem erro. O campo novo nao herdou o buraco. Consertar o antigo muda o comportamento de um campo em uso e pertence a um plano proprio; registrado no `WINDOWS.md`.
- **Ruff limpo nos quatro arquivos desta fase.** Os 26 erros pre-existentes em outros arquivos de teste, ja registrados no 10-01, continuam fora do escopo (SCOPE BOUNDARY) e nao foram tocados.

## Known Stubs

**A chamada convida a um comando que ainda nao faz nada — e isso e a ordem bloqueante do ROADMAP, nao um esquecimento.**

O texto da chamada manda o jogador responder `.join` no privado do bot. Depois do plano 10-01, `.join` e `.leave` sao reconhecidos pelo caminho real de leitura e ja tem a autorizacao certa, mas caem no `else: continue` do despacho em `atender_comandos` — ninguem entra em lista nenhuma, e quem mandar nao recebe resposta. O plano **10-03** fecha isso.

| Stub | Arquivo | Razao |
|---|---|---|
| A chamada pede `.join`, que ainda nao produz efeito nem resposta | `l2scanner/agenda.py` (texto) + `l2scanner/comandos.py` (despacho, do 10-01) | Ordem bloqueante declarada no `<objective>` do plano 10-02: "este plano entrega o AVISO; o `.join` que ele convida a mandar e o plano 10-03" |

**Consequencia se a fase parasse AQUI** (nao para — 10-03 vem em seguida, mas o verificador precisa saber): a partir do proximo boss par, o grupo receberia 12 perguntas por dia que ninguem consegue responder. Enquanto 10-02 e 10-03 nao estiverem AMBOS mergeados, `chamar_minutos_antes = 110` no `config.toml` e uma linha que promete mais do que o scanner entrega.

## Threat Flags

Nenhuma superficie de seguranca nova fora do `<threat_model>` do plano. As tres mitigacoes previstas foram aplicadas:

| Threat ID | Disposition | Onde ficou |
|---|---|---|
| T-10-07 (volume de mensagem no grupo) | mitigado | Opt-in por evento + os tres tripwires rearmados em 36/72/24, mutados de proposito para provar que disparam |
| T-10-09 (marcadores ja gravados em `.agenda/`) | mitigado | `Aviso.chave` intocada; a nao-colisao das tres chaves e afirmada por teste, e a varredura de duas instancias exige ver ao menos uma `_chamada` |
| T-10-10 (`chamar_minutos_antes` absurdo) | mitigado | Validacao no arranque recusa negativo, texto, booleano e fracionario, citando o NOME do evento |
| T-10-SC (instalacao de pacote) | mitigado | Zero dependencia nova; `git diff --stat` sobre a fase toca 4 arquivos, nenhum de dependencia |

## User Setup Required

Nenhuma. O `config.toml` do repositorio ja vem com `chamar_minutos_antes = 110` no Solo Boss. Quem nao quiser as 12 perguntas por dia apaga a linha — o comentario acima do bloco diz isso e diz o custo.

## Next Phase Readiness

Pronto para o 10-03. O que ele herda:

- `TipoDeAviso.CHAMADA` ja sai no minuto certo e ja tem marcador duravel proprio; 10-03 so precisa fazer o `.join` responder.
- `agenda.chave_da_ocorrencia(nome, alvo)` continua sendo o idioma de identidade de ocorrencia — a lista de presenca do 10-04 pendura nela.
- `chamar_minutos_antes` esta no `EventoAgendado`, entao "qual e a ocorrencia que acabou de ser chamada" e derivavel sem estado novo.

Sem blockers.

## Self-Check: PASSED

- Arquivos afirmados existem: `l2scanner/agenda.py`, `l2scanner/config.py`, `config.toml`, `tests/test_agenda.py`, `10-02-SUMMARY.md`.
- Commits afirmados existem: `5db167a`, `7af22c1`, `2d2ee01`, `9c997ef`, `954372d`, `2b7bb50`.
- `python -m pytest tests/ -q` -> **836 passed, 2 skipped** (linha de base 811; os 2 skips sao pre-existentes).
- `python -m pytest tests/test_agenda.py -q -k "chamada"` -> 15 passed.
- `python -m pytest tests/test_agenda.py -q -k "generico"` -> 1 passed.
- `python -m ruff check` sobre os arquivos alterados -> limpo.
- `git diff --stat 1af750f HEAD` -> 4 arquivos, nenhum de dependencia.
- `STATE.md` e `ROADMAP.md` NAO foram modificados — o orquestrador e o dono dessas escritas.

---
*Phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp*
*Completed: 2026-08-26*
