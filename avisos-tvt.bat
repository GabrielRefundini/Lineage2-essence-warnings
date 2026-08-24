@echo off
setlocal

REM ============================================================
REM  Avisos de TvT e Prime — so o relogio, sem vigiar a party
REM
REM  Basta dar dois cliques neste arquivo.
REM
REM  O JOGO NAO PRECISA ESTAR ABERTO. Este modo nao olha para a
REM  tela: ele so avisa no WhatsApp 10 minutos antes de cada
REM  evento e de novo na hora que comeca.
REM
REM  Os horarios ficam em config.toml — edite la quando o jogo
REM  mudar os horarios. Nunca e preciso mexer em codigo.
REM
REM  Para vigiar a party (mortes, saidas), use vigiar-party.bat.
REM ============================================================

cd /d "%~dp0"

REM O ambiente e o mesmo do vigiar-party.bat. Se ele ainda nao existe,
REM mandamos rodar aquele primeiro em vez de montar um segundo por conta —
REM dois ambientes divergindo e um problema pior do que um passo a mais.
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  O ambiente ainda nao foi preparado.
    echo  Rode vigiar-party.bat uma vez primeiro — ele monta tudo.
    echo.
    pause
    exit /b 1
)

if not exist "config.toml" (
    echo.
    echo  Nao encontrei o config.toml, que e onde ficam os horarios.
    echo  Ele deveria estar nesta mesma pasta.
    echo.
    pause
    exit /b 1
)

echo.
echo  Avisos de TvT e Prime. O jogo NAO precisa estar aberto.
echo  Deixe esta janela aberta. Feche com Ctrl+C ou no X.
echo.

".venv\Scripts\python.exe" -m l2scanner --so-agenda %*

echo.
pause
