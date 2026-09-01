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
    similaridade_do_resto,
)
from l2scanner.mercado_catalogo import PISO_DO_RESTO

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

# O par que fez a faixa cinzenta engolir um item REAL, na sessao de 2026-09-01
# 04:32 do usuario: 10 de 10 linhas recusadas, com as DUAS escalas de OCR
# concordando e lendo o nome CERTO. Os dois nomes estao no `.mercado/` dele.
SCROLL_ARMOR = "Protecting Scroll: Enchant C-grade Armor"
SCROLL_WEAPON = "Protecting Scroll: Enchant C-grade Weapon"
SCROLL_D_WEAPON = "Scroll: Enchant D-grade Weapon"

# As DUAS series que o catalogo do usuario tem DUPLICADAS por ruido de OCR:
# `4-hunter-s-st-kings#4` e `4-hunter-s-stockings#4` sao o MESMO item.
STOCKINGS = "+4 Hunter's Stockings"
STKINGS = "+4 Hunter's St«kings"

# O par que REFUTA qualquer recalibracao: ele da EXATAMENTE o mesmo 0,8889 do
# par Armor/Weapon, e e o MESMO item.
TUNIC = "Hunter's Tunic"
TUNIC_TORTO = "Hunteds Tunic"

# O par que as DUAS travas de hoje deixam passar, e que vale DEZ VEZES na loja
# de NPC do usuario: 200.000 contra 20.000 adena. A trava de DIGITOS nao ve
# letra (assinatura `''` nos dois) e a trava por PALAVRA nao veta (1 caractere
# torto em 7, resto 0,8571 contra o piso 0,4500). Sobra a similaridade do nome
# inteiro, 0,9375 >= corte 0,8947, e os dois FUNDEM numa serie so.
GEMSTONE_B = "B-grade Gemstone"
GEMSTONE_C = "C-grade Gemstone"

# Os OUTROS pares com letra de grade cujo veredito NAO pode se mexer. O
# `Armor`/`Weapon` continua separado pela trava por PALAVRA, e nao pela letra —
# a letra e a MESMA nos dois.
DRAGON_3 = "+3 Dragon Belt"
DRAGON_4 = "+4 Dragon Belt"
ESPIRITO_FOGO = "Fire Spirit Evolution Stone"
ESPIRITO_VENTO = "Wind Spirit Evolution Stone"
ADEN_1 = "Aden's Soul Crystal Lv. 1 - Weapon"
ADEN_3 = "Aden's Soul Crystal Lv. 3 - Weapon"
STOCKINGS_5 = "+5 Hunter's Stockings"
STKINGS_5 = "+5 Hunter's St«kings"

# Os dois numeros que estao no `calibration.json` do usuario HOJE. Os testes que
# reproduzem a sessao dele cobram contra ESTES, e nao contra numeros de
# conveniencia: o defeito so existe nesta faixa de 0,011 de largura.
CORTE_DA_PRODUCAO = 0.8947
PISO_DA_PRODUCAO = 0.8837


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


class TestALetraDeGrade:
    """A letra de grade entra na assinatura, pelo MESMO mecanismo do D-03.

    O DEFEITO, MEDIDO NO CATALOGO REAL DO USUARIO
    ==============================================
    `B-grade Gemstone` e `C-grade Gemstone` FUNDIAM numa serie so, e na loja de
    NPC dele os dois valem **200.000 e 20.000 adena** — dez vezes de diferenca.
    Fundidos, a mediana da serie mistura precos sem relacao nenhuma.

    POR QUE AS DUAS TRAVAS DE HOJE NAO PEGAVAM ESTE PAR
    ----------------------------------------------------
    - TRAVA DE DIGITOS (D-03): ela captura so DIGITO. `B-grade` e `C-grade` nao
      tem digito, entao os dois davam assinatura `''` e viravam candidatos um do
      outro.
    - TRAVA POR PALAVRA (D-09): o resto e o token `B-grade` contra `C-grade`, que
      difere em 1 de 7 caracteres — 0,8571, MUITO acima do `PISO_DO_RESTO`
      0,4500. Ela via ruido de OCR onde havia identidade.
    - Sobrava a similaridade do nome inteiro: 0,9375 >= corte 0,8947, e funde.

    O CONSERTO NAO E UM QUARTO MECANISMO, E O D-03 ESTENDIDO. A letra de grade
    carrega identidade exatamente como o digito de encantamento, entao ela entra
    na assinatura comparada por igualdade EXATA, ANTES de a similaridade opinar.
    Nunca num limiar: `corte`, `piso` e `PISO_DO_RESTO` nao foram tocados.
    """

    def test_a_letra_de_grade_vira_assinatura(self):
        assert assinatura_por_ocr(GEMSTONE_B) == "B"
        assert assinatura_por_ocr(GEMSTONE_C) == "C"
        assert assinatura_por_ocr(GEMSTONE_B) != assinatura_por_ocr(GEMSTONE_C)

    def test_o_par_que_vale_dez_vezes_deixa_de_FUNDIR(self):
        """O ALVO do conserto, com os numeros que o nomeiam.

        As duas travas de hoje sao afirmadas AQUI DENTRO, e nao so no comentario:
        se um dia a similaridade do nome cair abaixo do corte, ou o resto cair
        abaixo do piso, este teste passaria por motivo ERRADO e ninguem veria.
        """
        assert similaridade(GEMSTONE_B, GEMSTONE_C) >= CORTE_DA_PRODUCAO
        assert similaridade_do_resto(GEMSTONE_B, GEMSTONE_C) >= PISO_DO_RESTO

        catalogo = [_entrada(GEMSTONE_B)]
        r = agrupar(
            GEMSTONE_C,
            assinatura_por_ocr(GEMSTONE_C),
            catalogo,
            CORTE_DA_PRODUCAO,
            PISO_DA_PRODUCAO,
        )
        assert r.nova is True, f"o Gemstone ainda funde: {r.motivo}"
        assert r.chave != catalogo[0].chave
        assert "cinzenta" not in r.motivo.lower()

    def test_a_letra_entra_na_ORDEM_DE_APARICAO_junto_com_os_digitos(self):
        """Uma assinatura so, na ordem em que a tela desenha. Igual aos digitos.

        Separar letra de digito em dois campos daria a mesma resposta e custaria
        um formato novo na chave, que ja esta gravada no `.mercado/` do usuario.
        """
        assert assinatura_por_ocr("+5 B-grade Sword Lv. 3") == "5B3"
        assert assinatura_por_ocr("B-grade Sword Lv. 3") == "B3"

    def test_a_CAIXA_da_letra_nao_cria_serie_nova(self):
        """`b-grade` e `B-grade` sao a MESMA grade, e o L2 so escreve maiuscula.

        Dobrar a caixa nao pode FUNDIR duas grades distintas — nao existe par de
        grades que difira so na caixa. O precedente e o `_slug`, que ja dobra a
        caixa do corpo da chave (`D-grade Crystal` e `D-grade crystal` ja
        produzem UMA chave hoje).
        """
        assert assinatura_por_ocr("b-grade Gemstone") == "B"
        assert assinatura_por_ocr("B-GRADE Gemstone") == "B"
        assert assinatura_por_ocr("B-Grade Gemstone") == "B"

    def test_so_a_letra_SOLTA_antes_do_sufixo_conta(self):
        """`Non-grade` nao tem letra de grade: o `n` vem colado num `No`.

        Sem esta borda, toda palavra terminada em letra seguida de `-grade`
        entregaria a ULTIMA letra dela como se fosse grade.
        """
        assert assinatura_por_ocr("Non-grade Sword") == ""
        assert assinatura_por_ocr("Upgrade Kit") == ""
        assert assinatura_por_ocr("Sword-grade Thing") == ""

    def test_letra_nao_ascii_nao_conta_como_letra_de_grade(self):
        """O `С` cirilico e desenhado IGUAL ao `C` latino, e nao e ele.

        A mesma razao de `DIGITOS` existir em vez de `str.isdigit()`: um ponto
        Unicode parecido virando assinatura criaria uma serie que ninguem
        reproduz olhando a tela. O desfecho de recusar e assinatura `''`, que e
        o comportamento de HOJE — nunca uma assinatura inventada.
        """
        assert assinatura_por_ocr("С-grade Gemstone") == ""

    def test_nome_sem_letra_de_grade_nenhuma_continua_com_a_assinatura_DE_HOJE(self):
        """O controle negativo mais barato: quem nao tem grade nao muda."""
        assert assinatura_por_ocr(AGATHION_6) == "6"
        assert assinatura_por_ocr(AGATHION_0) == ""
        assert assinatura_por_ocr(EVOLUTION) == ""
        assert assinatura_por_ocr(STOCKINGS) == "4"

    def test_o_sufixo_incompleto_cai_no_comportamento_DE_HOJE_e_nao_inventa(self):
        """OCR que come o `-grade` devolve `''`, que e a assinatura de hoje.

        Isto NAO e o conserto falhando em silencio: e ele degradando para o
        estado anterior, que e o unico degrau seguro que existe. A evidencia de
        que o sufixo sobrevive ao OCR de verdade esta no `.mercado/` do usuario,
        onde `protecting-scroll-enchant-c-grade-armor#` acumulou 280
        avistamentos numa chave so.
        """
        assert assinatura_por_ocr("C grade Gemstone") == ""
        assert assinatura_por_ocr("C-grad Gemstone") == ""


class TestOsOitoParesDoControleNegativo:
    """Os SETE vereditos que nao podem se mexer, e o UM que tem de mudar.

    Um conserto que acerta o Gemstone e move qualquer um dos outros sete esta
    REPROVADO. A tabela vive aqui como teste, e nao como prosa num SUMMARY, para
    que a proxima mudanca na assinatura tropece nela antes de chegar ao farm.

    Medido nos dois lados do conserto, com o `corte` e o `piso` do
    `calibration.json` do usuario:

        no catalogo                  lido                     ANTES   DEPOIS
        +4 Hunter's Stockings        +4 Hunter's St«kings      FUNDE   FUNDE
        +5 Hunter's Stockings        +5 Hunter's St«kings      FUNDE   FUNDE
        ...C-grade Armor             ...C-grade Weapon         nova    nova
        +3 Dragon Belt               +4 Dragon Belt            nova    nova
        Fire Spirit Evolution Stone  Wind Spirit ...           nova    nova
        Aden's ... Lv. 1 - Weapon    Aden's ... Lv. 3 - Weapon nova    nova
        Hunter's Tunic               Hunteds Tunic             cinza   cinza
        B-grade Gemstone             C-grade Gemstone          FUNDE   nova
    """

    FUNDE = "FUNDE"
    NOVA = "separa (serie nova)"
    CINZENTA = "descarta (cinzenta)"

    @staticmethod
    def _desfecho(no_catalogo: str, lido: str) -> str:
        r = agrupar(
            lido,
            assinatura_por_ocr(lido),
            [_entrada(no_catalogo)],
            CORTE_DA_PRODUCAO,
            PISO_DA_PRODUCAO,
        )
        if r.chave is not None and not r.nova:
            return TestOsOitoParesDoControleNegativo.FUNDE
        if r.chave is None:
            return TestOsOitoParesDoControleNegativo.CINZENTA
        return TestOsOitoParesDoControleNegativo.NOVA

    @pytest.mark.parametrize(
        "no_catalogo, lido, esperado",
        [
            (STOCKINGS, STKINGS, FUNDE),
            (STOCKINGS_5, STKINGS_5, FUNDE),
            (SCROLL_ARMOR, SCROLL_WEAPON, NOVA),
            (DRAGON_3, DRAGON_4, NOVA),
            (ESPIRITO_FOGO, ESPIRITO_VENTO, NOVA),
            (ADEN_1, ADEN_3, NOVA),
            (TUNIC, TUNIC_TORTO, CINZENTA),
        ],
    )
    def test_os_sete_vereditos_de_hoje_ficam_INALTERADOS(
        self, no_catalogo, lido, esperado
    ):
        assert self._desfecho(no_catalogo, lido) == esperado

    def test_o_oitavo_par_e_o_unico_que_MUDA(self):
        assert self._desfecho(GEMSTONE_B, GEMSTONE_C) == self.NOVA

    def test_o_Armor_e_o_Weapon_continuam_separados_pela_trava_por_PALAVRA(self):
        """A letra e a MESMA nos dois, entao quem os separa nao pode ser ela.

        Sem esta afirmacao o par passaria a depender de um mecanismo que nao e o
        dele, e a proxima mexida na trava por palavra sairia impune.
        """
        assert assinatura_por_ocr(SCROLL_ARMOR) == assinatura_por_ocr(SCROLL_WEAPON)
        assert similaridade_do_resto(SCROLL_ARMOR, SCROLL_WEAPON) < PISO_DO_RESTO


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
        cinzenta nunca seria exercitada.

        A FIXTURA MUDOU EM 2026-09-01, E O MOTIVO PRECISA ESTAR ESCRITO. Ate a
        TRAVA POR PALAVRA (D-09) este teste usava `Common Aztac` contra
        `Common Aztac M. Def. +200` (0,6486). Esse par agora e resolvido ANTES,
        pela trava: o resto e `''` contra `'M. Def. +200'`, o veto morde, e ele
        vira SERIE NOVA — que e o veredito CERTO, porque os dois precisam
        separar (D-05). Ele nao sumiu da suite: virou
        `TestATravaPorPalavra::test_um_nome_que_e_o_outro_MAIS_palavras_vira_serie_nova`.

        A faixa cinzenta continua existindo e continua sendo cobrada — so que
        agora com o par cuja duvida e de CARACTERE e nao de PALAVRA, que e a
        duvida que ela existe para absorver. `Evolution` x `Ewlution` passa pela
        trava (resto 0,8235) e e a similaridade do nome inteiro que o coloca
        dentro da faixa.
        """
        catalogo = [_entrada(EVOLUTION)]
        similar = similaridade(EWLUTION, EVOLUTION)
        assert similaridade_do_resto(EWLUTION, EVOLUTION) >= PISO_DO_RESTO
        assert 0.90 <= similar < 0.95, similar
        r = agrupar(EWLUTION, "", catalogo, 0.95, 0.90)
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


class TestATravaPorPalavra:
    """D-09: os tokens IDENTICOS saem da conta ANTES de a similaridade opinar.

    A MESMA forma do D-03, um nivel acima. La o que sai por igualdade EXATA e a
    assinatura de DIGITOS; aqui saem as PALAVRAS INTEIRAS que as duas leituras
    tem em comum. Nos dois casos a similaridade decide so O RESTO.

    O DEFEITO QUE ESTA CLASSE PRENDE, com o numero que o nomeia
    ------------------------------------------------------------
    `difflib` sobre o nome INTEIRO e uma RAZAO, e por isso dilui a diferenca no
    prefixo compartilhado:

        'Hunteds Tunic'     x  "Hunter's Tunic"          = 0,8889  MESMO item
        '...C-grade Weapon' x  '...C-grade Armor'        = 0,8889  DIFERENTES

    O mesmo numero, com quatro casas, precisa decidir coisas OPOSTAS. Nenhum par
    (piso, corte) sobre esta metrica separa os dois casos, e a refutacao e
    ARITMETICA: 34 caracteres iguais de prefixo fazem uma PALAVRA trocada valer
    o mesmo que UM caractere torto num nome de 13.

    O resto e escala-livre em relacao ao prefixo, e ai o vao aparece. Medido
    sobre o catalogo REAL do usuario — 41 pares que precisam separar contra 4
    que precisam agrupar: pior AGRUPAR 0,8000, pior SEPARAR 0,4800, vao +0,3200.
    """

    def test_a_metrica_de_hoje_da_o_MESMO_numero_para_os_dois_vereditos(self):
        """A refutacao, presa como teste para que ninguem a redescubra."""
        ruido = similaridade(TUNIC_TORTO, TUNIC)
        itens_diferentes = similaridade(SCROLL_WEAPON, SCROLL_ARMOR)
        assert ruido == itens_diferentes
        assert PISO_DA_PRODUCAO <= ruido < CORTE_DA_PRODUCAO

    def test_o_resto_separa_o_que_a_similaridade_do_nome_inteiro_confunde(self):
        assert similaridade_do_resto(TUNIC_TORTO, TUNIC) >= PISO_DO_RESTO
        assert similaridade_do_resto(SCROLL_WEAPON, SCROLL_ARMOR) < PISO_DO_RESTO

    def test_uma_palavra_inteira_diferente_vira_SERIE_NOVA_e_nao_faixa_cinzenta(self):
        """O defeito da sessao de 2026-09-01 04:32, com os numeros dela.

        Enquanto `...C-grade Armor` estivesse no catalogo, `...C-grade Weapon`
        NUNCA agrupava e NUNCA criava serie. Nao era transitorio.
        """
        catalogo = [_entrada(SCROLL_ARMOR)]
        r = agrupar(
            SCROLL_WEAPON,
            assinatura_por_ocr(SCROLL_WEAPON),
            catalogo,
            CORTE_DA_PRODUCAO,
            PISO_DA_PRODUCAO,
        )
        assert r.chave == chave_da_serie(SCROLL_WEAPON, "")
        assert r.nova is True
        assert "cinzenta" not in r.motivo.lower()

    def test_o_catalogo_INTEIRO_do_usuario_nao_engole_mais_a_leitura(self):
        """Nao so contra `Armor`: contra as outras series de assinatura vazia.

        `Scroll: Enchant D-grade Weapon` esta no catalogo real e COMPARTILHA a
        palavra `Weapon` com a leitura — ele e o candidato que sobraria se a
        trava olhasse so a ULTIMA palavra.
        """
        catalogo = [
            _entrada(nome)
            for nome in (SCROLL_ARMOR, SCROLL_D_WEAPON, TUNIC, "Hunter's Breastplate")
        ]
        r = agrupar(SCROLL_WEAPON, "", catalogo, CORTE_DA_PRODUCAO, PISO_DA_PRODUCAO)
        assert r.nova is True

    def test_o_ruido_de_OCR_de_UMA_palavra_continua_agrupando(self):
        """O controle negativo do lado que NAO pode regredir.

        `St«kings` x `Stockings` e UM token com 2 caracteres tortos, e ele tem de
        sobreviver a trava. Os dois estao DUPLICADOS no catalogo do usuario hoje.
        """
        catalogo = [_entrada(STOCKINGS)]
        r = agrupar(STKINGS, "4", catalogo, 0.90, 0.70)
        assert r.nova is False
        assert r.chave == catalogo[0].chave

    def test_o_ruido_do_par_de_0_8889_continua_agrupando(self):
        """O outro lado do numero que refuta a recalibracao."""
        catalogo = [_entrada(TUNIC)]
        r = agrupar(TUNIC_TORTO, "", catalogo, 0.88, 0.70)
        assert r.nova is False
        assert r.chave == catalogo[0].chave

    def test_o_ruido_do_nome_inteiro_medido_pela_pesquisa_continua_agrupando(self):
        """`Evolution` x `Ewlution`: 0,9455 no nome inteiro, 0,8235 no resto."""
        assert similaridade_do_resto(EWLUTION, EVOLUTION) >= PISO_DO_RESTO
        r = agrupar(EWLUTION, "", [_entrada(EVOLUTION)], 0.90, 0.70)
        assert r.nova is False

    def test_a_trava_so_REMOVE_candidato_e_NUNCA_acrescenta(self):
        """A propriedade que honra o D-06: fusao NOVA e impossivel por construcao.

        Varre TODO par de nomes conhecidos deste arquivo que compartilhe
        assinatura: nenhum que hoje NAO agrupa pode passar a agrupar. Sem esta
        varredura a trava poderia mover a fronteira na direcao IRREVERSIVEL sem
        ninguem ver — e e justamente essa direcao que o D-06 protege.
        """
        nomes = [
            AGATHION_6, AGATHION_4, AGATHION_0, HARDIN_1, HARDIN_3, HARDIN_I,
            EVOLUTION, EWLUTION, AZTAC, AZTAC_LONGO, SCROLL_ARMOR, SCROLL_WEAPON,
            SCROLL_D_WEAPON, STOCKINGS, STKINGS, TUNIC, TUNIC_TORTO,
        ]
        for leitura in nomes:
            assinatura = assinatura_por_ocr(leitura)
            catalogo = [
                _entrada(outro)
                for outro in nomes
                if outro != leitura and assinatura_por_ocr(outro) == assinatura
            ]
            if not catalogo:
                continue
            veredito = agrupar(
                leitura, assinatura, catalogo, CORTE_DA_PRODUCAO, PISO_DA_PRODUCAO
            )
            if veredito.nova or veredito.chave is None:
                continue
            alvo = next(e for e in catalogo if e.chave == veredito.chave)
            assert similaridade(leitura, alvo.nome) >= CORTE_DA_PRODUCAO, (
                f"{leitura!r} passou a agrupar em {alvo.nome!r} e antes nao agrupava"
            )

    def test_um_nome_que_e_o_outro_MAIS_palavras_vira_serie_nova(self):
        """`Common Aztac` x `Common Aztac M. Def. +200`: 0,6486, precisa separar.

        Antes da trava este par caia na FAIXA CINZENTA e era descartado. Agora o
        resto e `''` contra `'M. Def. +200'`, o veto morde, e a serie nova nasce.
        Este e tambem o par que derrubou o `WRatio` com corte 88 (D-05): la ele
        FUNDIA a 90,00. A trava fecha essa porta por MECANISMO, e nao por limiar.
        """
        catalogo = [EntradaDoCatalogo(chave_da_serie(AZTAC, ""), AZTAC, "")]
        r = agrupar(AZTAC_LONGO, "", catalogo, 0.90, 0.60)
        assert r.nova is True
        assert r.chave == chave_da_serie(AZTAC_LONGO, "")

    def test_as_DUAS_bordas_do_vao_medido_ficam_de_cada_lado_do_piso(self):
        """Quem encosta no piso dos dois lados, preso com nome e numero.

        Estes dois pares SAO o vao. Se um deles se mexer, o piso 0,4500 deixa de
        ser o meio de coisa nenhuma e a medicao tem de ser refeita — e e melhor
        descobrir isso aqui do que numa sessao de farm.

            0,5000  `Chll` x `Doll`     PRECISA AGRUPAR — 2 caracteres em 4
            0,4000  `Earth` x `Water`   PRECISA SEPARAR — palavras inteiras

        O `Chll`/`Doll` e o par que derrubou a PRIMEIRA proposta desta trava:
        medida so contra o catalogo, ela propos 0,6400, e esse piso vetava um
        ruido de OCR que o repositorio nomeia por medicao ha tres fases.
        """
        assert similaridade_do_resto("Common Valakas Chll", "Common Valakas Doll") == 0.5
        assert similaridade_do_resto(EVOLUTION, "Water Spirit Evolution Stone") == 0.4
        assert 0.4 < PISO_DO_RESTO <= 0.5

    def test_o_ruido_de_DUAS_letras_num_token_curto_continua_agrupando(self):
        """`Chll` x `Doll`: 0,8947 no nome inteiro, e a borda de baixo do vao."""
        catalogo = [_entrada("Common Valakas Doll")]
        r = agrupar("Common Valakas Chll", "", catalogo, 0.89, 0.70)
        assert r.nova is False
        assert r.chave == catalogo[0].chave

    def test_dois_elementos_diferentes_no_mesmo_molde_de_nome_viram_series(self):
        """`Earth Spirit ...` x `Water Spirit ...`: 0,8929, dentro da faixa.

        O MESMO defeito do `Armor`/`Weapon` com outras palavras: dois itens
        reais que a faixa cinzenta descartava para sempre.
        """
        catalogo = [_entrada(EVOLUTION)]
        agua = "Water Spirit Evolution Stone"
        assert PISO_DA_PRODUCAO <= similaridade(agua, EVOLUTION) < CORTE_DA_PRODUCAO
        r = agrupar(agua, "", catalogo, CORTE_DA_PRODUCAO, PISO_DA_PRODUCAO)
        assert r.nova is True
        assert r.chave == chave_da_serie(agua, "")

    def test_sem_token_em_comum_a_trava_e_transparente(self):
        """O resto vira o nome inteiro, e a trava nao opina."""
        assert similaridade_do_resto("Stockings", "St«kings") == similaridade(
            "Stockings", "St«kings"
        )

    def test_o_resto_e_MULTICONJUNTO_e_nao_conjunto(self):
        """Uma palavra REPETIDA a mais nao pode virar "nome identico".

        Com conjunto, `Coin Coin Azul` contra `Coin Azul` esvaziaria os dois
        lados, a trava devolveria 1,0, e o par passaria como se fosse o mesmo
        nome — a FUSAO que a trava existe para impedir, entrando justamente pela
        funcao que deveria barra-la. Com multiconjunto sobra UM `Coin` de um
        lado so, e o resto e `'Coin'` contra `''`, que e 0,0 e veta.
        """
        assert similaridade_do_resto("Coin Coin Azul", "Coin Azul") == 0.0
        assert similaridade_do_resto("Coin Azul", "Coin Coin Azul") == 0.0

    def test_dois_nomes_identicos_dao_resto_perfeito(self):
        """Sem resto nenhum dos dois lados, a resposta e 1,0 e nao 0,0.

        `similaridade` devolve 0,0 para vazio contra vazio, e herdar esse 0,0
        aqui vetaria uma leitura contra ela mesma — o oposto do que a trava faz.
        """
        assert similaridade_do_resto(EVOLUTION, EVOLUTION) == 1.0

    def test_o_resto_nunca_levanta_no_vazio_nem_no_None(self):
        assert similaridade_do_resto(None, EVOLUTION) == 0.0
        assert similaridade_do_resto("", EVOLUTION) == 0.0
        assert similaridade_do_resto("   ", EVOLUTION) == 0.0
        assert similaridade_do_resto(None, None) == 0.0


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
