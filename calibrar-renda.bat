@echo off
setlocal

REM ============================================================
REM  Calibrar a RENDA: o EXP, a ADENA e o NIVEL
REM
REM  Com o jogo aberto, marque tres regioes da janela:
REM    1. o campo do EXP, na barra inferior esquerda;
REM    2. o campo da ADENA, na barra inferior direita;
REM    3. o numero do NIVEL, na janela de status.
REM
REM  A CALIBRACAO E POR PERSONAGEM. Medido: as duas instancias
REM  poem a janela de status em lugares diferentes, 14 px na
REM  vertical. Rode uma vez para CADA personagem que voce farma.
REM
REM  QUANDO RODAR:
REM    - voce moveu ou redimensionou a janela do jogo;
REM    - voce mudou a resolucao ou a escala da tela;
REM    - a leitura parou de bater com o que a tela mostra.
REM
REM  DE ONDE VEM A TELA:
REM
REM    calibrar-renda.bat --janela "NOME - XM Essence"
REM        le a janela viva daquele personagem. O nome do
REM        personagem sai do proprio titulo.
REM
REM    calibrar-renda.bat --imagem ^<frame.png^> --personagem NOME
REM        trabalha sobre uma gravacao. Assim voce pode errar,
REM        refazer e conferir a vontade, sem o jogo fechar no
REM        meio. Aqui --personagem e OBRIGATORIO: um PNG nao
REM        carrega titulo de janela.
REM
REM    calibrar-renda.bat --so-medir
REM        so IMPRIME a curva de brilho dos retangulos que ja
REM        estao gravados. NAO escreve nada no disco.
REM
REM  EM CADA SELECAO:
REM    ENTER               aceita o retangulo ja desenhado
REM    qualquer outra tecla deixa voce arrastar o seu
REM    ESC                 mantem o retangulo anterior daquela
REM                        regiao. Ele NAO e zerado.
REM
REM  Ele mantem TODO o resto da calibracao anterior intacto,
REM  inclusive a de outros personagens.
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

".venv\Scripts\python.exe" -m l2scanner.calibrar_renda %*

REM O bloco de conferencia SO sai quando a ferramenta terminou bem.
REM Sem esta guarda, uma recusa (personagem desconhecido, retangulo
REM fora do frame, --partir-de sem --so-medir) imprimiria mesmo assim
REM o bloco que manda conferir a imagem -- mandando o usuario conferir
REM um arquivo que nunca foi gerado. E a mesma mentira que o
REM calibrar-mercado.bat ja pagou em campo em 2026-08-28.
if errorlevel 1 (
    echo.
    echo  ------------------------------------------------------------
    echo   A CALIBRACAO NAO FOI CONCLUIDA. Nada foi gravado.
    echo   A mensagem acima diz o motivo.
    echo.
    echo   Se faltou dizer de quem e a tela, e assim:
    echo     calibrar-renda.bat --janela "NOME - XM Essence"
    echo     calibrar-renda.bat --imagem ^<frame.png^> --personagem NOME
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
echo   diz que nao deu para gravar nenhuma. Abra a que ela citou e
echo   confira se os tres retangulos caem onde voce espera:
echo     amarelo = o EXP    verde = a ADENA    azul = o NIVEL
echo.
echo   CONFIRA TAMBEM A CURVA DE BRILHO impressa acima. Ela diz,
echo   piso por piso, o que a mascara deixou passar. Uma banda de
echo   largura 1 ou 2 saiu com AVISO: aquela calibracao vai quebrar
echo   quando voce mudar de lugar de farm, e o aviso existe para
echo   voce saber que foi isso, e nao um defeito do scanner.
echo.
echo   A ADENA ainda nao tem piso medido nesta rodada: ela e lida
echo   por GLIFO e nao por OCR. A ordem de operacao impressa acima
echo   diz o que falta e em que ordem.
echo  ------------------------------------------------------------
echo.
pause
