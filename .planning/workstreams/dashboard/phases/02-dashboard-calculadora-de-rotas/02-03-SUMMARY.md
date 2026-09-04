---
phase: 02-dashboard-calculadora-de-rotas
plan: 03
subsystem: dashboard
tags: [calculadora, quarta-regiao, css, marcacao, sonda-com-controle, calc-02, calc-03, calc-04]
status: complete

requires:
  - "02-01: o bloco `calculadora` no payload, a quarta regiao, o molde da linha, as tres sondas de CSS reusaveis"
  - "02-02: o piso do veredito, os seis estados de linha, a diferenca em R$ nula sem cambio, a mediana de contexto"
  - "Fase 1: os tokens, a precedencia fechada de cinco estados, os tres ortogonais, o Copywriting Contract"
provides:
  - "a quarta regiao COMPLETA na tela: seis estados desenhados, duas rotas sempre visiveis, vencedora marcada"
  - "a procedencia do preco do NPC na linha (CALC-02), sem carimbo inventado"
  - "a linha de R$ da diferenca no MESMO agrupamento de seletores que o cartao de R$ do destaque (CALC-03)"
  - "a frase de falta do Python no lugar do veredito, e nunca um vencedor cinza (CALC-04)"
  - "tests/test_dashboard_calculadora_pagina.py: 69 testes, os cinco elos, controle por forma"
  - "_SOME_DA_TELA ampliado de TRES para SETE formas, numa autoridade so"
affects:
  - "tests/test_dashboard_rotas_tracer.py: o conjunto de reconhecimento das tres sondas ficou mais largo"

tech-stack:
  added: []
  patterns:
    - "sonda de ausencia com CONTROLE POR FORMA, e a fronteira do que ela nao pega declarada por extenso"
    - "conjunto de reconhecimento partilhado entre dois arquivos de teste, com teste contando as definicoes"
    - "criterio que CASA o seletor contra a lista do Python, em vez de buscar o literal"
    - "condicao de tela mora no CSS; o JS so troca o valor de um atributo"
    - "a mesma string num vao so — mover o elemento, e nunca duplicar o texto"

key-files:
  created:
    - tests/test_dashboard_calculadora_pagina.py
  modified:
    - l2scanner/recursos/dashboard/index.html
    - l2scanner/recursos/dashboard/dashboard.css
    - l2scanner/recursos/dashboard/dashboard.js
    - tests/test_dashboard_rotas_tracer.py

decisions:
  - "a frase de falta e o MESMO elemento e a MESMA string do aviso da linha, movido para o lugar do veredito — e nao uma segunda copia"
  - "o estado empatado ganhou copia propria na marcacao: sem ela ele era um retangulo mudo"
  - "o seletor do estado que nomeia a serie sentinela casa por PREFIXO, para nao afrouxar o DASH-05"
  - "`data-velho` fica NA LINHA, com o nome e o token do ortogonal da Fase 1"
  - "o vao `mercado-pacote` foi REMOVIDO: era orfao desde o 02-01"
  - "a divida de prefixo `FRASE_`/`MOLDE_` NAO foi paga, e a razao ficou escrita no `index.html`"

metrics:
  duration: "~2h"
  completed: 2026-09-04

actuals:
  tokens: 17566
  tasks: 3
  commits: 4
---

# Phase 2 Plan 03: A quarta regiao na tela — Summary

O payload ja sabia responder; agora a resposta e uma coisa que uma pessoa
confere com o dedo na tela. As duas rotas ficam sempre lado a lado com a
vencedora marcada por uma PALAVRA, o preco do NPC diz de onde veio sem inventar
carimbo, a diferenca em R$ some sozinha pelo mesmo seletor que ja retira o
cartao de R$ do destaque, e nos quatro estados sem vencedora o lugar da resposta
recebe a frase do Python — nunca um vencedor apagado.

## O que ficou de pe

**A linha completa, com o par de procedencia nos dois niveis certos.** O rotulo
"informado por voce no `config.toml`" e POR LINHA; o instante em que o programa
LEU a configuracao continua em nivel de REGIAO, onde o 02-01 o pos. As tres
candidatas de "quando" e o destino de cada uma estao escritas no `index.html`,
com o contraste que torna o vao necessario: o servidor e construido UMA vez
(`dashboard.py:799`) e e la que a configuracao e lida, enquanto
`ler_o_cambio` e chamado DENTRO do atendimento de cada pedido
(`dashboard.py:543`) — o valor velho sem sinal e um modo de falha **do
`config.toml`, e nao do cambio**, e e por isso que o cambio nunca precisou desta
linha.

**Os seis estados desenhados, e nenhum mudo.** Cada um tem regra propria; o
empate ganhou copia na marcacao (ver Deviations), e os quatro sem vencedora
recebem a frase do Python no lugar do veredito.

**A rota perdedora que nao pode sumir, provada por sonda com SETE controles.**

**A linha de R$ no mesmo agrupamento de seletores do cartao de R$**, e nao num
mecanismo paralelo — com teste que reprova o paralelo, e nao so a ausencia.

## O conjunto de reconhecimento: de TRES para SETE, e a fronteira escrita

O `_SOME_DA_TELA` do 02-01 reconhecia `display`, `visibility` e `opacity`. Ele
foi ampliado **no arquivo do tracer, e nao numa copia** — as sondas sao
importadas — para sete formas: mais `width`/`height` zeradas,
`content-visibility`, `clip-path` recortando a nada, e posicionamento fora da
tela. Cada uma tem **um controle proprio** (`MENTIRAS_POR_FORMA`), e as oito
folhas de mentira sao ACUSADAS.

**A fronteira esta declarada em `A_FRONTEIRA_DESTA_VARREDURA`**, com tres formas
que ela NAO pega: regra dentro de `@media`, classe aplicada por outro seletor, e
valor vindo de propriedade personalizada de nome opaco.

**Um detalhe que quase virou defeito, e ele esta medido no fonte:** sem o
`(?<![-\w])` antes de `width`, o `min-width: 0` de `.rota__lado` seria lido como
"o lado tem largura zero", e a sonda acusaria justamente a regra que MANTEM os
dois lados na tela. Ha teste do outro sentido cobrando isso.

## As provas de mutacao — NOVE, e as nove ficaram vermelhas

| Mutacao na linha de producao | Resultado |
|---|---|
| esconder a perdedora por LARGURA ZERO (forma nova, nao `display`) | 1 falha, `test_NENHUMA_regra_do_css_real_esconde_o_lado_perdedor` |
| o R$ da linha vira mecanismo PARALELO | 2 falhas, as duas do mesmo agrupamento |
| apagar a regra do estado empatado | 1 falha, `test_cada_estado_da_lista_do_PYTHON_tem_ao_menos_uma_regra` |
| a marca da vencedora vira SO COR | 1 falha, `test_a_marca_NASCE_ESCONDIDA_e_o_atributo_a_MOSTRA` |
| apagar a escrita do vao de R$ | 2 falhas: vao orfao + a guarda anti-vacuidade |
| por um `if` de nulo em volta do R$ | 1 falha |
| escrever num vao que o molde nao tem | 1 falha (elo 4, direcao 1) |
| ler propriedade que o payload nao manda | 2 falhas (elo 5 + o controle) |
| o instante da leitura migra para dentro da linha | 3 falhas |

Todas foram REVERTIDAS; a arvore volta a 69 passed e o `git status` sai limpo.

## Numeros pedidos pelo plano

- `python -m pytest tests/test_dashboard_calculadora_pagina.py -q` -> **69 testes**,
  0 falhas (pisos: 10 na tarefa 1, 22 no total).
- **Literais de cor FORA do bloco de tokens: 0 antes e 0 depois.** Dentro do
  bloco: **14**, antes e depois. A medicao e sobre os CORPOS das regras, e nao
  sobre o texto cru — assim `#cartao-reais` num seletor nunca e lido como cor.
- `node --check l2scanner/recursos/dashboard/dashboard.js` -> **sai 0**.
- `python -m pytest tests/test_firewall_dashboard.py -q` -> **13 passed**.
- `git diff --numstat requirements.txt` -> **vazio**. Nenhuma dependencia nova.
- Cerca dura intacta: o diff toca **cinco arquivos** — tres web e dois de teste.
  **Nenhum modulo Python de producao**, nenhum do workstream `mercado`.
- Escala tipografica e de espacamento: nenhum tamanho, peso ou passo novo — as
  quatro medidas e os dois pesos da Fase 1 continuam sendo os unicos.

## A rodada da suite, e o delta que e meu

Rodada unica, saida inteira: **15 failed, 6178 passed, 87 skipped**. O 02-02
mediu **6109 passed / 15 failed** na mesma arvore.

**Delta desta fase: +69 testes, 0 falhas novas.**

**Uma 16a falha apareceu na PRIMEIRA rodada e ela NAO era minha — o registro
fica aqui em vez de sumir.** `test_dashboard_servidor.py::test_um_POST_em_OUTRO_
caminho_responde_404` caiu com `RemoteDisconnected` no soquete (e nao com
assercao de conteudo), passou sozinha (78 passed) e **nao se reproduziu na
segunda rodada completa**. E instabilidade de soquete sob carga, num caminho de
POST que este plano nao toca — o diff nao tem uma linha de Python de producao.

**As 15 restantes sao PRE-EXISTENTES** (`test_janela_no_relogio.py` 7,
`test_sessao.py` 6, `test_respawn.py` 2) — subsistema de party/bosses/agenda,
fora do alcance deste plano, e ja medidas como pre-existentes no `02-01` (que
colocou a versao anterior de `config.py` no lugar e obteve resultado identico).

## Deviations from Plan

### [Regra 1 - Bug] O vao `mercado-pacote` era ORFAO, e foi removido

**Encontrado em:** Tarefa 1, ao mapear o molde para a segunda direcao do elo 4.
**O que houve:** o `<template>` tinha `data-vao="mercado-pacote"` desde o 02-01 e
**ninguem o preenchia**. Medido: `_lado_da_rota` devolve so `{"texto": ...}`, e o
`pacote_texto` e atribuido **apenas** ao lado do NPC, em `_linha_da_rota`.
**A razao de ele nao dever existir:** so o NPC vende em pacote fechado; o mercado
e o menor pedido visivel. Um vao que ninguem escreve e copia morta com cara de
campo. **O conserto:** removido, com o motivo escrito no lugar dele. A segunda
direcao do elo 4 agora prende isso.
**Commit:** `9e1dafb`.

### [Regra 3 - Bloqueio] `tests/test_dashboard_rotas_tracer.py` foi alterado

Ele nao esta em `files_modified`, e teve de ser — **e a alteracao e exatamente o
que o plano pediu**. Ampliar o conjunto de reconhecimento numa copia local
criaria as duas autoridades que a tarefa 2 existe para impedir. O `_SOME_DA_TELA`
foi ampliado **onde ele mora**, e as tres sondas continuam com UMA definicao na
suite inteira — ha teste contando as definicoes e exigindo que os dois arquivos a
chamem. Diff: +23/-2 linhas, nenhuma assercao daquele arquivo alterada.

### [Regra 2 - Funcionalidade critica] A classe `rota__empate` e a copia dela

Nao estavam na lista de artefatos do plano. **Medido no fonte:** no estado
empatado o Python manda `vencedora` **nula** e `aviso` **nulo** (`_eleger`
devolve `ROTA_EMPATADA, None, ...`, e `_linha_da_rota` so escreve `aviso` nos
quatro estados de quebra). Sem copia, a linha mostraria dois numeros, uma
diferenca pequena e NENHUMA marca — e seria lida como tela quebrada. Isso e o
retangulo mudo que a truth do plano e a placa do estado vazio da Fase 1 proibem.
A copia nasceu na MARCACAO, como o resto da regiao, e o CSS a mostra so sob o
estado.

### [Regra 1 - Bug no meu proprio teste] A sonda da marca da vencedora ficava VERDE com a marca visivel nos dois lados

**Encontrado por prova de mutacao, na tarefa 2.** A primeira versao perguntava
"existe alguma regra que fale de `rota__marca` e declare uma propriedade que nao
seja de cor?". Isso e verdade mesmo numa folha quebrada: a regra do ATRIBUTO
declara `display: block`, entao a busca a encontrava.
**A medicao:** com a regra base reduzida a `.rota__marca { margin: 0; color: ... }`
— ou seja, com "mais barato" visivel nos DOIS lados ao mesmo tempo — a suite
inteira ficava **VERDE (52 passed)**.
**O conserto:** o teste passou a medir o MECANISMO (a marca nasce fora da tela e
o atributo a traz), com controle nos dois sentidos. A mutacao agora reprova. Os
dois numeros estao escritos na docstring do teste.

### [Escolha declarada] A frase de falta e o MESMO elemento do aviso da linha, movido

O plano lista `rota__falta` como classe nova e a truth diz que a frase do Python
ocupa "o lugar da vencedora". **Nao nasceu um segundo vao:** o elemento do aviso
(`data-vao="aviso"`) desceu do topo da linha para o lugar do veredito e ganhou a
classe `rota__falta` ao lado. Uma segunda copia da mesma string na mesma linha
seria a duplicacao que esta regiao inteira recusa.
**Por que nao dentro de cada lado, onde a marca fica:** a marca e POR LADO e a
falta e DA LINHA; repeti-la nos dois lados imprimiria a mesma sentenca duas
vezes.

### [Escolha declarada] O seletor daquele estado casa por PREFIXO — uma colisao real entre duas regras da casa

**Duas sondas pre-existentes ACUSARAM a primeira versao desta tarefa**
(`test_o_CSS_INTEIRO_nao_escreve_o_nome_da_serie` e
`test_a_palavra_que_nomeia_a_serie_NAO_esta_no_js_nem_no_css`): o DASH-05 proibe
o nome da serie sentinela de aparecer no `dashboard.css` **em qualquer lugar,
comentario inclusive**. Mas o TOKEN de um dos seis estados contem esse nome, e o
vocabulario de estados e um so, vindo do Python.

As tres saidas, com o destino de cada uma:
1. **renomear o token no Python — recusada.** Mexe num modulo fora deste plano e
   quebraria o vocabulario partilhado por causa de uma folha de estilo.
2. **deixar o estado sem regra — recusada.** Ele viraria o unico dos seis sem
   desenho proprio, que e o retangulo mudo que esta fase proibe.
3. **casar por prefixo — adotada.** Designa exatamente o mesmo estado sem
   escrever a palavra.

**O custo esta dito por extenso e MEDIDO por teste:** um setimo estado que
comecasse com as mesmas palavras herdaria a regra em silencio.
`test_o_casamento_por_PREFIXO_cobre_UM_estado_so` casa o seletor contra a lista
do Python e fica vermelho no dia em que dois casarem. E o teste que cobra uma
regra por estado deixou de ser busca literal e passou a PERGUNTAR se existe regra
que se aplica ao estado — senao o conserto obvio seria afrouxar o DASH-05, ou
seja trocar um guarda por outro.

### [Escolha declarada] `data-velho` fica NA LINHA

O plano diz "pelo mesmo atributo de dado velho que ja existe". O `data-velho` do
`<body>` responde por UMA pergunta — a serie que o destaque exibe esta velha? —
enquanto cada linha responde a sua propria, sobre a serie do item dela. Pendurar
as duas no mesmo atributo esfriaria TODAS as linhas por causa da serie do topo, o
que e uma afirmacao falsa sobre cada item. **O que e compartilhado e o que tem de
ser:** o nome do atributo, o limiar (`LIMIAR_DE_FRESCOR`, aplicado no Python) e o
token de cor. Isso tambem consome `item.velho`, que sem ele seria campo orfao.

### [Regra 1 - Bug no meu proprio comentario] A sonda literal do 02-01 acusou a minha redacao

Escrevi o identificador do vao do instante DENTRO do comentario do molde, e
`test_o_vao_do_instante_NAO_aparece_dentro_do_template` ficou vermelho — ele e
uma varredura LITERAL sobre o texto do molde, comentarios inclusive.
**A sonda esta certa e nao foi afrouxada:** a redacao mudou, e a omissao ficou
explicada no proprio comentario para ninguem "consertar" o contrario depois.

### [Divida declarada, NAO paga] O prefixo `FRASE_`/`MOLDE_`

O 02-02 combinou renomear `FRASE_DE_SEM_TAXA_DA_ADENA` "no dia em que a marcacao
for mexida por outro motivo" — e este plano mexeu. **Nao foi renomeada**, e a
razao esta escrita no `index.html`, no lugar em que o nome e citado: o simbolo
mora em `dashboard_dados.py`, fora da lista de arquivos deste plano, e o rename
tocaria quatro sitios, dois deles de teste, por uma questao de prefixo.
**Nao ha simbolo fantasma** — o nome citado na marcacao EXISTE e e o certo, que
era o defeito que o 02-02 queria evitar. O que sobra e a divida de prefixo, e ela
ficou escrita em vez de calada.

## Roteiro de verificacao humana — o teto que nenhuma assercao de fonte alcanca

As sondas leem texto de CSS, de HTML e de JS. **Elas nao abrem um navegador**, e
por isso nao sabem dizer se o resultado e legivel, se as duas colunas alinham aos
olhos, nem se a marca da vencedora chama atencao. Isto fica para a pessoa:

1. abrir o `dashboard.bat` com um item configurado e a serie dele presente:
   conferir que a vencedora esta marcada e que **a perdedora continua legivel ao
   lado**, com o numero dela;
2. apagar o `.mercado/cambio.json` e recarregar: **a linha de R$ some e o
   veredito fica** (a vencedora, a diferenca em XM e a percentual);
3. configurar um item que nao existe no CSV: a linha aparece dizendo isso, com a
   frase no lugar do veredito;
4. configurar um item com poucas ofertas: conferir que aparece a frase de falta,
   e **nao** um vencedor cinza;
5. configurar um bloco torto e conferir que o `.bat` recusa subir com a mensagem
   nomeando o campo.

## Known Stubs

Nenhum. Todos os vaos do molde sao preenchidos por codigo desta fase — e ha
teste nas DUAS direcoes exigindo exatamente isso, que foi o que encontrou o unico
orfao que existia.

## Deferred Issues

**15 falhas PRE-EXISTENTES** em `tests/test_janela_no_relogio.py` (7),
`tests/test_sessao.py` (6) e `tests/test_respawn.py` (2) — subsistema de
party/bosses/agenda, com causa ja medida e registrada no `02-01` e em
`deferred-items.md`.

**Uma instabilidade de soquete observada uma vez** em
`test_dashboard_servidor.py::test_um_POST_em_OUTRO_caminho_responde_404`
(`RemoteDisconnected` sob carga da suite inteira; nao reproduziu na segunda
rodada, passa sozinha). Nao e deste plano — o diff nao tem Python de producao —
mas fica registrada para nao ser redescoberta como novidade.

## Self-Check: PASSED

- Os 5 arquivos citados em `key-files` existem em disco.
- Os 3 commits de codigo existem: `9e1dafb`, `4b98866`, `a5a3d78`.
- A contagem de testes confere: `tests/test_dashboard_calculadora_pagina.py` ->
  **69 passed**.
- As 9 mutacoes foram executadas e REVERTIDAS; a arvore volta ao verde e o
  `git status` sai limpo.
- `git diff --numstat` da fase toca 5 arquivos, nenhum deles do workstream
  `mercado`, nenhum modulo Python de producao, e nao inclui `requirements.txt`.

## Threat Flags

Nenhuma superficie nova alem da que o `<threat_model>` do plano ja previa.
T-02-11 (nome de item no DOM) segue mitigado por molde clonado e escrita por
propriedade de texto, com as quatro sondas de marcacao verdes; T-02-12 (rota
perdedora escondida) ganhou sete controles em vez de um; T-02-13 (preco sem
procedencia) tem a linha na marcacao com controle, e nenhuma data inventada;
T-02-14 (condicao de tela duplicada em JS e CSS) tem teste com controle nas tres
formas que o defeito tomaria; T-02-SC com `requirements.txt` intacto e o firewall
de `vendor/` verde.
