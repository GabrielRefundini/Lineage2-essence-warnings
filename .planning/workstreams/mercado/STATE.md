---
gsd_state_version: 1.0
milestone: v1-mercado
milestone_name: )
current_phase: 2
current_phase_name: Leitura de pagina
status: executing
stopped_at: Completed 02-04-PLAN.md (o TRACER)
last_updated: "2026-08-30T16:34:57.082Z"
last_activity: 2026-08-30
last_activity_desc: "Fase 2 plano 02: a sonda de oclusao, o limiar de dispersao, o piso de linhas comparadas e o piso/margem de leitura de glifo — seis chaves MEDIDAS por varredura sobre 478 frames e 55.342 glifos; a guarda de cruzamento REPROVOU e ficou desligada"
state_head: f97e3288fa0ccb101a0d02ae92e09a282b769b6a
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 11
  completed_plans: 9
  percent: 25
---

# Project State

## Project Reference

**Core value:** Cada abertura do World Exchange vira coleta de dados — preços lidos passivamente da tela, sem nunca enviar input ao jogo.
**Current focus:** Phase 1 — Fundação — firewall, gravador e spike de campo
**Delivery decision (locked):** console-only na v1; comandos WhatsApp de mercado são v2.

## Current Position

Phase: 2 — Leitura de pagina
Plan: 5 of 6
Status: Ready to execute
Last activity: 2026-08-30 — Completed 02-03: corte 0,894737 e piso 0,883732 medidos, A8 REFUTADA, e a fonte da assinatura decidida pelo usuario: `ocr-estrito`

Progress: [███░░░░░░░] 25%

## Accumulated Context

### Decisions

- F0 (firewall de escopo) dobrada na Fase 1: FIRE-01 é um teste de CI + Out of Scope já registrado; fase própria seria cerimônia (granularity: coarse)
- DETC-02 e LEIT-04 vivem na Fase 4: são a fiação do laço `--mercado` e a superfície de console, conforme a espinha da pesquisa
- Fase 3 paraleliza com a Fase 2: depende só do formato da página aceita, não da leitura pronta
- Slugs de fase levam prefixo `mercado-` para não colidir com o workstream default
- [Phase 1]: O log ALTO da falha de gravacao mora em gravador.py, nao em Sessao.tick: o modulo que possui a verdade do disco e o que reporta a mentira, e assim sessao.py fica byte-identico
- [Phase 1]: Contagem do disco usa is_file(): um diretorio com nome de PNG seria contado por um glob cru, reintroduzindo a mentira dentro da propria conferencia
- [Phase 1]: O firewall FIRE-01 prova o vermelho por mutacao e por dist-info fabricada; instalar uma banida de verdade num teste seria cometer o proprio pecado
- **[2026-08-29] PERSISTÊNCIA É CSV, NÃO SQLITE.** Decisão do usuário. O motivo que decidiu:
  ele quer ler o dado a olho nu, importar no Google Sheets e entregar para outra IA analisar
  — CSV serve os três, um `.db` não serve nenhum sem ferramenta no meio. Das três
  justificativas do SQLite, duas já tinham caído (só o Yazalaque escreve, então não há
  concorrência e a dedup cabe em memória) e a terceira estava dimensionada errada. Separador
  de campo `;`, porque a vírgula decimal travada colapsaria um CSV separado por vírgula.
  Reescrito em REQUIREMENTS.md e ROADMAP.md; a pesquisa está marcada como superseded nessa
  parte.

- **[2026-08-29] A calibração PROPÕE e o usuário confirma.** A ferramenta pedia ao humano
  para adivinhar o sentido de uma frase e aceitava calado o retângulo desenhado — violando a
  disciplina do próprio projeto, que mede em vez de supor. Agora cada retângulo vem
  pré-desenhado a partir de medição (`mercado_geometria.py`) e o ENTER confirma. Três
  defeitos que só o uso humano encontrou: instruções ambíguas, a mensagem final descrevendo
  uma imagem que não era a gravada (chip aberto), e a contagem de linhas truncando `447//45`
  em 9 — três pixels de erro de mão custavam um anúncio por página.

- [Phase 02]: A coluna do nome termina no rotulo `Quantity` do cabecalho, e nao no texto da pagina: medir pelo texto daria 263 px (os dez nomes do frame sao o mesmo item) e truncaria nome longo. Os 270 px do plano viraram PISO afirmado em teste; o medido e 324 px.
- [Phase 02]: O fim do icone do item sai da SATURACAO, com referencia medida nas colunas de numero da mesma linha. Maior-vao e Otsu foram TENTADOS e pousam no miolo escuro do icone (84-107 entre bordas de 193-255), devolvendo 22 onde a resposta e 42 — as duas refutacoes ficaram escritas na docstring de `_fim_do_icone`.
- [Phase 02]: As colunas de numero sao contadas A PARTIR DA DIREITA, com `Buy` de ancora: da esquerda a contagem quebra quando o icone e o nome se fundem (vao de 5 px em 063752/frame_000000 contra 13 px em pagina-cheia/frame_000010).
- [Phase 02]: As 3 ancoras gravadas no calibration.json sao NOVAS, recortadas de 063752/frame_000000, porque as originais do usuario foram apagadas pelo incidente da janela quebrada 13. Ele conferiu na imagem de conferencia e aprovou.
- [Phase 02]: Rotular linha limpa/coberta pela PASTA de origem foi REFUTADO por medicao — as 6 gravacoes "sem oclusao deliberada" contem tooltip (a pesquisa nomeia `scroll/frame_000084`), e com esse rotulo as populacoes se sobrepoem nos 214 trechos candidatos varridos. O rotulo passou a ser o GABARITO DE CAMPO nomeado frame a frame e linha a linha, em `tools/medir_oclusao.py`.
- [Phase 02]: Escolher o trecho da sonda por "menor dispersao mediana" tambem foi REFUTADO: o trecho de mediana zero rejeita 22,4% de TODAS as linhas de campo. A escolha e a MAIOR FOLGA RELATIVA contra o gabarito, e um candidato cuja pior limpa e exatamente 0 e descartado — a razao contra zero nao e medicao. Escolhido `x em [207, 417)` com folga 7,67x.
- [Phase 02]: O piso de LEITURA de glifo e 0,4698 e a margem 0,0370, MEDIDOS sobre 55.342 runs de 4.374 linhas. O limiar de COLISAO 0,8555 rejeitaria 39,4% dos glifos reais e a margem 0,12 herdada de identidade.py rejeitaria 26,7% — por isso os dois vivem em chaves proprias. A margem medida confirma de forma independente os 0,0370 do par `0`x`8` da pesquisa.
- [Phase 02]: A guarda de cruzamento `Total / Quantity` REPROVOU e ficou DESLIGADA (`mercado_tolerancia_do_cruzamento = None`): tolerancia 1273 centesimos por unidade contra o maximo 1,0, fechamento no limite derivado 0,6525, deteccao 0,0164 sobre 1.893 substituicoes `0`<->`8` injetadas. O 02-04 Task 4 le a linha `GUARDA REPROVADA por tolerancia, 1273.0000 centesimos por unidade (maximo 1.0)` e registra a refutacao em vez de ligar o mecanismo.
- [Phase 2]: [Phase 02]: A trava de digitos e o que torna o corte PROPONIVEL, e agora e numero: sem ela as populacoes se sobrepoem (vao -0,054416, 182 pares, '+6 Agathion' x 'Agathion' a 0,9492); com ela o vao e +0,022010. Corte 0,894737, piso 0,883732 (o MEIO do vao, nao o extremo — no extremo 'Wind Spirit Evolution Stone' ficaria permanentemente invisivel).
- [Phase 2]: [Phase 02]: A suposicao A8 esta REFUTADA. Com a posicao do digito dada DE FORA o molde acerta 9 de 9 contra o gabarito de encanto; com a regra de producao (cada run sozinho, digito quando passa no piso) acerta 0 de 10 e devolve '7655' onde a resposta e '6'. Os 13 moldes NAO TEM CLASSE DE REJEICAO: nao ha molde de letra. Ha vao entre digito verdadeiro (min 0,8510) e falso positivo (max 0,6947), mas o piso de hoje (0,4698, medido em colunas de NUMERO) nao separa.
- [Phase 2]: [Phase 02]: As duas populacoes de uma medicao tem de se apoiar na MESMA nocao de confianca. Aqui e o VOCABULARIO DE CONSENSO (50 nomes que as duas escalas leram identicos). Sem ele, '-ano' x '\ufffdano' (duas leituras FALHADAS) puxava o corte de 0,8947 para 0,7500, e leituras corrompidas por oclusao entravam como 'itens diferentes'.
- [Phase 2]: [Phase 02]: A rota 'ocr-igualdade' NAO cria as series duplicadas que a hipotese previa: ZERO nas 8 gravacoes. Ela recusa a linha antes de duplicar, e em troca perde 5 linhas a mais que 'ocr-estrito'. O argumento contra ela virou 'estritamente dominada', e nao 'suja o catalogo'.
- [Phase 2]: [Phase 02]: A FONTE da assinatura de digitos da chave da serie e o OCR (rota `ocr-estrito`), escolhida pelo usuario no portao do 02-03 em 2026-08-30. A `molde` caiu apesar dos 95,32% (A8 refutada: 0 de 10 sob a regra de producao; chave `7655` inutil num CSV que se le a olho); a `ocr-igualdade` caiu por dominancia estrita. Custo aceito: 8,86% das linhas caem, as vezes pagina inteira. Caminho de volta medido (vao +0,1563 entre 0,8510 e 0,6947) na docstring de assinatura_por_molde.

### Blockers

- **Nenhum bloqueio ativo.** O portao do 02-03 fechou em 2026-08-30: o usuario escolheu
  `ocr-estrito`.

- O bloqueio da Fase 1 (só o usuário podia gravar o World
  Exchange) foi cumprido: 8 gravações feitas, spike respondido e validado seção por seção,
  calibração completa pela mão do usuário em 2026-08-29.

- JANELA 13 ABERTA: `l2scanner/calibrar.py` (calibracao de PARTY) apaga TODA a calibracao de mercado — `calibrar_selecionando` monta uma Calibracao do zero (calibrar.py:353) e o fluxo grava por cima do arquivo inteiro (calibrar.py:1244). Confirmado em campo 2026-08-30. Enquanto nao for consertado, recalibrar a party DE NOVO custa a calibracao de mercado outra vez. Resgate em calibration.RESGATE-13-glifos.json.
- ~~DECISAO PENDENTE (02-03 Task 2): a fonte da assinatura de digitos.~~ **RESOLVIDA em 2026-08-30: `ocr-estrito`.** O usuario aceitou o custo de 8,86% das linhas caindo (as vezes pagina inteira) para nao pagar uma chave `7655` que ele nao consegue ler no CSV. O caminho de volta da rota `molde` esta medido e escrito na docstring de `mercado_catalogo.assinatura_por_molde` (vao +0,1563, entre 0,8510 e 0,6947).

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260829-rd9 | OCR de nomes de item entra no escopo: LEIT-01 reescrito, coluna do nome recortada (LEIT-05) | 2026-08-29 | dcab841 | [260829-rd9-ocr-de-nomes-de-item-entra-no-escopo-lei](./quick/260829-rd9-ocr-de-nomes-de-item-entra-no-escopo-lei/) |
| 260830-apd | A calibracao de party para de apagar a de mercado: carrega o disco e preserva os 27 campos que nao sao dela | 2026-08-30 | 0c9038c | [260830-apd-party-calibration-nao-pode-apagar-a-cali](./quick/260830-apd-party-calibration-nao-pode-apagar-a-cali/) |

### Todos

- [ ] ~~**DEFINIR A `[mercado] watchlist` no `config.toml`**~~ — **DEIXOU DE SER BLOQUEIO
      em 2026-08-29** (quick `260829-rd9`). O motivo escrito aqui era o critério 1 da Fase 2,
      que dizia "todo item da watchlist visível é reconhecido" — esse critério foi substituído.
      LEIT-01 agora lê o nome por OCR e agrupa por similaridade; item desconhecido vira série
      nova sozinho. A watchlist não é mais a porta de entrada do que é registrado. Se
      sobreviver, é como filtro de DESTAQUE no console (Fase 4). Fecha a janela quebrada 12.

- [ ] Registrar/atualizar a discrepância de docs: CLAUDE.md diz Python 3.13, venv real é 3.12.10 (não bloqueia)

### Fatos operacionais que só existiam na conversa

- **FLAKE CONHECIDO, PRÉ-EXISTENTE:** `tests/test_agenda.py` vaza um `KeyboardInterrupt` que
  aborta a sessão inteira do pytest perto de ~88 testes. Medido: 5 abortos em 60 rodadas,
  reproduzido em commit anterior a todo o trabalho do mercado. **Abortar não é falhar** —
  rode de novo. Baseline verde nesta árvore em 2026-08-30, depois do 02-02:
  **1934 passed, 2 skipped** (1881 antes dos 53 testes novos do 02-02).

- **pytest roda no Python GLOBAL, não no `.venv`** (o venv não tem pytest). Isso é
  load-bearing para o firewall FIRE-01, que por isso varre três lugares.

- **`calibration.json` é gitignored** — estado de máquina, nunca commitado. Hoje carrega:
  3 âncoras, grade de 10 linhas de 45 px em layout **`negociacao`** (deslocamento
  `dx=-427 dy=256`), geometria 1720x1392, **13 moldes de glifo completos**
  (`0-9`, `,`, `XM Coin`, `Adena`), as quatro colunas e o molde do cabeçalho (02-01), e
  os **seis números medidos pelo 02-02**: `mercado_sonda_do_fundo`
  `{dx0: 207, dx1: 417, folga: 2}`, `mercado_limiar_de_dispersao_do_fundo` 0.026377,
  `mercado_minimo_de_linhas_comparadas` 7, `mercado_limiar_de_leitura_de_glifo` 0.469831,
  `mercado_margem_de_leitura_de_glifo` 0.036984, e `mercado_tolerancia_do_cruzamento`
  **`None`** (guarda REPROVADA e desligada de propósito). `mercado_templates_de_nome` e
  `mercado_limiar_de_template` continuam `null` — sem número inventado.

- **Recordings ficam só no checkout principal** (gitignored). Um executor em worktree tem de
  lê-los por caminho absoluto, somente leitura.

- **Worktree:** `worktree.baseRef: "head"` fixado em `.claude/settings.local.json` porque o
  repo não tem remote — sem isso o `base-check` degrada para execução sequencial (#683).

## Session Continuity

**Last session:** 2026-08-30T16:34:56.952Z

**Stopped At:** Completed 02-04-PLAN.md (o TRACER)
**Resume File:** None
**Next:** `/gsd-plan-phase 1` (workstream mercado) após aprovação

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 1 P1 | 8 min | 3 tasks | 4 files |
| Phase 02 P01 | 8h 14m | 3 tasks | 9 files |
| Phase 02 P02 | 1h 25m | 2 tasks | 12 files |
| Phase 02 P03 | 1h 45m | 1 tasks | 8 files |
| Phase 02 P04 | 3h 25m | 3 tasks | 18 files |
