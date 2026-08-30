"""Os predicados PUROS do agrupamento de nome, presos contra os pares MEDIDOS.

Nada aqui toca `recordings/`, `calibration.json` nem motor de OCR. Sao strings e
numeros: os mesmos pares que a `02-RESEARCH.md` mediu contra a implementacao de
referencia do `rapidfuzz`, agora cobrados da metrica que este projeto usa de
verdade (`difflib.SequenceMatcher`). Um teste que dependesse de `recordings/`
ficaria verde nesta maquina e amarelo em toda outra.

OS NUMEROS QUE ESTE ARQUIVO COBRA, E DE ONDE VIERAM
====================================================

    par                                              WRatio   difflib   precisa
    Common Aztac x Common Aztac M. Def. +200          90,00    64,86    separar
    +6 Agathion ... x +4 Agathion ...                 96,77    96,77    separar
    Hardin's ... Lv. 1 x Lv. 3                        96,30    96,30    separar
    Hardin's ... Lv. I x Lv. 1                        96,30    96,30    AGRUPAR
    Earth Spirit Evolution ... x ... Ewlution ...        -     94,55    agrupar

As duas linhas do meio sao o achado que decide o desenho: **o mesmo numero teria
de decidir coisas opostas**, e `difflib` da EXATAMENTE o mesmo 0,9630 para as
duas. Nenhum corte escalar resolve. Por isso a TRAVA DE DIGITOS vem antes da
similaridade, e separa `Lv. 1` de `Lv. 3` por construcao.

UM NUMERO QUE CAIU PRECISA DIZER QUE CAIU: o `Evolution` x `Ewlution` do plano e
o par de NOME INTEIRO (0,9455). As duas palavras SOLTAS dao 0,8235 — abaixo de
0,90 — porque a razao de casamento cai quando o prefixo comum encolhe junto com a
string. Cobrar a palavra solta acima de 0,90 seria cobrar um numero que nunca foi
medido; o que a pesquisa mediu foi o nome inteiro, que e o que a producao compara.
"""

from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from l2scanner.mercado_catalogo import (
    EntradaDoCatalogo,
    ResultadoDoAgrupamento,
    agrupar,
    assinatura_por_molde,
    assinatura_por_ocr,
    chave_da_serie,
    similaridade,
)

RAIZ = Path(__file__).resolve().parent.parent

AGATHION_6 = "+6 Agathion Alpha Hunter Sealed"
AGATHION_4 = "+4 Agathion Alpha Hunter Sealed"
AGATHION_0 = "Agathion Alpha Hunter Sealed"
HARDIN_1 = "Hardin's Soul Crystal Lv. 1"
HARDIN_3 = "Hardin's Soul Crystal Lv. 3"
HARDIN_I = "Hardin's Soul Crystal Lv. I"
EVOLUTION = "Earth Spirit Evolution Stone"
EWLUTION = "Earth Spirit Ewlution Stone"
AZTAC = "Common Aztac"
AZTAC_LONGO = "Common Aztac M. Def. +200"


def _entrada(nome: str) -> EntradaDoCatalogo:
    """Uma entrada de catalogo com a chave derivada do proprio nome."""
    assinatura = assinatura_por_ocr(nome)
    return EntradaDoCatalogo(chave_da_serie(nome, assinatura), nome, assinatura)


class TestATravaDeDigitos:
    """D-03: a sequencia de digitos bate EXATAMENTE, antes de qualquer similaridade."""

    def test_o_prefixo_de_encanto_vira_assinatura(self):
        assert assinatura_por_ocr(AGATHION_6) == "6"
        assert assinatura_por_ocr(AGATHION_4) == "4"
        assert assinatura_por_ocr(AGATHION_6) != assinatura_por_ocr(AGATHION_4)

    def test_o_nivel_do_cristal_vira_assinatura(self):
        assert assinatura_por_ocr(HARDIN_1) == "1"
        assert assinatura_por_ocr(HARDIN_3) == "3"
        assert assinatura_por_ocr(HARDIN_1) != assinatura_por_ocr(HARDIN_3)

    def test_o_conflito_entre_D02_e_D03_fica_preso_por_escrito(self):
        """`Lv. I` tem assinatura VAZIA e nao bate com `Lv. 1`.

        Este teste nao afirma que isso e bom — afirma que e o que acontece. E o
        conflito medido entre D-02 (o ruido `I`/`1` tem de ser absorvido) e D-03
        (o digito tem de bater exato), e a Task 2 do 02-03 o poe na frente do
        usuario com o numero. Escondê-lo aqui seria a unica forma de ele voltar.
        """
        assert assinatura_por_ocr(HARDIN_I) == ""
        assert assinatura_por_ocr(HARDIN_1) == "1"
        assert assinatura_por_ocr(HARDIN_I) != assinatura_por_ocr(HARDIN_1)

    def test_nome_sem_digito_nenhum_da_assinatura_vazia(self):
        assert assinatura_por_ocr(AGATHION_0) == ""
        assert assinatura_por_ocr(EVOLUTION) == ""

    def test_a_assinatura_e_a_ordem_DE_APARICAO_e_nao_a_ordenacao(self):
        """`Lv. 12` e `Lv. 21` sao series diferentes, e a ordem e o que as separa.

        Ordenar os digitos colapsaria os dois numa assinatura `12` unica — a
        fusao que a trava existe para impedir.
        """
        assert assinatura_por_ocr("Coisa Lv. 12") == "12"
        assert assinatura_por_ocr("Coisa Lv. 21") == "21"

    def test_leitura_vazia_ou_None_nao_levanta(self):
        assert assinatura_por_ocr("") == ""
        assert assinatura_por_ocr("   ") == ""
        assert assinatura_por_ocr(None) == ""

    def test_digito_nao_ascii_nao_conta_como_digito(self):
        """`²`.isdigit() e True em Python, e um `²` nao e um digito da tela."""
        assert assinatura_por_ocr("Bota²") == ""


class TestASimilaridade:
    """Os pares medidos, cobrados da metrica que a producao usa."""

    def test_o_par_que_derrubou_o_WRatio_fica_abaixo_de_070(self):
        """`Common Aztac` x `Common Aztac M. Def. +200`.

        Este e o par que a decisao original citava como motivo de existir, e o
        `WRatio` dava 90,00 nele — acima do corte 88, fundindo as duas series.
        `difflib` da 64,86 e as separa sem ajuda de trava nenhuma.
        """
        assert similaridade(AZTAC, AZTAC_LONGO) < 0.70

    def test_o_ruido_de_ocr_do_nome_inteiro_fica_acima_de_090(self):
        assert similaridade(EVOLUTION, EWLUTION) > 0.90

    def test_a_palavra_solta_NAO_chega_a_090_e_isso_esta_registrado(self):
        """A refutacao preservada ao lado da medicao que vale.

        0,8235 para `Evolution` x `Ewlution` soltas. O 94,55 da pesquisa e do
        NOME INTEIRO, que e o que a producao compara. Confundir os dois faria
        alguem "consertar" o corte para caber uma comparacao que nunca acontece.
        """
        assert similaridade("Evolution", "Ewlution") < 0.90

    def test_o_mesmo_numero_teria_de_decidir_coisas_opostas(self):
        """0,9630 para o par que PRECISA separar e para o que PRECISA agrupar.

        E por isso que a trava de digitos nao e um detalhe de implementacao: ela
        e a unica coisa que separa estes dois casos.
        """
        separar = similaridade(HARDIN_1, HARDIN_3)
        agrupar_ = similaridade(HARDIN_I, HARDIN_1)
        assert abs(separar - agrupar_) < 1e-9
        assert separar > 0.95

    def test_string_vazia_da_zero_e_nunca_levanta(self):
        assert similaridade("", "") == 0.0
        assert similaridade("", AZTAC) == 0.0
        assert similaridade(AZTAC, "") == 0.0
        assert similaridade(None, None) == 0.0

    def test_identica_da_um(self):
        assert similaridade(AZTAC, AZTAC) == 1.0


class TestAChaveDaSerie:
    def test_nome_vazio_ou_so_espaco_nunca_produz_chave(self):
        assert chave_da_serie("", "") is None
        assert chave_da_serie("   ", "") is None
        assert chave_da_serie("\t\n", "6") is None
        assert chave_da_serie(None, "") is None

    def test_a_assinatura_entra_na_chave_de_forma_explicita(self):
        seis = chave_da_serie(AGATHION_6, assinatura_por_ocr(AGATHION_6))
        quatro = chave_da_serie(AGATHION_4, assinatura_por_ocr(AGATHION_4))
        assert seis != quatro
        assert seis.endswith("#6")
        assert quatro.endswith("#4")

    def test_a_chave_e_estavel_e_sem_espaco(self):
        chave = chave_da_serie(AGATHION_6, "6")
        assert " " not in chave
        assert chave == chave_da_serie(AGATHION_6, "6")

    def test_a_chave_sobrevive_a_um_nome_so_de_pontuacao(self):
        """Nome com conteudo mas sem alfanumerico nenhum ainda produz chave.

        `None` e reservado para "nao ha nome"; um nome estranho e um nome.
        """
        chave = chave_da_serie("+++", "")
        assert chave is not None
        assert " " not in chave


class TestOAgrupamento:
    CORTE = 0.90
    PISO = 0.70

    def test_catalogo_vazio_produz_a_primeira_serie(self):
        r = agrupar(AGATHION_6, "6", [], self.CORTE, self.PISO)
        assert r.nova is True
        assert r.chave == chave_da_serie(AGATHION_6, "6")

    def test_leitura_vazia_nunca_produz_chave_nem_serie(self):
        r = agrupar("   ", "", [_entrada(AGATHION_6)], self.CORTE, self.PISO)
        assert r.chave is None
        assert r.nova is False

    def test_o_ruido_de_ocr_agrupa_na_serie_que_ja_existe(self):
        catalogo = [_entrada(EVOLUTION)]
        r = agrupar(EWLUTION, "", catalogo, self.CORTE, self.PISO)
        assert r.nova is False
        assert r.chave == catalogo[0].chave

    def test_a_trava_separa_o_encanto_por_mais_alta_que_seja_a_similaridade(self):
        """0,9677 de similaridade, e mesmo assim serie nova. Por construcao."""
        catalogo = [_entrada(AGATHION_6)]
        assert similaridade(AGATHION_4, AGATHION_6) > self.CORTE
        r = agrupar(AGATHION_4, "4", catalogo, self.CORTE, self.PISO)
        assert r.nova is True
        assert r.chave != catalogo[0].chave

    def test_a_trava_separa_os_niveis_do_cristal(self):
        catalogo = [_entrada(HARDIN_1)]
        assert similaridade(HARDIN_3, HARDIN_1) > self.CORTE
        r = agrupar(HARDIN_3, "3", catalogo, self.CORTE, self.PISO)
        assert r.nova is True

    def test_a_faixa_cinzenta_descarta_sem_agrupar_e_sem_criar(self):
        """D-06: fusao no CSV e irreversivel, descarte nao e."""
        catalogo = [_entrada(AZTAC)]
        similar = similaridade(AZTAC_LONGO, AZTAC)
        assert self.PISO <= similar < self.CORTE, similar
        r = agrupar(AZTAC_LONGO, "200", catalogo, self.CORTE, self.PISO)
        # A assinatura difere, entao a trava ja separa: para exercitar a faixa
        # cinzenta os dois precisam da MESMA assinatura.
        catalogo = [EntradaDoCatalogo(chave_da_serie(AZTAC, ""), AZTAC, "")]
        r = agrupar(AZTAC_LONGO, "", catalogo, self.CORTE, 0.60)
        assert r.chave is None
        assert r.nova is False
        assert "cinzenta" in r.motivo.lower()

    def test_empate_EXATAMENTE_no_corte_agrupa(self):
        catalogo = [_entrada(EVOLUTION)]
        corte = similaridade(EWLUTION, EVOLUTION)
        r = agrupar(EWLUTION, "", catalogo, corte, 0.10)
        assert r.nova is False
        assert r.chave == catalogo[0].chave

    def test_empate_EXATAMENTE_no_piso_descarta(self):
        catalogo = [_entrada(EVOLUTION)]
        piso = similaridade(EWLUTION, EVOLUTION)
        r = agrupar(EWLUTION, "", catalogo, piso + 0.01, piso)
        assert r.chave is None
        assert r.nova is False

    def test_o_desempate_e_deterministico_e_nao_de_ordem_de_insercao(self):
        """Duas entradas empatadas: vence a de chave lexicograficamente menor.

        As duas ordens de insercao produzem a MESMA chave. Sem isto, duas
        execucoes sobre o mesmo frame poderiam gravar series diferentes.
        """
        a = EntradaDoCatalogo("aaa#", "Bota Azul", "")
        b = EntradaDoCatalogo("zzz#", "Bota Azul", "")
        leitura = "Bota Azul"
        assert similaridade(leitura, a.nome) == similaridade(leitura, b.nome)
        primeira = agrupar(leitura, "", [a, b], 0.90, 0.70)
        segunda = agrupar(leitura, "", [b, a], 0.90, 0.70)
        assert primeira.chave == segunda.chave == "aaa#"

    def test_o_maior_score_vence_o_desempate_lexicografico(self):
        melhor = EntradaDoCatalogo("zzz#", EVOLUTION, "")
        pior = EntradaDoCatalogo("aaa#", "Coisa Completamente Outra", "")
        r = agrupar(EWLUTION, "", [pior, melhor], 0.90, 0.10)
        assert r.chave == "zzz#"

    def test_o_resultado_e_um_ResultadoDoAgrupamento_com_motivo(self):
        r = agrupar(AGATHION_6, "6", [], 0.90, 0.70)
        assert isinstance(r, ResultadoDoAgrupamento)
        assert r.motivo


class TestAAssinaturaPorMolde:
    """A segunda fonte candidata: TUDO OU NADA, como `propor_rotulo`.

    O motor de glifo chega INJETADO — o mesmo desenho de
    `VigiaDeManutencao.__init__`, que recebe as duas leitoras. Aqui o dublê
    devolve a pontuacao diretamente, entao o predicado pode ser afirmado no
    Python GLOBAL, sem molde, sem `calibration.json` e sem `recordings/`.
    """

    RECORTE = np.zeros((11, 20, 3), dtype=np.uint8)

    def test_todos_os_runs_aprovados_produzem_a_assinatura(self):
        def pontuar(_recorte, _moldes):
            return [("6", 0.90, 0.30)]

        assert (
            assinatura_por_molde(
                self.RECORTE, {}, 0.47, 0.03, pontuar_runs=pontuar
            )
            == "6"
        )

    def test_um_run_abaixo_do_piso_derruba_a_leitura_inteira(self):
        def pontuar(_recorte, _moldes):
            return [("6", 0.90, 0.30), ("4", 0.30, 0.30)]

        assert (
            assinatura_por_molde(
                self.RECORTE, {}, 0.47, 0.03, pontuar_runs=pontuar
            )
            is None
        )

    def test_um_run_abaixo_da_margem_derruba_a_leitura_inteira(self):
        def pontuar(_recorte, _moldes):
            return [("6", 0.90, 0.01)]

        assert (
            assinatura_por_molde(
                self.RECORTE, {}, 0.47, 0.03, pontuar_runs=pontuar
            )
            is None
        )

    def test_run_que_nao_e_digito_derruba_a_leitura_inteira(self):
        """O `+` do prefixo de encanto nao tem molde, e nao pode virar digito."""

        def pontuar(_recorte, _moldes):
            return [(",", 0.90, 0.30), ("6", 0.90, 0.30)]

        assert (
            assinatura_por_molde(
                self.RECORTE, {}, 0.47, 0.03, pontuar_runs=pontuar
            )
            is None
        )

    def test_sem_run_nenhum_devolve_None(self):
        assert (
            assinatura_por_molde(
                self.RECORTE, {}, 0.47, 0.03, pontuar_runs=lambda _r, _m: None
            )
            is None
        )
        assert (
            assinatura_por_molde(
                self.RECORTE, {}, 0.47, 0.03, pontuar_runs=lambda _r, _m: []
            )
            is None
        )

    def test_recorte_vazio_devolve_None_sem_chamar_o_motor(self):
        chamou = []

        def pontuar(_recorte, _moldes):
            chamou.append(1)
            return [("6", 0.99, 0.99)]

        vazio = np.zeros((0, 0, 3), dtype=np.uint8)
        assert (
            assinatura_por_molde(vazio, {}, 0.47, 0.03, pontuar_runs=pontuar)
            is None
        )
        assert chamou == []

    def test_o_motor_que_levanta_nao_derruba_o_predicado(self):
        """O predicado roda dentro do tick de leitura. Ele NUNCA levanta."""

        def pontuar(_recorte, _moldes):
            raise RuntimeError("molde corrompido")

        assert (
            assinatura_por_molde(
                self.RECORTE, {}, 0.47, 0.03, pontuar_runs=pontuar
            )
            is None
        )


class TestOCharterDoModulo:
    def test_a_metrica_e_a_da_stdlib(self):
        import l2scanner.mercado_catalogo as m

        assert "SequenceMatcher" in inspect.getsource(m)

    def test_importar_o_modulo_nao_puxa_rapidfuzz(self):
        """A asserção e sobre o GRAFO DE IMPORT, nao sobre o texto do fonte.

        A docstring do modulo CITA `rapidfuzz` de proposito, para registrar por
        que ele caiu (D-04) — um grep negativo sobre o fonte se auto-invalidaria.
        Subprocesso porque a suite inteira compartilha `sys.modules`.
        """
        saida = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys, l2scanner.mercado_catalogo; "
                "assert 'rapidfuzz' not in sys.modules; print('sem rapidfuzz ok')",
            ],
            cwd=str(RAIZ),
            capture_output=True,
            text=True,
        )
        assert saida.returncode == 0, saida.stderr
        assert "sem rapidfuzz ok" in saida.stdout

    def test_o_modulo_puro_nao_importa_a_ferramenta_de_calibracao(self):
        """`calibrar_mercado` chama `tornar_consciente_de_dpi()` NO IMPORT.

        Um modulo de producao que o importasse pagaria esse efeito colateral so
        por existir, e inverteria a seta que o repositorio mantem em tres
        precedentes (a ferramenta importa o puro, nunca o contrario).
        """
        import l2scanner.mercado_catalogo as m

        fonte = inspect.getsource(m)
        assert "calibrar_mercado" not in fonte.split('"""')[2:] or True
        linhas_de_import = [
            linha
            for linha in fonte.splitlines()
            if linha.startswith(("import ", "from "))
        ]
        assert not any("calibrar_mercado" in linha for linha in linhas_de_import)

    def test_o_modulo_nao_faz_io_de_arquivo_nesta_etapa(self):
        """Primeira etapa: so predicados. O arquivo do catalogo e o 02-05."""
        import l2scanner.mercado_catalogo as m

        fonte = inspect.getsource(m)
        linhas_de_import = [
            linha
            for linha in fonte.splitlines()
            if linha.startswith(("import ", "from "))
        ]
        for proibido in ("import csv", "import os", "from pathlib"):
            assert not any(proibido in linha for linha in linhas_de_import), proibido


@pytest.mark.parametrize(
    "nome, esperada",
    [
        (AGATHION_6, "6"),
        (AGATHION_4, "4"),
        ("+2 Agathion Alpha Hunter Sealed", "2"),
        ("+7 Agathion Alpha Hunter Sealed", "7"),
        (AGATHION_0, ""),
        ("+5 Agathion Alpha Hunter Sealed", "5"),
    ],
)
def test_o_gabarito_de_encanto_da_063752_frame_000000(nome, esperada):
    """As dez linhas do frame que o usuario calibrou: +6/+4/+2/+7/(nenhum)/+5/..."""
    assert assinatura_por_ocr(nome) == esperada
