"""A ancora do painel XM Market, MEDIDA contra a gravacao do incidente 27x.

De onde vem o material: `recordings/inv3/` guarda 9 frames de janela completa
(1720x1392) do dia das 27 mortes falsas. A pesquisa da fase supunha que os 9
tinham o painel do mercado aberto. A medicao desmentiu, e a correcao vale mais
que a suposicao:

    f000   1.0000 @ (912, 350)    painel ABERTO
    f005   0.9996 @ (731, 493)    painel ABERTO, em OUTRA POSICAO
    f010..f040  0.32..0.41        painel FECHADO (f020 mostra o INVENTARIO)

Duas consequencias:

1. **O painel ANDA.** O f005 esta 181 px a esquerda e 143 px abaixo do f000 e
   ainda assim casa 0.9996. Um retangulo fixo calibrado NAO acha o painel numa
   segunda posicao — quem consumir precisa LOCALIZAR antes de comparar. Este
   arquivo mede a comparacao; achar e do consumidor.
2. **Os negativos ficaram melhores do que o plano previa.** Sete dos dez sao
   frames com OUTRO painel aberto (o inventario), que e exatamente o negativo
   que um limiar chutado confundiria. E o mais duro de todos,
   `negativo_escuro` (0.4624), e o banner de sistema "Someone has registered an
   item on XM Market!" — as MESMAS PALAVRAS na tela, sem painel nenhum aberto.
   E o teste de que a ancora casa arte de painel, e nao texto.

Cada negativo foi cortado na posicao de MELHOR casamento do seu frame — o lugar
mais parecido com a faixa de titulo naquele frame inteiro. E o corte
adversarial: e ele que o limiar precisa vencer, nao um pedaco de terreno
qualquer.

As fixtures aqui sao RESGATADAS: `recordings/` e gitignored e um clone limpo
nao a tem. `tests/fixtures/**/*.png` e a excecao versionavel do `.gitignore`, e
por isso estes recortes minimos (100x28, tons de cinza) sao a unica coisa da
gravacao do usuario que pode ser commitada.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.mercado_visao import (
    CASAMENTO_MINIMO_DA_ANCORA,
    casamento_da_ancora,
    mercado_aberto,
    molde_de_hex,
    molde_para_hex,
)

FIXTURES = Path(__file__).parent / "fixtures" / "mercado"
RECORDINGS = Path(__file__).parent.parent / "recordings"

# O retangulo de onde o molde saiu, no f000_JANELA.png (1720x1392).
ANCORA_NO_F000 = {"esquerda": 912, "topo": 350, "largura": 100, "altura": 28}


def recorte(rotulo: str) -> np.ndarray:
    caminho = FIXTURES / f"{rotulo}.png"
    pixels = cv2.imread(str(caminho), cv2.IMREAD_GRAYSCALE)
    assert pixels is not None, f"fixture ilegivel: {caminho}"
    return pixels


@pytest.fixture
def molde() -> np.ndarray:
    return recorte("molde_da_ancora")


class TestOsPositivosCasamAlto:
    """Os dois frames em que o painel do mercado estava mesmo aberto."""

    @pytest.mark.parametrize(
        ("rotulo", "esperado"),
        [
            ("ancora_27x_f000", 1.0000),
            ("ancora_27x_f005", 0.9996),
        ],
    )
    def test_com_o_painel_aberto_o_casamento_passa_do_limiar(
        self, molde, rotulo, esperado
    ):
        valor = casamento_da_ancora(recorte(rotulo), molde)
        assert valor >= CASAMENTO_MINIMO_DA_ANCORA, (
            f"{rotulo}: casamento {valor:.4f} abaixo do limiar — um painel "
            f"REALMENTE aberto deixou de ser reconhecido"
        )
        assert abs(valor - esperado) < 0.001, (
            f"{rotulo}: casamento {valor:.4f} em vez de {esperado} medido"
        )
        assert mercado_aberto(recorte(rotulo), molde, CASAMENTO_MINIMO_DA_ANCORA)

    def test_o_f005_prova_que_o_painel_ANDA(self, molde):
        """A resposta medida da pergunta em aberto A1.

        O f005 casa 0.9996 num ponto 181 px a esquerda e 143 px abaixo do f000.
        Se este numero cair, a afirmacao "o painel se move" mudou e o desenho da
        deteccao (localizar antes de comparar) precisa ser revisitado — nao
        apagado.
        """
        valor = casamento_da_ancora(recorte("ancora_27x_f005"), molde)
        assert valor > 0.99, (
            f"ancora_27x_f005 casa {valor:.4f}: o argumento de que a MESMA arte "
            f"de painel aparece em posicao diferente e o que obriga o consumidor "
            f"a localizar em vez de olhar um retangulo fixo"
        )


class TestOsNegativosFicamBemAbaixo:
    """Sem painel do mercado, no ponto mais parecido de cada frame."""

    @pytest.mark.parametrize(
        ("rotulo", "esperado"),
        [
            ("negativo_f010", 0.4053),
            ("negativo_f015", 0.4051),
            ("negativo_f020", 0.3614),
            ("negativo_f025", 0.4114),
            ("negativo_f030", 0.3903),
            ("negativo_f035", 0.3253),
            ("negativo_f040", 0.4102),
            ("negativo_base", 0.3506),
            ("negativo_agora", 0.4075),
            ("negativo_escuro", 0.4624),
        ],
    )
    def test_sem_o_painel_o_casamento_fica_abaixo_do_limiar(
        self, molde, rotulo, esperado
    ):
        valor = casamento_da_ancora(recorte(rotulo), molde)
        assert valor < CASAMENTO_MINIMO_DA_ANCORA, (
            f"{rotulo}: casamento {valor:.4f} passou do limiar — um frame SEM "
            f"o painel seria anunciado como mercado aberto"
        )
        assert abs(valor - esperado) < 0.001, (
            f"{rotulo}: casamento {valor:.4f} em vez de {esperado} medido"
        )
        assert not mercado_aberto(recorte(rotulo), molde, CASAMENTO_MINIMO_DA_ANCORA)

    def test_o_banner_com_AS_MESMAS_PALAVRAS_nao_engana(self, molde):
        """`negativo_escuro` e o texto "...on XM Market!" no log do jogo.

        E o negativo mais caro da colecao: um detector que procurasse o TEXTO
        "XM Market" dispararia aqui com o painel fechado. A ancora casa arte de
        painel e le 0.4624 — bem longe do limiar.
        """
        valor = casamento_da_ancora(recorte("negativo_escuro"), molde)
        assert valor < CASAMENTO_MINIMO_DA_ANCORA
        assert abs(valor - 0.4624) < 0.001

    def test_a_margem_medida_continua_grande(self, molde):
        """Pior positivo - melhor negativo. Se encolher, o limiar precisa mudar."""
        positivos = [
            casamento_da_ancora(recorte(r), molde)
            for r in ("ancora_27x_f000", "ancora_27x_f005")
        ]
        negativos = [
            casamento_da_ancora(recorte(caminho.stem), molde)
            for caminho in sorted(FIXTURES.glob("negativo_*.png"))
        ]
        margem = min(positivos) - max(negativos)
        assert margem > 0.5, (
            f"margem {margem:.4f} — foi medida em 0.5372 (0.9996 vs 0.4624). "
            f"Uma margem menor significa que a constante precisa ser remedida "
            f"contra as fixtures novas, nao afrouxada."
        )


class TestOsDegeneradosFalhamFECHADO:
    """Entrada degenerada devolve 0.0, e 0.0 nunca e "mercado aberto"."""

    def test_recorte_vazio(self, molde):
        vazio = np.zeros((0, 0), dtype=np.uint8)
        assert casamento_da_ancora(vazio, molde) == 0.0
        assert not mercado_aberto(vazio, molde, CASAMENTO_MINIMO_DA_ANCORA)

    def test_molde_vazio(self):
        vazio = np.zeros((0, 0), dtype=np.uint8)
        assert casamento_da_ancora(recorte("ancora_27x_f000"), vazio) == 0.0

    def test_recorte_uniforme_tem_desvio_zero(self, molde):
        """Captura falhando / janela minimizada dao um retangulo chapado."""
        chapado = np.full(molde.shape, 128, dtype=np.uint8)
        assert casamento_da_ancora(chapado, molde) == 0.0
        assert not mercado_aberto(chapado, molde, CASAMENTO_MINIMO_DA_ANCORA)

    def test_molde_uniforme_tambem(self, molde):
        chapado = np.full(molde.shape, 200, dtype=np.uint8)
        assert casamento_da_ancora(recorte("ancora_27x_f000"), chapado) == 0.0

    def test_molde_maior_que_o_alvo(self, molde):
        """Recorte na borda da janela sai menor que o molde."""
        pequeno = recorte("ancora_27x_f000")[:10, :10]
        assert casamento_da_ancora(pequeno, molde) == 0.0
        assert not mercado_aberto(pequeno, molde, CASAMENTO_MINIMO_DA_ANCORA)

    def test_um_recorte_colorido_e_convertido_e_nao_comparado_por_canal(self, molde):
        """O consumidor da Fase 4 entrega BGR; comparar canal com cinza mentiria."""
        colorido = cv2.cvtColor(recorte("ancora_27x_f000"), cv2.COLOR_GRAY2BGR)
        assert abs(casamento_da_ancora(colorido, molde) - 1.0) < 0.001


class TestOEmpacotamentoDoMolde:
    """Hex cru, padrao `Assinatura.como_dict` adaptado para tons de cinza."""

    def test_round_trip_devolve_array_identico(self, molde):
        devolvido = molde_de_hex(molde_para_hex(molde))
        assert devolvido.shape == molde.shape
        assert devolvido.dtype == molde.dtype
        assert (devolvido == molde).all()

    def test_o_empacotado_e_json_serializavel(self, molde):
        import json

        dados = molde_para_hex(molde)
        assert set(dados) == {"altura", "largura", "bytes"}
        assert json.loads(json.dumps(dados)) == dados

    def test_o_molde_de_volta_casa_1_0_com_o_original(self, molde):
        devolvido = molde_de_hex(molde_para_hex(molde))
        assert abs(casamento_da_ancora(recorte("ancora_27x_f000"), devolvido) - 1.0) < 0.001

    def test_o_tamanho_no_json_e_trivial(self, molde):
        """~1,6 KB de hex: cabe no calibration.json sem incomodar ninguem."""
        assert len(molde_para_hex(molde)["bytes"]) < 8000

    def test_dimensao_declarada_mentindo_e_recusada_ALTO(self, molde):
        """T-02-02: o dict vem do calibration.json, que e entrada nao confiavel."""
        dados = molde_para_hex(molde)
        dados["altura"] = dados["altura"] + 7
        with pytest.raises(ValueError, match="altura|largura|bytes"):
            molde_de_hex(dados)


class TestAsFixturesSaoFIEIS_A_GRAVACAO:
    """Os recortes versionados batem com a gravacao de onde sairam?

    So roda na maquina que tem `recordings/`: a pasta e gitignored e um clone
    limpo nao a tem. Sem este teste, um recorte editado a mao passaria
    despercebido para sempre.
    """

    def test_o_molde_e_o_pedaco_exato_do_f000(self):
        origem = RECORDINGS / "inv3" / "f000_JANELA.png"
        if not origem.is_file():
            pytest.skip(
                "recordings/ e gitignored: a gravacao do incidente 27x nao "
                "existe num clone limpo. As fixtures resgatadas acima cobrem "
                "positivos, negativos e degenerados."
            )
        janela = cv2.imread(str(origem), cv2.IMREAD_GRAYSCALE)
        assert janela.shape == (1392, 1720), (
            f"a geometria da gravacao mudou ({janela.shape}) e todo recorte "
            f"derivado mediria a regiao errada"
        )
        r = ANCORA_NO_F000
        derivado = janela[
            r["topo"] : r["topo"] + r["altura"],
            r["esquerda"] : r["esquerda"] + r["largura"],
        ]
        assert (derivado == recorte("molde_da_ancora")).all(), (
            "molde_da_ancora.png nao e mais o recorte exato de "
            "recordings/inv3/f000_JANELA.png no retangulo registrado"
        )
