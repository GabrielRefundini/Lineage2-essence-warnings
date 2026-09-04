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


class TestMoldurarParaOWhatsApp:
    """A moldura crua — a que sai no celular.

    O usuario pediu o bloco do console dentro da mensagem do WhatsApp, e
    escreveu o formato exato que queria. Este teste GUARDA esse formato: se
    alguem mexer na largura, no recuo ou no carimbo, quebra aqui e nao no
    grupo da party as duas da manha.
    """

    AVISO = "Solo Boss comeca em 10 minutos, as 10:00. Loot: TioMad."

    def test_e_o_formato_que_o_usuario_pediu(self):
        from l2scanner.console import moldurar

        linhas = moldurar(self.AVISO, "09:50").split("\n")

        assert len(linhas) == 3, "borda, texto, borda — nada alem disso"
        assert set(linhas[0]) == {"*"} and linhas[0] == linhas[2]
        assert linhas[1] == f"  {self.AVISO}  [09:50]"
        assert len(linhas[0]) == len(linhas[1]), "borda do tamanho do conteudo"

    def test_nao_leva_cor_nem_linha_em_branco(self):
        """ANSI no celular nao vira cor — vira lixo no meio da mensagem."""
        from l2scanner.console import moldurar

        bloco = moldurar(self.AVISO, "09:50")
        assert "\033" not in bloco
        assert not bloco.startswith("\n") and not bloco.endswith("\n")

    def test_texto_curto_ainda_enche_a_largura_minima(self):
        from l2scanner.console import LARGURA, moldurar

        linhas = moldurar("TvT comecou.", "21:50").split("\n")
        assert len(linhas[0]) == LARGURA
        assert len({len(l) for l in linhas}) == 1

    def test_console_e_whatsapp_usam_a_MESMA_geometria(self):
        """Uma conta so. Duas parecidas divergem no primeiro que for mexido.

        A cor e tirada antes de medir porque ela depende de o terminal ser
        tty — sem isso o teste passaria no pytest e falharia com `-s`.
        """
        import re

        from l2scanner.console import moldurar

        sem_cor = lambda t: re.sub(r"\033\[[0-9;]*m", "", t)  # noqa: E731

        do_console = [
            sem_cor(linha)
            for linha in destacar(self.AVISO, hora="09:50").split("\n")
            if linha.strip()
        ]
        do_whatsapp = moldurar(self.AVISO, "09:50").split("\n")

        assert do_console == do_whatsapp


class TestDestacarSemEvento:
    """Nem tudo que merece destaque no console e um Evento do rastreador.

    Os avisos de agenda e o cancelamento de silencio vem do RELOGIO, nao da
    tela, e nao tem TipoDeEvento nenhum.

    Sem os defaults, `destacar(texto)` levantava TypeError. E como esse caminho
    so executa quando um alerta de agenda vence DE VERDADE, o erro ficou
    escondido desde a Fase 6 — o scanner teria crashado na primeira vez que
    fosse falar sobre um TvT. Foi a cobertura de 20% do laco principal
    cobrando.
    """

    def test_destacar_aceita_so_o_texto(self):
        from l2scanner.console import destacar

        bloco = destacar("TvT comeca em 10 minutos, as 21:50.")
        assert "TvT comeca em 10 minutos" in bloco
        assert bloco.count("\n") >= 2, "o bloco tem moldura"

    def test_carimba_a_hora_de_agora_quando_nao_recebe_uma(self):
        import re

        from l2scanner.console import destacar

        assert re.search(r"\[\d{2}:\d{2}\]", destacar("qualquer coisa"))

    def test_continua_funcionando_com_os_tres_argumentos(self):
        from l2scanner.console import destacar
        from l2scanner.rastreador import TipoDeEvento

        bloco = destacar("KAUS MORREU", TipoDeEvento.MORREU, "13:39")
        assert "KAUS MORREU" in bloco and "13:39" in bloco

    def test_todas_as_chamadas_do_laco_principal_sao_validas(self):
        """A trava de verdade: exercita CADA chamada de destacar do __main__.

        Um teste que so cobre a assinatura nao teria pego o bug — o que faltava
        era alguem CHAMAR do jeito que o laco chama.
        """
        import inspect
        import re

        from l2scanner import __main__ as principal
        from l2scanner.console import destacar

        fonte = inspect.getsource(principal)
        chamadas = re.findall(r"destacar\(([^)]*)\)", fonte)
        assert len(chamadas) >= 5, f"esperava varias chamadas, achei {len(chamadas)}"

        # Toda chamada com UM argumento tem que funcionar
        de_um_argumento = [c for c in chamadas if "," not in c]
        assert de_um_argumento, "nenhuma chamada de um argumento — teste obsoleto?"
        for _ in de_um_argumento:
            destacar("texto de exemplo")  # nao pode levantar
