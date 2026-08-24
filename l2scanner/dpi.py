"""Consciencia de DPI — precisa rodar ANTES de importar mss ou cv2.

Por que isso e a primeira coisa do programa:

Sem declarar consciencia de DPI, o Windows entrega ao processo coordenadas
*logicas* (ja divididas pela escala) enquanto a captura de tela devolve o buffer
de pixels *fisicos*. A 125% de escala, todo recorte sai 25% deslocado — e nao ha
mensagem de erro nenhuma. A imagem chega valida, so que da regiao errada.

O modo mais cruel de falhar: voce calibra contra a regiao errada, os limiares
ficam ajustados para ela, e o bug fica assado dentro da calibracao.

O scanner e a ferramenta de calibracao precisam AMBOS chamar isso, senao as
coordenadas gravadas por um nao significam a mesma coisa para o outro.
"""

from __future__ import annotations

import ctypes
import sys

# DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
_PER_MONITOR_AWARE_V2 = -4

_ja_aplicado = False


def tornar_consciente_de_dpi() -> str:
    """Declara o processo como per-monitor DPI aware.

    Devolve uma string curta descrevendo o que foi conseguido, para o log.
    Idempotente: chamar duas vezes nao causa erro.
    """
    global _ja_aplicado
    if _ja_aplicado:
        return "ja aplicado"

    if sys.platform != "win32":
        _ja_aplicado = True
        return "nao-Windows, nada a fazer"

    # Windows 10 1703+ — o caminho bom, por monitor, reage a mudanca de escala
    try:
        user32 = ctypes.windll.user32
        if user32.SetProcessDpiAwarenessContext(_PER_MONITOR_AWARE_V2):
            _ja_aplicado = True
            return "per-monitor v2"
    except (AttributeError, OSError):
        pass

    # Windows 8.1+ — por monitor, mas sem reagir a mudanca em tempo real
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        _ja_aplicado = True
        return "per-monitor v1 (shcore)"
    except (AttributeError, OSError):
        pass

    # Vista+ — consciencia de sistema; funciona se todos os monitores usam a
    # mesma escala, que e o caso comum
    try:
        ctypes.windll.user32.SetProcessDPIAware()
        _ja_aplicado = True
        return "system-aware (legado)"
    except (AttributeError, OSError):
        pass

    _ja_aplicado = True
    return "FALHOU — coordenadas podem sair deslocadas se a escala nao for 100%"
