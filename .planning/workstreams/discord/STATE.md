---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: Ponte Discord
current_phase: 1
current_phase_name: Ponte viva — conexao provada e texto real
status: planning
stopped_at: "Roadmap escrito, aguardando aprovacao do usuario"
last_updated: "2026-08-28T00:00:00.000Z"
last_activity: 2026-08-28
last_activity_desc: Roadmap criado (3 fases, 21/21 exigencias mapeadas)
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

**Core value:** Quem nao abre o Discord fica sabendo do anuncio no WhatsApp, em segundos.
**Current focus:** Phase 1 — Ponte viva: conexao provada e texto real
**Workstream:** discord (paralelo a `mercado` e `default` no mesmo branch)

## Current Position

Phase: 1 (Ponte viva — conexao provada e texto real) — PLANNING
Plan: —
Status: Roadmap escrito, aguardando aprovacao
Last activity: 2026-08-28 — Roadmap criado

Progress: [░░░░░░░░░░] 0%

## Accumulated Context

### Decisions

- 3 fases (granularity: coarse). A divisao e vertical por etapa do caminho da mensagem: receber → formatar → entregar. Nada de camada horizontal.
- Fase 1 nao formata e nao entrega. Ela existe para provar o portao humano (intent MESSAGE CONTENT) com texto real no console antes que qualquer coisa seja construida em cima.
- ENTR-04 (nunca entregar duas vezes) vive na Fase 1, nao na Fase 3: o livro de ja-vistos decide como a mensagem recebida e identificada logo na PRIMEIRA linha do caminho de recebimento. Adiar custaria reescrever esse caminho no primeiro restart.
- CONF-04 (modo simulacao) vive na Fase 1: e o que torna o criterio do portao humano conferivel sem incomodar o grupo do WhatsApp. Na Fase 1 a ponte SO simula.
- A dependencia nova do Discord entra na Fase 1, com `tests/test_firewall_escopo.py` rodando verde na mesma fase — a banlist passa, mas isso e para se ver passando.
- Modulo, entrypoint e `.bat` proprios. `l2scanner/__main__.py` (editado pelo workstream `mercado`) e `l2scanner/notificador.py` nao sao tocados. Alem do merge, e a arquitetura certa: ponte async orientada a evento vs scanner sincrono de 1 Hz.
- Idioma: portugues sem acento em codigo, teste, commit e prosa de planejamento. Modulo no idioma do repo (`ponte_discord`, ao lado de `notificador`, `presenca`, `rastreador`).
- Slugs de fase levam prefixo `discord-` para nao colidir com escopos de commit dos workstreams `mercado` e `default`.
- Pesquisa de dominio pulada de proposito: `.planning/research/` e compartilhado e sobrescreveria os 220 KB da pesquisa do workstream `mercado`.

### Blockers

- **Fase 1 bloqueia no portao humano.** Os 4 passos so o USUARIO pode fazer: criar a aplicacao no Discord, ligar a intent **MESSAGE CONTENT**, convidar o bot para XM Games com `View Channel` + `Read Message History`, e informar o `conversation_id` do Chatwoot de destino. Sem a intent, a ponte conecta, parece saudavel e replica mensagem em branco para sempre — o modo de falha mais caro do milestone. O criterio 2 da Fase 1 fica pendente ate isso acontecer, e a Fase 2 nao deve ser planejada em detalhe antes dele estar conferido.

### Todos

- [ ] Aprovacao do roadmap pelo usuario (orquestrador commita depois)
- [ ] Decidir na Fase 1 o nome do `.bat` da raiz, no padrao dos existentes (`vigiar-party.bat`, `calibrar.bat`, `avisos-tvt.bat`)
- [ ] Escolher e travar a biblioteca cliente do Discord na Fase 1 (unica dependencia nova do projeto)

## Session Continuity

**Stopped At:** Roadmap escrito, aguardando aprovacao do usuario
**Resume File:** .planning/workstreams/discord/ROADMAP.md
**Next:** `/gsd-plan-phase 1` (workstream discord) apos aprovacao

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| — | — | — | — |
