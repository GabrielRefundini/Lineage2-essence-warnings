---
status: diagnosed
trigger: "O scanner anuncia membros ENTRANDO e SAINDO da party repetidamente, com a party completamente estavel (5 pessoas fixas, ninguem entrou nem saiu de verdade)."
created: 2026-08-24T17:30:00Z
updated: 2026-08-24T18:20:00Z
---

## Current Focus

bug_class: Heisenbug (nao-deterministico; depende do cenario do jogo por tras do texto)
status: causa raiz CONFIRMADA por observacao direta. Nenhuma correcao aplicada.
next_action: decidir o desenho da correcao (ver "Correcao proposta" e a pergunta em aberto sobre a coroa do lider)

reasoning_checkpoint:
  hypothesis: >
    O ENTROU/SAIU em looping e produzido por um AND de tres condicoes
    simultaneas: (1) algo claro vaza para dentro da mascara do nome e derruba a
    pontuacao da assinatura CORRETA de ~0.97 para ~0.43; (2) a janela deslizante
    infla a pontuacao de assinaturas ERRADAS em ate +0.271; (3) nao existe
    restricao de unicidade, entao a assinatura inflada e atribuida a uma segunda
    linha. O membro real some do conjunto `presentes`, dispara SAIU depois de 5
    frames, e volta como ENTROU quando o reconhecimento se recupera.
  confirming_evidence:
    - "logs/scanner.log 17:21:09 mostra 'Korzis, Korzis, TioMad, J4guar' — a MESMA assinatura em DUAS linhas, com Kaus sumido. 8 ocorrencias no log."
    - "logs/scanner.log 17:21:04 'KAUS SAIU DA PARTY' e 17:21:42 'KAUS ENTROU NA PARTY' — o par exato previsto pelo mecanismo."
    - "Medido em 60 frames reais: inflacao da janela deslizante = +0.271 para casamentos errados e +0.000 para os corretos."
    - "Medido: nos frames de dropout a mascara salta de 92 px para 184-251 px e a pontuacao do Korzis cai de 0.976 para 0.433."
  falsification_test: >
    Se a pontuacao no alinhamento calibrado fosse igual a do maximo deslizante
    para os casamentos ERRADOS, a janela deslizante estaria inocente. Medido:
    linha 2 vs Kaus alinhado 0.237 -> deslizante 0.508. Refuta a inocencia.
  fix_rationale: >
    A correcao tem de atacar a ATRIBUICAO, nao o sintoma: resolver o frame
    inteiro de uma vez com unicidade, e parar de inflar pontuacoes erradas.
    Suprimir o evento (o caminho tomado ate agora) desliga a deteccao de saida.
  blind_spots:
    - "Nao consegui medir o caso da COROA DO LIDER: o usuario nao e lider agora. A janela deslizante existe por causa dela e a remocao precisa dessa medicao."
    - "Nao identifiquei O QUE e o objeto branco que vaza na regiao do nome (V~230, S~6). Sei que vaza e com que frequencia, nao o que e."
  candidate_causes:
    - "code: `_correlacionar` usa `.max()` sobre 25 posicoes (l2scanner/identidade.py:144)"
    - "code: `identificar` decide linha a linha, sem unicidade global (l2scanner/identidade.py:160)"
    - "code: linha-fantasma depois do vao derruba `ui_visivel` do frame inteiro (l2scanner/visao.py)"
    - "code: `alguma_linha_sem_identidade` congela SAIDA de todos (l2scanner/rastreador.py)"
    - "data/environment: algo branco e claro (V~230, S~6) vaza na mascara — `mascara_de_texto` so tem piso de brilho"
  and_gate: >
    SIM. O sintoma exige (leak) E (inflacao deslizante) E (ausencia de unicidade)
    ao mesmo tempo. Sozinho, o leak so produz "nao sei" (guardado); sozinha, a
    inflacao nao chega a 0.75 com 2 assinaturas. A linha-fantasma (`ui_visivel`)
    e um QUARTO defeito independente, com o mesmo sintoma no console mas
    mecanismo proprio.

## Symptoms

expected: party estavel de 5 membros nao gera nenhum evento ENTROU/SAIU
actual: 52 eventos em 1479 frames (~25 min) numa party fisicamente estavel
errors: nenhuma excecao. Console mostra "[reajustando]" e todos os membros com "?"
reproduction: >
  `python -m l2scanner --dry-run --janela --status-a-cada 5` com o jogo aberto.
  Offline: 60 frames reais gravados + replay pelo Rastreador.
started: >
  commit d604cdf 16:56:27 "fix: atribuir o evento a quem realmente saiu, e
  reconhecer o lider da party" — o mesmo commit introduziu a janela deslizante
  (`.max()`) E removeu o criterio de saturacao de `mascara_de_texto`.

## Eliminated

- hypothesis: "`ha_membro_nomeado` e calculado antes do laco e abre uma janela onde as guardas nao valem"
  evidence: "`ha_membro_nomeado` le `self._membros`, que so cresce. Com `nome_proprio` configurado a chave `@Yazalaque` garante True a partir do 1o frame. Nunca fica False depois do aquecimento."
  timestamp: fase-2

- hypothesis: "REAQUISICAO reentrando em ciclo e o que gera os eventos"
  evidence: "Em 360 frames replayados o portao ficou 333 rastreando / 21 reaquisicao / 6 cego, e produziu ZERO eventos. REAQUISICAO explica o console ('[reajustando]' + '?') mas nao os eventos."
  timestamp: fase-2

- hypothesis: "Membros NAO calibrados estao virando membros calibrados"
  evidence: "Medido em 60 frames: linha 2 vs Kaus max 0.519, vs Korzis max 0.519; linha 3 vs Kaus max 0.233, vs Korzis max 0.265. Nenhum chega perto de 0.75. A troca acontece entre linhas CALIBRADAS, nao com as nao calibradas."
  timestamp: fase-3

## Evidence

- timestamp: fase-1
  checked: l2scanner/visao.py:_identificar_linha + calibration.json
  found: >
    A regiao de BUSCA e alargada 24 px so a ESQUERDA
    (`esquerda = max(0, regiao.esquerda - MARGEM_DE_BUSCA)`, borda direita fixa
    em `regiao.esquerda + regiao.largura`). Recorte 124x20, molde 100x20 ->
    matchTemplate devolve 1x25 e `_correlacionar` retorna `.max()`.
  implication: 25 tentativas independentes de ultrapassar 0.75 por assinatura.

- timestamp: fase-1
  checked: l2scanner/rastreador.py:_processar
  found: "`presentes` e um dict indexado por identidade; duas linhas com a mesma assinatura colapsam numa entrada (a ultima sobrescreve). Nao ha checagem de unicidade em lugar nenhum."
  implication: o conjunto de identidades muda de tamanho com a party estavel.

- timestamp: fase-2
  checked: 60 frames capturados ao vivo (jogo aberto, party de 5 estavel)
  found: >
    linha 0: Kaus 57/60, nao reconhecido 3/60 (0.68, 0.73, 0.73)
    linha 1: Korzis 52/60, nao reconhecido 8/60 (0.43-0.54)
    linha 2 e 3: nunca reconhecidos (0/60) — sao os "Membro 3"/"Membro 4"
    3 conjuntos de identidade distintos em 60 frames com a party parada.
  implication: o reconhecimento pisca em 13% dos frames com a party imovel.

- timestamp: fase-3
  checked: inflacao da janela deslizante, 60 frames, 4 linhas x 2 assinaturas
  found: >
    CORRETOS (vencem sempre no offset 24 = alinhamento calibrado):
      linha 0 vs Kaus    alinhado 0.877 -> deslizante 0.877   INFLACAO +0.000
      linha 1 vs Korzis  alinhado 0.907 -> deslizante 0.907   INFLACAO +0.000
    ERRADOS (vencem nos offsets 12/18/21/23 — alinhamentos SORTUDOS):
      linha 0 vs Korzis  alinhado 0.399 -> deslizante 0.525   INFLACAO +0.126
      linha 2 vs Kaus    alinhado 0.237 -> deslizante 0.508   INFLACAO +0.271
      linha 2 vs Korzis  alinhado 0.336 -> deslizante 0.510   INFLACAO +0.174
  implication: >
    A janela deslizante contribui ZERO para os casamentos corretos e ate +0.271
    para os errados. Nos dados atuais ela e prejuizo puro: come metade da margem
    de seguranca ate o limiar de 0.75.

- timestamp: fase-3
  checked: direcao da janela de busca vs. a coroa do lider
  found: >
    `regiao_do_nome` comeca em x=38 (icone_x 12 + nome_dx 26). O recorte de busca
    e x em [14, 138); o offset 24 e o alinhamento calibrado e e o MAIOR possivel.
    Os offsets 0..23 colocam o molde a ESQUERDA do calibrado. A coroa do lider
    aparece ANTES do nome e empurra o texto para a DIREITA, o que exigiria
    offset > 24 — inalcancavel no recorte atual.
  implication: >
    A busca alarga para o lado errado. Nao consegue absorver a coroa (o motivo
    pelo qual foi adicionada) e so adiciona 24 chances de falso positivo.
    NAO VERIFICADO ao vivo: o usuario nao e lider agora.

- timestamp: fase-4
  checked: logs/scanner.log — 390 blocos de status da sessao 16:44-17:21
  found: >
    8 blocos com a MESMA assinatura em DUAS linhas ao mesmo tempo:
      16:51:13-16:51:38 (5 blocos seguidos)  J4guar, J4guar, Kaus, TioMad
      17:19:09                               Kaus, Korzis, Kaus, J4guar
      17:20:39                               Kaus, J4guar, TioMad, J4guar
      17:21:09                               Korzis, Korzis, TioMad, J4guar
    E a cadeia causal completa em volta do ultimo:
      17:21:04  KAUS SAIU DA PARTY
      17:21:09  status: Korzis, Korzis, TioMad, J4guar   (Kaus roubado pelo Korzis)
      17:21:42  KAUS ENTROU NA PARTY
    Resumo da sessao: 1479 frames, 52 eventos, party fisicamente estavel.
  implication: >
    OBSERVACAO DIRETA da hipotese principal. Nao e inferencia: a mesma assinatura
    foi atribuida a duas linhas, o membro real sumiu do conjunto, SAIU disparou
    apos 5 confirmacoes e ENTROU disparou na recuperacao.

- timestamp: fase-4
  checked: causa do dropout — mascara de texto da linha 1 em 60 frames
  found: >
    Nos frames bons a mascara tem ~92 px (assinatura do Korzis: 41 px).
    Nos frames de dropout ela salta para 184, 185, 193, 210, 232, 236, 237, 251.
    Correlacao acompanha: 0.976 -> 0.538, 0.510, 0.445, 0.433.
    Os 158 pixels que vazam tem V mediano 230 e S mediano 6 — sao BRANCOS e
    claros, nao terreno colorido. Um teto de saturacao NAO os remove (com S<=30
    ainda sobram 200 px dos 251).
  implication: >
    `mascara_de_texto` so tem piso de brilho (V > 180). Qualquer objeto branco e
    claro na regiao do nome entra na mascara e destroi a correlacao. Note que o
    RANKING continua certo nesses frames (Korzis 0.433 vs Kaus 0.203) — o que
    falha e o limiar absoluto de 0.75, que rejeita a resposta correta.

- timestamp: fase-5
  checked: l2scanner/visao.py `extrair` — frame 40 dos 60 capturados
  found: >
    QUARTO DEFEITO, independente e deterministico. `max_linhas=8`; as linhas 5-7
    caem sobre o chat/minimapa. No frame 40 a linha 6 passou no teste de
    contraste do icone, entao `_bordas_da_barra_intactas` rodou sobre lixo,
    falhou, e executou `ui_visivel = False` para o FRAME INTEIRO.
    `_truncar_no_primeiro_vao` descarta a linha 6 logo depois — mas a cegueira ja
    aconteceu e nunca e desfeita.
    Efeito: portao CEGO -> REAQUISICAO (3 s de tolerancia) -> `_registrar_leituras`
    nunca avanca estado -> todos os membros ficam DESCONHECIDO.
    Isso reproduz EXATAMENTE o console colado pelo usuario:
      [reajustando]
        Kaus ? / Korzis ? / Membro 3 ? / Membro 4 ? / Yazalaque (voce) ?
    Frequencia medida: 1 frame em 60 (6 cegos + 21 reaquisicao em 360 replayados).
  implication: >
    Uma linha que a propria logica ja considera inexistente consegue cegar o
    scanner inteiro. A truncagem que existe justamente para matar linhas fantasma
    roda TARDE DEMAIS.

- timestamp: fase-6
  checked: "a calibracao ATUAL detecta uma saida de verdade?"
  found: >
    Teste sintetico com a calibracao atual (2 assinaturas): aquecimento de 15
    frames com a party completa, depois Kaus SAI DE VERDADE (a linha some e as
    demais sobem). 40 frames depois:
      *** NENHUM EVENTO ***   estado do Kaus: vivo   contador_saida = 0
    O contador nem chega a incrementar uma vez.
  implication: >
    QUINTO DEFEITO, o mais grave. `alguma_linha_sem_identidade` congela a SAIDA
    de TODOS os membros sempre que QUALQUER linha ocupada nao for reconhecida.
    Com as linhas 2 e 3 sem assinatura (o estado atual do usuario) isso vale em
    100% dos frames. A deteccao de saida esta COMPLETAMENTE DESLIGADA agora.
    O "0 eventos" da sessao atual nao e o bug corrigido — e o detector desligado.

- timestamp: fase-6
  checked: linha do tempo git vs. outbox.jsonl vs. logs/scanner.log
  found: >
    d604cdf 16:56:27  janela deslizante + remocao do criterio de saturacao
    01e0da9 17:15:05  guardas `alguma_linha_sem_identidade` / `#linhaN`
    O processo que produziu os 52 eventos rodou de 16:57:05 a 17:21:45 — comecou
    ANTES das guardas e nunca as carregou (Python nao recarrega codigo em runtime).
    A sessao seguinte (17:22 e 17:25) usou o codigo com guardas e a calibracao
    nova (2 assinaturas): 20 frames, 0 eventos — curta demais para provar
    qualquer coisa, e agora sabemos que 0 eventos e o estado esperado de um
    detector desligado.
  implication: >
    As guardas suprimem o sintoma ao preco de desligar a funcionalidade. As
    causas estruturais (leak, inflacao, falta de unicidade, linha-fantasma)
    continuam todas presentes no codigo atual.

- timestamp: fase-7
  checked: tests/fixtures/identidade/party_com_lider.png vs party_ordem_original.png
  found: >
    OS DOIS ARQUIVOS SAO IDENTICOS. md5 8fc38182643b5d0754643fc99a47914f nos
    dois; 0 pixels diferentes em 90828. `party_com_lider.png` nao tem coroa nem
    nome amarelo — e uma copia do frame sem lider.
    Consequencia: `test_o_lider_e_reconhecido` (tests/test_identidade.py:399)
    afirma que o lider e reconhecido contra uma imagem SEM lider. E vacuo.
    A janela deslizante foi adicionada para resolver a coroa e NUNCA foi
    validada contra um frame com coroa de verdade.
  implication: >
    Minha pergunta em aberto esta RESPONDIDA sem precisar que o usuario vire
    lider: nao existe nenhuma evidencia, em nenhum dataset deste projeto, de que
    a janela deslizante ajude. Em 8 casos corretos medidos (2 calibracoes, 2
    conjuntos de frames) a inflacao foi +0.000 em TODOS.

- timestamp: fase-7
  checked: inflacao com as 4 assinaturas da fixture (pior caso disponivel)
  found: >
    ERRADOS, alinhado -> deslizante:
      L2 vs J4guar  0.213 -> 0.586   INFLACAO +0.373
      L2 vs Korzis  0.199 -> 0.530   INFLACAO +0.331
      L1 vs Korzis  0.140 -> 0.414   INFLACAO +0.274
      L1 vs Kaus    0.203 -> 0.418   INFLACAO +0.215
      L0 vs J4guar  0.127 -> 0.339   INFLACAO +0.212
    CORRETOS: 4/4 vencem no offset 24 (alinhado), inflacao +0.000.
  implication: >
    Com 4 assinaturas o pior casamento ERRADO chega a 0.586 — a apenas 0.164 do
    limiar de 0.75. Junte o leak (que derruba o correto para ~0.43) e a
    ultrapassagem acontece. E a confirmacao quantitativa da porta E.
    Com 8 membros na party o numero de tentativas dobra de novo.

- timestamp: fase-7
  checked: "por que os 181 testes nao pegaram isto"
  found: >
    `test_ninguem_aparece_duplicado` (tests/test_identidade.py:407) afirma
    EXATAMENTE a propriedade que quebra em producao — `len(reconhecidos) ==
    len(set(reconhecidos))`. O oraculo esta certo. A ENTRADA e que e benigna:
    um unico frame limpo, sem leak, sem coroa, onde a duplicacao nao ocorre.
  implication: >
    O gate certo existia e falhou por falta de entrada adversarial, nao por
    falta de asserção. A correcao precisa levar essa mesma asserção para os 60
    frames reais gravados (que contem os frames de leak) e para um frame com
    coroa DE VERDADE — que ainda precisa ser capturado.

- timestamp: fase-6
  checked: "python -m pytest tests/ -q"
  found: "181 passed in 11.31s — baseline verde antes de qualquer mudanca."
  implication: nenhum teste existente cobre unicidade de assinatura nem linha-fantasma.

## Resolution

root_cause: >
  QUATRO defeitos independentes, tres deles em porta E (precisam acontecer
  juntos para produzir o looping), o quarto reproduzindo o console relatado:

  (1) l2scanner/identidade.py `mascara_de_texto` — mascara so por piso de brilho
      (V > 180), sem teto nem sanidade de tamanho. Objeto branco e claro na
      regiao do nome triplica a mascara (92 -> 251 px) e derruba a correlacao
      correta de 0.976 para 0.433. Acontece em 13% dos frames com a party parada.

  (2) l2scanner/identidade.py `_correlacionar` usa `.max()` sobre 25 posicoes.
      Medido: +0.000 de ganho nos casamentos corretos (que vencem sempre no
      alinhamento calibrado) e ate +0.271 nos errados. Alem disso a busca alarga
      so para a ESQUERDA, enquanto a coroa do lider — a razao de ela existir —
      empurra o texto para a DIREITA.

  (3) l2scanner/identidade.py `identificar` decide uma linha por vez, sem nenhuma
      restricao de unicidade. Nada impede a mesma assinatura de ganhar duas
      linhas no mesmo frame. Observado 8 vezes em logs/scanner.log
      (ex. 17:21:09 "Korzis, Korzis, TioMad, J4guar" com Kaus sumido, entre
      "KAUS SAIU" 17:21:04 e "KAUS ENTROU" 17:21:42).

  (2b) tests/fixtures/identidade/party_com_lider.png e byte-identico a
      party_ordem_original.png, entao `test_o_lider_e_reconhecido` e vacuo e a
      janela deslizante nunca foi validada contra a coroa que a justificou.

  (4) l2scanner/visao.py `extrair` — uma linha-fantasma DEPOIS do primeiro vao
      (chat/minimapa) reprova em `_bordas_da_barra_intactas` e executa
      `ui_visivel = False` para o frame inteiro. `_truncar_no_primeiro_vao`
      descarta essa linha logo em seguida, tarde demais. Produz o "[reajustando]"
      + todos "?" do console relatado.

  E um defeito adicional que hoje MASCARA os quatro:
  (5) l2scanner/rastreador.py `alguma_linha_sem_identidade` congela a saida de
      TODOS sempre que QUALQUER linha ocupada nao for reconhecida. Com as linhas
      2 e 3 sem assinatura isso vale sempre: uma saida real do Kaus nao gera
      evento nenhum e `contador_saida` fica em 0.

fix: NAO APLICADO — proposta abaixo, aguardando decisao sobre a coroa do lider.
verification: n/a
files_changed: []

## Correcao proposta (nao aplicada)

Ordem por relacao valor/risco. Cada item tem um criterio de aceite mensuravel
contra os 60 frames reais gravados.

### A. Atribuicao GLOBAL com unicidade (ataca a causa 3 — a decisiva)

Trocar "cada linha escolhe sozinha" por "o frame inteiro e resolvido de uma vez":
monta a matriz linhas x assinaturas, resolve por atribuicao otima (Hungarian) ou
guloso melhor-primeiro, e cada assinatura e consumida no maximo uma vez. Uma
linha so recebe nome se o par sobreviver ao limiar E a margem sobre a melhor
alternativa AINDA DISPONIVEL.

Criterio de aceite: nenhuma assinatura em duas linhas no mesmo frame, por
construcao — verificavel com uma asserção, nao com estatistica.

### B. Pontuar no alinhamento calibrado, nao no maximo deslizante (causa 2)

Medido: remover o deslize custa 0.000 aos casamentos corretos e devolve entre
+0.126 e +0.271 de margem contra os errados.

PERGUNTA RESOLVIDA (fase-7): a janela deslizante entrou para tolerar a COROA DO
LIDER, mas alarga so para a ESQUERDA enquanto a coroa empurra o texto para a
DIREITA — e a fixture que supostamente prova que ela funciona
(`party_com_lider.png`) e byte-identica ao frame SEM lider. Ela nunca foi
validada contra uma coroa de verdade, e em 8 casos corretos medidos o ganho foi
+0.000 em todos. Remover e seguro pelas evidencias disponiveis.

PENDENCIA para a coroa (nao bloqueia esta correcao): capturar um frame com coroa
DE VERDADE e substituir a fixture duplicada. Se a coroa realmente deslocar o
texto, a resposta certa e gravar DUAS assinaturas por membro (com e sem coroa),
ou alargar a busca para a DIREITA com um teto de deslocamento — nunca voltar ao
`.max()` irrestrito.

### C. Rejeitar recorte contaminado (causa 1)

Quando a mascara tem muito mais pixels que a assinatura (medido: 92 normal vs
184-251 contaminado, contra assinaturas de 28 e 41 px), o recorte nao e texto
limpo. Marcar como "nao sei" explicitamente em vez de deixar a correlacao
degradada competir. Nota importante: teto de saturacao NAO resolve — o vazamento
e branco (S mediano 6). O sinal confiavel e o TAMANHO da mascara.

### D. Truncar antes de julgar a visibilidade (causa 4)

Mover `_truncar_no_primeiro_vao` para ANTES do teste de bordas, ou so deixar
linhas ANTERIORES ao primeiro vao influenciarem `ui_visivel`. Uma linha que a
logica ja considera inexistente nao pode cegar o scanner.

Criterio de aceite: o frame 40 dos 60 gravados deve sair com `ui_visivel=True`.

### E. Estreitar a guarda de saida (causa 5)

Com A+B+C no lugar, a guarda larga deixa de ser necessaria e passa a ser
prejuizo puro (hoje ela desliga a deteccao de saida inteira). Substituir por algo
proporcional: congelar a saida so quando o numero de linhas nao reconhecidas for
suficiente para esconder os membros que sumiram.

Criterio de aceite: o teste sintetico "Kaus sai de verdade" precisa gerar SAIU
mesmo com as linhas 2 e 3 sem assinatura.

### Testes de regressao a adicionar

- unicidade: duas linhas nunca recebem a mesma assinatura (propriedade)
- linha nao calibrada nunca recebe nome (fixture das linhas 2/3, 60 frames)
- party estavel: 60 frames reais x N voltas -> zero eventos
- saida real: linha some -> SAIU dispara, mesmo com linhas nao calibradas
- frame 40 (linha-fantasma na 6) -> `ui_visivel` continua True
- oracle_type: derived (contrato de atribuicao) + specified (eventos esperados)
