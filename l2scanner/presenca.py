"""A lista de presenca do Solo Boss: quem vai, quem desistiu, e o que o bot diz.

O scanner chama no grupo 1h50 antes de cada ocorrencia (Fase 10, plano 10-02) e
cada membro responde `.join` no privado do bot. Este modulo e a DECISAO desse
`.join`: em que lista a pessoa entra, o que ela le de volta, e o que a party le.

TRES DECISOES DE DESENHO QUE NAO SAO DETALHE:

1. **A lista mora no `.agenda/`, e nao numa pasta propria.** O oposto do
   `.loot/`, e de proposito: a lista de presenca EXISTE PARA MORRER. Ela
   responde "quem vai no boss das 20:00 de hoje" e essa pergunta perde o
   sentido as 20:05. A poda de 3 dias, que seria fatal para a estatistica de
   loot ("quantos o J4guar pegou" e pergunta sobre meses), e exatamente o que
   esta lista quer. E a parte dificil — a atomicidade `O_CREAT|O_EXCL` entre as
   duas instancias do usuario — ja estava escrita no `RegistroEmDisco`.

2. **Este modulo NAO importa `comandos` nem `sessao`, e `loot` NUNCA importara
   este.** A direcao e `presenca -> loot -> agenda`, fixa. Um ciclo aqui nao
   degrada nada: mata os dois modulos com `ImportError` no arranque. E a mesma
   restricao que o fim da docstring de `loot.py` ja carrega desde a Fase 8,
   agora tambem afirmada por `ast.parse` em `tests/test_presenca.py` — busca
   textual nao serviria, porque este paragrafo escreve os nomes proibidos.
   Quem precisar da lista do lado do loot (plano 10-05) a recebe por PARAMETRO,
   lida na borda.

3. **O tempo entra por parametro, sem `datetime.now()`.** Mesma disciplina da
   agenda e do loot, e e o que permite testar em milissegundos o caso que so
   acontece uma vez a cada duas horas: o `.leave` as 20:01, com o boss das
   20:00 recem-comecado, que tem que ser RECUSADO.

E UMA DECISAO DE PRODUTO QUE VIROU TIPO: a resposta e um PAR. Ate esta fase o
`__main__.py` despachava o MESMO texto para o privado e para o grupo; a lista
de presenca precisa de redacoes diferentes, porque servem a leitores
diferentes. Ver `RespostaDePresenca`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from .agenda import (
    TOLERANCIA_MINUTOS,
    EventoAgendado,
    RegistroEmDisco,
    chave_da_ocorrencia,
    ocorrencias_do_dia,
    proxima_ocorrencia,
)
from .loot import apelido, exibir


@dataclass(frozen=True)
class RespostaDePresenca:
    """O que vai para o privado de quem digitou, e o que vai para o grupo.

    DUAS REDACOES, NUNCA UMA. Elas servem a leitores diferentes:

    - no PRIVADO, o que a pessoa precisa saber e que CHEGOU. Sem esse eco, um
      `.join` recusado por autorizacao e um `.join` que funcionou sao
      indistinguiveis para quem digitou — os dois produzem silencio na tela
      dela.
    - no GRUPO, o que importa e o NICK e o HORARIO. Ninguem na party quer ler
      "anotado, voce esta na lista"; eles querem saber quem vai.

    `grupo is None` e o jeito ESTRUTURADO de dizer "isto nao merece mensagem no
    grupo" — e nao uma string vazia, que o despachante enviaria assim mesmo,
    virando uma bolha em branco no WhatsApp. `None` e o default porque o
    silencio no grupo tem que ser o caminho facil: o grupo e o recurso caro
    desta fase (doze ocorrencias por dia ja foram a razao de o usuario desligar
    `avisar_no_horario` no Solo Boss).
    """

    privado: str
    grupo: str | None = None


def _com_chamada(eventos: list[EventoAgendado]) -> list[EventoAgendado]:
    """Os eventos que pediram chamada — D-03: mecanismo generico, config especifica.

    `chamar_minutos_antes > 0` e o unico criterio. Nada neste modulo escreve o
    nome de um evento: quem decide que o Solo Boss tem lista de presenca e a
    linha `chamar_minutos_antes = 110` do `config.toml`, e ligar TvT ou Prime
    um dia nao custa uma linha de codigo.
    """
    return [e for e in eventos if e.chamar_minutos_antes > 0]


def ocorrencia_da_chamada(
    agora: datetime, eventos: list[EventoAgendado]
) -> tuple[str, datetime] | None:
    """A ocorrencia sobre a qual um `.join` de agora fala. None se nao ha.

    E a `proxima_ocorrencia` da agenda, filtrada pelos eventos com chamada. Um
    `.join` fora da janela de chamada e ACEITO de proposito (D-07): quem lembrou
    tres horas antes nao pode ser punido por lembrar cedo. E por isso mesmo a
    resposta cita sempre o horario — e ela que impede a pessoa de achar que
    entrou no boss errado.
    """
    return proxima_ocorrencia(agora, _com_chamada(eventos))


def ocorrencia_recem_fechada(
    agora: datetime, eventos: list[EventoAgendado]
) -> tuple[str, datetime] | None:
    """A ocorrencia que acabou de comecar, se houver uma. None fora da janela.

    DECIDE PELO TEMPO, E NAO PELO MARCADOR `fechado_` EM DISCO — e essa e a
    predicao certa, nao uma aproximacao. Amarrar a recusa ao marcador faria a
    resposta depender de o tick ter rodado, que e detalhe de implementacao que
    quem digita nao enxerga. Caso concreto: scanner fora do ar as 20:00 e
    subindo as 20:03; um `.leave` as 20:02 nao seria recusado, cairia na
    ocorrencia das 22:00 e responderia "voce nao estava na lista" — confuso e
    errado. A janela recusa certo nos dois estados.

    Ontem entra na varredura pelo mesmo motivo que faz `silencio_ativo` varrer:
    um boss as 23:50 ainda esta recem-comecado as 00:02 do dia seguinte.

    Reusa `TOLERANCIA_MINUTOS` em vez de criar constante nova porque e a MESMA
    propriedade do laco respondendo a mesma pergunta — quanto tempo depois do
    alvo isto ainda e "agora".
    """
    tolerancia = timedelta(minutes=TOLERANCIA_MINUTOS)
    achado: tuple[str, datetime] | None = None
    hoje = agora.date()

    for deslocamento in (-1, 0):
        dia = hoje + timedelta(days=deslocamento)
        for evento in _com_chamada(eventos):
            for alvo in ocorrencias_do_dia(evento, dia):
                if not (alvo <= agora < alvo + tolerancia):
                    continue
                if achado is None or alvo > achado[1]:
                    achado = (evento.nome, alvo)
    return achado


def _hora(alvo: datetime) -> str:
    return f"{alvo.hour:02d}:{alvo.minute:02d}"


def _sem_nick() -> RespostaDePresenca:
    """Quem mandou o comando nao tem nick no mapa `[[membro]]`.

    Acontece com o DONO que nao se declarou membro: o nivel de dono alcanca
    todo comando (plano 10-01), entao o pedido chega — mas sem nick nao ha o
    que por na lista, e inventar um a partir do nome do contato do Chatwoot e
    exatamente o que o D-10 proibe. A resposta aponta onde consertar, porque
    "nao consegui" sem endereco vira uma pergunta no grupo.
    """
    return RespostaDePresenca(
        privado=(
            "Nao sei que nick por na lista para o seu telefone. "
            "Adicione um bloco [[membro]] com nick e telefone no config.toml."
        )
    )


def _sem_chamada_na_agenda() -> RespostaDePresenca:
    """Nenhum evento da agenda pediu chamada.

    Nomeia o CAMPO, e nao o evento: e o campo que o usuario tem que escrever, e
    citar "Solo Boss" aqui seria o modulo conhecendo um nome de evento.
    """
    return RespostaDePresenca(
        privado=(
            "Nenhum evento da agenda tem lista de presenca. "
            "Para ligar, ponha chamar_minutos_antes no [[evento]] do config.toml."
        )
    )


def responder_join(
    registro: RegistroEmDisco,
    eventos: list[EventoAgendado],
    agora: datetime,
    nick: str | None,
) -> RespostaDePresenca:
    """Obedece o `.join`: poe na lista da proxima ocorrencia e confirma.

    O `nick` e o `MensagemDeComando.nick` do plano 10-01, vindo do mapa
    `[[membro]]` — NUNCA o `sender.name` do Chatwoot (D-10). O nome do contato
    do WhatsApp nao e o nick do jogo, e a lista que a party le tem que trazer o
    nome que a party reconhece.

    UM RAMO POR ESTADO DO TRI-ESTADO, e os tres sao decisoes de produto:

    - `criado` — entrou agora: confirma no privado E no grupo.
    - `ja_existia` — ja estava: responde so no privado (D-08). Repetir no grupo
      transformaria um dedo nervoso em spam para 4-8 pessoas.
    - `falhou` — o disco nao gravou: pede para repetir, e CALA no grupo. Uma
      confirmacao de entrada que o disco perdeu faria a lista fechar sem essa
      pessoa, e ela chegaria no boss contando com uma vaga que nao existe.

    Todas as tres citam o horario do alvo (D-07). "Voce ja esta na lista", sem
    horario, e ambiguo entre o boss das 20:00 e o das 22:00 — e as 19:59 essa
    ambiguidade custa uma pessoa.
    """
    if not nick:
        return _sem_nick()

    proximo = ocorrencia_da_chamada(agora, eventos)
    if proximo is None:
        return _sem_chamada_na_agenda()

    nome, alvo = proximo
    hora = _hora(alvo)
    estado = registro.entrar(chave_da_ocorrencia(nome, alvo), apelido(nick))

    if estado == "criado":
        return RespostaDePresenca(
            privado=f"Anotado. Voce esta na lista do {nome} das {hora}.",
            grupo=f"{exibir(nick)} vai no {nome} das {hora}.",
        )
    if estado == "ja_existia":
        return RespostaDePresenca(
            privado=(
                f"Voce ja esta na lista do {nome} das {hora}. "
                f"Nao precisa mandar de novo."
            )
        )
    return RespostaDePresenca(
        privado=(
            f"Nao consegui gravar a sua entrada no {nome} das {hora}: "
            f"deu erro de disco aqui. Mande .join de novo."
        )
    )


def responder_leave(
    registro: RegistroEmDisco,
    eventos: list[EventoAgendado],
    agora: datetime,
    nick: str | None,
) -> RespostaDePresenca:
    """Obedece o `.leave`: tira da lista, ou recusa se o boss ja comecou.

    A CONSULTA AO FECHAMENTO VEM PRIMEIRO (D-14). Uma lista fechada e
    historico: ela ja alimentou a sugestao da vez do loot, e reabri-la faz duas
    pessoas lembrarem coisas diferentes do mesmo boss — a categoria de bug que
    o `.corrigir` do `loot.py` ja documenta como cara.

    A recusa e para quem ESTAVA na lista que fechou, e so. Quem nao entrou no
    boss das 20:00 nao tem historico para reabrir as 20:01: o `.leave` dele
    fala do boss das 22:00, e responder "o boss ja comecou" seria uma recusa
    sem causa e sem conserto.

    A ASSIMETRIA COM O `responder_join` E PROPOSITAL, e e a mesma do par
    `responder_designacao`/`responder_cancelamento` do loot: a saida so anuncia
    no grupo quando havia mesmo alguem para tirar. Um `.leave` de quem nunca
    joinou nao e erro — e quase sempre engano de quem achou que tinha entrado —
    e por isso responde, no privado, exatamente isso.
    """
    if not nick:
        return _sem_nick()

    slug = apelido(nick)

    fechada = ocorrencia_recem_fechada(agora, eventos)
    if fechada is not None:
        nome_fechado, alvo_fechado = fechada
        chave_fechada = chave_da_ocorrencia(nome_fechado, alvo_fechado)
        if slug in registro.presentes(chave_fechada):
            return RespostaDePresenca(
                privado=(
                    f"O {nome_fechado} das {_hora(alvo_fechado)} ja comecou e a "
                    f"lista fechou. Nao da mais para sair dela."
                )
            )

    proximo = ocorrencia_da_chamada(agora, eventos)
    if proximo is None:
        return _sem_chamada_na_agenda()

    nome, alvo = proximo
    hora = _hora(alvo)

    if registro.sair(chave_da_ocorrencia(nome, alvo), slug):
        return RespostaDePresenca(
            privado=f"Pronto. Voce saiu da lista do {nome} das {hora}.",
            grupo=f"{exibir(nick)} saiu da lista do {nome} das {hora}.",
        )
    return RespostaDePresenca(
        privado=f"Voce nao estava na lista do {nome} das {hora}."
    )


def nomes_dos_membros(membros: Iterable[object]) -> dict[str, str]:
    """Mapa slug -> nick como esta no `config.toml`.

    Existe para o plano 10-04 exibir a lista fechada com a grafia que o usuario
    escreveu. O disco guarda `j4guar`, `tiomad`; uma lista final assim le como
    bot quebrado — o mesmo motivo pelo qual `loot.exibir` existe.

    Recebe qualquer iteravel de objetos com `.nick`, e nao `list[Membro]`, para
    nao precisar importar `comandos` (ver o item 2 da docstring do modulo). A
    assinatura pede a FORMA, nao o tipo.
    """
    return {apelido(membro.nick): membro.nick for membro in membros}
