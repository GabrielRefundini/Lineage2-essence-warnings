"""O bug relatado, escrito como teste — de ponta a ponta.

O usuario tem dual boot. O Linux grava o relogio do hardware em UTC, o Windows
le o mesmo valor como hora local, e ao voltar do Linux o Windows fica ~3h
adiantado ate se corrigir sozinho.

`test_relogio.py` prova que o `Relogio` e imune ao pulo. ISTO AQUI prova a
outra metade, que e a que o usuario sente: que a hora ancorada chega DE FATO na
agenda, e que a hora torta a MATA. Um erro de 3h nao atrasa o aviso de TvT — ele
o APAGA, porque `avisos_devidos` so dispara dentro de `TOLERANCIA_MINUTOS = 5`
depois do alvo e 3h atravessam a janela inteira sem toca-la. Falha em silencio,
o pior modo de falha deste projeto.

Exercitado pelo nucleo testavel (`Sessao.tick`), nunca pelo `while`: o laco
precisa de jogo aberto, e a fase "o tick sai do laco e vira testavel" existiu
exatamente para isto.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import cv2
import pytest

from l2scanner.agenda import EventoAgendado, RegistroEmDisco
from l2scanner.calibracao import Calibracao
from l2scanner.config import ConfigAusente
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.rastreador import Rastreador
from l2scanner.relogio import Relogio
from l2scanner.sessao import Sessao

SEGUNDA = datetime(2026, 8, 24)
FIXTURES = Path(__file__).parent / "fixtures" / "party_estavel_com_vazamento"
TRES_HORAS = 3 * 3600.0

# 14:50 — exatamente 10 minutos antes do TvT das 15:00, que e quando o aviso
# de antecedencia vence. E o unico instante do dia em que este teste distingue
# um relogio certo de um errado.
HORA_DO_SERVIDOR = SEGUNDA.replace(hour=14, minute=50).timestamp()


class SilencioFalso:
    """Sem janela de silencio: aqui o assunto e o aviso, nao o mute."""

    janela = None

    def ativo(self) -> bool:
        return False

    def atualizar(self, agora):
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


@pytest.fixture
def tvt():
    """Um unico horario, de proposito: com varios, um relogio 3h adiantado
    poderia cair por acaso na janela de outra ocorrencia e o teste passaria
    sem que nada estivesse certo."""
    return EventoAgendado(
        nome="TvT",
        horarios=((15, 0),),
        avisar_minutos_antes=10,
        avisar_no_horario=False,
    )


def nova_sessao(calibracao, tmp_path, eventos):
    # tmp_path porque os marcadores de "ja avisei" sao DURAVEIS: cair no
    # .agenda/ de verdade cancelaria um aviso real do usuario.
    return Sessao(
        cal=calibracao,
        rastreador=Rastreador(nomes=list(calibracao.nomes)),
        eventos_agendados=list(eventos),
        registro=RegistroEmDisco(tmp_path),
        silencio=SilencioFalso(),
    )


def relogio_ancorado_com_windows_adiantado() -> Relogio:
    """A situacao do usuario: servidor as 14:50, Windows achando que sao 17:50."""
    relogio = Relogio(
        fonte=lambda: HORA_DO_SERVIDOR,
        monotonico=lambda: 1000.0,
        parede=lambda: HORA_DO_SERVIDOR + TRES_HORAS,
    )
    assert relogio.sincronizar() is True
    return relogio


class TestAAgendaLeAHoraAncorada:
    def test_com_a_hora_do_servidor_o_aviso_de_tvt_sai(
        self, calibracao, frame_real, tmp_path, tvt
    ):
        """O caso que o usuario perdeu quatro vezes por semana.

        O relogio do Windows esta 3h adiantado, mas o `momento` que desce para
        o tick vem do relogio ancorado — entao a agenda ve 14:50 e o lembrete
        do TvT das 15:00 sai.
        """
        relogio = relogio_ancorado_com_windows_adiantado()
        sessao = nova_sessao(calibracao, tmp_path, [tvt])

        resultado = sessao.tick(frame_real, relogio.agora_epoch())

        assert resultado.avisos, "o aviso de TvT nao saiu com a hora certa"
        assert "TvT" in resultado.avisos[0]

    def test_com_a_hora_torta_do_windows_o_aviso_MORRE_EM_SILENCIO(
        self, calibracao, frame_real, tmp_path, tvt
    ):
        """O contrario, para o teste acima nao passar por acaso.

        Este e literalmente o bug: nada explode, nada aparece no log, o aviso
        so nao acontece. Se um dia esta afirmacao passar a falhar porque o
        aviso SAIU, e porque a tolerancia virou larga o bastante para engolir
        3h — e ai o teste de cima deixou de provar qualquer coisa.
        """
        sessao = nova_sessao(calibracao, tmp_path, [tvt])

        # Exatamente o epoch que `time.time()` devolvia antes deste plano.
        resultado = sessao.tick(frame_real, HORA_DO_SERVIDOR + TRES_HORAS)

        assert resultado.avisos == []

    def test_o_pulo_depois_do_arranque_nao_move_a_agenda(
        self, calibracao, frame_real, tmp_path, tvt
    ):
        """O scanner ja estava rodando quando o Windows saltou 3h.

        E o cenario real: o usuario abre o scanner, vai para o Linux, volta, e
        o Windows se descorrige no meio da sessao. Depois de ancorado o avanco
        vem do monotonico, entao a agenda nem fica sabendo.
        """
        mono = [1000.0]
        parede = [HORA_DO_SERVIDOR]
        relogio = Relogio(
            fonte=lambda: HORA_DO_SERVIDOR,
            monotonico=lambda: mono[0],
            parede=lambda: parede[0],
        )
        relogio.sincronizar()

        parede[0] += TRES_HORAS  # o dual boot voltando do Linux

        sessao = nova_sessao(calibracao, tmp_path, [tvt])
        resultado = sessao.tick(frame_real, relogio.agora_epoch())

        assert resultado.avisos, "o pulo do Windows apagou o aviso"


class TestArranqueSemRede:
    """Sem rede, sem .env e sem Chatwoot o scanner TEM que subir.

    A fonte de hora nao pode virar mais um motivo para o produto nao abrir —
    e a mesma regra de `montar_despachante`, que degrada para o console em vez
    de morrer.
    """

    def test_fonte_que_sempre_falha_devolve_um_relogio_utilizavel(self):
        from l2scanner.__main__ import montar_relogio

        def sem_rede():
            raise OSError("getaddrinfo failed")

        relogio = montar_relogio(argparse.Namespace(), fonte=sem_rede)

        assert isinstance(relogio, Relogio)
        assert relogio.confiavel is False
        assert isinstance(relogio.agora(), datetime)

    def test_sem_env_o_arranque_nao_levanta(self, monkeypatch):
        """--dry-run, offline e sem .env e o caminho de quem so quer o TvT.

        Monkeypatch em `config_do_chatwoot` porque o .env de verdade do usuario
        nao pode entrar no teste: ele existe nesta maquina e faria a suite bater
        na rede.
        """
        from l2scanner import __main__ as principal

        def sem_env(*_args, **_kwargs):
            raise ConfigAusente("Nao encontrei o .env.")

        monkeypatch.setattr(principal, "config_do_chatwoot", sem_env)

        relogio = principal.montar_relogio(argparse.Namespace())

        assert relogio.confiavel is False
        assert isinstance(relogio.agora(), datetime)

    def test_nao_ancorado_a_agenda_ainda_funciona_com_a_hora_da_maquina(
        self, calibracao, frame_real, tmp_path, tvt
    ):
        """Degradar nao e desligar. Sem ancora o scanner segue avisando — com
        a hora que a maquina der, que e o que o WARNING do arranque diz."""
        relogio = Relogio(fonte=None, parede=lambda: HORA_DO_SERVIDOR)
        sessao = nova_sessao(calibracao, tmp_path, [tvt])

        resultado = sessao.tick(frame_real, relogio.agora_epoch())

        assert resultado.avisos
