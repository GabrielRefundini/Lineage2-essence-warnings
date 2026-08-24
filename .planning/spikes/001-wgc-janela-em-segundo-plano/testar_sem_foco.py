"""Spike 001b — um cliente SEM FOCO e COBERTO continua renderizando?

Experimento natural, sem tocar na tela do usuario: ele roda duas instancias do
jogo. Apenas uma pode estar em primeiro plano, entao a outra esta, por
definicao, sem foco — e coberta pela janela do Claude.

Se os frames dela mudarem ao longo do tempo, o cliente segue renderizando sem
foco e a captura por janela e viavel. Se congelarem, a captura entregaria o
ultimo frame para sempre: dado velho parecendo valido, pior do que erro.
"""

import ctypes
import hashlib
import sys
import time

try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

import numpy as np
from windows_capture import Frame, InternalCaptureControl, WindowsCapture

JANELA = sys.argv[1] if len(sys.argv) > 1 else "Faerlina - XM Essence"
DURACAO = float(sys.argv[2]) if len(sys.argv) > 2 else 15.0

user32 = ctypes.windll.user32


def hwnd_por_titulo(titulo):
    achado = {}

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if buf.value == titulo:
                achado["hwnd"] = hwnd
        return True

    user32.EnumWindows(cb, None)
    return achado.get("hwnd")


alvo = hwnd_por_titulo(JANELA)
if not alvo:
    print(f"Nao achei a janela '{JANELA}'")
    raise SystemExit(1)

primeiro_plano_inicial = user32.GetForegroundWindow()
print(f"Alvo   : {JANELA}")
print(f"Focado?: {'SIM' if primeiro_plano_inicial == alvo else 'NAO (e o que queremos)'}\n")

captura = WindowsCapture(cursor_capture=False, draw_border=False,
                         monitor_index=None, window_name=JANELA)

amostras = []
inicio = time.monotonic()


@captura.event
def on_frame_arrived(frame: Frame, control: InternalCaptureControl):
    agora = time.monotonic()
    if agora - inicio > DURACAO:
        control.stop()
        return
    bgr = np.ascontiguousarray(frame.frame_buffer[:, :, :3])
    # amostra so o miolo, para o hash nao depender de relogio/UI de canto
    h, w = bgr.shape[:2]
    miolo = bgr[h//4:3*h//4, w//4:3*w//4]
    amostras.append((
        agora - inicio,
        hashlib.blake2b(miolo.tobytes(), digest_size=8).hexdigest(),
        float(miolo.mean()),
        user32.GetForegroundWindow() == alvo,
    ))


@captura.event
def on_closed():
    pass


print(f"Capturando {DURACAO:.0f}s...\n")
try:
    captura.start()
except Exception as erro:
    print(f"A captura falhou: {erro}")
    raise SystemExit(1)

if not amostras:
    print("VEREDITO: INVALIDADO — nenhum frame chegou.")
    raise SystemExit(1)

sem_foco = [a for a in amostras if not a[3]]
hashes = [a[1] for a in sem_foco]
distintos = len(set(hashes))
brilhos = [a[2] for a in sem_foco]

print(f"{len(amostras)} frames, {len(sem_foco)} deles SEM foco")
print(f"  frames distintos (sem foco): {distintos}")
print(f"  brilho medio               : {np.mean(brilhos):.1f}")
print(f"  frames pretos              : {sum(1 for b in brilhos if b < 8)}")

# maior sequencia de frames identicos seguidos
maior, atual = 1, 1
for i in range(1, len(hashes)):
    atual = atual + 1 if hashes[i] == hashes[i-1] else 1
    maior = max(maior, atual)
print(f"  maior sequencia identica   : {maior} frames\n")

print("=" * 62)
if not sem_foco:
    print("INCONCLUSIVO — a janela estava focada o tempo todo.")
elif np.mean(brilhos) < 8:
    print("VEREDITO: INVALIDADO — frames pretos sem foco.")
elif distintos <= 1:
    print("VEREDITO: INVALIDADO — a imagem CONGELOU sem foco.")
    print("O cliente para de renderizar quando perde o foco. A captura")
    print("entregaria o ultimo frame para sempre — o scanner acharia que")
    print("esta vigiando e estaria olhando uma foto.")
else:
    taxa = distintos / len(sem_foco)
    print(f"VEREDITO: VALIDADO — {distintos} frames distintos sem foco")
    print(f"({taxa:.0%} dos frames sao novos). O cliente segue renderizando")
    print("mesmo sem foco e coberto: captura por janela e viavel.")
print("=" * 62)
