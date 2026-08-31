---
slug: series-duplicadas-por-catalogo-sem-estado
workstream: mercado
created: 2026-08-31
status: investigating
severity: alta
hypothesis: >
  O agrupamento por similaridade esta CORRETO e foi medido isoladamente, mas na
  producao ele consulta um catalogo sem estado atualizado: duas leituras do MESMO
  item, no MESMO lote, criam duas series porque a primeira ainda nao estava no
  catalogo quando a segunda foi agrupada.
next_action: >
  Achar onde o catalogo e consultado no laco e por que a entrada criada na mesma
  passada nao esta visivel para a leitura seguinte.
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
