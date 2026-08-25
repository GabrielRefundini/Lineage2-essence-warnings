"""O scanner passa a OUVIR. Abrir a volta e abrir superficie de ataque.

O Chatwoot do usuario NAO e dedicado a este projeto: medido, a conta tem 22
conversas e 11 com mensagens de entrada, de CLIENTES REAIS. Uma delas, do Joao
Pedro, diz literalmente "Quero cancelar".

Um leitor ingenuo obedeceria a ele. Por isso a maior parte destes testes e
sobre o que o scanner se RECUSA a fazer.
"""

from __future__ import annotations

from l2scanner.comandos import (
    Comando,
    LeitorDeComandos,
    chave_da_mensagem,
    comandos_novos,
    interpretar,
)


def msg(id_, texto, tipo=0, autor="Yazalaque", private=False):
    return {
        "id": id_,
        "content": texto,
        "message_type": tipo,
        "private": private,
        "sender": {"name": autor},
    }


class TestInterpretar:
    def test_o_comando_com_prefixo_e_reconhecido(self):
        assert interpretar(".cancelar") is Comando.CANCELAR_SILENCIO

    def test_aceita_as_formas_que_a_pessoa_lembra(self):
        for forma in (".cancelar", ".cancelar silencio", ".silencio", ".voltar"):
            assert interpretar(forma) is Comando.CANCELAR_SILENCIO, forma

    def test_ignora_maiuscula_e_espaco_sobrando(self):
        assert interpretar("  .CANCELAR  ") is Comando.CANCELAR_SILENCIO

    def test_SEM_prefixo_nao_e_comando(self):
        """A trava central: conversar sobre a acao nao e pedir a acao."""
        for texto in (
            "cancelar",
            "vamos cancelar o silencio?",
            "quero cancelar",
            "Quero cancelar",  # a mensagem real do Joao Pedro, cliente
            "alguem cancela isso",
        ):
            assert interpretar(texto) is None, texto

    def test_texto_vazio_ou_ausente(self):
        assert interpretar(None) is None
        assert interpretar("") is None
        assert interpretar("   ") is None

    def test_prefixo_com_palavra_desconhecida_nao_faz_nada(self):
        assert interpretar(".exportar tudo") is None
        assert interpretar(".rm -rf") is None

    def test_o_vocabulario_e_fechado(self):
        """Cada item e algo que qualquer um do grupo pode mandar o bot fazer."""
        assert set(Comando) == {Comando.CANCELAR_SILENCIO, Comando.STATUS}


class TestOQueOScannerSeRecusaAObedecer:
    def test_nunca_obedece_as_proprias_mensagens(self):
        """Um comando ecoado viraria laco infinito."""
        saindo = [msg(1, ".cancelar", tipo=1)]
        assert comandos_novos(saindo, set()) == []

    def test_nunca_obedece_nota_privada_de_agente(self):
        assert comandos_novos([msg(1, ".cancelar", private=True)], set()) == []

    def test_nao_obedece_a_mesma_mensagem_duas_vezes(self):
        mensagens = [msg(42, ".cancelar")]
        primeiro = comandos_novos(mensagens, set())
        assert len(primeiro) == 1

        ja = {chave_da_mensagem(42)}
        assert comandos_novos(mensagens, ja) == []

    def test_mensagem_sem_id_e_descartada(self):
        assert comandos_novos([{"content": ".cancelar", "message_type": 0}], set()) == []

    def test_conversa_de_cliente_nao_dispara_nada(self):
        """O cenario real medido no Chatwoot do usuario."""
        conversa_real = [
            msg(1, "Ola, gostaria de automatizar meu fluxo de trabalho"),
            msg(2, "Quero cancelar"),
            msg(3, "nao"),
            msg(4, "John Snow 31/02/2001"),
        ]
        assert comandos_novos(conversa_real, set()) == []


class TestComandosNovos:
    def test_devolve_o_comando_com_autor(self):
        achados = comandos_novos([msg(7, ".cancelar", autor="Kaus")], set())
        assert len(achados) == 1
        assert achados[0].comando is Comando.CANCELAR_SILENCIO
        assert achados[0].autor == "Kaus"
        assert achados[0].id == 7

    def test_vem_em_ordem_de_id(self):
        fora_de_ordem = [msg(9, ".status"), msg(3, ".cancelar"), msg(5, ".voltar")]
        assert [m.id for m in comandos_novos(fora_de_ordem, set())] == [3, 5, 9]

    def test_mistura_real_so_deixa_passar_o_comando(self):
        lote = [
            msg(1, "Scanner ativo", tipo=1),
            msg(2, "boa noite pessoal"),
            msg(3, ".cancelar", autor="Yazalaque"),
            msg(4, "vou dormir"),
        ]
        achados = comandos_novos(lote, set())
        assert [m.id for m in achados] == [3]


class TestLeitorDeComandos:
    def _leitor(self, conversas=("13",), intervalo=20.0):
        return LeitorDeComandos(
            url="https://exemplo.invalido",
            conta="1",
            token="x",
            conversas=list(conversas),
            segundos_entre_leituras=intervalo,
        )

    def test_sem_conversa_configurada_fica_inativo(self):
        leitor = self._leitor(conversas=())
        assert not leitor.ativo
        assert leitor.ler(0.0) == []

    def test_respeita_a_cadencia(self):
        """A 1 Hz seriam 86 mil requisicoes por dia, por instancia."""
        leitor = self._leitor(intervalo=20.0)
        assert leitor.vencido(0.0)
        leitor.ler(0.0)
        assert not leitor.vencido(5.0)
        assert not leitor.vencido(19.9)
        assert leitor.vencido(20.0)

    def test_falha_de_rede_NAO_derruba_o_scanner(self):
        """Ouvir comando e extra; vigiar a party e o trabalho.

        O host nao existe, entao a chamada falha de verdade — nao ha mock aqui.
        """
        leitor = self._leitor()
        assert leitor.ler(0.0) == []
        assert leitor.falhas == 1

    def test_as_falhas_sao_contadas_para_o_resumo(self):
        leitor = self._leitor(intervalo=0.0)
        for t in range(3):
            leitor.ler(float(t))
        assert leitor.falhas == 3
