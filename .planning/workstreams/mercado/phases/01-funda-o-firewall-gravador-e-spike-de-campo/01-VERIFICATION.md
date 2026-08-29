---
phase: 01-funda-o-firewall-gravador-e-spike-de-campo
workstream: mercado
verified: 2026-08-29T21:36:10Z
status: passed
score: 5/5 must-haves verificados
behavior_unverified: 0
overrides_applied: 0
suite: "1704 passed, 2 skipped (Python GLOBAL, medido pelo verificador; o flake do test_agenda vazou KeyboardInterrupt na 1a corrida e a 2a fechou limpa)"
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - >-
      G-01 — `mercado_templates_de_digito` nao tinha produtor nenhum no
      repositorio. Agora tem: `cortar_glifos` / `segmentar_glifos` /
      `matriz_de_confusao_de_glifos` / `fundir_glifos` / `_gravar_os_glifos` em
      `calibrar_mercado.py`, ligados nos DOIS fluxos (completo em `:2278-2367`
      e `--so-digitos` em `:2064-2085`). Eu mesmo dirigi a cadeia
      producao -> disco -> leitura sobre pixels REAIS do jogo e ela devolveu
      10 glifos, matriz APROVADA em 0.7110 e persistencia byte a byte.
  gaps_remaining: []
  regressions: []
  warnings_closed:
    - >-
      WARNING-01 — o dano residual de CR-03/CR-04 no `calibration.json` do
      disco sumiu na recalibracao humana: `mercado_limiar_de_template` deixou
      de ser o `0.5` sem significado e voltou a ser `null`.
deferred:
  - truth: "Os moldes de nome da watchlist cortados pela ferramenta (metade de D-05/D-06)"
    addressed_in: "Fase 2"
    evidence: >-
      A classificacao ANTERIOR foi reconferida e CONTINUA valendo, agora com a
      fase completa em volta. Criterio 1 da Fase 2, verbatim: "todo item da
      watchlist (`config.toml`) visivel na pagina e reconhecido pelo nome" —
      match especifico, nao tangencial. A capacidade existe e avisa alto
      (`calibrar_mercado.py:2248-2254`), o adiamento esta registrado no proprio
      codigo (`ler_watchlist`, `:1093`) e o que falta e a ENTRADA:
      `[mercado] watchlist` segue comentada em `config.toml:149-154`. Nada
      orfao, ao contrario do que os digitos eram.
warnings:
  - id: WARNING-03
    titulo: "A imagem de conferencia tem nome fixo, e o texto final descreve o que ela nao contem"
    severidade: warning
    bloqueia_a_fase: false
    evidencia: >-
      `_gravar_conferencia` (calibrar.py:677) grava sempre em
      `calibracao-conferencia.png`. No modo `--so-digitos` a imagem gravada e
      SO a montagem dos glifos (`calibrar_mercado.py:2070`), mas
      `_texto_final_da_conferencia` (`:1253-1256`) e o epilogo do
      `calibrar-mercado.bat` mandam conferir "os retangulos verdes ... a faixa
      de titulo, o X de fechar, a seta de rolagem, a area da lista e a
      primeira linha" — que nao estao no arquivo. Duas bocas repetem a mesma
      frase.
    por_que_nao_bloqueia: >-
      Nao toca `calibration.json`, nao produz numero errado e nao esta no
      caminho que os 5 criterios exigem. E o artefato final no disco esta
      CORRETO: `calibracao-conferencia.png` mede 1720x1480 = frame (1392) +
      montagem dos glifos (88), a imagem EMPILHADA que so o fluxo completo
      produz, com o mesmo mtime do `calibration.json` (18:25). A ultima rodada
      humana foi a completa, entao a sobrescrita ficou na direcao inofensiva.
    pendencia: >-
      Esta registrado APENAS em prosa no `01-05-SUMMARY.md` ("Pendencias
      registradas, NAO resolvidas"). Nao ha marcador de divida no codigo (o
      portao de TBD/FIXME/XXX nao dispara) e nao ha entrada em
      `.planning/todos/pending/`. Recomendacao: virar todo antes da Fase 2,
      para nao evaporar como prosa de SUMMARY.
  - id: WARNING-04
    titulo: "Bookkeeping desatualizado em tres arquivos"
    severidade: warning
    bloqueia_a_fase: false
    evidencia: >-
      (a) `ROADMAP.md:48-60` marca so `01-01-PLAN.md` como `[x]`, com os cinco
      planos executados e os cinco SUMMARYs no disco; a Fase 1 segue `[ ]`.
      (b) `REQUIREMENTS.md:92-94` lista FUND-02, FUND-03 e DETC-01 como
      `Pending` e sem `[x]`, com os tres satisfeitos.
      (c) `01-05-SUMMARY.md` tem `status: complete` e a secao "PORTAO
      CUMPRIDO", mas o frontmatter segue `tasks_completed: 2 / tasks_total: 3`
      e a tabela interna ainda diz "Task 3 — AGUARDANDO O USUARIO".
    por_que_nao_bloqueia: "Nenhum impacto funcional. Corrigir ao fechar a fase."
decision_coverage:
  honored: 10
  total: 10
  nota: >-
    D-06 estava PARCIAL na verificacao anterior ("templates cortados pela
    ferramenta, com conferencia visual e matriz de confusao" valia so para os
    moldes de NOME). Agora esta INTEIRA para os glifos: ferramenta propria,
    conferencia visual (`montar_glifos` empilhada na imagem) e matriz de
    confusao propria (`COLISAO_MAXIMA_ENTRE_GLIFOS`, 78 pares, 0 incalculaveis).
    Para os moldes de NOME a capacidade continua existindo e esperando a
    watchlist — o que esta `deferred`, nao ausente.
---

# Fase 1: Fundação — firewall, gravador e spike de campo — Relatório de Verificação (2ª passada)

**Objetivo da fase:** O usuário consegue produzir evidência de campo confiável do World Exchange, e dessa evidência saem a calibração, os templates e a detecção do painel — o sinal único que também protege o detector de morte.

**Verificado:** 2026-08-29T21:36:10Z
**Status:** `passed` — 5/5
**Re-verificação:** Sim — depois do fechamento da lacuna G-01 pelo plano 01-05

---

## Veredito em uma frase

A lacuna G-01 fechou de verdade, e eu não aceitei isso do SUMMARY: **dirigi a ferramenta eu mesmo, sobre pixels reais do jogo, com apenas o mouse e o teclado dublados, e ela cortou dez glifos, rodou a matriz, derivou o limiar e gravou tudo num JSON que voltou byte a byte** — o critério 3 passou de "duas de três coisas" para as três, e as outras quatro verdades continuam verdes sob reteste.

---

## O que eu fiz para não acreditar no SUMMARY

Nenhuma linha desta seção veio de um documento. Todas são comandos que rodei.

| Verificação | Comando | Resultado |
|---|---|---|
| Suíte completa | `python -m pytest tests/ -q` | 1ª corrida: o flake conhecido do `test_agenda` vazou `KeyboardInterrupt` aos 87 testes. 2ª corrida: **`1704 passed, 2 skipped in 34.06s`** |
| Firewall VERMELHO | `.venv\Scripts\pip install keyboard` + pytest | **`1 failed, 17 passed`**, com a mensagem citando a restrição fundadora |
| Firewall VERDE de volta | `pip uninstall -y keyboard` + pytest | **`18 passed`**; `pip list \| grep keyboard` vazio — **ambiente restaurado** |
| Portão das gravações | `python tools/conferir_gravacoes_do_spike.py` | exit 0, 8 sessões em 1720x1392 |
| Portão das respostas | `python tools/conferir_spike_respostas.py` | exit 0, 9 seções, 43 frames resolvidos |
| Matriz dos glifos, recalculada do disco | `matriz_de_confusao_de_glifos(glifos_de_calibracao(calibration.json))` | **APROVADA**, pior par `('0','8') = 0.7109813`, 78 pares, **0 incalculáveis**, limiar 0.85549 — idêntico ao gravado |
| **Produtor ponta a ponta** | `cortar_glifos` → `fundir_glifos` → `_gravar_os_glifos` → `salvar` → `carregar`, sobre `tests/fixtures/mercado/glifos_precos_f010.png` | **10 glifos cortados** (`, 0 1 2 3 4 5 7 8 9`), matriz APROVADA em 0.7110, limiar 0.8555 gravado, **moldes idênticos byte a byte na volta** |
| Regressão do 27x | `pytest tests/test_mercado_27x.py -k ZERO_eventos` | 3 passed |
| Regressão do gravador | `pytest tests/test_gravador_honesto.py` | 23 passed |
| Party não regrediu | `pytest -k calibr` + `TestAPartyNaoMudou` | 260 passed / 3 passed |

---

## Verdades Observáveis (os 5 critérios de sucesso do ROADMAP)

| # | Verdade | Status | Evidência |
|---|---------|--------|-----------|
| 1 | `--record` com contador batendo com o disco; `imwrite` que falha vira erro alto, nunca frame contado | ✓ VERIFICADO | Reteste: `gravador.py:222` mantém as três saídas atrás de `bool(cv2.imwrite(...))`; `alarme_de_divergencia` (`__main__.py:269`, chamada em `:1905`) COMPARA os dois números; 23 testes comportamentais verdes. Portão de campo: 8 sessões com JSONL == PNGs. |
| 2 | Sessões reais gravadas e perguntas de campo respondidas por escrito, incl. variantes de encanto | ✓ VERIFICADO | Os dois portões executáveis reprovaram nada: 8 gravações em 1720x1392, 43 caminhos de frame resolvidos no disco. As 7 perguntas exigidas pelo critério estão em §1-§5 e §7, com validação datada do usuário; §7 é a decisão de encanto (D-05). A única **NÃO RESPONDIDA** é §6 (idade do anúncio), que o critério não pede — e é a prova de que a falha honesta funciona. |
| 3 | Ferramenta de calibração sobre frame gravado, persistindo regiões/âncora/**templates de dígito** em `calibration.json`, **sem editar JSON à mão** | ✓ **VERIFICADO** (era ✗) | **As três metades, agora.** Regiões ✓ (`mercado_grade`: 10 linhas de 45 px, layout `adena`, dx=-428 dy=258). Âncora ✓ (`mercado_ancoras`: `titulo`, `botao_fechar`, `canto_inf_dir`). **Templates de dígito ✓**: 13 moldes — `0 1 2 3 4 5 6 7 8 9 , XM Coin Adena` — e `cobertura_dos_glifos` devolve `FALTAM: []`. Sem editar JSON à mão ✓ (`cal.salvar` regrava o arquivo inteiro; nada é impresso para o usuário colar). Detalhe abaixo. |
| 4 | No replay do 27x: painel reconhecido **E** ZERO alertas de morte — um sinal, dois consumidores | ✓ VERIFICADO | Reteste: `pytest tests/test_mercado_27x.py` → 22 passed, 0 skips, sobre fixtures COMMITADAS. Os 3 testes `ZERO_eventos` prendem as duas metades no mesmo laço. `rastreador.py` continua sem **uma única** ocorrência de "mercado". |
| 5 | Adicionar biblioteca de síntese de input deixa o teste de firewall vermelho | ✓ VERIFICADO **empiricamente** | Repetido do zero nesta passada: instalei `keyboard` no `.venv` e vi o vermelho com a mensagem completa; desinstalei e vi `18 passed`; conferi que o `.venv` voltou limpo. |

**Score: 5/5 verdades verificadas** (0 present-behavior-unverified, 0 overrides)

---

## O critério 3, em detalhe — porque era ele que falhava

### A metade da MÁQUINA: o produtor existe, é substantivo, está ligado, e eu o vi produzir

A verificação anterior disse: *"`grep -in 'digito|glifo|algarismo' calibrar_mercado.py` devolve nada em 43.527 bytes"*. Hoje o arquivo tem **112.388 bytes** e a mesma busca devolve **90+ linhas**. Mas tamanho não é evidência. O que é:

**Nível 1 — existe.** `l2scanner/mercado_geometria.py` (543 linhas, novo) e, em `calibrar_mercado.py`: `segmentar_glifos` (`:359`), `mascara_do_sufixo`/`recortar_sufixo` (`:456`/`:469`), `_alinhar_por_preenchimento` (`:501`), `_par_incalculavel` (`:529`), `matriz_de_confusao_de_glifos` (`:569`), `explicar_glifos` (`:653`), `GLIFOS_EXIGIDOS`/`cobertura_dos_glifos` (`:1283`/`:1294`), `fundir_glifos` (`:1309`), `cortar_glifos` (`:1700`), `montar_glifos` (`:1857`), `_gravar_os_glifos` (`:1971`), `_anunciar_o_que_faltou` (`:1999`), `_calibrar_so_digitos` (`:2023`).

**Nível 2 — substantivo.** Não é passagem de campo: `COLISAO_MAXIMA_ENTRE_GLIFOS = 0.85` traz as **três convenções de recorte medidas** na docstring, com o número que cada uma produz; `_par_incalculavel` decide por **pré-condições rechecadas**, não por comparar score a 0.0 (e o conjunto real tem quatro zeros legítimos); `VALOR_MINIMO_DO_SUFIXO = 120` sai de um platô medido (V máximo de `XM Coin` é 173, abaixo do piso 180 dos dígitos — a máscara sairia **vazia**).

**Nível 3 — ligado.** Nos **dois** fluxos, não em um: fluxo completo `:2278-2367` e `--so-digitos` `:2064-2085`, ambos terminando em `_gravar_os_glifos` → `cal.salvar`. O `.bat` documenta e passa `--so-digitos` (`:2396`), e `test_calibrar_mercado_bat.py` prende isso.

**Nível 4 — dados fluem, e eu vi fluir.** Dirigi a cadeia inteira substituindo **apenas** `_selecionar_regiao` e `input` — todo o resto é o código de produção — sobre a fixture commitada de **pixels reais do jogo** (`glifos_precos_f010.png`, resgatada de `frame_000010`), partindo de `mercado_templates_de_digito = None`:

```
PARTIDA: templates_de_digito = None | limiar = None
  ok: 100,00   ok: 3,00   ok: 18,90   ok: 7,50   ok: 18,00   ok: 2,45
CORTADOS pela ferramenta: [',', '0', '1', '2', '3', '4', '5', '7', '8', '9']
Matriz de glifos APROVADA: o pior score entre dois glifos diferentes e 0.7110
PERSISTIDOS: [',', '0', '1', '2', '3', '4', '5', '7', '8', '9']
limiar de glifo gravado: 0.8554906845092773
OK: ferramenta -> disco -> leitura, byte a byte
```

E a conferência de contagem **recusa** de verdade: quando dei um retângulo errado de propósito, ela respondeu *"RECUSADO: vi 6 glifo(s) no retangulo, mas voce digitou 9 caractere(s)"* e não gravou nada. Isso é comportamento, não presença.

### A metade HUMANA: aceito, e não pela palavra do SUMMARY

A verificação anterior recusou aceitar regiões medidas por agente. Continuo achando aquela recusa certa — e por isso conferi a afirmação nova contra os artefatos, não contra a prosa:

1. **A impressão digital de uma mão.** `mercado_grade.altura = 445 px`, com `altura_da_linha = 45`. **445 não é múltiplo de 45.** `derivar_grade` grava a altura CRUA do retângulo (`:786`), então esse número só pode ter vindo de um arrasto. Um agente medindo teria produzido 450 exatos — e foi exatamente isso que a passada anterior encontrou. É a evidência mais difícil de forjar do relatório inteiro.
2. **O defeito que só uma mão produz.** `round()` no lugar de `//` (commit `e7880cb`) existe porque 447 px viraram 9 linhas em vez de 10. Está preso por teste com o número real (`test_calibrar_mercado.py:1608-1637`) e por prova de mutação. Um defeito de três pixels não é algo que se invente.
3. **A ergonomia mudou por causa de uma reclamação humana citada literalmente.** *"está muito difícil calibrar isso e é muito fácil eu errar na interpretação do que está sendo pedido"* → quatro commits (`ea699bb`, `a52f04b`, `0defa09`, `f5c3b1d`) que transformam a ferramenta de "peça e aceite calado" em "proponha e o ENTER confirma".
4. **O artefato físico bate com o relógio.** `calibration.json` (34.610 B) e `calibracao-conferencia.png` (3,6 MB) têm o mesmo mtime — 18:25 de hoje. A imagem mede **1720x1480** = frame (1392) + montagem dos glifos (88): é a imagem EMPILHADA que **só o fluxo completo** produz (`:2291-2297`). O `--so-digitos` grava 88 px de altura.
5. **13 glifos de dois frames.** O conjunto completo inclui o `8`, que o SUMMARY registra não existir no frame de calibragem — só a fusão entre rodadas (`fundir_glifos`) explica isso, e a fusão é o mecanismo que existe justamente para essa costura.

Nada disso é a palavra do executor. É o estado do disco.

---

## Itens Adiados (não são lacunas acionáveis)

| # | Item | Endereçado em | Evidência |
|---|------|---------------|-----------|
| 1 | Moldes de nome da watchlist cortados pela ferramenta | Fase 2 | **Reconferido nesta passada e a classificação se mantém.** O critério 1 da Fase 2 é literalmente "todo item da watchlist (`config.toml`) visível na página é reconhecido pelo nome" — match específico, não tangencial. A capacidade existe e **avisa alto** (`:2248-2254`), o adiamento está registrado no próprio código (`ler_watchlist`, `:1093`), e o que falta é a ENTRADA: `[mercado] watchlist` segue comentada em `config.toml:149-154`. Aliviador extra: `mercado_limiar_de_template` voltou a ser `null` em vez do `0.5` sem significado, então **nenhum número inventado espera a Fase 2**. |
| 2 | Consumidores do sinal "mercado aberto" (laço `--mercado` e oclusão do detector de morte) | Fase 4 (junto de DETC-02) | Reconciliação `<detc01_reconciliation>` em `01-04-PLAN.md:118-151` e reproduzida no `ROADMAP.md:62`. Registro nos dois lugares, como antes. |

---

## Artefatos Exigidos

| Artefato | Existe | Substantivo | Ligado | Dados fluem | Status |
|----------|--------|-------------|--------|-------------|--------|
| `l2scanner/gravador.py` | ✓ | ✓ `bool(cv2.imwrite)` em `:222` | ✓ `__main__.py:1905` | ✓ disco real | ✓ VERIFICADO |
| `tests/test_firewall_escopo.py` | ✓ | ✓ 3 varreduras + teste-do-teste | ✓ | ✓ provado por instalação real | ✓ VERIFICADO |
| `tests/test_gravador_honesto.py` | ✓ | ✓ 23 testes | ✓ | ✓ | ✓ VERIFICADO |
| `l2scanner/mercado_visao.py` | ✓ | ✓ + `glifos_para/de_calibracao` (`:630`/`:667`) com guard de conjunto | ✓ `__main__.py:373` | ✓ fixtures reais | ✓ VERIFICADO |
| `ROTEIRO-SPIKE.md` / `SPIKE-RESPOSTAS.md` | ✓ | ✓ 8 cenários / 9 seções seladas | ✓ | ✓ 43 frames resolvidos | ✓ VERIFICADO |
| `tools/conferir_*.py` (2 portões) | ✓ | ✓ | ✓ executados: APROVADO, exit 0 | ✓ | ✓ VERIFICADO |
| `l2scanner/calibrar_mercado.py` | ✓ | ✓ **112 KB**, corte de glifos + matriz própria | ✓ `.bat` + `_selecionar_regiao` compartilhado | ✓ **dirigido por mim** | ✓ **VERIFICADO** (era ⚠️ INCOMPLETO) |
| `l2scanner/mercado_geometria.py` **(novo)** | ✓ | ✓ 543 linhas, `localizar_o_titulo` / `medir_a_grade` / `ancora_deslocada` | ✓ importado nos dois fluxos | ✓ mede nos pixels | ✓ VERIFICADO |
| `l2scanner/calibrar.py` (`_selecionar_regiao(sugestao=None)`) | ✓ | ✓ +112/-1 | ✓ mercado passa sugestão, party não passa | ✓ | ✓ VERIFICADO |
| `tests/test_mercado_glifos.py` **(novo)** | ✓ | ✓ sobre pixels reais commitados | ✓ | ✓ | ✓ VERIFICADO |
| `tests/test_sugestao_de_calibracao.py` **(novo)** | ✓ | ✓ 56 testes, inclui `TestAPartyNaoMudou` | ✓ | ✓ | ✓ VERIFICADO |
| `tests/fixtures/mercado/glifos_*.png` **(novos)** | ✓ | ✓ 240x45 e 40x30, de `frame_000010` real | ✓ usados em 30+ asserções | ✓ | ✓ VERIFICADO |
| `tests/test_mercado_27x.py` | ✓ | ✓ 22 testes, duas metades | ✓ fixtures commitadas | ✓ | ✓ VERIFICADO |
| `l2scanner/visao.py` (`mercado_aberto_aparente`) | ✓ | ✓ | ✓ `sessao.py:263` → `__main__.py:576` | ✓ | ✓ VERIFICADO |
| `calibration.json` (chaves de mercado) | ✓ | ✓ **4 de 4 chaves de conteúdo com valor honesto** | ✓ | ✓ | ✓ **VERIFICADO** (era ⚠️ PARCIAL) |

---

## Ligações-Chave (wiring)

| De | Para | Via | Status |
|----|------|-----|--------|
| `calibrar()` | `mercado_templates_de_digito` | `cortar_glifos` → `fundir_glifos` → `_gravar_os_glifos` → `cal.salvar` (`:2278-2342`) | ✓ **LIGADO — dirigido por mim** |
| `_calibrar_so_digitos()` | mesma chave | mesma cadeia (`:2064-2072`) | ✓ LIGADO |
| `calibrar_mercado.py` | `mercado_geometria.py` | `localizar_o_titulo` / `medir_a_grade` — proposta medida, não chute | ✓ LIGADO |
| `calibrar_mercado.py` | `calibrar.py` | `_gravar_conferencia`, `_selecionar_regiao` importados, **não duplicados** | ✓ LIGADO |
| `mercado_visao.glifos_para/de_calibracao` | JSON ↔ ndarray | hex + guard de altura dominante | ✓ LIGADO — **round-trip byte a byte provado** |
| `calibracao.py` | `calibration.json` | `mercado_limiar_de_glifo` opcional via `.get`; `VERSAO_DO_ESQUEMA` **segue 2** | ✓ LIGADO |
| `__main__.py` | `mercado_visao` | `montar_vigia_do_mercado` lê **só** `mercado_ancoras` (`:355,373`) | ✓ LIGADO |
| `sessao.py` | `visao.Observacao` | `replace(...)` **depois** de `rastreador.observar` (`:263`) | ✓ LIGADO |
| `test_mercado_27x.py` | `rastreador.py` | tripwire de arquitetura: o fonte NÃO cita mercado | ✓ LIGADO |

### Rastreamento de fluxo de dados (Nível 4)

**Caminho novo (glifos):** pixels reais → `segmentar_glifos` → `cortar_glifos` → `fundir_glifos` → `matriz_de_confusao_de_glifos` → `_gravar_os_glifos` → `calibration.json` → `glifos_de_calibracao` → moldes idênticos. **FLUINDO**, verificado por execução, com o mesmo `0.7110` saindo dos dois lados (arquivo do usuário e minha rodada independente).

**Caminho de produção (sinal):** `calibration.json` → `montar_vigia_do_mercado` → `RastreioDoPainel.observar` → `sessao._olhar_o_mercado` → `Observacao.mercado_aberto_aparente` → linha do console. **FLUINDO**, sem regressão.

---

## Execução de Portões (probes)

| Portão | Comando | Resultado | Status |
|--------|---------|-----------|--------|
| Gravações do spike | `python tools/conferir_gravacoes_do_spike.py` | exit 0 — 8 gravações, todas 1720x1392 | ✓ PASS |
| Respostas do spike | `python tools/conferir_spike_respostas.py` | exit 0 — 9 seções, 43 frames resolvidos | ✓ PASS |
| Suíte completa | `python -m pytest tests/ -q` | **1704 passed, 2 skipped** (2ª corrida; 1ª abortada pelo flake conhecido) | ✓ PASS |
| Testes de glifo/calibração | `pytest test_mercado_glifos + test_calibrar_mercado + test_sugestao + test_27x` | **239 passed** | ✓ PASS |
| **Firewall vermelho** | `pip install keyboard` → pytest → `pip uninstall` → pytest | **1 failed, 17 passed** → **18 passed**; `.venv` conferido limpo | ✓ PASS |
| **Produtor de glifos ponta a ponta** | script próprio sobre fixture real, só mouse/teclado dublados | 10 glifos, matriz APROVADA, persistência byte a byte | ✓ PASS |

Os 2 skips continuam sendo `pytest.skip` condicionais sobre `recordings/` (gitignored) — o padrão da casa, com fixtures commitadas equivalentes.

---

## Proibições (verificação negativa)

| Proibição | Status | Evidência desta passada |
|-----------|--------|--------------------------|
| `rastreador.py` NÃO pode ler o sinal de mercado | ✓ **VERIFICADO** | `grep -in "mercado" l2scanner/rastreador.py` → **zero ocorrências**. A segurança vem da leitura não existir. |
| NÃO estender o gate de brilho da barra própria | ✓ **VERIFICADO** | `git log 0ec4b97..HEAD -- l2scanner/visao.py` → **vazio**. O plano 01-05 não tocou o arquivo. `barra_propria_legivel` (`:294`), `_moldura_da_barra_propria` (`:278`) e `_bordas_da_barra_intactas` (`:511`) intocadas. |
| NÃO escrever imagem em `calibrar_mercado.py` | ✓ VERIFICADO | `grep -c imwrite` → **0**; importa `_gravar_conferencia`. Idem `mercado_geometria.py` → **0**. |
| NENHUM `cv2.imwrite` novo em `calibrar.py` | ✓ VERIFICADO | O único diff da fase em `calibrar.py` é `a52f04b` (+112/-1) e **não adiciona nem remove imwrite**. O `:662` é o `_gravar_conferencia` pré-existente. |
| A calibração de PARTY continua funcionando | ✓ VERIFICADO | `TestAPartyNaoMudou` afirma que a party não passa sugestão nenhuma **e** que `assinatura.parameters["sugestao"].default is None`. `pytest -k calibr` → 260 passed; `test_janela_de_selecao` + `test_conferencia_gravada` + `test_navegador_de_frames` → 38 passed. |
| NÃO chutar limiar | ✓ VERIFICADO | `mercado_limiar_de_glifo` só é escrito quando a matriz DERIVOU (`:1993-1995`); com <2 glifos ela diz "NENHUM limiar foi derivado" e não inventa — comportamento que eu vi na minha rodada de teste. |
| NÃO subir `VERSAO_DO_ESQUEMA` | ✓ VERIFICADO | `calibracao.py` → `2`; `calibration.json` → `versao: 2`. |
| NÃO apagar calibração anterior sem perguntar | ✓ VERIFICADO | `_gravar_os_glifos` repete a guarda do CR-04 (`if cortados: ... elif já-existe: avisa`); `fundir_glifos` provado por 3 testes ("o total nunca diminui"). |
| NÃO permitir biblioteca de síntese de input | ✓ VERIFICADO **empiricamente** | Vermelho e verde reproduzidos nesta passada. |

**Nenhuma proibição foi violada.**

---

## Cobertura de Requisitos

| Requisito | Plano | Descrição | Status | Evidência |
|-----------|-------|-----------|--------|-----------|
| **FIRE-01** | 01-01 | Build quebra se lib de síntese de input entrar na árvore | ✓ SATISFEITO | Vermelho reproduzido com `keyboard`, ambiente restaurado |
| **FUND-01** | 01-01 | Gravador só conta frames confirmados no disco | ✓ SATISFEITO | Código + 23 testes + 8 sessões sem divergência |
| **FUND-02** | 01-01/02/03 | Sessões gravadas + perguntas de campo respondidas | ✓ SATISFEITO | Dois portões executáveis, exit 0 |
| **FUND-03** | 01-04 **+ 01-05** | Calibração do mercado (regiões, âncora, **templates de dígito**) persiste via ferramenta própria | ✓ **SATISFEITO** (era ✗ BLOQUEADO) | Produtor existe, está ligado nos dois fluxos e eu o dirigi ponta a ponta; 13/13 glifos no disco, `cobertura_dos_glifos` → `FALTAM: []` |
| **DETC-01** | 01-02/04 | "World Exchange aberto" por âncora positiva, sinal compartilhado | ✓ SATISFEITO no escopo reconciliado | Sinal medido + superfície exibicional; consumidores na Fase 4 por desenho registrado |

**Requisitos órfãos:** nenhum.
**Bookkeeping:** `REQUIREMENTS.md:92-94` ainda diz `Pending` para FUND-02/03 e DETC-01 — ver WARNING-04.

---

## Anti-Padrões

| Categoria | Resultado |
|-----------|-----------|
| Marcadores de dívida (`TBD`/`FIXME`/`XXX`) | **ZERO** nos arquivos tocados pelo 01-05 (`calibrar_mercado.py`, `mercado_geometria.py`, `calibrar.py`, `mercado_visao.py`, `calibracao.py` e os três de teste) |
| `TODO`/`HACK`/`PLACEHOLDER` | **ZERO** nos arquivos do 01-05 |
| Retornos vazios / stubs | Nenhum no caminho de produção. `mercado_templates_de_nome: null` **não** é stub: é ausência de entrada do usuário, anunciada alto |
| Números inventados no disco | Nenhum. `mercado_limiar_de_template` voltou a `null` em vez do `0.5` derivado de matriz vazia — o WARNING-01 anterior fechou sozinho, como previsto |
| Testes circulares | Nenhum. Os glifos vêm de frames reais do jogo (fonte externa). A convenção de recorte está **declarada na assinatura** e presa por teste, exatamente para impedir que o próximo mantenedor ajuste o recorte até a asserção fechar |
| Força de asserção | **Comportamental** nos pontos caros: 40 ticks através de `sessao.tick` no 27x; recusa por contagem no laço de glifos; prova por mutação no `round()` |

---

## Avisos (nenhum bloqueia a fase)

### ⚠️ WARNING-03 — A imagem de conferência tem nome fixo, e o texto final descreve o que ela não contém

**O defeito, exato.** `_gravar_conferencia` grava sempre em `calibracao-conferencia.png`. No modo `--so-digitos`, a imagem gravada é **só** a montagem dos glifos (`calibrar_mercado.py:2070`) — mas `_texto_final_da_conferencia` (`:1253-1256`) manda conferir *"os retângulos verdes ... a faixa de título do painel, o X de fechar, a seta de rolagem, a área da lista e a primeira linha"*. **E o `calibrar-mercado.bat` repete a mesma frase no epílogo, também incondicionalmente.** São duas bocas dizendo a mesma coisa errada, e o SUMMARY só nomeia uma.

**Por que eu NÃO chamo isso de lacuna bloqueante** — e esta é a parte que o prompt pediu que eu julgasse, não que aceitasse:

1. **Não é o que o critério 3 pede.** O critério é sobre o que fica persistido em `calibration.json` pela ferramenta. Nada aqui toca esse arquivo, nenhum número sai errado, nenhuma calibração é corrompida.
2. **O artefato real no disco está CORRETO.** Medi: `calibracao-conferencia.png` é 1720x1480 = frame (1392) + montagem dos glifos (88) — a imagem **empilhada** que só o fluxo completo produz. A última rodada humana foi a completa, então a sobrescrita foi na direção inofensiva: o `--so-digitos` anterior é que foi apagado, depois de já ter sido conferido.
3. **A conferência visual aconteceu de fato.** O usuário registrou ter visto os dois laços do `8` contra o oval único do `0` — o pior par da matriz — e os cinco retângulos desenhados sobre o frame.
4. **Está honestamente registrado, com o mecanismo nomeado** ("o nome do arquivo é fixo"), e não escondido: o SUMMARY o chama de *"a família do FUND-01 num canto pequeno"*, que é a leitura certa.

**Onde eu discordo do fechamento, e o que peço:** a pendência vive **só em prosa de SUMMARY**. Não há marcador de dívida no código (então o portão de `TBD`/`FIXME`/`XXX` não dispara e nada a captura) e não há entrada em `.planning/todos/pending/`. É diferente dos moldes de nome, cujo adiamento está registrado no código, no SUMMARY e consumido por um critério nomeado da Fase 2. **Recomendação:** virar `todo` antes da Fase 2. Fica barato agora e some se ninguém reler este SUMMARY.

*(Atenuante que reduz ainda mais a urgência: o conjunto de glifos já está COMPLETO — `cobertura_dos_glifos` devolve `FALTAM: []` — então o `--so-digitos`, único caminho onde o texto mente, provavelmente não precisa ser rodado de novo.)*

### ⚠️ WARNING-04 — Bookkeeping desatualizado em três arquivos

`ROADMAP.md:48-60` marca só `01-01-PLAN.md` como `[x]` com cinco planos executados; `REQUIREMENTS.md:92-94` lista FUND-02/FUND-03/DETC-01 como `Pending`; e o `01-05-SUMMARY.md` tem `status: complete` e a seção "PORTÃO CUMPRIDO" mas segue com `tasks_completed: 2 / tasks_total: 3` no frontmatter e "Task 3 — AGUARDANDO O USUÁRIO" na tabela interna. Sem impacto funcional; corrigir ao fechar a fase.

---

## Verificação Humana Necessária

**Nenhuma.** É a diferença desta passada.

O único item humano que restava do relatório anterior — *"uma mão humana precisa desenhar os cinco retângulos"* — está cumprido, e eu o aceitei por evidência física no disco (a grade de **445 px**, que nenhum agente produziria; o defeito de três pixels virado teste; a imagem empilhada com o mtime do `calibration.json`), não pela afirmação do SUMMARY.

O segundo item do relatório anterior — recalibrar com a watchlist real — foi **reclassificado**: ele pertence ao escopo da Fase 2 (`deferred`), não a uma pendência de verificação da Fase 1. Listá-lo nos dois lugares, como a passada anterior fez, era inconsistente: um item que o Step 9b filtra como adiado não pode ao mesmo tempo travar o status desta fase.

---

## Resumo Narrativo

A lacuna fechou, e fechou pelo caminho difícil — o que o relatório anterior chamava de opção 1, e não pelo override.

O que eu procurei, com a suspeita ligada, foi o padrão clássico de fechamento de lacuna: a função aparece, o SUMMARY declara vitória, e ninguém nunca a chamou. Não é o caso. O produtor está ligado nos **dois** fluxos, termina em `cal.salvar` nos dois, e — o teste que importa — quando eu mesmo o dirigi sobre pixels reais do jogo, substituindo apenas o mouse e o teclado, ele cortou dez glifos, recusou o retângulo que dei errado de propósito citando os dois números, rodou a matriz e devolveu **0.7110** para o par `0`×`8`. Esse mesmo `0.7110` sai do `calibration.json` que o usuário produziu, por um caminho independente do meu. Dois cálculos separados chegando ao mesmo número é o tipo de coincidência que não acontece com código de fachada.

A metade humana do critério 3 era a que eu estava mais preparado para recusar de novo, porque a passada anterior a recusou com razão. O que me convenceu não foi a seção "PORTÃO CUMPRIDO": foi **445**. A altura da grade gravada no disco não é múltiplo de 45, e `derivar_grade` grava a altura crua do retângulo. Um agente medindo teria produzido 450 — e produziu, na rodada anterior. 445 é a impressão digital de um arrasto de mouse. Junto com ela vêm o defeito dos três pixels (447 // 45 = 9, que teria feito a Fase 2 perder um anúncio por página, em silêncio, para sempre) e uma reclamação humana citada literalmente que reescreveu a ergonomia da ferramenta inteira. Esses três achados têm em comum o fato de serem inalcançáveis por agente — e é isso que dá substância à afirmação, não a afirmação em si.

Ficam dois avisos, e eu os pesei em vez de os despachar. O da imagem de conferência é real e é da família do FUND-01: uma mensagem que descreve o que o arquivo não tem — e é pior do que o SUMMARY conta, porque o `.bat` repete a mesma frase e ninguém notou essa segunda boca. Mas ele não toca o `calibration.json`, não produz número errado, mora numa invocação secundária que talvez nem precise rodar de novo (o conjunto de glifos está completo), e o artefato final no disco está de fato correto — conferi as dimensões da imagem para não aceitar isso de palavra. Bloquear a fase nele seria desproporcional ao objetivo, que é evidência de campo confiável e a calibração que sai dela. O que eu peço é menor e específico: que ele deixe de ser prosa de SUMMARY e vire um `todo`, porque prosa de SUMMARY é onde dívida vai para morrer sem barulho.

E o `mercado_templates_de_nome` continua vazio, como continuava antes. Reexaminei se a conclusão anterior ainda se sustenta agora que o resto da fase está completo, e sustenta-se melhor do que antes: a capacidade existe e grita quando não corta nada, o adiamento está registrado no próprio código, a Fase 2 tem um critério que o consome pelo nome, e — a novidade boa — `mercado_limiar_de_template` deixou de ser o `0.5` derivado de uma matriz vazia e voltou a ser `null`. Não há mais nenhum número inventado esperando a Fase 2 acreditar nele. Essa era a única parte do dano residual que me incomodava de verdade, e ela fechou sozinha, exatamente como o relatório anterior previu que fecharia.

**5 de 5. A fase pode fechar.**

---

_Verificado: 2026-08-29T21:36:10Z_
_Verificador: Claude (gsd-verifier) — suíte, os dois portões, o teste vermelho do firewall e o produtor de glifos ponta a ponta executados pelo próprio verificador; `.venv` e árvore de trabalho restaurados e conferidos_
