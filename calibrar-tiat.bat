@echo off
setlocal

REM ============================================================
REM  Calibrar aviso de TIAT
REM
REM  Com o jogo aberto, marque duas regioes da janela:
REM    1. as linhas do chat onde sai o anuncio;
REM    2. somente o NOME do alvo selecionado.
REM
REM  Pode marcar apenas uma. O scanner avisa se Tiat aparecer
REM  no chat OU se o seu alvo virar Tiat.
REM ============================================================

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  O ambiente ainda nao foi preparado.
    echo  Rode vigiar-party.bat uma vez primeiro.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m l2scanner.calibrar --tiat %*

echo.
pause
