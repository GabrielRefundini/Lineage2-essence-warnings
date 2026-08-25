"""O controle de loot do Solo Boss: de quem e a vez, e quem ja pegou quanto.

O Solo Boss nasce de duas em duas horas e a party reveza quem fica com o
loot. Ate aqui o revezamento era combinado de boca — ninguem lembrava de quem
era a vez nem quantos cada um ja tinha pegado. Este modulo transforma isso em
REGISTRO: designar (`.loot-<nick>`), consultar (`.<nick>`) e consumir
automaticamente quando o horario do boss passa.

DUAS DECISOES DE DESENHO QUE NAO SAO DETALHE:

1. **Pasta propria, sem poda.** O `.agenda/` apaga marcadores com prefixo de
   data depois de 3 dias — certo para "ja avisei", fatal para estatistica.
   O `.loot/` NUNCA e podado: "quantos loots o J4guar pegou" e uma pergunta
   sobre meses, nao sobre a semana.

2. **Consumo com O_CREAT|O_EXCL, tri-estado.** As duas instancias do usuario
   dividem a mesma pasta; exatamente uma registra o loot vencido. E diferente
   do `marcar` do RegistroEmDisco, que colapsa falha de disco em True porque
   aviso perdido e pior que duplicado — aqui e o contrario: registro perdido
   em silencio e estatistica errada para sempre, entao falha de disco MANTEM
   a designacao para o proximo tick tentar de novo.

MESMA DISCIPLINA DA AGENDA: o tempo entra por parametro em tudo. Nenhum
`datetime.now()`, nenhum relogio proprio — e o que permite testar a corrida
de duas instancias e o consumo atrasado em milissegundos.

Este modulo NUNCA importa `comandos` nem `sessao`: sao eles que importam
daqui, e um ciclo mataria os dois.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .agenda import (
    Aviso,
    EventoAgendado,
    TipoDeAviso,
    ocorrencias_do_dia,
    proxima_ocorrencia,
)

# Prefixos dos arquivos que convivem na pasta — mesma tecnica de namespaces do
# `.agenda/`: a atomicidade e o compartilhamento valem para todos de graca.
_PREFIXO_PEGOU = "pegou_"
_PREFIXO_NICK = "nick_"
_ARQUIVO_PROXIMO = "proximo.json"

# O carimbo de horario no nome do arquivo: `pegou_2026-08-25-1000_j4guar`.
# A identidade do registro E o nome — o arquivo fica vazio de proposito.
_FORMATO_CARIMBO = "%Y-%m-%d-%H%M"

# O charset de nick do L2, e um minimo de 2 para que `.loot-a` de um dedo
# escorregado nao vire designacao.
#
# MORA AQUI, e nao no `comandos.py` onde nasceu, porque `interpretar_pegou`
# precisa validar nick e o `loot.py` NAO PODE importar `comandos` (ciclo — ver
# o fim da docstring do modulo). O `comandos.py` ja importa `apelido` daqui,
# entao a direcao da dependencia so foi reusada, nao invertida.
NICK_VALIDO = re.compile(r"[A-Za-z0-9]{2,16}")

# Quanto o horario digitado no `.pegou` pode estar longe de uma ocorrencia
# real do Solo Boss e ainda assim encaixar nela.
#
# O NUMERO NAO E ARBITRARIO. O boss nasce de duas em duas horas, entao
# QUALQUER minuto do dia esta a no maximo 60 min de alguma ocorrencia: uma
# tolerancia de 60 nunca recusaria nada e transformaria o encaixe em
# decoracao. 30 aceita "lembrei 20 minutos depois" — o caso real — e recusa
# `.pegou 19:00`, que e exatamente ambiguo entre o boss das 18:00 e o das
# 20:00. Ambiguidade RECUSA, porque o registro e permanente e nao ha poda que
# desfaca um palpite errado.
TOLERANCIA_DE_ENCAIXE = timedelta(minutes=30)


def apelido(nick: str) -> str:
    """Slug do nick — o mesmo idioma de `agenda.chave_da_ocorrencia`.

    E o que faz `.J4GUAR` e `.j4guar` serem a mesma pessoa, e o que torna o
    nick seguro para virar nome de arquivo.
    """
    return re.sub(r"[^a-z0-9]+", "-", nick.lower()).strip("-")


def exibir(nick: str) -> str:
    """Primeira letra maiuscula, o resto como veio.

    O `.loot-j4guar` chega minusculo do WhatsApp e a resposta nao pode
    parecer descuidada — "j4guar pega o loot" le como bot quebrado.
    """
    return nick[:1].upper() + nick[1:]


def eh_solo_boss(nome: str) -> bool:
    """Este evento da agenda e o Solo Boss?

    Comparacao tolerante por decisao do usuario: "Solo Boss", "SoloBoss" e
    "SOLO-BOSS" sao o mesmo evento. Sem config nova — o config.toml que ja
    existe basta.
    """
    return re.sub(r"[\s_\-]+", "", nome.lower()) == "soloboss"


@dataclass(frozen=True)
class Designacao:
    """Quem pega o loot do proximo Solo Boss, e de QUAL ocorrencia.

    O `alvo` e o que impede a designacao das 10:00 de vazar para o boss das
    12:00 quando ninguem consumiu a tempo.
    """

    nick: str  # como foi digitado
    alvo: datetime  # a ocorrencia do boss que ela mira
    designado_em: datetime


@dataclass(frozen=True)
class Correcao:
    """O que aconteceu numa tentativa de mexer no dono de um loot consumado.

    O `estado` e uma string de CINCO valores e nao um booleano pelo MESMO
    motivo do `_criar` logo abaixo: a resposta precisa distinguir "trocou" de
    "criei do zero" de "ja era dele" de "nao tinha nada para corrigir" de "o
    disco falhou". Colapsar qualquer par desses faria o bot mentir sobre o que
    acabou de acontecer com a estatistica — e um "pronto" depois de uma falha
    de disco e indistinguivel de sucesso para quem esta do outro lado do
    WhatsApp.

    O QUINTO estado, `"criado"`, nasceu com o `.pegou`. O `corrigir` nunca
    cria registro — ele so troca o dono de um que ja existe, e por isso os
    quatro primeiros bastavam. O `atribuir` cria quando nao havia NADA, que e
    o caso que o usuario relatou (o scanner estava fora do ar quando o boss
    passou). "Registrei o loot que ninguem tinha registrado" e uma frase
    diferente de "passou do Fulano para o Beltrano", e sair com a segunda
    quando aconteceu a primeira nomearia um dono anterior que nunca existiu.

    O `anterior` e o SLUG do dono antigo, minusculo, porque e o nome do
    arquivo que o guarda — nao ha outro registro da caixa original. No estado
    `"criado"` ele fica `""`, e a mensagem desse estado NAO pode chamar
    `exibir(anterior)`.
    """

    # "corrigido" | "criado" | "mesmo_dono" | "sem_registro" | "falhou"
    estado: str
    anterior: str = ""  # o slug do dono antigo
    novo: str = ""  # o nick novo, como foi digitado
    alvo: datetime | None = None


@dataclass(frozen=True)
class PedidoDePegou:
    """O `.pegou` DEPOIS da gramatica e ANTES do relogio.

    Nenhum `datetime` aqui, de proposito: e a mesma disciplina do modulo
    inteiro — o tempo entra por parametro, nunca por `datetime.now()`. Um
    pedido guarda o que a pessoa DIGITOU (hora, minuto e, quando ela quis ser
    explicita, o dia); transformar isso num instante e trabalho de
    `momento_desejado`, que recebe o `agora` de fora.

    E o que permite testar a virada da meia-noite sem esperar meia-noite: a
    frase "18:00" nao muda de sentido, mas o instante que ela nomeia muda
    conforme a hora em que foi dita.
    """

    nick: str  # como foi digitado
    hora: int
    minuto: int
    dia: int | None = None
    mes: int | None = None
    ano: int | None = None


class RegistroDeLoot:
    """Os loots consumados e a designacao corrente, em disco compartilhado.

    Tres tipos de arquivo convivem na pasta, cada um com prefixo proprio:

    - `pegou_{YYYY-MM-DD}-{HHMM}_{slug}` — um loot consumado (arquivo vazio;
      a identidade e o nome).
    - `nick_{slug}` — este nick ja foi alvo de `.loot-<nick>` alguma vez.
      Alimenta o portao do `.<nick>`.
    - `proximo.json` — a designacao corrente.

    NAO tem poda, de proposito: estatistica de loot e para sempre.
    """

    def __init__(self, pasta: Path) -> None:
        self._pasta = pasta
        self._pasta.mkdir(parents=True, exist_ok=True)

    # -- primitivas ---------------------------------------------------------

    def _criar(self, nome: str) -> str:
        """Cria um marcador vazio. Tri-estado: criado | ja_existia | falhou.

        Tri-estado porque `consumir` precisa distinguir "a outra instancia
        registrou" (apaga a designacao) de "o disco falhou" (MANTEM a
        designacao para tentar de novo). Colapsar os dois num booleano faria
        uma falha de disco apagar a designacao sem registrar nada — o loot
        sumiria da estatistica em silencio.
        """
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

    def _nome_do_pegou(self, nick: str, alvo: datetime) -> str:
        return f"{_PREFIXO_PEGOU}{alvo.strftime(_FORMATO_CARIMBO)}_{apelido(nick)}"

    # -- loots consumados ---------------------------------------------------

    def registrar(self, nick: str, alvo: datetime) -> bool:
        """True somente quando ESTE processo criou o registro agora."""
        return self._criar(self._nome_do_pegou(nick, alvo)) == "criado"

    def registros(self) -> list[tuple[str, datetime]]:
        """Todos os loots consumados: (slug, horario do boss).

        Nome malformado e pulado sem levantar: a pasta e compartilhada e
        duravel, e qualquer lixo que caia nela nao pode virar excecao no meio
        do farm.
        """
        achados: list[tuple[str, datetime]] = []
        try:
            nomes = [c.name for c in self._pasta.iterdir()]
        except OSError:
            return []
        for nome in nomes:
            if not nome.startswith(_PREFIXO_PEGOU):
                continue
            carimbo, _, slug = nome[len(_PREFIXO_PEGOU) :].partition("_")
            if not slug:
                continue
            try:
                alvo = datetime.strptime(carimbo, _FORMATO_CARIMBO)
            except ValueError:
                continue
            achados.append((slug, alvo))
        return achados

    def resumo(self, nick: str) -> tuple[int, datetime | None]:
        """Quantos loots este nick pegou, e quando foi o ultimo."""
        slug = apelido(nick)
        alvos = [alvo for dono, alvo in self.registros() if dono == slug]
        return (len(alvos), max(alvos) if alvos else None)

    # -- designacao ---------------------------------------------------------

    def designar(self, nick: str, alvo: datetime, agora: datetime) -> Designacao:
        """Grava quem pega o proximo loot. A ultima palavra vence.

        A escrita e ATOMICA: escreve num tmp com o pid no nome e `os.replace`
        por cima. O replace e atomico no Windows no mesmo volume, entao a
        outra instancia nunca le um json pela metade; o pid no nome impede
        uma instancia de atropelar o tmp da outra.
        """
        designacao = Designacao(nick=nick, alvo=alvo, designado_em=agora)
        temporario = self._pasta / f"{_ARQUIVO_PROXIMO}.tmp-{os.getpid()}"
        temporario.write_text(
            json.dumps(
                {
                    "nick": nick,
                    "alvo": alvo.isoformat(),
                    "designado_em": agora.isoformat(),
                }
            ),
            encoding="utf-8",
        )
        os.replace(temporario, self._pasta / _ARQUIVO_PROXIMO)
        # O nick vira conhecido para sempre — e o que abre o `.<nick>` para
        # ele. Idempotente: "ja_existia" e tao bom quanto "criado".
        self._criar(f"{_PREFIXO_NICK}{apelido(nick)}")
        return designacao

    def designacao(self) -> Designacao | None:
        """A designacao corrente. Ausente, ilegivel ou invalida -> None.

        Leitura defensiva de proposito: a outra instancia pode ter morrido no
        meio de uma escrita, e um arquivo meio-escrito nao pode derrubar o
        laco — o pior aceitavel e perder a designacao, nunca o scanner.
        """
        try:
            bruto = (self._pasta / _ARQUIVO_PROXIMO).read_text(encoding="utf-8")
            dados = json.loads(bruto)
            nick = dados["nick"]
            if not isinstance(nick, str) or not nick:
                return None
            return Designacao(
                nick=nick,
                alvo=datetime.fromisoformat(dados["alvo"]),
                designado_em=datetime.fromisoformat(dados["designado_em"]),
            )
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def consumir(self, agora: datetime) -> Designacao | None:
        """Registra o loot da designacao vencida. Devolve quem, se FOI este
        processo que registrou — e ele que loga.

        - Sem designacao, ou antes do alvo: None, nada muda.
        - "criado": este processo registrou; apaga a designacao e devolve.
        - "ja_existia": a outra instancia venceu; apaga a designacao e cala.
        - "falhou": disco falhou; MANTEM a designacao e o proximo tick tenta
          de novo — consumir em silencio seria estatistica errada para sempre.
        """
        designacao = self.designacao()
        if designacao is None or agora < designacao.alvo:
            return None

        estado = self._criar(self._nome_do_pegou(designacao.nick, designacao.alvo))
        if estado == "falhou":
            return None
        (self._pasta / _ARQUIVO_PROXIMO).unlink(missing_ok=True)
        return designacao if estado == "criado" else None

    def cancelar(self) -> Designacao | None:
        """Apaga a designacao corrente. Devolve quem perdeu a vez, ou None.

        DUAS COISAS QUE PARECEM DETALHE E NAO SAO:

        1. **`missing_ok=True` e o que torna o cancelamento IDEMPOTENTE.** As
           duas instancias do usuario dividem a mesma pasta, e a segunda a
           mandar encontra o arquivo ja apagado. Levantar ali transformaria um
           comando inofensivo — cancelar o que ja esta cancelado — em erro no
           meio do farm.

        2. **Nao mexe nos `pegou_*` nem nos `nick_*`, de proposito.** Cancelar
           e sobre de quem e a VEZ; apagar o historico junto destruiria o
           registro que o `.<nick>` consulta, e meses de estatistica sumiriam
           num comando de sete letras.

        A exposicao a `OSError` num disco travado e a mesma que `consumir` ja
        tem — consistencia deliberada, nao esquecimento.
        """
        anterior = self.designacao()
        (self._pasta / _ARQUIVO_PROXIMO).unlink(missing_ok=True)
        return anterior

    def corrigir(self, nick: str) -> Correcao:
        """Troca o dono do loot JA CONSUMADO mais recente. Nunca levanta.

        TRES COISAS QUE PARECEM DETALHE E SAO O TRABALHO INTEIRO:

        1. **CRIAR o registro novo ANTES de apagar o velho.** A ordem nao e
           estilo, e o desenho da falha. Se o criar falhar: nada mudou, o
           registro velho continua la. Se o apagar falhar: sobra um registro
           DUPLICADO, que aparece no `.<nick>` e e consertavel com outro
           `.corrigir`. A ordem inversa PERDE o loot em silencio, que e o pior
           desfecho possivel numa estatistica que este projeto trata como
           "para sempre" — nao ha backup e nao ha poda que traga de volta.

        2. **A guarda do mesmo apelido, e ela e o bug mais facil de escrever
           aqui.** `apelido("TIOMAD") == apelido("TioMad")`, entao os dois
           geram o MESMO nome de arquivo: o `_criar` devolveria "ja_existia" e
           o passo de apagar destruiria o unico registro que existia. O
           retorno antecipado e a unica coisa entre um no-op inofensivo e a
           perda do loot que o usuario estava tentando confirmar.

        3. **So o registro MAIS RECENTE, nunca historico arbitrario.** O raio
           de estrago e limitado por DESENHO, nao por cuidado de quem digita:
           nao existe sintaxe para atingir o loot da semana passada, entao
           nenhuma sequencia de comandos pode desfazer meses de estatistica.
           Corrigir registro arbitrario nao e funcionalidade que alguem pediu.
        """
        achados = self.registros()
        if not achados:
            return Correcao("sem_registro", novo=nick)

        # Desempate deterministico pelo slug: com um duplicado no mesmo alvo,
        # duas chamadas seguidas precisam escolher o MESMO registro.
        anterior, alvo = max(achados, key=lambda par: (par[1], par[0]))

        if apelido(nick) == anterior:
            return Correcao("mesmo_dono", anterior=anterior, novo=nick, alvo=alvo)

        estado = self._criar(self._nome_do_pegou(nick, alvo))
        if estado == "falhou":
            return Correcao("falhou", anterior=anterior, novo=nick, alvo=alvo)

        # "ja_existia" segue para o apagar DE PROPOSITO: ele so acontece
        # quando o alvo tinha DOIS donos registrados — o duplicado que a regra
        # 1 aceita deixar para tras. Apagar o velho ali e o conserto, nao a
        # perda.
        try:
            # `apelido()` e idempotente sobre um slug, entao `_nome_do_pegou`
            # reconstroi o nome do arquivo velho sem formatador novo.
            (self._pasta / self._nome_do_pegou(anterior, alvo)).unlink(
                missing_ok=True
            )
        except OSError:
            # Sobrou duplicado: visivel no `.<nick>` e consertavel. Seguir em
            # frente e melhor que levantar no meio do farm.
            pass

        # O nick corrigido vira conhecido, senao o `.<nick>` dele nao
        # responderia e a correcao ficaria invisivel exatamente para quem foi
        # corrigido. Idempotente: "ja_existia" e tao bom quanto "criado".
        self._criar(f"{_PREFIXO_NICK}{apelido(nick)}")
        return Correcao("corrigido", anterior=anterior, novo=nick, alvo=alvo)

    def atribuir(self, nick: str, alvo: datetime) -> Correcao:
        """Poe o loot de UM boss especifico no nome deste nick. Nunca levanta.

        E o motor do `.pegou`, e a diferenca dele para o `corrigir` logo acima
        e o alvo: o `corrigir` mira o registro MAIS RECENTE e nao aceita
        argumento de horario nenhum; o `atribuir` recebe um `alvo` ENDERECADO,
        que o chamador ja encaixou numa ocorrencia real da agenda. Os dois
        limites sao reais e sao DIFERENTES — o do `corrigir` e "nao existe
        sintaxe que alcance o passado", o do `atribuir` e "so alcanca instante
        que a agenda produz, e so no passado". E por isso que os dois comandos
        coexistem em vez de um substituir o outro.

        TRES COISAS QUE PARECEM DETALHE E SAO O TRABALHO INTEIRO:

        1. **CRIAR o registro novo ANTES de apagar o velho**, a mesma ordem do
           `corrigir`, e pelo mesmo desenho da falha. Se o criar falhar: nada
           muda, o dono antigo continua com o loot. Se o apagar falhar: sobra
           um DUPLICADO, visivel no `.<nick>` e consertavel com outro `.pegou`.
           A ordem inversa PERDE o loot em silencio, que e o pior desfecho
           possivel numa estatistica que nunca e podada e nao tem backup.

        2. **A guarda compara a LISTA INTEIRA de donos, nao o primeiro.** Com
           um unico dono que ja e o nick novo, mexer em disco seria destrutivo:
           `_criar` devolveria "ja_existia" e o apagar destruiria o unico
           registro que existia — e a resposta ainda diria sucesso. Mas quando
           o alvo tem DOIS donos e um deles ja e o nick novo, sair cedo
           deixaria o duplicado de pe; o certo ali e seguir e deixar o passo do
           apagar colapsar. Sao dois casos diferentes, e so a comparacao com a
           lista inteira os separa. E aqui que ela difere do `corrigir`, que
           olha um registro so e por isso compara um slug so.

        3. **Sem dono nenhum, CRIA** — o caso que o `corrigir` nao tem. E o
           motivo do comando existir: se o scanner estava fora do ar quando o
           boss passou, nao ha registro nenhum para corrigir, e o unico
           conserto ate aqui era criar arquivo a mao no Explorer.
        """
        donos = sorted(slug for slug, quando in self.registros() if quando == alvo)
        slug_novo = apelido(nick)

        if not donos:
            estado = self._criar(self._nome_do_pegou(nick, alvo))
            if estado == "falhou":
                return Correcao("falhou", novo=nick, alvo=alvo)
            # "ja_existia" aqui e impossivel (nao havia dono), mas tratar
            # junto com "criado" e honesto: o desfecho para quem le e o
            # mesmo — o loot daquele boss agora esta no nome dele.
            self._criar(f"{_PREFIXO_NICK}{slug_novo}")
            self._soltar_designacao(alvo)
            return Correcao("criado", novo=nick, alvo=alvo)

        if donos == [slug_novo]:
            return Correcao(
                "mesmo_dono", anterior=slug_novo, novo=nick, alvo=alvo
            )

        anterior = next(d for d in donos if d != slug_novo)

        estado = self._criar(self._nome_do_pegou(nick, alvo))
        if estado == "falhou":
            # Nada apagado: o loot continua exatamente de quem era.
            return Correcao("falhou", anterior=anterior, novo=nick, alvo=alvo)

        # "ja_existia" segue para o apagar DE PROPOSITO: ele so acontece
        # quando o alvo tinha DOIS donos registrados. Apagar o velho ali e o
        # conserto do duplicado, nao a perda.
        try:
            # `apelido()` e idempotente sobre um slug, entao `_nome_do_pegou`
            # reconstroi o nome do arquivo velho sem formatador novo.
            (self._pasta / self._nome_do_pegou(anterior, alvo)).unlink(
                missing_ok=True
            )
        except OSError:
            # Sobrou duplicado: visivel no `.<nick>` e consertavel. Seguir em
            # frente e melhor que levantar no meio do farm.
            pass

        self._criar(f"{_PREFIXO_NICK}{slug_novo}")
        self._soltar_designacao(alvo)
        return Correcao("corrigido", anterior=anterior, novo=nick, alvo=alvo)

    def _soltar_designacao(self, alvo: datetime) -> None:
        """Apaga a designacao corrente SE ela mirar exatamente este alvo.

        Este e o unico ponto deste comando que encosta na fronteira entre a
        VEZ e o HISTORICO — a mesma fronteira que o `cancelar` e o `corrigir`
        respeitam sem atravessar. Ele atravessa num caso so, e o caso e
        concreto: se o scanner estava fora do ar as 18:00, a designacao das
        18:00 continua em `proximo.json` sem nunca ter sido consumida. O
        usuario roda `.pegou 18:00 Korzis` e, no proximo tick, o `consumir()`
        cria um SEGUNDO dono para as 18:00 — um duplicado que ninguem pediu e
        que aparece na contagem de quem nao pegou nada.

        Uma designacao cujo boss ja passou E ja tem dono escrito a mao nao tem
        mais alvo nenhum. A comparacao e por igualdade EXATA justamente para a
        regra nao vazar: a designacao do boss das 20:00 fica intacta quando o
        usuario registra o das 18:00, porque aquela ainda tem para onde ir.
        """
        designacao = self.designacao()
        if designacao is None or designacao.alvo != alvo:
            return
        try:
            (self._pasta / _ARQUIVO_PROXIMO).unlink(missing_ok=True)
        except OSError:
            # Mesma exposicao do `cancelar` e do `consumir`: um disco travado
            # nao pode virar excecao no meio do farm.
            pass

    def nicks_conhecidos(self) -> frozenset[str]:
        """Slugs que o `.<nick>` aceita consultar.

        A uniao de quem ja foi designado (`nick_*`), quem ja pegou loot
        (`pegou_*`) e o designado corrente. E o portao contra `.palavra`
        aleatoria: sem ele o scanner responderia lixo a qualquer palavra com
        ponto no grupo.
        """
        try:
            nomes = [c.name for c in self._pasta.iterdir()]
        except OSError:
            nomes = []
        conhecidos = {
            nome[len(_PREFIXO_NICK) :]
            for nome in nomes
            if nome.startswith(_PREFIXO_NICK)
        }
        conhecidos.update(slug for slug, _ in self.registros())
        designacao = self.designacao()
        if designacao is not None:
            conhecidos.add(apelido(designacao.nick))
        conhecidos.discard("")
        return frozenset(conhecidos)


# -- texto e decisao (puras: tempo por parametro, sem disco proprio) ---------


def descrever_momento(alvo: datetime, agora: datetime) -> str:
    """"hoje as 10:00", "ontem as 22:00", "em 23/08 as 14:00".

    Relativo porque a pergunta real do `.j4guar` e "faz quanto tempo?" —
    "2026-08-25T10:00" obrigaria a pessoa a fazer a conta que o bot deveria
    ter feito.
    """
    hora = f"{alvo.hour:02d}:{alvo.minute:02d}"
    dias = (agora.date() - alvo.date()).days
    if dias == 0:
        return f"hoje as {hora}"
    if dias == 1:
        return f"ontem as {hora}"
    return f"em {alvo.day:02d}/{alvo.month:02d} as {hora}"


# O horario do `.pegou`, na unica grafia que esta task aceita. As faixas
# (hora 0-23, minuto 0-59) NAO moram aqui de proposito: este arquivo prefere
# uma linha legivel a uma expressao esperta, e uma faixa numerica escrita em
# regex e ilegivel na revisao seguinte.
_HORARIO_DO_PEGOU = re.compile(r"(\d{1,2}):(\d{2})")


def interpretar_pegou(argumento: str) -> PedidoDePegou | None:
    """A gramatica do `.pegou`, e ela mora AQUI por um motivo.

    Esta funcao e o PORTAO do parser e o LEITOR do responder: o
    `comandos.py` so devolve `LOOT_ATRIBUIR` quando ela aceita o argumento, e
    o `responder_atribuicao` le o mesmo argumento com a mesma funcao. Uma
    gramatica no parser e outra no responder divergiriam no primeiro ajuste, e
    o comando passaria a ACEITAR o que nao sabe EXECUTAR — que e o modo de
    falha mais caro possivel num comando que escreve estado permanente.

    O preco e um parse duplicado por comando: uma vez por mensagem, para um
    comando que o usuario manda uma vez por semana. Irrelevante.

    Recebe o argumento ja sem o `.pegou`. Devolve None para qualquer coisa que
    nao entenda — nunca levanta, nunca adivinha.

    Sem palavras reservadas aqui: o `.pegou` nao tem forma destrutiva sem
    argumento, entao nao existe a colisao que obrigou o
    `_PALAVRAS_DE_CANCELAMENTO` do `.loot-` a nascer.
    """
    palavras = (argumento or "").split()
    if len(palavras) != 2:
        return None

    bruto, nick = palavras

    casado = _HORARIO_DO_PEGOU.fullmatch(bruto)
    if casado is None:
        return None
    hora, minuto = int(casado.group(1)), int(casado.group(2))
    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        return None

    if not NICK_VALIDO.fullmatch(nick):
        return None

    # O nick sai COMO FOI DIGITADO: a resposta mostra o que a pessoa
    # escreveu, e normalizar e trabalho de `apelido()`, la no disco.
    return PedidoDePegou(nick=nick, hora=hora, minuto=minuto)


def momento_desejado(pedido: PedidoDePegou, agora: datetime) -> datetime | None:
    """O instante que a pessoa quis dizer. None quando nao existe nenhum.

    SEM DATA, o horario resolve para a ocorrencia mais recente que JA PASSOU,
    nunca para o futuro. O recuo de um dia e uma linha e e a regra inteira:
    as 02h da manha, quem digita "18:00" esta falando do boss de ONTEM — o
    boss de hoje as 18:00 ainda nao aconteceu, e registrar loot de um boss que
    ainda nao nasceu nao e coisa que alguem queira dizer.

    (A forma com data explicita entra no Task 3; ate la ela devolve None em
    vez de fingir que entendeu.)
    """
    if pedido.dia is not None:
        # Task 3: `.pegou 23/08 18:00 Korzis`. Ate la, um pedido com data nao
        # tem como virar instante, e mentir seria pior que recusar.
        return None

    desejado = agora.replace(
        hour=pedido.hora, minute=pedido.minuto, second=0, microsecond=0
    )
    if desejado > agora:
        desejado -= timedelta(days=1)
    return desejado


def encaixar_na_agenda(
    desejado: datetime, eventos: list[EventoAgendado], agora: datetime
) -> datetime | None:
    """A ocorrencia REAL de Solo Boss mais proxima do horario desejado.

    None quando nao ha Solo Boss na agenda, ou quando a melhor candidata esta
    mais longe que `TOLERANCIA_DE_ENCAIXE`. Esse None e o unico ponto entre
    "nao entendi" e um registro ORFAO PERMANENTE: a pasta de loot nunca e
    podada, entao um `pegou_` num horario que nenhum boss produz fica na
    estatistica para sempre e nao ha comando nenhum que o alcance.

    A varredura sao TRES dias centrados no DESEJADO, nunca em `agora`. E o que
    faz a virada da meia-noite funcionar nos dois sentidos: as 00:10, "23:50"
    quer dizer ontem, mas a ocorrencia mais proxima que ja passou e a de HOJE
    as 00:00, dez minutos depois do desejado. Centrar em `agora` a perderia.

    Ocorrencia no futuro e DESCARTADA aqui, e nao la em cima: sem esta linha,
    `.pegou 18:00` as 17:50 encaixaria no boss das 18:00 que ainda nao
    aconteceu, e o loot de um boss inexistente entraria na contagem.
    """
    evento = next((e for e in eventos if eh_solo_boss(e.nome)), None)
    if evento is None:
        return None

    candidatas: list[datetime] = []
    for deslocamento in (-1, 0, 1):
        dia = desejado.date() + timedelta(days=deslocamento)
        candidatas.extend(a for a in ocorrencias_do_dia(evento, dia) if a <= agora)
    if not candidatas:
        return None

    # O desempate pela ocorrencia mais CEDO e deterministico de proposito:
    # duas chamadas iguais precisam escolher o mesmo registro, senao um
    # `.pegou` repetido criaria um segundo dono num alvo vizinho.
    melhor = min(candidatas, key=lambda alvo: (abs(alvo - desejado), alvo))
    if abs(melhor - desejado) > TOLERANCIA_DE_ENCAIXE:
        return None
    return melhor


def horarios_do_solo_boss(eventos: list[EventoAgendado]) -> list[str]:
    """Os horarios do Solo Boss como texto, ordenados. Vazio se nao houver.

    Existe para a mensagem de RECUSA. Recusar sem dizer quais horarios valem
    obrigaria a pessoa a abrir o `config.toml` no meio do farm para descobrir
    por que o comando nao pegou — e a essa altura ela ja desistiu.
    """
    evento = next((e for e in eventos if eh_solo_boss(e.nome)), None)
    if evento is None:
        return []
    return [f"{h:02d}:{m:02d}" for h, m in sorted(evento.horarios)]


def nick_para_o_aviso(aviso: Aviso, designacao: Designacao | None) -> str | None:
    """O nome que entra no aviso de antecedencia, ou None.

    Tres condicoes, todas obrigatorias:

    - aviso de ANTES: so a antecedencia carrega o loot, por decisao do
      usuario (o Solo Boss nem tem aviso de AGORA);
    - evento e o Solo Boss: TvT e Prime jamais ganham a linha;
    - MESMO alvo: a comparacao e o que impede a designacao das 10:00 de
      vazar para o aviso do boss das 12:00 quando ninguem consumiu a tempo.
    """
    if designacao is None:
        return None
    if aviso.tipo is not TipoDeAviso.ANTES:
        return None
    if not eh_solo_boss(aviso.evento):
        return None
    if designacao.alvo != aviso.alvo:
        return None
    return exibir(designacao.nick)


def responder_consulta(registro: RegistroDeLoot, nick: str, agora: datetime) -> str:
    """A resposta do `.<nick>`: total, ultimo, e se a proxima vez e dele."""
    total, ultimo = registro.resumo(nick)
    nome = exibir(nick)
    if total == 0 or ultimo is None:
        resposta = f"{nome} ainda nao pegou nenhum loot de Solo Boss."
    else:
        palavra = "loot" if total == 1 else "loots"
        resposta = (
            f"{nome} pegou {total} {palavra} de Solo Boss. "
            f"Ultimo: {descrever_momento(ultimo, agora)}."
        )
    designacao = registro.designacao()
    if designacao is not None and apelido(designacao.nick) == apelido(nick):
        resposta += " O proximo e dele."
    return resposta


def responder_designacao(
    registro: RegistroDeLoot,
    eventos: list[EventoAgendado],
    agora: datetime,
    nick: str,
) -> str:
    """Obedece o `.loot-<nick>`: grava a designacao e confirma o horario.

    Sem Solo Boss na agenda (ou sem ocorrencia futura), NADA e gravado — uma
    designacao sem alvo seria um registro que nunca consome e nunca some.
    """
    evento = next((e for e in eventos if eh_solo_boss(e.nome)), None)
    proximo = proxima_ocorrencia(agora, [evento]) if evento is not None else None
    if proximo is None:
        return (
            "Nao achei o Solo Boss na agenda do config.toml — "
            "nao da para marcar o loot."
        )

    nome_do_evento, alvo = proximo
    anterior = registro.designacao()
    registro.designar(nick, alvo, agora)

    resposta = (
        f"{exibir(nick)} pega o loot do proximo {nome_do_evento}, "
        f"as {alvo.hour:02d}:{alvo.minute:02d}."
    )
    # So menciona o substituido quando era OUTRO nick para o MESMO boss: uma
    # designacao velha de um boss que ja passou nao "era" de ninguem agora.
    if (
        anterior is not None
        and anterior.alvo == alvo
        and apelido(anterior.nick) != apelido(nick)
    ):
        resposta += f" (Era do {exibir(anterior.nick)}.)"
    return resposta


def responder_cancelamento(
    registro: RegistroDeLoot,
    eventos: list[EventoAgendado],
    agora: datetime,
) -> str:
    """Obedece o `.loot-`: apaga a designacao e diz de quem era.

    APAGA PRIMEIRO, olha a agenda depois — e a imagem-espelho da regra do
    `responder_designacao`, e a assimetria e proposital. GRAVAR depende da
    agenda ter um alvo (uma designacao sem alvo nunca consome e nunca some),
    mas APAGAR nao pode depender de nada: um config.toml quebrado, ou o Solo
    Boss renomeado por engano, prenderia a designacao corrente para sempre
    sem nenhum jeito de solta-la pelo WhatsApp.

    A resposta nomeia QUEM perdeu a vez e QUAL boss, porque "cancelado"
    sozinho obrigaria a pessoa a lembrar o que estava marcado.
    """
    anterior = registro.cancelar()

    # A grafia sai do config.toml do usuario ("Solo Boss", "SoloBoss"), com
    # recurso ao nome canonico quando a agenda nao tem o evento — o que nao
    # impede o cancelamento, so o deixa menos especifico.
    evento = next((e for e in eventos if eh_solo_boss(e.nome)), None)
    nome_do_evento = evento.nome if evento is not None else "Solo Boss"

    if anterior is not None:
        return (
            f"Loot do {nome_do_evento} das "
            f"{anterior.alvo.hour:02d}:{anterior.alvo.minute:02d} cancelado — "
            f"era do {exibir(anterior.nick)}. O aviso sai sem nome."
        )

    # Sem nada marcado a resposta e uma correcao de expectativa, entao ela
    # nomeia o boss de que se esta falando: e o PROXIMO que estava em jogo.
    proximo = proxima_ocorrencia(agora, [evento]) if evento is not None else None
    if proximo is None:
        return f"Nao havia loot marcado para o proximo {nome_do_evento}."
    _, alvo = proximo
    return (
        f"Nao havia loot marcado para o {nome_do_evento} das "
        f"{alvo.hour:02d}:{alvo.minute:02d}."
    )


def responder_correcao(
    registro: RegistroDeLoot,
    eventos: list[EventoAgendado],
    agora: datetime,
    nick: str,
) -> str:
    """Obedece o `.corrigir-<nick>`: troca o dono do ultimo loot e NOMEIA a
    troca.

    O texto NAO E COSMETICO. Ele e a unica rede de seguranca do usuario
    contra ter corrigido o registro ERRADO — o comando sempre mira o loot
    mais recente, e se outro boss passou no meio tempo o alvo mudou sem
    ninguem avisar. Por isso a resposta diz o boss, o momento, de quem era e
    para quem foi, e nunca um "pronto" seco: quem le tem que conseguir
    perceber, na hora, que corrigiu o boss das 12:00 quando queria o das
    10:00.

    O momento sai por `descrever_momento`, o mesmo do `.<nick>` — o DIA e
    justamente a informacao que falta quando o registro errado e o de ontem.

    LIMITACAO ACEITA: o dono antigo sai slug-cased ("Tiomad", nao "TioMad")
    porque o nome do arquivo e o unico registro que existe dele — restaurar a
    caixa original exigiria adivinhar, e um nome adivinhado numa rede de
    seguranca vale menos que um nome feio e honesto.
    """
    correcao = registro.corrigir(nick)

    # A grafia sai do config.toml do usuario, com recurso ao nome canonico —
    # mesmo padrao do `responder_cancelamento`.
    evento = next((e for e in eventos if eh_solo_boss(e.nome)), None)
    nome_do_evento = evento.nome if evento is not None else "Solo Boss"

    if correcao.estado == "sem_registro":
        return (
            f"Nao ha nenhum loot de {nome_do_evento} registrado para corrigir."
        )

    momento = descrever_momento(correcao.alvo, agora)

    if correcao.estado == "mesmo_dono":
        return (
            f"O loot do {nome_do_evento} de {momento} JA era do "
            f"{exibir(correcao.novo)} — nada mudou."
        )

    if correcao.estado == "falhou":
        return (
            f"Nao consegui gravar a correcao do {nome_do_evento} de {momento} — "
            f"o loot continua do {exibir(correcao.anterior)}, nao do "
            f"{exibir(correcao.novo)}."
        )

    return (
        f"O loot do {nome_do_evento} de {momento} passou do "
        f"{exibir(correcao.anterior)} para o {exibir(correcao.novo)}."
    )


def responder_atribuicao(
    registro: RegistroDeLoot,
    eventos: list[EventoAgendado],
    agora: datetime,
    argumento: str,
) -> str:
    """Obedece o `.pegou [data] <hora> <nick>`: registra o loot de um boss que
    JA PASSOU, mesmo quando nunca houve designacao nenhuma.

    A RESPOSTA SEMPRE DIZ O DIA, por `descrever_momento`, e isso nao e
    cosmetico. O `.corrigir` mira o registro mais recente e a duvida de quem
    digita e "sera que outro boss passou no meio tempo?"; o `.pegou` alcanca
    horario ARBITRARIO, e a duvida passa a ser outra e maior: "sera que ele
    entendeu o dia que eu quis dizer?". As 02h da manha, `.pegou 18:00 Korzis`
    fala do boss de ONTEM — e a unica coisa entre acertar e registrar o boss
    errado e a resposta dizer "de ontem as 18:00" em vez de um "pronto" seco.
    E a mesma razao que o `responder_correcao` ja documenta, aplicada a um
    comando de alcance maior.

    Cada None do caminho tem TEXTO PROPRIO, porque cada um pede uma correcao
    diferente de quem digitou: arrumar a frase, arrumar o config.toml, arrumar
    a data ou arrumar o horario.
    """
    pedido = interpretar_pegou(argumento)
    if pedido is None:
        # Nao deveria acontecer — o parser so devolve LOOT_ATRIBUIR quando
        # esta mesma funcao aceita. Existe porque confiar na camada de cima e
        # exatamente o tipo de aposta que levanta no meio do farm.
        return (
            "Nao entendi. Use assim: `.pegou 18:00 Korzis` "
            "(ou `.pegou 24/08 18:00 Korzis` para um dia antigo)."
        )

    evento = next((e for e in eventos if eh_solo_boss(e.nome)), None)
    if evento is None:
        return (
            "Nao achei o Solo Boss na agenda do config.toml — "
            "nao da para registrar o loot."
        )
    nome_do_evento = evento.nome

    desejado = momento_desejado(pedido, agora)
    if desejado is None:
        # UMA mensagem so para data no futuro e para data que nao existe: o
        # texto e verdadeiro nos dois casos, e inventar um segundo canal de
        # erro para distingui-los nao ajudaria ninguem a digitar melhor.
        return (
            "Essa data nao aponta para nenhum momento que ja passou — "
            f"o `.pegou` so registra {nome_do_evento} que ja aconteceu."
        )

    alvo = encaixar_na_agenda(desejado, eventos, agora)
    if alvo is None:
        horarios = horarios_do_solo_boss(eventos)
        lista = ", ".join(horarios) if horarios else "nenhum"
        return (
            f"Nao achei nenhum {nome_do_evento} perto das "
            f"{pedido.hora:02d}:{pedido.minuto:02d}. "
            f"Os horarios sao: {lista}."
        )

    correcao = registro.atribuir(pedido.nick, alvo)
    momento = descrever_momento(alvo, agora)

    if correcao.estado == "criado":
        return (
            f"Registrei: o loot do {nome_do_evento} de {momento} e do "
            f"{exibir(correcao.novo)}. Ninguem tinha registrado esse boss."
        )

    if correcao.estado == "mesmo_dono":
        return (
            f"O loot do {nome_do_evento} de {momento} JA era do "
            f"{exibir(correcao.novo)} — nada mudou."
        )

    if correcao.estado == "falhou":
        if correcao.anterior:
            return (
                f"Nao consegui gravar o loot do {nome_do_evento} de "
                f"{momento} — ele continua do {exibir(correcao.anterior)}, "
                f"nao do {exibir(correcao.novo)}."
            )
        return (
            f"Nao consegui gravar o loot do {nome_do_evento} de {momento} — "
            "nao foi registrado nada."
        )

    return (
        f"O loot do {nome_do_evento} de {momento} passou do "
        f"{exibir(correcao.anterior)} para o {exibir(correcao.novo)}."
    )
