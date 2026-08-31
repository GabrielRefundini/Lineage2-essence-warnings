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

import re
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

    def test_o_nome_e_o_nivel_sem_has_spawned_nao_disparam(self):
        """Metade da frase nao e a frase.

        `Tiat North [Lv. 60]` e o que um jogador colaria no chat ao perguntar
        de qual boss se trata. Sem `has spawned` nao houve anuncio nenhum.
        """
        v = vigia(["Tiat North [Lv. 60]"], [""])

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []

    def test_a_frase_sem_nome_de_boss_nao_dispara(self):
        """O nome do boss e obrigatorio, e vem do config.

        Sem ele nao ha o que anunciar — e nao haveria o que escrever na
        mensagem, porque o nome despachado sai sempre do `[[boss]]` (T-01-04).
        """
        v = vigia(["[Lv. 60] has spawned!"], [""])

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []

    def test_o_anuncio_de_um_boss_fora_do_config_nao_dispara(self):
        """VIGI-01 pelo avesso: quem nao esta na lista nao e vigiado.

        O servidor anuncia dezenas de mobs por noite. Vigiar todos
        transformaria o grupo de WhatsApp em log do jogo, e a mensagem que
        importa se perderia no meio.
        """
        v = vigia(["Orfen [Lv. 70] has spawned!"], [""], bosses=(NORTH, SOUTH))

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []

    def test_a_notificacao_de_mercado_nao_e_confundida_com_o_anuncio(self):
        """O falso positivo REAL, medido nos prints do usuario.

        Esta linha e a mais perigosa do arquivo inteiro, e nao a pergunta
        digitada. Ela e uma linha de SISTEMA do mesmo chat: mesmo icone de
        sino, colchetes, e um numero DENTRO dos colchetes. Ela compartilha a
        estrutura visual do anuncio verdadeiro, entao um humano lendo a regex
        nao percebe que ela quase casa.

        Hoje o padrao a rejeita porque falta `has spawned`. Isso e
        COINCIDENCIA ate estar escrito aqui: qualquer afrouxamento futuro da
        parte fixa passaria a aceita-la, e o grupo receberia um aviso de boss
        toda vez que alguem vendesse um item.
        """
        mercado = "-> Dragon Belt - 1 pcs: added on the market [15,54 XM Coin]"
        v = vigia([mercado], [""], bosses=(NORTH, SOUTH))

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []

    def test_um_nivel_digitado_por_jogador_sem_colchetes_nao_dispara(self):
        """Do mesmo print: `LVL 62` num anuncio de procura de party.

        Os colchetes sao opcionais no padrao (o OCR os perde), entao esta
        linha exercita exatamente a folga que essa decisao abriu. Ela nao
        dispara porque nao tem `has spawned` nem nome de boss configurado.
        """
        procura = "Christine : PROCURO PT EM PLAINS ARCHER LVL 62 127GS"
        v = vigia([procura], [""], bosses=(NORTH, SOUTH))

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []

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
# RECO-04 (criterio 3): a precisao nao custou o reconhecimento do anuncio real.
# ---------------------------------------------------------------------------


class TestAFraseTortaEAFraseLimpaProduzemOMesmoAviso:
    """Criterio 3 afirmado como EQUIVALENCIA, e nao como "a torta dispara".

    Um teste que so afirma "a frase torta dispara" continuaria verde se ela
    disparasse nomeando o boss ERRADO — e nomear o boss errado manda a party
    para o outro lado do mapa, que e pior do que nao avisar. A asseracao aqui e
    que os dois caminhos chegam ao MESMO aviso, texto e origem inclusive.
    """

    def _aviso(self, texto, bosses=(NORTH, SOUTH)):
        v = vigia([texto], [""], bosses=bosses)
        avisos = v.avaliar(PIXELS, PIXELS, AGORA)
        assert len(avisos) == 1, texto
        return avisos[0]

    def test_a_letra_O_no_lugar_do_zero_nao_muda_nada(self):
        """`[Lv. 8O]` — o segundo caractere do nivel e a LETRA O.

        E o exemplo literal do criterio 3 do ROADMAP. Um `\\d+` reprovaria
        aqui, e reprovaria em SILENCIO: o alerta simplesmente nao sairia e
        ninguem perceberia que ele nao saiu (R-02).
        """
        limpo = self._aviso(ANUNCIO)
        torto = self._aviso(ANUNCIO_TORTO)

        assert torto.boss == limpo.boss == "Tiat North"
        assert torto.texto == limpo.texto
        assert torto.origem is limpo.origem

    def test_o_south_torto_continua_sendo_o_south(self):
        """A parte fixa degradada junto com o nome (D-09)."""
        torto = self._aviso("T1a7 Sou7h [Lv. 6O] ha5 5pawn3d!")

        assert torto.boss == "Tiat South"
        assert torto.texto.startswith("Tiat South")

    @pytest.mark.parametrize("nivel", ["60", "80", "1", "8O", "l00"])
    def test_o_nivel_nao_entra_na_identidade(self, nivel):
        """D-11: o nivel prova que a linha veio do servidor, e so isso.

        Se o servidor mudar o nivel do Tiat numa atualizacao, nada quebra e
        ninguem precisa editar o config.
        """
        aviso = self._aviso(f"Tiat North [Lv. {nivel}] has spawned!")

        assert aviso.boss == "Tiat North"


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

    def test_nem_um_comando_nem_um_endereco_atravessam_para_a_mensagem(self):
        """T-01-04 no formato mais hostil que o chat do jogo permite.

        Um jogador escreve o que quiser no chat geral, inclusive algo que
        pareca comando ou endereco. O recorte inteiro e PREDICADO BOOLEANO: ou
        ha anuncio naquela linha, ou nao ha. Nada do que foi LIDO viaja para o
        grupo de WhatsApp, porque o nome interpolado sai do `[[boss]]`.
        """
        hostil = (
            "!kick @all http://nao-clique.example/x "
            "Tiat North [Lv. 60] has spawned!"
        )
        v = vigia([hostil], [""])

        aviso = v.avaliar(PIXELS, PIXELS, AGORA)[0]

        assert aviso.texto == "Tiat North nasceu! (visto no chat do jogo)"
        for vazamento in ("!kick", "@all", "http", "example"):
            assert vazamento not in aviso.texto

    def test_o_alvo_sozinho_nomeia_o_boss(self):
        """RECO-03: o alvo e caminho proprio e nao depende do chat."""
        v = vigia([""], ["Tiat South"], bosses=(NORTH, SOUTH))

        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert len(avisos) == 1
        assert avisos[0].boss == "Tiat South"
        assert avisos[0].origem is OrigemDoAviso.ALVO


# ---------------------------------------------------------------------------
# RECO-03 (criterio 2): o alvo e um caminho proprio.
# ---------------------------------------------------------------------------


class TestOCaminhoDoAlvo:
    """O recorte do alvo nao tem frase nenhuma — so o nome.

    Por isso ele NAO passa por `padrao_do_anuncio`, e por isso a identificacao
    ali e estruturalmente mais fragil: nao existe `[Lv. NN] has spawned`
    provando que aquele texto veio do servidor. A defesa e exigir o nome
    COMPLETO do boss e recusar o empate.
    """

    def test_o_alvo_dispara_com_o_chat_mudo(self):
        """Criterio 2: nao depende de o chat ter anunciado nada."""
        v = vigia([""], ["Tiat South"], bosses=(NORTH, SOUTH))

        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert [(a.boss, a.origem) for a in avisos] == [
            ("Tiat South", OrigemDoAviso.ALVO)
        ]

    def test_o_alvo_degradado_pelo_ocr_nomeia_o_mesmo_boss(self):
        """A mesma folga do chat vale no alvo — e a mesma funcao a monta."""
        v = vigia([""], ["T1a7 Sou7h"], bosses=(NORTH, SOUTH))

        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert [a.boss for a in avisos] == ["Tiat South"]

    def test_um_alvo_truncado_nao_escolhe_entre_dois_bosses(self):
        """`Tiat` sozinho, com `Tiat North` e `Tiat South` na lista.

        Escolher um dos dois seria chutar, e o chute manda a party para o outro
        lado do mapa. O nome do alvo tem que estar COMPLETO — e nao estando,
        o silencio e a resposta correta, nao uma degradacao.
        """
        v = vigia([""], ["Tiat"], bosses=(NORTH, SOUTH))

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []

    def test_dois_bosses_casando_o_mesmo_trecho_do_alvo_nao_produzem_aviso(self):
        """A REGRA DE DESEMPATE: empate no mesmo trecho e silencio.

        Um alvo e UM mob. Se dois `[[boss]]` casam trechos que se sobrepoem no
        mesmo texto de alvo, no maximo um deles e o alvo de verdade e nao ha
        como saber qual. Dois avisos seriam um deles comprovadamente falso; um
        aviso escolhido pela ordem do config seria um chute com cara de
        certeza — e na Fase 2 esse chute vira ancora em disco.
        """
        generico = Boss(nome="Tiat", respawn_horas_min=6, respawn_horas_max=8)
        v = vigia([""], ["Tiat North"], bosses=(generico, NORTH))

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []

    def test_o_empate_no_alvo_nao_apaga_o_anuncio_do_chat(self):
        """O desempate e SO do caminho do alvo, e essa fronteira e a decisao.

        O chat traz `[Lv. NN] has spawned` provando a origem da linha: nao ha
        ambiguidade a resolver ali. Apagar o anuncio por causa de um empate
        NOUTRO recorte trocaria um falso positivo barato por um falso negativo
        silencioso, que e o erro caro (R-02).
        """
        generico = Boss(nome="Tiat", respawn_horas_min=6, respawn_horas_max=8)
        v = vigia([ANUNCIO], ["Tiat North"], bosses=(generico, NORTH))

        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert [(a.boss, a.origem) for a in avisos] == [
            ("Tiat North", OrigemDoAviso.CHAT)
        ]


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

    def test_o_south_alvejado_no_terceiro_tick_nao_e_engolido(self):
        """O caso de campo inteiro, e nao so dois ticks.

        A linha do anuncio de `Tiat North` fica MINUTOS no recorte do chat. Com
        um flag unico de rearme, qualquer boss alvejado durante esses minutos
        seria engolido — e um alerta que nunca saiu nao deixa rastro nenhum
        para alguem notar.
        """
        v = vigia(
            [ANUNCIO, ANUNCIO, ANUNCIO, ANUNCIO],
            ["", "", "Tiat South", "Tiat South"],
            bosses=(NORTH, SOUTH),
        )

        avisos = [
            v.avaliar(PIXELS, PIXELS, AGORA + timedelta(seconds=segundo))
            for segundo in range(4)
        ]

        assert [[a.boss for a in tick] for tick in avisos] == [
            ["Tiat North"],
            [],
            ["Tiat South"],
            [],
        ]

    def test_mesmo_boss_nos_dois_sinais_gera_um_despacho_so(self):
        v = vigia([ANUNCIO], ["Tiat North"], bosses=(NORTH, SOUTH))

        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert len(avisos) == 1
        assert avisos[0].origem is OrigemDoAviso.CHAT_E_ALVO


# ---------------------------------------------------------------------------
# D-24 (criterio 2 da Fase 3): o rearme deixa de ser um estado por BOSS e
# passa a ser um estado por CANAL.
# ---------------------------------------------------------------------------


class TestOChatNaoEEngolidoPeloAlvo:
    """O anuncio do servidor nao pode ser descartado dentro do vigia.

    O modo de falha que esta classe impede e um alerta que NUNCA SAIU — a
    mesma familia de defeito que
    `test_o_south_alvejado_no_terceiro_tick_nao_e_engolido` ja nomeia, agora
    num segundo eixo. Com um flag unico por boss, o usuario segurando
    `Tiat North` no alvo por minutos deixava `_armado` em `False`, e a frase
    do servidor chegando no chat era jogada fora antes de qualquer disco: sem
    ancora, sem `ResultadoDoTick`, sem log. Nada para alguem notar.

    A razao e do usuario e foi ditada junto com a regra (D-24): o chat SEMPRE
    avisa, "pois eu posso estar longe do computador". O anuncio do servidor e
    o unico sinal que existe quando ninguem esta olhando a tela; o alvo exige
    alguem na frente do computador.
    """

    def test_o_anuncio_do_chat_atravessa_o_alvo_segurado(self):
        """O caso de campo: o boss fica selecionado, e o servidor anuncia."""
        v = vigia(
            ["", "", ANUNCIO],
            ["Tiat North", "Tiat North", "Tiat North"],
        )

        avisos = [
            v.avaliar(PIXELS, PIXELS, AGORA + timedelta(seconds=segundo))
            for segundo in range(3)
        ]

        assert [[a.boss for a in tick] for tick in avisos] == [
            ["Tiat North"],
            [],
            ["Tiat North"],
        ]

    def test_a_origem_do_aviso_que_atravessa_vem_da_PRESENCA(self):
        """D-31: a presenca decide a ORIGEM, o canal decide se HA aviso.

        O aviso do terceiro tick e `CHAT_E_ALVO` e nao `CHAT`, porque os dois
        sinais estao na tela. A origem vira nome de arquivo de ancora (D-18) e
        ramifica o texto da mensagem de janela horas depois (D-16):
        deriva-la de "qual canal armou" mudaria a distribuicao das ancoras sem
        uma linha de `respawn.py` mudar e sem um teste de la ficar vermelho.
        """
        v = vigia(
            ["", "", ANUNCIO],
            ["Tiat North", "Tiat North", "Tiat North"],
        )

        avisos = [
            v.avaliar(PIXELS, PIXELS, AGORA + timedelta(seconds=segundo))
            for segundo in range(3)
        ]

        assert avisos[0][0].origem is OrigemDoAviso.ALVO
        assert avisos[2][0].origem is OrigemDoAviso.CHAT_E_ALVO

    def test_o_alvo_tambem_nao_e_engolido_pelo_chat(self):
        """O caso SIMETRICO, para a mudanca nao valer num sentido so.

        O efeito colateral aceito e uma ancora de origem `alvo` a mais, que e
        o custo ja apresentado e aceito de D-15 (T-03-11). Nenhuma tarefa
        desta fase toca `ancoras_mais_recentes` nem `_PESO_DA_ORIGEM`.
        """
        v = vigia(
            [ANUNCIO, ANUNCIO, ANUNCIO],
            ["", "", "Tiat North"],
        )

        avisos = [
            v.avaliar(PIXELS, PIXELS, AGORA + timedelta(seconds=segundo))
            for segundo in range(3)
        ]

        assert [[(a.boss, a.origem) for a in tick] for tick in avisos] == [
            [("Tiat North", OrigemDoAviso.CHAT)],
            [],
            [("Tiat North", OrigemDoAviso.CHAT_E_ALVO)],
        ]

    def test_os_dois_canais_armados_produzem_UM_aviso_so(self):
        """RECO-05 da Fase 1, intacto: um boss, no maximo um aviso por tick.

        Partir o ESTADO em dois nao pode partir a SAIDA em dois — seriam duas
        mensagens de WhatsApp para o mesmo nascimento, que e exatamente o
        defeito que esta fase esta consertando.
        """
        v = vigia([ANUNCIO], ["Tiat North"])

        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert len(avisos) == 1
        assert avisos[0].origem is OrigemDoAviso.CHAT_E_ALVO

    def test_o_canal_desarmado_nao_rearma_com_o_outro_sinal_presente(self):
        """A aritmetica do rearme e preservada byte a byte.

        Sao as leituras LIMPAS DAQUELE CANAL que rearmam, e nunca a chegada do
        outro sinal. Sem isto, o anuncio do chat no terceiro tick rearmaria o
        alvo de graca e o alvo voltaria a falar sozinho no quarto — spam por
        um caminho novo, no meio do plano que existe para tirar o spam.
        """
        v = vigia(
            ["", "", ANUNCIO, ""],
            ["Tiat North", "Tiat North", "Tiat North", "Tiat North"],
        )

        avisos = [
            v.avaliar(PIXELS, PIXELS, AGORA + timedelta(seconds=segundo))
            for segundo in range(4)
        ]

        assert [[a.boss for a in tick] for tick in avisos] == [
            ["Tiat North"],
            [],
            ["Tiat North"],
            [],
        ]


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


    def test_um_parentese_sem_par_no_nome_nao_quebra_a_compilacao(self):
        """`Tiat(` cru levantaria `re.error` no ARRANQUE.

        Nao e hipotese academica: os padroes sao pre-compilados no construtor
        justamente para um nome torto explodir com o usuario olhando para o
        console. Se a explosao for `re.error` em vez de `BossInvalido`, o
        usuario recebe traceback em vez de instrucao.
        """
        torto = Boss(nome="Tiat(", respawn_horas_min=6, respawn_horas_max=8)
        v = vigia(["Tiat( [Lv. 60] has spawned!"], [""], bosses=(torto,))

        assert len(v.avaliar(PIXELS, PIXELS, AGORA)) == 1

    def test_uma_classe_de_regex_no_nome_casa_literalmente(self):
        """`Tiat[a-z]` e um nome, nao uma classe de caracteres.

        Este e o caso mais insidioso do vetor: `Tiat[a-z]` COMPILA sem erro
        nenhum se concatenado cru, entao nao ha explosao no arranque — o vigia
        sobe e passa a disparar com `Tiata`, `Tiatb`, `Tiatz`, e ninguem
        descobre por que os avisos comecaram a sair errados.
        """
        classe = Boss(nome="Tiat[a-z]", respawn_horas_min=6, respawn_horas_max=8)

        v = vigia(["Tiatx [Lv. 60] has spawned!"], [""], bosses=(classe,))
        assert v.avaliar(PIXELS, PIXELS, AGORA) == []

        v = vigia(["Tiat[a-z] [Lv. 60] has spawned!"], [""], bosses=(classe,))
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


class TestDoisBossesNaoPodemDividirAMesmaAncora:
    """O `nome` do `[[boss]]` virou NOME DE ARQUIVO na Fase 2 (T-02-05).

    Dois nomes que o `casefold` considera DIFERENTES podem reduzir ao MESMO
    apelido, e ai passariam pela recusa por nome e depois compartilhariam a
    mesma ancora em `.agenda/`. O nascimento de um reancoraria a janela do
    outro, em silencio, e nenhuma mensagem estaria errada o bastante para
    alguem desconfiar.
    """

    def dois(self, tmp_path, primeiro, segundo):
        return escrever_config(
            tmp_path,
            f'[[boss]]\nnome = "{primeiro}"\n'
            "respawn_horas_min = 6\nrespawn_horas_max = 8\n"
            f'[[boss]]\nnome = "{segundo}"\n'
            "respawn_horas_min = 6\nrespawn_horas_max = 8\n",
        )

    @pytest.mark.parametrize(
        "primeiro,segundo",
        [
            ("Tiat North", "Tiat  North"),
            ("Tiat North", "Tiat-North"),
            ("Tiat North", "Tiat North!"),
            ("Tiat North", "tiat.north"),
        ],
        ids=["espaco-duplo", "hifen", "pontuacao", "ponto-e-caixa"],
    )
    def test_apelidos_colidentes_recusam_o_arranque(
        self, tmp_path, primeiro, segundo
    ):
        caminho = self.dois(tmp_path, primeiro, segundo)

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)

        mensagem = str(erro.value)
        # A mensagem cita os DOIS nomes: o usuario tem que saber qual par
        # apagar, e "um boss esta repetido" o faria contar blocos.
        assert primeiro in mensagem
        assert segundo in mensagem
        assert "tiat-north" in mensagem

    def test_a_prova_nao_e_vazia_dois_bosses_de_verdade_sobem(self, tmp_path):
        """Sem isto, uma recusa que rejeitasse TUDO passaria nos testes acima.

        `Tiat North` e `Tiat South` sao o par real do `config.toml` do usuario,
        e eles tem que continuar subindo.
        """
        caminho = self.dois(tmp_path, "Tiat North", "Tiat South")

        bosses = ler_bosses(caminho)

        assert [b.nome for b in bosses] == ["Tiat North", "Tiat South"]

    def test_nome_so_de_pontuacao_recusa_o_arranque(self, tmp_path):
        """Um apelido VAZIO produziria um marcador sem identidade."""
        caminho = escrever_config(
            tmp_path,
            '[[boss]]\nnome = "!!!"\n'
            "respawn_horas_min = 6\nrespawn_horas_max = 8\n",
        )

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "!!!" in str(erro.value)


class TestONomeHostilNaoEscapaDaPasta:
    """T-02-04: texto escrito a mao virando caminho no sistema de arquivos.

    `apelido_do_evento` reduz por LISTA DE PERMISSAO (`[^a-z0-9]+` vira hifen),
    entao separador de diretorio, ponto e sequencia de subida de nivel nao
    sobrevivem. Isso hoje e verdade por CONSEQUENCIA; estes testes afirmam por
    contrato, porque a propriedade so passou a importar quando o valor virou
    nome de arquivo.
    """

    @pytest.mark.parametrize(
        "hostil",
        [
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "Tiat/../../North",
            "C:\\Users\\refun\\config",
            "nome com / barra",
        ],
    )
    def test_o_apelido_so_tem_letras_numeros_e_hifen(self, hostil):
        from l2scanner.agenda import apelido_do_evento

        apelido = apelido_do_evento(hostil)

        assert re.fullmatch(r"[a-z0-9-]*", apelido), (
            f"o apelido de {hostil!r} escapou da lista de permissao: {apelido!r}"
        )

    @pytest.mark.parametrize(
        "hostil",
        [
            "../../etc/passwd",
            "..\\..\\windows\\system32",
            "Tiat/../../North",
        ],
    )
    def test_o_caminho_resultante_continua_filho_direto_da_agenda(
        self, tmp_path, hostil
    ):
        """A prova que importa: onde o arquivo REALMENTE cai.

        Um apelido que contivesse `/` ou `..` faria o marcador nascer fora de
        `.agenda/` — e a poda de 3 dias nunca mais o alcancaria.
        """
        from datetime import datetime

        from l2scanner.respawn import chave_do_nascimento

        pasta = tmp_path / ".agenda"
        pasta.mkdir()
        chave = chave_do_nascimento(
            hostil, datetime(2026, 8, 30, 14, 30), OrigemDoAviso.CHAT
        )

        destino = (pasta / f"nascimento_{chave}").resolve()

        assert destino.parent == pasta.resolve()


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

    def test_nome_vazio(self, tmp_path):
        """Um `nome` vazio nao e "sem nome": e um bloco que PARECE completo.

        `nome = ""` produziria um padrao que casa a string vazia — isto e,
        casaria QUALQUER linha do chat que tivesse `[Lv. NN] has spawned`,
        vindo de qualquer mob do servidor.
        """
        caminho = escrever_config(
            tmp_path,
            '[[boss]]\nnome = ""\n'
            "respawn_horas_min = 6\nrespawn_horas_max = 8\n",
        )

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "nome" in str(erro.value)
        assert "[[boss]] #1" in str(erro.value)

    def test_nome_so_com_espacos(self, tmp_path):
        """O mesmo buraco, com a aparencia de estar preenchido."""
        caminho = escrever_config(
            tmp_path,
            '[[boss]]\nnome = "   "\n'
            "respawn_horas_min = 6\nrespawn_horas_max = 8\n",
        )

        with pytest.raises(BossInvalido) as erro:
            ler_bosses(caminho)
        assert "nome" in str(erro.value)

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

    def test_o_arquivo_do_repositorio_tem_os_dois_tiat_com_a_janela_LIDA(self, roster):
        """O ESQUEMA, nunca o valor: a janela de respawn e DADO do servidor.

        Este teste ja cravou `6` e `8` e ficou VERMELHO em 2026-08-30, quando o
        servidor mudou a regra para 8+2 e o `config.toml` acompanhou (c4175da).
        Cravar o numero aqui contradiz o VIGI-02, que existe para a regra de
        respawn nao exigir deploy — o teste virava o deploy.
        """
        assert [b.nome for b in roster] == ["Tiat North", "Tiat South"]
        for boss in roster:
            assert isinstance(boss.respawn_horas_min, (int, float))
            assert isinstance(boss.respawn_horas_max, (int, float))
            assert boss.respawn_horas_min > 0
            assert boss.respawn_horas_min <= boss.respawn_horas_max

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
# VIGI-01 / VIGI-02 (criterio 5): a lista sai do codigo e vira dado.
# ---------------------------------------------------------------------------


INVENTADO = "Gargulha Chorona do Pantano"


class TestUmBossInventadoPassaAVigiadoSemTocarEmPy:
    """O criterio 5 do ROADMAP, fechado do arquivo ate a mensagem.

    Um teste com roster escrito a mao provaria so que `VigiaDeBosses` funciona.
    Este monta o vigia com o que `ler_bosses` devolveu de um `config.toml` que
    o teste ESCREVEU, com um mob que nao existe no jogo — e por isso nao pode
    ter sobrado em constante nenhuma do codigo.
    """

    def escrever(self, tmp_path, nome):
        return escrever_config(
            tmp_path,
            f'[[boss]]\nnome = "{nome}"\n'
            "respawn_horas_min = 3\nrespawn_horas_max = 5\n",
        )

    def test_o_anuncio_do_mob_inventado_dispara(self, tmp_path):
        roster = ler_bosses(self.escrever(tmp_path, INVENTADO))

        assert [b.nome for b in roster] == [INVENTADO]

        v = vigia([f"{INVENTADO} [Lv. 42] has spawned!"], [""], bosses=roster)
        avisos = v.avaliar(PIXELS, PIXELS, AGORA)

        assert len(avisos) == 1
        assert avisos[0].boss == INVENTADO
        assert avisos[0].texto.startswith(INVENTADO)

    def test_o_mob_inventado_tambem_e_reconhecido_no_alvo(self, tmp_path):
        roster = ler_bosses(self.escrever(tmp_path, INVENTADO))

        v = vigia([""], [INVENTADO], bosses=roster)

        assert [a.boss for a in v.avaliar(PIXELS, PIXELS, AGORA)] == [INVENTADO]

    def test_nenhum_arquivo_py_conhece_o_mob_inventado(self):
        """A metade "sem nenhuma alteracao em arquivo .py" do criterio 5.

        O teste acima passaria mesmo que o codigo tivesse uma lista de mobs
        conhecidos, desde que ela contivesse este nome. Esta asseracao fecha o
        outro lado: o scanner nao conhece mob nenhum por nome.
        """
        for arquivo in sorted((RAIZ / "l2scanner").glob("*.py")):
            texto = arquivo.read_text(encoding="utf-8")
            assert INVENTADO not in texto, arquivo.name

    def test_o_mob_inventado_nao_dispara_com_a_frase_de_outro_mob(self, tmp_path):
        """Vigiar um nao pode significar vigiar todos."""
        roster = ler_bosses(self.escrever(tmp_path, INVENTADO))

        v = vigia([ANUNCIO], [""], bosses=roster)

        assert v.avaliar(PIXELS, PIXELS, AGORA) == []


class TestOEsquemaDoBlocoBossEstaCompletoParaAFase2:
    """VIGI-02: os campos moram no arquivo antes de serem usados.

    Espelha `tests/test_agenda.py::test_as_duracoes_de_silencio_estao_no_esquema_para_a_fase_7`,
    e o precedente esta citado de proposito: e o MESMO movimento — um campo
    lido, validado e ignorado, presente desde ja para o usuario nao ter que
    editar duas vezes um config que ja editou. Citar o precedente e o que faz a
    proxima fase encontrar o padrao em vez de reinventa-lo.
    """

    @pytest.fixture
    def roster(self):
        return ler_bosses(RAIZ / "config.toml")

    def test_os_dois_tiat_do_repositorio_tem_a_janela_LIDA(self, roster):
        """As horas sao LIDAS e IGNORADAS nesta fase; a Fase 2 as consome.

        E POR ISSO O TESTE NAO AFIRMA O VALOR. A regra e do servidor — fixa
        mais um sorteio, contada a partir da MORTE — e ela MUDA: em 2026-08-30
        passou de 6+2 para 8+2 e o `config.toml` acompanhou em `c4175da`, sem
        uma linha de codigo. Este teste afirmava `== 6` e ficou vermelho por
        fazer o certo do jeito errado: ele provava a regra do servidor em vez
        de provar que ela e LIDA do arquivo.
        """
        por_nome = {b.nome: b for b in roster}

        assert set(por_nome) == {"Tiat North", "Tiat South"}
        for boss in por_nome.values():
            assert boss.respawn_horas_min is not None
            assert boss.respawn_horas_max is not None
            assert boss.respawn_horas_min > 0
            assert boss.respawn_horas_min <= boss.respawn_horas_max

    def test_o_cabecalho_documenta_os_tres_campos(self):
        """Um campo que existe e nao esta documentado e mentira por omissao.

        Quem le o `config.toml` e nao encontra `respawn_horas_min` na lista de
        campos conclui que a regra de respawn nao e editavel — e nao edita.
        Mesmo molde de `test_o_cabecalho_do_arquivo_documenta_o_campo`.
        """
        texto = (RAIZ / "config.toml").read_text(encoding="utf-8")
        # Corta no PRIMEIRO bloco de verdade, que comeca em coluna zero: o
        # proprio cabecalho escreve `[[boss]]` em prosa.
        cabecalho = texto.split(chr(10) + "[[boss]]")[0]
        cabecalho = cabecalho.split("Os bosses raros vigiados")[-1]

        for campo in ("nome", "respawn_horas_min", "respawn_horas_max"):
            assert campo in cabecalho, campo


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
