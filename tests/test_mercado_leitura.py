"""O TRACER: uma linha da grade de negociacao, de pixels ate pagina aceita.

Tudo aqui roda sobre fixturas VERSIONADAS em `tests/fixtures/mercado/` e nunca
sobre `recordings/` — a pasta e gitignored, tem 8 GB e nao vem de clone limpo,
entao um teste que dependesse dela ficaria verde nesta maquina e amarelo em toda
outra.

A CALIBRACAO DA FIXTURA E A MESMA DA PRODUCAO, E ISSO E DELIBERADO
-------------------------------------------------------------------
`tests/fixtures/mercado/calibracao_de_fixture.json` traz as chaves `mercado_*`
COPIADAS VERBATIM do `calibration.json` que o usuario confirmou — a mesma grade,
as mesmas quatro colunas, o mesmo molde de cabecalho, os mesmos 13 moldes de
glifo e os mesmos seis numeros medidos pelos planos 02-02 e 02-03. A alternativa
(uma calibracao de fixtura com layout proprio, de brinquedo) foi explicitamente
recusada: ela deixaria os testes verdes sobre uma geometria que a producao nunca
ve, que e o mesmo erro que o 02-02 corrigiu ao medir o corte sobre a populacao
pos-sonda em vez da crua.

O que NAO e copiado do arquivo real sao as chaves de PARTY (`party_window`,
`ancora`, `nomes`, `assinaturas`). Nada nesta fase as le, e versiona-las
publicaria o nome e o recorte de tela de gente real para carregar um dict que os
testes ignoram. Elas entram neutras, e o `Calibracao.carregar` continua exigindo
que existam.

AS DUAS ESCALAS DE OCR CHEGAM INJETADAS, NUNCA POR MONKEYPATCH
---------------------------------------------------------------
O pytest deste projeto roda no Python GLOBAL, que nao tem as bindings WinRT.
`LeitorDePagina` recebe `ler_texto` e `ler_texto_conferencia` no `__init__`,
como `VigiaDeManutencao` ja faz (`manutencao.py:384-402`) — e e isso que permite
CONTAR as chamadas e provar que as duas foram feitas. Uma segunda opiniao que
nunca e pedida e indistinguivel de nao ter segunda opiniao, e o resultado de uma
leitura so tambem e uma `LinhaLida` valida: nenhum outro criterio a pegaria.

O QUE A MEDICAO REFUTOU DO PLANO, E ESTA ESCRITO AQUI PARA NAO VOLTAR
----------------------------------------------------------------------
O plano 02-04 afirmava que a LINHA 0 de `janela_negociacao_f010.png` sairia como
`LinhaLida`. Ela NAO sai, e o motivo esta medido: naquele frame a tooltip cobre
a coluna Total das linhas 0 a 3, e a sonda de oclusao NAO a ve — a sonda mede o
trecho `dx 246..396` da grade, que fica na METADE ESQUERDA, e esta tooltip esta
na direita. Dispersao 0,0000 em todas as dez linhas.

(O trecho era `dx 207..417` ate 2026-08-31. Ele encolheu e andou para a direita
porque comecava DENTRO da coluna do nome e recusava linha de nome comprido; o
`linha_ocluida` de `mercado_leitura.py` carrega a medicao. As dez linhas deste
frame liam 0,0000 nos dois trechos, entao nada nesta pagina mudou de veredito.)

Quem pega o buraco e a peneira seguinte, e e por isso que ela existe: os runs da
coluna coberta nao passam no piso, a celula cai inteira (tudo-ou-nada de
LEIT-02) e a linha vira `Descarte`. As linhas que atravessam de verdade neste
frame sao a 6 (`18,90` x 2) e a 8 (`18,00` x 3).
"""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.identidade import VALOR_MINIMO_DO_TEXTO, mascara_de_texto
from l2scanner.mercado_catalogo import EntradaDoCatalogo
from l2scanner.mercado_geometria import nivel_de_fundo_da_linha
from l2scanner.mercado_leitura import (
    MOTIVO_DA_DISCORDANCIA,
    MOTIVO_DA_FAIXA_CINZENTA,
    MOTIVO_DA_GRAMATICA,
    MOTIVO_DA_OCLUSAO,
    MOTIVO_DO_CRUZAMENTO,
    Descarte,
    LinhaLida,
    centesimos_de_moeda,
    cruzamento_confere,
    inteiro_de_quantidade,
    larguras_com_folga,
    larguras_de_molde,
    ler_celula,
    ler_celula_de_numero,
    ler_celula_de_quantidade,
    ler_glifos,
    ler_linha,
    limite_de_glifo_unico,
    limite_derivado_do_cruzamento,
    linha_ocluida,
    linha_vazia,
    mascara_de_numero,
    numero_valido,
    particionar_run,
    residuo_do_cruzamento,
    segmentar_glifos,
    segmentar_glifos_no_brilho,
)
from l2scanner.mercado_pagina import LeitorDePagina, PaginaAceita
from l2scanner.mercado_visao import (
    RastreioDoPainel,
    ancoras_de_calibracao,
    glifos_de_calibracao,
)

FIXTURES = Path(__file__).parent / "fixtures" / "mercado"
CALIBRACAO = FIXTURES / "calibracao_de_fixture.json"
JANELA_F010 = FIXTURES / "janela_negociacao_f010.png"
JANELA_F005 = FIXTURES / "janela_negociacao_f005.png"
JANELA_F005_REPETIDA = FIXTURES / "janela_negociacao_f005_repetida.png"

# As linhas de `frame_000010` que atravessam o caminho INTEIRO. Medidas, nao
# supostas.
#
# ELAS CRESCERAM DE 2 PARA 6 NO 02-07, E O NUMERO E MEDIDO. Ate aqui a coluna
# Quantity lia no piso compartilhado 180 e o tronco do `1` (V = 174 no censo)
# ficava de fora: toda linha de quantidade `1` caia FECHADA. Com o piso PROPRIO
# da coluna, MEDIDO em 161, as quatro linhas de quantidade `1` (4, 5, 7 e 9)
# passam a atravessar. As DUAS que ja atravessavam continuam com os MESMOS
# digitos — 6 vale (1890, 2) e 8 vale (1800, 3) —, e essa igualdade e o que
# prova que o piso novo NAO vazou para a coluna de moeda.
LINHAS_QUE_ATRAVESSAM_F010_ANTES_DO_PISO_PROPRIO = {6: (1890, 2), 8: (1800, 3)}
LINHAS_QUE_ATRAVESSAM_F010 = {
    4: (10000, 1),
    5: (300, 1),
    6: (1890, 2),
    7: (750, 1),
    8: (1800, 3),
    9: (245, 1),
}

# As linhas de `frame_000005` que atravessam. Este e o par de frames PARADOS
# (005 e 006 mostram a mesma pagina), e por isso e ele que prova o acordo entre
# dois frames.
#
# ELAS CRESCERAM DE 4 PARA 10 NO 02-07, pela mesma medicao: as seis linhas novas
# (0, 2, 4, 7, 8 e 9) tem todas quantidade `1`, e as quatro antigas continuam
# com os MESMOS totais e as MESMAS quantidades.
LINHAS_QUE_ATRAVESSAM_F005_ANTES_DO_PISO_PROPRIO = {
    1: (3666, 3),
    3: (1500, 3),
    5: (1139, 6),
    6: (500, 2),
}
LINHAS_QUE_ATRAVESSAM_F005 = {
    0: (300, 1),
    1: (3666, 3),
    2: (498, 1),
    3: (1500, 3),
    4: (190, 1),
    5: (1139, 6),
    6: (500, 2),
    7: (1400, 1),
    8: (190, 1),
    9: (190, 1),
}


def ler_fixtura(caminho: Path) -> np.ndarray:
    pixels = cv2.imread(str(caminho))
    assert pixels is not None, f"nao decodifiquei a fixtura {caminho}"
    return pixels


@pytest.fixture(scope="module")
def cal() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO)


@pytest.fixture(scope="module")
def moldes(cal: Calibracao) -> dict:
    return glifos_de_calibracao(cal.mercado_templates_de_digito)


@pytest.fixture(scope="module")
def janela_f010() -> np.ndarray:
    return ler_fixtura(JANELA_F010)


class LeitoraContadora:
    """Uma leitora de OCR falsa que ANOTA cada recorte que lhe pediram.

    Ela e o instrumento do criterio central desta task: sem contar as chamadas
    nao ha como distinguir "duas escalas confrontadas" de "duas escalas
    injetadas e uma ignorada", porque as duas produzem `LinhaLida` valida.
    """

    def __init__(self, texto, marcador: list) -> None:
        self._texto = texto
        self._marcador = marcador
        # `id()` so e identidade ENQUANTO O OBJETO VIVE. O recorte de cada linha
        # e transitorio: assim que a linha termina de ser processada ele e
        # liberado, e o CPython reaproveita aquele mesmo endereco no recorte da
        # linha seguinte. Sem esta lista, recortes DIFERENTES apareciam com o
        # mesmo `id` e o `set()` la embaixo os fundia num so — medido nesta
        # fixtura: um unico `id` chegou a carregar QUATRO conteudos distintos, e
        # `len(set(vistos_2x))` deu 4, 5 ou 6 para as MESMAS seis chamadas,
        # conforme o layout do heap. Foi assim que o estabilizador do 02-05
        # (efcd73a), que nao encostou neste arquivo, derrubou este teste: ele
        # mexeu na alocacao, nao na leitura.
        #
        # Segurar uma referencia forte a cada recorte impede a reciclagem e
        # devolve a `id()` o significado que as afirmacoes sempre presumiram.
        # Nenhuma afirmacao muda por causa disto — e o teste fica mais forte,
        # porque `set()` so sabia ENCOLHER a contagem.
        self._vivos: list = []
        self.chamadas = 0

    def __call__(self, pixels) -> str | None:
        self.chamadas += 1
        self._vivos.append(pixels)
        self._marcador.append(id(pixels) if pixels is not None else None)
        if callable(self._texto):
            return self._texto(pixels)
        return self._texto


class LeitoraPorLinhaDaPagina:
    """Uma leitora falsa que responde por INDICE DE LINHA da grade.

    Ela existe porque toda a suite de pagina injeta um nome CONSTANTE para todas
    as linhas, e com todas as linhas lendo a MESMA string todas derivam a MESMA
    chave — o que torna ESTRUTURALMENTE invisivel qualquer defeito que separe
    duas linhas da mesma pagina. Uma pagina de mercado real tem varias ofertas do
    mesmo item, e e exatamente ai que a serie duplicou na sessao de 17:05.

    O INDICE VEM DA ORDEM DAS CHAMADAS, E NAO DO CONTEUDO DO RECORTE. Derivar do
    conteudo seria o natural, mas os dois frames da mesma pagina NAO sao
    byte-identicos — medido nas fixturas, 499.599 pixels diferentes, porque as
    ofertas se mexem entre capturas. A ordem, essa e firme: `_ler_o_nome` chama a
    escala barata e depois a de conferencia, nessa ordem, uma vez cada, por
    linha. Dai o `// 2`.

    `reiniciar()` e CHAMADO PELO TESTE entre os dois frames, e nao adivinhado
    aqui: o leitor nao avisa quando comeca uma pagina nova, e um reset por
    heuristica (contar ate `linhas_por_pagina`) mentiria na pagina curta, onde o
    laco para na primeira linha vazia.
    """

    def __init__(self, nomes: dict[int, str], padrao: str) -> None:
        self._nomes = nomes
        self._padrao = padrao
        self.chamadas = 0

    def reiniciar(self) -> None:
        self.chamadas = 0

    def __call__(self, _pixels) -> str:
        linha = self.chamadas // 2
        self.chamadas += 1
        return self._nomes.get(linha, self._padrao)


def montar_leitor(cal, nome_2x, nome_3x, catalogo=None):
    """Um `LeitorDePagina` com as duas leitoras CONTADORAS e catalogo proprio."""
    vistos_2x: list = []
    vistos_3x: list = []
    barata = LeitoraContadora(nome_2x, vistos_2x)
    conferencia = LeitoraContadora(nome_3x, vistos_3x)
    leitor = LeitorDePagina(
        RastreioDoPainel(
            ancoras_de_calibracao(cal.mercado_ancoras),
            float(cal.mercado_limiar_da_ancora),
        ),
        {} if catalogo is None else catalogo,
        barata,
        conferencia,
        cal,
    )
    return leitor, barata, conferencia, vistos_2x, vistos_3x


class TestOCharterDoModuloPuro:
    """`mercado_leitura` e PRODUCAO: nada de janela, teclado ou ferramenta."""

    def test_nao_abre_janela_nem_le_teclado(self) -> None:
        import l2scanner.mercado_leitura as modulo

        fonte = inspect.getsource(modulo)
        assert "imshow" not in fonte
        assert "waitKey" not in fonte
        assert "selectROI" not in fonte
        assert "input(" not in fonte

    def test_a_seta_aponta_da_ferramenta_para_o_puro_e_nunca_o_contrario(
        self, tmp_path: Path
    ) -> None:
        """Producao NAO pode importar `calibrar_mercado`.

        Aquele modulo chama `tornar_consciente_de_dpi()` NO IMPORT e carrega
        `argparse` e `cv2.imshow`. Um modulo de producao que o importasse pagaria
        esse efeito colateral so por existir.
        """
        import subprocess

        codigo = (
            "import sys, l2scanner.mercado_leitura, l2scanner.mercado_pagina; "
            "assert 'l2scanner.calibrar_mercado' not in sys.modules; "
            "print('puro ok')"
        )
        saida = subprocess.run(
            [sys.executable, "-c", codigo],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        assert saida.returncode == 0, saida.stderr
        assert "puro ok" in saida.stdout

    def test_nenhum_limiar_tem_valor_de_fabrica(self) -> None:
        """`piso` e `margem` sem default: numero magico nao entra por omissao."""
        assinatura = inspect.signature(ler_glifos)
        assert assinatura.parameters["piso"].default is inspect.Parameter.empty
        assert assinatura.parameters["margem"].default is inspect.Parameter.empty
        for funcao in (ler_celula_de_numero, ler_celula_de_quantidade):
            assinatura = inspect.signature(funcao)
            assert assinatura.parameters["piso"].default is inspect.Parameter.empty
            assert assinatura.parameters["margem"].default is inspect.Parameter.empty

    def test_o_PISO_DE_BRILHO_tambem_chega_sem_valor_de_fabrica(self) -> None:
        """Um default aqui e constante magica no caminho que decide QUANTIDADE.

        E a quantidade multiplica o preco no CSV da Fase 3: um piso errado nao
        acrescenta ruido, ele TROCA o numero.
        """
        for funcao in (ler_celula, ler_celula_de_numero, ler_celula_de_quantidade):
            assinatura = inspect.signature(funcao)
            assert (
                assinatura.parameters["valor_minimo"].default
                is inspect.Parameter.empty
            ), funcao.__name__

    def test_ler_linha_recebe_os_DOIS_pisos_sem_valor_de_fabrica(self) -> None:
        """Sao DOIS e nao um porque as duas faixas sao DISJUNTAS.

        A coluna de MOEDA carrega a palavra de sufixo dentro do proprio recorte
        (`XM Coin` vive entre V=120 e V=173), e um piso unico mais baixo
        arrastaria a palavra para dentro da celula: sondado, `18,90` vira
        `18,907` ja no piso 170.
        """
        parametros = inspect.signature(ler_linha).parameters
        for nome in ("valor_minimo_do_numero", "valor_minimo_da_quantidade"):
            assert parametros[nome].default is inspect.Parameter.empty, nome

    def test_omitir_o_piso_de_brilho_levanta_TypeError(self, moldes) -> None:
        """Nao ha como esquecer o parametro e ganhar um default calado."""
        vazio = np.zeros((4, 4, 3), dtype=np.uint8)
        with pytest.raises(TypeError):
            ler_celula_de_quantidade(vazio, moldes, 0.5, 0.05)


class TestAsPrimitivasIRMASDoPisoDeBrilho:
    """`mascara_de_numero` e `segmentar_glifos_no_brilho` nascem AO LADO.

    Elas nao substituem nada: `segmentar_glifos` mantem a assinatura intacta
    porque tem 35 pontos de chamada em producao, ferramentas e testes, todos
    querendo o piso COMPARTILHADO. Quebrar os 35 por causa de UMA coluna seria
    custo sem informacao — o mesmo raciocinio que fez `mascara_do_sufixo` nascer
    ao lado de `mascara_de_texto` em vez de substitui-la.
    """

    def test_no_piso_compartilhado_a_mascara_nova_e_IGUAL_a_de_texto(
        self, janela_f010, cal
    ) -> None:
        """Pixel a pixel. E esta igualdade que prova que nada mudou para quem
        nao pediu piso proprio — as colunas de MOEDA inclusive.
        """
        recorte = recorte_de_coluna(
            cal, janela_f010, 6, "mercado_coluna_do_total"
        )
        assert np.array_equal(
            mascara_de_numero(recorte, VALOR_MINIMO_DO_TEXTO),
            mascara_de_texto(recorte),
        )

    def test_um_recorte_vazio_devolve_matriz_vazia_e_nao_levanta(self) -> None:
        vazio = np.zeros((0, 0, 3), dtype=np.uint8)
        assert mascara_de_numero(vazio, VALOR_MINIMO_DO_TEXTO).size == 0

    @pytest.mark.parametrize(
        "fixtura", ["glifos_precos_f010.png", "glifos_quantidade_f012.png"]
    )
    def test_segmentar_no_piso_compartilhado_devolve_O_MESMO_de_antes(
        self, fixtura: str
    ) -> None:
        """A casca fina nao pode mudar o que os 35 chamadores ja recebiam."""
        recorte = ler_fixtura(FIXTURES / fixtura)
        assert segmentar_glifos_no_brilho(
            recorte, VALOR_MINIMO_DO_TEXTO
        ) == segmentar_glifos(recorte)

    def test_a_casca_nomeia_o_piso_compartilhado_UMA_vez(self) -> None:
        """Nomear uma vez e o contrario de espalhar o numero pelo repositorio."""
        fonte = inspect.getsource(segmentar_glifos)
        assert "VALOR_MINIMO_DO_TEXTO" in fonte

    def test_um_piso_mais_baixo_enxerga_MAIS_pixel(self, cal, janela_f010) -> None:
        """A mascara e `V > piso`: baixar o piso so pode ACRESCENTAR pixel."""
        recorte = recorte_de_coluna(
            cal, janela_f010, 6, "mercado_coluna_da_quantidade"
        )
        alta = mascara_de_numero(recorte, VALOR_MINIMO_DO_TEXTO)
        baixa = mascara_de_numero(recorte, 150)
        assert baixa.sum() >= alta.sum()
        assert np.array_equal(alta & baixa, alta)


class TestAGramaticaDoNumero:
    """A trava que pega glifo PERDIDO e glifo A MAIS. Nao pega substituicao."""

    @pytest.mark.parametrize(
        "texto", ["100,00", "3,00", "18,90", "5,000,000", "62,00", "48", "2", "5"]
    )
    def test_aceita_o_que_a_tela_desenha(self, texto: str) -> None:
        assert numero_valido(texto) is True

    @pytest.mark.parametrize(
        "texto",
        [
            "5,00,000",  # bloco de milhar com 2 digitos
            "1234",  # a virgula do milhar foi perdida
            "1,0000",  # grupo com 4
            ",00",  # sem parte inteira
            "100,",  # sem parte decimal
            "1,,000",  # grupo vazio
            "12a,00",  # nao e digito
            "",
        ],
    )
    def test_recusa_o_que_o_casamento_de_molde_produz_quando_erra(
        self, texto: str
    ) -> None:
        assert numero_valido(texto) is False

    def test_a_substituicao_passa_pela_gramatica_e_isso_esta_escrito(self) -> None:
        """`0` virando `8` mantem a gramatica. E a razao de a margem existir."""
        assert numero_valido("100,00") is True
        assert numero_valido("180,00") is True
        assert "substitui" in numero_valido.__doc__.lower()

    def test_a_moeda_termina_sempre_em_duas_casas(self) -> None:
        assert centesimos_de_moeda("100,00") == 10000
        assert centesimos_de_moeda("5,000,000") is None  # tres casas no fim
        assert centesimos_de_moeda("62,000") is None

    def test_a_quantidade_nao_tem_casa_decimal(self) -> None:
        assert inteiro_de_quantidade("48") == 48
        assert inteiro_de_quantidade("5,000,000") == 5000000


class TestALeituraDeCelula:
    """Tudo ou nada: um run reprovado derruba a celula inteira (LEIT-02)."""

    def test_le_o_total_da_linha_6_da_fixtura(self, cal, moldes, janela_f010) -> None:
        recorte = recorte_de_coluna(
            cal, janela_f010, 6, "mercado_coluna_do_total"
        )
        assert (
            ler_celula_de_numero(
                recorte,
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            == 1890
        )

    def test_le_a_quantidade_da_linha_6_da_fixtura(
        self, cal, moldes, janela_f010
    ) -> None:
        recorte = recorte_de_coluna(
            cal, janela_f010, 6, "mercado_coluna_da_quantidade"
        )
        assert (
            ler_celula_de_quantidade(
                recorte,
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                valor_minimo=int(cal.mercado_limiar_de_brilho_da_quantidade),
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            == 2
        )

    def test_um_piso_impossivel_derruba_a_celula_inteira(
        self, cal, moldes, janela_f010
    ) -> None:
        recorte = recorte_de_coluna(cal, janela_f010, 6, "mercado_coluna_do_total")
        assert (
            ler_celula_de_numero(
                recorte,
                moldes,
                1.01,
                0.0,
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            is None
        )

    def test_uma_margem_impossivel_derruba_a_celula_inteira(
        self, cal, moldes, janela_f010
    ) -> None:
        recorte = recorte_de_coluna(cal, janela_f010, 6, "mercado_coluna_do_total")
        assert (
            ler_celula_de_numero(
                recorte,
                moldes,
                0.0,
                1.01,
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            is None
        )

    def test_a_coluna_coberta_pela_tooltip_devolve_None_e_nunca_numero_parcial(
        self, cal, moldes, janela_f010
    ) -> None:
        """A linha 0 deste frame: a tooltip esta EM CIMA da coluna Total."""
        recorte = recorte_de_coluna(cal, janela_f010, 0, "mercado_coluna_do_total")
        assert (
            ler_celula_de_numero(
                recorte,
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            is None
        )


def recorte_de_coluna(cal, janela, indice: int, chave: str) -> np.ndarray:
    """O recorte de UMA coluna de UMA linha, pela geometria calibrada.

    Meio-aberto `[dx, dx + largura)`, a mesma convencao de `segmentar_glifos`.
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
    coluna = getattr(cal, chave)
    x = ox + int(coluna["dx"])
    return janela[topo : topo + altura, x : x + int(coluna["largura"])]


class TestAConvencaoDeRecorteDeColuna:
    """`[dx, dx + largura)`: colunas vizinhas nunca compartilham um pixel."""

    def test_as_quatro_colunas_nao_dividem_pixel(self, cal) -> None:
        colunas = sorted(
            (int(getattr(cal, c)["dx"]), int(getattr(cal, c)["largura"]), c)
            for c in (
                "mercado_coluna_do_nome",
                "mercado_coluna_da_quantidade",
                "mercado_coluna_do_total",
                "mercado_coluna_do_unitario",
            )
        )
        for (dx, largura, nome), (proximo, _l, seguinte) in zip(
            colunas, colunas[1:]
        ):
            assert dx + largura <= proximo, (
                f"{nome} termina em {dx + largura} e {seguinte} comeca em "
                f"{proximo}: elas compartilham pixel"
            )

    def test_o_recorte_tem_exatamente_a_largura_calibrada(
        self, cal, janela_f010
    ) -> None:
        for chave in (
            "mercado_coluna_do_nome",
            "mercado_coluna_da_quantidade",
            "mercado_coluna_do_total",
        ):
            recorte = recorte_de_coluna(cal, janela_f010, 0, chave)
            assert recorte.shape[1] == int(getattr(cal, chave)["largura"])
            assert recorte.shape[0] == int(cal.mercado_grade["altura_da_linha"])


class TestOAcordoEntreAsDuasEscalas:
    """D-01 e D-02: o nome e lido DUAS vezes e as duas leituras sao confrontadas."""

    def test_as_duas_leitoras_sao_CHAMADAS_em_toda_linha_que_vira_LinhaLida(
        self, cal, janela_f010
    ) -> None:
        """O criterio central: a CHAMADA, e nao a existencia da leitora.

        Um `ler_linha` que lesse com uma escala so faz este teste FALHAR — e e
        exatamente o defeito que ele existe para pegar, porque uma leitura unica
        tambem produz `LinhaLida` valida e todos os outros criterios a
        aprovariam.
        """
        leitor, barata, conferencia, vistos_2x, vistos_3x = montar_leitor(
            cal, "Earth Spirit Evolution Stone", "Earth Spirit Evolution Stone"
        )
        leitor.observar(janela_f010)
        leitura = leitor.ultima_leitura
        assert leitura is not None
        ambas = set(vistos_2x) & set(vistos_3x)
        assert len(ambas) == len(leitura.linhas)
        assert len(ambas) > 0
        assert barata.chamadas == conferencia.chamadas == len(leitura.linhas)

    def test_a_coluna_do_nome_e_recortada_UMA_vez_e_lida_DUAS(
        self, cal, janela_f010
    ) -> None:
        """As duas leitoras recebem O MESMO objeto de pixels, nao dois recortes."""
        leitor, _b, _c, vistos_2x, vistos_3x = montar_leitor(
            cal, "Earth Spirit Evolution Stone", "Earth Spirit Evolution Stone"
        )
        leitor.observar(janela_f010)
        assert vistos_2x == vistos_3x
        assert vistos_2x != []

    def test_discordancia_de_serie_derruba_a_linha(self, cal, janela_f010) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Earth Spirit Evolution Stone", "Common Fafurion Doll"
        )
        leitor.observar(janela_f010)
        leitura = leitor.ultima_leitura
        assert leitura.linhas == ()
        assert MOTIVO_DA_DISCORDANCIA in leitura.motivos

    def test_Lv_I_contra_Lv_1_cai_pela_trava_de_digitos_e_isso_esta_MEDIDO(
        self, cal, janela_f010
    ) -> None:
        """A ressalva de 2026-08-30: o exemplo de D-02 NAO e absorvido.

        `Lv. I` (assinatura `''`) contra `Lv. 1` (assinatura `'1'`) NAO cai na
        mesma serie — a trava de digitos chega antes da similaridade. Medido:
        311 de 3.511 linhas limpas (8,86%) morrem assim, e o usuario aceitou o
        custo ao escolher `ocr-estrito` no portao do 02-03.
        """
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal,
            "Aden's Soul Crystal Lv. I - Armor",
            "Aden's Soul Crystal Lv. 1 - Armor",
        )
        leitor.observar(janela_f010)
        assert leitor.ultima_leitura.linhas == ()
        assert MOTIVO_DA_DISCORDANCIA in leitor.ultima_leitura.motivos

    def test_ruido_SEM_digito_e_absorvido_e_a_linha_PASSA(
        self, cal, janela_f010
    ) -> None:
        """`Chll` x `Doll`: o que o agrupamento absorve de verdade (0,8947)."""
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Valakas Chll", "Common Valakas Doll"
        )
        leitor.observar(janela_f010)
        linhas = leitor.ultima_leitura.linhas
        assert len(linhas) == len(LINHAS_QUE_ATRAVESSAM_F010)
        assert all(isinstance(linha, LinhaLida) for linha in linhas)

    def test_uma_opiniao_so_nunca_produz_leitura(self, cal, janela_f010) -> None:
        """A escala de conferencia devolvendo `None` nao produz acordo."""
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Earth Spirit Evolution Stone", None
        )
        leitor.observar(janela_f010)
        assert leitor.ultima_leitura.linhas == ()
        assert MOTIVO_DA_DISCORDANCIA in leitor.ultima_leitura.motivos

    def test_o_nome_exibido_vem_SEMPRE_da_escala_de_conferencia(
        self, cal, janela_f010
    ) -> None:
        """Regra escrita, nao acaso de ordem: duas execucoes, o mesmo rotulo."""
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Valakas Chll", "Common Valakas Doll"
        )
        leitor.observar(janela_f010)
        for linha in leitor.ultima_leitura.linhas:
            assert linha.nome_exibido == "Common Valakas Doll"


class TestOsQuatroMotivosDeDescarte:
    """Quatro peneiras, quatro causas, quatro consertos diferentes (D-17)."""

    def test_sao_quatro_motivos_distintos(self) -> None:
        motivos = {
            MOTIVO_DA_OCLUSAO,
            MOTIVO_DA_GRAMATICA,
            MOTIVO_DA_FAIXA_CINZENTA,
            MOTIVO_DA_DISCORDANCIA,
        }
        assert len(motivos) == 4

    def test_a_gramatica_produz_o_motivo_dela(self, cal, janela_f010) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Earth Spirit Evolution Stone", "Earth Spirit Evolution Stone"
        )
        leitor.observar(janela_f010)
        assert MOTIVO_DA_GRAMATICA in leitor.ultima_leitura.motivos

    def test_a_faixa_cinzenta_produz_o_motivo_dela(self, cal, janela_f010) -> None:
        """Similaridade entre o piso e o corte: nao agrupa NEM cria serie.

        O par e MEDIDO com a mesma `difflib` da producao: `Hunteds Tunic` x
        `Hunter's Tunic` da 0,888889, que cai dentro de [0,883732 ; 0,894737).

        A FIXTURA MUDOU EM 2026-09-01, E O MOTIVO PRECISA ESTAR ESCRITO. Ate a
        TRAVA POR PALAVRA (D-09) este teste usava `Earth Spirit Evolution Stone`
        x `Water Spirit Evolution Stone` (0,892857). Esse par e de ITENS
        DIFERENTES, e a faixa cinzenta o descartava PARA SEMPRE — o mesmo
        defeito que a trava foi escrita para consertar, so que com `Earth` e
        `Water` no lugar de `Armor` e `Weapon`. A trava agora o resolve antes
        (resto 0,4000 < piso 0,4500) e ele vira SERIE NOVA, que e o veredito
        certo; ele e cobrado assim em
        `test_mercado_catalogo.py::TestATravaPorPalavra`.

        A faixa cinzenta continua existindo e continua sendo cobrada — agora com
        um par cuja duvida e de CARACTERE dentro de UMA palavra (resto 0,8000,
        passa pela trava), que e a duvida que ela existe para absorver.
        """
        catalogo = {
            "hunter-s-tunic#": EntradaDoCatalogo(
                chave="hunter-s-tunic#",
                nome="Hunter's Tunic",
                assinatura="",
            )
        }
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal,
            "Hunteds Tunic",
            "Hunteds Tunic",
            catalogo=catalogo,
        )
        leitor.observar(janela_f010)
        assert MOTIVO_DA_FAIXA_CINZENTA in leitor.ultima_leitura.motivos

    def test_o_descarte_carrega_o_indice_da_linha(self, cal, janela_f010) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Earth Spirit Evolution Stone", "Earth Spirit Evolution Stone"
        )
        leitor.observar(janela_f010)
        leitura = leitor.ultima_leitura
        assert set(leitura.descartadas) | {
            linha.indice for linha in leitura.linhas
        } == set(range(int(cal.mercado_grade["linhas_por_pagina"])))


class TestOTracerPontaAPonta:
    """De pixels de janela ate `PaginaAceita`, contra fixtura versionada."""

    def test_um_frame_sozinho_NUNCA_produz_pagina_aceita(
        self, cal, janela_f010
    ) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Earth Spirit Evolution Stone", "Earth Spirit Evolution Stone"
        )
        assert leitor.observar(janela_f010) is None

    def test_dois_frames_da_MESMA_pagina_produzem_pagina_aceita(self, cal) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        assert leitor.observar(ler_fixtura(JANELA_F005)) is None
        pagina = leitor.observar(ler_fixtura(JANELA_F005_REPETIDA))
        assert isinstance(pagina, PaginaAceita)
        lidas = {
            linha.indice: (linha.total_em_centesimos, linha.quantidade)
            for linha in pagina.linhas
        }
        assert lidas == LINHAS_QUE_ATRAVESSAM_F005

    def test_dois_frames_de_PAGINAS_diferentes_nao_produzem_acordo(
        self, cal
    ) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        assert leitor.observar(ler_fixtura(JANELA_F005)) is None
        assert leitor.observar(ler_fixtura(JANELA_F010)) is None

    def test_a_serie_so_NASCE_quando_a_pagina_foi_aceita(self, cal) -> None:
        """Serie no catalogo e irreversivel; um frame sozinho nao a cria.

        Gravar no primeiro frame criaria serie a partir de uma leitura que o
        segundo frame ainda pode desmentir — e a Fase 3 referencia a chave em
        cada observacao do CSV.
        """
        catalogo: dict = {}
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll", catalogo=catalogo
        )
        leitor.observar(ler_fixtura(JANELA_F005))
        primeira = leitor.ultima_leitura.linhas[0]
        assert primeira.serie_nova is True
        assert catalogo == {}, "um frame sozinho NAO pode criar serie"

        leitor.observar(ler_fixtura(JANELA_F005_REPETIDA))
        assert primeira.chave_da_serie in catalogo

        leitor.observar(ler_fixtura(JANELA_F005))
        terceira = leitor.ultima_leitura.linhas[0]
        assert terceira.serie_nova is False
        assert terceira.chave_da_serie == primeira.chave_da_serie

    def test_duas_ofertas_do_MESMO_item_na_MESMA_pagina_viram_UMA_serie(
        self, cal
    ) -> None:
        """O catalogo tem de estar VIVO dentro da pagina, e nao so entre paginas.

        O INCIDENTE, sessao real de 2026-08-31 17:05: uma unica pagina aceita
        deixou `+4 Hunter's Stockings` e `+4 Hunter's St«kings` como DUAS
        series. A prova de que foi uma pagina so esta no
        `catalogo-de-nomes.csv`: as duas tem `primeira_vez == ultima_vez ==
        17:05:48.609000`, byte a byte. Isso reparte o preco de um item entre
        duas chaves e corta o `n` da mediana pela metade, em silencio.

        O AGRUPAMENTO NAO ERA O CULPADO — ele foi medido nos dois sentidos e
        junta o par com folga (similaridade 0,9268 contra o corte 0,8947, e as
        duas assinaturas de digito sao `4`, entao a trava nao as separa). Quem
        falhava era a FIACAO: `_ler_a_pagina` entregava a mesma referencia
        `self._catalogo` para todas as linhas da grade, e quem escreve nele e
        `_gravar_no_catalogo`, que so roda DEPOIS da pagina inteira. A serie que
        a linha 0 criava era invisivel para a linha 1 da mesma passada.

        O NOME CORROMPIDO E CONTEXTO, NAO O DEFEITO. O OCR le `Stockings` como
        `St«kings` de forma sistematica na escala 3x; a conferencia entre
        escalas so pega DISCORDANCIA, e quando as duas erram IGUAL a corrupcao
        passa. Por isso as duas leitoras devolvem o mesmo texto aqui — e a
        reproducao fiel. Com o agrupamento consultado com o estado certo, a
        corrupcao e ABSORVIDA e o dado fica inteiro.

        A LINHA 2 EM DIANTE FICA DE FORA DE PROPOSITO: ela prende o outro lado
        do portao. Um "conserto" que fundisse tudo na primeira serie da pagina
        tambem faria as duas primeiras linhas baterem, e passaria por aqui sem
        esta afirmacao.
        """
        BOM = "+4 Hunter's Stockings"
        CORROMPIDO = "+4 Hunter's St«kings"
        OUTRO = "Common Fafurion Doll"

        leitora = LeitoraPorLinhaDaPagina({0: BOM, 1: CORROMPIDO}, OUTRO)
        catalogo: dict = {}
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, leitora, leitora, catalogo=catalogo
        )

        leitor.observar(ler_fixtura(JANELA_F005))
        leitora.reiniciar()
        pagina = leitor.observar(ler_fixtura(JANELA_F005_REPETIDA))
        assert isinstance(pagina, PaginaAceita)

        por_indice = {linha.indice: linha for linha in pagina.linhas}
        assert {0, 1}.issubset(por_indice), "as duas linhas do item tem de passar"

        assert por_indice[0].chave_da_serie == por_indice[1].chave_da_serie, (
            "as duas ofertas do MESMO item na MESMA pagina cairam em series "
            f"diferentes: {por_indice[0].chave_da_serie!r} e "
            f"{por_indice[1].chave_da_serie!r}"
        )
        assert por_indice[1].serie_nova is False, (
            "a segunda oferta agrupou na primeira, entao ela NAO e serie nova"
        )

        do_hunter = sorted(c for c in catalogo if "hunter" in c)
        assert len(do_hunter) == 1, f"nasceram series demais: {do_hunter}"

        # O outro lado do portao: a linha 2 e outro item e continua sozinha.
        assert por_indice[2].chave_da_serie != por_indice[0].chave_da_serie
        assert len(catalogo) == 2, f"o catalogo da pagina ficou {sorted(catalogo)}"

    def test_as_linhas_saem_na_ORDEM_da_grade(self, cal) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        leitor.observar(ler_fixtura(JANELA_F005))
        indices = [linha.indice for linha in leitor.ultima_leitura.linhas]
        assert indices == sorted(indices)

    def test_o_valor_e_INTEIRO_em_centesimos_e_nunca_float(self, cal) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        leitor.observar(ler_fixtura(JANELA_F005))
        for linha in leitor.ultima_leitura.linhas:
            assert isinstance(linha.total_em_centesimos, int)
            assert not isinstance(linha.total_em_centesimos, bool)
            assert isinstance(linha.quantidade, int)


class TestOUnitarioELIDOMasNuncaGuardadoComoPreco:
    """O 02-06 acrescentou a TERCEIRA leitura — e so para CONFERIR.

    A classe que vivia aqui no 02-04 afirmava o contrario (`a coluna do unitario
    NAO e recortada nesta onda`), e afirmava certo: ler uma coluna que ninguem
    consumia por uma onda inteira seria leitura morta. A onda em que ela passa a
    ter consumidor e esta, entao a afirmacao INVERTE. O que NAO inverte e a
    proibicao de guardar o unitario como preco.
    """

    def test_LinhaLida_nao_guarda_o_unitario_como_preco(self) -> None:
        campos = set(LinhaLida.__dataclass_fields__)
        assert "unitario" not in campos
        assert "unitario_em_centesimos" not in campos

    def test_a_docstring_explica_por_que_o_unitario_nao_e_dado(self) -> None:
        texto = LinhaLida.__doc__.lower()
        assert "arredond" in texto
        assert "02-06" in texto

    def test_a_coluna_do_unitario_E_recortada_a_partir_desta_onda(self) -> None:
        """O consumidor chegou: `mercado_pagina` tem de fatiar a quarta coluna."""
        import l2scanner.mercado_pagina as pagina

        fonte = inspect.getsource(pagina)
        assert "mercado_coluna_do_unitario" in fonte


class TestODescarteNaoEDado:
    """Descarte nao vira leitura, e leitura nao vira descarte."""

    def test_LinhaLida_e_Descarte_sao_tipos_diferentes(self) -> None:
        assert LinhaLida is not Descarte
        assert set(LinhaLida.__dataclass_fields__) != set(
            Descarte.__dataclass_fields__
        )

    def test_a_linha_descartada_nao_entra_na_comparacao_do_estabilizador(
        self, cal
    ) -> None:
        """Duas paginas com os MESMOS descartes e leituras diferentes nao casam."""
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        leitor.observar(ler_fixtura(JANELA_F005))
        assert leitor.observar(ler_fixtura(JANELA_F010)) is None


# ---------------------------------------------------------------------------
# Task 2 — a sonda de oclusao no lugar certo do pipeline, e a linha vazia
# ---------------------------------------------------------------------------

JANELA_TOOLTIP = FIXTURES / "janela_tooltip_f012.png"
JANELA_COM_LINHAS_VAZIAS = FIXTURES / "janela_com_linhas_vazias.png"
LINHA_SOB_TOOLTIP = FIXTURES / "linha_sob_tooltip_f015.png"
LINHA_LIMPA_NO_TOOLTIP = FIXTURES / "linha_limpa_no_frame_do_tooltip_f015.png"
LINHA_SOB_ALVO = FIXTURES / "linha_sob_alvo_f024.png"
LINHA_LIMPA_NO_ALVO = FIXTURES / "linha_limpa_no_frame_do_alvo_f024.png"
LINHA_VAZIA_PAR = FIXTURES / "linha_vazia_par.png"
LINHA_VAZIA_IMPAR = FIXTURES / "linha_vazia_impar.png"
LINHA_CHEIA_PAR = FIXTURES / "linha_limpa_par_f010.png"
LINHA_CHEIA_IMPAR = FIXTURES / "linha_limpa_impar_f010.png"

# As duas paridades de banda de `mercado-aberto/frame_000060`, o pior caso de
# NOME LONGO que o censo gravou: `Protecting Scroll: Enchant C-grade Armor`, 40
# caracteres, nas dez linhas, e SEM tooltip nenhuma por cima — conferido a olho
# no frame inteiro. A tinta do nome termina em x=247 do recorte da linha; a
# sonda calibrada comeca em x=207. Sao 40 px de GLIFO dentro da sonda.
LINHA_LIMPA_NOME_LONGO_PAR = FIXTURES / "linha_limpa_nome_longo_par_f060.png"
LINHA_LIMPA_NOME_LONGO_IMPAR = (
    FIXTURES / "linha_limpa_nome_longo_impar_f060.png"
)

# O PIOR NOME QUE O CAMPO JA PRODUZIU, e o que derrubou a sonda de 31/08.
# `nome-longo-weapon/frame_000000`, linhas 0 e 1:
# `Protecting Scroll: Enchant C-grade Weapon`, 41 caracteres, tinta ate x=255 --
# NOVE PIXELS ALEM do dx0=246 onde a sonda horizontal de 31/08 comeca. Um unico
# caractere a mais que o `...C-grade Armor` (40 ch, tinta ate x=246) empurrou a
# tinta 8 px e pos a sonda inteira DENTRO do nome. Sem tooltip nenhuma no frame.
LINHA_LIMPA_NOME_LONGO_WEAPON_PAR = (
    FIXTURES / "linha_limpa_nome_longo_weapon_par_f000.png"
)
LINHA_LIMPA_NOME_LONGO_WEAPON_IMPAR = (
    FIXTURES / "linha_limpa_nome_longo_weapon_impar_f000.png"
)

# A SONDA DE BANDA VERTICAL, escrita AQUI e nao lida da calibracao de fixtura,
# porque o que estes testes afirmam e a CAPACIDADE do detector de honrar uma
# banda -- nao o numero que a varredura gravou. Trocar o numero da fixtura nao
# pode ser o que faz este bloco ficar verde.
#
# x[42, 489) e a `janela_de_busca` INTEIRA (uniao das colunas do nome e da
# quantidade, ja derivada das colunas calibradas) -- nao ha `dx0` a escolher, e
# e essa escolha que o campo derrubou duas vezes. dy[3, 11) e a margem vertical
# de cima da linha, e quem a escolheu foi `tools/medir_oclusao.py` sobre as 9
# gravacoes do censo: MEDIDO, a tinta dessa janela vive em dy[15, 27], entao a
# banda tem 4 px de folga ate o texto e 3 px ate a moldura da linha anterior.
SONDA_DE_BANDA_VERTICAL = {
    "dx0": 42,
    "dx1": 489,
    "dy0": 3,
    "dy1": 11,
    "folga": 0,
}

# As oito primeiras linhas de `tooltip/frame_000012` estao COBERTAS e as duas
# ultimas nao. Medido com a sonda calibrada; e o mesmo frame que D-15 descreve.
COBERTAS_NO_TOOLTIP = (0, 1, 2, 3, 4, 5, 6, 7)
DESCOBERTAS_NO_TOOLTIP = (8, 9)


def em_cinza(caminho: Path) -> np.ndarray:
    return cv2.cvtColor(ler_fixtura(caminho), cv2.COLOR_BGR2GRAY)


def _dispersao_na_banda(caminho: Path) -> float:
    """A dispersao CRUA da banda vertical, sem o limiar no meio.

    A assertiva de folga compara duas populacoes, e comparar dois booleanos nao
    diz distancia nenhuma. Aqui a medicao vem da MESMA primitiva que a producao
    usa (`nivel_de_fundo_da_linha`), nunca de uma conta reescrita no teste.
    """
    sonda = SONDA_DE_BANDA_VERTICAL
    medido = nivel_de_fundo_da_linha(
        em_cinza(caminho),
        (
            sonda["dx0"],
            sonda["dy0"],
            sonda["dx1"] - sonda["dx0"],
            sonda["dy1"] - sonda["dy0"],
        ),
        sonda["folga"],
    )
    assert medido is not None, caminho
    return float(medido[1])


def fatiar_a_linha(cal, janela, indice: int) -> dict:
    """A linha inteira e as tres colunas, como `LeitorDePagina` as fatia."""
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
    saida = {
        "linha": janela[topo : topo + altura, gx : gx + int(grade["largura"])]
    }
    for nome, chave in (
        ("nome", "mercado_coluna_do_nome"),
        ("total", "mercado_coluna_do_total"),
        ("quantidade", "mercado_coluna_da_quantidade"),
        ("unitario", "mercado_coluna_do_unitario"),
    ):
        coluna = getattr(cal, chave)
        x = ox + int(coluna["dx"])
        saida[nome] = janela[topo : topo + altura, x : x + int(coluna["largura"])]
    return saida


def chamar_ler_linha(
    cal,
    moldes,
    recortes: dict,
    indice: int,
    catalogo=None,
    *,
    tolerancia=None,
    trava=None,
):
    """`ler_linha` direto, com as duas leitoras CONTADORAS.

    `tolerancia` chega EXPLICITA em toda chamada porque em `ler_linha` ela nao
    tem valor de fabrica: a guarda de cruzamento so descarta com um numero que
    alguem mediu, e um default aqui esconderia justamente quem o forneceu.

    `trava` OMITIDA VIRA UMA TRAVA NOVA, e nunca `None`. `ler_linha` tambem a
    exige sem valor de fabrica, pelo charter deste modulo; uma trava nova por
    chamada e o equivalente de "um tick isolado", que e o que a maioria destes
    testes quer. Quem precisa de DOIS ticks passa a MESMA trava nos dois, e e
    exatamente essa diferenca que prova a supressao da repeticao.
    """
    from l2scanner.mercado_leitura import TravaDaObservacao

    if trava is None:
        trava = TravaDaObservacao()
    contagem = {"2x": 0, "3x": 0}

    def barata(_pixels):
        contagem["2x"] += 1
        return "Common Fafurion Doll"

    def conferencia(_pixels):
        contagem["3x"] += 1
        return "Common Fafurion Doll"

    resultado = ler_linha(
        indice,
        recortes["linha"],
        recortes["nome"],
        recortes["total"],
        recortes["quantidade"],
        recortes["unitario"],
        moldes=moldes,
        tolerancia_do_cruzamento=tolerancia,
        trava_da_observacao=trava,
        piso=float(cal.mercado_limiar_de_leitura_de_glifo),
        margem=float(cal.mercado_margem_de_leitura_de_glifo),
        # OS DOIS PISOS DE BRILHO, cada um da sua fonte: as colunas de MOEDA no
        # COMPARTILHADO, nomeado a partir de `identidade`; a Quantity no PROPRIO
        # dela, vindo da calibracao de fixtura, que por sua vez o copia verbatim
        # da calibracao de producao. O teste nunca escolhe este numero.
        valor_minimo_do_numero=VALOR_MINIMO_DO_TEXTO,
        valor_minimo_da_quantidade=int(
            cal.mercado_limiar_de_brilho_da_quantidade
        ),
        # A FOLGA DE COLA, tambem da calibracao de fixtura, que a copia
        # VERBATIM da producao. `None` seria a GUARDA — um estado legitimo, mas
        # nao o que o tracer mede.
        folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
        sonda=cal.mercado_sonda_do_fundo,
        limiar_de_dispersao=float(cal.mercado_limiar_de_dispersao_do_fundo),
        catalogo={} if catalogo is None else catalogo,
        corte_de_similaridade=float(cal.mercado_corte_de_similaridade),
        piso_de_similaridade=float(cal.mercado_piso_de_similaridade),
        ler_texto=barata,
        ler_texto_conferencia=conferencia,
    )
    return resultado, contagem


class TestASondaDeOclusao:
    """D-14: o sinal e a UNIFORMIDADE DO FUNDO, nunca a confianca do casamento."""

    def test_a_linha_sob_a_tooltip_e_recusada(self, cal) -> None:
        assert (
            linha_ocluida(
                em_cinza(LINHA_SOB_TOOLTIP),
                cal.mercado_sonda_do_fundo,
                float(cal.mercado_limiar_de_dispersao_do_fundo),
            )
            is True
        )

    def test_a_linha_limpa_do_MESMO_frame_passa(self, cal) -> None:
        assert (
            linha_ocluida(
                em_cinza(LINHA_LIMPA_NO_TOOLTIP),
                cal.mercado_sonda_do_fundo,
                float(cal.mercado_limiar_de_dispersao_do_fundo),
            )
            is False
        )

    def test_a_marcacao_de_alvo_cai_pelo_MESMO_mecanismo(self, cal) -> None:
        """D-16: sem caso especial. O mesmo detector pega tooltip e alvo."""
        assert (
            linha_ocluida(
                em_cinza(LINHA_SOB_ALVO),
                cal.mercado_sonda_do_fundo,
                float(cal.mercado_limiar_de_dispersao_do_fundo),
            )
            is True
        )
        assert (
            linha_ocluida(
                em_cinza(LINHA_LIMPA_NO_ALVO),
                cal.mercado_sonda_do_fundo,
                float(cal.mercado_limiar_de_dispersao_do_fundo),
            )
            is False
        )

    @pytest.mark.parametrize(
        "linha",
        [LINHA_LIMPA_NOME_LONGO_PAR, LINHA_LIMPA_NOME_LONGO_IMPAR],
        ids=["banda_par", "banda_impar"],
    )
    def test_a_linha_de_NOME_LONGO_sem_tooltip_nenhuma_PASSA(
        self, cal, linha
    ) -> None:
        """O COMPRIMENTO DO NOME nao pode ser motivo de recusa.

        A sonda responde "ha alguma coisa desenhada POR CIMA desta linha". O
        texto que o proprio jogo escreve na coluna do nome NAO e alguma coisa
        por cima: e o conteudo da linha. Recusar por causa dele e recusar a
        linha por ser legivel demais.

        MEDIDO em campo, 2026-08-31, aba Enhancement > Scrolls: as quatro
        linhas de `Protecting Scroll: Enchant C-grade Armor` (40 caracteres)
        foram recusadas em TODOS os 32 ticks, e as seis de nome curto passaram
        em todos. Sobraram 6 linhas comparadas contra um piso de 7, e as 31
        paginas do periodo foram perdidas — `observacoes.csv` saiu so com o
        cabecalho.

        AS DUAS PARIDADES entram porque a grade tem listra alternada (moda 48 e
        66) e a sonda e auto-referente: uma so das duas provaria metade.
        """
        assert (
            linha_ocluida(
                em_cinza(linha),
                cal.mercado_sonda_do_fundo,
                float(cal.mercado_limiar_de_dispersao_do_fundo),
            )
            is False
        )

    # -- a sonda de BANDA VERTICAL (2026-09-01) --------------------------

    @pytest.mark.parametrize(
        "linha",
        [
            LINHA_LIMPA_NOME_LONGO_WEAPON_PAR,
            LINHA_LIMPA_NOME_LONGO_WEAPON_IMPAR,
        ],
        ids=["banda_par", "banda_impar"],
    )
    def test_a_banda_vertical_ACEITA_o_nome_de_41_caracteres(
        self, cal, linha
    ) -> None:
        """O sinal para de competir com o texto, e este e o teste que prova.

        DUAS VEZES a sonda foi movida na horizontal e DUAS VEZES o campo
        produziu um nome mais comprido que a alcancou: `207..417` morreu contra
        `...C-grade Armor` (40 ch, tinta ate x=246) e `246..396` morreu contra
        `...C-grade Weapon` (41 ch, tinta ate x=255). UM caractere entre as
        duas. Mover de novo so escolhe qual sera o proximo item a quebrar.

        A banda vertical nao tem essa falha porque nao disputa espaco com o
        nome: MEDIDO nas 120 linhas limpas do gabarito ampliado, a tinta da
        janela x[42,489) vive em dy[15,26] e a banda esta em dy[2,10). O nome
        pode crescer ate encher a coluna inteira que nao entra na banda.

        As DUAS paridades de banda entram porque a grade e listrada (moda 48 e
        66) e a sonda e auto-referente: uma so provaria metade.

        Medido nestas duas fixturas, com a banda: 0,0036 e 0,0020, contra um
        limiar de producao de 0,030130. Com a sonda horizontal de 31/08 e o
        limiar dela: 0,0114 e 0,0119 contra 0,003607 -- TRES VEZES o limiar, e a
        linha era limpa. As dez linhas de cada frame foram recusadas assim.
        """
        assert (
            linha_ocluida(
                em_cinza(linha),
                SONDA_DE_BANDA_VERTICAL,
                float(cal.mercado_limiar_de_dispersao_do_fundo),
            )
            is False
        )

    @pytest.mark.parametrize(
        "linha",
        [LINHA_SOB_TOOLTIP, LINHA_SOB_ALVO],
        ids=["tooltip", "marcacao_de_alvo"],
    )
    def test_a_banda_vertical_CONTINUA_RECUSANDO_a_linha_coberta(
        self, cal, linha
    ) -> None:
        """O CONTROLE NEGATIVO. Sem ele, "aceitar tudo" passaria no teste acima.

        Um sinal de oclusao que so precisasse aceitar linha limpa se satisfaria
        devolvendo `False` sempre -- e essa e exatamente a falha que o incidente
        27x descreve um nivel acima: a tooltip e SEMITRANSPARENTE, ela nao apaga
        o numero, ela o MISTURA, e numero misturado produz glifo plausivel com
        valor errado e confianca alta.

        As duas coberturas conhecidas entram: a tooltip (a farta) e a marcacao
        de alvo (a APERTADA -- opaca, mas cobrindo menos da linha). Medido com a
        banda nestas fixturas: tooltip 0,5182 e alvo 0,2659, contra um limiar de
        producao de 0,030130 -- 17x e 8,8x acima dele.
        """
        assert (
            linha_ocluida(
                em_cinza(linha),
                SONDA_DE_BANDA_VERTICAL,
                float(cal.mercado_limiar_de_dispersao_do_fundo),
            )
            is True
        )

    def test_a_banda_vertical_NAO_afrouxa_a_peneira(self, cal) -> None:
        """A separacao tem de ser MAIOR que a da sonda horizontal, nunca menor.

        A tentacao, depois de duas quebras, e alargar o limiar ate o nome longo
        passar. Isso consertaria o sintoma DESLIGANDO a guarda. Este teste
        prende o contrario: com a banda, a distancia entre a pior linha LIMPA
        conhecida e a MENOR cobertura conhecida (a marcacao de alvo) tem de ser
        de pelo menos uma ordem de grandeza.

        A regua e historica, e cada numero e um pedaco de campo perdido:

            sonda 207..417  folga 2,8x  -> quebrou contra 40 caracteres
            sonda 246..396  folga 1,8x  -> quebrou contra 41 caracteres
            banda dy[3,11)  folga  69x  -> medida contra os dois

        (as duas primeiras folgas sao contra o gabarito AMPLIADO, que inclui os
        nomes longos; contra o gabarito curto de entao a segunda parecia 30,8x,
        e essa diferenca e a licao inteira.)
        """
        limpas = [
            _dispersao_na_banda(caminho)
            for caminho in (
                LINHA_LIMPA_NOME_LONGO_WEAPON_PAR,
                LINHA_LIMPA_NOME_LONGO_WEAPON_IMPAR,
                LINHA_LIMPA_NOME_LONGO_PAR,
                LINHA_LIMPA_NOME_LONGO_IMPAR,
                LINHA_LIMPA_NO_TOOLTIP,
                LINHA_LIMPA_NO_ALVO,
                LINHA_CHEIA_PAR,
                LINHA_CHEIA_IMPAR,
            )
        ]
        cobertas = [
            _dispersao_na_banda(caminho)
            for caminho in (LINHA_SOB_TOOLTIP, LINHA_SOB_ALVO)
        ]
        pior_limpa, melhor_coberta = max(limpas), min(cobertas)
        assert melhor_coberta > 10.0 * pior_limpa, (
            f"pior LIMPA {pior_limpa:.4f}, melhor COBERTA {melhor_coberta:.4f}"
        )

    def test_sem_dy_na_sonda_a_leitura_cai_no_comportamento_ANTIGO(
        self, cal
    ) -> None:
        """Calibracao velha (so dx0/dx1/folga) nao pode virar 'aceita tudo'.

        Enquanto o usuario nao rodar a varredura de novo, o `calibration.json`
        dele ainda traz a sonda horizontal. O fallback correto e o
        comportamento de sempre -- a linha inteira em altura --, que erra para o
        lado de RECUSAR. Erra caro, mas erra FECHADO: e o mesmo default de
        `sonda is None`.
        """
        sonda_antiga = {"dx0": 246, "dx1": 396, "folga": 2}
        assert (
            linha_ocluida(
                em_cinza(LINHA_SOB_TOOLTIP),
                sonda_antiga,
                float(cal.mercado_limiar_de_dispersao_do_fundo),
            )
            is True
        )
        assert (
            linha_ocluida(
                em_cinza(LINHA_CHEIA_PAR),
                sonda_antiga,
                float(cal.mercado_limiar_de_dispersao_do_fundo),
            )
            is False
        )

    def test_ler_linha_NAO_tem_ramo_dedicado_a_marcacao_de_alvo(self) -> None:
        fonte = inspect.getsource(ler_linha).lower()
        assert "alvo" not in fonte.split('"""')[2], (
            "o CODIGO de ler_linha nao pode mencionar a marcacao de alvo"
        )

    def test_sem_sonda_calibrada_a_resposta_e_RECUSA(self, cal) -> None:
        """Feature OFF e o unico default seguro; `None` nao vira 'esta limpa'."""
        assert linha_ocluida(em_cinza(LINHA_LIMPA_NO_TOOLTIP), None, 0.5) is True
        assert linha_ocluida(em_cinza(LINHA_LIMPA_NO_TOOLTIP), {}, 0.5) is True

    def test_sonda_impossivel_de_medir_e_RECUSA(self, cal) -> None:
        """'Nao da para medir' NAO e 'esta limpa' — sao respostas diferentes."""
        sonda_maior_que_a_linha = {"dx0": 0, "dx1": 100_000, "folga": 2}
        assert (
            linha_ocluida(
                em_cinza(LINHA_LIMPA_NO_TOOLTIP), sonda_maior_que_a_linha, 0.5
            )
            is True
        )


class TestAOrdemDoPipeline:
    """A sonda roda ANTES do OCR, e o teste prova a ORDEM contando chamadas."""

    def test_ZERO_chamadas_de_OCR_para_a_linha_recusada_pela_sonda(
        self, cal, moldes
    ) -> None:
        janela = ler_fixtura(JANELA_TOOLTIP)
        recortes = fatiar_a_linha(cal, janela, COBERTAS_NO_TOOLTIP[0])
        resultado, contagem = chamar_ler_linha(
            cal, moldes, recortes, COBERTAS_NO_TOOLTIP[0]
        )
        assert isinstance(resultado, Descarte)
        assert resultado.motivo == MOTIVO_DA_OCLUSAO
        assert contagem == {"2x": 0, "3x": 0}, (
            "a linha coberta pagou OCR — a sonda esta depois dele no pipeline"
        )

    def test_a_linha_que_ATRAVESSA_paga_as_DUAS_chamadas(self, cal, moldes) -> None:
        """O controle do teste acima: sem ele, zero chamadas seria vacuo."""
        janela = ler_fixtura(JANELA_F010)
        indice = sorted(LINHAS_QUE_ATRAVESSAM_F010)[0]
        recortes = fatiar_a_linha(cal, janela, indice)
        resultado, contagem = chamar_ler_linha(cal, moldes, recortes, indice)
        assert isinstance(resultado, LinhaLida)
        assert contagem == {"2x": 1, "3x": 1}

    def test_ZERO_chamadas_de_OCR_quando_o_numero_nao_se_le(
        self, cal, moldes
    ) -> None:
        """A coluna de numero custa 13 casamentos; o OCR custa ~7 ms."""
        janela = ler_fixtura(JANELA_F010)
        recortes = fatiar_a_linha(cal, janela, 0)
        resultado, contagem = chamar_ler_linha(cal, moldes, recortes, 0)
        assert isinstance(resultado, Descarte)
        assert resultado.motivo == MOTIVO_DA_GRAMATICA
        assert contagem == {"2x": 0, "3x": 0}


class TestARecusaEPorLinhaNuncaPorPagina:
    """D-15: a tooltip cobriu 8 linhas seguidas e as outras 2 seguem sendo lidas."""

    def test_as_oito_cobertas_caem_por_OCLUSAO(self, cal) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        leitor.observar(ler_fixtura(JANELA_TOOLTIP))
        leitura = leitor.ultima_leitura
        por_indice = dict(zip(leitura.descartadas, leitura.motivos))
        for indice in COBERTAS_NO_TOOLTIP:
            assert por_indice[indice] == MOTIVO_DA_OCLUSAO

    def test_as_duas_descobertas_do_MESMO_frame_seguem_sendo_JULGADAS(
        self, cal
    ) -> None:
        """A pagina NAO parou no bloco coberto.

        MEDIDO, e o plano previa outra coisa: as duas linhas descobertas deste
        frame nao viram `LinhaLida`, mas NAO caem por oclusao — elas caem pela
        peneira SEGUINTE, cada uma julgada pelos proprios pixels. E isso que
        distingue "recusa por linha" de "recusa por pagina": uma recusa por
        pagina daria a TODAS as dez linhas o mesmo motivo.

        O CONSERTO CHEGOU NO 02-07, E ESTE TESTE MUDOU DE FORMA POR MEDICAO.
        Ate aqui as duas linhas descobertas caiam pela peneira SEGUINTE — a
        gramatica —, porque a quantidade delas e `1` e o tronco do `1` da coluna
        Quantity e desenhado a V = 174 (remedido no censo do 02-07), abaixo do
        piso compartilhado 180 de `mascara_de_texto`. Com o piso PROPRIO da
        coluna, MEDIDO em 161, elas atravessam INTEIRAS e leem `1`. A afirmacao
        que o teste protege nao mudou — a recusa e por LINHA e nunca por PAGINA
        —, e agora ela e ainda mais forte: as descobertas nao aparecem entre as
        descartadas de jeito nenhum, e TODA descartada caiu por oclusao.
        """
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        leitor.observar(ler_fixtura(JANELA_TOOLTIP))
        leitura = leitor.ultima_leitura
        lidas = {linha.indice: linha.quantidade for linha in leitura.linhas}
        for indice in DESCOBERTAS_NO_TOOLTIP:
            assert indice not in leitura.descartadas
            assert lidas[indice] == 1
        assert set(leitura.motivos) == {MOTIVO_DA_OCLUSAO}

    def test_a_pagina_com_tooltip_nao_para_no_primeiro_descarte(self, cal) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        leitor.observar(ler_fixtura(JANELA_TOOLTIP))
        leitura = leitor.ultima_leitura
        # TODA linha da grade foi JULGADA — nenhuma ficou sem veredito. Ate o
        # 02-07 as dez cabiam em `descartadas`; com o piso proprio da Quantity
        # duas delas viram `LinhaLida`, e a soma e que continua sendo dez. E a
        # soma que responde a pergunta do teste: a pagina nao parou no primeiro
        # descarte.
        assert len(leitura.descartadas) + len(leitura.linhas) == int(
            cal.mercado_grade["linhas_por_pagina"]
        )
        assert len(leitura.descartadas) > 0

    def test_a_linha_descartada_NAO_entra_no_estabilizador(self, cal) -> None:
        """A descartada nunca chega a `PaginaAceita`, e isso se ve pelo POSITIVO.

        A HISTORIA DESTE TESTE, EM TRES ONDAS, PORQUE ELA EXPLICA A FORMA:

        Ate o 02-07 esta fixtura nao produzia leitura nenhuma — as dez linhas
        caiam — e a afirmacao so podia ser feita pela NEGATIVA (`is None`), que
        e verdadeira tambem quando o estabilizador esta simplesmente quebrado.
        Com o piso proprio da Quantity, MEDIDO em 161, as duas linhas
        descobertas passaram a atravessar e o teste virou afirmacao positiva.

        **O 02-05 mudou a resposta de novo, e de proposito.** O piso de posicoes
        comparadas (`mercado_minimo_de_linhas_comparadas`, gravado em 7) recusa
        esta pagina com o piso de PRODUCAO — e esta CERTO em recusar: 2 linhas
        lidas de 10 e precisamente a "pagina praticamente nao lida" que
        T-02-26 descreve, e aceita-la seria o acordo trivial. O piso NAO foi
        afrouxado para salvar o teste; ele foi tornado EXPLICITO aqui, derivado
        das linhas que a propria fixtura entrega, para que a afirmacao continue
        sendo sobre a linha DESCARTADA e nao sobre o piso.

        A recusa pelo piso com o valor de producao tem teste proprio, e ele fica
        em `tests/test_mercado_pagina.py`, onde o piso mora.
        """
        import copy

        medidor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        medidor.observar(ler_fixtura(JANELA_TOOLTIP))
        descobertas = len(medidor.ultima_leitura.linhas)
        assert descobertas < int(cal.mercado_minimo_de_linhas_comparadas), (
            "esta fixtura deixou de ser o caso 'quase toda coberta'; sem isso o "
            "teste nao esta mais afirmando o que diz afirmar"
        )

        com_piso_explicito = copy.deepcopy(cal)
        com_piso_explicito.mercado_minimo_de_linhas_comparadas = descobertas

        leitor, _b, _c, _v2, _v3 = montar_leitor(
            com_piso_explicito, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        assert leitor.observar(ler_fixtura(JANELA_TOOLTIP)) is None
        pagina = leitor.observar(ler_fixtura(JANELA_TOOLTIP))
        assert isinstance(pagina, PaginaAceita)
        assert {linha.indice for linha in pagina.linhas} == set(
            DESCOBERTAS_NO_TOOLTIP
        )
        descartadas = set(leitor.ultima_leitura.descartadas)
        assert descartadas and not (
            descartadas & {linha.indice for linha in pagina.linhas}
        )


class TestALinhaVazia:
    """D-12: por AUSENCIA DE CONTEUDO, nunca por cor de fundo."""

    def test_as_duas_paridades_de_banda_dao_o_MESMO_veredito(self) -> None:
        par = ler_fixtura(LINHA_VAZIA_PAR)
        impar = ler_fixtura(LINHA_VAZIA_IMPAR)
        assert linha_vazia(par) is True
        assert linha_vazia(impar) is True

    def test_os_dois_fundos_das_linhas_vazias_sao_DIFERENTES(self) -> None:
        """Se fossem iguais, o teste acima nao provaria nada sobre a listra."""
        par = cv2.cvtColor(ler_fixtura(LINHA_VAZIA_PAR), cv2.COLOR_BGR2HSV)[:, :, 2]
        impar = cv2.cvtColor(
            ler_fixtura(LINHA_VAZIA_IMPAR), cv2.COLOR_BGR2HSV
        )[:, :, 2]
        assert int(par.max()) != int(impar.max())

    def test_as_duas_paridades_de_linha_CHEIA_tambem_concordam(self) -> None:
        assert linha_vazia(ler_fixtura(LINHA_CHEIA_PAR)) is False
        assert linha_vazia(ler_fixtura(LINHA_CHEIA_IMPAR)) is False

    def test_a_linha_vazia_devolve_None_e_nao_Descarte(self, cal, moldes) -> None:
        janela = ler_fixtura(JANELA_COM_LINHAS_VAZIAS)
        recortes = fatiar_a_linha(cal, janela, 5)
        resultado, contagem = chamar_ler_linha(cal, moldes, recortes, 5)
        assert resultado is None
        assert contagem == {"2x": 0, "3x": 0}

    def test_a_linha_vazia_marca_o_FIM_da_pagina(self, cal) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        leitor.observar(ler_fixtura(JANELA_COM_LINHAS_VAZIAS))
        leitura = leitor.ultima_leitura
        assert leitura.vazias == (1, 2, 3, 4, 5, 6, 7, 8, 9)
        # A linha 0 tem quantidade `1` e, ate o 02-07, caia FECHADA no piso
        # compartilhado. Com o piso proprio da Quantity, MEDIDO em 161, ela
        # ATRAVESSA — e o que o teste afirma continua sendo o mesmo: as nove
        # vazias marcam o fim da pagina e nenhuma delas vira descarte.
        assert leitura.descartadas == ()
        assert [linha.indice for linha in leitura.linhas] == [0]

    def test_linha_vazia_NAO_conta_como_perda(self, cal) -> None:
        """Tres estados distintos: lida, descartada, vazia."""
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        leitor.observar(ler_fixtura(JANELA_COM_LINHAS_VAZIAS))
        leitura = leitor.ultima_leitura
        assert set(leitura.vazias) & set(leitura.descartadas) == set()
        assert set(leitura.vazias) & {
            linha.indice for linha in leitura.linhas
        } == set()


class TestOLogDaRecusa:
    """A forma de `manutencao._registrar_desacordo`, e pelas mesmas razoes."""

    def test_a_recusa_e_ALTA(self, cal, caplog) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        with caplog.at_level("WARNING", logger="l2scanner.mercado_leitura"):
            leitor.observar(ler_fixtura(JANELA_TOOLTIP))
        assert [r for r in caplog.records if r.levelname == "WARNING"]

    def test_a_discordancia_registra_os_DOIS_textos_entre_delimitadores(
        self, cal, caplog
    ) -> None:
        """Espaco em branco importa: `Lv. 1` e `Lv.1` sao leituras diferentes."""
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Earth Spirit Evolution Stone", "Common Fafurion Doll"
        )
        with caplog.at_level("WARNING", logger="l2scanner.mercado_leitura"):
            leitor.observar(ler_fixtura(JANELA_F010))
        texto = caplog.text
        assert ">>>Earth Spirit Evolution Stone<<<" in texto
        assert ">>>Common Fafurion Doll<<<" in texto

    def test_NAO_ha_limitacao_de_repeticao(self, cal, caplog) -> None:
        """O log rotativo e a unica forense pos-farm: as linhas repetidas SAO
        o que responde 'por que nao gravou'."""
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        with caplog.at_level("WARNING", logger="l2scanner.mercado_leitura"):
            leitor.observar(ler_fixtura(JANELA_TOOLTIP))
            leitor.observar(ler_fixtura(JANELA_TOOLTIP))
        recusas = [r for r in caplog.records if "RECUSADA" in r.getMessage()]
        # UMA linha de log por linha descartada, em CADA uma das duas
        # observacoes. O total e DERIVADO da leitura e nao escolhido a mao: com
        # o piso proprio da Quantity duas das dez linhas passaram a atravessar,
        # e um 20 gravado aqui viraria um numero que sobreviveu a propria razao.
        descartadas = len(leitor.ultima_leitura.descartadas)
        assert descartadas > 0
        assert len(recusas) == 2 * descartadas


# ---------------------------------------------------------------------------
# Task 1 (02-06) — a guarda de cruzamento, e a TERCEIRA leitura que a alimenta
# ---------------------------------------------------------------------------
#
# O VEREDITO QUE MANDA NESTES TESTES JA EXISTE, E ELE REPROVOU. O 02-02 varreu
# 478 frames e 55.342 glifos e emitiu, na linha que este plano le literalmente:
#
#     GUARDA REPROVADA por tolerancia, 1273.0000 centesimos por unidade
#     (maximo 1.0)
#
# Por isso a bateria e DUPLA, e a assimetria e deliberada:
#
#   rota REPROVADA (producao)  `mercado_tolerancia_do_cruzamento` e `None`, a
#                              guarda nao descarta NADA, e o residuo vira
#                              OBSERVACAO — calculado, guardado e logado
#   rota APROVADA  (ensaio)    exercitada com a tolerancia DERIVADA (meio
#                              centesimo por unidade), porque o mecanismo tem de
#                              estar provado no dia em que uma medicao futura o
#                              aprovar. Este numero NAO e o de producao
#
# E o criterio central desta task nao e nenhuma das duas: e a TERCEIRA LEITURA
# ter acontecido. Sem o recorte de `mercado_coluna_do_unitario` o unitario chega
# nulo em toda linha, a guarda responde "nao opino" sempre, e todos os outros
# criterios ficam VERDES sobre codigo morto (T-02-39).

GLIFOS_DO_UNITARIO = FIXTURES / "glifos_unitario_f010.png"

# O caso conhecido do spike (SPIKE-RESPOSTAS secao 4): `40,00` por 48 unidades
# aparece na tela como `0,83`, e `0,83 x 48 = 39,84` — um numero que nunca
# existiu. O residuo e 16 contra o limite derivado 24.
SPIKE_TOTAL, SPIKE_UNITARIO, SPIKE_QUANTIDADE = 4000, 83, 48
SPIKE_RESIDUO = 16


def tolerancia_de_ensaio() -> float:
    """A tolerancia DERIVADA, por unidade — e nunca a de producao.

    Ela sai da propria aritmetica do arredondamento (meio centesimo por
    unidade), e nao de um numero escolhido: e por isso que ela pode viver num
    teste sem ser constante magica. A de producao e o que o 02-02 mediu, e o que
    ele mediu foi uma reprovacao.
    """
    return limite_derivado_do_cruzamento(1)


def adulterar_um_zero_em_oito(recorte_do_total: np.ndarray) -> np.ndarray:
    """Troca o `0` de `18,00` pelos PIXELS DO `8` DA MESMA LINHA -> `18,80`.

    A substituicao e injetada com pixel de verdade, do mesmo frame, da mesma
    linha e do mesmo rendering — e nao com um numero digitado no teste. E essa a
    ameaca que T-02-32 descreve: o par `0`x`8` tem a margem mais estreita do
    sistema (0,0370 medidos), a substituicao MANTEM a gramatica do numero
    intacta, e duas leituras do mesmo motor sobre o mesmo frame concordam no
    mesmo erro. So uma conferencia vinda de OUTRO lugar da tela a pega.

    Ela e especifica de `18,00`, que tem cinco runs — `1`, `8`, `,`, `0`, `0` —
    e os dois digitos envolvidos tem exatamente 4 px, medidos.
    """
    faixa, runs = segmentar_glifos(recorte_do_total)
    assert faixa is not None, "a fixtura do total nao tem pixel de texto"
    assert len(runs) == 5, f"esperava os 5 runs de `18,00`, vi {len(runs)}"
    oito, zero = runs[1], runs[3]
    assert (oito[1] - oito[0]) == (zero[1] - zero[0]) == 4
    copia = recorte_do_total.copy()
    copia[:, zero[0] : zero[1]] = recorte_do_total[:, oito[0] : oito[1]]
    return copia


def linha_com_o_total_adulterado(cal, janela, indice: int) -> dict:
    recortes = dict(fatiar_a_linha(cal, janela, indice))
    recortes["total"] = adulterar_um_zero_em_oito(recortes["total"])
    return recortes


class TestATerceiraLeituraACONTECE:
    """T-02-39: a guarda so vale se a coluna do unitario for mesmo LIDA."""

    def test_toda_LinhaLida_de_f010_carrega_residuo_do_cruzamento(
        self, cal, janela_f010
    ) -> None:
        """O criterio que pega a guarda instalada como codigo morto.

        Um `ler_linha` que nunca recorta a coluna do unitario faz este teste
        FALHAR — e nenhum outro criterio desta task o pegaria, porque "nao
        opino" e resultado legitimo e esperado em toda linha sem unitario.
        """
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Earth Spirit Evolution Stone", "Earth Spirit Evolution Stone"
        )
        leitor.observar(janela_f010)
        leitura = leitor.ultima_leitura
        com_residuo = [
            linha
            for linha in leitura.linhas
            if linha.residuo_do_cruzamento is not None
        ]
        assert len(leitura.linhas) > 0
        assert len(com_residuo) == len(leitura.linhas)

    def test_toda_LinhaLida_de_f005_carrega_residuo_do_cruzamento(
        self, cal
    ) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        leitor.observar(ler_fixtura(JANELA_F005))
        leitura = leitor.ultima_leitura
        com_residuo = [
            linha
            for linha in leitura.linhas
            if linha.residuo_do_cruzamento is not None
        ]
        assert len(leitura.linhas) == len(LINHAS_QUE_ATRAVESSAM_F005)
        assert len(com_residuo) == len(leitura.linhas)

    def test_o_unitario_da_fixtura_de_glifos_le_600(self, cal, moldes) -> None:
        """`glifos_unitario_f010.png` e `6,00`, e o cabecalho de
        `tests/test_mercado_glifos.py` ja o declarava antes deste plano."""
        assert (
            ler_celula_de_numero(
                ler_fixtura(GLIFOS_DO_UNITARIO),
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            == 600
        )

    def test_o_unitario_ILEGIVEL_nao_derruba_a_linha(
        self, cal, moldes, janela_f010
    ) -> None:
        """Falha fechada e sobre o DADO, nunca sobre a falta de conferencia."""
        recortes = dict(fatiar_a_linha(cal, janela_f010, 6))
        recortes["unitario"] = np.zeros_like(recortes["unitario"])
        for tolerancia in (None, tolerancia_de_ensaio()):
            resultado, _contagem = chamar_ler_linha(
                cal, moldes, recortes, 6, tolerancia=tolerancia
            )
            assert isinstance(resultado, LinhaLida)
            assert resultado.residuo_do_cruzamento is None
            assert resultado.total_em_centesimos == 1890


class TestOResiduoDoCruzamento:
    """Aritmetica INTEIRA de centesimos, e `None` sempre que faltar um fato."""

    def test_o_caso_conhecido_do_spike_fecha(self) -> None:
        assert (
            residuo_do_cruzamento(SPIKE_TOTAL, SPIKE_UNITARIO, SPIKE_QUANTIDADE)
            == SPIKE_RESIDUO
        )
        assert limite_derivado_do_cruzamento(SPIKE_QUANTIDADE) == 24
        assert SPIKE_RESIDUO <= limite_derivado_do_cruzamento(SPIKE_QUANTIDADE)

    def test_o_resultado_e_INTEIRO_e_nunca_float(self) -> None:
        residuo = residuo_do_cruzamento(1880, 600, 3)
        assert type(residuo) is int
        assert residuo == 80

    @pytest.mark.parametrize(
        "total,unitario,quantidade",
        [
            (None, 600, 3),
            (1800, None, 3),
            (1800, 600, None),
            (None, None, None),
        ],
    )
    def test_um_fato_que_faltou_devolve_None(
        self, total, unitario, quantidade
    ) -> None:
        assert residuo_do_cruzamento(total, unitario, quantidade) is None

    def test_quantidade_zero_nao_multiplica_nada(self) -> None:
        assert residuo_do_cruzamento(1800, 600, 0) is None


class TestCruzamentoConfere:
    """`None` e "nao opino", e "nao opino" NUNCA vira descarte (T-02-36)."""

    def test_a_tolerancia_NAO_tem_valor_de_fabrica(self) -> None:
        parametro = inspect.signature(cruzamento_confere).parameters[
            "tolerancia"
        ]
        assert parametro.default is inspect.Parameter.empty

    def test_ler_linha_tambem_exige_a_tolerancia_explicita(self) -> None:
        parametro = inspect.signature(ler_linha).parameters[
            "tolerancia_do_cruzamento"
        ]
        assert parametro.default is inspect.Parameter.empty

    def test_o_caso_do_spike_CONFERE_contra_a_tolerancia_derivada(self) -> None:
        assert (
            cruzamento_confere(
                SPIKE_TOTAL,
                SPIKE_UNITARIO,
                SPIKE_QUANTIDADE,
                tolerancia_de_ensaio(),
            )
            is True
        )

    def test_a_substituicao_0_por_8_NAO_confere(self) -> None:
        assert cruzamento_confere(1880, 600, 3, tolerancia_de_ensaio()) is False

    @pytest.mark.parametrize(
        "total,unitario,quantidade,tolerancia",
        [
            (1800, 600, 3, None),
            (1800, None, 3, 0.5),
            (None, 600, 3, 0.5),
            (1800, 600, 0, 0.5),
            (1800, 600, None, 0.5),
        ],
    )
    def test_nao_opino(self, total, unitario, quantidade, tolerancia) -> None:
        assert (
            cruzamento_confere(total, unitario, quantidade, tolerancia) is None
        )


class TestARotaREPROVADA:
    """A rota que a MEDICAO escolheu: observacao, nunca descarte."""

    def test_a_calibracao_traz_a_tolerancia_NULA(self, cal) -> None:
        assert cal.mercado_tolerancia_do_cruzamento is None

    def test_a_injecao_do_8_realmente_LANDOU_nos_pixels(
        self, cal, moldes, janela_f010
    ) -> None:
        """Sem esta afirmacao, um adulterador que nao adultera passaria calado."""
        recortes = linha_com_o_total_adulterado(cal, janela_f010, 8)
        assert (
            ler_celula_de_numero(
                recortes["total"],
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            == 1880
        )

    def test_a_linha_adulterada_NAO_e_descartada_e_guarda_o_residuo(
        self, cal, moldes, janela_f010
    ) -> None:
        """O preco do veredito, por escrito: 1880 ENTRA, com o residuo ao lado.

        E exatamente o dado errado que a guarda existiria para pegar. Ele passa
        porque a guarda nao se provou, e descartar com um sinal nao provado
        faria dela o defeito (T-02-36).
        """
        recortes = linha_com_o_total_adulterado(cal, janela_f010, 8)
        resultado, _contagem = chamar_ler_linha(
            cal, moldes, recortes, 8, tolerancia=None
        )
        assert isinstance(resultado, LinhaLida)
        assert resultado.total_em_centesimos == 1880
        assert resultado.residuo_do_cruzamento == 80

    def test_nenhuma_linha_da_pagina_e_descartada_pelo_cruzamento(
        self, cal, janela_f010
    ) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Earth Spirit Evolution Stone", "Earth Spirit Evolution Stone"
        )
        leitor.observar(janela_f010)
        assert MOTIVO_DO_CRUZAMENTO not in leitor.ultima_leitura.motivos

    def test_a_divergencia_vai_para_o_LOG_mesmo_sem_a_guarda(
        self, cal, moldes, janela_f010, caplog
    ) -> None:
        """A evidencia nao se perde so porque a guarda nao ligou."""
        recortes = linha_com_o_total_adulterado(cal, janela_f010, 8)
        with caplog.at_level("INFO", logger="l2scanner.mercado_leitura"):
            chamar_ler_linha(cal, moldes, recortes, 8, tolerancia=None)
        texto = caplog.text
        assert "cruzamento" in texto.lower()
        for numero in ("1880", "600", "80"):
            assert numero in texto

    def test_o_fonte_registra_a_medicao_REFUTADA_com_os_numeros(self) -> None:
        """`ocr.py:34-52`: um numero que caiu precisa dizer que caiu."""
        import l2scanner.mercado_leitura as modulo

        fonte = inspect.getsource(modulo)
        assert "REPROVADA" in fonte
        assert "1273" in fonte
        assert "0,6525" in fonte
        assert "0,0164" in fonte

    def test_o_veredito_do_02_02_esta_transcrito_no_fonte(self) -> None:
        import l2scanner.mercado_leitura as modulo

        fonte = inspect.getsource(modulo)
        assert "1273.0000 centesimos por unidade" in fonte


class TestARotaAPROVADA:
    """O mecanismo, exercitado com a tolerancia DERIVADA — nao a de producao."""

    def test_a_linha_intacta_passa_com_residuo_zero(
        self, cal, moldes, janela_f010
    ) -> None:
        recortes = fatiar_a_linha(cal, janela_f010, 8)
        resultado, _contagem = chamar_ler_linha(
            cal, moldes, recortes, 8, tolerancia=tolerancia_de_ensaio()
        )
        assert isinstance(resultado, LinhaLida)
        assert resultado.total_em_centesimos == 1800
        assert resultado.residuo_do_cruzamento == 0

    def test_a_linha_com_o_0_lido_como_8_vira_Descarte(
        self, cal, moldes, janela_f010
    ) -> None:
        recortes = linha_com_o_total_adulterado(cal, janela_f010, 8)
        resultado, _contagem = chamar_ler_linha(
            cal, moldes, recortes, 8, tolerancia=tolerancia_de_ensaio()
        )
        assert isinstance(resultado, Descarte)
        assert resultado.motivo == MOTIVO_DO_CRUZAMENTO

    def test_o_descarte_do_cruzamento_NAO_paga_OCR(
        self, cal, moldes, janela_f010
    ) -> None:
        """A guarda entra DEPOIS das tres celulas e ANTES do nome.

        Uma linha que a guarda derruba nunca vira dado — pagar ~7 ms de OCR por
        ela seria pagar por nada, pela mesma razao ja escrita para as colunas de
        numero.
        """
        recortes = linha_com_o_total_adulterado(cal, janela_f010, 8)
        _resultado, contagem = chamar_ler_linha(
            cal, moldes, recortes, 8, tolerancia=tolerancia_de_ensaio()
        )
        assert contagem == {"2x": 0, "3x": 0}

    def test_o_motivo_do_cruzamento_e_DISTINGUIVEL_dos_outros(self) -> None:
        """D-17: o usuario tem de ler no log QUAL peneira pegou o que."""
        motivos = {
            MOTIVO_DA_OCLUSAO,
            MOTIVO_DA_GRAMATICA,
            MOTIVO_DA_FAIXA_CINZENTA,
            MOTIVO_DA_DISCORDANCIA,
            MOTIVO_DO_CRUZAMENTO,
        }
        assert len(motivos) == 5
        assert MOTIVO_DO_CRUZAMENTO != MOTIVO_DA_OCLUSAO
        assert MOTIVO_DO_CRUZAMENTO != MOTIVO_DA_GRAMATICA

    def test_o_descarte_nomeia_os_TRES_numeros_lidos(
        self, cal, moldes, janela_f010, caplog
    ) -> None:
        recortes = linha_com_o_total_adulterado(cal, janela_f010, 8)
        with caplog.at_level("WARNING", logger="l2scanner.mercado_leitura"):
            chamar_ler_linha(
                cal, moldes, recortes, 8, tolerancia=tolerancia_de_ensaio()
            )
        texto = caplog.text
        for numero in ("1880", "600", "3"):
            assert numero in texto


def observacoes_emitidas(caplog) -> list[str]:
    """So as linhas de OBSERVACAO do cruzamento, e nao qualquer prosa.

    Um `in` solto ("cruzamento" em qualquer lugar) casaria tambem no DESCARTE
    da rota aprovada, e o teste ficaria verde contando a mensagem errada.
    """
    return [
        r.getMessage()
        for r in caplog.records
        if "OBSERVACAO do cruzamento" in r.getMessage()
    ]


class TestATravaDaObservacaoDoCruzamento:
    """O segundo defeito de producao de 2026-09-01, escrito como teste.

    A pagina e relida a cada tick, entao a MESMA divergencia da MESMA oferta
    saia a 1 Hz — duas linhas por tick na sessao real, ~7.200 por hora, e o
    `scanner.log` rotativo perde a forense que ele existe para guardar. E o
    mesmo defeito que `TravaDoDestaque` consertou no destaque; passou
    despercebido porque e outra mensagem.
    """

    def test_a_PRIMEIRA_observacao_de_uma_oferta_SEMPRE_sai(
        self, cal, moldes, janela_f010, caplog
    ) -> None:
        """O teste de CONTROLE dos outros, e o que nao pode mudar.

        A guarda de cruzamento esta DESLIGADA por medicao e o residuo e
        OBSERVACAO: ele existe para o usuario ver que aquela leitura pode estar
        torta. Uma trava que engolisse a primeira apagaria informacao, e nao
        ruido — ficaria verde em "nao repete" tendo destruido a unica pista
        independente de leitura errada que esta fase tem.
        """
        from l2scanner.mercado_leitura import TravaDaObservacao

        recortes = linha_com_o_total_adulterado(cal, janela_f010, 8)
        with caplog.at_level("INFO", logger="l2scanner.mercado_leitura"):
            chamar_ler_linha(
                cal,
                moldes,
                recortes,
                8,
                tolerancia=None,
                trava=TravaDaObservacao(),
            )
        emitidas = observacoes_emitidas(caplog)
        assert len(emitidas) == 1
        for numero in ("1880", "600", "80"):
            assert numero in emitidas[0]

    def test_a_mesma_observacao_em_dois_ticks_seguidos_sai_UMA_vez(
        self, cal, moldes, janela_f010, caplog
    ) -> None:
        """O defeito de producao, no minimo que o reproduz.

        DOIS ticks bastam; a sessao real fez isto por milhares deles. A trava e
        a MESMA nos dois, porque na producao ela e do LEITOR e o leitor
        atravessa a sessao inteira.
        """
        from l2scanner.mercado_leitura import TravaDaObservacao

        trava = TravaDaObservacao()
        recortes = linha_com_o_total_adulterado(cal, janela_f010, 8)
        with caplog.at_level("INFO", logger="l2scanner.mercado_leitura"):
            for _tick in range(2):
                chamar_ler_linha(
                    cal, moldes, recortes, 8, tolerancia=None, trava=trava
                )
        assert len(observacoes_emitidas(caplog)) == 1

    def test_a_oferta_continua_travada_muitos_ticks_depois(
        self, cal, moldes, janela_f010, caplog
    ) -> None:
        """A trava e da SESSAO, e nao uma janela de tempo.

        Enquanto a oferta estiver no quadro ela sera relida a cada tick, e uma
        trava que expirasse so trocaria milhares de linhas repetidas por
        dezenas de linhas repetidas — continuaria sendo repeticao do mesmo
        fato.
        """
        from l2scanner.mercado_leitura import TravaDaObservacao

        trava = TravaDaObservacao()
        recortes = linha_com_o_total_adulterado(cal, janela_f010, 8)
        with caplog.at_level("INFO", logger="l2scanner.mercado_leitura"):
            for _tick in range(60):
                chamar_ler_linha(
                    cal, moldes, recortes, 8, tolerancia=None, trava=trava
                )
        assert len(observacoes_emitidas(caplog)) == 1

    def test_uma_oferta_DIFERENTE_sai_com_anuncio_PROPRIO(self) -> None:
        """A trava e por OFERTA, e a identidade e a aritmetica conferida.

        Duas divergencias diferentes sao duas noticias diferentes. Uma trava
        grossa demais — por linha da grade, por exemplo — engoliria a segunda
        so porque a primeira ja tinha aparecido.
        """
        from l2scanner.mercado_leitura import TravaDaObservacao

        trava = TravaDaObservacao()
        assert trava.anunciar(2, 1880, 600, 3, 80) is not None
        assert trava.anunciar(2, 67400, 600, 3, 4) is not None

    def test_a_MESMA_oferta_em_outra_LINHA_da_grade_continua_travada(
        self,
    ) -> None:
        """O indice da grade NAO entra na identidade, e isso e decisao.

        A oferta sobe e desce de linha quando o usuario rola o quadro. Se o
        indice travasse, uma rolagem de uma linha reanunciaria tudo — o defeito
        de volta, disfarcado de observacao nova.
        """
        from l2scanner.mercado_leitura import TravaDaObservacao

        trava = TravaDaObservacao()
        assert trava.anunciar(2, 1880, 600, 3, 80) is not None
        assert trava.anunciar(5, 1880, 600, 3, 80) is None

    def test_a_trava_devolve_TEXTO_e_nao_um_booleano(self) -> None:
        """A disciplina de `TravaDoDestaque`, seguida e nao reinventada.

        Devolver o texto e o que impede a trava de virar um portao que alguem
        esquece de fechar: quem chama nao TEM como anunciar sem passar por
        aqui, porque e daqui que sai a mensagem.

        `None` E NAO STRING VAZIA: uma string vazia atravessaria um `if texto:`
        distraido e imprimiria uma linha em branco por tick.
        """
        from l2scanner.mercado_leitura import TravaDaObservacao

        trava = TravaDaObservacao()
        primeiro = trava.anunciar(2, 1880, 600, 3, 80)
        assert isinstance(primeiro, str)
        assert "OBSERVACAO do cruzamento" in primeiro
        assert trava.anunciar(2, 1880, 600, 3, 80) is None

    def test_cada_SESSAO_comeca_com_a_trava_limpa(self) -> None:
        """Duas travas nao compartilham memoria.

        Uma trava de escopo de MODULO faria a segunda sessao sair muda sobre
        divergencias que o usuario nunca viu.
        """
        from l2scanner.mercado_leitura import TravaDaObservacao

        TravaDaObservacao().anunciar(2, 1880, 600, 3, 80)
        assert TravaDaObservacao().anunciar(2, 1880, 600, 3, 80) is not None

    def test_a_identidade_e_PUBLICA_e_e_a_da_ARITMETICA_conferida(
        self,
    ) -> None:
        """`(total, unitario, quantidade)` — os tres numeros do cruzamento.

        A serie NAO entra porque ela nao existe ainda: o nome e lido DEPOIS da
        guarda, no passo 5 do pipeline documentado em `ler_linha`, e de
        proposito (uma linha que a guarda derruba nunca deveria pagar OCR).
        `chave_da_observacao` e inalcancavel aqui por construcao, e nao por
        escolha.
        """
        from l2scanner.mercado_leitura import TravaDaObservacao

        trava = TravaDaObservacao()
        trava.anunciar(2, 1880, 600, 3, 80)
        assert (1880, 600, 3) in trava.ja_observadas


class TestOLeitorDePaginaCONSULTA_A_TRAVA:
    """A prova de FIACAO, e nao so da peca.

    Uma trava perfeita num modulo que o laco de linhas nao usa deixaria o
    defeito de producao exatamente onde ele estava.
    """

    def test_o_leitor_PASSA_A_SUA_trava_a_cada_ler_linha(
        self, cal, janela_f010, monkeypatch
    ) -> None:
        """O criterio afirma que a trava foi CHAMADA, e nao que ela existe.

        E a mesma trava em todos os ticks: uma construida por tick nasceria
        vazia toda vez e nao travaria nada — verde na unidade, inutil em
        producao.
        """
        import l2scanner.mercado_pagina as mercado_pagina

        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Earth Spirit Evolution Stone", "Earth Spirit Evolution Stone"
        )
        original = mercado_pagina.ler_linha
        vistas: list = []

        def espiao(*args, **kwargs):
            vistas.append(kwargs.get("trava_da_observacao"))
            return original(*args, **kwargs)

        monkeypatch.setattr(mercado_pagina, "ler_linha", espiao)
        leitor.observar(janela_f010)
        leitor.observar(janela_f010)

        assert vistas, "`ler_linha` nao foi chamada: o teste nao cobre nada"
        assert all(trava is leitor.trava_da_observacao for trava in vistas), (
            "o leitor deixou de passar a SUA trava a `ler_linha` - sem ela a "
            "mesma observacao reanuncia a cada tick"
        )

    def test_a_trava_e_construida_UMA_vez_por_LEITOR(self) -> None:
        """Dentro do laco de linhas ela nasceria vazia a cada linha."""
        import ast

        import l2scanner.mercado_pagina as mercado_pagina

        arvore = ast.parse(inspect.getsource(mercado_pagina))
        lacos = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, (ast.While, ast.For))
        ]
        construcoes_dentro_do_laco = [
            no
            for laco in lacos
            for no in ast.walk(laco)
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Name)
            and no.func.id == "TravaDaObservacao"
        ]
        assert construcoes_dentro_do_laco == []


class TestAFronteiraDaFase3:
    """O residuo e informacao da Fase 2 sobre a propria leitura."""

    def test_o_campo_existe_em_LinhaLida(self) -> None:
        assert "residuo_do_cruzamento" in LinhaLida.__dataclass_fields__

    def test_a_docstring_do_campo_diz_que_o_CSV_e_da_FASE_3(self) -> None:
        texto = LinhaLida.__doc__
        assert "Fase 3" in texto
        assert "CSV" in texto


# ---------------------------------------------------------------------------
# 02-08 — A GUARDA E A PARTICAO DO RUN LARGO
# ---------------------------------------------------------------------------
#
# O defeito: um run mais largo que o MAIOR molde de um caractere era casado
# contra UM molde e virava UM digito, com score e margem que atravessavam as
# duas peneiras. Falha ABERTA — numero errado e PLAUSIVEL — e nao a falha
# FECHADA que LEIT-02 exige.
#
# As tres fixturas COLADAS saem de `recordings/20260828-053105-mercado-aberto/`,
# uma das 8 gravacoes NOMEADAS do censo, recortadas pelo `dx`/`largura` da
# calibracao de producao:
#
#     glifos_colados_quantidade_f078.png  Quantity de frame_000078 LINHA 3
#         `44` num run de 12 px; hoje lia `4`
#     glifos_colados_total_f105.png       Total de frame_000105 LINHA 6
#         `149,44` com um run de 11 px; o corte `6+5` produz `144,44` e passa
#         nas duas peneiras, o corte certo `7+4` produz `149,44`
#     glifos_colados_total_f054.png       Total de frame_000054 LINHA 8
#         `44,00` num run de 12 px; hoje lia `4,00`

GLIFOS_COLADOS_QUANTIDADE = FIXTURES / "glifos_colados_quantidade_f078.png"
GLIFOS_COLADOS_TOTAL_F105 = FIXTURES / "glifos_colados_total_f105.png"
GLIFOS_COLADOS_TOTAL_F054 = FIXTURES / "glifos_colados_total_f054.png"
GLIFOS_DOS_PRECOS = FIXTURES / "glifos_precos_f010.png"


class TestAGeometriaDoGlifoEDerivada:
    """O limite vem dos MOLDES, e por isso ele nao vira chave do JSON."""

    def test_larguras_de_molde_ignora_os_moldes_de_PALAVRA(self, moldes) -> None:
        assert larguras_de_molde(moldes) == (1, 4, 6)

    def test_limite_de_glifo_unico_e_o_MAIOR_deles(self, moldes) -> None:
        assert limite_de_glifo_unico(moldes) == 6

    def test_sem_molde_de_um_caractere_nao_ha_limite(self) -> None:
        assert limite_de_glifo_unico({}) is None

    def test_larguras_com_folga_zero_e_a_largura_de_molde_pura(self) -> None:
        assert larguras_com_folga((1, 4, 6), 0) == (1, 4, 6)

    def test_larguras_com_folga_um_acrescenta_UMA_coluna(self) -> None:
        assert larguras_com_folga((1, 4, 6), 1) == (1, 2, 4, 5, 6, 7)

    def test_o_limite_NAO_e_uma_chave_do_calibration(self) -> None:
        """Uma copia gravada seria a SEGUNDA verdade sobre uma so geometria."""
        dados = json.loads(CALIBRACAO.read_text(encoding="utf-8"))
        assert not [chave for chave in dados if "largura_maxima" in chave]


class TestOsDoisParametrosNovosNaoTemValorDeFabrica:
    """Um default aqui e constante magica no caminho que decide PRECO."""

    def test_ler_glifos_exige_os_DOIS(self) -> None:
        parametros = inspect.signature(ler_glifos).parameters
        for nome in ("largura_maxima_de_glifo", "folga_de_cola"):
            assert parametros[nome].default is inspect.Parameter.empty, nome
            assert parametros[nome].kind is inspect.Parameter.KEYWORD_ONLY, nome

    def test_a_cadeia_inteira_exige_folga_de_cola(self) -> None:
        for funcao in (
            ler_celula,
            ler_celula_de_numero,
            ler_celula_de_quantidade,
            ler_linha,
        ):
            parametros = inspect.signature(funcao).parameters
            assert (
                parametros["folga_de_cola"].default is inspect.Parameter.empty
            ), funcao.__name__

    def test_o_LIMITE_nao_entra_na_assinatura_de_ler_celula(self) -> None:
        """Derivar onde os moldes estao e o que impede DUAS verdades."""
        assert (
            "largura_maxima_de_glifo"
            not in inspect.signature(ler_celula).parameters
        )

    def test_chamar_ler_glifos_sem_eles_levanta_TypeError(
        self, moldes, janela_f010, cal
    ) -> None:
        recorte = recorte_de_coluna(cal, janela_f010, 6, "mercado_coluna_do_total")
        faixa, runs = segmentar_glifos(recorte)
        mascara = (mascara_de_numero(recorte, VALOR_MINIMO_DO_TEXTO) * 255).astype(
            "uint8"
        )
        with pytest.raises(TypeError):
            ler_glifos(mascara, faixa, runs, moldes, 0.4, 0.03)


class TestAsAssinaturasDeSegmentacaoEstaoINTACTAS:
    """Os 35 pontos de chamada continuam recebendo os MESMOS runs."""

    def test_segmentar_glifos(self) -> None:
        assert list(inspect.signature(segmentar_glifos).parameters) == ["recorte"]

    def test_segmentar_glifos_no_brilho(self) -> None:
        assert list(
            inspect.signature(segmentar_glifos_no_brilho).parameters
        ) == ["recorte", "valor_minimo"]


class TestAsCelulasESTREITASNaoMudamUmPixel:
    """Quando todo run cabe no limite, o caminho novo E o caminho antigo.

    Preso por VALOR e nao por "nao levantou": um teste de "leu" passaria sobre
    um mecanismo que vazou para quem nao pediu.
    """

    def _bandas(self, caminho: Path, quantas: int):
        pixels = ler_fixtura(caminho)
        altura = pixels.shape[0] // quantas
        return [
            pixels[indice * altura : (indice + 1) * altura]
            for indice in range(quantas)
        ]

    def test_os_seis_precos_de_controle(self, cal, moldes) -> None:
        esperados = ["100,00", "3,00", "18,90", "7,50", "18,00", "2,45"]
        lidos = [
            ler_celula(
                banda,
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            for banda in self._bandas(GLIFOS_DOS_PRECOS, 6)
        ]
        assert lidos == esperados

    def test_o_unitario_de_controle(self, cal, moldes) -> None:
        assert (
            ler_celula(
                ler_fixtura(GLIFOS_DO_UNITARIO),
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            == "6,00"
        )

    def test_o_controle_le_IGUAL_com_a_guarda_pura(self, cal, moldes) -> None:
        """Sem run largo, a folga nao muda NADA — nem quando ela e `None`."""
        assert (
            ler_celula(
                ler_fixtura(GLIFOS_DO_UNITARIO),
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=None,
            )
            == "6,00"
        )

    def test_os_runs_de_controle_seguem_os_MESMOS(self) -> None:
        _faixa, runs = segmentar_glifos(ler_fixtura(GLIFOS_DO_UNITARIO))
        assert [fim - inicio for inicio, fim in runs] == [4, 1, 4, 4]


def _ler_colada(cal, moldes, caminho: Path, valor_minimo: int, folga):
    return ler_celula(
        ler_fixtura(caminho),
        moldes,
        float(cal.mercado_limiar_de_leitura_de_glifo),
        float(cal.mercado_margem_de_leitura_de_glifo),
        valor_minimo=valor_minimo,
        folga_de_cola=folga,
    )


class TestOsGlifosCOLADOS:
    """As tres fixturas presas por VALOR, e a guarda pura presa por `None`."""

    def test_o_44_da_quantidade_deixa_de_ler_4(self, cal, moldes) -> None:
        assert (
            _ler_colada(
                cal,
                moldes,
                GLIFOS_COLADOS_QUANTIDADE,
                int(cal.mercado_limiar_de_brilho_da_quantidade),
                cal.mercado_folga_de_cola_do_glifo,
            )
            == "44"
        )

    def test_o_run_de_ONZE_px_le_o_corte_de_SETE_mais_quatro(
        self, cal, moldes
    ) -> None:
        """O VALOR, e nao apenas "leu": o corte errado tambem passa na gramatica.

        `6+5` produziria `144,44`, que `numero_valido` aceita. Um teste de "leu"
        passaria sobre o bug. O rotulo independente da linha (unitario `2,99`,
        quantidade `50`) exige o total em [149,25; 150,00).
        """
        assert (
            _ler_colada(
                cal,
                moldes,
                GLIFOS_COLADOS_TOTAL_F105,
                VALOR_MINIMO_DO_TEXTO,
                cal.mercado_folga_de_cola_do_glifo,
            )
            == "149,44"
        )

    def test_o_44_virgula_00_do_total(self, cal, moldes) -> None:
        assert (
            _ler_colada(
                cal,
                moldes,
                GLIFOS_COLADOS_TOTAL_F054,
                VALOR_MINIMO_DO_TEXTO,
                cal.mercado_folga_de_cola_do_glifo,
            )
            == "44,00"
        )

    @pytest.mark.parametrize(
        "caminho,e_quantidade",
        [
            (GLIFOS_COLADOS_QUANTIDADE, True),
            (GLIFOS_COLADOS_TOTAL_F105, False),
            (GLIFOS_COLADOS_TOTAL_F054, False),
        ],
    )
    def test_a_GUARDA_pura_derruba_as_tres(
        self, cal, moldes, caminho, e_quantidade
    ) -> None:
        """Sem a chave medida, a celula cai FECHADA. Afirmado, nao suposto."""
        valor_minimo = (
            int(cal.mercado_limiar_de_brilho_da_quantidade)
            if e_quantidade
            else VALOR_MINIMO_DO_TEXTO
        )
        assert _ler_colada(cal, moldes, caminho, valor_minimo, None) is None

    def test_a_quantidade_colada_chega_INTEIRA_a_leitura_de_quantidade(
        self, cal, moldes
    ) -> None:
        assert (
            ler_celula_de_quantidade(
                ler_fixtura(GLIFOS_COLADOS_QUANTIDADE),
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                valor_minimo=int(cal.mercado_limiar_de_brilho_da_quantidade),
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            == 44
        )

    def test_o_total_colado_chega_INTEIRO_a_leitura_de_numero(
        self, cal, moldes
    ) -> None:
        assert (
            ler_celula_de_numero(
                ler_fixtura(GLIFOS_COLADOS_TOTAL_F105),
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=cal.mercado_folga_de_cola_do_glifo,
            )
            == 14944
        )


class TestAParticaoDeUmRun:
    """`particionar_run` devolve o melhor corte, ou `None`. Falha FECHADA."""

    def _material(self, caminho: Path, valor_minimo: int):
        pixels = ler_fixtura(caminho)
        faixa, runs = segmentar_glifos_no_brilho(pixels, valor_minimo)
        mascara = (mascara_de_numero(pixels, valor_minimo) * 255).astype("uint8")
        largos = [(a, b) for a, b in runs if b - a > 6]
        return mascara, faixa, largos[0]

    def test_devolve_a_lista_no_formato_de_pontuar_glifos(
        self, cal, moldes
    ) -> None:
        mascara, faixa, (a, b) = self._material(
            GLIFOS_COLADOS_TOTAL_F105, VALOR_MINIMO_DO_TEXTO
        )
        achado = particionar_run(
            mascara,
            faixa,
            a,
            b,
            moldes,
            float(cal.mercado_limiar_de_leitura_de_glifo),
            float(cal.mercado_margem_de_leitura_de_glifo),
            larguras_com_folga(larguras_de_molde(moldes), 1),
        )
        assert achado is not None
        assert [rotulo for rotulo, _s, _m in achado] == ["4", "9"]
        for _rotulo, score, distancia in achado:
            assert score >= float(cal.mercado_limiar_de_leitura_de_glifo)
            assert distancia >= float(cal.mercado_margem_de_leitura_de_glifo)

    def test_sem_largura_que_some_devolve_None(self, cal, moldes) -> None:
        mascara, faixa, (a, b) = self._material(
            GLIFOS_COLADOS_TOTAL_F105, VALOR_MINIMO_DO_TEXTO
        )
        assert (
            particionar_run(
                mascara,
                faixa,
                a,
                b,
                moldes,
                float(cal.mercado_limiar_de_leitura_de_glifo),
                float(cal.mercado_margem_de_leitura_de_glifo),
                (4,),
            )
            is None
        )

    def test_um_piso_impossivel_derruba_TODO_corte(self, cal, moldes) -> None:
        mascara, faixa, (a, b) = self._material(
            GLIFOS_COLADOS_TOTAL_F105, VALOR_MINIMO_DO_TEXTO
        )
        assert (
            particionar_run(
                mascara,
                faixa,
                a,
                b,
                moldes,
                1.01,
                0.0,
                larguras_com_folga(larguras_de_molde(moldes), 1),
            )
            is None
        )

    def test_a_docstring_registra_a_CAUSA_geometrica(self) -> None:
        texto = ler_glifos.__doc__ or ""
        assert "GEOMETRIA" in texto.upper()
        assert "piso de brilho" in texto


class TestAFerramentaIMPORTAAsPrimitivas:
    """Duas copias envelheceriam separadas — a seta aponta ferramenta -> puro."""

    def test_a_varredura_nao_REDEFINE_as_primitivas(self) -> None:
        fonte = (
            Path(__file__).resolve().parent.parent
            / "tools"
            / "medir_largura_de_run.py"
        ).read_text(encoding="utf-8")
        for nome in (
            "larguras_de_molde",
            "limite_de_glifo_unico",
            "larguras_com_folga",
            "particionar_run",
        ):
            assert f"def {nome}(" not in fonte, f"{nome} foi COPIADA"
