@echo off
setlocal

REM ============================================================
REM  Calibrar o WORLD EXCHANGE (o "XM Market")
REM
REM  Basta dar dois cliques neste arquivo.
REM
REM  Ele NAO le a tela ao vivo: ele trabalha sobre uma GRAVACAO
REM  de janela completa que voce ja fez. Assim voce pode errar,
REM  refazer e conferir a vontade, sem o painel fechar no meio.
REM
REM  Rode assim, apontando a pasta da sua gravacao:
REM
REM    calibrar-mercado.bat --gravacao recordings\<pasta>
REM
REM  Voce vai marcar com o mouse, um retangulo de cada vez:
REM    1. as tres ancoras do painel (titulo, X de fechar, seta)
REM    2. a area da lista e a primeira linha dela
REM    3. o nome de cada item da watchlist do config.toml
REM
REM  Ele mantem TODO o resto da calibracao anterior intacto.
REM  Rode o calibrar.bat normal UMA vez antes, se nunca rodou.
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

".venv\Scripts\python.exe" -m l2scanner.calibrar_mercado %*

echo.
echo  ------------------------------------------------------------
echo   ABRA a imagem calibracao-conferencia.png e confira se os
echo   retangulos verdes caem onde voce espera: a faixa de titulo
echo   do painel, o X de fechar, a seta de rolagem, a area da
echo   lista e a primeira linha.
echo.
echo   Se a matriz de confusao RECUSOU, ela nomeou o par de itens
echo   que se confundem: recorte os dois mais largos, ou tire um
echo   deles da watchlist do config.toml.
echo  ------------------------------------------------------------
echo.
pause
