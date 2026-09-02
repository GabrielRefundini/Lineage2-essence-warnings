# Requisitos — v2-mercado

**Workstream:** mercado
**Milestone:** v2-mercado — a taxa de câmbio adena × XM Coin, e a assertividade da leitura
**Criado:** 2026-09-01, no fechamento do v1

> O v1-mercado fechou com **18/18**. Os requisitos dele estão em
> [milestones/v1-mercado-REQUIREMENTS.md](milestones/v1-mercado-REQUIREMENTS.md).

## Fase 5 — a aba Adena e a taxa de câmbio

- [x] **ADEN-01**: O `--mercado` reconhece a aba Adena e a lê, **sem perder** a leitura
      da aba de negociação. Hoje `calibration.json` guarda uma grade só e calibrar uma
      apagaria a outra — as duas passam a conviver, e a leitura escolhe pela grade que
      está na tela.
- [x] **ADEN-02**: O modelo de colunas da Adena é PRÓPRIO, não uma adaptação do de
      negociação. Ali o nome (`Auction List`) **carrega a quantidade**
      (`10,000,000 Adena`), não existe coluna de quantidade, e o unitário exibido é por
      cinco milhões. Ler com o modelo errado corromperia a série por um fator inteiro.
- [x] **ADEN-03**: Cada linha da Adena vira uma observação de TAXA no
      `.mercado/observacoes.csv` — `quantidade` = a adena, `total_em_centesimos` = o
      preço em XM. Nenhuma coluna nova, nenhum bump de `VERSAO_DO_ESQUEMA`: o unitário
      derivado em `Fraction` já dá XM por adena, exato.
- [x] **ADEN-04**: O console exibe a taxa na unidade que o usuário pensa — **XM por
      milhão de adena** —, dizendo que é derivada, com `n` e recência como todo número
      que sai na tela.

## Dívida carregada do v1 (melhoria, não regressão)

- [ ] **DEBT-01**: Assertividade do OCR de nome. Medido em 2026-09-01: 24 nomes contra
      29 palavras distintas, `Hunter's` em 13 deles. O discriminador certo é
      "esta palavra está no vocabulário conhecido?", e não similaridade de nome inteiro
      — `Armor` e `Weapon` são ambas conhecidas e nunca se corrigem uma na outra.
      Segunda direção já prevista e nunca construída: `mercado_templates_de_nome` existe
      no `calibration.json` e está `None`. Terceira REFUTADA antes de começar: mais
      escalas de OCR não resolve, porque nas falhas as duas CONCORDARAM no erro.
- [ ] **DEBT-02**: A cadeia de import `mercado_catalogo` → `config` → `notificador` →
      `rastreador`. **Fechou o v1 DECLARADA ABERTA, não silenciada** — o CLI recusou
      suprimi-la e o marcador manual não é lido pelo scanner.
- [ ] **DEBT-03**: A moldura do destaque tem 153 colunas e rola para fora do console.
      Mexer nela mexe na moldura compartilhada com os alertas de morte da party.
- [ ] **DEBT-04**: `Hunteds Tunic` × `Hunter's Tunic` (0,8889) cai na faixa cinzenta e
      é descartado. Mesmo item, o OCR erra o apóstrofo.
- [ ] **DEBT-05**: Quatro séries partidas por variação de OCR (`Stockings` ×
      `St«kings`, 0,9268). São sobra de antes do conserto; dado novo não se parte mais.
      A ferramenta de fusão não as junta de propósito — só funde com `nome_exibido`
      idêntico.

- [ ] **DEBT-06**: A guarda de paridade do ciano avisa TARDE, e DUAS frases no
      repositorio afirmam o contrario. Medido pelo verificador: `cortar_glifos`
      (os treze arrastos) roda em `calibrar_mercado.py:2586`;
      `conferir_a_paridade_do_ciano` so em 2491, dentro de `_gravar_os_glifos`,
      chamado em 2595. Ela impede a ESCRITA, nao a sessao. Mas o comentario da
      linha 2489 diz *"tem de custar uma mensagem, e nao uma sessao de farm"* e o
      doc de debug diz *"o que impede o esforco jogado fora"* — as duas sao
      FALSAS hoje, e custaram ao usuario TRES rodadas completas em 2026-09-01.
      **Pela regra da casa, ou as frases se corrigem ou a guarda sobe.** O
      conserto barato existe: `anel_do_zero_esta_partido` ja e pura sobre UM
      molde, entao da para conferir no primeiro `0` cortado, dentro do laco.
- [ ] **DEBT-07**: `tests/test_mercado_adena_pagina.py:350` — `_vencedor_medido`
      REIMPLEMENTA `_casamento_do_layout` dentro do teste (limiar, `max`, empate,
      `None`). `test_o_vencedor_por_banda` mede a copia, nao a producao. Contido
      (a funcao real e chamada em `TestOPortaoESCOLHEEmVezDeSoRecusar` e no ponta
      a ponta), por isso e aviso e nao lacuna. Conserto de uma linha: trocar o
      corpo por `leitor._casamento_do_layout(...)`. **E a decima aparicao do
      padrao desta sessao, numa variante nova: o teste que mede a propria copia.**
- [ ] **DEBT-08**: O `13588` na NEGOCIACAO. Mesmo defeito de digito do ciano, no
      caminho principal — e la `mercado_tolerancia_do_cruzamento` e `None`, entao
      o cruzamento so OBSERVA. Com quantidade 1 o total e o unitario erram IGUAL,
      o cruzamento FECHA por cima e nada e anunciado. Foi assim que
      `+6 Hunter's Breastplate 43,88` (quantidade 1, residuo 0) entrou no CSV do
      usuario — 1 de 92 linhas. A falha-fechada por cor entregue hoje estanca as
      celulas cromaticas, mas os moldes acromaticos nao receberam o tratamento
      que a Adena recebeu.

## Restrições herdadas — valem no v2 inteiro

- **FIRE-01 continua valendo**: nenhuma biblioteca de síntese de input entra na árvore.
- **Nunca acoplar mercado ao detector de morte** (`rastreador.py`, gate de brilho da
  barra própria em `visao.py`) — a manobra do incidente 27x.
- **Não afrouxar** o corte de similaridade (0,8947), o piso (0,8837), a trava de
  dígitos (D-03), a trava por palavra (D-09) nem a letra de grade na assinatura.
- **Falha fechada**: dado ilegível é descartado, nunca interpretado.
- **Nada de constante mágica**: limiar mora no `calibration.json`, produzido por
  ferramenta que mede.
- **Um número que caiu precisa dizer que caiu** — refutações ficam no fonte.

## Rastreabilidade

| ID | Fase | Estado |
|---|---|---|
| ADEN-01 | Phase 5 | Complete |
| ADEN-02 | Phase 5 | Complete |
| ADEN-03 | Phase 5 | Complete |
| ADEN-04 | Phase 5 | Complete |
| DEBT-01 | TBD | Pending |
| DEBT-02 | TBD | Pending |
| DEBT-03 | TBD | Pending |
| DEBT-04 | TBD | Pending |
| DEBT-05 | TBD | Pending |
| DEBT-06 | TBD | Pending |
| DEBT-07 | TBD | Pending |
| DEBT-08 | TBD | Pending |
