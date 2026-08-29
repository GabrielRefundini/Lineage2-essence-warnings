"""O corte de glifos: a metade PURA, afirmada contra pixels REAIS do jogo.

Este arquivo prende a tecnica inteira do plano 01-05 sem que uma janela abra.
Tudo aqui roda sobre duas fixtures RESGATADAS de uma gravacao de verdade
(`recordings/20260828-060622-mercado-pagina-cheia/frame_000010.png`), e nunca
sobre `recordings/` — a pasta e gitignored e nao vem de clone limpo, entao um
teste que dependesse dela ficaria verde nesta maquina e amarelo em toda outra.

    tests/fixtures/mercado/glifos_precos_f010.png     240x45 px, coluna Total
        `100,00`, `3,00`, `18,90`, `7,50`, `18,00`, `2,45` — nove dos dez
        digitos, mais a virgula
    tests/fixtures/mercado/glifos_unitario_f010.png    30x40 px, Unit price
        `6,00` — o unico `6` do frame

Juntas elas dao os ONZE glifos do conjunto fechado: `0`-`9` e a virgula. Sao so
digitos: nenhum nome de personagem, nenhuma linha de chat, nenhum nome de item.

A CONVENCAO DE RECORTE E CONTRATO, E ESTA PRESA AQUI
----------------------------------------------------
`segmentar_glifos` devolve UMA faixa de linhas COMPARTILHADA por todo o
retangulo marcado, e cada glifo sai dessa mesma faixa com os seus proprios
limites de coluna. Recortar cada glifo justo na PROPRIA altura deixaria a
virgula com 3 px e o digito com 8, jogando fora a posicao vertical relativa —
que e exatamente o que distingue uma virgula (baixa) de um digito (altura
cheia).

Isso nao e detalhe de gosto: os numeros da matriz de confusao MUDAM com a
convencao, e sem ela presa por teste o proximo mantenedor ajusta o recorte ate
as asserções fecharem, o que e teste circular. Por isso
`test_a_faixa_de_linhas_e_COMPARTILHADA...` afirma os 9 px nas SETE marcacoes.

O QUE NAO E CONTRATO, DE PROPOSITO
-----------------------------------
QUAL par e o pior. Ele muda de convencao para convencao — medido em tres
convencoes durante a revisao deste plano — e prende-lo transformaria um detalhe
de recorte em promessa. O que se afirma e a RELACAO (mascara vence cinza por
pelo menos 0.08, verdade nas tres convencoes medidas) mais a FAIXA de valores
que a convencao declarada produz.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibrar_mercado import (
    COLISAO_MAXIMA_ENTRE_GLIFOS,
    _alinhar_por_preenchimento,
    _par_incalculavel,
    matriz_de_confusao_de_glifos,
    segmentar_glifos,
)
from l2scanner.identidade import mascara_de_texto
from l2scanner.mercado_visao import glifos_de_calibracao, glifos_para_calibracao

FIXTURES = Path(__file__).parent / "fixtures" / "mercado"
PRECOS = FIXTURES / "glifos_precos_f010.png"
UNITARIO = FIXTURES / "glifos_unitario_f010.png"

# O que cada faixa de 45 px da fixture de precos contem, de cima para baixo.
# Conferido com o olho na propria imagem antes de virar numero aqui.
ROTULOS_DOS_PRECOS = ("100,00", "3,00", "18,90", "7,50", "18,00", "2,45")
ROTULO_DO_UNITARIO = "6,00"
ALTURA_DA_LINHA = 45

# A faixa de linhas MEDIDA, igual nas sete marcacoes das duas fixtures.
ALTURA_DA_FAIXA = 9


def _ler(caminho: Path) -> np.ndarray:
    pixels = cv2.imread(str(caminho))
    assert pixels is not None, f"nao decodifiquei a fixture {caminho}"
    return pixels


def _bandas_dos_precos() -> list[np.ndarray]:
    """As seis faixas de preco, uma por linha da grade (passo de 45 px)."""
    precos = _ler(PRECOS)
    return [
        precos[i * ALTURA_DA_LINHA : (i + 1) * ALTURA_DA_LINHA]
        for i in range(len(ROTULOS_DOS_PRECOS))
    ]


def _recortar(banda: np.ndarray, binaria: bool) -> dict[str, np.ndarray]:
    """Os glifos de UMA marcacao, na convencao linha-justa compartilhada."""
    faixa, runs = segmentar_glifos(banda)
    assert faixa is not None
    topo, base = faixa
    if binaria:
        fonte = (mascara_de_texto(banda) * 255).astype(np.uint8)
    else:
        fonte = cv2.cvtColor(banda, cv2.COLOR_BGR2GRAY)
    return {i: fonte[topo:base, a:b].copy() for i, (a, b) in enumerate(runs)}


def _conjunto_dos_onze(binaria: bool) -> dict[str, np.ndarray]:
    """Os 11 glifos reais, montados das duas fixtures pelos rotulos conhecidos.

    O primeiro corte de cada rotulo vence: `0` aparece sete vezes nas fixtures e
    e o mesmo desenho em todas, entao guardar o primeiro nao perde nada.
    """
    conjunto: dict[str, np.ndarray] = {}
    for banda, rotulo in zip(_bandas_dos_precos(), ROTULOS_DOS_PRECOS):
        for indice, glifo in _recortar(banda, binaria).items():
            conjunto.setdefault(rotulo[indice], glifo)
    for indice, glifo in _recortar(_ler(UNITARIO), binaria).items():
        conjunto.setdefault(ROTULO_DO_UNITARIO[indice], glifo)
    return conjunto


def _pior_par(conjunto: dict[str, np.ndarray]) -> float:
    resultado = matriz_de_confusao_de_glifos(conjunto)
    assert resultado.rodou
    return resultado.pior_score


class TestASegmentacaoContraPixelsReais:
    """A tecnica inteira: se ela regredir, estes testes ficam vermelhos.

    Sao a assercao mais valiosa do plano — contam glifos em celulas de preco de
    um jogo de verdade, e nao numa imagem sintetica que o proprio teste desenhou
    do jeito que o codigo espera.
    """

    def test_cada_preco_da_fixture_devolve_exatamente_os_glifos_do_rotulo(self):
        esperado = [len(rotulo) for rotulo in ROTULOS_DOS_PRECOS]
        assert esperado == [6, 4, 5, 4, 5, 4]  # `100,00`, `3,00`, ...

        obtido = [len(segmentar_glifos(b)[1]) for b in _bandas_dos_precos()]
        assert obtido == esperado, (
            f"a segmentacao devolveu {obtido} glifos, e os rotulos pedem "
            f"{esperado}. Medido em campo: 8 de 8 celulas de preco reais."
        )

    def test_o_unitario_devolve_os_quatro_glifos_de_6_virgula_00(self):
        _faixa, runs = segmentar_glifos(_ler(UNITARIO))
        assert len(runs) == len(ROTULO_DO_UNITARIO) == 4

    def test_a_virgula_do_unitario_e_o_segundo_run_e_mede_1_px(self):
        _faixa, runs = segmentar_glifos(_ler(UNITARIO))
        inicio, fim = runs[1]  # `6` `,` `0` `0`
        assert fim - inicio == 1

    def test_a_faixa_de_linhas_e_COMPARTILHADA_e_mede_9_px_nas_sete_marcacoes(
        self,
    ):
        """A convencao de recorte, presa contra as duas fixtures.

        Sem este teste o executor escolhe a propria convencao, mede outros
        numeros de matriz, e ajusta o recorte ate as asserções fecharem.
        """
        marcacoes = _bandas_dos_precos() + [_ler(UNITARIO)]
        assert len(marcacoes) == 7

        for indice, marcacao in enumerate(marcacoes):
            faixa, runs = segmentar_glifos(marcacao)
            assert faixa is not None, f"marcacao {indice} sem faixa"
            topo, base = faixa
            assert base - topo == ALTURA_DA_FAIXA, (
                f"marcacao {indice}: faixa de {base - topo} px, medido 9"
            )
            # E todo glifo dela sai com essa mesma altura: e o que preserva a
            # posicao vertical relativa que separa virgula de digito.
            for inicio, fim in runs:
                recorte = marcacao[topo:base, inicio:fim]
                assert recorte.shape[0] == ALTURA_DA_FAIXA

    def test_as_larguras_ficam_entre_1_e_6_px(self):
        for banda in _bandas_dos_precos() + [_ler(UNITARIO)]:
            _faixa, runs = segmentar_glifos(banda)
            for inicio, fim in runs:
                assert 1 <= fim - inicio <= 6

    def test_a_virgula_de_3_virgula_00_mede_1_px_e_o_4_de_2_virgula_45_mede_6(
        self,
    ):
        bandas = _bandas_dos_precos()
        _f, runs = segmentar_glifos(bandas[1])  # `3,00`
        assert runs[1][1] - runs[1][0] == 1
        _f, runs = segmentar_glifos(bandas[5])  # `2,45`
        assert runs[2][1] - runs[2][0] == 6

    def test_as_formas_do_conjunto_completo_sao_9x4_9x6_e_9x1(self):
        formas = {r: g.shape for r, g in _conjunto_dos_onze(binaria=True).items()}
        assert formas[","] == (9, 1)
        assert formas["4"] == (9, 6)
        for digito in "01235678 9".replace(" ", ""):
            if digito == "4":
                continue
            assert formas[digito] == (9, 4), digito

    def test_recorte_vazio_devolve_faixa_nula_e_lista_vazia_sem_levantar(self):
        faixa, runs = segmentar_glifos(np.zeros((0, 0, 3), dtype=np.uint8))
        assert faixa is None
        assert runs == []

    def test_recorte_sem_nenhum_pixel_de_texto_devolve_faixa_nula_e_vazia(self):
        escuro = np.zeros((20, 30, 3), dtype=np.uint8)
        faixa, runs = segmentar_glifos(escuro)
        assert faixa is None
        assert runs == []


class TestAMatrizDeConfusaoDosGlifos:
    """O conjunto real e separavel — e a ferramenta MEDE isso, nao chuta."""

    def test_o_conjunto_real_dos_onze_glifos_APROVA_nas_duas_representacoes(self):
        for binaria in (True, False):
            resultado = matriz_de_confusao_de_glifos(_conjunto_dos_onze(binaria))
            assert resultado.rodou
            assert resultado.aprovado, resultado.pior_score

    def test_a_mascara_separa_MELHOR_que_o_cinza_por_pelo_menos_0_08(self):
        """A conclusao DURAVEL: a relacao, nao o numero.

        Medido em tres convencoes de recorte diferentes durante a revisao do
        plano — banda completa 0.9020/0.7858, linha-justa por glifo
        0.8003/0.6953, linha-justa compartilhada 0.8434/0.7171. A mascara vence
        em todas, por 0.10 a 0.13. E a relacao que sobrevive a outra maquina,
        outra skin e outra resolucao; o valor absoluto nao.
        """
        cinza = _pior_par(_conjunto_dos_onze(binaria=False))
        mascara = _pior_par(_conjunto_dos_onze(binaria=True))
        assert cinza - mascara >= 0.08, (
            f"cinza {cinza:.4f} contra mascara {mascara:.4f}: a margem caiu "
            f"abaixo de 0.08, sinal de marcacao frouxa"
        )

    def test_o_pior_par_cai_na_faixa_que_a_convencao_declarada_produz(self):
        """A faixa, e NUNCA o nome do par.

        O par muda com a convencao de recorte (medido: `5` x `6` na mascara sob
        esta convencao, `0` x `8` no cinza) e prende-lo transformaria um detalhe
        de recorte em contrato.
        """
        assert 0.65 <= _pior_par(_conjunto_dos_onze(binaria=True)) <= 0.75
        assert 0.80 <= _pior_par(_conjunto_dos_onze(binaria=False)) <= 0.90

    def test_dois_glifos_quase_identicos_fazem_a_matriz_RECUSAR_nomeando_o_par(
        self,
    ):
        base = np.zeros((9, 4), dtype=np.uint8)
        base[2:7, 1:3] = 255
        gemeo = base.copy()
        gemeo[8, 3] = 255  # um pixel de diferenca: quase identicos

        resultado = matriz_de_confusao_de_glifos({"0": base, "8": gemeo})
        assert not resultado.aprovado
        assert set(resultado.par_colidente or ()) == {"0", "8"}
        assert resultado.limiar_sugerido is None, (
            "de um conjunto recusado nao se deriva limiar — ele iria para o "
            "calibration.json como se fosse medido"
        )

    def test_com_menos_de_dois_glifos_NAO_afirma_score_nem_deriva_limiar(self):
        """A licao do CR-03, descida ao caminho dos glifos."""
        for conjunto in ({}, {"7": np.zeros((9, 4), dtype=np.uint8)}):
            resultado = matriz_de_confusao_de_glifos(conjunto)
            assert resultado.aprovado
            assert not resultado.rodou
            assert resultado.pior_score is None
            assert resultado.limiar_sugerido is None


class TestOsQuatroZerosLEGITIMOS:
    """A armadilha que quase recusou o conjunto que a fase existe para produzir.

    `casamento_da_ancora` devolve um float PELADO cujo `0.0` esta sobrecarregado
    em quatro saidas: recorte vazio, molde maior que o alvo, desvio abaixo de
    `1e-6`, e correlacao GENUINAMENTE nula. O conjunto correto de 11 glifos tem
    quatro zeros do quarto tipo — e eles sao a MELHOR separacao que o conjunto
    tem, com desvios entre 70 e 125, cinco ordens de grandeza acima do piso.

    Uma implementacao que decidisse "o par foi mensuravel?" testando
    `score == 0.0` classificaria os quatro como nao-mensuraveis e RECUSARIA o
    conjunto correto. E este teste que mantem compativeis os dois criterios do
    plano — "aprova nas duas representacoes" e "par incalculavel faz recusar".
    """

    PARES_ZERO = ((",", "0"), (",", "6"), (",", "9"), ("0", "7"))

    def test_os_quatro_pares_medem_zero_na_mascara(self):
        conjunto = _conjunto_dos_onze(binaria=True)
        matriz = matriz_de_confusao_de_glifos(conjunto).matriz
        for par in self.PARES_ZERO:
            assert matriz[par] == 0.0, f"{par} deixou de medir 0.0: {matriz[par]}"

    def test_eles_entram_na_matriz_como_MEDICAO_e_o_conjunto_segue_aprovado(self):
        resultado = matriz_de_confusao_de_glifos(_conjunto_dos_onze(binaria=True))
        assert resultado.aprovado
        for par in self.PARES_ZERO:
            assert par in resultado.matriz
            assert par not in resultado.pares_incalculaveis

    def test_os_dois_lados_de_cada_zero_tem_desvio_muito_acima_do_piso(self):
        """Nenhum deles e degenerado — o zero e descorrelacao de verdade."""
        conjunto = _conjunto_dos_onze(binaria=True)
        for x, y in self.PARES_ZERO:
            a, b = _alinhar_por_preenchimento(conjunto[x], conjunto[y])
            assert a.astype(np.float32).std() > 1.0
            assert b.astype(np.float32).std() > 1.0
            assert not _par_incalculavel(a, b)

    def test_em_tons_de_cinza_nao_ha_zero_nenhum(self):
        """Os quatro sao fenomeno da MASCARA, nao da amostra."""
        matriz = matriz_de_confusao_de_glifos(_conjunto_dos_onze(False)).matriz
        assert [v for v in matriz.values() if v == 0.0] == []

    def test_o_score_nao_e_um_piso_ele_fica_negativo(self):
        """Mais uma razao para `0.0` nao servir de sentinela: nao e o minimo."""
        matriz = matriz_de_confusao_de_glifos(_conjunto_dos_onze(False)).matriz
        assert min(matriz.values()) < 0.0


class TestOParRealmenteIncalculavel:
    """Uma comparacao que NAO aconteceu nao e uma comparacao sem colisao."""

    def test_molde_uniforme_e_classificado_pelas_PRE_CONDICOES_e_faz_RECUSAR(
        self,
    ):
        conjunto = _conjunto_dos_onze(binaria=True)
        conjunto["chapado"] = np.full((9, 4), 255, dtype=np.uint8)  # desvio zero

        resultado = matriz_de_confusao_de_glifos(conjunto)
        assert not resultado.aprovado, (
            "um par que nao pode ser medido nao pode aprovar por omissao"
        )
        assert resultado.pares_incalculaveis
        assert all("chapado" in par for par in resultado.pares_incalculaveis)
        for par in resultado.pares_incalculaveis:
            assert par not in resultado.matriz

    def test_molde_vazio_tambem_e_incalculavel(self):
        vazio = np.zeros((0, 0), dtype=np.uint8)
        digito = np.zeros((9, 4), dtype=np.uint8)
        digito[2:7, 1:3] = 255
        assert _par_incalculavel(vazio, digito)
        assert _par_incalculavel(digito, vazio)

        resultado = matriz_de_confusao_de_glifos({"0": digito, "vazio": vazio})
        assert not resultado.aprovado

    def test_molde_maior_que_o_alvo_tambem_e_incalculavel(self):
        """A terceira saida `0.0` de `casamento_da_ancora`.

        O alinhamento por preenchimento normalmente impede que ela aconteca —
        os dois lados saem do mesmo tamanho. O guard segue conferido aqui,
        diretamente, para que ele nao possa ser removido por parecer morto.
        """
        pequeno = np.zeros((9, 4), dtype=np.uint8)
        pequeno[2:7, 1:3] = 255
        grande = np.zeros((9, 6), dtype=np.uint8)
        grande[2:7, 1:5] = 255
        assert _par_incalculavel(pequeno, grande)

    def test_desvio_abaixo_do_piso_e_incalculavel(self):
        chapado = np.full((9, 4), 7, dtype=np.uint8)
        digito = np.zeros((9, 4), dtype=np.uint8)
        digito[2:7, 1:3] = 255
        assert _par_incalculavel(chapado, digito)


class TestOAlinhamentoEPorPREENCHIMENTO:
    """Cortar ao menor comum mede outra coisa — e mede para o lado errado."""

    def test_a_virgula_contra_o_2_fica_abaixo_de_0_30(self):
        """Medido: cerca de 0.19 com preenchimento, 0.50 com corte.

        O corte reduz todo par que envolva a virgula a UMA coluna, e comparar um
        digito de 4 px pela sua primeira coluna nao e comparar o digito. O erro
        anda na direcao de similaridade FABRICADA, justamente sobre o glifo cuja
        confusao e mais cara.
        """
        matriz = matriz_de_confusao_de_glifos(_conjunto_dos_onze(True)).matriz
        assert matriz[(",", "2")] < 0.30

    def test_o_preenchimento_iguala_as_formas_sem_descartar_coluna(self):
        virgula = np.full((9, 1), 255, dtype=np.uint8)
        quatro = np.full((9, 6), 255, dtype=np.uint8)
        a, b = _alinhar_por_preenchimento(virgula, quatro)
        assert a.shape == b.shape == (9, 6)
        assert int(a.sum()) == int(virgula.sum())  # nada foi jogado fora
        assert int(b.sum()) == int(quatro.sum())


class TestARotaDosNOMESNaoMudou:
    """`matriz_de_confusao`, `_alinhar` e a constante deles ficam intocados.

    Os dois caminhos nascem lado a lado de proposito: a watchlist e do usuario e
    muda a cada edicao do `config.toml`; o conjunto de glifos e fixo pela fonte
    do jogo. Uma constante unica faria o afrouxamento de um viajar para o outro.
    """

    def test_a_constante_dos_glifos_e_SEPARADA_da_constante_dos_nomes(self):
        from l2scanner import calibrar_mercado

        assert (
            calibrar_mercado.COLISAO_MAXIMA_ENTRE_GLIFOS
            is not calibrar_mercado.COLISAO_MAXIMA_ENTRE_TEMPLATES
        ) or True  # floats iguais podem ser o mesmo objeto; o que importa e o nome
        fonte = Path(calibrar_mercado.__file__).read_text(encoding="utf-8")
        assert "COLISAO_MAXIMA_ENTRE_GLIFOS = " in fonte
        assert "COLISAO_MAXIMA_ENTRE_TEMPLATES = " in fonte
        assert "COLISAO_MAXIMA_ENTRE_GLIFOS = COLISAO_MAXIMA_ENTRE_TEMPLATES" not in (
            fonte
        ), "aliasar as duas faria o afrouxamento de um conjunto viajar para o outro"

    def test_a_constante_dos_glifos_fica_acima_do_pior_par_medido(self):
        assert _pior_par(_conjunto_dos_onze(True)) < COLISAO_MAXIMA_ENTRE_GLIFOS


class TestOEmpacotamentoDosGlifos:
    """Ida e volta pelo `calibration.json`, com os guards de forma."""

    def test_ida_e_volta_devolve_arrays_identicos_para_os_onze_glifos(self):
        original = _conjunto_dos_onze(binaria=True)
        voltou = glifos_de_calibracao(glifos_para_calibracao(original))

        assert set(voltou) == set(original)
        for rotulo, molde in original.items():
            assert np.array_equal(voltou[rotulo], molde), rotulo

    def test_o_empacotado_traz_rotulo_altura_e_largura_ao_lado_do_molde(self):
        dados = glifos_para_calibracao(_conjunto_dos_onze(binaria=True))
        assert len(dados) == 11
        for item in dados:
            assert set(item) == {"glifo", "altura", "largura", "molde"}
            assert item["altura"] == ALTURA_DA_FAIXA

    def test_EDICAO_MANUAL_de_UMA_COPIA_da_forma_e_recusada(self):
        """O alcance honesto deste guard, e nada alem dele.

        Os campos irmaos `altura`/`largura` sao REDUNDANCIA, nao fonte
        independente: um recorte de glifo nao carrega coordenada nenhuma (e por
        isso ele pode ser cortado de qualquer frame). O que se pega e alguem
        editando UMA das duas copias no `calibration.json` — caminho real, ja
        que `molde_de_hex` trata o arquivo como entrada nao confiavel. O que NAO
        se pega e uma transposicao coerente, com as duas copias trocadas juntas;
        essa quem pega e o guard de CONJUNTO.
        """
        dados = glifos_para_calibracao(_conjunto_dos_onze(binaria=True))
        dados[3]["altura"] = dados[3]["altura"] + 1  # so a copia irma mudou

        with pytest.raises(ValueError, match="[Rr]ecalibre"):
            glifos_de_calibracao(dados)

    def test_altura_divergente_da_dominante_do_CONJUNTO_e_recusada_nomeando(self):
        """O unico guard com fonte independente neste caminho.

        Todos os glifos de uma calibracao saem da mesma faixa compartilhada —
        medido: 9 px nas sete marcacoes. Um item transposto no meio de um
        conjunto de `(9,N)` e detectado pelos VIZINHOS.
        """
        conjunto = _conjunto_dos_onze(binaria=True)
        conjunto["7"] = conjunto["7"].T.copy()  # (9,4) -> (4,9), coerente
        dados = glifos_para_calibracao(conjunto)

        with pytest.raises(ValueError, match="'7'"):
            glifos_de_calibracao(dados)

    def test_lista_vazia_e_None_devolvem_dicionario_vazio(self):
        assert glifos_de_calibracao(None) == {}
        assert glifos_de_calibracao([]) == {}


class TestEntradaNaoConfiavel:
    """O `calibration.json` pode ter sido editado a mao ou gravado errado."""

    @pytest.fixture
    def dados(self) -> list[dict]:
        return glifos_para_calibracao(_conjunto_dos_onze(binaria=True))

    def test_item_sem_rotulo_levanta_explicado(self, dados):
        del dados[0]["glifo"]
        with pytest.raises(ValueError, match="[Rr]ecalibre"):
            glifos_de_calibracao(dados)

    def test_rotulo_vazio_levanta_explicado(self, dados):
        dados[0]["glifo"] = ""
        with pytest.raises(ValueError, match="[Rr]ecalibre"):
            glifos_de_calibracao(dados)

    def test_rotulo_repetido_levanta_explicado(self, dados):
        dados[1]["glifo"] = dados[0]["glifo"]
        with pytest.raises(ValueError, match="repetid"):
            glifos_de_calibracao(dados)

    def test_molde_faltando_levanta_explicado(self, dados):
        del dados[2]["molde"]
        with pytest.raises(ValueError, match="[Rr]ecalibre"):
            glifos_de_calibracao(dados)

    def test_bytes_de_tamanho_errado_levantam_explicado(self, dados):
        dados[2]["molde"]["bytes"] = dados[2]["molde"]["bytes"][:-4]
        with pytest.raises(ValueError, match="[Rr]ecalibre"):
            glifos_de_calibracao(dados)

    def test_item_que_nao_e_objeto_levanta_explicado(self, dados):
        dados[0] = ["nao", "sou", "objeto"]
        with pytest.raises(ValueError, match="[Rr]ecalibre"):
            glifos_de_calibracao(dados)


def test_as_duas_fixtures_existem_e_tem_a_forma_medida():
    """Guard de resgate: se alguem recortar de novo, tem de bater com o medido."""
    assert _ler(PRECOS).shape == (240, 45, 3)
    assert _ler(UNITARIO).shape == (30, 40, 3)
    assert PRECOS.stat().st_size + UNITARIO.stat().st_size < 8 * 1024


def test_o_conjunto_montado_das_fixtures_cobre_os_ONZE_glifos():
    assert set(_conjunto_dos_onze(binaria=True)) == set("0123456789,")


def test_a_matriz_compara_todo_par_uma_vez_so():
    conjunto = _conjunto_dos_onze(binaria=True)
    esperado = len(list(itertools.combinations(conjunto, 2)))
    assert len(matriz_de_confusao_de_glifos(conjunto).matriz) == esperado == 55
