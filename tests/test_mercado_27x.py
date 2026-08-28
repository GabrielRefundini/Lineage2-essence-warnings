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


# ---------------------------------------------------------------------------
# METADE 3 — o sinal chega ao caminho da party, e chega COMO INFORMACAO
# ---------------------------------------------------------------------------


class SilencioFalso:
    """O minimo que o `Sessao.tick` pede do silencio. Sem relogio."""

    janela = None

    def ativo(self) -> bool:
        return False

    def atualizar(self, agora):
        return None


def nova_sessao(calibracao, tmp_path, mercado=None):
    from l2scanner.agenda import RegistroEmDisco
    from l2scanner.sessao import Sessao

    return Sessao(
        cal=calibracao,
        rastreador=Rastreador(
            nomes=list(calibracao.nomes),
            nome_proprio=calibracao.nome_proprio,
            ajustes=Ajustes(),
        ),
        eventos_agendados=[],
        registro=RegistroEmDisco(tmp_path),
        silencio=SilencioFalso(),
        mercado=mercado,
    )


def frame_do_27x(barra: np.ndarray, janela: np.ndarray | None = None) -> Frame:
    """Party window real + barra propria + (opcional) a janela do mercado.

    O extra do mercado e a JANELA INTEIRA, e nao um retangulo fixo: o painel
    ANDA (181 px entre `f000` e `f005` do proprio incidente), entao um recorte
    fixo mediria grama na maior parte dos frames.
    """
    pixels = cv2.imread(str(PARTY / "limpo.png"))
    assert pixels is not None
    extras: dict[str, np.ndarray] = {"hp_proprio": barra}
    if janela is not None:
        extras["mercado_janela"] = janela
    return Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK, extras=extras)


def barra_viva() -> np.ndarray:
    px = cv2.imread(str(PARTY / "limpo__hp_proprio.png"))
    assert px is not None
    return px


class TestMetade3_OCampoEExibicional:
    """O sinal entra na `Observacao` e NAO sai de la como decisao."""

    def test_o_sinal_chega_a_observacao_e_ZERO_eventos_saem_dele(
        self, calibracao, tmp_path
    ):
        """As duas afirmacoes no mesmo teste, de proposito.

        Um teste que so afirmasse `is True` deixaria passar a promocao do campo
        a consumidor de decisao — que e o defeito inteiro que o bloco
        `<detc01_reconciliation>` do 01-04-PLAN.md existe para impedir.
        """
        from l2scanner.mercado_visao import RastreioDoPainel

        sessao = nova_sessao(
            calibracao, tmp_path, mercado=RastreioDoPainel(ancoras())
        )
        janela = janela_do_27x("aberto_27x_f000", (912, 350))

        resultado = sessao.tick(frame_do_27x(barra_viva(), janela), momento=0.0)

        assert resultado.observacao is not None
        assert resultado.observacao.mercado_aberto_aparente is True
        assert resultado.eventos == [], (
            "o mercado aberto produziu evento — o campo virou decisao"
        )

    def test_o_painel_FECHADO_da_False_e_nao_None(self, calibracao, tmp_path):
        """`False` e "olhei e nao esta"; `None` e "ninguem olhou". Nao e o mesmo.

        Achatar os dois num `None` faria o console calar exatamente quando ele
        tem resposta — e faria a Fase 4 nao conseguir distinguir "mercado
        fechado" de "mercado nao calibrado".
        """
        from l2scanner.mercado_visao import RastreioDoPainel

        sessao = nova_sessao(
            calibracao, tmp_path, mercado=RastreioDoPainel(ancoras())
        )
        janela = janela_do_27x("fechado_27x_f020", (912, 350))

        resultado = sessao.tick(frame_do_27x(barra_viva(), janela), momento=0.0)
        assert resultado.observacao.mercado_aberto_aparente is False

    def test_a_sequencia_do_27x_COM_o_mercado_ligado_segue_em_ZERO_eventos(
        self, calibracao, tmp_path
    ):
        """O criterio 4 do ROADMAP com as duas metades no MESMO laco.

        As metades 1 e 2 acima medem os dois lados separados. Este mede o que o
        usuario roda: o mesmo tick vendo o painel E as barras cobertas. Se
        alguem ligar o sinal ao rastreador, e aqui que aparece.
        """
        from l2scanner.mercado_visao import RastreioDoPainel

        sessao = nova_sessao(
            calibracao, tmp_path, mercado=RastreioDoPainel(ancoras())
        )
        janela = janela_do_27x("aberto_27x_f000", (912, 350))
        viva = barra_viva()

        for i in range(20):
            sessao.tick(frame_do_27x(viva, janela), momento=float(i))

        eventos = []
        vistas = []
        for i, rotulo in enumerate(COBERTAS * 10):
            r = sessao.tick(
                frame_do_27x(recorte_da_barra(rotulo), janela),
                momento=100.0 + i,
            )
            eventos.extend(r.eventos)
            vistas.append(r.observacao.mercado_aberto_aparente)

        assert all(v is True for v in vistas), (
            "o painel deixou de ser reconhecido no meio da sequencia"
        )
        assert eventos == [], (
            f"40 ticks com o painel aberto por cima da barra emitiram "
            f"{[e.tipo.name for e in eventos]} — o incidente 27x voltou"
        )


class TestODegenerado_SemCalibracaoDeMercadoNadaMuda:
    def test_sem_vigia_o_campo_fica_None(self, calibracao, tmp_path):
        """Instalacao que nunca calibrou o mercado: o campo nao existe de fato.

        `None` e "ninguem perguntou" — o mesmo contrato de `estado_do_cliente`.
        Nunca vira evento e nunca vira linha no console.
        """
        sessao = nova_sessao(calibracao, tmp_path, mercado=None)
        resultado = sessao.tick(frame_do_27x(barra_viva()), momento=0.0)
        assert resultado.observacao.mercado_aberto_aparente is None

    def test_com_vigia_mas_SEM_o_extra_o_campo_fica_None(
        self, calibracao, tmp_path
    ):
        """O extra some quando a regiao cai fora da janela (falha fechada).

        `captura_janela._extra_para_janela` devolve `None` nesse caso. Inventar
        `False` ali faria o console afirmar "mercado fechado" sobre pixels que
        ninguem capturou.
        """
        from l2scanner.mercado_visao import RastreioDoPainel

        sessao = nova_sessao(
            calibracao, tmp_path, mercado=RastreioDoPainel(ancoras())
        )
        resultado = sessao.tick(frame_do_27x(barra_viva()), momento=0.0)
        assert resultado.observacao.mercado_aberto_aparente is None

    def test_um_vigia_que_EXPLODE_nao_derruba_a_leitura_da_party(
        self, calibracao, tmp_path
    ):
        """Um campo de mostrar nao pode custar a deteccao de morte.

        Se a leitura do mercado levantar, o tick tem de seguir com a party lida
        e o campo em `None`. O contrario — `falhou_ao_analisar` — trocaria um
        enfeite de console pela funcionalidade inteira do scanner.
        """

        class VigiaQueExplode:
            def observar(self, janela):
                raise RuntimeError("molde corrompido")

        sessao = nova_sessao(calibracao, tmp_path, mercado=VigiaQueExplode())
        janela = janela_do_27x("aberto_27x_f000", (912, 350))

        resultado = sessao.tick(frame_do_27x(barra_viva(), janela), momento=0.0)

        assert not resultado.falhou_ao_analisar
        assert resultado.observacao is not None
        assert resultado.observacao.ui_visivel
        assert resultado.observacao.mercado_aberto_aparente is None


# ---------------------------------------------------------------------------
# A SUPERFICIE: o que o usuario ve, e o que a instalacao sem mercado NAO paga
# ---------------------------------------------------------------------------


class TestAMontagemDoVigiaNoArranque:
    """`montar_vigia_do_mercado` — o mesmo contrato do vigia de manutencao."""

    def test_sem_ancoras_calibradas_nao_ha_vigia(self, calibracao):
        from l2scanner.__main__ import montar_vigia_do_mercado

        assert calibracao.mercado_ancoras in (None, [])
        assert montar_vigia_do_mercado(calibracao, na_janela=True) is None

    def test_sem_janela_nao_ha_vigia_mesmo_com_ancoras(self, calibracao):
        """No caminho `mss` cada extra custa uma captura PROPRIA por tick.

        Capturar 1720x1392 a cada segundo para escrever uma linha de console
        seria caro pelo motivo errado — e a varredura da janela inteira nem faz
        sentido sem a janela inteira.
        """
        from dataclasses import replace as _replace

        from l2scanner.__main__ import montar_vigia_do_mercado
        from l2scanner.mercado_visao import ancoras_para_calibracao

        com_ancoras = _replace(
            calibracao, mercado_ancoras=ancoras_para_calibracao(ancoras())
        )
        assert montar_vigia_do_mercado(com_ancoras, na_janela=False) is None

    def test_ancoras_corrompidas_desligam_o_recurso_sem_derrubar_o_scanner(
        self, calibracao
    ):
        """O `calibration.json` e entrada NAO confiavel — e o scanner nao e opcional.

        `ancoras_de_calibracao` recusa alto e com o nome do campo, que e certo
        para uma ferramenta de calibracao. No arranque do scanner essa mesma
        recusa nao pode virar excecao: ela apagaria a deteccao de morte inteira
        por causa de um campo de mostrar.
        """
        from dataclasses import replace as _replace

        from l2scanner.__main__ import montar_vigia_do_mercado

        podre = _replace(calibracao, mercado_ancoras=[{"nome": "titulo"}])
        assert montar_vigia_do_mercado(podre, na_janela=True) is None

    def test_com_ancoras_e_janela_o_vigia_sobe_com_o_limiar_da_calibracao(
        self, calibracao
    ):
        """A calibracao do usuario e a autoridade sobre a tela dele."""
        from dataclasses import replace as _replace

        from l2scanner.__main__ import montar_vigia_do_mercado
        from l2scanner.mercado_visao import ancoras_para_calibracao

        pronta = _replace(
            calibracao,
            mercado_ancoras=ancoras_para_calibracao(ancoras()),
            mercado_limiar_da_ancora=0.81,
        )
        vigia = montar_vigia_do_mercado(pronta, na_janela=True)
        assert vigia is not None
        assert vigia._limiar == 0.81


class TestASuperficieNoConsole:
    """O sinal vira TEXTO, com marca — e some quando nao ha o que dizer."""

    def _status(self, calibracao, valor):
        from l2scanner.__main__ import desenhar_status

        rastreador = Rastreador(
            nomes=list(calibracao.nomes), nome_proprio=calibracao.nome_proprio
        )
        observacao = extrair(
            frame_de_party(cv2.imread(str(PARTY / "limpo__hp_proprio.png"))),
            calibracao,
        )
        rastreador.observar(observacao, 0.0)
        from dataclasses import replace as _replace

        return desenhar_status(
            rastreador,
            calibracao,
            _replace(observacao, mercado_aberto_aparente=valor),
        )

    def test_aberto_aparece_MARCADO_como_aparente(self, calibracao):
        """Sem a marca, o numero no `scanner.log` vira evidencia falsa depois."""
        status = self._status(calibracao, True)
        assert "WORLD EXCHANGE ABERTO" in status
        assert "(aparente)" in status

    @pytest.mark.parametrize("valor", [False, None])
    def test_fechado_e_nao_perguntado_NAO_ocupam_linha(self, calibracao, valor):
        """`False` e o estado normal do farm inteiro.

        Uma linha permanente dizendo "mercado fechado" empurraria para fora da
        tela justamente as linhas de HP que o usuario abre o console para ver.
        """
        assert "WORLD EXCHANGE" not in self._status(calibracao, valor)
