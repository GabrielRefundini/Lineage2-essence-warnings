"""O tick, agora testavel — e os tres bugs de producao como regressao.

Este arquivo existe por causa de uma medicao: `__main__.py` estava em 20% de
cobertura contra 98% do `rastreador`, e TODOS os bugs de integracao deste
projeto moraram la. Tres chegaram em producao no mesmo dia, e nenhum dos 420
testes os viu — porque nenhum teste chamava o laco.

Agora chama.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.agenda import EventoAgendado, RegistroEmDisco
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.notificador import Categoria
from l2scanner.rastreador import Rastreador
from l2scanner.sessao import Sessao

SEGUNDA = datetime(2026, 8, 24)
FIXTURES = Path(__file__).parent / "fixtures" / "party_estavel_com_vazamento"


class SilencioFalso:
    """Controla quando a janela abre e fecha, sem depender do relogio."""

    def __init__(self, encerra_em=None):
        self.janela = None
        self._encerra_em = encerra_em

    def ativo(self):
        return self.janela is not None

    def atualizar(self, agora):
        if self._encerra_em and agora >= self._encerra_em:
            self._encerra_em = None
            return "TvT encerrado. Voltei a vigiar."
        return None


@pytest.fixture
def calibracao():
    return Calibracao.carregar(FIXTURES / "calibracao.json")


@pytest.fixture
def frame_real():
    return Frame(
        pixels=cv2.imread(str(FIXTURES / "limpo.png")),
        indice=0,
        saude=SaudeDoFrame.OK,
    )


def nova_sessao(calibracao, tmp_path, eventos=(), silencio=None, despachante=None):
    return Sessao(
        cal=calibracao,
        rastreador=Rastreador(nomes=list(calibracao.nomes)),
        eventos_agendados=list(eventos),
        registro=RegistroEmDisco(tmp_path),
        silencio=silencio or SilencioFalso(),
        despachante=despachante,
    )


def em(hora, minuto):
    return SEGUNDA.replace(hour=hora, minute=minuto).timestamp()


class TestTickBasico:
    def test_um_frame_real_produz_observacao(self, calibracao, frame_real, tmp_path):
        s = nova_sessao(calibracao, tmp_path)
        r = s.tick(frame_real, momento=em(12, 0))
        assert r.observacao is not None
        assert not r.falhou_ao_analisar

    def test_frame_degenerado_vira_CEGUEIRA_e_nao_excecao(
        self, calibracao, tmp_path
    ):
        """Um frame de 1x1 preto nao lanca — e nao deveria mesmo.

        A `visao` trata e devolve `ui_visivel=False`, que e o comportamento
        certo: frame doente vira cegueira, nunca "todas as barras vazias", que
        seria um alerta de wipe total que nunca aconteceu.
        """
        s = nova_sessao(calibracao, tmp_path)
        ruim = Frame(
            pixels=np.zeros((1, 1, 3), np.uint8), indice=0, saude=SaudeDoFrame.OK
        )

        r = s.tick(ruim, momento=em(12, 0))

        assert not r.falhou_ao_analisar
        assert r.observacao is not None and not r.observacao.ui_visivel
        assert r.eventos == [], "frame degenerado nao pode gerar evento"

    def test_excecao_na_analise_e_reportada_sem_derrubar(
        self, calibracao, frame_real, tmp_path
    ):
        """Quando a analise REALMENTE explode, o tick reporta e segue.

        Um scanner que morre calado e pior do que nenhum scanner.
        """
        s = nova_sessao(calibracao, tmp_path)

        class RastreadorExplosivo:
            portao = None

            def observar(self, *_):
                raise RuntimeError("boom")

        s.rastreador = RastreadorExplosivo()

        r = s.tick(frame_real, momento=em(12, 0))

        assert r.falhou_ao_analisar
        assert r.eventos == []

    def test_a_saude_do_frame_e_contabilizada(self, calibracao, frame_real, tmp_path):
        s = nova_sessao(calibracao, tmp_path)
        s.tick(frame_real, momento=em(12, 0))
        assert s.contagem[SaudeDoFrame.OK] == 1

    def test_ticks_cego_conta(self, calibracao, tmp_path):
        s = nova_sessao(calibracao, tmp_path)
        cego = Frame(
            pixels=np.zeros((200, 200, 3), np.uint8),
            indice=0,
            saude=SaudeDoFrame.FALHA_DE_CAPTURA,
        )
        for _ in range(3):
            s.tick(cego, momento=em(12, 0))
        assert s.ticks_cego == 3


class TestBug1DestacarComUmArgumento:
    """`destacar(texto)` numa funcao de tres parametros.

    O scanner morreria no instante em que fosse falar sobre um TvT. E o
    marcador "ja avisei" e gravado ANTES do destacar, entao o aviso sumiria em
    silencio: nem sairia, nem seria reenviado.

    Um tick que dispara aviso de agenda pega isso.
    """

    def test_um_aviso_de_agenda_nao_derruba_o_tick(
        self, calibracao, frame_real, tmp_path
    ):
        tvt = EventoAgendado(nome="TvT", horarios=((15, 0),), avisar_minutos_antes=10)
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])

        r = s.tick(frame_real, momento=em(14, 50))

        assert r.avisos, "o aviso das 14:50 nao saiu"
        assert "TvT" in r.avisos[0]

    def test_o_aviso_sai_com_categoria_SEMPRE(self, calibracao, frame_real, tmp_path):
        """Se sair como NORMAL, o silencio engole o lembrete."""
        tvt = EventoAgendado(nome="TvT", horarios=((15, 0),), avisar_minutos_antes=10)
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])

        r = s.tick(frame_real, momento=em(14, 50))

        assert Categoria.SEMPRE in [c for _, c, _ in r.despachos]


class TestBug2DoisRelogios:
    """Um parametro `agora` usado para dois relogios incompativeis.

    `TypeError` no SEGUNDO tick — o primeiro passava porque a comparacao nem
    acontecia. Um teste de uma chamada so nao pegaria.
    """

    def test_muitos_ticks_seguidos_com_os_tipos_reais(
        self, calibracao, frame_real, tmp_path
    ):
        tvt = EventoAgendado(nome="TvT", horarios=((15, 0),))
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])

        base = em(14, 48)
        for i in range(30):  # trinta ticks, nao um
            s.tick(frame_real, momento=base + i)

    def test_o_aviso_sai_uma_vez_so_em_muitos_ticks(
        self, calibracao, frame_real, tmp_path
    ):
        """O marcador duravel tem que valer entre ticks."""
        tvt = EventoAgendado(nome="TvT", horarios=((15, 0),), avisar_minutos_antes=10)
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])

        avisos = []
        for i in range(60):
            avisos.extend(s.tick(frame_real, momento=em(14, 50) + i).avisos)

        antes = [a for a in avisos if "10 minutos" in a]
        assert len(antes) == 1, f"o aviso saiu {len(antes)} vezes"


class TestBug3DestinoDoDespacho:
    """Toda saida passa por um ponto so, e o resultado diz ONDE foi.

    Com o despacho espalhado por cinco lugares do laco, cada um podia errar o
    destino sozinho — e um errou: o `.status` respondia no grupo em vez de
    responder a quem perguntou.
    """

    def test_o_resultado_registra_o_destino_de_cada_despacho(
        self, calibracao, frame_real, tmp_path
    ):
        tvt = EventoAgendado(nome="TvT", horarios=((15, 0),), avisar_minutos_antes=10)
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])

        r = s.tick(frame_real, momento=em(14, 50))

        assert r.despachos
        for texto, categoria, alvo in r.despachos:
            assert isinstance(texto, str)
            assert isinstance(categoria, Categoria)
            assert alvo is None or isinstance(alvo, str)

    def test_aviso_de_agenda_vai_para_as_conversas_de_aviso(
        self, calibracao, frame_real, tmp_path
    ):
        """Alvo None = destinos de aviso. Um lembrete de TvT e para o grupo."""
        tvt = EventoAgendado(nome="TvT", horarios=((15, 0),), avisar_minutos_antes=10)
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])

        r = s.tick(frame_real, momento=em(14, 50))

        assert all(alvo is None for _, _, alvo in r.despachos)


class TestFimDoSilencio:
    def test_o_encerramento_sai_com_categoria_SEMPRE(
        self, calibracao, frame_real, tmp_path
    ):
        quando = SEGUNDA.replace(hour=15, minute=15)
        s = nova_sessao(
            calibracao, tmp_path, silencio=SilencioFalso(encerra_em=quando)
        )

        r = s.tick(frame_real, momento=quando.timestamp())

        assert r.avisos and "encerrado" in r.avisos[0]
        assert r.despachos[0][1] is Categoria.SEMPRE

    def test_encerra_uma_vez_so(self, calibracao, frame_real, tmp_path):
        quando = SEGUNDA.replace(hour=15, minute=15)
        s = nova_sessao(
            calibracao, tmp_path, silencio=SilencioFalso(encerra_em=quando)
        )

        avisos = []
        for i in range(10):
            avisos.extend(s.tick(frame_real, momento=quando.timestamp() + i).avisos)
        assert len([a for a in avisos if "encerrado" in a]) == 1
