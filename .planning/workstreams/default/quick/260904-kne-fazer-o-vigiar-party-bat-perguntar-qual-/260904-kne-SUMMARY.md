---
phase: default
plan: 260904-kne
subsystem: cli+launcher
tags: [janela, vigiar-party.bat, cli, tdd]
requires: []
provides: [--listar-janelas, escolha-de-janela-no-vigiar-party.bat]
affects: [l2scanner/__main__.py, vigiar-party.bat]
tech-stack:
  added: []
  patterns: ["sub-rotina .bat com endlocal & set para devolver valor ao chamador"]
key-files:
  created:
    - tests/test_listar_janelas_flag.py
    - tests/test_vigiar_party_bat.py
  modified:
    - l2scanner/__main__.py
    - vigiar-party.bat
decisions:
  - "Numero invalido ou vazio no prompt do .bat pede de novo (sem default silencioso) -- silencio escolheria por conta propria e o usuario ja reclamou de pegar o char errado sem aviso."
  - "--listar-janelas sai ANTES de configurar_log e de qualquer calibracao, para o stdout ficar puro o bastante para um for /f do cmd ler."
metrics:
  duration: "~35min"
  completed: 2026-09-04
status: complete
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
---

# Phase default Plan 260904-kne: vigiar-party.bat pergunta qual char vigiar Summary

Com Faerlina e Yazalaque abertas ao mesmo tempo, `vigiar-party.bat` agora
pergunta qual das duas vigiar no clique duplo, usando a nova flag pura
`--listar-janelas` em vez de um `python -c` inline que quebraria pelo
conflito de aspas do `for /f` do cmd.

## O que foi entregue

1. **`--listar-janelas`** em `l2scanner/__main__.py`: imprime cada titulo de
   `listar_janelas_do_jogo()` em uma linha, sem prefixo nem numeracao, sai
   com codigo 0 mesmo com lista vazia. Sai ANTES de `configurar_log` e de
   qualquer calibracao — stdout limpo o bastante para o `.bat` ler com
   `for /f`.
2. **`vigiar-party.bat`**: no clique duplo (sem argumento nenhum), conta as
   janelas do XM Essence abertas via `--listar-janelas`:
   - 0 janelas: nao pergunta, cai no `--janela` sem valor de sempre — o
     proprio scanner explica que nao achou nada.
   - 1 janela: nao pergunta, passa o titulo direto (`--janela "<titulo>"`).
   - 2+ janelas: mostra um menu numerado e pergunta qual vigiar. Numero
     vazio ou fora da faixa pede de novo.
   - Quem chama o `.bat` com QUALQUER argumento (`%~1` nao vazio) nunca e
     perguntado — mesmo principio ja corrigido no `calibrar.bat`.
   - Escolha UNICA nesta v1: nunca vigiar as duas janelas ao mesmo tempo.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — convencao do proprio arquivo] 3 travessoes (em-dash, nao-ASCII)
tirados do cabecalho de `vigiar-party.bat`**
- **Encontrado durante:** escrita do teste `test_o_bat_e_ascii_puro` (novo,
  seguindo o mesmo guarda que ja existe em `test_vigiar_mercado_bat.py`).
- **Motivo:** o arquivo ja tinha 3 ocorrencias de `—` (U+2014) herdadas de
  antes desta tarefa — texto para o console cp1252 do usuario, que vira lixo
  visual com acento/travessao. A regra dura do proprio pedido ("Portugues
  SEM acento... no proprio .bat") e o mesmo arquivo que este plano ja edita
  extensamente para o mesmo motivo (texto seguro no cmd).
- **Fix:** troca por hifen simples `-`, sem mudar sentido nenhum.
- **Arquivos:** `vigiar-party.bat`
- **Commit:** 1a2db1c

Fora isso: plano executado exatamente como escrito.

## Known Stubs

Nenhum.

## Self-Check: PASSED

- `l2scanner/__main__.py` — FOUND
- `vigiar-party.bat` — FOUND
- `tests/test_listar_janelas_flag.py` — FOUND
- `tests/test_vigiar_party_bat.py` — FOUND
- commit f32612a — FOUND (`git log --oneline --all`)
- commit 1a2db1c — FOUND (`git log --oneline --all`)
