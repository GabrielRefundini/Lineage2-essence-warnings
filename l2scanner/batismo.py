"""Perguntar quem e a pessoa que o scanner aprendeu, e colar o nome nela.

POR QUE O APELIDO E DERIVADO E NUNCA GUARDADO (D-02)

O usuario nao digita 64 caracteres no celular no meio de um farm, entao a
pergunta cita um apelido curto. Ele e um PREFIXO da propria chave, calculado na
hora. Um mapa `apelido -> chave` em disco seria um segundo estado sobre o
acervo, capaz de discordar dele — e a discordancia apareceria exatamente no
batismo, que e o momento em que errar significa dar o nome de uma pessoa para a
assinatura de outra.

POR QUE UM PREFIXO AMBIGUO E RECUSADO, E NUNCA DESEMPATADO (D-02)

O desempate silencioso e a mentira plausivel de sempre. Duas assinaturas que
comecam igual sao DUAS PESSOAS, e escolher uma delas por ordem alfabetica, por
data de gravacao ou por qualquer outro criterio produz uma mensagem que parece
perfeitamente normal e batiza a pessoa errada. A recusa vem com a lista dos
candidatos e com a saida ("mande mais digitos"), porque uma recusa que so diz
"nao" manda o usuario tentar de novo do mesmo jeito.

POR QUE NAO EXISTE SINTAXE QUE ALCANCE UMA LINHA (D-03)

O usuario esta jogando, e a resposta chega minutos depois. A party se
reorganiza nesse intervalo — ela COMPACTA quando alguem sai —, e resolver por
posicao batizaria a pessoa errada em SILENCIO. A posicao aparece na pergunta
como AJUDA VISUAL ("vi na linha 4"), e nunca como identificador.

A trava nao precisou ser escrita: ela e uma AUSENCIA. `/batizar 3 Mostarda` cai
em "apelido desconhecido", porque "3" e so um prefixo hex que nao casa chave
nenhuma. Nao acrescentar aqui nenhum ramo que aceite numero de linha.

O QUE ESTE MODULO NAO CONHECE

Ele nao importa `visao`, `sessao`, `rastreador`, `calibracao`, `loot`, `agenda`
nem `presenca`. Fala `AcervoDeIdentidades`, `chave_da_assinatura`, `Assinatura`
e stdlib, e so.

A AUSENCIA DE `loot` E DELIBERADA E TEM PRECEDENTE ESCRITO: `acervo.py` ja se
recusou a importar `loot.NICK_VALIDO` porque `loot` importa `agenda`, e
arrastar essa cadeia para um modulo que precisa NAO ter relogio nenhum trocaria
uma linha de regex por um acoplamento que o portao AST depois teria de
raciocinar sobre. Vale igual aqui, e por uma razao propria: este modulo e o
dono do marcador de D-04, e o marcador so e "uma pergunta para sempre" enquanto
nao houver relogio nenhum por perto para transformar isso em "uma pergunta por
dia".

Este modulo nao tem relogio, e a proibicao esta presa pelo portao AST de
`tests/test_presenca.py`, ao lado de `agenda`, `loot`, `presenca`, `bosses`,
`respawn`, `acervo` e `aprendiz`.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from .acervo import NOME_VALIDO, AcervoDeIdentidades, chave_da_assinatura
from .identidade import Assinatura

# Quantos digitos hex da chave a pergunta MOSTRA.
#
# O NUMERO E JUSTIFICADO CONTRA O QUE EXISTE, E NAO ESCOLHIDO NO OLHO:
#
# - o apelido serve para ser DIGITADO no celular no meio de um farm, entao 64
#   nao e uma opcao;
# - a colisao NAO e resolvida em silencio, ela e RECUSADA com a lista dos
#   candidatos (D-02). Ou seja, o comprimento nao troca seguranca por
#   conveniencia: ele troca CONVENIENCIA POR FREQUENCIA DE RECUSA. Um apelido
#   curto demais nunca resolve errado; ele so recusa mais vezes;
# - 6 digitos hex sao 16.7 milhoes de valores. Num acervo da ordem de dezenas
#   de entradas a chance de duas comecarem igual e desprezivel, e mesmo quando
#   acontecer o desfecho e uma recusa que diz o que fazer;
# - MEDIDO NO ACERVO REAL DO USUARIO EM 31/08/2026: as duas entradas anonimas
#   (`15caecfa...` e `f19e3c92...`) diferem no PRIMEIRO digito, entao ate um
#   apelido de 1 digito bastaria hoje. Os seis sao folga escolhida para o dia
#   em que a pasta tiver dezenas, e nao um requisito de agora.
DIGITOS_DO_APELIDO = 6

# O charset do apelido, sempre com `fullmatch`.
#
# SEM PISO INVENTADO, E ISSO E SEGURO. Um prefixo curto demais que hoje e unico
# resolve; no dia em que deixar de ser unico o comando passa a ser RECUSADO, e
# nunca a resolver errado. A degradacao e para o lado seguro, entao um
# comprimento minimo seria uma constante inventada sem nada para proteger.
#
# O que a expressao PRECISA garantir e o charset. Hex e subconjunto de
# `NOME_VALIDO`, e quem separa apelido de nick e a POSICAO do argumento, nunca
# o formato: `interpretar_batismo` le a primeira palavra como apelido e a
# segunda como nick, e por isso `/batizar Mostarda 15caec` (o erro humano mais
# provavel, que e inverter os dois) e recusado em vez de batizar ao contrario.
APELIDO_VALIDO = re.compile(r"[0-9a-f]{1,64}")


def apelido_da_chave(chave: str) -> str:
    """Os primeiros `DIGITOS_DO_APELIDO` digitos da chave. Puro."""
    return chave[:DIGITOS_DO_APELIDO]


def apelidos_para_escolher(chaves: Sequence[str]) -> tuple[str, ...]:
    """Apelidos que o usuario consegue DIGITAR para separar estas chaves.

    Comeca em `DIGITOS_DO_APELIDO` e cresce ate os recortes ficarem distintos.

    Sem isso, duas chaves que compartilhassem os seis primeiros digitos
    produziriam uma recusa listando o MESMO apelido duas vezes — e a saida que
    ela oferece ("mande mais digitos") nao teria como ser seguida, porque o
    texto nao diria quantos. Uma recusa sem saida e um beco.
    """
    tamanho = DIGITOS_DO_APELIDO
    while tamanho < 64:
        recortes = tuple(chave[:tamanho] for chave in chaves)
        if len(set(recortes)) == len(recortes):
            return recortes
        tamanho += 1
    return tuple(chaves)


@dataclass(frozen=True)
class Resolucao:
    """A que chave um apelido aponta, ou por que ele nao aponta a nenhuma.

    Estruturado e nao texto, pelo mesmo motivo que `ResultadoDoTick.despachos`
    e estruturado: o teste afirma ESTRUTURA, e a redacao muda toda vez que
    alguem a melhora.

    `candidatos` guarda as CHAVES INTEIRAS, e nao os apelidos ja recortados: o
    recorte que separa duas chaves ambiguas depende de quantos digitos elas
    compartilham, e essa e uma decisao de REDACAO (ver `apelidos_para_escolher`)
    que nao pode viver dentro do dado.
    """

    chave: str | None
    motivo: str
    candidatos: tuple[str, ...] = field(default=())


def resolver(prefixo: str, chaves: Sequence[str]) -> Resolucao:
    """Qual chave comeca por este prefixo? Funcao PURA. JAMAIS desempata.

    O PINO JA EXISTIA E NAO PRECISOU SER INVENTADO (D-01). A chave e o `sha256`
    do CONTEUDO da mascara, e ela foi desenhada na Fase 1 exatamente para esta
    fase: estavel entre reinicios (a mesma pessoa, recortada de novo, da o
    mesmo nome de arquivo), independente da POSICAO (a party window compacta
    quando alguem sai, e a posicao nunca foi identidade) e independente do NOME
    (batizar cria o irmao `nome_<chave>` e nao toca na assinatura). Nao ha pino
    novo a inventar; existe um pino a USAR.

    Os quatro desfechos:

    - `malformado`: o prefixo nao e hex. `/batizar linha3 Mostarda` cai aqui.
    - `desconhecido`: hex valido que nao casa chave nenhuma. **E AQUI QUE
      `/batizar 3 Mostarda` CAI**, e e por isso que D-03 nao precisa de trava
      especial contra posicao de linha: nao existe sintaxe que alcance uma
      linha, entao "3" e so um prefixo que nao aponta para nada. Nao
      acrescentar um ramo que aceite numero de linha.
    - `ambiguo`: dois ou mais candidatos. RECUSA, com TODOS eles. Um desempate
      por ordem, por data de gravacao ou por qualquer outro criterio produziria
      uma mensagem que parece normal e batiza a pessoa errada.
    - `ok`: exatamente um.
    """
    if not prefixo or not APELIDO_VALIDO.fullmatch(prefixo):
        return Resolucao(chave=None, motivo="malformado")

    achadas = tuple(chave for chave in chaves if chave.startswith(prefixo))
    if not achadas:
        return Resolucao(chave=None, motivo="desconhecido")
    if len(achadas) > 1:
        return Resolucao(chave=None, motivo="ambiguo", candidatos=achadas)
    return Resolucao(chave=achadas[0], motivo="ok")


@dataclass(frozen=True)
class Pendente:
    """Uma assinatura sem nome sobre a qual ainda nao se perguntou.

    `indice` e a linha em base ZERO onde ela foi vista, e e AJUDA VISUAL —
    nunca identificador (D-03). Ele e `None` quando a pergunta vem da varredura
    de arranque, e a ausencia e deliberada: aquela entrada foi aprendida numa
    sessao anterior, possivelmente por outra instancia, e nenhuma posicao de
    AGORA corresponde a ela. Inventar uma seria a primeira mentira do caminho,
    no recurso inteiro que existe para nao mentir.
    """

    chave: str
    indice: int | None = None


def pendentes_do_acervo(acervo: AcervoDeIdentidades) -> list[Pendente]:
    """As entradas anonimas do disco, sem posicao nenhuma.

    NAO CHECA O MARCADOR AQUI. Quem decide e `montar_pergunta`, porque o
    marcador E a decisao (D-04): uma checagem anterior seguida de escrita perde
    a corrida entre as duas instancias do usuario e produz duas perguntas.
    """
    return [Pendente(chave=chave, indice=None) for chave in acervo.anonimas()]


def montar_pergunta(
    acervo: AcervoDeIdentidades, pendentes: Sequence[Pendente]
) -> str | None:
    """O UNICO lugar que MARCA e o UNICO lugar que REDIGE. `None` se nada saiu.

    Os dois gatilhos desta fase — o aprendizado e a varredura de arranque —
    passam por aqui, com o MESMO `O_CREAT|O_EXCL`. D-04 diz "uma pergunta por
    assinatura, para sempre": por ASSINATURA, e nao por evento de aprendizado.
    Dois gatilhos com um marcador so continuam sendo uma pergunta so.

    UMA MENSAGEM PARA N ENTRADAS, E ISSO E DECISAO DE PRODUTO. Duas pessoas
    aprendidas no mesmo tick, ou dez esperando no arranque, produziriam dez
    bolhas no WhatsApp do grupo — e o usuario ja desligou `avisar_no_horario`
    do Solo Boss por volume.

    E ha um segundo ganho, que e o que torna a divida T-02-18 LEGIVEL: quando a
    MESMA pessoa foi aprendida duas vezes (o caso medido na Fase 2, drift acima
    de 43 celulas), as duas entradas aparecem como DUAS LINHAS DA MESMA
    MENSAGEM, uma embaixo da outra — em vez de duas perguntas soltas que o
    usuario le como dois desconhecidos diferentes.

    QUEM MARCOU E QUEM ENTRA NO TEXTO. A ordem importa: marcar depois de
    redigir deixaria uma janela em que a pergunta esta escrita e o marcador
    nao, e as duas instancias mandariam a mesma.
    """
    vencedoras = [
        pendente
        for pendente in pendentes
        if acervo.marcar_pergunta(pendente.chave)
    ]
    if not vencedoras:
        return None

    quantas = len(vencedoras)
    # As duas redacoes por extenso, e nao um sufixo colado.
    #
    # "esta" + "s" da "estas", que nao e o plural de "esta" — e o texto vai
    # para o WhatsApp de quatro a oito pessoas. Uma regra de plural por
    # concatenacao acerta o substantivo e erra o verbo, e o erro so aparece no
    # dia em que houver duas assinaturas esperando.
    if quantas == 1:
        cabecalho = "Aprendi 1 pessoa que ainda esta sem nome:"
    else:
        cabecalho = f"Aprendi {quantas} pessoas que ainda estao sem nome:"
    linhas = [cabecalho, ""]
    for pendente in vencedoras:
        apelido = apelido_da_chave(pendente.chave)
        if pendente.indice is None:
            linhas.append(f"  {apelido}")
        else:
            # BASE 1: e como o usuario conta as linhas olhando a party window.
            linhas.append(f"  {apelido} (vi na linha {pendente.indice + 1})")

    primeiro = apelido_da_chave(vencedoras[0].chave)
    linhas += [
        "",
        "Para dar o nome, responda: /batizar <apelido> <nick>",
        f"Exemplo: /batizar {primeiro} Fulano",
        "",
        # A FRASE DA AUTORIZACAO E OBRIGATORIA. O batismo e comando de DONO, e
        # um comando nao autorizado morre no `continue` do laco de autorizacao,
        # SEM resposta de recusa. Do lado de um party-mate que tentou
        # responder, isso e indistinguivel do bot ter caido.
        "So quem calibrou o scanner consegue responder isso.",
        # A SAIDA PARA A PERGUNTA ABSURDA (T-02-07), e ela e o unico descarte
        # que esta fase tem. Um recorte contaminado pontua 0.0 contra tudo e
        # pode ter sido aprendido: a pergunta pode estar pedindo que se batize
        # uma janela de navegador. Nao ha comando de esquecer no v1, entao o
        # descarte e IGNORAR — e ignorar so e seguro porque D-04 garante que a
        # pergunta nao volta nunca mais. Dizer isso com todas as letras e o que
        # transforma "o bot esta pedindo uma coisa sem sentido" em "e so nao
        # responder".
        "Se alguma delas nao for gente, e so nao responder: nao pergunto de novo.",
    ]
    return "\n".join(linhas)


@dataclass(frozen=True)
class RespostaDoBatismo:
    """O que vai para o privado de quem digitou, e o que vai para o grupo.

    UM TIPO PROPRIO, E NAO `presenca.RespostaDePresenca`. Importar `presenca`
    arrastaria `agenda` e `loot` para um modulo que precisa nao ter relogio, e
    o `__main__` converte os dois campos numa linha, no mesmo lugar onde ele ja
    converte todos os outros ramos.

    `grupo is None` e o jeito estruturado de dizer "isto nao merece mensagem no
    grupo", e nao uma string vazia — que o despachante enviaria assim mesmo,
    virando uma bolha em branco no WhatsApp.
    """

    privado: str
    grupo: str | None = None


def interpretar_batismo(argumento: str | None) -> tuple[str, str] | None:
    """`(apelido, nick)`, ou None. A GRAMATICA, e ela mora AQUI.

    O PRECEDENTE E O `interpretar_pegou`, e a razao ja esta escrita em
    `comandos.py`: uma gramatica so, que valida na INTERPRETACAO e le no
    RESPONDER. Duas divergiriam no primeiro ajuste e o comando passaria a
    aceitar o que nao executa.

    A POSICAO E QUE SEPARA os dois argumentos, e nao o formato: hex e
    subconjunto de `NOME_VALIDO`, entao `15caec` tambem seria um nick valido.
    Primeira palavra e apelido, segunda e nick, e nada mais e aceito.

    O apelido e normalizado para minusculo porque as chaves do acervo sao hex
    minusculo: quem copiar `15CAEC` de algum lugar continua sendo atendido, e
    isso nao alarga o charset nem um caractere.
    """
    if not argumento:
        return None

    palavras = argumento.split()
    if len(palavras) != 2:
        return None

    apelido, nick = palavras[0].lower(), palavras[1]
    if not APELIDO_VALIDO.fullmatch(apelido):
        return None
    if not NOME_VALIDO.fullmatch(nick):
        return None
    return (apelido, nick)


def _apelidos_sem_nome(acervo: AcervoDeIdentidades) -> tuple[str, ...]:
    return tuple(apelido_da_chave(chave) for chave in acervo.anonimas())


def _recusa_malformada(acervo: AcervoDeIdentidades) -> str:
    """O erro humano mais provavel e INVERTER os dois argumentos.

    Por isso a frase diz qual e qual em vez de so repetir a forma, e por isso o
    exemplo e montado a partir de um apelido REAL da pasta quando houver algum
    sem nome: um exemplo com um apelido inventado ensinaria a digitar uma coisa
    que vai ser recusada no passo seguinte.
    """
    linhas = [
        "Nao entendi. A forma e: /batizar <apelido> <nick>",
        "O apelido vem PRIMEIRO (os digitos que eu cito na pergunta) e o nick "
        "da pessoa vem DEPOIS.",
    ]
    sem_nome = _apelidos_sem_nome(acervo)
    if sem_nome:
        linhas.append(f"Exemplo: /batizar {sem_nome[0]} Fulano")
    return "\n".join(linhas)


def _recusa_desconhecida(acervo: AcervoDeIdentidades, apelido: str) -> str:
    """A recusa que transforma o modo de falha de D-03 em auto-diagnostico.

    `/batizar 3 Mostarda` cai aqui, e "3" e exatamente o que um usuario
    distraido digitaria pensando na terceira linha. Dizer na propria recusa que
    apelido NAO E numero de linha e o que faz ele descobrir sozinho, em vez de
    concluir que o comando esta quebrado.

    E a lista dos apelidos que estao sem nome AGORA vai junto: sem ela o
    usuario nao tem como agir sobre a informacao.
    """
    linhas = [
        f"Nao tenho nenhuma assinatura que comece por {apelido}.",
        "Apelido nao e numero de linha: ele e o codigo de digitos que eu cito "
        "na pergunta.",
    ]
    sem_nome = _apelidos_sem_nome(acervo)
    if sem_nome:
        linhas.append("Sem nome agora: " + ", ".join(sem_nome))
    else:
        linhas.append("Nao ha nenhuma assinatura sem nome agora.")
    return "\n".join(linhas)


def _dono_do_nome(
    nomeados: dict[str, str], nick: str, alvo: str
) -> str | None:
    """A chave DIFERENTE do alvo que ja tem este nome, ou None (BATI-04, D-07).

    A EXCECAO E O PROPRIO ALVO, e ela nao e conveniencia. Rebatizar a entrada X
    de `kaus` para `Kaus` recusado como duplicata DELA MESMA deixaria a
    correcao de caixa impossivel, e correcao de caixa e o conserto mais
    provavel depois de um nome digitado no celular.

    POR QUE `casefold()` AQUI NAO CONTRADIZ A IGUALDADE EXATA DE
    `carregar_identidades`, e a primeira leitura vai desconfiar que contradiz.
    A diferenca e a DIRECAO do erro.

    `carregar_identidades` compara nomes por igualdade EXATA para decidir se
    uma entrada do acervo duplica uma CALIBRADA. La um erro para o lado frouxo
    custa SILENCIO: a entrada entra, as duas se sombreiam pela margem, e a
    linha cala em vez de mentir. A regra e conservadora de proposito.

    Aqui a pergunta e outra: "este nome ja esta ocupado?". Um erro para o lado
    frouxo custa DUAS entradas com nomes que so diferem na caixa, e dois
    alertas que um humano le como a mesma pessoa. Ser MAIS ESTRITO aqui nunca
    contradiz a regra de la, porque ele so RECUSA mais, e recusar mais nao pode
    produzir um nome errado: a regra estrita e um SUBCONJUNTO da frouxa, entao
    as duas nao discordam em nenhum caso em que a resposta importa.

    E ISTO NAO E UM SEGUNDO CRITERIO DE IGUALDADE DE PESSOA, que a docstring de
    `carregar_identidades` proibe. Nao ha comparacao de imagem, nao ha limiar e
    nao ha "parecido o suficiente". A chave de conteudo continua sendo a unica
    definicao de "mesma pessoa" (D-01); isto e uma regra sobre o NOME, no mesmo
    registro da regra do nome que aquela funcao ja tem.
    """
    procurado = nick.casefold()
    for chave, nome in nomeados.items():
        if chave != alvo and nome.casefold() == procurado:
            return chave
    return None


def _recusa_de_nome_ocupado(nick: str, dono: str) -> str:
    """A recusa de BATI-04, e ela e a DOCUMENTACAO de duas dividas herdadas.

    AS DUAS FRASES DO MEIO NAO SAO ENFEITE, e apaga-las reabre as duas dividas
    que o `<threat_model>` do 03-01 registrou:

    - T-03-12 (T-02-18): a mesma pessoa pode ter sido aprendida DUAS vezes,
      quando a volta dela ficou abaixo de 0.75 contra a propria entrada
      (medido na Fase 2: 42 celulas de drift dao 0.7531 e nada nasce, 43 dao
      0.7492 e uma segunda entrada nasce). Sem a frase que diz que a segunda
      ficar sem nome NAO FAZ MAL, o usuario conclui que o scanner esta
      quebrado e fica tentando. Uma assinatura sem nome e reconhecida do mesmo
      jeito e nunca vira sujeito de alerta (APRE-03).

    - T-03-11 (T-02-07): um recorte CONTAMINADO pode ter virado entrada, e o
      usuario pode ter respondido a pergunta dela. O nome fica QUEIMADO, e
      quando a pessoa de verdade for aprendida o batismo dela cai exatamente
      aqui. NAO HA COMANDO DE ESQUECER NO V1 (adiado na Fase 1, e em Deferred
      Ideas do CONTEXT desta fase), entao a unica saida e batizar a entrada de
      lixo com outro nome. Esta mensagem e o unico lugar onde o usuario vai
      procurar por essa saida; uma recusa que so dissesse "esse nome ja e de
      outra" seria um beco sem saida.

    Sem acento e SEM TRAVESSAO: o texto passa por `cp1252` a caminho do
    WhatsApp.
    """
    curto = apelido_da_chave(dono)
    return "\n".join(
        [
            f"Nao batizei ninguem: o nome {nick} ja e da assinatura {curto}. "
            "Nada mudou, nem numa entrada nem na outra.",
            "Se as duas forem a mesma pessoa, eu aprendi o rosto dela duas "
            "vezes. Nesse caso a segunda pode ficar sem nome sem problema "
            "nenhum: assinatura sem nome continua sendo reconhecida e nunca "
            "vira sujeito de alerta.",
            f"Para o nome {nick} ficar livre aqui, batize a {curto} com outro "
            "nome. Essa e a unica saida: nao existe comando de esquecer uma "
            "assinatura.",
            f"Exemplo: /batizar {curto} Fulano",
        ]
    )


def _recusa_ambigua(apelido: str, resolucao: Resolucao) -> str:
    """Os candidatos, e o pedido de mais digitos. NUNCA um desempate."""
    candidatos = ", ".join(apelidos_para_escolher(resolucao.candidatos))
    return "\n".join(
        [
            f"O apelido {apelido} serve para mais de uma assinatura: "
            f"{candidatos}",
            "Mande mais digitos para eu saber qual delas e.",
        ]
    )


def responder_batismo(
    acervo: AcervoDeIdentidades,
    argumento: str | None,
    assinaturas_vivas=None,
    nomes_reservados=None,
) -> RespostaDoBatismo:
    """Da o nome, e faz o nome VALER no mesmo tick (D-06 e D-08).

    O batismo mexe em TRES lugares, e os tres sao obrigatorios:

    1. o DISCO (`acervo.nomear` -> o irmao `nome_<chave>`);
    2. a LISTA VIVA (`assinaturas_vivas`), que e a lista que o proximo
       `extrair` entrega a `identificar_linhas`;
    3. o SNAPSHOT (`nomes_reservados`), pela razao no comentario do `add`.

    OS DOIS ULTIMOS SAO `None` NO LACO DA AGENDA, e a degradacao e conhecida:
    la nao existe lista viva nem rastreador, porque nao existe tela. O DISCO JA
    FOI ESCRITO nesse caso, entao o nome vale a partir do proximo arranque do
    scanner. Ver T-03-07.
    """
    lido = interpretar_batismo(argumento)
    if lido is None:
        return RespostaDoBatismo(privado=_recusa_malformada(acervo))
    apelido, nick = lido

    resolucao = resolver(apelido, acervo.chaves())
    if resolucao.motivo == "ambiguo":
        return RespostaDoBatismo(privado=_recusa_ambigua(apelido, resolucao))
    if resolucao.chave is None:
        # `malformado` nao chega aqui — a gramatica ja filtrou o charset —, e
        # e por isso que os dois casos restantes colapsam num so: sobra
        # `desconhecido`, que e o desfecho de `/batizar 3 Mostarda`.
        return RespostaDoBatismo(privado=_recusa_desconhecida(acervo, apelido))
    chave = resolucao.chave

    # O MAPA `chave -> nome` E LIDO UMA VEZ SO, e as DUAS perguntas saem dele.
    #
    # Uma segunda leitura entre a recusa e a confirmacao abriria uma janela em
    # que o disco mudou no meio (a outra instancia do usuario roda sobre a
    # MESMA pasta), e a resposta descreveria um estado que nunca existiu.
    nomeados = acervo.nomeados()

    # BATI-04, NO LUGAR EXATO: depois de `resolver` ter dito `ok` e ANTES de
    # `acervo.nomear`. Recusar depois de escrever seria escrever.
    dono = _dono_do_nome(nomeados, nick, chave)
    if dono is not None:
        return RespostaDoBatismo(privado=_recusa_de_nome_ocupado(nick, dono))

    nome_anterior = nomeados.get(chave, "")

    desfecho = acervo.nomear(chave, nick)
    if desfecho != "nomeado":
        # `invalido` nao deveria acontecer aqui (a gramatica e a resolucao ja
        # filtraram), e responde igual: para quem digitou, os dois significam
        # "nao mudou nada e da para tentar de novo".
        return RespostaDoBatismo(
            privado=(
                "Nao consegui gravar o nome no disco. Nada mudou, "
                "pode tentar de novo."
            )
        )

    if assinaturas_vivas is not None:
        # A LISTA VIVA (D-08). Sem esta troca o disco tem o nome e a tela
        # continua dizendo "Membro 4" ate o proximo arranque — e o usuario
        # batiza de novo achando que falhou. A mascara e a MESMA, entao a chave
        # nao muda e o reconhecimento nao e perturbado.
        for posicao, assinatura in enumerate(assinaturas_vivas):
            if chave_da_assinatura(assinatura) == chave:
                assinaturas_vivas[posicao] = Assinatura(
                    nome=nick, mascara=assinatura.mascara
                )

    if nomes_reservados is not None:
        # O TERCEIRO ELO, e ele e a metade do criterio 2 que quase ninguem
        # escreve.
        #
        # `rastreador.nomes_reservados` e um SNAPSHOT do arranque, tirado de
        # `cal.nomes_com_assinatura`. Ele existe para que um nome que JA TEM
        # assinatura visual nunca seja emprestado por POSICAO — "a assinatura e
        # quem diz onde a pessoa esta".
        #
        # Sem esta linha, um nick que TAMBEM esteja em `cal.nomes` (o usuario
        # digitou a lista) e que nunca foi calibrado continuaria sendo entregue
        # por `nome_de(indice)` para qualquer linha NAO reconhecida. Desfecho:
        # a linha da pessoa de verdade sai com o nome pela assinatura, e uma
        # outra linha sai com o MESMO nome pela posicao. Dois nomes iguais na
        # tela, e um deles e mentira — exatamente a familia de defeito que a
        # Fase 1 gastou uma onda inteira consertando, chegando pela porta nova
        # desta fase.
        #
        # Mutar o snapshot em tempo de execucao e SEGURO: `calibracao.py`
        # constroi um `set` NOVO a cada leitura de `nomes_com_assinatura`,
        # entao ele nao e aliasado a nada dentro da `Calibracao`.
        #
        # E NUMA CORRECAO O NOME ANTIGO **NAO** SAI DAQUI, e isso e deliberado.
        # Este conjunto e um CONSERVADOR: ele so diz "este nome nao serve de
        # rotulo por POSICAO", e nunca "esta pessoa esta aqui". Tirar o antigo
        # o faria voltar a ser emprestado por posicao para qualquer linha nao
        # reconhecida, e um nome que ja pertenceu a uma assinatura nunca
        # deveria voltar a ser um palpite posicional. Errar para o lado do
        # silencio e a regra do projeto.
        nomes_reservados.add(nick)

    if nome_anterior:
        # A CORRECAO (BATI-05), e a resposta e DERIVADA DO ESTADO — nao ha
        # caminho segundo (D-06). A operacao foi a mesma; o que mudou e que
        # havia um nome antes.
        #
        # O ANTIGO E CITADO porque e o unico jeito de quem digitou conferir na
        # hora que corrigiu a entrada que queria, e nao a vizinha. Mesmo
        # raciocinio ja escrito no `.pegou`, que sempre diz o DIA de volta.
        #
        # E A FRASE DO "LIVRE" SO SAI QUANDO ELE FICOU MESMO LIVRE. Corrigir
        # `kaus` para `Kaus` e a excecao de D-07 sobre a MESMA entrada: o nome
        # continua ocupado por ela, so que com outra caixa, e dizer que ele
        # ficou livre mandaria o usuario tentar um batismo que sera recusado.
        liberou = nome_anterior.casefold() != nick.casefold()
        privado = (
            f"Pronto: {apelido} era {nome_anterior} e agora e {nick}. "
            + (f"O nome {nome_anterior} ficou livre. " if liberou else "")
            + "Os alertas dessa pessoa passam a sair com esse nome, sem "
            "reiniciar nada."
        )
    else:
        privado = (
            f"Pronto: {apelido} agora e {nick}. Os alertas dessa pessoa "
            "passam a sair com esse nome, sem reiniciar nada."
        )

    # POR QUE HA ECO NO GRUPO AQUI, AO CONTRARIO DE QUASE TODOS OS OUTROS
    # RAMOS: a PERGUNTA foi publica. Uma resposta so no privado deixaria a
    # pergunta pendurada no grupo para sempre, e o proximo party-mate que
    # tentasse responder cairia no `continue` da autorizacao, sem resposta
    # nenhuma. Fechar o circuito onde ele foi aberto e o unico jeito de a
    # pergunta nao virar ruido permanente.
    #
    # As RECUSAS acima nao ecoam (`grupo=None`): elas sao entre quem digitou e
    # o scanner.
    return RespostaDoBatismo(privado=privado, grupo=f"{apelido} agora e {nick}.")
