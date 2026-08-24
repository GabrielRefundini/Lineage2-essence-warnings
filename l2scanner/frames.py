"""Origem de frames e classificacao de saude do frame.

Duas ideias sustentam este modulo:

1. **FrameSource e uma porta.** O laco principal nunca sabe de onde o frame veio.
   Hoje ha `MssSource` (tela ao vivo) e `ReplaySource` (sessao gravada). Isolar
   isso agora custa ~20 linhas; fazer depois custa reescrever o laco.

2. **Frame preto nao e "todo mundo com HP zero".** Esta e a diferenca entre um
   scanner util e um que dispara quatro alertas de morte quando o Windows
   entrega um buffer vazio. A classificacao acontece AQUI, antes de qualquer
   leitura de barra, e produz tres estados bem separados.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator, Protocol

import numpy as np

# Abaixo deste brilho medio o frame e considerado falha de captura, nao imagem
# escura legitima. A party window do L2 tem molduras claras e barras coloridas;
# uma captura saudavel nunca chega perto disso.
LIMIAR_BRILHO_MINIMO = 8.0

# Quantos frames identicos seguidos ate considerar a imagem congelada.
# A 1 Hz isso e ~30 s. Uma tela de jogo viva sempre muda alguma coisa (grama,
# nuvem, animacao de personagem), entao frames byte-identicos por meio minuto
# significam jogo travado ou captura presa, nao party parada.
FRAMES_IDENTICOS_PARA_CONGELADO = 30


class SaudeDoFrame(Enum):
    """Estado de um frame capturado, antes de qualquer analise de conteudo."""

    OK = "ok"
    FALHA_DE_CAPTURA = "falha_de_captura"
    CONGELADO = "congelado"


@dataclass(frozen=True)
class Frame:
    """Uma captura, com a informacao necessaria para julga-la."""

    pixels: np.ndarray  # BGR, shape (altura, largura, 3)
    indice: int
    saude: SaudeDoFrame

    # Momento em que o frame foi capturado. Ao vivo fica None e o laco usa o
    # relogio; num replay vem do arquivo gravado. Essa distincao e o que faz
    # uma sessao de uma hora reproduzir os MESMOS eventos em trinta segundos —
    # sem ela, o debounce mediria o tempo do replay, nao o do farm, e o
    # harness de regressao nao provaria nada.
    momento: float | None = None

    @property
    def utilizavel(self) -> bool:
        return self.saude is SaudeDoFrame.OK


@dataclass(frozen=True)
class Regiao:
    """Retangulo em coordenadas de desktop virtual.

    Esquerda e topo podem ser NEGATIVOS: um monitor secundario posicionado a
    esquerda do principal tem coordenadas negativas no Windows. Guardar isso
    como inteiro sem sinal e um bug classico.
    """

    esquerda: int
    topo: int
    largura: int
    altura: int

    def como_dict_mss(self) -> dict[str, int]:
        return {
            "left": self.esquerda,
            "top": self.topo,
            "width": self.largura,
            "height": self.altura,
        }

    @classmethod
    def de_dict(cls, dados: dict) -> "Regiao":
        return cls(
            esquerda=int(dados["esquerda"]),
            topo=int(dados["topo"]),
            largura=int(dados["largura"]),
            altura=int(dados["altura"]),
        )

    def como_dict(self) -> dict[str, int]:
        return {
            "esquerda": self.esquerda,
            "topo": self.topo,
            "largura": self.largura,
            "altura": self.altura,
        }


class FrameSource(Protocol):
    """De onde os frames vem. O laco principal so conhece esta interface."""

    def capturar(self) -> Frame: ...
    def fechar(self) -> None: ...


class _ClassificadorDeSaude:
    """Julga frames em sequencia — precisa de memoria entre eles."""

    def __init__(self) -> None:
        self._hash_anterior: str | None = None
        self._repeticoes = 0

    def classificar(self, pixels: np.ndarray) -> SaudeDoFrame:
        if pixels.size == 0:
            return SaudeDoFrame.FALHA_DE_CAPTURA

        if float(pixels.mean()) < LIMIAR_BRILHO_MINIMO:
            return SaudeDoFrame.FALHA_DE_CAPTURA

        # Frames identicos: hash e barato e nao tem falso positivo pratico
        atual = hashlib.blake2b(pixels.tobytes(), digest_size=16).hexdigest()
        if atual == self._hash_anterior:
            self._repeticoes += 1
        else:
            self._repeticoes = 0
            self._hash_anterior = atual

        if self._repeticoes >= FRAMES_IDENTICOS_PARA_CONGELADO:
            return SaudeDoFrame.CONGELADO

        return SaudeDoFrame.OK


class MssSource:
    """Captura da tela ao vivo com mss.

    Escolhido em vez de dxcam de proposito: `dxcam.grab()` devolve `None` quando
    nenhum frame novo foi renderizado desde a ultima chamada — e uma party window
    parada durante farm AFK e exatamente esse caso. Um laco ingenuo leria `None`
    por minutos e concluiria que perdeu a visao. O mss sempre devolve pixels.
    """

    def __init__(self, regiao: Regiao) -> None:
        import mss  # importado aqui: exige DPI ja declarado

        self._regiao = regiao
        self._mss = mss.mss()
        self._saude = _ClassificadorDeSaude()
        self._contador = 0

    def capturar(self) -> Frame:
        bruto = self._mss.grab(self._regiao.como_dict_mss())
        # mss devolve BGRA; descartamos o canal alfa
        pixels = np.asarray(bruto, dtype=np.uint8)[:, :, :3]

        frame = Frame(
            pixels=pixels,
            indice=self._contador,
            saude=self._saude.classificar(pixels),
        )
        self._contador += 1
        return frame

    def fechar(self) -> None:
        self._mss.close()


class ReplaySource:
    """Reproduz uma sessao gravada — sem jogo, sem tela, sem rede.

    E isto que torna o projeto testavel: o evento alvo (alguem morrer) e raro e
    nao se reproduz sob demanda, entao a unica forma de iterar nos limiares e
    contra uma gravacao real.
    """

    def __init__(self, pasta: Path) -> None:
        import json

        self._arquivos = sorted(pasta.glob("frame_*.png"))
        if not self._arquivos:
            raise FileNotFoundError(f"Nenhum frame_*.png em {pasta}")

        # Momentos gravados, indexados por nome de arquivo. Sem eles o replay
        # mediria o tempo do proprio replay em vez do tempo do farm.
        self._momentos: dict[str, float] = {}
        meta = pasta / "observacoes.jsonl"
        if meta.exists():
            for linha in meta.read_text(encoding="utf-8").splitlines():
                if not linha.strip():
                    continue
                try:
                    registro = json.loads(linha)
                    self._momentos[registro["arquivo"]] = float(registro["momento"])
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

        self._iterador: Iterator[Path] = iter(self._arquivos)
        self._saude = _ClassificadorDeSaude()
        self._contador = 0

    def __len__(self) -> int:
        return len(self._arquivos)

    def capturar(self) -> Frame:
        import cv2

        caminho = next(self._iterador)  # StopIteration encerra o replay
        pixels = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
        if pixels is None:
            raise ValueError(f"Nao consegui ler {caminho}")

        frame = Frame(
            pixels=pixels,
            indice=self._contador,
            saude=self._saude.classificar(pixels),
            momento=self._momentos.get(caminho.name),
        )
        self._contador += 1
        return frame

    def fechar(self) -> None:
        pass
