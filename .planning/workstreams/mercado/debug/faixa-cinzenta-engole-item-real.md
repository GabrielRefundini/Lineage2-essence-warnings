---
slug: faixa-cinzenta-engole-item-real
workstream: mercado
created: 2026-09-01
status: investigating
severity: alta
hypothesis: >
  Dois itens REAIS que diferem por uma palavra inteira caem na faixa cinzenta e
  sao descartados para sempre. A similaridade de CARACTERES nao distingue "uma
  palavra diferente" (item diferente) de "alguns caracteres tortos" (ruido de
  OCR) — e o gabarito que calibrou piso e corte nao continha esse par.
next_action: >
  Medir se existe par (piso, corte) que separe Armor/Weapon de ruido real de OCR.
  Se nao existir, medir uma trava por PALAVRA, analoga a trava de digitos do D-03.
---

# A faixa cinzenta descarta um item real, para sempre

## Sintoma, sessao do usuario 2026-09-01 04:32

TODAS as 10 linhas recusadas por `faixa-cinzenta`, com **as duas escalas de OCR
concordando e lendo o nome CERTO**:

    linha 0 RECUSADA (faixa-cinzenta):
      2x=>>>Protecting Scroll: Enchant C-grade Weapon<<<
      3x=>>>Protecting Scroll: Enchant C-grade Weapon<<<

`lidas 0 | perdidas 7 | gravadas 0`. O OCR esta perfeito; quem erra e o criterio.

## A medida

    Protecting Scroll: Enchant C-grade Weapon
      x Protecting Scroll: Enchant C-grade Armor   =  0,8889

    piso  = 0,8837   <= 0,8889 <  corte = 0,8947  ->  FAIXA CINZENTA, descarta

O catalogo do usuario ja tem `...C-grade Armor`. Enquanto ele existir, o
`...C-grade Weapon` **nunca agrupa e nunca cria serie**. Nao e transitorio.

A faixa cinzenta tem **0,011 de largura** e o par real caiu no meio dela.

## Por que isto NAO e o defeito da oclusao de novo

A oclusao esta CONSERTADA — sumiu do log. Esta e a camada seguinte, e ela e de
CLASSIFICACAO, nao de captura.

## A forma do problema e a mesma de sempre neste projeto

`piso` e `corte` sao produzidos por `tools/medir_agrupamento_de_nome.py`. O
gabarito dele **nao continha o par `Armor` x `Weapon`** — mesma forma do
`GABARITO_LIMPAS` da oclusao: a ferramenta escolheu contra material que nao tinha
o caso dificil, e o comentario dela nao dizia isso.

## Duas direcoes a MEDIR (nenhuma escolhida)

1. **Recalibrar com o par no gabarito.** Se existir `piso < 0,8889`, o `Weapon`
   vira serie nova e o caso fecha. Mas o piso tambem separa ruido de OCR de item
   novo — baixa-lo demais faz cada leitura torta virar serie fantasma. **Medir se
   existe par (piso, corte) que sirva para os dois.**
2. **Trava por PALAVRA, analoga a trava de DIGITOS do D-03.** Hoje `+4 X` nunca
   se aproxima de `+6 X` porque a assinatura de digitos e comparada por igualdade
   EXATA antes de a similaridade opinar. O mesmo raciocinio vale aqui: `Armor` e
   `Weapon` sao tokens INTEIROS diferentes, enquanto `St<<kings` x `Stockings` e
   UM token com 2 caracteres tortos. Comparar token a token separaria os dois
   casos por MECANISMO, nao por limiar.

## Restricoes invioláveis

- **NAO subir o corte para "resolver"** — 0,8947 e o que impede `B-grade Gemstone`
  x `C-grade Gemstone` (0,9375) e `+3` x `+4 Dragon Belt` (0,9286) de FUNDIREM.
  Fusao no CSV e IRREVERSIVEL; descarte nao e. Essa assimetria e a razao da faixa.
- **NAO escolher piso a mao.** Ele sai de medicao, como todo limiar deste projeto.
- **NAO escrever** em `calibration.json` sem deixar o comando ao usuario; **NAO
  escrever** em `.mercado/`.
- **NAO tocar** `rastreador.py` nem o gate de brilho da barra propria em
  `visao.py`; nem `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`,
  `test_bosses.py` — outro agente trabalha neles nesta arvore.
- `recordings/` somente-leitura, **NUNCA glob amplo**. Nenhuma dependencia nova
  (FIRE-01) — em particular `rapidfuzz` NAO entra; a metrica e `difflib`. Nenhum
  `--amend`, nunca `git stash` (pilha compartilhada).

## Material real disponivel

`.mercado/catalogo-de-nomes.csv` e `.mercado/observacoes.csv` do usuario (LER,
nunca escrever) tem os nomes reais, incluindo os pares dificeis ja conhecidos:
`St<<kings` x `Stockings` (0,9268, mesmo item), `Hunteds Tunic` x `Hunter's Tunic`
(0,8889, mesmo item — MESMO VALOR do par Armor/Weapon, que sao itens DIFERENTES).

**Esse ultimo fato e o coracao do problema: 0,8889 significa "mesmo item" num
caso e "item diferente" no outro. Nenhum limiar sobre similaridade de caracteres
separa os dois.**
