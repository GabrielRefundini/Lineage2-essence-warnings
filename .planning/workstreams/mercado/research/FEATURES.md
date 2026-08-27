# Feature Research — Captura Passiva de Preços de Mercado (World Exchange)

**Domain:** Rastreamento de preços de mercado em MMO por leitura de tela (sem API, sem pacotes, sem input)
**Researched:** 2026-08-27
**Confidence:** MEDIUM (achados sobre o cliente XM Essence especificamente são **UNVERIFIED** até os prints do usuário confirmarem — ver nota abaixo)

---

## ⚑ RESPOSTA À PERGUNTA 1 — a maior incógnita do milestone

### O World Exchange já mostra histórico/gráfico de preços? **NÃO. Mas mostra um "preço médio" por item — um número único, sem série temporal.**

**Veredito em uma linha:** o milestone **não** encolhe para "ler um número já na tela" nem permanece "acumular série por semanas" — ele se divide em dois: **"quanto vale AGORA"** já está na tela (listagens ordenáveis por preço + preço médio embutido) e sai no v1; **"tendência/histórico"** não existe no cliente e continua exigindo acumulação própria — mas vira feature opcional/adiável, não fundação do milestone.

**Evidência (a cadeia):**

1. **Nomenclatura.** No Essence oficial (4game/NCSoft) o sistema chama-se **"World Trade"**; nos emuladores de servidor privado **L2J-Mobius** (a base de facto dos servidores Essence privados) chama-se **"World Exchange"** — exatamente o termo que o usuário usa. Isso é um indício MEDIUM de que o XM roda uma base Mobius ou derivada. ([l2.wiki World Trade](https://l2.wiki/essence/wiki/gameplay/world-trade/en); [GitLab MobiusDevelopment/L2J_Mobius](https://gitlab.com/MobiusDevelopment/L2J_Mobius))

2. **O preço médio existe e é UI nativa do cliente.** Fonte primária: o código do Mobius Essence (branch `L2J_Mobius_Essence_07.3_SevenSigns`) tem o pacote de servidor `WorldExchangeAveragePrice` — envia `itemId` + `long averagePrice` para o cliente exibir. O cliente pede via `ExWorldExchangeAveragePrice` (provavelmente ao selecionar um item, no fluxo de registro de venda). Confirmação independente do lado oficial: o patch note de abril/2024 do Essence corrigiu "bug na página principal do World Trade onde o preço médio era exibido incorretamente" — ou seja, **o cliente oficial exibe preço médio na página principal**. ([l2wiki April 2024 update](https://l2wiki.com/essence/articles/2559.html)) — **HIGH** para "o número existe na UI"; **MEDIUM** para "onde exatamente aparece".

3. **Mas o "preço médio" do Mobius é fraco.** `WorldExchangeManager.getAveragePriceOfItem()` = média dos **preços das listagens ATIVAS no momento** — não é histórico de vendas. Pior: é a média do preço **total de cada lote**, sem ponderar pela quantidade (um lote de 10.000 SS e um lote de 100 SS pesam igual). Ler esse número por OCR seria ler uma estatística ruidosa. **Raspar as linhas visíveis da lista (ordenada por preço por unidade) produz min/mediana melhores do que o número que o jogo mostra.** — **HIGH** (código-fonte lido diretamente).

4. **Não há nenhum pacote de histórico.** O conjunto completo de pacotes do World Exchange no Mobius: `ItemList`, `AveragePrice`, `BuyItem`, `RegisterItem`, `SellCompleteAlarm`, `SettleList` (vendas do próprio jogador), `SettleRecvResult`, `TotalList`. **Nenhum transporta série temporal, gráfico ou preço de transações passadas de terceiros.** O servidor nem guarda esse dado para expor. — **HIGH** para bases Mobius; **UNVERIFIED** para o XM se for uma base fortemente customizada.

### O que a janela do World Exchange mostra (para calibração de leitura)

Derivado do protocolo (o que o cliente RECEBE define o que a UI PODE mostrar) + patch notes oficiais:

| Elemento | Detalhe | Confiança |
|---|---|---|
| **Campos por listagem** | preço total do lote (`long`), tempo restante da oferta, item id (nome resolvido pelo cliente), **quantidade** (`long`), nível de encanto (+N), augment, atributos elementais, visual, soul crystals | HIGH (pacote `WorldExchangeItemList`) |
| **Colunas ordenáveis** = colunas visíveis | nome do item, **preço**, **quantidade**, **preço por unidade** — asc/desc cada (`WorldExchangeSortType`: NAME/PRICE/AMOUNT/PRICE_PER_PIECE) | HIGH (enum no código) |
| **Categorias/abas** | Weapon, Armor, Accessory, Etc, 4 tipos de scroll de encanto, Spiritshot, Soulshot, Buff, Variation Stone, Dye, Soul Crystal, Skillbook, Potion/Scroll, Ticket, Craft, Adena, etc. (22 subtipos) | HIGH (enum `WorldExchangeItemSubType`) |
| **Busca** | por nome do item; o cliente resolve nome→ids localmente e pede as listagens desses ids ao servidor | MEDIUM (fluxo do `ExWorldExchangeItemList` com `itemIdList`) |
| **Paginação** | servidor manda até **100 itens por página lógica**; quantas linhas cabem na janela visível é **desconhecido** (tipicamente ~8–10 em UIs L2) — **precisa de print** | MEDIUM / UNVERIFIED |
| **Formato numérico** | preço por unidade com **3 casas decimais** ("3 characters after comma displayed in the price for 1 pc") e **separadores de milhar** (patch notes mencionam bug de separador decimal divergente) — símbolo do separador pode variar com locale do cliente | MEDIUM ([l2wiki](https://l2wiki.com/essence/articles/2559.html)) |
| **Moeda** | vendas liquidadas em **L-Coin** (taxa ~5%); registro cobra taxa em **Adena** (100% do preço, no oficial). Servidor privado pode ter customizado moeda/taxas | MEDIUM, UNVERIFIED no XM |
| **Detalhe por item** | não há "página do item" com gráfico; o preço médio aparece como número único (fluxo de registro/seleção) | MEDIUM |

### ⚠ O que fica UNVERIFIED até os prints do usuário (spike de campo obrigatório)

O XM Essence é servidor privado — pode rodar Mobius puro, Mobius customizado, ou base própria. **Nada acima vale como calibração até o usuário fotografar a própria janela.** O spike de campo precisa responder:

1. A janela existe e chama-se "World Exchange"? Quais abas/colunas reais?
2. Quantas **linhas visíveis** por página e a geometria (posição fixa? redimensionável?)
3. Onde o **preço médio** aparece (se aparece) e para quais fluxos
4. Formato dos números no cliente do usuário: separador de milhar, decimais, fonte
5. Moeda das listagens (L-Coin? Adena? custom coin do XM?)
6. A lista atualiza sozinha ou só ao re-buscar? (afeta staleness da captura)

---

## PERGUNTA 2 — Feature Landscape de trackers "só-o-que-o-jogador-vê"

Padrão da categoria (addons WoW [Auctionator PriceTracker](https://www.curseforge.com/wow/addons/auctionator-pricetracker), [Market Tracker](https://www.curseforge.com/wow/addons/market-tracker-global-auction-house-tracker-viewer), [Market Watcher](https://www.curseforge.com/wow/addons/market-watcher); [Forza AH tracker](https://forza.labsgg.com/auction-house); price-checkers OCR de PoE2): quando não há API, a arquitetura universal é **captura oportunista** — o tool grava o que o jogador olha, acumula snapshots locais, e responde consultas a partir do acumulado. Ninguém varre o mercado inteiro; todos usam **watchlist**.

### Table Stakes (sem isso o produto parece quebrado)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Detecção "janela de mercado aberta"** | Sem isso o scanner não sabe QUANDO ler; é o gatilho de tudo | MEDIUM | Âncora de template no topo da janela (mesmo padrão da party window do v1). Reusa WGC + calibração existentes |
| **Captura oportunista das linhas visíveis** | O padrão da categoria: gravar o que o jogador vê, quando vê | MEDIUM | Rects calibrados por linha (reusa tooling `pick_region`/HSV). O usuário navega; o scanner só lê |
| **Watchlist em `config.toml`** | Todos os trackers view-only restringem a itens de interesse; conjunto fechado viabiliza matching | LOW | Mesmo padrão dos horários de evento do v2: editável à mão, sem commit |
| **Leitura de preço/quantidade (dígitos + separadores)** | O dado central. Dígitos são conjunto fechado de ~12 glifos — mais fácil que nome | MEDIUM | Template por glifo (como nomes no v1) ou OCR; separador de milhar e 3 decimais confirmados no oficial — calibrar com prints |
| **Identificação do item da linha** | Preço sem item é ruído | MEDIUM | Fuzzy match (rapidfuzz) do nome OCR **contra a watchlist** — nunca leitura aberta. Espelho da decisão v1 (roster fechado) |
| **Persistência local com timestamp** | Snapshot sem hora não vira histórico nem responde "quão velho é esse preço" | LOW | JSONL ou SQLite: `(ts, item, unit_price, qty, total)`. Dedupe de lote re-visto na mesma sessão |
| **Consulta via WhatsApp ("preço X")** | A superfície de comando já existe; é onde o usuário vive | LOW | Responde último snapshot: min/mediana visível + idade da observação ("há 2h") |
| **Staleness explícita em toda resposta** | Preço de ontem apresentado como atual é pior que nenhum preço — anti-feature clássica da categoria | LOW | "visto às 14:32" em toda resposta; recusa/aviso acima de N horas (config) |

### Differentiators (vantagem competitiva; alinhados ao Core Value = avisar no WhatsApp)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Alerta de "preço bom"** | DNA do projeto: push no WhatsApp quando listagem visível fica abaixo do limiar da watchlist | LOW (dado o pipeline) | Reusa debounce/cooldown do v1. Limiar manual primeiro; relativo à mediana depois |
| **Estatísticas de histórico (min/max/mediana/tendência)** | O que o jogo NÃO mostra (confirmado Q1) — o acumulado local vira o diferencial real | MEDIUM | Só fica útil após semanas de observações; por isso é v-next, não fundação |
| **Margem de craft (produto vs componentes)** | "Vale a pena craftar?" respondido no WhatsApp | MEDIUM | Receitas em config + preços da watchlist. Depende de estatísticas confiáveis primeiro |
| **Dedupe entre as 2 instâncias** | Usuário roda Yazalaque + Faerlina; observações duplicadas inflam stats e duplicam alertas | MEDIUM | Mesmo problema já resolvido em AGEN-07 — reusar o padrão |
| **Registro do preço médio nativo do jogo** | Se o print confirmar onde aparece, é um dado extra grátis por leitura | LOW | Complementar, nunca fonte única (é média de asks, não de vendas — ver Q1.3) |

### Anti-Features (parecem boas, quebram o projeto)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Varredura automática do mercado (paginar/buscar sozinho)** | "Cobre tudo, histórico completo" | Exige **enviar input ao jogo** — viola a constraint inegociável (risco de ban zero, scanner somente-leitura) | Captura oportunista: o humano navega, o scanner lê |
| **OCR aberto de qualquer item de qualquer categoria** | "Rastrear o mercado todo" | OCR open-set de fonte estilizada é o buraco de coelho que o v1 evitou de propósito no roster | Watchlist fechada + fuzzy match; crescer a lista em config |
| **Ler só o "preço médio" do jogo como fonte de verdade** | "O número já está pronto na tela" | É média de listagens ativas por LOTE, sem ponderar quantidade, sem histórico — estatística enganosa (fonte: código Mobius) | Raspar linhas visíveis ordenadas por preço/unidade → min/mediana reais |
| **Gráficos/dashboard em tempo real** | "Como os sites de GE/AH" | 1 jogador olhando o mercado esporadicamente = dado esparso; um gráfico bonito de dado esparso mente | Respostas textuais no WhatsApp com min/mediana/idade |
| **Previsão de preço / ML** | "Me diga quando comprar" | Sem volume de transações (invisível na UI), qualquer modelo é astrologia | Limiar configurável + comparação com mediana histórica |

## Feature Dependencies

```
Detecção "mercado aberto" (âncora template)
    └──requires──> WGC + calibração (v1, já existe)
Leitura de linhas (preço/qty/item)
    └──requires──> Detecção "mercado aberto"
    └──requires──> Spike de campo com prints do XM  ⚑ BLOQUEIA TUDO
Watchlist match ──requires──> Leitura de linhas
Persistência com timestamp ──requires──> Leitura de linhas
Consulta WhatsApp ──requires──> Persistência + superfície de comandos (v-anterior, já existe)
Alerta de preço bom ──requires──> Watchlist match + transporte Chatwoot (v1, já existe)
Estatísticas de histórico ──requires──> Persistência acumulada (semanas)
Margem de craft ──requires──> Estatísticas de histórico
Dedupe 2 instâncias ──enhances──> Persistência + Alertas (padrão AGEN-07)
Varredura automática ──conflicts──> constraint somente-leitura (NUNCA)
```

## MVP Definition

### Launch With (v1 do milestone)
- [ ] Spike de campo: prints do World Exchange do XM validam/refutam tudo da Q1 — **primeira fase, gate do resto**
- [ ] Detecção de janela de mercado aberta (âncora topo)
- [ ] Leitura das linhas visíveis: item (fuzzy vs watchlist) + quantidade + preço unitário
- [ ] Watchlist em `config.toml`
- [ ] Persistência local com timestamp + dedupe intra-sessão
- [ ] Consulta "preço X" no WhatsApp com min/mediana do último snapshot + idade

### Add After Validation (v1.x)
- [ ] Alerta push de preço abaixo do limiar — assim que a leitura provar zero falso-positivo
- [ ] Dedupe entre as duas instâncias — assim que ambas capturarem mercado

### Future Consideration (v2+)
- [ ] Estatísticas de tendência (precisa de semanas de dados acumulados)
- [ ] Margem de craft (precisa de estatísticas confiáveis)
- [ ] Leitura do preço médio nativo como sinal complementar

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Spike de campo (prints) | HIGH | LOW | P1 |
| Detecção mercado aberto | HIGH | MEDIUM | P1 |
| Leitura de linhas + watchlist | HIGH | MEDIUM | P1 |
| Persistência + staleness | HIGH | LOW | P1 |
| Consulta WhatsApp | HIGH | LOW | P1 |
| Alerta de preço bom | HIGH | LOW | P2 |
| Dedupe 2 instâncias | MEDIUM | MEDIUM | P2 |
| Estatísticas de histórico | MEDIUM | MEDIUM | P3 |
| Margem de craft | MEDIUM | MEDIUM | P3 |

## Sources

- [GitLab MobiusDevelopment/L2J_Mobius](https://gitlab.com/MobiusDevelopment/L2J_Mobius) — código lido diretamente (branch Essence 07.3 SevenSigns): `WorldExchangeAveragePrice.java`, `WorldExchangeItemList.java`, `WorldExchangeManager.getAveragePriceOfItem()`, `WorldExchangeSortType`, `WorldExchangeItemSubType`, `ExWorldExchangeItemList.java` — **HIGH** (fonte primária)
- [World Trade — l2.wiki Essence](https://l2.wiki/essence/wiki/gameplay/world-trade/en) e [l2central.info art. 1138](https://l2central.info/essence/articles/1138.html?lang=en) — mecânica oficial (taxas, cashier, 14 dias) — **MEDIUM**
- [April 2024 update — l2wiki.com](https://l2wiki.com/essence/articles/2559.html) — bug fix do preço médio na página principal; 3 decimais no preço por unidade; separadores — **MEDIUM**
- [Guia World Trade — 4gameforum](https://eu.4gameforum.com/threads/686995/) — fluxo de venda mostra listagens equivalentes para comparação de preço — **LOW** (guia de jogador, 2022)
- [Auctionator PriceTracker](https://www.curseforge.com/wow/addons/auctionator-pricetracker), [Market Tracker](https://www.curseforge.com/wow/addons/market-tracker-global-auction-house-tracker-viewer), [Market Watcher](https://www.curseforge.com/wow/addons/market-watcher) (WoW), [Forza AH tracker](https://forza.labsgg.com/auction-house), [Path of Price Check (OCR, PoE2)](https://apps.apple.com/qa/app/path-of-price-check-poe2-tool/id6741771726) — feature landscape da categoria view-only — **MEDIUM**
- XM Essence ([l2xm.com](https://l2xm.com/)) — nenhuma documentação pública do mercado encontrada; base do servidor não identificável por busca — **é por isso que tudo específico do XM fica UNVERIFIED até os prints**

---
*Feature research for: captura passiva de preços — World Exchange, L2 XM Essence*
*Researched: 2026-08-27*
