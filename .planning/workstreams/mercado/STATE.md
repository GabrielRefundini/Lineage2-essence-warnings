---
gsd_state_version: 1.0
milestone: v1-mercado
milestone_name: )
current_phase: 1
current_phase_name: Fundação — firewall, gravador e spike de campo
status: roadmap_created
stopped_at: Roadmap created, pre-approval
last_updated: "2026-08-27T23:27:19.331Z"
last_activity: 2026-08-27
last_activity_desc: Roadmap v1-mercado created (4 phases, 17/17 requirements mapped — a definição dizia 16, recontagem achou 17)
state_head: 70434c236e30980493023933a6ea87c1803de94e
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 4
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

**Core value:** Cada abertura do World Exchange vira coleta de dados — preços lidos passivamente da tela, sem nunca enviar input ao jogo.
**Current focus:** Fase 1 — Fundação: firewall, gravador e spike de campo.
**Delivery decision (locked):** console-only na v1; comandos WhatsApp de mercado são v2.

## Current Position

Phase: 1 (Fundação — firewall, gravador e spike de campo) — READY TO EXECUTE
Plan: Not planned yet
Status: Roadmap created — awaiting user approval, then `/gsd-plan-phase 1`
Last activity: 2026-08-27 — Roadmap v1-mercado created (4 phases, 17/17 requirements mapped — a definição dizia 16, recontagem achou 17)

Progress: [░░░░░░░░░░] 0%

## Accumulated Context

### Decisions

- F0 (firewall de escopo) dobrada na Fase 1: FIRE-01 é um teste de CI + Out of Scope já registrado; fase própria seria cerimônia (granularity: coarse)
- DETC-02 e LEIT-04 vivem na Fase 4: são a fiação do laço `--mercado` e a superfície de console, conforme a espinha da pesquisa
- Fase 3 paraleliza com a Fase 2: depende só do formato da página aceita, não da leitura pronta
- Slugs de fase levam prefixo `mercado-` para não colidir com o workstream default

### Blockers

- **Fase 1 bloqueia em gravações do usuário:** só o USUÁRIO pode gravar sessões reais do World Exchange. Ordem obrigatória: fix do gravador (FUND-01) → usuário grava → spike responde as perguntas de campo. Nenhuma fase seguinte deve ser planejada em detalhe antes disso.

### Todos

- [ ] Aprovação do roadmap pelo usuário (orquestrador commita depois)
- [ ] Decidir na Fase 1: variantes de encanto (+3 vs +4) na watchlist — incluir região do glifo no template ou declarar fora do v1
- [ ] Registrar/atualizar a discrepância de docs: CLAUDE.md diz Python 3.13, venv real é 3.12.10 (não bloqueia)

## Session Continuity

**Stopped At:** Roadmap created, pre-approval
**Resume File:** None
**Next:** `/gsd-plan-phase 1` (workstream mercado) após aprovação
