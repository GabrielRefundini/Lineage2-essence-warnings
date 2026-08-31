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

## Fase 1 entregue (2026-08-31)

O acervo `.identidades/` existe, e lido no arranque, sobrevive ao
`calibrar.bat` e nao e podado. Uma entrada SEM nome e reconhecida e continua
calada.

### O defeito ATIVO que a fase destapou e consertou

`Rastreador.assinaturas_configuradas` tinha default `False` e era atribuido em
OITO lugares, TODOS em `tests/test_identidade.py`. O unico construtor de
producao nao passava. Os tres portoes que SAO o silencio `#linhaN` estavam
desligados em campo:

  - `_e_so_uma_posicao`  -> o portao de MORREU / RESSUSCITOU
  - `_rotular`           -> `Membro N` em vez do nome por posicao
  - a purga de chave posicional

Ou seja: uma linha nao reconhecida pegava `nomes[indice]` e anunciava a morte
com o nome de quem estivesse naquela posicao da lista. E a mentira plausivel
que o modulo existe para impedir, e ela estava viva desde que a identidade por
imagem foi escrita. A suite provava que a logica funcionava; NADA provava que
ela estava ligada.

O conserto nao foi a linha que faltava: foi um portao de AST que afirma que
TODA chamada `Rastreador(...)` em `l2scanner/` decide explicitamente sobre a
flag. Esquecer virou nao-mesclavel. Quem quiser um rastreador mudo tem de
digitar `False`, e ai a escolha aparece no diff.

### Numeros medidos

  - assinatura serializada: 562 bytes (mil membros ~= 550 KB)
  - chamadas `Rastreador(...)` em `l2scanner/`: exatamente UMA, e era a muda
  - faixa perigosa do quase-duplicado: 12 bits virados numa mascara de 2000
    celulas ja fazem a pessoa parar de ser reconhecida. E o numero que a
    Fase 2 precisa para APRE-04.
  - suite: 3197 passando, zero falha
