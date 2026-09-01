# Requisitos — v1-dashboard

**Workstream:** dashboard
**Milestone:** v1-dashboard — o câmbio Adena → XM → BRL, ao vivo, no navegador local
**Criado:** 2026-09-01, a partir de `/gsd-explore`

> A fonte de dados é o `.mercado/observacoes.csv`, gravado pelo `--mercado` do workstream
> `mercado` (v2-mercado, Fase 5, ADEN-01..04 completos). Este workstream **não** coleta nada.

## Fase 1 — o câmbio em BRL, ao vivo

- [ ] **DASH-01**: O dashboard é uma superfície **somente-leitura** sobre o
      `.mercado/observacoes.csv`. Ele nunca escreve nesse arquivo, e a coleta não depende dele
      estar de pé. Lendo enquanto o scanner apenda, ele **não exibe linha parcial e não perde
      a série**: degrada para a última linha completa. Essa é uma divergência declarada da
      regra do terminador da Fase 3 do mercado — lá o contrato quebrado desliga a feature
      alto, aqui isso viraria cegueira a cada escrita —, e a divergência fica escrita no fonte.

- [ ] **DASH-02**: A taxa **XM → BRL é entrada manual** do usuário (hoje `1 XM = R$ 0,50`),
      editável na própria página e **persistida entre sessões**. Todo valor em R$ é derivado
      dela e é declarado na tela como *informado por você, em tal data* — nunca apresentado
      como medido. Sem taxa informada, a página mostra XM normalmente e diz que o R$ está
      indisponível: **nenhum valor padrão é chutado**.

- [ ] **DASH-03**: A história da taxa aparece como **linha do tempo com zoom** — das horas do
      dia até dias atrás — com **duas linhas sobrepostas**: menor pedido visível (o que você
      pagaria agora) e mediana `median_low` (o preço típico). Os números batem com os do
      console `--mercado` para o mesmo instante: mesma fonte, mesma conta, **sem um segundo
      parser do CSV**.

- [ ] **DASH-04**: O valor de **agora** fica em destaque: quanto vale 1 milhão de adena, em XM
      e em R$ — com `n` e **recência** ao lado, como todo número que sai na tela no
      `--mercado`. Com o scanner parado, o dashboard continua exibindo o último dado e diz de
      quando ele é; nunca afirma "agora" sobre um número velho.

- [ ] **DASH-05**: A visualização é um **componente de série genérico**, e a Adena é a
      primeira instância — não um caso especial no código. Instanciar uma segunda série
      (qualquer item da aba de negociação) não exige código de gráfico novo. O v1 só mostra
      Adena na tela; a generalidade é provada em teste.

- [ ] **DASH-06**: O dashboard sobe por **lançador próprio** (`dashboard.bat`), em processo
      separado. O caminho do `--mercado` fica **byte-idêntico** — nenhuma linha do modo mercado
      muda por causa desta fase —, e derrubar o dashboard não derruba a coleta da noite.

## Restrições herdadas — valem no workstream inteiro

- **FIRE-01 continua valendo**: nenhuma biblioteca de síntese de input entra na árvore.
- **Doutrina de zero-install**: dependência nova é decisão de pesquisa com justificativa, não
  um `pip install` de conveniência. Foi o que manteve o `rich` fora do console de mercado.
- **O dashboard nunca lê o `calibration.json`** nem toca em captura de tela.
- **Nunca acoplar ao detector de morte** (`rastreador.py`, `visao.py`).
- **Falha fechada**: dado incompleto é descartado, nunca interpretado.
- **Nada de constante mágica**, e **um número que caiu precisa dizer que caiu**.

## Rastreabilidade

| ID | Fase | Estado |
|---|---|---|
| DASH-01 | Phase 1 | Pending |
| DASH-02 | Phase 1 | Pending |
| DASH-03 | Phase 1 | Pending |
| DASH-04 | Phase 1 | Pending |
| DASH-05 | Phase 1 | Pending |
| DASH-06 | Phase 1 | Pending |
