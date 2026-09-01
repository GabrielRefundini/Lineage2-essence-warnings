# Requisitos — v2-mercado

**Workstream:** mercado
**Milestone:** v2-mercado — a taxa de câmbio adena × XM Coin, e a assertividade da leitura
**Criado:** 2026-09-01, no fechamento do v1

> O v1-mercado fechou com **18/18**. Os requisitos dele estão em
> [milestones/v1-mercado-REQUIREMENTS.md](milestones/v1-mercado-REQUIREMENTS.md).

## Fase 5 — a aba Adena e a taxa de câmbio

- [ ] **ADEN-01**: O `--mercado` reconhece a aba Adena e a lê, **sem perder** a leitura
      da aba de negociação. Hoje `calibration.json` guarda uma grade só e calibrar uma
      apagaria a outra — as duas passam a conviver, e a leitura escolhe pela grade que
      está na tela.
- [ ] **ADEN-02**: O modelo de colunas da Adena é PRÓPRIO, não uma adaptação do de
      negociação. Ali o nome (`Auction List`) **carrega a quantidade**
      (`10,000,000 Adena`), não existe coluna de quantidade, e o unitário exibido é por
      cinco milhões. Ler com o modelo errado corromperia a série por um fator inteiro.
- [ ] **ADEN-03**: Cada linha da Adena vira uma observação de TAXA no
      `.mercado/observacoes.csv` — `quantidade` = a adena, `total_em_centesimos` = o
      preço em XM. Nenhuma coluna nova, nenhum bump de `VERSAO_DO_ESQUEMA`: o unitário
      derivado em `Fraction` já dá XM por adena, exato.
- [ ] **ADEN-04**: O console exibe a taxa na unidade que o usuário pensa — **XM por
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
| ADEN-01 | Phase 5 | Pending |
| ADEN-02 | Phase 5 | Pending |
| ADEN-03 | Phase 5 | Pending |
| ADEN-04 | Phase 5 | Pending |
| DEBT-01 | TBD | Pending |
| DEBT-02 | TBD | Pending |
| DEBT-03 | TBD | Pending |
| DEBT-04 | TBD | Pending |
| DEBT-05 | TBD | Pending |
