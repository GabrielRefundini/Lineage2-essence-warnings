"""Gravador de sessao — a peca que destrava todo o resto.

Por que isto existe antes de qualquer logica de deteccao:

O evento que o scanner existe para pegar (alguem da PT morrer) e raro e nao se
reproduz sob demanda. Sem uma gravacao real, cada ajuste de limiar seria um
chute testado contra um jogo ao vivo esperando alguem morrer. Com gravacao, o
usuario farma uma hora com `--record` ligado, banca uma morte de verdade, e
aquela sessao vira ao mesmo tempo a base de calibracao e um teste de regressao
permanente.

Formato: PNG por frame (sem perda — compressao com perda destruiria justamente
as bordas de barra que precisamos medir) mais um JSONL com uma linha por frame.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .frames import Frame


class Gravador:
    """Grava frames e metadados de uma sessao em disco."""

    def __init__(self, pasta_base: Path, rotulo: str | None = None) -> None:
        carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
        nome = f"{carimbo}-{rotulo}" if rotulo else carimbo
        self.pasta = pasta_base / nome
        self.pasta.mkdir(parents=True, exist_ok=True)

        self._arquivo_meta = (self.pasta / "observacoes.jsonl").open(
            "w", encoding="utf-8"
        )
        self.frames_gravados = 0

    def gravar(self, frame: Frame, momento: float) -> None:
        import cv2

        caminho = self.pasta / f"frame_{frame.indice:06d}.png"
        cv2.imwrite(str(caminho), frame.pixels)

        linha = {
            "indice": frame.indice,
            "momento": momento,
            "saude": frame.saude.value,
            "arquivo": caminho.name,
        }
        self._arquivo_meta.write(json.dumps(linha, ensure_ascii=False) + "\n")
        self._arquivo_meta.flush()  # sobrevive a um Ctrl+C ou queda de energia

        self.frames_gravados += 1

    def fechar(self) -> None:
        self._arquivo_meta.close()

    def __enter__(self) -> "Gravador":
        return self

    def __exit__(self, *_) -> None:
        self.fechar()
