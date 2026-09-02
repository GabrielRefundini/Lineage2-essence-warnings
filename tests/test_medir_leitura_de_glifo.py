"""A LEITURA de glifo: o piso proprio dela, e a guarda de cruzamento.

Tudo aqui roda sobre fixtures VERSIONADAS em `tests/fixtures/mercado/`, e nunca
sobre `recordings/` nem sobre o `calibration.json` - os dois sao gitignored e nao
vem de clone limpo, entao um teste que dependesse deles ficaria verde nesta
maquina e amarelo em toda outra. A varredura que PRODUZ os numeros
(`tools/medir_leitura_de_glifo.py`) e outra coisa e roda no checkout principal.

    glifos_precos_f010.png      240x45x6, coluna Total de pagina-cheia/f010
        `100,00`, `3,00`, `18,90`, `7,50`, `18,00`, `2,45`
    glifos_unitario_f010.png    Unit price do mesmo frame, `6,00`
    glifos_quantidade_f012.png  123x45x3, coluna Quantity de
        scroll-transicao/frame_000012, linhas 5 a 7 da pagina: `10`, `48`, `5`
        - as tres que a secao 4 do SPIKE-RESPOSTAS nomeia, ao lado dos totais
        `24,90`, `40,00` e `17,00` e dos unitarios `2,49`, `0,83` e `3,40`

O PISO DE LEITURA NAO E `mercado_limiar_de_glifo`
--------------------------------------------------
`mercado_limiar_de_glifo = 0.8555` e o limiar de COLISAO, derivado de
`(1.0 + pior_par)/2` sobre molde-contra-molde. Ele certifica que o CONJUNTO de
moldes e separavel; ele nao foi medido sobre glifo REAL de tela. A pesquisa
mediu 2.057 glifos de campo e achou 18% deles abaixo dele, com o `8` tendo
MEDIANA 0,7242 contra o proprio molde - um piso ali mataria todo preco com `8`.

`TestOLimiarDeCOLISAONaoServeDePiso` prende isso por escrito: sobre as MESMAS
seis linhas, o piso de colisao perde leitura que o piso medido mantem.

OS MOLDES SAO CONSTRUIDOS DAS PROPRIAS FIXTURES
------------------------------------------------
Pelo mesmo motivo de `test_mercado_glifos.py`: os 13 moldes de verdade moram no
`calibration.json`, que e estado de maquina. Aqui os 11 glifos de um caractere
sao recortados das duas fixtures de preco pelos rotulos conhecidos, na mesma
convencao de faixa COMPARTILHADA de `segmentar_glifos`. O primeiro corte de cada
rotulo vence.

Isso nao torna o teste circular: o `8` do molde sai de `18,90` (banda de fundo
PAR) e e cobrado contra o `8` de `18,00` (banda IMPAR), que e exatamente o par
que a medicao de `calibrar_mercado.py:1364-1375` mostrou NAO casar 1,000.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.mercado_leitura import segmentar_glifos
from l2scanner.mercado_pagina import LeitorDePagina
from l2scanner.identidade import VALOR_MINIMO_DO_TEXTO, mascara_de_texto

RAIZ = Path(__file__).resolve().parent.parent


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


ferramenta = _carregar_a_ferramenta("medir_leitura_de_glifo")

DETECCAO_MINIMA = ferramenta.DETECCAO_MINIMA
FECHAMENTO_MINIMO = ferramenta.FECHAMENTO_MINIMO
LinhaMedida = ferramenta.LinhaMedida
centesimos_de_moeda = ferramenta.centesimos_de_moeda
classificar_celula = ferramenta.classificar_celula
inteiro_de_quantidade = ferramenta.inteiro_de_quantidade
limite_derivado_do_cruzamento = ferramenta.limite_derivado_do_cruzamento
residuo_do_cruzamento = ferramenta.residuo_do_cruzamento
veredito_da_guarda = ferramenta.veredito_da_guarda

FIXTURES = Path(__file__).parent / "fixtures" / "mercado"
ALTURA_DA_LINHA = 45

ROTULOS_DOS_PRECOS = ("100,00", "3,00", "18,90", "7,50", "18,00", "2,45")
ROTULO_DO_UNITARIO = "6,00"
ROTULOS_DAS_QUANTIDADES = ("10", "48", "5")

# O limiar de COLISAO que o `calibration.json` carrega. NAO e piso de leitura, e
# este arquivo existe em boa parte para provar isso.
LIMIAR_DE_COLISAO = 0.8554906845092773

# O par (piso, margem) MEDIDO sobre estas tres fixtures, com os moldes
# recortados delas:
#
#     pior score   0,5948  o `1` de `10` na coluna Quantity, contra o molde de
#                          `1` tirado de `100,00` - bandas de fundo opostas
#     pior margem  0,0449  o `0` de `10`, contra o `8`
#
# O par abaixo fica logo abaixo dos dois, com a folga declarada. Ele NAO e o
# numero de producao - quem produz aquele e a varredura sobre as 8 gravacoes, e
# ele mora no `calibration.json`.
PISO_DA_FIXTURA = 0.55
MARGEM_DA_FIXTURA = 0.04


def _ler(caminho: Path) -> np.ndarray:
    pixels = cv2.imread(str(caminho))
    assert pixels is not None, f"fixture ausente: {caminho}"
    return pixels


def _bandas(nome: str, quantas: int) -> list[np.ndarray]:
    imagem = _ler(FIXTURES / nome)
    return [
        imagem[i * ALTURA_DA_LINHA : (i + 1) * ALTURA_DA_LINHA]
        for i in range(quantas)
    ]


def _glifos_da_banda(banda: np.ndarray) -> list[np.ndarray]:
    faixa, runs = segmentar_glifos(banda)
    if faixa is None:
        return []
    topo, base = faixa
    mascara = (mascara_de_texto(banda) * 255).astype(np.uint8)
    return [mascara[topo:base, a:b].copy() for a, b in runs]


@pytest.fixture(scope="module")
def moldes() -> dict:
    """Os 11 glifos de um caractere, recortados das proprias fixtures."""
    conjunto: dict = {}
    for banda, rotulo in zip(
        _bandas("glifos_precos_f010.png", 6), ROTULOS_DOS_PRECOS
    ):
        for indice, glifo in enumerate(_glifos_da_banda(banda)):
            conjunto.setdefault(rotulo[indice], glifo)
    unitario = _ler(FIXTURES / "glifos_unitario_f010.png")
    for indice, glifo in enumerate(_glifos_da_banda(unitario)):
        conjunto.setdefault(ROTULO_DO_UNITARIO[indice], glifo)
    return conjunto


class TestALeituraDosSeisPrecos:
    """Digito a digito, sobre pixels reais do jogo."""

    def test_os_onze_glifos_foram_recortados(self, moldes) -> None:
        assert sorted(moldes) == sorted("0123456789,")

    def test_le_os_seis_precos(self, moldes) -> None:
        lidos = [
            classificar_celula(
                banda,
                moldes,
                PISO_DA_FIXTURA,
                MARGEM_DA_FIXTURA,
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=None,
            )
            for banda in _bandas("glifos_precos_f010.png", 6)
        ]
        assert lidos == list(ROTULOS_DOS_PRECOS)

    def test_le_as_tres_quantidades(self, moldes) -> None:
        lidos = [
            classificar_celula(
                banda,
                moldes,
                PISO_DA_FIXTURA,
                MARGEM_DA_FIXTURA,
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=None,
            )
            for banda in _bandas("glifos_quantidade_f012.png", 3)
        ]
        assert lidos == list(ROTULOS_DAS_QUANTIDADES)


class TestOLimiarDeCOLISAONaoServeDePiso:
    """O 0,8555 certifica o CONJUNTO de moldes, nao a leitura de tela."""

    def test_o_piso_de_colisao_PERDE_linha_que_o_piso_medido_mantem(
        self, moldes
    ) -> None:
        bandas = _bandas("glifos_precos_f010.png", 6)
        com_piso_medido = [
            classificar_celula(
                b,
                moldes,
                PISO_DA_FIXTURA,
                MARGEM_DA_FIXTURA,
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=None,
            )
            for b in bandas
        ]
        com_piso_de_colisao = [
            classificar_celula(
                b,
                moldes,
                LIMIAR_DE_COLISAO,
                MARGEM_DA_FIXTURA,
                valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=None,
            )
            for b in bandas
        ]

        assert None not in com_piso_medido
        perdidas = [
            rotulo
            for rotulo, lido in zip(ROTULOS_DOS_PRECOS, com_piso_de_colisao)
            if lido is None
        ]
        assert perdidas, "o piso de colisao tinha de perder alguma linha"
        assert any("8" in rotulo for rotulo in perdidas), (
            "as linhas perdidas tinham de ser as que contem `8` - "
            f"perdidas: {perdidas}"
        )


class TestTudoOuNada:
    """Uma celula com um run reprovado devolve None, nunca um numero truncado."""

    def test_piso_impossivel_devolve_None_inteiro(self, moldes) -> None:
        banda = _bandas("glifos_precos_f010.png", 6)[0]
        assert (
            classificar_celula(
                banda, moldes, 1.01, 0.0, valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=None,
            )
            is None
        )

    def test_margem_impossivel_devolve_None_inteiro(self, moldes) -> None:
        banda = _bandas("glifos_precos_f010.png", 6)[0]
        assert (
            classificar_celula(
                banda, moldes, 0.0, 1.01, valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=None,
            )
            is None
        )

    def test_celula_sem_texto_devolve_None(self, moldes) -> None:
        vazia = np.zeros((45, 60, 3), dtype=np.uint8)
        assert (
            classificar_celula(
                vazia, moldes, 0.0, 0.0, valor_minimo=VALOR_MINIMO_DO_TEXTO,
                folga_de_cola=None,
            )
            is None
        )


class TestAGramaticaDoNumero:
    """Moeda e quantidade nao sao a mesma coisa, e a virgula prova."""

    @pytest.mark.parametrize(
        "texto,esperado",
        [
            ("100,00", 10000),
            ("3,00", 300),
            ("18,90", 1890),
            ("2,45", 245),
            ("0,83", 83),
            ("40,00", 4000),
        ],
    )
    def test_moeda_em_centesimos(self, texto: str, esperado: int) -> None:
        assert centesimos_de_moeda(texto) == esperado

    @pytest.mark.parametrize("texto", ["1,0", "1,000", ",00", "12", "1,00,00"])
    def test_moeda_fora_da_gramatica_e_None(self, texto: str) -> None:
        assert centesimos_de_moeda(texto) is None

    @pytest.mark.parametrize(
        "texto,esperado", [("10", 10), ("48", 48), ("5", 5), ("5,000,000", 5000000)]
    )
    def test_quantidade_inteira(self, texto: str, esperado: int) -> None:
        assert inteiro_de_quantidade(texto) == esperado

    @pytest.mark.parametrize("texto", ["5,00", "1,0000", ",5", ""])
    def test_quantidade_fora_da_gramatica_e_None(self, texto: str) -> None:
        assert inteiro_de_quantidade(texto) is None


class TestOLimiteDerivadoDoCruzamento:
    """O unitario e `Total / Quantity` TRUNCADO a duas casas.

    Entao o residuo `|total - unitario x quantidade|` e limitado por UM
    centesimo POR UNIDADE, e o limite E a propria quantidade.

    OS NUMEROS DESTA CLASSE DOBRARAM EM 2026-09-02, e a razao e medicao e nao
    gosto: a prova limpa daquele dia declarou as dez linhas da tela por escrito
    ANTES de o scanner rodar, o leitor acertou 10 de 10, e as QUATRO linhas que
    discriminam truncamento de arredondamento truncaram as quatro (299,75 ->
    `299`, 366,67 -> `366`, 387,5 -> `387`, 388,89 -> `388`). Sob a regua antiga
    tres das dez linhas CERTAS eram reprovadas; sob esta, nenhuma.
    """

    def test_o_caso_conhecido_do_spike(self) -> None:
        # scroll-transicao/frame_000012: 40,00 XM Coin por 48 unidades, com o
        # jogo exibindo 0,83 no unitario (0,8333... truncado - esta linha nao
        # discrimina truncamento de arredondamento, os dois dariam 0,83).
        # O residuo continua 16; o LIMITE passou de 24 para 48.
        residuo = residuo_do_cruzamento(total=4000, unitario=83, quantidade=48)
        assert residuo == 16
        assert limite_derivado_do_cruzamento(48) == 48
        assert residuo <= limite_derivado_do_cruzamento(48)

    def test_as_divisoes_exatas_fecham_com_residuo_zero(self) -> None:
        # pagina-cheia/frame_000010: 18,90 / 2 = 9,45 e 18,00 / 3 = 6,00
        assert residuo_do_cruzamento(total=1890, unitario=945, quantidade=2) == 0
        assert residuo_do_cruzamento(total=1800, unitario=600, quantidade=3) == 0

    def test_o_limite_cresce_com_a_quantidade(self) -> None:
        # Um centesimo por unidade: o limite E a quantidade, e nao a metade.
        assert limite_derivado_do_cruzamento(10) == 10
        assert limite_derivado_do_cruzamento(1) == 1.0


class TestOVereditoDaGuarda:
    """DECIDIVEL, e os dois criterios sao obrigatorios."""

    def test_aprova_quando_os_dois_criterios_fecham(self) -> None:
        linhas = [
            LinhaMedida("t", "f", 0, 4000, 48, 83),
            LinhaMedida("t", "f", 1, 1890, 2, 945),
            LinhaMedida("t", "f", 2, 1800, 3, 600),
            LinhaMedida("t", "f", 3, 2490, 10, 249),
            LinhaMedida("t", "f", 4, 1700, 5, 340),
        ]
        veredito = veredito_da_guarda(linhas)
        assert veredito["aprovada"] is True
        assert veredito["fechamento"] >= FECHAMENTO_MINIMO
        assert veredito["deteccao"] >= DETECCAO_MINIMA
        assert veredito["tolerancia"] is not None
        assert veredito["linha_do_veredito"].startswith("GUARDA APROVADA")

    def test_reprova_e_grava_None_quando_a_DETECCAO_cai(self) -> None:
        """Quantidade enorme contra total pequeno absorve a troca `0`<->`8`.

        E o modo de falha que a guarda existe para pegar, e aqui ela nao pega:
        trocar um `0` por um `8` em `10,00` muda o total em 800 centesimos, e
        com 2.000 unidades a tolerancia sozinha ja vale 1.000 centesimos.
        """
        linhas = [
            LinhaMedida("t", "f", i, 1000, 2000, 1) for i in range(20)
        ]
        veredito = veredito_da_guarda(linhas)
        assert veredito["aprovada"] is False
        assert veredito["tolerancia_gravada"] is None
        assert veredito["criterio_que_caiu"] == "deteccao"
        assert veredito["linha_do_veredito"].startswith("GUARDA REPROVADA por deteccao")
        assert f"{veredito['deteccao']:.4f}" in veredito["linha_do_veredito"]

    def test_reprova_quando_a_TOLERANCIA_estoura_o_limite_derivado(self) -> None:
        """Residuo grande demais: a relacao nao e o arredondamento simples.

        `100,00` por 10 unidades daria `10,00` de unitario; aqui o unitario
        exibido e `5,00`, entao o residuo e 5.000 centesimos contra um limite
        derivado de 10 (era 5 ate 2026-09-02, quando a derivacao passou do
        arredondamento para o TRUNCAMENTO). Nenhuma tolerancia dentro do teto
        de 1,0 centesimo por unidade fecha isso - e o teto e o mesmo dos dois
        lados da mudanca, porque o fator caiu de 2,0 para 1,0 no mesmo commit.
        """
        linhas = [LinhaMedida("t", "f", i, 10000, 10, 500) for i in range(20)]
        veredito = veredito_da_guarda(linhas)
        assert veredito["aprovada"] is False
        assert veredito["tolerancia_gravada"] is None
        assert veredito["criterio_que_caiu"] == "tolerancia"
        assert veredito["linha_do_veredito"].startswith(
            "GUARDA REPROVADA por tolerancia"
        )

    def test_sem_linha_nenhuma_a_guarda_fica_DESLIGADA(self) -> None:
        veredito = veredito_da_guarda([])
        assert veredito["aprovada"] is False
        assert veredito["tolerancia_gravada"] is None
        assert veredito["linha_do_veredito"].startswith("GUARDA REPROVADA")


CALIBRACAO_DE_FIXTURE = FIXTURES / "calibracao_de_fixture.json"
GRAVACAO_SINTETICA = "20260828-000000-sintetica"

# As DUAS fixturas reais que a varredura vai ver, e o veredito que o portao de
# PRODUCAO tem de dar em cada uma. Elas nao sao arrays de brinquedo: sao as
# mesmas janelas que `tests/test_mercado_adena.py` e `tests/test_mercado_pagina.py`
# usam, com cabecalho de verdade na banda que `_casamento_do_layout` olha.
FRAMES_DA_GRAVACAO_SINTETICA = (
    ("frame_000001.png", "janela_negociacao_f005.png", "negociacao"),
    ("frame_000002.png", "janela_adena_f014.png", "adena"),
)


def montar_a_gravacao_sintetica(tmp_path: Path) -> Path:
    """Uma gravacao de duas fixturas REAIS, dentro de `tmp_path` e so ali.

    `recordings/` e material de campo insubstituivel e SOMENTE LEITURA - a
    pasta `pre-voo` sozinha tem 1.502 PNGs. Estes testes nunca a tocam: eles
    copiam duas fixturas versionadas para um diretorio temporario e apontam
    `GRAVACOES_DO_CENSO` para la.
    """
    pasta = tmp_path / GRAVACAO_SINTETICA
    pasta.mkdir(parents=True)
    for destino, origem, _veredito in FRAMES_DA_GRAVACAO_SINTETICA:
        shutil.copyfile(FIXTURES / origem, pasta / destino)
    return tmp_path


class TestOPortaoDeLayoutDaPRODUCAO_E_CHAMADO:
    """Provado por CONTAGEM DE CHAMADAS, e nunca por "o simbolo existe".

    A PROPRIEDADE QUE ESTA CLASSE MEDE nao e que a ferramenta saiba distinguir
    negociacao de adena - e que ela use O PORTAO DE PRODUCAO para isso. As duas
    coisas parecem iguais no resultado e sao opostas na manutencao: uma copia do
    casamento de cabecalho dentro da ferramenta continuaria devolvendo
    `negociacao`/`adena` no dia em que `LeitorDePagina` mudasse de limiar, de
    regra de empate ou de conjunto de candidatos - e o veredito da guarda sairia
    com o nome certo e o significado errado.

    E O DEFEITO JA ACONTECEU NESTE PROJETO: o DEBT-07 fechou exatamente a
    variante em que um teste media a propria copia em vez do original. Por isso o
    contador embrulha `LeitorDePagina._casamento_do_layout` na CLASSE DE
    PRODUCAO, delegando ao metodo original - se a ferramenta parar de chamar o
    portao, o contador vai a zero e estes testes caem.

    O CONTROLE NEGATIVO SEPARA DUAS AFIRMACOES DIFERENTES. "O portao foi
    chamado" e "a resposta do portao decide alguma coisa" nao sao a mesma coisa:
    a ferramenta poderia chama-lo e jogar a resposta fora. Com o portao forcado a
    responder `adena` para TODO frame, a populacao do CRUZAMENTO vai a ZERO
    enquanto `resultado.amostras` (a populacao de GLIFO) fica intacta - o que
    prova de uma vez que a resposta e consumida E que as duas populacoes sao
    filtradas de proposito por criterios diferentes.
    """

    def _varrer_contando(self, tmp_path, monkeypatch, portao_falso=None):
        """Varre a gravacao sintetica contando as chamadas ao portao REAL."""
        gravacoes = montar_a_gravacao_sintetica(tmp_path)
        monkeypatch.setattr(
            ferramenta, "GRAVACOES_DO_CENSO", [GRAVACAO_SINTETICA]
        )
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)

        original = LeitorDePagina._casamento_do_layout
        respostas: list = []

        def contando(leitor, janela, origem):
            resposta = (
                portao_falso
                if portao_falso is not None
                else original(leitor, janela, origem)
            )
            respostas.append(resposta)
            return resposta

        monkeypatch.setattr(
            LeitorDePagina, "_casamento_do_layout", contando, raising=True
        )
        resultado = ferramenta.varrer(gravacoes, cal)
        return resultado, respostas

    def test_as_duas_fixturas_ABREM_o_painel(self, tmp_path, monkeypatch) -> None:
        """A guarda contra medir vacuo, e ela vem ANTES de tudo.

        Um teste que medisse ZERO frames abertos passaria por acidente em todas
        as afirmacoes de contagem abaixo (0 == 0). Se esta afirmacao cair, o
        numero medido tem de ser RELATADO e a causa investigada - jamais o teste
        afrouxado para caber no que saiu.
        """
        resultado, _ = self._varrer_contando(tmp_path, monkeypatch)
        abertos = resultado.abertos_por_gravacao[GRAVACAO_SINTETICA]
        assert abertos == len(FRAMES_DA_GRAVACAO_SINTETICA), (
            "as duas fixturas tem de abrir o painel sob este rastreio; "
            f"abriram {abertos}"
        )

    def test_o_portao_e_chamado_UMA_VEZ_POR_FRAME_ABERTO(
        self, tmp_path, monkeypatch
    ) -> None:
        """A afirmacao central da tarefa, e ela e sobre CHAMADA e nao existencia."""
        resultado, respostas = self._varrer_contando(tmp_path, monkeypatch)
        abertos = resultado.abertos_por_gravacao[GRAVACAO_SINTETICA]
        assert abertos > 0
        assert len(respostas) == abertos

    def test_os_vereditos_sao_negociacao_e_adena_nas_duas_fixturas(
        self, tmp_path, monkeypatch
    ) -> None:
        """O portao de producao responde certo sobre pixel de verdade."""
        resultado, _ = self._varrer_contando(tmp_path, monkeypatch)
        for arquivo, _origem, esperado in FRAMES_DA_GRAVACAO_SINTETICA:
            assert (
                resultado.layout_por_frame[(GRAVACAO_SINTETICA, arquivo)]
                == esperado
            ), arquivo
        assert resultado.abertos_por_layout == {"negociacao": 1, "adena": 1}

    def test_com_o_portao_REAL_sobra_populacao_de_cruzamento(
        self, tmp_path, monkeypatch
    ) -> None:
        """E preciso sobrar linha, senao o controle negativo mede 0 contra 0."""
        resultado, _ = self._varrer_contando(tmp_path, monkeypatch)
        linhas = ferramenta.linhas_do_cruzamento(resultado)
        completas = [linha for linha in linhas if linha.completa]
        assert len(completas) > 0
        assert {linha.arquivo for linha in linhas} == {"frame_000001.png"}
        assert len(resultado.amostras) > 0

    def test_CONTROLE_NEGATIVO_o_portao_forcado_a_adena_ZERA_o_cruzamento(
        self, tmp_path, monkeypatch
    ) -> None:
        """A resposta do portao e CONSUMIDA, e as duas populacoes sao distintas.

        Com o portao respondendo `adena` para todo frame, a populacao do
        CRUZAMENTO vai a zero. A de GLIFO (`resultado.amostras`) NAO muda - ela e
        identica a do caso real, porque a producao le as duas colunas de moeda da
        aba Adena com os MESMOS retangulos de negociacao (medido no 05-01).
        """
        real, _ = self._varrer_contando(tmp_path / "real", monkeypatch)
        falso, respostas = self._varrer_contando(
            tmp_path / "falso", monkeypatch, portao_falso="adena"
        )

        assert set(respostas) == {"adena"}
        assert ferramenta.linhas_do_cruzamento(falso) == []
        assert ferramenta.quebra_do_cruzamento_por_layout(falso) == {
            "adena": ferramenta.quebra_do_cruzamento_por_layout(real)[
                "negociacao"
            ]
        }

        assert len(falso.amostras) == len(real.amostras)
        assert len(falso.amostras) > 0

    def test_o_fonte_CHAMA_o_portao_e_nao_reimplementa_o_casamento(self) -> None:
        """DEBT-07, por inspecao: a ferramenta nao pode ter a propria copia.

        `casamento_do_cabecalho` e `_banda_do_cabecalho` sao as duas pecas que
        uma reimplementacao precisaria. Se uma delas aparecer aqui, alguem
        copiou o portao - e a copia mede outra coisa que a producao decide.
        """
        fonte = (RAIZ / "tools" / "medir_leitura_de_glifo.py").read_text(
            encoding="utf-8"
        )
        assert "from l2scanner.mercado_pagina import LeitorDePagina" in fonte
        assert "_casamento_do_layout(" in fonte
        assert "casamento_do_cabecalho" not in fonte
        assert "def _banda_do_cabecalho" not in fonte


class TestOTetoAbsolutoDaTolerancia:
    """O teto e o PRODUTO dos dois fatores, e e ele que nao pode se mover.

    `LIMITE_POR_UNIDADE x FATOR_MAXIMO_SOBRE_O_LIMITE_DERIVADO` e o maximo em
    centesimos por unidade que a ferramenta aceita como tolerancia proposta. Em
    2026-09-02 os DOIS fatores mudaram no mesmo commit, em sentidos opostos:

        antes   0,5 x 2,0 = 1,0
        depois  1,0 x 1,0 = 1,0

    O 2x existia para deixar espaco para a hipotese do TRUNCAMENTO. Com o
    truncamento virando a propria derivacao, manter o 2x empilharia a mesma folga
    duas vezes e levaria o teto a 2,0 - um afrouxamento nascido de um commit cujo
    assunto era corrigir uma derivacao, que e o modo de falha que este projeto
    existe para evitar.

    ESTE TESTE AFIRMA O PRODUTO E NAO OS FATORES, DE PROPOSITO. Um teste que
    afirmasse `FATOR == 1.0` ficaria verde no dia em que alguem dobrasse
    `LIMITE_POR_UNIDADE` de novo, e o teto subiria em silencio. O produto e a
    grandeza que decide, entao e ele que tem de estar preso.
    """

    TETO = 1.0

    def test_o_produto_dos_dois_fatores_vale_um_centesimo_por_unidade(self) -> None:
        produto = (
            ferramenta.LIMITE_POR_UNIDADE
            * ferramenta.FATOR_MAXIMO_SOBRE_O_LIMITE_DERIVADO
        )
        assert produto == self.TETO

    def test_o_veredito_publica_o_MESMO_teto_que_o_produto(self) -> None:
        """O numero do relatorio nao pode divergir do numero que julga.

        Sem isto, a linha de formato fixo que o 02-06 le poderia anunciar um teto
        e a comparacao usar outro - e a reprovacao do 02-02 esta transcrita no
        fonte de producao com o `maximo 1.0` dessa linha.
        """
        veredito = veredito_da_guarda([LinhaMedida("t", "f", 0, 1890, 2, 945)])
        assert veredito["limite_aceitavel_por_unidade"] == self.TETO

    def test_a_reprovacao_do_02_02_cai_contra_o_MESMO_teto_de_antes(self) -> None:
        """1273 continua estourando 1,0, e por isso o registro nao mudou.

        Se o teto tivesse subido para 2,0 como efeito colateral, a frase
        `(maximo 1.0)` transcrita em `mercado_leitura.py` teria virado ficcao.
        """
        linhas = [LinhaMedida("t", "f", i, 10000, 10, 500) for i in range(20)]
        veredito = veredito_da_guarda(linhas)
        assert veredito["criterio_que_caiu"] == "tolerancia"
        assert f"(maximo {self.TETO})" in veredito["linha_do_veredito"]


class TestAsFerramentasNAO_ESCREVEM_EM_RECORDINGS:
    """T-02-08, afirmado por inspecao de fonte nas DUAS ferramentas."""

    @pytest.mark.parametrize(
        "nome", ["medir_oclusao", "medir_leitura_de_glifo"]
    )
    def test_nenhuma_escrita_sob_recordings(self, nome: str) -> None:
        fonte = (RAIZ / "tools" / (nome + ".py")).read_text(encoding="utf-8")
        assert "imwrite" not in fonte, "ferramenta de medicao nao grava imagem"
        for suspeito in ("shutil.rmtree", "os.remove(", "unlink(", "rmdir("):
            assert suspeito not in fonte, f"{nome} apaga arquivo: {suspeito}"
        # `recordings/` so aparece em `cv2.imread`, em `glob` e em prosa. A
        # UNICA escrita e o load-mutate-save do `calibration.json`, e ela nao
        # passa por `Path.write_*` nem por `open` sobre caminho de gravacao:
        # e um `NamedTemporaryFile` seguido de `os.replace`.
        for suspeito in ("write_text(", "write_bytes(", "savez", "np.save"):
            assert suspeito not in fonte, f"{nome} escreve: {suspeito}"
        assert "NamedTemporaryFile" in fonte
        assert "os.replace" in fonte
        for linha in fonte.splitlines():
            if "recordings" not in linha:
                continue
            assert (
                "imread" in linha
                or "glob" in linha
                or linha.lstrip().startswith("#")
                or "gravacoes" in linha
                or '"' not in linha
            ), f"{nome}: linha suspeita sobre recordings -> {linha}"
