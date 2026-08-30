"""Deteccao visual do Tiat no chat e no alvo selecionado.

O jogo nao oferece uma API de spawn para o scanner (e o projeto nao le memoria
nem trafego). Este modulo recebe apenas o texto que o OCR conseguiu enxergar
em duas regioes que o usuario calibra: o chat e o nome do alvo. Ele deliberada-
mente nao tenta interpretar a frase inteira do servidor: para este aviso, ver
o nome raro ``Tiat`` em qualquer um dos dois lugares e o sinal util.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# OCR costuma trocar I por 1/l, A por 4/@ e T por 7 na fonte fina do jogo.
# A normalizacao e limitada a esta busca; nao altera nem registra o texto cru.
_TIAT = re.compile(r"t[i1l][a4@][t7]", re.IGNORECASE)


class OrigemDoTiat(Enum):
    CHAT = "chat"
    ALVO = "alvo"
    CHAT_E_ALVO = "chat_e_alvo"


@dataclass(frozen=True)
class AvisoDeTiat:
    """Uma deteccao nova, antes de ser entregue ao WhatsApp."""

    origem: OrigemDoTiat

    @property
    def texto(self) -> str:
        if self.origem is OrigemDoTiat.CHAT:
            detalhe = "o chat do jogo anunciou Tiat"
        elif self.origem is OrigemDoTiat.ALVO:
            detalhe = "seu alvo virou Tiat"
        else:
            detalhe = "o chat anunciou Tiat e seu alvo virou Tiat"
        return f"TIAT DETECTADO — {detalhe}."


class VigiaDoTiat:
    """Transforma aparicoes de Tiat em um unico aviso por ocorrencia visual.

    A mesma linha fica no chat por varios frames e o alvo normalmente fica
    selecionado por minutos. Portanto, enquanto qualquer sinal continuar
    presente, nao ha segundo aviso. Duas leituras limpas consecutivas rearmam
    o vigia para o proximo spawn/novo target; uma falha isolada de OCR nao
    basta para rearmar e transformar o mesmo boss em spam.
    """

    def __init__(
        self,
        ler_texto,
        leituras_limpas_para_rearmar: int = 2,
        segundos_entre_leituras: float = 2.0,
    ) -> None:
        if leituras_limpas_para_rearmar < 1:
            raise ValueError("leituras_limpas_para_rearmar deve ser >= 1")
        if segundos_entre_leituras <= 0:
            raise ValueError("segundos_entre_leituras deve ser > 0")
        self._ler_texto = ler_texto
        self._limpas_para_rearmar = leituras_limpas_para_rearmar
        self._intervalo = segundos_entre_leituras
        self._ultima_leitura: datetime | None = None
        self._armado = True
        self._limpas = 0

    @staticmethod
    def _tem_tiat(texto: str | None) -> bool:
        return bool(texto and _TIAT.search(texto))

    def _ler(self, pixels) -> str | None:
        if pixels is None:
            return None
        try:
            return self._ler_texto(pixels)
        except Exception:
            # OCR e complementar ao rastreador: jamais pode derrubar o tick.
            return None

    def avaliar(
        self, pixels_do_chat, pixels_do_alvo, agora: datetime
    ) -> AvisoDeTiat | None:
        if (
            self._ultima_leitura is not None
            and (agora - self._ultima_leitura).total_seconds() < self._intervalo
        ):
            return None
        self._ultima_leitura = agora
        no_chat = self._tem_tiat(self._ler(pixels_do_chat))
        no_alvo = self._tem_tiat(self._ler(pixels_do_alvo))

        if no_chat or no_alvo:
            self._limpas = 0
            if not self._armado:
                return None
            self._armado = False
            if no_chat and no_alvo:
                origem = OrigemDoTiat.CHAT_E_ALVO
            elif no_chat:
                origem = OrigemDoTiat.CHAT
            else:
                origem = OrigemDoTiat.ALVO
            return AvisoDeTiat(origem)

        self._limpas += 1
        if self._limpas >= self._limpas_para_rearmar:
            self._armado = True
        return None
