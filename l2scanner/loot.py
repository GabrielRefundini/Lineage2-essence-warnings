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
