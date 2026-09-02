---
gsd_state_version: 1.0
milestone: v1-renda
milestone_name: Quanto rende esta hora
workstream: renda
created: 2026-09-02
current_phase: 01
current_phase_name: A leitura da barra
current_plan: null
status: planning
stopped_at: Roadmap criado, aguardando planejamento da Fase 1
last_updated: "2026-09-02T04:00:00.000Z"
last_activity: 2026-09-02
last_activity_desc: Roadmap de v1-renda criado — 3 fases, 18 requisitos mapeados
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

**Core value do workstream:** responder, ao vivo e sem tabela externa, "quanto rende esta hora
de farm" e "quanto tempo falta para o próximo nível" — lendo a **barra inferior** do cliente,
que já exibe EXP%, adena total e nível permanentemente e sem rolagem.

**A decisão de desenho que define tudo:** ler a barra é uma **diferença entre duas amostras**;
ler o chat seria uma **soma de eventos**. Numa soma, toda linha perdida é renda perdida para
sempre. Numa diferença, nenhuma amostra perdida corrompe o total — porque o total está na tela,
não na soma. Medido no spike, não suposto.

**Foco atual:** Fase 1 — transformar pixel em número, ou recusar.

## Current Position

**Status:** Planning
**Fase atual:** 01 — A leitura da barra (pixel vira número, ou recusa)
**Plano atual:** —
**Última atividade:** 2026-09-02 — Roadmap criado

## Progress

**Fases completas:** 0 de 3
**Planos completos:** 0
**Requisitos mapeados:** 18 de 18

| Fase | Requisitos | Estado |
|------|-----------|--------|
| 1. A leitura da barra | LEIT-01..06 | Not started |
| 2. A conta e o registro | REND-01..06, REG-01..04 | Not started |
| 3. O modo `--renda` | CONS-01..02, CEGO-01..02 | Not started |

## Accumulated Context

### Decisions

- **A fonte é a barra inferior, não o chat.** O usuário pediu o chat e ele mesmo levantou a
  ressalva ("eles sobem bem rápido"). O spike, feito na tela dele em 2026-09-01, achou fonte
  melhor: `EXP 68,5632%` + adena total + nível, permanentes, em texto branco de alto contraste.
  O chat volta em v2 como **enriquecimento** (XP absoluto, CHAT-01), nunca como fonte primária.

- **Três fases, não as quatro que os requisitos sugeriram.** Registro (`REG-*`) foi fundido com a
  conta (`REND-*`). Dois motivos: REND-04 é um requisito sobre o **registro** ("uma queda no
  contador é um gasto, registrado como tal") que estava morando na fase da conta, e decidir o
  esquema do arquivo duas vezes com um consumidor externo já apontado para ele é caro; e REG-02
  ("a primeira amostra depois de subir é âncora, não delta") é uma regra de **taxa** vestida de
  persistência, que não dá para verificar sem a conta. A granularidade do projeto é `coarse`.

- **REG-04 foi acrescentado pelo roadmap** — o registro tem que dizer de qual personagem é a
  renda. O usuário roda **duas instâncias** lado a lado (Yazalaque e Faerlina); sem isso o
  arquivo soma a adena de um com o EXP do outro e produz uma taxa que não descreve ninguém. É
  o mesmo modo de falha que LEIT-04 existe para impedir, e é barato: `--janela` já é exigido
  pelo `--mercado` e `cliente.nome_do_personagem` já extrai o nome do título.
  **Para revisão de manhã**, junto das quatro premissas já listadas no `REQUIREMENTS.md`.

- **"Sem um segundo parser" (REG-03) foi refutado com medição, e a refutação vai no fonte.**
  `dashboard_dados.observacoes_ao_vivo` delega para `mercado_registro.observacoes_do_arquivo`,
  que é amarrada a `COLUNAS = (chave_da_serie, nome_exibido, primeira_vez, total_em_centesimos,
  quantidade, residuo_do_cruzamento)`. Uma amostra de renda não é uma oferta de mercado. O que
  se reusa de verdade — e é bastante — é o **dialeto** (`;`, `csv` da stdlib, cabeçalho-contrato,
  append por linha) e a **disciplina de falha** (`ArquivoRecortado`, recorte na última linha
  completa). O `dashboard` acrescenta uma lista de colunas, não um parser.

- **O tempo entra por parâmetro, em tudo.** Nenhum `datetime.now()`. O PC do usuário é dual boot
  e o Windows volta do Linux ~3h adiantado; `relogio.py` já resolveu isso ancorando no cabeçalho
  `Date` do Chatwoot e avançando pelo monotônico. Para uma milestone que é inteiramente taxa por
  unidade de tempo, isto é fundação, não estilo.

- **Console primeiro, WhatsApp nunca nesta v1.** Mesma decisão que o `mercado` v1 tomou.
  ALER-01 ("avisar quando a renda cair") está reconhecido e adiado para v2.

### Todos

- Confirmar com o usuário, de manhã: REG-04 (coluna do personagem vs. arquivo por personagem)
  e a premissa "barra em vez de chat" que o `REQUIREMENTS.md` já registra.

### Blockers

- Nenhum. Nada nesta milestone depende do workstream `dashboard`, que roda em paralelo — o
  contrato entre os dois é um arquivo em disco, e este workstream não edita nenhum arquivo dele.

### Riscos abertos (herdados do roadmap)

- **O `calibration.json` é compartilhado por quatro features, e um calibrador já apagou o
  trabalho de outro** (`calibrar_mercado.py:2721` faz `cal.mercado_grade = grade`, e por isso
  calibrar a aba Adena apagaria a grade de negociação). O calibrador da Fase 1 tem que **provar**
  a não-destruição.
- **As quatro casas decimais do EXP** são a especificação mais apertada da milestone: seis
  dígitos significativos num texto de ~26 px de altura, e um erro na quarta casa vira uma taxa
  horária inteira de diferença.
- **Farm × venda no mercado não é dedutível só do contador de adena.** A escolha é do plano da
  Fase 2, mas tem que ser declarada no arquivo, não inferida por limiar mágico.
- **CEGO-02 pede staleness dos VALORES, não dos pixels.** O jogo pode renderizar normalmente com
  o EXP parado — `SaudeDoFrame` diria "saudável". Frame congelado e valor congelado são sinais
  diferentes e não podem colapsar no mesmo aviso.

## Session Continuity

**Stopped At:** Roadmap criado, aguardando planejamento da Fase 1
**Resume File:** `.planning/workstreams/renda/ROADMAP.md`
**Next:** `/gsd-plan-phase 1 --ws renda`
