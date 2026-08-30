@echo off
setlocal

REM ============================================================
REM  Calibrar as regioes do CHAT e do ALVO
REM
REM  Com o jogo aberto, marque duas regioes da janela:
REM    1. as linhas do chat onde sai o anuncio de nascimento;
REM    2. somente o NOME do alvo selecionado.
REM
REM  Pode marcar apenas uma. O scanner avisa quando o chat
REM  anunciar o nascimento de um boss da sua lista, ou quando
REM  o seu alvo virar um deles.
REM
REM  A MESMA calibracao vale para qualquer boss da lista do
REM  config.toml. Acrescentar um mob la nao pede recalibracao.
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
