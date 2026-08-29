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
- [ ] **DETC-02**: Modo `--mercado` separado — vigiar mercado não degrada nem compete com o modo party (o usuário roda duas instâncias; uma terceira invocação é normal)

### Leitura

- [ ] **LEIT-01**: Itens da watchlist (`config.toml`) reconhecidos nas linhas visíveis por template de conjunto fechado
- [ ] **LEIT-02**: Preços e quantidades lidos por template-por-dígito com falha FECHADA: frame ilegível é descartado, preço nunca é inventado
- [ ] **LEIT-03**: Página só é aceita quando dois frames consecutivos concordam nas linhas PARSEADAS (nunca em pixels — frames bit a bit idênticos são o sinal de captura congelada)
- [ ] **LEIT-04**: Console mostra ao vivo páginas lidas/perdidas e último item reconhecido; resumo final conta as duas metades ("li 7, perdi 3")

### Persistência

- [ ] **PERS-01**: Observações gravadas como snapshots com carimbo do relógio ancorado, em SQLite

> **CORRIGIDO PELO USUÁRIO (2026-08-28): o mercado lê SEMPRE do Yazalaque, nunca da
> Faerlina.** A redação original dizia "compartilhável entre as duas instâncias" e usava a
> escrita concorrente como justificativa do SQLite. Isso estava errado: há **um único
> escritor**. As duas instâncias de party seguem existindo (é a razão da AGEN-07), mas
> nenhuma delas escreve dado de mercado.
>
> **O SQLite continua, por outros três motivos, e cada um sozinho já basta:** a dedup da
> PERS-02 em CSV exigiria reler o arquivo inteiro a cada escrita (custo linear que cresce
> com o histórico) contra um índice `UNIQUE` de custo constante; as consultas de ANAL-01 a
> ANAL-03 rodam a cada tick com o mercado aberto e em CSV seriam um reparse completo; e um
> append de CSV interrompido no meio trunca a última linha e corrompe o arquivo em silêncio
> — a classe de falha que a Fase 1 inteira combateu.
>
> **WAL + `busy_timeout` ficam mesmo assim**, rebaixados de exigência de desenho a seguro
> barato: custam duas linhas e protegem do usuário abrir `--mercado` duas vezes sem querer,
> ou de um processo velho não ter morrido. O que muda é que deixaram de ser o motivo da
> escolha.
- [ ] **PERS-02**: Revisitar uma página não duplica observações (dedup por chave de conteúdo na inserção, `INSERT OR IGNORE`)
- [ ] **PERS-03**: Falha de banco desliga só a feature de mercado e avisa — nunca derruba o núcleo de alertas

### Análise (console)

- [ ] **ANAL-01**: "Vale quanto agora": mínimo e mediana dos pedidos visíveis por item da watchlist, sempre com contagem de evidência e recência — nomeado honestamente ("menor pedido visível", nunca "preço de venda")
- [ ] **ANAL-02**: Com o mercado aberto, linhas abaixo da mediana histórica são destacadas no console
- [ ] **ANAL-03**: Tendência por item (direção via regressão stdlib), explícita sobre o tamanho da janela de dados que a sustenta
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
| OCR aberto para nomes de item | A watchlist é conjunto fechado — template matching, a decisão já validada do v1 (`identidade.py`) |
| Histórico de VENDAS | Invisível ao cliente — só pedidos visíveis existem; as métricas carregam isso no nome |
| Varredura do mercado inteiro | A captura é passiva: só existe o que o usuário colocou na tela |

## Traceability

Preenchida na criação do roadmap (2026-08-27).

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIRE-01 | Phase 1 | Complete |
| FUND-01 | Phase 1 | Complete |
| FUND-02 | Phase 1 | Complete |
| FUND-03 | Phase 1 | Complete |
| DETC-01 | Phase 1 | Complete |
| DETC-02 | Phase 4 | Pending |
| LEIT-01 | Phase 2 | Pending |
| LEIT-02 | Phase 2 | Pending |
| LEIT-03 | Phase 2 | Pending |
| LEIT-04 | Phase 4 | Pending |
| PERS-01 | Phase 3 | Pending |
| PERS-02 | Phase 3 | Pending |
| PERS-03 | Phase 3 | Pending |
| ANAL-01 | Phase 4 | Pending |
| ANAL-02 | Phase 4 | Pending |
| ANAL-03 | Phase 4 | Pending |
| ANAL-04 | Phase 4 | Pending |

**Coverage:**

- v1 requirements: 17 total (a contagem "16" da definição inicial estava errada — recontado na criação do roadmap)
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-08-27*
*Last updated: 2026-08-27 after roadmap creation (traceability filled)*
