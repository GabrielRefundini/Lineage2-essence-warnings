"""A agenda: o relogio como fonte de eventos.

Todos estes testes rodam em milissegundos porque a agenda nao tem relogio
proprio — o tempo entra por parametro, igual ao rastreador. Sem essa
disciplina, testar "o TvT das 21h50 de uma quinta" exigiria esperar ate quinta
as 21h50, e a agenda nunca teria cobertura de verdade.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from l2scanner import agenda, respawn
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


# Quanto cada evento cala, NOS DADOS DO TESTE. Ver `agenda_de_silencio()`.
SILENCIO_DO_TVT = 15
SILENCIO_DO_PRIME = 120


def agenda_de_silencio() -> list[EventoAgendado]:
    """A agenda que as REGRAS de silencio usam, montada de dados PROPRIOS.

    NAO le o `config.toml` do repositorio, e isso e o ponto. Aquele arquivo e
    PREFERENCIA do usuario e ele MUDA: em 2026-08-31 o usuario trocou o
    `silenciar_minutos` do TvT de 15 para 9 e SETE testes ficaram vermelhos sem
    uma linha de codigo de producao ter mudado. Um teste que trava o dado do
    usuario transforma cada ajuste de preferencia dele num deploy — o oposto
    exato do motivo de o valor morar num arquivo de configuracao.

    E o mesmo defeito que `8b87eb3` consertou na janela de respawn do Tiat,
    quando o servidor mudou a regra de 6+2 para 8+2:

        "ele provava a regra do servidor em vez de provar que ela e LIDA do
        arquivo"

    OS 15 E OS 120 NAO SAO COPIA DO `config.toml`. Sao os dois numeros que
    FAZEM a borda das 22:05 existir, que e a regra que estes testes afirmam:
    o Prime das 20:00 + 120 min termina 22:00, o TvT das 21:50 + 15 min termina
    22:05, e a UNIAO das duas janelas tem de ir ate 22:05. Sao dados do TESTE,
    escolhidos pela regra afirmada — trocar o arquivo do usuario nao os move,
    e mover estes numeros TEM de quebrar os testes da borda.

    Devolve uma lista NOVA a cada chamada, para uma fixtura nunca poder sujar
    a agenda de outra.
    """
    return [
        EventoAgendado(
            nome="TvT",
            horarios=((15, 0), (17, 0), (19, 30), (21, 50), (23, 0)),
            dias=TODOS_OS_DIAS,
            avisar_minutos_antes=10,
            silenciar_minutos=SILENCIO_DO_TVT,
        ),
        EventoAgendado(
            nome="Prime",
            horarios=((20, 0),),
            dias=frozenset({0, 1, 2, 3}),
            avisar_minutos_antes=10,
            silenciar_minutos=SILENCIO_DO_PRIME,
        ),
        EventoAgendado(
            nome="Solo Boss",
            horarios=(
                (0, 0),
                (2, 0),
                (4, 0),
                (6, 0),
                (8, 0),
                (10, 0),
                (12, 0),
                (14, 0),
                (16, 0),
                (18, 0),
                (20, 0),
                (22, 0),
            ),
            dias=TODOS_OS_DIAS,
            avisar_minutos_antes=10,
            avisar_no_horario=False,
            chamar_minutos_antes=110,
            silenciar_minutos=0,
        ),
    ]


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


class TestChamada:
    """O terceiro tipo de aviso: a pergunta "quem vai?", bem antes do evento.

    Ela NAO substitui o aviso de 10 minutos — serve a outra acao. O de
    antecedencia manda parar o farm e se deslocar; a chamada pede uma DECISAO,
    e por isso tem que vencer enquanto a decisao ainda cabe.

    Com o Solo Boss de duas em duas horas, `chamar_minutos_antes = 110` e dez
    minutos DEPOIS do boss anterior: o unico instante do ciclo em que a party
    ainda esta reunida e ainda esta olhando o WhatsApp. Por isso os testes
    daqui usam 110 e um alvo as 20:00 — sao os numeros de campo, nao numeros
    escolhidos para a aritmetica ficar redonda.
    """

    def chamavel(self, **kwargs) -> EventoAgendado:
        padroes = dict(horarios=((20, 0),), chamar_minutos_antes=110)
        padroes.update(kwargs)
        return evento(**padroes)

    def test_o_campo_nasce_desligado(self):
        """0 == desligado, o mesmo idioma de `silenciar_minutos`.

        E o que mantem TvT e Prime intocados sem ninguem precisar lembrar de
        excluir os dois: o opt-in e por INCLUSAO.
        """
        assert evento().chamar_minutos_antes == 0

    def test_a_chamada_vence_no_minuto_configurado(self):
        devidos = avisos_devidos(em(18, 10), [self.chamavel()], set())
        assert [a.tipo for a in devidos] == [TipoDeAviso.CHAMADA]
        assert devidos[0].alvo == em(20, 0)
        assert devidos[0].devido_em == em(18, 10)

    def test_um_minuto_antes_ainda_nao_saiu(self):
        assert avisos_devidos(em(18, 9), [self.chamavel()], set()) == []

    def test_fora_da_tolerancia_a_chamada_nao_ressuscita(self):
        """18:16 esta 6 minutos depois do vencimento; a tolerancia e 5.

        Uma chamada atrasada e pior que nenhuma: pergunta "quem vai" de um boss
        para o qual ja nao da mais tempo de se organizar.
        """
        assert avisos_devidos(em(18, 16), [self.chamavel()], set()) == []

    def test_o_mesmo_evento_continua_avisando_dez_minutos_antes(self):
        """A chamada ACRESCENTA um aviso; nao troca o que ja existia."""
        devidos = avisos_devidos(em(19, 50), [self.chamavel()], set())
        assert [a.tipo for a in devidos] == [TipoDeAviso.ANTES]

    def test_sem_o_campo_o_dia_inteiro_nao_produz_chamada_nenhuma(self):
        from datetime import timedelta

        enviados: set[str] = set()
        tipos = set()
        instante = SEGUNDA
        for _ in range(24 * 60):
            for aviso in avisos_devidos(instante, [evento()], enviados):
                enviados.add(aviso.chave)
                tipos.add(aviso.tipo)
            instante += timedelta(minutes=1)
        # A igualdade (e nao um `not in`) tambem prova que a varredura nao
        # ficou vazia: uma prova vazia passaria sem provar nada.
        assert tipos == {TipoDeAviso.ANTES, TipoDeAviso.AGORA}

    def test_a_chamada_sai_sozinha_quando_a_antecedencia_esta_desligada(self):
        """As guardas de opt-in nao interferem uma na outra."""
        from datetime import timedelta

        so_chamada = self.chamavel(avisar_minutos_antes=0, avisar_no_horario=False)
        enviados: set[str] = set()
        tipos = []
        instante = SEGUNDA
        for _ in range(24 * 60):
            for aviso in avisos_devidos(instante, [so_chamada], enviados):
                enviados.add(aviso.chave)
                tipos.append(aviso.tipo)
            instante += timedelta(minutes=1)
        assert tipos == [TipoDeAviso.CHAMADA]

    def test_ja_enviada_nao_repete(self):
        """A chave `_chamada` suprime igual as outras duas."""
        primeiro = avisos_devidos(em(18, 10), [self.chamavel()], set())
        assert len(primeiro) == 1
        de_novo = avisos_devidos(em(18, 10), [self.chamavel()], {primeiro[0].chave})
        assert de_novo == []

    def test_o_mecanismo_e_generico_e_nao_conhece_nome_de_evento_nenhum(self):
        """D-03 afirmado por COMPORTAMENTO, nao por grep no arquivo.

        Um grep contra `agenda.py` nasceria falhando: o arquivo cita "Solo
        Boss" num comentario de volume desde a Fase 6. O que importa nao e a
        palavra estar ausente do texto — e um evento com nome inventado receber
        exatamente o mesmo tratamento.
        """
        raid = self.chamavel(
            nome="Raid Qualquer", horarios=((12, 0),), chamar_minutos_antes=30
        )
        devidos = avisos_devidos(em(11, 30), [raid], set())
        assert [a.tipo for a in devidos] == [TipoDeAviso.CHAMADA]
        assert "Raid Qualquer" in texto_do_aviso(devidos[0])

    def test_empate_de_vencimento_tem_ordem_deterministica(self):
        """O desempate do `sort` e `tipo.value` alfabetico.

        `"agora" < "antes" < "chamada"` — e por isso que trocar o VALOR do
        membro do enum mudaria a ordem de saida, alem de invalidar marcador ja
        em disco. O valor e escolhido uma vez e nao muda.
        """
        alfa = self.chamavel(
            nome="Alfa", avisar_minutos_antes=0, avisar_no_horario=False
        )  # chamada devida as 18:10
        beta = evento(nome="Beta", horarios=((18, 10),), avisar_minutos_antes=0)
        devidos = avisos_devidos(em(18, 10), [alfa, beta], set())
        assert [a.tipo for a in devidos] == [TipoDeAviso.AGORA, TipoDeAviso.CHAMADA]


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


    def test_a_chave_da_chamada_e_inedita_e_nao_invalida_marcador_nenhum(self):
        """A razao inteira de D-01 ser um TIPO novo e nao uma lista.

        `chave` ja carrega `tipo.value`, entao o marcador da chamada nasce
        distinto sem uma linha de codigo — e nenhum `_antes` ou `_agora` ja
        gravado em `.agenda/` muda de significado.
        """
        alvo = em(20, 0)
        chamada = Aviso("Solo Boss", TipoDeAviso.CHAMADA, alvo, em(18, 10))
        assert chamada.chave == "2026-08-24_solo-boss-2000_chamada"

        antes = Aviso("Solo Boss", TipoDeAviso.ANTES, alvo, em(19, 50)).chave
        agora = Aviso("Solo Boss", TipoDeAviso.AGORA, alvo, alvo).chave
        assert len({chamada.chave, antes, agora}) == 3
        assert antes == "2026-08-24_solo-boss-2000_antes"
        assert agora == "2026-08-24_solo-boss-2000_agora"


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


    def test_a_chamada_pergunta_quem_vai_e_manda_responder_no_privado(self):
        """O privado nao foi escolha de desenho: e imposicao.

        A ponte Baileys desta conta vem com ingestao de grupo desligada
        (medido 2026-08-24: os 11 grupos nao entregam entrada, so as conversas
        1-a-1). Uma chamada que nao diz onde responder colhe resposta no grupo,
        que o bot nunca le.
        """
        aviso = Aviso("Solo Boss", TipoDeAviso.CHAMADA, em(20, 0), em(18, 10))
        texto = texto_do_aviso(aviso)
        assert "Solo Boss" in texto
        assert "20:00" in texto
        # O vocabulario OFICIAL, e o texto mais lido do recurso inteiro: ele
        # sai duas vezes por ocorrencia de boss, para o grupo todo. As
        # negativas nao sao redundancia — o ponto E o nome ingles continuam os
        # DOIS aceitos pelo parser, entao so a ausencia deles AQUI prova que a
        # chamada nao ensina mais nenhuma das duas formas demovidas a quem
        # nunca usou o bot.
        assert "/entrar" in texto
        assert "/sair" in texto
        assert "/join" not in texto
        assert "/leave" not in texto
        assert ".entrar" not in texto
        assert ".sair" not in texto
        assert "privado" in texto.lower()

    def test_a_chamada_nao_repete_nenhum_dos_dois_textos_de_hoje(self):
        """Tres acoes diferentes, tres textos diferentes.

        Repetir a frase treinaria a party a ignorar as tres.
        """
        alvo = em(20, 0)
        chamada = texto_do_aviso(
            Aviso("Solo Boss", TipoDeAviso.CHAMADA, alvo, em(18, 10))
        )
        antes = texto_do_aviso(Aviso("Solo Boss", TipoDeAviso.ANTES, alvo, em(19, 50)))
        agora = texto_do_aviso(Aviso("Solo Boss", TipoDeAviso.AGORA, alvo, alvo))
        assert len({chamada, antes, agora}) == 3

    def test_a_chamada_nunca_carrega_a_linha_de_loot(self):
        """`loot` so entra na ANTECEDENCIA — a chamada e sobre ir, nao sobre pegar."""
        aviso = Aviso("Solo Boss", TipoDeAviso.CHAMADA, em(20, 0), em(18, 10))
        assert "Loot" not in texto_do_aviso(aviso, loot="J4guar")

    def test_os_textos_de_ANTES_e_AGORA_sao_byte_a_byte_os_de_hoje(self):
        """Regressao dura: o tipo novo nao pode ter encostado nos dois antigos."""
        alvo = em(20, 0)
        antes = Aviso("Solo Boss", TipoDeAviso.ANTES, alvo, em(19, 50))
        agora = Aviso("Solo Boss", TipoDeAviso.AGORA, alvo, alvo)
        assert texto_do_aviso(antes) == (
            "Solo Boss comeca em 10 minutos, as 20:00. "
            "Hora de voltar para a cidade e se preparar."
        )
        assert texto_do_aviso(antes, loot="J4guar") == (
            "Solo Boss comeca em 10 minutos, as 20:00. "
            "Hora de voltar para a cidade e se preparar. Loot: J4guar."
        )
        assert texto_do_aviso(agora) == "Solo Boss comecou agora, as 20:00."


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


class TestChamarMinutosAntesNoToml:
    """O campo que liga a chamada, lido e validado no ARRANQUE.

    O usuario nao edita codigo: ele edita uma linha do config.toml. Entao o
    numero errado tem que derrubar o scanner enquanto ele esta olhando para o
    console — nunca as 2h da manha, calado, com a party achando que vai ser
    chamada.
    """

    def escrever(self, tmp_path, linha=""):
        caminho = tmp_path / "config.toml"
        caminho.write_text(
            '[[evento]]\nnome = "Solo Boss"\nhorarios = ["20:00"]\n' + linha,
            encoding="utf-8",
        )
        return caminho

    def test_o_numero_do_toml_chega_no_evento(self, tmp_path):
        caminho = self.escrever(tmp_path, "chamar_minutos_antes = 110\n")
        assert ler_agenda(caminho)[0].chamar_minutos_antes == 110

    def test_campo_ausente_vira_zero(self, tmp_path):
        """Ausente e o estado de TvT e Prime — e nao pode ser erro."""
        assert ler_agenda(self.escrever(tmp_path))[0].chamar_minutos_antes == 0

    @pytest.mark.parametrize(
        "valor",
        ["-1", '"110"', "true", "1.5"],
        ids=["negativo", "texto", "booleano", "fracionario"],
    )
    def test_valor_sem_sentido_derruba_o_arranque_citando_o_evento(
        self, tmp_path, valor
    ):
        """`true` esta nesta lista de proposito.

        `isinstance(True, int)` e verdadeiro em Python, entao uma validacao
        copiada sem pensar aceitaria `chamar_minutos_antes = true` e trataria
        como "chamar 1 minuto antes" — uma chamada inutil, entregue todo dia,
        sem nenhuma mensagem de erro. A validacao de `avisar_minutos_antes` tem
        exatamente esse buraco hoje; esta nao pode herda-lo.
        """
        caminho = self.escrever(tmp_path, f"chamar_minutos_antes = {valor}\n")
        with pytest.raises(AgendaInvalida) as erro:
            ler_agenda(caminho)
        assert "chamar_minutos_antes" in str(erro.value)
        assert "Solo Boss" in str(erro.value), "a mensagem tem que citar o NOME"

    def test_zero_explicito_e_valido_e_significa_desligado(self, tmp_path):
        """Escrever `= 0` e a forma de desligar sem apagar a linha."""
        caminho = self.escrever(tmp_path, "chamar_minutos_antes = 0\n")
        assert ler_agenda(caminho)[0].chamar_minutos_antes == 0


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
        assert tvt.horarios == ((15, 0), (17, 0), (19, 30), (21, 50), (23, 0))
        assert tvt.dias == TODOS_OS_DIAS

    def test_prime_as_20h_de_segunda_a_quinta(self, agenda):
        prime = next(e for e in agenda if e.nome == "Prime")
        assert prime.horarios == ((20, 0),)
        assert prime.dias == frozenset({0, 1, 2, 3})

    def test_as_duracoes_de_silencio_do_repositorio_sao_LIDAS(self, agenda):
        """O ESQUEMA, nunca o valor: a duracao do silencio e PREFERENCIA do usuario.

        Lidas e ignoradas nesta fase. Moram no arquivo desde ja para o usuario
        nao ter que editar a mao um config que ja editou quando a Fase 7 chegar.

        E POR ISSO ESTE TESTE NAO AFIRMA O NUMERO. A duracao MUDA porque ela e
        escolha dele: em 2026-08-31 trocou o TvT de 15 para 9, e este teste — que
        cravava `== 15` — ficou vermelho junto com outros seis, sem uma linha de
        codigo de producao ter mudado. Cravar o numero aqui transforma um ajuste
        de preferencia num deploy, que e o oposto exato do motivo de o valor
        morar num arquivo de configuracao.

        Mesmo defeito que `8b87eb3` consertou na janela de respawn do Tiat:

            "ele provava a regra do servidor em vez de provar que ela e LIDA do
            arquivo"

        Os `horarios` do TvT continuam cravados nos testes acima, e isso e
        DELIBERADO — o cabecalho do proprio `config.toml` diz por que: horario
        errado de TvT deixa a party esperando um evento que nao vai acontecer.
        A distincao e entre dado que o usuario ESCOLHE e dado que o jogo IMPOE.
        """
        por_nome = {e.nome: e for e in agenda}
        for nome in ("TvT", "Prime", "Solo Boss"):
            duracao = por_nome[nome].silenciar_minutos
            assert isinstance(duracao, int), f"{nome}: silenciar_minutos sumiu do esquema"
            assert duracao >= 0, f"{nome}: silenciar_minutos negativo"

    def test_so_o_solo_boss_tem_chamada_no_arquivo_do_repositorio(self, agenda):
        """D-02: o opt-in e por evento, e hoje so um evento pediu.

        TvT e Prime nao mudam de comportamento em nada nesta fase. Se algum dia
        alguem quiser chamada neles, e uma linha no config.toml — e uma decisao
        de volume de mensagem, que este teste obriga a tomar de proposito.
        """
        por_nome = {e.nome: e for e in agenda}
        assert por_nome["Solo Boss"].chamar_minutos_antes == 110
        assert por_nome["TvT"].chamar_minutos_antes == 0
        assert por_nome["Prime"].chamar_minutos_antes == 0

    def test_o_cabecalho_do_arquivo_documenta_o_campo(self):
        """Um campo que existe e nao esta na lista de campos e uma mentira por
        omissao: quem le o arquivo conclui que a chamada nao da para desligar.
        """
        from pathlib import Path

        raiz = Path(__file__).resolve().parent.parent
        texto = (raiz / "config.toml").read_text(encoding="utf-8")
        # Corta no PRIMEIRO bloco de verdade — que comeca em coluna zero. O
        # proprio cabecalho escreve '[[evento]]' em prosa, entao um split
        # sem a quebra de linha cortaria no meio da lista de campos.
        cabecalho = texto.split(chr(10) + '[[evento]]')[0]
        assert "chamar_minutos_antes" in cabecalho

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
            ("TvT", TipoDeAviso.ANTES, "19:20"),
            ("TvT", TipoDeAviso.AGORA, "19:30"),
            ("Prime", TipoDeAviso.ANTES, "19:50"),
            ("Prime", TipoDeAviso.AGORA, "20:00"),
            ("TvT", TipoDeAviso.ANTES, "21:40"),
            ("TvT", TipoDeAviso.AGORA, "21:50"),
            ("TvT", TipoDeAviso.ANTES, "22:50"),
            ("TvT", TipoDeAviso.AGORA, "23:00"),
        ]

    def test_solo_boss_chama_e_avisa_mas_nunca_fala_no_horario(self, agenda):
        """12 ocorrencias, DOIS avisos cada — e nenhum deles no horario.

        Este teste ja travou em 12. Subiu para 24 por DECISAO (D-01, a chamada
        de 1h50), nao por acidente: o que ele protege nunca foi o total, foi o
        `avisar_no_horario = false`. Um aviso de AGORA aqui significaria as 12
        mensagens da meia-noite as 22h que o usuario desligou de proposito na
        Fase 6, e nenhuma chamada as compraria de volta.

        As duas contagens sao afirmadas SEPARADAS. Se um dia so uma delas
        mudar, o total continuaria batendo e o teste nao veria nada.
        """
        saidas = [
            s for s in self._varrer_um_dia(agenda, SEGUNDA) if s[0] == "Solo Boss"
        ]
        assert len(saidas) == 24, "Solo Boss: 12 chamadas + 12 antecedencias"

        assert not [s for s in saidas if s[1] is TipoDeAviso.AGORA], (
            "algum aviso saiu no horario; avisar_no_horario deveria estar false"
        )

        antes = [hora for _, tipo, hora in saidas if tipo is TipoDeAviso.ANTES]
        chamadas = [hora for _, tipo, hora in saidas if tipo is TipoDeAviso.CHAMADA]

        # 10 minutos antes de cada boss par -> sempre HH:50 em hora impar.
        assert antes == [f"{h:02d}:50" for h in list(range(1, 24, 2))]
        assert len(antes) == 12

        # 110 minutos antes de cada boss par -> HH:10 em hora PAR, porque 1h50
        # antes de um boss e dez minutos depois do boss anterior. E essa a
        # medida de campo inteira, visivel aqui na forma dos horarios.
        assert chamadas == [f"{h:02d}:10" for h in list(range(0, 24, 2))]
        assert len(chamadas) == 12

    def test_o_volume_diario_total_e_o_esperado(self, agenda):
        """36 mensagens por dia. Se subir, alguem mexeu no config sem pensar.

        Era 24. Subiu para 36 por DECISAO (D-01): a chamada de 1h50 do Solo
        Boss acrescenta 12 perguntas por dia, uma por ocorrencia, e esse custo
        foi aceito no CONTEXT desta fase junto com a razao do numero.

        A conta, evento por evento, numa segunda:

            TvT               10   5 horarios x (ANTES + AGORA)
            Prime              2   1 horario  x (ANTES + AGORA), so seg-qui
            Solo Boss ANTES   12   12 horarios, avisar_no_horario = false
            Solo Boss CHAMADA 12   12 horarios x chamar_minutos_antes = 110
            ----------------------------------------------------------------
            total             36

        O grupo do WhatsApp e de pessoas, nao um feed. Este teste existe para
        um evento novo nao dobrar o volume sem ninguem perceber — e o unico
        jeito de ele continuar servindo para isso e o numero ser ESCRITO a
        mao, a partir da conta acima, e nunca colhido da propria execucao. Um
        alarme calibrado pela saida que ele deveria vigiar so afirma que o
        codigo faz o que o codigo faz.
        """
        assert len(self._varrer_um_dia(agenda, SEGUNDA)) == 36

    def test_tvt_e_prime_ficaram_exatamente_como_estavam(self, agenda):
        """D-02: a chamada e opt-in, e nem TvT nem Prime pediram.

        A prova aqui e de COMPORTAMENTO, contada na varredura de um dia. Ler
        `chamar_minutos_antes == 0` no config (o que outro teste ja faz) prova
        que o arquivo esta certo; isto prova que o motor concorda com ele.

        Se algum dia alguem ligar chamada em TvT, este teste cai antes de as
        10 mensagens virarem 15 no celular de todo mundo.
        """
        saidas = self._varrer_um_dia(agenda, SEGUNDA)
        tvt = [s for s in saidas if s[0] == "TvT"]
        prime = [s for s in saidas if s[0] == "Prime"]

        assert len(tvt) == 10, "5 horarios de TvT x 2 avisos, como antes da Fase 10"
        assert len(prime) == 2, "1 horario de Prime x 2 avisos, como antes da Fase 10"
        assert not [
            s for s in tvt + prime if s[1] is TipoDeAviso.CHAMADA
        ], "TvT ou Prime ganhou chamada; o opt-in de D-02 vazou"

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
        assert nomes.count("TvT") == 10, "5 horarios de TvT x 2 avisos"

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

    # -- as chaves destes testes precisam ser DE HOJE ------------------------
    #
    # MEDIDO EM 2026-08-28: quatro testes desta classe passaram a falhar
    # sozinhos, sem ninguem mexer em codigo. A causa: eles cravavam a data
    # "2026-08-24" na chave, e `RegistroEmDisco.__init__` chama `podar()`, que
    # apaga marcador com mais de DIAS_DE_MARCADOR (3) dias. No dia 28 o limite
    # passou a ser 25, o marcador de 24 virou lixo, e o segundo `marcar` da
    # mesma chave voltou True em vez de False.
    #
    # Nao era um bug no `RegistroEmDisco` -- a poda estava certa. Era o teste
    # apodrecendo com o calendario. Chave ancorada em `date.today()` nao
    # apodrece, e continua provando exatamente a mesma coisa.
    #
    # `test_poda_apaga_o_velho_e_preserva_o_de_hoje` NAO usa isto de proposito:
    # ele injeta `hoje=` porque o que ele testa E a poda.

    @staticmethod
    def _chave(sufixo: str) -> str:
        """Uma chave com a data de hoje, para sobreviver a poda do construtor."""
        from datetime import date as _date

        return f"{_date.today().isoformat()}_{sufixo}"

    def test_duas_instancias_no_mesmo_instante_so_uma_envia(self, tmp_path):
        """A garantia central da tarefa.

        `O_CREAT | O_EXCL` e atomico no Windows: entre duas instancias
        competindo pelo mesmo aviso, exatamente uma cria o arquivo.
        """
        from l2scanner.agenda import RegistroEmDisco

        a = RegistroEmDisco(tmp_path)
        b = RegistroEmDisco(tmp_path)
        chave = self._chave("tvt-1500_agora")

        assert [a.marcar(chave), b.marcar(chave)] == [True, False]

    def test_muitas_instancias_competindo_produzem_um_envio_so(self, tmp_path):
        from l2scanner.agenda import RegistroEmDisco

        chave = self._chave("tvt-2150_antes")
        registros = [RegistroEmDisco(tmp_path) for _ in range(8)]
        assert sum(1 for r in registros if r.marcar(chave)) == 1

    def test_competicao_de_verdade_com_threads(self, tmp_path):
        """Nao basta chamar em sequencia — o risco e a corrida.

        Um "le o JSON, checa, escreve o JSON" passaria no teste sequencial e
        falharia aqui, porque tem janela entre o read e o write.
        """
        import threading

        from l2scanner.agenda import RegistroEmDisco

        chave = self._chave("prime-2000_agora")
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

        chave = self._chave("tvt-1700_agora")
        assert RegistroEmDisco(tmp_path).marcar(chave) is True
        # processo morre, sobe de novo, do zero
        assert RegistroEmDisco(tmp_path).marcar(chave) is False

    def test_enviados_enxerga_o_que_a_outra_instancia_escreveu(self, tmp_path):
        from l2scanner.agenda import RegistroEmDisco

        a = RegistroEmDisco(tmp_path)
        b = RegistroEmDisco(tmp_path)
        chave = self._chave("tvt-1500_antes")
        a.marcar(chave)
        assert chave in b.enviados()

    def test_a_agenda_inteira_com_registro_duravel_nao_duplica(self, tmp_path):
        """Ponta a ponta: dois dias de agenda real, duas instancias, um envio."""
        from datetime import timedelta

        from l2scanner.agenda import RegistroEmDisco

        raiz = __import__("pathlib").Path(__file__).resolve().parent.parent
        agenda = ler_agenda(raiz / "config.toml")

        # A SEGUNDA global e uma data fixa; aqui ela precisa ser >= hoje,
        # senao a poda do construtor apaga os marcadores dentro do proprio
        # laco e o teste acusa duplicacao que nunca houve. Segunda-feira
        # continua sendo segunda: o Prime so existe de segunda a quinta.
        from datetime import date as _date

        _hoje = _date.today()
        _ate_segunda = (7 - _hoje.weekday()) % 7
        _segunda = datetime(_hoje.year, _hoje.month, _hoje.day) + timedelta(
            days=_ate_segunda
        )

        enviados_por = {"A": [], "B": []}
        instante = _segunda
        for _ in range(2 * 24 * 60):
            for etiqueta in ("A", "B"):
                registro = RegistroEmDisco(tmp_path)
                for aviso in avisos_devidos(instante, agenda, registro.enviados()):
                    if registro.marcar(aviso.chave):
                        enviados_por[etiqueta].append(aviso.chave)
            instante += timedelta(minutes=1)

        todos = enviados_por["A"] + enviados_por["B"]
        # A asserção que mais importa: mesmo com as duas instancias do usuario
        # varrendo o mesmo minuto, nenhum aviso sai duas vezes. Agora ela cobre
        # tambem a chave `_chamada`, que e nova em disco.
        assert len(todos) == len(set(todos)), "houve aviso duplicado"
        assert any(c.endswith("_chamada") for c in todos), (
            "nenhuma chamada na varredura; a prova de nao-duplicacao nao "
            "estaria cobrindo a chave nova"
        )
        # 36 avisos por dia (TvT 10 + Prime 2 + Solo Boss 12 ANTES + 12
        # CHAMADA), dois dias. Era 48; subiu para 72 por DECISAO — a chamada
        # de 1h50 do D-01 — e nao porque a varredura passou a devolver isso.
        assert len(todos) == 72

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

    def test_competicao_de_verdade_com_threads_no_entrar(self, tmp_path):
        """A MESMA corrida do `marcar`, agora sobre a lista de presenca.

        E o teste que prova PRES-10 e PRES-15 de uma vez: as duas instancias do
        usuario (Yazalaque e Faerlina) leem a MESMA conversa do Chatwoot e veem
        o MESMO `.join` no mesmo tick. Se as duas recebessem "criado", o grupo
        receberia duas confirmacoes de que o J4guar entrou — que e exatamente o
        volume de mensagem que fez o usuario desligar `avisar_no_horario` no
        Solo Boss.

        Dezesseis threads em vez de duas porque uma implementacao com janela
        entre o read e o write (um "le a pasta, checa, cria") passa no teste
        sequencial e so cai aqui.
        """
        import threading

        from l2scanner.agenda import RegistroEmDisco

        chave = self._chave("solo-boss-2000")
        criados = []
        trava = threading.Lock()
        largada = threading.Event()

        def tentar():
            registro = RegistroEmDisco(tmp_path)
            largada.wait()
            if registro.entrar(chave, "j4guar") == "criado":
                with trava:
                    criados.append(1)

        threads = [threading.Thread(target=tentar) for _ in range(16)]
        for t in threads:
            t.start()
        largada.set()
        for t in threads:
            t.join()

        assert len(criados) == 1, (
            f"{len(criados)} confirmacoes chegariam ao grupo pelo mesmo .join"
        )


class TestRegistroSimulando:
    """O `--dry-run` nao pode roubar a vez da instancia de verdade.

    2026-08-26, 19:30. Uma simulacao (`--so-agenda --dry-run`) rodava ao mesmo
    tempo que o scanner de verdade do usuario, e as duas disputaram o marcador
    `.agenda/2026-08-26_tvt-1930_agora`. A instancia REAL ganhou a corrida do
    `O_EXCL` por milissegundos e o aviso do TvT saiu.

    Foi sorte. Se a simulacao tivesse ganhado, `marcar` teria devolvido True
    para ela e False para a real, e o aviso das 19:30 NUNCA teria sido enviado
    — sem erro, sem log, sem nada. O modo que existe justamente para nao ter
    efeito colateral era o unico capaz de APAGAR um aviso.

    O conserto nao esta no `marcar`: o `O_CREAT|O_EXCL` continua sendo a
    garantia entre as duas instancias do usuario (Yazalaque e Faerlina), e a
    docstring dele exige que a decisao de despachar seja aquela chamada. O
    conserto e nao deixar um processo que NAO vai despachar entrar na disputa.
    """

    CHAVE = "2026-08-26_tvt-1930_agora"

    def _retrato(self, pasta):
        """O conteudo da pasta. Os marcadores sao arquivos vazios: o nome e tudo."""
        return sorted(caminho.name for caminho in pasta.iterdir())

    def test_o_simulando_nao_cria_nem_apaga_um_arquivo(self, tmp_path):
        """`--dry-run` promete nao ter efeito colateral. Aqui o disco prova.

        `cancelar` e `fechar` entram junto de proposito: os dois passam pelo
        `marcar` e herdam o comportamento sem saber que ele existe. E essa
        heranca que faz um quinto sitio futuro nascer certo.
        """
        from l2scanner.agenda import RegistroEmDisco

        real = RegistroEmDisco(tmp_path)
        real.marcar("2026-08-26_prime-2000_antes")
        antes = self._retrato(tmp_path)

        simulando = RegistroEmDisco(tmp_path, simulando=True)

        assert simulando.marcar(self.CHAVE) is True
        assert simulando.cancelar("2026-08-26_prime-2000") is True
        assert simulando.fechar("2026-08-26_solo-boss-2000") is True

        assert self._retrato(tmp_path) == antes, (
            "a simulacao gravou na .agenda/ compartilhada com o scanner real"
        )

    def test_o_simulando_nao_rouba_a_vez_do_real(self, tmp_path):
        """O incidente das 19:30, agora com a simulacao ganhando a corrida.

        Este e o teste que falha sem o conserto, e a linha que ele quebra e
        exatamente o aviso de TvT que a party nao teria recebido.
        """
        from l2scanner.agenda import RegistroEmDisco

        simulando = RegistroEmDisco(tmp_path, simulando=True)
        real = RegistroEmDisco(tmp_path)

        assert simulando.marcar(self.CHAVE) is True, (
            "a simulacao precisa se comportar como vencedora para o aviso "
            "aparecer no console, que e o ponto inteiro do --dry-run"
        )
        assert real.marcar(self.CHAVE) is True, (
            "a simulacao queimou o marcador: o aviso das 19:30 nao sairia"
        )

    def test_enviados_do_simulando_le_o_disco_de_verdade(self, tmp_path):
        """Uma simulacao cega mentiria sobre o que teria acontecido.

        Se `enviados()` tambem ficasse inerte, o `--dry-run` mostraria no
        console avisos que a instancia real ja tinha enviado ha horas. O modo
        serve para prever o que vai sair, nao para inventar.
        """
        from l2scanner.agenda import RegistroEmDisco

        real = RegistroEmDisco(tmp_path)
        real.marcar(self.CHAVE)

        simulando = RegistroEmDisco(tmp_path, simulando=True)

        assert self.CHAVE in simulando.enviados()

    def test_o_simulando_nao_poda(self, tmp_path):
        """`podar` APAGA arquivo, e roda no construtor.

        Sem isto, o simples ato de SUBIR uma simulacao ao lado do scanner de
        verdade apagaria marcador dele — o mesmo efeito colateral que esta
        correcao existe para eliminar, entrando pela porta dos fundos.
        """
        from datetime import date as _date

        from l2scanner.agenda import RegistroEmDisco

        antigo = "2000-01-01_tvt-1500_agora"
        RegistroEmDisco(tmp_path).marcar(antigo)

        simulando = RegistroEmDisco(tmp_path, simulando=True)
        assert (tmp_path / antigo).exists(), (
            "o construtor da simulacao podou a pasta compartilhada"
        )

        assert simulando.podar(hoje=_date(2026, 8, 26)) == 0
        assert (tmp_path / antigo).exists()

    def test_o_simulando_nao_cria_nem_a_pasta(self, tmp_path):
        """Nada gravado quer dizer nada, nem o `.agenda/` que faltava.

        Quem roda a simulacao numa maquina que nunca subiu o scanner nao deve
        deixar rastro nenhum — e nada em modo simulacao precisa da pasta:
        `enviados()` ja devolve vazio quando ela nao existe.
        """
        from l2scanner.agenda import RegistroEmDisco

        alvo = tmp_path / "agenda-que-nao-existe"

        simulando = RegistroEmDisco(alvo, simulando=True)

        assert not alvo.exists()
        assert simulando.enviados() == set()
        assert simulando.marcar(self.CHAVE) is True
        assert not alvo.exists()


class TestSimulacaoNoLacoDaAgenda:
    """A regra provada no laco que a usa, e nao so na classe.

    O incidente de 2026-08-26 19:30 aconteceu no `--so-agenda`, que era o modo
    de menor cobertura do projeto. Uma guarda com teste de unidade verde e uma
    guarda que o laco pode simplesmente nunca receber — foi assim que os tres
    bugs de producao do mesmo dia passaram por 420 testes verdes.
    """

    QUANDO = datetime(2026, 8, 26, 19, 30)
    MARCADOR = "2026-08-26_tvt-1930_agora"

    def _tick(self, monkeypatch, tmp_path, eventos, dry_run=True):
        """Uma unica volta do `laco_da_agenda`, com o relogio parado."""
        import argparse

        from l2scanner import __main__ as principal

        class RelogioParado:
            def __init__(self, quando):
                self._quando = quando

            def agora(self):
                return self._quando

        pasta = tmp_path / ".agenda"
        monkeypatch.setattr(principal, "PASTA_AGENDA", pasta)
        monkeypatch.setattr(principal, "PASTA_LOOT", tmp_path / ".loot")
        monkeypatch.setattr(principal, "ler_agenda", lambda *a, **k: list(eventos))
        # O relogio de verdade pergunta a hora ao Chatwoot. Sem isto o teste
        # dependeria do .env do usuario e da rede.
        monkeypatch.setattr(
            principal, "montar_relogio", lambda *a, **k: RelogioParado(self.QUANDO)
        )
        if not dry_run:
            # Fora da simulacao os dois montadores leem o .env. Aqui o que
            # esta em julgamento e o disco, nao a entrega.
            monkeypatch.setattr(principal, "montar_despachante", lambda *a, **k: None)
            monkeypatch.setattr(
                principal, "montar_leitor_de_comandos", lambda *a, **k: None
            )

        def uma_volta_so(_segundos):
            # O laco so sai por KeyboardInterrupt, e ele ja trata e devolve 0.
            raise KeyboardInterrupt

        monkeypatch.setattr(principal.time, "sleep", uma_volta_so)

        args = argparse.Namespace(dry_run=dry_run, intervalo=0)
        return principal.laco_da_agenda(args), pasta

    def _tvt(self):
        return EventoAgendado(nome="TvT", horarios=((19, 30),))

    def test_um_tick_em_simulacao_avisa_no_console_e_nao_grava(
        self, monkeypatch, tmp_path, caplog
    ):
        """As duas metades do `--dry-run`: o aviso sai, o disco fica intacto."""
        import logging

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            codigo, pasta = self._tick(monkeypatch, tmp_path, [self._tvt()])

        assert codigo == 0
        assert "TvT" in caplog.text, "o aviso nao apareceu no console"
        assert not pasta.exists(), "a simulacao gravou na .agenda/ compartilhada"

    def test_depois_do_tick_simulado_a_instancia_real_ainda_avisa(
        self, monkeypatch, tmp_path
    ):
        """O incidente das 19:30 atravessado pelo laco inteiro.

        E a pergunta que importa: depois que a simulacao rodou, o scanner de
        verdade ainda consegue anunciar o TvT?
        """
        from l2scanner.agenda import RegistroEmDisco

        _, pasta = self._tick(monkeypatch, tmp_path, [self._tvt()])

        assert RegistroEmDisco(pasta).marcar(self.MARCADOR) is True, (
            "o --dry-run queimou o marcador: o aviso das 19:30 nao sairia"
        )

    def test_a_prova_nao_e_vazia_o_mesmo_tick_sem_simulacao_grava(
        self, monkeypatch, tmp_path
    ):
        """Guarda contra teste vazio.

        Se o tick nunca chegasse ao aviso, os dois testes acima passariam sem
        provar nada — a pasta ficaria limpa por nao ter acontecido nada.
        """
        _, pasta = self._tick(monkeypatch, tmp_path, [self._tvt()], dry_run=False)

        assert (pasta / self.MARCADOR).exists(), (
            "o tick nao alcancou o aviso; os testes de simulacao seriam vazios"
        )


class TestOndeMoraAGuardaDeSimulacao:
    """A guarda mora no REGISTRO. Um `if dry_run` perto de um `marcar` e o bug.

    Sao quatro `marcar` hoje. Espalhar a checagem resolveria os quatro e faria
    o quinto nascer errado — a mesma forma do defeito de poda que
    `_PREFIXOS_CONHECIDOS` consertou e da recusa derivada de `set(Comando)`.
    """

    def _fonte(self, arquivo):
        import pathlib

        raiz = pathlib.Path(__file__).resolve().parent.parent
        return (raiz / "l2scanner" / arquivo).read_text(encoding="utf-8")

    def test_a_sessao_nao_conhece_dry_run(self):
        """O laco principal recebe um registro que ja sabe; ele nao precisa saber.

        Grep e proposital aqui, ao contrario dos portoes de AST do projeto: a
        exigencia e que a PALAVRA nao apareca em `sessao.py` de forma alguma,
        nem em comentario. E o sinal mais barato de que a correcao foi feita no
        lugar certo.
        """
        assert "dry_run" not in self._fonte("sessao.py"), (
            "sessao.py voltou a conhecer o conceito de simulacao"
        )

    def test_os_dois_lacos_constroem_o_registro_com_simulando(self):
        """O elo que faz a guarda chegar ate os quatro sitios.

        Lido por AST e nao por grep: as docstrings desta correcao escrevem
        `simulando` varias vezes, e uma busca textual daria positivo na propria
        documentacao que a restricao existe para proteger.
        """
        import ast

        arvore = ast.parse(self._fonte("__main__.py"))
        for laco in ("laco_da_agenda", "laco_principal"):
            funcao = next(
                no
                for no in ast.walk(arvore)
                if isinstance(no, ast.FunctionDef) and no.name == laco
            )
            construcoes = [
                no
                for no in ast.walk(funcao)
                if isinstance(no, ast.Call)
                and getattr(no.func, "id", None) == "RegistroEmDisco"
            ]
            assert construcoes, f"{laco} nao constroi um RegistroEmDisco"
            for chamada in construcoes:
                nomes = {palavra.arg for palavra in chamada.keywords}
                assert "simulando" in nomes, (
                    f"{laco} monta o registro sem `simulando`: um --dry-run "
                    "voltaria a disputar marcador com o scanner de verdade"
                )

    def test_a_frase_do_console_fala_do_disco(self):
        """Ela prometia so "nada e enviado", e por isso era meia verdade.

        Quem lesse a frase antiga concluiria que rodar um `--dry-run` ao lado
        do scanner de verdade era seguro — e era exatamente o que quase apagou
        o aviso de TvT das 19:30.
        """
        import inspect

        from l2scanner import __main__ as principal

        fonte = inspect.getsource(principal.montar_despachante)
        assert ".agenda/" in fonte, "a frase de simulacao nao menciona o disco"


class TestListaDePresencaEmDisco:
    """O namespace `presenca_` no `.agenda/` — quem entrou, quem saiu.

    A lista mora aqui e nao numa pasta propria porque ela MORRE quando o boss
    passa: a poda de 3 dias, que seria fatal para a estatistica do `.loot/`, e
    exatamente o que a lista de presenca quer. E a atomicidade entre as duas
    instancias, que e o problema dificil, ja estava escrita nesta classe.
    """

    CHAVE = "2026-08-24_solo-boss-2000"

    def registro(self, pasta):
        from l2scanner.agenda import RegistroEmDisco

        return RegistroEmDisco(pasta)

    def test_o_primeiro_join_cria_e_o_segundo_ja_existia(self, tmp_path):
        """O tri-estado E a decisao de produto do D-08.

        `ja_existia` nao e detalhe de implementacao vazando: e a unica coisa
        que distingue "acabou de entrar" (anuncia no grupo) de "ja estava na
        lista" (responde so no privado). Um booleano aqui obrigaria o `.join`
        repetido a repetir no grupo, ou a calar nos dois lugares.
        """
        registro = self.registro(tmp_path)
        assert registro.entrar(self.CHAVE, "j4guar") == "criado"
        assert registro.entrar(self.CHAVE, "j4guar") == "ja_existia"

    def test_duas_instancias_no_mesmo_instante_so_uma_cria(self, tmp_path):
        registro_a = self.registro(tmp_path)
        registro_b = self.registro(tmp_path)
        assert [
            registro_a.entrar(self.CHAVE, "kaus"),
            registro_b.entrar(self.CHAVE, "kaus"),
        ] == ["criado", "ja_existia"]

    def test_pasta_inalcancavel_devolve_falhou_e_nunca_criado(self, tmp_path):
        """Disco falhando NAO pode virar "criado".

        Aqui a regra e a oposta a do `marcar`: anunciar no grupo uma entrada
        que nao foi gravada faria a lista fechar sem essa pessoa, e ela
        chegaria no boss confiando num registro que nao a guarda. Preferir a
        repeticao ao silencio — a regra dos avisos — seria errado.
        """
        pasta = tmp_path / "some"
        registro = self.registro(pasta)
        # A pasta some por baixo: disco removido, sincronizador apagando,
        # permissao mudando. O que importa e o os.open falhar com OSError.
        pasta.rmdir()

        assert registro.entrar(self.CHAVE, "korzis") == "falhou"

    def test_presentes_devolve_so_os_slugs_daquela_ocorrencia(self, tmp_path):
        registro = self.registro(tmp_path)
        registro.entrar(self.CHAVE, "j4guar")
        registro.entrar(self.CHAVE, "kaus")
        assert registro.presentes(self.CHAVE) == frozenset({"j4guar", "kaus"})

    def test_uma_ocorrencia_nao_vaza_para_a_outra(self, tmp_path):
        """O boss das 20:00 e o das 22:00 sao listas diferentes.

        Os dois nomes de arquivo compartilham quase todo o prefixo
        (`presenca_2026-08-24_solo-boss-`), entao um filtro descuidado juntaria
        as duas listas e o grupo veria, as 22:00, a lista das 20:00.
        """
        registro = self.registro(tmp_path)
        registro.entrar("2026-08-24_solo-boss-2000", "j4guar")
        registro.entrar("2026-08-24_solo-boss-2200", "kaus")

        assert registro.presentes("2026-08-24_solo-boss-2000") == frozenset({"j4guar"})
        assert registro.presentes("2026-08-24_solo-boss-2200") == frozenset({"kaus"})

    def test_presentes_ignora_nome_malformado_sem_levantar(self, tmp_path):
        """A pasta e compartilhada e duravel: lixo nao vira excecao no farm."""
        registro = self.registro(tmp_path)
        (tmp_path / "presenca_lixo").touch()
        (tmp_path / "presenca_").touch()
        registro.entrar(self.CHAVE, "j4guar")

        assert registro.presentes(self.CHAVE) == frozenset({"j4guar"})

    def test_presentes_de_ocorrencia_sem_ninguem_e_vazio(self, tmp_path):
        assert self.registro(tmp_path).presentes(self.CHAVE) == frozenset()

    def test_sair_diz_se_removeu_e_e_idempotente(self, tmp_path):
        registro = self.registro(tmp_path)
        registro.entrar(self.CHAVE, "j4guar")

        assert registro.sair(self.CHAVE, "j4guar") is True
        assert registro.sair(self.CHAVE, "j4guar") is False
        assert registro.presentes(self.CHAVE) == frozenset()

    def test_sair_de_quem_nunca_entrou_nao_levanta(self, tmp_path):
        assert self.registro(tmp_path).sair(self.CHAVE, "ninguem") is False

    def test_entrar_de_novo_depois_de_sair_volta_a_criar(self, tmp_path):
        """`.leave` seguido de `.join` e arrependimento, nao erro."""
        registro = self.registro(tmp_path)
        registro.entrar(self.CHAVE, "kaus")
        registro.sair(self.CHAVE, "kaus")
        assert registro.entrar(self.CHAVE, "kaus") == "criado"

    def test_fechar_e_do_primeiro_chamador_so(self, tmp_path):
        """O fechamento e um ANUNCIO, entao a regra e a do `marcar`.

        Com as duas instancias vivas, exatamente uma anuncia a lista fechada no
        grupo. A outra ve `False` e cala.
        """
        registro_a = self.registro(tmp_path)
        registro_b = self.registro(tmp_path)
        assert registro_a.fechar(self.CHAVE) is True
        assert registro_b.fechar(self.CHAVE) is False

    def test_fechar_uma_ocorrencia_nao_fecha_a_outra(self, tmp_path):
        registro = self.registro(tmp_path)
        assert registro.fechar("2026-08-24_solo-boss-2000") is True
        assert registro.fechar("2026-08-24_solo-boss-2200") is True

    def test_pasta_nao_gravavel_nao_reanuncia_a_lista_a_cada_tick(
        self, tmp_path, monkeypatch
    ):
        """WR-09: o "preferir o duplicado ao perdido" precisava de teto.

        Com a `.agenda/` legivel e NAO gravavel — permissao, disco cheio, pasta
        em rede — `marcar` devolve True em toda tentativa. Sem teto, o
        fechamento sai a cada tick durante os 5 minutos de tolerancia: a 1 Hz
        sao ~300 mensagens identicas no grupo por ocorrencia.
        """
        import os

        registro = self.registro(tmp_path)

        def disco_travado(*args, **kwargs):
            raise PermissionError("pasta somente leitura")

        monkeypatch.setattr(os, "open", disco_travado)

        assert registro.fechar(self.CHAVE) is True, (
            "o primeiro fechamento tem que sair mesmo com o disco travado — "
            "a party nao adivinha uma lista que ninguem anunciou"
        )
        for _ in range(300):
            assert registro.fechar(self.CHAVE) is False, (
                "o segundo tick reanunciou: e a enxurrada de mensagens do WR-09"
            )

    def test_o_teto_e_por_OCORRENCIA_e_nao_por_processo(self, tmp_path, monkeypatch):
        """Dois bosses nascendo juntos continuam produzindo dois anuncios."""
        import os

        registro = self.registro(tmp_path)
        monkeypatch.setattr(
            os, "open", lambda *a, **k: (_ for _ in ()).throw(PermissionError())
        )

        assert registro.fechar("2026-08-24_solo-boss-2000") is True
        assert registro.fechar("2026-08-24_tvt-2000") is True

    def test_o_teto_nao_enfraquece_a_garantia_entre_as_duas_instancias(
        self, tmp_path
    ):
        """Com o disco funcionando, quem decide continua sendo o O_CREAT|O_EXCL."""
        registro_a = self.registro(tmp_path)
        registro_b = self.registro(tmp_path)
        assert registro_a.fechar(self.CHAVE) is True
        assert registro_b.fechar(self.CHAVE) is False
        assert registro_a.fechar(self.CHAVE) is False

    def test_o_slug_com_separador_de_caminho_nao_escapa_da_pasta(self, tmp_path):
        """T-10-12: travessia de caminho pelo nick.

        Duas barreiras independentes ja protegem isto — `NICK_VALIDO` na
        leitura do `[[membro]]` e o `apelido()`, que reduz a `[a-z0-9-]`. Este
        teste prova a segunda: o que chega ao disco fica DENTRO da pasta.
        """
        from l2scanner.loot import apelido

        registro = self.registro(tmp_path)
        registro.entrar(self.CHAVE, apelido("..\\..\\evil"))

        criados = [c for c in tmp_path.iterdir() if c.name.startswith("presenca_")]
        assert len(criados) == 1
        assert criados[0].parent == tmp_path
        assert not (tmp_path.parent / "evil").exists()


class TestPodaAlcancaTodosOsPrefixos:
    """A poda de 3 dias tem que alcancar TODO namespace da pasta.

    Ate esta fase ela retirava UM prefixo (`cancelado_`) antes de ler a data;
    qualquer marcador de outro namespace caia no `except ValueError` e ficava
    em disco PARA SEMPRE. Isso contradiz frontalmente o D-11 ("a poda de 3 dias
    e CORRETA aqui: a lista morre quando o boss passa") — sem o conserto, a
    lista de presenca seria o unico registro do projeto a crescer sem limite
    sem ninguem ter decidido isso.

    Um teste POR PREFIXO, e nao um so com tres arquivos: um laco quebrado em UM
    dos prefixos tem que dizer QUAL.
    """

    # OS MODULOS VARRIDOS ATRAS DE `PREFIXO_*`, e ser uma TUPLA e o conserto.
    #
    # A versao anterior deste guarda varria so `vars(agenda)`, e isso era um
    # PONTO CEGO: um `PREFIXO_*` declarado em qualquer outro modulo passava por
    # ele sem levantar nada — e um prefixo que escapa do guarda nasce IMORTAL,
    # porque `podar` nao sabe retira-lo antes de ler a data e o arquivo cai no
    # `except ValueError` para sempre.
    #
    # Para uma ancora de respawn essa e a familia de defeito mais cara da fase:
    # uma ancora de duas semanas atras nao fica so ocupando disco, ela continua
    # PRODUZINDO janelas erradas com cara de certas, entregues no grupo
    # (T-02-03).
    #
    # A Fase 2 resolveu a metade barata declarando `PREFIXO_NASCIMENTO` dentro
    # de `agenda.py`, onde o guarda ja o alcancava de graca. Esta tupla fecha a
    # outra metade: o proximo modulo que declarar um prefixo entra aqui, e
    # enquanto nao entrar o autor pelo menos LE esta lista.
    MODULOS_COM_PREFIXO = (agenda, respawn)

    @staticmethod
    def _prefixos_declarados(*modulos):
        return {
            valor
            for modulo in modulos
            for nome, valor in vars(modulo).items()
            if nome.startswith("PREFIXO_") and isinstance(valor, str)
        }

    def test_a_lista_de_prefixos_conhecidos_nao_deixa_ninguem_de_fora(self):
        """Todo `PREFIXO_*` dos modulos varridos tem que estar CLASSIFICADO.

        SAO DOIS BALDES DESDE O `/desativarsoloboss`, e a exigencia nao
        afrouxou: `_PREFIXOS_CONHECIDOS` (tem data, a poda alcanca) ou
        `_PREFIXOS_SEM_DATA` (nao tem data, nao expira NUNCA, por decisao).
        Um prefixo novo continua quebrando este teste enquanto ninguem
        escolher um dos dois por escrito.

        O segundo balde nasceu de uma decisao explicita do usuario: o
        desligamento do Solo Boss nao pode expirar sozinho. Force-lo para
        dentro do primeiro balde, so para o teste passar, o faria religar o
        boss tres dias depois — sem ninguem mandar e sem nada dizer.
        """
        declarados = self._prefixos_declarados(*self.MODULOS_COM_PREFIXO)
        classificados = set(agenda._PREFIXOS_CONHECIDOS) | set(
            agenda._PREFIXOS_SEM_DATA
        )
        esquecidos = declarados - classificados
        assert not esquecidos, (
            f"prefixo(s) sem balde — nem podavel nem imortal-por-decisao, "
            f"logo imortal por acidente: {esquecidos}"
        )

    def test_o_guarda_acusa_um_prefixo_declarado_fora_da_agenda(self):
        """GUARDA CONTRA PROVA VAZIA: um portao que nao pode falhar nao e
        portao.

        Um namespace de mentira, com um `PREFIXO_*` que ninguem classificou,
        tem que ser ACUSADO. Sem este teste, a tupla acima poderia listar os
        modulos errados — ou um modulo sem prefixo nenhum — e o guarda ficaria
        verde para sempre, exatamente como ficava antes de a tupla existir.
        """

        class ModuloDeMentira:
            PREFIXO_INVENTADO = "inventado_"

        declarados = self._prefixos_declarados(ModuloDeMentira)
        classificados = set(agenda._PREFIXOS_CONHECIDOS) | set(
            agenda._PREFIXOS_SEM_DATA
        )

        assert declarados - classificados == {"inventado_"}

    def test_o_prefixo_da_ancora_esta_no_balde_dos_podaveis(self):
        """A ancora e um fato DATADO que deve morrer, e nao uma decisao.

        Afirmado nos dois sentidos: esta no balde certo E nao esta no outro.
        Se ela caisse em `_PREFIXOS_SEM_DATA`, uma ancora falsa — a de um
        jogador que digitou a frase do anuncio no chat (T-02-01) — mentiria
        para sempre em vez de morrer em tres dias.
        """
        assert agenda.PREFIXO_NASCIMENTO in agenda._PREFIXOS_CONHECIDOS
        assert agenda.PREFIXO_NASCIMENTO not in agenda._PREFIXOS_SEM_DATA

    def test_o_prefixo_do_anuncio_esta_no_balde_dos_podaveis(self):
        """O gemeo do teste acima, e o que ele impede e pior que uma mentira.

        Se `PREFIXO_ANUNCIO` caisse em `_PREFIXOS_SEM_DATA`, um marcador de
        silencio criado uma vez calaria aquele boss PARA SEMPRE. O sintoma
        seria um scanner que roda, loga, preve janela e nunca mais anuncia um
        nascimento — sem erro, sem log, sem nada (T-03-03). A ancora velha
        MENTE e alguem acaba percebendo a previsao errada; o anuncio velho
        EMUDECE, e ninguem percebe um alerta que nao chegou.
        """
        assert agenda.PREFIXO_ANUNCIO in agenda._PREFIXOS_CONHECIDOS
        assert agenda.PREFIXO_ANUNCIO not in agenda._PREFIXOS_SEM_DATA

    def test_os_dois_baldes_de_prefixo_nao_se_sobrepoem(self):
        """Um prefixo nos dois seria a poda contradizendo a decisao.

        Se `PREFIXO_EVENTO_CALADO` entrasse tambem em `_PREFIXOS_CONHECIDOS`,
        `podar` passaria a retira-lo antes de ler a data e o teste acima
        continuaria verde — a contradicao so apareceria no dia em que o boss
        religasse sozinho.
        """
        assert not (
            set(agenda._PREFIXOS_CONHECIDOS) & set(agenda._PREFIXOS_SEM_DATA)
        )

    @pytest.mark.parametrize(
        "prefixo,sufixo",
        [
            ("cancelado_", ""),
            ("presenca_", "_j4guar"),
            ("fechado_", ""),
            ("", "_agora"),
            # O SUFIXO DE ORIGEM E O FORMATO REAL DA ANCORA, e nao uma
            # aproximacao dele: `nascimento_<data>_<boss>-<HHMM>_<origem>`.
            # Sem `_chat` no nome, o teste exercitaria uma forma que o disco
            # nunca vai ter — e a poda quebraria justamente no caractere que
            # o teste omitiu.
            ("nascimento_", "_chat"),
            ("nascimento_", "_chat_e_alvo"),
            # A chave do AVISO de janela, que nao tem prefixo nenhum e poda
            # pela mesma linha de codigo que os avisos de agenda. E o que a
            # docstring de `AvisoDeJanela.chave` promete ao derivar a chave da
            # ANCORA em vez do alvo.
            ("", "_abre"),
            ("", "_limite"),
        ],
        ids=[
            "cancelado",
            "presenca",
            "fechado",
            "aviso-sem-prefixo",
            "ancora-de-nascimento",
            "ancora-com-origem-dupla",
            "janela-abre",
            "janela-limite",
        ],
    )
    def test_o_velho_morre_e_o_de_hoje_sobrevive(self, tmp_path, prefixo, sufixo):
        from datetime import date as _date

        from l2scanner.agenda import RegistroEmDisco

        registro = RegistroEmDisco(tmp_path)
        velho = f"{prefixo}2026-08-20_solo-boss-2000{sufixo}"
        novo = f"{prefixo}2026-08-24_solo-boss-2000{sufixo}"
        (tmp_path / velho).touch()
        (tmp_path / novo).touch()

        apagados = registro.podar(hoje=_date(2026, 8, 24))

        assert apagados == 1, f"a poda nao alcancou o prefixo {prefixo!r}"
        assert registro.enviados() == {novo}

    def test_a_poda_do_arranque_ja_limpa_presenca_velha(self, tmp_path):
        """`__init__` chama `podar()` — e ali que a limpeza acontece de fato.

        Sem esta prova o conserto seria teorico: ninguem chama `podar` a mao no
        laco do scanner.
        """
        from datetime import date as _date
        from datetime import timedelta as _timedelta

        from l2scanner.agenda import RegistroEmDisco

        antiga = _date.today() - _timedelta(days=10)
        (tmp_path / f"presenca_{antiga.isoformat()}_solo-boss-2000_kaus").touch()

        registro = RegistroEmDisco(tmp_path)

        assert registro.enviados() == set()

    def test_arquivo_sem_prefixo_conhecido_continua_intocado(self, tmp_path):
        from datetime import date as _date

        from l2scanner.agenda import RegistroEmDisco

        (tmp_path / "leiame.txt").write_text("nao me apague", encoding="utf-8")
        (tmp_path / "comando_998877").touch()
        registro = RegistroEmDisco(tmp_path)

        registro.podar(hoje=_date(2030, 1, 1))

        assert (tmp_path / "leiame.txt").exists()
        # Os marcadores `comando_<id>` do `chave_da_mensagem` tambem sobrevivem
        # — nao por decisao, mas porque nao ha data no nome deles. Esta linha
        # registra o fato observado; resolve-lo e outro desenho e outra fase.
        assert (tmp_path / "comando_998877").exists()

    def test_as_assinaturas_antigas_nao_mudaram(self, tmp_path):
        """Nenhum chamador de `marcar`/`cancelar`/`cancelados` foi tocado."""
        from l2scanner.agenda import RegistroEmDisco

        registro = RegistroEmDisco(tmp_path)
        assert registro.marcar("2026-08-24_tvt-1500_agora") is True
        assert registro.cancelar("2026-08-24_prime-2000") is True
        assert registro.cancelados() == {"2026-08-24_prime-2000"}
        assert "2026-08-24_tvt-1500_agora" in registro.enviados()


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

    Os dados sao PROPRIOS (`agenda_de_silencio()`) e nao do `config.toml`: a
    regra afirmada aqui e a UNIAO, e ela precisa de duas janelas que se
    sobrepoem de um jeito conhecido. Ler o arquivo do usuario punha a
    preferencia dele no caminho da regra — foi o que quebrou estes testes
    quando ele trocou o TvT de 15 para 9.
    """

    @pytest.fixture
    def agenda(self):
        return agenda_de_silencio()

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
            (19, 30, 15),
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


class TestOMarcadorDeNascimento:
    """A ANCORA: o par que a Fase 2 acrescentou ao registro, no molde do
    `cancelar`/`cancelados`.

    Os dois metodos nao conhecem boss nenhum — recebem e devolvem string opaca.
    A semantica de boss mora inteira em `respawn.py`, exatamente como a
    semantica de presenca mora em `presenca.py` e nao em
    `RegistroEmDisco.presentes`.
    """

    CHAVE = "2026-08-30_tiat-north-1430_chat"

    def test_registrar_poe_o_prefixo_e_a_chave_crua_fica_no_nome(self, tmp_path):
        from l2scanner.agenda import PREFIXO_NASCIMENTO, RegistroEmDisco

        registro = RegistroEmDisco(tmp_path)
        assert registro.registrar_nascimento(self.CHAVE) is True
        assert (tmp_path / (PREFIXO_NASCIMENTO + self.CHAVE)).exists()

    def test_o_marcador_e_VAZIO(self, tmp_path):
        """O arquivo vazio E a decisao de despacho inteira (D-18).

        A origem vai no NOME e nunca no CONTEUDO: um "cria e depois escreve"
        abriria uma janela em que a outra instancia le um arquivo ainda vazio e
        nao sabe qual sinal ancorou — e a criacao atomica com `O_CREAT|O_EXCL`
        deixaria de ser a decisao inteira.
        """
        from l2scanner.agenda import PREFIXO_NASCIMENTO, RegistroEmDisco

        registro = RegistroEmDisco(tmp_path)
        registro.registrar_nascimento(self.CHAVE)

        assert (tmp_path / (PREFIXO_NASCIMENTO + self.CHAVE)).stat().st_size == 0

    def test_nascimentos_devolve_sem_o_prefixo(self, tmp_path):
        from l2scanner.agenda import RegistroEmDisco

        registro = RegistroEmDisco(tmp_path)
        registro.registrar_nascimento(self.CHAVE)

        assert registro.nascimentos() == {self.CHAVE}

    def test_nascimentos_nao_confunde_os_outros_namespaces(self, tmp_path):
        """Namespaces diferentes na MESMA pasta.

        Sem o filtro por prefixo, um marcador de aviso de janela (que nao tem
        prefixo nenhum) entraria na lista de ancoras e seria parseado como
        nascimento.
        """
        from l2scanner.agenda import RegistroEmDisco

        registro = RegistroEmDisco(tmp_path)
        registro.registrar_nascimento(self.CHAVE)
        registro.marcar("2026-08-30_tiat-north-1430_abre")
        registro.cancelar("2026-08-30_solo-boss-2000")

        assert registro.nascimentos() == {self.CHAVE}

    def test_a_segunda_instancia_perde_a_corrida(self, tmp_path):
        """JANE-06 herdado de `marcar`, sem uma linha de codigo nova."""
        from l2scanner.agenda import RegistroEmDisco

        yaza = RegistroEmDisco(tmp_path)
        faer = RegistroEmDisco(tmp_path)

        assert yaza.registrar_nascimento(self.CHAVE) is True
        assert faer.registrar_nascimento(self.CHAVE) is False

    def test_em_simulacao_nao_grava_ancora_na_pasta_compartilhada(self, tmp_path):
        """Herdado de `marcar`, e nao reimplementado.

        Uma simulacao que gravasse ancora faria o scanner REAL contar seis
        horas a partir de um nascimento que a simulacao inventou.
        """
        from l2scanner.agenda import RegistroEmDisco

        pasta = tmp_path / "agenda"
        registro = RegistroEmDisco(pasta, simulando=True)

        assert registro.registrar_nascimento(self.CHAVE) is True
        assert not pasta.exists()
