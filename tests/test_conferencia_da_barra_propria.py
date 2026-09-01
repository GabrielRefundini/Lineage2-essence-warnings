"""A regiao gravada da SUA barra de HP e conferida contra a tela, no arranque.

O INCIDENTE, medido em campo em 2026-08-31. O `calibration.json` tinha
`hp_proprio = 191x24 em (298,701)`. A barra vermelha de verdade estava em
`topo=711`. Dez pixels acima, a regiao caia sobre a barra de CP (amarela) e so
encostava numa lasca vermelha do topo da HP.

O console mostrava `Yazalaque (voce) ok HP 8%` com a barra CHEIA na tela
(5418/5418).

POR QUE ISSO ERA PERIGOSO E NAO SO FEIO: 8% e MAIOR QUE ZERO, entao
`Rastreador._avaliar_so_o_proprio` marcou `_ja_viu_a_propria_barra_viva` como
True. Aquela guarda so protege quem NUNCA foi visto vivo; com ela satisfeita,
qualquer oscilacao da lasca vermelha ate zero teria disparado MORTE do usuario
com ele intacto, que e o pior modo de falha deste produto. Ele estava a um
pixel de distancia.

A CAUSA CONTINUA DESCONHECIDA e nao e o assunto deste arquivo. O erro medido e
(+9,-10), com sinais opostos nos dois eixos, e nenhum valor de origem produz
isso. O que estes testes prendem nao e a causa, e o DESFECHO: o usuario tem que
saber, no arranque, que a regiao gravada nao bate com a tela.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import l2scanner.conferencia_do_proprio as conferencia
from l2scanner.calibracao import Calibracao
from l2scanner.conferencia_do_proprio import (
    TOLERANCIA_DE_POSICAO,
    avisar_no_arranque,
    conferir_a_barra_do_proprio,
)
from l2scanner.frames import Regiao

FIXTURES = Path(__file__).parent / "fixtures" / "party_estavel_com_vazamento"

# Os numeros do incidente de 31/08, sem arredondar.
GRAVADA = Regiao(esquerda=298, topo=701, largura=191, altura=24)
ACHADA = Regiao(esquerda=289, topo=711, largura=191, altura=24)


@pytest.fixture
def cal() -> Calibracao:
    """A calibracao REAL do usuario, com a `hp_proprio` do incidente.

    Vem da fixture e nao de um objeto sintetico porque a conferencia le uma
    `Calibracao` inteira e nao pode depender de nenhum campo estar vazio.
    """
    return replace(Calibracao.carregar(FIXTURES / "calibracao.json"), hp_proprio=GRAVADA)


def janela_com_a_barra_em(x: int, y: int, largura_da_barra: int = 191) -> np.ndarray:
    """Uma janela de jogo com terreno e UMA barra vermelha na posicao.

    Mesmo molde de `tests/test_visao.py::TestBuscaDaBarraPropriaNaJanelaInteira`:
    quem acha a barra aqui e o MESMO `achar_barra_do_proprio` de producao, entao
    os pixels tem que ser os que ele reconhece.
    """
    gerador = np.random.default_rng(3)
    altura, largura = 1080, 1920
    px = np.zeros((altura, largura, 3), np.uint8)
    px[:, :, 1] = gerador.integers(40, 120, (altura, largura))
    px[:, :, 0] = gerador.integers(20, 70, (altura, largura))
    px[y : y + 24, x : x + largura_da_barra] = (30, 30, 200)
    return px


def detector_que_devolve(regiao):
    """Um `achar_barra_do_proprio` falso, para montar o caso sem pixels."""

    def detector(pixels, origem=(0, 0)):
        detector.chamadas.append((pixels, origem))
        return regiao

    detector.chamadas = []
    return detector


class TestODesvioDoIncidente:
    """Dez pixels no topo TEM que virar aviso. E o caso que motivou tudo."""

    def test_o_desvio_real_de_31_08_dispara(self, cal):
        aviso = conferir_a_barra_do_proprio(
            cal, janela_com_a_barra_em(0, 0), detector=detector_que_devolve(ACHADA)
        )
        assert aviso is not None
        assert "701" in aviso, "o aviso nao diz o que esta GRAVADO"
        assert "711" in aviso, "o aviso nao diz o que foi ACHADO na tela"

    def test_o_desvio_real_dispara_com_o_detector_DE_VERDADE(self, cal):
        """Sem detector falso: pixels reais, `achar_barra_do_proprio` de producao.

        E o unico caso que prova que a conferencia funciona com a funcao que ela
        vai chamar em campo. Os demais montam a situacao com um detector falso.
        """
        aviso = conferir_a_barra_do_proprio(cal, janela_com_a_barra_em(289, 711))
        assert aviso is not None
        assert "(289,711)" in aviso

    def test_a_barra_no_lugar_gravado_nao_dispara(self, cal):
        assert conferir_a_barra_do_proprio(cal, janela_com_a_barra_em(298, 701)) is None


class TestATolerancia:
    """So o CANTO e comparado, e ele tolera alguns pixels.

    A largura NAO entra: `achar_barra_do_proprio` acha o componente conexo
    PREENCHIDO, entao com HP parcial a barra medida e mais estreita que a
    gravada. Comparar largura acusaria divergencia toda vez que o usuario
    tomasse dano, que e a forma mais rapida de um aviso deixar de ser lido.
    """

    @pytest.mark.parametrize("dx,dy", [(0, 0), (0, 4), (4, 0), (-4, 4), (3, -3)])
    def test_dentro_da_tolerancia_cala(self, cal, dx, dy):
        detector = detector_que_devolve(
            replace(GRAVADA, esquerda=GRAVADA.esquerda + dx, topo=GRAVADA.topo + dy)
        )
        assert conferir_a_barra_do_proprio(cal, janela_com_a_barra_em(0, 0), detector) is None

    @pytest.mark.parametrize("dx,dy", [(0, 5), (5, 0), (0, -5), (-9, 10)])
    def test_alem_da_tolerancia_avisa(self, cal, dx, dy):
        detector = detector_que_devolve(
            replace(GRAVADA, esquerda=GRAVADA.esquerda + dx, topo=GRAVADA.topo + dy)
        )
        assert conferir_a_barra_do_proprio(cal, janela_com_a_barra_em(0, 0), detector)

    def test_a_tolerancia_e_menor_que_metade_do_desvio_do_incidente(self):
        """O caso real que precisa disparar e 10 px no topo, 9 na esquerda.

        A tolerancia existe para o tremor de bordas do componente conexo (a
        moldura da barra e o texto "HP 5418/5418" desenhado por cima mordem a
        primeira linha), nao para absorver um desvio de campo.
        """
        assert TOLERANCIA_DE_POSICAO < 9 / 2

    def test_barra_muito_mais_estreita_no_mesmo_canto_cala(self, cal):
        """HP parcial estreita a barra medida. Isso NAO e divergencia."""
        detector = detector_que_devolve(replace(GRAVADA, largura=40))
        assert conferir_a_barra_do_proprio(cal, janela_com_a_barra_em(0, 0), detector) is None

    def test_altura_diferente_no_mesmo_canto_cala(self, cal):
        detector = detector_que_devolve(replace(GRAVADA, altura=18))
        assert conferir_a_barra_do_proprio(cal, janela_com_a_barra_em(0, 0), detector) is None


class TestOSilencioQueEHonesto:
    """Ausencia de evidencia NAO e evidencia de divergencia.

    UI escondida com Alt+Z, personagem morto na tela de arranque, jogo em
    loading: nenhum desses tem barra vermelha na tela, e nenhum diz nada sobre a
    regiao gravada estar certa ou errada. Avisar neles seria transformar o
    arranque normal de quem esconde a UI num alarme, e um alarme que toca sem
    motivo e um alarme que ninguem le no dia em que ele estiver certo.
    """

    def test_detector_que_nao_acha_barra_nenhuma_cala(self, cal):
        detector = detector_que_devolve(None)
        assert conferir_a_barra_do_proprio(cal, janela_com_a_barra_em(0, 0), detector) is None
        assert detector.chamadas, "nem chamou o detector"

    def test_janela_sem_barra_nenhuma_cala_com_o_detector_de_verdade(self, cal):
        gerador = np.random.default_rng(1)
        so_terreno = np.zeros((600, 800, 3), np.uint8)
        so_terreno[:, :, 1] = gerador.integers(40, 120, (600, 800))
        assert conferir_a_barra_do_proprio(cal, so_terreno) is None

    def test_sem_frame_cala(self, cal):
        detector = detector_que_devolve(ACHADA)
        assert conferir_a_barra_do_proprio(cal, None, detector) is None
        assert detector.chamadas == [], "chamou o detector sem frame"

    def test_frame_vazio_cala(self, cal):
        detector = detector_que_devolve(ACHADA)
        vazio = np.zeros((0, 0, 3), dtype=np.uint8)
        assert conferir_a_barra_do_proprio(cal, vazio, detector) is None
        assert detector.chamadas == []

    def test_sem_hp_proprio_calibrado_cala(self, cal):
        """Quem nao calibrou a propria barra nao tem o que conferir."""
        detector = detector_que_devolve(ACHADA)
        sem = replace(cal, hp_proprio=None)
        assert conferir_a_barra_do_proprio(sem, janela_com_a_barra_em(0, 0), detector) is None
        assert detector.chamadas == []

    def test_um_detector_que_explode_nao_derruba_o_arranque(self, cal, caplog):
        """A conferencia e um extra. Ela nunca pode impedir o scanner de subir."""

        def detector_quebrado(pixels, origem=(0, 0)):
            raise RuntimeError("cv2 explodiu")

        with caplog.at_level("DEBUG", logger="l2scanner"):
            assert (
                conferir_a_barra_do_proprio(
                    cal, janela_com_a_barra_em(0, 0), detector_quebrado
                )
                is None
            )


class TestOTextoDoAviso:
    """O aviso diz o que achou, o que esta gravado, e o que fazer."""

    @pytest.fixture
    def aviso(self, cal) -> str:
        texto = conferir_a_barra_do_proprio(
            cal, janela_com_a_barra_em(0, 0), detector_que_devolve(ACHADA)
        )
        assert texto is not None
        return texto

    def test_nomeia_o_retangulo_gravado(self, aviso):
        assert "191x24 em (298,701)" in aviso

    def test_nomeia_o_canto_achado(self, aviso):
        assert "(289,711)" in aviso

    def test_diz_o_desvio_com_sinal(self, aviso):
        assert "(-9,+10)" in aviso

    def test_manda_rodar_o_calibrar(self, aviso):
        assert "calibrar.bat" in aviso

    def test_diz_que_nao_vai_corrigir_sozinho(self, aviso):
        assert "NAO vou" in aviso

    def test_sem_travessao(self, aviso):
        """O console do Windows e cp1252. Um travessao vira lixo ou excecao."""
        assert "—" not in aviso and "–" not in aviso

    def test_sem_acento(self, aviso):
        assert aviso.isascii(), "acento no texto de usuario"

    def test_o_avisar_no_arranque_registra_como_WARNING(self, cal, caplog):
        class FonteFalsa:
            def capturar_completo(self):
                return janela_com_a_barra_em(0, 0)

        with caplog.at_level("INFO", logger="l2scanner"):
            texto = avisar_no_arranque(
                cal, FonteFalsa(), detector=detector_que_devolve(ACHADA)
            )

        assert texto is not None
        assert any(r.levelname == "WARNING" for r in caplog.records)
        assert "711" in caplog.text

    def test_o_avisar_no_arranque_cala_quando_bate(self, cal, caplog):
        class FonteFalsa:
            def capturar_completo(self):
                return janela_com_a_barra_em(298, 701)

        with caplog.at_level("INFO", logger="l2scanner"):
            assert avisar_no_arranque(cal, FonteFalsa()) is None
        assert caplog.records == []

    def test_o_avisar_no_arranque_aguenta_uma_fonte_sem_frame(self, cal):
        class FonteFalsa:
            def capturar_completo(self):
                return None

        assert avisar_no_arranque(cal, FonteFalsa()) is None


class TestAvisarNuncaCorrigir:
    """A conferencia AVISA. Ela nao troca a regiao, nem em disco nem na memoria.

    Trocar a regiao de HP proprio por conta propria e da MESMA familia de risco
    que este aviso existe para cobrir: um detector que erra passaria a mandar no
    que o rastreador le sobre a vida do usuario. O reancoramento da party window
    (`l2scanner/reancoragem.py`) pode adotar geometria porque tem oito
    conferencias de plausibilidade antes; aqui nao ha nenhuma.
    """

    def test_a_calibracao_nao_e_tocada(self, cal):
        antes = cal.hp_proprio
        conferir_a_barra_do_proprio(
            cal, janela_com_a_barra_em(0, 0), detector_que_devolve(ACHADA)
        )
        assert cal.hp_proprio is antes
        assert (cal.hp_proprio.esquerda, cal.hp_proprio.topo) == (298, 701)

    def test_o_modulo_nao_escreve_calibracao_nenhuma(self):
        """Chamadas, nao prosa: o texto do aviso PODE falar em regravar."""
        fonte = inspect.getsource(conferencia)
        for proibido in (".salvar(", "json.dump", "imwrite", "open(", ".write("):
            assert proibido not in fonte, f"a conferencia escreve ({proibido})"

    def test_o_modulo_nao_atribui_hp_proprio(self):
        """`cal.hp_proprio = ...` seria a correcao silenciosa em memoria."""
        arvore = ast.parse(inspect.getsource(conferencia))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Attribute) and isinstance(no.ctx, ast.Store):
                assert no.attr != "hp_proprio"

    def test_o_modulo_nao_reaponta_a_fonte(self):
        """`apontar_para` e do reancoramento. Aqui seria correcao silenciosa."""
        assert "apontar_para" not in inspect.getsource(conferencia)


class TestOImportTardioDeCalibrar:
    """`calibrar.py` roda `tornar_consciente_de_dpi()` NO IMPORT.

    E arrasta junto o `cv2` das ferramentas interativas. Importa-lo no topo
    deste modulo faria todo arranque pagar por ele e poria um efeito colateral
    de DPI numa ordem que ninguem controla. Mesmo molde documentado em
    `l2scanner/reancoragem.py::Reancorador`.
    """

    def test_nenhum_import_de_calibrar_no_topo(self):
        arvore = ast.parse(inspect.getsource(conferencia))
        for no in arvore.body:
            if isinstance(no, ast.ImportFrom):
                assert "calibrar" not in (no.module or "")
            if isinstance(no, ast.Import):
                for alias in no.names:
                    assert "calibrar" not in alias.name

    def test_o_detector_padrao_e_o_achar_barra_do_proprio_de_producao(self, cal):
        """Um SEGUNDO detector discordaria no dia em que a resposta importa."""
        import l2scanner.calibrar

        chamadas = []
        real = l2scanner.calibrar.achar_barra_do_proprio

        def espiao(pixels, origem=(0, 0)):
            chamadas.append(origem)
            return real(pixels, origem)

        anterior = l2scanner.calibrar.achar_barra_do_proprio
        l2scanner.calibrar.achar_barra_do_proprio = espiao
        try:
            conferir_a_barra_do_proprio(cal, janela_com_a_barra_em(289, 711))
        finally:
            l2scanner.calibrar.achar_barra_do_proprio = anterior

        assert chamadas, "a conferencia usa um detector proprio"


class TestAFiacaoNoArranque:
    """So no caminho `--janela`, e so uma vez.

    No caminho `mss` a barra propria nem e capturavel: `__main__.py` ja avisa
    que "a barra do seu personagem so e lida com --janela". Conferir ali seria
    prometer cobertura que nao existe.
    """

    def _laco_principal(self) -> ast.FunctionDef:
        import l2scanner.__main__ as principal

        arvore = ast.parse(inspect.getsource(principal))
        for no in ast.walk(arvore):
            if isinstance(no, ast.FunctionDef) and no.name == "laco_principal":
                return no
        pytest.fail("laco_principal sumiu de l2scanner/__main__.py")

    def test_o_laco_principal_chama_a_conferencia(self):
        chamadas = [
            no
            for no in ast.walk(self._laco_principal())
            if isinstance(no, ast.Call)
            and getattr(no.func, "id", None) == "avisar_no_arranque"
        ]
        assert len(chamadas) == 1, "o arranque nao confere a barra propria"

    def test_a_conferencia_esta_dentro_de_um_if(self):
        """Nunca solta no corpo do laco: no caminho `mss` nao ha o que conferir."""
        dentro = [
            no
            for no in ast.walk(self._laco_principal())
            if isinstance(no, ast.If)
            for filho in ast.walk(no)
            if isinstance(filho, ast.Call)
            and getattr(filho.func, "id", None) == "avisar_no_arranque"
        ]
        assert dentro, "a conferencia roda fora de qualquer guarda"
