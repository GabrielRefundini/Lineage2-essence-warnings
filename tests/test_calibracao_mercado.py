"""As chaves de mercado entram no calibration.json SEM invalidar o que existe.

A doutrina esta escrita em `calibracao.py:196-206` e vale literalmente aqui: o
`carregar` recusa qualquer versao diferente de `VERSAO_DO_ESQUEMA`, entao subir
para 3 por causa de campos OPCIONAIS obrigaria o usuario a recalibrar a mao um
arquivo que continua correto. As quatro chaves novas seguem o trilho do
`banner_manutencao` — campo `| None = None`, serializacao condicional no
`salvar`, `.get` no `carregar` — e este arquivo e o que prende isso.

O teste que mais importa e o do arquivo ANTIGO: `calibracao_de_referencia.json`
foi gravado antes desta funcionalidade existir e nao tem nenhuma chave de
mercado. Ele precisa carregar sem excecao e sem uma linha de migracao.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from l2scanner.calibracao import VERSAO_DO_ESQUEMA, Calibracao, CalibracaoInvalida
from l2scanner.frames import Regiao

FIXTURES = Path(__file__).parent / "fixtures"
REFERENCIA = FIXTURES / "calibracao_de_referencia.json"

# Um molde minusculo, so para o round-trip: 2x3 bytes crus em hex.
MOLDE_DE_BRINQUEDO = {"altura": 2, "largura": 3, "bytes": "0102030405f0"}

ANCORA_DE_BRINQUEDO = Regiao(esquerda=912, topo=350, largura=100, altura=28)
GEOMETRIA_DE_BRINQUEDO = {"janela_largura": 1720, "janela_altura": 1392}


@pytest.fixture
def cal_sem_mercado() -> Calibracao:
    return Calibracao.carregar(REFERENCIA)


class TestACalibracaoAntigaContinuaValendo:
    def test_a_versao_do_esquema_segue_em_2(self):
        """Subir a versao invalidaria a calibracao medida a mao do usuario.

        Se este teste cair, alguem trocou um campo opcional por uma migracao
        obrigatoria — e a conta dessa troca e o usuario recalibrar tudo.
        """
        assert VERSAO_DO_ESQUEMA == 2

    def test_um_arquivo_gravado_antes_desta_funcionalidade_carrega(self):
        """`calibracao_de_referencia.json` nao tem NENHUMA chave de mercado."""
        dados = json.loads(REFERENCIA.read_text(encoding="utf-8"))
        assert not [c for c in dados if c.startswith("mercado_")], (
            "a fixture de referencia ganhou chaves de mercado e deixou de "
            "provar o que ela existe para provar"
        )
        cal = Calibracao.carregar(REFERENCIA)  # nao pode levantar
        assert cal.versao == 2

    def test_sem_as_chaves_novas_os_quatro_campos_voltam_None(self, cal_sem_mercado):
        assert cal_sem_mercado.mercado_ancora is None
        assert cal_sem_mercado.mercado_molde_da_ancora is None
        assert cal_sem_mercado.mercado_limiar_da_ancora is None
        assert cal_sem_mercado.mercado_geometria_da_captura is None

    def test_salvar_e_recarregar_sem_mercado_nao_inventa_chave(
        self, cal_sem_mercado, tmp_path
    ):
        destino = tmp_path / "calibration.json"
        cal_sem_mercado.salvar(destino)
        devolvida = Calibracao.carregar(destino)
        assert devolvida.mercado_ancora is None
        assert devolvida.mercado_molde_da_ancora is None
        assert devolvida.mercado_limiar_da_ancora is None
        assert devolvida.mercado_geometria_da_captura is None


class TestORoundTripDasChavesNovas:
    def test_as_quatro_chaves_voltam_identicas(self, cal_sem_mercado, tmp_path):
        cal_sem_mercado.mercado_ancora = ANCORA_DE_BRINQUEDO
        cal_sem_mercado.mercado_molde_da_ancora = MOLDE_DE_BRINQUEDO
        cal_sem_mercado.mercado_limiar_da_ancora = 0.73
        cal_sem_mercado.mercado_geometria_da_captura = GEOMETRIA_DE_BRINQUEDO

        destino = tmp_path / "calibration.json"
        cal_sem_mercado.salvar(destino)
        devolvida = Calibracao.carregar(destino)

        assert devolvida.mercado_ancora == ANCORA_DE_BRINQUEDO
        assert devolvida.mercado_limiar_da_ancora == 0.73
        assert devolvida.mercado_geometria_da_captura == GEOMETRIA_DE_BRINQUEDO

    def test_o_molde_volta_byte_a_byte(self, cal_sem_mercado, tmp_path):
        """O hex e o dado; um round-trip que perde um byte perde a ancora."""
        cal_sem_mercado.mercado_molde_da_ancora = MOLDE_DE_BRINQUEDO
        destino = tmp_path / "calibration.json"
        cal_sem_mercado.salvar(destino)
        devolvida = Calibracao.carregar(destino)

        assert devolvida.mercado_molde_da_ancora == MOLDE_DE_BRINQUEDO
        assert devolvida.mercado_molde_da_ancora["bytes"] == "0102030405f0"

    def test_a_versao_gravada_continua_2_com_as_chaves_preenchidas(
        self, cal_sem_mercado, tmp_path
    ):
        cal_sem_mercado.mercado_ancora = ANCORA_DE_BRINQUEDO
        cal_sem_mercado.mercado_limiar_da_ancora = 0.73
        destino = tmp_path / "calibration.json"
        cal_sem_mercado.salvar(destino)

        dados = json.loads(destino.read_text(encoding="utf-8"))
        assert dados["versao"] == 2
        assert dados["mercado_ancora"] == ANCORA_DE_BRINQUEDO.como_dict()
        assert dados["mercado_limiar_da_ancora"] == 0.73

    def test_um_scanner_ANTIGO_recusaria_alto_e_nao_calado(self, tmp_path):
        """A recusa de versao continua sendo a defesa de entrada (T-02-02).

        Nao e sobre as chaves novas: e a garantia de que o trilho escolhido
        (campo opcional, versao congelada) nao afrouxou o portao que ja existia.
        """
        dados = json.loads(REFERENCIA.read_text(encoding="utf-8"))
        dados["versao"] = 3
        destino = tmp_path / "futuro.json"
        destino.write_text(json.dumps(dados), encoding="utf-8")

        with pytest.raises(CalibracaoInvalida, match="v3"):
            Calibracao.carregar(destino)
