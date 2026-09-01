# Phase 1: Dashboard do cambio ao vivo - Context

**Gathered:** 2026-09-01
**Status:** Ready for planning
**Mode:** Smart discuss (autônomo, 4 áreas, todas aceitas como propostas)

<domain>
## Phase Boundary

Uma página no navegador local (`127.0.0.1`, porta fixa) responde **"quanto vale 1 milhão de
adena agora, em XM e em R$"** e mostra a história dessa taxa com zoom — lendo o
`.mercado/observacoes.csv` que o `--mercado` já grava, em processo próprio, **sem tocar na
coleta**.

**Dentro:** o servidor local, o endpoint de dados, a página (destaque + gráfico + procedência),
o câmbio XM→BRL informado à mão e persistido, o `dashboard.bat`, e os testes que provam tudo
isso sem navegador.

**Fora:** qualquer alteração no caminho do `--mercado` (ele fica byte-idêntico); a aba de
negociação na tela (o componente nasce genérico, mas só a Adena é instanciada); acesso pela
rede ou pelo celular; coleta automática do câmbio XM→BRL (é seed, não é esta fase).
</domain>

<decisions>
## Implementation Decisions

### A superfície — o que aparece na tela

- **Layout:** número grande no topo (o valor de agora), gráfico abaixo, rodapé com a
  procedência (`n`, recência, câmbio informado e quando). A pergunta do usuário é uma só,
  então uma coisa domina a tela.
- **Dois números no destaque, lado a lado:** **XM por milhão** (a unidade que ele fala em voz
  alta, já implementada em `mercado_console.formatar_taxa_derivada`) **e R$ por milhão**. Os
  dois carregam `n` e recência, como toda a disciplina do console de mercado exige.
- **Tema escuro E TEMÁTICO DE LINEAGE 2** (decisão do usuário, acrescentada em 2026-09-01
  depois das quatro áreas). Não é um dashboard genérico de analytics: é um painel do jogo,
  aberto ao lado do cliente, à noite, numa segunda tela. A identidade visual conversa com a UI
  do L2 — moldura/relevo escuro, dourado e âmbar dos painéis do jogo, tipografia com peso de
  fantasia nos títulos e algo legível e monoespaçado nos números. **O tema nunca custa
  legibilidade do número**: se um ornamento disputar com o valor em destaque, o ornamento sai.
- **Estado vazio é conteúdo, não ausência.** Hoje o CSV tem 93 linhas e **zero** com a
  sentinela `adena#` — a aba Adena foi construída na Fase 5 do mercado e nunca rodou em campo.
  Sem leitura da Adena, a página diz isso com todas as letras e explica como coletar (abrir a
  aba Adena com o `vigiar-mercado.bat` rodando). **Gráfico vazio mudo está proibido**: seria
  indistinguível de "o dashboard quebrou".

### O dado e a atualização

- **Atualização por polling:** o navegador consulta um endpoint JSON local a cada ~2s; o
  servidor relê o CSV quando `mtime`/tamanho mudam. Sem WebSocket, sem SSE — a coleta é 1 Hz e
  não justifica a peça a mais.
- **O arquivo inteiro é carregado.** 93 linhas hoje, crescendo devagar. Filtrar o zoom no
  navegador é mais simples e mais correto que paginar no servidor.
- **Um ponto do gráfico é um instante de leitura** (`primeira_vez`), com o menor pedido visível
  e a mediana daquele instante — exatamente a conta que o console já faz via `mercado_analise`.
  Não é uma nuvem de ofertas individuais.
- **Zoom largo agrega com `median_low`**, nunca média. É o D-02 do projeto: um número exibido
  tem de ter existido. A Fase 4 do mercado já recusou `statistics.median` pela mesma razão
  (inventa meio centavo com `n` par).

### O câmbio XM → BRL

- **Persiste em `.mercado/cambio.json`**, escrito pelo dashboard. Mesma pasta do dado do
  usuário, já gitignored. Fora do `calibration.json` (que o mercado só lê, nunca escreve) e
  fora do `config.toml` (o `tomllib` da stdlib é read-only). `localStorage` foi recusado: some
  quando o usuário limpa o navegador.
- **A entrada é em reais por 1 XM** (`0,50`), do jeito que o usuário falou.
- **Cada alteração é guardada com carimbo**, e a última é a vigente. Custa uma linha e é
  exatamente a estrutura que o listener dos grupos de WhatsApp vai preencher no v2.
- **Os pontos históricos em R$ usam o câmbio de hoje**, com o aviso na tela ("R$ calculado com
  o câmbio informado hoje"). Com um único valor informado não existe série de câmbio, e a
  pergunta que o usuário faz é "vale a pena agora". Aplicar câmbio de época é v2 e depende do
  histórico que esta fase começa a acumular.

### O processo, o servidor e a prova

- **`http.server` da stdlib — zero dependência Python nova.** Nada entra no `requirements.txt`.
- **A biblioteca de gráfico JS é vendorizada na árvore** (arquivo único, sem CDN, sem rede).
  Zoom/pan sobre série temporal é precisamente onde código à mão apodrece. Vendorizar não fere
  a doutrina de zero-install: não há instalador, não há `pip`, não há rede — o custo é um
  arquivo versionado, e ele precisa de proveniência escrita (nome, versão, licença, de onde
  veio) no fonte ou num README ao lado.
- **Bind em `127.0.0.1` apenas, nunca `0.0.0.0`**, em porta fixa. Esta máquina roda o jogo e
  está na rede da casa; expor o servidor não foi pedido e não é aceitável de graça. O `.bat`
  abre o navegador sozinho.
- **A única escrita do servidor é o `.mercado/cambio.json`.** O `observacoes.csv` é aberto em
  modo leitura, e há teste provando que tamanho e mtime não mudam depois de uma sessão.
- **A prova sem navegador** é por testes sobre o endpoint JSON e sobre as funções de agregação
  (puras). O desenho na tela fica como **verificação humana declarada** no fim da fase — é o
  que a casa já faz com o OCR real e o congelamento de captura. Playwright foi recusado:
  instalador pesado, contra a doutrina.

### Claude's Discretion

- Nome do módulo, nome do endpoint, porta escolhida, e qual biblioteca de gráfico exatamente
  (o critério é: arquivo único, licença permissiva, zoom/pan nativo, sem dependência de rede).
- A forma interna do JSON servido e a estrutura do `cambio.json`.
- Como o componente de série é generalizado (DASH-05) — só o resultado está travado: instanciar
  uma segunda série não pode exigir código de gráfico novo.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`l2scanner/mercado_registro.py`** — `observacoes_do_arquivo(arquivo) -> list[ObservacaoLida]`,
  `ARQUIVO_DE_OBSERVACOES`, `PASTA_DO_MERCADO`, `SEPARADOR`, `COLUNAS`,
  `conferir_o_terminador`, `conferir_o_cabecalho`, `ContratoDoArquivoQuebrado`. **É o único
  parser do CSV e tem que continuar sendo** — a Fase 4 do mercado extraiu os portões para
  funções de módulo exatamente para não haver um segundo.
- **`l2scanner/mercado_analise.py`** — `menor_pedido_visivel`, `mediana_dos_unitarios`,
  `tendencia`, `unitario`, `recencia_do_preco`, `ModeloDeMercado`, `Evidencia`, e os pisos
  `N_MINIMO_PARA_MENOR=1` / `N_MINIMO_PARA_MEDIANA=5` / `N_MINIMO_PARA_TENDENCIA=8`. Tudo puro,
  tudo em `Fraction`.
- **`l2scanner/mercado_console.py`** — `formatar_taxa_derivada(taxa)` devolve
  `"11,60 XM por milhao de adena (derivado)"`, com `UNIDADE_DA_TAXA = 1_000_000` e a conta
  escrita por extenso; `formatador_do_unitario(chave)` decide entre a taxa e o unitário comum
  a partir da chave-sentinela. **Um ponto de decisão só** — não replicar o `if`.
- **`l2scanner/mercado_catalogo.py`** — `CHAVE_DA_SERIE_DA_ADENA = "adena#"`,
  `SEPARADOR_DA_ASSINATURA`. É a sentinela que identifica a série da Adena, e ela não vem de
  OCR nenhum.
- **`vigiar-mercado.bat`** — o molde do lançador: resolve o Python, monta/atualiza o `.venv`,
  sonda dependências, e **os blocos de erro vêm ANTES da linha de execução com `goto` por
  cima** (defeito medido em campo em 2026-08-28).

### Established Patterns

- **Formato do dado:** `.mercado/observacoes.csv`, separador `;`, seis colunas
  (`chave_da_serie;nome_exibido;primeira_vez;total_em_centesimos;quantidade;residuo_do_cruzamento`),
  `primeira_vez` em ISO com microssegundos, terminador de linha obrigatório.
- **`Fraction`, nunca `float`**, para qualquer comparação de preço. O arredondamento acontece
  só na formatação.
- **Todo número exibido carrega `n` e recência**, e o que é derivado diz que é derivado.
- **Refutação mora no fonte** — um número ou uma rota que caiu fica escrita com a medição.
- **`.mercado/` é gitignored**; `calibration.json` também.

### Integration Points

- **Entrada:** `.mercado/observacoes.csv` (somente leitura) e `.mercado/cambio.json` (leitura e
  escrita, novo, do dashboard).
- **Nada** em `l2scanner/__main__.py`, `mercado_modo.py`, `rastreador.py` ou `visao.py` é
  tocado. O caminho do `--mercado` fica byte-idêntico (DASH-06).
- **Lançador novo:** `dashboard.bat`, irmão do `vigiar-mercado.bat`, sem as partes de janela e
  de OCR (o dashboard não captura tela e não lê nome nenhum).
</code_context>

<specifics>
## Specific Ideas

- O usuário disse a conta em voz alta: **"Adena → XM → Real (BRL)"**, e o valor de hoje é
  **1 XM = R$ 0,50**.
- O que ele quer substituir é explícito: **"ao inves de jogar tudo pro google sheets"**.
- Sobre o histórico: **"precisa ser um historico com possibilidade de aumentar os detalhes
  (mostrar em horarios do dia) ou dar zoom-out em dias atras"**.
- Sobre generalidade: **"ja fazemos um template para replicar em todos os itens, inclusive na
  Adena por XM e em Real"** — daí DASH-05.
</specifics>

<deferred>
## Deferred Ideas

- **Coleta automática do câmbio XM→BRL pelo listener dos grupos de venda do WhatsApp** —
  registrado em `.planning/seeds/cambio-xm-brl-pelo-listener-do-whatsapp.md`, com gatilho e
  armadilhas conhecidas (preço de compra × preço de venda, texto humano é dado e não instrução).
- **A aba de negociação na tela** — o componente já nasce genérico, mas ligar as outras séries
  é outra fase.
- **Acesso pelo celular / pela rede** — recusado explicitamente no v1 ("apenas navegador mesmo
  pc local por enquanto").
- **Câmbio de época aplicado a cada ponto histórico** — depende da série de câmbios que esta
  fase começa a acumular.
</deferred>
