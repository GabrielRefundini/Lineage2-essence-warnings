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

    def test_a_antecedencia_pode_carregar_o_loot(self):
        """O aviso que ja existe ganha "Loot: X" no fim — e SO ele.

        A agenda nao conhece designacao nenhuma: quem decide SE ha loot e o
        chamador, a agenda so formata. Mesma linha do console nao ganhar
        relogio.
        """
        alvo = em(10, 0)
        aviso = Aviso("Solo Boss", TipoDeAviso.ANTES, alvo, em(9, 50))
        assert texto_do_aviso(aviso, loot="J4guar").endswith("Loot: J4guar.")

    def test_sem_loot_o_texto_e_byte_a_byte_o_de_hoje(self):
        """Regressao: toda chamada existente continua valida e identica."""
        alvo = em(21, 50)
        aviso = Aviso("TvT", TipoDeAviso.ANTES, alvo, em(21, 40))
        assert texto_do_aviso(aviso) == (
            "TvT comeca em 10 minutos, as 21:50. "
            "Hora de voltar para a cidade e se preparar."
        )

    def test_o_aviso_AGORA_nunca_ganha_a_linha(self):
        """So a antecedencia carrega o loot, por decisao do usuario. O Solo
        Boss nem tem aviso de AGORA — e nao deve ganhar a linha nem se
        tivesse."""
        alvo = em(10, 0)
        aviso = Aviso("Solo Boss", TipoDeAviso.AGORA, alvo, alvo)
        assert "Loot" not in texto_do_aviso(aviso, loot="J4guar")


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


class TestAgendaRealDoUsuario:
    """O `config.toml` versionado, exatamente como ele esta no repositorio.

    Estes testes existem para pegar um dedo errado no arquivo. A agenda e dado,
    nao codigo — mas um dado errado aqui significa a party esperando um TvT que
    nao vai acontecer, ou perdendo um que vai.
    """

    @pytest.fixture
    def agenda(self):
        from pathlib import Path

        raiz = Path(__file__).resolve().parent.parent
        return ler_agenda(raiz / "config.toml")

    def test_o_arquivo_do_repositorio_e_valido(self, agenda):
        assert len(agenda) == 3
        assert {e.nome for e in agenda} == {"TvT", "Prime", "Solo Boss"}

    def test_tvt_tem_os_horarios_do_config_todo_dia(self, agenda):
        tvt = next(e for e in agenda if e.nome == "TvT")
        assert tvt.horarios == ((15, 0), (17, 0), (21, 50), (23, 0))
        assert tvt.dias == TODOS_OS_DIAS

    def test_prime_as_20h_de_segunda_a_quinta(self, agenda):
        prime = next(e for e in agenda if e.nome == "Prime")
        assert prime.horarios == ((20, 0),)
        assert prime.dias == frozenset({0, 1, 2, 3})

    def test_as_duracoes_de_silencio_estao_no_esquema_para_a_fase_7(self, agenda):
        """Lidas e ignoradas nesta fase.

        Moram no arquivo desde ja para o usuario nao ter que editar a mao um
        config que ja editou quando a Fase 7 chegar.
        """
        por_nome = {e.nome: e for e in agenda}
        assert por_nome["TvT"].silenciar_minutos == 15
        assert por_nome["Prime"].silenciar_minutos == 120

    def _varrer_um_dia(self, agenda, dia):
        """Todos os avisos de um dia, minuto a minuto."""
        from datetime import timedelta

        enviados: set[str] = set()
        saidas = []
        instante = dia
        for _ in range(24 * 60):
            for aviso in avisos_devidos(instante, agenda, enviados):
                enviados.add(aviso.chave)
                saidas.append(
                    (aviso.evento, aviso.tipo, aviso.devido_em.strftime("%H:%M"))
                )
            instante += timedelta(minutes=1)
        return saidas

    def test_tvt_e_prime_numa_segunda_saem_na_ordem_e_hora_certas(self, agenda):
        """Varre a segunda inteira e confere a sequencia de TvT e Prime.

        Filtrado por evento de proposito: um evento NOVO no config.toml nao
        deve quebrar a asserção sobre os que ja existiam.
        """
        saidas = [
            s for s in self._varrer_um_dia(agenda, SEGUNDA)
            if s[0] in ("TvT", "Prime")
        ]
        assert saidas == [
            ("TvT", TipoDeAviso.ANTES, "14:50"),
            ("TvT", TipoDeAviso.AGORA, "15:00"),
            ("TvT", TipoDeAviso.ANTES, "16:50"),
            ("TvT", TipoDeAviso.AGORA, "17:00"),
            ("Prime", TipoDeAviso.ANTES, "19:50"),
            ("Prime", TipoDeAviso.AGORA, "20:00"),
            ("TvT", TipoDeAviso.ANTES, "21:40"),
            ("TvT", TipoDeAviso.AGORA, "21:50"),
            ("TvT", TipoDeAviso.ANTES, "22:50"),
            ("TvT", TipoDeAviso.AGORA, "23:00"),
        ]

    def test_solo_boss_avisa_de_duas_em_duas_horas_so_com_antecedencia(self, agenda):
        """12 ocorrencias em horario par, UM aviso cada.

        Com dois avisos cada seriam 24 mensagens por dia — tres vezes o volume
        de TvT e Prime somados. Por isso `avisar_no_horario = false`.
        """
        saidas = [
            s for s in self._varrer_um_dia(agenda, SEGUNDA) if s[0] == "Solo Boss"
        ]
        assert len(saidas) == 12
        assert all(tipo is TipoDeAviso.ANTES for _, tipo, _ in saidas), (
            "algum aviso saiu no horario; avisar_no_horario deveria estar false"
        )
        assert [hora for _, _, hora in saidas] == [
            f"{h:02d}:50" for h in list(range(1, 24, 2))
        ]

    def test_o_volume_diario_total_e_o_esperado(self, agenda):
        """20 mensagens por dia. Se subir, alguem mexeu no config sem pensar.

        O grupo do WhatsApp e de pessoas, nao um feed. Este teste existe para
        um evento novo nao dobrar o volume sem ninguem perceber.
        """
        assert len(self._varrer_um_dia(agenda, SEGUNDA)) == 22

    def test_no_sabado_o_prime_nao_aparece(self, agenda):
        from datetime import timedelta

        sabado = SEGUNDA + timedelta(days=5)
        enviados: set[str] = set()
        nomes = []
        instante = sabado
        for _ in range(24 * 60):
            for aviso in avisos_devidos(instante, agenda, enviados):
                enviados.add(aviso.chave)
                nomes.append(aviso.evento)
            instante += timedelta(minutes=1)

        assert "Prime" not in nomes
        assert nomes.count("TvT") == 8, "4 horarios de TvT x 2 avisos"

    def test_mudar_a_antecedencia_nao_exige_tocar_em_codigo(self, tmp_path):
        """AGEN-04: uma atualizacao do jogo nao pode custar um commit."""
        caminho = tmp_path / "config.toml"
        caminho.write_text(
            '[[evento]]\nnome = "TvT"\nhorarios = ["15:00"]\n'
            "avisar_minutos_antes = 25\n",
            encoding="utf-8",
        )
        eventos = ler_agenda(caminho)
        assert avisos_devidos(em(14, 35), eventos, set())[0].tipo is TipoDeAviso.ANTES
        assert avisos_devidos(em(14, 50), eventos, set()) == []


class TestRegistroEmDisco:
    """Um aviso, uma vez — a prova de restart e de duas instancias.

    O usuario roda DUAS instancias lado a lado (Yazalaque e Faerlina). Sem
    isto, o grupo receberia cada lembrete de TvT em dobro, todo dia, tres vezes
    por dia.
    """

    def test_duas_instancias_no_mesmo_instante_so_uma_envia(self, tmp_path):
        """A garantia central da tarefa.

        `O_CREAT | O_EXCL` e atomico no Windows: entre duas instancias
        competindo pelo mesmo aviso, exatamente uma cria o arquivo.
        """
        from l2scanner.agenda import RegistroEmDisco

        a = RegistroEmDisco(tmp_path)
        b = RegistroEmDisco(tmp_path)
        chave = "2026-08-24_tvt-1500_agora"

        assert [a.marcar(chave), b.marcar(chave)] == [True, False]

    def test_muitas_instancias_competindo_produzem_um_envio_so(self, tmp_path):
        from l2scanner.agenda import RegistroEmDisco

        chave = "2026-08-24_tvt-2150_antes"
        registros = [RegistroEmDisco(tmp_path) for _ in range(8)]
        assert sum(1 for r in registros if r.marcar(chave)) == 1

    def test_competicao_de_verdade_com_threads(self, tmp_path):
        """Nao basta chamar em sequencia — o risco e a corrida.

        Um "le o JSON, checa, escreve o JSON" passaria no teste sequencial e
        falharia aqui, porque tem janela entre o read e o write.
        """
        import threading

        from l2scanner.agenda import RegistroEmDisco

        chave = "2026-08-24_prime-2000_agora"
        vencedores = []
        trava = threading.Lock()
        largada = threading.Event()

        def tentar():
            registro = RegistroEmDisco(tmp_path)
            largada.wait()
            if registro.marcar(chave):
                with trava:
                    vencedores.append(1)

        threads = [threading.Thread(target=tentar) for _ in range(16)]
        for t in threads:
            t.start()
        largada.set()
        for t in threads:
            t.join()

        assert len(vencedores) == 1, f"{len(vencedores)} instancias enviariam"

    def test_reiniciar_o_scanner_nao_reenvia(self, tmp_path):
        """AGEN-06: o marcador esta em disco, entao sobrevive ao processo."""
        from l2scanner.agenda import RegistroEmDisco

        chave = "2026-08-24_tvt-1700_agora"
        assert RegistroEmDisco(tmp_path).marcar(chave) is True
        # processo morre, sobe de novo, do zero
        assert RegistroEmDisco(tmp_path).marcar(chave) is False

    def test_enviados_enxerga_o_que_a_outra_instancia_escreveu(self, tmp_path):
        from l2scanner.agenda import RegistroEmDisco

        a = RegistroEmDisco(tmp_path)
        b = RegistroEmDisco(tmp_path)
        a.marcar("2026-08-24_tvt-1500_antes")
        assert "2026-08-24_tvt-1500_antes" in b.enviados()

    def test_a_agenda_inteira_com_registro_duravel_nao_duplica(self, tmp_path):
        """Ponta a ponta: dois dias de agenda real, duas instancias, um envio."""
        from datetime import timedelta

        from l2scanner.agenda import RegistroEmDisco

        raiz = __import__("pathlib").Path(__file__).resolve().parent.parent
        agenda = ler_agenda(raiz / "config.toml")

        enviados_por = {"A": [], "B": []}
        instante = SEGUNDA
        for _ in range(2 * 24 * 60):
            for etiqueta in ("A", "B"):
                registro = RegistroEmDisco(tmp_path)
                for aviso in avisos_devidos(instante, agenda, registro.enviados()):
                    if registro.marcar(aviso.chave):
                        enviados_por[etiqueta].append(aviso.chave)
            instante += timedelta(minutes=1)

        todos = enviados_por["A"] + enviados_por["B"]
        assert len(todos) == len(set(todos)), "houve aviso duplicado"
        # 22 avisos por dia (TvT 8 + Prime 2 + Solo Boss 12), dois dias.
        assert len(todos) == 44

    def test_poda_apaga_o_velho_e_preserva_o_de_hoje(self, tmp_path):
        from datetime import date as _date

        from l2scanner.agenda import RegistroEmDisco

        registro = RegistroEmDisco(tmp_path)
        registro.marcar("2026-08-01_tvt-1500_agora")  # antigo
        registro.marcar("2026-08-24_tvt-1500_agora")  # de hoje

        apagados = registro.podar(hoje=_date(2026, 8, 24))

        assert apagados == 1
        assert registro.enviados() == {"2026-08-24_tvt-1500_agora"}

    def test_poda_nao_mexe_em_arquivo_que_nao_e_nosso(self, tmp_path):
        from datetime import date as _date

        from l2scanner.agenda import RegistroEmDisco

        (tmp_path / "leiame.txt").write_text("nao me apague", encoding="utf-8")
        registro = RegistroEmDisco(tmp_path)
        registro.podar(hoje=_date(2030, 1, 1))
        assert (tmp_path / "leiame.txt").exists()

    def test_a_pasta_e_criada_se_nao_existir(self, tmp_path):
        from l2scanner.agenda import RegistroEmDisco

        alvo = tmp_path / "nao" / "existe" / "ainda"
        RegistroEmDisco(alvo)
        assert alvo.is_dir()


class TestModoAgendaSemJogo:
    """AGEN-05 / OPER-09: o aviso vem do relogio, nao da tela.

    Quem mais precisa do lembrete de TvT e justamente quem NAO esta online. Se
    o aviso dependesse do jogo aberto, ele so sairia para quem ja esta jogando
    — que e quem menos precisa dele.
    """

    def _rodar(self, *args, timeout=60):
        import subprocess
        import sys
        from pathlib import Path

        raiz = Path(__file__).resolve().parent.parent
        return subprocess.run(
            [sys.executable, "-m", "l2scanner", *args],
            cwd=raiz,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def test_testar_agenda_funciona_sem_jogo_e_sem_calibracao(self):
        """Prova de ponta a ponta: nenhuma janela do jogo, nenhum pixel."""
        r = self._rodar("--testar-agenda", "--dry-run")
        assert r.returncode == 0, r.stdout + r.stderr
        assert "[simulacao]" in r.stdout

    def test_o_aviso_de_teste_nomeia_um_evento_da_agenda_real(self):
        r = self._rodar("--testar-agenda", "--dry-run")
        assert any(n in r.stdout for n in ("TvT", "Prime", "Solo Boss"))

    def test_as_flags_novas_existem(self):
        r = self._rodar("--help")
        assert "--so-agenda" in r.stdout
        assert "--testar-agenda" in r.stdout

    def test_o_modo_agenda_nao_exige_calibracao(self):
        """O despacho sai ANTES de carregar calibration.json.

        Exigir calibracao num modo que nao olha para a tela seria inventar um
        requisito que a funcionalidade nao tem — e impediria rodar a agenda
        numa maquina que nunca calibrou nada.
        """
        import inspect

        from l2scanner import __main__ as principal

        fonte = inspect.getsource(principal.main)
        pos_agenda = fonte.index("args.so_agenda")
        pos_calibracao = fonte.index("Calibracao.carregar")
        assert pos_agenda < pos_calibracao, (
            "o modo agenda esta atras da carga de calibracao"
        )


class TestJanelaDeSilencio:
    """Janelas sobrepostas sao UNIAO, e isso e correcao, nao refinamento.

    De segunda a quinta o Prime vai das 20:00 as 22:00 e o TvT das 21:50 vai
    ate 22:05. Substituir faria o silencio acabar as 22:00 e os ultimos cinco
    minutos de TvT vazariam alerta — bem no auge do evento.
    """

    @pytest.fixture
    def agenda(self):
        from pathlib import Path

        raiz = Path(__file__).resolve().parent.parent
        return ler_agenda(raiz / "config.toml")

    def test_dentro_do_tvt_ha_silencio(self, agenda):
        from l2scanner.agenda import silencio_ativo

        janela = silencio_ativo(em(15, 5), agenda)
        assert janela is not None
        assert janela.evento == "TvT"
        assert janela.fim == em(15, 15)

    def test_depois_do_tvt_nao_ha(self, agenda):
        from l2scanner.agenda import silencio_ativo

        assert silencio_ativo(em(15, 15), agenda) is None
        assert silencio_ativo(em(16, 30), agenda) is None

    def test_a_uniao_termina_as_2205_e_nao_as_2200(self, agenda):
        """O caso que motivou a regra."""
        from l2scanner.agenda import silencio_ativo

        janela = silencio_ativo(em(21, 55), agenda)
        assert janela is not None
        assert janela.fim == em(22, 5), "a uniao encurtou para o fim do Prime"
        assert janela.inicio == em(20, 0), "a uniao perdeu o inicio do Prime"
        assert janela.evento == "TvT", "o nome tem que ser de quem termina por ultimo"

    def test_entre_2200_e_2205_ainda_ha_silencio(self, agenda):
        """O Prime ja acabou, o TvT nao."""
        from l2scanner.agenda import silencio_ativo

        janela = silencio_ativo(em(22, 2), agenda)
        assert janela is not None and janela.fim == em(22, 5)

    def test_as_2205_o_silencio_acabou(self, agenda):
        from l2scanner.agenda import silencio_ativo

        assert silencio_ativo(em(22, 5), agenda) is None

    def test_no_sabado_nao_ha_prime_e_a_janela_e_so_do_tvt(self, agenda):
        from datetime import timedelta

        from l2scanner.agenda import silencio_ativo

        sabado = SEGUNDA + timedelta(days=5)
        janela = silencio_ativo(em(21, 55, sabado), agenda)
        assert janela is not None
        assert janela.inicio == em(21, 50, sabado)
        assert janela.evento == "TvT"

    def test_evento_sem_silenciar_minutos_nao_silencia(self):
        from l2scanner.agenda import silencio_ativo

        assert silencio_ativo(em(15, 5), [evento(silenciar_minutos=0)]) is None

    def test_janela_atravessa_a_meia_noite(self):
        from datetime import timedelta

        from l2scanner.agenda import silencio_ativo

        tarde = evento(horarios=((23, 30),), silenciar_minutos=120)
        terca = SEGUNDA + timedelta(days=1)
        janela = silencio_ativo(em(0, 30, terca), [tarde])
        assert janela is not None
        assert janela.inicio == em(23, 30), "a janela de ONTEM foi perdida"

    def test_uma_segunda_inteira_minuto_a_minuto(self, agenda):
        """Os minutos silenciados sao exatamente os esperados."""
        from datetime import timedelta

        from l2scanner.agenda import silencio_ativo

        silenciados = []
        instante = SEGUNDA
        for _ in range(24 * 60):
            if silencio_ativo(instante, agenda):
                silenciados.append(instante.strftime("%H:%M"))
            instante += timedelta(minutes=1)

        # (hora, minuto, duracao). O Prime das 20h dura 125 min e nao 120
        # porque a UNIAO com o TvT das 21:50 estende o fim ate 22:05.
        esperados = []
        for hora, minuto, duracao in (
            (15, 0, 15),
            (17, 0, 15),
            (20, 0, 125),
            (23, 0, 15),
        ):
            base = SEGUNDA.replace(hour=hora, minute=minuto)
            esperados += [
                (base + timedelta(minutes=i)).strftime("%H:%M")
                for i in range(duracao)
            ]
        # 20:00 + 125 min = ate 22:05, ja contando a uniao com o TvT das 21:50
        assert silenciados == esperados

    def test_o_texto_de_encerramento_nao_promete_enviar_convite(self):
        from l2scanner.agenda import JanelaDeSilencio, texto_de_encerramento

        texto = texto_de_encerramento(
            JanelaDeSilencio("TvT", em(21, 50), em(22, 5))
        )
        assert "TvT" in texto
        assert "reenviados" in texto
        # O scanner NUNCA envia input ao jogo. A frase avisa, nao age.
        assert "vou convidar" not in texto.lower()
        assert "enviando convite" not in texto.lower()
