@echo off
setlocal

REM ============================================================
REM  L2 Party Scanner - vigia a party e avisa no WhatsApp
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

REM Procura o Python e guarda o CAMINHO COMPLETO - nunca o nome do comando.
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

REM O alias da Microsoft Store e um stub que so abre a loja - nao serve.
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
REM
REM QUAL CHAR VIGIAR, quando ha mais de uma janela do XM Essence aberta.
REM
REM Ate 04/09/2026 este arquivo sempre chamava --janela sem valor. Se a
REM calibracao tinha "janela" gravada, o scanner usava aquele titulo SEMPRE
REM -- mesmo com outro char aberto nesta sessao, pegando o char errado sem
REM avisar nada. Sem "janela" gravada e com duas ou mais janelas abertas, o
REM scanner recusava e saia, sem oferecer escolha nenhuma no clique duplo.
REM
REM Esta v1 e ESCOLHA UNICA: pergunta qual das janelas abertas vigiar --
REM nunca vigiar as duas ao mesmo tempo, isso fica para depois. So pergunta
REM no clique duplo (sem argumento nenhum) e so quando ha duas ou mais
REM janelas. Zero ou uma janela continuam sem pergunta, do jeito que ja
REM funciona hoje -- mesmo principio ja corrigido no calibrar.bat: quem
REM passa argumento na linha de comando NAO e perguntado de novo.
set "JANELA_ESCOLHIDA="
if "%~1"=="" call :escolher_janela

if defined JANELA_ESCOLHIDA (
    ".venv\Scripts\python.exe" -m l2scanner --janela "%JANELA_ESCOLHIDA%" %*
) else (
    ".venv\Scripts\python.exe" -m l2scanner --janela %*
)
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
exit /b 0

REM ============================================================
REM  :escolher_janela -- descobre quantas janelas do XM Essence estao
REM  abertas e, se houver duas ou mais, pergunta qual vigiar.
REM
REM  Nao listamos as janelas com "python -c" inline: o titulo delas e os
REM  proprios comandos python usam aspas simples E duplas ao mesmo tempo, e
REM  isso quebra dentro do for /f ('comando') do cmd, que usa aspas simples
REM  para delimitar o proprio comando. Por isso a flag propria
REM  --listar-janelas, que so imprime titulo puro, uma linha por janela.
REM
REM  Devolve o titulo escolhido em JANELA_ESCOLHIDA (variavel do escopo do
REM  chamador -- .bat nao tem escopo de funcao de verdade, entao o valor
REM  atravessa o "endlocal & set" no fim de cada saida desta sub-rotina).
REM ============================================================
:escolher_janela
setlocal EnableDelayedExpansion
set "N=0"
for /f "delims=" %%j in ('".venv\Scripts\python.exe" -m l2scanner --listar-janelas') do (
    set /a N+=1
    set "JANELA_!N!=%%j"
)

if "!N!"=="0" (
    REM nenhuma janela aberta -- segue como hoje, o proprio scanner explica
    REM que nao achou janela nenhuma
    endlocal
    goto :eof
)
if "!N!"=="1" (
    REM uma so -- nao ha ambiguidade nenhuma, sem pergunta
    set "ESCOLHIDA=!JANELA_1!"
    endlocal & set "JANELA_ESCOLHIDA=%ESCOLHIDA%"
    goto :eof
)

echo.
echo  Voce tem !N! janelas do XM Essence abertas. Qual delas quer vigiar?
echo  (esta versao vigia UMA de cada vez, nao as duas juntas)
echo.
for /l %%i in (1,1,!N!) do echo   %%i^) !JANELA_%%i!
echo.

:pedir_numero
set /p ESCOLHA="Digite o numero e aperte ENTER: "
if "!ESCOLHA!"=="" goto pedir_numero
set "VALIDA="
for /l %%i in (1,1,!N!) do if "!ESCOLHA!"=="%%i" set "VALIDA=1"
if not defined VALIDA (
    echo  Numero invalido. Digite um numero entre 1 e !N!.
    goto pedir_numero
)
set "ESCOLHIDA=!JANELA_%ESCOLHA%!"
endlocal & set "JANELA_ESCOLHIDA=%ESCOLHIDA%"
goto :eof
