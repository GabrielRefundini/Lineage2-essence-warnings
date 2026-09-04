---
phase: quick-20260904
plan: 01
subsystem: renda
tags: [renda, painel, adena, pack, REND-05, CONS-01]
status: complete
requires:
  - l2scanner/renda_conta.py::tempo_ate_o_nivel / TempoAteONivel (03-01, o molde)
  - l2scanner/renda_console.py::bloco_da_renda / _linha / _dobrar / duracao_curta
  - l2scanner/renda_laco.py::_tempo_ate_o_nivel (o molde da casca)
  - l2scanner/config.py::AjustesDaRenda / _inteiro_da_renda (02-01)
provides:
  - l2scanner/renda_conta.py::tempo_ate_o_pack / TempoAteOPack
  - "l2scanner/renda_conta.py::MOTIVO_DA_TAXA_DE_ADENA_{ZERADA,NEGATIVA}"
  - l2scanner/renda_console.py::_linhas_do_pack / _linha_dobrada
  - l2scanner/config.py::AjustesDaRenda.tamanho_do_pack_de_adena (a SEXTA chave)
  - "CLI: --pack-de-adena, que vence a chave NESTA RODADA e anuncia o vencedor"
affects:
  - l2scanner/renda_laco.py (o bloco por intervalo ganhou um parametro posicional)
  - config.toml (a secao [renda] comentada ganhou a sexta linha)
tech-stack:
  added: []
  patterns:
    - "um ETA e um numero OU um motivo, nunca infinito e nunca negativo"
    - "a tela mostra a CONTA e nao so a resposta (D-02)"
    - "duas fontes discordando: uma vence e o aviso NOMEIA o vencedor"
    - "linha de ausencia DOBRA (textwrap), nunca acolchoa"
key-files:
  created:
    - .planning/quick/20260904-eta-do-pack-de-adena/PLAN.md
    - .planning/quick/20260904-eta-do-pack-de-adena/SUMMARY.md
    - .planning/quick/20260904-eta-do-pack-de-adena/deferred-items.md
  modified:
    - l2scanner/renda_conta.py
    - l2scanner/renda_console.py
    - l2scanner/renda_laco.py
    - l2scanner/config.py
    - l2scanner/__main__.py
    - config.toml
    - tests/test_renda_conta.py
    - tests/test_renda_console.py
    - tests/test_renda_laco.py
    - tests/test_renda_no_main.py
    - tests/test_config_da_renda.py
    - .planning/workstreams/renda/STATE.md
decisions:
  - "o alvo e o proximo multiplo ESTRITAMENTE MAIOR, e nao um teto: com um pack exatamente fechado o teto daria `faltam 0` e um ETA de zero segundo"
  - "`tamanho_do_pack_de_adena` e a TERCEIRA constante de 5.000.000 da arvore, e a unica que o usuario ajusta -- as outras duas sao formato do jogo"
  - "a cerca de CINCO chaves de `[renda]` caiu para SEIS, com a razao antiga (cadencia) preservada no lugar"
  - "`--pack-de-adena` tem default `None` e nao `5000000`: com default numerico a flag venceria SEMPRE e a chave do arquivo nunca chegaria"
  - "a taxa de adena NEGATIVA e guarda estrutural e nao caso de uso -- `_adena_do_par` nao produz ganho negativo (CTX-6)"
  - "as linhas de ausencia do pack DOBRAM: medido, `_linha(rotulo, texto)` da 87 e 88 colunas"
  - "`pack` e posicional e SEM default em `bloco_da_renda`, ao contrario de `pisos_em_uso`"
metrics:
  duration: "~2h"
  completed: 2026-09-04
actuals:
  tokens: 20500
  tasks: 3
  commits: 6
---

# Quick 20260904: O ETA do proximo pack de adena — Summary

O bloco por intervalo do `--renda` passou a responder **"quando fecha o proximo pack
de adena"**, do mesmo jeito e com o mesmo vocabulario com que ele ja respondia
"quando eu subo de nivel" — e mostrando a conta inteira, nao so o resultado.

## A tela, renderizada com codigo de producao

```
O QUE ISSO RENDE (denominador em minutos farmados, e nao de relogio):
  XP/h janela (10min)              2,41 M    (n=142, agora)
  XP/h sessao (4h12 farmadas)      1,88 M    (n=3210, agora)
  adena/h janela (10min)           466 mil   (n=88, agora)
  adena/h sessao (4h12 farmadas)   226 mil   (n=1980, agora)
  falta para o nivel 69            3h20

O PROXIMO PACK DE ADENA (pack de 5,00 M):
  adena de agora                   27.309.465
  o proximo pack fecha em          30.000.000
  falta juntar                     2.690.535
  falta para o proximo pack        5h46
```

As tres coisas que o usuario ja tinha continuam onde estavam e nao foram tocadas: o
nick no titulo do bloco (`RENDA - TioMad`), o EXP como **numero** (nenhuma barra
desenhada) e o total de adena.

## A base do pytest, medida ANTES da primeira edicao

```
15 failed, 6231 passed, 87 skipped, 145 deselected, 5 warnings in 111.24s
```

## A rodada final, uma so, saida inteira

```
15 failed, 6265 passed, 87 skipped, 145 deselected, 5 warnings in 109.15s
```

**As MESMAS 15 falhas, nome por nome** — `test_janela_no_relogio` (7),
`test_sessao` (6), `test_respawn` (2), as bombas-relogio de `date.today()` ja
registradas no `deferred-items.md` da Fase 02. Nem uma a mais.

`6265 - 6231 = 34`, que sao exatamente os 34 testes novos: 10 em
`test_renda_conta.py`, 7 em `test_renda_console.py`, 7 em `test_renda_laco.py`,
2 em `test_renda_no_main.py` e 8 em `test_config_da_renda.py` (2 escritos e 6 de
crescimento das quatro `parametrize` que varrem as chaves — elas derivam a lista
do modulo, entao a sexta chave entrou sozinha).

**Onde a base foi medida:** neste worktree
(`.claude/worktrees/agent-ad3efade530df4de9`), com `python -m pytest -q --deselect
tests/test_agenda.py` e **sem** `PYTHONPATH` — o sandbox do worktree recusa um
`python` com `PYTHONPATH` apontando para fora dele (D-2 no `deferred-items.md`).
Por isso 87 skips e nao os 85 que o `quick/260903-bd8` mediu no checkout
principal: os dois a mais sao bindings WinRT ausentes, e as duas pontas da
comparacao foram medidas do mesmo jeito.

## O que mudou, tarefa por tarefa

**Task 1 - `test(...)` `8fb336b` / `feat(...)` `a120c96` - a conta.**
`renda_conta.tempo_ate_o_pack` e `TempoAteOPack`, gemeos exatos de
`tempo_ate_o_nivel` / `TempoAteONivel`: mesma forma, mesmos tres casos de ausencia
tratados **antes** da divisao, `Fraction` ate a borda, e o portao de arvore de
sintaxe que nega `math.inf` e `except ZeroDivisionError` continuando verde.

**Task 2 - `test(...)` `6e3318d` / `feat(...)` `06e12a9` - a casca.**
A sexta chave (`tamanho_do_pack_de_adena = 5000000`), a flag `--pack-de-adena` com
default `None`, e `_com_o_pack_da_linha_de_comando`, que troca o valor e **anuncia
o vencedor com os dois numeros** quando eles discordam.

**Task 3 - `test(...)` `61c1e20` / `feat(...)` `c449d51` - a tela.**
`_linhas_do_pack`, a secao logo abaixo do ETA do nivel, e
`renda_laco._tempo_ate_o_pack` ligando as duas metades.

## As seis observacoes de mutacao e controle

| # | tipo | o que foi feito | o que foi VISTO |
|---|------|-----------------|-----------------|
| 1 | mutacao | o alvo virou teto (`-(-adena // pack) * pack`) | **VERMELHA em 2 testes** - `assert previsao.alvo == 30000000` saindo com `alvo=0`, e o objeto impresso mostrando `segundos=Fraction(0, 1)`: exatamente o "voce ja tem o pack que ainda nao tem" que o desenho existe para impedir. `2 failed, 8 passed` |
| 2 | controle | `packs_ja_fechados` extraido para local nomeado | **VERDE** - `78 passed in 0.25s`. **MANTIDO**: a linha do `+ 1` passou a ser legivel |
| 3 | mutacao | a precedencia ao contrario (o arquivo vence a flag) | **VERMELHA** - `assert 7000000 == 3000000`, e o log capturado anunciando um vencedor que nao venceu. `1 failed, 5 passed` |
| 4 | controle | a grafia do numero extraida para funcao nomeada | **VERDE** - `56 passed`. **MANTIDO, mas apontado para `_grafia_da_adena`** (ver desvio 2) |
| 5 | mutacao | `_linha` no lugar de `_dobrar` numa linha de ausencia do pack | **VERMELHA com o numero na cara** - `AssertionError: 89 colunas`. `1 failed, 6 passed` |
| 6 | controle | as tres linhas de numero viradas laco sobre pares | **VERDE** - `84 passed`. **DESFEITO**: a lista literal e a forma do vizinho `_linhas_de_uma_taxa`, e duas formas para a mesma coisa no mesmo arquivo custam mais que a economia de duas linhas |

`git diff` confirma que os controles desfeitos nao deixaram rastro: os unicos
arquivos de producao no diff sao os seis listados no frontmatter.

## Numeros que cairam e dizem que cairam (Licao 6)

| onde | era | e | como foi medido |
|---|---|---|---|
| PLAN.md, o achado da largura | "86 colunas, e os tres estouram" | **87, 88 e 73 - so DOIS estouram** | chamada a `renda_console._linha` de producao |
| `test_config_da_renda.py`, o comentario de `AS_CINCO` | "uma lista escrita aqui envelheceria em silencio no dia em que uma sexta nascesse" | a sexta nasceu, e **nao envelheceu**: como os nomes vem do modulo, o unico ajuste foi acrescentar a linha | a propria mudanca |
| `test_renda_no_main.py`, a cerca | "a secao [renda] continua com **CINCO** chaves" | **SEIS**, com a razao antiga (cadencia) preservada no lugar e a cerca ainda de conjunto exato | a propria mudanca |
| `test_renda_console.py`, o controle do tamanho | pack de 10.000.000 -> alvo 40.000.000 | **30.000.000** - e por isso o controle passou a ser 4.000.000 | ver o achado abaixo |

## O ACHADO: um controle que nao controlava nada

O teste `test_O_TAMANHO_DO_PACK_CONFIGURADO_APARECE` nasceu comparando pack de
5.000.000 com pack de 10.000.000 e afirmando 40.000.000 no segundo. Ficou
vermelho - e a producao estava certa:

```
27.309.465 // 10.000.000 = 2   ->  o TERCEIRO pack fecha em 30.000.000
27.309.465 //  5.000.000 = 5   ->  o SEXTO    pack fecha em 30.000.000
```

Os dois tamanhos produzem **o mesmo alvo e o mesmo `falta juntar`** com aquela
adena. O 40.000.000 era uma conta de cabeca errada; mas o defeito maior nao era o
literal, e sim que um controle assim **nao distinguiria** um painel que ignorasse
o tamanho configurado - os dois lados dariam a mesma tela. E o mesmo padrao da
Licao 2 ("um criterio que nao muda com o fato que ele julga").

**A correcao foi na FIXTURA e nao no literal**: o controle passou a ser 4.000.000,
que da seis packs fechados (24.000.000) e o SETIMO fechando em 28.000.000,
faltando 690.535 - numeros diferentes dos do pack de cinco nas tres linhas. A
razao inteira esta escrita no fonte do teste, ao lado da constante, para ninguem
"simplificar" a fixtura de volta.

## Desvios do plano

**1. [Regra 1 - o numero do plano estava errado] o achado da largura era 87/88, e
nao 86.** O PLAN.md afirmava "86 colunas" e "os tres casos de ausencia estouram",
por conta a mao. A chamada a `renda_console._linha` de producao devolveu 87, 88 e
73: o terceiro texto (`TEXTO_SEM_EVIDENCIA`) **cabe**. O PLAN.md foi corrigido no
lugar, com os dois numeros lado a lado, antes da primeira edicao de codigo.

**2. [Regra 2 - evitar uma segunda verdade] o aviso de precedencia usa
`_grafia_da_adena` em vez de formatar o numero por conta propria.** O controle 4
extraiu a formatacao de milhar para uma funcao nomeada - e essa funcao **ja
existe**, e `renda_console._grafia_da_adena`, e a docstring dela diz com todas as
letras que uma aritmetica de milhar escrita a mao "seria uma segunda gramatica de
milhar nesta arvore". O `renda_laco` passou a importa-la. Precedente literal:
`renda_modo.py:192` ja importa esse mesmo nome privado, e a mesma razao fez
`duracao_curta` virar publica no `03-02`.

**3. [decisao de escopo] a cerca das CINCO chaves foi reescrita, nao removida.**
`test_a_secao_renda_continua_com_CINCO_chaves` afirmava conjunto exato de cinco
campos em `AjustesDaRenda`. Ela virou
`test_a_secao_renda_tem_SEIS_chaves_e_a_sexta_tem_nome`, **continua de conjunto
exato** (uma setima chave ainda a derruba), e a razao original - cadencia ja tem
`--intervalo` e `--status-a-cada` - esta preservada na docstring, junto do
argumento de por que o pack nao e cadencia.

**4. [fora de escopo, registrado] `_linhas_do_eta` estoura as 76 colunas.** Defeito
pre-existente do `03-01`, em linha que esta tarefa nao toca, com o conserto escrito
em `deferred-items.md` (D-1). As linhas NOVAS nao o repetem: elas passam por
`_linha_dobrada`, e a mutacao 5 prova que o teste pega se alguem desfizer isso.

**5. [nao corrigido, apenas registrado] o frontmatter de
`.planning/workstreams/renda/STATE.md` esta velho.** Ele diz `current_phase: 01` e
`status: planning`, mas a Fase 3 ja tem quatro planos com SUMMARY em disco.
Corrigir isso e trabalho do fluxo de fase; reescrever daqui inventaria um estado
que este agente nao mediu. Fica uma nota dentro do proprio STATE.md.

## Restricoes respeitadas

- **Nenhuma dependencia nova.** `rich` continua fora, e nenhuma barra de XP foi
  desenhada - o EXP segue sendo numero, como o usuario confirmou.
- **Nenhum `datetime.now()`** no caminho novo: o tempo entra por `agora=`, e
  `TestOPortaoDoRelogio` continua verde.
- **O laco chama `renda_conta`, nunca as regras de par** - o portao de
  `tests/test_renda_par.py` continua verde.
- **Nenhum arquivo do workstream `dashboard`** foi tocado.
- `calibration.json`, `.renda/` e `.mercado/` nao aparecem em nenhum dos seis
  commits; todo teste novo usa fixtura ou `tmp_path`.
- Nenhum `--amend`, nenhum `stash`, nenhum `git clean`.

## Conferencia visual pendente (para o orquestrador)

Com o jogo aberto e a janela calibrada:

    vigiar-renda.bat

O que tem de aparecer no bloco, a cada `--status-a-cada` segundos, logo abaixo de
`falta para o nivel NN`:

- o titulo `O PROXIMO PACK DE ADENA (pack de 5,00 M)`;
- `adena de agora` batendo, digito por digito, com o contador do canto da tela;
- `o proximo pack fecha em` sendo o proximo multiplo de 5.000.000 **acima** dele;
- e, depois de ~3 minutos de farm (o piso da janela e 120 s farmados),
  `falta para o proximo pack` saindo como duracao. Antes disso a linha diz
  "sem previsao: ainda nao da para dizer" com o piso que faltou escrito embaixo.

E, para conferir a flag numa rodada so:

    python -m l2scanner --renda --janela AUTO --pack-de-adena 10000000

O log tem de trazer UMA linha comecando com `PACK DE ADENA: vale 10.000.000,
pedido em --pack-de-adena`, e o titulo do bloco tem de dizer `pack de 10,00 M`.

## Self-Check: PASSED

Arquivos criados - os tres de `.planning/quick/20260904-eta-do-pack-de-adena/`
conferidos com `test -f`: PLAN.md, SUMMARY.md, deferred-items.md.
Commits - `8fb336b`, `a120c96`, `6e3318d`, `06e12a9`, `61c1e20`, `c449d51`: os
seis existem em `git log`.
