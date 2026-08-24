@echo off
REM Liga o scanner: vigia a party window e avisa no WhatsApp.
REM
REM Antes do primeiro uso:
REM   1. Copie ENV-EXEMPLO.txt para .env e preencha os dados do Chatwoot
REM   2. Rode calibrar-tela.bat para marcar onde fica a sua party window
REM
REM Deixe esta janela aberta enquanto farma. Ctrl+C encerra.

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

python -m l2scanner %*

echo.
pause
