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
    apelido_do_evento,
    chave_da_ocorrencia,
    ocorrencias_do_dia,
    proxima_ocorrencia,
)
from .loot import apelido, dono_do_loot, exibir, sugerir_a_vez


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
    """A proxima ocorrencia com chamada, ESTRITAMENTE no futuro. None se nao ha.

    E a `proxima_ocorrencia` da agenda, filtrada pelos eventos com chamada. Um
    `.join` fora da janela de chamada e ACEITO de proposito (D-07): quem lembrou
    tres horas antes nao pode ser punido por lembrar cedo. E por isso mesmo a
    resposta cita sempre o horario — e ela que impede a pessoa de achar que
    entrou no boss errado.

    ESTRITAMENTE NO FUTURO, e isso e o que o `.leave` precisa. A lista que
    acabou de fechar e historico (D-14): um `.leave` as 20:01 nao pode tirar
    ninguem da lista das 20:00, que ja foi ao grupo e ja alimentou a sugestao
    da vez do loot. Quem quer a tolerancia e o `.join` — ver
    `ocorrencia_do_join`, logo abaixo, e a razao pela qual as duas perguntas
    tem funcoes separadas em vez de um parametro booleano.
    """
    return proxima_ocorrencia(agora, _com_chamada(eventos))


def ocorrencia_do_join(
    agora: datetime, eventos: list[EventoAgendado]
) -> tuple[str, datetime] | None:
    """A ocorrencia sobre a qual um `.join` de agora fala. None se nao ha.

    A DIFERENCA PARA `ocorrencia_da_chamada` E A TOLERANCIA, E ELA E O CONSERTO
    DE UM BUG MEDIDO.

    A ponte Baileys entrega mensagem com atraso. Um `.join` que saiu do celular
    as 19:59:58 chega no tick de 20:00:03 — e, pela regra estrita, cai no boss
    das 22:00: a pessoa acha que confirmou o boss que esta COMECANDO e o
    scanner a poe no de duas horas depois. O eco privado cita o horario (D-07),
    entao ela ate consegue perceber, mas so lendo com atencao um texto que
    parece uma confirmacao.

    Dentro da tolerancia, um `.join` fala do boss que acabou de nascer. A
    ordem "ler antes de marcar" de `fechar_ocorrencias` e o que faz isso valer
    de ponta a ponta: com a lista ainda vazia as 20:00:00 nenhum marcador foi
    queimado, entao o tick de 20:00:04 encontra a pessoa e ANUNCIA.

    Reusa `ocorrencias_na_janela`, a mesma que o fechamento usa, e por isso as
    duas nunca podem discordar sobre o que e "o boss de agora". A mais recente
    quando ha duas vivas, pela mesma razao do `ocorrencia_recem_fechada`.
    """
    recem = ocorrencias_na_janela(agora, eventos)
    if recem:
        return recem[-1]
    return ocorrencia_da_chamada(agora, eventos)


def ocorrencias_na_janela(
    agora: datetime, eventos: list[EventoAgendado]
) -> list[tuple[str, datetime]]:
    """As ocorrencias com chamada que comecaram ha pouco. Vazia fora da janela.

    DECIDE PELO TEMPO, E NAO PELO MARCADOR `fechado_` EM DISCO — e essa e a
    predicao certa, nao uma aproximacao. Amarrar a decisao ao marcador faria
    ela depender de o tick ter rodado, que e detalhe de implementacao que quem
    digita nao enxerga. Caso concreto: scanner fora do ar as 20:00 e subindo as
    20:03; um `.leave` as 20:02 nao seria recusado, cairia na ocorrencia das
    22:00 e responderia "voce nao estava na lista" — confuso e errado. A janela
    responde certo nos dois estados.

    Ontem entra na varredura pelo mesmo motivo que faz `silencio_ativo` varrer:
    um boss as 23:50 ainda esta recem-comecado as 00:02 do dia seguinte.

    Reusa `TOLERANCIA_MINUTOS` em vez de criar constante nova porque e a MESMA
    propriedade do laco respondendo a mesma pergunta — quanto tempo depois do
    alvo isto ainda e "agora".

    Devolve LISTA e nao um so, porque os dois leitores querem coisas
    diferentes: o `.leave` quer a mais recente (uma recusa), e o fechamento
    quer TODAS (um scanner que voltou do ar as 20:04 pode ter duas listas por
    anunciar se dois eventos com chamada nasceram juntos). Ordenada pelo alvo
    para o fechamento sair sempre na mesma ordem no teste.
    """
    tolerancia = timedelta(minutes=TOLERANCIA_MINUTOS)
    achados: list[tuple[str, datetime]] = []
    hoje = agora.date()

    for deslocamento in (-1, 0):
        dia = hoje + timedelta(days=deslocamento)
        for evento in _com_chamada(eventos):
            for alvo in ocorrencias_do_dia(evento, dia):
                if alvo <= agora < alvo + tolerancia:
                    achados.append((evento.nome, alvo))
    return sorted(achados, key=lambda par: par[1])


def ocorrencia_recem_fechada(
    agora: datetime, eventos: list[EventoAgendado]
) -> tuple[str, datetime] | None:
    """A ocorrencia que acabou de comecar, se houver uma. None fora da janela.

    A MAIS RECENTE entre as da janela: com duas ocorrencias vivas ao mesmo
    tempo, quem manda `.leave` esta falando da que acabou de nascer.
    """
    achados = ocorrencias_na_janela(agora, eventos)
    return achados[-1] if achados else None


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


def _evento_com_lista_desligada(
    eventos: list[EventoAgendado], desligadas: frozenset[str] | set[str]
) -> str | None:
    """O nome do primeiro evento COM CHAMADA cuja lista foi desligada, ou None.

    Sobre `_com_chamada`, e nao sobre `eventos`: um marcador gravado para um
    evento sem `chamar_minutos_antes` nao desligaria lista nenhuma, e recusar
    um `/entrar` por causa dele seria calar por um estado que nao existe.

    Devolve o NOME e nao o apelido, porque quem chama vai escrever a resposta —
    a mesma disciplina do D-10, com o slug parando na fronteira do disco.
    """
    for evento in _com_chamada(eventos):
        if apelido_do_evento(evento.nome) in desligadas:
            return evento.nome
    return None


def _lista_desligada(nome: str) -> RespostaDePresenca:
    """A recusa do `/entrar` e do `/sair` com a lista desligada.

    UM TEXTO SO PARA OS DOIS COMANDOS, e por isso ele fala do ESTADO da lista
    em vez do que a pessoa tentou fazer: "voce nao entrou" leria errado para
    quem mandou `/sair`, e vice-versa.

    NAO PROMETE NADA SOBRE O LEMBRETE DE 10 MINUTOS, de proposito. Quem sabe se
    o boss tambem esta calado e o responder do dono, que le as duas chaves;
    esta superficie nao tem esse fato e por isso nao faz a promessa.

    `grupo=None`: a recusa e assunto de quem digitou. Ecoar no grupo repetiria
    a mesma informacao a cada dedo nervoso de 4 a 8 pessoas.
    """
    return RespostaDePresenca(
        privado=(
            f"A lista de presenca do {nome} esta desligada: ninguem entra e "
            f"ninguem sai enquanto estiver assim. Quem religa e o dono, com "
            f"/ativarlista."
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

    A ocorrencia sai de `ocorrencia_do_join`, e nao de `ocorrencia_da_chamada`:
    dentro da tolerancia um `.join` atrasado pela ponte fala do boss que acabou
    de nascer, e nao do de daqui a duas horas. Ver a docstring de la.
    """
    # PREPENDIDO, E A POSICAO E A DECISAO. Um guarda posto depois do
    # `if not nick` deixaria o DONO sem bloco `[[membro]]` recebendo "Adicione
    # um bloco [[membro]]..." com a lista desligada — uma mensagem que manda a
    # pessoa consertar um arquivo que nao esta quebrado. Aqui em cima, toda
    # entrada responde a verdade, e o caminho com a lista LIGADA fica byte a
    # byte o de hoje (o helper devolve None e nada abaixo muda de lugar).
    #
    # LIDO DO `registro` POR DENTRO, e nao por parametro: esta funcao ja recebe
    # o `RegistroEmDisco` e ja toca disco na linha seguinte. Um parametro aqui
    # nao compraria pureza nenhuma — compraria mais dois pontos de edicao no
    # `__main__.py` e no `sessao.py`.
    desligada = _evento_com_lista_desligada(eventos, registro.listas_desligadas())
    if desligada is not None:
        return _lista_desligada(desligada)

    if not nick:
        return _sem_nick()

    proximo = ocorrencia_do_join(agora, eventos)
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
            f"deu erro de disco aqui. Mande /entrar de novo."
        )
    )


def responder_leave(
    registro: RegistroEmDisco,
    eventos: list[EventoAgendado],
    agora: datetime,
    nick: str | None,
) -> RespostaDePresenca:
    """Obedece o `.leave`: tira da lista, ou recusa se o boss ja comecou.

    A SAIDA E TENTADA PRIMEIRO, E A RECUSA SO VEM DEPOIS. A ordem inversa —
    consultar o fechamento antes de qualquer coisa — deixava o `.leave`
    QUEBRADO durante os 5 minutos de tolerancia de CADA ocorrencia. `.leave`
    nao tem argumento, entao quem estava na lista que acabou de fechar nao
    conseguia sair da lista SEGUINTE, e ainda recebia uma recusa citando uma
    ocorrencia que ele nem mencionou. Com doze ocorrencias por dia isso e uma
    hora inteira por dia de comando quebrado.

    D-14 CONTINUA VALENDO, e e por construcao: nada aqui toca na chave da
    ocorrencia fechada. `registro.sair` opera SEMPRE sobre
    `ocorrencia_da_chamada`, que e estritamente futura — a lista que fechou e
    historico e continua intocavel. A recusa nao era a garantia; ela era so a
    mensagem. A garantia e a chave.

    A recusa e para quem ESTAVA na lista que fechou E nao tinha nada a tirar
    adiante — e so ai ela responde a pergunta que a pessoa realmente fez. Quem
    nao entrou no boss das 20:00 nao tem historico para reabrir as 20:01: o
    `.leave` dele fala do boss das 22:00.

    A ASSIMETRIA COM O `responder_join` E PROPOSITAL, e e a mesma do par
    `responder_designacao`/`responder_cancelamento` do loot: a saida so anuncia
    no grupo quando havia mesmo alguem para tirar. Um `.leave` de quem nunca
    joinou nao e erro — e quase sempre engano de quem achou que tinha entrado —
    e por isso responde, no privado, exatamente isso.
    """
    # PREPENDIDO, E A POSICAO E A DECISAO. Um guarda posto depois do
    # `if not nick` deixaria o DONO sem bloco `[[membro]]` recebendo "Adicione
    # um bloco [[membro]]..." com a lista desligada — uma mensagem que manda a
    # pessoa consertar um arquivo que nao esta quebrado. Aqui em cima, toda
    # entrada responde a verdade, e o caminho com a lista LIGADA fica byte a
    # byte o de hoje (o helper devolve None e nada abaixo muda de lugar).
    #
    # LIDO DO `registro` POR DENTRO, e nao por parametro: esta funcao ja recebe
    # o `RegistroEmDisco` e ja toca disco na linha seguinte. Um parametro aqui
    # nao compraria pureza nenhuma — compraria mais dois pontos de edicao no
    # `__main__.py` e no `sessao.py`.
    desligada = _evento_com_lista_desligada(eventos, registro.listas_desligadas())
    if desligada is not None:
        return _lista_desligada(desligada)

    if not nick:
        return _sem_nick()

    slug = apelido(nick)

    proximo = ocorrencia_da_chamada(agora, eventos)
    if proximo is not None:
        nome, alvo = proximo
        hora = _hora(alvo)
        if registro.sair(chave_da_ocorrencia(nome, alvo), slug):
            return RespostaDePresenca(
                privado=f"Pronto. Voce saiu da lista do {nome} das {hora}.",
                grupo=f"{exibir(nick)} saiu da lista do {nome} das {hora}.",
            )

    # So agora a recusa de historico faz sentido: nao havia nada a tirar
    # adiante, entao a pessoa esta MESMO falando da lista que fechou.
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

    if proximo is None:
        return _sem_chamada_na_agenda()

    nome, alvo = proximo
    return RespostaDePresenca(
        privado=f"Voce nao estava na lista do {nome} das {_hora(alvo)}."
    )


@dataclass(frozen=True)
class Fechamento:
    """A lista de UMA ocorrencia, no instante em que ela virou historico.

    ESTRUTURADO, E NUNCA O TEXTO — pelo mesmo motivo que `Aviso.chave` e
    estruturada e que `ResultadoDoTick` existe: o teste afirma estrutura, e a
    redacao muda toda semana. Um `fechar_ocorrencias` que devolvesse string
    obrigaria todo teste desta fase a casar frase, e a primeira melhoria de
    redacao quebraria dez testes que nao falam de redacao nenhuma.

    `nicks` guarda SLUGS, que e o que o disco tem. A grafia do `config.toml`
    entra so na hora de escrever a frase, por `texto_de_fechamento(nomes=...)`
    — a mesma separacao entre o que se guarda e o que se mostra que `apelido`
    e `exibir` ja fazem no loot. Ordenado para o teste poder afirmar.
    """

    evento: str
    alvo: datetime
    nicks: tuple[str, ...]


def fechar_ocorrencias(
    registro: RegistroEmDisco,
    eventos: list[EventoAgendado],
    agora: datetime,
) -> list[Fechamento]:
    """As listas que ESTE processo fechou agora. Vazia quando nao ha o que dizer.

    LE OS PRESENTES ANTES DE MARCAR, E A ORDEM E A DECISAO CENTRAL DESTA
    FUNCAO. O `RegistroEmDisco.fechar` e um `marcar`, e a docstring do `marcar`
    diz que a decisao de despachar tem que ser ELE, nunca uma checagem
    anterior. Isso continua verdade aqui — mas D-12 acrescenta uma segunda
    regra: zero confirmacoes produz ZERO mensagem.

    A JUSTIFICATIVA E ESSA SEGUNDA REGRA, E SO ELA: LISTA VAZIA NAO PODE
    QUEIMAR O MARCADOR. Marcando primeiro, o tick de 20:00:00 com a lista vazia
    fecharia a ocorrencia e calaria — e qualquer `.join` que chegasse dentro
    dos 5 minutos seguintes encontraria a ocorrencia ja fechada e nunca viraria
    mensagem, porque o marcador teria sido queimado por um tick que nao falou
    nada. Lendo antes, um tick de lista vazia simplesmente nao toca em disco, e
    o primeiro tick que enxergar alguem fecha e anuncia.

    (Esta docstring ja defendeu a ordem com um cenario que NAO existia: o
    `.join` de 20:00:03 caindo na ocorrencia das 20:00. Ate o conserto do
    WR-01 ele caia na das 22:00, porque `responder_join` resolvia por
    `proxima_ocorrencia`, que exige `alvo > agora` estritamente. Hoje o cenario
    e real — `ocorrencia_do_join` tem a mesma tolerancia que esta funcao — mas
    ele e a CONSEQUENCIA de ler antes de marcar, e nao a razao dela. A razao
    continua sendo o marcador que a lista vazia nao queima.)

    A GARANTIA CONTRA DUPLICATA NAO SE PERDE. O `fechar` continua sendo a linha
    que decide quem fala: com as duas instancias do usuario (Yazalaque e
    Faerlina) sobre a mesma pasta, o `O_CREAT|O_EXCL` deixa exatamente uma
    criar o marcador, e so ela produz o `Fechamento`. A que perdeu devolve
    lista vazia e cala.

    NAO PASSA POR `avisos_devidos`, de proposito (D-12). O Solo Boss do usuario
    tem `avisar_no_horario = false` — foram as doze ocorrencias diarias que o
    fizeram desligar o aviso de AGORA — e amarrar o fechamento ao aviso
    obrigaria ele a religar justamente o volume que rejeitou. O unico criterio
    e `chamar_minutos_antes > 0`, o mesmo que criou a lista.
    """
    fechados: list[Fechamento] = []
    # UMA leitura de disco para o tick inteiro, e ela vem ANTES do laco: sao
    # ate duas ocorrencias por tick e reler por iteracao so daria chance de as
    # duas discordarem entre si.
    desligadas = registro.listas_desligadas()
    for nome, alvo in ocorrencias_na_janela(agora, eventos):
        if apelido_do_evento(nome) in desligadas:
            # O `continue` VEM ANTES DO `fechar`, e a posicao e a decisao —
            # exatamente o mesmo argumento que esta docstring ja faz para a
            # lista vazia: UM TICK QUE NAO FALA NAO PODE QUEIMAR O MARCADOR.
            # Queimando-o aqui, o usuario que religasse a lista dentro dos 5
            # minutos de tolerancia encontraria a ocorrencia ja fechada, e
            # aquela lista ficaria muda PARA SEMPRE, sem nada explicando por
            # que. Pulando antes, religar dentro da janela ainda fecha.
            continue
        chave = chave_da_ocorrencia(nome, alvo)
        presentes = registro.presentes(chave)
        if not presentes:
            continue
        if not registro.fechar(chave):
            continue
        # RELER DEPOIS DE VENCER. A leitura de tres linhas acima decide SE ha o
        # que anunciar; ela nao pode decidir O QUE se anuncia. Com as duas
        # instancias do usuario sobre a mesma pasta, um `.join` gravado entre
        # aquela leitura e o `fechar` existe em disco e nao apareceria na
        # mensagem — e nunca apareceria, porque o marcador ja foi queimado. A
        # janela e de microssegundos e o efeito e permanente: a pessoa esta na
        # lista em disco e ausente da lista que a party leu.
        #
        # O `or presentes` guarda o caso em que a releitura falha (disco
        # travando bem nesse instante): anunciar a lista de antes e melhor que
        # anunciar uma lista vazia num marcador ja queimado.
        presentes = registro.presentes(chave) or presentes
        fechados.append(
            Fechamento(evento=nome, alvo=alvo, nicks=tuple(sorted(presentes)))
        )
    return fechados


def texto_de_fechamento(
    fechamento: Fechamento,
    nomes: dict[str, str] | None = None,
    sugestao: tuple[str, int] | None = None,
) -> str:
    """A lista fechada como a party a le no grupo.

    O `nomes` e o mapa slug -> nick de `nomes_dos_membros`, e existe por D-10:
    o disco guarda `tiomad` e a party reconhece `TioMad`. Quem nao estiver no
    mapa — um party-mate sem bloco `[[membro]]` — nao pode SUMIR da lista, e
    por isso cai em `exibir(slug)` em vez de ser filtrado.

    `sugestao` e o par `(slug, total_de_loots)` que `loot.sugerir_a_vez`
    devolve, e QUEM O PREENCHE E O CHAMADOR — `sessao._processar_agenda` e
    `__main__._fechar_listas_de_presenca`. Ele nasceu declarado e ignorado no
    plano 10-04 (precedente literal: `EventoAgendado.silenciar_minutos`, da
    Fase 6) e o plano 10-05 o ligou.

    A funcao so FORMATA — quem decide SE ha sugestao e o chamador, e neste
    modulo o chamador e `fechar_e_narrar`. Mesmo idioma de
    `texto_do_aviso(aviso, loot)`, em que a agenda nao conhece designacao
    nenhuma: aqui chega um par de valores, nunca um registro.

    `None` produz a mensagem EXATA do plano 10-04. Nao e tolerancia
    decorativa: e o caso de quem roda com `loot=None`, e perder a lista
    fechada — que e o desfecho da chamada feita 1h50 antes — por falta de uma
    estatistica opcional seria trocar a mensagem que importa pela que enfeita.
    """
    mapa = nomes or {}
    lista = ", ".join(mapa.get(slug, exibir(slug)) for slug in fechamento.nicks)
    texto = (
        f"{fechamento.evento} das {_hora(fechamento.alvo)} comecando. "
        f"Confirmaram: {lista}."
    )
    if sugestao is not None:
        slug, total = sugestao
        # "1 loots" e "0 loots" leem como bug, e esta e a linha que a party vai
        # discutir em voz alta — ela nao pode ser a que parece quebrada.
        if total == 0:
            quanto = "ainda nenhum"
        else:
            quanto = f"{total} loot" + ("" if total == 1 else "s")
        texto += f" Sugestao de loot: {mapa.get(slug, exibir(slug))} ({quanto})."
    return texto


def fechar_e_narrar(
    registro: RegistroEmDisco,
    eventos: list[EventoAgendado],
    agora: datetime,
    membros: Iterable[object] = (),
    loot: object | None = None,
) -> list[tuple[Fechamento, str]]:
    """Fecha as listas que venceram e escreve o que a party le. UMA implementacao.

    EXISTE PORQUE ESTA SEQUENCIA ESTAVA DUPLICADA LITERALMENTE (WR-08), entre
    `sessao.Sessao._processar_agenda` (o laco principal) e
    `__main__._fechar_listas_de_presenca` (o `--so-agenda`) — os mesmos cinco
    passos, com ate os comentarios repetidos. As duas copias escrevem no MESMO
    `.agenda/` e falam no MESMO grupo, entao qualquer conserto precisava ser
    aplicado duas vezes; aplicado uma so, os dois modos do scanner passariam a
    anunciar coisas diferentes sobre o mesmo boss. E o usuario deste projeto e
    exatamente quem roda os dois modos.

    O QUE FICA COM O CHAMADOR e o que e mesmo dele: o log, a moldura, o
    despacho e o `ResultadoDoTick`. Aqui mora so a decisao e o texto.

    A SUGESTAO E CALADA QUANDO ESTE BOSS JA TEM DONO (CR-02). Se `.loot-<nick>`
    ja foi consumido para esta ocorrencia, a mensagem de fechamento nao tem
    opiniao nenhuma a dar sobre ele: dez minutos antes o aviso de antecedencia
    do MESMO boss saiu no MESMO grupo dizendo "Loot: Kaus", e uma sugestao
    calculada DEPOIS do consumo aponta necessariamente para outra pessoa —
    porque o Kaus acabou de ganhar um loot no placar. O bot se desmentia no
    pior momento, e quem obedecesse a sugestao errada gravaria `.pegou` no
    `.loot/`, que nao tem poda nem backup.

    Calar e mais honesto que explicar. A alternativa era escrever "sugestao
    para o proximo boss", e ai a mesma frase teria dois significados conforme o
    estado do disco — de quem e a vez NESTE boss quando nao ha designacao
    consumida, e no PROXIMO quando ha. Uma frase que muda de sentido sem mudar
    de forma e pior que frase nenhuma.

    D-13 CONTINUA INTOCADO: a lista SUGERE e nunca manda. Calar a sugestao nao
    bloqueia coisa alguma — `.loot-<nick>` de quem nao joinou continua avisando
    e OBEDECENDO, em `responder_designacao`.

    `loot` entra tipado como `object | None` pela mesma razao de
    `nomes_dos_membros`: a assinatura pede a FORMA, e o `None` e o caminho de
    quem roda sem registro de loot — a lista fecha igual, so sem sugestao.
    """
    fechados = fechar_ocorrencias(registro, eventos, agora)
    if not fechados:
        return []

    nomes = nomes_dos_membros(membros)
    narrados: list[tuple[Fechamento, str]] = []
    for fechamento in fechados:
        # A LEITURA DA LISTA ACONTECE AQUI, NA BORDA: `loot.py` recebe os
        # presentes por parametro e nunca importa `presenca` — a direcao e
        # `presenca -> loot -> agenda` e um ciclo mataria os dois modulos.
        sugestao = None
        if loot is not None and dono_do_loot(loot, fechamento.alvo) is None:
            sugestao = sugerir_a_vez(loot, frozenset(fechamento.nicks))
        narrados.append(
            (fechamento, texto_de_fechamento(fechamento, nomes, sugestao))
        )
    return narrados


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
