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
import unicodedata
from datetime import datetime
from pathlib import Path

import pytest

from l2scanner.agenda import TODOS_OS_DIAS, EventoAgendado, RegistroEmDisco
from l2scanner.presenca import (
    RespostaDePresenca,
    nomes_dos_membros,
    ocorrencia_da_chamada,
    ocorrencia_recem_fechada,
    responder_join,
    responder_leave,
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
        """Um boss as 23:50 continua recem-fechado as 00:02 do dia seguinte."""
        tardio = solo_boss(horarios=((23, 50),))
        assert ocorrencia_recem_fechada(em(0, 2, dia=25), [tardio]) == (
            "Solo Boss",
            em(23, 50, dia=24),
        )

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

    def test_quem_entrou_na_lista_das_2200_sai_dela_as_2001(self, registro):
        """O caso simetrico: ha o que apagar, e e da ocorrencia certa."""
        responder_join(registro, [solo_boss()], em(20, 1), "Kaus")

        resposta = responder_leave(registro, [solo_boss()], em(20, 2), "Kaus")

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

    def test_loot_nunca_importa_presenca(self):
        """No plano 10-05 quem precisa da lista no loot a recebe por PARAMETRO."""
        importados = _modulos_importados(RAIZ / "l2scanner" / "loot.py")
        assert "presenca" not in importados

    def test_agenda_nao_importa_nenhum_dos_dois(self):
        """A agenda e a base: ela nao conhece nem loot nem presenca."""
        importados = _modulos_importados(RAIZ / "l2scanner" / "agenda.py")
        assert not ({"loot", "presenca", "comandos"} & importados)

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
    """O tempo entra por parametro nos TRES modulos, nao so no arquivo novo.

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
    """

    MODULOS = ("agenda.py", "loot.py", "presenca.py")

    @pytest.mark.parametrize("modulo", MODULOS)
    def test_nenhum_now_de_datetime_na_arvore(self, modulo):
        arvore = ast.parse((RAIZ / "l2scanner" / modulo).read_text(encoding="utf-8"))
        achados = [
            f"{getattr(no.value, 'id', None) or getattr(no.value, 'attr', '?')}.{no.attr}"
            for no in ast.walk(arvore)
            if isinstance(no, ast.Attribute)
            and no.attr in {"now", "utcnow"}
            and (getattr(no.value, "id", None) or getattr(no.value, "attr", None))
            in {"datetime", "date", "time"}
        ]
        assert not achados, f"{modulo} tem relogio proprio: {achados}"

    def test_a_prova_pega_de_verdade_um_relogio_proprio(self):
        """Guarda contra prova vazia: o detector acha o que deveria achar."""
        arvore = ast.parse("from datetime import datetime\nx = datetime.now()\n")
        achados = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Attribute) and no.attr == "now"
        ]
        assert achados, "o detector nao acharia nem um datetime.now() literal"
