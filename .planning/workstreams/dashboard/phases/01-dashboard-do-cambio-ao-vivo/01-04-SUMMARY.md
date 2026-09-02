---
phase: 01-dashboard-do-cambio-ao-vivo
plan: 04
subsystem: ui
tags: [uplot, vendor, supply-chain, firewall, sha256, gitattributes, csp]

requires:
  - phase: 01-01
    provides: "l2scanner/recursos/dashboard/ e a constante CSP em dashboard.py (VEND-4, ja no tracer)"
provides:
  - "l2scanner/recursos/dashboard/vendor/uPlot.iife.min.js — uPlot 1.6.32, 51.081 bytes, MIT"
  - "l2scanner/recursos/dashboard/vendor/uPlot.min.css — a folha de estilo que uPlot exige, 1.857 bytes"
  - "l2scanner/recursos/dashboard/vendor/uPlot.LICENSE — o texto MIT ao lado do codigo"
  - "l2scanner/recursos/dashboard/vendor/README.md — VEND-1 (proveniencia com SHA-256 recalculado) e VEND-2 (revisao com contagem por primitiva)"
  - "l2scanner/recursos/dashboard/vendor/.gitattributes — `* -text`, o que mantem o hash estavel num clone novo"
  - "tests/test_firewall_dashboard.py — VEND-3: _primitivas_presentes, controle negativo, guarda de alcance, guarda contra vacuidade, TestNenhumaDependenciaNova"
affects: [01-05, 01-06, 01-07, 01-08]

actuals:
  tokens: 22994
  tasks: 3
  commits: 3

tech-stack:
  added:
    - "uPlot 1.6.32 (MIT) — ATIVO ESTATICO vendorizado, nao dependencia Python; requirements.txt intocado"
  patterns:
    - "Artefato de terceiro entra com hash RECALCULADO em disco, nunca copiado do documento de pesquisa"
    - "`.gitattributes` com `* -text` ao lado de qualquer arquivo cujo hash e guardado por teste"
    - "Guarda com ALCANCE explicito quando o documento que a regra manda escrever cita o que a regra proibe"
    - "Guarda contra VACUIDADE ao lado de toda varredura: enumerar zero arquivos tem de falhar, nao passar"

key-files:
  created:
    - l2scanner/recursos/dashboard/vendor/uPlot.iife.min.js
    - l2scanner/recursos/dashboard/vendor/uPlot.min.css
    - l2scanner/recursos/dashboard/vendor/uPlot.LICENSE
    - l2scanner/recursos/dashboard/vendor/README.md
    - l2scanner/recursos/dashboard/vendor/.gitattributes
    - tests/test_firewall_dashboard.py
  modified: []

key-decisions:
  - "O SHA-256 do .js recalculado em disco BATEU byte a byte com o da pesquisa (19c8d4c6...eb78f1f); o do .css nasce aqui, porque a pesquisa so mediu o content-length dele"
  - "`.gitattributes` com `* -text` acrescentado (Rule 2): medido `git ls-files --eol`, todo texto deste repo sai `w/crlf`; sem ele o guarda de hash quebraria num clone novo por motivo errado"
  - "A varredura enxerga so `.js`/`.css`/`.mjs`/`.cjs`/`.ts`; o README fica FORA por construcao, porque o VEND-2 exige que ele cite as primitivas pelo nome"
  - "O extrator de nome de distribuicao e IMPORTADO de test_firewall_escopo, nao reescrito — dois extratores discordando seria o buraco mais silencioso"
  - "uPlot NAO entra em requirements.txt: e ativo estatico servido ao navegador, e nenhum `import` Python o alcanca"

patterns-established:
  - "Prova viva registrada em duas metades: o arquivo ofensor entra (VERMELHO, com a saida colada), sai (VERDE) — e nao so a afirmacao de que quebraria"
  - "Refutacao com MEDICAO no lugar onde sera lida: a lista dos 9 eventos que uPlot registra mora no README do vendor, e nao so a conclusao `nao tem wheel`"

requirements-completed: [DASH-03]

coverage:
  - id: D1
    description: "uPlot 1.6.32 esta na arvore com licenca MIT ao lado, e o SHA-256 registrado no README bate com o do arquivo EM DISCO (VEND-1)"
    requirement: DASH-03
    verification:
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#test_o_sha256_do_README_bate_com_o_arquivo_EM_DISCO"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#test_o_README_nomeia_a_versao_e_uma_licenca_PERMISSIVA"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#test_o_texto_da_licenca_esta_na_arvore_e_NAO_esta_vazio"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#test_o_README_registra_a_proveniencia_BYTES_URL_e_DATA"
        status: pass
    human_judgment: false
  - id: D2
    description: "A revisao do fonte esta escrita com a contagem POR primitiva e por arquivo, e acompanha a banlist do proprio modulo de teste (VEND-2)"
    requirement: DASH-03
    verification:
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#test_o_README_registra_a_revisao_de_TODAS_as_primitivas"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#test_a_revisao_registra_o_VEREDITO_e_nao_so_a_tabela"
        status: pass
    human_judgment: false
  - id: D3
    description: "A refutacao do zoom por roda esta registrada com a MEDICAO (os 9 eventos que uPlot registra, zero `wheel`, zero `deltaY`), e nao so a conclusao"
    requirement: DASH-03
    verification:
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#test_a_revisao_registra_a_REFUTACAO_do_zoom_por_roda"
        status: pass
    human_judgment: false
  - id: D4
    description: "O firewall QUEBRA quando uma primitiva de rede aparece num arquivo de codigo vendorizado, e nao passa por vacuidade nem se auto-acusa pelo README (VEND-3)"
    requirement: DASH-03
    verification:
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#test_nenhum_arquivo_vendorizado_TRAZ_primitiva_de_rede"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#test_o_detector_ACUSA_uma_primitiva_de_rede_injetada"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#test_a_varredura_NAO_alcanca_o_README_que_CITA_as_primitivas"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#test_a_varredura_enumerou_ao_menos_UM_arquivo"
        status: pass
      - kind: integration
        ref: "prova viva: PROVA_TEMPORARIA.js com `fetch(` dentro do vendor -> `3 failed, 10 passed`; apagado -> `13 passed`"
        status: pass
    human_judgment: false
  - id: D5
    description: "`requirements.txt` nao ganhou linha nesta fase, preso por lista escrita a mao com controle negativo"
    requirement: DASH-03
    verification:
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#TestNenhumaDependenciaNova::test_o_requirements_nao_ganhou_linha_nesta_fase"
        status: pass
      - kind: unit
        ref: "tests/test_firewall_dashboard.py#TestNenhumaDependenciaNova::test_o_guarda_REPROVA_quando_uma_linha_NOVA_e_declarada"
        status: pass
      - kind: integration
        ref: "git diff --stat requirements.txt -> saida vazia"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-01
status: complete
---

# Phase 01 Plan 04: uPlot vendorizado com as tres provas Summary

**uPlot 1.6.32 (MIT, 52.938 bytes em dois arquivos) entrou na arvore com proveniencia conferivel por SHA-256 recalculado em disco, revisao de fonte registrada com contagem por primitiva — zero ocorrencias — e um firewall que provadamente QUEBRA, demonstrado nas duas metades: ofensor dentro deixa a suite em 3 failed, ofensor fora devolve 13 passed.**

## Performance

- **Duration:** 25 min
- **Tasks:** 3 de 3
- **Files modified:** 6 (todos criados)
- **Suite:** 4.530 passed, 25 skipped (era 4.517 depois do 01-01; +13 sao exatamente os testes novos)

## Accomplishments

- **A biblioteca entrou pelas quatro provas, nao por confianca.** VEND-1 e VEND-2 moram em `vendor/README.md` e sao conferidos por teste; VEND-3 e `tests/test_firewall_dashboard.py`; VEND-4 ja viajava desde o tracer.
- **O SHA-256 do `.js` recalculado nesta arvore bateu BYTE A BYTE com o registrado na pesquisa** — `19c8d4c6ad88929a79f4ae49d6f7161566dfd0ba3d15cc495e974f787eb78f1f`, e os 51.081 bytes tambem. O do `.css` nasce aqui, porque a pesquisa so tinha medido o `content-length` dele. Nenhuma divergencia a explicar; a tabela de conferencia esta no README de qualquer modo, para o caso de haver uma no futuro.
- **VEND-2 aprovou com zero ocorrencias em todas as 11 primitivas**, sobre os arquivos em disco. Nao houve `arquivo:linha` a registrar e **nao houve interrupcao para decisao do usuario** — o plano previa os dois caminhos e este foi o tomado.
- **O firewall foi demonstrado nas duas metades, e nao apenas afirmado.** Com um `.js` fabricado contendo `fetch(` dentro do `vendor/`: `3 failed, 10 passed`. Apagado: `13 passed`. As duas saidas estao coladas abaixo.
- **A suposicao do UI-SPEC sobre zoom por roda caiu, com a medicao no lugar onde sera lida.** Medido neste arquivo: `wheel` 0, `deltaY` 0, e a lista dos 9 eventos que uPlot de fato registra. Ha teste prendendo os dois lados — se o `.min.js` passar a registrar `wheel`, o teste cai e cobra a atualizacao do documento.
- **`requirements.txt` nao ganhou uma linha, e agora ha teste com controle negativo prendendo isso.**

## Task Commits

1. **Tarefa 1: VEND-1 — vendorizar e registrar proveniencia** — `28a1cd6` (feat)
2. **Tarefa 2: VEND-2 — ler o fonte e registrar a revisao** — `6061a84` (docs)
3. **Tarefa 3: VEND-3 — o teste que quebra** — `744fe80` (test)

## Files Created/Modified

**Criados**
- `l2scanner/recursos/dashboard/vendor/uPlot.iife.min.js` — 51.081 bytes, uPlot 1.6.32
- `l2scanner/recursos/dashboard/vendor/uPlot.min.css` — 1.857 bytes, a folha que uPlot exige
- `l2scanner/recursos/dashboard/vendor/uPlot.LICENSE` — 1.078 bytes, MIT, com `Copyright (c) 2022 Leon Sorokin`
- `l2scanner/recursos/dashboard/vendor/README.md` — VEND-1 (tabela de proveniencia, conferencia contra a pesquisa, nota do `.gitattributes`), VEND-2 (contagem por primitiva, a comparacao medida das tres candidatas, por que as tres camadas nao sao redundantes, a refutacao do zoom por roda), e o roteiro de atualizacao de versao
- `l2scanner/recursos/dashboard/vendor/.gitattributes` — `* -text`, com o motivo escrito dentro
- `tests/test_firewall_dashboard.py` — 13 testes; `PRIMITIVAS`, `_arquivos_de_codigo_do_vendor`, `_primitivas_presentes`, `_mensagem`, o controle negativo, o guarda de alcance, o guarda contra vacuidade e `TestNenhumaDependenciaNova`

**Alterados:** nenhum. Nenhum dos arquivos da cerca dura (`rastreador.py`, `visao.py`, `console.py`, `mercado_registro.py`, `mercado_analise.py`, `mercado_console.py`, `config.py`, `mercado_catalogo.py`, `requirements.txt`) foi tocado.

## A prova viva do VEND-3, nas duas metades

O criterio de aceitacao pedia as duas saidas registradas. Com
`vendor/PROVA_TEMPORARIA.js` contendo `!function(){fetch('https://exemplo.invalido/coleta');}();`:

```
FAILED tests/test_firewall_dashboard.py::test_o_sha256_do_README_bate_com_o_arquivo_EM_DISCO
FAILED tests/test_firewall_dashboard.py::test_o_README_registra_a_proveniencia_BYTES_URL_e_DATA
FAILED tests/test_firewall_dashboard.py::test_nenhum_arquivo_vendorizado_TRAZ_primitiva_de_rede
3 failed, 10 passed in 0.38s
```

A mensagem do terceiro, que e a do VEND-3:

```
AssertionError: PRIMITIVA DE REDE NO ARQUIVO VENDORIZADO: fetch( (encontrada em
l2scanner\recursos\dashboard\vendor\PROVA_TEMPORARIA.js).

Este arquivo e de TERCEIRO e executa no NAVEGADOR DO USUARIO, na mesma maquina em
que o jogo roda e na mesma arvore em que mora o `.env` com o token do Chatwoot.
[...] Ver a secao `Registry Safety` de .planning/workstreams/dashboard/phases/
01-dashboard-do-cambio-ao-vivo/01-UI-SPEC.md.
```

Apagado o arquivo:

```
13 passed in 0.05s
```

**O achado que valeu a pena:** o ofensor derrubou **tres** testes, e nao um. Os
guardas de VEND-1 tambem acusaram — um arquivo de codigo dentro do `vendor/` sem
hash nem tamanho registrados no README e, por si so, uma violacao de
proveniencia. Vendorizar por contrabando exige, alem de escapar da varredura de
primitivas, escrever o proprio hash no documento que denuncia a mudanca no diff.

## Decisions Made

- **`.gitattributes` com `* -text` na pasta do vendor** — a unica adicao fora da lista `files_modified` do plano, e a razao esta medida. `git config core.autocrlf` devolve `true` nesta maquina, e `git ls-files --eol` mostra `i/lf w/crlf` para **todo** arquivo de texto do repo (`requirements.txt`, `dashboard.py`, `dashboard.js`). Sem `-text`, o `.js` (2 LF) e a licenca (20 LF) seriam convertidos no checkout de um clone novo, o hash mudaria, e `test_o_sha256_do_README_bate_com_o_arquivo_EM_DISCO` ficaria vermelho numa arvore em que nada de errado aconteceu. O custo real nao seria o falso positivo: seria que uma troca **de verdade** (T-01-14) viraria indistinguivel do ruido de fim de linha, e o primeiro reflexo de quem visse o vermelho seria "e o CRLF de novo". Depois da adicao, `git ls-files --eol` mostra `attr/-text` e `w/lf` para os dois arquivos.
- **O alcance da varredura e por EXTENSAO, e o README fica fora por construcao.** A alternativa — varrer o diretorio inteiro e abrir excecao para `README.md` pelo nome — daria o mesmo resultado hoje e um resultado pior amanha, quando alguem acrescentasse um `NOTES.md`. O filtro positivo (`.js`, `.mjs`, `.cjs`, `.css`, `.ts`) descreve o que a regra realmente quer dizer: **codigo que executa**. O comentario no ponto do filtro explica o laco, e `test_a_varredura_NAO_alcanca_o_README_que_CITA_as_primitivas` prova que o filtro e load-bearing, exigindo que o README de fato dispararia o detector se estivesse ao alcance (`>= 5` primitivas presentes nele).
- **O extrator de nome de distribuicao e importado, nao reescrito.** `_nomes_declarados_no_requirements` vem de `tests/test_firewall_escopo.py`. Escrever um segundo com um `_FIM_DO_NOME` ligeiramente diferente seria a forma mais silenciosa de os dois firewalls passarem a discordar sobre o que e um nome de pacote — e o FIRE-01 ja pagou o preco de aprender as quatro sintaxes que o pip aceita.
- **A biblioteca vendorizada NAO entra em `DISTRIBUICOES_ANTES_DA_FASE_01_DASHBOARD`,** e a distincao esta escrita no comentario da constante: ela e um **ativo estatico servido ao navegador**, nao uma dependencia do interpretador. Nenhum `pip install` a traz, nenhum `import` a alcanca, e o `vigiar-party.bat` nao muda por causa dela. Foi exatamente por isso que a escolha da biblioteca pesou **bytes vendorizados** e nao peso de wheel.
- **O limite da varredura literal esta escrito no fonte, e nao escondido.** `_primitivas_presentes` nao ve `window["fet"+"ch"]` nem um nome ofuscado. Isso nao e descuido: e a razao de existirem tres camadas, e a tabela de "o que cada uma pega e o que cada uma nao pega" esta no README para que ninguem proponha trocar as tres por uma.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `.gitattributes` com `* -text` na pasta do vendor**
- **Found during:** Tarefa 1, ao conferir se o guarda de hash sobreviveria a um clone novo
- **Issue:** `core.autocrlf=true` nesta maquina. Medido com `git ls-files --eol`: `requirements.txt`, `l2scanner/dashboard.py` e `l2scanner/recursos/dashboard/dashboard.js` saem todos como `i/lf w/crlf` — a conversao **acontece**. O `uPlot.iife.min.js` tem 2 LF e o `uPlot.LICENSE` tem 20; num checkout novo os dois virariam CRLF, o SHA-256 mudaria, e VEND-1 — cuja funcao inteira e detectar a troca silenciosa do arquivo (T-01-14) — passaria a falhar por ruido de fim de linha. O modo de falha caro nao e o vermelho errado, e o vermelho **certo** virando indistinguivel dele.
- **Fix:** `l2scanner/recursos/dashboard/vendor/.gitattributes` com `* -text` e o motivo por extenso dentro do arquivo. Escopo minimo: a pasta do vendor, e nao a raiz do repo — nao ha razao para mexer na convencao de fim de linha de nenhum outro arquivo, e um `.gitattributes` na raiz colidiria com o que os planos irmaos 01-02 e 01-03 estao fazendo.
- **Files modified:** `l2scanner/recursos/dashboard/vendor/.gitattributes` (criado)
- **Verification:** `git ls-files --eol l2scanner/recursos/dashboard/vendor/` -> `attr/-text` e `w/lf` nos arquivos vendorizados, contra `attr/` e `w/crlf` no resto do repo. A tabela lado a lado esta no README.
- **Committed in:** `28a1cd6` (commit da Tarefa 1)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Sem scope creep. O acrescimo e uma exigencia de corretude do proprio VEND-1 — sem ele a prova de proveniencia nao sobrevive a um `git clone`. Um arquivo novo, 21 linhas, dentro da pasta que o plano ja possui, sem tocar nada da cerca dura.

## Issues Encountered

- **O `-k "proveniencia or sha"` do plano selecionava um unico teste.** O nome `test_o_README_registra_os_BYTES_e_a_URL_de_cada_arquivo` nao continha nenhuma das duas palavras, entao o portao da Tarefa 1 cobrava menos do que o criterio de aceitacao dela pedia. Renomeado para `test_o_README_registra_a_proveniencia_BYTES_URL_e_DATA`; o seletor passou a pegar 2 de 4. Nao e deviation — e o nome do teste alinhado ao portao que o plano escreveu.
- **Uma rodada de `pytest tests/` foi interrompida por `KeyboardInterrupt` em `tests/test_agenda.py:1231`.** Nao e falha de teste: aquele teste **levanta `KeyboardInterrupt` de proposito** (e o jeito de fazer `laco_da_agenda` dar uma volta so), e a interrupcao veio de fora, do ambiente. `python -m pytest tests/test_agenda.py -q` isolado -> `145 passed`, e a re-execucao da suite completa -> `4.530 passed`. Registrado para ninguem gastar tempo caçando um fantasma.
- **O shell desta maquina recusa heredocs longos com URL e caminho dentro** (a mesma familia do problema de codificacao que o 01-01 registrou). As edicoes grandes de texto foram feitas pelas ferramentas de edicao, com `encoding="utf-8"` explicito. O `vendor/README.md` foi escrito em **ASCII puro de proposito**, e o motivo esta dito no proprio documento: um arquivo cujo unico proposito e ser conferido byte a byte nao pode depender de sorte de codificacao.

## User Setup Required

None — nenhuma configuracao de servico externo. O download da biblioteca ja foi feito e os arquivos estao versionados.

## Next Phase Readiness

**Pronto para os planos seguintes:**
- **01-06 / 01-07 (o grafico):** `uPlot.iife.min.js` e `uPlot.min.css` estao na arvore e podem ser servidos por `PASTA_DOS_ESTATICOS`. Como o build e **IIFE**, o global `uPlot` fica disponivel sem `type="module"` — compativel com `script-src 'self'` sem nenhuma diretiva nova.
- **01-05 (endpoint e cabecalho):** VEND-4 continua sendo a prova daquele plano; as outras tres ja estao fechadas aqui.

**O que o proximo planejador precisa saber:**
- **NAO ha zoom por roda do mouse, e isso e medido, nao suposto.** Zero listeners de `wheel`, zero `deltaY`. O plano 01-07 escreve as ~30 linhas de `over.addEventListener("wheel", ...)` pela API de hooks. O zoom por **arrasto de selecao** (box zoom com rescale) e nativo e cobre o caso principal; o botao `Ver todo o periodo` ja esta especificado.
- **Ha um teste prendendo essa ausencia dos dois lados.** Se uma atualizacao de versao trouxer `wheel`, `test_a_revisao_registra_a_REFUTACAO_do_zoom_por_roda` cai e cobra que o README e o codigo do 01-07 sejam reconciliados. Isso e intencional.
- **Atualizar a versao da biblioteca tem um roteiro de 5 passos escrito no `vendor/README.md`.** Pular qualquer um deixa a suite vermelha no hash — e a mensagem de falha diz exatamente isso.
- **Sao DOIS arquivos, sempre.** `test_a_varredura_enumerou_ao_menos_UM_arquivo` exige `len(arquivos) >= 2`: se alguem trocar por uma biblioteca de arquivo unico, esse piso precisa mudar junto, de propósito.

## Known Stubs

Nenhum stub. Os artefatos vendorizados sao os arquivos reais baixados da origem registrada, com hash conferido; nao ha placeholder, arquivo vazio nem hash inventado. O `vendor/README.md` nao contem nenhum campo por preencher — os tres caminhos que o plano previa como possiveis pendencias (divergencia de hash a explicar, ocorrencia de primitiva a revisar, interrupcao para decisao do usuario) **nao ocorreram**, e o README diz isso por extenso em vez de omitir.

## Self-Check: PASSED

- **Arquivos criados:** os 6 artefatos conferidos no disco — todos presentes e nao vazios.
- **Commits:** `28a1cd6`, `6061a84` e `744fe80` conferidos no `git log`.
- **Sem delecoes:** `git diff --stat` contra a base — **807 insertions(+), 0 deletions**, 6 arquivos, todos novos.
- **Suite:** `python -m pytest tests/ -q` -> **4.530 passed, 25 skipped**, 0 falhas (4.517 era o numero depois do 01-01; +13 sao exatamente os testes deste plano).
- **`tests/test_firewall_dashboard.py`:** 13 testes coletados (o criterio pedia >= 8), todos verdes.
- **`requirements.txt`:** `git diff --stat requirements.txt` -> saida vazia.
- **Cerca dura de escopo:** nenhum dos oito arquivos proibidos aparece no `git diff --stat` contra a base.
- **Sem rastro da prova viva:** `git status --short` limpo depois de apagar `PROVA_TEMPORARIA.js` — nenhum `git clean` foi usado em momento algum.

---
*Phase: 01-dashboard-do-cambio-ao-vivo*
*Completed: 2026-09-01*
