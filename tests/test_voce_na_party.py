"""Detectar que VOCE saiu (ou foi removido) da party.

Isto so e possivel porque a barra do proprio personagem e lida separada da
party window. A combinacao de sinais e unica:

    alt-tab / jogo coberto  -> a captura por janela ve tudo, nada some
    tela de loading         -> some tudo, a sua barra inclusive
    voce fora da party      -> SO a party window some; a sua barra fica

Sem a barra propria, "sair da party" era indistinguivel de "perdi a visao", e o
scanner ficava calado — o usuario podia ser expulso da party e passar o farm
inteiro achando que estava coberto.
"""

from __future__ import annotations

import pytest

from l2scanner.notificador import formatar, formatar_console
from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento
from l2scanner.visao import EstadoDaLinha, LeituraDeLinha, Observacao

MEMBROS = ["Kaus", "Korzis"]


def com_party(hp_proprio: float = 1.0) -> Observacao:
    linhas = tuple(
        LeituraDeLinha(
            i, EstadoDaLinha.COM_MEMBRO, 1.0, 1.0, nome=n, confianca_do_nome=0.98
        )
        for i, n in enumerate(MEMBROS)
    )
    return Observacao(0, True, linhas, hp_proprio=hp_proprio)


def sem_party(hp_proprio: float = 1.0) -> Observacao:
    """Party window sumiu, mas a barra do personagem continua legivel."""
    return Observacao(0, False, (), hp_proprio=hp_proprio)


def loading() -> Observacao:
    """Some tudo: nem party window, nem a barra propria."""
    return Observacao(0, False, (), hp_proprio=None)


def novo(**kwargs) -> Rastreador:
    padroes = dict(confirmacoes_para_voce_sem_party=4, confirmacoes_para_entrada=3)
    padroes.update(kwargs)
    r = Rastreador(
        nomes=list(MEMBROS), nome_proprio="Yazalaque", ajustes=Ajustes(**padroes)
    )
    for i in range(15):
        r.observar(com_party(), -100 + i)
    return r


def alimentar(r, obs, vezes, inicio=10.0):
    eventos = []
    for i in range(vezes):
        eventos.extend(r.observar(obs, inicio + i))
    return eventos


class TestVoceForaDaParty:
    def test_party_window_sumindo_com_a_sua_barra_visivel_avisa(self):
        r = novo()
        eventos = alimentar(r, sem_party(), vezes=8)

        avisos = [e for e in eventos if e.tipo is TipoDeEvento.VOCE_SEM_PARTY]
        assert len(avisos) == 1
        assert avisos[0].membro == "Yazalaque"

    def test_avisa_uma_vez_so(self):
        """Ficar sem party por meia hora nao vira meia hora de mensagens."""
        r = novo()
        eventos = alimentar(r, sem_party(), vezes=200)

        avisos = [e for e in eventos if e.tipo is TipoDeEvento.VOCE_SEM_PARTY]
        assert len(avisos) == 1

    def test_sumico_curto_nao_avisa(self):
        """Trocar de zona ou abrir menu esconde a party por alguns frames."""
        r = novo()
        eventos = alimentar(r, sem_party(), vezes=3)
        assert eventos == []

    def test_voltar_para_uma_party_avisa(self):
        r = novo()
        alimentar(r, sem_party(), vezes=8)

        eventos = alimentar(r, com_party(), vezes=5, inicio=100)
        voltas = [
            e for e in eventos if e.tipo is TipoDeEvento.VOCE_ENTROU_EM_PARTY
        ]
        assert len(voltas) == 1

    def test_comeco_frio_sem_party_nao_avisa(self):
        """Ligar o scanner ja fora de party nao e um evento."""
        r = Rastreador(
            nomes=list(MEMBROS),
            nome_proprio="Yazalaque",
            ajustes=Ajustes(confirmacoes_para_voce_sem_party=4),
        )
        eventos = alimentar(r, sem_party(), vezes=20, inicio=0)
        assert [
            e for e in eventos if e.tipo is TipoDeEvento.VOCE_SEM_PARTY
        ] == []


class TestNaoConfundirComOutrasCausas:
    """A distincao que faz o recurso valer a pena."""

    def test_loading_nao_e_lido_como_sair_da_party(self):
        """Na tela de loading a sua barra some junto — e outra coisa."""
        r = novo()
        eventos = alimentar(r, loading(), vezes=30)

        assert [
            e for e in eventos if e.tipo is TipoDeEvento.VOCE_SEM_PARTY
        ] == []

    def test_party_normal_nao_gera_aviso(self):
        r = novo()
        eventos = alimentar(r, com_party(), vezes=50)
        assert eventos == []

    def test_sua_morte_nao_e_confundida_com_sair_da_party(self):
        """Morrer zera a sua barra, mas a party window continua la."""
        r = novo(confirmacoes_para_morte=3)
        eventos = alimentar(r, com_party(hp_proprio=0.0), vezes=10)

        tipos = {e.tipo for e in eventos}
        assert TipoDeEvento.MORREU in tipos
        assert TipoDeEvento.VOCE_SEM_PARTY not in tipos

    def test_sem_barra_propria_calibrada_o_recurso_fica_desligado(self):
        """Calibracao antiga nao ganha avisos que nao sabe sustentar."""
        r = Rastreador(nomes=list(MEMBROS), nome_proprio=None)
        for i in range(15):
            r.observar(com_party(hp_proprio=None), -100 + i)

        eventos = alimentar(r, Observacao(0, False, (), hp_proprio=None), vezes=30)
        assert [
            e for e in eventos if e.tipo is TipoDeEvento.VOCE_SEM_PARTY
        ] == []


class TestTextoDoAviso:
    def _evento(self):
        from l2scanner.rastreador import Evento

        return Evento(
            tipo=TipoDeEvento.VOCE_SEM_PARTY, momento=1787590000.0, membro="Yazalaque"
        )

    def test_whatsapp_diz_que_pode_ter_sido_removido(self):
        """Nao da para saber se saiu ou foi expulso — o texto nao finge saber."""
        texto = formatar(self._evento())
        assert "Yazalaque" in texto
        assert "removido" in texto.lower()

    def test_whatsapp_explica_a_consequencia(self):
        """O usuario precisa saber que a cobertura da party acabou.

        A GARANTIA E A MESMA DE SEMPRE; o que mudou em 2026-09-02 foi o
        pedaco do texto que a carrega. A frase dizia "a party window sumiu da
        tela, e a partir de agora so o proprio personagem esta sendo vigiado":
        a primeira metade e o MECANISMO (como o scanner descobriu), e a
        segunda e a CONSEQUENCIA (o que mudou para quem le). No encurtamento
        pedido pelo usuario o mecanismo foi para a docstring de `formatar` e
        ficou a consequencia, que e a unica das duas sobre a qual o leitor
        decide alguma coisa.
        """
        texto = formatar(self._evento())
        assert "vigiando so o proprio personagem" in texto.lower()

    def test_console_e_direto(self):
        texto = formatar_console(self._evento())
        assert "YAZALAQUE" in texto
        assert "PARTY" in texto

    def test_texto_do_console_e_ascii(self):
        formatar_console(self._evento()).encode("ascii")


class TestCegueiraNaoEsaidaDaParty:
    """Sair da party NAO zera o seu HP. Cegueira zera.

    Visto ao vivo entre 18:19:50 e 18:21:19, com a party intacta o tempo todo:

        18:19:50  YAZALAQUE SAIU OU FOI REMOVIDO DA PARTY
        18:19:57  [SEM VISAO]  Yazalaque (voce) ok HP 0%
        18:20:57  [SEM VISAO]  Yazalaque (voce) ok HP 0%
        18:21:19  YAZALAQUE ENTROU EM PARTY

    Os dois alertas foram entregues no WhatsApp. Nada tinha mudado na party.

    A raiz: `medir_barra` devolve 0.0 para um recorte ilegivel, nunca None.
    Entao `hp_proprio is not None` — que o rastreador lia como "a minha barra
    esta visivel" — na verdade so diz "a regiao esta calibrada". Noventa
    segundos de cegueira produziram exatamente a assinatura de "voce saiu":
    party window ausente + barra propria "presente".

    O discriminador honesto nao precisa de pixel novo: uma saida de party nao
    encosta no seu HP. Party window ausente JUNTO com HP proprio zerado e
    cegueira, e cegueira congela — igual a morte e a ressurreicao.
    """

    def cego(self) -> Observacao:
        """O que o scanner ve com o recorte ilegivel: tudo zero."""
        return Observacao(0, False, (), hp_proprio=0.0)

    def test_cegueira_longa_nao_anuncia_que_voce_saiu(self):
        r = novo()
        eventos = alimentar(r, self.cego(), vezes=90)

        avisos = [e for e in eventos if e.tipo is TipoDeEvento.VOCE_SEM_PARTY]
        assert avisos == [], (
            "a barra propria lendo 0% junto com a party window ausente e "
            "recorte ilegivel, nao saida de party"
        )

    def test_recuperar_a_visao_nao_anuncia_que_voce_entrou(self):
        """O espelho: sem o falso 'saiu', a volta nao pode virar 'entrou'."""
        r = novo()
        alimentar(r, self.cego(), vezes=90)

        eventos = alimentar(r, com_party(), vezes=10, inicio=200)
        voltas = [
            e for e in eventos if e.tipo is TipoDeEvento.VOCE_ENTROU_EM_PARTY
        ]
        assert voltas == [], "a party estava la o tempo todo; a visao e que voltou"

    def test_saida_de_verdade_ainda_avisa(self):
        """A guarda nao pode desligar a deteccao.

        Numa saida de verdade a party window some e a SUA barra continua sendo
        lida normalmente — cheia, nao zerada.
        """
        r = novo()
        eventos = alimentar(r, sem_party(hp_proprio=1.0), vezes=8)

        avisos = [e.membro for e in eventos if e.tipo is TipoDeEvento.VOCE_SEM_PARTY]
        assert avisos == ["Yazalaque"]

    def test_voce_morto_e_sem_party_window_nao_e_saida(self):
        """Morrer nao e sair da party — e o caso que a guarda protege de graca.

        Se voce morre no exato momento em que a party window fica ilegivel, o
        certo e ficar calado sobre a party, nao anunciar uma saida que nao
        houve.
        """
        r = novo()
        eventos = alimentar(r, Observacao(0, False, (), hp_proprio=0.0), vezes=30)

        assert [
            e for e in eventos if e.tipo is TipoDeEvento.VOCE_SEM_PARTY
        ] == []


class TestArranqueCegoNaoEEntradaEmParty:
    """Demorar para enxergar a party window nao e "voce entrou em party".

    logs/scanner.log 18:07:46-18:08:00: o scanner subiu, passou ~14 s sem
    conseguir ler a party window (a barra propria lendo 100% normal o tempo
    todo) e anunciou "YAZALAQUE ENTROU EM PARTY" quando a visao voltou. A party
    estava la desde antes do scanner ligar.

    Mecanismo: `_voce_em_party` comeca None; N leituras sem party window fixam
    False em silencio (comeco frio, correto); a recuperacao entao ve
    False -> True e trata como transicao CONHECIDA, anunciando.

    Os pixels de "liguei o bot fora de party e depois entrei numa" e de "liguei
    o bot e demorei para conseguir ler a tela" sao identicos — nao existe imagem
    que separe os dois. A escolha e calar: anunciar uma entrada que voce mesmo
    fez (e portanto ja sabe) vale menos do que nao inventar uma que nao houve.
    """

    def test_visao_voltando_no_arranque_nao_anuncia_entrada(self):
        r = Rastreador(
            nomes=list(MEMBROS),
            nome_proprio="Yazalaque",
            ajustes=Ajustes(
                confirmacoes_para_voce_sem_party=4, confirmacoes_para_entrada=3
            ),
        )
        # nunca vimos a party window; a barra propria le normal
        eventos = alimentar(r, sem_party(hp_proprio=1.0), vezes=14, inicio=0)
        eventos += alimentar(r, com_party(), vezes=10, inicio=100)

        assert [
            e for e in eventos if e.tipo is TipoDeEvento.VOCE_ENTROU_EM_PARTY
        ] == [], "a party estava la o tempo todo; quem chegou foi a visao"

    def test_saida_e_volta_de_verdade_ainda_avisam_as_duas(self):
        """A guarda so vale para o comeco frio.

        Depois de ter visto a party window uma vez, "sem party" volta a ser
        conhecimento e o ciclo completo precisa avisar nas duas pontas.
        """
        r = novo()  # aquece 15 frames COM party

        saida = alimentar(r, sem_party(hp_proprio=1.0), vezes=8, inicio=10)
        volta = alimentar(r, com_party(), vezes=6, inicio=100)

        assert [
            e.membro for e in saida if e.tipo is TipoDeEvento.VOCE_SEM_PARTY
        ] == ["Yazalaque"]
        assert [
            e.membro for e in volta if e.tipo is TipoDeEvento.VOCE_ENTROU_EM_PARTY
        ] == ["Yazalaque"]
