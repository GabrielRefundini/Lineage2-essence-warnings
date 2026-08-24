"""Captura da janela do jogo, mesmo coberta por outra janela.

Validado no spike 001: o cliente XM Essence continua renderizando sem foco e
coberto (443 frames distintos de 456). Isso derruba o risco que a pesquisa
apontava como bloqueante — clientes UE2 costumam congelar a renderizacao sem
foco, e a captura entregaria o ultimo frame para sempre.

DUAS DIFERENCAS EM RELACAO AO `mss` que moldam este codigo:

1. **A WGC empurra frames, nao entrega sob demanda.** Um callback recebe ~38
   frames por segundo. O laco do scanner pede 1 por segundo. Entao guardamos
   sempre o mais recente e devolvemos esse — descartar frames e o normal aqui.

2. **O referencial das coordenadas muda.** A calibracao esta em coordenadas de
   DESKTOP; o frame da WGC comeca no canto da JANELA. E preciso descontar a
   origem da janela a cada captura, porque ela muda se o usuario arrastar o
   jogo — e nesse caso o `mss` quebraria calado, enquanto aqui acompanhamos.

LIMITE QUE NAO TEM CONTORNO: janela MINIMIZADA nao produz frame nenhum. Isso
nao e limitacao da biblioteca, e como o Windows funciona. O detector de frame
congelado cobre esse caso.
"""

from __future__ import annotations

import ctypes
import threading
import time

import numpy as np

from .frames import Frame, Regiao, SaudeDoFrame, _ClassificadorDeSaude

# Quanto esperar pelo primeiro frame antes de desistir
SEGUNDOS_PARA_PRIMEIRO_FRAME = 5.0

_user32 = ctypes.windll.user32


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class JanelaNaoEncontrada(Exception):
    """A janela do jogo nao esta aberta, ou o titulo nao confere."""


def achar_janela(titulo: str) -> int:
    """Devolve o handle da janela cujo titulo bate exatamente."""
    achado: dict[str, int] = {}

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def visitar(hwnd, _):
        tamanho = _user32.GetWindowTextLengthW(hwnd)
        if tamanho:
            buffer = ctypes.create_unicode_buffer(tamanho + 1)
            _user32.GetWindowTextW(hwnd, buffer, tamanho + 1)
            if buffer.value == titulo:
                achado["hwnd"] = hwnd
        return True

    _user32.EnumWindows(visitar, None)

    if "hwnd" not in achado:
        disponiveis = listar_janelas_do_jogo()
        dica = (
            "\nJanelas do jogo abertas agora:\n  "
            + "\n  ".join(disponiveis)
            if disponiveis
            else "\nNenhuma janela do XM Essence encontrada — o jogo esta aberto?"
        )
        raise JanelaNaoEncontrada(
            f"Nao achei uma janela chamada '{titulo}'.{dica}"
        )
    return achado["hwnd"]


# O executavel do cliente. Filtrar por processo, e nao so pelo titulo, evita
# confundir uma ABA DE NAVEGADOR chamada "XM Essence - Brave" com o jogo.
EXECUTAVEL_DO_JOGO = "l2.bin"


def _nome_do_processo(hwnd: int) -> str:
    """Executavel dono da janela, em minusculas. Vazio se nao der para saber."""
    pid = ctypes.c_uint32()
    _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value
    )
    if not handle:
        return ""

    try:
        buffer = ctypes.create_unicode_buffer(512)
        tamanho = ctypes.c_uint32(512)
        if kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(tamanho)
        ):
            return buffer.value.rsplit("\\", 1)[-1].lower()
    finally:
        kernel32.CloseHandle(handle)
    return ""


def listar_janelas_do_jogo(fragmento: str = "XM Essence") -> list[str]:
    """Titulos das janelas que sao mesmo do cliente do jogo.

    Casa titulo E processo. So o titulo nao basta: uma aba de navegador chamada
    "XM Essence - Brave" apareceria na lista e o usuario acharia que e o jogo.
    """
    encontrados: list[str] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def visitar(hwnd, _):
        if not _user32.IsWindowVisible(hwnd):
            return True
        tamanho = _user32.GetWindowTextLengthW(hwnd)
        if not tamanho:
            return True
        buffer = ctypes.create_unicode_buffer(tamanho + 1)
        _user32.GetWindowTextW(hwnd, buffer, tamanho + 1)
        if fragmento not in buffer.value:
            return True
        if _nome_do_processo(hwnd) != EXECUTAVEL_DO_JOGO:
            return True
        encontrados.append(buffer.value)
        return True

    _user32.EnumWindows(visitar, None)
    return encontrados


def janela_que_contem(x: int, y: int) -> str | None:
    """Titulo da janela do jogo que contem o ponto dado, se houver.

    Usado pela calibracao para descobrir sozinha a qual cliente a party window
    marcada pertence — com duas instancias abertas, adivinhar daria errado.
    """
    for titulo in listar_janelas_do_jogo():
        try:
            hwnd = achar_janela(titulo)
        except JanelaNaoEncontrada:
            continue
        rect = _RECT()
        if ctypes.windll.dwmapi.DwmGetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_uint(_DWMWA_EXTENDED_FRAME_BOUNDS),
            ctypes.byref(rect),
            ctypes.sizeof(rect),
        ) != 0:
            _user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if rect.left <= x < rect.right and rect.top <= y < rect.bottom:
            return titulo
    return None


# DWMWA_EXTENDED_FRAME_BOUNDS
_DWMWA_EXTENDED_FRAME_BOUNDS = 9


def origem_da_janela(hwnd: int) -> tuple[int, int]:
    """Canto superior esquerdo VISIVEL da janela, em coordenadas de desktop.

    Nao usar `GetWindowRect` aqui. No Windows 10/11 ele inclui a borda
    invisivel de redimensionamento — tipicamente 7 px de cada lado — enquanto a
    captura de janela comeca no conteudo real. A diferenca foi medida: 7 px na
    horizontal, o bastante para a ancora de visibilidade cair fora e o scanner
    se declarar cego com a party window bem na frente dele.

    O DWM sabe os limites de verdade, entao perguntamos a ele e so caimos no
    `GetWindowRect` se a chamada falhar.
    """
    rect = _RECT()
    resultado = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        ctypes.c_void_p(hwnd),
        ctypes.c_uint(_DWMWA_EXTENDED_FRAME_BOUNDS),
        ctypes.byref(rect),
        ctypes.sizeof(rect),
    )
    if resultado != 0:  # S_OK == 0
        _user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return int(rect.left), int(rect.top)


def esta_minimizada(hwnd: int) -> bool:
    return bool(_user32.IsIconic(hwnd))


class JanelaSource:
    """Captura uma janela especifica, mesmo coberta por outras.

    Implementa a mesma porta `FrameSource` do `MssSource`, entao o laco do
    scanner nao sabe qual dos dois esta usando.
    """

    def __init__(
        self,
        titulo_da_janela: str,
        regiao: Regiao,
        relativa: bool = False,
        extras: dict[str, Regiao] | None = None,
    ) -> None:
        from windows_capture import (
            Frame as FrameWGC,
            InternalCaptureControl,
            WindowsCapture,
        )

        self._titulo = titulo_da_janela
        self._regiao = regiao
        # `relativa` diz se a regiao ja esta em coordenadas do canto da
        # janela. Se estiver, arrastar o jogo nao afeta nada. Se nao, ela
        # esta em coordenadas de desktop e precisa ser convertida a cada
        # captura — e ai mover a janela entre a calibracao e a execucao
        # faria a conta sair errada.
        self._relativa = relativa
        # Recortar extras aqui e de graca: o frame completo da janela ja
        # esta em maos. No caminho do desktop cada extra custa uma captura.
        self._extras = extras or {}
        self._hwnd = achar_janela(titulo_da_janela)

        self._ultimo: np.ndarray | None = None
        self._trava = threading.Lock()
        self._saude = _ClassificadorDeSaude()
        self._contador = 0
        self._parar = threading.Event()
        self._erro: Exception | None = None

        captura = WindowsCapture(
            cursor_capture=False,
            draw_border=False,
            monitor_index=None,
            window_name=titulo_da_janela,
        )

        @captura.event
        def on_frame_arrived(frame: FrameWGC, control: InternalCaptureControl):
            if self._parar.is_set():
                control.stop()
                return
            # BGRA -> BGR. Guardamos so o mais recente: a WGC entrega ~38 fps e
            # o scanner consome 1 por segundo, entao descartar e o normal.
            bgr = np.ascontiguousarray(frame.frame_buffer[:, :, :3])
            with self._trava:
                self._ultimo = bgr

        @captura.event
        def on_closed():
            pass

        self._thread = threading.Thread(
            target=self._rodar_captura, args=(captura,), daemon=True
        )
        self._thread.start()
        self._esperar_primeiro_frame()

    def _rodar_captura(self, captura) -> None:
        try:
            captura.start()
        except Exception as erro:  # a thread nao pode morrer calada
            self._erro = erro

    def _esperar_primeiro_frame(self) -> None:
        limite = time.monotonic() + SEGUNDOS_PARA_PRIMEIRO_FRAME
        while time.monotonic() < limite:
            if self._erro:
                raise RuntimeError(
                    f"A captura de janela falhou ao iniciar: {self._erro}"
                )
            with self._trava:
                if self._ultimo is not None:
                    return
            time.sleep(0.05)

        raise RuntimeError(
            f"Nenhum frame chegou de '{self._titulo}' em "
            f"{SEGUNDOS_PARA_PRIMEIRO_FRAME:.0f}s.\n"
            f"A janela esta minimizada? Janela minimizada nao produz frame — "
            f"nenhuma API do Windows contorna isso."
        )

    def capturar_completo(self) -> np.ndarray | None:
        """A janela inteira, sem recortar. Usado pela calibracao.

        A calibracao precisa varrer a janela toda atras do padrao das barras —
        ela ainda nao sabe onde a party window esta, que e justamente o que
        vai descobrir.
        """
        with self._trava:
            return None if self._ultimo is None else self._ultimo.copy()

    def capturar(self) -> Frame:
        with self._trava:
            completo = None if self._ultimo is None else self._ultimo.copy()

        if completo is None:
            vazio = np.zeros((1, 1, 3), dtype=np.uint8)
            frame = Frame(
                pixels=vazio,
                indice=self._contador,
                saude=SaudeDoFrame.FALHA_DE_CAPTURA,
            )
            self._contador += 1
            return frame

        # A calibracao esta em coordenadas de DESKTOP e o frame comeca no canto
        # da JANELA. Recalcular a origem a cada captura faz o scanner acompanhar
        # o jogo se ele for arrastado — o `mss` quebraria calado nesse caso.
        if self._relativa:
            x, y = self._regiao.esquerda, self._regiao.topo
        else:
            ox, oy = origem_da_janela(self._hwnd)
            x = self._regiao.esquerda - ox
            y = self._regiao.topo - oy

        recorte = (
            completo[y : y + self._regiao.altura, x : x + self._regiao.largura]
            if x >= 0 and y >= 0
            else np.zeros((0, 0, 3), dtype=np.uint8)
        )

        if (
            recorte.shape[0] != self._regiao.altura
            or recorte.shape[1] != self._regiao.largura
        ):
            # A regiao calibrada caiu fora da janela: ela foi movida ou
            # redimensionada. Falha de captura, nunca "barras vazias".
            saude = SaudeDoFrame.FALHA_DE_CAPTURA
            recorte = np.zeros(
                (self._regiao.altura, self._regiao.largura, 3), dtype=np.uint8
            )
        else:
            saude = self._saude.classificar(recorte)

        recortes: dict[str, np.ndarray] = {}
        for nome, extra in self._extras.items():
            ex = self._extra_para_janela(extra, completo)
            if ex is not None:
                recortes[nome] = ex

        frame = Frame(
            pixels=recorte,
            indice=self._contador,
            saude=saude,
            extras=recortes,
        )
        self._contador += 1
        return frame

    def _extra_para_janela(
        self, extra: Regiao, completo: np.ndarray
    ) -> np.ndarray | None:
        """Recorta uma regiao extra do frame completo da janela."""
        if self._relativa:
            x, y = extra.esquerda, extra.topo
        else:
            ox, oy = origem_da_janela(self._hwnd)
            x, y = extra.esquerda - ox, extra.topo - oy
        if x < 0 or y < 0:
            return None
        recorte = completo[y : y + extra.altura, x : x + extra.largura]
        if (
            recorte.shape[0] != extra.altura
            or recorte.shape[1] != extra.largura
        ):
            return None
        return recorte

    def fechar(self) -> None:
        self._parar.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
