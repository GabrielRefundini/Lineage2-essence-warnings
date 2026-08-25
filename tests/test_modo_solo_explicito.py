"""O modo solo EXPLICITO: nao estou em party, e isso e escolha.

A diferenca em relacao a "party window sumiu" e toda. Ali o scanner nao sabe se
voce saiu, se a UI travou ou se o jogo caiu — e reclamar e o certo. Aqui ele
SABE que nao ha party, porque voce disse. Reclamar da ausencia seria ruido
garantido, a cada tick, pela sessao inteira.

O que NAO muda: a sua morte continua vigiada com o mesmo debounce, e a agenda
continua igual. Solo e justamente quando morrer AFK passa mais despercebido —
em party alguem nota.
"""

from __future__ import annotations

from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento
from l2scanner.visao import EstadoDaLinha, LeituraDeLinha, Observacao


def com_party(hp_proprio=1.0):
    linhas = tuple(
        LeituraDeLinha(i, EstadoDaLinha.COM_MEMBRO, 1.0, 1.0, n, 0.98)
        for i, n in enumerate(["Kaus", "Korzis"])
    )
    return Observacao(0, True, linhas, hp_proprio=hp_proprio)


def sem_party(hp_proprio=1.0):
    return Observacao(0, False, (), hp_proprio=hp_proprio)


def novo(solo: bool):
    return Rastreador(
        nomes=["Kaus", "Korzis"],
        nome_proprio="Yazalaque",
        modo_solo=solo,
        ajustes=Ajustes(),
    )


def rodar(r, obs, vezes, inicio=0.0):
    eventos = []
    for i in range(vezes):
        eventos.extend(r.observar(obs, inicio + i))
    return eventos


class TestSoloNaoReclamaDePartyAusente:
    def _sair_da_party_e_ficar(self, solo):
        r = novo(solo)
        rodar(r, com_party(), 20)
        return r, rodar(r, sem_party(), 400, inicio=100)

    def test_solo_nao_anuncia_que_voce_saiu_da_party(self):
        _, eventos = self._sair_da_party_e_ficar(solo=True)
        tipos = [e.tipo for e in eventos]
        assert TipoDeEvento.VOCE_SEM_PARTY not in tipos

    def test_solo_nao_reclama_de_cegueira(self):
        """Nao ha party window para enxergar. Reclamar seria reclamar da
        ausencia de algo que o usuario decidiu nao ter."""
        _, eventos = self._sair_da_party_e_ficar(solo=True)
        tipos = [e.tipo for e in eventos]
        assert TipoDeEvento.CEGUEIRA_LONGA not in tipos

    def test_no_modo_NORMAL_os_dois_avisos_continuam(self):
        """A trava contra o solo virar o comportamento padrao por engano."""
        _, eventos = self._sair_da_party_e_ficar(solo=False)
        tipos = [e.tipo for e in eventos]
        assert TipoDeEvento.VOCE_SEM_PARTY in tipos
        assert TipoDeEvento.CEGUEIRA_LONGA in tipos


class TestSoloAindaVigiaVoce:
    """O motivo de o modo existir. Em party alguem nota que voce caiu."""

    def test_sua_morte_e_detectada(self):
        r = novo(solo=True)
        rodar(r, sem_party(), 20)
        eventos = rodar(r, sem_party(hp_proprio=0.0), 10, inicio=100)
        mortes = [e for e in eventos if e.tipo is TipoDeEvento.MORREU]
        assert [e.membro for e in mortes] == ["Yazalaque"]

    def test_sua_ressurreicao_tambem(self):
        r = novo(solo=True)
        rodar(r, sem_party(), 20)
        rodar(r, sem_party(hp_proprio=0.0), 10, inicio=100)
        eventos = rodar(r, sem_party(hp_proprio=0.9), 10, inicio=200)
        assert any(e.tipo is TipoDeEvento.RESSUSCITOU for e in eventos)

    def test_o_mesmo_debounce_do_modo_normal(self):
        """Nao ha motivo para a sua morte ser julgada com criterio diferente."""
        r = Rastreador(
            nome_proprio="Yazalaque",
            modo_solo=True,
            ajustes=Ajustes(confirmacoes_para_morte=3),
        )
        rodar(r, sem_party(), 20)
        assert rodar(r, sem_party(hp_proprio=0.0), 2, inicio=100) == []
        eventos = rodar(r, sem_party(hp_proprio=0.0), 1, inicio=200)
        assert [e.tipo for e in eventos] == [TipoDeEvento.MORREU]

    def test_barra_ilegivel_continua_sem_virar_morte(self):
        """A guarda do recorte degenerado vale igual no solo."""
        r = novo(solo=True)
        rodar(r, sem_party(), 20)
        assert rodar(r, sem_party(hp_proprio=None), 60, inicio=100) == []


class TestTrocarDeModoAoVivo:
    """`.solo` e `.party` sem reiniciar.

    E o comando que mais faz sentido vir do WhatsApp: a hora de virar solo e
    quando a party se desfaz, e nesse momento o usuario esta no jogo.
    """

    def test_ligar_o_solo_cala_o_aviso_de_party(self):
        r = novo(solo=False)
        rodar(r, com_party(), 20)
        r.modo_solo = True
        eventos = rodar(r, sem_party(), 400, inicio=100)
        assert TipoDeEvento.VOCE_SEM_PARTY not in [e.tipo for e in eventos]

    def test_desligar_o_solo_devolve_a_vigilancia_da_party(self):
        """Depois de voltar ao normal, ele precisa VER a party antes de poder
        anunciar que voce saiu dela.

        Em solo o scanner nunca estabelece "voce esta em party" — a avaliacao
        e pulada. Entao a primeira conclusao depois de desligar o solo e comeco
        frio, e comeco frio nao anuncia. Ele so pode dizer "voce saiu" depois de
        ter visto voce dentro.
        """
        r = novo(solo=True)
        rodar(r, com_party(), 20)

        r.modo_solo = False
        rodar(r, com_party(), 20, inicio=100)  # agora ele VE a party

        eventos = rodar(r, sem_party(), 400, inicio=200)
        assert TipoDeEvento.VOCE_SEM_PARTY in [e.tipo for e in eventos]

    def test_logo_apos_desligar_o_solo_ele_NAO_inventa_uma_saida(self):
        """O espelho: sem ter visto a party, nao ha saida a anunciar."""
        r = novo(solo=True)
        rodar(r, com_party(), 20)

        r.modo_solo = False
        eventos = rodar(r, sem_party(), 400, inicio=100)
        assert TipoDeEvento.VOCE_SEM_PARTY not in [e.tipo for e in eventos]

    def test_o_console_diz_SOLO_em_vez_de_SEM_VISAO(self):
        """No solo, "SEM VISAO" seria mentira por omissao: o scanner nao perdeu
        nada. Ele esta vigiando voce, e precisa dizer isso."""
        from l2scanner.__main__ import desenhar_status
        from l2scanner.calibracao import Calibracao

        r = novo(solo=True)
        cal = Calibracao.__new__(Calibracao)
        texto = desenhar_status(r, cal, sem_party())
        assert "SOLO" in texto
        assert "SEM VISAO" not in texto
