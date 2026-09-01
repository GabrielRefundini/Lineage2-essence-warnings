"""A aba Adena de pixels a pagina: a chave opcional, o portao que ESCOLHE e as
nove linhas de taxa.

O que esta suite prende, em uma frase por bloco:

- `mercado_layouts` entra OPCIONAL. Um `calibration.json` sem ela carrega
  inteiro, `VERSAO_DO_ESQUEMA` segue em 2, e a lista das QUINZE pecas de
  calibracao de mercado NAO cresce — quem nunca calibrou a Adena continua com o
  `--mercado` subindo.
- A MATRIZ DE CASAMENTO, medida nos DOIS sentidos sobre as quatro bandas
  versionadas. Os oito numeros estao na docstring de
  `LeitorDePagina._casamento_do_layout` e sao reafirmados aqui contra os pixels,
  para a tabela nao envelhecer em silencio (o padrao que o 05-01 estabeleceu com
  `TestAFixturaDaAdenaLeOQueODocstringDiz`).
- O portao ESCOLHE em vez de so recusar, e EMPATE NAO E VEREDITO.
- A pagina da Adena lida ponta a ponta, e a negociacao PROVADA identica com e
  sem a chave nova.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import Calibracao, CalibracaoInvalida
from l2scanner.mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA
from l2scanner.mercado_leitura import casamento_do_cabecalho
from l2scanner.mercado_pagina import (
    LAYOUTS_COM_LEITORA,
    LEITORAS_DE_LINHA_POR_LAYOUT,
    LeitorDePagina,
    modelo_de_layout,
    pecas_de_calibracao_de_mercado_faltando,
)
from l2scanner.mercado_visao import (
    RastreioDoPainel,
    ancoras_de_calibracao,
    cabecalho_de_calibracao,
)

FIXTURAS = Path(__file__).parent / "fixtures" / "mercado"


# --------------------------------------------------------------------------
# Ferramenta comum
# --------------------------------------------------------------------------


def _dados_da_fixtura() -> dict:
    return json.loads(
        (FIXTURAS / "calibracao_de_fixture.json").read_text(encoding="utf-8")
    )


def _calibracao_da_fixtura() -> Calibracao:
    return Calibracao.carregar(FIXTURAS / "calibracao_de_fixture.json")


def _imagem(nome: str) -> np.ndarray:
    caminho = FIXTURAS / nome
    if not caminho.exists():
        pytest.skip(f"fixtura ausente: {nome}")
    return cv2.imread(str(caminho), cv2.IMREAD_COLOR)


def _gravar(tmp_path: Path, dados: dict) -> Path:
    caminho = tmp_path / "calibration.json"
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return caminho


class _ContadoraDeOCR:
    """As duas leitoras chegam por INJECAO, e por isso da para conta-las.

    Na Adena isto e mais que conveniencia: `ler_linha_de_adena` NAO le nome, e
    "zero chamadas" e como se prova que nenhuma delas foi acionada.
    """

    def __init__(self) -> None:
        self.chamadas = 0

    def __call__(self, _pixels) -> str:
        self.chamadas += 1
        return "Common Fafurion Doll"


def _montar_leitor(cal):
    barata, conferencia = _ContadoraDeOCR(), _ContadoraDeOCR()
    leitor = LeitorDePagina(
        RastreioDoPainel(
            ancoras_de_calibracao(cal.mercado_ancoras),
            float(cal.mercado_limiar_da_ancora),
        ),
        {},
        barata,
        conferencia,
        cal,
    )
    return leitor, barata, conferencia


def _origem_do_painel(leitor, janela: np.ndarray) -> tuple[int, int]:
    """Onde o painel esta NESTA janela, pelo mesmo rastreio da producao.

    Nunca uma origem escrita a mao: o painel anda 827x831 px nas gravacoes de
    campo, e um par fixo aqui mediria uma geometria que a producao nao usa.
    """
    voto = leitor._rastreio.observar(janela)
    assert voto.aberto, "o rastreio nao viu o painel aberto nesta fixtura"
    origem = leitor._rastreio.origem
    assert origem is not None, "o rastreio nao localizou o painel nesta fixtura"
    return origem


# --------------------------------------------------------------------------
# Task 1 — a chave nova entra ANINHADA e OPCIONAL
# --------------------------------------------------------------------------


class TestAListaDasQuinzeNaoCresceu:
    """A pergunta "estou calibrado para mercado?" tem UMA resposta so.

    Se `mercado_layouts` entrasse nela, todo usuario que nunca viu a aba Adena
    passaria a ter o `--mercado` RECUSANDO subir — a feature vira produto la, e
    a lista e quem decide.
    """

    def test_uma_calibracao_vazia_de_mercado_devolve_exatamente_quinze(self):
        cal = Calibracao(
            party_window=None,
            ancora=None,
            layout=None,
            limiares_hp=None,
            limiares_mp=None,
            geometria_da_tela=None,
        )
        faltando = pecas_de_calibracao_de_mercado_faltando(cal)
        assert len(faltando) == 15, faltando

    def test_mercado_layouts_nao_esta_entre_as_quinze(self):
        cal = Calibracao(
            party_window=None,
            ancora=None,
            layout=None,
            limiares_hp=None,
            limiares_mp=None,
            geometria_da_tela=None,
        )
        assert "mercado_layouts" not in pecas_de_calibracao_de_mercado_faltando(cal)

    def test_o_CONTROLE_NEGATIVO_a_lista_reage_a_uma_peca_de_verdade(self):
        """Sem ele, "15" nao distinguiria uma lista viva de uma constante.

        Tirar `mercado_grade` de uma calibracao COMPLETA tem de fazer a lista
        crescer de zero para um; se nao fizesse, o teste acima estaria medindo
        um numero congelado.
        """
        completa = _calibracao_da_fixtura()
        assert pecas_de_calibracao_de_mercado_faltando(completa) == []
        completa.mercado_grade = None
        assert pecas_de_calibracao_de_mercado_faltando(completa) == ["mercado_grade"]


class TestMercadoLayoutsEOpcional:
    def test_ausente_carrega_sem_erro_e_chega_como_None(self, tmp_path):
        dados = _dados_da_fixtura()
        dados.pop("mercado_layouts", None)
        cal = Calibracao.carregar(_gravar(tmp_path, dados))
        assert cal.mercado_layouts is None

    def test_a_VERSAO_DO_ESQUEMA_continua_2(self, tmp_path):
        dados = _dados_da_fixtura()
        cal = Calibracao.carregar(_gravar(tmp_path, dados))
        assert cal.versao == 2

    def test_a_chave_atravessa_o_ida_e_volta_do_arquivo(self, tmp_path):
        dados = _dados_da_fixtura()
        cal = Calibracao.carregar(_gravar(tmp_path, dados))
        destino = tmp_path / "de_volta.json"
        cal.salvar(destino)
        assert (
            Calibracao.carregar(destino).mercado_layouts == cal.mercado_layouts
        )


class TestUmBlocoCorrompidoCaiNoARRANQUE:
    """T-05-04: o hex torto tem de levantar AQUI, nao dentro do tick.

    O caminho do construtor do leitor vira feature OFF com aviso, e la o usuario
    le "a leitura de mercado nao vai acontecer" sem nunca ler a causa.
    """

    def test_bytes_de_tamanho_errado_levanta_citando_o_conserto(self, tmp_path):
        dados = _dados_da_fixtura()
        molde = copy.deepcopy(dados["mercado_cabecalho_de_coluna"])
        molde["layout"] = "adena"
        molde["bytes"] = molde["bytes"][:-4]  # dois bytes a menos
        dados["mercado_layouts"] = {
            "adena": {"cabecalho": molde, "limiar_do_cabecalho": 0.73}
        }
        with pytest.raises(CalibracaoInvalida) as erro:
            Calibracao.carregar(_gravar(tmp_path, dados))
        mensagem = str(erro.value)
        assert "mercado_layouts.adena.cabecalho" in mensagem
        assert "Recalibre o mercado" in mensagem

    def test_o_CONTROLE_NEGATIVO_o_mesmo_bloco_INTEIRO_carrega(self, tmp_path):
        """Sem ele, "levantou" nao distinguiria a contagem de bytes de qualquer
        outra peneira do carregamento."""
        dados = _dados_da_fixtura()
        molde = copy.deepcopy(dados["mercado_cabecalho_de_coluna"])
        molde["layout"] = "adena"
        dados["mercado_layouts"] = {
            "adena": {"cabecalho": molde, "limiar_do_cabecalho": 0.73}
        }
        cal = Calibracao.carregar(_gravar(tmp_path, dados))
        assert set(cal.mercado_layouts) == {"adena"}

    def test_negociacao_aninhada_e_recusada(self, tmp_path):
        dados = _dados_da_fixtura()
        dados["mercado_layouts"] = {"negociacao": {"limiar_do_cabecalho": 0.73}}
        with pytest.raises(CalibracaoInvalida, match="negociacao"):
            Calibracao.carregar(_gravar(tmp_path, dados))

    def test_um_bloco_que_nao_e_objeto_e_recusado(self, tmp_path):
        dados = _dados_da_fixtura()
        dados["mercado_layouts"] = {"adena": [1, 2, 3]}
        with pytest.raises(CalibracaoInvalida, match="mercado_layouts.adena"):
            Calibracao.carregar(_gravar(tmp_path, dados))

    def test_mercado_layouts_que_nao_e_objeto_e_recusado(self, tmp_path):
        dados = _dados_da_fixtura()
        dados["mercado_layouts"] = ["adena"]
        with pytest.raises(CalibracaoInvalida, match="mercado_layouts"):
            Calibracao.carregar(_gravar(tmp_path, dados))

    def test_coluna_de_largura_zero_e_recusada(self, tmp_path):
        dados = _dados_da_fixtura()
        dados["mercado_layouts"] = {
            "adena": {"colunas": {"total": {"dx": 62, "largura": 0}}}
        }
        with pytest.raises(CalibracaoInvalida, match="largura nao-positiva"):
            Calibracao.carregar(_gravar(tmp_path, dados))

    def test_dx_NEGATIVO_e_legitimo_e_passa(self, tmp_path):
        """`dx` e deslocamento a partir da origem do painel: a coluna do nome de
        negociacao ja e -385. Recusar negativo mataria a calibracao de hoje."""
        dados = _dados_da_fixtura()
        dados["mercado_layouts"] = {
            "adena": {"colunas": {"total": {"dx": -385, "largura": 324}}}
        }
        cal = Calibracao.carregar(_gravar(tmp_path, dados))
        assert cal.mercado_layouts["adena"]["colunas"]["total"]["dx"] == -385

    def test_limiar_do_cabecalho_fora_da_faixa_e_recusado(self, tmp_path):
        """A conferencia de faixa do limiar ANINHADO nao pode ser vacua.

        Ela procura `limiar_do_cabecalho` DENTRO do bloco enquanto reporta o
        nome pontuado; um `.get` pelo nome pontuado devolveria `None` e a
        conferencia passaria sempre, calada.
        """
        dados = _dados_da_fixtura()
        dados["mercado_layouts"] = {"adena": {"limiar_do_cabecalho": 0.0}}
        with pytest.raises(CalibracaoInvalida) as erro:
            Calibracao.carregar(_gravar(tmp_path, dados))
        assert "mercado_layouts.adena.limiar_do_cabecalho" in str(erro.value)

    def test_limiar_do_cabecalho_booleano_e_recusado(self, tmp_path):
        """`bool` e subclasse de `int`: `True` viraria limiar 1.0 calado."""
        dados = _dados_da_fixtura()
        dados["mercado_layouts"] = {"adena": {"limiar_do_cabecalho": True}}
        with pytest.raises(CalibracaoInvalida, match="precisa ser um numero"):
            Calibracao.carregar(_gravar(tmp_path, dados))

    def test_o_CONTROLE_NEGATIVO_do_limiar_um_valor_valido_passa(self, tmp_path):
        dados = _dados_da_fixtura()
        dados["mercado_layouts"] = {"adena": {"limiar_do_cabecalho": 0.73}}
        cal = Calibracao.carregar(_gravar(tmp_path, dados))
        assert cal.mercado_layouts["adena"]["limiar_do_cabecalho"] == 0.73

    def test_grade_que_nao_e_objeto_e_recusada(self, tmp_path):
        dados = _dados_da_fixtura()
        dados["mercado_layouts"] = {"adena": {"grade": 45}}
        with pytest.raises(CalibracaoInvalida, match="grade precisa ser um objeto"):
            Calibracao.carregar(_gravar(tmp_path, dados))

    def test_uma_grade_CURTA_passa_porque_o_resto_se_herda(self, tmp_path):
        dados = _dados_da_fixtura()
        dados["mercado_layouts"] = {"adena": {"grade": {"linhas_por_pagina": 9}}}
        cal = Calibracao.carregar(_gravar(tmp_path, dados))
        assert cal.mercado_layouts["adena"]["grade"] == {"linhas_por_pagina": 9}


# --------------------------------------------------------------------------
# Task 2 — a matriz medida nos DOIS sentidos, e o portao que ESCOLHE
# --------------------------------------------------------------------------

BANDAS = (
    "cabecalho_negociacao_goods.png",
    "cabecalho_negociacao_unitprice.png",
    "cabecalho_adena.png",
    "cabecalho_busca.png",
)

# A MATRIZ MEDIDA nesta arvore em 2026-09-01, com o codigo de producao sobre as
# quatro bandas versionadas. Os mesmos oito numeros estao na docstring de
# `LeitorDePagina._casamento_do_layout`; esta tabela e o que impede aquela de
# envelhecer em silencio (o padrao que `TestAFixturaDaAdenaLeOQueODocstringDiz`
# estabeleceu no 05-01).
#
# O VAO E SIMETRICO — 0,1331 nos DOIS sentidos —, e isso CORRIGE a suposicao A1
# da pesquisa, que esperava assimetria. `casamento_da_ancora` e uma correlacao
# normalizada, e correlacao normalizada e simetrica nos seus dois argumentos.
MATRIZ_MEDIDA = {
    ("negociacao", "cabecalho_negociacao_goods.png"): 1.0000,
    ("adena", "cabecalho_negociacao_goods.png"): 0.1331,
    ("negociacao", "cabecalho_negociacao_unitprice.png"): 1.0000,
    ("adena", "cabecalho_negociacao_unitprice.png"): 0.1331,
    ("negociacao", "cabecalho_adena.png"): 0.1331,
    ("adena", "cabecalho_adena.png"): 1.0000,
    ("negociacao", "cabecalho_busca.png"): -0.0027,
    ("adena", "cabecalho_busca.png"): -0.0029,
}

VENCEDOR_POR_BANDA = {
    "cabecalho_negociacao_goods.png": "negociacao",
    "cabecalho_negociacao_unitprice.png": "negociacao",
    "cabecalho_adena.png": "adena",
    "cabecalho_busca.png": None,
}


def _moldes_dos_dois_layouts(cal) -> dict:
    saida = {}
    for nome in ("negociacao", "adena"):
        modelo = modelo_de_layout(cal, nome)
        saida[nome] = (
            cabecalho_de_calibracao(modelo["cabecalho"]),
            int(modelo["cabecalho"]["corte_de_brilho"]),
            float(modelo["limiar_do_cabecalho"]),
        )
    return saida


def _vencedor_medido(cal, banda: str) -> str | None:
    passam = {}
    for nome, (molde, corte, limiar) in _moldes_dos_dois_layouts(cal).items():
        score = casamento_do_cabecalho(_imagem(banda), molde, corte)
        if score >= limiar:
            passam[nome] = score
    if not passam:
        return None
    topo = max(passam.values())
    nomes = [n for n, s in passam.items() if s == topo]
    return nomes[0] if len(nomes) == 1 else None


class TestAMatrizDeCasamentoNosDoisSentidos:
    """As OITO casas, reafirmadas contra os pixels versionados a cada rodada."""

    @pytest.mark.parametrize("banda", BANDAS)
    @pytest.mark.parametrize("layout", ("negociacao", "adena"))
    def test_a_casa_medida_continua_valendo(self, layout, banda):
        cal = _calibracao_da_fixtura()
        molde, corte, _limiar = _moldes_dos_dois_layouts(cal)[layout]
        score = casamento_do_cabecalho(_imagem(banda), molde, corte)
        assert score == pytest.approx(MATRIZ_MEDIDA[(layout, banda)], abs=5e-4)

    @pytest.mark.parametrize("banda", BANDAS)
    def test_o_vencedor_por_banda(self, banda):
        cal = _calibracao_da_fixtura()
        assert _vencedor_medido(cal, banda) == VENCEDOR_POR_BANDA[banda]

    def test_a_BUSCA_nao_ganha_casamento_de_NENHUM_dos_dois(self):
        """Ela nao tem leitora, e um casamento dela seria recusa por tick."""
        cal = _calibracao_da_fixtura()
        for _nome, (molde, corte, limiar) in _moldes_dos_dois_layouts(cal).items():
            score = casamento_do_cabecalho(
                _imagem("cabecalho_busca.png"), molde, corte
            )
            assert score < limiar

    def test_o_vao_e_SIMETRICO_e_isso_corrige_a_suposicao_A1(self):
        cal = _calibracao_da_fixtura()
        moldes = _moldes_dos_dois_layouts(cal)
        adena_contra_negociacao = casamento_do_cabecalho(
            _imagem("cabecalho_negociacao_goods.png"), *moldes["adena"][:2]
        )
        negociacao_contra_adena = casamento_do_cabecalho(
            _imagem("cabecalho_adena.png"), *moldes["negociacao"][:2]
        )
        assert adena_contra_negociacao == pytest.approx(
            negociacao_contra_adena, abs=5e-4
        )

    def test_a_docstring_do_portao_carrega_os_oito_numeros(self):
        """A tabela no fonte e o que alguem le antes de mexer no limiar."""
        fonte = LeitorDePagina._casamento_do_layout.__doc__
        for valor in ("1,0000", "0,1331", "-0,0027", "-0,0029"):
            assert valor in fonte


class TestOPortaoESCOLHEEmVezDeSoRecusar:
    def test_devolve_o_NOME_do_vencedor_e_nao_um_bool(self):
        cal = _calibracao_da_fixtura()
        leitor, _b, _c = _montar_leitor(cal)
        janela = _imagem("janela_adena_f014.png")
        origem = _origem_do_painel(leitor, janela)
        vencedor = leitor._casamento_do_layout(janela, origem)
        assert vencedor == "adena"
        assert not isinstance(vencedor, bool)

    def test_a_janela_de_negociacao_elege_negociacao(self):
        cal = _calibracao_da_fixtura()
        leitor, _b, _c = _montar_leitor(cal)
        janela = _imagem("janela_negociacao_f005.png")
        origem = _origem_do_painel(leitor, janela)
        assert leitor._casamento_do_layout(janela, origem) == "negociacao"

    def test_o_vencedor_fica_guardado_em_layout_atual(self):
        cal = _calibracao_da_fixtura()
        leitor, _b, _c = _montar_leitor(cal)
        leitor.observar(_imagem("janela_adena_f014.png"))
        assert leitor._layout_atual == "adena"

    def test_layout_confere_continua_devolvendo_bool(self):
        cal = _calibracao_da_fixtura()
        leitor, _b, _c = _montar_leitor(cal)
        janela = _imagem("janela_adena_f014.png")
        origem = _origem_do_painel(leitor, janela)
        assert leitor._layout_confere(janela, origem) is True


class TestEmpateNaoEVeredito:
    """Aceitar "o primeiro que passou" faria o veredito depender da ordem de
    iteracao de um dict lido de JSON — a ordem em que o USUARIO calibrou."""

    def _cal_com_clone(self, tmp_path):
        dados = _dados_da_fixtura()
        clone = copy.deepcopy(dados["mercado_cabecalho_de_coluna"])
        clone["layout"] = "adena"
        # O molde da NEGOCIACAO, byte a byte, gravado sob o nome do outro
        # layout: os dois casam a mesma banda com o MESMO score.
        dados["mercado_layouts"] = {
            "adena": {
                "cabecalho": clone,
                "limiar_do_cabecalho": 0.73,
                "colunas": {
                    "total": {"dx": 62, "largura": 209},
                    "unitario": {"dx": 271, "largura": 174},
                },
            }
        }
        return Calibracao.carregar(_gravar(tmp_path, dados))

    def test_dois_moldes_identicos_devolvem_None(self, tmp_path):
        cal = self._cal_com_clone(tmp_path)
        leitor, _b, _c = _montar_leitor(cal)
        janela = _imagem("janela_negociacao_f005.png")
        origem = _origem_do_painel(leitor, janela)
        assert leitor._casamento_do_layout(janela, origem) is None

    def test_no_empate_NENHUMA_linha_e_lida(self, tmp_path):
        cal = self._cal_com_clone(tmp_path)
        leitor, _b, _c = _montar_leitor(cal)
        assert leitor.observar(_imagem("janela_negociacao_f005.png")) is None
        assert leitor.ultima_leitura is None

    def test_o_CONTROLE_NEGATIVO_sem_o_clone_a_MESMA_janela_e_lida(self):
        """Sem ele, "None" nao distinguiria o empate de uma janela ilegivel."""
        cal = _calibracao_da_fixtura()
        leitor, _b, _c = _montar_leitor(cal)
        janela = _imagem("janela_negociacao_f005.png")
        origem = _origem_do_painel(leitor, janela)
        assert leitor._casamento_do_layout(janela, origem) == "negociacao"


class TestUmLayoutSemLeitoraFicaFORADoPortao:
    """`busca` e o caso vivo: o calibrador ja a aceita e `LINHAS_ESPERADAS` ja
    tem 9 para ela. Com o portao escolhendo por maior score, ela passaria a
    poder VENCER — e vencer sem leitora significa RECUSAR a pagina, que e a
    perda que o ADEN-01 proibe."""

    def _cal_com_busca(self, tmp_path):
        dados = _dados_da_fixtura()
        # A `busca` recebe o molde da NEGOCIACAO, de proposito: assim ela
        # casaria 1,0000 a janela de negociacao e venceria, SE entrasse.
        clone = copy.deepcopy(dados["mercado_cabecalho_de_coluna"])
        clone["layout"] = "busca"
        dados["mercado_layouts"]["busca"] = {
            "cabecalho": clone,
            "limiar_do_cabecalho": 0.73,
            "colunas": {"total": {"dx": 62, "largura": 209}},
        }
        return Calibracao.carregar(_gravar(tmp_path, dados))

    def test_o_conjunto_de_candidatos_se_deriva_das_leitoras(self):
        assert LAYOUTS_COM_LEITORA == frozenset(LEITORAS_DE_LINHA_POR_LAYOUT)
        assert "busca" not in LAYOUTS_COM_LEITORA

    def test_a_leitora_e_resolvida_NA_HORA_e_nao_congelada_no_import(
        self, monkeypatch
    ):
        """Um objeto guardado no registro congelaria a ligacao no import, e o
        despacho deixaria de enxergar um `monkeypatch` sobre o modulo — que e
        como a suite prova CHAMADA (`TestOLeitorDePaginaCONSULTA_A_TRAVA`).

        MEDIDO: com a funcao congelada, aquele teste falha em "`ler_linha` nao
        foi chamada: o teste nao cobre nada".
        """
        import l2scanner.mercado_pagina as pagina

        sentinela = object()
        monkeypatch.setattr(pagina, "ler_linha", sentinela)
        assert pagina.leitora_de_linha("negociacao") is sentinela

    def test_o_CONTROLE_NEGATIVO_sem_patch_a_leitora_e_a_de_verdade(self):
        import l2scanner.mercado_pagina as pagina

        assert pagina.leitora_de_linha("negociacao") is pagina.ler_linha
        assert pagina.leitora_de_linha("adena") is pagina.ler_linha_de_adena

    def test_busca_calibrada_NAO_entra_nos_candidatos(self, tmp_path):
        cal = self._cal_com_busca(tmp_path)
        leitor, _b, _c = _montar_leitor(cal)
        assert "busca" not in leitor._layouts
        assert set(leitor._layouts) == {"negociacao", "adena"}

    def test_busca_calibrada_NAO_impede_a_leitura_da_negociacao(self, tmp_path):
        """A perda que esta protecao existe para evitar, medida.

        Sem ela `busca` empataria 1,0000 com `negociacao` sobre esta janela, o
        portao devolveria `None` por empate, e o usuario perderia a leitura da
        negociacao — conferida em campo, 353 paginas lidas contra 2 perdidas.
        """
        cal = self._cal_com_busca(tmp_path)
        leitor, _b, _c = _montar_leitor(cal)
        janela = _imagem("janela_negociacao_f005.png")
        origem = _origem_do_painel(leitor, janela)
        assert leitor._casamento_do_layout(janela, origem) == "negociacao"

    def test_ela_produz_UM_aviso_no_arranque_e_nao_silencio(self, tmp_path, caplog):
        cal = self._cal_com_busca(tmp_path)
        with caplog.at_level("WARNING", logger="l2scanner.mercado_pagina"):
            _montar_leitor(cal)
        assert "busca" in caplog.text
        assert "nao existe leitora" in caplog.text

    def test_o_CONTROLE_NEGATIVO_um_layout_COM_leitora_nao_avisa(self, caplog):
        """Sem ele, o aviso poderia estar saindo para todo bloco aninhado."""
        cal = _calibracao_da_fixtura()
        with caplog.at_level("WARNING", logger="l2scanner.mercado_pagina"):
            _montar_leitor(cal)
        assert "nao existe leitora" not in caplog.text


class TestUmBlocoTortoNaoDerrubaOLeitor:
    """T-05-06: feature OFF para o bloco, nunca `raise` no tick."""

    def test_molde_indecodificavel_vira_ausente_com_aviso(self, tmp_path, caplog):
        dados = _dados_da_fixtura()
        cal = Calibracao.carregar(_gravar(tmp_path, dados))
        # A corrupcao entra DEPOIS do carregamento, de proposito: aqui o alvo e
        # a resiliencia do LEITOR, e nao a validacao do arranque — que ja tem
        # teste proprio e recusaria este arquivo antes de chegar aqui.
        cal.mercado_layouts["adena"]["cabecalho"]["altura"] = 7
        with caplog.at_level("WARNING", logger="l2scanner.mercado_pagina"):
            leitor, _b, _c = _montar_leitor(cal)
        assert "adena" not in leitor._layouts
        assert "negociacao" in leitor._layouts
        assert "corrompido" in caplog.text

    def test_a_negociacao_continua_lida_com_o_bloco_torto(self, tmp_path):
        dados = _dados_da_fixtura()
        cal = Calibracao.carregar(_gravar(tmp_path, dados))
        cal.mercado_layouts["adena"]["cabecalho"]["altura"] = 7
        leitor, _b, _c = _montar_leitor(cal)
        janela = _imagem("janela_negociacao_f005.png")
        origem = _origem_do_painel(leitor, janela)
        assert leitor._casamento_do_layout(janela, origem) == "negociacao"


class TestAGradeDaAdenaSeHERDA:
    def test_os_campos_ausentes_caem_em_mercado_grade(self):
        cal = _calibracao_da_fixtura()
        modelo = modelo_de_layout(cal, "adena")
        for campo in ("dx", "dy", "largura", "altura_da_linha", "linhas_por_pagina"):
            assert modelo["grade"][campo] == cal.mercado_grade[campo], campo

    def test_um_campo_PROPRIO_vence_a_heranca(self, tmp_path):
        """O CONTROLE NEGATIVO da heranca: sem ele, "igual a mercado_grade" nao
        distinguiria heranca de uma copia congelada."""
        dados = _dados_da_fixtura()
        dados["mercado_layouts"]["adena"]["grade"] = {"linhas_por_pagina": 9}
        cal = Calibracao.carregar(_gravar(tmp_path, dados))
        modelo = modelo_de_layout(cal, "adena")
        assert modelo["grade"]["linhas_por_pagina"] == 9
        assert modelo["grade"]["dx"] == cal.mercado_grade["dx"]

    def test_o_layout_inexistente_devolve_None(self):
        cal = _calibracao_da_fixtura()
        assert modelo_de_layout(cal, "nao_existe") is None


# --------------------------------------------------------------------------
# Task 3 — a pagina da Adena, de pixels a nove linhas de taxa
# --------------------------------------------------------------------------


def _pagina_da_adena(cal):
    """A pagina aceita depois do ACORDO ENTRE DOIS FRAMES.

    A mesma janela lida DUAS vezes: e assim que a producao funciona, e uma
    passada so nunca devolve `PaginaAceita`.
    """
    leitor, barata, conferencia = _montar_leitor(cal)
    janela = _imagem("janela_adena_f014.png")
    assert leitor.observar(janela) is None
    aceita = leitor.observar(janela)
    return leitor, aceita, barata, conferencia


class TestAPaginaDaAdenaPontaAPonta:
    def test_nove_linhas_de_taxa(self):
        _leitor, aceita, _b, _c = _pagina_da_adena(_calibracao_da_fixtura())
        assert aceita is not None
        assert len(aceita.linhas) == 9

    def test_a_linha_5_cai_por_CRUZAMENTO(self):
        """O `13588` que a tela mostra como `135,00`. Sem a guarda ele entraria
        no CSV como taxa `135,88` — plausivel, e errado."""
        _leitor, aceita, _b, _c = _pagina_da_adena(_calibracao_da_fixtura())
        assert aceita.descartadas == (5,)
        assert aceita.motivos == ("cruzamento",)

    def test_toda_chave_da_serie_e_a_SENTINELA(self):
        _leitor, aceita, _b, _c = _pagina_da_adena(_calibracao_da_fixtura())
        chaves = {linha.chave_da_serie for linha in aceita.linhas}
        assert chaves == {CHAVE_DA_SERIE_DA_ADENA}

    def test_as_quantidades_sao_5M_ou_10M(self):
        _leitor, aceita, _b, _c = _pagina_da_adena(_calibracao_da_fixtura())
        quantidades = {linha.quantidade for linha in aceita.linhas}
        assert quantidades <= {5_000_000, 10_000_000}
        assert quantidades

    def test_NENHUMA_chamada_de_OCR_na_pagina_da_adena(self):
        """A identidade vem da sentinela, e `ler_linha_de_adena` nao TEM por
        onde receber uma leitora de texto (afirmado por assinatura no 05-01)."""
        _leitor, _aceita, barata, conferencia = _pagina_da_adena(
            _calibracao_da_fixtura()
        )
        assert barata.chamadas == 0
        assert conferencia.chamadas == 0

    def test_a_pagina_conta_como_LIDA_e_nao_como_de_outro_layout(self):
        leitor, _aceita, _b, _c = _pagina_da_adena(_calibracao_da_fixtura())
        assert leitor.paginas_de_outro_layout == 0
        assert leitor.paginas_lidas == 1


class TestOsRecortesDaAdenaSaoEXATAMENTEDois:
    """A truth que nenhum criterio de contagem alcanca.

    Com CONTINENCIA (`>= {"total","unitario"}`) um terceiro recorte inutil sobre
    a `Auction List` passaria despercebido, as 9 linhas continuariam saindo, e a
    promessa de que aquela coluna nao e tocada viraria prosa. Por isso IGUALDADE.
    """

    def test_o_conjunto_de_recortes_e_igual_e_nao_apenas_contido(self):
        cal = _calibracao_da_fixtura()
        leitor, _b, _c = _montar_leitor(cal)
        janela = _imagem("janela_adena_f014.png")
        ox, _oy = _origem_do_painel(leitor, janela)
        modelo = leitor._layouts["adena"]
        recortes = leitor._recortes_de_coluna(janela, ox, 300, 45, modelo)
        assert set(recortes) == {"total", "unitario"}

    def test_o_modelo_da_adena_nao_tem_coluna_de_NOME(self):
        modelo = modelo_de_layout(_calibracao_da_fixtura(), "adena")
        assert set(modelo["colunas"]) == {"total", "unitario"}
        assert "nome" not in modelo["colunas"]

    def test_o_CONTROLE_NEGATIVO_a_negociacao_tem_as_QUATRO(self):
        """Sem ele, "duas colunas" nao distinguiria o modelo da Adena de um
        `_recortes_de_coluna` que simplesmente parou de recortar."""
        modelo = modelo_de_layout(_calibracao_da_fixtura(), "negociacao")
        assert set(modelo["colunas"]) == {
            "nome",
            "quantidade",
            "total",
            "unitario",
        }

    def test_nenhum_recorte_da_adena_alcanca_a_coluna_do_NOME(self):
        """A medicao por tras da regra: a coluna do nome de negociacao comeca a
        −1 px do primeiro run claro da `Auction List` (x=624 contra x=625).
        Reaproveita-la cortaria o `1` de `10,000,000` -> `0,000,000`."""
        cal = _calibracao_da_fixtura()
        dx_do_nome = int(cal.mercado_coluna_do_nome["dx"])
        largura_do_nome = int(cal.mercado_coluna_do_nome["largura"])
        fim_do_nome = dx_do_nome + largura_do_nome
        modelo = modelo_de_layout(cal, "adena")
        for nome, coluna in modelo["colunas"].items():
            assert int(coluna["dx"]) >= fim_do_nome, nome


class TestUmCloneQueNuncaCalibrouAAdenaLeIgual:
    """A prova de ADEN-01, e ela e um PAR: a mesma janela de negociacao, com e
    sem `mercado_layouts`, campo a campo."""

    def _leitura(self, cal, nome_da_janela: str):
        leitor, _b, _c = _montar_leitor(cal)
        janela = _imagem(nome_da_janela)
        leitor.observar(janela)
        return leitor.ultima_leitura

    def test_janela_negociacao_f005_le_IGUAL_com_e_sem_a_chave(self):
        com = _calibracao_da_fixtura()
        sem = _calibracao_da_fixtura()
        sem.mercado_layouts = None
        de_com = self._leitura(com, "janela_negociacao_f005.png")
        de_sem = self._leitura(sem, "janela_negociacao_f005.png")
        assert de_com is not None
        assert de_com == de_sem

    def test_os_CAMPOS_um_a_um_e_nao_so_a_igualdade_do_dataclass(self):
        com = _calibracao_da_fixtura()
        sem = _calibracao_da_fixtura()
        sem.mercado_layouts = None
        de_com = self._leitura(com, "janela_negociacao_f005.png")
        de_sem = self._leitura(sem, "janela_negociacao_f005.png")
        assert de_com.linhas == de_sem.linhas
        assert de_com.descartadas == de_sem.descartadas
        assert de_com.motivos == de_sem.motivos
        assert de_com.vazias == de_sem.vazias

    def test_o_CONTROLE_NEGATIVO_a_chave_MUDA_a_leitura_da_janela_da_ADENA(self):
        """Sem ele, "iguais" nao distinguiria "a chave nao afeta a negociacao"
        de "a chave nao afeta nada" — que e o modo de falha em que o portao
        novo nunca teria sido ligado."""
        com = _calibracao_da_fixtura()
        sem = _calibracao_da_fixtura()
        sem.mercado_layouts = None
        assert self._leitura(sem, "janela_adena_f014.png") is None
        assert self._leitura(com, "janela_adena_f014.png") is not None
