"""O silencio durante TvT e Prime.

NAO E CORRECAO DE BUG — E FILTRO DE RELEVANCIA. Os alertas durante um TvT sao
verdadeiros: as pessoas morreram mesmo. Eles so nao sao noticia, porque em
evento morre todo mundo o tempo todo.

Essa distincao decide onde o codigo mora. O corte fica no TRANSPORTE, depois do
rastreador ter decidido e registrado tudo normalmente. Silenciar na deteccao
corromperia o estado — quem morre e ressuscita durante o silencio precisa sair
do outro lado com o estado certo — e apagaria o log, que e a unica ferramenta
de depuracao pos-farm do projeto.
"""

from __future__ import annotations

import json

import pytest

from l2scanner.notificador import Categoria, Despachante, NotificadorEmMemoria


@pytest.fixture
def notificador():
    return NotificadorEmMemoria()


def _despachante(notificador, outbox=None, calado=False):
    d = Despachante(notificador, arquivo_outbox=outbox)
    d.em_silencio = lambda: calado
    return d


def _entregar(despachante):
    """Roda a fila ate o fim, sem thread, para o teste ser deterministico."""
    despachante.iniciar()
    despachante.encerrar()


class TestOCorteNoTransporte:
    def test_em_silencio_o_evento_do_scanner_nao_sai(self, notificador):
        d = _despachante(notificador, calado=True)
        d.despachar("Korzis: HP zerado — possivel morte na PT.")
        _entregar(d)
        assert notificador.enviados == []
        assert d.silenciados == 1

    def test_em_silencio_o_aviso_de_agenda_ATRAVESSA(self, notificador):
        """MUTE-05, e sem ele a funcionalidade se anula sozinha.

        De segunda a quinta o lembrete do TvT das 21h40 cai dentro do silencio
        do Prime (20:00-22:00). Se ele fosse silenciado junto, o usuario nunca
        receberia aviso do TvT das 21h50 em quatro dias da semana.
        """
        d = _despachante(notificador, calado=True)
        d.despachar("TvT comeca em 10 minutos, as 21:50.", Categoria.SEMPRE)
        _entregar(d)
        assert len(notificador.enviados) == 1

    def test_sem_silencio_tudo_passa_como_antes(self, notificador):
        d = _despachante(notificador, calado=False)
        d.despachar("Korzis: HP zerado.")
        d.despachar("TvT comecou agora.", Categoria.SEMPRE)
        _entregar(d)
        assert len(notificador.enviados) == 2
        assert d.silenciados == 0

    def test_o_padrao_e_NORMAL(self, notificador):
        """Quem nao pensa no assunto tem que ser silenciado, nao o contrario.

        Uma fonte de eventos nova que esqueca de declarar categoria deve cair
        no lado seguro: calada durante o evento.
        """
        d = _despachante(notificador, calado=True)
        d.despachar("qualquer coisa")
        _entregar(d)
        assert notificador.enviados == []


class TestSilencioNaoApagaORegistro:
    """MUTE-07: silencio e do WhatsApp, NUNCA do registro.

    Sem isto, um falso positivo que aconteca durante um TvT fica invisivel para
    sempre — e o projeto passou um dia inteiro cacando falso positivo pelo log.
    """

    def test_o_silenciado_nao_entra_no_outbox(self, notificador, tmp_path):
        """O outbox garante que nada se perca no caminho da REDE.

        Uma mensagem que decidimos nao enviar nao esta a caminho de lugar
        nenhum — ela esta no log, que e onde ela pertence.
        """
        outbox = tmp_path / "outbox.jsonl"
        d = _despachante(notificador, outbox=outbox, calado=True)
        d.despachar("Korzis morreu")
        _entregar(d)
        assert not outbox.exists() or outbox.read_text(encoding="utf-8") == ""

    def test_o_que_passa_continua_indo_para_o_outbox(self, notificador, tmp_path):
        outbox = tmp_path / "outbox.jsonl"
        d = _despachante(notificador, outbox=outbox, calado=False)
        d.despachar("Korzis morreu")
        _entregar(d)
        linhas = outbox.read_text(encoding="utf-8").strip().splitlines()
        assert len(linhas) == 1
        assert "Korzis" in json.loads(linhas[0])["texto"]


class TestControleDoSilencio:
    """A transicao para fora da janela e o que produz a mensagem de fim."""

    @pytest.fixture
    def agenda(self):
        from pathlib import Path

        from l2scanner.config import ler_agenda

        raiz = Path(__file__).resolve().parent.parent
        return ler_agenda(raiz / "config.toml")

    def _controle(self, agenda):
        from l2scanner.__main__ import ControleDoSilencio

        return ControleDoSilencio(agenda)

    def test_atravessar_a_janela_produz_uma_mensagem(self, agenda):
        from datetime import timedelta

        from tests.test_agenda import SEGUNDA

        c = self._controle(agenda)
        mensagens = []
        instante = SEGUNDA.replace(hour=14, minute=50)
        for _ in range(60):
            m = c.atualizar(instante)
            if m:
                mensagens.append(m)
            instante += timedelta(minutes=1)

        assert len(mensagens) == 1, mensagens
        assert "TvT" in mensagens[0]

    def test_ficar_em_silencio_nao_repete_a_mensagem(self, agenda):
        from datetime import timedelta

        from tests.test_agenda import SEGUNDA

        c = self._controle(agenda)
        c.atualizar(SEGUNDA.replace(hour=19, minute=59))
        mensagens = []
        instante = SEGUNDA.replace(hour=20, minute=0)
        for _ in range(200):  # atravessa a janela inteira do Prime + TvT
            m = c.atualizar(instante)
            if m:
                mensagens.append(m)
            instante += timedelta(minutes=1)
        assert len(mensagens) == 1

    def test_a_mensagem_nomeia_quem_terminou_por_ultimo(self, agenda):
        """Seg-qui a uniao termina as 22:05, e quem estava rolando era o TvT."""
        from datetime import timedelta

        from tests.test_agenda import SEGUNDA

        c = self._controle(agenda)
        mensagens = []
        instante = SEGUNDA.replace(hour=19, minute=59)
        for _ in range(140):
            m = c.atualizar(instante)
            if m:
                mensagens.append(m)
            instante += timedelta(minutes=1)

        assert len(mensagens) == 1
        assert "TvT" in mensagens[0], "nomeou o Prime, que acabou as 22:00"

    def test_comeco_frio_dentro_da_janela_nao_anuncia_encerramento(self, agenda):
        """O scanner nunca viu esse evento comecar.

        Anunciar o fim de algo que nao acompanhou seria inventar contexto.
        """
        from datetime import timedelta

        from tests.test_agenda import SEGUNDA

        c = self._controle(agenda)
        mensagens = []
        instante = SEGUNDA.replace(hour=15, minute=5)  # ja dentro do TvT
        for _ in range(30):
            m = c.atualizar(instante)
            if m:
                mensagens.append(m)
            instante += timedelta(minutes=1)
        assert mensagens == []

    def test_o_texto_nao_promete_convidar_ninguem(self, agenda):
        """Restricao dura: o scanner e somente leitura, nunca envia input."""
        from datetime import timedelta

        from tests.test_agenda import SEGUNDA

        c = self._controle(agenda)
        texto = None
        instante = SEGUNDA.replace(hour=14, minute=50)
        for _ in range(40):
            m = c.atualizar(instante)
            if m:
                texto = m
            instante += timedelta(minutes=1)

        assert texto is not None
        assert "reenviados" in texto
        for proibido in ("vou convidar", "convidando", "enviando convite"):
            assert proibido not in texto.lower()


class TestConsoleDoSilencio:
    """MUTE-08: um scanner calado precisa PARECER calado de proposito.

    Sem isto, "nao chegou nada no WhatsApp" e ambiguo entre "esta tudo bem",
    "estou em silencio de TvT" e "o scanner quebrou". Depois de um dia inteiro
    corrigindo alarme falso, a ambiguidade custa a confianca inteira.
    """

    def _status(self, silencio):
        from l2scanner.__main__ import desenhar_status
        from l2scanner.calibracao import Calibracao
        from l2scanner.rastreador import Rastreador
        from l2scanner.visao import Observacao

        obs = Observacao(0, True, ())
        cal = Calibracao.__new__(Calibracao)
        return desenhar_status(Rastreador(), cal, obs, silencio)

    def test_em_silencio_o_console_diz_ate_quando(self):
        from datetime import datetime

        from l2scanner.__main__ import ControleDoSilencio
        from l2scanner.agenda import JanelaDeSilencio

        controle = ControleDoSilencio([])
        controle._janela = JanelaDeSilencio(
            "TvT", datetime(2026, 8, 24, 21, 50), datetime(2026, 8, 24, 22, 5)
        )
        texto = self._status(controle)
        assert "SILENCIO DE TVT" in texto
        assert "22:05" in texto

    def test_sem_silencio_o_console_nao_menciona_nada(self):
        from l2scanner.__main__ import ControleDoSilencio

        assert "SILENCIO" not in self._status(ControleDoSilencio([]))

    def test_status_sem_silencio_algum_continua_funcionando(self):
        """Compatibilidade: quem chama sem o parametro nao quebra."""
        assert "SILENCIO" not in self._status(None)

    def test_o_status_ao_vivo_recebe_o_silencio(self):
        """A linha que aparece a cada 30s durante o farm.

        E a que o usuario realmente le. Se so o 'estado final' mostrasse o
        silencio, ele so descobriria o motivo depois de encerrar o scanner.
        """
        import inspect

        from l2scanner import __main__ as principal

        fonte = inspect.getsource(principal.laco_principal)
        chamadas = [
            linha for linha in fonte.splitlines() if "desenhar_status(" in linha
        ]
        assert chamadas, "nenhuma chamada encontrada"
        for chamada in chamadas:
            assert "silencio" in chamada, f"sem silencio: {chamada.strip()}"
