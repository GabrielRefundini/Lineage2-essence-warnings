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


def apelido_do_evento(nome: str) -> str:
    """O nome do evento reduzido ao que pode virar nome de arquivo.

    UM SO APELIDO PARA TODOS OS USOS, e isto nao e arrumacao. A mesma linha
    estava escrita duas vezes — em `Aviso.chave` e em `chave_da_ocorrencia` — e
    agora tem um terceiro consumidor, o marcador de evento calado, um quarto,
    o `respawn.py` da janela de boss (`chave_do_nascimento` e
    `AvisoDeJanela.chave`), e um quinto, o marcador de anuncio de nascimento
    (`respawn.chave_do_anuncio`, Fase 3 do `tiat`). Cinco copias da mesma
    expressao divergem no primeiro ajuste, e a divergencia aqui e invisivel: o
    gate procuraria
    `soloboss` enquanto a agenda escreve `solo-boss`, ninguem levantaria
    excecao nenhuma, e o boss simplesmente continuaria falando depois de o
    usuario o ter desligado.

    O VALOR E DURAVEL. Ele ja e nome de arquivo em `.agenda/` desde a Fase 6 —
    muda-lo faria todo marcador gravado deixar de casar, e a party receberia
    de novo tudo que ja tinha recebido. Desde a Fase 2 do workstream `tiat` ele
    tambem e a identidade da ANCORA de respawn, e ali o custo de mudar e outro:
    a contagem de seis horas reinicia do nada, em silencio.

    E POR ISSO QUE A REDUCAO E POR LISTA DE PERMISSAO, e nao por lista de
    recusa. So `a-z` e `0-9` sobrevivem; todo o resto vira hifen. Um `nome` de
    `[[boss]]` escrito a mao no `config.toml` nao consegue produzir separador
    de diretorio, ponto, nem sequencia de subida de nivel dentro de `.agenda/`
    (T-02-04). Isso era verdade por consequencia enquanto o valor so nomeava
    eventos; virou propriedade a defender quando o `nome` do boss passou a ser
    nome de arquivo.
    """
    return re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")


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
        apelido = apelido_do_evento(self.evento)
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
    eventos_calados: frozenset[str] | set[str] = frozenset(),
) -> list[Aviso]:
    """Quais avisos venceram agora e ainda nao sairam.

    Funcao pura: mesmo instante, mesma agenda, mesmo conjunto de enviados ->
    mesma resposta, sempre. Sem relogio, sem disco, sem rede.

    `eventos_calados` sao APELIDOS de evento (ver `apelido_do_evento`) que o
    usuario desligou por comando, e o filtro deles mora AQUI por duas razoes:

    1. **AQUI E O FUNIL DOS TRES TIPOS.** `ANTES`, `AGORA` e `CHAMADA` nascem
       na mesma lista de candidatos tres linhas abaixo, entao um evento calado
       perde os tres de uma vez e NAO EXISTE SINTAXE PARA CALAR METADE. A
       decisao e do usuario e ela e de produto: a chamada de 1h50 sem o
       lembrete de 10 minutos convida a party para um boss que ninguem lembra
       de ir, e o lembrete sem a chamada avisa uma party que nunca foi
       consultada. Meia-mudez e pior que os dois extremos. Um `TipoDeAviso`
       futuro nasce calado junto, sem ninguem precisar lembrar disto.

    2. **NAO E A AGENDA QUE ENCOLHE.** Tirar o evento da lista de eventos
       calaria os avisos e junto com eles `proxima_ocorrencia` (o console
       deixaria de saber que o boss existe), `ocorrencias_do_dia` (o encaixe do
       `.pegou`) e a lista de presenca. O usuario pediu para calar avisos, nao
       para o boss deixar de existir.

    Default VAZIO: toda chamada que nao conhece este parametro se comporta byte
    a byte como antes.
    """
    devidos: list[Aviso] = []
    tolerancia = timedelta(minutes=tolerancia_minutos)
    hoje = agora.date()

    # Ontem e amanha entram porque um aviso perto da meia-noite pertence a um
    # evento de outro dia. Varrer so "hoje" perderia toda virada de dia.
    for deslocamento in (-1, 0, 1):
        dia = hoje + timedelta(days=deslocamento)
        for evento in eventos:
            if apelido_do_evento(evento.nome) in eventos_calados:
                continue
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
            f"Mande /entrar no PRIVADO do bot para entrar na lista, "
            f"ou /sair para sair. Aqui no grupo o bot nao le comando."
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

# Prefixo do marcador de EVENTO CALADO: `evento_calado_<apelido-do-evento>`.
# Um por evento, e o unico namespace desta pasta SEM DATA no nome.
#
# A AUSENCIA DA DATA E A FUNCIONALIDADE, e por isso este prefixo NAO entra em
# `_PREFIXOS_CONHECIDOS` logo abaixo. Todos os outros marcadores sao fatos
# datados que devem morrer ("avisei o boss das 20:00 de hoje"); este e uma
# DECISAO do usuario, e ele decidiu explicitamente que ela nao expira — nem por
# reinicio, nem por tempo. Um marcador datado aqui religaria o Solo Boss
# sozinho depois de `DIAS_DE_MARCADOR`, sem ninguem mandar e sem nada dizer.
#
# A poda ja ignora o que nao sabe datar: sem prefixo conhecido para retirar,
# `date.fromisoformat("evento")` levanta `ValueError` e o arquivo e pulado. A
# imortalidade sai de graca, mas ela e DELIBERADA — ver o teste
# `test_a_poda_nao_expira_o_desligamento`.
PREFIXO_EVENTO_CALADO = "evento_calado_"

# Prefixo da ANCORA de nascimento de boss — o instante em que um boss nasceu,
# gravado como arquivo VAZIO para a contagem de respawn nao morar em memoria.
# O nome completo e `nascimento_<YYYY-MM-DD>_<boss-slug>-<HHMM>_<origem>`, e a
# ORIGEM VAI NO NOME (D-18): a mensagem que sai seis horas depois precisa citar
# QUAL sinal ancorou, e guardar isso no CONTEUDO quebraria a propriedade que
# sustenta a pasta inteira — um "cria e depois escreve" abriria uma janela em
# que a outra instancia le um arquivo ainda vazio e nao sabe a origem.
#
# ENTRA EM `_PREFIXOS_CONHECIDOS`, e a escolha do balde tem duas metades.
#
# A primeira: a ancora e EFEMERA POR CONSTRUCAO. A vida util dela acaba no
# proximo nascimento e, no maximo, em `respawn_horas_max` mais a tolerancia —
# oito horas e cinco minutos, contra os 3 dias de `DIAS_DE_MARCADOR`. Nenhuma
# ancora legitima chega perto do limite da poda.
#
# A segunda, e a que importa: UMA ANCORA VELHA NAO E NEUTRA, E PERIGOSA. Ela
# nao fica so ocupando disco como um marcador de aviso vencido — ela continua
# PRODUZINDO janelas, e as janelas erradas tem exatamente a mesma cara das
# certas. O modo de falha e uma previsao confiante sobre um nascimento que
# nunca existiu, entregue no grupo, e e ela que a poda de 3 dias limita
# (T-02-01, T-02-03).
#
# `_PREFIXOS_SEM_DATA` foi considerado e RECUSADO. Aquele balde existe para a
# imortalidade DELIBERADA do evento calado, que e uma decisao do usuario e nao
# expira. Uma ancora e o oposto disso: e um fato datado que deve morrer, e o
# unico dos dois baldes em que "nao expira" seria esquecimento e nao decisao.
PREFIXO_NASCIMENTO = "nascimento_"

# Prefixo do marcador de ANUNCIO de nascimento — a prova duravel de que a
# mensagem "o boss nasceu" JA SAIU no grupo, para ela nao sair de novo.
#
# A FORMA COMPLETA E `anuncio_<YYYY-MM-DD>_<boss-slug>-<HHMM>`, com a data e a
# hora do INICIO DO EPISODIO e nao do instante da deteccao (D-28). Um episodio
# e um nascimento e TODAS as deteccoes dele; a semantica inteira mora em
# `respawn.py` (`inicio_do_episodio` e `chave_do_anuncio`), como a semantica da
# ancora ja mora la. Este modulo continua sem importar nada do pacote.
#
# ENTRA EM `_PREFIXOS_CONHECIDOS`, e o balde e a decisao de seguranca deste
# prefixo. Ele TEM data, e precisa ter: um marcador de silencio imortal e um
# boss que nunca mais e anunciado. E a mesma familia de defeito descrita acima
# em `PREFIXO_NASCIMENTO`, so que na direcao oposta e pior — a ancora velha
# MENTE, e alguem acaba percebendo a previsao errada; o anuncio velho EMUDECE,
# e o unico sintoma e um scanner que roda, loga, preve janela e nunca mais
# avisa um nascimento. Sem erro, sem log, sem nada (T-03-03).
#
# `_PREFIXOS_SEM_DATA` FOI CONSIDERADO E RECUSADO. Aquele balde e da
# imortalidade DELIBERADA do evento calado, que e uma decisao do usuario. Este
# silencio nao e decisao de ninguem: e a consequencia mecanica de uma mensagem
# ja enviada, e tem que expirar junto com a relevancia dela.
PREFIXO_ANUNCIO = "anuncio_"

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
_PREFIXOS_CONHECIDOS = (
    PREFIXO_CANCELADO,
    PREFIXO_PRESENCA,
    PREFIXO_FECHADO,
    PREFIXO_NASCIMENTO,
    PREFIXO_ANUNCIO,
)

# O SEGUNDO destino possivel de um prefixo: os que NAO tem data e nao expiram
# NUNCA — por decisao, e nao por esquecimento.
#
# Esta tupla existe para preservar a forca do tripwire de
# `TestPodaAlcancaTodosOsPrefixos`, que deriva a prova por introspecao dos
# `PREFIXO_*` do modulo. Sem ela, a unica forma de o marcador de evento calado
# passar naquele teste seria entrar em `_PREFIXOS_CONHECIDOS` e ganhar uma
# data — e ai o Solo Boss religaria sozinho tres dias depois de o usuario o ter
# desligado, sem ninguem mandar e sem nada dizer.
#
# Com os DOIS baldes declarados, todo prefixo novo continua obrigado a
# escolher um deles por escrito, e continua quebrando o teste enquanto nao
# escolher. O que mudou nao foi a exigencia — foi so passarem a existir duas
# respostas certas em vez de uma.
_PREFIXOS_SEM_DATA = (PREFIXO_EVENTO_CALADO,)


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

    # -- ancoras de nascimento de boss --------------------------------------

    def registrar_nascimento(self, chave: str) -> bool:
        """Grava a ANCORA de um nascimento. True se ESTE processo gravou.

        A `chave` e OPACA: este metodo nao conhece boss nenhum, nao sabe o que
        e uma origem e nunca parseia o que recebe. A semantica inteira mora em
        `respawn.py`, exatamente como a semantica de presenca mora em
        `presenca.py` e nao em `presentes`. E o que mantem `agenda.py` sem
        importar nada do pacote.

        HERDA DE `marcar` AS DUAS PROPRIEDADES QUE A FASE PRECISA, e nao
        reimplementa nenhuma:

        - **Em `--dry-run` devolve True sem encostar no disco.** Uma simulacao
          nao pode gravar ancora na pasta COMPARTILHADA: o scanner real
          passaria a contar seis horas a partir de um nascimento que a
          simulacao inventou, e a previsao errada sairia no grupo horas depois
          com a mesma cara de uma certa.
        - **Entre as duas instancias do usuario, exatamente uma cria o
          arquivo.** Mesmo `O_CREAT|O_EXCL` dos avisos — nenhuma corrida nova
          foi introduzida por este namespace.
        """
        return self.marcar(PREFIXO_NASCIMENTO + chave)

    def nascimentos(self) -> set[str]:
        """As ancoras gravadas, sem o prefixo.

        O filtro por prefixo e o que mantem os namespaces separados dentro da
        MESMA pasta: sem ele, um marcador de aviso de janela (que nao tem
        prefixo nenhum) entraria nesta lista e seria lido como se fosse um
        nascimento.
        """
        return {
            nome[len(PREFIXO_NASCIMENTO) :]
            for nome in self.enviados()
            if nome.startswith(PREFIXO_NASCIMENTO)
        }

    # -- o anuncio de nascimento ja feito ------------------------------------

    def registrar_anuncio(self, chave: str) -> bool:
        """Grava que o nascimento JA FOI ANUNCIADO. True se ESTE processo deve
        falar.

        A `chave` e OPACA: este metodo nao conhece boss nenhum, nao sabe o que
        e um episodio e nunca parseia o que recebe. A semantica inteira mora em
        `respawn.chave_do_anuncio`, exatamente como a da ancora.

        POR QUE ELE EXISTE, MEDIDO EM CAMPO. 2026-08-30, 21:59 as 22:02: o
        usuario recebeu SEIS mensagens para um unico Tiat South. Tres do chat
        as 21:59 e tres do alvo entre 22:01 e 22:02, com as duas instancias
        dele rodando (confirmado por `Win32_Process`). O aviso de nascimento
        era o UNICO alerta do projeto que chamava o despacho direto, sem passar
        por `marcar` — a agenda passa, a janela de respawn passa, ele nao.

        HERDA DE `marcar` AS DUAS PROPRIEDADES, e nao reimplementa nenhuma:

        - **Em `--dry-run` devolve True sem encostar no disco.** Uma simulacao
          repete a mensagem no console a cada volta, e isso e o produto inteiro
          do modo — sem queimar o marcador de quem vai mesmo falar no grupo.
        - **Entre as duas instancias do usuario, exatamente uma cria o
          arquivo.** Mesmo `O_CREAT|O_EXCL`; nenhuma corrida nova.

        NAO EXISTE UM `anuncios()`, E A AUSENCIA E DELIBERADA. `cancelar` tem
        `cancelados` e `registrar_nascimento` tem `nascimentos`, entao a
        simetria vai fazer alguem querer completar o par. Nao complete. Nao ha
        caso de uso legitimo para enumerar anuncios ja feitos, e o unico uso
        imaginavel — "conferir antes de falar" — e exatamente o read-then-write
        que a docstring de `marcar` proibe por escrito. O sintoma dele nao e a
        mensagem repetida que este metodo veio consertar: e a mensagem
        PERDIDA, porque as duas instancias se veriam livres para calar achando
        que a outra falou, e cada uma ficaria verde sozinha. A decisao de
        despachar tem que SER esta chamada.
        """
        return self.marcar(PREFIXO_ANUNCIO + chave)

    # -- eventos calados por comando ----------------------------------------

    def calar_evento(self, nome: str) -> str:
        """Desliga TODOS os avisos de um evento. Tri-estado, igual ao `entrar`.

        POR QUE O MARCADOR E NAO UM JSON. O outro idioma de persistencia deste
        projeto e o `os.replace` do `loot.py`, e ele existe porque loot carrega
        DADO ESTRUTURADO (nick, alvo, carimbo). Aqui nao ha dado nenhum — ha um
        estado de dois valores por evento, e o nome do arquivo ja o expressa
        inteiro. Tres coisas caem de graca ao ficar no marcador:

        - **Nao existe read-check-write para dar errado.** O usuario roda duas
          instancias (Yazalaque e Faerlina) sobre a MESMA pasta. Desligar e uma
          criacao atomica e religar e um `unlink` atomico: em qualquer
          intercalacao o disco termina num dos dois estados validos. Um mapa
          JSON de eventos calados teria que ser lido, alterado e reescrito, e a
          instancia que escrevesse por ultimo apagaria a decisao da outra.
        - **A direcao da falha de leitura ja esta certa.** `enviados()` devolve
          vazio em `OSError`, logo disco ilegivel = nenhum evento calado = o
          aviso SAI. E a lei escrita no `marcar`: preferir o duplicado ao
          perdido, porque a party ignora uma repeticao e nao adivinha um boss
          que ninguem anunciou.
        - **A lista de presenca ja prova o padrao.** `entrar`/`sair` sao
          criar/apagar arquivo neste mesmo diretorio desde a Fase 10.

        E POR QUE TRI-ESTADO, e nao o `bool` do `marcar`. `marcar` colapsa
        `OSError` em True porque, para um ANUNCIO, o duplicado e melhor que o
        perdido. Aqui a regra e a inversa, pelo mesmo raciocinio aplicado a
        outro fato — e o argumento e literalmente o do `entrar`: responder
        "desativei" sobre uma escrita que o disco nao guardou faria o usuario
        parar de esperar os avisos que vao continuar chegando, e no dia em que
        ele quisesse religar nao haveria nada para religar. Melhor pedir para
        repetir o comando.
        """
        alvo = self._pasta / (PREFIXO_EVENTO_CALADO + apelido_do_evento(nome))
        try:
            descritor = os.open(alvo, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return "ja_estava"
        except OSError:
            return "falhou"
        os.close(descritor)
        return "calado"

    def voltar_a_avisar(self, nome: str) -> str:
        """Religa os avisos de um evento. O mesmo tri-estado, e ele e simetrico.

        `sair` (a saida da lista de presenca) devolve `bool` e trata `OSError`
        como "nao estava la". AQUI ISSO SERIA O PIOR DESFECHO POSSIVEL: o
        marcador continuaria em disco, o boss continuaria calado, e a unica
        pessoa capaz de notar teria acabado de ler "voltei a avisar". Um boss
        perdido em silencio e exatamente o que esta funcionalidade nao pode
        produzir, entao a falha de escrita e DITA.
        """
        alvo = self._pasta / (PREFIXO_EVENTO_CALADO + apelido_do_evento(nome))
        try:
            alvo.unlink()
        except FileNotFoundError:
            return "ja_estava"
        except OSError:
            return "falhou"
        return "religado"

    def eventos_calados(self) -> frozenset[str]:
        """Os apelidos dos eventos desligados por comando.

        Leitura defensiva pela mesma porta de sempre: `enviados()` ja engole
        `OSError` devolvendo vazio, e vazio aqui quer dizer "nada calado", que
        e a direcao segura — o aviso sai.

        O `if apelido` descarta um `evento_calado_` truncado: a pasta e
        compartilhada e duravel, entao um nome malformado que caia nela e
        PULADO, nunca levantado. Sem ele, a string vazia entraria no conjunto e
        um evento de nome vazio (que nao existe) seria "calado" — inofensivo
        hoje, e o tipo de lixo que confunde quem for depurar isto as duas da
        manha.
        """
        achados = set()
        for nome in self.enviados():
            if not nome.startswith(PREFIXO_EVENTO_CALADO):
                continue
            apelido = nome[len(PREFIXO_EVENTO_CALADO) :]
            if apelido:
                achados.add(apelido)
        return frozenset(achados)

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
    apelido = apelido_do_evento(nome)
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


# ---------------------------------------------------------------------------
# Desligar e religar TODOS os avisos de um evento, por comando
# ---------------------------------------------------------------------------

# O evento que os comandos `/desativarsoloboss` e `/ativarsoloboss` alcancam.
#
# TEXTO, e igual ao `nome` do bloco `[[evento]]` do config.toml. O acordo entre
# os dois arquivos e por NOME, e e por isso que `responder_silenciamento`
# RECUSA quando o nome nao esta na agenda em vez de gravar um marcador que nao
# cala coisa nenhuma.
NOME_DO_SOLO_BOSS = "Solo Boss"


def nomes_calados(
    eventos: list[EventoAgendado], calados: frozenset[str] | set[str]
) -> list[str]:
    """Os eventos desligados, com o nome COMO O USUARIO ESCREVEU.

    O disco guarda `solo-boss` e o config.toml diz `Solo Boss`. Mesma
    disciplina do D-10 na lista de presenca: o apelido e detalhe de
    armazenamento e nunca pode vazar para a tela de ninguem.

    Derivado da agenda, e nao do disco: um marcador orfao — de um evento que o
    usuario renomeou no config.toml depois de te-lo desligado — nao aparece
    aqui porque tambem nao cala nada. Ele e inerte nas duas pontas, e nao ha
    estado escondido nisso.

    Na ordem da agenda, que e a ordem do config.toml: mesma fonte, mesma
    sequencia, sem uma segunda opiniao sobre o que vem antes.
    """
    return [e.nome for e in eventos if apelido_do_evento(e.nome) in calados]


def _o_que_o_evento_anuncia(evento: EventoAgendado) -> tuple[str, ...]:
    """Os avisos que este evento faz, por extenso e com os minutos do config.

    OS NUMEROS SAEM DO `EventoAgendado`, NUNCA DE UM LITERAL. A resposta que
    dissesse "110" a mao passaria a mentir no dia em que o usuario editasse
    `chamar_minutos_antes` — e mentir sobre o que acabou de ser desligado e
    pior do que nao explicar, porque quem leu para de conferir.

    Devolve as PARTES e nao a frase pronta: as duas respostas as coem com
    conjuncoes diferentes ("nem A, nem B" contra "A e B"), e uma frase montada
    aqui obrigaria uma delas a ler errado. Foi exatamente o que aconteceu na
    primeira versao — "nem a chamada de 110 minutos antes, o lembrete de 10
    minutos antes", com o segundo "nem" faltando.
    """
    partes = []
    if evento.chamar_minutos_antes > 0:
        partes.append(f"a chamada de {evento.chamar_minutos_antes} minutos antes")
    if evento.avisar_minutos_antes > 0:
        partes.append(f"o lembrete de {evento.avisar_minutos_antes} minutos antes")
    if evento.avisar_no_horario:
        partes.append("o aviso na hora")
    return tuple(partes) if partes else ("os avisos",)


def _lista_em_prosa(partes: tuple[str, ...], cauda: str) -> str:
    """As partes numa frase que uma pessoa leria em voz alta.

    `cauda` e o que liga a ULTIMA parte as demais, com pontuacao e espacos
    inteiros: `", nem "` para o que foi desligado, `" e "` para o que volta.
    Vem pronta do chamador porque a pontuacao muda junto com a conjuncao, e
    montar `f" {conjuncao} "` aqui produziria "a chamada ... nem o lembrete",
    sem a virgula que a enumeracao negativa pede.

    Uma a tres partes e o tamanho real disto — a lista vem de tres campos do
    `EventoAgendado` —, entao nao ha lista longa para tratar.
    """
    if len(partes) == 1:
        return partes[0]
    return ", ".join(partes[:-1]) + cauda + partes[-1]


def responder_silenciamento(
    registro: RegistroEmDisco,
    eventos: list[EventoAgendado],
    nome: str,
    calar: bool,
    quem: str,
) -> str:
    """Desliga (ou religa) todos os avisos de um evento, e diz o que fez.

    TUDO OU NADA, e nao ha sintaxe para outra coisa. O gate mora em
    `avisos_devidos`, no funil por onde os tres tipos passam — ver a docstring
    de la para a razao de produto de nao existir meia-mudez.

    RECUSA EVENTO QUE NAO ESTA NA AGENDA, e esse ramo fecha um modo de falha
    silencioso de duas caras: um marcador gravado para um nome que o
    `config.toml` nao tem nao cala nada (o gate compara com os eventos
    configurados) e nao aparece no `/status` (que tambem so conhece a agenda).
    Sem esta recusa, o bot responderia "desativei" e as duas superficies
    concordariam em nao mostrar nada — enquanto os avisos continuavam
    chegando.

    NAO E ESTA FUNCAO QUE DECIDE QUEM PODE MANDAR. A fronteira mora em
    `comandos.COMANDOS_DE_MEMBRO`, e estes dois comandos estao FORA dela: um
    `/entrar` de party-mate mexe numa linha da lista de uma ocorrencia, e isto
    apaga doze chamadas por dia da party inteira por tempo indeterminado.
    """
    evento = next((e for e in eventos if e.nome == nome), None)
    if evento is None:
        return (
            f"Nao achei {nome} na agenda do config.toml — nao ha aviso nenhum "
            f"desse evento para desligar nem para religar."
        )

    avisos = _o_que_o_evento_anuncia(evento)

    if calar:
        desfecho = registro.calar_evento(nome)
        if desfecho == "ja_estava":
            return (
                f"Os avisos do {nome} ja estavam desativados. "
                f"Mande /ativarsoloboss quando quiser os dois de volta."
            )
        if desfecho == "falhou":
            # A escrita nao aconteceu, entao a unica resposta honesta e que
            # NADA mudou. Mesmo racional do "falhou" do `entrar`: anunciar um
            # estado que o disco nao guardou faz o usuario parar de esperar
            # avisos que vao continuar chegando.
            return (
                f"Nao consegui gravar o desligamento do {nome} — o disco "
                f"recusou. Os avisos CONTINUAM saindo; mande "
                f"/desativarsoloboss de novo."
            )
        return (
            f"{quem} desativou os avisos do {nome}: "
            f"nem {_lista_em_prosa(avisos, ', nem ')}. "
            f"Nada disso volta sozinho — nem reiniciando o scanner. "
            f"Mande /ativarsoloboss para religar tudo de uma vez."
        )

    desfecho = registro.voltar_a_avisar(nome)
    if desfecho == "ja_estava":
        return f"Os avisos do {nome} ja estavam ligados. Nao mudei nada."
    if desfecho == "falhou":
        # A direcao perigosa, e por isso ela e dita em voz alta: o marcador
        # continua em disco e o boss continua calado. Quem leu isto e a unica
        # pessoa capaz de perceber, entao a frase nao pode soar como sucesso.
        return (
            f"Nao consegui apagar o desligamento do {nome} — o disco recusou. "
            f"Os avisos CONTINUAM desativados; mande /ativarsoloboss de novo."
        )
    return (
        f"{quem} reativou os avisos do {nome}: "
        f"volto a mandar {_lista_em_prosa(avisos, ' e ')}."
    )
