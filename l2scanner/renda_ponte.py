"""A PONTE XP <-> PORCENTAGEM: pontos percentuais do nivel viram XP absoluto.

O usuario pediu isto com as proprias palavras — *"XP e isso que aparece no chat
e sobe a porcentagem, mas preciso do numero do chat"* (REND-08). A barra entrega
porcentagem; o chat entrega XP. Este modulo e o cambio entre as duas, e ele
recusa converter quando nao tem a taxa.

SOMAR O CHAT NAO FUNCIONA, E ESTA MEDIDO
=========================================
Amostrando a 0,8 s, o chat entregou **55,4%** da adena que a barra viu no mesmo
intervalo; a 2,0 s entregou **29,8%**. O chat tem 6 linhas visiveis e o
personagem abate ~104 mobs por minuto, entao a janela inteira vira em ~4 s.
Somar linhas produziria um XP/h **45% abaixo da verdade, com cara de medido** —
que e o modo de falha que este workstream inteiro existe para impedir.

A divisao de trabalho e o ponto: o **chat** entrega o que NAO exige completude
(quanto vale um abate); a **barra** entrega o que exige (quantos abates
aconteceram). Invertido, nao funciona.

A MEDICAO QUE DA DIREITO DE CHAMAR ISTO DE CONSTANTE
=====================================================
Faerlina, nivel 67, 2026-09-02, a **55 Hz** (0,018 s) — 8.555 leituras de EXP em
2,5 minutos:

- **zero leituras negativas em 8.555.** O leitor de EXP da Fase 1 nao oscila, e
  isto valida a Fase 1 de quebra.
- **a soma dos 188 degraus e 1903 unidades, e a barra andou exatamente 1903.**
  Nenhum evento escapou: isto e um CENSO, e nao uma amostra.
- com o censo, o aglomerado do abate isola-se sozinho: **114 eventos de ~10
  unidades, media 9,956**.
- **387 XP por abate**, media de **240 linhas** de chat.
- portanto `387 / 0,0009956 = 388.700 XP por ponto percentual`, e
  **38,87 milhoes** de XP no nivel 67.

**DUAS MEDICOES INDEPENDENTES, 1,5% DE DIFERENCA.** A primeira conta, a 0,8 s de
amostragem, deu **383.124**; o refinamento a 55 Hz deu **388.700**. Duas
medicoes que nao compartilham o metodo de agrupamento e caem a 1,5% uma da outra
e o que separa uma constante de um chute.

**O AGLOMERADO QUE NINGUEM EXPLICA VAI REGISTRADO, E NAO ESCONDIDO:** 50 eventos
de ~3 unidades, a 20 por minuto, somando 7,9% do XP da janela. Nao sao erro de
leitura (nao ha um degrau negativo sequer em 8.555 amostras) e nao sao abate (o
chat mostra XP por abate entre 363 e 439, um intervalo de 1,2x e nao de 3x).
**Isso nao afeta a constante:** ela converte pontos percentuais em XP do nivel,
seja qual for a ORIGEM do ganho.

Tudo acima esta versionado em `.planning/workstreams/renda/REQUIREMENTS.md`,
REND-08 e REND-09.

A RECUSA E O PRODUTO TANTO QUANTO A CONVERSAO
==============================================
**Sem constante para o NIVEL ATUAL, o XP absoluto e DECLARADO INDISPONIVEL** —
nunca convertido com a constante do nivel anterior. O custo do nivel muda
justamente entre um nivel e o seguinte, e a constante do 66 aplicada ao 67 nao
produz um campo vazio que alguem nota: produz um numero com a mesma cara de
certo e alguns por cento errado, indistinguivel de um certo depois de gravado.

A disciplina e a do cambio XM->BRL do `dashboard`: sem taxa informada, mostra a
moeda de origem e **diz que a outra esta indisponivel**. E as ausencias sao
TRES, com tres textos diferentes, porque o conserto de cada uma e outro: medir a
ponte pela primeira vez, medir a ponte deste personagem, ou medir a ponte deste
nivel.

O QUE ESTE MODULO NAO E, E POR QUE
===================================
Ele **nao importa `calibracao`**: recebe a chave `renda_ponte_de_xp` por
parametro e nao sabe que existe um arquivo em disco. E ele **nao importa
`renda_conta`**: a ponte e conversao de UNIDADE e a conta e TAXA. Se as duas se
misturassem, `renda_conta` passaria a saber que o `calibration.json` existe — e
os dois planos desta onda deixariam de poder rodar em paralelo.

**NENHUM PONTO FLUTUANTE ATRAVESSA A CONVERSAO**, pela regra ja escrita na
docstring do `LeituraDaRenda`: `Fraction` quando a divisao nao e exata, `int`
quando e. E a unidade do EXP sai da constante da Fase 1
(`renda_leitura.DECIMOS_DE_MILESIMO_POR_PONTO`) e nunca de um literal — dois
literais iguais sao duas verdades esperando divergir.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

# ===========================================================================
# OS TRES MOTIVOS DE AUSENCIA, E ELES SAO TRES PORQUE O CONSERTO E OUTRO
# ===========================================================================

SEM_PONTE_NENHUMA = (
    "a ponte XP<->porcentagem nunca foi medida: o painel mostra pontos "
    "percentuais e o XP absoluto fica indisponivel. Conserto: medir a ponte "
    "(XP por abate no chat dividido por pontos percentuais por abate na barra) "
    "e semea-la no calibration.json."
)

SEM_PONTE_PARA_O_PERSONAGEM = (
    "a ponte XP<->porcentagem nao foi medida PARA ESTE PERSONAGEM: o "
    "multiplicador de XP e do personagem — a barra da Faerlina exibe 562% —, "
    "entao a constante de outra instancia nao serve. Conserto: medir a ponte "
    "nesta instancia."
)

SEM_PONTE_PARA_O_NIVEL = (
    "a ponte XP<->porcentagem nao foi medida PARA O NIVEL ATUAL, e a constante "
    "do nivel anterior NAO e usada: o custo do nivel muda, e converter com ela "
    "produziria um numero plausivel e errado. Conserto: remedir a ponte neste "
    "nivel."
)


# ===========================================================================
# A CONVENCAO DO BONUS DO CHAT (REND-09), RESOLVIDA POR MEDICAO
# ===========================================================================

# As quatro linhas distintas versionadas no REND-08/REND-09, como (total, bonus).
#
# Os RESTOS — `363-299=64`, `388-319=69`, `405-333=72`, `439-361=78` — sao o que
# o requisito versiona, e sao o denominador do multiplicador.
LINHAS_MEDIDAS_DO_BONUS = ((363, 299), (388, 319), (405, 333), (439, 361))

# A banda do multiplicador, em CENTESIMOS de vez (562 = 5,62x = 562%).
#
# Ela e em centesimos inteiros de proposito: a comparacao vira divisao inteira e
# nenhum ponto flutuante entra numa conta cujo resultado e uma afirmacao sobre a
# tela. `363*100 // 64 = 567`, `388*100 // 69 = 562`, `405*100 // 72 = 562`,
# `439*100 // 78 = 562`.
PISO_DO_MULTIPLICADOR_EM_CENTESIMOS = 562
TETO_DO_MULTIPLICADOR_EM_CENTESIMOS = 567

# O numero que a PROPRIA BARRA exibe ao lado do EXP, e que e o que fecha a
# prova: se o total fosse `363+299`, o multiplicador seria 10,34x e nada na tela
# corresponderia a ele.
MULTIPLICADOR_EXIBIDO_PELA_BARRA_EM_CENTESIMOS = 562


def total_do_xp_da_linha(total: int, bonus: int) -> int:
    """`363 XP (bonus: 299)` -> **363**. O parenteses NAO se soma.

    O usuario perguntou se aquela linha vale 363 ou 662, e disse nao saber. E
    363: o valor entre parenteses e a PARTE do total que veio de bonus, e nao um
    extra a acrescentar.

    A PROVA E POR MEDICAO E NAO POR LEITURA DE DOCUMENTACAO. Para dez das onze
    linhas distintas capturadas, `total / (total - bonus)` cai entre 562% e 567%
    — `363/64 = 5,67`, `388/69 = 5,62`, `405/72 = 5,62`, `439/78 = 5,63` — e a
    propria barra exibe **562%** ao lado do EXP, que e o multiplicador de XP do
    personagem. Se o total fosse a soma, o multiplicador seria 10,3x e nada na
    tela corresponderia a ele.

    ESTA FUNCAO EXISTE MESMO SEM NINGUEM PARSEAR O CHAT AINDA, e essa e a razao
    dela: a ferramenta que vai medir a ponte esta deferida para a Fase 3, e sem
    esta convencao presa por teste o REND-09 fecharia como PROSA — e a proxima
    pessoa a escrever o parser somaria o parenteses.
    """
    if bonus < 0 or bonus >= total:
        raise ValueError(
            f"linha de chat malformada: total={total}, bonus={bonus}. O bonus e "
            f"a PARTE do total que veio de bonus, entao ele e sempre menor que "
            f"o total; um bonus maior ou igual descreve outra convencao, e "
            f"adivinhar qual seria inventar o numero."
        )
    return total


def multiplicador_em_centesimos(total: int, bonus: int) -> int:
    """`total / (total - bonus)` em centesimos de vez, por divisao INTEIRA.

    E a conta que refuta a soma: o resto `total - bonus` e o XP base do abate, e
    a razao entre o total e ele e o multiplicador de XP do personagem. Ele tem
    de bater com o que a barra exibe, e bate.
    """
    resto = total - bonus
    if resto <= 0:
        raise ValueError(
            f"linha de chat malformada: total={total}, bonus={bonus}. Sem resto "
            f"positivo nao existe multiplicador — e um multiplicador infinito "
            f"seria uma divisao por zero com cara de medicao."
        )
    return total * 100 // resto


# ===========================================================================
# O RESULTADO, NA FORMA DE `Tendencia`: VALOR OU MOTIVO, NUNCA OS DOIS
# ===========================================================================


@dataclass(frozen=True)
class XpAbsoluto:
    """O XP em numero absoluto, ou o MOTIVO de ele nao estar aqui.

    `valor` e `None` sempre que nao ha numero a dizer, e `motivo_da_ausencia`
    diz POR QUE. Quem desenha nunca precisa adivinhar o motivo de um campo
    vazio — e nunca precisa decidir sozinho se pode usar a constante do nivel
    anterior, porque essa decisao ja foi tomada aqui.

    `procedencia` e a entrada CRUA da constante que produziu o valor, e ela
    viaja DENTRO do resultado e nao ao lado: quem exibe consegue dizer que o
    numero veio de uma medicao de 2,5 minutos com censo completo, 114 abates e
    240 linhas de chat — e nao de um chute. Ela e o dict cru e nao uma
    reconstrucao, pela mesma razao do `salvar`: um campo que a ferramenta de
    medicao grave amanha atravessa em vez de sumir no caminho.
    """

    valor: int | Fraction | None
    motivo_da_ausencia: str | None
    procedencia: dict | None


def constante_do_nivel(
    ponte: dict | None, personagem: str | None, nivel: int | None
) -> tuple[dict | None, str | None]:
    """A entrada DAQUELE personagem NAQUELE nivel, ou o motivo nomeado da falta.

    A PROIBICAO DE QUEDA MORA AQUI, NUM LUGAR SO, e `Calibracao.ponte_do_nivel`
    delega para ca em vez de repetir a busca: duas normalizacoes da chave de
    nivel seriam duas verdades sobre uma so forma, e na primeira mudanca de
    formato uma delas envelheceria calada.

    A CHAVE DO NIVEL E TEXTO NO JSON. `{67: ...}` gravado volta `{"67": ...}`, e
    um `.get(nivel)` cru nao levantaria erro nenhum — so devolveria nada, e o
    painel diria "indisponivel" para sempre sem ninguem entender por que. As
    duas formas sao aceitas: a de texto, que e a que volta do disco, e a
    inteira, que e a que existe em memoria antes do primeiro `salvar`.
    """
    if not ponte or not isinstance(ponte, dict):
        return None, SEM_PONTE_NENHUMA

    do_personagem = ponte.get(personagem) if personagem else None
    if not isinstance(do_personagem, dict) or not do_personagem:
        return None, SEM_PONTE_PARA_O_PERSONAGEM

    entrada = None
    if nivel is not None:
        entrada = do_personagem.get(str(nivel))
        if entrada is None:
            entrada = do_personagem.get(nivel)
    if not isinstance(entrada, dict):
        return None, SEM_PONTE_PARA_O_NIVEL

    return entrada, None


def _converter(
    ponte: dict | None,
    personagem: str | None,
    nivel: int | None,
    pontos_percentuais: Fraction,
) -> XpAbsoluto:
    """Pontos percentuais (como `Fraction`) vezes a constante, ou a recusa.

    UM LUGAR SO PARA A MULTIPLICACAO, e por isso as tres portas publicas
    convergem para ca: o ganho, o acumulado e a taxa diferem no que a UNIDADE de
    entrada significa, e nao na conta.
    """
    entrada, motivo = constante_do_nivel(ponte, personagem, nivel)
    if entrada is None:
        return XpAbsoluto(valor=None, motivo_da_ausencia=motivo, procedencia=None)

    valor = pontos_percentuais * entrada["xp_por_ponto"]
    if valor.denominator == 1:
        valor = int(valor)
    return XpAbsoluto(valor=valor, motivo_da_ausencia=None, procedencia=entrada)


def _pontos_percentuais(decimos: int) -> Fraction:
    """Decimos de milesimo -> pontos percentuais, como `Fraction` exata.

    O IMPORT MORA AQUI E NAO NO TOPO, pelo numero medido no `renda_conta`:
    `import l2scanner.renda_leitura` traz **334 modulos, com cv2 E numpy**,
    porque ele importa `mercado_visao` e `ocr`. Este modulo nao tem nada que ver
    com pixel — ele e aritmetica —, e paga-lo no topo faria `import
    l2scanner.renda_ponte` custar OpenCV inteiro.

    A DEFINICAO CONTINUA SENDO UMA SO: a unidade e IMPORTADA e nunca
    redefinida. Um `10_000` escrito aqui seria uma segunda verdade sobre a
    gramatica do EXP, e ela envelheceria calada no dia em que a primeira
    mudasse.
    """
    from .renda_leitura import DECIMOS_DE_MILESIMO_POR_PONTO

    return Fraction(decimos, DECIMOS_DE_MILESIMO_POR_PONTO)


def xp_do_ganho(
    ponte: dict | None,
    personagem: str | None,
    nivel: int | None,
    ganho_em_decimos: int,
) -> XpAbsoluto:
    """Um GANHO de EXP em decimos de milesimo vira XP absoluto.

    E a porta que o painel usa para responder "quanto XP eu ganhei nesta
    sessao": o `PassoDaRenda` entrega o ganho em decimos, e esta funcao o
    converte — ou diz por que nao converteu.
    """
    return _converter(ponte, personagem, nivel, _pontos_percentuais(ganho_em_decimos))


def xp_acumulado_no_nivel(
    ponte: dict | None,
    personagem: str | None,
    nivel: int | None,
    exp_em_decimos: int,
) -> XpAbsoluto:
    """O EXP LIDO NA BARRA vira o XP ja acumulado dentro do nivel atual.

    A conta e a mesma do ganho — a diferenca esta no que o numero significa, e
    nomear as duas separado e o que impede alguem de somar um acumulado a um
    ganho por engano.
    """
    return _converter(ponte, personagem, nivel, _pontos_percentuais(exp_em_decimos))


def xp_por_hora(
    ponte: dict | None,
    personagem: str | None,
    nivel: int | None,
    pontos_percentuais_por_hora: Fraction | int,
) -> XpAbsoluto:
    """Uma TAXA em pontos percentuais por hora vira uma taxa em XP por hora.

    A entrada ja esta em PONTOS PERCENTUAIS (e nao em decimos), porque e assim
    que `renda_conta.taxa_por_hora` fala. E a taxa HERDA o motivo de ausencia:
    sem ponte, a resposta continua sendo a recusa nomeada, e nunca um XP/h
    convertido pela constante do nivel errado.

    A EVIDENCIA NAO ATRAVESSA ESTA FUNCAO de proposito. `n`, janela e recencia
    sao da taxa e continuam com ela; aqui so muda a unidade. Duplicar a
    `Evidencia` deste lado criaria uma segunda copia do `n` que uma hora
    divergiria da primeira.
    """
    return _converter(ponte, personagem, nivel, Fraction(pontos_percentuais_por_hora))
