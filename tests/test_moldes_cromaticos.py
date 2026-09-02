"""O SEGUNDO conjunto de moldes tem CHAVE PROPRIA, e por que ela e obrigatoria.

O DEFEITO QUE ESTA CHAVE TORNA IMPOSSIVEL
------------------------------------------
`fundir_glifos` funde por ROTULO (`{**anteriores, **desta_rodada}`), e o rotulo
`0` e o mesmo no branco e no ciano. Sem uma chave separada, uma rodada de
`calibrar-mercado.bat --so-digitos` sobre texto CIANO APAGARIA os treze moldes
BRANCOS -- calado, e no fim de uma sessao de calibracao que o usuario acharia
bem-sucedida. E os moldes brancos sao o que hoje vira dado.

Nao e um risco hipotetico: e o mesmo defeito que o CR-04 consertou no caminho
dos moldes de NOME, e que o 05-04 consertou no caminho das COLUNAS por layout.
Este arquivo e a terceira instancia da mesma licao, e a primeira em que a
protecao e ESTRUTURAL -- duas chaves nao podem colidir.

A PARIDADE DA FAIXA ZEBRADA, E POR QUE O CALIBRADOR A CONFERE
--------------------------------------------------------------
A grade e ZEBRADA: o fundo da linha alterna entre 48 e 66. A borda
antisserrilhada de um glifo fica a ~0,62 do caminho entre o fundo e o pico, e o
piso da mascara e ABSOLUTO em 180 -- entao o ciano (pico 255) cai dos DOIS
lados do piso:

    ciano sobre fundo 48:  48 + 0,62*(255-48) = 176  -> some,  `0` PARTIDO
    ciano sobre fundo 66:  66 + 0,62*(255-66) = 183  -> FICA,  `0` FECHADO

MEDIDO com o `8` CIANO REAL de `janela_tooltip_f012.png` L2 (`380,00`):

    conjunto cortado em    obs fundo 48       obs fundo 66
    fundo 48 (escuro)      OK  folga 0,4107   FALHA  folga 0,0080
    fundo 66 (claro)       OK  folga 0,2013   OK     folga 0,2174

A margem exigida e 0,03698. Um conjunto cortado sobre fundo 48 NAO conserta a
paridade que esta quebrada -- um QUINTO da folga necessaria -- e nada nele
parece errado. O usuario descobriria em campo, depois de treze recortes de
mouse. Por isso `conferir_a_paridade_do_ciano` recusa ANTES de gravar.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import l2scanner.calibrar_mercado
from l2scanner import mercado_leitura
from l2scanner.calibracao import Calibracao
from l2scanner.calibrar_mercado import (
    MercadoNaoCalibravel,
    _gravar_os_glifos,
    anel_do_zero_esta_partido,
    conferir_a_paridade_do_ciano,
    cortar_glifos,
    fundir_glifos,
)
from l2scanner.calibrar_mercado import ResultadoDaConfusao

# O `0` nas duas paridades, na forma MEDIDA. Nao sao desenhos ilustrativos: sao
# a contagem de tinta observada no pixel (12 px sobre fundo 48, 16 sobre 66).
ZERO_PARTIDO = np.array(
    [
        [0, 1, 1, 0],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [0, 1, 1, 0],
    ],
    dtype=np.uint8,
) * 255
ZERO_FECHADO = np.array(
    [
        [0, 1, 1, 0],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [0, 1, 1, 0],
    ],
    dtype=np.uint8,
) * 255


def conjunto(zero: np.ndarray) -> dict[str, np.ndarray]:
    """Onze rotulos, porque conjunto incompleto nao entra em uso."""
    moldes = {rotulo: ZERO_FECHADO.copy() for rotulo in "123456789,"}
    moldes["0"] = zero
    return moldes


# A calibracao de fixtura, que ja tem os treze moldes BRANCOS gravados. Ela e
# carregada de disco e nao construida a mao: `Calibracao` exige seis campos
# obrigatorios que nao tem nada a ver com este arquivo.
CALIBRACAO_DE_FIXTURE = (
    Path(__file__).parent / "fixtures" / "mercado" / "calibracao_de_fixture.json"
)


def calibracao() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO_DE_FIXTURE)


@pytest.fixture
def resultado_vazio() -> ResultadoDaConfusao:
    """Sem limiar sugerido: a rodada ciana nunca deve mexer no limiar."""
    return ResultadoDaConfusao(
        aprovado=True, pior_score=None, par_colidente=None, limiar_sugerido=0.9
    )


class TestAChaveCromaticaEUmaChavePROPRIA:
    """A protecao e ESTRUTURAL: duas chaves nao tem como colidir."""

    def test_a_calibracao_de_hoje_nao_tem_a_chave_e_isso_e_legitimo(self) -> None:
        """`None` nao e falta de calibracao: e "ainda nao cortei o ciano".

        E por isso a chave NAO entra em `pecas_de_calibracao_faltando`: uma
        peca cuja ausencia ja tem resposta segura (a recusa da metade B) nao
        pode aparecer na lista de faltas, sob pena de ensinar o usuario a
        ignorar a lista.
        """
        assert calibracao().mercado_templates_de_digito_cromatico is None

    def test_cortar_CIANO_nao_toca_nos_moldes_BRANCOS(
        self, resultado_vazio
    ) -> None:
        """O TESTE QUE ESTE ARQUIVO EXISTE PARA TER.

        Sem a chave separada, esta gravacao apagaria os treze brancos, porque
        `fundir_glifos` funde por rotulo e o rotulo `0` e o mesmo nas duas
        cores.
        """
        cal = calibracao()
        brancos = [{"rotulo": r, "altura": 8, "largura": 4} for r in "0123456789,"]
        cal.mercado_templates_de_digito = brancos

        cianos = conjunto(ZERO_FECHADO)
        _gravar_os_glifos(
            cal, cianos, cianos, resultado_vazio, cromatica=True
        )

        assert cal.mercado_templates_de_digito is brancos
        assert cal.mercado_templates_de_digito_cromatico is not None
        assert len(cal.mercado_templates_de_digito_cromatico) == 11

    def test_cortar_BRANCO_nao_toca_nos_moldes_CIANOS(
        self, resultado_vazio
    ) -> None:
        """A simetria importa: a protecao vale nos DOIS sentidos."""
        cal = calibracao()
        cianos = [{"rotulo": r, "altura": 8, "largura": 4} for r in "0123456789,"]
        cal.mercado_templates_de_digito_cromatico = cianos

        brancos = conjunto(ZERO_PARTIDO)
        _gravar_os_glifos(cal, brancos, brancos, resultado_vazio)

        assert cal.mercado_templates_de_digito_cromatico is cianos
        assert len(cal.mercado_templates_de_digito) == 11

    def test_a_rodada_CIANA_nao_reescreve_o_limiar_do_glifo(
        self, resultado_vazio
    ) -> None:
        """`mercado_limiar_de_glifo` e UM escalar compartilhado.

        Deixar uma calibracao OPCIONAL mexer nele faria o caminho branco -- o
        que hoje vira dado -- depender de uma rodada que pode nunca acontecer.
        """
        cal = calibracao()
        cal.mercado_limiar_de_glifo = 0.42
        cianos = conjunto(ZERO_FECHADO)
        _gravar_os_glifos(cal, cianos, cianos, resultado_vazio, cromatica=True)
        assert cal.mercado_limiar_de_glifo == 0.42

    def test_e_a_rodada_ACROMATICA_continua_reescrevendo_o_limiar(
        self, resultado_vazio
    ) -> None:
        """O controle negativo do teste acima."""
        cal = calibracao()
        cal.mercado_limiar_de_glifo = 0.42
        brancos = conjunto(ZERO_PARTIDO)
        _gravar_os_glifos(cal, brancos, brancos, resultado_vazio)
        assert cal.mercado_limiar_de_glifo == 0.9

    def test_a_chave_sobrevive_a_ida_e_volta_do_json(self, tmp_path) -> None:
        cal = calibracao()
        cal.mercado_templates_de_digito_cromatico = [
            {"rotulo": "0", "altura": 8, "largura": 4}
        ]
        arquivo = tmp_path / "calibration.json"
        cal.salvar(arquivo)
        assert Calibracao.carregar(
            arquivo
        ).mercado_templates_de_digito_cromatico == [
            {"rotulo": "0", "altura": 8, "largura": 4}
        ]


class TestAGuardaDeParidade:
    """Um conjunto ciano cortado na faixa errada custa uma mensagem, nao um farm."""

    def test_o_anel_partido_e_reconhecido_pela_linha_vazia_no_meio(self) -> None:
        assert anel_do_zero_esta_partido(ZERO_PARTIDO)
        assert not anel_do_zero_esta_partido(ZERO_FECHADO)

    def test_sem_molde_do_zero_ela_se_cala(self) -> None:
        """Quem cobra a PRESENCA dos glifos e `cobertura_dos_glifos`."""
        assert not anel_do_zero_esta_partido(None)
        assert not anel_do_zero_esta_partido(np.zeros((0, 0), dtype=np.uint8))
        assert not anel_do_zero_esta_partido(np.zeros((8, 4), dtype=np.uint8))
        conferir_a_paridade_do_ciano({})

    def test_o_conjunto_cortado_na_faixa_ESCURA_e_RECUSADO(self) -> None:
        with pytest.raises(MercadoNaoCalibravel) as erro:
            conferir_a_paridade_do_ciano(conjunto(ZERO_PARTIDO))
        # A mensagem tem de dizer ONDE cortar, e nao so que esta errado.
        assert "88" in str(erro.value)
        assert "Nada foi gravado" in str(erro.value)

    def test_e_a_recusa_acontece_ANTES_de_escrever(self, resultado_vazio) -> None:
        """Levantar depois de gravar deixaria o conjunto ruim no disco."""
        cal = calibracao()
        partido = conjunto(ZERO_PARTIDO)
        with pytest.raises(MercadoNaoCalibravel):
            _gravar_os_glifos(
                cal, partido, partido, resultado_vazio, cromatica=True
            )
        assert cal.mercado_templates_de_digito_cromatico is None

    def test_a_guarda_NAO_vale_para_o_conjunto_acromatico(
        self, resultado_vazio
    ) -> None:
        """O `0` BRANCO E um anel partido, e isso e o registro fiel do piso.

        Aplicar a guarda aos dois conjuntos recusaria a calibracao que hoje
        funciona -- a assinatura que ela procura e o estado NORMAL do branco.
        """
        cal = calibracao()
        brancos = conjunto(ZERO_PARTIDO)
        _gravar_os_glifos(cal, brancos, brancos, resultado_vazio)
        assert len(cal.mercado_templates_de_digito) == 11


class TestOLeitorSoUsaOConjuntoINTEIRO:
    """Meio conjunto cromatico falha ABERTO, e por isso vale o mesmo que nenhum."""

    def test_onze_rotulos_bastam_e_dez_nao(self) -> None:
        completo = {r: ZERO_FECHADO for r in "0123456789,"}
        assert mercado_leitura.conjunto_descreve_numeros(completo)
        for faltante in "0123456789,":
            parcial = {k: v for k, v in completo.items() if k != faltante}
            assert not mercado_leitura.conjunto_descreve_numeros(parcial), (
                faltante
            )

    def test_as_palavras_de_sufixo_nao_sao_exigidas(self) -> None:
        """`XM Coin` e `Adena` vivem ABAIXO do piso: nenhuma celula as contem."""
        completo = {r: ZERO_FECHADO for r in "0123456789,"}
        assert mercado_leitura.conjunto_descreve_numeros(completo)
        assert "XM Coin" not in mercado_leitura.GLIFOS_DO_NUMERO
        assert "Adena" not in mercado_leitura.GLIFOS_DO_NUMERO


# --------------------------------------------------------------------------
# DEBT-06 -- O MOMENTO da guarda, que ate 2026-09-01 era o errado
# --------------------------------------------------------------------------
#
# A guarda existia num lugar so: dentro de `_gravar_os_glifos`, DEPOIS dos treze
# arrastos e DEPOIS de a matriz de confusao aprovar. Duas frases do repositorio
# afirmavam que ela custava "uma mensagem, e nao uma sessao de farm" e que era
# "o que impede o esforco jogado fora" -- e em 2026-09-01 ela custou ao usuario
# TRES rodadas completas de treze recortes a mao, acertando so na terceira.
#
# O que estes casos prendem nao e a RECUSA (isso `TestAGuardaDeParidade` ja
# prendia) e sim o MOMENTO dela, medido pela unica grandeza que o usuario sente:
# QUANTOS ARRASTOS DE MOUSE ele gastou antes de ouvir "nao". A conta e de
# chamadas a `_selecionar_regiao`, que e onde o mouse dele entra.


# Os glifos sinteticos sao DESENHADOS, e nao blocos chapados. Um bloco cheio e
# um molde de variancia zero, e `matriz_de_confusao_de_glifos` o RECUSA com
# razao ("um molde chapado nao se compara com nada") -- medido: a primeira
# versao destes casos usava blocos e o modo isolado morria na matriz, e nao na
# guarda. Um teste que morre no passo errado nao mede o passo que ele nomeia.
_UM = (
    "..#.",
    "..#.",
    "..#.",
    "..#.",
    "..#.",
    "..#.",
    "..#.",
    "..#.",
    ".###",
)
_ZERO_FECHADO = (
    ".##.",
    "#..#",
    "#..#",
    "#..#",
    "#..#",
    "#..#",
    "#..#",
    "#..#",
    ".##.",
)
# A MESMA arte com o vao MEDIDO no meio: sobre fundo 48 a borda
# antisserrilhada cai abaixo do piso 180 e some, e sobram linhas inteiramente
# vazias entre o arco de cima e o de baixo. Ver a matriz no cabecalho.
_ZERO_PARTIDO = (
    ".##.",
    "#..#",
    "#..#",
    "....",
    "....",
    "#..#",
    "#..#",
    "#..#",
    ".##.",
)


def _desenhar(tela: np.ndarray, arte: tuple[str, ...], topo: int, esq: int) -> None:
    for dy, linha in enumerate(arte):
        for dx, celula in enumerate(linha):
            if celula == "#":
                tela[topo + dy, esq + dx] = 255


def _preco_ciano(zero_partido: bool, com_o_zero: bool = True) -> np.ndarray:
    """Um preco de DOIS glifos cujo `0` tem a paridade PEDIDA.

    `com_o_zero=False` troca o segundo glifo por um anel FECHADO rotulado `2`,
    para o caso em que a rodada nao corta `0` nenhum.
    """
    tela = np.zeros((45, 90, 3), dtype=np.uint8)
    _desenhar(tela, _UM, 10, 5)
    segundo = _ZERO_PARTIDO if (zero_partido and com_o_zero) else _ZERO_FECHADO
    _desenhar(tela, segundo, 10, 10)
    return tela


def _preco_de_UM_glifo(zero_partido: bool) -> np.ndarray:
    """So o `0`, para medir a recusa com UM glifo na mao e nenhum segundo."""
    tela = np.zeros((45, 90, 3), dtype=np.uint8)
    _desenhar(tela, _ZERO_PARTIDO if zero_partido else _ZERO_FECHADO, 10, 10)
    return tela


class TestAGuardaAvisaANTESDosTrezeArrastos:
    """DEBT-06: a recusa custa UM arrasto, e nao treze mais uma matriz."""

    def _armar(self, monkeypatch, pixels, respostas, cromatica, ja_gravados=None):
        """Devolve `(rodar, arrastos)`.

        A lista de arrastos vive FORA da chamada de proposito: o caso principal
        levanta, e um contador devolvido pela funcao nunca chegaria ao assert.
        """
        arrastos: list[str] = []

        def espiao(_pixels, titulo, _instrucao, _sugestao=None):
            arrastos.append(titulo)
            return (0, 0, pixels.shape[1], pixels.shape[0])

        monkeypatch.setattr(
            l2scanner.calibrar_mercado, "_selecionar_regiao", espiao
        )
        fala = iter(respostas)

        def rodar():
            return cortar_glifos(
                pixels,
                ja_gravados or {},
                ler=lambda *a, **k: next(fala),
                cromatica=cromatica,
            )

        return rodar, arrastos

    def test_o_zero_PARTIDO_e_recusado_no_PRIMEIRO_arrasto(self, monkeypatch):
        """TREZE marcacoes na fila; a recusa tem de consumir UMA.

        Se a guarda continuasse so no momento da escrita, as treze seriam
        consumidas e o `f` fecharia o laco antes de qualquer recusa -- que e
        exatamente o que o usuario viveu tres vezes em 2026-09-01.
        """
        pixels = _preco_ciano(zero_partido=True)
        respostas = ["n", "10"] * 13 + ["f"]
        rodar, arrastos = self._armar(monkeypatch, pixels, respostas, True)

        with pytest.raises(MercadoNaoCalibravel) as erro:
            rodar()

        assert len(arrastos) == 1, (
            f"a recusa saiu depois de {len(arrastos)} arrasto(s). Ela tem de "
            f"sair no PRIMEIRO: e isso, e so isso, que a faz custar uma "
            f"mensagem em vez de uma sessao de marcacao a mao."
        )
        # A mensagem tem de dizer ONDE cortar, e nao so que esta errado.
        assert "88" in str(erro.value)
        assert "Nada foi gravado" in str(erro.value)

    def test_a_recusa_sai_com_UM_glifo_na_mao_e_nenhum_segundo(self, monkeypatch):
        """O limite exato do "antes do segundo glifo".

        Um preco de UM glifo so: quando a guarda fala, `cortados` tem tamanho 1.
        Nao ha segundo glifo cortado, nem segundo arrasto.
        """
        pixels = _preco_de_UM_glifo(zero_partido=True)
        rodar, arrastos = self._armar(
            monkeypatch, pixels, ["n", "0", "n", "0", "f"], True
        )
        with pytest.raises(MercadoNaoCalibravel):
            rodar()
        assert len(arrastos) == 1

    def test_o_CONTROLE_NEGATIVO_o_zero_FECHADO_passa_e_o_laco_SEGUE(
        self, monkeypatch
    ):
        """Sem isto, uma guarda que recusasse TUDO passaria no caso acima."""
        pixels = _preco_ciano(zero_partido=False)
        rodar, arrastos = self._armar(
            monkeypatch, pixels, ["n", "10", "n", "10", "f"], True
        )
        cortados = rodar()
        assert sorted(cortados) == ["0", "1"]
        assert len(arrastos) == 2, (
            "o laco tem de SEGUIR quando a paridade esta certa — recusar aqui "
            "tornaria o corte ciano impossivel"
        )
        assert not anel_do_zero_esta_partido(cortados["0"])

    def test_a_guarda_do_LACO_nao_vale_para_a_rodada_ACROMATICA(self, monkeypatch):
        """O `0` BRANCO E um anel partido, e isso e o registro fiel do piso.

        O assert final e o discriminante: ele prova que a fixtura E recusavel.
        Sem ele, este caso passaria por nao haver o que recusar.
        """
        pixels = _preco_ciano(zero_partido=True)
        rodar, arrastos = self._armar(
            monkeypatch, pixels, ["n", "10", "f"], False
        )
        cortados = rodar()
        assert sorted(cortados) == ["0", "1"]
        assert len(arrastos) == 1
        assert anel_do_zero_esta_partido(cortados["0"]), (
            "a fixtura tem de ser mesmo um anel PARTIDO — sem isso o caso "
            "acima estaria medindo a ausencia de defeito, e nao a guarda"
        )

    def _rodar_o_modo_isolado(
        self, monkeypatch, tmp_path, pixels, respostas, cromatica
    ):
        """`_calibrar_so_digitos` de verdade, que e o UNICO caminho cromatico.

        POR QUE NAO UM `grep` NO FONTE. A primeira versao deste caso procurava
        `"cromatica=cromatica"` na fonte de `_calibrar_so_digitos` — e passou com
        o fio CORTADO, porque a mesma string aparece na chamada de
        `_gravar_os_glifos` logo abaixo. Foi vacuo, medido. Aqui a ligacao e
        exercitada: se o flag nao chegar a `cortar_glifos`, nao ha recusa.

        Nada toca `.mercado/` nem o `calibration.json` do usuario: o arquivo de
        saida e de `tmp_path` e a recusa acontece antes de qualquer `salvar`.
        """
        arrastos: list[str] = []

        def espiao(_pixels, titulo, _instrucao, _sugestao=None):
            arrastos.append(titulo)
            return (0, 0, pixels.shape[1], pixels.shape[0])

        monkeypatch.setattr(
            l2scanner.calibrar_mercado, "_selecionar_regiao", espiao
        )
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "_gravar_conferencia",
            lambda tela: tmp_path / "conf.png",
        )
        fala = iter(respostas)
        monkeypatch.setattr("builtins.input", lambda *a, **k: next(fala))

        cal = calibracao()
        args = SimpleNamespace(layout="negociacao", so_digitos=True)

        def rodar():
            return l2scanner.calibrar_mercado._calibrar_so_digitos(
                args,
                cal,
                tmp_path / "calibration.json",
                Path("frame_sintetico.png"),
                pixels,
                {},
                None,
                cromatica=cromatica,
            )

        return rodar, arrastos, cal, tmp_path / "calibration.json"

    def test_o_MODO_ISOLADO_cromatico_recusa_no_primeiro_arrasto(
        self, monkeypatch, tmp_path
    ):
        """A ligacao ponta a ponta: `--so-digitos --tinta cromatica`."""
        rodar, arrastos, cal, arquivo = self._rodar_o_modo_isolado(
            monkeypatch,
            tmp_path,
            _preco_ciano(zero_partido=True),
            ["n", "10"] * 13 + ["f"],
            cromatica=True,
        )
        with pytest.raises(MercadoNaoCalibravel) as erro:
            rodar()

        assert len(arrastos) == 1, (
            f"o modo isolado gastou {len(arrastos)} arrasto(s) antes da recusa "
            f"— o flag nao esta chegando a `cortar_glifos`"
        )
        assert "88" in str(erro.value)
        assert not arquivo.exists(), "nada pode ter sido gravado"
        assert cal.mercado_templates_de_digito_cromatico is None

    def test_o_CONTROLE_NEGATIVO_o_modo_isolado_ACROMATICO_nao_recusa(
        self, monkeypatch, tmp_path
    ):
        """Sobre os MESMOS pixels: o `0` branco partido e o estado normal.

        Sem este par, o caso acima nao distinguiria "a guarda ligou" de "o modo
        isolado quebrou por qualquer outro motivo".
        """
        rodar, arrastos, cal, arquivo = self._rodar_o_modo_isolado(
            monkeypatch,
            tmp_path,
            _preco_ciano(zero_partido=True),
            ["n", "10", "f"],
            cromatica=False,
        )
        assert rodar() == 0
        assert len(arrastos) == 1
        assert arquivo.exists(), "a rodada acromatica tem de ter GRAVADO"
        assert len(cal.mercado_templates_de_digito) == 2


class TestAGuardaDaESCRITAContinuaSendoARedeFinal:
    """A do laco e CONVENIENCIA. A da escrita e a rede, e ela ve o que a outra nao ve."""

    def test_uma_rodada_SEM_zero_passa_inteira_pela_guarda_do_laco(
        self, monkeypatch
    ):
        """O caminho que passa POR CIMA da guarda do laco, exercitado de verdade.

        A do laco ve so `cortados` — o corte DESTA rodada. Uma rodada que corta
        so glifos sem `0` atravessa o laco calada e correta, e e assim que o `0`
        partido do conjunto ANTERIOR chega a escrita.
        """
        anterior = {"0": ZERO_PARTIDO.copy()}
        pixels = _preco_ciano(zero_partido=False, com_o_zero=False)
        arrastos: list[str] = []

        def espiao(_pixels, titulo, _instrucao, _sugestao=None):
            arrastos.append(titulo)
            return (0, 0, pixels.shape[1], pixels.shape[0])

        monkeypatch.setattr(
            l2scanner.calibrar_mercado, "_selecionar_regiao", espiao
        )
        fala = iter(["n", "12", "f"])
        cortados = cortar_glifos(
            pixels, anterior, ler=lambda *a, **k: next(fala), cromatica=True
        )

        assert sorted(cortados) == ["1", "2"], "a rodada nao pode ter cortado `0`"
        assert len(arrastos) == 1, "o laco nao recusou — era esse o ponto"
        assert anel_do_zero_esta_partido(anterior["0"]), (
            "o conjunto anterior tem de estar mesmo PARTIDO, senao nao ha o que "
            "a rede final devesse pegar"
        )

    def test_e_a_guarda_da_ESCRITA_pega_esse_conjunto(self, resultado_vazio):
        """A continuacao do caso acima, com os mesmos dois lados."""
        cal = calibracao()
        anterior = {"0": ZERO_PARTIDO.copy()}
        cortados = {"1": ZERO_FECHADO.copy(), "2": ZERO_FECHADO.copy()}

        # A guarda do laco, chamada com o que o laco veria: silencio.
        conferir_a_paridade_do_ciano(cortados)

        fundidos = fundir_glifos(anterior, cortados)
        assert "0" in fundidos, "o `0` partido entra pelo conjunto ANTERIOR"

        with pytest.raises(MercadoNaoCalibravel):
            _gravar_os_glifos(
                cal, cortados, fundidos, resultado_vazio, cromatica=True
            )
        assert cal.mercado_templates_de_digito_cromatico is None

    def test_o_CONTROLE_NEGATIVO_com_o_anterior_FECHADO_a_escrita_acontece(
        self, resultado_vazio
    ):
        """Sem isto, uma escrita quebrada por qualquer motivo passaria acima."""
        cal = calibracao()
        anterior = {r: ZERO_FECHADO.copy() for r in "03456789,"}
        cortados = {"1": ZERO_FECHADO.copy(), "2": ZERO_FECHADO.copy()}
        fundidos = fundir_glifos(anterior, cortados)
        _gravar_os_glifos(
            cal, cortados, fundidos, resultado_vazio, cromatica=True
        )
        assert cal.mercado_templates_de_digito_cromatico is not None
        assert len(cal.mercado_templates_de_digito_cromatico) == 11
