"""O consumo da ponte: XP absoluto quando ha constante, MOTIVO quando nao ha.

As duas metades deste requisito falham por motivos OPOSTOS, e por isso os dois
caminhos sao testados lado a lado. Sem a constante, nao ha o que converter. Sem
a recusa nomeada, a conversao acontece com a constante do NIVEL ANTERIOR e
produz um numero plausivel e errado — o unico defeito que este workstream trata
como inaceitavel.

E o teste da ausencia por nivel afirma, na MESMA funcao, que a constante do
nivel anterior EXISTIA no arquivo. Sem essa assercao ele passaria por vacuidade:
estaria provando que nao houve queda para uma entrada que nunca existiu.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from l2scanner.renda_ponte import (
    LINHAS_MEDIDAS_DO_BONUS,
    MULTIPLICADOR_EXIBIDO_PELA_BARRA_EM_CENTESIMOS,
    PISO_DO_MULTIPLICADOR_EM_CENTESIMOS,
    SEM_PONTE_NENHUMA,
    SEM_PONTE_PARA_O_NIVEL,
    SEM_PONTE_PARA_O_PERSONAGEM,
    TETO_DO_MULTIPLICADOR_EM_CENTESIMOS,
    XpAbsoluto,
    multiplicador_em_centesimos,
    total_do_xp_da_linha,
    xp_acumulado_no_nivel,
    xp_do_ganho,
    xp_por_hora,
)

# A CONSTANTE MEDIDA, e ela e o numero versionado no REQUIREMENTS.md (REND-08).
#
# `387 / 0,0009956 = 388.700 XP por ponto percentual`, de um censo COMPLETO a
# 55 Hz: a soma dos 188 degraus e 1903 unidades e a barra andou exatamente 1903.
XP_POR_PONTO_NO_67 = 388_700

# A medicao ANTERIOR, a 0,8 s de amostragem. Ela mora aqui como a constante do
# nivel VIZINHO nos testes de queda — 1,5% abaixo, que e o que da direito de
# chamar a de cima de constante.
XP_POR_PONTO_NO_66 = 383_124

# O EXP de campo da Faerlina: 8,0012% em decimos de milesimo
# (`tests/test_renda_par.py:100`).
EXP_DE_CAMPO_EM_DECIMOS = 80_012

# O ganho do par do level up, ja com a regra do REND-03 aplicada pela Fase 2.
GANHO_DO_LEVEL_UP_EM_DECIMOS = 394_380

PROCEDENCIA = {
    "medido_em": "2026-09-02",
    "n_abates": 114,
    "n_linhas_de_chat": 240,
    "janela_em_segundos": 150,
}


def entrada(xp_por_ponto: int) -> dict:
    return dict(PROCEDENCIA, xp_por_ponto=xp_por_ponto)


def ponte_com_os_dois_niveis() -> dict:
    return {
        "Faerlina": {
            "66": entrada(XP_POR_PONTO_NO_66),
            "67": entrada(XP_POR_PONTO_NO_67),
        },
        "Yazalaque": {"70": entrada(410_000)},
    }


class TestOCaminhoComConstante:
    """Com constante para o nivel ATUAL, o XP absoluto sai."""

    def test_O_GANHO_DO_LEVEL_UP_VIRA_XP_ABSOLUTO(self):
        """A conta feita a mao no proprio teste, e nao copiada do modulo."""
        resultado = xp_do_ganho(
            ponte_com_os_dois_niveis(),
            "Faerlina",
            67,
            GANHO_DO_LEVEL_UP_EM_DECIMOS,
        )
        assert resultado.motivo_da_ausencia is None
        # 39,438 pontos percentuais x 388.700 XP por ponto.
        assert resultado.valor == Fraction(
            GANHO_DO_LEVEL_UP_EM_DECIMOS * XP_POR_PONTO_NO_67, 10_000
        )
        assert int(resultado.valor) == 15_329_550

    def test_O_EXP_DE_CAMPO_VIRA_XP_ACUMULADO_NO_NIVEL(self):
        resultado = xp_acumulado_no_nivel(
            ponte_com_os_dois_niveis(), "Faerlina", 67, EXP_DE_CAMPO_EM_DECIMOS
        )
        assert resultado.motivo_da_ausencia is None
        assert resultado.valor == Fraction(
            EXP_DE_CAMPO_EM_DECIMOS * XP_POR_PONTO_NO_67, 10_000
        )
        assert int(resultado.valor) == 3_110_066

    def test_O_NIVEL_VIZINHO_USA_A_CONSTANTE_DELE_E_NAO_A_DO_67(self):
        """O controle da proibicao de queda pelo lado de cima.

        Se o modulo devolvesse sempre a primeira entrada do personagem, este
        teste e o do 67 nao poderiam passar juntos.
        """
        no_66 = xp_do_ganho(
            ponte_com_os_dois_niveis(), "Faerlina", 66, GANHO_DO_LEVEL_UP_EM_DECIMOS
        )
        no_67 = xp_do_ganho(
            ponte_com_os_dois_niveis(), "Faerlina", 67, GANHO_DO_LEVEL_UP_EM_DECIMOS
        )
        assert no_66.valor != no_67.valor
        assert no_66.valor == Fraction(
            GANHO_DO_LEVEL_UP_EM_DECIMOS * XP_POR_PONTO_NO_66, 10_000
        )

    def test_O_RESULTADO_CARREGA_A_PROCEDENCIA_DA_CONSTANTE_QUE_USOU(self):
        """Quem exibe precisa poder dizer DE ONDE o numero veio.

        Uma constante medida em 2,5 minutos com censo completo e uma medida em
        seis minutos por amostragem sao o mesmo numero na tela. A procedencia e
        o que as separa.
        """
        resultado = xp_do_ganho(
            ponte_com_os_dois_niveis(), "Faerlina", 67, GANHO_DO_LEVEL_UP_EM_DECIMOS
        )
        assert resultado.procedencia["n_abates"] == 114
        assert resultado.procedencia["n_linhas_de_chat"] == 240
        assert resultado.procedencia["medido_em"] == "2026-09-02"
        assert resultado.procedencia["xp_por_ponto"] == XP_POR_PONTO_NO_67

    def test_UMA_SUBCHAVE_DESCONHECIDA_ATRAVESSA_ATE_A_PROCEDENCIA(self):
        """A procedencia e o dict CRU, e nao uma reconstrucao campo a campo.

        Reconstruir aqui faria o campo novo da ferramenta de medicao sumir no
        caminho entre o arquivo e a tela — o mesmo defeito que o `salvar`
        evita, uma camada acima.
        """
        ponte = ponte_com_os_dois_niveis()
        ponte["Faerlina"]["67"]["n_sessoes"] = 3
        resultado = xp_do_ganho(ponte, "Faerlina", 67, GANHO_DO_LEVEL_UP_EM_DECIMOS)
        assert resultado.procedencia["n_sessoes"] == 3

    def test_A_CHAVE_DE_NIVEL_INTEIRA_TAMBEM_E_ENCONTRADA(self):
        """Antes do primeiro `salvar` a chave e inteira; depois dele e texto."""
        ponte = {"Faerlina": {67: entrada(XP_POR_PONTO_NO_67)}}
        resultado = xp_do_ganho(ponte, "Faerlina", 67, GANHO_DO_LEVEL_UP_EM_DECIMOS)
        assert resultado.motivo_da_ausencia is None


class TestAsTresAusenciasSaoDISTINGUIVEIS:
    """Tres textos diferentes, porque o CONSERTO de cada uma e outro."""

    def test_SEM_A_CHAVE_INTEIRA_O_VALOR_E_NADA_COM_MOTIVO(self):
        resultado = xp_do_ganho(None, "Faerlina", 67, GANHO_DO_LEVEL_UP_EM_DECIMOS)
        assert resultado.valor is None
        assert resultado.motivo_da_ausencia == SEM_PONTE_NENHUMA
        assert resultado.procedencia is None

    def test_SEM_ENTRADA_PARA_O_PERSONAGEM_O_VALOR_E_NADA_COM_MOTIVO(self):
        """E a entrada do OUTRO personagem existia, e nao foi usada."""
        ponte = ponte_com_os_dois_niveis()
        resultado = xp_do_ganho(ponte, "Korzis", 67, GANHO_DO_LEVEL_UP_EM_DECIMOS)
        assert ponte["Faerlina"]["67"]["xp_por_ponto"] == XP_POR_PONTO_NO_67, (
            "a entrada vizinha tem de EXISTIR, senao a assercao de baixo e vacua"
        )
        assert resultado.valor is None
        assert resultado.motivo_da_ausencia == SEM_PONTE_PARA_O_PERSONAGEM

    def test_SEM_ENTRADA_PARA_O_NIVEL_ATUAL_NAO_CAI_PARA_O_ANTERIOR(self):
        """O defeito que este modulo existe para impedir (CTX-8).

        A constante do 66 aplicada ao 67 produz um numero com a mesma cara e
        errado, e o custo do nivel muda justamente entre os dois. Este teste
        afirma, na MESMA funcao, que a constante do 66 estava no arquivo — sem
        isso ele passaria por vacuidade, que e o Pitfall 5.
        """
        ponte = ponte_com_os_dois_niveis()
        del ponte["Faerlina"]["67"]

        assert ponte["Faerlina"]["66"]["xp_por_ponto"] == XP_POR_PONTO_NO_66, (
            "a constante do nivel ANTERIOR tem de existir no arquivo, senao "
            "este teste nao prova que ela nao foi usada"
        )

        resultado = xp_do_ganho(ponte, "Faerlina", 67, GANHO_DO_LEVEL_UP_EM_DECIMOS)
        assert resultado.valor is None
        assert resultado.motivo_da_ausencia == SEM_PONTE_PARA_O_NIVEL
        assert resultado.procedencia is None

        no_66 = xp_do_ganho(ponte, "Faerlina", 66, GANHO_DO_LEVEL_UP_EM_DECIMOS)
        assert no_66.valor is not None, (
            "o CONTROLE: a constante do 66 continua utilizavel para o 66"
        )

    def test_OS_TRES_MOTIVOS_SAO_TEXTOS_DIFERENTES(self):
        """Um motivo unico obrigaria quem le a adivinhar qual conserto fazer."""
        motivos = {
            SEM_PONTE_NENHUMA,
            SEM_PONTE_PARA_O_PERSONAGEM,
            SEM_PONTE_PARA_O_NIVEL,
        }
        assert len(motivos) == 3
        assert all(texto for texto in motivos), "nenhum motivo pode ser vazio"

    def test_SEM_NOME_E_SEM_NIVEL_TAMBEM_TEM_MOTIVO(self):
        ponte = ponte_com_os_dois_niveis()
        assert xp_do_ganho(ponte, None, 67, 100).motivo_da_ausencia is not None
        assert xp_do_ganho(ponte, "Faerlina", None, 100).motivo_da_ausencia is not None


class TestATaxaAtravessaAMesmaPonte:
    """Pontos percentuais por hora viram XP por hora pela MESMA constante."""

    def test_UMA_TAXA_EM_PONTOS_PERCENTUAIS_VIRA_TAXA_EM_XP(self):
        # 6,29 pontos percentuais por hora — a janela de seis minutos do REND-08.
        resultado = xp_por_hora(
            ponte_com_os_dois_niveis(), "Faerlina", 67, Fraction(629, 100)
        )
        assert resultado.motivo_da_ausencia is None
        assert resultado.valor == 2_444_923

    def test_A_TAXA_HERDA_O_MOTIVO_DE_AUSENCIA_QUANDO_NAO_HA_PONTE(self):
        ponte = ponte_com_os_dois_niveis()
        del ponte["Faerlina"]["67"]
        resultado = xp_por_hora(ponte, "Faerlina", 67, Fraction(629, 100))
        assert resultado.valor is None
        assert resultado.motivo_da_ausencia == SEM_PONTE_PARA_O_NIVEL


class TestNenhumPontoFlutuanteAtravessaAConversao:
    """A regra ja escrita na docstring do `LeituraDaRenda`, aplicada aqui."""

    @pytest.mark.parametrize("decimos", [80_012, 394_380, 10_000, 1])
    def test_O_RESULTADO_E_INTEIRO_OU_FRACTION_E_NUNCA_FLOAT(self, decimos):
        resultado = xp_do_ganho(
            ponte_com_os_dois_niveis(), "Faerlina", 67, decimos
        )
        assert isinstance(resultado.valor, (int, Fraction))
        assert not isinstance(resultado.valor, float)

    def test_UM_PONTO_PERCENTUAL_INTEIRO_VOLTA_COMO_INTEIRO(self):
        """10.000 decimos de milesimo E um ponto percentual: a conta e exata."""
        resultado = xp_do_ganho(ponte_com_os_dois_niveis(), "Faerlina", 67, 10_000)
        assert resultado.valor == XP_POR_PONTO_NO_67
        assert isinstance(resultado.valor, int)

    def test_O_XP_TOTAL_DO_NIVEL_E_A_CONSTANTE_VEZES_CEM(self):
        """38,87 milhoes, que e o numero versionado no REND-08."""
        resultado = xp_acumulado_no_nivel(
            ponte_com_os_dois_niveis(), "Faerlina", 67, 100 * 10_000
        )
        assert resultado.valor == 38_870_000


class TestAConvencaoDoBonusDoChat:
    """REND-09: `363 XP (bonus: 299)` e 363, e a prova e o multiplicador."""

    def test_O_TOTAL_JA_INCLUI_O_BONUS(self):
        assert total_do_xp_da_linha(total=363, bonus=299) == 363

    def test_O_CONTROLE_ELE_NAO_DEVOLVE_A_SOMA(self):
        """Sem este controle, uma funcao que somasse passaria no irmao acima?

        Nao — mas ela e a implementacao ERRADA que a proxima pessoa vai
        escrever, e escrever o numero errado por extenso e o que impede o
        proximo leitor de "consertar" a funcao para 662.
        """
        assert total_do_xp_da_linha(total=363, bonus=299) != 662

    def test_AS_QUATRO_LINHAS_MEDIDAS_CAEM_NA_BANDA_DO_MULTIPLICADOR(self):
        fora = []
        for total, bonus in LINHAS_MEDIDAS_DO_BONUS:
            centesimos = multiplicador_em_centesimos(total=total, bonus=bonus)
            if not (
                PISO_DO_MULTIPLICADOR_EM_CENTESIMOS
                <= centesimos
                <= TETO_DO_MULTIPLICADOR_EM_CENTESIMOS
            ):
                fora.append((total, bonus, centesimos))
        assert not fora, (
            f"estas linhas do chat nao caem entre "
            f"{PISO_DO_MULTIPLICADOR_EM_CENTESIMOS}% e "
            f"{TETO_DO_MULTIPLICADOR_EM_CENTESIMOS}%: {fora}. A propria barra "
            f"exibe {MULTIPLICADOR_EXIBIDO_PELA_BARRA_EM_CENTESIMOS}% ao lado "
            f"do EXP, e e com ele que estes numeros tem de conversar."
        )

    def test_AS_QUATRO_LINHAS_SAO_AS_VERSIONADAS_NO_REQUIREMENTS(self):
        """Os restos `64, 69, 72, 78` sao o que o REND-09 versiona."""
        restos = [total - bonus for total, bonus in LINHAS_MEDIDAS_DO_BONUS]
        assert restos == [64, 69, 72, 78]
        assert [total for total, _ in LINHAS_MEDIDAS_DO_BONUS] == [363, 388, 405, 439]

    def test_A_BANDA_CONVERSA_COM_OS_562_QUE_A_BARRA_EXIBE(self):
        assert (
            PISO_DO_MULTIPLICADOR_EM_CENTESIMOS
            == MULTIPLICADOR_EXIBIDO_PELA_BARRA_EM_CENTESIMOS
        )

    def test_A_SOMA_DARIA_UM_MULTIPLICADOR_QUE_NAO_EXISTE_NA_TELA(self):
        """A refutacao por medicao, e nao por leitura de documentacao.

        Se o total fosse `363+299`, o multiplicador seria 10,3x — e nada na
        tela do usuario corresponde a 10,3x.
        """
        somado = 363 + 299
        centesimos_da_soma = somado * 100 // 64
        assert centesimos_da_soma > TETO_DO_MULTIPLICADOR_EM_CENTESIMOS
        assert centesimos_da_soma == 1034

    def test_UMA_LINHA_COM_BONUS_MAIOR_QUE_O_TOTAL_E_RECUSADA(self):
        """Ela e malformada, e um parser que a aceitasse inventaria o resto."""
        with pytest.raises(ValueError):
            total_do_xp_da_linha(total=299, bonus=363)
        with pytest.raises(ValueError):
            multiplicador_em_centesimos(total=363, bonus=363)


class TestAFormaDoResultado:
    """`XpAbsoluto` copia a forma de `Tendencia`: valor OU motivo, nunca os dois."""

    def test_O_VALOR_E_O_MOTIVO_SAO_EXCLUDENTES(self):
        com = xp_do_ganho(ponte_com_os_dois_niveis(), "Faerlina", 67, 10_000)
        sem = xp_do_ganho(None, "Faerlina", 67, 10_000)
        for resultado in (com, sem):
            assert (resultado.valor is None) != (
                resultado.motivo_da_ausencia is None
            ), "um resultado com valor E motivo, ou sem os dois, e incoerente"

    def test_ELE_E_CONGELADO(self):
        resultado = xp_do_ganho(ponte_com_os_dois_niveis(), "Faerlina", 67, 10_000)
        assert isinstance(resultado, XpAbsoluto)
        with pytest.raises(Exception):
            resultado.valor = 1
