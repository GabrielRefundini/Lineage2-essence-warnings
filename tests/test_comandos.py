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
    interpretar_dinamico,
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
        """Cada item e algo que qualquer um autorizado pode mandar o bot fazer.

        A lista curta nao e falta de imaginacao — e o limite do estrago
        possivel. Quando ela crescer, e para crescer de proposito.
        """
        assert set(Comando) == {
            Comando.CANCELAR_SILENCIO,
            Comando.STATUS,
            Comando.SOLO,
            Comando.PARTY,
            # O controle de loot do Solo Boss. Crescimento DE PROPOSITO:
            # designar quem pega o proximo, e consultar quanto um nick pegou.
            Comando.LOOT_DESIGNAR,
            Comando.LOOT_CONSULTA,
            # E desmarcar. O unico DESTRUTIVO da lista — entrou de proposito,
            # porque sem ele o proximo boss nao tinha como voltar a ser de
            # ninguem sem editar arquivo e reiniciar o scanner.
            Comando.LOOT_CANCELAR,
            # E corrigir um loot JA CONSUMADO. Tambem de proposito, e o de
            # maior alcance da lista: e o unico que reescreve HISTORICO, que
            # nunca e podado. O contrapeso e a mira fixa no registro mais
            # recente — nao ha sintaxe para atingir a estatistica antiga.
            Comando.LOOT_CORRIGIR,
        }

    def test_as_formas_do_modo_solo(self):
        for forma in (".solo", ".soloplay", ".SOLO"):
            assert interpretar(forma) is Comando.SOLO, forma
        for forma in (".party", ".pt", ".grupo"):
            assert interpretar(forma) is Comando.PARTY, forma

    def test_falar_de_solo_sem_ponto_nao_liga_nada(self):
        for texto in ("vou jogar solo", "solo", "party amanha"):
            assert interpretar(texto) is None, texto


class TestInterpretarDinamico:
    """Os comandos com argumento: `.loot-<nick>` e `.<nick>`.

    Superficie dinamica e superficie de ataque. Por isso o desenho e todo
    restricao: nick com charset fechado, consulta so de nick conhecido, o
    vocabulario fixo com precedencia e `.offline` excluido por nome.
    """

    def test_loot_com_hifen_designa(self):
        assert interpretar_dinamico(".loot-j4guar", frozenset()) == (
            Comando.LOOT_DESIGNAR,
            "j4guar",
        )

    def test_o_comando_e_case_insensitive_mas_o_nick_e_preservado(self):
        """`.LOOT-J4guar` designa "J4guar", nao "j4guar" — a resposta vai
        mostrar o nick como a pessoa o escreveu."""
        assert interpretar_dinamico(".LOOT-J4guar", frozenset()) == (
            Comando.LOOT_DESIGNAR,
            "J4guar",
        )

    def test_loot_em_duas_palavras_tambem_designa(self):
        assert interpretar_dinamico(".loot j4guar", frozenset()) == (
            Comando.LOOT_DESIGNAR,
            "j4guar",
        )

    def test_loot_com_hifen_e_nada_depois_CANCELA(self):
        """`.loot-` apaga a designacao — a sintaxe que o usuario escolheu.

        Antes isto morria em silencio no `_NICK_VALIDO.fullmatch("")`, e nao
        havia como deixar o proximo boss sem dono sem editar arquivo.
        """
        assert interpretar_dinamico(".loot-", frozenset()) == (
            Comando.LOOT_CANCELAR,
            "",
        )

    def test_loot_SOZINHO_continua_sendo_nada(self):
        """A trava de D-02: comando sem argumento nao pode ser destrutivo.

        Quem digita `.loot` no meio de um farm quase sempre esta PERGUNTANDO
        "quem pega o loot?", nao mandando apagar. Um `.loot` que apagasse em
        silencio seria a pior armadilha possivel nesta superficie.
        """
        assert interpretar_dinamico(".loot", frozenset()) is None

    def test_o_nick_normal_nao_virou_cancelamento(self):
        """A regressao que o ramo novo poderia causar: o cancelamento entra
        ANTES do `_NICK_VALIDO`, e um nick comum tem que passar ileso."""
        assert interpretar_dinamico(".loot-J4guar", frozenset()) == (
            Comando.LOOT_DESIGNAR,
            "J4guar",
        )

    def test_as_palavras_reservadas_tambem_cancelam(self):
        """Quem nao lembra que o hifen sozinho basta escreve por extenso.

        O preco esta pago e documentado: um personagem chamado "Cancelar" nao
        pode ser designado. Barato perto de `.loot-cancelar` designar um
        personagem que nao existe e deixar a party sem jeito de desmarcar.
        """
        for texto in (
            ".loot-cancelar",
            ".loot-ninguem",
            ".loot-nenhum",
            ".loot-limpar",
            ".LOOT-CANCELAR",  # o comando e case-insensitive
        ):
            assert interpretar_dinamico(texto, frozenset()) == (
                Comando.LOOT_CANCELAR,
                "",
            ), texto

    def test_a_palavra_reservada_vale_em_duas_palavras(self):
        """`.loot cancelar` cancela — a alternativa seria DESIGNAR um
        personagem inexistente chamado "cancelar", exatamente o acidente que
        as palavras reservadas existem para evitar."""
        assert interpretar_dinamico(".loot cancelar", frozenset()) == (
            Comando.LOOT_CANCELAR,
            "",
        )

    def test_nick_de_um_caractere_nao_designa(self):
        """`.loot-a` e quase sempre um dedo escorregado, nao uma designacao."""
        assert interpretar_dinamico(".loot-a", frozenset()) is None

    def test_nick_com_caractere_fora_do_charset_nao_designa(self):
        for texto in (".loot-j4;rm", ".loot-j4_guar", ".loot-nick!"):
            assert interpretar_dinamico(texto, frozenset()) is None, texto

    def test_consulta_so_de_nick_conhecido(self):
        """O portao central: sem ele o scanner responderia lixo a qualquer
        `.palavra` do grupo."""
        conhecidos = frozenset({"j4guar"})
        assert interpretar_dinamico(".j4guar", conhecidos) == (
            Comando.LOOT_CONSULTA,
            "j4guar",
        )
        assert interpretar_dinamico(".kaus", conhecidos) is None

    def test_consulta_atravessa_maiusculas(self):
        assert interpretar_dinamico(".J4GUAR", frozenset({"j4guar"})) == (
            Comando.LOOT_CONSULTA,
            "J4GUAR",
        )

    def test_offline_NUNCA_e_comando(self):
        """`.offline` e convencao humana do grupo — quem digita esta avisando
        gente, nao o bot. Nem estando no conjunto de nicks ele vira consulta."""
        assert interpretar_dinamico(".offline", frozenset({"offline"})) is None

    def test_o_vocabulario_fixo_tem_precedencia(self):
        """Um nick homonimo de comando jamais sombreia o comando."""
        for palavra in ("status", "cancelar", "solo", "party", "pt", "grupo"):
            conhecidos = frozenset({palavra})
            assert interpretar_dinamico(f".{palavra}", conhecidos) is None, palavra

    def test_corrigir_com_hifen_corrige(self):
        assert interpretar_dinamico(".corrigir-kaus", frozenset()) == (
            Comando.LOOT_CORRIGIR,
            "kaus",
        )

    def test_corrigir_em_duas_palavras_faz_a_MESMA_coisa(self):
        """A porta dos fundos que o `.loot cancelar` ja abriu uma vez.

        Tratar so o ramo do hifen deixaria `.corrigir kaus` morrer em silencio
        — e quem digitou acharia que corrigiu. Foi exatamente esse o bug da
        tarefa anterior, onde `.loot cancelar` DESIGNAVA um personagem
        chamado "cancelar".
        """
        assert interpretar_dinamico(".corrigir kaus", frozenset()) == (
            Comando.LOOT_CORRIGIR,
            "kaus",
        )

    def test_corrigir_e_case_insensitive_mas_o_nick_e_preservado(self):
        assert interpretar_dinamico(".CORRIGIR-Kaus", frozenset()) == (
            Comando.LOOT_CORRIGIR,
            "Kaus",
        )

    def test_corrigir_SOZINHO_nao_faz_nada(self):
        """Comando sem argumento nao pode reescrever historico.

        E o `return None` explicito do ramo tambem e o que impede `.corrigir`
        de escorregar para o ramo de consulta logo abaixo, onde
        `_NICK_VALIDO` casa a palavra "corrigir" como se fosse um nick.
        """
        assert interpretar_dinamico(".corrigir", frozenset()) is None

    def test_corrigir_nao_vira_consulta_nem_com_nick_homonimo(self):
        """A prova direta de que a porta fica fechada: mesmo existindo um
        personagem chamado "Corrigir", o comando nao vira consulta dele."""
        assert interpretar_dinamico(".corrigir", frozenset({"corrigir"})) is None

    def test_nick_invalido_nao_corrige(self):
        """O mesmo `_NICK_VALIDO` dos outros comandos, sem excecao."""
        for texto in (".corrigir-a", ".corrigir-j4;rm", ".corrigir a", ".corrigir-"):
            assert interpretar_dinamico(texto, frozenset()) is None, texto

    def test_o_comando_novo_nao_deslocou_os_ramos_de_loot(self):
        """Regressao: `.corrigir` entrou entre o ramo do `.loot` e o da
        consulta, e nenhum dos dois pode ter mudado de comportamento."""
        assert interpretar_dinamico(".loot-j4guar", frozenset()) == (
            Comando.LOOT_DESIGNAR,
            "j4guar",
        )
        assert interpretar_dinamico(".loot-", frozenset()) == (
            Comando.LOOT_CANCELAR,
            "",
        )
        assert interpretar_dinamico(".loot", frozenset()) is None

    def test_sem_prefixo_nao_e_nada(self):
        assert interpretar_dinamico("j4guar", frozenset({"j4guar"})) is None
        assert interpretar_dinamico("loot j4guar", frozenset()) is None

    def test_texto_vazio_ou_ausente(self):
        assert interpretar_dinamico(None, frozenset()) is None
        assert interpretar_dinamico("", frozenset()) is None
        assert interpretar_dinamico("   ", frozenset()) is None


class TestComandosDinamicosNasTravas:
    """As travas antigas valem INTEGRALMENTE para os comandos novos.

    `.loot-<nick>` muda estado compartilhado; se um estranho pudesse mandar,
    ele controlaria de quem e a vez do loot da party inteira.
    """

    def test_loot_designar_atravessa_com_argumento(self):
        achados = comandos_novos(
            [msg(1, ".loot-j4guar")], set(), nicks_conhecidos=frozenset()
        )
        assert len(achados) == 1
        assert achados[0].comando is Comando.LOOT_DESIGNAR
        assert achados[0].argumento == "j4guar"

    def test_consulta_atravessa_com_argumento(self):
        achados = comandos_novos(
            [msg(2, ".j4guar")], set(), nicks_conhecidos=frozenset({"j4guar"})
        )
        assert len(achados) == 1
        assert achados[0].comando is Comando.LOOT_CONSULTA
        assert achados[0].argumento == "j4guar"

    def test_nick_desconhecido_morre_em_silencio(self):
        assert comandos_novos([msg(3, ".kaus")], set()) == []

    def test_telefone_nao_autorizado_e_descartado(self):
        """A trava de allowlist vale para o comando novo."""
        meus = ["+5544997077000"]
        de_outro = [msg(4, ".loot-j4guar", autor="Hiago")]
        de_outro[0]["sender"]["phone_number"] = "+48608297919"
        assert comandos_novos(de_outro, set(), meus) == []

    def test_comando_fixo_continua_sem_argumento(self):
        """`.status` com "status" nos nicks conhecidos continua STATUS."""
        achados = comandos_novos(
            [msg(5, ".status")], set(), nicks_conhecidos=frozenset({"status"})
        )
        assert len(achados) == 1
        assert achados[0].comando is Comando.STATUS
        assert achados[0].argumento is None


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


class TestTelefoneEquivalente:
    """O nono digito brasileiro, e por que comparacao exata falharia.

    O usuario se identifica como +5544997077000. O Chatwoot registra o dono do
    grupo dele como 554497077000 — SEM o 9. Mesma pessoa, duas formas, as duas
    circulando na base do WhatsApp.

    Comparacao exata falharia em SILENCIO: o comando seria ignorado sem erro
    nenhum. Para uma trava de seguranca, esse e o pior modo de falha — parece
    que nao funciona, e ninguem sabe por que.
    """

    def test_o_caso_real_do_usuario(self):
        from l2scanner.comandos import telefone_equivalente

        assert telefone_equivalente("+5544997077000", "554497077000")

    def test_atravessa_formatacao(self):
        from l2scanner.comandos import telefone_equivalente

        for outro in (
            "+55 44 99707-7000",
            "(44) 99707-7000",
            "5544997077000",
            "44997077000",
        ):
            assert telefone_equivalente("+5544997077000", outro), outro

    def test_numero_de_outra_pessoa_nao_casa(self):
        from l2scanner.comandos import telefone_equivalente

        assert not telefone_equivalente("+5544997077000", "+48608297919")

    def test_vazio_nunca_casa(self):
        from l2scanner.comandos import telefone_equivalente

        assert not telefone_equivalente("+5544997077000", "")
        assert not telefone_equivalente(None, "+5544997077000")
        assert not telefone_equivalente(None, None)

    def test_numero_curto_exige_igualdade_completa(self):
        """Sem isso, um sufixo pequeno casaria com meio mundo."""
        from l2scanner.comandos import telefone_equivalente

        assert telefone_equivalente("123", "123")
        assert not telefone_equivalente("123", "456")


class TestSoOMeuNumeroMandaNoScanner:
    def test_com_allowlist_so_o_dono_passa(self):
        meus = ["+5544997077000"]
        do_dono = [msg(1, ".cancelar", autor="Yazalaque")]
        do_dono[0]["sender"]["phone_number"] = "554497077000"  # sem o 9
        assert len(comandos_novos(do_dono, set(), meus)) == 1

    def test_com_allowlist_um_estranho_e_ignorado(self):
        meus = ["+5544997077000"]
        de_outro = [msg(2, ".cancelar", autor="Hiago")]
        de_outro[0]["sender"]["phone_number"] = "+48608297919"
        assert comandos_novos(de_outro, set(), meus) == []

    def test_remetente_sem_telefone_e_ignorado_quando_ha_allowlist(self):
        """Sem numero nao da para afirmar que e voce."""
        assert comandos_novos([msg(3, ".cancelar")], set(), ["+5544997077000"]) == []

    def test_sem_allowlist_qualquer_um_passa(self):
        """Compatibilidade. O aviso de arranque torna isso visivel."""
        assert len(comandos_novos([msg(4, ".cancelar")], set(), [])) == 1

    def test_num_grupo_a_allowlist_de_conversa_nao_bastaria(self):
        """O cenario que motivou a trava.

        Num grupo, permitir a CONVERSA libera todo mundo que escreve nela. Só
        o telefone separa o dono dos outros doze membros.
        """
        meus = ["+5544997077000"]
        grupo = [
            dict(msg(10, ".cancelar", autor="Kaus"), sender={"name": "Kaus", "phone_number": "+5511999998888"}),
            dict(msg(11, ".cancelar", autor="Yazalaque"), sender={"name": "Yazalaque", "phone_number": "+5544997077000"}),
        ]
        achados = comandos_novos(grupo, set(), meus)
        assert [m.id for m in achados] == [11]


class TestEtiquetaComoInterruptor:
    def test_etiqueta_sozinha_ja_deixa_o_leitor_ativo(self):
        from l2scanner.comandos import LeitorDeComandos

        leitor = LeitorDeComandos(
            url="https://x.invalido", conta="1", token="t",
            conversas=[], etiqueta="scanner",
        )
        assert leitor.ativo

    def test_sem_conversa_e_sem_etiqueta_fica_inativo(self):
        from l2scanner.comandos import LeitorDeComandos

        leitor = LeitorDeComandos(
            url="https://x.invalido", conta="1", token="t", conversas=[],
        )
        assert not leitor.ativo

    def test_aberto_a_qualquer_um_quando_nao_ha_telefone(self):
        from l2scanner.comandos import LeitorDeComandos

        leitor = LeitorDeComandos(
            url="https://x.invalido", conta="1", token="t", conversas=["13"],
        )
        assert leitor.aberto_a_qualquer_um

    def test_com_telefone_deixa_de_estar_aberto(self):
        from l2scanner.comandos import LeitorDeComandos

        leitor = LeitorDeComandos(
            url="https://x.invalido", conta="1", token="t",
            conversas=["13"], telefones=["+5544997077000"],
        )
        assert not leitor.aberto_a_qualquer_um

    def test_falha_ao_listar_etiquetas_ouve_MENOS_nunca_mais(self):
        """Uma falha de rede nao pode abrir canal nenhum."""
        from l2scanner.comandos import LeitorDeComandos

        leitor = LeitorDeComandos(
            url="https://host.que.nao.existe.invalido", conta="1", token="t",
            conversas=[], etiqueta="scanner", segundos_entre_leituras=0.0,
        )
        assert leitor.ler(0.0) == []
        assert leitor.falhas >= 1


class TestAtenderComandosNaCostura:
    """O crash real de 2026-08-24 22:59, em producao.

        TypeError: '>=' not supported between 'timedelta' and 'float'

    `atender_comandos` recebia UM parametro `agora` e o usava para DOIS
    relogios incompativeis: o `datetime` de parede que a agenda entende, e os
    segundos corridos que o limitador de taxa do leitor entende.

    Os testes existentes nao pegaram porque chamavam `LeitorDeComandos.ler()`
    direto, sempre com float. O erro so existia na COSTURA — e a costura
    (`__main__.py`, 20% de cobertura) e onde TODOS os erros de integracao deste
    projeto moraram: os tres do code review, o `destacar` com um argumento, e
    este.

    Por isso estes testes chamam a funcao do jeito que o LACO chama, com os
    tipos de verdade.
    """

    def _pecas(self, tmp_path):
        from datetime import datetime

        from l2scanner.agenda import EventoAgendado, RegistroEmDisco
        from l2scanner.comandos import LeitorDeComandos

        leitor = LeitorDeComandos(
            url="https://host.que.nao.existe.invalido",
            conta="1",
            token="t",
            conversas=["1"],
            segundos_entre_leituras=0.0,
        )
        registro = RegistroEmDisco(tmp_path)
        eventos = [
            EventoAgendado(
                nome="Prime",
                horarios=((20, 0),),
                silenciar_minutos=120,
            )
        ]
        return leitor, registro, eventos, datetime(2026, 8, 24, 20, 30)

    def test_chamada_como_o_laco_chama_nao_levanta(self, tmp_path):
        """A reproducao exata do crash."""
        import time

        from l2scanner.__main__ import atender_comandos

        leitor, registro, eventos, agora = self._pecas(tmp_path)
        atender_comandos(leitor, registro, eventos, None, agora, time.monotonic())

    def test_o_relogio_de_parede_e_datetime_e_o_da_cadencia_e_float(self, tmp_path):
        """Trocar os dois de lugar tem que quebrar, e quebrar visivelmente.

        Se um dia alguem 'simplificar' juntando os parametros, este teste diz
        por que eles sao dois.
        """
        import pytest as _pytest

        from l2scanner.__main__ import atender_comandos

        leitor, registro, eventos, agora = self._pecas(tmp_path)
        # A PRIMEIRA chamada passa: `_ultima_leitura` e None e a comparacao nem
        # acontece. O crash de producao so apareceu no SEGUNDO tick — mais um
        # motivo de ter escapado, porque um teste de uma chamada so nao pega.
        atender_comandos(leitor, registro, eventos, None, agora, agora)
        with _pytest.raises(TypeError):
            atender_comandos(leitor, registro, eventos, None, agora, agora)

    def test_leitor_ausente_nao_faz_nada(self, tmp_path):
        import time

        from l2scanner.__main__ import atender_comandos

        _, registro, eventos, agora = self._pecas(tmp_path)
        atender_comandos(None, registro, eventos, None, agora, time.monotonic())

    def test_os_dois_lacos_passam_time_monotonic(self):
        """A trava contra a regressao voltar por um refactor.

        Le a fonte dos dois lacos e exige que a chamada carregue o segundo
        relogio. Foi assim que travamos o `destacar` e a ordem da agenda.
        """
        import inspect
        import re

        from l2scanner import __main__ as principal

        for nome in ("laco_principal", "laco_da_agenda"):
            fonte = inspect.getsource(getattr(principal, nome))
            # Casa ate o fecha-parenteses da PROPRIA chamada. Um `.*?` simples
            # para dentro de `time.monotonic()` e mede o argumento pela metade.
            corpo = fonte[fonte.index("atender_comandos(") :]
            chamada = re.match(r"atender_comandos\((.*?)\n\s*\)", corpo, re.S)
            assert chamada, f"{nome} nao chama atender_comandos"
            assert "time.monotonic()" in chamada.group(1), (
                f"{nome} nao passa o relogio monotonico para a cadencia"
            )


class TestRespondeOndePerguntaram:
    """Medido ao vivo: pergunta as 23:04:42 na conversa 1 (privado), resposta
    as 23:04:52 na conversa 13 (grupo). Funcionou — no lugar errado, e o
    usuario concluiu que nao tinha funcionado.

    O `Despachante` so sabia mandar para os destinos de AVISO. Ninguem
    respondia onde a pergunta chegou.
    """

    def _atender(self, tmp_path, texto, conversa="1"):
        import time
        from datetime import datetime

        from l2scanner.__main__ import atender_comandos
        from l2scanner.agenda import EventoAgendado, RegistroEmDisco
        from l2scanner.notificador import Despachante, NotificadorEmMemoria

        class LeitorFalso:
            ativo = True
            telefones: list[str] = []

            def ler(self, _):
                return [
                    {
                        "id": 4242,
                        "content": texto,
                        "message_type": 0,
                        "private": False,
                        "sender": {"name": "Yazalaque"},
                        "conversation_id": conversa,
                    }
                ]

        notificador = NotificadorEmMemoria()
        despachante = Despachante(notificador)
        eventos = [
            EventoAgendado(nome="Prime", horarios=((20, 0),), silenciar_minutos=120)
        ]
        atender_comandos(
            LeitorFalso(),
            RegistroEmDisco(tmp_path),
            eventos,
            despachante,
            datetime(2026, 8, 24, 20, 30),
            time.monotonic(),
        )
        despachante.iniciar()
        despachante.encerrar()
        return notificador.destinos

    def test_status_responde_no_privado_e_NAO_no_grupo(self, tmp_path):
        destinos = self._atender(tmp_path, ".status", conversa="1")
        assert destinos, "nao respondeu nada"
        alvos = [alvo for _, alvo in destinos]
        assert alvos == ["1"], (
            f"status deveria responder so na conversa 1; foi para {alvos}"
        )

    def test_cancelar_responde_no_privado_E_avisa_o_grupo(self, tmp_path):
        """Cancelar muda o que o GRUPO recebe — todo mundo tinha parado de ser
        avisado por causa daquele silencio."""
        destinos = self._atender(tmp_path, ".cancelar", conversa="1")
        alvos = [alvo for _, alvo in destinos]
        assert "1" in alvos, "quem pediu nao recebeu confirmacao"
        assert None in alvos, "o grupo nao foi avisado de que o silencio caiu"

    def test_sem_origem_conhecida_cai_no_grupo(self, tmp_path):
        """Compatibilidade: melhor responder em algum lugar do que em nenhum."""
        destinos = self._atender(tmp_path, ".status", conversa=None)
        assert [alvo for _, alvo in destinos] == [None]


class TestLootNaCostura:
    """Os dois comandos de loot pelo caminho que o LACO usa.

    Sem eco no grupo, de proposito: a designacao vai aparecer no aviso de
    antecedencia que ja existe ("Loot: X"), e ecoar agora seria dizer a mesma
    coisa duas vezes. A consulta e pergunta pessoal, mesmo racional do
    `.status`.
    """

    def _atender(self, tmp_path, texto, loot):
        import time
        from datetime import datetime

        from l2scanner.__main__ import atender_comandos
        from l2scanner.agenda import EventoAgendado, RegistroEmDisco
        from l2scanner.notificador import Despachante, NotificadorEmMemoria

        class LeitorFalso:
            ativo = True
            telefones: list[str] = []

            def ler(self, _):
                return [
                    {
                        "id": 999,
                        "content": texto,
                        "message_type": 0,
                        "private": False,
                        "sender": {"name": "Yazalaque"},
                        "conversation_id": "1",
                    }
                ]

        notificador = NotificadorEmMemoria()
        despachante = Despachante(notificador)
        eventos = [
            EventoAgendado(
                nome="Solo Boss",
                horarios=tuple((h, 0) for h in range(0, 24, 2)),
                avisar_no_horario=False,
            )
        ]
        atender_comandos(
            LeitorFalso(),
            RegistroEmDisco(tmp_path / "agenda"),
            eventos,
            despachante,
            datetime(2026, 8, 25, 9, 5),
            time.monotonic(),
            loot=loot,
        )
        despachante.iniciar()
        despachante.encerrar()
        return notificador.destinos

    def test_designar_responde_so_no_privado_e_grava(self, tmp_path):
        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")
        destinos = self._atender(tmp_path, ".loot-j4guar", loot)

        assert [alvo for _, alvo in destinos] == ["1"], (
            "a confirmacao tinha que sair SO na conversa de origem"
        )
        assert "J4guar" in destinos[0][0]
        assert loot.designacao() is not None

    def test_consultar_responde_so_no_privado(self, tmp_path):
        from datetime import datetime

        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")
        loot.registrar("j4guar", datetime(2026, 8, 25, 8, 0))
        destinos = self._atender(tmp_path, ".j4guar", loot)

        assert [alvo for _, alvo in destinos] == ["1"]
        assert "pegou 1 loot" in destinos[0][0]

    def test_sem_registro_de_loot_avisa_que_nao_da(self, tmp_path):
        """Mesmo padrao do _obedecer_modo sem rastreador: responder que nao
        da e melhor que calar — calar parece quebrado."""
        destinos = self._atender(tmp_path, ".loot-j4guar", None)

        # Sem `loot` nao ha nicks conhecidos, mas `.loot-<nick>` nao depende
        # do portao — o comando existe e a resposta explica a limitacao.
        assert destinos, "o comando morreu em silencio"
        assert "Nao consigo mexer no loot agora." in destinos[0][0]

    def test_cancelar_apaga_de_verdade_e_responde_so_no_privado(self, tmp_path):
        """A costura inteira do `.loot-`: parser, dispatch, disco e resposta.

        Sem eco no grupo, mesmo racional do designar: o grupo vai perceber
        pelo proprio aviso de antecedencia, que passa a sair sem "Loot:".
        """
        from datetime import datetime

        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")
        loot.designar("J4guar", datetime(2026, 8, 25, 10, 0), datetime(2026, 8, 25, 9))

        destinos = self._atender(tmp_path, ".loot-", loot)

        assert loot.designacao() is None, "o comando nao apagou nada"
        assert [alvo for _, alvo in destinos] == ["1"], (
            "a confirmacao tinha que sair SO na conversa de origem"
        )
        assert "J4guar" in destinos[0][0]

    def test_corrigir_atravessa_parser_dispatch_e_disco(self, tmp_path):
        """A costura inteira do `.corrigir-<nick>`: o loot troca de dono.

        Sem eco no grupo: corrigir historico e conserto de contabilidade entre
        quem sabe o que aconteceu, e anunciar que o loot mudou de dono
        convidaria justamente a discussao que o registro existe para encerrar.
        """
        from datetime import datetime

        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")
        loot.registrar("tiomad", datetime(2026, 8, 25, 8, 0))

        destinos = self._atender(tmp_path, ".corrigir-kaus", loot)

        assert [alvo for _, alvo in destinos] == ["1"], (
            "a confirmacao tinha que sair SO na conversa de origem"
        )
        assert "Kaus" in destinos[0][0]
        assert loot.resumo("kaus")[0] == 1, "a correcao nao chegou no disco"

    def test_cancelar_sem_nada_marcado_nao_levanta_e_responde(self, tmp_path):
        """O comando nao pode morrer calado: quem mandou merece saber que nao
        havia nada marcado, em vez de ficar na duvida se funcionou."""
        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")
        destinos = self._atender(tmp_path, ".loot-", loot)

        assert destinos, "o cancelamento morreu em silencio"
        assert "Nao havia loot marcado" in destinos[0][0]

    def test_cancelar_sem_registro_de_loot_avisa_que_nao_da(self, tmp_path):
        destinos = self._atender(tmp_path, ".loot-", None)

        assert destinos, "o comando morreu em silencio"
        assert "Nao consigo mexer no loot agora." in destinos[0][0]
