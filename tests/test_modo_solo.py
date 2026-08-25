"""Upando SOLO, a sua morte tem que ser detectada.

E quem upa solo e exatamente quem mais precisa: em party alguem nota que voce
caiu; sozinho, ninguem nota.

MEDIDO ANTES DA CORRECAO: 30 frames com o HP proprio em ZERO produziam ZERO
eventos, e o estado ficava DESCONHECIDO para sempre. O portao de cegueira fala
da PARTY WINDOW, e deixa-lo bloquear a avaliacao da propria barra confundia
"nao vejo a party" com "nao vejo voce".
"""

from __future__ import annotations


from l2scanner.rastreador import Ajustes, EstadoDoMembro, Rastreador, TipoDeEvento
from l2scanner.visao import Observacao


def solo(hp: float | None) -> Observacao:
    """Sem party window na tela; a SUA barra continua sendo lida."""
    return Observacao(0, False, (), hp_proprio=hp)


def novo() -> Rastreador:
    return Rastreador(nomes=["Kaus"], nome_proprio="Yazalaque", ajustes=Ajustes())


def alimentar(r, obs, vezes, inicio=0.0):
    eventos = []
    for i in range(vezes):
        eventos.extend(r.observar(obs, inicio + i))
    return eventos


class TestMorteSolo:
    def test_sua_morte_e_detectada_sem_party_nenhuma(self):
        r = novo()
        alimentar(r, solo(1.0), 20)
        eventos = alimentar(r, solo(0.0), 10, 100)

        mortes = [e for e in eventos if e.tipo is TipoDeEvento.MORREU]
        assert [e.membro for e in mortes] == ["Yazalaque"]

    def test_sua_ressurreicao_tambem(self):
        r = novo()
        alimentar(r, solo(1.0), 20)
        alimentar(r, solo(0.0), 10, 100)
        eventos = alimentar(r, solo(0.8), 10, 200)

        voltas = [e for e in eventos if e.tipo is TipoDeEvento.RESSUSCITOU]
        assert [e.membro for e in voltas] == ["Yazalaque"]
        assert voltas[0].segundos_no_estado is not None

    def test_avisa_uma_vez_so(self):
        """Morrer e ficar morto meia hora nao vira meia hora de mensagens."""
        r = novo()
        alimentar(r, solo(1.0), 20)
        eventos = alimentar(r, solo(0.0), 300, 100)
        assert len([e for e in eventos if e.tipo is TipoDeEvento.MORREU]) == 1

    def test_o_mesmo_debounce_dos_outros_membros(self):
        """Nao ha motivo para a SUA morte ser julgada com criterio diferente."""
        r = Rastreador(
            nome_proprio="Yazalaque", ajustes=Ajustes(confirmacoes_para_morte=3)
        )
        alimentar(r, solo(1.0), 20)

        # duas leituras zeradas nao bastam
        assert alimentar(r, solo(0.0), 2, 100) == []
        # a terceira fecha
        eventos = alimentar(r, solo(0.0), 1, 200)
        assert [e.tipo for e in eventos] == [TipoDeEvento.MORREU]

    def test_piscada_de_hp_nao_vira_morte(self):
        r = novo()
        alimentar(r, solo(1.0), 20)
        eventos = alimentar(r, solo(0.0), 1, 100)
        eventos += alimentar(r, solo(0.9), 5, 200)
        assert eventos == []


class TestBarraIlegivelNaoVIRAMorte:
    """A trava contra o bug que este projeto ja cometeu duas vezes.

    `medir_barra` devolve 0.0 tanto para "HP zerado" quanto para um recorte
    preto. Um modo solo ingenuo anunciaria "voce morreu" toda vez que a captura
    falhasse — e o usuario estaria vivo, provavelmente AFK, sem ninguem para
    desmentir.
    """

    def test_hp_proprio_None_nao_produz_evento_nenhum(self):
        r = novo()
        alimentar(r, solo(1.0), 20)
        eventos = alimentar(r, solo(None), 60, 100)
        assert eventos == []

    def test_barra_ilegivel_CONGELA_em_vez_de_concluir(self):
        """Depois da captura voltar, o estado tem que ser o de antes."""
        r = novo()
        alimentar(r, solo(1.0), 20)
        assert r.estado_de_membro("@Yazalaque") is EstadoDoMembro.VIVO

        alimentar(r, solo(None), 60, 100)
        assert r.estado_de_membro("@Yazalaque") is EstadoDoMembro.VIVO

    def test_a_visao_devolve_None_para_recorte_degenerado(self):
        """A garantia vem daqui: a `visao` nunca entrega 0.0 de lixo."""
        import numpy as np

        from l2scanner.visao import barra_propria_legivel

        assert not barra_propria_legivel(np.zeros((8, 120, 3), dtype=np.uint8))
        assert not barra_propria_legivel(np.full((8, 120, 3), 60, dtype=np.uint8))
        assert not barra_propria_legivel(None)

    def test_a_barra_real_do_usuario_e_legivel(self):
        """Medido: desvio 38,6 contra 0,00 do lixo. Margem enorme."""
        import glob

        import cv2

        from l2scanner.visao import barra_propria_legivel

        recortes = glob.glob("tests/fixtures/**/*hp_proprio*.png", recursive=True)
        assert recortes, "sem fixture da barra propria"
        for caminho in recortes:
            assert barra_propria_legivel(cv2.imread(caminho)), caminho

    def test_o_discriminador_e_contraste_e_nao_saturacao(self):
        """Saturacao seria tentador e ERRADO.

        A parte VAZIA da barra e transparente e mostra o terreno, entao uma
        barra quase vazia tem saturacao baixa. Usar saturacao faria o scanner
        declarar "nao consigo ler" exatamente no frame em que voce morre.
        """
        import numpy as np

        from l2scanner.visao import barra_propria_legivel

        # cinza texturizado: contraste alto, saturacao ZERO
        gerador = np.random.default_rng(7)
        texturizado = np.repeat(
            gerador.integers(0, 255, (8, 120, 1), dtype=np.uint8), 3, axis=2
        )
        assert barra_propria_legivel(texturizado), (
            "rejeitou um recorte com estrutura so porque nao tem cor"
        )


class TestOCasoQueMotivouTudo:
    def test_antes_da_correcao_isto_produzia_zero_eventos(self):
        """Reproduz a medicao que motivou o modo solo.

        Este e o teste que teria pego o problema no dia em que o usuario
        decidisse upar sozinho.
        """
        r = novo()
        alimentar(r, solo(1.0), 20)
        eventos = alimentar(r, solo(0.0), 30, 100)
        assert eventos, "solo, com HP zerado, o scanner voltou a ficar mudo"


class TestCalibracaoVelhaNaoViraAlarmeDeMorte:
    """O alarme falso de 2026-08-24 23:27.

    O usuario mudou a barra de HP de lugar na UI do jogo. A regiao calibrada
    passou a apontar para GRAMA, `medir_barra` leu 0%, e o scanner anunciou
    "Yazalaque MORTO" com ele vivo e com 3537/3537 de HP na tela.

    NENHUMA HEURISTICA DE PIXEL RESOLVE ISSO. A parte vazia da barra e
    transparente e mostra o terreno, entao "barra vazia" e "grama" sao
    literalmente a mesma imagem. Medido: a razao entre variacao vertical e
    horizontal deu 1.10 na barra real e 0.71 na grama — perto demais para
    separar.

    O que separa nao e o pixel, e a HISTORIA: uma calibracao boa mostra a barra
    com vida em algum momento; uma velha nunca mostra.
    """

    def test_regiao_que_NUNCA_teve_vida_nao_gera_morte(self):
        r = novo()
        eventos = alimentar(r, solo(0.0), 200)
        assert eventos == [], "inventou uma morte a partir de calibracao velha"

    def test_depois_de_ver_vida_a_morte_volta_a_ser_detectada(self):
        r = novo()
        alimentar(r, solo(1.0), 20)
        eventos = alimentar(r, solo(0.0), 10, inicio=100)
        assert [e.tipo for e in eventos] == [TipoDeEvento.MORREU]

    def test_um_unico_frame_com_vida_ja_valida_a_calibracao(self):
        """Nao precisa de muito: se a regiao mostrou a barra uma vez, ela e a
        barra."""
        r = novo()
        alimentar(r, solo(0.5), 1)
        alimentar(r, solo(1.0), 20, inicio=10)
        eventos = alimentar(r, solo(0.0), 10, inicio=100)
        assert any(e.tipo is TipoDeEvento.MORREU for e in eventos)

    def test_ligar_o_scanner_ja_morto_tambem_cala(self):
        """Aceito de proposito: se ele ja esta morto quando o scanner sobe, ele
        sabe. Melhor perder esse aviso do que anunciar a morte de quem esta
        vivo."""
        r = novo()
        assert alimentar(r, solo(0.0), 50) == []
