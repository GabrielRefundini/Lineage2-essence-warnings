"""O miolo da ponte: dada uma mensagem ja normalizada, passa ou nao passa.

ZERO IMPORT DE TERCEIRO, pela mesma razao medida do `ponte_config.py`: o pytest
roda no Python GLOBAL (sem `discord`) e o `discord` vive no `.venv` de producao
(sem pytest). Este arquivo e o que torna a ponte testavel sem rede, sem
`asyncio` e sem `pytest-asyncio` — que nao esta instalado e nao vai entrar.

A FORMA E A DO `Sessao.tick(frame, momento)` (`sessao.py:187`): a beirada async
normaliza e chama um metodo SINCRONO que devolve estrutura. O precedente e o
`ocr.py:256`, onde o async fica na beirada e o miolo e sincrono. Aqui isso deixa
de ser intencao e vira estrutura de arquivo.

O FILTRO E SO O DO PROPRIO ID. Esta e a afirmacao central do modulo. O recorte
`if message.author.bot: return` e o mais copiado de tutorial de bot do Discord,
e aqui ele apagaria justamente o CASO PRINCIPAL: anuncio de guild costuma vir de
bot ou de webhook. A unica mensagem que a ponte descarta por autoria e a que ela
mesma enviou — sem isso, a Fase 3 vira laco de entrega (a ponte entrega, se ve,
entrega de novo). Nao ha filtro de cargo, nao ha filtro de mencao (PONTE-03).

A ORDEM DAS TRAVAS: canal fora da lista sai primeiro (PONTE-02, e a trava mais
barata e a que corta o servidor inteiro), mensagem da propria ponte sai depois
(PONTE-04), e mais nada filtra.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


@dataclass(frozen=True)
class MensagemRecebida:
    """A forma NORMALIZADA de uma mensagem, sem uma linha de `discord` dentro.

    Os sete booleanos do fim nao servem a esta fase: nascem agora porque a
    FORM-04 (postagem so-com-imagem nao pode sumir calada) e o aviso de intent
    desligada precisam saber que HAVIA algo na mensagem quando o texto vem
    vazio. Acrescenta-los depois obrigaria a mexer no normalizador, no nucleo e
    nos testes ao mesmo tempo — agora custa uma linha cada.
    """

    id: int
    canal: int
    autor: int
    autor_nome: str
    texto: str

    tem_anexo: bool = False
    tem_embed: bool = False
    tem_figurinha: bool = False
    tem_componente: bool = False
    tem_enquete: bool = False
    e_encaminhamento: bool = False
    e_mensagem_de_sistema: bool = False


class Decisao(Enum):
    """O que o nucleo decidiu, e por que.

    O motivo importa tanto quanto a decisao: quando o usuario disser "postei e
    nao apareceu", a diferenca entre IGNORADA_CANAL e IGNORADA_PROPRIA e a
    diferenca entre "voce postou no canal errado" e "a ponte esta se ouvindo".

    O `01-03-PLAN.md` acrescenta membros aqui (a mensagem ja vista, do livro de
    ja-vistos). Eles NAO sao inventados agora: um membro de enum sem codigo que
    o produza e um caminho morto que parece coberto.
    """

    ACEITA = "aceita"
    IGNORADA_CANAL = "ignorada_canal"
    IGNORADA_PROPRIA = "ignorada_propria"


@dataclass(frozen=True)
class Resultado:
    """A decisao e a linha PRONTA para o console.

    A linha vem daqui, e nao do `on_message`, para que a unica parte do caminho
    que o usuario efetivamente LE tenha teste. Decisao ignorada nao produz
    linha: imprimir o que foi recusado transformaria o console no servidor
    inteiro, e o console e a prova do criterio 2 da fase.
    """

    decisao: Decisao
    linha: str = ""


class NucleoDaPonte:
    """Quem decide. A beirada async nao decide nada.

    `id_da_ponte` pode nascer `None`, e isso e um estado DE PRE-CONEXAO
    LEGITIMO, nao um esquecimento: o `main` monta o nucleo ANTES do `run`, e
    nesse instante `Client.user` ainda e `None` — a ponte literalmente nao sabe
    quem ela e. Com `None` ninguem e descartado por autoria, o que e o
    comportamento certo, porque nao ha "eu" com que comparar.

    QUEM TIRA A PONTE DESSE ESTADO E O `on_ready`, chamando
    `definir_id_da_ponte(self.user.id)` ANTES de qualquer outra coisa. Um `None`
    que sobrevive a conexao nao e um padrao inofensivo: e a trava da PONTE-04
    desligada sem aviso, verde em todo teste que passa o id na mao e morta na
    maquina do usuario — e o sintoma so apareceria na Fase 3, como laco de
    entrega.
    """

    def __init__(
        self,
        guild: int,
        canais: frozenset[int],
        id_da_ponte: int | None = None,
    ) -> None:
        self._guild = guild
        self._canais = canais
        self._id_da_ponte = id_da_ponte

    @property
    def guild(self) -> int:
        return self._guild

    @property
    def canais(self) -> frozenset[int]:
        return self._canais

    @property
    def id_da_ponte(self) -> int | None:
        return self._id_da_ponte

    def definir_id_da_ponte(self, id_da_ponte: int) -> None:
        """Chamado pelo `on_ready`. IDEMPOTENTE de proposito.

        O `on_ready` dispara de novo a cada IDENTIFY, entao uma reconexao no
        meio do farm chama isto varias vezes — e nao pode mudar quem a ponte
        descarta.
        """
        self._id_da_ponte = id_da_ponte

    def receber(self, mensagem: MensagemRecebida) -> Resultado:
        """SINCRONO, sem `await`. A DECISAO MORA AQUI, E NAO NOS CHAMADORES."""
        # PONTE-02. Primeiro porque e a mais barata e a que corta mais: sem ela
        # a ponte repete o servidor inteiro. Um id de thread vive no mesmo
        # espaco de numeros que um id de canal, entao ele simplesmente nao casa
        # com o conjunto — thread fica de fora sem uma linha a mais.
        if mensagem.canal not in self._canais:
            return Resultado(Decisao.IGNORADA_CANAL)

        # PONTE-04. So o proprio id. O autor de um webhook e o id DO WEBHOOK, e
        # o de outro bot e o id daquele bot: nenhum dos dois e o meu, entao os
        # dois passam — que e o caso principal desta ponte.
        if self._id_da_ponte is not None and mensagem.autor == self._id_da_ponte:
            return Resultado(Decisao.IGNORADA_PROPRIA)

        # PONTE-03: e acabou. Nao existe filtro de autor, de cargo ou de mencao.
        return Resultado(Decisao.ACEITA, linha_do_console(mensagem))


def linha_do_console(mensagem: MensagemRecebida) -> str:
    """O texto CRU, sem formatar e sem truncar.

    Formato e a Fase 2. Cortar aqui destruiria o proprio criterio 2 da fase:
    uma linha truncada nao distingue "o texto chegou inteiro" de "o texto
    chegou pela metade", e provar que o texto chega e a unica coisa que esta
    fase existe para fazer.
    """
    return f"[{mensagem.canal}] {mensagem.autor_nome}: {mensagem.texto}"


class ClienteDiscordEmMemoria:
    """O duble que substitui o cliente do Discord inteiro. Sem rede, sem asyncio.

    Mora no CODIGO DE PRODUCAO, ao lado do nucleo, pelo mesmo motivo que o
    `NotificadorEmMemoria` mora em `notificador.py:209`: um duble no diretorio
    de testes diverge do que ele finge ser, e o teste passa a exercitar uma
    forma que nao existe.

    Sem ele, provar "bot passa, webhook passa, canal de fora nao passa" exigiria
    um servidor Discord de verdade e um humano postando — ou seja, nao seria
    provado nunca.
    """

    def __init__(self, nucleo: NucleoDaPonte) -> None:
        self._nucleo = nucleo
        self.mensagens: list[MensagemRecebida] = []
        self.resultados: list[Resultado] = []
        self.linhas: list[str] = []

    def entregar(self, mensagem: MensagemRecebida) -> Resultado:
        resultado = self._nucleo.receber(mensagem)
        self.mensagens.append(mensagem)
        self.resultados.append(resultado)
        if resultado.decisao is Decisao.ACEITA:
            self.linhas.append(resultado.linha)
        return resultado

    def entregar_todas(self, mensagens) -> list[Resultado]:
        return [self.entregar(mensagem) for mensagem in mensagens]


# Padroes da fabrica. Neutros de proposito: nenhum deles casa com um canal
# configurado, entao todo teste tem de dizer em QUAL canal a mensagem caiu.
_PADROES = MensagemRecebida(
    id=900000000000000001,
    canal=1000000000000000001,
    autor=2000000000000000002,
    autor_nome="Alguem",
    texto="teste da ponte 1",
)


def mensagem_de_teste(**campos) -> MensagemRecebida:
    """Fabrica com padroes sensatos, no molde do helper `evento(**kwargs)`.

    Mora em producao (e nao em `tests/`) para que o duble acima e os testes
    usem A MESMA fabrica: duas fabricas divergem no primeiro campo novo, e a
    partir dai o duble exercita uma mensagem que nao existe.
    """
    return replace(_PADROES, **campos)


__all__ = [
    "ClienteDiscordEmMemoria",
    "Decisao",
    "MensagemRecebida",
    "NucleoDaPonte",
    "Resultado",
    "linha_do_console",
    "mensagem_de_teste",
]
