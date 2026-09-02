"""A AGREGACAO E O PAYLOAD do dashboard. Puro, sem disco na maior parte.

UM PONTO E UM INSTANTE DE LEITURA, LITERALMENTE (CTX-1)
========================================================
E isso doi, e a dor esta medida. O CSV de campo tem 92 observacoes com apenas
**13** valores distintos de `primeira_vez`, e a maior serie tem 15 observacoes em
**2** instantes. Com `N_MINIMO_PARA_MEDIANA = 5`, agrupar por instante deixa a
linha da mediana AUSENTE na maior parte do grafico.

A pesquisa desta fase mediu exatamente isso e RECOMENDOU a outra leitura — o
acumulado ate o instante, que bate literalmente com o console e quase sempre tem
mediana. **O usuario foi confrontado com a medicao em 2026-09-01 e RECUSOU a
recomendacao**, mantendo a leitura literal do CONTEXT.

Consequencia aceita de olhos abertos, e que estes testes tratam como o caminho
NORMAL: onde a mediana falta, o que aparece e a frase de piso vinda do Python, e
nunca um numero. Um teste que exigisse mediana em todo ponto estaria cobrando o
comportamento que o usuario recusou.

O CONTROLE QUE CARREGA O PESO DESTE ARQUIVO
============================================
`test_o_valor_de_CADA_balde_esta_CONTIDO_na_lista_dos_instantes_dele` e a forma
EXECUTAVEL do D-02: um numero exibido tem de ter existido. Sem esse `assert in`,
trocar `median_low` por `median` — ou por `mean` — passaria despercebido, porque
os dois devolvem um numero plausivel e do tamanho certo. Medido na pesquisa:
`statistics.median` sobre quatro `Fraction` devolveu `13/42`, que **nao esta na
lista**.

NADA AQUI TOCA A `.mercado/` REAL. As observacoes sao montadas A MAO, no molde de
`tests/test_mercado_analise.py:283-300`, e o que precisa de disco usa `tmp_path`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

from l2scanner import dashboard_dados, mercado_console, mercado_registro
from l2scanner.mercado_analise import (
    N_MINIMO_PARA_MEDIANA,
    mediana_dos_unitarios,
    menor_pedido_visivel,
)
from l2scanner.mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA, SEPARADOR
from l2scanner.mercado_registro import ObservacaoLida

AGORA = datetime(2026, 9, 1, 15, 0, 0)


def _oferta(
    *,
    chave: str = CHAVE_DA_SERIE_DA_ADENA,
    nome: str = "Adena",
    carimbo: datetime = AGORA,
    total: int = 11600,
    quantidade: int = 10_000_000,
    residuo: int | None = 0,
) -> ObservacaoLida:
    """Uma oferta montada a mao — a agregacao nunca precisa de disco."""
    return ObservacaoLida(
        chave_da_serie=chave,
        nome_exibido=nome,
        primeira_vez=carimbo,
        total_em_centesimos=total,
        quantidade=quantidade,
        residuo_do_cruzamento=residuo,
    )


def _instante(carimbo: datetime, totais) -> list[ObservacaoLida]:
    """N ofertas do MESMO instante, com totais diferentes (unitarios distintos)."""
    return [_oferta(carimbo=carimbo, total=total) for total in totais]


# ===========================================================================
# UM PONTO E UM INSTANTE DE LEITURA (CTX-1)
# ===========================================================================


class TestUmPontoEUmINSTANTE:
    def test_tres_instantes_distintos_produzem_TRES_pontos_ordenados(self) -> None:
        """A ordem e por instante, e nao a do arquivo.

        O `ModeloDeMercado` preserva de proposito a ordem do CSV (para nao
        esconder de quem depura o que o arquivo diz). Um grafico, ao contrario,
        precisa do eixo do tempo crescente — ordenar aqui e a responsabilidade
        desta camada, e nao um conserto na de baixo.
        """
        observacoes = (
            _instante(datetime(2026, 9, 1, 14, 10), [12000])
            + _instante(datetime(2026, 9, 1, 14, 0), [11600])
            + _instante(datetime(2026, 9, 1, 14, 5), [30000])
        )

        pontos = dashboard_dados.pontos_por_instante(observacoes)

        assert [ponto.instante for ponto in pontos] == [
            datetime(2026, 9, 1, 14, 0),
            datetime(2026, 9, 1, 14, 5),
            datetime(2026, 9, 1, 14, 10),
        ]

    def test_um_instante_com_DUAS_ofertas_tem_menor_mas_a_tipica_e_NULA(self) -> None:
        """O caso NORMAL desta tela, e nao uma borda (CTX-1).

        O menor tem piso 1 e existe; a mediana tem piso 5 e nao existe. A
        resposta abaixo do piso e O QUE FALTA, nunca um numero — e `faltam` e
        campo derivado da `Evidencia` justamente para quem desenha nao ter de
        fazer a conta de cabeca.
        """
        pontos = dashboard_dados.pontos_por_instante(
            _instante(datetime(2026, 9, 1, 14, 0), [11600, 12000])
        )

        assert len(pontos) == 1
        ponto = pontos[0]
        assert ponto.menor is not None
        assert ponto.tipica is None
        assert ponto.tipica_evidencia.n == 2
        assert ponto.tipica_evidencia.piso == N_MINIMO_PARA_MEDIANA
        assert ponto.tipica_evidencia.faltam == 3
        assert ponto.n == 2

    def test_um_instante_com_CINCO_ofertas_tem_tipica_que_ESTEVE_na_lista(
        self,
    ) -> None:
        """`median_low` devolve um ELEMENTO, e cada elemento esteve na tela."""
        totais = [11600, 12000, 13000, 14000, 30000]
        pontos = dashboard_dados.pontos_por_instante(
            _instante(datetime(2026, 9, 1, 14, 0), totais)
        )

        ponto = pontos[0]
        unitarios = [Fraction(total, 10_000_000) for total in totais]
        assert ponto.tipica is not None
        assert ponto.tipica in unitarios
        assert ponto.tipica_evidencia.suficiente is True

    def test_a_evidencia_viaja_DENTRO_do_ponto_e_nunca_ao_lado(self) -> None:
        """O molde de `mercado_analise:226-254`.

        Estatistica sem `n` e adivinhacao com cara de numero, e um `n` que quem
        desenha pode esquecer de pedir e um `n` que uma hora nao vai ser exibido.
        """
        ponto = dashboard_dados.pontos_por_instante(
            _instante(datetime(2026, 9, 1, 14, 0), [11600, 12000])
        )[0]

        assert ponto.menor_evidencia.n == 2
        assert ponto.tipica_evidencia.n == 2
        # Os dois pisos sao DIFERENTES, e e por isso que sao duas evidencias e
        # nao uma: o menor e um fato observado (piso 1), a mediana e uma
        # inferencia (piso 5).
        assert ponto.menor_evidencia.piso != ponto.tipica_evidencia.piso

    def test_um_instante_SEM_oferta_comparavel_nao_vira_ponto_com_numero(
        self,
    ) -> None:
        """Quantidade nao positiva sai da conta E sai do `n` (`_comparaveis`)."""
        pontos = dashboard_dados.pontos_por_instante(
            [_oferta(carimbo=datetime(2026, 9, 1, 14, 0), quantidade=0)]
        )

        assert len(pontos) == 1
        assert pontos[0].menor is None
        assert pontos[0].tipica is None
        assert pontos[0].n == 0


# ===========================================================================
# O BALDE NUNCA INVENTA VALOR (D-02)
# ===========================================================================


class TestOBaldeNuncaInventaVALOR:
    def test_o_valor_de_CADA_balde_esta_CONTIDO_na_lista_dos_instantes_dele(
        self,
    ) -> None:
        """A FORMA EXECUTAVEL DO D-02, e o teste mais importante deste arquivo.

        Medido na pesquisa: `statistics.median` sobre quatro `Fraction` devolveu
        `13/42`, um valor que **nao esta na lista**. Trocar `median_low` por
        `median` ou por `mean` continuaria devolvendo um numero plausivel, do
        tamanho certo, e passaria em qualquer assercao de intervalo. So o
        `assert in` pega.
        """
        base = datetime(2026, 9, 1, 14, 0)
        entradas = [
            (base + timedelta(minutes=minutos), Fraction(total, 10_000_000))
            for minutos, total in enumerate([11600, 12000, 13000, 30000, 9000, 8000])
        ]
        ancora = dashboard_dados.ancora_da_meia_noite(base)
        largura = timedelta(minutes=2)

        produzidos = dashboard_dados.baldes(entradas, largura, ancora)

        assert produzidos, "nenhum balde saiu — o teste passaria por vacuidade"
        for inicio, valor in produzidos:
            do_balde = [
                v for instante, v in entradas if ancora + ((instante - ancora) // largura) * largura == inicio
            ]
            assert do_balde, inicio
            assert valor in do_balde, (inicio, valor, do_balde)

    def test_o_balde_de_uma_HORA_agrupa_por_indice_INTEIRO(self) -> None:
        """`(t - ancora) // largura`, e nunca `total_seconds()`.

        Medido: `total_seconds()` devolve `69713.696` (float) onde a divisao
        inteira de `timedelta` devolve `69713`. Float e como um centavo aparece
        do nada, e o indice de um balde nao tem parte fracionaria nenhuma a
        preservar.
        """
        base = datetime(2026, 9, 1, 14, 0)
        entradas = [
            (base, Fraction(1, 10)),
            (base + timedelta(minutes=59), Fraction(2, 10)),
            (base + timedelta(minutes=61), Fraction(3, 10)),
        ]

        produzidos = dashboard_dados.baldes(
            entradas, timedelta(hours=1), dashboard_dados.ancora_da_meia_noite(base)
        )

        assert len(produzidos) == 2
        assert produzidos[0][0] == datetime(2026, 9, 1, 14, 0)
        assert produzidos[1][0] == datetime(2026, 9, 1, 15, 0)

    def test_duas_leituras_do_MESMO_dia_civil_caem_no_MESMO_balde_de_um_dia(
        self,
    ) -> None:
        """"Dias atras" tem de querer dizer o que um humano acha que quer dizer."""
        manha = datetime(2026, 9, 1, 9, 0)
        noite = datetime(2026, 9, 1, 22, 0)
        entradas = [(manha, Fraction(1, 10)), (noite, Fraction(2, 10))]

        produzidos = dashboard_dados.baldes(
            entradas,
            timedelta(days=1),
            dashboard_dados.ancora_da_meia_noite(manha),
        )

        assert len(produzidos) == 1
        assert produzidos[0][0] == datetime(2026, 9, 1, 0, 0)

    def test_CONTROLE_com_ancora_arbitraria_o_MESMO_dia_se_PARTE_em_dois(
        self,
    ) -> None:
        """O controle sem o qual o teste acima nao prova nada.

        Medido na pesquisa: com a ancora em `2026-08-31 15:00`, os baldes de um
        dia comecam as **15:00**. As duas leituras do mesmo dia civil caem em
        baldes DIFERENTES — e e exatamente essa quebra que
        `ancora_da_meia_noite` existe para nao ter. Sem este controle, uma
        implementacao que ignorasse a ancora deixaria o teste anterior verde.
        """
        manha = datetime(2026, 9, 1, 9, 0)
        noite = datetime(2026, 9, 1, 22, 0)
        entradas = [(manha, Fraction(1, 10)), (noite, Fraction(2, 10))]

        produzidos = dashboard_dados.baldes(
            entradas, timedelta(days=1), datetime(2026, 8, 31, 15, 0)
        )

        assert len(produzidos) == 2

    def test_a_ancora_da_meia_noite_zera_hora_minuto_segundo_e_microssegundo(
        self,
    ) -> None:
        ancora = dashboard_dados.ancora_da_meia_noite(
            datetime(2026, 9, 1, 15, 47, 3, 123456)
        )

        assert ancora == datetime(2026, 9, 1, 0, 0, 0, 0)

    def test_as_LARGURAS_DE_BALDE_cobrem_as_duas_perguntas_do_usuario(self) -> None:
        """"Horarios do dia" e "dias atras", mais uma intermediaria."""
        larguras = dashboard_dados.LARGURAS_DE_BALDE

        assert timedelta(minutes=5) in larguras.values()
        assert timedelta(hours=1) in larguras.values()
        assert timedelta(days=1) in larguras.values()


# ===========================================================================
# NADA AQUI DEVOLVE FLOAT
# ===========================================================================


class TestNadaNaAgregacaoDevolveFLOAT:
    """`Fraction` na conta; o arredondamento so acontece ao formatar.

    A conversao para `float` existe UMA vez, na fronteira do JSON, e la ela e o
    PIXEL — a verdade viaja como string ao lado. Aqui dentro, um `float` seria
    erro acumulando em silencio sobre dinheiro real.
    """

    def test_o_valor_de_todo_ponto_e_Fraction_e_nunca_float(self) -> None:
        pontos = dashboard_dados.pontos_por_instante(
            _instante(datetime(2026, 9, 1, 14, 0), [11600, 12000, 13000, 14000, 30000])
        )

        for ponto in pontos:
            assert isinstance(ponto.menor, Fraction)
            assert isinstance(ponto.tipica, Fraction)
            assert not isinstance(ponto.menor, float)

    def test_o_valor_de_todo_balde_e_Fraction_e_nunca_float(self) -> None:
        base = datetime(2026, 9, 1, 14, 0)
        entradas = [
            (base + timedelta(minutes=m), Fraction(11600 + m, 10_000_000))
            for m in range(6)
        ]

        produzidos = dashboard_dados.baldes(
            entradas, timedelta(minutes=2), dashboard_dados.ancora_da_meia_noite(base)
        )

        for _, valor in produzidos:
            assert isinstance(valor, Fraction)
            assert not isinstance(valor, float)

    def test_baldes_sem_entrada_devolve_lista_VAZIA_e_nao_levanta(self) -> None:
        """`statistics.median_low([])` levantaria; o agrupamento pega antes."""
        assert (
            dashboard_dados.baldes([], timedelta(hours=1), AGORA) == []
        )


# ===========================================================================
# O PAYLOAD — A PRECEDENCIA FECHADA E A SERIE COMO ELEMENTO DE LISTA
# ===========================================================================
#
# O CSV DE FIXTURE E ESCRITO A MAO, e nao pelo `RegistroDeObservacoes`: o que se
# quer julgar aqui e o payload, e construir o arquivo com o escritor faria o
# teste depender do escritor para julgar o leitor.

TERMINADOR = "\r\n"


def _escrever_csv(pasta: Path, linhas, cabecalho=None) -> Path:
    campos = cabecalho or mercado_registro.COLUNAS
    montadas = [SEPARADOR.join(campos)]
    montadas.extend(SEPARADOR.join(linha) for linha in linhas)
    alvo = pasta / mercado_registro.ARQUIVO_DE_OBSERVACOES
    alvo.write_text(
        "".join(linha + TERMINADOR for linha in montadas),
        encoding="utf-8",
        newline="",
    )
    return alvo


def _linha(chave, nome, carimbo, total, quantidade) -> tuple[str, ...]:
    return (chave, nome, carimbo, str(total), str(quantidade), "0")


def _linhas_da_adena(totais, base="2026-09-01T14:0{}:00"):
    return [
        _linha(CHAVE_DA_SERIE_DA_ADENA, "Adena", base.format(i), total, 10_000_000)
        for i, total in enumerate(totais)
    ]


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    alvo = tmp_path / ".mercado"
    alvo.mkdir()
    return alvo


@dataclass(frozen=True)
class _CambioDeTeste:
    """A FORMA que o payload espera de um cambio — nada alem dela.

    ELE NAO IMPORTA `dashboard_cambio`, E ISSO E ESTRUTURAL. O cambio entra no
    payload por PARAMETRO (`key_links` do plano), e e isso que mantem
    `dashboard_dados` puro e testavel sem disco. Um import dos dois lados
    tornaria o modulo de dado dependente do modulo de persistencia para uma
    conta que nao precisa de disco nenhum — e faria este arquivo de teste ter de
    gravar um `cambio.json` para exercitar uma multiplicacao.

    Os dois campos sao os que o `01-03` define em `Cambio`. Se ele mudar a forma,
    este dublê fica vermelho junto — e e para isso que ele existe.
    """

    reais_por_xm: Decimal
    informado_em: datetime


def _todas_as_strings(valor):
    """Todo valor de string do payload, em qualquer profundidade."""
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for chave, dentro in valor.items():
            yield chave
            yield from _todas_as_strings(dentro)
    elif isinstance(valor, (list, tuple)):
        for dentro in valor:
            yield from _todas_as_strings(dentro)


class TestAPrecedenciaDosCincoESTADOS:
    """A ordem e FECHADA, e o primeiro que casar manda no destaque e no grafico.

    Varios podem ser verdade ao mesmo tempo — um arquivo com cabecalho trocado
    tambem nao tem serie da Adena — e e exatamente por isso que a ordem precisa
    estar escrita num lugar so, e testada uma a uma mais o empate.
    """

    def test_o_cabecalho_QUEBRADO_e_o_primeiro_da_ordem(self, pasta: Path) -> None:
        """Falha fechada: sem destaque, sem grafico, so a mensagem.

        Adivinhar coluna num arquivo que deixou de ser este arquivo e como o
        append escrevendo valores nas colunas erradas — o dado continua abrindo
        e passa a estar errado, que e a pior das duas falhas possiveis.
        """
        _escrever_csv(
            pasta,
            _linhas_da_adena([11600]),
            cabecalho=("chave", "nome", "quando", "total", "qtd", "res"),
        )

        pronto = dashboard_dados.payload(pasta, AGORA)

        assert pronto["estado"] == "erro_de_contrato"
        assert pronto["destaque"] is None
        assert pronto["series"] == []
        assert any("cabeçalho" in aviso for aviso in pronto["avisos"])

    def test_arquivo_AUSENTE_tem_estado_proprio_e_diz_o_que_fazer(
        self, pasta: Path
    ) -> None:
        pronto = dashboard_dados.payload(pasta, AGORA)

        assert pronto["estado"] == "arquivo_ausente"
        assert pronto["destaque"] is None
        assert any("vigiar-mercado.bat" in aviso for aviso in pronto["avisos"])

    def test_sem_leitura_da_adena_carrega_a_contagem_REAL_de_linhas(
        self, pasta: Path
    ) -> None:
        """A frase de PROVA — sem ela, "0 da serie Adena" e indistinguivel de
        "o dashboard nao conseguiu abrir o arquivo"."""
        _escrever_csv(
            pasta,
            [
                _linha("common-aztac#0", "Common Aztac", "2026-09-01T13:00:00", 6200, 48),
                _linha("common-aztac#0", "Common Aztac", "2026-09-01T13:05:00", 6300, 48),
            ],
        )

        pronto = dashboard_dados.payload(pasta, AGORA)

        assert pronto["estado"] == "sem_leitura"
        assert any("2 linhas" in aviso and "0 da série" in aviso for aviso in pronto["avisos"])
        assert "sem evidencia" in pronto["destaque"]["xm"]["texto"]

    def test_abaixo_do_piso_mostra_o_MENOR_e_a_frase_no_lugar_da_mediana(
        self, pasta: Path
    ) -> None:
        """O menor tem piso 1 e existe; a mediana tem piso 5 e nao existe."""
        _escrever_csv(pasta, _linhas_da_adena([11600, 12000]))

        pronto = dashboard_dados.payload(pasta, AGORA)

        assert pronto["estado"] == "abaixo_do_piso"
        assert pronto["destaque"]["xm"]["texto"] == "11,60 XM por milhao de adena (derivado)"
        tipica = pronto["series"][0]["pontos"][0]["tipica_texto"]
        assert "sem evidencia" in tipica

    def test_serie_presente_com_SEIS_ofertas_traz_o_numero_do_destaque(
        self, pasta: Path
    ) -> None:
        _escrever_csv(
            pasta, _linhas_da_adena([11600, 12000, 13000, 14000, 15000, 30000])
        )

        pronto = dashboard_dados.payload(pasta, AGORA)

        assert pronto["estado"] == "serie_presente"
        assert pronto["destaque"]["xm"]["n"] == 6
        assert "0,00" not in pronto["destaque"]["xm"]["texto"]

    def test_EMPATE_cabecalho_quebrado_E_sem_adena_vence_o_ERRO_DE_CONTRATO(
        self, pasta: Path
    ) -> None:
        """Os dois sao verdade ao mesmo tempo; a ordem decide, e ela e fechada."""
        _escrever_csv(
            pasta,
            [_linha("common-aztac#0", "Common Aztac", "2026-09-01T13:00:00", 6200, 48)],
            cabecalho=("chave", "nome", "quando", "total", "qtd", "res"),
        )

        pronto = dashboard_dados.payload(pasta, AGORA)

        assert pronto["estado"] == "erro_de_contrato"
        assert pronto["estado"] != "sem_leitura"

    def test_os_ESTADOS_sao_CINCO_na_ordem_do_UI_SPEC(self) -> None:
        assert dashboard_dados.ESTADOS == (
            "erro_de_contrato",
            "arquivo_ausente",
            "sem_leitura",
            "abaixo_do_piso",
            "serie_presente",
        )


class TestASerieEUmElementoDeLista:
    """DASH-05 do lado do dado: uma serie nova e um ELEMENTO a mais.

    Nao uma chave nova, nao um `if` da Adena, nao um campo `adena` no payload.
    Se instanciar a segunda serie exigisse forma nova, o requisito seria uma
    intencao escrita num documento; sendo um elemento de lista, ele e estrutural.
    """

    def test_duas_series_produzem_DOIS_elementos_com_as_MESMAS_chaves(
        self, pasta: Path
    ) -> None:
        _escrever_csv(
            pasta,
            _linhas_da_adena([11600, 12000])
            + [
                _linha("common-aztac#0", "Common Aztac", "2026-09-01T13:00:00", 6200, 48),
                _linha("common-aztac#0", "Common Aztac", "2026-09-01T13:05:00", 6300, 48),
            ],
        )

        series = dashboard_dados.payload(pasta, AGORA)["series"]

        assert len(series) == 2
        assert set(series[0]) == set(series[1])
        assert {serie["chave"] for serie in series} == {
            CHAVE_DA_SERIE_DA_ADENA,
            "common-aztac#0",
        }

    def test_series_e_LISTA_mesmo_com_UMA_serie_so(self, pasta: Path) -> None:
        _escrever_csv(pasta, _linhas_da_adena([11600, 12000]))

        series = dashboard_dados.payload(pasta, AGORA)["series"]

        assert isinstance(series, list)
        assert len(series) == 1

    def test_a_serie_de_um_item_comum_sai_em_OUTRA_unidade_que_a_da_adena(
        self, pasta: Path
    ) -> None:
        """O ponto de decisao continua sendo UM: `formatador_do_unitario`.

        Se a unidade fosse decidida por um segundo `if` sobre a sentinela, o dia
        em que os dois divergissem a tela imprimiria `0,00 por unidade` para a
        Adena com toda a confianca do mundo.
        """
        _escrever_csv(
            pasta,
            _linhas_da_adena([11600])
            + [_linha("common-aztac#0", "Common Aztac", "2026-09-01T13:00:00", 6200, 48)],
        )

        series = dashboard_dados.payload(pasta, AGORA)["series"]
        unidades = {serie["chave"]: serie["unidade"] for serie in series}

        assert unidades[CHAVE_DA_SERIE_DA_ADENA] != unidades["common-aztac#0"]


class TestNenhumValorPadraoEChutado:
    """Um cambio chutado vira decisao de dinheiro real errada.

    A ausencia se escreve com PALAVRA, e nunca com zero — que e a mesma regra do
    `0,00` proibido como espaco reservado.
    """

    def test_SEM_cambio_o_sub_objeto_de_reais_e_NULO(self, pasta: Path) -> None:
        _escrever_csv(pasta, _linhas_da_adena([11600, 12000]))

        pronto = dashboard_dados.payload(pasta, AGORA)

        assert pronto["destaque"]["reais"] is None
        assert any("indisponível" in aviso for aviso in pronto["avisos"])
        # Nenhuma chave de R$ com numero em lugar nenhum do payload.
        assert not any("R$ 0" in texto for texto in _todas_as_strings(pronto))

    def test_COM_cambio_o_real_aparece_DERIVADO_e_com_carimbo(
        self, pasta: Path
    ) -> None:
        _escrever_csv(pasta, _linhas_da_adena([11600, 12000]))
        cambio = _CambioDeTeste(
            reais_por_xm=Decimal("0.50"),
            informado_em=datetime(2026, 9, 1, 14, 32),
        )

        pronto = dashboard_dados.payload(pasta, AGORA, cambio=cambio)
        reais = pronto["destaque"]["reais"]

        assert reais is not None
        assert reais["derivado"] is True
        assert reais["informado_em"] == "2026-09-01T14:32:00"
        # 11,60 XM por milhao x R$ 0,50 por XM = R$ 5,80 por milhao.
        assert "5,80" in reais["texto"]
        assert "informado por você" in reais["texto"]
        assert any("toda a série" in aviso for aviso in pronto["avisos"])

    def test_o_R_de_hoje_aplicado_a_serie_INTEIRA_e_dito_em_voz_alta(
        self, pasta: Path
    ) -> None:
        """Com UM valor informado nao existe serie de cambio, e a tela diz isso.

        Aplicar o cambio de hoje a um ponto de tres dias atras sem avisar seria
        um numero certo com um significado errado — a familia de mentira
        plausivel que este projeto inteiro combate.
        """
        _escrever_csv(pasta, _linhas_da_adena([11600, 12000]))
        cambio = _CambioDeTeste(
            reais_por_xm=Decimal("0.50"), informado_em=datetime(2026, 9, 1, 14, 32)
        )

        pronto = dashboard_dados.payload(pasta, AGORA, cambio=cambio)

        assert dashboard_dados.AVISO_DO_CAMBIO_HISTORICO in pronto["avisos"]


class TestODadoVelhoPerdeOAgoraENaoONumero:
    def test_recencia_ACIMA_do_limiar_marca_velho_e_MANTEM_o_numero(
        self, pasta: Path
    ) -> None:
        """O que sai e a AFIRMACAO de "agora", e nao o valor."""
        _escrever_csv(pasta, _linhas_da_adena([11600, 12000]))
        muito_depois = datetime(2026, 9, 1, 14, 1) + dashboard_dados.LIMIAR_DE_FRESCOR + timedelta(minutes=1)

        pronto = dashboard_dados.payload(pasta, muito_depois)

        assert pronto["destaque"]["xm"]["velho"] is True
        assert "11,60" in pronto["destaque"]["xm"]["texto"]
        assert any("não de agora" in aviso for aviso in pronto["avisos"])
        # A frase PROIBIDA e "agora" colado no numero — e a unica forma
        # verificavel dela nesta arvore e o "agora mesmo" que o console emite
        # para recencia abaixo de um minuto.
        assert not any("agora mesmo" in texto for texto in _todas_as_strings(pronto))

    def test_recencia_DENTRO_do_limiar_nao_marca_velho(self, pasta: Path) -> None:
        _escrever_csv(pasta, _linhas_da_adena([11600, 12000]))

        pronto = dashboard_dados.payload(pasta, datetime(2026, 9, 1, 14, 30))

        assert pronto["destaque"]["xm"]["velho"] is False
        assert not any("não de agora" in aviso for aviso in pronto["avisos"])


class TestAsFrasesProibidasNaoAparecem:
    def test_nenhuma_frase_proibida_em_NENHUM_dos_cinco_estados(
        self, tmp_path: Path
    ) -> None:
        """As proibicoes herdadas do `mercado_console`, aplicadas ao payload.

        `preco de venda` / `vendido por` / `valor de mercado`: o scanner ve
        OFERTAS, e nao transacoes — ninguem comprou por este valor, alguem PEDIU
        este valor. `0,00`: ausencia se escreve com palavra, nunca com zero, e
        nenhuma fixture deste teste tem valor real que arredonde para zero — um
        `0,00` aqui so pode vir de espaco reservado ou do formatador errado.
        """
        montagens = {
            "erro_de_contrato": (
                _linhas_da_adena([11600]),
                ("chave", "nome", "quando", "total", "qtd", "res"),
            ),
            "sem_leitura": (
                [_linha("common-aztac#0", "Common Aztac", "2026-09-01T13:00:00", 6200, 48)],
                None,
            ),
            "abaixo_do_piso": (_linhas_da_adena([11600, 12000]), None),
            "serie_presente": (
                _linhas_da_adena([11600, 12000, 13000, 14000, 15000, 30000]),
                None,
            ),
        }

        prontos = []
        for nome, (linhas, cabecalho) in montagens.items():
            destino = tmp_path / nome
            destino.mkdir()
            _escrever_csv(destino, linhas, cabecalho=cabecalho)
            prontos.append(dashboard_dados.payload(destino, AGORA))
        # O quinto: arquivo ausente.
        ausente = tmp_path / "arquivo_ausente"
        ausente.mkdir()
        prontos.append(dashboard_dados.payload(ausente, AGORA))

        assert len(prontos) == len(dashboard_dados.ESTADOS)
        assert {pronto["estado"] for pronto in prontos} == set(dashboard_dados.ESTADOS)

        for pronto in prontos:
            for texto in _todas_as_strings(pronto):
                for proibida in dashboard_dados.FRASES_PROIBIDAS:
                    assert proibida not in texto.lower(), (proibida, texto)


class TestAFronteiraDoFLOAT:
    """O `float` no JSON e o PIXEL; a `string` no JSON e a VERDADE."""

    def test_o_ponto_carrega_o_pixel_em_float_E_a_verdade_em_string(
        self, pasta: Path
    ) -> None:
        _escrever_csv(pasta, _linhas_da_adena([11600, 12000]))

        ponto = dashboard_dados.payload(pasta, AGORA)["series"][0]["pontos"][0]

        assert isinstance(ponto["menor_pixel"], float)
        assert ponto["menor_pixel"] == pytest.approx(1160.0)
        assert ponto["menor_texto"] == "11,60 XM por milhao de adena (derivado)"

    def test_sem_valor_o_pixel_e_NULO_e_nao_zero(self, pasta: Path) -> None:
        """Zero e um lugar no eixo; ausencia nao e."""
        _escrever_csv(pasta, _linhas_da_adena([11600, 12000]))

        ponto = dashboard_dados.payload(pasta, AGORA)["series"][0]["pontos"][0]

        assert ponto["tipica_pixel"] is None
        assert ponto["tipica_pixel"] != 0


class TestAFraseDePisoEAMESMADoConsole:
    """O antidoto para a duplicacao que o `01-01-SUMMARY` deixou sinalizada.

    A frase de piso nao pode ser reusada por CHAMADA porque o console a entrega
    dentro de uma linha ja formatada para o terminal (recuo de quatro espacos,
    rotulo colado). O que da para prender e a IGUALDADE POR SUBSTRING: se alguem
    mexer no texto de um dos dois lados, estes dois testes caem.
    """

    def test_a_frase_do_menor_e_SUBSTRING_da_linha_do_console(self) -> None:
        observacoes = _instante(datetime(2026, 9, 1, 14, 0), [])

        nossa = dashboard_dados.frase_de_piso_do_menor(
            menor_pedido_visivel(observacoes).evidencia
        )
        do_console = mercado_console._linha_do_menor(
            observacoes, AGORA, CHAVE_DA_SERIE_DA_ADENA
        )

        assert nossa in do_console

    def test_a_frase_da_tipica_e_SUBSTRING_da_linha_do_console(self) -> None:
        observacoes = _instante(datetime(2026, 9, 1, 14, 0), [11600, 12000])

        nossa = dashboard_dados.frase_de_piso_da_tipica(
            mediana_dos_unitarios(observacoes).evidencia
        )
        do_console = mercado_console._linha_da_mediana(
            observacoes, AGORA, CHAVE_DA_SERIE_DA_ADENA
        )

        assert nossa in do_console
