"""Entrega dos eventos: do rastreador para o WhatsApp, via Chatwoot.

O limite deteccao->transporte nasce aqui e nao e retrofit. Se `enviar()` chegar
a ser chamado inline pela deteccao, agregacao de wipe, deduplicacao e limite de
taxa ficam impossiveis de acrescentar depois. A fila custa poucas linhas e e o
limite mais importante do projeto.

Duas garantias operacionais:

- **Grava antes de enviar.** Cada alerta vai para um arquivo duravel ANTES da
  tentativa de rede. Uma queda de conexao no meio de um farm nao pode apagar o
  registro de que alguem morreu.

- **Falha alto.** Entrega que falha em silencio e pior do que nao ter
  ferramenta nenhuma, porque a party aprende a confiar num silencio que nao
  significa mais nada.
"""

from __future__ import annotations

import json
import random
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Protocol

from .rastreador import Evento, TipoDeEvento

TIMEOUT_CONEXAO = (3, 10)  # (conectar, ler) em segundos
MAX_TENTATIVAS = 4

# O Chatwoot pode estar atras do Cloudflare, e o User-Agent padrao do urllib
# ("Python-urllib/3.x") e barrado pela verificacao de integridade de navegador
# com erro 1010. Um User-Agent normal resolve — nao e disfarce, e so nao se
# anunciar como script para um filtro que barra scripts por padrao.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def formatar(evento: Evento) -> str:
    """Texto que chega no celular.

    A redacao e HEDGED de proposito: "HP zerado ha 6s (possivel morte)"
    sobrevive a um falso positivo; "MORREU" nao. O scanner le pixels, nao le a
    verdade — e o texto precisa ser honesto sobre isso.

    Horario local com data curta: quem le no celular precisa saber se aquilo
    aconteceu agora ou ha duas horas.
    """
    hora = datetime.fromtimestamp(evento.momento).strftime("%H:%M")

    if evento.tipo is TipoDeEvento.MORREU:
        return f"[{hora}] {evento.membro}: HP zerado — possivel morte na PT."

    if evento.tipo is TipoDeEvento.RESSUSCITOU:
        if evento.segundos_no_estado:
            tempo = _duracao_legivel(evento.segundos_no_estado)
            return f"[{hora}] {evento.membro}: HP de volta apos {tempo}."
        return f"[{hora}] {evento.membro}: HP de volta."

    if evento.tipo is TipoDeEvento.SAIU:
        return f"[{hora}] {evento.membro}: saiu da party."

    if evento.tipo is TipoDeEvento.ENTROU:
        return f"[{hora}] {evento.membro}: entrou na party."

    if evento.tipo is TipoDeEvento.CEGUEIRA_LONGA:
        tempo = _duracao_legivel(evento.segundos_no_estado or 0)
        return (
            f"[{hora}] Scanner sem visao da party ha {tempo}. "
            f"Pode ser tela de loading, jogo minimizado ou cliente fechado — "
            f"eventos nesse periodo nao serao detectados."
        )

    if evento.tipo is TipoDeEvento.VISAO_RECUPERADA:
        tempo = _duracao_legivel(evento.segundos_no_estado or 0)
        return (
            f"[{hora}] Scanner voltou a enxergar a party. "
            f"Estive cego por {tempo} — posso ter perdido eventos nesse intervalo."
        )

    return f"[{hora}] {evento.tipo.value}: {evento.membro or ''}".strip()


def formatar_console(evento: Evento) -> str:
    """Texto curto e direto para quem esta olhando o console agora.

    Deliberadamente DIFERENTE do texto que vai para o WhatsApp. La a redacao e
    cautelosa ("possivel morte") porque quem le esta longe e nao tem como
    conferir; aqui o usuario esta na frente da tela e pode olhar o jogo no
    mesmo segundo. Ser direto no console e mais util e nao custa nada.
    """
    quem = evento.membro or "?"

    if evento.tipo is TipoDeEvento.MORREU:
        return f"{quem.upper()} MORREU"

    if evento.tipo is TipoDeEvento.RESSUSCITOU:
        if evento.segundos_no_estado:
            return (
                f"{quem.upper()} FOI RESSUSCITADO "
                f"(ficou {_duracao_legivel(evento.segundos_no_estado)} morto)"
            )
        return f"{quem.upper()} FOI RESSUSCITADO"

    if evento.tipo is TipoDeEvento.SAIU:
        return f"{quem.upper()} SAIU DA PARTY"

    if evento.tipo is TipoDeEvento.ENTROU:
        return f"{quem.upper()} ENTROU NA PARTY"

    if evento.tipo is TipoDeEvento.CEGUEIRA_LONGA:
        tempo = _duracao_legivel(evento.segundos_no_estado or 0)
        return f"SEM VISAO DA PARTY HA {tempo} - NADA E DETECTADO AGORA"

    if evento.tipo is TipoDeEvento.VISAO_RECUPERADA:
        tempo = _duracao_legivel(evento.segundos_no_estado or 0)
        return f"VISAO RECUPERADA - estive cego por {tempo}"

    return evento.tipo.value.upper()


def _duracao_legivel(segundos: float) -> str:
    segundos = int(segundos)
    if segundos < 60:
        return f"{segundos}s"
    minutos, resto = divmod(segundos, 60)
    if minutos < 60:
        return f"{minutos}min" if resto < 10 else f"{minutos}min{resto}s"
    horas, minutos = divmod(minutos, 60)
    return f"{horas}h{minutos:02d}"


class Notificador(Protocol):
    """Para onde os alertas vao. Trocar o adaptador e o modo simulacao."""

    def enviar(self, texto: str) -> None: ...


class NotificadorDeConsole:
    """Modo simulacao: mostra no console, nao envia nada."""

    def __init__(self, escrever=print) -> None:
        self._escrever = escrever

    def enviar(self, texto: str) -> None:
        self._escrever(f"  [simulacao] {texto}")


class NotificadorEmMemoria:
    """Para testes: guarda o que seria enviado."""

    def __init__(self) -> None:
        self.enviados: list[str] = []

    def enviar(self, texto: str) -> None:
        self.enviados.append(texto)


@dataclass
class ConfigChatwoot:
    url: str
    conta: str
    token: str
    conversas: list[str]


class ErroDeEntrega(Exception):
    """Falhou o envio. Distingue transitorio de definitivo."""

    def __init__(self, mensagem: str, transitorio: bool) -> None:
        super().__init__(mensagem)
        self.transitorio = transitorio


class NotificadorChatwoot:
    """Envia via API do Chatwoot. Um POST por conversa de destino."""

    def __init__(self, config: ConfigChatwoot) -> None:
        self._config = config

    def enviar(self, texto: str) -> None:
        erros = []
        for conversa in self._config.conversas:
            try:
                self._postar(conversa, texto)
            except ErroDeEntrega as erro:
                erros.append((conversa, erro))

        if erros:
            # Se QUALQUER destino for transitorio, o lote merece nova tentativa
            transitorio = any(e.transitorio for _, e in erros)
            detalhes = "; ".join(f"conversa {c}: {e}" for c, e in erros)
            raise ErroDeEntrega(detalhes, transitorio=transitorio)

    def _postar(self, conversa: str, texto: str) -> None:
        url = (
            f"{self._config.url}/api/v1/accounts/{self._config.conta}"
            f"/conversations/{conversa}/messages"
        )
        corpo = json.dumps(
            {"content": texto, "message_type": "outgoing"}
        ).encode("utf-8")

        req = urllib.request.Request(url, data=corpo, method="POST")
        # Header plano, sem prefixo Bearer — e assim que o Chatwoot espera
        req.add_header("api_access_token", self._config.token)
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", USER_AGENT)
        req.add_header("Accept", "application/json")

        try:
            with urllib.request.urlopen(
                req, timeout=TIMEOUT_CONEXAO[1]
            ) as resposta:
                resposta.read()
        except urllib.error.HTTPError as erro:
            # 4xx e erro nosso: token errado, conversa inexistente. Repetir so
            # gasta tentativa. 429 e a excecao: e "espere um pouco".
            transitorio = erro.code >= 500 or erro.code == 429
            raise ErroDeEntrega(f"HTTP {erro.code}", transitorio=transitorio) from erro
        except (urllib.error.URLError, TimeoutError, OSError) as erro:
            raise ErroDeEntrega(f"rede: {erro}", transitorio=True) from erro


class Despachante:
    """Fila + thread de entrega. Isola a rede do laco de captura.

    Sem isto, um Chatwoot lento faria o scanner parar de olhar a tela — e a
    proxima morte passaria despercebida enquanto o socket esperava.
    """

    def __init__(
        self,
        notificador: Notificador,
        arquivo_outbox: Path | None = None,
        ao_falhar=None,
    ) -> None:
        self._notificador = notificador
        self._outbox = arquivo_outbox
        self._ao_falhar = ao_falhar or (lambda texto, erro: None)
        self._fila: Queue[str | None] = Queue(maxsize=200)
        self._thread: threading.Thread | None = None
        self._rodando = False
        self.entregues = 0
        self.falhados = 0

    def iniciar(self) -> None:
        self._rodando = True
        self._thread = threading.Thread(
            target=self._laco, name="despachante", daemon=True
        )
        self._thread.start()

    def despachar(self, texto: str) -> None:
        """Enfileira. Grava no outbox ANTES de qualquer tentativa de rede."""
        if self._outbox:
            registro = {"momento": time.time(), "texto": texto}
            with self._outbox.open("a", encoding="utf-8") as arquivo:
                arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")

        try:
            self._fila.put_nowait(texto)
        except Exception:
            # Fila cheia: o evento ja esta no outbox, entao nada se perdeu de
            # verdade — mas o usuario precisa saber.
            self._ao_falhar(texto, "fila de envio cheia")

    def _laco(self) -> None:
        while self._rodando:
            try:
                texto = self._fila.get(timeout=0.5)
            except Empty:
                continue

            if texto is None:
                break

            self._tentar_entregar(texto)
            self._fila.task_done()

    def _tentar_entregar(self, texto: str) -> None:
        for tentativa in range(1, MAX_TENTATIVAS + 1):
            try:
                self._notificador.enviar(texto)
                self.entregues += 1
                return
            except ErroDeEntrega as erro:
                if not erro.transitorio:
                    self.falhados += 1
                    self._ao_falhar(texto, f"erro definitivo: {erro}")
                    return
                if tentativa == MAX_TENTATIVAS:
                    self.falhados += 1
                    self._ao_falhar(
                        texto, f"falhou apos {MAX_TENTATIVAS} tentativas: {erro}"
                    )
                    return
                # backoff com jitter: se varios alertas falham juntos, nao
                # voltam todos no mesmo instante
                espera = (2 ** (tentativa - 1)) + random.uniform(0, 0.5)
                time.sleep(espera)
            except Exception as erro:  # notificador local nao deve derrubar
                self.falhados += 1
                self._ao_falhar(texto, f"erro inesperado: {erro}")
                return

    def encerrar(self, espera_maxima: float = 10.0) -> None:
        """Drena a fila antes de sair — alerta pendente ainda vale a pena."""
        limite = time.monotonic() + espera_maxima
        while not self._fila.empty() and time.monotonic() < limite:
            time.sleep(0.1)

        self._rodando = False
        self._fila.put(None)
        if self._thread:
            self._thread.join(timeout=2.0)
