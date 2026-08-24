---
gsd_state_version: '1.0'  # placeholder; syncStateFrontmatter overwrites on first state.* call
status: planning
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-24)

**Core value:** Quando alguém da party morre ou sai da PT, a galera fica sabendo no WhatsApp em segundos — mesmo quem está AFK.
**Current focus:** Phase 1 — Gate de entrega e fundação de captura

## Current Position

Phase: 1 of 4 (Gate de entrega e fundação de captura)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-08-24 — Roadmap criado (4 fases, 55/55 requisitos mapeados)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: `mss` para captura, não `dxcam` — `dxcam.grab()` devolve `None` em frame não alterado, e uma party window parada em AFK é exatamente esse caso (leitura ingênua = modo cego falso)
- [Roadmap]: Identidade por índice de linha + roster configurado em `config.toml`; OCR só bootstrap/re-âncora, e nunca dispara alerta sozinho (v1 dispensa OCR por completo — vai para v2)
- [Roadmap]: Cooldown mora na FSM, não no notificador — "um alerta até ressuscitar" é propriedade de estado, não janela de tempo
- [Roadmap]: BLIND congela os contadores de debounce em vez de zerá-los — uma morte 200 ms antes de um alt-tab ainda alerta na volta
- [Roadmap]: Blind curto continua só no console (decisão do usuário mantida), mas blind longo (~5 min) escala para uma mensagem no WhatsApp — silêncio de cobertura é o pior modo de falha do domínio

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

- ~~**[Fase 1 — portão duro]**~~ **RESOLVIDO 2026-08-24: o usuário roda o fork `fazer-ai/chatwoot` com Baileys integrado** na VPS do projeto Atenda. Baileys é bridge **não-oficial**, portanto a regra da janela de 24h da Meta **não se aplica** — mensagem livre iniciada por nós funciona a qualquer hora, e o fork suporta conversas de grupo nativas. O maior risco do projeto caiu. **Falta apenas a confirmação empírica**: rodar `python tools/check_whatsapp.py inboxes` (deve mostrar `Channel::Baileys`) e depois `enviar`, confirmando no celular. A ferramenta já está construída e commitada.
- ~~**[Aberto — falso negativo silencioso]**~~ **RESOLVIDO 2026-08-24 (teste do usuário): o HP de membro distante ATUALIZA AO VIVO**, não congela. Morte longe é detectável normalmente. Não há necessidade de detector de barra congelada por este motivo (o detector de frame estático continua valendo para o caso de jogo travado).
- **[Parcialmente aberto — nomeação de eventos]** A party window compacta as linhas quando alguém sai? O usuário enviou o par antes/depois (2026-08-24), mas **o teste foi inconclusivo**: quem saiu foi J4guar, que era o **último** da lista — nesse caso "compactar" e "preservar posição" produzem exatamente a mesma imagem. **O que os prints PROVARAM:** a janela é ancorada no topo e encolhe por baixo (altura varia com o número de membros), logo a âncora de visibilidade da UI deve ficar no TOPO da janela, nunca na borda inferior. **Teste que falta:** sair um membro do MEIO (ex.: Kaus, com Korzis abaixo) e ver se Korzis sobe de posição.
- **[Aberto — limiar de cor]** O matiz da barra de HP muda com o nível? Varredura em 90/70/50/30/10/1% na sessão gravada decide se limiar por hue é sólido.

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-08-24
Stopped at: ROADMAP.md e STATE.md criados; traceability de REQUIREMENTS.md preenchida
Resume file: None
