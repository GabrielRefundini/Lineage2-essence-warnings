"""A PROVA de que trocar a escala de exibicao foi SO exibicao.

O QUE ESTE ARQUIVO EXISTE PARA PEGAR
=====================================
`mercado_console.UNIDADE_DA_TAXA` passou de 1.000.000 para 5.000.000 em
2026-09-03. O comentario dela sempre afirmou, por escrito, que ela e "de
EXIBICAO, SO" — que `menor_pedido_visivel`, `mediana_dos_unitarios` e
`tendencia` comparam `Fraction(total, quantidade)` exata e que a escala nao muda
ordenacao nenhuma.

Uma frase no fonte que afirma uma propriedade e uma PROMESSA. Este arquivo e o
que a mede: ele troca a escala e afirma que as tres decisoes nao se movem nem
por um bit, e que o conjunto de caminhos que diferem no payload e EXATAMENTE o
conjunto fechado de exibicao.

O ARQUIVO E NOVO DE PROPOSITO, e nao mais uma classe em
`tests/test_dashboard_dados.py`: as duas tasks anteriores ja mexeram naquele
arquivo, e uma prova de "nada vazou" que morasse dentro do arquivo que mudou
junto seria mais facil de acreditar do que de conferir.

NADA AQUI TOCA A `.mercado/` REAL. Todo teste escreve num `tmp_path`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

from l2scanner import dashboard_dados, mercado_analise, mercado_console, mercado_registro
from l2scanner.mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA, SEPARADOR
from l2scanner.mercado_registro import ObservacaoLida

AGORA = datetime(2026, 9, 1, 15, 0, 0)
TERMINADOR = "\r\n"

# A ESCALA DE MENTIRA, e ela e 1.000.000 de proposito: e a escala que este
# projeto REALMENTE usou ate 2026-09-03, entao o teste mede a troca que de fato
# aconteceu, e nao um numero inventado para o teste passar.
ESCALA_TROCADA = 1_000_000

# AS DUAS OFERTAS, E A ORDEM DELAS IMPORTA.
#
# `11101` e `11100` sobre 10.000.000 de adena EXIBEM A MESMA STRING: `11101`
# escalado da `5.550,5` centesimos, que arredonda para `5.550` — exatamente o que
# `11100` da. As duas leem `55,50`.
#
# `11101` VEM PRIMEIRO para que um `min` que comparasse o valor ARREDONDADO
# escolhesse ELE, por ser o primeiro do empate. E o defeito "arredondar antes de
# comparar", contra o qual metade das docstrings deste projeto ja avisa, e este
# par e a unica forma de pegar: a STRING nao discrimina, entao so a `Fraction`
# pode.
TOTAL_QUE_EMPATA_NA_TELA = 11101
TOTAL_QUE_E_MENOR_DE_VERDADE = 11100
QUANTIDADE = 10_000_000

# A TERCEIRA OFERTA EXISTE POR UMA RAZAO MEDIDA, E ELA E UMA CORRECAO.
#
# A primeira redacao de `test_a_RAZAO_entre_os_pixels...` usava so as duas
# ofertas acima e era VACUA contra o defeito que ela dizia pegar: com a mutacao
# "arredondar antes de converter para `float`" aplicada em `_pixel`, o teste
# ficou VERDE. Medido:
#
#     11101 -> real 5.550,5 -> arredonda 5.550 | trocado 1.110,1 -> arredonda 1.110
#              e 5.550 x 0,2 = 1.110,0, que e exatamente o outro lado
#
# Os dois lados arredondaram PROPORCIONALMENTE, por coincidencia dos numeros
# escolhidos, e a razao sobreviveu. Um criterio que nao muda com o fato que ele
# julga e o defeito que a Licao 2 do CLAUDE.md nomeia.
#
# `11111` QUEBRA a proporcao, e por isso ele esta aqui:
#
#     11111 -> real 5.555,5 -> arredonda 5.556 | trocado 1.111,1 -> arredonda 1.111
#              e 5.556 x 0,2 = 1.111,2, que NAO e 1.111
#
# Ele nao entra em `_observacoes()` — so no disco — porque a premissa do teste
# da comparacao exata e que TODAS as ofertas dali exibem a MESMA string, e
# `11111` exibe `55,56`.
TOTAL_QUE_QUEBRA_A_PROPORCAO = 11111


def _oferta(minuto: int, total: int) -> ObservacaoLida:
    return ObservacaoLida(
        chave_da_serie=CHAVE_DA_SERIE_DA_ADENA,
        nome_exibido="Adena",
        primeira_vez=datetime(2026, 9, 1, 14, minuto),
        total_em_centesimos=total,
        quantidade=QUANTIDADE,
        residuo_do_cruzamento=0,
    )


def _observacoes() -> list[ObservacaoLida]:
    """O PAR QUE EMPATA NA TELA, montado a mao — sem disco.

    So as duas: a premissa de `TestAComparacaoEExata` e que as duas exibem a
    MESMA string, e a terceira oferta do disco (`11111`) exibe `55,56`.
    """
    return [
        _oferta(0, TOTAL_QUE_EMPATA_NA_TELA),
        _oferta(1, TOTAL_QUE_E_MENOR_DE_VERDADE),
    ]


def _observacoes_em_disco() -> list[ObservacaoLida]:
    """As duas do par, MAIS a que quebra a proporcao sob arredondamento."""
    return _observacoes() + [_oferta(2, TOTAL_QUE_QUEBRA_A_PROPORCAO)]


@dataclass(frozen=True)
class _CambioDeTeste:
    """A FORMA que o payload espera de um cambio, no molde ja usado em
    `tests/test_dashboard_dados.py`. Ele entra por PARAMETRO, e por isso este
    arquivo nao precisa gravar um `cambio.json` para exercitar o R$ derivado."""

    reais_por_xm: Decimal = Decimal("0.50")
    informado_em: datetime = datetime(2026, 9, 1, 14, 32)


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    """As TRES ofertas em disco, para o payload ter o que ler."""
    alvo = tmp_path / ".mercado"
    alvo.mkdir()
    linhas = [SEPARADOR.join(mercado_registro.COLUNAS)]
    linhas.extend(
        SEPARADOR.join(
            (
                obs.chave_da_serie,
                obs.nome_exibido,
                obs.primeira_vez.isoformat(),
                str(obs.total_em_centesimos),
                str(obs.quantidade),
                "0",
            )
        )
        for obs in _observacoes_em_disco()
    )
    (alvo / mercado_registro.ARQUIVO_DE_OBSERVACOES).write_text(
        "".join(linha + TERMINADOR for linha in linhas),
        encoding="utf-8",
        newline="",
    )
    return alvo


def _trocar_a_escala(monkeypatch: pytest.MonkeyPatch) -> None:
    """Os DOIS alvos, e a duplicidade e ACOPLAMENTO REAL — nao ruido do teste.

    `dashboard_dados` importa `UNIDADE_DA_TAXA` POR NOME
    (`from .mercado_console import UNIDADE_DA_TAXA`), entao ele carrega uma
    SEGUNDA ligacao para a mesma constante. Trocar so em `mercado_console` move o
    texto do console e NAO move `_escala_do_grafico` — o payload sairia com o
    destaque numa escala e os pixels na outra.

    Isso esta escrito aqui em vez de escondido atras de um ajudante mudo porque
    esconde-lo faria o teste MENTIR sobre o que ele precisou fazer para medir.
    """
    monkeypatch.setattr(mercado_console, "UNIDADE_DA_TAXA", ESCALA_TROCADA)
    monkeypatch.setattr(dashboard_dados, "UNIDADE_DA_TAXA", ESCALA_TROCADA)


def _caminhos_que_diferem(um, outro, prefixo: str = "") -> set[str]:
    """Os caminhos, em profundidade, onde os dois payloads discordam.

    Devolve CAMINHO e nao valor: o que este arquivo julga e ONDE a escala tocou,
    e o valor de cada diferenca ja e julgado pelos outros testes.
    """
    if isinstance(um, dict) and isinstance(outro, dict):
        divergentes: set[str] = set()
        for chave in set(um) | set(outro):
            caminho = f"{prefixo}.{chave}" if prefixo else str(chave)
            if chave not in um or chave not in outro:
                divergentes.add(caminho)
                continue
            divergentes |= _caminhos_que_diferem(um[chave], outro[chave], caminho)
        return divergentes
    if isinstance(um, list) and isinstance(outro, list):
        if len(um) != len(outro):
            return {f"{prefixo}[]"}
        divergentes = set()
        for indice, (a, b) in enumerate(zip(um, outro)):
            divergentes |= _caminhos_que_diferem(a, b, f"{prefixo}[{indice}]")
        return divergentes
    return set() if um == outro else {prefixo}


def _sem_indice(caminhos: set[str]) -> set[str]:
    """`series[0].pontos[1].menor_texto` -> `series[].pontos[].menor_texto`.

    A POSICAO NA LISTA NAO E O QUE SE JULGA. Com o indice dentro, o conjunto
    esperado cresceria com o numero de pontos da fixtura e o teste passaria a
    medir o tamanho do CSV.
    """
    return {re.sub(r"\[\d+\]", "[]", caminho) for caminho in caminhos}


class TestAComparacaoEExata:
    def test_o_menor_pedido_SAI_PELA_FRACAO_e_nao_pela_string(self) -> None:
        """As duas ofertas exibem `55,50`, e so UMA e a menor de verdade.

        `Fraction(11101, 10_000_000)` escalado da `5.550,5`, que arredonda para
        `5.550` — o mesmo que `Fraction(11100, 10_000_000)` da. A STRING nao
        pode discriminar, e por isso este teste afirma a FRACAO.

        E o teste que pega "arredondar antes de comparar". Sem ele, um `min`
        sobre o valor arredondado escolheria `11101` (o primeiro do empate) e
        NADA na tela denunciaria: os dois imprimem a mesma coisa.
        """
        observacoes = _observacoes()

        # A PREMISSA, MEDIDA E NAO SUPOSTA: as duas exibem a mesma string.
        textos = {
            mercado_console.formatar_taxa_derivada(
                mercado_analise.unitario(obs.total_em_centesimos, obs.quantidade)
            )
            for obs in observacoes
        }
        assert textos == {"55,50 XM por 5 milhoes de adena (derivado)"}, textos

        menor = mercado_analise.menor_pedido_visivel(observacoes)

        assert menor.unitario == Fraction(TOTAL_QUE_E_MENOR_DE_VERDADE, QUANTIDADE)
        assert menor.total_em_centesimos == TOTAL_QUE_E_MENOR_DE_VERDADE


class TestTrocarAEscalaNaoMoveDecisaoNenhuma:
    def test_as_TRES_decisoes_sao_IDENTICAS_com_a_escala_trocada(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Menor pedido, mediana e tendencia — incluindo o `n` de cada uma."""
        observacoes = _observacoes()

        menor_antes = mercado_analise.menor_pedido_visivel(observacoes)
        mediana_antes = mercado_analise.mediana_dos_unitarios(observacoes)
        tendencia_antes = mercado_analise.tendencia(observacoes)

        _trocar_a_escala(monkeypatch)

        menor_depois = mercado_analise.menor_pedido_visivel(observacoes)
        mediana_depois = mercado_analise.mediana_dos_unitarios(observacoes)
        tendencia_depois = mercado_analise.tendencia(observacoes)

        assert menor_depois == menor_antes
        assert menor_depois.unitario == menor_antes.unitario
        assert menor_depois.evidencia.n == menor_antes.evidencia.n

        assert mediana_depois == mediana_antes
        assert mediana_depois.unitario == mediana_antes.unitario
        assert mediana_depois.evidencia.n == mediana_antes.evidencia.n

        assert tendencia_depois == tendencia_antes
        assert tendencia_depois.evidencia.n == tendencia_antes.evidencia.n


class TestOPayloadDifereSOnumConjuntoFECHADO:
    # O CONJUNTO ESPERADO, ESCRITO POR EXTENSO E NUNCA POR PADRAO AMPLO.
    #
    # Um conjunto derivado por expressao regular ("tudo que termina em `_texto`")
    # ACEITARIA o proximo campo que vazasse, desde que ele tivesse a forma certa
    # — e o proximo campo a vazar e justamente o que ninguem previu. Escrito a
    # mao, qualquer caminho novo aparece como um a mais e reprova.
    # `series[].unidade` NAO ESTA AQUI, E A AUSENCIA E UMA MEDICAO.
    # `UNIDADE_EXIBIDA_DA_TAXA` e uma string escrita a mao (`"XM por 5 milhões de
    # adena"`) e nao e derivada de `UNIDADE_DA_TAXA`, entao trocar o NUMERO nao
    # move o ROTULO. As duas coisas so podem ser mantidas em acordo por teste, e
    # quem faz isso e
    # `tests/test_dashboard_dados.py::TestUmaTelaUmaUnidade`, que afirma as seis
    # superficies na mesma funcao.
    CAMINHOS_DE_EXIBICAO = {
        "destaque.xm.texto",
        "destaque.reais.texto",
        "series[].pontos[].menor_texto",
        "series[].pontos[].menor_pixel",
        # A LISTA INTEIRA, E NAO MARCA A MARCA: a QUANTIDADE de escadas muda
        # junto com a escala, e isso e correto. A faixa real desta fixtura tem
        # 6 centesimos de largura (5.550 a 5.556) e admite tres passos bonitos;
        # a trocada tem 1,1 (1.110 a 1.111,1) e admite um so. Quando o tamanho
        # da lista difere, o comparador para ali em vez de descer — e ele para
        # de proposito, porque emparelhar por indice duas listas de tamanhos
        # diferentes compararia marcas que nao sao a mesma coisa.
        "series[].escadas_do_eixo[]",
        "series[].baldes.cinco_minutos.principal[].texto",
        "series[].baldes.cinco_minutos.principal[].pixel",
        "series[].baldes.uma_hora.principal[].texto",
        "series[].baldes.uma_hora.principal[].pixel",
        "series[].baldes.um_dia.principal[].texto",
        "series[].baldes.um_dia.principal[].pixel",
    }

    def _dois_payloads(self, pasta: Path, monkeypatch: pytest.MonkeyPatch):
        """COM cambio, para o R$ derivado entrar na comparacao tambem."""
        real = dashboard_dados.payload(pasta, AGORA, cambio=_CambioDeTeste())
        _trocar_a_escala(monkeypatch)
        trocado = dashboard_dados.payload(pasta, AGORA, cambio=_CambioDeTeste())
        return real, trocado

    def test_o_conjunto_de_caminhos_que_diferem_e_EXATAMENTE_o_esperado(
        self, pasta: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Qualquer vazamento aparece como um caminho A MAIS.

        `n`, a ordem dos pontos, `estado`, `avisos`, `fonte`, os instantes — se
        qualquer um deles se mexer com a escala, ele entra neste conjunto e o
        teste reprova nomeando o caminho.
        """
        real, trocado = self._dois_payloads(pasta, monkeypatch)

        diferem = _sem_indice(_caminhos_que_diferem(real, trocado))

        assert diferem == self.CAMINHOS_DE_EXIBICAO

    def test_CONTROLE_o_patch_MORDE(
        self, pasta: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sem ele, um `monkeypatch` que nao pegasse deixaria os dois testes
        acima VERDES sem medir nada — o silencio com cara de verde.
        """
        real, trocado = self._dois_payloads(pasta, monkeypatch)

        assert real["destaque"]["xm"]["texto"] != trocado["destaque"]["xm"]["texto"]
        assert real["destaque"]["xm"]["texto"].startswith("55,50")
        assert trocado["destaque"]["xm"]["texto"].startswith("11,10")

    def test_a_RAZAO_entre_os_pixels_e_a_razao_entre_as_escalas(
        self, pasta: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Pega a escala aplicada DUAS vezes, e o arredondamento na fronteira.

        Se alguem escalasse de novo dentro da escada, a razao daria 1/25 em vez
        de 1/5; se alguem arredondasse antes de converter para `float`, o ponto
        de `1110,1` sairia como `1110,0`. As duas coisas passam MUITO longe da
        tolerancia abaixo.

        A RAZAO NAO FECHA EXATAMENTE, E ISSO E A FRONTEIRA DO `float` E NAO UM
        DEFEITO. O plano pedia "exatamente a razao entre as duas escalas", e
        MEDIDO isso e impossivel: `5550.5` e representavel em binario, `1110.1`
        nao e. O erro dessa conversao foi medido com codigo de producao e vale
        **8,19e-17 relativo** (9,09e-14 absoluto) — abaixo do epsilon da maquina
        (2,22e-16), e a mesma ordem do pior caso ja documentado em `_pixel`. A
        tolerancia de `1e-12` esta cinco ordens de grandeza acima do ruido
        medido e quatro abaixo do menor defeito que este teste precisa pegar.
        """
        real, trocado = self._dois_payloads(pasta, monkeypatch)

        esperada = ESCALA_TROCADA / 5_000_000
        pontos_reais = real["series"][0]["pontos"]
        pontos_trocados = trocado["series"][0]["pontos"]

        # TRES pontos, e o terceiro e o que discrimina — ver
        # `TOTAL_QUE_QUEBRA_A_PROPORCAO`. Com dois, este teste era vacuo contra
        # a mutacao do arredondamento, e isso foi MEDIDO e nao suposto.
        assert len(pontos_reais) == len(pontos_trocados) == 3
        for antes, depois in zip(pontos_reais, pontos_trocados):
            assert depois["menor_pixel"] == pytest.approx(
                antes["menor_pixel"] * esperada, rel=1e-12
            )
