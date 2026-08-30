# Phase 2: Leitura de página - Research

**Researched:** 2026-08-29
**Domain:** Leitura estruturada de uma grade de UI de jogo por template-por-dígito + OCR de campo fechado, com falha fechada
**Confidence:** HIGH nas medições (tudo abaixo foi rodado nesta sessão, no `.venv` desta máquina, contra as gravações reais); MEDIUM nas recomendações de desenho que derivam delas

> **Esta pesquisa MEDIU em vez de supor.** Nove scripts rodaram contra as 8 gravações de
> 2026-08-28 usando o código que já existe. Três medições **contradizem premissas travadas**
> e estão marcadas com 🚩 — elas são o produto principal deste documento e precisam de
> decisão humana antes do plano fechar. Nada em `recordings/` foi escrito; os scripts
> viveram no scratchpad da sessão.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Leitura do nome por OCR**

- **Duas escalas de OCR (2x e 3x) que precisam CONCORDAR; discordância descarta a linha.**
  É o desenho que `l2scanner/ocr.py` já usa e documenta (D-d, diversidade de método), e a
  medição de 2026-08-29 mostrou as escalas divergindo exatamente onde o motor erra
  (`Evolution` em 2x/3x contra `Ewlution` em 4x). Duas leituras pelo MESMO método concordam
  no mesmo erro; é por isso que a segunda opinião tem de ser um método diferente.
- **Agrupamento por `rapidfuzz.WRatio` com corte em 88, e uma FAIXA CINZENTA de 80 a 88 que
  não agrupa NEM cria série nova — a linha é descartada com aviso.** O motivo é medido na
  página real do usuário: `Common Aztac` e `Common Aztac M. Def. +200` coexistem, e um corte
  permissivo funde as duas séries. Fusão no CSV é irreversível; descarte não é.
- **O catálogo de nomes já vistos vive em ARQUIVO PRÓPRIO, ao lado do CSV de observações.**
  Não em `calibration.json`: aquele arquivo é reescrito inteiro pela ferramenta de
  calibração, e o catálogo é dado ACUMULADO — sumiria na primeira recalibração.
- **Nome novo entra DIRETO como série nova, com contagem de avistamentos e data da primeira
  vez.** Sem quarentena: a quarentena esconderia a primeira aparição, que é justamente o
  evento que o usuário quer ver. A contagem deixa ele julgar no Sheets. O acordo entre
  escalas e a faixa cinzenta já são os filtros.

**Coluna do nome e os três layouts**

- **O v1 lê SOMENTE o layout que está calibrado.** Hoje o `calibration.json` da máquina do
  usuário traz `mercado_grade.layout: "adena"`. Página de outro layout é RECUSADA com aviso
  alto, nunca lida. O spike mediu três layouts com colunas diferentes e significados
  diferentes (a aba Adena tem `5 mln increment`, que é normalizado por 5 milhões de adena e
  NÃO por unidade) — ler a coluna errada com confiança é exatamente o modo de falha que
  esta fase existe para impedir.
- **O layout é reconhecido por molde do cabeçalho de coluna, cortado SEM a seta de
  ordenação.** Medido na seção 3 do spike: a seta fica DENTRO da célula de cabeçalho e muda
  de coluna conforme o usuário ordena — um molde cortado com a seta não casa a mesma coluna
  sem ela.
- **Linha vazia é decidida por AUSÊNCIA DE CONTEÚDO dentro do retângulo da linha (sem
  ícone, sem glifo), nunca por cor de fundo.** Medido: a listra alternada da grade dá dois
  fundos diferentes para linhas cheias e dois para linhas vazias.
- **A coluna do nome é calibrada como `x` + largura relativos à ORIGEM DO PAINEL** (o canto
  superior esquerdo da faixa de título, a mesma referência de `mercado_grade`), persistida
  em `calibration.json` e marcada no mesmo fluxo propor-e-confirmar do
  `calibrar-mercado.bat`. Este é o único item da fase que toca a calibração.

**Oclusão e recusa — a lição do incidente 27x**

- **O sinal de oclusão é a FAIXA DE FUNDO ALTERNADA da linha, medida num trecho sem texto.**
  São dois valores conhecidos e opacos; qualquer outro valor significa que há algo desenhado
  por cima. **A recusa NUNCA vem da confiança do casamento** — a tooltip é SEMITRANSPARENTE,
  então um número coberto ainda produz glifos plausíveis com boa confiança e valor errado. O
  spike chamou isso de "o incidente das 27 mortes falsas, um nível acima", e está certo.
- **A recusa é por LINHA, não por página.** A tooltip cobriu até 8 linhas seguidas num frame
  medido, mas raramente todas — descartar a página inteira jogaria fora leitura boa. **A
  linha descartada NÃO conta como desacordo no estabilizador:** ela simplesmente não entra
  na comparação entre os dois frames.
- **A marcação de alvo usa o MESMO mecanismo, sem caso especial.** Ela é opaca, previsível
  (topo do painel) e cobre o cabeçalho `Goods` e o nome da linha 1 — o detector de fundo
  pega as duas sem código dedicado. Nas 47 gravações do cenário ela nunca alcançou a faixa
  de título.
- **O usuário vê a recusa como CONTAGEM no console ("li 7, perdi 3") e o motivo no log — e
  NADA no CSV.** Escrever a linha recusada no CSV misturaria descarte com dado, que é a
  confusão que a falha fechada existe para evitar.

**Estabilizador de página e cadência**

- **A comparação entre dois frames é sobre a TUPLA PARSEADA de cada linha (nome agrupado,
  total, quantidade), nunca sobre pixels.** Já travado por LEIT-03.
- **A detecção de captura congelada olha a JANELA INTEIRA, não o recorte da grade.** Esta é
  a decisão que contradiz a leitura ingênua do requisito, e ela é medida: a seção 9 do spike
  provou que o painel é BIT-ESTÁVEL ("o mundo atrás mudou completamente e o retângulo da
  âncora não mudou um bit"). Grade idêntica entre frames é o caso NORMAL de uma página
  parada; usá-la como sinal de congelamento daria falso alarme o tempo todo. O mundo atrás
  do painel é que se mexe. **3 janelas consecutivas bit-idênticas = captura congelada.**
- **A busca do painel usa memória da última posição, com rebusca a cada 5 s** (precedente
  `SEGUNDOS_ENTRE_BUSCAS_DO_DIALOGO = 5.0`), e confirmação barata por âncora a cada tick.
  Medido: a varredura custa ~45 ms numa janela de 1720x1392, e em 255 frames houve só 34
  posições distintas — o painel fica parado a maior parte do tempo.
- **Cadência de leitura: 1 Hz**, igual ao resto do scanner.

### Claude's Discretion

- Forma exata do arquivo de catálogo de nomes (colunas, cabeçalho) — desde que seja legível
  a olho nu e sobreviva a uma recalibração.
- Como o trecho "sem texto" da faixa de fundo é escolhido dentro da linha, e se ele é
  calibrado ou derivado da geometria da coluna.
- Estrutura interna dos módulos novos, nomes de função e organização dos testes.

### Deferred Ideas (OUT OF SCOPE)

- **Ler os outros dois layouts** (grade de negociação e tela de busca). Cada um exige a sua
  própria calibração de colunas; o v1 recusa o que não está calibrado.
- **Idade do anúncio** e a tela de detalhe/confirmação de compra.
- **Truncamento de nome longo com prefixo de encanto** — o usuário informou que nenhum item
  tem nome com reticências, então a população é vazia.
- **Outras janelas do Menu sobrepondo o painel** — edge case raro. O inventário NUNCA
  sobrepõe (abrir o inventário FECHA o mercado).
- **A watchlist como filtro de DESTAQUE no console** — território de ANAL-* na Fase 4.
- **Alerta de oportunidade no WhatsApp** (WAPP-02) — Out of Scope do v1.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LEIT-01 | Nome do item lido por OCR sobre o recorte da coluna do nome e agrupado por similaridade; nome desconhecido vira SÉRIE NOVA sem intervenção | §"OCR do nome" (custo 2,9/4,1 ms medido, nomes completos lidos), §"Agrupamento por similaridade" (matriz WRatio/ratio medida contra a implementação de referência do rapidfuzz 3.14.5) — **e os dois 🚩 que mostram que o predicado de acordo e o scorer travados falham na medição** |
| LEIT-02 | Preços e quantidades por template-por-dígito com falha FECHADA | §"Leitura de dígitos" — o pipeline foi rodado ponta a ponta contra 3 frames e leu 25 preços dígito a dígito sem erro; §"O limiar de glifo" mostra que `mercado_limiar_de_glifo = 0.8555` NÃO serve como piso de leitura |
| LEIT-03 | Página aceita só com dois frames consecutivos concordando nas linhas PARSEADAS; bit-idênticos = captura congelada | §"Estabilizador" — `np.array_equal` na janela inteira custa 0,89 ms medido; a comparação de tuplas é grátis |
| LEIT-05 | Recorte da COLUNA DO NOME, calibrado e persistido | §"A coluna do nome" — largura medida, e a prova de que o recorte de coluna SOZINHO **não** basta contra a tooltip |
</phase_requirements>

---

## Summary

O trabalho pesado desta fase **já está construído**. `calibrar_mercado.py` contém, escritas e
medidas, todas as primitivas do caminho de leitura de dígito: `segmentar_glifos` (projeção de
coluna sobre a máscara de brilho), `_alinhar_por_preenchimento` (o alinhamento certo para
glifos de larguras diferentes), `numeros_com_sufixo` (a assinatura "número claro + palavra
apagada" que localiza a coluna de preço) e `propor_rotulo` (o classificador argmax + margem).
Rodei esse conjunto contra três frames reais e **ele leu 25 preços dígito a dígito, sem um
erro**: `100,00`, `18,90`, `7,50`, `2,45`, `135,88`, `62,00`, `24,90`, `40,00`, `16,00`… A
Fase 2 não precisa inventar o leitor de dígitos — precisa **promover código de ferramenta a
código de produção** e resolver três coisas que a medição descobriu.

O OCR do nome também fecha com folga enorme: **2,9 ms na escala 2x e 4,1 ms na 3x** sobre o
recorte de 45×270 px da coluna do nome, e **70 ms para a página inteira** (10 linhas × 2
escalas). A cadência de 1 Hz gasta 7% do orçamento. A detecção de captura congelada na janela
inteira de 1720×1392 custa **0,89 ms** com `np.array_equal` — hash é 4 a 7 vezes mais caro e
não compra nada.

O que a medição derrubou são três premissas, e as três mudam desenho:

1. 🚩 **`rapidfuzz.WRatio` com corte 88 FUNDE as séries que a decisão foi escrita para
   separar.** Medido contra a implementação de referência do próprio rapidfuzz 3.14.5:
   `Common Aztac` × `Common Aztac M. Def. +200` = **90,00**. Pior: `+6 Agathion…` × `+4
   Agathion…` = **96,77**, e `Hardin's Soul Crystal Lv. 1` × `Lv. 3` = **96,30** — o mesmo
   96,30 que o ruído de OCR `Lv. I` × `Lv. 1` produz. Nenhum corte escalar separa os dois.
2. 🚩 **O acordo 2x==3x por igualdade de string descarta 50% das linhas legíveis.** Medido
   sobre 60 linhas de 6 frames: 30 acordos. As discordâncias são `Lv. I` vs `Lv. 1` e `Kng`
   vs `King` — ruído que o agrupamento absorveria.
3. 🚩 **O layout calibrado na máquina do usuário é `adena`, e a aba Adena NÃO TEM NOME DE
   ITEM.** Censo dos 335 frames: ~25 são Adena, ~290 são a grade de negociação. Na aba Adena
   a primeira coluna OCR sai literalmente como `'Adena'`. LEIT-01 e LEIT-05 só existem na
   grade de negociação.

**Primary recommendation:** planeje a Wave 0 como uma **onda de medição** que fecha as três
lacunas acima com ferramenta que mede (o padrão da casa), e só depois escreva o leitor. O
leitor em si é a promoção de `calibrar_mercado.py` para um módulo `mercado_leitura.py` puro.

---

## Architectural Responsibility Map

Este projeto não é multi-tier de rede; os "tiers" são as camadas do próprio scanner, e a
disciplina fundadora é que cada uma não sabe da seguinte.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Localizar o painel na janela | `mercado_visao.py` (visão pura) | — | Já existe: `localizar_painel` + `RastreioDoPainel`. Não duplicar. |
| Derivar a geometria (grade, bordas, bandas) | `mercado_geometria.py` (medição pura) | — | Já existe. A Fase 2 usa `perfil_por_mediana`/`trechos_de_nivel` para a sonda de oclusão. |
| Segmentar e classificar glifos | **módulo NOVO** `mercado_leitura.py` (transform puro) | `calibrar_mercado.py` (que passa a importar dele) | Hoje as primitivas vivem na FERRAMENTA. Produção não pode importar de um módulo que abre janela do OpenCV e lê teclado. |
| Ler o nome por OCR | `ocr.py` (já existe, sem mudança) | `mercado_leitura.py` chama | `_reconhecer` já é o caminho cru; nada a acrescentar no motor. |
| Agrupar nome contra o catálogo | **módulo NOVO** `mercado_catalogo.py` (model + file-I/O) | — | O catálogo é estado durável acumulado; a regra de agrupamento mora junto do dado que ela indexa. |
| Detectar oclusão por linha | `mercado_leitura.py` | `mercado_geometria.py` (primitivas) | É um transform de pixels → bool. Consumidor externo (DETC-02) só na Fase 4. |
| Estabilizar a página (2 frames) | **módulo NOVO** `mercado_pagina.py` (state machine) | — | Precisa de memória entre ticks; nenhum dos outros tem. |
| Detectar captura congelada | `mercado_pagina.py` | — | Olha a JANELA inteira, que só o dono do laço tem. |
| Persistir observações | **Fase 3** | — | Fronteira dura. A Fase 2 devolve um objeto `PaginaAceita` e não toca disco de observação. |
| Marcar coluna do nome / molde de cabeçalho | `calibrar_mercado.py` (o fluxo propor-e-confirmar) | `mercado_geometria.py` (a proposta medida) | Único item da fase que toca calibração (decisão travada). |

**A fronteira Fase 2 ↔ Fase 3, explicitada:** a Fase 2 termina quando existe um valor
`PaginaAceita(linhas=[LinhaLida(nome_agrupado, chave_da_serie, total_em_centesimos,
quantidade, é_serie_nova)], descartadas=N, motivos=[…])`. A Fase 2 **escreve** o catálogo de
nomes (é ela que cria a série nova); a Fase 3 **escreve** o CSV de observações. Dois arquivos,
dois donos, nenhum compartilhado. Ver §"Onde o catálogo mora".

---

## Standard Stack

### Core (já instalado — não mexer)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `opencv-python` | **4.14.0.94** | máscara, resize, `matchTemplate` | `[VERIFIED: .venv/Lib/site-packages/opencv_python-4.14.0.94.dist-info]` |
| `numpy` | **2.5.2** | toda a aritmética de pixel | `[VERIFIED: .venv/…/numpy-2.5.2.dist-info]` |
| `winrt-*` | **3.2.1** (7 namespaces) | `Windows.Media.Ocr` | `[VERIFIED: .venv/…/winrt_windows_media_ocr-3.2.1.dist-info]`; `ocr.disponivel()` devolveu `True` nesta máquina nesta sessão |
| `mss` | 10.2.0 | captura (não usada nesta fase) | `[VERIFIED: .venv]` |
| stdlib `json`, `csv`, `pathlib`, `logging`, `difflib`, `os.replace` | — | catálogo, log, escrita atômica | zero dependência |

### Supporting — a ÚNICA dependência nova candidata

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `rapidfuzz` | **3.14.5** | agrupamento de nome por similaridade | **NÃO ESTÁ INSTALADA** e não está em `requirements.txt` `[VERIFIED: .venv/Lib/site-packages listado nesta sessão; requirements.txt lido integralmente]`. Ver a análise inteira em §"Agrupamento por similaridade" antes de adicionar — a medição sugere que o que se precisa dela pode não valer a dependência. |

**Custo de adicionar `rapidfuzz`, medido:** wheel `rapidfuzz-3.14.5-cp312-cp312-win_amd64.whl`,
**1,5 MB**, `License-Expression: MIT`, `Requires-Python: >=3.10`, e **zero dependências de
runtime obrigatórias** (`Requires-Dist: numpy; extra == "all"` — só no extra, e numpy já está
instalado) `[VERIFIED: METADATA extraído do wheel baixado do PyPI nesta sessão]`. Não há nada
da banlist FIRE-01 na árvore. É uma dependência barata e limpa.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `rapidfuzz.fuzz.WRatio` | `rapidfuzz.fuzz.ratio` (Indel normalizado) | **Medido: `ratio` separa o par motivador e `WRatio` não.** Ver 🚩 #1. |
| `rapidfuzz` inteiro | `difflib.SequenceMatcher` (stdlib) | Serve para o caso simples, mas **o corte 88 teria de ser remedido** — ver §"difflib serve?" |
| `numeros_com_sufixo` como localizador em produção | retângulo de coluna CALIBRADO | **Medido: em produção `numeros_com_sufixo` devolve grupos-lixo** (leu `'361689'` e `'436,569,,,96,5,3'` de regiões que não são preço). Ela é boa PROPONDO na calibração e ruim DECIDINDO em produção. |
| `hashlib` para congelamento | `np.array_equal` | Medido: 0,89 ms vs 3,7–13,5 ms. Sem contest. |

**Installation (se `rapidfuzz` for aprovado):**

```bash
# requirements.txt ganha uma linha; o vigiar-party.bat reinstala sozinho
rapidfuzz>=3.14.5,<4
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `rapidfuzz` 3.14.5 | PyPI | publicado 2026-04-07 | *não exposto pela API do PyPI* | github.com/rapidfuzz/RapidFuzz | **SUS** (motivo: `unknown-downloads`) | **Aprovado com ressalva** — ver nota |

```
gsd-tools query package-legitimacy check --ecosystem pypi rapidfuzz
-> { "verdict": "SUS", "signals": { "exists": true,
     "publishedAt": "2026-04-07T11:13:37.733795Z", "weeklyDownloads": null,
     "repoUrl": "https://github.com/rapidfuzz/RapidFuzz", "deprecated": false,
     "postinstall": null }, "reasons": ["unknown-downloads"] }
```

`[VERIFIED: saída do seam nesta sessão]`

**Nota honesta sobre o veredito `SUS`.** O único motivo é `unknown-downloads`, que é uma
**limitação da API do PyPI** (ela não expõe contagem de downloads), não um sinal de risco:
o pacote existe, tem repositório de código declarado, não está deprecado e não tem
`postinstall`. Os sinais positivos foram conferidos por download real do wheel nesta sessão
(MIT, 1,5 MB, sem dependência obrigatória). Ainda assim, seguindo a regra do projeto:

- **Nome do pacote:** `rapidfuzz` chegou até aqui pelo `CLAUDE.md` (memória de treino
  destilada em documento), não por documentação oficial descoberta nesta sessão → o nome em
  si é `[ASSUMED]` até o usuário confirmar. `pip index versions rapidfuzz` e o download do
  wheel provam que **existe** um pacote com esse nome no PyPI, o que **não** é o mesmo que
  provar que é o que se quer.
- **Recomendação para o planner:** se `rapidfuzz` entrar, coloque um
  `checkpoint:human-verify` antes do `pip install`, mostrando ao usuário a URL do repositório
  e o `License-Expression`. Custa um ENTER e fecha a categoria inteira.

**Packages removed due to [SLOP] verdict:** nenhum.
**Packages flagged as suspicious [SUS]:** `rapidfuzz` (motivo administrativo, não de risco).

---

## Architecture Patterns

### System Architecture Diagram

```
      janela capturada (1720x1392 BGR)
                 |
                 v
   +-------------------------------+
   | CONGELAMENTO (mercado_pagina) |  np.array_equal contra a janela anterior
   |  3 iguais seguidas -> ABORTA  |  0,89 ms medido
   +-------------------------------+
                 | (janela viva)
                 v
   +-------------------------------+
   | RASTREIO DO PAINEL            |  RastreioDoPainel.observar  (JA EXISTE)
   |  memoria + rebusca a cada 5 s |  varredura ~39 ms medido
   +-------------------------------+
                 | origem (ox, oy)  -- ou "painel ausente" -> nada a ler
                 v
   +-------------------------------+
   | PORTAO DE LAYOUT              |  molde do cabecalho SEM a seta
   |  layout != calibrado -> RECUSA|  banda [topo-32, topo-2], mascara V>210
   +-------------------------------+
                 | layout confere
                 v
        fatiar em N linhas de `altura_da_linha` (grade calibrada)
                 |
     +-----------+-----------+
     |  para CADA linha      |
     v                       v
+----------------+   +--------------------------+
| SONDA DE       |   | LINHA VAZIA?             |
| OCLUSAO        |   |  sem glifo E sem icone   |
| trecho sem     |   |  -> fim da pagina        |
| texto, fundo   |   +--------------------------+
| 48/66 +-tol    |
| fora -> DESCART|
+----------------+
     | linha limpa
     v
  +------------------------+        +---------------------------+
  | COLUNA DO NOME         |        | COLUNA DE PRECO / QTD     |
  | recorte calibrado      |        | retangulo CALIBRADO       |
  |  OCR 2x  +  OCR 3x     |        |  mascara V>180            |
  |  2,9 ms     4,1 ms     |        |  segmentar_glifos         |
  |  acordo? (ver 🚩 #2)   |        |  argmax + margem por run  |
  +------------------------+        |  GRAMATICA: milhar=3,     |
     | texto                        |  decimal=2 -> senao DESCART|
     v                              +---------------------------+
  +------------------------+                  | inteiro em centesimos
  | CATALOGO DE NOMES      |                  |
  |  similaridade vs vistos|                  |
  |  >= corte  -> agrupa   |                  |
  |  faixa cinzenta-> DESCA|                  |
  |  <  piso   -> SERIE NOVA (grava)          |
  +------------------------+                  |
     | chave da serie                         |
     +--------------------+-------------------+
                          v
              LinhaLida(chave, total, qtd, nova?)
                          |
                          v
   +-------------------------------------------+
   | ESTABILIZADOR (mercado_pagina)            |
   |  tupla parseada deste frame == a anterior?|
   |  linhas DESCARTADAS ficam FORA da compara.|
   +-------------------------------------------+
                          | acordo
                          v
                  PaginaAceita  --->  Fase 3 (CSV)
```

### Recommended Project Structure

```
l2scanner/
├── mercado_leitura.py     # NOVO — transform puro: pixels de uma linha -> LinhaLida|Descarte
│                          #   (segmentar, classificar glifo, gramatica, sonda de oclusao)
├── mercado_catalogo.py    # NOVO — o catalogo de nomes vistos: carregar, agrupar, gravar
├── mercado_pagina.py      # NOVO — a maquina de estado: congelamento + acordo entre frames
├── mercado_visao.py       # existente — SEM MUDANCA
├── mercado_geometria.py   # existente — pode ganhar a primitiva da sonda de fundo
├── calibrar_mercado.py    # existente — PASSA A IMPORTAR de mercado_leitura.py;
│                          #   ganha a marcacao da coluna do nome e o molde de cabecalho
└── ocr.py                 # existente — SEM MUDANCA
```

**A regra que decide o que vai para onde:** `mercado_leitura.py` não pode importar `cv2.imshow`,
não lê teclado, não abre arquivo e não tem relógio. É o mesmo charter de `mercado_geometria.py`
(`[VERIFIED: l2scanner/mercado_geometria.py:1-9]` — *"Este modulo nao abre janela, nao le
teclado, nao escreve arquivo e nao pergunta nada"*).

### Pattern 1: mover a primitiva, não copiá-la

**What:** `segmentar_glifos`, `_alinhar_por_preenchimento`, `_par_incalculavel`,
`mascara_do_sufixo` e a lógica de `propor_rotulo` **mudam de arquivo** para
`mercado_leitura.py`; `calibrar_mercado.py` passa a importá-las.
**When to use:** sempre. Copiar cria duas convenções de recorte que divergem, e a docstring de
`segmentar_glifos` já avisa por quê:

> *"Deixar a convencao implicita tambem convida ao teste circular: os numeros da matriz de
> confusao MUDAM com o recorte, e quem escolhe o recorte depois de ver a matriz ajusta um ate
> o outro fechar."* `[VERIFIED: l2scanner/calibrar_mercado.py:375-381]`

**A prova de que a mecânica é a mesma dos dois lados** já está escrita: `propor_rotulo`
*"Reaproveitar exatamente a mecanica da matriz e o que faz o numero significar a mesma coisa
dos dois lados; medir de um jeito e decidir com o outro seria comparar convencoes."*
`[VERIFIED: l2scanner/calibrar_mercado.py:1610-1614]`

### Pattern 2: argmax + margem, nunca piso absoluto

**What:** um glifo é decidido pelo template que casa MELHOR e pela distância até o segundo
colocado — não por um limiar de "quão bem casou".
**When to use:** toda classificação em conjunto fechado neste projeto.
**Precedente:** `identidade.LIMIAR_DE_CASAMENTO = 0.75` + `MARGEM_MINIMA_SOBRE_O_SEGUNDO = 0.12`
`[VERIFIED: l2scanner/identidade.py:109,113]`, replicado em
`MINIMO_PARA_PROPOR_ROTULO = 0.80` + `MARGEM_MINIMA_PARA_PROPOR = 0.12`
`[VERIFIED: l2scanner/calibrar_mercado.py:1386-1387]`.

### Pattern 3: a gramática do número como trava de validação

Já travada em `SPIKE-RESPOSTAS.md` §2 e validada pelo usuário: **milhar agrupa em blocos de
exatamente 3; decimal tem exatamente 2.** `5,00,000` ou `62,000` violam a regra e a linha cai.
Isso é falha fechada de graça, e pega o modo de falha que a classificação não pega (glifo
perdido ou glifo a mais). **O que ela NÃO pega é substituição** (`0`→`8` mantém a gramática) —
para isso serve a margem e o acordo entre frames.

### Anti-Patterns to Avoid

- **Usar `numeros_com_sufixo` para localizar a coluna de preço em produção.** Medido: no
  `pagina-cheia/frame_000010` ela devolveu um grupo espúrio que classificou como `'361689'`
  (cauda 89), e no `scroll-transicao/frame_000012` devolveu `'436,569,,,96,5,3'` (cauda 33)
  a partir do carimbo de quantidade do ícone. Em produção a coluna é **retângulo calibrado**;
  `numeros_com_sufixo` continua sendo o que PROPÕE aquele retângulo na calibração.
- **Reaproveitar `mercado_limiar_de_glifo` como piso de leitura.** Ele é o limiar de
  COLISÃO derivado de `(1.0 + pior_par)/2` — ver 🚩 na §"O limiar de glifo".
- **Comparar frames de grade para detectar congelamento.** Já travado; a grade parada é o caso
  normal. Confirmado pela medição do spike §9 (diferença 0 no retângulo da âncora).
- **Recortar a linha inteira para o OCR.** LEIT-05. E ver a prova de que nem a coluna basta,
  em §"A coluna do nome".
- **Truncar o nome do nosso lado.** Medi o dano por acidente: com o recorte de 143 px
  `Common Mafia Leader Luciano Doll` saiu como `'Common Mafia Leader Lucia'` e
  `+6 Agathion Alpha Hunter Sealed` como `'+6 Agathion Alpha Hunter S'`. Com 270 px os dois
  saem inteiros. É exatamente a trava estrutural de `SPIKE-RESPOSTAS.md` §7.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Segmentar glifos numa célula | varredura de `matchTemplate` com supressão de não-máximos | `segmentar_glifos` (projeção de coluna, já existe) | Medido 8/8 e agora 25/25 preços. NMS resolve um problema que não temos: os glifos **não se sobrepõem**, e a menor lacuna medida entre vizinhos é de exatamente 1 coluna. |
| Alinhar moldes de larguras diferentes | corte ao menor comum | `_alinhar_por_preenchimento` | Medido nesta sessão: `,`×`2` dá **0,1918** preenchendo e **0,5000** cortando. E `,`×`0`/`1`/`3`/`7` todos dão **0,189** cortando — similaridade fabricada. |
| Isolar o texto do fundo | limiar próprio | `identidade.mascara_de_texto` (V>180) e `mascara_do_sufixo` (V>120) | Os dois pisos são medidos e a diferença entre eles é o que separa número de sufixo. |
| Localizar a grade / medir bandas | derivada do perfil | `mercado_geometria` (`perfil_por_mediana`, `trechos_de_nivel`) | A versão por derivada já foi tentada e derrubada por medição — está registrado em `mercado_geometria.py:107-127`. |
| Comparar duas janelas | hash | `np.array_equal` | 0,89 ms vs 3,7 ms (sha256) / 6,8 ms (blake2b). |
| Similaridade de string | Levenshtein escrito à mão | `rapidfuzz.fuzz.ratio` ou `difflib` | Mas leia 🚩 #1 antes de escolher **qual** métrica. |

**Key insight:** neste projeto o custo de hand-roll não é o tempo de escrever — é que a versão
nova nasce **sem a medição** que justificou a antiga, e o número que a sustentava desaparece.

---

## Respostas às 8 perguntas da pesquisa

### 1. Segmentação de dígitos numa célula de preço — RESOLVIDO, e já funciona

**Projeção de coluna, não varredura por `matchTemplate`.** `segmentar_glifos` separa por
QUALQUER coluna vazia, sem tolerância de lacuna, e a docstring registra a medição que
autoriza isso: *"a menor lacuna real medida entre dois glifos vizinhos e de exatamente uma
coluna"* `[VERIFIED: l2scanner/calibrar_mercado.py:383-385]`.

**Medido nesta sessão, ponta a ponta**, rodando `localizar_painel` → `mercado_grade` →
`numeros_com_sufixo` (filtrando a cauda de 44 px do `XM Coin`) → `segmentar_glifos` →
argmax contra os 11 moldes de um caractere:

| frame | preços lidos |
|---|---|
| `pagina-cheia/frame_000010` | `100,00` `3,00` `18,90` `7,50` `18,00` `2,45` |
| `scroll/frame_000014` (Adena) | `62,00` `64,99` `65,00` `66,00` `67,00` `135,88` `68,00` `68,50` `70,00` `70,00` |
| `scroll-transicao/frame_000012` | `22,22` `18,00` `22,69` `33,00` `20,00` `24,90` `40,00` `17,00` `16,00` `24,00` |

`[VERIFIED: script rodado nesta sessão contra os frames citados]` — **25 preços, todos
conferindo com os valores que o `SPIKE-RESPOSTAS.md` registrou lendo os mesmos frames a olho**
(`24,90`/`17,00`/`40,00` com quantidades 10/5/48 na §4; `62,00` na §2; `18,90`/`18,00` na §4).

**Espaçamento variável:** não é problema. As colunas vazias entre glifos separam, e as colunas
vazias nas pontas não criam run — registrado em
`MARGEM_DO_RETANGULO_DE_PRECO` `[VERIFIED: l2scanner/calibrar_mercado.py:1350-1356]`.

**A vírgula de 1 px:** ver a pergunta 2. Ela é o glifo que a segmentação separa MELHOR, não
pior.

### 2. A vírgula de 1×9 px — MEDIDA, e ela é o glifo mais seguro do conjunto

O molde da vírgula é **9 linhas × 1 coluna** `[VERIFIED: calibration.json,
mercado_templates_de_digito, entrada `,` -> "altura": 9, "largura": 1]`. As 9 linhas não são
enchimento: a **faixa de linhas é COMPARTILHADA** por todos os glifos do retângulo marcado, de
propósito, e é isso que preserva a posição vertical:

> *"Recortar cada glifo justo na PROPRIA altura deixaria a virgula com 3 px e o digito com 8,
> descartando a posicao vertical relativa -- que e precisamente o que distingue uma virgula
> (baixa) de um digito (altura cheia)."* `[VERIFIED: l2scanner/calibrar_mercado.py:370-374]`

Decodifiquei os moldes e imprimi a máscara. A vírgula e o `1`, lado a lado:

```
','  9x1          '1'  9x4
 |.|               |..#.|
 |.|               |###.|
 |.|               |..#.|
 |.|               |..#.|
 |.|               |..#.|
 |.|               |..#.|
 |#|               |..#.|
 |#|               |####|
 |#|               |....|
```

`[VERIFIED: moldes decodificados de calibration.json nesta sessão]`

**"Um molde de 1 px casa contra o traço vertical de um `1`?" — NÃO, e a medição é dura.**
Matriz completa dos 11 glifos de um caractere, no alinhamento de produção
(`_alinhar_por_preenchimento`), rodada nesta sessão:

| par | score |
|---|---|
| `,` × `2` | **0,1918** ← o pior par que envolve a vírgula |
| `,` × `0` | 0,0806 |
| `,` × `7` | 0,0580 |
| `,` × `9` | 0,0000 |
| **`,` × `1`** | **−0,0174** |
| `,` × `3`, `,` × `8` | −0,0174 |
| `,` × `6` | −0,0344 |
| `,` × `5` | −0,0510 |
| `,` × `4` | −0,1504 |
| *(pior par do conjunto inteiro)* `0` × `8` | **0,7110** |

`[VERIFIED: matriz recalculada nesta sessão; o pior par 0×8 = 0.7110 reproduz exatamente o
número registrado no CONTEXT.md]`

A vírgula contra o `1` é **negativamente correlacionada**. Ela fica 0,52 abaixo do pior par do
conjunto. **O risco caro não é a vírgula; é o `0`×`8`** — ver a pergunta seguinte e §"O
limiar de glifo".

**O alinhamento entre larguras diferentes favorece recusar?** Sim, e há duas escolhas
deliberadas e opostas no código, cada uma com a sua medição:

- **Nomes → `_alinhar` (corta ao menor comum).** *"Cortar torna a matriz MAIS conservadora, e
  isso e de proposito"* `[VERIFIED: l2scanner/calibrar_mercado.py:249-253]`.
- **Glifos → `_alinhar_por_preenchimento` (preenche com zeros até a maior caixa).**
  *"Medido: 0.1918 preenchendo, 0.5000 cortando"* `[VERIFIED:
  l2scanner/calibrar_mercado.py:509-512]`.

Reproduzi as duas nesta sessão e confirmo: cortando, `,`×`0`, `,`×`1`, `,`×`3` e `,`×`7` todos
sobem para **0,1890** e `,`×`2` para **0,5000**, porque a comparação vira "1 coluna contra 1
coluna". **Preenchendo é o conservador para glifos; cortando é o conservador para nomes.** As
duas convenções estão certas e não podem ser unificadas.

### 3. `rapidfuzz` está instalado? — NÃO. E o corte 88 tem um problema maior que a instalação

**Não está.** `.venv/Lib/site-packages` contém apenas: `aiohttp`, `attrs`, `coverage`, `cv2`,
`discord`, `mss`, `numpy`, `pip`, `typing_extensions`, `windows_capture`, `winrt-*`, `yarl` e
transitivas. Não há `rapidfuzz` nem `Levenshtein`. `requirements.txt` também não o menciona
`[VERIFIED: listagem do .venv e leitura integral de requirements.txt nesta sessão]`.

**Custo de adicionar:** 1,5 MB, MIT, zero dependência obrigatória (ver §Package Legitimacy).
Barato.

#### 🚩 O achado que importa: `WRatio` com corte 88 FUNDE as séries que a decisão protegia

Baixei o wheel do PyPI e **rodei a implementação de referência em Python puro que o próprio
rapidfuzz distribui** (`rapidfuzz/fuzz_py.py`), sem instalar nada no `.venv`:

| a | b | **WRatio** | `ratio` | `partial_ratio` |
|---|---|---|---|---|
| `Common Aztac` | `Common Aztac M. Def. +200` | **90,00** 💥 | **64,86** | 100,00 |
| `+6 Agathion Alpha Hunter Sealed` | `+4 Agathion Alpha Hunter Sealed` | **96,77** 💥 | 96,77 | 96,77 |
| `Agathion Alpha Hunter Sealed` | `+7 Agathion Alpha Hunter Sealed` | **95,00** 💥 | 94,92 | 100,00 |
| `Hardin's Soul Crystal Lv. 1` | `Hardin's Soul Crystal Lv. 3` | **96,30** 💥 | 96,30 | 98,11 |
| `Hardin's Soul Crystal Lv. I` | `Hardin's Soul Crystal Lv. 1` | 96,30 ✅ | 96,30 | 98,11 |
| `Earth Spirit Evolution Stone` | `Earth Spirit Ewlution Stone` | 94,55 ✅ | 94,55 | 92,59 |
| `Common King Procella Doll` | `Common Kng Procella Doll` | 97,96 ✅ | 97,96 | 95,83 |
| `Common Aztac` | `Common Fafuri` | 64,00 ✅ | 64,00 | 76,19 |
| `Agathion Alpha Hunter Sealed` | *(vazamento de tooltip)* | 30,30 ✅ | 30,30 | 36,73 |

`[VERIFIED: rapidfuzz 3.14.5 fuzz_py.WRatio/ratio/partial_ratio executados nesta sessão]`

**Por que o `WRatio` faz isso, do próprio fonte:**

```python
len_ratio = len1 / len2 if len1 > len2 else len2 / len1
end_ratio = ratio(s1, s2, score_cutoff=score_cutoff)
if len_ratio < 1.5:
    ...
    return max(end_ratio, token_ratio(...) * UNBASE_SCALE)
PARTIAL_SCALE = 0.9 if len_ratio <= 8.0 else 0.6
end_ratio = max(end_ratio, partial_ratio(s1, s2, ...) * PARTIAL_SCALE)
```
`[VERIFIED: rapidfuzz-3.14.5/rapidfuzz/fuzz_py.py, função WRatio — extraída do wheel oficial
do PyPI nesta sessão]`

`Common Aztac` (12) e `Common Aztac M. Def. +200` (25) têm `len_ratio = 2,083 ≥ 1,5`, então
entra o ramo do `partial_ratio`. O curto é **substring perfeita** do longo → `partial_ratio =
100` → `100 × 0,9 = 90,00`. **90 > 88. As duas séries se fundem.** É o par exato que a decisão
travada cita como motivo de existir.

**E o problema é mais fundo que o scorer.** Olhe as duas últimas linhas relevantes:

- `Lv. I` × `Lv. 1` = **96,30** — ruído de OCR, PRECISA agrupar.
- `Lv. 1` × `Lv. 3` = **96,30** — itens DIFERENTES, PRECISA separar.

**O mesmo número tem de decidir coisas opostas.** Nenhum corte escalar resolve isso, com
`WRatio`, `ratio`, `difflib` ou qualquer métrica de distância de edição. E não é hipótese: os
três aparecem juntos em `scroll-transicao/frame_000016`, onde as linhas 8 e 9 são
`Hardin's Soul Crystal Lv. 3` e `Lv. 5` enquanto as outras oito são `Lv. 1`
`[VERIFIED: OCR rodado nesta sessão sobre esse frame]`.

**O que a evidência sustenta (proposta, requer confirmação do usuário porque toca decisão travada):**

1. **Trocar `WRatio` por `fuzz.ratio`.** Ele resolve o par motivador (64,86 vs 90,00) e mantém
   o ruído agrupado (94,55 / 96,43 / 97,96). Um `partial_ratio` embutido é exatamente o que
   não se quer quando "um nome é prefixo do outro" significa "são itens diferentes".
2. **Nunca agrupar por similaridade quando os DÍGITOS do nome diferem.** O `+N ` de encanto
   e o `Lv. N` são a informação de maior consequência de preço (medido no spike: 7,02 a
   100,00 para o mesmo nome) e ocupam 1–2 caracteres numa string de 30 — invisíveis para
   qualquer distância de edição. A regra mínima, barata e fechada: **extrair a sequência
   ordenada de dígitos do nome; ela tem de bater EXATAMENTE; a similaridade decide só o
   resto.** Com isso `+6 X` ≠ `+4 X` por construção e `Lv. 1` ≠ `Lv. 3` por construção.
3. **O casamento com a doutrina do projeto:** o dígito dentro do nome é lido pelo mesmo
   motor que erra vírgula (`Lv. I` por `Lv. 1`). A saída consistente com LEIT-01/LEIT-02 é
   **ler o `+N` com os moldes de dígito, não com o OCR** — a fonte é a mesma. Isso precisa de
   uma medição que ainda não existe (§Open Questions #2).
4. **Fallback fail-closed, se (3) não couber no v1:** todo nome que contenha dígito sai da
   rota de similaridade e exige **igualdade exata de string**. Custo: séries duplicadas
   quando o OCR oscila (`Lv. I` cria uma série a mais). Ganho: fusão impossível. É a
   aplicação literal do princípio do usuário — *"Fusão no CSV é irreversível; descarte não é"*.

#### `difflib.SequenceMatcher` serviria com o corte 88?

**Não sem remedir, e digo por quê.** `difflib.SequenceMatcher.ratio()` é `2·M/T` sobre blocos
contíguos casados (algoritmo de Ratcliff/Obershelp); `rapidfuzz.fuzz.ratio` é a similaridade
**Indel normalizada**. São métricas diferentes; coincidem em alguns pares e divergem noutros —
`difflib` tem inclusive um `autojunk` que altera o resultado em strings ≥ 200 caracteres.
Medi os mesmos pares com as duas:

| par | `difflib.ratio` | `rapidfuzz.ratio` |
|---|---|---|
| `Common Aztac` × `Common Aztac M. Def. +200` | 64,9 | 64,86 |
| `Evolution` × `Ewlution` | 94,5 | 94,55 |
| `1-time` × `I-time` | 96,4 | 96,43 |
| `+6 …` × `+4 …` | 96,8 | 96,77 |

`[VERIFIED: difflib e rapidfuzz.fuzz_py rodados nesta sessão]`

Nos nomes deste jogo (curtos, sem tokens reordenados, com diferenças de 1–2 caracteres) as
duas dão praticamente o mesmo número. **Mas o corte 88 foi escolhido pensando no `WRatio`, que
é composto — se a métrica muda, o número precisa ser remedido**, e o jeito de remedir é o
jeito da casa: uma ferramenta que passa todas as leituras das 8 gravações pelas duas métricas e
mostra ao usuário o histograma dos pares que agrupam e dos que separam. Sem isso, 88 é um
número herdado de outro contexto.

**Recomendação:** se a solução for `ratio` (não `WRatio`), **`difflib` da stdlib entrega o
mesmo resultado e evita a dependência inteira**. `rapidfuzz` só se paga se o corpus crescer a
ponto de o desempenho importar — o que não acontece com 10 linhas por segundo contra um
catálogo de algumas centenas de nomes.

### 4. Detecção de oclusão pela faixa de fundo alternada — MEDIDA, e funciona

**Os dois valores conhecidos são 48 e 66**, e a paridade é rígida: linhas de índice par valem
48, ímpares valem 66, contadas a partir do topo da grade. Isso reproduz o número já registrado
em `mercado_geometria.py:96-98` (*"o fundo das linhas alterna entre 48 e 66 — 18 niveis de
diferenca"*) `[VERIFIED: l2scanner/mercado_geometria.py:96-98]` e foi reconfirmado por mim em
3 frames × 10 linhas `[VERIFIED: medição desta sessão]`.

**Onde procurar dentro da linha.** Varri a linha em blocos de 30 colunas medindo a fração da
moda. O trecho mais limpo — e o mesmo em todas as linhas — é **x ∈ [180, 510) relativo à
esquerda da grade**, o vão entre o fim do nome do item e o começo da coluna de preço. Com **2
linhas de folga em cima e embaixo** (o mesmo cuidado que `fim_da_alternancia` já toma,
`[VERIFIED: l2scanner/mercado_geometria.py:470-472]`), a sonda separa assim:

| condição | frame | `pixels fora de moda±3` |
|---|---|---|
| linha limpa, banda par (48) | `scroll/frame_000014` | **0,024** |
| linha limpa, banda ímpar (66) | idem | **0,049** |
| linha limpa, banda par | `pagina-cheia/frame_000010` | 0,027–0,028 |
| **coberta por tooltip** | `tooltip/frame_000015`, linhas 0–7 | **0,502 – 0,599** |
| limpas no MESMO frame | `tooltip/frame_000015`, linhas 8–9 | 0,027 |
| **marcação de alvo**, linhas 0–1 | `alvo-sobreposto/frame_000024` | **0,120–0,121** |
| limpas no mesmo frame | idem, linhas 2–9 | 0,027–0,070 |

`[VERIFIED: medição desta sessão sobre os frames nomeados]`

**A separação é de uma ordem de grandeza** para tooltip (0,027 → 0,53) e de **~5×** para a
marcação de alvo (0,027 → 0,12). Um corte em torno de **0,10** pega os dois; mas ele **tem de
ser calibrado por varredura sobre as 8 gravações**, não escolhido aqui — a marcação de alvo é
o caso apertado e eu a medi em UM frame.

**Duas ressalvas que mudam o desenho:**

1. **A moda NÃO muda sob tooltip em todas as linhas.** Nas linhas 2, 4, 6 do frame de tooltip
   a moda continua 48. **Testar "a moda é 48 ou 66?" falharia.** O que separa é a
   **dispersão** (fração de pixels fora de moda±3), que é auto-referente e não depende de
   conhecer 48/66.
2. **Os valores absolutos NÃO são universais.** Em `scroll/frame_000009` a sonda leu modas de
   **47 e 65**, com a paridade invertida — porque aquele frame é a **tela de busca** (9
   linhas, layout diferente), e aplicar a grade Adena ali produz lixo. Isso é uma confirmação
   independente de que o **portão de layout tem de vir ANTES da sonda de oclusão**.

**Primitiva reaproveitável:** `perfil_por_mediana` + `trechos_de_nivel` de
`mercado_geometria.py` respondem "qual é o nível de fundo" com imunidade a texto; e
`fim_da_alternancia` já faz mediana por coluna com 2 linhas de folga em cada ponta
`[VERIFIED: l2scanner/mercado_geometria.py:437-486]`. A sonda nova é ~10 linhas em cima delas.
Sugestão: `nivel_de_fundo_da_linha(cinza, retangulo) -> (moda, dispersao)` em
`mercado_geometria.py`, e a decisão (o limiar) em `mercado_leitura.py`.

### 5. Custo por página — MEDIDO, e o orçamento fecha com folga de 12×

A tabela do `ocr.py` foi medida na banda 732×240 (1x=10, 2x=23, 3x=31, 4x=55 ms)
`[VERIFIED: l2scanner/ocr.py:71-74]`. **Não precisei extrapolar — medi direto no recorte real.**

Recorte da coluna do nome: **45 × 270 px** (a linha inteira de 45 px de altura, 270 px de
largura a partir do fim do ícone).

| passada | custo mediano | leitura |
|---|---|---|
| OCR 2x | **2,9 ms** (min 2,8 / max 3,3) | `'Earth Spirit Evolution Stone'` |
| OCR 3x | **4,1 ms** (min 3,9 / max 4,3) | `'Earth Spirit Evolution Stone'` |
| **página inteira: 10 linhas × 2 escalas** | **70 ms** | 10/10 nomes lidos |

`[VERIFIED: medição desta sessão, motor já aquecido, sobre `pagina-cheia/frame_000010`]`

**O orçamento de um tick a 1 Hz:**

| etapa | custo medido |
|---|---|
| `np.array_equal` da janela (congelamento) | 0,89 ms |
| varredura do painel (só na aquisição / a cada 5 s) | ~39 ms |
| confirmação por âncora (todo tick) | << 39 ms |
| OCR do nome, 10 linhas × 2 escalas | 70 ms |
| leitura de dígitos, 10 linhas (segmentar + argmax ×11 moldes) | << 10 ms (o script inteiro, incluindo I/O de PNG, roda em ~1 s para 3 frames) |
| sonda de oclusão, 10 linhas | ~0 |
| **total do pior tick** | **~110 ms de 1000 ms** |

**Cabe com folga de ~9×.** O custo é 11% de um núcleo. A escolha do recorte da COLUNA (270 px)
contra a linha inteira (942 px) reduz o custo do OCR por um fator de ~3,5 — LEIT-05 paga o
próprio preço em desempenho, além de corrigir o vazamento de tooltip.

### 6. Molde de cabeçalho de coluna SEM a seta — MEDIDO, e há um separador melhor que geometria

A banda do cabeçalho é **`[topo_da_grade − 32, topo_da_grade − 2)`**, largura da grade. Grupos
de texto claro (coordenadas relativas à esquerda da grade), medidos nesta sessão:

| layout | frame | grupos | OCR 3x da banda |
|---|---|---|---|
| negociação, ordenado por **Goods** | `063752-mercado-aberto/frame_000000` | `(153,182)` `(198,201)` `(367,408)` `(538,562)` `(734,779)` `(900,916)` | `'Goods Quantity Total Unit price'` |
| negociação, ordenado por **Unit price** | `063752-mercado-aberto/frame_000020` | `(153,182)` `(367,408)` `(538,562)` `(734,779)` `(796,799)` `(900,916)` | `'Quantity Total Unit price'` |
| **Adena** | `055323-mercado-scroll/frame_000014` | `(174,231)` `(490,541)` `(704,782)` `(798,801)` `(900,916)` | `'Auction List Total Price 5 mln increment'` |
| **tela de busca** | `055323-mercado-scroll/frame_000048` | `(33,53)` `(212,232)` `(619,627)` | `'dolll x'` |

`[VERIFIED: medição desta sessão sobre os 4 frames nomeados]`

**Onde a seta cai, exatamente:** ela é o grupo `(198,201)` quando a ordenação está em `Goods` e
o grupo `(796,799)` quando está em `Unit price` — **3 px de largura, linhas de texto 15..22**.
Ela some de um lugar e aparece no outro, confirmando §3 do spike ao pixel.

**E há um separador mais barato que qualquer geometria: o BRILHO.**

| elemento | V máximo |
|---|---|
| rótulos de coluna (`Goods`, `Quantity`, `Total`, `Unit price`, `Buy`) | **229** |
| **a seta de ordenação** | **181** |
| borda esquerda da banda (grupo `(2,3)`) | 201 |

`[VERIFIED: medição desta sessão]`

**Cortar o molde do cabeçalho da máscara `V > 210` remove a seta E a borda, sem uma linha de
código de geometria.** Confirmei rodando o censo de layouts inteiro com esse corte: a seta
desaparece dos grupos em todos os frames.

**Como a página é recusada quando o layout não bate:** o conjunto de fronteiras de grupo é uma
impressão digital. Rodei o censo dos 335 frames com `V>210` e as três assinaturas se separam
sem ambiguidade — negociação `{(153,180),(367,407),(538,559),(734,779)}`, Adena
`{(174,230),(490,511),(519,541),(704,728)}`, busca `{(40,48),(212,~)}`. Casar o molde do
cabeçalho por `casamento_da_ancora` na posição conhecida (uma posição só, o padrão da casa) é
mais direto ainda e reusa código existente.

#### 🚩 O censo de layouts trouxe um problema de material

| gravação | Adena | negociação | busca | sem painel |
|---|---|---|---|---|
| `053105-mercado-aberto` | 11 | ~154 | 14 | 6 |
| `055323-mercado-scroll` | 14 | ~57 | 16 | 7 |
| `060622-mercado-pagina-cheia` | 0 | 26 | 6 | 1 |
| `061253-mercado-tooltip` | 0 | ~35 | 0 | 0 |
| `061409-mercado-alvo-sobreposto` | 0 | 28 | 0 | 14 |
| `063240-mercado-farm-com-party` | 0 | 36 | 0 | 3 |
| `063409-mercado-scroll-transicao` | 0 | 26 | 0 | 0 |
| `063752-mercado-aberto` | 0 | 21 | 0 | 0 |
| **total** | **~25** | **~283** | **~36** | **~31** |

`[VERIFIED: censo rodado nesta sessão sobre todas as gravações `*mercado*`]`

**O `calibration.json` da máquina do usuário diz `layout: "adena"`.** Sob a decisão travada
*"o v1 lê SOMENTE o layout que está calibrado"*, o replay contra as fixtures **recusaria ~283
dos ~308 frames com painel aberto**. O critério de sucesso 1 da fase ("rodando o replay contra
as fixtures, cada linha visível tem seu nome lido por OCR") não é demonstrável no material que
existe.

**E há um motivo mais forte que material: a aba Adena não tem nome de item.** OCR 3x da
primeira coluna, medido nesta sessão:

```
ABA ADENA   (055323-mercado-scroll/frame_000014)
  linha0 : 'Adena'      linha1 : 'Adena'      linha2 : 'Adena'      linha3 : 'Adena'
NEGOCIACAO  (060622-mercado-pagina-cheia/frame_000010)
  linha0 : 'Earth Spirit Evolution Stone'   linha1 : 'Earth Spirit Evolution Stone'
```

Na aba Adena a "mercadoria" é adena; a primeira coluna carrega `5,000,000 Adena`, e o único
texto é o sufixo dourado. **LEIT-01 (nome por OCR + agrupamento) e LEIT-05 (coluna do nome) não
têm objeto na aba Adena.** Eles descrevem a grade de negociação.

**Recomendação (requer confirmação do usuário — a decisão de "só o layout calibrado" continua
de pé; o que muda é QUAL layout se calibra):** recalibrar `mercado_grade.layout` para a grade
de negociação, e tratar a aba Adena como um layout futuro. A alternativa é o harness de teste
carregar uma calibração própria de fixture para a negociação — o que também é razoável e não
depende do usuário, mas deixa produção e teste calibrados em layouts diferentes, que é
exatamente o tipo de divergência que este projeto evita.

### 7. O estabilizador — MEDIDO, e `np.array_equal` ganha de lavada

**Comparar tuplas parseadas:** custo desprezível. A regra travada — linhas descartadas ficam
fora da comparação — implica que a chave de comparação é a **lista de tuplas das linhas
ACEITAS, na ordem**, e o acordo exige que as duas listas sejam idênticas. Nota de desenho: se
a linha 3 é descartada no frame A e aceita no frame B, as listas têm tamanhos diferentes; a
leitura fiel da regra é comparar apenas as posições aceitas **em ambos** os frames, e exigir
um mínimo de linhas comparadas para a página valer.

**Congelamento na janela inteira (1720×1392×3 uint8 = 7,2 MB):**

| método | custo mediano (frames diferentes) | pior caso (frames iguais) |
|---|---|---|
| **`np.array_equal(a, b)`** | **0,89 ms** | **0,96 ms** |
| `(a != b).any()` | 0,92 ms | — |
| `a.tobytes() == b.tobytes()` | 1,62 ms | — |
| `hashlib.sha256(a.tobytes())` | 3,70 ms | — |
| `hashlib.blake2b(a.tobytes())` | 6,81 ms | 13,48 ms (dois hashes) |

`[VERIFIED: medição desta sessão sobre `scroll-transicao/frame_000016` e `frame_000017`]`

**`np.array_equal` guardando o frame anterior.** Hash é 4 a 15× mais caro e só se pagaria se
fosse preciso guardar muitos frames — não é: a regra são **3 janelas consecutivas
bit-idênticas**, o que exige lembrar de 1 frame e um contador. Custo de memória: 7,2 MB, o
mesmo que já se paga para capturar.

Detalhe importante: `np.array_equal` faz curto-circuito assim que acha diferença, mas o pior
caso (iguais) foi medido em 0,96 ms — **não há caso ruim**.

### 8. Onde o catálogo de nomes deve morar — precedente já existe no repositório

**O padrão da casa para estado local durável é um diretório-ponto na raiz, no `.gitignore`.**
Existem dois: `.agenda/` e `.loot/`, e o `.gitignore` explica o porquê em prosa:

> *"`.loot/` guarda o registro de loot do Solo Boss — estado local e DURAVEL (nunca podado).
> Versionar misturaria a estatistica de maquinas diferentes."* `[VERIFIED: .gitignore, bloco
> "Saída em tempo de execução"]`

O catálogo de nomes tem exatamente essa natureza: local, durável, acumulado, nunca podado.

**Proposta (área de discrição do usuário — "desde que seja legível a olho nu e sobreviva a uma
recalibração"):**

```
.mercado/                       # gitignored, ao lado de .loot/ e .agenda/
├── catalogo-de-nomes.csv       # dono: FASE 2
└── observacoes.csv             # dono: FASE 3  (PERS-01)
```

`catalogo-de-nomes.csv`, separador `;` (o mesmo já travado para o CSV de observações, porque
o Sheets em português espera `;` e a vírgula decimal do jogo colidiria):

```csv
chave;nome_exibido;primeira_vez;ultima_vez;avistamentos
earth-spirit-evolution-stone;Earth Spirit Evolution Stone;2026-08-29T14:32:11-03:00;2026-08-29T18:02:04-03:00;47
agathion-alpha-hunter-sealed+6;+6 Agathion Alpha Hunter Sealed;2026-08-29T15:10:00-03:00;...;12
```

- **`chave`** é o que vai para o CSV de observações — estável, sem espaço, e carrega o encanto
  explicitamente para tornar a fusão de séries impossível na própria chave.
- **`nome_exibido`** é o rótulo humano; o usuário pode corrigir à mão no Sheets sem quebrar a
  chave.
- **`avistamentos`** e **`primeira_vez`** são a decisão travada ("contagem de avistamentos e
  data da primeira vez"), e é o que deixa o usuário julgar uma série nova no Sheets.

**Escrita:** o precedente de escrita atômica já existe e deve ser copiado —
`temporario.write_text(...)` num `.tmp-<pid>` seguido de `os.replace`, com a justificativa
escrita no fonte `[VERIFIED: l2scanner/loot.py:264-281]` (*"O replace e atomico no Windows no
mesmo volume, entao a outra instancia nunca le um json pela metade"*).

**A fronteira Fase 2 ↔ Fase 3, para não haver dúvida:**

| arquivo | quem escreve | quando |
|---|---|---|
| `catalogo-de-nomes.csv` | **Fase 2** | quando uma série nova nasce, ou a contagem de uma existente sobe |
| `observacoes.csv` | **Fase 3** | quando uma `PaginaAceita` chega e passa pela dedup |

A Fase 3 **lê** a chave que a Fase 2 produziu; ela nunca escreve no catálogo, e a Fase 2 nunca
escreve observação. Se a Fase 3 encontrar uma chave que não está no catálogo, isso é um erro de
programa, não um caso de uso.

---

## Common Pitfalls

### Pitfall 1: 🚩 `mercado_limiar_de_glifo` NÃO é um piso de leitura

**What goes wrong:** o `calibration.json` traz `mercado_limiar_de_glifo =
0.8554906845092773`, e é natural usá-lo como "aceite o glifo se casar acima disso".
**Why it happens:** ele é derivado de `(1.0 + pior_par)/2` — `(1 + 0,7110)/2 = 0,8555`
`[VERIFIED: l2scanner/calibrar_mercado.py:284-291, `limiar_sugerido=(1.0 + pior) / 2`]`. É um
número que certifica que o CONJUNTO de moldes é separável, medido molde-contra-molde. Não é um
número medido sobre glifos REAIS da tela.
**A medição:** classifiquei **2.057 glifos da coluna de preço** em 55 frames de 5 gravações:

```
score:  min=0,0818   p1=0,1918   p5=0,7242   mediana=1,0000
margem: min=0,0370   p1=0,0607   p5=0,0607   mediana=0,3451

abaixo de 0,8555 (o "limiar"): 370 de 2.057  =  18,0%
abaixo da margem 0,12:         145 de 2.057  =   7,0%

pior score por rótulo:   ',' 0,1918 | '0' 0,7559 | '8' 0,7242 (MEDIANA 0,7242!)
                         '9' 0,8367 | '7' 0,8292 | '6' 0,1218 | '4' 0,1048
```
`[VERIFIED: medição desta sessão]`

**O `8` tem MEDIANA 0,7242 contra o próprio molde.** Um piso em 0,8555 rejeitaria
**praticamente todo `8` da tela** — `135,88` cairia. O código já sabia disso e registrou a
medição que derrubou a primeira tentativa: *"Eu supus que o mesmo digito no mesmo frame casaria
1.000 por ser o mesmo desenho. Ele nao casa: o FUNDO da linha alterna entre 48 e 66 … acerto
PIOR 0.837"* `[VERIFIED: l2scanner/calibrar_mercado.py:1364-1375]`.

**How to avoid:** o piso de LEITURA é um número **diferente** e tem de ser medido por
ferramenta própria, gravado numa chave própria (proponho
`mercado_limiar_de_leitura_de_glifo` + `mercado_margem_de_leitura_de_glifo`), pela mesma razão
já escrita para não aliasar os limiares de nome e de glifo:
*"Aliasar as duas faria o afrouxamento de um viajar para o outro"*
`[VERIFIED: l2scanner/calibrar_mercado.py:344-350]`.
**Warning signs:** taxa de descarte alta e concentrada em números que contêm `8` ou `0`.

### Pitfall 2: 🚩 A margem `0`×`8` é de 0,0370 — o mais estreito do sistema

**What goes wrong:** um `0` lido como `8` mantém a gramática do número, passa pelo
estabilizador (dois frames do mesmo método concordam no mesmo erro) e vira preço plausível.
**A medição, sobre recortes REAIS:**

| o que está na tela | contra molde `0` | contra molde `8` | margem |
|---|---|---|---|
| um `0` real (n=194) | 0,7559 – 1,0000 (med. 0,9258) | 0,6952 – **0,8249** (med. 0,7110) | **mín. 0,0370** |
| um `8` real (n=76) | 0,5345 – 0,7110 | **0,7242** – 1,0000 (med. 0,7242) | mín. 0,0680 |

`[VERIFIED: medição desta sessão]`

**Não há sobreposição — o argmax nunca errou nos 270 casos.** Mas o pior `0` casa **0,8249**
contra o molde do `8`, e o `8` típico casa **0,7242** contra o próprio. Os intervalos quase se
tocam.
**How to avoid:** (a) **melhorar os moldes** — a assimetria diz que os moldes de `0` e `8`
foram cortados numa banda de fundo que não é a maioria; cortar um molde por (glifo, paridade
da banda) é o conserto de raiz e sobe as duas medianas para perto de 1,0; (b) enquanto isso,
margem calibrada, nunca `0,12` herdado; (c) a gramática do número como rede.
**Warning signs:** preços com `8` sistematicamente descartados, ou séries com saltos de 10×.

### Pitfall 3: 🚩 O acordo 2x==3x por igualdade de string custa metade das linhas

**What goes wrong:** a decisão travada diz "duas escalas que precisam CONCORDAR". Se
"concordar" for `a == b`, o rendimento despenca.
**A medição, 60 linhas de 6 frames:**

```
ACORDO 2x == 3x na coluna do nome:  30/60  =  50,0%
```
`[VERIFIED: medição desta sessão]`

E as discordâncias são triviais:

```
2x = "Hardin's Soul Crystal Lv. I"   3x = "Hardin's Soul Crystal Lv. 1"    (x10)
2x = 'Common Kng Procella Doll'      3x = 'Common King Procella Doll'
2x = 'Agathion Alpha Hunter Seale'   3x = 'Agathion Alpha Hunter Seak'
```

Em `scroll-transicao/frame_000016` o acordo estrito é **0 de 10** — a página inteira se perde
por causa de um `I` contra um `1`.
**How to avoid:** a decisão travada exige acordo entre as escalas; ela **não define o
predicado**, e a forma do acordo é área de implementação. A proposta que preserva a
diversidade de método e devolve o rendimento: **agrupar as DUAS leituras contra o catálogo e
exigir que as duas caiam na MESMA série.** Um erro de método real (um nome lido como outro
item) leva as duas a séries diferentes e a linha cai; `Lv. I` e `Lv. 1` caem na mesma e a
linha passa. **Esta é uma proposta, não uma decisão — precisa do usuário**, porque toca uma
decisão travada.
**Warning signs:** "li 2, perdi 8" no console com nomes visivelmente corretos no log.

### Pitfall 4: o recorte da coluna do nome NÃO basta contra a tooltip

**What goes wrong:** LEIT-05 nasceu para impedir que o texto da tooltip virasse nome de item.
Mas quando a tooltip cai **em cima da própria coluna do nome**, o recorte não ajuda. Medido em
`tooltip/frame_000015` com o recorte de coluna de 270 px:

```
linha4: 'same, but rnaterials disappear. Common Kng F"'
linha5: 'In case of success, you will get a high Common Kng F doll that cannot be exchanged.'
linha0: 'Common Kng IL Weight: O'
```
`[VERIFIED: medição desta sessão]`

**How to avoid:** exatamente o desenho já travado — a **sonda de oclusão é obrigatória** e é
ela que rejeita essas linhas (as mesmas linhas 0–7 medem 0,50–0,60 de dispersão contra 0,027
das limpas). LEIT-05 reduz a superfície; ele não fecha o buraco sozinho. **A ordem importa:
sonda de oclusão ANTES do OCR**, para não pagar 7 ms por uma linha que vai cair.

### Pitfall 5: o replay precisa de caminho absoluto e de fixtures cortadas

`recordings/` está no `.gitignore` e só existe no checkout principal
`[VERIFIED: .gitignore, "recordings/"]`. Um executor em worktree não o enxerga. O projeto já
resolveu isso: `tests/fixtures/mercado/` versiona **recortes** (a exceção `!tests/fixtures/`
está escrita e justificada no `.gitignore`), e já existem `glifos_precos_f010.png` e
`glifos_unitario_f010.png` — cortados exatamente do `pagina-cheia/frame_000010`
`[VERIFIED: ls tests/fixtures/mercado/]`.
**How to avoid:** a Wave 0 corta e versiona os recortes que os testes desta fase precisam
(linha limpa, linha coberta por tooltip, linha coberta por alvo, linha vazia, banda de
cabeçalho de cada layout). O teste de replay completo, que precisa das gravações, roda só no
checkout principal e se pula sozinho quando `recordings/` não existe — o padrão já usado em
`test_conferir_gravacoes_do_spike.py`.

### Pitfall 6: `pytest` roda no Python GLOBAL, não no `.venv`

Registrado no CONTEXT.md e confirmado por mim ao acidentalmente rodar um script sem o
interpretador do `.venv`: `l2scanner.ocr` levantou `AttributeError: 'NoneType' object has no
attribute 'recognize_async'` porque o Python global não tem as bindings WinRT — o motor sai
`None` e `_reconhecer` estoura, enquanto `_ler` (o caminho público) devolveria `None` limpo.
`[VERIFIED: reproduzido nesta sessão]`
**Consequência para os testes:** todo teste que exercite OCR de verdade tem de **pular** quando
`ocr.disponivel()` for `False`; e o caminho de produção tem de passar por `_ler`/`ler_texto`,
nunca por `_reconhecer` cru — `_ler` é o que tem a garantia *"NUNCA levanta"*
`[VERIFIED: l2scanner/ocr.py:198-208]`.

### Pitfall 7: o FLAKE conhecido do `test_agenda.py`

`tests/test_agenda.py` vaza um `KeyboardInterrupt` que aborta a sessão do pytest perto de ~88
testes (5 abortos em 60 rodadas). **Abortar não é falhar** — rode de novo. Baseline verde:
**1704 passed, 2 skipped** `[CITED: 02-CONTEXT.md §specifics]`.

---

## Code Examples

Todos abaixo são padrões **já existentes no repositório**, com o caminho e as linhas.

### Classificar um glifo (argmax + margem) — o que promover para produção

```python
# Fonte: l2scanner/calibrar_mercado.py:1620-1643 (propor_rotulo)
for inicio, fim in runs:
    recorte = mascara[topo:base, inicio:fim]
    pontuados: list[tuple[float, str]] = []
    for rotulo, molde in de_um_caractere.items():
        a, b = _alinhar_por_preenchimento(recorte, molde)
        if _par_incalculavel(a, b):
            continue
        pontuados.append((casamento_da_ancora(a, b), rotulo))
    if not pontuados:
        return None
    pontuados.sort(reverse=True)
    melhor_score, melhor_rotulo = pontuados[0]
    if melhor_score < MINIMO_PARA_PROPOR_ROTULO:      # em producao: limiar CALIBRADO
        return None
    segundo = pontuados[1][0] if len(pontuados) > 1 else -1.0
    if melhor_score - segundo < MARGEM_MINIMA_PARA_PROPOR:   # idem
        return None
    lido.append(melhor_rotulo)
```

**"TUDO OU NADA, de proposito: basta um run que nao passe no piso E na margem para a funcao
devolver `None`"** `[VERIFIED: l2scanner/calibrar_mercado.py:1614-1618]` — é a falha fechada de
LEIT-02 já escrita.

### Segmentar os glifos de uma célula

```python
# Fonte: l2scanner/calibrar_mercado.py:406-428 (segmentar_glifos)
mascara = mascara_de_texto(recorte)              # V > 180
linhas = np.flatnonzero(mascara.any(axis=1))
faixa = (int(linhas[0]), int(linhas[-1]) + 1)    # UMA faixa para o retangulo inteiro
runs = []
inicio = None
for coluna, tem_texto in enumerate(mascara.any(axis=0)):
    if tem_texto and inicio is None:
        inicio = coluna
    elif not tem_texto and inicio is not None:
        runs.append((inicio, coluna)); inicio = None
```

### A sonda de oclusão (NOVA — 10 linhas sobre primitivas existentes)

```python
# Padrao: mercado_geometria.fim_da_alternancia (2 linhas de folga em cada ponta,
# l2scanner/mercado_geometria.py:470-472) + a moda de extensao_do_separador (:399-401)
def dispersao_do_fundo(cinza_da_linha, x0: int, x1: int) -> tuple[int, float]:
    """(nivel de fundo, fracao de pixels fora dele) num trecho SEM texto."""
    sub = cinza_da_linha[2:-2, x0:x1]
    niveis, contagens = np.unique(sub, return_counts=True)
    moda = int(niveis[int(np.argmax(contagens))])
    fora = float((np.abs(sub.astype(np.int32) - moda) > TOLERANCIA_DE_NIVEL).mean())
    return moda, fora
```

Medido: limpa 0,024–0,073; tooltip 0,50–0,60; marcação de alvo 0,12. `TOLERANCIA_DE_NIVEL = 3`
é a constante já medida em `mercado_geometria.py:105`.

### Escrita atômica do catálogo

```python
# Fonte: l2scanner/loot.py:264-281 (Registro.designar)
temporario = pasta / f"{ARQUIVO}.tmp-{os.getpid()}"
temporario.write_text(conteudo, encoding="utf-8")
os.replace(temporario, pasta / ARQUIVO)
```

### Congelamento

```python
if anterior is not None and np.array_equal(janela, anterior):   # 0,89 ms medido
    iguais += 1
else:
    iguais = 0
anterior = janela
if iguais >= 2:      # 3 janelas consecutivas bit-identicas (decisao travada)
    ...  # captura congelada: avisa alto e NAO aceita pagina nenhuma
```

---

## Runtime State Inventory

Esta fase **não é** rename/refactor/migração — é código novo mais promoção de primitivas entre
módulos. Ainda assim, movimentar funções entre arquivos tem estado runtime associado, e o
inventário fica registrado:

| Categoria | Encontrado | Ação |
|---|---|---|
| Dados armazenados | **`calibration.json`** ganha chaves novas (coluna do nome, molde de cabeçalho, limiares de leitura). O arquivo existente tem 13 moldes de glifo e 3 âncoras que **não podem ser perdidos**. | A calibração é **load-mutate-save** — padrão já usado (`calibrar.py` 637-664 segundo `01-PATTERNS.md`). O `fundir_glifos` já protege o corte parcial `[VERIFIED: calibrar_mercado.py:1309-1325]`. Nenhuma migração de dado. |
| Configuração de serviço vivo | Nenhuma. O scanner não fala com serviço externo nesta fase. | Nenhuma. |
| Estado registrado no SO | Nenhum. `calibrar-mercado.bat` e `vigiar-party.bat` são launchers de arquivo, sem registro. | Nenhuma. |
| Segredos / variáveis de ambiente | Nenhum. Esta fase não toca token nem `.env`. | Nenhuma. |
| Artefatos de build / pacotes instalados | Se `rapidfuzz` entrar em `requirements.txt`, o `.venv` do usuário precisa de um `pip install -r`. O `vigiar-party.bat` já faz isso sozinho `[CITED: l2scanner/ocr.py:SEM_BINDINGS]`. **E o `test_firewall_escopo.py` varre o venv INSTALADO** — uma dependência nova passa por ele. | Confirmar que `rapidfuzz` não normaliza para nada da `BANIDAS` `[VERIFIED: tests/test_firewall_escopo.py:68-78 — {pyautogui, pydirectinput, pynput, keyboard, mouse, autoit, pyautoit, ahk, pywinauto}]`. Não normaliza. |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| `Windows.Media.Ocr` via `winrt-*` | LEIT-01 | ✓ | 3.2.1; `ocr.disponivel()` → `True` nesta sessão | nenhum — sem OCR, LEIT-01 não existe. `ocr.py` já degrada sem derrubar o produto. |
| Pacote de idioma `en-US` | idem | ✓ | `C:\Windows\OCR` traz `en-us` e `pt-br` | `try_create_from_user_profile_languages()` já é o fallback no código |
| `opencv-python` | tudo | ✓ | 4.14.0.94 | — |
| `numpy` | tudo | ✓ | 2.5.2 | — |
| **`rapidfuzz`** | LEIT-01 (agrupamento) | ✗ | — | **`difflib.SequenceMatcher` da stdlib** — ver §3 das perguntas |
| `recordings/` (8 gravações) | replay / medição | ✓ **só no checkout principal** | 335 frames de 2026-08-28 | recortes versionados em `tests/fixtures/mercado/` |
| Python do `.venv` | qualquer script que use OCR | ✓ `.venv/Scripts/python.exe` | — | **o `pytest` roda no Python GLOBAL, que NÃO tem WinRT** — ver Pitfall 6 |

**Missing dependencies with no fallback:** nenhuma.
**Missing dependencies with fallback:** `rapidfuzz` → `difflib` (stdlib), com o corte a
remedir.

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1` `[VERIFIED: .planning/config.json]`.
Esta fase não tem rede, autenticação, sessão nem usuário — é um leitor de pixels local. As
categorias que **de fato** aplicam:

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | não | sem identidade |
| V3 Session Management | não | sem sessão |
| V4 Access Control | não | processo único, dono único da máquina |
| **V5 Input Validation** | **sim** | `calibration.json` e o catálogo de nomes são **entrada não confiável** (arquivos que o usuário edita à mão). O padrão já existe e é explícito: *"O dict e ENTRADA NAO CONFIAVEL: veio de um arquivo que o usuario pode editar"* `[VERIFIED: l2scanner/mercado_visao.py:230-238]`, com conferência de dimensões antes do `reshape` e mensagem que diz o conserto. `glifos_de_calibracao` já recusa rótulo repetido, rótulo ausente e molde de altura divergente `[VERIFIED: l2scanner/mercado_visao.py:667-741]`. **Toda chave nova do `calibration.json` desta fase precisa da mesma validação.** |
| V6 Cryptography | não | nada a cifrar |
| **V12 File Handling** | **sim** | o catálogo é lido e escrito por caminho derivado da raiz do projeto (`RAIZ = Path(__file__).resolve().parent.parent`, `[VERIFIED: l2scanner/config.py:32]`), nunca de entrada do usuário. Escrita atômica via `os.replace` (§8). |

### Known Threat Patterns for este stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| `calibration.json` com dimensão mentida → `reshape` devolve molde silenciosamente errado → mercado fica invisível sem uma linha de erro | Tampering | conferir bytes contra dimensões declaradas ANTES do reshape (já implementado, replicar nas chaves novas) |
| Rótulo de glifo repetido → o segundo some calado | Tampering | `glifos_de_calibracao` já levanta com mensagem de conserto |
| Catálogo truncado por append interrompido → última linha malformada | Tampering / DoS | descartar a última linha malformada com aviso, **nunca** tratar o arquivo inteiro como corrompido (a mesma regra já travada para o CSV de observações em REQUIREMENTS.md) |
| Linha coberta por tooltip lida com confiança | Spoofing (a UI engana o leitor) | **a sonda de oclusão** — a mitigação central desta fase, e a lição do incidente 27x |
| Biblioteca de síntese de input entrando pela porta dos fundos | Elevation of Privilege (do escopo) | `tests/test_firewall_escopo.py` varre o venv instalado e o `requirements.txt`, com banlist de 9 nomes e normalização PEP 503 |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Nome do item por watchlist configurada (conjunto fechado por template) | **Nome por OCR + agrupamento por similaridade** | 2026-08-29, quick `260829-rd9` | LEIT-01 reescrito, LEIT-05 criado. `mercado_templates_de_nome` fica `None` para sempre. |
| Bordas de banda por derivada do perfil | **Trechos de nível constante** | Fase 1, `mercado_geometria.py:107-127` | a versão por derivada colapsava e dava 9 linhas em vez de 10 |
| Âncora única (faixa de título) com limiar 0,73 | **Votação multi-âncora**, limiar 0,73 POR ÂNCORA | Fase 1, plano 01-04 | margem de campo passou de −0,0643 para +0,3700 |
| Piso único de 0,95 para propor rótulo de glifo | **0,80 + margem 0,12** | Fase 1, `calibrar_mercado.py:1358-1385` | com 0,95 a ferramenta não propunha nada |
| Persistência em SQLite | **CSV com separador `;`** | 2026-08-29 | Fase 3; irrelevante para a Fase 2 exceto pela forma do catálogo |

**Deprecado / superado:**
- `mercado_templates_de_nome` e `mercado_limiar_de_template` — mortos pela mudança de LEIT-01;
  hoje `None` / `null` no `calibration.json`, e **assim devem ficar**.
- A tabela de custo de OCR de 1x=44/2x=158/3x=308/4x=680 ms — já refutada no próprio
  `ocr.py:65-70`, e agora refutada de novo pela medição no recorte real (2,9 / 4,1 ms).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | O nome `rapidfuzz` veio do `CLAUDE.md` (memória destilada), não de documentação oficial descoberta nesta sessão | Standard Stack, Package Legitimacy | baixo — o wheel foi baixado do PyPI e inspecionado; mas a regra do projeto pede confirmação humana antes de instalar |
| A2 | O corte de brilho `V > 210` separa rótulo de cabeçalho (máx. 229) da seta (máx. 181) em **todas** as peles/resoluções | Pergunta 6 | médio — medido em 4 frames e no censo dos 335, mas numa única resolução (1720×1392) e numa única pele. O limiar tem de ir para `calibration.json`, não para o código |
| A3 | O trecho x∈[180,510) é "sem texto" em toda linha do layout de negociação | Pergunta 4 | médio — medido em 3 frames × 10 linhas. Um item com nome muito longo poderia invadir. Mitigação: derivar o trecho da geometria da coluna calibrada, e conferir na calibração que ele está vazio na página mostrada |
| A4 | Um limiar de dispersão em torno de 0,10 separa "limpa" de "coberta" | Pergunta 4 | **alto** — a marcação de alvo mediu 0,12 em UM frame contra 0,027 das limpas. A folga é de ~4×, não de 20×. **Este número precisa de varredura sobre as 8 gravações antes de virar constante** |
| A5 | Cortar um molde de glifo por paridade de banda de fundo elevaria as medianas de `0` e `8` | Pitfall 2 | médio — é a explicação que o código já registra para a variação, mas eu **não medi** o resultado do conserto |
| A6 | O acordo "as duas escalas caem na mesma série" preserva a diversidade de método | Pitfall 3 | médio — é raciocínio, não medição. Um erro de método que leve as duas escalas ao mesmo item errado passaria. Contra-argumento: o erro de método medido (`I`↔`1`, `Kng`↔`King`) é sempre de 1–2 caracteres, e um erro que trocasse o item inteiro seria muito maior |
| A7 | A quantidade (coluna `Quantity`) se lê pelo mesmo pipeline do preço | Pergunta 1 | médio — **não medi a coluna `Quantity`**, só a de preço. Ela não tem sufixo `XM Coin`, então `numeros_com_sufixo` não a acha; com retângulo calibrado o resto do pipeline deveria valer, mas isso é dedução |
| A8 | Os moldes de dígito, cortados da coluna de preço, casam também os dígitos DENTRO do nome (`+6`, `Lv. 3`) | Pergunta 3, proposta 3 | **alto** — brilho, tamanho e antialias do texto de nome podem diferir dos do preço. É a medição que decide se a proposta 3 é viável |
| A9 | O par `Common Fafuri` / `Common Fafuri 1` da minha tabela é real | Pergunta 3 | baixo — ele saiu de um vazamento de tooltip, não de um item real. Não usei ele para concluir nada |

---

## Open Questions

1. **🚩 O layout calibrado é `adena`, mas LEIT-01/LEIT-05 só existem na grade de negociação —
   e ~283 de ~308 frames de fixture são negociação.**
   - O que sabemos: a aba Adena não tem nome de item (medido: OCR devolve `'Adena'`); o censo
     de layouts está feito; a decisão "só o layout calibrado" é travada e correta.
   - O que não sabemos: se o usuário quer recalibrar para a negociação, ou se prefere a
     calibração de produção em Adena com o replay usando uma calibração de fixture.
   - Recomendação: **perguntar antes de planejar**. Recalibrar é o caminho que mantém produção
     e teste no mesmo layout, e é o único em que o critério de sucesso 1 da fase é
     demonstrável.

2. **🚩 Os moldes de dígito servem para ler o `+N` e o `Lv. N` DENTRO do nome?**
   - O que sabemos: eles leem a coluna de preço com 25/25 de acerto; a fonte do jogo é a mesma;
     `mascara_de_texto` (V>180) é o piso do texto claro.
   - O que não sabemos: se o texto do nome tem o mesmo brilho e o mesmo tamanho do preço.
   - Recomendação: **Wave 0, uma medição de 30 minutos** — rodar `segmentar_glifos` +
     `propor_rotulo` sobre o recorte do prefixo de encanto em `063752-mercado-aberto/frame_000000`
     (as dez linhas `+6/+4/+2/+7/(nenhum)/+5/+7/+5/+7/+6` são um gabarito pronto e conhecido).
     Se casar, a proposta 3 da §3 fica disponível e o problema `Lv. 1`×`Lv. 3` some por
     construção.

3. **🚩 Qual predicado de "acordo" entre 2x e 3x?**
   - O que sabemos: igualdade de string rende 50%; as discordâncias medidas são de 1–2
     caracteres.
   - O que não sabemos: se o usuário aceita "concordam quando caem na mesma série" como forma
     do acordo travado.
   - Recomendação: apresentar as duas taxas medidas e deixar ele decidir. É uma decisão de
     produto (perder metade das leituras vs. afrouxar o guard), não técnica.

4. **Qual o limiar de LEITURA de glifo, e qual a margem?**
   - O que sabemos: a distribuição de 2.057 glifos (p5 = 0,7242 de score; p5 = 0,0607 de
     margem); que 0,8555 rejeita 18% e que 0,12 de margem rejeita 7%.
   - O que não sabemos: o número certo — ele depende de os moldes serem melhorados ou não.
   - Recomendação: ferramenta de varredura que produz a distribuição e propõe o par
     (piso, margem), gravando em chaves próprias. Nunca herdar `mercado_limiar_de_glifo`.

5. **A coluna `Quantity` lê pelo mesmo caminho?**
   - O que sabemos: ela não tem sufixo de moeda, então `numeros_com_sufixo` não a localiza;
     em compensação, com retângulo calibrado a localização deixa de ser problema.
   - O que não sabemos: se a quantidade tem separador de milhar e como o carimbo de quantidade
     desenhado sobre o ÍCONE (medido: gera lixo como `'436,569,,,96,5,3'`) interfere.
   - Recomendação: medir na mesma Wave 0, com o mesmo gabarito de
     `scroll-transicao/frame_000012` (quantidades 10, 5, 48 registradas no spike §4).

6. **Existe um cross-check independente para os números?**
   - O que sabemos: na grade de negociação, `Total ÷ Quantity ≈ Unit price` com arredondamento
     conhecido a 2 casas (medido no spike: `40,00 ÷ 48 = 0,8333…` exibido como `0,83`). Isso é
     uma **segunda leitura independente** do mesmo fato — exatamente a diversidade de método
     que falta ao caminho de dígitos, cujo estabilizador é cego a erro de método.
   - O que não sabemos: se a relação fecha em todas as linhas das gravações, e qual a
     tolerância honesta (`|total − unit × qty| ≤ qty / 200`, meio centésimo por unidade?).
   - Recomendação: **medir**. Se fechar, é a guarda mais forte disponível contra o `0`↔`8`, e
     custa três linhas. É uma proposta de mecanismo novo — o planner deve levá-la ao usuário
     antes de virar tarefa, porque adiciona uma coluna à leitura.

---

## Sources

### Primary (HIGH confidence) — medido ou lido nesta sessão

- **`recordings/`** (8 gravações, 335 frames de 2026-08-28) — todas as medições numéricas
  deste documento. Somente leitura; nada foi escrito.
- **`calibration.json`** desta máquina — 13 moldes de glifo decodificados, 3 âncoras,
  `mercado_grade`, `mercado_limiar_de_glifo`.
- **`l2scanner/calibrar_mercado.py`** — `segmentar_glifos` (359-428), `_alinhar` (242-256),
  `_alinhar_por_preenchimento` (501-527), `_par_incalculavel` (529+), `propor_rotulo`
  (1596-1643), `numeros_com_sufixo` (1463-1509), `_cauda_apagada` (1418-1461),
  `_grupos_de_colunas` (1390-1416), `matriz_de_confusao` (258-295), constantes 356/453/1283-1387.
- **`l2scanner/mercado_visao.py`** — `casamento_da_ancora` (102-136),
  `CASAMENTO_MINIMO_DA_ANCORA` (171), `glifos_de_calibracao` (667-741), `molde_de_hex` (227+).
- **`l2scanner/mercado_geometria.py`** — charter (1-9), constantes (96-153),
  `perfil_por_mediana`, `trechos_de_nivel`, `bordas_de_banda`, `fim_da_alternancia` (437-486).
- **`l2scanner/ocr.py`** — tabela de escalas (28-79), `_ler`/`_reconhecer` (198-260).
- **`l2scanner/identidade.py`** — `VALOR_MINIMO_DO_TEXTO` (56), `LIMIAR_DE_CASAMENTO` (109),
  `MARGEM_MINIMA_SOBRE_O_SEGUNDO` (113).
- **`l2scanner/loot.py`** (195-281) — o padrão de escrita atômica e de estado durável.
- **`tests/test_firewall_escopo.py`** (60-113) — a banlist FIRE-01 e a normalização PEP 503.
- **`.gitignore`**, **`.planning/config.json`**, **`requirements.txt`**, listagem do `.venv`.
- **`rapidfuzz-3.14.5-cp312-cp312-win_amd64.whl`** baixado do PyPI — `METADATA` e
  `rapidfuzz/fuzz_py.py` (a implementação de referência do `WRatio`, executada nesta sessão).

### Secondary (MEDIUM confidence)

- `SPIKE-RESPOSTAS.md` (Fase 1) — validado pelo usuário seção por seção. Reproduzi
  independentemente §1 (10 linhas de 45 px), §2 (48/66 e a vírgula dupla), §3 (três layouts,
  a seta que anda), §4 (os valores de preço), §9 (o painel bit-estável).
- `260829-rd9-EVIDENCIA-SPIKE-OCR.md` — reproduzi o Resultado 1 (nomes lidos, estáveis) e o
  Resultado 3 (vazamento de tooltip). O Resultado 2 (números não são lidos pelo OCR) não
  reexecutei: ele é a premissa de LEIT-02 e não mudou.
- `gsd-tools query package-legitimacy check --ecosystem pypi rapidfuzz` — veredito `SUS`
  por `unknown-downloads` (limitação da API do PyPI, não sinal de risco).

### Tertiary (LOW confidence)

- `.claude/CLAUDE.md` §Technology Stack — é pesquisa destilada em documento, não estado do
  `.venv`. **Verifiquei e boa parte dela é aspiracional:** `pydantic`, `requests`, `rich`,
  `python-dotenv`, `uv`, `rapidfuzz` **não estão instalados**. O que está instalado é
  `mss` + `opencv` + `numpy` + `winrt-*` + `discord.py` + `windows-capture`. Um plano que
  assuma o CLAUDE.md como inventário vai propor tarefas contra bibliotecas que não existem
  aqui.
- `https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html` — consultada; **não documenta** o
  algoritmo do `WRatio` (só diz "weighted ratio based on the other ratio algorithms"). Por
  isso fui ao fonte distribuído no wheel, que é primário.

---

## Metadata

**Confidence breakdown:**
- **Leitura de dígitos: HIGH** — pipeline rodado ponta a ponta, 25 preços corretos, 2.057
  glifos classificados, distribuição de score e margem medida.
- **Custo / orçamento: HIGH** — medido no recorte real, motor aquecido, 5 repetições.
- **Oclusão: MEDIUM-HIGH** — separação de uma ordem de grandeza para tooltip é sólida; o caso
  da marcação de alvo (4×) foi medido em um frame só e o limiar precisa de varredura.
- **Agrupamento de nome: HIGH no diagnóstico, MEDIUM na solução** — que `WRatio`+88 funde as
  séries motivadoras está provado contra o fonte do rapidfuzz. Qual métrica e qual chave de
  série substituem é proposta que depende da medição do Open Question #2.
- **Layout / cabeçalho: HIGH** — censo dos 335 frames, três assinaturas separadas, seta
  localizada ao pixel e separável por brilho.
- **Catálogo em disco: MEDIUM** — o precedente é claro (`.loot/`, `os.replace`); a forma
  exata é discrição declarada do usuário.

**Research date:** 2026-08-29
**Valid until:** 2026-09-28 — ou até a próxima calibração do usuário, o que vier primeiro. As
medições contra `recordings/` não expiram (as gravações são imutáveis); o que expira é o
`calibration.json`, que a recalibração reescreve inteiro.
