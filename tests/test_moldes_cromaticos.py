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

import numpy as np
import pytest

from l2scanner import mercado_leitura
from l2scanner.calibracao import Calibracao
from l2scanner.calibrar_mercado import (
    MercadoNaoCalibravel,
    _gravar_os_glifos,
    anel_do_zero_esta_partido,
    conferir_a_paridade_do_ciano,
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
