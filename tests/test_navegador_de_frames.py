"""O navegador de frames: as teclas que ele aceita e a saida quando some a janela.

Ele existe porque calibrar sobre um frame OCLUIDO nasce torto em silencio -- a
mesma familia do incidente 27x. A escolha e do olho do usuario; entao o teclado
e a unica interface, e as duas coisas afirmadas aqui sao sobre ela.

Nada aqui abre janela de verdade: o HighGUI e dublado inteiro. O que se afirma e
a maquina de estados de teclas, que e onde os dois defeitos moravam.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.calibrar_mercado as cm
from l2scanner.calibrar_mercado import (
    SETA_BAIXO,
    SETA_CIMA,
    SETA_DIREITA,
    SETA_ESQUERDA,
    MercadoNaoCalibravel,
    navegar_e_escolher,
)

ENTER = 13
ESC = 27


@pytest.fixture
def quadros(tmp_path: Path) -> list[Path]:
    """30 PNGs minusculos de verdade -- `cv2.imread` nao e dublado."""
    caminhos = []
    for i in range(30):
        caminho = tmp_path / f"frame_{i:06d}.png"
        assert cv2.imwrite(str(caminho), np.full((20, 30, 3), i, dtype=np.uint8))
        caminhos.append(caminho)
    return caminhos


@pytest.fixture
def highgui_dublado(monkeypatch: pytest.MonkeyPatch):
    """Silencia toda a GUI e devolve um controle da janela e das teclas.

    `janela_viva` comeca em True; um teste pode desligar para simular o usuario
    fechando no X.
    """
    estado = {"viva": True, "teclas": []}

    for nome in ("namedWindow", "moveWindow", "imshow", "destroyWindow"):
        monkeypatch.setattr(cv2, nome, lambda *a, **k: None)
    monkeypatch.setattr(cv2, "waitKey", lambda *a, **k: -1)
    monkeypatch.setattr(
        cv2,
        "getWindowProperty",
        lambda *a, **k: 1.0 if estado["viva"] else 0.0,
    )

    def waitKeyEx_falso(_ms=0):
        if not estado["teclas"]:
            return -1
        return estado["teclas"].pop(0)

    monkeypatch.setattr(cv2, "waitKeyEx", waitKeyEx_falso)
    return estado


class TestAsTeclasDeNavegacao:
    """WR-03: os codigos 81-84 eram as setas do GTK e sao Q/R/S/T em ASCII."""

    def test_S_maiusculo_VOLTA_dez_como_o_s_minusculo(
        self, quadros, highgui_dublado
    ):
        """`ord("S") == 83`, que estava no ramo do 'proximo frame'.

        O `S` maiusculo andava para FRENTE em vez de voltar dez, e o `ord("S")`
        do ultimo ramo era codigo morto -- inalcancavel. Duas teclas com o mesmo
        nome fazendo coisas opostas, num navegador cujo unico proposito e o
        usuario chegar no frame limpo.
        """
        highgui_dublado["teclas"] = [ord("S"), ENTER]

        escolhido = navegar_e_escolher(quadros, comeco=15)

        assert escolhido == quadros[5], (
            f"'S' levou a {escolhido.name}; o 's' minusculo leva a "
            f"{quadros[5].name}. As duas sao a mesma tecla para quem digita."
        )

    def test_s_minusculo_e_S_maiusculo_fazem_a_mesma_coisa(
        self, quadros, highgui_dublado
    ):
        highgui_dublado["teclas"] = [ord("s"), ENTER]
        assert navegar_e_escolher(quadros, comeco=15) == quadros[5]

    @pytest.mark.parametrize(
        "tecla,comeco,esperado",
        [
            (ord("d"), 10, 11),
            (ord("D"), 10, 11),
            (SETA_DIREITA, 10, 11),
            (ord("a"), 10, 9),
            (ord("A"), 10, 9),
            (SETA_ESQUERDA, 10, 9),
            (ord("w"), 10, 20),
            (SETA_CIMA, 10, 20),
            (SETA_BAIXO, 10, 0),
        ],
        ids=[
            "d", "D", "seta-direita",
            "a", "A", "seta-esquerda",
            "w", "seta-cima", "seta-baixo",
        ],
    )
    def test_cada_tecla_anda_para_o_lado_certo(
        self, quadros, highgui_dublado, tecla: int, comeco: int, esperado: int
    ):
        highgui_dublado["teclas"] = [tecla, ENTER]
        assert navegar_e_escolher(quadros, comeco) == quadros[esperado]

    def test_as_setas_do_GTK_nao_sao_mais_lidas_como_setas(
        self, quadros, highgui_dublado
    ):
        """81-84 sao Q/R/S/T aqui. `T` (84) nao pode andar nada.

        `S` (83) tem o proprio ramo -- volta dez --, e ele e coberto acima.
        """
        highgui_dublado["teclas"] = [84, ENTER]  # 'T', a antiga "seta baixo"
        assert navegar_e_escolher(quadros, comeco=10) == quadros[10]

    def test_uma_tecla_desconhecida_nao_move_e_nao_derruba(
        self, quadros, highgui_dublado
    ):
        highgui_dublado["teclas"] = [ord("z"), ENTER]
        assert navegar_e_escolher(quadros, comeco=7) == quadros[7]

    def test_o_ESC_cancela_sem_gravar(self, quadros, highgui_dublado):
        highgui_dublado["teclas"] = [ESC]
        with pytest.raises(MercadoNaoCalibravel, match="cancelada"):
            navegar_e_escolher(quadros, comeco=3)

    def test_os_extremos_nao_saem_da_lista(self, quadros, highgui_dublado):
        highgui_dublado["teclas"] = [SETA_ESQUERDA, SETA_ESQUERDA, ENTER]
        assert navegar_e_escolher(quadros, comeco=0) == quadros[0]

        highgui_dublado["teclas"] = [SETA_CIMA, SETA_CIMA, ENTER]
        assert navegar_e_escolher(quadros, comeco=29) == quadros[29]


class TestFecharNoXNaoTrava:
    """WR-04: `waitKey(0)` bloqueava para sempre quando nao havia mais janela."""

    def test_fechar_a_janela_levanta_em_vez_de_travar(
        self, quadros, highgui_dublado
    ):
        """Sem prazo, este teste nao terminaria -- e era o que acontecia ao vivo.

        O console ficava parado na tela de instrucoes, sem janela e sem
        mensagem, e a unica saida era Ctrl-C.
        """
        highgui_dublado["viva"] = False

        with pytest.raises(MercadoNaoCalibravel) as erro:
            navegar_e_escolher(quadros, comeco=0)

        assert "fechada" in str(erro.value)
        assert "nada foi gravado" in str(erro.value)
        assert "ESC" in str(erro.value), "a mensagem nao diz como cancelar direito"

    def test_a_sondagem_vazia_nao_e_confundida_com_tecla(
        self, quadros, highgui_dublado
    ):
        """Com prazo, `waitKeyEx` devolve -1 o tempo todo em que ninguem digita.

        Um `-1 & 0xFF == 255` cairia no ramo de 'tecla desconhecida' -- inofensivo
        --, mas o laco tem de continuar esperando, nao consumir o frame.
        """
        highgui_dublado["teclas"] = [-1, -1, -1, ord("d"), -1, ENTER]
        assert navegar_e_escolher(quadros, comeco=4) == quadros[5]

    def test_o_texto_de_ajuda_avisa_para_nao_fechar_no_X(
        self, quadros, highgui_dublado, capsys
    ):
        """O bloco de selecao ja avisava; este nao avisava nada."""
        highgui_dublado["teclas"] = [ENTER]
        navegar_e_escolher(quadros, comeco=0)
        assert "NAO feche" in capsys.readouterr().out
