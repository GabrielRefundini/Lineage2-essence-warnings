---
gsd_state_version: 1.0
milestone: v1-mercado
milestone_name: )
current_phase: 2
current_phase_name: Leitura de pagina
status: executing
stopped_at: "Completed 02-01-PLAN.md (portao humano cumprido: calibration.json em negociacao)"
last_updated: "2026-08-30T10:43:15.211Z"
last_activity: 2026-08-30
last_activity_desc: "Fase 2 plano 01: as 14 chaves da leitura de pagina, as quatro colunas e o molde do cabecalho — e o calibration.json recalibrado para a grade de negociacao pela mao do usuario"
state_head: ba58b26f615f6d5d0a9f5c65f7c2f9cb8cf5d510
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 11
  completed_plans: 6
  percent: 25
---

# Project State

## Project Reference

**Core value:** Cada abertura do World Exchange vira coleta de dados — preços lidos passivamente da tela, sem nunca enviar input ao jogo.
**Current focus:** Phase 1 — Fundação — firewall, gravador e spike de campo
**Delivery decision (locked):** console-only na v1; comandos WhatsApp de mercado são v2.

## Current Position

Phase: 2 — Leitura de pagina
Plan: 2 of 6
Status: Ready to execute
Last activity: 2026-08-30 — Completed 02-01: superficie de calibracao da leitura de pagina

Progress: [███░░░░░░░] 25%

## Accumulated Context

### Decisions

- F0 (firewall de escopo) dobrada na Fase 1: FIRE-01 é um teste de CI + Out of Scope já registrado; fase própria seria cerimônia (granularity: coarse)
- DETC-02 e LEIT-04 vivem na Fase 4: são a fiação do laço `--mercado` e a superfície de console, conforme a espinha da pesquisa
- Fase 3 paraleliza com a Fase 2: depende só do formato da página aceita, não da leitura pronta
- Slugs de fase levam prefixo `mercado-` para não colidir com o workstream default
- [Phase 1]: O log ALTO da falha de gravacao mora em gravador.py, nao em Sessao.tick: o modulo que possui a verdade do disco e o que reporta a mentira, e assim sessao.py fica byte-identico
- [Phase 1]: Contagem do disco usa is_file(): um diretorio com nome de PNG seria contado por um glob cru, reintroduzindo a mentira dentro da propria conferencia
- [Phase 1]: O firewall FIRE-01 prova o vermelho por mutacao e por dist-info fabricada; instalar uma banida de verdade num teste seria cometer o proprio pecado
- **[2026-08-29] PERSISTÊNCIA É CSV, NÃO SQLITE.** Decisão do usuário. O motivo que decidiu:
  ele quer ler o dado a olho nu, importar no Google Sheets e entregar para outra IA analisar
  — CSV serve os três, um `.db` não serve nenhum sem ferramenta no meio. Das três
  justificativas do SQLite, duas já tinham caído (só o Yazalaque escreve, então não há
  concorrência e a dedup cabe em memória) e a terceira estava dimensionada errada. Separador
  de campo `;`, porque a vírgula decimal travada colapsaria um CSV separado por vírgula.
  Reescrito em REQUIREMENTS.md e ROADMAP.md; a pesquisa está marcada como superseded nessa
  parte.

- **[2026-08-29] A calibração PROPÕE e o usuário confirma.** A ferramenta pedia ao humano
  para adivinhar o sentido de uma frase e aceitava calado o retângulo desenhado — violando a
  disciplina do próprio projeto, que mede em vez de supor. Agora cada retângulo vem
  pré-desenhado a partir de medição (`mercado_geometria.py`) e o ENTER confirma. Três
  defeitos que só o uso humano encontrou: instruções ambíguas, a mensagem final descrevendo
  uma imagem que não era a gravada (chip aberto), e a contagem de linhas truncando `447//45`
  em 9 — três pixels de erro de mão custavam um anúncio por página.

- [Phase 02]: A coluna do nome termina no rotulo `Quantity` do cabecalho, e nao no texto da pagina: medir pelo texto daria 263 px (os dez nomes do frame sao o mesmo item) e truncaria nome longo. Os 270 px do plano viraram PISO afirmado em teste; o medido e 324 px.
- [Phase 02]: O fim do icone do item sai da SATURACAO, com referencia medida nas colunas de numero da mesma linha. Maior-vao e Otsu foram TENTADOS e pousam no miolo escuro do icone (84-107 entre bordas de 193-255), devolvendo 22 onde a resposta e 42 — as duas refutacoes ficaram escritas na docstring de `_fim_do_icone`.
- [Phase 02]: As colunas de numero sao contadas A PARTIR DA DIREITA, com `Buy` de ancora: da esquerda a contagem quebra quando o icone e o nome se fundem (vao de 5 px em 063752/frame_000000 contra 13 px em pagina-cheia/frame_000010).
- [Phase 02]: As 3 ancoras gravadas no calibration.json sao NOVAS, recortadas de 063752/frame_000000, porque as originais do usuario foram apagadas pelo incidente da janela quebrada 13. Ele conferiu na imagem de conferencia e aprovou.

### Blockers

- **Nenhum bloqueio ativo.** O bloqueio da Fase 1 (só o usuário podia gravar o World
  Exchange) foi cumprido: 8 gravações feitas, spike respondido e validado seção por seção,
  calibração completa pela mão do usuário em 2026-08-29.

- JANELA 13 ABERTA: `l2scanner/calibrar.py` (calibracao de PARTY) apaga TODA a calibracao de mercado — `calibrar_selecionando` monta uma Calibracao do zero (calibrar.py:353) e o fluxo grava por cima do arquivo inteiro (calibrar.py:1244). Confirmado em campo 2026-08-30. Enquanto nao for consertado, recalibrar a party DE NOVO custa a calibracao de mercado outra vez. Resgate em calibration.RESGATE-13-glifos.json.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260829-rd9 | OCR de nomes de item entra no escopo: LEIT-01 reescrito, coluna do nome recortada (LEIT-05) | 2026-08-29 | dcab841 | [260829-rd9-ocr-de-nomes-de-item-entra-no-escopo-lei](./quick/260829-rd9-ocr-de-nomes-de-item-entra-no-escopo-lei/) |
| 260830-apd | A calibracao de party para de apagar a de mercado: carrega o disco e preserva os 27 campos que nao sao dela | 2026-08-30 | 0c9038c | [260830-apd-party-calibration-nao-pode-apagar-a-cali](./quick/260830-apd-party-calibration-nao-pode-apagar-a-cali/) |

### Todos

- [ ] ~~**DEFINIR A `[mercado] watchlist` no `config.toml`**~~ — **DEIXOU DE SER BLOQUEIO
      em 2026-08-29** (quick `260829-rd9`). O motivo escrito aqui era o critério 1 da Fase 2,
      que dizia "todo item da watchlist visível é reconhecido" — esse critério foi substituído.
      LEIT-01 agora lê o nome por OCR e agrupa por similaridade; item desconhecido vira série
      nova sozinho. A watchlist não é mais a porta de entrada do que é registrado. Se
      sobreviver, é como filtro de DESTAQUE no console (Fase 4). Fecha a janela quebrada 12.

- [ ] Registrar/atualizar a discrepância de docs: CLAUDE.md diz Python 3.13, venv real é 3.12.10 (não bloqueia)

### Fatos operacionais que só existiam na conversa

- **FLAKE CONHECIDO, PRÉ-EXISTENTE:** `tests/test_agenda.py` vaza um `KeyboardInterrupt` que
  aborta a sessão inteira do pytest perto de ~88 testes. Medido: 5 abortos em 60 rodadas,
  reproduzido em commit anterior a todo o trabalho do mercado. **Abortar não é falhar** —
  rode de novo. Baseline verde: **1704 passed, 2 skipped**.

- **pytest roda no Python GLOBAL, não no `.venv`** (o venv não tem pytest). Isso é
  load-bearing para o firewall FIRE-01, que por isso varre três lugares.

- **`calibration.json` é gitignored** — estado de máquina, nunca commitado. Hoje carrega:
  3 âncoras, grade de 10 linhas de 45 px (layout `adena`, guardada como deslocamento
  `dx=-428 dy=258`), geometria 1720x1392, e **13 moldes de glifo completos**
  (`0-9`, `,`, `XM Coin`, `Adena`). `mercado_templates_de_nome` está VAZIO à espera da
  watchlist, e `mercado_limiar_de_template` está `null` — sem número inventado.

- **Recordings ficam só no checkout principal** (gitignored). Um executor em worktree tem de
  lê-los por caminho absoluto, somente leitura.

- **Worktree:** `worktree.baseRef: "head"` fixado em `.claude/settings.local.json` porque o
  repo não tem remote — sem isso o `base-check` degrada para execução sequencial (#683).

## Session Continuity

**Last session:** 2026-08-30T10:42:06.426Z

**Stopped At:** Completed 02-01-PLAN.md (portao humano cumprido: calibration.json em negociacao)
**Resume File:** None
**Next:** `/gsd-plan-phase 1` (workstream mercado) após aprovação

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 1 P1 | 8 min | 3 tasks | 4 files |
| Phase 02 P01 | 8h 14m | 3 tasks | 9 files |
