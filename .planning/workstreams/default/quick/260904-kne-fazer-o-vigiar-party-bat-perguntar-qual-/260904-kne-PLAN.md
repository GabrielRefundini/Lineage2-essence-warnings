---
phase: default
plan: 260904-kne
type: quick
autonomous: true
---

# Plan: vigiar-party.bat pergunta qual char vigiar (uma escolha, v1)

## Objective

Com duas janelas do XM Essence abertas (Faerlina e Yazalaque), o
`vigiar-party.bat` hoje sempre roda `--janela` sem valor. Se a calibracao
tiver `janela` gravada, ele usa esse titulo SEMPRE, mesmo que o usuario tenha
aberto outro char nesta sessao — pegando o char errado sem avisar. Sem
`janela` gravada e com duas ou mais janelas abertas, `escolher_janela_do_jogo`
recusa e sai (codigo 2), sem oferecer escolha nenhuma no clique duplo.

Esta v1 faz o `.bat` perguntar qual das janelas abertas vigiar SOMENTE no
clique duplo (sem argumento nenhum) e SOMENTE quando ha duas ou mais janelas.
Zero ou uma janela continuam sem pergunta. Escolha UNICA — nao ha opcao de
vigiar as duas ao mesmo tempo nesta versao.

## Context

- `l2scanner/captura_janela.py` ja tem `listar_janelas_do_jogo()`.
- `l2scanner/__main__.py` ja tem `--janela` (`nargs="?"`, `const="AUTO"`).
- Precedente no mesmo projeto: `calibrar.bat` foi corrigido para "quem passa
  argumento na linha de comando NAO e perguntado de novo" — mesmo principio
  aplicado aqui.
- Um `python -c "..."` inline dentro do `.bat` quebra por causa do conflito
  de aspas simples/duplas com `for /f ('comando')`. Por isso a flag nova
  `--listar-janelas`.

## Tasks

### Task 1: `--listar-janelas` no `__main__.py` (TDD)

<task type="auto" tdd="true">
<files>l2scanner/__main__.py, tests/test_listar_janelas_flag.py</files>
<behavior>
Uma flag `--listar-janelas` que imprime cada titulo de
`listar_janelas_do_jogo()` em uma linha, sem prefixo nem numeracao, sai com
codigo 0 mesmo com lista vazia, nao abre calibracao nem log, e sai ANTES de
qualquer outro caminho do `main()`.
</behavior>
<action>
Adicionar `parser.add_argument("--listar-janelas", action="store_true",
dest="listar_janelas", ...)` e checar `args.listar_janelas` logo apos
`parser.parse_args()`, antes de qualquer outra validacao ou `configurar_log`.
</action>
<verify>python -m pytest tests/test_listar_janelas_flag.py -q</verify>
<done>4 testes verdes; RED confirmado antes com o mesmo arquivo.</done>
</task>
