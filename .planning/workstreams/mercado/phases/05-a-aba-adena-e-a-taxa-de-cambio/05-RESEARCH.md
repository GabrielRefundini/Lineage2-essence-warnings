# Phase 5: A aba Adena e a taxa de câmbio — Research

**Researched:** 2026-09-01
**Domain:** leitura de grade por molde de glifo + convivência de dois modelos de coluna no `calibration.json`
**Confidence:** HIGH nas quatro perguntas do escopo — porque as respostas saíram de **rodar o código de produção contra a fixtura versionada**, não de leitura de fonte.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **A aba Adena vira o ORÁCULO DA TAXA.** Cada linha é uma observação de câmbio, não
  de item. Com a taxa, o resto do mercado ganha um denominador comum — e a pergunta
  que ele fez ("compensa gastar adena ou vender?") passa a ter resposta.
- **Paridade total com Equipment foi RECUSADA** por ele, nesta fase. Fica disponível
  para depois.
- **`calibration.json` guarda UMA grade só** (`cal.mercado_grade = grade`,
  `calibrar_mercado.py:2721`). Calibrar adena hoje **apagaria** a de negociação.
- **Ler com o modelo errado corrompe por fator inteiro.**
- **O esquema do CSV já comporta a taxa.** Nenhuma coluna nova, nenhum bump de
  `VERSAO_DO_ESQUEMA`: `quantidade` = a adena da oferta, `total_em_centesimos` = o preço
  em XM, o unitário derivado em `Fraction(total, quantidade)` = XM por adena, **exato**.
- **Chave nova no `calibration.json` entra OPCIONAL** (`.get`), nunca obrigatória.
- **Falha fechada**: dado ilegível é descartado, nunca interpretado.
- **Nada de constante mágica**: limiar mora no `calibration.json`.
- **Um número que caiu precisa dizer que caiu.**
- **NÃO tocar** `rastreador.py` nem o gate de brilho da barra própria em `visao.py`.
- **FIRE-01** continua valendo.
- **`recordings/` é somente-leitura e nunca usar glob amplo.**
- O pytest roda no **Python GLOBAL**, não no `.venv`.

### Claude's Discretion

Nada foi marcado como discrição explícita no CONTEXT.md. O que esta pesquisa trata como
espaço de recomendação é **o mecanismo** (como as duas grades convivem, como a quantidade
é obtida), nunca **o alvo** (a taxa) nem os invioláveis acima.

### Deferred Ideas (OUT OF SCOPE)

- **A margem de arbitragem** (NPC em adena contra mercado em XM) — precisa de tabela
  de preços de NPC, que é configuração.
- **A aba `busca`** (9 linhas).
- **Paridade total da Adena** com a aba Equipment — recusada pelo usuário nesta fase.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Descrição (de REQUIREMENTS.md) | O que desta pesquisa habilita a implementação |
|----|-------------------------------|-----------------------------------------------|
| **ADEN-01** | Reconhecer e ler a aba Adena **sem perder** a de negociação; hoje há uma grade só | §Q1 (segunda chave opcional `mercado_layouts`) + §Q2 (o portão vira *escolha entre moldes*, não *aceita/recusa*). O portão já **discrimina de fato**: medido `adena 0,1331` × `negociação 1,0000` contra o molde de negociação. |
| **ADEN-02** | Modelo de colunas PRÓPRIO da Adena | §Q3. Medido: `Total Price` e `5 mln increment` **caem exatamente dentro dos retângulos de negociação**; `Quantity` cai em cima de vazio; `Auction List` **não se lê com os moldes atuais em nenhum piso de brilho**. |
| **ADEN-03** | Cada linha vira observação de TAXA no CSV, sem coluna nova e sem bump de versão | §Q3 + §Q4. `COLUNAS` (`mercado_registro.py:129-136`) e `chave_da_observacao` (`:154`) já servem; a decisão que falta é **qual `chave_da_serie`** a Adena usa. |
| **ADEN-04** | Console exibe **XM por milhão de adena**, marcado como derivado, com `n` e recência | §Q4. Quatro pontos de chamada de `formatar_unitario_derivado` em `mercado_console.py` (linhas 267, 269, 443, 476) — a superfície inteira da mudança de exibição. |

</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

O `CLAUDE.md` deste repositório descreve o *stack* do projeto (Python 3.13, `mss`,
`opencv-python>=4.14,<5`, `numpy` 2.5.2, WinRT OCR, `rapidfuzz`, `requests`, `rich`,
`pydantic`, `uv`) e um bloco **"What NOT to Use"**. Os itens dele que **incidem nesta fase**:

| Diretiva do CLAUDE.md | Consequência para o plano |
|---|---|
| **`pyautogui` não entra na árvore, de forma nenhuma** (FIRE-01, "estruturalmente impossível de violar") | Nenhuma task pode adicionar dependência de síntese de input. |
| **`rapidfuzz` está no stack recomendado** | **NÃO usar nesta fase.** O prompt e o REQUIREMENTS proíbem: a métrica de similaridade do mercado é `difflib`, e o corte 0,8947 / piso 0,8837 não se afrouxam. Onde CLAUDE.md e o requisito da fase divergem, **o requisito da fase manda**. (Ver Assumptions Log A4.) |
| **"Hardcoded HSV constants in source" → proibido; todo limiar em `calibration.json`** | Vale para *limiar medido*. **Não** vale para *como o jogo escreve a palavra* — precedente escrito em `mercado_catalogo.py:108-113` (`SUFIXO_DA_GRADE`). Ver §Q3, decisão sobre onde mora `5_000_000`. |
| **`opencv-python` full (não headless)** — `cv2.selectROI`/`imshow`/`createTrackbar` são obrigatórios pelas ferramentas de calibração | A calibração da Adena continua sendo arrasto de mouse no mesmo `calibrar_mercado.py`. |
| **Contour detection para barra é proibido** | Não incide (mercado não usa barra). |

---

## Summary

A fase é **muito menor do que o CONTEXT temia, e o obstáculo real está em outro lugar**.

Rodei o pipeline de produção (`ler_celula_de_numero`, `ler_celula_de_quantidade`,
`segmentar_glifos_no_brilho`, `linha_ocluida`) contra `tests/fixtures/mercado/janela_adena_f014.png`
— a janela Adena completa, 1720×1392, bit-idêntica a `scroll/frame_000014`, já versionada —
usando `tests/fixtures/mercado/calibracao_de_fixture.json`. Três resultados mudam o plano:

1. **A geometria da Adena é a MESMA da negociação, exceto duas colunas.** Cabeçalho no mesmo
   `dy=224`, grade no mesmo `dy=256`, 10 linhas de 45 px, largura 944. As colunas `Total` e
   `Unitário` de negociação leem a Adena **exatamente**, sem tocar num pixel de calibração:
   `62,00 / 62,00`, `64,99 / 64,99`, `65,00`, `66,00`, `67,00`, `68,00`, `68,50`, `70,00`, `70,00`.
   A coluna `Quantity` cai sobre vazio e devolve `None` — falha fechada, de graça.

2. **A coluna `Auction List` NÃO se lê com os moldes de dígito atuais, em piso de brilho nenhum.**
   Varri 180, 200, 210, 220, 230, 240, 250: em 180-200 os dígitos de lá saem 5-6 px de largura
   (os moldes têm 4); em 210+ o `0` se parte em dois runs de 1-2 px. `ler_celula` devolve `None`
   nas dez linhas, em todos os pisos. O texto da Auction List é **mais claro e mais grosso**
   (dígitos p99 = 246) que o das colunas de moeda (Vmax 226-230), de onde os moldes foram cortados.
   O molde de palavra `Adena` (10×35, cortado no piso 120) também não corresponde: no piso 180
   a palavra segmenta em **quatro** runs (14, 6, 5, 6), não num blob de 35 px.

3. **A fixtura contém um defeito de leitura ativo, silencioso, e ele é a justificativa da fase.**
   Na linha 5 — a linha destacada, em ciano — a tela diz `135,00` (confirmado no pixel, máscara
   no piso 180 legível a olho) e `ler_celula_de_numero` devolve **13588**. Dois `0` viraram `8`:
   é o par `0`×`8`, a margem mais estreita do sistema (0,0370), disparando de verdade. A gramática
   passa (`135,88` é válido), a sonda de oclusão não pega (`linha_ocluida` = False nas dez linhas),
   e a guarda de cruzamento está **desligada** (`mercado_tolerancia_do_cruzamento: None`).
   Hoje isso iria para o CSV como taxa 135,88 — plausível e errada.

**Primary recommendation:** a quantidade da Adena **não se lê da coluna `Auction List`** — ela se
**deriva das duas colunas de moeda que já leem perfeitamente**: `quantidade = 5.000.000 × round(total / incremento)`,
aceita apenas quando `|total − n × incremento| ≤ n × LIMITE_DERIVADO_POR_UNIDADE`. Esse critério
usa a função que **já existe** (`limite_derivado_do_cruzamento`, `mercado_leitura.py:1027-1051`),
com a derivação escrita ao lado, e **discrimina os dois casos difíceis conhecidos**: aceita o
`133,33 / 66,66` do CONTEXT (resíduo 1 ≤ limite 1) e **rejeita o `13588` da fixtura** (resíduo 88 > limite 1).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Reconhecer QUAL aba está na tela | `mercado_pagina.LeitorDePagina._layout_confere` | `mercado_leitura.casamento_do_cabecalho` | O portão de layout já é o único dono dessa pergunta (D-11); nada mais no sistema sabe distinguir abas. |
| Guardar os DOIS modelos de coluna | `calibracao.Calibracao` (campo novo, opcional) | `calibrar_mercado` (escreve) | Precedente escrito: `banner_manutencao`, `tiat_chat`, as 14 chaves de mercado — todas opcionais, `VERSAO_DO_ESQUEMA` intacta em 2. |
| Ler os números da linha | `mercado_leitura.ler_celula_de_numero` | — | Já lê a Adena corretamente. **Não mexer.** |
| Obter a quantidade de adena | `mercado_leitura` (função nova, pura) | — | Deriva de duas leituras que já existem; não é I/O nem geometria. |
| Conferir a aritmética da linha | `mercado_leitura.limite_derivado_do_cruzamento` | `residuo_do_cruzamento` | Já existem, com a derivação escrita. Reuso, não mecanismo novo. |
| Decidir a identidade da série | `mercado_catalogo.chave_da_serie` **ou** sentinela do layout | `mercado_registro.chave_da_observacao` | Decisão do planejador — ver "Decisões que o planejador precisa tomar", D-A. |
| Persistir a observação | `mercado_registro.RegistroDeObservacoes` | — | **Não muda.** `COLUNAS` já comporta a taxa. |
| Calcular menor/mediana/tendência | `mercado_analise` | — | **PURO, e não pode saber de aba nenhuma.** `Fraction(total, quantidade)` já é XM por adena. |
| Exibir na unidade útil | `mercado_console` | `mercado_modo` | Único lugar que pode saber "aqui a unidade é o milhão". |
| Calibrar a aba Adena | `l2scanner/calibrar_mercado.py` (`--layout adena`) | — | A flag já existe (`:2839-2841`), com os três valores. |

---

## Standard Stack

### Core

**Nenhuma biblioteca nova. FIRE-01.** Tudo que a fase precisa já está na árvore e já foi medido.

| Peça já existente | Onde | Papel nesta fase | Estado |
|---|---|---|---|
| `casamento_do_cabecalho` | `mercado_leitura.py:1876-1901` | Discriminar Adena × negociação | **Já discrimina.** Ver §Q2. |
| `cabecalho_de_calibracao` | `mercado_visao.py:791+` | Desempacotar molde de cabeçalho, com `layout` obrigatório dentro | Serve aos dois layouts sem mudança |
| `ler_celula_de_numero` | `mercado_leitura.py:862-906` | Ler `Total Price` e `5 mln increment` | **Já lê a Adena exatamente.** Ver §Q3. |
| `numero_valido` / `centesimos_de_moeda` / `inteiro_de_quantidade` | `:410`, `:363`, `:392` | Gramática travada do número | Já documentam `5,000,000 Adena` como caso |
| `limite_derivado_do_cruzamento` + `LIMITE_DERIVADO_POR_UNIDADE = 0.5` | `:1024-1051` | O critério de aceite da derivação de quantidade | **Reuso exato.** Ver §Q3. |
| `residuo_do_cruzamento` | `:1054-1073` | Aritmética inteira, sem divisão (T-02-38) | Reuso do padrão, escala nova |
| `COLUNAS` / `chave_da_observacao` | `mercado_registro.py:129-136`, `:154` | O CSV | **Zero mudança.** |
| `unitario()` → `Fraction` | `mercado_analise.py:178-206` | XM por adena, exato | **Zero mudança. Pura.** |
| `formatar_centesimos` / `formatar_unitario_derivado` | `mercado_console.py:214-241` | Exibição | Ganha irmã, não muda |
| `--layout {negociacao,adena,busca}` | `calibrar_mercado.py:2838-2846` | Calibrar a Adena | Já aceita; falta o destino da escrita |

### Alternatives Considered

| Em vez de | Poderia usar | Tradeoff |
|---|---|---|
| Derivar a quantidade das duas colunas de moeda | Cortar um **segundo conjunto de moldes de dígito** da Auction List (`mercado_templates_de_digito_da_adena`) | Fiel ao que a tela escreve, e a única rota que lê quantidades que **não** são múltiplo de 5M. Custa 10 dígitos + `,` + `Adena` de arrasto de mouse, uma chave opcional nova, e uma segunda geometria de glifo para envelhecer. **Não é preciso para a taxa.** |
| Derivar a quantidade | **OCR** da Auction List (o mesmo `ler_texto` do nome) | Barato de escrever e caro de provar: `leituras_de_nome.json` (as 3.511 leituras reproduzidas) **não contém recorte nenhum da Adena**, então o replay da Fase 2 não conseguiria afirmar a leitura sem uma varredura de OCR nova contra o motor real. |
| Uma chave `mercado_layouts` com os dois modelos | Prefixar chaves (`mercado_grade_adena`, `mercado_coluna_do_nome_adena`, …) | ~8 chaves opcionais novas em vez de 1, e a conferência de `pecas_de_calibracao_de_mercado_faltando` teria de crescer para 23 itens com metade "opcional". Uma chave aninhada mantém a lista das 15 exatamente como está. |
| Uma sentinela `adena` como `chave_da_serie` | Deixar `agrupar` produzir a chave do nome (`10-000-000-adena#10000000`) | A trava de dígitos (D-03) partiria a Adena em **uma série por quantidade** — 5M e 10M viram séries diferentes, e a mediana da taxa nasce partida ao meio. Ver D-A. |

**Installation:** nenhuma. `uv sync` já cobre.

---

## Package Legitimacy Audit

**Não se aplica.** Esta fase **não instala pacote nenhum** — FIRE-01 e a restrição
"nenhuma dependência nova" a proíbem explicitamente, e nada no plano precisa de uma.
Nenhum nome de pacote foi buscado, sugerido ou recomendado nesta pesquisa.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### Diagrama do fluxo, com o que muda marcado

```
   janela capturada (BGR, 1720x1392)
            |
            v
   RastreioDoPainel.observar  ---> painel fechado -> nada
            |  origem (ox, oy)
            v
   [PORTAO DE LAYOUT]                            <=== MUDA (Q2)
   recorta a banda do cabecalho em (ox+grade.dx, oy+cab.dy)
   hoje:  casa contra UM molde        -> passa / RECUSA
   novo:  casa contra CADA molde      -> o layout VENCEDOR, ou RECUSA
            |
            +--> "negociacao" ------+                +--> "adena" -----------+
            |                       |                |                       |
            v                       v                v                       v
   modelo de coluna de          4 recortes      modelo de coluna da      3 recortes
   negociacao (hoje)            por linha       adena (NOVO, Q1)         por linha
                                                (sem Quantity)
            |                                            |
            v                                            v
   ler_celula_de_numero x3                     ler_celula_de_numero x2
   ler_celula_de_quantidade x1                 (Total Price, 5 mln increment)
            |                                            |
            |                                            v
            |                              quantidade = 5.000.000 x n   <=== NOVO (Q3)
            |                              n = round(total / incremento)
            |                              aceita se |total - n*incr| <= n*0,5
            |                                            |
            v                                            v
   _ler_o_nome (OCR 2x + 3x, agrupar)          chave_da_serie = sentinela   <=== DECISAO D-A
            |                                            |
            +--------------------+-----------------------+
                                 v
                          LinhaLida(chave, nome, total, quantidade, residuo)
                                 v
                    acordo entre DOIS frames (inalterado)
                                 v
                    RegistroDeObservacoes -> .mercado/observacoes.csv   (SEM MUDANCA)
                                 v
                    mercado_analise: Fraction(total, quantidade)        (SEM MUDANCA, PURO)
                                 v
                    mercado_console: formatar_*                          <=== MUDA (Q4)
                    se a serie e a da adena -> "XM por milhao (derivado)"
```

### Pattern 1: chave nova entra ANINHADA e OPCIONAL, e a lista das 15 não cresce

**What:** um campo só, `mercado_layouts: dict | None = None`, carregado com
`dados.get("mercado_layouts")`, contendo os modelos **não-negociação**.

**When to use:** sempre que a fase precisar de geometria alternativa. É o precedente já
escrito três vezes em `calibracao.py` (`banner_manutencao` :234-249, `tiat_chat`/`tiat_alvo`
:252-256, o bloco de mercado :259-265), e o argumento é **literal** e vale aqui sem tradução:

> `mercado_pagina` EXIGE as chaves de mercado presentes e PARA sem elas: uma chave nova
> obrigatória deixaria o scanner morto no próximo start até o usuário rodar a recalibração.
> — `mercado_catalogo.py:154-159`, ao lado de `PISO_DO_RESTO = 0.45`

**Example:**

```jsonc
// calibration.json — o que EXISTE hoje nao se toca; isto e ACRESCIMO
{
  "versao": 2,                                  // NUNCA sobe. Ver calibracao.py:23
  "mercado_grade": { "layout": "negociacao", "dx": -427, "dy": 256, ... },
  "mercado_coluna_do_nome":       { "dx": -385, "largura": 324 },
  "mercado_coluna_da_quantidade": { "dx":  -61, "largura": 123 },
  "mercado_coluna_do_total":      { "dx":   62, "largura": 209 },
  "mercado_coluna_do_unitario":   { "dx":  271, "largura": 174 },
  "mercado_cabecalho_de_coluna":  { "layout": "negociacao", "dy": 224, "altura": 30,
                                    "largura": 944, "corte_de_brilho": 222, "bytes": "..." },

  // NOVO, OPCIONAL. Ausente => o scanner de hoje roda IDENTICO.
  "mercado_layouts": {
    "adena": {
      "grade":     { "layout": "adena", "dx": -427, "dy": 256, "largura": 944,
                     "altura": 450, "altura_da_linha": 45, "linhas_por_pagina": 10 },
      "cabecalho": { "layout": "adena", "dy": 224, "altura": 30, "largura": 944,
                     "corte_de_brilho": 222, "bytes": "..." },
      "limiar_do_cabecalho": 0.73,
      "colunas": {
        "total":    { "dx":  62, "largura": 209 },
        "unitario": { "dx": 271, "largura": 174 }
        // sem "nome", sem "quantidade" — a Adena nao tem coluna de quantidade,
        // e a Auction List NAO se le com os moldes atuais (medido, ver Pitfall 2)
      }
    }
  }
}
```

**O que custa** (dito por inteiro, porque a pergunta foi feita):

- **Uma segunda verdade sobre `dx`/`dy`/`altura_da_linha`.** Medido: são **idênticos** aos de
  negociação hoje. Duas cópias do mesmo número envelhecem separadas — é o argumento que
  `_banda_do_cabecalho` (`mercado_pagina.py:693-698`) já escreve para não gravar o `dx` duas vezes.
  *Mitigação barata:* o bloco `adena` grava só o que **difere** e herda o resto de `mercado_grade`,
  com `.get(...)` caindo no valor de negociação. Custa uma linha de leitura e mata a divergência.
- **Uma superfície de validação nova.** `calibracao.py:997-1210` valida `mercado_grade` e
  `mercado_cabecalho_de_coluna` campo a campo. O bloco novo precisa da mesma disciplina, ou entra
  como dict cru não conferido — e um `bytes` hex corrompido lá dentro faria `cabecalho_de_calibracao`
  levantar **dentro do construtor do leitor**, que hoje é o caminho que vira feature OFF com aviso.
- **`pecas_de_calibracao_de_mercado_faltando` NÃO cresce.** Essa é a economia: as 15 continuam 15,
  a "única verdade sobre calibrado para mercado" (`mercado_pagina.py:110-197`) continua uma só, e
  o `--mercado` continua subindo em uma instalação que nunca calibrou a Adena.

### Pattern 2: o portão de layout vira ESCOLHA, e continua falhando fechado

**What:** `_casamento_do_layout` devolve hoje `bool`. Passa a devolver `str | None` — o nome do
layout que **venceu** o casamento, ou `None`.

**When to use:** só aqui. É a única função do sistema que sabe qual aba está na tela.

**Regra que não pode ser afrouxada:** vencer é `score >= limiar` **e** ser o maior score. Empate,
ou nenhum acima do limiar → `None` → nenhuma linha lida. O latch de log (`_layout_ja_recusado`,
`:660-671`) continua: a mensagem sai quando o **veredito muda**, não a cada tick.

**Example:**

```python
def _casamento_do_layout(self, janela, origem) -> str | None:
    """O layout que a banda do cabecalho AFIRMA, ou None. Falha FECHADA.

    ESCOLHA, E NAO SOMA DE PORTOES: o vencedor e o de MAIOR score entre os que
    passam do proprio limiar. Aceitar "o primeiro que passou" faria o veredito
    depender da ordem de iteracao do dict — e a ordem de um dict lido de JSON e
    a ordem em que o usuario calibrou, que nao e criterio de nada.

    O VAO E ENORME E ELE ESTA MEDIDO, em `casamento_do_cabecalho` (:1886-1895):

        molde de negociacao  x  banda de negociacao (Goods)       1,0000
        molde de negociacao  x  banda de negociacao (Unit price)  1,0000
        molde de negociacao  x  banda de ADENA                    0,1331
        molde de negociacao  x  banda de BUSCA                   -0,0027

    0,1331 contra 1,0000 nao e zona cinzenta: e um vale de oito decimos, e o
    limiar 0,73 cai no meio dele. O molde de adena contra a banda de negociacao
    PRECISA SER MEDIDO PELA FERRAMENTA e escrito aqui — a simetria e provavel,
    nao provada. Ver Assumptions Log A1.
    """
    banda = self._banda_do_cabecalho(janela, origem)
    if banda is None:
        return None
    vencedor, melhor = None, None
    for nome, cab, molde, limiar in self._layouts_calibrados():
        if molde is None or not limiar:
            continue
        score = casamento_do_cabecalho(banda, molde, int(cab["corte_de_brilho"]))
        if score < float(limiar):
            continue
        if melhor is None or score > melhor:
            vencedor, melhor = nome, score
        elif score == melhor:
            return None          # EMPATE NAO E VEREDITO.
    return vencedor
```

### Anti-Patterns to Avoid

- **Ler a Adena com o modelo de negociação "porque a geometria bate".** Bate para `Total` e para o
  incremento; **não** bate para a semântica. O `5 mln increment` normalizado por unidade daria uma
  taxa 5.000.000× errada. A geometria coincidir é conveniência de calibração, nunca licença de leitura.
- **Fazer `mercado_analise` perguntar "é a aba Adena?".** O módulo é puro e o CONTEXT o protege
  explicitamente. Um `if` de aba ali contamina menor/mediana/tendência para sempre.
- **Subir `VERSAO_DO_ESQUEMA` para 3.** `carregar` recusa qualquer versão diferente
  (`calibracao.py:733-736`): isso apagaria os 13 moldes de glifo e as 3 âncoras que só a mão do
  usuário produz. O comentário em `:259-265` diz isso com todas as letras.
- **Afrouxar o piso de brilho para fazer a Auction List ler.** Varrido: 180, 200, 210, 220, 230,
  240, 250. Nenhum funciona (Pitfall 2). Baixar o piso troca um defeito por outro — é o mesmo
  aviso que `ler_glifos` já escreve em `:723-726`.
- **Fabricar uma tolerância nova para o cruzamento da Adena.** O 0,5 já existe, derivado, com a
  conta ao lado (`:1027-1051`). Um número novo aqui seria a constante mágica que o projeto recusa.

---

## Don't Hand-Roll

| Problema | Não construa | Use | Por quê |
|---|---|---|---|
| Distinguir a aba na tela | comparação de largura de coluna, contagem de células, heurística de cor | `casamento_do_cabecalho` + um segundo molde | O vão está **medido**: 1,0000 × 0,1331. Qualquer heurística nova nasce sem medição. |
| Parsear `5,000,000` e `62,00` | regex de número | `numero_valido` + `centesimos_de_moeda` + `inteiro_de_quantidade` | A gramática **já cita a Adena como caso** (`:877-883`, `:366-369`) e já pega glifo perdido/a mais. |
| O critério de aceite da derivação | escolher uma tolerância | `limite_derivado_do_cruzamento` | Não é escolha, é consequência aritmética do arredondamento da tela. E discrimina os dois casos difíceis (§Q3). |
| Aritmética da conferência | `float`, divisão | multiplicação cruzada em `int` | T-02-38, escrito em `residuo_do_cruzamento:1061-1063`. Um resíduo de `1e-13` viraria divergência. |
| A taxa exata | dividir em `float` | `Fraction(total, quantidade)` | `mercado_analise.py:185-206`. Já existe, já ordena, já entra em `median_low` sem perder um bit. |
| Formatar dinheiro | `f"{x:.2f}"` | `formatar_centesimos` | `mercado_console.py:214-223`. O formato do jogo é `1.480,00`. |
| Dedup da observação | comparar linhas | `chave_da_observacao` | Já é `(série, total, quantidade)` — exatamente o que a taxa precisa. |

**Key insight:** esta fase quase não tem código novo. Tem **uma escolha de layout**, **uma derivação
de quantidade** e **uma linha de formatação**. Tudo o mais é reuso de peça medida. A tentação cara é
reescrever a leitura da Adena "porque é outra aba" — e a medição diz que 2 das 3 colunas já leem certo.

---

## Runtime State Inventory

Fase de leitura nova sobre estado de calibração existente. Inventário obrigatório.

| Categoria | O que encontrei | Ação necessária |
|---|---|---|
| **Dado armazenado** | `.mercado/observacoes.csv` (dado real do usuário, **proibido escrever**) e `.mercado/` catálogo de séries. Se a Adena entrar com `chave_da_serie` derivada do nome, ela cria séries novas no catálogo do usuário — **irreversíveis para o CSV**. Se entrar com sentinela, cria **uma** série. | Decisão D-A. Nenhuma migração de dado existente: nada no CSV de hoje é da Adena (o portão recusou tudo, sempre). |
| **Config de serviço vivo** | `calibration.json` na máquina do usuário — **fora do git**, contém 13 moldes de glifo e 3 âncoras que só a mão dele produz. **Proibido escrever nesta fase.** | A calibração da Adena é ação do **usuário**, rodando a ferramenta. Nenhuma task pode escrever ali. |
| **Estado registrado no SO** | Nenhum. O `--mercado` é processo de linha de comando, sem tarefa agendada nem serviço. Verificado: `mercado_modo.py` não registra nada. | Nenhuma. |
| **Segredos / variáveis de ambiente** | Nenhum. O caminho da Adena não toca Chatwoot, `.env`, nem `CHATWOOT_API_TOKEN`. | Nenhuma. |
| **Artefatos de build** | Nenhum. Sem `pyproject` novo, sem entry point novo, sem egg-info. `pytest` roda no **Python global**, não no `.venv` — então nem reinstalação há. | Nenhuma. |

**A pergunta canônica** — *depois que todo arquivo do repo estiver atualizado, que sistema em
tempo de execução ainda tem o estado antigo?* — tem **uma** resposta aqui: **o `calibration.json`
do usuário, que não terá o bloco `adena` até ele rodar a ferramenta.** É por isso que a chave
tem de ser opcional, e é por isso que o caminho "chave ausente" precisa de teste próprio:
**um clone sem `mercado_layouts` tem de ler negociação byte a byte como hoje.**

---

## Common Pitfalls

### Pitfall 1: o `0`×`8` na linha destacada — ATIVO, MEDIDO, e ninguém o pega hoje

**O que dá errado:** na linha 5 de `janela_adena_f014.png` a tela diz `135,00` e
`ler_celula_de_numero` devolve **13588**.

**Por que acontece:** a linha está **destacada** (nome em verde, total em ciano, Vmax 255 contra
226-230 das linhas normais). No piso 180 os traços saem mais grossos, o miolo do `0` estreita, e
o par `0`×`8` — margem medida 0,0370, a mais estreita do sistema — cai do lado errado.

**O que NÃO pega isso hoje:**
- a gramática (`numero_valido`): `135,88` é válido — está escrito em `:422-427` que ela não pega substituição;
- a sonda de oclusão: `linha_ocluida` = **False** nas dez linhas da fixtura, conferido;
- o acordo entre dois frames: a linha continua destacada no frame seguinte, então os dois concordam **no erro**;
- a guarda de cruzamento: **desligada** (`mercado_tolerancia_do_cruzamento: None`).

**Como evitar:** a conferência do §Q3 pega. Resíduo 88 contra limite derivado 1 → linha descartada.
**E isto é a razão de a conferência da Adena ser GUARDA e não observação**, ao contrário da de
negociação: lá o resíduo é evidência registrada; aqui ele é a única rede contra uma taxa errada e plausível.

**Sinal de alerta:** uma taxa no CSV cujo `total` não é múltiplo exato do incremento vezes `n`.

> **Isto vale além da fase.** O mesmo defeito atinge a aba de negociação em qualquer linha
> destacada, e o v1 não o vê. Não é escopo desta fase consertar lá — mas **precisa estar escrito**,
> porque é um número que caiu.

### Pitfall 2: a Auction List não se lê com os moldes atuais, e nenhum piso conserta

**O que dá errado:** `ler_celula` devolve `None` nas dez linhas da Auction List.

**Por que acontece:** medido, linha 0, larguras de run por piso de brilho:

| piso | runs dos 9 dígitos de `5,000,000` | leitura |
|---|---|---|
| 180 | `4, 2, 5, 5, 6, 2, 5, 5, 6` | `None` |
| 200 | `4, 2, 5, 5, 5, 2, 5, 5, 5` | `None` |
| 210 | `4, 2, 2, 2, 2, 2, 2, 2, 2` (o `0` partiu em dois) | `None` |
| 220-240 | `4, 2, 1, 1, 1, 1, 1, 1, 2` | `None` |
| 250 | 6 runs só — o texto sumiu | `None` |

Os moldes valem `,`=1 px, dígitos=4 px, `4`=6 px (`larguras_de_molde` → `(1, 4, 6)`,
`mercado_leitura.py:503`). A Auction List desenha **mais grosso**: no piso onde os dígitos ficam
inteiros eles têm 5-6 px; no piso onde têm a largura certa, já se partiram. **Não há vale entre
as duas populações** — é o oposto exato do vale de 4 níveis que justificou `limite_de_glifo_unico`.

E o molde de palavra `Adena` (10×35, cortado com `mascara_do_sufixo` no piso **120**) não serve
para essa célula: no piso 180 a palavra segmenta em **quatro** runs (14, 6, 5, 6). Os dois estão
em máscaras diferentes por construção (`VALOR_MINIMO_DO_SUFIXO = 120` × `VALOR_MINIMO_DO_TEXTO = 180`).

**Como evitar:** não ler a Auction List nesta fase. Derivar (§Q3). Se alguém insistir, o custo real
é **um segundo conjunto de 12 moldes cortado daquela célula**, mais uma chave opcional — não um
ajuste de piso.

**Sinal de alerta:** qualquer task que diga "ler a quantidade do nome" sem dizer **com quais moldes**.

### Pitfall 3: a coluna do nome de negociação corta a Auction List na borda

**O que dá errado:** o primeiro run da Auction List começa na **coluna 0** do retângulo
`mercado_coluna_do_nome` (`dx=-385`, ou seja x=625 nesta fixtura). Os pixels claros do texto
começam em x=**624**. Margem: **−1 px**.

**Por que importa:** em negociação o texto começa em x=630 — 5 px de folga. A Adena escreve mais à
esquerda. Perder uma coluna do `1` de `10,000,000` produziria `0,000,000` — **corrupção por fator
inteiro exatamente como o ADEN-02 descreve**, e plausível.

**Como evitar:** é mais um motivo para **não** reaproveitar a coluna do nome. Se o modelo da Adena
algum dia ganhar uma coluna de nome, ela precisa de `dx` próprio, medido.

### Pitfall 4: uma chave obrigatória mata o scanner no próximo arranque

**O que dá errado:** `mercado_layouts` entrando em `pecas_de_calibracao_de_mercado_faltando`.

**Por que acontece:** essa lista é a **única verdade** sobre "calibrado para mercado"
(`mercado_pagina.py:110-197`), e o `--mercado` a transforma em **recusa de subir**
(`mercado_modo.py:256`). Uma chave a mais lá = todo usuário que não calibrou a Adena perde o mercado inteiro.

**Como evitar:** `.get`, `None` legítimo, feature OFF sem aviso (a ausência da Adena é o **estado
normal**, não uma degradação — diferente da `mercado_folga_de_cola_do_glifo`, cuja ausência custa
6,08% das linhas e por isso avisa alto).

### Pitfall 5: o `5.000.000` no `calibration.json`

**O que dá errado:** parece limiar, e "todo limiar mora na calibração".

**Por que está errado:** não é medição — é **como o jogo escreve a coluna** (`5 mln increment`).
O precedente está escrito e é literal: `SUFIXO_DA_GRADE = "-grade"` fica no fonte porque
*"nem e um numero medido: e como o jogo escreve a palavra"* (`mercado_catalogo.py:108-113`).
E quem garante que a coluna é mesmo "por 5 mln" é o **molde do cabeçalho** — o portão de layout
carrega o significado da constante. Pô-la na calibração criaria duas verdades: o molde dizendo
`5 mln increment` e um número dizendo outra coisa.

**Como evitar:** constante de módulo em `mercado_leitura`, com a derivação e o exemplo do CONTEXT
escritos ao lado.

---

## Code Examples

### Q1 — as duas grades convivendo (o carregamento)

```python
# l2scanner/calibracao.py — o CAMPO, no trilho ja escrito para banner_manutencao
#
# OPCIONAL, e por isso a VERSAO_DO_ESQUEMA SEGUE EM 2 (calibracao.py:23). O
# `carregar` recusa qualquer versao diferente da constante (:733-736), entao
# subir para 3 apagaria os 13 moldes de glifo e as 3 ancoras que so a mao do
# usuario produz — por causa de um campo que uma instalacao sem a aba Adena
# nem preenche.
#
# ANINHADO, e nao ~8 chaves prefixadas, para que
# `pecas_de_calibracao_de_mercado_faltando` continue com QUINZE itens. Aquela
# lista e a UNICA VERDADE sobre "calibrado para mercado" e ela vira recusa de
# subir em `mercado_modo.py:256` — crescer nela e desligar o mercado de quem
# nunca calibrou a Adena.
mercado_layouts: dict | None = None

# em `carregar`, ao lado das outras:
mercado_layouts=dados.get("mercado_layouts"),
```

### Q3 — a quantidade derivada, com o critério que já existe

```python
# l2scanner/mercado_leitura.py

# QUANTA ADENA CABE EM UM INCREMENTO. NAO E LIMIAR E NAO VAI PARA A CALIBRACAO,
# pela razao literal de `SUFIXO_DA_GRADE` (mercado_catalogo.py:108-113): nao e
# um numero MEDIDO, e como o jogo ESCREVE a coluna — `5 mln increment`. Quem
# garante que a coluna e essa e o MOLDE DO CABECALHO, e ele ja mora na
# calibracao: o portao de layout carrega o significado desta constante. Grava-la
# tambem criaria duas verdades sobre uma so coluna.
ADENA_POR_INCREMENTO = 5_000_000


def quantidade_de_adena(
    total: int | None, incremento: int | None
) -> tuple[int, int] | None:
    """`(quantidade_em_adena, incrementos)` da linha da aba Adena, ou `None`.

    A QUANTIDADE NAO E LIDA DA TELA, E ISSO PRECISA ESTAR ESCRITO. A coluna
    `Auction List` carrega o numero (`5,000,000 Adena`), mas ele NAO SE LE com
    os moldes de digito deste projeto: medido em `janela_adena_f014.png`, nos
    pisos de brilho 180/200/210/220/230/240/250, `ler_celula` devolve `None` nas
    DEZ linhas. Naquela celula o texto e mais claro (p99 = 246 contra 226-230 das
    colunas de moeda, de onde os moldes foram cortados) e sai 5-6 px de largura
    onde os moldes tem 4; subindo o piso ate a largura certa, o `0` se PARTE em
    dois runs. Nao ha vale entre as duas populacoes — e o oposto exato do vale de
    quatro niveis que justificou `limite_de_glifo_unico`.

    Entao a quantidade vem das DUAS COLUNAS DE MOEDA, que leem exatamente:
    medido na mesma fixtura, com os retangulos de NEGOCIACAO e sem tocar um pixel
    de calibracao, `Total Price` e `5 mln increment` devolveram 6200/6200,
    6499/6499, 6500, 6600, 6700, 6800, 6850, 7000, 7000.

    O CRITERIO DE ACEITE NAO E ESCOLHIDO: e `limite_derivado_do_cruzamento`, a
    funcao que ja existe (:1027-1051), com a derivacao escrita ao lado — a tela
    exibe `round(total / n, 2)`, entao cada incremento carrega no maximo meio
    centesimo de erro. So muda a UNIDADE do `n`: aqui ele conta INCREMENTOS, e
    nao unidades.

    ELE DISCRIMINA OS DOIS CASOS DIFICEIS CONHECIDOS, e sao de sinais opostos:

        ACEITAR  10M por 133,33 com incremento 66,66  (captura do usuario,
                 2026-09-01, 17h)   n = 2, residuo |13333 - 13332| = 1
                                    limite = 2 x 0,5 = 1,0   ->  1 <= 1,0  PASSA

        RECUSAR  a linha 5 de `janela_adena_f014.png`, onde a tela diz `135,00`
                 e `ler_celula_de_numero` devolve 13588 (dois `0` lidos como
                 `8` — o par mais estreito do sistema, margem 0,0370, na linha
                 DESTACADA em ciano, Vmax 255).
                                    n = 2, residuo |13588 - 13500| = 88
                                    limite = 1,0             ->  88 > 1,0  CAI

    O caso de aceitar passa RASPANDO (1 contra 1,0). Isso nao e folga: e o
    arredondamento da tela no seu pior, e nao ha espaco para apertar. Se alguem
    precisar apertar, tem de MEDIR primeiro, e a medicao precisa de material com
    o `133,33` dentro — que hoje NAO EXISTE no repositorio (ver o Assumptions Log).

    ARITMETICA INTEIRA, SEM UMA UNICA DIVISAO NO JULGAMENTO (T-02-38). O `round`
    so escolhe o candidato `n`; quem decide e a multiplicacao.

    `None` quando qualquer coluna nao leu, quando o incremento e zero, quando
    `n < 1`, ou quando o residuo estoura. Falha FECHADA em todas.
    """
    if total is None or incremento is None:
        return None
    if int(incremento) <= 0 or int(total) <= 0:
        return None
    incrementos = round(int(total) / int(incremento))
    if incrementos < 1:
        return None
    residuo = abs(int(total) - incrementos * int(incremento))
    if residuo > limite_derivado_do_cruzamento(incrementos):
        return None
    return incrementos * ADENA_POR_INCREMENTO, incrementos
```

### Q4 — a exibição, sem contaminar a análise

```python
# l2scanner/mercado_console.py

# A UNIDADE UTIL DA TAXA E O MILHAO, E ESSA E A UNICA COISA QUE A EXIBICAO
# PRECISA SABER SOBRE A ABA ADENA.
#
# `mercado_analise` continua PURO e continua sem saber de aba nenhuma: la a
# taxa ja e `Fraction(total, quantidade)` (mercado_analise.py:206), exata, e
# menor pedido / mediana `median_low` / tendencia ordenam sobre ela sem perder
# um bit. Um `if` de aba naquele modulo contaminaria as tres para sempre.
#
# POR QUE UMA FUNCAO IRMA E NAO UM PARAMETRO EM `formatar_unitario_derivado`:
# `round(Fraction(11600, 10_000_000))` vale ZERO. A taxa por unidade nao e
# pequena — ela e INEXIBIVEL em centesimos, e um parametro com default faria a
# chamada errada imprimir `0,00` com toda a confianca do mundo.
UNIDADE_DA_TAXA = 1_000_000


def formatar_taxa_derivada(taxa: Fraction) -> str:
    """XM por milhao de adena, com a marca de derivado colada.

        10.000.000 adena por 116,00 XM
          -> Fraction(11600, 10_000_000) centesimo por adena
          -> x 1.000.000 = 11600 centesimos = `116,00 XM por milhao (derivado)`

    A MARCA `(derivado)` E A MESMA REGRA DE `formatar_unitario_derivado`
    (:226-241): sem ela alguem copia a linha para o WhatsApp e o numero derivado
    vira "o que o scanner leu", que e falso. O CSV guarda `total` e `quantidade`;
    a taxa e derivacao, e o rotulo tem de dizer isso.

    O arredondamento acontece SO aqui, sobre a `Fraction` exata — a comparacao
    entre ofertas ja aconteceu, e aconteceu sem perder um bit.
    """
    return (
        f"{formatar_centesimos(round(taxa * UNIDADE_DA_TAXA))} "
        f"XM por milhao de adena (derivado)"
    )
```

**Onde ela entra:** os quatro pontos que hoje chamam `formatar_unitario_derivado` —
`mercado_console.py:267`, `:269`, `:443`, `:476`. É a superfície inteira, e o critério de escolha
é a `chave_da_serie` (decisão D-A).

---

## As quatro perguntas, respondidas

### Q1 — como duas grades convivem no `calibration.json`

**Resposta:** uma chave nova, **aninhada e opcional**, `mercado_layouts`, carregada com `.get`,
contendo só os layouts **não-negociação**. `mercado_grade` e as quatro colunas de hoje **não se
tocam** e continuam sendo a negociação.

**A razão escrita ao lado de `PISO_DO_RESTO`** (`mercado_catalogo.py:154-159`, lida como pedido):
`mercado_pagina` **EXIGE** as chaves de mercado presentes e **PARA** sem elas — uma chave nova
obrigatória deixaria o scanner morto no próximo arranque até o usuário recalibrar. O mesmo
argumento aparece em `calibracao.py:234-249` (banner) e `:259-265` (o bloco de mercado inteiro).

**Custo, por inteiro:** (a) duas verdades sobre `dx`/`dy`/`altura_da_linha`, que hoje são
**idênticas** entre os dois layouts — mitigável gravando só o que difere e herdando o resto;
(b) validação nova em `calibracao.py` para o dict aninhado, sob pena de um hex corrompido levantar
dentro do construtor do leitor; (c) **zero** crescimento em `pecas_de_calibracao_de_mercado_faltando`,
que é a economia inteira do desenho aninhado.

**Confiança:** HIGH. `[VERIFIED: l2scanner/calibracao.py:23,234-249,259-265,733-736,792,807-808]`
`[VERIFIED: l2scanner/mercado_catalogo.py:108-113,154-160]`
`[VERIFIED: l2scanner/mercado_pagina.py:110-197]`

### Q2 — o portão já sabe DISTINGUIR, ou só sabe RECUSAR?

**Resposta: ele já distingue de fato, mas só sabe **relatar** aceita/recusa.**

O mecanismo é `casamento_do_cabecalho(banda, molde, corte)` → `float`, comparado contra
`mercado_limiar_do_cabecalho`. A medição está escrita na própria docstring
(`mercado_leitura.py:1886-1895`), contra as quatro bandas versionadas, **com o molde de negociação**:

```
cabecalho_negociacao_goods.png       1,0000   PASSA
cabecalho_negociacao_unitprice.png   1,0000   PASSA
cabecalho_adena.png                  0,1331   recusa
cabecalho_busca.png                 -0,0027   recusa
```

Ou seja: **o discriminador existe, é numérico, e o vão entre Adena e negociação é de oito décimos.**
O que falta é que `_casamento_do_layout` (`mercado_pagina.py:673-686`) devolve `bool` e só conhece
**um** molde (`self._cabecalho`, singular, `:378`). A mudança é de tipo de retorno e de laço, não de mecanismo.

Confirmei que a peça relevante é mesmo o molde de cabeçalho: `cabecalho_adena.png` (30×944) casa
`janela_adena_f014.png` em **0,9999993** na posição `(583, 436)` — a **mesma** posição em que
`cabecalho_negociacao_goods.png` casa `janela_negociacao_f005.png` (0,9908). Mesma origem, mesmo
`dy=224`, mesma largura 944.

**O que falta medir:** o molde de **adena** contra a banda de **negociação**. A simetria é provável,
não provada. Ver A1.

**Confiança:** HIGH para o mecanismo e para os quatro números (estão no fonte, e reproduzi a
localização). MEDIUM para a simetria.
`[VERIFIED: l2scanner/mercado_leitura.py:1876-1901]` `[VERIFIED: l2scanner/mercado_pagina.py:633-686,688-706]`

### Q3 — o que muda no parse da Adena

**Resposta em três partes, e a primeira é a que muda o plano.**

**(a) As colunas de moeda já leem, sem calibração nova.** Rodei `ler_celula_de_numero` com os
retângulos de negociação (`total dx=62 larg=209`, `unitario dx=271 larg=174`) sobre as dez linhas
de `janela_adena_f014.png`:

| linha | `Total Price` lido | `5 mln increment` lido | tela |
|---|---|---|---|
| 0 | 6200 | 6200 | `62,00` / `62,00` ✓ |
| 1 | 6499 | 6499 | `64,99` / `64,99` ✓ |
| 2 | 6500 | 6500 | ✓ |
| 3 | 6600 | 6600 | ✓ |
| 4 | 6700 | 6700 | ✓ |
| **5** | **13588** | **6750** | **tela diz `135,00` — LEITURA ERRADA, ver Pitfall 1** |
| 6 | 6800 | 6800 | ✓ |
| 7 | 6850 | 6850 | ✓ |
| 8 | 7000 | 7000 | ✓ |
| 9 | 7000 | 7000 | ✓ |

E `ler_celula_de_quantidade` sobre a coluna `Quantity` devolve `None` nas dez — ela cai sobre vazio.
Falha fechada de graça.

**(b) A quantidade NÃO se extrai do nome — ela se deriva.** A extração "com falha fechada" que a
pergunta pede **não é implementável com as peças atuais**: `ler_celula` devolve `None` na Auction
List em **todos** os pisos de brilho varridos (Pitfall 2), e o molde de palavra `Adena` (piso 120)
não corresponde à segmentação da célula (piso 180). A rota que funciona é
`quantidade = 5.000.000 × round(total / incremento)`, aceita sob
`limite_derivado_do_cruzamento(incrementos)` — código completo acima.

**(c) O `5 mln increment` como conferência cruzada — é exatamente o papel que a pergunta descreve,
mas com uma diferença de STATUS que precisa estar no plano.** Em negociação, o resíduo é
**observação registrada** (a guarda está reprovada por medição, `tolerancia = None`,
`_observar_o_cruzamento:1667-1710`). Na Adena, o mesmo cálculo é **guarda**, porque é a única rede
entre o `0`×`8` e uma taxa errada e plausível no CSV. `116,00 / 2 = 58,00` é o caso trivial; o caso
que importa é o `13588`, que **está na fixtura** e que a guarda pega.

**Confiança:** HIGH — os números vieram de executar o código de produção, não de ler.
`[VERIFIED: execução de l2scanner.mercado_leitura contra tests/fixtures/mercado/janela_adena_f014.png com tests/fixtures/mercado/calibracao_de_fixture.json, 2026-09-01]`
`[VERIFIED: l2scanner/mercado_leitura.py:500-521,524-550,862-906,1024-1073]`

### Q4 — o que a exibição precisa saber

**Resposta:** exatamente **uma** coisa — que ali a unidade é o milhão. E ela entra em
`mercado_console.py`, em nenhum outro lugar.

- `mercado_analise.unitario` (`:178-206`) devolve `Fraction(total_em_centesimos, quantidade)`.
  Para `11600 / 10.000.000` isso é `Fraction(29, 25000)` — **exato**, e `menor_pedido_visivel`,
  `mediana_dos_unitarios` (`median_low`) e `tendencia` ordenam sobre ele sem uma linha nova.
  **O módulo é puro e continua sem saber de aba nenhuma.**
- `mercado_registro` não muda: `COLUNAS` (`:129-136`) e `chave_da_observacao` (`:154`) já servem.
- Muda `mercado_console`: uma irmã de `formatar_unitario_derivado`, e os quatro pontos de chamada
  (`:267`, `:269`, `:443`, `:476`) escolhem entre as duas.

**O critério da escolha é a `chave_da_serie`** — e é por isso que D-A é a decisão nº 1 da fase.
`round(Fraction(11600, 10_000_000))` vale **zero**: chamar a função errada imprime `0,00` com toda
a confiança do mundo. O default seguro é a função de adena **exigir** ser chamada explicitamente.

**Confiança:** HIGH. `[VERIFIED: l2scanner/mercado_analise.py:178-206]`
`[VERIFIED: l2scanner/mercado_console.py:214-241,267,269,443,476]`
`[VERIFIED: l2scanner/mercado_registro.py:129-136,154-171]`

### Q5 — o que o usuário precisa RODAR, e o que isso não pode quebrar

**O comando** (o `--layout` já existe, `calibrar_mercado.py:2838-2846`):

```bat
uv run python -m l2scanner.calibrar_mercado --layout adena --gravacao <pasta com a aba Adena aberta>
```

**Como conseguir a gravação, sem violar a regra de `recordings/`:** o próprio gravador do projeto,
com a aba Adena na tela. **Não** varrer `recordings/` com glob — `pre-voo` tem 1502 PNGs.
A gravação que já contém a Adena é `recordings/20260828-055323-mercado-scroll` (**95 arquivos**,
contados com um `ls` único), e o frame conhecido é `frame_000014.png`, já versionado como
`tests/fixtures/mercado/janela_adena_f014.png`. Para desenvolver e testar, **use a fixtura** — ela
é bit-idêntica e está no git.

**O que a calibração da Adena NÃO pode quebrar** (a negociação foi conferida em campo: 353 páginas
lidas contra 2 perdidas). A ferramenta hoje escreve, **incondicionalmente**, em `main` (`:2706-2745`):
`mercado_ancora`, `mercado_molde_da_ancora`, `mercado_limiar_da_ancora`,
`mercado_geometria_da_captura`, `mercado_ancoras`, **`mercado_grade`**, as **quatro colunas**, e
(condicionalmente) `mercado_cabecalho_de_coluna` + `mercado_limiar_do_cabecalho`.

**Uma rodada `--layout adena` de hoje destrói sete dessas.** O plano precisa de um portão explícito
por layout: com `--layout` diferente de `negociacao`, a escrita vai para `mercado_layouts[<layout>]`
e **nenhuma** das chaves de topo é tocada. Precedentes de aditividade já escritos no mesmo arquivo:
o molde de cabeçalho só substitui quando houve molde novo (`:2741-2749`) e o CR-04 tirou
`mercado_templates_de_nome` do fluxo por ter apagado calibração sem perguntar (`:2752-2760`).

**O critério de aceitação que NÃO é vácuo** (a advertência do prompt): não basta "a negociação
continua funcionando". O que discrimina é **carregar o `calibration.json` depois da rodada de adena
e afirmar que as chaves de topo têm valor byte a byte igual ao de antes** — e que uma
`Calibracao` sem `mercado_layouts` produz leitura de negociação idêntica à de hoje sobre
`janela_negociacao_f005.png`. Já existe teste com esse nome e essa disciplina —
`tests/test_calibrar_nao_apaga_mercado.py` e `tests/test_calibrar_nao_apaga_identidades.py` — e o
teste novo é irmão desses, não invenção.

**Confiança:** HIGH. `[VERIFIED: l2scanner/calibrar_mercado.py:2706-2760,2838-2846]`
`[VERIFIED: ls recordings/20260828-055323-mercado-scroll | wc -l → 95]`
`[VERIFIED: tests/test_mercado_replay.py:23,99-108 — a proveniência da fixtura é afirmada por teste]`

---

## O material, e se ele contém o pior caso

A advertência do prompt vale a fase inteira, então isto vem por escrito, item a item.

| Medição que esta pesquisa propõe | Material que a sustenta | Contém o pior caso? |
|---|---|---|
| **As colunas de moeda leem a Adena com os retângulos de negociação** | `tests/fixtures/mercado/janela_adena_f014.png` (versionada, bit-idêntica a `scroll/frame_000014`, proveniência afirmada por teste) + `calibracao_de_fixture.json`. 10 linhas, 20 células. | **SIM, e ele apareceu sozinho.** A linha 5 é destacada (ciano/verde, Vmax 255) e produz o `13588`. Se eu tivesse medido só as linhas "normais", teria concluído 10/10 e escrito um critério vácuo. |
| **A Auction List não se lê com os moldes atuais** | A mesma fixtura, 10 linhas × 7 pisos de brilho = 70 leituras. | **SIM.** A varredura inclui os dois lados do problema: o piso onde o glifo está gordo e o piso onde ele se parte. Não há vale entre eles. |
| **O critério `residuo ≤ n × 0,5` aceita o `133,33 / 66,66`** | **NENHUM.** Esse par vem do CONTEXT.md — uma captura da tela do usuário em 2026-09-01, **que não está no repositório**. A conta fecha na aritmética (resíduo 1 ≤ limite 1,0), mas eu **não li esses pixels**. | **NÃO. É o pior caso e ele está AUSENTE.** E ele passa **raspando** — 1 contra 1,0. Um erro de arredondamento a mais e o critério derruba a linha. **Esta é a lacuna nº 1 da fase.** |
| **O portão distingue adena de negociação** | As 4 bandas versionadas, com os números na docstring, **medidos só com o molde de negociação**. | **METADE.** A direção "molde de adena × banda de negociação" nunca foi medida. Ver A1. |
| **A grade da Adena é 10 × 45 px no mesmo `dy`** | A mesma fixtura, uma janela, uma resolução (1720×1392), uma posição de painel. | **NÃO.** `LINHAS_ESPERADAS` já diz 10 para adena, e os meus recortes em `468 + 45i` acertaram as dez linhas. Mas o painel **anda 827×831 px** e outra resolução muda tudo. É por isso que a calibração é do usuário e não do plano. |

---

## Assumptions Log

| # | Claim | Seção | Risco se errado |
|---|---|---|---|
| **A1** | O molde de cabeçalho da **adena** recusa a banda de **negociação** com folga parecida (o inverso de 0,1331) | Q2, Pattern 2 | Se o vão for assimétrico, um dos dois layouts pode ganhar o casamento na aba errada — e ler a aba errada com confiança é a corrupção por fator inteiro que o ADEN-02 nomeia. **Mitigação barata: medir as 4 bandas × os 2 moldes (8 números) e escrever a matriz no fonte, como a de hoje.** |
| **A2** | Toda oferta de adena é múltiplo de 5.000.000 | Q3 | Se não for, a derivação recusa a linha. **Falha fechada** — perde dado, não inventa. Evidência: 5M e 10M na fixtura; 10M e 15M na captura do CONTEXT. Nenhum contraexemplo. Não confirmado pelo usuário. |
| **A3** | O critério `residuo ≤ n × 0,5` aceita o `133,33 / 66,66` | Q3 | Passa **raspando** (1 contra 1,0). Se a tela **truncar** em vez de arredondar — suspeita já registrada no fonte (`:1042-1049`, `11,39 / 6` com resíduo 5 contra limite 3) — o limite precisaria dobrar, e essa mudança **tocaria a negociação também**. **Precisa de material com o caso dentro.** |
| **A4** | Onde `CLAUDE.md` recomenda `rapidfuzz` e o requisito da fase manda `difflib`, o requisito manda | Project Constraints | Se invertido, entra dependência nova (viola FIRE-01) e a métrica de similaridade muda sob o corte 0,8947 já medido. |
| **A5** | O `--mercado` deve gravar Adena e negociação no **mesmo** `.mercado/observacoes.csv` | Q4, D-A | O CONTEXT diz "sem coluna nova, sem bump" e a dedup é `(série, total, quantidade)` — dois arquivos exigiriam segundo dono e segundo contrato de cabeçalho. Não confirmado explicitamente pelo usuário. |
| **A6** | A linha 5 da fixtura é "destacada/selecionada" e não "oferta própria do usuário" | Pitfall 1 | Muda a **frequência** esperada do defeito, não a existência dele. O `13588` está medido de qualquer forma. |

---

## Open Questions

1. **O `133,33 / 66,66` não tem pixel no repositório.**
   - O que se sabe: a aritmética fecha, raspando (resíduo 1, limite 1,0).
   - O que falta: um frame da aba Adena com uma linha cujo incremento **não** divide o total
     exatamente. A fixtura versionada não tem nenhuma — todas as 9 linhas boas dela dividem exato.
   - Recomendação: **antes de fechar o critério**, pedir ao usuário uma gravação curta da aba Adena
     com a coluna `5 mln increment` ordenada, e conferir se o par aparece. Se não aparecer, o plano
     tem de dizer por escrito que o ramo "arredondamento" é **inferido da aritmética, não medido**.

2. **A leitura errada `135,00 → 13588` é dívida do v1, achada aqui.**
   - O que se sabe: reproduz na fixtura, com a calibração de fixtura, e nenhuma peneira de hoje a pega.
   - O que falta: saber se a aba de negociação também destaca linhas assim (a fixtura de negociação
     não tem nenhuma linha destacada — conferido, Vmax 215/226/230 uniformes).
   - Recomendação: **não** consertar nesta fase. Registrar como DEBT no REQUIREMENTS, com o número.
     Um número que caiu precisa dizer que caiu.

3. **A sentinela da série da Adena vai aparecer no CSV que o usuário abre no Sheets.**
   - Qual string? Ela vira `chave_da_serie` e `nome_exibido`, e é o que ele lê.
   - Recomendação: perguntar. `"adena"` como chave e `"Adena"` como rótulo é o palpite mínimo.

---

## Environment Availability

| Dependência | Requerida por | Disponível | Versão | Fallback |
|---|---|---|---|---|
| Python (global) | pytest, calibrador | ✓ | executei o pipeline nesta sessão | — |
| `opencv-python` (full) | `cv2.imread`, `matchTemplate`, `selectROI` | ✓ | importado e usado nesta sessão | — |
| `numpy` | tudo | ✓ | idem | — |
| `tests/fixtures/mercado/janela_adena_f014.png` | **toda a medição desta fase** | ✓ | 1720×1392, versionada | — |
| `tests/fixtures/mercado/cabecalho_adena.png` | o segundo molde de cabeçalho | ✓ | 30×944 | — |
| `tests/fixtures/mercado/calibracao_de_fixture.json` | rodar o leitor sem tocar o `calibration.json` do usuário | ✓ | 13 moldes, 4 colunas | — |
| `recordings/20260828-055323-mercado-scroll` | frame de origem | ✓ | 95 arquivos | usar a fixtura |
| WinRT OCR | **não é preciso nesta fase** | n/a | — | a rota derivada dispensa OCR |
| `calibration.json` do usuário | calibrar a Adena de verdade | fora do git, **proibido escrever** | — | ação manual do usuário, fora do plano |

**Sem dependência faltando e sem bloqueio.**

---

## Security Domain

Fase local, sem rede, sem entrada de usuário remoto, sem credencial. O caminho da Adena não toca
Chatwoot, `.env`, `CHATWOOT_API_TOKEN` nem qualquer I/O de rede.

| Categoria ASVS | Aplica | Controle padrão |
|---|---|---|
| V2 Autenticação | não | — |
| V3 Sessão | não | — |
| V4 Controle de acesso | não | — |
| **V5 Validação de entrada** | **sim** | O `calibration.json` é **entrada não confiável** e o projeto já o trata assim: `cabecalho_de_calibracao` (`mercado_visao.py:791-840`) valida tipo, campos, faixa e contagem de bytes antes de reformatar, e recusa a transposição. **O bloco `mercado_layouts` precisa da mesma disciplina** — um `bytes` hex corrompido ali não pode virar `raise` no meio do tick. |
| V6 Criptografia | não | — |

**Padrão de ameaça que incide:** *Tampering* — geometria de calibração corrompida (à mão, ou por
uma rodada de calibrador com o layout errado) produzindo leitura plausível e errada. Mitigação:
o portão de layout, a gramática do número, e a guarda de cruzamento do §Q3.

**A restrição de segurança do projeto** — detecção 100% passiva, nunca injetar, nunca enviar input —
não é tocada: esta fase só lê pixels de uma imagem já capturada.

---

## Sources

### Primary (HIGH)

Todos são leitura direta do repositório nesta sessão, e onde diz "medido" o código **foi executado**.

- `l2scanner/mercado_pagina.py` — `:110-197` (as 15 chaves), `:290-440` (construção), `:470-540`
  (ordem dos portões), `:633-706` (portão de layout), `:720-830` (fatia e recortes)
- `l2scanner/mercado_leitura.py` — `:212-280` (piso do sufixo, `recortar_sufixo`), `:363-449`
  (gramática e conversões), `:452-521` (`pontuar_glifos`, `larguras_de_molde`), `:524-550`
  (`limite_de_glifo_unico`), `:673-760` (`ler_glifos`), `:796-906` (`ler_celula*`), `:1024-1100`
  (limite derivado, resíduo, cruzamento), `:1214-1246` (`LinhaLida`), `:1488-1710` (`ler_linha`),
  `:1876-1901` (`casamento_do_cabecalho`, com a matriz das 4 bandas)
- `l2scanner/calibracao.py` — `:23`, `:228-265`, `:340-410`, `:733-736`, `:792-808`, `:997-1210`
- `l2scanner/mercado_catalogo.py` — `:99-160` (`DIGITOS`, `SUFIXO_DA_GRADE`, `PISO_DO_RESTO` e a
  razão da chave opcional), `:197-215`, `:387-407`, `:503-545`, `:902-911`
- `l2scanner/mercado_registro.py` — `:125-215`, `:383-512`, `:795-880`
- `l2scanner/mercado_analise.py` — `:178-206`, `:286-370`, `:428-490`, `:636-690`
- `l2scanner/mercado_console.py` — `:214-241`, `:267-269`, `:433-476`, `:667-685`
- `l2scanner/mercado_visao.py` — `:791-840` (`cabecalho_de_calibracao`)
- `l2scanner/calibrar_mercado.py` — `:150-161` (`LINHAS_ESPERADAS`), `:505-600` (`derivar_grade`),
  `:1521-1560`, `:1925-1960`, `:2690-2760` (a escrita), `:2838-2846` (`--layout`)
- `tests/test_mercado_replay.py` — `:13-56` (o inventário de material e a proveniência), `:99-108`
- `tests/fixtures/mercado/` — `janela_adena_f014.png`, `janela_negociacao_f005.png`,
  `cabecalho_adena.png`, `cabecalho_negociacao_goods.png`, `calibracao_de_fixture.json`
- `.planning/workstreams/mercado/REQUIREMENTS.md`, `ROADMAP.md`, `05-CONTEXT.md`
- `.planning/config.json` — `workflow.nyquist_validation: false` (por isso não há seção de
  Validation Architecture aqui)

### Execuções desta sessão (a origem dos números "medidos")

- `ler_celula_de_numero` / `ler_celula_de_quantidade` / `ler_celula` / `segmentar_glifos_no_brilho`
  / `linha_ocluida` / `limite_de_glifo_unico`, importados de `l2scanner.mercado_leitura`, contra
  `janela_adena_f014.png` e `janela_negociacao_f005.png` com `calibracao_de_fixture.json`
- `cv2.matchTemplate` para localizar as bandas de cabeçalho: adena 0,9999993 e negociação 0,9908,
  ambas em `(583, 436)`
- Perfis de brilho HSV-V (máximo e p99) por coluna e por linha, nos dois layouts
- Varredura de piso de brilho 180→250 sobre a célula `Auction List`

### Secondary (MEDIUM)

- `.planning/workstreams/mercado/phases/05-a-aba-adena-e-a-taxa-de-cambio/05-CONTEXT.md` — os
  números da captura de 2026-09-01 (`116,00`, `133,33 / 66,66`, `15.000.000 por 300,00`). São do
  usuário, **não estão no repositório**, e por isso sustentam A3 como *inferência*, não como medição.

### Tertiary (LOW)

Nenhuma. **Nenhuma busca na web foi feita e nenhuma era necessária:** todas as perguntas do escopo
são sobre este código.

---

## Decisões que o planejador precisa tomar

**D-A (bloqueante, e é a nº 1). Qual `chave_da_serie` a Adena usa.**
Sentinela constante (`"adena"`) → **uma** série, e menor/mediana/tendência funcionam sobre a taxa
como o CONTEXT promete. Deixar `agrupar` derivar do nome → a trava de dígitos (D-03) parte em
**uma série por quantidade** (5M ≠ 10M ≠ 15M), a mediana nasce partida, e a fase não entrega o que
foi pedido. **Recomendação: sentinela.** Ela também é o que o console usa para escolher a
formatação (Q4), então D-A decide duas coisas. **Escolher a string com o usuário** — ela aparece no
Sheets dele.

**D-B (bloqueante). Derivar a quantidade, ou cortar moldes novos?**
Recomendação: **derivar** (§Q3). É a única rota que a medição sustenta hoje, dispensa OCR, dispensa
chave nova e traz a guarda de graça. O custo honesto: perde linhas cujo `total/incremento` não fecha
dentro do limite derivado, e **nunca lê o número que a tela escreve**. Se o planejador escolher os
moldes novos, ele precisa de uma task de calibração adicional (12 recortes) e de uma chave opcional
`mercado_templates_de_digito_da_adena`.

**D-C. Guarda ou observação?** Recomendação: **guarda** na Adena (descarta a linha), **observação**
na negociação (inalterado). A justificativa está medida: sem a guarda, o `13588` entra no CSV.

**D-D. Herdar ou copiar a geometria?** `dx`, `dy`, `altura_da_linha` e `linhas_por_pagina` são
**idênticos** hoje. Herdar de `mercado_grade` com `.get` evita duas verdades; copiar é mais simples
de validar. Recomendação: **herdar o que não difere**, no argumento já escrito em `_banda_do_cabecalho`.

**D-E. Onde mora `5_000_000`?** Recomendação: **no fonte**, com a derivação ao lado, pelo precedente
literal de `SUFIXO_DA_GRADE`. Não é limiar medido — é como o jogo escreve a coluna, e quem garante a
coluna é o molde de cabeçalho que já está na calibração.

**D-F. Material.** Antes de fechar o critério de aceite, decidir se a fase **pede ao usuário** uma
gravação da aba Adena contendo uma linha de arredondamento (o `133,33 / 66,66`). Se não pedir, o
plano tem de escrever que aquele ramo é inferido e não medido. **Não escrever um critério de aceite
que só exercita as linhas que já fecham exato** — é exatamente o erro que produziu os sete critérios
vácuos desta sessão.

---

## Metadata

**Confidence breakdown:**

| Área | Nível | Razão |
|---|---|---|
| Convivência das duas grades (Q1) | HIGH | Três precedentes literais em `calibracao.py` + a razão escrita ao lado de `PISO_DO_RESTO`, lida como pedido |
| Discriminação de layout (Q2) | HIGH mecanismo / MEDIUM simetria | Os quatro números estão no fonte; a direção inversa nunca foi medida (A1) |
| Parse da Adena (Q3) | HIGH | Código de produção **executado** contra fixtura versionada; 20 células de moeda, 70 leituras de varredura de piso |
| O critério de aceite da derivação | MEDIUM | Discrimina os dois casos difíceis, mas um deles (o de aceitar) **não tem pixel no repositório** e passa raspando (A3) |
| Exibição (Q4) | HIGH | Quatro pontos de chamada localizados; a análise é pura e conferida |
| O que rodar / o que não quebrar (Q5) | HIGH | A escrita incondicional do calibrador está lida linha a linha (`:2706-2745`) |

**Research date:** 2026-09-01
**Valid until:** enquanto a calibração do usuário e a resolução 1720×1392 não mudarem. As medições
de pixel são desta janela e desta pele; o mecanismo sobrevive, os números não.
