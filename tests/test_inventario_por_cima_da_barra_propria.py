"""O falso positivo mais volumoso do projeto: o inventario aberto vira MORTE.

O SINTOMA: com o inventario aberto por cima da barra de vida do proprio
personagem, o scanner le 0% e anuncia "YAZALAQUE MORREU". O `logs/scanner.log`
real tem **27 mortes + 27 ressurreicoes** desse defeito — mais que todos os
alertas de party somados.

A CAUSA: `barra_propria_legivel` decidia so por desvio-padrao de cinza. A GRADE
do inventario tem contraste de sobra e PASSAVA; dai `medir_barra` devolvia 0.0 e
o rastreador convertia em morte.

E O DESVIO-PADRAO NAO PODE RESOLVER ISSO, e esta medido nas fixtures deste
repositorio: `coberta_0` da desvio 36.54, MAIOR que `livre_0` (35.47). Qualquer
limiar de desvio que rejeite a coberta rejeita tambem a livre.

O que separa e a MOLDURA — menor media de cinza entre as quatro bordas do
recorte:

    coberta_0..3   48.00  48.92  28.00  29.00   (pior: 48.92)
    livre_0..3     86.42 nas quatro
    quase vazia    78.73                        (pior livre/vazia)

Vao medido de 29.8 pontos, sem zona cinzenta.

As barras da PARTY ja tinham o remedio para exatamente esta classe de problema
(`_bordas_da_barra_intactas`). A barra PROPRIA nunca tinha ganhado o
equivalente. Este arquivo prende os DOIS sentidos: o inventario nao vira morte,
e a morte de verdade continua virando morte.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento
from l2scanner.visao import (
    BRILHO_MINIMO_DA_MOLDURA_PROPRIA,
    DESVIO_MINIMO_DA_BARRA_PROPRIA,
    _moldura_da_barra_propria,
    barra_propria_legivel,
    extrair,
)

FIXTURES = Path(__file__).parent / "fixtures" / "barra_propria"
CALIBRACAO = (
    Path(__file__).parent
    / "fixtures"
    / "party_estavel_com_vazamento"
    / "calibracao.json"
)

COBERTAS = ("coberta_0", "coberta_1", "coberta_2", "coberta_3")
LIVRES = ("livre_0", "livre_1", "livre_2", "livre_3")

# As tres cobertas que `medir_barra` le como 0.0% — sao elas que viravam morte.
# `coberta_0` le 0.87 porque o painel do inventario cobre so parte da barra:
# ela era ILEGIVEL do mesmo jeito, mas nao chegava a produzir alarme.
COBERTAS_QUE_LIAM_ZERO = ("coberta_1", "coberta_2", "coberta_3")

# A barra de MP do proprio personagem em `recordings/agora_janela.png`, a
# 170/2567 (6.6%) — praticamente VAZIA, com o terreno aparecendo atras de ~95%
# do comprimento. Mesmo widget, mesma largura, mesmo chrome que a barra de HP.
# E o unico proxy alinhado de barra vazia que o repositorio tem: todas as
# amostras de HP proprio estao a 100%.
QUASE_VAZIA = "quase_vazia_terreno_atras"


@pytest.fixture
def calibracao() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO)


def recorte(rotulo: str) -> np.ndarray:
    """O recorte 191x24 da barra propria, como a captura o entrega."""
    caminho = FIXTURES / f"{rotulo}.png"
    pixels = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
    assert pixels is not None, f"fixture {caminho} nao pode ser lida"
    return pixels


def frame_solo(rotulo: str) -> Frame:
    """Um frame de quem esta upando SOLO, com o recorte da barra propria junto.

    A regiao da party window vem preta de proposito: solo, a party window nao
    esta na tela, e e justamente ai que a barra propria e a UNICA fonte de
    morte. Isto atravessa `extrair` de verdade — nada de montar a `Observacao`
    a mao, senao o teste nao toca no caminho do defeito.
    """
    return Frame(
        pixels=np.zeros((522, 174, 3), dtype=np.uint8),
        indice=0,
        saude=SaudeDoFrame.OK,
        extras={"hp_proprio": recorte(rotulo)},
    )


def novo(cal: Calibracao) -> Rastreador:
    return Rastreador(
        nomes=list(cal.nomes), nome_proprio=cal.nome_proprio, ajustes=Ajustes()
    )


def alimentar(r, obs, vezes, inicio=0.0):
    eventos = []
    for i in range(vezes):
        eventos.extend(r.observar(obs, inicio + i))
    return eventos


def mortes(eventos):
    return [e for e in eventos if e.tipo is TipoDeEvento.MORREU]


class TestOInventarioNaoViraMorte:
    """O caminho que precisa deixar de existir, de ponta a ponta."""

    @pytest.mark.parametrize("rotulo", COBERTAS_QUE_LIAM_ZERO)
    def test_recorte_coberto_da_hp_proprio_None_e_nunca_0(self, rotulo, calibracao):
        """Antes da correcao estas tres devolviam 0.0 — o zero que matava.

        `None` e `0.0` sao coisas diferentes e o rastreador depende disso:
        `None` CONGELA o estado, `0.0` conclui morte.
        """
        obs = extrair(frame_solo(rotulo), calibracao)
        assert obs.hp_proprio is None, (
            f"{rotulo}.png: o inventario por cima da barra foi lido como "
            f"{obs.hp_proprio!r} de HP em vez de 'nao consigo ler'"
        )

    @pytest.mark.parametrize("rotulo", COBERTAS)
    def test_nenhum_recorte_coberto_produz_leitura(self, rotulo, calibracao):
        """Inclusive `coberta_0`, que lia 0.87 e nao chegava a virar alarme.

        Ela e ilegivel pelo mesmo motivo das outras tres, e deixa-la passar
        seria gravar HP inventado no historico.
        """
        assert extrair(frame_solo(rotulo), calibracao).hp_proprio is None

    def test_trinta_frames_de_inventario_aberto_nao_emitem_morte(self, calibracao):
        """A reproducao do defeito: 27 mortes falsas no log real do usuario."""
        r = novo(calibracao)
        alimentar(r, extrair(frame_solo("livre_0"), calibracao), 20)

        coberto = extrair(frame_solo("coberta_1"), calibracao)
        eventos = alimentar(r, coberto, 30, 100)

        assert mortes(eventos) == [], (
            "abrir o inventario continua anunciando a morte de quem esta vivo"
        )


class TestAMorteDeVerdadeContinuaSaindo:
    """A RESTRICAO DURA, e a razao de este grupo existir.

    O remedio nao pode transformar o scanner num que deixa de avisar morte de
    verdade. A morte real acontece com a barra VISIVEL — este e o caminho que
    precisa estar VERDE antes da correcao e continuar verde depois. E a rede,
    nao o alvo.
    """

    def test_barra_quase_vazia_real_e_legivel_E_zerada(self, calibracao):
        """Medido no recorte: moldura 78.73, desvio 31.71, HP 0.0%.

        A parte vazia da barra e transparente e mostra o TERRENO, entao uma
        barra praticamente vazia continua CLARA. E por isso que o portao de
        moldura nao suprime a leitura de zero — e isso e um numero, nao uma
        esperanca.
        """
        obs = extrair(frame_solo(QUASE_VAZIA), calibracao)
        assert obs.hp_proprio == 0.0, (
            "uma barra REAL quase vazia foi declarada ilegivel — o portao "
            "novo esta suprimindo morte de verdade, o pior desfecho possivel"
        )

    def test_a_barra_quase_vazia_real_ainda_emite_MORREU(self, calibracao):
        r = novo(calibracao)
        alimentar(r, extrair(frame_solo("livre_0"), calibracao), 20)

        vazia = extrair(frame_solo(QUASE_VAZIA), calibracao)
        eventos = alimentar(r, vazia, 10, 100)

        assert [e.membro for e in mortes(eventos)] == [calibracao.nome_proprio], (
            "o scanner ficou mudo na morte — vigiar sem avisar e pior que "
            "nao vigiar"
        )


class TestAsOitoFixturesReaisNosDoisSentidos:
    """A regressao permanente das amostras que o usuario capturou da tela dele.

    Uma assercao por arquivo, com o nome do arquivo na mensagem: quando isto
    quebrar daqui a seis meses, o que importa saber e QUAL recorte mudou de
    veredito, nao que "alguma fixture falhou".
    """

    @pytest.mark.parametrize("rotulo", COBERTAS)
    def test_coberta_pelo_inventario_e_ILEGIVEL(self, rotulo):
        """Moldura medida: 48.00, 48.92, 28.00, 29.00 — todas abaixo de 60."""
        assert not barra_propria_legivel(recorte(rotulo)), (
            f"{rotulo}.png: a barra coberta pelo inventario voltou a ser lida "
            f"como barra — e dai sai 'YAZALAQUE MORREU' com ele vivo"
        )

    @pytest.mark.parametrize("rotulo", LIVRES)
    def test_livre_e_LEGIVEL(self, rotulo):
        """Moldura medida: 86.42 nas quatro — 26 pontos acima do limiar."""
        assert barra_propria_legivel(recorte(rotulo)), (
            f"{rotulo}.png: a barra LIVRE foi declarada ilegivel — o scanner "
            f"parou de vigiar o proprio personagem sem reclamar"
        )

    def test_a_barra_quase_vazia_real_e_LEGIVEL(self):
        """O proxy de barra vazia, e a razao de ele ser a barra de MP.

        NENHUMA amostra de HP proprio alinhada e de HP baixo: as 8 fixtures, as
        4 `*__hp_proprio*.png` e todos os frames de janela em `recordings/`
        estao a 100%. O que existe e a barra de MP do MESMO widget — mesma
        largura, mesmo chrome — a 170/2567 (6.6%) em
        `recordings/agora_janela.png`.

        Medido nesse recorte: moldura 78.73, desvio 31.71, e `medir_barra` com
        os limiares de HP le 0.0% (nao ha vermelho nenhum ali). Ou seja: uma
        barra praticamente vazia deste widget continua CLARA, porque o vazio
        mostra o terreno. O portao de moldura nao suprime a leitura de zero.
        """
        assert barra_propria_legivel(recorte(QUASE_VAZIA)), (
            "uma barra REAL quase vazia caiu no portao de moldura — o remedio "
            "virou o defeito, e morte real deixa de ser anunciada"
        )


class TestOTripwireDoDesvioPadrao:
    """Contra quem olhar o codigo daqui a um ano e achar o desvio suficiente.

    O portao de moldura parece redundante ao lado do de contraste. Nao e, e a
    prova esta nas proprias fixtures: a coberta tem MAIS contraste que a livre.
    """

    def test_o_desvio_SOZINHO_deixaria_a_coberta_passar(self):
        """Medido: coberta_0 da 36.54 e livre_0 da 35.47.

        A coberta pelo inventario tem contraste MAIOR que a livre. Qualquer
        limiar de desvio que rejeite uma rejeita a outra — nao existe numero
        que separe. Este teste afirma as duas coisas ao mesmo tempo: que o
        portao de desvio isolado aprovaria a coberta, e que o portao completo a
        rejeita.
        """
        coberta = cv2.cvtColor(recorte("coberta_0"), cv2.COLOR_BGR2GRAY)
        livre = cv2.cvtColor(recorte("livre_0"), cv2.COLOR_BGR2GRAY)

        assert float(coberta.std()) > float(livre.std()), (
            "as fixtures mudaram: o desvio da coberta era MAIOR que o da livre, "
            "e e por isso que o portao de moldura precisa existir"
        )
        assert float(coberta.std()) >= DESVIO_MINIMO_DA_BARRA_PROPRIA, (
            "o portao de desvio sozinho aprovava a coberta — se isto deixou de "
            "valer, o tripwire perdeu o sentido e precisa ser remedido"
        )
        assert not barra_propria_legivel(recorte("coberta_0")), (
            "alguem apagou o portao de moldura achando que o desvio bastava"
        )

    def test_o_portao_de_desvio_continua_no_lugar(self):
        """E o segundo motivo de os dois rodarem EM SERIE, tambem medido.

        `np.full((8,120,3), 60)` — que `tests/test_modo_solo.py` afirma ILEGIVEL
        desde o modo solo — da moldura exatamente 60.00 e PASSA no portao de
        moldura (o limiar e `>=`). Ele so continua rejeitado porque o portao de
        desvio nao saiu do lugar. Apagar o desvio reabre um buraco medido.
        """
        uniforme = np.full((8, 120, 3), 60, dtype=np.uint8)

        assert _moldura_da_barra_propria(uniforme) == 60.0
        assert _moldura_da_barra_propria(uniforme) >= BRILHO_MINIMO_DA_MOLDURA_PROPRIA, (
            "o limiar subiu acima de 60 e esta armadilha deixou de existir: "
            "reveja a medicao antes de mexer no portao de desvio"
        )
        assert not barra_propria_legivel(uniforme), (
            "um recorte uniforme passou: o portao de desvio foi removido e a "
            "moldura sozinha nao pega o degenerado"
        )

    def test_o_ruido_texturizado_segue_LEGIVEL(self):
        """A outra ponta: o portao novo nao pode rejeitar o que ja era aceito.

        O recorte de `rng(7)` que `test_o_discriminador_e_contraste_e_nao_saturacao`
        usa da moldura 120.33 — bem acima do limiar, como deve.
        """
        gerador = np.random.default_rng(7)
        texturizado = np.repeat(
            gerador.integers(0, 255, (8, 120, 1), dtype=np.uint8), 3, axis=2
        )
        assert barra_propria_legivel(texturizado)
