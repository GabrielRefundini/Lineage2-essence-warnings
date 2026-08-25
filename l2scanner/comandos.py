"""Comandos vindos do WhatsApp: o scanner passa a OUVIR, nao so a falar.

Ate aqui o caminho era de mao unica. Isto abre a volta — e abrir a volta e
abrir uma superficie de ataque, entao o desenho comeca pela seguranca e nao
pela funcionalidade.

TRES TRAVAS, E NENHUMA E OPCIONAL:

1. **Allowlist de conversa.** So conversas explicitamente configuradas em
   `CHATWOOT_CONVERSAS_COMANDO` sao lidas. Medido no Chatwoot do usuario: a
   conta tem 22 conversas, 11 com mensagens de entrada, e sao CLIENTES REAIS —
   uma delas, do Joao Pedro, diz literalmente "Quero cancelar". Um leitor que
   varresse a conta inteira obedeceria a ele.

2. **Prefixo estrito.** Comandos comecam com ponto (`.cancelar`), a mesma
   convencao que o grupo do usuario ja usa (`.offline`). Sem o prefixo,
   qualquer conversa sobre "cancelar o silencio" viraria uma acao.

3. **So `incoming`.** `message_type == 0`. O scanner nunca pode obedecer as
   proprias mensagens — um comando ecoado viraria laco infinito.

E UMA QUARTA, contra repeticao: cada mensagem so e obedecida uma vez, por id.
O registro e o mesmo `.agenda/`, entao vale entre reinicios e entre as duas
instancias do usuario.

NOTA DE CAMPO (2026-08-24): o grupo do usuario NAO entrega mensagens de entrada
ao Chatwoot — a ponte Baileys vem com ingestao de grupo desligada. Conversas
1-a-1 entregam normalmente. Por isso a conversa de comandos e configuravel
separada da de avisos: da para receber comando no privado e responder no grupo.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum

# Todo comando comeca com isto. Mesma convencao do `.offline` que o grupo ja
# usa, entao nao e vocabulario novo para ninguem.
PREFIXO = "."

# Chatwoot usa INT em message_type. 0 = incoming (pessoa), 1 = outgoing (bot).
# Descoberto lendo a API de verdade — a documentacao fala em strings.
MESSAGE_TYPE_INCOMING = 0


class Comando(Enum):
    """O que o scanner aceita obedecer. Fechado de proposito.

    Cada item aqui e uma coisa que qualquer pessoa do grupo pode mandar o
    scanner fazer. A lista curta nao e falta de imaginacao — e o limite do
    estrago possivel.
    """

    CANCELAR_SILENCIO = "cancelar_silencio"
    STATUS = "status"


# As formas escritas que valem para cada comando. Varias por comando porque
# ninguem lembra a sintaxe exata no meio de um farm.
_VOCABULARIO: dict[str, Comando] = {
    "cancelar": Comando.CANCELAR_SILENCIO,
    "cancelarsilencio": Comando.CANCELAR_SILENCIO,
    "silencio": Comando.CANCELAR_SILENCIO,
    "voltar": Comando.CANCELAR_SILENCIO,
    "status": Comando.STATUS,
    "scanner": Comando.STATUS,
}


@dataclass(frozen=True)
class MensagemDeComando:
    """Uma mensagem que pede alguma coisa ao scanner."""

    id: int
    comando: Comando
    autor: str | None
    texto: str


def interpretar(texto: str | None) -> Comando | None:
    """Que comando este texto pede? None quando nao pede nenhum.

    Exige o prefixo. "vamos cancelar o silencio?" nao e comando; ".cancelar" e.
    A diferenca entre conversar sobre uma acao e pedir a acao tem que ser
    visivel no texto, senao o scanner age no meio de uma conversa.
    """
    if not texto:
        return None

    primeira = texto.strip().split()
    if not primeira:
        return None

    palavra = primeira[0]
    if not palavra.startswith(PREFIXO):
        return None

    # `.cancelar` e `.cancelar silencio` sao o mesmo pedido — juntamos as duas
    # primeiras palavras para aceitar as duas formas sem gramatica nenhuma.
    miolo = palavra[len(PREFIXO) :].lower()
    if len(primeira) > 1:
        junto = (miolo + primeira[1].lower()).replace("-", "").replace("_", "")
        if junto in _VOCABULARIO:
            return _VOCABULARIO[junto]

    return _VOCABULARIO.get(miolo.replace("-", "").replace("_", ""))


def comandos_novos(
    mensagens: list[dict],
    ja_obedecidos: set[str],
) -> list[MensagemDeComando]:
    """Filtra o que veio da API e devolve so o que deve ser obedecido.

    Funcao pura — recebe a resposta ja decodificada. E o que permite testar
    todas as travas sem rede e sem um Chatwoot de verdade.
    """
    achados: list[MensagemDeComando] = []
    for bruta in mensagens:
        # TRAVA 3: nunca obedecer as proprias mensagens.
        if bruta.get("message_type") != MESSAGE_TYPE_INCOMING:
            continue
        # Nota privada de agente nao e pedido de ninguem do grupo.
        if bruta.get("private"):
            continue

        identificador = bruta.get("id")
        if identificador is None:
            continue
        if chave_da_mensagem(identificador) in ja_obedecidos:
            continue

        comando = interpretar(bruta.get("content"))
        if comando is None:
            continue

        remetente = bruta.get("sender") or {}
        achados.append(
            MensagemDeComando(
                id=int(identificador),
                comando=comando,
                autor=remetente.get("name"),
                texto=str(bruta.get("content", "")),
            )
        )

    achados.sort(key=lambda m: m.id)
    return achados


def chave_da_mensagem(identificador: int | str) -> str:
    """Chave duravel de 'ja obedeci esta mensagem'.

    Prefixo proprio para nao se confundir com os marcadores de aviso e de
    cancelamento, que dividem o mesmo diretorio.
    """
    return f"comando_{identificador}"


class LeitorDeComandos:
    """Puxa mensagens novas do Chatwoot, com cadencia.

    Cadencia porque isto e rede: a 1 Hz seriam 86 mil requisicoes por dia por
    instancia, para um comando que o usuario manda uma vez por semana. A
    latencia de alguns segundos e irrelevante para "cancele o silencio".
    """

    def __init__(
        self,
        url: str,
        conta: str,
        token: str,
        conversas: list[str],
        segundos_entre_leituras: float = 20.0,
        user_agent: str = "",
    ) -> None:
        self._url = url.rstrip("/")
        self._conta = conta
        self._token = token
        self._conversas = list(conversas)
        self._intervalo = segundos_entre_leituras
        self._user_agent = user_agent
        self._ultima_leitura: float | None = None
        self.falhas = 0

    @property
    def ativo(self) -> bool:
        """Ha conversa configurada para ouvir?"""
        return bool(self._conversas)

    def vencido(self, agora: float) -> bool:
        return (
            self._ultima_leitura is None
            or agora - self._ultima_leitura >= self._intervalo
        )

    def ler(self, agora: float) -> list[dict]:
        """Mensagens cruas das conversas de comando. Vazio se nao venceu.

        NUNCA levanta. Uma falha de rede no caminho de ENTRADA nao pode
        derrubar o scanner — o trabalho dele e vigiar a party, e ouvir comando
        e um extra. As falhas sao contadas para o resumo de sessao.
        """
        if not self._conversas or not self.vencido(agora):
            return []
        self._ultima_leitura = agora

        tudo: list[dict] = []
        for conversa in self._conversas:
            try:
                tudo.extend(self._puxar(conversa))
            except Exception:  # noqa: BLE001 — ver docstring
                self.falhas += 1
        return tudo

    def _puxar(self, conversa: str) -> list[dict]:
        alvo = (
            f"{self._url}/api/v1/accounts/{self._conta}"
            f"/conversations/{conversa}/messages"
        )
        req = urllib.request.Request(alvo, method="GET")
        req.add_header("api_access_token", self._token)
        req.add_header("Accept", "application/json")
        if self._user_agent:
            req.add_header("User-Agent", self._user_agent)

        with urllib.request.urlopen(req, timeout=10) as resposta:
            dados = json.loads(resposta.read())
        return dados.get("payload", []) if isinstance(dados, dict) else []
