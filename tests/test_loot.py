"""O controle de loot do Solo Boss: registro duravel, consulta e designacao.

A party reveza quem fica com o loot do Solo Boss, e hoje o revezamento e
combinado de boca — ninguem lembra de quem e a vez nem quantos cada um ja
pegou. Estes testes provam as tres propriedades que transformam isso em
registro:

1. **Atomicidade entre duas instancias.** O usuario roda Yazalaque e Faerlina
   lado a lado, sobre a MESMA pasta. Quando o horario do boss passa, exatamente
   uma instancia registra o loot — a outra cala. Sem isso, cada boss viraria
   dois registros e a estatistica mentiria em dobro.

2. **Durabilidade.** O registro e arquivo em disco, um por loot, e NUNCA e
   podado — diferente dos marcadores do `.agenda/`, que somem em 3 dias.
   Estatistica de loot e para sempre.

3. **Leitura defensiva.** Um `proximo.json` meio-escrito (a outra instancia
   morreu no meio do replace) nao pode derrubar o laco — vira None, nunca
   excecao.
"""

from __future__ import annotations

import json
from datetime import datetime

from l2scanner.agenda import (
    Aviso,
    EventoAgendado,
    RegistroEmDisco,
    TipoDeAviso,
    chave_da_ocorrencia,
)
from l2scanner.loot import (
    Designacao,
    RegistroDeLoot,
    apelido,
    descrever_momento,
    eh_solo_boss,
    exibir,
    nick_para_o_aviso,
    responder_atribuicao,
    responder_cancelamento,
    responder_consulta,
    responder_correcao,
    responder_designacao,
    sugerir_a_vez,
)
from l2scanner.presenca import fechar_ocorrencias, texto_de_fechamento

SEGUNDA = datetime(2026, 8, 25)


def em(hora, minuto, dia=25):
    return datetime(2026, 8, dia, hora, minuto)


class TestRegistroAtomico:
    def test_o_mesmo_loot_so_registra_uma_vez(self, tmp_path):
        """Duas tentativas sobre o mesmo boss: a primeira vence, a segunda cala.

        E o O_CREAT|O_EXCL fazendo o papel de lock — sem lock. Se as duas
        devolvessem True, as duas instancias do usuario logariam o mesmo loot
        e a contagem do `.j4guar` sairia dobrada.
        """
        registro = RegistroDeLoot(tmp_path)
        alvo = em(10, 0)

        assert registro.registrar("J4guar", alvo) is True
        assert registro.registrar("J4guar", alvo) is False

        arquivos = [p.name for p in tmp_path.iterdir() if p.name.startswith("pegou_")]
        assert len(arquivos) == 1

    def test_bosses_diferentes_sao_registros_diferentes(self, tmp_path):
        registro = RegistroDeLoot(tmp_path)
        assert registro.registrar("J4guar", em(10, 0))
        assert registro.registrar("J4guar", em(12, 0))
        assert registro.resumo("J4guar")[0] == 2

    def test_nome_malformado_na_pasta_e_pulado_sem_levantar(self, tmp_path):
        """Um arquivo estranho na pasta nao pode derrubar a leitura.

        A pasta e compartilhada e duravel; qualquer lixo que caia nela tem que
        ser ignorado, nunca virar excecao no meio do farm.
        """
        registro = RegistroDeLoot(tmp_path)
        (tmp_path / "pegou_lixo").touch()
        (tmp_path / "pegou_2026-99-99-9999_x").touch()
        registro.registrar("Kaus", em(10, 0))

        assert len(registro.registros()) == 1


class TestCorridaDeDuasInstancias:
    def test_exatamente_uma_instancia_consome(self, tmp_path):
        """As duas instancias do usuario, mesma pasta, mesma designacao vencida.

        Uma devolve a Designacao (e ela que loga); a outra devolve None. Um
        unico `pegou_*` existe, e `proximo.json` sumiu nas duas visoes — o
        aviso do boss seguinte nao pode herdar a designacao consumida.
        """
        a = RegistroDeLoot(tmp_path)
        b = RegistroDeLoot(tmp_path)
        alvo = em(10, 0)
        a.designar("J4guar", alvo, em(9, 5))

        resultados = [a.consumir(em(10, 0)), b.consumir(em(10, 0))]

        vencedores = [r for r in resultados if r is not None]
        assert len(vencedores) == 1
        assert vencedores[0].alvo == alvo
        pegou = [p for p in tmp_path.iterdir() if p.name.startswith("pegou_")]
        assert len(pegou) == 1
        assert a.designacao() is None
        assert b.designacao() is None

    def test_a_outra_instancia_ja_tinha_registrado(self, tmp_path):
        """O pegou_* ja existe mas o proximo.json ficou para tras.

        Acontece quando a outra instancia registrou e morreu antes de apagar o
        json. O certo e limpar a designacao e calar — devolver a Designacao
        aqui faria o loot ser logado duas vezes.
        """
        registro = RegistroDeLoot(tmp_path)
        alvo = em(10, 0)
        registro.designar("J4guar", alvo, em(9, 5))
        registro.registrar("J4guar", alvo)  # a outra instancia venceu

        assert registro.consumir(em(10, 0)) is None
        assert registro.designacao() is None

    def test_falha_de_disco_MANTEM_a_designacao(self, tmp_path, monkeypatch):
        """Disco falhou: nao registrou, entao nao pode apagar a designacao.

        O `marcar` do RegistroEmDisco colapsa falha em True porque aviso
        perdido e pior que duplicado. Aqui e o contrario — registro perdido em
        silencio e estatistica errada para sempre. A designacao fica, e o
        proximo tick tenta de novo.
        """
        registro = RegistroDeLoot(tmp_path)
        alvo = em(10, 0)
        registro.designar("J4guar", alvo, em(9, 5))
        monkeypatch.setattr(registro, "_criar", lambda nome: "falhou")

        assert registro.consumir(em(10, 0)) is None
        assert registro.designacao() is not None


class TestConsumo:
    def test_antes_do_alvo_nao_registra_nada(self, tmp_path):
        registro = RegistroDeLoot(tmp_path)
        registro.designar("J4guar", em(10, 0), em(9, 5))

        assert registro.consumir(em(9, 59)) is None
        assert registro.designacao() is not None
        assert registro.registros() == []

    def test_no_alvo_em_diante_registra_e_apaga(self, tmp_path):
        registro = RegistroDeLoot(tmp_path)
        registro.designar("J4guar", em(10, 0), em(9, 5))

        consumida = registro.consumir(em(10, 0))

        assert consumida is not None
        assert consumida.nick == "J4guar"
        assert registro.designacao() is None
        assert registro.resumo("j4guar") == (1, em(10, 0))

    def test_consumo_atrasado_registra_com_o_horario_do_boss(self, tmp_path):
        """As duas instancias ficaram desligadas e so voltaram as 13:07.

        O registro tem que dizer QUAL boss foi — o das 10:00 — e nao a hora em
        que o scanner acordou. Senao o `.j4guar` responderia um horario em que
        boss nenhum nasceu.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.designar("J4guar", em(10, 0), em(9, 5))

        consumida = registro.consumir(em(13, 7))

        assert consumida is not None
        assert registro.resumo("J4guar") == (1, em(10, 0))

    def test_sem_designacao_nao_faz_nada(self, tmp_path):
        assert RegistroDeLoot(tmp_path).consumir(em(10, 0)) is None


class TestResumo:
    def test_conta_e_acha_o_ultimo_sem_ligar_para_maiuscula(self, tmp_path):
        """`.J4GUAR` e `.j4guar` sao a mesma pessoa — o slug decide."""
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("j4guar", em(10, 0, dia=23))
        registro.registrar("J4guar", em(14, 0, dia=24))
        registro.registrar("j4guar", em(10, 0, dia=25))
        registro.registrar("Kaus", em(12, 0, dia=25))

        assert registro.resumo("J4GUAR") == (3, em(10, 0, dia=25))

    def test_nick_sem_registro_e_zero(self, tmp_path):
        assert RegistroDeLoot(tmp_path).resumo("TioMad") == (0, None)


class TestNicksConhecidos:
    def test_comeca_vazio(self, tmp_path):
        assert RegistroDeLoot(tmp_path).nicks_conhecidos() == frozenset()

    def test_designar_torna_o_nick_conhecido_para_sempre(self, tmp_path):
        """E o portao do `.<nick>`: sem ele o scanner responderia a qualquer
        `.palavra` do grupo. Designar uma vez basta — mesmo depois do consumo,
        o marcador nick_* fica."""
        registro = RegistroDeLoot(tmp_path)
        registro.designar("J4guar", em(10, 0), em(9, 5))
        assert "j4guar" in registro.nicks_conhecidos()

        registro.consumir(em(10, 0))
        assert "j4guar" in registro.nicks_conhecidos()

    def test_registrar_direto_tambem_torna_conhecido(self, tmp_path):
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("Kaus", em(10, 0))
        assert "kaus" in registro.nicks_conhecidos()


class TestSugerirAVez:
    """Entre quem confirmou presenca, de quem deveria ser a vez do proximo loot.

    A funcao SUGERE e nao manda (D-13). Ela nao grava, nao apaga e nao tem
    efeito nenhum na pasta sem poda — e por isso que ela pode existir dentro do
    `loot.py` sem colocar meses de estatistica em risco.
    """

    def _com_loots(self, pasta, **quantos):
        """Monta o estado pelo METODO PUBLICO, e nao escrevendo arquivo a mao.

        Mesmo idioma de `TestResumo` e `TestNicksConhecidos`: se um dia o nome
        do arquivo mudar, estes testes continuam valendo por serem sobre
        comportamento e nao sobre formato.
        """
        registro = RegistroDeLoot(pasta)
        passo = 0
        for nick, total in quantos.items():
            for _ in range(total):
                registro.registrar(
                    nick, em((passo * 2) % 24, 0, dia=25 + (passo * 2) // 24)
                )
                passo += 1
        return registro

    def test_escolhe_quem_pegou_menos(self, tmp_path):
        """Tres presentes com 0, 2 e 5 loots: a vez e de quem tem 0."""
        registro = self._com_loots(tmp_path, kaus=2, j4guar=5)

        assert sugerir_a_vez(
            registro, frozenset({"tiomad", "kaus", "j4guar"})
        ) == ("tiomad", 0)

    def test_empate_no_total_desempata_pelo_ultimo_mais_antigo(self, tmp_path):
        """Um loot cada: vai quem pegou o dele ha mais tempo.

        Sem este nivel o desempate cairia direto no alfabeto, e o `Kaus`
        pegaria duas vezes seguidas enquanto o `TioMad` do mesmo total
        esperaria — que e exatamente o rodizio quebrado que a party quer
        evitar.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("tiomad", em(10, 0, dia=23))
        registro.registrar("kaus", em(10, 0, dia=25))

        assert sugerir_a_vez(registro, frozenset({"tiomad", "kaus"})) == (
            "tiomad",
            1,
        )

    def test_empate_total_desempata_pelo_alfabeto_e_e_ESTAVEL(self, tmp_path):
        """T-10-19: duas instancias, duas chamadas, o MESMO nome.

        O usuario roda Yazalaque e Faerlina lado a lado. Uma sugestao que
        variasse por instancia transformaria a ajuda em discussao — e e a
        mesma razao pela qual `encaixar_na_agenda` desempata por regra fixa e
        nao pelo que a pasta devolver primeiro.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("tiomad", em(10, 0))
        registro.registrar("kaus", em(10, 0))

        presentes = frozenset({"tiomad", "kaus"})
        primeira = sugerir_a_vez(registro, presentes)
        segunda = sugerir_a_vez(RegistroDeLoot(tmp_path), presentes)

        assert primeira == ("kaus", 1)
        assert primeira == segunda

    def test_presentes_vazio_devolve_None(self, tmp_path):
        """Uma lista vazia nao tem opiniao sobre de quem e a vez."""
        registro = self._com_loots(tmp_path, kaus=2)
        assert sugerir_a_vez(registro, frozenset()) is None

    def test_quem_nunca_pegou_ganha_de_quem_ja_pegou(self, tmp_path):
        registro = self._com_loots(tmp_path, kaus=1)
        assert sugerir_a_vez(registro, frozenset({"kaus", "novato"})) == (
            "novato",
            0,
        )

    def test_slug_que_nao_existe_na_pasta_e_zero_sem_levantar(self, tmp_path):
        """O primeiro boss de alguem e o caso NORMAL, e nao um erro.

        A lista de presenca mora no `.agenda/` e o `.loot/` pode nunca ter
        visto aquele nick. Levantar aqui calaria a mensagem de fechamento
        inteira — a party perderia a lista por causa de um novato.
        """
        registro = RegistroDeLoot(tmp_path)
        assert sugerir_a_vez(registro, frozenset({"desconhecido"})) == (
            "desconhecido",
            0,
        )

    def test_ninguem_de_fora_da_lista_e_sugerido(self, tmp_path):
        """O `fantasma` tem zero loots e mesmo assim nao pode ser nomeado.

        E o coracao do recurso: a sugestao sai de DENTRO de quem confirmou.
        """
        registro = self._com_loots(tmp_path, kaus=3)
        registro.registrar("fantasma", em(10, 0))

        escolhido = sugerir_a_vez(registro, frozenset({"kaus"}))

        assert escolhido == ("kaus", 3)

    def test_devolve_o_total_junto_com_o_slug(self, tmp_path):
        """O total entra na mensagem: sugerir sem dizer por que nao convence."""
        registro = self._com_loots(tmp_path, kaus=2)
        assert sugerir_a_vez(registro, frozenset({"kaus"})) == ("kaus", 2)

    def test_nao_escreve_NADA_na_pasta_sem_poda(self, tmp_path):
        """T-10-08, afirmado por estado e nao por leitura de codigo.

        O `.loot/` nunca e podado e nao tem backup. Esta fase inteira
        atravessa a pasta em modo somente leitura, e a unica prova que
        envelhece bem e comparar o conteudo antes e depois.
        """
        registro = self._com_loots(tmp_path, kaus=2, j4guar=1)
        antes = sorted(p.name for p in tmp_path.iterdir())

        sugerir_a_vez(registro, frozenset({"kaus", "j4guar", "tiomad"}))

        assert sorted(p.name for p in tmp_path.iterdir()) == antes

    def test_maiuscula_no_presente_nao_cria_pessoa_nova(self, tmp_path):
        """A lista guarda slug, mas se um dia chegar `Kaus` ele e o mesmo."""
        registro = self._com_loots(tmp_path, kaus=2)
        assert sugerir_a_vez(registro, frozenset({"Kaus"})) == ("kaus", 2)


class TestNenhumTipoDeArquivoNovoNaPastaDeLoot:
    """O ciclo inteiro da fase, e a pasta sem poda sai como entrou (T-10-08).

    Este e o teste mais importante do plano e o mais chato de escrever, e as
    duas coisas tem a mesma causa: ele nao afirma um retorno, afirma um ESTADO.
    Um `sugerir_a_vez` que gravasse um cache, um contador de sugestoes ou um
    marcador de "ja sugeri este boss" passaria em todos os testes acima e
    criaria, na pasta que nunca e podada e nao tem backup, um tipo de arquivo
    que nenhum comando alcanca depois.
    """

    FAMILIAS_DE_HOJE = frozenset({"pegou_", "nick_", "proximo.json"})
    SOLO = EventoAgendado(
        nome="Solo Boss",
        horarios=tuple((h, 0) for h in range(0, 24, 2)),
        avisar_no_horario=False,
        chamar_minutos_antes=110,
    )

    def _familia(self, nome: str) -> str:
        for prefixo in sorted(self.FAMILIAS_DE_HOJE):
            if nome.startswith(prefixo):
                return prefixo
        return f"DESCONHECIDA:{nome}"

    def test_o_ciclo_completo_nao_inventa_tipo_de_arquivo(self, tmp_path):
        """Designar, consumir, encher a lista, fechar e sugerir."""
        pasta_loot = tmp_path / "loot"
        pasta_agenda = tmp_path / "agenda"
        loot = RegistroDeLoot(pasta_loot)
        agenda = RegistroEmDisco(pasta_agenda)
        alvo = em(20, 0)
        chave = chave_da_ocorrencia("Solo Boss", alvo)

        loot.designar("Kaus", alvo, em(18, 10))
        loot.consumir(em(20, 0))
        for nick in ("kaus", "j4guar", "tiomad"):
            agenda.entrar(chave, nick)

        fechados = fechar_ocorrencias(agenda, [self.SOLO], em(20, 1))
        assert len(fechados) == 1
        sugestao = sugerir_a_vez(loot, frozenset(fechados[0].nicks))
        assert sugestao is not None
        texto_de_fechamento(fechados[0], None, sugestao)

        familias = {self._familia(p.name) for p in pasta_loot.iterdir()}
        assert familias <= self.FAMILIAS_DE_HOJE, familias

    def test_a_prova_pega_de_verdade_uma_familia_nova(self, tmp_path):
        """Guarda contra prova vazia: o classificador acha o que deveria."""
        pasta_loot = tmp_path / "loot"
        RegistroDeLoot(pasta_loot)
        (pasta_loot / "sugestao_2026-08-25-2000").touch()

        familias = {self._familia(p.name) for p in pasta_loot.iterdir()}

        assert not familias <= self.FAMILIAS_DE_HOJE


class TestDesignacao:
    def test_json_corrompido_vira_None_sem_levantar(self, tmp_path):
        """Um arquivo meio-escrito nao pode derrubar o laco.

        A outra instancia pode morrer no meio da escrita; o pior aceitavel e
        perder a designacao, nunca perder o scanner.
        """
        registro = RegistroDeLoot(tmp_path)
        for lixo in ("nao e json", '{"nick": "J4g', '{"nick": 42}', "{}"):
            (tmp_path / "proximo.json").write_text(lixo, encoding="utf-8")
            assert registro.designacao() is None, lixo

    def test_json_com_data_invalida_vira_None(self, tmp_path):
        registro = RegistroDeLoot(tmp_path)
        (tmp_path / "proximo.json").write_text(
            json.dumps({"nick": "J4guar", "alvo": "ontem", "designado_em": "x"}),
            encoding="utf-8",
        )
        assert registro.designacao() is None

    def test_a_ultima_designacao_vence(self, tmp_path):
        """Designar j4guar e depois kaus para o mesmo boss: vale o kaus.

        A ultima palavra vence de proposito — e como a party corrige um
        `.loot-` mandado errado, sem precisar de comando de desfazer.
        """
        registro = RegistroDeLoot(tmp_path)
        alvo = em(10, 0)
        registro.designar("j4guar", alvo, em(9, 0))
        registro.designar("kaus", alvo, em(9, 5))

        atual = registro.designacao()
        assert atual is not None
        assert atual.nick == "kaus"
        assert atual.alvo == alvo


class TestNickParaOAviso:
    def _aviso(self, evento="Solo Boss", tipo=TipoDeAviso.ANTES, alvo=None):
        alvo = alvo or em(10, 0)
        return Aviso(evento=evento, tipo=tipo, alvo=alvo, devido_em=em(9, 50))

    def _designacao(self, alvo=None):
        return Designacao(
            nick="j4guar", alvo=alvo or em(10, 0), designado_em=em(9, 5)
        )

    def test_antecedencia_do_boss_designado_ganha_o_nome(self):
        assert nick_para_o_aviso(self._aviso(), self._designacao()) == "J4guar"

    def test_aviso_AGORA_nunca_ganha(self):
        """So a antecedencia carrega o loot, por decisao do usuario."""
        aviso = self._aviso(tipo=TipoDeAviso.AGORA)
        assert nick_para_o_aviso(aviso, self._designacao()) is None

    def test_TvT_nunca_ganha(self):
        aviso = self._aviso(evento="TvT")
        assert nick_para_o_aviso(aviso, self._designacao()) is None

    def test_alvo_de_outra_ocorrencia_nao_vaza(self):
        """A designacao das 10:00 nao pode aparecer no aviso do boss das 12:00.

        E o que acontece quando ninguem consome a tempo: a comparacao de alvo
        segura o nome no boss certo em vez de deixa-lo migrar.
        """
        aviso = self._aviso(alvo=em(12, 0))
        assert nick_para_o_aviso(aviso, self._designacao(alvo=em(10, 0))) is None

    def test_sem_designacao_nao_ha_nome(self):
        assert nick_para_o_aviso(self._aviso(), None) is None


class TestEhSoloBoss:
    def test_as_grafias_que_o_usuario_pode_ter_no_config(self):
        for nome in ("Solo Boss", "solo boss", "SoloBoss", "SOLO-BOSS", "solo_boss"):
            assert eh_solo_boss(nome), nome

    def test_outros_eventos_nao_sao(self):
        for nome in ("TvT", "Prime", "Solo"):
            assert not eh_solo_boss(nome), nome


class TestNormalizacao:
    def test_apelido_e_o_mesmo_idioma_de_slug_da_agenda(self):
        assert apelido("J4guar") == "j4guar"
        assert apelido("  Tio Mad  ") == "tio-mad"

    def test_exibir_levanta_a_primeira_letra(self):
        """O `.loot-j4guar` chega minusculo e a resposta nao pode parecer
        descuidada."""
        assert exibir("j4guar") == "J4guar"
        assert exibir("kaus") == "Kaus"
        assert exibir("") == ""


class TestDescreverMomento:
    def test_mesmo_dia(self):
        assert descrever_momento(em(10, 0), em(13, 7)) == "hoje as 10:00"

    def test_vespera(self):
        assert descrever_momento(em(22, 0, dia=24), em(9, 0, dia=25)) == (
            "ontem as 22:00"
        )

    def test_mais_antigo(self):
        assert descrever_momento(em(14, 0, dia=23), em(9, 0, dia=25)) == (
            "em 23/08 as 14:00"
        )


class TestResponderConsulta:
    def test_com_varios_loots(self, tmp_path):
        registro = RegistroDeLoot(tmp_path)
        for dia, hora in ((23, 10), (23, 12), (23, 14), (24, 10), (24, 12), (24, 14)):
            registro.registrar("J4guar", em(hora, 0, dia=dia))
        registro.registrar("J4guar", em(10, 0, dia=25))

        assert responder_consulta(registro, "j4guar", em(13, 7)) == (
            "J4guar pegou 7 loots de Solo Boss. Ultimo: hoje as 10:00."
        )

    def test_um_loot_e_singular(self, tmp_path):
        """"1 loots" na resposta pareceria bot quebrado."""
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("Kaus", em(10, 0))
        resposta = responder_consulta(registro, "kaus", em(13, 7))
        assert "pegou 1 loot de Solo Boss" in resposta
        assert "loots" not in resposta

    def test_sem_nenhum_loot(self, tmp_path):
        assert responder_consulta(RegistroDeLoot(tmp_path), "j4guar", em(13, 7)) == (
            "J4guar ainda nao pegou nenhum loot de Solo Boss."
        )

    def test_designado_corrente_ganha_o_lembrete(self, tmp_path):
        """Quem consulta o proprio designado merece saber que a vez e dele."""
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("J4guar", em(10, 0))
        registro.designar("J4guar", em(12, 0), em(10, 30))

        resposta = responder_consulta(registro, "j4guar", em(10, 45))
        assert resposta.endswith("O proximo e dele.")

    def test_designado_de_outro_nick_nao_contamina(self, tmp_path):
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("J4guar", em(10, 0))
        registro.designar("Kaus", em(12, 0), em(10, 30))

        assert "proximo" not in responder_consulta(registro, "j4guar", em(10, 45))


class TestResponderDesignacao:
    SOLO = EventoAgendado(
        nome="Solo Boss",
        horarios=tuple((h, 0) for h in range(0, 24, 2)),
        avisar_no_horario=False,
    )

    def test_designa_para_a_proxima_ocorrencia(self, tmp_path):
        registro = RegistroDeLoot(tmp_path)

        resposta = responder_designacao(
            registro, [self.SOLO], em(9, 5), "j4guar"
        )

        assert resposta == "J4guar pega o loot do proximo Solo Boss, as 10:00."
        atual = registro.designacao()
        assert atual is not None
        assert atual.alvo == em(10, 0)

    def test_substituir_menciona_o_substituido(self, tmp_path):
        """A troca de vez tem que ser visivel para quem perdeu a vez."""
        registro = RegistroDeLoot(tmp_path)
        responder_designacao(registro, [self.SOLO], em(9, 0), "kaus")

        resposta = responder_designacao(registro, [self.SOLO], em(9, 5), "j4guar")

        assert "(Era do Kaus.)" in resposta
        assert registro.designacao().nick == "j4guar"

    def test_designacao_velha_de_outro_boss_nao_e_mencionada(self, tmp_path):
        """A designacao das 10:00 que ninguem consumiu nao 'era' de ninguem
        para o boss das 12:00 — mencionar confundiria a party."""
        registro = RegistroDeLoot(tmp_path)
        registro.designar("kaus", em(10, 0), em(9, 0))

        resposta = responder_designacao(registro, [self.SOLO], em(10, 30), "j4guar")

        assert "Era do" not in resposta
        assert registro.designacao().alvo == em(12, 0)

    def test_o_mesmo_nick_de_novo_nao_menciona_nada(self, tmp_path):
        registro = RegistroDeLoot(tmp_path)
        responder_designacao(registro, [self.SOLO], em(9, 0), "j4guar")
        resposta = responder_designacao(registro, [self.SOLO], em(9, 5), "j4guar")
        assert "Era do" not in resposta

    def test_agenda_sem_solo_boss_nao_grava_nada(self, tmp_path):
        registro = RegistroDeLoot(tmp_path)
        tvt = EventoAgendado(nome="TvT", horarios=((21, 50),))

        resposta = responder_designacao(registro, [tvt], em(9, 5), "j4guar")

        assert resposta == (
            "Nao achei o Solo Boss na agenda do config.toml — "
            "nao da para marcar o loot."
        )
        assert registro.designacao() is None
        assert registro.nicks_conhecidos() == frozenset()

    def test_solo_boss_sem_ocorrencia_futura_tambem_avisa(self, tmp_path):
        """Evento existe mas nunca acontece (dias vazios): mesma mensagem de
        erro, nada gravado — melhor que gravar uma designacao sem alvo."""
        registro = RegistroDeLoot(tmp_path)
        nunca = EventoAgendado(
            nome="Solo Boss", horarios=((10, 0),), dias=frozenset()
        )

        resposta = responder_designacao(registro, [nunca], em(9, 5), "j4guar")

        assert "Nao achei o Solo Boss" in resposta
        assert registro.designacao() is None


class TestCancelamento:
    """Apagar a designacao: o `.loot-` que deixa o proximo boss sem dono.

    Designar e trocar ja existiam; o que faltava era voltar ao estado "sem
    dono" sem editar arquivo e sem reiniciar o scanner. Duas propriedades
    mandam aqui: cancelar toca SO a vez (nunca a estatistica), e cancelar e
    idempotente (as duas instancias do usuario dividem a mesma pasta).
    """

    SOLO = EventoAgendado(
        nome="Solo Boss",
        horarios=tuple((h, 0) for h in range(0, 24, 2)),
        avisar_no_horario=False,
    )

    def test_cancelar_devolve_a_anterior_e_some_com_a_designacao(self, tmp_path):
        registro = RegistroDeLoot(tmp_path)
        registro.designar("J4guar", em(10, 0), em(9, 0))

        anterior = registro.cancelar()

        assert anterior is not None
        assert anterior.nick == "J4guar"
        assert anterior.alvo == em(10, 0)
        assert registro.designacao() is None, "a designacao nao foi apagada"

    def test_cancelar_nao_toca_no_historico(self, tmp_path):
        """Cancelar e sobre a VEZ, nunca sobre a estatistica.

        Apagar os `pegou_*` junto destruiria o registro que o `.<nick>`
        consulta — meses de loot indo embora num comando de sete letras.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.designar("J4guar", em(10, 0), em(9, 0))
        registro.registrar("J4guar", em(8, 0))

        registro.cancelar()

        total, ultimo = registro.resumo("J4guar")
        assert total == 1 and ultimo == em(8, 0)
        assert "j4guar" in registro.nicks_conhecidos()

    def test_responder_cancelamento_diz_de_quem_era_e_de_qual_boss(self, tmp_path):
        """A resposta tem que nomear os dois: quem perdeu a vez e qual boss.

        "Cancelado" sozinho obrigaria a pessoa a lembrar o que estava marcado
        — exatamente o que o registro existe para nao exigir.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.designar("TioMad", em(10, 0), em(9, 0))

        resposta = responder_cancelamento(registro, [self.SOLO], em(9, 5))

        assert "TioMad" in resposta
        assert "10:00" in resposta
        assert registro.designacao() is None

    def test_cancelar_duas_vezes_nao_levanta(self, tmp_path):
        """A idempotencia entre as duas instancias do usuario.

        Elas dividem a mesma pasta: a segunda a mandar encontra o
        `proximo.json` ja apagado, e levantar ali transformaria um comando
        inofensivo em erro no meio do farm.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.designar("J4guar", em(10, 0), em(9, 0))

        assert registro.cancelar() is not None
        assert registro.cancelar() is None

    def test_cancelar_sem_designacao_responde_com_honestidade(self, tmp_path):
        """Sem nada marcado a resposta corrige a expectativa e nomeia o
        proximo boss — e o que faz o parametro de tempo ganhar o lugar dele."""
        registro = RegistroDeLoot(tmp_path)

        resposta = responder_cancelamento(registro, [self.SOLO], em(9, 5))

        assert "Nao havia loot marcado" in resposta
        assert "10:00" in resposta

    def test_sem_solo_boss_na_agenda_o_cancelamento_ainda_acontece(self, tmp_path):
        """A assimetria contra `responder_designacao`: GRAVAR depende da
        agenda ter um alvo, APAGAR nunca pode depender disso.

        Se dependesse, um config.toml quebrado prenderia a designacao
        corrente para sempre, sem jeito de solta-la pelo WhatsApp.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.designar("Kaus", em(10, 0), em(9, 0))
        tvt = EventoAgendado(nome="TvT", horarios=((21, 50),))

        resposta = responder_cancelamento(registro, [tvt], em(9, 5))

        assert registro.designacao() is None, "o config quebrado prendeu a vez"
        assert "Kaus" in resposta

    def test_depois_de_cancelar_a_designacao_nova_nao_menciona_ninguem(
        self, tmp_path
    ):
        """O cancelamento apaga tambem do TEXTO: sem ele, a proxima
        designacao ainda diria "(Era do Kaus.)" e a party leria uma troca
        onde houve um recomeco.

        A TROCA em si continua coberta por
        `TestResponderDesignacao::test_substituir_menciona_o_substituido`,
        que prova o "(Era do X.)" com as duas designacoes seguidas.
        """
        registro = RegistroDeLoot(tmp_path)
        responder_designacao(registro, [self.SOLO], em(9, 0), "kaus")
        responder_cancelamento(registro, [self.SOLO], em(9, 2))

        resposta = responder_designacao(registro, [self.SOLO], em(9, 5), "j4guar")

        assert "Era do" not in resposta
        assert registro.designacao().nick == "j4guar"


class TestCorrecao:
    """Trocar o dono de um loot JA CONSUMADO: o `.corrigir-<nick>`.

    O caso real: o boss das 10:00 passou, a designacao era do TioMad, o
    `consumir()` gravou `pegou_..._tiomad`, mas quem pegou foi o Kaus. Antes
    disto a unica saida era renomear o arquivo a mao no Explorer.

    Cancelar e sobre a VEZ; corrigir e sobre o HISTORICO. Sao coisas
    diferentes de proposito, e a propriedade que manda aqui e uma so: o dono
    de um loot pode mudar, o loot nunca some.
    """

    SOLO = EventoAgendado(
        nome="Solo Boss",
        horarios=tuple((h, 0) for h in range(0, 24, 2)),
        avisar_no_horario=False,
    )

    def test_a_troca_aparece_nos_DOIS_lados(self, tmp_path):
        """O antigo perde um loot e o novo ganha um, na mesma chamada.

        Uma correcao que so somasse no novo (ou so subtraisse do antigo)
        deixaria a estatistica mentindo de um dos dois lados — e e justamente
        pelo `.<nick>` que a party confere se a correcao pegou.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("TioMad", em(10, 0))

        resposta = responder_correcao(registro, [self.SOLO], em(10, 30), "Kaus")

        assert registro.resumo("TioMad") == (0, None), "o antigo continuou com o loot"
        assert registro.resumo("Kaus") == (1, em(10, 0)), "o novo nao recebeu o loot"
        assert len(registro.registros()) == 1, "o total de loots mudou"
        # O dono ANTIGO sai slug-cased ("Tiomad") porque o nome do arquivo e o
        # unico registro que existe dele — limitacao aceita e documentada.
        assert "Tiomad" in resposta
        assert "Kaus" in resposta
        assert "10:00" in resposta

    def test_corrigir_para_o_MESMO_apelido_nao_apaga_nada(self, tmp_path):
        """A guarda critica: mesmo apelido, caixa diferente, nada muda.

        `apelido("TIOMAD") == apelido("TioMad")`, entao os dois geram o MESMO
        nome de arquivo: o `_criar` devolveria "ja_existia" e o passo de
        apagar destruiria o unico registro que existia. Sem esta guarda o
        caminho de sucesso apaga o arquivo que ele acabou de nao criar.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("TioMad", em(10, 0))

        correcao = registro.corrigir("TIOMAD")

        assert correcao.estado == "mesmo_dono"
        assert registro.resumo("TioMad") == (1, em(10, 0)), "a guarda apagou o loot"
        assert len(registro.registros()) == 1

    def test_so_o_registro_MAIS_RECENTE_e_tocado(self, tmp_path):
        """O boss das 08:00 fica intacto quando o das 10:00 e corrigido.

        O raio de estrago e limitado por DESENHO: nao existe sintaxe que
        alcance historico arbitrario, entao nenhuma sequencia de `.corrigir`
        pode desfazer meses de estatistica.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("TioMad", em(8, 0))
        registro.registrar("TioMad", em(10, 0))

        registro.corrigir("Kaus")

        assert registro.resumo("TioMad") == (1, em(8, 0)), "o mais antigo foi tocado"
        assert registro.resumo("Kaus") == (1, em(10, 0))

    def test_o_total_nunca_DIMINUI_numa_correcao_bem_sucedida(self, tmp_path):
        """Corrigir move um loot de dono; nao subtrai um loot do mundo."""
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("TioMad", em(10, 0))
        antes = len(registro.registros())

        registro.corrigir("Kaus")

        assert len(registro.registros()) == antes

    def test_sobra_sempre_um_pegou_para_aquele_alvo_em_TODOS_os_desfechos(
        self, tmp_path, monkeypatch
    ):
        """A forma sempre-verdadeira da invariante: o dono pode mudar, o loot
        nunca some.

        Os quatro desfechos de uma vez, porque a propriedade nao e sobre o
        caminho feliz — ela existe justamente para os caminhos em que alguma
        coisa deu errado no meio da troca.
        """

        def tem_registro_no_alvo(registro, alvo):
            return any(a == alvo for _, a in registro.registros())

        alvo = em(10, 0)

        # 1. corrigido
        corrigido = RegistroDeLoot(tmp_path / "corrigido")
        corrigido.registrar("TioMad", alvo)
        assert corrigido.corrigir("Kaus").estado == "corrigido"
        assert tem_registro_no_alvo(corrigido, alvo)

        # 2. mesmo_dono
        mesmo = RegistroDeLoot(tmp_path / "mesmo")
        mesmo.registrar("TioMad", alvo)
        assert mesmo.corrigir("TIOMAD").estado == "mesmo_dono"
        assert tem_registro_no_alvo(mesmo, alvo)

        # 3. sem_registro — nao ha alvo nenhum, e nao pode levantar
        vazio = RegistroDeLoot(tmp_path / "vazio")
        assert vazio.corrigir("Kaus").estado == "sem_registro"
        assert vazio.registros() == []

        # 4. falhou — o disco nao aceitou o registro novo
        falho = RegistroDeLoot(tmp_path / "falho")
        falho.registrar("TioMad", alvo)
        monkeypatch.setattr(falho, "_criar", lambda nome: "falhou")
        assert falho.corrigir("Kaus").estado == "falhou"
        assert tem_registro_no_alvo(falho, alvo)

    def test_falha_de_disco_NAO_apaga_o_velho(self, tmp_path, monkeypatch):
        """Criar antes de apagar, provado pelo lado que importa.

        Se o criar falhou, nada mudou: o registro velho continua la e a
        proxima tentativa acha o mesmo estado. A ordem inversa teria apagado o
        loot do TioMad sem nunca ter gravado o do Kaus.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("TioMad", em(10, 0))
        monkeypatch.setattr(registro, "_criar", lambda nome: "falhou")

        assert registro.corrigir("Kaus").estado == "falhou"
        assert registro.resumo("TioMad") == (1, em(10, 0)), "perdeu o loot do antigo"
        assert registro.resumo("Kaus") == (0, None)

    def test_sem_nenhum_registro_nao_levanta_e_responde_honesto(self, tmp_path):
        """Pasta vazia e um estado normal, nao um erro — o primeiro
        `.corrigir` de uma instalacao nova cai exatamente aqui."""
        registro = RegistroDeLoot(tmp_path)

        resposta = responder_correcao(registro, [self.SOLO], em(10, 30), "Kaus")

        assert "registrado" in resposta and "corrigir" in resposta
        assert registro.registros() == []

    def test_o_duplicado_COLAPSA(self, tmp_path):
        """O outro lado da ordem criar-antes-de-apagar.

        Dois donos no mesmo boss e o estado que sobra quando um apagar falhou.
        Corrigir para o dono certo apaga o excedente: isto e o CONSERTO do
        duplicado, nao perda de loot — o alvo continua com exatamente um dono.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("tiomad", em(10, 0))
        registro.registrar("kaus", em(10, 0))

        registro.corrigir("Kaus")

        no_alvo = [slug for slug, alvo in registro.registros() if alvo == em(10, 0)]
        assert no_alvo == ["kaus"]

    def test_a_resposta_do_no_op_nao_mente(self, tmp_path):
        """"Ja era dele" nunca pode sair como "passou de X para Y".

        Um bot que anuncia uma troca que nao houve treina o usuario a nao
        conferir — e conferir e a unica defesa contra corrigir o boss errado.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("TioMad", em(10, 0))

        resposta = responder_correcao(registro, [self.SOLO], em(10, 30), "TIOMAD")

        assert "passou do" not in resposta
        assert "nada mudou" in resposta
        assert registro.resumo("TioMad") == (1, em(10, 0))


class TestAtribuicaoEnderecada:
    """Registrar quem pegou o loot de um boss que JA PASSOU: o `.pegou`.

    O caso real, nas palavras do usuario: *"nao consegui atribuir o loot do
    boss das 18h e a Korzis pegou"*. Ate aqui isso era impossivel por
    construcao — um `pegou_*` so vinha ao mundo quando havia designacao
    previa e o `consumir()` a transformava em registro. Sem designacao previa
    NAO EXISTIA registro nenhum, e o `.corrigir` so troca o dono do registro
    mais recente: ele nao alcanca um horario especifico nem o caso "nao ha
    registro algum".

    O `.pegou` cria a sintaxe que alcanca historico arbitrario, e paga por
    ela com duas protecoes que o `.corrigir` nao tem: o horario e ENCAIXADO
    numa ocorrencia real do Solo Boss (nunca nasce registro orfao) e a
    resposta sempre diz o DIA de volta (o `.corrigir` nunca precisa disso,
    porque o alvo dele e sempre o mais recente).
    """

    SOLO = EventoAgendado(
        nome="Solo Boss",
        horarios=tuple((h, 0) for h in range(0, 24, 2)),
        avisar_no_horario=False,
    )

    def test_registra_um_boss_que_nao_tinha_registro_NENHUM(self, tmp_path):
        """O problema que o usuario relatou, na forma mais crua.

        Pasta vazia, nenhuma designacao, nenhum `pegou_*`. Este teste falha
        hoje porque nao existe caminho nenhum — nao porque o caminho esta
        errado.
        """
        registro = RegistroDeLoot(tmp_path)

        resposta = responder_atribuicao(
            registro, [self.SOLO], em(18, 30), "18:00 Korzis"
        )

        assert registro.resumo("Korzis") == (1, em(18, 0))
        assert len(registro.registros()) == 1
        assert "Korzis" in resposta
        assert "18:00" in resposta
        assert "hoje" in resposta, "a resposta precisa dizer o DIA de volta"

    def test_o_horario_gravado_e_o_do_BOSS_nao_o_digitado(self, tmp_path):
        """Quem lembra 20 minutos depois digita 18:20; o boss e o das 18:00.

        Deixar o horario digitado passar direto criaria
        `pegou_2026-08-25-1820_korzis`, um registro que nenhuma consulta
        futura por horario de boss encontraria.
        """
        registro = RegistroDeLoot(tmp_path)

        responder_atribuicao(registro, [self.SOLO], em(18, 30), "18:20 Korzis")

        assert [alvo for _, alvo in registro.registros()] == [em(18, 0)]

    def test_sem_boss_por_perto_RECUSA_e_NAO_grava(self, tmp_path):
        """19:00 esta a 60 minutos de 18:00 e de 20:00 — ambiguo, entao recusa.

        Registro de loot NUNCA e podado e nao tem backup: um registro orfao
        num horario inventado fica na estatistica para sempre, e nao ha
        comando nenhum que o alcance. A recusa e mais barata que a limpeza,
        e por isso a resposta diz quais horarios existem em vez de mandar a
        pessoa abrir o config.toml no meio do farm.
        """
        registro = RegistroDeLoot(tmp_path)

        resposta = responder_atribuicao(
            registro, [self.SOLO], em(19, 30), "19:00 Korzis"
        )

        assert registro.registros() == [], "gravou um registro orfao"
        assert "19:00" in resposta
        assert "18:00" in resposta and "20:00" in resposta

    def test_as_02h_o_horario_de_18h_e_de_ONTEM(self, tmp_path):
        """A regra que o usuario pediu nominalmente: sem data, o horario
        resolve para a ocorrencia mais recente que JA PASSOU.

        As 02h30, o boss de hoje as 18:00 ainda nao aconteceu — registrar
        loot de um boss que nao nasceu nao e coisa que alguem queira dizer.
        E a resposta diz "ontem" porque, num comando que alcanca horario
        arbitrario, o DIA e exatamente a informacao que falta para conferir.
        """
        registro = RegistroDeLoot(tmp_path)

        resposta = responder_atribuicao(
            registro, [self.SOLO], em(2, 30), "18:00 Korzis"
        )

        assert registro.resumo("Korzis") == (1, em(18, 0, dia=24))
        assert "ontem" in resposta

    def test_a_virada_da_meia_noite_no_sentido_CONTRARIO(self, tmp_path):
        """As 00:10, "23:50" encaixa no boss das 00:00 de HOJE.

        O desejado e 23:50 de ontem, mas a ocorrencia mais proxima que ja
        passou e a de hoje as 00:00 — dez minutos DEPOIS do desejado, contra
        cento e dez minutos do boss das 22:00 de ontem.

        E o teste que prova que a varredura do encaixe e centrada no DESEJADO
        e nao em `agora`. Ele falha de forma silenciosa e permanente se
        alguem "simplificar" os tres dias para um so.
        """
        registro = RegistroDeLoot(tmp_path)

        responder_atribuicao(registro, [self.SOLO], em(0, 10), "23:50 Korzis")

        assert [alvo for _, alvo in registro.registros()] == [em(0, 0, dia=25)]

    def test_nunca_resolve_para_o_FUTURO(self, tmp_path):
        """As 17:00, "18:00" e o boss de ontem — nao o de daqui a uma hora.

        Sem esta regra, `.pegou 18:00` as 17:00 registraria o loot de um boss
        que ainda nao aconteceu, e o `consumir()` do horario real depois
        criaria um segundo dono para o mesmo alvo.
        """
        registro = RegistroDeLoot(tmp_path)

        resposta = responder_atribuicao(
            registro, [self.SOLO], em(17, 0), "18:00 Korzis"
        )

        assert [alvo for _, alvo in registro.registros()] == [em(18, 0, dia=24)]
        assert "ontem" in resposta

    def test_o_boss_que_AINDA_NAO_NASCEU_nao_pode_ser_encaixado(self, tmp_path):
        """As 17:55, "17:50" nao pode virar o boss das 18:00 — ele nao nasceu.

        Este e o teste que prende a linha que DESCARTA ocorrencia futura no
        encaixe, e nenhum outro o faz. Nos demais casos o passado ja e a
        candidata mais proxima, entao a linha nunca e exercida: aqui, e so
        aqui, a ocorrencia FUTURA (18:00, a 10 minutos do desejado) esta mais
        perto que a passada (16:00, a 110 minutos). Sem o descarte, o scanner
        registraria o loot de um boss que ainda vai acontecer — e quando ele
        acontecesse, o `consumir()` criaria um segundo dono para o mesmo alvo.

        O desfecho certo e a RECUSA: 17:50 esta a mais de 30 minutos de
        qualquer boss que ja passou.
        """
        registro = RegistroDeLoot(tmp_path)

        resposta = responder_atribuicao(
            registro, [self.SOLO], em(17, 55), "17:50 Korzis"
        )

        assert registro.registros() == [], "registrou um boss que nao aconteceu"
        assert "17:50" in resposta

    def test_o_encaixe_aceita_o_atraso_de_quem_lembrou_depois(self, tmp_path):
        """A tolerancia existe para o caso real: a pessoa lembra depois.

        E ela vale nos DOIS sentidos — a ocorrencia mais proxima pode estar
        depois do horario digitado, contanto que ja tenha passado.
        """
        depois = RegistroDeLoot(tmp_path / "depois")
        responder_atribuicao(depois, [self.SOLO], em(18, 40), "18:20 Korzis")
        assert [alvo for _, alvo in depois.registros()] == [em(18, 0)]

        antes = RegistroDeLoot(tmp_path / "antes")
        responder_atribuicao(antes, [self.SOLO], em(19, 0), "17:45 Korzis")
        assert [alvo for _, alvo in antes.registros()] == [em(18, 0)]

    def test_a_recusa_LISTA_os_horarios_que_existem(self, tmp_path):
        """Recusar sem dizer quais horarios valem obrigaria a pessoa a abrir
        o config.toml no meio do farm — e a essa altura ela ja desistiu."""
        registro = RegistroDeLoot(tmp_path)
        resposta = responder_atribuicao(
            registro, [self.SOLO], em(19, 30), "19:00 Korzis"
        )
        assert "18:00" in resposta and "20:00" in resposta
        assert registro.registros() == []

        # Com uma agenda curta, a lista e exatamente aquela — nao um texto
        # generico que finge conhecer horarios que o usuario nao configurou.
        curta = EventoAgendado(
            nome="Solo Boss", horarios=((8, 0), (20, 0)), avisar_no_horario=False
        )
        outro = RegistroDeLoot(tmp_path / "curta")
        resposta = responder_atribuicao(outro, [curta], em(19, 0), "14:00 Korzis")

        assert "08:00" in resposta and "20:00" in resposta
        assert "18:00" not in resposta
        assert outro.registros() == []

    def test_agenda_sem_solo_boss_NAO_levanta(self, tmp_path):
        """Config quebrado, ou o Solo Boss renomeado por engano, vira resposta
        honesta — nunca excecao no meio do farm."""
        tvt = EventoAgendado(nome="TvT", horarios=((21, 50),))

        for eventos in ([], [tvt]):
            registro = RegistroDeLoot(tmp_path / f"a{len(eventos)}")
            resposta = responder_atribuicao(
                registro, eventos, em(18, 30), "18:00 Korzis"
            )
            assert "Solo Boss" in resposta
            assert registro.registros() == []

    def test_a_troca_enderecada_alcanca_um_boss_que_NAO_e_o_mais_recente(
        self, tmp_path
    ):
        """O que o `.pegou` faz e o `.corrigir` nao consegue fazer.

        O `.corrigir` mira o registro MAIS RECENTE e nao tem sintaxe para
        outro; aqui o boss das 08:00 e trocado com o das 18:00 intacto. E
        exatamente por isso que os dois comandos coexistem: um alcanca o
        passado enderecado, o outro nao pode alcancar por desenho.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("TioMad", em(8, 0))
        registro.registrar("Kaus", em(18, 0))

        responder_atribuicao(registro, [self.SOLO], em(19, 0), "08:00 Korzis")

        assert registro.resumo("Korzis") == (1, em(8, 0))
        assert registro.resumo("Kaus") == (1, em(18, 0)), "tocou no boss errado"
        assert registro.resumo("TioMad") == (0, None)

    def test_atribuir_ao_dono_que_JA_e_o_dono_nao_apaga_nada(self, tmp_path):
        """A guarda critica, e ela falha de forma DESTRUTIVA quando falta.

        `apelido("KORZIS") == apelido("Korzis")`, entao os dois geram o MESMO
        nome de arquivo: o `_criar` devolveria "ja_existia" e o passo de
        apagar destruiria o unico registro que existia — respondendo sucesso.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("Korzis", em(18, 0))

        correcao = registro.atribuir("KORZIS", em(18, 0))

        assert correcao.estado == "mesmo_dono"
        assert registro.resumo("Korzis") == (1, em(18, 0)), "a guarda apagou o loot"
        assert len(registro.registros()) == 1

    def test_sobra_sempre_um_pegou_para_o_alvo_em_TODOS_os_desfechos(
        self, tmp_path, monkeypatch
    ):
        """A forma sempre-verdadeira da invariante: o dono pode mudar, o loot
        nunca some.

        Os quatro desfechos de uma vez, porque a propriedade nao e sobre o
        caminho feliz — ela existe justamente para os caminhos em que alguma
        coisa deu errado no meio da troca.
        """

        def tem_registro_no_alvo(registro, alvo):
            return any(a == alvo for _, a in registro.registros())

        alvo = em(18, 0)

        # 1. criado — nao havia nada, e agora ha exatamente um
        criado = RegistroDeLoot(tmp_path / "criado")
        assert criado.atribuir("Korzis", alvo).estado == "criado"
        assert tem_registro_no_alvo(criado, alvo)

        # 2. corrigido
        corrigido = RegistroDeLoot(tmp_path / "corrigido")
        corrigido.registrar("TioMad", alvo)
        assert corrigido.atribuir("Korzis", alvo).estado == "corrigido"
        assert tem_registro_no_alvo(corrigido, alvo)

        # 3. mesmo_dono
        mesmo = RegistroDeLoot(tmp_path / "mesmo")
        mesmo.registrar("Korzis", alvo)
        assert mesmo.atribuir("KORZIS", alvo).estado == "mesmo_dono"
        assert tem_registro_no_alvo(mesmo, alvo)

        # 4. falhou — o disco nao aceitou o registro novo
        falho = RegistroDeLoot(tmp_path / "falho")
        falho.registrar("TioMad", alvo)
        monkeypatch.setattr(falho, "_criar", lambda nome: "falhou")
        assert falho.atribuir("Korzis", alvo).estado == "falhou"
        assert tem_registro_no_alvo(falho, alvo)

    def test_falha_de_disco_NAO_apaga_o_velho(self, tmp_path, monkeypatch):
        """Criar antes de apagar, provado pelo lado que importa.

        Se o criar falhou, nada mudou: o registro velho continua la. A ordem
        inversa teria apagado o loot do TioMad sem nunca ter gravado o do
        Kaus — e o WhatsApp diria que deu certo.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("TioMad", em(18, 0))
        monkeypatch.setattr(registro, "_criar", lambda nome: "falhou")

        assert registro.atribuir("Kaus", em(18, 0)).estado == "falhou"
        assert registro.resumo("TioMad") == (1, em(18, 0)), "perdeu o loot do antigo"
        assert registro.resumo("Kaus") == (0, None)

        resposta = responder_atribuicao(
            registro, [self.SOLO], em(18, 30), "18:00 Kaus"
        )
        assert "continua do Tiomad" in resposta

    def test_a_falha_de_disco_SEM_registro_previo_nao_inventa_dono_antigo(
        self, tmp_path, monkeypatch
    ):
        """"Continua do <ninguem>" seria uma frase sobre um dono que nunca
        existiu. Falhar criando do zero diz outra coisa: nada foi registrado.
        """
        registro = RegistroDeLoot(tmp_path)
        monkeypatch.setattr(registro, "_criar", lambda nome: "falhou")

        resposta = responder_atribuicao(
            registro, [self.SOLO], em(18, 30), "18:00 Korzis"
        )

        assert "nao foi registrado nada" in resposta
        assert "continua do" not in resposta
        assert registro.registros() == []

    def test_o_duplicado_COLAPSA(self, tmp_path):
        """Dois donos no mesmo boss e o estado que sobra quando um apagar
        falhou. Atribuir ao dono certo apaga o excedente.

        E aqui que a guarda tem que comparar a LISTA INTEIRA: sair cedo por
        `donos[0] == slug_novo` deixaria o duplicado de pe para sempre.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.registrar("tiomad", em(18, 0))
        registro.registrar("korzis", em(18, 0))

        registro.atribuir("Korzis", em(18, 0))

        no_alvo = [slug for slug, alvo in registro.registros() if alvo == em(18, 0)]
        assert no_alvo == ["korzis"]

    def test_a_designacao_pendente_do_MESMO_alvo_e_solta(self, tmp_path):
        """Se o scanner estava fora do ar as 18:00, a designacao das 18:00
        continua pendente. Sem solta-la, o proximo `consumir()` criaria um
        SEGUNDO dono para o mesmo boss — um duplicado que ninguem pediu.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.designar("TioMad", em(18, 0), em(17, 50))

        responder_atribuicao(registro, [self.SOLO], em(18, 30), "18:00 Korzis")

        assert registro.designacao() is None
        assert registro.consumir(em(19, 0)) is None
        assert len(registro.registros()) == 1

    def test_a_designacao_de_OUTRO_alvo_fica_INTACTA(self, tmp_path):
        """A regra e estreita de proposito e nao mistura conceito.

        Uma designacao cujo boss ja passou E ja tem dono escrito a mao nao
        tem mais alvo; a do boss das 20:00 ainda tem para onde ir, e apaga-la
        aqui seria o `.pegou` cancelando a VEZ de alguem sem ninguem pedir.
        """
        registro = RegistroDeLoot(tmp_path)
        registro.designar("TioMad", em(20, 0), em(18, 0))

        responder_atribuicao(registro, [self.SOLO], em(18, 30), "18:00 Korzis")

        designacao = registro.designacao()
        assert designacao is not None, "apagou a designacao de outro boss"
        assert designacao.alvo == em(20, 0)
        assert designacao.nick == "TioMad"

    def test_data_explicita_alcanca_um_dia_ANTIGO(self, tmp_path):
        """`.pegou 23/08 18:00 Korzis` em 25/08: dois dias atras.

        Sem a data, "18:00" so alcanca a ocorrencia mais recente que ja
        passou — e um boss de anteontem fica fora de alcance para sempre,
        porque a pasta nunca e podada e nao ha outro jeito de escrever nela.
        """
        registro = RegistroDeLoot(tmp_path)

        resposta = responder_atribuicao(
            registro, [self.SOLO], em(10, 0), "23/08 18:00 Korzis"
        )

        assert registro.resumo("Korzis") == (1, datetime(2026, 8, 23, 18, 0))
        assert "23/08" in resposta, "a resposta precisa dizer o DIA de volta"

    def test_data_com_ano_de_quatro_digitos_chega_no_mesmo_alvo(self, tmp_path):
        registro = RegistroDeLoot(tmp_path)

        responder_atribuicao(
            registro, [self.SOLO], em(10, 0), "23/08/2026 18:00 Korzis"
        )

        assert registro.resumo("Korzis") == (1, datetime(2026, 8, 23, 18, 0))

    def test_data_no_FUTURO_ou_IMPOSSIVEL_recusa_e_nao_grava(self, tmp_path):
        """Uma mensagem so para os dois casos, porque ela e verdadeira nos
        dois: aquela data nao aponta para nenhum momento que ja passou.

        Inventar um segundo canal de erro para distinguir "30/12 ainda nao
        chegou" de "31/02 nao existe" nao ajudaria ninguem a digitar melhor.
        """
        for argumento in ("30/12 18:00 Korzis", "31/02 18:00 Korzis"):
            registro = RegistroDeLoot(tmp_path / apelido(argumento))
            resposta = responder_atribuicao(
                registro, [self.SOLO], em(10, 0), argumento
            )
            assert registro.registros() == [], argumento
            assert "ja passou" in resposta, argumento

    def test_a_virada_do_ANO(self, tmp_path):
        """Em 03/01/2027, "30/12" sem ano e dezembro de 2026.

        Sem o recuo de um ano, dezembro seria SEMPRE uma data futura para
        quem digita em janeiro — e o comando recusaria justamente na semana
        em que a pessoa mais precisa dele, com uma mensagem que nao explica
        nada.
        """
        registro = RegistroDeLoot(tmp_path)

        responder_atribuicao(
            registro,
            [self.SOLO],
            datetime(2027, 1, 3, 10, 0),
            "30/12 18:00 Korzis",
        )

        assert registro.resumo("Korzis") == (1, datetime(2026, 12, 30, 18, 0))

    def test_as_grafias_de_horario(self, tmp_path):
        """"18h" e a grafia que o usuario usa — ele escreveu "boss das 18h"
        ao relatar o problema. Recusar por causa do formato transformaria o
        comando numa adivinhacao de sintaxe.
        """
        for argumento in (
            "18:00 Korzis",
            "18h Korzis",
            "18h00 Korzis",
            "18h30 Korzis",  # encaixa em 18:00 pela tolerancia
            "18 Korzis",
        ):
            registro = RegistroDeLoot(tmp_path / apelido(argumento))
            responder_atribuicao(registro, [self.SOLO], em(19, 0), argumento)
            assert [a for _, a in registro.registros()] == [em(18, 0)], argumento
