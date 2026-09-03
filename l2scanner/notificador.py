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
import secrets
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import Empty, Queue
from typing import TYPE_CHECKING, Protocol

from .rastreador import Evento, TipoDeEvento

if TYPE_CHECKING:  # pragma: no cover - so para o type checker
    # SO em tempo de checagem, e a razao e a direcao da dependencia: o
    # transporte nao pode importar o desenho, porque o desenho arrasta `cv2`
    # para um modulo cuja unica funcao e falar HTTP. Em execucao, `montar_
    # multipart` so precisa dos tres campos de `Anexo`.
    from .retrato import Anexo

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

    ESTES SAO OS TEXTOS MAIS RECORRENTES DO PROJETO, e por isso os de
    orcamento mais apertado (2026-09-02, a pedido do usuario): eles chegam
    durante o farm, um por evento, e sao lidos numa olhada. O corte esta em
    `tests/test_mensagens_curtas.py`.

    O QUE SAIU DE CADA UM FOI A LISTA DE CAUSAS POSSIVEIS, e a razao e sempre
    a mesma: nao havia o que fazer com ela. A cegueira dizia "pode ser tela de
    loading, jogo minimizado ou cliente fechado" e a queda dizia "pode ser
    queda de conexao ou manutencao do servidor". Quem le esta longe do PC (e o
    caso inteiro para o alerta existir) e nao pode agir sobre nenhuma delas. O
    que ficou e a CONSEQUENCIA, que e o que muda o comportamento de quem le:
    que nada esta sendo detectado agora, e que houve um intervalo cego.

    QUEM ESTA NA FRENTE DO PC NAO PERDEU NADA: `formatar_console` continua com
    a redacao propria dele, e o `scanner.log` guarda o diagnostico completo.

    A REDACAO HEDGED SOBREVIVEU AO CORTE, e essa e a linha que nao se cruza.
    "HP zerado, possivel morte" nao virou "morreu": encurtar nao pode virar
    afirmar, porque o unico jeito de a party parar de confiar no scanner e ele
    afirmar uma morte que nao houve.

    O TRAVESSAO SAIU DE QUATRO DESTAS FRASES, e isso e conserto e nao estilo:
    o caminho ate o WhatsApp passa por `cp1252`, e um travessao chega no
    celular como caractere corrompido. As frases afetadas eram MORREU,
    CEGUEIRA_LONGA, VISAO_RECUPERADA, VOCE_SEM_PARTY e JOGO_CAIU.
    """
    hora = datetime.fromtimestamp(evento.momento).strftime("%H:%M")

    if evento.tipo is TipoDeEvento.MORREU:
        return f"[{hora}] {evento.membro}: HP zerado, possivel morte na PT."

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
            f"[{hora}] Sem visao da party ha {tempo}. "
            f"Eventos nesse periodo nao serao detectados."
        )

    if evento.tipo is TipoDeEvento.VISAO_RECUPERADA:
        tempo = _duracao_legivel(evento.segundos_no_estado or 0)
        return (
            f"[{hora}] Voltei a enxergar a party. Estive cego {tempo}, "
            f"posso ter perdido eventos."
        )

    if evento.tipo is TipoDeEvento.VOCE_SEM_PARTY:
        quem = evento.membro or "Voce"
        return (
            f"[{hora}] {quem} saiu ou foi removido da party. "
            f"Vigiando so o proprio personagem."
        )

    if evento.tipo is TipoDeEvento.VOCE_ENTROU_EM_PARTY:
        quem = evento.membro or "Voce"
        return f"[{hora}] {quem} entrou em party. Voltei a vigiar o grupo."

    if evento.tipo is TipoDeEvento.JOGO_CAIU:
        quem = evento.membro or "O jogo"
        motivo = (
            "voltou para a tela de login"
            if evento.detalhe == "tela de login"
            else "foi desconectado do servidor"
        )
        return (
            f"[{hora}] O cliente do {quem} {motivo}. "
            f"Nao vigio ninguem ate ele voltar."
        )

    if evento.tipo is TipoDeEvento.JOGO_VOLTOU:
        quem = evento.membro or "O jogo"
        return (
            f"[{hora}] O cliente do {quem} voltou ao jogo. "
            f"Voltei a vigiar a party."
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

    if evento.tipo is TipoDeEvento.VOCE_SEM_PARTY:
        return f"{(evento.membro or 'VOCE').upper()} SAIU OU FOI REMOVIDO DA PARTY"

    if evento.tipo is TipoDeEvento.VOCE_ENTROU_EM_PARTY:
        return f"{(evento.membro or 'VOCE').upper()} ENTROU EM PARTY"

    if evento.tipo is TipoDeEvento.JOGO_CAIU:
        motivo = (
            "TELA DE LOGIN"
            if evento.detalhe == "tela de login"
            else "DESCONECTADO DO SERVIDOR"
        )
        return f"O JOGO CAIU - {motivo} - NADA E DETECTADO AGORA"

    if evento.tipo is TipoDeEvento.JOGO_VOLTOU:
        return "O JOGO VOLTOU - vigiando a party de novo"

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


# Quais tipos de evento se juntam quando caem no MESMO tick.
#
# A regra de admissao e uma so: agrupar AFIRMA CAUSA COMUM, entao so entra
# quem tem uma. Quatro barras zerando dentro do mesmo segundo tem uma causa
# fisica unica (a AoE que pegou a party), e "4 membros com HP zerado ao mesmo
# tempo" e uma frase verdadeira sobre ela. As voltas de HP do mesmo tick vem
# da mesma ressurreicao em area, ou da mesma sequencia de rez que a party fez
# reagindo aquele wipe -- e cada uma ainda carrega o proprio "apos 13s", que o
# texto agrupado preserva membro a membro.
#
# SAIU e ENTROU ficam de fora DE PROPOSITO, e nao por falta de tempo: a tela
# nao distingue "o lider desfez a party" de "tres pessoas sairam por conta
# propria". As duas cenas produzem os mesmos pixels, entao uma frase unica
# afirmaria uma causa comum que o scanner nao viu -- o oposto do que o resto
# deste arquivo faz. Alem disso ninguem precisa correr para socorrer quem
# saiu; a rajada ali custa incomodo, e nao credibilidade.
#
# Os demais tipos (cegueira, jogo caiu, voce sem party) nao chegam a ser uma
# escolha: sao no maximo um por tick, por construcao do rastreador.
TIPOS_AGRUPAVEIS = (TipoDeEvento.MORREU, TipoDeEvento.RESSUSCITOU)


def _lista_legivel(itens: list[str]) -> str:
    """"A, B e C" -- o "e" por extenso, e nao um sufixo colado.

    Uma regra de plural por concatenacao acerta o substantivo e erra o verbo,
    e o erro so aparece no dia em que houver mais de um -- que e o dia do farm
    real. Ja aconteceu neste projeto (5f1aa97, "estas" no lugar de "estao").
    """
    if len(itens) == 1:
        return itens[0]
    return f"{', '.join(itens[:-1])} e {itens[-1]}"


def formatar_grupo(
    eventos: list[Evento], membros_vigiados: int | None = None
) -> str:
    """Um texto so para os eventos de um mesmo tipo VINDOS DO MESMO TICK.

    Sem isto, o wipe das 13:58 saiu como quatro notificacoes no mesmo segundo
    para um evento so, e as duas voltas de HP das 13:59 como mais duas. O
    grupo de WhatsApp e o ativo mais fragil do produto: um grupo que recebe
    rajada aprende a ignorar o grupo, e ai o alerta seguinte -- o que importa
    -- chega num canal que ninguem mais le.

    A REDACAO CONTINUA HEDGED. "3 morreram" nao sobrevive a um falso positivo;
    "3 membros com HP zerado ao mesmo tempo, possiveis mortes" sobrevive. O
    scanner le pixels, nao le a verdade, e agrupar nao lhe da certeza nenhuma
    que ele nao tinha evento a evento.

    `membros_vigiados` e quantas pessoas o scanner estava enxergando NESTE
    tick. So com esse numero da para afirmar "a party inteira": sem ele, ou
    com mortes de menos, o texto lista os nomes e nao usa a palavra wipe.
    """
    if len(eventos) == 1:
        # Nunca deveria chegar aqui, mas se chegar tem de sair identico ao
        # texto de hoje: ha muitos testes -- e um usuario -- contando com ele.
        return formatar(eventos[0])

    hora = datetime.fromtimestamp(eventos[0].momento).strftime("%H:%M")
    quantos = len(eventos)

    if eventos[0].tipo is TipoDeEvento.MORREU:
        # A PARTY INTEIRA GANHA FRASE PROPRIA, e sem lista de nomes.
        #
        # Quando todo mundo que estava sendo visto cai junto, os nomes nao
        # acrescentam informacao -- o conjunto e "todos". "Wipe" e a palavra
        # que a party ja usa para isso, cabe na previa da notificacao do
        # celular e diz o que aconteceu antes de a pessoa abrir o app.
        if membros_vigiados is not None and quantos == membros_vigiados:
            return (
                f"[{hora}] PARTY INTEIRA com HP zerado ao mesmo tempo "
                f"({quantos} membros). Possivel wipe na PT."
            )
        nomes = [evento.membro or "?" for evento in eventos]
        return (
            f"[{hora}] {quantos} membros com HP zerado ao mesmo tempo: "
            f"{_lista_legivel(nomes)}. Possiveis mortes na PT."
        )

    if eventos[0].tipo is TipoDeEvento.RESSUSCITOU:
        # CADA UM MANTEM O PROPRIO TEMPO. "HP de volta apos 13s" e "apos 12s"
        # nao sao a mesma informacao: quem ficou mais tempo morto e quem a
        # party demorou mais para socorrer, e e isso que se olha depois. Um
        # tempo unico para o grupo seria um numero inventado.
        partes = []
        for evento in eventos:
            quem = evento.membro or "?"
            if evento.segundos_no_estado:
                tempo = _duracao_legivel(evento.segundos_no_estado)
                partes.append(f"{quem} (apos {tempo})")
            else:
                partes.append(quem)
        return f"[{hora}] {quantos} membros com HP de volta: {_lista_legivel(partes)}."

    # Tipo fora do escopo caiu aqui por engano: melhor repetir as mensagens de
    # hoje do que inventar uma frase que ninguem escreveu.
    return "\n".join(formatar(evento) for evento in eventos)


def formatar_tick(
    eventos: list[Evento], membros_vigiados: int | None = None
) -> list[str]:
    """Os textos de UM tick, com os simultaneos ja consolidados.

    AGRUPA SO DENTRO DO MESMO TICK, E NUNCA ESPERA -- e essa e a razao de o
    conserto ser barato. A tentacao obvia era juntar mortes numa janela de
    3 segundos, mas isso paga atraso justamente no alerta que mais precisa de
    velocidade: o produto inteiro existe para a party socorrer alguem a tempo,
    e a latencia alvo (captura de 1 Hz + debounce) ja consome o orcamento
    inteiro. Dentro de um tick a consolidacao e de graca, porque a lista de
    eventos ja existe e ja esta completa -- nao ha nada a esperar.

    O AGRUPAMENTO E DE APRESENTACAO, SO. Quem chama continua registrando um
    evento por evento; esta funcao decide apenas quantas MENSAGENS saem.

    A ordem das mensagens segue a ordem dos eventos: o texto do grupo ocupa a
    posicao do primeiro evento daquele tipo.
    """
    grupos: dict[TipoDeEvento, list[Evento]] = {}
    for evento in eventos:
        if evento.tipo in TIPOS_AGRUPAVEIS:
            grupos.setdefault(evento.tipo, []).append(evento)

    textos: list[str] = []
    ja_saiu: set[TipoDeEvento] = set()
    for evento in eventos:
        grupo = grupos.get(evento.tipo)
        if grupo is None or len(grupo) == 1:
            # Caminho de UM evento: byte a byte o texto de sempre.
            textos.append(formatar(evento))
            continue
        if evento.tipo in ja_saiu:
            continue
        ja_saiu.add(evento.tipo)
        textos.append(formatar_grupo(grupo, membros_vigiados))

    return textos


class Notificador(Protocol):
    """Para onde os alertas vao. Trocar o adaptador e o modo simulacao.

    `anexos` e `texto_sem_anexos` sao OPCIONAIS e so aparecem no caminho da
    pergunta do batismo, que e o unico que leva imagem. Quem entrega texto
    continua sendo chamado com dois argumentos, e nada no caminho de sempre
    precisou aprender o que e um anexo.
    """

    def enviar(
        self,
        texto: str,
        conversa_alvo: str | None = None,
        anexos: Sequence["Anexo"] | None = None,
        texto_sem_anexos: str | None = None,
    ) -> None: ...


class NotificadorDeConsole:
    """Modo simulacao: mostra no console, nao envia nada."""

    def __init__(self, escrever=print) -> None:
        self._escrever = escrever

    def enviar(
        self,
        texto: str,
        conversa_alvo: str | None = None,
        anexos: Sequence["Anexo"] | None = None,
        texto_sem_anexos: str | None = None,
    ) -> None:
        destino = f" -> conversa {conversa_alvo}" if conversa_alvo else ""
        # O sufixo so aparece quando ha imagem: o `--dry-run` de todo o resto
        # do produto tem de continuar imprimindo a linha de sempre.
        imagens = f" (+{len(anexos)} imagens)" if anexos else ""
        self._escrever(f"  [simulacao{destino}] {texto}{imagens}")


class NotificadorEmMemoria:
    """Para testes: guarda o que seria enviado."""

    def __init__(self) -> None:
        self.enviados: list[str] = []
        # (texto, conversa_alvo), para os testes que verificam ONDE saiu.
        self.destinos: list[tuple[str, str | None]] = []
        # Os anexos de cada envio, na ordem dos envios.
        self.anexados: list[tuple[str, ...]] = []

    def enviar(
        self,
        texto: str,
        conversa_alvo: str | None = None,
        anexos: Sequence["Anexo"] | None = None,
        texto_sem_anexos: str | None = None,
    ) -> None:
        self.enviados.append(texto)
        self.destinos.append((texto, conversa_alvo))
        self.anexados.append(
            tuple(anexo.nome_do_arquivo for anexo in anexos or ())
        )


@dataclass
class ConfigChatwoot:
    url: str
    conta: str
    token: str
    conversas: list[str]

    # De onde o scanner aceita COMANDO. Vazia por padrao: abrir a volta e abrir
    # superficie de ataque, e isso nao pode acontecer por acidente de config.
    conversas_de_comando: list[str] = field(default_factory=list)

    # Quem pode mandar comando. Vazia = qualquer um da conversa permitida.
    telefones_de_comando: list[str] = field(default_factory=list)

    # Etiqueta do Chatwoot que transforma uma conversa em canal de comando.
    # Interruptor de administracao: marcar e desmarcar no painel vale na hora.
    etiqueta_de_comando: str = ""


class ErroDeEntrega(Exception):
    """Falhou o envio. Distingue transitorio de definitivo."""

    def __init__(self, mensagem: str, transitorio: bool) -> None:
        super().__init__(mensagem)
        self.transitorio = transitorio


# ---------------------------------------------------------------------------
# O ANEXO: `multipart/form-data` montado a mao, com a stdlib
# ---------------------------------------------------------------------------
#
# POR QUE A MAO, E NAO UMA BIBLIOTECA
#
# Este projeto fala `urllib.request`. `requests` NAO esta na arvore, e o
# `test_firewall_escopo` existe justamente para que a arvore de dependencias
# seja uma decisao e nao um acidente. Montar o envelope custa ~20 linhas.
#
# E o custo vem com um ganho que uma biblioteca nao daria: como o corpo e
# construido por uma funcao pura, ele e COMPARAVEL BYTE A BYTE NUM TESTE SEM
# REDE NENHUMA. A peca mais chata do recurso e tambem a unica que da para
# provar inteira offline.

_CRLF = b"\r\n"

# Quantos bytes de aleatorio a fronteira carrega. 16 bytes hex (128 bits) e
# folga absurda para o unico requisito real, que e nao aparecer dentro de um
# PNG de ~5 KB.
_BYTES_DA_FRONTEIRA = 16


def escolher_fronteira(
    anexos: Sequence["Anexo"], gerar: Callable[[], str] | None = None
) -> str:
    """Uma fronteira que NAO aparece dentro de nenhum anexo.

    Uma fronteira que existe no conteudo corta a mensagem ao meio: o servidor
    aceita o que veio antes dela e o usuario recebe meio PNG. Com 128 bits de
    aleatorio a chance e desprezivel — e "desprezivel" nao e "impossivel", e o
    desfecho de um anexo truncado nao e um erro visivel, e uma imagem
    corrompida que o dono nao consegue ler.

    Conferir custa uma varredura sobre ~40 KB. `gerar` e injetavel para que o
    teste force a colisao e prove que a escolha REAGE, em vez de confiar na
    sorte de nunca colidir.
    """
    gerar = gerar or (lambda: secrets.token_hex(_BYTES_DA_FRONTEIRA))
    for _ in range(16):
        candidata = gerar()
        marca = candidata.encode("ascii")
        if not any(marca in anexo.conteudo for anexo in anexos):
            return candidata
    # Dezesseis sorteios de 128 bits colidindo seguidos nao acontece por acaso.
    raise ErroDeEntrega(
        "nao consegui escolher uma fronteira livre", transitorio=False
    )


def _nome_de_arquivo_seguro(nome: str) -> str:
    """Sem aspas, sem barras e sem quebra de linha.

    O nome do arquivo entra DENTRO de um cabecalho. Hoje ele e sempre o apelido
    hex, que nao tem como conter nada disso; o dia em que alguem passar o nick
    do jogador aqui e o dia em que um `"` ou um CRLF vira cabecalho HTTP
    inventado. Fechar agora custa uma linha.
    """
    limpo = "".join(c for c in nome if c not in '"\\\r\n' and c.isprintable())
    return limpo or "anexo.png"


def montar_multipart(
    campos: Mapping[str, str], anexos: Sequence["Anexo"], fronteira: str
) -> bytes:
    """O corpo `multipart/form-data`, com os campos e depois os anexos.

    TODA quebra de linha e CRLF, e isso nao e preciosismo de RFC: um `\\n`
    solto faz o parser do outro lado ver UMA parte gigante em vez de tres, e o
    desfecho e um 422 que se parece com erro de token.

    A ORDEM DOS ANEXOS E A ORDEM DA LISTA, e ela e contrato. O texto da
    pergunta lista os apelidos numa ordem; se as imagens sairem noutra, o dono
    batiza a pessoa errada — que e exatamente a mentira plausivel que este
    projeto combate. (A defesa de verdade e o apelido desenhado DENTRO da
    imagem; a ordem e o segundo cinto.)
    """
    marca = f"--{fronteira}".encode("ascii")
    partes: list[bytes] = []

    for nome, valor in campos.items():
        partes.append(
            marca
            + _CRLF
            + f'Content-Disposition: form-data; name="{nome}"'.encode("utf-8")
            + _CRLF
            + _CRLF
            + str(valor).encode("utf-8")
            + _CRLF
        )

    for anexo in anexos:
        arquivo = _nome_de_arquivo_seguro(anexo.nome_do_arquivo)
        partes.append(
            marca
            + _CRLF
            + (
                'Content-Disposition: form-data; name="attachments[]"; '
                f'filename="{arquivo}"'
            ).encode("utf-8")
            + _CRLF
            + f"Content-Type: {anexo.tipo}".encode("utf-8")
            + _CRLF
            + _CRLF
            + anexo.conteudo
            + _CRLF
        )

    partes.append(marca + b"--" + _CRLF)
    return b"".join(partes)


class NotificadorChatwoot:
    """Envia via API do Chatwoot. Um POST por conversa de destino."""

    def __init__(self, config: ConfigChatwoot) -> None:
        self._config = config
        # Quantas vezes o anexo falhou e a mensagem saiu em texto puro. Contado
        # em vez de logado porque este modulo nao tem logger: quem quiser
        # mostrar isso no console le o numero.
        self.anexos_que_falharam = 0

    def enviar(
        self,
        texto: str,
        conversa_alvo: str | None = None,
        anexos: Sequence["Anexo"] | None = None,
        texto_sem_anexos: str | None = None,
    ) -> None:
        """Sem alvo, vai para as conversas de AVISO. Com alvo, so para ela.

        O alvo existe para RESPONDER onde perguntaram. Sem ele, um `.status`
        mandado no privado era respondido no grupo — mediu-se isso ao vivo:
        pergunta as 23:04:42 na conversa 1, resposta as 23:04:52 na 13.

        SEM `anexos`, NADA MUDA: o corpo continua sendo o mesmo JSON de
        sempre, byte a byte. O multipart e um caminho NOVO, e ele so existe
        quando ha imagem.
        """
        erros = []
        for conversa in [conversa_alvo] if conversa_alvo else self._config.conversas:
            try:
                if anexos:
                    self._postar_com_reserva(
                        conversa, texto, anexos, texto_sem_anexos or texto
                    )
                else:
                    self._postar(conversa, texto)
            except ErroDeEntrega as erro:
                erros.append((conversa, erro))

        if erros:
            # Se QUALQUER destino for transitorio, o lote merece nova tentativa
            transitorio = any(e.transitorio for _, e in erros)
            detalhes = "; ".join(f"conversa {c}: {e}" for c, e in erros)
            raise ErroDeEntrega(detalhes, transitorio=transitorio)

    def _postar(self, conversa: str, texto: str) -> None:
        corpo = json.dumps(
            {"content": texto, "message_type": "outgoing"}
        ).encode("utf-8")
        self._enviar_corpo(conversa, corpo, "application/json")

    def _postar_com_anexos(
        self, conversa: str, texto: str, anexos: Sequence["Anexo"]
    ) -> None:
        """UMA mensagem com N imagens, e nao N mensagens.

        O Chatwoot aceita varios `attachments[]` no mesmo POST, e usar isso e
        deliberado: a pergunta lista todas as pendentes de uma vez desde o
        inicio (D-04), e voltar a mandar uma bolha por pessoa desfaria o
        trabalho que CORR-03 acabou de fazer consolidando rajada. O grupo de
        WhatsApp e o ativo mais fragil do produto: um grupo que recebe rajada
        aprende a ignorar o grupo.
        """
        fronteira = escolher_fronteira(anexos)
        corpo = montar_multipart(
            {"content": texto, "message_type": "outgoing"}, anexos, fronteira
        )
        self._enviar_corpo(
            conversa, corpo, f"multipart/form-data; boundary={fronteira}"
        )

    def _postar_com_reserva(
        self,
        conversa: str,
        texto: str,
        anexos: Sequence["Anexo"],
        texto_de_reserva: str,
    ) -> None:
        """Tenta com imagem; se falhar, manda o texto puro assim mesmo.

        A ORDEM E A DECISAO, E ELA E SOBRE O MARCADOR. Quando esta funcao roda,
        o `perguntado_<chave>` de D-04 JA FOI QUEIMADO — ele e de mao unica e
        vale para sempre, entao daqui para a frente uma pergunta que nao sai e
        uma pessoa que fica "Membro N" ate alguem apagar um arquivo a mao. A
        unica regra que importa, entao, e: NENHUM caminho pode terminar sem uma
        tentativa de texto puro.

        Duas ordens cumprem essa regra, e a escolha entre elas e sobre o custo
        no caso NORMAL:

        - texto puro primeiro e imagens depois cumpriria, e custaria DUAS
          bolhas no grupo TODA VEZ — inclusive quando tudo funciona;
        - multipart primeiro e texto puro so na falha custa duas bolhas SO
          quando falha, e no caso de falha o dono ja perdeu a imagem de
          qualquer jeito.

        O QUE SE PAGA POR ISSO, ESCRITO: se o multipart chegar ao servidor e a
        resposta se perder no caminho, saem DUAS perguntas iguais. Pergunta
        repetida e barulho; pergunta que nunca sai e uma pessoa anonima para
        sempre. A escolha e pelo barulho.

        O `texto_de_reserva` e um texto DIFERENTE de proposito: o texto com
        imagem diz "mandei junto a imagem", e repetir essa frase numa mensagem
        sem anexo nenhum mandaria o dono procurar um arquivo que nao existe.
        """
        try:
            self._postar_com_anexos(conversa, texto, anexos)
            return
        except ErroDeEntrega:
            self.anexos_que_falharam += 1

        self._postar(conversa, texto_de_reserva)

    def _enviar_corpo(
        self, conversa: str, corpo: bytes, tipo_do_conteudo: str
    ) -> None:
        url = (
            f"{self._config.url}/api/v1/accounts/{self._config.conta}"
            f"/conversations/{conversa}/messages"
        )

        req = urllib.request.Request(url, data=corpo, method="POST")
        # Header plano, sem prefixo Bearer — e assim que o Chatwoot espera
        req.add_header("api_access_token", self._config.token)
        req.add_header("Content-Type", tipo_do_conteudo)
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


class Categoria(Enum):
    """De onde a mensagem veio, e se o silencio se aplica a ela.

    Existe porque durante TvT e Prime o scanner cala — mas os LEMBRETES de
    TvT e Prime tem que atravessar esse silencio. Sem essa distincao, de
    segunda a quinta o lembrete do TvT das 21h40 cairia dentro do silencio do
    Prime e a funcionalidade se anularia sozinha.
    """

    # Eventos do scanner: morte, saida, entrada, jogo caiu, cegueira.
    # Verdadeiros durante um TvT, e irrelevantes — em evento morre todo mundo
    # o tempo todo.
    NORMAL = "normal"

    # Avisos de agenda e mensagens de ciclo de vida. Atravessam o silencio.
    SEMPRE = "sempre"


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
        # Chamavel sem argumento que responde "estou em silencio agora?".
        # Injetado em vez de consultado por dentro: o Despachante nao deveria
        # precisar conhecer a agenda para entregar uma mensagem.
        self.em_silencio = lambda: False
        self.silenciados = 0
        # (texto, conversa_alvo). O alvo atravessa a fila porque a resposta
        # tem de sair na conversa onde a pergunta chegou, e a fila e
        # assincrona — a informacao se perderia se ficasse so na chamada.
        # (texto, conversa_alvo, anexos, texto_sem_anexos). Os dois ultimos
        # sao vazios em tudo que nao e a pergunta do batismo.
        self._fila: Queue[
            tuple[str, str | None, tuple, str | None] | None
        ] = Queue(maxsize=200)
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

    def despachar(
        self,
        texto: str,
        categoria: Categoria = Categoria.NORMAL,
        conversa_alvo: str | None = None,
        anexos: Sequence["Anexo"] | None = None,
        texto_sem_anexos: str | None = None,
    ) -> None:
        """Enfileira. Grava no outbox ANTES de qualquer tentativa de rede.

        O SILENCIO E CORTADO AQUI, no transporte, e nao na deteccao. Silenciar
        na deteccao corromperia o estado — quem morre e ressuscita durante o
        silencio precisa sair do outro lado com o estado certo — e apagaria o
        log, que e a unica ferramenta de depuracao pos-farm do projeto.

        A mensagem silenciada NAO entra no outbox. O outbox existe para
        garantir que nada se perca no caminho da rede; uma mensagem que
        decidimos nao enviar nao esta a caminho de lugar nenhum. Ela esta no
        log, que e onde ela pertence.
        """
        if categoria is Categoria.NORMAL and self.em_silencio():
            self.silenciados += 1
            return

        if self._outbox:
            registro = {"momento": time.time(), "texto": texto}
            if anexos:
                # SO os nomes: o outbox e um registro duravel para forense
                # pos-farm, e enfiar ~40 KB de PNG por pergunta dentro de um
                # JSONL que ninguem poda trocaria a utilidade dele por peso.
                registro["anexos"] = [
                    anexo.nome_do_arquivo for anexo in anexos
                ]
            with self._outbox.open("a", encoding="utf-8") as arquivo:
                arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")

        try:
            self._fila.put_nowait(
                (texto, conversa_alvo, tuple(anexos or ()), texto_sem_anexos)
            )
        except Exception:
            # Fila cheia: o evento ja esta no outbox, entao nada se perdeu de
            # verdade — mas o usuario precisa saber.
            self._ao_falhar(texto, "fila de envio cheia")

    def _laco(self) -> None:
        while self._rodando:
            try:
                item = self._fila.get(timeout=0.5)
            except Empty:
                continue

            if item is None:
                break

            texto, conversa_alvo, anexos, texto_sem_anexos = item
            self._tentar_entregar(
                texto, conversa_alvo, anexos, texto_sem_anexos
            )
            self._fila.task_done()

    def _tentar_entregar(
        self,
        texto: str,
        conversa_alvo: str | None = None,
        anexos: Sequence["Anexo"] = (),
        texto_sem_anexos: str | None = None,
    ) -> None:
        for tentativa in range(1, MAX_TENTATIVAS + 1):
            try:
                if anexos:
                    self._notificador.enviar(
                        texto,
                        conversa_alvo,
                        anexos=anexos,
                        texto_sem_anexos=texto_sem_anexos,
                    )
                else:
                    # A CHAMADA DE SEMPRE, com dois argumentos e nada mais.
                    # Um notificador de teste que so aceita `(texto)` ou
                    # `(texto, conversa_alvo)` continua servindo — e ha varios.
                    self._notificador.enviar(texto, conversa_alvo)
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
