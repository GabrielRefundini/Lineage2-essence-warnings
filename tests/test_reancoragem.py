"""O scanner reencontra a party window sozinho quando ela e movida (ADVC-02).

O INCIDENTE, medido em campo em 2026-08-31: o usuario arrastou a party window
dentro do jogo e o scanner passou a ler os pixels errados. A unica saida era
ele PERCEBER e rodar `calibrar.bat` a mao.

Os dois desfechos de um deslocamento, os dois ruins:

  - deslocamento GRANDE: a ancora some, `ui_visivel` cai, o scanner fica cego.
    Honesto, e sem alerta nenhum ate alguem perceber.
  - deslocamento PEQUENO (15 a 40 px, ja documentado em `visao.py:744`): passa
    pela ancora e faz TODAS as linhas lerem errado.

A REGRA QUE MANDA EM TODAS AS OUTRAS, e por isso a maioria dos casos deste
arquivo e de RECUSA: UM REANCORAMENTO ERRADO E PIOR QUE FICAR CEGO. Cegueira e
honesta -- o usuario nao recebe alerta e o console diz por que. Um
reancoramento errado faz o scanner ler com confianca um lugar que nao e a party
window, e ai ele MENTE. Toda duvida resolve em NAO reancorar.
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import threading
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import l2scanner.reancoragem as reancoragem
from l2scanner.calibracao import Calibracao
from l2scanner.captura_janela import JanelaSource
from l2scanner.frames import Regiao, SaudeDoFrame, _ClassificadorDeSaude
from l2scanner.reancoragem import (
    Reancorador,
    adotar_geometria,
    linhas_que_cabem,
    motivo_para_recusar,
)

FIXTURES = Path(__file__).parent / "fixtures" / "party_estavel_com_vazamento"

# A janela do jogo em que a busca acontece. Numero da maquina do usuario.
ALTURA_DA_JANELA = 1080
LARGURA_DA_JANELA = 1920


@pytest.fixture
def antiga() -> Calibracao:
    """A calibracao REAL do usuario, com assinaturas, nomes e limiares.

    Vem da fixture e nao de um objeto sintetico de proposito: o que este
    arquivo precisa provar e que a adocao nao apaga nada do que uma calibracao
    de verdade carrega.
    """
    cal = Calibracao.carregar(FIXTURES / "calibracao.json")
    # As regioes dos OUTROS recursos, que a party nunca deveria tocar.
    # Ver WINDOWS #13.
    return replace(
        cal,
        tiat_chat=Regiao(10, 20, 30, 40),
        tiat_alvo=Regiao(50, 60, 70, 80),
        banner_manutencao=Regiao(90, 100, 110, 120),
        mercado_limiar_de_glifo=0.87,
        mercado_grade={"linhas": 10, "passo": 45},
    )


def nova_em(antiga: Calibracao, dx: int, dy: int) -> Calibracao:
    """A MESMA geometria, deslocada. E o que um arrasto produz."""
    janela = antiga.party_window_na_janela
    return replace(
        antiga,
        party_window=replace(
            janela, esquerda=janela.esquerda + dx, topo=janela.topo + dy
        ),
        party_window_na_janela=None,
        assinaturas=[],
        nomes=[],
        tiat_chat=None,
        tiat_alvo=None,
        banner_manutencao=None,
        mercado_limiar_de_glifo=None,
        mercado_grade=None,
    )


class FonteFalsa:
    """Uma fonte que entrega SEMPRE a mesma janela e anota o que pediram."""

    def __init__(self, completo=None):
        self.completo = (
            completo
            if completo is not None
            else np.zeros((ALTURA_DA_JANELA, LARGURA_DA_JANELA, 3), dtype=np.uint8)
        )
        self.pedidos = 0
        self.apontada_para = None

    def capturar_completo(self):
        self.pedidos += 1
        return self.completo

    def apontar_para(self, regiao):
        self.apontada_para = regiao


def detector_que_devolve(cal):
    """Um `calibrar_automatico` falso que anota com que argumentos foi chamado."""
    chamadas = []

    def detector(pixels, ox, oy):
        chamadas.append((pixels, ox, oy))
        return cal

    detector.chamadas = chamadas
    return detector


def reancorador(fonte, detector, **kwargs):
    return Reancorador(fonte=fonte, detector=detector, **kwargs)


def _janela_com_party(esquerda: int, topo: int, altura=500, largura=700):
    """Uma janela de jogo sintetica com uma party window desenhada dentro.

    As medidas sao as que `achar_barras_vermelhas` e `achar_icone_a_esquerda`
    reconhecem: barra de HP vermelha saturada de 120x8, barra de MP azul 11 px
    abaixo, icone escuro de 24 px a esquerda, quatro linhas com 46 px de passo.
    """
    janela = np.full((altura, largura, 3), 40, dtype=np.uint8)
    for linha in range(4):
        y = topo + linha * 46
        janela[y : y + 8, esquerda + 40 : esquerda + 160] = (30, 30, 220)
        janela[y + 11 : y + 19, esquerda + 40 : esquerda + 160] = (220, 60, 30)
        janela[y - 6 : y + 18, esquerda : esquerda + 24] = 8
        janela[y - 4 : y + 10, esquerda + 4 : esquerda + 12] = 240
    return janela


class TestQuandoProcurar:
    """So procura quando ESTA CEGO, e nem a cada tick de cegueira."""

    def test_nao_procura_com_a_visao_boa(self, antiga):
        fonte = FonteFalsa()
        detector = detector_que_devolve(nova_em(antiga, 40, 40))
        r = reancorador(fonte, detector)

        assert r.talvez_reancorar(0, antiga) is None
        assert fonte.pedidos == 0
        assert detector.chamadas == []

    def test_nao_procura_antes_do_limiar(self, antiga):
        fonte = FonteFalsa()
        detector = detector_que_devolve(nova_em(antiga, 40, 40))
        r = reancorador(fonte, detector, ticks_para_procurar=45)

        for ticks in range(1, 45):
            assert r.talvez_reancorar(ticks, antiga) is None
        assert detector.chamadas == []

    def test_procura_ao_cruzar_o_limiar(self, antiga):
        fonte = FonteFalsa()
        detector = detector_que_devolve(nova_em(antiga, 40, 40))
        r = reancorador(fonte, detector, ticks_para_procurar=45)

        assert r.talvez_reancorar(45, antiga) is not None
        assert len(detector.chamadas) == 1

    def test_nao_procura_a_cada_tick_de_cegueira(self, antiga):
        """A busca custa 113 ms medidos. A 1 Hz, uma por tick e caro e inutil."""
        fonte = FonteFalsa()
        detector = detector_que_devolve(None)  # nao acha nada
        r = reancorador(fonte, detector, ticks_para_procurar=45, ticks_entre_buscas=15)

        for ticks in range(45, 60):
            r.talvez_reancorar(ticks, antiga)

        assert len(detector.chamadas) == 1

    def test_volta_a_procurar_depois_do_intervalo(self, antiga):
        fonte = FonteFalsa()
        detector = detector_que_devolve(None)
        r = reancorador(fonte, detector, ticks_para_procurar=45, ticks_entre_buscas=15)

        for ticks in range(45, 76):
            r.talvez_reancorar(ticks, antiga)

        assert len(detector.chamadas) == 3  # 45, 60 e 75

    def test_a_busca_le_a_janela_do_jogo_em_coordenadas_da_janela(self, antiga):
        """`ox=oy=0`: a geometria sai em coordenadas DA JANELA, nao de desktop.

        E o mesmo referencial de `party_window_na_janela`, que e o que o
        caminho `--janela` recorta.
        """
        fonte = FonteFalsa()
        detector = detector_que_devolve(nova_em(antiga, 40, 40))
        r = reancorador(fonte, detector, ticks_para_procurar=45)

        r.talvez_reancorar(45, antiga)

        pixels, ox, oy = detector.chamadas[0]
        assert (ox, oy) == (0, 0)
        assert pixels is fonte.completo


class TestOQueEAdotado:
    """SO A GEOMETRIA. Ver WINDOWS #13."""

    def test_adota_a_posicao_nova(self, antiga):
        nova = nova_em(antiga, 40, -25)
        adotada = adotar_geometria(antiga, nova)

        assert adotada.party_window_na_janela == nova.party_window
        assert adotada.ancora == nova.ancora
        assert adotada.layout.icone_x == nova.layout.icone_x
        assert adotada.layout.hp_y == nova.layout.hp_y
        assert adotada.layout.passo == nova.layout.passo

    def test_nao_apaga_nada_do_que_a_party_nao_mediu(self, antiga):
        """WINDOWS #13: adotar o objeto INTEIRO custou 13 moldes de glifo.

        `calibrar_automatico` devolve uma `Calibracao` montada DO ZERO, e todo
        campo que a party window nao possui vem `None` nela. Adotar o objeto
        todo seria o mesmo incidente de 2026-08-30, agora sem nem um comando
        do usuario para culpar.
        """
        nova = nova_em(antiga, 40, -25)
        adotada = adotar_geometria(antiga, nova)

        assert adotada.assinaturas == antiga.assinaturas
        assert adotada.nomes == antiga.nomes
        assert adotada.nome_proprio == antiga.nome_proprio
        assert adotada.hp_proprio == antiga.hp_proprio
        assert adotada.limiares_hp == antiga.limiares_hp
        assert adotada.limiares_mp == antiga.limiares_mp
        assert adotada.tiat_chat == antiga.tiat_chat
        assert adotada.tiat_alvo == antiga.tiat_alvo
        assert adotada.banner_manutencao == antiga.banner_manutencao
        assert adotada.mercado_limiar_de_glifo == antiga.mercado_limiar_de_glifo
        assert adotada.mercado_grade == antiga.mercado_grade
        assert adotada.janela == antiga.janela
        assert adotada.geometria_da_tela == antiga.geometria_da_tela

    def test_mantem_o_recorte_do_nome_e_os_limiares_do_layout(self, antiga):
        """Trocar `nome_dx` invalidaria TODA assinatura, em silencio.

        As assinaturas foram gravadas com o recorte da calibracao ANTIGA (aqui,
        `nome_dx=26`), e `calibrar_automatico` sempre devolve os defaults de
        hoje (`nome_dx=16`). Adotar os defaults mudaria o recorte por baixo de
        assinaturas que continuam validas: a versao para IDENTIDADE do
        WINDOWS #13.
        """
        nova = nova_em(antiga, 40, -25)
        nova = replace(nova, layout=replace(nova.layout, nome_dx=16, nome_largura=110))

        adotada = adotar_geometria(antiga, nova)

        assert adotada.layout.nome_dx == antiga.layout.nome_dx
        assert adotada.layout.nome_dy == antiga.layout.nome_dy
        assert adotada.layout.nome_largura == antiga.layout.nome_largura
        assert adotada.layout.nome_altura == antiga.layout.nome_altura
        assert adotada.layout.icone_desvio_min == antiga.layout.icone_desvio_min
        assert adotada.layout.ancora_desvio_min == antiga.layout.ancora_desvio_min
        assert adotada.layout.borda_v_max == antiga.layout.borda_v_max
        assert adotada.layout.max_linhas == antiga.layout.max_linhas

    def test_mantem_a_forma_das_barras(self, antiga):
        """A barra nao muda de tamanho quando a janela e arrastada.

        E `achar_barras_vermelhas` mede a parte PREENCHIDA: uma party detectada
        com HP parcial devolve barra mais estreita do que a real, e adotar ISSO
        inflaria toda leitura de HP.
        """
        nova = nova_em(antiga, 40, -25)
        nova = replace(
            nova,
            layout=replace(nova.layout, barra_largura=114, barra_altura=7),
        )

        adotada = adotar_geometria(antiga, nova)

        assert adotada.layout.barra_largura == antiga.layout.barra_largura
        assert adotada.layout.barra_altura == antiga.layout.barra_altura
        assert adotada.layout.icone_tamanho == antiga.layout.icone_tamanho

    def test_a_lista_viva_de_assinaturas_continua_sendo_a_MESMA(self, antiga):
        """O batismo e o aprendiz mutam essa lista em memoria (D-08).

        Uma COPIA faria o nome aprendido depois do reancoramento valer para uma
        calibracao que ninguem mais le.
        """
        adotada = adotar_geometria(antiga, nova_em(antiga, 40, -25))

        assert adotada.assinaturas is antiga.assinaturas

    def test_a_fonte_passa_a_recortar_no_lugar_novo(self, antiga):
        fonte = FonteFalsa()
        nova = nova_em(antiga, 40, -25)
        r = reancorador(fonte, detector_que_devolve(nova), ticks_para_procurar=45)

        adotada = r.talvez_reancorar(45, antiga)

        assert adotada is not None
        assert fonte.apontada_para == adotada.party_window_na_janela

    def test_a_janela_source_de_verdade_obedece_o_apontar_para(self):
        """Codigo de producao, e nao um duble: sem isto o recorte nao muda.

        Adotar a geometria e NAO reapontar a fonte deixaria o scanner lendo o
        retangulo antigo com uma calibracao nova -- pior que nao reancorar.
        """
        janela = np.zeros((200, 300, 3), dtype=np.uint8)
        janela[20:40, 10:60] = 200  # o lugar VELHO
        janela[120:140, 110:160] = 90  # o lugar NOVO

        fonte = JanelaSource.__new__(JanelaSource)
        fonte._trava = threading.Lock()
        fonte._ultimo = janela
        fonte._completo_do_ultimo_frame = None
        fonte._relativa = True
        fonte._regiao = Regiao(esquerda=10, topo=20, largura=50, altura=20)
        fonte._extras = {}
        fonte._saude = _ClassificadorDeSaude()
        fonte._contador = 0

        antes = fonte.capturar()
        assert int(antes.pixels.mean()) == 200

        fonte.apontar_para(Regiao(esquerda=110, topo=120, largura=50, altura=20))
        depois = fonte.capturar()

        assert int(depois.pixels.mean()) == 90
        assert depois.saude is not SaudeDoFrame.FALHA_DE_CAPTURA


class TestPlausibilidade:
    """A geometria nova so vale se for PLAUSIVEL contra a antiga."""

    def forma(self):
        return (ALTURA_DA_JANELA, LARGURA_DA_JANELA)

    def test_aceita_o_deslocamento_puro(self, antiga):
        nova = nova_em(antiga, 40, -25)
        assert motivo_para_recusar(antiga, nova, self.forma()) is None

    def test_recusa_passo_diferente(self, antiga):
        """Passo e propriedade do skin, nao da posicao. Arrastar nao reespaca."""
        nova = nova_em(antiga, 40, 0)
        nova = replace(nova, layout=replace(nova.layout, passo=48))

        motivo = motivo_para_recusar(antiga, nova, self.forma())

        assert motivo is not None
        assert "passo" in motivo

    def test_aceita_um_pixel_de_diferenca_no_passo(self, antiga):
        nova = nova_em(antiga, 40, 0)
        nova = replace(nova, layout=replace(nova.layout, passo=62))

        assert motivo_para_recusar(antiga, nova, self.forma()) is None

    def test_recusa_largura_de_barra_diferente(self, antiga):
        nova = nova_em(antiga, 40, 0)
        nova = replace(nova, layout=replace(nova.layout, barra_largura=60))

        motivo = motivo_para_recusar(antiga, nova, self.forma())

        assert motivo is not None
        assert "barra" in motivo

    def test_recusa_janela_de_largura_muito_outra(self, antiga):
        nova = nova_em(antiga, 40, 0)
        nova = replace(
            nova, party_window=replace(nova.party_window, largura=400)
        )

        motivo = motivo_para_recusar(antiga, nova, self.forma())

        assert motivo is not None
        assert "largura" in motivo

    def test_recusa_janela_que_nao_cabe_no_frame(self, antiga):
        """Um retangulo que sai da janela vira FALHA_DE_CAPTURA para sempre."""
        nova = nova_em(antiga, 40, 0)
        nova = replace(
            nova,
            party_window=replace(nova.party_window, topo=ALTURA_DA_JANELA - 10),
        )

        motivo = motivo_para_recusar(antiga, nova, self.forma())

        assert motivo is not None
        assert "cabe" in motivo

    def test_recusa_quando_cabem_menos_linhas(self, antiga):
        """Menos linhas = membros deixados de fora EM SILENCIO."""
        nova = nova_em(antiga, 0, 0)
        nova = replace(nova, party_window=replace(nova.party_window, altura=180))

        motivo = motivo_para_recusar(antiga, nova, self.forma())

        assert motivo is not None
        assert "linha" in motivo

    def test_recusa_quando_o_layout_antigo_nao_cabe_na_janela_nova(self, antiga):
        """A mistura tem que ser coerente: forma antiga DENTRO da janela nova."""
        nova = nova_em(antiga, 0, 0)
        nova = replace(
            nova,
            party_window=replace(nova.party_window, largura=160),
            layout=replace(nova.layout, barra_x=42),
        )

        motivo = motivo_para_recusar(antiga, nova, self.forma())

        assert motivo is not None

    def test_recusa_calibracao_sem_posicao_dentro_da_janela(self, antiga):
        """Sem `party_window_na_janela` nao ha referencial comum para comparar."""
        velha = replace(antiga, party_window_na_janela=None)
        nova = nova_em(antiga, 40, 0)

        motivo = motivo_para_recusar(velha, nova, self.forma())

        assert motivo is not None

    def test_nao_reancora_quando_esta_no_mesmo_lugar(self, antiga):
        """Achar a party onde ela ja estava NAO e um deslocamento.

        E um diagnostico util: a cegueira tem outra causa.
        """
        motivo = motivo_para_recusar(antiga, nova_em(antiga, 0, 0), self.forma())

        assert motivo is not None
        assert "MESMO lugar" in motivo

    def test_linhas_que_cabem_conta_a_janela_real_do_usuario(self, antiga):
        assert linhas_que_cabem(antiga.party_window_na_janela, antiga.layout) == 8


class TestOLog:
    """O log e parte da entrega."""

    def test_diz_de_onde_para_onde_em_numeros(self, antiga, caplog):
        fonte = FonteFalsa()
        nova = nova_em(antiga, 40, -25)
        r = reancorador(fonte, detector_que_devolve(nova), ticks_para_procurar=45)

        with caplog.at_level("INFO", logger="l2scanner"):
            r.talvez_reancorar(45, antiga)

        texto = caplog.text
        velha = antiga.party_window_na_janela
        assert f"({velha.esquerda},{velha.topo})" in texto
        assert f"({velha.esquerda + 40},{velha.topo - 25})" in texto
        assert "+40" in texto and "-25" in texto

    def test_diz_que_o_calibration_json_nao_foi_tocado(self, antiga, caplog):
        fonte = FonteFalsa()
        nova = nova_em(antiga, 40, -25)
        r = reancorador(fonte, detector_que_devolve(nova), ticks_para_procurar=45)

        with caplog.at_level("INFO", logger="l2scanner"):
            r.talvez_reancorar(45, antiga)

        assert "calibration.json" in caplog.text
        assert "calibrar.bat" in caplog.text

    def test_avisa_que_procurou_e_nao_adotou(self, antiga, caplog):
        fonte = FonteFalsa()
        r = reancorador(
            fonte, detector_que_devolve(None), ticks_para_procurar=45,
            ticks_entre_buscas=15,
        )

        with caplog.at_level("INFO", logger="l2scanner"):
            r.talvez_reancorar(45, antiga)

        assert "Procurei" in caplog.text

    def test_avisa_UMA_VEZ_e_nao_a_cada_busca(self, antiga, caplog):
        """Uma linha por busca durante um farm de tres horas nao e lida."""
        fonte = FonteFalsa()
        r = reancorador(
            fonte, detector_que_devolve(None), ticks_para_procurar=45,
            ticks_entre_buscas=15,
        )

        with caplog.at_level("INFO", logger="l2scanner"):
            for ticks in range(45, 200):
                r.talvez_reancorar(ticks, antiga)

        assert caplog.text.count("Procurei") == 1

    def test_volta_a_avisar_depois_de_enxergar_de_novo(self, antiga, caplog):
        fonte = FonteFalsa()
        r = reancorador(
            fonte, detector_que_devolve(None), ticks_para_procurar=45,
            ticks_entre_buscas=15,
        )

        with caplog.at_level("INFO", logger="l2scanner"):
            for ticks in range(45, 100):
                r.talvez_reancorar(ticks, antiga)
            r.talvez_reancorar(0, antiga)  # voltou a enxergar
            for ticks in range(45, 100):
                r.talvez_reancorar(ticks, antiga)

        assert caplog.text.count("Procurei") == 2

    def test_a_recusa_diz_o_motivo(self, antiga, caplog):
        fonte = FonteFalsa()
        nova = nova_em(antiga, 40, 0)
        nova = replace(nova, layout=replace(nova.layout, passo=48))
        r = reancorador(fonte, detector_que_devolve(nova), ticks_para_procurar=45)

        with caplog.at_level("INFO", logger="l2scanner"):
            assert r.talvez_reancorar(45, antiga) is None

        assert "passo" in caplog.text

    def test_o_modulo_inteiro_e_ascii(self):
        """A fonte do cmd.exe varia; acento e travessao viram lixo na tela."""
        fonte = Path(inspect.getfile(reancoragem)).read_text(encoding="utf-8")
        fonte.encode("ascii")


class TestNaoEscreveNoDisco:
    """A adocao vale para a SESSAO, em memoria."""

    def test_o_modulo_nao_grava_nada(self):
        """Persistir faria um reancoramento errado sobreviver ao reinicio.

        E o usuario perderia a calibracao boa sem ter pedido nada.
        """
        fonte = Path(inspect.getfile(reancoragem)).read_text(encoding="utf-8")

        assert "salvar" not in fonte
        assert "json.dump" not in fonte
        assert "open(" not in fonte
        assert "write_text" not in fonte

    def test_o_arquivo_de_calibracao_fica_byte_a_byte_igual(self, antiga, tmp_path):
        caminho = tmp_path / "calibration.json"
        original = (FIXTURES / "calibracao.json").read_bytes()
        caminho.write_bytes(original)

        fonte = FonteFalsa()
        r = reancorador(
            fonte, detector_que_devolve(nova_em(antiga, 40, -25)),
            ticks_para_procurar=45,
        )
        assert r.talvez_reancorar(45, antiga) is not None

        assert caminho.read_bytes() == original
        assert json.loads(caminho.read_text())["party_window_na_janela"] == {
            "esquerda": 18, "topo": 325, "largura": 174, "altura": 522
        }


class TestVarreduraContida:
    """O usuario roda DOIS clientes."""

    def test_a_busca_so_enxerga_a_janela_mirada(self, antiga):
        """`JanelaSource.capturar_completo` devolve UMA janela, nunca a tela.

        A captura e por TITULO (`window_name=` no `WindowsCapture`, ver
        `captura_janela.py`), entao a varredura fica contida numa janela so. Se
        ela pudesse varrer o desktop, acharia a party window do OUTRO cliente e
        o scanner passaria a vigiar a party errada EM SILENCIO.
        """
        assinatura = inspect.signature(Reancorador.__init__)
        assert "fonte" in assinatura.parameters

        fonte = FonteFalsa()
        detector = detector_que_devolve(nova_em(antiga, 10, 10))
        r = reancorador(fonte, detector, ticks_para_procurar=45)
        r.talvez_reancorar(45, antiga)

        # Os pixels analisados sao EXATAMENTE os que a fonte da janela entregou.
        assert detector.chamadas[0][0] is fonte.completo
        assert fonte.pedidos == 1

    def test_o_modulo_nao_captura_a_tela(self):
        """Nenhum caminho deste modulo pode chamar `mss` ou `capturar_tela`."""
        fonte = Path(inspect.getfile(reancoragem)).read_text(encoding="utf-8")

        assert "capturar_tela" not in fonte
        assert "import mss" not in fonte
        assert "monitors" not in fonte

    def test_a_busca_de_verdade_reancora_uma_party_deslocada(self, caplog):
        """SEM DUBLE NENHUM: o detector do `calibrar.bat --auto` de ponta a ponta.

        E o unico caso que prova que a `Calibracao` que aquele detector devolve
        passa nos criterios de plausibilidade e sobrevive a adocao. Os demais
        casos usam um detector falso para construir a situacao; este constroi os
        PIXELS.

        A party sintetica usa as constantes que o detector reconhece: barra
        vermelha saturada de 120x8, MP azul 11 px abaixo, icone escuro de 24 px
        a esquerda, quatro linhas com 46 px de passo. Custo medido: 4 ms por
        busca neste frame de 700x500.
        """
        antes = _janela_com_party(esquerda=120, topo=100)
        depois = _janela_com_party(esquerda=160, topo=75)

        from l2scanner.calibrar import calibrar_automatico

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            calibrada = calibrar_automatico(antes, 0, 0)
        assert calibrada is not None
        # `main()` grava a posicao dentro da janela depois de calibrar; aqui
        # `ox=oy=0`, entao as duas coincidem.
        calibrada = replace(
            calibrada,
            party_window_na_janela=calibrada.party_window,
            nomes=["Kaus"],
            assinaturas=[object()],
        )

        fonte = FonteFalsa(completo=depois)
        # SEM `detector=`: quem roda e `calibrar.calibrar_automatico`, pelo
        # import tardio.
        r = Reancorador(fonte=fonte, ticks_para_procurar=45)

        with caplog.at_level("INFO", logger="l2scanner"):
            adotada = r.talvez_reancorar(45, calibrada)

        assert adotada is not None
        assert adotada.party_window_na_janela.esquerda == (
            calibrada.party_window_na_janela.esquerda + 40
        )
        assert adotada.party_window_na_janela.topo == (
            calibrada.party_window_na_janela.topo - 25
        )
        assert adotada.assinaturas is calibrada.assinaturas
        assert fonte.apontada_para == adotada.party_window_na_janela
        # A conversa do detector nao vaza para o console do scanner.
        assert "Procurando barras de HP" not in caplog.text

    def test_frame_vazio_nao_vira_reancoramento(self, antiga, caplog):
        fonte = FonteFalsa()
        fonte.completo = None
        detector = detector_que_devolve(nova_em(antiga, 40, 0))
        r = reancorador(fonte, detector, ticks_para_procurar=45)

        with caplog.at_level("INFO", logger="l2scanner"):
            assert r.talvez_reancorar(45, antiga) is None

        assert detector.chamadas == []
