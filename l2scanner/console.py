"""Destaque visual dos eventos no console.

Um evento nao pode se perder no meio das linhas de log. Quando o usuario volta
do banheiro e olha a janela, "KORZIS MORREU" precisa saltar aos olhos — nao
estar diluido numa linha igual a todas as outras.

Cor e opcional de proposito: se o terminal nao suportar, o destaque continua
funcionando so com as bordas.
"""

from __future__ import annotations

import os
import sys

from .rastreador import TipoDeEvento

LARGURA = 58

# Codigos ANSI. So sao emitidos se o terminal aceitar (ver `_habilitar_cor`).
_RESET = "\033[0m"
_VERMELHO = "\033[91m"
_VERDE = "\033[92m"
_AMARELO = "\033[93m"
_CIANO = "\033[96m"
_NEGRITO = "\033[1m"

_cor_ligada: bool | None = None


def _habilitar_cor() -> bool:
    """Liga o processamento ANSI no console do Windows, se possivel.

    O cmd.exe do Windows 10+ entende ANSI, mas so depois de o processo pedir.
    Sem esse pedido, os codigos de cor aparecem como lixo na tela — pior do que
    nao ter cor nenhuma.
    """
    global _cor_ligada
    if _cor_ligada is not None:
        return _cor_ligada

    # Convencao respeitada por ferramentas de linha de comando em geral
    if os.environ.get("NO_COLOR"):
        _cor_ligada = False
        return False

    if not sys.stdout.isatty():
        _cor_ligada = False
        return False

    if sys.platform != "win32":
        _cor_ligada = True
        return True

    try:
        import ctypes

        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        HANDLE_SAIDA = -11

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(HANDLE_SAIDA)
        modo = ctypes.c_uint32()

        if not kernel32.GetConsoleMode(handle, ctypes.byref(modo)):
            _cor_ligada = False
            return False

        kernel32.SetConsoleMode(
            handle, modo.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
        )
        _cor_ligada = True
    except Exception:
        _cor_ligada = False

    return _cor_ligada


def _pintar(texto: str, cor: str) -> str:
    if not _habilitar_cor():
        return texto
    return f"{cor}{texto}{_RESET}"


_ESTILO = {
    TipoDeEvento.MORREU: ("!", _VERMELHO + _NEGRITO),
    TipoDeEvento.RESSUSCITOU: ("+", _VERDE + _NEGRITO),
    TipoDeEvento.SAIU: ("-", _AMARELO),
    TipoDeEvento.ENTROU: ("+", _CIANO),
    TipoDeEvento.CEGUEIRA_LONGA: ("~", _AMARELO + _NEGRITO),
    TipoDeEvento.VISAO_RECUPERADA: ("~", _CIANO),
    TipoDeEvento.VOCE_SEM_PARTY: ("-", _AMARELO + _NEGRITO),
    TipoDeEvento.VOCE_ENTROU_EM_PARTY: ("+", _CIANO),
}


def destacar(texto: str, tipo: TipoDeEvento, hora: str) -> str:
    """Monta o bloco de destaque de um evento.

    Devolve uma string de varias linhas pronta para imprimir. O bloco cresce se
    o texto for longo, em vez de estourar a moldura — uma borda desalinhada
    parece defeito e tira a atencao do que importa.
    """
    marca, cor = _ESTILO.get(tipo, ("*", _CIANO))

    miolo = f"  {texto}"
    carimbo = f"  [{hora}]"
    largura = max(LARGURA, len(miolo) + len(carimbo))

    preenchimento = largura - len(miolo) - len(carimbo)
    linha = f"{miolo}{' ' * preenchimento}{carimbo}"
    borda = marca * largura

    return "\n".join(
        ["", _pintar(borda, cor), _pintar(linha, cor), _pintar(borda, cor), ""]
    )
