"""A agenda: o relogio como fonte de eventos.

Todos estes testes rodam em milissegundos porque a agenda nao tem relogio
proprio — o tempo entra por parametro, igual ao rastreador. Sem essa
disciplina, testar "o TvT das 21h50 de uma quinta" exigiria esperar ate quinta
as 21h50, e a agenda nunca teria cobertura de verdade.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from l2scanner.agenda import (
    TODOS_OS_DIAS,
    AgendaInvalida,
    Aviso,
    EventoAgendado,
    TipoDeAviso,
    avisos_devidos,
    proxima_ocorrencia,
    texto_do_aviso,
)
from l2scanner.config import ler_agenda

# Uma segunda-feira, para os testes que precisam de um dia conhecido.
SEGUNDA = datetime(2026, 8, 24)
assert SEGUNDA.weekday() == 0


def evento(**kwargs) -> EventoAgendado:
    padroes = dict(
        nome="TvT", horarios=((15, 0),), dias=TODOS_OS_DIAS, avisar_minutos_antes=10
    )
    padroes.update(kwargs)
    return EventoAgendado(**padroes)


def em(hora: int, minuto: int, dia: datetime = SEGUNDA) -> datetime:
    return dia.replace(hour=hora, minute=minuto)


class TestAvisosDevidos:
    def test_avisa_dez_minutos_antes(self):
        devidos = avisos_devidos(em(14, 50), [evento()], set())
        assert [a.tipo for a in devidos] == [TipoDeAviso.ANTES]
        assert devidos[0].alvo == em(15, 0)

    def test_avisa_no_horario(self):
        devidos = avisos_devidos(em(15, 0), [evento()], set())
        assert [a.tipo for a in devidos] == [TipoDeAviso.AGORA]

    def test_nao_avisa_fora_da_janela(self):
        assert avisos_devidos(em(14, 30), [evento()], set()) == []
        assert avisos_devidos(em(16, 0), [evento()], set()) == []

    def test_aviso_vencido_nao_ressuscita(self):
        """Subir o scanner as 16h nao pode soltar o aviso das 15h.

        A party receberia um lembrete de um TvT que ja acabou — pior do que
        nao avisar, porque destroi a confianca no que o scanner diz.
        """
        assert avisos_devidos(em(16, 0), [evento()], set()) == []

    def test_dispara_dentro_da_tolerancia(self):
        """Um restart demorado nao pode custar o aviso."""
        devidos = avisos_devidos(em(15, 2), [evento()], set())
        assert [a.tipo for a in devidos] == [TipoDeAviso.AGORA]

    def test_ja_enviado_nao_repete(self):
        primeiro = avisos_devidos(em(15, 0), [evento()], set())
        assert len(primeiro) == 1
        de_novo = avisos_devidos(em(15, 0), [evento()], {primeiro[0].chave})
        assert de_novo == []

    def test_antecedencia_zero_nao_duplica(self):
        """Com 0 minutos de antecedencia o 'antes' coincidiria com o 'agora'."""
        devidos = avisos_devidos(em(15, 0), [evento(avisar_minutos_antes=0)], set())
        assert [a.tipo for a in devidos] == [TipoDeAviso.AGORA]


class TestDiasDaSemana:
    @pytest.mark.parametrize("deslocamento", range(7))
    def test_evento_de_todo_dia_dispara_nos_sete(self, deslocamento):
        from datetime import timedelta

        dia = SEGUNDA + timedelta(days=deslocamento)
        devidos = avisos_devidos(em(15, 0, dia), [evento()], set())
        assert len(devidos) == 1, f"falhou no dia {dia:%A}"

    def test_prime_so_de_segunda_a_quinta(self):
        from datetime import timedelta

        prime = evento(
            nome="Prime", horarios=((20, 0),), dias=frozenset({0, 1, 2, 3})
        )
        disparou = []
        for deslocamento in range(7):
            dia = SEGUNDA + timedelta(days=deslocamento)
            if avisos_devidos(em(20, 0, dia), [prime], set()):
                disparou.append(dia.weekday())
        assert disparou == [0, 1, 2, 3], "Prime vazou para sexta, sabado ou domingo"

    def test_sexta_as_20h_nao_produz_prime(self):
        from datetime import timedelta

        sexta = SEGUNDA + timedelta(days=4)
        prime = evento(nome="Prime", horarios=((20, 0),), dias=frozenset({0, 1, 2, 3}))
        assert avisos_devidos(em(20, 0, sexta), [prime], set()) == []


class TestViradaDeDia:
    """O dia da semana vale para o EVENTO, nunca para o aviso.

    Um evento a 00:05 de segunda avisa as 23:55 de DOMINGO. Se a checagem de
    dia olhasse o dia do aviso, esse evento nunca seria anunciado.
    """

    def test_aviso_da_vespera_pertence_ao_evento_do_dia_seguinte(self):
        from datetime import timedelta

        domingo = SEGUNDA - timedelta(days=1)
        madrugada = evento(horarios=((0, 5),), dias=frozenset({0}))  # so segunda

        devidos = avisos_devidos(em(23, 55, domingo), [madrugada], set())
        assert len(devidos) == 1
        assert devidos[0].tipo is TipoDeAviso.ANTES
        assert devidos[0].alvo.weekday() == 0, "o alvo tem que ser a SEGUNDA"

    def test_proxima_ocorrencia_atravessa_a_meia_noite(self):
        proximo = proxima_ocorrencia(em(23, 50), [evento()])
        assert proximo is not None
        nome, quando = proximo
        assert nome == "TvT"
        assert quando == em(15, 0) .replace(day=SEGUNDA.day + 1)

    def test_proxima_ocorrencia_pula_para_a_semana_seguinte(self):
        from datetime import timedelta

        sexta = SEGUNDA + timedelta(days=4)
        prime = evento(nome="Prime", horarios=((20, 0),), dias=frozenset({0}))
        proximo = proxima_ocorrencia(em(21, 0, sexta), [prime])
        assert proximo is not None
        assert proximo[1].weekday() == 0

    def test_agenda_vazia_nao_tem_proxima(self):
        assert proxima_ocorrencia(em(12, 0), []) is None


class TestChaveDoAviso:
    def test_chave_e_estruturada_e_nao_o_texto(self):
        """O texto muda quando alguem melhora a redacao. A chave nao pode."""
        aviso = Aviso(
            evento="TvT",
            tipo=TipoDeAviso.ANTES,
            alvo=em(21, 50),
            devido_em=em(21, 40),
        )
        assert aviso.chave == "2026-08-24_tvt-2150_antes"

    def test_horarios_diferentes_tem_chaves_diferentes(self):
        chaves = {
            Aviso("TvT", TipoDeAviso.AGORA, em(h, m), em(h, m)).chave
            for h, m in ((15, 0), (17, 0), (21, 50))
        }
        assert len(chaves) == 3

    def test_nome_com_espaco_vira_chave_segura_para_arquivo(self):
        aviso = Aviso("Cerco de Aden", TipoDeAviso.AGORA, em(15, 0), em(15, 0))
        assert "cerco-de-aden" in aviso.chave
        assert " " not in aviso.chave


class TestTextoDoAviso:
    def test_antes_e_agora_dizem_coisas_diferentes(self):
        alvo = em(21, 50)
        antes = texto_do_aviso(Aviso("TvT", TipoDeAviso.ANTES, alvo, em(21, 40)))
        agora = texto_do_aviso(Aviso("TvT", TipoDeAviso.AGORA, alvo, alvo))
        assert antes != agora
        assert "21:50" in antes and "21:50" in agora
        assert "10 minutos" in antes


class TestLerAgenda:
    def test_arquivo_ausente_nao_e_erro(self, tmp_path):
        """O scanner roda sem agenda desde a v1 e precisa continuar rodando.

        Quem nunca criou o arquivo nao pode ver o programa quebrar por causa de
        uma funcionalidade que nao pediu.
        """
        assert ler_agenda(tmp_path / "nao-existe.toml") == []

    def test_le_um_evento(self, tmp_path):
        caminho = tmp_path / "config.toml"
        caminho.write_text(
            '[[evento]]\nnome = "TvT"\nhorarios = ["15:00", "21:50"]\n'
            'dias = ["seg", "dom"]\navisar_minutos_antes = 10\n'
            "silenciar_minutos = 15\n",
            encoding="utf-8",
        )
        eventos = ler_agenda(caminho)
        assert len(eventos) == 1
        assert eventos[0].nome == "TvT"
        assert eventos[0].horarios == ((15, 0), (21, 50))
        assert eventos[0].dias == frozenset({0, 6})
        assert eventos[0].silenciar_minutos == 15

    def test_sem_dias_vale_todo_dia(self, tmp_path):
        caminho = tmp_path / "config.toml"
        caminho.write_text(
            '[[evento]]\nnome = "TvT"\nhorarios = ["15:00"]\n', encoding="utf-8"
        )
        assert ler_agenda(caminho)[0].dias == TODOS_OS_DIAS

    @pytest.mark.parametrize(
        "corpo,trecho_esperado",
        [
            ('[[evento]]\nnome = "X"\nhorarios = ["25:00"]\n', "nao existe"),
            ('[[evento]]\nnome = "X"\nhorarios = ["15h"]\n', "HH:MM"),
            ('[[evento]]\nnome = "X"\nhorarios = []\n', "vazio"),
            ('[[evento]]\nhorarios = ["15:00"]\n', "nome"),
            ('[[evento]]\nnome = "X"\nhorarios = ["15:00"]\ndias = ["sabado?"]\n', "dia"),
            (
                '[[evento]]\nnome = "X"\nhorarios = ["15:00"]\navisar_minutos_antes = -1\n',
                "avisar_minutos_antes",
            ),
        ],
    )
    def test_config_errada_falha_no_arranque_com_mensagem_util(
        self, tmp_path, corpo, trecho_esperado
    ):
        """Erro de digitacao derruba o scanner AGORA, nao as 15h.

        O usuario esta olhando para o console quando sobe o programa. As 15h
        ele esta AFK confiando no silencio.
        """
        caminho = tmp_path / "config.toml"
        caminho.write_text(corpo, encoding="utf-8")
        with pytest.raises(AgendaInvalida) as erro:
            ler_agenda(caminho)
        assert trecho_esperado in str(erro.value)

    def test_a_mensagem_cita_o_nome_do_evento(self, tmp_path):
        """'O terceiro [[evento]] esta errado' faz o usuario contar blocos."""
        caminho = tmp_path / "config.toml"
        caminho.write_text(
            '[[evento]]\nnome = "TvT"\nhorarios = ["15:00"]\n'
            '[[evento]]\nnome = "Prime"\nhorarios = ["99:00"]\n',
            encoding="utf-8",
        )
        with pytest.raises(AgendaInvalida) as erro:
            ler_agenda(caminho)
        assert "Prime" in str(erro.value)

    def test_toml_quebrado_diz_que_e_toml_quebrado(self, tmp_path):
        caminho = tmp_path / "config.toml"
        caminho.write_text("[[evento]\nnome =", encoding="utf-8")
        with pytest.raises(AgendaInvalida) as erro:
            ler_agenda(caminho)
        assert "TOML" in str(erro.value)
