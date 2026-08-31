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
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from l2scanner.mercado_catalogo import (
    ARQUIVO_DO_CATALOGO,
    COLUNAS,
    SEPARADOR,
    Catalogo,
    EntradaDoCatalogo,
    ResultadoDoAgrupamento,
    SerieDeNome,
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
        """D-06: fusao no CSV e irreversivel, descarte nao e.

        Os dois nomes entram com a MESMA assinatura de proposito — com
        assinaturas diferentes a trava de digitos ja separaria e a faixa
        cinzenta nunca seria exercitada. O piso 0,60 e escolhido para colocar o
        0,6486 medido do par DENTRO da faixa.
        """
        catalogo = [EntradaDoCatalogo(chave_da_serie(AZTAC, ""), AZTAC, "")]
        similar = similaridade(AZTAC_LONGO, AZTAC)
        assert 0.60 <= similar < self.CORTE, similar
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
        linhas_de_import = [
            linha
            for linha in fonte.splitlines()
            if linha.startswith(("import ", "from "))
        ]
        assert not any("calibrar_mercado" in linha for linha in linhas_de_import)

    def test_o_modulo_AGORA_faz_io_e_isso_e_a_METADE_DE_ARQUIVO_do_02_05(self):
        """UM NUMERO QUE CAIU PRECISA DIZER QUE CAIU — e um teste tambem.

        Ate o 02-04 este arquivo cobrava o OPOSTO: que o modulo nao importasse
        `csv`, `os` nem `pathlib`, porque a primeira etapa era so de predicados
        e o arquivo do catalogo estava marcado para o 02-05. O 02-05 chegou. O
        teste antigo nao foi apagado em silencio: ele foi INVERTIDO, com a razao
        aqui, para que ninguem leia o import novo como regressao.

        As tres dependencias sao exatamente as que a metade de arquivo exige, e
        nenhuma a mais: `csv` (o dialeto que cita e escapa), `os` (o
        `os.replace` atomico) e `pathlib` (o caminho derivado da RAIZ).
        """
        import l2scanner.mercado_catalogo as m

        fonte = inspect.getsource(m)
        linhas_de_import = [
            linha
            for linha in fonte.splitlines()
            if linha.startswith(("import ", "from "))
        ]
        for exigido in ("import csv", "import os", "from pathlib"):
            assert any(exigido in linha for linha in linhas_de_import), exigido

    def test_o_modulo_NAO_conhece_o_arquivo_de_observacoes_da_FASE_3(self):
        """A fronteira, cobrada por inspecao: dois arquivos, dois donos.

        A Fase 2 escreve o catalogo de NOMES. O CSV de OBSERVACOES e da Fase 3.
        Se este modulo passar a nomear o arquivo da fase seguinte, a fronteira
        virou porosa — e o modo de falha nao e um erro, e um segundo escritor
        para um arquivo que tem dono.
        """
        import l2scanner.mercado_catalogo as m

        fonte = inspect.getsource(m).lower()
        for proibido in ("observacoes.csv", "observacao.csv", "observacoes-de-"):
            assert proibido not in fonte, proibido

    def test_o_gitignore_tem_a_linha_do_mercado_UMA_vez(self):
        """`.mercado/` e estado local e duravel, igual a `.loot/` e `.agenda/`.

        Versionar misturaria a estatistica de maquinas diferentes — a mesma
        prosa que o `.gitignore` ja escreve para as outras duas pastas-ponto.
        """
        linhas = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
        assert [linha for linha in linhas if linha.strip() == ".mercado/"] == [
            ".mercado/"
        ]

    def test_a_escrita_do_catalogo_e_ATOMICA(self):
        """`os.replace` no fonte — o precedente de `loot.py:264-281`."""
        import l2scanner.mercado_catalogo as m

        assert "os.replace" in inspect.getsource(m)


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


# ===========================================================================
# A METADE DE ARQUIVO (02-05): o catalogo duravel em `.mercado/`
# ===========================================================================
#
# Nada aqui toca a `.mercado/` REAL. Toda instancia recebe `tmp_path`, pelo
# mesmo motivo de `RegistroDeLoot` receber a pasta no construtor em vez de
# derivar uma: um teste que escrevesse na pasta de producao contaminaria a
# estatistica do usuario, que e dado ACUMULADO e sem poda — nao ha desfazer.

AGORA = datetime(2026, 8, 30, 21, 15, 0)
DEPOIS = datetime(2026, 8, 31, 9, 0, 0)


def _chave(nome: str) -> str:
    return chave_da_serie(nome, assinatura_por_ocr(nome))


def _linhas_cruas(pasta: Path) -> list[str]:
    return (pasta / ARQUIVO_DO_CATALOGO).read_text(encoding="utf-8").splitlines()


class TestOArquivoNasceEMorreBem:
    """Arranque numa maquina limpa, e a pasta que o construtor possui."""

    def test_catalogo_inexistente_carrega_VAZIO_e_nao_levanta(self, tmp_path):
        """A primeira execucao numa maquina limpa e um estado LEGITIMO."""
        catalogo = Catalogo(tmp_path / ".mercado")
        assert catalogo.series == {}

    def test_o_construtor_POSSUI_a_pasta(self, tmp_path):
        """Igual a `RegistroDeLoot.__init__` — a pasta nasce com o objeto."""
        pasta = tmp_path / ".mercado"
        assert not pasta.exists()
        Catalogo(pasta)
        assert pasta.is_dir()

    def test_gravar_sem_serie_nenhuma_produz_arquivo_com_CABECALHO(self, tmp_path):
        """O arquivo e legivel a olho nu: a primeira linha nomeia as colunas."""
        catalogo = Catalogo(tmp_path / ".mercado")
        catalogo.gravar()
        assert _linhas_cruas(tmp_path / ".mercado")[0] == SEPARADOR.join(COLUNAS)

    def test_o_separador_e_PONTO_E_VIRGULA_e_nao_virgula(self, tmp_path):
        """A exibicao usa virgula DECIMAL (`62,00`).

        Um CSV separado por virgula colapsaria a planilha inteira numa coluna
        assim que a Fase 3 herdasse este dialeto — e ela herda, de proposito.
        """
        assert SEPARADOR == ";"
        catalogo = Catalogo(tmp_path / ".mercado")
        catalogo.registrar(_chave(AGATHION_6), AGATHION_6, AGORA)
        catalogo.gravar()
        assert _linhas_cruas(tmp_path / ".mercado")[1].count(";") >= 4


class TestOAvistamentoDeUmNome:
    """Nome novo entra DIRETO como serie nova, sem quarentena (D-08)."""

    def test_o_primeiro_nome_vira_serie_com_UM_avistamento(self, tmp_path):
        catalogo = Catalogo(tmp_path / ".mercado")
        serie = catalogo.registrar(_chave(AGATHION_6), AGATHION_6, AGORA)
        assert isinstance(serie, SerieDeNome)
        assert serie.avistamentos == 1
        assert serie.primeira_vez == AGORA
        assert serie.ultima_vez == AGORA
        assert serie.nome_exibido == AGATHION_6

    def test_o_mesmo_nome_de_novo_SOBE_a_contagem_sem_criar_serie(self, tmp_path):
        catalogo = Catalogo(tmp_path / ".mercado")
        chave = _chave(AGATHION_6)
        catalogo.registrar(chave, AGATHION_6, AGORA)
        serie = catalogo.registrar(chave, AGATHION_6, DEPOIS)
        assert len(catalogo.series) == 1
        assert serie.avistamentos == 2

    def test_a_PRIMEIRA_vez_nunca_se_mexe_e_a_ULTIMA_sempre(self, tmp_path):
        """A data da primeira aparicao e o evento que o usuario quer ver."""
        catalogo = Catalogo(tmp_path / ".mercado")
        chave = _chave(AGATHION_6)
        catalogo.registrar(chave, AGATHION_6, AGORA)
        serie = catalogo.registrar(chave, AGATHION_6, DEPOIS)
        assert serie.primeira_vez == AGORA
        assert serie.ultima_vez == DEPOIS

    def test_um_relogio_que_ANDOU_PARA_TRAS_nao_reescreve_a_primeira_vez(
        self, tmp_path
    ):
        """Horario de verao e ajuste de NTP andam para tras de verdade.

        A primeira vez e MIN e a ultima e MAX, e nao "a ultima que chegou": um
        tick com relogio atrasado nao pode fazer a serie parecer mais nova nem
        mais velha do que o material prova.
        """
        catalogo = Catalogo(tmp_path / ".mercado")
        chave = _chave(AGATHION_6)
        catalogo.registrar(chave, AGATHION_6, DEPOIS)
        serie = catalogo.registrar(chave, AGATHION_6, AGORA)
        assert serie.primeira_vez == AGORA
        assert serie.ultima_vez == DEPOIS

    def test_duas_chaves_diferentes_sao_duas_series(self, tmp_path):
        catalogo = Catalogo(tmp_path / ".mercado")
        catalogo.registrar(_chave(AGATHION_6), AGATHION_6, AGORA)
        catalogo.registrar(_chave(AGATHION_4), AGATHION_4, AGORA)
        assert len(catalogo.series) == 2

    def test_chave_VAZIA_ou_None_nao_cria_serie_nenhuma(self, tmp_path):
        """`chave_da_serie` devolve `None` para leitura vazia (ja preso acima).

        Uma chave vazia que virasse linha do CSV seria referenciada pela Fase 3
        como se fosse item.
        """
        catalogo = Catalogo(tmp_path / ".mercado")
        assert catalogo.registrar(None, "", AGORA) is None
        assert catalogo.registrar("", "", AGORA) is None
        assert catalogo.series == {}


class TestAIdaEVolta:
    """Gravar e recarregar devolve as MESMAS series."""

    def test_o_roundtrip_preserva_chave_nome_datas_e_contagem(self, tmp_path):
        pasta = tmp_path / ".mercado"
        catalogo = Catalogo(pasta)
        chave = _chave(AGATHION_6)
        catalogo.registrar(chave, AGATHION_6, AGORA)
        catalogo.registrar(chave, AGATHION_6, DEPOIS)
        catalogo.registrar(_chave(HARDIN_1), HARDIN_1, AGORA)
        catalogo.gravar()

        recarregado = Catalogo(pasta)
        assert recarregado.series == catalogo.series

    def test_uma_serie_que_NAO_apareceu_nesta_sessao_continua_la(self, tmp_path):
        """O catalogo nunca perde serie: ele so acrescenta.

        Este e o teste que prende a ausencia de poda como COMPORTAMENTO, e nao
        so como comentario no fonte.
        """
        pasta = tmp_path / ".mercado"
        primeiro = Catalogo(pasta)
        primeiro.registrar(_chave(AGATHION_6), AGATHION_6, AGORA)
        primeiro.gravar()

        segundo = Catalogo(pasta)
        segundo.registrar(_chave(HARDIN_1), HARDIN_1, DEPOIS)
        segundo.gravar()

        terceiro = Catalogo(pasta)
        assert set(terceiro.series) == {_chave(AGATHION_6), _chave(HARDIN_1)}

    def test_o_nome_exibido_com_PONTO_E_VIRGULA_sobrevive_a_releitura(
        self, tmp_path
    ):
        """O usuario corrige `nome_exibido` no Sheets — e pode digitar um `;`.

        Escrita e leitura pelo modulo `csv` da stdlib, que cita e escapa. Um
        `split(";")` a mao partiria a linha em duas aqui (T-02-23).
        """
        pasta = tmp_path / ".mercado"
        nome = 'Agathion; o "Alpha" Hunter'
        catalogo = Catalogo(pasta)
        catalogo.registrar("agathion-tortuoso#0", nome, AGORA)
        catalogo.gravar()

        recarregado = Catalogo(pasta)
        assert recarregado.series["agathion-tortuoso#0"].nome_exibido == nome

    def test_o_nome_exibido_com_QUEBRA_DE_LINHA_sobrevive(self, tmp_path):
        """Colar do Sheets traz quebra de linha junto mais vezes do que se pensa."""
        pasta = tmp_path / ".mercado"
        catalogo = Catalogo(pasta)
        catalogo.registrar("multi#0", "Linha um\nLinha dois", AGORA)
        catalogo.gravar()
        assert Catalogo(pasta).series["multi#0"].nome_exibido == (
            "Linha um\nLinha dois"
        )

    def test_gravar_nao_deixa_TEMPORARIO_para_tras(self, tmp_path):
        pasta = tmp_path / ".mercado"
        catalogo = Catalogo(pasta)
        catalogo.registrar(_chave(AGATHION_6), AGATHION_6, AGORA)
        catalogo.gravar()
        assert [c.name for c in pasta.iterdir()] == [ARQUIVO_DO_CATALOGO]

    def test_a_ordem_das_linhas_e_ESTAVEL_entre_duas_gravacoes(self, tmp_path):
        """Sem ordem estavel, `git diff` e o olho humano ficam inuteis.

        A ordem e a da CHAVE, e nao a de insercao do dicionario: duas execucoes
        sobre o mesmo material produzem o mesmo arquivo, byte a byte.
        """
        pasta = tmp_path / ".mercado"
        primeiro = Catalogo(pasta)
        for nome in (HARDIN_3, AGATHION_6, AGATHION_4, HARDIN_1):
            primeiro.registrar(_chave(nome), nome, AGORA)
        primeiro.gravar()
        bruto = (pasta / ARQUIVO_DO_CATALOGO).read_bytes()

        segundo = Catalogo(pasta)
        segundo.gravar()
        assert (pasta / ARQUIVO_DO_CATALOGO).read_bytes() == bruto

        chaves = [linha.split(";")[0] for linha in _linhas_cruas(pasta)[1:]]
        assert chaves == sorted(chaves)


class TestALeituraDEFENSIVA:
    """Linha malformada cai SOZINHA, com aviso. O arquivo nunca e 'corrompido'."""

    def _escrever(self, tmp_path: Path, corpo: str) -> Path:
        pasta = tmp_path / ".mercado"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / ARQUIVO_DO_CATALOGO).write_text(corpo, encoding="utf-8")
        return pasta

    def test_a_ULTIMA_linha_truncada_cai_e_as_anteriores_CARREGAM(
        self, tmp_path, caplog
    ):
        """Um append interrompido trunca a ultima linha. Familia do FUND-01.

        O dado parcial nao pode virar dado plausivel — e o resto do arquivo,
        que esta inteiro, nao pode ser jogado fora por causa dele.
        """
        pasta = self._escrever(
            tmp_path,
            "chave;nome_exibido;primeira_vez;ultima_vez;avistamentos\n"
            "a#0;Item A;2026-08-30T21:15:00;2026-08-30T21:15:00;3\n"
            "b#0;Item B;2026-08-30T21:16:00;2026-08-30T21:16:00;5\n"
            "c#0;Item C;2026-08-30T21:1",
        )
        with caplog.at_level("WARNING", logger="l2scanner.mercado_catalogo"):
            catalogo = Catalogo(pasta)
        assert set(catalogo.series) == {"a#0", "b#0"}
        assert catalogo.series["b#0"].avistamentos == 5
        assert "c#0" in caplog.text
        assert "linha 4" in caplog.text

    def test_uma_linha_DO_MEIO_com_campos_a_menos_cai_sozinha(
        self, tmp_path, caplog
    ):
        pasta = self._escrever(
            tmp_path,
            "chave;nome_exibido;primeira_vez;ultima_vez;avistamentos\n"
            "a#0;Item A;2026-08-30T21:15:00;2026-08-30T21:15:00;3\n"
            "b#0;Item B;2026-08-30T21:16:00\n"
            "c#0;Item C;2026-08-30T21:17:00;2026-08-30T21:17:00;7\n",
        )
        with caplog.at_level("WARNING", logger="l2scanner.mercado_catalogo"):
            catalogo = Catalogo(pasta)
        assert set(catalogo.series) == {"a#0", "c#0"}
        assert "b#0" in caplog.text

    def test_uma_linha_com_campos_A_MAIS_tambem_cai(self, tmp_path, caplog):
        pasta = self._escrever(
            tmp_path,
            "chave;nome_exibido;primeira_vez;ultima_vez;avistamentos\n"
            "a#0;Item A;2026-08-30T21:15:00;2026-08-30T21:15:00;3;sobra\n"
            "c#0;Item C;2026-08-30T21:17:00;2026-08-30T21:17:00;7\n",
        )
        with caplog.at_level("WARNING", logger="l2scanner.mercado_catalogo"):
            catalogo = Catalogo(pasta)
        assert set(catalogo.series) == {"c#0"}

    def test_avistamentos_que_nao_e_numero_derruba_SO_a_linha(
        self, tmp_path, caplog
    ):
        pasta = self._escrever(
            tmp_path,
            "chave;nome_exibido;primeira_vez;ultima_vez;avistamentos\n"
            "a#0;Item A;2026-08-30T21:15:00;2026-08-30T21:15:00;muitas\n"
            "c#0;Item C;2026-08-30T21:17:00;2026-08-30T21:17:00;7\n",
        )
        with caplog.at_level("WARNING", logger="l2scanner.mercado_catalogo"):
            catalogo = Catalogo(pasta)
        assert set(catalogo.series) == {"c#0"}
        assert "a#0" in caplog.text

    def test_data_ilegivel_derruba_SO_a_linha(self, tmp_path, caplog):
        pasta = self._escrever(
            tmp_path,
            "chave;nome_exibido;primeira_vez;ultima_vez;avistamentos\n"
            "a#0;Item A;ontem;2026-08-30T21:15:00;3\n"
            "c#0;Item C;2026-08-30T21:17:00;2026-08-30T21:17:00;7\n",
        )
        with caplog.at_level("WARNING", logger="l2scanner.mercado_catalogo"):
            catalogo = Catalogo(pasta)
        assert set(catalogo.series) == {"c#0"}

    def test_chave_VAZIA_no_arquivo_cai(self, tmp_path, caplog):
        pasta = self._escrever(
            tmp_path,
            "chave;nome_exibido;primeira_vez;ultima_vez;avistamentos\n"
            ";Item sem chave;2026-08-30T21:15:00;2026-08-30T21:15:00;3\n"
            "c#0;Item C;2026-08-30T21:17:00;2026-08-30T21:17:00;7\n",
        )
        with caplog.at_level("WARNING", logger="l2scanner.mercado_catalogo"):
            catalogo = Catalogo(pasta)
        assert set(catalogo.series) == {"c#0"}

    def test_o_aviso_NOMEIA_a_linha_e_mostra_o_que_ela_tinha(
        self, tmp_path, caplog
    ):
        """Forense depois do farm: sem o numero da linha, o usuario nao acha."""
        pasta = self._escrever(
            tmp_path,
            "chave;nome_exibido;primeira_vez;ultima_vez;avistamentos\n"
            "quebrada#0;so isso\n",
        )
        with caplog.at_level("WARNING", logger="l2scanner.mercado_catalogo"):
            Catalogo(pasta)
        assert "linha 2" in caplog.text
        assert "quebrada#0" in caplog.text

    def test_um_arquivo_INTEIRAMENTE_lixo_carrega_vazio_e_NAO_levanta(
        self, tmp_path, caplog
    ):
        pasta = self._escrever(tmp_path, "lixo sem estrutura\nmais lixo\n")
        with caplog.at_level("WARNING", logger="l2scanner.mercado_catalogo"):
            catalogo = Catalogo(pasta)
        assert catalogo.series == {}

    def test_um_arquivo_SEM_cabecalho_ainda_carrega_as_linhas_boas(self, tmp_path):
        """O usuario pode apagar o cabecalho no Sheets sem querer.

        Ele nao e a identidade do arquivo — as linhas sao.
        """
        pasta = self._escrever(
            tmp_path,
            "a#0;Item A;2026-08-30T21:15:00;2026-08-30T21:15:00;3\n",
        )
        assert set(Catalogo(pasta).series) == {"a#0"}

    def test_a_linha_descartada_NAO_volta_ao_arquivo_na_gravacao_seguinte(
        self, tmp_path, caplog
    ):
        """Ela caiu porque nao era dado. Reescreve-la a promoveria a dado."""
        pasta = self._escrever(
            tmp_path,
            "chave;nome_exibido;primeira_vez;ultima_vez;avistamentos\n"
            "a#0;Item A;2026-08-30T21:15:00;2026-08-30T21:15:00;3\n"
            "b#0;truncad",
        )
        with caplog.at_level("WARNING", logger="l2scanner.mercado_catalogo"):
            catalogo = Catalogo(pasta)
        catalogo.gravar()
        assert "b#0" not in (pasta / ARQUIVO_DO_CATALOGO).read_text(
            encoding="utf-8"
        )


class TestAPonteComOsPredicados:
    """O catalogo em disco alimenta `agrupar`, que so fala `EntradaDoCatalogo`."""

    def test_as_entradas_saem_no_formato_que_agrupar_consome(self, tmp_path):
        catalogo = Catalogo(tmp_path / ".mercado")
        catalogo.registrar(_chave(AGATHION_6), AGATHION_6, AGORA)
        entradas = catalogo.entradas()
        assert isinstance(entradas, dict)
        entrada = entradas[_chave(AGATHION_6)]
        assert isinstance(entrada, EntradaDoCatalogo)
        assert entrada.nome == AGATHION_6
        assert entrada.assinatura == assinatura_por_ocr(AGATHION_6)

    def test_uma_leitura_com_RUIDO_agrupa_na_serie_que_veio_do_DISCO(
        self, tmp_path
    ):
        """A ida e volta pelo arquivo nao pode quebrar o agrupamento."""
        pasta = tmp_path / ".mercado"
        primeiro = Catalogo(pasta)
        primeiro.registrar(_chave(EVOLUTION), EVOLUTION, AGORA)
        primeiro.gravar()

        recarregado = Catalogo(pasta)
        veredito = agrupar(
            EWLUTION,
            assinatura_por_ocr(EWLUTION),
            recarregado.entradas().values(),
            0.90,
            0.88,
        )
        assert veredito.chave == _chave(EVOLUTION)
        assert veredito.nova is False
