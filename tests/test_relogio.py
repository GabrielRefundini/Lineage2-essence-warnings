"""Testes do relogio ancorado — a hora nao pode vir de um relogio que mente.

O PC do usuario e dual boot. O Linux grava o relogio do hardware em UTC, o
Windows le o mesmo valor como hora local, e ao voltar do Linux o Windows fica
~3h adiantado ate sincronizar sozinho. A agenda lia esse relogio a cada tick, e
um erro de 3h atravessa INTEIRA a janela de tolerancia de 5 minutos do aviso:
o aviso de TvT nao saia nenhuma vez, em silencio.

Todo teste aqui injeta monotonico e parede. Nao ha rede, nao ha sleep e nao ha
monkeypatch em lugar nenhum — a mesma disciplina de agenda.py, onde o tempo
entra por parametro.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from l2scanner.relogio import Relogio, epoch_do_cabecalho_date

# 25/08/2026 11:46:09 UTC — a hora que o servidor diz.
EPOCH_SERVIDOR = datetime(2026, 8, 25, 11, 46, 9, tzinfo=timezone.utc).timestamp()
TRES_HORAS = 3 * 3600.0


class Maquina:
    """O relogio da maquina, sob controle do teste."""

    def __init__(self, mono: float = 1000.0, parede: float = EPOCH_SERVIDOR) -> None:
        self.mono = mono
        self.parede = parede

    def monotonico(self) -> float:
        return self.mono

    def de_parede(self) -> float:
        return self.parede

    def andar(self, segundos: float) -> None:
        """Tempo passando de verdade: os dois relogios andam juntos."""
        self.mono += segundos
        self.parede += segundos

    def pular_parede(self, segundos: float) -> None:
        """O que o dual boot faz: so o relogio de parede salta."""
        self.parede += segundos


def montar(maquina: Maquina, fonte) -> Relogio:
    return Relogio(
        fonte=fonte, monotonico=maquina.monotonico, parede=maquina.de_parede
    )


class TestAncoragem:
    def test_ancorado_a_hora_vem_do_servidor_e_nao_da_maquina(self):
        """Ancorar so vale se a hora da maquina deixar de ser consultada."""
        maquina = Maquina(parede=EPOCH_SERVIDOR + TRES_HORAS)
        relogio = montar(maquina, lambda: EPOCH_SERVIDOR)

        assert relogio.sincronizar() is True
        assert relogio.confiavel is True
        assert relogio.agora_epoch() == pytest.approx(EPOCH_SERVIDOR)

    def test_fonte_indisponivel_cai_no_relogio_de_parede_sem_levantar(self):
        """A fonte e rede, e rede falha. Isso nunca pode derrubar o scanner.

        Sem rede, sem .env e sem Chatwoot o scanner tem que subir do mesmo
        jeito — degradando para o relogio do Windows, nunca morrendo.
        """
        maquina = Maquina()

        def fonte_morta():
            raise OSError("sem rede")

        relogio = montar(maquina, fonte_morta)

        assert relogio.sincronizar() is False
        assert relogio.confiavel is False
        assert relogio.agora_epoch() == pytest.approx(maquina.parede)

    def test_fonte_sem_data_utilizavel_nao_ancora(self):
        """Resposta que chegou mas nao trouxe Date nao e ancora — e nada."""
        relogio = montar(Maquina(), lambda: None)

        assert relogio.sincronizar() is False
        assert relogio.confiavel is False

    def test_reancorar_troca_a_ancora_e_a_contagem_segue_dela(self):
        """A sincronizacao periodica so serve se a segunda ancora valer."""
        maquina = Maquina()
        epochs = [EPOCH_SERVIDOR, EPOCH_SERVIDOR + 600.0]
        relogio = montar(maquina, lambda: epochs.pop(0))

        relogio.sincronizar()
        maquina.andar(30.0)
        assert relogio.sincronizar() is True
        maquina.andar(10.0)

        assert relogio.agora_epoch() == pytest.approx(EPOCH_SERVIDOR + 610.0)


class TestImunidadeAoPulo:
    def test_pulo_de_tres_horas_no_windows_nao_move_a_hora_ancorada(self):
        """ESTE TESTE E O BUG. O usuario volta do Linux e o Windows salta 3h.

        Depois de ancorado, o scanner conta pelo monotonico: se o monotonico
        andou 10s, passaram-se 10s — nao importa o que o Windows ache.
        """
        maquina = Maquina()
        relogio = montar(maquina, lambda: EPOCH_SERVIDOR)
        relogio.sincronizar()

        maquina.andar(10.0)
        maquina.pular_parede(TRES_HORAS)  # o dual boot voltando do Linux

        assert relogio.agora_epoch() == pytest.approx(EPOCH_SERVIDOR + 10.0)

    def test_sem_ancora_o_pulo_aparece_porque_o_fallback_e_honesto(self):
        """O fallback nao finge estabilidade que nao tem.

        Sem ancora a hora E a do Windows, com defeito e tudo. Esconder isso
        seria pior: o arranque avisa em WARNING justamente porque a hora
        passa a ser a que a maquina der.
        """
        maquina = Maquina()
        relogio = montar(maquina, lambda: None)
        relogio.sincronizar()

        antes = relogio.agora_epoch()
        maquina.pular_parede(TRES_HORAS)

        assert relogio.agora_epoch() - antes == pytest.approx(TRES_HORAS)


class TestCompensacaoDeLatencia:
    def test_ancora_fica_no_ponto_medio_da_requisicao(self):
        """O Date e do instante da resposta, e a viagem tem duracao.

        Prender a ancora ao MEIO da viagem corta o erro maximo pela metade e
        custa duas linhas. Com 2s de viagem: ancorar no fim erraria ate 2s,
        no meio erra no maximo 1s.
        """
        maquina = Maquina()

        def fonte_lenta():
            maquina.andar(2.0)
            return EPOCH_SERVIDOR

        relogio = montar(maquina, fonte_lenta)
        relogio.sincronizar()

        assert relogio.agora_epoch() == pytest.approx(EPOCH_SERVIDOR + 1.0)
        assert abs(relogio.agora_epoch() - EPOCH_SERVIDOR) <= 1.0


class TestDesvioDoWindows:
    def test_desvio_diz_quanto_a_maquina_esta_adiantada(self):
        """E o numero que o arranque imprime para o usuario entender o erro."""
        maquina = Maquina(parede=EPOCH_SERVIDOR + TRES_HORAS)
        relogio = montar(maquina, lambda: EPOCH_SERVIDOR)
        relogio.sincronizar()

        assert relogio.desvio_do_windows() == pytest.approx(TRES_HORAS)

    def test_desvio_negativo_quando_a_maquina_esta_atrasada(self):
        maquina = Maquina(parede=EPOCH_SERVIDOR - 120.0)
        relogio = montar(maquina, lambda: EPOCH_SERVIDOR)
        relogio.sincronizar()

        assert relogio.desvio_do_windows() == pytest.approx(-120.0)

    def test_sem_ancora_nao_ha_desvio_para_medir(self):
        """Sem uma segunda fonte nao ha com o que comparar — None, nao zero."""
        relogio = montar(Maquina(), lambda: None)

        assert relogio.desvio_do_windows() is None


class TestCabecalhoDate:
    def test_formato_rfc_7231_vira_o_epoch_utc_correto(self):
        assert epoch_do_cabecalho_date(
            "Mon, 25 Aug 2026 11:46:09 GMT"
        ) == pytest.approx(EPOCH_SERVIDOR)

    @pytest.mark.parametrize("lixo", ["", "nao e data", None, "   ", "25/08/2026"])
    def test_entrada_invalida_vira_none_sem_levantar(self, lixo):
        """Um cabecalho estranho nao pode derrubar o arranque do scanner."""
        assert epoch_do_cabecalho_date(lixo) is None

    def test_data_absurda_e_recusada(self):
        """Um intermediario quebrado nao pode reancorar o scanner em 1970.

        Ancorar no passado remoto seria pior que nao ancorar: a agenda
        acharia que todo aviso de hoje ja venceu ha decadas.
        """
        assert epoch_do_cabecalho_date("Thu, 01 Jan 1970 00:00:00 GMT") is None
        assert epoch_do_cabecalho_date("Sat, 01 Jan 2000 00:00:00 GMT") is None


class TestHoraLocal:
    def test_agora_devolve_datetime_ingenuo_na_hora_local(self):
        """A agenda inteira trabalha com datetime ingenuo, e de proposito.

        O dual boot estraga o RELOGIO, nao a configuracao de fuso. Hora certa
        de fora + fuso intacto = hora local certa.
        """
        maquina = Maquina(parede=EPOCH_SERVIDOR + TRES_HORAS)
        relogio = montar(maquina, lambda: EPOCH_SERVIDOR)
        relogio.sincronizar()

        agora = relogio.agora()

        assert isinstance(agora, datetime)
        assert agora.tzinfo is None
        assert agora == datetime.fromtimestamp(EPOCH_SERVIDOR)


class TestSincronizacaoPeriodica:
    def test_a_thread_e_daemon_para_nao_segurar_o_encerramento(self):
        """O laco de captura NUNCA pode bloquear em rede — a mesma razao pela
        qual o Despachante existe. E um Ctrl+C tem que encerrar na hora."""
        relogio = montar(Maquina(), lambda: EPOCH_SERVIDOR)

        thread = relogio.iniciar_sincronizacao_periodica(intervalo=3600)

        assert thread.daemon is True
        assert thread.is_alive()
