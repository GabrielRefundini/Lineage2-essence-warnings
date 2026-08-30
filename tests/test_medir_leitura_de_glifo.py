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
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.mercado_leitura import segmentar_glifos
from l2scanner.identidade import mascara_de_texto

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
            classificar_celula(banda, moldes, PISO_DA_FIXTURA, MARGEM_DA_FIXTURA)
            for banda in _bandas("glifos_precos_f010.png", 6)
        ]
        assert lidos == list(ROTULOS_DOS_PRECOS)

    def test_le_as_tres_quantidades(self, moldes) -> None:
        lidos = [
            classificar_celula(banda, moldes, PISO_DA_FIXTURA, MARGEM_DA_FIXTURA)
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
            classificar_celula(b, moldes, PISO_DA_FIXTURA, MARGEM_DA_FIXTURA)
            for b in bandas
        ]
        com_piso_de_colisao = [
            classificar_celula(b, moldes, LIMIAR_DE_COLISAO, MARGEM_DA_FIXTURA)
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
        assert classificar_celula(banda, moldes, 1.01, 0.0) is None

    def test_margem_impossivel_devolve_None_inteiro(self, moldes) -> None:
        banda = _bandas("glifos_precos_f010.png", 6)[0]
        assert classificar_celula(banda, moldes, 0.0, 1.01) is None

    def test_celula_sem_texto_devolve_None(self, moldes) -> None:
        vazia = np.zeros((45, 60, 3), dtype=np.uint8)
        assert classificar_celula(vazia, moldes, 0.0, 0.0) is None


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
    """O unitario e `Total / Quantity` arredondado a duas casas.

    Entao o residuo `|total - unitario x quantidade|` e limitado por meio
    centesimo POR UNIDADE. O caso conhecido do spike e o que prende isso.
    """

    def test_o_caso_conhecido_do_spike(self) -> None:
        # scroll-transicao/frame_000012: 40,00 XM Coin por 48 unidades, com o
        # jogo exibindo 0,83 no unitario (0,8333... arredondado).
        residuo = residuo_do_cruzamento(total=4000, unitario=83, quantidade=48)
        assert residuo == 16
        assert limite_derivado_do_cruzamento(48) == 24
        assert residuo <= limite_derivado_do_cruzamento(48)

    def test_as_divisoes_exatas_fecham_com_residuo_zero(self) -> None:
        # pagina-cheia/frame_000010: 18,90 / 2 = 9,45 e 18,00 / 3 = 6,00
        assert residuo_do_cruzamento(total=1890, unitario=945, quantidade=2) == 0
        assert residuo_do_cruzamento(total=1800, unitario=600, quantidade=3) == 0

    def test_o_limite_cresce_com_a_quantidade(self) -> None:
        assert limite_derivado_do_cruzamento(10) == 5
        assert limite_derivado_do_cruzamento(1) == 0.5


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
        derivado de 5. Nenhuma tolerancia dentro de 2x o limite fecha isso.
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
