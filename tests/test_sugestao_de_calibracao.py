"""A ferramenta PROPOE e o usuario confirma — em vez de descrever em prosa.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
MEDIDO EM CAMPO, 2026-08-29, na primeira vez que uma mao humana tentou a
calibracao de mercado inteira: *"esta muito dificil calibrar isso e e muito
facil eu errar na interpretacao do que esta sendo pedido"*. As cinco instrucoes
em prosa geraram cinco duvidas, e uma delas virou erro gravado — o usuario
incluiu a faixa de cabecalho na area da lista e a grade saiu com **11 linhas**
contra as 10 medidas para o layout adena.

Aquele erro so foi pego porque `derivar_grade` tinha, por acaso, uma expectativa
medida para aquele campo. Os outros quatro retangulos nao tinham guarda nenhuma.

A capacidade de medir tudo isso ja existia e nao era oferecida: um agente achou
a ancora de titulo por casamento de molde a 0.9999 e derivou as bordas da grade
do perfil vertical, sem tocar no mouse. Este arquivo prova que agora a
ferramenta faz isso, e — igualmente importante — que a calibracao de PARTY, que
compartilha `_selecionar_regiao` e funciona hoje, nao mudou em nada.

O QUE E SINTETICO E O QUE FOI MEDIDO DE VERDADE
------------------------------------------------
Os frames aqui sao SINTETICOS, construidos com as constantes MEDIDAS em
`recordings/20260828-115700-calibragem/frame_000012.png`: fundo de linha
alternando 48/66, separador do cabecalho em 100, moldura interna em 68, passo de
45 px, 10 linhas, borda esquerda em 744. `recordings/` e gitignored e nao existe
neste worktree — testar contra ele deixaria a suite verde por ausencia.

Os testes contra os frames REAIS existem logo abaixo e sao PULADOS quando a
pasta nao esta presente. No checkout principal eles rodam e afirmam os numeros
exatos.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.calibrar
import l2scanner.calibrar_mercado
from l2scanner.calibrar import _selecionar_regiao
from l2scanner.calibrar_mercado import (
    MARGEM_MINIMA_PARA_PROPOR,
    _avisar_divergencia_da_grade,
    _pedir_rotulo,
    propor_rotulo,
    segmentar_glifos,
    sugerir_a_coluna_de_preco,
    sugerir_as_ancoras,
)
from l2scanner.identidade import mascara_de_texto
from l2scanner.mercado_geometria import (
    GradeMedida,
    ancora_deslocada,
    bordas_de_banda,
    cadeia_periodica,
    extensao_do_separador,
    localizar_o_titulo,
    medir_a_grade,
    perfil_por_mediana,
    trechos_de_nivel,
)
from l2scanner.mercado_visao import AncoraDoPainel

RAIZ = Path(__file__).resolve().parent.parent
GRAVACOES = RAIZ / "recordings"
FRAME_DA_GRADE = GRAVACOES / "20260828-115700-calibragem" / "frame_000012.png"
FRAME_CHEIO = (
    GRAVACOES / "20260828-060622-mercado-pagina-cheia" / "frame_000010.png"
)

# --- as constantes MEDIDAS no frame de calibragem, reproduzidas no sintetico ---
ORIGEM = (1176, 362)
TAMANHO_DO_TITULO = (100, 28)
TOPO_DA_GRADE = 618
PASSO = 45
LINHAS = 10
ESQUERDA = 744
DIREITA = 1688
FUNDO_ESCURO = 48
FUNDO_CLARO = 66
SEPARADOR = 100
MOLDURA = 68


def _painel_sintetico(
    origem: tuple[int, int] = ORIGEM,
    linhas: int = LINHAS,
    passo: int = PASSO,
    topo: int = TOPO_DA_GRADE,
) -> np.ndarray:
    """Um painel de mercado com a geometria MEDIDA, e nada mais.

    Sem texto: este frame serve as funcoes de GEOMETRIA. O frame com precos e
    construido a parte, porque a deteccao da coluna de preco depende de brilho e
    misturar as duas coisas esconderia qual delas quebrou.
    """
    pixels = np.full((1392, 1720, 3), 30, dtype=np.uint8)

    # A faixa de titulo, com textura para casar por molde (um retangulo chapado
    # tem desvio zero e `buscar_ancora` o recusaria, com razao).
    largura, altura = TAMANHO_DO_TITULO
    x, y = origem
    ruido = np.random.default_rng(7).integers(
        60, 220, (altura, largura, 3), dtype=np.uint8
    )
    pixels[y : y + altura, x : x + largura] = ruido

    pixels[:, ESQUERDA - 1] = MOLDURA
    pixels[:, DIREITA] = MOLDURA
    pixels[topo - 1, ESQUERDA:DIREITA] = SEPARADOR
    for indice in range(linhas):
        cor = FUNDO_ESCURO if indice % 2 == 0 else FUNDO_CLARO
        base = topo + indice * passo
        pixels[base : base + passo, ESQUERDA:DIREITA] = cor
    return pixels


def _ancora_do_titulo(pixels: np.ndarray) -> AncoraDoPainel:
    largura, altura = TAMANHO_DO_TITULO
    x, y = ORIGEM
    molde = cv2.cvtColor(
        pixels[y : y + altura, x : x + largura], cv2.COLOR_BGR2GRAY
    )
    return AncoraDoPainel(nome="titulo", dx=0, dy=0, molde=molde.copy())


def _escrever(pixels: np.ndarray, y: int, x: int, larguras, valor: int) -> int:
    """Blocos verticais de 9 px separados por 1 coluna. Devolve a coluna final."""
    cursor = x
    for largura in larguras:
        pixels[y : y + 9, cursor : cursor + largura] = valor
        cursor += largura + 1
    return cursor - 1


def _painel_com_precos(quantos_glifos: tuple[int, ...]) -> np.ndarray:
    """O painel sintetico com uma coluna de preco ALINHADA A DIREITA.

    Cada linha ganha, nesta ordem: um icone claro, um nome claro (as duas
    iscas), o NUMERO claro terminando sempre na mesma coluna, e a palavra de
    moeda APAGADA logo a direita dele. `quantos_glifos` diz quantos blocos o
    numero de cada linha tem — larguras diferentes na mesma coluna sao o caso
    que derrubou a primeira versao da votacao.
    """
    pixels = _painel_sintetico()
    borda_do_numero = 1299
    for indice, glifos in enumerate(quantos_glifos):
        y = TOPO_DA_GRADE + indice * PASSO + 18
        _escrever(pixels, y, 749, (27,), 255)          # icone
        _escrever(pixels, y, 785, (95,), 255)          # nome do item
        largura_do_numero = glifos * 5 - 1
        _escrever(
            pixels, y, borda_do_numero - largura_do_numero, (4,) * glifos, 255
        )
        # a palavra de moeda: APAGADA (acima de 120, abaixo de 180)
        pixels[y : y + 8, borda_do_numero + 6 : borda_do_numero + 42] = 150
        _escrever(pixels, y, 1572, (25,), 255)         # coluna sem moeda
    return pixels


# ==========================================================================
# A GEOMETRIA PURA
# ==========================================================================


class TestOPerfilEAsBordas:
    def test_a_mediana_ignora_o_texto_que_a_media_dilui(self):
        """Por que MEDIANA: um digito claro no meio da banda nao pode mover o nivel."""
        faixa = np.full((40, 100), FUNDO_ESCURO, dtype=np.uint8)
        faixa[10:19, 40:60] = 255  # o "numero" da linha

        perfil = perfil_por_mediana(faixa, 0, 100)

        assert set(np.unique(perfil)) == {float(FUNDO_ESCURO)}, (
            "a mediana deixou o texto entrar no nivel de fundo"
        )

    def test_a_linha_de_transicao_NAO_vira_uma_banda(self):
        """A transicao gasta uma linha (65 -> 52 -> 48); ela nao e uma linha da lista."""
        perfil = np.array([48.0] * 20 + [53.0] + [66.0] * 20)

        longos = [
            (a, b)
            for a, b in trechos_de_nivel(perfil, 0, perfil.size)
            if b - a >= 10
        ]

        assert longos == [(0, 20), (21, 41)]

    def test_o_FIM_da_ultima_banda_entra_como_borda(self):
        """Sem ele a cadeia fica com dez elos e a grade sai com NOVE linhas.

        Perfil no molde do frame real: a ultima banda termina em 1065, e o que
        vem depois e rodape -- niveis diferentes e comprimentos diferentes.
        Nenhum trecho longo COMECA em 1066; ele so existe como FIM da banda.
        """
        perfil = np.array(
            [66.0] * 1066 + [52.0] + [68.0] + [49.0] * 5 + [70.0] + [56.0] * 10
        )

        bordas = bordas_de_banda(perfil, 1000, perfil.size)

        assert 1066 in bordas, (
            f"a base da ultima banda sumiu do conjunto de bordas: {bordas}"
        )

    def test_o_lado_mais_contrastado_do_separador_NAO_decide_a_borda(self):
        """A fragilidade que a deteccao por derivada tinha, e que a por trecho nao tem.

        Aqui o separador entra com 70 niveis de degrau (30 -> 100) e sai com 52
        (100 -> 48). Marcando "a borda de maior degrau", a borda gravada seria a
        de CIMA -- a linha do separador -- e a grade comecaria dentro do
        cabecalho, deslocada em 1 px, com uma linha a menos.
        """
        perfil = np.array([30.0] * 30 + [100.0] + [48.0] * 45 + [66.0] * 45)

        bordas = bordas_de_banda(perfil, 0, perfil.size)
        cadeia = cadeia_periodica(bordas)

        assert 31 in bordas, f"o topo da primeira linha de dados sumiu: {bordas}"
        assert cadeia[0] == 31, (
            f"a cadeia comecou em {cadeia[0]} -- 30 e a linha do SEPARADOR, e "
            f"comecar nela desloca a grade inteira em 1 px: {bordas}"
        )

    def test_o_empate_de_cadeia_e_desfeito_pelo_ERRO_e_nao_pela_ordem(self):
        """Duas bordas a 1 px produzem cadeias do mesmo tamanho; vence a mais justa."""
        bordas = [30, 31, 76, 121, 166]

        assert cadeia_periodica(bordas) == [31, 76, 121, 166]


class TestACadeiaPeriodica:
    def test_pega_a_maior_sequencia_e_ignora_o_ruido_de_cima(self):
        bordas = [402, 521, 555, 599, 618, 663, 706, 753, 796, 843, 1087]

        cadeia = cadeia_periodica(bordas)

        assert cadeia == [618, 663, 706, 753, 796, 843]

    def test_as_posicoes_previstas_saem_da_BASE_e_nao_da_anterior(self):
        """O jitter de +-2 da linha de transicao nao pode se acumular.

        Encadeando a partir da borda anterior, o erro soma e a cadeia se perde
        por volta da setima banda. Estas dez bordas alternam +45/+43 exatamente
        como as medidas no frame real.
        """
        bordas = [618, 663, 706, 753, 796, 843, 886, 933, 976, 1023, 1066]

        assert len(cadeia_periodica(bordas)) == 11

    def test_sem_periodicidade_devolve_vazio(self):
        assert cadeia_periodica([10, 400, 900]) == []


class TestOSeparadorDoCabecalho:
    def test_acha_a_faixa_pelo_plato_sem_limiar_fixo(self):
        linha = np.full((1, 1720), 30, dtype=np.uint8)
        linha[0, ESQUERDA:DIREITA] = SEPARADOR
        linha[0, ESQUERDA - 1] = MOLDURA

        assert extensao_do_separador(linha, 0) == (ESQUERDA, DIREITA)


class TestAMedicaoDaGrade:
    def test_reproduz_a_geometria_medida_no_frame_de_calibragem(self):
        pixels = _painel_sintetico()

        grade = medir_a_grade(pixels, (*ORIGEM, *TAMANHO_DO_TITULO))

        assert grade == GradeMedida(
            esquerda=ESQUERDA, topo=TOPO_DA_GRADE, largura=DIREITA - ESQUERDA,
            passo=PASSO, linhas=LINHAS,
        )

    def test_o_cabecalho_fica_de_fora_por_construcao(self):
        """O erro humano de 2026-08-29, agora impossivel de cometer sem ver.

        O separador do cabecalho esta em `topo - 1`; a grade comeca em `topo`.
        Nao ha caminho pelo qual a faixa `Auction List | Total Price | ...`
        entre na area proposta.
        """
        pixels = _painel_sintetico()

        grade = medir_a_grade(pixels, (*ORIGEM, *TAMANHO_DO_TITULO))

        assert grade.topo == TOPO_DA_GRADE
        assert pixels[grade.topo - 1, ESQUERDA, 0] == SEPARADOR

    def test_a_altura_e_multiplo_EXATO_do_passo(self):
        """`derivar_grade` conta linhas por divisao inteira; sobra vira erro calado."""
        pixels = _painel_sintetico()

        grade = medir_a_grade(pixels, (*ORIGEM, *TAMANHO_DO_TITULO))

        assert grade.altura % grade.passo == 0
        assert grade.altura // grade.passo == LINHAS

    def test_um_frame_sem_grade_devolve_None_em_vez_de_palpite(self):
        """Sugestao errada e pior que nenhuma: o usuario aperta ENTER nela."""
        pixels = np.full((1392, 1720, 3), 30, dtype=np.uint8)

        assert medir_a_grade(pixels, (*ORIGEM, *TAMANHO_DO_TITULO)) is None

    def test_frame_vazio_devolve_None_sem_estourar(self):
        assert medir_a_grade(np.zeros((0, 0, 3), np.uint8), (0, 0, 1, 1)) is None


class TestALocalizacaoDoTitulo:
    def test_acha_a_faixa_de_titulo_pela_ancora(self):
        pixels = _painel_sintetico()

        achado = localizar_o_titulo(pixels, [_ancora_do_titulo(pixels)])

        assert achado is not None
        retangulo, score, nome = achado
        assert retangulo == (*ORIGEM, *TAMANHO_DO_TITULO)
        assert score > 0.99
        assert nome == "titulo"

    def test_sem_ancora_conhecida_nao_ha_sugestao(self):
        """Primeira calibracao da vida: o usuario desenha, e o resto vem dai."""
        assert localizar_o_titulo(_painel_sintetico(), []) is None

    def test_casamento_fraco_NAO_vira_sugestao(self):
        pixels = _painel_sintetico()
        ancora = _ancora_do_titulo(pixels)
        outro = np.full((1392, 1720, 3), 90, dtype=np.uint8)
        outro[100:400, 100:400] = np.random.default_rng(3).integers(
            0, 255, (300, 300, 3), dtype=np.uint8
        )

        assert localizar_o_titulo(outro, [ancora]) is None


class TestOsDeslocamentosDeAncora:
    def test_empurra_para_dentro_em_vez_de_recusar(self):
        """MEDIDO: em `frame_000012` o painel encosta na direita e a caixa de
        60x60 do `X` cairia em 1670..1730, dez pixels alem da borda."""
        caixa = ancora_deslocada((1176, 362), (494, -10), (60, 60), (1392, 1720))

        assert caixa == (1660, 352, 60, 60)

    def test_o_que_nem_empurrado_cabe_devolve_None(self):
        assert ancora_deslocada((0, 0), (0, 0), (2000, 60), (1392, 1720)) is None

    def test_prefere_o_deslocamento_da_calibracao_ANTERIOR(self):
        """A anterior foi medida na maquina do usuario; a constante, numa janela."""
        anterior = AncoraDoPainel(
            nome="botao_fechar", dx=400, dy=20,
            molde=np.zeros((40, 50), dtype=np.uint8),
        )

        saida = sugerir_as_ancoras((1392, 1720), (100, 100), [anterior])

        assert saida["botao_fechar"] == (500, 120, 50, 40)

    def test_sem_anterior_cai_nas_constantes_medidas(self):
        saida = sugerir_as_ancoras((1392, 1720), (100, 100), [])

        assert saida["botao_fechar"] == (594, 90, 60, 60)
        assert saida["canto_inf_dir"] == (594, 765, 60, 60)
        assert "titulo" not in saida, "o titulo E a origem, nao um derivado dela"


# ==========================================================================
# A COLUNA DE PRECO
# ==========================================================================


class TestASugestaoDaColunaDePreco:
    def test_propoe_um_retangulo_por_linha_com_a_contagem_certa(self):
        glifos = (5,) * LINHAS
        pixels = _painel_com_precos(glifos)
        grade = medir_a_grade(pixels, (*ORIGEM, *TAMANHO_DO_TITULO))

        numeros, _sufixos = sugerir_a_coluna_de_preco(pixels, grade)

        assert len(numeros) == LINHAS
        for (x, y, largura, altura), esperado in zip(numeros, glifos):
            _faixa, runs = segmentar_glifos(pixels[y : y + altura, x : x + largura])
            assert len(runs) == esperado

    def test_larguras_DIFERENTES_na_mesma_coluna_nao_dividem_o_voto(self):
        """A regressao MEDIDA em `frame_000010`.

        Ali convivem `100,00`, `18,90` e `3,00` na mesma coluna alinhada a
        direita. Votando no par `(inicio, fim)`, cada largura virava um
        candidato e so 3 das 6 linhas eram propostas -- justamente as curtas,
        que sao as que MENOS acrescentam digitos ao conjunto.
        """
        glifos = (6, 4, 5, 4, 5, 4, 6, 4, 5, 4)
        pixels = _painel_com_precos(glifos)
        grade = medir_a_grade(pixels, (*ORIGEM, *TAMANHO_DO_TITULO))

        numeros, _ = sugerir_a_coluna_de_preco(pixels, grade)

        assert len(numeros) == LINHAS
        contagens = [
            len(segmentar_glifos(pixels[y : y + a, x : x + larg])[1])
            for (x, y, larg, a) in numeros
        ]
        assert contagens == list(glifos)

    def test_o_icone_e_o_nome_do_item_NAO_sao_confundidos_com_preco(self):
        """As duas iscas do frame real: o icone e o nome dourado ao lado dele."""
        pixels = _painel_com_precos((5,) * LINHAS)
        grade = medir_a_grade(pixels, (*ORIGEM, *TAMANHO_DO_TITULO))

        numeros, _ = sugerir_a_coluna_de_preco(pixels, grade)

        for x, _y, largura, _altura in numeros:
            assert x > 1200, (
                f"a coluna proposta comeca em x={x} -- e o icone (749) ou o "
                f"nome do item (785), nao o preco"
            )
            assert x + largura < 1400

    def test_a_palavra_de_moeda_e_proposta_sem_engolir_o_ultimo_digito(self):
        pixels = _painel_com_precos((5,) * LINHAS)
        grade = medir_a_grade(pixels, (*ORIGEM, *TAMANHO_DO_TITULO))

        numeros, sufixos = sugerir_a_coluna_de_preco(pixels, grade)

        assert len(sufixos) == len(numeros)
        for (nx, _ny, nlarg, _na), (sx, _sy, _sl, _sa) in zip(numeros, sufixos):
            assert sx >= nx + nlarg - 2 * 2, (
                "o retangulo do sufixo comecou dentro do numero"
            )

    def test_sem_grade_nao_ha_proposta(self):
        assert sugerir_a_coluna_de_preco(_painel_sintetico(), None) == ([], [])

    def test_uma_coluna_SEM_moeda_ao_lado_nao_e_proposta(self):
        """A coluna `5 mln increment` tem numeros e nenhuma palavra ao lado."""
        pixels = _painel_sintetico()
        for indice in range(LINHAS):
            y = TOPO_DA_GRADE + indice * PASSO + 18
            _escrever(pixels, y, 1572, (4, 4, 4), 255)
        grade = medir_a_grade(pixels, (*ORIGEM, *TAMANHO_DO_TITULO))

        assert sugerir_a_coluna_de_preco(pixels, grade) == ([], [])


# ==========================================================================
# A LEITURA PROPOSTA
# ==========================================================================


def _molde(padrao: str) -> np.ndarray:
    """Um glifo 9x4 desenhado a partir de um texto de 9 linhas."""
    linhas = padrao.split("|")
    saida = np.zeros((len(linhas), 4), dtype=np.uint8)
    for y, linha in enumerate(linhas):
        for x, c in enumerate(linha):
            saida[y, x] = 255 if c == "#" else 0
    return saida


TRES = "####|#..#|...#|.###|...#|...#|#..#|####|...."
SETE = "####|...#|...#|..#.|..#.|.#..|.#..|.#..|...."


class TestAPropostaDeLeitura:
    def test_sem_moldes_nao_arrisca(self):
        assert propor_rotulo(np.zeros((9, 9), np.uint8), (0, 9), [(0, 4)], {}) is None

    def test_propoe_quando_o_glifo_e_o_MESMO_desenho(self):
        mascara = np.zeros((9, 9), dtype=np.uint8)
        mascara[:, 0:4] = _molde(TRES)
        moldes = {"3": _molde(TRES), "7": _molde(SETE)}

        assert propor_rotulo(mascara, (0, 9), [(0, 4)], moldes) == "3"

    def test_uma_MARGEM_curta_derruba_a_proposta_inteira(self):
        """Tudo ou nada: `6?,00` convidaria ao ENTER distraido no `?`."""
        mascara = np.zeros((9, 9), dtype=np.uint8)
        mascara[:, 0:4] = _molde(TRES)
        # dois rotulos com o MESMO desenho: o melhor e o segundo empatam
        moldes = {"3": _molde(TRES), "8": _molde(TRES)}

        assert propor_rotulo(mascara, (0, 9), [(0, 4)], moldes) is None

    def test_as_palavras_de_sufixo_ficam_FORA_do_conjunto_de_leitura(self):
        """Um digito nunca e candidato a casar com `XM Coin` (colunas diferentes)."""
        mascara = np.zeros((9, 9), dtype=np.uint8)
        mascara[:, 0:4] = _molde(TRES)
        moldes = {"XM Coin": np.full((8, 35), 255, dtype=np.uint8)}

        assert propor_rotulo(mascara, (0, 9), [(0, 4)], moldes) is None

    def test_a_margem_declarada_e_a_que_o_codigo_usa(self):
        fonte = inspect.getsource(propor_rotulo)
        assert "MARGEM_MINIMA_PARA_PROPOR" in fonte
        assert 0 < MARGEM_MINIMA_PARA_PROPOR < 1


class TestOPedidoDeRotuloComProposta:
    def test_ENTER_vazio_confirma_a_proposta(self):
        assert _pedir_rotulo(lambda _p: "", 5, "62,00") == "62,00"

    def test_o_que_o_usuario_DIGITA_sempre_vence(self):
        assert _pedir_rotulo(lambda _p: "63,00", 5, "62,00") == "63,00"

    def test_SEM_proposta_o_ENTER_vazio_continua_sendo_RECUSA(self):
        """Silencio nao vira concordancia quando nao ha com o que concordar."""
        assert _pedir_rotulo(lambda _p: "", 5) is None

    def test_a_conferencia_de_contagem_vale_TAMBEM_sobre_a_proposta(self):
        """A proposta nao tem passe livre: 4 glifos contra 5 caracteres recusa."""
        assert _pedir_rotulo(lambda _p: "", 4, "62,00") is None

    def test_a_pergunta_MOSTRA_a_proposta_para_o_usuario_ler(self):
        vistas: list[str] = []

        def ler(pergunta):
            vistas.append(pergunta)
            return ""

        _pedir_rotulo(ler, 5, "62,00")

        assert "62,00" in vistas[0]


# ==========================================================================
# O AVISO DE DIVERGENCIA — INFORMACAO, NUNCA RECUSA
# ==========================================================================


class TestOAvisoDeDivergencia:
    GRADE = GradeMedida(
        esquerda=ESQUERDA, topo=TOPO_DA_GRADE, largura=944, passo=45, linhas=10
    )

    def test_o_desenho_que_bate_com_a_medicao_nao_diz_nada(self, capsys):
        _avisar_divergencia_da_grade(
            self.GRADE, (744, 618, 944, 450), (744, 618, 944, 45)
        )

        assert capsys.readouterr().out == ""

    def test_o_cabecalho_engolido_e_denunciado_com_os_dois_numeros(self, capsys):
        """Exatamente o erro de campo: uma linha inteira a mais na area."""
        _avisar_divergencia_da_grade(
            self.GRADE, (744, 573, 944, 495), (744, 573, 944, 45)
        )

        saida = capsys.readouterr().out
        assert "573" in saida and "618" in saida
        assert "495" in saida and "450" in saida

    def test_o_aviso_NAO_levanta_excecao_nem_recusa(self):
        """O usuario e a autoridade; recusar o obrigaria a editar o JSON a mao."""
        assert (
            _avisar_divergencia_da_grade(
                self.GRADE, (0, 0, 10, 10), (0, 0, 10, 3)
            )
            is None
        )

    def test_sem_medicao_nao_ha_o_que_comparar(self, capsys):
        _avisar_divergencia_da_grade(None, (0, 0, 10, 10), (0, 0, 10, 3))

        assert capsys.readouterr().out == ""


# ==========================================================================
# `_selecionar_regiao`: A SUGESTAO E OPCIONAL, E A PARTY NAO MUDOU
# ==========================================================================


@pytest.fixture
def highgui_dublado(monkeypatch):
    """Toda a mecanica de janela substituida; nada abre, nada bloqueia."""
    estado = {"selectROI": 0, "imshow": [], "teclas": []}

    monkeypatch.setattr(l2scanner.calibrar, "esvaziar_a_fila_de_teclas", lambda: 0)
    monkeypatch.setattr(cv2, "namedWindow", lambda *a, **k: None)
    monkeypatch.setattr(cv2, "moveWindow", lambda *a, **k: None)
    monkeypatch.setattr(cv2, "destroyAllWindows", lambda: None)
    monkeypatch.setattr(cv2, "waitKey", lambda *a, **k: -1)
    monkeypatch.setattr(cv2, "getWindowProperty", lambda *a, **k: 1.0)
    monkeypatch.setattr(
        cv2, "imshow", lambda _t, img: estado["imshow"].append(img)
    )
    monkeypatch.setattr(
        cv2, "waitKeyEx", lambda *a, **k: estado["teclas"].pop(0)
    )

    def selectROI(_titulo, _img, showCrosshair=False):
        estado["selectROI"] += 1
        return (10, 20, 30, 40)

    monkeypatch.setattr(cv2, "selectROI", selectROI)
    return estado


PIXELS = np.zeros((400, 800, 3), dtype=np.uint8)


class TestASugestaoOpcional:
    def test_sem_sugestao_o_caminho_e_o_de_sempre(self, highgui_dublado):
        caixa = _selecionar_regiao(PIXELS, "t", "i")

        assert caixa == (10, 20, 30, 40)
        assert highgui_dublado["selectROI"] == 1

    def test_ENTER_aceita_a_sugestao_SEM_abrir_o_arrasto(self, highgui_dublado):
        highgui_dublado["teclas"] = [13]

        caixa = _selecionar_regiao(PIXELS, "t", "i", (100, 50, 60, 20))

        assert caixa == (100, 50, 60, 20)
        assert highgui_dublado["selectROI"] == 0, (
            "com a sugestao aceita, o selectROI nem devia ter sido chamado"
        )

    def test_ESC_continua_CANCELANDO_mesmo_com_sugestao_na_tela(
        self, highgui_dublado
    ):
        """A distincao que o `cv2.selectROI` nao entrega: ESC != ENTER-sem-arrasto."""
        highgui_dublado["teclas"] = [27]

        assert _selecionar_regiao(PIXELS, "t", "i", (100, 50, 60, 20)) is None

    def test_qualquer_outra_tecla_devolve_o_arrasto_ao_usuario(
        self, highgui_dublado
    ):
        highgui_dublado["teclas"] = [ord("r")]

        caixa = _selecionar_regiao(PIXELS, "t", "i", (100, 50, 60, 20))

        assert caixa == (10, 20, 30, 40)
        assert highgui_dublado["selectROI"] == 1

    def test_a_janela_fechada_no_X_cancela_em_vez_de_travar(
        self, highgui_dublado, monkeypatch
    ):
        monkeypatch.setattr(cv2, "getWindowProperty", lambda *a, **k: 0.0)
        highgui_dublado["teclas"] = [-1]

        assert _selecionar_regiao(PIXELS, "t", "i", (100, 50, 60, 20)) is None

    def test_a_sugestao_e_desenhada_na_ESCALA_da_visualizacao(
        self, highgui_dublado
    ):
        """Uma janela de 3200 px e mostrada em 1600: o retangulo tem de encolher junto."""
        largos = np.zeros((900, 3200, 3), dtype=np.uint8)
        highgui_dublado["teclas"] = [13]

        caixa = _selecionar_regiao(largos, "t", "i", (200, 100, 400, 60))

        assert caixa == (200, 100, 400, 60), "a volta tem de ser no ORIGINAL"
        desenhada = highgui_dublado["imshow"][0]
        verdes = np.argwhere(
            (desenhada[:, :, 1] == 255)
            & (desenhada[:, :, 0] == 0)
            & (desenhada[:, :, 2] == 0)
        )
        assert verdes.size, "nenhum retangulo verde foi desenhado"
        # escala 0.5 -> o retangulo cai em torno de (100, 50)..(300, 80)
        assert 45 <= verdes[:, 0].min() <= 55
        assert 95 <= verdes[:, 1].min() <= 105

    def test_o_dreno_por_tempo_continua_intacto(self):
        """Tripwire herdado: um laco com `break` aqui deixava o ENTER vazar."""
        fonte = inspect.getsource(l2scanner.calibrar._selecionar_regiao)

        assert "esvaziar_a_fila_de_teclas()" in fonte
        assert "break" not in fonte


class TestAPartyNaoMudou:
    """CR-01 acabou de devolver o 1:1 a calibracao de party. Nada aqui a toca."""

    def test_a_party_NAO_passa_sugestao_nenhuma(self, monkeypatch):
        vistos: list[tuple] = []

        def espiao(pixels, titulo, instrucao, sugestao=None):
            vistos.append((titulo, sugestao))
            return None

        monkeypatch.setattr(l2scanner.calibrar, "_selecionar_regiao", espiao)

        l2scanner.calibrar.calibrar_selecionando(PIXELS, 0, 0)

        assert vistos == [("Marque a party window", None)]

    def test_o_padrao_da_assinatura_e_None(self):
        assinatura = inspect.signature(_selecionar_regiao)

        assert assinatura.parameters["sugestao"].default is None

    def test_sem_sugestao_a_caixa_degenerada_segue_sendo_CANCELAMENTO(
        self, monkeypatch, highgui_dublado
    ):
        """Cancelar nunca vira aceitacao por omissao."""
        monkeypatch.setattr(cv2, "selectROI", lambda *a, **k: (0, 0, 0, 0))

        assert _selecionar_regiao(PIXELS, "t", "i") is None


# ==========================================================================
# OS FRAMES REAIS — pulados quando `recordings/` nao esta presente
# ==========================================================================

sem_gravacoes = pytest.mark.skipif(
    not FRAME_DA_GRADE.is_file() or not FRAME_CHEIO.is_file(),
    reason="recordings/ e gitignored e nao existe neste checkout",
)


@sem_gravacoes
class TestContraOsFramesReais:
    """Os numeros MEDIDOS a mao, agora afirmados por teste."""

    def _ancoras(self) -> list[AncoraDoPainel]:
        molde = cv2.imread(
            str(RAIZ / "tests" / "fixtures" / "mercado" / "ancora_27x_f000.png")
        )
        return [
            AncoraDoPainel(
                nome="titulo", dx=0, dy=0,
                molde=cv2.cvtColor(molde, cv2.COLOR_BGR2GRAY),
            )
        ]

    def test_a_ancora_de_titulo_casa_0999_no_frame_de_calibragem(self):
        pixels = cv2.imread(str(FRAME_DA_GRADE))

        retangulo, score, _nome = localizar_o_titulo(pixels, self._ancoras())

        assert retangulo == (1176, 362, 100, 28)
        assert score > 0.999

    def test_a_grade_medida_bate_com_o_campo(self):
        pixels = cv2.imread(str(FRAME_DA_GRADE))
        retangulo, _s, _n = localizar_o_titulo(pixels, self._ancoras())

        grade = medir_a_grade(pixels, retangulo)

        assert (grade.topo, grade.passo, grade.linhas) == (618, 45, 10)
        assert grade.esquerda == 744
        assert grade.altura == 450

    def test_dez_precos_de_cinco_glifos_no_frame_de_calibragem(self):
        pixels = cv2.imread(str(FRAME_DA_GRADE))
        retangulo, _s, _n = localizar_o_titulo(pixels, self._ancoras())
        grade = medir_a_grade(pixels, retangulo)

        numeros, sufixos = sugerir_a_coluna_de_preco(pixels, grade)

        assert len(numeros) == 10 and len(sufixos) == 10
        contagens = [
            len(segmentar_glifos(pixels[y : y + a, x : x + larg])[1])
            for (x, y, larg, a) in numeros
        ]
        assert contagens == [5] * 10

    def test_a_tooltip_derruba_so_as_linhas_que_ela_cobre(self):
        """`frame_000010` tem quatro linhas cobertas; as seis restantes saem
        com as contagens medidas 6, 4, 5, 4, 5, 4."""
        pixels = cv2.imread(str(FRAME_CHEIO))
        retangulo, _s, _n = localizar_o_titulo(pixels, self._ancoras())
        grade = medir_a_grade(pixels, retangulo)

        numeros, _sufixos = sugerir_a_coluna_de_preco(pixels, grade)

        contagens = [
            len(segmentar_glifos(pixels[y : y + a, x : x + larg])[1])
            for (x, y, larg, a) in numeros
        ]
        assert contagens == [6, 4, 5, 4, 5, 4]

    def test_a_palavra_XM_Coin_proposta_tem_texto_apagado_e_nenhum_digito(self):
        pixels = cv2.imread(str(FRAME_DA_GRADE))
        retangulo, _s, _n = localizar_o_titulo(pixels, self._ancoras())
        grade = medir_a_grade(pixels, retangulo)

        _numeros, sufixos = sugerir_a_coluna_de_preco(pixels, grade)

        for x, y, largura, altura in sufixos:
            recorte = pixels[y : y + altura, x : x + largura]
            assert not mascara_de_texto(recorte).any(), (
                "o retangulo do sufixo pegou um digito claro junto"
            )
            assert l2scanner.calibrar_mercado.recortar_sufixo(recorte) is not None
