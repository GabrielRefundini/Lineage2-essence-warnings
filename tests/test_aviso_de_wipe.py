"""Mortes simultaneas viram UM aviso, e nao uma rajada (CORR-03).

O defeito foi lido no celular do usuario, e nao inferido:

    [13:58] Membro 4: HP zerado - possivel morte na PT.
    [13:58] Membro 1: HP zerado - possivel morte na PT.
    [13:58] Membro 2: HP zerado - possivel morte na PT.
    [13:58] Membro 3: HP zerado - possivel morte na PT.
    [13:59] Membro 4: HP de volta apos 13s.
    [13:59] Membro 1: HP de volta apos 12s.

Quatro mensagens no mesmo segundo para UM evento: um wipe. O grupo de WhatsApp
e o ativo mais fragil do produto -- um grupo que recebe rajada aprende a
ignorar o grupo.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2
import pytest

from l2scanner.agenda import RegistroEmDisco
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.notificador import formatar, formatar_tick
from l2scanner.rastreador import Evento, Rastreador, TipoDeEvento
from l2scanner.sessao import Sessao

MOMENTO = 1787583219.0  # horario fixo para o texto ser estavel
FIXTURES = Path(__file__).parent / "fixtures" / "party_estavel_com_vazamento"

HORA = datetime.fromtimestamp(MOMENTO).strftime("%H:%M")


def morte(membro: str) -> Evento:
    return Evento(tipo=TipoDeEvento.MORREU, momento=MOMENTO, membro=membro)


def volta(membro: str, segundos: float | None = None) -> Evento:
    return Evento(
        tipo=TipoDeEvento.RESSUSCITOU,
        momento=MOMENTO,
        membro=membro,
        segundos_no_estado=segundos,
    )


class TestOCaminhoDeUmaMorteSoNaoMuda:
    """A rajada e o defeito; a morte isolada e o caminho que ja funciona.

    Ha muitos testes afirmando o texto exato de uma morte sozinha. Se o
    agrupamento tocar nesse texto, o conserto de uma dor produz outra.
    """

    def test_uma_morte_sozinha_sai_byte_a_byte_como_hoje(self):
        so_uma = morte("Membro 4")

        assert formatar_tick([so_uma]) == [formatar(so_uma)]

    def test_uma_ressurreicao_sozinha_sai_byte_a_byte_como_hoje(self):
        so_uma = volta("Membro 4", segundos=13.0)

        assert formatar_tick([so_uma]) == [formatar(so_uma)]

    def test_tick_sem_evento_nenhum_nao_produz_texto(self):
        assert formatar_tick([]) == []


class TestMortesDoMESMOTickViramUmAvisoSo:
    def test_duas_mortes(self):
        textos = formatar_tick([morte("Membro 1"), morte("Membro 2")])

        assert textos == [
            f"[{HORA}] 2 membros com HP zerado ao mesmo tempo: "
            f"Membro 1 e Membro 2. Possiveis mortes na PT."
        ]

    def test_tres_mortes(self):
        textos = formatar_tick(
            [morte("Membro 1"), morte("Membro 2"), morte("Membro 3")],
            membros_vigiados=4,
        )

        assert textos == [
            f"[{HORA}] 3 membros com HP zerado ao mesmo tempo: "
            f"Membro 1, Membro 2 e Membro 3. Possiveis mortes na PT."
        ]

    def test_a_party_inteira_caindo_junto_ganha_frase_propria(self):
        """"Wipe" e mais util do que quatro nomes que a party ja conhece.

        Quando TODO MUNDO que estava sendo visto cai no mesmo tick, a lista de
        nomes nao acrescenta informacao: o conjunto e "todos". A palavra que a
        party usa para isso e wipe, e ela cabe na notificacao do celular.
        """
        textos = formatar_tick(
            [
                morte("Membro 1"),
                morte("Membro 2"),
                morte("Membro 3"),
                morte("Membro 4"),
            ],
            membros_vigiados=4,
        )

        assert textos == [
            f"[{HORA}] PARTY INTEIRA com HP zerado ao mesmo tempo "
            f"(4 membros). Possivel wipe na PT."
        ]

    def test_sem_saber_o_tamanho_da_party_nunca_afirma_wipe(self):
        """Sem a contagem, "todos" e uma afirmacao que ninguem verificou."""
        textos = formatar_tick(
            [morte("Membro 1"), morte("Membro 2")], membros_vigiados=None
        )

        assert "wipe" not in textos[0].lower(), textos[0]

    def test_menos_mortes_que_membros_nao_e_wipe(self):
        textos = formatar_tick(
            [morte("Membro 1"), morte("Membro 2"), morte("Membro 3")],
            membros_vigiados=4,
        )

        assert "wipe" not in textos[0].lower(), textos[0]

    def test_o_texto_agrupado_continua_sendo_uma_SUSPEITA(self):
        """O scanner le pixels, nao le a verdade -- inclusive no plural.

        "3 morreram" nao sobrevive a um falso positivo; "HP zerado, possiveis
        mortes" sobrevive. A redacao cautelosa e a mesma regra do caminho de
        um evento so, e nao pode se perder no agrupamento.
        """
        for quantas in (2, 3, 4):
            textos = formatar_tick(
                [morte(f"Membro {i + 1}") for i in range(quantas)],
                membros_vigiados=4,
            )
            texto = textos[0]
            assert "ossive" in texto, texto  # possivel / possiveis
            assert "morreram" not in texto.lower(), texto
            assert "MORREU" not in texto, texto

    @pytest.mark.parametrize("quantas", [2, 3, 4, 5, 6, 7, 8])
    def test_o_plural_nunca_sai_quebrado(self, quantas):
        """Um conserto de 2026-08-31 pegou um plural que a suite nao pegava.

        So o caminho singular era exercitado, entao o erro aparecia no dia em
        que houvesse duas pessoas -- que e o dia do farm real.
        """
        textos = formatar_tick(
            [morte(f"Membro {i + 1}") for i in range(quantas)],
            membros_vigiados=99,
        )
        texto = textos[0]

        assert "1 membros" not in texto, texto
        assert f"{quantas} membros" in texto, texto
        assert ",," not in texto and " e e " not in texto, texto


class TestRessurreicoesAgrupadasNaoPerdemOTEMPO:
    """Cada volta carrega o proprio "apos 13s", e o numero e a informacao."""

    def test_duas_voltas_mantem_a_duracao_de_cada_uma(self):
        textos = formatar_tick(
            [volta("Membro 4", 13.0), volta("Membro 1", 12.0)]
        )

        assert textos == [
            f"[{HORA}] 2 membros com HP de volta: "
            f"Membro 4 (apos 13s) e Membro 1 (apos 12s)."
        ]

    def test_quem_nao_tem_duracao_sai_so_com_o_nome(self):
        textos = formatar_tick(
            [volta("Membro 4", 13.0), volta("Membro 1"), volta("Membro 2", 12.0)]
        )

        assert textos == [
            f"[{HORA}] 3 membros com HP de volta: "
            f"Membro 4 (apos 13s), Membro 1 e Membro 2 (apos 12s)."
        ]


class TestOEscopoDoAgrupamento:
    """Agrupar afirma CAUSA COMUM. So agrupa quem tem uma."""

    def test_saidas_continuam_uma_por_uma(self):
        """Quatro pessoas saindo sao quatro decisoes, e nao um evento.

        N barras zerando num segundo tem uma causa fisica unica (a AoE que
        pegou a party). N saidas nao tem: a tela nao distingue "o lider
        desfez a party" de "tres pessoas sairam por conta propria", e uma
        frase so afirmaria a causa que o scanner nao viu.
        """
        saidas = [
            Evento(tipo=TipoDeEvento.SAIU, momento=MOMENTO, membro=f"Membro {i}")
            for i in (1, 2, 3)
        ]

        assert formatar_tick(saidas) == [formatar(e) for e in saidas]

    def test_entradas_continuam_uma_por_uma(self):
        entradas = [
            Evento(tipo=TipoDeEvento.ENTROU, momento=MOMENTO, membro=f"Membro {i}")
            for i in (1, 2)
        ]

        assert formatar_tick(entradas) == [formatar(e) for e in entradas]

    def test_tipos_diferentes_no_mesmo_tick_nao_se_misturam(self):
        eventos = [
            morte("Membro 1"),
            Evento(tipo=TipoDeEvento.SAIU, momento=MOMENTO, membro="Membro 9"),
            morte("Membro 2"),
        ]

        textos = formatar_tick(eventos)

        assert len(textos) == 2, textos
        assert "Membro 1 e Membro 2" in textos[0], textos[0]
        assert textos[1] == formatar(eventos[1])


class TestOTextoAgrupadoPassaPeloConsoleDoWindows:
    """O console do Windows e cp1252: um travessao novo derruba o print."""

    def test_nenhum_texto_agrupado_tem_travessao(self):
        casos = [
            formatar_tick([morte("Membro 1"), morte("Membro 2")]),
            formatar_tick(
                [morte(f"Membro {i}") for i in (1, 2, 3, 4)], membros_vigiados=4
            ),
            formatar_tick([volta("Membro 1", 13.0), volta("Membro 2", 12.0)]),
        ]

        for textos in casos:
            for texto in textos:
                assert "—" not in texto, texto
                texto.encode("cp1252")
                texto.encode("ascii")


# -- o tick de verdade -----------------------------------------------------


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


def sessao_que_produz(calibracao, tmp_path, eventos, registrados):
    rastreador = Rastreador(nomes=list(calibracao.nomes))
    rastreador.observar = lambda obs, agora: list(eventos)
    return Sessao(
        cal=calibracao,
        rastreador=rastreador,
        eventos_agendados=[],
        registro=RegistroEmDisco(tmp_path),
        silencio=None,
        ao_registrar=registrados.append,
    )


class TestAMaquinaDeEstadoNaoPercebeOAgrupamento:
    """Agrupar e APRESENTACAO. Quem consome evento continua vendo N."""

    def test_quatro_mortes_num_tick_sao_um_despacho_e_quatro_eventos(
        self, calibracao, frame_real, tmp_path
    ):
        registrados: list = []
        mortes = [morte(f"Membro {i}") for i in (1, 2, 3, 4)]
        s = sessao_que_produz(calibracao, tmp_path, mortes, registrados)

        r = s.tick(frame_real, momento=MOMENTO)

        assert len(r.despachos) == 1, r.despachos
        assert len(r.eventos) == 4
        assert len(registrados) == 4
        assert s.total_eventos == 4

    def test_o_aviso_sai_NO_MESMO_TICK_sem_janela_de_espera(
        self, calibracao, frame_real, tmp_path
    ):
        """Esperar 3s para juntar mortes paga atraso no alerta mais urgente.

        O produto inteiro existe para a party socorrer alguem a tempo. Dentro
        de um tick o agrupamento e de graca, porque a lista ja existe.
        """
        registrados: list = []
        mortes = [morte(f"Membro {i}") for i in (1, 2)]
        s = sessao_que_produz(calibracao, tmp_path, mortes, registrados)

        r = s.tick(frame_real, momento=MOMENTO)

        assert r.despachos, "o aviso tem de sair no proprio tick"

    def test_a_party_inteira_do_frame_real_vira_wipe(
        self, calibracao, frame_real, tmp_path
    ):
        """O frame de fixture tem 4 linhas ocupadas; 4 mortes sao um wipe."""
        registrados: list = []
        mortes = [morte(f"Membro {i}") for i in (1, 2, 3, 4)]
        s = sessao_que_produz(calibracao, tmp_path, mortes, registrados)

        r = s.tick(frame_real, momento=MOMENTO)

        texto = r.despachos[0][0]
        assert "PARTY INTEIRA" in texto, texto
        assert "wipe" in texto, texto

    def test_uma_morte_sozinha_no_tick_continua_com_o_texto_de_hoje(
        self, calibracao, frame_real, tmp_path
    ):
        registrados: list = []
        so_uma = morte("Membro 2")
        s = sessao_que_produz(calibracao, tmp_path, [so_uma], registrados)

        r = s.tick(frame_real, momento=MOMENTO)

        assert r.despachos[0][0] == formatar(so_uma)
