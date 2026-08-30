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
    ler_linha,
    linha_ocluida,
    linha_vazia,
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
        """Similaridade entre o piso e o corte: nao agrupa NEM cria serie.

        O par e MEDIDO com a mesma `difflib` da producao: `Earth Spirit
        Evolution Stone` x `Water Spirit Evolution Stone` da 0,892857, que cai
        dentro de [0,883732 ; 0,894737).
        """
        catalogo = {
            "earth-spirit-evolution-stone#": EntradaDoCatalogo(
                chave="earth-spirit-evolution-stone#",
                nome="Earth Spirit Evolution Stone",
                assinatura="",
            )
        }
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal,
            "Water Spirit Evolution Stone",
            "Water Spirit Evolution Stone",
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

# As oito primeiras linhas de `tooltip/frame_000012` estao COBERTAS e as duas
# ultimas nao. Medido com a sonda calibrada; e o mesmo frame que D-15 descreve.
COBERTAS_NO_TOOLTIP = (0, 1, 2, 3, 4, 5, 6, 7)
DESCOBERTAS_NO_TOOLTIP = (8, 9)


def em_cinza(caminho: Path) -> np.ndarray:
    return cv2.cvtColor(ler_fixtura(caminho), cv2.COLOR_BGR2GRAY)


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
    ):
        coluna = getattr(cal, chave)
        x = ox + int(coluna["dx"])
        saida[nome] = janela[topo : topo + altura, x : x + int(coluna["largura"])]
    return saida


def chamar_ler_linha(cal, moldes, recortes: dict, indice: int, catalogo=None):
    """`ler_linha` direto, com as duas leitoras CONTADORAS."""
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
        moldes=moldes,
        piso=float(cal.mercado_limiar_de_leitura_de_glifo),
        margem=float(cal.mercado_margem_de_leitura_de_glifo),
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

        A razao de elas nao atravessarem esta medida e registrada na docstring de
        `ler_celula_de_quantidade`: a quantidade destas duas linhas e `1`, e o
        tronco do `1` da coluna Quantity e desenhado a V = 177, abaixo do piso
        180 de `mascara_de_texto`. A falha e FECHADA, que e o comportamento
        certo, e o conserto e um piso de brilho proprio da coluna, MEDIDO.
        """
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        leitor.observar(ler_fixtura(JANELA_TOOLTIP))
        leitura = leitor.ultima_leitura
        por_indice = dict(zip(leitura.descartadas, leitura.motivos))
        for indice in DESCOBERTAS_NO_TOOLTIP:
            assert por_indice[indice] != MOTIVO_DA_OCLUSAO
        assert set(leitura.motivos) == {MOTIVO_DA_OCLUSAO, MOTIVO_DA_GRAMATICA}

    def test_a_pagina_com_tooltip_nao_para_no_primeiro_descarte(self, cal) -> None:
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        leitor.observar(ler_fixtura(JANELA_TOOLTIP))
        assert len(leitor.ultima_leitura.descartadas) == int(
            cal.mercado_grade["linhas_por_pagina"]
        )

    def test_a_linha_descartada_NAO_entra_no_estabilizador(self, cal) -> None:
        """Duas paginas so de descarte nunca viram `PaginaAceita`."""
        leitor, _b, _c, _v2, _v3 = montar_leitor(
            cal, "Common Fafurion Doll", "Common Fafurion Doll"
        )
        assert leitor.observar(ler_fixtura(JANELA_TOOLTIP)) is None
        assert leitor.observar(ler_fixtura(JANELA_TOOLTIP)) is None


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
        assert leitura.descartadas == (0,)

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
        assert len(recusas) == 20
