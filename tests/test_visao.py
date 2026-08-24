"""Testes da extracao visual — contra um frame REAL do cliente do usuario.

O frame de referencia em fixtures/ foi capturado da tela real em 2026-08-24:
party do Yazalaque com J4guar, Kaus, TioMad e Korzis, todos com HP cheio,
J4guar e Kaus com MP baixo. Ele e a verdade contra a qual a leitura e conferida.

Sem esse frame, um bug de leitura so reapareceria quando alguem morresse de novo
no jogo — e o evento alvo e justamente o que nao se reproduz sob demanda.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import (
    LIMIARES_HP_PADRAO,
    LIMIARES_MP_PADRAO,
    Calibracao,
)
from l2scanner.frames import Frame, Regiao, SaudeDoFrame
from l2scanner.visao import EstadoDaLinha, extrair, medir_barra

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def calibracao() -> Calibracao:
    return Calibracao.carregar(FIXTURES / "calibracao_de_referencia.json")


@pytest.fixture
def frame_real() -> Frame:
    pixels = cv2.imread(
        str(FIXTURES / "party_4_membros_hp_cheio.png"), cv2.IMREAD_COLOR
    )
    assert pixels is not None, "frame de referencia nao pode ser lido"
    return Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK)


class TestFrameReal:
    """A leitura tem que bater com o que se ve na tela."""

    def test_reconhece_os_quatro_membros(self, frame_real, calibracao):
        obs = extrair(frame_real, calibracao)
        assert obs.membros_presentes == 4

    def test_ui_esta_visivel(self, frame_real, calibracao):
        obs = extrair(frame_real, calibracao)
        assert obs.ui_visivel is True

    def test_todos_com_hp_cheio(self, frame_real, calibracao):
        obs = extrair(frame_real, calibracao)
        presentes = [l for l in obs.linhas if l.estado is EstadoDaLinha.COM_MEMBRO]

        for linha in presentes:
            assert linha.hp == pytest.approx(1.0, abs=0.02), (
                f"linha {linha.indice} deveria estar com HP cheio, leu {linha.hp}"
            )

    def test_mp_baixo_e_lido_como_baixo(self, frame_real, calibracao):
        """J4guar e Kaus estao com MP quase zerado na captura real.

        Este teste protege contra o leitor 'arredondar' tudo para cheio ou
        vazio: ele precisa medir fracoes intermediarias com precisao.
        """
        obs = extrair(frame_real, calibracao)

        assert obs.linhas[0].mp == pytest.approx(0.067, abs=0.02)  # J4guar
        assert obs.linhas[1].mp == pytest.approx(0.108, abs=0.02)  # Kaus
        assert obs.linhas[2].mp == pytest.approx(1.0, abs=0.02)  # TioMad
        assert obs.linhas[3].mp == pytest.approx(1.0, abs=0.02)  # Korzis

    def test_linhas_alem_da_party_estao_vazias(self, frame_real, calibracao):
        """A regiao capturada e mais alta que a party window de proposito.

        O excedente e terreno puro. Ler isso como 'membro com HP zerado' seria
        inventar mortes que nunca aconteceram.
        """
        obs = extrair(frame_real, calibracao)

        for linha in obs.linhas[4:]:
            assert linha.estado is EstadoDaLinha.VAZIA
            assert linha.hp is None

    def test_nenhuma_linha_vazia_conta_como_morte(self, frame_real, calibracao):
        """A distincao que sustenta o produto inteiro.

        'HP zerado' e 'linha ausente' leem igual nas barras: 0%. Se `hp_zerado`
        respondesse True para linha vazia, o scanner anunciaria quatro mortes
        toda vez que a PT ficasse menor.
        """
        obs = extrair(frame_real, calibracao)

        for linha in obs.linhas:
            if linha.estado is EstadoDaLinha.VAZIA:
                assert linha.hp_zerado is False


class TestFrameDoente:
    """Frame ruim nao pode produzir leitura nenhuma."""

    @pytest.mark.parametrize(
        "saude", [SaudeDoFrame.FALHA_DE_CAPTURA, SaudeDoFrame.CONGELADO]
    )
    def test_frame_doente_nao_produz_linhas(self, frame_real, calibracao, saude):
        doente = Frame(pixels=frame_real.pixels, indice=1, saude=saude)
        obs = extrair(doente, calibracao)

        assert obs.ui_visivel is False
        assert obs.linhas == ()
        assert obs.membros_presentes == 0

    def test_frame_preto_nao_vira_wipe_total(self, calibracao):
        """O pior bug possivel: buffer vazio lido como party inteira morta."""
        preto = np.zeros((520, 200, 3), dtype=np.uint8)
        frame = Frame(
            pixels=preto, indice=0, saude=SaudeDoFrame.FALHA_DE_CAPTURA
        )

        obs = extrair(frame, calibracao)
        assert not any(l.hp_zerado for l in obs.linhas)


class TestMedicaoDeBarra:
    """A medicao em si, com barras sinteticas de fracao conhecida."""

    def _barra(self, fracao: float, cor_bgr: tuple[int, int, int]) -> np.ndarray:
        """Barra de 120x8 sobre 'terreno' dessaturado, como no jogo real."""
        # o vazio da barra e transparente e mostra o cenario — nunca preto
        terreno = np.full((8, 120, 3), (90, 110, 130), dtype=np.uint8)
        preenchido = int(120 * fracao)
        if preenchido:
            terreno[:, :preenchido] = cor_bgr
        return terreno

    VERMELHO = (30, 30, 200)
    AZUL = (200, 90, 30)

    @pytest.mark.parametrize("fracao", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_mede_fracoes_conhecidas(self, fracao):
        pixels = self._barra(fracao, self.VERMELHO)
        regiao = Regiao(0, 0, 120, 8)

        medido = medir_barra(pixels, regiao, LIMIARES_HP_PADRAO)
        assert medido == pytest.approx(fracao, abs=0.02)

    def test_barra_vazia_le_zero(self):
        """0% e o evento mais importante do projeto — nao pode falhar."""
        pixels = self._barra(0.0, self.VERMELHO)
        assert medir_barra(pixels, Regiao(0, 0, 120, 8), LIMIARES_HP_PADRAO) == 0.0

    def test_terreno_avermelhado_nao_vira_barra_cheia(self):
        """Cenario de lava/deserto: chao com matiz vermelho, mas dessaturado.

        Se o leitor olhasse so o matiz, um chao avermelhado seria lido como
        barra cheia e uma morte real passaria despercebida. A saturacao e o
        discriminador que impede isso.
        """
        # matiz vermelho, mas saturacao baixa como terreno de verdade
        terreno_vermelhado = np.full((8, 120, 3), (80, 85, 130), dtype=np.uint8)

        medido = medir_barra(
            terreno_vermelhado, Regiao(0, 0, 120, 8), LIMIARES_HP_PADRAO
        )
        assert medido == 0.0

    def test_apenas_corrida_inicial_conta(self):
        """Um efeito vermelho do jogo passando por cima da barra nao infla.

        A barra esvazia da direita para a esquerda, entao so preenchimento
        continuo desde a borda esquerda e real. Manchas soltas mais adiante
        sao ruido visual, nao vida.
        """
        pixels = self._barra(0.3, self.VERMELHO)
        pixels[:, 90:110] = self.VERMELHO  # mancha solta depois de um vao

        medido = medir_barra(pixels, Regiao(0, 0, 120, 8), LIMIARES_HP_PADRAO)
        assert medido == pytest.approx(0.3, abs=0.02)

    def test_matiz_azul_nao_dispara_no_limiar_vermelho(self):
        pixels = self._barra(1.0, self.AZUL)
        assert medir_barra(pixels, Regiao(0, 0, 120, 8), LIMIARES_HP_PADRAO) == 0.0

    def test_matiz_vermelho_nao_dispara_no_limiar_azul(self):
        pixels = self._barra(1.0, self.VERMELHO)
        assert medir_barra(pixels, Regiao(0, 0, 120, 8), LIMIARES_MP_PADRAO) == 0.0


class TestVoltaDoMatizVermelho:
    """O vermelho da a volta no circulo de matiz: precisa de DUAS faixas.

    Uma faixa so e a razao classica de um leitor de vida 'as vezes ler 0%' —
    que aqui viraria um alerta falso de morte.
    """

    @pytest.mark.parametrize("matiz", [0, 3, 5, 8, 12, 170, 175, 179])
    def test_ambos_os_lados_da_volta_contam_como_cheio(self, matiz):
        hsv = np.full((8, 120, 3), (matiz, 210, 150), dtype=np.uint8)
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        medido = medir_barra(bgr, Regiao(0, 0, 120, 8), LIMIARES_HP_PADRAO)
        assert medido == pytest.approx(1.0, abs=0.02), (
            f"matiz {matiz} deveria contar como vermelho de barra cheia"
        )

    @pytest.mark.parametrize("matiz", [30, 60, 90, 120, 150])
    def test_matizes_fora_da_faixa_nao_contam(self, matiz):
        hsv = np.full((8, 120, 3), (matiz, 210, 150), dtype=np.uint8)
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

        assert medir_barra(bgr, Regiao(0, 0, 120, 8), LIMIARES_HP_PADRAO) == 0.0


class TestSemBuracoNaLista:
    """A party window nunca tem vao: membros ocupam as linhas de cima pra baixo.

    Isto importa porque a regiao capturada e mais alta que a janela de proposito
    (para caber uma party cheia), e o excedente cai em cima do chat e do
    minimapa — que tem contraste alto e poderiam passar por icone de classe.
    """

    def _frame_com_icone_falso_no_fim(self, calibracao) -> Frame:
        """Simula o chat disparando o detector de icone numa linha distante."""
        pixels = np.full((520, 200, 3), (110, 120, 100), dtype=np.uint8)
        lay = calibracao.layout

        def pintar_icone(indice: int) -> None:
            dy = indice * lay.passo
            y, x = lay.icone_y + dy, lay.icone_x
            # quadrado escuro com miolo claro: exatamente o que o detector busca
            pixels[y : y + lay.icone_tamanho, x : x + lay.icone_tamanho] = (20, 20, 20)
            pixels[y + 6 : y + 18, x + 6 : x + 18] = (240, 240, 240)

        pintar_icone(0)
        pintar_icone(1)
        # vao nas linhas 2 e 3, e um "icone" falso na 4 (chat colorido)
        pintar_icone(4)

        return Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK)

    def test_linha_apos_o_vao_e_descartada(self, calibracao):
        frame = self._frame_com_icone_falso_no_fim(calibracao)
        obs = extrair(frame, calibracao)

        assert obs.linhas[0].estado is EstadoDaLinha.COM_MEMBRO
        assert obs.linhas[1].estado is EstadoDaLinha.COM_MEMBRO
        assert obs.linhas[2].estado is EstadoDaLinha.VAZIA
        assert obs.linhas[4].estado is EstadoDaLinha.VAZIA, (
            "um icone falso depois de um vao viraria membro fantasma, e a "
            "'saida' dele viraria alerta de um evento que nunca aconteceu"
        )

    def test_membro_fantasma_nao_entra_na_contagem(self, calibracao):
        frame = self._frame_com_icone_falso_no_fim(calibracao)
        obs = extrair(frame, calibracao)
        assert obs.membros_presentes == 2

    def test_party_contigua_nao_e_afetada(self, frame_real, calibracao):
        """A regra nao pode cortar uma party legitima."""
        obs = extrair(frame_real, calibracao)
        assert obs.membros_presentes == 4
