"""O aviso de Tiat e conservador: um spawn, uma mensagem."""

from datetime import datetime, timedelta

import numpy as np

from l2scanner.bosses import OrigemDoTiat, VigiaDoTiat


PIXELS = np.zeros((5, 5, 3), dtype=np.uint8)
AGORA = datetime(2026, 8, 29, 12, 0)


class Leitor:
    def __init__(self, textos):
        self.textos = iter(textos)

    def __call__(self, _pixels):
        return next(self.textos)


def vigia(chat, alvo, **kwargs):
    """Cada avaliacao le chat primeiro e alvo depois."""
    textos = [valor for par in zip(chat, alvo) for valor in par]
    return VigiaDoTiat(Leitor(textos), segundos_entre_leituras=1, **kwargs)


def test_detecta_o_anuncio_no_chat():
    v = vigia(["Raid boss Tiat has appeared"], ["Orc"])

    aviso = v.avaliar(PIXELS, PIXELS, AGORA)

    assert aviso is not None
    assert aviso.origem is OrigemDoTiat.CHAT
    assert "chat" in aviso.texto.lower()


def test_detecta_quando_o_alvo_vira_tiat_mesmo_sem_anuncio_no_chat():
    v = vigia(["mensagem comum"], ["Tiat"])

    aviso = v.avaliar(PIXELS, PIXELS, AGORA)

    assert aviso is not None
    assert aviso.origem is OrigemDoTiat.ALVO
    assert "alvo" in aviso.texto.lower()


def test_sinais_juntos_geram_uma_mensagem_combinada():
    v = vigia(["TIAT apareceu"], ["Tiat"])

    aviso = v.avaliar(PIXELS, PIXELS, AGORA)

    assert aviso is not None
    assert aviso.origem is OrigemDoTiat.CHAT_E_ALVO


def test_trocas_classicas_do_ocr_ainda_encontram_o_nome():
    v = vigia(["T1A7 apareceu"], ["nenhum"])

    assert v.avaliar(PIXELS, PIXELS, AGORA) is not None


def test_persistencia_do_chat_ou_alvo_nunca_spamma():
    v = vigia(["Tiat", "Tiat", "Tiat"], ["Tiat", "Tiat", "Tiat"])

    avisos = [
        v.avaliar(PIXELS, PIXELS, AGORA + timedelta(seconds=segundo))
        for segundo in range(3)
    ]

    assert sum(aviso is not None for aviso in avisos) == 1


def test_so_rearma_depois_de_duas_leituras_limpas():
    v = vigia(
        ["Tiat", "", "", "Tiat"], ["", "", "", ""],
        leituras_limpas_para_rearmar=2,
    )

    avisos = [
        v.avaliar(PIXELS, PIXELS, AGORA + timedelta(seconds=segundo))
        for segundo in range(4)
    ]

    assert [a is not None for a in avisos] == [True, False, False, True]


def test_falha_do_ocr_nao_derruba_o_vigia():
    def explode(_pixels):
        raise RuntimeError("OCR indisponivel")

    v = VigiaDoTiat(explode)

    assert v.avaliar(PIXELS, PIXELS, AGORA) is None
