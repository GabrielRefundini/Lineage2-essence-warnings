# Phase 4: Modo `--mercado`, análise e console — Research

**Researched:** 2026-08-31
**Domain:** Laço de produção Windows/WGC + análise estatística stdlib + console de texto
**Confidence:** ALTA no que é código desta árvore (lido nesta sessão, com linha citada); MÉDIA no custo de recursos entre processos (calculado, não medido); BAIXA em qualquer número de "piso de evidência" (nenhum foi medido — são escolhas, e estão marcadas como tal)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

> **ESTAS DECISÕES FORAM TOMADAS POR CLAUDE, NÃO PELO USUÁRIO.** Ele foi dormir em
> 2026-08-31 e autorizou execução autônoma das Fases 3 e 4 "tomando as decisões
> recomendadas". Cada decisão abaixo carrega a razão, para ele auditar ao acordar. Onde a
> decisão contraria a letra de um critério do ROADMAP, isso está dito em voz alta.

### Locked Decisions

**A watchlist no critério 3 — a contradição herdada**

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

**O modo `--mercado` (DETC-02)**

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

**O console (LEIT-04)**

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

**A análise (ANAL-01, 02, 03)**

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

**A margem de craft (ANAL-04)**

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

### Deferred Ideas (OUT OF SCOPE)

- **Alerta de oportunidade no WhatsApp** (WAPP-02) — Out of Scope do v1, registrado desde o
  REQUIREMENTS.
- **Série temporal por dia** — a Fase 3 grava uma linha por anúncio com a data da primeira
  vez; "como o preço deste item andou" exigiria mudar aquela decisão.
- **A fusão `B-grade Gemstone` × `C-grade Gemstone`** (0,9375, letra de grade) continua aberta
  desde a Fase 2 — ela apareceria como uma série só na análise.
- **Ler os outros dois layouts** do mercado (Adena e busca) — o v1 lê só a grade de
  negociação calibrada.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Descrição | Suporte desta pesquisa |
|----|-----------|------------------------|
| **DETC-02** | Modo `--mercado` separado — vigiar mercado não degrada nem compete com o modo party | §Lacuna 1: o que é medível (orçamento de tick medido, custo de cópia WGC calculado, `minimum_update_interval` VERIFICADO na lib instalada), o que é só afirmação, e os DOIS tripwires executáveis que já existem + os dois que faltam |
| **LEIT-04** | Console ao vivo com páginas lidas/perdidas e último item; resumo conta as duas metades | §Lacuna 2 (o laço) + §Contadores que já existem: `LeitorDePagina` já publica os sete números; esta fase só desenha |
| **ANAL-01** | Menor pedido visível e mediana, com n e recência | §Lacuna 3: `median_low` (precedente da casa), `Fraction` para o unitário, e as DUAS recências que não podem ser confundidas |
| **ANAL-02** | Linha abaixo da mediana histórica destacada na hora | §Lacuna 3 > "O destaque ao vivo": a mediana é tirada do snapshot ANTES das escritas deste tick |
| **ANAL-03** | Tendência por item com tamanho da janela explícito | §Lacuna 3 > "A tendência": `statistics.linear_regression` sobre ORDINAL, nunca sobre o carimbo; as três `StatisticsError` já exercitadas |
| **ANAL-04** | Margem de craft com staleness por componente | §Lacuna 4: forma mínima do `[[receita]]` (VERIFICADA no `tomllib`), a resolução nome→chave que é o verdadeiro problema, e o que a proposta NÃO resolve |
</phase_requirements>

---

## Summary

A Fase 4 tem **muito menos código novo do que parece** e **um fio a mais do que o CONTEXT
sabia**. A Fase 2 já publica os sete contadores que o LEIT-04 pede (`paginas_lidas`,
`paginas_perdidas`, `paginas_vazias`, `paginas_de_outro_layout`, `ticks_com_painel_aberto`,
`frames_congelados`, `linhas_descartadas`, mais `ultimo_motivo_de_perda` e `ultima_leitura`)
[VERIFIED: l2scanner/mercado_pagina.py:310-321]. A Fase 3 já entrega `montar_registro_de_mercado`
no trilho da casa [VERIFIED: l2scanner/__main__.py:468-544]. O `tools/gerar_observacoes_do_censo.py`
já é o laço inteiro, escrito para PNG em vez de janela [VERIFIED: tools/gerar_observacoes_do_censo.py:197-265].

**O fio que ninguém contou: `Catalogo` — a classe de disco do catálogo de nomes da Fase 2 —
não tem NENHUM chamador de produção.** `grep -rn "Catalogo("` fora de `tests/` devolve zero
[VERIFIED: grep sobre l2scanner/ e tools/ nesta sessão]. `LeitorDePagina` recebe um `dict`
simples e o muta em memória [VERIFIED: l2scanner/mercado_pagina.py:680-694]; `Catalogo.entradas()`
devolve um SNAPSHOT desconectado [VERIFIED: l2scanner/mercado_catalogo.py:617-635]. Se a Fase 4
só passar `catalogo.entradas()` e nunca chamar `catalogo.registrar()` + `catalogo.gravar()`,
**toda série nova descoberta ao vivo morre com o processo** — e o `.mercado/catalogo-de-nomes.csv`
que o 02-05 entregou fica vazio para sempre. São **três** fios a ligar, não dois.

Nada aqui pede dependência nova. `statistics.median_low`, `statistics.linear_regression`,
`fractions.Fraction`, `csv`, `tomllib`, `datetime` cobrem a análise inteira, e `median_low` já
é precedente da casa [VERIFIED: l2scanner/calibrar_mercado.py:58,1691,1709].

**Recomendação primária:** um módulo novo `l2scanner/mercado_modo.py` com o laço, e um
`l2scanner/mercado_analise.py` puro com a estatística — para que o diff no disputado
`__main__.py` seja **uma flag + um `if` de saída antecipada + um import adiado**, no molde
exato do `--so-agenda` [VERIFIED: l2scanner/__main__.py:2420-2427].

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Captura da janela do jogo | `captura_janela.JanelaSource` (WGC) | — | Único caminho que expõe a janela INTEIRA, que é o que o painel exige [VERIFIED: __main__.py:1905-1930] |
| Detecção de painel aberto | `mercado_visao.RastreioDoPainel` | — | Sinal positivo próprio da Fase 1; o rastreador NÃO o lê (tripwire) |
| Leitura de página | `mercado_pagina.LeitorDePagina` | — | Já existe, já conta as duas metades |
| Persistência de observação | `mercado_registro.RegistroDeObservacoes` | `montar_registro_de_mercado` | Já existe, já degrada certo |
| Persistência do catálogo de nomes | `mercado_catalogo.Catalogo` | **SEM CHAMADOR — nasce nesta fase** | Ver §Lacuna 2 > "O terceiro fio" |
| Laço de produção (tick, cadência, desligamento) | **`mercado_modo.py` (novo)** | `__main__.py` (1 flag) | Laço separado pelo precedente literal de `laco_da_agenda` |
| Estatística (menor, mediana, tendência, margem) | **`mercado_analise.py` (novo, PURO)** | — | Sem disco, sem relógio, sem console: é o que a torna testável no Python global |
| Desenho do console | **`mercado_console.py` (novo)** ou funções em `mercado_modo.py` | `console.moldurar` para destaque | Texto puro; `console.py` já dá a moldura sem cor para o caso não-tty |
| Leitura de `[[receita]]` / `[mercado] watchlist` | `config.py` (novas funções, molde `ler_bosses`) | — | `calibrar_mercado.ler_watchlist` NÃO serve: aquele módulo chama `tornar_consciente_de_dpi()` no import [VERIFIED: l2scanner/calibrar_mercado.py:49-51] |

---

## Standard Stack

### Core

| Biblioteca | Versão | Propósito | Por que |
|------------|--------|-----------|---------|
| `statistics` (stdlib) | Python 3.12.13 (.venv) / 3.12.10 (global) | mediana, regressão | `median_low` e `linear_regression` verificados executando o interpretador nesta sessão [VERIFIED: `python -c "import statistics..."`] |
| `fractions` (stdlib) | — | unitário exato sem float | `total_em_centesimos / quantidade` em `float` reintroduz erro de ponto flutuante exatamente onde o parsing o evitou [CITED: REQUIREMENTS.md "O que NÃO muda"] |
| `csv`, `tomllib`, `datetime`, `argparse`, `logging` | stdlib | — | Já em uso no projeto inteiro |
| `windows_capture` | **2.0.1** (já instalado) | captura da janela | Já é dependência; ver §Lacuna 1 para `minimum_update_interval` |
| `numpy` | 2.5.2 (já instalado) | frames | Já é dependência |

**Nenhuma instalação.** `pip install` não aparece em plano nenhum desta fase.

### Alternativas consideradas

| Em vez de | Poderia usar | Trade-off |
|-----------|--------------|-----------|
| console de texto | `rich` 15.x | **RECUSADO pelo CONTEXT.** Nota de precisão: `rich` **não faria o FIRE-01 falhar** — a banlist dele é só de síntese de input (`pyautogui`, `pydirectinput`, `pynput`, `keyboard`, `mouse`, `autoit`, `pyautoit`, `ahk`, `pywinauto`) [VERIFIED: tests/test_firewall_escopo.py:66-78]. O motivo real é doutrina de zero-install + `vigiar-party.bat` rodar `pip install -r requirements.txt` na primeira execução [VERIFIED: vigiar-party.bat:56]. A decisão continua certa; a justificativa escrita no CONTEXT está imprecisa e o plano não deve repeti-la como está. |
| `JanelaSource` (WGC) para o mercado | `MssSource` sobre o retângulo da janela no desktop | Elimina a terceira sessão WGC (§Lacuna 1) e o custo de cópia, mas **exige o jogo VISÍVEL** e obriga a converter as coordenadas de janela do `calibration.json` para desktop via `origem_da_janela(hwnd)` [VERIFIED: l2scanner/captura_janela.py:179]. Como o usuário abre o World Exchange **manualmente e com a janela em foco**, tecnicamente serve. **Não recomendado para o v1:** perde a resiliência a arrastar/cobrir que o resto do projeto já tem, e cria uma segunda convenção de coordenadas — exatamente o que o `CLAUDE.md` alerta para o backend `dxcam`. |
| `statistics.median` | `statistics.median_low` | **Use `median_low`.** Medido nesta sessão: `median([1,2,3,4]) == 2.5` (float) e `median_low([1,2,3,4]) == 2` (int) [VERIFIED: execução local]. Com preços em centésimos inteiros, `median` de n par inventa **meio centavo que nunca existiu na tela** — o mesmo pecado do unitário arredondado que o D-02 recusou. `median_low` devolve sempre um valor OBSERVADO. Precedente já na casa: `calibrar_mercado.py:1691,1709`. |

## Package Legitimacy Audit

**Não aplicável.** Esta fase não instala nenhum pacote externo. `requirements.txt` não muda.
Toda biblioteca usada já está no `.venv` e foi confirmada por listagem de `site-packages`
nesta sessão: `mss 10.2.0`, `opencv-python 4.14.0.94`, `numpy 2.5.2`, `windows_capture 2.0.1`,
`winrt-* 3.2.1`, `discord.py 2.7.1` [VERIFIED: `ls .venv/Lib/site-packages`].
**`rich` NÃO está presente** — confirmado [VERIFIED: mesma listagem].

---

# LACUNA 1 — DETC-02: "nenhuma competição de recursos perceptível". O que se mede e o que é só afirmação.

## 1.1 O que É medível, com número

| Grandeza | Valor | Origem |
|---|---|---|
| Orçamento do PIOR tick da leitura de mercado | **~110 ms de 1000 ms (11% de UM núcleo)** | [VERIFIED: 02-RESEARCH.md:705-716 — tabela medida, inclui OCR de 10 linhas × 2 escalas = 70 ms] |
| Custo com o painel FECHADO (o caso comum) | ~135 ms a cada 3 ticks = **~45 ms/s (~4,5% de um núcleo)** | Derivado de: 3 âncoras × ~45 ms [VERIFIED: mercado_visao.py:190-193] ÷ `TICKS_ENTRE_VARREDURAS_OCIOSAS = 3` [VERIFIED: mercado_visao.py:193] |
| Núcleos lógicos da máquina | **8** | [VERIFIED: `os.cpu_count()` nesta sessão] |
| Cópia por frame de cada sessão WGC | **~7,2 MB** (janela 1720×1392, BGRA→BGR) | [VERIFIED: comentário medido em mercado_pagina.py:422 — "memcpy de ~7,2 MB"; geometria em calibration.json `mercado_geometria_da_captura`] |
| Taxa de entrega da WGC | **~38 fps** | [VERIFIED: comentário de `on_frame_arrived`, captura_janela.py:265-267] |
| Volume de cópia por sessão WGC | **~273 MB/s** (7,2 MB × 38) | **[DERIVADO — não medido]** |

**A conclusão honesta em uma linha:** o processo `--mercado` custa **~11% de um núcleo no pico
e ~4,5% no repouso**, num PC de 8 núcleos — ou seja, ~1,4% da máquina no pico. O que ele
adiciona de verdade é a **terceira thread de callback WGC copiando ~273 MB/s**, e esse número
é calculado, não medido.

## 1.2 A terceira sessão WGC — o único risco real, e ele tem alavanca

O `--mercado` precisa da janela inteira, e o único caminho para ela é `JanelaSource`, que abre
uma `WindowsCapture` própria numa thread daemon [VERIFIED: l2scanner/captura_janela.py:252-280].
O `calibration.json` do usuário diz `janela = "Yazalaque - XM Essence"`, e o `vigiar-party.bat`
roda `--janela` [VERIFIED: calibration.json; vigiar-party.bat:76]. Ou seja: **a terceira
invocação abre uma terceira sessão WGC, possivelmente sobre o MESMO HWND de uma das party.**

- Múltiplas sessões WGC simultâneas **são suportadas** pela API, com um `GraphicsCaptureItem`
  e uma `GraphicsCaptureSession` por captura [CITED: learn.microsoft.com — GraphicsCaptureSession;
  blogs.windows.com "New Ways to do Screen Capture"].
- A documentação menciona **uma borda amarela desenhada em volta de cada item capturado**
  [CITED: mesma fonte]. O projeto passa `draw_border=False` [VERIFIED: captura_janela.py:255].
  O usuário já roda DUAS instâncias sem reclamar de borda — evidência empírica de que a
  supressão funciona nesta máquina, mas **não é prova para três** [ASSUMED].

**A alavanca, e ela é real:** `windows_capture 2.0.1` aceita
`minimum_update_interval: int | None` no construtor — "Requested minimum interval between
eligible updates, in milliseconds" [VERIFIED: `inspect.signature(WindowsCapture.__init__)`
executado no `.venv` nesta sessão; docstring lida no mesmo comando]. `JanelaSource` **não o
passa hoje**.

Recomendação: acrescentar a `JanelaSource.__init__` um parâmetro **opcional, `None` por
padrão** (comportamento de hoje idêntico, byte a byte, para o party) e usá-lo **somente** no
laço do mercado. Um `minimum_update_interval=250` (≈4 fps) cortaria a cópia do processo de
mercado de ~273 MB/s para ~29 MB/s — **~9,5× menos** — mantendo ≥4 frames distintos por tick.

⚠️ **Não use 1000.** Com atualizações a cada ~1000 ms e leitura a cada ~1000 ms, a deriva de
fase produz leituras repetidas do mesmo buffer; três seguidas disparam
`JANELAS_IGUAIS_PARA_CONGELAR = 3` e o console diria "CAPTURA CONGELADA" com o jogo vivo
[VERIFIED: mercado_pagina.py:93, 408-455]. O `250` é uma **escolha com margem 4×, não uma
medição** [ASSUMED] — o plano deve declará-lo como constante nomeada com a razão escrita e um
teste que prove que o padrão `None` do party não mudou.

## 1.3 "O party não mudou" — o que JÁ é prova executável

Existem **dois tripwires de arquitetura** que já rodam na suíte:

- `test_o_fonte_do_rastreador_nao_cita_mercado` — lê o fonte de `rastreador.py` e falha se a
  palavra aparecer [VERIFIED: tests/test_mercado_27x.py:254].
- `test_o_rastreador_nao_importa_o_modulo_de_visao_do_mercado` [VERIFIED: mesmo arquivo:262].
- Mais a regressão comportamental: `test_a_sequencia_do_27x_COM_o_mercado_ligado_segue_em_ZERO_eventos`
  [VERIFIED: mesmo arquivo:381] e `test_um_vigia_que_EXPLODE_nao_derruba_a_leitura_da_party` [:448].

**O que falta e o plano deve criar (barato, e é a resposta honesta a "existe prova?"):**

1. **Estender o tripwire ao módulo novo.** Um teste que afirma que `mercado_modo.py` e
   `mercado_analise.py` **não importam** `rastreador`, `visao`, `sessao` nem `presenca` —
   simétrico ao que já existe do outro lado. Isso prende o acoplamento nas DUAS direções.
2. **Um teste de assinatura do laço party.** Afirmar que `laco_principal` continua sem
   parâmetro novo e que `Sessao(...)` continua recebendo o mesmo conjunto de argumentos —
   ou, mais simples e mais forte: **a suíte inteira do party verde** (`test_rastreador.py`,
   `test_party_estavel.py`, `test_mercado_27x.py`, `test_modo_solo*.py`) como portão da fase.
3. **Um teste que prova que `--mercado` nunca constrói `Rastreador`** — monkeypatch em
   `l2scanner.rastreador.Rastreador` que levanta se chamado, e rodar o arranque do modo.

## 1.4 O que **NÃO** é provável por teste, e precisa ser dito assim

| Afirmação do critério 1 | Provável? | Como |
|---|---|---|
| "nenhum comportamento do detector de morte muda" | **SIM** | Tripwires de fonte + import + regressão do 27x + suíte party verde |
| "o modo `--mercado` não toca `rastreador.py`/`visao.py`" | **SIM** | `git diff --stat` vazio nesses dois arquivos no commit da fase (verificação, não teste) |
| **"nenhuma competição de recursos perceptível"** | **NÃO — por teste automatizado, jamais** | Contenção entre 3 processos é propriedade do SISTEMA, não do programa. Nenhum unit test a alcança. |

**Proposta concreta para a parte não-provável — e ela cabe no plano:**

- **(a) Auto-medição embutida, sem custo.** O laço já vai calcular `dormir = intervalo - (agora - inicio)`
  (molde de `__main__.py:2197-2199`). Acumular p50/p95/máximo de `(agora - inicio)` e imprimir
  no resumo final, junto com **quantos ticks estouraram o orçamento**. Isso transforma "não
  compete" em um número que o usuário lê no fim da sessão, e é a única metade que o programa
  pode afirmar sobre si mesmo. Precedente da casa: o resumo do gravador imprime contador E
  disco lado a lado [VERIFIED: __main__.py:2229-2246].
- **(b) Um portão humano nomeado, com critério objetivo.** "Rode as duas instâncias de party
  + o `--mercado` por 10 minutos com o mercado aberto. No Gerenciador de Tarefas, o total de
  CPU dos três `python.exe` deve ficar abaixo de X%; e o `scanner.log` das duas party não pode
  ganhar nenhuma linha de `Falha de captura` nem `Imagem congelada` que não aparecesse antes."
  Esse é o único jeito honesto de fechar o critério 1, e ele é do USUÁRIO, não do agente.
- **(c) A linha de arranque conta o orçamento.** Precedente literal já escrito:
  `montar_vigia_do_mercado` imprime âncoras, limiar, cadência e "~45 ms por âncora"
  [VERIFIED: __main__.py:455-465]. O `--mercado` deve abrir dizendo **"~110 ms de 1000 ms no
  pior tick; sou o terceiro processo; a party não me lê e eu não leio a party"**.

---

# LACUNA 2 — O laço de produção, a partir do precedente

## 2.1 O esqueleto que se reusa DIRETO do `gerar_observacoes_do_censo.py`

Estas partes atravessam sem mudança conceitual [VERIFIED: tools/gerar_observacoes_do_censo.py]:

| Peça | Linhas | Reusa? |
|---|---|---|
| `_novo_leitor(cal)` — fiação `RastreioDoPainel` + `LeitorDePagina` | :229-242 | **Sim**, mas trocando `{}` pelo catálogo de disco (§2.3) |
| `Contagem` (observações / duplicadas / perdidas / séries) com `absorver` | :175-195 | **Sim**, literal. Os três campos separados são exatamente o "não confunda dedup com disco cheio" que o console precisa |
| `gravar_as_paginas(paginas, registro, relogio)` | :197-221 | **Sim**, literal — inclusive o `elif registro.ligado` que separa duplicada de perdida |
| A sequência de portões de arranque (OCR → calibração → `mercado_grade` → layout `"negociacao"` → `configurar_log` → `montar_registro_de_mercado`) | :365-413 | **Sim**, e é o esqueleto do "sem calibração o modo NÃO SOBE" |
| Códigos de saída NOMEADOS (`SAIDA_SEM_OCR = 5`, etc.) | :111-118 | **Sim, o padrão.** Mas o `__main__` do projeto usa `return 2` para recusa de configuração [VERIFIED: __main__.py:2440,2470,2490] — **siga o `2` do `__main__`, não a numeração da ferramenta**, senão o produto ganha duas convenções |
| O relatório final com as duas metades | :434-444 | **Sim**, e é literalmente o LEIT-04 |

## 2.2 O que **NÃO** se reusa, e por quê

| O que muda | Por quê |
|---|---|
| `cv2.imread(caminho)` → `fonte.capturar()` | Óbvio, mas a consequência não é: o PNG **nunca falha parcialmente**, a captura sim. O laço precisa do bloco `except Exception` + `erros_seguidos >= 10` do laço principal [VERIFIED: __main__.py:2088-2098], que a ferramenta não tem porque não precisa |
| `varrer_uma_gravacao` com **um leitor por gravação** | Em produção há **UMA sessão contínua**: um leitor só, vivo o tempo todo. A regra "um leitor por gravação" existe porque duas gravações não são ticks vizinhos — em produção eles são [VERIFIED: docstring em :245-252] |
| `for caminho in arquivos` (varre e acaba) | Vira `while True` + `time.sleep(dormir)` com a compensação de deriva do laço principal [VERIFIED: __main__.py:2197-2199]. **Não use `sleep(intervalo)` puro**: com 110 ms de trabalho o tick viraria 1,11 s e o console "a 1 Hz" mentiria |
| Nada de `--saida` / `razao_para_recusar_a_saida` | A produção escreve em `.mercado/` **de propósito** — é o inverso exato da guarda da ferramenta. `montar_registro_de_mercado()` sem argumento já resolve para `PASTA_DO_MERCADO` [VERIFIED: __main__.py:527] |
| `GRAVACOES_DO_CENSO` / `_carregar_o_censo` | Não existe conjunto fechado em produção |
| `print(...)` | Vira `log.info(...)`, para que o `scanner.log` rotativo tenha a forense pós-farm — que é a única ferramenta de depuração do projeto |
| **"painel fechado" não existe na ferramenta** | Nos PNGs do censo o painel está lá ou não, e `observar()` devolve `None` calado. **Em produção, "painel fechado" é o estado NORMAL e majoritário** — e o console precisa dizer isso sem virar spam. Ver §2.4 |
| **Desligamento** | A ferramenta acaba sozinha. Produção precisa de `try/except KeyboardInterrupt/finally` com `fonte.fechar()`, `catalogo.gravar()` e o resumo — molde de `laco_da_agenda` [VERIFIED: __main__.py:1641-1650] e do `finally` do laço principal [:2205-2264] |

## 2.3 O TERCEIRO FIO — `Catalogo` também nasceu sem chamador

**Achado desta pesquisa, não previsto no CONTEXT.**

- `LeitorDePagina.__init__` recebe `catalogo: dict[str, EntradaDoCatalogo]` e o **muta em
  memória** quando uma página é aceita [VERIFIED: mercado_pagina.py:199-206, 680-694].
- `Catalogo` (a classe de disco, `.mercado/catalogo-de-nomes.csv`) tem `registrar()`,
  `gravar()` atômico e `entradas()` [VERIFIED: mercado_catalogo.py:408-635].
- `Catalogo.entradas()` devolve um **dicionário NOVO** construído por compreensão — mutá-lo
  não altera `self.series` [VERIFIED: mercado_catalogo.py:626-634].
- **`Catalogo(` não aparece em `l2scanner/` nem em `tools/`. Só em `tests/`** [VERIFIED: grep
  nesta sessão sobre l2scanner/, tools/, tests/].

**Consequência se o plano ignorar isto:** o modo `--mercado` roda, o `observacoes.csv` cresce,
e o `catalogo-de-nomes.csv` fica **vazio para sempre**. Pior: a cada arranque o catálogo em
memória volta do disco vazio, então **toda série é "nova" toda sessão** — a chave da série pode
sair diferente entre sessões e a dedup do `observacoes.csv` deixa de dedupar entre dias.

**A fiação certa, no tick:**

```python
# no arranque
catalogo = Catalogo(PASTA_DO_MERCADO)          # lê o CSV de nomes
leitor = LeitorDePagina(rastreio, catalogo.entradas(), ler_texto, ler_texto_ampliado, cal)

# quando uma pagina e ACEITA
for linha in pagina.linhas:
    catalogo.registrar(linha.chave_da_serie, linha.nome_exibido, agora)
    registro.registrar(linha, agora)

# no `finally`
catalogo.gravar()   # reescrita ATOMICA, .tmp-<pid> + os.replace
```

⚠️ `catalogo.gravar()` **só no `finally`**, nunca por tick: ele reescreve o arquivo INTEIRO de
forma atômica [VERIFIED: mercado_catalogo.py:575-600]. Reescrever dezenas de linhas a 1 Hz
seria trabalho puro. **Mas** isso significa que um `taskkill` perde as séries da sessão —
mitigação barata: gravar também a cada N páginas aceitas (ex.: 20), com o número escrito no
fonte. Isto é uma **escolha, não uma medição** [ASSUMED].

⚠️ O `Catalogo.__init__` faz `mkdir` e `carregar` **fora de qualquer `try`** — mesmo modo de
falha que fez `montar_registro_de_mercado` existir [VERIFIED: mercado_catalogo.py:426-434 vs
__main__.py:487-497]. **Ele precisa de uma `montar_catalogo_de_mercado` no mesmo trilho**:
`try` em volta do construtor inteiro, `except OSError` estreito, duas mensagens sendo a segunda
"o que continua funcionando", `return None`, nunca `raise`.

## 2.4 "Painel fechado" — o estado majoritário

Medido no censo: **478 ticks com painel aberto** de 517 frames — mas esses 517 frames são
material CURADO de sessões em que o usuário estava com o mercado aberto [VERIFIED:
02-05-SUMMARY.md:153]. Num farm real o painel fica fechado a maior parte do tempo — é
exatamente o que `TICKS_ENTRE_VARREDURAS_OCIOSAS` existe para baratear [VERIFIED:
mercado_visao.py:190-193].

Recomendação para o console: **uma linha de estado que se repinta, não uma linha por tick.**
Duas transições merecem `log.info` (evento): "PAINEL ABERTO" e "painel fechado". O resto é a
tabela repintada. E o precedente do projeto para não poluir é o LATCH — usado três vezes já
em `mercado_pagina.py` (`_layout_ja_recusado`, `_congelamento_ja_avisado`, `_falta_ja_avisada`).

## 2.5 O diff mínimo em `__main__.py` (arquivo DISPUTADO)

Molde literal do `--so-agenda` [VERIFIED: __main__.py:2342-2350 e 2420-2427]:

```python
    parser.add_argument(
        "--mercado",
        action="store_true",
        help=(
            "roda SO a leitura do World Exchange, como terceira invocacao ao "
            "lado das duas de party. Nao vigia a party e nao envia alerta."
        ),
    )
...
    # ANTES de carregar calibracao? NAO — ele PRECISA dela (ver abaixo).
    if args.mercado:
        from .mercado_modo import laco_do_mercado
        return laco_do_mercado(args)
```

Diferença importante em relação ao `--so-agenda`: aquele sai **antes** de
`Calibracao.carregar` porque não olha para a tela. O `--mercado` **olha**, então ele sai
**depois** da carga da calibração e depois da resolução de `--janela AUTO`, junto do
`--testar-manutencao` [VERIFIED: __main__.py:2455-2461]. Isso mantém uma só verdade sobre
como a janela é escolhida.

**Total do diff em `__main__.py`: ~14 linhas.** Tudo o mais mora nos módulos novos.

⚠️ **`--mercado` implica `--janela`.** O `parser.error(...)` no molde de
`--record-janela` [VERIFIED: __main__.py:2394-2400] é o lugar certo — recusar no parse, com a
razão, em vez de descobrir dentro do laço.

---

# LACUNA 3 — A estatística honesta, e onde ela mora

## 3.1 O que o CSV realmente contém (e por que isso muda tudo)

`COLUNAS = ("chave_da_serie", "nome_exibido", "primeira_vez", "total_em_centesimos",
"quantidade", "residuo_do_cruzamento")` [VERIFIED: l2scanner/mercado_registro.py:124-131 —
citado verbatim].

A chave de dedup é `(chave_da_serie, total_em_centesimos, quantidade)` [VERIFIED:
mercado_registro.py:149-166]. **Sem tempo, de propósito.** Consequência que o plano precisa
carregar por escrito:

> **Uma linha do CSV não é "o preço às 14:32". É "esta oferta específica — este item, este
> total, esta quantidade — foi vista pela PRIMEIRA vez às 14:32".** Um anúncio que fica no
> quadro por uma semana produz **uma** linha. Duas ofertas idênticas de vendedores diferentes
> produzem **uma** linha. Uma oferta que some e volta igual produz **uma** linha.

Portanto: **não existe série temporal de preço.** Existe uma **sequência de ofertas distintas,
ordenada pela primeira vez que cada uma apareceu**. Toda a nomenclatura do console tem de
respeitar isso, ou repete o pecado que "menor pedido visível" foi criado para evitar. Isto
está registrado como Deferred Idea no CONTEXT ("Série temporal por dia") — a Fase 4 **não** o
conserta, ela **narra a limitação**.

## 3.2 O comparável entre ofertas: o unitário, em `Fraction`

Comparar `total_em_centesimos` entre ofertas de quantidades diferentes é sem sentido (um lote
de 100 custa mais que um de 1). O único comparável é o unitário.

Mas o D-02 recusou **guardar** o unitário porque o que o jogo exibe é derivação arredondada
(`40,00 / 48 → 0,83`, e `0,83 × 48 = 39,84`, um número que nunca existiu) [VERIFIED:
mercado_registro.py:106-112]. **Derivar na hora de exibir é outra coisa** — desde que não se
arredonde antes de comparar.

```python
from fractions import Fraction
unitario = Fraction(total_em_centesimos, quantidade)   # exato, sem float
```

`Fraction` ordena, compara e entra em `median_low` sem perder um bit. O arredondamento
acontece **só na formatação**, e o número exibido carrega a marca de derivado.

**Recomendação de apresentação, que resolve os dois requisitos de uma vez:**

- **"menor pedido visível"** = a oferta de **menor unitário**, exibida como
  **`total ; quantidade`** — nunca um total solto, que é meaningless — mais o unitário
  derivado marcado.
  `menor pedido visivel: 62,00 por 48 un  (1,29/un derivado)  visto 31/08 14:32`
- **mediana** = `median_low` sobre os unitários das n ofertas. Devolve o unitário de uma
  oferta que **existiu de verdade**.

## 3.3 O piso de evidência — e a resposta honesta é "não foi medido"

**Pergunta do briefing: "com quantas observações uma mediana deixa de enganar — e esse piso é
medido ou escolhido?"**

**Resposta: ele é ESCOLHIDO. Nenhum piso desse tipo foi medido neste projeto, e nenhum número
existente serve de substituto.** O que existe medido é sobre a LEITURA, não sobre a análise:
151 páginas lidas / 189 perdidas, 39 séries distintas, piso de 7 posições comparadas
[VERIFIED: 02-05-SUMMARY.md:153,176,188]. **Quantas observações DISTINTAS por série o censo
produziria é um número que ninguém rodou** — o `.mercado/observacoes.csv` não existe nesta
árvore e `C:/temp/portao-fase3/` também não [VERIFIED: `ls` nesta sessão].

Proposta, com a razão escrita e marcada como escolha:

| Estatística | Piso proposto | Razão (escolha, não medição) |
|---|---|---|
| **menor pedido visível** | **n ≥ 1** | Um mínimo com n=1 é um **fato observado**, não uma estimativa. Mas o console **tem** de escrever `n=1` — a honestidade está no rótulo, não em esconder |
| **mediana** | **n ≥ 5** | Com 5 pontos o ponto de ruptura é 2: duas leituras aberrantes não conseguem mover a mediana para fora do miolo. Com n=2 a "mediana" é a média dos dois — literalmente o número que engana que o CONTEXT proíbe |
| **tendência** | **n ≥ 8** | Uma reta sobre 3 pontos tem a mesma cara de uma sobre 300, que é o que o ANAL-03 existe para impedir. 8 é o menor número em que o console pode dizer "em 8 observações" sem que a frase pareça piada |
| **destaque abaixo da mediana** | **mesmo piso da mediana (n ≥ 5)** | Destacar contra uma mediana que não vale seria pintar de vermelho um número inventado |

**Abaixo do piso o console escreve o que falta, não um número:**
`Common Aztac    n=3  — evidencia insuficiente para mediana (preciso de 5)`

**Onde os pisos moram:** o `CLAUDE.md`/CONTEXT dizem "nada de constante mágica — limiar mora
no `calibration.json`". **Aqui isso não se aplica e o plano deve dizer por quê:** aquele
arquivo é **escrito pela ferramenta de calibração e lido, nunca escrito, por este modo**
(decisão travada), e esses pisos não são calibração de pixel — são julgamento de produto. E
`config.toml` está fora dos limites nesta árvore (§Riscos). **Recomendação: constantes
nomeadas no módulo puro, com a razão por extenso e a marca de que são escolha, não medição** —
exatamente como `JANELAS_IGUAIS_PARA_CONGELAR = 3` faz [VERIFIED: mercado_pagina.py:88-93].
Isto é uma tensão real com a doutrina e está registrada aqui de propósito.

## 3.4 A tendência: contra o quê se compara

`statistics.linear_regression` existe e sua assinatura é `(x, y, /, *, proportional=False)`
[VERIFIED: `inspect.signature` executado nesta sessão]. Três modos de falha, todos exercitados
aqui:

```
linear_regression([1], [2])        -> StatisticsError: requires at least two data points
linear_regression([1,1], [2,3])    -> StatisticsError: x is constant
linear_regression([1,2], [3,3])    -> LinearRegression(slope=0.0, intercept=3.0)
statistics.median([])              -> StatisticsError: no median for empty data
```
[VERIFIED: todos executados no Python global nesta sessão]

**O `x` NÃO pode ser o carimbo.** `gravar_as_paginas` chama `relogio.agora()` **por linha**
[VERIFIED: tools/gerar_observacoes_do_censo.py:215], então as 10 linhas de uma página têm
carimbos separados por microssegundos. Uma regressão sobre `x` quase-constante devolve uma
inclinação absurda — e não levanta `StatisticsError`, porque tecnicamente `x` varia. **É um
número plausível e errado, que é o modo de falha que este projeto inteiro combate.**

**Recomendação: `x` é o ORDINAL (1..n) das ofertas distintas da série, ordenadas por
`primeira_vez`; `y` é o unitário em `float(Fraction)`.** Os ordinais são distintos por
construção, então "x is constant" é impossível. E a frase que sai já é a do requisito:

> `Common Aztac  tendencia: -12% ao longo das ultimas 30 ofertas distintas (n=30)`

**A palavra "ofertas distintas" é obrigatória** e substitui "observações": ela é o que impede
o usuário de ler a reta como "o preço caiu 12% nas últimas 30 horas".

⚠️ Reporte a variação em **percentual sobre a janela inteira** (`slope × (n-1) / intercept`),
não a inclinação crua. `slope = -3,4 centésimos por oferta` não significa nada para quem lê.

## 3.5 As DUAS recências, e por que confundi-las seria mentir

| Fonte | Campo | O que ele significa DE VERDADE |
|---|---|---|
| `.mercado/observacoes.csv` | `primeira_vez` | Quando **esta oferta específica** foi vista pela primeira vez |
| `.mercado/catalogo-de-nomes.csv` | `ultima_vez` | Quando **o item** foi visto pela última vez, em qualquer preço [VERIFIED: mercado_catalogo.py:383, 401-405, 570-571] |

Para o ANAL-01, a recência do PREÇO é `max(primeira_vez)` sobre as linhas daquela série no
`observacoes.csv` — "a oferta mais nova que eu vi". **Nunca** `ultima_vez` do catálogo, que
pode ser de agora mesmo sobre um preço de três dias atrás. E o **menor pedido visível deve
carregar o carimbo DELE**, não o da série: um mínimo de terça-feira ao lado de "visto às
14:32" de hoje é exatamente a mentira plausível.

**Formato do carimbo** (discricionário, proposta): `datetime` ingênuo em hora local
[VERIFIED: relogio.py:156-163 e mercado_registro.py:168-181]. Como não há fuso, e como o
`Relogio` pode estar sem âncora (degrada para o relógio do Windows, com WARNING no arranque
[VERIFIED: relogio.py:146-154]), o console deve mostrar **relativo + absoluto**:

```
hoje 14:32 (ha 12 min)      # mesmo dia
30/08 21:07 (ha 17 h)       # dias anteriores
```

O relativo é o que o olho lê; o absoluto é o que sobrevive a copiar a linha para o WhatsApp.
E se `relogio.confiavel` for `False`, o cabeçalho do console diz isso uma vez — senão "há 12
min" pode estar 3 horas errado num dual boot, que é o defeito que o `Relogio` existe para
corrigir.

## 3.6 Onde a análise mora, e o custo

**`l2scanner/mercado_analise.py`, PURO**: sem disco, sem relógio, sem `print`. Entrada: uma
lista de observações já parseadas + `agora` por parâmetro. Saída: dataclasses. É o que permite
a suíte inteira rodar no Python global sem WinRT — a mesma disciplina que
`mercado_registro.campos_da_observacao` já segue ("o carimbo entra por parâmetro (D-16)")
[VERIFIED: mercado_registro.py:168-181].

**A leitura do CSV**: `RegistroDeObservacoes.carregar()` já valida tudo (terminador, cabeçalho,
contagem de campos, tipos) mas **descarta os campos e guarda só o `set` de chaves** [VERIFIED:
mercado_registro.py:412-437, 564-636]. A análise precisa dos campos. **Não duplique o portão
de contrato.** Recomendação: uma função nova em `mercado_registro.py` que reusa
`_conferir_o_terminador` / `_conferir_o_cabecalho` / `chave_dos_campos` / `residuo_dos_campos`
e devolve as linhas parseadas — uma verdade só sobre o que o arquivo é.

**Cadência:** carregue **uma vez no arranque** e mantenha em memória, acrescentando cada
observação nova quando `registro.registrar(...)` devolver `True`. Reler o CSV a 1 Hz seria
desperdício e — pior — abriria uma corrida com o usuário editando o arquivo no Sheets no meio
da sessão. O contrato do arquivo já é "lido no arranque"; a análise segue o mesmo contrato.

**Volume:** dezenas de séries e milhares de linhas [VERIFIED: mercado_catalogo.py:418-419,
"milhares de linhas, nao de milhoes"]. Recalcular medianas por tick sobre isso é ruído.

## 3.7 O destaque ao vivo (ANAL-02) — a ordem importa

A mediana usada para destacar tem de ser **a de ANTES deste tick**. Se as linhas do tick já
tiverem entrado no modelo, o item se compara consigo mesmo. Ordem correta no tick:

1. página aceita chega
2. **para cada linha: comparar contra o modelo COMO ELE ESTÁ** → decidir destaque
3. só então `catalogo.registrar(...)` e `registro.registrar(...)` e acrescentar ao modelo

---

# LACUNA 4 — A margem de craft com staleness POR COMPONENTE (ANAL-04)

## 4.1 O que é exatamente uma "margem de craft" aqui

O requisito: "margem produto vs componentes, com staleness de cada componente visível". Com o
que o CSV tem, a única definição defensável é:

> **margem = (menor pedido visível do PRODUTO × quanto a receita rende) − Σ (menor pedido
> visível de cada COMPONENTE × quantidade da receita)**

Tudo em centésimos inteiros, tudo em unitário-`Fraction` antes de multiplicar. E — crucial —
**os dois lados são "menor pedido visível", ou seja OFERTAS, não transações.** A margem
resultante NÃO é lucro: é *"a diferença entre o que estão pedindo pelo produto e o que estão
pedindo pelos ingredientes"*. A palavra "lucro" é tão proibida quanto "preço de venda". Um
teste deve prender as duas strings.

**Por que "menor" e não "mediana" dos dois lados:** porque é assim que um humano compraria os
ingredientes e venderia o produto — pelo melhor pedido visível. E porque a mediana exige n≥5
por componente, o que multiplicaria a chance de a margem inteira cair. A **mediana entra como
linha secundária**, não como a conta principal.

## 4.2 A forma mínima do `[[receita]]` no TOML

Duas formas foram testadas contra o `tomllib` nesta sessão e **as duas parseiam**
[VERIFIED: `tomllib.loads` executado, saída conferida]. Recomendação: **a de tabela inline**,
porque é um bloco contíguo que se comenta e descomenta como uma unidade — igual ao
`watchlist = [...]` que já está comentado no `config.toml` [VERIFIED: config.toml:199-204]:

```toml
# [[receita]]
# produto = "Dragon Belt"
# rende = 1
# componentes = [
#   { item = "Common Aztac", quantidade = 5 },
#   { item = "Leonard",      quantidade = 20 },
# ]
```

A forma alternativa `[[receita.componente]]` também funciona, mas comentada vira quatro blocos
soltos que o usuário descomenta pela metade sem perceber.

**Validação, no molde literal de `_boss_de_dict`** [VERIFIED: config.py:327-408]: bloco que não
é dict, `produto` ausente ou vazio, `rende` ausente/booleano/≤0, `componentes` que não é lista,
componente sem `item`, `quantidade` booleana ou ≤0 — cada uma com mensagem que **nomeia a
receita** (`receita 'Dragon Belt'` quando há nome, `[[receita]] #2` quando não há) e mostra o
formato certo. O `isinstance(valor, bool)` **antes** do teste numérico não é zelo: sem ele
`quantidade = true` vira 1 [VERIFIED: config.py:383-390, comentário medido].

⚠️ **`rende` é opcional com padrão 1?** Recomendo **obrigatório**, pelo mesmo argumento que
tornou `respawn_horas_*` obrigatórios: um padrão silencioso produz uma margem plausível e
errada para quem craftou 5 de cada vez [VERIFIED: config.py:334-338, o argumento já escrito].

## 4.3 O problema REAL do ANAL-04, e não é a aritmética

**O usuário escreve `"Common Aztac"`. O CSV guarda `chave_da_serie`, que é
`nome + "#" + assinatura_de_digitos`** [VERIFIED: mercado_catalogo.py:637-648,
`assinatura_da_chave` recupera o que vem depois do `#`]. E o `nome_exibido` **oscila no OCR**
— é o D-03 inteiro, e é por isso que a chave existe [VERIFIED: mercado_registro.py:113-115,
"o nome que se LE (D-03, os dois porque o OCR faz o rotulo oscilar)"].

Então a resolução `"Common Aztac"` → chave tem três desfechos, e **cada um precisa de um
comportamento nomeado**:

| Desfecho | O que fazer |
|---|---|
| **exatamente uma série** cujo `nome_exibido` casa | usa ela |
| **nenhuma série** casa | **a margem inteira NÃO aparece**, com o nome do que faltou — decisão travada no CONTEXT ("Ingrediente sem observação nenhuma quebra a margem inteira") |
| **duas ou mais** casam (`Dragon Belt` × `+3 Dragon Belt`; `B-grade Gemstone` × `C-grade Gemstone`, a fusão de 0,9375 ainda ABERTA desde a Fase 2) | **quebra também, listando as candidatas.** Escolher a "mais parecida" produziria uma margem plausível e errada, que é o pecado central deste projeto |

**Recomendação de casamento: igualdade exata sobre `nome_exibido`, com caixa normalizada e
espaços colapsados. NÃO use similaridade fuzzy aqui.** O `mercado_catalogo.similaridade` existe
e é calibrado (`mercado_corte_de_similaridade = 0.8947`), mas ele foi medido para agrupar duas
leituras de OCR **do mesmo pixel**, não para casar texto que o humano digitou. Usá-lo aqui
casaria `Dragon Belt` com `+3 Dragon Belt` (que são séries de preço deliberadamente separadas —
"misturar +3 e +4 na mesma série não acrescenta ruído: destrói a série" [VERIFIED:
config.toml:186-189]). Se o nome exato não casar, a mensagem deve **listar os nomes disponíveis
que mais se parecem** para o usuário copiar — ajuda sem decidir por ele.

## 4.4 Staleness por componente, sem virar tabela ilegível

O requisito exige granularidade por componente; o console é texto. Proposta: **uma linha por
componente, indentada, com a idade como a última coluna, e a mais velha promovida ao cabeçalho
da margem.**

```
MARGEM DE CRAFT — Dragon Belt (rende 1)
  produto     Dragon Belt          menor 1.480,00 por 1 un    n=6    ha 22 min
  - 5x        Common Aztac         menor    62,00 por 48 un   n=12   ha 8 min
  - 20x       Leonard              menor     4,50 por 100 un  n=3    HA 3 DIAS  <--
  margem      +1.163,50   (evidencia mais velha: 3 dias — Leonard)
```

Três decisões dentro disso:

1. **A idade em uma palavra por linha** (`ha 8 min`, `ha 3 dias`), não um ISO por componente —
   é o que mantém a tabela legível.
2. **A mais velha sobe para a linha da margem**, com o nome do componente. É o número que
   decide se a margem vale alguma coisa, e enterrá-lo no meio da lista seria escondê-lo.
3. **Um marcador `<--`** no componente mais velho quando ele passa de um limiar. Limiar
   proposto: **24 h** — escolha, não medição [ASSUMED]. Constante nomeada, com a razão escrita.

**Onde ela aparece:** **não no repintar de 1 Hz.** A margem é cara de ler e não muda a cada
segundo. Recomendação: no arranque, e depois só quando uma das séries envolvidas ganha
observação nova. Precedente da casa: `desenhar_status` sai a cada `--status-a-cada` segundos,
não por tick [VERIFIED: __main__.py:2186-2193].

## 4.5 O que esta proposta **NÃO** resolve — dito em voz alta

1. **Ela não sabe se a oferta ainda existe.** "Menor pedido visível de 22 min atrás" pode ter
   sido comprado há 21 minutos. O CSV não registra desaparecimento (a dedup é por conteúdo,
   sem tempo de saída). **Nenhuma margem deste projeto é acionável sem o usuário conferir na
   tela.** O console tem de dizer isso, uma vez, no cabeçalho da seção.
2. **Ela ignora taxa de mercado, chance de falha do craft e custo de adena.** O World Exchange
   cobra comissão; o craft pode falhar. A "margem" é bruta e sobre ofertas. Isto é escopo do
   v1 e deve estar escrito no `config.toml` ao lado do `[[receita]]`.
3. **Ela não lida com quantidade mínima.** Se o menor pedido de `Leonard` é um lote de 100 e a
   receita precisa de 20, o usuário compra 100. A conta usa o unitário, o que é a
   simplificação certa — mas é uma simplificação, e o console não deve fingir que não é.
4. **Ela herda a fusão aberta da Fase 2.** `B-grade Gemstone` × `C-grade Gemstone` (0,9375)
   podem estar na MESMA série. Se um deles for componente de uma receita, a margem sai errada
   e **não há como o programa saber**. Isto é Deferred Idea registrada — a Fase 4 não a
   conserta, e o plano deve citá-la como limitação conhecida da margem.
5. **Ela não valida que a receita é real.** O programa não conhece o crafting de L2. Um
   `[[receita]]` errado produz uma margem perfeitamente formatada e completamente falsa. A
   única defesa é que o usuário escreveu a receita.

---

## Don't Hand-Roll

| Problema | Não construa | Use | Por quê |
|---|---|---|---|
| Ler o `observacoes.csv` | um parser CSV novo | `_conferir_o_terminador` + `_conferir_o_cabecalho` + `chave_dos_campos` de `mercado_registro.py` | O portão do terminador é o achado central da Fase 3: cinco truncagens byte-a-byte deixam o arquivo sem quebra final e **duas delas produzem seis campos parseáveis** com `80` virando `8` [VERIFIED: mercado_registro.py:461-500]. Um parser novo reintroduz isso |
| Mediana | `sorted(x)[len(x)//2]` ou `statistics.median` | **`statistics.median_low`** | `median` inventa meio centavo em n par (§Alternativas) |
| Unitário | `total / quantidade` em float | `fractions.Fraction(total, quantidade)` | Erro de ponto flutuante pela porta dos fundos |
| Regressão | mínimos quadrados à mão | `statistics.linear_regression` | ANAL-03 diz "regressão stdlib" literalmente |
| Detectar painel aberto | qualquer coisa nova | `mercado_visao.RastreioDoPainel` | Um sinal, dois consumidores. Duplicar é a manobra do 27x |
| Congelamento de captura | comparar a grade | `LeitorDePagina._captura_congelada` (janela inteira) | Medido: o painel é bit-estável; grade parada é o caso NORMAL [VERIFIED: mercado_pagina.py:40-48] |
| Montar `Catalogo`/`Registro` | construir direto | `montar_registro_de_mercado` + uma `montar_catalogo_de_mercado` nova no mesmo trilho | Os dois construtores fazem `mkdir` fora de `try` |
| Escrever o catálogo | `open("w")` | `Catalogo.gravar()` (`.tmp-<pid>` + `os.replace`) | Atomicidade já resolvida [VERIFIED: mercado_catalogo.py:575-600] |
| Moldura de destaque | `print("="*60)` | `console.moldurar` | Já existe, já é sem-cor quando não é tty [VERIFIED: console.py:97-119] |
| Ler `[[receita]]` | `tomllib` solto | função nova em `config.py` no molde de `ler_bosses` | Arquivo ausente e seção ausente **não são erro**; TOML quebrado **é erro de arranque** [VERIFIED: config.py:296-323] |
| Ler a watchlist | importar `calibrar_mercado.ler_watchlist` | função nova em `config.py` | `calibrar_mercado` chama `tornar_consciente_de_dpi()` **no import** [VERIFIED: calibrar_mercado.py:49-51] e arrasta `cv2` GUI |

**Insight central:** quase tudo que esta fase precisa **já existe e já foi medido**. O trabalho
novo é *fiação, cadência, desligamento e desenho* — e a estatística pura, que é ~150 linhas.

---

## Common Pitfalls

### Pitfall 1: o catálogo de nomes fica vazio para sempre
**O que acontece:** o modo roda, o `observacoes.csv` cresce, e `catalogo-de-nomes.csv` nunca
ganha uma linha. Na sessão seguinte tudo é "série nova" outra vez.
**Causa:** passar `catalogo.entradas()` (snapshot) para `LeitorDePagina` e nunca chamar
`catalogo.registrar()` / `catalogo.gravar()`.
**Prevenção:** §2.3. **Sinal de alarme:** o arquivo com só o cabeçalho depois de uma sessão
em que o console disse "li 30 páginas".

### Pitfall 2: "CAPTURA CONGELADA" com o jogo vivo
**O que acontece:** o console entra em congelamento eterno e nenhuma página é aceita.
**Causa:** `minimum_update_interval` igual ou maior que o intervalo do laço (§1.2), ou um
backend que reusa o buffer. O `LeitorDePagina` já copia a janela justamente por isso
[VERIFIED: mercado_pagina.py:417-423].
**Prevenção:** margem de ≥4× entre a cadência da WGC e a do laço.

### Pitfall 3: a tendência sobre carimbos quase-idênticos
**O que acontece:** "caiu 4.000% em 30 observações".
**Causa:** regressão com `x = primeira_vez` — as 10 linhas de uma página distam microssegundos
[VERIFIED: gerar_observacoes_do_censo.py:215, `relogio.agora()` por linha].
**Prevenção:** `x` é ordinal (§3.4). **Sinal:** qualquer percentual acima de ~100%.

### Pitfall 4: comparar totais de quantidades diferentes
**O que acontece:** "menor pedido visível: 4,50" para um item que custa 1.480,00 — porque
4,50 era um lote de 1 unidade de outra coisa, ou a mesma coisa em lote pequeno.
**Prevenção:** ordenar por unitário-`Fraction`; **nunca imprimir total sem quantidade ao lado**.

### Pitfall 5: o tick estoura 1 s e o console mente sobre a cadência
**Causa:** `time.sleep(args.intervalo)` puro em vez de compensar o tempo já gasto.
**Prevenção:** `dormir = intervalo - (time.monotonic() - inicio)` [VERIFIED: __main__.py:2197].

### Pitfall 6: o console vira spam de log
**Causa:** uma linha por tick com o painel fechado — 3.600 linhas por hora.
**Prevenção:** LATCH nas transições; repintar em vez de acumular. Três precedentes já no
`mercado_pagina.py`.

### Pitfall 7: recência do preço trocada pela recência do item
**Causa:** usar `Catalogo.ultima_vez` no lugar de `max(primeira_vez)` (§3.5). Produz "visto às
14:32" ao lado de um preço de terça.

### Pitfall 8: o console do Windows engasgando em acento
**Causa:** cp1252. `configurar_log` já faz `reconfigure(encoding="utf-8", errors="replace")`
[VERIFIED: __main__.py:164-170] — mas **só depois de ser chamado**. Chame `configurar_log`
**antes** de qualquer `print`/`log`, como a ferramenta do censo faz [VERIFIED:
gerar_observacoes_do_censo.py:400]. E siga a doutrina da casa: **sem travessão nem acento em
texto de erro**.

### Pitfall 9: recalcular a mediana já incluindo a linha deste tick
**Prevenção:** §3.7, a ordem do tick.

### Pitfall 10: `[[receita]]` ambígua resolvida "na melhor"
**Prevenção:** §4.3 — casamento exato, quebra listando as candidatas.

---

## Code Examples

### O esqueleto do laço (síntese do precedente do censo + `laco_da_agenda`)

```python
def laco_do_mercado(args, cal) -> int:
    """SO o World Exchange. Sem party, sem rastreador, sem despachante.

    LACO SEPARADO DE PROPOSITO, no precedente literal de `laco_da_agenda`: o
    laco principal e o codigo mais critico do projeto e nao pode ganhar ramos
    que so existem para um modo.
    """
    # 1. OS PORTOES DE ARRANQUE. Aqui o modo NAO SOBE, e nao "sobe degradado" —
    #    subir cego faria o usuario achar que esta coletando.
    if not ocr.disponivel():
        log.error("O motor de OCR nao respondeu: %s", ocr.motivo_indisponivel())
        return 2
    faltando = pecas_de_calibracao_de_mercado_faltando(cal)   # ver nota abaixo
    if faltando:
        log.error("O modo --mercado NAO vai subir: falta %s no calibration.json.",
                  ", ".join(faltando))
        log.error("Rode calibrar-mercado.bat sobre um frame da GRADE DE NEGOCIACAO.")
        return 2

    # 2. A FIACAO. Tres montagens no mesmo trilho: tenta, degrada, devolve None.
    registro = montar_registro_de_mercado()
    if registro is None:
        return 2                      # aqui a feature E o produto
    catalogo = montar_catalogo_de_mercado()
    if catalogo is None:
        return 2
    relogio = montar_relogio(args)
    fonte = JanelaSource(args.janela,
                         Regiao(0, 0, largura_carimbada, altura_carimbada),
                         relativa=True,
                         minimum_update_interval=MS_ENTRE_FRAMES_DO_MERCADO)
    leitor = LeitorDePagina(RastreioDoPainel(ancoras_de_calibracao(cal.mercado_ancoras),
                                            float(cal.mercado_limiar_da_ancora)),
                            catalogo.entradas(),
                            ocr.ler_texto, ocr.ler_texto_ampliado, cal)
    modelo = ModeloDeMercado.do_csv(registro.arquivo)   # leitura UNICA, no arranque

    contagem = Contagem()
    try:
        while True:
            inicio = time.monotonic()
            frame = fonte.capturar()                 # `pixels` E a janela inteira
            pagina = leitor.observar(frame.pixels)
            if pagina is not None:
                agora = relogio.agora()
                for linha in pagina.linhas:
                    destacar_abaixo_da_mediana(modelo, linha)   # ANTES de gravar
                    catalogo.registrar(linha.chave_da_serie, linha.nome_exibido, agora)
                    if registro.registrar(linha, agora):
                        contagem.observacoes += 1
                        modelo.acrescentar(linha, agora)
                    elif registro.ligado:
                        contagem.duplicadas += 1
                    else:
                        contagem.perdidas += 1
            repintar(leitor, modelo, ...)            # o console, a 1 Hz
            dormir = args.intervalo - (time.monotonic() - inicio)
            if dormir > 0:
                time.sleep(dormir)
    except KeyboardInterrupt:
        log.info("Encerrando o modo mercado.")
    finally:
        fonte.fechar()
        catalogo.gravar()                            # ATOMICO, so aqui
        imprimir_o_resumo(leitor, contagem)          # AS DUAS METADES
    return 0
```

⚠️ **`pecas_de_calibracao_de_mercado_faltando`**: **não redigite a lista.** `_calibrado()`
já a tem, com onze chaves e a razão de cada uma [VERIFIED: mercado_pagina.py:698-744]. Extraia
uma função de módulo que `_calibrado` passa a chamar, e acrescente a ela as três chaves que só
o arranque confere hoje: `mercado_ancoras`, `mercado_limiar_da_ancora` e
`mercado_geometria_da_captura` [VERIFIED: __main__.py:423, 450, 1917-1930]. **Uma verdade só**
sobre o que "calibrado para mercado" significa.

### O resumo final — as duas metades, com os motivos agregados

```python
log.info("-" * 66)
log.info("ticks com o painel aberto : %d", leitor.ticks_com_painel_aberto)
log.info("paginas LIDAS             : %d", leitor.paginas_lidas)
log.info("paginas PERDIDAS          : %d", leitor.paginas_perdidas)
log.info("paginas vazias            : %d", leitor.paginas_vazias)
log.info("paginas de OUTRO layout   : %d", leitor.paginas_de_outro_layout)
log.info("frames congelados         : %d", leitor.frames_congelados)
log.info("linhas descartadas        : %d", leitor.linhas_descartadas)
for motivo, quantas in sorted(descartes_por_motivo.items()):
    log.info("   %-26s %d", motivo, quantas)
log.info("observacoes GRAVADAS      : %d", contagem.observacoes)
log.info("duplicadas descartadas    : %d", contagem.duplicadas)
if contagem.perdidas:
    log.info("PERDIDAS (registro OFF)   : %d", contagem.perdidas)
log.info("-" * 66)
```

Os motivos vêm de `PaginaAceita.motivos` e de `LeituraDaPagina.motivos`, e os nomes são
constantes já exportadas: `"oclusao"`, `"numero"`, `"cruzamento"`, `"faixa-cinzenta"`,
`"discordancia-entre-escalas"` [VERIFIED: mercado_leitura.py:1123-1127 — citado verbatim].
Note que o CONTEXT chama um deles de "gramática"; **o valor real da constante é `"numero"`**
(`MOTIVO_DA_GRAMATICA = "numero"`), e o console deve usar a constante, não a palavra do
CONTEXT.

⚠️ **`motivos` só carrega as descartadas da ÚLTIMA leitura de cada página, não um acumulado.**
Para agregar por sessão o laço precisa somar num `Counter` próprio a cada tick, lendo
`leitor.ultima_leitura.motivos` [VERIFIED: mercado_pagina.py:323-332, `ultima_leitura` existe
exatamente para o console da Fase 4].

### O `Fraction` como comparável

```python
from fractions import Fraction

def unitario(total_em_centesimos: int, quantidade: int) -> Fraction:
    """O unitario EXATO. Nunca float: `40,00 / 48` em float acumula erro
    exatamente onde o parsing por molde de digito o evitou."""
    return Fraction(total_em_centesimos, quantidade)

def menor_pedido_visivel(observacoes):
    """A oferta de MENOR unitario. NUNCA "preco de venda": o scanner ve
    ofertas, nao transacoes."""
    return min(observacoes, key=lambda o: unitario(o.total, o.quantidade))
```

---

## State of the Art

| Antes | Agora | Impacto |
|---|---|---|
| `sorted()[n//2]` à mão | `statistics.median_low` (3.4+) | Devolve valor OBSERVADO em n par |
| regressão à mão | `statistics.linear_regression` (3.10+) | ANAL-03 pede stdlib; disponível no 3.12 [VERIFIED] |
| `WindowsCapture` sem controle de taxa | `minimum_update_interval` em `windows_capture` 2.0.1 | A única alavanca real de DETC-02 [VERIFIED: assinatura no `.venv`] |
| `window_name` (substring) | `window_hwnd` também aceito no 2.0.1 | Não necessário aqui, mas registrado: mais confiável para títulos dinâmicos [VERIFIED: docstring] |

---

## Security Domain

O modo não abre porta, não envia nada e não lê segredo. As superfícies são de **entrada não
confiável vinda de arquivo**, e o projeto já as trata assim.

| ASVS | Aplica | Controle padrão nesta fase |
|---|---|---|
| V2 Authentication | não | Sem autenticação; nenhum token é lido por este modo |
| V3 Session Management | não | Sem sessão |
| V4 Access Control | não | Processo local do usuário |
| **V5 Input Validation** | **sim** | Três entradas não confiáveis: **(a)** `calibration.json` — já tratado por `Calibracao.carregar` + `ancoras_de_calibracao` + `cabecalho_de_calibracao`, que **levantam e viram feature OFF** [VERIFIED: __main__.py:439-448]; **(b)** `observacoes.csv`, que o usuário **edita à mão no Sheets** — portão de contrato + duas redes por linha [VERIFIED: mercado_registro.py:461-500, 564-636]; **(c)** `config.toml` `[[receita]]` — validação no molde de `_boss_de_dict`, recusa de arranque com mensagem nomeada |
| V6 Cryptography | não | Nenhuma |

**Ameaça específica desta fase, e ela é de integridade e não de confidencialidade:**

| Padrão | STRIDE | Mitigação |
|---|---|---|
| CSV editado à mão devolvendo número plausível e errado (truncagem que passa na contagem de campos) | Tampering | Portão do terminador ANTES da contagem — já implementado e medido |
| `[[receita]]` com `quantidade = true` virando 1 | Tampering | `isinstance(valor, bool)` **antes** do teste numérico |
| Nome de item ambíguo resolvido "na melhor" | Tampering (do usuário contra si) | Quebra explícita listando candidatas (§4.3) |
| Replay contaminando o registro de produção com carimbo de agora | Tampering | `razao_para_recusar_a_saida` já protege `.mercado/` [VERIFIED: gerar_observacoes_do_censo.py:138-167] — **e o modo `--mercado` não pode ganhar um `--saida`** que fure isso |
| **CSV injection no Sheets** (`nome_exibido` começando com `=`, `+`, `-`, `@`) | Tampering | **NÃO tratado hoje, e não é desta fase**: quem escreve o nome é o OCR, e o `=` não é glifo do conjunto. Registrado como observação, não como ação |

---

## Environment Availability

| Dependência | Requerida por | Disponível | Versão | Fallback |
|---|---|---|---|---|
| Python (.venv) | tudo | ✓ | **3.12.13** | — |
| Python (global, pytest) | suíte | ✓ | **3.12.10** | — |
| `windows_capture` | captura da janela | ✓ | **2.0.1** (com `minimum_update_interval`) | `MssSource` (§Alternativas) |
| `winrt-*` (OCR) | nome do item | ✓ | 3.2.1 | **Nenhum** — sem OCR o modo não sobe |
| `numpy` / `opencv-python` | frames / moldes | ✓ | 2.5.2 / 4.14.0.94 | — |
| `statistics`, `fractions`, `csv`, `tomllib` | análise | ✓ | stdlib | — |
| `rich` | — | ✗ | — | **Console de texto (é a decisão)** |
| `calibration.json` calibrado para mercado | o modo inteiro | ✓ nesta máquina (14 chaves de mercado presentes, `layout: "negociacao"`) | — | **Nenhum — o modo não sobe** |
| `.mercado/observacoes.csv` com dado real | a análise ter o que analisar | **✗** | — | Nasce vazio; o console diz "sem evidência" até a primeira sessão. **Ou** o usuário roda `tools/gerar_observacoes_do_censo.py --saida C:/temp/...` e importa — mas isso NÃO pode ir para `.mercado/` |

**Ausência bloqueante:** nenhuma para o código. **Ausência que afeta a verificação:** não
existe `observacoes.csv` real nesta árvore [VERIFIED: `ls .mercado/` e `ls C:/temp/portao-fase3`
falharam nesta sessão], então **os critérios 3, 4 e 5 da fase não têm material para serem
demonstrados até o usuário rodar o modo por uma sessão de verdade** — ou até alguém rodar a
varredura do censo, que está proibida nesta sessão.

---

## Riscos de coordenação (outro agente na mesma árvore)

| Arquivo | Risco | Mitigação |
|---|---|---|
| `l2scanner/__main__.py` | **DISPUTADO** | Diff de ~14 linhas: uma `add_argument` no fim da lista + um `if` de saída + o `parser.error` do `--mercado` sem `--janela`. Todo o resto em módulos novos |
| **`config.toml`** | **PROIBIDO pelo briefing**, mas o CONTEXT exige o `[[receita]]` comentado lá | **Conflito real, e o plano tem de escolher conscientemente.** Três saídas: (a) o bloco comentado **no fim do arquivo**, onde conflito textual é improvável, numa task isolada e sequenciada por último; (b) o bloco em `config.local.exemplo.toml`, que é versionado e não disputado, com `ler_receitas` lendo os dois arquivos no molde de `_blocos_de_membro` [VERIFIED: config.py:571-598]; (c) adiar o bloco comentado e documentar o formato só no console e no `LEIAME.txt`. **Recomendo (a) com sequenciamento**, porque o CONTEXT é explícito e porque comentário não altera o parse. ⚠️ Depois de tocar `config.toml`, rodar `pytest tests/test_bosses.py tests/test_mira_da_janela.py tests/test_calibracao_generica.py` — os três leem o arquivo real [VERIFIED: grep nesta sessão] |
| `l2scanner/config.py` | Não está na lista de proibidos, mas é vizinho de `bosses.py`/`agenda.py` | As funções novas (`ler_receitas`, `ler_watchlist_do_mercado`) vão no **fim** do módulo, sem tocar nada existente |
| `l2scanner/rastreador.py`, `l2scanner/visao.py` | **PROIBIDOS** | `git diff --stat` vazio neles é portão da fase |
| `l2scanner/mercado_pagina.py` | Só a extração de `_calibrado` → função de módulo | Mudança de refactor pura, com o teste existente como rede |
| `l2scanner/captura_janela.py` | Um parâmetro opcional `minimum_update_interval=None` | Padrão `None` = comportamento de hoje. Teste que prova que o party não mudou |

---

## Assumptions Log

| # | Afirmação | Seção | Risco se estiver errado |
|---|---|---|---|
| A1 | `minimum_update_interval=250` é seguro (margem 4× contra o congelamento) | 1.2 | Escolhido, não medido. Errado → "CAPTURA CONGELADA" falso ou economia menor que a esperada. Mitigação: constante nomeada + teste do padrão `None` |
| A2 | ~273 MB/s de cópia por sessão WGC | 1.1 | Derivado de 7,2 MB (medido) × 38 fps (comentário). Se a WGC entrega menos com a janela sem foco, o número é menor — o que só ajuda |
| A3 | Três sessões WGC simultâneas sobre o mesmo HWND funcionam sem borda amarela | 1.2 | Duas já funcionam empiricamente; três é extrapolação. Errado → borda visível no jogo. Portão humano em 1.4(b) o pega |
| A4 | Piso n≥5 para mediana, n≥8 para tendência, n≥1 com rótulo para o mínimo | 3.3 | **Escolhas puras.** Errado → console cala demais (n alto) ou afirma demais (n baixo). Ajustável numa linha |
| A5 | Limiar de staleness de 24 h para o marcador | 4.4 | Escolha. Errado → marcador irrelevante ou ausente |
| A6 | `rende` obrigatório em vez de padrão 1 | 4.2 | Escolha. Errado → usuário reclama de verbosidade |
| A7 | Gravar o catálogo a cada 20 páginas aceitas, além do `finally` | 2.3 | Escolha. Errado → I/O demais ou perda maior num `taskkill` |
| A8 | O usuário roda `--mercado` sobre a MESMA janela que uma das party | 1.2 | `calibration.json` só guarda uma `janela`. Se ele tiver dois clientes, a terceira sessão vai para outro HWND e o risco cai |
| A9 | Casamento exato (caixa normalizada) resolve os nomes de receita na prática | 4.3 | Se o `nome_exibido` do OCR oscilar entre sessões, a receita quebra e o usuário tem de copiar o nome do CSV. É falha FECHADA, que é o desfecho certo |

---

## Open Questions (RESOLVED — exceto a Q1, aberta de propósito)

**Estado em 2026-08-31, depois do planejamento da fase:** quatro das cinco foram resolvidas
nos planos 04-01 a 04-05, com o caminho de cada uma anotado abaixo. **A Q1 continua ABERTA
e isso é deliberado:** a medição custa mais de 10 minutos de varredura do censo, ela está
proibida nesta sessão, e nenhum plano depende dela para executar — ela valida ou refuta um
piso que já está escrito no fonte como escolha, e ajustá-lo é uma linha.

1. **Quantas observações DISTINTAS por série o material real produz?** — **ABERTA, de
   propósito.**
   - Sabemos: 151 páginas, ≥7 linhas cada, 39 séries [VERIFIED].
   - Não sabemos: quantas sobrevivem à dedup por `(serie, total, quantidade)`.
   - **Recomendação:** é o número que valida ou refuta o piso n≥5. Mede-se rodando
     `tools/gerar_observacoes_do_censo.py --saida C:/temp/... --gravacao <uma>` — **proibido
     nesta sessão**, e deve virar uma medição de Wave 0 do plano, com UMA gravação, não as 8.
   - **Por que ela ficou aberta e não virou task:** a varredura passa de 10 minutos e já
     matou dois agentes nesta árvore. Nenhum plano da fase depende do número para executar.
     O piso `N_MINIMO_PARA_MEDIANA = 5` está no fonte declarado como ESCOLHA, com teste
     (`04-02`, critério do `assert 'escolha' in m.__doc__.lower()`), e a medição, quando
     acontecer, muda uma linha. O caminho mais barato para o número real não é a varredura:
     é o usuário rodar `--mercado` por uma sessão de farm de verdade, que é o portão humano
     do `04-05`.

2. **A margem de craft usa "menor" ou "mediana" como conta principal?**
   - Proposta: **menor** (§4.1), com a mediana como linha secundária.
   - Depende de o usuário querer "quanto eu ganharia se comprasse agora" (menor) ou "quanto
     isso vale em geral" (mediana). Discretionary; a proposta está justificada.
   - **(RESOLVED)** `04-04-PLAN.md` Task 2(a) adotou **menor** como conta principal, com a
     mediana como linha secundária, e escreveu no fonte as duas razões: é assim que um humano
     compraria e venderia, e a mediana exigiria o piso de cinco POR COMPONENTE, o que
     multiplicaria a chance de a margem inteira cair.

3. **O `[[receita]]` vai para `config.toml` (disputado) ou `config.local.exemplo.toml`?**
   - Ver §Riscos. É a única decisão desta pesquisa que **contraria uma restrição do briefing
     para honrar uma decisão do CONTEXT**, e por isso está no topo das Open Questions.
   - **(RESOLVED)** Saída (a), decidida pelo orquestrador e aplicada no `04-05-PLAN.md`
     Task 2: bloco **comentado, no FIM do `config.toml`**, em task **isolada e sequenciada
     por último na fase**, com `<precondition>` que confere `git status` antes de escrever,
     critério mecânico de **zero linhas removidas**, e os três testes que leem o arquivo real
     como rede.

4. **O console mostra `residuo_do_cruzamento`?**
   - A guarda está **DESLIGADA** (`mercado_tolerancia_do_cruzamento = None`, reprovada por
     medição) [VERIFIED: calibration.json + mercado_pagina.py:257-261]. Se aparecer, tem de ser
     como **observação**, jamais como veredito. **Recomendação: não mostrar no repintar de
     1 Hz** — ele já está no CSV para o usuário olhar no Sheets. Mostrar um número que o
     próprio projeto declarou não-decidível é convidar a interpretação errada.
   - **(RESOLVED)** Recomendação acatada. `04-03-PLAN.md` restrição 5 proíbe mostrá-lo no
     repintar, e `04-01-PLAN.md` Task 3 tem o critério `grep -n "residuo"` sobre
     `mercado_console.py` provando que ele não aparece em `linha_ao_vivo`.

5. **As duas conferências humanas abertas da Fase 2** (o OCR real DENTRO do tick, e o
   congelamento provocado) fecham naturalmente aqui — mas só quando o usuário rodar o modo
   ao vivo. O plano deve nomeá-las como portões humanos desta fase, não presumi-las fechadas.
   - **(RESOLVED)** Nomeadas como portão humano em dois lugares, e nunca presumidas
     fechadas: `<human-check>` do `04-01-PLAN.md` e o fecho da fase no `<human-check>` do
     `04-05-PLAN.md`. Como `human_verify_mode` é `end-of-phase`, elas vivem em
     `<verify><human-check>` e não como task de checkpoint.

---

## Sources

### Primárias (ALTA confiança — código e execução desta árvore, lidos/rodados nesta sessão)
- `l2scanner/mercado_pagina.py` — `LeitorDePagina`, contadores :310-321, `observar` :334-404, `_calibrado` :698-744, congelamento :88-93/408-455
- `l2scanner/mercado_registro.py` — `COLUNAS` :124-131, `chave_da_observacao` :149-166, `campos_da_observacao` :168-181, portão de contrato :461-500, `_montar_o_indice` :564-636, `registrar` :648-729
- `l2scanner/mercado_catalogo.py` — `PASTA_DO_MERCADO`/`SEPARADOR` :374-381, `COLUNAS` :383, `SerieDeNome` :387-405, `Catalogo` :408-635
- `l2scanner/mercado_leitura.py` — constantes de motivo :1123-1127, `Descarte` :1166-1180, `_recusar` :1609-1616
- `l2scanner/__main__.py` — `configurar_log` :155-186, `montar_gravador` :227-277, `montar_vigia_do_mercado` :406-465, `montar_registro_de_mercado` :468-544, `montar_relogio` :559-614, `desenhar_status` :617-724, `laco_da_agenda` :1476-1652, `laco_principal` :1852-2274, `main` :2277-2497
- `l2scanner/captura_janela.py` — constantes :34-43, `JanelaSource` :207-446
- `l2scanner/frames.py`, `l2scanner/console.py`, `l2scanner/relogio.py`, `l2scanner/config.py` (`ler_bosses` :296-408, `_blocos_de_membro` :571-598)
- `tools/gerar_observacoes_do_censo.py` — arquivo inteiro
- `tests/test_mercado_27x.py` (tripwires :254-268), `tests/test_firewall_escopo.py` (banlist :66-78), `tests/test_mercado_replay.py`
- `calibration.json`, `config.toml`, `requirements.txt`, `vigiar-party.bat`, `.gitignore`
- **Execuções nesta sessão:** `python -c "import statistics"` (median/median_low/linear_regression e as três `StatisticsError`), `tomllib.loads` das duas formas de `[[receita]]`, `inspect.signature(WindowsCapture.__init__)` no `.venv`, `ls .venv/Lib/site-packages`, `os.cpu_count()`

### Secundárias (MÉDIA confiança — artefatos de planejamento deste projeto)
- `.planning/workstreams/mercado/phases/02-leitura-de-p-gina/02-RESEARCH.md:705-720` — a tabela do orçamento do tick (~110 ms), medida
- `02-05-SUMMARY.md:153,176,188` — 517 frames, 478 ticks, 151/189, 39 séries, as três famílias de perda
- `02-08-PLAN.md:142` / `02-08-SUMMARY.md:154-168` — 1.135 → 1.148 linhas completas
- `02-VERIFICATION.md:184-190` — o rendimento como decisão de produto ainda aberta
- `.planning/workstreams/mercado/ROADMAP.md`, `REQUIREMENTS.md`, `04-CONTEXT.md`

### Terciárias (BAIXA/MÉDIA — web, para o comportamento da API do Windows)
- learn.microsoft.com — `GraphicsCaptureSession`, `IGraphicsCaptureItemInterop::CreateForWindow`
- blogs.windows.com — "New Ways to do Screen Capture" (múltiplas sessões, borda amarela)

---

## Metadata

**Confiança por área:**
- Fiação e laço: **ALTA** — todo o material é código desta árvore, com linha citada
- Contadores do console: **ALTA** — já existem e foram escritos para esta fase
- Custo de recursos (DETC-02): **MÉDIA** — o tick é medido; a cópia WGC é derivada; a contenção entre 3 processos **não é medível por teste** e está proposta como portão humano
- Estatística stdlib: **ALTA** — verificada executando o interpretador
- Pisos de evidência: **BAIXA** — escolhas declaradas, nenhuma medição existe
- Margem de craft: **MÉDIA** — a forma do TOML é verificada; a definição da margem e a resolução de nomes são propostas com as cinco limitações escritas

**Data:** 2026-08-31
**Válido até:** ~30 dias, ou até alguém rodar o censo e produzir o primeiro `observacoes.csv`
real — esse número muda o §3.3 e é a única coisa aqui que uma medição de 10 minutos resolveria.
