---
gsd_state_version: 1.0
workstream: receitas
milestone: v1-receitas
milestone_name: A receita lida da tela, e o custo real de craftar em adena, XM e R$
created: 2026-09-04
status: planning
current_phase: 1
current_phase_name: A receita pela tela
current_plan: 0
last_activity: 2026-09-04
last_activity_desc: Roadmap e requisitos escritos a partir da captura da janela Special Craft
stopped_at: Roadmap com 3 fases e 15 requisitos (RECE/CUST/ABA) escrito e parseado. Nenhuma fase planejada ainda.
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Current Position

**Status:** Planning — Phase 1 not yet planned
**Current Phase:** 1 — A receita pela tela
**Last Activity:** 2026-09-04 — roadmap e requisitos criados

## Progress

**Phases Complete:** 0 / 3
**Current Plan:** nenhum

## Accumulated Context

### Decisions (usuário, 2026-09-04)

- **Custo esperado por resultado.** O craft devolve uma distribuição (`30/50/20`), não um item.
  O custo de UMA unidade de um resultado é o custo da tentativa dividido pela probabilidade
  daquele resultado. É o único número comparável com o preço de mercado daquele grau.

- **Varredura única, catálogo em JSON.** Receita é dado estático; pôr essa região no ciclo
  noturno custaria calibração rodando a noite toda para reler o que não muda. O critério de qual
  arquivo recebe o quê é o mesmo já usado duas vezes aqui — **quem escreve**: o programa escreve
  JSON, o humano escreve TOML. O `config.toml` não é reescrito.

- **L-Coin fica fora do total convertido, dita em voz alta.** Ela não tem série no World
  Exchange. Inventar um câmbio para ela daria um total único e falso; manter a regra do
  `margem_de_craft` (componente sem série mata a margem) faria a receita da captura nunca
  aparecer. É divergência declarada do ANAL-04, e fica escrita no fonte.

### Fatos herdados que este workstream NÃO refaz

- **ANAL-04 existe**: `mercado_analise.margem_de_craft` + `config.Receita` /
  `ComponenteDaReceita` / `ler_receitas` / `ReceitaInvalida`. Conta em `Fraction`, casamento de
  nome exato que quebra listando candidatas.
- A docstring do `margem_de_craft` **já declara** a limitação que este workstream ataca (item 5:
  o programa não sabe se a receita é real).
- O `dashboard` já tem página, câmbio informado e calculadora de rotas.

### Blockers

- **Nenhum bloqueio de código.** O bloqueio é de **dado**: a Fase 1 precisa de uma captura real
  da janela Special Craft para calibrar, e a Fase 2 precisa de séries de mercado dos itens
  envolvidos — hoje o CSV tem só `Adena` e `Common Fafurion Doll`.

### Risco aberto, a medir e não a supor

- **Idioma misturado.** `Pedra da Rota` (PT) na tela de craft contra `Common Fafurion Doll` (EN)
  no World Exchange. O casamento é exato de propósito. Se as duas telas divergirem de idioma, ele
  quebra corretamente e parece defeito. A Fase 2 mede isso; nenhum plano pode assumir que casa.

## Session Continuity

**Stopped At:** Roadmap e requisitos escritos; nenhuma fase planejada.
**Resume File:** .planning/workstreams/receitas/ROADMAP.md
**Next:** `/gsd-plan-phase 1 --ws receitas`
