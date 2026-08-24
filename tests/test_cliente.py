"""O cliente caiu — tela de login ou desconexao — e isso e um EVENTO.

Ate 2026-08-24 o scanner so sabia dizer "sem visao da party", e essa frase
cobria coisas muito diferentes: o jogo coberto por outra janela, um menu aberto
por cima, o servidor em manutencao, e o cliente de volta na tela de login.

Naquele dia o servidor entrou em manutencao e o scanner passou 90 s, e depois
5 min, repetindo "sem visao" sem nunca dizer o motivo. Os dois silencios estao
no `outbox.jsonl`. Cegueira com causa conhecida nao e cegueira: e um evento, e
e o evento que explica todos os silencios que vierem depois dele.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from l2scanner.cliente import (
    EstadoDoCliente,
    carregar_template,
    casar_dialogo,
    esta_na_tela_de_login,
    estado_do_cliente,
    nome_do_personagem,
)
from l2scanner.notificador import formatar, formatar_console
from l2scanner.rastreador import Ajustes, Evento, Rastreador, TipoDeEvento
from l2scanner.visao import EstadoDaLinha, LeituraDeLinha, Observacao

FIXTURES = Path(__file__).parent / "fixtures" / "cliente"


class TestTituloDaJanela:
    """O titulo e o sinal mais confiavel do projeto: texto do Windows.

    Sem limiar, sem HSV, sem calibracao, e nao quebra quando o usuario muda a
    resolucao. Verificado ao vivo com as duas instancias do usuario abertas ao
    mesmo tempo: 'Faerlina - XM Essence' (jogando) e 'XM Essence' (login).
    """

    @pytest.mark.parametrize(
        "titulo",
        ["XM Essence", "  XM Essence  ", "XM Essence "],
    )
    def test_titulo_sem_personagem_e_tela_de_login(self, titulo):
        assert esta_na_tela_de_login(titulo)

    @pytest.mark.parametrize(
        "titulo",
        [
            "Yazalaque - XM Essence",
            "Faerlina - XM Essence",
            "J4guar - XM Essence",
        ],
    )
    def test_titulo_com_personagem_nao_e_tela_de_login(self, titulo):
        assert not esta_na_tela_de_login(titulo)

    def test_endswith_seria_errado(self):
        """`endswith` casaria a janela do JOGO e inverteria a deteccao."""
        assert "Faerlina - XM Essence".endswith("XM Essence")
        assert not esta_na_tela_de_login("Faerlina - XM Essence")

    def test_titulo_ausente_nao_decide_nada(self):
        assert not esta_na_tela_de_login(None)
        assert not esta_na_tela_de_login("")

    def test_extrai_o_personagem(self):
        assert nome_do_personagem("Yazalaque - XM Essence") == "Yazalaque"
        assert nome_do_personagem("XM Essence") is None
        assert nome_do_personagem(None) is None


class TestTemplateDoDialogo:
    def test_o_template_esta_no_pacote(self):
        """Sem ele a deteccao de desconexao nao existe."""
        assert carregar_template() is not None

    def test_casa_o_dialogo_real(self):
        """Contra o frame capturado da desconexao de verdade."""
        recorte = cv2.imread(str(FIXTURES / "dialogo_desconexao_recorte.png"))
        assert recorte is not None
        pontuacao = casar_dialogo(recorte, carregar_template())
        assert pontuacao is not None
        assert pontuacao >= 0.99, f"casou apenas {pontuacao:.4f}"

    def test_frame_menor_que_o_template_e_nao_sei(self):
        """`None` e 'nao sei', nunca 0.0.

        Confundir os dois faz o scanner anunciar o contrario do que ve.
        """
        import numpy as np

        minusculo = np.zeros((5, 5, 3), dtype=np.uint8)
        assert casar_dialogo(minusculo, carregar_template()) is None

    def test_sem_template_nao_afirma_desconexao(self):
        assert casar_dialogo(None, None) is None
        estado = estado_do_cliente("Yazalaque - XM Essence", None, None)
        assert estado is EstadoDoCliente.EM_JOGO


class TestEstadoDoCliente:
    def test_login_vence_o_dialogo(self):
        """Um dialogo aberto NA tela de login ainda e tela de login.

        O titulo e prova; o template e evidencia. Prova vence.
        """
        recorte = cv2.imread(str(FIXTURES / "dialogo_desconexao_recorte.png"))
        assert (
            estado_do_cliente("XM Essence", recorte, carregar_template())
            is EstadoDoCliente.TELA_DE_LOGIN
        )

    def test_dialogo_com_titulo_de_jogo_e_desconectado(self):
        """O caso que MAIS importa: AFK e desconectado.

        Com o dialogo aberto o cliente continua se chamando
        'Faerlina - XM Essence' — pela janela ele ainda esta no jogo. Se o
        usuario esta AFK, o dialogo fica parado na tela para sempre e o titulo
        nunca muda. Sem o template, isso e silencio permanente.
        """
        recorte = cv2.imread(str(FIXTURES / "dialogo_desconexao_recorte.png"))
        assert (
            estado_do_cliente(
                "Faerlina - XM Essence", recorte, carregar_template()
            )
            is EstadoDoCliente.DESCONECTADO
        )

    def test_sem_titulo_e_desconhecido(self):
        """Janela fechada nao e 'caiu' — e 'nao sei'."""
        assert estado_do_cliente(None) is EstadoDoCliente.DESCONHECIDO


def _obs(estado, ui=True, nomes=("Kaus", "Korzis")):
    linhas = tuple(
        LeituraDeLinha(
            i, EstadoDaLinha.COM_MEMBRO, 1.0, 1.0, nome=n, confianca_do_nome=0.98
        )
        for i, n in enumerate(nomes)
    )
    return Observacao(0, ui, linhas, hp_proprio=1.0, estado_do_cliente=estado)


def _novo():
    return Rastreador(
        nomes=["Kaus", "Korzis"],
        nome_proprio="Yazalaque",
        ajustes=Ajustes(
            confirmacoes_para_jogo_caiu=2, confirmacoes_para_jogo_voltou=4
        ),
    )


def _alimentar(r, obs, vezes, inicio=0.0):
    eventos = []
    for i in range(vezes):
        eventos.extend(r.observar(obs, inicio + i))
    return eventos


class TestRastreadorAnunciaAQueda:
    def test_queda_para_a_tela_de_login_avisa(self):
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 10)

        eventos = _alimentar(
            r, _obs(EstadoDoCliente.TELA_DE_LOGIN, ui=False, nomes=()), 6, 100
        )
        quedas = [e for e in eventos if e.tipo is TipoDeEvento.JOGO_CAIU]
        assert len(quedas) == 1
        assert quedas[0].detalhe == "tela de login"

    def test_desconexao_avisa_com_o_motivo_certo(self):
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 10)

        eventos = _alimentar(
            r, _obs(EstadoDoCliente.DESCONECTADO, ui=False, nomes=()), 6, 100
        )
        quedas = [e for e in eventos if e.tipo is TipoDeEvento.JOGO_CAIU]
        assert len(quedas) == 1
        assert quedas[0].detalhe == "desconectado do servidor"

    def test_avisa_uma_vez_so(self):
        """Meia hora de manutencao nao vira meia hora de mensagens."""
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 10)

        eventos = _alimentar(
            r, _obs(EstadoDoCliente.TELA_DE_LOGIN, ui=False, nomes=()), 300, 100
        )
        assert len([e for e in eventos if e.tipo is TipoDeEvento.JOGO_CAIU]) == 1

    def test_a_volta_avisa(self):
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 10)
        _alimentar(
            r, _obs(EstadoDoCliente.TELA_DE_LOGIN, ui=False, nomes=()), 10, 100
        )

        eventos = _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 10, 500)
        voltas = [e for e in eventos if e.tipo is TipoDeEvento.JOGO_VOLTOU]
        assert len(voltas) == 1

    def test_jogo_caido_nao_gera_evento_de_party(self):
        """O silencio passa a ter nome, e nada mais e inventado.

        Com o jogo caido a party window nao esta escondida: ela nao existe.
        Deixar as avaliacoes de party rodarem produziria "voce saiu da party"
        e "fulano saiu" a partir de uma tela de login.
        """
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 15)

        eventos = _alimentar(
            r, _obs(EstadoDoCliente.TELA_DE_LOGIN, ui=False, nomes=()), 200, 100
        )
        proibidos = {
            TipoDeEvento.SAIU,
            TipoDeEvento.VOCE_SEM_PARTY,
            TipoDeEvento.MORREU,
            TipoDeEvento.CEGUEIRA_LONGA,
        }
        vazou = [e.tipo.value for e in eventos if e.tipo in proibidos]
        assert vazou == [], f"o jogo caiu, mas vazou: {vazou}"

    def test_comeco_frio_com_o_jogo_ja_caido_nao_avisa(self):
        """Ligar o scanner com o jogo na tela de login nao e uma queda.

        O usuario esta olhando para a tela — ele sabe.
        """
        r = _novo()
        eventos = _alimentar(
            r, _obs(EstadoDoCliente.TELA_DE_LOGIN, ui=False, nomes=()), 20
        )
        assert [e for e in eventos if e.tipo is TipoDeEvento.JOGO_CAIU] == []

    def test_comeco_frio_nao_anuncia_volta_no_primeiro_login(self):
        """O espelho: sem queda anunciada, nao ha volta a anunciar."""
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.TELA_DE_LOGIN, ui=False, nomes=()), 20)

        eventos = _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 15, 100)
        assert [e for e in eventos if e.tipo is TipoDeEvento.JOGO_VOLTOU] == []

    def test_sem_o_sinal_o_comportamento_antigo_e_preservado(self):
        """Quem nao passa `estado_do_cliente` nao muda de comportamento."""
        r = _novo()
        obs_sem = Observacao(
            0,
            True,
            (
                LeituraDeLinha(
                    0, EstadoDaLinha.COM_MEMBRO, 1.0, 1.0, "Kaus", 0.98
                ),
            ),
            hp_proprio=1.0,
        )
        eventos = _alimentar(r, obs_sem, 20)
        do_cliente = [
            e
            for e in eventos
            if e.tipo in (TipoDeEvento.JOGO_CAIU, TipoDeEvento.JOGO_VOLTOU)
        ]
        assert do_cliente == []

    def test_desconhecido_congela_em_vez_de_concluir(self):
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 10)
        eventos = _alimentar(r, _obs(EstadoDoCliente.DESCONHECIDO), 50, 100)
        assert [e for e in eventos if e.tipo is TipoDeEvento.JOGO_CAIU] == []


class TestMensagens:
    def _ev(self, tipo, detalhe=None):
        return Evento(
            tipo=tipo, momento=1787600000.0, membro="Yazalaque", detalhe=detalhe
        )

    def test_whatsapp_diz_o_motivo(self):
        texto = formatar(self._ev(TipoDeEvento.JOGO_CAIU, "tela de login"))
        assert "tela de login" in texto
        assert "Yazalaque" in texto

    def test_whatsapp_distingue_desconexao_de_login(self):
        desc = formatar(
            self._ev(TipoDeEvento.JOGO_CAIU, "desconectado do servidor")
        )
        assert "desconectado do servidor" in desc
        assert "tela de login" not in desc

    def test_a_volta_tem_mensagem_propria(self):
        texto = formatar(self._ev(TipoDeEvento.JOGO_VOLTOU))
        assert "voltou" in texto.lower()

    def test_console_nao_cai_no_texto_generico(self):
        """Sem tratamento explicito sairia 'JOGO_CAIU', que nao ajuda ninguem."""
        linha = formatar_console(self._ev(TipoDeEvento.JOGO_CAIU, "tela de login"))
        assert "JOGO_CAIU" not in linha
        assert "TELA DE LOGIN" in linha
