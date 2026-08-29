---
phase: 01-funda-o-firewall-gravador-e-spike-de-campo
plan: 05
subsystem: calibracao-do-mercado
tags: [glifos, ocr-por-template, calibracao, gap-closure, FUND-03]
status: checkpoint
gap_closure: true
closes_gap: G-01
requires:
  - phase: 01-04
    provides: "calibrar_mercado.py, o par ancoras_para/de_calibracao, molde_para/de_hex, ResultadoDaConfusao"
  - phase: 01-03
    provides: "SPIKE-RESPOSTAS.md validado — a virgula como separador de milhar E decimal, e o sufixo como desambiguador"
provides:
  - "l2scanner/calibrar_mercado.segmentar_glifos: segmentacao por projecao de coluna sobre a mascara de brilho, com a faixa de linhas COMPARTILHADA na assinatura"
  - "l2scanner/calibrar_mercado.matriz_de_confusao_de_glifos: matriz propria, mascara binaria, alinhamento por PREENCHIMENTO, par incalculavel contado a parte"
  - "l2scanner/calibrar_mercado.COLISAO_MAXIMA_ENTRE_GLIFOS: constante SEPARADA da de templates, com as tres convencoes medidas na docstring"
  - "l2scanner/calibrar_mercado.cortar_glifos: o laco interativo com conferencia de CONTAGEM contra o rotulo digitado"
  - "l2scanner/calibrar_mercado.fundir_glifos: fusao por rotulo (CR-04) — o corte novo vence, o ausente e preservado"
  - "l2scanner/calibrar_mercado.VALOR_MINIMO_DO_SUFIXO + recortar_sufixo: piso de brilho PROPRIO das palavras de sufixo, medido"
  - "l2scanner/calibrar_mercado --so-digitos: corte isolado sobre outro frame, sem refazer ancoras e grade"
  - "l2scanner/mercado_visao.glifos_para/de_calibracao: empacotamento com guard de CONJUNTO (altura dominante dos glifos de um caractere)"
  - "l2scanner/calibracao.mercado_limiar_de_glifo: chave opcional via .get, faixa (0,1]; VERSAO_DO_ESQUEMA segue 2"
  - "tests/fixtures/mercado/glifos_precos_f010.png + glifos_unitario_f010.png: os onze glifos reais, commitados"
affects: [fase 2 LEIT-02 leitura de precos por template-por-digito]
tech-stack:
  added: []
  patterns:
    - "conjunto fechado + correlacao de posicao unica (identidade.py), aplicado glifo a glifo"
    - "convencao de recorte DECLARADA na assinatura, para o numero de matriz ser reproduzivel"
    - "incalculabilidade por PRE-CONDICOES re-checadas, nunca por comparacao do score a 0.0"
key-files:
  created:
    - tests/test_mercado_glifos.py
    - tests/fixtures/mercado/glifos_precos_f010.png
    - tests/fixtures/mercado/glifos_unitario_f010.png
  modified:
    - l2scanner/calibrar_mercado.py
    - l2scanner/mercado_visao.py
    - l2scanner/calibracao.py
    - calibrar-mercado.bat
    - tests/test_calibrar_mercado.py
    - .planning/workstreams/mercado/phases/01-funda-o-firewall-gravador-e-spike-de-campo/01-04-SUMMARY.md
decisions:
  - "A representacao dos moldes de glifo e a MASCARA BINARIA, nao o cinza: ela vence nas TRES convencoes de recorte medidas, por 0.10 a 0.13"
  - "O alinhamento da matriz dos glifos e por PREENCHIMENTO ate a maior caixa, nao por corte ao menor: cortar compara a virgula de 1 px contra a primeira coluna do digito (0.1918 contra 0.5000, medido)"
  - "As palavras de sufixo tem piso de brilho PROPRIO (V>120) — elas ficam INTEIRAS abaixo do piso de 180 dos digitos, com V maximo 173"
  - "O guard de altura do conjunto para nos glifos de UM caractere: a palavra sai com 8 px e o digito com 9, e exigir igualdade recusaria a calibracao correta"
  - "Duas matrizes de confusao, uma por confusao ALCANCAVEL: entre digitos e entre as duas palavras. Digito contra palavra nao e alcancavel"
metrics:
  duration: "~1h"
  completed: 2026-08-28
  tasks_completed: 2
  tasks_total: 3
actuals:
  tokens: 61000
  tasks: 2
  commits: 5
---

# Phase 01 Plano 05: Produtor dos Templates de Digito — Summary

Corte de glifos por projecao de coluna com convenção de recorte declarada, matriz de
confusão própria que recusa colisão e par incalculável, e o modo `--so-digitos` — dando
a `mercado_templates_de_digito` o produtor que nunca teve.

## ESTADO: AGUARDANDO O PORTÃO HUMANO (Task 3)

| Task | O que é | Estado |
|---|---|---|
| 1 | Segmentação, matriz dos glifos, par de empacotamento, fixtures resgatadas | **COMPLETA**, commits `d3dbcc2` (RED) + `f33883c` (GREEN) |
| — | Correção: piso de brilho próprio do sufixo (desvio medido, ver abaixo) | **COMPLETA**, commit `8608229` |
| 2 | Laço de corte, fusão, chave do limiar, `--so-digitos`, `.bat`, SUMMARY do 01-04 | **COMPLETA**, commits `710eca6` (RED) + `59fc6e8` (GREEN) |
| 3 | `checkpoint:human-action` `gate="blocking-human"` — a primeira mão humana no fluxo | **AGUARDANDO O USUÁRIO** |

## A MATRIZ DE CONFUSÃO MEDIDA — com a convenção ao lado do número

**Convenção de recorte: LINHA-JUSTA COMPARTILHADA.** Uma única faixa de linhas por
retângulo marcado (`flatnonzero(mascara.any(axis=1))`, do primeiro ao último inclusive),
com cada glifo cortado nessa mesma faixa e nos seus próprios limites de coluna. Um número
de matriz sem a convenção ao lado não é reproduzível — foi exatamente assim que a primeira
versão deste plano errou.

Sobre os **11 glifos reais** (`0`-`9` e a vírgula) montados das duas fixtures commitadas,
55 pares:

| representação | pior par inter-classe | 2º pior | 3º pior | margem até 1.0 |
|---|---|---|---|---|
| tons de cinza nativo | **0.8434** (`0` x `8`) | 0.8101 (`5` x `6`) | 0.7797 (`3` x `8`) | 0.1566 |
| **máscara binária (V>180)** | **0.7171** (`5` x `6`) | 0.6952 (`0` x `8`) | 0.6549 (`3` x `5`) | 0.2829 |

**Diferença máscara↔cinza: 0.1263** — acima do piso de 0.08 que o critério exige. Todos os
números do plano reproduziram exatamente, incluindo o mínimo negativo do cinza (−0.1849),
que é a prova extra de que `0.0` não é piso e portanto não serve de sentinela.

**Os quatro zeros legítimos estão lá, e são MEDIÇÃO:** `(',','0')`, `(',','6')`, `(',','9')`
e `('0','7')` medem exatamente `0.0` na máscara, com desvios de 70.478 / 120.208 / 110.418 —
cinco ordens de grandeza acima do piso de `1e-6`. Nenhum é contado como não-mensurável, e o
conjunto real **APROVA**. Em tons de cinza não há zero nenhum: os quatro são fenômeno da
máscara. `,` x `2` mede **0.1918** com preenchimento contra **0.5000** com corte ao menor —
a regressão que o critério `< 0.30` existe para impedir.

**Geometria, idêntica ao medido:** faixa de **9 px** nas SETE marcações; dígitos de 4 px,
o `4` em 6 px, a vírgula em 1 px. Segmentação: **6, 4, 5, 4, 5, 4** e **4** — 7 de 7.

## O DESVIO QUE A EXECUÇÃO ENCONTROU (Rule 1)

**As palavras de sufixo não podiam ser cortadas com a máscara dos dígitos.** O plano
assumia que sim. Medido no `frame_000010`, na coluna à direita do preço:

| recorte | V máximo | V p99 | pixels com V>180 |
|---|---|---|---|
| preços (coluna Total) | 255 | 219 | 274 |
| `XM Coin` (ao lado) | **173** | 148 | **0** |

A palavra fica **inteira** abaixo do piso de 180 de `identidade.mascara_de_texto` — com o
piso dos dígitos, a máscara dela sai **vazia**, e um molde vazio não casa com nada. Marcar
a palavra teria produzido um molde nulo, descoberto só no fim de toda a marcação de mouse —
exatamente o modo de falha que este projeto vem matando.

`VALOR_MINIMO_DO_SUFIXO = 120` fica no meio de um platô largo e medido: qualquer piso entre
100 e 140 devolve a **mesma** faixa de 8 px e largura 35–36 px, idêntica nas seis linhas, e
o fundo não invade em nenhum deles (0 pixel de fundo acima do piso, em 4500 px de área sem
texto). Não há zona cinzenta a dividir: há um vale vazio.

**Consequência no guard de altura**, e é uma correção do meu próprio trabalho da Task 1: a
palavra sai com **8 px** e o dígito com **9 px**. Exigir a mesma altura dos dois grupos
**recusaria uma calibração correta** — o pior desfecho que um guard pode ter. O guard passa
a afirmar só onde tem evidência: os glifos de **um caractere**, que são também o conjunto de
onde um preço é lido. Um dígito transposto segue recusado, com teste
(`test_mas_um_DIGITO_de_altura_divergente_segue_recusado`).

Isto também motivou **duas matrizes** em vez de uma, pelas duas confusões realmente
alcançáveis: entre dígitos (troca o preço) e entre as duas palavras (inverte a convenção da
vírgula). Dígito contra palavra não é alcançável — moram em colunas diferentes e o leitor
sabe qual está lendo; e o alinhamento por preenchimento poria um dígito de 4 px dentro de
uma caixa de 35 px, medindo a área vazia em vez do desenho.

**Segundo desvio, menor:** `cortar_glifos` tinha `ler=input` como valor padrão, que amarra o
`input` existente no momento do import e ignora calado quem o substitua depois. Resolvido em
tempo de chamada.

## OS ARQUIVOS RESGATADOS

| arquivo | forma | bytes | conteúdo |
|---|---|---|---|
| `tests/fixtures/mercado/glifos_precos_f010.png` | (240, 45, 3) | 5.354 | `100,00`, `3,00`, `18,90`, `7,50`, `18,00`, `2,45` |
| `tests/fixtures/mercado/glifos_unitario_f010.png` | (30, 40, 3) | 769 | `6,00` |

Somam 5.354 + 769 = **6.123 bytes**, abaixo do teto de 8 KB. Conferidos com o olho
antes do commit: **só dígitos** — nenhum nome de personagem, nenhuma linha de chat, nenhum
nome de item. Recortados por script descartável, fora do repositório: os dois módulos de
calibração têm tripwire estrutural contando escrita de imagem no fonte, e ambos seguem em
**zero** ocorrências.

## GLIFOS GRAVADOS / FALTANTES

Nenhum glifo foi gravado em `calibration.json` por esta execução — **isso é o portão da
Task 3**, e gravar sem a mão humana seria simular o critério que o plano existe para
cumprir. Os onze glifos estão provados contra os pixels reais nas fixtures; o que falta é o
usuário produzi-los na máquina dele, mais as duas palavras de sufixo.

## VERIFICAÇÃO

- `python -m pytest tests/ -q` → **1638 passed, 8 skipped**, contra a linha de base de
  **1552 passed, 8 skipped** neste worktree (1558/2 no checkout principal — mesmo total de
  1560; os 6 skips a mais são os testes que dependem de `recordings/`, ausente no worktree).
  **Zero regressões.** O flake conhecido do `tests/test_agenda.py` apareceu uma vez e passou
  na re-execução, como previsto.
- `tests/test_mercado_glifos.py` → 47 passed. `tests/test_calibrar_mercado.py` → 110 passed.
- Os dois tripwires de escrita de imagem seguem verdes; `grep -c imwrite
  l2scanner/calibrar_mercado.py` → **0**.
- `git diff --stat` **não** toca `rastreador.py`, `visao.py` nem `sessao.py`;
  `grep -ic mercado l2scanner/rastreador.py` → **0**.
- `VERSAO_DO_ESQUEMA = 2`; `calibration.json` segue gitignored e não foi tocado.
- Nenhuma dependência nova — FIRE-01 intacto.

## Deviations from Plan

**1. [Rule 1 - Bug] Palavras de sufixo abaixo do piso de brilho dos dígitos**
- **Encontrado durante:** Task 2, ao desenhar o caminho de marcação das palavras
- **Problema:** o plano assumia a máscara dos dígitos para as palavras; medido, `XM Coin`
  tem V máximo 173 e **zero** pixels acima do piso de 180. O molde sairia vazio.
- **Correção:** `VALOR_MINIMO_DO_SUFIXO = 120` + `recortar_sufixo`, com o platô medido; e o
  guard de altura do conjunto escopado aos glifos de um caractere, para não recusar a
  calibração correta.
- **Arquivos:** `l2scanner/calibrar_mercado.py`, `l2scanner/mercado_visao.py`,
  `tests/test_mercado_glifos.py`
- **Commit:** `8608229`

**2. [Rule 1 - Bug] `ler=input` como valor padrão amarrava o `input` do import**
- **Encontrado durante:** Task 2. Resolvido em tempo de chamada. Commit `59fc6e8`.

**3. [Rule 3 - Bloqueio] Testes existentes do fluxo completo passaram a ler do stdin**
- O fluxo completo ganhou um passo (o corte de glifos), então quatro cenários existentes
  precisaram responder "terminar". Comportamento anterior preservado. Commit `59fc6e8`.

## Known Stubs

Nenhum. Todo caminho novo tem implementação real e teste.

## Threat Flags

Nenhuma superfície nova além da já registrada no `<threat_model>` do plano. Zero
dependências novas; nenhuma escrita de imagem própria; `calibration.json` segue como a única
saída, gravada pelo caminho atômico já existente.

## Self-Check: PASSED

Arquivos afirmados, conferidos no disco: `tests/test_mercado_glifos.py` (27.679 B),
`tests/fixtures/mercado/glifos_precos_f010.png` (5.354 B),
`tests/fixtures/mercado/glifos_unitario_f010.png` (769 B), `calibrar-mercado.bat` (4.112 B),
`l2scanner/calibrar_mercado.py`, `l2scanner/mercado_visao.py`, `l2scanner/calibracao.py`.

Commits afirmados, conferidos no `git log`: `d3dbcc2`, `f33883c`, `8608229`, `710eca6`,
`59fc6e8` — todos presentes, na ordem citada.
