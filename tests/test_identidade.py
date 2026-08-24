"""Testes da identidade por imagem do nome.

O que estes testes protegem: sem identidade visual, o nome do membro vem da
POSICAO da linha. A party window compacta as linhas quando alguem sai, entao a
posicao nao e uma identidade — e so um lugar. O resultado seria "Korzis morreu"
quando quem morreu foi o Kaus, e a party socorreria a pessoa errada sem
desconfiar, porque a mensagem parece perfeitamente normal.

A fixture e um frame REAL da party do usuario, com as assinaturas gravadas pela
calibracao contra a mesma tela.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.identidade import (
    LIMIAR_DE_CASAMENTO,
    Assinatura,
    criar_assinatura,
    identificar,
    mascara_de_texto,
)
from l2scanner.visao import EstadoDaLinha, extrair

FIXTURES = Path(__file__).parent / "fixtures" / "identidade"


@pytest.fixture
def calibracao() -> Calibracao:
    return Calibracao.carregar(FIXTURES / "calibracao.json")


@pytest.fixture
def pixels() -> np.ndarray:
    px = cv2.imread(str(FIXTURES / "party_ordem_original.png"), cv2.IMREAD_COLOR)
    assert px is not None, "fixture da party nao pode ser lida"
    return px


def remontar(px: np.ndarray, cal: Calibracao, ordem: list[int]) -> np.ndarray:
    """Reordena as linhas da party window, simulando a party reorganizada."""
    lay = cal.layout
    novo = px.copy()

    def topo_de(i: int) -> int:
        return lay.icone_y + i * lay.passo + lay.nome_dy - 4

    blocos = [px[topo_de(i) : topo_de(i) + lay.passo].copy() for i in range(4)]
    for destino, origem in enumerate(ordem):
        inicio = topo_de(destino)
        novo[inicio : inicio + lay.passo] = blocos[origem]
    return novo


class TestMascaraDeTexto:
    """O texto e claro e dessaturado; o cenario e colorido."""

    def test_texto_branco_e_marcado(self):
        branco = np.full((10, 10, 3), 240, dtype=np.uint8)
        assert mascara_de_texto(branco).all()

    def test_terreno_colorido_nao_e_marcado(self):
        # verde de grama: claro o bastante, mas saturado
        grama = np.full((10, 10, 3), (60, 130, 70), dtype=np.uint8)
        assert not mascara_de_texto(grama).any()

    def test_sombra_escura_nao_e_marcada(self):
        escuro = np.full((10, 10, 3), 40, dtype=np.uint8)
        assert not mascara_de_texto(escuro).any()

    def test_recorte_vazio_nao_quebra(self):
        vazio = np.zeros((0, 0, 3), dtype=np.uint8)
        assert mascara_de_texto(vazio).size == 0


class TestAssinatura:
    def test_ida_e_volta_pela_serializacao(self):
        gerador = np.random.default_rng(3)
        recorte = gerador.integers(0, 255, (20, 100, 3), dtype=np.uint8)
        original = criar_assinatura("TioMad", recorte)

        voltou = Assinatura.de_dict(original.como_dict())

        assert voltou.nome == "TioMad"
        assert voltou.mascara.shape == original.mascara.shape
        assert np.array_equal(voltou.mascara, original.mascara)

    def test_assinatura_de_verdade_tem_texto(self, pixels, calibracao):
        regiao = calibracao.regiao_do_nome(0)
        recorte = pixels[
            regiao.topo : regiao.topo + regiao.altura,
            regiao.esquerda : regiao.esquerda + regiao.largura,
        ]
        assert criar_assinatura("J4guar", recorte).pixels_de_texto > 12


class TestIdentificacao:
    def test_reconhece_cada_membro_no_frame_real(self, pixels, calibracao):
        obs = extrair(
            Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK), calibracao
        )
        reconhecidos = [l.nome for l in obs.linhas[:4]]
        assert reconhecidos == calibracao.nomes

    def test_confianca_alta_nos_acertos(self, pixels, calibracao):
        obs = extrair(
            Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK), calibracao
        )
        for linha in obs.linhas[:4]:
            assert linha.confianca_do_nome > LIMIAR_DE_CASAMENTO

    def test_sem_assinaturas_nao_reconhece_e_nao_quebra(self, pixels, calibracao):
        """Calibracao antiga, sem assinaturas: degrada para o nome por ordem."""
        calibracao.assinaturas = []
        obs = extrair(
            Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK), calibracao
        )
        assert all(l.nome is None for l in obs.linhas)
        assert obs.membros_presentes == 4  # o resto continua funcionando

    def test_recorte_sem_texto_nao_e_identificado(self, calibracao):
        """Linha vazia nao pode ser atribuida a ninguem."""
        terreno = np.full((20, 100, 3), (60, 130, 70), dtype=np.uint8)
        casamento = identificar(terreno, calibracao.assinaturas)
        assert casamento.nome is None

    def test_nome_desconhecido_nao_e_chutado(self, calibracao):
        """Um membro novo, sem assinatura gravada, nao pode virar outro.

        Chutar seria pior do que nao saber: o alerta sairia com o nome de quem
        nao morreu.
        """
        # texto sintetico que nao corresponde a nenhuma assinatura
        estranho = np.zeros((20, 100, 3), dtype=np.uint8)
        estranho[4:16, 5:95] = 255  # bloco solido, nada parecido com um nome

        casamento = identificar(estranho, calibracao.assinaturas)
        assert casamento.nome is None


class TestOrdemDaParty:
    """O motivo de tudo isto existir."""

    @pytest.mark.parametrize(
        "descricao,ordem",
        [
            ("ordem original", [0, 1, 2, 3]),
            ("dois membros trocados", [0, 3, 2, 1]),
            ("ordem invertida", [3, 2, 1, 0]),
            ("primeiro saiu, os outros sobem", [1, 2, 3, 3]),
        ],
    )
    def test_o_nome_segue_o_membro_e_nao_a_linha(
        self, pixels, calibracao, descricao, ordem
    ):
        reordenado = remontar(pixels, calibracao, ordem)
        obs = extrair(
            Frame(pixels=reordenado, indice=0, saude=SaudeDoFrame.OK), calibracao
        )

        reconhecidos = [l.nome for l in obs.linhas[:4]]
        esperados = [calibracao.nomes[i] for i in ordem]

        assert reconhecidos == esperados, (
            f"{descricao}: o nome ficou preso a posicao da linha em vez de "
            f"seguir o membro — foi exatamente isto que a identidade visual "
            f"veio resolver"
        )

    def test_sem_identidade_visual_a_ordem_engana(self, pixels, calibracao):
        """Prova que o problema era real, e nao teorico.

        Com as assinaturas removidas, o nome volta a vir da posicao — e uma
        party reordenada produz atribuicao errada.
        """
        reordenado = remontar(pixels, calibracao, [3, 2, 1, 0])
        calibracao.assinaturas = []

        obs = extrair(
            Frame(pixels=reordenado, indice=0, saude=SaudeDoFrame.OK), calibracao
        )

        # sem assinatura nenhuma linha e identificada, e quem chama cairia no
        # nome por posicao — que aqui esta invertido em relacao a realidade
        assert all(l.nome is None for l in obs.linhas)
        nomes_por_posicao = [calibracao.nome_da_linha(i) for i in range(4)]
        nomes_reais = [calibracao.nomes[i] for i in [3, 2, 1, 0]]
        assert nomes_por_posicao != nomes_reais


class TestRastreadorUsaONomeReconhecido:
    def test_evento_leva_o_nome_reconhecido_e_nao_o_da_posicao(self):
        from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento
        from l2scanner.visao import LeituraDeLinha, Observacao

        def obs(hp_linha0: float, nome_linha0: str) -> Observacao:
            return Observacao(
                indice_do_frame=0,
                ui_visivel=True,
                linhas=(
                    LeituraDeLinha(
                        indice=0,
                        estado=EstadoDaLinha.COM_MEMBRO,
                        hp=hp_linha0,
                        mp=1.0,
                        nome=nome_linha0,
                        confianca_do_nome=0.98,
                    ),
                ),
            )

        # a lista diz que a linha 0 e do J4guar, mas a imagem diz que e o Korzis
        rastreador = Rastreador(
            nomes=["J4guar"], ajustes=Ajustes(confirmacoes_para_morte=2)
        )
        for i in range(15):
            rastreador.observar(obs(1.0, "Korzis"), -100 + i)

        eventos = []
        for i in range(3):
            eventos.extend(rastreador.observar(obs(0.0, "Korzis"), 10 + i))

        mortes = [e for e in eventos if e.tipo is TipoDeEvento.MORREU]
        assert len(mortes) == 1
        assert mortes[0].membro == "Korzis", (
            "o alerta precisa nomear quem a IMAGEM identificou, nao quem a "
            "lista diz que ocupa aquela posicao"
        )
