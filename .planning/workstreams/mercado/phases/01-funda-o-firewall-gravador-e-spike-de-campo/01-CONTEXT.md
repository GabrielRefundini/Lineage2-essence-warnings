# Phase 1: Fundação — firewall, gravador e spike de campo - Context

**Gathered:** 2026-08-27
**Status:** Ready for planning
**Mode:** Discussão interativa (áreas 1-4) concluída via autonomous smart discuss

<domain>
## Phase Boundary

O usuário consegue produzir evidência de campo confiável do World Exchange, e dessa evidência saem a calibração, os templates e a detecção do painel — o sinal único que também protege o detector de morte. Requisitos: FIRE-01, FUND-01, FUND-02, FUND-03, DETC-01.

**Bloqueio externo estrutural:** só o USUÁRIO pode gravar as sessões do World Exchange (conta, cliente e servidor dele). Ordem obrigatória: fix do gravador (FUND-01) + firewall (FIRE-01) + roteiro → **PAUSA: usuário grava** → análise das gravações, calibração, templates e detecção do painel. Nenhuma fase seguinte deve ser planejada em detalhe antes das respostas do spike.

</domain>

<decisions>
## Implementation Decisions

### Roteiro das gravações do spike (FUND-02)
- Roteiro entregue como **checklist markdown** (`ROTEIRO-SPIKE.md` no diretório da fase): cada cenário numerado, com o rótulo exato de `--record` a usar e o que fazer na tela. O usuário segue com o arquivo aberto no segundo monitor.
- Cenários obrigatórios: mercado fechado, mercado aberto, com scroll, página cheia.
- Cenários extras decididos: **tooltip por cima das linhas** (gêmeo do incidente 27x — snapshot parcial confiante); **marcação de alvo/vida do próprio char sobrepondo levemente o painel** (acontece de verdade, informado pelo usuário); **mercado aberto durante o farm com party window visível** (caso real de uso + material para o sinal compartilhado); **scroll no meio do movimento** (material para o estabilizador da Fase 2 rejeitar página em transição).
- **Fato de campo (usuário, 2026-08-27): o inventário NUNCA sobrepõe o mercado — abrir o inventário FECHA o painel do mercado.** Outras janelas do menu podem sobrepor em edge cases raros → registrado como ideia deferida, não entra no roteiro do v1.
- **Uma sessão por cenário**, com rótulo fixo definido no checklist (ex.: `--record mercado-aberto`, `--record mercado-tooltip`). Pastas pequenas e nomeadas viram fixtures estáveis que os testes citam pelo nome.
- Respostas das perguntas de campo: **Claude analisa os frames gravados e propõe as respostas em `SPIKE-RESPOSTAS.md`** no diretório da fase, citando frames específicos como evidência; o usuário valida ou corrige. Perguntas mínimas: linhas por página, separador de milhar, moeda, colunas, preço total vs unitário, onde fica o preço médio embutido, confirmação da renderização do encanto.

### Variantes de encanto (+3 vs +4) na watchlist
- **Variantes importam e entram no v1** — itens encantados estão entre os que o usuário quer preçar; misturar +3 com +4 corromperia a série.
- **Renderização confirmada pelo usuário: o encanto aparece como prefixo de texto no nome — `+3 <nome do item>`.** O spike só valida com frames o que já foi confirmado.
- Template único: **nome-como-renderizado incluindo o prefixo `+N` no recorte** — `+3 Bota X` e `+4 Bota X` são dois templates distintos. Mesma técnica medida do `identidade.py`, zero lógica nova de dois passos.
- Semântica da watchlist: **só o que está listado explicitamente** no `config.toml`. Um `+5` não listado é ignorado como qualquer item fora da watchlist. Conjunto fechado puro; adicionar variante = editar config.
- Análise: **cada variante é uma série independente de ponta a ponta** (leitura, banco, console) — mínimo, mediana e tendência separados. Nenhuma visão agregada.

### Ferramenta de calibração do mercado (FUND-03)
- **Estender o fluxo de calibração existente com um modo mercado** — nasce um `calibrar-mercado.bat` seguindo o precedente `calibrar.bat` / `calibrar-solo.bat`, reusando o código de calibração atual.
- Interação no **mesmo estilo da ferramenta atual**: seleção de regiões sobre um frame com confirmação visual.
- Fonte do frame: **frame GRAVADO do spike (replay)**, nunca captura ao vivo — calibra sobre a evidência real e permite recalibrar sem abrir o jogo (disciplina fixture-first).
- Templates de dígito e de nomes: **cortados da gravação pela própria ferramenta, com confirmação visual e matriz de confusão medida** contra linhas negativas reais. Critério: nunca editar JSON à mão.
- Chaves novas em `calibration.json` são opcionais via `.get` (padrão `banner_manutencao`) — instalações sem calibração de mercado continuam funcionando.

### Firewall FIRE-01
- Banlist **ampla e nomeada**: `pyautogui`, `pydirectinput`, `pynput`, `keyboard`, `mouse`, `autoit`/wrappers de AHK — pré-recusa qualquer síntese de input, não só o exemplo do CLAUDE.md.
- Mecanismo: **teste pytest que varre a árvore INSTALADA do venv** (`importlib.metadata.distributions`) além do `requirements.txt` — pega dependência transitiva que um grep no requirements não vê.
- Vive em **`tests/test_firewall_escopo.py` na suíte normal** — roda em todo `pytest`, sem infra nova de CI.
- Mensagem de falha **explica o porquê**: cita a constraint fundadora ("o scanner é somente leitura, nunca envia input ao jogo") e aponta a tabela Out of Scope de REQUIREMENTS.md.

### Claude's Discretion
- Detalhes internos do fix do `imwrite` (FUND-01): checagem de retorno + erro alto e visível; forma exata da mensagem/exceção a critério de Claude, desde que o contador só conte escritas confirmadas.
- Implementação da âncora/template do painel (DETC-01): âncora positiva própria do mercado, jamais estender o gate de brilho da barra própria (`visao.py`); verificada no replay da gravação do incidente 27x com ZERO alertas de morte.

</decisions>

<canonical_refs>
## Canonical Refs

- `.planning/workstreams/mercado/REQUIREMENTS.md` — 17 requisitos v1, Out of Scope (pré-recusas do firewall)
- `.planning/workstreams/mercado/ROADMAP.md` — critérios de sucesso da fase, bloqueio externo declarado
- `.planning/workstreams/mercado/research/SUMMARY.md` — síntese da pesquisa (spike gate, zero deps novas, sinal compartilhado)
- `.planning/workstreams/mercado/research/PITFALLS.md` — incidente 27x, imwrite, oclusão parcial
- `.planning/workstreams/mercado/research/ARCHITECTURE.md` — camadas e pontos de integração com file:line
- `.planning/workstreams/mercado/research/STACK.md` — verificação empírica (Python 3.12.10, SQLite 3.49.1)
- `l2scanner/gravador.py` — o `cv2.imwrite` sem checagem (alvo do FUND-01)
- `l2scanner/identidade.py` — técnica de template matching medida (1.000 acerto vs 0.454 erro)
- `l2scanner/visao.py` — lógica de oclusão existente que consumirá o sinal do painel

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `l2scanner/gravador.py` — Gravador com PNG por frame + JSONL flushed; o fix é pontual (checar retorno de `cv2.imwrite` e falhar alto)
- `l2scanner/calibracao.py` + `l2scanner/calibrar.py` + `calibrar.bat`/`calibrar-solo.bat` — fluxo de calibração a estender com modo mercado
- `l2scanner/identidade.py` — matching de conjunto fechado por template, técnica validada a replicar para nomes de mercado e dígitos
- `ReplaySource` / `tests/test_conferencia_gravada.py` — infraestrutura de replay para rodar detecção contra gravações
- `recordings/` — contém a gravação do incidente 27x (inventário/painéis) para o teste de regressão do sinal compartilhado

### Established Patterns
- Fixture-first: toda detecção é desenvolvida e testada contra gravações, nunca ao vivo
- Chaves de calibração opcionais via `.get` (padrão `banner_manutencao`) — compat com calibrações antigas
- Falha fechada: sinal ilegível é descartado com aviso, nunca interpretado
- Zero dependências novas neste milestone (verificado pela pesquisa; venv real é Python 3.12.10)

### Integration Points
- `l2scanner/__main__.py` — flags de invocação (`--record` já existe; `--mercado` só na Fase 4)
- `l2scanner/visao.py` — o detector de morte consome o sinal "World Exchange aberto" como oclusão conhecida (um sinal, dois consumidores)
- `calibration.json` — recebe as novas chaves de mercado (regiões, âncora do painel, templates)

</code_context>

<specifics>
## Specific Ideas

- O encanto renderiza hoje como `+3 <nome do item>` — confirmado pelo usuário direto do jogo
- Inventário e mercado são mutuamente exclusivos na UI (abrir um fecha o outro) — simplifica o cenário de oclusão do painel
- A marcação de alvo/vida do próprio char pode sobrepor levemente o painel às vezes — cenário real a gravar
- Verificação do DETC-01: replay da gravação do incidente 27x com painel reconhecido e ZERO alertas de morte

</specifics>

<deferred>
## Deferred Ideas

- **Outras janelas do menu sobrepondo o mercado (edge cases raros)** — o usuário confirmou que acontece, mas é raro; anotado para tratar em versão futura, fora do roteiro do v1
- Spike validado não-empacotado `wgc-janela-em-segundo-plano` — rodar `/gsd-spike --wrap-up` para virar findings skill (fora desta fase)
- Comandos WhatsApp de mercado (WAPP-01/02) — já registrados como v2 em REQUIREMENTS.md

</deferred>
