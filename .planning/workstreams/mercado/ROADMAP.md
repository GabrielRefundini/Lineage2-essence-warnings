# Roadmap: L2 Party Scanner — Mercado

**Workstream:** mercado (`.planning/workstreams/mercado/`)

## Milestones

- ✅ **v1-mercado** — Fases 1-4 (fechado 2026-09-01) — [arquivo](milestones/v1-mercado-ROADMAP.md)
- 🚧 **v2-mercado** — Fase 5 em diante (em curso)

## Phases

<details>
<summary>✅ v1-mercado (Fases 1-4) — FECHADO 2026-09-01, 18/18 requisitos</summary>

- [x] Fase 1: Fundação — firewall, gravador e spike de campo
- [x] Fase 2: Leitura de página
- [x] Fase 3: Persistência de observações
- [x] Fase 4: Modo `--mercado`, análise e console

Detalhe completo em [milestones/v1-mercado-ROADMAP.md](milestones/v1-mercado-ROADMAP.md).
Requisitos em [milestones/v1-mercado-REQUIREMENTS.md](milestones/v1-mercado-REQUIREMENTS.md).

</details>

---

## v2-mercado

**Milestone:** a taxa de câmbio adena × XM Coin, e a assertividade da leitura.

**O que o v1 entregou e este parte de:** o `--mercado` lê a aba Equipment/Enhancement
(layout `negociacao`), grava em `.mercado/observacoes.csv` com dedup por conteúdo, e
responde "vale quanto agora?" com menor pedido visível, mediana `median_low` e
tendência — tudo medido em campo.

**O que o usuário pediu com urgência em 2026-09-01:** a aba **Adena**, para saber se
compensa gastar adena ou vendê-la por XM Coin.

### Phase 5: A aba Adena e a taxa de câmbio

**Goal:** o `--mercado` passa a ler a aba Adena e a registrar a TAXA (quanto custa
adena em XM Coin), sem perder a leitura da aba de negociação.

**O obstáculo, já medido:** não é a mesma grade em outro lugar da tela — é **outro
modelo de colunas**.

| negociação (funciona hoje) | Adena |
|---|---|
| `Goods` — nome do item | `Auction List` — **é a quantidade** (`10,000,000 Adena`) |
| `Quantity` | *não existe* |
| `Total` — XM Coin | `Total Price` — XM Coin |
| `Unit price` — por unidade | `5 mln increment` — por cinco milhões |

E o `calibration.json` guarda **uma grade só** (`cal.mercado_grade = grade`,
`calibrar_mercado.py:2721`): calibrar adena hoje **apagaria** a de negociação. O
calibrador já aceita `--layout adena` (`choices=("negociacao","adena","busca")`,
`LINHAS_ESPERADAS` tem os três), mas a ajuda dele diz que negociação é *"o único que
tem nome de item"* — os outros nunca tiveram modelo de coluna próprio.

**A descoberta que encolhe o trabalho:** o esquema do CSV **já comporta a taxa**, sem
coluna nova e sem bump de versão. Com `quantidade` = a adena e `total_em_centesimos` =
o preço em XM, o unitário derivado (`Fraction`) é XM por adena — exato, nunca `float`:

    10.000.000 adena por 116,00 XM
      -> 11600 / 10.000.000 = 0,00116 centesimo por adena
      -> x 1.000.000        = 11,60 XM por milhao

Logo "menor pedido visível", mediana e tendência funcionam sobre a taxa de graça. Só a
**exibição** precisa saber que ali a unidade útil é o milhão.

**Decisão do usuário (2026-09-01):** o alvo é **a taxa ao longo do tempo**, não
paridade total com a aba Equipment. A aba Adena vira o oráculo do câmbio, e o resto do
mercado ganha um denominador comum.

**Requirements**: ADEN-01 a ADEN-04 (ver REQUIREMENTS.md)
**Depends on:** v1-mercado
**Plans:** 4 plans

Plans:

- [ ] 05-01-PLAN.md — a quantidade DERIVADA (a `Auction List` não se lê) e a guarda de cruzamento que rejeita o `13588` — *onda 1*
- [ ] 05-02-PLAN.md — `mercado_layouts` opcional e o portão de layout que ESCOLHE, com a matriz medida nos dois sentidos — *onda 2*
- [ ] 05-03-PLAN.md — a taxa em XM por milhão no console, e a dívida do `13588` registrada — *onda 2*
- [ ] 05-04-PLAN.md — `--layout adena` grava aninhado e não destrói a calibração de negociação — *onda 3*

---

### Carregado do v1-mercado (não é regressão, é melhoria)

Estes vieram do fechamento do v1 e estão em REQUIREMENTS.md como DEBT-*:

- **A assertividade do OCR de nome** — o discriminador certo é vocabulário de PALAVRA,
  não similaridade de nome inteiro. Medido: 24 nomes contra 29 palavras distintas.
- **A cadeia de import** `mercado_catalogo` → `config` → `notificador` → `rastreador`
  (fecha o v1 DECLARADA ABERTA, não silenciada).
- **A moldura de 153 colunas** do destaque, que rola para fora do console.
- **`Hunteds Tunic` × `Hunter's Tunic`** (0,8889) na faixa cinzenta.
- **As 4 séries partidas** por variação de OCR, que a ferramenta de fusão não junta de
  propósito.

---

*v1-mercado fechado em 2026-09-01: 4 fases, 21 planos, 44 tasks, 18/18 requisitos.*
