@echo off
setlocal

REM ============================================================
REM  L2 Party Scanner — vigia a party e avisa no WhatsApp
REM
REM  Basta dar dois cliques neste arquivo.
REM
REM  Antes do primeiro uso:
REM    1. Copie ENV-EXEMPLO.txt para .env e preencha o Chatwoot
REM       (sem isso ele funciona, mas so mostra no console)
REM    2. Rode calibrar.bat com o jogo aberto
REM ============================================================

REM Vai para a pasta deste arquivo, seja qual for o diretorio atual
cd /d "%~dp0"

REM Procura o Python e guarda o CAMINHO COMPLETO — nunca o nome do comando.
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

REM O alias da Microsoft Store e um stub que so abre a loja — nao serve.
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

REM --janela le a janela do jogo direto, entao cobrir o jogo com o
REM navegador nao cega mais o scanner. Tire a flag para voltar a ler o
REM desktop (mais simples, mas exige o jogo visivel).
".venv\Scripts\python.exe" -m l2scanner --janela %*
goto fim

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

:fim
echo.
pause
