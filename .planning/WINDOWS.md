---
schema_version: 1
open_count: 10
waived_count: 1
fixed_count: 2
total_count: 13
last_updated: 2026-08-30T10:16:35.946Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | quick-260825-pik | deviation | l2scanner/loot.py |  | momento_desejado: data sem ano escolhe a leitura de calendario mais proxima em vez do recuo de ano irrestrito que o plano descrevia — o plano se contradizia e o teste do futuro venceu | waived | Implementado esta CERTO e a divergencia e melhoria, nao defeito: em 25/08/2026 o recuo de ano irrestrito que o plano descrevia gravaria `.pegou 30/12 18:00 Korzis` como 30/12/2025 18:00 (medido lado a lado com a regra atual), e como `.loot/` nunca e podada e `.corrigir-<nick>` so alcanca o registro MAIS RECENTE, esse registro nasceria permanente e inalcancavel; a leitura de calendario mais proxima (loot.py:641-706) recusa esse caso com texto, nao com silencio (`ja passou`, loot.py:989), e CONCORDA com o recuo em 03/01/2027, onde as duas regras dao 30/12/2026 — ela nao perde nada e so fecha a porta destrutiva. Os dois sentidos da regra estao presos por test_data_no_FUTURO_ou_IMPOSSIVEL_recusa_e_nao_grava (tests/test_loot.py:1120) e test_a_virada_do_ANO (tests/test_loot.py:1135), com test_data_explicita_alcanca_um_dia_ANTIGO (:1095) cobrindo a data explicita, e a escolha ja foi ratificada em STATE.md ## Decisions [Phase 4] loot — o ledger registrava divergencia contra um plano que o proprio projeto ja substituiu. | 2026-08-25T21:59:50.148Z | 2026-08-26T13:53:16.579Z |
| 2 | quick-260825-psq | unmet-truth | l2scanner/ocr.py |  | ESCALA_DE_DETECCAO=1 nao le os digitos do banner real (le MOninutes): com 1x e 3x as duas escalas nunca concordam e o recurso nunca anuncia | fixed |  | 2026-08-25T22:04:27.547Z | 2026-08-25T22:11:00.846Z |
| 3 | 10 | todo | l2scanner/config.py |  | avisar_minutos_antes ainda aceita true (isinstance(True, int) e verdadeiro); chamar_minutos_antes nao herdou o buraco, o campo antigo espera plano proprio | open |  | 2026-08-26T15:25:06.252Z |  |
| 4 | 10 | todo | l2scanner/presenca.py |  | texto_de_fechamento(sugestao=) nasce declarado e sem chamador; quem o preenche e o plano 10-05 (D-13) | open |  | 2026-08-26T16:22:22.620Z |  |
| 5 | quick-260827-fsk | unrun-verify | .planning/quick/260827-fsk-trocar-o-discriminador-da-legibilidade-d/260827-fsk-PLAN.md |  | verify da Task 3 aponta para .planning/STATE.md, movido para .planning/workstreams/default/ por processo concorrente; STATE atualizado no caminho novo | open |  | 2026-08-27T15:59:09.257Z |  |
| 6 | 1 | unrun-verify | l2scanner/__main__.py |  | human-check da Task 1 nao rodou: resumo final com 0 confirmados / N falhas / 0 no disco exige uma sessao real com destino de gravacao invalido | open |  | 2026-08-27T23:47:45.913Z |  |
| 7 | 1 | unrun-verify | l2scanner/gravador.py |  | human-check da Task 2 nao rodou: PNG de ~3,5 MB da janela inteira exige o jogo aberto (gate externo da fase) | open |  | 2026-08-27T23:47:46.298Z |  |
| 8 | 1 | unrun-verify | tools/conferir_gravacoes_do_spike.py |  | verificacao 5 do 01-02 nao rodou: o portao das gravacoes so sai com codigo 0 depois que o usuario gravar as 8 sessoes (gate externo, Task 3) | open |  | 2026-08-28T00:18:09.481Z |  |
| 9 | 1 | deviation | tests/fixtures/mercado/ |  | criterio de aceite do 01-02 nao satisfeito: pedia >=8 positivos do 27x, existem 2 — so 2 dos 9 frames _JANELA tem o painel do mercado aberto (medido; os outros mostram o inventario) | open |  | 2026-08-28T00:18:16.266Z |  |
| 10 | 1 | unrun-verify | PORTAO-DISCORD.txt |  | Criterio 2 da Fase 1 (texto real no console) nao conferido: os 4 passos do portao humano do Discord nao foram dados | open |  | 2026-08-28T17:31:16.484Z |  |
| 11 | 1 | unrun-verify | l2scanner/__main__.py |  | Task 3 do 01-04: a sessao ao vivo --janela SEM calibracao de mercado nao foi rodada com o jogo aberto. O caminho degenerado esta provado por teste (campo None, extras sem a chave), mas o comportamento identico ao de antes num farm real nao foi observado | open |  | 2026-08-28T20:04:07.455Z |  |
| 12 | quick-260829-rd9 | unmet-truth | .planning/workstreams/mercado/STATE.md | 72 | Todo da watchlist cita verbatim o criterio 1 da Fase 2 que foi substituido em 260829-rd9; a watchlist deixou de ser pre-requisito de bloqueio | fixed |  | 2026-08-29T23:05:24.348Z | 2026-08-29T23:08:10.741Z |
| 13 | 02 | deviation | l2scanner/calibrar.py |  | calibrar.py (calibracao de PARTY) apaga TODA a calibracao de mercado: calibrar_selecionando monta uma Calibracao do zero (calibrar.py:353) e o fluxo grava por cima do arquivo inteiro (calibrar.py:1244). CONFIRMADO EM CAMPO 2026-08-30: o usuario rodou calibrar.bat e perdeu 13 moldes de glifo, 3 ancoras, mercado_grade e mercado_limiar_de_glifo. E a gemea exata do CR-04, ja consertado do lado do mercado e nunca do lado da party. Resgate em calibration.RESGATE-13-glifos.json | open |  | 2026-08-30T10:16:35.946Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "quick-260825-pik",
    "file": "l2scanner/loot.py",
    "line": null,
    "description": "momento_desejado: data sem ano escolhe a leitura de calendario mais proxima em vez do recuo de ano irrestrito que o plano descrevia — o plano se contradizia e o teste do futuro venceu",
    "status": "waived",
    "reason": "Implementado esta CERTO e a divergencia e melhoria, nao defeito: em 25/08/2026 o recuo de ano irrestrito que o plano descrevia gravaria `.pegou 30/12 18:00 Korzis` como 30/12/2025 18:00 (medido lado a lado com a regra atual), e como `.loot/` nunca e podada e `.corrigir-<nick>` so alcanca o registro MAIS RECENTE, esse registro nasceria permanente e inalcancavel; a leitura de calendario mais proxima (loot.py:641-706) recusa esse caso com texto, nao com silencio (`ja passou`, loot.py:989), e CONCORDA com o recuo em 03/01/2027, onde as duas regras dao 30/12/2026 — ela nao perde nada e so fecha a porta destrutiva. Os dois sentidos da regra estao presos por test_data_no_FUTURO_ou_IMPOSSIVEL_recusa_e_nao_grava (tests/test_loot.py:1120) e test_a_virada_do_ANO (tests/test_loot.py:1135), com test_data_explicita_alcanca_um_dia_ANTIGO (:1095) cobrindo a data explicita, e a escolha ja foi ratificada em STATE.md ## Decisions [Phase 4] loot — o ledger registrava divergencia contra um plano que o proprio projeto ja substituiu.",
    "recorded_at": "2026-08-25T21:59:50.148Z",
    "resolved_at": "2026-08-26T13:53:16.579Z"
  },
  {
    "id": 2,
    "kind": "unmet-truth",
    "phase": "quick-260825-psq",
    "file": "l2scanner/ocr.py",
    "line": null,
    "description": "ESCALA_DE_DETECCAO=1 nao le os digitos do banner real (le MOninutes): com 1x e 3x as duas escalas nunca concordam e o recurso nunca anuncia",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-25T22:04:27.547Z",
    "resolved_at": "2026-08-25T22:11:00.846Z"
  },
  {
    "id": 3,
    "kind": "todo",
    "phase": "10",
    "file": "l2scanner/config.py",
    "line": null,
    "description": "avisar_minutos_antes ainda aceita true (isinstance(True, int) e verdadeiro); chamar_minutos_antes nao herdou o buraco, o campo antigo espera plano proprio",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T15:25:06.252Z",
    "resolved_at": null
  },
  {
    "id": 4,
    "kind": "todo",
    "phase": "10",
    "file": "l2scanner/presenca.py",
    "line": null,
    "description": "texto_de_fechamento(sugestao=) nasce declarado e sem chamador; quem o preenche e o plano 10-05 (D-13)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T16:22:22.620Z",
    "resolved_at": null
  },
  {
    "id": 5,
    "kind": "unrun-verify",
    "phase": "quick-260827-fsk",
    "file": ".planning/quick/260827-fsk-trocar-o-discriminador-da-legibilidade-d/260827-fsk-PLAN.md",
    "line": null,
    "description": "verify da Task 3 aponta para .planning/STATE.md, movido para .planning/workstreams/default/ por processo concorrente; STATE atualizado no caminho novo",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-27T15:59:09.257Z",
    "resolved_at": null
  },
  {
    "id": 6,
    "kind": "unrun-verify",
    "phase": "1",
    "file": "l2scanner/__main__.py",
    "line": null,
    "description": "human-check da Task 1 nao rodou: resumo final com 0 confirmados / N falhas / 0 no disco exige uma sessao real com destino de gravacao invalido",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-27T23:47:45.913Z",
    "resolved_at": null
  },
  {
    "id": 7,
    "kind": "unrun-verify",
    "phase": "1",
    "file": "l2scanner/gravador.py",
    "line": null,
    "description": "human-check da Task 2 nao rodou: PNG de ~3,5 MB da janela inteira exige o jogo aberto (gate externo da fase)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-27T23:47:46.298Z",
    "resolved_at": null
  },
  {
    "id": 8,
    "kind": "unrun-verify",
    "phase": "1",
    "file": "tools/conferir_gravacoes_do_spike.py",
    "line": null,
    "description": "verificacao 5 do 01-02 nao rodou: o portao das gravacoes so sai com codigo 0 depois que o usuario gravar as 8 sessoes (gate externo, Task 3)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-28T00:18:09.481Z",
    "resolved_at": null
  },
  {
    "id": 9,
    "kind": "deviation",
    "phase": "1",
    "file": "tests/fixtures/mercado/",
    "line": null,
    "description": "criterio de aceite do 01-02 nao satisfeito: pedia >=8 positivos do 27x, existem 2 — so 2 dos 9 frames _JANELA tem o painel do mercado aberto (medido; os outros mostram o inventario)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-28T00:18:16.266Z",
    "resolved_at": null
  },
  {
    "id": 10,
    "kind": "unrun-verify",
    "phase": "1",
    "file": "PORTAO-DISCORD.txt",
    "line": null,
    "description": "Criterio 2 da Fase 1 (texto real no console) nao conferido: os 4 passos do portao humano do Discord nao foram dados",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-28T17:31:16.484Z",
    "resolved_at": null
  },
  {
    "id": 11,
    "kind": "unrun-verify",
    "phase": "1",
    "file": "l2scanner/__main__.py",
    "line": null,
    "description": "Task 3 do 01-04: a sessao ao vivo --janela SEM calibracao de mercado nao foi rodada com o jogo aberto. O caminho degenerado esta provado por teste (campo None, extras sem a chave), mas o comportamento identico ao de antes num farm real nao foi observado",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-28T20:04:07.455Z",
    "resolved_at": null
  },
  {
    "id": 12,
    "kind": "unmet-truth",
    "phase": "quick-260829-rd9",
    "file": ".planning/workstreams/mercado/STATE.md",
    "line": 72,
    "description": "Todo da watchlist cita verbatim o criterio 1 da Fase 2 que foi substituido em 260829-rd9; a watchlist deixou de ser pre-requisito de bloqueio",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-29T23:05:24.348Z",
    "resolved_at": "2026-08-29T23:08:10.741Z"
  },
  {
    "id": 13,
    "kind": "deviation",
    "phase": "02",
    "file": "l2scanner/calibrar.py",
    "line": null,
    "description": "calibrar.py (calibracao de PARTY) apaga TODA a calibracao de mercado: calibrar_selecionando monta uma Calibracao do zero (calibrar.py:353) e o fluxo grava por cima do arquivo inteiro (calibrar.py:1244). CONFIRMADO EM CAMPO 2026-08-30: o usuario rodou calibrar.bat e perdeu 13 moldes de glifo, 3 ancoras, mercado_grade e mercado_limiar_de_glifo. E a gemea exata do CR-04, ja consertado do lado do mercado e nunca do lado da party. Resgate em calibration.RESGATE-13-glifos.json",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-30T10:16:35.946Z",
    "resolved_at": null
  }
]
````
