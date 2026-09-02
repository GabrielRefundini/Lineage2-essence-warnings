@echo off
setlocal

REM ============================================================
REM  L2 Party Scanner - DASHBOARD DO CAMBIO (a janela do mercado)
REM
REM  Basta dar dois cliques neste arquivo.
REM
REM  O QUE ELE E: a JANELA do que o mercado ja coletou, aberta no
REM  navegador, ao lado do jogo. Ele le a pasta .mercado\ e desenha
REM  o numero e a serie. So isso.
REM
REM  O QUE ELE NAO E:
REM    - ele NAO coleta nada. Quem le o painel do World Exchange e
REM      o vigiar-mercado.bat, e ele continua sendo o unico.
REM    - ele NAO mira janela, NAO le pixel do jogo e NAO faz OCR.
REM    - ele NAO envia alerta nenhum, nem para o WhatsApp nem para
REM      o Discord.
REM    - FECHAR ESTA JANELA PRETA NAO INTERROMPE A COLETA DA NOITE.
REM      Sao dois programas separados, em dois processos separados:
REM      derrubar este aqui nao encosta no outro, e derrubar o outro
REM      deixa esta pagina viva mostrando o ultimo dado, com a
REM      recencia na cara dizendo de quando ele e.
REM
REM  O QUE ELE PRECISA: que o vigiar-mercado.bat ja tenha rodado ao
REM  menos uma vez, para existir arquivo a ler. Se nao houver, a
REM  propria pagina explica isso com todas as letras, em vez de
REM  mostrar um zero que ninguem observou.
REM
REM  PARA MUDAR A PORTA, se a sua estiver ocupada, passe na linha
REM  de comando:
REM    dashboard.bat --porta 8788
REM ============================================================

REM Vai para a pasta deste arquivo, seja qual for o diretorio atual
cd /d "%~dp0"

REM Procura o Python e guarda o CAMINHO COMPLETO -- nunca o nome do comando.
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

REM O alias da Microsoft Store e um stub que so abre a loja -- nao serve.
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

REM O ambiente e o MESMO do vigiar-mercado.bat, e este bloco so age quando ele
REM AINDA NAO EXISTE. Se o executavel nao esta no disco, nenhum processo pode
REM estar rodando a partir dele, e montar aqui e seguro.
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

REM A SONDA DE DEPENDENCIAS DESTE PROCESSO, E ELA FOI MEDIDA -- nao copiada do
REM vigiar-mercado.bat. Uma sonda copiada do irmao concordaria com o que o irmao
REM precisa, e nao provaria nada sobre o que o dashboard precisa.
REM
REM A MEDICAO, refeita nesta arvore em 2026-09-02: `import l2scanner.dashboard`
REM traz 342 modulos e EXATAMENTE DUAS distribuicoes de site-packages, cv2 e
REM numpy. Nenhuma de captura de tela (mss), nenhuma de janela
REM (windows_capture) e nenhuma de OCR (winrt) entra nesta cadeia -- este
REM processo nao olha para a tela do jogo, entao nada disso e sondado aqui.
REM
REM O NUMERO QUE CAIU, dito em voz alta: a pesquisa desta fase antecipava um
REM lancador SEM ambiente virtual nenhum, com o dashboard virando stdlib puro
REM depois do corte de RAIZ. A medicao derrubou essa expectativa. O corte de
REM RAIZ matou a aresta mercado_catalogo para config, mas sobrou a segunda,
REM mercado_console para console para rastreador para visao, e o dashboard e
REM OBRIGADO a usar os formatadores de mercado_console (DASH-03, um formatador
REM so). Cortar a segunda exigiria mexer em console.py ou rastreador.py, fora
REM do que o usuario autorizou nesta fase. Um numero que caiu precisa dizer que
REM caiu, inclusive num arquivo de lote.
".venv\Scripts\python.exe" -c "import cv2,numpy" >nul 2>&1
if errorlevel 1 goto erro_dependencias

REM ESTA JANELA NAO INSTALA NADA quando o ambiente ja existe, e isso e de
REM proposito -- mesma regra do ponte-discord.bat, pelo mesmo motivo MEDIDO
REM naquele arquivo: os pinos do requirements.txt sao abertos, e o dashboard
REM foi feito para ser aberto COM O SCANNER FARMANDO. Rodar o instalador daqui
REM nesse instante escreveria por cima de cv2.pyd e das DLLs do numpy com elas
REM CARREGADAS pelo outro processo -- falha de arquivo travado, ou pior, um
REM upgrade silencioso da pilha numerica no meio da coleta. Seria esta janela
REM derrubando a coleta da noite, que e exatamente o oposto do que o DASH-06
REM promete. Aqui a gente confere e recusa; quem conserta e o vigiar-mercado.bat.

REM OS BLOCOS DE ERRO VEM ANTES DA LINHA DE EXECUCAO, e nao depois dela.
REM Nao e estilo: e o que torna ESTRUTURAL a promessa de que nada e impresso
REM depois de o programa rodar. O defeito medido em campo no
REM calibrar-mercado.bat, em 2026-08-28, foi exatamente um bloco de
REM encerramento saindo depois de a ferramenta ter saido em codigo 1 --
REM anunciando um desfecho que o .bat nao conferiu. Aqui nao ha bloco de
REM encerramento nenhum: a porta ocupada, a porta reservada e o encerramento
REM normal sao TODOS impressos pelo proprio programa, que e quem sabe o que
REM aconteceu.
goto executar

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

:erro_dependencias
echo.
echo  O ambiente existe, mas faltam pecas que o dashboard usa.
echo  Rode vigiar-mercado.bat uma vez primeiro - ele monta tudo.
echo  Esta janela nao instala nada de proposito: ela pode estar
echo  sendo aberta com a coleta rodando, e instalar por cima de
echo  uma biblioteca carregada derrubaria a coleta da noite.
echo.
pause
exit /b 1

:executar
REM O MODULO E CHAMADO DIRETO, e nao pelo ponto de entrada do pacote. E assim
REM que o caminho do --mercado fica INTOCADO: l2scanner\__main__.py nao muda uma
REM linha para o dashboard existir, e por isso os dois nao se encontram nem para
REM subir nem para cair (DASH-06).
REM
REM O %* no fim e o que deixa voce passar --porta 8788 sem editar fonte nenhum.
REM
REM O NAVEGADOR NAO E ABERTO AQUI, e sim pelo main do Python, DEPOIS de o bind
REM ter dado certo. Abrir antes mostraria uma aba de erro de conexao justamente
REM no caso da porta ocupada -- que e o caso em que o usuario mais precisa ler a
REM mensagem que esta nesta janela preta, e nao um "nao foi possivel acessar
REM este site" que nao explica nada.
".venv\Scripts\python.exe" -m l2scanner.dashboard %*

pause
