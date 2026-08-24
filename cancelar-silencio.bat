@echo off
setlocal

REM ============================================================
REM  Cancelar o silencio de TvT / Prime
REM
REM  Basta dar dois cliques neste arquivo.
REM
REM  O Prime cala o scanner por DUAS HORAS. Quando voce nao vai
REM  fazer Prime — ou ele acabou antes — rode isto e os alertas
REM  de morte e saida voltam na hora.
REM
REM  Cancela SO a ocorrencia de hoje. Amanha o silencio volta ao
REM  normal sozinho, sem voce precisar lembrar de nada.
REM
REM  Funciona com o jogo fechado, e vale para as DUAS instancias
REM  do scanner ao mesmo tempo.
REM ============================================================

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  O ambiente ainda nao foi preparado.
    echo  Rode vigiar-party.bat uma vez primeiro — ele monta tudo.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m l2scanner --cancelar-silencio %*

echo.
pause
