@echo off
setlocal

REM ============================================================
REM  L2 Party Scanner - VIGIAR A RENDA (o EXP, a adena e o nivel)
REM
REM  Basta dar dois cliques neste arquivo.
REM
REM  O QUE ELE E: a QUARTA invocacao. Ele roda AO LADO das duas
REM  janelas de party e da janela do mercado, e nunca no lugar delas.
REM  Cada uma e um PROCESSO SEPARADO: fechar esta janela nao derruba
REM  as outras, e fechar qualquer uma delas nao derruba esta.
REM
REM  O QUE ELE NAO E:
REM    - ele NAO vigia a party. Morte, saida e volta continuam sendo
REM      trabalho do vigiar-party.bat, e este aqui nao olha para isso.
REM    - ele NAO le o mercado. O World Exchange e do vigiar-mercado.bat.
REM    - ele NAO envia alerta nenhum. Nada sai daqui para o WhatsApp
REM      nem para o Discord: ele so LE a barra inferior e a janela de
REM      status, e grava em .renda\.
REM
REM  O QUE ELE PRECISA ANTES:
REM    1. A CALIBRACAO DA RENDA, feita pelo calibrar-renda.bat: os tres
REM       retangulos (o EXP, a adena e o nivel) e os tres pisos de
REM       brilho, POR PERSONAGEM. Medido: as duas instancias poem a
REM       janela de status em lugares diferentes.
REM    2. Para a ADENA, os moldes dos digitos, cortados pelo
REM       calibrar-renda-moldes.bat. Ela e lida por GLIFO e nao por OCR.
REM
REM  Sem essas duas pecas a leitura RECUSA NOMEANDO o que falta, e
REM  recusar dizendo o motivo CONTA COMO FUNCIONAR -- nao como quebrar.
REM  Um numero errado, depois de gravado, e indistinguivel de um certo,
REM  e envenena toda taxa dali para a frente.
REM
REM  O QUE ELE PRODUZ: a pasta .renda\, com um CSV por personagem e um
REM  LEIAME.txt ao lado dele. O txt no meio dos dados e de proposito:
REM  ele explica as colunas para quem abrir o CSV daqui a seis meses.
REM
REM  QUAL CLIENTE ELE LE: o do personagem escrito na chave
REM  [jogo] personagem do config.toml (o config.local.toml vence, se
REM  voce tiver um). Sem a chave, ele mira o PERSONAGEM_PADRAO logo
REM  abaixo. Mirar importa porque esta maquina roda DUAS instancias do
REM  jogo, e o EXP e a adena sao DO PERSONAGEM: sem mira, a renda de um
REM  entraria no arquivo do outro, e o resultado nao descreve ninguem.
REM
REM  PARA LER O OUTRO CLIENTE SEM EDITAR ARQUIVO, passe o titulo exato
REM  na linha de comando -- o ultimo --janela e o que vale:
REM    vigiar-renda.bat --janela "Faerlina - XM Essence"
REM ============================================================

REM Vai para a pasta deste arquivo, seja qual for o diretorio atual
cd /d "%~dp0"

REM O personagem mirado quando o config.toml nao diz qual.
REM A CHAVE [jogo] personagem DO CONFIG VENCE ESTA LINHA: ela e so o
REM ultimo recurso, e esta aqui em UMA linha editavel em vez de escondida
REM no meio do fonte. Trocar de personagem e trocar esta palavra.
set "PERSONAGEM_PADRAO=Yazalaque"

REM Procura o Python e guarda o CAMINHO COMPLETO -- nunca o nome do comando.
REM Guardar so "py" quebra na hora de usar entre aspas, porque o cmd passa a
REM procurar um arquivo com esse nome literal em vez de resolver pelo PATH.
REM
REM Nao dependemos so do PATH: uma janela de cmd aberta ANTES da instalacao do
REM Python carrega um PATH antigo e nao acha o comando.
set "PY="
for /f "delims=" %%i in ('where py 2^>nul') do if not defined PY set "PY=%%i"
if not defined PY for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY set "PY=%%i"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

REM O alias da Microsoft Store e um stub que so abre a loja -- nao serve.
REM Substituicao de string e recurso nativo do cmd: nao depende do find.exe,
REM que pode estar sombreado por um find de outro shell no PATH.
if defined PY if not "%PY%"=="%PY:WindowsApps=%" set "PY="

if not defined PY (
    echo.
    echo  Nao encontrei o Python nesta maquina.
    echo.
    echo  Instale em https://python.org/downloads
    echo  marcando a caixa "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)

REM Ambiente proprio, montado na primeira execucao
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  Primeira execucao: preparando o ambiente. Leva um minuto...
    echo.
    "%PY%" -m venv .venv
    if errorlevel 1 goto erro_venv
    ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
    ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
    if errorlevel 1 goto erro_deps
    echo  Pronto.
    echo.
)

REM O ambiente pode ter sido montado antes de alguma dependencia nova entrar
REM na lista. Conferir e barato; descobrir isso por um traceback no meio do
REM farm nao e.
REM
REM O OCR ENTRA NESTA SONDA de proposito: sem ele o modo renda nao sobe,
REM porque o EXP e o nivel saem por OCR do Windows. Foi o buraco medido em
REM campo em 2026-08-31, com o modo rodado pelo Python global e recusando
REM por falta de OCR -- e a mensagem daquele dia ainda mandou rodar o
REM lancador de OUTRA feature para consertar esta. Aqui nao.
".venv\Scripts\python.exe" -c "import mss,cv2,numpy,windows_capture,winrt.windows.media.ocr,winrt.windows.graphics.imaging" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Faltam dependencias novas. Instalando...
    echo.
    ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
    if errorlevel 1 goto erro_deps
    echo  Pronto.
    echo.
)

REM A MIRA. O titulo exato vem do MESMO lugar que a calibracao usa: a chave
REM [jogo] personagem, lida por `ler_personagem_do_jogo` (que ja resolve a
REM precedencia do config.local.toml). O sufixo do titulo vem das constantes
REM do proprio codigo, e nao escrito de novo aqui: uma segunda copia de
REM " - XM Essence" envelheceria sozinha.
REM
REM Sem aspas dentro do -c de proposito: o `for /f` recorta o comando entre
REM aspas simples, e um apostrofo no fonte Python encerraria o comando no meio.
REM O padrao entra por argumento (sys.argv[1]), que nao precisa de aspas la.
set "JANELA="
for /f "delims=" %%t in ('.venv\Scripts\python.exe -c "import sys; from l2scanner.config import ler_personagem_do_jogo; from l2scanner.cliente import NOME_DO_CLIENTE, SEPARADOR; print((ler_personagem_do_jogo() or sys.argv[1]) + SEPARADOR + NOME_DO_CLIENTE)" "%PERSONAGEM_PADRAO%" 2^>nul') do if not defined JANELA set "JANELA=%%t"

if not defined JANELA (
    echo.
    echo  Nao consegui montar o titulo da janela a mirar.
    echo  Confira a chave [jogo] personagem do config.toml: um TOML
    echo  quebrado faz esta leitura falhar sem dizer mais nada aqui.
    echo.
    echo  Com a chave certa e a leitura ainda recusando, quem conserta
    echo  e o calibrar-renda.bat: e ele quem grava os retangulos e os
    echo  pisos deste personagem.
    echo.
    pause
    exit /b 1
)

REM OS BLOCOS DE ERRO VEM ANTES DA LINHA DE EXECUCAO, e nao depois dela.
REM Nao e estilo: e o que torna ESTRUTURAL a promessa de que nada e impresso
REM depois de o programa rodar. O defeito medido em campo no
REM calibrar-mercado.bat, em 2026-08-28, foi exatamente um bloco de
REM encerramento saindo depois de a ferramenta ter saido em codigo 1 --
REM anunciando um desfecho que o .bat nao conferiu. Aqui nao ha bloco de
REM encerramento nenhum: o resumo da sessao sai do proprio programa.
goto executar

:erro_venv
echo.
echo  Falhou ao criar o ambiente virtual.
echo  Python encontrado em: %PY%
echo.
pause
exit /b 1

:erro_deps
echo.
echo  Falhou ao instalar as dependencias.
echo  Confira sua conexao com a internet e tente de novo.
echo.
pause
exit /b 1

:executar
REM --renda exige --janela pela mesma razao que o --mercado exige: esta
REM maquina roda DUAS instancias, e o EXP e a adena sao do PERSONAGEM.
REM Sem mira o scanner leria a instancia errada e gravaria a renda de um
REM char no arquivo do outro -- um numero que nao parece errado em lugar
REM nenhum, so parece baixo. O %* no fim deixa voce acrescentar ou
REM sobrescrever qualquer flag -- inclusive um --janela com outro titulo,
REM o --intervalo (a cadencia do laco) e o --status-a-cada (a do bloco).
".venv\Scripts\python.exe" -m l2scanner --renda --janela "%JANELA%" %*

pause
