---
slug: series-duplicadas-por-catalogo-sem-estado
workstream: mercado
created: 2026-08-31
status: resolved
severity: alta
hypothesis: >
  O agrupamento por similaridade esta CORRETO e foi medido isoladamente, mas na
  producao ele consulta um catalogo sem estado atualizado: duas leituras do MESMO
  item, no MESMO lote, criam duas series porque a primeira ainda nao estava no
  catalogo quando a segunda foi agrupada.
next_action: >
  Consertado e verificado por teste. Falta a confirmacao do usuario numa sessao
  real de mercado com varias ofertas do mesmo item na mesma pagina.
---

# Duas series para o mesmo item, nascidas no mesmo carimbo

## Sintoma, sessao real do usuario 2026-08-31 17:05

`.mercado/observacoes.csv` e `.mercado/catalogo-de-nomes.csv` ficaram com DUAS
series para o mesmo item:

    4-hunter-s-stockings#4 ; +4 Hunter's Stockings   (correto)
    4-hunter-s-st-kings#4  ; +4 Hunter's St<<kings   (corrompido pelo OCR)

O mesmo aconteceu com o `+5`. **Isso divide a evidencia em silencio**: os precos
de um item ficam repartidos entre duas chaves, o `n` cai pela metade, e a mediana
passa a ser calculada sobre dado parcial sem nenhum aviso.

## A prova de que foi no MESMO lote

No `catalogo-de-nomes.csv`, as duas entradas tem `primeira_vez` **byte a byte
identico**:

    4-hunter-s-st-kings#4   17:05:48.609000   avistamentos 2
    4-hunter-s-stockings#4  17:05:48.609000   avistamentos 1
    5-hunter-s-st-kings#5   17:05:48.609000   avistamentos 1
    5-hunter-s-stockings#5  17:05:48.609000   avistamentos 2

Nao e uma que apareceu depois da outra. Nasceram juntas.

## O algoritmo NAO e o culpado — medido

`mercado_catalogo.agrupar` foi exercitado isoladamente, com a calibracao de
producao (`corte=0.8947`, `piso=0.8837`), nos DOIS sentidos:

    catalogo tem o BOM,        chega o CORROMPIDO -> agrupada em 4-hunter-s-stockings#4 (0.9268)
    catalogo tem o CORROMPIDO, chega o BOM        -> agrupada em 4-hunter-s-st-kings#4  (0.9268)

As duas assinaturas de digito sao `4`, entao a trava de digitos NAO as separa —
elas sao candidatas legitimas uma da outra, e a similaridade 0,9268 passa o corte
0,8947 com folga.

**Logo: se o catalogo consultado contivesse a primeira, a segunda teria sido
agrupada. Ele nao continha.**

## A causa do nome corrompido (contexto, nao o defeito)

O OCR na escala 3x le `Stockings` como `St<<kings` de forma SISTEMATICA (o `oc`
vira um unico glifo). Na sessao, 47 das 70 linhas descartadas foram
`discordancia-entre-escalas` — a peneira funcionando.

**Mas a peneira so pega DISCORDANCIA.** Quando as duas escalas cometem o MESMO
erro, a corrupcao passa e vira serie. Foi assim que `St<<kings` entrou.

Isso e uma limitacao conhecida do desenho, e **nao e o alvo desta sessao** — o
alvo e o agrupamento nao ter juntado as duas depois. Se o agrupamento funcionasse,
a corrupcao seria absorvida e o dado ficaria intacto.

## Restricoes

- **NAO afrouxar** a conferencia entre escalas nem o corte de similaridade: os
  dois foram medidos e o corte 0,8947 e o que impede `B-grade Gemstone` (0,9375)
  e `+3` x `+4 Dragon Belt` (0,9286) de fundirem. Mexer nele funde item real.
- **NAO tocar** `rastreador.py` nem o gate de brilho da barra propria em
  `visao.py`.
- **NAO escrever** em `.mercado/` — tem o dado real do usuario. Teste em `tmp_path`.
- **NAO commitar** `calibration.json`.
- `recordings/` e somente-leitura e NUNCA usar glob nela.
- Nao tocar `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`, `test_bosses.py`
  nem nada de `identidade`/`tiat` — outro agente trabalha neles nesta arvore.
- Nenhuma dependencia nova (FIRE-01). Nenhum `--amend`.

## Evidencia disponivel

Os dois CSV de producao existem e podem ser LIDOS (nunca escritos). A sessao do
usuario esta reproduzida no console dele e nas linhas citadas acima.


## A CAUSA, na fiacao (2026-08-31)

    LE   mercado_pagina.py:725   catalogo=self._catalogo   -- a CADA linha do laco
    ESCREVE mercado_pagina.py:785 _gravar_no_catalogo(...)  -- chamado de :503,
                                                              DEPOIS da pagina inteira

`_ler_a_pagina` (`:681`) percorre as linhas da grade e entrega a MESMA referencia
`self._catalogo` para todas elas. `_ler_o_nome` faz `entradas =
list(catalogo.values())` (`mercado_leitura.py:1574`) e NUNCA escreve de volta.
Quem escreve e `_gravar_no_catalogo`, e ele so roda em `:503`, depois de a pagina
ter sido lida INTEIRA e ter passado o acordo de dois frames.

Logo: a serie que a linha 0 cria e invisivel para a linha 1 da MESMA pagina.

### O CSV de producao confirma a pagina unica

No `catalogo-de-nomes.csv` as series se agrupam em TRES carimbos, e o terceiro
tem `primeira_vez == ultima_vez` — foi UMA pagina aceita, e nunca mais:

    17:05:11.515 -> 17:05:25.640   Agathion Alpha Hunter Sealed (+2..+7)
    17:05:31.578 -> 17:05:38.625   Breastplate / Gaiters
    17:05:48.609 == 17:05:48.609   Stockings / St«kings / Tunic   <- UMA pagina

Nessa unica pagina: `4-hunter-s-st-kings#4` (2 avistamentos),
`4-hunter-s-stockings#4` (1), `5-hunter-s-st-kings#5` (1),
`5-hunter-s-stockings#5` (2), `hunter-s-stockings#` (1). Sao varias ofertas do
MESMO item na MESMA pagina — o caso que a fiacao nao cobre.

As duas leituras identicas caindo na mesma chave (`avistamentos 2`) nao
contradizem nada: a chave de uma serie NOVA e derivada do proprio nome, sem
consultar catalogo.

### Por que ATRAVES de paginas funciona

`mercado_modo.py:439` passa `catalogo.entradas()` — um dicionario DESCONECTADO —
uma vez so, na construcao. `_gravar_no_catalogo` muta esse mesmo dicionario,
entao o estado ACUMULA de pagina para pagina. O buraco e estritamente DENTRO de
uma pagina.

## reasoning_checkpoint

    hypothesis: a linha i cria serie e a linha j>i da mesma pagina nao a enxerga,
      porque a leitura e em :725 e a escrita em :785 (chamada de :503).
    confirming_evidence:
      - le em :725 a cada linha; escreve em :785 so depois da pagina
      - `entradas = list(catalogo.values())` em mercado_leitura.py:1574, sem volta
      - producao: as quatro series do Stockings tem primeira_vez == ultima_vez
      - medido de novo aqui: similaridade 0,9268 >= corte 0,8947, assinaturas '4'
    falsification_test: um LeitorDePagina isolado, com duas linhas do MESMO item
      na MESMA pagina, tem de produzir UMA chave. Se produzir duas, confirmado.
    fix_rationale: LEVANTAR para o laco da pagina a entrada PROVISORIA que ja
      existe um nivel abaixo em `_ler_o_nome` (a 3x abre provisoria, a 2x resolve
      contra ela). A provisoria vive so durante a pagina; quem promove continua
      sendo `_gravar_no_catalogo`, entao a garantia de dois frames fica intacta.
    blind_spots: o rotulo que sobrevive e o da linha que veio PRIMEIRO — pode ser
      o corrompido. O dado fica unificado de qualquer forma; escolher rotulo nao
      e desta sessao.
    candidate_causes:
      - code/fiacao: catalogo estagnado dentro da pagina  (CONFIRMADO)
      - config: corte de similaridade                     (descartado, medido)
      - data: trava de digitos                            (descartado, ambos '4')
      - environment: um processo so                       (nao se aplica)
    and_gate: sim — precisa de (a) o catalogo estagnado E (b) duas ofertas do
      mesmo item na MESMA pagina. (b) e o gatilho, nao segunda causa.

## O padrao do projeto, de novo (vizinhanca)

1. `tests/test_mercado_pagina.py` nao tem NENHUMA mencao a `catalogo` — a fiacao
   de catalogo no nivel da pagina nao tem teste algum.
2. `test_a_serie_so_NASCE_quando_a_pagina_foi_aceita`
   (`tests/test_mercado_leitura.py:736`) so exercita ATRAVES de frames; dentro de
   uma pagina, nunca.
3. Todo teste de pagina injeta um nome CONSTANTE para todas as linhas
   (`montar_leitor(cal, "Common Fafurion Doll", "Common Fafurion Doll")`). Com
   todas as linhas lendo a MESMA string, todas derivam a MESMA chave e a divisao
   dentro da pagina fica ESTRUTURALMENTE invisivel para a suite inteira. A
   fixtura mascara o defeito.


## Resolution

    root_cause: `_ler_a_pagina` (mercado_pagina.py:681) entregava a MESMA
      referencia `self._catalogo` para todas as linhas da grade (`:725`),
      enquanto quem escreve nele — `_gravar_no_catalogo` (`:785`) — so roda em
      `:503`, depois da pagina INTEIRA e do acordo de dois frames. A serie criada
      pela linha i era invisivel para a linha j>i da MESMA passada.

    fix: um catalogo PROVISORIO da pagina (`catalogo_da_pagina =
      dict(self._catalogo)`), estendido a cada linha aceita por
      `_acrescentar_serie`. E a mesma mecanica de entrada provisoria que
      `_ler_o_nome` ja usava um nivel abaixo (a 3x abre, a 2x resolve contra
      ela), levantada para o nivel da pagina. A COPIA e o que preserva a garantia
      de dois frames: a provisoria morre com a pagina recusada, e quem promove
      para `self._catalogo` continua sendo `_gravar_no_catalogo`.
      `_acrescentar_serie` e compartilhada pelos dois chamadores para que nao
      possam divergir.

    verification:
      - reproducao: teste VERMELHO antes do conserto, com as chaves de producao
        byte a byte (`4-hunter-s-stockings#4` x `4-hunter-s-st-kings#4`); VERDE
        depois.
      - mutacao 1 — tirar `_acrescentar_serie(catalogo_da_pagina, resultado)`:
        MORTO pelo teste novo.
      - mutacao 2 — trocar `dict(self._catalogo)` por `self._catalogo`: MORTO
        pelo `test_a_serie_so_NASCE_quando_a_pagina_foi_aceita` ja existente.
        As duas metades do conserto estao presas, por testes DIFERENTES.
      - regressao: 310 testes de mercado passam
        (leitura + pagina + modo + replay).
      - suite completa: 3581 passam. As 2 falhas em `test_silenciamento.py` sao
        FANTASMA do outro agente — ele deixou `silenciar_minutos = 15 -> 9` sem
        commitar em `config.toml`, e 21:50 + 9min = 21:59 e exatamente o valor
        observado contra os 22:05 esperados. `test_silenciamento.py` nao tem
        NENHUMA mencao a mercado.
      - ruff check: limpo. (`ruff format` ja reclamava dos dois arquivos ANTES
        da minha mudanca — o projeto nao formata por ele.)
      - `.mercado/` so foi LIDO. Nada escrito fora de fixtura e teste.
      - guardrail_verdict: accepted

    files_changed:
      - l2scanner/mercado_pagina.py
      - tests/test_mercado_leitura.py

## O que este conserto NAO cobre (escrito de proposito)

- `hunter-s-stockings#` — a mesma pagina criou TAMBEM esta, sem digito nenhum.
  A trava de digitos chega antes da similaridade e separa `''` de `'4'`, entao
  ela NAO e absorvida. E a limitacao conhecida do `Lv. I` x `Lv. 1`, e nao esta.
- O ROTULO que sobrevive e o da linha que veio primeiro — pode ser o corrompido
  (`+4 Hunter's St«kings`). A identidade fica unificada e o `n` volta a ser
  honesto, que era o dano; o rotulo bonito e outra conversa.
- A corrupcao continua entrando quando as DUAS escalas erram IGUAL. Continua
  fora de escopo, e agora ela e absorvida em vez de virar serie propria.

## RESOLVIDO — verificado em campo 2026-09-01

O catalogo provisorio por pagina esta em producao. Nas sessoes reais de
2026-09-01 (mais de 500 paginas lidas ao todo) **nenhuma serie nova nasceu
partida** — o defeito era duas leituras do mesmo item na MESMA pagina criarem
duas series, e isso parou.

**As quatro series ja partidas ANTES do conserto continuam no arquivo**
(`+4`/`+5 Hunter's Stockings` contra `St«kings`, similaridade 0,9268). Elas sao
sobra, nao regressao: dado novo nao se parte mais. A ferramenta
`tools/fundir_chaves_de_serie.py` NAO as funde de proposito — ela so funde com
`nome_exibido` IDENTICO, e fundir por similaridade seria julgamento no lado
irreversivel. Documentado no README.
