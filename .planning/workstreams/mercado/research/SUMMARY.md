# Project Research Summary — Workstream Mercado (v1-mercado)

> **SUPERSEDIDO EM PARTE (2026-08-29): a persistência não é mais SQLite, é CSV.**
> Esta pesquisa recomendou `sqlite3` com WAL, e a recomendação valia com o que se sabia na
> época. Dois dos três motivos caíram depois (o usuário corrigiu que só o Yazalaque escreve,
> o que eliminou a concorrência e enfraqueceu a dedup indexada), e o terceiro perdeu para um
> caso de uso que não estava na mesa: ele quer ler o dado a olho nu, importar no Google
> Sheets e entregar para outra IA analisar. Ver REQUIREMENTS.md, seção Persistência, para o
> raciocínio completo. O resto desta pesquisa segue válido — em especial o spike de campo,
> a técnica de template matching e os pitfalls, que a Fase 1 confirmou em campo.

**Project:** L2 Party Scanner — captura passiva de preços do World Exchange
**Domain:** Leitura de tela de UI de jogo (dígitos de fonte fixa) + série temporal local de preços
**Researched:** 2026-08-27
**Confidence:** MEDIUM-HIGH — integração e stack HIGH (verificados no repo e na máquina-alvo); tudo específico da UI do XM Essence UNVERIFIED até gravações reais

## Executive Summary

Este milestone responde "quanto vale um item AGORA e como ele se comporta ao longo do tempo" lendo passivamente a janela do World Exchange — sem input, sem API, sem pacotes. FEATURES respondeu a pergunta de ouro do milestone: **o cliente NÃO tem histórico/gráfico de preços**; existe apenas um "preço médio" nativo fraco (média dos preços de lotes ativos, sem ponderar quantidade — código Mobius lido diretamente). Portanto o milestone se divide: "vale quanto AGORA" sai no v1 raspando as linhas visíveis (min/mediana dos pedidos, melhor que o número do jogo); tendência/histórico é diferencial adiável que exige acumulação local por semanas. Entrega no console em v1; comandos WhatsApp de mercado ficam adiados (decisão do usuário).

A abordagem recomendada é conservadora e inteiramente reaproveitada: modo `--mercado` separado no mesmo binário (precedente `--so-agenda`), template-por-dígito com `cv2.matchTemplate` (a técnica já medida em `identidade.py`: 1.000 acerto vs 0.454 erro), estabilizador de página com acordo de 2 frames sobre LINHAS PARSEADAS, e `sqlite3` stdlib com WAL num módulo-registro dedicado (`mercado_registro.py`, padrão `loot.py`). **Zero dependências novas** — verificado empiricamente: tudo já está na árvore ou na stdlib.

O risco dominante é duplo. Primeiro, **todas as afirmações sobre a UI do XM são UNVERIFIED** — os quatro pesquisadores convergiram independentemente: a primeira fase obrigatória é um spike de campo com frames reais gravados da janela do World Exchange (separador de milhar, alinhamento, linhas visíveis, preço total vs unitário, opacidade do painel). Segundo, o pior falso positivo da história do v1 (painel de mercado lido como morte 27x) é *literalmente convidado* por este milestone — a detecção do painel precisa ser UM sinal compartilhado entre o leitor de mercado e o detector de morte. E antes de qualquer spike: **corrigir o `imwrite` sem checagem de retorno no `gravador.py`** — o gravador é a ferramenta de evidência do spike e hoje conta frames que nunca verificou terem sido escritos.

## Key Findings

### Recommended Stack

Zero dependências novas; `requirements.txt` não muda. Detalhes em STACK.md.

**Core technologies:**
- `cv2.matchTemplate` (já instalado): classificação de dígitos (10-12 glifos, separador incluso como glifo) e de nomes da watchlist — classificação fechada com limiar falha *fechado* (descarta); OCR falha *aberto* (inventa preço plausível)
- `sqlite3` stdlib (SQLite 3.49.1 verificado no venv): série temporal em `mercado.db` com WAL + `busy_timeout` — duas instâncias escrevem na mesma pasta
- `statistics` stdlib: mediana/percentis/tendência em Python — **o build do sqlite3 NÃO tem `median()`/`percentile_cont()` (verificado empiricamente: `no such function`)**; `SELECT` da janela → `statistics.median`
- numpy (já instalado): segmentação de glifos por projeção de colunas; sparkline Unicode sobre o console ANSI existente (que é stdlib puro, não rich)
- **Discrepância a registrar:** o venv real é **Python 3.12.10**, não 3.13 como o CLAUDE.md afirma. Nada nesta pesquisa exige 3.13; não há razão para upgrade neste milestone.

### Expected Features

**Must have (table stakes):**
- Detecção "janela de mercado aberta" (âncora de template) — gatilho de tudo E sinal de oclusão para o detector de morte
- Captura oportunista das linhas visíveis (o humano navega, o scanner lê — padrão universal da categoria view-only)
- Watchlist em `config.toml` + identificação por matching fechado contra ela
- Leitura de preço/quantidade (dígitos + separador) com acordo de 2 frames
- Persistência local com timestamp + dedupe; staleness explícita em toda saída ("visto às 14:32")

**Should have (competitive):**
- Alerta de "preço bom" via Chatwoot (v1.x, após leitura provar zero falso positivo)
- Dedupe entre as 2 instâncias (padrão AGEN-07)

**Defer (v2+):**
- Estatísticas de tendência/histórico (precisa de semanas de dados), margem de craft, leitura do preço médio nativo como sinal complementar
- **Anti-features permanentes:** varredura automática/paginar sozinho (exige input — viola a constraint inegociável), OCR aberto de qualquer item, previsão/ML

### Architecture Approach

Modo `--mercado` separado no mesmo binário — terceira invocação, party path intocado byte a byte. Camadas espelham exatamente as do v1: extração pura → tracker com memória → sessão com contadores → registro dono do disco. Reusa `JanelaSource`, classificador de saúde de frame, `Gravador`/`ReplaySource`, calibração com chaves opcionais via `.get` (padrão `banner_manutencao`).

**Major components:**
1. `mercado_visao.py` (NEW, puro) — `mercado_aberto()` (âncora positiva) + `ler_pagina()`; jamais estender o gate de brilho da barra própria
2. `mercado.py` (NEW, tracker puro) — `EstabilizadorDePagina`: aceita página só com 2 frames consecutivos concordando em linhas PARSEADAS (nunca hash de pixels — cenário atrás do texto muda; frames idênticos = captura congelada)
3. `mercado_registro.py` (NEW) — único dono do SQLite; WAL, `INSERT OR IGNORE` em chave de conteúdo, falha tri-estado visível (padrão `loot.py`), firewall de exceção: falha de DB desliga o mercado ruidosamente, nunca derruba o scanner
4. `__main__.py`/`calibracao.py`/`calibrar.py` (MODIFIED) — flag, laço, bloco de status com contadores de honestidade (`paginas: N aceitas · N perdidas · N ilegiveis`)

### Critical Pitfalls

1. **Painel de mercado = pior inimigo histórico (incidente 27x)** — detecção do painel é UM sinal compartilhado: início da leitura de mercado E supressão/oclusão para o detector de morte. Construir PRIMEIRO; verificar contra a gravação do incidente 27x.
2. **Preço mal-lido é plausível-mas-errado e o DB o torna permanente** — acordo de 2 frames obrigatório; validação de agrupamento (grupos de 3 dígitos); abster, nunca reparar; auditoria de outliers potência-de-10 na análise.
3. **`gravador.py` ainda não checa o retorno de `cv2.imwrite`** — corrigir ANTES do spike; contadores contam resultados confirmados, nunca tentativas; "snapshots hoje" é `SELECT COUNT(*)`.
4. **Schema evento-de-listing é porta sem volta** — armazenar como snapshot + observações (dedup vira decisão de análise com informação completa); guardar `price_total` + `quantity` separados (confusão total/unitário corrompe a série por 1000x); `PRAGMA user_version` + escada de migração desde o dia 1.
5. **Pressão por automação** — dado esparso gera "só um F10 por hora"; pré-recusar em Out of Scope AGORA + teste que falha CI se biblioteca de input entrar na árvore.
6. **Alinhamento à direita, separadores, margem fina entre dígitos** — ancorar no canto direito da célula; separador é glifo de primeira classe; matriz de confusão de dígitos medida na calibração; recusar leitura se o tamanho da janela mudar (degradar para OFF, nunca para silenciosamente pior).

## Implications for Roadmap

### Phase 0 (embutida na definição do roadmap): Firewall de escopo
**Rationale:** a pressão por automação começa no primeiro gráfico esparso; custa minutos agora.
**Delivers:** entradas Out of Scope pré-recusando auto-refresh/auto-open/auto-buy; teste grep de bibliotecas de input na árvore de dependências.

### Phase 1: Spike de campo + detecção do painel + calibração
**Rationale:** convergência unânime dos 4 pesquisadores — toda afirmação sobre a UI do XM é UNVERIFIED; gravações reais são o gate de tudo. Corrigir `gravador.py` (imwrite) ANTES de gravar.
**Delivers:** fix do gravador; gravações reais (fechado/aberto/scroll/página completa); respostas empíricas (separador, decimais, linhas visíveis, total vs unitário, alinhamento, opacidade, moeda, idade de listing); chaves de calibração (âncora + grade) opcionais via `.get`; templates de dígito + nomes-como-renderizados com matriz de confusão e limiar calibrado contra linhas negativas reais; `mercado_aberto()` medido contra fixtures; sinal compartilhado com o detector de morte verificado no replay do incidente 27x.
**Avoids:** Pitfalls 1, 3, 5, 6, 7, 14.

### Phase 2: Leitura de página (dígitos + watchlist) e estabilizador
**Rationale:** o dado central; tudo roda contra as fixtures da Fase 1, sem abrir o jogo.
**Delivers:** `ler_pagina()` (janela deslizante, âncora à direita, validação de agrupamento, abstenção); matching rejection-first contra a watchlist; `EstabilizadorDePagina` (2 frames, linhas parseadas); gate de completude de página; gating de custo por tick (âncora barata quando fechado; p95 medido).
**Avoids:** Pitfalls 2, 4, 7, 9, 15.

### Phase 3: Persistência (`mercado_registro.py`)
**Rationale:** o schema snapshot-céntrico é a decisão de mão única do milestone — impossível retrofit sem migração dolorosa. Pode andar em paralelo com a Fase 2 (só depende do shape de `PaginaAceita`).
**Delivers:** schema `snapshot` + `observation` (preço INTEGER, total/quantidade/unitário separados, NULL nunca adivinhado); WAL + `busy_timeout` + transação-por-snapshot + `INSERT OR IGNORE`; firewall de exceção; `user_version` + migração; teste de martelo com 2 processos; contadores verdade-do-DB.
**Avoids:** Pitfalls 6, 8, 13, 14.

### Phase 4: Sessão, laço `--mercado`, análise e console
**Rationale:** fiação final e a superfície de valor do v1 (console-only, por decisão do usuário).
**Delivers:** `SessaoDeMercado` + `ResultadoDoTickDeMercado`; laço + bloco de status + resumo final; consultas de análise (min/mediana via `statistics`, sparkline Unicode); métricas honestas ("menor pedido visível", nunca "preço"), toda saída com n e recência, sem interpolação; auditoria potência-de-10; harness de replay reproduzindo páginas e contadores.
**Avoids:** Pitfalls 10, 11; auditoria do 2.

### Phase Ordering Rationale

- Espinha de dependência da ARCHITECTURE: gravação → calibração → detecção/leitura → estabilizador → fiação, com registro em paralelo — cada passo testável sem o jogo (disciplina fixture-first fundadora do projeto).
- O spike de campo vem primeiro porque quatro pesquisas independentes o marcaram como gate: nada da UI do XM é verificável por busca (servidor privado sem documentação pública).
- O fix do gravador precede o spike porque as conclusões do spike serão construídas sobre as gravações — evidência não-verificada é o pesadelo documentado do projeto.
- O schema (F3) é decidido antes de dados existirem porque é irrecuperável depois.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** é ela própria a pesquisa — o spike responde as 6+ perguntas UNVERIFIED; nenhuma fase seguinte deve ser planejada em detalhe antes dos resultados.
- **Phase 2:** decisão template vs OCR para dígitos deve ser MEDIDA nas fixtures (esperado: template vence, como em `identidade.py`), não assumida.

Phases with standard patterns (skip research-phase):
- **Phase 3:** SQLite WAL/dedup/migração são semântica estabelecida, já detalhada em STACK/PITFALLS.
- **Phase 4:** espelha padrões existentes do repo (sessão, status, resumo); métricas e wording já especificados.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verificado empiricamente na máquina-alvo (venv 3.12.10, SQLite 3.49.1, ausência de median() testada ao vivo) + medições do próprio repo |
| Features | MEDIUM | Código Mobius lido diretamente (HIGH para bases Mobius); tudo específico do XM UNVERIFIED até os prints |
| Architecture | HIGH | Pontos de integração lidos dos módulos reais com file:line; especificidades da UI de mercado MEDIUM (sem frames gravados ainda) |
| Pitfalls | MEDIUM-HIGH | Baseado na história real do projeto (incidente 27x, imwrite) e semântica SQLite estabelecida; UI do XM UNVERIFIED |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **UI real do World Exchange no XM** (separador, decimais, linhas visíveis, total vs unitário, alinhamento, opacidade do painel, moeda, idade de listing, auto-refresh): resolvido pelo spike da Fase 1 com gravações reais — bloqueia planejamento detalhado das Fases 2-4.
- **Fonte de preço determinística?** Esperado sim (mesma engine dos nomes), mas a margem de matchTemplate para dígitos deve ser medida (matriz de confusão) — fallback documentado: upscale, depois WinRT OCR com validação estrutural.
- **Discrepância de docs:** CLAUDE.md diz Python 3.13; venv real é 3.12.10 — atualizar docs ou registrar; não bloqueia nada.
- **Variantes de encanto (+3 vs +4) na watchlist:** decidir explicitamente na Fase 1 (incluir região do glifo no template, ou declarar fora de escopo do v1) — não descobrir nos dados.

## Sources

### Primary (HIGH confidence)
- Verificação empírica na máquina-alvo (2026-08-27): venv Python 3.12.10, SQLite 3.49.1, `median()`/`percentile_cont()` ausentes, WAL/STRICT/math functions presentes
- Codebase real (`identidade.py`, `visao.py`, `sessao.py`, `loot.py`, `ocr.py`, `gravador.py`, `manutencao.py`, `__main__.py`, `calibracao.py`) — medições e padrões citados por file:line
- GitLab MobiusDevelopment/L2J_Mobius (branch Essence 07.3) — pacotes do World Exchange lidos diretamente

### Secondary (MEDIUM confidence)
- sqlite.org (percentile.html, lang_aggfunc.html, wal.html) — extensão percentile desligada por padrão; semântica WAL
- l2wiki.com / l2.wiki / l2central.info — mecânica oficial do World Trade, patch notes (3 decimais, separadores, preço médio na página principal)
- Addons WoW view-only (Auctionator PriceTracker, Market Tracker, Market Watcher) e price-checkers OCR de PoE2 — landscape da categoria
- PyImageSearch / docs OpenCV — template-por-dígito como técnica padrão

### Tertiary (LOW confidence / UNVERIFIED)
- Toda especificidade da UI do cliente XM Essence (l2xm.com sem documentação pública) — gated no spike da Fase 1
- Guias de jogador 4gameforum (2022)

---
*Research completed: 2026-08-27*
*Ready for roadmap: yes (Fase 1 = spike de campo obrigatório antes do planejamento detalhado das demais)*
