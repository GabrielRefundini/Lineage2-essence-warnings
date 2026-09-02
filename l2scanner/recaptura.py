"""Religar a captura quando ela congela.

O INCIDENTE, medido em 2026-09-01 as 23:18:39
---------------------------------------------
O scanner logou `Imagem congelada — jogo travado ou captura presa` e ficou 33
minutos em `[SEM VISAO]`. O jogo estava VIVO o tempo todo: a janela existia
(hwnd 30216936), nao estava minimizada, ocupava (1713,0)-(3447,1399), a
geometria batia com `cal["geometria_da_tela"]` (dx=0, dy=0), o recorte da party
mostrava quatro membros legiveis, `hp_proprio` lia `HP 5915/5915`, o `mss` via a
tela MUDANDO (diffs de 174.087 e 120.828 entre capturas) e — a medicao que
decide tudo — uma `JanelaSource` NOVA, construida naquele mesmo instante,
funcionava (diffs de 150.453 e 149.983, brilho medio 58,2).

Ou seja: o detector de congelamento acertou, a calibracao estava certa, a janela
estava certa. So o OBJETO DE CAPTURA preso no processo estava morto. O laco
escrevia um `log.warning` e seguia chamando `capturar()` naquele cadaver para
sempre. Uma morte nessa janela de 33 minutos nao teria sido anunciada.

O que este modulo faz e a coisa que faltava: depois de N frames `CONGELADO`
seguidos, RECONSTROI a fonte pela mesma fabrica que a construiu no arranque.

POR QUE UM ENVELOPE, E NAO UM `fonte = construir()` NO LACO
-----------------------------------------------------------
Tres objetos guardam a fonte (ou um metodo LIGADO dela) na propria construcao:
`Sessao.fonte`, `Gravador(fonte_completa=fonte.completo_do_frame_atual)` e
`Reancorador(fonte=fonte)`. Rebindar a variavel local do laco trocaria so a
variavel: os tres continuariam apontando para o objeto morto. Seria o defeito de
hoje, agora em tres lugares. O envelope tem identidade estavel e troca o
INTERIOR, entao quem guardou a referencia continua vendo a fonte viva.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from .frames import Frame, FrameSource, SaudeDoFrame

log = logging.getLogger(__name__)


# AS TRES CONSTANTES MORAM AQUI, E NAO NO `calibration.json`.
#
# Mesmo motivo ja registrado para `PISO_DO_RESTO` em `mercado_catalogo.py`: uma
# chave nova OBRIGATORIA no arquivo de calibracao deixaria o scanner morto no
# proximo arranque, ate o usuario rodar a recalibracao. Estes tres numeros nao
# dependem do monitor, do gamma nem do skin da UI — sao ritmo de recuperacao, e
# ritmo de recuperacao nao se calibra com um trackbar. Move-los para a
# calibracao depois nao exige reescrever nada aqui.

# Quantos frames `CONGELADO` seguidos disparam a religacao.
#
# TRES BASTAM PORQUE `CONGELADO` JA E CARO DE GANHAR. Ele so sai depois de
# `FRAMES_IDENTICOS_PARA_CONGELADO` (30) frames byte-identicos, ou seja meio
# minuto a 1 Hz. Este numero nao e o debounce — o debounce ja aconteceu la
# dentro. Tres ticks a mais sao ~3 s de confirmacao em cima de ~30 s de
# evidencia, e a primeira tentativa acontece por volta dos 33 s de cegueira, e
# nao dos 33 minutos.
CONGELADOS_SEGUIDOS_PARA_RELIGAR = 3

# O teto de reconstrucoes por episodio de congelamento.
#
# No caso MEDIDO, a fonte nova funcionou na PRIMEIRA tentativa — o teto nao
# existe para aquele caso, existe para o outro: quando reconstruir nao resolve
# (driver caido, sessao WGC que nasce morta, jogo realmente travado). Sem teto
# seria uma sessao de captura nova por tick, para sempre, martelando a WGC e
# vazando uma thread de captura a cada volta.
TENTATIVAS_DE_RELIGACAO = 5

# A espera minima entre duas tentativas.
#
# Cinco tentativas espacadas em 30 s dao ~2,5 min de esforco de recuperacao,
# suficientes para atravessar um hiccup do compositor sem virar um laco de
# reconstrucao. Nao ha `time.sleep` nenhum: o portao e COMPARACAO DE INSTANTES,
# porque o laco ja dorme `args.intervalo` por tick e bloquear aqui atrasaria os
# comandos e a agenda junto.
SEGUNDOS_ENTRE_TENTATIVAS = 30.0


class FonteRecuperavel:
    """Uma `FrameSource` que reconstroi a fonte de dentro quando ela congela.

    Implementa a mesma porta `FrameSource` (`capturar`, `fechar`), entao o laco
    nao sabe que existe um envelope no caminho.
    """

    def __init__(self, construir: Callable[[], FrameSource]) -> None:
        # A FABRICA E O UNICO LUGAR ONDE A LISTA DE ARGUMENTOS DA FONTE EXISTE.
        # Arranque e religacao chamam a MESMA funcao — nao ha um segundo site
        # com os parametros repetidos, que e como dois sites divergem em
        # silencio (e como `minimum_update_interval` apareceria de repente na
        # construcao da party).
        self._construir = construir
        self._interior = construir()
        self._congelados_seguidos = 0

    def capturar(self) -> Frame:
        frame = self._interior.capturar()

        if frame.saude is SaudeDoFrame.CONGELADO:
            self._congelados_seguidos += 1
            if self._congelados_seguidos >= CONGELADOS_SEGUIDOS_PARA_RELIGAR:
                self._religar()
        else:
            self._congelados_seguidos = 0

        # O FRAME DESTA VOLTA E SEMPRE DEVOLVIDO, inclusive no tick em que a
        # reconstrucao aconteceu. Quem chamou pediu um frame; a cura acontece
        # debaixo dele, e o `CONGELADO` deste tick continua caindo no portao
        # `PortaoGlobal.CEGO` que ja imprime "SEM VISAO".
        return frame

    def _religar(self) -> None:
        log.warning(
            "Captura congelada — reconstruindo a fonte (a sessao de captura "
            "morreu com o jogo vivo; ver o cabecalho de recaptura.py)"
        )
        antiga = self._interior
        # CONSTRUIR O NOVO ANTES DE FECHAR O VELHO.
        nova = self._construir()
        antiga.fechar()
        self._interior = nova
        log.info("Fonte de captura reconstruida — voltando a ler a tela")
