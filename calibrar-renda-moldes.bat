@echo off
setlocal

REM ============================================================
REM  Cortar os MOLDES DE DIGITO da fonte da BARRA inferior
REM
REM  QUANDO RODAR: a primeira vez, para a adena passar a ser
REM  lida por glifo em vez de por OCR. E DE NOVO, APONTANDO
REM  OUTRO --campo, TODA VEZ QUE A SAIDA DISSER QUE FALTAM
REM  ROTULOS. Esta e a unica ferramenta desta casa feita para
REM  ser rodada mais de uma vez -- e a saida dela diz, por
REM  nome, o que falta e EM QUE CAMPO DA BARRA procurar.
REM
REM  ELA NAO LE A TELA AO VIVO. Ela trabalha sobre imagens que
REM  ja estao no disco, entao voce pode errar, refazer e
REM  conferir a vontade, sem o painel fechar no meio.
REM
REM  ------------------------------------------------------------
REM  A MAQUINA PROPOE, VOCE CONFIRMA
REM
REM    ENTER          aceita a leitura proposta
REM    digitar        corrige (o que voce digita SEMPRE vence)
REM
REM  Na PRIMEIRA rodada nao ha molde nenhum e nao ha proposta:
REM  voce digita o numero inteiro, olhando o recorte ampliado.
REM  E assim que o primeiro molde nasce certo.
REM
REM  A proposta e TUDO OU NADA de proposito. Uma proposta pela
REM  metade convidaria ao ENTER distraido justamente sobre a
REM  parte que a ferramenta NAO sabia.
REM
REM  ------------------------------------------------------------
REM  1) ENSAIO, sem escrever nada no disco:
REM
REM       calibrar-renda-moldes.bat --gravacoes tests\fixtures\renda ^
REM           --campo adena --filtro barra_direita ^
REM           --recorte inteiro --piso 185 --propor
REM
REM     Ela imprime, frame a frame, o que proporia -- e nao
REM     toca na calibracao. E o jeito de conferir que o
REM     recorte e o piso estao certos ANTES de gravar.
REM
REM  2) A RODADA DE VERDADE: o mesmo comando SEM o --propor.
REM
REM  3) OUTRO CAMPO, quando faltar rotulo. Passe o retangulo
REM     daquele campo e o piso dele:
REM
REM       calibrar-renda-moldes.bat --gravacoes recordings\<pasta> ^
REM           --campo lcoin --recorte <esq>,<topo>,<LARG>x<ALT> --piso <n>
REM
REM     --campo aceita: adena, lcoin, bonus, exp.
REM     `adena` e `exp` ja tem retangulo calibrado por
REM     personagem: para esses dois basta --personagem <nome>.
REM
REM  ------------------------------------------------------------
REM  ENQUADRE O CAMPO DE ICONE A ICONE
REM
REM  A peneira de forma e a MESMA que a leitura usa: ela espera
REM  uma corrida larga (o icone) em cada ponta e so larguras de
REM  digito e de virgula no meio. Um recorte fora dessa forma e
REM  PULADO, com o frame e o motivo nomeados.
REM
REM  Isso nao e chatice: moldes cortados de um recorte que a
REM  leitura recusaria seriam cortados de um conjunto de
REM  corridas e lidos de outro, e o desalinhamento apareceria
REM  como pontuacao baixa -- que e a forma de defeito que
REM  alguem "conserta" baixando o piso de leitura.
REM
REM  SE ELA PULAR DIZENDO QUE A CORRIDA E LARGA DEMAIS: e a
REM  BARRA VERDE de progresso entrando na mascara e colando o
REM  campo inteiro num borrao so. Aperte o recorte VERTICAL ate
REM  sobrar so a linha do texto, ou suba o piso. Ela NAO fatia
REM  aquele borrao -- fatia-lo fabricaria dezenas de digitos
REM  que nunca estiveram na tela.
REM
REM  ------------------------------------------------------------
REM  O CONJUNTO PODE FICAR INCOMPLETO, E TUDO BEM
REM
REM  Ela GRAVA o que voce confirmou, mesmo que faltem rotulos,
REM  e ANUNCIA por nome o que falta. Enquanto faltar, a adena
REM  vai RECUSAR em vez de ser lida -- e isso e a peneira
REM  funcionando, nao um defeito. Meio conjunto de moldes le um
REM  `8` como `0` com a mesma confianca de uma leitura certa.
REM
REM  NAO complete o conjunto a mao, e nao aceite um rotulo que
REM  voce nao conseguiu LER no recorte ampliado. Um conjunto
REM  completado com palpite e pior que um conjunto pela metade.
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

".venv\Scripts\python.exe" -m l2scanner.calibrar_renda_moldes %*

if errorlevel 1 (
    echo.
    echo  ------------------------------------------------------------
    echo   A RODADA NAO FOI CONCLUIDA. Nada foi gravado.
    echo   A mensagem acima diz o motivo.
    echo.
    echo   Se faltou dizer de onde ler, e assim:
    echo     calibrar-renda-moldes.bat --gravacoes ^<pasta^> --campo adena ^
    echo         --personagem ^<nome^>
    echo  ------------------------------------------------------------
    echo.
    pause
    exit /b 1
)

echo.
echo  ------------------------------------------------------------
echo   A MENSAGEM ACIMA lista, por NOME, os rotulos que voce ja
echo   tem e os que ainda faltam -- e diz em que campo da barra
echo   cada faltante foi medido.
echo.
echo   Se faltar algum, RODE DE NOVO apontando aquele campo:
echo     calibrar-renda-moldes.bat --gravacoes ^<pasta^> --campo bonus ^
echo         --recorte ^<esq^>,^<topo^>,^<LARG^>x^<ALT^> --piso ^<n^>
echo.
echo   Nao ha nada a esperar do farm: os rotulos que faltavam ja
echo   foram medidos na tela, em outros campos da MESMA barra.
echo  ------------------------------------------------------------
echo.
pause
