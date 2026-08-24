"""Calibracao: o que vigiar e onde.

Separada da configuracao escrita a mao de proposito. A calibracao e gerada por
ferramenta (arrastar o mouse) e sobrescrita a cada recalibragem; a configuracao
e escrita pelo usuario. Se morassem no mesmo arquivo, a ferramenta apagaria os
ajustes manuais na primeira vez que rodasse.

A calibracao guarda a geometria de tela sob a qual foi feita. Se a resolucao ou
o arranjo de monitores mudar, os retangulos gravados nao significam mais a mesma
coisa — e o scanner se recusa a iniciar em vez de medir a regiao errada em
silencio.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .frames import Regiao

VERSAO_DO_ESQUEMA = 1


class CalibracaoInvalida(Exception):
    """A calibracao nao existe, esta corrompida ou nao vale para esta tela."""


@dataclass
class Calibracao:
    """Onde ficam as coisas na tela deste usuario."""

    # A janela inteira da party — e o que o scanner captura a cada tick
    party_window: Regiao

    # Ancora de visibilidade: um pedaco da moldura no TOPO da janela.
    # Precisa ser no topo porque a janela e ancorada em cima e encolhe por baixo
    # conforme a PT diminui — uma ancora embaixo sumiria sozinha com 3 membros.
    # Coordenadas RELATIVAS a party_window.
    ancora: Regiao

    # Geometria da tela quando isto foi calibrado, para detectar mudanca
    geometria_da_tela: str

    # Barra de HP do proprio personagem (fica no topo da tela, fora da party
    # window) — opcional ate ser calibrada
    hp_proprio: Regiao | None = None

    # Regioes de HP e MP de cada linha de membro, RELATIVAS a party_window.
    # Preenchidas na Fase 2; a Fase 1 so precisa capturar e gravar.
    linhas_hp: list[Regiao] = field(default_factory=list)
    linhas_mp: list[Regiao] = field(default_factory=list)

    versao: int = VERSAO_DO_ESQUEMA

    def salvar(self, caminho: Path) -> None:
        dados = {
            "versao": self.versao,
            "geometria_da_tela": self.geometria_da_tela,
            "party_window": self.party_window.como_dict(),
            "ancora": self.ancora.como_dict(),
            "hp_proprio": self.hp_proprio.como_dict() if self.hp_proprio else None,
            "linhas_hp": [r.como_dict() for r in self.linhas_hp],
            "linhas_mp": [r.como_dict() for r in self.linhas_mp],
        }
        caminho.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @classmethod
    def carregar(cls, caminho: Path) -> "Calibracao":
        if not caminho.exists():
            raise CalibracaoInvalida(
                f"Nao encontrei {caminho}.\n"
                f"Rode a calibracao primeiro (Fase 2 do roadmap)."
            )

        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except json.JSONDecodeError as erro:
            raise CalibracaoInvalida(f"{caminho} esta corrompido: {erro}") from erro

        versao = dados.get("versao")
        if versao != VERSAO_DO_ESQUEMA:
            raise CalibracaoInvalida(
                f"{caminho} foi gravado no formato v{versao}, "
                f"mas este scanner espera v{VERSAO_DO_ESQUEMA}. Recalibre."
            )

        return cls(
            party_window=Regiao.de_dict(dados["party_window"]),
            ancora=Regiao.de_dict(dados["ancora"]),
            geometria_da_tela=dados["geometria_da_tela"],
            hp_proprio=(
                Regiao.de_dict(dados["hp_proprio"]) if dados.get("hp_proprio") else None
            ),
            linhas_hp=[Regiao.de_dict(r) for r in dados.get("linhas_hp", [])],
            linhas_mp=[Regiao.de_dict(r) for r in dados.get("linhas_mp", [])],
            versao=versao,
        )

    def conferir_geometria(self, atual: str) -> None:
        """Recusa se a tela mudou desde a calibracao (CAPT-07).

        Falhar alto aqui e muito melhor do que medir a regiao errada calado.
        """
        if self.geometria_da_tela != atual:
            raise CalibracaoInvalida(
                "A configuracao de tela mudou desde a calibracao.\n"
                f"  calibrado sob: {self.geometria_da_tela}\n"
                f"  agora:         {atual}\n"
                "As coordenadas gravadas nao valem mais. Recalibre."
            )


def descrever_geometria_da_tela() -> str:
    """Assinatura estavel do arranjo de monitores.

    Usada para detectar que a tela mudou entre a calibracao e a execucao.
    """
    import mss

    with mss.mss() as sct:
        # monitors[0] e a uniao de todos; os demais sao cada monitor
        partes = [
            f"{m['width']}x{m['height']}+{m['left']}+{m['top']}"
            for m in sct.monitors[1:]
        ]
    return ";".join(partes)
