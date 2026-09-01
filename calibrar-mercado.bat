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
REM  SAO DUAS INVOCACOES, e a segunda existe por um motivo
REM  medido -- nao e opcional nem enfeite.
REM
REM  1) O FLUXO COMPLETO, apontando a pasta da sua gravacao:
REM
REM       calibrar-mercado.bat --gravacao recordings\<pasta>
REM
REM     A FERRAMENTA PROPOE E VOCE CONFIRMA. Ela mede o painel
REM     nos pixels e abre cada janela com o retangulo JA
REM     DESENHADO em verde:
REM
REM       ENTER               aceita o retangulo proposto
REM       qualquer outra tecla deixa voce arrastar o seu
REM       ESC                 cancela sem gravar nada
REM
REM     Voce confere, um retangulo de cada vez:
REM       1. as tres ancoras do painel (titulo, X de fechar, seta)
REM       2. a area da lista e a primeira linha dela
REM       3. o nome de cada item da watchlist do config.toml
REM       4. os numeros da coluna de preco, para cortar os glifos
REM
REM     Nos numeros, quando ela conseguir LER o preco pelos glifos
REM     que voce ja confirmou, ela propoe a leitura e o ENTER
REM     confirma. O que voce digitar sempre vence.
REM
REM     Se ela nao conseguir medir alguma regiao neste frame, a
REM     janela abre vazia e voce arrasta como antes. Nada foi
REM     tirado -- so deixou de ser obrigatorio.
REM
REM  2) SO OS DIGITOS QUE FALTARAM, sobre OUTRO frame:
REM
REM       calibrar-mercado.bat --so-digitos --frame <frame.png>
REM
REM     Um frame so quase nunca tem os dez digitos na tela. O frame
REM     que calibra a grade, por exemplo, nao tem o `8` em lugar
REM     nenhum. Esta segunda invocacao corta so os glifos que
REM     faltam, sobre um frame que os tenha, SEM refazer as
REM     ancoras e a grade -- e FUNDE com o que ja estava gravado.
REM
REM  3) OS GLIFOS DO TEXTO CIANO, num conjunto SEPARADO:
REM
REM       calibrar-mercado.bat --so-digitos --tinta cromatica --frame <frame.png>
REM
REM     O PRECO EM CIANO NAO SE LE COM OS MOLDES BRANCOS, e isso
REM     foi medido e nao suposto. Os moldes brancos foram cortados
REM     de texto com pico de brilho 226-230; o ciano desenha o
REM     MESMO glifo com pico 255, e a borda antisserrilhada do `0`
REM     passa a sobreviver ao corte. O `0` vira um anel FECHADO, e
REM     anel fechado casa melhor com o `8`. Resultado em campo:
REM     `100,00` lido como `188,88`, com gramatica perfeita.
REM
REM     `--tinta cromatica` grava numa CHAVE PROPRIA. Ela NAO toca
REM     nos moldes brancos -- e nao e questao de cuidado, e que sao
REM     duas chaves diferentes no arquivo.
REM
REM     ENQUANTO O CONJUNTO CIANO NAO ESTIVER COMPLETO (os dez
REM     digitos e a virgula), NADA MUDA: a celula ciana continua
REM     sendo DESCARTADA, como ja e hoje. Conjunto pela metade
REM     vale o mesmo que conjunto nenhum -- meio conjunto leria
REM     um `8` como `0`, que e o mesmo defeito ao contrario.
REM
REM     SE ELA RECUSAR DIZENDO QUE O `0` E UM ANEL PARTIDO: voce
REM     cortou de uma linha da faixa ESCURA da grade. A grade e
REM     zebrada, e so os moldes cortados na faixa CLARA servem as
REM     duas. Nao ha regra de "linha par ou impar" -- a rolagem
REM     desloca a faixa. Corte de uma linha cujo total apareca
REM     ERRADO hoje (um `8` onde a tela mostra `0`): essas estao,
REM     por definicao, na faixa clara. Nada foi gravado.
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
REM de confusao) imprimia mesmo assim "ABRA a imagem de conferencia" �
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
echo.
echo   Se ela disse que FALTAM GLIFOS, complete o conjunto com um
echo   frame que tenha os que faltam:
echo     calibrar-mercado.bat --so-digitos --frame ^<frame.png^>
echo   Enquanto faltar glifo, a leitura de precos vai descartar
echo   toda linha que contenha um glifo nao gravado.
echo  ------------------------------------------------------------
echo.
pause
