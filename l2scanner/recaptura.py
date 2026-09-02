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

    def __init__(
        self,
        construir: Callable[[], FrameSource],
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        # A FABRICA E O UNICO LUGAR ONDE A LISTA DE ARGUMENTOS DA FONTE EXISTE.
        # Arranque e religacao chamam a MESMA funcao — nao ha um segundo site
        # com os parametros repetidos, que e como dois sites divergem em
        # silencio (e como `minimum_update_interval` apareceria de repente na
        # construcao da party).
        self._construir = construir
        # O relogio entra por parametro pela mesma disciplina do resto do
        # projeto: o portao de espera tem de ser demonstravel sem a suite
        # dormir 30 s por caso.
        self._relogio = relogio
        self._interior = construir()
        self._congelados_seguidos = 0
        self._tentativas_gastas = 0
        self._instante_da_ultima_tentativa: float | None = None
        self._ja_avisou_que_desistiu = False
        # A ultima regiao que o `Reancorador` adotou EM MEMORIA, para reaplicar
        # na fonte reconstruida. Sem ela, um congelamento depois de um
        # reancoramento devolveria o scanner a ler o lugar antigo — ler um lugar
        # com a regua de outro, que `reancoragem.py` chama de pior do que nao
        # reancorar.
        self._regiao_reancorada = None

    # A DELEGACAO E DE DOIS TIPOS, E A DIFERENCA IMPORTA.
    #
    # Declarados aqui: `capturar`, `capturar_completo`, `completo_do_frame_atual`,
    # `apontar_para` e `fechar` — exatamente os metodos cujos donos guardam a
    # REFERENCIA (ou o metodo LIGADO) atravessando a religacao. `Gravador` colhe
    # `fonte.completo_do_frame_atual` na propria construcao; declara-lo aqui e o
    # que faz aquele metodo ligado apontar para o interior CORRENTE no momento
    # da chamada, e nao para o cadaver de onde foi colhido.
    #
    # Todo o resto vai por `__getattr__`. E OBRIGATORIO QUE SEJA ASSIM:
    # `sessao.py` decide se pede o estado do cliente com
    # `hasattr(fonte, "estado_do_cliente")`, e `MssSource` NAO tem esse metodo.
    # Um `def estado_do_cliente` declarado no envelope faria o caminho de
    # desktop prometer um estado de cliente que nao existe, e a promessa
    # estouraria dentro do `try` de analise do tick.

    def capturar(self) -> Frame:
        frame = self._interior.capturar()

        if frame.saude is SaudeDoFrame.CONGELADO:
            self._congelados_seguidos += 1
            if self._congelados_seguidos >= CONGELADOS_SEGUIDOS_PARA_RELIGAR:
                self._religar()
        else:
            self._congelados_seguidos = 0
            # O RESET DO ORCAMENTO ESTA ANCORADO NO FRAME SAUDAVEL, e nao no
            # `__init__` ter retornado. A WGC entrega sessoes que constroem sem
            # erro nenhum e continuam mortas — foi EXATAMENTE o caso medido em
            # campo. Um reset ancorado na construcao nunca esgotaria o teto
            # justamente nesse caso, e o teto so existiria no papel.
            self._devolver_o_orcamento()

        # O FRAME DESTA VOLTA E SEMPRE DEVOLVIDO, inclusive no tick em que a
        # reconstrucao aconteceu. Quem chamou pediu um frame; a cura acontece
        # debaixo dele, e o `CONGELADO` deste tick continua caindo no portao
        # `PortaoGlobal.CEGO` que ja imprime "SEM VISAO".
        return frame

    def capturar_completo(self):
        return self._interior.capturar_completo()

    def completo_do_frame_atual(self):
        return self._interior.completo_do_frame_atual()

    def apontar_para(self, regiao) -> None:
        # A recusa do interior PROPAGA aqui, de proposito: quem chama e o
        # `Reancorador`, e ele precisa ver o `ValueError` de uma fonte de
        # coordenadas de desktop igual a hoje. So guardamos a regiao DEPOIS de
        # o interior aceitar — guardar antes marcaria para reaplicacao um
        # retangulo que a fonte ja rejeitou.
        self._interior.apontar_para(regiao)
        self._regiao_reancorada = regiao

    def fechar(self) -> None:
        self._interior.fechar()

    def __getattr__(self, nome: str):
        # So o que nao esta declarado chega aqui. O prefixo `_` e barrado para
        # o proprio `_interior` nunca cair nesta funcao antes de existir — seria
        # recursao infinita no meio do `__init__`.
        if nome.startswith("_"):
            raise AttributeError(nome)
        return getattr(object.__getattribute__(self, "_interior"), nome)

    def _devolver_o_orcamento(self) -> None:
        self._tentativas_gastas = 0
        self._instante_da_ultima_tentativa = None
        self._ja_avisou_que_desistiu = False

    def _religar(self) -> None:
        if self._tentativas_gastas >= TENTATIVAS_DE_RELIGACAO:
            self._avisar_que_desistiu()
            return

        # O PORTAO DE ESPERA E COMPARACAO DE INSTANTES, NUNCA `time.sleep`. O
        # laco ja dorme `args.intervalo` por tick; dormir aqui atrasaria os
        # comandos e a agenda do mesmo tick junto.
        agora = self._relogio()
        if (
            self._instante_da_ultima_tentativa is not None
            and agora - self._instante_da_ultima_tentativa
            < SEGUNDOS_ENTRE_TENTATIVAS
        ):
            return

        self._instante_da_ultima_tentativa = agora
        # A TENTATIVA CONTA ANTES DE TENTAR. Contar so no sucesso deixaria uma
        # fabrica que explode gastando tentativa nenhuma — e o teto, que existe
        # justamente para o caso em que reconstruir nao resolve, nunca chegaria.
        self._tentativas_gastas += 1
        log.warning(
            "Captura congelada — reconstruindo a fonte (tentativa %d de %d). "
            "A sessao de captura pode ter morrido com o jogo vivo; ver o "
            "cabecalho de recaptura.py.",
            self._tentativas_gastas,
            TENTATIVAS_DE_RELIGACAO,
        )

        antiga = self._interior
        # CONSTRUIR O NOVO ANTES DE FECHAR O VELHO: uma fabrica que explode tem
        # de deixar o scanner com a fonte ANTIGA, e nao sem fonte nenhuma.
        try:
            nova = self._construir()
        except Exception:
            log.exception(
                "A reconstrucao da fonte falhou — seguindo com a fonte antiga"
            )
            return

        # Falhar em FECHAR a antiga nao pode impedir a adocao da nova: o
        # vazamento de uma thread de captura e ruim, ficar com o cadaver e pior.
        try:
            antiga.fechar()
        except Exception:
            log.warning(
                "Nao consegui fechar a fonte antiga — adotando a nova assim "
                "mesmo",
                exc_info=True,
            )

        self._interior = nova
        self._reaplicar_a_regiao_reancorada()
        log.info("Fonte de captura reconstruida — voltando a ler a tela")

    def _reaplicar_a_regiao_reancorada(self) -> None:
        """A fonte nova nasce apontada para a regiao do ARRANQUE.

        Se o `Reancorador` ja adotou outra em memoria, e para ELA que a fonte
        reconstruida tem de olhar. A reaplicacao falha FECHADA: `apontar_para`
        recusa fonte de coordenadas de desktop com `ValueError`, e essa recusa
        nao pode virar crash de religacao — a fonte nova ja foi adotada e ler o
        retangulo do arranque e melhor do que nao ler nada.
        """
        if self._regiao_reancorada is None:
            return
        try:
            self._interior.apontar_para(self._regiao_reancorada)
        except Exception:
            log.warning(
                "A fonte reconstruida nao aceitou a regiao reancorada — "
                "seguindo com o retangulo do arranque",
                exc_info=True,
            )

    def _avisar_que_desistiu(self) -> None:
        """UMA vez, alto, e o laco segue rodando cego.

        Nao sai, nao levanta, nao silencia. Um erro por tick durante um farm de
        tres horas e a forma mais confiavel de o aviso nao ser lido — mesma
        disciplina do `_ja_avisou_que_nao_adotou` em `reancoragem.py`. A marca
        volta a `False` no proximo frame saudavel, porque ai a proxima cegueira
        e outra historia.
        """
        if self._ja_avisou_que_desistiu:
            return
        self._ja_avisou_que_desistiu = True
        log.error(
            "A captura NAO voltou depois de %d tentativas de religacao. O "
            "scanner continua rodando, mas SEGUE CEGO: nada sera detectado nem "
            "alertado ate a imagem mudar. Verifique a janela do jogo.",
            TENTATIVAS_DE_RELIGACAO,
        )
