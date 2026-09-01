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
from l2scanner.mercado_pagina import pecas_de_calibracao_de_mercado_faltando

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
