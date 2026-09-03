---
phase: quick-260903-bd8
plan: 01
subsystem: dashboard
tags: [adena, exibicao, eixo, dash-03, dash-05, aden-04]
status: complete
requires:
  - l2scanner/mercado_console.py::UNIDADE_DA_TAXA
  - l2scanner/dashboard_dados.py::_escala_do_grafico
provides:
  - l2scanner/dashboard_dados.py::_escadas_do_eixo
  - "payload: series[].escadas_do_eixo"
  - l2scanner/recursos/dashboard/dashboard.js::marcasVisiveis
affects:
  - l2scanner/mercado_console.py
  - l2scanner/dashboard_dados.py
  - l2scanner/recursos/dashboard/dashboard.js
  - l2scanner/recursos/dashboard/index.html
tech-stack:
  added: []
  patterns:
    - "o Python entrega VARIAS escadas; o navegador escolhe qual cabe (molde de `resolucaoPara`)"
key-files:
  created:
    - tests/test_escala_de_exibicao.py
  modified:
    - l2scanner/mercado_console.py
    - l2scanner/dashboard_dados.py
    - l2scanner/recursos/dashboard/dashboard.js
    - l2scanner/recursos/dashboard/index.html
    - tests/test_dashboard_dados.py
    - tests/test_dashboard_js.py
    - tests/test_dashboard_pagina.py
    - tests/test_dashboard_serie_generica.py
    - tests/test_dashboard_tracer.py
    - tests/test_mercado_console.py
    - tests/test_mercado_registro_adena.py
decisions:
  - "`UNIDADE_DA_TAXA` = 5.000.000, a escala da coluna `5 mln increment` do jogo"
  - "`UNIDADE_DA_TAXA` e `ADENA_POR_INCREMENTO` continuam DUAS constantes apesar de valerem o mesmo"
  - "as marcas do eixo e os textos delas vem do Python; o navegador so seleciona"
  - "`MAXIMO_DE_MARCAS_POR_ESCADA` = 200 e `MAXIMO_DE_MARCAS_VISIVEIS` = 8 sao ESCOLHA, nao medicao"
metrics:
  duration: ~50 min
  completed: 2026-09-03
actuals:
  tokens: 21000
  tasks: 3
  commits: 3
---

# Quick 260903-bd8: A taxa da Adena passa a se falar por 5 milhoes — Summary

A escala de exibicao da taxa foi de um milhao para CINCO milhoes — a escala em que
o proprio jogo escreve a coluna (`5 mln increment`) — e o eixo vertical do grafico
passou a receber marcas e textos prontos do Python, na mesma forma de dinheiro
brasileiro que o titulo logo acima dele.

## A base do pytest, medida ANTES da primeira edicao

```
15 failed, 5693 passed, 85 skipped, 5 warnings in 135.96s (0:02:15)
```

As 15 sao as CONHECIDAS, da area de outro agente: `test_janela_no_relogio` (7),
`test_sessao` (6), `test_respawn` (2).

## A rodada final, uma so, saida inteira

```
15 failed, 5708 passed, 85 skipped, 5 warnings in 154.86s (0:02:34)
```

As MESMAS 15 falhas, nome por nome — nem uma a mais. `5708 - 5693 = 15`, que sao
exatamente os 15 testes novos deste plano (2 + 5 + 1 + 2 + 5).

## O que mudou

**Task 1 (`f098f7a`)** — `UNIDADE_DA_TAXA` passa a `5_000_000`. Seis superficies
alinhadas numa unidade so, afirmadas na MESMA funcao de teste
(`TestUmaTelaUmaUnidade`), porque o defeito relatado nao foi "um numero errado"
e sim "duas unidades na mesma tela". A oferta do usuario (10.000.000 de adena
por `111,00` XM) le `55,50` e nunca mais `11,10`.

**Task 2 (`aec1cb6`)** — o payload ganha `escadas_do_eixo` por serie: varias
escadas de passo bonito (1, 2, 5 x potencia de dez), da mais fina para a mais
grossa, com pixel e texto prontos. O `dashboard.js` ganha `marcasVisiveis`, que
FILTRA por faixa e devolve a primeira escada que cabe — selecao, nao formatacao.
`axes[1]` ganha `splits` e `values`.

**Task 3 (`6aa646b`)** — `tests/test_escala_de_exibicao.py`, cinco testes que
MEDEM a frase que o fonte sempre afirmou: que a constante e de exibicao so.

## Numeros que cairam e dizem que cairam (Licao 6)

| onde | era | e | como foi medido |
|---|---|---|---|
| `formatar_taxa_derivada`, conta por extenso | `1.160 centesimos = 11,60` | `5.800 centesimos = 58,00` | aritmetica, refeita no fonte |
| `_valor_em_reais`, conta por extenso | `R$ 5,80 por milhao` | `R$ 29,00 por 5 milhoes` | idem |
| `_pixel`, pior caso do `float` (absoluto) | `1,94e-11` | **`7,76e-11`** — SUBIU | chamada ao proprio `_pixel` |
| `_pixel`, erro relativo | `5,82e-17` | **`4,66e-17`** — CAIU | idem |
| `_pixel`, valores reais do CSV | erro ZERO | erro ZERO, **remedido** | idem |

O pior caso absoluto SUBIU x4 e a docstring diz isso com as duas medicoes lado a
lado. Multiplicar por cinco leva o valor a uma faixa com menos bits de fracao
disponiveis; o erro relativo, esse, nao piorou — os dois abaixo do epsilon da
maquina (2,22e-16).

## As nove observacoes de mutacao e controle

| # | tipo | o que foi feito | o que foi VISTO |
|---|---|---|---|
| 1 | mutacao | `UNIDADE_DA_TAXA` de volta a `1_000_000` | **VERMELHA** — `assert '11,10 XM por...' == '55,50 XM por...'`; `1 failed, 1 passed, 35 deselected in 0.65s` |
| 2 | controle | `round(taxa * UNIDADE_DA_TAXA)` extraido para local nomeado | **VERDE** — `221 passed in 0.79s` |
| 3a | mutacao | texto da marca sem `formatar_centesimos` (numero cru) | **VERMELHA dos DOIS lados da costura** — `assert ['5600', ...] == ['56,00', ...]`, `At index 0 diff: '5600' != '56,00'`; `2 failed in 0.93s` |
| 3b | mutacao | `marcasVisiveis` devolve a ULTIMA escada que cabe | **VERMELHA, com lista mais CURTA** — `assert ['56,00', '58,00', '60,00'] == [...cinco...]` e `assert ['58,00'] == ['57,90', ...]`; `2 failed, 41 deselected in 0.54s` |
| 4a | controle | laco das marcas reescrito como laco explicito (Python) | **VERDE** — `97 passed in 2.15s` |
| 4b | controle | condicao de faixa extraida para funcao nomeada (JS) | **VERDE** — na mesma rodada acima |
| 5a | mutacao | `menor_pedido_visivel` comparando `round(unitario * 5_000_000)` | **VERMELHA, escolhendo `11101`** — `assert Fraction(11101, 10000000) == Fraction(111, 100000)`; `1 failed, 4 passed in 0.22s` |
| 5b | mutacao | `_pixel` arredondando antes do `float` | **VERDE NA PRIMEIRA TENTATIVA — ver o achado abaixo.** Depois da correcao do criterio: **VERMELHA**, `assert 1111.0 == 1111.2 +- 1.1e-09`; `1 failed, 4 passed in 0.36s` |
| 6 | controle | lista de unitarios extraida para local nomeado antes do `min` | **VERDE** — `5 passed in 0.12s` |

Controle 2 foi MANTIDO (ficou mais legivel, e a saida e byte-identica). Todos os
outros foram desfeitos, e `git diff` confirma `mercado_analise.py`,
`rastreador.py` e `visao.py` sem uma linha de mudanca.

## O ACHADO: uma mutacao que nao ficou vermelha

**A mutacao 5b sobreviveu ao criterio na primeira tentativa**, e isso e o unico
achado real deste plano. Reportado aqui em vez de corrigido em silencio.

O teste da razao entre os pixels dizia pegar "o arredondamento na fronteira do
`float`". Com a fixtura de duas ofertas ele NAO pegava. Medido:

```
11101 -> real 5.550,5 -> arredonda 5.550 | trocado 1.110,1 -> arredonda 1.110
         e 5.550 x 0,2 = 1.110,0, que e exatamente o outro lado
```

Os dois lados arredondaram PROPORCIONALMENTE, por coincidencia dos numeros
escolhidos, e a razao sobreviveu. Um criterio que nao muda com o fato que ele
julga e exatamente o defeito que a Licao 2 nomeia — o teste estava afirmando uma
propriedade em vez de medi-la.

**A correcao foi na FIXTURA, e nao na tolerancia.** Uma terceira oferta
(`11111`) quebra a proporcao sob arredondamento:

```
11111 -> real 5.555,5 -> arredonda 5.556 | trocado 1.111,1 -> arredonda 1.111
         e 5.556 x 0,2 = 1.111,2, que NAO e 1.111
```

Com ela a mutacao fica vermelha. A razao inteira esta escrita no fonte do teste,
ao lado da constante, para ninguem "simplificar" a fixtura de volta.

## Desvios do plano

**1. [Rule 1 — o literal do plano contradizia a propria conta] `R$ 27,75`, e nao
`R$ 29,00`, no Teste 1 da Task 1.** O plano pedia o CSV da oferta de `11100` e o
literal `29,00`. Mas `destaque.reais` sai do MENOR pedido, e o menor daquele CSV
e `11100`: `5.550 centesimos x R$ 0,50 = 2.775 centavos = R$ 27,75`. O `29,00` da
tabela `<a_conta_por_extenso>` e do OUTRO exemplo, o de `11600`. O teste afirma
`27,75` com a conta por extenso ao lado; o `29,00` esta afirmado no seu lugar
proprio, em `test_dashboard_dados.py`, sobre o CSV de `11600`.

**2. [Rule 1 — a exatidao que o plano pediu e impossivel em `float`] a razao
entre os pixels nao fecha EXATAMENTE.** O plano dizia "e exatamente a razao entre
as duas escalas". Medido com codigo de producao: `5550.5` e representavel em
binario, `1110.1` nao e; o erro e **8,19e-17 relativo** (9,09e-14 absoluto),
abaixo do epsilon da maquina. A tolerancia usada e `1e-12` — cinco ordens acima
do ruido medido e quatro abaixo do menor defeito que o teste precisa pegar —, e
os tres numeros estao escritos na docstring.

**3. [Rule 2 — contrato que precisava crescer junto] `PROPRIEDADES_DO_CONTRATO`
foi de SEIS para SETE.** O teste `test_a_funcao_de_serie_usa_EXATAMENTE_as_propriedades_do_contrato`
reprovou assim que o JS passou a ler `serie.escadas_do_eixo` — funcionou
exatamente como projetado. A entrada nova tem a razao escrita ao lado, e ela nao
e uma excecao com forma de Adena: TODA serie traz a chave.

**4. [Rule 1 — dano de ferramenta, corrigido] linhas de `dashboard_dados.py`.**
Um script Python de mutacao converteu o arquivo inteiro de LF para CRLF (o
`read_text`/`write_text` do Windows traduz), o que teria virado um diff de
arquivo inteiro. Detectado pelo `git diff --stat` e desfeito: o arquivo voltou a
LF, preservando ate o `\r` solto que ele ja tinha no fim. O diff final e de
**127 insercoes e ZERO delecoes**.

**5. [decisao de escopo, ACEITA pelo orquestrador] o eixo do item comum.** A
correcao generica alcanca a serie do item comum, cujo rotulo continua
`centésimos por unidade` mas cujas marcas agora saem em forma de dinheiro pela
mesma `formatar_centesimos`. Ha teste medindo isso
(`test_as_DUAS_series_ganham_escada_de_eixo_na_forma_de_DINHEIRO`), e o DASH-05
proibia a excecao com forma de Adena de qualquer modo.

## Sobre os portoes de TDD

As Tasks 1 e 2 sao `tdd="true"`. O ciclo RED foi OBSERVADO e esta registrado
antes de cada implementacao — `'11,10' != '55,50'` na Task 1, `KeyError:
'escadas_do_eixo'` e `ReferenceError: marcasVisiveis is not defined` na Task 2 —,
mas **nao ha commit `test(...)` separado do `feat(...)`** nas duas. A razao: os
mesmos arquivos de teste carregavam, na mesma edicao, as fixacoes ANTIGAS
atualizadas com a razao ao lado, e um commit intermediario teria sido vermelho
por dois motivos diferentes ao mesmo tempo. O que prende cada mudanca no lugar do
commit RED sao as cinco mutacoes acima, que sao prova mais forte. A Task 3, que e
so teste, tem o seu `test(...)` proprio.

## Conferencia visual pendente (para o orquestrador)

O servidor da porta 8787 NAO foi tocado. Ao reinicia-lo, o que tem de aparecer:

- o titulo diz **`Quanto valem 5 milhões de adena`** (aba e `<h1>`, iguais);
- o destaque diz **`55,50 XM por 5 milhoes de adena (derivado)`** para a oferta
  de 10.000.000 por `111,00`;
- o eixo vertical mostra **`56,00 / 57,00 / 58,00 ...`** — dinheiro brasileiro,
  a mesma forma do titulo logo acima —, e nunca mais `900 / 1.000 / 1.100`;
- aproximar o grafico troca a escada para uma mais fina (`57,90 / 57,95 / ...`)
  sem uma nova viagem ao servidor.

## Restricoes respeitadas

- `calibration.json`, `.mercado/` e `recordings/` NAO aparecem em nenhum dos tres
  commits, e `git status` esta limpo. Todo teste usa `tmp_path`.
- O vigia do mercado e o servidor da 8787 nao foram tocados.
- Nenhuma dependencia nova; nenhuma biblioteca de sintese de input. O `node`
  continua opcional, com `pytest.skip` que diz a razao (e ele EXISTE nesta
  maquina, entao os dois testes da costura rodaram de verdade: `2 passed`).
- `rastreador.py`, `visao.py`, `mercado_analise.py` e `VERSAO_DO_ESQUEMA`
  intactos. Nenhum `--amend`, nenhum `stash`.
- As duas convencoes de acentuacao ficaram: o console escreve `5 milhoes`, a
  pagina escreve `5 milhões`.
- Nenhum comentario novo do `dashboard.js` cita pelo nome uma funcao de
  formatacao do navegador, e nao ha variavel `n` comparada com digito. As sondas
  de `tests/test_dashboard_js.py` continuam verdes.

## Self-Check: PASSED

Arquivos: os 12 conferidos com `git log --name-only`, todos presentes.
Commits: `f098f7a`, `aec1cb6`, `6aa646b` — os tres existem em `git log`.

---

## Verificacao do orquestrador — e um achado NOVO que ela produziu

O payload de producao foi conferido no servidor vivo: `series[0].escadas_do_eixo` traz **6
escadas**, e a primeira marca e `{"pixel": 4550, "texto": "45,50"}` — o texto brasileiro,
vindo do Python, exatamente como o plano desenhou. Os 48 testes de costura
Python -> JSON -> JavaScript passam.

**Mas a tela continuava mostrando `6.000` / `5.500`.** Medido, e nao suposto:

    performance.getEntriesByType('resource')  ->  dashboard.js
      encodedBodySize : 51.193      transferSize: 0   (DO CACHE)
    o servidor entrega: 56.677 bytes

Cinco mil e quatrocentos bytes de diferenca — o codigo novo inteiro. E o navegador serviu a
copia velha **ate numa aba nova**, porque o cache HTTP e do perfil, nao da aba.

A causa esta nos cabecalhos: o dashboard manda `Last-Modified`, `Content-Type` e o CSP, mas
**nao manda `Cache-Control` nem `ETag`**. Sem diretiva explicita o navegador aplica cache
heuristico e decide sozinho por quanto tempo guarda.

**Isto e uma lacuna aberta, e ela e maior que esta tarefa:** toda mudanca futura no
`dashboard.js` ou no `dashboard.css` vai parecer que nao funcionou, e o usuario nao tem como
saber que o problema e cache. Um dashboard que nao consegue se atualizar sozinho e um
dashboard que mente sobre a propria versao. Fica registrado aqui como o proximo trabalho
obvio do workstream do dashboard; nao entrou nesta tarefa porque o escopo era a escala e o
eixo, e mexer no servico de arquivos estaticos e outra decisao.
