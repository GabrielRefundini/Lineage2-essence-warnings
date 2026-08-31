@echo off
setlocal

REM ============================================================
REM  L2 Party Scanner - VIGIAR O MERCADO (o World Exchange)
REM
REM  Basta dar dois cliques neste arquivo.
REM
REM  O QUE ELE E: a TERCEIRA invocacao. Ele roda AO LADO das duas
REM  janelas de party que voce ja abre, e nunca no lugar delas.
REM
REM  O QUE ELE NAO E:
REM    - ele NAO vigia a party. Morte, saida e volta continuam sendo
REM      trabalho do vigiar-party.bat, e este aqui nao olha para isso.
REM    - ele NAO envia alerta nenhum. Nada sai daqui para o WhatsApp
REM      nem para o Discord: ele so LE o painel e grava em .mercado\.
REM
REM  O QUE ELE PRECISA:
REM    1. A CALIBRACAO DO MERCADO, feita antes pelo calibrar-mercado.bat
REM       sobre uma gravacao do painel. Sem ela o modo NAO SOBE, e a
REM       mensagem na tela diz exatamente qual peca falta e como gravar.
REM    2. O PAINEL DO WORLD EXCHANGE ABERTO na tela. Ele so coleta
REM       enquanto o painel estiver aberto; com o painel fechado ele
REM       fica de pe sem gravar nada, que e o estado normal do farm.
REM
REM  QUAL CLIENTE ELE LE: o do personagem escrito na chave
REM  [jogo] personagem do config.toml (o config.local.toml vence, se
REM  voce tiver um). Sem a chave, ele mira o PERSONAGEM_PADRAO logo
REM  abaixo. Mirar importa porque esta maquina roda DUAS instancias do
REM  jogo, e sem mira nao ha como escolher entre elas.
REM
REM  PARA LER O OUTRO CLIENTE SEM EDITAR ARQUIVO, passe o titulo exato
REM  na linha de comando -- o ultimo --janela e o que vale:
REM    vigiar-mercado.bat --janela "Faerlina - XM Essence"
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
REM O OCR ENTRA NESTA SONDA de proposito: sem ele o modo mercado nao sobe,
REM porque sem nome lido nao ha serie de preco. Foi o buraco medido em campo,
REM com o modo rodado pelo Python global e recusando por falta de OCR.
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
REM --mercado exige --janela: o painel do World Exchange ANDA dentro da
REM janela, entao ele e procurado na janela inteira, e so o caminho da
REM janela a expoe como unidade. O %* no fim deixa voce acrescentar ou
REM sobrescrever qualquer flag -- inclusive um --janela com outro titulo.
".venv\Scripts\python.exe" -m l2scanner --mercado --janela "%JANELA%" %*

pause
