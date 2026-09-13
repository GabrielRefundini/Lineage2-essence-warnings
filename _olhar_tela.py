"""Uma captura da tela, sob demanda — para eu enxergar a janela de calibracao.

Nao roda em laco. Existe para o momento em que o usuario diz "abriu": eu chamo,
olho, e respondo. O watch continuo foi tentado e descartado — a regiao captura o
que estiver por cima naquele canto (o jogo, ou o proprio chat), entao ele
gerava evento sem conteudo.

Nao grava no repositorio e nao toca em calibration.json.
"""
import sys
from pathlib import Path
import mss, numpy as np, cv2

destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("agora.png")
with mss.MSS() as sct:
    bruto = np.array(sct.grab({"left": 0, "top": 0, "width": 1700, "height": 1400}))[:, :, :3]
peq = cv2.resize(bruto, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
destino.parent.mkdir(parents=True, exist_ok=True)
if not cv2.imwrite(str(destino), peq):
    raise SystemExit(f"nao consegui gravar {destino}")
print(f"capturado: {destino}  {peq.shape[1]}x{peq.shape[0]}")
