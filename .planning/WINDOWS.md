---
schema_version: 1
open_count: 20
waived_count: 1
fixed_count: 7
total_count: 28
last_updated: 2026-08-31T00:51:01.264Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | quick-260825-pik | deviation | l2scanner/loot.py |  | momento_desejado: data sem ano escolhe a leitura de calendario mais proxima em vez do recuo de ano irrestrito que o plano descrevia — o plano se contradizia e o teste do futuro venceu | waived | Implementado esta CERTO e a divergencia e melhoria, nao defeito: em 25/08/2026 o recuo de ano irrestrito que o plano descrevia gravaria `.pegou 30/12 18:00 Korzis` como 30/12/2025 18:00 (medido lado a lado com a regra atual), e como `.loot/` nunca e podada e `.corrigir-<nick>` so alcanca o registro MAIS RECENTE, esse registro nasceria permanente e inalcancavel; a leitura de calendario mais proxima (loot.py:641-706) recusa esse caso com texto, nao com silencio (`ja passou`, loot.py:989), e CONCORDA com o recuo em 03/01/2027, onde as duas regras dao 30/12/2026 — ela nao perde nada e so fecha a porta destrutiva. Os dois sentidos da regra estao presos por test_data_no_FUTURO_ou_IMPOSSIVEL_recusa_e_nao_grava (tests/test_loot.py:1120) e test_a_virada_do_ANO (tests/test_loot.py:1135), com test_data_explicita_alcanca_um_dia_ANTIGO (:1095) cobrindo a data explicita, e a escolha ja foi ratificada em STATE.md ## Decisions [Phase 4] loot — o ledger registrava divergencia contra um plano que o proprio projeto ja substituiu. | 2026-08-25T21:59:50.148Z | 2026-08-26T13:53:16.579Z |
| 2 | quick-260825-psq | unmet-truth | l2scanner/ocr.py |  | ESCALA_DE_DETECCAO=1 nao le os digitos do banner real (le MOninutes): com 1x e 3x as duas escalas nunca concordam e o recurso nunca anuncia | fixed |  | 2026-08-25T22:04:27.547Z | 2026-08-25T22:11:00.846Z |
| 3 | 10 | todo | l2scanner/config.py |  | avisar_minutos_antes ainda aceita true (isinstance(True, int) e verdadeiro); chamar_minutos_antes nao herdou o buraco, o campo antigo espera plano proprio | open |  | 2026-08-26T15:25:06.252Z |  |
| 4 | 10 | todo | l2scanner/presenca.py |  | texto_de_fechamento(sugestao=) nasce declarado e sem chamador; quem o preenche e o plano 10-05 (D-13) | open |  | 2026-08-26T16:22:22.620Z |  |
| 5 | quick-260827-fsk | unrun-verify | .planning/quick/260827-fsk-trocar-o-discriminador-da-legibilidade-d/260827-fsk-PLAN.md |  | verify da Task 3 aponta para .planning/STATE.md, movido para .planning/workstreams/default/ por processo concorrente; STATE atualizado no caminho novo | open |  | 2026-08-27T15:59:09.257Z |  |
| 6 | 1 | unrun-verify | l2scanner/__main__.py |  | human-check da Task 1 nao rodou: resumo final com 0 confirmados / N falhas / 0 no disco exige uma sessao real com destino de gravacao invalido | open |  | 2026-08-27T23:47:45.913Z |  |
| 7 | 1 | unrun-verify | l2scanner/gravador.py |  | human-check da Task 2 nao rodou: PNG de ~3,5 MB da janela inteira exige o jogo aberto (gate externo da fase) | open |  | 2026-08-27T23:47:46.298Z |  |
| 8 | 1 | unrun-verify | tools/conferir_gravacoes_do_spike.py |  | verificacao 5 do 01-02 nao rodou: o portao das gravacoes so sai com codigo 0 depois que o usuario gravar as 8 sessoes (gate externo, Task 3) | open |  | 2026-08-28T00:18:09.481Z |  |
| 9 | 1 | deviation | tests/fixtures/mercado/ |  | criterio de aceite do 01-02 nao satisfeito: pedia >=8 positivos do 27x, existem 2 — so 2 dos 9 frames _JANELA tem o painel do mercado aberto (medido; os outros mostram o inventario) | open |  | 2026-08-28T00:18:16.266Z |  |
| 10 | 1 | unrun-verify | PORTAO-DISCORD.txt |  | Criterio 2 da Fase 1 (texto real no console) nao conferido: os 4 passos do portao humano do Discord nao foram dados | open |  | 2026-08-28T17:31:16.484Z |  |
| 11 | 1 | unrun-verify | l2scanner/__main__.py |  | Task 3 do 01-04: a sessao ao vivo --janela SEM calibracao de mercado nao foi rodada com o jogo aberto. O caminho degenerado esta provado por teste (campo None, extras sem a chave), mas o comportamento identico ao de antes num farm real nao foi observado | open |  | 2026-08-28T20:04:07.455Z |  |
| 12 | quick-260829-rd9 | unmet-truth | .planning/workstreams/mercado/STATE.md | 72 | Todo da watchlist cita verbatim o criterio 1 da Fase 2 que foi substituido em 260829-rd9; a watchlist deixou de ser pre-requisito de bloqueio | fixed |  | 2026-08-29T23:05:24.348Z | 2026-08-29T23:08:10.741Z |
| 13 | 02 | deviation | l2scanner/calibrar.py |  | calibrar.py (calibracao de PARTY) apaga TODA a calibracao de mercado: calibrar_selecionando monta uma Calibracao do zero (calibrar.py:353) e o fluxo grava por cima do arquivo inteiro (calibrar.py:1244). CONFIRMADO EM CAMPO 2026-08-30: o usuario rodou calibrar.bat e perdeu 13 moldes de glifo, 3 ancoras, mercado_grade e mercado_limiar_de_glifo. E a gemea exata do CR-04, ja consertado do lado do mercado e nunca do lado da party. Resgate em calibration.RESGATE-13-glifos.json | open |  | 2026-08-30T10:16:35.946Z |  |
| 14 | 2 | deviation | l2scanner/mercado_catalogo.py |  | O corte 0,894737 funde 'B-grade Gemstone' com 'C-grade Gemstone' (0,9375): a trava de digitos nao alcanca uma diferenca de LETRA de grade, e as duas assinaturas sao vazias. Unica fusao conhecida sobre os 50 nomes confirmados; presa por teste em test_medir_agrupamento_de_nome.py. | open |  | 2026-08-30T13:43:57.341Z |  |
| 15 | 2 | deviation | tools/medir_agrupamento_de_nome.py |  | T-02-11 agravado: a sonda de fundo do 02-02 mede x em [207,417) a partir de gx e NAO alcanca o inicio do nome. Medido, 'Cohi nn Mafia Leader Luciano Doll' (marcacao de alvo sobre o inicio) passou como linha limpa. O 02-04 poe a sonda no pipeline e precisa saber disso. | open |  | 2026-08-30T13:43:57.709Z |  |
| 16 | 2 | unmet-truth | l2scanner/mercado_leitura.py |  | O digito 1 da coluna Quantity NAO se le, e isso derruba a maioria das linhas do mercado. MEDIDO em pagina-cheia/frame_000010: o tronco do 1 da quantidade e desenhado a V=177, ABAIXO do piso 180 de identidade.mascara_de_texto, enquanto o tronco do 1 do 100,00 da coluna Total tem V=205. A mascara fica so com a serifa e a base, o casamento devolve 0,2988 (o proprio molde 1 vale -0,1810) e o piso de leitura 0,4698 reprova. Falha FECHADA, comportamento certo, custo alto: nas gravacoes tooltip e alvo-sobreposto ZERO linhas atravessam por causa disso. Conserto = piso de brilho PROPRIO da coluna Quantity, MEDIDO por varredura, no mesmo padrao de VALOR_MINIMO_DO_SUFIXO=120. A7 do 02-RESEARCH volta a ficar aberta. | fixed |  | 2026-08-30T16:30:42.703Z | 2026-08-31T00:45:42.344Z |
| 17 | 2 | unmet-truth | l2scanner/mercado_leitura.py |  | A sonda de oclusao NAO ve tooltip na metade DIREITA da grade. Ela mede dx [207,417) a partir de gx, e em pagina-cheia/frame_000010 a tooltip cobre a coluna Total das linhas 0 a 3 com dispersao 0,0000 nas dez linhas. Complementa o windows #15 (que registrou o lado esquerdo). Quem pega o caso hoje e o tudo-ou-nada + gramatica, que falham FECHADO; mas uma tooltip semitransparente sobre um numero pode produzir glifo plausivel que passe nas duas peneiras. Fecha de vez com a guarda de cruzamento do 02-06 ou com uma sonda por FAIXA em vez de trecho unico. | open |  | 2026-08-30T16:31:01.391Z |  |
| 18 | 2 | deviation | .planning/workstreams/mercado/phases/02-leitura-de-p-gina/02-04-PLAN.md |  | Tres fixturas que o plano 02-04 nomeou foram trocadas por medicao: (a) a linha 0 de janela_negociacao_f010.png NAO vira LinhaLida (tooltip sobre a coluna Total; atravessam a 6 e a 8); (b) janela_negociacao_f010_repetida.png nao existe — f010 nao e pagina parada, os vizinhos f009/f011 mostram paginas diferentes, e o par parado medido e f005/f006; (c) tooltip/frame_000015 NAO serve para provar recusa por linha porque a tooltip cobre tambem o cabecalho e o portao de layout recusa a pagina inteira (casamento 0,4469 contra limiar 0,73) — o frame que serve e o 000012 (cabecalho 0,9196, 8 linhas cobertas e 2 nao). | open |  | 2026-08-30T16:31:01.783Z |  |
| 19 | 2 | unrun-verify | l2scanner/mercado_pagina.py |  | O tracer nunca rodou com o JOGO ABERTO e OCR de verdade. Toda a suite do 02-04 injeta as duas leitoras (o Python global nao tem as bindings WinRT), entao a leitura de nome ponta a ponta com Windows.Media.Ocr sobre a coluna calibrada segue sem observacao ao vivo. Portao humano de fim de fase. | open |  | 2026-08-30T16:31:02.167Z |  |
| 20 | 01 | unrun-verify | l2scanner/bosses.py |  | A frase real do servidor nunca passou pelo OCR deste projeto: toda a suite alimenta o vigia com texto ja decodificado. A folga de OCR e um palpite calibrado, nao uma medicao — o plano 01-04 constroi a ferramenta que confronta a frase contra pixels. | open |  | 2026-08-30T17:06:37.685Z |  |
| 21 | 2 | unmet-truth | l2scanner/mercado_leitura.py |  | Dois digitos VIZINHOS sem coluna vazia entre eles viram UM run e a celula le o numero ERRADO. MEDIDO no censo do 02-07: 053105-mercado-aberto L3, quantidade 44 (rotulo derivado de Total 56,00 e Unit price 1,27) sai como UM run de 12 px em segmentar_glifos e casa com o molde 4 - le 4, atravessa a gramatica e vira numero plausivel e errado. 14 celulas em 2170 rotuladas. NAO e defeito de brilho: e identico nos 36 pisos de 180 a 145, entao nenhum piso de brilho o conserta. Ele e a causa 1 que REPROVOU a proposta de piso do 02-07, e o conserto e de SEGMENTACAO (largura esperada do glifo), nao de mascara. | fixed |  | 2026-08-30T18:30:20.716Z | 2026-08-30T23:10:42.157Z |
| 22 | 2 | deviation | tools/medir_brilho_da_quantidade.py |  | O 02-07 MEDIU e REPROVOU a proposta de piso de brilho proprio da coluna Quantity, e gravou o piso COMPARTILHADO (180) em mercado_limiar_de_brilho_da_quantidade - o comportamento de HOJE, que falha FECHADA. Causa: o piso compartilhado JA ERRA em 14 de 2170 celulas rotuladas (a janela do glifo COLADO), e a regra e que um piso so se propoe sobre um conjunto seguro que comece limpo. O que a medicao mostrou e que o vao EXISTE: com as 14 celulas do defeito de segmentacao de fora, os pisos 173..161 tem o balde LE ERRADO identico ao do piso 180, o primeiro piso a acrescentar erro NOVO e 160, e o ultimo seguro seria 161, com folga (a)=1 e folga (b)=13 contra o tronco do 1 remedido em 174. O rendimento saltaria de 463 para 2045 leituras certas em 2170. Reabrir depois que a janela do glifo colado fechar. | fixed |  | 2026-08-30T18:30:34.326Z | 2026-08-31T00:45:42.775Z |
| 23 | 02 | deviation | l2scanner/respawn.py |  | Task 2 sem fase RED: as quatro frases foram escritas na Task 1 para nao existir commit em que a origem ALVO atribua a citacao ao servidor; compensado por conferencia via mutacao | open |  | 2026-08-30T22:50:55.361Z |  |
| 24 | 2 | deviation | tools/medir_largura_de_run.py |  | O 02-08 MEDIU e PROPOS mercado_folga_de_cola_do_glifo = 1 (LE CERTO 82, NAO LE 42, LE ERRADO 0 sobre 124 celulas com run largo e rotulo, nas duas populacoes: total 58/1/0 e unitario 10/1/0 contra o rotulo de INTERVALO, quantidade 14/40/0 contra o rotulo DERIVADO). Contra HOJE, 69 leituras ERRADAS viram ZERO; rendimento 1135 -> 1148 linhas completas e 155 -> 156 paginas. DUAS afirmacoes do plano foram REFUTADAS pela medicao e ficam registradas: (a) as folgas 2, 3 e 4 NAO inventam numero - elas produzem leitura IDENTICA a folga 1 (0 celulas mudam), porque particionar_run escolhe pelo PIOR segmento do corte e nao pela primeira composicao valida; a sondagem do planejador previa 54 invencoes na variante D e mediu outra regra de escolha. (b) o pior caso da particao e 60,2 ms por linha, 17x abaixo do tick de 1 Hz - e nao as tres ordens de grandeza que o plano afirmava. Os dois numeros passam nos criterios (teto de 200 ms; balde LE ERRADO vazio), mas o segundo deixa menos folga do que o plano supunha e precisa ser reconferido se a particao ganhar largura. | open |  | 2026-08-30T23:10:42.554Z |  |
| 25 | 2 | unmet-truth | tools/medir_brilho_da_quantidade.py |  | A CAUSA da REPROVA do 02-07 esta REMOVIDA: o balde LE ERRADO do piso compartilhado eram as 14 celulas de glifo COLADO (windows #21), e com a particao do 02-08 elas leem CERTO. A varredura de piso do 02-07 volta a ser PROPONIVEL e pega o beneficio de graca, porque medir_brilho_da_quantidade.py chama ler_celula, que agora recebe folga_de_cola da calibracao. NAO foi re-rodada aqui de proposito: ela passa de 10 minutos e ja custou uma sessao a um executor. Quem fechar o 02-07 roda 'tools/medir_brilho_da_quantidade.py --gravar' e deve encontrar o passo ZERO limpo, com os pisos 173..161 seguros e o ultimo seguro em 161 (rendimento previsto 463 -> 2045 em 2170). | fixed |  | 2026-08-30T23:10:56.513Z | 2026-08-31T00:45:43.180Z |
| 26 | 2 | deviation | calibration.json |  | 02-07 FECHA a janela #16 por MEDICAO: mercado_limiar_de_brilho_da_quantidade = 161, o ULTIMO PISO SEGURO com PASSO_DA_VARREDURA = 1. Balde LE ERRADO do proprio 161 VAZIO sobre 2247 celulas rotuladas; folga (a) ate o primeiro piso que erra = 1 (o 160 acrescenta 2 erros novos), folga (b) ate o tronco medido do 1 = 13 (tronco remedido no censo = 174, e nao os 177 da sondagem do plano). Rendimento da coluna Quantity 541 -> 2133 de 2247; o rotulo 1 (n=1680) vai de 0 para 1590 leituras certas; as 3 gravacoes que liam ZERO (tooltip, alvo-sobreposto, farm-com-party) passam a 199/241, 215/224 e 327/329. A hipotese do 02-08 CONFIRMOU-SE: o balde LE ERRADO do piso compartilhado 180, que tinha 14 celulas e REPROVOU a proposta em 2026-08-30, esta VAZIO depois da particao do glifo colado. O piso e PROPRIO da coluna e nunca global - o mesmo 161 aplicado as colunas de moeda faria 4697 celulas deixarem de ler e 1029 lerem outra coisa. | fixed |  | 2026-08-31T00:46:06.875Z | 2026-08-31T00:46:17.224Z |
| 27 | 2 | unmet-truth | tests/test_bosses.py |  | FORA DO ESCOPO do 02-07, registrado por descoberta durante a suite completa: tests/test_bosses.py tem 2 falhas PRE-EXISTENTES, do workstream tiat e nao do mercado. O commit c4175da mudou o config.toml para 'Tiat 8h + 2 random (o servidor mudou a regra)' e os dois testes (test_o_arquivo_do_repositorio_tem_os_dois_tiat_com_6_e_8 e test_os_dois_tiat_do_repositorio_tem_6_e_8) seguem cobrando 6 e 8. Nenhum arquivo do 02-07 os toca. Suite: 2501 passed, 2 skipped, 2 failed sem test_agenda.py; 144 passed so com ele. | open |  | 2026-08-31T00:46:17.943Z |  |
| 28 | 2 | deviation | tests/test_bosses.py |  | CONTAMINACAO ENTRE WORKSTREAMS num commit do 02-07: o commit RED e0e0083 ('test(02-07): o rotulo derivado, as quatro recusas e o ultimo piso seguro') carregou junto quatro arquivos do workstream TIAT que nao pertencem ao 02-07 — l2scanner/bosses.py, tests/test_bosses.py, tests/test_presenca.py e um 01-03-SUMMARY.md do tiat. Foi um executor concorrente com arquivos ja no index. Descoberto no fechamento do 02-07 (sessao seguinte), quando a janela #27 foi rastreada ate a origem. Nada foi desfeito: reverter arrastaria trabalho legitimo do tiat, e o commit c4175da (posterior) ja construiu por cima. Registrado para que o padrao 'git add por arquivo, nunca git add -A' tenha um caso concreto atras dele. | open |  | 2026-08-31T00:51:01.264Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "quick-260825-pik",
    "file": "l2scanner/loot.py",
    "line": null,
    "description": "momento_desejado: data sem ano escolhe a leitura de calendario mais proxima em vez do recuo de ano irrestrito que o plano descrevia — o plano se contradizia e o teste do futuro venceu",
    "status": "waived",
    "reason": "Implementado esta CERTO e a divergencia e melhoria, nao defeito: em 25/08/2026 o recuo de ano irrestrito que o plano descrevia gravaria `.pegou 30/12 18:00 Korzis` como 30/12/2025 18:00 (medido lado a lado com a regra atual), e como `.loot/` nunca e podada e `.corrigir-<nick>` so alcanca o registro MAIS RECENTE, esse registro nasceria permanente e inalcancavel; a leitura de calendario mais proxima (loot.py:641-706) recusa esse caso com texto, nao com silencio (`ja passou`, loot.py:989), e CONCORDA com o recuo em 03/01/2027, onde as duas regras dao 30/12/2026 — ela nao perde nada e so fecha a porta destrutiva. Os dois sentidos da regra estao presos por test_data_no_FUTURO_ou_IMPOSSIVEL_recusa_e_nao_grava (tests/test_loot.py:1120) e test_a_virada_do_ANO (tests/test_loot.py:1135), com test_data_explicita_alcanca_um_dia_ANTIGO (:1095) cobrindo a data explicita, e a escolha ja foi ratificada em STATE.md ## Decisions [Phase 4] loot — o ledger registrava divergencia contra um plano que o proprio projeto ja substituiu.",
    "recorded_at": "2026-08-25T21:59:50.148Z",
    "resolved_at": "2026-08-26T13:53:16.579Z"
  },
  {
    "id": 2,
    "kind": "unmet-truth",
    "phase": "quick-260825-psq",
    "file": "l2scanner/ocr.py",
    "line": null,
    "description": "ESCALA_DE_DETECCAO=1 nao le os digitos do banner real (le MOninutes): com 1x e 3x as duas escalas nunca concordam e o recurso nunca anuncia",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-25T22:04:27.547Z",
    "resolved_at": "2026-08-25T22:11:00.846Z"
  },
  {
    "id": 3,
    "kind": "todo",
    "phase": "10",
    "file": "l2scanner/config.py",
    "line": null,
    "description": "avisar_minutos_antes ainda aceita true (isinstance(True, int) e verdadeiro); chamar_minutos_antes nao herdou o buraco, o campo antigo espera plano proprio",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T15:25:06.252Z",
    "resolved_at": null
  },
  {
    "id": 4,
    "kind": "todo",
    "phase": "10",
    "file": "l2scanner/presenca.py",
    "line": null,
    "description": "texto_de_fechamento(sugestao=) nasce declarado e sem chamador; quem o preenche e o plano 10-05 (D-13)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-26T16:22:22.620Z",
    "resolved_at": null
  },
  {
    "id": 5,
    "kind": "unrun-verify",
    "phase": "quick-260827-fsk",
    "file": ".planning/quick/260827-fsk-trocar-o-discriminador-da-legibilidade-d/260827-fsk-PLAN.md",
    "line": null,
    "description": "verify da Task 3 aponta para .planning/STATE.md, movido para .planning/workstreams/default/ por processo concorrente; STATE atualizado no caminho novo",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-27T15:59:09.257Z",
    "resolved_at": null
  },
  {
    "id": 6,
    "kind": "unrun-verify",
    "phase": "1",
    "file": "l2scanner/__main__.py",
    "line": null,
    "description": "human-check da Task 1 nao rodou: resumo final com 0 confirmados / N falhas / 0 no disco exige uma sessao real com destino de gravacao invalido",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-27T23:47:45.913Z",
    "resolved_at": null
  },
  {
    "id": 7,
    "kind": "unrun-verify",
    "phase": "1",
    "file": "l2scanner/gravador.py",
    "line": null,
    "description": "human-check da Task 2 nao rodou: PNG de ~3,5 MB da janela inteira exige o jogo aberto (gate externo da fase)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-27T23:47:46.298Z",
    "resolved_at": null
  },
  {
    "id": 8,
    "kind": "unrun-verify",
    "phase": "1",
    "file": "tools/conferir_gravacoes_do_spike.py",
    "line": null,
    "description": "verificacao 5 do 01-02 nao rodou: o portao das gravacoes so sai com codigo 0 depois que o usuario gravar as 8 sessoes (gate externo, Task 3)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-28T00:18:09.481Z",
    "resolved_at": null
  },
  {
    "id": 9,
    "kind": "deviation",
    "phase": "1",
    "file": "tests/fixtures/mercado/",
    "line": null,
    "description": "criterio de aceite do 01-02 nao satisfeito: pedia >=8 positivos do 27x, existem 2 — so 2 dos 9 frames _JANELA tem o painel do mercado aberto (medido; os outros mostram o inventario)",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-28T00:18:16.266Z",
    "resolved_at": null
  },
  {
    "id": 10,
    "kind": "unrun-verify",
    "phase": "1",
    "file": "PORTAO-DISCORD.txt",
    "line": null,
    "description": "Criterio 2 da Fase 1 (texto real no console) nao conferido: os 4 passos do portao humano do Discord nao foram dados",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-28T17:31:16.484Z",
    "resolved_at": null
  },
  {
    "id": 11,
    "kind": "unrun-verify",
    "phase": "1",
    "file": "l2scanner/__main__.py",
    "line": null,
    "description": "Task 3 do 01-04: a sessao ao vivo --janela SEM calibracao de mercado nao foi rodada com o jogo aberto. O caminho degenerado esta provado por teste (campo None, extras sem a chave), mas o comportamento identico ao de antes num farm real nao foi observado",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-28T20:04:07.455Z",
    "resolved_at": null
  },
  {
    "id": 12,
    "kind": "unmet-truth",
    "phase": "quick-260829-rd9",
    "file": ".planning/workstreams/mercado/STATE.md",
    "line": 72,
    "description": "Todo da watchlist cita verbatim o criterio 1 da Fase 2 que foi substituido em 260829-rd9; a watchlist deixou de ser pre-requisito de bloqueio",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-29T23:05:24.348Z",
    "resolved_at": "2026-08-29T23:08:10.741Z"
  },
  {
    "id": 13,
    "kind": "deviation",
    "phase": "02",
    "file": "l2scanner/calibrar.py",
    "line": null,
    "description": "calibrar.py (calibracao de PARTY) apaga TODA a calibracao de mercado: calibrar_selecionando monta uma Calibracao do zero (calibrar.py:353) e o fluxo grava por cima do arquivo inteiro (calibrar.py:1244). CONFIRMADO EM CAMPO 2026-08-30: o usuario rodou calibrar.bat e perdeu 13 moldes de glifo, 3 ancoras, mercado_grade e mercado_limiar_de_glifo. E a gemea exata do CR-04, ja consertado do lado do mercado e nunca do lado da party. Resgate em calibration.RESGATE-13-glifos.json",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-30T10:16:35.946Z",
    "resolved_at": null
  },
  {
    "id": 14,
    "kind": "deviation",
    "phase": "2",
    "file": "l2scanner/mercado_catalogo.py",
    "line": null,
    "description": "O corte 0,894737 funde 'B-grade Gemstone' com 'C-grade Gemstone' (0,9375): a trava de digitos nao alcanca uma diferenca de LETRA de grade, e as duas assinaturas sao vazias. Unica fusao conhecida sobre os 50 nomes confirmados; presa por teste em test_medir_agrupamento_de_nome.py.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-30T13:43:57.341Z",
    "resolved_at": null
  },
  {
    "id": 15,
    "kind": "deviation",
    "phase": "2",
    "file": "tools/medir_agrupamento_de_nome.py",
    "line": null,
    "description": "T-02-11 agravado: a sonda de fundo do 02-02 mede x em [207,417) a partir de gx e NAO alcanca o inicio do nome. Medido, 'Cohi nn Mafia Leader Luciano Doll' (marcacao de alvo sobre o inicio) passou como linha limpa. O 02-04 poe a sonda no pipeline e precisa saber disso.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-30T13:43:57.709Z",
    "resolved_at": null
  },
  {
    "id": 16,
    "kind": "unmet-truth",
    "phase": "2",
    "file": "l2scanner/mercado_leitura.py",
    "line": null,
    "description": "O digito 1 da coluna Quantity NAO se le, e isso derruba a maioria das linhas do mercado. MEDIDO em pagina-cheia/frame_000010: o tronco do 1 da quantidade e desenhado a V=177, ABAIXO do piso 180 de identidade.mascara_de_texto, enquanto o tronco do 1 do 100,00 da coluna Total tem V=205. A mascara fica so com a serifa e a base, o casamento devolve 0,2988 (o proprio molde 1 vale -0,1810) e o piso de leitura 0,4698 reprova. Falha FECHADA, comportamento certo, custo alto: nas gravacoes tooltip e alvo-sobreposto ZERO linhas atravessam por causa disso. Conserto = piso de brilho PROPRIO da coluna Quantity, MEDIDO por varredura, no mesmo padrao de VALOR_MINIMO_DO_SUFIXO=120. A7 do 02-RESEARCH volta a ficar aberta.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-30T16:30:42.703Z",
    "resolved_at": "2026-08-31T00:45:42.344Z"
  },
  {
    "id": 17,
    "kind": "unmet-truth",
    "phase": "2",
    "file": "l2scanner/mercado_leitura.py",
    "line": null,
    "description": "A sonda de oclusao NAO ve tooltip na metade DIREITA da grade. Ela mede dx [207,417) a partir de gx, e em pagina-cheia/frame_000010 a tooltip cobre a coluna Total das linhas 0 a 3 com dispersao 0,0000 nas dez linhas. Complementa o windows #15 (que registrou o lado esquerdo). Quem pega o caso hoje e o tudo-ou-nada + gramatica, que falham FECHADO; mas uma tooltip semitransparente sobre um numero pode produzir glifo plausivel que passe nas duas peneiras. Fecha de vez com a guarda de cruzamento do 02-06 ou com uma sonda por FAIXA em vez de trecho unico.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-30T16:31:01.391Z",
    "resolved_at": null
  },
  {
    "id": 18,
    "kind": "deviation",
    "phase": "2",
    "file": ".planning/workstreams/mercado/phases/02-leitura-de-p-gina/02-04-PLAN.md",
    "line": null,
    "description": "Tres fixturas que o plano 02-04 nomeou foram trocadas por medicao: (a) a linha 0 de janela_negociacao_f010.png NAO vira LinhaLida (tooltip sobre a coluna Total; atravessam a 6 e a 8); (b) janela_negociacao_f010_repetida.png nao existe — f010 nao e pagina parada, os vizinhos f009/f011 mostram paginas diferentes, e o par parado medido e f005/f006; (c) tooltip/frame_000015 NAO serve para provar recusa por linha porque a tooltip cobre tambem o cabecalho e o portao de layout recusa a pagina inteira (casamento 0,4469 contra limiar 0,73) — o frame que serve e o 000012 (cabecalho 0,9196, 8 linhas cobertas e 2 nao).",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-30T16:31:01.783Z",
    "resolved_at": null
  },
  {
    "id": 19,
    "kind": "unrun-verify",
    "phase": "2",
    "file": "l2scanner/mercado_pagina.py",
    "line": null,
    "description": "O tracer nunca rodou com o JOGO ABERTO e OCR de verdade. Toda a suite do 02-04 injeta as duas leitoras (o Python global nao tem as bindings WinRT), entao a leitura de nome ponta a ponta com Windows.Media.Ocr sobre a coluna calibrada segue sem observacao ao vivo. Portao humano de fim de fase.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-30T16:31:02.167Z",
    "resolved_at": null
  },
  {
    "id": 20,
    "kind": "unrun-verify",
    "phase": "01",
    "file": "l2scanner/bosses.py",
    "line": null,
    "description": "A frase real do servidor nunca passou pelo OCR deste projeto: toda a suite alimenta o vigia com texto ja decodificado. A folga de OCR e um palpite calibrado, nao uma medicao — o plano 01-04 constroi a ferramenta que confronta a frase contra pixels.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-30T17:06:37.685Z",
    "resolved_at": null
  },
  {
    "id": 21,
    "kind": "unmet-truth",
    "phase": "2",
    "file": "l2scanner/mercado_leitura.py",
    "line": null,
    "description": "Dois digitos VIZINHOS sem coluna vazia entre eles viram UM run e a celula le o numero ERRADO. MEDIDO no censo do 02-07: 053105-mercado-aberto L3, quantidade 44 (rotulo derivado de Total 56,00 e Unit price 1,27) sai como UM run de 12 px em segmentar_glifos e casa com o molde 4 - le 4, atravessa a gramatica e vira numero plausivel e errado. 14 celulas em 2170 rotuladas. NAO e defeito de brilho: e identico nos 36 pisos de 180 a 145, entao nenhum piso de brilho o conserta. Ele e a causa 1 que REPROVOU a proposta de piso do 02-07, e o conserto e de SEGMENTACAO (largura esperada do glifo), nao de mascara.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-30T18:30:20.716Z",
    "resolved_at": "2026-08-30T23:10:42.157Z"
  },
  {
    "id": 22,
    "kind": "deviation",
    "phase": "2",
    "file": "tools/medir_brilho_da_quantidade.py",
    "line": null,
    "description": "O 02-07 MEDIU e REPROVOU a proposta de piso de brilho proprio da coluna Quantity, e gravou o piso COMPARTILHADO (180) em mercado_limiar_de_brilho_da_quantidade - o comportamento de HOJE, que falha FECHADA. Causa: o piso compartilhado JA ERRA em 14 de 2170 celulas rotuladas (a janela do glifo COLADO), e a regra e que um piso so se propoe sobre um conjunto seguro que comece limpo. O que a medicao mostrou e que o vao EXISTE: com as 14 celulas do defeito de segmentacao de fora, os pisos 173..161 tem o balde LE ERRADO identico ao do piso 180, o primeiro piso a acrescentar erro NOVO e 160, e o ultimo seguro seria 161, com folga (a)=1 e folga (b)=13 contra o tronco do 1 remedido em 174. O rendimento saltaria de 463 para 2045 leituras certas em 2170. Reabrir depois que a janela do glifo colado fechar.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-30T18:30:34.326Z",
    "resolved_at": "2026-08-31T00:45:42.775Z"
  },
  {
    "id": 23,
    "kind": "deviation",
    "phase": "02",
    "file": "l2scanner/respawn.py",
    "line": null,
    "description": "Task 2 sem fase RED: as quatro frases foram escritas na Task 1 para nao existir commit em que a origem ALVO atribua a citacao ao servidor; compensado por conferencia via mutacao",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-30T22:50:55.361Z",
    "resolved_at": null
  },
  {
    "id": 24,
    "kind": "deviation",
    "phase": "2",
    "file": "tools/medir_largura_de_run.py",
    "line": null,
    "description": "O 02-08 MEDIU e PROPOS mercado_folga_de_cola_do_glifo = 1 (LE CERTO 82, NAO LE 42, LE ERRADO 0 sobre 124 celulas com run largo e rotulo, nas duas populacoes: total 58/1/0 e unitario 10/1/0 contra o rotulo de INTERVALO, quantidade 14/40/0 contra o rotulo DERIVADO). Contra HOJE, 69 leituras ERRADAS viram ZERO; rendimento 1135 -> 1148 linhas completas e 155 -> 156 paginas. DUAS afirmacoes do plano foram REFUTADAS pela medicao e ficam registradas: (a) as folgas 2, 3 e 4 NAO inventam numero - elas produzem leitura IDENTICA a folga 1 (0 celulas mudam), porque particionar_run escolhe pelo PIOR segmento do corte e nao pela primeira composicao valida; a sondagem do planejador previa 54 invencoes na variante D e mediu outra regra de escolha. (b) o pior caso da particao e 60,2 ms por linha, 17x abaixo do tick de 1 Hz - e nao as tres ordens de grandeza que o plano afirmava. Os dois numeros passam nos criterios (teto de 200 ms; balde LE ERRADO vazio), mas o segundo deixa menos folga do que o plano supunha e precisa ser reconferido se a particao ganhar largura.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-30T23:10:42.554Z",
    "resolved_at": null
  },
  {
    "id": 25,
    "kind": "unmet-truth",
    "phase": "2",
    "file": "tools/medir_brilho_da_quantidade.py",
    "line": null,
    "description": "A CAUSA da REPROVA do 02-07 esta REMOVIDA: o balde LE ERRADO do piso compartilhado eram as 14 celulas de glifo COLADO (windows #21), e com a particao do 02-08 elas leem CERTO. A varredura de piso do 02-07 volta a ser PROPONIVEL e pega o beneficio de graca, porque medir_brilho_da_quantidade.py chama ler_celula, que agora recebe folga_de_cola da calibracao. NAO foi re-rodada aqui de proposito: ela passa de 10 minutos e ja custou uma sessao a um executor. Quem fechar o 02-07 roda 'tools/medir_brilho_da_quantidade.py --gravar' e deve encontrar o passo ZERO limpo, com os pisos 173..161 seguros e o ultimo seguro em 161 (rendimento previsto 463 -> 2045 em 2170).",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-30T23:10:56.513Z",
    "resolved_at": "2026-08-31T00:45:43.180Z"
  },
  {
    "id": 26,
    "kind": "deviation",
    "phase": "2",
    "file": "calibration.json",
    "line": null,
    "description": "02-07 FECHA a janela #16 por MEDICAO: mercado_limiar_de_brilho_da_quantidade = 161, o ULTIMO PISO SEGURO com PASSO_DA_VARREDURA = 1. Balde LE ERRADO do proprio 161 VAZIO sobre 2247 celulas rotuladas; folga (a) ate o primeiro piso que erra = 1 (o 160 acrescenta 2 erros novos), folga (b) ate o tronco medido do 1 = 13 (tronco remedido no censo = 174, e nao os 177 da sondagem do plano). Rendimento da coluna Quantity 541 -> 2133 de 2247; o rotulo 1 (n=1680) vai de 0 para 1590 leituras certas; as 3 gravacoes que liam ZERO (tooltip, alvo-sobreposto, farm-com-party) passam a 199/241, 215/224 e 327/329. A hipotese do 02-08 CONFIRMOU-SE: o balde LE ERRADO do piso compartilhado 180, que tinha 14 celulas e REPROVOU a proposta em 2026-08-30, esta VAZIO depois da particao do glifo colado. O piso e PROPRIO da coluna e nunca global - o mesmo 161 aplicado as colunas de moeda faria 4697 celulas deixarem de ler e 1029 lerem outra coisa.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-08-31T00:46:06.875Z",
    "resolved_at": "2026-08-31T00:46:17.224Z"
  },
  {
    "id": 27,
    "kind": "unmet-truth",
    "phase": "2",
    "file": "tests/test_bosses.py",
    "line": null,
    "description": "FORA DO ESCOPO do 02-07, registrado por descoberta durante a suite completa: tests/test_bosses.py tem 2 falhas PRE-EXISTENTES, do workstream tiat e nao do mercado. O commit c4175da mudou o config.toml para 'Tiat 8h + 2 random (o servidor mudou a regra)' e os dois testes (test_o_arquivo_do_repositorio_tem_os_dois_tiat_com_6_e_8 e test_os_dois_tiat_do_repositorio_tem_6_e_8) seguem cobrando 6 e 8. Nenhum arquivo do 02-07 os toca. Suite: 2501 passed, 2 skipped, 2 failed sem test_agenda.py; 144 passed so com ele.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-31T00:46:17.943Z",
    "resolved_at": null
  },
  {
    "id": 28,
    "kind": "deviation",
    "phase": "2",
    "file": "tests/test_bosses.py",
    "line": null,
    "description": "CONTAMINACAO ENTRE WORKSTREAMS num commit do 02-07: o commit RED e0e0083 ('test(02-07): o rotulo derivado, as quatro recusas e o ultimo piso seguro') carregou junto quatro arquivos do workstream TIAT que nao pertencem ao 02-07 — l2scanner/bosses.py, tests/test_bosses.py, tests/test_presenca.py e um 01-03-SUMMARY.md do tiat. Foi um executor concorrente com arquivos ja no index. Descoberto no fechamento do 02-07 (sessao seguinte), quando a janela #27 foi rastreada ate a origem. Nada foi desfeito: reverter arrastaria trabalho legitimo do tiat, e o commit c4175da (posterior) ja construiu por cima. Registrado para que o padrao 'git add por arquivo, nunca git add -A' tenha um caso concreto atras dele.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-31T00:51:01.264Z",
    "resolved_at": null
  }
]
````
