---
status: awaiting_human_verify
trigger: "abro o inventario POR CIMA da party window e o scanner manda falso alerta de morte no WhatsApp — mas o log mostra HP ok 100% o tempo todo, quem oscila e o NOME"
created: 2026-08-26T00:00:00Z
updated: 2026-08-26T00:00:00Z
---

## Current Focus

bug_class: Bohrbug — deterministico, reproduzido offline a partir do log real
status: CAUSA RAIZ CONFIRMADA por reproducao offline em tres variantes, todas
  batendo com assinaturas reais de `logs/scanner.log`
next_action: >
  AGUARDANDO O USUARIO. Correcao JA aplicada e commitada em f2013c3 (suite
  758 passando + 2 skipped, mutacao 7/7 morta). NAO reescrever os testes nem
  refazer a correcao num resume. O que falta e resposta humana a tres
  perguntas, nesta ordem:
  (1) verificacao em campo — reiniciar o bot e confirmar que o inventario por
      cima nao gera alerta e que a morte real de membro reconhecido ainda avisa;
  (2) veto ou aceite do preco — a morte de membro SEM assinatura passa a ser
      silenciosa, o que obrigou a reverter a assercao de
      `test_morte_em_linha_desconhecida_nao_usa_nome_de_outro`
      (era mortes == ["Membro 2"], virou mortes == []);
  (3) o furo em aberto — barra ilegivel em linha RECONHECIDA ainda pode virar
      "KORZIS MORREU"; so uma gravacao real (tools/record.py com o inventario
      aberto) permite fechar isso sem inventar fixture.

reasoning_checkpoint:
  hypothesis: >
    A hipotese anterior ("o rotulo oscilando, sozinho, vira morte") esta
    REFUTADA — medido: party estavel, HP 100% constante, rotulo da linha 0
    oscilando Korzis <-> Membro 1 por 96 frames produz ZERO eventos.

    A causa real e que a chave POSICIONAL `#linhaN` — criada quando o
    reconhecimento falha — e um membro de primeira classe da maquina de estado
    para MORTE e RESSURREICAO, enquanto SAIU e ENTROU ja foram fechados contra
    ela em duas sessoes anteriores. Restaram exatamente os dois eventos que
    ninguem fechou.

    E `#linhaN` nao e uma pessoa: e o scanner dizendo "nao sei quem esta aqui".
    Como e uma POSICAO, ela nao tem continuidade — o estado dela sobrevive a
    lacunas arbitrarias (frames em que a linha FOI reconhecida, ou em que a
    linha nem existia) e o `desde` continua correndo. Dai "ficou 1h56 morto".
  confirming_evidence:
    - "logs/scanner.log:13803 — 'MEMBRO 3 FOI RESSUSCITADO (ficou 1h56 morto)'; 13666 — 51min20s; 13705 — 53min31s. Duracao impossivel para uma morte real."
    - "logs/scanner.log:12341-12345 — [vigiando] as 14:06:44 mostra uma party de DOIS (Membro 1, Membro 2) e as 14:06:59 anuncia 'MEMBRO 3 MORREU' — morte numa linha que nao existia no frame anterior."
    - "logs/scanner.log:14711-15036 — 17:05-17:10: 22 eventos alternando MEMBRO 1 e MEMBRO 4, quase todos 'ficou 5s morto' — exatamente `confirmacoes_para_ressurreicao=5` a 1 Hz, assinatura de contador batendo no limiar, nao de ressurreicao real."
    - "reproducao offline (3 cenarios) devolve as MESMAS assinaturas: RESSUSCITOU 'Membro 1' com 228s; metralhadora MORREU/RESSUSCITOU a cada 5-6s; MORREU 'Membro 3' com party de dois."
    - "rastreador.py:864-868 `_pode_ter_saido` recusa `#linhaN`; rastreador.py:979 `e_chave_de_posicao` recusa `#linhaN` na entrada. O bloco de morte/ressurreicao (rastreador.py:1010-1048) nao tem guarda nenhuma."
  falsification_test: >
    Se a causa fosse a oscilacao do rotulo por si so, party estavel com HP
    100% constante e rotulo oscilando produziria eventos. Medido: ZERO eventos
    em 96 frames. Refuta a hipotese anterior e isola a causa no estado ZUMBI da
    chave posicional, nao na oscilacao.
  fix_rationale: >
    Aplicar a morte e a ressurreicao a MESMA regra que o projeto ja aplicou
    duas vezes a entrada e a saida: uma identidade posicional nao anuncia
    evento. Mais a metade que faltava nas duas vezes anteriores — uma
    identidade posicional nao SOBREVIVE a uma lacuna, porque posicao nao e
    identidade e o proximo ocupante da linha 2 nao tem relacao com o anterior.
    A guarda e condicionada a `assinaturas_configuradas`, que e a propria
    fronteira que o projeto ja usa em `_rotular` entre "a posicao e a
    identidade" (modo legado) e "a imagem e a identidade" (modo atual).
  blind_spots:
    - "NAO explico, no nivel de PIXEL, por que a barra de uma linha ocupada le 0% com o inventario aberto. `medir_barra` devolve 0.0 para recorte ilegivel e as linhas da party NAO tem o equivalente de `barra_propria_legivel` — mas sem gravacao em `recordings/` nao da para medir se `_bordas_da_barra_intactas` deveria ter pego. Registrado no checkpoint, nao corrigido as cegas."
    - "A morte real de um membro SEM assinatura gravada passa a ser silenciosa. E o preco explicito, e bate com a definicao do proprio constraint ('a morte real acontece com a party window visivel e o NOME LEGIVEL')."
  candidate_causes:
    - "code: morte/ressurreicao sem a guarda de identidade posicional que entrada/saida ja tem (CONFIRMADO)"
    - "code: o estado de `#linhaN` sobrevive a lacunas e o `desde` continua correndo (CONFIRMADO — produz 1h56)"
    - "data: a party tem membros SEM assinatura gravada, entao chaves `#linhaN` existem o tempo todo (CONFIRMADO — warning de linha ocupada ha 120 leituras em scanner.log:22427)"
    - "environment: inventario por cima / janela arrastada derruba nome E barra ao mesmo tempo (GATILHO, nao corrigido aqui — sem gravacao para medir)"
  and_gate: >
    SIM. Exige (1) a ausencia da guarda no caminho de morte/ressurreicao E
    (2) a existencia de chaves `#linhaN`, que so nascem quando o
    reconhecimento falha. Com a party inteira reconhecida nao existe chave
    posicional e nenhum falso positivo aparece — foi por isso que a validacao
    em campo de 2026-08-24 (12 mortes reais, nomes corretos) passou limpa.

## Symptoms

expected: >
  abrir o inventario por cima da party window nao gera evento nenhum; a
  cobertura da UI e um problema de VISAO, e visao ruim congela estado.

actual: >
  [08:25] Membro 1: HP de volta apos 3min42s.
  [08:26] Membro 1: HP zerado — possivel morte na PT.
  [08:26] Membro 1: HP de volta apos 19s.

  Alertas chegaram no WhatsApp nomeando "Membro 1" — um rotulo posicional
  que nao diz nada para quem le no celular e nao permite agir.

## Evidence

- timestamp: 08:25-08:27 (logs/scanner.log ~23498-23545)
  fact: >
    O HP NUNCA foi lido como zero. Toda linha de [vigiando] diz `ok 100%`.
    O que oscila entre as leituras e o NOME da linha:

      08:25:20  [vigiando]  Korzis ok 100% | Kaus ok 100% | J4guar ok 100% | TioMad ok 100%
      08:25:44  MEMBRO 1 FOI RESSUSCITADO (ficou 3min42s morto)
      08:25:51  [vigiando]  Membro 1 ok 100% | Membro 2 ok 100% | J4guar ok 100% | TioMad ok 100%
      08:26:22  [vigiando]  Membro 1 ok 100% | Kaus ok 100% | J4guar ok 100% | TioMad ok 100%
      08:26:32  MEMBRO 1 MORREU
      08:26:51  MEMBRO 1 FOI RESSUSCITADO (ficou 19s morto)
      08:26:53  [vigiando]  Korzis ok 91% | Membro 2 ok 100% | J4guar ok 100% | TioMad ok 100%
      08:27:23  [vigiando]  Korzis ok 100% | Membro 2 ok 100% | Membro 3 ok 100% | TioMad ok 100%
  implication: >
    REFUTA a hipotese obvia ("o inventario cobre a barra e ela le 0%"). A
    barra esta legivel e cheia. Os eventos sao emitidos para o PSEUDO-MEMBRO
    POSICIONAL, que so existe porque o reconhecimento de identidade falhou.

- timestamp: sessao inteira
  fact: 'grep -c "sem reconhecer\|SEM NOME\|nao reconhec" logs/scanner.log = 35 ocorrencias'
  implication: falha de identidade e frequente, nao um caso isolado

- timestamp: 08:27:44
  fact: WARNING "Imagem congelada — jogo travado ou captura presa"
  implication: a captura ficou presa DEPOIS dos falsos alertas

- timestamp: 08:28:13
  fact: WARNING "Sem visao da party ha 30 leituras seguidas"
  implication: >
    o portao de cegueira DISPARA, mas tarde demais e no nivel errado (party
    window inteira). Ele nao impediu nenhum dos falsos alertas.

- timestamp: contexto de projeto
  fact: >
    `sessao.py` ja conta `ticks_sem_reconhecer` por linha; o comentario
    registra que em 2026-08-25 uma falha de identidade durou DUAS HORAS e so
    foi descoberta por alertas errados. Hoje isso so gera AVISO depois de
    120 ticks.
  implication: >
    o projeto ja SABE que identidade falha, mas nao fechou o caminho entre
    "nao sei quem e" e "mandei alerta de morte". O sinal existe e e ignorado
    pelo caminho de eventos.

- timestamp: contexto de projeto
  fact: >
    A margem medida do reconhecimento por imagem e 0.546 (mesmo nome 1.000,
    outros no maximo 0.454) — ver `identidade.py` e o LEARNINGS da fase.
  implication: um inventario por cima do nome derruba essa margem

- timestamp: fase-1 (2026-08-26)
  checked: reproducao offline com o Rastreador puro, tres cenarios
  found: |
    A. `#linha0` nasce MORTO em silencio (4 frames com nome ilegivel E HP 0),
       fica 222 frames fora de `presentes` com o estado congelado, e ao voltar
       com HP 100% anuncia RESSUSCITOU 'Membro 1' (228.0s).
       -> bate com scanner.log:23506 "MEMBRO 1 FOI RESSUSCITADO (3min42s)"
    B. com `#linha0` ja VIVO, alternar HP 0/100 na linha nao reconhecida
       produz MORREU/RESSUSCITOU a cada 5-6 s, indefinidamente.
       -> bate com scanner.log:14711-15036 (22 eventos em 5 min, "ficou 5s morto")
    C. party de DOIS; `#linha2` fica VIVO de uma aparicao antiga, congela 60
       frames fora da tela, e quando a linha 2 reaparece com a barra ainda
       desenhando (HP 0) anuncia MORREU 'Membro 3'.
       -> bate com scanner.log:12341-12345 ("MEMBRO 3 MORREU" com party de dois)
  implication: >
    As tres assinaturas do log real sao reproduzidas sem tocar em pixel nenhum.
    Bohrbug. A causa esta inteira no rastreador.

- timestamp: fase-2 (2026-08-26)
  checked: as guardas de identidade posicional que JA existem
  found: |
    rastreador.py:864  `_pode_ter_saido`  -> recusa `#linhaN`   (SAIU fechado)
    rastreador.py:979  `e_chave_de_posicao` -> recusa `#linhaN` (ENTROU fechado)
    rastreador.py:1010-1048  morte e ressurreicao -> NENHUMA guarda
  implication: >
    Dois dos quatro eventos de membro foram fechados contra a chave posicional,
    em duas sessoes diferentes desta mesma familia. Os outros dois nunca foram.
    O furo nao e uma omissao aleatoria — e o mesmo raciocinio aplicado pela
    metade, duas vezes.

- timestamp: pre-investigacao
  fact: NAO ha gravacoes em `recordings/`
  implication: >
    a reproducao vai depender de fixture sintetica no nivel do rastreador,
    ou de o usuario gravar uma nova sessao. Se um dado so puder vir de
    gravacao real, dizer no checkpoint em vez de inventar fixture.

## Eliminated

- hypothesis: >
    o rotulo oscilando, sozinho, vira morte — "MESMA party, HP 100% constante,
    apenas o rotulo de uma linha oscilando Korzis -> Membro 1 -> Korzis"
  why: >
    MEDIDO e REFUTADO. Party de 4 estavel, HP 1.0 em todas as linhas, o rotulo
    da linha 0 alternando reconhecido/nao a cada 8 frames, 96 frames no total:
    ZERO eventos. O pseudo-membro `#linha0` nasce, vira VIVO em silencio e fica
    la. A oscilacao do rotulo e necessaria (ela cria a chave) mas nao e
    suficiente — falta o estado ZUMBI dessa chave atravessando lacunas.

- hypothesis: o inventario cobre a BARRA e ela e lida como 0%
  why: >
    refutado pelo log — toda leitura de [vigiando] durante a janela dos
    falsos alertas reporta `ok 100%`. A barra nunca leu zero.

## Filosofia do projeto que a correcao deve respeitar

Registrada no STATE.md, ja paga com bugs anteriores:

1. "cegueira congela contadores em vez de zerar"
2. "o portao de cegueira fala da PARTY WINDOW, nao de voce"
3. "toda maquina de estado que anuncia transicoes precisa distinguir 'mudou'
   de 'foi assim que eu encontrei'"

## Direcao de solucao a avaliar (nao decidida)

- Uma linha OCUPADA mas NAO RECONHECIDA deveria ser tratada como cegueira
  DAQUELA LINHA: congelar o estado dela em vez de transicionar. E a
  aplicacao literal da filosofia (1) por linha em vez de por party window.
- E/ou: eventos NUNCA deveriam ser emitidos para rotulo posicional, so para
  membros identificados do roster.
- Avaliar se o rotulo posicional "Membro N" deveria sequer chegar ao WhatsApp.

## Custo do remedio (restricao dura)

NAO pode virar um scanner que deixa de avisar morte de verdade. A morte real
acontece com a party window visivel e o nome legivel; o remedio precisa
preservar esse caminho, e isso precisa ser PROVADO com teste.

## Resolution

root_cause: >
  A chave POSICIONAL `#linhaN` — criada em `_chave_da_linha` quando o
  reconhecimento falha — e um membro de primeira classe da maquina de estado
  para MORTE e RESSURREICAO, enquanto ENTROU e SAIU ja tinham sido fechados
  contra ela em duas sessoes anteriores desta mesma familia
  (`_pode_ter_saido`, `e_chave_de_posicao`). Restaram exatamente os dois
  eventos que ninguem fechou.

  Duas consequencias, as duas confirmadas por reproducao offline:

  (1) O EVENTO NAO TEM SUJEITO. `#linha0` nao e uma pessoa; e o scanner
      dizendo "nao sei quem esta aqui". "MEMBRO 1 MORREU" no WhatsApp nao diz
      a ninguem quem socorrer.

  (2) O ESTADO E ZUMBI. Posicao nao tem continuidade: o estado de `#linhaN`
      atravessava lacunas inteiras — frames em que a linha VOLTOU a ser
      reconhecida (a chave vira o nome e some do conjunto), ou em que a linha
      nem existia — com o `desde` correndo do outro lado. Dai as duracoes
      impossiveis do log real: "ficou 1h56 morto" (16:03:28), "51min20s",
      "53min31s", e uma morte anunciada numa linha que nao estava na tela no
      frame anterior (14:06:59, "MEMBRO 3 MORREU" com a party de DOIS).

  A hipotese de entrada ("o rotulo oscilando, sozinho, vira morte") foi
  MEDIDA e REFUTADA: party parada, HP 100% constante e o rotulo alternando por
  96 frames produz ZERO eventos. A oscilacao CRIA a chave, mas quem produz o
  evento e o estado zumbi dela.

fix: >
  Duas metades, as duas em `l2scanner/rastreador.py`, as duas condicionadas a
  `assinaturas_configuradas` — a mesma fronteira que `_rotular` ja usa entre
  "a posicao e a identidade" (modo legado) e "a imagem e a identidade".

  (1) `_e_so_uma_posicao` + guarda nos dois pontos de emissao: uma identidade
      posicional NAO anuncia morte nem ressurreicao. O estado interno continua
      avancando, entao o console segue honesto sobre o que a barra esta lendo;
      o que nao sai e o alerta.

  (2) UMA POSICAO NAO SOBREVIVE A UMA LACUNA: no fim de `_processar`, toda
      chave `#linhaN` ausente do frame e descartada de `_membros`. E o que
      torna a duracao inventada impossivel de calcular, em vez de apenas
      impossivel de anunciar.

  Preco explicito e aceito: a morte de um membro SEM assinatura gravada passa
  a ser silenciosa. Bate com a definicao do proprio constraint ("a morte real
  acontece com a party window visivel e o NOME LEGIVEL"), e o caminho de
  recuperacao ja existe no produto — o aviso de `ticks_sem_reconhecer`
  ("a linha N esta ocupada ha 120 leituras e eu nao reconheci quem esta nela...
  rode calibrar.bat de novo"), em `__main__.py:1341`.

verification: |
  SINAL 1 — reproducao offline (falhava antes, passa agora)
    4 testes reproduzem as tres assinaturas do log real e falhavam pelo bug:
      RESSUSCITOU 'Membro 1' (228.0s)      ~ log 08:25:44 "3min42s"
      metralhadora a cada 5-6 s            ~ log 17:05-17:10 (22 eventos)
      MORREU 'Membro 3' com party de dois  ~ log 14:06:59
      propriedade: nenhum alerta nomeia `Membro N`

  SINAL 2 — suite completa
    758 passando + 2 skipped (baseline 746 + 2). Zero regressoes.

  SINAL 3 — reversao reintroduz o bug
    `git stash` de rastreador.py: 5 falham (os 4 acima + o teste atualizado);
    8 passam — e sao justamente os que guardam a DETECCAO REAL, entao passar
    sem a correcao e o esperado.

  SINAL 4 — mutacao no ponto da correcao, 7/7 MORTOS
    M1 remove a guarda de evento da MORTE ............ MORTO
    M2 remove a guarda de evento da RESSURREICAO ..... MORTO
    M3 a posicao volta a sobreviver a lacuna ......... SOBREVIVEU -> teste novo
       `test_o_console_nao_mostra_morto_numa_linha_lendo_hp_cheio` -> MORTO
       (sem a parte 2, o painel mostrava a linha como `morto` lendo HP 100% —
        medido; a guarda de evento sozinha escondia o sintoma)
    M4 o predicado ignora `assinaturas_configuradas` . MORTO
    M5 o predicado sempre diz False .................. MORTO
    M6 o predicado sempre diz True ................... MORTO
    M7 a lacuna descarta toda identidade ausente ..... MORTO

  SINAL 5 — lint
    ruff nos dois arquivos tocados: 7 erros agora, 7 erros em HEAD. Identico
    ao baseline; nenhum introduzido.

  DETECCAO REAL PRESERVADA, uma a uma (passam ANTES e DEPOIS da correcao):
    morte real de membro reconhecido ........... MORREU Korzis          OK
    ressurreicao real de membro reconhecido .... RESSUSCITOU Korzis     OK
    morte real COM o nome piscando no meio ..... MORREU Korzis          OK
    sua propria morte (`@Yazalaque`) ........... MORREU Yazalaque       OK
    saida real de membro ....................... SAIU Kaus              OK
    modo legado (sem assinaturas) .............. MORREU Korzis          OK

  oracle_type: derived — o esperado nao vem de um valor observado, vem do
  contrato do dominio (um alerta precisa ter sujeito; uma posicao nao e um
  sujeito). Vizinhos de fronteira cobertos: lacuna de 0 / 4 / 60 / 222 frames,
  party de 2 / 3 / 4 linhas, HP 0.0 / 1.0, com e sem assinaturas, com e sem
  `nome_proprio`.

  pendente_em_farm_real: NAO CONFERIDO EM JOGO. Todos os cinco sinais sao
    OFFLINE. O que precisa ser conferido: abrir o inventario por cima da party
    window e confirmar que nenhum alerta de morte sai; e uma morte real de
    membro RECONHECIDO continuar avisando com o nome certo.

files_changed:
  - l2scanner/rastreador.py
  - tests/test_identidade.py

## Em aberto — precisa de dado que so uma gravacao real fornece

Por que a barra de uma linha OCUPADA le 0% com o inventario por cima?

`medir_barra` devolve 0.0 para qualquer recorte ilegivel, e as linhas da party
NAO tem o equivalente de `barra_propria_legivel` — a guarda que a sessao
[[alarme-falso-no-arranque]] instalou para a barra do PROPRIO personagem
exatamente por esse motivo ("`hp_proprio is not None` nao significa que a barra
esta visivel"). A guarda que deveria pegar isso nas linhas e
`_bordas_da_barra_intactas`, que derruba `ui_visivel` do frame inteiro — mas
sem frames gravados nao da para medir se ela deveria ter disparado.

Consequencia pratica: com a correcao desta sessao, uma barra ilegivel numa
linha RECONHECIDA ainda pode virar "KORZIS MORREU". Nao foi tocado aqui porque
`recordings/` esta vazio e inventar fixture de pixel seria inventar o caso.

Para investigar: rodar `tools/record.py` durante uma sessao com o inventario
aberto por cima da party window, e replayar contra `visao.extrair`.
