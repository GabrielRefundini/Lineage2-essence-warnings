---
phase: 01-reconhecimento-preciso-e-lista-de-bosses-no-config
workstream: tiat
verified: 2026-08-30T15:35:00Z
status: gaps_found
score: 8/9 must-haves verificados
behavior_unverified: 0
overrides_applied: 0
ambiente_de_teste: ".venv/Scripts/python.exe com PYTHONPATH apontando para o site-packages do Python 3.12 do sistema (pytest 9.1.1). O .venv NAO tem pytest e o Python do sistema NAO tem as bindings WinRT; a combinacao e a unica em que ocr.disponivel() == True E o pytest existe. Confirmado: ocr True / pytest 9.1.1 / numpy 2.5.2 / cv2 4.14.0 nos dois lados."
gaps:
  - truth: "KEY LINK 01-04: `PNG ou pasta de gravacao -> recorte por calibracao.tiat_chat -> ocr.ler_texto -> bosses.padrao_do_anuncio -> veredito`"
    status: failed
    reason: >-
      `regiao_da_calibracao` subtrai a origem da janela de `cal.tiat_chat` com base
      numa premissa FALSA, escrita na propria docstring: "A calibracao guarda
      tiat_chat em coordenadas de DESKTOP". Medido: ela guarda em coordenadas de
      JANELA. `calibrar_tiat` captura o frame COMPLETO da janela
      (`JanelaSource(alvo, Regiao(0,0,1,1)).capturar_completo()`) e roda
      `_selecionar_regiao` sobre ele, e a producao recorta com
      `_extra_para_janela` no ramo `relativa=True` (porque `laco_principal` passa
      `relativa=cal.party_window_na_janela is not None`, e ele existe), usando
      `extra.esquerda` CRU. A subtracao e um deslocamento a mais.
      Prova de campo, no `calibration.json` real desta maquina:
      origem = party_window(1737,325) - party_window_na_janela(17,325) = (1720,0);
      tiat_chat.esquerda = 8; 8 - 1720 = -1712 -> a ferramenta recusa a imagem
      inteira e sai com codigo 1. Com o MESMO retangulo usado CRU
      (`--recorte 8 878 625 455`) ela le o chat e casa `Tiat North` no
      frame_000030 daquela gravacao. O retangulo `20 880 600 470` que a varredura
      de 01-04 achou "a olho" e praticamente o proprio `tiat_chat`, o que confirma
      o espaco de coordenadas por um segundo caminho.
    artifacts:
      - path: "tools/conferir_anuncio_de_boss.py"
        issue: "`regiao_da_calibracao` (linhas ~420-460) subtrai `ox`/`oy` de um retangulo que ja esta em coordenadas de janela; a docstring afirma o contrario do que o codigo de producao faz."
      - path: "tests/test_conferir_anuncio_de_boss.py"
        issue: "So o ramo de RECUSA tem teste (`test_sem_calibracao_e_sem_recorte_devolve_1_dizendo_onde_olhar`). A aritmetica da origem tem ZERO cobertura — foi por isso que o defeito atravessou."
    missing:
      - "Usar `cal.tiat_chat` / `cal.tiat_alvo` CRUS quando a imagem e um frame de janela (que e o que o `gravador` grava), e corrigir a docstring que afirma coordenadas de desktop."
      - "Um teste que case o retangulo devolvido contra o `calibration.json` REAL do repositorio (que hoje tem os dois campos preenchidos), e nao so contra o ramo de recusa."
      - "Se o caminho de desktop precisar continuar existindo, ele tem de ser escolhido por um sinal explicito (o `relativa` da producao), nunca presumido."
deferred: []
behavior_unverified_items: []
coincidental_reliance_items: []
human_verification:
  - test: "Com o jogo aberto, rodar `calibrar-tiat.bat` e marcar as duas regioes."
    expected: >-
      A ferramenta pede 1/2 (CHAT) e 2/2 (ALVO), as janelas de selecao se chamam
      'Regiao do chat' e 'Regiao do alvo', nenhum texto na tela nomeia um mob, a
      imagem de conferencia sai com os rotulos CHAT (amarelo) e ALVO (verde), e o
      `calibration.json` recebe `tiat_chat` e `tiat_alvo`.
    why_human: >-
      E um caminho interativo que abre janelas do OpenCV, exige arrastar o mouse
      sobre a janela do jogo e ESCREVE no `calibration.json`. Nenhum teste da suite
      o exercita e nenhum poderia sem o jogo aberto. O diff da fase mostra que so
      literais de texto mudaram dentro de `calibrar_tiat` — as duas chamadas de
      `_selecionar_regiao` e as duas gravacoes estao intactas — mas isso e leitura
      de codigo, nao execucao.
  - test: "Depois de calibrar, rodar `tools/conferir_anuncio_de_boss.py <gravacao> --regiao chat` SEM `--recorte`."
    expected: "O recorte deve cair sobre o chat e o texto cru deve sair legivel."
    why_human: >-
      E a confirmacao final do gap acima depois da correcao. Hoje esse comando
      recusa a imagem inteira nesta maquina.
---

# Fase 1 (tiat): Reconhecimento preciso e lista de bosses no config — Relatorio de Verificacao

**Objetivo da fase:** O alerta de boss raro so sai quando o servidor anunciou um nascimento, nomeia qual dos bosses nasceu, e quem e vigiado passa a ser uma linha do `config.toml` em vez de uma constante no codigo.

**Verificado:** 2026-08-30
**Status:** `gaps_found`
**Re-verificacao:** Nao — verificacao inicial.

**Veredito em uma linha:** os **8 criterios de sucesso do ROADMAP sao VERDADE**, e cada um foi confirmado executando codigo de producao, nao lendo SUMMARY. O gap unico esta fora deles: uma aritmetica de coordenadas errada na ferramenta de diagnostico criada em `01-04` — exatamente a aritmetica que o proprio `01-04-SUMMARY.md` declarou, honestamente, como nunca confirmada contra dado real. Confirmei contra dado real, e ela esta errada.

---

## Achievement do Objetivo

### Verdades Observaveis (os 8 criterios do ROADMAP)

| # | Criterio | Status | Evidencia (executada) |
|---|---|---|---|
| 1 | `Fulano: tiat ja nasceu?` nao gera alerta; `Tiat North [Lv. 80] has spawned!` gera um cuja mensagem contem `Tiat North`; trocando por `South`, contem `Tiat South` — RECO-01, RECO-02 | VERIFICADO | `VigiaDeBosses` + `ler_bosses(config.toml)` reais: negativo `[]`; `Tiat North [Lv. 60/80]` -> `Tiat North nasceu! (visto no chat do jogo)`; `South` -> `Tiat South nasceu! ...`. Os dois negativos NOVOS do `01-EVIDENCIA` (`-> Dragon Belt ... [15,54 XM Coin]` e `Christine : ... LVL 62`) tambem devolveram `[]`. |
| 2 | Chat mudo e alvo lido como `Tiat South` gera alerta que identifica o boss PELO ALVO, caminho proprio — RECO-03 | VERIFICADO | `avaliar(chat=None/"" , alvo="Tiat South")` -> `[('Tiat South','alvo','Tiat South nasceu! (seu alvo virou Tiat South)')]`. Independe do chat: o laco de `avaliar` calcula `no_alvo` sem consultar `no_chat`. |
| 3 | `T1a7 Nor7h [Lv. 8O] has spawned!` produz o MESMO alerta e o MESMO boss; os dois sentidos vivem no mesmo conjunto de testes — RECO-04, RECO-01 | VERIFICADO | Executado: a frase degradada -> `Tiat North`. **Provado por MUTACAO** (secao "Prova por mutacao" abaixo): apertar o padrao deixa VERMELHO o lado positivo, afrouxa-lo deixa VERMELHO o lado negativo, e ambos moram em `tests/test_bosses.py`. |
| 4 | Mesmo boss no chat e no alvo = UMA mensagem; bosses diferentes = DOIS alertas; o rearme e por boss e o `Tiat South` alvejado nao e engolido — RECO-05 | VERIFICADO | Executado, nos dois sentidos: mesmo boss -> `[('Tiat North','chat_e_alvo')]`; diferentes -> `[('Tiat North','chat'),('Tiat South','alvo')]`; South alvejado enquanto o anuncio de North PERSISTE no chat -> `[('Tiat South','alvo')]` (nao engolido) e nada no tick seguinte. Rearme por boss e "uma falha isolada nao rearma" tambem executados. |
| 5 | Um `[[boss]]` novo faz o scanner vigiar aquele mob sem NENHUMA alteracao em `.py`; o Tiat entra com 6 e 8 — VIGI-01, VIGI-02 | VERIFICADO | Boss INVENTADO (`Grendizer Vermelho`, 3/4.5h) num `config.toml` temporario: anuncio dispara, alvo dispara, e o anuncio do Tiat (fora daquela lista) NAO dispara. `git grep -i Grendizer -- '*.py'` = vazio. O `config.toml` do repositorio le `[('Tiat North',6.0,8.0),('Tiat South',6.0,8.0)]`. |
| 6 | Bloco torto derruba o arranque citando o boss e o campo, no formato de `_evento_de_dict` — VIGI-03 | VERIFICADO | 9 formas de bloco torto, todas recusadas com o boss e o campo nomeados. E **ponta a ponta, sem stub**: `config.toml` real com `max<min` -> `main()` devolveu **2** e imprimiu UMA linha de erro, sem traceback. |
| 7 | Sem nenhum `[[boss]]`, o scanner SOBE e o console diz que a vigilancia esta desligada e como liga-la; arquivo ausente tambem nao e erro — VIGI-04 | VERIFICADO | `ler_bosses` devolve `[]` para secao ausente E para arquivo ausente. `main()` com um `config.toml` sem `[[boss]]` rodou o replay inteiro e devolveu **0**, tendo logado em `INFO`: "Vigilancia de boss desligada: nao ha nenhum bloco [[boss]] ... acrescente um bloco com 'nome', 'respawn_horas_min' e 'respawn_horas_max'." |
| 8 | `calibrar-tiat.bat` continua marcando as duas regioes e nem ele nem o texto que imprime nomeiam um mob — OPER-01 | VERIFICADO | Guarda AST re-medido contra o fonte PRE-FASE: **11 acusacoes**, todas pelo token curto, nenhuma pelos nomes completos (secao propria abaixo). Contra o estado de hoje: **0** acusacoes nos dois arquivos, e `"qualquer boss"` presente nos literais. A metade "continua marcando as duas regioes" tem diff so de literais e esta na lista de verificacao humana. |
| 9 | **KEY LINK 01-04:** recorte derivado de `calibracao.tiat_chat` -> OCR -> veredito | **FALHOU** | `regiao_da_calibracao` desloca o retangulo por uma origem que nao deve ser aplicada. Ver "Gaps". |

**Score:** 8/9 must-haves verificados (os 8 criterios do ROADMAP, todos VERDES; 1 key link de plano QUEBRADO).

### A varredura de campo de 01-04 — REPRODUZIDA, numero por numero

Rodei eu mesmo, no `.venv`, sobre o `recordings/` real:

```
.venv/Scripts/python.exe tools/conferir_anuncio_de_boss.py recordings \
    --regiao chat --recorte 20 880 600 470
```

| Medida | 01-04-SUMMARY afirma | Eu medi | |
|---|---|---|---|
| Frames varridos | 2.110 | **2.110** | bate |
| Passadas de OCR | 4.220 | **4.220** | bate |
| Passadas sem texto nenhum | 6 | **6** | bate |
| Frames com casamento de ANUNCIO | 36 | **36** | bate |
| Passadas com casamento | 72 (as duas escalas concordaram) | **72** (72/36 = 2 -> as duas escalas em TODOS) | bate |
| Frames de chat real SEM casamento | 2.074 | **2.074** (2110 - 36) | bate |
| Casamentos de `Tiat South` | 0 | **0** | bate |
| Anuncio no texto CRU e padrao NAO casou | 0 | **0** (contadas 72 passadas com a frase no cru, 72 com veredito SIM) | bate |
| Frames casados, contiguos | `000011`..`000046` | **`000011`..`000046`, sem buraco** (verificado por diferenca sucessiva) | bate |
| Codigo de saida | 0 | **0** | bate |

**R-01 esta FECHADO.** A frase `<Nome> [Lv. NN] has spawned!` deixou de ser assercao do usuario: ela atravessou o pipeline de OCR deste projeto, em pixels gravados numa sessao de farm real de 2026-08-28, e o padrao do `01-01` a reconheceu em 36 frames seguidos nas duas escalas. **R-02 tambem esta fechado no sentido que importa:** 2.074 frames de chat de jogador de verdade (recrutamento, futebol, cafe, mercado) e ZERO falso positivo, com ZERO falso negativo.

O tempo total da varredura foi ~9 minutos; ela e o unico item caro desta verificacao.

### O guarda de OPER-01 — RE-MEDIDO contra o fonte pre-fase

Importei o proprio detector do teste (`termos_procurados`, `literais_da_funcao`, `acusacoes`) e o apontei para `git show 26cc059b:l2scanner/calibrar.py` e `git show 26cc059b:calibrar-tiat.bat`.

| Fonte | Acusacoes com os termos REAIS | Acusacoes so com os nomes COMPLETOS |
|---|---|---|
| `l2scanner/calibrar.py` PRE-FASE | **8** (todas por `tiat`) | **0** |
| `calibrar-tiat.bat` PRE-FASE | **3** (todas por `tiat`) | **0** |
| **Total** | **11** | **0** |
| `l2scanner/calibrar.py` HOJE | **0** | — |
| `calibrar-tiat.bat` HOJE | **0** | — |

A afirmacao do `01-02-PLAN` reproduz exatamente: **11 acusacoes, todas pelo token curto `tiat`, nenhuma pelos nomes completos**. As 8 do `.py` sao a docstring, o `1/2 - marque ... de Tiat.`, `Tiat: chat`, `Tiat: alvo`, `TIAT CHAT`, `TIAT ALVO`, `Aviso de Tiat calibrado para `, e `Nao sei qual janela ... para o Tiat.`. Um guarda so com `{'tiat north','tiat south'}` teria ficado **VERDE sobre todas as 11** — o guarda nao e decorativo, e o proprio arquivo prova isso com `test_um_conjunto_so_com_nomes_completos_ficaria_cego`.

### Prova por mutacao — RECO-01 morde nas DUAS direcoes

Sem tocar no repositorio: substitui `l2scanner.bosses.padrao_do_anuncio` em memoria e rodei `tests/test_bosses.py` + `tests/test_sessao.py`.

| Mutacao | Direcao | Resultado | Testes que ficaram VERMELHOS |
|---|---|---|---|
| (nenhuma) | — | 0 falhas | — |
| Exigir o `!` final | APERTA | 2 falhas | `test_a_frase_sem_a_exclamacao_dispara` |
| Ancorar em `^` | APERTA | 3 falhas | `test_lixo_do_icone_no_comeco_da_linha_nao_impede_o_casamento` + 2 |
| Nivel com `\d+` | APERTA | 6 falhas | `test_o_nivel_nao_entra_na_identidade[8O]`, `[l00]`, `test_a_letra_O_no_lugar_do_zero_nao_muda_nada`, `test_o_south_torto_continua_sendo_o_south`, `test_trocas_classicas_do_ocr_ainda_encontram_o_nome` |
| So o nome (curinga parcial) | AFROUXA | 4 falhas | `test_nome_solto_no_chat_sem_a_frase_nao_dispara`, `test_o_nome_e_o_nivel_sem_has_spawned_nao_disparam`, ... |
| **O gatilho EXATO da v1** (`t[i1l][a4@][t7]`) | AFROUXA | **34 falhas** | inclui `test_pergunta_digitada_por_jogador_nao_dispara` e os tres testes do seam em `tests/test_sessao.py` |

**A tolerancia do nivel aceita LETRA, e nao ha `\d+` no fonte.** `grep '\\d'` em `l2scanner/bosses.py` acha o padrao apenas em COMENTARIO, explicando por que ele seria um defeito. A classe real e `_DIGITO_COM_FOLGA = "0123456789OoQDlI|iSsZzBbgGAa"`, e a mutacao acima mostra que troca-la por `\d+` reprova em `[Lv. 8O]` e em `[Lv. l00]`.

### Artefatos exigidos

| Artefato | Esperado | Status | Detalhes |
|---|---|---|---|
| `l2scanner/bosses.py` | O vigia, os padroes, `Boss`, `BossInvalido` | VERIFICADO | 394 linhas, importado por `config.py`, `__main__.py`, `sessao.py`, `tools/conferir_anuncio_de_boss.py`. So stdlib — a direcao de importacao alegada e real. |
| `l2scanner/config.py::ler_bosses` / `_boss_de_dict` / `_horas_de_respawn` / `_recusar_bosses_repetidos` | Leitura e validacao | VERIFICADO | Executado contra 9 formas tortas + 3 formas validas. |
| `l2scanner/__main__.py::montar_vigia_de_bosses` | Degradacao com log | VERIFICADO | As 4 recusas exercitadas (lista vazia / sem recorte / sem `--janela` / sem OCR) e o caminho feliz. |
| `config.toml` | Dois `[[boss]]` do Tiat com 6 e 8 | VERIFICADO | Lidos pelo `ler_bosses` real. |
| `tests/test_bosses.py` | A matriz dos 8 criterios | VERIFICADO | 1183 linhas; os **7 nomes de teste** do `test_tiat.py` antigo sobreviveram TODOS (conferido nome a nome contra `git show 26cc059b:tests/test_tiat.py`), com a aritmetica de debounce byte a byte (`range(3)`, `range(4)`, `[True, False, False, True]`). |
| `tests/test_calibracao_generica.py` | O guarda de OPER-01 | VERIFICADO | 296 linhas; re-medido acima. |
| `tools/conferir_anuncio_de_boss.py` | A ferramenta de confronto | PARCIAL | Funciona e fechou R-01 pelo caminho `--recorte`; o caminho `--regiao` derivado da calibracao esta quebrado (gap). |
| `tests/test_conferir_anuncio_de_boss.py` | A regua da ferramenta | VERIFICADO com lacuna | 120 testes verdes no conjunto; a aritmetica da origem nao tem NENHUM teste. |
| `l2scanner/tiat.py`, `tests/test_tiat.py` | Removidos pelo renomeio | VERIFICADO | Nao existem. `VigiaDoTiat` e `montar_vigia_do_tiat` nao aparecem em nenhum fonte (so na assercao que os proibe). |

### Verificacao dos Key Links

| De | Para | Via | Status |
|---|---|---|---|
| `config.toml` | `config.ler_bosses` | `tomllib` + `_boss_de_dict` | WIRED (executado) |
| `ler_bosses` | `bosses.VigiaDeBosses` | `montar_vigia_de_bosses(bosses=...)`, padroes pre-compilados no `__init__` | WIRED (executado) |
| `VigiaDeBosses` | `sessao._processar_bosses` | `Sessao(bosses=...)` -> `avaliar` -> laco sobre a LISTA | WIRED (executado; `tests/test_sessao.py::TestOSeamDosBosses`) |
| `_processar_bosses` | `_despachar(Categoria.SEMPRE)` | um `_despachar` por aviso da lista | WIRED |
| `__main__.laco_principal` | `ler_bosses()` | chamada direta na montagem | WIRED (provado ponta a ponta: `config.toml` torto -> codigo 2) |
| `cal.tiat_chat`/`tiat_alvo` | `frame.extras['tiat_chat'|'tiat_alvo']` | `extras` -> `JanelaSource(relativa=True)._extra_para_janela` / `MssSource` | WIRED |
| `calibrar-tiat.bat` | `calibrar_tiat()` | `-m l2scanner.calibrar --tiat` | WIRED (leitura de codigo; execucao interativa vai para verificacao humana) |
| `bosses.padrao_do_anuncio` | `tools/conferir_anuncio_de_boss.py` | import, sem regex propria | WIRED (`test_a_ferramenta_nao_escreve_expressao_regular_propria`) |
| **`calibracao.tiat_chat`** | **recorte da ferramenta** | **`regiao_da_calibracao`** | **NOT_WIRED — ver Gaps** |

### Cobertura de Requisitos

| Requisito | Planos | Status | Evidencia |
|---|---|---|---|
| RECO-01 | 01-01, 01-03, 01-04 | SATISFEITO | Negativos executados + mutacao nas duas direcoes + 2.074 frames de campo com zero falso positivo |
| RECO-02 | 01-01, 01-03 | SATISFEITO | North/South distintos; o nome da mensagem vem do `[[boss]]`, nunca do OCR |
| RECO-03 | 01-03 | SATISFEITO | Caminho do alvo proprio; desempate por SPAN devolve silencio no empate |
| RECO-04 | 01-01, 01-03, 01-04 | SATISFEITO | `T1a7 Nor7h [Lv. 8O]` casa; a folga vale para a parte fixa tambem |
| RECO-05 | 01-01, 01-03 | SATISFEITO | Um alerta no mesmo boss; dois em bosses diferentes; rearme por boss |
| VIGI-01 | 01-01, 01-03, 01-04 | SATISFEITO | Boss inventado vigiado sem `.py` tocado |
| VIGI-02 | 01-01, 01-03, 01-04 | SATISFEITO | `nome` + `respawn_horas_min/max`; Tiat com 6 e 8 |
| VIGI-03 | 01-03 | SATISFEITO | 9 recusas nomeando boss e campo; `main()` devolve 2 ponta a ponta |
| VIGI-04 | 01-01, 01-03, 01-04 | SATISFEITO | Lista vazia e arquivo ausente sobem; `INFO` diz como ligar |
| OPER-01 | 01-02, 01-04 | SATISFEITO | Guarda AST VERMELHO no pre-fase (11), VERDE hoje (0) |

Nenhum requisito orfao: o ROADMAP mapeia 10 para a Fase 1 e os 4 planos reivindicam exatamente esses 10.

### Cobertura de Decisoes (CONTEXT)

| Decisao | Honrada? | Onde |
|---|---|---|
| Frase com FOLGA na parte fixa; `!` opcional | SIM | `Tiat South Lv 60 has spawned` (sem `!`, sem colchete) dispara |
| Identidade vem do config, procurada logo antes de `[Lv.` | SIM | `padrao_do_anuncio` concatena `nome` + `\s*` + colchete opcional + `Lv` |
| O nivel entra no padrao e sai da decisao | SIM | Lv 1 / 60 / 80 / 8O / l00 produzem o mesmo boss; o nivel nao vai para a mensagem |
| Modulo renomeado para `bosses.py` com `VigiaDeBosses`; os 7 testes migram | SIM, com o desvio de D-12 ja declarado no ROADMAP | 7 nomes intactos, aritmetica intacta; o desvio adicional (`bosses=(NORTH,)` na construcao direta) FORTALECE a assercao — sem ele o teste passaria com o `except` apagado |
| Dois blocos, nao um com lista | SIM | `config.toml` |
| A mensagem comeca pelo nome do boss | SIM | `Tiat North nasceu! (visto no chat do jogo)` |

### Spot-checks comportamentais

| Comportamento | Comando | Resultado | Status |
|---|---|---|---|
| Suite completa | `pytest -q -p no:randomly` (venv + pytest do sistema) | 40 failed, **2330 passed**, 0 skipped | PASS (falhas alheias, ver abaixo) |
| Arquivos da fase | `pytest tests/test_bosses.py test_calibracao_generica.py test_conferir_anuncio_de_boss.py test_sessao.py test_presenca.py` | **317 passed** | PASS |
| VIGI-03 ponta a ponta | `main()` com `config.toml` `max<min` | codigo **2**, 1 linha de erro | PASS |
| VIGI-04 ponta a ponta | `main()` com `config.toml` sem `[[boss]]` | codigo **0**, log `INFO` | PASS |
| Contrato de codigo de saida da ferramenta | recorte fora da imagem vs. recorte valido | **1** vs. **0** | PASS (T-04-02 mitigado) |
| Varredura de campo | `conferir_anuncio_de_boss.py recordings ...` | 2110/4220/72/0 | PASS |

**Atribuicao das 40 falhas — confirmada por mim, nao aceita de terceiros.** Todas as 40 estao em `tests/test_mercado_leitura.py` (36) e `tests/test_mercado_pagina.py` (4). `git log 26cc059b..HEAD -- <arquivos de mercado>` lista **so** commits `02-06`/`02-07` do workstream **mercado** (`d3fb336`, `d8c4711`, `e0e0083`, `af4635b`, `d20373d`) — nenhum commit `01-xx` do tiat toca esses arquivos. Alem disso `git status` mostra `l2scanner/mercado_leitura.py`, `mercado_pagina.py` e `test_mercado_leitura.py` MODIFICADOS na arvore de trabalho pelo agente que esta trabalhando em mercado agora; os erros sao `TypeError: int() argument ... not 'NoneType'` e `AttributeError: 'NoneType' has no attribute 'linhas'`, consistentes com um parametro obrigatorio recem-introduzido e uma edicao em curso. **EXCLUIDAS deste veredito. Nao toquei nesses arquivos.**
**Correcao ao briefing:** o teste nomeado no briefing (`test_medir_brilho_da_quantidade.py::TestOCensoEIMPORTADOENaoCOPIADO::test_o_censo_e_o_MESMO_OBJETO_de_medir_oclusao`) **passa** neste momento; o conjunto de falhas de mercado cresceu de 1 para 40 desde o briefing, mas continua inteiramente dentro de mercado.

### Auditoria de qualidade dos testes

| Arquivo | Requisitos ligados | Ativos | Pulados | Circular | Nivel de assercao | Veredito |
|---|---|---|---|---|---|---|
| `tests/test_bosses.py` | RECO-01..05, VIGI-01..04 | 100 | 0 | Nao | Comportamental (o vigia real, entrada -> lista de avisos) | OK |
| `tests/test_calibracao_generica.py` | OPER-01 | 11 | 0 (2 `pytest.skip` condicionais que NAO disparam — o `config.toml` tem bosses) | Nao | Valor (acusacoes concretas) + prova-vazia nas duas direcoes | OK |
| `tests/test_conferir_anuncio_de_boss.py` | RECO-01, RECO-04 | 9 (dos 120 do conjunto) | 0 | Nao | Valor + codigo de saida | **LACUNA**: a aritmetica de `regiao_da_calibracao` nao tem teste |
| `tests/test_sessao.py::TestOSeamDosBosses` | RECO-05 | 6 | 0 | Nao | Comportamental (despachos reais) | OK |
| `tests/test_presenca.py::TestSemRelogioProprio` | OPER-03 (antecipado) | 4 modulos | 0 | Nao | AST | OK — `bosses.py` entrou na tupla e o portao esta verde |

- **Testes desabilitados sobre requisito:** 0. A suite completa reportou **0 skipped**.
- **Padroes circulares:** 0. Os valores esperados da fase vem de (a) strings escritas a mao a partir do print do usuario, (b) do `config.toml` do repositorio, (c) de pixels gravados em campo em 2026-08-28 — nunca da saida do proprio sistema.
- **Assercoes insuficientes:** 1 lacuna (a origem da calibracao), ja contada como gap.

### Anti-padroes encontrados

| Arquivo | Linha | Padrao | Severidade | Impacto |
|---|---|---|---|---|
| — | — | — | — | Nenhum. `grep -E "TBD\|FIXME\|XXX\|HACK\|PLACEHOLDER\|TODO"` nos arquivos da fase so acha `TODOS`/`TODO comando` em portugues (`TODOS_OS_DIAS`, "TODO comando, inclusive /corrigir"), que nao sao marcadores de divida. Zero `return None` de stub, zero dado codificado chegando a saida. |

### Verificacao humana necessaria

Ver o bloco `human_verification` no frontmatter. Sao **2** itens, os dois genuinamente humanos (janela interativa do OpenCV sobre o jogo aberto), nenhum inventado.

---

## Gaps — o que falta e por que

### G-01 — A ferramenta de conferencia desloca o retangulo da calibracao por uma origem que nao existe

O `01-04-SUMMARY.md` registrou, com honestidade que merece ser dita em voz alta:

> "o caminho `regiao_da_calibracao` ... **nao foi exercitado contra dado real**. Ele tem teste unitario do ramo de recusa, mas a aritmetica da origem so sera confirmada quando alguem rodar `calibrar-tiat.bat`."

**Alguem rodou.** O `calibration.json` do checkout principal, modificado hoje as 14:27, tem `tiat_chat = (8, 878, 625, 455)` e `tiat_alvo = (350, 772, 160, 24)`. Exercitei o caminho, e a aritmetica esta errada.

A cadeia da medida:

1. `party_window = (1737, 325)` e `party_window_na_janela = (17, 325)` -> a ferramenta calcula origem `(1720, 0)`.
2. `tiat_chat.esquerda = 8`; `8 - 1720 = -1712`. A ferramenta recusa a imagem inteira: *"o recorte pedido nao cabe"*, e sai com **codigo 1**.
3. Usado **CRU** (`--recorte 8 878 625 455`), o mesmo retangulo le o chat do `frame_000030` e casa `Tiat North [Lv. 60] has spawned!`.
4. A producao concorda com (3): `laco_principal` constroi `JanelaSource(..., relativa=cal.party_window_na_janela is not None)`, que aqui e `True`, e `_extra_para_janela` no ramo `relativa` usa `extra.esquerda` **sem subtrair nada**.
5. `calibrar_tiat` concorda com (3) e (4): ele captura o frame COMPLETO da janela e roda `_selecionar_regiao` sobre ele — o retangulo nasce em coordenadas de JANELA.
6. Confirmacao independente: o retangulo `20 880 600 470` que o `01-04` achou "a olho" e, dentro de poucos pixels, o proprio `tiat_chat`.

**Por que isso importa mesmo estando fora dos 8 criterios.** Nesta maquina o defeito falha FECHADO (coordenada negativa -> recusa -> codigo 1), o que e a boa direcao. Mas numa maquina com origem de janela pequena e nao-nula (por exemplo `(0, 30)`), a subtracao produziria um retangulo que **cabe** e **le as linhas erradas em silencio** — e a ferramenta existe justamente para que um "nao casou" seja acionavel. Um "nao casou" produzido por recorte errado e o unico modo de falha que levaria alguem a afrouxar um padrao que estava certo, que e a familia de defeito que `T-04-02` nomeia.

**Escopo:** `tools/` apenas. `l2scanner/` nao e afetado, o scanner nao e afetado, e os 8 criterios nao dependem disso.

---

## Itens abertos registrados para a Fase 2 (NAO sao gaps desta fase)

Os dois vieram sinalizados pelos SUMMARYs e ambos foram **confirmados por medida** nesta verificacao.

### 1. `splitlines()` e inerte em producao — T-01-01/T-01-02 precisam de re-rating

`l2scanner/ocr.py:280` devolve `resultado.text`, e `OcrResult.text` do WinRT junta as linhas com **espaco**. Medido em campo: nas 4.220 passadas da varredura, **toda** leitura saiu como `texto cru, 1 linha(s)` — inclusive frames com seis conversas simultaneas. Portanto o `linhas_do_chat = (texto_do_chat or "").splitlines()` de `VigiaDeBosses.avaliar` sempre itera **uma** linha, e a mitigacao de T-01-02 nao esta operante.

**Exposicao real, medida:** baixa, e vale registrar o numero para a Fase 2 nao superestimar o risco. Como os separadores do padrao sao `\s*`/`\s+` e nao `.*`, um prefixo de remetente entre as partes quebra o casamento. Cinco blobs construidos de proposito para costurar duas linhas (`'Fulano : alguem viu o Tiat North Beltran : [Lv. 60] eu tava la has spawned amanha'`, `'Zeca : Tiat North Ana : [Lv. 60] has spawned!'`, e mais tres) produziram **`[]` em todos**. Somado aos 2.074 frames de campo com zero casamento, a costura entre linhas nao e um defeito observado — e uma mitigacao inoperante contra uma ameaca cuja probabilidade caiu.

### 2. Origem `ALVO` afirma nascimento sem prova de nascimento

Confirmado no texto de producao: `AvisoDeBoss(origem=ALVO).texto` -> `"Tiat South nasceu! (seu alvo virou Tiat South)"`. Ter o boss alvejado nao prova que ele acabou de nascer — pode estar vivo ha uma hora. A Fase 2 tem de decidir **explicitamente** se `ALVO` ganha o direito de ancorar uma contagem de 6-8h em disco. O proprio `bosses.py` ja escreve, na docstring de `_bosses_identificados_no_alvo`, que "na Fase 2 a conta fica pior" — a decisao esta preparada, mas nao tomada.

---

## Observacoes menores (nao acionaveis nesta fase)

1. **Uma afirmacao do `01-04-SUMMARY` esta desatualizada.** Ele diz que "os quatro `calibration*.json` do checkout principal tem `tiat_chat: null`". Medido hoje: `calibration.json` (modificado 14:27) e `calibration.antes-do-tiat.bak` **tem** os dois campos preenchidos; `rascunho`, `ANTES-DA-INSTALACAO` e `RESGATE-13-glifos` tem `null`. E o que tornou G-01 mensuravel.
2. **`STATE.md` do workstream esta parado.** Continua dizendo *"Status: Roadmap criado, aguardando planejamento da Fase 1"* e *"Phases Complete: 0 / 2"*. E tarefa do orquestrador no fechamento, nao do plano.
3. **`calibrar-tiat.bat` e a flag `--tiat` mantem o nome antigo de proposito**, e a razao esta escrita em comentario (nao em docstring, porque a docstring e varrida pelo proprio guarda). A assimetria e correta e o guarda perdoa `calibrar-tiat.bat` e `--tiat` ANTES da busca, nunca depois — conferi os dois testes simetricos.
4. **Ambiente de teste.** Registro para quem repetir: nem o `.venv` (tem WinRT, nao tem pytest) nem o Python do sistema (tem pytest, nao tem WinRT) rodam a suite completa sozinhos. A combinacao usada foi `.venv/Scripts/python.exe -m pytest` com `PYTHONPATH` para o `site-packages` do sistema; `numpy 2.5.2` e `cv2 4.14.0` sao identicos nos dois, entao nao ha sombreamento de versao.

---

## Resumo narrativo

O objetivo da fase esta **atingido**. O alerta so sai com o anuncio do servidor — e isso nao e uma afirmacao de SUMMARY: e 2.074 frames de chat de jogador de verdade sem um unico falso positivo, e 36 frames de um nascimento real de `Tiat North` reconhecidos nas duas escalas de OCR sem um unico falso negativo. O alerta nomeia qual boss nasceu, e o nome vem sempre do `[[boss]]`, nunca do texto lido. Quem e vigiado e uma linha do `config.toml`: um mob inventado passou a ser vigiado sem nenhum `.py` tocado, e nenhum `.py` conhece o nome dele. O debounce, que era o ativo a nao quebrar, sobreviveu com os 7 nomes e a aritmetica intactos e ganhou a forma por boss que o criterio 4 exigia — verificada nas duas direcoes.

O que impede o `passed` e um defeito de coordenadas na ferramenta de diagnostico criada em `01-04`. Ele nao afeta o scanner, nao afeta nenhum dos 8 criterios, e a evidencia que fechou R-01 foi obtida pelo caminho que funciona. Mas e um key link declarado que esta quebrado, a docstring afirma o contrario do que a producao faz, e a unica linha de codigo sem teste da fase e exatamente aquela — que e a razao pela qual ele atravessou. A correcao e curta; o que ela precisa e de um teste que case o retangulo contra o `calibration.json` real, que agora existe.

---

*Verificado: 2026-08-30*
*Verificador: Claude (gsd-verifier) — 8 criterios executados contra codigo de producao, varredura de campo de 4.220 passadas reproduzida, guarda de OPER-01 re-medido contra o fonte pre-fase, e o padrao provado por mutacao nas duas direcoes.*
