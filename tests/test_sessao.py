"""O tick, agora testavel — e os tres bugs de producao como regressao.

Este arquivo existe por causa de uma medicao: `__main__.py` estava em 20% de
cobertura contra 98% do `rastreador`, e TODOS os bugs de integracao deste
projeto moraram la. Tres chegaram em producao no mesmo dia, e nenhum dos 420
testes os viu — porque nenhum teste chamava o laco.

Agora chama.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.agenda import EventoAgendado, RegistroEmDisco
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.notificador import Categoria
from l2scanner.rastreador import Rastreador
from l2scanner.sessao import Sessao

SEGUNDA = datetime(2026, 8, 24)
FIXTURES = Path(__file__).parent / "fixtures" / "party_estavel_com_vazamento"


class SilencioFalso:
    """Controla quando a janela abre e fecha, sem depender do relogio."""

    def __init__(self, encerra_em=None):
        self.janela = None
        self._encerra_em = encerra_em

    def ativo(self):
        return self.janela is not None

    def atualizar(self, agora):
        if self._encerra_em and agora >= self._encerra_em:
            self._encerra_em = None
            return "TvT encerrado. Voltei a vigiar."
        return None


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


def nova_sessao(
    calibracao,
    tmp_path,
    eventos=(),
    silencio=None,
    despachante=None,
    loot=None,
    manutencao=None,
):
    return Sessao(
        cal=calibracao,
        rastreador=Rastreador(nomes=list(calibracao.nomes)),
        eventos_agendados=list(eventos),
        registro=RegistroEmDisco(tmp_path),
        silencio=silencio or SilencioFalso(),
        despachante=despachante,
        loot=loot,
        manutencao=manutencao,
    )


def em(hora, minuto):
    return SEGUNDA.replace(hour=hora, minute=minuto).timestamp()


class TestTickBasico:
    def test_um_frame_real_produz_observacao(self, calibracao, frame_real, tmp_path):
        s = nova_sessao(calibracao, tmp_path)
        r = s.tick(frame_real, momento=em(12, 0))
        assert r.observacao is not None
        assert not r.falhou_ao_analisar

    def test_frame_degenerado_vira_CEGUEIRA_e_nao_excecao(
        self, calibracao, tmp_path
    ):
        """Um frame de 1x1 preto nao lanca — e nao deveria mesmo.

        A `visao` trata e devolve `ui_visivel=False`, que e o comportamento
        certo: frame doente vira cegueira, nunca "todas as barras vazias", que
        seria um alerta de wipe total que nunca aconteceu.
        """
        s = nova_sessao(calibracao, tmp_path)
        ruim = Frame(
            pixels=np.zeros((1, 1, 3), np.uint8), indice=0, saude=SaudeDoFrame.OK
        )

        r = s.tick(ruim, momento=em(12, 0))

        assert not r.falhou_ao_analisar
        assert r.observacao is not None and not r.observacao.ui_visivel
        assert r.eventos == [], "frame degenerado nao pode gerar evento"

    def test_excecao_na_analise_e_reportada_sem_derrubar(
        self, calibracao, frame_real, tmp_path
    ):
        """Quando a analise REALMENTE explode, o tick reporta e segue.

        Um scanner que morre calado e pior do que nenhum scanner.
        """
        s = nova_sessao(calibracao, tmp_path)

        class RastreadorExplosivo:
            portao = None

            def observar(self, *_):
                raise RuntimeError("boom")

        s.rastreador = RastreadorExplosivo()

        r = s.tick(frame_real, momento=em(12, 0))

        assert r.falhou_ao_analisar
        assert r.eventos == []

    def test_a_saude_do_frame_e_contabilizada(self, calibracao, frame_real, tmp_path):
        s = nova_sessao(calibracao, tmp_path)
        s.tick(frame_real, momento=em(12, 0))
        assert s.contagem[SaudeDoFrame.OK] == 1

    def test_ticks_cego_conta(self, calibracao, tmp_path):
        s = nova_sessao(calibracao, tmp_path)
        cego = Frame(
            pixels=np.zeros((200, 200, 3), np.uint8),
            indice=0,
            saude=SaudeDoFrame.FALHA_DE_CAPTURA,
        )
        for _ in range(3):
            s.tick(cego, momento=em(12, 0))
        assert s.ticks_cego == 3


class TestReconhecimentoParadoFicaVisivel:
    """Enxergar a linha e nao saber quem esta nela era invisivel para o scanner.

    Ele sempre soube contar cegueira de CAPTURA (`ticks_cego`) e reclamar dela.
    Nunca soube contar "estou vendo a linha ha dois minutos e nao faco ideia de
    quem esta nela" — e em 2026-08-25 isso durou DUAS HORAS
    (logs/scanner.log 10:03:24 a 11:59), atravessando ate um reinicio do
    scanner as 10:46:57, sem uma palavra no log.

    O custo nao foi so estetico: pela limitacao travada em
    `test_saida_de_quem_ja_estava_fora_do_reconhecimento_passa_calada`, quem
    aparece como "Membro N" nao gera aviso ao sair. Reconhecimento parado em
    silencio vira saida real passando calada — exatamente o evento que o projeto
    existe para anunciar.

    A causa daquele caso especifico (a coroa do lider) esta corrigida em
    `identidade.py`. Este contador e a rede para a PROXIMA causa, a que ninguem
    previu.
    """

    def sem_o_nome(self, pixels, cal, indice):
        """Apaga so o recorte do nome: a linha continua OCUPADA, mas sem nome.

        O icone e a barra ficam intactos, entao `EstadoDaLinha` continua
        COM_MEMBRO — que e exatamente a situacao real: a pessoa esta la, o
        scanner e que nao sabe quem e.
        """
        r = cal.regiao_do_nome(indice)
        sujo = pixels.copy()
        sujo[r.topo : r.topo + r.altura, r.esquerda : r.esquerda + r.largura] = 20
        return sujo

    def test_linha_ocupada_e_sem_nome_e_contada(
        self, calibracao, frame_real, tmp_path
    ):
        s = nova_sessao(calibracao, tmp_path)
        apagada = Frame(
            pixels=self.sem_o_nome(frame_real.pixels, calibracao, 0),
            indice=0,
            saude=SaudeDoFrame.OK,
        )

        for _ in range(5):
            s.tick(apagada, momento=em(12, 0))

        assert s.ticks_sem_reconhecer[0] == 5

    def test_reconhecer_de_novo_zera_a_conta(
        self, calibracao, frame_real, tmp_path
    ):
        """A piscada e normal e nao pode acumular ate virar aviso."""
        s = nova_sessao(calibracao, tmp_path)
        apagada = Frame(
            pixels=self.sem_o_nome(frame_real.pixels, calibracao, 0),
            indice=0,
            saude=SaudeDoFrame.OK,
        )

        for _ in range(4):
            s.tick(apagada, momento=em(12, 0))
        assert s.ticks_sem_reconhecer[0] == 4

        s.tick(frame_real, momento=em(12, 0))

        assert 0 not in s.ticks_sem_reconhecer

    def test_a_conta_e_por_linha(self, calibracao, frame_real, tmp_path):
        """Uma linha piscando nao pode zerar a conta de outra parada de verdade.

        Foi por isso que o contador nao e global: no caso real de 2026-08-25 as
        linhas 2/3/4 piscavam o tempo todo enquanto a linha 1 estava morta ha
        duas horas. Um contador global reiniciaria a cada piscada das outras e
        nunca chegaria ao aviso.
        """
        s = nova_sessao(calibracao, tmp_path)
        so_a_zero = Frame(
            pixels=self.sem_o_nome(frame_real.pixels, calibracao, 0),
            indice=0,
            saude=SaudeDoFrame.OK,
        )
        as_duas = Frame(
            pixels=self.sem_o_nome(
                self.sem_o_nome(frame_real.pixels, calibracao, 0), calibracao, 1
            ),
            indice=0,
            saude=SaudeDoFrame.OK,
        )

        s.tick(as_duas, momento=em(12, 0))
        s.tick(as_duas, momento=em(12, 0))
        s.tick(so_a_zero, momento=em(12, 0))  # a linha 1 voltou

        assert s.ticks_sem_reconhecer[0] == 3
        assert 1 not in s.ticks_sem_reconhecer

    def test_party_window_coberta_nao_conta_como_falha_de_reconhecimento(
        self, tmp_path
    ):
        """Propriedade 3 do rastreador, valendo aqui tambem.

        A party window coberta pelo inventario e o caso perigoso, e nao o frame
        preto: ela produz linhas OCUPADAS e SEM NOME — os pixels de "reconheci
        nada" — com `ui_visivel` False. Contar isso encheria o contador durante
        qualquer alt-tab com o inventario aberto e acabaria pedindo recalibracao
        por causa de uma janela na frente.

        Que e exatamente a confusao entre mudanca de VISAO e mudanca de
        REALIDADE que esta familia inteira de bugs vem cometendo.
        """
        pasta = Path(__file__).parent / "fixtures" / "sessao_morte_e_ressurreicao"
        cal = Calibracao.carregar(pasta / "calibracao.json")
        s = nova_sessao(cal, tmp_path)

        vivo = Frame(
            pixels=cv2.imread(str(pasta / "vivo.png")),
            indice=0,
            saude=SaudeDoFrame.OK,
        )
        coberta = Frame(
            pixels=cv2.imread(str(pasta / "coberta_por_inventario.png")),
            indice=1,
            saude=SaudeDoFrame.OK,
        )

        obs = s.tick(coberta, momento=em(12, 0)).observacao
        assert not obs.ui_visivel and obs.membros_presentes > 0, (
            "a fixture precisa ser cegueira COM linhas ocupadas — se ela virar "
            "um frame sem linhas, este teste para de testar o que promete"
        )

        s.tick(vivo, momento=em(12, 0))
        antes = dict(s.ticks_sem_reconhecer)
        for _ in range(10):
            s.tick(coberta, momento=em(12, 0))

        assert s.ticks_sem_reconhecer == antes, (
            "a cegueira nao pode somar nem zerar a conta de reconhecimento"
        )

    def test_frame_ilegivel_tambem_congela(self, calibracao, frame_real, tmp_path):
        s = nova_sessao(calibracao, tmp_path)
        apagada = Frame(
            pixels=self.sem_o_nome(frame_real.pixels, calibracao, 0),
            indice=0,
            saude=SaudeDoFrame.OK,
        )
        cego = Frame(
            pixels=np.zeros((200, 200, 3), np.uint8),
            indice=0,
            saude=SaudeDoFrame.FALHA_DE_CAPTURA,
        )

        for _ in range(3):
            s.tick(apagada, momento=em(12, 0))
        for _ in range(10):
            s.tick(cego, momento=em(12, 0))

        assert s.ticks_sem_reconhecer[0] == 3, "a cegueira nao pode somar nem zerar"

    def test_party_toda_reconhecida_nao_conta_nada(
        self, calibracao, frame_real, tmp_path
    ):
        s = nova_sessao(calibracao, tmp_path)

        for _ in range(5):
            s.tick(frame_real, momento=em(12, 0))

        reconhecidos = [
            linha.indice
            for linha in s.ultima_observacao.linhas
            if linha.nome is not None
        ]
        assert reconhecidos, "a fixture precisa reconhecer alguem"
        for indice in reconhecidos:
            assert indice not in s.ticks_sem_reconhecer


class TestBug1DestacarComUmArgumento:
    """`destacar(texto)` numa funcao de tres parametros.

    O scanner morreria no instante em que fosse falar sobre um TvT. E o
    marcador "ja avisei" e gravado ANTES do destacar, entao o aviso sumiria em
    silencio: nem sairia, nem seria reenviado.

    Um tick que dispara aviso de agenda pega isso.
    """

    def test_um_aviso_de_agenda_nao_derruba_o_tick(
        self, calibracao, frame_real, tmp_path
    ):
        tvt = EventoAgendado(nome="TvT", horarios=((15, 0),), avisar_minutos_antes=10)
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])

        r = s.tick(frame_real, momento=em(14, 50))

        assert r.avisos, "o aviso das 14:50 nao saiu"
        assert "TvT" in r.avisos[0]

    def test_o_aviso_sai_com_categoria_SEMPRE(self, calibracao, frame_real, tmp_path):
        """Se sair como NORMAL, o silencio engole o lembrete."""
        tvt = EventoAgendado(nome="TvT", horarios=((15, 0),), avisar_minutos_antes=10)
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])

        r = s.tick(frame_real, momento=em(14, 50))

        assert Categoria.SEMPRE in [c for _, c, _ in r.despachos]


class TestBug2DoisRelogios:
    """Um parametro `agora` usado para dois relogios incompativeis.

    `TypeError` no SEGUNDO tick — o primeiro passava porque a comparacao nem
    acontecia. Um teste de uma chamada so nao pegaria.
    """

    def test_muitos_ticks_seguidos_com_os_tipos_reais(
        self, calibracao, frame_real, tmp_path
    ):
        tvt = EventoAgendado(nome="TvT", horarios=((15, 0),))
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])

        base = em(14, 48)
        for i in range(30):  # trinta ticks, nao um
            s.tick(frame_real, momento=base + i)

    def test_o_aviso_sai_uma_vez_so_em_muitos_ticks(
        self, calibracao, frame_real, tmp_path
    ):
        """O marcador duravel tem que valer entre ticks."""
        tvt = EventoAgendado(nome="TvT", horarios=((15, 0),), avisar_minutos_antes=10)
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])

        avisos = []
        for i in range(60):
            avisos.extend(s.tick(frame_real, momento=em(14, 50) + i).avisos)

        antes = [a for a in avisos if "10 minutos" in a]
        assert len(antes) == 1, f"o aviso saiu {len(antes)} vezes"


class TestBug3DestinoDoDespacho:
    """Toda saida passa por um ponto so, e o resultado diz ONDE foi.

    Com o despacho espalhado por cinco lugares do laco, cada um podia errar o
    destino sozinho — e um errou: o `.status` respondia no grupo em vez de
    responder a quem perguntou.
    """

    def test_o_resultado_registra_o_destino_de_cada_despacho(
        self, calibracao, frame_real, tmp_path
    ):
        tvt = EventoAgendado(nome="TvT", horarios=((15, 0),), avisar_minutos_antes=10)
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])

        r = s.tick(frame_real, momento=em(14, 50))

        assert r.despachos
        for texto, categoria, alvo in r.despachos:
            assert isinstance(texto, str)
            assert isinstance(categoria, Categoria)
            assert alvo is None or isinstance(alvo, str)

    def test_aviso_de_agenda_vai_para_as_conversas_de_aviso(
        self, calibracao, frame_real, tmp_path
    ):
        """Alvo None = destinos de aviso. Um lembrete de TvT e para o grupo."""
        tvt = EventoAgendado(nome="TvT", horarios=((15, 0),), avisar_minutos_antes=10)
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])

        r = s.tick(frame_real, momento=em(14, 50))

        assert all(alvo is None for _, _, alvo in r.despachos)


class TestFimDoSilencio:
    def test_o_encerramento_sai_com_categoria_SEMPRE(
        self, calibracao, frame_real, tmp_path
    ):
        quando = SEGUNDA.replace(hour=15, minute=15)
        s = nova_sessao(
            calibracao, tmp_path, silencio=SilencioFalso(encerra_em=quando)
        )

        r = s.tick(frame_real, momento=quando.timestamp())

        assert r.avisos and "encerrado" in r.avisos[0]
        assert r.despachos[0][1] is Categoria.SEMPRE

    def test_encerra_uma_vez_so(self, calibracao, frame_real, tmp_path):
        quando = SEGUNDA.replace(hour=15, minute=15)
        s = nova_sessao(
            calibracao, tmp_path, silencio=SilencioFalso(encerra_em=quando)
        )

        avisos = []
        for i in range(10):
            avisos.extend(s.tick(frame_real, momento=quando.timestamp() + i).avisos)
        assert len([a for a in avisos if "encerrado" in a]) == 1


class TestLootNoTick:
    """O fio inteiro do loot dentro do tick: aviso com "Loot: X" e consumo.

    Como no config real: o Solo Boss tem `avisar_no_horario = False`, entao o
    unico aviso que existe e o de antecedencia — e e nele que o nome entra.
    """

    SOLO = EventoAgendado(
        nome="Solo Boss", horarios=((10, 0), (12, 0)), avisar_no_horario=False
    )

    def _loot(self, tmp_path):
        from l2scanner.loot import RegistroDeLoot

        return RegistroDeLoot(tmp_path / "loot")

    def test_o_aviso_sai_com_o_nome_do_designado(
        self, calibracao, frame_real, tmp_path
    ):
        loot = self._loot(tmp_path)
        loot.designar("J4guar", SEGUNDA.replace(hour=10), SEGUNDA.replace(hour=9))
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO], loot=loot)

        r = s.tick(frame_real, momento=em(9, 50))

        assert r.avisos, "o aviso de antecedencia nao saiu"
        assert "Solo Boss" in r.avisos[0]
        assert "Loot: J4guar" in r.avisos[0]

    def test_o_que_vai_para_o_whatsapp_vai_dentro_da_moldura(
        self, calibracao, frame_real, tmp_path
    ):
        """O aviso concorre com a conversa do grupo — e o bloco e quem ganha.

        A moldura vale no DESPACHO e nao no `avisos`: quem imprime o console
        monta a propria moldura a partir de `avisos`, e moldurar nos dois
        lugares poria um bloco dentro do outro na tela.
        """
        loot = self._loot(tmp_path)
        loot.designar("TioMad", SEGUNDA.replace(hour=10), SEGUNDA.replace(hour=9))
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO], loot=loot)

        r = s.tick(frame_real, momento=em(9, 50))

        (texto, _, _) = r.despachos[0]
        linhas = texto.split("\n")
        assert len(linhas) == 3, f"esperava borda/texto/borda, veio {texto!r}"
        assert set(linhas[0]) == {"*"} and linhas[0] == linhas[2]
        assert linhas[1].endswith("  [09:50]"), "carimbo da hora do envio"
        assert "Loot: TioMad" in linhas[1]

        assert "\n" not in r.avisos[0], "o console recebe o texto CRU"

    def test_depois_do_cancelamento_o_aviso_sai_sem_a_linha(
        self, calibracao, frame_real, tmp_path
    ):
        """A prova de que o `.loot-` apagou DE VERDADE.

        Nao basta o registro devolver None: o que a party ve e o aviso de
        antecedencia, e e nele que a linha "Loot:" tem que sumir. O aviso
        continua saindo — cancelar o loot nao cancela o boss.
        """
        loot = self._loot(tmp_path)
        loot.designar("J4guar", SEGUNDA.replace(hour=10), SEGUNDA.replace(hour=9))
        loot.cancelar()
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO], loot=loot)

        r = s.tick(frame_real, momento=em(9, 50))

        assert r.avisos, "o aviso do Solo Boss sumiu junto com a designacao"
        assert "Solo Boss" in r.avisos[0]
        assert "Loot" not in r.avisos[0]

    def test_sem_designacao_o_aviso_sai_sem_a_linha(
        self, calibracao, frame_real, tmp_path
    ):
        s = nova_sessao(
            calibracao, tmp_path, eventos=[self.SOLO], loot=self._loot(tmp_path)
        )

        r = s.tick(frame_real, momento=em(9, 50))

        assert r.avisos
        assert "Loot" not in r.avisos[0]

    def test_TvT_nunca_ganha_a_linha(self, calibracao, frame_real, tmp_path):
        """A designacao do Solo Boss esta ativa, mas o aviso e do TvT."""
        tvt = EventoAgendado(nome="TvT", horarios=((10, 0),))
        loot = self._loot(tmp_path)
        loot.designar("J4guar", SEGUNDA.replace(hour=10), SEGUNDA.replace(hour=9))
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt], loot=loot)

        r = s.tick(frame_real, momento=em(9, 50))

        assert r.avisos and "TvT" in r.avisos[0]
        assert "Loot" not in r.avisos[0]

    def test_o_consumo_dispara_no_horario_e_uma_vez_so(
        self, calibracao, frame_real, tmp_path
    ):
        loot = self._loot(tmp_path)
        loot.designar("J4guar", SEGUNDA.replace(hour=10), SEGUNDA.replace(hour=9))
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO], loot=loot)

        r = s.tick(frame_real, momento=em(10, 0))

        assert r.loot_consumado is not None
        assert r.loot_consumado.nick == "J4guar"
        pegou = [p for p in (tmp_path / "loot").iterdir() if p.name.startswith("pegou_")]
        assert len(pegou) == 1
        assert loot.designacao() is None

        seguinte = s.tick(frame_real, momento=em(10, 1))
        assert seguinte.loot_consumado is None, "registrou em dobro"

    def test_duas_instancias_consomem_uma_vez_so(
        self, calibracao, frame_real, tmp_path
    ):
        """As duas Sessao do usuario, mesma pasta de loot, mesmo tick."""
        loot_a = self._loot(tmp_path)
        loot_b = self._loot(tmp_path)
        loot_a.designar("J4guar", SEGUNDA.replace(hour=10), SEGUNDA.replace(hour=9))
        a = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO], loot=loot_a)
        b = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO], loot=loot_b)

        consumos = [
            a.tick(frame_real, momento=em(10, 0)).loot_consumado,
            b.tick(frame_real, momento=em(10, 0)).loot_consumado,
        ]

        assert len([c for c in consumos if c is not None]) == 1
        pegou = [p for p in (tmp_path / "loot").iterdir() if p.name.startswith("pegou_")]
        assert len(pegou) == 1

    def test_o_boss_seguinte_nao_herda_a_designacao(
        self, calibracao, frame_real, tmp_path
    ):
        """Consumida as 10:00, a designacao nao pode aparecer no aviso do
        boss das 12:00 — a vez do loot vale para UM boss, nao para o dia."""
        loot = self._loot(tmp_path)
        loot.designar("J4guar", SEGUNDA.replace(hour=10), SEGUNDA.replace(hour=9))
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO], loot=loot)

        assert s.tick(frame_real, momento=em(10, 0)).loot_consumado is not None

        r = s.tick(frame_real, momento=em(11, 50))
        assert r.avisos and "Solo Boss" in r.avisos[0]
        assert "Loot" not in r.avisos[0]


class TestManutencaoNoTick:
    """A costura do aviso de manutencao — que e onde os erros deste projeto moram.

    O parser e o vigia tem testes proprios em `test_manutencao.py`. O que se
    prova AQUI e o fio inteiro: vigia -> marcador em disco -> resultado ->
    despacho, com `Categoria.SEMPRE` (D-08) e moldura (D-11).
    """

    BANNER = "Server Maintence 40 minutes 26 seconds"

    def _frame_com_banner(self, frame_real):
        """O recorte do banner entra pelo mesmo `extras` que o `hp_proprio` usa.

        O conteudo dos pixels e irrelevante: o `ler_texto` do vigia e injetado,
        porque o Python da suite nao tem as bindings do WinRT.
        """
        return replace(
            frame_real, extras={"banner_manutencao": np.zeros((10, 10, 3), np.uint8)}
        )

    def _vigia(self, texto=BANNER):
        from l2scanner.manutencao import VigiaDeManutencao

        return VigiaDeManutencao(ler_texto=lambda _: texto)

    def test_o_anuncio_atravessa_vigia_marcador_resultado_e_despacho(
        self, calibracao, frame_real, tmp_path
    ):
        from l2scanner.manutencao import TipoDeAvisoDeManutencao

        s = nova_sessao(calibracao, tmp_path, manutencao=self._vigia())
        frame = self._frame_com_banner(frame_real)

        # DOIS ticks espacados de 6 s: o consenso de D-05 exige duas leituras
        # concordantes, e a cadencia de D-06 so deixa a segunda acontecer
        # depois de 5 s.
        s.tick(frame, momento=em(12, 0))
        r = s.tick(frame, momento=em(12, 0) + 6)

        assert r.avisos_de_manutencao == [TipoDeAvisoDeManutencao.ANUNCIADA]

        despachos = [d for d in r.despachos if "manuten" in d[0].lower()]
        assert len(despachos) == 1
        (texto, categoria, _) = despachos[0]
        assert categoria is Categoria.SEMPRE
        assert "***" in texto, "o aviso sai moldurado (D-11)"
        assert "40 minutos" in texto and "26 segundos" in texto

    def test_sai_uma_vez_so_em_muitos_ticks(self, calibracao, frame_real, tmp_path):
        s = nova_sessao(calibracao, tmp_path, manutencao=self._vigia())
        frame = self._frame_com_banner(frame_real)

        total = 0
        base = em(12, 0)
        for i in range(30):
            total += len(s.tick(frame, momento=base + i).avisos_de_manutencao)

        assert total == 1
