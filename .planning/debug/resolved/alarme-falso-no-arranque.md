---
status: resolved
trigger: "a party ja estava fixa, nada mudou desde que rodei calibrar.bat e liguei o bot, pq ele apitou TioMad entrou na party? [+ 18:19 'Yazalaque nao esta mais na party' e 18:21 'Yazalaque entrou em party' — NADA MUDOU NO GRUPO, alarme falso]"
created: 2026-08-24T18:25:00Z
updated: 2026-08-24T18:25:00Z
---

## Current Focus

bug_class: dois defeitos independentes, os dois deterministicos e reproduzidos offline
status: causa raiz CONFIRMADA nos dois por reproducao
next_action: aplicar as duas correcoes + testes de regressao

reasoning_checkpoint:
  hypothesis: >
    Sao DOIS bugs distintos, nao um. Os dois sao a mesma familia ja
    diagnosticada em [[party-entra-sai-em-loop]]: tratar mudanca de
    RECONHECIMENTO/VISAO como mudanca de REALIDADE. A correcao anterior
    instalou o sinal certo (a contagem de linhas), mas deixou dois furos.

    (1) TIOMAD ENTROU — a linha de base da contagem comeca em ZERO. No primeiro
    frame rastreado a comparacao vira "a party cresceu de 0 para 4", e esse
    True fica gravado por membro. Quem confirma a entrada DEPOIS que o
    aquecimento termina dispara ENTROU com o flag velho.

    (2) YAZALAQUE SAIU/ENTROU — `hp_proprio is not None` e usado como "a minha
    barra esta visivel", mas so significa "a regiao esta calibrada".
    `medir_barra` devolve 0.0 para um recorte ilegivel. Entao 90 s de CEGUEIRA
    viram "minha barra esta la a 0%, a party window sumiu" => "voce saiu da
    party". E `_avaliar_se_voce_esta_em_party` roda ANTES do portao de
    visibilidade, entao a cegueira nao congela esse veredito — ao contrario de
    todo o resto do rastreador.

## Symptoms

expected: party fixa de 5 pessoas, sem ninguem entrando ou saindo, nao gera evento nenhum
actual: >
  18:18:03  TIOMAD ENTROU NA PARTY        (7 s depois de ligar o bot)
  18:19:50  YAZALAQUE SAIU OU FOI REMOVIDO DA PARTY
  18:21:19  YAZALAQUE ENTROU EM PARTY
  Os tres entregues no WhatsApp. Nenhum aconteceu de verdade.
errors: nenhuma excecao
reproduction: >
  (1) offline, rastreador puro: party de 4 linhas fixas, reconhecimento do
      TioMad falha em UM frame. Dispara ENTROU.
  (2) logs/scanner.log 18:19:57-18:20:57: "[SEM VISAO]" com
      "Yazalaque (voce) ok HP 0%" — a propria barra lendo 0% e a assinatura de
      recorte ilegivel, nao de morte.
started: apos as sete correcoes de [[party-entra-sai-em-loop]]

## Evidence

- timestamp: fase-1
  checked: logs/scanner.log 18:17:56-18:18:03
  found: >
    Arranque as 18:17:56 com "[reajustando]" e os 5 membros com "?".
    ENTROU do TioMad as 18:18:03 — 7 s depois. Bate com 3 s de tolerancia
    (`segundos_de_tolerancia_na_volta`) + `confirmacoes_para_entrada=3` a ~1 Hz,
    com UM frame de atraso.
  implication: o evento nasce no aquecimento, nao no meio da sessao.

- timestamp: fase-2
  checked: reproducao offline com Rastreador puro, party de 4 linhas SEMPRE cheia
  found: >
    A: reconhecimento perfeito         -> 0 eventos
    B: TioMad pisca UM frame (frame 4) -> ENTROU TioMad no frame 6
    C: TioMad pisca UM frame (frame 5) -> ENTROU TioMad no frame 6
    `membros_presentes` = 4 em 100% dos frames. A party window NUNCA cresceu.
  implication: >
    Um unico frame de falha de reconhecimento, com a party fisicamente parada,
    e suficiente. Nao e Heisenbug: e deterministico.

- timestamp: fase-2
  checked: instrumentacao de `_ultima_contagem_estavel` / `apareceu_com_crescimento` / `_aquecido`
  found: |
    fr portao       linhas _ultima(ANTES) aquecido | TioMad cont/cresc/estado
     0 reaquisicao       4              0    False | 0 / False / desconhecido
     1 reaquisicao       4              0    False | 0 / False / desconhecido
     2 reaquisicao       4              0    False | 0 / False / desconhecido
     3 rastreando        4              0    False | 1 / True  / desconhecido   <- flag nasce True
     4 rastreando        4              4    False | 1 / True  / desconhecido   <- pisca, contador congela
     5 rastreando        4              4     True | 2 / True  / desconhecido   <- os outros viram VIVO
     6 rastreando        4              4     True | 0 / True  / vivo   <<< ENTROU
  implication: >
    PROVA DIRETA. `_ultima_contagem_estavel` comeca em 0 e so e escrito no FIM
    de `_processar`. `_registrar_leituras` (os frames de REAQUISICAO) atualiza
    `linhas_quando_visto` de cada membro mas NUNCA a linha de base global.
    Resultado: no primeiro frame rastreado, `linhas_agora > 0` e verdade para
    todo mundo, e `apareceu_com_crescimento` e gravado True — de proposito
    "guardado em vez de reavaliado" (rastreador.py:527-532), entao o valor
    errado e permanente.

    Os 4 membros reconhecidos desde o frame 3 escapam porque confirmam a
    entrada JUNTOS, enquanto `_aquecido` ainda e False (ele so vira True no fim
    do laco). Quem atrasa UM frame cai do lado errado da porta.

- timestamp: fase-3
  checked: logs/scanner.log 18:19:27-18:21:28 + l2scanner/visao.py:369-378
  found: >
    18:19:27  [vigiando] 5 membros, todos 100%
    18:19:50  YAZALAQUE SAIU OU FOI REMOVIDO DA PARTY
    18:19:57  [SEM VISAO]  Yazalaque (voce) ok HP 0%
    18:20:12  WARNING sem visao ha 30 leituras seguidas
    18:20:57  [SEM VISAO]  Yazalaque (voce) ok HP 0%
    18:21:19  YAZALAQUE ENTROU EM PARTY
    18:21:28  [vigiando] 5 membros, todos 100%

    `hp_proprio = medir_barra(recorte_proprio, ...)` (visao.py:378) devolve um
    float SEMPRE que o recorte existe. Recorte preto/ilegivel -> 0.0, nunca
    None. So `SaudeDoFrame != OK` produz None (visao.py:233), e a saude estava
    OK.
  implication: >
    `hp_proprio is not None` NAO significa "a minha barra esta visivel" — significa
    "a regiao esta calibrada". O discriminador inteiro do rastreador
    (rastreador.py:276-287: "tela de loading -> some tudo, a sua barra
    inclusive") descansa nessa premissa falsa.

    90 s de cegueira leram como "minha barra esta la a 0%, a party window
    sumiu" = a assinatura exata de "voce saiu da party".

- timestamp: fase-3
  checked: ordem de avaliacao em `Rastreador.observar`
  found: >
    `_avaliar_se_voce_esta_em_party` roda na linha 290, ANTES do portao de
    visibilidade (linha 293+). O portao faz `return` em `not ui_visivel` e
    CONGELA todos os contadores — morte, ressurreicao, saida. O veredito
    "voce em party" e o unico que atravessa a cegueira e conclui.
  implication: >
    Contradiz a propriedade 2 do proprio docstring do modulo ("o portao de
    visibilidade e avaliado ANTES das linhas") e a 3 ("cegueira CONGELA os
    contadores"). O bug e uma excecao nao intencional a uma regra que o modulo
    declara.

- timestamp: fase-3
  checked: "sair da party zera a sua barra de HP?"
  found: >
    Nao. Sair (ou ser removido) da party nao encosta no seu HP. A combinacao
    "party window sumiu E a minha barra le 0%" nao e producivel por uma saida
    de party — so por um recorte ilegivel (ou por morte, que e justamente
    quando NAO se deve concluir saida).
  implication: >
    Existe um discriminador honesto e sem pixel novo: HP proprio ~0 junto com
    party window ausente e assinatura de CEGUEIRA, nunca de saida.

## Eliminated

- hypothesis: "a calibracao de 18:17 ficou errada e o TioMad nao estava sendo reconhecido"
  evidence: "o bloco [reajustando] de 18:17:56 ja mostra Korzis, J4guar, TioMad, Kaus reconhecidos pelo nome, e todos os blocos [vigiando] seguintes tambem."
  timestamp: fase-1

- hypothesis: "a correcao G (crescimento da janela) nao foi aplicada / nao esta no codigo rodando"
  evidence: "rastreador.py:553-559 contem `apareceu_com_crescimento` e o commit bf1b1c9 esta no HEAD. A guarda existe — ela e que e alimentada com uma linha de base invalida."
  timestamp: fase-2

- hypothesis: "os dois alarmes (TioMad e Yazalaque) sao o mesmo bug"
  evidence: "reproducao B/C dispara ENTROU do TioMad com `ui_visivel=True` em 100% dos frames e sem tocar em `hp_proprio`. O do Yazalaque exige 90 s de `ui_visivel=False`. Mecanismos disjuntos."
  timestamp: fase-3

## Resolution

root_cause: >
  DOIS defeitos independentes.

  (1) l2scanner/rastreador.py — `_ultima_contagem_estavel` comeca em 0 e so e
      escrito no fim de `_processar`. No PRIMEIRO frame rastreado a comparacao
      `linhas_agora > _ultima_contagem_estavel` compara contra uma linha de
      base que nunca existiu, e grava `apareceu_com_crescimento = True` para
      todo membro visto nesse frame. Como o flag e guardado e nunca
      reavaliado, qualquer membro cuja confirmacao de entrada termine DEPOIS
      de `_aquecido` virar True dispara um ENTROU falso. Basta UM frame de
      falha de reconhecimento para produzir esse atraso.

  (2) l2scanner/visao.py + l2scanner/rastreador.py — `medir_barra` devolve 0.0
      para um recorte ilegivel, entao `hp_proprio` e um float mesmo com a tela
      inteira ilegivel. `hp_proprio is not None` e lido como "a minha barra
      esta visivel" quando so quer dizer "a regiao esta calibrada". Somado ao
      fato de `_avaliar_se_voce_esta_em_party` rodar ANTES do portao de
      visibilidade, 90 s de cegueira viraram VOCE_SEM_PARTY seguido de
      VOCE_ENTROU_EM_PARTY na recuperacao.

fix: >
  (1) `_ultima_contagem_estavel` passa a comecar em None em vez de 0, e o teste
      de crescimento exige linha de base: `is not None and linhas_agora > base`.
      Sem linha de base nao existe crescimento — o primeiro frame rastreado so a
      estabelece. Custo: uma entrada de verdade nos primeiros ~4 s passa calada,
      o mesmo comeco frio que `_aquecido` ja aplica ao resto.

  (2) `_avaliar_se_voce_esta_em_party` ganha uma guarda de cegueira no topo:
      party window ausente JUNTO com HP proprio <= `fracao_hp_considerada_zero`
      congela os dois contadores e nao conclui nada. Fundamento de dominio, sem
      pixel novo: sair da party nao encosta no seu HP, entao essa combinacao nao
      e producivel por uma saida — so por recorte ilegivel (ou por morte, que e
      justamente quando NAO se deve concluir saida).

verification: >
  Reproducao offline que falhava antes e passa agora:
    party de 4 linhas fixas + 1 frame de falha de reconhecimento -> 0 eventos
    (antes: ENTROU TioMad, nos frames 4, 5, 6 e 7 da piscada)
    90 s de cegueira com HP proprio 0% -> 0 eventos
    (antes: VOCE_SEM_PARTY + VOCE_ENTROU_EM_PARTY)

  Deteccao real preservada, verificada uma a uma:
    party 3 -> 4 linhas             -> entrou:Kaus            OK
    party 4 -> 3 linhas             -> saiu:Kaus              OK
    party window some, barra cheia  -> voce_sem_party         OK
    volta para a party depois disso -> voce_entrou_em_party   OK
    HP de um membro vai a zero      -> morreu:Kaus            OK

  Suite: 224 testes passando (215 antes + 9 novos).
  ruff: 23 erros e 2 arquivos a reformatar — identicos ao baseline em 52e5145,
  nenhum introduzido aqui.

files_changed:
  - l2scanner/rastreador.py
  - tests/test_identidade.py (TestArranqueNaoInventaEntrada, 5 testes)
  - tests/test_voce_na_party.py (TestCegueiraNaoEsaidaDaParty, 4 testes)

## Terceiro falso positivo — CORRIGIDO (decisao do usuario)

logs/scanner.log 18:08:00 "YAZALAQUE ENTROU EM PARTY", numa sessao em modo
simulacao (nao chegou ao WhatsApp). Caminho diferente dos dois acima:

  arranque, ~14 frames sem conseguir ler a party window, barra propria lendo
  100% normal, party LA o tempo todo -> VOCE_ENTROU_EM_PARTY na recuperacao

Mecanismo: `_voce_em_party` comeca None; 8 leituras sem party window fixam False
em silencio (comeco frio, correto); a recuperacao entao ve False -> True e trata
como transicao conhecida, anunciando.

A leitura e AMBIGUA de verdade — "liguei fora de party e entrei" produz os
mesmos pixels que "liguei e demorei para ler a tela" — entao nao havia correcao
puramente tecnica. Usuario escolheu CALAR NO ARRANQUE.

Implementado: `_ja_viu_party_window` marca se a party window ja foi vista
alguma vez, e `_sem_party_era_confiavel` congela esse fato NO INSTANTE em que o
veredito "sem party" e firmado. Consultar na volta nao funcionaria: quando a
entrada confirma, a party window ja esta visivel ha varios frames e a resposta
seria sempre "sim".

Preco aceito: entrar numa party logo depois de ligar o scanner nao gera aviso.
Sair de uma party e voltar (com a window ja vista antes) continua avisando nas
duas pontas — coberto por `test_saida_e_volta_de_verdade_ainda_avisam_as_duas`.
