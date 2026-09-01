"""As GUARDAS da varredura que escolhe a sonda de oclusao.

Esta ferramenta ja causou dois defeitos de campo, e os dois tinham a mesma
forma: a escolha foi feita contra um gabarito que nao continha o pior caso, e a
prosa que avisava disso nao era executada por ninguem. `tools/medir_oclusao.py`
respondeu com guardas que PARAM a ferramenta -- e ate 2026-09-01 nenhuma delas
tinha teste. Uma guarda sem teste e uma prosa mais longa.

Tudo aqui e PURO: nenhum teste abre `recordings/` nem le o `calibration.json` de
producao. Os dois sao gitignored e nao vem de clone limpo. O que se afirma sao
as decisoes da ferramenta sobre dados MONTADOS a mao, onde a resposta certa e
conhecida por construcao -- que e a unica forma de saber se a guarda morde.

O QUE CADA CLASSE PRENDE
------------------------
    TestOConjuntoMedido        o censo historico nao pode ser reescrito por
                               engano quando a varredura ganha material novo
    TestAsBandasCandidatas     a banda usa a janela inteira em x; nao ha `dx0`
    TestAEscolhaSobDeriva      a folga que decide e a do PIOR caso, nao a do
                               ponto calibrado -- a correcao do FORMATO do
                               defeito de 31/08
    TestAGuardaDoGabarito      as tres conferencias que PARAM a ferramenta
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent


def _carregar_a_ferramenta(nome: str):
    caminho = RAIZ / "tools" / f"{nome}.py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    assert spec and spec.loader, f"nao carreguei {caminho}"
    modulo = importlib.util.module_from_spec(spec)
    # Registrar ANTES de executar: `@dataclass` resolve as anotacoes por
    # `sys.modules[cls.__module__]`, e sem isto ele encontra None.
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


ferramenta = _carregar_a_ferramenta("medir_oclusao")

GRAVACOES_DO_CENSO = ferramenta.GRAVACOES_DO_CENSO
GRAVACOES_DA_VARREDURA = ferramenta.GRAVACOES_DA_VARREDURA
GRAVACAO_DO_NOME_LONGO = ferramenta.GRAVACAO_DO_NOME_LONGO
GABARITO_LIMPAS = ferramenta.GABARITO_LIMPAS
GABARITO_COBERTAS = ferramenta.GABARITO_COBERTAS
PIOR_NOME_CONHECIDO_EM_CARACTERES = ferramenta.PIOR_NOME_CONHECIDO_EM_CARACTERES
FOLGA_VERTICAL_MINIMA = ferramenta.FOLGA_VERTICAL_MINIMA
DERIVA_CONFERIDA = ferramenta.DERIVA_CONFERIDA
LeituraDeFrame = ferramenta.LeituraDeFrame
Varredura = ferramenta.Varredura


# ---------------------------------------------------------------------------
# Montagem de uma varredura de mentira, com a resposta conhecida
# ---------------------------------------------------------------------------

LINHAS = 10


def _leitura(
    gravacao: str,
    arquivo: str,
    valor_por_candidato: dict,
    *,
    n_candidatos: int,
    ponta: int = 100,
    tinta: tuple[int, int] = (15, 27),
    por_deriva: dict | None = None,
) -> LeituraDeFrame:
    """Um frame inteiro com a MESMA dispersao em todas as dez linhas."""
    matriz = np.full((LINHAS, n_candidatos), np.nan)
    for coluna, valor in valor_por_candidato.items():
        matriz[:, coluna] = valor
    derivadas = {}
    for deriva, mapa in (por_deriva or {}).items():
        movida = np.full((LINHAS, n_candidatos), np.nan)
        for coluna, valor in mapa.items():
            movida[:, coluna] = valor
        derivadas[deriva] = movida
    return LeituraDeFrame(
        gravacao,
        arquivo,
        matriz,
        np.full(LINHAS, ponta, dtype=int),
        np.tile(np.asarray(tinta, dtype=int), (LINHAS, 1)),
        derivadas,
    )


class TestOConjuntoMedido:
    """O censo historico e o material da varredura sao listas DIFERENTES."""

    def test_o_censo_continua_sendo_as_OITO_da_pesquisa(self) -> None:
        """Tres outras ferramentas IMPORTAM esta lista daqui.

        `medir_agrupamento_de_nome.py` tem um fixture versionado -
        `leituras_de_nome.json`, 3.511 linhas lidas por OCR - cujo teste afirma
        que ele cobre exatamente estas oito gravacoes. Empurrar material novo
        para dentro do censo quebraria esse fixture calado, e "consertar" o
        teste exigiria reprocessar 3.511 linhas com o motor de OCR.

        O censo e um artefato HISTORICO datado - as 335 frames da pesquisa -,
        nao "o material que as ferramentas medem". Crescer a medicao e crescer
        `GRAVACOES_DA_VARREDURA`.
        """
        assert len(GRAVACOES_DO_CENSO) == 8
        assert GRAVACAO_DO_NOME_LONGO not in GRAVACOES_DO_CENSO

    def test_a_varredura_mede_o_censo_MAIS_a_gravacao_de_nome_longo(self) -> None:
        assert GRAVACOES_DA_VARREDURA[: len(GRAVACOES_DO_CENSO)] == (
            GRAVACOES_DO_CENSO
        )
        assert GRAVACOES_DA_VARREDURA[-1] == GRAVACAO_DO_NOME_LONGO
        assert len(set(GRAVACOES_DA_VARREDURA)) == len(GRAVACOES_DA_VARREDURA)

    def test_a_pre_voo_fica_de_fora_das_duas(self) -> None:
        """1.502 PNGs de outro dia dominariam sozinhos qualquer distribuicao."""
        assert "20260827-225521-pre-voo" not in GRAVACOES_DA_VARREDURA
        assert "20260827-225521-pre-voo" in ferramenta.MOTIVO_PARA_IGNORAR

    def test_o_gabarito_limpo_declara_o_pior_nome_conhecido(self) -> None:
        """A guarda so morde se houver o que ela confere. Aqui e a tabela.

        Sem esta assertiva alguem poderia subir
        `PIOR_NOME_CONHECIDO_EM_CARACTERES` e deixar o gabarito para tras: a
        ferramenta pararia, e a reacao natural seria BAIXAR o piso de volta -
        que e desligar a guarda.
        """
        declarados = [
            len(nome) for _g, _a, _l, nome in GABARITO_LIMPAS if nome
        ]
        assert declarados
        assert max(declarados) >= PIOR_NOME_CONHECIDO_EM_CARACTERES

    def test_o_gabarito_COBERTO_nao_encosta_no_gabarito_LIMPO(self) -> None:
        """Uma linha nao pode estar nas duas tabelas. Rotulo e rotulo."""
        limpas = {
            (g, a, i) for g, a, linhas, _n in GABARITO_LIMPAS for i in linhas
        }
        cobertas = {
            (g, a, i) for g, a, linhas in GABARITO_COBERTAS for i in linhas
        }
        assert not (limpas & cobertas)


class TestAsBandasCandidatas:
    """A banda desliza em Y. Nao ha `dx0` a escolher, e essa e a mudanca."""

    def test_toda_banda_cabe_na_linha(self) -> None:
        for dy0, dy1 in ferramenta.candidatos_de_banda(45):
            assert 0 <= dy0 < dy1 <= 45

    def test_as_alturas_sao_as_declaradas(self) -> None:
        alturas = {dy1 - dy0 for dy0, dy1 in ferramenta.candidatos_de_banda(45)}
        assert alturas == set(ferramenta.ALTURAS_DA_BANDA)

    def test_uma_linha_mais_baixa_que_a_banda_nao_gera_candidato(self) -> None:
        """Geometria impossivel devolve lista vazia, e nunca levanta."""
        assert ferramenta.candidatos_de_banda(3) == []

    def test_a_varredura_NAO_desliza_em_x(self) -> None:
        """A prova de que o defeito saiu de circulacao, e nao so de posicao.

        Enquanto existisse uma escolha de `dx0`, existiria um proximo item cujo
        nome a alcancasse. A ferramenta so pode voltar a ter essa falha se
        alguem reintroduzir a varredura horizontal - e ai este teste cai.
        """
        fonte = (RAIZ / "tools" / "medir_oclusao.py").read_text(
            encoding="utf-8"
        )
        assert "def candidatos_de_sonda" not in fonte
        assert "LARGURA_DA_SONDA =" not in fonte
        assert "PASSO_DA_VARREDURA =" not in fonte


class TestAEscolhaSobDeriva:
    """A folga que decide e a do PIOR caso sob deriva, nunca a do ponto."""

    def _escolher(self, limpa, coberta, limpa_movida, coberta_movida):
        """Duas bandas: a 0 brilha no ponto e some ao derivar; a 1 aguenta.

        As duas tabelas do gabarito sao SUBSTITUIDAS por frames montados aqui.
        Reaproveitar as de verdade nao serve: `GABARITO_LIMPAS[0]` e
        `GABARITO_COBERTAS[0]` sao o MESMO frame (`tooltip/frame_000015`, as
        linhas 8 e 9 limpas e as 0 a 7 cobertas), entao as duas populacoes
        cairiam sobre a mesma leitura montada e nao haveria o que separar.
        """
        derivas = [
            d
            for d in range(-DERIVA_CONFERIDA, DERIVA_CONFERIDA + 1)
            if d != 0
        ]
        limpas_originais = ferramenta.GABARITO_LIMPAS
        cobertas_originais = ferramenta.GABARITO_COBERTAS
        ferramenta.GABARITO_LIMPAS = (
            ("g", "limpa.png", tuple(range(LINHAS)), "n" * 60),
        )
        ferramenta.GABARITO_COBERTAS = (("g", "coberta.png", tuple(range(LINHAS))),)
        try:
            varredura = Varredura(
                candidatos=[(0, 8), (3, 11)], linhas_por_pagina=LINHAS
            )
            varredura.leituras = [
                _leitura(
                    "g",
                    "limpa.png",
                    limpa,
                    n_candidatos=2,
                    por_deriva={d: limpa_movida for d in derivas},
                ),
                _leitura(
                    "g",
                    "coberta.png",
                    coberta,
                    n_candidatos=2,
                    por_deriva={d: coberta_movida for d in derivas},
                ),
            ]
            return ferramenta.escolher_a_banda(varredura)
        finally:
            ferramenta.GABARITO_LIMPAS = limpas_originais
            ferramenta.GABARITO_COBERTAS = cobertas_originais

    def test_a_banda_do_fio_da_navalha_PERDE_para_a_mais_folgada(self) -> None:
        """O caso medido, reduzido a numeros de mentira.

        Em campo: dy[0,8) mede folga 112,7x no ponto calibrado e 0,9x quando a
        linha anda 2 px, porque a -2 px ela come a moldura da linha de cima.
        dy[3,11) mede 68,7x no ponto e SEGURA 49,3x. As duas escolhas de sonda
        que o campo derrubou foram feitas pelo primeiro numero.

        Aqui a banda 0 e a do fio da navalha (folga 100x no ponto, populacoes
        invertidas ao derivar) e a banda 1 e a folgada (folga 10x sempre). A
        escolha tem de ser a 1.
        """
        escolhida, tabela = self._escolher(
            limpa={0: 0.001, 1: 0.010},
            coberta={0: 0.100, 1: 0.100},
            limpa_movida={0: 0.500, 1: 0.010},
            coberta_movida={0: 0.100, 1: 0.100},
        )
        assert escolhida == 1
        por_coluna = {c["coluna"]: c for c in tabela}
        assert por_coluna[0]["folga"] > por_coluna[1]["folga"]
        assert not por_coluna[0]["separa_derivada"]
        assert por_coluna[1]["separa_derivada"]

    def test_nenhuma_banda_que_so_separa_no_ponto_e_aceita(self) -> None:
        """Se TODAS forem do fio da navalha, a resposta e -1 e a ferramenta PARA.

        Uma separacao que so existe quando a linha esta no pixel exato da
        calibracao nao foi medida, foi encenada. Propor limiar sobre ela e o
        que produziu 31 paginas perdidas.
        """
        escolhida, _tabela = self._escolher(
            limpa={0: 0.001, 1: 0.001},
            coberta={0: 0.100, 1: 0.100},
            limpa_movida={0: 0.500, 1: 0.500},
            coberta_movida={0: 0.100, 1: 0.100},
        )
        assert escolhida == -1

    def test_pior_limpa_ZERO_continua_descartada(self) -> None:
        """Folga infinita nao e medicao, e a recusa e mais velha que a banda."""
        escolhida, tabela = self._escolher(
            limpa={0: 0.0, 1: 0.010},
            coberta={0: 0.100, 1: 0.100},
            limpa_movida={0: 0.0, 1: 0.010},
            coberta_movida={0: 0.100, 1: 0.100},
        )
        assert escolhida == 1
        assert not {c["coluna"]: c for c in tabela}[0]["mensuravel"]


class TestAGuardaDoGabarito:
    """As tres conferencias que PARAM a ferramenta. Aqui elas sao executadas."""

    def _varredura(self, *, nome, ponta, tinta, n=1):
        g_limpo, a_limpo, _linhas, _n = GABARITO_LIMPAS[0]
        varredura = Varredura(candidatos=[(3, 11)], linhas_por_pagina=LINHAS)
        varredura.leituras = [
            _leitura(
                g_limpo,
                a_limpo,
                {0: 0.001},
                n_candidatos=n,
                ponta=ponta,
                tinta=tinta,
            )
        ]
        # O nome declarado vem da tabela, entao a montagem substitui a tabela.
        varredura.leituras[0].gravacao = g_limpo
        varredura.leituras[0].arquivo = a_limpo
        return varredura, nome

    def _com_nome(self, nome, ponta, tinta):
        """Roda a guarda com um GABARITO_LIMPAS de uma linha so, montado aqui."""
        original = ferramenta.GABARITO_LIMPAS
        g, a = "gravacao-de-teste", "frame_de_teste.png"
        ferramenta.GABARITO_LIMPAS = ((g, a, tuple(range(LINHAS)), nome),)
        try:
            varredura = Varredura(candidatos=[(3, 11)], linhas_por_pagina=LINHAS)
            varredura.leituras = [
                _leitura(g, a, {0: 0.001}, n_candidatos=1, ponta=ponta,
                         tinta=tinta)
            ]
            return ferramenta.conferir_o_gabarito_limpo(varredura, (3, 11))
        finally:
            ferramenta.GABARITO_LIMPAS = original

    def test_1_nome_curto_demais_REPROVA(self) -> None:
        """A conferencia que teria evitado 2026-08-31, na grandeza do defeito."""
        passou, diagnostico = self._com_nome(
            "Hardin's Soul Crystal Lv. 1", ponta=169, tinta=(15, 27)
        )
        assert passou is False
        assert "nao contem nome comprido" in diagnostico["motivo"]

    def test_1_o_pior_nome_conhecido_APROVA(self) -> None:
        passou, _d = self._com_nome(
            "Protecting Scroll: Enchant C-grade Weapon",
            ponta=255,
            tinta=(15, 27),
        )
        assert passou is True

    def test_2_declaracao_que_discorda_dos_pixels_REPROVA(self) -> None:
        """O erro de APONTAMENTO de 2026-08-30: prosa apontando o frame errado.

        Aqui o nome declarado tem 41 caracteres mas a tinta para em x=169 -- e
        outro frame do mesmo gabarito inka mais fundo. Declaracao e pixel
        discordando e contradicao, nao detalhe.
        """
        original = ferramenta.GABARITO_LIMPAS
        ferramenta.GABARITO_LIMPAS = (
            ("g", "a.png", tuple(range(LINHAS)),
             "Protecting Scroll: Enchant C-grade Weapon"),
            ("g", "b.png", tuple(range(LINHAS)), None),
        )
        try:
            varredura = Varredura(candidatos=[(3, 11)], linhas_por_pagina=LINHAS)
            varredura.leituras = [
                _leitura("g", "a.png", {0: 0.001}, n_candidatos=1, ponta=169),
                _leitura("g", "b.png", {0: 0.001}, n_candidatos=1, ponta=215),
            ]
            passou, diagnostico = ferramenta.conferir_o_gabarito_limpo(
                varredura, (3, 11)
            )
        finally:
            ferramenta.GABARITO_LIMPAS = original
        assert passou is False
        assert "DECLARACAO E OS PIXELS DISCORDAM" in diagnostico["motivo"]

    def test_3_banda_EM_CIMA_do_texto_REPROVA(self) -> None:
        """O defeito de 31/08 no outro eixo, e a guarda o pega no outro eixo.

        A conferencia de ALCANCE que existia antes perguntava "a tinta alcanca o
        `dx0` da sonda?". Com uma banda que usa a janela inteira em x a resposta
        e sempre sim, para qualquer nome: a pergunta virou vacua. Esta e a mesma
        pergunta no eixo em que ela ainda quer dizer alguma coisa.
        """
        passou, diagnostico = self._com_nome(
            "Protecting Scroll: Enchant C-grade Weapon",
            ponta=255,
            tinta=(4, 30),
        )
        assert passou is False
        assert "EM CIMA DO TEXTO" in diagnostico["motivo"]

    def test_3_banda_ENCOSTADA_no_texto_REPROVA(self) -> None:
        """Margem de um pixel e o formato do defeito, nao um detalhe de gosto.

        A banda vai ate dy=11 e a tinta comeca em dy=12: um pixel de folga. Foi
        exatamente assim que a sonda de 31/08 nasceu -- encostada em x=246, que
        e a ponta da tinta do nome de 40 caracteres -- e um caractere a mais a
        derrubou.
        """
        passou, diagnostico = self._com_nome(
            "Protecting Scroll: Enchant C-grade Weapon",
            ponta=255,
            tinta=(12, 30),
        )
        assert passou is False
        assert str(FOLGA_VERTICAL_MINIMA) in diagnostico["motivo"]

    def test_3_a_folga_medida_entra_no_diagnostico(self) -> None:
        """A guarda IMPRIME o numero em vez de prometer que ele existe."""
        passou, diagnostico = self._com_nome(
            "Protecting Scroll: Enchant C-grade Weapon",
            ponta=255,
            tinta=(15, 27),
        )
        assert passou is True
        assert diagnostico["folga_do_texto"] == 15 - 11
        assert diagnostico["tinta_topo"] == 15
        assert diagnostico["tinta_base"] == 27
