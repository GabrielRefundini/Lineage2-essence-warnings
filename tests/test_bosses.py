"""O aviso de boss e conservador: um nascimento, uma mensagem.

O CONTRATO DE MIGRACAO DOS 7 TESTES (D-12), escrito aqui porque quem abrir
este arquivo daqui a seis meses vai perguntar por que os literais mudaram.

O CONTEXT da Fase 1 travou "os 7 testes de `tests/test_tiat.py` migram
INTACTOS — so o import muda". Isso e literalmente impossivel, e a
impossibilidade E o objetivo da fase: quatro deles alimentavam o vigia com
`Raid boss Tiat has appeared`, `Tiat`, `TIAT apareceu` e `T1A7 apareceu`, e
RECO-01 existe justamente para que esses textos PAREM de disparar. Um teste
que continuasse verde com aqueles literais provaria que RECO-01 nao foi
implementado.

O que a restricao PROTEGE — e o que este arquivo preserva integralmente — e o
DEBOUNCE, que e o ativo mais valioso do modulo:

- Os 7 nomes de funcao sobrevivem literalmente. Nenhum apagado, nenhum
  renomeado.
- A aritmetica sobrevive byte a byte: o `== 1` de
  `test_persistencia_do_chat_ou_alvo_nunca_spamma` continua `== 1`, e o lado
  direito de `test_so_rearma_depois_de_duas_leituras_limpas` continua sendo
  `[True, False, False, True]`, na mesma ordem.
- So tres categorias de edicao mecanica foram permitidas: (a) a linha de
  import; (b) os literais entregues ao `Leitor`, porque a definicao do gatilho
  e o que esta fase muda; (c) a adaptacao de `is None` / `is not None` para
  contagem de itens, porque `avaliar` passou a devolver LISTA para que o
  criterio 4 possa emitir dois avisos num tick.
- A categoria (b) e restrita pela INTENCAO: onde o literal antigo DEVIA
  disparar, o novo e o anuncio COMPLETO de um boss do roster (ou, no recorte
  do alvo, o nome completo dele); onde o antigo NAO devia disparar, o novo
  continua nao sendo anuncio; onde o antigo era a string vazia que produz uma
  leitura limpa, ela continua vazia. A POSICAO de cada literal na sequencia do
  `Leitor` nao mudou: o terceiro texto continua sendo o terceiro texto.
- Nenhuma asseracao foi enfraquecida. `sum(len(a) for a in avisos) == 1` conta
  AVISOS e nao ticks-com-aviso, que e mais forte que o `is not None` original.

UM DESVIO DECLARADO, e a razao: `test_falha_do_ocr_nao_derruba_o_vigia`
constroi o vigia direto (nao pelo helper `vigia`), entao ele recebeu o mesmo
roster padrao que o helper ganhou. Sem isso a asseracao viraria VAZIA — um
vigia com roster vazio nao tem como emitir aviso nenhum, e o teste passaria
mesmo que o `except` do OCR tivesse sido apagado. O desvio deixa o teste mais
forte, nunca mais fraco.
"""

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from l2scanner.bosses import (
    Boss,
    BossInvalido,
    OrigemDoAviso,
    VigiaDeBosses,
    padrao_do_anuncio,
    padrao_do_nome,
)
from l2scanner.config import ler_bosses


PIXELS = np.zeros((5, 5, 3), dtype=np.uint8)
AGORA = datetime(2026, 8, 29, 12, 0)

RAIZ = Path(__file__).resolve().parent.parent

NORTH = Boss(nome="Tiat North", respawn_horas_min=6, respawn_horas_max=8)
SOUTH = Boss(nome="Tiat South", respawn_horas_min=6, respawn_horas_max=8)

# A frase real, medida do print do usuario em 2026-08-30. O ROADMAP supunha
# `[Lv. 80]`; o print mostra 60 — e por isso que o numero do nivel nao entra em
# decisao nenhuma (D-11).
ANUNCIO = "Tiat North [Lv. 60] has spawned!"
# A mesma frase como o OCR a degrada (criterio 3 do ROADMAP). O segundo
# caractere do nivel e a LETRA O, e nao um zero: um `\d+` reprovaria aqui.
ANUNCIO_TORTO = "T1a7 Nor7h [Lv. 8O] has spawned!"


class Leitor:
    def __init__(self, textos):
        self.textos = iter(textos)

    def __call__(self, _pixels):
        return next(self.textos)


def vigia(chat, alvo, bosses=(NORTH,), **kwargs):
    """Cada avaliacao le chat primeiro e alvo depois."""
    textos = [valor for par in zip(chat, alvo) for valor in par]
    return VigiaDeBosses(
        Leitor(textos), bosses=bosses, segundos_entre_leituras=1, **kwargs
    )


# ---------------------------------------------------------------------------
# Os 7 testes migrados de `tests/test_tiat.py`, sob o contrato acima.
# ---------------------------------------------------------------------------


def test_detecta_o_anuncio_no_chat():
    v = vigia([ANUNCIO], ["Orc"])

    avisos = v.avaliar(PIXELS, PIXELS, AGORA)

    assert len(avisos) == 1
    assert avisos[0].origem is OrigemDoAviso.CHAT
    assert "chat" in avisos[0].texto.lower()


def test_detecta_quando_o_alvo_vira_tiat_mesmo_sem_anuncio_no_chat():
    v = vigia(["mensagem comum"], ["Tiat North"])

    avisos = v.avaliar(PIXELS, PIXELS, AGORA)

    assert len(avisos) == 1
    assert avisos[0].origem is OrigemDoAviso.ALVO
    assert "alvo" in avisos[0].texto.lower()


def test_sinais_juntos_geram_uma_mensagem_combinada():
    v = vigia([ANUNCIO], ["Tiat North"])

    avisos = v.avaliar(PIXELS, PIXELS, AGORA)

    assert len(avisos) == 1
    assert avisos[0].origem is OrigemDoAviso.CHAT_E_ALVO


def test_trocas_classicas_do_ocr_ainda_encontram_o_nome():
    v = vigia([ANUNCIO_TORTO], ["nenhum"])

    assert len(v.avaliar(PIXELS, PIXELS, AGORA)) == 1


def test_persistencia_do_chat_ou_alvo_nunca_spamma():
    v = vigia(
        [ANUNCIO, ANUNCIO, ANUNCIO],
        ["Tiat North", "Tiat North", "Tiat North"],
    )

    avisos = [
        v.avaliar(PIXELS, PIXELS, AGORA + timedelta(seconds=segundo))
        for segundo in range(3)
    ]

    assert sum(len(aviso) for aviso in avisos) == 1


def test_so_rearma_depois_de_duas_leituras_limpas():
    v = vigia(
        [ANUNCIO, "", "", ANUNCIO], ["", "", "", ""],
        leituras_limpas_para_rearmar=2,
    )

    avisos = [
        v.avaliar(PIXELS, PIXELS, AGORA + timedelta(seconds=segundo))
        for segundo in range(4)
    ]

    assert [bool(a) for a in avisos] == [True, False, False, True]


def test_falha_do_ocr_nao_derruba_o_vigia():
    def explode(_pixels):
        raise RuntimeError("OCR indisponivel")

    v = VigiaDeBosses(explode, bosses=(NORTH,))

    assert v.avaliar(PIXELS, PIXELS, AGORA) == []


# ---------------------------------------------------------------------------
# O par de guarda do contrato: a mudanca de FORMA que o criterio 4 exige.
# ---------------------------------------------------------------------------


def test_dois_bosses_no_mesmo_tick_produzem_dois_avisos():
    """Sem este teste, a mudanca de assinatura seria regressao nao afirmada.

    Um retorno unico nao carrega dois avisos, e o criterio 4 exige que chat e
    alvo mostrando bosses DIFERENTES produzam um alerta para cada. Este e o
    unico teste que quebra se alguem "simplificar" `avaliar` de volta para um
    retorno unico.
    """
    v = vigia([ANUNCIO], ["Tiat South"], bosses=(NORTH, SOUTH))

    avisos = v.avaliar(PIXELS, PIXELS, AGORA)

    assert len(avisos) == 2
    assert [a.boss for a in avisos] == ["Tiat North", "Tiat South"]
    assert avisos[0].origem is OrigemDoAviso.CHAT
    assert avisos[1].origem is OrigemDoAviso.ALVO


# ---------------------------------------------------------------------------
# RECO-01: o chat digitado por jogador nao dispara mais.
# ---------------------------------------------------------------------------


class TestOAnuncioDoServidorContraOChatDigitado:
    """Os dois sentidos no MESMO arquivo, um por direcao.

    Apertar o padrao contra o chat digitado (RECO-01) e afrouxa-lo contra o OCR
    torto (RECO-04) puxam para lados opostos. Estao juntos aqui para que
    apertar um nunca afrouxe o outro sem alguem ver.
    """

    def test_pergunta_digitada_por_jogador_nao_dispara(self):
        v = vigia(["Fulano: tiat ja nasceu?"], [""])

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []

    def test_nome_solto_no_chat_sem_a_frase_nao_dispara(self):
        v = vigia(["Fulano: alguem viu o Tiat North?"], [""])

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []

    def test_a_frase_completa_dispara(self):
        v = vigia([ANUNCIO], [""])

        assert len(v.avaliar(PIXELS, PIXELS, AGORA)) == 1

    def test_a_frase_sem_a_exclamacao_dispara(self):
        """Pontuacao e o que o OCR mais perde (D-09).

        Exigir o `!` trocaria o falso positivo de hoje por um falso NEGATIVO
        silencioso — pior, porque ninguem percebe que o aviso nao saiu (R-02).
        """
        v = vigia(["Tiat North [Lv. 60] has spawned"], [""])

        assert len(v.avaliar(PIXELS, PIXELS, AGORA)) == 1

    def test_a_frase_sem_os_colchetes_dispara(self):
        v = vigia(["Tiat North Lv. 60 has spawned!"], [""])

        assert len(v.avaliar(PIXELS, PIXELS, AGORA)) == 1

    def test_lixo_do_icone_no_comeco_da_linha_nao_impede_o_casamento(self):
        """O padrao NAO e ancorado no inicio da linha, de proposito.

        A linha do servidor vem com icone proprio, e o OCR de um icone produz
        lixo no comeco da linha. Ancorar trocaria um falso positivo barato por
        um falso negativo silencioso.
        """
        v = vigia(["|]* Tiat North [Lv. 60] has spawned!"], [""])

        assert len(v.avaliar(PIXELS, PIXELS, AGORA)) == 1

    def test_a_frase_e_casada_linha_A_linha_e_nunca_no_blob(self):
        """T-01-02: dois jogadores nao podem costurar um anuncio entre si.

        Sobre o blob inteiro, o `\\s+` da parte fixa emendaria o fim de uma
        linha ao comeco de outra e produziria um casamento que NENHUMA linha
        real contem.
        """
        costura = "Fulano: Tiat North [Lv. 60]\nCicrano: has spawned!"
        v = vigia([costura], [""])

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []


# ---------------------------------------------------------------------------
# RECO-02: a identidade vem do config, nunca do OCR.
# ---------------------------------------------------------------------------


class TestAIdentidadeVemDoConfig:
    def test_south_no_lugar_de_north_nomeia_o_south(self):
        v = vigia(
            ["Tiat South [Lv. 60] has spawned!"], [""], bosses=(NORTH, SOUTH)
        )

        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert len(avisos) == 1
        assert avisos[0].boss == "Tiat South"
        assert avisos[0].texto.startswith("Tiat South")

    def test_a_mensagem_comeca_pelo_nome_do_boss(self):
        """D-14: o nome primeiro, porque e ele que decide para onde a party vai."""
        v = vigia([ANUNCIO], [""])

        assert v.avaliar(PIXELS, PIXELS, AGORA)[0].texto.startswith("Tiat North")

    def test_o_nome_da_mensagem_vem_do_config_e_nunca_do_texto_lido(self):
        """T-01-04: nada escrito por um jogador atravessa para o WhatsApp.

        O texto lido e usado so como predicado booleano e descartado. Aqui o
        anuncio chega cercado de lixo de OCR e de texto de terceiros, e a
        mensagem sai contendo SO o nome configurado.
        """
        sujo = "xX_dr0p_Xx: vem: T1a7 Nor7h [Lv. 8O] has spawned! ##@@"
        v = vigia([sujo], [""])

        aviso = v.avaliar(PIXELS, PIXELS, AGORA)[0]

        assert aviso.boss == "Tiat North"
        assert "dr0p" not in aviso.texto
        assert "T1a7" not in aviso.texto
        assert aviso.texto == "Tiat North nasceu! (visto no chat do jogo)"

    def test_o_alvo_sozinho_nomeia_o_boss(self):
        """RECO-03: o alvo e caminho proprio e nao depende do chat."""
        v = vigia([""], ["Tiat South"], bosses=(NORTH, SOUTH))

        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert len(avisos) == 1
        assert avisos[0].boss == "Tiat South"
        assert avisos[0].origem is OrigemDoAviso.ALVO


# ---------------------------------------------------------------------------
# RECO-05: o rearme deixa de ser um estado unico.
# ---------------------------------------------------------------------------


class TestORearmeEPorBoss:
    def test_o_estado_de_um_boss_nao_desarma_o_outro(self):
        """O caso exato do criterio 4.

        `Tiat South` alvejado durante os minutos em que o anuncio de
        `Tiat North` ainda persiste no recorte do chat NAO pode ser engolido.
        Com um flag global, seria.
        """
        v = vigia(
            [ANUNCIO, ANUNCIO],
            ["", "Tiat South"],
            bosses=(NORTH, SOUTH),
        )

        primeiro = v.avaliar(PIXELS, PIXELS, AGORA)
        segundo = v.avaliar(PIXELS, PIXELS, AGORA + timedelta(seconds=1))

        assert [a.boss for a in primeiro] == ["Tiat North"]
        assert [a.boss for a in segundo] == ["Tiat South"]

    def test_o_rearme_de_um_boss_nao_rearma_o_outro(self):
        """As leituras limpas tambem sao contadas por boss."""
        v = vigia(
            [ANUNCIO, "", "", ANUNCIO],
            ["Tiat South", "Tiat South", "Tiat South", "Tiat South"],
            bosses=(NORTH, SOUTH),
        )

        avisos = [
            v.avaliar(PIXELS, PIXELS, AGORA + timedelta(seconds=segundo))
            for segundo in range(4)
        ]

        # North: anuncio, limpo, limpo, anuncio -> dois avisos.
        # South: presente nos quatro ticks -> um aviso, no primeiro.
        assert [[a.boss for a in tick] for tick in avisos] == [
            ["Tiat North", "Tiat South"],
            [],
            [],
            ["Tiat North"],
        ]

    def test_mesmo_boss_nos_dois_sinais_gera_um_despacho_so(self):
        v = vigia([ANUNCIO], ["Tiat North"], bosses=(NORTH, SOUTH))

        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert len(avisos) == 1
        assert avisos[0].origem is OrigemDoAviso.CHAT_E_ALVO


# ---------------------------------------------------------------------------
# T-01-03: o `nome` do config chega ESCAPADO ao `re.compile`.
# ---------------------------------------------------------------------------


class TestONomeDoConfigNaoViraCuringa:
    def test_metacaractere_no_nome_nao_casa_com_qualquer_coisa(self):
        curinga = Boss(nome="Tiat.*", respawn_horas_min=6, respawn_horas_max=8)
        v = vigia(["Tiatzzz [Lv. 1] has spawned"], [""], bosses=(curinga,))

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []

    def test_o_nome_com_metacaractere_ainda_casa_consigo_mesmo(self):
        curinga = Boss(nome="Tiat.*", respawn_horas_min=6, respawn_horas_max=8)
        v = vigia(["Tiat.* [Lv. 1] has spawned"], [""], bosses=(curinga,))

        assert len(v.avaliar(PIXELS, PIXELS, AGORA)) == 1

    def test_o_padrao_do_nome_tambem_escapa(self):
        assert padrao_do_nome("Tiat.*").search("Tiatzzz") is None
        assert padrao_do_nome("Tiat.*").search("Tiat.*") is not None

    def test_um_nome_com_parentese_nao_quebra_a_compilacao(self):
        """Um nome com `(` cru levantaria `re.error` no ARRANQUE."""
        estranho = Boss(nome="Tiat (N)", respawn_horas_min=6, respawn_horas_max=8)
        v = vigia(["Tiat (N) [Lv. 60] has spawned!"], [""], bosses=(estranho,))

        assert len(v.avaliar(PIXELS, PIXELS, AGORA)) == 1


class TestOPadraoDoAnuncio:
    def test_o_nivel_e_casado_e_descartado(self):
        """D-11: o nivel prova que a linha veio do servidor, e so isso."""
        for nivel in ("60", "80", "8O", "1", "100"):
            frase = f"Tiat North [Lv. {nivel}] has spawned!"
            assert padrao_do_anuncio("Tiat North").search(frase), nivel

    def test_sem_o_nivel_nao_ha_anuncio(self):
        assert padrao_do_anuncio("Tiat North").search(
            "Tiat North has spawned!"
        ) is None

    def test_a_parte_fixa_tambem_tem_folga_de_ocr(self):
        """D-09: `has spawned` degradado continua casando."""
        assert padrao_do_anuncio("Tiat North").search(
            "Tiat North [Lv. 60] ha5 5pawn3d!"
        )


# ---------------------------------------------------------------------------
# VIGI-01 / VIGI-02 / VIGI-03: os blocos `[[boss]]` do config.toml.
# ---------------------------------------------------------------------------


def escrever_config(tmp_path, corpo):
    caminho = tmp_path / "config.toml"
    caminho.write_text(corpo, encoding="utf-8")
    return caminho


class TestLerBosses:
    def test_arquivo_ausente_devolve_lista_vazia_e_nao_e_erro(self, tmp_path):
        """O scanner roda sem `[[boss]]` nenhum desde a v1."""
        assert ler_bosses(tmp_path / "nao_existe.toml") == []

    def test_arquivo_sem_bloco_boss_devolve_lista_vazia(self, tmp_path):
        caminho = escrever_config(tmp_path, "[jogo]\npersonagem = \"Kaus\"\n")

        assert ler_bosses(caminho) == []

    def test_um_bloco_vira_um_boss_validado(self, tmp_path):
        caminho = escrever_config(
            tmp_path,
            '[[boss]]\nnome = "Orfen"\n'
            "respawn_horas_min = 6\nrespawn_horas_max = 8.5\n",
        )

        bosses = ler_bosses(caminho)

        assert len(bosses) == 1
        assert bosses[0].nome == "Orfen"
        assert bosses[0].respawn_horas_min == 6
        assert bosses[0].respawn_horas_max == 8.5

    def test_toml_quebrado_e_erro_de_arranque_e_cita_o_arquivo(self, tmp_path):
        caminho = escrever_config(tmp_path, "[[boss]\nnome =\n")

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "config.toml" in str(erro.value)

    def test_bloco_que_nao_e_bloco_explica_o_formato(self, tmp_path):
        caminho = escrever_config(tmp_path, 'boss = ["Tiat North"]\n')

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "[[boss]]" in str(erro.value)

    def test_dois_blocos_com_o_mesmo_nome_sao_recusados(self, tmp_path):
        """O padrao de OCR e IGNORECASE: `tiat north` e `Tiat North` sao
        indistinguiveis para o vigia, e na Fase 2 dividiriam a mesma ancora.
        """
        caminho = escrever_config(
            tmp_path,
            '[[boss]]\nnome = "Tiat North"\n'
            "respawn_horas_min = 6\nrespawn_horas_max = 8\n"
            '[[boss]]\nnome = "tiat north"\n'
            "respawn_horas_min = 6\nrespawn_horas_max = 8\n",
        )

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "Tiat North" in str(erro.value)


class TestARecusaCitaOBossEOCampo:
    """Criterio 6: nunca sobe vigiando errado em silencio."""

    def escrever(self, tmp_path, linhas):
        return escrever_config(
            tmp_path, '[[boss]]\nnome = "Tiat North"\n' + linhas
        )

    def test_sem_nome(self, tmp_path):
        caminho = escrever_config(
            tmp_path,
            "[[boss]]\nrespawn_horas_min = 6\nrespawn_horas_max = 8\n",
        )

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "nome" in str(erro.value)
        assert "[[boss]] #1" in str(erro.value)

    def test_sem_respawn_horas_min(self, tmp_path):
        caminho = self.escrever(tmp_path, "respawn_horas_max = 8\n")

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "respawn_horas_min" in str(erro.value)
        assert "Tiat North" in str(erro.value)

    def test_sem_respawn_horas_max(self, tmp_path):
        caminho = self.escrever(tmp_path, "respawn_horas_min = 6\n")

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "respawn_horas_max" in str(erro.value)
        assert "Tiat North" in str(erro.value)

    def test_booleano_e_recusado_antes_do_teste_numerico(self, tmp_path):
        """`isinstance(True, int)` e verdadeiro em Python.

        Sem a recusa explicita, `respawn_horas_min = true` passaria como
        "1 hora" — uma janela errada, sem um unico erro no console. E o mesmo
        buraco que o comentario de `chamar_minutos_antes` documenta.
        """
        caminho = self.escrever(
            tmp_path, "respawn_horas_min = true\nrespawn_horas_max = 8\n"
        )

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "respawn_horas_min" in str(erro.value)
        assert "Tiat North" in str(erro.value)

    def test_texto_no_lugar_de_numero(self, tmp_path):
        caminho = self.escrever(
            tmp_path, 'respawn_horas_min = "seis"\nrespawn_horas_max = 8\n'
        )

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "respawn_horas_min" in str(erro.value)

    def test_horas_negativas(self, tmp_path):
        caminho = self.escrever(
            tmp_path, "respawn_horas_min = -6\nrespawn_horas_max = 8\n"
        )

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "respawn_horas_min" in str(erro.value)

    def test_zero_e_recusado_junto_com_negativo(self, tmp_path):
        """Uma regra de respawn de zero hora nao descreve nada."""
        caminho = self.escrever(
            tmp_path, "respawn_horas_min = 0\nrespawn_horas_max = 8\n"
        )

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "respawn_horas_min" in str(erro.value)

    def test_max_menor_que_min_cita_os_dois_valores(self, tmp_path):
        caminho = self.escrever(
            tmp_path, "respawn_horas_min = 8\nrespawn_horas_max = 6\n"
        )

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        mensagem = str(erro.value)
        assert "respawn_horas_max" in mensagem
        assert "Tiat North" in mensagem
        assert "8" in mensagem and "6" in mensagem


# ---------------------------------------------------------------------------
# A FATIA VERTICAL: do arquivo do repositorio ate a mensagem pronta.
# ---------------------------------------------------------------------------


class TestOConfigDoRepositorioProduzOAviso:
    """O roster vem do ARQUIVO, e e isso que torna isto uma fatia vertical.

    Um roster escrito a mao no teste provaria so que a classe funciona. Este
    conjunto prova que editar o `config.toml` — e nada mais — muda o que o
    usuario recebe no WhatsApp.
    """

    @pytest.fixture
    def roster(self):
        return ler_bosses(RAIZ / "config.toml")

    def test_o_arquivo_do_repositorio_tem_os_dois_tiat_com_6_e_8(self, roster):
        assert [b.nome for b in roster] == ["Tiat North", "Tiat South"]
        assert all(b.respawn_horas_min == 6 for b in roster)
        assert all(b.respawn_horas_max == 8 for b in roster)

    def test_o_anuncio_produz_um_aviso_que_nomeia_o_boss(self, roster):
        v = vigia([ANUNCIO], [""], bosses=roster)

        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert len(avisos) == 1
        assert avisos[0].boss == "Tiat North"
        assert avisos[0].texto.startswith("Tiat North")

    def test_a_pergunta_digitada_nao_produz_aviso_nenhum(self, roster):
        v = vigia(["Fulano: tiat ja nasceu?"], [""], bosses=roster)

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []

    def test_trocando_north_por_south_o_aviso_nomeia_o_south(self, roster):
        v = vigia(["Tiat South [Lv. 60] has spawned!"], [""], bosses=roster)

        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert len(avisos) == 1
        assert avisos[0].texto.startswith("Tiat South")

    def test_chat_com_um_boss_e_alvo_com_outro_produzem_dois_avisos(self, roster):
        v = vigia([ANUNCIO], ["Tiat South"], bosses=roster)

        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert {a.boss for a in avisos} == {"Tiat North", "Tiat South"}


# ---------------------------------------------------------------------------
# VIGI-04: o arranque monta o vigia, ou diz por que nao montou.
# ---------------------------------------------------------------------------


class TestOArranque:
    """Tenta, degrada com log, devolve `None`, e o scanner sobe do mesmo jeito.

    A ordem das recusas importa: lista vazia vem PRIMEIRO porque e a recusa
    mais informativa — sem bloco nenhum nao ha o que vigiar, mesmo com tudo o
    mais calibrado, e mandar o usuario recalibrar seria mandar consertar o que
    nao esta quebrado.
    """

    @pytest.fixture
    def cal_sem_recorte(self):
        """Uma calibracao real do repositorio, sem os recortes de chat/alvo."""
        from dataclasses import replace

        from l2scanner.calibracao import Calibracao

        crua = Calibracao.carregar(
            RAIZ / "tests" / "fixtures" / "party_estavel_com_vazamento"
            / "calibracao.json"
        )
        return replace(crua, tiat_chat=None, tiat_alvo=None)

    @pytest.fixture
    def cal(self, cal_sem_recorte):
        from dataclasses import replace

        from l2scanner.frames import Regiao

        recorte = Regiao(esquerda=10, topo=20, largura=300, altura=80)
        return replace(cal_sem_recorte, tiat_chat=recorte, tiat_alvo=recorte)

    def montar(self, cal, bosses, caplog, disponivel=True):
        """O OCR e FORCADO nos dois sentidos, e nao herdado do ambiente.

        As bindings de OCR do Windows nao estao instaladas em todo lugar onde a
        suite roda. Sem forcar, o caminho "tudo pronto" nunca seria exercitado
        numa maquina sem elas — e o teste passaria sem provar nada.
        """
        import logging

        from l2scanner import __main__ as principal

        original = principal.ocr.disponivel
        principal.ocr.disponivel = lambda: disponivel
        try:
            with caplog.at_level(logging.INFO, logger=principal.log.name):
                return principal.montar_vigia_de_bosses(
                    cal, na_janela=True, bosses=bosses
                )
        finally:
            principal.ocr.disponivel = original

    def test_sem_bloco_nenhum_o_scanner_sobe_e_o_log_diz_como_ligar(
        self, cal, caplog
    ):
        """Criterio 7: seccao ausente nao e erro, e o console explica."""
        assert self.montar(cal, [], caplog) is None

        texto = caplog.text
        assert "[[boss]]" in texto
        assert "nome" in texto
        assert "respawn_horas_min" in texto
        assert "respawn_horas_max" in texto
        # `info`, e nao `warning`: nao ter bloco nenhum nao e erro.
        assert all(
            r.levelname == "INFO"
            for r in caplog.records
            if "[[boss]]" in r.getMessage()
        )

    def test_com_bosses_mas_sem_recorte_calibrado_devolve_none(
        self, cal_sem_recorte, caplog
    ):
        assert self.montar(cal_sem_recorte, [NORTH], caplog) is None
        assert "calibrar-tiat" in caplog.text

    def test_com_bosses_e_sem_ocr_devolve_none(self, cal, caplog):
        assert self.montar(cal, [NORTH], caplog, disponivel=False) is None

    def test_a_linha_de_ativo_nomeia_os_bosses_vigiados(self, cal, caplog):
        """A metade de OPER-02 que esta fase entrega.

        A Fase 2 completa a outra metade acrescentando a proxima janela
        prevista, e por isso a linha ja nasce com o NOME como ancora do texto —
        nao a reescreva como uma contagem.
        """
        v = self.montar(cal, [NORTH, SOUTH], caplog)

        assert v is not None
        assert "Tiat North" in caplog.text
        assert "Tiat South" in caplog.text

    def test_o_vigia_montado_ja_reconhece_o_anuncio(self, cal, caplog):
        """Guarda contra montar um vigia com roster vazio por engano."""
        v = self.montar(cal, [NORTH], caplog)

        v._ler_texto = lambda pixels: ANUNCIO if pixels is PIXELS else ""
        avisos = v.avaliar(PIXELS, None, AGORA)

        assert [a.boss for a in avisos] == ["Tiat North"]

    def test_nenhum_simbolo_antigo_sobreviveu_no_main(self):
        """`VigiaDoTiat` e `montar_vigia_do_tiat` nao existem mais."""
        from l2scanner import __main__ as principal

        fonte = Path(principal.__file__).read_text(encoding="utf-8")
        assert "VigiaDoTiat" not in fonte
        assert "montar_vigia_do_tiat" not in fonte

    def test_um_bloco_torto_derruba_o_arranque_com_codigo_2(
        self, monkeypatch, caplog
    ):
        """Criterio 6: nenhum traceback chega ao usuario.

        A recusa de config sai como UMA linha de erro legivel e o processo
        devolve 2 — o mesmo desfecho de `CalibracaoInvalida` e de
        `ConfiguracaoPerigosa`, que sao as outras duas recusas de configuracao
        do projeto.
        """
        import logging
        import sys

        from l2scanner import __main__ as principal

        recusa = BossInvalido(
            "boss 'Tiat North': falta o campo 'respawn_horas_min'."
        )

        def explode(*_args, **_kwargs):
            raise recusa

        monkeypatch.setattr(principal, "laco_principal", explode)
        monkeypatch.setattr(
            principal,
            "ARQUIVO_CALIBRACAO",
            RAIZ / "tests" / "fixtures" / "party_estavel_com_vazamento"
            / "calibracao.json",
        )
        # `--replay` pula a conferencia de geometria da tela: uma sessao
        # gravada foi feita noutra hora.
        monkeypatch.setattr(sys, "argv", ["l2scanner", "--replay", "nao-usada"])

        with caplog.at_level(logging.ERROR, logger=principal.log.name):
            codigo = principal.main()

        assert codigo == 2
        assert "Tiat North" in caplog.text
        assert "respawn_horas_min" in caplog.text
