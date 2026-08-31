"""A lista de presenca: quem entra, quem sai, e o que o bot responde.

Estes testes provam as tres propriedades que fazem a chamada do Solo Boss ter
resposta em vez de eco:

1. **Duas redacoes, nunca uma.** O privado e o grupo recebem textos
   DIFERENTES, porque servem a leitores diferentes: quem digitou precisa saber
   que CHEGOU (sem esse eco, um `.join` recusado por autorizacao e um que
   funcionou sao indistinguiveis); o grupo precisa do NICK e do HORARIO. E
   `grupo is None` e o jeito estruturado de dizer "isto nao merece mensagem no
   grupo" — nunca uma string vazia, que o despachante enviaria assim mesmo.

2. **Nada e anunciado sem ter sido gravado.** O tri-estado do `entrar` nunca
   colapsa `"falhou"` em sucesso, e toda resposta que nao escreveu em disco sai
   com `grupo is None`. Uma confirmacao de entrada que o disco perdeu faria a
   lista fechar sem essa pessoa.

3. **O tempo entra por parametro.** Sem relogio proprio, o `.leave` as 20:01
   com o boss das 20:00 recem-fechado e testado em milissegundos em vez de as
   20:01 de um dia real.
"""

from __future__ import annotations

import ast
import logging
import unicodedata
from datetime import datetime
from pathlib import Path

import pytest

from l2scanner.agenda import (
    TODOS_OS_DIAS,
    EventoAgendado,
    RegistroEmDisco,
    chave_da_ocorrencia,
)
from l2scanner.presenca import (
    Fechamento,
    RespostaDePresenca,
    fechar_e_narrar,
    fechar_ocorrencias,
    nomes_dos_membros,
    ocorrencia_da_chamada,
    ocorrencia_do_join,
    ocorrencia_recem_fechada,
    responder_join,
    responder_leave,
    texto_de_fechamento,
)

RAIZ = Path(__file__).resolve().parent.parent

# Uma segunda-feira, para os testes que precisam de um dia conhecido.
SEGUNDA = datetime(2026, 8, 24)
assert SEGUNDA.weekday() == 0


def em(hora: int, minuto: int, dia: int = 24) -> datetime:
    return datetime(2026, 8, dia, hora, minuto)


def solo_boss(**kwargs) -> EventoAgendado:
    """O Solo Boss como o `config.toml` do usuario o descreve, encurtado.

    Dois horarios em vez de doze: o que os testes precisam e de um "proximo" e
    de um "o de depois", para provar que a lista das 20:00 nao vaza para a das
    22:00.
    """
    padroes = dict(
        nome="Solo Boss",
        horarios=((20, 0), (22, 0)),
        dias=TODOS_OS_DIAS,
        avisar_minutos_antes=10,
        avisar_no_horario=False,
        chamar_minutos_antes=110,
    )
    padroes.update(kwargs)
    return EventoAgendado(**padroes)


def sem_chamada() -> EventoAgendado:
    """Um evento que NAO pediu chamada — o estado de TvT e Prime."""
    return EventoAgendado(nome="TvT", horarios=((15, 0), (21, 50)))


@pytest.fixture
def registro(tmp_path):
    return RegistroEmDisco(tmp_path)


class TestQualOcorrenciaAChamadaPegou:
    """D-07: a resposta tem que dizer QUAL horario pegou.

    `.join` fora da janela e aceito de proposito — quem lembrou tres horas
    antes nao pode ser punido por lembrar cedo. Mas entao a resposta e a UNICA
    coisa que impede o mal-entendido de a pessoa achar que entrou no boss
    errado.
    """

    def test_pega_a_proxima_ocorrencia_com_chamada(self):
        assert ocorrencia_da_chamada(em(18, 15), [solo_boss()]) == (
            "Solo Boss",
            em(20, 0),
        )

    def test_tres_horas_antes_pega_a_mesma_ocorrencia(self):
        assert ocorrencia_da_chamada(em(9, 0), [solo_boss()]) == (
            "Solo Boss",
            em(20, 0),
        )

    def test_depois_do_alvo_ja_e_a_ocorrencia_seguinte(self):
        assert ocorrencia_da_chamada(em(20, 1), [solo_boss()]) == (
            "Solo Boss",
            em(22, 0),
        )

    def test_evento_sem_chamada_nao_e_escolhido(self):
        """TvT tem ocorrencia mais proxima e mesmo assim nao entra.

        O filtro e `chamar_minutos_antes > 0`, nao "o que vem primeiro".
        """
        achado = ocorrencia_da_chamada(em(14, 0), [sem_chamada(), solo_boss()])
        assert achado == ("Solo Boss", em(20, 0))

    def test_agenda_sem_nenhuma_chamada_devolve_nada(self):
        assert ocorrencia_da_chamada(em(14, 0), [sem_chamada()]) is None

    def test_agenda_vazia_devolve_nada(self):
        assert ocorrencia_da_chamada(em(14, 0), []) is None

    def test_o_mecanismo_e_generico_e_nao_conhece_nome_de_evento(self):
        """D-03: quem decide que evento tem chamada e o config.toml.

        Um nome inventado, que nunca apareceu no codigo nem vai aparecer, e
        escolhido normalmente so por declarar `chamar_minutos_antes`. Se algum
        dia alguem escrever "Solo Boss" dentro de `presenca.py`, este teste
        continua passando — e por isso ele vem acompanhado do teste de
        `eh_solo_boss` NAO ser importado, logo abaixo em TestDirecaoDeImportacao.
        """
        inventado = EventoAgendado(
            nome="Baium do Zodiaco",
            horarios=((3, 30),),
            chamar_minutos_antes=45,
        )
        assert ocorrencia_da_chamada(em(1, 0), [inventado]) == (
            "Baium do Zodiaco",
            em(3, 30),
        )


class TestOcorrenciaRecemFechada:
    """A janela em que o boss ja comecou — a base da recusa do D-14.

    Decide pelo TEMPO e nao pelo marcador `fechado_` de proposito. Amarrar a
    recusa ao marcador faria a resposta depender de o tick ter rodado: scanner
    fora do ar as 20:00, subindo as 20:03, e um `.leave` as 20:02 cairia na
    ocorrencia das 22:00 e responderia "voce nao estava na lista" — confuso e
    errado. A janela recusa certo nos dois estados.
    """

    def test_um_minuto_depois_do_boss_a_ocorrencia_esta_recem_fechada(self):
        assert ocorrencia_recem_fechada(em(20, 1), [solo_boss()]) == (
            "Solo Boss",
            em(20, 0),
        )

    def test_no_minuto_exato_do_boss_ja_conta(self):
        assert ocorrencia_recem_fechada(em(20, 0), [solo_boss()]) == (
            "Solo Boss",
            em(20, 0),
        )

    def test_antes_do_boss_nao_ha_nada_fechado(self):
        assert ocorrencia_recem_fechada(em(19, 59), [solo_boss()]) is None

    def test_passada_a_tolerancia_a_janela_fecha(self):
        """A mesma TOLERANCIA_MINUTOS dos avisos, e nao uma constante nova.

        E a mesma propriedade do laco (que roda a 1 Hz) respondendo a mesma
        pergunta: quanto tempo depois do alvo isto ainda e "agora".
        """
        assert ocorrencia_recem_fechada(em(20, 5), [solo_boss()]) is None

    def test_a_virada_da_meia_noite_e_varrida(self):
        """Um boss as 23:59 continua recem-fechado as 00:02 do dia seguinte.

        Dois minutos depois do alvo, mas do OUTRO LADO da meia-noite: uma
        varredura que olhasse so `agora.date()` acharia o boss das 23:59 de
        HOJE (que ainda nem aconteceu) e devolveria None. E o mesmo motivo pelo
        qual `silencio_ativo` varre ontem.
        """
        tardio = solo_boss(horarios=((23, 59),))
        assert ocorrencia_recem_fechada(em(0, 2, dia=25), [tardio]) == (
            "Solo Boss",
            em(23, 59, dia=24),
        )

    def test_doze_minutos_depois_do_alvo_ja_passou_da_tolerancia(self):
        """A varredura de ontem nao afrouxa a janela: ela so a alcanca.

        Este teste existe porque a primeira versao do teste da meia-noite usava
        23:50 contra 00:02 e falhou — corretamente, porque sao doze minutos.
        A borda ficou registrada em vez de apagada.
        """
        tardio = solo_boss(horarios=((23, 50),))
        assert ocorrencia_recem_fechada(em(0, 2, dia=25), [tardio]) is None

    def test_evento_sem_chamada_nunca_esta_recem_fechado(self):
        """TvT das 15:00 as 15:01 nao tem lista para fechar."""
        assert ocorrencia_recem_fechada(em(15, 1), [sem_chamada()]) is None


class TestJoin:
    CHAVE_2000 = "2026-08-24_solo-boss-2000"

    def test_o_join_poe_na_lista_e_confirma_nos_dois_lugares(self, registro):
        resposta = responder_join(registro, [solo_boss()], em(18, 15), "J4guar")

        assert "20:00" in resposta.privado
        assert resposta.grupo is not None
        assert "J4guar" in resposta.grupo
        assert "20:00" in resposta.grupo
        assert registro.presentes(self.CHAVE_2000) == frozenset({"j4guar"})

    def test_as_duas_redacoes_sao_DIFERENTES(self, registro):
        """D-09: o privado e o grupo nao podem receber a mesma frase.

        Hoje o `__main__.py` despacha o MESMO texto nos dois destinos. Se as
        duas redacoes fossem iguais, o par `RespostaDePresenca` nao teria razao
        de existir e alguem o colapsaria numa string na primeira limpeza.
        """
        resposta = responder_join(registro, [solo_boss()], em(18, 15), "J4guar")
        assert resposta.privado != resposta.grupo

    def test_join_tres_horas_antes_cita_o_horario_que_pegou(self, registro):
        """D-07: quem lembrou cedo nao e punido, mas precisa saber o que pegou."""
        resposta = responder_join(registro, [solo_boss()], em(9, 0), "Kaus")
        assert "20:00" in resposta.privado
        assert resposta.grupo is not None and "20:00" in resposta.grupo

    def test_join_repetido_responde_no_privado_e_CALA_no_grupo(self, registro):
        """D-08: o grupo e o recurso caro desta fase.

        Doze ocorrencias por dia ja foram a razao de o usuario desligar
        `avisar_no_horario` no Solo Boss. Um `.join` repetido que repetisse no
        grupo desfaria essa decisao pela porta dos fundos.
        """
        responder_join(registro, [solo_boss()], em(18, 15), "J4guar")
        segunda = responder_join(registro, [solo_boss()], em(18, 20), "J4guar")

        assert segunda.grupo is None
        assert "ja esta" in segunda.privado.lower()
        assert "20:00" in segunda.privado

    def test_maiuscula_e_minuscula_sao_a_mesma_pessoa(self, registro):
        """O slug e o mesmo idioma do `.loot-<nick>`: `.J4GUAR` == `.j4guar`."""
        responder_join(registro, [solo_boss()], em(18, 15), "J4guar")
        segunda = responder_join(registro, [solo_boss()], em(18, 20), "J4GUAR")
        assert segunda.grupo is None

    def test_o_nome_no_grupo_e_o_NICK_configurado_e_nao_o_slug(self, registro):
        """D-10: o nick vem do mapa `[[membro]]`, com a grafia do config.toml.

        Reler o slug do disco para montar o texto entregaria "j4guar" ao grupo
        — le como bot quebrado, e e o mesmo motivo pelo qual `loot.exibir`
        existe.
        """
        resposta = responder_join(registro, [solo_boss()], em(18, 15), "TioMad")
        assert "TioMad" in resposta.grupo
        assert "tiomad" not in resposta.grupo

    def test_duas_pessoas_entram_na_mesma_lista(self, registro):
        responder_join(registro, [solo_boss()], em(18, 15), "J4guar")
        responder_join(registro, [solo_boss()], em(18, 16), "Kaus")
        assert registro.presentes(self.CHAVE_2000) == frozenset({"j4guar", "kaus"})

    def test_disco_falhando_NAO_anuncia_no_grupo(self, tmp_path):
        """T-10-13: anunciar o que nao foi gravado e a pior falha desta fase.

        A pessoa veria a confirmacao no grupo, contaria com a vaga, e a lista
        fecharia sem ela.
        """
        pasta = tmp_path / "some"
        registro = RegistroEmDisco(pasta)
        pasta.rmdir()

        resposta = responder_join(registro, [solo_boss()], em(18, 15), "Korzis")

        assert resposta.grupo is None
        assert "de novo" in resposta.privado.lower()

    def test_sem_nick_aponta_o_config_toml(self, registro):
        """O dono que nao esta em `[[membro]]` chega sem nick (plano 10-01).

        Ele PODE mandar `.join` — o nivel de dono alcanca tudo — mas o bot nao
        tem que nick por na lista. A resposta diz onde consertar.
        """
        resposta = responder_join(registro, [solo_boss()], em(18, 15), None)

        assert resposta.grupo is None
        assert "config.toml" in resposta.privado

    def test_sem_evento_com_chamada_explica_e_nao_grava(self, registro, tmp_path):
        resposta = responder_join(registro, [sem_chamada()], em(18, 15), "J4guar")

        assert resposta.grupo is None
        assert "chamar_minutos_antes" in resposta.privado
        assert [c for c in tmp_path.iterdir() if c.name.startswith("presenca_")] == []

    def test_a_lista_das_2000_nao_vaza_para_a_das_2200(self, registro):
        """Duas ocorrencias do mesmo evento sao duas listas."""
        responder_join(registro, [solo_boss()], em(18, 15), "J4guar")
        responder_join(registro, [solo_boss()], em(20, 30), "Kaus")

        assert registro.presentes(self.CHAVE_2000) == frozenset({"j4guar"})
        assert registro.presentes("2026-08-24_solo-boss-2200") == frozenset({"kaus"})


class TestLeave:
    def test_o_leave_tira_da_lista_e_o_grupo_fica_sabendo(self, registro):
        responder_join(registro, [solo_boss()], em(18, 15), "J4guar")

        resposta = responder_leave(registro, [solo_boss()], em(18, 40), "J4guar")

        assert resposta.grupo is not None
        assert "J4guar" in resposta.grupo
        assert "20:00" in resposta.grupo
        assert "20:00" in resposta.privado
        assert registro.presentes("2026-08-24_solo-boss-2000") == frozenset()

    def test_as_duas_redacoes_do_leave_tambem_sao_diferentes(self, registro):
        responder_join(registro, [solo_boss()], em(18, 15), "J4guar")
        resposta = responder_leave(registro, [solo_boss()], em(18, 40), "J4guar")
        assert resposta.privado != resposta.grupo

    def test_leave_de_quem_nunca_joinou_nao_anuncia_nada(self, registro):
        resposta = responder_leave(registro, [solo_boss()], em(18, 40), "Korzis")

        assert resposta.grupo is None
        assert "nao estava" in resposta.privado.lower()
        assert "20:00" in resposta.privado

    def test_leave_repetido_para_de_anunciar_na_segunda_vez(self, registro):
        responder_join(registro, [solo_boss()], em(18, 15), "Kaus")
        responder_leave(registro, [solo_boss()], em(18, 40), "Kaus")

        segunda = responder_leave(registro, [solo_boss()], em(18, 45), "Kaus")
        assert segunda.grupo is None

    def test_depois_do_fechamento_o_leave_e_RECUSADO(self, registro):
        """D-14: uma lista fechada e historico, e reabrir historico e caro.

        E a mesma categoria de bug que o `.corrigir` do `loot.py` ja documenta:
        o registro ja alimentou uma decisao (a sugestao da vez do loot), entao
        muda-lo depois faz duas pessoas lembrarem coisas diferentes.
        """
        responder_join(registro, [solo_boss()], em(18, 15), "J4guar")

        resposta = responder_leave(registro, [solo_boss()], em(20, 1), "J4guar")

        assert resposta.grupo is None
        assert "20:00" in resposta.privado
        assert "comecou" in resposta.privado.lower()
        # E a recusa NAO pode ter tirado ninguem de lista nenhuma.
        assert registro.presentes("2026-08-24_solo-boss-2000") == frozenset({"j4guar"})

    def test_quem_NAO_estava_na_lista_fechada_opera_na_proxima(self, registro):
        """A recusa e para quem estava na lista, nao para todo mundo as 20:01.

        Quem nao entrou no boss das 20:00 nao tem historico para reabrir — o
        `.leave` dele fala do boss das 22:00, e responder "o boss ja comecou"
        seria uma recusa sem causa.
        """
        responder_join(registro, [solo_boss()], em(19, 0), "J4guar")

        resposta = responder_leave(registro, [solo_boss()], em(20, 1), "Kaus")

        assert "22:00" in resposta.privado
        assert "nao estava" in resposta.privado.lower()

    def test_quem_entrou_na_lista_das_2200_sai_dela(self, registro):
        """O caso simetrico: ha o que apagar, e e da ocorrencia certa.

        O `.join` e as 20:06, FORA da tolerancia de 5 minutos — dentro dela ele
        falaria do boss das 20:00, que acabou de nascer (ver
        `ocorrencia_do_join`). Este teste e sobre a lista SEGUINTE.
        """
        responder_join(registro, [solo_boss()], em(20, 6), "Kaus")

        resposta = responder_leave(registro, [solo_boss()], em(20, 7), "Kaus")

        assert resposta.grupo is not None
        assert "22:00" in resposta.grupo
        assert registro.presentes("2026-08-24_solo-boss-2200") == frozenset()

    def test_sem_nick_aponta_o_config_toml(self, registro):
        resposta = responder_leave(registro, [solo_boss()], em(18, 15), None)
        assert resposta.grupo is None
        assert "config.toml" in resposta.privado

    def test_sem_evento_com_chamada_explica(self, registro):
        resposta = responder_leave(registro, [sem_chamada()], em(18, 15), "J4guar")
        assert resposta.grupo is None
        assert "chamar_minutos_antes" in resposta.privado


class TestOLeaveNaoFicaQuebradoCincoMinutosPorBoss:
    """WR-02: a recusa de historico era consultada antes de qualquer coisa.

    `.leave` nao tem argumento. Enquanto a recusa vinha primeiro, quem estava
    na lista que acabou de fechar nao conseguia sair da lista SEGUINTE durante
    toda a tolerancia de 5 minutos — e ainda recebia uma recusa citando uma
    ocorrencia que ele nem mencionou. Com doze ocorrencias por dia isso e uma
    hora inteira por dia de comando quebrado.
    """

    CHAVE_2000 = "2026-08-24_solo-boss-2000"
    CHAVE_2200 = "2026-08-24_solo-boss-2200"

    def test_quem_estava_nas_DUAS_listas_sai_da_que_ainda_da(self, registro):
        registro.entrar(self.CHAVE_2000, "kaus")
        registro.entrar(self.CHAVE_2200, "kaus")

        resposta = responder_leave(registro, [solo_boss()], em(20, 1), "Kaus")

        assert "22:00" in resposta.privado, (
            "a recusa de historico respondeu por uma ocorrencia que o usuario "
            "nem mencionou, e a lista das 22:00 ficou intocada"
        )
        assert registro.presentes(self.CHAVE_2200) == frozenset()

    def test_e_a_lista_FECHADA_continua_intocada_D14(self, registro):
        """A garantia de D-14 e a CHAVE, e nunca foi a mensagem de recusa."""
        registro.entrar(self.CHAVE_2000, "kaus")
        registro.entrar(self.CHAVE_2200, "kaus")

        responder_leave(registro, [solo_boss()], em(20, 1), "Kaus")

        assert registro.presentes(self.CHAVE_2000) == frozenset({"kaus"}), (
            "o .leave reabriu historico: a lista das 20:00 ja foi ao grupo e "
            "ja alimentou a sugestao da vez do loot"
        )

    def test_quem_so_estava_na_fechada_ainda_recebe_a_recusa(self, registro):
        """A recusa continua existindo — ela so parou de vir na frente de tudo."""
        registro.entrar(self.CHAVE_2000, "kaus")

        resposta = responder_leave(registro, [solo_boss()], em(20, 1), "Kaus")

        assert resposta.grupo is None
        assert "20:00" in resposta.privado
        assert "comecou" in resposta.privado.lower()
        assert registro.presentes(self.CHAVE_2000) == frozenset({"kaus"})


class TestOJoinAtrasadoPelaPonte:
    """WR-01: o `.join` que a ponte Baileys entregou depois do alvo.

    A docstring de `fechar_ocorrencias` defendia a ordem "ler antes de marcar"
    com este cenario — e ele era impossivel, porque `responder_join` resolvia
    por `proxima_ocorrencia`, que exige `alvo > agora` estritamente. O `.join`
    de 20:00:03 caia silenciosamente no boss de DUAS HORAS DEPOIS e a pessoa
    achava que tinha confirmado o boss que estava comecando.
    """

    CHAVE_2000 = "2026-08-24_solo-boss-2000"

    def test_dentro_da_tolerancia_o_join_fala_do_boss_que_acabou_de_nascer(self):
        assert ocorrencia_do_join(em(20, 3), [solo_boss()]) == (
            "Solo Boss",
            em(20, 0),
        )

    def test_fora_da_tolerancia_volta_a_ser_o_proximo(self):
        assert ocorrencia_do_join(em(20, 6), [solo_boss()]) == (
            "Solo Boss",
            em(22, 0),
        )

    def test_antes_do_alvo_nada_muda(self):
        assert ocorrencia_do_join(em(18, 15), [solo_boss()]) == (
            "Solo Boss",
            em(20, 0),
        )

    def test_o_LEAVE_continua_estritamente_no_futuro(self):
        """A tolerancia e do `.join` e so dele: D-14 proibe reabrir a fechada."""
        assert ocorrencia_da_chamada(em(20, 1), [solo_boss()]) == (
            "Solo Boss",
            em(22, 0),
        )

    def test_o_join_de_200003_entra_na_lista_das_2000_e_e_ANUNCIADO(
        self, registro
    ):
        """O cenario da docstring, de ponta a ponta, agora de verdade.

        As 20:00:00 a lista esta vazia: lendo antes de marcar, nenhum marcador
        e queimado. As 20:00:03 chega o `.join`. O tick de 20:00:04 fecha e
        anuncia — que e exatamente o que a docstring sempre afirmou acontecer.
        """
        eventos = [solo_boss()]
        assert fechar_ocorrencias(registro, eventos, em(20, 0)) == []

        resposta = responder_join(
            registro, eventos, datetime(2026, 8, 24, 20, 0, 3), "J4guar"
        )
        assert "20:00" in resposta.privado, (
            "o .join atrasado caiu no boss de duas horas depois: a pessoa acha "
            "que confirmou o boss que esta comecando"
        )
        assert registro.presentes(self.CHAVE_2000) == frozenset({"j4guar"})

        fechados = fechar_ocorrencias(
            registro, eventos, datetime(2026, 8, 24, 20, 0, 4)
        )
        assert [f.nicks for f in fechados] == [("j4guar",)]


class TestOQueSeAnunciaVemDaLeituraQueVENCEU:
    """WR-10: a leitura que decide SE anunciar nao pode decidir O QUE anunciar.

    Com as duas instancias do usuario sobre a mesma pasta, um `.join` gravado
    entre a leitura e o `fechar` existe em disco e nao apareceria na mensagem —
    e nunca apareceria, porque o marcador ja foi queimado.
    """

    CHAVE = "2026-08-24_solo-boss-2000"

    def test_um_join_gravado_entre_a_leitura_e_o_marcador_ainda_aparece(
        self, registro, monkeypatch
    ):
        original = registro.fechar

        def fechar_com_corrida(chave):
            # A outra instancia grava o `.join` exatamente na janela entre a
            # leitura e a criacao do marcador.
            registro.entrar(self.CHAVE, "korzis")
            return original(chave)

        registro.entrar(self.CHAVE, "kaus")
        monkeypatch.setattr(registro, "fechar", fechar_com_corrida)

        fechados = fechar_ocorrencias(registro, [solo_boss()], em(20, 0))

        assert [f.nicks for f in fechados] == [("kaus", "korzis")], (
            "o korzis esta na lista em disco e ausente da lista que a party "
            "leu — e o marcador ja foi queimado, entao ele nunca vai aparecer"
        )

    def test_releitura_vazia_nao_apaga_a_lista_que_ia_ser_anunciada(
        self, registro, monkeypatch
    ):
        """O `or presentes`: disco travando bem no instante da releitura."""
        registro.entrar(self.CHAVE, "kaus")
        original = registro.fechar

        def fechar_e_travar(chave):
            ok = original(chave)
            monkeypatch.setattr(registro, "presentes", lambda _: frozenset())
            return ok

        monkeypatch.setattr(registro, "fechar", fechar_e_travar)

        fechados = fechar_ocorrencias(registro, [solo_boss()], em(20, 0))

        assert [f.nicks for f in fechados] == [("kaus",)]


class TestNomesDosMembros:
    """O mapa slug -> nick configurado, para o plano 10-04 exibir a lista.

    Sem ele a lista fechada sairia com a caixa do slug (`j4guar, kaus`), que e
    o que o disco guarda e nao o que o usuario escreveu.
    """

    class MembroFalso:
        """Qualquer objeto com `.nick` serve — de proposito.

        `presenca.py` NAO importa `comandos` (ver TestDirecaoDeImportacao),
        entao a assinatura pede a forma e nao o tipo.
        """

        def __init__(self, nick):
            self.nick = nick

    def test_o_slug_aponta_para_a_grafia_do_config(self):
        membros = [self.MembroFalso("J4guar"), self.MembroFalso("TioMad")]
        assert nomes_dos_membros(membros) == {
            "j4guar": "J4guar",
            "tiomad": "TioMad",
        }

    def test_lista_vazia_vira_mapa_vazio(self):
        assert nomes_dos_membros([]) == {}


class TestFechamentoDaLista:
    """D-12: no horario do boss a lista fecha e a party fica sabendo quem vai.

    TRES PROPRIEDADES, E AS TRES SAO DECISAO DE PRODUTO:

    1. **Zero confirmacao produz ZERO mensagem.** O Solo Boss e doze
       ocorrencias por dia; um fechamento que falasse "ninguem confirmou" doze
       vezes seria exatamente o volume que fez o usuario desligar
       `avisar_no_horario` neste evento. O piso e silencio.

    2. **O fechamento NAO passa por `avisar_no_horario`.** O evento de teste
       aqui tem o campo em `False`, como o `config.toml` real do usuario — e
       fecha do mesmo jeito. Amarrar o fechamento ao aviso de AGORA obrigaria
       o usuario a religar o aviso que ele desligou de proposito.

    3. **Le a lista ANTES de marcar, e isso tem teste proprio.** Marcar
       primeiro queimaria o marcador num tick de lista vazia, e um `.join`
       entregue tres segundos depois do alvo — dentro da tolerancia — nunca
       viraria mensagem. A garantia contra duplicata nao se perde: o `fechar`
       continua sendo a linha que decide quem fala.
    """

    def test_fecha_com_a_lista_cheia_e_devolve_todo_mundo(self, registro):
        chave = chave_da_ocorrencia("Solo Boss", em(20, 0))
        registro.entrar(chave, "j4guar")
        registro.entrar(chave, "tiomad")

        fechados = fechar_ocorrencias(registro, [solo_boss()], em(20, 0))

        assert len(fechados) == 1
        assert fechados[0].evento == "Solo Boss"
        assert fechados[0].alvo == em(20, 0)
        assert fechados[0].nicks == ("j4guar", "tiomad")

    def test_a_segunda_instancia_do_usuario_nao_fecha_de_novo(self, tmp_path):
        """Yazalaque e Faerlina dividem o `.agenda/`. Exatamente uma anuncia.

        E o mesmo `O_CREAT|O_EXCL` do `marcar`, alcancado pelo `fechar`: sem
        ele o grupo receberia a lista em dobro toda vez que o boss nascesse.
        """
        yazalaque = RegistroEmDisco(tmp_path)
        faerlina = RegistroEmDisco(tmp_path)
        yazalaque.entrar(chave_da_ocorrencia("Solo Boss", em(20, 0)), "kaus")

        primeiro = fechar_ocorrencias(yazalaque, [solo_boss()], em(20, 0))
        segundo = fechar_ocorrencias(faerlina, [solo_boss()], em(20, 0))

        assert len(primeiro) == 1
        assert segundo == [], "as duas instancias anunciaram a mesma lista"

    def test_dois_ticks_seguidos_fecham_uma_vez_so(self, registro):
        """A 1 Hz, a janela de 5 minutos tem ~300 ticks. Um deles fala."""
        registro.entrar(chave_da_ocorrencia("Solo Boss", em(20, 0)), "kaus")
        eventos = [solo_boss()]

        assert len(fechar_ocorrencias(registro, eventos, em(20, 0))) == 1
        assert fechar_ocorrencias(registro, eventos, em(20, 1)) == []

    def test_lista_vazia_nao_fecha_nem_escreve_nada_em_disco(
        self, registro, tmp_path
    ):
        """D-12 na sua forma mais literal: zero joins, zero de tudo.

        A comparacao e do CONTEUDO DA PASTA, e nao so do retorno: um
        `fechar_ocorrencias` que devolvesse lista vazia mas gravasse o marcador
        passaria na afirmacao sobre o retorno e quebraria o teste seguinte.
        """
        antes = sorted(caminho.name for caminho in tmp_path.iterdir())

        fechados = fechar_ocorrencias(registro, [solo_boss()], em(20, 0))

        assert fechados == []
        assert sorted(c.name for c in tmp_path.iterdir()) == antes

    def test_join_entregue_depois_do_alvo_ainda_vira_fechamento(self, registro):
        """A PROVA DA ORDEM. Sem ler antes de marcar, este teste falha.

        O caso e real: o `.join` sai do celular as 19:59:58 e a ponte do
        Chatwoot so o entrega no tick de 20:00:03. Ainda esta dentro da
        tolerancia de 5 minutos, entao ele conta.
        """
        eventos = [solo_boss()]
        chave = chave_da_ocorrencia("Solo Boss", em(20, 0))

        assert fechar_ocorrencias(registro, eventos, em(20, 0)) == []

        registro.entrar(chave, "korzis")

        fechados = fechar_ocorrencias(
            registro, eventos, datetime(2026, 8, 24, 20, 0, 4)
        )
        assert [f.nicks for f in fechados] == [("korzis",)], (
            "o marcador foi queimado cedo demais: o tick de lista vazia fechou "
            "a ocorrencia, e o .join entregue tres segundos depois nunca virou "
            "mensagem nenhuma"
        )

    def test_antes_do_alvo_nao_fecha(self, registro):
        registro.entrar(chave_da_ocorrencia("Solo Boss", em(20, 0)), "kaus")
        assert fechar_ocorrencias(registro, [solo_boss()], em(19, 59)) == []

    def test_fora_da_tolerancia_nao_fecha(self, registro):
        """20:06 ja passou dos 5 minutos: quem nao fechou, perdeu a vez.

        Nao e desperdicio — e o que impede o scanner que subiu as 21:30 de
        anunciar, no meio do farm, a lista de um boss que ja acabou.
        """
        registro.entrar(chave_da_ocorrencia("Solo Boss", em(20, 0)), "kaus")
        assert fechar_ocorrencias(registro, [solo_boss()], em(20, 6)) == []

    def test_evento_sem_chamada_nunca_fecha(self, registro):
        """TvT nao tem lista, entao nao tem o que fechar."""
        tvt = sem_chamada()
        registro.entrar(chave_da_ocorrencia("TvT", em(15, 0)), "kaus")
        assert fechar_ocorrencias(registro, [tvt], em(15, 0)) == []

    def test_avisar_no_horario_desligado_fecha_do_mesmo_jeito(self, registro):
        """O config REAL do usuario: `avisar_no_horario = false` no Solo Boss.

        O fechamento nao passa por `avisos_devidos`, e por isso o usuario nao
        precisa religar o aviso de AGORA — que ele desligou por causa das doze
        ocorrencias diarias — para ganhar a lista fechada (D-12).
        """
        evento = solo_boss(avisar_no_horario=False)
        assert evento.avisar_no_horario is False
        registro.entrar(chave_da_ocorrencia("Solo Boss", em(20, 0)), "j4guar")

        fechados = fechar_ocorrencias(registro, [evento], em(20, 0))
        assert [f.nicks for f in fechados] == [("j4guar",)]

    def test_a_lista_das_2000_nao_arrasta_a_das_2200(self, registro):
        """Os dois horarios do mesmo evento sao ocorrencias separadas."""
        registro.entrar(chave_da_ocorrencia("Solo Boss", em(20, 0)), "j4guar")
        registro.entrar(chave_da_ocorrencia("Solo Boss", em(22, 0)), "tiomad")

        fechados = fechar_ocorrencias(registro, [solo_boss()], em(20, 0))
        assert [f.nicks for f in fechados] == [("j4guar",)]

    def test_a_virada_da_meia_noite_fecha_a_lista_de_ontem(self, registro):
        """Um boss as 23:58 ainda esta recem-nascido as 00:02 do dia seguinte.

        A varredura inclui ONTEM pelo mesmo motivo de `silencio_ativo` — sem
        isso a lista de todo boss que nasce nos ultimos minutos do dia morreria
        sem ser anunciada. Os dois minutos aqui nao sao folga: a tolerancia e
        de 5, entao 23:58 e o ultimo horario cheio cuja janela atravessa a
        meia-noite de verdade.
        """
        evento = solo_boss(horarios=((23, 58),))
        registro.entrar(
            chave_da_ocorrencia("Solo Boss", em(23, 58, dia=24)), "kaus"
        )

        fechados = fechar_ocorrencias(registro, [evento], em(0, 2, dia=25))
        assert [f.alvo for f in fechados] == [em(23, 58, dia=24)]

    def test_o_fechamento_e_imutavel(self):
        """Estruturado e congelado, pelo mesmo motivo de `Aviso.chave` ser."""
        fechamento = Fechamento(evento="Solo Boss", alvo=em(20, 0), nicks=("kaus",))
        with pytest.raises(Exception):
            fechamento.evento = "TvT"


class TestTextoDeFechamento:
    """A redacao da lista fechada — e o parametro que nasce ignorado."""

    UM = Fechamento(evento="Solo Boss", alvo=em(20, 0), nicks=("j4guar", "tiomad"))

    def test_cita_o_evento_o_horario_e_os_nicks(self):
        texto = texto_de_fechamento(self.UM)
        assert "Solo Boss" in texto
        assert "20:00" in texto
        assert "J4guar" in texto
        assert "TioMad" not in texto  # sem mapa, cai no `exibir` do slug

    def test_com_o_mapa_sai_a_grafia_do_config(self):
        """D-10: o disco guarda `tiomad`, mas a party le `TioMad`."""
        nomes = {"j4guar": "J4guar", "tiomad": "TioMad"}
        texto = texto_de_fechamento(self.UM, nomes=nomes)
        assert "TioMad" in texto
        assert "Tiomad" not in texto

    def test_sem_o_mapa_cai_no_exibir_do_slug(self):
        """O recurso nao DEPENDE do mapa — sem ele a lista sai assim mesmo."""
        texto = texto_de_fechamento(self.UM, nomes=None)
        assert "Tiomad" in texto

    def test_slug_fora_do_mapa_ainda_aparece(self):
        """Um party-mate sem bloco `[[membro]]` nao pode sumir da lista."""
        texto = texto_de_fechamento(self.UM, nomes={"j4guar": "J4guar"})
        assert "J4guar" in texto and "Tiomad" in texto

    def test_sugestao_none_nao_acrescenta_nada(self):
        """Sem registro de loot a lista fecha igual — a sugestao e um EXTRA.

        E o caso real de quem roda `--so-agenda` sem pasta de loot, e o de
        `Sessao(loot=None)`. A lista fechada e o desfecho da chamada; perde-la
        por falta de estatistica seria trocar a mensagem que importa pela que
        enfeita.
        """
        assert texto_de_fechamento(self.UM) == texto_de_fechamento(
            self.UM, sugestao=None
        )

    def test_sugestao_preenchida_entra_no_fim(self):
        """O par `(slug, total)` de `loot.sugerir_a_vez` (plano 10-05)."""
        texto = texto_de_fechamento(self.UM, sugestao=("kaus", 2))
        assert texto.endswith("Sugestao de loot: Kaus (2 loots).")

    def test_a_sugestao_sai_com_a_grafia_do_config(self):
        """D-10 vale para a sugestao tambem: o disco tem `tiomad`.

        Sugerir com a caixa do slug no meio de uma frase que ja usa a grafia
        certa na lista leria como bot quebrado justamente na linha que a party
        vai discutir.
        """
        texto = texto_de_fechamento(
            self.UM, nomes={"tiomad": "TioMad"}, sugestao=("tiomad", 1)
        )
        assert texto.endswith("Sugestao de loot: TioMad (1 loot).")

    def test_um_loot_no_singular_e_zero_diz_que_nunca_pegou(self):
        """"1 loots" e "0 loots" leem como bug — e a frase e para humano."""
        um = texto_de_fechamento(self.UM, sugestao=("kaus", 1))
        nenhum = texto_de_fechamento(self.UM, sugestao=("kaus", 0))
        assert um.endswith("Sugestao de loot: Kaus (1 loot).")
        assert nenhum.endswith("Sugestao de loot: Kaus (ainda nenhum).")


class TestFecharENarrar:
    """CR-02 e WR-08: a UNICA implementacao da sequencia de fechamento.

    Ela existe por duas razoes que se somam. WR-08: os cinco passos estavam
    duplicados literalmente entre `sessao` e `__main__`, escrevendo no MESMO
    `.agenda/` e falando no MESMO grupo — um conserto aplicado de um lado so
    faria os dois modos do scanner anunciarem coisas diferentes sobre o mesmo
    boss. CR-02: o conserto que precisava ser aplicado era exatamente este.
    """

    CHAVE_2000 = "2026-08-24_solo-boss-2000"

    class MembroFalso:
        def __init__(self, nick):
            self.nick = nick

    def _loot(self, tmp_path):
        from l2scanner.loot import RegistroDeLoot

        return RegistroDeLoot(tmp_path / "loot")

    def test_sem_loot_a_lista_fecha_e_sai_sem_sugestao(self, registro):
        registro.entrar(self.CHAVE_2000, "kaus")

        narrados = fechar_e_narrar(registro, [solo_boss()], em(20, 0))

        assert [t for _, t in narrados] == [
            "Solo Boss das 20:00 comecando. Confirmaram: Kaus."
        ]

    def test_lista_vazia_nao_narra_nada(self, registro):
        assert fechar_e_narrar(registro, [solo_boss()], em(20, 0)) == []

    def test_com_loot_e_sem_dono_deste_boss_a_sugestao_SAI(self, registro, tmp_path):
        loot = self._loot(tmp_path)
        registro.entrar(self.CHAVE_2000, "kaus")

        narrados = fechar_e_narrar(registro, [solo_boss()], em(20, 0), (), loot)

        assert narrados[0][1].endswith("Sugestao de loot: Kaus (ainda nenhum).")

    def test_quando_ESTE_boss_ja_tem_dono_a_sugestao_e_CALADA(
        self, registro, tmp_path
    ):
        """CR-02, no ponto exato em que o bot se desmentia.

        O `.loot-Kaus` das 20:00 ja foi consumido e o credito esta em disco. A
        sugestao calculada depois disso aponta necessariamente para OUTRA
        pessoa — porque o Kaus acabou de ganhar um loot no placar — e a frase
        ia colada numa mensagem que fala do boss que esta COMECANDO. Dez
        minutos antes, o aviso de antecedencia do MESMO boss saiu no MESMO
        grupo com "Loot: Kaus".
        """
        loot = self._loot(tmp_path)
        loot.registrar("kaus", em(20, 0))
        registro.entrar(self.CHAVE_2000, "kaus")
        registro.entrar(self.CHAVE_2000, "j4guar")

        narrados = fechar_e_narrar(registro, [solo_boss()], em(20, 0), (), loot)

        assert narrados[0][1] == (
            "Solo Boss das 20:00 comecando. Confirmaram: J4guar, Kaus."
        ), "a mensagem sugeriu um loot que contradiz o dono ja registrado"

    def test_o_dono_de_OUTRO_boss_nao_cala_a_sugestao_deste(
        self, registro, tmp_path
    ):
        """Guarda contra prova vazia: a supressao e por OCORRENCIA, nao global."""
        loot = self._loot(tmp_path)
        loot.registrar("kaus", em(18, 0))
        registro.entrar(self.CHAVE_2000, "kaus")
        registro.entrar(self.CHAVE_2000, "j4guar")

        narrados = fechar_e_narrar(registro, [solo_boss()], em(20, 0), (), loot)

        assert narrados[0][1].endswith("Sugestao de loot: J4guar (ainda nenhum).")

    def test_um_pegou_mandado_a_mao_tambem_cala_a_sugestao(
        self, registro, tmp_path
    ):
        """O disco sabe o que o retorno de `consumir` nao conta.

        `.pegou` registra dono sem passar por designacao nenhuma, e `consumir`
        devolve `None` quando a OUTRA instancia venceu a corrida do `pegou_`.
        Nos dois casos, so a leitura do disco responde certo.
        """
        loot = self._loot(tmp_path)
        loot.registrar("j4guar", em(20, 0))
        registro.entrar(self.CHAVE_2000, "kaus")

        narrados = fechar_e_narrar(registro, [solo_boss()], em(20, 0), (), loot)

        assert "Sugestao de loot" not in narrados[0][1]

    def test_os_membros_dao_a_grafia_do_config(self, registro):
        registro.entrar(self.CHAVE_2000, "tiomad")

        narrados = fechar_e_narrar(
            registro, [solo_boss()], em(20, 0), [self.MembroFalso("TioMad")]
        )

        assert "TioMad" in narrados[0][1] and "Tiomad" not in narrados[0][1]

    def test_D13_continua_valendo_a_lista_SUGERE_e_nao_manda(self):
        """Calar a sugestao nao bloqueia nada: `.loot-<nick>` segue obedecendo.

        Lido do codigo: `responder_designacao` nao pode ter ganhado uma recusa
        por causa deste conserto. Um bloqueio ali transformaria uma
        conveniencia em obstaculo no pior momento — alguem chegou sem avisar e
        a party precisa designar agora.
        """
        import inspect

        from l2scanner.loot import responder_designacao

        fonte = inspect.getsource(responder_designacao)
        assert "presenca" in fonte, "o aviso de quem nao confirmou sumiu"
        assert "designar(" in fonte, "a designacao deixou de ser gravada"


class TestUmaImplementacaoSoDoFechamento:
    """WR-08: os dois modos do scanner nao podem divergir sobre o mesmo boss.

    Lido por AST, e nao por grep: as docstrings desta fase escrevem os nomes
    das duas funcoes de proposito, ao explicar a restricao.
    """

    def _chamadas(self, modulo: str, funcao: str) -> set[str]:
        arvore = ast.parse((RAIZ / "l2scanner" / modulo).read_text(encoding="utf-8"))
        alvo = next(
            no
            for no in ast.walk(arvore)
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
            and no.name == funcao
        )
        return {
            no.func.id
            for no in ast.walk(alvo)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Name)
        }

    @pytest.mark.parametrize(
        "modulo,funcao",
        [
            ("sessao.py", "_processar_agenda"),
            ("__main__.py", "_fechar_listas_de_presenca"),
        ],
    )
    def test_os_dois_lados_chamam_a_mesma_funcao(self, modulo, funcao):
        chamadas = self._chamadas(modulo, funcao)
        assert "fechar_e_narrar" in chamadas, (
            f"{modulo}:{funcao} montou a propria sequencia de fechamento — "
            "qualquer conserto a partir daqui precisa ser feito duas vezes"
        )
        assert not ({"sugerir_a_vez", "texto_de_fechamento"} & chamadas), (
            f"{modulo}:{funcao} voltou a decidir sozinho o texto do fechamento"
        )


class TestFormaDoTexto:
    """Toda frase que o bot produz, junta, contra as regras do projeto.

    Sem acento porque o resto do codigo e das mensagens nao tem, e uma unica
    frase acentuada no meio le como colada de outro lugar. Sem quebra de linha
    porque o despachante do Chatwoot manda uma mensagem por chamada e um `\\n`
    viraria duas bolhas no WhatsApp.
    """

    def todas_as_frases(self, tmp_path):
        frases: list[str] = []
        registro = RegistroEmDisco(tmp_path / "agenda")
        eventos = [solo_boss()]

        for resposta in (
            responder_join(registro, eventos, em(18, 15), "J4guar"),
            responder_join(registro, eventos, em(18, 20), "J4guar"),
            responder_join(registro, eventos, em(18, 25), None),
            responder_join(registro, [sem_chamada()], em(18, 30), "Kaus"),
            responder_leave(registro, eventos, em(18, 35), "Korzis"),
            responder_leave(registro, eventos, em(18, 40), "J4guar"),
            responder_leave(registro, eventos, em(18, 45), None),
            responder_leave(registro, [sem_chamada()], em(18, 50), "Kaus"),
        ):
            frases.append(resposta.privado)
            if resposta.grupo is not None:
                frases.append(resposta.grupo)

        # A recusa do D-14 precisa de alguem na lista que acabou de fechar.
        responder_join(registro, eventos, em(19, 0), "TioMad")
        recusa = responder_leave(registro, eventos, em(20, 1), "TioMad")
        frases.append(recusa.privado)

        # E o "falhou", que so acontece com o disco fora do ar.
        pasta_morta = tmp_path / "morta"
        registro_morto = RegistroEmDisco(pasta_morta)
        pasta_morta.rmdir()
        frases.append(responder_join(registro_morto, eventos, em(18, 15), "Kaus").privado)

        # A lista fechada passa pelas MESMAS regras: ela sai pelo mesmo
        # despachante, para o mesmo grupo, e uma frase acentuada no meio le
        # como colada de outro lugar.
        fechamento = Fechamento(
            evento="Solo Boss", alvo=em(20, 0), nicks=("tiomad",)
        )
        frases.append(texto_de_fechamento(fechamento, nomes={"tiomad": "TioMad"}))
        # E a MESMA frase com a sugestao de loot do plano 10-05: ela sai
        # colada na anterior, no mesmo grupo, e nao pode ser a unica com
        # acento ou quebra de linha.
        for total in (0, 1, 3):
            frases.append(
                texto_de_fechamento(
                    fechamento,
                    nomes={"tiomad": "TioMad"},
                    sugestao=("tiomad", total),
                )
            )

        return frases

    def test_ha_frase_suficiente_para_a_prova_valer(self, tmp_path):
        """Guarda contra prova vazia: um laco sobre lista curta prova pouco."""
        frases = self.todas_as_frases(tmp_path)
        assert len(frases) >= 12, f"so {len(frases)} frases entraram na prova"

    def test_nenhuma_frase_tem_acento(self, tmp_path):
        for frase in self.todas_as_frases(tmp_path):
            acentuados = [
                c for c in frase if unicodedata.combining(c) or ord(c) > 127
            ]
            assert not acentuados, f"{frase!r} tem {acentuados}"

    def test_nenhuma_frase_tem_quebra_de_linha(self, tmp_path):
        for frase in self.todas_as_frases(tmp_path):
            assert "\n" not in frase, f"{frase!r} viraria duas bolhas no WhatsApp"

    def test_nenhuma_frase_e_vazia(self, tmp_path):
        for frase in self.todas_as_frases(tmp_path):
            assert frase.strip(), "o despachante enviaria uma bolha em branco"

    def test_toda_resposta_com_alvo_cita_o_horario(self, tmp_path):
        """D-07 aplicado a TODAS as respostas, e nao so ao `.join` que deu certo.

        "Voce ja esta na lista" sem horario e ambiguo entre o boss das 20:00 e
        o das 22:00 — e as 19:59 essa ambiguidade custa uma pessoa.
        """
        registro = RegistroEmDisco(tmp_path)
        eventos = [solo_boss()]

        com_alvo = [
            responder_join(registro, eventos, em(18, 15), "J4guar"),
            responder_join(registro, eventos, em(18, 20), "J4guar"),
            responder_leave(registro, eventos, em(18, 25), "Korzis"),
            responder_leave(registro, eventos, em(18, 30), "J4guar"),
        ]
        for resposta in com_alvo:
            assert "20:00" in resposta.privado, resposta.privado
            if resposta.grupo is not None:
                assert "20:00" in resposta.grupo, resposta.grupo


class TestRespostaDePresenca:
    def test_o_grupo_e_None_por_padrao(self):
        """`None` e o default para o silencio no grupo ser o caminho facil."""
        assert RespostaDePresenca(privado="oi").grupo is None

    def test_e_imutavel(self):
        resposta = RespostaDePresenca(privado="oi", grupo="oi grupo")
        with pytest.raises(Exception):
            resposta.privado = "outro"


def _modulos_importados(caminho: Path) -> set[str]:
    """Os modulos que um arquivo REALMENTE importa, lidos da arvore sintatica.

    AST, e nunca `grep`. As docstrings de `presenca.py` e de `loot.py` CITAM
    `comandos` e `sessao` de proposito, para explicar a restricao por escrito —
    uma busca textual daria positivo justamente na documentacao que protege a
    regra, e o teste morreria de falso alarme na primeira leitura.
    """
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    achados: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                achados.add(alias.name.split(".")[0])
        elif isinstance(no, ast.ImportFrom):
            if no.module:
                achados.update(no.module.split("."))
            for alias in no.names:
                achados.add(alias.name)
    return achados


class TestDirecaoDeImportacao:
    """A direcao e `presenca -> loot -> agenda`, e nao pode fechar ciclo.

    Um ciclo aqui nao degrada nada: mata os dois modulos com `ImportError` no
    arranque. A regra ja estava escrita no fim da docstring de `loot.py` desde
    a Fase 8; esta classe a transforma de politica em estrutura.
    """

    def test_presenca_nao_importa_comandos_nem_sessao(self):
        importados = _modulos_importados(RAIZ / "l2scanner" / "presenca.py")
        proibidos = {"comandos", "sessao", "__main__"} & importados
        assert not proibidos, f"presenca.py importa {proibidos}"

    def test_loot_nunca_importa_presenca_comandos_nem_sessao(self):
        """No plano 10-05 quem precisa da lista no loot a recebe por PARAMETRO.

        Os TRES nomes, e nao so `presenca`. O fim da docstring do `loot.py`
        proibe os tres desde a Fase 8 — mas ate aqui `comandos` e `sessao`
        eram proibidos so por escrito, e regra que vive em docstring e
        cumprida ate o dia em que alguem tem pressa. O verificador da Fase 10
        media exatamente esta lacuna: o must-have afirmava os tres, o portao
        guardava um.
        """
        importados = _modulos_importados(RAIZ / "l2scanner" / "loot.py")
        proibidos = {"presenca", "comandos", "sessao", "__main__"} & importados
        assert not proibidos, f"loot.py importa {proibidos}"

    def test_agenda_nao_importa_nenhum_dos_dois(self):
        """A agenda e a base: ela nao conhece nem loot nem presenca."""
        importados = _modulos_importados(RAIZ / "l2scanner" / "agenda.py")
        assert not ({"loot", "presenca", "comandos"} & importados)

    def test_respawn_so_conhece_agenda_e_bosses(self):
        """A direcao e `respawn -> {agenda, bosses}`, e nada mais.

        `respawn.py` e chamado pelos DOIS lacos (o principal, na `sessao`, e o
        `--so-agenda` do plano 02-02). Um import de `sessao` aqui fecharia o
        ciclo na hora; um import de `comandos` ou `loot` arrastaria para dentro
        da previsao de respawn dependencias que ela nao tem motivo para ter.
        """
        importados = _modulos_importados(RAIZ / "l2scanner" / "respawn.py")
        proibidos = {
            "comandos",
            "sessao",
            "presenca",
            "loot",
            "__main__",
        } & importados
        assert not proibidos, f"respawn.py importa {proibidos}"

    def test_respawn_importa_mesmo_de_agenda_e_de_bosses(self):
        """Guarda contra prova vazia, no molde do teste da `presenca`.

        Um `respawn.py` que nao importasse NADA passaria no teste acima sem
        provar coisa alguma. Este afirma que a direcao permitida esta em uso —
        e ela precisa estar: `apelido_do_evento` vindo da `agenda` e o que faz
        a chave da ancora casar com a poda, e uma quinta copia daquela
        expressao regular divergiria no primeiro ajuste.
        """
        importados = _modulos_importados(RAIZ / "l2scanner" / "respawn.py")
        assert "agenda" in importados
        assert "bosses" in importados

    def test_nem_agenda_nem_bosses_importam_respawn(self):
        """A volta do ciclo, afirmada do outro lado.

        `agenda.py` declara `PREFIXO_NASCIMENTO` e `bosses.py` declara
        `OrigemDoAviso` — os dois dados que a ancora usa. A tentacao de fazer
        um deles chamar `respawn` para "fechar a semantica" mataria os tres com
        `ImportError` no arranque.
        """
        for modulo in ("agenda.py", "bosses.py"):
            importados = _modulos_importados(RAIZ / "l2scanner" / modulo)
            assert "respawn" not in importados, f"{modulo} importa respawn"

    def test_presenca_importa_mesmo_de_agenda_e_de_loot(self):
        """Guarda contra prova vazia.

        Um `presenca.py` que nao importasse NADA passaria nos tres testes
        acima sem provar coisa alguma. Este afirma que a direcao permitida
        esta de fato em uso.
        """
        importados = _modulos_importados(RAIZ / "l2scanner" / "presenca.py")
        assert "agenda" in importados
        assert "loot" in importados

    def test_o_pacote_inteiro_importa(self):
        """A prova final de que nenhum ciclo se fechou: o import real roda."""
        import importlib

        for nome in ("l2scanner.presenca", "l2scanner.loot", "l2scanner.__main__"):
            assert importlib.import_module(nome) is not None


class TestSemRelogioProprio:
    """O tempo entra por parametro nos QUATRO modulos, nao so no arquivo novo.

    A disciplina esta travada no CONTEXT desde a Fase 6 ("o tempo entra por
    parametro em tudo") e os tres ganharam codigo nesta fase. Cobrir so o
    arquivo novo deixaria a proibicao como politica nos outros dois — e e
    justamente num `datetime.now()` enfiado dentro de `agenda.py` que a
    cobertura de meia-noite e da corrida de duas instancias morreria em
    silencio, porque os testes continuariam passando o `agora` que o codigo ja
    nao usaria.

    AST, e nunca `grep`: as docstrings de `agenda.py` e de `loot.py` citam
    `datetime.now()` ao explicar a disciplina.

    `date.today()` NAO esta na proibicao, e a excecao e deliberada: o unico uso
    e o default de `podar(hoje=None)`, um parametro que os testes sempre
    passam. A regra protegida aqui e "o instante da DECISAO vem de fora".

    `bosses.py` entrou na Fase 1 do workstream `tiat`, ANTES de ter uma linha
    de logica de tempo, e a antecipacao e a decisao. O instante que
    `VigiaDeBosses.avaliar` recebe por parametro e exatamente o instante que a
    Fase 2 vai gravar em disco como ANCORA do ciclo de respawn: um
    `datetime.now()` enfiado ali faria a ancora registrar o momento em que o
    codigo rodou, e nao o momento do frame — e num `--replay`, ou nos dois
    lacos que a Fase 2 precisa costurar, os testes continuariam verdes
    passando um `agora` que o codigo ja nao usaria. E a mesma familia de
    defeito descrita acima para `agenda.py`, com a diferenca de que aqui o
    defeito ESCREVE EM DISCO e a previsao errada sai horas depois, com a mesma
    cara de uma certa. Adotar agora custa uma linha, porque o modulo ja cumpre
    a regra; adotar na Fase 2 seria adotar um modulo que ja pode ter violado
    a regra, e o portao nasceria vermelho ou nasceria afrouxado.

    `respawn.py` entrou na Fase 2 do workstream `tiat`, e nele a regra tem um
    DENTE A MAIS do que em `agenda.py`. O instante que `janelas_devidas` recebe
    e o mesmo que decide se uma mensagem sai AGORA ou NUNCA — a janela de
    tolerancia e de cinco minutos, e fora dela o aviso nao ressuscita. Um
    relogio proprio enfiado ali faria os testes continuarem verdes passando um
    `agora` que o codigo ja nao usaria, e as quatro bordas de tolerancia
    deixariam de provar qualquer coisa.

    A diferenca em relacao a `agenda.py` e que aqui o instante da ancora
    tambem foi LIDO DE DISCO horas antes. Uma divergencia entre o relogio do
    CALCULO e o relogio da ANCORA nao produz um aviso faltando — produz uma
    previsao ERRADA, entregue no grupo, com exatamente a mesma cara de uma
    certa. E o modo de falha caro desta fase, e ele nao aparece em teste
    nenhum que passe o tempo por parametro.

    `acervo.py` entrou na Fase 1 do workstream `identidade`, e ele entra na
    tupla ANTES de ter uma linha de logica de tempo — a antecipacao E a
    decisao. O acervo de assinaturas e DURAVEL e NAO PODADO por decisao
    travada do usuario, que viu o numero na mao (562 bytes por assinatura,
    medido no `calibration.json` real em 2026-08-31) e dispensou qualquer
    limpeza no v1. A maneira de um modulo assim adquirir poda POR ACIDENTE e
    adquirindo um relogio proprio primeiro: um `datetime.now()` num `gravar`
    ou numa varredura vira, duas fases depois, um "so leio o que e recente"
    que ninguem escreveu de proposito — e o que se perde nao e um aviso, e a
    identidade de uma pessoa que o scanner passa a chamar de "Membro 3".
    Adotar agora custa uma linha, porque o modulo ja cumpre a regra; adotar
    na Fase 2 seria adotar um modulo que ja pode ter violado a regra, e o
    portao nasceria vermelho ou nasceria afrouxado.

    `aprendiz.py` entrou na Fase 2 do workstream `identidade`, e ele tambem
    entra ANTES de ter uma linha de logica de tempo — a antecipacao E a decisao,
    igual a de `bosses.py` e a de `acervo.py`. Contar LEITURAS e nao SEGUNDOS e
    o coracao de D-09: o tick nao e garantido (a captura mira ~1 Hz, mas um
    frame doente, uma cegueira ou uma varredura de mercado mudam o intervalo
    real), e um `time.time()` que aparecesse aqui para "so aprender depois de 5
    segundos" transformaria a UNICA logica nova da fase numa dependencia de
    relogio.

    O que se perde nesse caso e especifico e caro: o replay de uma gravacao
    deixaria de produzir o mesmo acervo que a sessao ao vivo produziu, e o
    acervo e IRREVERSIVEL — nao ha comando de esquecer no v1. Ou seja, a
    divergencia entre o replay e o campo nao seria um teste instavel, seria uma
    entrada permanente que ninguem consegue reproduzir para investigar.
    """

    MODULOS = (
        "agenda.py",
        "loot.py",
        "presenca.py",
        "bosses.py",
        "respawn.py",
        "acervo.py",
        "aprendiz.py",
    )

    @staticmethod
    def _relogios_proprios(fonte: str) -> list[str]:
        arvore = ast.parse(fonte)
        return [
            f"{getattr(no.value, 'id', None) or getattr(no.value, 'attr', '?')}.{no.attr}"
            for no in ast.walk(arvore)
            if isinstance(no, ast.Attribute)
            and no.attr in {"now", "utcnow"}
            and (getattr(no.value, "id", None) or getattr(no.value, "attr", None))
            in {"datetime", "date", "time"}
        ]

    @pytest.mark.parametrize("modulo", MODULOS)
    def test_nenhum_now_de_datetime_na_arvore(self, modulo):
        fonte = (RAIZ / "l2scanner" / modulo).read_text(encoding="utf-8")
        achados = self._relogios_proprios(fonte)
        assert not achados, f"{modulo} tem relogio proprio: {achados}"

    @pytest.mark.parametrize("modulo", MODULOS)
    def test_a_prova_pega_um_relogio_enfiado_em_CADA_modulo(self, modulo):
        """Guarda contra prova vazia, POR MODULO.

        O teste generico de detector (abaixo) prova que a busca funciona sobre
        um fonte de mentira. Este prova que ela funciona sobre o fonte REAL de
        cada modulo — injetando a linha proibida no fim do arquivo em memoria e
        exigindo que o detector a acuse. Sem ele, um modulo cujo caminho
        estivesse errado passaria verde para sempre.
        """
        fonte = (RAIZ / "l2scanner" / modulo).read_text(encoding="utf-8")
        assert self._relogios_proprios(fonte) == []

        envenenado = fonte + "\n_agora_escondido = datetime.now()\n"
        assert self._relogios_proprios(envenenado), (
            f"o portao nao acusaria um datetime.now() dentro de {modulo}"
        )

    def test_a_prova_pega_de_verdade_um_relogio_proprio(self):
        """Guarda contra prova vazia: o detector acha o que deveria achar."""
        arvore = ast.parse("from datetime import datetime\nx = datetime.now()\n")
        achados = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Attribute) and no.attr == "now"
        ]
        assert achados, "o detector nao acharia nem um datetime.now() literal"


# ---------------------------------------------------------------------------
# A COSTURA: `atender_comandos` e o funil unico por onde toda resposta sai.
#
# As pecas abaixo sao de MODULO e nao de classe, de proposito: a tabela de
# regressao dos comandos antigos e a prova dos ramos novos exercitam a MESMA
# funcao pelo MESMO caminho. Duas montagens paralelas provariam que cada uma
# concorda consigo mesma, em vez de provar o despacho.
# ---------------------------------------------------------------------------

# O telefone da allowlist de DONO. Precisa ser o de dono para que TODOS os
# ramos sejam alcancaveis num teste so: o nivel de membro (plano 10-01) alcanca
# exclusivamente `.join` e `.leave`, entao um telefone de membro nao chegaria
# perto do `.corrigir` nem do `.pegou`.
DONO = "+5544997077000"


class DespachanteQueGrava:
    """Grava `(texto, categoria, conversa_alvo)` em vez de mandar para a rede.

    O `Despachante` de verdade tem fila e thread; usa-lo aqui obrigaria cada
    teste a `iniciar()`/`encerrar()` e mediria o TRANSPORTE, que nao e o que
    esta em jogo. O que esta em jogo e o DESTINO, e o destino e o terceiro
    argumento desta chamada.

    Truthy de proposito: `atender_comandos` testa `if not despachante`, entao
    um falso que implementasse `__len__` ou `__bool__` sairia silenciosamente
    do caminho que ele existe para exercitar.
    """

    def __init__(self) -> None:
        self.despachos: list[tuple[str, object, str | None]] = []

    def despachar(self, texto, categoria=None, conversa_alvo=None) -> None:
        self.despachos.append((texto, categoria, conversa_alvo))

    @property
    def alvos(self) -> list:
        """So os destinos, na ordem em que sairam. `None` e o grupo."""
        return [conversa for _, _, conversa in self.despachos]

    @property
    def textos(self) -> list:
        return [texto for texto, _, _ in self.despachos]


class LeitorDeUmaMensagem:
    """Um `LeitorDeComandos` falso que devolve UMA mensagem crua.

    Carrega `telefones` E `membros` porque as duas listas sao o que
    `atender_comandos` consulta do leitor. Um falso sem `membros` mediria um
    leitor que nao existe em producao — e `membros` e justamente o elo que liga
    o nivel de autorizacao do plano 10-01 ao caminho real.

    A mensagem e CRUA (dict como a API do Chatwoot devolve) de proposito: as
    travas de `comandos_novos` — tipo, nota privada, id repetido, vocabulario e
    autorizacao — tem de rodar de verdade. Montar `MensagemDeComando` a mao
    aqui pularia justamente a costura, que e onde os erros deste projeto moram.
    """

    ativo = True

    def __init__(
        self,
        texto: str,
        *,
        conversa=None,
        telefone: str = DONO,
        membros=(),
        identificador: int = 4242,
    ) -> None:
        self.telefones = [telefone]
        self.membros = list(membros)
        self._mensagem = {
            "id": identificador,
            "content": texto,
            "message_type": 0,
            "private": False,
            "sender": {"name": "Yazalaque", "phone_number": telefone},
            "conversation_id": conversa,
        }

    def ler(self, _monotonico):
        return [self._mensagem]


def eventos_classicos() -> list:
    """A agenda de ANTES desta fase: ninguem pediu chamada.

    Deliberadamente sem `chamar_minutos_antes`. A tabela de regressao dos
    comandos antigos nao pode depender de nenhuma peca da lista de presenca —
    se dependesse, ela deixaria de medir "o que o codigo fazia antes".
    """
    return [
        EventoAgendado(nome="Prime", horarios=((20, 0),), silenciar_minutos=120),
        EventoAgendado(
            nome="Solo Boss",
            horarios=tuple((h, 0) for h in range(0, 24, 2)),
            avisar_no_horario=False,
        ),
    ]


def despachos_de(
    texto: str,
    tmp_path,
    *,
    eventos=None,
    agora=None,
    conversa="1",
    telefone: str = DONO,
    membros=(),
    loot=None,
    registro=None,
    identificador: int = 4242,
    rastreador=None,
) -> DespachanteQueGrava:
    """Roda `atender_comandos` como o LACO roda, e devolve o que saiu.

    `agora` e `datetime`, `monotonico` e float: os dois relogios de
    `atender_comandos` nao sao intercambiaveis, e passar um so foi o crash de
    producao de 2026-08-24 (`TypeError: '>=' not supported between 'timedelta'
    and 'float'`). Este helper existe, em parte, para que nenhum teste desta
    fase nasca com aquele erro dentro.

    `registro` e injetavel para o caso de DUAS chamadas sobre o mesmo disco —
    e o que o `.join` repetido precisa, e um registro novo a cada chamada
    apagaria justamente a memoria que ele existe para exercitar.
    """
    import time

    from l2scanner.__main__ import atender_comandos

    despachante = DespachanteQueGrava()
    atender_comandos(
        LeitorDeUmaMensagem(
            texto,
            conversa=conversa,
            telefone=telefone,
            membros=membros,
            identificador=identificador,
        ),
        registro if registro is not None else RegistroEmDisco(tmp_path / "agenda"),
        list(eventos) if eventos is not None else eventos_classicos(),
        despachante,
        agora if agora is not None else em(20, 30),
        time.monotonic(),
        rastreador,
        loot=loot,
    )
    return despachante


class TestDestinoDosComandosAntigos:
    """A tabela dos comandos que ja existiam, e para onde cada um responde.

    ESTA CLASSE FOI ESCRITA E RODADA VERDE ANTES DE O BLOCO DE DESPACHO SER
    TOCADO, e essa ordem e a razao de ela existir. Um teste escrito depois de
    uma refatoracao prova que a refatoracao concorda consigo mesma; escrito
    antes, ele e a rede. O git guarda a prova: o commit desta classe vem antes
    do commit que generaliza o `__main__.py`, e o diff entre os dois nao a
    toca.

    O modo de falha que ela existe para pegar e SILENCIOSO — a mensagem chega,
    no lugar errado — e ja aconteceu neste projeto: `.status` perguntado as
    23:04:42 na conversa 1 (privado) foi respondido as 23:04:52 na conversa 13
    (grupo), e o usuario concluiu que nao tinha funcionado.

    O QUE ELA AFIRMA E SO O DESTINO, nunca a redacao inteira de uma mensagem.
    Amarrar a frase faria a rede quebrar em toda melhoria de texto, e uma rede
    que grita a toa e uma rede que se aprende a ignorar.
    """

    # (rotulo, texto digitado, o grupo recebe o eco?)
    #
    # `eco_no_grupo=True` significa, hoje, "o grupo recebe o MESMO texto do
    # privado" — e e isso que os casos abaixo afirmam, comparando os dois.
    TABELA = [
        (".cancelar", ".cancelar", True),
        (".solo", ".solo", True),
        (".party", ".party", True),
        (".status", ".status", False),
        (".help", ".help", False),
        (".loot-<nick>", ".loot-J4guar", False),
        (".loot-", ".loot-", False),
        (".<nick>", ".J4guar", False),
        (".corrigir-<nick>", ".corrigir-Korzis", False),
        (".pegou <hora> <nick>", ".pegou 18:00 Korzis", False),
        # Os dois do desligamento do Solo Boss. Nao sao "antigos" — entraram
        # nesta tabela porque o tripwire logo abaixo os TROUXE, derivando a
        # cobertura de `set(Comando)`. E entram com o mesmo contrato de destino
        # do `.cancelar`, pela mesma razao dele: mudam o que o GRUPO INTEIRO
        # recebe daqui pra frente. Aqui pesa mais — sao 12 chamadas por dia da
        # party toda, e o efeito e a AUSENCIA de mensagem, que do lado dos
        # outros e indistinguivel do bot ter caido.
        (".desativarsoloboss", ".desativarsoloboss", True),
        (".ativarsoloboss", ".ativarsoloboss", True),
        # E o par da LISTA DE PRESENCA, que entrou pela MESMA pinca: o tripwire
        # abaixo deriva a cobertura de `set(Comando)`, os dois nascem fora de
        # `COMANDOS_DE_MEMBRO`, e por isso caem em `antigos` e cobram linha
        # aqui. Mesmo contrato de destino do par acima, e pela mesma razao:
        # muda o que o GRUPO INTEIRO recebe daqui pra frente — a chamada "Quem
        # vai?" para de sair e o /entrar de todos passa a ser recusado.
        (".desativarlista", ".desativarlista", True),
        (".ativarlista", ".ativarlista", True),
    ]

    def _loot(self, tmp_path):
        """Um registro de loot com J4guar ja conhecido.

        `.<nick>` so e reconhecido para nick CONHECIDO — o portao contra o
        scanner responder lixo a qualquer palavra com ponto. Sem este registro
        o caso da consulta nao chegaria ao despacho, e o teste passaria
        provando nada.
        """
        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")
        loot.registrar("J4guar", em(18, 0))
        return loot

    @pytest.mark.parametrize(
        "rotulo,texto,eco_no_grupo",
        TABELA,
        ids=[linha[0] for linha in TABELA],
    )
    def test_destino_de_cada_comando_antigo(
        self, rotulo, texto, eco_no_grupo, tmp_path
    ):
        despachante = despachos_de(texto, tmp_path, loot=self._loot(tmp_path))

        assert despachante.despachos, f"{rotulo} nao respondeu nada"
        assert despachante.alvos[0] == "1", (
            f"{rotulo} tinha que responder na conversa de origem; "
            f"o primeiro despacho foi para {despachante.alvos[0]!r}"
        )

        if eco_no_grupo:
            assert despachante.alvos == ["1", None], (
                f"{rotulo} tinha que responder na origem E avisar o grupo; "
                f"os destinos foram {despachante.alvos}"
            )
            assert despachante.textos[0] == despachante.textos[1], (
                f"{rotulo} ecoou no grupo com texto DIFERENTE do privado"
            )
        else:
            assert despachante.alvos == ["1"], (
                f"{rotulo} tinha que responder SO na conversa de origem; "
                f"os destinos foram {despachante.alvos}"
            )

    @pytest.mark.parametrize(
        "rotulo,texto,eco_no_grupo",
        TABELA,
        ids=[linha[0] for linha in TABELA],
    )
    def test_todo_destino_antigo_atravessa_o_silencio(
        self, rotulo, texto, eco_no_grupo, tmp_path
    ):
        """Resposta de comando e `Categoria.SEMPRE`, sem excecao.

        `Categoria.NORMAL` e cortada no transporte quando ha silencio de
        TvT/Prime. Uma resposta de comando cortada assim seria a mesma falha
        silenciosa do destino errado, vestida de outra roupa: quem digitou nao
        recebe nada e conclui que o bot morreu — justo quando ele esta calado
        DE PROPOSITO e mais precisaria dizer isso.
        """
        from l2scanner.notificador import Categoria

        despachante = despachos_de(texto, tmp_path, loot=self._loot(tmp_path))

        categorias = {categoria for _, categoria, _ in despachante.despachos}
        assert categorias == {Categoria.SEMPRE}, (
            f"{rotulo} despachou com categoria {categorias}"
        )

    def test_a_tabela_cobre_todo_comando_ANTIGO_do_enum(self):
        """Guarda contra prova vazia: nenhum ramo antigo ficou de fora.

        DERIVADA do enum e nao digitada: `set(Comando)` menos os comandos que
        esta fase acrescenta (`COMANDOS_DE_MEMBRO` e exatamente `.join` e
        `.leave`). Um comando novo no enum entra nesta prova sozinho — e se ele
        nao tiver linha na tabela, este teste diz o NOME dele, em vez de o
        silencio custar uma regressao de destino.
        """
        from l2scanner.comandos import (
            COMANDOS_DE_MEMBRO,
            Comando,
            interpretar,
            interpretar_dinamico,
        )

        conhecidos = frozenset({"j4guar", "korzis"})
        cobertos = set()
        for _, texto, _ in self.TABELA:
            comando = interpretar(texto)
            if comando is None:
                dinamico = interpretar_dinamico(texto, conhecidos)
                assert dinamico is not None, f"{texto!r} nao e comando nenhum"
                comando = dinamico[0]
            cobertos.add(comando)

        antigos = set(Comando) - COMANDOS_DE_MEMBRO
        assert antigos, "o conjunto derivado ficou vazio; a prova nao prova nada"
        faltando = antigos - cobertos
        assert not faltando, (
            "comando sem linha na tabela de destino: "
            + ", ".join(sorted(c.name for c in faltando))
        )

    def test_sem_conversa_de_origem_a_resposta_cai_no_grupo(self, tmp_path):
        """Compatibilidade: melhor responder em algum lugar do que em nenhum.

        Mensagem sem `conversation_id` nao deveria acontecer com a API atual,
        mas o caminho existe desde antes desta fase e a generalizacao do bloco
        de despacho passa exatamente por ele.
        """
        despachante = despachos_de(".status", tmp_path, conversa=None)
        assert despachante.alvos == [None]


class TestSemConversaDeOrigemVaiAREDACAODEGRUPO:
    """WR-07: no ramo sem conversa, o destino e o grupo — entao o texto tambem.

    Para os oito comandos antigos os dois textos sao o mesmo e a escolha era
    indiferente. Para presenca era a errada das duas: o grupo recebia "Anotado.
    Voce esta na lista do Solo Boss das 22:00." — sem nick, inutil para quem le
    — e a redacao feita para o grupo era descartada.
    """

    def test_o_join_sem_conversa_manda_a_redacao_do_GRUPO(self, tmp_path):
        despachante = despachos_do_membro(".join", tmp_path, conversa=None)

        assert despachante.alvos == [None]
        texto = despachante.textos[0]
        assert "J4guar" in texto, (
            "o grupo recebeu o texto do privado: sem nick, ele nao diz a "
            "ninguem quem esta indo"
        )
        assert "Anotado" not in texto

    def test_quando_nao_ha_redacao_de_grupo_cai_no_privado(self, tmp_path):
        """`.join` repetido tem `grupo is None` — e ainda assim tem que responder."""
        registro = RegistroEmDisco(tmp_path / "agenda")
        despachos_do_membro(
            ".join", tmp_path, conversa=None, registro=registro, identificador=1
        )
        despachante = despachos_do_membro(
            ".join", tmp_path, conversa=None, registro=registro, identificador=2
        )

        assert despachante.alvos == [None]
        assert "ja esta na lista" in despachante.textos[0]

    def test_o_ramo_sem_conversa_manda_UMA_mensagem_so(self, tmp_path):
        """O defeito que este ramo sempre evitou nao pode ter voltado."""
        despachante = despachos_do_membro(".join", tmp_path, conversa=None)
        assert len(despachante.despachos) == 1


class TestAFlagDoGrupoNaoAtravessaIteracoes:
    """WR-06: `avisar_o_grupo` nunca era inicializada por volta do laco.

    Ela e atribuida dentro dos ramos e lida no bloco de despacho. Os dois ramos
    de presenca NAO a atribuem — hoje isso e inofensivo apenas porque eles
    produzem `RespostaDePresenca` e o `isinstance` curto-circuita antes da
    leitura, e nada no codigo preserva essa coincidencia. O primeiro ramo
    futuro que devolver `str` sem setar a flag herda EM SILENCIO o destino do
    comando ANTERIOR da mesma volta.

    Lido por AST porque o defeito e estrutural: nao ha entrada que o produza
    HOJE, e um teste de comportamento passaria provando nada. O que se afirma e
    a propriedade que impede o defeito de nascer.
    """

    def _corpo_do_laco(self):
        import inspect

        from l2scanner import __main__ as principal

        arvore = ast.parse(inspect.getsource(principal.atender_comandos))
        funcao = next(
            no for no in ast.walk(arvore) if isinstance(no, ast.FunctionDef)
        )
        return next(no for no in ast.walk(funcao) if isinstance(no, ast.For))

    def test_a_flag_tem_default_no_topo_de_cada_volta(self):
        laco = self._corpo_do_laco()
        atribuicoes = [
            no
            for no in laco.body
            if isinstance(no, ast.Assign)
            and any(
                getattr(alvo, "id", None) == "avisar_o_grupo" for alvo in no.targets
            )
        ]
        assert atribuicoes, (
            "`avisar_o_grupo` nao tem default por iteracao: o primeiro ramo "
            "que devolver str sem setar a flag herda o destino do comando "
            "anterior, em silencio"
        )
        assert atribuicoes[0].value.value is False, (
            "o default tem que ser False — silencio no grupo e o caminho facil"
        )

    def test_o_default_vem_ANTES_de_qualquer_ramo_que_a_use(self):
        laco = self._corpo_do_laco()
        linha_do_default = min(
            no.lineno
            for no in laco.body
            if isinstance(no, ast.Assign)
            and any(
                getattr(alvo, "id", None) == "avisar_o_grupo" for alvo in no.targets
            )
        )
        leituras = [
            no.lineno
            for no in ast.walk(laco)
            if isinstance(no, ast.Name)
            and no.id == "avisar_o_grupo"
            and isinstance(no.ctx, ast.Load)
        ]
        assert leituras, "ninguem le a flag; a prova nao prova nada"
        assert min(leituras) > linha_do_default

    def test_sem_despachante_nada_levanta(self, tmp_path):
        """Rodar sem `.env` e um modo suportado — o log continua saindo.

        `atender_comandos` nunca levanta: vigiar a party e o trabalho, ouvir
        comando e um extra. Este caso passa pelo `if not despachante` que fica
        DEPOIS do log, e a generalizacao do bloco nao pode perde-lo.
        """
        import time

        from l2scanner.__main__ import atender_comandos

        atender_comandos(
            LeitorDeUmaMensagem(".status", conversa="1"),
            RegistroEmDisco(tmp_path / "agenda"),
            eventos_classicos(),
            None,
            em(20, 30),
            time.monotonic(),
        )


# O telefone de um party-mate declarado em `[[membro]]` e em mais lugar nenhum.
#
# Os 8 digitos finais (98001122) sao deliberadamente diferentes dos do `DONO`
# (97077000): o scanner compara telefones pelo sufixo de 8, e dois numeros de
# teste que colidissem ali fariam o party-mate ser aceito como DONO — o teste
# passaria verde provando o nivel errado.
TELEFONE_DO_MEMBRO = "+5544998001122"


def despachos_do_membro(
    texto: str,
    tmp_path,
    *,
    registro=None,
    identificador: int = 4242,
    agora=None,
    nick: str = "J4guar",
    membros=None,
    conversa="1",
) -> DespachanteQueGrava:
    """Um `.join`/`.leave` vindo de um PARTY-MATE, nao do dono do scanner.

    A allowlist de dono e sobrescrita para OUTRO numero de proposito. O
    construtor do leitor falso poe o telefone do remetente tambem em
    `telefones`, e deixar assim faria o party-mate entrar pelo nivel de DONO —
    o teste ficaria verde medindo a autorizacao antiga e nao diria nada sobre
    o `[[membro]]`, que e o elo que esta fase existe para ligar.

    Nao pode ser lista VAZIA: allowlist vazia aceita qualquer um, por
    compatibilidade com quem configurava comandos so por conversa. Vazia, este
    helper provaria ainda menos.
    """
    import time

    from l2scanner.__main__ import atender_comandos
    from l2scanner.comandos import Membro

    leitor = LeitorDeUmaMensagem(
        texto,
        conversa=conversa,
        telefone=TELEFONE_DO_MEMBRO,
        membros=(
            [Membro(nick=nick, telefone=TELEFONE_DO_MEMBRO)]
            if membros is None
            else membros
        ),
        identificador=identificador,
    )
    leitor.telefones = [DONO]

    despachante = DespachanteQueGrava()
    atender_comandos(
        leitor,
        registro if registro is not None else RegistroEmDisco(tmp_path / "agenda"),
        [solo_boss()],
        despachante,
        agora if agora is not None else em(19, 0),
        time.monotonic(),
    )
    return despachante


class TestDespachoDoJoinEDoLeave:
    """Os dois ramos novos, pelo caminho que o LACO usa.

    A PROPRIEDADE NOVA DO PROJETO ESTA AQUI: pela primeira vez os dois destinos
    recebem redacoes DIFERENTES. Ate esta fase, `avisar_o_grupo = True`
    significava "mande o mesmo texto duas vezes", e era o suficiente porque
    todo comando ecoado mudava algo que o grupo inteiro ja estava vivendo. A
    lista de presenca nao: quem digitou precisa saber que CHEGOU, e o grupo
    precisa do NICK e do HORARIO — e ninguem na party quer ler "anotado, voce
    esta na lista".

    O que estes testes afirmam e a CONTAGEM e o DESTINO dos despachos, mais a
    diferenca entre os dois textos. A redacao em si e afirmada em `TestJoin`,
    `TestLeave` e `TestFormaDoTexto`, contra `presenca.py` direto — repeti-la
    aqui faria a costura quebrar em toda melhoria de frase.
    """

    def test_join_de_membro_responde_no_privado_E_anuncia_no_grupo(self, tmp_path):
        despachante = despachos_do_membro(".join", tmp_path)

        assert despachante.alvos == ["1", None], (
            "um .join que gravou tinha que responder na origem E anunciar no "
            f"grupo; os destinos foram {despachante.alvos}"
        )
        privado, grupo = despachante.textos
        assert privado != grupo, (
            "as duas redacoes sairam IGUAIS — o eco do bloco antigo continua "
            "de pe e o D-09 nao chegou ao despacho"
        )
        assert "J4guar" in grupo, "o grupo nao ficou sabendo QUEM entrou"
        assert "20:00" in grupo, "o grupo nao ficou sabendo de QUAL ocorrencia"

    def test_sem_o_bloco_membro_o_join_do_party_mate_NAO_atravessa(self, tmp_path):
        """Guarda contra prova vazia: o que deixou o `.join` passar foi o nivel
        de membro, e nao a allowlist de dono nem a falta de trava.

        O mesmo telefone, a mesma mensagem, so que sem `[[membro]]` nenhum
        configurado: tem de morrer em silencio na quinta trava. Sem este
        controle, o teste acima passaria identico num scanner que aceitasse
        comando de qualquer um.
        """
        despachante = despachos_do_membro(".join", tmp_path, membros=[])
        assert despachante.despachos == [], (
            "um telefone sem [[membro]] e fora da allowlist de dono conseguiu "
            "dar .join"
        )

    def test_join_repetido_responde_no_privado_e_CALA_no_grupo(self, tmp_path):
        """D-08. O grupo e o recurso caro desta fase.

        Sao doze ocorrencias por dia; um dedo nervoso repetindo `.join` viraria
        spam para as 4-8 pessoas do grupo, e foi por causa desse volume que o
        usuario ja desligou `avisar_no_horario` do Solo Boss.

        O MESMO registro nas duas chamadas de proposito: um registro novo a
        cada chamada apagaria a memoria que este teste existe para exercitar.
        """
        registro = RegistroEmDisco(tmp_path / "agenda")
        primeiro = despachos_do_membro(
            ".join", tmp_path, registro=registro, identificador=1
        )
        assert primeiro.alvos == ["1", None], "o primeiro .join nem entrou"

        segundo = despachos_do_membro(
            ".join", tmp_path, registro=registro, identificador=2
        )
        assert segundo.alvos == ["1"], (
            "o .join repetido tinha que responder SO no privado; os destinos "
            f"foram {segundo.alvos}"
        )

    def test_leave_de_quem_estava_na_lista_anuncia_no_grupo(self, tmp_path):
        registro = RegistroEmDisco(tmp_path / "agenda")
        despachos_do_membro(".join", tmp_path, registro=registro, identificador=1)

        saida = despachos_do_membro(
            ".leave", tmp_path, registro=registro, identificador=2
        )
        assert saida.alvos == ["1", None], (
            f"o .leave de quem estava na lista foi para {saida.alvos}"
        )
        privado, grupo = saida.textos
        assert privado != grupo, "as duas redacoes do .leave sairam IGUAIS"
        assert "J4guar" in grupo, "o grupo nao ficou sabendo QUEM saiu"

    def test_leave_de_quem_nunca_joinou_responde_so_no_privado(self, tmp_path):
        """A assimetria com o `.join` e proposital.

        Um `.leave` de quem nunca entrou quase sempre e engano de quem achou
        que tinha entrado — e anunciar no grupo a saida de alguem que nunca
        esteve la e ruido puro.
        """
        despachante = despachos_do_membro(".leave", tmp_path)
        assert despachante.alvos == ["1"], (
            f"o .leave sem entrada previa foi para {despachante.alvos}"
        )

    def test_join_de_dono_fora_do_bloco_membro_NAO_inventa_nick(self, tmp_path):
        """D-10. O `sender.name` do Chatwoot nunca vira nick de lista.

        O nivel de dono alcanca todo comando, entao o pedido CHEGA — mas sem
        `[[membro]]` nao ha nick nenhum para por na lista. Inventar um a partir
        do nome do contato poria na lista da party um "Yazalaque" que nao e
        personagem de ninguem, e a lista fechada e o que alimenta a sugestao da
        vez do loot.
        """
        despachante = despachos_de(
            ".join", tmp_path, eventos=[solo_boss()], agora=em(19, 0)
        )
        assert despachante.alvos == ["1"], (
            "um .join sem nick nao pode produzir anuncio no grupo; os destinos "
            f"foram {despachante.alvos}"
        )
        assert "Yazalaque" not in despachante.textos[0], (
            "o nome do CONTATO do Chatwoot vazou para a resposta como se fosse "
            "nick de personagem"
        )

    def test_o_ramo_novo_sem_despachante_nao_levanta(self, tmp_path):
        """Rodar sem `.env` continua sendo um modo suportado, tambem no `.join`."""
        import time

        from l2scanner.__main__ import atender_comandos
        from l2scanner.comandos import Membro

        leitor = LeitorDeUmaMensagem(
            ".join",
            conversa="1",
            telefone=TELEFONE_DO_MEMBRO,
            membros=[Membro(nick="J4guar", telefone=TELEFONE_DO_MEMBRO)],
        )
        leitor.telefones = [DONO]
        atender_comandos(
            leitor,
            RegistroEmDisco(tmp_path / "agenda"),
            [solo_boss()],
            None,
            em(19, 0),
            time.monotonic(),
        )


class TestFechamentoComOJogoFechado:
    """O `--so-agenda` tambem fecha a lista — e e ele que faz o recurso valer.

    E a MESMA razao pela qual AGEN-05 existe: quem mais precisa saber quem vai
    no boss e justamente quem nao esta online. Um fechamento que so acontecesse
    no laco principal so falaria para quem ja esta com o jogo aberto — e essa
    pessoa esta olhando a party na tela.

    DIFERENCA DELIBERADA EM RELACAO AO CONSUMO DE LOOT, que no mesmo laco e
    "SO LOG, sem WhatsApp": a lista fechada VAI para o grupo. Ela e o desfecho
    da pergunta que a chamada fez 1h50 antes, e deixa-la so no console deixaria
    a party sem a resposta. O volume nao e o mesmo problema porque zero
    confirmacoes produz zero mensagem (D-12): o piso e silencio, e nao doze
    mensagens por dia.
    """

    def _registro_com(self, tmp_path, *nicks):
        registro = RegistroEmDisco(tmp_path / "agenda")
        chave = chave_da_ocorrencia("Solo Boss", em(20, 0))
        for nick in nicks:
            registro.entrar(chave, nick)
        return registro

    def test_lista_cheia_produz_exatamente_um_despacho_no_grupo(self, tmp_path):
        from l2scanner.__main__ import _fechar_listas_de_presenca
        from l2scanner.notificador import Categoria

        despachante = DespachanteQueGrava()
        fechados = _fechar_listas_de_presenca(
            self._registro_com(tmp_path, "j4guar", "tiomad"),
            [solo_boss()],
            em(20, 0),
            (),
            despachante,
        )

        assert len(fechados) == 1
        assert len(despachante.despachos) == 1
        (texto, categoria, conversa) = despachante.despachos[0]
        assert "Solo Boss" in texto
        assert "J4guar" in texto
        assert categoria is Categoria.SEMPRE
        assert conversa is None, "a lista sai nas conversas de AVISO (T-10-17)"

    def test_lista_vazia_produz_zero_despacho_e_zero_log(self, tmp_path, caplog):
        """D-12 no laco: o boss nasce, ninguem confirmou, e o bot nao fala."""
        from l2scanner.__main__ import _fechar_listas_de_presenca

        despachante = DespachanteQueGrava()
        with caplog.at_level(logging.INFO, logger="l2scanner"):
            fechados = _fechar_listas_de_presenca(
                RegistroEmDisco(tmp_path / "agenda"),
                [solo_boss()],
                em(20, 0),
                (),
                despachante,
            )

        assert fechados == []
        assert despachante.despachos == []
        assert not [r for r in caplog.records if "Solo Boss" in r.getMessage()]

    def test_sem_despachante_o_fechamento_ainda_aparece_no_log(
        self, tmp_path, caplog
    ):
        """Quem roda sem `.env` e sem `--dry-run` nao pode perder a mensagem.

        E a mesma separacao que o laco ja faz com o encerramento de silencio:
        loga SEMPRE, despacha se houver para onde.
        """
        from l2scanner.__main__ import _fechar_listas_de_presenca

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            fechados = _fechar_listas_de_presenca(
                self._registro_com(tmp_path, "kaus"),
                [solo_boss()],
                em(20, 0),
                (),
                None,
            )

        assert len(fechados) == 1
        assert [r for r in caplog.records if "Kaus" in r.getMessage()]

    def test_os_membros_dao_a_grafia_do_config_tambem_aqui(self, tmp_path):
        """D-10 nao pode valer so no laco principal."""
        from l2scanner.__main__ import _fechar_listas_de_presenca

        class MembroFalso:
            def __init__(self, nick):
                self.nick = nick

        despachante = DespachanteQueGrava()
        _fechar_listas_de_presenca(
            self._registro_com(tmp_path, "tiomad"),
            [solo_boss()],
            em(20, 0),
            [MembroFalso("TioMad")],
            despachante,
        )

        (texto, _, _) = despachante.despachos[0]
        assert "TioMad" in texto and "Tiomad" not in texto

    def test_duas_voltas_do_laco_fecham_uma_vez_so(self, tmp_path):
        """O `fechar` E a decisao de despachar, aqui como no tick (T-10-16)."""
        from l2scanner.__main__ import _fechar_listas_de_presenca

        registro = self._registro_com(tmp_path, "kaus")
        despachante = DespachanteQueGrava()
        for minuto in (0, 1):
            _fechar_listas_de_presenca(
                registro, [solo_boss()], em(20, minuto), (), despachante
            )

        assert len(despachante.despachos) == 1

    def test_o_laco_da_agenda_chama_o_fechamento(self):
        """Lido por AST: a funcao pode existir e nunca ser chamada.

        E o modo de falha mais caro desta fase — codigo com teste verde que o
        laco nunca alcanca, exatamente o que `TestOEloDoNivelDeMembro` abaixo
        descreve sobre o nivel de membro.
        """
        arvore = ast.parse(
            (RAIZ / "l2scanner" / "__main__.py").read_text(encoding="utf-8")
        )
        laco = next(
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.FunctionDef) and no.name == "laco_da_agenda"
        )
        chamadas = [
            no
            for no in ast.walk(laco)
            if isinstance(no, ast.Call)
            and getattr(no.func, "id", None) == "_fechar_listas_de_presenca"
        ]
        assert chamadas, "laco_da_agenda nunca fecha a lista de presenca"

    def test_a_sessao_do_laco_principal_recebe_membros(self):
        """Sem isto o mapa existe, tem teste verde, e a lista sai em slug."""
        arvore = ast.parse(
            (RAIZ / "l2scanner" / "__main__.py").read_text(encoding="utf-8")
        )
        chamadas = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call) and getattr(no.func, "id", None) == "Sessao"
        ]
        assert chamadas, "ninguem constroi a Sessao"
        for chamada in chamadas:
            nomes = {palavra.arg for palavra in chamada.keywords}
            assert "membros" in nomes, (
                "a Sessao e construida sem `membros`: a lista fechada sairia "
                "com a caixa do slug mesmo com os blocos [[membro]] no config"
            )


class TestOEloDoNivelDeMembro:
    """`leitor.membros` chegando ate `comandos_novos` — o elo que o plano 10-01
    deixou pronto e ninguem consultava.

    Sem ele, `Membro`, `nick_do_membro`, `COMANDOS_DE_MEMBRO` e os blocos
    `[[membro]]` do `config.toml` existem, tem teste unitario verde, e a fase
    inteira fica MUDA para os party-mates: `autorizado_para` recebe a tupla
    vazia por default e recusa todo mundo que nao seja dono. E o modo de falha
    mais caro possivel — codigo inalcancavel que parece pronto.
    """

    def test_atender_comandos_passa_membros_para_comandos_novos(self):
        import inspect

        from l2scanner import __main__ as principal

        arvore = ast.parse(inspect.getsource(principal.atender_comandos))
        chamadas = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and getattr(no.func, "id", None) == "comandos_novos"
        ]
        assert chamadas, "atender_comandos nao chama comandos_novos"
        for chamada in chamadas:
            nomes = {palavra.arg for palavra in chamada.keywords}
            assert "membros" in nomes, (
                "comandos_novos e chamado sem `membros`: o nivel de membro "
                "existe e nunca e consultado"
            )

    @pytest.mark.parametrize("laco", ["laco_principal", "laco_da_agenda"])
    def test_os_dois_lacos_entregam_um_leitor_que_carrega_membros(self, laco):
        """As DUAS chamadas de `atender_comandos`, e nao so a do laco principal.

        `--so-agenda` e o modo de quem nao esta com o jogo aberto — e e
        exatamente quem manda `.join` pelo celular. Ligar o elo so no laco
        principal deixaria o comando funcionando na maquina de quem esta
        jogando e mudo em quem so quer entrar na lista.

        Lido por AST e nao por grep: a docstring desta fase escreve `membros`
        varias vezes, e uma busca textual daria positivo na propria
        documentacao que a restricao existe para proteger.
        """
        arvore = ast.parse(
            (RAIZ / "l2scanner" / "__main__.py").read_text(encoding="utf-8")
        )
        funcao = next(
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.FunctionDef) and no.name == laco
        )
        chamada = next(
            no
            for no in ast.walk(funcao)
            if isinstance(no, ast.Call)
            and getattr(no.func, "id", None) == "atender_comandos"
        )
        variavel = getattr(chamada.args[0], "id", None)
        assert variavel, f"{laco} passa algo que nao e um nome para atender_comandos"

        montagens = [
            no
            for no in ast.walk(funcao)
            if isinstance(no, ast.Assign)
            and any(getattr(alvo, "id", None) == variavel for alvo in no.targets)
            and isinstance(no.value, ast.Call)
            and getattr(no.value.func, "id", None) == "montar_leitor_de_comandos"
        ]
        assert montagens, (
            f"{laco} entrega a atender_comandos um `{variavel}` que nao veio de "
            "montar_leitor_de_comandos — o leitor pode nao carregar os membros"
        )
