---
phase: 03-um-aviso-por-nascimento-com-o-chat-mandando-no-alvo
workstream: tiat
plan: 02
subsystem: detection
tags: [rearme-por-canal, d-24, ast-gate, vigia-de-bosses, falso-negativo-silencioso]

requires:
  - phase: 01-reconhecimento-do-nascimento
    provides: "VigiaDeBosses, AvisoDeBoss, OrigemDoAviso e o rearme por boss"
  - phase: 03-um-aviso-por-nascimento-com-o-chat-mandando-no-alvo/03-01
    provides: "o marcador duravel do episodio, nascimentos_calados e os helpers de AST de tests/test_anuncio_unico.py"
provides:
  - "VigiaDeBosses.CANAIS e o estado de rearme por (canal, boss): o anuncio do servidor deixou de poder ser descartado dentro do vigia"
  - "TestOChatNaoEEngolidoPeloAlvo: o criterio 2 afirmado na unidade"
  - "TestOAnuncioDoServidorNaoEEngolidoPeloAlvo: o criterio 2 afirmado ponta a ponta, atravessando vigia, disco e despacho"
  - "TestOEstadoDeRearmeEPorCanal: o portao AST de dois niveis de indexacao"
affects: [mortes-e-comandos, qualquer fase que leia o recorte do chat ou do alvo]

actuals:
  tokens: 45074
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Estado de deduplicacao particionado por CANAL DE ENTRADA, e nao so pelo sujeito: dois sinais independentes nunca se calam"
    - "Portao AST sobre a PROFUNDIDADE DE INDEXACAO de uma escrita de estado, e nao sobre a existencia de um nome"
    - "RED provado restaurando o arquivo de producao anterior por `git checkout <commit> -- <arquivo>`, e nao so por fonte fabricado"

key-files:
  created: []
  modified:
    - l2scanner/bosses.py
    - tests/test_bosses.py
    - tests/test_sessao.py
    - tests/test_anuncio_unico.py

key-decisions:
  - "D-31 implementado como escrito: apenas `_armado` e `_limpas` viraram por `(canal, boss)`. A `origem` do `AvisoDeBoss` continua saindo da PRESENCA (`no_chat`/`no_alvo`), e o bloco de tres ramos que escolhe entre CHAT_E_ALVO, CHAT e ALVO nao mudou uma letra. Origem vira nome de arquivo de ancora (D-18) e ramifica a mensagem de janela (D-16); deriva-la do canal mudaria o disco sem nenhum teste de respawn.py ficar vermelho."
  - "D-32 respeitado: o silencio do MARCADOR continua calando qualquer canal, inclusive o chat, porque ele deixa rastro. O que acabou foi o silencio do VIGIA, que nao deixava nenhum."
  - "A mudanca e simetrica de proposito: o alvo tambem deixou de ser engolido pelo chat. O custo e uma ancora de origem `alvo` a mais por episodio (T-03-11), ja aceito em D-15."
  - "O portao AST olha `_armado` e `_limpas` PELOS NOMES e so acusa alvos que ja sao `ast.Subscript` — a criacao do dicionario inteiro no `__init__` e legitima, e dicionarios de um nivel em outros atributos nao sao problema dele."

patterns-established:
  - "Provar o RED de um teste escrito DEPOIS do conserto restaurando o arquivo de producao do commit anterior, rodando, e devolvendo com `git checkout HEAD -- <arquivo>`"
  - "Portao AST com prova nao vazia em TRES pontos: fonte fabricado acusado, fonte fabricado aprovado, e o arquivo de producao REAL de antes do conserto acusado"

requirements-completed: [UNIC-02, UNIC-06, UNIC-08]

coverage:
  - id: D1
    description: "Com o alvo segurando Tiat North por ticks seguidos, o anuncio do servidor chegando no chat AINDA produz um aviso (criterio 2 / UNIC-02 / D-24)"
    requirement: UNIC-02
    verification:
      - kind: unit
        ref: "tests/test_bosses.py#TestOChatNaoEEngolidoPeloAlvo::test_o_anuncio_do_chat_atravessa_o_alvo_segurado"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestOAnuncioDoServidorNaoEEngolidoPeloAlvo::test_o_anuncio_do_servidor_CHEGA_com_o_boss_segurado_no_alvo"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestOAnuncioDoServidorNaoEEngolidoPeloAlvo::test_o_silencio_que_resta_e_o_do_MARCADOR_e_deixa_rastro"
        status: pass
    human_judgment: false
  - id: D2
    description: "O rearme continua existindo e continua sendo o primeiro filtro barato — duas leituras limpas, por boss — mas agora por CANAL, e a aritmetica nao mudou"
    verification:
      - kind: unit
        ref: "tests/test_bosses.py#TestOChatNaoEEngolidoPeloAlvo::test_o_canal_desarmado_nao_rearma_com_o_outro_sinal_presente"
        status: pass
      - kind: unit
        ref: "tests/test_bosses.py::test_so_rearma_depois_de_duas_leituras_limpas"
        status: pass
    human_judgment: false
  - id: D3
    description: "Os sete testes de rearme das Fases 1 e 2 atravessam INTACTOS, sem uma asseracao enfraquecida"
    verification:
      - kind: unit
        ref: "git diff 4ad2ebb..HEAD --numstat -- tests/test_bosses.py -> 126 adicoes, 0 remocoes"
        status: pass
      - kind: unit
        ref: "tests/test_bosses.py#TestORearmeEPorBoss (os quatro) + os tres de persistencia/rearme/OCR"
        status: pass
    human_judgment: false
  - id: D4
    description: "A origem do AvisoDeBoss continua sendo calculada por PRESENCA e nao por qual canal armou (D-31 / D-27 / D-16)"
    requirement: UNIC-06
    verification:
      - kind: unit
        ref: "tests/test_bosses.py#TestOChatNaoEEngolidoPeloAlvo::test_a_origem_do_aviso_que_atravessa_vem_da_PRESENCA"
        status: pass
      - kind: integration
        ref: "tests/test_sessao.py#TestAAncoragemSobreviveASupressao (03-01, intacto)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Um boss continua produzindo no MAXIMO um AvisoDeBoss por tick, mesmo com os dois canais armados (RECO-05)"
    verification:
      - kind: unit
        ref: "tests/test_bosses.py#TestOChatNaoEEngolidoPeloAlvo::test_os_dois_canais_armados_produzem_UM_aviso_so"
        status: pass
      - kind: unit
        ref: "tests/test_bosses.py#TestORearmeEPorBoss::test_mesmo_boss_nos_dois_sinais_gera_um_despacho_so"
        status: pass
    human_judgment: false
  - id: D6
    description: "O estado de rearme nao pode voltar a ser unico sem um teste nomeado ficar vermelho, e o portao morde nos dois sentidos"
    verification:
      - kind: unit
        ref: "tests/test_anuncio_unico.py#TestOEstadoDeRearmeEPorCanal::test_toda_escrita_no_estado_de_rearme_e_indexada_por_canal"
        status: pass
      - kind: unit
        ref: "tests/test_anuncio_unico.py#TestOEstadoDeRearmeEPorCanal::test_o_detector_acusa_o_estado_de_canal_unico_fabricado"
        status: pass
      - kind: unit
        ref: "tests/test_anuncio_unico.py#TestOEstadoDeRearmeEPorCanal::test_o_detector_aprova_o_estado_por_canal_fabricado"
        status: pass
      - kind: unit
        ref: "o portao rodado contra o l2scanner/bosses.py real do commit de8866f: 3 vermelhos"
        status: pass
    human_judgment: false
  - id: D7
    description: "Tudo demonstravel com o jogo fechado, sem OCR real e sem rede (UNIC-08)"
    requirement: UNIC-08
    verification:
      - kind: integration
        ref: "python -m pytest -q (2800 passed, 23 skipped, jogo fechado, sem rede)"
        status: pass
    human_judgment: false
  - id: D8
    description: "Em campo, com o usuario deixando o boss selecionado e saindo de perto do computador, o anuncio do servidor chega ao WhatsApp"
    verification: []
    human_judgment: true
    rationale: "O eixo do defeito e de CAMPO: exige OCR real, o boss realmente selecionado por minutos e o servidor anunciando. A suite prova a mecanica com Sessao construidas em tmp_path e o vigia alimentado por roteiro; a confirmacao final e o proximo nascimento de Tiat com o alvo segurado."

duration: 14min
completed: 2026-08-31
status: complete
---

# Phase 3 Plan 02: O chat mandando no alvo Summary

**O rearme do `VigiaDeBosses` deixou de ser um flag por boss e passou a ser um flag por `(canal, boss)`, de modo que o anuncio do servidor no chat nao pode mais ser descartado dentro do vigia por causa de um boss segurado no alvo.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-08-31T02:36:12Z
- **Completed:** 2026-08-31T02:50:00Z
- **Tasks:** 2
- **Files modified:** 4 (nenhum criado)

## Accomplishments

- **A causa 2 do defeito de campo esta fechada, e com ela um defeito PIOR que o ruido que iniciou a fase.** `bosses.py` montava `self._armado` como um flag por boss e desarmava em `if no_chat or no_alvo`, com a reentrada barrada por `if not self._armado[nome]: continue` — ANTES de a origem ser calculada. Com o boss segurado no alvo, `_limpas[nome]` nunca acumulava, `_armado[nome]` ficava em `False` indefinidamente, e o `Tiat North [Lv. 60] has spawned!` chegando no chat era jogado fora dentro do vigia: sem ancora, sem `ResultadoDoTick`, sem log. Agora atravessa.
- **O silencio mudou de lugar, do escuro para o rastro.** Depois desta fase o unico silencio possivel para um sinal presente e o do MARCADOR DURAVEL, que sempre grava a ancora, entra em `nascimentos_calados` e sai no `log.info` nomeando o boss e a origem. O silencio do VIGIA — que era indistinguivel de "nao aconteceu nada" — acabou. Isso e T-03-09 fechado.
- **A mudanca e de ESCOPO DE ESTADO e nunca de aritmetica.** Continua sendo `leituras_limpas_para_rearmar` leituras limpas consecutivas, continua sendo por boss, continua sendo o primeiro filtro barato que evita bater no disco a cada tick (risco 3 do ROADMAP). So a chave do dicionario mudou.
- **Os sete testes de rearme das Fases 1 e 2 atravessaram intactos.** `git diff 4ad2ebb..HEAD -- tests/test_bosses.py` mostra **126 adicoes e 0 remocoes**. Nenhuma asseracao foi enfraquecida e nenhum corpo de teste existente foi tocado.
- **D-31 preservado literalmente.** A `origem` continua saindo de `no_chat`/`no_alvo`, e ha teste nomeado afirmando que o aviso que atravessa e `CHAT_E_ALVO` e nao `CHAT`. Nenhuma linha de `respawn.py` mudou, e `ancoras_mais_recentes` e `_PESO_DA_ORIGEM` nao foram tocados.
- **O portao AST morde em tres pontos, e nao em um.** Fonte fabricado de canal unico acusado; fonte fabricado por canal aprovado (com um `self._ultimo_texto[nome]` de um nivel LEGITIMO junto, provando que o portao nao se alargou para o arquivo inteiro); e o `bosses.py` REAL de antes do conserto acusado, restaurado por `git checkout de8866f -- l2scanner/bosses.py` e devolvido em seguida.

## Task Commits

As duas tarefas sao `tdd="true"`. A Task 1 tem o par RED/GREEN explicito:

1. **Task 1 (RED): o anuncio do servidor engolido pelo alvo** — `de8866f` (test) — 4 vermelhos, 1 verde
2. **Task 1 (GREEN): o rearme por canal** — `3991fee` (feat) — 103 verdes em `tests/test_bosses.py`
3. **Task 2: a prova ponta a ponta e o portao** — `17782a0` (test)

## Files Created/Modified

- `l2scanner/bosses.py` — `VigiaDeBosses.CANAIS = ("chat", "alvo")`; `_armado` e `_limpas` indexados por canal e depois por boss; o laco de `avaliar` com o `for canal, presente in ...` decidindo por canal e o `disparou` juntando os dois num aviso so; o segundo paragrafo da docstring de classe contando a mudanca, o caso que a obriga e a consequencia aceita
- `tests/test_bosses.py` — `TestOChatNaoEEngolidoPeloAlvo`, cinco testes: o caso de campo, a origem por presenca, o simetrico, o guarda de RECO-05 e o guarda da aritmetica do rearme. **Apenas adicoes**
- `tests/test_sessao.py` — `TestOAnuncioDoServidorNaoEEngolidoPeloAlvo`, cinco testes ponta a ponta, com a distincao entre os dois silencios escrita na docstring da classe (D-32); mais a correcao de expectativa descrita em Deviations
- `tests/test_anuncio_unico.py` — `TestOEstadoDeRearmeEPorCanal` com `_base_e_niveis`, `_escritas_no_estado`, `_escritas_de_canal_unico` e os dois fontes fabricados

## Decisions Made

Nenhuma decisao nova. D-24, D-27, D-31 e D-32 estavam travadas no plano antes da primeira linha de codigo e foram seguidas. Duas observacoes que o plano nao previa e ficam registradas:

- **O plano previu a consequencia mas nao previu onde ela apareceria.** O `<behavior>` da Task 1 diz, por escrito, que o caso simetrico produz "uma ancora de origem `alvo` a mais". Essa ancora a mais e exatamente o que fez `DETECCOES_DE_ALVO` de `tests/test_sessao.py` ir de 6 para 7 — ver Deviations. A consequencia estava prevista; o sitio de teste que a mede, nao.
- **O RED da Task 2 foi provado contra o arquivo de producao anterior, e nao so contra fonte fabricado.** Os testes ponta a ponta da Task 2 foram escritos DEPOIS do conserto da Task 1, entao nasceriam verdes e nao provariam nada. Restaurar `l2scanner/bosses.py` do commit `de8866f`, rodar (3 de 5 vermelhos), e devolver com `git checkout HEAD -- l2scanner/bosses.py` foi o que tornou a prova real. O mesmo foi feito para o portao AST (3 de 5 vermelhos). Fica como padrao.

## Deviations from Plan

### Correcao de expectativa em testes de `03-01`

**1. [Rule 1 - Expectativa desatualizada pela mudanca deste plano] `DETECCOES_DE_ALVO` foi de 6 para 7 em `tests/test_sessao.py`**

- **Found during:** Task 1, no GREEN
- **Issue:** `TestOAlvoCalaDepoisDeOChatFalar` afirmava que sete remarcacoes de alvo produzem SEIS deteccoes, porque a primeira remarcacao caia dentro do desarme em memoria que a deteccao do chat acabara de fazer. Esse desarme cruzado E o defeito que este plano conserta: com os canais separados, a primeira remarcacao tambem chega ao marcador. Tres testes ficaram vermelhos — `test_as_remarcacoes_CONTINUAM_gravando_ancora`, `test_cada_deteccao_calada_deixa_rastro` e `test_o_silencio_sai_no_log_com_o_boss`.
- **Fix:** `DETECCOES_DE_ALVO = 7`, o comentario de sete linhas acima dela reescrito para contar a mudanca e a razao, e `test_o_silencio_sai_no_log_com_o_boss` passou de 1 para 2 supressoes com o comentario correspondente.
- **Nenhuma asseracao foi enfraquecida.** As tres continuam sendo igualdade exata de lista ou de contagem; o `assert "Tiat South" in calados[0]` virou `assert all("Tiat South" in m for m in calados)`, que e mais forte, e nao menos.
- **Por que isto nao viola a restricao do plano:** a proibicao e sobre `tests/test_bosses.py` e sobre "nenhum teste das Fases 1 e 2". Estes sao testes da propria Fase 3, escritos em `03-01` ontem, e `tests/test_sessao.py` esta em `files_modified` deste plano. A ancora `alvo` a mais e T-03-11, disposicao `accept`, e o `<behavior>` da Task 1 a nomeia por escrito.
- **Files modified:** `tests/test_sessao.py`
- **Commit:** `3991fee`

**Total deviations:** 1
**Impact on plan:** nenhum sobre o desenho. Nenhum teste das Fases 1 e 2 foi tocado; `git diff` sobre `tests/test_bosses.py` continua sendo 126 adicoes e 0 remocoes.

## Issues Encountered

- **Nenhuma falha de workstream concorrente para atribuir.** O plano avisava para esperar vermelhos em `tests/test_mercado_*.py` e `tests/test_medir_*.py` de `discord` e `mercado`. Na base deste worktree (`4ad2ebb`) eles estao todos verdes, entao nao ha nada para atribuir por `git log` nem para listar nominalmente.
- Nenhum arquivo de `<workstream_isolation>` foi lido, tocado ou renomeado.

## Verificacao medida

O `<verify>` nominal do plano:

```
python -m pytest tests/test_bosses.py tests/test_sessao.py \
  tests/test_anuncio_unico.py tests/test_respawn.py tests/test_agenda.py \
  tests/test_janela_no_relogio.py tests/test_presenca.py -q
678 passed
```

A suite inteira, com o jogo fechado, sem calibracao e sem rede:

```
python -m pytest -q
2800 passed, 23 skipped, 2 warnings in 76.61s
```

Baseline de `03-01`: 2785 passed, 23 skipped. Os 15 a mais sao exatamente os cinco testes novos de cada um dos tres arquivos de teste. Os 23 skips sao de ambiente (as ligacoes WinRT do OCR moram no `.venv` e nao no `python` do sistema usado dentro do worktree), identicos ao baseline.

Additions-only em `tests/test_bosses.py`:

```
git diff --numstat 4ad2ebb..HEAD -- tests/test_bosses.py
126     0       tests/test_bosses.py
```

## Known Stubs

Nenhum. Nao ha valor vazio codificado, texto de espera reservada nem componente sem fonte de dado nesta entrega.

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano. Nenhum endpoint, nenhum caminho de autenticacao, nenhuma dependencia e nenhum caminho novo para o disco — a unica mudanca de producao e estado em memoria dentro de `VigiaDeBosses`. T-03-02, T-03-09 e T-03-10 passaram de `mitigate` para mitigados; T-03-11 e T-03-12 continuam `accept` e sem mudanca de comportamento.

## User Setup Required

None — nenhuma chave de `config.toml` nova, nenhuma dependencia nova, nenhum servico externo.

## Next Phase Readiness

- **A fase 3 esta completa.** As duas causas do defeito de campo de 2026-08-30 estao fechadas: a causa 1 (sem marcador duravel) em `03-01`, a causa 2 (o alvo calando o chat) aqui.
- **O que resta e julgamento humano** (D8 acima): o proximo nascimento de Tiat com as duas instancias rodando e o boss segurado no alvo.
- **A ideia adiada continua adiada.** Revisitar D-15 (o alvo ancorar) nao foi tocado; `ancoras_mais_recentes` e `_PESO_DA_ORIGEM` estao byte a byte como estavam, confirmado por `git diff`.

## Self-Check: PASSED

- `l2scanner/bosses.py` contem `CANAIS = ("chat", "alvo")` e nenhuma escrita rasa em `_armado`/`_limpas` — afirmado pelo proprio portao AST
- `tests/test_bosses.py`, `tests/test_sessao.py` e `tests/test_anuncio_unico.py` existem em disco com as tres classes novas
- Os tres commits existem: `de8866f`, `3991fee`, `17782a0`
- `git diff --numstat 4ad2ebb..HEAD -- tests/test_bosses.py` = `126 0`
- `git diff 4ad2ebb..HEAD` nao toca `l2scanner/respawn.py`, `l2scanner/agenda.py`, `l2scanner/sessao.py` nem nenhum arquivo de `discord`/`mercado`

---
*Phase: 03-um-aviso-por-nascimento-com-o-chat-mandando-no-alvo*
*Completed: 2026-08-31*
