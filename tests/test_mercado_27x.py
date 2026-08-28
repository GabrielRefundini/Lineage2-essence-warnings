"""Criterio 4 do ROADMAP: o painel e reconhecido E zero alertas de morte.

AS DUAS METADES NO MESMO ARQUIVO, DE PROPOSITO. A metade "zero mortes" ja passa
hoje — o portao de moldura da quick `260826-dxm` a conquistou. Um teste que so
afirmasse isso nao prenderia nada do DETC-01, e um teste que so afirmasse a
deteccao do painel nao prenderia a licao que este projeto pagou 27 alertas
falsos para aprender. Juntas, elas nao podem ser desfeitas uma sem a outra.

O QUE FOI O INCIDENTE 27x: com o inventario aberto por cima da barra de vida do
proprio personagem, o scanner lia 0% e anunciava "YAZALAQUE MORREU". O
`scanner.log` real tem 27 mortes e 27 ressurreicoes desse unico defeito.

O PARENTESCO COM O MERCADO, e a razao de este arquivo existir agora: o painel do
World Exchange e outra janela do jogo desenhada por cima da tela. A tentacao
obvia — "detectar o mercado pelo jeito estranho que a barra fica" — e literal e
exatamente o caminho que produziu as 27 mortes falsas. Por isso a ancora do
mercado e um sinal POSITIVO e PROPRIO (`mercado_visao`), medido contra a arte do
painel, e o rastreador NAO a le. Ha um tripwire de arquitetura abaixo para isso.

SOBRE O MATERIAL: `recordings/inv3/` (o incidente) e gitignored e nao existe num
clone limpo. As duas metades sao afirmadas sobre fixtures VERSIONADAS resgatadas
de la — os recortes das ancoras nos frames de janela `f000`/`f005`/`f020`, e as
barras `coberta_*` que o incidente produziu.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.rastreador
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.mercado_visao import (
    CASAMENTO_MINIMO_DA_ANCORA,
    AncoraDoPainel,
    RastreioDoPainel,
)
from l2scanner.rastreador import Ajustes, Rastreador
from l2scanner.visao import extrair

MERCADO = Path(__file__).parent / "fixtures" / "mercado"
BARRAS = Path(__file__).parent / "fixtures" / "barra_propria"
PARTY = Path(__file__).parent / "fixtures" / "party_estavel_com_vazamento"
CALIBRACAO = PARTY / "calibracao.json"
RECORDINGS = Path(__file__).resolve().parents[1] / "recordings"

DESLOCAMENTOS = {"titulo": (0, 0), "botao_fechar": (494, -10), "canto_inf_dir": (494, 665)}

# As barras que o inventario cobriu no incidente. `coberta_0` le 0.87 porque o
# painel cobre so parte da barra; as outras tres liam 0.0 — foram elas que
# viraram morte.
COBERTAS = ("coberta_0", "coberta_1", "coberta_2", "coberta_3")


def cinza(caminho: Path) -> np.ndarray:
    px = cv2.imread(str(caminho))
    assert px is not None, f"fixture ausente: {caminho}"
    return cv2.cvtColor(px, cv2.COLOR_BGR2GRAY)


def ancoras() -> list[AncoraDoPainel]:
    return [
        AncoraDoPainel(
            nome=nome,
            dx=dx,
            dy=dy,
            molde=cinza(
                MERCADO
                / ("molde_da_ancora.png" if nome == "titulo" else f"molde_{nome}.png")
            ),
        )
        for nome, (dx, dy) in DESLOCAMENTOS.items()
    ]


def janela_do_27x(rotulo: str, origem: tuple[int, int]) -> np.ndarray:
    """Remonta a janela do jogo com os PIXELS REAIS daquele frame do incidente.

    Os recortes versionados sao as tres ancoras daquele frame, na origem em que
    o painel estava. Recolando-os numa janela de 1720x1392 sobre ruido, o
    caminho de producao inteiro — varredura, seguimento, votacao — roda contra
    material real sem que o repositorio carregue um frame de 3,5 MB.

    O fundo e RUIDO, e nao preto: um fundo chapado tem desvio zero e a busca
    devolveria 0.0 em qualquer lugar, o que faria o teste passar por construcao.
    """
    janela = np.random.default_rng(42).integers(
        0, 255, size=(1392, 1720), dtype=np.uint8
    )
    ox, oy = origem
    for nome, (dx, dy) in DESLOCAMENTOS.items():
        recorte = cinza(MERCADO / f"{rotulo}__{nome}.png")
        h, w = recorte.shape
        x, y = ox + dx, oy + dy
        if x < 0 or y < 0 or y + h > janela.shape[0] or x + w > janela.shape[1]:
            continue
        janela[y : y + h, x : x + w] = recorte
    return janela


# ---------------------------------------------------------------------------
# METADE 1 — o que o DETC-01 ACRESCENTA
# ---------------------------------------------------------------------------


class TestMetade1_OPainelEReconhecidoNoReplayDo27x:
    @pytest.mark.parametrize(
        ("rotulo", "origem"),
        [("aberto_27x_f000", (912, 350)), ("aberto_27x_f005", (731, 493))],
    )
    def test_o_painel_e_encontrado_em_CADA_posicao(self, rotulo, origem):
        """O painel ANDA: 181 px a esquerda e 143 px abaixo entre f000 e f005."""
        rastreio = RastreioDoPainel(ancoras())
        voto = rastreio.observar(janela_do_27x(rotulo, origem))
        assert voto.aberto, f"{rotulo}: {voto.por_ancora}"
        assert voto.origem == origem
        assert voto.melhor >= CASAMENTO_MINIMO_DA_ANCORA

    def test_o_frame_de_INVENTARIO_do_27x_nao_vira_mercado(self):
        """`f020` tem uma janela do jogo aberta — e ela nao e o mercado.

        Este e o negativo que mais importa do incidente inteiro: o defeito
        original foi confundir "tem uma janela por cima" com um veredito. Os
        recortes aqui sao ADVERSARIAIS — cada ancora na sua melhor posicao
        naquele frame, o ponto mais parecido com ela em toda a tela.
        """
        rastreio = RastreioDoPainel(ancoras())
        voto = rastreio.observar(janela_do_27x("fechado_27x_f020", (912, 350)))
        assert not voto.aberto, f"o inventario virou mercado: {voto.por_ancora}"

    def test_a_sequencia_INTEIRA_do_27x_classifica_certo(self):
        """Aberto, ARRASTADO, fechado — com o rastreio de verdade, na ordem.

        Os frames de janela do 27x estao amostrados de 5 em 5, entao entre um e
        o seguinte o painel "teleporta". E o pior caso possivel para um rastreio
        que segue posicao, e o criterio 4 do ROADMAP exige que ele acerte assim
        mesmo: **todo frame com o painel aberto e reconhecido, sem excecao e sem
        latencia.**

        Foi este teste que cobrou a cadencia errada da primeira versao — ela
        dava `f005` como fechado, e um "quase todos" nao satisfaz o criterio.
        """
        rastreio = RastreioDoPainel(ancoras())
        assert rastreio.observar(janela_do_27x("aberto_27x_f000", (912, 350))).aberto

        arrastado = rastreio.observar(janela_do_27x("aberto_27x_f005", (731, 493)))
        assert arrastado.aberto, (
            "o painel aberto em posicao NOVA foi dado como fechado — e o "
            "criterio 4 do ROADMAP nao admite um frame perdido"
        )
        assert arrastado.origem == (731, 493)

        fechado = janela_do_27x("fechado_27x_f020", (912, 350))
        assert not rastreio.observar(fechado).aberto
        assert rastreio.origem is None


# ---------------------------------------------------------------------------
# METADE 2 — o que NAO pode regredir
# ---------------------------------------------------------------------------


@pytest.fixture
def calibracao() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO)


def recorte_da_barra(rotulo: str) -> np.ndarray:
    px = cv2.imread(str(BARRAS / f"{rotulo}.png"), cv2.IMREAD_COLOR)
    assert px is not None, f"fixture ausente: {rotulo}"
    return px


def frame_de_party(barra: np.ndarray) -> Frame:
    """Party window REAL mais a barra propria escolhida.

    O aquecimento vem de pixels de verdade, e nao de campos privados fixados a
    mao — o padrao de `test_inventario_por_cima_da_barra_propria.frame_de_party`.
    Um aquecimento fabricado provaria menos.
    """
    pixels = cv2.imread(str(PARTY / "limpo.png"))
    assert pixels is not None
    return Frame(
        pixels=pixels, indice=0, saude=SaudeDoFrame.OK, extras={"hp_proprio": barra}
    )


class TestMetade2_ZeroAlertasDeMorteNaSequenciaDo27x:
    def test_a_sequencia_inteira_emite_ZERO_eventos(self, calibracao: Calibracao):
        """Nao "menos eventos": ZERO, e de tipo NENHUM.

        Filtrar por MORREU nao prova ausencia dos outros: a quick `260826-dxm`
        pagou 27 mortes E 27 ressurreicoes, e a ressurreicao falsa e a metade
        mais cara — ela manda a party parar de socorrer quem continua morto.
        """
        rastreador = Rastreador(
            nomes=list(calibracao.nomes),
            nome_proprio=calibracao.nome_proprio,
            ajustes=Ajustes(),
        )

        viva = extrair(
            frame_de_party(
                cv2.imread(str(PARTY / "limpo__hp_proprio.png"))
            ),
            calibracao,
        )
        assert viva.ui_visivel and viva.hp_proprio == 1.0, (
            "o aquecimento parou de mostrar party window com barra propria "
            "cheia — o rastreador nao fica QUENTE e o teste passa a medir o "
            "comeco frio, que protege por acidente"
        )
        for i in range(20):
            rastreador.observar(viva, float(i))

        eventos = []
        for i, rotulo in enumerate(COBERTAS * 10):
            coberta = extrair(frame_de_party(recorte_da_barra(rotulo)), calibracao)
            assert coberta.hp_proprio is None, (
                f"{rotulo} voltou a produzir leitura de verdade: o portao de "
                f"moldura caiu e o defeito do 27x esta de volta"
            )
            eventos.extend(rastreador.observar(coberta, 100.0 + i))

        assert eventos == [], (
            f"40 ticks com o inventario por cima da barra emitiram "
            f"{[e.tipo.name for e in eventos]} — o incidente 27x voltou"
        )


# ---------------------------------------------------------------------------
# O TRIPWIRE DE ARQUITETURA
# ---------------------------------------------------------------------------


class TestORastreadorNaoLeOMercado:
    """A seguranca nao vem de guardas: vem de a leitura NAO EXISTIR para ele.

    A mesma protecao que `hp_proprio_aparente` ja tem. Promover o sinal do
    mercado a um segundo consumidor de DECISAO dentro do detector de morte e
    exatamente a manobra que causou o incidente 27x — e ligar a oclusao ao
    rastreador na mesma fase em que a ancora nasce significaria confiar num
    limiar recem-medido para SUPRIMIR alertas de morte.

    O consumidor de oclusao chega na Fase 4, por desenho, junto do DETC-02. Ver
    o bloco `<detc01_reconciliation>` do 01-04-PLAN.md.
    """

    def test_o_fonte_do_rastreador_nao_cita_mercado(self):
        fonte = inspect.getsource(l2scanner.rastreador)
        assert "mercado" not in fonte.lower(), (
            "rastreador.py passou a citar o mercado. Se isso e deliberado, e "
            "uma decisao de arquitetura da Fase 4 e precisa da medicao de campo "
            "da ancora antes — nao de apagar este teste"
        )

    def test_o_rastreador_nao_importa_o_modulo_de_visao_do_mercado(self):
        fonte = inspect.getsource(l2scanner.rastreador)
        assert "mercado_visao" not in fonte


class TestOReplayCOMPLETO:
    """Os 45 recortes e os 10 frames de janela — so onde `recordings/` existe."""

    def test_o_replay_completo_nao_e_afirmavel_num_clone_limpo(self):
        if not (RECORDINGS / "inv3").is_dir():
            pytest.skip(
                "recordings/inv3/ e gitignored e nao se materializa num "
                "worktree nem num clone limpo. As duas metades acima rodam "
                "sobre as fixtures VERSIONADAS resgatadas de la."
            )
        janelas = sorted((RECORDINGS / "inv3").glob("f*_JANELA.png"))
        assert len(janelas) >= 9, "o material do 27x mudou de forma"
