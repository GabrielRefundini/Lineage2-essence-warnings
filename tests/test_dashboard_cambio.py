"""O cambio XM -> BRL: o portao de duas camadas e a persistencia carimbada.

NADA AQUI TOCA A `.mercado/` REAL. Toda gravacao vai para `tmp_path`. O arquivo
de producao e dado do USUARIO, acumulado e sem desfazer — um teste que
escrevesse nele apagaria a taxa que ele informou a mao.

POR QUE ESTE ARQUIVO E MAIS PARANOICO QUE OS OUTROS DA FASE
===========================================================
Todo numero desta tela sai de uma leitura de tela que o usuario pode conferir
olhando o cliente do jogo. O cambio nao: ele e o UNICO numero que o jogo nao
sustenta, e ele MULTIPLICA todos os outros. Um digito lido errado aqui nao
mostra um valor estranho — mostra um valor plausivel e errado por um fator de
dez ou de mil, e a decisao de dinheiro real sai dele.

Por isso as formas perigosas tem teste com NOME PROPRIO, e nao so uma linha de
parametrizacao: um nome que cita `1_0` e o que faz alguem parar antes de
"simplificar" o portao numa refatoracao futura.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from l2scanner.dashboard_cambio import (
    MENSAGEM_DE_CAMBIO_INVALIDO,
    MOLDE_DO_CAMBIO,
    CambioInvalido,
    _apenas_o_valor,
    interpretar_o_cambio,
)

# ===========================================================================
# A TABELA MEDIDA DA PESQUISA (01-RESEARCH.md, Pitfall 5), REMEDIDA AQUI
# ===========================================================================
#
# Cada linha e uma entrada e o veredito que o portao INTEIRO tem que dar.
# `None` significa RECUSADO.
#
# As linhas marcadas com "so o molde pega" sao a razao de o molde existir: a
# segunda camada, sozinha, ACEITA todas elas — e ha um controle negativo abaixo
# provando isso, para que remover o molde nao deixe esta suite verde.
TABELA_MEDIDA = [
    # entrada, esperado
    ("0,50", Decimal("0.50")),  # a forma que o usuario digita
    ("0.50", Decimal("0.50")),  # a mesma, com ponto
    ("11", Decimal("11")),  # inteiro puro, sem separador
    ("0", None),  # zero nao e taxa: recusado pelas duas camadas
    ("-1", None),
    ("", None),
    ("abc", None),
    ("0,5,0", None),
    ("Infinity", None),  # recusado por `is_finite`
    ("NaN", None),
    ("1e3", None),  # so o molde pega -> a segunda camada le MIL
    ("+0.5", None),  # so o molde pega
    ("1_0", None),  # so o molde pega -> a segunda camada le DEZ
    ("1234567890123,5", None),  # so o molde pega
    ("٥", None),  # so o `re.ASCII` pega -> a segunda camada le CINCO
    ("０．５", None),  # digito e ponto de largura inteira
]

# As formas que a SEGUNDA CAMADA SOZINHA aceita, com o valor que ela produz.
# Medido nesta arvore (Python 3.12.10) e colado aqui: e este par entrada->valor
# que torna o molde obrigatorio, e nao a opiniao de ninguem.
FORMAS_QUE_SO_O_MOLDE_PEGA = [
    ("1e3", Decimal("1E+3")),
    ("+0.5", Decimal("0.5")),
    ("1_0", Decimal("10")),
    ("1234567890123,5", Decimal("1234567890123.5")),
    ("٥", Decimal("5")),
]


class TestOPortaoDeDuasCamadas:
    """A FORMA e julgada antes do VALOR, e a ordem e o produto."""

    @pytest.mark.parametrize("entrada, esperado", TABELA_MEDIDA)
    def test_a_tabela_MEDIDA_da_pesquisa_INTEIRA(self, entrada, esperado):
        if esperado is None:
            with pytest.raises(CambioInvalido):
                interpretar_o_cambio(entrada)
        else:
            assert interpretar_o_cambio(entrada) == esperado

    def test_a_virgula_e_o_ponto_dao_o_MESMO_Decimal(self):
        assert interpretar_o_cambio("0,50") == interpretar_o_cambio("0.50")

    # -- as formas com nome proprio ----------------------------------------
    #
    # Cada uma destas tem teste separado DE PROPOSITO. Elas ja estao na
    # parametrizacao acima; o que o nome acrescenta e o aviso para quem for
    # mexer no molde depois.

    def test_notacao_de_EXPOENTE_e_recusada_1e3_valeria_MIL(self):
        with pytest.raises(CambioInvalido):
            interpretar_o_cambio("1e3")

    def test_SUBLINHADO_e_recusado_1_0_valeria_DEZ_vinte_vezes_o_pretendido(self):
        # O usuario digita `1_0` querendo `1,0`. Sem o molde, a tela passa a
        # mostrar R$ vinte vezes maior que o pretendido, sem nenhum aviso.
        with pytest.raises(CambioInvalido):
            interpretar_o_cambio("1_0")

    def test_SINAL_explicito_e_recusado_mais_0_ponto_5(self):
        with pytest.raises(CambioInvalido):
            interpretar_o_cambio("+0.5")

    def test_numero_LONGO_DEMAIS_e_recusado_antes_de_virar_layout(self):
        # O UI-SPEC pede `maxlength` no campo; o servidor nao acredita nele.
        with pytest.raises(CambioInvalido):
            interpretar_o_cambio("1234567890123,5")

    def test_digito_UNICODE_nao_ASCII_e_recusado(self):
        # `٥` e o cinco arabe-indico. Ver o controle negativo: ele passa
        # por `Decimal` valendo 5, e por um `\d` SEM `re.ASCII` tambem.
        with pytest.raises(CambioInvalido):
            interpretar_o_cambio("٥")

    # -- a mensagem --------------------------------------------------------

    def test_a_mensagem_da_recusa_e_a_TRAVADA_no_UI_SPEC(self):
        # A frase esta travada no `## Copywriting Contract` da 01-UI-SPEC.md.
        # Improvisar aqui produziria duas frases para o mesmo estado.
        assert "maior que zero" in MENSAGEM_DE_CAMBIO_INVALIDO
        assert "0,50" in MENSAGEM_DE_CAMBIO_INVALIDO
        assert MENSAGEM_DE_CAMBIO_INVALIDO.isascii()

    def test_a_excecao_CARREGA_a_mensagem_travada_e_nao_uma_improvisada(self):
        with pytest.raises(CambioInvalido) as capturado:
            interpretar_o_cambio("abc")
        assert str(capturado.value) == MENSAGEM_DE_CAMBIO_INVALIDO

    def test_a_mensagem_diz_que_o_cambio_ANTERIOR_continua_valendo(self):
        # Anatomia da casa (`mercado_registro.py:472-479`): o que aconteceu,
        # que nada foi alterado, o que fazer, e o que continua funcionando.
        assert "anterior continua valendo" in MENSAGEM_DE_CAMBIO_INVALIDO
        assert "O QUE FAZER" in MENSAGEM_DE_CAMBIO_INVALIDO

    # -- a borda do espaco -------------------------------------------------

    def test_espaco_EM_VOLTA_e_tolerado_mas_espaco_NO_MEIO_nao(self):
        assert interpretar_o_cambio("  0,50  ") == Decimal("0.50")
        with pytest.raises(CambioInvalido):
            interpretar_o_cambio("0, 50")


class TestOControleNegativoDaSegundaCamada:
    """A PROVA de que a primeira camada nao e decorativa.

    Os testes acima afirmam que o portao INTEIRO recusa. Sozinhos, eles nao
    distinguem duas hipoteses muito diferentes: "o molde faz o trabalho" e "o
    `Decimal` ja recusaria isso de qualquer jeito, e o molde e enfeite".

    Esta classe separa as duas, chamando a SEGUNDA CAMADA SOZINHA sobre as
    mesmas entradas e afirmando que ela as ACEITA, com o valor que ela produz.
    E o controle negativo: sem ele, alguem que lesse so a classe de cima nao
    teria como saber que remover uma linha de `re` transforma `1_0` em dez.
    """

    @pytest.mark.parametrize("entrada, valor", FORMAS_QUE_SO_O_MOLDE_PEGA)
    def test_a_segunda_camada_SOZINHA_ACEITA_o_que_o_molde_recusa(
        self, entrada, valor
    ):
        # Chamada DIRETA na segunda camada, sem o molde na frente.
        assert _apenas_o_valor(entrada) == valor
        # E o portao INTEIRO recusa a mesma entrada.
        with pytest.raises(CambioInvalido):
            interpretar_o_cambio(entrada)

    def test_o_molde_SEM_re_ASCII_deixaria_o_digito_arabe_passar(self):
        # `re.ASCII` nao e enfeite: o mesmo padrao sem a flag CASA com `٥`,
        # e `Decimal` o converte em 5. As duas camadas, sem a flag, aceitariam.
        import re

        sem_a_flag = re.compile(MOLDE_DO_CAMBIO.pattern)
        assert sem_a_flag.fullmatch("٥") is not None
        assert MOLDE_DO_CAMBIO.fullmatch("٥") is None
