# Requirements: L2 Party Scanner — Mercado (v1-mercado)

**Defined:** 2026-08-27
**Core Value:** Cada vez que o usuário abre o World Exchange vira uma coleta de dados — preços dos itens que ele acompanha, lidos passivamente da tela, sem nunca enviar input ao jogo.

## v1 Requirements

Requisitos do milestone v1-mercado. Cada um mapeia para uma fase do roadmap.

### Firewall de escopo

- [x] **FIRE-01**: O build quebra se qualquer biblioteca de síntese de input entrar na árvore de dependências (estende o ban de `pyautogui` do v1)

### Fundação (spike de campo)

- [x] **FUND-01**: O gravador só conta frames confirmados no disco — retorno do `cv2.imwrite` checado, falha aparece alto (pré-requisito da coleta de evidência da spike)
- [x] **FUND-02**: Sessões reais do World Exchange gravadas com `--record`, com as perguntas de campo respondidas e registradas: linhas por página, separador de milhar, moeda, colunas, onde fica o preço médio embutido
- [x] **FUND-03**: Calibração do mercado (regiões da janela, âncora do painel, templates de dígito) persiste em `calibration.json` via ferramenta própria

### Detecção

- [x] **DETC-01**: "World Exchange aberto" detectado por âncora/template positivo, e o sinal é compartilhado com a lógica de oclusão do detector de morte — um sinal, dois consumidores, nunca duplicado
- [x] **DETC-02**: Modo `--mercado` separado — vigiar mercado não degrada nem compete com o modo party (o usuário roda duas instâncias; uma terceira invocação é normal)

### Leitura

- [x] **LEIT-01**: Nome do item lido por OCR sobre o recorte da coluna do nome e agrupado por similaridade contra os nomes já vistos; um nome que não casa com nenhum conhecido entra como SÉRIE NOVA, sem intervenção do usuário — o que é registrado não depende de lista prévia
- [x] **LEIT-02**: Preços e quantidades lidos por template-por-dígito com falha FECHADA: frame ilegível é descartado, preço nunca é inventado
- [x] **LEIT-03**: Página só é aceita quando dois frames consecutivos concordam nas linhas PARSEADAS (nunca em pixels — frames bit a bit idênticos são o sinal de captura congelada)
- [x] **LEIT-04**: Console mostra ao vivo páginas lidas/perdidas e último item reconhecido; resumo final conta as duas metades ("li 7, perdi 3")
- [x] **LEIT-05**: A leitura do nome usa o recorte da COLUNA DO NOME, nunca a linha inteira — a coluna é calibrada e persistida em `calibration.json`. Medido: com a tooltip aberta, o texto dela vaza para dentro da linha e viraria nome de item

#### Por que o OCR de nomes voltou ao escopo

Até 2026-08-29 este documento excluía explicitamente a leitura de nomes de item por OCR. A
entrada da tabela Out of Scope dizia `| OCR aberto para nomes de item | ... |`, e ela saiu de
lá nesta data. O raciocínio derrubado fica registrado aqui, porque o que derruba uma decisão
importa mais que a decisão derrubada.

**De onde a exclusão veio, e o que ela realmente era.** Ela nasceu em `db751c7` (2026-08-27).
A primeira gravação do World Exchange no disco é de 2026-08-28 05:31. O OCR foi descartado
**um dia antes de existir um frame do mercado para medir contra**. A justificativa escrita —
a lista ser conjunto fechado — não era um achado técnico: era uma decisão de PRODUTO
registrada com aparência de achado técnico. Não havia medição nenhuma por baixo dela.

**O que caiu não foi uma medição: foi a premissa.** Em 2026-08-29 o usuário declarou que quer
acompanhar TODOS os itens do mercado, e que um item novo postado precisa ser reconhecido sem
mapeamento prévio. A lista pré-configurada só servia de portão enquanto o conjunto fosse
pequeno e conhecido de antemão. Deixou de ser as duas coisas no mesmo dia.

**E o portão não fica só trabalhoso — ele para de funcionar.** A calibração recusa ALTO
quando dois moldes de nome colidem; isso é proteção deliberada, registrada como must_have em
`01-04-PLAN.md`. Nomes do L2 compartilham prefixo em profusão, e isso não é hipótese: a
própria página do usuário trouxe `Common Aztac` e `Common Aztac M. Def. +200`. Com o mercado
inteiro como conjunto, é a salvaguarda funcionando CORRETAMENTE que trava a calibração. Um
conjunto fechado grande não é um conjunto fechado caro — é um conjunto fechado impossível.

**O que a medição mostrou, e o que ela recusou.** A spike registrada em
`260829-rd9-EVIDENCIA-SPIKE-OCR.md` passou as linhas gravadas pelo motor de OCR do Windows:
os NOMES saem estáveis o bastante para agrupamento por similaridade; os NÚMEROS não saem — a
vírgula decimal some, e `16,50` volta como `1650`, um erro de 100x com aparência plausível.
Conclusão travada: nome por OCR, preço e quantidade por molde — LEIT-02 não muda, e essa
medição é exatamente a razão de ele existir. A mesma spike produziu LEIT-05: lendo a linha
inteira, o texto de uma tooltip aberta entra na leitura como se fosse nome de item.

**O que sobra da lista configurada.** Ela deixa de decidir O QUE É REGISTRADO — isso passa a
ser tudo que aparece na tela. No máximo ela vira um filtro de DESTAQUE no console, que é
território da Fase 4 (ANAL-01, ANAL-02). Nenhum requisito novo é criado aqui para esse papel.

### Persistência

> **DECISÃO DO USUÁRIO (2026-08-29): CSV, não SQLite.** Esta seção foi reescrita; a
> redação anterior (SQLite + WAL + `INSERT OR IGNORE`) está superada. O histórico da
> decisão fica abaixo porque o raciocínio importa mais que a conclusão.

- [x] **PERS-01**: Observações gravadas como linhas num arquivo CSV com carimbo do relógio ancorado, uma linha por observação, legível a olho nu e importável no Google Sheets sem conversão
- [x] **PERS-02**: Revisitar uma página não duplica observações — dedup por chave de conteúdo, conferida em memória antes de escrever
- [x] **PERS-03**: Falha de escrita desliga só a feature de mercado e avisa alto — nunca derruba o núcleo de alertas

#### Por que CSV, e por que a decisão mudou duas vezes

A pesquisa e o roadmap originais pediam SQLite, com três justificativas. Duas caíram e a
terceira perdeu para um caso de uso que ninguém tinha declarado:

1. **Escrita concorrente entre as duas instâncias** — MORREU em 2026-08-28, quando o
   usuário corrigiu que **o mercado lê SEMPRE do Yazalaque**. Há um único escritor. As duas
   instâncias de party continuam existindo (é a razão da AGEN-07), mas nenhuma escreve dado
   de mercado.

2. **Dedup de custo constante por índice `UNIQUE`** — enfraqueceu junto: com um escritor só,
   o conjunto de chaves de conteúdo cabe em memória, carregado uma vez no arranque. O custo
   linear que eu temia era do cenário multiprocesso que não existe.

3. **Consultas de análise a cada tick** — real, mas dimensionada errada. O volume aqui é de
   milhares de linhas, não milhões; `statistics` sobre uma lista em memória resolve.

**O que decidiu, e não estava na mesa antes:** o usuário quer **ler o dado com os próprios
olhos, jogar no Google Sheets, e entregar para outra IA analisar**. CSV serve os três
nativamente. Um `.db` não serve nenhum sem ferramenta no meio — e "exportar depois" é um
passo a mais em todo uso real, não um detalhe.

#### O que o CSV OBRIGA a fazer, e que o SQLite dava de graça

Estas não são sugestões: são as três falhas que a escolha traz junto, e cada uma tem de ter
mecanismo próprio.

- **Append interrompido trunca a última linha.** Escrever linha a linha com `flush` a cada
  uma, e na leitura tolerar uma última linha malformada descartando-a com aviso — nunca
  tratando o arquivo inteiro como corrompido. Esta é a mesma família do FUND-01: o dado
  parcial não pode virar dado plausível.

- **Dedup vira responsabilidade nossa.** Carregar as chaves de conteúdo existentes no
  arranque, manter em memória, conferir antes de escrever. Se o arquivo não puder ser lido,
  a feature desliga alto (PERS-03) em vez de duplicar calado.

- **O separador decimal colide com o separador de campo.** A decisão travada em
  `SPIKE-RESPOSTAS.md` seção 2 é exibição em padrão brasileiro (`5.000.000` e `62,00`), e a
  vírgula decimal quebraria um CSV separado por vírgula. **Separador de campo: `;`** — que é
  o que o Google Sheets em português espera. Isto tem de ser TESTADO com uma importação
  real antes de fixar: um CSV que abre com tudo numa coluna só é pior que nenhum.

#### O que NÃO muda

Preços continuam guardados como **inteiros** (centésimos), nunca float — a acumulação de
erro de ponto flutuante entraria pela porta dos fundos exatamente onde o parsing a evitou.
Preço total e quantidade em colunas separadas, unitário derivado. Carimbo do relógio
ancorado. E o nome honesto: "menor pedido visível", nunca "preço de venda".

### Análise (console)

- [x] **ANAL-01**: "Vale quanto agora": mínimo e mediana dos pedidos visíveis por item da watchlist, sempre com contagem de evidência e recência — nomeado honestamente ("menor pedido visível", nunca "preço de venda")
- [x] **ANAL-02**: Com o mercado aberto, linhas abaixo da mediana histórica são destacadas no console
- [x] **ANAL-03**: Tendência por item (direção via regressão stdlib), explícita sobre o tamanho da janela de dados que a sustenta
- [ ] **ANAL-04**: Margem de craft: receitas no `config.toml`, margem produto vs componentes, com staleness de cada componente visível

## v2 Requirements

Adiado. Registrado, fora do roadmap atual.

### WhatsApp

- **WAPP-01**: Comando `/preco <item>` responde com as estatísticas do item (decisão do usuário: console-only na v1)
- **WAPP-02**: Alerta de oportunidade via WhatsApp quando um item da watchlist aparece abaixo do limiar

## Out of Scope

Excluído explicitamente. Documentado para impedir retorno silencioso.

| Feature | Reason |
|---------|--------|
| Paginação, refresh ou busca automática no mercado | Exige enviar input ao jogo — violação estrutural da restrição fundadora; FIRE-01 torna impossível, não só proibido |
| Ler o "preço médio" do jogo como fonte primária | Estatística fraca (média de lotes ativos, não ponderada, não é venda); as linhas visíveis dão mínimo/mediana melhores |
| Histórico de VENDAS | Invisível ao cliente — só pedidos visíveis existem; as métricas carregam isso no nome |
| Varredura do mercado inteiro | A captura é passiva: só existe o que o usuário colocou na tela |

> A entrada que excluía a leitura de nomes por OCR saiu desta tabela em 2026-08-29. Ela não foi apagada: o argumento inteiro, e o que o derrubou, está em "Por que o OCR de nomes voltou ao escopo", na seção Leitura. Uma exclusão que cai também não pode cair em silêncio.

## Traceability

Preenchida na criação do roadmap (2026-08-27).

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIRE-01 | Phase 1 | Complete |
| FUND-01 | Phase 1 | Complete |
| FUND-02 | Phase 1 | Complete |
| FUND-03 | Phase 1 | Complete |
| DETC-01 | Phase 1 | Complete |
| DETC-02 | Phase 4 | Complete |
| LEIT-01 | Phase 2 | Complete |
| LEIT-02 | Phase 2 | Complete |
| LEIT-03 | Phase 2 | Complete |
| LEIT-04 | Phase 4 | Complete |
| LEIT-05 | Phase 2 | Complete |
| PERS-01 | Phase 3 | Complete |
| PERS-02 | Phase 3 | Complete |
| PERS-03 | Phase 3 | Complete |
| ANAL-01 | Phase 4 | Complete |
| ANAL-02 | Phase 4 | Complete |
| ANAL-03 | Phase 4 | Complete |
| ANAL-04 | Phase 4 | Pending |

**Coverage:**

- v1 requirements: 18 total (a contagem "16" da definição inicial estava errada — a recontagem na criação do roadmap deu 17; LEIT-05 entrou em 2026-08-29)
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-27*
*Last updated: 2026-08-27 after roadmap creation (traceability filled)*
