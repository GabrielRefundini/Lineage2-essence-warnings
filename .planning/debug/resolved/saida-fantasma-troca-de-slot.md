---
status: resolved
trigger: "Rastreador reporta 'saiu da party' para varios membros quando apenas um saiu de fato, e associa nicks errados quando membros trocam de posicao/slot na party window. Evidencia: WhatsApp recebeu 'J4guar: saiu da party', 'Korzis: saiu da party', 'Kaus: saiu da party' as 10:17 quando apenas UM saiu."
created: 2026-08-25T00:00:00Z
updated: 2026-08-25T11:20:00Z
---

## Current Focus

bug_class: Bohrbug — deterministico, reproduzido offline a partir do log real
status: causa raiz CONFIRMADA por logs/scanner.log 09:49-10:18 + leitura de codigo

reasoning_checkpoint:
  hypothesis: >
    A hipotese inicial ("estado ancorado no indice do slot") esta ERRADA — o
    estado JA e guardado por identidade (rastreador.py:207) e o reconhecimento
    JA sobrevive a compactacao de linhas (provado as 09:56:28, quando o Kaus
    saiu, o Korzis subiu de linha e continuou reconhecido).

    A causa real e o campo `_EstadoInterno.linhas_quando_visto`. Ele guarda
    quantas linhas a party window tinha DA ULTIMA VEZ QUE ESTE MEMBRO FOI
    RECONHECIDO, e a guarda de saida pergunta `linhas_agora < linhas_quando_visto`
    a CADA frame. Enquanto o membro nao volta a ser reconhecido esse retrato
    envelhece indefinidamente, e a pergunta deixa de ser "a janela encolheu
    quando ele sumiu?" e vira "a janela encolheu em ALGUM momento desde a
    ultima vez que eu o reconheci?".

    Consequencia: N membros com reconhecimento degradado ficam todos com o
    retrato congelado em 4. A PRIMEIRA saida real de QUALQUER pessoa derruba a
    contagem para 3 e destranca a guarda dos N ao mesmo tempo. Um evento real
    vira N alertas, no mesmo segundo, com os nomes errados.
  confirming_evidence:
    - "logs/scanner.log 10:17:44 — J4GUAR, KAUS e KORZIS saem no MESMO segundo; os tres contadores cruzaram o limiar no mesmo frame"
    - "logs/scanner.log 10:17:32 (4 linhas) -> 10:18:02 (3 linhas) — a janela encolheu exatamente 1; o dominio permite no maximo 1 saida"
    - "logs/scanner.log 10:03:24 em diante — o reconhecimento desabou: 'Membro 1 / J4guar / Membro 3'. J4guar e Kaus passaram MINUTOS fora de `presentes` com o retrato preso em 4"
    - "logs/scanner.log 10:10:00 -> 10:10:30 — J4guar sai do reconhecimento e Korzis entra, com 4 linhas o tempo todo: o pisca-pisca que produz identidades nomeadas obsoletas em `_membros`"
    - "rastreador.py:857 — `linhas_quando_visto` so e reescrito quando o membro esta em `presentes`; rastreador.py:820 le esse retrato a cada frame"
    - "rastreador.py:832 — `contador_saida` so e zerado quando o membro e VISTO; ausencia continuada acumula ate o limiar"
  falsification_test: >
    Se a hipotese for falsa, uma party de 4 com dois membros fora do
    reconhecimento ha varios frames NAO deve gerar alerta quando um terceiro
    membro sai de verdade. Reproduzido offline: gera 3 alertas (2 falsos).
  fix_rationale: >
    A resposta certa e TRAVAR o veredito no instante em que o membro some, em
    vez de reavalia-lo contra um retrato velho — exatamente o espelho do que
    `apareceu_com_crescimento` ja faz do lado da entrada (rastreador.py:873).
    No frame da PRIMEIRA ausencia o retrato ainda esta fresco, entao a pergunta
    e honesta; nos frames seguintes ela e substituida pelo valor travado.
    Somado a isso, a lei de conservacao do dominio: a janela so perde uma linha
    por pessoa que sai, entao o numero de saidas confirmadas num frame nunca
    pode passar de quanto a janela encolheu naquele frame.
  blind_spots: >
    (a) NAO corrige a degradacao do reconhecimento apos 10:03 — essa e a
        segunda condicao do AND e continua em aberto (ver Evidence fase-4).
    (b) Se o membro que sai de verdade JA estava fora do reconhecimento, a
        saida dele passa calada. Preco aceito e consistente com o resto do
        projeto: silencio e recuperavel, nome errado nao.
    (c) Saida real + piscada de reconhecimento de outro membro no MESMO frame
        congela os dois. Mitigado pelo debounce de 5 leituras.
  candidate_causes:
    - "code — `linhas_quando_visto` e um retrato por membro que envelhece; a guarda de saida o le como se fosse o frame atual (CONFIRMADO)"
    - "code — nenhuma lei de conservacao limita quantas saidas podem ser confirmadas num mesmo frame (CONFIRMADO)"
    - "environment/calibration — a party window ou a janela do jogo saiu de lugar durante a cegueira de 09:59-10:03, degradando o casamento de nomes a partir de 10:03 (CONFIRMADO como gatilho, nao corrigido aqui)"
    - "data — descartado: as assinaturas funcionaram perfeitamente das 09:49 as 09:59 na mesma sessao"
  and_gate: >
    SIM — exige as duas condicoes ao mesmo tempo. (1) reconhecimento falhando
    de forma persistente para >=1 membro, para que a identidade dele fique
    obsoleta em `_membros` com o retrato preso; E (2) uma saida REAL de
    qualquer pessoa, que e o unico jeito de a contagem cair e destrancar a
    guarda de todos os obsoletos de uma vez. Nenhuma das duas sozinha produz o
    bug: sem (2) a guarda bloqueia; sem (1) so o verdadeiro faltante sai do
    conjunto e o alerta e correto.

next_action: nenhuma — correcao commitada em fb0862c. CONFERENCIA EM FARM REAL AINDA
  PENDENTE por decisao explicita do usuario ("commitar agora e ja vou testar agora
  tambem"): ele foi testar ao vivo DEPOIS do commit. Se o teste ao vivo falhar,
  reabrir esta sessao — ver `verification.pendente_em_farm_real` na Resolution.

## Symptoms

expected: >
  Quando UM membro sai da party, o scanner envia UM aviso, nomeando corretamente
  quem saiu. Os demais membros continuam rastreados com os nomes certos, mesmo
  que tenham subido de posicao na janela.

actual: >
  10:17  J4guar: saiu da party.
  10:17  Korzis: saiu da party.
  10:17  Kaus: saiu da party.
  Tres avisos no mesmo minuto quando apenas um membro saiu de fato.
  Alem disso, nicks passam a ser associados ao membro errado depois que a
  ordem das linhas muda.

errors: nenhuma excecao — o scanner nao quebra, apenas conclui errado

timeline: observado em sessao de farm real; nao ha indicacao de que ja tenha
  funcionado corretamente sob troca de slot (provavel bug latente desde sempre,
  so exposto quando alguem sai com membros abaixo dele)

reproduction: >
  Rodar o scanner com uma party de 4-5 membros e fazer o membro que NAO esta na
  ultima linha sair da party. Esperado offline: reproduzir com frames/fixtures
  em tests/fixtures simulando a lista de membros antes e depois da saida.

## Evidence

- timestamp: fase-1
  checked: logs/scanner.log 09:49:44 - 09:57:48 (mesma sessao, ANTES do bug)
  found: |
    09:49:44  TioMad  J4guar  Kaus  Korzis          (4 linhas, todos reconhecidos)
    09:56:28  KAUS SAIU DA PARTY
    09:56:47  TioMad  J4guar  Korzis                (3 linhas)
    09:57:26  KAUS ENTROU NA PARTY
    09:57:48  TioMad  J4guar  Korzis  Kaus          (4 linhas, ordem NOVA)
  implication: >
    HIPOTESE INICIAL REFUTADA. O Kaus saiu da linha 2, o Korzis subiu de 3 para
    2 e continuou sendo reconhecido pelo nome; na volta o Kaus ocupou a linha 3
    e a ordem ficou diferente da calibrada. UM alerta, com o nome certo, nas
    duas pontas. Troca de slot, sozinha, NAO quebra nada — nem o
    reconhecimento (o recorte do nome e `icone_y + i*passo + nome_dy`, uniforme
    por linha) nem a atribuicao (o estado e chaveado por identidade).

- timestamp: fase-2
  checked: logs/scanner.log 09:59:48 - 10:12:00 (a degradacao)
  found: |
    09:59:48  YAZALAQUE SAIU OU FOI REMOVIDO DA PARTY
    09:59:50  [SEM VISAO] ... ate 10:03:16   (falha de captura, ~3.5 min)
    10:03:24  Membro 1  J4guar  Membro 3              <- 3 de 4 nomes perdidos
    10:05:57  Membro 1  J4guar  Membro 3  Membro 4
    10:10:00  Membro 1  J4guar  Membro 3  Membro 4
    10:10:30  Membro 1  Membro 2 Membro 3  Korzis     <- J4guar sai, Korzis entra
    10:12:00  Membro 1  Membro 2 Membro 3  Korzis
  implication: >
    Depois da cegueira o reconhecimento passou a PISCAR: com 4 linhas o tempo
    todo, o conjunto de nomes reconhecidos muda de um bloco de status para o
    outro. Cada piscada deixa uma identidade NOMEADA (J4guar, Kaus, Korzis) em
    `_membros`, no estado VIVO, fora de `presentes`, e com
    `linhas_quando_visto` congelado em 4.

- timestamp: fase-3
  checked: logs/scanner.log 10:17:32 - 10:18:02 (o evento reportado)
  found: |
    10:17:32  Membro 1  Membro 2  Membro 3  Korzis    (4 linhas)
    10:17:44  J4GUAR SAIU DA PARTY
    10:17:44  KAUS   SAIU DA PARTY
    10:17:44  KORZIS SAIU DA PARTY
    10:18:02  Membro 1  Membro 2  Membro 3            (3 linhas)
  implication: >
    PROVA DIRETA. A janela encolheu de 4 para 3 — exatamente UMA pessoa saiu.
    Os tres alertas carimbam o MESMO segundo, ou seja os tres contadores
    cruzaram `confirmacoes_para_saida` no mesmo frame: eles vinham subindo
    juntos desde o frame do encolhimento.

    Dos tres, so o Korzis estava reconhecido no frame anterior (10:17:32).
    J4guar e Kaus estavam fora do reconhecimento ha MINUTOS — a ausencia deles
    nao comecou as 10:17, comecou as 10:05/10:10.

- timestamp: fase-3
  checked: l2scanner/rastreador.py:800-857 (a guarda de saida)
  found: |
    linhas_agora = obs.membros_presentes                  # 3
    ...
    if linhas_agora >= interno.linhas_quando_visto:       # 3 >= 4 ? nao
        continue                                          # -> NAO bloqueia
    ...
    interno.contador_saida += 1                           # sobe para todos
    ...
    # e o zeramento so acontece do outro lado:
    for identidade, linha in presentes.items():
        interno.contador_saida = 0
        interno.linhas_quando_visto = linhas_agora         # linha 857
  implication: >
    `linhas_quando_visto` e escrito SO quando o membro esta presente. Enquanto
    o reconhecimento falha, o retrato nao envelhece junto com o mundo — ele
    fica parado em 4. A guarda entao responde a pergunta errada:

      pretendida: "a janela encolheu no momento em que ele sumiu?"
      real:       "a janela encolheu em ALGUM momento desde a ultima vez que
                   eu consegui reconhece-lo?"

    A segunda vira verdadeira, de uma vez, para TODOS os obsoletos, no instante
    da primeira saida real. Dai 1 evento real -> 3 alertas.

    O mesmo defeito de forma no `contador_saida`: ele so zera na presenca,
    entao ausencia continuada acumula sem nunca ser reavaliada.

- timestamp: fase-3
  checked: reproducao offline com Rastreador puro (sem visao, sem captura)
  found: |
    party de 4 (Korzis J4guar Kaus TioMad), aquecida 15 frames.
    depois: 10 frames com so o Korzis reconhecido (os outros como linha
    ocupada sem nome) -> 0 eventos, correto, a janela nao encolheu.
    depois: Korzis sai de verdade, janela 4 -> 3, 8 frames.

      ANTES da correcao: SAIU J4guar, SAIU Kaus, SAIU TioMad, SAIU Korzis
                         (4 alertas para 1 saida, todos no mesmo frame)
      DEPOIS da correcao: SAIU Korzis
  implication: >
    Deterministico e reproduzido sem tocar em pixel nenhum. Bohrbug.

- timestamp: fase-4
  checked: "a lei de conservacao existe em algum lugar do rastreador?"
  found: >
    Nao. Nada limita quantos SAIU podem ser confirmados no mesmo frame. O
    dominio diz que a party window perde exatamente uma linha por pessoa que
    sai, entao o numero de saidas confirmadas nunca poderia passar de quanto a
    janela encolheu — mas essa invariante nunca foi codificada.
  implication: >
    Mesmo com o retrato travado, dois membros sumindo no mesmo frame de um
    encolhimento de 1 produziriam 2 alertas. A conservacao e a segunda metade
    da correcao, e e o que transforma "1 evento real -> N alertas" em
    estruturalmente impossivel, e nao apenas improvavel.

- timestamp: fase-4
  checked: "por que o reconhecimento desabou depois das 10:03?"
  found: >
    A cegueira de 09:59:50-10:03:16 vem com "Falha de captura" e com o aviso de
    que a party window pode ter sido ARRASTADA. `_correlacionar` pontua num
    alinhamento UNICO (`matchTemplate(...)[0, 0]`, identidade.py:182), entao
    um deslocamento de poucos pixels na regiao capturada derruba a correlacao
    para perto do limiar de 0.75 e o casamento passa a piscar. Bate com o
    sintoma: nunca zero nomes, nunca quatro, sempre um subconjunto instavel.
    `conferir_geometria` so roda no arranque e so olha o arranjo de monitores —
    nao pega a janela do jogo movida no meio da sessao.
  implication: >
    Esta e a SEGUNDA condicao do AND, e e uma investigacao propria (robustez do
    reconhecimento). Nao e o que faz o scanner MENTIR — o que faz ele mentir e
    concluir saida a partir de um retrato velho. A correcao daqui tem que valer
    mesmo com o reconhecimento ruim, e vale: com o veredito travado, um membro
    fora do reconhecimento simplesmente nao e candidato a saida.

## Eliminated

- hypothesis: "o estado do rastreador e indexado por posicao de linha (slot), entao a compactacao troca os donos"
  evidence: >
    `Rastreador._membros` e `dict[str, _EstadoInterno]` chaveado por IDENTIDADE
    (rastreador.py:207), e `_chave_da_linha` so cai para `#linhaN` quando o
    reconhecimento falha. Provado ao vivo as 09:56-09:57: Kaus saiu, Korzis
    subiu de linha, o alerta nomeou o Kaus e o Korzis seguiu rastreado.
  timestamp: fase-1

- hypothesis: "o recorte do nome muda quando o membro troca de linha, e por isso o reconhecimento quebra"
  evidence: >
    `Calibracao.regiao_do_nome` e uniforme: `icone_x + nome_dx`,
    `icone_y + indice*passo + nome_dy`, mesma largura e altura para todas as
    linhas. Linha diferente produz o mesmo recorte, deslocado do passo exato.
    E o log confirma: 09:56:47 o Korzis muda de linha e continua reconhecido.
  timestamp: fase-1

- hypothesis: "o nick errado vem de `_rotular` pegando `nomes[indice]` emprestado"
  evidence: >
    `nome_de` recusa qualquer nome que esteja em `nomes_reservados`
    (rastreador.py:321), e `__main__.py:916` passa
    `nomes_reservados=cal.nomes_com_assinatura`. No log a degradacao aparece
    como "Membro 1/2/3", nunca como um nome emprestado. Os nicks errados dos
    alertas sao identidades REAIS e obsoletas, nao rotulos por posicao.
  timestamp: fase-2

- hypothesis: "sao varias saidas reais em sequencia rapida (a party se desfez)"
  evidence: >
    A contagem de linhas cai de 4 para 3 e PARA em 3 (10:18:02, 10:18:32,
    10:19:02 mostram tres linhas ocupadas). Tres pessoas saindo teriam deixado
    a janela com uma linha. Encolhimento de 1 = uma saida.
  timestamp: fase-3

## Resolution

root_cause: >
  DOIS defeitos que so produzem o sintoma JUNTOS (AND confirmado), os dois em
  l2scanner/rastreador.py.

  (1) RETRATO QUE ENVELHECE. `_EstadoInterno.linhas_quando_visto` guardava
      quantas linhas a party window tinha da ultima vez que aquele membro foi
      RECONHECIDO, e so era reescrito quando o membro aparecia em `presentes`.
      A guarda de saida comparava `linhas_agora < linhas_quando_visto` a cada
      frame. Com o reconhecimento falhando, o retrato para no tempo enquanto o
      mundo anda, e a guarda troca de pergunta:

        pretendida: "a janela encolheu quando ele sumiu?"
        real:       "a janela encolheu em ALGUM momento desde a ultima vez que
                     eu consegui reconhece-lo?"

      A segunda vira verdadeira, simultaneamente, para TODAS as identidades
      obsoletas, no instante da primeira saida real de qualquer pessoa.

  (2) NENHUMA LEI DE CONSERVACAO. Nada limitava quantos SAIU podiam ser
      confirmados no mesmo frame. O dominio diz que a party window perde
      exatamente uma linha por pessoa que sai, mas essa invariante nunca tinha
      sido escrita em codigo — entao "1 evento real -> N alertas" era permitido
      pela estrutura, nao apenas possivel por azar.

  Gatilho (terceira condicao, NAO corrigida aqui): a captura falhou entre
  09:59:50 e 10:03:16 e o reconhecimento de nomes voltou degradado e piscando.
  `_correlacionar` pontua num alinhamento unico (`matchTemplate(...)[0,0]`),
  entao poucos pixels de deslocamento na regiao capturada derrubam a
  correlacao para perto do limiar de 0.75.

fix: >
  (1) `linhas_quando_visto` foi REMOVIDO e substituido por dois campos com um
      dono so cada: `visto_no_ultimo_frame` (este membro estava na tela no
      ultimo frame processado) e `sumiu_com_encolhimento` (a janela encolheu no
      frame em que ele sumiu). O veredito e TRAVADO na primeira ausencia —
      espelho exato do `apareceu_com_crescimento` que ja existia do lado da
      entrada — porque so na primeira ausencia a contagem de linhas ainda
      descreve o mundo em que aquele membro estava.

  (2) Lei de conservacao codificada: `0 < len(sumiram_agora) <= queda`, onde
      `queda` e o encolhimento em relacao ao ultimo frame PROCESSADO. Se
      sumiram mais identidades do que a janela perdeu linhas, parte delas sumiu
      por falha de reconhecimento e nao da para dizer quais — congela todas.

  (3) Achado durante o teste de mutacao: a sua propria chave (`@Nome`) era
      elegivel a "saiu da party" pela lista de LINHAS. Bastava o recorte da sua
      barra ficar ilegivel junto com um encolhimento da janela para o SEU nome
      entrar na fila de saidas de membro. Voce nao aparece na propria party
      window; agora `_pode_ter_saido` recusa a chave `@`, e quem responde essa
      pergunta continua sendo so `_avaliar_se_voce_esta_em_party`.

  (4) `_registrar_leituras` (reaquisicao) NAO toca em `visto_no_ultimo_frame`
      nem em `_ultima_contagem_estavel`. Congelar os dois e o que preserva a
      propriedade 3 do modulo tambem para a saida: uma saida ocorrida DURANTE a
      cegueira continua sendo detectada quando a visao volta.

  Preco aceito e documentado em teste: quem ja estava fora do reconhecimento
  quando saiu passa calado. Silencio e recuperavel; nome errado nao.

verification: |
  SINAL 1 — reproducao offline (falhava antes, passa agora)
    party de 4, 12 frames com 3 membros fora do reconhecimento, depois uma
    saida real (4 -> 3 linhas):
      antes:  SAIU Korzis, SAIU J4guar, SAIU Kaus, SAIU TioMad  (4 alertas,
              todos no mesmo frame t=31.0 — a mesma assinatura de "mesmo
              segundo" do log real)
      depois: SAIU Korzis                                        (1 alerta)

  SINAL 2 — suite completa
    613 testes passando (599 antes + 14 novos). Zero regressoes.

  SINAL 3 — reversao reintroduz o bug
    `git stash` do rastreador.py: 8 dos 14 testes novos falham, incluindo o
    caso das 10:17 e a invariante de conservacao. Os 6 que passam sao os que
    guardam a deteccao REAL (protegem contra congelar demais), entao passar
    sem a correcao e o esperado.

  SINAL 4 — mutacao no ponto da correcao
    M1 remove o teto de conservacao ................. MORTO (7 falhas)
    M2 remove o travamento na primeira ausencia ..... MORTO (15 falhas)
    M3 deixa a chave `@` elegivel ................... SOBREVIVEU -> teste novo
                                                      `test_voce_nao_sai_nem_
                                                      quando_e_o_unico_
                                                      candidato` -> MORTO
    M4 reset redundante em `presentes` .............. EQUIVALENTE -> codigo
                                                      morto REMOVIDO
    M5 troca `<=` por `>=` no teto .................. MORTO (7 falhas)
    M6 escreve True sobre True na reaquisicao ....... EQUIVALENTE (no-op real)
    M7 reaquisicao sincroniza o retrato de presenca . MORTO
    M8 reaquisicao atualiza a linha de base ......... MORTO

  SINAL 5 — lint
    ruff: 24 erros no projeto, 7 nos dois arquivos tocados — IDENTICO ao
    baseline em HEAD (4a18941). Nenhum introduzido.

  DETECCAO REAL PRESERVADA, uma a uma:
    saida do MEIO da lista, party compacta ..... SAIU J4guar (nome certo)  OK
    duas saidas reais no mesmo frame ........... SAIU Kaus + TioMad        OK
    party 2->1, 3->2, 4->3 ..................... 1 alerta cada             OK
    saida durante a cegueira ................... detectada na volta        OK
    morte apos reordenacao ..................... nomeia o membro certo     OK
    entrada de verdade ......................... inalterada                OK

  oracle_type: derived — o numero esperado de alertas nao vem de um valor
  observado, vem da lei de conservacao do dominio (a janela perde uma linha por
  pessoa que sai). Vizinhos de fronteira cobertos: queda 0 / 1 / 2, candidatos
  0 / 1 / 2 / 3, party de 2 / 3 / 4 membros.

  pendente_em_farm_real: NAO CONFERIDO EM JOGO ATE O MOMENTO DO COMMIT.
    Todos os cinco sinais acima sao OFFLINE — reproducao a partir do log,
    suite, reversao, mutacao e lint. Nenhum deles viu o jogo rodando.

    O checkpoint de verificacao humana foi apresentado ao usuario e ele
    respondeu "commitar agora e ja vou testar agora tambem": aceitou fechar a
    sessao antes da confirmacao ao vivo, apoiado na cobertura offline, e foi
    para uma sessao de farm real logo em seguida. Registrado aqui como
    PENDENTE, e nao como verificado, porque nao foi verificado.

    O que ainda precisa ser conferido em jogo:
      1. party de 4-5, alguem que NAO esta na ultima linha sai;
      2. chega UM aviso so, nomeando quem realmente saiu;
      3. depois do aviso os demais continuam rastreados ([vigiando] ainda os
         lista), mesmo tendo subido de linha.

    Se qualquer um dos tres falhar, reabrir esta sessao — o commit da correcao
    e fb0862c e o estado anterior e 4a18941.

files_changed:
  - l2scanner/rastreador.py
  - tests/test_identidade.py (TestUmaSaidaRealNaoViraVariosAlertas, 15 testes)

commit: fb0862c  # fix(rastreador): uma saida real so pode anunciar uma saida, e
                 # voce nunca sai da propria party  (baseline anterior: 4a18941)

known_limitations:
  - "Quem sai estando JA fora do reconhecimento nao gera alerta (coberto por `test_saida_de_quem_ja_estava_fora_do_reconhecimento_passa_calada`)."
  - "Saida real + piscada de outro membro no MESMO frame congela os dois. Mitigado pelo debounce de 5 leituras, que filtra piscadas curtas."
  - "A degradacao do reconhecimento apos falha de captura continua em aberto — merece sessao propria (`_correlacionar` num alinhamento unico + `conferir_geometria` so no arranque)."
