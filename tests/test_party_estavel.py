"""Regressao do bug "a party estavel entra e sai em looping".

O SINTOMA: com 5 pessoas fixas na party, o scanner anunciou 52 eventos de
ENTROU/SAIU em 25 minutos. Nenhum deles aconteceu de verdade.

Os frames em fixtures/party_estavel_com_vazamento/ foram capturados ao vivo com
a party PARADA, e sao a unica entrada da suite que contem as condicoes reais que
quebravam o reconhecimento:

    limpo.png            mascara do nome com  93 px, Korzis casa a 0.976
    vazamento_leve.png   mascara com 184 px,        Korzis cai para 0.538
    vazamento_forte.png  mascara com 251 px,        Korzis cai para 0.433
    linha_fantasma.png   uma linha de chat passa no teste de icone

O teste que devia ter pego isto ja existia (`test_ninguem_aparece_duplicado`) e
tinha o oraculo certo. O que faltava era ENTRADA ADVERSARIAL: ele rodava contra
um frame limpo, onde a propriedade vale trivialmente.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.visao import EstadoDaLinha, extrair

FIXTURES = Path(__file__).parent / "fixtures" / "party_estavel_com_vazamento"

TODOS_OS_FRAMES = ("limpo", "vazamento_leve", "vazamento_forte", "linha_fantasma")


@pytest.fixture
def calibracao() -> Calibracao:
    return Calibracao.carregar(FIXTURES / "calibracao.json")


def carregar(rotulo: str) -> Frame:
    pixels = cv2.imread(str(FIXTURES / f"{rotulo}.png"), cv2.IMREAD_COLOR)
    assert pixels is not None, f"fixture {rotulo}.png nao pode ser lida"
    return Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK)


class TestLinhaFantasmaNaoCegaOScanner:
    """Correcao D.

    A regiao capturada e mais alta que a party window de proposito, para caber
    uma party cheia. O excedente cai sobre o chat e o minimapa.

    Uma linha de chat com contraste alto passava no teste do icone de classe.
    Ai `_bordas_da_barra_intactas` rodava sobre esse lixo, falhava, e executava
    `ui_visivel = False` para o FRAME INTEIRO. `_truncar_no_primeiro_vao`
    descartava a linha logo depois — tarde demais, a cegueira ja tinha
    acontecido e nada a desfazia.

    Custo real: cada frame assim levava o rastreador para CEGO e depois para
    REAQUISICAO, com 3 s de tolerancia em que nenhum estado avanca. O usuario
    via "[reajustando]" e todos os membros com "?".
    """

    def test_linha_de_chat_depois_do_vao_nao_derruba_a_visibilidade(self, calibracao):
        obs = extrair(carregar("linha_fantasma"), calibracao)
        assert obs.ui_visivel, (
            "uma linha DEPOIS do primeiro vao nao existe para a party window; "
            "deixa-la cegar o scanner troca 4 membros visiveis por 4 pontos de "
            "interrogacao"
        )

    def test_a_party_continua_com_quatro_membros(self, calibracao):
        obs = extrair(carregar("linha_fantasma"), calibracao)
        assert obs.membros_presentes == 4

    @pytest.mark.parametrize("rotulo", TODOS_OS_FRAMES)
    def test_nenhum_frame_da_party_parada_fica_cego(self, rotulo, calibracao):
        assert extrair(carregar(rotulo), calibracao).ui_visivel

    @pytest.mark.parametrize("rotulo", TODOS_OS_FRAMES)
    def test_nao_ha_vao_no_meio_da_lista(self, rotulo, calibracao):
        """A party window nunca tem buraco: ocupadas primeiro, vazias depois."""
        obs = extrair(carregar(rotulo), calibracao)
        estados = [l.estado is EstadoDaLinha.COM_MEMBRO for l in obs.linhas]
        assert estados == sorted(estados, reverse=True), (
            f"lista com vao no meio: {estados}"
        )
