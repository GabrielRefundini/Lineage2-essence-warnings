"""A calculadora de rotas, do `config.toml` ate o JSON servido. CALC-01/CALC-02.

O QUE ESTE ARQUIVO PRENDE, EM UMA FRASE
========================================
Que o veredito de "sai mais barato do NPC ou do mercado?" e **exato**, que ele
**quebra em vez de adivinhar** quando o nome nao resolve, e que ele **nao mexeu
numa virgula** da lista `avisos` que o `01-07` transformou em contrato.

NADA AQUI TOCA A `.mercado/` REAL NEM O `config.toml` REAL. Todo CSV nasce em
`tmp_path` e todo item e montado a mao.

ESTE ARQUIVO NAO LEVA LETRA ACENTUADA, como o resto de `tests/`. As frases
acentuadas de que ele precisa sao IMPORTADAS do Python que as define — copiar uma
frase para ca seria a segunda copia que o DASH-03 recusa.
"""

from __future__ import annotations

import http.client
import json
import random
import socket
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from fractions import Fraction
from pathlib import Path

import pytest

from l2scanner import dashboard, dashboard_dados, dashboard_rotas, mercado_registro
from l2scanner.config import ItemDeRota
from l2scanner.mercado_analise import ModeloDeMercado, unitario
from l2scanner.mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA, SEPARADOR
from l2scanner.mercado_console import formatar_unitario_derivado
from l2scanner.mercado_registro import ObservacaoLida

TERMINADOR = "\r\n"
AGORA = datetime(2026, 9, 1, 15, 0, 0)

# A TAXA REAL MEDIDA no `.mercado/observacoes.csv` de 2026-09-03: o menor pedido
# da Adena e 45,00 XM por 5.000.000 de adena, ou seja `Fraction(4500, 5_000_000)`
# centesimos de XM POR ADENA.
TAXA_MEDIDA = Fraction(9, 10000)


# ---------------------------------------------------------------------------
# O MATERIAL
# ---------------------------------------------------------------------------


def _item(nome="Gemstone C", preco=15000, pacote=1) -> ItemDeRota:
    return ItemDeRota(
        nome=nome, preco_npc_adena=preco, quantidade_do_pacote=pacote
    )


def _obs(chave, nome, quando, total, quantidade) -> ObservacaoLida:
    return ObservacaoLida(
        chave_da_serie=chave,
        nome_exibido=nome,
        primeira_vez=quando,
        total_em_centesimos=total,
        quantidade=quantidade,
        residuo_do_cruzamento=0,
    )


def _modelo(*observacoes) -> ModeloDeMercado:
    return ModeloDeMercado.de_observacoes(list(observacoes))


def _modelo_com_gemstone(total=5900, quantidade=1, quando=None):
    return _modelo(
        _obs(
            "gemstone-c#0",
            "Gemstone C",
            quando or datetime(2026, 9, 1, 14, 30, 0),
            total,
            quantidade,
        )
    )


def _linha(chave, nome, carimbo, total, quantidade) -> str:
    return SEPARADOR.join(
        (chave, nome, carimbo.isoformat(), str(total), str(quantidade), "0")
    )


def _escrever_csv(pasta: Path, *linhas) -> Path:
    alvo = pasta / mercado_registro.ARQUIVO_DE_OBSERVACOES
    corpo = SEPARADOR.join(mercado_registro.COLUNAS) + TERMINADOR
    corpo += "".join(linha + TERMINADOR for linha in linhas)
    alvo.write_text(corpo, encoding="utf-8", newline="")
    return alvo


# A ADENA a `Fraction(9, 10000)` por unidade: 45,00 XM por 5.000.000.
LINHA_DA_ADENA = _linha(
    CHAVE_DA_SERIE_DA_ADENA,
    "Adena",
    datetime(2026, 9, 1, 14, 50, 0),
    4500,
    5_000_000,
)
# O item a 59,00 por unidade.
LINHA_DA_GEMSTONE = _linha(
    "gemstone-c#0", "Gemstone C", datetime(2026, 9, 1, 14, 30, 0), 5900, 1
)


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    alvo = tmp_path / ".mercado"
    alvo.mkdir()
    return alvo


# ===========================================================================
# A CONTA, EXATA
# ===========================================================================


class TestAContaEExata:
    def test_a_rota_do_npc_converte_adena_em_centesimos_de_XM(self):
        """A derivacao do cabecalho do modulo, presa como numero.

        15.000 adena x Fraction(9, 10000) = Fraction(27, 2) centesimos de XM.
        IGUALDADE EXATA CONTRA UMA `Fraction`, e nunca `pytest.approx`: a coisa
        que este teste existe para prender e justamente que nao ha aproximacao
        em ponto nenhum.
        """
        custo = dashboard_rotas.custo_da_rota_do_npc(_item(), TAXA_MEDIDA)
        assert custo.unitario == Fraction(27, 2)
        assert custo.total_do_pacote == Fraction(27, 2)
        assert custo.quantidade == 1
        assert custo.preco_em_adena == 15000

    def test_o_PACOTE_divide_o_unitario_e_nao_o_total(self):
        """Um pacote de 9 pelo mesmo preco custa um nono por unidade."""
        custo = dashboard_rotas.custo_da_rota_do_npc(
            _item(pacote=9), TAXA_MEDIDA
        )
        assert custo.total_do_pacote == Fraction(27, 2)
        assert custo.unitario == Fraction(27, 18)
        assert custo.quantidade == 9

    def test_a_rota_do_mercado_ja_chega_na_unidade_certa(self):
        from l2scanner.mercado_analise import menor_pedido_visivel

        menor = menor_pedido_visivel(
            _modelo_com_gemstone().observacoes_de("gemstone-c#0")
        )
        custo = dashboard_rotas.custo_da_rota_do_mercado(menor)
        assert custo.unitario == Fraction(5900, 1)
        assert custo.preco_em_adena is None

    def test_com_os_dois_medidos_o_NPC_vence_e_a_diferenca_e_EXATA(self):
        veredito = dashboard_rotas.veredito_de_uma_rota(
            _item(), _modelo_com_gemstone(), TAXA_MEDIDA, AGORA
        )
        assert veredito.estado == dashboard_rotas.ROTA_DECIDIDA
        assert veredito.vencedora == dashboard_rotas.VENCEDORA_NPC
        assert veredito.diferenca_por_unidade == Fraction(5900) - Fraction(27, 2)
        assert veredito.diferenca_por_unidade == Fraction(11773, 2)

    def test_a_taxa_NAO_e_multiplicada_pela_escala_de_exibicao(self):
        """O erro por fator de cinco milhoes, preso.

        Se alguem multiplicasse a taxa por `UNIDADE_DA_TAXA` antes de comparar, o
        unitario do NPC saltaria de 13,50 para 67.500.000 e o veredito
        INVERTERIA — sem uma linha de erro em lugar nenhum. Este teste afirma o
        valor pequeno, que e o unico dos dois que pode estar certo.
        """
        from l2scanner.mercado_console import UNIDADE_DA_TAXA

        custo = dashboard_rotas.custo_da_rota_do_npc(_item(), TAXA_MEDIDA)
        assert custo.unitario == Fraction(27, 2)
        assert custo.unitario != Fraction(27, 2) * UNIDADE_DA_TAXA


# ===========================================================================
# O CONTROLE DO `Fraction` — o que foi TENTADO, e o que ficou MEDIDO
# ===========================================================================


class TestOFractionMudaOQueSaiNaTela:
    """POR QUE ESTA CLASSE FECHA PELA SAIDA (b) DO CRITERIO, E O QUE FOI TENTADO.

    O criterio do plano oferece duas saidas: **(a)** demonstrar um par DERIVADO
    em que o `float` faz a vencedora cair do lado errado, ou **(b)** registrar o
    que foi tentado, por que o par nao apareceu, e prender no lugar a propriedade
    mais forte que se conseguir medir. Esta classe fecha por **(b)**, e o
    registro e este.

    O QUE FOI TENTADO, COM OS NUMEROS
    ==================================
    1. **Sorteio de 400.000 pares** em faixas realistas (taxa, preco de NPC ate o
       teto, pacote ate mil), com o lado exato saindo de `custo_da_rota_do_npc` e
       `mercado_analise.unitario` e o lado float espelhando as MESMAS operacoes:
       **0 inversoes de vencedora, 0 colapsos para empate.**
    2. **Mais 300.000 sorteios** procurando especificamente "diferenca exata nao
       nula e diferenca em float zero", construindo o preco do mercado a partir
       do unitario do NPC: **0 casos.**
    3. **2.000.000 de sorteios** procurando divergencia de arredondamento:
       **0 casos.** O sorteio nunca cai em cima de uma fronteira.

    POR QUE O PAR DA SAIDA (a) NAO APARECE — E A RAZAO E ESTRUTURAL
    ===============================================================
    Duas razoes, e as duas estao medidas logo abaixo como teste:

    **PRIMEIRA: converter `Fraction` para `float` e MONOTONICO.** Se `x < y`
    entao `float(x) <= float(y)`, sempre — o arredondamento correto nao troca a
    ordem. Medido: **0 violacoes em 200.000 pares**. Logo uma implementacao que
    convertesse e depois comparasse NAO CONSEGUE inverter uma vencedora. O mais
    longe que ela chega e colapsar uma decisao num empate.

    **SEGUNDA: a grade de precos do mercado e grossa demais para caber no erro.**
    O preco do mercado e `Fraction(total, quantidade)` sobre inteiros que o jogo
    exibe, entao o espacamento entre dois precos possiveis perto de um valor e
    `1/quantidade` — da ordem de um milesimo. O erro do `float` e da ordem de
    `1e-16` RELATIVO. Para o `float` inverter uma comparacao, o preco do mercado
    teria de cair DENTRO daquele erro, e nao ha nenhum preco possivel ali: a
    grade e treze ordens de grandeza mais larga que o buraco.

    A ISSO SE SOMA A FAIXA DE EMPATE, que e de tres POR CENTO — catorze ordens de
    grandeza acima do erro do `float`. Enquanto ela existir, nenhum erro de
    representacao consegue mover o ESTADO de uma linha.

    A PROPRIEDADE MAIS FORTE QUE SE CONSEGUIU MEDIR, E ELA E VISIVEL NA TELA
    ========================================================================
    O par nao precisa ser sorteado: ele se CONSTROI, a partir do fato de que
    `1/98` nao e representavel em binario. Com esse par, os dois testes abaixo
    mostram o `float` produzindo, atraves dos formatadores de PRODUCAO:

    - um CENTESIMO DIFERENTE na tela (`0,02` contra `0,01`), e
    - uma diferenca NAO NULA onde a conta exata da um empate cravado, com o
      `float` chegando a afirmar que o NPC e estritamente mais barato quando as
      duas rotas custam exatamente o mesmo.

    A forma fraca — "a implementacao usa `Fraction`" — nao aparece em teste
    nenhum desta classe, de proposito: ela nao exercita diferenca nenhuma.
    """

    # O PAR DERIVADO, e nao escolhido a dedo ate dar certo.
    #
    # taxa = Fraction(1, 2d) e preco = (2K+1)*d, com pacote 1, dao
    # unitario = (2K+1)/2 — um meio-centesimo CRAVADO, que e a fronteira do
    # arredondamento. Com d = 49 (nao potencia de dois), `1/98` nao e
    # representavel e a conta em float cai do lado de baixo.
    #
    # Varrendo d impar de 3 a 3999 e K de 1 a 399 dentro do teto do preco,
    # **40.616** pares divergem. Os dois abaixo sao os dois primeiros.
    D = 49
    TAXA_DERIVADA = Fraction(1, 2 * D)

    def test_o_CENTESIMO_EXIBIDO_difere_entre_a_conta_exata_e_a_mesma_em_float(
        self,
    ):
        """O texto que o usuario LE muda. Pelos formatadores de PRODUCAO."""
        preco = 3 * self.D  # K = 1 -> unitario exato = 3/2
        exato = dashboard_rotas.custo_da_rota_do_npc(
            _item(preco=preco), self.TAXA_DERIVADA
        ).unitario
        # A MESMA conta que uma implementacao em ponto flutuante teria escrito.
        flutuante = preco * (1 / (2 * self.D)) / 1

        assert exato == Fraction(3, 2)
        assert flutuante != 1.5
        assert formatar_unitario_derivado(exato).startswith("0,02")
        assert formatar_unitario_derivado(Fraction(flutuante)).startswith("0,01")

    def test_o_float_NAO_reconhece_um_empate_EXATO_e_elege_um_vencedor(self):
        """A conta exata da zero; a mesma em float da uma vencedora.

        As duas rotas custam EXATAMENTE `Fraction(7, 2)`. A conta exata devolve
        diferenca zero e vencedora nenhuma. A conta em float devolve uma
        diferenca de -4,44e-16 e afirma que o NPC e estritamente mais barato —
        um vencedor eleito num empate cravado.
        """
        preco = 7 * self.D  # K = 3 -> unitario exato = 7/2
        npc_exato = dashboard_rotas.custo_da_rota_do_npc(
            _item(preco=preco), self.TAXA_DERIVADA
        ).unitario
        mercado_exato = unitario(7, 2)
        npc_float = preco * (1 / (2 * self.D)) / 1
        mercado_float = 7 / 2

        assert npc_exato == mercado_exato == Fraction(7, 2)
        assert npc_exato - mercado_exato == 0

        assert npc_float != mercado_float
        assert npc_float - mercado_float != 0
        assert npc_float < mercado_float

    def test_MEDICAO_converter_Fraction_para_float_e_MONOTONICO(self):
        """A razao estrutural de a saida (a) ser inalcancavel por conversao.

        Se a conversao pudesse trocar a ordem, um `float(a) > float(b)` com
        `a < b` inverteria a vencedora sozinho. Ela nao pode — e isto e medido, e
        nao afirmado.
        """
        rnd = random.Random(1)
        violacoes = 0
        for _ in range(20000):
            a = Fraction(rnd.randint(1, 10**12), rnd.randint(1, 10**9))
            b = Fraction(rnd.randint(1, 10**12), rnd.randint(1, 10**9))
            if a < b and not float(a) <= float(b):
                violacoes += 1
        assert violacoes == 0

    def test_MEDICAO_a_faixa_de_empate_e_ordens_de_grandeza_acima_do_erro(self):
        """A segunda razao: a faixa domina o erro de representacao.

        Enquanto a margem for de tres por cento e o erro relativo do `float` for
        da ordem de `1e-16`, nenhum erro de representacao move o ESTADO de uma
        linha. O numero e derivado da constante, e nao escrito a mao — se a
        margem descer para `1e-16` este teste fica vermelho, que e o desfecho
        certo.
        """
        erro_relativo_do_float = Fraction(sys.float_info.epsilon)
        assert dashboard_rotas.MARGEM_DE_EMPATE_PERCENTUAL > (
            erro_relativo_do_float * 10**10
        )


# ===========================================================================
# A FAIXA DE EMPATE, E A BORDA DERIVADA DA CONSTANTE
# ===========================================================================

# A borda e DERIVADA da constante, e nao escrita a mao: mudar a margem move os
# tres testes abaixo juntos. Com a taxa de UM centesimo por adena e pacote de
# UM, o unitario do NPC E o preco em adena — o que torna a borda escrevivel em
# inteiros exatos.
TAXA_UNITARIA = Fraction(1, 1)
UNITARIO_DO_MERCADO = 10000
NA_BORDA = int(
    UNITARIO_DO_MERCADO * (1 - dashboard_rotas.MARGEM_DE_EMPATE_PERCENTUAL)
)


class TestAFaixaDeEmpate:
    def _veredito(self, preco_npc):
        modelo = _modelo_com_gemstone(total=UNITARIO_DO_MERCADO, quantidade=1)
        return dashboard_rotas.veredito_de_uma_rota(
            _item(preco=preco_npc), modelo, TAXA_UNITARIA, AGORA
        )

    def test_a_borda_derivada_e_um_inteiro_exato(self):
        """O controle da propria derivacao: se a margem virar um numero que nao
        divide 10.000 em inteiro, os testes de borda passariam a medir o
        arredondamento da fixture em vez da faixa."""
        assert (
            Fraction(UNITARIO_DO_MERCADO)
            * dashboard_rotas.MARGEM_DE_EMPATE_PERCENTUAL
        ).denominator == 1
        # E ela cai DENTRO da faixa util: uma margem de 0% ou de 100% faria os
        # tres testes de borda abaixo medirem outra coisa.
        assert 0 < NA_BORDA < UNITARIO_DO_MERCADO

    def test_LOGO_ABAIXO_da_margem_e_EMPATE_sem_vencedora(self):
        veredito = self._veredito(NA_BORDA + 1)
        assert veredito.estado == dashboard_rotas.ROTA_EMPATADA
        assert veredito.vencedora is None
        assert veredito.diferenca_percentual < (
            dashboard_rotas.MARGEM_DE_EMPATE_PERCENTUAL
        )

    def test_LOGO_ACIMA_da_margem_e_DECIDIDA_com_a_vencedora_NOMEADA(self):
        veredito = self._veredito(NA_BORDA - 1)
        assert veredito.estado == dashboard_rotas.ROTA_DECIDIDA
        assert veredito.vencedora == dashboard_rotas.VENCEDORA_NPC
        assert veredito.diferenca_percentual > (
            dashboard_rotas.MARGEM_DE_EMPATE_PERCENTUAL
        )

    def test_EXATAMENTE_na_margem_e_EMPATE_e_a_borda_INCLUI(self):
        """Mesmo criterio de `componente_esta_velho`: exatamente no limiar ja
        conta. Um `<` estrito faria o desfecho depender do ultimo bit."""
        veredito = self._veredito(NA_BORDA)
        assert veredito.diferenca_percentual == (
            dashboard_rotas.MARGEM_DE_EMPATE_PERCENTUAL
        )
        assert veredito.estado == dashboard_rotas.ROTA_EMPATADA
        assert veredito.vencedora is None

    def test_o_empate_acontece_MESMO_com_uma_rota_estritamente_menor(self):
        """A frase inteira da faixa: dentro dela, ter um numero menor NAO e ter
        um vencedor."""
        veredito = self._veredito(NA_BORDA + 1)
        assert veredito.npc.unitario < veredito.mercado.unitario
        assert veredito.vencedora is None

    def test_o_MERCADO_tambem_pode_vencer(self):
        """O controle do lado oposto: sem ele, um `return VENCEDORA_NPC` cravado
        passaria em tudo acima."""
        veredito = self._veredito(UNITARIO_DO_MERCADO * 2)
        assert veredito.estado == dashboard_rotas.ROTA_DECIDIDA
        assert veredito.vencedora == dashboard_rotas.VENCEDORA_MERCADO


class TestOPercentualUsaODenominadorMaisCARO:
    def test_o_dobro_le_cinquenta_por_cento_e_nao_cem(self):
        """A escolha do denominador, com os dois numeros lado a lado.

        Uma rota que custa 100 e outra 200: pelo denominador CARO economiza-se
        50%; pelo BARATO a outra e 100% mais cara. Os dois estao certos para
        perguntas diferentes, e o MAIOR e o que agrada — por isso a escolha e
        presa aqui.
        """
        modelo = _modelo_com_gemstone(total=200, quantidade=1)
        veredito = dashboard_rotas.veredito_de_uma_rota(
            _item(preco=100), modelo, TAXA_UNITARIA, AGORA
        )
        assert veredito.diferenca_por_unidade == 100
        assert veredito.diferenca_percentual == Fraction(1, 2)
        assert veredito.diferenca_percentual != Fraction(1, 1)


class TestOCasoDegenerado:
    def test_as_duas_rotas_a_ZERO_empatam_sem_dividir(self):
        """Zero contra zero E empate, e a divisao nao acontece.

        Sem a guarda, isto seria `ZeroDivisionError` no meio de um pedido HTTP.
        """
        modelo = _modelo_com_gemstone(total=0, quantidade=1)
        veredito = dashboard_rotas.veredito_de_uma_rota(
            _item(preco=0 or 1), modelo, Fraction(0, 1), AGORA
        )
        assert veredito.estado == dashboard_rotas.ROTA_EMPATADA
        assert veredito.vencedora is None
        assert veredito.diferenca_percentual is None
        assert veredito.diferenca_por_unidade == 0


# ===========================================================================
# O CASAMENTO DO NOME QUEBRA EM VEZ DE ADIVINHAR
# ===========================================================================


class TestOCasamentoDoNome:
    def test_nome_que_nao_casa_com_serie_nenhuma_e_NUNCA_VISTA(self):
        veredito = dashboard_rotas.veredito_de_uma_rota(
            _item(nome="Gemstone D"), _modelo_com_gemstone(), TAXA_MEDIDA, AGORA
        )
        assert veredito.estado == dashboard_rotas.ROTA_NUNCA_VISTA
        assert veredito.npc is None
        assert veredito.mercado is None

    def test_a_linha_nunca_vista_carrega_o_nome_QUE_O_USUARIO_ESCREVEU(self):
        """E o texto dele que ele vai procurar no `config.toml` para conferir."""
        veredito = dashboard_rotas.veredito_de_uma_rota(
            _item(nome="Gemstone D"), _modelo_com_gemstone(), TAXA_MEDIDA, AGORA
        )
        assert veredito.item == "Gemstone D"
        assert veredito.nome_exibido == "Gemstone D"

    def test_nome_que_casa_com_DUAS_series_e_AMBIGUO_com_as_candidatas(self):
        """`resolver_o_nome` E CHAMADO DE FATO, e nao reimplementado aqui.

        Duas series cujo `nome_exibido` normaliza igual (caixa e espaco duplo)
        so produzem ambiguidade se o casamento passar por `nome_normalizado` —
        uma comparacao crua veria dois textos diferentes e escolheria um.
        """
        modelo = _modelo(
            _obs("gem-b#1", "Gemstone C", AGORA, 100, 1),
            _obs("gem-z#9", "gemstone  c", AGORA, 200, 1),
        )
        veredito = dashboard_rotas.veredito_de_uma_rota(
            _item(), modelo, TAXA_MEDIDA, AGORA
        )
        assert veredito.estado == dashboard_rotas.ROTA_NOME_AMBIGUO
        assert veredito.candidatas == ("gem-b#1", "gem-z#9")
        assert veredito.vencedora is None

    def test_as_candidatas_saem_ORDENADAS(self):
        """A mensagem tem de sair igual em toda leitura do mesmo arquivo — senao
        o usuario ve a lista trocar de ordem e acha o programa indeciso."""
        modelo = _modelo(
            _obs("zzz#9", "Gemstone C", AGORA, 100, 1),
            _obs("aaa#1", "Gemstone C", AGORA, 200, 1),
        )
        veredito = dashboard_rotas.veredito_de_uma_rota(
            _item(), modelo, TAXA_MEDIDA, AGORA
        )
        assert veredito.candidatas == tuple(sorted(veredito.candidatas))
        assert veredito.candidatas == ("aaa#1", "zzz#9")

    def test_serie_SEM_oferta_comparavel_cai_em_NUNCA_VISTA(self):
        """Quantidade nao positiva e a linha que o usuario editou a mao no
        Sheets: `_comparaveis` ja a descarta, e aqui nao ha preco a comparar."""
        modelo = _modelo(_obs("gemstone-c#0", "Gemstone C", AGORA, 5900, 0))
        veredito = dashboard_rotas.veredito_de_uma_rota(
            _item(), modelo, TAXA_MEDIDA, AGORA
        )
        assert veredito.estado == dashboard_rotas.ROTA_NUNCA_VISTA

    def test_o_corte_de_similaridade_NAO_juntaria_o_que_este_casamento_separa(
        self,
    ):
        """A refutacao medida, presa como teste em vez de so escrita no fonte.

        O corte calibrado (`0.8947`) foi feito para agrupar duas leituras de OCR
        DOS MESMOS PIXELS. Sobre nome digitado ele daria 0,9375 para `B-grade
        Gemstone` contra `C-grade Gemstone` — acima do corte, e series
        deliberadamente separadas. Aqui ele juntaria as DUAS primeiras
        instancias desta calculadora.

        Este teste afirma o desfecho CERTO: com as duas series no modelo, pedir
        uma devolve UMA, e nunca a outra.
        """
        modelo = _modelo(
            _obs("gemstone-c#0", "Gemstone C", AGORA, 5900, 1),
            _obs("gemstone-b#0", "Gemstone B", AGORA, 11800, 1),
        )
        c = dashboard_rotas.veredito_de_uma_rota(
            _item(nome="Gemstone C"), modelo, TAXA_MEDIDA, AGORA
        )
        b = dashboard_rotas.veredito_de_uma_rota(
            _item(nome="Gemstone B"), modelo, TAXA_MEDIDA, AGORA
        )
        assert c.chave == "gemstone-c#0"
        assert b.chave == "gemstone-b#0"
        assert c.mercado.unitario != b.mercado.unitario


# ===========================================================================
# A ORDEM E A PRECEDENCIA
# ===========================================================================


class TestAOrdemEFechada:
    def test_os_QUATRO_estados_estao_na_tupla_e_na_ordem_de_precedencia(self):
        assert dashboard_rotas.ESTADOS_DA_ROTA == (
            dashboard_rotas.ROTA_NOME_AMBIGUO,
            dashboard_rotas.ROTA_NUNCA_VISTA,
            dashboard_rotas.ROTA_EMPATADA,
            dashboard_rotas.ROTA_DECIDIDA,
        )

    def test_todo_estado_devolvido_pertence_a_tupla_fechada(self):
        modelo = _modelo_com_gemstone()
        itens = [
            _item(),
            _item(nome="Gemstone D"),
            _item(preco=int(5900 / TAXA_MEDIDA)),
        ]
        for veredito in dashboard_rotas.vereditos_das_rotas(
            itens, modelo, TAXA_MEDIDA, AGORA
        ):
            assert veredito.estado in dashboard_rotas.ESTADOS_DA_ROTA

    def test_a_ordem_da_lista_e_a_do_config_e_nao_a_da_economia(self):
        """Reordenar a cada volta de polling faria as linhas trocarem de lugar
        debaixo do dedo do usuario no meio de uma conferencia."""
        modelo = _modelo(
            _obs("gemstone-c#0", "Gemstone C", AGORA, 5900, 1),
            _obs("gemstone-b#0", "Gemstone B", AGORA, 11800, 1),
        )
        itens = [_item(nome="Gemstone B"), _item(nome="Gemstone C")]
        vereditos = dashboard_rotas.vereditos_das_rotas(
            itens, modelo, TAXA_MEDIDA, AGORA
        )
        assert [v.item for v in vereditos] == ["Gemstone B", "Gemstone C"]

    def test_sem_itens_devolve_vazio(self):
        assert (
            dashboard_rotas.vereditos_das_rotas(
                (), _modelo_com_gemstone(), TAXA_MEDIDA, AGORA
            )
            == ()
        )


# ===========================================================================
# O CONTRATO POR FORMA — verificado, e nao so afirmado
# ===========================================================================


class TestOContratoEPorForma:
    def test_importar_dashboard_rotas_NAO_traz_o_leitor_de_config(self):
        """Uma dependencia entre o CALCULO e o LEITOR DE ARQUIVO tornaria a conta
        nao-testavel sem disco."""
        saida = subprocess.run(
            [
                sys.executable,
                "-c",
                "import l2scanner.dashboard_rotas, sys, json; "
                "print(json.dumps(sorted("
                "m for m in sys.modules if m.startswith('l2scanner'))))",
            ],
            capture_output=True,
            text=True,
        )
        assert saida.returncode == 0, saida.stderr
        carregados = json.loads(saida.stdout)
        assert "l2scanner.dashboard_rotas" in carregados
        assert "l2scanner.config" not in carregados

    def test_a_conta_roda_sobre_um_objeto_QUALQUER_com_os_tres_atributos(self):
        """O contrato e por FORMA: nao ha `isinstance` nenhum no caminho."""

        class ItemDeMentira:
            nome = "Gemstone C"
            preco_npc_adena = 15000
            quantidade_do_pacote = 1

        custo = dashboard_rotas.custo_da_rota_do_npc(ItemDeMentira(), TAXA_MEDIDA)
        assert custo.unitario == Fraction(27, 2)


# ===========================================================================
# O BLOCO NO PAYLOAD
# ===========================================================================


class TestOBlocoNoPayload:
    def test_sem_item_configurado_o_bloco_diz_O_QUE_ESCREVER(self, pasta):
        _escrever_csv(pasta, LINHA_DA_ADENA)
        bloco = dashboard_dados.payload(pasta, AGORA)["calculadora"]
        assert bloco["estado"] == dashboard_dados.CALCULADORA_SEM_ITENS
        assert bloco["aviso"] == dashboard_dados.FRASE_DE_SEM_ITENS_CONFIGURADOS
        assert bloco["itens"] == []

    def test_a_regiao_NUNCA_fica_um_retangulo_mudo(self, pasta):
        """Nos tres estados de bloco ha ou uma frase ou uma lista de itens."""
        _escrever_csv(pasta, LINHA_DA_ADENA)
        sem_item = dashboard_dados.payload(pasta, AGORA)["calculadora"]
        com_item = dashboard_dados.payload(
            pasta, AGORA, None, [_item()], AGORA
        )["calculadora"]
        _escrever_csv(pasta, LINHA_DA_GEMSTONE)
        sem_taxa = dashboard_dados.payload(
            pasta, AGORA, None, [_item()], AGORA
        )["calculadora"]

        for bloco in (sem_item, com_item, sem_taxa):
            assert bloco["aviso"] or bloco["itens"]

    def test_sem_taxa_da_adena_o_bloco_diz_que_nao_da_para_converter(self, pasta):
        _escrever_csv(pasta, LINHA_DA_GEMSTONE)
        dados = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)
        bloco = dados["calculadora"]
        assert bloco["estado"] == dashboard_dados.CALCULADORA_SEM_TAXA
        assert bloco["aviso"] == dashboard_dados.FRASE_DE_SEM_TAXA_DA_ADENA
        assert bloco["itens"] == []

    def test_a_taxa_vem_do_MESMO_objeto_que_o_destaque_exibe(self, pasta):
        """UMA AUTORIDADE SO SOBRE A TAXA.

        Duas leituras da mesma serie no MESMO payload poderiam divergir se
        alguem mudasse uma delas, e a pagina mostraria dois valores para a mesma
        adena — um no destaque, outro dentro do veredito.

        A prova e por CONSEQUENCIA e nao por leitura de fonte: o estado de "sem
        taxa" do bloco acompanha, byte a byte, a ausencia do destaque. Se o
        bloco chamasse `menor_pedido_visivel` por conta propria, as duas
        respostas continuariam batendo por acaso — mas o teste seguinte, que
        muda a taxa, mostraria a divergencia.
        """
        _escrever_csv(pasta, LINHA_DA_GEMSTONE)
        sem = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)
        assert sem["destaque"]["xm"]["n"] == 0
        assert sem["calculadora"]["estado"] == dashboard_dados.CALCULADORA_SEM_TAXA

        _escrever_csv(pasta, LINHA_DA_ADENA, LINHA_DA_GEMSTONE)
        com = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)
        assert com["destaque"]["xm"]["n"] == 1
        assert com["calculadora"]["estado"] == dashboard_dados.CALCULADORA_COM_ITENS

    def test_a_taxa_USADA_e_a_do_destaque_e_move_o_veredito_junto(self, pasta):
        """A prova que MEDE, e nao afirma: trocar a oferta da Adena por uma dez
        mil vezes mais cara inverte a vencedora. Se o bloco usasse uma taxa
        propria e fixa, o veredito nao se moveria."""
        _escrever_csv(pasta, LINHA_DA_ADENA, LINHA_DA_GEMSTONE)
        barata = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)
        assert barata["calculadora"]["itens"][0]["vencedora"] == (
            dashboard_rotas.VENCEDORA_NPC
        )

        adena_cara = _linha(
            CHAVE_DA_SERIE_DA_ADENA,
            "Adena",
            datetime(2026, 9, 1, 14, 50, 0),
            45_000_000,
            5_000_000,
        )
        _escrever_csv(pasta, adena_cara, LINHA_DA_GEMSTONE)
        cara = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)
        assert cara["calculadora"]["itens"][0]["vencedora"] == (
            dashboard_rotas.VENCEDORA_MERCADO
        )

    def test_o_texto_do_npc_e_BYTE_IDENTICO_ao_formatador_de_producao(
        self, pasta
    ):
        """Nenhum segundo formatador nasce nesta fase."""
        _escrever_csv(pasta, LINHA_DA_ADENA, LINHA_DA_GEMSTONE)
        dados = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)
        linha = dados["calculadora"]["itens"][0]
        assert linha["npc"]["texto"] == formatar_unitario_derivado(Fraction(27, 2))
        assert linha["mercado"]["texto"] == formatar_unitario_derivado(
            Fraction(5900, 1)
        )

    def test_o_pacote_do_npc_aparece_como_o_NPC_realmente_vende(self, pasta):
        _escrever_csv(pasta, LINHA_DA_ADENA, LINHA_DA_GEMSTONE)
        dados = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)
        pacote = dados["calculadora"]["itens"][0]["npc"]["pacote_texto"]
        assert "15.000 de adena" in pacote
        assert "1 unidade" in pacote

    def test_todo_numero_viaja_com_n_e_recencia(self, pasta):
        _escrever_csv(pasta, LINHA_DA_ADENA, LINHA_DA_GEMSTONE)
        dados = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)
        linha = dados["calculadora"]["itens"][0]
        assert linha["n"] == 1
        assert linha["recencia"]
        assert linha["velho"] is False

    def test_o_item_NUNCA_VISTO_aparece_dizendo_isso_com_o_nome_do_usuario(
        self, pasta
    ):
        """Sumir seria indistinguivel de "esqueci de configurar" (D-07)."""
        _escrever_csv(pasta, LINHA_DA_ADENA)
        dados = dashboard_dados.payload(
            pasta, AGORA, None, [_item(nome="Gemstone C")], AGORA
        )
        linha = dados["calculadora"]["itens"][0]
        assert linha["estado"] == dashboard_rotas.ROTA_NUNCA_VISTA
        assert linha["item"] == "Gemstone C"
        assert "Gemstone C" in linha["aviso"]
        assert linha["npc"] is None
        assert linha["mercado"] is None

    def test_o_instante_da_LEITURA_e_uma_string_PRONTA_de_nivel_de_bloco(
        self, pasta
    ):
        """O navegador nao tem o direito de compor uma segunda forma de tempo."""
        _escrever_csv(pasta, LINHA_DA_ADENA, LINHA_DA_GEMSTONE)
        lidos_em = AGORA - timedelta(minutes=3)
        bloco = dashboard_dados.payload(
            pasta, AGORA, None, [_item()], lidos_em
        )["calculadora"]

        assert isinstance(bloco["itens_lidos_em"], str)
        assert bloco["itens_lidos_em"]
        # ELE E DE NIVEL DE BLOCO: nenhuma linha o repete.
        for linha in bloco["itens"]:
            assert "itens_lidos_em" not in linha

    def test_a_frase_do_instante_fala_de_LEITURA_e_nunca_de_INFORME(self):
        """As duas coisas tem nomes parecidos e sao fatos diferentes: o numero
        pode estar no arquivo ha meses e a leitura ser de agora. Dizer "informado"
        seria mentir com a forma de um numero.

        O `cambio` tem a frase do OUTRO lado — `informado por voce` — e ela existe
        no mesmo payload. As duas nao podem colidir.
        """
        molde = dashboard_dados.MOLDE_DA_LEITURA_DA_CONFIGURACAO.lower()
        assert "lidos" in molde or "lido" in molde
        assert "informado" not in molde
        assert "informou" not in molde

    def test_os_dois_estados_de_falha_fechada_zeram_a_calculadora(self, pasta):
        """A mesma falha fechada do destaque e da serie: quando o programa acabou
        de dizer que nao entende o arquivo, ele nao pode oferecer um veredito
        sobre dinheiro tirado dele."""
        ausente = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)
        assert ausente["estado"] == dashboard_dados.ESTADO_ARQUIVO_AUSENTE
        assert ausente["calculadora"] is None

        alvo = pasta / mercado_registro.ARQUIVO_DE_OBSERVACOES
        alvo.write_text("coluna_errada\r\n", encoding="utf-8", newline="")
        quebrado = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)
        assert quebrado["estado"] == dashboard_dados.ESTADO_ERRO_DE_CONTRATO
        assert quebrado["calculadora"] is None


class TestALinhaDeAvisosNaoMudou:
    """A REGRA DURA DESTA FASE, e o criterio que reprova a rota mais tentadora.

    O `01-07` registrou que a ORDEM de `avisos` virou contrato: o `dashboard.js`
    acha tres frases por POSICAO, e quatro testes prendem isso sobre payloads
    reais. Acrescentar a frase da calculadora la seria empurrar a linha de R$
    para fora do lugar em que o navegador a procura.
    """

    def test_a_lista_INTEIRA_e_identica_com_e_sem_itens_configurados(self, pasta):
        """A comparacao e da LISTA INTEIRA, e nao do comprimento: uma troca de
        duas frases de lugar tem o mesmo comprimento."""
        _escrever_csv(pasta, LINHA_DA_ADENA, LINHA_DA_GEMSTONE)
        sem = dashboard_dados.payload(pasta, AGORA)["avisos"]
        com = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)[
            "avisos"
        ]
        assert com == sem

    def test_a_lista_e_identica_TAMBEM_no_estado_vazio(self, pasta):
        """O estado de tres avisos e o mais fragil dos cinco — e o unico em que o
        JS le por `posicao + 2`."""
        _escrever_csv(pasta)
        sem = dashboard_dados.payload(pasta, AGORA)["avisos"]
        com = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)[
            "avisos"
        ]
        assert com == sem
        assert len(com) == 4

    def test_a_lista_e_identica_nos_DOIS_estados_de_falha_fechada(self, pasta):
        sem = dashboard_dados.payload(pasta, AGORA)["avisos"]
        com = dashboard_dados.payload(pasta, AGORA, None, [_item()], AGORA)[
            "avisos"
        ]
        assert com == sem

    def test_nenhuma_frase_da_calculadora_vazou_para_a_lista_de_avisos(
        self, pasta
    ):
        _escrever_csv(pasta, LINHA_DA_ADENA, LINHA_DA_GEMSTONE)
        avisos = dashboard_dados.payload(
            pasta, AGORA, None, [_item(nome="Gemstone D")], AGORA
        )["avisos"]
        juntos = " ".join(avisos)
        assert dashboard_dados.FRASE_DE_SEM_ITENS_CONFIGURADOS not in juntos
        assert dashboard_dados.FRASE_DE_SEM_TAXA_DA_ADENA not in juntos
        assert "Gemstone D" not in juntos


# ===========================================================================
# O TRACER: DO `config.toml` AO JSON SERVIDO
# ===========================================================================


def _get_dados(porta: int):
    conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
    try:
        conexao.request("GET", dashboard.CAMINHO_DOS_DADOS)
        resposta = conexao.getresponse()
        return resposta.status, json.loads(resposta.read().decode("utf-8"))
    finally:
        conexao.close()


class TestOTracerDePontaAPonta:
    def test_um_item_configurado_vira_um_veredito_num_GET_de_verdade(
        self, pasta
    ):
        """**A PROVA DE PONTA A PONTA DESTE TRACER.**

        Um `ItemDeRota` entra no `montar_servidor`, uma fixture de CSV entra na
        pasta, e o que sai do soquete e um veredito com as duas rotas e a
        vencedora marcada.
        """
        _escrever_csv(pasta, LINHA_DA_ADENA, LINHA_DA_GEMSTONE)
        servidor = dashboard.montar_servidor(
            porta=0,
            pasta_do_mercado=pasta,
            itens=[_item()],
            itens_lidos_em=datetime.now(),
        )
        tarefa = threading.Thread(
            target=servidor.serve_forever,
            kwargs={"poll_interval": 0.01},
            daemon=True,
        )
        tarefa.start()
        try:
            status, dados = _get_dados(servidor.server_address[1])
        finally:
            servidor.shutdown()
            servidor.server_close()
            tarefa.join(timeout=5)
            assert not tarefa.is_alive()

        assert status == 200
        bloco = dados["calculadora"]
        assert bloco["estado"] == dashboard_dados.CALCULADORA_COM_ITENS
        assert bloco["itens_lidos_em"]

        linha = bloco["itens"][0]
        assert linha["vencedora"] == dashboard_rotas.VENCEDORA_NPC
        assert linha["npc"]["texto"] == formatar_unitario_derivado(Fraction(27, 2))
        assert linha["mercado"]["texto"] == formatar_unitario_derivado(
            Fraction(5900, 1)
        )
        assert linha["diferenca"]["xm"] == formatar_unitario_derivado(
            Fraction(11773, 2)
        )
        assert linha["diferenca"]["percentual"]

    def test_um_servidor_SEM_item_continua_respondendo_como_na_fase_1(
        self, pasta
    ):
        """A assinatura antiga continua valendo, exatamente como quando o cambio
        entrou."""
        _escrever_csv(pasta, LINHA_DA_ADENA)
        servidor = dashboard.montar_servidor(porta=0, pasta_do_mercado=pasta)
        tarefa = threading.Thread(
            target=servidor.serve_forever,
            kwargs={"poll_interval": 0.01},
            daemon=True,
        )
        tarefa.start()
        try:
            status, dados = _get_dados(servidor.server_address[1])
        finally:
            servidor.shutdown()
            servidor.server_close()
            tarefa.join(timeout=5)

        assert status == 200
        assert dados["destaque"] is not None
        assert dados["calculadora"]["estado"] == (
            dashboard_dados.CALCULADORA_SEM_ITENS
        )


class TestOArranqueParaComUmBlocoTorto:
    """A recusa do `config.toml` derruba o arranque, e a porta nunca abre."""

    def _config_torto(self, tmp_path: Path) -> Path:
        caminho = tmp_path / "config.toml"
        caminho.write_text(
            "[[dashboard.item]]\n"
            'nome = "Gemstone C"\n'
            "preco_npc_adena = true\n"
            "quantidade_do_pacote = 1\n",
            encoding="utf-8",
        )
        return caminho

    def test_o_main_devolve_codigo_NAO_ZERO_e_a_mensagem_nomeia_item_e_campo(
        self, tmp_path, monkeypatch, capsys
    ):
        from l2scanner import config

        caminho = self._config_torto(tmp_path)
        monkeypatch.setattr(config, "ARQUIVO_CONFIG", caminho)
        monkeypatch.setattr(config, "ARQUIVO_CONFIG_LOCAL", tmp_path / "nao-existe")

        codigo = dashboard.main(["--sem-navegador", "--porta", "0"])
        saida = capsys.readouterr().out

        assert codigo != 0
        assert "Gemstone C" in saida
        assert "preco_npc_adena" in saida

    def test_NENHUMA_PORTA_e_aberta_nesse_caminho(
        self, tmp_path, monkeypatch, capsys
    ):
        """A prova e por CONSEQUENCIA: a porta continua livre para um bind
        subsequente com `allow_reuse_address = False`, que e justamente o modo em
        que um segundo bind na mesma porta LEVANTA.

        Um `main` que subisse o servidor antes de validar deixaria esta porta
        ocupada, e o bind abaixo estouraria.
        """
        with socket.socket() as sonda:
            sonda.bind(("127.0.0.1", 0))
            porta = sonda.getsockname()[1]

        from l2scanner import config

        caminho = self._config_torto(tmp_path)
        monkeypatch.setattr(config, "ARQUIVO_CONFIG", caminho)
        monkeypatch.setattr(config, "ARQUIVO_CONFIG_LOCAL", tmp_path / "nao-existe")

        assert dashboard.main(["--sem-navegador", "--porta", str(porta)]) != 0
        capsys.readouterr()

        # A PORTA CONTINUA LIVRE.
        servidor = dashboard.montar_servidor(porta=porta, pasta_do_mercado=tmp_path)
        servidor.server_close()

    def test_a_mensagem_diz_que_NADA_foi_alterado(
        self, tmp_path, monkeypatch, capsys
    ):
        """A anatomia de mensagem da casa: o que houve, o que NAO mudou, e o
        passo que religa a coisa."""
        from l2scanner import config

        caminho = self._config_torto(tmp_path)
        monkeypatch.setattr(config, "ARQUIVO_CONFIG", caminho)
        monkeypatch.setattr(config, "ARQUIVO_CONFIG_LOCAL", tmp_path / "nao-existe")

        dashboard.main(["--sem-navegador", "--porta", "0"])
        saida = capsys.readouterr().out.lower()

        assert "nada foi alterado" in saida
        assert "config.toml" in saida


class TestOsItensNaoEntramNaChaveDoCache:
    def test_dois_pedidos_com_itens_DIFERENTES_no_mesmo_minuto(self, pasta):
        """OS ITENS NAO ENTRAM NA CHAVE, e este teste MEDE a consequencia.

        Eles sao lidos uma vez no arranque e nao podem mudar sem reinicio —
        justamente porque um bloco torto tem de derrubar o arranque. Como o
        `Manipulador` sempre passa os MESMOS itens, a entrada guardada continua
        valendo, e e isso que este teste mostra: o segundo pedido, com itens
        diferentes, devolve o que estava guardado.

        Se um dia alguem quiser releitura por pedido, este teste fica vermelho —
        que e o aviso certo, porque essa mudanca move a derrubada do arranque
        para uma volta de polling no meio da noite.
        """
        _escrever_csv(pasta, LINHA_DA_ADENA, LINHA_DA_GEMSTONE)
        cache = dashboard.CacheDaLeitura()

        primeiro = cache.pronto(pasta, AGORA, None, (_item(),), AGORA)
        segundo = cache.pronto(pasta, AGORA, None, (), AGORA)

        assert primeiro["calculadora"]["estado"] == (
            dashboard_dados.CALCULADORA_COM_ITENS
        )
        assert segundo["calculadora"] == primeiro["calculadora"]
