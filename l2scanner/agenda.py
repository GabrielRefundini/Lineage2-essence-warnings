"""A agenda: o relogio como fonte de eventos.

Ate aqui o scanner so falava sobre o que via na tela. Esta camada responde uma
pergunta diferente — "que horas sao" — e por isso nao tem um unico pixel.

MESMA DISCIPLINA DO RASTREADOR, E PELO MESMO MOTIVO: **nao ha relogio proprio.**
O tempo entra por parametro. Sem isso, testar "o aviso do TvT das 21h50 de uma
quinta-feira" exigiria esperar ate quinta as 21h50, e a agenda nunca teria
cobertura de verdade. Com isso, os 7 dias da semana sao testados em
milissegundos.

TRES ARESTAS QUE PARECEM DETALHE E NAO SAO:

1. **O dia da semana vale para o EVENTO, nao para o aviso.** Um evento a 00:05
   de segunda avisa as 23:55 de DOMINGO. Se a checagem de dia olhasse o dia do
   aviso, esse evento nunca seria anunciado. Por isso as ocorrencias sao
   geradas a partir da data do EVENTO, e o aviso e derivado dela.

2. **Ontem e amanha entram na varredura.** Pelo mesmo motivo acima: as 23:57 de
   domingo, o aviso devido pertence a um evento de SEGUNDA. Varrer so "hoje"
   perderia toda virada de dia.

3. **Um aviso vencido nao ressuscita.** So dispara dentro de uma janela curta
   depois do alvo. Subir o scanner as 16h nao pode soltar o aviso das 15h — a
   party receberia um lembrete de um TvT que ja acabou.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path

# Quanto tempo depois do alvo um aviso ainda pode sair.
#
# Constante, e nao configuracao: e uma propriedade do laco (que roda a 1 Hz),
# nao uma preferencia do usuario. Mais um botao no config.toml e mais uma coisa
# para errar as duas da manha. Cinco minutos absorve um restart demorado sem
# ressuscitar aviso velho.
TOLERANCIA_MINUTOS = 5

# Nomes de dia como o usuario escreve no config.toml -> weekday() do Python,
# onde segunda e 0. Aceitos com e sem acento porque quem edita o arquivo a mao
# nao deveria ter que adivinhar.
DIAS_DA_SEMANA = {
    "seg": 0, "segunda": 0,
    "ter": 1, "terca": 1, "terça": 1,
    "qua": 2, "quarta": 2,
    "qui": 3, "quinta": 3,
    "sex": 4, "sexta": 4,
    "sab": 5, "sabado": 5, "sábado": 5,
    "dom": 6, "domingo": 6,
}

TODOS_OS_DIAS = frozenset(range(7))


class AgendaInvalida(Exception):
    """O config.toml tem agenda, mas ela nao faz sentido.

    Levantada no ARRANQUE, nunca no meio do farm. Um horario com erro de
    digitacao tem que derrubar o scanner enquanto o usuario esta olhando para o
    console, e nao as 15h enquanto ele esta AFK confiando no silencio.
    """


class TipoDeAviso(Enum):
    ANTES = "antes"
    AGORA = "agora"


@dataclass(frozen=True)
class EventoAgendado:
    """Um evento recorrente do jogo, como o usuario o descreveu."""

    nome: str
    horarios: tuple[tuple[int, int], ...]  # (hora, minuto)
    dias: frozenset[int] = TODOS_OS_DIAS
    avisar_minutos_antes: int = 10

    # Quanto tempo o scanner deve calar depois que o evento comeca. Lido aqui e
    # IGNORADO nesta fase — quem usa e a Fase 7. Mora no esquema desde ja para
    # o usuario nao ter que editar a mao um arquivo que ja editou.
    silenciar_minutos: int = 0


@dataclass(frozen=True)
class Aviso:
    """Um aviso que venceu e ainda nao foi enviado."""

    evento: str
    tipo: TipoDeAviso
    alvo: datetime  # o instante do EVENTO, nao o do aviso
    devido_em: datetime  # quando este aviso deveria ter saido

    @property
    def chave(self) -> str:
        """Identidade durável do aviso, para nunca mandar duas vezes.

        ESTRUTURADA, jamais o texto da mensagem. O texto muda toda vez que
        alguem melhora a redacao, e a chave nao pode mudar junto — senao um
        aviso ja enviado volta a parecer novo e a party recebe em dobro.
        """
        apelido = re.sub(r"[^a-z0-9]+", "-", self.evento.lower()).strip("-")
        return (
            f"{self.alvo.date().isoformat()}"
            f"_{apelido}-{self.alvo.hour:02d}{self.alvo.minute:02d}"
            f"_{self.tipo.value}"
        )


def _ocorrencias(evento: EventoAgendado, dia: date) -> list[datetime]:
    """Instantes em que este evento acontece nesta data.

    Vazio quando a data nao e um dia configurado. A checagem de dia mora AQUI,
    olhando a data do EVENTO — nunca a do aviso.
    """
    if dia.weekday() not in evento.dias:
        return []
    return [
        datetime(dia.year, dia.month, dia.day, hora, minuto)
        for hora, minuto in evento.horarios
    ]


def avisos_devidos(
    agora: datetime,
    eventos: list[EventoAgendado],
    ja_enviados: set[str],
    tolerancia_minutos: int = TOLERANCIA_MINUTOS,
) -> list[Aviso]:
    """Quais avisos venceram agora e ainda nao sairam.

    Funcao pura: mesmo instante, mesma agenda, mesmo conjunto de enviados ->
    mesma resposta, sempre. Sem relogio, sem disco, sem rede.
    """
    devidos: list[Aviso] = []
    tolerancia = timedelta(minutes=tolerancia_minutos)
    hoje = agora.date()

    # Ontem e amanha entram porque um aviso perto da meia-noite pertence a um
    # evento de outro dia. Varrer so "hoje" perderia toda virada de dia.
    for deslocamento in (-1, 0, 1):
        dia = hoje + timedelta(days=deslocamento)
        for evento in eventos:
            for alvo in _ocorrencias(evento, dia):
                candidatos = [
                    (
                        TipoDeAviso.ANTES,
                        alvo - timedelta(minutes=evento.avisar_minutos_antes),
                    ),
                    (TipoDeAviso.AGORA, alvo),
                ]
                for tipo, devido_em in candidatos:
                    if evento.avisar_minutos_antes <= 0 and tipo is TipoDeAviso.ANTES:
                        # Antecedencia zero: o aviso "antes" coincidiria com o
                        # "agora" e a party receberia a mesma coisa duas vezes.
                        continue
                    if not (devido_em <= agora < devido_em + tolerancia):
                        continue
                    aviso = Aviso(
                        evento=evento.nome, tipo=tipo, alvo=alvo, devido_em=devido_em
                    )
                    if aviso.chave in ja_enviados:
                        continue
                    devidos.append(aviso)

    devidos.sort(key=lambda a: (a.devido_em, a.tipo.value))
    return devidos


def proxima_ocorrencia(
    agora: datetime, eventos: list[EventoAgendado]
) -> tuple[str, datetime] | None:
    """O proximo evento e quando ele acontece. None se a agenda esta vazia.

    Existe para o console. Um scanner que nao diz quando vai falar de novo e
    indistinguivel de um scanner quebrado — e depois de um dia inteiro
    corrigindo alarme falso, parecer quebrado custa caro.
    """
    melhor: tuple[str, datetime] | None = None
    hoje = agora.date()
    # Oito dias cobrem qualquer agenda semanal a partir de qualquer momento.
    for deslocamento in range(0, 8):
        dia = hoje + timedelta(days=deslocamento)
        for evento in eventos:
            for alvo in _ocorrencias(evento, dia):
                if alvo <= agora:
                    continue
                if melhor is None or alvo < melhor[1]:
                    melhor = (evento.nome, alvo)
    return melhor


def texto_do_aviso(aviso: Aviso) -> str:
    """A mensagem que vai para o WhatsApp.

    O aviso de ANTES serve para parar o farm e se deslocar; o de AGORA serve
    para dizer que comecou. Textos diferentes porque servem a acoes diferentes
    — repetir a mesma frase duas vezes treinaria a party a ignorar as duas.
    """
    hora = f"{aviso.alvo.hour:02d}:{aviso.alvo.minute:02d}"
    if aviso.tipo is TipoDeAviso.ANTES:
        faltam = int((aviso.alvo - aviso.devido_em).total_seconds() // 60)
        return (
            f"{aviso.evento} comeca em {faltam} minutos, as {hora}. "
            f"Hora de voltar para a cidade e se preparar."
        )
    return f"{aviso.evento} comecou agora, as {hora}."


DIAS_DE_MARCADOR = 3


class RegistroEmDisco:
    """Quais avisos ja sairam — a prova de restart E de duas instancias.

    DUAS EXIGENCIAS QUE PARECEM SEPARADAS E SAO A MESMA:

      AGEN-06  reiniciar o scanner nao pode reenviar um aviso ja enviado
      AGEN-07  duas instancias rodando nao podem fazer o grupo receber em dobro

    As duas pedem um registro DURAVEL e FORA DO PROCESSO de qual aviso ja saiu.
    Resolver uma sem a outra deixa metade do bug em pe — e o usuario roda duas
    instancias lado a lado (Yazalaque e Faerlina), entao a metade que sobrasse
    apareceria no primeiro dia.

    A IMPLEMENTACAO E UM ARQUIVO VAZIO POR AVISO, criado com O_CREAT | O_EXCL.

    Essa combinacao e ATOMICA no Windows: entre duas instancias competindo pelo
    mesmo aviso no mesmo instante, exatamente uma cria o arquivo e a outra leva
    FileExistsError. Quem criou despacha; quem falhou cala. Nao precisa de lock,
    nao precisa de biblioteca, e nao tem janela de corrida entre ler e escrever
    — que e justamente o furo de um "le o JSON, checa, escreve o JSON".

    E o mesmo arquivo que resolve o restart, porque ele esta em disco.

    POR QUE NAO DERIVAR DO outbox.jsonl: ele ja registra tudo que foi enviado,
    com hora. Tentador e errado — exigiria casar o TEXTO da mensagem para saber
    o que cada linha era, e o texto e exatamente a parte que muda quando alguem
    melhora a redacao. Registro de intencao precisa de chave estruturada.
    """

    def __init__(self, pasta: Path) -> None:
        self._pasta = pasta
        self._pasta.mkdir(parents=True, exist_ok=True)
        self.podar()

    def enviados(self) -> set[str]:
        """Avisos ja registrados por QUALQUER instancia.

        Serve para o caminho comum, evitando criar arquivo a toa. NAO e a
        garantia — a garantia e o O_EXCL do `marcar`, porque entre este read e
        aquele write a outra instancia pode ter escrito.
        """
        try:
            return {caminho.name for caminho in self._pasta.iterdir()}
        except OSError:
            return set()

    def marcar(self, chave: str) -> bool:
        """True se ESTE processo deve enviar. False se alguem ja enviou.

        Aqui mora a garantia. A decisao de despachar tem que ser esta chamada,
        nunca uma checagem anterior.
        """
        alvo = self._pasta / chave
        try:
            descritor = os.open(alvo, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        except OSError:
            # Disco cheio, permissao, pasta sumiu. Preferir o aviso duplicado
            # ao aviso perdido: a party consegue ignorar uma repeticao, mas nao
            # consegue adivinhar um TvT que ninguem anunciou.
            return True
        os.close(descritor)
        return True

    def podar(self, hoje: date | None = None) -> int:
        """Apaga marcadores velhos. Devolve quantos foram apagados.

        Sem isto a pasta cresce para sempre — devagar, mas para sempre.
        """
        hoje = hoje or date.today()
        limite = hoje - timedelta(days=DIAS_DE_MARCADOR)
        apagados = 0
        try:
            nomes = list(self._pasta.iterdir())
        except OSError:
            return 0
        for caminho in nomes:
            try:
                dia = date.fromisoformat(caminho.name.split("_", 1)[0])
            except (ValueError, IndexError):
                continue  # nao e um marcador nosso; nao mexer
            if dia < limite:
                try:
                    caminho.unlink()
                    apagados += 1
                except OSError:
                    pass
        return apagados


@dataclass(frozen=True)
class JanelaDeSilencio:
    """Um periodo em que os alertas do scanner nao vao para o WhatsApp.

    `evento` e o que TERMINA POR ULTIMO, porque e ele que ainda estava
    acontecendo quando o silencio acabou — e e o nome que faz sentido na
    mensagem de encerramento.
    """

    evento: str
    inicio: datetime
    fim: datetime


def chave_da_ocorrencia(nome: str, alvo: datetime) -> str:
    """Identidade duravel de UMA ocorrencia de evento.

    Mesma forma da chave de aviso, sem o tipo: `{data}_{evento}-{HHMM}`. E o
    que permite cancelar "o Prime de hoje as 20h" sem tocar no de amanha.
    """
    apelido = re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")
    return f"{alvo.date().isoformat()}_{apelido}-{alvo.hour:02d}{alvo.minute:02d}"


def silencio_ativo(
    agora: datetime,
    eventos: list[EventoAgendado],
    cancelados: frozenset[str] | set[str] = frozenset(),
) -> JanelaDeSilencio | None:
    """A janela de silencio valendo agora, ou None.

    JANELAS SOBREPOSTAS SAO UNIAO, NAO SUBSTITUICAO. Isso nao e refinamento, e
    correcao: de segunda a quinta o Prime vai das 20:00 as 22:00 e o TvT das
    21:50 vai ate 22:05. Substituir faria o silencio acabar as 22:00 e os
    ultimos cinco minutos de TvT vazariam alerta — bem no auge do evento, que e
    quando mais gente morre.

    Funcao pura, igual ao resto da agenda: o tempo entra por parametro.
    """
    cobrindo: list[JanelaDeSilencio] = []
    hoje = agora.date()

    # Ontem entra porque uma janela de 2h iniciada as 23:00 atravessa a
    # meia-noite. Amanha nao entra: uma janela que ainda nao comecou nao
    # silencia nada.
    for deslocamento in (-1, 0):
        dia = hoje + timedelta(days=deslocamento)
        for evento in eventos:
            if evento.silenciar_minutos <= 0:
                continue
            for inicio in _ocorrencias(evento, dia):
                # Cancelado pelo usuario: esta ocorrencia deixa de silenciar,
                # e so ela. O Prime de amanha continua valendo.
                if chave_da_ocorrencia(evento.nome, inicio) in cancelados:
                    continue
                fim = inicio + timedelta(minutes=evento.silenciar_minutos)
                if inicio <= agora < fim:
                    cobrindo.append(
                        JanelaDeSilencio(evento=evento.nome, inicio=inicio, fim=fim)
                    )

    if not cobrindo:
        return None

    # A UNIAO: comeca no mais cedo, termina no mais tarde, e leva o nome de quem
    # termina por ultimo.
    ultima = max(cobrindo, key=lambda j: j.fim)
    return JanelaDeSilencio(
        evento=ultima.evento,
        inicio=min(j.inicio for j in cobrindo),
        fim=ultima.fim,
    )


def texto_de_encerramento(janela: JanelaDeSilencio) -> str:
    """A unica mensagem que sai quando o silencio acaba.

    Sem resumo do que foi engolido — decisao explicita do usuario.

    ATENCAO: "os convites estao sendo reenviados" e TEXTO. O scanner NUNCA
    envia input ao jogo; quem convida e uma pessoa. Essa frase avisa a galera
    para ficar atenta ao convite, e nada mais.
    """
    return (
        f"{janela.evento} encerrado. Os convites de party estao sendo "
        f"reenviados — fiquem atentos. Voltei a vigiar o grupo."
    )


# Ate quanto tempo ANTES de um evento faz sentido cancela-lo por antecipacao.
#
# Nao e "qualquer momento": marcar as 10h que nao vai fazer o Prime das 20h e
# quase sempre esquecimento, e o cancelamento ficaria pendurado o dia inteiro
# sem que ninguem lembrasse. Tres horas cobrem "estou vendo que hoje nao rola"
# sem virar armadilha.
HORAS_PARA_CANCELAR_ANTECIPADO = 3


def ocorrencias_cancelaveis(
    agora: datetime,
    eventos: list[EventoAgendado],
    cancelados: frozenset[str] | set[str] = frozenset(),
) -> list[tuple[str, datetime, bool]]:
    """O que da para cancelar agora: (nome, inicio, ja_esta_rolando).

    Cobre os DOIS momentos que o usuario pediu:

    - **durante**: a janela ja comecou e ele quer os alertas de volta agora;
    - **antes**: ele ja sabe que hoje nao vai, e marca para a janela nem
      comecar.

    Ordenada pelo que esta acontecendo primeiro, entao o primeiro item e
    sempre a escolha mais provavel — e um cancelamento sem argumento pode
    simplesmente pegar ele.
    """
    achados: list[tuple[str, datetime, bool]] = []
    limite = agora + timedelta(hours=HORAS_PARA_CANCELAR_ANTECIPADO)
    hoje = agora.date()

    for deslocamento in (-1, 0, 1):
        dia = hoje + timedelta(days=deslocamento)
        for evento in eventos:
            if evento.silenciar_minutos <= 0:
                continue
            for inicio in _ocorrencias(evento, dia):
                if chave_da_ocorrencia(evento.nome, inicio) in cancelados:
                    continue
                fim = inicio + timedelta(minutes=evento.silenciar_minutos)
                if inicio <= agora < fim:
                    achados.append((evento.nome, inicio, True))
                elif agora < inicio <= limite:
                    achados.append((evento.nome, inicio, False))

    achados.sort(key=lambda a: (not a[2], a[1]))
    return achados
