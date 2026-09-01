"""Tirar do acervo o que nunca deveria ter entrado.

POR QUE ESTE MODULO NASCE, E O QUE A FALTA DELE CUSTAVA

O acervo era de mao unica, e tres modulos escreveram isso com todas as letras:
`acervo.py` ("NAO tem poda, de proposito"), `batismo.py` ("nao existe comando de
esquecer uma assinatura", dentro da propria recusa de nome ocupado) e
`sessao.py` ("a gravacao e IRREVERSIVEL"). Era verdade, e a conta chegou.

MEDIDO NA PASTA REAL DO USUARIO EM 2026-08-31: 11 assinaturas conhecidas, 6 sem
nome, e o arranque avisando que 7 delas foram gravadas com a regiao de nome
20x100 quando a atual e 20x110. Uma assinatura de forma diferente nunca mais
casa, entao aquelas 7 sao entradas mortas: as pessoas delas aparecem como
Membro N para sempre. Renderizando as mascaras apareceram tambem "Show
Options", texto de UI, e duas capturas contaminadas com "Kills: 4 Deaths" por
cima do nome. Sem comando de esquecer isso so cresce.

ESQUECER E RENOMEAR, NUNCA APAGAR

A regra e do `acervo.py` e a razao esta escrita la, junto dos prefixos. Aqui
vale repetir so o desfecho: nada sai do disco, e por isso toda resposta deste
modulo TERMINA dizendo o nome do arquivo e como renomea-lo de volta. Uma
promessa de recuperabilidade que nao diz COMO recuperar e uma frase de release
note.

O APELIDO CURTO E O DO `/batizar`, E NAO UM SEGUNDO

`resolver`, `apelido_da_chave`, `apelidos_para_escolher` e `APELIDO_VALIDO` sao
IMPORTADOS de `batismo.py`. Uma segunda resolucao de prefixo divergiria da
primeira no dia em que uma delas ganhasse um desempate, e as duas discordariam
exatamente onde errar e mais caro: um `/batizar 6288ee` e um `/esquecer 6288ee`
mandados no mesmo minuto apontariam para assinaturas diferentes.

E A RECUSA DO AMBIGUO PESA MAIS AQUI QUE NO BATISMO. Um desempate errado la
cola o nome na pessoa errada, e o usuario ve a mentira no primeiro alerta. Aqui
ele tira de circulacao a assinatura da pessoa CERTA, e o sintoma e ela virar
"Membro N" no meio de um farm, sem uma linha de log dizendo por que.

O QUE ESTE MODULO NAO CONHECE

Ele nao importa `visao`, `sessao`, `rastreador`, `calibracao`, `loot`, `agenda`,
`presenca` nem `comandos`. Fala `AcervoDeIdentidades`, `batismo`, `Assinatura` e
stdlib, e so. A geometria de agora CHEGA POR PARAMETRO (`forma_esperada`), pelo
mesmo motivo que ela chega assim em `carregar_identidades`: ler o
`calibration.json` daqui de dentro amarraria o comando a um arquivo que o
`--so-agenda` nao tem.

Este modulo nao tem relogio, e a proibicao esta presa pelo portao AST de
`tests/test_presenca.py`, ao lado de `agenda`, `loot`, `presenca`, `bosses`,
`respawn`, `acervo`, `aprendiz` e `batismo`. A razao e a mesma do `batismo`, com
um agravante proprio: um `datetime.now()` aqui viraria, na primeira
conveniencia, um "esquece sozinho o que tem mais de N dias" — poda automatica
sobre uma pasta que o projeto inteiro decidiu nao podar, decidida por um relogio
em vez de pelo dono.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .acervo import (
    PREFIXO_ASSINATURA,
    PREFIXO_ESQUECIDA,
    PREFIXO_NOME,
    PREFIXO_NOME_ESQUECIDO,
    SUFIXO_ASSINATURA,
    AcervoDeIdentidades,
    chave_da_assinatura,
    fora_de_forma,
)
from .batismo import (
    APELIDO_VALIDO,
    apelido_da_chave,
    apelidos_para_escolher,
    resolver,
)
from .identidade import Assinatura

# A palavra que pede o LOTE.
#
# POR QUE EXISTE UMA FORMA EM LOTE. Sao 7 entradas mortas na pasta do usuario
# hoje. Pedir sete comandos digitados no celular no meio de um farm e pedir
# para ele desistir, e uma limpeza que ninguem faz e uma limpeza que nao
# existe.
#
# POR QUE ELA E ESTA PALAVRA, E NAO "tudo" NEM UM NUMERO. Este e o unico
# comando do projeto que atinge N entradas com uma frase, entao a mira dele nao
# pode ser uma quantidade nem uma vontade: ela e um FATO ja provado. "Fora de
# forma" quer dizer "gravada sob outra regiao de nome", e uma assinatura assim
# NAO PODE casar com nada — ela e comparada no alinhamento calibrado com o
# conteudo deslocado, e pontuou no maximo 0.281 contra o limiar 0.75 nos 16
# pares medidos na Fase 1. Ou seja: o lote so alcanca o que ja esta morto, e
# essa e a diferenca entre uma limpeza e um estrago.
#
# E ELA TEM LETRAS FORA DO HEX, e isso nao e coincidencia: a separacao entre
# "isto e um prefixo de chave" e "isto e o lote" fica ESTRUTURAL. Nenhuma chave
# comeca por `fora-de-forma`, entao nao ha desempate a fazer, nem hoje nem
# depois de a pasta ter centenas de entradas.
PALAVRA_DO_LOTE = "fora-de-forma"


@dataclass(frozen=True)
class PedidoDeEsquecimento:
    """O que o usuario pediu. Estruturado, e nunca uma string com dois sentidos.

    Um `str` que fosse "ou um apelido ou a palavra do lote" obrigaria cada
    leitor a refazer a distincao, e o segundo leitor a faria de outro jeito.
    """

    apelido: str | None = None
    lote: bool = False


@dataclass(frozen=True)
class RespostaDoEsquecimento:
    """O que vai para o privado de quem digitou, e o que vai para o grupo.

    `grupo` E SEMPRE `None` HOJE, e o campo existe assim mesmo. Ele mantem este
    modulo falando a MESMA lingua de `RespostaDoBatismo` e de
    `RespostaDePresenca`, que e a lingua que o bloco de despacho do `__main__`
    entende. Um tipo com um campo a menos obrigaria um ramo especial no funil
    por onde TODA resposta de comando passa, e um erro naquele funil nao quebra
    um recurso: ele muda o destino de todos ao mesmo tempo, em silencio.

    POR QUE NAO HA ECO NO GRUPO, ao contrario do `/batizar`. O batismo ecoa
    porque a PERGUNTA foi publica: sem a resposta, ela fica pendurada no grupo
    para sempre e o proximo party-mate que tentar responder cai no `continue`
    da autorizacao, sem resposta nenhuma. Esquecer nao responde pergunta
    nenhuma, e o grupo nao tem o que fazer com a informacao de que uma
    assinatura saiu de circulacao. Ecoar seria ruido num grupo cujo dono ja
    desligou `avisar_no_horario` do Solo Boss por volume.
    """

    privado: str
    grupo: str | None = None


def interpretar_esquecimento(argumento: str | None) -> PedidoDeEsquecimento | None:
    """A GRAMATICA, e ela mora AQUI. `None` quando nao e pedido nenhum.

    O PRECEDENTE E O `interpretar_pegou` E O `interpretar_batismo`, com a razao
    ja escrita nos dois: uma gramatica so, que valida na INTERPRETACAO e le no
    RESPONDER. Duas divergiriam no primeiro ajuste e o comando passaria a
    aceitar o que nao executa.

    UMA PALAVRA, E EXATAMENTE UMA. `/esquecer 6288ee TITANDER` e recusado em vez
    de lido pela metade: quem digita isso esta pensando em outra coisa (talvez
    em batizar), e obedecer a primeira metade de um pedido destrutivo e o pior
    desfecho possivel.

    NAO EXISTE SINTAXE QUE ALCANCE UMA LINHA, e a trava e uma AUSENCIA — o
    mesmo desenho de D-03 no batismo. `/esquecer 3` cai em "nao tenho nenhuma
    assinatura que comece por 3", porque "3" e so um prefixo hex que nao aponta
    para nada. Nao acrescentar aqui nenhum ramo que aceite numero de linha: a
    party compacta as linhas quando alguem sai, e resolver por posicao tiraria
    de circulacao a assinatura da pessoa errada em SILENCIO.

    O apelido e normalizado para minusculo porque as chaves do acervo sao hex
    minusculo: quem copiar `6288EE` de algum lugar continua sendo atendido, e
    isso nao alarga o charset em um caractere.
    """
    if not argumento:
        return None

    palavras = argumento.split()
    if len(palavras) != 1:
        return None

    palavra = palavras[0].lower()
    if palavra == PALAVRA_DO_LOTE:
        return PedidoDeEsquecimento(lote=True)
    if APELIDO_VALIDO.fullmatch(palavra):
        return PedidoDeEsquecimento(apelido=palavra)
    return None


def _linha_da_volta(chaves: Sequence[str], com_nome: bool) -> str:
    """COMO desfazer, dito com o nome do arquivo. Sem isto a promessa e vazia.

    A resposta inteira existe para dizer duas coisas: que nada foi apagado, e o
    que fazer para trazer de volta. A primeira sem a segunda e pior que nada —
    ela informa que ha volta e esconde o caminho, e o usuario fica procurando
    um comando de desfazer que nao existe de proposito.

    O NOME DO ARQUIVO SAI COM A CHAVE INTEIRA, e nao com o apelido curto. O
    apelido serve para DIGITAR um comando; aqui o usuario vai PROCURAR um
    arquivo numa pasta, e um prefixo de seis digitos o faria abrir cada um para
    conferir. Os 64 caracteres sao feios na tela do celular e sao exatamente o
    que ele precisa colar.
    """
    if len(chaves) == 1:
        chave = chaves[0]
        # CADA CHAVE SO APARECE O NUMERO DE VEZES QUE PRECISA. Sao 64
        # caracteres cada uma, e um "(era assinatura_<chave>.json)" a mais
        # colava 80 caracteres de nada no meio da instrucao. O que o usuario
        # precisa e do nome de ORIGEM e do nome de DESTINO, uma vez cada.
        volta = (
            f"Para trazer de volta, renomeie ele para "
            f"{PREFIXO_ASSINATURA}{chave}{SUFIXO_ASSINATURA}"
        )
        if com_nome:
            volta += (
                f", e {PREFIXO_NOME_ESQUECIDO}{chave} para {PREFIXO_NOME}{chave}"
            )
        return (
            f"Nada foi apagado: na pasta .identidades o arquivo agora se chama "
            f"{PREFIXO_ESQUECIDA}{chave}{SUFIXO_ASSINATURA}. {volta}. Depois "
            "reinicie o scanner. Nao ha comando para isso, e a volta a mao e "
            "de proposito."
        )

    return (
        f"Nada foi apagado: na pasta .identidades cada arquivo trocou o "
        f"prefixo {PREFIXO_ASSINATURA} pelo prefixo {PREFIXO_ESQUECIDA} (e o "
        f"{PREFIXO_NOME} de quem tinha nome virou {PREFIXO_NOME_ESQUECIDO}). "
        "Para trazer uma de volta, renomeie os dois arquivos daquela chave de "
        "volta e reinicie o scanner. Nao ha comando para isso, e a volta a mao "
        "e de proposito."
    )


def _quanto_sobrou(acervo: AcervoDeIdentidades) -> str:
    """A frase do saldo, lida do DISCO depois da operacao.

    DERIVADA e nunca contada por subtracao. Um `antes - quantas` seria uma
    segunda opiniao sobre o disco, e ela erraria justamente quando a outra
    instancia do usuario mexeu na mesma pasta no meio — que e o caso em que o
    usuario mais precisa que o numero esteja certo.
    """
    entradas = acervo.entradas()
    sem_nome = sum(1 for _, assinatura in entradas if assinatura.anonima)
    if not entradas:
        return "Nao sobrou nenhuma assinatura no acervo."
    if len(entradas) == 1:
        return f"Sobrou 1 assinatura no acervo, {sem_nome} sem nome."
    return f"Sobraram {len(entradas)} assinaturas no acervo, {sem_nome} sem nome."


def _tirar_da_lista_viva(
    assinaturas_vivas, chaves: Sequence[str]
) -> None:
    """Tira do reconhecimento AGORA, sem reiniciar. O analogo de D-08.

    MUTA NO LUGAR (`[:]`), e nunca reatribui. Quem le esta lista e o `extrair`
    do proximo tick, pela MESMA referencia que `cal.assinaturas` guarda: trocar
    por uma lista nova aqui dentro deixaria a `Calibracao` apontando para a
    antiga, e o comando pareceria nao ter efeito nenhum ate o proximo arranque
    — que e exatamente o defeito que o batismo consertou com D-08.

    O QUE ESTA FUNCAO **NAO** MEXE, e as duas ausencias sao deliberadas:

    - `Rastreador.assinaturas_configuradas`. Ela e o booleano que separa
      "Membro N" (feio e honesto) de `nomes[indice]` (o nome de quem esta vivo
      em OUTRA linha). Recalcula-la a partir de uma lista que acabou de
      encolher a poria em `False` no dia em que o lote esvaziasse o acervo, e
      devolveria o scanner ao modo em que a POSICAO e a identidade. E a mesma
      armadilha que `Identidades.aviso_de_forma` ja descreve para o descarte
      automatico: "proteger" o reconhecimento jogando o lixo fora entregaria de
      volta a mentira que a identidade visual existe para impedir.

    - `Rastreador.nomes_reservados`. O batismo ACRESCENTA e nunca remove, pela
      razao escrita la: o conjunto e um CONSERVADOR, ele so diz "este nome nao
      serve de rotulo por POSICAO". Tirar um nome dali o faria voltar a ser
      emprestado por posicao para qualquer linha nao reconhecida, e um nome que
      ja pertenceu a uma assinatura nunca deveria voltar a ser um palpite
      posicional. Vale igual na saida.
    """
    if assinaturas_vivas is None:
        return
    procuradas = set(chaves)
    assinaturas_vivas[:] = [
        assinatura
        for assinatura in assinaturas_vivas
        if chave_da_assinatura(assinatura) not in procuradas
    ]


def _sobraram_fora_de_forma(
    assinaturas_vivas, forma_esperada: tuple[int, int] | None
) -> int:
    """Quantas fora de forma continuam vivas depois do lote.

    Elas so podem ter vindo do `calibration.json`, que este comando NAO toca:
    escrever nele desfaria pelo lado de dentro a unica razao de a pasta
    `.identidades/` ser propria (o `calibrar.bat` reescreve o arquivo inteiro).

    Calar sobre elas deixaria o usuario esperando um efeito que nunca vem, que
    e o modo de falha que este projeto mais combate — e que ja custou duas
    horas de "Membro 1" em 2026-08-25, sem uma linha de log dizendo por que.
    """
    if assinaturas_vivas is None:
        return 0
    return sum(
        1
        for assinatura in assinaturas_vivas
        if fora_de_forma(assinatura, forma_esperada)
    )


def _recusa_malformada() -> str:
    """O erro humano mais provavel e digitar o apelido junto com o nick.

    A mao ja aprendeu `/batizar <apelido> <nick>`, e ela repete a forma de dois
    argumentos aqui. Por isso a frase diz que este comando leva UM argumento so,
    em vez de so repetir a sintaxe.
    """
    return "\n".join(
        [
            "Nao entendi. As duas formas sao:",
            "  /esquecer <apelido>       tira UMA assinatura de circulacao",
            f"  /esquecer {PALAVRA_DO_LOTE}   tira todas as que foram gravadas "
            "com outra regiao de nome",
            "O apelido e o codigo de digitos que eu cito na pergunta, e vem "
            "sozinho: aqui nao vai nick nenhum junto.",
        ]
    )


def _recusa_desconhecida(acervo: AcervoDeIdentidades, apelido: str) -> str:
    """A recusa que se auto-diagnostica, no molde da do batismo.

    A lista dos apelidos que existem AGORA vai junto: sem ela o usuario nao tem
    como agir sobre a informacao, e uma recusa que so diz "nao" o manda tentar
    de novo do mesmo jeito.
    """
    linhas = [
        f"Nao tenho nenhuma assinatura que comece por {apelido}. "
        "Nada foi esquecido.",
        "Apelido nao e numero de linha: ele e o codigo de digitos que eu cito "
        "na pergunta.",
    ]
    chaves = acervo.chaves()
    if chaves:
        linhas.append(
            "No acervo agora: " + ", ".join(apelido_da_chave(c) for c in chaves)
        )
    else:
        linhas.append("O acervo esta vazio.")
    return "\n".join(linhas)


def _recusa_ambigua(apelido: str, candidatos: Sequence[str]) -> str:
    """Os candidatos, e o pedido de mais digitos. NUNCA um desempate.

    Os recortes saem de `apelidos_para_escolher`, e nao de um `[:6]` daqui: a
    saida oferecida ("mande mais digitos") tem de ser SEGUIVEL, e duas chaves
    que compartilham os seis primeiros digitos produziriam uma lista com o
    mesmo apelido duas vezes. Uma recusa sem saida e um beco.
    """
    return "\n".join(
        [
            f"O apelido {apelido} serve para mais de uma assinatura: "
            + ", ".join(apelidos_para_escolher(tuple(candidatos))),
            "Nao esqueci nenhuma delas. Mande mais digitos para eu saber qual e.",
        ]
    )


def _esquecer_uma(
    acervo: AcervoDeIdentidades, apelido: str, assinaturas_vivas
) -> RespostaDoEsquecimento:
    resolucao = resolver(apelido, acervo.chaves())
    if resolucao.motivo == "ambiguo":
        return RespostaDoEsquecimento(
            privado=_recusa_ambigua(apelido, resolucao.candidatos)
        )
    if resolucao.chave is None:
        # `malformado` nao chega aqui: a gramatica ja filtrou o charset. Sobra
        # `desconhecido`, que e o desfecho de `/esquecer 3`.
        return RespostaDoEsquecimento(
            privado=_recusa_desconhecida(acervo, apelido)
        )
    chave = resolucao.chave

    # O NOME E LIDO ANTES DE A ENTRADA SUMIR. Depois do `esquecer` ela nao esta
    # mais no acervo, e a resposta nao teria como cita-lo — e citar o nome e o
    # unico jeito de quem digitou conferir NA HORA que tirou a entrada que
    # queria, e nao a vizinha. Mesmo raciocinio ja escrito no `.pegou`, que
    # sempre diz o DIA de volta.
    nome_gravado = acervo.nomeados().get(chave, "")

    desfecho = acervo.esquecer(chave)
    if desfecho == "simulado":
        return RespostaDoEsquecimento(privado=_recusa_da_simulacao())
    if desfecho == "ausente":
        return RespostaDoEsquecimento(
            privado=(
                f"A assinatura {apelido} ja nao estava no acervo. "
                "Nada mudou. " + _quanto_sobrou(acervo)
            )
        )
    if desfecho != "esquecida":
        return RespostaDoEsquecimento(privado=_recusa_do_disco())

    _tirar_da_lista_viva(assinaturas_vivas, [chave])

    quem = f"{apelido} (era {nome_gravado})" if nome_gravado else apelido
    partes = [
        f"Esqueci a assinatura {quem}. {_quanto_sobrou(acervo)}",
    ]
    if assinaturas_vivas is not None:
        partes.append(
            "Ela ja saiu do reconhecimento agora, sem reiniciar nada."
        )
    partes.append(_linha_da_volta([chave], com_nome=bool(nome_gravado)))
    return RespostaDoEsquecimento(privado=" ".join(partes))


def _esquecer_o_lote(
    acervo: AcervoDeIdentidades,
    assinaturas_vivas,
    forma_esperada: tuple[int, int] | None,
) -> RespostaDoEsquecimento:
    if forma_esperada is None:
        # SEM GEOMETRIA NAO HA LOTE, e adivinhar aqui seria o comando
        # escolhendo sozinho o que esta morto. A escolha errada tira de
        # circulacao gente VIVA, e o sintoma so aparece no proximo farm.
        #
        # E o caso do `--so-agenda`, que nao le calibracao nenhuma de proposito
        # (a docstring de `laco_da_agenda` diz "sem jogo, sem calibracao"). A
        # recusa DIZ ONDE o comando funciona: uma recusa que so diz nao manda o
        # usuario tentar de novo do mesmo jeito.
        return RespostaDoEsquecimento(
            privado=(
                "Nao sei qual e a regiao de nome de agora, entao nao tenho "
                "como saber o que esta fora de forma. Nada foi esquecido. "
                "Mande esse comando com o scanner da party rodando, que e "
                "quem le a calibracao."
            )
        )

    entradas = acervo.entradas()
    mortas = [
        chave
        for chave, assinatura in entradas
        if fora_de_forma(assinatura, forma_esperada)
    ]
    if not mortas:
        # A GUARDA QUE IMPEDE O LOTE DE VIRAR "APAGUE TUDO". Sem ela, um
        # `/esquecer fora-de-forma` mandado depois de uma recalibracao bem
        # sucedida nao acharia nada e poderia ser "consertado" para alcancar
        # outra coisa. Dizer que o alvo do lote e vazio, e parar, e o
        # comportamento inteiro.
        altura, largura = forma_esperada
        return RespostaDoEsquecimento(
            privado=(
                f"Nenhuma assinatura do acervo esta fora da regiao de nome de "
                f"agora ({altura}x{largura}). Nada foi esquecido: este lote so "
                "alcanca o que ja nao pode casar com nada."
            )
        )

    esquecidas: list[str] = []
    for chave in mortas:
        desfecho = acervo.esquecer(chave)
        if desfecho == "simulado":
            return RespostaDoEsquecimento(privado=_recusa_da_simulacao())
        if desfecho == "esquecida":
            esquecidas.append(chave)

    if not esquecidas:
        # Todas falharam ou ja tinham sumido no meio do caminho (a outra
        # instancia do usuario roda sobre a MESMA pasta).
        return RespostaDoEsquecimento(privado=_recusa_do_disco())

    _tirar_da_lista_viva(assinaturas_vivas, esquecidas)

    altura, largura = forma_esperada
    curtos = ", ".join(apelido_da_chave(chave) for chave in esquecidas)
    quantas = len(esquecidas)
    # AS DUAS REDACOES POR EXTENSO, e nao um sufixo colado. Mesma disciplina
    # (e mesma razao) do cabecalho de `montar_pergunta`: uma regra de plural
    # por concatenacao acerta o substantivo e erra o verbo, e o erro so
    # aparece no dia em que o lote pegar exatamente uma entrada.
    if quantas == 1:
        cabecalho = (
            f"Esqueci 1 assinatura que estava fora da regiao de nome de agora "
            f"({altura}x{largura}): {curtos}."
        )
    else:
        cabecalho = (
            f"Esqueci {quantas} assinaturas que estavam fora da regiao de nome "
            f"de agora ({altura}x{largura}): {curtos}."
        )
    partes = [cabecalho, _quanto_sobrou(acervo)]
    if assinaturas_vivas is not None:
        partes.append("Ja sairam do reconhecimento agora, sem reiniciar nada.")
        restantes = _sobraram_fora_de_forma(assinaturas_vivas, forma_esperada)
        if restantes:
            partes.append(
                f"Ainda ha {restantes} fora de forma que nao vieram do acervo "
                "e sim do calibration.json: essas eu nao mexo, e a saida delas "
                'e rodar calibrar.bat --nomes "..." de novo.'
            )
    partes.append(_linha_da_volta(esquecidas, com_nome=False))
    return RespostaDoEsquecimento(privado=" ".join(partes))


def _recusa_da_simulacao() -> str:
    """O `--dry-run` nao encosta na pasta compartilhada. Ver `acervo.esquecer`."""
    return (
        "Isto aqui e uma simulacao (--dry-run), entao nao esqueci nada: a "
        "pasta .identidades e a MESMA do scanner de verdade, e mexer nela "
        "daqui apagaria do reconhecimento dele uma pessoa que ele esta vendo."
    )


def _recusa_do_disco() -> str:
    return (
        "Nao consegui renomear o arquivo no disco. Nada mudou, pode tentar "
        "de novo."
    )


def responder_esquecimento(
    acervo: AcervoDeIdentidades,
    argumento: str | None,
    assinaturas_vivas: list[Assinatura] | None = None,
    forma_esperada: tuple[int, int] | None = None,
) -> RespostaDoEsquecimento:
    """Tira do disco e do reconhecimento vivo, e diz como desfazer.

    OS DOIS PARAMETROS OPCIONAIS SAO `None` NO LACO DA AGENDA, e as duas
    ausencias sao honestas, nao descuido: la nao existe lista viva (nao existe
    tela) nem calibracao lida (o modo `--so-agenda` e o de quem esta com o jogo
    FECHADO). A degradacao de cada uma esta escrita onde ela acontece:
    `_tirar_da_lista_viva` vira no-op e o disco vale a partir do proximo
    arranque (T-03-07), e o LOTE e recusado com uma frase que diz onde ele
    funciona.
    """
    pedido = interpretar_esquecimento(argumento)
    if pedido is None:
        return RespostaDoEsquecimento(privado=_recusa_malformada())
    if pedido.lote:
        return _esquecer_o_lote(acervo, assinaturas_vivas, forma_esperada)
    return _esquecer_uma(acervo, pedido.apelido, assinaturas_vivas)
