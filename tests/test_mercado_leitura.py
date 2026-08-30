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
trecho `dx 207..417` da grade, que fica na METADE ESQUERDA, e esta tooltip esta
na direita. Dispersao 0,0000 em todas as dez linhas.

Quem pega o buraco e a peneira seguinte, e e por isso que ela existe: os runs da
coluna coberta nao passam no piso, a celula cai inteira (tudo-ou-nada de
LEIT-02) e a linha vira `Descarte`. As linhas que atravessam de verdade neste
frame sao a 6 (`18,90` x 2) e a 8 (`18,00` x 3).
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.mercado_catalogo import EntradaDoCatalogo
from l2scanner.mercado_leitura import (
    MOTIVO_DA_DISCORDANCIA,
    MOTIVO_DA_FAIXA_CINZENTA,
    MOTIVO_DA_GRAMATICA,
    MOTIVO_DA_OCLUSAO,
    Descarte,
    LinhaLida,
    centesimos_de_moeda,
    inteiro_de_quantidade,
    ler_celula_de_numero,
    ler_celula_de_quantidade,
    ler_glifos,
    numero_valido,
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

# As duas linhas de `frame_000010` que atravessam o caminho INTEIRO. Medidas,
# nao supostas: as outras oito caem, e a docstring do modulo diz por que.
LINHAS_QUE_ATRAVESSAM_F010 = {6: (1890, 2), 8: (1800, 3)}

# As quatro linhas de `frame_000005` que atravessam. Este e o par de frames
# PARADOS (005 e 006 mostram a mesma pagina), e por isso e ele que prova o
# acordo entre dois frames.
LINHAS_QUE_ATRAVESSAM_F005 = {1: (3666, 3), 3: (1500, 3), 5: (1139, 6), 6: (500, 2)}


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
        self.chamadas = 0

    def __call__(self, pixels) -> str | None:
        self.chamadas += 1
        self._marcador.append(id(pixels) if pixels is not None else None)
        if callable(self._texto):
            return self._texto(pixels)
        return self._texto


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
            )
            == 2
        )

    def test_um_piso_impossivel_derruba_a_celula_inteira(
        self, cal, moldes, janela_f010
    ) -> None:
        recorte = recorte_de_coluna(cal, janela_f010, 6, "mercado_coluna_do_total")
        assert ler_celula_de_numero(recorte, moldes, 1.01, 0.0) is None

    def test_uma_margem_impossivel_derruba_a_celula_inteira(
        self, cal, moldes, janela_f010
    ) -> None:
        recorte = recorte_de_coluna(cal, janela_f010, 6, "mercado_coluna_do_total")
        assert ler_celula_de_numero(recorte, moldes, 0.0, 1.01) is None

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
        """Similaridade entre o piso e o corte: nao agrupa NEM cria serie."""
        catalogo = {
            "earth-spirit-evolution-stone#": EntradaDoCatalogo(
                chave="earth-spirit-evolution-stone#",
                nome="Earth Spirit Evolution Stone",
                assinatura="",
            )
        }
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal,
            "Fire Spirit Evolution Stone",
            "Fire Spirit Evolution Stone",
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

    def test_a_linha_sai_com_serie_nova_na_PRIMEIRA_vez(self, cal) -> None:
        catalogo: dict = {}
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll", catalogo=catalogo
        )
        leitor.observar(ler_fixtura(JANELA_F005))
        primeira = leitor.ultima_leitura.linhas[0]
        assert primeira.serie_nova is True
        assert primeira.chave_da_serie in catalogo
        leitor.observar(ler_fixtura(JANELA_F005_REPETIDA))
        segunda = leitor.ultima_leitura.linhas[0]
        assert segunda.serie_nova is False
        assert segunda.chave_da_serie == primeira.chave_da_serie

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


class TestOUnitarioNaoEntraNestePlano:
    """`ler_linha` sai desta onda lendo DUAS colunas de numero, nao tres."""

    def test_LinhaLida_nao_guarda_o_unitario_como_preco(self) -> None:
        campos = set(LinhaLida.__dataclass_fields__)
        assert "unitario" not in campos
        assert "unitario_em_centesimos" not in campos

    def test_a_docstring_explica_por_que_o_unitario_nao_e_dado(self) -> None:
        texto = LinhaLida.__doc__.lower()
        assert "arredond" in texto
        assert "02-06" in texto

    def test_a_coluna_do_unitario_NAO_e_recortada_nesta_onda(self) -> None:
        import l2scanner.mercado_pagina as pagina

        fonte = inspect.getsource(pagina)
        assert "mercado_coluna_do_unitario" not in fonte


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
