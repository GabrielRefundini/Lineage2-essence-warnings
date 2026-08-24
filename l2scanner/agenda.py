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

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum

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


class RegistroEmMemoria:
    """Guarda quais avisos ja sairam, so enquanto o processo vive.

    Suficiente para uma sessao. NAO resolve reiniciar o scanner nem duas
    instancias rodando lado a lado — as duas coisas que fariam o grupo receber
    o mesmo aviso duas vezes. Quem resolve isso e o registro duravel da
    Tarefa 3, que implementa esta mesma interface.

    A interface existe desde ja justamente para essa troca nao mexer no laco.
    """

    def __init__(self) -> None:
        self._chaves: set[str] = set()

    def enviados(self) -> set[str]:
        return self._chaves

    def marcar(self, chave: str) -> bool:
        """True se ESTE processo deve enviar. False se ja foi enviado."""
        if chave in self._chaves:
            return False
        self._chaves.add(chave)
        return True
