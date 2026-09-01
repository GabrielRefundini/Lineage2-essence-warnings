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
`limite_derivado_do_cruzamento` ja existe (`mercado_leitura.py:1027`) com a
derivacao escrita ao lado, e ela DISCRIMINA os dois casos dificeis conhecidos:

    133,33 / 66,66  ->  n=2  residuo=1   limite=1,0  ->  ACEITA (por IGUALDADE)
    13588  / 6750   ->  n=2  residuo=88  limite=1,0  ->  REJEITA

O caso bom passa por IGUALDADE, e nao por folga. E por isso que a comparacao e
`residuo <= limite`; com `<` o caso legitimo REPROVA e a Adena perde as ofertas
de preco quebrado. `TestOSinalDaComparacao` prende os dois lados disso.
"""

from __future__ import annotations

import pytest

from l2scanner import mercado_leitura
from l2scanner.mercado_leitura import (
    ADENA_POR_INCREMENTO,
    limite_derivado_do_cruzamento,
    quantidade_de_adena,
)


class TestOsDoisCasosDificeis:
    """O par que da valor um ao outro: eles discriminam em sentidos OPOSTOS."""

    def test_aceita_o_arredondamento_de_133_33_por_66_66(self) -> None:
        """A captura do usuario de 2026-09-01, 17h: 10M de adena por 133,33 XM.

        `round(13333 / 6666) = 2`, e `|13333 - 2 x 6666| = 1` contra o limite
        derivado `2 x 0,5 = 1,0`. PASSA RASPANDO: nao ha folga nenhuma aqui.
        """
        assert quantidade_de_adena(13333, 6666) == (10_000_000, 2)

    def test_rejeita_a_linha_5_da_fixtura(self) -> None:
        """`13588` por `6750`: a substituicao `0`x`8` que a fase existe para pegar.

        `round(13588 / 6750) = 2`, e `|13588 - 2 x 6750| = 88` contra o limite
        derivado `1,0`. Sem esta recusa a taxa `135,88` entraria no CSV.
        """
        assert quantidade_de_adena(13588, 6750) is None

    def test_a_aceitacao_do_caso_bom_e_por_IGUALDADE_e_nao_por_folga(self) -> None:
        """A conta explicita, para o proximo mantenedor nao supor que ha margem."""
        total, incremento, n = 13333, 6666, 2
        assert abs(total - n * incremento) == 1
        assert limite_derivado_do_cruzamento(n) == 1.0

    def test_a_recusa_do_caso_ruim_e_por_88_contra_1(self) -> None:
        """O controle negativo do teste acima: a distancia REAL entre os dois."""
        total, incremento, n = 13588, 6750, 2
        assert abs(total - n * incremento) == 88
        assert limite_derivado_do_cruzamento(n) == 1.0


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

    Com `<` no lugar do `<=`, o caso-bandeira `(13333, 6666)` — residuo 1 contra
    limite 1,0 — REPROVA, e a fase perde justamente a linha de arredondamento
    que o usuario capturou. O `<=` e o mesmo sentido que `_observar_o_cruzamento`
    ja usa (`mercado_leitura.py:1700`).
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
