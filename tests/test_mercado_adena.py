"""A aba Adena: a quantidade que se DERIVA, e o criterio que ja existia.

POR QUE A QUANTIDADE NAO SE LE
-------------------------------
A aba Adena nao tem coluna `Quantity`. O que ocupa o lugar do nome do item e a
coluna `Auction List`, e ela escreve a quantidade por extenso (`10,000,000
Adena`) — mas ela **nao se le com os moldes de digito deste projeto**, e isso
foi MEDIDO contra `tests/fixtures/mercado/janela_adena_f014.png` em sete pisos
de brilho (180, 200, 210, 220, 230, 240, 250): `ler_celula` devolve `None` nas
dez linhas em todos eles. Nao ha vale entre as populacoes de largura de run.

Medido nesta arvore, com o codigo de producao (`ler_celula_de_numero`, moldes e
retangulos de NEGOCIACAO, sobre `janela_adena_f014.png`):

    linha   Total Price   5 mln increment   coluna Quantity
      0        6200            6200              None
      1        6499            6499              None
      2        6500            6500              None
      3        6600            6600              None
      4        6700            6700              None
      5       13588            6750              None     <=== a tela diz 135,00
      6        6800            6800              None
      7        6850            6850              None
      8        7000            7000              None
      9        7000            7000              None

As duas colunas de MOEDA leem exatamente. A `Quantity` cai sobre vazio e falha
fechada de graca. Logo a quantidade vem das duas que leem, e nao da que nao le.

A LINHA 5 E A JUSTIFICATIVA DA FASE
------------------------------------
Na linha 5 a tela diz `135,00` e a leitura devolve `13588`: dois `0` lidos como
`8`, o par de margem mais estreita do sistema (0,0370). A gramatica passa
(`135,88` e um numero valido), a sonda de oclusao diz limpo (dispersao 0,0000
nas dez linhas) e o acordo entre dois frames CONCORDA no erro, porque os dois
frames leem os mesmos pixels. Sem uma guarda aritmetica isso entra no CSV como
taxa `135,88` — plausivel e errada.

O CRITERIO NAO E ESCOLHIDO, E REUSADO
--------------------------------------
`limite_derivado_do_cruzamento` ja existe com a derivacao escrita ao lado, e ela
DISCRIMINA os dois casos dificeis conhecidos:

    133,33 / 66,66  ->  n=2  residuo=1   limite=2,0  ->  ACEITA (com FOLGA)
    13588  / 6750   ->  n=2  residuo=88  limite=2,0  ->  REJEITA

O LIMITE DOBROU EM 2026-09-02 e esta tabela foi recomputada, nao reinterpretada:
a tela TRUNCA `total / quantidade` em vez de arredondar, o que da um centesimo
inteiro por unidade em vez de meio. Medido contra um gabarito de dez linhas
declarado por escrito ANTES da leitura, com quatro linhas discriminantes
truncando as quatro.

A DISCRIMINACAO SOBREVIVEU A DOBRA, e e isso que sustenta a fase: 1 contra 2,0
cabe, 88 contra 2,0 estoura por duas ordens de grandeza. O que NAO sobreviveu
foi o caso bom ser a testemunha do sinal `<=`: ele passava por IGUALDADE contra
o limite 1,0 e agora passa com folga contra 2,0. Quem prende o sinal e
`TestOSinalDaComparacao`, que INJETA o limite e nao depende da constante.
"""

from __future__ import annotations

import inspect
import logging
import math
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner import mercado_leitura
from l2scanner.calibracao import Calibracao
from l2scanner.identidade import VALOR_MINIMO_DO_TEXTO
from l2scanner.mercado_catalogo import (
    CHAVE_DA_SERIE_DA_ADENA,
    DIGITOS,
    NOME_EXIBIDO_DA_ADENA,
    SEPARADOR_DA_ASSINATURA,
    EntradaDoCatalogo,
    assinatura_por_ocr,
)
from l2scanner.mercado_leitura import (
    ADENA_POR_INCREMENTO,
    MOTIVO_DA_GRAMATICA,
    MOTIVO_DA_TINTA,
    MOTIVO_DA_OCLUSAO,
    MOTIVO_DO_CRUZAMENTO,
    Descarte,
    LinhaLida,
    ler_linha_de_adena,
    limite_derivado_do_cruzamento,
    quantidade_de_adena,
)
from l2scanner.mercado_visao import (
    RastreioDoPainel,
    ancoras_de_calibracao,
    glifos_de_calibracao,
)

FIXTURES = Path(__file__).parent / "fixtures" / "mercado"
CALIBRACAO = FIXTURES / "calibracao_de_fixture.json"
JANELA_ADENA = FIXTURES / "janela_adena_f014.png"
LINHA_VAZIA = FIXTURES / "linha_vazia_par.png"
LINHA_SOB_TOOLTIP = FIXTURES / "linha_sob_tooltip_f015.png"

# As leituras MEDIDAS nesta arvore com o codigo de producao sobre
# `janela_adena_f014.png` — ver a docstring do modulo. Elas nao sao suposicao:
# `tests/test_mercado_adena.py::TestAFixturaDaAdenaLeOQueODocstringDiz` as
# reafirma contra os pixels a cada rodada.
LEITURAS_DA_FIXTURA = {
    0: (6200, 6200),
    1: (6499, 6499),
    2: (6500, 6500),
    3: (6600, 6600),
    4: (6700, 6700),
    5: (13588, 6750),  # a tela diz 135,00 — a linha do defeito
    6: (6800, 6800),
    7: (6850, 6850),
    8: (7000, 7000),
    9: (7000, 7000),
}
LINHA_DO_DEFEITO = 5


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
def janela_adena() -> np.ndarray:
    return ler_fixtura(JANELA_ADENA)


def fatiar_a_linha_da_adena(cal, janela, indice: int) -> dict:
    """A linha e as colunas da Adena, com os retangulos de NEGOCIACAO.

    ISSO NAO E ATALHO, E MEDICAO: a grade da Adena tem o MESMO `dx`, o mesmo
    `dy`, a mesma altura de linha e a mesma largura da de negociacao. As colunas
    `Total` e `Unitario` de negociacao caem exatamente sobre `Total Price` e
    `5 mln increment` e leem os dez valores sem tocar um pixel de calibracao —
    ver `LEITURAS_DA_FIXTURA`, reafirmada contra os pixels a cada rodada.

    A coluna `quantidade` sai daqui tambem, e ela e o INSTRUMENTO da celula
    ILEGIVEL: na Adena a `Quantity` de negociacao cai sobre VAZIO e devolve
    `None` nas dez linhas. E um recorte REAL que genuinamente nao le, e nao um
    array de brinquedo montado para falhar.
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
    gx = ox + int(grade["dx"])
    topo = oy + int(grade["dy"]) + indice * altura
    saida = {"linha": janela[topo : topo + altura, gx : gx + int(grade["largura"])]}
    for nome, chave in (
        ("total", "mercado_coluna_do_total"),
        ("incremento", "mercado_coluna_do_unitario"),
        ("quantidade", "mercado_coluna_da_quantidade"),
    ):
        coluna = getattr(cal, chave)
        x = ox + int(coluna["dx"])
        saida[nome] = janela[topo : topo + altura, x : x + int(coluna["largura"])]
    return saida


def chamar_ler_linha_da_adena(
    cal,
    moldes,
    recortes: dict,
    indice: int,
    catalogo=None,
    *,
    recorte_do_total=None,
    recorte_do_incremento=None,
    recorte_da_linha=None,
):
    """`ler_linha_de_adena` direto, com todo limiar vindo da calibracao.

    Nenhum parametro tem valor de fabrica na funcao real — o charter do modulo
    proibe —, entao todos chegam aqui explicitos, e nenhum deles e escolhido
    pelo teste: todos saem de `calibracao_de_fixture.json`, que os copia
    VERBATIM do `calibration.json` de producao.

    NAO HA LEITORA DE TEXTO NESTA CHAMADA, e nao ha onde encaixar uma: e essa a
    afirmacao que `TestNadaAquiLeNome` transforma em teste de assinatura.
    """
    return ler_linha_de_adena(
        indice,
        recortes["linha"] if recorte_da_linha is None else recorte_da_linha,
        recortes["total"] if recorte_do_total is None else recorte_do_total,
        recortes["incremento"]
        if recorte_do_incremento is None
        else recorte_do_incremento,
        moldes=moldes,
        piso=float(cal.mercado_limiar_de_leitura_de_glifo),
        margem=float(cal.mercado_margem_de_leitura_de_glifo),
        valor_minimo_do_numero=VALOR_MINIMO_DO_TEXTO,
        folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
        sonda=cal.mercado_sonda_do_fundo,
        limiar_de_dispersao=float(cal.mercado_limiar_de_dispersao_do_fundo),
        catalogo={} if catalogo is None else catalogo,
    )


class TestOsDoisCasosDificeis:
    """O par que da valor um ao outro: eles discriminam em sentidos OPOSTOS.

    ESTA CLASSE TINHA UM SEGUNDO PROPOSITO ATE 2026-09-02, E ELE MORREU: com o
    limite derivado em meio centesimo por unidade o caso bom passava por
    IGUALDADE (residuo 1 contra 1,0), e por isso ele testemunhava tambem o sinal
    `<=`. O limite dobrou (a tela TRUNCA, medido em campo) e o caso bom passou a
    passar com FOLGA (1 contra 2,0). A testemunha do sinal se mudou por inteiro
    para `TestOSinalDaComparacao`, que injeta o limite e por isso nao depende do
    valor da constante - onde essa propriedade devia ter morado desde sempre.

    O QUE SOBREVIVEU, e e o que esta classe mede: a DISCRIMINACAO. 1 contra 2,0
    cabe; 88 contra 2,0 estoura por duas ordens de grandeza.
    """

    def test_aceita_o_arredondamento_de_133_33_por_66_66(self) -> None:
        """A captura do usuario de 2026-09-01, 17h: 10M de adena por 133,33 XM.

        `round(13333 / 6666) = 2`, e `|13333 - 2 x 6666| = 1` contra o limite
        derivado `2 x 1,0 = 2,0`. PASSA COM FOLGA - e ate 2026-09-02 passava
        raspando, contra o limite 1,0 da hipotese do arredondamento.
        """
        assert quantidade_de_adena(13333, 6666) == (10_000_000, 2)

    def test_rejeita_a_linha_5_da_fixtura(self) -> None:
        """`13588` por `6750`: a substituicao `0`x`8` que a fase existe para pegar.

        `round(13588 / 6750) = 2`, e `|13588 - 2 x 6750| = 88` contra o limite
        derivado `2,0`. Sem esta recusa a taxa `135,88` entraria no CSV. A
        justificativa da Fase 5 SOBREVIVE a dobra do limite: 88 nao chega perto
        de 2,0, e nao chegaria perto nem de 20.
        """
        assert quantidade_de_adena(13588, 6750) is None

    def test_a_aceitacao_do_caso_bom_e_por_FOLGA_desde_a_medicao_de_02_09(
        self,
    ) -> None:
        """A conta explicita, recomputada contra o limite do TRUNCAMENTO.

        Ela dizia `limite == 1.0` e se chamava `..._por_IGUALDADE_e_nao_por_folga`.
        Deixar o nome antigo em teste verde seria manter no repositorio uma
        afirmacao que a constante desmentiu - e um teste que afirma o contrario
        do que mede e pior que teste nenhum.
        """
        total, incremento, n = 13333, 6666, 2
        assert abs(total - n * incremento) == 1
        assert limite_derivado_do_cruzamento(n) == 2.0
        assert abs(total - n * incremento) < limite_derivado_do_cruzamento(n)

    def test_a_recusa_do_caso_ruim_e_por_88_contra_2(self) -> None:
        """O controle negativo do teste acima: a distancia REAL entre os dois."""
        total, incremento, n = 13588, 6750, 2
        assert abs(total - n * incremento) == 88
        assert limite_derivado_do_cruzamento(n) == 2.0


class TestAFronteiraDeDeteccaoDaDobraDoLimite:
    """O CUSTO da dobra de 2026-09-02, medido nos DOIS lados e com o controle.

    O limite derivado dobrou porque a tela TRUNCA o unitario em vez de
    arredonda-lo (prova de campo de 2026-09-02: gabarito de dez linhas declarado
    por escrito ANTES da leitura, 10 de 10 exatos, quatro linhas discriminantes
    truncando as quatro). Um limite mais CORRETO que pega MENOS e uma troca, e
    uma troca que ninguem mediu e um afrouxamento disfarcado de conserto. Esta
    classe mede.

    A ARITMETICA DO CUSTO, sem suavizar: uma troca `0`<->`8` mexe o total em no
    MINIMO 8 centesimos - o digito na ultima casa decimal. A guarda so pega essa
    troca enquanto `quantidade x LIMITE_DERIVADO_POR_UNIDADE` for menor que 8:

        limite 0,5/unidade  ->  pega ate 15 unidades ou incrementos de escala
        limite 1,0/unidade  ->  pega ate  7

    A FRONTEIRA EXATA, com residuo 8 nos dois casos e so a escala mudando:

        (1000, 144)  n=7  residuo 8  contra limite 7,0  ->  RECUSA (pega)
        (1000, 126)  n=8  residuo 8  contra limite 8,0  ->  ACEITA (escapa)

    O CASO DE CAMPO CONTINUA COBERTO: as ofertas reais da aba Adena sao de 1 a 3
    incrementos (5M/10M/15M), limites 1,0 / 2,0 / 3,0 - todos bem abaixo de 8. E
    na negociacao a guarda esta DESLIGADA, entao la o efeito e so no limiar do
    log de `_observar_o_cruzamento`, nunca em descarte.
    """

    def test_com_n_igual_a_7_a_troca_ainda_e_PEGA(self) -> None:
        """`|1000 - 7 x 144| = 8` contra limite `7 x 1,0 = 7,0`. Estoura."""
        n = round(1000 / 144)
        assert n == 7
        assert abs(1000 - n * 144) == 8
        assert limite_derivado_do_cruzamento(n) == 7.0
        assert quantidade_de_adena(1000, 144) is None

    def test_com_n_igual_a_8_a_troca_ESCAPA_e_esse_e_o_custo(self) -> None:
        """`|1000 - 8 x 126| = 8` contra limite `8 x 1,0 = 8,0`. Cabe.

        O MESMO residuo 8, uma unidade de escala adiante, passa a ser aceito.
        Este teste existe para o custo estar escrito como AFIRMACAO e nao como
        prosa: com o limite dobrado, a partir de 8 de escala a guarda deixa de
        pegar a substituicao que ela existe para pegar.
        """
        n = round(1000 / 126)
        assert n == 8
        assert abs(1000 - n * 126) == 8
        assert limite_derivado_do_cruzamento(n) == 8.0
        assert quantidade_de_adena(1000, 126) == (ADENA_POR_INCREMENTO * 8, 8)

    def test_com_o_limite_ANTIGO_injetado_o_mesmo_caso_era_RECUSADO(
        self, monkeypatch
    ) -> None:
        """O controle que MEDE a dobra: 0,5 de volta, e o n=8 volta a ser pego.

        Sem ele, "n=8 escapa" seria compativel com qualquer outra causa. Aqui a
        UNICA coisa que muda e a constante, e o veredito vira - o que prova que o
        custo veio da dobra, e nao de outro lugar.
        """
        monkeypatch.setattr(mercado_leitura, "LIMITE_DERIVADO_POR_UNIDADE", 0.5)
        assert limite_derivado_do_cruzamento(8) == 4.0
        assert quantidade_de_adena(1000, 126) is None

    def test_a_conta_de_ate_quanto_cada_limite_pega(self) -> None:
        """15 contra 7: os dois numeros escritos no fonte, conferidos aqui.

        Uma troca `0`<->`8` vale no minimo 8 centesimos, entao a guarda pega
        enquanto o limite for ESTRITAMENTE menor que 8.
        """
        escalas = range(1, 30)
        com_o_novo = [n for n in escalas if limite_derivado_do_cruzamento(n) < 8]
        assert max(com_o_novo) == 7
        com_o_antigo = [n for n in escalas if n * 0.5 < 8]
        assert max(com_o_antigo) == 15

    def test_as_ofertas_REAIS_da_aba_continuam_cobertas(self) -> None:
        """1, 2 e 3 incrementos (5M/10M/15M): limites 1,0 / 2,0 / 3,0 < 8."""
        for n in (1, 2, 3):
            assert limite_derivado_do_cruzamento(n) < 8


class TestOGabaritoDeCampoDe20260902:
    """As dez linhas declaradas ANTES da leitura, contra a regua nova e a velha.

    A prova limpa: o vigia foi parado, `.mercado/observacoes.csv` foi truncado no
    cabecalho, as dez linhas da tela foram escritas a mao ANTES de o scanner
    rodar, a pagina nao mudou durante a leitura (grid diff 8.463 sobre um recorte
    de 450.000 pixels) e o leitor acertou 10 de 10 em nome, quantidade e total.
    Essas dez linhas estao CERTAS por construcao - qualquer regua que reprove
    alguma delas esta errada sobre a regua, e nao sobre a leitura.

    Preservadas em `.planning/quick/260902-ca4-o-limite-derivado-do-cruzamento-
    passa-de/260902-ca4-GABARITO-DA-PROVA-REAL.txt` e no CSV que o scanner
    produziu logo depois.
    """

    # (quantidade, total_em_centesimos, unitario_exibido)
    GABARITO = (
        (8, 2000, 250),
        (4, 1199, 299),
        (6, 1800, 300),
        (3, 1000, 333),
        (4, 1360, 340),
        (3, 1050, 350),
        (6, 2200, 366),
        (8, 3100, 387),
        (9, 3500, 388),
        (5, 1980, 396),
    )

    def test_as_dez_linhas_fecham_contra_o_limite_de_hoje(self) -> None:
        fecham = [
            (q, t, u)
            for q, t, u in self.GABARITO
            if mercado_leitura.residuo_do_cruzamento(t, u, q)
            <= limite_derivado_do_cruzamento(q)
        ]
        assert len(fecham) == 10, "a pagina verificada fecha 10 de 10"

    def test_com_o_limite_ANTIGO_tres_linhas_CERTAS_eram_reprovadas(
        self, monkeypatch
    ) -> None:
        """7 de 10. As tres que caem sao as que a aritmetica preve, e nomeadas.

        Este e o teste que justifica a mudanca da constante inteira: nao ha
        leitura errada nenhuma aqui, e mesmo assim a regua antiga descarta 30% de
        uma pagina que se sabe certa.
        """
        monkeypatch.setattr(mercado_leitura, "LIMITE_DERIVADO_POR_UNIDADE", 0.5)
        caem = [
            (q, t, u)
            for q, t, u in self.GABARITO
            if mercado_leitura.residuo_do_cruzamento(t, u, q)
            > limite_derivado_do_cruzamento(q)
        ]
        assert caem == [(4, 1199, 299), (6, 2200, 366), (9, 3500, 388)]
        assert len(self.GABARITO) - len(caem) == 7

    def test_as_QUATRO_linhas_discriminantes_TRUNCAM_as_quatro(self) -> None:
        """A evidencia direta de que a tela trunca, e nao arredonda.

        Seis das dez dividem exato e nao opinam. As outras quatro tem unitario
        diferente sob as duas hipoteses - e o exibido e o TRUNCADO nas quatro.
        Zero linhas arredondam.
        """
        discriminantes = []
        for q, t, u in self.GABARITO:
            truncado = math.floor(t / q)
            arredondado = round(t / q)
            if truncado == arredondado:
                continue
            discriminantes.append((q, t, u, truncado, arredondado))
        assert len(discriminantes) == 4
        for q, t, u, truncado, arredondado in discriminantes:
            assert u == truncado, f"{t}/{q}: exibido {u}, truncado {truncado}"
            assert u != arredondado


class TestAsLeiturasQueSustentamARotaDerivada:
    """Os numeros do CONTEXT e os da fixtura, cada um com a sua procedencia."""

    @pytest.mark.parametrize(
        ("total", "incremento", "esperado", "procedencia"),
        [
            (11600, 5800, (10_000_000, 2), "CONTEXT: 10M por 116,00"),
            (30000, 10000, (15_000_000, 3), "CONTEXT: 15M por 300,00"),
            (6200, 6200, (5_000_000, 1), "fixtura f014 linha 0, LIDA"),
            (6499, 6499, (5_000_000, 1), "fixtura f014 linha 1, LIDA"),
            (7000, 7000, (5_000_000, 1), "fixtura f014 linha 8, LIDA"),
        ],
    )
    def test_a_oferta_vira_quantidade_e_incrementos(
        self, total: int, incremento: int, esperado: tuple[int, int], procedencia: str
    ) -> None:
        assert quantidade_de_adena(total, incremento) == esperado, procedencia


class TestAFalhaFechada:
    """Dado ilegivel e descartado, nunca interpretado. O padrao da casa."""

    @pytest.mark.parametrize(
        ("total", "incremento", "por_que"),
        [
            (None, 6666, "a coluna Total Price nao se leu"),
            (13333, None, "a coluna 5 mln increment nao se leu"),
            (None, None, "nenhuma das duas se leu"),
            (13333, 0, "incremento zero dividiria por zero"),
            (13333, -6666, "incremento negativo nao e leitura de tela"),
            (0, 6666, "total zero nao e uma oferta"),
            (-13333, 6666, "total negativo nao e leitura de tela"),
            (100, 6666, "n arredonda para ZERO: nao ha oferta de 0 adena"),
        ],
    )
    def test_devolve_None(
        self, total: int | None, incremento: int | None, por_que: str
    ) -> None:
        assert quantidade_de_adena(total, incremento) is None, por_que


class TestOCriterioEChamadoENaoCopiado:
    """A propriedade que separa "usa o criterio medido" de "usa um 1,0 inline".

    Um teste que so afirmasse o RESULTADO nao distinguiria os dois: `(13333,
    6666)` devolve `(10_000_000, 2)` nas duas implementacoes. So substituindo a
    funcao e vendo o veredito MUDAR e que se prova que ela foi CHAMADA.
    """

    def test_com_o_limite_zerado_o_caso_BOM_reprova(self, monkeypatch) -> None:
        monkeypatch.setattr(
            mercado_leitura, "limite_derivado_do_cruzamento", lambda _n: 0.0
        )
        assert quantidade_de_adena(13333, 6666) is None

    def test_com_o_limite_generoso_o_caso_RUIM_passa(self, monkeypatch) -> None:
        """O controle negativo do teste acima, no sentido OPOSTO.

        Sem ele, "devolveu None" seria compativel com a funcao ignorar o limite
        e recusar por qualquer outra razao. Aqui o veredito vira do OUTRO lado
        pela MESMA alavanca: so o limite decide.
        """
        monkeypatch.setattr(
            mercado_leitura, "limite_derivado_do_cruzamento", lambda _n: 1000.0
        )
        assert quantidade_de_adena(13588, 6750) == (10_000_000, 2)

    def test_sem_monkeypatch_os_dois_vao_para_os_lados_de_sempre(self) -> None:
        """O controle que prova que os dois testes acima mudaram alguma coisa."""
        assert quantidade_de_adena(13333, 6666) == (10_000_000, 2)
        assert quantidade_de_adena(13588, 6750) is None


class TestOSinalDaComparacao:
    """`residuo <= limite`. O sinal e LOAD-BEARING, nos DOIS sentidos.

    ESTA CLASSE E A UNICA TESTEMUNHA DO SINAL DESDE 2026-09-02, e ela sempre foi
    a testemunha certa: ela INJETA o limite (1,0 e 0,99 sobre o mesmo residuo 1)
    e por isso nao depende do valor de `LIMITE_DERIVADO_POR_UNIDADE`. Ate aquele
    dia `TestOsDoisCasosDificeis` tambem testemunhava, por acidente: com o limite
    em meio centesimo por unidade o caso-bandeira `(13333, 6666)` passava por
    igualdade (residuo 1 contra 1,0), entao trocar `<=` por `<` o derrubava. Com
    o limite dobrado ele passa com folga (1 contra 2,0) e ja nao denuncia nada -
    uma testemunha que a mudanca de uma constante fez calar. Aqui a injecao
    mantem o par de casos exatamente na fronteira, para sempre.

    O `<=` e o mesmo sentido que `_observar_o_cruzamento` ja usa; escrever o
    outro criaria DUAS leituras opostas do MESMO limite.
    """

    def test_residuo_IGUAL_ao_limite_ACEITA(self, monkeypatch) -> None:
        monkeypatch.setattr(
            mercado_leitura, "limite_derivado_do_cruzamento", lambda _n: 1.0
        )
        assert quantidade_de_adena(13333, 6666) == (10_000_000, 2)

    def test_residuo_UM_FIO_acima_do_limite_REJEITA(self, monkeypatch) -> None:
        """O controle negativo: 0,99 contra o mesmo residuo 1."""
        monkeypatch.setattr(
            mercado_leitura, "limite_derivado_do_cruzamento", lambda _n: 0.99
        )
        assert quantidade_de_adena(13333, 6666) is None


class TestAConstanteDoIncremento:
    """`5_000_000` mora no FONTE, pelo precedente literal de `SUFIXO_DA_GRADE`."""

    def test_vale_cinco_milhoes(self) -> None:
        assert ADENA_POR_INCREMENTO == 5_000_000

    def test_a_quantidade_e_multiplo_dela(self) -> None:
        resultado = quantidade_de_adena(13333, 6666)
        assert resultado is not None
        quantidade, incrementos = resultado
        assert quantidade == ADENA_POR_INCREMENTO * incrementos


# ---------------------------------------------------------------------------
# Task 2: a linha da Adena, sem nome e sem OCR, com identidade de sentinela
# ---------------------------------------------------------------------------


class TestAFixturaDaAdenaLeOQueODocstringDiz:
    """O ANCORADOURO de tudo o mais: se os pixels mudarem, isto cai primeiro.

    Sem este teste, `LEITURAS_DA_FIXTURA` seria uma tabela copiada de um
    relatorio e envelheceria em silencio; todo teste abaixo passaria a afirmar
    numeros que a fixtura nao produz mais.
    """

    @pytest.mark.parametrize("indice", sorted(LEITURAS_DA_FIXTURA))
    def test_as_duas_colunas_de_moeda_leem_o_valor_medido(
        self, cal, moldes, janela_adena, indice: int
    ) -> None:
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, indice)
        piso = float(cal.mercado_limiar_de_leitura_de_glifo)
        margem = float(cal.mercado_margem_de_leitura_de_glifo)
        lido = tuple(
            mercado_leitura.ler_celula_de_numero(
                recortes[coluna],
                moldes,
                piso,
                margem,
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            for coluna in ("total", "incremento")
        )
        assert lido == LEITURAS_DA_FIXTURA[indice]

    @pytest.mark.parametrize("indice", sorted(LEITURAS_DA_FIXTURA))
    def test_a_coluna_Quantity_de_negociacao_NAO_le_nada_na_Adena(
        self, cal, moldes, janela_adena, indice: int
    ) -> None:
        """O outro lado da medicao: e por isso que a quantidade se DERIVA."""
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, indice)
        assert (
            mercado_leitura.ler_celula_de_numero(
                recortes["quantidade"],
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            is None
        )


class TestALinhaBoaDaAdena:
    """A linha 0 da fixtura, de pixels a `LinhaLida`, sem OCR nenhum."""

    def test_vira_LinhaLida_com_a_sentinela(self, cal, moldes, janela_adena) -> None:
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, 0)
        lida = chamar_ler_linha_da_adena(cal, moldes, recortes, 0)
        assert isinstance(lida, LinhaLida)
        assert lida.indice == 0
        assert lida.chave_da_serie == CHAVE_DA_SERIE_DA_ADENA
        assert lida.nome_exibido == NOME_EXIBIDO_DA_ADENA
        # `62,00` em XM por UM incremento de cinco milhoes de adena.
        assert lida.total_em_centesimos == 6200
        assert lida.quantidade == 5_000_000
        assert lida.residuo_do_cruzamento == 0

    def test_as_NOVE_linhas_boas_atravessam(self, cal, moldes, janela_adena) -> None:
        """O controle de volume: uma linha so poderia passar por acidente."""
        boas = [i for i in sorted(LEITURAS_DA_FIXTURA) if i != LINHA_DO_DEFEITO]
        for indice in boas:
            recortes = fatiar_a_linha_da_adena(cal, janela_adena, indice)
            lida = chamar_ler_linha_da_adena(cal, moldes, recortes, indice)
            assert isinstance(lida, LinhaLida), indice
            assert lida.quantidade == 5_000_000, indice
            assert lida.total_em_centesimos == LEITURAS_DA_FIXTURA[indice][0], indice


class TestOCruzamentoEGUARDANaAdena:
    """A diferenca de STATUS: na negociacao ele OBSERVA; aqui ele DERRUBA.

    Na negociacao a guarda foi REPROVADA por medicao e
    `mercado_tolerancia_do_cruzamento` esta gravada como `None` — o cruzamento
    de la so registra. Aqui ele e a UNICA rede entre uma leitura errada e uma
    taxa plausivel no CSV: sem ela a linha 5 desta fixtura entra como `135,88`.
    """

    # O PAR RECOMPOSTO que alcanca a guarda com tinta BRANCA.
    #
    # Ele existe porque a metade B poe o portao de COR antes da aritmetica, e a
    # linha 5 — a unica desta fixtura cuja aritmetica nao fecha — e CIANA: ela
    # agora cai por `tinta`, ANTES de a guarda opinar. Sem este par a fiacao da
    # guarda ficaria sem teste ponta a ponta, e guarda sem teste apodrece.
    #
    # Os DOIS recortes sao pixels REAIS desta mesma fixtura, e os dois sao
    # ACROMATICOS. So o PAREAMENTO e deliberado: o `Total Price` da linha 8
    # (`70,00`) contra o `5 mln increment` da linha 1 (`64,99`). Nenhuma tela
    # jamais mostrou essa combinacao — e nao precisa ter mostrado, porque a
    # afirmacao aqui e sobre a FIACAO ("a guarda esta ligada e derruba"), e nao
    # sobre uma pagina que existiu.
    LINHA_DO_TOTAL_BRANCO = 8
    LINHA_DO_INCREMENTO_BRANCO = 1

    def _par_branco_que_nao_fecha(self, cal, janela_adena):
        de_total = fatiar_a_linha_da_adena(
            cal, janela_adena, self.LINHA_DO_TOTAL_BRANCO
        )
        de_incremento = fatiar_a_linha_da_adena(
            cal, janela_adena, self.LINHA_DO_INCREMENTO_BRANCO
        )
        return de_total, de_incremento

    def test_a_linha_do_13588_agora_cai_ANTES_da_guarda_por_ser_CIANA(
        self, cal, moldes, janela_adena
    ) -> None:
        """A guarda nao foi afrouxada — ela deixou de ser a PRIMEIRA a pegar.

        Ate a metade B esta linha caia por `cruzamento`: a leitura devolvia
        `135,88` contra incremento `67,50`, o residuo dava 88 e a aritmetica
        recusava. Ela continua caindo, e continua fora do CSV. O que mudou e
        que agora ela cai por `tinta`, uma peneira ANTES — a tinta dela tem
        saturacao mediana 114 e os 13 moldes foram cortados sobre tinta de
        saturacao 0, entao o leitor sabe que nao sabe ler, e diz isso em vez de
        deixar a aritmetica descobrir depois.

        O motivo registrado passou a nomear a CAUSA ("nao sei ler esta cor") em
        vez da consequencia ("os numeros nao fecham"), e e a causa que diz ao
        usuario o que fazer: cortar moldes cianos.
        """
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, LINHA_DO_DEFEITO)
        recusada = chamar_ler_linha_da_adena(
            cal, moldes, recortes, LINHA_DO_DEFEITO
        )
        assert isinstance(recusada, Descarte)
        assert recusada.motivo == MOTIVO_DA_TINTA

    def test_a_guarda_CONTINUA_LIGADA_e_derruba_o_par_branco_que_nao_fecha(
        self, cal, moldes, janela_adena
    ) -> None:
        """A fiacao da guarda, alcancada com tinta que o leitor SABE ler.

        `70,00` contra incremento `64,99`: `round(7000 / 6499)` da 1, o residuo
        e |7000 - 6499| = 501 centesimos, e o limite derivado para n = 1 e 0,5.
        A guarda recusa — e o motivo e `cruzamento`, provando que ela nao foi
        desligada nem substituida pelo portao de cor.
        """
        de_total, de_incremento = self._par_branco_que_nao_fecha(
            cal, janela_adena
        )
        recusada = chamar_ler_linha_da_adena(
            cal,
            moldes,
            de_total,
            self.LINHA_DO_TOTAL_BRANCO,
            recorte_do_incremento=de_incremento["incremento"],
        )
        assert isinstance(recusada, Descarte)
        assert recusada.motivo == MOTIVO_DO_CRUZAMENTO

    def test_e_o_par_branco_atravessa_o_portao_de_COR_sem_ser_tocado(
        self, cal, moldes, janela_adena
    ) -> None:
        """O controle do teste acima: sem ele, `cruzamento` poderia ser sorte.

        Se o portao de cor tivesse opiniao sobre estes dois recortes, a linha
        teria caido por `tinta` e o teste acima estaria medindo outra coisa.
        """
        de_total, de_incremento = self._par_branco_que_nao_fecha(
            cal, janela_adena
        )
        for recorte in (de_total["total"], de_incremento["incremento"]):
            assert (
                mercado_leitura.saturacao_da_tinta(
                    recorte, VALOR_MINIMO_DO_TEXTO
                )
                == 0.0
            )
            assert not mercado_leitura.tinta_fora_da_curva_dos_moldes(
                recorte, VALOR_MINIMO_DO_TEXTO
            )

    def test_ela_NAO_e_recusada_por_oclusao_nem_por_gramatica(
        self, cal, moldes, janela_adena
    ) -> None:
        """O controle que prova que o motivo acima nao vem de outra peneira.

        A gramatica PASSA (`135,88` e numero valido) e a sonda diz LIMPO — e
        exatamente por isso que a guarda aritmetica precisa existir.
        """
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, LINHA_DO_DEFEITO)
        cinza = cv2.cvtColor(recortes["linha"], cv2.COLOR_BGR2GRAY)
        assert mercado_leitura.linha_vazia(recortes["linha"]) is False
        assert (
            mercado_leitura.linha_ocluida(
                cinza,
                cal.mercado_sonda_do_fundo,
                float(cal.mercado_limiar_de_dispersao_do_fundo),
            )
            is False
        )
        assert LEITURAS_DA_FIXTURA[LINHA_DO_DEFEITO] == (13588, 6750)

    def test_o_detalhe_da_recusa_cita_total_incremento_n_e_residuo(
        self, cal, moldes, janela_adena, caplog
    ) -> None:
        """Um numero que caiu precisa dizer POR QUE caiu, e com que numeros.

        Corre sobre o PAR RECOMPOSTO desde a metade B, pela mesma razao do
        teste da fiacao: a linha ciana nao chega mais a guarda.
        """
        de_total, de_incremento = self._par_branco_que_nao_fecha(
            cal, janela_adena
        )
        with caplog.at_level(logging.WARNING, logger="l2scanner.mercado_leitura"):
            chamar_ler_linha_da_adena(
                cal,
                moldes,
                de_total,
                self.LINHA_DO_TOTAL_BRANCO,
                recorte_do_incremento=de_incremento["incremento"],
            )
        texto = "\n".join(r.getMessage() for r in caplog.records)
        for pedaco in ("7000", "6499", "n=1", "501"):
            assert pedaco in texto, (pedaco, texto)

    def test_e_a_recusa_por_TINTA_tambem_diz_qual_coluna_caiu(
        self, cal, moldes, janela_adena, caplog
    ) -> None:
        """A peneira nova segue a mesma regra das antigas: ela se explica."""
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, LINHA_DO_DEFEITO)
        with caplog.at_level(logging.WARNING, logger="l2scanner.mercado_leitura"):
            chamar_ler_linha_da_adena(cal, moldes, recortes, LINHA_DO_DEFEITO)
        texto = "\n".join(r.getMessage() for r in caplog.records)
        assert "Total Price" in texto
        assert "cor" in texto


class TestAsPeneirasNaMESMAORDEMDeLerLinha:
    """vazia -> oclusao -> Total Price -> 5 mln increment -> cruzamento."""

    def test_a_linha_vazia_devolve_None_e_marca_o_fim_da_pagina(
        self, cal, moldes, janela_adena
    ) -> None:
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, 0)
        assert (
            chamar_ler_linha_da_adena(
                cal,
                moldes,
                recortes,
                0,
                recorte_da_linha=ler_fixtura(LINHA_VAZIA),
            )
            is None
        )

    def test_a_linha_coberta_vira_Descarte_de_oclusao(
        self, cal, moldes, janela_adena
    ) -> None:
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, 0)
        recusada = chamar_ler_linha_da_adena(
            cal,
            moldes,
            recortes,
            0,
            recorte_da_linha=ler_fixtura(LINHA_SOB_TOOLTIP),
        )
        assert isinstance(recusada, Descarte)
        assert recusada.motivo == MOTIVO_DA_OCLUSAO

    def test_o_Total_Price_ilegivel_vira_Descarte_de_gramatica(
        self, cal, moldes, janela_adena
    ) -> None:
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, 0)
        recusada = chamar_ler_linha_da_adena(
            cal, moldes, recortes, 0, recorte_do_total=recortes["quantidade"]
        )
        assert isinstance(recusada, Descarte)
        assert recusada.motivo == MOTIVO_DA_GRAMATICA

    def test_o_incremento_ilegivel_vira_Descarte_de_gramatica(
        self, cal, moldes, janela_adena
    ) -> None:
        """Aqui o incremento NAO e opiniao opcional, e essa e a diferenca.

        Na negociacao o unitario ilegivel nao derruba a linha — ele so CALA a
        guarda, porque `Total` e `Quantity` bastam para a observacao. Na Adena
        nao ha `Quantity`: sem incremento nao ha quantidade, e sem quantidade
        nao ha taxa. Logo ele derruba.
        """
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, 0)
        recusada = chamar_ler_linha_da_adena(
            cal, moldes, recortes, 0, recorte_do_incremento=recortes["quantidade"]
        )
        assert isinstance(recusada, Descarte)
        assert recusada.motivo == MOTIVO_DA_GRAMATICA

    def test_a_linha_coberta_nao_chega_a_ler_numero(
        self, cal, moldes, janela_adena, caplog
    ) -> None:
        """A ORDEM, e nao so o veredito: a oclusao vem ANTES das colunas."""
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, 0)
        with caplog.at_level(logging.WARNING, logger="l2scanner.mercado_leitura"):
            chamar_ler_linha_da_adena(
                cal,
                moldes,
                recortes,
                0,
                recorte_do_total=recortes["quantidade"],
                recorte_da_linha=ler_fixtura(LINHA_SOB_TOOLTIP),
            )
        texto = "\n".join(r.getMessage() for r in caplog.records)
        assert MOTIVO_DA_OCLUSAO in texto
        assert "Total Price" not in texto


class TestUmaSerieSO:
    """D-A: a Adena e UMA serie. Decisao do usuario, respondida a pergunta direta."""

    def test_a_primeira_linha_abre_serie_e_a_SEGUNDA_nao(
        self, cal, moldes, janela_adena
    ) -> None:
        catalogo: dict[str, EntradaDoCatalogo] = {}
        primeira = chamar_ler_linha_da_adena(
            cal, moldes, fatiar_a_linha_da_adena(cal, janela_adena, 0), 0, catalogo
        )
        assert isinstance(primeira, LinhaLida)
        assert primeira.serie_nova is True

        catalogo[primeira.chave_da_serie] = EntradaDoCatalogo(
            chave=primeira.chave_da_serie,
            nome=primeira.nome_exibido,
            assinatura="",
        )
        segunda = chamar_ler_linha_da_adena(
            cal, moldes, fatiar_a_linha_da_adena(cal, janela_adena, 6), 6, catalogo
        )
        assert isinstance(segunda, LinhaLida)
        assert segunda.serie_nova is False
        assert segunda.chave_da_serie == primeira.chave_da_serie
        # Duas linhas com totais DIFERENTES (62,00 e 68,00) e UMA serie so.
        assert segunda.total_em_centesimos != primeira.total_em_centesimos
        assert len(catalogo) == 1

    def test_a_chave_e_montada_do_separador_e_nao_escrita_solta(self) -> None:
        assert CHAVE_DA_SERIE_DA_ADENA == "adena" + SEPARADOR_DA_ASSINATURA
        assert NOME_EXIBIDO_DA_ADENA == "Adena"

    def test_a_sentinela_nao_carrega_digito_nenhum(self) -> None:
        """A propriedade estrutural que impede a chave de depender da quantidade."""
        assert not any(caractere in DIGITOS for caractere in CHAVE_DA_SERIE_DA_ADENA)

    def test_a_chave_DERIVADA_DO_NOME_partiria_a_Adena_ao_meio(self) -> None:
        """O controle negativo MEDIDO: por que a sentinela e necessaria.

        Sem ela, `agrupar` produziria a chave a partir do nome lido, e a trava
        de digitos (D-03) usa a assinatura por igualdade EXATA. `5,000,000
        Adena` e `10,000,000 Adena` tem assinaturas diferentes: seriam DUAS
        series, e a mediana da taxa nasceria partida ao meio — exatamente o que
        esta fase existe para nao fazer.
        """
        de_5_milhoes = assinatura_por_ocr("5,000,000 Adena")
        de_10_milhoes = assinatura_por_ocr("10,000,000 Adena")
        assert de_5_milhoes != de_10_milhoes, (de_5_milhoes, de_10_milhoes)


class TestNadaAquiLeNome:
    """A coluna `Auction List` nao e tocada, e a assinatura nao tem por onde."""

    def test_a_assinatura_nao_recebe_leitora_de_texto(self) -> None:
        """Mais forte que contar chamadas numa execucao: nao HA parametro.

        Contar zero chamadas de OCR prova uma execucao; a assinatura prova
        TODAS. Se um dia alguem acrescentar `ler_texto` aqui, este teste cai no
        mesmo commit.
        """
        esperado = [
            "indice",
            "bgr_da_linha",
            "recorte_do_total",
            "recorte_do_incremento",
            "moldes",
            # O segundo conjunto de moldes, o CROMATICO. Ele entra na assinatura
            # OPCIONAL e por omissao `None`, e e isso que faz a metade B
            # sobreviver a metade A: sem conjunto ciano gravado, a celula ciana
            # continua sendo RECUSADA e nao adivinhada.
            "moldes_cromaticos",
            "piso",
            "margem",
            "valor_minimo_do_numero",
            "folga_de_cola",
            "sonda",
            "limiar_de_dispersao",
            "catalogo",
        ]
        assert list(inspect.signature(ler_linha_de_adena).parameters) == esperado

    def test_o_controle_negativo_ler_linha_TEM_as_duas_leitoras(self) -> None:
        """Sem ele, "nao tem ler_texto" nao diria nada sobre este projeto."""
        de_negociacao = list(
            inspect.signature(mercado_leitura.ler_linha).parameters
        )
        assert "ler_texto" in de_negociacao
        assert "ler_texto_conferencia" in de_negociacao

    def test_nao_ha_parametro_de_recorte_de_nome(self) -> None:
        parametros = list(inspect.signature(ler_linha_de_adena).parameters)
        assert not [p for p in parametros if "nome" in p]

class TestNUNCALevanta:
    """T-05-03: ela roda dentro do tick, no modelo de `ler_linha`.

    A PRIMEIRA VERSAO DESTE TESTE ERA VACUA, E ESTA ESCRITO AQUI PARA NAO
    VOLTAR. Ela passava `"isto nao e uma imagem"` como recorte da linha e
    esperava `Descarte`. Mas `linha_vazia` faz `getattr(bgr, "size", 0) == 0`, e
    uma `str` nao tem `.size`: a string era classificada como LINHA VAZIA e a
    funcao devolvia `None` sem NUNCA chegar ao `except`. O teste media a
    primeira peneira e afirmava a ultima.

    O instrumento correto e forcar a excecao DENTRO do pipeline, sobre pixels
    que atravessam de verdade — e provar, com o controle negativo, que sem a
    excecao aqueles mesmos pixels viram `LinhaLida`.
    """

    def test_a_excecao_no_meio_do_pipeline_vira_Descarte(
        self, cal, moldes, janela_adena, monkeypatch
    ) -> None:
        def explodir(*_args, **_kwargs):
            raise RuntimeError("a sonda explodiu no meio do tick")

        monkeypatch.setattr(mercado_leitura, "linha_ocluida", explodir)
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, 0)
        recusada = chamar_ler_linha_da_adena(cal, moldes, recortes, 0)
        assert isinstance(recusada, Descarte)
        assert recusada.indice == 0
        assert recusada.motivo == MOTIVO_DA_GRAMATICA

    def test_o_controle_negativo_sem_a_excecao_a_MESMA_linha_atravessa(
        self, cal, moldes, janela_adena
    ) -> None:
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, 0)
        lida = chamar_ler_linha_da_adena(cal, moldes, recortes, 0)
        assert isinstance(lida, LinhaLida)

    def test_a_linha_vazia_de_verdade_e_um_ARRAY_e_devolve_None(
        self, cal, moldes, janela_adena
    ) -> None:
        """A peneira que a versao vacua estava medindo sem saber, com pixels reais."""
        recortes = fatiar_a_linha_da_adena(cal, janela_adena, 0)
        vazia = ler_fixtura(LINHA_VAZIA)
        assert isinstance(vazia, np.ndarray)
        assert (
            chamar_ler_linha_da_adena(
                cal, moldes, recortes, 0, recorte_da_linha=vazia
            )
            is None
        )
