"""O PORTAO DE LAYOUT: pagina que nao e a grade calibrada e recusada alto.

D-09 e o limite do v1: **le-se SOMENTE o layout calibrado**, que desde o censo
dos 335 frames e a GRADE DE NEGOCIACAO. D-11 diz como ele e reconhecido: por
molde do cabecalho de coluna, cortado SEM a seta de ordenacao.

POR QUE A RECUSA NAO PROPOE "LER MESMO ASSIM"
----------------------------------------------
Ler a coluna errada com confianca corrompe a serie por um FATOR INTEIRO, e a aba
Adena e o exemplo vivo: ali a coluna e `5 mln increment`, normalizada por cinco
milhoes de adena e NAO por unidade. Um `12` lido dali entraria no CSV como doze
centesimos de moeda e a serie de precos daquele item ficaria errada em seis
ordens de grandeza — calada, e para sempre, porque nada no CSV diria de que
layout aquela linha veio.

POR QUE ELE RODA ANTES DA SONDA DE OCLUSAO
-------------------------------------------
MEDIDO: em `scroll/frame_000009` a sonda de fundo leu modas de 47 e 65 com a
PARIDADE INVERTIDA em relacao a grade calibrada, porque aquele frame e a TELA DE
BUSCA. Aplicar a geometria da grade de negociacao ali mede fundo de uma tabela
que nao existe. Se a sonda viesse primeiro, ela decidiria sobre uma geometria que
nao vale — e o pior caso e ela dizer "limpa" e liberar a leitura.

AS QUATRO BANDAS VERSIONADAS, E O VAO ENTRE ELAS
-------------------------------------------------
    cabecalho_negociacao_goods.png       1,0000   PASSA   (ordenado por Goods)
    cabecalho_negociacao_unitprice.png   1,0000   PASSA   (ordenado por Unit price)
    cabecalho_adena.png                  0,1331   recusa  (scroll/frame_000014)
    cabecalho_busca.png                 -0,0027   recusa  (scroll/frame_000048)

As duas primeiras sao o MESMO layout com a seta de ordenacao em celulas
DIFERENTES, e as duas casam 1,0000: o corte de brilho tira a seta do molde, que
e exatamente o que D-11 exige.
"""

from __future__ import annotations

import copy
import inspect
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import TETO_DA_FOLGA_DE_COLA, Calibracao
from l2scanner.identidade import VALOR_MINIMO_DO_TEXTO
from l2scanner.mercado_leitura import (
    casamento_do_cabecalho,
    layout_confere,
    ler_linha,
)
from l2scanner.mercado_leitura import LinhaLida
from l2scanner.mercado_pagina import (
    JANELAS_IGUAIS_PARA_CONGELAR,
    LeituraDaPagina,
    LeitorDePagina,
    paginas_concordam,
    posicoes_comparaveis,
    tupla_comparavel,
)
from l2scanner.mercado_visao import (
    RastreioDoPainel,
    ancoras_de_calibracao,
    cabecalho_de_calibracao,
)

FIXTURES = Path(__file__).parent / "fixtures" / "mercado"
CALIBRACAO = FIXTURES / "calibracao_de_fixture.json"

BANDAS_QUE_PASSAM = (
    "cabecalho_negociacao_goods.png",
    "cabecalho_negociacao_unitprice.png",
)
BANDAS_QUE_CAEM = ("cabecalho_adena.png", "cabecalho_busca.png")

JANELA_NEGOCIACAO = FIXTURES / "janela_negociacao_f010.png"
JANELA_ADENA = FIXTURES / "janela_adena_f014.png"
JANELA_TOOLTIP = FIXTURES / "janela_tooltip_f012.png"
JANELA_F005 = FIXTURES / "janela_negociacao_f005.png"
JANELA_F005_REPETIDA = FIXTURES / "janela_negociacao_f005_repetida.png"
JANELA_F010 = JANELA_NEGOCIACAO

# Os totais que o TRACER do 02-04 ja lia, escritos por valor. Se um deles mudar
# depois desta onda, o piso da Quantity VAZOU para a coluna de moeda — que e a
# unica coisa que o 02-07 nao pode fazer.
TOTAIS_DO_TRACER_F005 = {1: (3666, 3), 3: (1500, 3), 5: (1139, 6), 6: (500, 2)}
TOTAIS_DO_TRACER_F010 = {6: (1890, 2), 8: (1800, 3)}


def ler_fixtura(caminho: Path) -> np.ndarray:
    pixels = cv2.imread(str(caminho))
    assert pixels is not None, f"nao decodifiquei a fixtura {caminho}"
    return pixels


@pytest.fixture(scope="module")
def cal() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO)


@pytest.fixture(scope="module")
def molde(cal: Calibracao) -> np.ndarray:
    return cabecalho_de_calibracao(cal.mercado_cabecalho_de_coluna)


class ContadoraDeOCR:
    def __init__(self) -> None:
        self.chamadas = 0

    def __call__(self, _pixels) -> str:
        self.chamadas += 1
        return "Common Fafurion Doll"


def montar_leitor(cal):
    barata, conferencia = ContadoraDeOCR(), ContadoraDeOCR()
    leitor = LeitorDePagina(
        RastreioDoPainel(
            ancoras_de_calibracao(cal.mercado_ancoras),
            float(cal.mercado_limiar_da_ancora),
        ),
        {},
        barata,
        conferencia,
        cal,
    )
    return leitor, barata, conferencia


def _leitura_falsa(
    por_indice: dict[int, tuple[int, int]], descartadas: tuple[int, ...] = ()
) -> LeituraDaPagina:
    """Uma `LeituraDaPagina` sintetica: indice -> (total, quantidade).

    Ela existe para afirmar os PREDICADOS de comparacao sem montar pixels — do
    mesmo jeito que os testes de `agrupar` afirmam a regra sem montar um frame.
    O nome e o `serie_nova` variam de proposito entre as duas leituras de um
    par, porque nenhum dos dois entra na tupla comparavel.
    """
    linhas = tuple(
        LinhaLida(
            indice=indice,
            chave_da_serie=f"item-{indice}#0",
            nome_exibido=f"Item {indice}",
            total_em_centesimos=total,
            quantidade=quantidade,
            serie_nova=False,
            residuo_do_cruzamento=None,
        )
        for indice, (total, quantidade) in sorted(por_indice.items())
    )
    return LeituraDaPagina(
        linhas=linhas,
        descartadas=descartadas,
        motivos=tuple("sintetico" for _ in descartadas),
    )


class TestOCasamentoDoCabecalho:
    """As quatro bandas versionadas, e o vao que o limiar 0,73 divide."""

    @pytest.mark.parametrize("nome", BANDAS_QUE_PASSAM)
    def test_as_duas_ordenacoes_de_NEGOCIACAO_casam(self, cal, molde, nome) -> None:
        banda = ler_fixtura(FIXTURES / nome)
        score = casamento_do_cabecalho(
            banda, molde, int(cal.mercado_cabecalho_de_coluna["corte_de_brilho"])
        )
        assert score >= float(cal.mercado_limiar_do_cabecalho), (
            f"{nome} casou {score:.4f}, abaixo do limiar "
            f"{float(cal.mercado_limiar_do_cabecalho):.4f}"
        )

    @pytest.mark.parametrize("nome", BANDAS_QUE_CAEM)
    def test_adena_e_busca_sao_RECUSADAS(self, cal, molde, nome) -> None:
        banda = ler_fixtura(FIXTURES / nome)
        score = casamento_do_cabecalho(
            banda, molde, int(cal.mercado_cabecalho_de_coluna["corte_de_brilho"])
        )
        assert score < float(cal.mercado_limiar_do_cabecalho), (
            f"{nome} casou {score:.4f} e passaria o portao de layout"
        )

    def test_o_vao_entre_as_duas_populacoes_e_GRANDE(self, cal, molde) -> None:
        """Se o vao fosse estreito, o limiar seria sorte e nao medicao."""
        corte = int(cal.mercado_cabecalho_de_coluna["corte_de_brilho"])
        passam = [
            casamento_do_cabecalho(ler_fixtura(FIXTURES / n), molde, corte)
            for n in BANDAS_QUE_PASSAM
        ]
        caem = [
            casamento_do_cabecalho(ler_fixtura(FIXTURES / n), molde, corte)
            for n in BANDAS_QUE_CAEM
        ]
        assert min(passam) - max(caem) > 0.5

    def test_a_seta_de_ordenacao_NAO_participa_do_casamento(
        self, cal, molde
    ) -> None:
        """As duas bandas de negociacao sao o MESMO layout, ordenacoes diferentes.

        Elas nao sao pixel-identicas — a seta anda de celula —, e mesmo assim as
        duas casam. E isso que prova que o corte de brilho a removeu do molde.
        """
        goods = ler_fixtura(FIXTURES / BANDAS_QUE_PASSAM[0])
        unitprice = ler_fixtura(FIXTURES / BANDAS_QUE_PASSAM[1])
        assert not np.array_equal(goods, unitprice)
        corte = int(cal.mercado_cabecalho_de_coluna["corte_de_brilho"])
        assert casamento_do_cabecalho(goods, molde, corte) == pytest.approx(
            casamento_do_cabecalho(unitprice, molde, corte), abs=1e-6
        )

    def test_banda_vazia_devolve_zero_e_nao_levanta(self, cal, molde) -> None:
        vazia = np.zeros((0, 0, 3), dtype=np.uint8)
        assert casamento_do_cabecalho(vazia, molde, 222) == 0.0


class TestOPortaoDeLayout:
    """`layout_confere` sobre a janela inteira, na posicao conhecida."""

    def test_a_janela_de_negociacao_passa(self, cal, molde) -> None:
        janela = ler_fixtura(JANELA_NEGOCIACAO)
        assert (
            layout_confere(
                janela,
                (1010, 212),
                int(cal.mercado_grade["dx"]),
                cal.mercado_cabecalho_de_coluna,
                molde,
                float(cal.mercado_limiar_do_cabecalho),
            )
            is True
        )

    def test_a_janela_da_aba_ADENA_e_recusada(self, cal, molde) -> None:
        janela = ler_fixtura(JANELA_ADENA)
        assert (
            layout_confere(
                janela,
                (1010, 212),
                int(cal.mercado_grade["dx"]),
                cal.mercado_cabecalho_de_coluna,
                molde,
                float(cal.mercado_limiar_do_cabecalho),
            )
            is False
        )

    def test_sem_molde_a_resposta_e_False_e_NAO_um_raise(self, cal) -> None:
        janela = ler_fixtura(JANELA_NEGOCIACAO)
        assert (
            layout_confere(
                janela,
                (1010, 212),
                int(cal.mercado_grade["dx"]),
                cal.mercado_cabecalho_de_coluna,
                None,
                float(cal.mercado_limiar_do_cabecalho),
            )
            is False
        )

    def test_sem_limiar_a_resposta_e_False(self, cal, molde) -> None:
        janela = ler_fixtura(JANELA_NEGOCIACAO)
        assert (
            layout_confere(
                janela,
                (1010, 212),
                int(cal.mercado_grade["dx"]),
                cal.mercado_cabecalho_de_coluna,
                molde,
                None,
            )
            is False
        )

    def test_banda_fora_da_janela_e_False_e_NAO_um_recorte_torto(
        self, cal, molde
    ) -> None:
        """`janela[-500:, -500:]` e VALIDO em numpy e devolve o canto oposto."""
        janela = ler_fixtura(JANELA_NEGOCIACAO)
        assert (
            layout_confere(
                janela,
                (100_000, 100_000),
                int(cal.mercado_grade["dx"]),
                cal.mercado_cabecalho_de_coluna,
                molde,
                float(cal.mercado_limiar_do_cabecalho),
            )
            is False
        )
        assert (
            layout_confere(
                janela,
                (-100_000, -100_000),
                int(cal.mercado_grade["dx"]),
                cal.mercado_cabecalho_de_coluna,
                molde,
                float(cal.mercado_limiar_do_cabecalho),
            )
            is False
        )


class TestAPaginaRecusadaPorLayout:
    """Recusada = ZERO linhas lidas e ZERO chamadas de OCR."""

    def test_a_aba_adena_nao_produz_linha_nem_chamada_de_OCR(self, cal) -> None:
        leitor, barata, conferencia = montar_leitor(cal)
        assert leitor.observar(ler_fixtura(JANELA_ADENA)) is None
        assert leitor.ultima_leitura is None
        assert barata.chamadas == 0
        assert conferencia.chamadas == 0

    def test_dois_frames_da_aba_adena_nunca_produzem_pagina_aceita(
        self, cal
    ) -> None:
        leitor, _b, _c = montar_leitor(cal)
        assert leitor.observar(ler_fixtura(JANELA_ADENA)) is None
        assert leitor.observar(ler_fixtura(JANELA_ADENA)) is None

    def test_a_mensagem_nomeia_o_layout_calibrado_e_diz_que_so_ele_e_lido(
        self, cal, caplog
    ) -> None:
        leitor, _b, _c = montar_leitor(cal)
        with caplog.at_level("WARNING", logger="l2scanner.mercado_pagina"):
            leitor.observar(ler_fixtura(JANELA_ADENA))
        texto = caplog.text
        assert cal.mercado_cabecalho_de_coluna["layout"] in texto
        assert "SOMENTE o layout calibrado" in texto
        assert "Adena" in texto


class TestAOrdemDoPortaoNaObservacao:
    """O portao de layout roda ANTES da sonda de oclusao (e antes de tudo)."""

    def test_a_pagina_recusada_por_layout_nao_chega_a_medir_oclusao(
        self, cal
    ) -> None:
        """Se a sonda tivesse rodado, haveria descarte por oclusao no registro.

        Recusada por layout, `ultima_leitura` e `None`: nem leitura, nem
        descarte, nem linha vazia. A grade nem chegou a ser fatiada — que e o
        ponto, porque fatiar uma geometria que nao vale ja e o erro.
        """
        leitor, _b, _c = montar_leitor(cal)
        leitor.observar(ler_fixtura(JANELA_ADENA))
        assert leitor.ultima_leitura is None

    def test_o_portao_aparece_ANTES_da_fatia_no_fonte_de_observar(self) -> None:
        fonte = inspect.getsource(LeitorDePagina.observar)
        assert fonte.index("_layout_confere") < fonte.index("_ler_a_pagina")

    def test_a_sonda_de_oclusao_so_e_consultada_dentro_da_fatia(self) -> None:
        """Ela mora em `ler_linha`, que so roda depois do portao de layout.

        `mercado_pagina` nao chama `linha_ocluida` em lugar nenhum: nao ha um
        segundo caminho pelo qual a sonda pudesse rodar antes do portao.
        """
        import l2scanner.mercado_pagina as pagina

        codigo = [
            linha
            for linha in inspect.getsource(pagina).splitlines()
            if not linha.lstrip().startswith("#")
        ]
        assert not [linha for linha in codigo if "linha_ocluida(" in linha]


class TestFeatureOFFQuandoFaltaCalibracao:
    """Ausencia e feature OFF com aviso alto, NUNCA um `raise` no arranque."""

    def _sem(self, cal: Calibracao, campo: str) -> Calibracao:
        copia = copy.deepcopy(cal)
        setattr(copia, campo, None)
        return copia

    @pytest.mark.parametrize(
        "campo",
        [
            "mercado_cabecalho_de_coluna",
            "mercado_limiar_do_cabecalho",
            "mercado_sonda_do_fundo",
            "mercado_limiar_de_leitura_de_glifo",
            "mercado_margem_de_leitura_de_glifo",
            "mercado_corte_de_similaridade",
            "mercado_piso_de_similaridade",
            "mercado_templates_de_digito",
            # A quarta coluna entrou no 02-06: sem ela a TERCEIRA leitura de
            # numero nao acontece, e sem aviso a fatia da linha levantaria
            # dentro do tick em vez de virar feature OFF.
            "mercado_coluna_do_unitario",
            # A DECIMA, do 02-07: o piso de brilho PROPRIO da coluna Quantity.
            # Sem ela nao ha piso para passar a `ler_celula_de_quantidade`, que
            # o exige SEM valor de fabrica — e o portao por AUSENCIA e o que
            # transforma isso em feature OFF em vez de `TypeError` no tick.
            "mercado_limiar_de_brilho_da_quantidade",
        ],
    )
    def test_a_leitura_nao_acontece_e_nada_levanta(self, cal, campo) -> None:
        leitor, barata, conferencia = montar_leitor(self._sem(cal, campo))
        assert leitor.observar(ler_fixtura(JANELA_NEGOCIACAO)) is None
        assert leitor.ultima_leitura is None
        assert barata.chamadas == conferencia.chamadas == 0

    def test_a_falta_e_AVISADA_e_diz_o_que_rodar(self, cal, caplog) -> None:
        sem_cabecalho = self._sem(cal, "mercado_cabecalho_de_coluna")
        leitor, _b, _c = montar_leitor(sem_cabecalho)
        with caplog.at_level("WARNING", logger="l2scanner.mercado_pagina"):
            leitor.observar(ler_fixtura(JANELA_NEGOCIACAO))
        assert "mercado_cabecalho_de_coluna" in caplog.text
        assert "calibrar_mercado" in caplog.text

    def test_um_molde_de_cabecalho_CORROMPIDO_tambem_e_feature_OFF(
        self, cal, caplog
    ) -> None:
        """Um molde corrompido nao le a coluna errada — ele recusa TUDO.

        E o preco do erro e maior que o de um glifo corrompido: este molde e o
        portao de layout inteiro, e sem esta mensagem ele recusaria toda pagina,
        para sempre, sem uma linha de erro dizendo por que.
        """
        corrompida = copy.deepcopy(cal)
        cabecalho = dict(corrompida.mercado_cabecalho_de_coluna)
        cabecalho["bytes"] = "nao sou hex"
        corrompida.mercado_cabecalho_de_coluna = cabecalho
        with caplog.at_level("WARNING", logger="l2scanner.mercado_pagina"):
            leitor, _b, _c = montar_leitor(corrompida)
            assert leitor.observar(ler_fixtura(JANELA_NEGOCIACAO)) is None
        assert "corrompido" in caplog.text.lower()


def _quantidades_lidas(cal, caminho: Path, valor_minimo: int) -> list:
    """As quantidades que a pagina produz com o piso de brilho DADO.

    Ela monta um `LeitorDePagina` com a calibracao mexida so nessa chave, e
    devolve a lista de quantidades lidas. Comparar DUAS chamadas desta funcao no
    mesmo arquivo de teste e o que torna a afirmacao verdadeira qualquer que
    tenha sido o numero medido — nenhum total e escolhido pelo plano.
    """
    mexida = copy.deepcopy(cal)
    mexida.mercado_limiar_de_brilho_da_quantidade = int(valor_minimo)
    leitor, _b, _c = montar_leitor(mexida)
    leitor.observar(ler_fixtura(caminho))
    leitura = leitor.ultima_leitura
    assert leitura is not None, f"a pagina {caminho.name} nem foi fatiada"
    return [linha.quantidade for linha in leitura.linhas]


class TestOPisoDeBrilhoDaQuantidadeChegaAProducao:
    """O ramo NAO e escolhido pelo teste: ele e DERIVADO do valor gravado.

    Iguais ao piso compartilhado -> ramo REPROVADO da Task 1, e o criterio e
    IGUALDADE. Diferentes -> ramo PROPOSTO, e o criterio e desigualdade estrita.
    Escrito assim, o teste continua verdadeiro qualquer que tenha sido a
    medicao, e nenhum numero entra aqui escolhido a mao.
    """

    def test_o_rendimento_da_coluna_Quantity_cobra_o_ramo_CERTO(
        self, cal
    ) -> None:
        gravado = int(cal.mercado_limiar_de_brilho_da_quantidade)
        antes = _quantidades_lidas(cal, JANELA_TOOLTIP, VALOR_MINIMO_DO_TEXTO)
        depois = _quantidades_lidas(cal, JANELA_TOOLTIP, gravado)
        if gravado == VALOR_MINIMO_DO_TEXTO:
            # Ramo REPROVADO: o piso medido E o piso compartilhado, e a
            # desigualdade seria falsa POR CONSTRUCAO. A coluna le exatamente o
            # que lia, e o que muda e so o CONTRATO — o piso deixou de ser
            # implicito e passou a ser um numero conferido no arranque.
            assert len(depois) == len(antes)
        else:
            assert len(depois) > len(antes)
            assert all(q == 1 for q in depois)

    def test_as_colunas_de_MOEDA_leem_EXATAMENTE_os_mesmos_digitos(
        self, cal
    ) -> None:
        """Preso por VALOR sobre fixtura versionada, nos dois ramos.

        Um total que mude significa que o piso da Quantity vazou para a coluna
        de moeda — e ali a palavra de sufixo mora entre V=120 e V=173, esperando
        para entrar na celula.
        """
        for caminho, esperado in (
            (JANELA_F005, TOTAIS_DO_TRACER_F005),
            (JANELA_NEGOCIACAO, TOTAIS_DO_TRACER_F010),
        ):
            leitor, _b, _c = montar_leitor(cal)
            leitor.observar(ler_fixtura(caminho))
            leitura = leitor.ultima_leitura
            assert leitura is not None
            lidas = {
                linha.indice: (linha.total_em_centesimos, linha.quantidade)
                for linha in leitura.linhas
            }
            for indice, par in esperado.items():
                assert lidas[indice] == par, (caminho.name, indice)

    def test_a_chave_da_fixtura_e_copia_VERBATIM_da_producao(self, cal) -> None:
        """A fixtura nunca inventa um valor proprio.

        Se ela inventasse, teste e producao passariam a medir coisas
        diferentes — e o teste ficaria verde sobre um piso que a maquina do
        usuario nunca usou.
        """
        valor = cal.mercado_limiar_de_brilho_da_quantidade
        assert isinstance(valor, int) and not isinstance(valor, bool)
        assert 1 <= valor <= 254


class TestAFolgaDeColaChegaAProducaoPeloPORTAO_POR_AUSENCIA:
    """A AUSENCIA liga a GUARDA. Ela e a UNICA ausencia da fase que NAO desliga
    a leitura inteira, e a razao e que aqui a ausencia degrada para MAIS SEGURO:
    a celula com run largo cai FECHADA, em vez de virar numero errado plausivel.
    """

    def _sem_a_folga(self, cal: Calibracao) -> Calibracao:
        copia = copy.deepcopy(cal)
        copia.mercado_folga_de_cola_do_glifo = None
        return copia

    def test_sem_a_chave_a_leitura_CONTINUA_acontecendo(self, cal) -> None:
        """Ela NAO entra em `_calibrado`: uma guarda que degrada para seguro nao
        pode impedir a leitura de acontecer."""
        leitor, barata, conferencia = montar_leitor(self._sem_a_folga(cal))
        leitor.observar(ler_fixtura(JANELA_NEGOCIACAO))
        leitura = leitor.ultima_leitura
        assert leitura is not None
        assert leitura.linhas
        assert barata.chamadas > 0 and conferencia.chamadas > 0

    def test_sem_a_chave_o_aviso_e_ALTO_e_diz_o_que_rodar(
        self, cal, caplog
    ) -> None:
        with caplog.at_level("WARNING", logger="l2scanner.mercado_pagina"):
            leitor, _b, _c = montar_leitor(self._sem_a_folga(cal))
            leitor.observar(ler_fixtura(JANELA_NEGOCIACAO))
        assert "mercado_folga_de_cola_do_glifo" in caplog.text
        assert "medir_largura_de_run" in caplog.text

    def test_sem_a_chave_nada_LEVANTA(self, cal) -> None:
        """Um `raise` aqui derrubaria o scanner que existe para avisar morte."""
        leitor, _b, _c = montar_leitor(self._sem_a_folga(cal))
        assert leitor.observar(ler_fixtura(JANELA_NEGOCIACAO)) is not None or True

    def test_as_colunas_de_MOEDA_leem_o_MESMO_com_e_sem_a_chave(
        self, cal
    ) -> None:
        """As linhas do tracer nao tem run largo: elas NAO PODEM mudar.

        Este e o criterio central da onda — se um total mudar, o mecanismo
        vazou para quem nao pediu.
        """
        for calibracao in (cal, self._sem_a_folga(cal)):
            for caminho, esperado in (
                (JANELA_F005, TOTAIS_DO_TRACER_F005),
                (JANELA_NEGOCIACAO, TOTAIS_DO_TRACER_F010),
            ):
                leitor, _b, _c = montar_leitor(calibracao)
                leitor.observar(ler_fixtura(caminho))
                leitura = leitor.ultima_leitura
                assert leitura is not None
                lidas = {
                    linha.indice: (linha.total_em_centesimos, linha.quantidade)
                    for linha in leitura.linhas
                }
                for indice, par in esperado.items():
                    assert lidas[indice] == par, (caminho.name, indice)

    def test_a_chave_da_fixtura_e_copia_VERBATIM_da_producao(self, cal) -> None:
        valor = cal.mercado_folga_de_cola_do_glifo
        assert isinstance(valor, int) and not isinstance(valor, bool)
        assert 0 <= valor <= TETO_DA_FOLGA_DE_COLA

    def test_a_folga_chega_ate_ler_linha(self, cal) -> None:
        """Por `inspect.signature`, e nao por leitura de codigo."""
        parametros = inspect.signature(ler_linha).parameters
        assert (
            parametros["folga_de_cola"].default is inspect.Parameter.empty
        )


# ===========================================================================
# O ESTABILIZADOR COMPLETO (02-05)
# ===========================================================================
#
# As duas guardas que faltavam: o CONGELAMENTO de captura, que olha a JANELA
# INTEIRA, e o ACORDO entre dois frames sobre a TUPLA PARSEADA das posicoes
# aceitas em AMBOS — com o minimo de posicoes comparadas lido do
# `calibration.json`.
#
# O QUE ESTE ARQUIVO NAO PRENDE, DE PROPOSITO: os valores exatos de score e de
# dispersao. Eles mudam com a convencao de recorte e com a calibracao do
# usuario. O que se afirma aqui e RELACAO e BORDA — duas janelas iguais nao
# congelam, tres congelam — e nunca um numero absoluto escolhido a mao.


class TestOCongelamentoDeCaptura:
    """Tres janelas consecutivas bit-identicas = captura congelada (D-19).

    A COMPARACAO E SOBRE A JANELA INTEIRA, E ISSO CONTRADIZ A LEITURA INGENUA
    DE LEIT-03. Medido na secao 9 do spike: o painel e BIT-ESTAVEL — o mundo
    atras mudou completamente e o retangulo da ancora nao mudou um bit. Grade
    identica entre frames e o caso NORMAL de uma pagina parada, e usa-la como
    sinal de congelamento daria falso alarme o tempo todo.
    """

    def test_a_regra_e_TRES_e_esta_escrita_como_constante(self) -> None:
        assert JANELAS_IGUAIS_PARA_CONGELAR == 3

    def test_DUAS_janelas_bit_identicas_ainda_NAO_congelam(self, cal) -> None:
        """A borda de baixo. Uma pagina parada produz janelas quase iguais."""
        leitor, _b, _c = montar_leitor(cal)
        janela = ler_fixtura(JANELA_F005)
        leitor.observar(janela)
        leitor.observar(janela.copy())
        assert leitor.frames_congelados == 0

    def test_TRES_janelas_bit_identicas_CONGELAM(self, cal) -> None:
        """A borda de cima, no mesmo teste-irmao da de baixo."""
        leitor, _b, _c = montar_leitor(cal)
        janela = ler_fixtura(JANELA_F005)
        for _ in range(3):
            leitor.observar(janela.copy())
        assert leitor.frames_congelados >= 1

    def test_congelada_NENHUMA_pagina_e_aceita(self, cal) -> None:
        """Mesmo com o acordo trivial de um frame consigo mesmo."""
        leitor, _b, _c = montar_leitor(cal)
        janela = ler_fixtura(JANELA_F005)
        aceitas = [leitor.observar(janela.copy()) for _ in range(5)]
        assert aceitas[2:] == [None, None, None]

    def test_o_aviso_do_congelamento_e_ALTO_e_diz_o_que_houve(
        self, cal, caplog
    ) -> None:
        leitor, _b, _c = montar_leitor(cal)
        janela = ler_fixtura(JANELA_F005)
        with caplog.at_level("WARNING", logger="l2scanner.mercado_pagina"):
            for _ in range(3):
                leitor.observar(janela.copy())
        assert "congelada" in caplog.text.lower()

    def test_depois_de_uma_janela_DIFERENTE_a_contagem_zera(self, cal) -> None:
        """A corrida de iguais e um run, e ele quebra na primeira diferenca."""
        leitor, _b, _c = montar_leitor(cal)
        janela = ler_fixtura(JANELA_F005)
        outra = ler_fixtura(JANELA_F010)
        leitor.observar(janela)
        leitor.observar(janela.copy())
        leitor.observar(outra)
        congelados_antes = leitor.frames_congelados
        leitor.observar(outra.copy())
        assert leitor.frames_congelados == congelados_antes

    def test_janelas_de_TAMANHOS_diferentes_nunca_sao_iguais(self, cal) -> None:
        """`np.array_equal` responde False para formas diferentes, sem levantar.

        O usuario redimensiona a janela do jogo, e o tick seguinte chega com
        outra forma. Um `==` elemento a elemento levantaria aqui dentro.
        """
        leitor, _b, _c = montar_leitor(cal)
        janela = ler_fixtura(JANELA_F005)
        leitor.observar(janela)
        leitor.observar(janela[:-10, :-10].copy())
        leitor.observar(janela)
        assert leitor.frames_congelados == 0

    def test_a_janela_guardada_e_uma_COPIA_e_nao_o_buffer_do_chamador(
        self, cal
    ) -> None:
        """Um backend que REUSA o proprio buffer criaria um congelamento eterno.

        Se guardassemos a referencia, escrever o frame seguinte por cima do
        mesmo array faria a comparacao dar sempre igual — o falso positivo
        exato que este detector existe para nao produzir, invertido.
        """
        leitor, _b, _c = montar_leitor(cal)
        buffer = ler_fixtura(JANELA_F005)
        leitor.observar(buffer)
        buffer[:] = ler_fixtura(JANELA_F010)
        leitor.observar(buffer)
        buffer[:] = ler_fixtura(JANELA_F005)
        leitor.observar(buffer)
        assert leitor.frames_congelados == 0

    def test_o_modulo_NAO_usa_hash_para_comparar_janela(self) -> None:
        """MEDIDO: `np.array_equal` 0,89 ms contra sha256 3,70 e blake2b 6,81.

        Hash e 4 a 15 vezes mais caro e nao compra nada, porque a regra exige
        lembrar de UM frame e um contador, e nao de muitos.
        """
        import l2scanner.mercado_pagina as modulo

        fonte = inspect.getsource(modulo)
        assert "hashlib" not in fonte
        assert "array_equal" in fonte


class TestOMinimoDePosicoesComparadas:
    """T-02-26: o acordo trivial sobre pouquissimas linhas nao aceita pagina."""

    def test_a_chave_NULA_desliga_a_leitura_com_aviso_alto(
        self, cal, caplog
    ) -> None:
        """Um piso ausente valeria ZERO, que e o acordo trivial de volta."""
        sem_piso = copy.deepcopy(cal)
        sem_piso.mercado_minimo_de_linhas_comparadas = None
        leitor, barata, conferencia = montar_leitor(sem_piso)
        with caplog.at_level("WARNING", logger="l2scanner.mercado_pagina"):
            assert leitor.observar(ler_fixtura(JANELA_F005)) is None
        assert leitor.ultima_leitura is None
        assert barata.chamadas == conferencia.chamadas == 0
        assert "mercado_minimo_de_linhas_comparadas" in caplog.text

    def test_um_piso_ALTO_DEMAIS_recusa_a_pagina_que_de_outro_modo_passaria(
        self, cal
    ) -> None:
        """O ramo e DERIVADO: a mesma pagina, so o piso muda.

        Nenhum numero e escolhido pelo teste — ele compara o valor gravado com
        um piso maior que a pagina inteira e cobra a diferenca de veredito.
        """
        leitor, _b, _c = montar_leitor(cal)
        assert leitor.observar(ler_fixtura(JANELA_F005)) is None
        assert leitor.observar(ler_fixtura(JANELA_F005_REPETIDA)) is not None

        exigente = copy.deepcopy(cal)
        exigente.mercado_minimo_de_linhas_comparadas = int(
            cal.mercado_grade["linhas_por_pagina"]
        )
        duro, _b, _c = montar_leitor(exigente)
        duro.observar(ler_fixtura(JANELA_F005))
        assert duro.observar(ler_fixtura(JANELA_F005_REPETIDA)) is None
        assert duro.paginas_perdidas >= 1

    def test_a_pagina_recusada_pelo_minimo_reporta_o_MOTIVO(self, cal) -> None:
        exigente = copy.deepcopy(cal)
        exigente.mercado_minimo_de_linhas_comparadas = int(
            cal.mercado_grade["linhas_por_pagina"]
        )
        leitor, _b, _c = montar_leitor(exigente)
        leitor.observar(ler_fixtura(JANELA_F005))
        leitor.observar(ler_fixtura(JANELA_F005_REPETIDA))
        assert leitor.ultimo_motivo_de_perda is not None
        assert "minimo" in leitor.ultimo_motivo_de_perda.lower()

    def test_o_piso_da_fixtura_e_copia_VERBATIM_da_producao(self, cal) -> None:
        valor = cal.mercado_minimo_de_linhas_comparadas
        assert isinstance(valor, int) and not isinstance(valor, bool)
        assert 1 <= valor <= int(cal.mercado_grade["linhas_por_pagina"])


class TestOAcordoSobreAsPosicoesACEITAS_EM_AMBOS:
    """D-15: a linha DESCARTADA fica FORA da comparacao e nao e desacordo."""

    def test_tupla_comparavel_e_a_PARSEADA_e_nao_o_indice_nem_o_nome(
        self,
    ) -> None:
        """O `nome_exibido` fica de fora: o OCR oscila um caractere sem mudar
        a serie, e a serie e o que a Fase 3 grava. O `serie_nova` fica de fora
        porque ele e True no primeiro frame e False no segundo POR CONSTRUCAO —
        inclui-lo tornaria o acordo impossivel."""
        linha = LinhaLida(
            indice=3,
            chave_da_serie="item#0",
            nome_exibido="Item",
            total_em_centesimos=1234,
            quantidade=2,
            serie_nova=True,
            residuo_do_cruzamento=0,
        )
        outra = LinhaLida(
            indice=3,
            chave_da_serie="item#0",
            nome_exibido="Ilem",
            total_em_centesimos=1234,
            quantidade=2,
            serie_nova=False,
            residuo_do_cruzamento=80,
        )
        assert tupla_comparavel(linha) == tupla_comparavel(outra)

    def test_tupla_comparavel_SEPARA_totais_diferentes(self) -> None:
        base = dict(
            indice=3,
            chave_da_serie="item#0",
            nome_exibido="Item",
            quantidade=2,
            serie_nova=False,
            residuo_do_cruzamento=None,
        )
        assert tupla_comparavel(
            LinhaLida(total_em_centesimos=1234, **base)
        ) != tupla_comparavel(LinhaLida(total_em_centesimos=1235, **base))

    def test_posicoes_comparaveis_e_a_INTERSECAO_e_nao_a_uniao(self) -> None:
        a = _leitura_falsa({0: (1, 1), 1: (2, 2), 3: (4, 4)})
        b = _leitura_falsa({1: (2, 2), 3: (4, 4), 5: (6, 6)})
        assert posicoes_comparaveis(a, b) == [1, 3]

    def test_posicoes_comparaveis_sai_ORDENADA(self) -> None:
        a = _leitura_falsa({5: (1, 1), 0: (2, 2), 3: (3, 3)})
        b = _leitura_falsa({3: (3, 3), 5: (1, 1), 0: (2, 2)})
        assert posicoes_comparaveis(a, b) == [0, 3, 5]

    def test_a_linha_DESCARTADA_num_dos_frames_nao_e_desacordo(
        self, cal
    ) -> None:
        """O caso vivo: a tooltip cobre a linha 3 no frame A e sai no frame B.

        As duas listas tem TAMANHOS diferentes, e a leitura fiel de D-15 e
        comparar so as posicoes aceitas em AMBOS. Comparar as listas inteiras
        faria uma tooltip passageira impedir para sempre o acordo de uma pagina
        parada.
        """
        com_a_linha_3 = _leitura_falsa({0: (1, 1), 1: (2, 2), 3: (4, 4)})
        sem_a_linha_3 = _leitura_falsa({0: (1, 1), 1: (2, 2)}, descartadas=(3,))
        assert paginas_concordam(com_a_linha_3, sem_a_linha_3) is True

    def test_um_valor_DIFERENTE_numa_posicao_comum_E_desacordo(self) -> None:
        a = _leitura_falsa({0: (1, 1), 1: (2, 2)})
        b = _leitura_falsa({0: (1, 1), 1: (2, 9)})
        assert paginas_concordam(a, b) is False


class TestOsContadoresDasDuasMetades:
    """`paginas_lidas` e `paginas_perdidas` — a superficie que LEIT-04 exibe.

    Esta fase PRODUZ o numero e NAO desenha console.
    """

    def test_os_contadores_nascem_em_ZERO(self, cal) -> None:
        leitor, _b, _c = montar_leitor(cal)
        assert leitor.paginas_lidas == 0
        assert leitor.paginas_perdidas == 0
        assert leitor.frames_congelados == 0
        assert leitor.linhas_descartadas == 0

    def test_a_pagina_aceita_sobe_LIDAS_e_o_primeiro_frame_sobe_PERDIDAS(
        self, cal
    ) -> None:
        """O primeiro frame nao tem anterior para comparar: ele nao foi lido.

        Contar isso como perda e honesto — aquele tick realmente nao produziu
        pagina — e e o que fecha a soma. A 1 Hz com o painel aberto por uma
        hora, isso e UM tick em 3.600.
        """
        leitor, _b, _c = montar_leitor(cal)
        leitor.observar(ler_fixtura(JANELA_F005))
        assert (leitor.paginas_lidas, leitor.paginas_perdidas) == (0, 1)
        leitor.observar(ler_fixtura(JANELA_F005_REPETIDA))
        assert (leitor.paginas_lidas, leitor.paginas_perdidas) == (1, 1)

    def test_uma_pagina_de_outro_LAYOUT_nao_conta_como_lida_nem_perdida(
        self, cal
    ) -> None:
        leitor, _b, _c = montar_leitor(cal)
        leitor.observar(ler_fixtura(JANELA_ADENA))
        assert leitor.paginas_lidas == 0
        assert leitor.paginas_perdidas == 0
        assert leitor.paginas_de_outro_layout == 1

    def test_linhas_descartadas_ACUMULA_entre_ticks(self, cal) -> None:
        leitor, _b, _c = montar_leitor(cal)
        leitor.observar(ler_fixtura(JANELA_TOOLTIP))
        primeira = leitor.linhas_descartadas
        leitor.observar(ler_fixtura(JANELA_TOOLTIP))
        assert leitor.linhas_descartadas >= primeira
        assert primeira == len(leitor.ultima_leitura.descartadas)

    def test_a_SOMA_dos_baldes_cobre_todo_tick_com_painel_aberto(
        self, cal
    ) -> None:
        """A identidade que faz a contagem ser afirmavel, e nao so plausivel.

        Um tick com o painel aberto cai em EXATAMENTE um balde: outro layout,
        vazia, perdida ou lida. O congelamento e contado a parte porque ele
        recusa ANTES de procurar o painel — captura congelada e propriedade da
        CAPTURA, e nao da pagina.
        """
        leitor, _b, _c = montar_leitor(cal)
        for caminho in (
            JANELA_F005,
            JANELA_F005_REPETIDA,
            JANELA_ADENA,
            JANELA_TOOLTIP,
            JANELA_F010,
            JANELA_NEGOCIACAO,
        ):
            leitor.observar(ler_fixtura(caminho))
        assert leitor.ticks_com_painel_aberto == (
            leitor.paginas_de_outro_layout
            + leitor.paginas_vazias
            + leitor.paginas_perdidas
            + leitor.paginas_lidas
        )
        assert leitor.ticks_com_painel_aberto > 0


class TestAOrdemDaPaginaAceita:
    """A ordem e CONTRATO: a Fase 3 grava uma observacao por linha."""

    def test_as_linhas_saem_de_CIMA_para_BAIXO(self, cal) -> None:
        leitor, _b, _c = montar_leitor(cal)
        leitor.observar(ler_fixtura(JANELA_F005))
        pagina = leitor.observar(ler_fixtura(JANELA_F005_REPETIDA))
        assert pagina is not None
        indices = [linha.indice for linha in pagina.linhas]
        assert indices == sorted(indices)
        assert len(set(indices)) == len(indices)


class TestAPaginaQUE_MUDOU:
    """Rolagem: as linhas mudaram, e o frame novo vira a nova referencia."""

    def test_paginas_diferentes_nao_produzem_acordo(self, cal) -> None:
        leitor, _b, _c = montar_leitor(cal)
        assert leitor.observar(ler_fixtura(JANELA_F005)) is None
        assert leitor.observar(ler_fixtura(JANELA_F010)) is None

    def test_o_frame_NOVO_vira_a_nova_referencia(self, cal) -> None:
        """Depois da rolagem, dois frames da pagina NOVA fecham o acordo."""
        leitor, _b, _c = montar_leitor(cal)
        leitor.observar(ler_fixtura(JANELA_F010))
        leitor.observar(ler_fixtura(JANELA_F005))
        assert leitor.observar(ler_fixtura(JANELA_F005_REPETIDA)) is not None

    def test_perder_o_PAINEL_apaga_a_memoria_do_frame_anterior(
        self, cal
    ) -> None:
        """Comparar a pagina de antes com a de depois de o painel sumir
        afirmaria estabilidade sobre uma DESCONTINUIDADE."""
        leitor, _b, _c = montar_leitor(cal)
        leitor.observar(ler_fixtura(JANELA_F005))
        leitor.observar(np.zeros((1392, 1720, 3), dtype=np.uint8))
        assert leitor.observar(ler_fixtura(JANELA_F005_REPETIDA)) is None
