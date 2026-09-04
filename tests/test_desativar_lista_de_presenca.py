"""Desligar a lista de presenca do Solo Boss SEM calar o lembrete de 10 minutos.

A irma fina do `test_desativar_solo_boss.py`. Aquele cala o boss por completo;
este so para de MONTAR GRUPO — a chamada "Quem vai?", o `/entrar`, o `/sair`, o
fechamento da lista e a designacao de loot. A party parou de fazer Solo Boss
por enquanto e o usuario quer continuar sabendo que o boss vai nascer.

O QUE ESTE ARQUIVO PROVA, e por que cada prova existe:

1. **O LEMBRETE DE 10 MINUTOS CONTINUA SAINDO.** E o pedido inteiro. Se este
   arquivo tiver um so teste verde, que seja
   `test_com_a_lista_desligada_o_LEMBRETE_de_10_minutos_continua_saindo`; se
   ele for o unico vermelho, nada mais aqui importa. A garantia e ESTRUTURAL —
   o gate mora dentro do laco de TIPO, condicionado a `TipoDeAviso.CHAMADA`, e
   o ramo do `ANTES` nao consulta a variavel. Este teste confirma um desenho;
   ele nao segura um.

2. **QUATRO SUPERFICIES CALAM, E SO ELAS.** A chamada, o `/entrar`/`/sair`, o
   fechamento e a designacao de loot. Um portao por superficie, no funil mais
   estreito de cada uma, e nunca um `if lista_desligada` espalhado pelo
   despacho.

3. **O HISTORICO DE LOOT NAO E TOCADO.** `/pegou`, `/corrigir`, `/<nick>` e o
   consumo automatico continuam inteiros. Desligar a lista nao encosta na
   pasta `.loot/`. Isso inclui a fronteira consciente: uma designacao que JA
   existia continua sendo consumida no horario do boss — escrita como teste
   justamente para nao virar surpresa.

4. **O DESLIGAMENTO SOBREVIVE AO `vigiar-party.bat` E NAO EXPIRA NA PODA.** O
   marcador nao tem data, pela mesma razao do `evento_calado_`: `podar` roda no
   construtor, ou seja a cada arranque, e um marcador datado religaria a lista
   sozinho em `DIAS_DE_MARCADOR` — contra a decisao explicita do usuario.

5. **AS DUAS CHAVES SAO INDEPENDENTES, E O `/status` MOSTRA AS DUAS.** Cada uma
   e desfeita por um COMANDO DIFERENTE. Um `/status` que as fundisse deixaria o
   usuario sem saber se manda `/ativarsoloboss` ou `/ativarlista` — e mandar o
   errado devolve "ja estava ligado", que le como bot quebrado.

6. **DISCO ESTRAGADO FAZ A CHAMADA SAIR, nunca sumir.** A mesma lei do
   `RegistroEmDisco.marcar`: preferir o duplicado ao perdido.

Nenhum relogio e nenhuma fonte sao monkeypatchados — o tempo entra por
parametro e o disco estragado se produz apagando a pasta ou criando um
diretorio com nome de marcador. As fixtures (`SEGUNDA`, `SOLO_BOSS`, `TVT`) sao
as do arquivo irmao de proposito: os dois falam da MESMA agenda.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from l2scanner.agenda import (
    PREFIXO_FECHADO,
    PREFIXO_LISTA_DESLIGADA,
    Aviso,
    EventoAgendado,
    RegistroEmDisco,
    TipoDeAviso,
    avisos_devidos,
    chave_da_ocorrencia,
    nomes_dos_eventos,
    responder_lista_de_presenca,
    texto_do_aviso,
)

RAIZ = Path(__file__).resolve().parent.parent

# Uma segunda-feira, o mesmo dia conhecido do `test_agenda.py` e do irmao.
SEGUNDA = datetime(2026, 8, 24)
assert SEGUNDA.weekday() == 0

# O Solo Boss como o `config.toml` do repositorio o descreve, reduzido a UM
# horario para a prova caber: chamada 1h50 antes, lembrete 10 minutos antes, e
# NUNCA no horario.
SOLO_BOSS = EventoAgendado(
    nome="Solo Boss",
    horarios=((20, 0),),
    avisar_minutos_antes=10,
    avisar_no_horario=False,
    chamar_minutos_antes=110,
)
TVT = EventoAgendado(nome="TvT", horarios=((21, 50),), avisar_minutos_antes=10)

# Um segundo evento COM chamada, para provar que o desligamento e por evento e
# nao um modo global. O TvT do repositorio nao tem lista de presenca.
OUTRO_COM_LISTA = EventoAgendado(
    nome="Prime",
    horarios=((15, 0),),
    avisar_minutos_antes=10,
    chamar_minutos_antes=110,
)

ALVO = datetime(2026, 8, 24, 20, 0)
CHAMADA = datetime(2026, 8, 24, 18, 10)  # 110 minutos antes
LEMBRETE = datetime(2026, 8, 24, 19, 50)  # 10 minutos antes

SLUG = "solo-boss"


def _tipos(agora, eventos, desligadas=frozenset(), calados=frozenset()):
    return [
        a.tipo
        for a in avisos_devidos(
            agora,
            eventos,
            set(),
            eventos_calados=calados,
            listas_desligadas=desligadas,
        )
    ]


def _aviso(tipo, devido_em):
    return Aviso(evento="Solo Boss", tipo=tipo, alvo=ALVO, devido_em=devido_em)


# ---------------------------------------------------------------------------
# PONTO 1 — o teste-titulo, e ele vem primeiro no arquivo de proposito (D3)
# ---------------------------------------------------------------------------


class TestOLembreteDeDezMinutosSobrevive:
    """D3. O pedido inteiro mora nesta classe.

    O usuario parou de fazer Solo Boss em grupo e quer continuar sabendo que o
    boss vai nascer. Um plano que cale a antecedencia esta errado, por mais
    verde que o resto fique.
    """

    def test_com_a_lista_desligada_o_LEMBRETE_de_10_minutos_continua_saindo(self):
        assert _tipos(LEMBRETE, [SOLO_BOSS], frozenset({SLUG})) == [TipoDeAviso.ANTES]

    def test_o_lembrete_sai_com_o_texto_de_sempre(self):
        """Nao basta o aviso existir — ele tem que continuar dizendo o mesmo.

        Um lembrete que saisse mutilado ("Solo Boss comeca em 10 minutos" sem o
        horario) cumpriria a asercao de tipo acima e nao serviria para nada.
        """
        avisos = avisos_devidos(
            LEMBRETE, [SOLO_BOSS], set(), listas_desligadas=frozenset({SLUG})
        )
        texto = texto_do_aviso(avisos[0])
        assert "Solo Boss" in texto
        assert "10 minutos" in texto
        assert "20:00" in texto

    def test_o_lembrete_sai_MESMO_com_os_dois_gates_lidos_no_mesmo_tick(self):
        """O gate da lista nao pode vazar para o do evento calado.

        Os dois parametros chegam juntos em toda chamada real. Passar o
        conjunto errado para o lugar errado calaria a antecedencia sem erro
        nenhum — e o unico sintoma seria o usuario nao receber o aviso.
        """
        assert _tipos(
            LEMBRETE, [SOLO_BOSS], desligadas=frozenset({SLUG}), calados=frozenset()
        ) == [TipoDeAviso.ANTES]

    def test_so_o_desativarsoloboss_alcanca_o_lembrete(self):
        """A outra chave, a que o usuario NAO mandou, e que cala a antecedencia.

        Esta e a contraprova do teste-titulo: se nada calasse o lembrete, o
        teste acima passaria mesmo com o gate ausente.
        """
        assert _tipos(LEMBRETE, [SOLO_BOSS], calados=frozenset({SLUG})) == []


# ---------------------------------------------------------------------------
# PONTO 2 — o texto da CHAMADA (D4)
# ---------------------------------------------------------------------------


class TestOTextoDaChamada:
    """D4. A frase de hoje tem 149 caracteres e sai 12 vezes por dia no grupo."""

    def test_a_chamada_e_exatamente_a_frase_curta(self):
        assert (
            texto_do_aviso(_aviso(TipoDeAviso.CHAMADA, CHAMADA))
            == "Solo Boss as 20:00. Quem vai? (/entrar /sair no privado)"
        )

    def test_a_palavra_privado_sobreviveu_ao_encurtamento(self):
        """O fato mais caro de reaprender neste recurso.

        A ponte Baileys desta conta vem com ingestao de grupo desligada
        (medido 2026-08-24): quem responder no grupo fala com uma parede. A
        forma curta perdeu a explicacao e teve que MANTER a palavra.
        """
        texto = texto_do_aviso(_aviso(TipoDeAviso.CHAMADA, CHAMADA))
        assert "privado" in texto.lower()

    def test_a_chamada_encolheu_de_verdade(self):
        """Se um dia alguem 'melhorar' a frase de volta, isto avisa."""
        texto = texto_do_aviso(_aviso(TipoDeAviso.CHAMADA, CHAMADA))
        assert len(texto) < 80, f"a chamada voltou a ter {len(texto)} caracteres"

    def test_os_outros_dois_textos_nao_mudaram_junto(self):
        antes = texto_do_aviso(_aviso(TipoDeAviso.ANTES, LEMBRETE))
        agora = texto_do_aviso(_aviso(TipoDeAviso.AGORA, ALVO))
        assert "comeca em" in antes
        assert "comecou agora" in agora


# ---------------------------------------------------------------------------
# PONTO 3 — o portao (a), a CHAMADA
# ---------------------------------------------------------------------------


class TestPortaoDaChamada:
    """O gate mora em `avisos_devidos`, e SO no ramo da CHAMADA."""

    def test_ligada_a_chamada_sai_como_sempre(self):
        assert _tipos(CHAMADA, [SOLO_BOSS]) == [TipoDeAviso.CHAMADA]

    def test_desligada_a_chamada_nao_sai(self):
        assert _tipos(CHAMADA, [SOLO_BOSS], frozenset({SLUG})) == []

    def test_o_aviso_de_AGORA_de_quem_o_tem_ligado_continua_saindo(self):
        """O terceiro tipo nao e alcancado, e a diferenca com o irmao e essa.

        O `/desativarsoloboss` cala os TRES tipos porque o gate dele mora no
        laco de EVENTO. Este mora no laco de TIPO, e alcanca UM.
        """
        falante = EventoAgendado(
            nome="Solo Boss",
            horarios=((20, 0),),
            avisar_no_horario=True,
            chamar_minutos_antes=110,
        )
        assert _tipos(ALVO, [falante], frozenset({SLUG})) == [TipoDeAviso.AGORA]

    def test_outro_evento_com_chamada_nao_e_afetado(self):
        """O marcador e por EVENTO, e nao um modo global do scanner."""
        agora = datetime(2026, 8, 24, 13, 10)  # 110 min antes das 15:00
        assert _tipos(agora, [SOLO_BOSS, OUTRO_COM_LISTA], frozenset({SLUG})) == [
            TipoDeAviso.CHAMADA
        ]

    def test_sem_o_parametro_tudo_fica_byte_a_byte_como_estava(self):
        """O default vazio e o que mantem a suite inteira de hoje valendo."""
        assert [a.tipo for a in avisos_devidos(CHAMADA, [SOLO_BOSS], set())] == [
            TipoDeAviso.CHAMADA
        ]

    def test_o_dia_inteiro_perde_as_chamadas_e_mantem_os_lembretes(self):
        """A prova de volume, com os numeros escritos a mao.

        O Solo Boss do `config.toml` tem 12 ocorrencias: 12 chamadas + 12
        lembretes = 24 mensagens por dia. Com a lista desligada tem que sobrar
        exatamente a metade, e ela tem que ser a metade CERTA.
        """
        from l2scanner.config import ler_agenda

        agenda = [e for e in ler_agenda(RAIZ / "config.toml") if e.nome == "Solo Boss"]
        assert agenda, "o config.toml do repositorio perdeu o Solo Boss"

        enviados: set[str] = set()
        saidas = []
        instante = SEGUNDA
        for _ in range(24 * 60):
            for aviso in avisos_devidos(
                instante, agenda, enviados, listas_desligadas=frozenset({SLUG})
            ):
                enviados.add(aviso.chave)
                saidas.append(aviso.tipo)
            instante += timedelta(minutes=1)

        assert saidas.count(TipoDeAviso.CHAMADA) == 0
        assert saidas.count(TipoDeAviso.ANTES) == 12


# ---------------------------------------------------------------------------
# PONTO 4 — o portao (b), `/entrar` e `/sair`
# ---------------------------------------------------------------------------


class TestPortaoDoEntrarEDoSair:
    """A recusa e PREPENDIDA, e a posicao e a decisao.

    Um guarda inserido depois do `if not nick` deixaria o DONO sem bloco
    `[[membro]]` recebendo "Adicione um bloco [[membro]]..." com a lista
    desligada — uma mensagem que manda a pessoa consertar um arquivo que nao
    esta quebrado.
    """

    def _registro(self, tmp_path, desligar=True):
        registro = RegistroEmDisco(tmp_path)
        if desligar:
            registro.desligar_lista("Solo Boss")
        return registro

    def test_entrar_com_a_lista_desligada_recusa_e_diz_por_que(self, tmp_path):
        from l2scanner.presenca import responder_join

        resposta = responder_join(
            self._registro(tmp_path), [SOLO_BOSS], CHAMADA, "TioMad"
        )

        assert "desligada" in resposta.privado.lower()
        assert "/ativarlista" in resposta.privado

    def test_entrar_recusado_NAO_fala_no_grupo(self, tmp_path):
        from l2scanner.presenca import responder_join

        resposta = responder_join(
            self._registro(tmp_path), [SOLO_BOSS], CHAMADA, "TioMad"
        )
        assert resposta.grupo is None

    def test_entrar_recusado_NAO_escreve_nada_em_disco(self, tmp_path):
        """A recusa que gravasse deixaria a pessoa numa lista invisivel."""
        from l2scanner.agenda import PREFIXO_PRESENCA
        from l2scanner.presenca import responder_join

        responder_join(self._registro(tmp_path), [SOLO_BOSS], CHAMADA, "TioMad")

        assert [p.name for p in tmp_path.iterdir() if p.name.startswith(
            PREFIXO_PRESENCA
        )] == []

    def test_sair_com_a_lista_desligada_recusa_igual(self, tmp_path):
        from l2scanner.presenca import responder_leave

        resposta = responder_leave(
            self._registro(tmp_path), [SOLO_BOSS], CHAMADA, "TioMad"
        )

        assert "desligada" in resposta.privado.lower()
        assert resposta.grupo is None

    def test_o_texto_da_recusa_le_certo_para_os_DOIS_comandos(self, tmp_path):
        """Um texto so, e por isso ele nao pode dizer "voce nao entrou"."""
        from l2scanner.presenca import responder_join, responder_leave

        registro = self._registro(tmp_path)
        entrada = responder_join(registro, [SOLO_BOSS], CHAMADA, "TioMad")
        saida = responder_leave(registro, [SOLO_BOSS], CHAMADA, "TioMad")

        assert entrada.privado == saida.privado
        assert "ninguem entra e ninguem sai" in entrada.privado

    def test_o_dono_sem_bloco_membro_tambem_recebe_a_verdade(self, tmp_path):
        """O guarda vem ANTES do `if not nick`, e e isto que prova.

        Sem o prepend, este caminho responderia "Adicione um bloco [[membro]]
        com nick e telefone no config.toml" — mandando o usuario consertar um
        arquivo que esta certo.
        """
        from l2scanner.presenca import responder_join

        resposta = responder_join(self._registro(tmp_path), [SOLO_BOSS], CHAMADA, None)

        assert "desligada" in resposta.privado.lower()
        assert "[[membro]]" not in resposta.privado

    def test_a_recusa_NAO_manda_editar_o_config_toml(self, tmp_path):
        """A alternativa recusada: gatear no resolvedor de ocorrencia.

        Fazer `ocorrencia_da_chamada` devolver None produziria a mensagem do
        `_sem_chamada_na_agenda` — "ponha chamar_minutos_antes no [[evento]]" —,
        que e mentira: o config esta certo e foi um comando que desligou.
        """
        from l2scanner.presenca import responder_join

        resposta = responder_join(
            self._registro(tmp_path), [SOLO_BOSS], CHAMADA, "TioMad"
        )
        assert "chamar_minutos_antes" not in resposta.privado
        assert "config.toml" not in resposta.privado

    def test_com_a_lista_LIGADA_o_entrar_continua_exatamente_como_hoje(self, tmp_path):
        from l2scanner.presenca import responder_join

        resposta = responder_join(
            self._registro(tmp_path, desligar=False), [SOLO_BOSS], CHAMADA, "TioMad"
        )

        assert "Anotado" in resposta.privado
        assert resposta.grupo is not None

    def test_com_a_lista_LIGADA_o_sair_continua_exatamente_como_hoje(self, tmp_path):
        from l2scanner.presenca import responder_join, responder_leave

        registro = self._registro(tmp_path, desligar=False)
        responder_join(registro, [SOLO_BOSS], CHAMADA, "TioMad")

        resposta = responder_leave(registro, [SOLO_BOSS], CHAMADA, "TioMad")

        assert "saiu da lista" in resposta.privado
        assert resposta.grupo is not None

    def test_desligar_a_lista_do_boss_nao_recusa_a_lista_de_OUTRO_evento(
        self, tmp_path
    ):
        """O helper procura o evento com chamada cujo apelido esta no conjunto.

        Com o Solo Boss desligado e o Prime ligado, um `/entrar` ainda tem para
        onde ir — e nao pode ser recusado por causa do vizinho.
        """
        from l2scanner.presenca import responder_join

        registro = self._registro(tmp_path)
        resposta = responder_join(
            registro, [OUTRO_COM_LISTA], datetime(2026, 8, 24, 13, 10), "TioMad"
        )

        assert "Anotado" in resposta.privado


# ---------------------------------------------------------------------------
# PONTO 5 — o portao (c), o FECHAMENTO
# ---------------------------------------------------------------------------


class TestPortaoDoFechamento:
    """O `continue` vem ANTES do `fechar`, e a posicao e a decisao.

    Um tick que nao fala nao pode queimar o marcador — o mesmo argumento que a
    docstring da funcao ja faz para o caso da lista vazia.
    """

    DEPOIS = datetime(2026, 8, 24, 20, 1)

    def _com_presente(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        registro.entrar(chave_da_ocorrencia("Solo Boss", ALVO), "tiomad")
        return registro

    def test_com_a_lista_desligada_o_fechamento_nao_sai(self, tmp_path):
        from l2scanner.presenca import fechar_ocorrencias

        registro = self._com_presente(tmp_path)
        registro.desligar_lista("Solo Boss")

        assert fechar_ocorrencias(registro, [SOLO_BOSS], self.DEPOIS) == []

    def test_e_o_marcador_fechado_NAO_e_queimado(self, tmp_path):
        from l2scanner.presenca import fechar_ocorrencias

        registro = self._com_presente(tmp_path)
        registro.desligar_lista("Solo Boss")
        fechar_ocorrencias(registro, [SOLO_BOSS], self.DEPOIS)

        marcador = tmp_path / (PREFIXO_FECHADO + chave_da_ocorrencia("Solo Boss", ALVO))
        assert not marcador.exists()

    def test_religando_dentro_da_janela_o_fechamento_ainda_acontece(self, tmp_path):
        """A consequencia de nao queimar o marcador, e ela e o ponto.

        Se o `continue` viesse depois do `fechar`, a lista daquela ocorrencia
        ficaria muda para SEMPRE — mesmo com o usuario religando um segundo
        depois.
        """
        from l2scanner.presenca import fechar_ocorrencias

        registro = self._com_presente(tmp_path)
        registro.desligar_lista("Solo Boss")
        fechar_ocorrencias(registro, [SOLO_BOSS], self.DEPOIS)

        registro.religar_lista("Solo Boss")
        fechados = fechar_ocorrencias(registro, [SOLO_BOSS], self.DEPOIS)

        assert [f.evento for f in fechados] == ["Solo Boss"]
        assert fechados[0].nicks == ("tiomad",)

    def test_com_a_lista_ligada_o_fechamento_continua_como_hoje(self, tmp_path):
        from l2scanner.presenca import fechar_ocorrencias

        registro = self._com_presente(tmp_path)

        fechados = fechar_ocorrencias(registro, [SOLO_BOSS], self.DEPOIS)

        assert [f.evento for f in fechados] == ["Solo Boss"]

    def test_o_fechamento_de_OUTRO_evento_nao_e_alcancado(self, tmp_path):
        from l2scanner.presenca import fechar_ocorrencias

        alvo_do_outro = datetime(2026, 8, 24, 15, 0)
        registro = RegistroEmDisco(tmp_path)
        registro.entrar(chave_da_ocorrencia("Prime", alvo_do_outro), "tiomad")
        registro.desligar_lista("Solo Boss")

        fechados = fechar_ocorrencias(
            registro, [OUTRO_COM_LISTA], datetime(2026, 8, 24, 15, 1)
        )

        assert [f.evento for f in fechados] == ["Prime"]


# ---------------------------------------------------------------------------
# PONTO 6 — o portao (d), a DESIGNACAO de loot
# ---------------------------------------------------------------------------


class TestPortaoDaDesignacao:
    """Duas superficies: a linha `Loot:` do aviso e o comando `/loot-<nick>`."""

    def _loot(self, tmp_path):
        from l2scanner.loot import RegistroDeLoot

        return RegistroDeLoot(tmp_path / "loot")

    def test_a_linha_Loot_some_do_aviso_de_antecedencia(self, tmp_path):
        from l2scanner.loot import nick_para_o_aviso

        loot = self._loot(tmp_path)
        designacao = loot.designar("J4guar", ALVO, CHAMADA)

        assert (
            nick_para_o_aviso(
                _aviso(TipoDeAviso.ANTES, LEMBRETE), designacao, lista_desligada=True
            )
            is None
        )

    def test_com_a_lista_ligada_a_linha_Loot_continua_no_aviso(self, tmp_path):
        from l2scanner.loot import nick_para_o_aviso

        loot = self._loot(tmp_path)
        designacao = loot.designar("J4guar", ALVO, CHAMADA)

        assert (
            nick_para_o_aviso(_aviso(TipoDeAviso.ANTES, LEMBRETE), designacao)
            == "J4guar"
        )

    def test_o_texto_do_aviso_sai_sem_a_cauda_de_loot(self, tmp_path):
        """A prova na saida, e nao so no helper: e o texto que a party le."""
        from l2scanner.loot import nick_para_o_aviso

        loot = self._loot(tmp_path)
        designacao = loot.designar("J4guar", ALVO, CHAMADA)
        aviso = _aviso(TipoDeAviso.ANTES, LEMBRETE)

        texto = texto_do_aviso(
            aviso, nick_para_o_aviso(aviso, designacao, lista_desligada=True)
        )

        assert "Loot:" not in texto
        assert "Solo Boss comeca em 10 minutos" in texto

    def test_loot_nick_recusa_com_a_lista_desligada(self, tmp_path):
        from l2scanner.loot import responder_designacao

        resposta = responder_designacao(
            self._loot(tmp_path),
            [SOLO_BOSS],
            CHAMADA,
            "J4guar",
            lista_desligada=True,
        )

        assert "desligada" in resposta.lower()
        assert "/ativarlista" in resposta

    def test_a_recusa_da_designacao_NAO_grava_nada(self, tmp_path):
        from l2scanner.loot import responder_designacao

        loot = self._loot(tmp_path)
        responder_designacao(
            loot, [SOLO_BOSS], CHAMADA, "J4guar", lista_desligada=True
        )

        assert loot.designacao() is None

    def test_a_recusa_nao_apaga_uma_designacao_ANTERIOR(self, tmp_path):
        """Recusar e nao fazer nada. Apagar seria um estrago que ninguem pediu."""
        from l2scanner.loot import apelido, responder_designacao

        loot = self._loot(tmp_path)
        loot.designar("Korzis", ALVO, CHAMADA)

        responder_designacao(
            loot, [SOLO_BOSS], CHAMADA, "J4guar", lista_desligada=True
        )

        atual = loot.designacao()
        assert atual is not None and apelido(atual.nick) == "korzis"

    def test_a_recusa_promete_o_historico_intacto(self, tmp_path):
        from l2scanner.loot import responder_designacao

        resposta = responder_designacao(
            self._loot(tmp_path),
            [SOLO_BOSS],
            CHAMADA,
            "J4guar",
            lista_desligada=True,
        )

        assert "/pegou" in resposta
        assert "/corrigir" in resposta

    def test_cancelar_a_designacao_CONTINUA_funcionando(self, tmp_path):
        """De proposito, e a razao e de produto.

        Bloquear a unica forma de apagar uma designacao existente encalharia
        estado que o usuario nao consegue mais ver — o aviso de antecedencia
        parou de mostrar a linha `Loot:`. Cancelar so remove; nao ha estrago a
        conter.
        """
        from l2scanner.loot import responder_cancelamento

        loot = self._loot(tmp_path)
        loot.designar("J4guar", ALVO, CHAMADA)

        resposta = responder_cancelamento(loot, [SOLO_BOSS], CHAMADA)

        assert loot.designacao() is None
        assert "J4guar" in resposta

    def test_com_a_lista_ligada_a_designacao_continua_como_hoje(self, tmp_path):
        from l2scanner.loot import responder_designacao

        loot = self._loot(tmp_path)
        resposta = responder_designacao(loot, [SOLO_BOSS], CHAMADA, "J4guar")

        assert loot.designacao() is not None
        assert "J4guar" in resposta


# ---------------------------------------------------------------------------
# PONTO 7 — D3, o HISTORICO de loot nao e tocado
# ---------------------------------------------------------------------------


class TestOHistoricoDeLootFicaInteiro:
    """D3, segunda metade. Desligar a lista nao encosta na pasta `.loot/`."""

    def _loot(self, tmp_path):
        from l2scanner.loot import RegistroDeLoot

        return RegistroDeLoot(tmp_path / "loot")

    def test_a_consulta_por_nick_responde_igual(self, tmp_path):
        from l2scanner.loot import responder_consulta

        loot = self._loot(tmp_path)
        loot.registrar("J4guar", datetime(2026, 8, 24, 18, 0))
        RegistroEmDisco(tmp_path).desligar_lista("Solo Boss")

        resposta = responder_consulta(loot, "J4guar", CHAMADA)

        assert "J4guar" in resposta
        assert "1 loot" in resposta

    def test_o_corrigir_responde_igual(self, tmp_path):
        from l2scanner.loot import responder_correcao

        loot = self._loot(tmp_path)
        loot.registrar("J4guar", datetime(2026, 8, 24, 18, 0))
        RegistroEmDisco(tmp_path).desligar_lista("Solo Boss")

        resposta = responder_correcao(loot, [SOLO_BOSS], CHAMADA, "Korzis")

        assert "Korzis" in resposta
        assert loot.resumo("Korzis")[0] == 1

    def test_o_pegou_responde_igual(self, tmp_path):
        from l2scanner.loot import responder_atribuicao

        loot = self._loot(tmp_path)
        RegistroEmDisco(tmp_path).desligar_lista("Solo Boss")

        resposta = responder_atribuicao(
            loot, [SOLO_BOSS], datetime(2026, 8, 24, 21, 0), "20:00 Korzis"
        )

        assert "Korzis" in resposta
        assert loot.resumo("Korzis")[0] == 1

    def test_uma_designacao_ANTERIOR_ainda_e_consumida(self, tmp_path):
        """FRONTEIRA CONSCIENTE, escrita como teste para nao virar surpresa.

        Uma designacao que ja existia quando a lista foi desligada continua
        sendo consumida no horario do boss e continua gravando em `.loot/`.
        Isso e D3 sendo obedecido, e nao esquecimento: o consumo e HISTORICO, e
        o usuario disse para nao tocar no historico. Quem quiser desfazer usa
        `/loot-` antes do horario, ou `/corrigir` depois.
        """
        loot = self._loot(tmp_path)
        loot.designar("J4guar", ALVO, CHAMADA)
        RegistroEmDisco(tmp_path).desligar_lista("Solo Boss")

        consumida = loot.consumir(ALVO)

        assert consumida is not None and consumida.nick == "J4guar"
        assert loot.resumo("J4guar")[0] == 1

    def test_a_pasta_do_loot_nao_ganha_nem_perde_arquivo_ao_desligar(self, tmp_path):
        """A prova grosseira, e ela e a que o usuario entenderia."""
        loot = self._loot(tmp_path)
        loot.registrar("J4guar", datetime(2026, 8, 24, 18, 0))
        antes = sorted(p.name for p in (tmp_path / "loot").iterdir())

        RegistroEmDisco(tmp_path).desligar_lista("Solo Boss")

        assert sorted(p.name for p in (tmp_path / "loot").iterdir()) == antes


# ---------------------------------------------------------------------------
# PONTO 8 — o estado em disco: duravel, e a poda nao o come
# ---------------------------------------------------------------------------


class TestOEstadoEmDisco:
    """Onde o desligamento mora, e o que ele tem que aguentar."""

    def test_desligar_e_ler_de_volta(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        assert registro.desligar_lista("Solo Boss") == "desligada"
        assert registro.listas_desligadas() == frozenset({SLUG})

    def test_reiniciar_o_scanner_NAO_religa_a_lista(self, tmp_path):
        """O `vigiar-party.bat` e literalmente isto: objeto novo, mesma pasta."""
        RegistroEmDisco(tmp_path).desligar_lista("Solo Boss")

        assert RegistroEmDisco(tmp_path).listas_desligadas() == frozenset({SLUG})

    def test_a_poda_nao_expira_o_desligamento_da_lista(self, tmp_path):
        """Marcador sem data, de PROPOSITO — o usuario recusou expiracao.

        `podar` roda no construtor, ou seja a cada arranque. Se este marcador
        entrasse em `_PREFIXOS_CONHECIDOS` e ganhasse data, a lista religaria
        sozinha depois de tres dias e ninguem saberia por que.
        """
        registro = RegistroEmDisco(tmp_path)
        registro.desligar_lista("Solo Boss")

        assert registro.podar(hoje=date(2030, 1, 1)) >= 0
        assert registro.listas_desligadas() == frozenset({SLUG})
        assert RegistroEmDisco(tmp_path).listas_desligadas() == frozenset({SLUG})

    def test_desligar_duas_vezes_diz_que_ja_estava(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        assert registro.desligar_lista("Solo Boss") == "desligada"
        assert registro.desligar_lista("Solo Boss") == "ja_estava"

    def test_religar_diz_se_havia_o_que_religar(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        assert registro.religar_lista("Solo Boss") == "ja_estava"
        registro.desligar_lista("Solo Boss")
        assert registro.religar_lista("Solo Boss") == "religada"
        assert registro.listas_desligadas() == frozenset()

    def test_os_dois_namespaces_sao_independentes_em_disco(self, tmp_path):
        """Calar o boss nao desliga a lista, e desligar a lista nao cala o boss.

        As duas chaves nao sao aninhadas — e por isso o `/status` tem que
        mostrar as duas separadas.
        """
        registro = RegistroEmDisco(tmp_path)
        registro.desligar_lista("Solo Boss")

        assert registro.eventos_calados() == frozenset()
        assert registro.listas_desligadas() == frozenset({SLUG})

        registro.religar_lista("Solo Boss")
        registro.calar_evento("Solo Boss")

        assert registro.eventos_calados() == frozenset({SLUG})
        assert registro.listas_desligadas() == frozenset()

    def test_o_marcador_nao_atrapalha_o_resto_da_pasta(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        registro.desligar_lista("Solo Boss")
        registro.marcar("2026-08-24_solo-boss-2000_antes")

        assert registro.cancelados() == set()
        assert registro.presentes("2026-08-24_solo-boss-2000") == frozenset()
        assert registro.listas_desligadas() == frozenset({SLUG})

    def test_os_dois_baldes_de_prefixo_continuam_disjuntos(self):
        """Um prefixo nos dois seria a poda contradizendo a decisao."""
        from l2scanner.agenda import _PREFIXOS_CONHECIDOS, _PREFIXOS_SEM_DATA

        assert set(_PREFIXOS_CONHECIDOS) & set(_PREFIXOS_SEM_DATA) == set()

    def test_o_prefixo_novo_esta_no_balde_SEM_DATA(self):
        from l2scanner.agenda import _PREFIXOS_CONHECIDOS, _PREFIXOS_SEM_DATA

        assert PREFIXO_LISTA_DESLIGADA in _PREFIXOS_SEM_DATA
        assert PREFIXO_LISTA_DESLIGADA not in _PREFIXOS_CONHECIDOS

    def test_o_tripwire_de_introspecao_continua_verde(self):
        """Todo `PREFIXO_*` do modulo tem que escolher um dos dois baldes.

        O mesmo tripwire que o irmao preservou. Um prefixo novo que nao escolha
        nasce imortal em silencio — ou expira quando nao devia.
        """
        from l2scanner import agenda as modulo
        from l2scanner.agenda import _PREFIXOS_CONHECIDOS, _PREFIXOS_SEM_DATA

        declarados = {
            valor
            for nome, valor in vars(modulo).items()
            if nome.startswith("PREFIXO_") and isinstance(valor, str)
        }
        orfaos = declarados - set(_PREFIXOS_CONHECIDOS) - set(_PREFIXOS_SEM_DATA)
        assert not orfaos, f"prefixo sem balde: {sorted(orfaos)}"


# ---------------------------------------------------------------------------
# PONTO 9 — disco estragado, e a direcao da falha
# ---------------------------------------------------------------------------


class TestDiscoEstragado:
    """Leitura defensiva: a pasta e duravel, compartilhada e nao e nossa."""

    def test_nome_truncado_e_ignorado_sem_derrubar_nada(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        (tmp_path / PREFIXO_LISTA_DESLIGADA).write_text("", encoding="utf-8")

        assert registro.listas_desligadas() == frozenset()

    def test_lixo_na_pasta_nao_derruba_a_leitura(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        registro.desligar_lista("Solo Boss")
        (tmp_path / "arquivo_qualquer.txt").write_text("lixo", encoding="utf-8")
        (tmp_path / "lista_desligada").write_text("sem underline final", "utf-8")
        os.mkdir(tmp_path / (PREFIXO_LISTA_DESLIGADA + "uma-pasta"))

        assert SLUG in registro.listas_desligadas()

    def test_a_pasta_sumindo_faz_a_CHAMADA_sair(self, tmp_path):
        """A direcao da falha, e ela nao e simetrica.

        Disco ilegivel = nenhuma lista desligada = a chamada SAI. E a lei
        escrita no `marcar`: preferir o duplicado ao perdido. A direcao oposta
        silenciaria a chamada por causa de um disco travado, que e a falha que
        ninguem percebe.
        """
        pasta = tmp_path / "agenda"
        registro = RegistroEmDisco(pasta)
        registro.desligar_lista("Solo Boss")
        for arquivo in pasta.iterdir():
            arquivo.unlink()
        pasta.rmdir()

        assert registro.listas_desligadas() == frozenset()
        assert _tipos(CHAMADA, [SOLO_BOSS], registro.listas_desligadas()) == [
            TipoDeAviso.CHAMADA
        ]

    def test_a_escrita_que_falha_NAO_vira_sucesso(self, tmp_path):
        """Dizer "desliguei" sobre uma escrita que o disco recusou faria o
        usuario parar de esperar a chamada que vai continuar saindo."""
        registro = RegistroEmDisco(tmp_path / "agenda")
        (tmp_path / "agenda").rmdir()

        assert registro.desligar_lista("Solo Boss") == "falhou"

    def test_religar_que_falha_diz_que_a_lista_CONTINUA_desligada(self, tmp_path):
        """A direcao perigosa, e por isso ela e dita em voz alta."""
        registro = RegistroEmDisco(tmp_path)
        os.mkdir(tmp_path / (PREFIXO_LISTA_DESLIGADA + SLUG))
        os.mkdir(tmp_path / (PREFIXO_LISTA_DESLIGADA + SLUG) / "trava")

        assert registro.religar_lista("Solo Boss") == "falhou"

        resposta = responder_lista_de_presenca(
            registro, [SOLO_BOSS], "Solo Boss", False, "quem"
        )
        assert "CONTINUA desligada" in resposta

    def test_a_escrita_que_falha_produz_a_resposta_que_nao_promete_nada(
        self, tmp_path
    ):
        registro = RegistroEmDisco(tmp_path / "agenda")
        (tmp_path / "agenda").rmdir()

        resposta = responder_lista_de_presenca(
            registro, [SOLO_BOSS], "Solo Boss", True, "quem"
        )

        assert "CONTINUA saindo" in resposta


# ---------------------------------------------------------------------------
# PONTO 10 — duas instancias
# ---------------------------------------------------------------------------


class TestDuasInstancias:
    """O usuario roda Yazalaque e Faerlina lado a lado, na MESMA pasta."""

    def test_duas_instancias_competindo_so_uma_desliga(self, tmp_path):
        yazalaque = RegistroEmDisco(tmp_path)
        faerlina = RegistroEmDisco(tmp_path)

        resultados = [
            yazalaque.desligar_lista("Solo Boss"),
            faerlina.desligar_lista("Solo Boss"),
        ]

        assert resultados.count("desligada") == 1
        assert resultados.count("ja_estava") == 1
        assert faerlina.listas_desligadas() == frozenset({SLUG})

    def test_duas_instancias_religando_so_uma_religa(self, tmp_path):
        yazalaque = RegistroEmDisco(tmp_path)
        faerlina = RegistroEmDisco(tmp_path)
        yazalaque.desligar_lista("Solo Boss")

        resultados = [
            yazalaque.religar_lista("Solo Boss"),
            faerlina.religar_lista("Solo Boss"),
        ]

        assert resultados.count("religada") == 1
        assert resultados.count("ja_estava") == 1


# ---------------------------------------------------------------------------
# PONTO 11 — o `/status` nas QUATRO combinacoes
# ---------------------------------------------------------------------------


class TestOStatusNasQuatroCombinacoes:
    """As duas chaves nao sao aninhadas, e o `/status` tem que mostrar as duas.

    Um `/status` que as fundisse num "tudo desligado" deixaria o usuario sem
    saber se manda `/ativarsoloboss` ou `/ativarlista` — e mandar o errado
    devolve "ja estava ligado", que le como bot quebrado.
    """

    def _status(self, tmp_path, calar=False, desligar=False):
        from l2scanner.__main__ import _obedecer_status

        registro = RegistroEmDisco(tmp_path)
        if calar:
            registro.calar_evento("Solo Boss")
        if desligar:
            registro.desligar_lista("Solo Boss")
        return _obedecer_status(
            registro, [SOLO_BOSS, TVT], datetime(2026, 8, 24, 12, 0)
        )

    def test_tudo_ligado_o_status_nao_inventa_nada(self, tmp_path):
        resposta = self._status(tmp_path)
        assert "desativad" not in resposta.lower()
        assert "lista de presenca" not in resposta.lower()

    def test_so_a_lista_desligada(self, tmp_path):
        """A combinacao desta tarefa: o boss fala, a lista nao monta grupo."""
        resposta = self._status(tmp_path, desligar=True)
        assert "lista de presenca DESLIGADA de Solo Boss" in resposta
        assert "avisos DESATIVADOS" not in resposta

    def test_so_os_avisos_desativados(self, tmp_path):
        resposta = self._status(tmp_path, calar=True)
        assert "avisos DESATIVADOS de Solo Boss" in resposta
        assert "lista de presenca" not in resposta.lower()

    def test_as_duas_desligadas_saem_NOMEADAS_SEPARADAMENTE(self, tmp_path):
        """Cada uma e desfeita por um comando diferente."""
        resposta = self._status(tmp_path, calar=True, desligar=True)
        assert "avisos DESATIVADOS de Solo Boss" in resposta
        assert "lista de presenca DESLIGADA de Solo Boss" in resposta

    def test_o_silencio_maior_vem_primeiro(self, tmp_path):
        resposta = self._status(tmp_path, calar=True, desligar=True)
        assert resposta.index("avisos DESATIVADOS") < resposta.index(
            "lista de presenca DESLIGADA"
        )

    def test_o_status_sobrevive_ao_restart_junto_com_o_estado(self, tmp_path):
        RegistroEmDisco(tmp_path).desligar_lista("Solo Boss")
        assert "lista de presenca DESLIGADA" in self._status(tmp_path)

    def test_nomes_dos_eventos_devolve_o_nome_COMO_CONFIGURADO(self):
        """O disco guarda `solo-boss`; o usuario escreveu `Solo Boss`.

        A funcao mapeia apelidos -> nomes e NUNCA soube por que um apelido
        estava no conjunto. O nome antigo (`nomes_calados`) passou a mentir na
        segunda chamada; por isso ele virou `nomes_dos_eventos`.
        """
        assert nomes_dos_eventos([SOLO_BOSS, TVT], frozenset({SLUG})) == ["Solo Boss"]
        assert nomes_dos_eventos([SOLO_BOSS], frozenset()) == []
        assert nomes_dos_eventos([TVT], frozenset({SLUG})) == []


# ---------------------------------------------------------------------------
# PONTO 12 — a resposta do comando, e ela consulta o OUTRO estado
# ---------------------------------------------------------------------------


class TestARespostaDoComando:
    """`responder_lista_de_presenca`, no tri-estado dos dois sentidos."""

    def test_desligar_lista_promete_o_lembrete_com_os_minutos_do_config(
        self, tmp_path
    ):
        """`{N}` sai de `evento.avisar_minutos_antes`, nunca de um literal.

        Mesma lei do `_o_que_o_evento_anuncia`: a resposta que dissesse "10" a
        mao passaria a mentir no dia em que o usuario editasse o campo.
        """
        registro = RegistroEmDisco(tmp_path)
        resposta = responder_lista_de_presenca(
            registro, [SOLO_BOSS], "Solo Boss", True, "Yazalaque"
        )

        assert "O lembrete de 10 minutos antes CONTINUA chegando" in resposta
        assert "Yazalaque" in resposta

    def test_os_minutos_acompanham_o_config(self, tmp_path):
        outro = EventoAgendado(
            nome="Solo Boss",
            horarios=((20, 0),),
            avisar_minutos_antes=25,
            chamar_minutos_antes=110,
        )
        resposta = responder_lista_de_presenca(
            RegistroEmDisco(tmp_path), [outro], "Solo Boss", True, "quem"
        )
        assert "25 minutos" in resposta

    def test_desligar_lista_diz_as_QUATRO_coisas_que_calam(self, tmp_path):
        resposta = responder_lista_de_presenca(
            RegistroEmDisco(tmp_path), [SOLO_BOSS], "Solo Boss", True, "quem"
        )
        assert "quem vai" in resposta
        assert "/entrar" in resposta and "/sair" in resposta
        assert "nao fecha mais" in resposta
        assert "/loot-<nick>" in resposta

    def test_desligar_lista_diz_que_nao_volta_sozinho(self, tmp_path):
        resposta = responder_lista_de_presenca(
            RegistroEmDisco(tmp_path), [SOLO_BOSS], "Solo Boss", True, "quem"
        )
        assert "nao volta sozinho" in resposta
        assert "/ativarlista" in resposta

    def test_com_o_boss_JA_CALADO_a_resposta_NAO_promete_o_lembrete(self, tmp_path):
        """A frase que faz esta funcionalidade valer e FALSA se o boss estiver
        calado. Prometer um aviso que nao vai chegar e o pior defeito possivel
        aqui."""
        registro = RegistroEmDisco(tmp_path)
        registro.calar_evento("Solo Boss")

        resposta = responder_lista_de_presenca(
            registro, [SOLO_BOSS], "Solo Boss", True, "quem"
        )

        assert "CONTINUA chegando" not in resposta
        assert "tambem nao esta saindo" in resposta
        assert "/ativarsoloboss" in resposta

    def test_com_o_boss_calado_a_resposta_ainda_diz_o_que_ELA_desligou(
        self, tmp_path
    ):
        registro = RegistroEmDisco(tmp_path)
        registro.calar_evento("Solo Boss")

        resposta = responder_lista_de_presenca(
            registro, [SOLO_BOSS], "Solo Boss", True, "quem"
        )

        assert "paro de perguntar quem vai" in resposta
        assert "/ativarlista" in resposta

    def test_a_resposta_promete_o_historico_de_loot_inteiro(self, tmp_path):
        resposta = responder_lista_de_presenca(
            RegistroEmDisco(tmp_path), [SOLO_BOSS], "Solo Boss", True, "quem"
        )
        assert "/pegou" in resposta
        assert "/corrigir" in resposta

    def test_ja_desligada_diz_que_ja_estava(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        registro.desligar_lista("Solo Boss")

        resposta = responder_lista_de_presenca(
            registro, [SOLO_BOSS], "Solo Boss", True, "quem"
        )

        assert "ja estava desligada" in resposta

    def test_religar_diz_o_que_volta(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        registro.desligar_lista("Solo Boss")

        resposta = responder_lista_de_presenca(
            registro, [SOLO_BOSS], "Solo Boss", False, "Yazalaque"
        )

        assert "Yazalaque" in resposta
        assert "volto a perguntar quem vai" in resposta
        assert registro.listas_desligadas() == frozenset()

    def test_ja_ligada_diz_que_nao_mudou_nada(self, tmp_path):
        resposta = responder_lista_de_presenca(
            RegistroEmDisco(tmp_path), [SOLO_BOSS], "Solo Boss", False, "quem"
        )
        assert "ja estava ligada" in resposta

    def test_evento_fora_da_agenda_e_RECUSADO(self, tmp_path):
        """Um marcador gravado para um evento que o config.toml nao tem nao
        gateia nada e nao aparece no `/status` — duas superficies mentindo
        juntas enquanto a chamada continua saindo."""
        registro = RegistroEmDisco(tmp_path)

        resposta = responder_lista_de_presenca(
            registro, [TVT], "Solo Boss", True, "quem"
        )

        assert registro.listas_desligadas() == frozenset()
        assert "agenda" in resposta.lower()

    def test_evento_SEM_CHAMADA_e_RECUSADO_nomeando_o_CAMPO(self, tmp_path):
        """Segue `_sem_chamada_na_agenda`: nomeia o campo, e nao o evento.

        O TvT esta na agenda mas nao tem lista de presenca. Gravar um marcador
        para ele responderia "desliguei" sobre coisa nenhuma.
        """
        registro = RegistroEmDisco(tmp_path)

        resposta = responder_lista_de_presenca(
            registro, [SOLO_BOSS, TVT], "TvT", True, "quem"
        )

        assert registro.listas_desligadas() == frozenset()
        assert "chamar_minutos_antes" in resposta


# ---------------------------------------------------------------------------
# PONTO 13 — os comandos
# ---------------------------------------------------------------------------


class TestOsComandos:
    """As quatro palavras, as variantes de graca, e a fronteira de autorizacao."""

    @pytest.mark.parametrize(
        "texto",
        [
            "/desativarlista",
            "/desativar-lista",
            "/desativar lista",
            "/desativarpresenca",
            "/desativar-presenca",
            "/desativar presenca",
        ],
    )
    def test_as_formas_do_desligamento_caem_no_membro_novo(self, texto):
        from l2scanner.comandos import Comando, interpretar

        assert interpretar(texto) is Comando.DESATIVAR_LISTA

    @pytest.mark.parametrize(
        "texto",
        [
            "/ativarlista",
            "/ativar-lista",
            "/ativar lista",
            "/ativarpresenca",
            "/ativar-presenca",
            "/ativar presenca",
        ],
    )
    def test_as_formas_do_religamento_caem_no_membro_novo(self, texto):
        from l2scanner.comandos import Comando, interpretar

        assert interpretar(texto) is Comando.ATIVAR_LISTA

    def test_o_apelido_aqui_e_SINONIMO_e_nao_abreviacao(self):
        """A diferenca para o precedente, escrita para nao ser confundida.

        O `desativarboss` nasceu porque `desativarsoloboss` tem 17 caracteres e
        a mao erra no meio do farm. `desativarlista` ja tem 14. O risco aqui e
        outro: quem pensa "presenca" em vez de "lista" digitaria uma forma que
        morre no `continue` do laco de autorizacao, SEM resposta de recusa — e
        o sintoma, do lado de quem digitou, e o bot ter caido.
        """
        assert len("desativarlista") == 14
        assert len("desativarpresenca") == 17

    def test_desativar_sozinho_NAO_vira_nada(self):
        """Mesma disciplina do D-02: comando sem argumento nao mexe em estado
        duravel. Quem digita `/desativar` nao disse O QUE desativar."""
        from l2scanner.comandos import interpretar

        assert interpretar("/desativar") is None
        assert interpretar("/ativar") is None

    def test_lista_sozinho_NAO_entra_no_vocabulario(self):
        """"Lista" e um nome de personagem plausivel demais para queimar."""
        from l2scanner.comandos import interpretar

        assert interpretar("/lista") is None
        assert interpretar("/presenca") is None

    @pytest.mark.parametrize(
        "nick", ["TioMad", "Kaus", "Korzis", "J4guar", "Yazalaque", "Faerlina"]
    )
    def test_o_roster_real_continua_resolvendo_como_consulta(self, nick):
        """A auditoria de colisao do vocabulario, conferida contra o roster.

        `desativarlista` (14), `ativarlista` (11) e `ativarpresenca` (14) casam
        `_NICK_VALIDO` e portanto queimam esses tres nomes de personagem. O
        preco esta aceito e documentado; o que NAO pode acontecer e um nick de
        verdade cair junto.
        """
        from l2scanner.comandos import Comando, interpretar, interpretar_dinamico

        conhecidos = frozenset({nick.lower()})
        assert interpretar("/" + nick) is None
        assert interpretar_dinamico("/" + nick, conhecidos) == (
            Comando.LOOT_CONSULTA,
            nick,
        )

    def test_os_dois_novos_ficam_FORA_de_COMANDOS_DE_MEMBRO(self):
        """Prova NOMEADA, alem do tripwire derivado.

        O efeito e a ausencia de mensagem para a party inteira por tempo
        indeterminado — a mesma categoria de estrago do `/desativarsoloboss`, e
        aqui com uma agravante: um party-mate podia desligar a lista de
        presenca de todos os outros.
        """
        from l2scanner.comandos import COMANDOS_DE_MEMBRO, Comando

        assert Comando.DESATIVAR_LISTA not in COMANDOS_DE_MEMBRO
        assert Comando.ATIVAR_LISTA not in COMANDOS_DE_MEMBRO

    def test_o_tripwire_da_ajuda_continua_verde(self):
        from l2scanner.comandos import _AJUDA, Comando

        assert set(_AJUDA) == set(Comando)

    def test_a_ajuda_do_par_novo_diz_que_o_lembrete_continua(self):
        """Quem le a ajuda precisa saber o recorte ANTES de digitar.

        Descobrir depois — pela ausencia de uma chamada que ele achava que
        tinha mantido, ou pela presenca de um lembrete que achava que tinha
        desligado — e descobrir tarde.
        """
        from l2scanner.comandos import _AJUDA, Comando

        assert "lembrete" in _AJUDA[Comando.DESATIVAR_LISTA].descricao.lower()

    def test_o_par_novo_fica_na_familia_Silencio(self):
        from l2scanner.comandos import _AJUDA, Comando

        assert _AJUDA[Comando.DESATIVAR_LISTA].familia == "Silencio"
        assert _AJUDA[Comando.ATIVAR_LISTA].familia == "Silencio"


# ---------------------------------------------------------------------------
# PONTO 14 — os dois lacos obedecem
# ---------------------------------------------------------------------------


class TestOsDoisLacosObedecem:
    """Sao DOIS lacos, e desligar so um deixaria a chamada saindo pelo outro.

    O usuario roda `vigiar-party.bat` (o laco principal, via `Sessao`) e
    `avisos-tvt.bat` (`--so-agenda`). Os dois leem a MESMA pasta `.agenda/` e
    falam no MESMO grupo.
    """

    def _sessao(self, eventos, registro, loot=None):
        from l2scanner.sessao import Sessao

        class SemSilencio:
            def ativo(self):
                return False

            def atualizar(self, agora):
                return None

        return Sessao(
            cal=None,
            rastreador=None,
            eventos_agendados=eventos,
            registro=registro,
            silencio=SemSilencio(),
            loot=loot,
        )

    def _avisos_do_tick(self, tmp_path, agora, desligar):
        from l2scanner.sessao import ResultadoDoTick

        registro = RegistroEmDisco(tmp_path)
        if desligar:
            registro.desligar_lista("Solo Boss")
        sessao = self._sessao([SOLO_BOSS], registro)
        resultado = ResultadoDoTick()
        sessao._processar_agenda(agora, resultado)
        return resultado.avisos

    def test_o_laco_principal_cala_a_chamada(self, tmp_path):
        assert self._avisos_do_tick(tmp_path, CHAMADA, desligar=False)
        assert self._avisos_do_tick(tmp_path / "outra", CHAMADA, desligar=True) == []

    def test_o_laco_principal_MANTEM_o_lembrete(self, tmp_path):
        """O teste-titulo, agora pelo caminho real do `vigiar-party.bat`."""
        avisos = self._avisos_do_tick(tmp_path, LEMBRETE, desligar=True)

        assert len(avisos) == 1
        assert "comeca em 10 minutos" in avisos[0]

    def test_o_laco_principal_tira_a_linha_Loot_do_lembrete(self, tmp_path):
        from l2scanner.loot import RegistroDeLoot
        from l2scanner.sessao import ResultadoDoTick

        registro = RegistroEmDisco(tmp_path)
        registro.desligar_lista("Solo Boss")
        loot = RegistroDeLoot(tmp_path / "loot")
        loot.designar("J4guar", ALVO, CHAMADA)

        resultado = ResultadoDoTick()
        self._sessao([SOLO_BOSS], registro, loot=loot)._processar_agenda(
            LEMBRETE, resultado
        )

        assert resultado.avisos and "Loot:" not in resultado.avisos[0]

    def test_o_laco_da_agenda_le_as_listas_desligadas(self):
        """Tripwire de fonte, o mesmo idioma do teste do relogio monotonico.

        `laco_da_agenda` e um `while True` com rede e sono dentro; le-lo e a
        forma que este repositorio ja usa para provar que uma chamada carrega o
        argumento certo.
        """
        import inspect
        import re

        from l2scanner import __main__ as principal

        fonte = inspect.getsource(principal.laco_da_agenda)
        corpo = fonte[fonte.index("avisos_devidos(") :]
        chamada = re.match(r"avisos_devidos\((.*?)\n\s*\)", corpo, re.S)
        assert chamada, "laco_da_agenda nao chama avisos_devidos em varias linhas"
        assert "listas_desligadas" in chamada.group(1), (
            "o laco --so-agenda ignora o desligamento da lista: a chamada "
            "ficaria quieta no vigiar-party.bat e falante no avisos-tvt.bat"
        )

    def test_o_laco_da_agenda_converte_o_conjunto_em_BOOLEANO_para_o_loot(self):
        """A unica armadilha de TIPO desta costura.

        `listas_desligadas()` devolve um conjunto de apelidos;
        `nick_para_o_aviso` recebe um `bool`. Passar o frozenset direto
        compila, roda, e fica truthy sempre que a lista de QUALQUER evento
        estiver desligada — a linha `Loot:` sumiria do TvT tambem, sem erro
        nenhum.
        """
        import inspect

        from l2scanner import __main__ as principal

        fonte = inspect.getsource(principal.laco_da_agenda)
        assert "lista_desligada=" in fonte, (
            "o laco --so-agenda nao passa `lista_desligada=` para "
            "nick_para_o_aviso"
        )
        trecho = fonte[fonte.index("lista_desligada=") :]
        assert "in " in trecho[:120], (
            "o laco --so-agenda parece passar o CONJUNTO cru em vez do "
            "booleano `apelido_do_evento(NOME_DO_SOLO_BOSS) in desligadas`"
        )

    def test_a_sessao_le_o_disco_a_cada_tick_sem_cache(self, tmp_path):
        """O comando pode chegar na OUTRA instancia.

        Um cache faria este processo continuar chamando o que o outro acabou de
        desligar.
        """
        from l2scanner.sessao import ResultadoDoTick

        registro = RegistroEmDisco(tmp_path)
        sessao = self._sessao([SOLO_BOSS], registro)

        primeiro = ResultadoDoTick()
        sessao._processar_agenda(CHAMADA, primeiro)
        assert primeiro.avisos

        # A outra instancia desliga a lista entre um tick e o outro.
        RegistroEmDisco(tmp_path).desligar_lista("Solo Boss")

        segundo = ResultadoDoTick()
        sessao._processar_agenda(datetime(2026, 8, 24, 18, 11), segundo)
        assert segundo.avisos == []


# ---------------------------------------------------------------------------
# PONTO 15 — ponta a ponta, por `atender_comandos`
# ---------------------------------------------------------------------------


class TestNaCostura:
    """Os dois comandos pelo caminho REAL, com as cinco travas ligadas.

    Um parser paralelo montado aqui provaria que o teste concorda consigo
    mesmo.
    """

    TELEFONE = "+5544997077000"

    def _atender(
        self, tmp_path, texto, registro=None, loot=None, conversa="1", ident=909
    ):
        """O `ident` NAO e enfeite: `chave_da_mensagem` grava um marcador
        `comando_<id>` e o segundo comando com o MESMO id seria descartado como
        repetido — que e o dedup fazendo o trabalho dele. Um teste que mande
        dois comandos no mesmo registro tem que dar dois ids, senao afirma o
        contrario do que pensa estar afirmando."""
        import time

        from l2scanner.__main__ import atender_comandos
        from l2scanner.notificador import Despachante, NotificadorEmMemoria

        class LeitorFalso:
            ativo = True
            telefones = [TestNaCostura.TELEFONE]
            membros: list = []

            def ler(self, _):
                return [
                    {
                        "id": ident,
                        "content": texto,
                        "message_type": 0,
                        "private": False,
                        "sender": {
                            "name": "Yazalaque",
                            "phone_number": TestNaCostura.TELEFONE,
                        },
                        "conversation_id": conversa,
                    }
                ]

        notificador = NotificadorEmMemoria()
        despachante = Despachante(notificador)
        registro = registro if registro is not None else RegistroEmDisco(tmp_path)
        atender_comandos(
            LeitorFalso(),
            registro,
            [SOLO_BOSS, TVT],
            despachante,
            CHAMADA,
            time.monotonic(),
            loot=loot,
        )
        despachante.iniciar()
        despachante.encerrar()
        return registro, notificador

    def test_desativarlista_desliga_de_verdade(self, tmp_path):
        registro, _ = self._atender(tmp_path, "/desativarlista")
        assert registro.listas_desligadas() == frozenset({SLUG})

    def test_e_o_gate_da_CHAMADA_morde_no_mesmo_registro(self, tmp_path):
        registro, _ = self._atender(tmp_path, "/desativarlista")
        assert _tipos(CHAMADA, [SOLO_BOSS], registro.listas_desligadas()) == []

    def test_e_o_LEMBRETE_atravessa_o_mesmo_registro(self, tmp_path):
        """O pedido inteiro, provado no fim do caminho de verdade."""
        registro, _ = self._atender(tmp_path, "/desativarlista")
        assert _tipos(LEMBRETE, [SOLO_BOSS], registro.listas_desligadas()) == [
            TipoDeAviso.ANTES
        ]

    def test_ativarlista_religa(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        registro.desligar_lista("Solo Boss")

        self._atender(tmp_path, "/ativarlista", registro=registro)

        assert registro.listas_desligadas() == frozenset()
        assert _tipos(CHAMADA, [SOLO_BOSS], registro.listas_desligadas()) == [
            TipoDeAviso.CHAMADA
        ]

    def test_o_GRUPO_e_avisado_de_que_a_lista_caiu(self, tmp_path):
        """Muda o que TODO MUNDO recebe daqui pra frente: as 12 chamadas
        diarias param. Fazer isso em segredo e a versao coletiva do estado
        escondido."""
        _, notificador = self._atender(tmp_path, "/desativarlista")
        alvos = [alvo for _, alvo in notificador.destinos]

        assert "1" in alvos, "quem pediu nao recebeu confirmacao"
        assert None in alvos, "o grupo nao ficou sabendo que a lista caiu"

    def test_o_GRUPO_e_avisado_de_que_a_lista_voltou(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        registro.desligar_lista("Solo Boss")
        _, notificador = self._atender(tmp_path, "/ativarlista", registro=registro)

        assert None in [alvo for _, alvo in notificador.destinos]

    def test_o_loot_designar_recusa_pelo_caminho_real(self, tmp_path):
        from l2scanner.loot import RegistroDeLoot

        registro = RegistroEmDisco(tmp_path)
        registro.desligar_lista("Solo Boss")
        loot = RegistroDeLoot(tmp_path / "loot")

        _, notificador = self._atender(
            tmp_path, "/loot-J4guar", registro=registro, loot=loot
        )

        assert loot.designacao() is None
        assert any("desligada" in texto.lower() for texto, _ in notificador.destinos)

    def test_com_a_lista_ligada_o_loot_designar_continua_gravando(self, tmp_path):
        from l2scanner.loot import RegistroDeLoot

        loot = RegistroDeLoot(tmp_path / "loot")
        self._atender(tmp_path, "/loot-J4guar", loot=loot)

        assert loot.designacao() is not None

    def test_as_duas_chaves_convivem_pelo_caminho_real(self, tmp_path):
        """Nenhuma precedencia: as duas valem, cada uma no que alcanca."""
        registro = RegistroEmDisco(tmp_path)
        self._atender(tmp_path, "/desativarsoloboss", registro=registro, ident=1)
        self._atender(tmp_path, "/desativarlista", registro=registro, ident=2)

        assert registro.eventos_calados() == frozenset({SLUG})
        assert registro.listas_desligadas() == frozenset({SLUG})

    def test_religar_a_lista_nao_religa_os_avisos(self, tmp_path):
        registro = RegistroEmDisco(tmp_path)
        registro.calar_evento("Solo Boss")
        registro.desligar_lista("Solo Boss")

        self._atender(tmp_path, "/ativarlista", registro=registro)

        assert registro.listas_desligadas() == frozenset()
        assert registro.eventos_calados() == frozenset({SLUG})
