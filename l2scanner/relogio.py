"""Um unico lugar decide que horas sao — e ele nao pergunta ao Windows.

O PC do usuario e dual boot. O Linux grava o relogio do hardware em UTC, o
Windows le o mesmo valor como hora local, e ao voltar do Linux o Windows fica
~3h adiantado ate ressincronizar sozinho. Palavras dele: "as vezes ele muda
pois eu logo no linux e volta um horario aleatorio".

A DETECCAO NUNCA ESTEVE EM RISCO: debounce, cooldown, staleness e o ritmo do
laco usam `time.monotonic()`, que nao pula. QUEM QUEBRAVA ERA A AGENDA. Ela le
a hora de parede a cada tick e so dispara um aviso dentro de
`TOLERANCIA_MINUTOS = 5` depois do alvo — um pulo de 3h atravessa a janela
inteira sem tocar nela. O aviso de TvT simplesmente nao saia, em silencio, que
e o pior modo de falha que este projeto tem.

O DESENHO, em uma frase: pegar a hora de fora UMA vez e, dai em diante, contar
pelo monotonico. Isso da um relogio CERTO (a hora vem do servidor) e IMUNE A
PULO (o avanco vem do monotonico), inclusive quando o proprio Windows se
corrige no meio da sessao.

A fonte externa e o cabecalho `Date` da resposta HTTP do Chatwoot: zero
dependencia nova, zero porta nova, e reusa o servidor e a porta 443 que o
scanner ja atravessa. O acoplamento e de graca — se o Chatwoot estiver fora, o
scanner ja esta mudo de qualquer jeito.

MESMA DISCIPLINA DE `agenda.py`: nao ha relogio proprio escondido aqui. Fonte,
monotonico e parede entram por parametro, e e por isso que os testes nao
precisam de rede nem de monkeypatch.
"""

from __future__ import annotations

import email.utils
import logging
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Callable

log = logging.getLogger("l2scanner.relogio")

# Isto roda no ARRANQUE. Um usuario offline nao pode esperar 10s para o
# scanner subir so para descobrir que nao ha hora la fora.
TIMEOUT_ANCORA = 3.0

# Intervalo padrao entre reancoragens. O motivo nao e deriva de cristal
# (irrelevante em minutos): e que o comportamento do monotonico atravessando
# suspensao do sistema depende de plataforma e nao e coisa em que apostar.
INTERVALO_PADRAO = 1800.0

# Abaixo disto a data e lixo, nao hora. Um intermediario quebrado devolvendo
# 1970 seria PIOR que nao ancorar: a agenda acharia que todo aviso de hoje
# venceu ha decadas e nunca mais falaria.
ANO_MINIMO_PLAUSIVEL = 2020


def epoch_do_cabecalho_date(valor: str | None) -> float | None:
    """Le o `Date` de uma resposta HTTP (RFC 7231) e devolve o epoch UTC.

    Nunca levanta: esta funcao roda no caminho de arranque, e um cabecalho
    estranho de um proxy no meio nao pode impedir o scanner de subir.
    """
    if not valor:
        return None
    try:
        momento = email.utils.parsedate_to_datetime(valor)
    except (TypeError, ValueError):
        return None
    if momento is None:
        return None
    if momento.year < ANO_MINIMO_PLAUSIVEL:
        return None
    try:
        return momento.timestamp()
    except (OverflowError, OSError, ValueError):
        return None


class Relogio:
    """A hora que a agenda usa: ancorada la fora, contada pelo monotonico."""

    def __init__(
        self,
        fonte: Callable[[], float | None] | None = None,
        monotonico: Callable[[], float] = time.monotonic,
        parede: Callable[[], float] = time.time,
    ) -> None:
        self._fonte = fonte
        self._monotonico = monotonico
        self._parede = parede
        self._ancora_epoch: float | None = None
        self._ancora_mono: float = 0.0

    # -- ancoragem ----------------------------------------------------------

    def sincronizar(self) -> bool:
        """Pergunta a hora la fora e prende a ancora ao PONTO MEDIO da viagem.

        O `Date` e do instante em que o servidor respondeu, e a resposta levou
        um tempo para voltar. Ancorar no meio da ida-e-volta corta o erro
        maximo pela metade e custa duas linhas.

        Devolve False — nunca levanta — quando a fonte falha: a fonte e rede,
        rede falha, e nada disso pode impedir o scanner de subir.
        """
        if self._fonte is None:
            return False

        antes = self._monotonico()
        try:
            epoch = self._fonte()
        except Exception as erro:  # rede, DNS, timeout, resposta torta
            log.debug("Fonte de hora indisponivel: %s", erro)
            return False
        depois = self._monotonico()

        if epoch is None:
            return False

        self._ancora_epoch = float(epoch)
        self._ancora_mono = (antes + depois) / 2
        return True

    def iniciar_sincronizacao_periodica(
        self, intervalo: float = INTERVALO_PADRAO
    ) -> threading.Thread:
        """Reancora de tempos em tempos, numa thread daemon e a parte.

        Daemon e separada pela mesma razao pela qual o `Despachante` existe: o
        laco de captura NUNCA pode bloquear em rede. E daemon para que um
        Ctrl+C encerre o scanner na hora, sem esperar o proximo intervalo.
        """

        def laco() -> None:
            while True:
                time.sleep(intervalo)
                self.sincronizar()

        thread = threading.Thread(target=laco, daemon=True, name="relogio")
        thread.start()
        return thread

    # -- leitura ------------------------------------------------------------

    def agora_epoch(self) -> float:
        if self._ancora_epoch is None:
            # Sem ancora a hora E a do Windows, defeito e tudo. O arranque
            # avisa em WARNING justamente porque este caminho e o honesto,
            # nao o bom.
            return self._parede()
        # ESTA LINHA E A CORRECAO: o avanco vem do monotonico, entao um pulo
        # de 3h no relogio do Windows nao move a hora que a agenda usa.
        return self._ancora_epoch + (self._monotonico() - self._ancora_mono)

    def agora(self) -> datetime:
        """Datetime ingenuo, hora local, de proposito.

        A agenda inteira trabalha com datetime ingenuo, e o fuso do Windows
        continua correto mesmo quando o relogio nao esta — o dual boot estraga
        o RELOGIO, nao a configuracao de fuso.
        """
        return datetime.fromtimestamp(self.agora_epoch())

    @property
    def confiavel(self) -> bool:
        return self._ancora_epoch is not None

    def desvio_do_windows(self) -> float | None:
        """Quanto o relogio da maquina esta ADIANTADO, em segundos com sinal.

        E o numero que o arranque imprime para o usuario: sem ele o aviso
        diria "a hora esta errada" sem dizer de quanto, que e inacionavel.
        """
        if self._ancora_epoch is None:
            return None
        return self._parede() - self.agora_epoch()


def fonte_chatwoot(
    url: str, timeout: float = TIMEOUT_ANCORA
) -> Callable[[], float | None]:
    """Chamavel que le o cabecalho `Date` da URL base do Chatwoot.

    Tres detalhes que sao desenho, nao acaso:

    1. SEM TOKEN. Qualquer resposta HTTP carrega `Date`, inclusive 401/403/404
       — nao ha motivo para expor o token do usuario neste caminho, nem para
       ter que escolher um endpoint autenticado.
    2. `HTTPError` TAMBEM SERVE. Ele expoe `.headers`, entao um 404 e uma
       ancoragem bem-sucedida. So DNS, conexao e timeout sao falha de verdade.
    3. USER_AGENT DO NOTIFICADOR. O Chatwoot do usuario esta atras do
       Cloudflare, que barra o UA padrao do urllib com erro 1010.
    """
    from l2scanner.notificador import USER_AGENT

    def _buscar() -> float | None:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", USER_AGENT)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resposta:
                cabecalho = resposta.headers.get("Date")
        except urllib.error.HTTPError as erro:
            cabecalho = erro.headers.get("Date") if erro.headers else None
        except (urllib.error.URLError, TimeoutError, OSError):
            return None
        return epoch_do_cabecalho_date(cabecalho)

    return _buscar
