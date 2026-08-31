---
workstream: identidade
created: 2026-08-30
---

# Project State

## Current Position

**Status:** Roadmap pronto, nenhuma fase planejada
**Current Phase:** None (proxima: Phase 1 - O acervo e o silencio dele)
**Last Activity:** 2026-08-30
**Last Activity Description:** ROADMAP.md criado; 16/16 requisitos mapeados em 3 fases

## Progress

**Phases Complete:** 0/3
**Current Plan:** N/A

## Accumulated Context

### Decisions

- **O acervo aprendido mora em pasta propria, no precedente do `.loot/` — nunca no
  `calibration.json`.** `calibrar.py:1281` lista `nomes` e `assinaturas` dentro de
  `CAMPOS_DA_PARTY`, a lista de DONOS: o `fundir_com_a_calibracao_em_disco`
  (calibrar.py:1300) preserva por subtracao tudo o que a party NAO possui, e esses dois
  campos a party possui. Sao reescritos por desenho, em toda rodada. Ver WINDOWS #13.
- **O comando de batismo e do nivel de DONO e fica FORA de `COMANDOS_DE_MEMBRO`.** Nome
  errado e corrupcao duravel num acervo que nunca e podado — mesma familia de `/corrigir`
  e `/pegou`, que ja sao de dono pela mesma razao (comandos.py:819-853).
- **Ordem escolhida: durabilidade antes do aprendizado.** O aprendizado-primeiro nao so
  morreria na primeira `calibrar.bat`; gravando em `cal.assinaturas` com nome de mentira
  ele promoveria uma linha anonima a sujeito e mataria a degradacao `#linhaN` do
  `rastreador.py`. Argumento completo no Overview do ROADMAP.md.

### Blockers

Nenhum.

## Session Continuity

**Stopped At:** Roadmap criado, aguardando `/gsd-plan-phase 1`
**Resume File:** .planning/workstreams/identidade/ROADMAP.md
