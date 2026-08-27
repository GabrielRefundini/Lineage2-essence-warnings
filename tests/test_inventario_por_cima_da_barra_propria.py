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

import dataclasses
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import Calibracao, Regiao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento
from l2scanner.visao import (
    BRILHO_MINIMO_DA_MOLDURA_PROPRIA,
    CASAMENTO_MINIMO_DO_PERFIL_PROPRIO,
    DESVIO_MINIMO_DA_BARRA_PROPRIA,
    LEITURA_MINIMA_PARA_O_CASAMENTO,
    Observacao,
    _braco_do_casamento,
    _casamento_do_perfil_proprio,
    _moldura_da_barra_propria,
    barra_propria_legivel,
    extrair,
    medir_barra,
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


# ---------------------------------------------------------------------------
# TERRENO ESCURO — o outro lado do portao de moldura, medido em 2026-08-27
# ---------------------------------------------------------------------------

# As tres fixtures resgatadas de `recordings/escuro_janela.png` (1392x1720,
# brilho medio 58.12), que esta no `.gitignore` e era a UNICA copia da unica
# cena escura que o repositorio conhece. Recortes, em linhas e colunas do
# arquivo:
#
#   escuro_cheia       = [716:740, 294:485]  a regiao `hp_proprio` calibrada
#   escuro_cauda_vazia = [741:765, 294:485]  o widget de MP, 25 px abaixo
#   escuro_faixa       = [739:767, 294:485]  a mesma cauda com 2 px de folga
ESCURO_CHEIA = "escuro_cheia"
ESCURO_CAUDA_VAZIA = "escuro_cauda_vazia"
ESCURO_FAIXA = "escuro_faixa"

# 88.48% de 191 px termina o preenchimento na coluna 169 — daqui para a direita
# a barra e 100% vazia e mostra so o terreno escuro. Numero MEDIDO, nao chutado.
PRIMEIRA_COLUNA_VAZIA = 169


def calibracao_do_widget(cal: Calibracao) -> Calibracao:
    """A mesma calibracao, com o detector apontado para as cores do widget.

    A fixture de terreno escuro e o widget de MP (AZUL): a mascara de HP
    (vermelha) simplesmente nao a enxerga, e `medir_barra` devolveria 0.0 por
    daltonismo, nao por barra vazia.

    Isto NAO sintetiza pixel nenhum e nao afrouxa portao nenhum: todo o resto do
    caminho de `extrair` — o portao de desvio, o portao de moldura, a corrida
    inicial de colunas — fica exatamente como em producao. Trocar `limiares_hp`
    por `limiares_mp` e o equivalente a dizer ao detector de que cor e a barra
    que ele esta olhando.
    """
    return dataclasses.replace(cal, limiares_hp=cal.limiares_mp)


class TestOTerrenoEscuroSomeDoConsole:
    """O DEFEITO, preso em pixels reais: a barra legitima some em cena escura.

    Medido em 2026-08-27 sobre `recordings/escuro_janela.png`:

        escuro_janela HP  (716,294)  100% cheia   moldura 86.42  LEGIVEL
        escuro_janela MP  (741,294)  88.5% cheia  moldura 29.08  ILEGIVEL
        agora_janela  MP  (741,294)   6.8% cheia  moldura 78.73  LEGIVEL

    A barra NAO precisa estar vazia para cair: 11.5% de cauda vazia sobre
    terreno escuro ja bastam. O "~32 estimado" do TODO virou 29.08 MEDIDO.

    E as duas classes se sobrepoem NESTE ARQUIVO, nao em teoria:

        coberta pelo inventario  28.00 .. 48.92   (n=8, tela real)
        livre em cena escura     29.08            (n=1, tela real)

    29.08 fica DENTRO da faixa das cobertas. Nenhum limiar de brilho separa as
    duas classes, e por isso o remedio nao e mexer em
    `BRILHO_MINIMO_DA_MOLDURA_PROPRIA`: e um discriminador diferente, invariante
    a brilho.

    Consequencia no produto, e e ela que esta tarefa ataca: durante a descida
    inteira de HP numa cena escura, o console e o `scanner.log` nao mostram NADA
    da barra propria — some justamente a unica ferramenta de depuracao pos-farm
    que o projeto tem, e sem log nao ha como capturar a amostra que fecharia a
    pendencia.
    """

    def test_a_barra_legitima_em_cena_escura_cai_na_faixa_das_cobertas(self):
        """A sobreposicao, afirmada sobre pixels versionados.

        Passa HOJE e deve continuar passando DEPOIS: este teste documenta a
        SOBREPOSICAO, nao o remedio. O dia em que ele quebrar, alguem mexeu no
        limiar de moldura ou nas fixtures — e a medicao inteira precisa ser
        refeita.
        """
        moldura = _moldura_da_barra_propria(recorte(ESCURO_CAUDA_VAZIA))

        assert moldura < BRILHO_MINIMO_DA_MOLDURA_PROPRIA, (
            f"{ESCURO_CAUDA_VAZIA}.png: moldura {moldura:.2f} passou no portao "
            f"de hoje — a fixture mudou e a premissa desta tarefa caiu"
        )
        assert 28.00 <= moldura <= 48.92, (
            f"moldura {moldura:.2f} saiu da faixa das COBERTAS (28.00..48.92); "
            f"a sobreposicao medida em 2026-08-27 era o coracao do argumento"
        )

    def test_hp_proprio_continua_None_e_isso_e_PROPOSITAL(self, calibracao):
        """A assercao que prova que a mudanca NAO mexe na maquina de estado.

        `hp_proprio` alimenta TRES consumidores no `rastreador.py` (linhas 454,
        496 e 833). Uma leitura vinda daqui pode ser um recorte parcialmente
        ocluido — `coberta_0` (moldura 48.00) e esta fixture (29.08) so se
        ordenam pela moldura, e nessa ordem a classe coberta fica dos DOIS lados
        do unico ponto legitimo. Entao ela nao pode virar `hp_proprio`, hoje nem
        depois.

        Este teste e VERDE hoje e tem que continuar verde: e o gate que impede
        alguem de "melhorar" a correcao para dentro do rastreador.
        """
        obs = extrair(frame_solo(ESCURO_CAUDA_VAZIA), calibracao_do_widget(calibracao))

        assert obs.hp_proprio is None, (
            f"hp_proprio saiu {obs.hp_proprio!r} em vez de None: a leitura de "
            f"cena escura vazou para a maquina de estado, que e exatamente o "
            f"que a revisao 3 deste plano existe para impedir"
        )

    def test_a_descida_volta_a_ser_MOSTRADA_pelo_campo_aparente(self, calibracao):
        """VERMELHA hoje: `hp_proprio_aparente` ainda nao existe.

        Medido: a leitura da cauda vazia com os limiares do widget e 0.8848 — a
        barra esta 88.5% cheia e o usuario esta VIVO. Hoje o console e o log nao
        mostram nada; depois mostram este numero, MARCADO COMO APARENTE.
        """
        obs = extrair(frame_solo(ESCURO_CAUDA_VAZIA), calibracao_do_widget(calibracao))

        assert obs.hp_proprio_aparente is not None, (
            "a barra 88.5% cheia em cena escura continua sem produzir NADA "
            "para o console e para o log"
        )
        assert abs(obs.hp_proprio_aparente - 0.8848) < 0.001, (
            f"a leitura aparente saiu {obs.hp_proprio_aparente!r}; o medido em "
            f"2026-08-27 sobre esta fixture e 0.8848"
        )

    def test_a_cena_escura_SOZINHA_nao_derruba_nada(self):
        """A testemunha: mesma cena, mesma janela, mesmo frame, barra CHEIA.

        `escuro_cheia` mede moldura 86.42 e ja e legivel hoje. Ou seja: nao e o
        escuro que derruba o portao — e a CAUDA VAZIA mostrando terreno escuro.
        Sem esta testemunha, "cena escura quebra a leitura" seria uma explicacao
        plausivel e errada.
        """
        assert barra_propria_legivel(recorte(ESCURO_CHEIA)), (
            f"{ESCURO_CHEIA}.png: a barra CHEIA em cena escura foi declarada "
            f"ilegivel — entao o problema nao e a cauda vazia e toda a medicao "
            f"de 2026-08-27 precisa ser refeita"
        )
        assert _moldura_da_barra_propria(recorte(ESCURO_CHEIA)) > 80.0

    def test_a_cauda_100_por_cento_vazia_e_terreno_escuro_puro(self, calibracao):
        """As duas metades da prova, afirmadas juntas de proposito.

        A primeira mostra que o recorte foi derivado certo (a partir da coluna
        169 nao ha preenchimento nenhum — 88.48% de 191 px termina ali). A
        segunda mostra que esse terreno escuro, sozinho, REPROVA no portao de
        hoje. Uma sem a outra nao prova nada: leitura zero poderia ser recorte
        errado, e moldura baixa poderia ser barra ainda preenchida.
        """
        cauda = recorte(ESCURO_CAUDA_VAZIA)[:, PRIMEIRA_COLUNA_VAZIA:]
        regiao = Regiao(
            esquerda=0, topo=0, largura=cauda.shape[1], altura=cauda.shape[0]
        )

        assert medir_barra(cauda, regiao, calibracao.limiares_mp) == 0.0, (
            "a cauda a partir da coluna 169 ainda tem preenchimento: a "
            "derivacao do recorte esta errada e o resto da medicao nao vale"
        )
        assert _moldura_da_barra_propria(cauda) < BRILHO_MINIMO_DA_MOLDURA_PROPRIA, (
            "o terreno escuro atras da barra vazia PASSOU no portao de hoje — "
            "entao nao ha defeito a consertar e a premissa caiu"
        )

    def test_a_faixa_carrega_a_prova_do_proprio_alinhamento(self):
        """`escuro_faixa[2:26]` E `escuro_cauda_vazia`, byte a byte.

        A faixa tem 28 linhas justamente para que os deslocamentos de -2 a +2 px
        venham de PIXELS REAIS, e nao de `np.roll` (que inventa linhas). Esta
        assercao e o que garante que a janela do meio e a fixture principal.
        """
        faixa = recorte(ESCURO_FAIXA)
        assert faixa.shape == (28, 191, 3), faixa.shape
        assert (faixa[2:26] == recorte(ESCURO_CAUDA_VAZIA)).all(), (
            "a faixa deixou de estar alinhada com a cauda vazia — os testes de "
            "tolerancia a desalinhamento passam a medir outra coisa"
        )


# ---------------------------------------------------------------------------
# O BRACO NOVO — leitura APARENTE, so para o console e para o log
# ---------------------------------------------------------------------------

RECORDINGS = Path(__file__).parent.parent / "recordings"

# As 8 amostras da tabela de verificacao do plano, com a calibracao apontada
# para as cores do widget de CADA fixture. `escuro_cauda_vazia` e
# `quase_vazia_terreno_atras` sao o widget de MP (azul); as outras seis sao HP.
#
# `hp_proprio` sai IDENTICO ao que sai hoje nas oito — e esse "identico" e a
# prova de que nenhum alerta pode ter mudado.
AS_OITO_AMOSTRAS = (
    ("escuro_cauda_vazia", "MP", None, 0.8848),
    ("escuro_cheia", "HP", 1.0000, None),
    ("coberta_0", "HP", None, 0.8691),
    ("coberta_1", "HP", None, None),
    ("coberta_2", "HP", None, None),
    ("coberta_3", "HP", None, None),
    ("livre_0", "HP", 1.0000, None),
    ("quase_vazia_terreno_atras", "MP", 0.0681, None),
)


def cal_do_widget(cal: Calibracao, widget: str) -> Calibracao:
    return calibracao_do_widget(cal) if widget == "MP" else cal


def regiao_inteira(px: np.ndarray) -> Regiao:
    return Regiao(esquerda=0, topo=0, largura=px.shape[1], altura=px.shape[0])


def frame_de_party(rotulo_da_barra: str | None) -> Frame:
    """Um frame com a party window REAL visivel e a barra propria escolhida.

    Aquecer o rastreador exige `_ja_viu_party_window=True` e `_voce_em_party=
    True`, que e o estado NORMAL de qualquer sessao em party depois do primeiro
    minuto. Aqui esse estado vem de pixels de verdade — a party window da
    fixture `party_estavel_com_vazamento/limpo.png` — em vez de ser fixado a
    mao nos campos privados. Um aquecimento fabricado provaria menos.
    """
    if rotulo_da_barra is None:
        barra = cv2.imread(str(CALIBRACAO.parent / "limpo__hp_proprio.png"))
        assert barra is not None
    else:
        barra = recorte(rotulo_da_barra)
    return Frame(
        pixels=cv2.imread(str(CALIBRACAO.parent / "limpo.png")),
        indice=0,
        saude=SaudeDoFrame.OK,
        extras={"hp_proprio": barra},
    )


class TestOBracoNovoNuncaCertificaLeituraDeMorte:
    """A varredura EXAUSTIVA, nas DUAS direcoes de oclusao.

    `medir_barra` mede a corrida inicial DA ESQUERDA. Isso torna as duas
    direcoes assimetricas, e a assimetria e a coisa mais perigosa deste arquivo:

        painel a DIREITA  -> SUBESTIMA a leitura   (k/191)
        painel a ESQUERDA -> ZERA a leitura        (0.0000)

    E a direcao que zera e a que o casamento NAO enxerga: o perfil e a media por
    LINHA, entao cobrir 5 de 191 colunas mal move a media e Pearson e cego a
    escala. Medido: painel cobrindo 5 colunas a esquerda le 0.0000 e casa
    +1.000. Sem o portao de LEITURA, abrir o inventario voltaria a produzir
    morte falsa — a classe de defeito que a quick `260826-dxm` pagou para matar.

    A assercao e sobre a LEITURA, e nao sobre k: para TODO composto cuja leitura
    caia em ou abaixo de `Ajustes().fracao_hp_considerada_zero`, o braco novo
    recusa. Escrita sobre k, ela certificaria a propriedade errada — foi o
    BLOCKER 2 da primeira iteracao do plan-check.

    HONESTIDADE SOBRE A AMOSTRA: os 4 paineis sao recortes REAIS do inventario
    do usuario. Dos 3 preenchimentos de direita, DOIS sao recortes reais de
    largura inteira (`livre_0`, `quase_vazia_terreno_atras`) e o TERCEIRO e a
    cauda 100% vazia real de terreno escuro LADRILHADA ate 191 colunas — pixels
    reais, geometria sintetica.
    """

    def test_nenhum_composto_em_regime_de_morte_e_certificado(self, calibracao):
        """Medido em 2026-08-27: 4608 compostos, 3279 em regime de morte, ZERO.

        As fixtures sao lidas UMA vez fora do laco de proposito: em cache a
        varredura leva ~0.13 s, relendo o disco a cada iteracao leva ~0.4 s.
        """
        cauda = recorte(ESCURO_CAUDA_VAZIA)[:, PRIMEIRA_COLUNA_VAZIA:]
        ladrilhada = np.tile(cauda, (1, (191 // cauda.shape[1]) + 1, 1))[:, :191]
        direitas = {
            "livre_0": recorte("livre_0"),
            "quase_vazia": recorte(QUASE_VAZIA),
            "cauda_escura_ladrilhada": ladrilhada,
        }
        paineis = {rotulo: recorte(rotulo) for rotulo in COBERTAS}
        limiar_de_morte = Ajustes().fracao_hp_considerada_zero

        total = 0
        em_regime_de_morte = 0
        for nome_direita, direita in direitas.items():
            for nome_painel, painel in paineis.items():
                for k in range(0, 192):
                    compostos = (
                        ("painel a ESQUERDA", np.hstack([painel[:, :k], direita[:, k:]])),
                        ("painel a DIREITA", np.hstack([direita[:, :k], painel[:, k:]])),
                    )
                    for direcao, composto in compostos:
                        total += 1
                        leitura = medir_barra(
                            composto, regiao_inteira(composto), calibracao.limiares_hp
                        )
                        if leitura > limiar_de_morte:
                            continue
                        em_regime_de_morte += 1
                        assert not _braco_do_casamento(composto, leitura), (
                            f"{direcao}, {nome_painel} sobre {nome_direita}, k={k}: "
                            f"leitura {leitura:.4f} (limiar de morte "
                            f"{limiar_de_morte}) foi CERTIFICADA pelo braco novo "
                            f"— um painel de inventario acabou de virar uma "
                            f"leitura de morte, que e o defeito de 27 alertas "
                            f"falsos que a quick 260826-dxm pagou para matar"
                        )

        assert total == 4608, total
        assert em_regime_de_morte > 0, (
            "NENHUM composto ficou em regime de morte: a montagem quebrou e "
            "esta varredura passou VERDE sem testar coisa nenhuma"
        )
        assert em_regime_de_morte == 3279, (
            f"o conjunto em regime de morte mudou de 3279 para "
            f"{em_regime_de_morte}: as fixtures ou a montagem mudaram, e a "
            f"exaustao precisa ser remedida antes de valer como prova"
        )


class TestACobertaAtravessaORastreadorSemEmitirNada:
    """O TESTE QUE FALTAVA — e cuja ausencia deixou o risco escapar da suite.

    Nenhum teste deste repositorio levava um recorte COBERTO ate dentro do
    `Rastreador`. O unico que chega la,
    `test_trinta_frames_de_inventario_aberto_nao_emitem_morte`, FILTRA os
    eventos por `MORREU` — entao um `VOCE_SEM_PARTY` ou um `RESSUSCITOU` falso
    passaria despercebido. Foi por isso que o custo apareceu no plan-check e nao
    na suite.

    Aqui a assercao e sobre a lista de eventos INTEIRA, de QUALQUER tipo.

    O QUE ACONTECERIA se a leitura aparente virasse `hp_proprio` — simulado com
    `Ajustes()` de producao (`confirmacoes_para_voce_sem_party = 8`,
    `confirmacoes_para_morte = 3`), porque `hp_proprio` tem TRES consumidores no
    `rastreador.py` (linhas 454, 496 e 833):

        quente com party, inventario 30 ticks -> `voce_sem_party` falso (tick 27)
        morre e depois abre o inventario      -> `ressuscitou` falso (tick 34)
                                                 + `voce_sem_party` falso (37)
        SOLO: morre e abre o inventario       -> `ressuscitou` falso (tick 34)
        morrendo (2 de 3), abre e fecha       -> morte ATRASA do tick 18 para o 20

    A `ressuscitou` falsa e literalmente metade do defeito da quick
    `260826-dxm` (27 mortes + 27 ressurreicoes num unico log real).

    REGRA GERAL que sai daqui: teste de deteccao que filtra por UM tipo de
    evento nao prova ausencia dos outros.
    """

    def _aquecido(self, cal: Calibracao, solo: bool) -> tuple[Rastreador, Observacao]:
        rastreador = Rastreador(
            nomes=list(cal.nomes),
            nome_proprio=cal.nome_proprio,
            ajustes=Ajustes(),
            modo_solo=solo,
        )
        viva = extrair(frame_de_party(None), cal)
        assert viva.ui_visivel and viva.hp_proprio == 1.0, (
            "o frame de aquecimento parou de mostrar a party window com a "
            "barra propria cheia — o rastreador nao fica QUENTE e o teste "
            "passa a medir o comeco frio, que protege por acidente"
        )
        for i in range(20):
            rastreador.observar(viva, float(i))
        return rastreador, viva

    @pytest.mark.parametrize("solo", [False, True], ids=["party", "solo"])
    def test_trinta_ticks_de_inventario_nao_emitem_evento_de_tipo_nenhum(
        self, calibracao, solo
    ):
        rastreador, _ = self._aquecido(calibracao, solo)
        coberto = extrair(frame_solo("coberta_0"), calibracao)

        assert coberto.hp_proprio is None
        assert coberto.hp_proprio_aparente is not None, (
            "`coberta_0` parou de produzir leitura aparente: este teste deixou "
            "de exercitar o caminho que existe para vigiar"
        )

        eventos = alimentar(rastreador, coberto, 30, 100.0)

        assert eventos == [], (
            f"modo {'solo' if solo else 'party'}: abrir o inventario por 30 "
            f"ticks emitiu {[e.tipo.name for e in eventos]} — a leitura "
            f"aparente vazou para a maquina de estado"
        )

    @pytest.mark.parametrize("solo", [False, True], ids=["party", "solo"])
    def test_depois_de_uma_morte_REAL_o_inventario_nao_ressuscita_ninguem(
        self, calibracao, solo
    ):
        """O cenario que mais importa: morre, e ai abre o inventario.

        E o mais perigoso porque o alerta falso vem DEPOIS de um alerta
        verdadeiro — o grupo ja foi mobilizado, e um `RESSUSCITOU` falso manda
        todo mundo parar de socorrer alguem que continua morto.
        """
        rastreador, _ = self._aquecido(calibracao, solo)

        # Morte de verdade, com a party window VISIVEL: o portao de cegueira so
        # congela o veredito quando a tela some, e aqui ela nao some.
        morta = extrair(frame_de_party(QUASE_VAZIA), calibracao)
        assert morta.ui_visivel and morta.hp_proprio == 0.0
        eventos_da_morte = alimentar(rastreador, morta, 10, 100.0)

        assert [e.tipo for e in eventos_da_morte] == [TipoDeEvento.MORREU], (
            f"a morte REAL nao saiu como unico evento: "
            f"{[e.tipo.name for e in eventos_da_morte]}"
        )

        depois = alimentar(
            rastreador, extrair(frame_solo("coberta_0"), calibracao), 30, 200.0
        )

        assert depois == [], (
            f"modo {'solo' if solo else 'party'}: depois de uma morte real, "
            f"abrir o inventario emitiu {[e.tipo.name for e in depois]} — o "
            f"medido em 2026-08-27 para o desenho REJEITADO era "
            f"['RESSUSCITOU', 'VOCE_SEM_PARTY'] em party e ['RESSUSCITOU'] "
            f"em solo"
        )


class TestOAparenteNaoMudaNadaDoQueAMaquinaDeEstadoVe:
    """A conta que fecha a promessa: `hp_proprio` sai identico ao de hoje."""

    @pytest.mark.parametrize(
        ("rotulo", "widget", "esperado_proprio", "esperado_aparente"), AS_OITO_AMOSTRAS
    )
    def test_as_oito_amostras(
        self, calibracao, rotulo, widget, esperado_proprio, esperado_aparente
    ):
        obs = extrair(frame_solo(rotulo), cal_do_widget(calibracao, widget))

        if esperado_proprio is None:
            assert obs.hp_proprio is None, (
                f"{rotulo}: hp_proprio saiu {obs.hp_proprio!r} onde hoje sai "
                f"None — a maquina de estado passou a ver uma leitura nova"
            )
        else:
            assert obs.hp_proprio is not None
            assert abs(obs.hp_proprio - esperado_proprio) < 0.001, (
                f"{rotulo}: hp_proprio saiu {obs.hp_proprio!r} em vez de "
                f"{esperado_proprio} — o que alimenta os alertas MUDOU"
            )

        if esperado_aparente is None:
            assert obs.hp_proprio_aparente is None, (
                f"{rotulo}: a leitura aparente apareceu onde nao devia "
                f"({obs.hp_proprio_aparente!r})"
            )
        else:
            assert obs.hp_proprio_aparente is not None
            assert abs(obs.hp_proprio_aparente - esperado_aparente) < 0.001, (
                f"{rotulo}: a leitura aparente saiu "
                f"{obs.hp_proprio_aparente!r} em vez de {esperado_aparente}"
            )

    def test_o_rastreador_NAO_le_a_leitura_aparente(self):
        """TRIPWIRE DE ARQUITETURA, grosseiro de proposito.

        A seguranca desta mudanca nao vem de guarda nenhuma: vem de a leitura
        NAO EXISTIR para a maquina de estado. O jeito de verificar isso e ler o
        fonte do rastreador e exigir que o nome do campo nao esteja la.

        Se este teste quebrar, alguem promoveu uma leitura que pode vir de um
        recorte PARCIALMENTE OCLUIDO a fonte de decisao — e o custo medido disso
        e `voce_sem_party` falso, `ressuscitou` falso (inclusive em `--solo`) e
        morte atrasada.
        """
        fonte = (
            Path(__file__).parent.parent / "l2scanner" / "rastreador.py"
        ).read_text(encoding="utf-8")

        assert "hp_proprio_aparente" not in fonte, (
            "l2scanner/rastreador.py passou a ler a leitura APARENTE. A "
            "maquina de estado agora depende de uma leitura que pode vir de um "
            "recorte ocluido: `coberta_0` casa +0.999 com o inventario por "
            "cima da barra. Medido em 2026-08-27, o custo disso e "
            "`voce_sem_party` falso no tick 27, `ressuscitou` falso no tick 34 "
            "e uma morte em andamento atrasando do tick 18 para o 20."
        )


class TestOPortaoDeLeituraEstaAmarradoAoRastreador:
    """Duas camadas, um acoplamento numerico — e ele precisa de tripwire.

    `LEITURA_MINIMA_PARA_O_CASAMENTO` (visao.py) so protege enquanto for MAIOR
    que `Ajustes.fracao_hp_considerada_zero` (rastreador.py). Baixar o limiar de
    morte do rastreador anularia a trava A DISTANCIA, sem tocar em `visao.py` —
    e a revisao nem passaria perto do arquivo onde a propriedade mora.
    """

    def test_o_portao_de_leitura_fica_acima_do_limiar_de_morte(self):
        limiar_de_morte = Ajustes().fracao_hp_considerada_zero

        assert LEITURA_MINIMA_PARA_O_CASAMENTO > limiar_de_morte, (
            f"LEITURA_MINIMA_PARA_O_CASAMENTO ({LEITURA_MINIMA_PARA_O_CASAMENTO}) "
            f"deixou de ficar acima de fracao_hp_considerada_zero "
            f"({limiar_de_morte}): o braco novo voltou a poder certificar uma "
            f"leitura que o rastreador leria como MORTE"
        )
        assert LEITURA_MINIMA_PARA_O_CASAMENTO >= 2.5 * limiar_de_morte, (
            "a folga de 2.5x medida em 2026-08-27 encolheu; a exaustao das "
            "duas direcoes de oclusao foi verificada com ela e precisa ser "
            "refeita antes de o limiar descer"
        )


class TestOCasamentoTolera2pxDeDesalinhamento:
    """O motivo de a referencia DESLIZAR, medido em pixels reais.

    A versao de posicao FIXA cai de +0.972 para -0.179 com UM pixel de
    deslocamento. Deslizando, o casamento fica CONSTANTE ate a terceira casa em
    +-2 px — enquanto a moldura, no mesmo intervalo, pula de 12.64 a 32.33.

    Nada de `np.roll`: rolar inventa linhas. `escuro_faixa.png` tem 28 linhas
    justamente para que cada deslocamento venha de pixels reais do frame.

    E +-2 px E A TOLERANCIA INTEIRA. Em +-3 px o casamento cai para
    +0.293/+0.364, os dois abaixo do limiar, e a moldura reprova junto: nao ha
    rede alem disso, e o TODO registra isso como regime nao coberto.
    """

    def test_as_cinco_janelas_reais_casam_todas(self):
        faixa = recorte(ESCURO_FAIXA)
        casamentos = []
        molduras = []
        for dy in range(-2, 3):
            janela = faixa[2 + dy : 26 + dy]
            assert janela.shape == (24, 191, 3)
            casamentos.append(_casamento_do_perfil_proprio(janela))
            molduras.append(_moldura_da_barra_propria(janela))

        for dy, valor in zip(range(-2, 3), casamentos):
            assert valor >= CASAMENTO_MINIMO_DO_PERFIL_PROPRIO, (
                f"dy={dy:+d}: casamento {valor:.4f} abaixo de "
                f"{CASAMENTO_MINIMO_DO_PERFIL_PROPRIO} — a tolerancia de +-2 px "
                f"encolheu e a janela do jogo arrastada volta a calar a barra"
            )
            assert abs(valor - 0.9641) < 0.001, (
                f"dy={dy:+d}: casamento {valor:.4f}; o medido em 2026-08-27 e "
                f"+0.9641 CONSTANTE nas cinco janelas"
            )

        assert min(molduras) < 15.0 and max(molduras) > 30.0, (
            f"as molduras das mesmas 5 janelas ({[round(m, 2) for m in molduras]}) "
            f"deixaram de ser caoticas — o contraste entre o discriminador "
            f"ANTIGO (12.64..32.33) e o NOVO (constante) era metade do "
            f"argumento para trocar"
        )

    def test_a_janela_do_meio_e_a_fixture_principal(self):
        assert (recorte(ESCURO_FAIXA)[2:26] == recorte(ESCURO_CAUDA_VAZIA)).all()


class TestOCasamentoNasFixturesVERSIONADAS:
    """As duas classes, contra o discriminador novo — so o que o repo carrega.

    As populacoes grandes que o plano cita (45 livres de `recordings/inv2/`, 8
    cobertas de `recordings/inv3/`) NAO podem ser afirmadas aqui: `recordings/`
    esta no `.gitignore` e um clone limpo nao as tem. Este arquivo afirma sobre
    as fixtures VERSIONADAS; a parte de `recordings/` fica atras de
    `pytest.skip`, com a razao dita.
    """

    @pytest.mark.parametrize(
        ("rotulo", "esperado"),
        [
            ("livre_0", 1.0000),
            ("livre_1", 0.9992),
            ("livre_2", 0.9986),
            ("livre_3", 0.9963),
            ("escuro_cheia", 0.9439),
            ("escuro_cauda_vazia", 0.9641),
            (QUASE_VAZIA, 0.9793),
        ],
    )
    def test_as_livres_casam_alto(self, rotulo, esperado):
        valor = _casamento_do_perfil_proprio(recorte(rotulo))
        assert valor >= CASAMENTO_MINIMO_DO_PERFIL_PROPRIO, (
            f"{rotulo}: casamento {valor:.4f} abaixo do limiar — uma barra "
            f"LEGITIMA deixou de ser reconhecida"
        )
        assert abs(valor - esperado) < 0.001, (
            f"{rotulo}: casamento {valor:.4f} em vez de {esperado} medido"
        )

    @pytest.mark.parametrize(
        ("rotulo", "esperado"),
        [("coberta_1", 0.0000), ("coberta_2", 0.2356), ("coberta_3", 0.0729)],
    )
    def test_as_cobertas_TOTAIS_ficam_bem_abaixo(self, rotulo, esperado):
        """Estas tres sao as que liam 0% — as que viravam morte falsa."""
        valor = _casamento_do_perfil_proprio(recorte(rotulo))
        assert valor < CASAMENTO_MINIMO_DO_PERFIL_PROPRIO, (
            f"{rotulo}: casamento {valor:.4f} passou do limiar"
        )
        assert abs(valor - esperado) < 0.001, (
            f"{rotulo}: casamento {valor:.4f} em vez de {esperado} medido"
        )

    def test_a_coberta_PARCIAL_casa_alto_e_por_isso_a_leitura_e_APARENTE(self):
        """`coberta_0` casa +0.999 COM O INVENTARIO POR CIMA DA BARRA.

        E a razao inteira de a leitura ir para um campo separado. Casamento alto
        nao prova recorte LIVRE — prova estrutura horizontal visivel. Se um dia
        alguem quiser promover a leitura a `hp_proprio`, este numero e o que
        precisa ser explicado primeiro.
        """
        valor = _casamento_do_perfil_proprio(recorte("coberta_0"))
        assert valor > 0.99, (
            f"coberta_0 casa {valor:.4f}: se isto caiu, o argumento de que o "
            f"casamento nao distingue livre de parcialmente ocluido mudou, e a "
            f"decisao de desenho precisa ser revisitada — nao apagada"
        )

    def test_as_populacoes_de_recordings_nao_sao_afirmaveis_num_clone_limpo(self):
        if not (RECORDINGS / "inv2").is_dir() or not (RECORDINGS / "inv3").is_dir():
            pytest.skip(
                "recordings/ e gitignored: as 45 livres de inv2/ e as 8 "
                "cobertas de inv3/ nao existem num clone limpo. As fixtures "
                "VERSIONADAS acima cobrem as duas classes."
            )
        livres = sorted((RECORDINGS / "inv2").glob("*_propria.png"))
        assert livres, "recordings/inv2/ existe mas nao tem *_propria.png"
        for caminho in livres:
            px = cv2.imread(str(caminho))
            valor = _casamento_do_perfil_proprio(px)
            assert valor >= CASAMENTO_MINIMO_DO_PERFIL_PROPRIO, (
                f"{caminho.name}: casamento {valor:.4f} abaixo do limiar"
            )


class TestOBuracoPreExistenteDoBracoDeMoldura:
    """CARACTERIZACAO de um defeito que esta tarefa NAO cria e NAO fecha.

    `coberta_2` com o painel cobrindo o lado ESQUERDO da barra le 0.0000 com
    moldura 64.00 — acima do limiar de 60 — e ja e aceito HOJE por
    `barra_propria_legivel`. Isso e uma morte falsa por um caminho que NENHUM
    dos dois bracos cobre.

    Nao e fechavel por portao de leitura, e a razao e estrutural: o braco de
    MOLDURA precisa poder certificar leitura zero, porque e assim que a morte e
    anunciada em terreno de dia.

    Candidato MEDIDO para fechar: contiguidade do preenchimento (`sobra` = 0 nas
    51 amostras genuinas, 11..186 nos compostos de oclusao a esquerda). Ele so
    pode entrar depois de medido contra TERRENO VERMELHO — lava e chao
    avermelhado podem gerar colunas cheias espurias, e o modo de falha dessa
    heuristica e SILENCIO, que e o pior desfecho declarado do projeto.

    Registrado em
    `.planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md`.
    QUANDO ALGUEM FECHAR O BURACO, ESTE TESTE QUEBRA — de proposito, para
    obrigar a atualizar aquele registro em vez de deixa-lo envelhecer mentindo.
    """

    @pytest.mark.parametrize("k", [5, 20, 60])
    def test_o_painel_a_esquerda_le_zero_e_ja_passa_HOJE(self, calibracao, k):
        composto = np.hstack(
            [recorte("coberta_2")[:, :k], recorte("livre_0")[:, k:]]
        )
        leitura = medir_barra(
            composto, regiao_inteira(composto), calibracao.limiares_hp
        )
        moldura = _moldura_da_barra_propria(composto)

        assert leitura == 0.0, f"k={k}: leitura {leitura:.4f}, esperado 0.0000"
        assert abs(moldura - 64.00) < 0.05, f"k={k}: moldura {moldura:.2f}"
        assert barra_propria_legivel(composto), (
            f"k={k}: o buraco PRE-EXISTENTE do braco de moldura fechou. Isso e "
            f"uma boa noticia — e o TODO "
            f"2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md "
            f"precisa ser atualizado, porque ele ainda registra este caminho "
            f"como aberto."
        )

    def test_o_braco_NOVO_recusa_o_mesmo_composto(self, calibracao):
        """A metade que ESTA tarefa garante: o braco novo nao piora o buraco.

        Ele nao FECHA (o composto ja passa pelo braco de moldura, que roda
        antes), mas tambem nao acrescenta um segundo caminho para a mesma morte
        falsa.
        """
        composto = np.hstack([recorte("coberta_2")[:, :5], recorte("livre_0")[:, 5:]])
        leitura = medir_barra(
            composto, regiao_inteira(composto), calibracao.limiares_hp
        )
        assert not _braco_do_casamento(composto, leitura)
