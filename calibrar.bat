@echo off
setlocal

REM ============================================================
REM  Calibracao — descobre onde fica a party window na sua tela
REM
REM  Rode com o JOGO ABERTO e a PARTY WINDOW VISIVEL.
REM
REM  Rode de novo sempre que:
REM    - mover a janela do jogo ou a party window
REM    - mudar a resolucao ou o arranjo de monitores
REM    - mudar quem esta na party
REM ============================================================

cd /d "%~dp0"

REM Caminho completo sempre — guardar so o nome do comando quebra entre aspas
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if not defined PY for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY set "PY=%%i"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
REM Substituicao de string e recurso nativo do cmd: nao depende do find.exe,
REM que pode estar sombreado por um find de outro shell no PATH.
if defined PY if not "%PY%"=="%PY:WindowsApps=%" set "PY="

if not defined PY (
    echo.
    echo  Nao encontrei o Python. Rode vigiar-party.bat uma vez primeiro,
    echo  que ele prepara o ambiente.
    echo.
    pause
    exit /b 1
)

REM Mesma conferencia do vigiar-party.bat: o ambiente pode estar defasado.
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import mss,cv2,numpy,windows_capture" >nul 2>&1
    if errorlevel 1 (
        echo  Instalando dependencias novas...
        ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
    )
)

echo.
set /p NOMES="Nomes da party em ordem, separados por virgula (ENTER para pular): "

echo.
if "%NOMES%"=="" (
    "%PY%" -m l2scanner.calibrar --auto
) else (
    "%PY%" -m l2scanner.calibrar --auto --nomes "%NOMES%"
)

echo.
echo  ------------------------------------------------------------
echo   ABRA a imagem calibracao-conferencia.png e confira se os
echo   retangulos coloridos batem com a sua party window.
echo.
echo   Se nao baterem, rode este arquivo de novo — se insistir em
echo   errar, use:  .venv\Scripts\python -m l2scanner.calibrar --selecionar
echo  ------------------------------------------------------------
echo.
pause
