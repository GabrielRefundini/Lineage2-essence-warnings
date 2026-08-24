"""Calibracao: onde ficam as coisas na tela e que cores contam como barra cheia.

Separada da configuracao escrita a mao de proposito. A calibracao e gerada por
ferramenta e sobrescrita a cada recalibragem; a configuracao e escrita pelo
usuario. Se morassem no mesmo arquivo, a ferramenta apagaria os ajustes manuais
na primeira vez que rodasse.

A calibracao guarda a geometria de tela sob a qual foi feita. Se a resolucao ou
o arranjo de monitores mudar, os retangulos gravados nao significam mais a mesma
coisa — e o scanner se recusa a iniciar em vez de medir a regiao errada calado.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .frames import Regiao

VERSAO_DO_ESQUEMA = 2


class CalibracaoInvalida(Exception):
    """A calibracao nao existe, esta corrompida ou nao vale para esta tela."""


@dataclass(frozen=True)
class LimiaresDeCor:
    """Que pixels contam como preenchimento de uma barra.

    A SATURACAO e o discriminador principal, nao o matiz. Motivo medido na tela
    real: a parte vazia da barra e transparente e mostra o terreno do jogo
    (S~75), enquanto a barra cheia e solida (S~210). O terreno muda de cor entre
    zonas, mas nunca fica saturado como a barra.

    Para o vermelho, `matiz_min` > `matiz_max` sinaliza a volta no circulo de
    matiz: a faixa vale de matiz_min ate 179 E de 0 ate matiz_max.
    """

    matiz_min: int
    matiz_max: int
    saturacao_min: int
    valor_min: int


@dataclass(frozen=True)
class LayoutDaParty:
    """Geometria das linhas de membro, tudo RELATIVO a party_window.

    As linhas sao uniformes e igualmente espacadas, entao um passo unico
    descreve todas — nao e preciso listar retangulo por retangulo.
    """

    # Icone de classe — o indicador de presenca da linha
    icone_x: int
    icone_y: int  # do primeiro membro
    icone_tamanho: int

    # Barras (HP e MP compartilham x, largura e altura)
    barra_x: int
    barra_largura: int
    barra_altura: int
    hp_y: int  # do primeiro membro
    mp_y: int  # do primeiro membro

    passo: int  # distancia vertical entre membros consecutivos
    max_linhas: int

    # Limiares de contraste para "tem icone aqui".
    # Medidos na tela real: linha com membro da desvio 43-52 e 46-52% de pixels
    # escuros; linha vazia da desvio 9-10 e 0% escuros. O corte fica no meio da
    # margem, bem longe dos dois lados.
    icone_desvio_min: float = 25.0
    icone_escuros_min: float = 0.15

    # A ancora da janela e mais fraca que o icone (moldura fina), entao seu
    # corte e mais baixo. Medido: canto da moldura da desvio 35, terreno da 8-12.
    ancora_desvio_min: float = 20.0
    ancora_escuros_min: float = 0.02


@dataclass
class Calibracao:
    """Onde ficam as coisas na tela deste usuario."""

    # A janela inteira da party — e o que o scanner captura a cada tick
    party_window: Regiao

    # Ancora de visibilidade da UI, RELATIVA a party_window.
    # Fica no TOPO porque a janela e ancorada em cima e encolhe por baixo
    # conforme a PT diminui; uma ancora embaixo sumiria sozinha com menos gente.
    ancora: Regiao

    layout: LayoutDaParty
    limiares_hp: LimiaresDeCor
    limiares_mp: LimiaresDeCor

    # Geometria da tela quando isto foi calibrado, para detectar mudanca
    geometria_da_tela: str

    # Barra de HP do proprio personagem (fica no topo da tela, fora da party
    # window). RELATIVA a party_window se estiver dentro dela; caso contrario
    # exige uma captura separada — deixado para depois.
    hp_proprio: Regiao | None = None

    # Nomes dos membros, em ordem de linha. Fonte da verdade para identidade —
    # nunca leitura de texto da tela, que erraria um glifo e inventaria um
    # membro fantasma entrando e saindo da party.
    nomes: list[str] = field(default_factory=list)

    versao: int = VERSAO_DO_ESQUEMA

    def nome_da_linha(self, indice: int) -> str:
        """Nome configurado, ou um rotulo generico se a lista for mais curta."""
        if 0 <= indice < len(self.nomes):
            return self.nomes[indice]
        return f"Membro {indice + 1}"

    def salvar(self, caminho: Path) -> None:
        dados = {
            "versao": self.versao,
            "geometria_da_tela": self.geometria_da_tela,
            "party_window": self.party_window.como_dict(),
            "ancora": self.ancora.como_dict(),
            "layout": asdict(self.layout),
            "limiares_hp": asdict(self.limiares_hp),
            "limiares_mp": asdict(self.limiares_mp),
            "hp_proprio": self.hp_proprio.como_dict() if self.hp_proprio else None,
            "nomes": self.nomes,
        }
        caminho.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @classmethod
    def carregar(cls, caminho: Path) -> "Calibracao":
        if not caminho.exists():
            raise CalibracaoInvalida(
                f"Nao encontrei {caminho}.\n"
                f"Rode a calibracao:  python -m l2scanner.calibrar"
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
            layout=LayoutDaParty(**dados["layout"]),
            limiares_hp=LimiaresDeCor(**dados["limiares_hp"]),
            limiares_mp=LimiaresDeCor(**dados["limiares_mp"]),
            geometria_da_tela=dados["geometria_da_tela"],
            hp_proprio=(
                Regiao.de_dict(dados["hp_proprio"]) if dados.get("hp_proprio") else None
            ),
            nomes=list(dados.get("nomes", [])),
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
    """Assinatura estavel do arranjo de monitores."""
    import mss

    with mss.mss() as sct:
        partes = [
            f"{m['width']}x{m['height']}+{m['left']}+{m['top']}"
            for m in sct.monitors[1:]
        ]
    return ";".join(partes)


# Valores medidos na tela real do usuario em 2026-08-24, cliente XM Essence,
# janela do Yazalaque em (1713,0) num monitor de 3440x1440. Servem de ponto de
# partida; a ferramenta de calibracao regrava tudo isto.
LIMIARES_HP_PADRAO = LimiaresDeCor(
    matiz_min=168,  # > matiz_max: volta no circulo, duas faixas combinadas
    matiz_max=12,
    saturacao_min=120,  # barra cheia da ~210, terreno da ~75
    valor_min=60,
)

LIMIARES_MP_PADRAO = LimiaresDeCor(
    matiz_min=95,
    matiz_max=130,
    saturacao_min=120,  # barra cheia da ~195
    valor_min=60,
)
