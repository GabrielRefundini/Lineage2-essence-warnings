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

REM O bloco de conferencia SO sai quando a ferramenta terminou bem.
REM Sem esta guarda, uma chamada sem argumento (ou uma recusa da matriz
REM de confusao) imprimia mesmo assim "ABRA a imagem de conferencia" —
REM mandando o usuario conferir um arquivo que nunca foi gerado. E a
REM mesma mentira que o FUND-01 tirou do gravador: dizer que deu certo
REM sem ter conferido que deu.
if errorlevel 1 (
    echo.
    echo  ------------------------------------------------------------
    echo   A CALIBRACAO NAO FOI CONCLUIDA. Nada foi gravado.
    echo   A mensagem acima diz o motivo.
    echo.
    echo   Se faltou dizer de onde ler, e assim:
    echo     calibrar-mercado.bat --gravacao recordings\^<pasta^>
    echo  ------------------------------------------------------------
    echo.
    pause
    exit /b 1
)

echo.
echo  ------------------------------------------------------------
REM O NOME DA IMAGEM NAO PODE SER CITADO AQUI: o .bat nao sabe qual foi.
REM `_gravar_conferencia` grava em calibracao-conferencia.png, ou num nome
REM alternativo com horario quando aquele esta travado no visualizador de
REM fotos, ou em lugar nenhum. Citar o nome de sempre mandava o usuario
REM conferir A IMAGEM DA CALIBRACAO ANTERIOR -- validar a rodada nova
REM olhando a antiga. Quem sabe o nome e a ferramenta, e ela ja o diz.
echo   A MENSAGEM ACIMA diz qual imagem de conferencia abrir, ou
echo   diz que nao deu para gravar nenhuma. Abra a que ela citou
echo   e confira se os retangulos verdes caem onde voce espera: a
echo   faixa de titulo do painel, o X de fechar, a seta de rolagem,
echo   a area da lista e a primeira linha.
echo.
echo   Se a matriz de confusao RECUSOU, ela nomeou o par de itens
echo   que se confundem: recorte os dois mais largos, ou tire um
echo   deles da watchlist do config.toml.
echo  ------------------------------------------------------------
echo.
pause
