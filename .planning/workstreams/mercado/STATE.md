---
gsd_state_version: 1.0
milestone: v1-mercado
milestone_name: )
current_phase: 1
status: executing
stopped_at: "Fase 1: gap closure 01-05 PARADO no portao de marcacao dos glifos (a primeira mao humana no fluxo completo)"
last_updated: "2026-08-29T21:40:54.933Z"
last_activity: 2026-08-29
last_activity_desc: Phase 1 marked complete
state_head: 048eaa3d79629bd8732d5680c4d7f9b45cce04bf
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 5
  completed_plans: 5
  percent: 0
---

# Project State

## Project Reference

**Core value:** Cada abertura do World Exchange vira coleta de dados — preços lidos passivamente da tela, sem nunca enviar input ao jogo.
**Current focus:** Phase 1 — Fundação — firewall, gravador e spike de campo
**Delivery decision (locked):** console-only na v1; comandos WhatsApp de mercado são v2.

## Current Position

Phase: 1 — COMPLETE
Plan: 2 of 4
Status: Phase 1 complete
Last activity: 2026-08-29 — Phase 1 marked complete

Progress: [░░░░░░░░░░] 0%

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

### Blockers

- **Nenhum bloqueio ativo.** O bloqueio da Fase 1 (só o usuário podia gravar o World
  Exchange) foi cumprido: 8 gravações feitas, spike respondido e validado seção por seção,
  calibração completa pela mão do usuário em 2026-08-29.

### Todos

- [ ] **DEFINIR A `[mercado] watchlist` no `config.toml`** — é entrada do usuário e a Fase 2
      depende dela: sem os moldes de nome, o critério 1 ("todo item da watchlist visível é
      reconhecido") não tem o que reconhecer. Variantes de encanto são entradas SEPARADAS
      (`Dragon Belt`, `+3 Dragon Belt`, `+4 Dragon Belt`), decisão D-05. Depois de escrever,
      rodar `calibrar-mercado.bat` de novo para cortar os moldes.
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

**Last session:** 2026-08-29T02:59:07.936Z

**Stopped At:** Fase 1: gap closure 01-05 PARADO no portao de marcacao dos glifos (a primeira mao humana no fluxo completo)
**Resume File:** .planning/workstreams/mercado/phases/01-funda-o-firewall-gravador-e-spike-de-campo/01-05-SUMMARY.md
**Next:** `/gsd-plan-phase 1` (workstream mercado) após aprovação

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 1 P1 | 8 min | 3 tasks | 4 files |
