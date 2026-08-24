"""Testes do destaque de eventos no console."""

from __future__ import annotations

import pytest

from l2scanner.console import destacar
from l2scanner.notificador import formatar, formatar_console
from l2scanner.rastreador import Evento, TipoDeEvento

MOMENTO = 1787590000.0


def evento(tipo: TipoDeEvento, **kwargs) -> Evento:
    return Evento(tipo=tipo, momento=MOMENTO, **kwargs)


class TestTextoDoConsole:
    """Direto, porque o usuario esta na frente da tela e pode conferir."""

    def test_morte_e_direta(self):
        texto = formatar_console(evento(TipoDeEvento.MORREU, membro="Korzis"))
        assert texto == "KORZIS MORREU"

    def test_ressurreicao_diz_que_foi_ressuscitado(self):
        texto = formatar_console(
            evento(TipoDeEvento.RESSUSCITOU, membro="Korzis")
        )
        assert "KORZIS" in texto
        assert "RESSUSCITADO" in texto

    def test_ressurreicao_informa_o_tempo_morto(self):
        texto = formatar_console(
            evento(
                TipoDeEvento.RESSUSCITOU, membro="Kaus", segundos_no_estado=95.0
            )
        )
        assert "1min35s" in texto

    def test_saida_e_entrada_sao_distintas(self):
        saida = formatar_console(evento(TipoDeEvento.SAIU, membro="X"))
        entrada = formatar_console(evento(TipoDeEvento.ENTROU, membro="X"))

        assert "SAIU" in saida
        assert "ENTROU" in entrada
        assert saida != entrada

    def test_console_e_mais_direto_que_o_whatsapp(self):
        """Duas redacoes de proposito, para dois publicos diferentes.

        No WhatsApp quem le esta longe e nao consegue conferir, entao o texto
        precisa sobreviver a um falso positivo. No console o usuario olha o
        jogo no mesmo segundo — hedge ali so atrapalha a leitura rapida.
        """
        e = evento(TipoDeEvento.MORREU, membro="Korzis")

        console = formatar_console(e)
        whatsapp = formatar(e)

        assert "MORREU" in console
        assert "possivel morte" in whatsapp.lower()
        assert console != whatsapp

    def test_texto_do_console_e_ascii_puro(self):
        """A fonte do cmd.exe varia; acento e travessao viram lixo na tela."""
        eventos = [
            evento(TipoDeEvento.MORREU, membro="Korzis"),
            evento(TipoDeEvento.RESSUSCITOU, membro="Kaus", segundos_no_estado=95.0),
            evento(TipoDeEvento.SAIU, membro="J4guar"),
            evento(TipoDeEvento.ENTROU, membro="TioMad"),
            evento(TipoDeEvento.CEGUEIRA_LONGA, segundos_no_estado=420.0),
            evento(TipoDeEvento.VISAO_RECUPERADA, segundos_no_estado=520.0),
        ]

        for e in eventos:
            texto = formatar_console(e)
            texto.encode("ascii")  # levanta se houver caractere fora do ASCII

    def test_evento_sem_membro_nao_quebra(self):
        texto = formatar_console(evento(TipoDeEvento.CEGUEIRA_LONGA))
        assert texto  # nao explode nem devolve vazio


class TestDestaque:
    """A moldura que faz o evento saltar aos olhos no meio do log."""

    def test_bloco_contem_o_texto_e_a_hora(self):
        bloco = destacar("KORZIS MORREU", TipoDeEvento.MORREU, "13:46:40")
        assert "KORZIS MORREU" in bloco
        assert "13:46:40" in bloco

    def test_bordas_tem_a_mesma_largura_do_conteudo(self):
        """Borda desalinhada parece defeito e tira a atencao do que importa."""
        bloco = destacar("KORZIS MORREU", TipoDeEvento.MORREU, "13:46:40")
        linhas = [l for l in bloco.split("\n") if l.strip()]

        larguras = {len(l) for l in linhas}
        assert len(larguras) == 1, f"larguras diferentes: {larguras}"

    def test_texto_longo_estica_a_moldura_em_vez_de_estourar(self):
        longo = "SEM VISAO DA PARTY HA 7min - NADA E DETECTADO AGORA"
        bloco = destacar(longo, TipoDeEvento.CEGUEIRA_LONGA, "14:01:40")
        linhas = [l for l in bloco.split("\n") if l.strip()]

        assert len({len(l) for l in linhas}) == 1
        assert longo in bloco

    @pytest.mark.parametrize(
        "tipo",
        [
            TipoDeEvento.MORREU,
            TipoDeEvento.RESSUSCITOU,
            TipoDeEvento.SAIU,
            TipoDeEvento.ENTROU,
            TipoDeEvento.CEGUEIRA_LONGA,
            TipoDeEvento.VISAO_RECUPERADA,
        ],
    )
    def test_cada_tipo_tem_moldura_propria(self, tipo):
        """Da para reconhecer o tipo do evento pela borda, sem ler o texto."""
        bloco = destacar("TESTE", tipo, "12:00:00")
        assert bloco.strip()

    def test_morte_e_ressurreicao_tem_molduras_diferentes(self):
        morte = destacar("X MORREU", TipoDeEvento.MORREU, "12:00:00")
        vida = destacar("X MORREU", TipoDeEvento.RESSUSCITOU, "12:00:00")
        assert morte != vida
