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
from datetime import datetime
from pathlib import Path

from .agenda import Aviso, EventoAgendado, TipoDeAviso, proxima_ocorrencia

# Prefixos dos arquivos que convivem na pasta — mesma tecnica de namespaces do
# `.agenda/`: a atomicidade e o compartilhamento valem para todos de graca.
_PREFIXO_PEGOU = "pegou_"
_PREFIXO_NICK = "nick_"
_ARQUIVO_PROXIMO = "proximo.json"

# O carimbo de horario no nome do arquivo: `pegou_2026-08-25-1000_j4guar`.
# A identidade do registro E o nome — o arquivo fica vazio de proposito.
_FORMATO_CARIMBO = "%Y-%m-%d-%H%M"


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
    """O que aconteceu numa tentativa de trocar o dono de um loot consumado.

    O `estado` e uma string de quatro valores e nao um booleano pelo MESMO
    motivo do `_criar` logo abaixo: a resposta precisa distinguir "trocou" de
    "ja era dele" de "nao tinha nada para corrigir" de "o disco falhou".
    Colapsar qualquer par desses faria o bot mentir sobre o que acabou de
    acontecer com a estatistica — e um "pronto" depois de uma falha de disco e
    indistinguivel de sucesso para quem esta do outro lado do WhatsApp.

    O `anterior` e o SLUG do dono antigo, minusculo, porque e o nome do
    arquivo que o guarda — nao ha outro registro da caixa original.
    """

    estado: str  # "corrigido" | "mesmo_dono" | "sem_registro" | "falhou"
    anterior: str = ""  # o slug do dono antigo
    novo: str = ""  # o nick novo, como foi digitado
    alvo: datetime | None = None


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
