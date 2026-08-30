---
workstream: tiat
created: 2026-08-29
---

# Project State

## Project Reference

**Core Value:** A party fica sabendo no WhatsApp que o Tiat nasceu, em
segundos, sem ninguem estar olhando a tela — e sabe com antecedencia quando a
proxima janela de respawn abre.

**Current Focus:** Fase 1 — reconhecimento preciso (a frase inteira do anuncio
do servidor, e QUAL boss) e lista de bosses no `config.toml`.

**Ponto de partida:** `l2scanner/tiat.py` ja existe, ja esta ligado em
`sessao._processar_tiat` e tem 7 testes. O encanamento ate o WhatsApp esta
inteiro; falta a PRECISAO e a PREVISAO.

## Current Position

**Status:** Roadmap criado, aguardando planejamento da Fase 1
**Current Phase:** 1 — Reconhecimento preciso e lista de bosses no config
**Last Activity:** 2026-08-30
**Last Activity Description:** ROADMAP.md criado — 2 fases, 18/18 requisitos mapeados

## Progress

**Phases Complete:** 0 / 2
**Current Plan:** N/A

```
Fase 1  [          ]  0%   Reconhecimento preciso e lista de bosses
Fase 2  [          ]  0%   Janela de respawn
```

## Accumulated Context

### Decisoes travadas (do usuario, anteriores ao roadmap)

- **D-01** O gatilho exige a frase completa do anuncio do servidor
  (`<Nome> [Lv. NN] has spawned!`), nao a mera presenca do nome. Requerer a
  frase captura North/South de graca.
- **D-02** A lista de bosses vigiados mora no `config.toml`, no molde dos
  `[[evento]]`. Mob novo e bloco novo, nunca edicao de codigo. Tiat: 6h e 8h.
- **D-03** A janela e ancorada no NASCIMENTO, nao na morte. O usuario rejeitou
  `/morreu` e rejeitou detectar a morte pela tela. O erro e conhecido e
  aceito; a mensagem tem que ser honesta sobre ele (JANE-03).
- **D-04** Dois avisos: quando a janela ABRE (min) e quando o limite passa
  (max).
- **D-05** Os avisos de janela funcionam com o jogo FECHADO, pelo relogio,
  como a agenda de TvT.

### Decisoes do roadmap

- **D-06** A ancora mora em `.agenda/`, com prefixo novo, e NAO em `.loot/`.
  `.agenda/` poda em 3 dias; a ancora vale no maximo 8h. Uma ancora imortal
  em `.loot/` produziria janelas erradas com cara de certas. Ver a secao
  "Onde o historico de spawn mora em disco" no ROADMAP.md.
- **D-07** A precisao (RECO+VIGI) vem ANTES da janela (JANE) por correcao, nao
  por gosto: ancorar uma contagem de 6h num falso positivo de chat digitado e
  pior do que nao ter previsao nenhuma.
- **D-08** JANE-04 (reancorar) e ESTRUTURAL, sem marcador de cancelamento: o
  calculo so olha a ancora mais recente por boss, entao as chaves do ciclo
  anterior deixam de vencer sozinhas.

### Contas que o planejamento nao pode pular

- **A direcao do erro da janela e sempre a mesma.** Boss nasce em `T`, morre em
  `T+k`, renasce em `[T+k+min, T+k+max]`. Ancorados em `T`, os dois avisos saem
  `k` CEDO demais, nunca tarde. Logo o aviso de `max` NAO PODE afirmar que a
  janela fechou — em `T+max` ela pode nem ter aberto. "Perdemos a janela" e
  falso.

### Riscos abertos

- **R-01** A frase `<Nome> [Lv. NN] has spawned!` e asserção do usuario, nunca
  capturada por este projeto. Confrontar com gravacao real na Fase 1.
- **R-02** Gate estrito demais na parte fixa da frase troca o falso positivo de
  hoje por um falso NEGATIVO silencioso, que e pior.
- **R-03** O guarda de `_PREFIXOS_CONHECIDOS` varre `vars(agenda)` — um
  prefixo declarado em modulo novo passa por ele sem levantar nada.
- **R-04** Dois lugares de fiacao para JANE-05: `laco_da_agenda` e
  `laco_principal`. Consertar so um faz os dois divergirem.

## Session Continuity

**Stopped At:** ROADMAP.md escrito e traceability preenchida
**Resume File:** `.planning/workstreams/tiat/ROADMAP.md`
**Next:** planejar a Fase 1
