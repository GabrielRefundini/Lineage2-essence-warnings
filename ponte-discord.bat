@echo off
setlocal

REM ============================================================
REM  Ponte do Discord - repete anuncio de guild no WhatsApp
REM
REM  Basta dar dois cliques neste arquivo.
REM
REM  O JOGO NAO PRECISA ESTAR ABERTO. Esta janela nao olha para a
REM  tela: ela le dois canais do servidor do Discord e, por
REM  enquanto, SO MOSTRA no console o que chegou. Nada e enviado
REM  para o WhatsApp ainda.
REM
REM  Antes do primeiro uso, faca os 4 passos do PORTAO-DISCORD.txt:
REM  criar o bot, ligar a intent MESSAGE CONTENT, convidar o bot
REM  nos dois canais e escolher a conversa de destino.
REM
REM  ESTA JANELA NUNCA INSTALA NADA, e isso e de proposito.
REM  Quem monta o ambiente e o vigiar-party.bat, e so ele. O
REM  motivo esta medido: os pinos do arquivo de requisitos sao
REM  abertos, entao rodar o instalador daqui com o scanner
REM  farmando escreveria por cima de cv2.pyd e das DLLs do numpy
REM  com elas CARREGADAS - falha de arquivo travado, ou pior, um
REM  upgrade silencioso da pilha numerica no meio do farm. Os dois
REM  programas dividem o mesmo ambiente; esta janela confere e
REM  recusa, nunca conserta por conta propria.
REM ============================================================

cd /d "%~dp0"

REM O ambiente e o mesmo do vigiar-party.bat. Se ele ainda nao existe,
REM mandamos rodar aquele primeiro em vez de montar um segundo por conta -
REM dois ambientes divergindo e um problema pior do que um passo a mais.
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  O ambiente ainda nao foi preparado.
    echo  Rode vigiar-party.bat uma vez primeiro - ele monta tudo.
    echo.
    pause
    exit /b 1
)

if not exist "config.toml" (
    echo.
    echo  Nao encontrei o config.toml, que e onde fica a secao [discord]
    echo  com o servidor e os dois canais.
    echo  Ele deveria estar nesta mesma pasta.
    echo.
    pause
    exit /b 1
)

REM Sonda de dependencia com UM alvo so. Se faltar, esta janela RECUSA e
REM manda montar o ambiente no lugar certo. Ver o cabecalho para o porque.
".venv\Scripts\python.exe" -c "import discord" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Falta a biblioteca da ponte no ambiente.
    echo  Rode vigiar-party.bat uma vez primeiro - ele monta tudo.
    echo  Esta janela nao instala nada, de proposito.
    echo.
    pause
    exit /b 1
)

echo.
echo  Ponte do Discord. O jogo NAO precisa estar aberto.
echo  Deixe esta janela aberta. Feche com Ctrl+C ou no X.
echo.

".venv\Scripts\python.exe" -m l2scanner.ponte_discord %*

REM A despedida existe por um motivo. Ha relato recorrente de um RuntimeError
REM cosmetico do transporte do Proactor aparecer no Ctrl+C no Windows DEPOIS
REM de o processo ja ter saido limpo. Esta linha e o que diz a quem nao
REM programa que a saida foi normal. Nao tente suprimir a excecao - ela e do
REM interpretador, nao nossa.
echo.
echo  Ponte encerrada.
echo.
pause
