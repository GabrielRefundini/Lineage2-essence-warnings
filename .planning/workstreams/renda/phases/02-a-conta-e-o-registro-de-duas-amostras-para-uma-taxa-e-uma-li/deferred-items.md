# Itens adiados — Fase 02 (workstream `renda`)

Descobertas fora do escopo dos planos desta fase. **Nenhuma delas foi consertada
aqui**, pela regra de fronteira do executor: so se auto-conserta o que a mudanca
da propria tarefa causou.

---

## D-1 — A suite tem uma BOMBA-RELOGIO de calendario, e ela disparou em 2026-09-03

**Descoberto durante:** `02-02`, Tarefa 2, ao rodar a suite inteira depois da
virada da meia-noite.

**O que acontece.** `l2scanner/agenda.py:1004` faz `hoje = hoje or date.today()`.
Tres arquivos de teste ancoram fixtures em `datetime(2026, 8, 30, ...)` e passam
por esse caminho sem injetar `hoje`. Enquanto o relogio da maquina esteve em
2026-09-02 eles passaram; as 00h de 2026-09-03 comecaram a falhar, e o numero de
falhas **cresce com o tempo de parede** (15 numa rodada, 16 na seguinte).

**Arquivos afetados** (todos FORA dos `files_modified` de qualquer plano desta
fase):

- `tests/test_sessao.py` — 6 testes
- `tests/test_janela_no_relogio.py` — 7 testes
- `tests/test_respawn.py` — 2 testes

**Prova de que e PRE-EXISTENTE e nao consequencia do `02-02`.** O commit base da
onda 2 (`9b90572`, antes de qualquer linha desta tarefa) foi extraido para uma
arvore limpa com `git archive` e a suite rodou la, no mesmo instante:

| Arvore | `passed` | `failed` |
|---|---|---|
| base `9b90572`, limpa | 5492 | 16 |
| `02-02` | 5547 | 15 |

O conjunto de testes falhando e **o mesmo nos dois**, e `5547 - 5492 = 55` e
exatamente o numero de testes novos do `02-02`. Nenhum modulo de `l2scanner/`
importa `renda_conta` (conferido por varredura), entao nao ha caminho por onde
esta tarefa pudesse alcancar `sessao.py`, `agenda.py` ou `respawn`.

**Por que `tests/test_agenda.py` ja estava desselecionado.** Ele e o irmao mais
obvio da mesma familia, e o `02-01` ja rodava a suite com
`--ignore=tests/test_agenda.py`. O que 2026-09-03 mostrou e que a dependencia de
`date.today()` vazou para mais tres arquivos que ninguem tinha marcado.

**O conserto certo, e ele NAO e desselecionar mais arquivos.** E injetar `hoje`
por parametro nesses testes — o mesmo idioma que o resto da arvore ja usa para o
relogio (`relogio.py`, `Maquina`, carimbo por parametro). Uma suite que so passa
em certos dias do calendario e uma suite que nao mede o que afirma medir.

**Dono:** ninguem desta fase. E do workstream que possui `agenda.py` /
`sessao.py`.

---

## D-2 — A guarda de SALTO DE ORDEM DE GRANDEZA DA ADENA nao roda quando o nivel recusa

**Descoberto durante:** `02-02`, Tarefa 1, ao escrever `passo_entre_campos`.

**O que acontece.** As quatro regras de par exigem `LeituraDaRenda`, que exige os
TRES campos inteiros. Com o nivel recusado esse objeto nao existe, entao
`conferir_o_par` nao pode ser chamada — e junto com ela deixa de rodar
`a_adena_saltou_ordem_de_grandeza`, que sozinha **so precisa da adena**. Com o
nivel recusado em 79% dos tiques (`02-CONTEXT.md:150`), e a maioria dos passos.

**Por que nao foi consertado aqui.** As duas saidas obvias estao fechadas de
proposito:

1. Chamar `a_adena_saltou_ordem_de_grandeza` solta de `renda_conta.py` derruba o
   portao invertido de `tests/test_renda_par.py`, que exige que producao chame a
   COMPOSICAO e nunca uma das tres irmas. E o portao esta certo: duas portas de
   entrada para as regras sao duas politicas de recusa divergindo no dia em que
   uma delas mudar.
2. Fabricar um nivel para completar a `LeituraDaRenda` e exatamente o tipo de
   invencao que a CTX-5 proibe.

**O conserto certo.** Uma composicao em `renda_leitura.py` que aceite o par
PARCIAL — "as regras que dao para conferir com os campos que chegaram" — e que
passe a ser a chamada por `passo_entre_campos`. E trabalho de quem for dono
daquele modulo; o `02-02` nao o toca, e a limitacao esta escrita na docstring de
`passo_entre_campos`.

**Dono:** um plano futuro sobre `l2scanner/renda_leitura.py`.
