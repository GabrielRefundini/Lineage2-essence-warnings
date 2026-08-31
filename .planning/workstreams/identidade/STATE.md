---
workstream: identidade
created: 2026-08-30
---

# Project State

## Current Position

**Status:** Fase 2 em andamento (plano 02-01 entregue, 02-02 pendente)
**Current Phase:** Phase 2 - Aprender sozinho
**Last Activity:** 2026-08-31
**Last Activity Description:** 02-01 executado: l2scanner/aprendiz.py, o elo do assinaturas_configuradas e o auto-diagnostico de D-07

## Progress

**Phases Complete:** 1/3
**Current Plan:** 02-02

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

**Stopped At:** Completado 02-01-PLAN.md
**Resume File:** .planning/workstreams/identidade/phases/02-aprender-sozinho/02-02-PLAN.md

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

## Fase 2, plano 01 entregue (2026-08-31)

O scanner grava sozinho a assinatura de quem ele nao conhece, depois de cinco
leituras seguidas com a imagem do nome estavel, e a linha continua calada.
`l2scanner/aprendiz.py` nasceu SEM RELOGIO e ja esta na tupla `MODULOS` do
portao AST. Nenhum alerta novo saiu desta fase.

### O elo que o criterio exigia, e que nao era obvio

Gravar a assinatura NAO bastava. `Rastreador.assinaturas_configuradas` e
calculado UMA vez no arranque e nasce `False` numa instalacao sem assinatura
nenhuma — que e exatamente a instalacao onde esta fase mais importa. Sem um elo
novo, a primeira pessoa aprendida seria gravada como ANONIMA no disco e
ANUNCIADA COM O NOME DE OUTRA na tela: o defeito que a Fase 1 acabou de
consertar, chegando por outra porta.

Agora o mesmo tick que grava a primeira assinatura liga a flag. E a virada muda
o regime da party INTEIRA (toda linha nao reconhecida passa a ser "Membro N", e
MORREU/RESSUSCITOU passam a ser vetados para `#linhaN`), entao ela sai no
`scanner.log` com um `log.warning`, UMA vez — depois do `log.info` do
aprendizado, porque as duas caem no mesmo tick e o log nao pode anunciar a
consequencia antes da causa.

A GARANTIA NAO E TOTAL, e isso esta escrito: o aprendizado roda DEPOIS do
`rastreador.observar` do mesmo tick, entao nas N leituras ate a primeira
assinatura existir a flag ainda e `False`. A fase ENCURTA para cinco leituras
uma janela que hoje dura a sessao inteira; ela nao a fecha.

### O numero de campo que AINDA NAO EXISTE

Nao ha medicao do ruido entre frames consecutivos, e a checagem foi feita em vez
de assumida: as duas unicas capturas de party window versionadas
(`party_ordem_original.png` e `party_com_lider.png`) sao BYTE A BYTE IDENTICAS
(0 pixels diferentes de 90828), e `recordings/` nao se materializa num clone.
O "0" que sai de compara-las nao e medida de ruido: e a mesma imagem consigo
mesma.

Por isso `celulas_toleradas` nasce ZERO, e por isso D-07 e requisito e nao
enfeite: toda recusa por instabilidade registra a DISTANCIA MEDIDA, e o resumo
com a faixa (minimo, maximo e mediana) sai no `scanner.log` quando o retrato
muda. O numero de campo vem da primeira sessao real, e o comentario do
`[identidade]` no `config.toml` diz onde acha-lo.

### Numeros medidos

  - teto de `celulas_toleradas`: 12, DERIVADO da tabela da Fase 1 (em 12 o
    reconhecedor ainda se recusa a distinguir; em 20 ja distingue). A CONDICAO
    DE VALIDADE esta escrita: a medida foi feita numa mascara de 48 pixels de
    texto, e num nick curto as mesmas 12 celulas sao 60% do sinal.
  - 300 leituras alternando duas mascaras a 7 celulas: 299 recusas e UMA linha
    de resumo no log.
  - quem conhece o acervo: `{acervo.py, aprendiz.py, __main__.py}`. `sessao.py`
    e `visao.py` continuam de fora.
  - suite: 3324 passando, 23 skipped (linha de base 3259/23).

### O que falta na fase

O plano 02-02: a prova exaustiva do ramo da MARGEM (D-02) e o T-02-18 da
confianca registrada. `Aprendizado.confianca` ja viaja e ja sai no `log.info`.

## Fase 2 entregue (2026-08-31)

Uma linha ocupada que nao casa com ninguem conhecido deixa de ser misterio
permanente: depois de 5 leituras estaveis o scanner grava a assinatura dela
sozinho, sem nome, e continua calado. Os 5 criterios do ROADMAP verificados
por mutacao do fonte, nao por leitura de teste.

### A forma do defeito da Fase 1 voltou, e foi fechada aqui

A Fase 1 destapou uma logica correta, testada, e nunca ligada em producao. A
Fase 2 repetiu a FORMA: o verificador trocou `aprendiz=aprendiz` por
`aprendiz=None` em `__main__.py` e a suite inteira — 3514 casos — ficou verde.
A feature desligada em campo, e nada acusando. Idem para
`cal.assinaturas = identidades.assinaturas` e para a passagem dos ajustes.

As tres ligacoes agora tem guarda no molde do `TestNenhumRastreadorNasceMudo`,
e cada uma foi provada matando a mutacao correspondente, uma por vez, contra a
suite inteira. `LEITURAS_PARA_APRENDER = 5` tambem estava solto (trocar por 1
deixava tudo verde) e agora esta preso junto com a DERIVACAO dele: e o mesmo
numero da familia cara de `rastreador.Ajustes` (ressurreicao e saida custam 5;
morte e entrada custam 3), porque gravar num acervo sem comando de esquecer e
a direcao cara por definicao.

### A fronteira que esta fase NAO fecha, dita em voz alta

A pessoa que sai e volta correlacionando ABAIXO de 0.75 contra a propria
entrada gravada vira mesmo uma SEGUNDA entrada. Nao ha conserto honesto sem
medida de campo do drift entre sessoes, e essa medida nao existe: as duas
capturas de party window versionadas sao BYTE A BYTE IDENTICAS, entao compara-las
mede uma imagem consigo mesma, nunca ruido. O caso esta afirmado como conhecido
e aceito (T-02-18), e o `log.info` do aprendizado passou a citar a confianca
justamente para o primeiro caso real virar numero em vez de misterio.

### Numeros medidos

Mascara 20x100 (2000 celulas), 60 pixels de texto, nick `TioMad`:

  - 12 celulas viradas -> correlacao 0.9075, ACIMA de 0.75, reconhecida
  - 42 celulas viradas -> correlacao 0.7531, ACIMA, nenhuma chave nova
  - 43 celulas viradas -> correlacao 0.7492, ABAIXO, SEGUNDA chave nasce

Uma unica celula separa as duas metades. E o segundo numero que generaliza, e
nao o primeiro: 43 celulas sao 2.15% da mascara mas 71.7% do SINAL DE TEXTO —
num nick curto a fronteira chega muito antes. E o modelo de drift usado ACENDE
celulas (60 -> 101 pixels), entao a tabela e um limite OTIMISTA: drift que
apaga texto derruba a correlacao mais rapido.

### Divida herdada pela Fase 3

  - T-02-07: um recorte contaminado pontua 0.0, passa no veto e pode ser
    aprendido. Na Fase 3 isso vira uma pergunta no WhatsApp pedindo ao usuario
    que batize uma janela de navegador.
  - T-02-18: uma entrada nunca respondida mais outra com confianca entre 0.70 e
    0.75 no log = a mesma pessoa perguntada duas vezes.
  - Armadilha: baixar `LIMIAR_DO_ORNAMENTO` abaixo de 0.75 reabre o caminho do
    operador que hoje D-02 fecha.
  - O criterio 5 (replay duas vezes) e NECESSARIO e NAO SUFICIENTE: sozinho ele
    fica verde com D-03 desligado, porque o mesmo frame produz a mesma chave e
    recebe `ja_existia`. Quem prende D-03 sao os casos de sair-e-voltar.
