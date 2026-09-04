---
phase: 02-dashboard-calculadora-de-rotas
plan: 01
subsystem: dashboard
tags: [calculadora, fraction, config-toml, payload, quarta-regiao, tracer]
status: complete

requires:
  - "Fase 1 do dashboard: payload, servidor, cache, precedencia de estados, tokens de tema"
  - "mercado_analise: menor_pedido_visivel, unitario, resolver_o_nome, Evidencia, recencia_do_preco"
  - "mercado_console: formatador_do_unitario, formatar_centesimos, descrever_a_quantidade, _recencia_em_duas_formas"
provides:
  - "l2scanner/dashboard_rotas.py: a conta das duas rotas em Fraction, pura e sem cambio"
  - "config.ler_itens_de_rota: o leitor de [[dashboard.item]] que derruba o arranque"
  - "payload.calculadora: o bloco novo, com tres estados de bloco e quatro de linha"
  - "a quarta regiao da pagina, com o molde da linha em <template>"
  - "tres sondas de CSS reusaveis, para o plano 02-03 ESTENDER"
affects:
  - "l2scanner/dashboard.py: main le o config.toml ANTES do bind"
  - "l2scanner/dashboard_dados.py: payload ganha dois parametros com default"

tech-stack:
  added: []
  patterns:
    - "Fraction de ponta a ponta, arredondamento so no formatador"
    - "contrato por FORMA sob TYPE_CHECKING, verificado por subprocesso"
    - "constante de julgamento nomeada, com a razao e a marca ESCOLHA"
    - "refutacao medida escrita no fonte, ao lado do codigo que ela justifica"
    - "sonda de teste como funcao de modulo, para o plano seguinte estender em vez de copiar"

key-files:
  created:
    - l2scanner/dashboard_rotas.py
    - tests/test_dashboard_itens_config.py
    - tests/test_dashboard_rotas_tracer.py
  modified:
    - l2scanner/config.py
    - l2scanner/dashboard_dados.py
    - l2scanner/dashboard.py
    - l2scanner/recursos/dashboard/index.html
    - l2scanner/recursos/dashboard/dashboard.css
    - l2scanner/recursos/dashboard/dashboard.js
    - config.toml

decisions:
  - "MARGEM_DE_EMPATE_PERCENTUAL = Fraction(3,100), ESCOLHA declarada e nao medicao"
  - "o percentual usa o denominador MAIS CARO (quanto eu economizo), com os dois numeros escritos"
  - "a marca de vencedora ENTRA na lista fechada de posicoes do acento dourado do UI-SPEC"
  - "os itens NAO entram na chave do cache: sao lidos uma vez, no arranque"
  - "ItemDeRotaInvalido e classe propria, e nao ReceitaInvalida reusada"

metrics:
  duration: "~3h"
  completed: 2026-09-03

actuals:
  tokens: 40486
  tasks: 3
  commits: 4
---

# Phase 2 Plan 01: A calculadora de rotas — Summary

O tracer atravessou a fase inteira numa fatia fina de producao: um bloco
`[[dashboard.item]]` no `config.toml` vira, num `GET /dados` sobre um servidor
de pe, um veredito com as duas rotas lado a lado e a vencedora marcada — com a
comparacao acontecendo em `Fraction` e sem que a conta saiba o que e cambio.

## O que ficou de pe

**`l2scanner/dashboard_rotas.py` (novo, puro).** As duas rotas convergem em
centesimos de XM por UMA unidade: a do mercado ja chega assim; a do NPC sai de
adena multiplicada pela taxa (centesimos de XM por adena) e dividida pelo
pacote. **Nao existe parametro de cambio neste modulo**, e essa ausencia e a
garantia estrutural do achado que desenha a fase: as duas rotas terminam
multiplicadas pelo mesmo `reais_por_xm`, entao ele CANCELA — o veredito continua
respondendo no dia em que o usuario esquecer de atualizar o cambio, que e o dia
em que ele mais precisa dele.

**`config.ler_itens_de_rota`.** Molde literal de `ler_receitas`, com quatro
diferencas deliberadas e escritas: o acesso aninhado em dois niveis, a guarda de
que a secao e tabela, os dois tetos, e a recusa de nome repetido por
`nome_normalizado`.

**O bloco `calculadora` no payload**, com tres estados de bloco e quatro de
linha, e `null` nos dois estados de falha fechada.

**A quarta regiao**, que e um `.painel` — e por isso entra na precedencia de
estados da Fase 1 sem uma linha de CSS nova.

## A medicao contra o `.mercado/` REAL

Rodada com `dashboard_dados.payload` de PRODUCAO contra a pasta do usuario, em
2026-09-03. **Somente leitura, e conferido:** a impressao digital do
`observacoes.csv` (tamanho, `mtime_ns`, sha256) e byte-identica antes e depois —
`3617 / 1788464390541245100 / eaf589d023c61979` nos dois lados.

| Fato da tabela do plano | Medido agora | Confere? |
|---|---|---|
| series: `adena#` (n=50) e `common-fafurion-doll#` (n=8) | identico | sim |
| menor unitario da Adena = `Fraction(9, 10000)` | `9/10000` | sim |
| menor unitario do doll = `5900` centesimos | `5900` | sim |

**Nenhum numero da tabela caiu.** A saida completa, com um preco de NPC de
exemplo declarado de 15.000 adena (ninguem nesta arvore sabe quanto o NPC cobra):

```
estado da calculadora: com_itens
instante da leitura  : Precos de NPC lidos do config.toml agora mesmo (03/09 23:38).
                       Corrigiu o arquivo? Reinicie o dashboard.
  item      : Common Fafurion Doll
  estado    : decidida
  npc       : 0,14 por unidade (derivado)
  pacote    : 15.000 de adena por 1 unidade
  mercado   : 59,00 por unidade (derivado)
  vencedora : npc
  diferenca : 58,86 por unidade (derivado) / 99,8%
  n         : 8 | recencia: ha 6 h (03/09 16:39)
```

## O controle do `Fraction` — fechou pela saida (b), e o registro esta aqui

O criterio do plano tinha duas saidas. **Esta fechou pela (b)**, e o registro do
que foi tentado esta na docstring de `TestOFractionMudaOQueSaiNaTela` e resumido
aqui.

**Tentado, com codigo de producao no lado exato:** 400 mil sorteios em faixas
realistas (**0 inversoes de vencedora, 0 colapsos**); 300 mil procurando
"diferenca exata nao nula com diferenca em float zero" (**0 casos**); 2 milhoes
procurando divergencia de arredondamento (**0 casos**).

**Por que a saida (a) e ESTRUTURALMENTE inalcancavel** — e as duas razoes viraram
teste, em vez de ficarem como prosa:

1. **Converter `Fraction` para `float` e monotonico.** Medido: 0 violacoes em
   200 mil pares. Uma implementacao que convertesse e comparasse NAO CONSEGUE
   inverter uma vencedora.
2. **A grade de precos do mercado e grossa demais para caber no erro.** O preco
   e `Fraction(total, quantidade)` sobre inteiros que o jogo exibe, entao o
   espacamento perto de um valor e `1/quantidade` — da ordem de um milesimo,
   contra um erro de `float` da ordem de `1e-16` relativo. Nao ha preco possivel
   dentro do buraco.

A isso soma-se a faixa de empate de tres por cento, catorze ordens de grandeza
acima do erro — enquanto ela existir, nenhum erro de representacao move o ESTADO
de uma linha.

**A propriedade pinada no lugar e VISIVEL na tela, e o par e DERIVADO e nao
escolhido a dedo:** de `1/98` nao ser representavel em binario. Com
`taxa = Fraction(1, 2d)` e `preco = (2K+1)*d`, o unitario exato cai em cima da
fronteira de arredondamento; varrendo `d` impar ate 3999 e `K` ate 399 dentro do
teto, **40.616 pares divergem**. Nos dois testes, pelos formatadores de producao:

- o `float` imprime **`0,01`** onde a conta exata imprime **`0,02`**;
- num empate cravado (as duas rotas em `Fraction(7,2)`), o `float` devolve
  diferenca `-4,44e-16` e afirma que o NPC e **estritamente mais barato**.

A forma fraca — "a implementacao usa `Fraction`" — nao aparece em teste nenhum.

## As provas de mutacao

Cada guarda desta fase foi quebrada de proposito para ver o teste ficar vermelho:

| Mutacao na linha de producao | Resultado |
|---|---|
| `<=` vira `<` na faixa de empate | 1 falha, exatamente `test_EXATAMENTE_na_margem_e_EMPATE_e_a_borda_INCLUI` |
| a frase da calculadora empurrada para `avisos` | 3 falhas — 2 minhas e **1 do `01-07`** |
| apagar a regra que mostra a marca da vencedora | 1 falha |
| esconder o lado perdedor no CSS | 1 falha |
| regra PROPRIA de falha fechada para `#rotas` | 1 falha |
| o vao do instante migrado para dentro do molde | 2 falhas (as duas metades) |

## Numeros pedidos pelo plano

- `python -m pytest tests/test_dashboard_itens_config.py -q` -> **40 testes** (piso: 18).
- `python -m pytest tests/test_dashboard_rotas_tracer.py -q` -> **75 testes** (piso: 20).
- `grep -c 'painel' index.html`: **7 antes -> 13 depois**.
- `grep -v '^#' config.toml | grep -c 'dashboard.item'` -> **0** (o bloco entra comentado).
- `git diff --numstat requirements.txt` -> **vazio**. Nenhuma dependencia nova.
- Cerca dura intacta: nenhum modulo do workstream `mercado` aparece no diff da fase.
- `import l2scanner.dashboard_rotas` **nao** carrega `l2scanner.config`.
- Custo do import de `config` no dashboard, re-medido: **341 -> 366 modulos (+25)**,
  com `cv2` e `numpy` **ja presentes antes** e **ausentes** entre os novos.

## Deviations from Plan

### [Regra 1 - Bug] Uma afirmacao minha caiu, e foi reescrita no lugar

**Encontrado em:** Tarefa 1.
**O que houve:** escrevi um teste afirmando `config.toml` e ASCII. Ele ficou
vermelho.
**A medicao:** o arquivo **ja tinha 45 travessoes U+2014 em 41 linhas**, desde a
linha 1, antes desta fase — e zero letra acentuada. A pasta `tests/` inteira e
igual. A regra da casa nunca foi "ASCII"; e "sem letra acentuada", porque o
console do Windows abre em cp1252 e pontuacao em docstring nunca chega la.
**O conserto:** o teste passou a medir a coisa certa — o unico caractere fora do
ASCII e o travessao, com controle de que ele esta mesmo presente. A frase antiga
e a nova estao as duas escritas no fonte, com os dois numeros (regra 6).
**Commit:** `20984bc`.

### [Escolha declarada] O `_EXEMPLO_DO_ITEM` NAO viaja na recusa de nome repetido

O plano dizia "ele viaja em TODA recusa desta secao". Ele viaja em toda recusa
de **sintaxe**, e nao na de nome repetido — seguindo o precedente de
`_recusar_nicks_repetidos` e `_recusar_bosses_repetidos`, que tambem nao mostram
exemplo. **A razao esta escrita no fonte:** nome repetido nao e erro de sintaxe;
o usuario ja escreveu o bloco certo, duas vezes. Mostrar o exemplo ali sugeriria
acrescentar um TERCEIRO bloco, que e o oposto do conserto. Isso tambem mantem o
teste de repetidos medindo de verdade — com o exemplo colado, `count("Gemstone C")
>= 2` passaria sem os dois nomes serem listados.

### [Escolha declarada] `MOLDE_DA_DIFERENCA_PERCENTUAL` e so o numero

Ele saiu como `"{valor}%"`, sem rotulo. O rotulo ("mais barato") nasce na
**marcacao**, junto com o resto da copia de interface — que e a regra desta
regiao. Uma metade da frase no Python e a outra no HTML seria copia em dois
lugares.

### Nota sobre o primeiro formatador de porcentagem

`_percentual_em_texto` e o **primeiro** formatador de porcentagem da camada de
exibicao, e nao um segundo: nao havia nenhum. O unico lugar que imprime
porcentagem e `mercado_analise.frase_da_tendencia`, que a monta inline com
`:+.1f%` para o **console** (ASCII, com sinal), enquanto este e **pagina**
(acento, sem sinal, virgula decimal). O que os dois compartilham e a PRECISAO de
uma casa, e a razao esta escrita: duas casas afirmariam sobre um numero apoiado
em UMA oferta uma precisao que ele nao tem.

## A pergunta deixada ESCRITA para o plano 02-02

O criterio de "sem taxa" nesta fatia e `menor.unitario is None` — o piso do
menor, que vale um. **Falta decidir se o veredito herda tambem a EVIDENCIA da
taxa**, isto e, se uma taxa apoiada numa unica oferta deve enfraquecer o veredito
do mesmo jeito que enfraquece o destaque. A pergunta esta na docstring de
`_bloco_da_calculadora`, nomeando o 02-02 — deixa-la escrita e diferente de
deixa-la calada: o proximo plano tem de encontra-la, e nao redescobri-la.

## Known Stubs

Nenhum. Todos os vaos criados nesta fase sao preenchidos por codigo desta fase —
inclusive o do instante da leitura, que o plano exigiu criar E escrever na mesma
onda, com teste sobre as duas metades.

## Deferred Issues

**16 falhas PRE-EXISTENTES** em `test_respawn.py`, `test_sessao.py`,
`test_janela_no_relogio.py` e `test_janela_de_selecao.py` — subsistema de
party/bosses/agenda, fora do alcance declarado deste plano.

**A causalidade foi MEDIDA, e nao suposta.** Como esta fase mexeu em `config.py`
e esses testes o CARREGAM, "eles nao importam o que eu mudei" nao bastava: a
versao de `config.py` anterior a esta fase foi colocada no lugar e os quatro
arquivos rodaram de novo. Resultado **identico** (`15 failed, 264 passed` nos
dois casos, mesmo conjunto). Detalhes e a hipotese de causa (dependencia de data)
em `deferred-items.md`.

## Self-Check: PASSED

- Os 10 arquivos citados em `key-files` existem em disco.
- Os 4 commits citados existem: `bfbb5ab`, `20984bc`, `24b3977`, `9d00547`.
- As duas contagens de teste conferem: `40 + 75 = 115 passed`.
- A impressao digital do `.mercado/observacoes.csv` real e identica antes e
  depois da medicao manual.

## Threat Flags

Nenhuma superficie nova alem da que o `<threat_model>` do plano ja previa. O
`config.toml` entra pela fronteira que T-02-01 nomeia, com os dois tetos e a
guarda de booleano; o nome do item entra no DOM por propriedade de texto sobre
molde clonado (T-02-03), com as quatro sondas do `01-07` cobrindo a regressao.
