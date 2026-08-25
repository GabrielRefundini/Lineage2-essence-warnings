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
        """UMA janela produz UMA mensagem, por mais longa que seja.

        A varredura para no fim da uniao Prime+TvT (22:05) de proposito: ir
        alem entraria na janela SEGUINTE, e ai duas mensagens seria o certo.
        Amarrar o teste ao fim da janela em vez de a um numero de minutos faz
        ele sobreviver a um horario novo no config.toml — foi exatamente o que
        aconteceu quando o TvT das 23:00 entrou.
        """
        from datetime import timedelta

        from tests.test_agenda import SEGUNDA

        c = self._controle(agenda)
        c.atualizar(SEGUNDA.replace(hour=19, minute=59))
        mensagens = []
        instante = SEGUNDA.replace(hour=20, minute=0)
        fim = SEGUNDA.replace(hour=22, minute=10)  # logo apos a uniao acabar
        while instante <= fim:
            m = c.atualizar(instante)
            if m:
                mensagens.append(m)
            instante += timedelta(minutes=1)
        assert len(mensagens) == 1, mensagens

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
        # A chamada agora ocupa varias linhas; olhar o bloco inteiro.
        assert "desenhar_status(" in fonte
        for trecho in fonte.split("desenhar_status(")[1:]:
            assert "silencio" in trecho[:200], (
                f"chamada sem silencio: {trecho[:120]!r}"
            )


class TestAgendaUsaOTempoDoFrame:
    """No replay, a agenda tem que usar o tempo GRAVADO, nao o relogio.

    O projeto ja aplicava essa disciplina ao rastreador, e o comentario no
    codigo explica por que: "num replay o tempo vem do arquivo, nao do relogio
    — e o que faz uma sessao de uma hora produzir os mesmos eventos ao ser
    reproduzida em trinta segundos".

    A agenda tinha nascido furando essa regra. Duas consequencias:

    - reproduzir uma sessao gravada durante um TvT NAO reproduziria o silencio
      daquele TvT, entao a pergunta "por que nao recebi alerta naquele horario"
      seria indepuravel offline;
    - reproduzir uma gravacao as 14h50 dispararia um aviso de TvT DE VERDADE no
      grupo, no meio de uma depuracao.
    """

    def test_o_nucleo_nao_usa_o_relogio_de_parede_para_a_agenda(self):
        """A regra mudou de casa com o refactor, mas continua valendo.

        O tick recebe `momento` do FRAME e deriva tudo dele. Se alguem chamar
        `datetime.now()` ali dentro, o replay para de reproduzir o silencio
        gravado — que e a razao de o replay existir.
        """
        import inspect

        from l2scanner import sessao as nucleo

        fonte = inspect.getsource(nucleo.Sessao)
        assert "datetime.now()" not in fonte, (
            "a Sessao passou a usar o relogio de parede"
        )
        assert "datetime.fromtimestamp(momento)" in fonte

    def test_o_tempo_da_agenda_e_o_MESMO_que_o_rastreador_recebe(self):
        """Um instante so, derivado do frame, para os dois."""
        import inspect

        from l2scanner import sessao as nucleo

        fonte = inspect.getsource(nucleo.Sessao.tick)
        assert "agora = datetime.fromtimestamp(momento)" in fonte
        assert "self.rastreador.observar(observacao, momento)" in fonte

    def test_o_modo_so_agenda_usa_o_relogio_mesmo(self):
        """La nao existe frame, entao o relogio e a unica fonte de tempo."""
        import inspect

        from l2scanner import __main__ as principal

        fonte = inspect.getsource(principal.laco_da_agenda)
        assert "agora = datetime.now()" in fonte


class TestCorrecoesDaRevisao:
    """Travas para os achados do code review de 2026-08-24.

    Os tres warnings eram todos de INTEGRACAO — coisas que os testes unitarios
    nao alcancam porque vivem no laco principal. Por isso estes testes leem a
    fonte: e a unica forma de afirmar ordem de execucao sem subir o scanner
    inteiro com um jogo aberto.
    """

    def _fonte(self, funcao):
        import inspect

        from l2scanner import __main__ as principal

        return inspect.getsource(getattr(principal, funcao))

    def test_a_agenda_roda_ANTES_da_extracao(self):
        """W-02. A agenda nao depende de um unico pixel.

        Se ficar depois do `try` da extracao, um erro de leitura faz o
        `continue` engolir o lembrete de TvT junto — o que contradiz a razao
        inteira de a agenda existir.
        """
        import inspect

        from l2scanner import sessao as nucleo

        fonte = inspect.getsource(nucleo.Sessao.tick)
        pos_agenda = fonte.index("self._processar_agenda(")
        pos_extracao = fonte.index("extrair(frame, self.cal)")
        assert pos_agenda < pos_extracao, (
            "a agenda voltou para depois da extracao; um erro de pixel passa a "
            "calar o lembrete de TvT"
        )

    def test_o_encerramento_e_logado_mesmo_sem_despachante(self):
        """W-03. Silencio que nao deveria existir.

        Quem roda sem .env e sem --dry-run perdia a mensagem ate no console.
        """
        fonte = self._fonte("laco_da_agenda")
        assert "if encerrou and despachante:" not in fonte, (
            "o `and despachante` cala o console tambem"
        )
        assert "if encerrou:" in fonte

    def test_o_resumo_mostra_quantos_foram_silenciados(self):
        """I-01. Depois de um TvT, 3 engolidos e 300 engolidos sao coisas bem
        diferentes — e essa diferenca e o sinal de que o silencio funcionou."""
        fonte = self._fonte("laco_principal")
        assert "despachante.silenciados" in fonte


class TestBuscaDoDialogoNaFaixaCentral:
    """W-01. Varrer a janela inteira custava 121 ms POR FRAME, medido.

    Sao 12% do orcamento de um tick a 1 Hz, gastos continuamente numa maquina
    que tambem roda dois clientes de Lineage 2, para procurar um evento que
    acontece uma vez por manutencao.

    O dialogo e modal e CENTRADO — medido, o centro dele cai exatamente no meio
    da janela.
    """

    def test_o_positivo_real_continua_casando(self):
        """A otimizacao nao pode custar a deteccao."""
        from pathlib import Path

        import cv2

        from l2scanner.cliente import carregar_template, casar_dialogo

        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "cliente"
            / "dialogo_desconexao_recorte.png"
        )
        recorte = cv2.imread(str(fixture))
        pontuacao = casar_dialogo(recorte, carregar_template())
        assert pontuacao is not None and pontuacao >= 0.99

    def test_janela_pequena_demais_cai_para_o_frame_inteiro(self):
        """Perder a deteccao e pior do que gastar o tempo."""
        import numpy as np

        from l2scanner.cliente import carregar_template, casar_dialogo

        template = carregar_template()
        altura, largura = template.shape[:2]
        # Cabe o template, mas a faixa central sozinha nao caberia.
        quadro = np.zeros((altura + 4, largura + 4, 3), dtype=np.uint8)
        assert casar_dialogo(quadro, template) is not None

    def test_a_faixa_cobre_com_folga_a_posicao_real_medida(self):
        """O template real ocupa x 0.41-0.59 e y 0.53-0.58 da janela."""
        from l2scanner.cliente import FAIXA_DO_DIALOGO

        fx0, fy0, fx1, fy1 = FAIXA_DO_DIALOGO
        assert fx0 <= 0.41 and fx1 >= 0.59, "a faixa horizontal corta o dialogo"
        assert fy0 <= 0.53 and fy1 >= 0.58, "a faixa vertical corta o dialogo"


class TestCancelarOSilencio:
    """O usuario pode cancelar o silencio de UMA ocorrencia.

    Pedido dele: "preciso de uma forma de cancelar o silenciamento da prime se
    eu quiser". O Prime cala por 2h, e nem todo dia ele vai fazer Prime.

    DOIS MOMENTOS, os dois pedidos explicitamente:
      - durante: a janela ja comecou e ele quer os alertas de volta agora
      - antes:   ele ja sabe que hoje nao vai, e marca para nem comecar
    """

    @pytest.fixture
    def agenda(self):
        from pathlib import Path

        from l2scanner.config import ler_agenda

        raiz = Path(__file__).resolve().parent.parent
        return ler_agenda(raiz / "config.toml")

    def _em(self, hora, minuto, dia=None):
        from tests.test_agenda import SEGUNDA

        return (dia or SEGUNDA).replace(hour=hora, minute=minuto)

    def test_cancelar_devolve_os_alertas_no_meio_da_janela(self, agenda):
        from l2scanner.agenda import chave_da_ocorrencia, silencio_ativo

        meio = self._em(20, 30)
        assert silencio_ativo(meio, agenda) is not None, "deveria estar calado"

        chave = chave_da_ocorrencia("Prime", self._em(20, 0))
        assert silencio_ativo(meio, agenda, {chave}) is None

    def test_cancelar_antes_impede_a_janela_de_comecar(self, agenda):
        from l2scanner.agenda import chave_da_ocorrencia, silencio_ativo

        chave = chave_da_ocorrencia("Prime", self._em(20, 0))
        # cancelado as 19h; as 20h30 o silencio nem existe
        assert silencio_ativo(self._em(20, 30), agenda, {chave}) is None

    def test_cancelar_o_prime_NAO_cala_o_tvt(self, agenda):
        """Cancelamento e por OCORRENCIA, nao por dia nem por tudo.

        As 21h55 o TvT das 21h50 esta rolando por conta propria. Cancelar o
        Prime nao pode levar o TvT junto.
        """
        from l2scanner.agenda import chave_da_ocorrencia, silencio_ativo

        chave = chave_da_ocorrencia("Prime", self._em(20, 0))
        janela = silencio_ativo(self._em(21, 55), agenda, {chave})
        assert janela is not None
        assert janela.evento == "TvT"
        assert janela.fim == self._em(22, 5)
        assert janela.inicio == self._em(21, 50), "a uniao ainda inclui o Prime"

    def test_cancelar_hoje_nao_afeta_amanha(self, agenda):
        from datetime import timedelta

        from tests.test_agenda import SEGUNDA

        from l2scanner.agenda import chave_da_ocorrencia, silencio_ativo

        chave = chave_da_ocorrencia("Prime", self._em(20, 0))
        terca = SEGUNDA + timedelta(days=1)
        assert silencio_ativo(self._em(20, 30, terca), agenda, {chave}) is not None

    def test_sem_cancelamento_o_comportamento_e_o_de_antes(self, agenda):
        from l2scanner.agenda import silencio_ativo

        assert silencio_ativo(self._em(20, 30), agenda) is not None
        assert silencio_ativo(self._em(20, 30), agenda, frozenset()) is not None


class TestOQueDaParaCancelar:
    """A lista que o gatilho usa para saber o que oferecer."""

    @pytest.fixture
    def agenda(self):
        from pathlib import Path

        from l2scanner.config import ler_agenda

        raiz = Path(__file__).resolve().parent.parent
        return ler_agenda(raiz / "config.toml")

    def _em(self, hora, minuto):
        from tests.test_agenda import SEGUNDA

        return SEGUNDA.replace(hour=hora, minute=minuto)

    def test_no_meio_do_prime_o_primeiro_e_o_prime_rolando(self, agenda):
        from l2scanner.agenda import ocorrencias_cancelaveis

        itens = ocorrencias_cancelaveis(self._em(20, 30), agenda)
        assert itens[0][0] == "Prime"
        assert itens[0][2] is True, "deveria estar marcado como ja rolando"

    def test_antes_do_prime_ele_aparece_como_futuro(self, agenda):
        from l2scanner.agenda import ocorrencias_cancelaveis

        itens = ocorrencias_cancelaveis(self._em(19, 0), agenda)
        nomes = [(n, rolando) for n, _, rolando in itens]
        assert ("Prime", False) in nomes

    def test_o_que_esta_rolando_vem_antes_do_que_ainda_vai_comecar(self, agenda):
        """O primeiro item e a escolha mais provavel de quem pede."""
        from l2scanner.agenda import ocorrencias_cancelaveis

        itens = ocorrencias_cancelaveis(self._em(20, 30), agenda)
        rolando = [i for i, x in enumerate(itens) if x[2]]
        futuros = [i for i, x in enumerate(itens) if not x[2]]
        if rolando and futuros:
            assert max(rolando) < min(futuros)

    def test_evento_distante_demais_nao_aparece(self, agenda):
        """Marcar as 10h que nao vai fazer o Prime das 20h e esquecimento.

        O cancelamento ficaria pendurado o dia inteiro sem ninguem lembrar.
        """
        from l2scanner.agenda import ocorrencias_cancelaveis

        itens = ocorrencias_cancelaveis(self._em(10, 0), agenda)
        assert all(n != "Prime" for n, _, _ in itens)

    def test_o_ja_cancelado_some_da_lista(self, agenda):
        from l2scanner.agenda import chave_da_ocorrencia, ocorrencias_cancelaveis

        chave = chave_da_ocorrencia("Prime", self._em(20, 0))
        itens = ocorrencias_cancelaveis(self._em(20, 30), agenda, {chave})
        assert all(n != "Prime" for n, _, _ in itens)

    def test_madrugada_sem_nada_por_perto_devolve_vazio(self, agenda):
        from l2scanner.agenda import ocorrencias_cancelaveis

        assert ocorrencias_cancelaveis(self._em(4, 0), agenda) == []
