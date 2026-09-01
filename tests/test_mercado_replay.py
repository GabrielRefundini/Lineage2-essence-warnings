"""O REPLAY DA FASE 2: de pixels de janela ate `PaginaAceita` e ate o catalogo.

DUAS METADES, e a divisao segue o desenho que `test_mercado_27x.py` ja usa.

A METADE QUE SEMPRE RODA afirma a fase inteira sobre fixturas VERSIONADAS. Ela
nao toca `recordings/` em caminho nenhum, nao precisa de WinRT e nao le o
`calibration.json` da maquina: um clone limpo a roda verde.

A METADE ATRAS DO PORTAO afirma o que so o material real prova, e comeca com o
mesmo `pytest.skip` do `test_mercado_27x.py`. Um teste que dependesse de
`recordings/` ficaria verde nesta maquina e amarelo em toda outra.

O MATERIAL, ARQUIVO POR ARQUIVO, COM O FRAME DE ORIGEM
=======================================================
Todas as janelas versionadas sao copias BIT-IDENTICAS de um frame do censo, e a
identidade esta conferida por teste abaixo (`TestAProveniencia`) — se uma
fixtura for regravada de outro frame, o teste cai em vez de mentir.

    janela_negociacao_f005.png           pagina-cheia/frame_000005.png
    janela_negociacao_f005_repetida.png  pagina-cheia/frame_000006.png
    janela_negociacao_f010.png           pagina-cheia/frame_000010.png
    janela_tooltip_f012.png              tooltip/frame_000012.png
    janela_adena_f014.png                scroll/frame_000014.png
    calibracao_de_fixture.json           copia da calibracao do usuario
    leituras_de_nome.json                as 3.511 leituras LIMPAS das 8
                                         gravacoes, com texto2x e texto3x

O OCR NAO E SIMULADO: ELE E REPRODUZIDO
========================================
As leitoras injetadas nao inventam nome. Elas devolvem EXATAMENTE o que o
Windows OCR devolveu naquele recorte, lido de `leituras_de_nome.json`, que a
varredura do 02-03 produziu contra o motor de verdade. O casamento e por
CONTEUDO do recorte (`ndarray.tobytes()`), e nao por posicao: assim uma mudanca
na geometria de recorte quebra o teste em vez de silenciosamente alinhar o nome
errado com a linha errada.

Quando dois recortes distintos tem os MESMOS pixels e textos diferentes, o mapa
guarda `""` para aquela chave — falha FECHADA. Adivinhar qual dos dois era
produziria uma serie que ninguem consegue reproduzir olhando a tela.

O QUE NAO E CONTRATO AQUI, DE PROPOSITO
========================================
No espirito do `test_mercado_glifos.py`: os valores exatos de score e de
dispersao mudam com a convencao de recorte e com a calibracao do usuario. O que
se afirma e a RELACAO ("a pagina cheia le mais linhas que a coberta") e a FAIXA,
e nunca um numero absoluto escolhido a mao. As unicas excecoes sao os totais que
o tracer do 02-04 ja prendeu por VALOR em `test_mercado_pagina.py`, e eles ficam
la, onde nasceram.

O QUE ESTA FASE NAO ESCREVE
============================
**A Fase 2 escreve o catalogo de nomes e NAO escreve observacao nenhuma.** O CSV
de observacoes e da Fase 3. Dois arquivos, dois donos — e ha teste disso.
"""

from __future__ import annotations

import copy
import inspect
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.mercado_catalogo import Catalogo
from l2scanner.mercado_pagina import LeitorDePagina, PaginaAceita
from l2scanner.mercado_visao import RastreioDoPainel, ancoras_de_calibracao

RAIZ = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "mercado"
CALIBRACAO = FIXTURES / "calibracao_de_fixture.json"
LEITURAS_DE_NOME = FIXTURES / "leituras_de_nome.json"

# A pasta do material real. Ela e usada SOMENTE pela classe do portao — ha teste
# de inspecao de fonte cobrando isso.
RECORDINGS = RAIZ / "recordings"

# A PROVENIENCIA das janelas versionadas: fixtura -> (gravacao, frame).
PROVENIENCIA = {
    "janela_negociacao_f005.png": (
        "20260828-060622-mercado-pagina-cheia",
        "frame_000005.png",
    ),
    "janela_negociacao_f005_repetida.png": (
        "20260828-060622-mercado-pagina-cheia",
        "frame_000006.png",
    ),
    "janela_negociacao_f010.png": (
        "20260828-060622-mercado-pagina-cheia",
        "frame_000010.png",
    ),
    "janela_tooltip_f012.png": (
        "20260828-061253-mercado-tooltip",
        "frame_000012.png",
    ),
    "janela_adena_f014.png": (
        "20260828-055323-mercado-scroll",
        "frame_000014.png",
    ),
}

PAGINA_CHEIA = "janela_negociacao_f005.png"
PAGINA_CHEIA_VIZINHA = "janela_negociacao_f005_repetida.png"
PAGINA_TOOLTIP = "janela_tooltip_f012.png"
PAGINA_ADENA = "janela_adena_f014.png"


# ---------------------------------------------------------------------------
# O material, e as leitoras que o reproduzem
# ---------------------------------------------------------------------------


def ler_fixtura(caminho: Path) -> np.ndarray:
    pixels = cv2.imread(str(caminho))
    assert pixels is not None, f"nao decodifiquei {caminho}"
    return pixels


@pytest.fixture(scope="module")
def cal() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO)


@pytest.fixture(scope="module")
def cal_sem_adena(cal: Calibracao) -> Calibracao:
    """A calibracao de um clone que nunca calibrou a Adena — o estado de ANTES.

    Ver a fixtura homonima em `test_mercado_pagina.py`: desde o 05-02 a Adena E
    lida, entao o exemplo de "aba nao lida" passou a ser uma aba SEM layout
    calibrado. A verdade prendida nao mudou; o exemplo mudou.
    """
    copia = copy.copy(cal)
    copia.mercado_layouts = None
    return copia


@pytest.fixture(scope="module")
def leituras() -> dict[tuple[str, str, int], tuple[str, str]]:
    """`leituras_de_nome.json` indexado por (gravacao, arquivo, linha)."""
    bruto = json.loads(LEITURAS_DE_NOME.read_text(encoding="utf-8"))
    return {
        (r["gravacao"], r["arquivo"], int(r["linha"])): (r["texto2x"], r["texto3x"])
        for r in bruto
    }


class LeitoraDeRecorte:
    """Devolve o texto que o OCR REAL leu naquele recorte, ou `""`.

    Ela e uma leitora injetada no molde de `VigiaDeManutencao.__init__`: o
    leitor de pagina nao sabe o que "escala" significa, e recebe duas maneiras
    INDEPENDENTES de ler o mesmo recorte. Aqui as duas vem do mesmo arquivo, mas
    de COLUNAS diferentes (`texto2x` e `texto3x`), que sao as duas leituras que
    o motor de verdade produziu.

    Recorte desconhecido devolve `""`, e nao levanta: uma linha coberta nunca
    chega a ser lida em producao, mas a de layout errado pode chegar por um
    caminho novo, e um `KeyError` no meio do tick seria a pior resposta.
    """

    def __init__(self) -> None:
        self._por_bytes: dict[bytes, str] = {}
        self.chamadas = 0

    def registrar(self, recorte: np.ndarray, texto: str) -> None:
        chave = recorte.tobytes()
        anterior = self._por_bytes.get(chave)
        if anterior is not None and anterior != texto:
            # DOIS recortes de pixels IDENTICOS com textos diferentes. Escolher
            # um seria inventar. Falha FECHADA: a linha nao le.
            self._por_bytes[chave] = ""
            return
        self._por_bytes[chave] = texto

    def __call__(self, recorte: np.ndarray) -> str:
        self.chamadas += 1
        return self._por_bytes.get(recorte.tobytes(), "")


def _recortes_do_nome(
    frame: np.ndarray, origem: tuple[int, int], cal: Calibracao
) -> dict[int, np.ndarray]:
    """A celula do NOME de cada linha, com a geometria da producao.

    Ela reproduz `LeitorDePagina._recortes_de_coluna` para a coluna do nome, e
    e isso que faz o casamento por bytes funcionar: os mesmos pixels, cortados
    com a mesma convencao meio-aberta.
    """
    grade = cal.mercado_grade
    coluna = cal.mercado_coluna_do_nome
    ox, oy = origem
    gy = oy + int(grade["dy"])
    altura = int(grade["altura_da_linha"])
    x = ox + int(coluna["dx"])
    largura = int(coluna["largura"])

    saida: dict[int, np.ndarray] = {}
    for indice in range(int(grade["linhas_por_pagina"])):
        topo = gy + indice * altura
        if topo < 0 or x < 0:
            continue
        if topo + altura > frame.shape[0] or x + largura > frame.shape[1]:
            continue
        saida[indice] = frame[topo : topo + altura, x : x + largura]
    return saida


def _novo_rastreio(cal: Calibracao) -> RastreioDoPainel:
    return RastreioDoPainel(
        ancoras_de_calibracao(cal.mercado_ancoras),
        float(cal.mercado_limiar_da_ancora),
    )


def alimentar(
    duas: LeitoraDeRecorte,
    tres: LeitoraDeRecorte,
    frame: np.ndarray,
    cal: Calibracao,
    gravacao: str,
    arquivo: str,
    leituras: dict,
) -> None:
    """Ensina as duas leitoras o que o OCR real leu neste frame.

    Ela roda o SEU proprio `RastreioDoPainel`, e nao o do leitor: os dois veem o
    mesmo frame com as mesmas ancoras e o mesmo limiar, entao chegam a mesma
    origem. Espiar o estado interno do leitor seria acoplar o teste ao que ele
    existe para nao saber.
    """
    rastreio = _novo_rastreio(cal)
    voto = rastreio.observar(frame)
    if not voto.aberto or rastreio.origem is None:
        return
    for indice, recorte in _recortes_do_nome(frame, rastreio.origem, cal).items():
        par = leituras.get((gravacao, arquivo, indice))
        if par is None:
            # Linha que a varredura do 02-03 nao pos na populacao limpa: coberta,
            # vazia ou de meia-leitura. Em producao ela nao chega ao OCR; aqui
            # ela fica sem texto, que e o mesmo efeito.
            continue
        duas.registrar(recorte, par[0])
        tres.registrar(recorte, par[1])


def montar(cal: Calibracao) -> tuple[LeitorDePagina, LeitoraDeRecorte, LeitoraDeRecorte, dict]:
    duas, tres = LeitoraDeRecorte(), LeitoraDeRecorte()
    catalogo_em_memoria: dict = {}
    leitor = LeitorDePagina(
        _novo_rastreio(cal), catalogo_em_memoria, duas, tres, cal
    )
    return leitor, duas, tres, catalogo_em_memoria


def replay_de_uma_janela(
    cal: Calibracao,
    leituras: dict,
    fixturas: list[str],
) -> tuple[LeitorDePagina, list[PaginaAceita | None]]:
    """Passa as fixturas nomeadas por um unico `LeitorDePagina`, em ordem."""
    leitor, duas, tres, _catalogo = montar(cal)
    aceitas: list[PaginaAceita | None] = []
    for nome in fixturas:
        frame = ler_fixtura(FIXTURES / nome)
        gravacao, arquivo = PROVENIENCIA[nome]
        alimentar(duas, tres, frame, cal, gravacao, arquivo, leituras)
        aceitas.append(leitor.observar(frame))
    return leitor, aceitas


# ===========================================================================
# METADE 1 — A FASE INTEIRA, SOBRE FIXTURA VERSIONADA (sempre roda)
# ===========================================================================


class TestAProveniencia:
    """Cada janela versionada E o frame do censo que o cabecalho declara.

    Sem isto o cabecalho seria prosa: alguem regravaria uma fixtura de outro
    frame e o mapa de leituras de OCR passaria a alinhar o nome errado com a
    linha errada, calado.
    """

    @pytest.mark.parametrize("fixtura", sorted(PROVENIENCIA))
    def test_a_janela_versionada_existe_e_decodifica(self, fixtura) -> None:
        assert ler_fixtura(FIXTURES / fixtura).ndim == 3

    @pytest.mark.parametrize("fixtura", sorted(PROVENIENCIA))
    def test_a_gravacao_de_origem_esta_no_CENSO(self, fixtura) -> None:
        """Ela nao pode vir de uma pasta fora das 8 medidas."""
        sys.path.insert(0, str(RAIZ / "tools"))
        try:
            import medir_oclusao
        finally:
            sys.path.pop(0)
        gravacao, _arquivo = PROVENIENCIA[fixtura]
        assert gravacao in medir_oclusao.GRAVACOES_DO_CENSO


class TestOOCRReproduzidoEHONESTO:
    """As leitoras devolvem o que o motor real leu — nao um nome inventado."""

    def test_as_leituras_da_pagina_cheia_existem_no_arquivo(
        self, leituras
    ) -> None:
        gravacao, arquivo = PROVENIENCIA[PAGINA_CHEIA]
        presentes = [i for i in range(10) if (gravacao, arquivo, i) in leituras]
        assert len(presentes) == 10, (
            "a pagina cheia deixou de ter as 10 linhas limpas no censo; o "
            "material mudou de forma"
        )

    def test_um_recorte_DESCONHECIDO_devolve_vazio_e_nao_levanta(self) -> None:
        leitora = LeitoraDeRecorte()
        assert leitora(np.zeros((4, 4, 3), dtype=np.uint8)) == ""

    def test_pixels_IGUAIS_com_textos_DIFERENTES_falham_FECHADO(self) -> None:
        """Adivinhar produziria uma serie que ninguem reproduz olhando a tela."""
        leitora = LeitoraDeRecorte()
        recorte = np.zeros((4, 4, 3), dtype=np.uint8)
        leitora.registrar(recorte, "Adena")
        leitora.registrar(recorte.copy(), "Outra Coisa")
        assert leitora(recorte) == ""


class TestAPaginaCHEIA:
    """A pagina de 10 linhas atravessa ate `PaginaAceita`."""

    def test_dois_frames_da_MESMA_pagina_produzem_pagina_aceita(
        self, cal, leituras
    ) -> None:
        leitor, aceitas = replay_de_uma_janela(
            cal, leituras, [PAGINA_CHEIA, PAGINA_CHEIA_VIZINHA]
        )
        assert aceitas[0] is None, "um frame sozinho NUNCA vira pagina aceita"
        assert isinstance(aceitas[1], PaginaAceita)
        assert leitor.paginas_lidas == 1

    def test_as_DEZ_linhas_saem_com_nome_agrupado_e_numeros_lidos(
        self, cal, leituras
    ) -> None:
        _leitor, aceitas = replay_de_uma_janela(
            cal, leituras, [PAGINA_CHEIA, PAGINA_CHEIA_VIZINHA]
        )
        pagina = aceitas[1]
        assert len(pagina.linhas) == int(cal.mercado_grade["linhas_por_pagina"])
        for linha in pagina.linhas:
            assert linha.chave_da_serie
            assert isinstance(linha.total_em_centesimos, int)
            assert isinstance(linha.quantidade, int)
            assert linha.total_em_centesimos > 0
            assert linha.quantidade > 0

    def test_as_linhas_saem_na_ORDEM_da_grade_de_cima_para_baixo(
        self, cal, leituras
    ) -> None:
        """A ordem e CONTRATO: a Fase 3 grava uma observacao por linha, e ela e
        o unico vinculo com o que o usuario viu na tela."""
        _leitor, aceitas = replay_de_uma_janela(
            cal, leituras, [PAGINA_CHEIA, PAGINA_CHEIA_VIZINHA]
        )
        indices = [linha.indice for linha in aceitas[1].linhas]
        assert indices == sorted(indices)
        assert len(set(indices)) == len(indices)

    def test_o_par_de_frames_e_de_ARQUIVOS_DIFERENTES(self) -> None:
        """Um par degenerado (o mesmo array duas vezes) nao provaria acordo.

        Ele tambem cairia no detector de congelamento na terceira repeticao,
        que e outro jeito de dizer a mesma coisa.
        """
        a = ler_fixtura(FIXTURES / PAGINA_CHEIA)
        b = ler_fixtura(FIXTURES / PAGINA_CHEIA_VIZINHA)
        assert not np.array_equal(a, b)


class TestAPaginaCOBERTA_PELA_TOOLTIP:
    """A recusa e por LINHA, nunca por pagina (D-14)."""

    def test_a_contagem_de_descartadas_bate_com_as_linhas_cobertas(
        self, cal, leituras
    ) -> None:
        leitor, _aceitas = replay_de_uma_janela(cal, leituras, [PAGINA_TOOLTIP])
        leitura = leitor.ultima_leitura
        assert leitura is not None
        assert len(leitura.descartadas) + len(leitura.linhas) == int(
            cal.mercado_grade["linhas_por_pagina"]
        )
        assert len(leitura.descartadas) > 0, "a tooltip nao cobriu nada"

    def test_as_DESCOBERTAS_sao_lidas_e_as_cobertas_nao(
        self, cal, leituras
    ) -> None:
        leitor, _aceitas = replay_de_uma_janela(cal, leituras, [PAGINA_TOOLTIP])
        leitura = leitor.ultima_leitura
        lidas = {linha.indice for linha in leitura.linhas}
        assert lidas, "nenhuma linha descoberta atravessou"
        assert not (lidas & set(leitura.descartadas))

    def test_a_pagina_QUASE_TODA_COBERTA_nao_e_aceita_pelo_piso(
        self, cal, leituras
    ) -> None:
        """T-02-26 com o piso de PRODUCAO: 2 linhas de 10 nao fazem pagina.

        Duas leituras dela concordariam TRIVIALMENTE nas poucas posicoes que
        sobraram — e essa e exatamente a "pagina praticamente nao lida" que o
        piso existe para recusar.
        """
        leitor, aceitas = replay_de_uma_janela(
            cal, leituras, [PAGINA_TOOLTIP, PAGINA_TOOLTIP]
        )
        assert aceitas == [None, None]
        assert leitor.paginas_perdidas >= 1
        assert "minimo" in leitor.ultimo_motivo_de_perda.lower()

    def test_a_pagina_coberta_le_MENOS_que_a_cheia(self, cal, leituras) -> None:
        """A RELACAO, e nao o numero absoluto — que muda com a calibracao."""
        coberta, _a = replay_de_uma_janela(cal, leituras, [PAGINA_TOOLTIP])
        cheia, _b = replay_de_uma_janela(cal, leituras, [PAGINA_CHEIA])
        assert len(coberta.ultima_leitura.linhas) < len(
            cheia.ultima_leitura.linhas
        )


class TestOPortaoDeLayoutNoReplay:
    """Uma aba NAO CALIBRADA e RECUSADA: zero linhas, zero chamadas de OCR."""

    def test_uma_aba_nao_calibrada_nao_produz_linha_nem_chamada_de_OCR(
        self, cal_sem_adena, leituras
    ) -> None:
        leitor, duas, tres, _cat = montar(cal_sem_adena)
        frame = ler_fixtura(FIXTURES / PAGINA_ADENA)
        gravacao, arquivo = PROVENIENCIA[PAGINA_ADENA]
        alimentar(duas, tres, frame, cal_sem_adena, gravacao, arquivo, leituras)
        assert leitor.observar(frame) is None
        assert leitor.ultima_leitura is None
        assert duas.chamadas == tres.chamadas == 0
        assert leitor.paginas_de_outro_layout == 1

    def test_COM_a_adena_calibrada_a_MESMA_janela_e_lida_SEM_OCR(
        self, cal, leituras
    ) -> None:
        """O CONTROLE NEGATIVO do teste acima, e o discriminante da fase.

        A MESMA janela, o MESMO leitor, so a chave `mercado_layouts` a mais: ela
        deixa de ser recusada e passa a ser lida. E as chamadas de OCR seguem em
        ZERO — a identidade da Adena vem da sentinela de serie, nao de texto.
        """
        leitor, duas, tres, _cat = montar(cal)
        frame = ler_fixtura(FIXTURES / PAGINA_ADENA)
        gravacao, arquivo = PROVENIENCIA[PAGINA_ADENA]
        alimentar(duas, tres, frame, cal, gravacao, arquivo, leituras)
        leitor.observar(frame)
        assert leitor.ultima_leitura is not None
        assert leitor.paginas_de_outro_layout == 0
        assert duas.chamadas == tres.chamadas == 0

    def test_um_frame_de_layout_NAO_CALIBRADO_no_meio_nao_contamina_o_acordo(
        self, cal_sem_adena, leituras
    ) -> None:
        """Ele apaga a memoria do frame anterior, e com razao: comparar a pagina
        de antes com a de depois de o layout mudar afirmaria estabilidade sobre
        uma descontinuidade."""
        _leitor, aceitas = replay_de_uma_janela(
            cal_sem_adena,
            leituras,
            [PAGINA_CHEIA, PAGINA_ADENA, PAGINA_CHEIA_VIZINHA],
        )
        assert aceitas == [None, None, None]


class TestOCatalogoNoReplay:
    """A idempotencia: a segunda passada nao cria serie nova."""

    def _passada(self, cal, leituras, catalogo: Catalogo) -> PaginaAceita:
        from datetime import datetime

        leitor = LeitorDePagina(
            _novo_rastreio(cal),
            catalogo.entradas(),
            *self._leitoras(cal, leituras),
            cal,
        )
        pagina = None
        for nome in (PAGINA_CHEIA, PAGINA_CHEIA_VIZINHA):
            pagina = leitor.observar(ler_fixtura(FIXTURES / nome))
        assert pagina is not None
        for linha in pagina.linhas:
            catalogo.registrar(
                linha.chave_da_serie,
                linha.nome_exibido,
                datetime(2026, 8, 30, 21, 0, 0),
            )
        return pagina

    def _leitoras(self, cal, leituras):
        duas, tres = LeitoraDeRecorte(), LeitoraDeRecorte()
        for nome in (PAGINA_CHEIA, PAGINA_CHEIA_VIZINHA):
            gravacao, arquivo = PROVENIENCIA[nome]
            alimentar(
                duas,
                tres,
                ler_fixtura(FIXTURES / nome),
                cal,
                gravacao,
                arquivo,
                leituras,
            )
        return duas, tres

    def test_a_PRIMEIRA_passada_cria_as_series(
        self, cal, leituras, tmp_path
    ) -> None:
        catalogo = Catalogo(tmp_path / ".mercado")
        pagina = self._passada(cal, leituras, catalogo)
        assert len(catalogo.series) == len(
            {linha.chave_da_serie for linha in pagina.linhas}
        )

    def test_a_SEGUNDA_passada_nao_cria_serie_nova(
        self, cal, leituras, tmp_path
    ) -> None:
        """A idempotencia e o que impede o catalogo de inchar a cada sessao."""
        catalogo = Catalogo(tmp_path / ".mercado")
        self._passada(cal, leituras, catalogo)
        depois_da_primeira = set(catalogo.series)
        catalogo.gravar()

        recarregado = Catalogo(tmp_path / ".mercado")
        self._passada(cal, leituras, recarregado)
        assert set(recarregado.series) == depois_da_primeira

    def test_a_segunda_passada_SOBE_a_contagem_de_avistamentos(
        self, cal, leituras, tmp_path
    ) -> None:
        catalogo = Catalogo(tmp_path / ".mercado")
        self._passada(cal, leituras, catalogo)
        antes = {c: s.avistamentos for c, s in catalogo.series.items()}
        self._passada(cal, leituras, catalogo)
        assert all(catalogo.series[c].avistamentos > v for c, v in antes.items())

    def test_o_catalogo_sobrevive_a_ida_e_volta_pelo_DISCO(
        self, cal, leituras, tmp_path
    ) -> None:
        catalogo = Catalogo(tmp_path / ".mercado")
        self._passada(cal, leituras, catalogo)
        catalogo.gravar()
        assert Catalogo(tmp_path / ".mercado").series == catalogo.series


class TestAFronteiraComAFase3:
    """A Fase 2 escreve o catalogo de nomes e NADA MAIS."""

    def test_a_passada_escreve_SO_o_catalogo_na_pasta(
        self, cal, leituras, tmp_path
    ) -> None:
        pasta = tmp_path / ".mercado"
        catalogo = Catalogo(pasta)
        TestOCatalogoNoReplay()._passada(cal, leituras, catalogo)
        catalogo.gravar()
        assert [c.name for c in pasta.iterdir()] == ["catalogo-de-nomes.csv"]

    def test_nenhum_modulo_desta_fase_nomeia_o_CSV_de_observacoes(self) -> None:
        import l2scanner.mercado_catalogo as catalogo
        import l2scanner.mercado_leitura as leitura
        import l2scanner.mercado_pagina as pagina

        for modulo in (catalogo, leitura, pagina):
            fonte = inspect.getsource(modulo).lower()
            assert "observacoes.csv" not in fonte, modulo.__name__


class TestOCharterDesteArquivo:
    """A metade que sempre roda nao pode depender de `recordings/`."""

    def test_so_a_metade_do_PORTAO_USA_a_constante_da_pasta(self) -> None:
        """Pela ARVORE de sintaxe, e nao por grep sobre o texto.

        Se a metade versionada passasse a usar a pasta do material real, ela
        ficaria verde nesta maquina e amarela em toda outra — e a suite
        deixaria de ser o detector de regressao que ela existe para ser.

        A afirmacao e sobre USO, e nao sobre mencao: este arquivo NOMEIA a
        constante em prosa varias vezes de proposito, e um grep sobre o texto se
        auto-invalidaria — o mesmo motivo pelo qual o teste do `rapidfuzz` em
        `test_mercado_catalogo.py` olha o grafo de import e nao o fonte.
        """
        import ast

        arquivo = Path(__file__)
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))

        # A fronteira e a PRIMEIRA definicao da metade do portao. Tudo acima
        # dela e a metade que roda num clone limpo.
        inicio_do_portao = min(
            no.lineno
            for no in ast.walk(arvore)
            if isinstance(no, ast.Name)
            and no.id == "RAZAO_DO_PORTAO"
            and isinstance(no.ctx, ast.Store)
        )
        # SO contexto de LEITURA: a linha que DEFINE `RECORDINGS` mora no topo
        # do arquivo por necessidade (o modulo tem de nomea-la em algum lugar),
        # e defini-la nao e usa-la.
        usos = sorted(
            no.lineno
            for no in ast.walk(arvore)
            if isinstance(no, ast.Name)
            and no.id == "RECORDINGS"
            and isinstance(no.ctx, ast.Load)
        )
        antes_do_portao = [
            linha for linha in usos if linha < inicio_do_portao
        ]
        assert antes_do_portao == [], (
            "a metade versionada passou a USAR a pasta do material real nas "
            f"linhas {antes_do_portao}"
        )
        assert usos, "ninguem mais usa a pasta do material real"

    def test_a_metade_versionada_nao_precisa_de_WinRT(self) -> None:
        """As leitoras sao injetadas; nada aqui importa `l2scanner.ocr`."""
        fonte = inspect.getsource(sys.modules[__name__])
        linhas_de_import = [
            linha
            for linha in fonte.splitlines()
            if linha.startswith(("import ", "from "))
        ]
        assert not any("ocr" in linha for linha in linhas_de_import)


# ===========================================================================
# METADE 2 — O MATERIAL REAL, ATRAS DO PORTAO
# ===========================================================================

RAZAO_DO_PORTAO = (
    "recordings/ e gitignored e nao se materializa num worktree nem num clone "
    "limpo, entao um teste que dependesse dela ficaria verde nesta maquina e "
    "amarelo em toda outra. A metade acima afirma a fase inteira sobre as "
    "fixturas VERSIONADAS, que sao copias bit-identicas de frames destas "
    "mesmas gravacoes."
)


def _familia_do_motivo(motivo: str) -> str:
    """A familia de uma perda, para a contagem do relatorio.

    Ela olha o INICIO da frase e nao a frase inteira, porque o motivo carrega
    numeros (quantas posicoes, qual o piso) que sao forense e nao categoria.
    """
    if motivo.startswith("primeiro frame"):
        return "primeiro frame do par"
    if motivo.startswith("so "):
        return "abaixo do minimo comparado"
    if "DISCORDAM" in motivo:
        return "os dois frames discordam"
    return "outro"


def gravacoes_do_censo() -> tuple[str, ...]:
    """As 8 gravacoes NOMEADAS, importadas das ferramentas de medicao.

    NUNCA um glob sobre `recordings/`: a pasta tem 16 subdiretorios, e um glob
    arrastaria as 8 que estao FORA do censo — incluindo a `pre-voo`, que e
    anterior ao spike, de outro dia, e sozinha tem 1.502 PNGs. Redigitar a lista
    aqui criaria uma segunda verdade sobre o mesmo conjunto.
    """
    sys.path.insert(0, str(RAIZ / "tools"))
    try:
        import medir_oclusao
    finally:
        sys.path.pop(0)
    return medir_oclusao.GRAVACOES_DO_CENSO


@pytest.fixture(scope="module")
def censo(cal, leituras):
    """Uma passada UNICA pelas 8 gravacoes, com um leitor por gravacao.

    Um leitor POR GRAVACAO, e nao um so para todas: duas gravacoes seguidas
    nao sao ticks vizinhos de uma sessao, e carregar a memoria de frame de
    uma para a outra afirmaria continuidade onde ha um corte.
    """
    nomes = gravacoes_do_censo()
    faltando = [n for n in nomes if not (RECORDINGS / n).is_dir()]
    if faltando:
        pytest.skip(RAZAO_DO_PORTAO)

    por_gravacao: dict[str, dict] = {}
    for nome in nomes:
        leitor, duas, tres, _cat = montar(cal)
        series_aceitas: set[str] = set()
        indices_descartados = 0
        linhas_de_pagina_aceita: list = []
        leituras_por_tick: list = []

        motivos_de_perda: list[str] = []
        perdidas_antes = 0

        arquivos = sorted(
            p for p in (RECORDINGS / nome).glob("frame_*.png") if p.is_file()
        )
        for caminho in arquivos:
            frame = cv2.imread(str(caminho))
            if frame is None:
                continue
            alimentar(duas, tres, frame, cal, nome, caminho.name, leituras)
            pagina = leitor.observar(frame)
            if leitor.paginas_perdidas > perdidas_antes:
                # Uma perda NESTE tick: o motivo corrente e o dela.
                motivos_de_perda.append(leitor.ultimo_motivo_de_perda)
                perdidas_antes = leitor.paginas_perdidas
            leituras_por_tick.append(leitor.ultima_leitura)
            if leitor.ultima_leitura is not None:
                indices_descartados += len(leitor.ultima_leitura.descartadas)
            if pagina is not None:
                linhas_de_pagina_aceita.extend(pagina.linhas)
                series_aceitas.update(
                    linha.chave_da_serie for linha in pagina.linhas
                )

        por_gravacao[nome] = {
            "leitor": leitor,
            "frames": len(arquivos),
            "series": series_aceitas,
            "descartados": indices_descartados,
            "linhas": linhas_de_pagina_aceita,
            "por_tick": leituras_por_tick,
            "motivos": motivos_de_perda,
        }
    return por_gravacao


class TestOReplayCOMPLETO:
    """As 8 gravacoes do censo — so onde `recordings/` existe."""

    def test_o_replay_completo_nao_e_afirmavel_num_clone_limpo(self) -> None:
        faltando = [
            n for n in gravacoes_do_censo() if not (RECORDINGS / n).is_dir()
        ]
        if faltando:
            pytest.skip(RAZAO_DO_PORTAO)
        assert len(gravacoes_do_censo()) == 8

    def test_a_lista_e_NOMEADA_e_nao_um_glob(self) -> None:
        """A `pre-voo` sozinha tem 1.502 PNGs e dominaria qualquer contagem."""
        nomes = gravacoes_do_censo()
        assert len(nomes) == 8
        assert not any("pre-voo" in n for n in nomes)

    def test_a_soma_dos_baldes_cobre_TODO_tick_com_painel_aberto(
        self, censo
    ) -> None:
        """A identidade que faz a contagem ser afirmavel, e nao so plausivel."""
        for nome, dados in censo.items():
            leitor = dados["leitor"]
            assert leitor.ticks_com_painel_aberto == (
                leitor.paginas_de_outro_layout
                + leitor.paginas_vazias
                + leitor.paginas_perdidas
                + leitor.paginas_lidas
            ), nome

    def test_nenhum_frame_de_layout_NAO_CALIBRADO_produz_linha_lida(
        self, censo
    ) -> None:
        """O portao de layout roda ANTES de fatiar a grade.

        Quando ele recusa, `ultima_leitura` e `None`: nem leitura, nem descarte,
        nem linha vazia. A grade nem chegou a ser fatiada — que e o ponto,
        porque fatiar uma geometria que nao vale ja e o erro.
        """
        recusadas = sum(
            dados["leitor"].paginas_de_outro_layout for dados in censo.values()
        )
        assert recusadas > 0, (
            "o censo deixou de conter frame de outro layout; sem ele esta "
            "afirmacao nao esta afirmando nada"
        )
        for nome, dados in censo.items():
            leitor = dados["leitor"]
            lidas_ou_perdidas = leitor.paginas_lidas + leitor.paginas_perdidas
            assert lidas_ou_perdidas + leitor.paginas_vazias == (
                leitor.ticks_com_painel_aberto - leitor.paginas_de_outro_layout
            ), nome

    def test_nenhuma_serie_nasce_de_uma_linha_que_a_SONDA_recusou(
        self, censo
    ) -> None:
        """Toda serie do catalogo veio de uma `LinhaLida` de pagina ACEITA.

        A linha que a sonda de oclusao recusou vira `Descarte`, e `Descarte` nao
        tem chave de serie — ela nunca chega ao catalogo por construcao. Este
        teste cobra isso sobre o material inteiro, e nao sobre um frame.
        """
        for nome, dados in censo.items():
            das_linhas = {
                linha.chave_da_serie for linha in dados["linhas"]
            }
            assert dados["series"] == das_linhas, nome
            assert all(chave for chave in dados["series"]), nome

    def test_a_pagina_ACEITA_nunca_contem_um_indice_descartado(
        self, censo
    ) -> None:
        for nome, dados in censo.items():
            for leitura in dados["por_tick"]:
                if leitura is None:
                    continue
                lidas = {linha.indice for linha in leitura.linhas}
                assert not (lidas & set(leitura.descartadas)), nome

    def test_as_gravacoes_com_OCLUSAO_deliberada_DESCARTAM(self, censo) -> None:
        """A sonda faz trabalho nas duas gravacoes de oclusao deliberada."""
        for nome in (
            "20260828-061253-mercado-tooltip",
            "20260828-061409-mercado-alvo-sobreposto",
        ):
            assert censo[nome]["descartados"] > 0, nome


    def test_o_replay_do_censo_LE_alguma_coisa(self, censo) -> None:
        """O criterio de sucesso da fase, na forma mais crua: ela le.

        Um replay que nao lesse nada satisfaria todas as identidades acima por
        vacuidade.
        """
        total_lidas = sum(d["leitor"].paginas_lidas for d in censo.values())
        total_series = len(set().union(*(d["series"] for d in censo.values())))
        assert total_lidas > 0
        assert total_series > 0

    def test_a_CADA_perda_corresponde_um_MOTIVO_nao_vazio(self, censo) -> None:
        """'Perdi 189' sem motivo e indistinguivel de um bug.

        Este teste e o que impede o contador de virar um numero sem historia:
        toda perda registrada tem uma frase que diz por que, e a frase e o que
        o console da Fase 4 e o log vao carregar.
        """
        for nome, dados in censo.items():
            assert len(dados["motivos"]) == dados["leitor"].paginas_perdidas, nome
            assert all(motivo for motivo in dados["motivos"]), nome

    def test_RELATORIO_do_censo(self, censo, capsys) -> None:
        """Nao e afirmacao: e a EVIDENCIA que vai para o SUMMARY.

        Ele afirma so o que nao pode deixar de ser verdade (as duas metades
        somam), e imprime o resto. Os numeros por gravacao mudam com a
        calibracao do usuario, e prende-los aqui por valor seria transformar
        medicao em contrato.
        """
        with capsys.disabled():
            print()
            print("=" * 78)
            print("REPLAY COMPLETO DO CENSO — as 8 gravacoes NOMEADAS")
            print("=" * 78)
            cabecalho = (
                f"{'gravacao':38} {'frames':>6} {'abert':>6} {'lidas':>6} "
                f"{'perd':>6} {'cong':>5} {'vaz':>4} {'lay':>4} "
                f"{'desc':>6} {'series':>7}"
            )
            print(cabecalho)
            print("-" * len(cabecalho))
            totais = dict(
                frames=0,
                abertos=0,
                lidas=0,
                perdidas=0,
                congelados=0,
                vazias=0,
                layout=0,
                descartadas=0,
            )
            todas_as_series: set[str] = set()
            for nome in gravacoes_do_censo():
                dados = censo[nome]
                leitor = dados["leitor"]
                print(
                    f"{nome[9:]:38} {dados['frames']:>6} "
                    f"{leitor.ticks_com_painel_aberto:>6} "
                    f"{leitor.paginas_lidas:>6} {leitor.paginas_perdidas:>6} "
                    f"{leitor.frames_congelados:>5} {leitor.paginas_vazias:>4} "
                    f"{leitor.paginas_de_outro_layout:>4} "
                    f"{leitor.linhas_descartadas:>6} {len(dados['series']):>7}"
                )
                totais["frames"] += dados["frames"]
                totais["abertos"] += leitor.ticks_com_painel_aberto
                totais["lidas"] += leitor.paginas_lidas
                totais["perdidas"] += leitor.paginas_perdidas
                totais["congelados"] += leitor.frames_congelados
                totais["vazias"] += leitor.paginas_vazias
                totais["layout"] += leitor.paginas_de_outro_layout
                totais["descartadas"] += leitor.linhas_descartadas
                todas_as_series |= dados["series"]
            print("-" * len(cabecalho))
            print(
                f"{'TOTAL':38} {totais['frames']:>6} {totais['abertos']:>6} "
                f"{totais['lidas']:>6} {totais['perdidas']:>6} "
                f"{totais['congelados']:>5} {totais['vazias']:>4} "
                f"{totais['layout']:>4} {totais['descartadas']:>6} "
                f"{len(todas_as_series):>7}"
            )
            print()
            print(
                f"AS DUAS METADES: li {totais['lidas']}, "
                f"perdi {totais['perdidas']}."
            )
            print(f"Series distintas no catalogo: {len(todas_as_series)}")

            print()
            print("POR QUE PERDI, agrupado pelo INICIO do motivo:")
            baldes: dict[str, int] = {}
            for dados in censo.values():
                for motivo in dados["motivos"]:
                    baldes[_familia_do_motivo(motivo)] = (
                        baldes.get(_familia_do_motivo(motivo), 0) + 1
                    )
            for familia, quantas in sorted(baldes.items(), key=lambda p: -p[1]):
                print(f"  {familia:32} {quantas:>5}")

            print()
            print("DESCARTES DE LINHA por frame, do maior para o menor:")
            for nome, dados in sorted(
                censo.items(),
                key=lambda par: -par[1]["descartados"] / max(par[1]["frames"], 1),
            ):
                print(
                    f"  {nome[9:]:38} "
                    f"{dados['descartados'] / max(dados['frames'], 1):6.2f}"
                    f"   ({dados['descartados']} em {dados['frames']})"
                )
            print("=" * 78)

        assert totais["abertos"] == (
            totais["lidas"]
            + totais["perdidas"]
            + totais["vazias"]
            + totais["layout"]
        )
