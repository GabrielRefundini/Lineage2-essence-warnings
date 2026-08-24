"""Testes da entrega — texto das mensagens, retentativa e durabilidade."""

from __future__ import annotations

import json
import time

import pytest

from l2scanner.notificador import (
    Despachante,
    ErroDeEntrega,
    NotificadorEmMemoria,
    formatar,
)
from l2scanner.rastreador import Evento, TipoDeEvento

MOMENTO = 1787583219.0  # 2026-08-24, horario fixo para o texto ser estavel


def evento(tipo: TipoDeEvento, **kwargs) -> Evento:
    return Evento(tipo=tipo, momento=MOMENTO, **kwargs)


class TestTextoDoAlerta:
    """O que chega no celular de quem esta AFK."""

    def test_morte_e_fraseada_para_sobreviver_a_falso_positivo(self):
        """"MORREU" nao sobrevive a um erro; "possivel morte" sobrevive.

        O scanner le pixels, nao le a verdade. O texto precisa ser honesto
        sobre isso, senao o primeiro falso positivo destroi a confianca em
        todos os alertas seguintes.
        """
        texto = formatar(evento(TipoDeEvento.MORREU, membro="Korzis"))

        assert "Korzis" in texto
        assert "possivel morte" in texto.lower()
        assert "MORREU" not in texto

    def test_alerta_sempre_nomeia_o_membro(self):
        """Alerta anonimo e inacionavel: nao da para socorrer "alguem"."""
        for tipo in (
            TipoDeEvento.MORREU,
            TipoDeEvento.RESSUSCITOU,
            TipoDeEvento.SAIU,
            TipoDeEvento.ENTROU,
        ):
            texto = formatar(evento(tipo, membro="TioMad"))
            assert "TioMad" in texto

    def test_alerta_traz_horario_local(self):
        texto = formatar(evento(TipoDeEvento.MORREU, membro="Kaus"))
        assert ":" in texto and texto.startswith("[")

    def test_ressurreicao_informa_quanto_tempo_ficou_morto(self):
        texto = formatar(
            evento(
                TipoDeEvento.RESSUSCITOU, membro="Kaus", segundos_no_estado=125.0
            )
        )
        assert "2min" in texto

    def test_saida_e_distinta_de_morte(self):
        morte = formatar(evento(TipoDeEvento.MORREU, membro="X"))
        saida = formatar(evento(TipoDeEvento.SAIU, membro="X"))
        assert morte != saida
        assert "saiu" in saida.lower()

    def test_cegueira_longa_explica_a_consequencia(self):
        """O usuario precisa entender que ficou descoberto, nao so que 'algo'."""
        texto = formatar(
            evento(TipoDeEvento.CEGUEIRA_LONGA, segundos_no_estado=420.0)
        )
        assert "7min" in texto
        assert "nao serao detectados" in texto.lower()

    def test_volta_da_cegueira_admite_o_buraco(self):
        texto = formatar(
            evento(TipoDeEvento.VISAO_RECUPERADA, segundos_no_estado=480.0)
        )
        assert "8min" in texto
        assert "perdido" in texto.lower()

    @pytest.mark.parametrize(
        "segundos,esperado",
        [(5, "5s"), (59, "59s"), (60, "1min"), (125, "2min"), (3600, "1h00")],
    )
    def test_duracoes_legiveis(self, segundos, esperado):
        texto = formatar(
            evento(
                TipoDeEvento.RESSUSCITOU, membro="X", segundos_no_estado=segundos
            )
        )
        assert esperado in texto


class _NotificadorQueFalha:
    """Falha as N primeiras vezes, depois entrega."""

    def __init__(self, falhas: int, transitorio: bool = True) -> None:
        self.restantes = falhas
        self.transitorio = transitorio
        self.tentativas = 0
        self.entregues: list[str] = []

    def enviar(self, texto: str) -> None:
        self.tentativas += 1
        if self.restantes > 0:
            self.restantes -= 1
            raise ErroDeEntrega("simulado", transitorio=self.transitorio)
        self.entregues.append(texto)


def drenar(despachante: Despachante, limite: float = 15.0) -> None:
    fim = time.monotonic() + limite
    while (
        despachante.entregues + despachante.falhados == 0
        and time.monotonic() < fim
    ):
        time.sleep(0.05)
    despachante.encerrar(espera_maxima=2.0)


class TestDespachante:
    def test_entrega_o_que_foi_despachado(self):
        notificador = NotificadorEmMemoria()
        d = Despachante(notificador)
        d.iniciar()

        d.despachar("Korzis: HP zerado")
        drenar(d)

        assert notificador.enviados == ["Korzis: HP zerado"]

    def test_grava_no_outbox_antes_de_tentar_a_rede(self, tmp_path):
        """Queda de conexao nao pode apagar o registro de que alguem morreu."""
        outbox = tmp_path / "outbox.jsonl"

        # notificador que sempre falha: mesmo assim o registro tem que existir
        d = Despachante(_NotificadorQueFalha(99), arquivo_outbox=outbox)
        d.despachar("Kaus: HP zerado")  # sem iniciar a thread de proposito

        assert outbox.exists()
        registro = json.loads(outbox.read_text(encoding="utf-8").strip())
        assert registro["texto"] == "Kaus: HP zerado"

    def test_falha_transitoria_e_retentada(self):
        notificador = _NotificadorQueFalha(falhas=2, transitorio=True)
        d = Despachante(notificador)
        d.iniciar()

        d.despachar("teste")
        drenar(d)

        assert notificador.entregues == ["teste"]
        assert notificador.tentativas == 3

    def test_erro_definitivo_nao_e_retentado(self):
        """4xx e culpa nossa: token errado, conversa inexistente.

        Repetir so gasta tentativa e atrasa os alertas seguintes na fila.
        """
        notificador = _NotificadorQueFalha(falhas=99, transitorio=False)
        falhas = []
        d = Despachante(notificador, ao_falhar=lambda t, e: falhas.append((t, e)))
        d.iniciar()

        d.despachar("teste")
        drenar(d)

        assert notificador.tentativas == 1
        assert len(falhas) == 1

    def test_falha_de_entrega_e_reportada_nunca_silenciosa(self):
        """Entrega que falha calada e pior do que nao ter ferramenta."""
        falhas = []
        d = Despachante(
            _NotificadorQueFalha(falhas=99, transitorio=False),
            ao_falhar=lambda texto, erro: falhas.append((texto, erro)),
        )
        d.iniciar()

        d.despachar("Korzis: HP zerado")
        drenar(d)

        assert len(falhas) == 1
        assert "Korzis" in falhas[0][0]

    def test_desiste_apos_o_teto_de_tentativas(self):
        notificador = _NotificadorQueFalha(falhas=99, transitorio=True)
        falhas = []
        d = Despachante(notificador, ao_falhar=lambda t, e: falhas.append(e))
        d.iniciar()

        d.despachar("teste")
        drenar(d, limite=40.0)

        assert d.falhados == 1
        assert notificador.tentativas <= 4

    def test_notificador_que_explode_nao_derruba_o_despachante(self):
        class Explosivo:
            def enviar(self, texto):
                raise RuntimeError("boom")

        falhas = []
        d = Despachante(Explosivo(), ao_falhar=lambda t, e: falhas.append(e))
        d.iniciar()

        d.despachar("teste")
        drenar(d)

        assert len(falhas) == 1


class TestModoSimulacao:
    def test_simulacao_nao_envia_nada_de_verdade(self):
        """`--dry-run` troca o adaptador, nao espalha `if` pelo codigo."""
        saida = []
        from l2scanner.notificador import NotificadorDeConsole

        NotificadorDeConsole(escrever=saida.append).enviar("Korzis: HP zerado")

        assert len(saida) == 1
        assert "simulacao" in saida[0]
        assert "Korzis" in saida[0]
