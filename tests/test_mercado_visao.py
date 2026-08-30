"""O molde do CABECALHO DE COLUNA, desempacotado como ENTRADA NAO CONFIAVEL.

`cabecalho_de_calibracao` e irma de `glifos_de_calibracao` (mesmo arquivo,
mesma estrutura) e existe pelo mesmo motivo: o `calibration.json` e um arquivo
que o proprio modulo chama de editavel, e um molde corrompido nunca casa com
nada. So que aqui o preco e maior — este molde e o PORTAO DE LAYOUT (D-11).
Um molde silenciosamente errado nao le a coluna errada: ele recusa TODA pagina,
para sempre, sem uma linha de erro dizendo por que.

As tres invariantes copiadas da irma, e prendidas aqui:
  (a) `None`/vazio devolve `None` — feature OFF, nunca erro;
  (b) toda mensagem de recusa termina no CONSERTO ("Recalibre...");
  (c) `bool` excluido explicitamente do `int`.

Nada aqui abre janela, le disco de gravacao ou depende de `recordings/`: os
moldes sao montados no proprio teste, byte a byte.
"""

from __future__ import annotations

import numpy as np
import pytest

from l2scanner.mercado_visao import cabecalho_de_calibracao


def _cabecalho(altura: int = 2, largura: int = 3, **mudancas) -> dict:
    bytes_ = bytes(range(altura * largura)).hex()
    base = {
        "layout": "negociacao",
        "dy": -32,
        "altura": altura,
        "largura": largura,
        "bytes": bytes_,
        "corte_de_brilho": 210,
    }
    base.update(mudancas)
    return base


class TestAAusenciaEFeatureOFF:
    """Uma instalacao que nunca calibrou o cabecalho sobe igual."""

    @pytest.mark.parametrize("vazio", [None, {}])
    def test_none_e_dict_vazio_devolvem_None_sem_levantar(self, vazio):
        assert cabecalho_de_calibracao(vazio) is None

    def test_o_que_nao_e_objeto_e_recusado(self):
        with pytest.raises(ValueError, match="Recalibre"):
            cabecalho_de_calibracao([1, 2, 3])


class TestODesempacotamento:
    def test_o_molde_volta_com_a_forma_declarada(self):
        molde = cabecalho_de_calibracao(_cabecalho(altura=2, largura=3))
        assert isinstance(molde, np.ndarray)
        assert molde.shape == (2, 3)
        assert molde.dtype == np.uint8
        assert molde.tolist() == [[0, 1, 2], [3, 4, 5]]


class TestAsRecusas:
    @pytest.mark.parametrize("altura,largura", [(0, 3), (2, 0), (-2, -3)])
    def test_dimensao_nao_positiva_e_recusada(self, altura, largura):
        dados = _cabecalho()
        dados["altura"], dados["largura"] = altura, largura
        with pytest.raises(ValueError, match="Recalibre"):
            cabecalho_de_calibracao(dados)

    @pytest.mark.parametrize("campo", ["altura", "largura", "dy"])
    def test_booleano_nao_passa_por_inteiro(self, campo):
        """`bool` e subclasse de `int` e passaria por um isinstance ingenuo."""
        dados = _cabecalho(**{campo: True})
        with pytest.raises(ValueError, match="Recalibre"):
            cabecalho_de_calibracao(dados)

    def test_bytes_em_contagem_errada_recusa_dizendo_quantos_faltam(self):
        """ANTES do reshape: um reshape sobre dimensao mentida e molde errado."""
        dados = _cabecalho(altura=2, largura=3, bytes="0102")
        with pytest.raises(ValueError, match="Recalibre") as erro:
            cabecalho_de_calibracao(dados)
        texto = str(erro.value)
        assert "6" in texto, texto
        assert "2" in texto, texto

    def test_layout_ausente_e_recusado(self):
        """O layout E o que este molde afirma; sem ele o casamento nao decide."""
        dados = _cabecalho()
        dados["layout"] = ""
        with pytest.raises(ValueError, match="Recalibre"):
            cabecalho_de_calibracao(dados)

    def test_corte_de_brilho_fora_de_0_a_255_e_recusado(self):
        with pytest.raises(ValueError, match="Recalibre"):
            cabecalho_de_calibracao(_cabecalho(corte_de_brilho=999))

    def test_bytes_que_nao_sao_hex_recusam_limpo(self):
        with pytest.raises(ValueError, match="Recalibre"):
            cabecalho_de_calibracao(_cabecalho(bytes="zz"))
