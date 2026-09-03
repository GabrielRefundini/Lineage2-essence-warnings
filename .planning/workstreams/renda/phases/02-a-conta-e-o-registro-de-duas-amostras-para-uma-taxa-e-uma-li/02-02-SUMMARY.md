---
phase: 02-a-conta-e-o-registro-de-duas-amostras-para-uma-taxa-e-uma-li
plan: 02
subsystem: renda
tags: [renda, aritmetica, fraction, level-up, lacuna, ast-gate, tdd, taxa]

requires:
  - phase: 01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa
    provides: "`LeituraDaRenda`, `CamposDaRenda`, `ValorDaRenda`, `ValorDaAdena`, `RecusaDaRenda`, `DECIMOS_DE_MILESIMO_POR_PONTO` e `conferir_o_par`"
  - phase: 02-a-conta-e-o-registro-de-duas-amostras-para-uma-taxa-e-uma-li
    plan: 01
    provides: "`PassoDaRenda`, `passo_entre`, `TaxaDaRenda`, `taxa_por_hora`, as cinco chaves de `[renda]` no `config.toml`, e o portao invertido de `tests/test_renda_par.py`"
provides:
  - "`passo_entre_campos` — o caminho de `CamposDaRenda`, que sobrevive ao nivel recusado (79% dos tiques) sem chamar `conferir_o_par`"
  - "As duas descontinuidades de nivel indisponivel: `-com-exp-caindo` (exclui o EXP) e `-com-exp-subindo` (PROCEDENCIA, o passo conta)"
  - "`DESCONTINUIDADE_DO_EXP_INDISPONIVEL` e `DESCONTINUIDADE_DA_ADENA_INDISPONIVEL`, e as tres tuplas `DESCONTINUIDADES_DO_TEMPO` / `_QUE_EXCLUEM` / `_DE_PROCEDENCIA` que as partem"
  - "`PassoDaRenda.aceito_para(grandeza)` e `ganho_do_passo` — o denominador POR GRANDEZA"
  - "`PassoDaRenda.niveis_ganhos` e `PassoDaRenda.carimbo`"
  - "`passos_da_janela`, `AsDuasTaxas` e `as_duas_taxas` — a janela movel por TEMPO e as duas taxas juntas"
  - "`TaxaDaRenda.por_minuto`, ao lado de `por_hora`, os dois `Fraction` ou `None` juntos"
  - "`TempoAteONivel` e `tempo_ate_o_nivel`, com os tres motivos de ausencia distintos"
  - "`ContagemDaRenda` e `contar_o_passo` — quatro fatos que nao se somam, mutados no lugar"
affects: [02-03 (le `descontinuidade` para a coluna do CSV), 02-04, Fase 3 (o laco), workstream dashboard]

actuals:
  tokens: 35000
  tasks: 3
  commits: 8

tech-stack:
  added: []
  patterns:
    - "Marcador de PROCEDENCIA ao lado dos de EXCLUSAO, partidos por tuplas com teste de particao"
    - "Denominador por GRANDEZA via `ganho is None` — a mesma frase para todo campo que nao mediu"
    - "Portao de AST com o conjunto de nomes DERIVADO e compartilhado com o controle positivo"
    - "Mascara deterministica por aritmetica modular (`(i*37) % 100 < 21`) em vez de semente de RNG"

key-files:
  created:
    - tests/test_renda_conta.py
    - .planning/workstreams/renda/phases/02-a-conta-e-o-registro-de-duas-amostras-para-uma-taxa-e-uma-li/deferred-items.md
  modified:
    - l2scanner/renda_conta.py

key-decisions:
  - "As descontinuidades ganharam DUAS familias — `DESCONTINUIDADES_DO_TEMPO` (matam toda grandeza) e as que excluem so uma — porque o denominador e por grandeza e `aceito` sozinho nao consegue dizer as duas coisas"
  - "Nasceram DOIS marcadores alem dos quatro do plano (`exp-indisponivel`, `adena-indisponivel`), porque a adena recusa em 21% dos tiques e sem marcador o passo dela sairia com a descontinuidade VAZIA, parecendo limpo"
  - "`PassoDaRenda` ganhou `carimbo` proprio: `CamposDaRenda` nao tem carimbo, e a recencia da taxa nao pode depender de qual dos dois caminhos produziu o passo"
  - "O EXP EXATAMENTE IGUAL nas duas pontas com o nivel recusado cai no ramo do `-subindo` e rende ganho ZERO — nao caiu, logo nao ha level up a supor, e excluir o passo inflaria a taxa"
  - "Os ganhos continuam COMPUTADOS num passo com recusa de par (comportamento do `02-01`), e quem filtra e `aceito`/`aceito_para` — nao nula-los deixa o teste do EXP-caindo afirmar `niveis_ganhos == 0` e o valor da subtracao simples, que e a prova direta de que a formula do level up nao disparou"
  - "`passo_entre_campos` DELEGA a `passo_entre` quando os seis valores estao presentes: uma aritmetica so, e `conferir_o_par` continua com um chamador so"

requirements-completed: [REND-01, REND-02, REND-03, REND-04, REND-05, REND-06, REG-02, LEIT-11]

coverage:
  - id: E1
    description: "O par de campo real da Faerlina rende 394_380 decimos, com o CONTROLE contra -605_620 e contra zero"
    requirement: REND-03
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestOParDeCampoDoLevelUp (3 testes)"
        status: pass
    human_judgment: false
  - id: E2
    description: "Dois niveis atravessados contam os dois, com o controle de um nivel so"
    requirement: REND-03
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestOLevelUpDeDoisNiveis (2 testes)"
        status: pass
    human_judgment: false
  - id: E3
    description: "A formula do level up nao dispara com o nivel parado, nem com o nivel descendo"
    requirement: LEIT-11
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestAFormulaDoLevelUpSoDisparaComONivelMudando (2 testes)"
        status: pass
    human_judgment: false
  - id: E4
    description: "Gasto de adena em campo proprio; a sequencia com gasto no meio nao soma ponta a ponta; o salto de ordem de grandeza e recusa e nao gasto"
    requirement: REND-04
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestAAdenaQueCaiEGastoENaoRendaNegativa (3 testes)"
        status: pass
    human_judgment: false
  - id: E5
    description: "Carimbo decrescente e evento nomeado, o intervalo guarda o sinal, e o passo sai do denominador; `abs`/`max`/`min` ausentes do modulo por AST, com controle positivo"
    requirement: REND-06
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestOCarimboQueAndaParaTras + ::TestOPortaoDoSinal (4 testes)"
        status: pass
    human_judgment: false
  - id: E6
    description: "Nivel recusado com EXP caindo nao vira level up; com EXP subindo o ganho e IGUAL ao do mesmo par com nivel; os dois marcadores sao textos diferentes; a adena continua contando; `conferir_o_par` nao e chamada (por injecao) e o controle prova que ela E chamada no par completo"
    requirement: REND-02
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestONivelRecusadoNaoViraLevelUpAdivinhado (9 testes)"
        status: pass
    human_judgment: false
  - id: E7
    description: "A janela corta por TEMPO: dobrar a cadencia nao muda a janela farmada e muda o `n`"
    requirement: REND-06
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestAJanelaEPorTempoENaoPorContagem (2 testes)"
        status: pass
    human_judgment: false
  - id: E8
    description: "Com e sem lacuna a taxa por hora e a MESMA por igualdade exata; duas lacunas somam; uma sequencia inteira dentro de uma lacuna nao tem taxa"
    requirement: REND-06
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestALacunaSaiDoDenominadorEEContadaAParte (3 testes)"
        status: pass
    human_judgment: false
  - id: E9
    description: "As duas taxas divergem com tempo parado e coincidem sem ele"
    requirement: REND-06
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestAsDuasTaxasENaoUma (2 testes)"
        status: pass
    human_judgment: false
  - id: E10
    description: "A ancora nao entra em denominador nenhum, e `sessao 1 / reinicio / sessao 2` soma os dois trechos em vez de atravessar o buraco"
    requirement: REG-02
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestAAncoraEOReinicio (2 testes)"
        status: pass
    human_judgment: false
  - id: E11
    description: "DISPONIBILIDADE MEDIDA: 600 amostras a 1 Hz com nivel 79% / adena 21% / EXP 0% de recusa produzem `n == 599` para o EXP e `n` derivado da mascara para a adena, as duas acima dos pisos"
    requirement: REND-06
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestADisponibilidadeMedida (4 testes) + ::TestODenominadorEPorGrandeza"
        status: pass
    human_judgment: false
  - id: E12
    description: "O tempo ate o nivel bate com a conta a mao; os TRES motivos de ausencia sao textos diferentes; EXP em 999_999 da tempo pequeno e positivo; nenhum `math.inf` nem captura de `ZeroDivisionError`"
    requirement: REND-05
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestOTempoAteOProximoNivel (7 testes)"
        status: pass
    human_judgment: false
  - id: E13
    description: "A contagem separa aceitas, lacunas, recusas por motivo e descontinuidades por motivo; os campos nao se somam; ela e mutada no lugar e nao e estado de modulo"
    verification:
      - kind: unit
        ref: "tests/test_renda_conta.py::TestAContagemDaRenda (5 testes)"
        status: pass
    human_judgment: false

duration: 33min
completed: 2026-09-03
status: complete
---

# Fase 2 Plano 02: A conta — os quatro deltas negativos, a janela e o tempo ate o nivel — Summary

**Os quatro casos em que `atual - anterior` mente estao presos por teste com o par de campo real da Faerlina, cada um com o seu controle; o nivel recusado em 79% dos tiques deixou de derrubar a adena e o EXP junto; e 600 amostras a 1 Hz sob as recusas MEDIDAS produzem `n == 599` para o EXP — o numero que separa a regra que ficou da regra que caiu.**

## Performance

- **Duration:** ~33 min de execucao (23h45 -> 00h18), depois de ~30 min de leitura e medicao de linha de base
- **Tasks:** 3 de 3
- **Files created:** 2 · **Files modified:** 1
- **`tests/test_renda_conta.py`:** 68 testes, 0 `skip`
- **Suite:** ver a secao "A linha de base virou um problema de calendario" — o piso foi conferido e passa, mas nao pela leitura literal do criterio

## Accomplishments

- **O par de campo REAL atravessa a conta e sai `394_380` decimos** — os 39,438 pontos percentuais que o usuario viu na tela —, com o CONTROLE ao lado afirmando que ele nao e o `-605_620` da subtracao ingenua **nem zero** (porque um `max(0, ...)` em cima do ingenuo passaria no primeiro teste). A procedencia das duas pontas esta na docstring da classe.
- **Dois niveis atravessados contam os dois.** `66 -> 68` rende `1_394_380` decimos, e o CONTROLE de um nivel so existe para que uma formula que somasse sempre um nivel inteiro nao passasse nos dois.
- **A formula do level up so dispara quando o nivel REALMENTE subiu.** O teste do nivel parado com o EXP caindo muito afirma `niveis_ganhos == 0` **e** que o ganho e a subtracao simples — as duas juntas provam que o ramo do level up nao foi executado —, e a mensagem de falha nomeia a alternativa que a CTX-5 recusou por escrito, com a medicao do LEIT-11 (3 das 4 leituras erradas de nivel passaram por CONCORDANCIA das duas escalas).
- **O nivel recusado virou um caminho de producao proprio, `passo_entre_campos`, e ele nao chama `conferir_o_par`** — provado por INJECAO de um substituto que registra chamadas, com o CONTROLE ao lado afirmando que no par completo ela **e** chamada exatamente uma vez.
- **Os dois marcadores de nivel indisponivel dizem coisas opostas e sao afirmados na MESMA funcao.** Sem esse par, uma implementacao que suprimisse os dois passaria em cada teste isolado. Ha ainda um teste de PARTICAO afirmando que `DESCONTINUIDADES_QUE_EXCLUEM` e `DESCONTINUIDADES_DE_PROCEDENCIA` cobrem os cinco marcadores sem sobra e sem sobreposicao — somar uma sexta obriga quem a escrever a dizer de que lado ela cai.
- **O denominador passou a ser POR GRANDEZA.** `PassoDaRenda.aceito_para(grandeza)` decide por tres condicoes, e a terceira (`ganho is None`) e a mesma frase para todo campo que nao mediu. O passo em que o nivel recusou e o EXP caiu sai do denominador do EXP e **continua** no da adena, com teste afirmando que a `janela_farmada_em_segundos` da adena e MAIOR que a do EXP na mesma sequencia.
- **O portao da DISPONIBILIDADE MEDIDA e o que discrimina.** 600 amostras a 1 Hz construidas com nivel 79% / adena 21% / EXP 0% de recusa — deterministicas por aritmetica modular escrita no proprio teste, sem RNG — afirmam para o EXP `n == 599`, `janela_farmada == 599.0` e `lacunas == 0`. Sob a regra que caiu na Tarefa 1, `n` seria da ordem de 26 e a janela ficaria abaixo do piso de 120 s: uma assercao de "nao nulo" passaria nas duas regras. Ha ainda o CONTROLE que roda a mesma sequencia com o nivel SEMPRE presente e afirma o mesmo `n` e a mesma taxa.
- **A exclusao da lacuna esta provada por IGUALDADE EXATA:** 21 amostras a 30 s dao `120_000` decimos/h com e sem um buraco de 20m30 no meio, com `lacunas_excluidas` 0 e 1 e `segundos_em_lacuna` `0.0` e `1230.0`.
- **Duas taxas, e elas divergem quando devem:** janela `600_000`/h contra sessao `360_000`/h numa sequencia com uma pausa de meia hora, e o CONTROLE numa sequencia sem tempo parado afirmando que as duas coincidem.
- **O tempo ate o nivel tem resposta ou tem um de TRES motivos distintos**, e cada um sai de uma sequencia de verdade — inclusive a taxa NEGATIVA, que e alcancavel pelo caminho do campo parcial. Os tres casos sao tratados **antes** da divisao, com portao de AST negando `math.inf` e `ZeroDivisionError` e com controle positivo.
- **Nenhum `float()` sobreviveu no modulo**, e o portao de AST prende isso. Os `float(...)` que o `02-01` tinha eram todos conversoes redundantes; sairam sem mudar comportamento.
- **Nenhuma dependencia nova** (`git diff --stat requirements.txt` vazio), **nenhum arquivo do `dashboard`**, **nenhuma linha de `renda_registro.py`**, e `import l2scanner.renda_conta` continua trazendo 129 modulos sem `cv2` e sem `numpy`.

## Task Commits

| # | Tarefa | Commit | Tipo |
|---|---|---|---|
| 1 | Os quatro deltas negativos — RED | `ee73cb1` | test |
| 1 | Os quatro deltas negativos — GREEN | `5f22c88` | feat |
| 2 | A janela, o denominador e as duas taxas — RED | `279b3b0` | test |
| 2 | A janela, o denominador e as duas taxas — GREEN | `2f44844` | feat |
| 3 | O tempo ate o nivel e a contagem — RED | `be23103` | test |
| 3 | O tempo ate o nivel e a contagem — GREEN | `2bcf9b4` | feat |
| — | Os itens adiados | `2999f1d` | docs |
| — | A particao das descontinuidades + docstring do modulo | `ef4a7d9` | refactor |

Os tres ciclos RED/GREEN estao em `git log` na ordem exigida. O unico REFACTOR e o ultimo commit, e ele nao muda comportamento: acrescenta o teste de particao e a secao nova da docstring do modulo.

## Files Created/Modified

- `l2scanner/renda_conta.py` — de 511 para ~1.100 linhas. Novos: os quatro marcadores (`-com-exp-caindo`, `-com-exp-subindo`, `exp-indisponivel`, `adena-indisponivel`), as tres tuplas de particao, `PassoDaRenda.carimbo` / `.niveis_ganhos` / `.aceito_para`, `ancora_da_sequencia`, `_passo_sem_delta`, `_exp_do_par`, `_adena_do_par`, `_decimos_de_um_nivel`, `_valor_do_campo`, `passo_entre_campos`, `_exp_sem_um_dos_lados`, `_marcador_do_campo_ausente`, `ganho_do_passo`, `TaxaDaRenda.por_minuto`, `passos_da_janela`, `AsDuasTaxas`, `as_duas_taxas`, `MOTIVO_DA_TAXA_DE_EXP_ZERADA` / `_NEGATIVA`, `TempoAteONivel`, `tempo_ate_o_nivel`, `ContagemDaRenda`, `contar_o_passo`.
- `tests/test_renda_conta.py` (novo) — 68 testes, zero `skip`, zero dependencia de OCR/pixel/disco/rede.
- `deferred-items.md` (novo, no diretorio da fase) — os dois achados fora de escopo.

## Decisions Made

1. **As descontinuidades se partiram em DUAS familias, e nao numa lista so.** `DESCONTINUIDADES_DO_TEMPO` (ancora, lacuna, relogio para tras) matam TODA grandeza porque o intervalo nao existe; as outras que excluem tiram so a grandeza do campo que faltou. `DESCONTINUIDADES_QUE_EXCLUEM` — o nome que o `02-01` deixou reservado — passou a ser a uniao das duas, e `DESCONTINUIDADES_DE_PROCEDENCIA` guarda a unica que nao exclui nada. Sem essa separacao, `aceito` teria de significar duas coisas ao mesmo tempo.
2. **Nasceram DOIS marcadores alem dos quatro que o plano nomeia.** O plano fala dos quatro casos da tabela, mas o proprio teste de disponibilidade que ele exige tem a **adena recusando em 21% dos tiques** — e um passo com a adena ausente sairia com a descontinuidade VAZIA, indistinguivel de um passo limpo. `exp-indisponivel` e `adena-indisponivel` fecham isso. O motivo de LEITURA de cada campo ja viaja na coluna propria do `02-01` (`motivo_do_nivel`, `motivo_do_exp`, `motivo_da_adena`); estes dois dizem o fato de PAR, e por isso um marcador so por passo nao perde informacao. A prioridade entre eles esta escrita no fonte.
3. **`PassoDaRenda` ganhou `carimbo` proprio.** `CamposDaRenda` **nao tem carimbo** — a Fase 1 carimba `LeituraDaRenda` e nao o objeto de tres campos —, e `taxa_por_hora` lia `aceitos[-1].atual.carimbo`. A recencia nao pode depender de qual dos dois caminhos produziu o passo, entao o carimbo virou campo do passo e chega por parametro no caminho de `CamposDaRenda`.
4. **O EXP EXATAMENTE IGUAL nas duas pontas com o nivel recusado conta, e cai no ramo do `-subindo`.** O ramo do `-caindo` existe para o EXP que ANDOU PARA TRAS, porque so ai ha um level up a supor. Um EXP identico rende ganho ZERO, que e uma medicao legitima; excluir o passo o tiraria do denominador e **inflaria** a taxa — o erro oposto e igual. Ha teste proprio, e o fonte diz que `==` cai nesse lado.
5. **Os ganhos continuam computados num passo com recusa de par.** Era tentador nula-los (o `aceito` ja exclui o passo de toda taxa, entao a aritmetica nao muda). Ficaram computados porque e o comportamento que o `02-01` gravou, e porque e o que permite ao teste do EXP-caindo afirmar `ganho == 80_012 - 685_632` — a prova DIRETA de que a formula do level up nao disparou, que um `None` nao daria.
6. **`passo_entre_campos` DELEGA a `passo_entre` quando os seis valores estao presentes.** Nao ha uma segunda aritmetica do level up nem uma segunda porta para `conferir_o_par`: aquele caminho descobre se o caminho completo pode ser usado, e usa.
7. **A sequencia de disponibilidade e deterministica por ARITMETICA MODULAR e nao por semente de RNG.** `(i * 37) % 100 < 21` acerta exatamente 21 presencas a cada 100 indices porque 37 e primo com 100; `(i * 53) % 100 < 79` faz o mesmo com 79. Os multiplicadores sao diferentes para que as duas recusas nao andem em lockstep. Isso e mais forte que `random.Random(semente)`: nao depende da implementacao do gerador, e os numeros exatos (126 e 474 presencas em 600) sao conferidos por um teste proprio ANTES de o teste principal se apoiar neles.
8. **O `n` da adena e DERIVADO da mesma mascara que construiu a sequencia**, e nunca escrito a mao. Um numero copiado envelheceria em silencio se a receita mudasse.

## Deviations from Plan

### 1. [Rule 2 — funcionalidade critica ausente] Dois marcadores alem dos quatro do plano

- **Found during:** Tarefa 1, ao escrever `passo_entre_campos`.
- **Issue:** o plano nomeia quatro descontinuidades de exclusao (as quatro da tabela dos casos), mas o teste de disponibilidade que ele exige na Tarefa 2 tem a **adena recusando em 21% dos tiques**. Sem um marcador para "a adena nao foi lida", esse passo sairia com `descontinuidade == ""` — visualmente identico a um passo limpo — e a coluna `descontinuidade` do CSV do `02-03` gravaria essa mentira uma vez a cada cinco linhas.
- **Fix:** `DESCONTINUIDADE_DO_EXP_INDISPONIVEL` e `DESCONTINUIDADE_DA_ADENA_INDISPONIVEL`, com a prioridade entre os marcadores escrita no fonte e o teste de particao garantindo que nenhum marcador fique fora das duas tuplas.
- **Files modified:** `l2scanner/renda_conta.py`.
- **Commit:** `5f22c88`, `ef4a7d9`.

### 2. [Correcao de criterio] A linha de base da suite mudou de 5355 para 5508 — e depois virou um problema de CALENDARIO

- **Found during:** antes da Tarefa 1 (medicao), e de novo na Tarefa 2 (a virada da meia-noite).
- **Issue, primeira metade:** o plano cita `5355 passed` como piso. O `02-01` ja tinha registrado que `5355` era o total SELECIONADO (passed + skipped) e nao `passed`. Medido nesta arvore, a linha de base real do `02-02` (base `9b90572`, ja com o `02-01` mergeado) e **5508 passed / 24 skipped**.
- **Issue, segunda metade — e ela nao e minha:** durante a Tarefa 2 o relogio da maquina virou de 2026-09-02 para 2026-09-03, e **15 testes de `test_sessao.py`, `test_janela_no_relogio.py` e `test_respawn.py` passaram a falhar**. `l2scanner/agenda.py:1004` faz `hoje = hoje or date.today()` e aqueles arquivos ancoram fixtures em `datetime(2026, 8, 30, ...)`. E a mesma familia por que `tests/test_agenda.py` ja estava desselecionado desde o `02-01`.
- **Prova de que e PRE-EXISTENTE:** o commit base `9b90572` foi extraido com `git archive` para uma arvore limpa e a suite rodou la, no mesmo instante. Resultado: **o mesmo conjunto de falhas**, 5492 passed + 16 failed. Nenhum modulo de `l2scanner/` importa `renda_conta` (varredura de arvore), entao nao ha caminho por onde esta tarefa pudesse alcancar aqueles modulos.
- **Fix:** **nada foi enfraquecido e nada foi consertado.** Regra de fronteira do executor: falhas pre-existentes em arquivos nao relacionados sao fora de escopo. Registradas em `deferred-items.md` (D-1) e no `.planning/WINDOWS.md`. O piso foi conferido na aritmetica que sobrevive a bomba:

  | Arvore | `passed` | `failed` | `passed + failed` |
  |---|---|---|---|
  | 2026-09-02, antes da virada (base) | 5508 | 0 | 5508 |
  | base `9b90572`, limpa, em 2026-09-03 | 5492 | 16 | **5508** |
  | `02-02` completo, mesmo instante | 5561 | 15 | **5576** |

  `5576 - 5508 = 68`, que e exatamente o numero de testes de `tests/test_renda_conta.py`. Nenhum teste desta fase falha, e nenhum teste existente foi perdido.
- **Files modified:** nenhum. E leitura de criterio + achado registrado.

### 3. [Limitacao registrada, nao consertada] A guarda de salto da adena nao roda no caminho parcial

- **Found during:** Tarefa 1.
- **Issue:** sem `LeituraDaRenda` nao ha `conferir_o_par`, e junto com ela deixam de rodar `a_adena_saltou_ordem_de_grandeza` (que sozinha so precisa da adena) e `o_exp_andou_para_tras`. Com o nivel recusado em 79% dos tiques, e a maioria dos passos.
- **Por que nao foi consertado:** chamar as irmas soltas de `renda_conta.py` derruba o portao invertido de `tests/test_renda_par.py`, e o portao esta certo — duas portas de entrada sao duas politicas de recusa divergindo. Fabricar um nivel para completar o objeto e exatamente o que a CTX-5 proibe. O conserto e uma composicao para o par PARCIAL em `renda_leitura.py`, que este plano nao possui.
- **Fix:** escrito na docstring de `passo_entre_campos`, registrado em `deferred-items.md` (D-2) e no `.planning/WINDOWS.md`. O teste `taxa_negativa_de_exp()` **usa** esse buraco para produzir a taxa negativa, e afirma que o tempo ate o nivel se recusa a transforma-la numa previsao.

---

**Total deviations:** 1 auto-fix (Rule 2), 1 correcao de criterio com achado pre-existente registrado, 1 limitacao estrutural documentada. **0 mudanca arquitetural, 0 criterio enfraquecido, 0 teste removido, 0 `skip` acrescentado.**

## Issues Encountered

- **`gsd-tools.cjs` nao existe em `<raiz>/gsd-core/bin/` nem em `.claude/gsd-core/bin/` desta arvore.** O binario esta em `$HOME/.claude/gsd-core/bin/gsd-tools.cjs`, e foi de la que os dois registros no `.planning/WINDOWS.md` sairam. O bootstrap do executor tentou a raiz primeiro e falhou com `MODULE_NOT_FOUND`.
- **`.planning/WINDOWS.md` foi modificado nesta onda paralela.** Ele e um array JSON compartilhado; se o `02-03` ou o `02-04` tambem escreverem nele, o merge vai conflitar no fechamento do array. O conflito e trivial de resolver (concatenar as entradas e renumerar os `id`), mas quem fizer o merge precisa saber que ele e esperado.

## Contratos que o `02-03` e a Fase 3 herdam

- **`PassoDaRenda` mudou de forma.** Campos novos: `carimbo: float` e `niveis_ganhos: int | None`. Metodo novo: `aceito_para(grandeza)`. `anterior`/`atual` agora podem ser `CamposDaRenda`.
- **`TaxaDaRenda` mudou de forma.** Campo novo: `por_minuto: Fraction | None`, sempre nulo junto com `por_hora`.
- **A coluna `descontinuidade` do CSV tem agora SEIS valores possiveis alem do vazio:** `ancora`, `lacuna`, `relogio-andou-para-tras`, `nivel-indisponivel-com-exp-caindo`, `nivel-indisponivel-com-exp-subindo`, `exp-indisponivel`, `adena-indisponivel`. O `02-03`, que e o dono do CSV, precisa aceitar os quatro novos — e o `-com-exp-subindo` **nao** e recusa: o passo dele conta.
- **`DESCONTINUIDADES_QUE_EXCLUEM` deixou de ser o conjunto inteiro.** Quem quiser "toda descontinuidade" tem de somar `DESCONTINUIDADES_DE_PROCEDENCIA`, e o teste de particao garante que as duas cobrem tudo.
- **Assinaturas somente-nomeadas e sem default (novas):** `passo_entre_campos(anterior, atual, *, carimbo_anterior, carimbo, fator_de_salto, limiar_de_lacuna_em_segundos)`; `passos_da_janela(passos, *, janela_em_segundos)`; `as_duas_taxas(passos, *, grandeza, janela_em_segundos, piso_de_amostras, piso_da_janela_em_segundos)`; `tempo_ate_o_nivel(*, exp_atual_em_decimos, taxa)`; `contar_o_passo(passo, contagem)`.
- **`janela_movel_minutos` do `config.toml` ganhou consumidor.** O `02-01` a deixou lida e validada com "AINDA NAO FAZ NADA" escrito ao lado; quem chama `as_duas_taxas` converte minutos para segundos.

## Known Stubs

Nenhum. Nenhum valor vazio codificado, nenhum `TODO`, nenhum `FIXME`, nenhum `placeholder`, nenhum `skip`, nenhuma funcao com `pass` no corpo.

`DESCONTINUIDADES_DE_PROCEDENCIA` tem um unico elemento hoje, e isso **nao e stub**: ela e uma particao de um conjunto que tem cinco membros e um deles nao exclui. O teste de particao afirma que a tupla e usada de verdade.

## Threat Flags

Nenhum. As seis ameacas com disposicao `mitigate` do `<threat_model>` do plano estao cobertas:

| ID | Mitigacao | Onde esta preso |
|---|---|---|
| T-02-09 | nivel recusado com EXP caindo e descontinuidade nomeada; a medicao do LEIT-11 esta no fonte; o IRMAO com o EXP subindo prova que a guarda nao virou supressao geral | `TestONivelRecusadoNaoViraLevelUpAdivinhado` (9 testes) |
| T-02-10 | descontinuidade nomeada, passo fora do denominador, e portao de AST sobre os TRES nomes que absorvem sinal, com controle positivo | `TestOCarimboQueAndaParaTras` + `TestOPortaoDoSinal` |
| T-02-27 | o par de EXP nao depende do nivel quando o EXP nao caiu; o argumento do limiar de lacuna esta no fonte com o numero | `TestADisponibilidadeMedida::test_O_EXP_SAI_COM_TODOS_OS_INTERVALOS_APESAR_DO_NIVEL_RECUSADO` (`n == 599`) |
| T-02-11 | `ContagemDaRenda` com quatro campos que nao se somam | `TestAContagemDaRenda` (5 testes) |
| T-02-12 | os tres casos tratados ANTES da divisao; portao negando `math.inf` e `ZeroDivisionError`, com controle | `TestOTempoAteOProximoNivel` (7 testes) |
| T-02-13 | `Fraction` na divisao, inteiro no resto; portao negando `float()` e `total_seconds()` | `TestAAritmeticaEExata` (4 testes) |
| T-02-SC | nenhum `pip install`; `git diff --stat requirements.txt` vazio | conferido |

## Verification Results

| Criterio do plano | Resultado |
|---|---|
| `pytest tests/test_renda_conta.py -q` termina em 0 com 0 skipped | **68 passed, 0 skipped** |
| `pytest tests/test_renda_conta.py tests/test_renda_conta_tracer.py tests/test_renda_par.py -q` em 0 com 0 skipped | **179 passed, 0 skipped** (com `test_config_da_renda.py` junto) |
| `pytest --ignore=tests/test_agenda.py -q` termina em 0 | **NAO** — 15 falhas PRE-EXISTENTES de calendario, identicas no commit base numa arvore limpa. Ver Deviation 2 |
| `passed` nao cai abaixo da linha de base | **5561 passed** contra 5492 na base no mesmo instante; `passed + failed` sobe de 5508 para 5576, exatamente os 68 testes novos |
| `abs`/`max`/`min` chamados em `renda_conta.py` | `[]` |
| literal `1_000_000` em `renda_conta.py` | `[]` |
| `float` / `total_seconds` chamados em `renda_conta.py` | `[]` |
| `inf` / `ZeroDivisionError` mencionados em `renda_conta.py` | `[]` |
| `now`/`time`/`imshow`/`selectROI`/`createTrackbar` em `renda_conta.py` | `[]` |
| `cv2` / `numpy` apos `import l2scanner.renda_conta` | `False False` (129 modulos) |
| `git diff --stat requirements.txt` | vazio |
| `git status --porcelain` sem `renda_registro.py` e sem `dashboard*` | limpo |

## Self-Check: PASSED

Arquivos conferidos em disco: `l2scanner/renda_conta.py`, `tests/test_renda_conta.py`, `deferred-items.md` — os tres presentes.

Commits conferidos em `git log`: `ee73cb1`, `5f22c88`, `279b3b0`, `2f44844`, `be23103`, `2bcf9b4`, `2999f1d`, `ef4a7d9` — os oito presentes. `git diff --diff-filter=D` vazio nos oito: nenhum apagou arquivo.
