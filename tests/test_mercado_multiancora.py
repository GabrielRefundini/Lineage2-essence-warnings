"""O painel do mercado por VOTACAO entre ancoras — e por que uma so nao serve.

O 01-02 mediu a faixa de titulo contra as fixtures do incidente 27x e achou
margem +0.5372, com o limiar 0.73 no meio dela. Aquela medicao continua correta
PARA AQUELE MATERIAL. O campo desmentiu a arquitetura, nao o numero.

O QUE AS 8 GRAVACOES DE CAMPO MOSTRARAM (335 frames, `SPIKE-RESPOSTAS.md` 8):

    pior POSITIVO de campo   0.4110   painel ABERTO, tooltip por cima do titulo
    melhor NEGATIVO de campo 0.4753   painel FECHADO, sessao mercado-fechado
    MARGEM DE CAMPO         -0.0643

As duas classes se SOBREPOEM. Um frame com o painel aberto marca MENOS que um
frame com o painel fechado. Nenhum limiar sobre a faixa de titulo separa as duas
classes neste material — o defeito nao e o valor 0.73, e depender de UM
retangulo. A tooltip caiu exatamente sobre o unico retangulo que a ancora olhava.

O CONSERTO E ESTRUTURAL, e esta afirmado neste arquivo: VARIAS ancoras
independentes, espalhadas pelo painel, decididas por VOTACAO (o MAXIMO). Uma
tooltip e um retangulo LOCAL perto do cursor; ela cobre uma ancora, e cobrir
todas ao mesmo tempo e implausivel.

POR QUE O MAXIMO, e nao a media ou o consenso: o ruido esperado e LOCAL. Media
puniria o frame inteiro por uma ancora coberta; consenso exigiria que a ancora
coberta concordasse. O MAXIMO tem um preco conhecido — cada ancora e uma chance
independente de um alvo errado achar um alinhamento sortudo, a licao medida em
`identidade._correlacionar` — e o preco esta PAGO em medicao: sobre os 335
frames de campo mais os 9 frames de janela do 27x, o melhor negativo das TRES
ancoras juntas e 0.5337.

A NAO-SOLUCAO que foi recusada: o usuario se ofereceu para evitar passar o mouse
no meio da lista, mantendo a tooltip longe. A oferta reduz a frequencia e foi
aceita como isso — reducao de ruido. Ela NAO pode ser o mecanismo de correcao:
este projeto nao troca falha-fechada por disciplina do usuario, porque um dia
ele esquece e o modo de falha volta calado.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.mercado_visao import (
    CASAMENTO_MINIMO_DA_ANCORA,
    TICKS_ENTRE_VARREDURAS_OCIOSAS,
    AncoraDoPainel,
    RastreioDoPainel,
    ancoras_de_calibracao,
    ancoras_para_calibracao,
    buscar_ancora,
    casamento_da_ancora,
    conferir_painel,
    localizar_painel,
)

FIX = Path(__file__).parent / "fixtures" / "mercado"

# Deslocamentos MEDIDOS a partir da origem do painel (o canto da faixa de
# titulo). Painel medido em 1720x1392: canto superior esquerdo em -452,-11 e
# borda inferior em +724 — ver o resgate no 01-04-SUMMARY.
DESLOCAMENTOS = {
    "titulo": (0, 0),
    "botao_fechar": (494, -10),
    "canto_inf_dir": (494, 665),
}


def crop(nome: str) -> np.ndarray:
    caminho = FIX / f"{nome}.png"
    px = cv2.imread(str(caminho))
    assert px is not None, f"fixture ausente: {caminho}"
    return cv2.cvtColor(px, cv2.COLOR_BGR2GRAY)


def molde(nome: str) -> np.ndarray:
    return crop("molde_da_ancora" if nome == "titulo" else f"molde_{nome}")


def ancoras() -> list[AncoraDoPainel]:
    return [
        AncoraDoPainel(nome=n, dx=dx, dy=dy, molde=molde(n))
        for n, (dx, dy) in DESLOCAMENTOS.items()
    ]


# (rotulo, titulo, botao_fechar, canto_inf_dir) — recortados na ORIGEM real do
# painel em cada frame. `None` = a ancora cai fora da janela naquele frame.
POSITIVOS = [
    ("aberto_27x_f000", 1.0000, 0.9768, 0.8547),
    ("aberto_27x_f005", 0.9996, 0.9785, 0.5293),
    ("aberto_tooltip_f084", 0.4110, 0.9056, 0.8824),
    ("aberto_tooltip_f090", 0.0216, 0.9037, 0.8019),
    ("aberto_tooltip_f012", 0.1715, 0.9446, 0.9566),
]

# ADVERSARIAIS: cada ancora recortada na sua MELHOR posicao no frame inteiro —
# o ponto mais parecido com ela naquele frame, que e o numero que a aquisicao
# por varredura precisa vencer.
NEGATIVOS = [
    ("fechado_campo_f012", 0.3726, 0.4739, 0.5337),
    ("fechado_27x_f020", 0.3614, 0.4197, 0.5062),
]

PIOR_POSITIVO = 0.9037  # aberto_tooltip_f090, pelo botao de fechar
MELHOR_NEGATIVO = 0.5337  # fechado_campo_f012, pelo canto inferior direito


def voto_das_fixtures(rotulo: str) -> float:
    return max(
        casamento_da_ancora(crop(f"{rotulo}__{n}"), molde(n)) for n in DESLOCAMENTOS
    )


class TestAFaixaDeTituloSOZINHA_NAO_SEPARA_AS_CLASSES:
    """A prova de que a mudanca de desenho era necessaria, e nao preferencia."""

    @pytest.mark.parametrize(
        ("rotulo", "esperado"),
        [(r, t) for r, t, _, _ in POSITIVOS if r.startswith("aberto_tooltip")],
    )
    def test_com_o_painel_ABERTO_o_titulo_fica_ABAIXO_do_limiar(self, rotulo, esperado):
        valor = casamento_da_ancora(crop(f"{rotulo}__titulo"), molde("titulo"))
        assert abs(valor - esperado) < 0.001, (
            f"{rotulo}: titulo {valor:.4f} em vez de {esperado} medido"
        )
        assert valor < CASAMENTO_MINIMO_DA_ANCORA, (
            f"{rotulo}: o titulo passou do limiar. Se isto caiu, o material "
            f"mudou e a justificativa da votacao precisa ser remedida — nao "
            f"apagada"
        )

    def test_um_positivo_do_campo_marca_MENOS_que_um_negativo(self):
        """A margem NEGATIVA, no mesmo teste, para nao virar prosa esquecivel."""
        pior_aberto = casamento_da_ancora(
            crop("aberto_tooltip_f084__titulo"), molde("titulo")
        )
        melhor_fechado = casamento_da_ancora(
            crop("fechado_campo_f012__canto_inf_dir"), molde("canto_inf_dir")
        )
        assert pior_aberto < melhor_fechado, (
            "as classes deixaram de se sobrepor pelo titulo: reveja o desenho"
        )


class TestAVotacaoENTRE_ANCORAS_SEPARA:
    @pytest.mark.parametrize(("rotulo", "t", "b", "c"), POSITIVOS)
    def test_cada_ancora_le_o_valor_MEDIDO(self, rotulo, t, b, c):
        for nome, esperado in zip(DESLOCAMENTOS, (t, b, c)):
            valor = casamento_da_ancora(crop(f"{rotulo}__{nome}"), molde(nome))
            assert abs(valor - esperado) < 0.001, (
                f"{rotulo}/{nome}: {valor:.4f} em vez de {esperado} medido"
            )

    @pytest.mark.parametrize("rotulo", [r for r, *_ in POSITIVOS])
    def test_o_voto_aprova_todo_frame_com_o_painel_aberto(self, rotulo):
        assert voto_das_fixtures(rotulo) >= CASAMENTO_MINIMO_DA_ANCORA

    @pytest.mark.parametrize(("rotulo", "t", "b", "c"), NEGATIVOS)
    def test_o_voto_reprova_os_adversariais(self, rotulo, t, b, c):
        for nome, esperado in zip(DESLOCAMENTOS, (t, b, c)):
            valor = casamento_da_ancora(crop(f"{rotulo}__{nome}"), molde(nome))
            assert abs(valor - esperado) < 0.001, (
                f"{rotulo}/{nome}: {valor:.4f} em vez de {esperado} medido"
            )
        assert voto_das_fixtures(rotulo) < CASAMENTO_MINIMO_DA_ANCORA

    def test_a_margem_voltou_a_ser_POSITIVA_e_o_limiar_cabe_nela(self):
        pior = min(voto_das_fixtures(r) for r, *_ in POSITIVOS)
        melhor = max(voto_das_fixtures(r) for r, *_ in NEGATIVOS)
        assert abs(pior - PIOR_POSITIVO) < 0.001, f"pior positivo virou {pior:.4f}"
        assert abs(melhor - MELHOR_NEGATIVO) < 0.001, (
            f"melhor negativo virou {melhor:.4f}"
        )
        assert melhor < CASAMENTO_MINIMO_DA_ANCORA < pior, (
            f"o limiar {CASAMENTO_MINIMO_DA_ANCORA} saiu do vao "
            f"[{melhor:.4f}, {pior:.4f}]"
        )


def janela_sintetica(
    origem: tuple[int, int], com_painel: bool = True, semente: int = 7
) -> np.ndarray:
    """Uma janela de teste com as ancoras REAIS coladas na origem dada.

    Fundo de ruido, para que nada case por acidente. As ancoras sao os moldes
    versionados — nada aqui e desenhado a mao.
    """
    rng = np.random.default_rng(semente)
    janela = rng.integers(0, 255, size=(1392, 1720), dtype=np.uint8)
    if com_painel:
        ox, oy = origem
        for anc in ancoras():
            x, y = ox + anc.dx, oy + anc.dy
            h, w = anc.molde.shape
            # Ancora que nao cabe simplesmente nao e colada — e o que permite
            # montar a cena do painel arrastado ate a borda da janela.
            if x < 0 or y < 0 or y + h > janela.shape[0] or x + w > janela.shape[1]:
                continue
            janela[y : y + h, x : x + w] = anc.molde
    return janela


class TestAquisicaoPorVarredura:
    def test_acha_o_painel_e_devolve_a_ORIGEM(self):
        janela = janela_sintetica((912, 350))
        assert localizar_painel(janela, ancoras(), CASAMENTO_MINIMO_DA_ANCORA) == (
            912,
            350,
        )

    def test_acha_o_painel_em_OUTRA_posicao(self):
        """O painel ANDA: 827x831 px de alcance medidos em 34 posicoes."""
        janela = janela_sintetica((412, 79))
        assert localizar_painel(janela, ancoras(), CASAMENTO_MINIMO_DA_ANCORA) == (
            412,
            79,
        )

    def test_sem_painel_devolve_None(self):
        janela = janela_sintetica((0, 0), com_painel=False)
        assert localizar_painel(janela, ancoras(), CASAMENTO_MINIMO_DA_ANCORA) is None

    def test_para_na_PRIMEIRA_ancora_que_passa(self):
        """A varredura custa ~45 ms POR ancora: parar cedo e o que a torna viavel."""
        janela = janela_sintetica((912, 350))
        vistas: list[str] = []
        marcadas = [
            AncoraDoPainel(a.nome, a.dx, a.dy, a.molde) for a in ancoras()
        ]

        def espiao(j, anc):
            vistas.append(anc.nome)
            return buscar_ancora(j, anc)

        localizar_painel(
            janela, marcadas, CASAMENTO_MINIMO_DA_ANCORA, _buscar=espiao
        )
        assert vistas == ["titulo"], (
            f"varreu {vistas}: a aquisicao precisa parar na primeira ancora que "
            f"passa, senao custa 3x"
        )

    def test_com_a_PRIMEIRA_ancora_coberta_a_aquisicao_ainda_acha(self):
        """O caso de campo: a tooltip apaga o titulo e o painel continua la."""
        janela = janela_sintetica((912, 350))
        rng = np.random.default_rng(3)
        janela[350:378, 912:1012] = rng.integers(0, 255, size=(28, 100), dtype=np.uint8)
        assert localizar_painel(janela, ancoras(), CASAMENTO_MINIMO_DA_ANCORA) == (
            912,
            350,
        )


class TestSeguimentoNaPosicaoCONHECIDA:
    def test_confere_barato_e_aprova(self):
        janela = janela_sintetica((912, 350))
        voto = conferir_painel(
            janela, (912, 350), ancoras(), CASAMENTO_MINIMO_DA_ANCORA
        )
        assert voto.aberto
        assert voto.origem == (912, 350)
        assert set(voto.por_ancora) == set(DESLOCAMENTOS)
        assert voto.melhor > 0.99

    def test_na_posicao_ERRADA_reprova(self):
        janela = janela_sintetica((912, 350))
        voto = conferir_painel(
            janela, (400, 400), ancoras(), CASAMENTO_MINIMO_DA_ANCORA
        )
        assert not voto.aberto

    def test_ancora_FORA_da_janela_ABSTEM_em_vez_de_votar_zero(self):
        """Painel arrastado ate a borda: a ancora da direita sai da janela.

        Medido em `mercado-farm-com-party/frame_000021.png`: o painel esta
        aberto em (1239, 578) e o botao de fechar cai FORA. Abster e o que
        permite ao titulo sozinho decidir ali; votar 0.0 seria uma leitura
        inventada sobre pixels que nao existem.
        """
        janela = janela_sintetica((1600, 350))
        voto = conferir_painel(
            janela, (1600, 350), ancoras(), CASAMENTO_MINIMO_DA_ANCORA
        )
        assert "botao_fechar" in voto.abstiveram
        assert "botao_fechar" not in voto.por_ancora
        assert voto.aberto, "o titulo sozinho ainda deveria decidir"

    def test_origem_NEGATIVA_nao_faz_o_numpy_dar_a_volta(self):
        """`janela[-5:, -5:]` recorta o CANTO OPOSTO calado. Isso e um bug."""
        janela = janela_sintetica((912, 350))
        voto = conferir_painel(
            janela, (-500, -500), ancoras(), CASAMENTO_MINIMO_DA_ANCORA
        )
        assert not voto.aberto
        assert set(voto.abstiveram) == set(DESLOCAMENTOS)

    def test_janela_vazia_falha_FECHADO(self):
        voto = conferir_painel(
            np.zeros((0, 0), dtype=np.uint8),
            (0, 0),
            ancoras(),
            CASAMENTO_MINIMO_DA_ANCORA,
        )
        assert not voto.aberto

    def test_janela_CHAPADA_falha_FECHADO(self):
        """Captura falhando devolve retangulo uniforme. Nunca pode virar aberto."""
        voto = conferir_painel(
            np.zeros((1392, 1720), dtype=np.uint8),
            (912, 350),
            ancoras(),
            CASAMENTO_MINIMO_DA_ANCORA,
        )
        assert not voto.aberto
        assert voto.melhor == 0.0


class TestORastreioAdquireDepoisSegue:
    def test_adquire_UMA_vez_e_depois_so_segue(self):
        rastreio = RastreioDoPainel(ancoras())
        janela = janela_sintetica((912, 350))
        for _ in range(5):
            assert rastreio.observar(janela).aberto
        assert rastreio.varreduras == 1, (
            f"{rastreio.varreduras} varreduras em 5 ticks: a posicao e ESTAVEL "
            f"(o painel reabre onde foi fechado) e varrer custa ~45 ms"
        )

    def test_com_a_ancora_da_frente_coberta_o_seguimento_NAO_perde_o_painel(self):
        rastreio = RastreioDoPainel(ancoras())
        limpa = janela_sintetica((912, 350))
        assert rastreio.observar(limpa).aberto

        com_tooltip = limpa.copy()
        rng = np.random.default_rng(11)
        com_tooltip[350:378, 912:1012] = rng.integers(
            0, 255, size=(28, 100), dtype=np.uint8
        )
        for _ in range(4):
            assert rastreio.observar(com_tooltip).aberto
        assert rastreio.varreduras == 1

    def test_depois_de_o_usuario_ARRASTAR_o_painel_o_MESMO_tick_reencontra(self):
        """Perder a posicao e a prova de que o painel se MEXEU. Procurar ja.

        A primeira versao esperava tres ticks tambem aqui, e o replay das
        gravacoes cobrou: 20 de 33 frames abertos na sessao em que o usuario
        arrasta o painel, e o `f005` do incidente 27x dado como fechado.
        """
        rastreio = RastreioDoPainel(ancoras())
        assert rastreio.observar(janela_sintetica((912, 350))).aberto

        voto = rastreio.observar(janela_sintetica((412, 79)))
        assert voto.aberto
        assert voto.origem == (412, 79)
        assert rastreio.varreduras == 2

    def test_com_o_painel_FECHADO_a_varredura_e_RATEADA(self):
        """O caso comum e caro: sem mercado na tela, ~135 ms por volta e demais."""
        rastreio = RastreioDoPainel(ancoras())
        vazia = janela_sintetica((0, 0), com_painel=False)

        for _ in range(TICKS_ENTRE_VARREDURAS_OCIOSAS * 3):
            assert not rastreio.observar(vazia).aberto
        assert rastreio.varreduras == 3, (
            f"{rastreio.varreduras} varreduras em 9 ticks ociosos: a cadencia "
            f"de {TICKS_ENTRE_VARREDURAS_OCIOSAS} ticks nao esta valendo"
        )

    def test_fechar_o_painel_custa_UMA_varredura_e_depois_entra_na_cadencia(self):
        rastreio = RastreioDoPainel(ancoras())
        assert rastreio.observar(janela_sintetica((912, 350))).aberto

        vazia = janela_sintetica((0, 0), com_painel=False)
        assert not rastreio.observar(vazia).aberto
        assert rastreio.varreduras == 2, "a perda precisa varrer na hora"
        assert rastreio.origem is None

        for _ in range(TICKS_ENTRE_VARREDURAS_OCIOSAS - 1):
            assert not rastreio.observar(vazia).aberto
        assert rastreio.varreduras == 2, "a cadencia ociosa nao segurou nada"

    def test_sem_ancora_nenhuma_nunca_abre(self):
        """Instalacao sem calibracao de mercado: a feature fica OFF, nao ON."""
        rastreio = RastreioDoPainel([])
        assert not rastreio.observar(janela_sintetica((912, 350))).aberto


class TestOEmpacotamentoParaACalibracao:
    def test_ida_e_volta_preserva_nome_deslocamento_e_pixels(self):
        originais = ancoras()
        voltaram = ancoras_de_calibracao(ancoras_para_calibracao(originais))
        assert [a.nome for a in voltaram] == [a.nome for a in originais]
        assert [(a.dx, a.dy) for a in voltaram] == [
            (a.dx, a.dy) for a in originais
        ]
        for antes, depois in zip(originais, voltaram):
            assert np.array_equal(antes.molde, depois.molde)

    def test_lista_vazia_ou_None_devolve_lista_vazia(self):
        assert ancoras_de_calibracao(None) == []
        assert ancoras_de_calibracao([]) == []

    def test_molde_com_dimensao_mentida_e_RECUSADO(self):
        dados = ancoras_para_calibracao(ancoras())
        dados[0]["molde"]["altura"] = 29
        with pytest.raises(ValueError, match="corrompido"):
            ancoras_de_calibracao(dados)

    def test_ancora_sem_nome_e_RECUSADA(self):
        dados = ancoras_para_calibracao(ancoras())
        del dados[0]["nome"]
        with pytest.raises(ValueError, match="nome"):
            ancoras_de_calibracao(dados)

    def test_deslocamento_nao_inteiro_e_RECUSADO(self):
        dados = ancoras_para_calibracao(ancoras())
        dados[1]["dx"] = "494"
        with pytest.raises(ValueError, match="dx"):
            ancoras_de_calibracao(dados)

    # ---------------------------------------------------------------
    # WR-01: o guard `forma_esperada` existia e NENHUM chamador de
    # producao o usava -- so os testes. Este e o caminho que o
    # `RastreioDoPainel` percorre de verdade.
    # ---------------------------------------------------------------

    def test_a_forma_do_molde_e_GRAVADA_ao_lado_do_molde(self):
        """`AncoraDoPainel` nao guarda largura/altura separadas.

        Sem estes dois campos nao ha de onde tirar a forma esperada, e a
        conferencia fica impossivel por construcao: uma dimensao que mora so
        DENTRO do proprio molde nao pode conferi-lo -- o dado se declararia
        correto sozinho.
        """
        for bruto, original in zip(ancoras_para_calibracao(ancoras()), ancoras()):
            assert bruto["altura"] == original.molde.shape[0]
            assert bruto["largura"] == original.molde.shape[1]

    def test_um_molde_TRANSPOSTO_e_recusado_no_caminho_de_PRODUCAO(self):
        """100x28 declarado como 28x100 pede os mesmos 2800 bytes.

        Ele sobrevivia ao `reshape`, batia no guard
        `forma.shape[0] > alvo.shape[0]` de `casamento_da_ancora` e devolvia
        0.0 para TODO frame, para sempre: o mercado sumia sem uma linha de
        log. Verbatim o desfecho que `molde_de_hex` diz impedir -- e que ele
        nao impedia aqui, porque `ancoras_de_calibracao` chamava
        `molde_de_hex(molde)` sem `forma_esperada`.
        """
        dados = ancoras_para_calibracao(ancoras())
        molde = dados[0]["molde"]
        assert molde["altura"] != molde["largura"], (
            "um molde quadrado nao provaria nada aqui"
        )
        molde["altura"], molde["largura"] = molde["largura"], molde["altura"]

        with pytest.raises(ValueError, match="transposto|nao bate|Recalibre"):
            ancoras_de_calibracao(dados)

    def test_um_calibration_json_ANTIGO_sem_a_forma_continua_carregando(self):
        """Compatibilidade, pelo mesmo criterio do `.get` do banner_manutencao.

        Um arquivo gravado antes desta mudanca nao tem `altura`/`largura` nas
        `mercado_ancoras`. Ele nao ganha a conferencia -- recalibrar o mercado
        a acrescenta --, mas nao pode deixar de carregar.
        """
        dados = ancoras_para_calibracao(ancoras())
        for bruto in dados:
            del bruto["altura"]
            del bruto["largura"]

        voltaram = ancoras_de_calibracao(dados)

        assert [a.nome for a in voltaram] == [a.nome for a in ancoras()]
        for antes, depois in zip(ancoras(), voltaram):
            assert np.array_equal(antes.molde, depois.molde)

    def test_uma_forma_do_tipo_errado_e_ignorada_em_vez_de_estourar(self):
        """`"28"` em texto nao pode virar `TypeError` no meio do farm."""
        dados = ancoras_para_calibracao(ancoras())
        dados[0]["altura"] = "28"
        voltaram = ancoras_de_calibracao(dados)
        assert len(voltaram) == len(ancoras())


class TestOsNumerosDeCampoContraAsGRAVACOES:
    """O censo inteiro dos 335 frames — so roda onde `recordings/` existe."""

    def test_o_censo_completo_nao_e_afirmavel_num_clone_limpo(self):
        recordings = (
            Path(__file__).resolve().parents[1] / "recordings"
        )
        if not recordings.is_dir():
            pytest.skip(
                "recordings/ e gitignored e nao se materializa num worktree "
                "nem num clone limpo. O censo dos 335 frames esta no "
                "01-04-SUMMARY.md; as fixtures VERSIONADAS acima carregam os "
                "dois extremos dele (pior positivo 0.9037, melhor negativo "
                "0.5337)."
            )
        assert (recordings / "20260828-053003-mercado-fechado").is_dir()
