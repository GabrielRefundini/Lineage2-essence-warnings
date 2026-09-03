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

    `suspeita_de_intent_desligada` e uma ANOTACAO, nunca uma decisao. Ela existe
    para a beirada gritar; a mensagem segue ACEITA e a linha segue montada.
    """

    decisao: Decisao
    linha: str = ""
    suspeita_de_intent_desligada: bool = False


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
        #
        # A heuristica entra DEPOIS de a mensagem ja estar aceita, e so anota.
        # Ela nao e uma quarta trava: e um bilhete preso na mensagem que a
        # beirada le para gritar. Ver `parece_intent_desligada`.
        return Resultado(
            Decisao.ACEITA,
            linha_do_console(mensagem),
            suspeita_de_intent_desligada=parece_intent_desligada(mensagem),
        )


def linha_do_console(mensagem: MensagemRecebida) -> str:
    """O texto CRU, sem formatar e sem truncar.

    Formato e a Fase 2. Cortar aqui destruiria o proprio criterio 2 da fase:
    uma linha truncada nao distingue "o texto chegou inteiro" de "o texto
    chegou pela metade", e provar que o texto chega e a unica coisa que esta
    fase existe para fazer.
    """
    return f"[{mensagem.canal}] {mensagem.autor_nome}: {mensagem.texto}"


# ---------------------------------------------------------------------------
# O PRE-VOO DA INTENT MESSAGE CONTENT
#
# Mora aqui, e nao no `ponte_discord.py`, por um motivo pratico e nao estetico:
# assim a DECISAO do arranque — e nao apenas o `or` de duas flags — fica
# conferivel no Python global, sem `discord` instalado e sem um socket aberto.
# A beirada le as flags; quem decide o que fazer com elas e este arquivo.


class IntentDeConteudoDesligada(Exception):
    """O painel do Discord esta com MESSAGE CONTENT desligada, e a ponte recusa.

    Irma de `PonteInvalida`: capturada no `main`, virando `log.error` e codigo
    de saida 2. Ela existe para que a mensagem que o usuario le seja a NOSSA, em
    portugues, com os cliques — e nao um traceback em ingles da biblioteca.
    """


CONSERTO_DA_INTENT = """A intent MESSAGE CONTENT esta DESLIGADA no painel do Discord.

Sem ela o bot conecta, aparece online e PARECE saudavel — mas recebe toda
mensagem com o texto VAZIO. Por isso a ponte prefere nao subir: uma ponte que
replica branco e pior do que uma ponte que nao sobe, porque ninguem percebe.

Conserto, na ordem:

  1. Abra https://discord.com/developers/applications
  2. Escolha a sua aplicacao.
  3. Clique em "Bot", no menu da esquerda.
  4. Em "Privileged Gateway Intents", ligue MESSAGE CONTENT INTENT.
  5. Clique em "Save Changes". O painel NAO salva sozinho.
  6. Suba a ponte de novo — a intent so vale na proxima conexao.

Os 4 passos completos do primeiro uso estao no PORTAO-DISCORD.txt."""


SAIDA_SE_O_PRE_VOO_ESTIVER_ERRADO = """Se voce TEM CERTEZA de que MESSAGE CONTENT ja esta ligada e salva no painel,
suba a ponte assim, uma vez:

    ponte-discord.bat --ignorar-pre-voo

Isso pula so esta conferencia. Se a intent estiver mesmo desligada, o proprio
Discord vai fechar a conexao e voce vai ler este mesmo texto de novo — a saida
existe para o caso de a conferencia estar errada, nao para esconder o problema."""


class VereditoDoPreVoo(Enum):
    """As TRES saidas do pre-voo. Tres, e nao duas, e essa e a decisao inteira.

    `SEGUIR_COM_AVISO` existe porque "nao consegui ler as flags" nao e a mesma
    coisa que "as flags dizem que esta desligada" — e tratar as duas igual e o
    que trancaria a porta por fora.
    """

    SEGUIR = "seguir"
    RECUSAR = "recusar"
    SEGUIR_COM_AVISO = "seguir_com_aviso"


def intent_ligada_no_painel(verificada: bool, limitada: bool) -> bool:
    """As duas flags de conteudo de mensagem do gateway, com um `or`.

    `gateway_message_content` (1<<18) e da aplicacao VERIFICADA — a que passou
    de 100 servidores e pediu aprovacao a Discord. `gateway_message_content_limited`
    (1<<19) e da aplicacao pequena, que e o caso desta ponte: um servidor so,
    sem verificacao.

    Ler so a primeira recusaria toda aplicacao pequena, ou seja, justamente
    esta. Ler so a segunda quebraria no dia em que o bot crescesse. O `or` cobre
    os dois estados e nao custa nada.
    """
    return bool(verificada or limitada)


def veredito_do_pre_voo(
    flags_lidas: bool, verificada: bool, limitada: bool, ignorar: bool
) -> VereditoDoPreVoo:
    """A PORTA do pre-voo. Funcao pura: entra o que se apurou, sai a decisao.

    A ORDEM E O CONTRATO:

      1. `ignorar` verdadeiro devolve `SEGUIR_COM_AVISO` antes de qualquer
         coisa — a valvula de escape nao pode depender do que ela existe para
         atropelar.
      2. `flags_lidas` falso devolve `SEGUIR_COM_AVISO`.
      3. So com as flags lidas o predicado decide entre `SEGUIR` e `RECUSAR`.

    POR QUE "NAO CONSEGUI LER" NUNCA VIRA RECUSA. Se a leitura falhar — outra
    versao da biblioteca, um soluco do `GET /applications/@me`, um formato de
    aplicacao que a leitura de fonte nao cobriu — o inteiro chega 0 e os dois
    bits leem falso. Um pre-voo de duas saidas RECUSARIA A SUBIDA COM A INTENT
    LIGADA, e a unica coisa que a tela saberia dizer ao usuario seria: refaca os
    quatro passos do portao que voce acabou de fazer. Sem saida nenhuma.

    A ASSIMETRIA DECIDE, E ELA E ENORME. Recusar por engano custa o milestone
    inteiro e nao tem conserto pela tela. Seguir por engano nao custa nada: a
    `PrivilegedIntentsRequired` da biblioteca ainda aborta o laco quando o
    gateway fechar em 4014, e a heuristica de runtime ainda grita na primeira
    mensagem vazia. Um pre-voo que confunde AUSENCIA DE INFORMACAO com
    INFORMACAO NEGATIVA e um pre-voo que um dia tranca a porta por fora.
    """
    if ignorar:
        return VereditoDoPreVoo.SEGUIR_COM_AVISO

    if not flags_lidas:
        return VereditoDoPreVoo.SEGUIR_COM_AVISO

    if intent_ligada_no_painel(verificada, limitada):
        return VereditoDoPreVoo.SEGUIR

    return VereditoDoPreVoo.RECUSAR


def parece_intent_desligada(mensagem: MensagemRecebida) -> bool:
    """A terceira linha: AVISA, E NAO DESCARTA. Nunca troque isso.

    O fato que sustenta a heuristica: o Discord NAO deixa postar uma mensagem
    sem nada dentro. Uma mensagem comum que chega com texto, anexo, embed,
    figurinha, componente, enquete e encaminhamento todos vazios nao e uma
    mensagem que alguem conseguiria escrever — e o retrato de uma censura de
    conteudo no caminho, ou seja, da intent desligada.

    ELA EXISTE PARA UM CASO SO: o botao ser desligado no painel com a ponte JA
    RODANDO. O pre-voo roda uma vez, no arranque, e e deterministico; esta roda
    sempre e e probabilistica. Por isso ela anota e a beirada grita.

    OS FALSOS POSITIVOS CONHECIDOS, E O QUE OS CORTA:

    - Mensagem de SISTEMA (entrou no servidor, fixou mensagem, criou thread,
      deu boost) e vazia POR DIREITO e frequente. Ela sai antes de tudo. Sem
      esta linha a ponte gritaria todo dia, e um aviso diario deixa de ser lido
      exatamente quando importa.
    - Post so-com-imagem, so-embed, so-figurinha, so-componente: vazios de texto
      e legitimos. Sao a FORM-04 da Fase 2, e nao podem sumir nem virar alarme.

    `enquete` e `encaminhamento` estao na lista SEM confirmacao de que a intent
    os censura (Assumptions A1 e A2 da pesquisa). Mante-los custa, no pior caso,
    um aviso a menos numa mensagem que ja estava estranha. Tira-los custaria, no
    pior caso, um alarme falso recorrente. Essa assimetria decide, e ela esta
    registrada aqui para que quem confirmar o fato um dia saiba o que mexer.
    """
    if mensagem.e_mensagem_de_sistema:
        return False

    return not (
        mensagem.texto
        or mensagem.tem_anexo
        or mensagem.tem_embed
        or mensagem.tem_figurinha
        or mensagem.tem_componente
        or mensagem.tem_enquete
        or mensagem.e_encaminhamento
    )


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
    "CONSERTO_DA_INTENT",
    "SAIDA_SE_O_PRE_VOO_ESTIVER_ERRADO",
    "ClienteDiscordEmMemoria",
    "Decisao",
    "IntentDeConteudoDesligada",
    "MensagemRecebida",
    "NucleoDaPonte",
    "Resultado",
    "VereditoDoPreVoo",
    "intent_ligada_no_painel",
    "linha_do_console",
    "mensagem_de_teste",
    "parece_intent_desligada",
    "veredito_do_pre_voo",
]
