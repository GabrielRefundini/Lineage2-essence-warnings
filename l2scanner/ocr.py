"""Ler texto da tela com o motor de OCR que ja vem no Windows 11.

POR QUE ESTE MODULO EXISTE ISOLADO
==================================

O Windows 11 tem um motor de OCR embutido (`Windows.Media.Ocr`), gratuito,
offline e ja instalado — zero instalador, zero modelo para baixar. Mas as
bindings Python do WinRT sao MODULARES desde set/2023: sao seis pacotes
separados, e eles simplesmente nao estao no `.venv` de quem nao rodou o
`vigiar-party.bat` depois desta atualizacao.

O RECURSO DE MANUTENCAO E OPCIONAL. O SCANNER NAO E.

Um `import winrt` no topo de um modulo que o scanner sempre carrega faria o
produto INTEIRO morrer no arranque por causa de um recurso que o usuario nem
pediu. Por isso: este e o unico arquivo do projeto que conhece WinRT, o import
mora DENTRO das funcoes, e a ausencia das bindings desliga o recurso — nunca o
produto.

E o mesmo desenho de `montar_despachante`: tenta, degrada, avisa alto, e deixa
o scanner subir.
"""

from __future__ import annotations

import asyncio
import logging

import cv2
import numpy as np

log = logging.getLogger(__name__)

# Quanto ampliar o recorte antes de mandar para o OCR.
#
# Fonte de UI de jogo e pequena e estilizada, e ampliar antes do OCR e a
# recomendacao da propria pesquisa de stack deste projeto. A 0,2 Hz (uma
# leitura a cada 5 s) o custo de um resize e irrelevante — e a diferenca entre
# ler `40 minutes` e ler `4O rninutes` nao e.
ESCALA = 3

# O idioma do banner. O jogo escreve em ingles, e `en-US` esta presente em
# praticamente todo Windows 11 (o usuario tem `en-us` e `pt-br` em
# C:\Windows\OCR, conferido no spike).
IDIOMA = "en-US"

SEM_BINDINGS = (
    "As bibliotecas de OCR do Windows nao estao instaladas neste ambiente.\n"
    "  Conserto: rode o vigiar-party.bat uma vez — ele reinstala sozinho\n"
    "  (ou, na mao: pip install -r requirements.txt)."
)

SEM_MOTOR = (
    "O Windows nao devolveu um motor de OCR utilizavel.\n"
    "  Conserto: confira se a pasta C:\\Windows\\OCR tem a pasta en-us; se nao\n"
    "  tiver, instale o idioma Ingles (EUA) em Configuracoes > Hora e idioma."
)

# Calculado UMA vez e guardado. `_CHECADO` separado de `_MOTIVO` porque None em
# `_MOTIVO` significa "esta tudo certo", e sem a segunda variavel nao daria para
# distinguir isso de "ainda nao perguntei".
_CHECADO = False
_MOTIVO: str | None = None
_MOTOR = None


def _resetar_cache() -> None:
    """So para os testes: devolve o modulo ao estado de quem nunca perguntou."""
    global _CHECADO, _MOTIVO, _MOTOR
    _CHECADO = False
    _MOTIVO = None
    _MOTOR = None


def _checar() -> None:
    """Descobre PREGUICOSAMENTE se da para usar o OCR.

    Preguicosamente porque importar este modulo nao pode custar o import do
    WinRT: quem so carrega o scanner e nunca liga o recurso nao deve pagar nada
    — nem tempo, nem risco de um import estranho derrubar o arranque.
    """
    global _CHECADO, _MOTIVO, _MOTOR
    if _CHECADO:
        return
    _CHECADO = True

    try:
        from winrt.windows.globalization import Language
        from winrt.windows.media.ocr import OcrEngine
    except Exception as erro:  # ImportError, e o que mais o WinRT inventar
        log.debug("bindings de OCR ausentes: %s", erro)
        _MOTIVO = SEM_BINDINGS
        return

    try:
        motor = OcrEngine.try_create_from_language(Language(IDIOMA))
        if motor is None:
            # Sem o pacote de idioma pedido, tenta o que o usuario ja tem.
            motor = OcrEngine.try_create_from_user_profile_languages()
    except Exception as erro:
        log.debug("falha ao criar o motor de OCR: %s", erro)
        motor = None

    if motor is None:
        _MOTIVO = SEM_MOTOR
        return

    # Guardado em modulo: criar o motor a cada 5 s seria desperdicio puro.
    _MOTOR = motor


def disponivel() -> bool:
    """Da para ler texto da tela nesta maquina?"""
    _checar()
    return _MOTIVO is None


def motivo_indisponivel() -> str | None:
    """Por que nao da, e COMO CONSERTAR. None quando esta tudo certo.

    O texto carrega o conserto de proposito: o usuario nao e desenvolvedor, e
    um aviso que diz "OCR indisponivel" e o deixa exatamente onde estava e
    ruido, nao aviso.
    """
    _checar()
    return _MOTIVO


def ler_texto(pixels) -> str | None:
    """O texto que o OCR viu no recorte, ou None. NUNCA levanta.

    Nunca levanta porque roda DENTRO do tick de captura. Uma excecao aqui
    pararia o scanner de olhar a party — e a proxima morte real passaria
    despercebida, que e o unico defeito que este projeto trata como
    inaceitavel.

    A guarda contra recorte vazio vem ANTES de tudo: um array de altura zero
    viraria uma excecao la dentro do WinRT em vez de um None limpo.
    """
    if pixels is None:
        return None
    if getattr(pixels, "size", 0) == 0:
        return None

    if not disponivel():
        return None

    try:
        return _reconhecer(pixels)
    except Exception as erro:
        log.debug("OCR falhou neste recorte: %s", erro)
        return None


def _reconhecer(pixels: np.ndarray) -> str | None:
    """O caminho do WinRT que o spike provou. Nao redescobrir — reproduzir."""
    ampliado = cv2.resize(
        pixels, None, fx=ESCALA, fy=ESCALA, interpolation=cv2.INTER_CUBIC
    )
    ok, codificado = cv2.imencode(".png", ampliado)
    if not ok:
        return None
    return asyncio.run(_reconhecer_async(codificado.tobytes()))


async def _reconhecer_async(png: bytes) -> str | None:
    """PNG em memoria -> SoftwareBitmap -> OcrEngine.

    O desvio pelo PNG existe porque `SoftwareBitmap` nao aceita um buffer BGR
    cru sem uma dança de formatos; deixar o `BitmapDecoder` fazer o trabalho e
    o caminho curto que o spike exercitou com sucesso.
    """
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

    stream = InMemoryRandomAccessStream()
    escritor = DataWriter(stream)
    escritor.write_bytes(png)
    await escritor.store_async()
    await escritor.flush_async()
    stream.seek(0)

    decodificador = await BitmapDecoder.create_async(stream)
    bitmap = await decodificador.get_software_bitmap_async()

    resultado = await _MOTOR.recognize_async(bitmap)
    return resultado.text if resultado is not None else None
