"""O tick, agora testavel — e os tres bugs de producao como regressao.

Este arquivo existe por causa de uma medicao: `__main__.py` estava em 20% de
cobertura contra 98% do `rastreador`, e TODOS os bugs de integracao deste
projeto moraram la. Tres chegaram em producao no mesmo dia, e nenhum dos 420
testes os viu — porque nenhum teste chamava o laco.

Agora chama.
"""

from __future__ import annotations

import logging
import os
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.agenda import (
    EventoAgendado,
    RegistroEmDisco,
    chave_da_ocorrencia,
)
from l2scanner.bosses import Boss, OrigemDoAviso, VigiaDeBosses
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.notificador import Categoria
from l2scanner.rastreador import Rastreador
from l2scanner.respawn import TipoDeJanela
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
    membros=(),
    registro=None,
    bosses=None,
    regras_de_respawn=(),
):
    return Sessao(
        cal=calibracao,
        rastreador=Rastreador(nomes=list(calibracao.nomes)),
        eventos_agendados=list(eventos),
        registro=registro if registro is not None else RegistroEmDisco(tmp_path),
        silencio=silencio or SilencioFalso(),
        despachante=despachante,
        loot=loot,
        manutencao=manutencao,
        membros=membros,
        bosses=bosses,
        regras_de_respawn=regras_de_respawn,
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


class TestPresencaNoTick:
    """A lista do Solo Boss fechando dentro do laco principal (D-12).

    O EVENTO DE TESTE E O CONFIG REAL DO USUARIO: `avisar_no_horario=False`,
    como em `TestLootNoTick`, agora tambem com `chamar_minutos_antes`. Nao e
    detalhe de fixture — e a prova de que o fechamento NAO se pendura no aviso
    de AGORA. Se ele se pendurasse, o usuario teria que religar as doze
    mensagens diarias que desligou de proposito para ganhar a lista.

    E o piso e SILENCIO: sem ninguem confirmado, o tick nao produz aviso,
    despacho nem fechamento.
    """

    SOLO = EventoAgendado(
        nome="Solo Boss",
        horarios=((10, 0), (12, 0)),
        avisar_no_horario=False,
        chamar_minutos_antes=110,
    )

    class MembroFalso:
        """Qualquer objeto com `.nick` serve — `presenca` nao importa `comandos`."""

        def __init__(self, nick):
            self.nick = nick

    def _com_lista(self, sessao, hora=10, *nicks):
        chave = chave_da_ocorrencia("Solo Boss", SEGUNDA.replace(hour=hora))
        for nick in nicks:
            sessao.registro.entrar(chave, nick)

    def test_o_tick_do_horario_fecha_a_lista(self, calibracao, frame_real, tmp_path):
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO])
        self._com_lista(s, 10, "j4guar", "tiomad")

        r = s.tick(frame_real, momento=em(10, 0))

        assert len(r.presencas_fechadas) == 1
        fechamento = r.presencas_fechadas[0]
        assert fechamento.evento == "Solo Boss"
        assert fechamento.alvo == SEGUNDA.replace(hour=10)
        assert fechamento.nicks == ("j4guar", "tiomad")

    def test_o_evento_de_teste_tem_o_aviso_de_agora_DESLIGADO(self):
        """Guarda contra prova vazia: sem isto o teste acima nao prova D-12.

        Um dia alguem "conserta" o fixture ligando `avisar_no_horario` e o
        fechamento passaria a sair de carona no aviso de AGORA sem ninguem
        notar — que e exatamente o acoplamento que D-12 proibe.
        """
        assert self.SOLO.avisar_no_horario is False

    def test_o_console_recebe_o_texto_CRU_e_o_whatsapp_a_moldura(
        self, calibracao, frame_real, tmp_path
    ):
        """A mesma separacao do aviso de agenda tres linhas acima no arquivo.

        Quem imprime o console monta a propria moldura a partir de `avisos`;
        moldurar nos dois lugares poria um bloco dentro do outro na tela.
        """
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO])
        self._com_lista(s, 10, "j4guar")

        r = s.tick(frame_real, momento=em(10, 0))

        assert r.avisos, "o fechamento nao chegou ao console"
        assert "\n" not in r.avisos[-1], "o console recebe o texto CRU"
        assert "Solo Boss" in r.avisos[-1]
        assert "J4guar" in r.avisos[-1]

        (texto, categoria, conversa) = r.despachos[-1]
        linhas = texto.split("\n")
        assert len(linhas) == 3, f"esperava borda/texto/borda, veio {texto!r}"
        assert set(linhas[0]) == {"*"} and linhas[0] == linhas[2]
        assert linhas[1].endswith("  [10:00]"), "carimbo da hora do envio"
        assert categoria is Categoria.SEMPRE, (
            "a lista fechada e organizacao de party, nao alerta de morte: "
            "silencia-la dentro do Prime esconderia quem esta indo"
        )
        assert conversa is None, (
            "a lista tem que sair nas conversas de AVISO, e nunca numa "
            "conversa de comando (T-10-17)"
        )

    def test_zero_confirmacoes_produz_ZERO_de_tudo(
        self, calibracao, frame_real, tmp_path
    ):
        """D-12 dentro do tick: o piso do Solo Boss e silencio, nao 12/dia."""
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO])

        r = s.tick(frame_real, momento=em(10, 0))

        assert r.presencas_fechadas == []
        assert r.avisos == []
        assert r.despachos == []

    def test_dois_ticks_dentro_da_janela_fecham_uma_vez_so(
        self, calibracao, frame_real, tmp_path
    ):
        """A 1 Hz seriam ~300 mensagens por ocorrencia sem o marcador (T-10-16)."""
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO])
        self._com_lista(s, 10, "kaus")

        primeiro = s.tick(frame_real, momento=em(10, 0))
        segundo = s.tick(frame_real, momento=em(10, 1))

        assert len(primeiro.presencas_fechadas) == 1
        assert segundo.presencas_fechadas == []
        assert segundo.avisos == []
        assert segundo.despachos == []

    def test_com_membros_a_lista_sai_com_a_grafia_do_config(
        self, calibracao, frame_real, tmp_path
    ):
        """D-10: o disco guarda `tiomad` e a party reconhece `TioMad`."""
        s = nova_sessao(
            calibracao,
            tmp_path,
            eventos=[self.SOLO],
            membros=[self.MembroFalso("TioMad")],
        )
        self._com_lista(s, 10, "tiomad")

        r = s.tick(frame_real, momento=em(10, 0))

        assert "TioMad" in r.avisos[-1]
        assert "Tiomad" not in r.avisos[-1]

    def test_sem_membros_a_lista_sai_com_a_caixa_do_slug(
        self, calibracao, frame_real, tmp_path
    ):
        """O recurso NAO depende do mapa para funcionar.

        Sem nenhum bloco `[[membro]]` no config a lista ainda fecha e ainda
        sai — so com a caixa do slug. Deixar o fechamento inteiro em pe por
        falta do mapa seria trocar um defeito cosmetico por um mudo.
        """
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO])
        self._com_lista(s, 10, "tiomad")

        r = s.tick(frame_real, momento=em(10, 0))

        assert r.presencas_fechadas
        assert "Tiomad" in r.avisos[-1]

    def test_a_sessao_sem_o_parametro_novo_continua_valida(
        self, calibracao, tmp_path
    ):
        """Default vazio, como o `loot=None` ja fez — nada existente muda."""
        s = Sessao(
            cal=calibracao,
            rastreador=Rastreador(nomes=list(calibracao.nomes)),
            eventos_agendados=[],
            registro=RegistroEmDisco(tmp_path),
            silencio=SilencioFalso(),
        )
        assert s.membros == ()

    def test_evento_sem_chamada_nunca_fecha_no_tick(
        self, calibracao, frame_real, tmp_path
    ):
        """TvT nao tem lista, entao o tick das 10:00 nao inventa uma."""
        tvt = EventoAgendado(nome="TvT", horarios=((10, 0),))
        s = nova_sessao(calibracao, tmp_path, eventos=[tvt])
        s.registro.entrar(
            chave_da_ocorrencia("TvT", SEGUNDA.replace(hour=10)), "kaus"
        )

        r = s.tick(frame_real, momento=em(10, 0))
        assert r.presencas_fechadas == []

    def _loot_com(self, tmp_path, **quantos):
        from l2scanner.loot import RegistroDeLoot

        registro = RegistroDeLoot(tmp_path / "loot")
        passo = 0
        for nick, total in quantos.items():
            for _ in range(total):
                # Vespera, para nenhum registro historico colidir com o boss
                # das 10:00 que o tick deste teste vai consumir.
                registro.registrar(
                    nick, SEGUNDA.replace(day=23, hour=(passo * 2) % 24)
                )
                passo += 1
        return registro

    def test_a_lista_fechada_sai_com_a_sugestao_de_loot(
        self, calibracao, frame_real, tmp_path
    ):
        """PRES-14/PRES-15: quem esteve presente aparece na hora de decidir.

        Tres na lista, e o `tiomad` nunca pegou nada: a mensagem que o grupo
        recebe nomeia ele. Sem esta linha a lista fechada seria so um recibo —
        util, mas sem a decisao que a party de fato precisa tomar no momento
        em que o boss nasce.
        """
        loot = self._loot_com(tmp_path, kaus=2, j4guar=5)
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO], loot=loot)
        self._com_lista(s, 10, "kaus", "j4guar", "tiomad")

        r = s.tick(frame_real, momento=em(10, 0))

        assert r.presencas_fechadas
        assert r.avisos[-1].endswith("Sugestao de loot: Tiomad (ainda nenhum).")

    def test_com_um_nick_so_a_sugestao_e_ele(
        self, calibracao, frame_real, tmp_path
    ):
        loot = self._loot_com(tmp_path, kaus=3)
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO], loot=loot)
        self._com_lista(s, 10, "kaus")

        r = s.tick(frame_real, momento=em(10, 0))

        assert r.avisos[-1].endswith("Sugestao de loot: Kaus (3 loots).")

    def test_a_sugestao_sai_com_a_grafia_do_config(
        self, calibracao, frame_real, tmp_path
    ):
        """D-10 na sugestao tambem: o disco tem `tiomad`, a party le `TioMad`."""
        loot = self._loot_com(tmp_path, kaus=2)
        s = nova_sessao(
            calibracao,
            tmp_path,
            eventos=[self.SOLO],
            loot=loot,
            membros=[self.MembroFalso("TioMad")],
        )
        self._com_lista(s, 10, "kaus", "tiomad")

        r = s.tick(frame_real, momento=em(10, 0))

        assert r.avisos[-1].endswith("Sugestao de loot: TioMad (ainda nenhum).")

    def test_sem_registro_de_loot_a_mensagem_sai_como_no_plano_10_04(
        self, calibracao, frame_real, tmp_path
    ):
        """`loot=None` e o caso de quem nunca usou o revezamento.

        A lista fechada e o desfecho da chamada feita 1h50 antes; perde-la por
        falta de estatistica de loot seria deixar a party sem a resposta por
        causa de um extra.
        """
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO])
        self._com_lista(s, 10, "kaus", "tiomad")

        r = s.tick(frame_real, momento=em(10, 0))

        assert r.presencas_fechadas
        assert "Sugestao de loot" not in r.avisos[-1]
        assert r.avisos[-1] == (
            "Solo Boss das 10:00 comecando. Confirmaram: Kaus, Tiomad."
        )

    def test_o_boss_que_JA_TEM_DONO_fecha_sem_opiniao_de_loot(
        self, calibracao, frame_real, tmp_path
    ):
        """CR-02: a lista fechada nao pode contradizer a designacao do MESMO boss.

        Este teste ja existia sob o nome
        `test_o_consumo_do_boss_ANTERIOR_ja_conta_na_sugestao` e afirmava o
        defeito: o `kaus` designado para ESTE boss das 10:00, o consumo
        creditando o loot dele antes de a lista fechar, e a sugestao — calculada
        em seguida — apontando para o `tiomad`. Dez minutos antes, o aviso de
        antecedencia do MESMO boss saiu no MESMO grupo com "Loot: Kaus". O bot
        se desmentia, e quem obedecesse a sugestao errada gravaria `.pegou` no
        `.loot/`, que nao tem poda nem backup.

        Quando o loot deste boss ja esta decidido e registrado, a mensagem de
        fechamento nao tem opiniao nenhuma a dar sobre ele.
        """
        loot = self._loot_com(tmp_path)
        loot.designar("kaus", SEGUNDA.replace(hour=10), SEGUNDA.replace(hour=9))
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO], loot=loot)
        self._com_lista(s, 10, "kaus", "tiomad")

        r = s.tick(frame_real, momento=em(10, 0))

        assert r.loot_consumado is not None, "o consumo continua rodando antes"
        assert r.avisos[-1] == (
            "Solo Boss das 10:00 comecando. Confirmaram: Kaus, Tiomad."
        ), "a mensagem sugeriu um loot que contradiz a designacao ja consumida"

    def test_o_consumo_do_boss_ANTERIOR_ja_conta_na_sugestao(
        self, calibracao, frame_real, tmp_path
    ):
        """A razao de o fechamento vir DEPOIS do consumo de loot no tick.

        A ordem continua importando — mas o caso que a exercita e o do boss
        ANTERIOR, como o nome sempre disse. O `kaus` foi designado para o boss
        das 08:00 e ninguem consumiu a tempo; no tick das 10:00 o consumo
        registra o loot dele (com o carimbo das 08:00) ANTES de a lista fechar,
        entao a sugestao deste boss ja o enxerga com um loot a mais e passa a
        vez para o outro. Invertida a ordem, o bot sugeriria justamente quem
        acabou de pegar.

        E, como o dono registrado e do boss das 08:00 e nao do das 10:00, a
        sugestao SAI: este boss ainda nao tem dono, entao a mensagem tem o que
        dizer sobre ele.
        """
        loot = self._loot_com(tmp_path)
        loot.designar("kaus", SEGUNDA.replace(hour=8), SEGUNDA.replace(hour=7))
        s = nova_sessao(calibracao, tmp_path, eventos=[self.SOLO], loot=loot)
        self._com_lista(s, 10, "kaus", "tiomad")

        r = s.tick(frame_real, momento=em(10, 0))

        assert r.loot_consumado is not None
        assert r.avisos[-1].endswith("Sugestao de loot: Tiomad (ainda nenhum).")


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


class LeitorDoBanner:
    """Le o banner nas duas primeiras vezes e fica cego depois.

    Duas leituras e o minimo que o consenso de D-05 exige. Ficar cego em
    seguida e o caso REAL: o banner some, o jogo fica coberto, o cliente
    engasga — e e exatamente ai que a ancora tem que segurar o segundo aviso.
    """

    def __init__(self, texto: str, leituras: int = 2) -> None:
        self._texto = texto
        self._restantes = leituras
        self._ultimo: str | None = None

    def __call__(self, _pixels):
        if self._restantes <= 0:
            self._ultimo = None
            return None
        self._restantes -= 1
        self._ultimo = self._texto
        return self._texto

    def conferir(self, _pixels):
        """A segunda escala de D-d, devolvendo o que a barata acabou de ler.

        ELA NAO CONSOME UMA LEITURA. As duas escalas leem os MESMOS pixels do
        MESMO frame — gastar o contador aqui transformaria "duas escalas num
        tick" em "dois ticks", que e a outra guarda, e a cegueira chegaria na
        metade do tempo.
        """
        return self._ultimo


def _vigia_das_duas_escalas(leitor: LeitorDoBanner):
    """Liga as DUAS escalas no mesmo duble (D-d).

    Aqui elas concordam sempre, de proposito: o que estes testes exercitam e a
    COSTURA no `Sessao`, e o desacordo entre escalas tem testes proprios em
    `test_manutencao.py`.
    """
    from l2scanner.manutencao import VigiaDeManutencao

    return VigiaDeManutencao(
        ler_texto=leitor, ler_texto_conferencia=leitor.conferir
    )


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

        ler = lambda _: texto  # noqa: E731 — as duas escalas concordam trivialmente
        return VigiaDeManutencao(ler_texto=ler, ler_texto_conferencia=ler)

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

    def test_as_duas_instancias_competem_pelo_mesmo_marcador(
        self, calibracao, frame_real, tmp_path
    ):
        """D-09: Yazalaque e Faerlina rodam lado a lado — e o grupo recebe UMA.

        Prova que o `marcar` E a decisao de despachar, e nao uma checagem
        anterior: as duas sessoes chegam ao mesmo aviso, com a mesma chave, no
        mesmo instante, e exatamente uma cria o arquivo com O_CREAT|O_EXCL.
        """

        frame = self._frame_com_banner(frame_real)
        sessoes = [
            nova_sessao(
                calibracao,
                tmp_path,
                manutencao=_vigia_das_duas_escalas(LeitorDoBanner(self.BANNER)),
            )
            for _ in range(2)
        ]

        despachos = []
        for momento in (em(12, 0), em(12, 0) + 6):
            for s in sessoes:
                despachos += [
                    d
                    for d in s.tick(frame, momento=momento).despachos
                    if "manuten" in d[0].lower()
                ]

        assert len(despachos) == 1

    def test_o_faltam5_tambem_atravessa_a_costura(
        self, calibracao, frame_real, tmp_path
    ):
        """Os DOIS avisos saem `SEMPRE` e moldurados — e o segundo sai cego.

        Depois das duas leituras o banner some (o leitor passa a devolver
        None), e mesmo assim o aviso de 5 minutos sai: ele vem da ancora, nao
        da tela (D-10).
        """
        from l2scanner.manutencao import TipoDeAvisoDeManutencao

        vigia = _vigia_das_duas_escalas(
            LeitorDoBanner("Server Maintence 6 minutes")
        )
        s = nova_sessao(calibracao, tmp_path, manutencao=vigia)
        frame = self._frame_com_banner(frame_real)

        base = em(12, 0)
        tipos, despachos = [], []
        for segundos in [0, 6] + list(range(7, 131)):
            r = s.tick(frame, momento=base + segundos)
            tipos += r.avisos_de_manutencao
            despachos += [d for d in r.despachos if "manuten" in d[0].lower()]

        assert tipos == [
            TipoDeAvisoDeManutencao.ANUNCIADA,
            TipoDeAvisoDeManutencao.FALTAM5,
        ]
        assert len(despachos) == 2
        for texto, categoria, _ in despachos:
            assert categoria is Categoria.SEMPRE
            assert texto.split("\n")[0].strip("*") == ""


class TestSimulacaoNoLacoPrincipal:
    """O `--dry-run` visto do tick: o aviso sai, o disco fica intacto.

    O incidente de 2026-08-26 19:30 foi no `--so-agenda`, mas o laco principal
    chama o MESMO `marcar` duas vezes (os avisos da agenda e o banner de
    manutencao) sobre a MESMA pasta `.agenda/`. Um usuario com o jogo aberto e
    uma simulacao ao lado corria o mesmo risco.

    `sessao.py` nao conhece `dry_run` e nao deve conhecer: quem sabe que esta
    simulando e o registro que ela recebe pronto. E o que faz um sitio futuro
    de `marcar` nascer certo sem ninguem lembrar da regra.
    """

    QUANDO = datetime(2026, 8, 26, 19, 30).timestamp()
    MARCADOR = "2026-08-26_tvt-1930_agora"

    def _tvt(self):
        return EventoAgendado(nome="TvT", horarios=((19, 30),))

    def test_um_tick_simulado_avisa_e_nao_deixa_marcador(
        self, calibracao, frame_real, tmp_path
    ):
        pasta = tmp_path / "agenda"
        s = nova_sessao(
            calibracao,
            tmp_path,
            eventos=[self._tvt()],
            registro=RegistroEmDisco(pasta, simulando=True),
        )

        r = s.tick(frame_real, momento=self.QUANDO)

        assert any("TvT" in aviso for aviso in r.avisos), (
            "o aviso nao apareceu no resultado do tick; o console ficaria mudo"
        )
        assert not pasta.exists(), "a simulacao gravou na .agenda/ compartilhada"

    def test_depois_do_tick_simulado_a_instancia_real_ainda_avisa(
        self, calibracao, frame_real, tmp_path
    ):
        """A pergunta que o incidente fez: o scanner de verdade ainda fala?"""
        pasta = tmp_path / "agenda"
        s = nova_sessao(
            calibracao,
            tmp_path,
            eventos=[self._tvt()],
            registro=RegistroEmDisco(pasta, simulando=True),
        )
        s.tick(frame_real, momento=self.QUANDO)

        assert RegistroEmDisco(pasta).marcar(self.MARCADOR) is True, (
            "o --dry-run queimou o marcador: o aviso das 19:30 nao sairia"
        )

    def test_a_prova_nao_e_vazia_sem_simulacao_o_marcador_aparece(
        self, calibracao, frame_real, tmp_path
    ):
        """Guarda contra teste vazio: fora da simulacao o tick GRAVA.

        Sem isto, um tick que nunca chegasse ao aviso deixaria a pasta limpa e
        os dois testes acima passariam sem provar nada.
        """
        pasta = tmp_path / "agenda"
        s = nova_sessao(
            calibracao,
            tmp_path,
            eventos=[self._tvt()],
            registro=RegistroEmDisco(pasta),
        )

        s.tick(frame_real, momento=self.QUANDO)

        assert (pasta / self.MARCADOR).exists(), (
            "o tick nao alcancou o aviso; os testes de simulacao seriam vazios"
        )


class TestOSeamDosBosses:
    """O unico teste que existe do caminho `_processar_bosses`.

    Ate aqui aquele seam nao tinha teste nenhum — e a docstring de abertura
    deste arquivo diz, por escrito, que TODOS os bugs de integracao deste
    projeto moraram exatamente no codigo sem teste de laco.

    A fatia que `tests/test_bosses.py` prova do arquivo ate a mensagem pronta
    chega aqui ate `resultado.despachos`, que e o funil de saida de verdade.
    """

    NORTH = Boss(nome="Tiat North", respawn_horas_min=6, respawn_horas_max=8)
    SOUTH = Boss(nome="Tiat South", respawn_horas_min=6, respawn_horas_max=8)
    ANUNCIO = "Tiat North [Lv. 60] has spawned!"

    def vigia(self, chat, alvo):
        """Molde do `Leitor` de `tests/test_bosses.py`: chat primeiro."""
        textos = iter([chat, alvo])

        def ler(_pixels):
            return next(textos)

        return VigiaDeBosses(
            ler, bosses=(self.NORTH, self.SOUTH), segundos_entre_leituras=1
        )

    def frame_com_recortes(self, frame_real):
        """Os `extras` que o `laco_principal` monta quando o vigia existe.

        As chaves continuam `tiat_chat` e `tiat_alvo` de proposito: renomea-las
        desligaria a vigilancia, em silencio, em todo `calibration.json` que ja
        existe na maquina do usuario.
        """
        recorte = np.zeros((5, 5, 3), dtype=np.uint8)
        return replace(
            frame_real, extras={"tiat_chat": recorte, "tiat_alvo": recorte}
        )

    def test_o_anuncio_no_chat_vira_um_despacho_que_comeca_pelo_boss(
        self, calibracao, frame_real, tmp_path
    ):
        s = nova_sessao(
            calibracao, tmp_path, bosses=self.vigia(self.ANUNCIO, "")
        )

        r = s.tick(self.frame_com_recortes(frame_real), momento=em(12, 0))

        assert len(r.despachos) == 1
        texto, categoria, _alvo = r.despachos[0]
        assert texto.startswith("Tiat North")
        # Spawn e urgente: tem que atravessar o silencio de TvT.
        assert categoria is Categoria.SEMPRE

    def test_o_resultado_carrega_o_par_boss_e_origem_e_nao_o_texto(
        self, calibracao, frame_real, tmp_path
    ):
        """Estruturado, e nao texto: casar com a frase quebraria na primeira
        melhoria de redacao. O `boss` entra no par porque, com dois avisos num
        tick, a origem sozinha nao diz mais de quem ela e.
        """
        s = nova_sessao(
            calibracao, tmp_path, bosses=self.vigia(self.ANUNCIO, "")
        )

        r = s.tick(self.frame_com_recortes(frame_real), momento=em(12, 0))

        assert r.avisos_de_boss == [("Tiat North", OrigemDoAviso.CHAT)]

    def test_chat_com_um_boss_e_alvo_com_outro_produzem_dois_despachos(
        self, calibracao, frame_real, tmp_path
    ):
        """Criterio 4: um tick pode entregar DOIS avisos."""
        s = nova_sessao(
            calibracao, tmp_path, bosses=self.vigia(self.ANUNCIO, "Tiat South")
        )

        r = s.tick(self.frame_com_recortes(frame_real), momento=em(12, 0))

        assert len(r.despachos) == 2
        assert [b for b, _origem in r.avisos_de_boss] == [
            "Tiat North",
            "Tiat South",
        ]

    def test_a_pergunta_digitada_no_chat_nao_despacha_nada(
        self, calibracao, frame_real, tmp_path
    ):
        """RECO-01 afirmado sobre uma `Sessao` de verdade, e nao so no vigia."""
        s = nova_sessao(
            calibracao,
            tmp_path,
            bosses=self.vigia("Fulano: tiat ja nasceu?", ""),
        )

        r = s.tick(self.frame_com_recortes(frame_real), momento=em(12, 0))

        assert r.despachos == []
        assert r.avisos_de_boss == []

    def test_uma_sessao_sem_vigia_roda_um_tick_identico_ao_de_hoje(
        self, calibracao, frame_real, tmp_path
    ):
        """As cinco construcoes de `Sessao` que ja existem no repositorio nao
        passam `bosses=`, e o default `None` e o que as mantem validas sem
        edicao nenhuma.
        """
        s = nova_sessao(calibracao, tmp_path)

        r = s.tick(self.frame_com_recortes(frame_real), momento=em(12, 0))

        assert r.avisos_de_boss == []
        assert r.despachos == []
        assert r.observacao is not None
        assert not r.falhou_ao_analisar

    def test_sem_recorte_calibrado_o_tick_nao_quebra(
        self, calibracao, frame_real, tmp_path
    ):
        """Vigia ligado e `extras` vazio: o `_ler` devolve None sem levantar."""
        s = nova_sessao(
            calibracao, tmp_path, bosses=self.vigia(self.ANUNCIO, "")
        )

        r = s.tick(frame_real, momento=em(12, 0))

        assert r.avisos_de_boss == []
        assert not r.falhou_ao_analisar


class TestAFatiaInteiraDaJanelaDeRespawn:
    """DA TELA AO WHATSAPP, atravessando o disco e seis horas de relogio.

    Este e o unico teste do projeto que exercita o caminho INTEIRO da Fase 2:
    um anuncio no recorte do chat as 14:30 vira um arquivo vazio em `.agenda/`,
    e as 20:30 esse arquivo vira uma mensagem no grupo — sem tela, sem rede, e
    possivelmente noutro processo.

    AS HORAS VEM DO `Boss` CONSTRUIDO AQUI, e nunca do `config.toml` do
    repositorio. Aquele arquivo e do usuario e ele o edita: um teste que
    fixasse `20:30` sobre o `respawn_horas_min` de la ficaria vermelho no dia
    em que ele trocasse 6 por 5, sem defeito nenhum.
    """

    NORTH = Boss(nome="Tiat North", respawn_horas_min=6, respawn_horas_max=8)
    ANUNCIO = "Tiat North [Lv. 60] has spawned!"

    NASCIMENTO = datetime(2026, 8, 30, 14, 30)
    ANCORA = "nascimento_2026-08-30_tiat-north-1430"

    def quando(self, **desloc):
        return (self.NASCIMENTO + timedelta(**desloc)).timestamp()

    def vigia(self, chat, alvo):
        """Le `chat` e `alvo` no primeiro tick e NADA em todos os seguintes.

        Um `iter` de dois itens levantaria `StopIteration` no segundo tick, e o
        teste da janela precisa de pelo menos dois: o que ancora e o que
        anuncia. Depois do primeiro, os recortes voltam limpos — que e o que
        acontece de verdade seis horas depois.
        """
        restantes = [chat, alvo]

        def ler(_pixels):
            return restantes.pop(0) if restantes else ""

        return VigiaDeBosses(
            ler, bosses=(self.NORTH,), segundos_entre_leituras=1
        )

    def frame(self, frame_real):
        recorte = np.zeros((5, 5, 3), dtype=np.uint8)
        return replace(
            frame_real, extras={"tiat_chat": recorte, "tiat_alvo": recorte}
        )

    def sessao(self, calibracao, tmp_path, pasta, com_vigia=True):
        return nova_sessao(
            calibracao,
            tmp_path,
            registro=RegistroEmDisco(pasta),
            bosses=self.vigia(self.ANUNCIO, "") if com_vigia else None,
            regras_de_respawn=[self.NORTH],
        )

    # -- 1. a ancora ------------------------------------------------------

    def test_o_anuncio_grava_exatamente_uma_ancora_com_o_nome_duravel(
        self, calibracao, frame_real, tmp_path
    ):
        """D-18 literal: a ORIGEM entra no NOME, e nao no conteudo.

        A forma e uma porta de mao unica ja atravessada pelo usuario. Mudar
        qualquer byte dela invalida todo marcador ja gravado: a contagem
        reinicia do nada e um aviso ja enviado sai de novo no grupo.
        """
        pasta = tmp_path / "agenda"
        s = self.sessao(calibracao, tmp_path, pasta)

        s.tick(self.frame(frame_real), momento=self.quando())

        ancoras = [n for n in os.listdir(pasta) if n.startswith("nascimento_")]
        assert ancoras == [f"{self.ANCORA}_chat"]

    def test_o_resultado_carrega_a_ancora_estruturada(
        self, calibracao, frame_real, tmp_path
    ):
        pasta = tmp_path / "agenda"
        s = self.sessao(calibracao, tmp_path, pasta)

        r = s.tick(self.frame(frame_real), momento=self.quando())

        assert r.ancoras_gravadas == [("Tiat North", OrigemDoAviso.CHAT)]

    # -- 2. a janela ------------------------------------------------------

    def test_um_minuto_antes_da_janela_nao_sai_nada(
        self, calibracao, frame_real, tmp_path
    ):
        pasta = tmp_path / "agenda"
        s = self.sessao(calibracao, tmp_path, pasta)
        s.tick(self.frame(frame_real), momento=self.quando())

        r = s.tick(
            self.frame(frame_real), momento=self.quando(hours=6, minutes=-1)
        )

        assert r.avisos_de_janela == []

    def test_na_abertura_sai_um_aviso_que_atravessa_o_silencio(
        self, calibracao, frame_real, tmp_path
    ):
        """D-23: `Categoria.SEMPRE`.

        Um boss nascendo durante o Prime e exatamente a informacao que ninguem
        quer perder — a mesma razao ja escrita em `_processar_bosses`.
        """
        pasta = tmp_path / "agenda"
        s = self.sessao(calibracao, tmp_path, pasta)
        s.tick(self.frame(frame_real), momento=self.quando())
        antes = len(s.tick(self.frame(frame_real), momento=self.quando(hours=1)).despachos)

        r = s.tick(self.frame(frame_real), momento=self.quando(hours=6))

        assert antes == 0
        assert len(r.avisos_de_janela) == 1
        boss, tipo = r.avisos_de_janela[0]
        assert boss == "Tiat North"
        assert tipo is TipoDeJanela.ABRE

        assert len(r.despachos) == 1
        texto, categoria, _alvo = r.despachos[0]
        assert categoria is Categoria.SEMPRE
        assert "Tiat North" in texto
        assert "14:30" in texto

    def test_o_segundo_tick_dentro_da_tolerancia_nao_repete(
        self, calibracao, frame_real, tmp_path
    ):
        """O `marcar` recusou: e ELE a decisao de despachar, e nao uma
        checagem anterior."""
        pasta = tmp_path / "agenda"
        s = self.sessao(calibracao, tmp_path, pasta)
        s.tick(self.frame(frame_real), momento=self.quando())
        s.tick(self.frame(frame_real), momento=self.quando(hours=6))

        r = s.tick(
            self.frame(frame_real), momento=self.quando(hours=6, minutes=1)
        )

        assert r.avisos_de_janela == []
        assert r.despachos == []

    # -- 3. a contagem nunca esteve em memoria ----------------------------

    def test_um_processo_novo_sobre_a_mesma_pasta_anuncia_igual(
        self, calibracao, frame_real, tmp_path
    ):
        """A PROVA DE JANE-01, e a razao de a ancora morar em disco.

        Esta segunda `Sessao` nunca viu o nascimento e nem sequer tem vigia de
        bosses ligado. Se o instante morasse em memoria, ela nao teria o que
        anunciar — e derrubar e subir o scanner perderia o ciclo inteiro.
        """
        pasta = tmp_path / "agenda"
        primeira = self.sessao(calibracao, tmp_path, pasta)
        primeira.tick(self.frame(frame_real), momento=self.quando())

        segunda = self.sessao(calibracao, tmp_path, pasta, com_vigia=False)
        r = segunda.tick(frame_real, momento=self.quando(hours=6))

        assert len(r.avisos_de_janela) == 1
        assert "14:30" in r.despachos[0][0]

    def test_a_previsao_existe_mesmo_com_o_vigia_desligado(
        self, calibracao, frame_real, tmp_path
    ):
        """`regras_de_respawn` e kwarg SEPARADO de `bosses`, de proposito.

        Sem calibracao dos recortes ou sem OCR o vigia fica `None` — mas a
        ancora ja esta em disco e a previsao continua correta. Amarrar a
        previsao ao vigia faria uma calibracao quebrada apagar, em silencio,
        uma funcionalidade que so depende do relogio.
        """
        pasta = tmp_path / "agenda"
        semente = RegistroEmDisco(pasta)
        semente.registrar_nascimento("2026-08-30_tiat-north-1430_chat")

        s = self.sessao(calibracao, tmp_path, pasta, com_vigia=False)
        r = s.tick(frame_real, momento=self.quando(hours=6))

        assert len(r.avisos_de_janela) == 1

    def test_sem_regras_de_respawn_nada_muda(
        self, calibracao, frame_real, tmp_path
    ):
        """As construcoes de `Sessao` que ja existem nao passam o kwarg."""
        pasta = tmp_path / "agenda"
        semente = RegistroEmDisco(pasta)
        semente.registrar_nascimento("2026-08-30_tiat-north-1430_chat")

        s = nova_sessao(calibracao, tmp_path, registro=RegistroEmDisco(pasta))
        r = s.tick(frame_real, momento=self.quando(hours=6))

        assert r.avisos_de_janela == []
        assert r.despachos == []
        assert not r.falhou_ao_analisar

    # -- 4. JANE-04 dentro de UM tick -------------------------------------

    def test_ancorar_vem_antes_de_anunciar_no_mesmo_tick(
        self, calibracao, frame_real, tmp_path
    ):
        """D-20 valendo DENTRO de um unico tick, e nao so entre ticks.

        As 20:30 o aviso do ciclo das 14:30 venceria. Se um nascimento NOVO
        chega no mesmo tick, a ancora nova ja esta em disco quando
        `anunciar_janelas` monta as ancoras: a chave velha nao e gerada e o
        aviso obsoleto nao sai. Inverter a ordem das duas chamadas anunciaria
        uma janela que o proprio tick acabou de invalidar.
        """
        pasta = tmp_path / "agenda"
        semente = RegistroEmDisco(pasta)
        semente.registrar_nascimento("2026-08-30_tiat-north-1430_chat")

        s = self.sessao(calibracao, tmp_path, pasta)
        r = s.tick(self.frame(frame_real), momento=self.quando(hours=6))

        assert r.ancoras_gravadas == [("Tiat North", OrigemDoAviso.CHAT)]
        assert r.avisos_de_janela == [], (
            "o aviso do ciclo velho saiu depois de o ciclo novo ter ancorado"
        )

    def test_uma_ancora_torta_na_pasta_nao_derruba_o_tick(
        self, calibracao, frame_real, tmp_path
    ):
        pasta = tmp_path / "agenda"
        semente = RegistroEmDisco(pasta)
        semente.registrar_nascimento("2026-08-30_tiat-north-1430_chat")
        (pasta / "nascimento_lixo").touch()

        s = self.sessao(calibracao, tmp_path, pasta, com_vigia=False)
        r = s.tick(frame_real, momento=self.quando(hours=6))

        assert len(r.avisos_de_janela) == 1
        assert not r.falhou_ao_analisar


class TestUmNascimentoUmaMensagem:
    """A FATIA VERTICAL DA FASE 3: duas instancias, uma mensagem.

    O DEFEITO DE CAMPO, medido em 2026-08-30 com `Win32_Process` confirmando
    DUAS instancias (`Yazalaque` e `Faerlina`) rodando desde as 21:28:47:

        21:59  Tiat South nasceu! (visto no chat do jogo)      x3
        22:01  Tiat South nasceu! (seu alvo virou Tiat South)
        22:02  Tiat South nasceu! (seu alvo virou Tiat South)  x2

    Seis mensagens para UM nascimento. A causa que esta classe fecha e a maior
    das duas: o aviso de nascimento era o UNICO alerta do projeto que chamava
    `_despachar` sem passar por `registro.marcar()`.

    O `Boss` E CONSTRUIDO AQUI e nunca lido do `config.toml` do repositorio:
    aquele arquivo e do usuario, ele o edita, e um teste ancorado nas horas de
    la fica vermelho sem defeito nenhum.
    """

    NORTH = Boss(nome="Tiat North", respawn_horas_min=6, respawn_horas_max=8)
    ANUNCIO = "Tiat North [Lv. 60] has spawned!"

    NASCIMENTO = datetime(2026, 8, 30, 21, 59)

    def quando(self, **desloc):
        return (self.NASCIMENTO + timedelta(**desloc)).timestamp()

    def vigia(self, chat, alvo):
        """Le `chat` e `alvo` no primeiro tick e nada nos seguintes."""
        restantes = [chat, alvo]

        def ler(_pixels):
            return restantes.pop(0) if restantes else ""

        return VigiaDeBosses(
            ler, bosses=(self.NORTH,), segundos_entre_leituras=1
        )

    def frame(self, frame_real):
        recorte = np.zeros((5, 5, 3), dtype=np.uint8)
        return replace(
            frame_real, extras={"tiat_chat": recorte, "tiat_alvo": recorte}
        )

    def instancia(self, calibracao, tmp_path, pasta, chat=None, simulando=False):
        """Uma `Sessao` NOVA sobre a MESMA pasta — o modelo do defeito.

        Cada chamada e um processo diferente do usuario: vigia proprio (memoria
        propria, logo o rearme em memoria nao ajuda em nada) e registro proprio
        sobre o mesmo disco.
        """
        return nova_sessao(
            calibracao,
            tmp_path,
            registro=RegistroEmDisco(pasta, simulando=simulando),
            bosses=self.vigia(self.ANUNCIO if chat is None else chat, ""),
            regras_de_respawn=[self.NORTH],
        )

    # -- o caminho unico ---------------------------------------------------

    def test_a_primeira_instancia_anuncia_uma_vez(
        self, calibracao, frame_real, tmp_path
    ):
        pasta = tmp_path / "agenda"
        s = self.instancia(calibracao, tmp_path, pasta)

        r = s.tick(self.frame(frame_real), momento=self.quando())

        assert len(r.despachos) == 1
        _texto, categoria, _alvo = r.despachos[0]
        assert categoria is Categoria.SEMPRE
        assert r.avisos_de_boss == [("Tiat North", OrigemDoAviso.CHAT)]
        assert [
            n for n in os.listdir(pasta) if n.startswith("nascimento_")
        ] == ["nascimento_2026-08-30_tiat-north-2159_chat"]

    def test_a_SEGUNDA_instancia_sobre_a_mesma_pasta_CALA(
        self, calibracao, frame_real, tmp_path
    ):
        """As tres mensagens das 21:59 viram uma."""
        pasta = tmp_path / "agenda"
        self.instancia(calibracao, tmp_path, pasta).tick(
            self.frame(frame_real), momento=self.quando()
        )

        outra = self.instancia(calibracao, tmp_path, pasta)
        r = outra.tick(self.frame(frame_real), momento=self.quando(seconds=1))

        assert r.despachos == []
        assert r.avisos_de_boss == []
        assert r.nascimentos_calados == [("Tiat North", OrigemDoAviso.CHAT)]
        assert [
            n for n in os.listdir(pasta) if n.startswith("anuncio_")
        ] == ["anuncio_2026-08-30_tiat-north-2159"]

    def test_a_instancia_do_MINUTO_SEGUINTE_grava_ancora_e_continua_calada(
        self, calibracao, frame_real, tmp_path
    ):
        """As instancias ticam em minutos diferentes — 21:59 contra 22:01, foi
        o que o campo mediu. A chave do episodio tem que ser a MESMA nas duas,
        e a ancora tem que continuar sendo gravada assim mesmo (D-27).
        """
        pasta = tmp_path / "agenda"
        self.instancia(calibracao, tmp_path, pasta).tick(
            self.frame(frame_real), momento=self.quando()
        )

        outra = self.instancia(calibracao, tmp_path, pasta)
        r = outra.tick(self.frame(frame_real), momento=self.quando(minutes=2))

        assert r.despachos == []
        assert r.ancoras_gravadas == [("Tiat North", OrigemDoAviso.CHAT)]
        assert (pasta / "nascimento_2026-08-30_tiat-north-2201_chat").exists()
        assert (
            len([n for n in os.listdir(pasta) if n.startswith("anuncio_")]) == 1
        )

    def test_o_REINICIO_nao_reenvia(self, calibracao, frame_real, tmp_path):
        """A terceira `Sessao` e o scanner subindo de novo: nada em memoria
        sobrevive, e o marcador em disco e o que cala."""
        pasta = tmp_path / "agenda"
        for _ in range(2):
            self.instancia(calibracao, tmp_path, pasta).tick(
                self.frame(frame_real), momento=self.quando()
            )

        terceira = self.instancia(calibracao, tmp_path, pasta)
        r = terceira.tick(self.frame(frame_real), momento=self.quando())

        assert r.despachos == []

    # -- as bordas ---------------------------------------------------------

    def test_em_simulacao_tres_instancias_repetem_e_o_disco_fica_vazio(
        self, calibracao, frame_real, tmp_path
    ):
        """Herdado de `marcar` e ACEITO, no molde de
        `TestOModoDeSimulacaoNaJanela`: o produto inteiro do `--dry-run` e a
        mensagem aparecer no console."""
        pasta = tmp_path / "agenda"
        despachos = 0
        for _ in range(3):
            s = self.instancia(calibracao, tmp_path, pasta, simulando=True)
            despachos += len(
                s.tick(self.frame(frame_real), momento=self.quando()).despachos
            )

        assert despachos == 3
        assert not pasta.exists()

    def test_um_anuncio_lixo_na_pasta_nao_derruba_o_tick(
        self, calibracao, frame_real, tmp_path
    ):
        pasta = tmp_path / "agenda"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "anuncio_lixo").touch()
        (pasta / "nascimento_lixo").touch()

        s = self.instancia(calibracao, tmp_path, pasta)
        r = s.tick(self.frame(frame_real), momento=self.quando())

        assert len(r.despachos) == 1
        assert not r.falhou_ao_analisar


# ---------------------------------------------------------------------------
# A MATRIZ DOS CRITERIOS 3, 4, 5 E 6 DA FASE 3.
#
# NAO MEXER EM `ancoras_mais_recentes` NEM EM `_PESO_DA_ORIGEM` PARA "MELHORAR"
# ESTES TESTES. Com a supressao ligada, uma remarcacao de alvo continua
# reescrevendo a ancora mais recente, e a mensagem de janela de daqui a seis
# horas vai citar o ALVO mesmo tendo havido anuncio no chat. Isso e o custo de
# D-15, apresentado ao usuario e aceito por ele, e D-27 manda preserva-lo:
# mexer ali mudaria o calculo da janela, que e Fase 2 verificada, e reabriria
# uma decisao que `03-CONTEXT.md` lista entre as ideias ADIADAS.
# ---------------------------------------------------------------------------


class BaseDaMatrizDeAnuncio:
    """O molde comum: dois bosses, um roteiro de ticks, uma pasta."""

    NORTH = Boss(nome="Tiat North", respawn_horas_min=6, respawn_horas_max=8)
    SOUTH = Boss(nome="Tiat South", respawn_horas_min=6, respawn_horas_max=8)

    ANUNCIO_SOUTH = "Tiat South [Lv. 60] has spawned!"
    ANUNCIO_NORTH = "Tiat North [Lv. 60] has spawned!"

    NASCIMENTO = datetime(2026, 8, 30, 21, 59)

    def quando(self, **desloc):
        return (self.NASCIMENTO + timedelta(**desloc)).timestamp()

    def vigia(self, pares):
        """`pares` e a lista `(chat, alvo)` que cada tick vai ler, em ordem.

        O vigia le os DOIS recortes uma vez por tick, o do chat antes do do
        alvo, entao um roteiro achatado casa tick a tick. Depois do fim do
        roteiro os recortes voltam limpos, que e o que acontece de verdade.
        """
        leituras = [texto for par in pares for texto in par]

        def ler(_pixels):
            return leituras.pop(0) if leituras else ""

        return VigiaDeBosses(
            ler,
            bosses=(self.NORTH, self.SOUTH),
            segundos_entre_leituras=1,
        )

    def frame(self, frame_real):
        recorte = np.zeros((5, 5, 3), dtype=np.uint8)
        return replace(
            frame_real, extras={"tiat_chat": recorte, "tiat_alvo": recorte}
        )

    def sessao(self, calibracao, tmp_path, pasta, pares, simulando=False):
        return nova_sessao(
            calibracao,
            tmp_path,
            registro=RegistroEmDisco(pasta, simulando=simulando),
            bosses=self.vigia(pares),
            regras_de_respawn=[self.NORTH, self.SOUTH],
        )

    @staticmethod
    def remarcacoes_de_alvo(nome, vezes):
        """O usuario desmarcando e remarcando o boss, `vezes` vezes.

        Sao TRES ticks por remarcacao porque `VigiaDeBosses` exige duas
        leituras limpas consecutivas para rearmar — e o rearme e justamente o
        que faz cada remarcacao produzir uma deteccao nova. Sem ele, o defeito
        de campo nao se reproduz.
        """
        return [("", nome), ("", ""), ("", "")] * vezes


class TestOAlvoCalaDepoisDeOChatFalar(BaseDaMatrizDeAnuncio):
    """CRITERIO 3 / UNIC-03 / D-25 — a metade maior do defeito de campo.

    Em 2026-08-30 o usuario recebeu tres mensagens de alvo depois das tres de
    chat, porque cada remarcacao rearmava o vigia e nada em disco lembrava que
    o boss ja tinha sido anunciado.
    """

    def _rodar(self, calibracao, frame_real, tmp_path, vezes=7):
        pasta = tmp_path / "agenda"
        pares = [(self.ANUNCIO_SOUTH, "")] + self.remarcacoes_de_alvo(
            "Tiat South", vezes
        )
        s = self.sessao(calibracao, tmp_path, pasta, pares)
        return pasta, [
            s.tick(self.frame(frame_real), momento=self.quando(minutes=i))
            for i in range(len(pares))
        ]

    def test_o_chat_anuncia_uma_vez_e_as_remarcacoes_nao_produzem_nada(
        self, calibracao, frame_real, tmp_path
    ):
        _pasta, ticks = self._rodar(calibracao, frame_real, tmp_path)

        assert ticks[0].avisos_de_boss == [
            ("Tiat South", OrigemDoAviso.CHAT)
        ]
        assert sum(len(t.despachos) for t in ticks[1:]) == 0

    # SETE, E NAO SEIS: o numero mudou no plano `03-02`, e mudou de proposito.
    #
    # Ate `03-01`, a PRIMEIRA remarcacao caia dentro do desarme EM MEMORIA que
    # a deteccao do chat acabava de fazer no vigia, e nunca chegava a virar
    # deteccao — o rearme era um flag por BOSS, e o chat desarmava o alvo
    # junto. `03-02` partiu esse estado por CANAL (D-24), porque o mesmo
    # desarme cruzado descartava o ANUNCIO DO SERVIDOR quando o boss ficava
    # segurado no alvo. Com os canais separados, as sete remarcacoes chegam, e
    # quem as cala e o MARCADOR.
    #
    # A ancora de origem `alvo` a mais e o custo aceito de D-15 (T-03-11): o
    # disco ganha uma por episodio, e D-16 manda a mensagem citar a origem
    # para quem le julgar. O que a divisao ensinava continua valendo e ficou
    # mais nitido: o filtro em memoria evita bater no disco enquanto o MESMO
    # sinal persiste NAQUELE canal, e o marcador e a garantia — ele e o unico
    # que sobrevive ao reinicio e o unico que existe entre as duas instancias.
    DETECCOES_DE_ALVO = 7

    def test_as_remarcacoes_CONTINUAM_gravando_ancora(
        self, calibracao, frame_real, tmp_path
    ):
        """Criterio 6 dentro do 3: a supressao e do ANUNCIO, nunca da
        ancoragem (D-27)."""
        pasta, ticks = self._rodar(calibracao, frame_real, tmp_path)

        por_alvo = [
            par
            for t in ticks[1:]
            for par in t.ancoras_gravadas
            if par[1] is OrigemDoAviso.ALVO
        ]
        assert len(por_alvo) == self.DETECCOES_DE_ALVO
        assert (
            len(
                [
                    n
                    for n in os.listdir(pasta)
                    if n.startswith("nascimento_") and n.endswith("_alvo")
                ]
            )
            == self.DETECCOES_DE_ALVO
        )

    def test_cada_deteccao_calada_deixa_rastro(
        self, calibracao, frame_real, tmp_path
    ):
        """T-03-05: sem rastro, o unico sintoma de uma supressao errada e o
        silencio, e ninguem percebe um alerta que nao chegou."""
        _pasta, ticks = self._rodar(calibracao, frame_real, tmp_path)

        calados = [par for t in ticks for par in t.nascimentos_calados]
        assert (
            calados
            == [("Tiat South", OrigemDoAviso.ALVO)] * self.DETECCOES_DE_ALVO
        )

    def test_o_silencio_sai_no_log_com_o_boss(
        self, calibracao, frame_real, tmp_path, caplog
    ):
        pasta = tmp_path / "agenda"
        # DUAS remarcacoes, DUAS supressoes: desde `03-02` o alvo tem estado
        # de rearme proprio, entao a primeira remarcacao tambem chega ao
        # marcador em vez de morrer no desarme que a deteccao do chat fez.
        # Ver `DETECCOES_DE_ALVO` acima.
        pares = [(self.ANUNCIO_SOUTH, "")] + self.remarcacoes_de_alvo(
            "Tiat South", 2
        )
        s = self.sessao(calibracao, tmp_path, pasta, pares)

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            for i in range(len(pares)):
                s.tick(self.frame(frame_real), momento=self.quando(minutes=i))

        calados = [m for m in caplog.messages if "calado" in m]
        assert len(calados) == 2
        assert all("Tiat South" in mensagem for mensagem in calados)


class TestOFallbackDoAlvoContinuaExistindo(BaseDaMatrizDeAnuncio):
    """CRITERIO 4 / UNIC-04 / D-25.

    O alvo existe para o caso que o usuario descreveu: o scanner perdeu o
    anuncio (estava fechado, ou o OCR falhou) e o boss esta na frente dele.
    Calar o alvo por completo trocaria uma repeticao barata por um nascimento
    perdido.
    """

    def test_sem_o_chat_o_alvo_anuncia_UMA_vez(
        self, calibracao, frame_real, tmp_path
    ):
        pasta = tmp_path / "agenda"
        pares = self.remarcacoes_de_alvo("Tiat South", 3)
        s = self.sessao(calibracao, tmp_path, pasta, pares)

        ticks = [
            s.tick(self.frame(frame_real), momento=self.quando(minutes=i))
            for i in range(len(pares))
        ]

        despachados = [t for t in ticks if t.despachos]
        assert len(despachados) == 1
        texto, _categoria, _alvo = despachados[0].despachos[0]
        assert "seu alvo virou" in texto
        assert despachados[0].avisos_de_boss == [
            ("Tiat South", OrigemDoAviso.ALVO)
        ]

    def test_as_remarcacoes_seguintes_calam(
        self, calibracao, frame_real, tmp_path
    ):
        pasta = tmp_path / "agenda"
        pares = self.remarcacoes_de_alvo("Tiat South", 3)
        s = self.sessao(calibracao, tmp_path, pasta, pares)

        ticks = [
            s.tick(self.frame(frame_real), momento=self.quando(minutes=i))
            for i in range(len(pares))
        ]

        assert [par for t in ticks for par in t.nascimentos_calados] == [
            ("Tiat South", OrigemDoAviso.ALVO)
        ] * 2


class TestOSilencioAcabaQuandoONascimentoVoltaASerPossivel(
    BaseDaMatrizDeAnuncio
):
    """CRITERIO 5 / UNIC-05 / D-26 / D-29 / T-03-01.

    O TESTE MAIS IMPORTANTE DO PLANO. Ele e a prova de que a supressao nao
    virou PERDA: o silencio termina no instante em que o proximo nascimento se
    torna POSSIVEL pela regra do `[[boss]]`, e nao no instante em que ele se
    torna provavel. Terminar mais tarde seria confortavel no papel e custaria
    um nascimento real, sem deixar rastro nenhum — ninguem percebe um alerta
    que nao chegou.

    E por isso que `MARGEM_DO_EPISODIO` vai para o lado CURTO: a janela do
    episodio e `respawn_horas_min` MENOS cinco minutos, deliberadamente mais
    curta que o minimo do servidor. Longa demais, ela funde dois nascimentos e
    cala o segundo, que e a falha invisivel; curta demais, ela repete uma
    mensagem, que o usuario le e ignora em dois segundos.
    """

    def _dois_anuncios(self, calibracao, frame_real, tmp_path, **intervalo):
        pasta = tmp_path / "agenda"
        pares = [
            (self.ANUNCIO_SOUTH, ""),
            ("", ""),
            ("", ""),
            (self.ANUNCIO_SOUTH, ""),
        ]
        s = self.sessao(calibracao, tmp_path, pasta, pares)

        s.tick(self.frame(frame_real), momento=self.quando())
        s.tick(self.frame(frame_real), momento=self.quando(minutes=1))
        s.tick(self.frame(frame_real), momento=self.quando(minutes=2))
        return s.tick(self.frame(frame_real), momento=self.quando(**intervalo))

    def test_um_segundo_nascimento_em_respawn_horas_min_AINDA_ANUNCIA(
        self, calibracao, frame_real, tmp_path
    ):
        r = self._dois_anuncios(calibracao, frame_real, tmp_path, hours=6)

        assert r.avisos_de_boss == [("Tiat South", OrigemDoAviso.CHAT)]
        assert r.nascimentos_calados == []

    def test_um_segundo_anuncio_dez_minutos_depois_CALA(
        self, calibracao, frame_real, tmp_path
    ):
        r = self._dois_anuncios(calibracao, frame_real, tmp_path, minutes=10)

        assert r.avisos_de_boss == []
        assert r.nascimentos_calados == [("Tiat South", OrigemDoAviso.CHAT)]

    def test_o_episodio_e_por_boss_e_o_outro_nao_e_calado_junto(
        self, calibracao, frame_real, tmp_path
    ):
        pasta = tmp_path / "agenda"
        pares = [(self.ANUNCIO_SOUTH, ""), (self.ANUNCIO_NORTH, "")]
        s = self.sessao(calibracao, tmp_path, pasta, pares)

        s.tick(self.frame(frame_real), momento=self.quando())
        r = s.tick(self.frame(frame_real), momento=self.quando(minutes=1))

        assert r.avisos_de_boss == [("Tiat North", OrigemDoAviso.CHAT)]


class TestAAncoragemSobreviveASupressao(BaseDaMatrizDeAnuncio):
    """CRITERIO 6 / UNIC-06 / D-27 — a Fase 2 continua inteira.

    A ancora nao muda de comportamento nesta fase. O teste afirma isso pelo
    ARQUIVO em disco, e nao so pelo `ResultadoDoTick`: um campo de resultado
    pode ser preenchido sem nada ter sido gravado, e o que a Fase 2 le seis
    horas depois e o disco.
    """

    def test_a_ancora_do_alvo_existe_em_disco_com_o_anuncio_suprimido(
        self, calibracao, frame_real, tmp_path
    ):
        pasta = tmp_path / "agenda"
        pares = [(self.ANUNCIO_SOUTH, ""), ("", ""), ("", ""), ("", "Tiat South")]
        s = self.sessao(calibracao, tmp_path, pasta, pares)

        for i in range(3):
            s.tick(self.frame(frame_real), momento=self.quando(minutes=i))
        r = s.tick(self.frame(frame_real), momento=self.quando(minutes=6))

        assert r.despachos == []
        assert r.ancoras_gravadas == [("Tiat South", OrigemDoAviso.ALVO)]
        assert (pasta / "nascimento_2026-08-30_tiat-south-2205_alvo").exists()

    def test_a_previsao_de_janela_continua_saindo_depois_de_uma_supressao(
        self, calibracao, frame_real, tmp_path
    ):
        """A ancora reescrita pelo alvo continua mandando na previsao — e o
        custo de D-15, que esta fase preserva de proposito."""
        pasta = tmp_path / "agenda"
        pares = [(self.ANUNCIO_SOUTH, ""), ("", ""), ("", ""), ("", "Tiat South")]
        s = self.sessao(calibracao, tmp_path, pasta, pares)

        for i in range(3):
            s.tick(self.frame(frame_real), momento=self.quando(minutes=i))
        s.tick(self.frame(frame_real), momento=self.quando(minutes=6))

        r = s.tick(
            self.frame(frame_real), momento=self.quando(hours=6, minutes=6)
        )

        assert [tipo for _boss, tipo in r.avisos_de_janela] == [
            TipoDeJanela.ABRE
        ]


class TestOQueASupressaoPERDE(BaseDaMatrizDeAnuncio):
    """O preco de D-26, AFIRMADO e nao escondido.

    Um comportamento aceito nunca fica sem teste neste projeto: sem um teste
    nomeado, a perda vira surpresa no dia em que alguem a descobrir em campo.
    """

    def test_dois_nascimentos_dentro_da_janela_produzem_UMA_mensagem(
        self, calibracao, frame_real, tmp_path
    ):
        """D-26 literal. O que se perde e o MESMO boss nascer duas vezes dentro
        da mesma janela, e isso e impossivel pela regra do servidor: o respawn
        conta a partir da MORTE, entao dois nascimentos distam no minimo
        `respawn_horas_min`.
        """
        pasta = tmp_path / "agenda"
        pares = [
            (self.ANUNCIO_SOUTH, ""),
            ("", ""),
            ("", ""),
            (self.ANUNCIO_SOUTH, ""),
        ]
        s = self.sessao(calibracao, tmp_path, pasta, pares)

        ticks = [
            s.tick(self.frame(frame_real), momento=self.quando(hours=h))
            for h in (0, 1, 2, 3)
        ]

        assert sum(len(t.avisos_de_boss) for t in ticks) == 1

    def test_em_simulacao_a_mesma_sessao_repete_e_o_disco_fica_vazio(
        self, calibracao, frame_real, tmp_path
    ):
        """Molde de `TestOModoDeSimulacaoNaJanela`: um comportamento aceito e
        AFIRMADO, nunca consertado."""
        pasta = tmp_path / "agenda"
        pares = [
            (self.ANUNCIO_SOUTH, ""),
            ("", ""),
            ("", ""),
            (self.ANUNCIO_SOUTH, ""),
            ("", ""),
            ("", ""),
            (self.ANUNCIO_SOUTH, ""),
        ]
        s = self.sessao(calibracao, tmp_path, pasta, pares, simulando=True)

        ticks = [
            s.tick(self.frame(frame_real), momento=self.quando(minutes=i))
            for i in range(len(pares))
        ]

        assert sum(len(t.avisos_de_boss) for t in ticks) == 3
        assert not pasta.exists()
