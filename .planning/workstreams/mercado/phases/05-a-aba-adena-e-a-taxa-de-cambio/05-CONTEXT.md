# Phase 5: A aba Adena e a taxa de câmbio - Context

**Gathered:** 2026-09-01
**Status:** Ready for planning
**Mode:** decisão direta do usuário, com medição prévia

> **O USUÁRIO PEDIU ESTA FASE COM URGÊNCIA** em 2026-09-01, logo após o v1 fechar.
> A decisão de escopo abaixo é DELE, respondida a uma pergunta direta.

<domain>
## Phase Boundary

O `--mercado` passa a ler a aba **Adena** e a registrar a **TAXA** — quanto custa adena
em XM Coin — **sem perder** a leitura da aba de negociação.

**O que ela NÃO é:** paridade total com a aba Equipment. O usuário escolheu
explicitamente "a taxa de câmbio ao longo do tempo" contra "paridade total", e a razão
dele é a arbitragem: saber se compensa gastar adena ou vendê-la por XM Coin.

Requisitos: ADEN-01 (conviver com negociação), ADEN-02 (modelo de colunas próprio),
ADEN-03 (a taxa no CSV sem coluna nova), ADEN-04 (exibir em XM por milhão).

</domain>

<decisions>
## Implementation Decisions

### O alvo, decidido pelo usuário

- **A aba Adena vira o ORÁCULO DA TAXA.** Cada linha é uma observação de câmbio, não
  de item. Com a taxa, o resto do mercado ganha um denominador comum — e a pergunta
  que ele fez ("compensa gastar adena ou vender?") passa a ter resposta.
- **Paridade total com Equipment foi RECUSADA** por ele, nesta fase. Fica disponível
  para depois.

### O obstáculo, MEDIDO antes de planejar

Não é a mesma grade em outro lugar da tela — é **outro modelo de colunas**:

| negociação (funciona hoje) | Adena |
|---|---|
| `Goods` — nome do item | `Auction List` — **é a quantidade** (`10,000,000 Adena`) |
| `Quantity` | *não existe* |
| `Total` — XM Coin | `Total Price` — XM Coin |
| `Unit price` — por unidade | `5 mln increment` — por CINCO MILHÕES |

- **`calibration.json` guarda UMA grade só** (`cal.mercado_grade = grade`,
  `calibrar_mercado.py:2721`). Calibrar adena hoje **apagaria** a de negociação.
- **O calibrador já aceita `--layout adena`**
  (`choices=("negociacao","adena","busca")`, e `LINHAS_ESPERADAS` tem os três com
  10/10/9 linhas) — mas a ajuda dele diz que negociação é *"o único que tem nome de
  item"*: os outros nunca ganharam modelo de coluna próprio.
- **Ler com o modelo errado corrompe por fator inteiro.** A própria mensagem de recusa
  do v1 já avisa isto: na Adena a coluna é `5 mln increment`, normalizada por cinco
  milhões e NÃO por unidade.

### A descoberta que encolhe o trabalho

**O esquema do CSV já comporta a taxa.** Nenhuma coluna nova, nenhum bump de
`VERSAO_DO_ESQUEMA`:

- `quantidade` = a adena da oferta (ex.: `10000000`)
- `total_em_centesimos` = o preço em XM (ex.: `11600`)
- o unitário derivado em `Fraction(total, quantidade)` = XM por adena, **exato**

      10.000.000 adena por 116,00 XM
        -> 11600 / 10.000.000 = 0,00116 centesimo por adena
        -> x 1.000.000        = 11,60 XM por milhao

Logo **"menor pedido visível", mediana `median_low` e tendência funcionam de graça**
sobre a taxa. Só a EXIBIÇÃO precisa saber que ali a unidade útil é o milhão.

### O que fica fora

- **A aba `busca`** — o calibrador a conhece (9 linhas), mas ninguém pediu.
- **Enhancement e Product List** — já são lidas quando estão no layout `negociacao`;
  o que muda entre elas é o conteúdo, não a grade.
- **A margem de arbitragem calculada** (comprar de NPC por adena contra comprar por
  XM). Precisa de preços de NPC, que são configuração e não observação. Esta fase
  entrega a TAXA, que é a metade que falta; a conta vem depois.

</decisions>

<code_context>
## Existing Code Insights

- **`l2scanner/mercado_pagina.py`** — `LeitorDePagina`, o portão de layout que hoje
  RECUSA tudo que não é `negociacao`, e `RastreioDoPainel` (3 âncoras, votação).
- **`l2scanner/mercado_leitura.py`** — `ler_linha`, `LinhaLida`, a sonda de oclusão
  (banda vertical, consertada em 2026-09-01) e o acordo entre duas escalas de OCR.
- **`l2scanner/mercado_catalogo.py`** — `agrupar`, com a trava de dígitos (D-03), a
  trava por palavra (D-09) e a letra de grade na assinatura.
- **`l2scanner/mercado_registro.py`** — o CSV, cabeçalho-contrato, dedup por
  `(série, total, quantidade)`.
- **`tools/calibrar_mercado.py`** — já tem `--layout` com os três valores.

### Padrões da casa

- **Falha fechada**: dado ilegível é descartado, nunca interpretado.
- **Nada de constante mágica**: limiar mora no `calibration.json`.
- **Um número que caiu precisa dizer que caiu.**
- **Chave nova no `calibration.json` entra OPCIONAL** (`.get`), nunca obrigatória:
  uma chave obrigatória deixa o scanner morto no próximo arranque até o usuário
  recalibrar. Está escrito no fonte, ao lado de `PISO_DO_RESTO`.

### Integration Points

- **NÃO tocar** `rastreador.py` nem o gate de brilho da barra própria em `visao.py`.
- **FIRE-01** continua valendo.
- Outro agente trabalha nos workstreams `tiat`/`identidade` NESTA MESMA ÁRVORE.

</code_context>

<specifics>
## Specific Ideas

- **Números reais da tela do usuário** (2026-09-01, captura): `10,000,000 Adena` por
  `116,00`, `117,00`, `118,00`, `120,00`, `122,00`, `125,00`, `130,00`, `133,33`; e
  `15,000,000 Adena` por `300,00`. A coluna `5 mln increment` mostrava `58,00`,
  `58,50`, `59,00`, `60,00`, `61,00`, `62,50`, `65,00`, `66,66`.
- **A taxa se move MUITO**: às ~09h de 31/08 era 10M por 200,00 XM (50.000 adena por
  XM); às ~17h era 10M por 116,00 (86.207 por XM). **72% em seis horas.**
- **O `5 mln increment` é derivado** e serve de conferência cruzada, no mesmo papel do
  `residuo_do_cruzamento` de hoje: `116,00 / 2 = 58,00` para 10M.
- O pytest roda no **Python GLOBAL**, não no `.venv`.
- `recordings/` é somente-leitura e **nunca** usar glob amplo.

</specifics>

<deferred>
## Deferred Ideas

- **A margem de arbitragem** (NPC em adena contra mercado em XM) — precisa de tabela
  de preços de NPC, que é configuração.
- **A aba `busca`** (9 linhas).
- **Paridade total da Adena** com a aba Equipment — recusada pelo usuário nesta fase.

</deferred>
