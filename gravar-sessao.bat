@echo off
REM Grava uma sessao de farm para servir de base de calibracao e de teste.
REM
REM Antes do primeiro uso, descubra as coordenadas da sua party window e troque
REM os numeros da linha --regiao abaixo por: esquerda,topo,largura,altura
REM (a ferramenta visual de calibracao chega na Fase 2 e dispensa isso).
REM
REM Deixe rodando enquanto farma. Ctrl+C encerra e fecha a gravacao direito.

cd /d "%~dp0"

if not exist ".venv\" (
    echo Preparando o ambiente pela primeira vez...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

python -m l2scanner --record --rotulo farm --regiao 1713,330,450,300

echo.
pause
