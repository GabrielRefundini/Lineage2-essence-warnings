@echo off
setlocal

REM ============================================================
REM  Calibrar SO a sua barra de vida — para quem joga sozinho
REM
REM  Basta dar dois cliques neste arquivo.
REM
REM  Rode com o JOGO ABERTO e a sua barra de HP VISIVEL.
REM  NAO precisa estar em party.
REM
REM  Use quando:
REM    - voce arrastou a barra de HP para outro lugar da tela
REM    - o scanner diz que voce morreu e voce esta vivo
REM
REM  Ele mantem a party window da calibracao anterior. Quando
REM  voltar a jogar em grupo, rode o calibrar.bat normal.
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

".venv\Scripts\python.exe" -m l2scanner.calibrar --solo %*

echo.
echo  ------------------------------------------------------------
echo   ABRA a imagem calibracao-conferencia.png e confira se o
echo   retangulo verde esta na SUA barra de vida.
echo.
echo   Se estiver na barra de um MONSTRO, tire o alvo (clique no
echo   chao) e rode este arquivo de novo.
echo  ------------------------------------------------------------
echo.
pause
