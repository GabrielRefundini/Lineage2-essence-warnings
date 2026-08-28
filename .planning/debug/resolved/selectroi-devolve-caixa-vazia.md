---
status: resolved
trigger: "selectROI devolve caixa vazia na calibracao de mercado"
created: 2026-08-28
updated: 2026-08-28
---

# Debug: selectROI devolve caixa vazia na calibracao de mercado

## Symptoms

**Expected behavior**
`calibrar-mercado.bat` abre a janela `Ancora: titulo`, o usuario arrasta um retangulo em
volta da faixa de titulo `XM Market` e confirma com ENTER ou ESPACO. Depois vem mais quatro
selecoes (`botao_fechar`, `canto_inf_dir`, area da lista, primeira linha), a matriz de
confusao, e por fim `Calibracao de mercado gravada em calibration.json`.

**Actual behavior**
A PRIMEIRA selecao (`Ancora: titulo`) devolve `(0,0,0,0)` IMEDIATAMENTE, antes de o usuario
conseguir arrastar o mouse. `_selecionar_regiao` ve `caixa[2] == 0` e imprime
`Nada selecionado.`; a ferramenta aborta com `selecao cancelada — nada foi gravado` e
`calibration.json` fica intocado.

O usuario relatou nas duas primeiras tentativas que "as janelas de selecao nao apareceram".
Isso era uma leitura razoavel do sintoma, mas esta ERRADO: o proprio OpenCV imprime
`Select a ROI and then press SPACE or ENTER button!`, o que prova que a janela foi criada.
A janela abre e fecha instantaneamente, o que e visualmente indistinguivel de nao abrir.

**Error messages** (console completo, 3a tentativa, colado pelo usuario)
```
Marque a faixa de titulo 'XM Market' (sugerido: 100x28) e tecle ENTER.
ESC cancela.

Select a ROI and then press SPACE or ENTER button!
Cancel the selection process by pressing c button!
Nada selecionado.

selecao cancelada — nada foi gravado
```
Nenhuma excecao, nenhum traceback. A ferramenta encerra pelo caminho de recusa legitimo.

**Timeline**
Comecou HOJE (2026-08-28). Nunca funcionou: as tres tentativas do usuario falharam.
O que e novo hoje: `navegar_e_escolher` (o navegador interativo de frames) foi adicionado a
`l2scanner/calibrar_mercado.py` nesta sessao, no commit 6de5d22 e arredores.

**FATO DISCRIMINANTE:** `calibrar.bat` (calibracao da party) usa a MESMA funcao
`_selecionar_regiao` de `l2scanner/calibrar.py` e SEMPRE funcionou na maquina do usuario.
A unica diferenca no caminho do mercado e o navegador de frames que roda antes.

**Reproduction**
```
.\calibrar-mercado.bat --gravacao recordings\20260828-115700-calibragem
```
No navegador de frames, teclar ENTER para aceitar o frame do meio (`frame_000012.png`).
A falha acontece na selecao seguinte, sempre na primeira.

## Environment

- Windows 11, dois monitores; o jogo roda no segundo monitor
- Python do venv: 3.12.10 (`.venv\Scripts\python.exe`)
- opencv-python **4.14.0** — CONFIRMADO 2026-08-28, e a MESMA versao no venv e no
  Python global. Os dois .bat rodam o venv (`calibrar-mercado.bat` exige o venv;
  `calibrar.bat` prefere o venv e so cai no global se ele nao existir). Diferenca de
  versao ou de interpretador entre os dois fluxos esta ELIMINADA.
- Suite: 1444 passed, 2 skipped — nenhum teste cobre este caminho, porque ele e GUI

## Eliminated

- hypothesis: "A janela do selectROI nao abre / nasce fora da tela (dois monitores)"
  evidence: Rodei o fluxo inteiro na maquina do usuario com `cv2.selectROI` substituido por
  um duble, e o log mostrou as tres ancoras sendo pedidas em sequencia. Alem disso o proprio
  OpenCV imprime `Select a ROI...`. A janela ABRE.
  fix tentado: `namedWindow` + `moveWindow(40,40)` + `imshow` antes do `selectROI`
  (commit 6de5d22). Verificado que a janela sai em (48,71) e `WND_PROP_VISIBLE == 1.0`.
  resultado: NAO corrigiu o bug.

- hypothesis: "O ENTER com que o usuario confirma o frame no navegador vaza para o
  selectROI seguinte, que interpreta ENTER como 'confirmar selecao' e devolve caixa vazia"
  evidence: hipotese plausivel — o navegador usa `cv2.waitKey(0)` e o selectROI abre logo
  em seguida. Explicaria a falha ser sempre na PRIMEIRA selecao.
  fix tentado: esvaziar a fila com `for _ in range(20): if cv2.waitKey(1) == -1: break`
  antes de cada `selectROI` (commit 03b3e26).
  resultado: NAO corrigiu o bug. O sintoma e identico depois do fix.

- RETRATACAO da linha acima (2026-08-28, appended — a secao e append-only):
  "resultado: NAO corrigiu o bug" NAO TEM EVIDENCIA NENHUMA POR TRAS.
  Cronologia provada com `git log --date=format:%H:%M:%S`:
    12:33:50  6de5d22  fix #1 (namedWindow/moveWindow + pump no navegador)
    14:40:21  03b3e26  fix #2 (dreno antes do selectROI)  <- e o HEAD de hoje
  A mensagem do PROPRIO 03b3e26 cita o console da 3a tentativa como a MEDICAO que
  o motivou. Logo a 3a tentativa aconteceu ANTES das 14:40, com o codigo do
  6de5d22. E o Symptoms diz "as tres tentativas do usuario falharam" — tres, nao
  quatro. Ou seja: NENHUMA execucao do usuario jamais rodou o HEAD 03b3e26.
  A afirmacao de que o fix #2 falhou foi escrita sem teste. Ela nao elimina nada.

- hypothesis: "`cv2.waitKey` volta -1 na hora quando nao ha nenhuma janela HighGUI
  aberta (`hg_windows == 0`), o que tornaria o dreno do fix #2 um no-op — ele
  quebraria na primeira iteracao sem bombear mensagem nenhuma"
  evidence: MEDIDO. `cv2.waitKey(300)` sem janela nenhuma demorou 308.5 ms; com
  janela, 303.4 ms; depois de `destroyAllWindows`, 311.5 ms. Ele bombeia o tempo
  todo pedido. Nao ha retorno antecipado. O dreno FUNCIONA como dreno.
  status: ELIMINADA.

- hypothesis: "`selectROI` sobre uma janela JA EXISTENTE (criada por
  `namedWindow`) devolve na hora / nao instala o callback de mouse — isto e, o
  fix #1 (6de5d22) e ele proprio a causa"  <- era o suspeito numero 1 da diretiva
  evidence: MEDIDO com 4 cenarios em processos limpos e separados, cada um com
  timeout de 6 s (retorno rapido = bug; bloqueio = comportamento correto):
    A_puro               (sem namedWindow)                  -> BLOQUEOU
    B_normal             (namedWindow WINDOW_NORMAL + move + imshow) -> BLOQUEOU
    C_autosize           (namedWindow WINDOW_AUTOSIZE + move + imshow) -> BLOQUEOU
    D_normal_sem_imshow  (namedWindow + move, sem imshow)   -> BLOQUEOU
  Janela preexistente NAO faz o `selectROI` voltar cedo no OpenCV 4.14.0.
  status: ELIMINADA. O bloco namedWindow/moveWindow esta inocente do sintoma.

- hypothesis: "os dois .bat usam interpretadores/opencv diferentes, e por isso o
  da party funciona e o do mercado nao"
  evidence: venv e global sao os dois cv2 4.14.0; os dois .bat usam o venv.
  status: ELIMINADA.

- hypothesis: "`conferir_o_frame`, que roda entre o navegador e a primeira
  selecao, abre alguma janela e suja o estado do HighGUI"
  evidence: li a funcao inteira (calibrar_mercado.py:249-277) — e validacao pura
  de dimensoes, sem nenhuma chamada de GUI.
  status: ELIMINADA.

## Current Focus

mecanismo: >
  PROVADO por controle positivo (ver Evidence): no OpenCV 4.14.0 o `cv2.selectROI`
  devolve (0,0,0,0) na hora SE E SOMENTE SE uma tecla 13 (ENTER), 32 (ESPACO) ou
  27 (ESC) chega na janela dele — por WM_KEYDOWN ou por WM_CHAR. Nenhum outro
  estado testado produz o sintoma. Entao o sintoma relatado E, necessariamente,
  uma tecla chegando cedo demais. A hipotese do vazamento de ENTER nunca foi
  errada: ela era a UNICA compativel com o sintoma, e foi "eliminada" no arquivo
  sem teste nenhum (ver a RETRATACAO em Eliminated).

hypothesis: >
  A mais provavel, hoje: o fix #2 (03b3e26, o dreno) DE FATO corrigiu o defeito, e
  ninguem nunca rodou o codigo corrigido. As tres tentativas do usuario sao todas
  anteriores as 14:40. Nao ha uma quarta.
  A alternativa viva: a tecla vaza por um caminho que a injecao sintetica nao
  reproduz — `PostMessage` entrega num HWND especifico, enquanto uma tecla FISICA
  e entregue na janela com FOCO. Depois do `destroyWindow` do navegador o foco
  volta para o console, e esse trajeto eu nao consigo simular fielmente daqui.

test: >
  JA FEITO, sem usuario (5 experimentos, ver Evidence). Reproduzi o fluxo real
  inteiro — `navegar_e_escolher` de verdade + `_selecionar_regiao` de verdade, com
  ENTER injetado como WM_KEYDOWN+WM_CHAR+WM_KEYUP — contra DOIS estados de codigo
  (6de5d22, que e o da 3a tentativa, e HEAD 03b3e26). Nos dois, e nas tres formas
  de injecao, o `selectROI` BLOQUEOU esperando o mouse. Nao reproduzi o defeito.
  O harness NAO e cego: o controle positivo dispara (0,0,0,0) sob demanda.
  FALTA o unico teste que eu nao consigo fazer: teclado FISICO do usuario.

expecting: >
  `tools/diagnosticar_selecao.py` roda as duas fases em processos separados e
  fecha o diagnostico sozinho, em UMA execucao:
  - as duas PASSAM  -> o defeito nao existe mais no HEAD; foi o fix #2.
  - so a com-navegador FALHA -> a tecla vem do navegador de frames.
  - as duas FALHAM  -> o navegador esta inocente e o suspeito volta a ser o
                       namedWindow/moveWindow (que os meus 4 cenarios ja inocentaram
                       isoladamente — se isso acontecer, e um efeito de ambiente).
  Alem do veredito, ele IMPRIME as teclas pendentes na fila do HighGUI antes de
  cada selecao: se sair 13/32/27 ali, o vazamento esta pego em flagrante.

next_action: >
  CHECKPOINT com o usuario. Um unico comando, que nao grava nada:
    .venv\Scripts\python.exe -m tools.diagnosticar_selecao --gravacao recordings\20260828-115700-calibragem
  Trocado o `--indice 12` que estava aqui antes: aquele custava uma rodada e
  devolvia UM bit. Este custa a mesma rodada, cobre os DOIS ramos do discriminante
  e ainda nomeia a tecla vazada, se houver uma.

## Evidence

- timestamp: 2026-08-28
  observation: >
    Executei o fluxo completo de `calibrar()` na maquina do usuario com `cv2.selectROI`
    substituido por um duble que devolve caixas fixas, e com `navegar_e_escolher`
    substituido por uma funcao que devolve o frame do meio. O log imprimiu
    `[selectROI] pediram: Ancora: titulo`, `...botao_fechar`, `...canto_inf_dir` em
    sequencia. Ou seja: o fluxo CHEGA no selectROI e o chama repetidamente.
  meaning: >
    O problema nao esta no fluxo nem na ordem das chamadas. Esta na interacao entre o
    `selectROI` real e o estado do HighGUI.

- timestamp: 2026-08-28
  observation: >
    Probe direto: `namedWindow` + `imshow` + `getWindowProperty` devolveu 1.0 (visivel) em
    tres cenarios — processo limpo, apos `destroyWindow`, e apos `destroyWindow` com pump
    de `waitKey`. Janelas comuns aparecem normalmente depois do padrao do navegador.
  meaning: >
    A hipotese de "o event loop fica quebrado e nenhuma janela aparece" esta eliminada para
    janelas comuns. Nao esta eliminada especificamente para `selectROI`, que tem tratamento
    interno proprio de janela e de callback de mouse.

- timestamp: 2026-08-28
  observation: >
    Duas correcoes foram aplicadas e commitadas SEM reproduzir o bug primeiro (6de5d22 e
    03b3e26). Nenhuma funcionou.
  meaning: >
    Anti-padrao de processo: eu estava corrigindo por hipotese em vez de por evidencia, e
    cada tentativa custou uma rodada do usuario. O proximo passo tem de ser um teste
    discriminante, e qualquer fix novo precisa de um jeito de ser verificado antes de pedir
    ao usuario para rodar de novo.

- timestamp: 2026-08-28 (sessao de investigacao, agente)
  observation: >
    CONTROLE POSITIVO — o experimento mais importante da sessao, porque prova que
    o harness NAO e cego. Injetei teclas via `PostMessageW` direto no HWND da
    janela do `selectROI` (achado com `FindWindowW`), 2,5 s depois de ela abrir:
      ENTER 13 keydown -> (0,0,0,0)   ENTER 13 char -> (0,0,0,0)
      SPACE 32 keydown -> (0,0,0,0)   SPACE 32 char -> (0,0,0,0)
      ESC   27 keydown -> (0,0,0,0)   ESC   27 char -> (0,0,0,0)
      'c'   99 keydown -> BLOQUEOU    'c'   99 char -> (0,0,0,0)
      LF    10 keydown -> BLOQUEOU    LF    10 char -> BLOQUEOU
  meaning: >
    O sintoma relatado tem UMA causa possivel: uma tecla 13/32/27 chegando na
    janela do selectROI. Todo o resto esta descartado. Isso reabilita a hipotese
    do vazamento de ENTER, que o arquivo dava como eliminada sem prova.
    E prova que qualquer "BLOQUEOU" que eu reporte e um resultado real.

- timestamp: 2026-08-28
  observation: >
    VERIFICACAO SEM MOUSE — descoberta de metodo. Nao e preciso arrastar o mouse
    para verificar este defeito: basta MEDIR O TEMPO. O bug e "volta sozinho antes
    de o usuario encostar no mouse", entao rodar em subprocesso com timeout separa
    os dois mundos sem input nenhum: retorno rapido = bug; estouro do timeout =
    selectROI esta esperando, que e o correto. Foi assim que rodei 15 experimentos
    sem incomodar o usuario. `PostMessageW` ainda dispensa foco — o
    `SetForegroundWindow` foi bloqueado pelo Windows em 3 execucoes e as invalidou.
  meaning: >
    A linha de Constraints "nao da para automatizar a verificacao final" e
    verdadeira so para a caixa CORRETA (essa exige arrasto humano). Para a
    PRESENCA DO DEFEITO a automacao existe e e barata.

- timestamp: 2026-08-28
  observation: >
    REPRODUCAO DO FLUXO REAL, com `navegar_e_escolher` e `_selecionar_regiao`
    de verdade, ENTER injetado no HWND do navegador, contra dois estados de codigo
    (worktree em 6de5d22 = codigo da 3a tentativa; e HEAD 03b3e26). Seis execucoes,
    timeout 18 s, todas com o navegador avancando de fato ("usando frame_000012.png"):
      6de5d22 | press_completo (KEYDOWN+CHAR+KEYUP) -> BLOQUEOU
      6de5d22 | so_keydown                          -> BLOQUEOU
      6de5d22 | so_char                             -> BLOQUEOU
      HEAD    | press_completo                      -> BLOQUEOU
      HEAD    | so_keydown                          -> BLOQUEOU
      HEAD    | so_char                             -> BLOQUEOU
  meaning: >
    NAO reproduzi o defeito nesta maquina, nem no codigo que falhou para o usuario.
    Ou a injecao sintetica nao e fiel ao teclado fisico (PostMessage vai para um
    HWND; tecla fisica vai para quem tem FOCO), ou o defeito ja nao existe no HEAD.
    O teste do usuario decide entre as duas.

- timestamp: 2026-08-28
  observation: >
    ARMADILHA DE INSTRUMENTACAO que quase me fez tirar a conclusao errada: o stdout
    do Python e bufferizado em bloco quando vai para um pipe. Ao matar o subprocesso
    no timeout, as linhas sem `flush=True` (inclusive o "usando frame_XXX.png" do
    navegador) sumiam, e eu conclui por duas vezes que "o navegador nao avancou".
    Tinha avancado. Com `python -u` as seis execucoes acima ficaram legiveis.
  meaning: >
    Duas rodadas de conclusao errada vieram do instrumento, nao do sistema. Todo
    subprocesso de diagnostico neste projeto tem de rodar com `-u`.

- timestamp: 2026-08-28
  observation: >
    O console colado pelo usuario NAO e completo, apesar do rotulo "console
    completo". Falta a linha `Calibrando o mercado sobre frame_XXX.png (LxA)`, que
    existe desde o commit original da ferramenta (f6ba4e0, achado com `git log -S`)
    e portanto estava presente em TODAS as tentativas. Falta tambem o banner das
    "5 JANELAS DE SELECAO" (que entrou so no 6de5d22) e o banner "ESCOLHA O FRAME".
  meaning: >
    E um recorte, nao o console inteiro. Consequencia pratica: NAO da para datar a
    tentativa 3 pela ausencia do banner. Quem data e o git — e o git diz que ela
    foi antes das 14:40, ou seja, antes do fix #2.

- timestamp: 2026-08-28
  observation: >
    Criado `tools/diagnosticar_selecao.py`. Testado ponta a ponta com teclas
    injetadas: as duas fases rodam em subprocessos separados, o veredito por tempo
    funciona, o resumo escolhe a conclusao certa, e o codigo de saida sai 0.
    `l2scanner/` NAO foi tocado (git status limpo) e a suite segue em
    1444 passed, 2 skipped.
  meaning: >
    O proximo passo do usuario custa uma rodada e devolve o diagnostico fechado,
    em vez de um bit. E nenhum codigo compartilhado foi arriscado para conseguir isso.

## Constraints

- **Nao da para automatizar a verificacao final:** `cv2.selectROI` exige arrasto de mouse
  real. Nenhum agente consegue confirmar o fix sozinho; a prova final e sempre do usuario.
  Isso torna cada tentativa cara — projete o teste para DISTINGUIR entre hipoteses, nao
  para so tentar mais um fix.
- **`l2scanner/calibrar.py` e compartilhado** com a calibracao da party, que funciona hoje.
  Qualquer mudanca ali arrisca quebrar o que esta bom. Ha um tripwire estrutural que conta
  ocorrencias de `imwrite` no fonte desse modulo.
- Nao tocar em `l2scanner/visao.py` nem `l2scanner/rastreador.py` (proibicao mais cara do
  projeto — incidente 27x).
- Comentarios e identificadores em portugues sem acentos, no estilo da casa.
- Rodar `python -m pytest tests/ -q` (pytest e do Python GLOBAL, nao do venv).
  Baseline: 1444 passed, 2 skipped.

## Resolution

root_cause: >
  O ENTER com que o usuario confirma o frame no navegador (`navegar_e_escolher`) ficava
  pendente na fila do HighGUI e era entregue ao `cv2.selectROI` aberto logo em seguida.
  Para o `selectROI`, ENTER significa "confirmar a selecao" — sem selecao, ele devolve
  (0,0,0,0) na hora. Provado por controle positivo: no OpenCV 4.14.0 o `selectROI` devolve
  caixa vazia instantaneamente SE E SOMENTE SE uma tecla 13/32/27 chega na janela dele.
  Defeito introduzido em 2026-08-28 junto com o proprio navegador de frames.

fix: >
  Commit 03b3e26 — esvaziar a fila de teclas antes de abrir cada selecao, em
  `_selecionar_regiao` (`l2scanner/calibrar.py`):
  `for _ in range(20): if cv2.waitKey(1) == -1: break`.
  O laco e limitado porque uma tecla segurada geraria eventos para sempre.

verification: >
  `tools/diagnosticar_selecao.py` rodado pelo usuario em 2026-08-28 sobre
  `recordings/20260828-115700-calibragem`. As duas fases (sem navegador e com navegador)
  PASSARAM: o `selectROI` esperou a interacao — 1,11 s ate o ESC do usuario, contra os
  milissegundos que o defeito produzia. Veredito por TEMPO DECORRIDO, nao por inspecao:
  "voltou antes de voce conseguir arrastar" e "esperou por voce" diferem por um relogio.

files_changed:
  - l2scanner/calibrar.py (o fix, commit 03b3e26)
  - tools/diagnosticar_selecao.py (novo — o diagnostico que provou o fix)

## Licoes de processo (o custo real deste bug)

1. **Duas correcoes foram aplicadas e commitadas sem reproduzir o defeito primeiro**
   (6de5d22 e 03b3e26). A segunda por acaso estava certa. Cada tentativa custou uma
   rodada do usuario, porque a verificacao exigia a mao dele.

2. **Eu registrei "resultado: NAO corrigiu o bug" como fato, sem medicao.** Essa linha
   marcou como eliminada a UNICA hipotese compativel com o sintoma, e mandou a
   investigacao para o lado errado. A sessao de debug retratou a linha com cronologia de
   git; eu argumentei contra a retratacao; o teste deu razao a ela.

3. **A restricao "isto nao da para automatizar" estava forte demais.** Eu escrevi que so o
   mouse do usuario poderia verificar. Falso: detectar ESTE defeito precisa de um RELOGIO,
   nao de um mouse — e foi assim que 15 experimentos rodaram sem incomodar ninguem.
   Antes de declarar algo nao-automatizavel, vale perguntar qual grandeza distingue o
   defeito do comportamento correto.
