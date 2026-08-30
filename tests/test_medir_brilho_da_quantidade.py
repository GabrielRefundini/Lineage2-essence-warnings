"""O PISO DE BRILHO PROPRIO da coluna Quantity: o rotulo, a proposta, a recusa.

Tudo aqui roda sobre fixturas VERSIONADAS de `tests/fixtures/mercado/` e sobre
populacoes CONSTRUIDAS a mao, nunca sobre `recordings/` nem sobre o
`calibration.json` da maquina - os dois sao gitignored e nao vem de clone limpo,
entao um teste que dependesse deles ficaria verde nesta maquina e amarelo em
toda outra. A varredura que PRODUZ o numero
(`tools/medir_brilho_da_quantidade.py --gravar`) e outra coisa, roda no checkout
principal, e o numero dela vive no `calibration.json`.

    janela_tooltip_f012.png     a pagina inteira de tooltip/frame_000012; e a
        fixtura do defeito, porque nela `Total` e `Unit price` sao IGUAIS em 9
        das 10 linhas - o que faz a quantidade derivada valer `1` - e a coluna
        Quantity nao le NENHUMA delas no piso compartilhado
    janela_negociacao_f005.png  a pagina de negociacao/frame_000005, com as 4
        linhas que o tracer do 02-04 ja lia
    janela_negociacao_f010.png  a pagina de negociacao/frame_000010

O ROTULO E NAO CIRCULAR, E ESSA E A PROPRIEDADE CENTRAL
---------------------------------------------------------
`quantidade_derivada(total, unitario)` recebe DOIS inteiros e mais nada. Ela nao
ve pixel, nao ve recorte e nao ve a coluna Quantity - e por isso ela pode servir
de gabarito para MEDIR essa coluna. Rotular pelo que a propria coluna le seria
medir a leitura contra ela mesma; foi assim que o 02-02 refutou o rotulo por
pasta de origem.

O TETO E TAO REAL QUANTO O CHAO
--------------------------------
Baixar o piso demais nao volta a falhar FECHADO, passa a falhar ABERTO: sondado
pelo planejador em `scroll-transicao/frame_000016`, com o piso em 150 o `30` da
quantidade vira `38` com score 0,724 e margem 0,127 - os dois acima do piso de
leitura 0,4698 e da margem 0,0370. Por isso a proposta e por VAO entre a pior
leitura certa e a melhor leitura errada, e nao por "o mais baixo que ainda le".
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.identidade import VALOR_MINIMO_DO_TEXTO
from l2scanner.mercado_visao import (
    RastreioDoPainel,
    ancoras_de_calibracao,
    glifos_de_calibracao,
)

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures" / "mercado"
CALIBRACAO = FIXTURES / "calibracao_de_fixture.json"


def _carregar_a_ferramenta(nome: str):
    """`tools/` nao e pacote, entao o import vem do caminho do arquivo."""
    caminho = RAIZ / "tools" / (nome + ".py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    assert spec and spec.loader, f"nao carreguei {caminho}"
    modulo = importlib.util.module_from_spec(spec)
    # Registrar ANTES de executar: `@dataclass` resolve as anotacoes por
    # `sys.modules[cls.__module__]`, e sem isto ele encontra None.
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


ferramenta = _carregar_a_ferramenta("medir_brilho_da_quantidade")

Baldes = ferramenta.Baldes
PASSO_DA_VARREDURA = ferramenta.PASSO_DA_VARREDURA
PISO_COMPARTILHADO = ferramenta.PISO_COMPARTILHADO
propor_o_piso = ferramenta.propor_o_piso
quantidade_derivada = ferramenta.quantidade_derivada
regiao_segura = ferramenta.regiao_segura


# ---------------------------------------------------------------------------
# As populacoes CONSTRUIDAS - baldes por piso, sem tocar em pixel nenhum
# ---------------------------------------------------------------------------


def _baldes(certo: int = 40, nao_le: int = 0, errado: int = 0) -> Baldes:
    """Um balde com `errado` divergencias fabricadas, para a recusa disparar."""
    return Baldes(
        certo=certo,
        nao_le=nao_le,
        errado=tuple(
            (("fabricada", "frame.png", indice), "30", "38")
            for indice in range(errado)
        ),
    )


def _populacao(segura: range, errada: range = range(0)) -> dict:
    """`{piso: Baldes}` sobre as duas faixas, com passo 1 e sem buracos."""
    tabela = {piso: _baldes() for piso in segura}
    tabela.update({piso: _baldes(certo=38, errado=2) for piso in errada})
    return tabela


class TestORotuloDerivadoNaoTocaAColunaQuantity:
    """A propriedade que torna a medicao valida: ela nao se mede a si mesma."""

    def test_a_assinatura_recebe_dois_inteiros_e_mais_nada(self) -> None:
        """Sem recorte, sem moldes, sem piso: nao ha por onde um pixel entrar."""
        import inspect

        assinatura = inspect.signature(quantidade_derivada)
        assert list(assinatura.parameters) == ["total", "unitario"]

    def test_o_caso_conhecido_do_spike_fecha(self) -> None:
        """`40,00` por 48 unidades exibindo `0,83`: residuo 16 contra limite 24."""
        assert quantidade_derivada(4000, 83) == 48

    def test_total_igual_ao_unitario_da_quantidade_1(self) -> None:
        """O caso COMUM do mercado, e o que o defeito derruba inteiro."""
        assert quantidade_derivada(300, 300) == 1

    def test_unitario_zero_nao_produz_rotulo(self) -> None:
        """Dividir por zero nao e um rotulo; e uma linha que ninguem afirmou."""
        assert quantidade_derivada(4000, 0) is None

    def test_um_residuo_que_estoura_o_limite_derivado_nao_produz_rotulo(
        self,
    ) -> None:
        """`11,39` por 6 a `1,89`: residuo 5 contra limite 3. Precisao alta.

        Um rotulo pode ter recall baixo; ele nao pode estar errado. E a linha
        que nao fecha simplesmente nao entra na medicao.
        """
        assert quantidade_derivada(1139, 189) is None


class TestOPassoDaVarreduraEUm:
    """Com passo maior que 1 o piso gravado seria interpolacao, nao medicao."""

    def test_o_passo_e_a_constante_um(self) -> None:
        assert PASSO_DA_VARREDURA == 1

    def test_o_piso_compartilhado_e_o_de_identidade(self) -> None:
        """A ferramenta nao redeclara o 180: ela o importa de onde ele mora."""
        assert PISO_COMPARTILHADO == VALOR_MINIMO_DO_TEXTO


class TestARegiaoSegura:
    """O maior PREFIXO DESCENDENTE de pisos com o balde LE ERRADO vazio."""

    def test_o_prefixo_para_no_primeiro_que_erra(self) -> None:
        tabela = _populacao(range(180, 164, -1), range(164, 144, -1))
        assert regiao_segura(tabela) == tuple(range(180, 164, -1))

    def test_ela_nunca_alcanca_o_segundo_trecho_seguro(self) -> None:
        """Populacao segura em 180..170, errada em 169..165, segura em 164..160."""
        tabela = _populacao(range(180, 169, -1), range(169, 164, -1))
        tabela.update({piso: _baldes() for piso in range(164, 159, -1)})
        assert regiao_segura(tabela) == tuple(range(180, 169, -1))


class TestAPropostaEOULTIMOPISOSEGURO:
    """Nunca a media entre inteiros adjacentes - ela escolheria o que ERRA."""

    def test_segura_em_180_165_e_errada_em_164_propoe_165(self) -> None:
        """A media `(165 + 164) / 2` arredondada para baixo daria 164.

        164 e o piso que ERRA. A reclassificacao o reprovaria e a ferramenta
        devolveria REPROVADO por ARITMETICA, e nao por medicao. Arredondar para
        o lado SEGURO, com passo 1, e escolher o ultimo seguro.
        """
        proposta = propor_o_piso(_populacao(range(180, 164, -1), range(164, 144, -1)))
        assert proposta.veredito == "PROPOSTO"
        assert proposta.piso == 165

    def test_a_folga_ate_o_primeiro_que_erra_vale_um_por_construcao(self) -> None:
        proposta = propor_o_piso(_populacao(range(180, 164, -1), range(164, 144, -1)))
        assert proposta.folga_ate_o_primeiro_que_erra == 1

    def test_a_folga_ate_o_tronco_e_a_que_informa(self) -> None:
        """Piso 165 contra tronco 176: 11 niveis de V de margem."""
        proposta = propor_o_piso(
            _populacao(range(180, 164, -1), range(164, 144, -1)),
            tronco_do_um=176,
        )
        assert proposta.folga_ate_o_tronco == 11

    def test_folga_nula_contra_o_tronco_e_dita_ALTO(self) -> None:
        """Um piso que nao captura o `1` nao serve, ainda que passe nos baldes.

        Com o tronco em 165 e o piso em 165, a mascara e `V > 165`: o proprio
        tronco fica FORA. A ferramenta diz isso em vez de propor um numero que
        passa nos baldes e falha no proposito.
        """
        proposta = propor_o_piso(
            _populacao(range(180, 164, -1), range(164, 144, -1)),
            tronco_do_um=165,
        )
        assert proposta.folga_ate_o_tronco == 0
        assert proposta.captura_o_um is False
        assert "NAO CAPTURA" in proposta.linha_do_veredito


class TestAsQuatroCausasDeRECUSA:
    """Cada uma com mensagem propria: sem isso o numero e atribuido ao errado."""

    def test_o_piso_compartilhado_JA_ERRA_tem_causa_propria(self) -> None:
        """E o comportamento de HOJE que erra, e nao o piso novo que falhou.

        Sem separar as duas causas, o numero que vai para o `WINDOWS.md #16`
        fica atribuido a coisa errada.
        """
        tabela = _populacao(range(179, 144, -1))
        tabela[PISO_COMPARTILHADO] = _baldes(certo=38, errado=2)
        proposta = propor_o_piso(tabela)
        assert proposta.veredito == "REPROVADO"
        assert proposta.causa == "o piso compartilhado JA ERRA"
        assert "comportamento de HOJE" in proposta.linha_do_veredito

    def test_a_regiao_vazia_por_OUTRA_causa_tem_causa_propria(self) -> None:
        """Tabela sem o piso compartilhado: nao ha por onde o prefixo comecar."""
        proposta = propor_o_piso(_populacao(range(179, 144, -1)))
        assert proposta.veredito == "REPROVADO"
        assert proposta.causa == "regiao segura vazia"

    def test_o_CONJUNTO_seguro_DESCONTINUO_reprova(self) -> None:
        """Segura em 180..170, errada em 169..165, segura de novo em 164..160.

        Sobre um conjunto descontinuo o pior seguro fica ABAIXO do melhor que
        erra, o vao se INVERTE, e qualquer escolha calculada dentro dele cai na
        zona de erro com aparencia de proposta legitima.
        """
        tabela = _populacao(range(180, 169, -1), range(169, 164, -1))
        tabela.update({piso: _baldes() for piso in range(164, 159, -1)})
        proposta = propor_o_piso(tabela)
        assert proposta.veredito == "REPROVADO"
        assert proposta.causa == "conjunto seguro DESCONTINUO"
        assert proposta.piso is None

    def test_o_predicado_da_descontinuidade_e_sobre_o_CONJUNTO_INTEIRO(
        self,
    ) -> None:
        """Escrito sobre o retorno de `regiao_segura` ele nunca dispararia.

        `regiao_segura` devolve um prefixo CONTIGUO por construcao. A pergunta
        executavel e outra: existe piso seguro ABAIXO do primeiro que erra?
        """
        tabela = _populacao(range(180, 169, -1), range(169, 164, -1))
        tabela.update({piso: _baldes() for piso in range(164, 159, -1)})
        assert ferramenta.ha_seguro_abaixo_do_primeiro_que_erra(tabela) is True
        assert (
            ferramenta.ha_seguro_abaixo_do_primeiro_que_erra(
                _populacao(range(180, 164, -1), range(164, 144, -1))
            )
            is False
        )

    def test_a_RECLASSIFICACAO_do_piso_escolhido_pode_reprovar(self) -> None:
        """Um piso proposto e um piso MEDIDO, e a medicao dele e refeita.

        O criterio nao e "os vizinhos estao limpos": e "o balde LE ERRADO DELE
        esta vazio", conferido na propria linha dele.
        """
        proposta = propor_o_piso(
            _populacao(range(180, 164, -1), range(164, 144, -1)),
            reclassificar=lambda _piso: _baldes(certo=38, errado=1),
        )
        assert proposta.veredito == "REPROVADO"
        assert proposta.causa == "a reclassificacao do piso escolhido REPROVOU"

    def test_o_piso_escolhido_tem_a_PROPRIA_linha_com_os_tres_baldes(
        self,
    ) -> None:
        """Um piso proposto sem a propria linha na tabela e interpolacao."""
        proposta = propor_o_piso(_populacao(range(180, 164, -1), range(164, 144, -1)))
        assert proposta.baldes_do_piso is not None
        assert proposta.baldes_do_piso.errado == ()
        assert proposta.baldes_do_piso.certo > 0


class TestOCensoEIMPORTADOENaoCOPIADO:
    """IDENTIDADE, e nao igualdade: uma copia envelheceria em separado."""

    def test_o_censo_e_o_MESMO_OBJETO_de_medir_oclusao(self) -> None:
        """O modulo de referencia vem de `sys.modules`, que o proprio
        `_carregar_o_censo` registrou. Um segundo `importlib` produziria outro
        objeto e a identidade falharia sobre codigo CORRETO.
        """
        oclusao = sys.modules["medir_oclusao"]
        assert ferramenta.GRAVACOES_DO_CENSO is oclusao.GRAVACOES_DO_CENSO
        assert ferramenta.MOTIVO_PARA_IGNORAR is oclusao.MOTIVO_PARA_IGNORAR

    def test_sao_as_oito_gravacoes(self) -> None:
        assert len(ferramenta.GRAVACOES_DO_CENSO) == 8


class TestAParadaQuandoFaltaMaterial:
    """Medir sobre outro conjunto produz numero que nao se compara com nada."""

    def test_diretorio_de_gravacoes_inexistente_devolve_2(self, tmp_path) -> None:
        codigo = ferramenta.main(
            [
                "--gravacoes",
                str(tmp_path / "nao-existe"),
                "--calibracao",
                str(CALIBRACAO),
            ]
        )
        assert codigo == 2

    def test_uma_pasta_so_devolve_3_e_NOMEIA_as_sete_que_faltam(
        self, tmp_path, capsys
    ) -> None:
        (tmp_path / ferramenta.GRAVACOES_DO_CENSO[0]).mkdir()
        codigo = ferramenta.main(
            ["--gravacoes", str(tmp_path), "--calibracao", str(CALIBRACAO)]
        )
        assert codigo == 3
        saida = capsys.readouterr().out
        for nome in ferramenta.GRAVACOES_DO_CENSO[1:]:
            assert nome in saida
        assert ferramenta.GRAVACOES_DO_CENSO[0] not in saida.split("AUSENTE")[1]


class TestAFixturaDoDEFEITO:
    """`janela_tooltip_f012.png`: rotulo `1` e ZERO leituras. E o caso base."""

    @pytest.fixture(scope="class")
    def cal(self) -> Calibracao:
        return Calibracao.carregar(CALIBRACAO)

    @pytest.fixture(scope="class")
    def celulas(self, cal):
        return _celulas_da_fixtura(cal, "janela_tooltip_f012.png")

    def test_nove_das_dez_linhas_tem_rotulo_derivado_1(self, celulas) -> None:
        """MEDIDO, e nao suposto: a linha 5 nao le Total nem Unit price.

        A sondagem do planejamento dizia "as dez linhas"; a medicao diz NOVE, e
        a medicao manda. A decima nao tem rotulo porque as duas colunas de moeda
        dela nao leram - ela nao entra na medicao nem para bem nem para mal.
        """
        rotulos = [c["rotulo"] for c in celulas]
        assert rotulos.count(1) == 9
        assert rotulos.count(None) == 1

    def test_no_piso_COMPARTILHADO_nenhuma_quantidade_atravessa(
        self, celulas
    ) -> None:
        """O defeito, preso por valor: 9 linhas rotuladas, 0 lidas."""
        lidas = [
            c["lido"][PISO_COMPARTILHADO]
            for c in celulas
            if c["rotulo"] is not None
        ]
        assert lidas == [None] * 9

    def test_abaixo_do_TRONCO_as_mesmas_linhas_passam_a_ler_1(
        self, celulas
    ) -> None:
        """O piso 170 e so uma sonda deste teste, e nunca o piso de producao.

        Quem escolhe o piso de producao e a varredura sobre as 8 gravacoes, com
        os tres baldes e as duas folgas. Aqui ele serve para provar que o
        MECANISMO e o brilho, e nao o molde nem a margem.
        """
        lidas = [c["lido"][170] for c in celulas if c["rotulo"] is not None]
        assert lidas == ["1"] * 9


class TestOCustoNaColunaDeMOEDA:
    """Um piso GLOBAL arrasta a palavra de sufixo para dentro da celula."""

    @pytest.fixture(scope="class")
    def cal(self) -> Calibracao:
        return Calibracao.carregar(CALIBRACAO)

    @pytest.fixture(scope="class")
    def celulas(self, cal):
        return _celulas_da_fixtura(cal, "janela_negociacao_f010.png")

    def test_no_piso_compartilhado_o_custo_e_zero_por_construcao(
        self, celulas
    ) -> None:
        custo = ferramenta.custo_na_coluna_de_moeda(celulas, PISO_COMPARTILHADO)
        assert custo["deixaram_de_ler"] == 0
        assert custo["passaram_a_ler_outra_coisa"] == 0

    def test_um_piso_mais_baixo_cobra_um_preco_POSITIVO(self, celulas) -> None:
        """MEDIDO: `18,90` vira `18,907` ja no piso 170, porque a palavra
        `XM Coin` vive entre V=120 e V=173 e entra no recorte.
        """
        custo = ferramenta.custo_na_coluna_de_moeda(celulas, 170)
        assert custo["deixaram_de_ler"] + custo["passaram_a_ler_outra_coisa"] > 0


class TestAGravacaoNaoApagaOsMoldes:
    """Load-mutate-save. Montar uma `Calibracao` do zero foi a janela #13."""

    def test_gravar_muta_UMA_chave_e_preserva_moldes_e_ancoras(
        self, tmp_path
    ) -> None:
        destino = tmp_path / "calibration.json"
        destino.write_text(
            CALIBRACAO.read_text(encoding="utf-8"), encoding="utf-8"
        )
        antes = json.loads(destino.read_text(encoding="utf-8"))
        ferramenta.gravar(destino, 165)
        depois = json.loads(destino.read_text(encoding="utf-8"))

        assert depois["mercado_limiar_de_brilho_da_quantidade"] == 165
        assert len(depois["mercado_templates_de_digito"]) == 13
        assert len(depois["mercado_ancoras"]) == 3
        assert depois["mercado_templates_de_digito"] == antes[
            "mercado_templates_de_digito"
        ]
        assert depois["mercado_ancoras"] == antes["mercado_ancoras"]
        assert set(depois) - set(antes) == {
            "mercado_limiar_de_brilho_da_quantidade"
        }

    def test_gravar_usa_os_replace_e_nao_escrita_direta(self) -> None:
        """Uma escrita interrompida no meio deixaria o arquivo do usuario em
        pedacos, e ele carrega 13 moldes que so a mao dele produz.
        """
        import inspect

        assert "os.replace" in inspect.getsource(ferramenta.gravar)


# ---------------------------------------------------------------------------
# O apoio das fixturas - a mesma geometria calibrada da producao
# ---------------------------------------------------------------------------


def _celulas_da_fixtura(cal: Calibracao, nome: str) -> list:
    """As dez linhas de uma janela versionada, varridas em toda a faixa."""
    janela = cv2.imread(str(FIXTURES / nome))
    assert janela is not None, f"nao decodifiquei a fixtura {nome}"
    rastreio = RastreioDoPainel(
        ancoras_de_calibracao(cal.mercado_ancoras),
        float(cal.mercado_limiar_da_ancora),
    )
    voto = rastreio.observar(janela)
    assert voto.aberto and rastreio.origem is not None
    moldes = glifos_de_calibracao(cal.mercado_templates_de_digito)
    return ferramenta.varrer_uma_janela(
        janela,
        rastreio.origem,
        cal,
        moldes,
        nome_da_gravacao="fixtura",
        nome_do_arquivo=nome,
    )


def test_a_ferramenta_nao_importa_de_calibrar_mercado() -> None:
    """A seta aponta ferramenta -> puro, e nunca ferramenta -> interativo.

    `calibrar_mercado.py` chama `tornar_consciente_de_dpi()` NO IMPORT e carrega
    as chamadas de JANELA do OpenCV. Uma varredura offline que o importasse
    pagaria esse efeito colateral so por existir.
    """
    fonte = (RAIZ / "tools" / "medir_brilho_da_quantidade.py").read_text(
        encoding="utf-8"
    )
    assert "calibrar_mercado" not in fonte


def test_a_faixa_da_varredura_mostra_os_DOIS_lados_do_vao() -> None:
    """Do piso compartilhado ate bem abaixo do tronco medido do `1`.

    Uma faixa que parasse no primeiro piso que le mostraria so o lado bom, e o
    relatorio nao teria como afirmar que existe um TETO.
    """
    faixa = ferramenta.faixa_de_candidatos()
    assert faixa[0] == PISO_COMPARTILHADO
    assert faixa[-1] < 160
    assert np.all(np.diff(faixa) == -PASSO_DA_VARREDURA)
