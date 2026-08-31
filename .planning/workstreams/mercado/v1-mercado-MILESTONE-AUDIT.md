---
milestone: v1-mercado
workstream: mercado
audited: 2026-08-31
status: gaps_found
scores:
  requirements: 17/18
  phases: 1/4 verificadas sem pendencia
  integration: 4/4 fios ligados
  flows: 1/1 fluxo ponta a ponta exercitado em producao
gaps:
  requirements:
    - id: "DETC-02"
      status: "partial"
      phase: "Phase 4"
      verification_status: "codigo pronto; portao de campo ABERTO"
      evidence: >
        O modo sobe como terceira invocacao e foi exercitado hoje, mas por ~40s de
        painel, nao os 10 min com as DUAS partys rodando. Nenhum teste automatizado
        alcanca contencao entre processos. Revertido de Complete para Pending nesta
        auditoria (commit a041e3e) — marcar Complete seria um portao aberto virando
        fechado sem ninguem decidir isso.
  verificacao:
    - fase: "02-leitura-de-pagina"
      status: "human_needed"
      pendencia: "OCR real dentro do tick; congelamento provocado (minimizar a janela 3+ ticks)"
    - fase: "03-persistencia-de-observacoes"
      status: "human_needed"
      pendencia: "abrir o CSV e entende-lo; importar no Google Sheets; contar linhas antes/depois; ver o desligamento alto"
    - fase: "04-modo-mercado-analise-e-console"
      status: "gaps_found (DESATUALIZADO)"
      pendencia: >
        Os 4 gaps foram consertados em a0c0ecd, f0a9ad4, 1463ce7 e a041e3e, mas o
        04-VERIFICATION.md e ANTERIOR a eles e nao foi reescrito. Uma reverificacao
        nao rodou — o veredito no arquivo nao reflete a arvore.
tech_debt:
  - fase: "04"
    items:
      - "destaque_ao_vivo nao tem UM teste, e nao tem latch: agora que a linha ao vivo repinta por tick, as duas mensagens competem na tela (22 blocos medidos em 8 ticks)"
      - "A tendencia (ANAL-03) roda sobre o ordinal das ofertas. No dado real, Phantom Mask Sealed tem n=10 com apenas 3 carimbos distintos — 7 ofertas de UMA leitura. Como a grade do jogo vem ordenada por preco, a regressao mede a escada de precos de uma tela, nao movimento no tempo. Saiu +10,6%. DECISAO DO USUARIO PENDENTE."
      - "O criterio 'o exemplo comentado de [[receita]] parseia quando descomentado' foi especificado como COMANDO, nao como teste: nada guarda isso daqui pra frente"
  - fase: "geral"
    items:
      - "Um layout so e lido (aba Equipment, chamada 'negociacao'). Adena/Enhancement/Product List/Characters sao recusadas de proposito. O usuario pediu as outras abas em 2026-08-31 — escopo de proximo milestone."
      - "A fusao B-grade Gemstone x C-grade Gemstone (similaridade 0,9375, letra de grade) segue aberta desde a Fase 2: viram uma serie so"
      - "milestone_name aparece como ')' no init e no STATE.md — defeito de parse pre-existente, cosmetico"
---

# Auditoria do milestone v1-mercado

## Veredito: `gaps_found` — e nenhum dos gaps e codigo quebrado

Os 18 requisitos estao implementados. O que impede o `passed` sao **portoes humanos
abertos** e **um veredito de fase desatualizado** — nao defeito de software.

## O que esta PROVADO

**Os quatro fios estao ligados, e chamados.** Verificado por AST sobre
`l2scanner/mercado_modo.py`: dos nomes importados das Fases 2, 3 e 4, **nenhum fica
sem ponto de chamada**. `LeitorDePagina`, `ModeloDeMercado`, `linha_ao_vivo`,
`destaque_ao_vivo`, `secao_do_vale_quanto`, `secao_da_margem` e `resumo_da_sessao`
sao todos invocados, nao apenas importados.

Isso importa mais que o normal neste projeto: **oito vezes neste milestone um
mecanismo foi instalado e nunca chamado**, com a suite verde porque o estado
degenerado era indistinguivel do valido. A Fase 4 existia justamente para ser o
chamador que faltava, e ela e.

**O fluxo ponta a ponta rodou em producao hoje**, com o jogo aberto: 31 paginas
lidas, 12 perdidas, 39 de outro layout recusadas, 36 observacoes gravadas, 274
duplicadas descartadas, 8 series, 0 frames congelados, 0 de 106 ticks estourando o
orcamento de 1s (p50 16 ms, p95 172 ms).

**Suite verde num snapshot congelado: 3201 passed, 23 skipped, zero falhas.**

## O que ficou ABERTO

Tres portoes humanos, nenhum alcancavel por teste, todos do usuario:

1. **DETC-02** — as duas partys mais o `--mercado` por 10 min, conferindo CPU no
   Gerenciador de Tarefas. E o unico requisito nao-Complete.
2. **Fase 2** — OCR real dentro do tick (parcialmente exercitado hoje) e o
   congelamento provocado.
3. **Fase 3** — importar o CSV no Sheets e conferir a contagem.

## Uma decisao de produto pendente

A tendencia do ANAL-03 esta medindo a escada de precos de **uma tela**, nao
movimento no tempo — porque 7 das 10 observacoes de uma serie vieram de uma unica
leitura, e a grade do jogo ja vem ordenada por preco. O numero calculado e
verdadeiro; o **nome** dele e que promete outra coisa. Aguarda o usuario.

## NAO limpar worktrees

`worktree-agent-ad4547ac54a9fd3fe` guarda **3 commits `discord-01` de outro agente**
que nao estao em lugar nenhum. `worktree.cleanup-wave` os apagaria.
