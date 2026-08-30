# Phase 2: Leitura de página - Context

**Gathered:** 2026-08-29
**Revised:** 2026-08-29, depois da pesquisa — três decisões caíram por medição
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — 4 áreas propostas, 16 decisões, todas aceitas pelo usuário

> **TRÊS DECISÕES DESTE ARQUIVO FORAM SUBSTITUÍDAS NO MESMO DIA.** A `02-RESEARCH.md` mediu
> as propostas e refutou três delas; o usuário confirmou as substituições. As decisões
> antigas ficam registradas abaixo, riscadas e com o número que as derrubou — apagar teria
> escondido que o processo funcionou. As três são: o scorer de agrupamento (`WRatio` + 88),
> o predicado de acordo entre escalas, e QUAL layout se calibra.

<domain>
## Phase Boundary

Contra as fixtures gravadas na Fase 1, esta fase entrega a LEITURA de uma página do World
Exchange: reconhecer o nome de cada linha visível, ler preço e quantidade, e aceitar a
página só quando ela se provou parada. Ela NÃO persiste nada (Fase 3), NÃO tem modo de
invocação próprio e NÃO liga a oclusão ao detector de morte (as duas são Fase 4).

**A fronteira que mudou em 2026-08-29 (quick `260829-rd9`):** o nome do item deixou de vir
de uma watchlist configurada e passa a vir por OCR, agrupado por similaridade contra os
nomes já vistos. Item desconhecido vira série nova sem o usuário configurar nada. Isso
nasceu de medição: o OCR do Windows lê os NOMES de forma estável nas gravações de campo, e
NÃO lê os NÚMEROS — ele perde a vírgula decimal e devolve `1650` onde a tela diz `16,50`.
A evidência está em `260829-rd9-EVIDENCIA-SPIKE-OCR.md`, no diretório daquela quick task.

Requisitos: LEIT-01 (nome por OCR + agrupamento), LEIT-02 (preço/quantidade por molde de
dígito, falha FECHADA), LEIT-03 (acordo entre dois frames), LEIT-05 (recorte da coluna do
nome, nunca a linha inteira).

</domain>

<decisions>
## Implementation Decisions

### Leitura do nome por OCR

- **Duas escalas de OCR (2x e 3x) que precisam CONCORDAR; discordância descarta a linha.**
  É o desenho que `l2scanner/ocr.py` já usa e documenta (D-d, diversidade de método), e a
  medição de 2026-08-29 mostrou as escalas divergindo exatamente onde o motor erra
  (`Evolution` em 2x/3x contra `Ewlution` em 4x). Duas leituras pelo MESMO método concordam
  no mesmo erro; é por isso que a segunda opinião tem de ser um método diferente.
- **O PREDICADO do acordo é "as duas leituras caem na MESMA SÉRIE do catálogo"** — não
  igualdade de string. **REVISADO 2026-08-29 por medição:** a igualdade estrita acertou 30 de
  60 linhas em 6 frames, e em `scroll-transicao/frame_000016` acertou **0 de 10** — a página
  inteira perdida por um `I` contra um `1`. As discordâncias medidas são todas ruído de 1–2
  caracteres (`Lv. I`/`Lv. 1`, `Kng`/`King`), que o agrupamento absorve. A diversidade de
  método fica preservada: um erro de método REAL — um nome lido como outro item — leva as
  duas escalas a séries diferentes e a linha cai.
  ~~Predicado original: igualdade exata de string entre as duas escalas.~~
- **Agrupamento por `difflib.SequenceMatcher` (stdlib), E uma trava de dígitos: a sequência
  ordenada de dígitos do nome tem de bater EXATAMENTE antes de qualquer similaridade.**
  **REVISADO 2026-08-29 por medição** — a proposta anterior era `rapidfuzz.WRatio` com corte
  88, e ela funde exatamente as séries que existia para separar. Rodada contra a
  implementação de referência do rapidfuzz 3.14.5:

  | par | WRatio | precisa |
  |---|---|---|
  | `Common Aztac` × `Common Aztac M. Def. +200` | **90,00** | separar |
  | `+6 Agathion Alpha Hunter Sealed` × `+4 …` | **96,77** | separar |
  | `Hardin's Soul Crystal Lv. 1` × `Lv. 3` | **96,30** | separar |
  | `Hardin's Soul Crystal Lv. I` × `Lv. 1` | **96,30** | **agrupar** (ruído de OCR) |

  As duas últimas linhas são o achado que decide o desenho: **o mesmo número teria de decidir
  coisas opostas.** Nenhum corte escalar resolve, em nenhuma métrica de distância de edição —
  e os três casos aparecem juntos num frame real. Por isso a trava de dígitos: `+6 X` ≠
  `+4 X` e `Lv. 1` ≠ `Lv. 3` **por construção**, não por limiar. A similaridade decide só o
  resto do nome.
  ~~Scorer original: `rapidfuzz.WRatio` com corte 88 e faixa cinzenta 80–88.~~
- **`difflib` da stdlib, e NÃO `rapidfuzz`.** `rapidfuzz` não está instalado nem no
  `requirements.txt`, e medido sobre estes nomes (curtos, sem tokens reordenados, diferenças
  de 1–2 caracteres) `difflib.SequenceMatcher` e `rapidfuzz.fuzz.ratio` dão praticamente o
  mesmo número. Não vale uma dependência nova para 10 linhas por segundo contra um catálogo
  de algumas centenas de nomes.
- **O CORTE precisa ser REMEDIDO, e com ferramenta.** O 88 foi escolhido pensando no
  `WRatio`, que é um scorer composto; trocada a métrica, o número é herança de outro
  contexto. Remedir é o jeito da casa: uma ferramenta que passa todas as leituras das 8
  gravações pela métrica escolhida e mostra o histograma dos pares que agrupam e dos que
  separam. **Nenhum corte entra no código antes dessa medição.**
- **A faixa cinzenta continua existindo** — abaixo do corte e acima de um piso, a linha não
  agrupa NEM cria série: é descartada com aviso. Fusão no CSV é irreversível; descarte não é.
- **O catálogo de nomes já vistos vive em ARQUIVO PRÓPRIO, ao lado do CSV de observações.**
  Não em `calibration.json`: aquele arquivo é reescrito inteiro pela ferramenta de
  calibração, e o catálogo é dado ACUMULADO — sumiria na primeira recalibração.
- **Nome novo entra DIRETO como série nova, com contagem de avistamentos e data da primeira
  vez.** Sem quarentena: a quarentena esconderia a primeira aparição, que é justamente o
  evento que o usuário quer ver. A contagem deixa ele julgar no Sheets. O acordo entre
  escalas e a faixa cinzenta já são os filtros.

### Coluna do nome e os três layouts

- **O v1 lê SOMENTE o layout que está calibrado — e o layout calibrado passa a ser a GRADE DE
  NEGOCIAÇÃO** (`Goods | Quantity | Total | Unit price | Buy`). Página de outro layout é
  RECUSADA com aviso alto, nunca lida. O spike mediu três layouts com colunas e significados
  diferentes (a aba Adena tem `5 mln increment`, normalizado por 5 milhões de adena e NÃO por
  unidade) — ler a coluna errada com confiança é o modo de falha que esta fase existe para
  impedir.
  **REVISADO 2026-08-29 por medição.** O `calibration.json` da máquina do usuário dizia
  `layout: "adena"`, e isso quebrava a fase por dois motivos independentes:
  1. **Material:** censo das 335 gravações — ~25 frames de Adena contra ~283 da grade de
     negociação. O replay recusaria 283 dos ~308 frames com painel aberto, e o critério de
     sucesso 1 não seria demonstrável contra as fixtures que existem.
  2. **Mais forte que material: a aba Adena não tem nome de item.** A mercadoria ali É adena;
     o OCR da primeira coluna devolve literalmente `'Adena'` em todas as linhas. **LEIT-01
     (nome por OCR) e LEIT-05 (coluna do nome) não têm objeto na aba Adena** — eles descrevem
     a grade de negociação.

  ~~Layout original: o que estivesse em `mercado_grade.layout`, que era `adena`.~~

- **PORTÃO HUMANO — o usuário recalibra.** Escolhido por ele em 2026-08-29 sobre a
  alternativa de dar ao teste uma calibração de fixture própria: aquela não custaria nada ao
  usuário, mas deixaria produção e teste calibrados em layouts DIFERENTES, que é exatamente a
  divergência que este projeto evita. O plano precisa parar e esperar: `calibrar-mercado.bat`
  rodado sobre um frame da grade de negociação, com `mercado_grade.layout` gravado como tal.
  Frames de negociação bons para calibrar estão em `<specifics>`.
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

### Oclusão e recusa — a lição do incidente 27x

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

### Estabilizador de página e cadência

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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`l2scanner/ocr.py`** — o motor de OCR do Windows já embrulhado, com o import do WinRT
  DENTRO das funções (ausência das bindings desliga o recurso, nunca o produto), conversão
  para cinza antes de tudo (D-a) e tabela de escalas MEDIDA contra a fonte real do jogo.
  `_reconhecer(pixels, escala)` é o caminho cru. As bindings `winrt-*` 3.2.1 já estão no
  `.venv` e `C:\Windows\OCR` traz `en-us` e `pt-br`.
- **`l2scanner/mercado_visao.py`** — `localizar_painel` (aquisição por varredura),
  `conferir_painel`, `RastreioDoPainel` (seguimento barato), `ancoras_de_calibracao`,
  `glifos_de_calibracao` e a validação dos moldes. A votação multi-âncora já existe e foi
  medida em 6 de 6 frames de condições diferentes.
- **`l2scanner/mercado_geometria.py`** — `medir_a_grade`, `perfil_por_mediana`,
  `trechos_de_nivel`, `bordas_de_banda`, `cadeia_periodica`, `fim_da_alternancia`. A
  segmentação por projeção de coluna que corta os glifos já está aqui.
- **`l2scanner/identidade.py`** — o precedente medido de reconhecimento por conjunto fechado
  (`matchTemplate`, 1.000 no acerto contra 0.454 no erro). É o modelo para a leitura de
  DÍGITO, não mais para a de nome.
- **`calibration.json`** (gitignored, estado de máquina) — hoje: 3 âncoras, grade de 10
  linhas de 45 px com `layout: "adena"` e deslocamento `dx=-428 dy=258`, geometria de
  captura 1720x1392, **13 moldes de glifo** (`0-9`, vírgula, `XM Coin`, `Adena`) e
  `mercado_limiar_de_glifo = 0.8555`. `mercado_templates_de_nome` está `None` e
  `mercado_limiar_de_template` está `null` — sem número inventado.

### Established Patterns

- **Falha fechada, sempre.** Frame ilegível é descartado, nunca interpretado. É o princípio
  fundador do projeto depois do incidente 27x (um painel de UI lido como 27 alertas de morte
  falsos).
- **Nada de constante mágica no código** — todo limiar mora no `calibration.json`, produzido
  por ferramenta que mede.
- **Degradar, avisar alto, e deixar o scanner subir** (`montar_despachante`, `ocr.py`).
- **Um número que caiu precisa dizer que caiu** — medições refutadas ficam registradas no
  código junto com a que as substituiu.

### Integration Points

- A leitura NÃO toca `l2scanner/rastreador.py` nem o gate de brilho da barra própria em
  `l2scanner/visao.py` (`barra_propria_legivel`, `_moldura_da_barra_propria`,
  `_bordas_da_barra_intactas`). Acoplar o sinal de mercado ao detector de morte é
  precisamente a manobra que causou o incidente 27x; o consumidor de oclusão é DETC-02, na
  Fase 4.
- A saída desta fase é a "página aceita" que a Fase 3 consome para escrever o CSV.
- `calibrar_mercado.py` ganha a marcação da coluna do nome (LEIT-05) e o molde do cabeçalho
  de coluna, no fluxo propor-e-confirmar já existente.
- **FIRE-01 continua valendo:** nenhuma biblioteca de síntese de input entra na árvore de
  dependências (`pyautogui`, `pydirectinput`, `pynput`, `keyboard`, `mouse`, autoit/AHK).

</code_context>

<specifics>
## Specific Ideas

- As fixtures são as 8 gravações de 2026-08-28 em `recordings/` — **somente leitura, e só
  existem no checkout principal** (gitignored). Um executor em worktree precisa lê-las por
  caminho absoluto.
- Frames de referência já citados pelo spike, úteis como casos de teste nomeados:
  - página cheia, 10 linhas: `20260828-060622-mercado-pagina-cheia/frame_000010.png`
  - 1 linha cheia + 8 vazias: `20260828-055323-mercado-scroll/frame_000009.png`
  - tooltip sobre 8 linhas + cabeçalho: `20260828-061253-mercado-tooltip/frame_000015.png`
  - tooltip sobre a faixa de título (a âncora): `20260828-055323-mercado-scroll/frame_000084.png`
  - marcação de alvo sobre o nome da linha 1: `20260828-061409-mercado-alvo-sobreposto/frame_000024.png`
  - dois frames de rolagem, conteúdo totalmente diferente e AMBOS nítidos:
    `20260828-063409-mercado-scroll-transicao/frame_000016.png` e `frame_000017.png`
  - o arredondamento do unitário (`40,00 ÷ 48` exibido como `0,83`):
    `20260828-063409-mercado-scroll-transicao/frame_000012.png`
- **A vírgula é ambígua e a desambiguação vem do SUFIXO, não do número:** `5,000,000 Adena` e
  `62,00 XM Coin` aparecem na mesma linha. Por isso `XM Coin` e `Adena` são moldes de
  primeira classe entre os 13 já cortados. Nenhum PONTO apareceu como separador em 335
  frames.
- **O unitário exibido é derivação arredondada, não dado.** A Fase 3 guarda `Total` e
  `Quantity`; reconstruir o total a partir do unitário devolve um número que nunca existiu
  (`0,83 × 48 = 39,84`).
- **FLAKE conhecido e pré-existente:** `tests/test_agenda.py` vaza um `KeyboardInterrupt` que
  aborta a sessão do pytest perto de ~88 testes (5 abortos em 60 rodadas). **Abortar não é
  falhar** — rode de novo. Baseline verde: **1704 passed, 2 skipped**. E o pytest roda no
  Python GLOBAL, não no `.venv`.

</specifics>

<deferred>
## Deferred Ideas

- **Ler os outros dois layouts** (grade de negociação e tela de busca). Cada um exige a sua
  própria calibração de colunas; o v1 recusa o que não está calibrado.
- **Idade do anúncio** e a tela de detalhe/confirmação de compra — o spike ficou devendo
  material (seção 10, item 10) e a pergunta perdeu urgência quando o usuário decidiu
  registrar o que foi visto no dia.
- **Truncamento de nome longo com prefixo de encanto** — o usuário informou que nenhum item
  tem nome com reticências, então a população é vazia; fica registrado caso apareça.
- **Outras janelas do Menu sobrepondo o painel** — edge case raro informado pelo usuário na
  Fase 1. O inventário NUNCA sobrepõe (abrir o inventário FECHA o mercado).
- **A watchlist como filtro de DESTAQUE no console** — ela deixou de ser a porta de entrada
  do que é registrado; se sobreviver, é território de ANAL-* na Fase 4.
- **Alerta de oportunidade no WhatsApp** (WAPP-02) — já registrado como Out of Scope do v1.

</deferred>
