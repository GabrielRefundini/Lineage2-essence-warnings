"""A janela onde o usuario DESENHA os retangulos tem de ter o tamanho da imagem.

Este arquivo existe por causa de uma regressao de 2026-08-28. O bloco
`namedWindow` + `moveWindow` foi adicionado a `_selecionar_regiao` para resolver
um problema real -- numa maquina de dois monitores a janela de selecao nascia
onde o usuario nao a achava, e uma ferramenta interativa cuja janela some e
indistinguivel de uma ferramenta travada. O objetivo era legitimo; o flag
escolhido, `cv2.WINDOW_NORMAL`, nao.

Uma janela `WINDOW_NORMAL` NAO se dimensiona pela imagem: ela nasce no tamanho
que o Win32 resolver dar e a imagem e espremida dentro dele. MEDIDO nesta
maquina (cv2 4.14.0), chamando `_selecionar_regiao` de verdade com o
`cv2.selectROI` dublado e lendo `getWindowImageRect` do MESMO titulo, que e a
janela onde o arrasto aconteceria:

    visao 1600x1295 | WINDOW_NORMAL   -> 120x1440   (e 304x281 noutra medicao)
    visao 1600x1295 | WINDOW_AUTOSIZE -> 1600x1295
    visao 1720x1392 | WINDOW_NORMAL   -> 120x1440
    visao 1720x1392 | WINDOW_AUTOSIZE -> 1720x1392

O numero do NORMAL varia entre execucoes porque nao vem da imagem -- e essa
instabilidade e o argumento, nao um detalhe. O AUTOSIZE bate a imagem em toda
dimensao testada.

Por que isso e caro: a visualizacao JA e reescalada (`escala = 1600/largura`) e
`_selecionar_regiao` divide a caixa desenhada por essa escala para voltar ao
original. Um SEGUNDO encolhimento, feito pelo sistema de janelas, nao entra
nessa conta. O retangulo sai plausivel e no lugar errado -- que e literalmente o
que o docstring da funcao chama de "o defeito mais caro que uma ferramenta de
calibracao pode ter".

E `_selecionar_regiao` e COMPARTILHADA: `calibrar_selecionando` (a party window,
a ancora, o passo entre membros -- tudo que a deteccao de morte usa) passa por
aqui. A regressao atingia uma calibracao que funcionava.

Os testes de janela sao pulados, com a razao dita, quando o HighGUI nao esta
disponivel (build headless do OpenCV, sessao sem display). O tripwire
estrutural no fim do arquivo nao depende de GUI nenhuma e roda sempre.
"""

from __future__ import annotations

import inspect
import io
import tokenize

import cv2
import numpy as np
import pytest

import l2scanner.calibrar
import l2scanner.calibrar_mercado
from l2scanner.calibrar import _selecionar_regiao


def _sem_prosa(fonte: str) -> str:
    """O fonte sem comentarios nem docstrings -- so o que o Python executa.

    O tripwire proibe uma MECANICA, nao uma palavra: sem isto, o proprio
    comentario que explica a proibicao faria o teste reprovar.
    """
    pedacos = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(fonte).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            pedacos.append(tok.string)
    except tokenize.TokenError:  # pragma: no cover - fonte truncado
        return fonte
    return " ".join(pedacos)


def _exige_highgui() -> None:
    """Pula o teste, dizendo o motivo, quando nao ha janela possivel."""
    try:
        cv2.namedWindow("__sonda_highgui__", cv2.WINDOW_AUTOSIZE)
        cv2.destroyWindow("__sonda_highgui__")
        cv2.waitKey(1)
    except cv2.error as erro:  # pragma: no cover - depende do ambiente
        pytest.skip(
            "HighGUI indisponivel neste ambiente (build headless do OpenCV ou "
            f"sessao sem display): {erro}. O tamanho da janela de selecao so "
            "pode ser MEDIDO onde ha janela; o tripwire estrutural deste "
            "arquivo cobre o resto."
        )


def _medir_a_janela_da_selecao(pixels: np.ndarray) -> tuple[tuple, tuple, tuple]:
    """Roda `_selecionar_regiao` DE VERDADE e mede a janela que o usuario recebe.

    O unico duble e o `cv2.selectROI`, que exige arrasto de mouse humano. Ele e
    substituido por uma funcao que le `getWindowImageRect` do titulo recebido --
    ou seja, da janela exata onde o arrasto aconteceria -- e devolve uma caixa
    conhecida, para conferir tambem a volta da reescala.

    Devolve (rect_da_janela, tamanho_da_visao, caixa_devolvida).
    """
    medido: dict = {}
    original = cv2.selectROI

    def duble(titulo, imagem, showCrosshair=False):
        cv2.waitKey(50)  # deixa o gerenciador de janelas assentar antes de medir
        medido["rect"] = cv2.getWindowImageRect(titulo)
        medido["visao"] = (imagem.shape[1], imagem.shape[0])
        return (10, 20, 100, 50)

    cv2.selectROI = duble
    try:
        caixa = _selecionar_regiao(pixels, "medicao", "arraste")
    finally:
        cv2.selectROI = original
        cv2.destroyAllWindows()
        cv2.waitKey(1)
    return medido["rect"], medido["visao"], caixa


class TestOTamanhoDaJanelaDeDesenho:
    """A janela tem de ter EXATAMENTE o tamanho da imagem mostrada nela."""

    @pytest.mark.parametrize(
        "largura,altura",
        [
            (800, 600),      # janela pequena: nada e reescalado
            (1600, 1295),    # o limite exato da reescala
            (1720, 1392),    # a janela do usuario que motivou o navegador
        ],
    )
    def test_a_janela_tem_o_tamanho_da_imagem(self, largura: int, altura: int):
        _exige_highgui()
        pixels = np.zeros((altura, largura, 3), dtype=np.uint8)

        rect, visao, _ = _medir_a_janela_da_selecao(pixels)

        assert (rect[2], rect[3]) == visao, (
            f"a janela de desenho saiu {rect[2]}x{rect[3]} para uma imagem de "
            f"{visao[0]}x{visao[1]}. O usuario desenha numa escala que "
            f"`_selecionar_regiao` NAO desconta -- ela so divide por `escala`, "
            f"a reescala dela. Cada pixel de mouse vira "
            f"{visao[0] / max(rect[2], 1):.1f} px gravados no calibration.json, "
            f"e o retangulo sai plausivel no lugar errado. Isto foi uma "
            f"regressao de WINDOW_NORMAL: use WINDOW_AUTOSIZE, ou declare o "
            f"tamanho com resizeWindow logo depois do namedWindow."
        )

    def test_a_calibracao_de_party_volta_a_ser_um_para_um(self):
        """O caminho COMPARTILHADO: janela que cabe em 1600 px nao reescala nada.

        `calibrar_selecionando` -- party window, ancora, passo entre membros --
        chama esta mesma funcao. Com a janela do jogo em 1600 px ou menos,
        `escala == 1.0`: o pixel que o usuario ve, o pixel que ele arrasta e o
        pixel gravado tem de ser o MESMO. Isso valia antes desta fase e a
        regressao do WINDOW_NORMAL tirou.
        """
        _exige_highgui()
        pixels = np.zeros((900, 1440, 3), dtype=np.uint8)

        rect, visao, caixa = _medir_a_janela_da_selecao(pixels)

        assert visao == (1440, 900), "a visao nao devia ter sido reescalada"
        assert (rect[2], rect[3]) == (1440, 900), (
            f"janela {rect[2]}x{rect[3]} para um frame 1440x900: o arrasto da "
            f"calibracao de party deixou de ser 1:1"
        )
        assert caixa == (10, 20, 100, 50), (
            "a caixa desenhada voltou alterada num caminho sem reescala"
        )


class TestOTripwireEstrutural:
    """Sem GUI: proibir a mecanica, para a regressao nao voltar calada."""

    @pytest.mark.parametrize(
        "modulo",
        [l2scanner.calibrar, l2scanner.calibrar_mercado],
        ids=["calibrar", "calibrar_mercado"],
    )
    def test_nenhum_WINDOW_NORMAL_sem_resizeWindow_ao_lado(self, modulo):
        codigo = _sem_prosa(inspect.getsource(modulo))
        if "WINDOW_NORMAL" not in codigo:
            return
        assert "resizeWindow" in codigo, (
            f"{modulo.__name__} cria janela com WINDOW_NORMAL e nao declara o "
            f"tamanho com resizeWindow. Uma janela NORMAL nasce no tamanho que "
            f"o Win32 der (medido: 120x1440 para uma imagem de 1600x1295) e "
            f"espreme a imagem dentro dele. Numa ferramenta que PERSISTE "
            f"coordenadas isso produz retangulo plausivel na posicao errada. "
            f"Use WINDOW_AUTOSIZE, ou chame resizeWindow com as dimensoes reais."
        )


class TestODrenoDaFilaDeTeclas:
    """WR-05: drenar POR TEMPO, nao ate a primeira sondagem vazia.

    O fix do vazamento de ENTER era

        for _ in range(20):
            if cv2.waitKey(1) == -1:
                break

    e ele saia na primeira leitura vazia: ~1 ms de bombeamento. A ferramenta
    que DIAGNOSTICOU o defeito (`tools/diagnosticar_selecao.py`) documenta,
    medido, que isso nao basta -- "uma tecla pode chegar alguns milissegundos
    depois" -- e por isso ela mesma dreno por 300 ms.

    E o caminho de risco nao e so o navegador de frames: `calibrar()` faz 5+N
    selecoes seguidas, e a tecla que confirma a selecao k e candidata a vazar
    para a k+1. Quando isso acontece, todos os retangulos ja marcados sao
    perdidos.
    """

    def test_nao_para_na_primeira_sondagem_vazia(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Uma tecla que chega DEPOIS do primeiro -1 ainda tem de ser drenada."""
        respostas = [-1, -1, -1, 13, -1]  # o ENTER chega na 4a sondagem
        vistas: list[int] = []

        def waitKey_falso(_ms):
            valor = respostas.pop(0) if respostas else -1
            vistas.append(valor)
            return valor

        monkeypatch.setattr(cv2, "waitKey", waitKey_falso)

        drenadas = l2scanner.calibrar.esvaziar_a_fila_de_teclas(0.05)

        assert 13 in vistas, (
            "o dreno parou antes de a tecla chegar. Ela vazaria para o "
            "selectROI seguinte, que devolveria (0,0,0,0) e jogaria fora todos "
            "os retangulos ja marcados."
        )
        assert drenadas == 1

    def test_dreno_por_tempo_e_nao_por_numero_de_sondagens(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Com a fila sempre vazia, ele continua bombeando ate o prazo."""
        import time

        contador = {"n": 0}

        def waitKey_falso(_ms):
            contador["n"] += 1
            time.sleep(0.001)
            return -1

        monkeypatch.setattr(cv2, "waitKey", waitKey_falso)

        comeco = time.perf_counter()
        assert l2scanner.calibrar.esvaziar_a_fila_de_teclas(0.05) == 0
        decorrido = time.perf_counter() - comeco

        assert decorrido >= 0.05, (
            f"o dreno durou {decorrido * 1000:.1f} ms para um prazo de 50 ms"
        )
        assert contador["n"] > 20, (
            f"so {contador['n']} sondagens -- o laco antigo fazia 1 e saia"
        )

    def test_o_selecionar_regiao_usa_o_dreno_por_tempo(self):
        """Tripwire: o laco de `range(20)` com `break` nao pode voltar."""
        fonte = inspect.getsource(l2scanner.calibrar._selecionar_regiao)
        assert "esvaziar_a_fila_de_teclas()" in fonte
        assert "break" not in fonte, (
            "voltou um dreno que sai cedo dentro de _selecionar_regiao"
        )
