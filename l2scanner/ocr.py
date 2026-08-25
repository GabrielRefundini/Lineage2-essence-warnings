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

# DUAS ESCALAS, E ELAS EXISTEM PORQUE A PRECISAO NAO E MONOTONICA (D-d).
#
# ESTA TABELA SUBSTITUI UMA MEDICAO ANTERIOR QUE FOI REFUTADA. O registro da
# refutacao fica aqui de proposito: este projeto documenta numero medido, e um
# numero que caiu precisa dizer que caiu, senao ele volta na proxima leitura.
#
# A medicao antiga dizia "1x acerta, 2x erra" e foi o que escolheu o 1x como
# escala de deteccao. Ela tinha sido feita na imagem INTEIRA e com
# pre-processamento MANUAL, ANTES de a conversao para cinza (D-a), a guarda
# estrutural (D-b) e a tolerancia (D-c) existirem. Refeita com o codigo de
# hoje, sobre DUAS imagens reais, o resultado se inverte e se estabiliza:
#
#     escala   fixture 360x135   screenshot 385x285   custo (fixture/screenshot)
#     1x       None              None                 52 / 19 ms
#     2x       0:40:26           0:40:26              19 / 44 ms
#     3x       0:40:26           0:40:26              28 / 58 ms
#     4x       0:40:26           0:40:26              47 / 95 ms
#
# 1x ABSTEM NAS DUAS IMAGENS — le `MOninutes`, e a guarda de D-b devolve None
# (conferido 5 de 5, deterministico). Ele NAO serve como escala de leitura.
# 2x, 3x e 4x acertam nas duas imagens.
#
# E as duas medicoes discordarem sobre qual escala vence e, ironicamente, a
# evidencia mais forte a favor de D-d: se duas condicoes de leitura honestas
# chegam a vereditos opostos sobre a MESMA fonte, entao nenhuma escala unica e
# confiavel sozinha, e exigir que DUAS concordem sobre o MESMO frame e a unica
# postura defensavel.
#
# POR QUE A DETECCAO E 2x E NAO 1x: 1x nao le os digitos. Com 1x e 3x as duas
# escalas nunca concordariam sobre o banner real — a barata abstem, a cara
# acerta, e o recurso gravaria o warning de desacordo a cada 5 s sem nunca
# avisar ninguem. O modo de falha silencioso que este projeto passa o tempo
# todo tentando evitar.
#
# O ORCAMENTO DEIXOU DE SER A RESTRICAO (D-e revisado). A tabela de custo
# antiga (1x=44, 2x=158, 3x=308, 4x=680 ms) estava inflada pela inicializacao
# do motor amortizada em poucas chamadas. Medido de novo, ja aquecido, na banda
# de producao 732x240 (a de D-f): 1x=10, 2x=23, 3x=31, 4x=55 ms. A 0,2 Hz, a
# passada de 2x custa ~0,5% de um nucleo.
#
# ENTAO A RAZAO DE EXISTIR UMA ESCALA BARATA MUDOU, e vale dizer em voz alta:
# nao e mais ORCAMENTO, e DIVERSIDADE DE METODO. As duas passadas existem para
# ler os mesmos pixels de dois jeitos diferentes e se contradizerem quando o
# motor errar. Se um dia alguem colapsar as duas numa so para economizar 23 ms,
# estara economizando o que nao aperta e gastando a unica guarda que pega erro
# de metodo.
ESCALA_DE_DETECCAO = 2
ESCALA_DE_CONFERENCIA = 3

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
    """A passada de DETECCAO (cinza 2x, 23 ms medidos). Roda sempre na cadencia.

    E ela que DETECTA o banner. So depois de ela ver a raiz `mainten` e que a
    passada de conferencia roda (D-e).

    2x, e nao 1x: 1x abstem nas duas imagens reais medidas — le `MOninutes` e a
    guarda de D-b devolve None. Uma escala que nao le digito nunca poderia
    concordar com a outra, e o recurso ficaria mudo. Veja a tabela no topo do
    modulo.
    """
    return _ler(pixels, ESCALA_DE_DETECCAO)


def ler_texto_ampliado(pixels) -> str | None:
    """A passada de CONFERENCIA (cinza 3x, 31 ms medidos). So durante a contagem.

    E a segunda opiniao de D-d: uma maneira INDEPENDENTE de ler os mesmos
    pixels, para que um erro de metodo do motor nao atravesse o consenso
    temporal — que e cego a ele, porque duas leituras pelo mesmo metodo
    concordam no mesmo erro.
    """
    return _ler(pixels, ESCALA_DE_CONFERENCIA)


def _ler(pixels, escala: int) -> str | None:
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
        return _reconhecer(pixels, escala)
    except Exception as erro:
        log.debug("OCR falhou neste recorte: %s", erro)
        return None


def _reconhecer(pixels: np.ndarray, escala: int) -> str | None:
    """O caminho do WinRT que o spike provou. Nao redescobrir — reproduzir.

    CINZA ANTES DE TUDO (D-a), e e a correcao mais barata deste recurso.

    Medido contra `tests/fixtures/manutencao/banner_40min26s.png` (fonte real
    do jogo, verdade = 40 min 26 s): em COR o motor leu `__40nin? es` e o
    parser devolveu 0:00:26; a MESMA imagem em CINZA leu `40 minutes` e devolveu
    0:40:26. Nao e ajuste fino — e a diferenca entre acertar e errar por 40
    minutos.

    O PORQUE: a fonte do banner e clara sobre fundo escuro, entao toda a
    informacao de FORMA — que e o que o motor procura — ja esta na
    luminancia. Os tres canais BGR carregam variacao de COR que nao carrega
    forma nenhuma, e o motor gasta contraste com ela.

    E custa zero: um `cvtColor` sobre a banda de producao e ruido perto dos
    23-31 ms que a propria passada de reconhecimento leva.

    Um recorte que ja chega com um canal so passa direto — quem grava frame
    em escala de cinza nao paga uma conversao que nao precisa.
    """
    if pixels.ndim == 3:
        pixels = cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY)
    if escala != 1:
        # NA ESCALA 1 O RESIZE NAO E CHAMADO DE FORMA NENHUMA. Nenhuma das
        # duas escalas de producao usa 1 hoje (2x e 3x), mas o atalho fica:
        # ele e o que permite medir a escala 1 sem pagar um resize por 1, e e
        # por uma medicao dessas que o 1x foi descartado.
        pixels = cv2.resize(
            pixels, None, fx=escala, fy=escala, interpolation=cv2.INTER_CUBIC
        )
    ok, codificado = cv2.imencode(".png", pixels)
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
