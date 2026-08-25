"""O aviso de manutencao do servidor: ler o banner e sobreviver a cegueira.

Este arquivo existe por causa de uma cegueira de 90 s e outra de 5 min em
2026-08-24. A causa era o servidor caindo para manutencao, e a Fase 5 aprendeu
a reconhecer o servidor DEPOIS da queda. Mas o jogo ANUNCIA a queda com 40
minutos de antecedencia, em texto, na tela — e o scanner atravessava esse
anuncio inteiro sem ver.

DISCIPLINA DESTE ARQUIVO: nenhum teste pode depender de uma leitura de OCR bem
sucedida. O Python que roda a suite NAO tem as bindings do WinRT (so o `.venv`
do usuario tem), entao o caminho "sem OCR" e o caminho PADRAO daqui. Todo teste
que precisa de texto INJETA um `ler_texto` falso — que e exatamente por que
`VigiaDeManutencao` recebe `ler_texto` por parametro.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pytest

from l2scanner.agenda import RegistroEmDisco
from l2scanner.manutencao import (
    TipoDeAvisoDeManutencao,
    chave_do_marcador,
    descrever_duracao,
    eh_banner_de_manutencao,
    interpretar_banner,
)

# Texto EXATO que o spike leu de um banner sintetico, typo do jogo incluso.
BANNER_REAL = "Server Maintence 40 minutes 26 seconds Please avoid entering instance"

HOJE = datetime(2026, 8, 25, 14, 0, 0)


def pixels():
    """Um recorte qualquer. O conteudo nao importa: o `ler_texto` e injetado."""
    return np.zeros((10, 10, 3), dtype=np.uint8)


class TestLeituraDoBanner:
    def test_o_banner_real_do_jogo_e_reconhecido_e_interpretado(self):
        assert eh_banner_de_manutencao(BANNER_REAL) is True
        assert interpretar_banner(BANNER_REAL) == timedelta(minutes=40, seconds=26)

    def test_a_grafia_correta_tambem_vale(self):
        """O jogo escreve `Maintence`; a grafia certa e `Maintenance`.

        Aceitar so uma seria apostar que o jogo nunca corrige o proprio typo.
        """
        texto = "Server Maintenance 5 minutes"
        assert eh_banner_de_manutencao(texto) is True
        assert interpretar_banner(texto) == timedelta(minutes=5)

    def test_caixa_e_espaco_nao_importam(self):
        texto = "  SERVER   MAINTENCE   26 SECONDS "
        assert eh_banner_de_manutencao(texto) is True
        assert interpretar_banner(texto) == timedelta(seconds=26)

    def test_as_confusoes_de_ocr_viram_digito(self):
        """`4O` -> 40 e `2l` -> 21: o OCR troca O/0, l/1 e S/5 o tempo todo."""
        texto = "Server Maintence 4O minutes 2l seconds"
        assert interpretar_banner(texto) == timedelta(minutes=40, seconds=21)

    def test_a_normalizacao_nao_atropela_a_lingua(self):
        """A palavra `seconds` sai INTACTA — e um token sem digito nao vira numero.

        Normalizar o texto inteiro era o caminho obvio e ERRADO: ele trocaria o
        `s` e o `o` de `seconds` por `5` e `0`, quebrando justamente a palavra
        que da sentido ao numero. E um `SO` solto viraria `50`, deixando
        qualquer palavra da tela virar duracao.
        """
        assert interpretar_banner("Server Maintenance 5 seconds") == timedelta(
            seconds=5
        )
        assert interpretar_banner("Server Maintenance SO seconds") is None

    def test_a_forma_com_horas_se_aparecer(self):
        assert interpretar_banner("Server Maintence 1 hour 5 minutes") == timedelta(
            hours=1, minutes=5
        )

    @pytest.mark.parametrize(
        "texto",
        [
            # O TESTE MAIS IMPORTANTE DO ARQUIVO. Frase REAL dos prints do
            # usuario: contem `server`, `restart` E `minutes`, e mesmo assim
            # NAO e o banner de manutencao. Um parser frouxo anunciaria uma
            # manutencao a cada vez que alguem tentasse usar um item.
            "You cannot use this item because the server will restart in a few minutes",
            "Please avoid entering instance",
            "Korzis 40 minutes",
            "",
            None,
        ],
    )
    def test_texto_que_nao_e_o_banner_nao_vira_nada(self, texto):
        assert eh_banner_de_manutencao(texto) is False

    def test_descrever_duracao_diz_o_tempo_como_esta_na_tela(self):
        """GOAL-01 pede o tempo COMO ESTA NA TELA — entao nao arredonda."""
        assert descrever_duracao(timedelta(minutes=40, seconds=26)) == (
            "40 minutos e 26 segundos"
        )
        assert descrever_duracao(timedelta(minutes=5)) == "5 minutos"
        assert descrever_duracao(timedelta(seconds=26)) == "26 segundos"
        assert "1 hora" in descrever_duracao(timedelta(hours=1, minutes=5))


class TestChaveDoMarcador:
    def test_a_chave_comeca_com_a_data_e_sobrevive_ao_podar(self, tmp_path):
        """Sem o prefixo de data o `podar()` PULA o arquivo e a pasta cresce.

        O `podar` faz `date.fromisoformat(nome.split("_", 1)[0])` e da
        `continue` quando levanta. Um marcador sem data na frente nunca seria
        apagado — o defeito silencioso que D-09 manda evitar.
        """
        registro = RegistroEmDisco(tmp_path)
        velho = chave_do_marcador(
            HOJE - timedelta(days=4), TipoDeAvisoDeManutencao.ANUNCIADA
        )
        registro.marcar(velho)
        registro.podar(hoje=HOJE.date())
        assert not (tmp_path / velho).exists()

        novo = chave_do_marcador(HOJE, TipoDeAvisoDeManutencao.ANUNCIADA)
        registro.marcar(novo)
        registro.podar(hoje=HOJE.date())
        assert (tmp_path / novo).exists()

    def test_a_chave_sai_do_momento_da_manutencao_nao_do_aviso(self):
        """E o que faz as DUAS instancias do usuario convergirem na mesma chave."""
        a = chave_do_marcador(HOJE, TipoDeAvisoDeManutencao.ANUNCIADA)
        b = chave_do_marcador(HOJE, TipoDeAvisoDeManutencao.ANUNCIADA)
        assert a == b

        faltam5 = chave_do_marcador(HOJE, TipoDeAvisoDeManutencao.FALTAM5)
        assert faltam5 != a
