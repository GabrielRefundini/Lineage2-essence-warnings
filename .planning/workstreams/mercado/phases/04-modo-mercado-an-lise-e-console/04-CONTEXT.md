# Phase 4: Modo --mercado, análise e console - Context

**Gathered:** 2026-08-31
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — 5 áreas, 20 decisões

> **ESTAS DECISÕES FORAM TOMADAS POR CLAUDE, NÃO PELO USUÁRIO.** Ele foi dormir em
> 2026-08-31 e autorizou execução autônoma das Fases 3 e 4 "tomando as decisões
> recomendadas". Cada decisão abaixo carrega a razão, para ele auditar ao acordar. Onde a
> decisão contraria a letra de um critério do ROADMAP, isso está dito em voz alta.

<domain>
## Phase Boundary

O usuário roda `--mercado` como TERCEIRA invocação, ao lado das duas instâncias de party, e
o console responde "vale quanto agora?" com estatística nomeada honestamente e evidência
sempre visível.

Ela é a fase que LIGA OS FIOS: a Fase 2 entregou a leitura sem laço, a Fase 3 entregou o
registro sem chamador. Aqui os dois ganham um processo que os chama.

Requisitos: DETC-02 (modo separado que não degrada o party), LEIT-04 (console ao vivo com as
duas metades), ANAL-01 (menor pedido visível e mediana, com n e recência), ANAL-02 (destaque
abaixo da mediana), ANAL-03 (tendência com janela explícita), ANAL-04 (margem de craft com
staleness por componente).

</domain>

<decisions>
## Implementation Decisions

### A watchlist no critério 3 — a contradição herdada

O critério 3 do ROADMAP diz *"para cada item da **watchlist**"*. **Esse critério é anterior à
Fase 2**, que em 2026-08-29 tirou a watchlist da porta de entrada: o nome passa a vir por OCR
e **tudo** que aparece é registrado. O `[mercado] watchlist` do `config.toml` continua
comentado — o usuário nunca o preencheu, e a Fase 2 tornou isso irrelevante para a leitura.

- **A watchlist volta como FILTRO DE DESTAQUE, opcional — nunca como porta de entrada.** É
  exatamente o papel que o `02-CONTEXT.md` já previu para ela ("se sobreviver, é como filtro
  de DESTAQUE no console (Fase 4)"), e o que o `260829-rd9` deixou escrito ao removê-la do
  `LEIT-01`.
- **Sem watchlist configurada, o console responde para os itens com MAIS EVIDÊNCIA** — as N
  séries com maior contagem de observações. O usuário não precisa configurar nada para ver
  valor, que é a premissa que o fez trocar a watchlist por OCR.
- **Com watchlist, os itens dela vêm PRIMEIRO e marcados**; o resto continua visível abaixo.
  Filtrar de vez esconderia o item novo que a Fase 2 existe para descobrir.
- **O critério 3 é honrado em substância, não na letra.** Está dito aqui porque a divergência
  precisa ser visível para quem verificar a fase.

### O modo `--mercado` (DETC-02)

- **Terceira invocação, processo próprio.** O usuário já roda duas instâncias de party; uma
  terceira é normal e é o que o requisito descreve.
- **O modo party fica INTOCADO.** Nada em `l2scanner/rastreador.py` nem no gate de brilho da
  barra própria em `l2scanner/visao.py` muda. Acoplar mercado ao detector de morte é a
  manobra que causou o incidente 27x, e a Fase 2 recusou fazê-lo três vezes.
- **`calibration.json` é lido, NUNCA escrito** por este modo. Quem escreve é a ferramenta de
  calibração.
- **Sem calibração de mercado, o modo NÃO SOBE** — mensagem alta dizendo o que falta e como
  calibrar. Subir cego seria pior que não subir: o usuário acharia que está coletando.
- **A oclusão do painel é o sinal compartilhado da Fase 1** (DETC-01), consumido aqui. Um
  sinal, dois consumidores, nunca duplicado.

### O console (LEIT-04)

- **Texto simples, sem dependência nova.** O `CLAUDE.md` recomenda `rich`, mas **ele não está
  instalado** e o projeto tem doutrina de zero-install (`uv run` + `.bat`, sem ritual). O
  FIRE-01 varre o venv instalado. Um console de texto entrega o requisito inteiro.
- **Repinta na cadência de captura (1 Hz)** — a mesma do resto do scanner.
- **Mostra ao vivo:** páginas lidas e perdidas, e o último item reconhecido.
- **O resumo final conta AS DUAS METADES** — "li 7, perdi 3". Nunca só a metade boa: a Fase 2
  mediu 151 lidas contra 189 perdidas no censo, e esconder a segunda faria o usuário confiar
  numa cobertura que não existe.
- **Os motivos de descarte aparecem agregados** no resumo (oclusão, gramática, discordância,
  faixa cinzenta) — são o que diz ao usuário se vale mover a tooltip ou recalibrar.

### A análise (ANAL-01, 02, 03)

- **"MENOR PEDIDO VISÍVEL", nunca "preço de venda".** É a palavra do requisito e a razão é
  honestidade: o scanner vê ofertas, não transações. Um teste prende a string proibida.
- **Menor e mediana, SEMPRE com contagem de evidência e recência** — `n=12, visto às 14:32`.
  Estatística sem n e sem data é adivinhação com cara de número.
- **Destaque na hora para linha abaixo da mediana histórica** (ANAL-02), calculada sobre o
  que o CSV já tem.
- **Tendência com o TAMANHO DA JANELA EXPLÍCITO** (ANAL-03) — "caiu 12% em 30 observações",
  nunca "caiu 12%". Sem o tamanho, a tendência de 3 pontos parece a de 300.
- **Tudo lê do CSV da Fase 3**, e a análise NÃO reescreve o arquivo. Leitura é leitura.
- **Sem evidência suficiente, o console diz isso** em vez de calcular — mediana de duas
  observações é um número que engana.

### A margem de craft (ANAL-04)

- **A seção de receitas NÃO EXISTE no `config.toml`** — conferido. Ela nasce nesta fase, como
  `[[receita]]`, **comentada**, no mesmo padrão da watchlist e dos `[[evento]]`.
- **Cada componente mostra a PRÓPRIA staleness.** Uma margem calculada com um ingrediente
  visto hoje e outro visto há uma semana não é uma margem — e o requisito exige exatamente
  essa granularidade.
- **Sem receita configurada, a margem simplesmente NÃO APARECE.** Não é erro, não é aviso: é
  uma seção opcional que o usuário preenche quando quiser.
- **Ingrediente sem observação nenhuma quebra a margem inteira**, com o nome do que falta.
  Calcular com um buraco daria número plausível e errado.

### Claude's Discretion

- Layout exato do console e ordem das colunas.
- Nome do arquivo/módulo da análise e da montagem.
- Quantas séries mostrar quando não há watchlist (o "N" do topo por evidência).
- Formato do carimbo de recência exibido.

</decisions>

<code_context>
## Existing Code Insights

### O que as fases anteriores entregaram, e que esta liga

- **Fase 2** — `l2scanner/mercado_pagina.py` (`LeitorDePagina`, `PaginaAceita`, estabilizador,
  congelamento pela janela inteira), `l2scanner/mercado_leitura.py` (`ler_linha`, `LinhaLida`
  com `total_em_centesimos`, `quantidade`, `chave_da_serie`, `nome_exibido`,
  `residuo_do_cruzamento`), `l2scanner/mercado_catalogo.py` (`Catalogo`).
  **Nenhum deles tem chamador de produção — este é o fio que falta.**
- **Fase 3** — `l2scanner/mercado_registro.py` (registro, dedup por conteúdo, portão de
  contrato) e **`montar_registro_de_mercado`** já no `l2scanner/__main__.py`, escrita no
  precedente de `montar_gravador`. **A montagem existe e nasceu sem chamador, de propósito.**
- **`tools/gerar_observacoes_do_censo.py`** — produz o CSV a partir das gravações. É o
  precedente literal de "montar o leitor, rodar o laço, contar as duas metades" que esta fase
  transforma em modo de produção.

### Padrões da casa

- **Montagem que falha para o lado certo** (`montar_gravador`, `__main__.py:227-262`): `try`
  envolve o construtor inteiro, `except` estreito e nomeado, `log.error`, DUAS mensagens
  sendo a segunda "o que continua funcionando", `return None` nunca `raise`.
- **Falha fechada**: dado ilegível é descartado, nunca interpretado.
- **Um número que caiu precisa dizer que caiu** — refutações ficam no fonte.
- **Nada de constante mágica** — limiar mora no `calibration.json`.

### Integration Points

- **FIRE-01**: nenhuma biblioteca de síntese de input entra na árvore. Há teste que varre o
  venv INSTALADO.
- **NÃO tocar** `rastreador.py` nem o gate de brilho da barra própria em `visao.py`.
- **Outro agente trabalha nos workstreams `tiat`/`identidade` NESTA MESMA ÁRVORE.** Não tocar
  `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`, `test_bosses.py`. O
  `l2scanner/__main__.py` é **disputado** — fazer o menor diff possível.

</code_context>

<specifics>
## Specific Ideas

- **Números medidos que dimensionam o console:** no censo, 478 ticks com painel aberto, **151
  páginas lidas contra 189 perdidas**, 39 séries distintas. Das perdas, 72% são o piso de 7
  posições comparadas funcionando.
- **A guarda de cruzamento está DESLIGADA** (`mercado_tolerancia_do_cruzamento = None`,
  reprovada por medição). O `residuo_do_cruzamento` é observação, não veredito — se o console
  o mostrar, tem de ser como observação.
- **`rich` NÃO está instalado** (conferido). O venv tem `mss`, `opencv`, `numpy`, `winrt-*`,
  `discord.py`, `windows-capture`.
- **Duas conferências humanas da Fase 2 continuam abertas** e esta fase é onde elas fecham
  naturalmente: o OCR real DENTRO do tick, e o congelamento provocado.
- **FLAKE conhecido:** `tests/test_agenda.py:1141` levanta `KeyboardInterrupt` de propósito e
  às vezes derruba a sessão do pytest. **Abortar não é falhar.** Verde de referência:
  **2819 passed, 2 skipped** sem esse arquivo.
- O pytest roda no **Python GLOBAL**, não no `.venv`.

</specifics>

<deferred>
## Deferred Ideas

- **Alerta de oportunidade no WhatsApp** (WAPP-02) — Out of Scope do v1, registrado desde o
  REQUIREMENTS.
- **Série temporal por dia** — a Fase 3 grava uma linha por anúncio com a data da primeira
  vez; "como o preço deste item andou" exigiria mudar aquela decisão.
- **A fusão `B-grade Gemstone` × `C-grade Gemstone`** (0,9375, letra de grade) continua aberta
  desde a Fase 2 — ela apareceria como uma série só na análise.
- **Ler os outros dois layouts** do mercado (Adena e busca) — o v1 lê só a grade de
  negociação calibrada.

</deferred>
