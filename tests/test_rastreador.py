"""Testes do rastreador — a logica que decide o que aconteceu.

Cada classe aqui corresponde a um jeito concreto do scanner mentir para a party.
Tudo roda sem jogo, sem tela e sem rede: o tempo entra por parametro, entao meia
hora de cegueira e testada em microssegundos.
"""

from __future__ import annotations

import pytest

from l2scanner.rastreador import (
    Ajustes,
    EstadoDoMembro,
    PortaoGlobal,
    Rastreador,
    TipoDeEvento,
)
from l2scanner.visao import EstadoDaLinha, LeituraDeLinha, Observacao

NOMES = ["J4guar", "Kaus", "TioMad", "Korzis"]


def obs(
    *hp: float | None, ui_visivel: bool = True, indice: int = 0
) -> Observacao:
    """Observacao curta de escrever: `obs(1.0, 0.0, None, 1.0)`.

    `None` significa linha vazia (membro nao esta ali).
    """
    linhas = []
    for i, valor in enumerate(hp):
        if valor is None:
            linhas.append(
                LeituraDeLinha(indice=i, estado=EstadoDaLinha.VAZIA, hp=None, mp=None)
            )
        else:
            linhas.append(
                LeituraDeLinha(
                    indice=i, estado=EstadoDaLinha.COM_MEMBRO, hp=valor, mp=1.0
                )
            )
    return Observacao(
        indice_do_frame=indice, ui_visivel=ui_visivel, linhas=tuple(linhas)
    )


def alimentar(
    rastreador: Rastreador,
    observacao: Observacao,
    vezes: int,
    inicio: float = 0.0,
    passo: float = 1.0,
) -> list:
    """Alimenta a mesma observacao N vezes e acumula os eventos."""
    eventos = []
    for i in range(vezes):
        eventos.extend(rastreador.observar(observacao, inicio + i * passo))
    return eventos


def novo(**kwargs) -> Rastreador:
    return Rastreador(nomes=list(NOMES), ajustes=Ajustes(**kwargs))


def aquecer(rastreador: Rastreador, observacao: Observacao) -> None:
    """Leva o rastreador ate o regime permanente, sem gerar evento nenhum.

    O aquecimento nao e instantaneo de proposito: o scanner gasta a tolerancia
    de reaquisicao e depois as confirmacoes de presenca antes de acreditar no
    que ve. Isso e o que impede o proprio ato de ligar o scanner de anunciar
    que a party inteira acabou de entrar.
    """
    eventos = alimentar(rastreador, observacao, vezes=15, inicio=-100, passo=1.0)
    assert eventos == [], f"o aquecimento nao deveria gerar eventos: {eventos}"


class TestComecoFrio:
    """Ligar o scanner nao pode anunciar nada."""

    def test_party_viva_no_inicio_nao_gera_evento(self):
        r = novo()
        eventos = alimentar(r, obs(1.0, 1.0, 1.0, 1.0), vezes=10)
        assert eventos == []

    def test_membro_ja_morto_ao_ligar_nao_anuncia_morte(self):
        """Se ele ja estava morto quando liguei, nao foi agora que morreu."""
        r = novo()
        eventos = alimentar(r, obs(1.0, 0.0, 1.0, 1.0), vezes=10)

        assert [e for e in eventos if e.tipo is TipoDeEvento.MORREU] == []
        assert r.estado_de(1) is EstadoDoMembro.MORTO

    def test_party_menor_no_inicio_nao_anuncia_saidas(self):
        r = novo()
        eventos = alimentar(r, obs(1.0, 1.0, None, None), vezes=10)
        assert eventos == []


class TestMorte:
    """O evento central do produto."""

    def test_morte_confirmada_apos_n_leituras(self):
        r = novo(confirmacoes_para_morte=3)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        # duas leituras de HP zerado ainda nao bastam
        eventos = alimentar(r, obs(1.0, 1.0, 0.0, 1.0), vezes=2, inicio=10)
        assert eventos == []

        # a terceira confirma
        eventos = alimentar(r, obs(1.0, 1.0, 0.0, 1.0), vezes=1, inicio=12)
        assert len(eventos) == 1
        assert eventos[0].tipo is TipoDeEvento.MORREU
        assert eventos[0].membro == "TioMad"

    def test_hp_piscando_nao_gera_morte(self):
        """Um frame borrado ou um efeito passando por cima nao e morte."""
        r = novo(confirmacoes_para_morte=3)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        eventos = []
        for i in range(20):  # alterna zerado/cheio
            leitura = obs(1.0, 1.0, 0.0 if i % 2 else 1.0, 1.0)
            eventos.extend(r.observar(leitura, 10 + i))

        assert [e for e in eventos if e.tipo is TipoDeEvento.MORREU] == []

    def test_um_morto_gera_exatamente_um_alerta(self):
        """Um cadaver por cinco minutos nao vira cinco minutos de mensagens."""
        r = novo(confirmacoes_para_morte=3)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        eventos = alimentar(r, obs(1.0, 1.0, 0.0, 1.0), vezes=300, inicio=10)
        mortes = [e for e in eventos if e.tipo is TipoDeEvento.MORREU]
        assert len(mortes) == 1

    def test_residuo_de_pixel_na_borda_conta_como_zero(self):
        """A borda da barra deixa um ou dois pixels; 1% nao e estar vivo."""
        r = novo(confirmacoes_para_morte=3, fracao_hp_considerada_zero=0.02)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        eventos = alimentar(r, obs(1.0, 1.0, 0.008, 1.0), vezes=5, inicio=10)
        assert any(e.tipo is TipoDeEvento.MORREU for e in eventos)

    def test_wipe_total_gera_um_alerta_por_membro(self):
        r = novo(confirmacoes_para_morte=3)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        eventos = alimentar(r, obs(0.0, 0.0, 0.0, 0.0), vezes=10, inicio=10)
        mortes = [e for e in eventos if e.tipo is TipoDeEvento.MORREU]

        assert len(mortes) == 4
        assert {e.membro for e in mortes} == set(NOMES)


class TestRessurreicao:
    """Histerese assimetrica — sair do estado morto e mais dificil que entrar."""

    def test_ressurreicao_exige_mais_confirmacoes_que_a_morte(self):
        r = novo(confirmacoes_para_morte=3, confirmacoes_para_ressurreicao=5)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))
        alimentar(r, obs(1.0, 1.0, 0.0, 1.0), vezes=5, inicio=10)

        # quatro leituras de HP de volta ainda nao bastam
        eventos = alimentar(r, obs(1.0, 1.0, 0.5, 1.0), vezes=4, inicio=20)
        assert eventos == []

        eventos = alimentar(r, obs(1.0, 1.0, 0.5, 1.0), vezes=1, inicio=24)
        assert len(eventos) == 1
        assert eventos[0].tipo is TipoDeEvento.RESSUSCITOU

    def test_ressurreicao_informa_quanto_tempo_ficou_morto(self):
        r = novo(confirmacoes_para_morte=3, confirmacoes_para_ressurreicao=3)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))
        alimentar(r, obs(1.0, 1.0, 0.0, 1.0), vezes=3, inicio=100)

        eventos = alimentar(r, obs(1.0, 1.0, 0.9, 1.0), vezes=3, inicio=160)
        ressurreicao = next(
            e for e in eventos if e.tipo is TipoDeEvento.RESSUSCITOU
        )
        assert ressurreicao.segundos_no_estado == pytest.approx(60, abs=2)

    def test_piscar_de_hp_no_cadaver_nao_gera_bate_estaca(self):
        """Sem histerese, isto viraria ressuscitou/morreu/ressuscitou sem fim."""
        r = novo(confirmacoes_para_morte=3, confirmacoes_para_ressurreicao=5)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))
        alimentar(r, obs(1.0, 1.0, 0.0, 1.0), vezes=5, inicio=10)

        eventos = []
        for i in range(40):
            leitura = obs(1.0, 1.0, 0.5 if i % 2 else 0.0, 1.0)
            eventos.extend(r.observar(leitura, 20 + i))

        assert eventos == []


class TestSaidaDaParty:
    """Linha some = saiu. Distinto de HP zerado, que e morte."""

    def test_saida_confirmada_apos_alguns_segundos(self):
        r = novo(confirmacoes_para_saida=5)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        eventos = alimentar(r, obs(1.0, 1.0, 1.0, None), vezes=5, inicio=10)
        saidas = [e for e in eventos if e.tipo is TipoDeEvento.SAIU]

        assert len(saidas) == 1
        assert saidas[0].membro == "Korzis"

    def test_morte_e_saida_sao_eventos_diferentes(self):
        """A distincao que sustenta o produto.

        Nas barras os dois leem 0%. So o icone de classe separa os casos.
        """
        r = novo(confirmacoes_para_morte=3, confirmacoes_para_saida=5)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        # membro 2 morre (presente, HP zerado); membro 3 sai (linha vazia)
        eventos = alimentar(r, obs(1.0, 1.0, 0.0, None), vezes=6, inicio=10)

        tipos = {(e.tipo, e.membro) for e in eventos}
        assert (TipoDeEvento.MORREU, "TioMad") in tipos
        assert (TipoDeEvento.SAIU, "Korzis") in tipos

    def test_entrada_de_novo_membro(self):
        r = novo(confirmacoes_para_entrada=3, confirmacoes_para_saida=3)
        aquecer(r, obs(1.0, 1.0, 1.0, None))

        eventos = alimentar(r, obs(1.0, 1.0, 1.0, 1.0), vezes=5, inicio=20)
        entradas = [e for e in eventos if e.tipo is TipoDeEvento.ENTROU]

        assert len(entradas) == 1
        assert entradas[0].membro == "Korzis"


class TestPortaoDeCegueira:
    """A propriedade de ordem: visibilidade e checada ANTES das linhas."""

    def test_alt_tab_nao_anuncia_que_a_party_inteira_saiu(self):
        """Se o portao rodasse depois das linhas, isto seriam quatro alertas."""
        r = novo()
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        eventos = alimentar(
            r, obs(None, None, None, None, ui_visivel=False), vezes=30, inicio=20
        )
        assert [e for e in eventos if e.tipo is TipoDeEvento.SAIU] == []

    def test_wipe_total_nao_e_confundido_com_alt_tab(self):
        """A diferenca vem do icone de classe, que sobrevive a morte.

        Se a visibilidade fosse deduzida das barras, uma party inteira morta
        seria identica a um alt-tab — e o scanner ficaria mudo no momento mais
        importante possivel.
        """
        r = novo(confirmacoes_para_morte=3)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        # todos com HP zerado, mas a UI continua visivel (icones presentes)
        eventos = alimentar(
            r, obs(0.0, 0.0, 0.0, 0.0, ui_visivel=True), vezes=5, inicio=10
        )
        assert len([e for e in eventos if e.tipo is TipoDeEvento.MORREU]) == 4

    def test_cegueira_congela_contadores_em_vez_de_zerar(self):
        """Uma morte iniciada logo antes do alt-tab ainda precisa alertar."""
        r = novo(confirmacoes_para_morte=3, segundos_de_tolerancia_na_volta=0.0)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        # duas leituras de HP zerado — falta uma para confirmar
        alimentar(r, obs(1.0, 1.0, 0.0, 1.0), vezes=2, inicio=10)

        # alt-tab no meio do caminho
        alimentar(r, obs(ui_visivel=False), vezes=20, inicio=12)

        # a visao volta e o membro continua morto: UMA leitura fecha a conta,
        # porque o contador foi congelado, nao zerado
        eventos = alimentar(r, obs(1.0, 1.0, 0.0, 1.0), vezes=1, inicio=40)

        assert len([e for e in eventos if e.tipo is TipoDeEvento.MORREU]) == 1

    def test_tolerancia_na_volta_evita_morte_inventada(self):
        """A UI redesenha em partes; as barras leem zero por um ou dois frames."""
        r = novo(confirmacoes_para_morte=2, segundos_de_tolerancia_na_volta=3.0)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))
        alimentar(r, obs(ui_visivel=False), vezes=5, inicio=10)

        # volta com tudo lendo zero (UI meio desenhada), dentro da tolerancia
        eventos = alimentar(r, obs(0.0, 0.0, 0.0, 0.0), vezes=3, inicio=20, passo=0.5)
        assert eventos == []

    def test_apos_a_tolerancia_o_rastreio_volta_normal(self):
        r = novo(confirmacoes_para_morte=2, segundos_de_tolerancia_na_volta=3.0)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))
        alimentar(r, obs(ui_visivel=False), vezes=5, inicio=10)
        alimentar(r, obs(1.0, 1.0, 1.0, 1.0), vezes=2, inicio=20, passo=0.5)

        eventos = alimentar(r, obs(1.0, 1.0, 0.0, 1.0), vezes=3, inicio=30)
        assert any(e.tipo is TipoDeEvento.MORREU for e in eventos)


class TestCegueiraLonga:
    """Perda de cobertura silenciosa e o pior modo de falha do dominio."""

    def test_alt_tab_curto_nao_gera_aviso(self):
        r = novo(segundos_para_cegueira_longa=300.0)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        eventos = alimentar(r, obs(ui_visivel=False), vezes=60, inicio=10)
        assert eventos == []

    def test_cegueira_prolongada_gera_um_aviso(self):
        r = novo(segundos_para_cegueira_longa=300.0)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        eventos = alimentar(r, obs(ui_visivel=False), vezes=400, inicio=10)
        avisos = [e for e in eventos if e.tipo is TipoDeEvento.CEGUEIRA_LONGA]

        assert len(avisos) == 1
        assert avisos[0].segundos_no_estado >= 300

    def test_volta_de_cegueira_longa_informa_a_duracao(self):
        r = novo(segundos_para_cegueira_longa=300.0)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))
        alimentar(r, obs(ui_visivel=False), vezes=400, inicio=10)

        eventos = alimentar(r, obs(1.0, 1.0, 1.0, 1.0), vezes=1, inicio=500)
        recuperacao = [
            e for e in eventos if e.tipo is TipoDeEvento.VISAO_RECUPERADA
        ]

        assert len(recuperacao) == 1
        assert recuperacao[0].segundos_no_estado == pytest.approx(490, abs=5)

    def test_volta_de_cegueira_curta_nao_informa_nada(self):
        r = novo(segundos_para_cegueira_longa=300.0)
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))
        alimentar(r, obs(ui_visivel=False), vezes=10, inicio=10)

        eventos = alimentar(r, obs(1.0, 1.0, 1.0, 1.0), vezes=1, inicio=30)
        assert eventos == []


class TestPortaoEstado:
    def test_comeca_cego(self):
        assert novo().portao is PortaoGlobal.CEGO

    def test_vira_rastreando_apos_a_tolerancia(self):
        r = novo(segundos_de_tolerancia_na_volta=2.0)
        alimentar(r, obs(1.0, 1.0, 1.0, 1.0), vezes=5, passo=1.0)
        assert r.portao is PortaoGlobal.RASTREANDO

    def test_perder_visao_volta_para_cego(self):
        r = novo()
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))
        r.observar(obs(ui_visivel=False), 100)
        assert r.portao is PortaoGlobal.CEGO


class TestFechamentoDoJogo:
    def test_fechar_o_jogo_nao_anuncia_quatro_saidas(self):
        """Fechar o cliente as duas da manha nao pode acordar a party toda."""
        r = novo()
        aquecer(r, obs(1.0, 1.0, 1.0, 1.0))

        eventos = r.encerrar(agora=100.0, jogo_fechou=True)
        assert eventos == []


class TestNomes:
    def test_usa_o_nome_configurado(self):
        r = novo()
        assert r.nome_de(0) == "J4guar"
        assert r.nome_de(3) == "Korzis"

    def test_linha_sem_nome_ganha_rotulo_generico(self):
        """Melhor alertar 'Membro 5 morreu' do que nao alertar."""
        r = novo()
        assert r.nome_de(4) == "Membro 5"
