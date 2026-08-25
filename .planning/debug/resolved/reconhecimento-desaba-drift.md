---
status: resolved
trigger: "Depois de uma falha de captura (09:59-10:03), o reconhecimento de nomes desabou e nao se recuperou: 'Membro 1 / J4guar / Membro 3' em vez dos nicks. Ficou piscando por MINUTOS — o conjunto de nomes reconhecidos mudava de um bloco de status para o outro com a party window estavel em 4 linhas."
created: 2026-08-25T00:00:00Z
updated: 2026-08-25T13:40:00Z
---

## Current Focus

bug_class: Bohrbug — deterministico; reproduzido offline com os pixels REAIS da
  coroa (Evidence fase-3)
status: CAUSA RAIZ CONFIRMADA
next_action: nenhuma — correcao commitada em b0b8a0b. CONFERENCIA EM FARM REAL
  AINDA PENDENTE por decisao explicita do usuario ("commitar agora, testo no
  farm"): ele vai testar ao vivo DEPOIS do commit, o mesmo caminho da sessao
  anterior. Se o teste ao vivo falhar, reabrir esta sessao — ver
  `verification.pendente_em_farm_real` na Resolution. Nada mais a fazer offline:
  os seis sinais do guardrail passaram e a mutacao esta 12/12.

reasoning_checkpoint:
  hypothesis: >
    A identidade de um membro e pontuada contra UM retrato calibrado, num UNICO
    alinhamento de pixel, e o scanner nao tem como perceber nem contar que aquele
    retrato parou de casar. Entao qualquer mudanca PERMANENTE em como o jogo
    desenha aquele nome apaga o membro do reconhecimento para sempre, em silencio.

    A instancia concreta que aconteceu: a COROA DO LIDER. A calibracao foi feita
    com o Yazalaque lider (nenhuma das 4 assinaturas em `calibration.json` tem
    coroa — medido). As 10:03:21 ele entrou numa party de OUTRO lider. O lider
    ocupa a linha 1 e ganha a coroa, que empurra o texto 10 px para a direita.
    `_correlacionar` le `matchTemplate(...)[0, 0]` — so a origem — e o casamento
    do membro contra a PROPRIA assinatura cai para 0.266 contra um limiar de
    0.75. Nao volta nunca: nem com o tempo, nem com reinicio do scanner, porque
    a assinatura gravada e fixa.
  confirming_evidence:
    - "MEDIDO na fixture: um membro calibrado SEM coroa que vira lider pontua 0.266 contra a propria assinatura, enquanto os outros tres da MESMA party pontuam 0.960 / 0.957 / 0.992. Um linha morta, tres perfeitas — a assinatura exata do log."
    - "MEDIDO: `_correlacionar` no alinhamento fixo tem tolerancia ZERO. 1 px de deslocamento derruba o casamento do mesmo nome contra si mesmo de 1.000 para 0.24-0.47 (horizontal) e 0.40-0.47 (vertical). O limiar e 0.75. Nao ha margem nenhuma."
    - "MEDIDO em `calibration.json` (a calibracao REAL daquela sessao): nenhuma das 4 assinaturas tem coroa — todas comecam na coluna 0/1. Logo o Yazalaque era o lider quando calibrou, e nenhum retrato cobre o estado 'com coroa'."
    - "MEDIDO na fixture com coroa REAL: a coroa ocupa as colunas 0..5, ha uma lacuna de 4 colunas em branco, e o nome so comeca na coluna 10. Desvio = 10 px."
    - "LOG, tres partys, tres previsoes, tres acertos: party 09:47 (Yazalaque lider) todas as linhas reconhecidas; party 10:03 (entrou em party alheia, logo NAO e lider) linha 1 morta por 2 HORAS, inclusive apos o REINICIO do scanner as 10:46:57; party 12:02 (ele entra e os outros entram depois — ele e o lider) linha 1 volta a ser reconhecida."
    - "LOG 10:26:06 — tres das quatro linhas voltam a ser reconhecidas DE UMA VEZ, sozinhas, sem intervencao. Degradacao global (drift, calibracao ruim) nao se cura sozinha; a linha 1 nao se curou nunca."
  falsification_test: >
    Se a hipotese for falsa, uma assinatura calibrada SEM coroa deve continuar
    casando quando o membro passa a exibir a coroa. Testado com os pixels reais
    da coroa na fixture: casa 0.266 contra um limiar de 0.75 — REFUTA a
    alternativa, CONFIRMA a hipotese.

    Segundo teste: se a causa fosse deslocamento da regiao capturada, TODAS as
    linhas cairiam juntas (o recorte de cada linha e `icone_y + i*passo +
    nome_dy` — deslocamento uniforme). O log mostra uma linha morta e tres vivas
    ao mesmo tempo, por duas horas. REFUTA o drift.
  fix_rationale: >
    Duas partes, cada uma atacando uma metade da causa raiz.

    (1) A COROA. Um SEGUNDO passe, que so olha as linhas que o passe atual
        deixou sem nome e so usa as assinaturas que ele nao consumiu. Ele testa
        UMA hipotese a mais, e nao um leque: se a mascara do recorte tem um bloco
        de texto inicial seguido de uma LACUNA de >=4 colunas em branco, esse
        bloco e um ornamento (a coroa), e o nome comeca depois dele. Reancora e
        pontua no alinhamento fixo, com limiar e margem MAIORES que os do passe
        normal.

        Por que a lacuna e um discriminador honesto e nao um chute: medido em 10
        assinaturas reais de 3 calibracoes independentes, TODO nome sem coroa e
        UM unico bloco (zero lacunas >3). A unica assinatura que se parte em dois
        blocos e justamente a do lider com coroa. Nao ha zona cinzenta.

        Por que NAO voltar ao `matchTemplate(...).max()`: medido de novo agora,
        um deslize de 0..14 px para a direita leva o pior casamento ERRADO de
        0.371 para 0.579 e come a folga ate o limiar de 0.379 para 0.171. Foi o
        que produziu o bug do "entra e sai". O segundo passe nao e um deslize: e
        um alinhamento so, escolhido pelo conteudo do proprio recorte.

    (2) O SILENCIO. O scanner conta e reclama de cegueira de CAPTURA
        (`ticks_cego` + o aviso "pode ter sido ARRASTADA... rode calibrar.bat"),
        mas nao conta nada sobre IDENTIDADE. Uma linha ocupada e sem nome por N
        leituras seguidas passa duas horas sem uma palavra. Passa a contar e a
        avisar, com a causa provavel e o remedio. Isto e o que garante que a
        proxima causa — uma que ninguem previu — nao custe outras duas horas.
  blind_spots: >
    (a) Nao tenho os PIXELS da sessao de 10:03 (nao havia gravacao ligada). Que
        a linha 1 era o TioMad de coroa, e nao um estranho sem assinatura, e
        INFERENCIA — forte, mas inferencia. O que a sustenta: em 10:17:44 saiu
        exatamente uma pessoa e, em 10:26:06, as linhas 2/3/4 sao J4guar/Korzis/
        Kaus; se quem saiu fosse o ocupante da linha 1, o J4guar teria subido
        para a linha 1, e ele esta na 2. Logo o ocupante da linha 1 ficou ali de
        10:03 a 11:59 sem nunca ser reconhecido.
        A UNICA testemunha possivel foi consultada no checkpoint — perguntei ao
        usuario quem estava na linha 1 daquela party e a resposta foi "nao
        lembro". Entao isto FICA como ponto cego, no mesmo grau de confianca com
        que foi escrito: nao ha pixels gravados daquela sessao e nao ha memoria
        humana para cruzar com o log. Nao promovo a inferencia a prova.
        A correcao NAO depende de qual das duas era: se era um estranho,
        "Membro 1" era a resposta honesta e a parte (2) e que passa a dize-lo em
        voz alta; se era o TioMad de coroa, a parte (1) o recupera.
    (b) A parte (1) so cobre ornamento a ESQUERDA do nome. Um ornamento a
        direita, ou uma troca de cor que mude a mascara, continua sem cobertura —
        agora com a diferenca de que a parte (2) reclama.
    (c) A piscada das linhas 2/3/4 NAO e corrigida aqui. Medida: o casamento
        aguenta ~20-40 pixels claros de cenario invadindo o recorte, ou ~40% de
        perda do texto, antes de cair de 0.75. E degradacao gradual e que se
        cura sozinha — incomoda, mas nao produz o sumico permanente. Fica
        registrado em known_limitations.
  candidate_causes:
    - "code — `_correlacionar` pontua num alinhamento unico com mascara binaria esparsa: tolerancia zero a deslocamento (CONFIRMADO por medicao)"
    - "data — ha UMA assinatura por membro, mas o jogo desenha o mesmo membro em DOIS estados (com e sem coroa). O conjunto de retratos e incompleto por construcao (CONFIRMADO: nenhuma das 4 assinaturas de `calibration.json` tem coroa)"
    - "code/observabilidade — nao existe contador nem aviso para 'linha ocupada e sem nome ha N leituras'; a falha de identidade e estruturalmente invisivel (CONFIRMADO por leitura de codigo: so `ticks_cego` existe)"
    - "environment — deslocamento da regiao capturada: ELIMINADO. A regiao e ancorada na JANELA (`party_window_na_janela`), entao mover a janela nao desloca nada; e um deslocamento derrubaria as 4 linhas juntas, nao uma."
    - "environment/config — `conferir_geometria` so roda no arranque: verdadeiro, mas irrelevante aqui. Ele compara o ARRANJO DE MONITORES, que nao mudou (a mesma string esta em `calibration.json` e nas fixtures)."
  and_gate: >
    SIM para o sintoma completo, e e por isso que a correcao tem duas partes.
    (1) o membro ter mudado de estado visual (virou lider) E (2) o scanner nao
    ter como perceber que parou de reconhecer. Sozinha, (1) seria um incomodo de
    um membro sem nome que o usuario notaria e resolveria com `calibrar.bat`.
    Sozinha, (2) e uma divida latente. Juntas produziram duas horas de operacao
    cega para identidade — e, via a limitacao travada por teste da sessao
    anterior, saidas reais passando caladas.

hypothesis_atual: >
  DUAS causas distintas, em categorias diferentes, produzindo o mesmo sintoma
  "Membro N":

  (A) PERMANENTE, so na LINHA 1 — a COROA DO LIDER. A calibracao foi feita com o
      Yazalaque LIDER da party; o lider nao aparece na propria party window,
      entao NENHUMA assinatura foi gravada com coroa. As 09:59:48 o Yazalaque
      saiu da party e as 10:03:21 entrou numa party de OUTRO lider. O lider passa
      a ocupar a linha 1 COM coroa, o texto e empurrado para a direita, e
      `_correlacionar` — que pontua so no alinhamento calibrado — nunca mais
      reconhece esse membro. E exatamente o caso que identidade.py:71-73 declara
      sem cobertura ("o membro calibrado SEM coroa que depois VIRA lider").

  (B) INTERMITENTE, nas demais linhas — degradacao de score na faixa 0.6-0.75,
      que faz o casamento piscar em torno de LIMIAR_DE_CASAMENTO=0.75.

hypothesis_anterior_REFUTADA: >
  `_correlacionar` (identidade.py:182) pontua a assinatura em UM alinhamento
  fixo — le `matchTemplate(...)[0, 0]`, ou seja, so o casamento exato na
  origem do recorte. Alguns pixels de drift na regiao capturada empurram a
  correlacao para perto do limiar de 0.75, e o casamento passa a PISCAR:
  ora acima, ora abaixo, com a cena praticamente identica.

  `conferir_geometria` so roda no arranque, entao uma janela do jogo que se
  moveu no meio da sessao nunca e detectada — o scanner segue recortando o
  lugar errado por tempo indeterminado, sem nunca reclamar.

  A falha de captura de 09:59-10:03 e o gatilho suspeito: alguma coisa mudou de
  lugar durante a cegueira, e ao voltar a enxergar o recorte ja nao estava mais
  alinhado com as assinaturas calibradas.

impact: >
  Isto e o GATILHO do bug ja corrigido em [[saida-fantasma-troca-de-slot]], nao
  a mentira em si — aquela correcao segura mesmo com reconhecimento ruim. Mas
  enquanto isto nao for resolvido o scanner opera cego para identidade, e a
  limitacao deliberada travada por teste (se quem sai ja aparecia como
  `Membro N`, NENHUM aviso e enviado) vira silencio na pratica: exatamente o
  evento que o projeto existe para anunciar passa calado.

## Symptoms

expected: >
  O reconhecimento de nomes sobrevive a pequenos deslocamentos da janela do
  jogo e se recupera sozinho depois de uma falha de captura. Se a geometria
  realmente saiu de lugar, o scanner percebe e avisa em vez de seguir recortando
  a regiao errada em silencio.

actual: >
  09:59:50 - 10:03:16  [SEM VISAO]  (falha de captura, ~3.5 min)
  10:03:24  Membro 1  J4guar    Membro 3              <- 3 de 4 nomes perdidos
  10:05:57  Membro 1  J4guar    Membro 3  Membro 4
  10:10:00  Membro 1  J4guar    Membro 3  Membro 4
  10:10:30  Membro 1  Membro 2  Membro 3  Korzis      <- J4guar sai, Korzis entra
  10:12:00  Membro 1  Membro 2  Membro 3  Korzis
  Com 4 linhas o tempo todo, o conjunto de nomes reconhecidos muda entre blocos
  de status. Nao se recuperou sozinho ate o fim da sessao.

errors: nenhuma excecao — o scanner nao quebra, apenas para de reconhecer

timeline: >
  Funcionou perfeitamente das 09:49 as 09:59 NA MESMA SESSAO (ver Evidence
  fase-1 de [[saida-fantasma-troca-de-slot]]), inclusive atravessando uma saida
  e uma volta com mudanca de ordem dos slots. A degradacao comeca exatamente
  apos a cegueira de 09:59-10:03. Isto descarta as assinaturas como causa.

reproduction: >
  Offline: pegar os frames/fixtures da sessao e deslocar a regiao capturada em
  N pixels, medindo o score de `_correlacionar` em funcao de N. Esperado: queda
  abrupta perto do limiar de 0.75 com poucos pixels de deslocamento.

## Evidence

- timestamp: fase-1
  checked: logs/scanner.log — linha do tempo COMPLETA do reconhecimento, 09:47 as 12:14
  found: |
    09:47:43  TioMad | J4guar | Kaus | Korzis      <- 12 min sem UMA falha
    09:59:48  YAZALAQUE SAIU OU FOI REMOVIDO DA PARTY
    09:59:50  [SEM VISAO] ... ate 10:03:16
    10:03:21  YAZALAQUE ENTROU EM PARTY            <- entrou numa party ALHEIA
    10:03:24  Membro | J4guar | Membro
    10:04:25  Membro | J4guar | Membro | Kaus      <- Kaus reconhecido na volta
    10:05:57  Membro | J4guar | Membro | Membro
    10:10:30  Membro | Membro | Membro | Korzis
    10:20:32  Membro | Membro | Membro | Kaus
    10:26:06  Membro | J4guar | Korzis | Kaus      <- recuperou SOZINHO
    10:28:06  Membro | J4guar | Membro | Kaus
    10:28:36  Membro | J4guar | Korzis | Kaus
    10:30:38  Membro | Membro | Membro | Membro
    10:37:42  Membro | J4guar | Korzis | Kaus
    10:46:57  [reajustando] Membro | J4guar | Korzis | Kaus   <- REINICIO do scanner
    ... ate 11:59  o modal e sempre  Membro | J4guar | Korzis | Kaus
    12:00:04  YAZALAQUE SAIU / 12:02:45 YAZALAQUE ENTROU EM PARTY (party NOVA)
    12:02:44  [reajustando] Kaus                   <- linha 1 volta a ser reconhecida
    12:04:44  Kaus | Korzis
  implication: >
    Tres fatos que mudam o diagnostico inteiro:

    1. A LINHA 1 NUNCA MAIS E RECONHECIDA entre 10:03 e 11:59 — nem depois do
       REINICIO do scanner as 10:46:57, com a mesma calibracao. Falha permanente,
       nao piscada. As linhas 2/3/4 piscam e se recuperam sozinhas.
    2. Kaus e Korzis foram reconhecidos DEPOIS da suposta cegueira (10:04:25,
       10:10:30, 10:20:32), e as 10:26:06 tres dos quatro voltaram de uma vez sem
       nenhuma intervencao.
    3. Na party NOVA formada as 12:02 a linha 1 volta a ser reconhecida (Kaus).

    O fato 1 sozinho ja separa as duas causas: um deslocamento da regiao
    capturada atingiria TODAS as linhas por igual (o recorte de cada linha e
    `icone_y + i*passo + nome_dy`, deslocamento uniforme). O que atinge UMA linha
    so, de forma permanente, e algo proprio daquela linha — e a linha 1 e a do
    LIDER.

- timestamp: fase-1
  checked: quem estava em cada linha, reconstruido do log
  found: |
    party 09:47-09:59 : TioMad(L1) J4guar(L2) Kaus(L3) Korzis(L4), Yazalaque LIDER
    party 10:03-11:59 : ?(L1) J4guar(L2) Korzis(L3) Kaus(L4)   -> L1 = TioMad
      prova: 10:26:06 mostra "Membro | J4guar | Korzis | Kaus" — sobra so o
      TioMad para a linha 1, e ele e o unico da lista que nunca reaparece.
    party 12:02-      : Kaus(L1) Korzis(L2) ...  -> L1 volta a ser reconhecida
  implication: >
    As 10:03 o Yazalaque ENTROU numa party que ja existia (J4guar e outros ja
    estavam la as 10:03:24), logo o lider e outra pessoa — o TioMad, na linha 1.
    As 12:02 o Yazalaque ENTROU e os outros entraram DEPOIS (KORZIS ENTROU as
    12:04:25), o padrao de quem CRIOU a party: ele volta a ser lider, o lider
    nao aparece na propria party window, e a linha 1 volta a ser um membro comum
    — reconhecido normalmente. O sintoma acompanha exatamente quem e o lider.

- timestamp: fase-1
  checked: l2scanner/identidade.py:58-75 (o comentario "PENDENCIA CONHECIDA")
  found: >
    O proprio codigo declara este caso como o unico sem cobertura: "O caso que
    continua sem cobertura e o membro calibrado SEM coroa que depois VIRA lider.
    Quando houver um frame real dessa transicao, a resposta e gravar DUAS
    assinaturas por membro (com e sem coroa) e continuar pontuando no alinhamento
    fixo."
  implication: >
    Nao e um bug desconhecido — e uma divida tecnica registrada, esperando o
    frame real que agora existe no log. E o `test_o_lider_e_reconhecido` que
    passa hoje NAO cobre isso: na fixture `party_com_lider.png` a calibracao foi
    gravada com o lider JA de coroa, entao o alinhamento fixo casa. O teste
    protege o sentido contrario (calibrado COM coroa), nao a transicao.

- timestamp: fase-2
  checked: "quanto deslocamento `_correlacionar` aguenta?" — medido na fixture
    tests/fixtures/identidade, cada nome contra a PROPRIA assinatura
  found: |
    deslocamento HORIZONTAL (px):  0      1      2      3      6     10
                        Korzis  1.000  0.318  0.247  0.294  0.200  0.224
                        J4guar  1.000  0.309  0.171  0.427  0.447  0.092
                        Kaus    1.000  0.265  0.127  0.265  0.265  0.035
                        TioMad  1.000  0.239  0.188  0.256  0.324  0.070

    deslocamento VERTICAL (px):    0      1      2      3      4      5
                        Korzis  1.000  0.424  0.318  0.259  0.156  0.193
                        TioMad  1.000  0.459  0.391  0.357  0.222  0.239

    LIMIAR_DE_CASAMENTO = 0.75
  implication: >
    TOLERANCIA ZERO. UM pixel de desalinhamento derruba o casamento do nome
    contra si mesmo de 1.000 para 0.24-0.47 — muito abaixo do limiar. Nao existe
    "degradar perto do limiar" por deslocamento: e um precipicio.

    Isto tem duas consequencias. Primeira: a piscada das linhas 2/3/4 NAO pode
    ser deslocamento — deslocamento nao pisca, mata. Segunda: qualquer mudanca
    permanente na posicao do texto (a coroa) e fatal e definitiva.

- timestamp: fase-2
  checked: "entao o que faz as linhas 2/3/4 piscarem?" — tolerancia a ruido e a
    perda de texto, medida na mesma fixture
  found: |
    pixels claros de cenario invadindo o recorte:
      ruido:   0      10     20     30     40     60
      Korzis 1.000  0.947  0.904  0.863  0.829  0.771
      J4guar 1.000  0.916  0.849  0.797  0.749  0.023  <- guarda de contaminacao
      Kaus   1.000  0.828  0.722  0.000  0.000  0.000  <- 22 px de assinatura

    perda de pixels do texto (nome atenuado/escurecido):
      perda%:  0      10     20     30     40     50
      qualquer nome ~ 1.000  0.950  0.895  0.840  0.775  0.705
  implication: >
    Aqui SIM a degradacao e gradual: ~20-40 pixels de cenario claro, ou ~40% de
    perda do texto, para cruzar o limiar. E o mecanismo da piscada — e ele se
    cura sozinho quando a cena muda, que e exatamente o que o log mostra as
    10:26:06. Mecanismo DIFERENTE do da linha 1, que nunca se curou.

    Nota lateral: a guarda de contaminacao (`FATOR_MAXIMO_DE_CONTAMINACAO=2.0`)
    e muito mais apertada para nomes curtos — o Kaus tem 22 px de assinatura,
    entao 45 pixels claros no recorte ja zeram o par dele. Nao e a causa desta
    sessao, mas explica por que nomes curtos piscam mais.

- timestamp: fase-3
  checked: REPRODUCAO OFFLINE com os pixels REAIS da coroa. Na fixture
    `party_ordem_original.png` o Korzis E o lider (tem coroa). Construi a
    assinatura "Korzis SEM coroa" a partir do proprio recorte — apagando a coroa
    e trazendo o nome para a origem — e rodei `identificar_linhas` com ela.
    Isso e exatamente "membro calibrado antes de virar lider".
  found: |
    a coroa ocupa as colunas 0..5, lacuna de 4 colunas, nome a partir da 10.

    L0 esperado=Korzis  ->  None    conf=0.266  2o=0.172   <<< some
    L1 esperado=J4guar  ->  J4guar  conf=0.960
    L2 esperado=Kaus    ->  Kaus    conf=0.957
    L3 esperado=TioMad  ->  TioMad  conf=0.992
  implication: >
    O sintoma do log reproduzido com pixel real, sem jogo, sem captura: UMA
    linha morta e as outras tres perfeitas, no mesmo frame. Bohrbug.

    0.266 nao esta "perto do limiar": esta a 0.484 dele. Nenhuma espera, nenhuma
    mudanca de cenario e nenhum reinicio do scanner traz isso de volta — o que
    casa com o log, onde a linha 1 continuou morta ATE DEPOIS do reinicio das
    10:46:57.

- timestamp: fase-3
  checked: "a lacuna depois da coroa e um discriminador seguro?" — estrutura de
    blocos de texto de 10 assinaturas reais, de 3 calibracoes independentes
  found: |
    calibracao REAL da sessao (calibration.json), lacuna maxima > 3 colunas:
      TioMad  1 bloco (0..21)      J4guar  1 bloco (0..20)
      Kaus    1 bloco (1..10)      Korzis  1 bloco (1..16)
    fixture/identidade:
      Korzis  2 blocos (0..5) lacuna=4 (10..37)   <<< o unico, e e o LIDER
      J4guar  1 bloco   Kaus 1 bloco   TioMad 1 bloco
    fixture/party_estavel:
      Kaus    1 bloco   Korzis 1 bloco
  implication: >
    9 de 10 assinaturas sao UM bloco unico. A unica que se parte em dois e a do
    lider com coroa, e a lacuna dela e de 4 colunas. Nao ha zona cinzenta —
    mesmo padrao de evidencia que sustenta `FATOR_MAXIMO_DE_CONTAMINACAO`.
    Reancorar pela lacuna e ler uma estrutura que so a coroa produz, nao chutar.

- timestamp: fase-3
  checked: "e voltar ao casamento deslizante, resolveria?" — remedido agora, so
    para a direita (o lado para onde a coroa empurra), 0..14 px
  found: |
    CERTOS  : fixo min 0.946   deslizado min 0.946   ganho max +0.000
    ERRADOS : fixo max 0.371   deslizado max 0.579   ganho max +0.376
    folga ate o limiar — fixo 0.379   deslizado 0.171
  implication: >
    Reproduz os numeros que identidade.py ja documentava. O deslize nao da NADA
    a quem esta certo e da quase quatro decimos a quem esta errado: come 55% da
    folga. Descartado. A correcao tem que testar UM alinhamento a mais, escolhido
    pelo conteudo, e nao um leque de 15.

- timestamp: checkpoint
  checked: perguntei ao usuario quem estava na LINHA 1 da party de 10:03 — a
    unica fonte fora do log, ja que nao ha pixels gravados daquela sessao
  found: >
    "Nao lembro."
  implication: >
    O ponto cego (a) continua ponto cego, e agora por esgotamento: nao ha pixels
    e nao ha memoria. A reconstrucao da Evidence fase-1 ("sobra so o TioMad para
    a linha 1") segue valendo como INFERENCIA a partir do log — e so isso. Nao
    sobe para fato.

    Nao muda nada na correcao, e esse e o ponto: ela foi desenhada para nao
    depender da resposta. Se era o TioMad de coroa, a parte (1) o recupera; se
    era um estranho sem assinatura, "Membro 1" sempre foi a resposta honesta e a
    parte (2) e que passa a dize-la em voz alta em vez de calar por duas horas.

## Eliminated

- hypothesis: "o reconhecimento desabou por DRIFT da regiao capturada (a janela do jogo ou a party window se moveu durante a cegueira de 09:59-10:03)"
  why: >
    Era a hipotese herdada de [[saida-fantasma-troca-de-slot]]. Tres evidencias
    independentes a refutam:
    (1) o recorte de cada linha e `icone_y + i*passo + nome_dy` — um deslocamento
        e UNIFORME, derrubaria as 4 linhas juntas. O log mostra 1 morta e 3 vivas
        simultaneamente, por 2 horas.
    (2) medido: 1 px de deslocamento leva o casamento a 0.24-0.47. Se houvesse
        drift, NINGUEM seria reconhecido — e Kaus (10:04:25), Korzis (10:10:30) e
        os tres de uma vez as 10:26:06 foram.
    (3) a regiao e ancorada na JANELA (`party_window_na_janela`), nao na tela:
        arrastar a janela do jogo nao desloca o recorte.
  timestamp: fase-1/fase-2

- hypothesis: "`conferir_geometria` so rodar no arranque e a causa"
  why: >
    Verdadeiro como divida, falso como causa. Ele compara o ARRANJO DE MONITORES
    (`3440x1440+0+0;1920x1080+1920+-1084;1920x1080+0+-1080`), e essa string e
    identica em `calibration.json` e nas fixtures — a tela nao mudou. Alem disso
    ele nao teria como pegar uma coroa.
  timestamp: fase-2

- hypothesis: "a party de 10:03 era so gente fora da lista, entao 'Membro N' estava certo"
  why: >
    Nao explica 10:26:06, quando as linhas 2/3/4 viram J4guar/Korzis/Kaus de uma
    vez, sem nenhum evento de entrada ou saida entre 10:25:36 e 10:26:06. Eram as
    mesmas pessoas o tempo todo; o que mudou foi o RECONHECIMENTO.
    (Continua em aberto apenas quem ocupava a LINHA 1 — ver blind_spot (a).)
  timestamp: fase-1

- hypothesis: "as assinaturas calibradas estao ruins ou desatualizadas"
  why: >
    Funcionaram perfeitamente das 09:49 as 09:59 na mesma sessao, com a mesma
    calibracao, atravessando troca de slots. O que mudou foi a cegueira no meio.

## Resolution

root_cause: >
  A identidade de um membro e pontuada contra UM retrato calibrado, num UNICO
  alinhamento de pixel, e o scanner nao tem como perceber que aquele retrato
  parou de casar. Sao duas metades, e o sintoma completo exige as duas.

  (1) TOLERANCIA ZERO A DESLOCAMENTO. `_correlacionar` le
      `matchTemplate(...)[0, 0]` — so a origem — sobre uma mascara binaria
      esparsa. Medido: UM pixel de deslocamento derruba o casamento de um nome
      contra a PROPRIA assinatura de 1.000 para 0.24-0.47, com o limiar em 0.75.
      Nao e degradacao, e precipicio.

      A instancia concreta e a COROA DO LIDER. A calibracao da sessao foi feita
      com o Yazalaque lider — e o lider nao aparece na propria party window,
      entao NENHUMA das quatro assinaturas em `calibration.json` tem coroa
      (verificado: todas comecam na coluna 0 ou 1). As 09:59:48 ele saiu da
      party; as 10:03:21 entrou numa party de OUTRO lider. O lider ocupa a linha
      1 e a coroa empurra o texto 10 px para a direita. Reproduzido offline com
      os pixels REAIS da coroa: 0.266 contra a propria assinatura, enquanto os
      outros tres da mesma party casam 0.960 / 0.957 / 0.992.

      Nao se recupera com o tempo nem com reinicio, porque a assinatura gravada
      nao muda — e o log confirma: a linha 1 seguiu morta ate depois do reinicio
      do scanner as 10:46:57, e so voltou quando a party foi refeita as 12:02
      com o usuario lider de novo.

  (2) A FALHA ERA INVISIVEL. O scanner sempre soube contar cegueira de CAPTURA
      (`ticks_cego`) e reclamar dela com um remedio ("pode ter sido ARRASTADA...
      rode calibrar.bat"). Nao havia contador nem aviso nenhum para "estou
      vendo a linha e nao faco ideia de quem esta nela". Por isso o defeito (1)
      custou DUAS HORAS em vez de dois minutos, e o usuario so descobriu por
      causa dos alertas errados que vieram depois.

  Somado a limitacao travada por teste da sessao anterior (quem ja aparece como
  "Membro N" nao gera aviso ao sair), reconhecimento parado em silencio vira
  saida real passando calada — exatamente o evento que o projeto existe para
  anunciar.

fix: >
  (1) SEGUNDO PASSE CONSCIENTE DO ORNAMENTO, em `l2scanner/identidade.py`.
      `_segundo_passe_do_ornamento` faz uma repescagem: le a estrutura do
      proprio recorte, e se a mascara for "bloco, lacuna, bloco" trata o bloco
      inicial como ornamento, reancora o nome e pontua de novo no alinhamento
      fixo.

      O que o torna seguro, em ordem de quanto trabalho cada trava faz:

        - Um nome SEM coroa e um bloco unico, entao o passe nem comeca para ele.
          Medido em 10 assinaturas reais de 3 calibracoes: 9 sao bloco unico
          (nenhuma lacuna acima de 3 colunas) e a unica que se parte em dois e
          justamente a do lider, com lacuna de 4. Sem zona cinzenta.
        - Estritamente ADITIVO: so olha linhas que o primeiro passe deixou sem
          nome, e so usa assinaturas que ele nao consumiu. Nao existe caminho
          por onde ele troque um nome ja dado.
        - UM alinhamento a mais, nunca um leque — e ancorado na primeira coluna
          DA ASSINATURA, nao na coluna 0, porque assinaturas reais comecam na 0
          ou na 1 e 1 px de erro ja e fatal. So para a DIREITA, que e o unico
          lado para onde um ornamento empurra.
        - Cobra mais caro: LIMIAR_DO_ORNAMENTO 0.85 e MARGEM_DO_ORNAMENTO 0.25,
          contra 0.75 / 0.12 do primeiro passe.

      Por que NAO o casamento deslizante: remedido nesta sessao, deslizar 0..14
      px para a direita leva o pior casamento ERRADO de 0.371 para 0.579 e come
      a folga ate o limiar de 0.379 para 0.171. Foi o que produziu o bug do
      "entra e sai".

  (2) O SILENCIO ACABOU, em `l2scanner/sessao.py` e `l2scanner/__main__.py`.
      `Sessao.ticks_sem_reconhecer` conta, POR LINHA, ha quantas leituras
      seguidas ela esta ocupada e sem nome. Ao cruzar
      TICKS_SEM_RECONHECER_PARA_AVISAR (120, ~2 min a 1 Hz) o laco avisa uma vez,
      dizendo QUAL linha, as duas causas possiveis (alguem fora da calibracao,
      ou alguem que virou lider) e o remedio.

      Por linha, e nao global: no caso real as linhas 2/3/4 piscavam enquanto a
      linha 1 estava morta ha duas horas — um contador global seria zerado por
      cada piscada das outras e nunca chegaria ao aviso.

      Cegueira CONGELA a conta, como todo o resto do rastreador. O caso que
      importa nao e o frame preto e sim a party window COBERTA PELO INVENTARIO:
      ela produz linhas ocupadas e sem nome com `ui_visivel` False — os pixels
      de "nao reconheci nada". Conta-la pediria recalibracao por causa de uma
      janela na frente, que e a confusao entre mudanca de VISAO e mudanca de
      REALIDADE que esta familia inteira de bugs vem cometendo.

  (3) Achado no teste de mutacao: a guarda de saida antecipada no topo do
      segundo passe era EQUIVALENTE (o `while` ja nao roda com qualquer um dos
      conjuntos vazio). Removida como codigo morto, com a nota do porque.

verification: |
  SINAL 1 — reproducao offline com os pixels REAIS da coroa
    membro calibrado sem coroa que virou lider, na mesma party:
      antes:  L0 = None (0.266) | J4guar | Kaus | TioMad
      depois: Korzis | J4guar | Kaus | TioMad
    Vizinhos de fronteira: assinatura comecando na coluna 0, 1 e 2 — as tres
    recuperam. Alinhar na coluna 0 fixa falharia em duas delas.

  SINAL 2 — suite completa
    634 testes passando (613 antes + 21 novos). Zero regressoes.

  SINAL 3 — reversao reintroduz o bug
    `git stash` dos tres arquivos de codigo: a reproducao volta a devolver
    L0=None com 0.266, e os 5 testes de `TestReconhecimentoParadoFicaVisivel`
    falham.

  SINAL 4 — mutacao no ponto da correcao (12 mutantes, 12 mortos)
    M1  lacuna do ornamento vira 0 ................. MORTO (10 falhas)
    M2  aceita deslocamento para a ESQUERDA ........ SOBREVIVEU -> teste novo
                                                     `test_so_reancora_para_a_
                                                     DIREITA` -> MORTO
    M3  reancora na coluna 0 (ignora a margem) ..... MORTO (2 falhas)
    M4  limiar do ornamento cai para 0.0 ........... SOBREVIVEU -> mascarado
                                                     pela margem; teste novo
                                                     `test_pontuacao_fraca_nao_
                                                     passa_so_por_estar_sozinha`
                                                     -> MORTO
    M5  margem do ornamento zerada ................. SOBREVIVEU -> mascarado
                                                     pelo limiar; teste novo
                                                     `test_dois_candidatos_
                                                     empatados_nao_viram_cara_
                                                     ou_coroa` -> MORTO
    M6  usa TODAS as assinaturas, nao so as livres .. MORTO
    M7  usa a ULTIMA lacuna em vez da primeira ...... SOBREVIVEU -> teste novo
                                                     `test_a_coroa_e_a_PRIMEIRA_
                                                     lacuna` -> MORTO
    M8  guarda de saida antecipada .................. EQUIVALENTE -> codigo
                                                      morto REMOVIDO
    M8' segundo passe olha linhas ja nomeadas ....... SOBREVIVEU -> teste novo
                                                      `test_o_segundo_passe_
                                                      nunca_RENOMEIA_uma_linha_
                                                      ja_resolvida` -> MORTO
    M9  conta durante a cegueira .................... SOBREVIVEU -> o teste de
                                                      cegueira usava um frame
                                                      SEM linhas, entao nao
                                                      testava nada; trocado
                                                      pela party window coberta
                                                      pelo inventario -> MORTO
    M10 reconhecer nao zera a conta ................. MORTO (2 falhas)
    M11 contador global em vez de por linha ......... MORTO (5 falhas)

    Nota: M4 e M5 sobreviveram porque um mascarava o outro — duas guardas em
    serie, cada uma cobrindo o mutante da outra. Os dois testes novos fixam cada
    guarda isoladamente.

  SINAL 5 — lint
    ruff: 29 erros no projeto — IDENTICO ao baseline em HEAD (4a18941). Nenhum
    introduzido (o unico E741 novo era meu e foi corrigido).

  SINAL 6 — a mensagem de aviso, ponta a ponta
    130 ticks com o nome apagado: o aviso dispara UMA vez por linha, exatamente
    na leitura 120, e a string renderiza com a linha em base 1. (O historico
    deste projeto tem um bug de aridade em chamada de log — bug 1 do docstring
    de sessao.py — entao a renderizacao foi conferida de verdade, e nao so a
    contagem.)

  DETECCAO REAL PRESERVADA, uma a uma:
    calibracao normal, party inteira ........... 4 nomes certos, conf > 0.90  OK
    lider de fora da lista ..................... sem nome (nao empresta)      OK
    assinatura ja consumida .................... sem nome (nao rouba)         OK
    linha ja resolvida pelo 1o passe ........... intocada                     OK
    recorte sujo, 5 a 60 px de ruido ........... None ou o certo, NUNCA outro OK
    party toda reconhecida ..................... nao conta nada              OK

  oracle_type: derived — o esperado nao vem de um valor observado, vem de duas
  propriedades: a estrutura do dominio (a coroa e um ornamento a esquerda,
  separado por uma lacuna) e a invariante do modulo (o segundo passe e
  estritamente aditivo e preserva unicidade). Vizinhos de fronteira cobertos:
  margem da assinatura 0/1/2, deslocamento negativo/zero/positivo, lacuna
  primeira/ultima, ruido 0/5/10/20/30/60, contador antes/em/depois do limiar.

  pendente_em_farm_real: NAO CONFERIDO EM JOGO ATE O MOMENTO DO COMMIT.
    Todos os seis sinais acima sao OFFLINE — reproducao com os pixels reais da
    coroa, suite, reversao, mutacao, lint e a renderizacao da mensagem. Nenhum
    deles viu o jogo rodando.

    O checkpoint de verificacao humana foi apresentado ao usuario e ele
    respondeu "commitar agora, testo no farm": aceitou fechar a sessao antes da
    confirmacao ao vivo, apoiado na cobertura offline, e foi para uma sessao de
    farm real em seguida — o mesmo caminho de [[saida-fantasma-troca-de-slot]].
    Registrado aqui como PENDENTE, e nao como verificado, porque nao foi
    verificado.

    O que ainda precisa ser conferido em jogo:
      1. numa party em que OUTRA pessoa e lider, o nome dela aparece no
         [vigiando] em vez de "Membro 1";
      2. os demais membros continuam com os nomes certos;
      3. se alguma linha ficar 2 minutos sem nome, o aviso novo aparece no log
         com o numero da linha certo.

    Se qualquer um dos tres falhar, reabrir esta sessao — o commit da correcao e
    b0b8a0b e o estado anterior e d94f3d3. A linha de base para re-conferir e a
    do SINAL 3: revertendo os tres arquivos de codigo, a reproducao offline
    volta a devolver L0=None com 0.266 e os 5 testes de
    `TestReconhecimentoParadoFicaVisivel` voltam a falhar. Se a reversao NAO
    reintroduzir o bug, quem estiver lendo isto esta medindo outra coisa.

files_changed:
  - l2scanner/identidade.py
  - l2scanner/sessao.py
  - l2scanner/__main__.py
  - tests/test_identidade.py (TestMembroQueViraLider, 15 testes)
  - tests/test_sessao.py (TestReconhecimentoParadoFicaVisivel, 6 testes)

commit: b0b8a0b  # fix(identidade): a coroa do lider apagava um membro para
                 # sempre, e ninguem contava isso  (baseline anterior: d94f3d3)

known_limitations:
  - "A PISCADA das demais linhas continua em aberto e NAO foi corrigida aqui. Medida: o casamento aguenta ~20-40 pixels claros de cenario invadindo o recorte, ou ~40% de perda do texto, antes de cair do limiar de 0.75. E gradual e se cura sozinha (o log mostra a recuperacao espontanea as 10:26:06), diferente do sumico permanente da coroa."
  - "A guarda de contaminacao e desproporcionalmente apertada para nomes curtos: o Kaus tem 22 px de assinatura, entao 45 pixels claros no recorte ja zeram o par dele. Explica por que nomes curtos piscam mais. Nao investigado."
  - "O segundo passe so cobre ornamento a ESQUERDA do nome. Ornamento a direita, ou mudanca de cor que altere a mascara, continua sem cobertura — com a diferenca de que agora o aviso de reconhecimento parado reclama."
  - "Quem ocupava a LINHA 1 na sessao real (TioMad de coroa, ou um estranho sem assinatura) nao pode ser provado sem os pixels daquela sessao, que nao foram gravados. Perguntado diretamente no checkpoint, o usuario respondeu que NAO LEMBRA — com isso se esgotaram as duas fontes possiveis, e a atribuicao continua sendo INFERENCIA a partir do log, nao fato. A correcao cobre os dois casos: coroa e recuperada, estranho passa a ser anunciado como nao-reconhecido."
  - "`conferir_geometria` continua rodando so no arranque e olhando so o arranjo de monitores. Nao foi causa aqui, mas segue como divida."
