"""O .bat de calibracao nao pode mentir que deu certo.

MEDIDO EM CAMPO, 2026-08-28. O usuario rodou `calibrar-mercado.bat` sem
argumento. A ferramenta recusou corretamente ("diga de onde ler") e saiu com
codigo 1 -- mas o .bat imprimia o bloco de conferencia MESMO ASSIM:

    ABRA a imagem calibracao-conferencia.png e confira se os
    retangulos verdes caem onde voce espera...

Mandando o usuario conferir um arquivo que nunca foi gerado.

E a mesma mentira que o FUND-01 tirou do gravador, um nivel acima: dizer que
deu certo sem ter conferido que deu. O gravador contava frames que nao checou
terem sido escritos; o .bat anunciava uma calibracao que nao checou ter
acontecido. Por isso o teste mora aqui e nao num canto de "polimento de UX".
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
BAT = RAIZ / "calibrar-mercado.bat"


def _texto() -> str:
    return BAT.read_text(encoding="cp1252")


def _posicao_do_echo(texto: str, trecho: str, inicio: int = 0) -> int:
    """Onde um ECHO diz `trecho` -- comentario REM nao conta.

    A primeira versao deste teste procurava a frase crua e foi enganada pelo
    proprio comentario que explica o defeito. Uma guarda que se satisfaz com
    prosa nao guarda nada: o que precisa vir depois do `if errorlevel` e a
    linha que o cmd EXECUTA.
    """
    for casamento in re.finditer(re.escape(trecho), texto):
        if casamento.start() < inicio:
            continue
        comeco_da_linha = texto.rfind(chr(10), 0, casamento.start()) + 1
        linha = texto[comeco_da_linha : casamento.start()].strip().lower()
        if linha.startswith("echo"):
            return casamento.start()
    return -1


def test_o_bat_existe():
    assert BAT.is_file(), "calibrar-mercado.bat sumiu"


def test_o_bloco_de_conferencia_vem_depois_de_uma_guarda_de_erro():
    """A guarda tem de estar ENTRE a chamada da ferramenta e o bloco de sucesso.

    Nao basta existir um `if errorlevel` em algum lugar do arquivo: ele precisa
    interromper o caminho antes da mensagem que manda conferir a imagem.
    """
    t = _texto()

    chamada = t.find("l2scanner.calibrar_mercado")
    guarda = t.find("if errorlevel 1", chamada)
    conferencia = _posicao_do_echo(t, "ABRA a imagem", chamada)

    assert chamada != -1, "o .bat nao chama mais l2scanner.calibrar_mercado"
    assert guarda != -1, "sumiu a guarda `if errorlevel 1` depois da chamada"
    assert conferencia != -1, "sumiu o bloco de conferencia"
    assert guarda < conferencia, (
        "o bloco 'ABRA a imagem' vem ANTES da guarda de erro -- uma falha da "
        "ferramenta voltaria a anunciar uma calibracao que nao aconteceu"
    )


def test_a_guarda_encerra_o_script_com_codigo_de_falha():
    """Sair com 0 depois de falhar mentiria para quem encadeia o .bat."""
    t = _texto()
    guarda = t.find("if errorlevel 1")
    trecho = t[guarda : _posicao_do_echo(t, "ABRA a imagem", guarda)]
    assert "exit /b 1" in trecho, (
        "a guarda nao encerra com `exit /b 1`; um chamador veria sucesso"
    )


def test_a_mensagem_de_falha_diz_que_nada_foi_gravado():
    """O usuario precisa saber que o disco NAO mudou, nao so que 'deu erro'."""
    t = _texto()
    guarda = t.find("if errorlevel 1")
    trecho = t[guarda : _posicao_do_echo(t, "ABRA a imagem", guarda)]
    assert re.search(r"[Nn]ada foi gravado", trecho), (
        "a mensagem de falha nao afirma que nada foi gravado"
    )


def test_os_sinais_de_maior_e_menor_estao_escapados():
    """`<pasta>` cru dentro de um echo vira redirecionamento no cmd.

    Sem o escape o proprio bloco de erro morria com 'A sintaxe do comando esta
    incorreta' -- medido ao escrever esta guarda.
    """
    t = _texto()
    for linha in t.splitlines():
        despido = linha.strip()
        if not despido.lower().startswith("echo "):
            continue
        for sinal in ("<", ">"):
            for pos in (i for i, c in enumerate(despido) if c == sinal):
                assert pos > 0 and despido[pos - 1] == "^", (
                    f"`{sinal}` sem escape num echo do .bat, o cmd trata como "
                    f"redirecionamento: {despido!r}"
                )
