"""O texto CIANO da coluna Total Price, e por que ele le `8` onde ha `0`.

O DEFEITO, EM UMA FRASE
-----------------------
Os 13 moldes foram cortados de uma mascara feita com piso de brilho ABSOLUTO
(`V > 180`) sobre texto BRANCO, cujo pico de V vale 226-230. Nesse brilho as
hastes laterais antisserrilhadas do `0` caem em V = 160-177, ABAIXO do piso, e
somem da mascara — o molde `0` gravado e um anel PARTIDO de 8 pixels de tinta.
O ciano desenha o MESMO glifo com pico 255; as MESMAS hastes sobem para
V = 181-199, passam do MESMO piso absoluto e SOBREVIVEM — a mascara observada e
um anel FECHADO de 16 pixels. Anel fechado casa melhor com o molde `8` (que tem
hastes) do que com o molde `0` (que nao tem).

    o molde '0' gravado        a observacao CIANA        o molde '8' gravado
       .##.   (8 px)              .##.   (16 px)            .##.   (13 px)
       #..#                       #..#                      #..#
       ....   <- hastes           #..#   <- hastes          #..#
       ....      APAGADAS         #..#      PRESENTES       .#..
       ....      no corte         #..#                      #..#
       ....                       #..#                      ....
       #..#                       #..#                      #..#
       .##.                       .##.                      .##.

    scores da observacao ciana:  8 = 0,7242   0 = 0,5976
    scores da observacao branca: 0 = 1,0000   8 = 0,7110

O piso e ABSOLUTO; o brilho do glifo NAO E. Logo a forma que um molde codifica
so se reproduz no brilho em que ele foi cortado.

O QUE ISSO **NAO** E — TRES HIPOTESES MEDIDAS E MORTAS
-------------------------------------------------------
1. NAO e o par `0`x`8` ser ambiguo. Na MESMA linha, com os MESMOS digitos, a
   coluna do incremento (branca) le `50,00` certo enquanto a do total (ciana)
   devolve `188,88`. O `0` branco casa 1,0000 contra 0,7110 do `8`.

2. NAO e a conversao ponderada para cinza penalizar o vermelho (`0,299*R`).
   NAO HA conversao ponderada neste caminho: `mascara_de_numero` usa o canal V
   do HSV, que E `max(B,G,R)` por definicao. Medido: `V == max(B,G,R)` em
   450.000 pixels do bloco da grade, ZERO divergencias. Normalizar por canal e
   um NO-OP — ja e o que o codigo faz. `TestOCanalVJaEOMaximo` prende isso.

3. NAO e a largura do run mudar. Branca e ciana dao run de 4 px para o `0`, e
   duas linhas CIANAS do mesmo frame com larguras IDENTICAS `[4,4,4,1,4,4]`
   leem uma `188,88` e a outra `100,00`. `TestALarguraDoRunNaoDiscrimina`
   prende isso.

POR QUE NENHUM PISO DE BRILHO RESOLVE — O CONJUNTO ADMISSIVEL E UM PONTO
-------------------------------------------------------------------------
Varrido o piso sobre o material que tem o CASO DIFICIL (branco e ciano na mesma
pagina, mais o run colado de 11 px de `frame_000105.png` L6, cuja verdade
`149,44` esta documentada em `larguras_com_folga`):

    piso <= 182  ->  `149,44` OK,  zeros cianos 0/5   (o defeito de hoje)
    piso >= 183  ->  zeros cianos 5/5,  `149,44` vira `149,99`

A intersecao e VAZIA. Nem um piso proporcional ao pico salva: normalizando pelo
fundo e pelo pico (`piso = fundo + k*(pico-fundo)`, com trava em 180) o conjunto
admissivel de `k` e o PONTO 0,64 —

    k = 0,63  ->  INVENTA `360,00` onde a tela diz `380,00`  (falha ABERTA)
    k = 0,64  ->  os tres casos passam
    k = 0,65  ->  quebra o `149,44` documentado

Zero folga dos dois lados. Isso nao e um vale, e um fio de navalha ajustado a
exatamente as tres restricoes para as quais existe material. A razao e a
mecanica: um piso e UM escalar, e cada glifo cruza o limiar num ritmo proprio —
subir o piso conserta o `0` (anel fecha) e ARRUINA o `4` (a barra horizontal
erode e ele vira `9`). Por isso a correcao tem de vir de MOLDES cortados na
curva tonal do ciano, e nao de mexer no piso.

O CONTROLE NEGATIVO MORA AQUI DENTRO
-------------------------------------
`TestOCaminhoDaNegociacaoNaoMuda` reafirma as nove linhas BRANCAS da fixtura e o
`149,44` do run colado. Qualquer correcao do ciano que mexa em
`ler_celula_de_numero` ou na segmentacao tem de deixar esses dois intactos — foi
o caminho conferido em campo (353 paginas lidas contra 2 perdidas).
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner import mercado_leitura
from l2scanner.calibracao import Calibracao
from l2scanner.identidade import VALOR_MINIMO_DO_TEXTO
from l2scanner.mercado_visao import (
    RastreioDoPainel,
    ancoras_de_calibracao,
    casamento_da_ancora,
    glifos_de_calibracao,
)

FIXTURES = Path(__file__).parent / "fixtures" / "mercado"
CALIBRACAO = FIXTURES / "calibracao_de_fixture.json"
JANELA_ADENA = FIXTURES / "janela_adena_f014.png"
GLIFOS_COLADOS_TOTAL_F105 = FIXTURES / "glifos_colados_total_f105.png"

# A linha CIANA da fixtura, e a UNICA dela. A tela diz `135,00`; a leitura de
# hoje devolve `135,88`. A verdade de campo esta na docstring de
# `ler_linha_de_adena` e na de `tests/test_mercado_adena.py`, e ela nao e
# suposicao: foi lida do proprio frame.
LINHA_CIANA = 5
TOTAL_NA_TELA = "135,00"

# As nove linhas BRANCAS da fixtura, com a leitura MEDIDA hoje. Elas sao o
# CONTROLE NEGATIVO: nenhuma correcao do ciano pode move-las.
TOTAIS_BRANCOS = {
    0: "62,00",
    1: "64,99",
    2: "65,00",
    3: "66,00",
    4: "67,00",
    6: "68,00",
    7: "68,50",
    8: "70,00",
    9: "70,00",
}


def ler_fixtura(caminho: Path) -> np.ndarray:
    imagem = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
    assert imagem is not None, caminho
    return imagem


@pytest.fixture(scope="module")
def cal() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO)


@pytest.fixture(scope="module")
def moldes(cal: Calibracao) -> dict:
    return glifos_de_calibracao(cal.mercado_templates_de_digito)


@pytest.fixture(scope="module")
def janela() -> np.ndarray:
    return ler_fixtura(JANELA_ADENA)


def recorte_do_total(cal, janela, indice: int) -> np.ndarray:
    """A coluna `Total Price` de UMA linha, pelos retangulos de NEGOCIACAO.

    A grade da Adena tem o mesmo `dx`, `dy`, altura de linha e largura da de
    negociacao — medido, e ja reusado por `test_mercado_adena.py`.
    """
    rastreio = RastreioDoPainel(
        ancoras_de_calibracao(cal.mercado_ancoras),
        float(cal.mercado_limiar_da_ancora),
    )
    voto = rastreio.observar(janela)
    assert voto.aberto and rastreio.origem is not None
    ox, oy = rastreio.origem
    grade = cal.mercado_grade
    altura = int(grade["altura_da_linha"])
    topo = oy + int(grade["dy"]) + indice * altura
    coluna = cal.mercado_coluna_do_total
    x = ox + int(coluna["dx"])
    return janela[topo : topo + altura, x : x + int(coluna["largura"])]


def ler(cal, moldes, recorte, *, piso_de_brilho: int = VALOR_MINIMO_DO_TEXTO):
    return mercado_leitura.ler_celula(
        recorte,
        moldes,
        float(cal.mercado_limiar_de_leitura_de_glifo),
        float(cal.mercado_margem_de_leitura_de_glifo),
        valor_minimo=piso_de_brilho,
        folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
    )


class TestOCanalVJaEOMaximo:
    """Normalizar por canal e um NO-OP: `mascara_de_numero` ja usa `max(B,G,R)`.

    Este teste existe para MATAR uma hipotese por medicao, e nao por argumento.
    A suspeita natural — "a conversao para cinza pondera o vermelho por 0,299,
    entao o ciano perde borda" — descreve `cv2.COLOR_BGR2GRAY`, que NAO esta
    neste caminho. `mascara_de_numero` faz `cvtColor(..., COLOR_BGR2HSV)` e usa
    o canal V, e V e definido como `max(B,G,R)`. Trocar um pelo outro nao mudaria
    um pixel.
    """

    def test_o_canal_v_e_exatamente_o_maximo_dos_tres(self, janela):
        v = cv2.cvtColor(janela, cv2.COLOR_BGR2HSV)[:, :, 2]
        assert np.array_equal(v, janela.max(axis=2))

    def test_e_o_ciano_nao_e_mais_escuro_em_v_e_sim_mais_claro(
        self, cal, janela
    ):
        """O ciano tem brilho ALTO. O problema nunca foi passar do corte."""
        ciano = recorte_do_total(cal, janela, LINHA_CIANA)
        branco = recorte_do_total(cal, janela, 0)

        def pico(recorte):
            return int(cv2.cvtColor(recorte, cv2.COLOR_BGR2HSV)[:, :, 2].max())

        assert pico(ciano) > pico(branco)
        assert pico(ciano) == 255 and pico(branco) == 230


class TestOMoldeDoZeroEUmAnelPartido:
    """A causa, no molde gravado: o `0` perdeu as hastes laterais no corte.

    O `8` tem hastes nas linhas 2 e 4; o `0` nao tem tinta NENHUMA nas linhas
    2 a 5. Nao e defeito do molde — e o registro fiel do que o piso 180 deixa
    passar sobre texto branco. E e exatamente por isso que ele nao descreve o
    mesmo glifo desenhado mais claro.
    """

    def test_o_molde_do_zero_nao_tem_hastes_no_meio(self, moldes):
        zero = moldes["0"]
        assert zero.shape == (9, 4)
        assert int((zero > 0).sum()) == 8
        assert not zero[2:6, :].any(), "o `0` gravado nao tem tinta no meio"

    def test_o_molde_do_oito_tem_hastes_no_meio(self, moldes):
        oito = moldes["8"]
        assert oito.shape == (9, 4)
        assert int((oito > 0).sum()) == 13
        assert oito[2, :].any() and oito[4, :].any()


def glifos_da_celula(recorte, moldes, piso_de_brilho=VALOR_MINIMO_DO_TEXTO):
    faixa, runs = mercado_leitura.segmentar_glifos_no_brilho(
        recorte, piso_de_brilho
    )
    mascara = (
        mercado_leitura.mascara_de_numero(recorte, piso_de_brilho) * 255
    ).astype(np.uint8)
    topo, base = faixa
    return [mascara[topo:base, ini:fim] for ini, fim in runs]


class TestALarguraDoRunNaoDiscrimina:
    """A largura do run e a MESMA em branco e em ciano. Nao e por ali.

    O `0` sai com 4 px de largura nos dois casos. O que muda e a TINTA DENTRO
    do run — 8 pixels no branco contra 16 no ciano —, e e a tinta que decide o
    casamento.
    """

    def test_o_zero_tem_a_mesma_largura_em_branco_e_em_ciano(
        self, cal, janela, moldes
    ):
        ciano = glifos_da_celula(
            recorte_do_total(cal, janela, LINHA_CIANA), moldes
        )
        branco = glifos_da_celula(recorte_do_total(cal, janela, 0), moldes)
        # `135,88` e `62,00`: os dois ultimos glifos sao o par de `0` da tela.
        assert ciano[-1].shape[1] == branco[-1].shape[1] == 4

    def test_o_anel_ciano_e_fechado_e_o_branco_e_partido(
        self, cal, janela, moldes
    ):
        ciano = glifos_da_celula(
            recorte_do_total(cal, janela, LINHA_CIANA), moldes
        )[-1]
        branco = glifos_da_celula(recorte_do_total(cal, janela, 0), moldes)[-1]
        assert int((branco > 0).sum()) == 8, "no branco as hastes somem"
        assert int((ciano > 0).sum()) == 16, "no ciano as hastes sobrevivem"

    def test_e_o_anel_fechado_casa_melhor_com_oito_do_que_com_zero(
        self, cal, janela, moldes
    ):
        """A falha e ABERTA: ela nao empata, ela vence com folga no rotulo errado."""
        ciano = glifos_da_celula(
            recorte_do_total(cal, janela, LINHA_CIANA), moldes
        )[-1]

        def score(rotulo):
            a, b = mercado_leitura._alinhar_por_preenchimento(
                ciano, moldes[rotulo]
            )
            return float(casamento_da_ancora(a, b))

        assert score("8") > score("0")
        assert score("8") - score("0") > float(
            cal.mercado_margem_de_leitura_de_glifo
        ), "a margem nao segura: o erro passa confiante"


class TestOCaminhoDaNegociacaoNaoMuda:
    """O CONTROLE NEGATIVO. Estas leituras sao o caminho conferido em campo.

    Qualquer correcao do ciano que toque `ler_celula_de_numero`, a segmentacao
    ou o piso de brilho tem de deixar estas duas coisas intactas. Elas estao
    aqui, e nao no modulo do ciano, para que a correcao nao possa ser aceita sem
    passar por elas.
    """

    @pytest.mark.parametrize("indice,esperado", sorted(TOTAIS_BRANCOS.items()))
    def test_as_linhas_brancas_leem_o_mesmo(
        self, cal, janela, moldes, indice, esperado
    ):
        assert ler(cal, moldes, recorte_do_total(cal, janela, indice)) == esperado

    def test_o_run_colado_de_11px_continua_lendo_149_44(self, cal, moldes):
        """A verdade documentada em `larguras_com_folga`, e o limite superior
        de qualquer piso: com piso >= 183 esta celula vira `149,99`."""
        assert ler(cal, moldes, ler_fixtura(GLIFOS_COLADOS_TOTAL_F105)) == "149,44"


class TestOTotalCianoSeLe:
    """O ALVO. Hoje ele falha: a tela diz `135,00` e a leitura devolve `135,88`.

    Ele passa quando a leitura souber lidar com a curva tonal do ciano — e a
    medicao ja disse que isso NAO pode vir de mexer no piso de brilho (ver a
    docstring do modulo: o conjunto admissivel e um ponto, sem folga).
    """

    def test_a_linha_ciana_le_o_que_esta_na_tela(self, cal, janela, moldes):
        assert ler(cal, moldes, recorte_do_total(cal, janela, LINHA_CIANA)) == (
            TOTAL_NA_TELA
        )

    def test_e_a_falha_de_hoje_e_trocar_zero_por_oito(
        self, cal, janela, moldes
    ):
        """A ASSINATURA do defeito, presa para que a correcao seja reconhecivel.

        Enquanto o defeito existir esta leitura e `135,88`. Quando ele morrer
        este teste deve ser APAGADO junto — ele descreve o defeito, nao o
        contrato.
        """
        lido = ler(cal, moldes, recorte_do_total(cal, janela, LINHA_CIANA))
        assert lido in (TOTAL_NA_TELA, "135,88")


# ---------------------------------------------------------------------------
# A METADE B — a tinta que os moldes NAO descrevem cai FECHADA
# ---------------------------------------------------------------------------
#
# O QUE ESTA METADE FAZ, e o que ela deliberadamente NAO faz.
#
# Ela NAO ensina o leitor a ler ciano — isso e a metade A, e o teste vermelho de
# `TestOTotalCianoSeLe` continua vermelho depois desta. Ela faz o leitor
# RECONHECER que nao sabe ler aquela celula, e RECUSAR em vez de adivinhar.
#
# POR QUE A RECUSA E NECESSARIA MESMO ONDE A LEITURA ACERTA — e esta e a medicao
# que decide o desenho. Duas celulas CIANAS, mesma cor (saturacao mediana 117 e
# 116), mesmos moldes, resultados OPOSTOS:
#
#     janela_negociacao_f010.png L4     o anel do `0` sai PARTIDO  ->  100,00 ok
#     janela_tooltip_f012.png    L3     o anel do `0` sai FECHADO  ->  158,88 ERRO
#
# O que decide e o antisserrilhamento daquele glifo naquela posicao, e ele NAO
# aparece na leitura. Um `100,00` ciano e um `158,88` ciano chegam com a mesma
# confianca e a mesma cara. Nao existe peneira a jusante que separe os dois,
# porque a informacao que os separa ja se perdeu na mascara.
#
# E O CRUZAMENTO NAO PEGA, POR CONSTRUCAO. Com quantidade 1 o `Total` e o
# `Unit price` sao a MESMA celula desenhada duas vezes: os dois erram IDENTICO,
# o residuo da 0 e a guarda fecha EM CIMA do erro. Medido nas tres linhas
# cianas de quantidade 1 das fixturas versionadas — `f010 L4` (residuo 0),
# `tooltip L8` (residuo 0) e `tooltip L9` (residuo 0). A guarda nao esta fraca:
# ela esta CEGA a este defeito.
#
# O PREDITIVO, E POR QUE ELE E A SATURACAO E NAO A RAZAO `R / max(B,G)`
# ----------------------------------------------------------------------
# O enunciado propunha `R / max(B,G)` (branco 1,000 contra ciano 0,544-0,557).
# Medido, ele e um detector de CIANO e nao de croma: entre as celulas que ele
# chama de acromaticas a razao vai a 1,8651 e a saturacao a 186,96 — amarelo e
# vermelho passam ilesos, porque num pixel amarelo `R / max(B,G)` vale 1,0.
#
# A SATURACAO MEDIANA DA TINTA e cega a matiz e mede exatamente a pergunta
# certa: "esta tinta e CINZA, que e a curva tonal em que os 13 moldes foram
# cortados?". Varridas 4.248 celulas de numero (4.028 de negociacao em 176
# frames de 9 gravacoes, e 220 da aba Adena em 11 frames), das quais 3.823 leem
# hoje:
#
#     tinta ACROMATICA  (3.422 celulas):  mediana da saturacao  min 0   max 0
#     tinta CROMATICA   (  401 celulas):  mediana da saturacao  113 a 118
#                                          (+1 artefato de scroll em 59)
#
# O lado branco nao e "perto de zero": e ZERO em todas as 3.422. E TODO limiar
# de 0 a 56 produz a MESMA particao dessas 3.823 celulas — um plato de 57
# niveis, contra o fio de navalha de folga ZERO do piso de brilho.
#
# O CONTROLE NEGATIVO AQUI E ESTRUTURAL, E NAO ESTATISTICO
# ---------------------------------------------------------
# `ler_celula`, `ler_celula_de_numero`, `mascara_de_numero` e a segmentacao
# ficaram BYTE A BYTE INTACTAS. O portao mora em `ler_linha` e
# `ler_linha_de_adena`, ANTES da leitura, e ele so olha celula cromatica. Uma
# celula acromatica portanto percorre o MESMO caminho de antes — nao "um caminho
# medido como equivalente", o mesmo caminho. E por isso que
# `test_o_run_colado_de_11px_continua_lendo_149_44` continua verde sem uma
# linha de mudanca: ele chama `ler_celula`, que ninguem tocou.
#
# O CUSTO, DECLARADO E NAO ESCONDIDO
# -----------------------------------
# 313 das 3.603 celulas de numero de negociacao que leem hoje (8,7%) passam a
# ser recusadas, e 120 delas terminam em `88` — a assinatura do defeito. As
# outras 193 leem CERTO hoje, e o `149,44` documentado esta entre elas. Elas
# sao perdidas de proposito: "nao coletou" vence "coletou errado", e o leitor
# nao tem como saber de que lado cada uma esta. A metade A e quem as devolve.


def ler_linha_da_fixtura(cal, moldes, janela, indice: int):
    """UMA linha inteira pelo caminho de PRODUCAO da negociacao.

    Existe porque o defeito desta metade nao e da celula: e do que a LINHA faz
    com uma celula que nao devia ter sido lida. Testar so `ler_celula` mediria o
    andar de baixo e deixaria passar exatamente o que corrompe o CSV.
    """
    rastreio = RastreioDoPainel(
        ancoras_de_calibracao(cal.mercado_ancoras),
        float(cal.mercado_limiar_da_ancora),
    )
    voto = rastreio.observar(janela)
    assert voto.aberto and rastreio.origem is not None
    ox, oy = rastreio.origem
    grade = cal.mercado_grade
    altura = int(grade["altura_da_linha"])
    topo = oy + int(grade["dy"]) + indice * altura

    def coluna(rect):
        x = ox + int(rect["dx"])
        return janela[topo : topo + altura, x : x + int(rect["largura"])]

    faixa = janela[
        topo : topo + altura,
        ox + int(grade["dx"]) : ox + int(grade["dx"]) + int(grade["largura"]),
    ]
    return mercado_leitura.ler_linha(
        indice,
        faixa,
        coluna(cal.mercado_coluna_do_nome),
        coluna(cal.mercado_coluna_do_total),
        coluna(cal.mercado_coluna_da_quantidade),
        coluna(cal.mercado_coluna_do_unitario),
        moldes=moldes,
        piso=float(cal.mercado_limiar_de_leitura_de_glifo),
        margem=float(cal.mercado_margem_de_leitura_de_glifo),
        valor_minimo_do_numero=VALOR_MINIMO_DO_TEXTO,
        valor_minimo_da_quantidade=int(
            cal.mercado_limiar_de_brilho_da_quantidade
        ),
        folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
        sonda=cal.mercado_sonda_do_fundo,
        limiar_de_dispersao=float(cal.mercado_limiar_de_dispersao_do_fundo),
        tolerancia_do_cruzamento=cal.mercado_tolerancia_do_cruzamento,
        trava_da_observacao=mercado_leitura.TravaDaObservacao(),
        catalogo={},
        corte_de_similaridade=float(cal.mercado_corte_de_similaridade),
        piso_de_similaridade=float(cal.mercado_piso_de_similaridade),
        ler_texto=lambda _img: "Item De Teste",
        ler_texto_conferencia=lambda _img: "Item De Teste",
    )


def ler_linha_de_adena_da_fixtura(cal, moldes, janela, indice: int):
    """UMA linha inteira pelo caminho de PRODUCAO da aba Adena."""
    rastreio = RastreioDoPainel(
        ancoras_de_calibracao(cal.mercado_ancoras),
        float(cal.mercado_limiar_da_ancora),
    )
    voto = rastreio.observar(janela)
    assert voto.aberto and rastreio.origem is not None
    ox, oy = rastreio.origem
    grade = cal.mercado_grade
    altura = int(grade["altura_da_linha"])
    topo = oy + int(grade["dy"]) + indice * altura
    colunas = cal.mercado_layouts["adena"]["colunas"]

    def coluna(rect):
        x = ox + int(rect["dx"])
        return janela[topo : topo + altura, x : x + int(rect["largura"])]

    faixa = janela[
        topo : topo + altura,
        ox + int(grade["dx"]) : ox + int(grade["dx"]) + int(grade["largura"]),
    ]
    return mercado_leitura.ler_linha_de_adena(
        indice,
        faixa,
        coluna(colunas["total"]),
        coluna(colunas["unitario"]),
        moldes=moldes,
        piso=float(cal.mercado_limiar_de_leitura_de_glifo),
        margem=float(cal.mercado_margem_de_leitura_de_glifo),
        valor_minimo_do_numero=VALOR_MINIMO_DO_TEXTO,
        folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
        sonda=cal.mercado_sonda_do_fundo,
        limiar_de_dispersao=float(cal.mercado_limiar_de_dispersao_do_fundo),
        catalogo={},
    )


@pytest.fixture(scope="module")
def janela_negociacao() -> np.ndarray:
    return ler_fixtura(FIXTURES / "janela_negociacao_f010.png")


@pytest.fixture(scope="module")
def janela_tooltip() -> np.ndarray:
    return ler_fixtura(FIXTURES / "janela_tooltip_f012.png")


# As linhas ACROMATICAS de `janela_negociacao_f010.png` que viram dado hoje, com
# o valor MEDIDO. Elas sao o CONTROLE NEGATIVO NO NIVEL DA LINHA — o nivel em
# que o portao desta metade mora. `(total_em_centesimos, quantidade)`.
LINHAS_BRANCAS_DA_NEGOCIACAO = {
    5: (300, 1),
    6: (1890, 2),
    7: (750, 1),
    8: (1800, 3),
    9: (245, 1),
}


class TestOPreditivoDeRecusa:
    """A SATURACAO MEDIANA DA TINTA, e o vale que ela mede.

    Aqui se prende o NUMERO, para que a proxima sessao nao precise reconquistar
    a medicao — e para que baixar o limiar por palpite quebre um teste.
    """

    def test_a_tinta_branca_tem_saturacao_mediana_exatamente_zero(
        self, cal, janela
    ):
        for indice in sorted(TOTAIS_BRANCOS):
            recorte = recorte_do_total(cal, janela, indice)
            assert (
                mercado_leitura.saturacao_da_tinta(
                    recorte, VALOR_MINIMO_DO_TEXTO
                )
                == 0.0
            ), f"linha {indice}"

    def test_e_a_tinta_ciana_fica_entre_113_e_118(self, cal, janela):
        medida = mercado_leitura.saturacao_da_tinta(
            recorte_do_total(cal, janela, LINHA_CIANA), VALOR_MINIMO_DO_TEXTO
        )
        assert 113.0 <= medida <= 118.0

    def test_o_limiar_cai_DENTRO_do_vale_medido(self):
        """0 de um lado, 59 do outro (o menor cromatico medido em campo)."""
        assert 0 < mercado_leitura.LIMIAR_DE_SATURACAO_DA_TINTA < 59

    def test_o_portao_separa_as_duas_populacoes_da_fixtura(self, cal, janela):
        cromaticas = {
            indice
            for indice in range(10)
            if mercado_leitura.tinta_fora_da_curva_dos_moldes(
                recorte_do_total(cal, janela, indice), VALOR_MINIMO_DO_TEXTO
            )
        }
        assert cromaticas == {LINHA_CIANA}

    def test_celula_sem_tinta_nao_e_recusada_por_cor(self):
        """Sem tinta nao ha cor a julgar — quem recusa vazio e a gramatica."""
        vazio = np.zeros((45, 209, 3), dtype=np.uint8)
        assert not mercado_leitura.tinta_fora_da_curva_dos_moldes(
            vazio, VALOR_MINIMO_DO_TEXTO
        )
        assert (
            mercado_leitura.saturacao_da_tinta(vazio, VALOR_MINIMO_DO_TEXTO)
            is None
        )

    def test_o_portao_nunca_levanta(self):
        """Ele roda DENTRO do tick, no modelo do resto do modulo."""
        assert not mercado_leitura.tinta_fora_da_curva_dos_moldes(
            None, VALOR_MINIMO_DO_TEXTO
        )
        assert not mercado_leitura.tinta_fora_da_curva_dos_moldes(
            np.zeros((0, 0, 3), dtype=np.uint8), VALOR_MINIMO_DO_TEXTO
        )


class TestATintaCianaCaiFechadaNaNegociacao:
    """O ALVO DESTA METADE. A linha ciana da negociacao para de virar dado."""

    def test_a_linha_ciana_de_quantidade_1_vira_DESCARTE(
        self, cal, moldes, janela_negociacao
    ):
        """`f010 L4`: ciana, quantidade 1, e ACEITA hoje com residuo 0."""
        resultado = ler_linha_da_fixtura(cal, moldes, janela_negociacao, 4)
        assert isinstance(resultado, mercado_leitura.Descarte)
        assert resultado.motivo == mercado_leitura.MOTIVO_DA_TINTA

    def test_o_cruzamento_fecha_EM_CIMA_do_erro_e_por_isso_nao_serve(
        self, cal, moldes, janela_negociacao
    ):
        """A prova de que a guarda existente NAO podia pegar isto.

        Com quantidade 1, `Total` e `Unit price` sao a mesma celula desenhada
        duas vezes: qualquer corrupcao entra IDENTICA nas duas, o residuo da 0
        e a guarda aprova. Este teste afirma a IDENTIDADE das duas leituras —
        e ela continua verdadeira depois do conserto, porque o conserto nao
        mexeu na leitura, e sim em quem a autoriza.
        """
        rastreio = RastreioDoPainel(
            ancoras_de_calibracao(cal.mercado_ancoras),
            float(cal.mercado_limiar_da_ancora),
        )
        rastreio.observar(janela_negociacao)
        ox, oy = rastreio.origem
        grade = cal.mercado_grade
        altura = int(grade["altura_da_linha"])
        topo = oy + int(grade["dy"]) + 4 * altura

        def celula(rect):
            x = ox + int(rect["dx"])
            recorte = janela_negociacao[
                topo : topo + altura, x : x + int(rect["largura"])
            ]
            return mercado_leitura.ler_celula_de_numero(
                recorte,
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )

        total = celula(cal.mercado_coluna_do_total)
        unitario = celula(cal.mercado_coluna_do_unitario)
        assert total == unitario
        assert mercado_leitura.residuo_do_cruzamento(total, unitario, 1) == 0

    def test_o_149_44_CIANO_tambem_e_recusado_e_isso_e_o_custo(
        self, cal, moldes, janela_tooltip
    ):
        """O `149,44` e CIANO, e ele LE CERTO hoje. Ainda assim cai.

        Medido: saturacao mediana 114 em `janela_tooltip_f012.png` L9, e 115,55
        no recorte versionado `glifos_colados_total_f105.png`, que vem da coluna
        Total de `053105-mercado-aberto/frame_000105.png` L6 — NEGOCIACAO.

        Ele nao cai por estar errado; cai porque nenhum molde BRANCO pode
        certificar tinta CIANA. O proprio arquivo de debug ja media que subir o
        piso de brilho transforma este mesmo `149,44` em `149,99`: a leitura
        certa de hoje e um acidente do antisserrilhamento, e nao uma garantia.
        """
        resultado = ler_linha_da_fixtura(cal, moldes, janela_tooltip, 9)
        assert isinstance(resultado, mercado_leitura.Descarte)
        assert resultado.motivo == mercado_leitura.MOTIVO_DA_TINTA

    def test_a_outra_linha_ciana_de_quantidade_1_tambem_cai(
        self, cal, moldes, janela_tooltip
    ):
        """`tooltip L8`: ciana, quantidade 1, aceita hoje como `134,40`."""
        resultado = ler_linha_da_fixtura(cal, moldes, janela_tooltip, 8)
        assert isinstance(resultado, mercado_leitura.Descarte)
        assert resultado.motivo == mercado_leitura.MOTIVO_DA_TINTA


class TestATintaCianaCaiFechadaNaAdena:
    """A Adena recusa pela TINTA, e nao mais pela aritmetica do cruzamento.

    A guarda de cruzamento da Adena ja derrubava estas linhas — ela e o motivo
    de o `.mercado/observacoes.csv` estar limpo, e ela NAO foi afrouxada. O que
    muda e QUEM recusa e QUANDO: a tinta recusa ANTES, e o motivo registrado
    passa a dizer a verdade ("nao sei ler esta cor") em vez de uma consequencia
    dela ("a aritmetica nao fechou").
    """

    def test_a_linha_ciana_da_adena_e_recusada_pela_TINTA(
        self, cal, moldes, janela
    ):
        resultado = ler_linha_de_adena_da_fixtura(
            cal, moldes, janela, LINHA_CIANA
        )
        assert isinstance(resultado, mercado_leitura.Descarte)
        assert resultado.motivo == mercado_leitura.MOTIVO_DA_TINTA


class TestOCaminhoBrancoNaoSEMOVE:
    """O CONTROLE NEGATIVO NO NIVEL DA LINHA, que e onde o portao mora.

    `TestOCaminhoDaNegociacaoNaoMuda` afirma a CELULA; esta classe afirma a
    LINHA INTEIRA, pelo caminho de producao, na mesma pagina em que a linha
    ciana e recusada. As duas juntas cobrem os dois andares que a metade B
    poderia ter quebrado.

    E a conferencia e por LEITURA CORRETA e nao por CONTAGEM DE ACEITAS: cada
    valor abaixo esta escrito, e um valor errado que continuasse sendo aceito
    reprovaria aqui — que e exatamente o que uma contagem de linhas aceitas
    NAO faz.
    """

    @pytest.mark.parametrize(
        "indice,esperado", sorted(LINHAS_BRANCAS_DA_NEGOCIACAO.items())
    )
    def test_as_linhas_brancas_continuam_virando_o_MESMO_dado(
        self, cal, moldes, janela_negociacao, indice, esperado
    ):
        resultado = ler_linha_da_fixtura(cal, moldes, janela_negociacao, indice)
        assert isinstance(resultado, mercado_leitura.LinhaLida)
        assert (
            resultado.total_em_centesimos,
            resultado.quantidade,
        ) == esperado

    def test_e_nenhuma_delas_e_recusada_por_tinta(
        self, cal, moldes, janela_negociacao
    ):
        for indice in LINHAS_BRANCAS_DA_NEGOCIACAO:
            resultado = ler_linha_da_fixtura(
                cal, moldes, janela_negociacao, indice
            )
            assert not isinstance(resultado, mercado_leitura.Descarte)
