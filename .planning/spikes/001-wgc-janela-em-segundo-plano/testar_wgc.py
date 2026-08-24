"""Spike 001 — a party window pode ser lida com o jogo em segundo plano?

CRITERIO DE APROVACAO (deliberadamente exigente):
os valores de HP precisam continuar MUDANDO enquanto a janela do jogo esta
coberta E sem foco. "Chegou um frame nao-preto" NAO basta: o risco real e o
cliente parar de renderizar sem foco e a captura devolver o ultimo frame para
sempre — dado velho parecendo valido, que e pior do que um erro claro.

Uso:
    python testar_wgc.py            # 30s de captura, relatorio no fim
    python testar_wgc.py 60         # duracao customizada
"""

import ctypes
import sys
import time
from collections import Counter
from pathlib import Path

try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))

from l2scanner.calibracao import Calibracao  # noqa: E402
from l2scanner.frames import Frame, SaudeDoFrame  # noqa: E402
from l2scanner.visao import EstadoDaLinha, extrair  # noqa: E402

JANELA = "Yazalaque - XM Essence"
DURACAO = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0

cal = Calibracao.carregar(RAIZ / "calibration.json")
pw = cal.party_window

# A janela do jogo comeca em (1713,0); a calibracao esta em coordenadas de
# desktop. Para recortar de um frame da JANELA e preciso descontar a origem.
user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def origem_da_janela(titulo: str):
    achado = {}

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if buf.value == titulo:
                r = RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(r))
                achado["rect"] = (r.left, r.top)
                achado["hwnd"] = hwnd
        return True

    user32.EnumWindows(cb, None)
    return achado


info = origem_da_janela(JANELA)
if not info:
    print(f"Nao achei a janela '{JANELA}'. O jogo esta aberto?")
    raise SystemExit(1)

ox, oy = info["rect"]
hwnd = info["hwnd"]
print(f"Janela em ({ox},{oy})")
print(f"Party window (desktop): ({pw.esquerda},{pw.topo}) {pw.largura}x{pw.altura}")
print(f"Party window (relativa a janela): ({pw.esquerda-ox},{pw.topo-oy})\n")

from windows_capture import Frame as WGCFrame, InternalCaptureControl, WindowsCapture  # noqa: E402

captura = WindowsCapture(
    cursor_capture=False,
    draw_border=False,
    monitor_index=None,
    window_name=JANELA,
)

registros = []
inicio = time.monotonic()


@captura.event
def on_frame_arrived(frame: WGCFrame, control: InternalCaptureControl):
    agora = time.monotonic()
    if agora - inicio > DURACAO:
        control.stop()
        return

    bgra = frame.frame_buffer
    bgr = np.ascontiguousarray(bgra[:, :, :3])

    # A janela pode ter borda; a origem do frame WGC e o canto da janela
    x, y = pw.esquerda - ox, pw.topo - oy
    recorte = bgr[y:y+pw.altura, x:x+pw.largura]
    if recorte.shape[0] != pw.altura or recorte.shape[1] != pw.largura:
        return

    obs = extrair(Frame(pixels=recorte, indice=len(registros),
                        saude=SaudeDoFrame.OK), cal)
    hps = tuple(
        round(l.hp, 3) if l.hp is not None else None
        for l in obs.linhas[:4]
    )
    # foco: a janela do jogo esta em primeiro plano?
    focada = user32.GetForegroundWindow() == hwnd
    registros.append((agora - inicio, focada, obs.ui_visivel, hps,
                      float(bgr.mean())))


@captura.event
def on_closed():
    pass


print(f"Capturando por {DURACAO:.0f}s.")
print(">>> ALT+TAB AGORA e cubra o jogo com outra janela. <<<\n")

try:
    captura.start()
except Exception as erro:
    print(f"A captura falhou: {erro}")
    raise SystemExit(1)

if not registros:
    print("VEREDITO: INVALIDADO — nenhum frame chegou.")
    raise SystemExit(1)

com_foco = [r for r in registros if r[1]]
sem_foco = [r for r in registros if not r[1]]

print(f"\n{len(registros)} frames em {registros[-1][0]:.1f}s")
print(f"  com foco : {len(com_foco)}")
print(f"  sem foco : {len(sem_foco)}\n")


def analisar(grupo, rotulo):
    if not grupo:
        print(f"{rotulo}: sem amostras")
        return None
    leituras = [r[3] for r in grupo]
    distintas = len(set(leituras))
    brilho = [r[4] for r in grupo]
    pretos = sum(1 for b in brilho if b < 8)
    print(f"{rotulo}:")
    print(f"   frames                  : {len(grupo)}")
    print(f"   leituras de HP distintas: {distintas}")
    print(f"   frames pretos           : {pretos}")
    print(f"   brilho medio            : {np.mean(brilho):.1f}")
    print(f"   exemplo de HP           : {leituras[0]}")
    if distintas > 1:
        mudancas = [l for l in set(leituras)][:3]
        print(f"   valores vistos          : {mudancas}")
    print()
    return distintas


d_com = analisar(com_foco, "COM FOCO")
d_sem = analisar(sem_foco, "SEM FOCO (coberto)")

print("=" * 62)
if not sem_foco:
    print("INCONCLUSIVO — o jogo nunca perdeu o foco durante o teste.")
    print("Rode de novo e faca alt+tab enquanto ele captura.")
elif all(r[4] < 8 for r in sem_foco):
    print("VEREDITO: INVALIDADO — sem foco a captura devolve frames pretos.")
elif d_sem is not None and d_sem <= 1 and len(sem_foco) > 20:
    print("VEREDITO: INVALIDADO — sem foco o HP PAROU de mudar.")
    print("O cliente congela a renderizacao sem foco: a captura entrega o")
    print("ultimo frame para sempre. Dado velho parecendo valido e pior do")
    print("que erro — o scanner acharia que esta cobrindo e nao estaria.")
else:
    print("VEREDITO: VALIDADO — sem foco o HP continuou mudando.")
    print("A captura por janela ve o jogo mesmo coberto e sem foco.")
print("=" * 62)
