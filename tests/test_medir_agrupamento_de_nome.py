"""A varredura do agrupamento de nome: os rotulos, o corte, e a refutacao de A8.

Tudo aqui roda sobre fixtures VERSIONADAS em `tests/fixtures/mercado/`, e nunca
sobre `recordings/` nem sobre o `calibration.json` — os dois sao gitignored e
nao vem de clone limpo, entao um teste que dependesse deles ficaria verde nesta
maquina e amarelo em toda outra. A varredura que PRODUZ os numeros
(`tools/medir_agrupamento_de_nome.py --gravar`) e outra coisa e roda no checkout
principal, no `.venv`, porque so la existem as gravacoes e o motor de OCR.

    leituras_de_nome.json       as 3.511 linhas LIMPAS das 8 gravacoes, com o
                                nome lido pelas duas escalas (2x e 3x). E o
                                despejo da propria varredura, e e o que permite
                                REPRODUZIR o corte sem motor de OCR nenhum.
    nome_linha0_f000.png        324x45, coluna do nome de
                                063752-mercado-aberto/frame_000000 linha 0,
                                `+6 Agathion Alpha Hunter Sealed` — a linha do
                                gabarito de encanto
    nome_linha0_f010.png        idem de pagina-cheia/frame_000010 linha 0,
                                `Earth Spirit Evolution Stone`
    nome_sob_tooltip_f015.png   idem de tooltip/frame_000015 linha 0, COM a
                                tooltip por cima. Medido, o recorte de coluna
                                sozinho devolve `'Common King It Weight: O'`
                                (2x) e `'Common King I, Weight : O'` (3x) — o
                                nome do item some e o texto da TOOLTIP entra no
                                lugar (T-02-11)

OS NUMEROS QUE ESTE ARQUIVO PRENDE, E DE ONDE VIERAM
=====================================================
Varredura de 2026-08-30 sobre as 8 gravacoes do censo, 415 frames com painel
aberto, 3.511 linhas limpas (951 recusadas pela sonda de oclusao do 02-02):

    mercado_corte_de_similaridade   0,894737   = min(precisa agrupar)
    mercado_piso_de_similaridade    0,883732   = meio do vao ate max(separar)
    vao entre as populacoes         0,022010
    fusoes conhecidas no corte      1 par, `B-grade Gemstone` x `C-grade Gemstone`

A REFUTACAO DE A8 (a fonte da assinatura por MOLDE) TAMBEM E PRESA AQUI. Com a
posicao do digito dada DE FORA, o molde acerta 9 de 9 contra o gabarito. Com a
regra que a producao teria de usar — cada run sozinho, digito quando passa no
piso e na margem — ele acerta 0 de 10 e devolve `7655` onde a resposta e `6`. O
conjunto de 13 moldes NAO TEM CLASSE DE REJEICAO: nao ha molde de letra, entao
toda letra e forcada sobre o digito mais parecido e algumas passam no piso.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibrar_mercado import segmentar_glifos
from l2scanner.identidade import mascara_de_texto

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "mercado"
ALTURA_DA_LINHA = 45


def _carregar_a_ferramenta(nome: str):
    """`tools/` nao e pacote, entao o import vem do caminho do arquivo."""
    caminho = RAIZ / "tools" / (nome + ".py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    assert spec and spec.loader, f"nao carreguei {caminho}"
    modulo = importlib.util.module_from_spec(spec)
    # Registrar ANTES de executar: `@dataclass` resolve as anotacoes por
    # `sys.modules[cls.__module__]`, e sem isto ele encontra None.
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


ferramenta = _carregar_a_ferramenta("medir_agrupamento_de_nome")

DISTANCIA_MAXIMA_DE_RUIDO = ferramenta.DISTANCIA_MAXIMA_DE_RUIDO
GABARITO_DE_ENCANTO = ferramenta.GABARITO_DE_ENCANTO
GRAVACOES_DO_CENSO = ferramenta.GRAVACOES_DO_CENSO
LeituraDeNome = ferramenta.LeituraDeNome
assinatura_de_molde_da_linha = ferramenta.assinatura_de_molde_da_linha
censo_do_conflito = ferramenta.censo_do_conflito
distancia_de_edicao = ferramenta.distancia_de_edicao
fusoes_no_corte = ferramenta.fusoes_no_corte
pares_que_precisam_agrupar = ferramenta.pares_que_precisam_agrupar
pares_que_precisam_separar = ferramenta.pares_que_precisam_separar
pontuar_runs = ferramenta.pontuar_runs
propor_corte_e_piso = ferramenta.propor_corte_e_piso
recorte_de_runs = ferramenta.recorte_de_runs
series_duplicadas_projetadas = ferramenta.series_duplicadas_projetadas
vocabulario_de_consenso = ferramenta.vocabulario_de_consenso

from l2scanner.mercado_catalogo import EntradaDoCatalogo  # noqa: E402

# Os numeros MEDIDOS pela varredura de 2026-08-30. Eles vivem aqui como
# constantes de teste, e nao lidos do `calibration.json`: o arquivo e estado de
# maquina e um teste que o lesse afirmaria o que quer que estivesse gravado.
CORTE_MEDIDO = 0.8947368421052632
PISO_MEDIDO = 0.8837320574162679
PIOR_SEPARAR_MEDIDO = 0.8727272727272727
LINHAS_MEDIDAS = 3511
CONFLITOS_MEDIDOS = 311

# O piso e a margem de LEITURA que o 02-02 mediu sobre 55.342 glifos das colunas
# de NUMERO. Eles entram aqui para provar o que NAO fazem: separar digito de
# letra na coluna do NOME.
PISO_DE_LEITURA = 0.4698309302330017
MARGEM_DE_LEITURA = 0.03698354959487915

ROTULOS_DOS_PRECOS = ("100,00", "3,00", "18,90", "7,50", "18,00", "2,45")
ROTULO_DO_UNITARIO = "6,00"


@pytest.fixture(scope="module")
def leituras() -> list:
    """As 3.511 linhas limpas, resgatadas para JSON pela propria varredura."""
    caminho = FIXTURES / "leituras_de_nome.json"
    assert caminho.is_file(), f"fixture ausente: {caminho}"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return [
        LeituraDeNome(
            d["gravacao"], d["arquivo"], d["linha"], d["texto2x"], d["texto3x"]
        )
        for d in dados
    ]


def _ler(nome: str) -> np.ndarray:
    pixels = cv2.imread(str(FIXTURES / nome))
    assert pixels is not None, f"fixture ausente: {FIXTURES / nome}"
    return pixels


def _bandas(nome: str, quantas: int) -> list:
    imagem = _ler(nome)
    return [
        imagem[i * ALTURA_DA_LINHA : (i + 1) * ALTURA_DA_LINHA]
        for i in range(quantas)
    ]


def _glifos_da_banda(banda: np.ndarray) -> list:
    faixa, runs = segmentar_glifos(banda)
    if faixa is None:
        return []
    topo, base = faixa
    mascara = (mascara_de_texto(banda) * 255).astype(np.uint8)
    return [mascara[topo:base, a:b].copy() for a, b in runs]


@pytest.fixture(scope="module")
def moldes() -> dict:
    """Os 11 glifos de um caractere, recortados das fixtures de PRECO.

    Pelo mesmo motivo de `test_medir_leitura_de_glifo.py`: os 13 moldes de
    verdade moram no `calibration.json`, que e estado de maquina. E o ponto do
    teste que os usa e justamente que moldes cortados de uma coluna de NUMERO
    nao classificam texto de NOME — entao corta-los do numero e o experimento.
    """
    conjunto: dict = {}
    for banda, rotulo in zip(_bandas("glifos_precos_f010.png", 6), ROTULOS_DOS_PRECOS):
        for indice, glifo in enumerate(_glifos_da_banda(banda)):
            conjunto.setdefault(rotulo[indice], glifo)
    for indice, glifo in enumerate(_glifos_da_banda(_ler("glifos_unitario_f010.png"))):
        conjunto.setdefault(ROTULO_DO_UNITARIO[indice], glifo)
    return conjunto


class TestOConjuntoDeMedicao:
    def test_sao_as_OITO_gravacoes_nomeadas_do_censo(self):
        assert len(GRAVACOES_DO_CENSO) == 8
        assert all(n.startswith("20260828-") for n in GRAVACOES_DO_CENSO)

    def test_a_lista_nao_e_duplicada_e_sim_importada(self):
        """Duas varreduras medindo conjuntos diferentes e o modo de falha calado.

        A afirmacao e sobre o FONTE, e nao sobre identidade de objeto: carregar
        `medir_oclusao` de novo por caminho cria uma tupla nova, entao um `is`
        aqui passaria a testar o carregador em vez da duplicacao.
        """
        oclusao = _carregar_a_ferramenta("medir_oclusao")
        assert GRAVACOES_DO_CENSO == oclusao.GRAVACOES_DO_CENSO
        fonte = (RAIZ / "tools" / "medir_agrupamento_de_nome.py").read_text(
            encoding="utf-8"
        )
        for pasta in GRAVACOES_DO_CENSO:
            if pasta == ferramenta.FRAME_DO_GABARITO[0]:
                # Esta aparece uma vez, e nao como lista: e o frame do gabarito.
                assert fonte.count(f'"{pasta}"') == 1
                continue
            assert f'"{pasta}"' not in fonte, pasta

    def test_a_pre_voo_e_as_outras_sete_ficam_de_fora(self):
        assert "20260827-225521-pre-voo" not in GRAVACOES_DO_CENSO
        assert "inv3" not in GRAVACOES_DO_CENSO
        assert len(ferramenta.MOTIVO_PARA_IGNORAR) == 8


class TestADistanciaDeEdicao:
    def test_identicas_dao_zero(self):
        assert distancia_de_edicao("Common Valakas Doll", "Common Valakas Doll") == 0

    def test_um_caractere_trocado_da_um(self):
        assert distancia_de_edicao("Lv. I", "Lv. 1") == 1
        assert distancia_de_edicao("B-grade Gemstone", "C-grade Gemstone") == 1

    def test_dois_caracteres_dao_dois(self):
        assert distancia_de_edicao("Common Valakas Chll", "Common Valakas Doll") == 2

    def test_o_nome_comido_pela_oclusao_passa_do_limite(self):
        assert (
            distancia_de_edicao(
                "Common Mafia Leader Luciano Doll", "Cohi nn Mafia Leader Luciano Doll"
            )
            > DISTANCIA_MAXIMA_DE_RUIDO
        )


class TestOsDoisRotulosDaMedicao:
    def test_o_vocabulario_de_consenso_sao_os_nomes_confirmados(self, leituras):
        consenso = vocabulario_de_consenso(leituras)
        assert "Earth Spirit Evolution Stone" in consenso
        assert "+6 Agathion Alpha Hunter Sealed" in consenso
        assert len(consenso) == 50

    def test_precisa_agrupar_exclui_a_discordancia_GRANDE(self, leituras):
        """Discordancia acima de 2 caracteres e erro de METODO: a linha cai."""
        consenso = vocabulario_de_consenso(leituras)
        agrupam, por_metodo, _ = pares_que_precisam_agrupar(leituras, True, consenso)
        assert por_metodo, "o material tem erro de metodo e ele precisa aparecer"
        for par in agrupam:
            assert distancia_de_edicao(par.a, par.b) <= DISTANCIA_MAXIMA_DE_RUIDO

    def test_precisa_agrupar_exclui_o_par_em_que_os_DOIS_lados_falharam(
        self, leituras
    ):
        """O `'\\ufffdano'` x `'-ano'`: duas leituras falhadas nao ensinam o corte."""
        consenso = vocabulario_de_consenso(leituras)
        agrupam, _, sem_consenso = pares_que_precisam_agrupar(
            leituras, True, consenso
        )
        assert sem_consenso
        assert min(par.score for par in sem_consenso) < min(
            par.score for par in agrupam
        )
        for par in agrupam:
            assert par.a in consenso or par.b in consenso

    def test_precisa_separar_so_aceita_linha_de_CONSENSO(self, leituras):
        """Uma leitura que so uma escala produziu nao prova que sao dois itens."""
        consenso = vocabulario_de_consenso(leituras)
        separam, _ = pares_que_precisam_separar(leituras, True)
        for par in separam:
            assert par.a in consenso and par.b in consenso

    def test_precisa_separar_manda_o_par_de_ATE_dois_caracteres_para_indecidivel(
        self, leituras
    ):
        separam, indecidiveis = pares_que_precisam_separar(leituras, True)
        for par in separam:
            assert distancia_de_edicao(par.a, par.b) > DISTANCIA_MAXIMA_DE_RUIDO
        for par in indecidiveis:
            assert 0 < distancia_de_edicao(par.a, par.b) <= DISTANCIA_MAXIMA_DE_RUIDO

    def test_a_trava_de_digitos_tira_da_mesa_o_par_que_ela_ja_separa(self, leituras):
        """Com a trava, `Lv. 1` x `Lv. 3` nunca chega a similaridade."""
        _, sem_trava = pares_que_precisam_separar(leituras, False)
        _, com_trava = pares_que_precisam_separar(leituras, True)
        assert len(com_trava) < len(sem_trava)


class TestACorteEOPiso:
    def test_o_corte_e_o_piso_sao_REPRODUZIVEIS_a_partir_da_fixture(self, leituras):
        """Sem motor de OCR, num clone limpo: os mesmos dois numeros."""
        consenso = vocabulario_de_consenso(leituras)
        agrupam, _, _ = pares_que_precisam_agrupar(leituras, True, consenso)
        separam, _ = pares_que_precisam_separar(leituras, True)
        diag = propor_corte_e_piso(agrupam, separam)
        assert diag["corte"] == pytest.approx(CORTE_MEDIDO)
        assert diag["piso"] == pytest.approx(PISO_MEDIDO)
        assert diag["pior_separar"] == pytest.approx(PIOR_SEPARAR_MEDIDO)

    def test_as_populacoes_INTEIRAS_ficam_do_lado_certo(self, leituras):
        """Nao e uma afirmacao sobre extremos: e sobre os 4.170 pares."""
        consenso = vocabulario_de_consenso(leituras)
        agrupam, _, _ = pares_que_precisam_agrupar(leituras, True, consenso)
        separam, _ = pares_que_precisam_separar(leituras, True)
        assert [par for par in agrupam if par.score < CORTE_MEDIDO] == []
        assert [par for par in separam if par.score >= PISO_MEDIDO] == []

    def test_o_piso_e_o_MEIO_do_vao_e_nao_o_maximo_de_separar(self, leituras):
        """A refutacao preservada: com `piso = max(separar)`, o pior par de
        'precisa separar' cai EXATAMENTE no piso e e descartado toda vez —
        `'Wind Spirit Evolution Stone'` nunca entraria no catalogo."""
        assert PISO_MEDIDO > PIOR_SEPARAR_MEDIDO
        assert PISO_MEDIDO < CORTE_MEDIDO
        assert PISO_MEDIDO == pytest.approx((PIOR_SEPARAR_MEDIDO + CORTE_MEDIDO) / 2)

    def test_a_faixa_cinzenta_existe(self):
        """D-06: sem vao entre piso e corte nao ha onde a duvida cair."""
        assert CORTE_MEDIDO > PISO_MEDIDO

    def test_a_sobreposicao_impede_a_proposta(self):
        Par = ferramenta.Par
        agrupam = [Par("a", "b", 0.80, "x")]
        separam = [Par("c", "d", 0.90, "y")]
        diag = propor_corte_e_piso(agrupam, separam)
        assert diag["sobrepostos"]
        assert "SOBREPOEM" in diag["motivo"]

    def test_populacao_vazia_nao_propoe_nada(self):
        diag = propor_corte_e_piso([], [])
        assert diag["corte"] is None


class TestAsFusoesQueOCorteProduz:
    def test_o_corte_funde_EXATAMENTE_um_par_do_vocabulario_confirmado(
        self, leituras
    ):
        """`B-grade Gemstone` x `C-grade Gemstone`, 0,9375. UM caractere.

        A trava de digitos nao alcanca este par: a diferenca e uma LETRA de
        grade, e as duas assinaturas sao vazias. E a janela quebrada conhecida
        deste corte, e ela fica presa por teste em vez de esquecida.
        """
        consenso = vocabulario_de_consenso(leituras)
        fusoes = fusoes_no_corte(consenso, CORTE_MEDIDO)
        assert len(fusoes) == 1
        score, a, b = fusoes[0]
        assert {a, b} == {"B-grade Gemstone", "C-grade Gemstone"}
        assert score == pytest.approx(0.9375)

    def test_um_corte_mais_alto_nao_resolve_sem_perder_o_que_precisa_agrupar(
        self, leituras
    ):
        """Acima de 0,9375 a fusao some — e leva junto pares que devem agrupar."""
        consenso = vocabulario_de_consenso(leituras)
        agrupam, _, _ = pares_que_precisam_agrupar(leituras, True, consenso)
        assert fusoes_no_corte(consenso, 0.94) == []
        perdidos = [par for par in agrupam if par.score < 0.94]
        assert perdidos, "subir o corte tem um custo, e ele precisa ser visivel"


class TestOCensoDoConflito:
    def test_o_numero_de_linhas_que_D02_e_D03_matam_juntas(self, leituras):
        censo = censo_do_conflito(leituras)
        assert censo["n_linhas"] == LINHAS_MEDIDAS
        assert censo["n_conflitos"] == CONFLITOS_MEDIDOS

    def test_o_conflito_e_o_Lv_I_contra_o_Lv_1(self, leituras):
        censo = censo_do_conflito(leituras)
        assinaturas = {(a, b) for _, a, b in censo["conflitos"]}
        assert ("", "1") in assinaturas

    def test_ha_frame_em_que_a_PAGINA_INTEIRA_morre(self, leituras):
        censo = censo_do_conflito(leituras)
        piores = [
            frame
            for frame, linhas in censo["por_frame"].items()
            if len(linhas) == censo["linhas_por_frame"][frame]
            and len(linhas) == 10
        ]
        assert piores, "a perda de pagina inteira e o custo que decide o portao"


class TestAsSeriesDuplicadas:
    def _catalogo(self, *nomes) -> dict:
        from l2scanner.mercado_catalogo import assinatura_por_ocr, chave_da_serie

        saida = {}
        for nome in nomes:
            assinatura = assinatura_por_ocr(nome)
            chave = chave_da_serie(nome, assinatura)
            saida[chave] = EntradaDoCatalogo(chave, nome, assinatura)
        return saida

    def test_Lv_I_e_Lv_1_colapsam(self):
        catalogo = self._catalogo(
            "Hardin's Soul Crystal Lv. I", "Hardin's Soul Crystal Lv. 1"
        )
        grupos = series_duplicadas_projetadas(catalogo, CORTE_MEDIDO)
        assert len(grupos) == 1
        assert len(grupos[0]) == 2

    def test_Lv_1_e_Lv_3_NAO_colapsam(self):
        catalogo = self._catalogo(
            "Hardin's Soul Crystal Lv. 1", "Hardin's Soul Crystal Lv. 3"
        )
        assert series_duplicadas_projetadas(catalogo, CORTE_MEDIDO) == []

    def test_o_encanto_diferente_NAO_e_duplicata(self):
        """Punir a rota por separar `+2 X` de `+4 X` seria puni-la por acertar."""
        catalogo = self._catalogo(
            "+2 Agathion Alpha Hunter Sealed", "+4 Agathion Alpha Hunter Sealed"
        )
        assert series_duplicadas_projetadas(catalogo, CORTE_MEDIDO) == []

    def test_a_caixa_da_inicial_nem_chega_a_virar_DUAS_series(self):
        """`D-grade Crystal` e `D-grade crystal` colidem antes, na propria chave.

        O slug de `chave_da_serie` e minusculo, entao as duas grafias produzem a
        MESMA chave e a duplicata nunca nasce. Medido ao escrever este teste, que
        primeiro afirmou "colapsam em 1 grupo" e estava errado: nao ha grupo
        porque nao ha dois. A protecao esta uma camada antes do que eu supus.
        """
        catalogo = self._catalogo("D-grade Crystal", "D-grade crystal")
        assert len(catalogo) == 1
        assert series_duplicadas_projetadas(catalogo, CORTE_MEDIDO) == []


class TestARefutacaoDeA8:
    """A fonte da assinatura por MOLDE, presa por teste sobre pixels reais."""

    def test_a_faixa_do_nome_INTEIRO_e_mais_alta_que_a_de_um_digito_sozinho(self):
        """A causa mecanica: a faixa compartilhada e esticada pelas LETRAS."""
        recorte = _ler("nome_linha0_f000.png")
        faixa_inteira, runs = segmentar_glifos(recorte)
        assert faixa_inteira is not None and len(runs) > 2
        so_o_digito = recorte_de_runs(recorte, runs, 1, 2)
        faixa_do_digito, _ = segmentar_glifos(so_o_digito)
        altura_inteira = faixa_inteira[1] - faixa_inteira[0]
        altura_do_digito = faixa_do_digito[1] - faixa_do_digito[0]
        assert altura_do_digito < altura_inteira

    def test_com_a_posicao_dada_de_fora_o_molde_LE_o_digito_do_encanto(self, moldes):
        """9 de 9 contra o gabarito — mas so porque alguem disse qual run e."""
        recorte = _ler("nome_linha0_f000.png")
        _, runs = segmentar_glifos(recorte)
        pontuados = pontuar_runs(recorte_de_runs(recorte, runs, 1, 2), moldes)
        assert pontuados and pontuados[0][0] == GABARITO_DE_ENCANTO[0] == "6"

    def test_a_regra_de_PRODUCAO_nao_devolve_o_digito_do_encanto(self, moldes):
        """0 de 10 no gabarito: sem classe de rejeicao, letra vira digito.

        Esta e a refutacao de A8, e ela e o argumento que a Task 2 poe na mesa.
        """
        recorte = _ler("nome_linha0_f000.png")
        assinatura, aprovados = assinatura_de_molde_da_linha(
            recorte, moldes, PISO_DE_LEITURA, MARGEM_DE_LEITURA
        )
        assert assinatura != "6"
        assert len(aprovados) > 1, "ha mais de um run passando, e so um e digito"

    def test_o_nome_SEM_encanto_nenhum_ainda_produz_digito(self, moldes):
        """Falso positivo puro: nao ha digito na tela e o molde le um."""
        recorte = _ler("nome_linha0_f010.png")
        assinatura, _ = assinatura_de_molde_da_linha(
            recorte, moldes, PISO_DE_LEITURA, MARGEM_DE_LEITURA
        )
        assert assinatura, "'Earth Spirit Evolution Stone' nao tem digito nenhum"

    def test_recorte_de_runs_recusa_faixa_degenerada(self):
        recorte = _ler("nome_linha0_f000.png")
        _, runs = segmentar_glifos(recorte)
        assert recorte_de_runs(recorte, runs, 2, 2) is None
        assert recorte_de_runs(recorte, runs, 0, len(runs) + 1) is None
        assert recorte_de_runs(recorte, [], 0, 1) is None

    def test_pontuar_runs_nao_levanta_em_recorte_vazio(self, moldes):
        assert pontuar_runs(None, moldes) is None
        assert pontuar_runs(np.zeros((0, 0, 3), dtype=np.uint8), moldes) is None

    def test_sem_molde_de_um_caractere_nao_ha_o_que_pontuar(self):
        recorte = _ler("nome_linha0_f000.png")
        assert pontuar_runs(recorte, {}) is None


class TestOVazamentoDaTooltip:
    """T-02-11: o recorte de COLUNA sozinho nao protege o nome."""

    def test_a_fixture_do_vazamento_existe_e_tem_a_forma_da_coluna(self):
        coberta = _ler("nome_sob_tooltip_f015.png")
        limpa = _ler("nome_linha0_f010.png")
        assert coberta.shape == limpa.shape == (45, 324, 3)

    def test_a_tooltip_APAGA_texto_da_mascara_em_vez_de_acrescentar(self):
        """A medicao contrariou a suposicao, e o registro fica.

        Eu supus que a tooltip ACRESCENTARIA glifo — ela escreve por cima, entao
        haveria mais texto. MEDIDO: a mascara de brilho (`V > 180`) ve 152 pixels
        de texto na linha coberta contra 213 na limpa, e 24 runs contra 28. A
        tooltip e SEMITRANSPARENTE: ela nao escreve por cima do nome, ela o
        MISTURA e o derruba abaixo do corte de brilho.

        E por isso que ela e pior que uma janela opaca. O motor de molde perde o
        nome CALADO — menos glifo, nenhum sinal de erro — enquanto o OCR ainda
        devolve texto plausivel: medido no mesmo recorte,
        `'Common King It Weight: O'` (2x) e `'Common King I, Weight : O'` (3x),
        em que `Weight:` e da TOOLTIP e nao do nome. Nome de item plausivel e
        errado e o incidente das 27 mortes falsas um nivel acima, e nenhuma das
        duas leituras se recusa sozinha. Quem recusa e a sonda de fundo.
        """
        coberta = mascara_de_texto(_ler("nome_sob_tooltip_f015.png"))
        limpa = mascara_de_texto(_ler("nome_linha0_f010.png"))
        assert int(coberta.sum()) < int(limpa.sum())

    def test_a_segmentacao_da_linha_coberta_acha_MENOS_runs(self):
        _, runs_cobertos = segmentar_glifos(_ler("nome_sob_tooltip_f015.png"))
        _, runs_limpos = segmentar_glifos(_ler("nome_linha0_f010.png"))
        assert len(runs_cobertos) < len(runs_limpos)

    def test_o_recorte_de_COLUNA_sozinho_nao_denuncia_a_cobertura(self):
        """T-02-11: nada no recorte diz "estou coberta". Ele so tem menos texto.

        Menos texto tambem e o que uma linha de nome curto produz, entao a
        contagem de glifo nao serve de sinal. A recusa tem de vir da SONDA DE
        FUNDO (D-14), medida no 02-02 e aplicada no 02-04 — nunca da confianca
        da leitura.
        """
        _, runs_cobertos = segmentar_glifos(_ler("nome_sob_tooltip_f015.png"))
        _, runs_do_encanto = segmentar_glifos(_ler("nome_linha0_f000.png"))
        assert len(runs_cobertos) < len(runs_do_encanto)


class TestAsLeiturasVersionadas:
    def test_a_fixture_traz_a_varredura_inteira(self, leituras):
        assert len(leituras) == LINHAS_MEDIDAS

    def test_as_oito_gravacoes_estao_representadas(self, leituras):
        assert {le.gravacao for le in leituras} == set(GRAVACOES_DO_CENSO)

    def test_nenhuma_leitura_vazia_entrou(self, leituras):
        assert all(le.texto2x and le.texto3x for le in leituras)

    def test_a_ordem_e_deterministica(self, leituras):
        assert [le.origem for le in leituras] == sorted(le.origem for le in leituras)
