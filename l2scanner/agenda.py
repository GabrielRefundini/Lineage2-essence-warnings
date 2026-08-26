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

    # A pergunta "quem vai?", bem antes do evento.
    #
    # O VALOR entra na `Aviso.chave` e vira nome de arquivo em `.agenda/`:
    # foi escolhido uma vez e nao muda. Troca-lo faria todo marcador ja
    # gravado deixar de casar, e a party receberia a chamada de novo.
    CHAMADA = "chamada"


@dataclass(frozen=True)
class EventoAgendado:
    """Um evento recorrente do jogo, como o usuario o descreveu."""

    nome: str
    horarios: tuple[tuple[int, int], ...]  # (hora, minuto)
    dias: frozenset[int] = TODOS_OS_DIAS
    avisar_minutos_antes: int = 10

    # Mandar tambem o aviso NO horario, alem do de antecedencia.
    #
    # Existe porque nem todo evento merece dois avisos. Um Solo Boss de duas em
    # duas horas sao 12 ocorrencias por dia; com dois avisos cada, viram 24
    # mensagens no grupo — mais do que TvT e Prime somados, tres vezes. Para
    # esses, o lembrete de antecedencia basta: quem ia, ja se preparou.
    avisar_no_horario: bool = True

    # Quanto tempo ANTES do evento perguntar no grupo quem vai.
    #
    # `0` desliga, o mesmo idioma de `silenciar_minutos` abaixo: um evento
    # so ganha chamada se o config.toml pedir, entao um evento novo nasce
    # calado sem ninguem precisar lembrar de exclui-lo.
    #
    # O 110 do Solo Boss nao e um numero solto. Com o boss de duas em duas
    # horas, 1h50 antes cai dez minutos DEPOIS do boss anterior: o unico
    # instante do ciclo em que a party ainda esta reunida e ainda esta
    # olhando o WhatsApp. Perguntar mais cedo pega gente dispersa;
    # perguntar mais tarde ja nao da tempo de ninguem se organizar.
    chamar_minutos_antes: int = 0

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


def ocorrencias_do_dia(evento: EventoAgendado, dia: date) -> list[datetime]:
    """Instantes em que este evento acontece nesta data.

    Vazio quando a data nao e um dia configurado. A checagem de dia mora AQUI,
    olhando a data do EVENTO — nunca a do aviso.

    PUBLICA porque o encaixe do `.pegou` precisa enumerar ocorrencias que JA
    PASSARAM, e `proxima_ocorrencia` so olha para frente. Uma segunda
    enumeracao dentro do `loot.py` divergiria desta no primeiro ajuste da
    regra de dias da semana.
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
            for alvo in ocorrencias_do_dia(evento, dia):
                candidatos = [
                    (
                        TipoDeAviso.ANTES,
                        alvo - timedelta(minutes=evento.avisar_minutos_antes),
                    ),
                    (TipoDeAviso.AGORA, alvo),
                    (
                        TipoDeAviso.CHAMADA,
                        alvo - timedelta(minutes=evento.chamar_minutos_antes),
                    ),
                ]
                for tipo, devido_em in candidatos:
                    if tipo is TipoDeAviso.AGORA and not evento.avisar_no_horario:
                        continue
                    if evento.chamar_minutos_antes <= 0 and tipo is TipoDeAviso.CHAMADA:
                        # Chamada desligada: e o default, e e o que mantem
                        # todo evento que nao pediu exatamente como estava.
                        continue
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
            for alvo in ocorrencias_do_dia(evento, dia):
                if alvo <= agora:
                    continue
                if melhor is None or alvo < melhor[1]:
                    melhor = (evento.nome, alvo)
    return melhor


def texto_do_aviso(aviso: Aviso, loot: str | None = None) -> str:
    """A mensagem que vai para o WhatsApp.

    O aviso de ANTES serve para parar o farm e se deslocar; o de AGORA serve
    para dizer que comecou. Textos diferentes porque servem a acoes diferentes
    — repetir a mesma frase duas vezes treinaria a party a ignorar as duas.

    A CHAMADA serve a uma terceira acao, anterior as duas: decidir SE vai.
    Ela vence cedo o bastante para a resposta ainda mudar alguma coisa, e por
    isso tambem nao pode repetir o texto das outras duas.

    `loot` e o nick de quem pega o loot desta ocorrencia, e so entra no aviso
    de ANTECEDENCIA. A agenda nao conhece designacao nenhuma: quem decide SE
    ha loot e o chamador, a agenda so formata — mesma linha do console nao
    ganhar relogio.
    """
    hora = f"{aviso.alvo.hour:02d}:{aviso.alvo.minute:02d}"
    if aviso.tipo is TipoDeAviso.ANTES:
        faltam = int((aviso.alvo - aviso.devido_em).total_seconds() // 60)
        texto = (
            f"{aviso.evento} comeca em {faltam} minutos, as {hora}. "
            f"Hora de voltar para a cidade e se preparar."
        )
        if loot:
            texto += f" Loot: {loot}."
        return texto
    if aviso.tipo is TipoDeAviso.CHAMADA:
        # "no PRIVADO" nao e gentileza: a ponte Baileys desta conta vem com
        # ingestao de grupo desligada (medido 2026-08-24 — os 11 grupos nao
        # entregam entrada, so as conversas 1-a-1). Uma chamada que nao diz
        # onde responder colhe resposta num lugar que o bot nunca le.
        return (
            f"{aviso.evento} as {hora}. Quem vai? "
            f"Mande .join no PRIVADO do bot para entrar na lista, "
            f"ou .leave para sair. Aqui no grupo o bot nao le comando."
        )
    return f"{aviso.evento} comecou agora, as {hora}."


DIAS_DE_MARCADOR = 3

# Prefixo dos marcadores de CANCELAMENTO, para nao se confundirem com os de
# "ja avisei". Namespaces diferentes no mesmo diretorio: a poda, a atomicidade
# e o compartilhamento entre instancias valem para os dois de graca.
PREFIXO_CANCELADO = "cancelado_"

# Prefixo dos marcadores de PRESENCA — um arquivo vazio por pessoa por
# ocorrencia. O nome completo e `presenca_<chave-da-ocorrencia>_<slug>`.
PREFIXO_PRESENCA = "presenca_"

# Prefixo do marcador de FECHAMENTO da lista: `fechado_<chave-da-ocorrencia>`.
# Um por ocorrencia, escrito quando o boss nasce e a lista vira historico.
PREFIXO_FECHADO = "fechado_"

# Todo namespace que a poda sabe desmontar.
#
# CONSERTA UM DEFEITO REAL: ate esta fase a poda retirava UM prefixo
# (`cancelado_`) antes de ler a data. Todo marcador de qualquer outro namespace
# caia no `except ValueError` de `date.fromisoformat` e ficava em disco PARA
# SEMPRE — o oposto exato do que a lista de presenca quer, porque ela existe
# para morrer quando o boss passa. Um prefixo novo tem que entrar AQUI, ou
# nasce imortal em silencio.
#
# FATO OBSERVADO, deliberadamente NAO consertado aqui: os marcadores
# `comando_<id>` (o `chave_da_mensagem` da leitura de comandos) tambem nunca
# sao podados — mas por outro motivo, o de nao existir data nenhuma no nome
# deles. Resolve-los pede um segundo criterio de idade (mtime, ou id
# monotonico), que e outro desenho e outra fase.
_PREFIXOS_CONHECIDOS = (PREFIXO_CANCELADO, PREFIXO_PRESENCA, PREFIXO_FECHADO)


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

    E `simulando`, QUE E O AVESSO DE TUDO ISSO: um processo em `--dry-run` nao
    vai despachar nada, entao ele nao pode entrar na disputa pelo marcador de
    quem VAI. O registro e que sabe que esta simulando — nunca cada chamador.
    Ver `marcar`, que explica o incidente de campo que obrigou isto.
    """

    def __init__(self, pasta: Path, simulando: bool = False) -> None:
        self._pasta = pasta
        self._simulando = simulando
        # Em simulacao nao cria a pasta e nao poda. As duas coisas mexem no
        # disco COMPARTILHADO com o scanner de verdade — e `podar` chega a
        # APAGAR marcador dele —, o que seria o mesmo efeito colateral que
        # `marcar` acabou de fechar, entrando pela porta dos fundos. Nada em
        # modo simulacao precisa da pasta: `enviados()` ja devolve vazio
        # quando ela nao existe.
        if not simulando:
            self._pasta.mkdir(parents=True, exist_ok=True)
        # O TETO DO "PREFERIR O DUPLICADO AO PERDIDO", em memoria e so para o
        # fechamento de lista. Ver `fechar`, que explica por que ele existe.
        self._fechamentos_desta_execucao: set[str] = set()
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

        EM MODO SIMULACAO DEVOLVE True SEM ENCOSTAR NO DISCO. Isso nao e "nao
        faz nada": e FINGIR QUE GANHOU, para o aviso aparecer no console — que
        e o produto inteiro do `--dry-run` — sem tirar a vez de quem vai mesmo
        falar no grupo.

        POR QUE, MEDIDO EM CAMPO. 2026-08-26, 19:30: uma simulacao
        (`--so-agenda --dry-run`) rodava ao lado do scanner de verdade do
        usuario e as duas disputaram `2026-08-26_tvt-1930_agora`. O arquivo foi
        criado as 19:30:00.629 e o `outbox.jsonl` registra o envio real no
        mesmo instante — a instancia REAL ganhou por milissegundos e o aviso
        saiu. Foi sorte: tivesse a simulacao ganhado, ela receberia True, a
        real receberia False, e o lembrete de TvT NUNCA teria sido enviado —
        sem erro, sem log, sem nada. O modo que existe justamente para nao ter
        efeito colateral era o unico capaz de APAGAR um aviso.

        A DECISAO MORA AQUI, E NAO NOS CHAMADORES. Sao quatro `marcar` hoje
        (dois no laco principal, um no `--so-agenda`, um no fechamento de
        lista); um `if dry_run` em cada resolveria os quatro de hoje e
        garantiria que o quinto nascesse errado — a mesma forma do defeito de
        poda que `_PREFIXOS_CONHECIDOS` acabou de consertar. Com a decisao no
        registro, `cancelar` e `fechar` herdam sem saber que isto existe.

        `entrar` e `sair` NAO passam por aqui e continuam escrevendo de
        proposito: so sao alcancadas por comando, e em `--dry-run`
        `montar_leitor_de_comandos` devolve `None` na primeira linha. Nao ha
        caminho que as chame simulando, e inventar semantica para um caminho
        morto seria pior do que a lacuna.
        """
        if self._simulando:
            return True
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

    def cancelar(self, chave_da_ocorrencia: str) -> bool:
        """Marca uma ocorrencia como cancelada. True se ESTE processo marcou.

        Mesma atomicidade dos avisos: com as duas instancias do usuario
        rodando, exatamente uma vence — e e ela que anuncia no grupo. A outra
        le o marcador no proximo tick e para de silenciar do mesmo jeito.
        """
        return self.marcar(PREFIXO_CANCELADO + chave_da_ocorrencia)

    def cancelados(self) -> set[str]:
        """Ocorrencias canceladas, sem o prefixo."""
        return {
            nome[len(PREFIXO_CANCELADO) :]
            for nome in self.enviados()
            if nome.startswith(PREFIXO_CANCELADO)
        }

    # -- a lista de presenca ------------------------------------------------

    def entrar(self, chave_da_ocorrencia: str, slug: str) -> str:
        """Poe alguem na lista. Tri-estado: criado | ja_existia | falhou.

        O TRI-ESTADO E O ANALOGO DO `RegistroDeLoot._criar`, NAO DO `marcar`
        LOGO ACIMA — e a diferenca e de produto, nao de estilo.

        `ja_existia` e informacao que o usuario final ENXERGA: e a unica coisa
        que distingue "acabou de entrar" (confirma no grupo) de "ja estava na
        lista" (responde so no privado, e cala no grupo). Sem ela, um `.join`
        repetido ou repetiria a confirmacao para a party inteira — o volume de
        mensagem que fez o usuario desligar `avisar_no_horario` no Solo Boss —
        ou calaria nos dois lugares, e quem digitou nao saberia se chegou.

        `"falhou"` nao pode virar sucesso. O `marcar` colapsa OSError em True
        porque, para um ANUNCIO, o duplicado e melhor que o perdido: a party
        ignora uma repeticao, mas nao adivinha um TvT que ninguem falou. Aqui a
        regra e a inversa, e pelo mesmo raciocinio aplicado a outro fato:
        anunciar no grupo uma entrada que o disco nao guardou faria a lista
        fechar SEM essa pessoa, e ela chegaria no boss confiando num registro
        que nao a tem. Melhor pedir para repetir o comando.

        O `slug` ja chega reduzido a `[a-z0-9-]` por `loot.apelido` — e a
        segunda das duas barreiras que impedem um nick de virar travessia de
        caminho (a primeira e `NICK_VALIDO`, na leitura do `[[membro]]`).
        """
        nome = f"{PREFIXO_PRESENCA}{chave_da_ocorrencia}_{slug}"
        try:
            descritor = os.open(
                self._pasta / nome, os.O_CREAT | os.O_EXCL | os.O_WRONLY
            )
        except FileExistsError:
            return "ja_existia"
        except OSError:
            return "falhou"
        os.close(descritor)
        return "criado"

    def sair(self, chave_da_ocorrencia: str, slug: str) -> bool:
        """Tira alguem da lista. True se havia algo para tirar.

        Idempotente e sem levantar, com a mesma exposicao deliberada de
        `RegistroDeLoot.cancelar`: um disco travado no meio do farm nao pode
        virar excecao no laco. Um `.leave` que nao conseguiu apagar responde
        "voce nao estava na lista", que e menos ruim do que derrubar o scanner
        — e o proximo tick tenta de novo se o disco voltar.
        """
        alvo = self._pasta / f"{PREFIXO_PRESENCA}{chave_da_ocorrencia}_{slug}"
        try:
            existia = alvo.exists()
            alvo.unlink(missing_ok=True)
        except OSError:
            return False
        return existia

    def presentes(self, chave_da_ocorrencia: str) -> frozenset[str]:
        """Os slugs de quem esta na lista DESTA ocorrencia.

        O `rpartition` no ultimo `_` e a mesma leitura defensiva de
        `loot.registros()`: a pasta e compartilhada e duravel, entao um nome
        malformado que caia nela e PULADO, nunca levantado.

        A comparacao e pela chave INTEIRA, e nao por `startswith`. O boss das
        20:00 e o das 22:00 geram nomes que compartilham quase todo o prefixo
        (`presenca_2026-08-24_solo-boss-`); um filtro por prefixo juntaria as
        duas listas e o grupo veria, as 22:00, quem tinha entrado para as 20:00.
        """
        achados: set[str] = set()
        for nome in self.enviados():
            if not nome.startswith(PREFIXO_PRESENCA):
                continue
            chave, _, slug = nome[len(PREFIXO_PRESENCA) :].rpartition("_")
            if not slug or chave != chave_da_ocorrencia:
                continue
            achados.add(slug)
        return frozenset(achados)

    def fechar(self, chave_da_ocorrencia: str) -> bool:
        """Fecha a lista desta ocorrencia. True se ESTE processo fechou.

        Aqui o `marcar` E o analogo certo, ao contrario do `entrar` acima: o
        fechamento e um ANUNCIO ("a lista do boss das 20:00 e esta"), e a regra
        dos anuncios deste projeto e preferir o duplicado ao perdido. Com as
        duas instancias vivas, exatamente uma fala no grupo.

        MAS "DUPLICADO" TEM QUE TER TETO, E ESTE E O UNICO LUGAR DA PASTA ONDE
        ELE NAO TINHA. `marcar` devolve True em `OSError` — disco cheio,
        permissao, pasta em rede — de proposito. Com a `.agenda/` legivel e NAO
        gravavel, `presentes()` continua devolvendo a lista, `marcar` continua
        levantando e devolvendo True, e `fechar_ocorrencias` produz um
        `Fechamento` A CADA TICK durante os 5 minutos de tolerancia. A 1 Hz sao
        ~300 mensagens identicas no grupo por ocorrencia — o oposto exato da
        disciplina de volume que fez o usuario desligar `avisar_no_horario`.

        O teto e um `set` em memoria, e nao um marcador novo em disco: o disco
        e justamente o recurso que falhou. Ele NAO enfraquece a garantia entre
        as duas instancias (essa continua sendo o `O_CREAT|O_EXCL`) — ele so
        impede que UM processo anuncie a MESMA ocorrencia duas vezes. Um
        restart reanuncia, e isso e o certo: o marcador em disco nao existe, e
        preferir o duplicado ao perdido continua valendo uma vez por execucao.
        """
        chave = PREFIXO_FECHADO + chave_da_ocorrencia
        if chave in self._fechamentos_desta_execucao:
            return False
        if not self.marcar(chave):
            return False
        self._fechamentos_desta_execucao.add(chave)
        return True

    def podar(self, hoje: date | None = None) -> int:
        """Apaga marcadores velhos. Devolve quantos foram apagados.

        Sem isto a pasta cresce para sempre — devagar, mas para sempre.

        A DATA E LIDA DO INICIO DO NOME, depois de retirar QUALQUER prefixo
        conhecido — ver `_PREFIXOS_CONHECIDOS` e o defeito que a tupla
        conserta. Todo namespace desta pasta comeca por `YYYY-MM-DD` logo apos
        o prefixo, porque tanto `Aviso.chave` quanto `chave_da_ocorrencia`
        comecam pela data; e essa propriedade compartilhada que deixa uma unica
        regra de poda servir os quatro.

        EM MODO SIMULACAO NAO PODA NADA. Esta e a unica funcao da classe que
        APAGA arquivo, e ela roda no construtor: sem esta guarda, o simples ato
        de subir um `--dry-run` ao lado do scanner de verdade apagaria marcador
        dele. O `return 0` fica AQUI e nao no `__init__` pela mesma razao que a
        guarda de `marcar` nao ficou nos chamadores.
        """
        if self._simulando:
            return 0
        hoje = hoje or date.today()
        limite = hoje - timedelta(days=DIAS_DE_MARCADOR)
        apagados = 0
        try:
            nomes = list(self._pasta.iterdir())
        except OSError:
            return 0
        for caminho in nomes:
            nome = caminho.name
            for prefixo in _PREFIXOS_CONHECIDOS:
                if nome.startswith(prefixo):
                    nome = nome[len(prefixo) :]
                    break
            try:
                dia = date.fromisoformat(nome.split("_", 1)[0])
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
            for inicio in ocorrencias_do_dia(evento, dia):
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
            for inicio in ocorrencias_do_dia(evento, dia):
                if chave_da_ocorrencia(evento.nome, inicio) in cancelados:
                    continue
                fim = inicio + timedelta(minutes=evento.silenciar_minutos)
                if inicio <= agora < fim:
                    achados.append((evento.nome, inicio, True))
                elif agora < inicio <= limite:
                    achados.append((evento.nome, inicio, False))

    achados.sort(key=lambda a: (not a[2], a[1]))
    return achados


def texto_de_cancelamento(nome: str, inicio: datetime, rolando: bool) -> str:
    """A mensagem que avisa o grupo que o silencio foi cancelado.

    Vai para o grupo, e nao so para o console, porque o silencio e uma promessa
    COLETIVA: a party inteira parou de receber alerta por causa dele. Cancelar
    em silencio deixaria todo mundo achando que ainda esta calado.
    """
    hora = inicio.strftime("%H:%M")
    if rolando:
        return (
            f"Silencio do {nome} das {hora} cancelado. "
            f"Voltei a avisar mortes e saidas da party."
        )
    return (
        f"O {nome} das {hora} nao vai silenciar hoje. "
        f"Vou continuar avisando normalmente durante ele."
    )
