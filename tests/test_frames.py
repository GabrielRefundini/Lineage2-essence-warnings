"""Testes da classificacao de saude de frame — sem jogo, sem tela, sem rede.

Cada teste aqui corresponde a um jeito concreto do scanner mentir para a party.
"""

from __future__ import annotations

import numpy as np
import pytest

from l2scanner.calibracao import Calibracao, CalibracaoInvalida
from l2scanner.frames import (
    FRAMES_IDENTICOS_PARA_CONGELADO,
    Regiao,
    SaudeDoFrame,
    _ClassificadorDeSaude,
)


def frame_preto(altura: int = 50, largura: int = 50) -> np.ndarray:
    return np.zeros((altura, largura, 3), dtype=np.uint8)


def frame_com_conteudo(semente: int = 0) -> np.ndarray:
    gerador = np.random.default_rng(semente)
    return gerador.integers(60, 200, size=(50, 50, 3), dtype=np.uint8)


class TestFramePreto:
    """CAPT-04: frame preto e falha de captura, nunca 'todo mundo com HP zero'.

    Este e o caminho para o pior bug possivel: um buffer vazio lido como quatro
    barras vazias dispara um alerta de wipe total que nunca aconteceu.
    """

    def test_frame_preto_e_falha_de_captura(self):
        classificador = _ClassificadorDeSaude()
        assert (
            classificador.classificar(frame_preto()) is SaudeDoFrame.FALHA_DE_CAPTURA
        )

    def test_frame_vazio_e_falha_de_captura(self):
        classificador = _ClassificadorDeSaude()
        vazio = np.zeros((0, 0, 3), dtype=np.uint8)
        assert classificador.classificar(vazio) is SaudeDoFrame.FALHA_DE_CAPTURA

    def test_frame_quase_preto_ainda_e_falha(self):
        classificador = _ClassificadorDeSaude()
        escuro = np.full((50, 50, 3), 3, dtype=np.uint8)
        assert classificador.classificar(escuro) is SaudeDoFrame.FALHA_DE_CAPTURA

    def test_frame_com_conteudo_passa(self):
        classificador = _ClassificadorDeSaude()
        assert classificador.classificar(frame_com_conteudo()) is SaudeDoFrame.OK


class TestTelaEstatica:
    """CAPT-05: tela parada nao pode virar 'perdi a visao'.

    Durante farm AFK a party window fica minutos sem mudar nada. Se isso fosse
    lido como perda de visao, o scanner passaria o farm inteiro sem alertar.
    Mas frames BYTE-IDENTICOS por muito tempo significam jogo travado — e ai
    o alerta de congelado e legitimo.
    """

    def test_frames_identicos_por_pouco_tempo_seguem_ok(self):
        classificador = _ClassificadorDeSaude()
        parado = frame_com_conteudo()

        for _ in range(FRAMES_IDENTICOS_PARA_CONGELADO - 1):
            assert classificador.classificar(parado) is SaudeDoFrame.OK

    def test_frames_identicos_demais_viram_congelado(self):
        classificador = _ClassificadorDeSaude()
        parado = frame_com_conteudo()

        for _ in range(FRAMES_IDENTICOS_PARA_CONGELADO + 1):
            resultado = classificador.classificar(parado)

        assert resultado is SaudeDoFrame.CONGELADO

    def test_qualquer_mudanca_zera_o_contador(self):
        classificador = _ClassificadorDeSaude()
        parado = frame_com_conteudo(semente=1)

        for _ in range(FRAMES_IDENTICOS_PARA_CONGELADO - 1):
            classificador.classificar(parado)

        # um unico frame diferente reabilita o relogio
        classificador.classificar(frame_com_conteudo(semente=2))

        assert classificador.classificar(parado) is SaudeDoFrame.OK


class TestRegiao:
    """Monitor secundario a esquerda do principal tem coordenada NEGATIVA."""

    def test_coordenada_negativa_sobrevive_ao_ciclo_de_serializacao(self):
        original = Regiao(esquerda=-1920, topo=-200, largura=400, altura=300)
        voltou = Regiao.de_dict(original.como_dict())
        assert voltou == original
        assert voltou.esquerda == -1920

    def test_traducao_para_mss(self):
        regiao = Regiao(esquerda=1713, topo=330, largura=450, altura=300)
        assert regiao.como_dict_mss() == {
            "left": 1713,
            "top": 330,
            "width": 450,
            "height": 300,
        }


class TestCalibracao:
    """CAPT-07: recusar iniciar se a tela mudou desde a calibracao."""

    def _calibracao(self, geometria: str) -> Calibracao:
        return Calibracao(
            party_window=Regiao(0, 0, 100, 100),
            ancora=Regiao(0, 0, 100, 8),
            geometria_da_tela=geometria,
        )

    def test_mesma_geometria_passa(self):
        cal = self._calibracao("1920x1080+0+0")
        cal.conferir_geometria("1920x1080+0+0")  # nao levanta

    def test_geometria_diferente_recusa(self):
        cal = self._calibracao("1920x1080+0+0")
        with pytest.raises(CalibracaoInvalida, match="mudou"):
            cal.conferir_geometria("2560x1440+0+0")

    def test_monitor_removido_recusa(self):
        cal = self._calibracao("1920x1080+0+0;1718x1360+1713+0")
        with pytest.raises(CalibracaoInvalida):
            cal.conferir_geometria("1920x1080+0+0")

    def test_ida_e_volta_em_disco(self, tmp_path):
        original = Calibracao(
            party_window=Regiao(1713, 330, 450, 300),
            ancora=Regiao(0, 0, 450, 8),
            geometria_da_tela="1920x1080+0+0",
            hp_proprio=Regiao(1750, 40, 200, 20),
        )
        caminho = tmp_path / "calibration.json"
        original.salvar(caminho)

        voltou = Calibracao.carregar(caminho)
        assert voltou.party_window == original.party_window
        assert voltou.ancora == original.ancora
        assert voltou.hp_proprio == original.hp_proprio

    def test_versao_incompativel_recusa(self, tmp_path):
        caminho = tmp_path / "calibration.json"
        caminho.write_text('{"versao": 99}', encoding="utf-8")

        with pytest.raises(CalibracaoInvalida, match="v99"):
            Calibracao.carregar(caminho)

    def test_arquivo_ausente_recusa_com_instrucao(self, tmp_path):
        with pytest.raises(CalibracaoInvalida, match="calibra"):
            Calibracao.carregar(tmp_path / "nao_existe.json")


class TestInvarianteDeSeguranca:
    """SAFE-02: nenhuma lib de input pode entrar na arvore de dependencias."""

    def test_nenhuma_biblioteca_de_input_declarada(self):
        from pathlib import Path

        raiz = Path(__file__).resolve().parent.parent
        requisitos = (raiz / "requirements.txt").read_text(encoding="utf-8")

        # so as linhas que declaram dependencia, nao os comentarios que
        # justamente explicam por que estas libs estao proibidas
        declaradas = [
            linha.strip().lower()
            for linha in requisitos.splitlines()
            if linha.strip() and not linha.strip().startswith("#")
        ]

        proibidas = ("pyautogui", "pydirectinput", "keyboard", "pynput", "autoit")
        for linha in declaradas:
            for proibida in proibidas:
                assert proibida not in linha, (
                    f"'{proibida}' apareceu em requirements.txt. "
                    f"O scanner e somente leitura — ver l2scanner/__init__.py."
                )
