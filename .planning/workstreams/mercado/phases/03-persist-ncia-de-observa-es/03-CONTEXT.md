# Phase 3: Persistência de observações - Context

**Gathered:** 2026-08-30
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — 4 áreas, 16 decisões, todas aceitas pelo usuário

> **ESTE CONTEXTO NASCEU DEPOIS DA FASE 2, E ISSO MUDA O QUE A FASE 3 CONSOME.** O ROADMAP
> dizia que a Fase 3 "paraleliza com a Fase 2 — só depende do formato da página aceita". Na
> prática ela veio depois, e ganhou com isso: o formato da página aceita hoje é conhecido e
> medido, não suposto. Em particular, a Fase 2 já escreve um CSV próprio (o catálogo de
> nomes) e já calcula um campo (o resíduo do cruzamento) cuja persistência ela deixou
> explicitamente para esta fase decidir.

<domain>
## Phase Boundary

Cada página aceita pela Fase 2 vira linhas num arquivo CSV que o usuário abre e lê — sem
duplicar, sem adivinhar, e sem jamais derrubar o núcleo de alertas de party.

Ela NÃO analisa nada (mínimo, mediana, tendência e margem de craft são ANAL-*, Fase 4), NÃO
desenha console (LEIT-04, Fase 4), NÃO tem modo de invocação próprio (DETC-02, Fase 4) e NÃO
mexe na leitura (Fase 2, fechada em 8 planos).

Requisitos: PERS-01 (linhas com carimbo ancorado, legível a olho e importável no Sheets),
PERS-02 (dedup por chave de conteúdo, conferida em memória antes de escrever), PERS-03
(falha de escrita desliga só o mercado e avisa alto — nunca derruba os alertas).

</domain>

<decisions>
## Implementation Decisions

### As colunas do CSV

- **O RESÍDUO DO CRUZAMENTO entra como coluna própria.** A Fase 2 o calcula em
  `LinhaLida.residuo_do_cruzamento` e registrou por escrito que a decisão de persistir é
  desta fase. Ele é a **única pista independente** de que uma leitura de número pode estar
  errada — a guarda que o consumiria foi medida e REPROVOU (fechamento 0,6525 contra 0,99
  exigido; detecção 0,0164 contra 0,90), então o resíduo virou observação em vez de gate.
  Jogá-lo fora perderia informação que já custou uma wave inteira para existir.
- **O UNITÁRIO DERIVADO NÃO vira coluna.** Total e quantidade bastam, e o critério 1 da fase
  exige "unitário derivado, nunca confundido". Uma coluna derivada dentro do arquivo convida
  alguém a tratá-la como dado — e o unitário EXIBIDO pelo jogo é arredondado a 2 casas
  (`40,00 ÷ 48` aparece como `0,83`), medido na Fase 1. Reconstruir o total a partir dele
  devolve um número que nunca existiu.
- **O NOME LEGÍVEL e a CHAVE DA SÉRIE vão os dois.** O nome é o que o usuário lê; a chave é o
  que agrupa. Só o nome perde o agrupamento quando o OCR oscila; só a chave é ilegível — e
  este arquivo existe para ser lido a olho nu e entregue a outra IA.
- **Só o CARIMBO DE TEMPO como proveniência — nada de gravação ou frame.** Eles são artefatos
  de replay: no farm ao vivo não existe "frame 78". Persistir campo que só tem valor em
  bancada é convidar a confusão entre teste e produção.

### O que é "a mesma observação"

- **A chave de dedup é `série + total + quantidade`.** É o que identifica um anúncio. **Sem o
  tempo**, deliberadamente: incluí-lo tornaria a dedup vácua, porque cada tick teria carimbo
  diferente e toda observação seria "nova".
- **O mesmo anúncio visto em dias diferentes é UMA linha, com a data da PRIMEIRA vez.** O
  usuário quer saber que o anúncio existe e por quanto — não quantas vezes olhou para ele.
  A alternativa (uma linha por dia) daria série temporal ao custo de inflar o arquivo com
  repetição do mesmo fato.
- **As chaves são carregadas EM MEMÓRIA no arranque, do próprio CSV.** Há **um único
  escritor** — o mercado lê sempre do Yazalaque, corrigido pelo usuário em 2026-08-28 — e o
  volume é de milhares de linhas, não milhões. Foi essa correção que derrubou duas das três
  justificativas originais do SQLite.
- **Chave igual com conteúdo diferente é impossível por construção**, porque a chave É o
  conteúdo. Se acontecer, é bug — e o aviso sai ALTO em vez de escolher um dos dois.

### O arquivo

- **UM arquivo só, que cresce.** Milhares de linhas por ano; o Sheets aguenta com folga, e um
  arquivo é o que o usuário abre sem ter que pensar em qual. Rotação seria complexidade a
  serviço de um problema que não existe neste volume.
- **Mora em `.mercado/`**, ao lado do `catalogo-de-nomes.csv` que a Fase 2 já escreve. Uma
  pasta, dois arquivos com papéis distintos: o catálogo é o vocabulário; este é o registro.
- **O CABEÇALHO é escrito UMA VEZ, na criação, e CONFERIDO na abertura.**
- **O cabeçalho é CONTRATO: se o do disco divergir do esperado, a feature DESLIGA ALTO** em
  vez de escrever desalinhado. Migração automática sobre um arquivo que o usuário edita à mão
  e importa no Sheets é como se corrompe dado calado.

### Falha

- **"Desligar alto" é: aviso no console E no log, a feature de mercado para, e os alertas de
  party continuam chegando.** É o `PERS-03` literal, e é a razão de a fase existir separada.
- **A linha truncada é detectada na LEITURA do arranque**, por contagem de campos — descarta
  só ela, com aviso, e nunca trata o arquivo inteiro como corrompido. Mesma família do
  FUND-01: dado parcial não pode virar dado plausível.
- **Escrita por APPEND com `flush` linha a linha.** Escrita atômica do arquivo inteiro
  (`os.replace`) é o padrão certo para o `calibration.json`, que é pequeno e reescrito por
  inteiro — aqui perderia a sessão toda num corte de energia. São problemas diferentes.
- **O carimbo usa o RELÓGIO ANCORADO que o projeto já tem**, nunca `datetime.now()` solto.

### Claude's Discretion

- Nomes exatos das colunas e a ordem delas, desde que legíveis a olho e coerentes com o que
  o resto do projeto já chama pelos mesmos nomes.
- Forma interna do índice de chaves em memória.
- Como o aviso alto é formatado, desde que apareça no console E no log.

</decisions>

<code_context>
## Existing Code Insights

### O que a Fase 2 entrega, e que esta fase consome

- **`PaginaAceita`** — o produto do estabilizador em `l2scanner/mercado_pagina.py`. Só nasce
  quando dois frames consecutivos concordam nas linhas PARSEADAS, com no mínimo **7 posições
  aceitas em ambos** (`mercado_minimo_de_linhas_comparadas`, medido).
- **`LinhaLida`** em `l2scanner/mercado_leitura.py` — carrega nome, chave da série, total,
  quantidade e **`residuo_do_cruzamento`**. O unitário é lido para calcular o resíduo e
  **nunca guardado como preço**.
- **`l2scanner/mercado_catalogo.py`** — o `Catalogo`, com escrita atômica por `os.replace`,
  leitura defensiva linha a linha e separador `;` pelo módulo `csv`. **É o analog mais
  próximo do que esta fase escreve** — mesmo formato, papel diferente.
- **`.mercado/`** já existe e já está no `.gitignore`.

### Números medidos que dimensionam esta fase

- Replay do censo: **478 ticks com painel aberto, 151 páginas aceitas, 39 séries distintas**.
  É a ordem de grandeza do volume real.
- A guarda de cruzamento está **DESLIGADA** (`mercado_tolerancia_do_cruzamento = None`) — o
  resíduo é observação, não veredito.

### Padrões da casa

- **Falha fechada**: dado ilegível é descartado, nunca interpretado.
- **Degradar, avisar alto, e deixar o scanner subir** (`montar_despachante`, `ocr.py`).
- **Um número que caiu precisa dizer que caiu** — refutações ficam registradas no fonte ao
  lado do que as substituiu.
- **Nada de constante mágica** — limiar mora no `calibration.json`, produzido por ferramenta
  que mede.

### Integration Points

- **NÃO tocar** `l2scanner/rastreador.py` nem o gate de brilho da barra própria em
  `l2scanner/visao.py` — acoplar mercado ao detector de morte é a manobra do incidente 27x.
- **FIRE-01** continua valendo: nenhuma biblioteca de síntese de input na árvore.
- O consumidor deste CSV é a Fase 4 (ANAL-*), e o usuário — que o abre no editor, importa no
  Sheets, e entrega a outra IA.

</code_context>

<specifics>
## Specific Ideas

- **Separador `;`, e o motivo é travado:** a exibição usa padrão brasileiro com vírgula
  decimal (`62,00`), e um CSV separado por vírgula colapsaria tudo numa coluna no Sheets.
- **Preços como inteiros em centésimos** — nunca float. `1139` é `11,39`.
- O critério 2 exige **importação REAL no Google Sheets**, não presumida. É portão humano.
- A Fase 2 deixou **duas conferências humanas** pendentes que NÃO bloqueiam esta fase: o OCR
  real dentro do tick, e o congelamento provocado.
- **Borda aceita pelo usuário em 2026-08-30:** numa captura travada, UMA página é aceita
  antes de o congelamento disparar (o acordo fecha com 2 frames, o congelamento exige 3). O
  dado é o último frame vivo — verdadeiro, só velho — e **a dedup desta fase é o que impede
  de virar linha duplicada**. Isso é dependência real: registrado em `WINDOWS.md`.
- **FLAKE conhecido:** `tests/test_agenda.py:1141` levanta `KeyboardInterrupt` de propósito e
  às vezes derruba a sessão do pytest. **Abortar não é falhar.** Estado verde de referência:
  **2605 passed, 2 skipped** sem esse arquivo, e **144 passed** só com ele.
- O pytest roda no **Python GLOBAL**, não no `.venv`.

</specifics>

<deferred>
## Deferred Ideas

- **Série temporal por dia** — o mesmo anúncio visto em dias diferentes vira uma linha só.
  Se um dia a pergunta virar "como o preço deste item andou", isso muda, e a decisão está
  registrada aqui para quem for reabri-la.
- **Rotação de arquivo** (por mês ou por ano) — desnecessária neste volume.
- **Exportar/importar de volta** — o arquivo é de mão única por ora.
- **Persistir os motivos de descarte** — a contagem "li N, perdi M" é da Fase 4; as linhas
  descartadas não entram no CSV, por decisão da Fase 2.
- **A fusão `B-grade Gemstone` × `C-grade Gemstone`** (0,9375, letra de grade) continua
  aberta desde a Fase 2 — ela produziria duas séries fundidas neste CSV, e o registro fica
  em `WINDOWS.md`.

</deferred>
