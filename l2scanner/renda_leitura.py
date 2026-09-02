"""O transform PURO da leitura da renda: pixels da barra inferior -> inteiro.

Este modulo nao abre janela, nao le argumento de linha de comando, nao escreve
arquivo e nao le relogio. Ele olha um recorte e responde "este campo diz
`8,0012%`", ou diz POR QUE nao respondeu. Quem mostra isso a um humano e
`renda_modo.py`; quem calibra e o calibrador da renda.

A SETA APONTA FERRAMENTA -> PURO, E NUNCA O CONTRARIO
=====================================================
A razao NAO e estetica, e a mesma que `mercado_leitura` ja escreveu: os modulos
de calibracao chamam `tornar_consciente_de_dpi()` NO IMPORT e carregam
`argparse` e as chamadas de JANELA do OpenCV. Um modulo de producao que
importasse a ferramenta pagaria esse efeito colateral so por existir, e uma
janela de conferencia acabaria abrindo dentro do tick de captura.

(As chamadas de janela nao aparecem NEM POR NOME neste arquivo, nem em
comentario: um teste de fonte varre o arquivo inteiro atras delas, e um teste
que aceitasse mencao em comentario deixaria de pegar a chamada de verdade no
dia em que ela entrasse comentada e fosse descomentada.)

TODO LIMIAR CHEGA POR PARAMETRO, SEM VALOR DE FABRICA
=====================================================
O piso de brilho de cada regiao vem do `calibration.json`, medido no frame do
proprio usuario, e chega como parametro somente-nomeado SEM default. Um default
e um numero magico que entra por omissao — e aqui ele seria pior que numero
magico, porque MEDIDO nao existe um piso unico: a banda em que o nivel sai
correto e 190-220 e a da adena por OCR e 150, e elas nao tem intersecao
nenhuma (M-E). Um default serviria a uma regiao e apagaria a outra em silencio.

O NUMERO INTERNO E INTEIRO, SEMPRE
==================================
O EXP viaja em DECIMOS DE MILESIMO de ponto percentual, no precedente de
`total_em_centesimos`: `57,9749%` e `579749`. Nunca `float`. Uma taxa calculada
sobre binario de ponto flutuante acumula erro que ninguem consegue ver depois
de gravado, e o produto inteiro desta milestone e uma diferenca entre duas
leituras.

A FASE 1 E SEM ESTADO
=====================
`frame -> valor | recusa`. Nao ha memoria de tick anterior aqui, e nao vai
haver: a monotonicidade entra como funcao PURA sobre um par passado por
parametro, e nunca como memoria viva. Um leitor com memoria mente sobre a tela
atual usando a tela passada.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import numpy as np

from .frames import Regiao
from .mercado_leitura import limite_de_glifo_unico, mascara_de_numero
from .ocr import ler_texto, ler_texto_ampliado

log = logging.getLogger(__name__)

# OS NOMES DOS CAMPOS, e os dois primeiros carregam a mesma mentira que as
# sub-chaves do `calibration.json`: `barra_esquerda` e o EXP e `barra_direita` e
# a ADENA. A mentira fica ESCRITA em vez de consertada em silencio — quem
# renomear renomeia as duas, num commit proprio.
CAMPO_DO_EXP = "exp"

# ---------------------------------------------------------------------------
# OS MOTIVOS DE RECUSA -- e eles sao DISTINTOS porque os consertos sao distintos
# ---------------------------------------------------------------------------
#
#   recorte-fora-do-frame -> o retangulo calibrado nao cabe nesta janela;
#                            recalibre, ou a janela mudou de tamanho
#   campo-vazio           -> o OCR abstem nas duas escalas; a tela esta noutro
#                            lugar, ou o piso de brilho apagou o campo
#   gramatica             -> o OCR LEU alguma coisa e a leitura nao respeita a
#                            forma; tipicamente piso de brilho errado
#   discordancia          -> as duas escalas leram numeros DIFERENTES; e o caso
#                            perigoso, e o unico em que ha duas afirmacoes
#   personagem            -> nao se sabe de quem e esta tela, ou ele nao esta
#                            calibrado; NUNCA se cai na calibracao do vizinho
#
# Campo vazio e gramatica PARECEM a mesma coisa e nao sao, e somar os dois num
# motivo unico faria dois consertos diferentes parecerem o mesmo.
MOTIVO_DO_RECORTE_FORA_DO_FRAME = "recorte-fora-do-frame"
MOTIVO_DO_CAMPO_VAZIO = "campo-vazio"
MOTIVO_DA_GRAMATICA = "gramatica"
MOTIVO_DA_DISCORDANCIA = "discordancia-entre-escalas"
MOTIVO_DO_PERSONAGEM = "personagem-sem-calibracao"


@dataclass(frozen=True)
class RecusaDaRenda:
    """Um campo que NAO virou numero, e a peneira que o pegou.

    ELE CARREGA O `detalhe`, QUE O `Descarte` DO MERCADO JOGA FORA, e a
    diferenca e de consumidor. O `Descarte` tem `indice` de linha de grade —
    que nao significa nada aqui — e manda o detalhe so para o log, porque ali
    quem ve a recusa e o resumo de sessao. Para um leitor de tres campos que a
    Fase 2 vai consumir, o motivo precisa viajar NO DADO: quem exibe a renda
    precisa poder dizer "o nivel nao leu porque o campo estava vazio" sem abrir
    o arquivo de log.
    """

    campo: str
    motivo: str
    detalhe: str


@dataclass(frozen=True)
class ValorDaRenda:
    """Um campo que virou numero, e POR QUANTAS ESCALAS ele foi sustentado.

    `escalas` NAO E DECORACAO, E A GUARDA SE ANUNCIANDO. Medido em campo (M-D),
    as duas escalas de OCR quase nunca concordam — elas se REVEZAM —, e a regra
    de cruzamento aceita um valor sustentado por UMA escala so, porque exigir
    duas recusaria 100% das amostras de alguns campos. O custo dessa aceitacao
    e real: com uma escala so, o cruzamento deixa de pegar substituicao de
    digito naquele campo.

    Entao o custo VIAJA COM O VALOR. Quem exibe marca a leitura de uma escala
    so, na mesma disciplina de `n` e recencia que o `--mercado` ja aplica a todo
    numero que vai a tela. Uma guarda enfraquecida que nao se anuncia e uma
    guarda que ninguem sabe que perdeu.
    """

    campo: str
    valor: int
    escalas: int
    texto: str


def _recusar(campo: str, motivo: str, detalhe: str) -> RecusaDaRenda:
    """A recusa vai para o log com os delimitadores `>>><<<`, sem rate-limit.

    A forma e a de `mercado_leitura._recusar`, e as duas decisoes dele valem
    aqui pelas mesmas razoes: os delimitadores porque ESPACO EM BRANCO E O QUE
    DISTINGUE DUAS LEITURAS PARECIDAS (`8.0012%` e `8. 0012%` nao sao a mesma
    leitura, e sem delimitador as duas saem iguais no log), e a AUSENCIA de
    limitacao de repeticao porque o log rotativo e a unica ferramenta de
    forense pos-farm deste projeto — sao exatamente estas linhas que respondem
    "por que nao gravou".
    """
    log.warning("renda: %s RECUSADO (%s): %s", campo, motivo, detalhe)
    return RecusaDaRenda(campo=campo, motivo=motivo, detalhe=detalhe)


def entre_delimitadores(texto: str | None) -> str:
    """`>>>o que o OCR viu<<<`. `None` vira `>>><<<`, que e visivelmente vazio."""
    return f">>>{texto if texto is not None else ''}<<<"


def recortar(
    frame: np.ndarray, regiao: Regiao, *, campo: str
) -> np.ndarray | RecusaDaRenda:
    """O recorte, ou RECUSA NOMEADA. NUNCA um array silenciosamente menor.

    A ARMADILHA QUE ESTA FUNCAO EXISTE PARA FECHAR, MEDIDA (M12): numa janela
    de altura 1392, `frame[1368 : 1368+26]` devolve **24 linhas**, em silencio.
    `1368 + 26 = 1394`, numpy encurta a fatia e nao levanta, nao avisa e nao
    marca o array de forma nenhuma. Um EXP lido de 24 linhas em vez de 26 nao e
    um erro que aparece: e uma leitura plausivel e errada, do tipo que, depois
    de gravada, nao se distingue de uma certa.

    E e a armadilha mais barata de evitar e a mais cara de descobrir depois — o
    retangulo vem de um arquivo editavel a mao, e a janela do jogo pode ter
    mudado de tamanho desde a calibracao.

    `campo` VIAJA POR PARAMETRO e nao tem default: a recusa precisa dizer QUAL
    campo nao coube, e um rotulo generico transformaria tres consertos
    diferentes numa mensagem so.
    """
    if frame is None or getattr(frame, "size", 0) == 0:
        return _recusar(
            campo,
            MOTIVO_DO_RECORTE_FORA_DO_FRAME,
            "o frame chegou vazio; a captura nao entregou pixels",
        )

    altura_do_frame, largura_do_frame = frame.shape[0], frame.shape[1]
    direita = regiao.esquerda + regiao.largura
    base = regiao.topo + regiao.altura
    if (
        regiao.esquerda < 0
        or regiao.topo < 0
        or regiao.largura <= 0
        or regiao.altura <= 0
        or direita > largura_do_frame
        or base > altura_do_frame
    ):
        return _recusar(
            campo,
            MOTIVO_DO_RECORTE_FORA_DO_FRAME,
            f"o retangulo {regiao.esquerda},{regiao.topo} "
            f"{regiao.largura}x{regiao.altura} vai ate "
            f"{direita},{base} e o frame mede "
            f"{largura_do_frame}x{altura_do_frame}. numpy encurtaria a fatia "
            f"EM SILENCIO e a leitura sairia plausivel e errada",
        )

    return frame[
        regiao.topo : base,
        regiao.esquerda : direita,
    ]


# ---------------------------------------------------------------------------
# A GRAMATICA DO EXP -- irma de `mercado_leitura`, e NAO uma parametrizacao dela
# ---------------------------------------------------------------------------
#
# POR QUE A FUNCAO DE MOEDA DO MERCADO NAO E REUSADA. A irma dela naquele modulo
# (a que converte `100,00` em 10000) trava em DUAS casas decimais e EXIGE
# virgula. Medido por execucao na pesquisa desta fase, ela devolve nada para as
# DUAS grafias do EXP: `8.0012%` tem ponto e quatro casas, `8,0012%` tem quatro
# casas. Nao ha parametro que as una sem afrouxar a trava de duas casas, que e
# justamente o que faz aquela funcao derrubar uma linha em vez de inventar um
# numero plausivel. Duas travas apertadas valem mais que uma trava frouxa
# reusada, e a FORMA e o que se copia daqui — nunca a chamada.
#
# O SEPARADOR ENTRA COMO CLASSE DE CARACTERE E NAO COMO CARACTERE, e a razao e
# medida: o jogo escreve o decimal com PONTO num campo e o milhar com PONTO em
# outro, e o OCR do Windows devolveu VIRGULA para os dois em leituras reais
# desta arvore. Quem decide o significado e a CONTAGEM de digitos depois do
# separador, nunca o caractere.
#
# A ANCORA SAO OS QUATRO DIGITOS IMEDIATAMENTE ANTES DO SINAL DE PORCENTAGEM, e
# nunca "o primeiro numero com porcentagem". A MESMA barra carrega um segundo
# campo com sinal de porcentagem — o bonus, medido em `592%` na Faerlina e
# `612%` na Yazalaque —, e uma expressao que pegasse o primeiro numero com `%`
# leria o bonus como se fosse o EXP.
#
# E ELA E ANCORADA DOS DOIS LADOS, o que nao era obvio e custou um numero
# fabricado. Sem o `(?<!\d)`, a expressao casa DENTRO de um numero maior:
# `1234.5678%` devolvia `2345678`, porque `\d{1,3}` encontrava `234` e o resto
# fechava. Isso nao e uma entrada inventada — o OCR desta arvore cola numero
# vizinho na frente o tempo todo (`76 EXP 80012% 592%` e leitura real de
# campo), e o EXP e uma fracao de nivel que nunca passa de 100 pontos
# percentuais: quatro digitos na parte inteira NAO sao um EXP, e recortar os
# tres ultimos para caber e fabricar leitura.
#
# O `(?![\d.,])` fecha o outro lado pelo mesmo motivo: sem ele, um separador ou
# digito depois do `%` indicaria que a leitura continua e que a fatia casada
# nao e o campo inteiro.
_EXP_DA_BARRA = re.compile(r"(?<!\d)(\d{1,3})[.,](\d{4})%(?![\d.,])")

# 100,0000% cabe em seis digitos significativos, e o EXP e uma fracao de nivel:
# ele nunca passa de 100 pontos percentuais.
DECIMOS_DE_MILESIMO_POR_PONTO = 10_000


def decimos_de_milesimo(texto: str | None) -> int | None:
    """`8,0012%` -> 80012. `None` para tudo que nao respeita a gramatica.

    A GRAMATICA E UMA TRAVA DE VALIDACAO, E NAO SO UMA REGRA DE PARSING. Um
    digito perdido pelo OCR produz `8,001%` ou `8,00123%`, que violam a regra e
    derrubam a leitura — em vez de virar um numero plausivel e errado.

    TRES CASAS, CINCO CASAS OU AUSENCIA DO SINAL DE PORCENTAGEM SAO RECUSA, E
    NUNCA ARREDONDAMENTO E NUNCA COMPLETAR COM ZERO. Um EXP de duas casas
    tratado como se tivesse quatro e uma mentira que ninguem consegue ver
    depois de gravada: `8,00%` completado com zero vira `80000`, que e um valor
    perfeitamente formatado e a quase mil vezes de distancia do certo.

    A unidade e o DECIMO DE MILESIMO de ponto percentual, inteiro, no
    precedente de `total_em_centesimos`. Nunca `float`.
    """
    if not texto:
        return None
    candidatos = {
        int(inteiro) * DECIMOS_DE_MILESIMO_POR_PONTO + int(decimal)
        for inteiro, decimal in _EXP_DA_BARRA.findall(texto)
    }
    if len(candidatos) != 1:
        # ZERO e nao ha o que ler. MAIS DE UM e AMBIGUIDADE, e ela recusa em vez
        # de escolher: pegar o primeiro seria uma decisao tomada pela ordem em
        # que o motor de OCR devolveu as palavras, e essa ordem nao e informacao
        # sobre a tela. O MESMO valor repetido nao e ambiguidade — por isso o
        # conjunto, e nao a lista.
        return None
    return candidatos.pop()


def _cruzar_as_escalas(
    campo: str, leituras: list[tuple[str | None, int | None]]
) -> ValorDaRenda | RecusaDaRenda:
    """Os quatro desfechos do cruzamento. ABSTENCAO NAO E DISCORDANCIA.

    POR QUE EXISTE CRUZAMENTO. Em um frame real desta arvore, dois caminhos de
    leitura dos MESMOS pixels discordaram num digito da segunda casa decimal:
    `57.6499%` contra `57.8499%` (M6, gravacao
    `mercado-farm-com-party/frame_000000`). Sem cruzamento, um dos dois teria
    virado numero gravado — e depois de gravado um numero errado e
    indistinguivel de um certo.

    POR QUE O PAR E 2x x 3x. A escala mais baixa nao tem entrada publica neste
    projeto e ABSTEM por medicao documentada no proprio modulo de OCR: ela le
    `MOninutes` e a guarda estrutural devolve nada, deterministicamente.

    POR QUE A REGRA E ABSTENCAO E NAO IGUALDADE -- E ESTE PARAGRAFO CORRIGE UMA
    DECISAO TRAVADA. O texto original era "as duas leituras tem que dar o mesmo
    numero; divergiram -> recusa". Medido em campo com as duas instancias vivas
    (M-D, `01-MEDICOES-DE-CAMPO.md`), as duas escalas quase nunca CONCORDAM —
    elas se REVEZAM. O nivel da Faerlina so sai na 3x, com a 2x devolvendo
    vazio em TODA a banda util. Com a regra antiga aquele campo seria recusado
    PARA SEMPRE, e recusar 100% das amostras e o mesmo que nao ter medidor. A
    regra que vale e a que o proprio modulo de OCR ja documenta para a escala
    mais baixa: abstencao nao e discordancia.

    E O CUSTO FOI COBRADO, MEDIDO, NUM CAMPO -- ENTAO ELE VAI ESCRITO AQUI. O
    Adendo de `01-MEDICOES-DE-CAMPO.md` mediu esta regra contra a ADENA e ela
    ACEITOU NUMERO ERRADO: `106020` no lugar de `1.696.020` e `91` no lugar de
    `13.160.684`, os dois gramaticalmente validos, plausiveis, e errados por
    seis ordens de grandeza (M-G). E exigir concordancia tambem nao salvava
    aquele campo: em 173 concordancias da Faerlina, as 173 estavam erradas —
    todas liam a L-Coin (M-H).

    ONDE A REGRA SERVE E ONDE ELA PERDEU, nomeados, para que ninguem a aplique
    de novo no mesmo lugar:

    - ela continua CORRETA E OBRIGATORIA para o EXP e para o nivel, porque a
      alternativa recusaria os dois para sempre;
    - ela FALHOU na adena, e a razao nao e da regra: e do campo. A adena tem um
      SOSIA GRAMATICAL ADJACENTE — a L-Coin passa na gramatica de milhar
      inteira —, e um cruzamento entre duas leituras do MESMO pixel nao tem
      como distinguir "leu o campo certo errado" de "leu o campo do lado
      certo". Nenhuma regra sobre DUAS LEITURAS resolve um problema de QUAL
      CAMPO. Por isso a adena saiu do OCR, e nao por isso a regra saiu do
      projeto.

    Quem for afrouxa-la ou aperta-la de novo tem de responder ao M-G e ao M-H,
    e nao apenas ao M-D.

    OS QUATRO DESFECHOS:

    ===========================  =======================================
    leituras de gramatica valida desfecho
    ===========================  =======================================
    zero, todas com texto vazio  RECUSA por CAMPO VAZIO
    zero, alguma com texto       RECUSA por GRAMATICA
    exatamente uma               ACEITA, `escalas = 1` -- o caso COMUM
    duas ou mais, e iguais       ACEITA, `escalas = 2`
    duas ou mais, e diferentes   RECUSA por DISCORDANCIA
    ===========================  =======================================

    SER FUNCAO PURA E SEPARADA NAO E ORGANIZACAO: e o que permite os quatro
    desfechos serem testados sem OCR nenhum, com pares montados a mao —
    inclusive os dois que a medicao de campo produziu de verdade.
    """
    validas = [(texto, valor) for texto, valor in leituras if valor is not None]
    cruas = " ".join(entre_delimitadores(texto) for texto, _ in leituras)

    if not validas:
        tudo_vazio = all(not (texto or "").strip() for texto, _ in leituras)
        if tudo_vazio:
            return _recusar(
                campo,
                MOTIVO_DO_CAMPO_VAZIO,
                f"as {len(leituras)} escalas devolveram texto vazio: {cruas}",
            )
        return _recusar(
            campo,
            MOTIVO_DA_GRAMATICA,
            f"nenhuma das {len(leituras)} escalas respeita a forma do campo: "
            f"{cruas}",
        )

    distintos = {valor for _, valor in validas}
    if len(distintos) > 1:
        return _recusar(
            campo,
            MOTIVO_DA_DISCORDANCIA,
            f"as escalas leram numeros DIFERENTES ({sorted(distintos)}): "
            f"{cruas}",
        )

    texto, valor = validas[0]
    return ValorDaRenda(
        campo=campo, valor=valor, escalas=len(validas), texto=texto or ""
    )


def exp_da_barra(
    recorte: np.ndarray, *, piso_de_brilho: int
) -> ValorDaRenda | RecusaDaRenda:
    """O EXP do recorte da barra, em decimos de milesimo. Ou RECUSA NOMEADA.

    A MASCARA E OBRIGATORIA, E NAO UMA MELHORA. Medido (M4/M5): no recorte CRU
    de `adena-diagnostico/frame_000005` o EXP simplesmente SOME — as duas
    escalas devolvem `845%' 126` e `120` —, e com a mascara no piso certo o
    mesmo recorte devolve `EXP 58.8189%`. E medido de novo em campo (M-E), com
    fundo de grama clara atras da barra semitransparente, o cru devolve texto
    vazio nas duas escalas.

    O PISO VEM POR PARAMETRO SOMENTE-NOMEADO E SEM DEFAULT, pela regra escrita
    no charter do modulo puro do mercado: um default e um numero magico que
    entra por omissao. Aqui ele seria pior, porque nao existe piso unico —
    existe um por regiao (M-E).

    AS DUAS ESCALAS RODAM SEMPRE, E ISTO CORRIGE O DESENHO ANTERIOR. Ele era
    "le na barata, e so paga a cara se a barata passar na gramatica" — a ordem
    que o modulo de manutencao estabeleceu. Medido em campo (M-D), essa ordem
    CALA metade dos campos: o nivel da Faerlina so sai na 3x, porque a 2x
    devolve vazio em toda a banda util, e um curto-circuito na barata nunca
    chegaria a perguntar a cara. O custo esta orcado na tabela do proprio
    modulo de OCR: recortes deste tamanho custam dezenas de milissegundos numa
    leitura que acontece uma vez por tick.
    """
    if recorte is None or getattr(recorte, "size", 0) == 0:
        return _recusar(
            CAMPO_DO_EXP,
            MOTIVO_DO_CAMPO_VAZIO,
            "o recorte chegou vazio; nao ha pixel para ler",
        )

    # A mascara de brilho sai em 0/1 (e um `uint8` logico); o motor de OCR
    # espera tinta visivel, entao ela vira 0/255. Sem isso o recorte inteiro
    # chega quase preto e as duas escalas abstem — que seria uma recusa por
    # campo vazio apontando para o lugar errado.
    tinta = (mascara_de_numero(recorte, int(piso_de_brilho)) * 255).astype(np.uint8)

    leituras = [
        (texto, decimos_de_milesimo(texto))
        for texto in (ler_texto(tinta), ler_texto_ampliado(tinta))
    ]
    return _cruzar_as_escalas(CAMPO_DO_EXP, leituras)


# ---------------------------------------------------------------------------
# A PENEIRA DE FORMA -- UMA SO nesta fase, e ela mora AQUI, no modulo puro
# ---------------------------------------------------------------------------
#
# POR QUE ELA NAO MORA NO CORTADOR. O cortador de moldes precisa dela para
# fatiar, e o leitor da adena precisa dela para ler. Se o corte dos moldes e a
# leitura peneirassem corridas por regras DIFERENTES, os moldes seriam cortados
# de um conjunto de corridas e lidos de outro -- e o desalinhamento nao
# apareceria como erro, apareceria como PONTUACAO BAIXA, que e a forma de
# defeito que alguem "conserta" baixando o piso de leitura. Trocar um defeito
# visivel por um invisivel e o unico jeito de piorar este projeto.
#
# E a seta desta casa aponta FERRAMENTA -> PURO. Se ela morasse na ferramenta,
# `renda_leitura` teria de importar um calibrador -- e com ele `argparse`, a
# consciencia de DPI no import e as chamadas de janela do OpenCV -- so para ler
# um numero dentro do tick de captura.
#
# A CONVENCAO DE LARGURA E EXCLUSIVA (`fim - inicio`), E ELA ESTA DECLARADA
# =========================================================================
# E a convencao de `segmentar_glifos_no_brilho` e de `larguras_de_molde`, e
# portanto a unica em que `limite_de_glifo_unico` significa alguma coisa. O
# `01-MEDICOES-DE-CAMPO.md` relata os MESMOS runs numa convencao INCLUSIVA
# (`fim - inicio + 1`), e as duas diferem por UM pixel (M-P):
#
#     elemento          aqui (exclusiva)      no documento (inclusiva)
#     digito                4, 5, 6                  5, 6, 7
#     virgula                  1                        2
#     icone de ponta        14, 15                   15, 16
#
# Uma peneira escrita com os numeros do documento, rodando nesta convencao,
# RECUSA o digito mais largo e ACEITA um icone estreito -- e o modo de falha e
# silencioso nos dois sentidos. Foi exatamente um numero sem convencao
# declarada (o "17" do M-I) que ja produziu uma refutacao nesta fase.


#: Quantos glifos da largura MAXIMA cabem num run antes de ele deixar de poder
#: ser um simbolo so.
#:
#: MEDIDO (M-O e M-P, nesta convencao exclusiva): o simbolo mais largo que a
#: barra desenha numa posicao -- o icone de moeda das pontas -- mede 14 ou 15
#: colunas contra um limite de glifo unico de 6. Isso e DOIS glifos de largura
#: maxima, e nao mais. Um run que caberia TRES ou mais nao e simbolo nenhum: e
#: o campo colado pela mascara, e o caso esta medido -- o EXP da Yazalaque, em
#: piso alto e recorte largo, cola tudo num run unico de 141 colunas porque a
#: barra verde de progresso entra na mascara (M-L).
#:
#: ELE E UMA CONTAGEM DE GLIFOS, E NAO UMA GEOMETRIA. Ele nao muda se a fonte
#: mudar de tamanho, porque e medido em unidades do `limite` que chega por
#: parametro -- e o `limite` continua saindo dos moldes que um humano cortou.
#: Nenhum pixel desta fonte entra aqui como constante.
SIMBOLOS_POR_RUN_ANORMAL = 3

#: O recorte precisa de um icone em cada ponta MAIS ao menos um glifo no meio.
CORRIDAS_MINIMAS_DE_UM_NUMERO = 3

MOTIVO_DA_FORMA = "forma-do-recorte"
MOTIVO_DO_RUN_ANORMAL = "run-anormalmente-largo"


@dataclass(frozen=True)
class GlifosDoNumero:
    """As corridas do NUMERO, sem os icones, e a faixa recomputada sobre elas.

    `faixa` NAO e a que `segmentar_glifos_no_brilho` devolveu: e a que sobra
    depois de os icones sairem. A diferenca e o achado M-K inteiro -- ver
    `_glifos_do_numero`.
    """

    faixa: tuple[int, int]
    runs: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class RecusaDeForma:
    """Um recorte que NAO contem exatamente um numero, e por que.

    ELA NAO CARREGA `campo`, DE PROPOSITO, e isso e o contrario de esquecimento:
    a peneira nao sabe se esta olhando a adena, a L-Coin, o bonus ou o EXP --
    ela olha corridas. Quem sabe o campo e quem chamou, e e ele que embrulha
    esta recusa numa `RecusaDaRenda` com o nome certo. Uma peneira que exigisse
    o nome do campo so poderia ser usada por quem tem campo, e o cortador de
    moldes varre os QUATRO.
    """

    motivo: str
    detalhe: str


def _glifos_do_numero(
    mascara: np.ndarray,
    faixa: tuple[int, int] | None,
    runs: list[tuple[int, int]],
    *,
    limite: int | None,
) -> GlifosDoNumero | RecusaDeForma:
    """As corridas do numero entre os dois icones, ou RECUSA NOMEADA.

    AS TRES REGRAS DE FORMA, NESTA ORDEM, COM O NUMERO MEDIDO AO LADO DE CADA:

    1. **Um run largo em cada PONTA e icone, e sai.** Medido (M-J/M-O, na
       convencao exclusiva): `[14, 4, 4, 1, 4, 4, 4, 1, 4, 4, 6, 15]` -- icone,
       digitos de 4 a 6, virgulas de 1, icone. O limite vem de
       `limite_de_glifo_unico(moldes)`, DERIVADO dos moldes e nunca gravado: a
       docstring daquela funcao escreve por que gravar a copia criaria DUAS
       VERDADES sobre uma so geometria, e por que a copia envelheceria contra
       os moldes que ela descreve.
    2. **Um run largo no MEIO nao e descartado: ele derruba o recorte**, com o
       motivo nomeado. Descartar ali apagaria um digito e devolveria um numero
       mais curto e PLAUSIVEL -- e numero plausivel e errado e exatamente o que
       esta fase existe para nao produzir. O caso e medido: o recorte
       `1500,1360 200x32` pega a cauda da L-Coin, o icone da moeda de ouro e so
       entao a adena, produzindo um run largo no meio nas QUATRO fixturas
       (M-N, reconferido em M-Q).
    3. **Exatamente um run largo em cada ponta, ou recusa de forma.** Zero ou
       dois significam que o recorte deixou de conter exatamente um numero.

    E A QUARTA REGRA, QUE E A RAZAO DE ESTA FUNCAO DEVOLVER A FAIXA E NAO SO OS
    RUNS. `segmentar_glifos_no_brilho` devolve UMA faixa de linhas para o
    retangulo inteiro -- e decisao de projeto dela, documentada, porque e a
    posicao vertical relativa que distingue a virgula (baixa) do digito (altura
    cheia). Foi essa decisao, com um icone DENTRO do recorte, que produziu a
    altura 17 do M-I sobre uma fonte de altura 10. Entao a faixa e RECOMPUTADA
    sobre as colunas SOBREVIVENTES ao descarte, e e essa que sai.

    A medicao, porque quem ler vai achar que e zelo: sobre a L-Coin sem icone a
    faixa e `(17, 26)`, altura 10, nas duas instancias; sobre o mesmo campo com
    o icone dentro, a faixa unica da 17; e em `1560:1690` basta um run de
    largura 9 no fim para esticar de 10 para 17 (M-K). Medir a altura ANTES do
    descarte e reproduzir por dentro o defeito que esta funcao existe para nao
    repetir -- e a consequencia tem nome: uma guarda de altura calibrada contra
    17 recusaria TODO molde legitimo desta barra, e o modo de falha seria um
    cortador que roda, sai com codigo 0 e nunca corta nada.

    E OS DOIS NUMEROS DO M-K TAMBEM ESTAO NA CONVENCAO INCLUSIVA -- MEDIDO AQUI,
    E ESTA E A TERCEIRA VEZ QUE UM PIXEL DE CONVENCAO MORDE ESTA FASE. O M-P
    pegou a divergencia nas LARGURAS de run; ela vale igual para a ALTURA da
    faixa. Reconferido sobre as QUATRO fixturas versionadas de campo
    (`tests/fixtures/renda/*__barra_direita.png`), nos pisos 180, 185 e 190, com
    esta funcao e com `segmentar_glifos_no_brilho`:

        faixa bruta      (com os icones dentro)  -> 16, invariavel nas 12 medicoes
        faixa peneirada  (depois do descarte)    ->  9, invariavel nas 12 medicoes

    Sao os MESMOS pixels que o M-K chamou de 17 e 10. `faixa[1] - faixa[0]` da
    16 e 9; contados de forma inclusiva, 17 e 10. O comportamento medido do
    descarte -- a faixa encolhendo do icone para a fonte -- e exatamente o que o
    M-K descreve, e e ele que importa.

    NADA AQUI DEPENDE DO VALOR, E ESSE E O PONTO. Esta funcao nao compara altura
    com numero nenhum: ela RECOMPUTA e devolve. Quem compara e a guarda do
    cortador, e ela compara contra a altura DOMINANTE dos moldes ja gravados.
    Por isso a correcao custou uma docstring e nao uma reescrita -- e por isso
    ela e escrita em vez de o numero ser trocado em silencio.

    A GUARDA DO RUN ANORMALMENTE LARGO, E ELA E MEDIDA E NAO IMAGINADA. Um run
    que caberia `SIMBOLOS_POR_RUN_ANORMAL` glifos de largura maxima e recusado
    com a largura NOMEADA, e nunca fatiado. A aritmetica e o argumento inteiro:
    os 141 px que o M-L mediu no EXP da Yazalaque -- onde a barra verde de
    progresso entra na mascara e cola o campo -- fatiados em glifos desta fonte
    dariam VINTE E OITO digitos que nunca estiveram na tela. `folga_de_cola`
    nasce `null` no `01-01` justamente para que `particionar_run` nao seja
    chamado aqui; esta guarda e o cinto sobre o suspensorio.

    A guarda so olha o MIOLO quando ha miolo: com tres runs ou mais, as duas
    pontas ficam de fora dela, porque um icone de ponta e largo POR DESENHO e
    uma anomalia apertada demais o transformaria em recusa -- o cortador nunca
    cortaria nada, o mesmo modo de falha da guarda contra 17. Com menos de tres
    runs nao ha ponta a preservar, e e ai que o run colado aparece.

    `limite` e SOMENTE-NOMEADO E SEM DEFAULT. Um default seria geometria desta
    fonte entrando por omissao, e a geometria desta fonte sai de moldes que um
    humano confirmou. `limite=None` -- o que `limite_de_glifo_unico` devolve
    sobre um conjunto vazio -- RECUSA com o motivo nomeado, em vez de adivinhar.

    A funcao e PURA: sem disco, sem OCR, sem relogio, sem janela.
    """
    if limite is None or int(limite) <= 0:
        return RecusaDeForma(
            MOTIVO_DA_FORMA,
            "o limite de glifo unico nao foi derivado dos moldes "
            f"(recebido: {limite!r}). Sem moldes nao ha como saber qual "
            "corrida e icone e qual e digito, e adivinhar aqui seria inventar "
            "a geometria que o conjunto de moldes existe para carregar",
        )
    limite = int(limite)

    if mascara is None or getattr(mascara, "size", 0) == 0:
        return RecusaDeForma(
            MOTIVO_DA_FORMA,
            "a mascara chegou vazia; nao ha coluna para peneirar",
        )

    corridas = [(int(inicio), int(fim)) for inicio, fim in (runs or [])]
    larguras = [fim - inicio for inicio, fim in corridas]
    if not corridas:
        return RecusaDeForma(
            MOTIVO_DA_FORMA,
            "o recorte nao tem corrida nenhuma acima do piso de brilho: ou o "
            "piso apagou o campo, ou o retangulo esta apontando para outro "
            "lugar da tela",
        )

    # A ANOMALIA VEM ANTES DA FORMA, e a ordem importa: um campo colado num run
    # so tambem falharia a regra 3, mas com uma mensagem que mandaria o usuario
    # mexer no retangulo HORIZONTAL, e o conserto medido e VERTICAL.
    anormal = SIMBOLOS_POR_RUN_ANORMAL * limite
    if len(corridas) >= CORRIDAS_MINIMAS_DE_UM_NUMERO:
        suspeitas = range(1, len(corridas) - 1)
    else:
        suspeitas = range(len(corridas))
    for i in suspeitas:
        if larguras[i] >= anormal:
            return RecusaDeForma(
                MOTIVO_DO_RUN_ANORMAL,
                f"a corrida {i} mede {larguras[i]} colunas, e um simbolo desta "
                f"barra cabe em menos de {anormal} ({SIMBOLOS_POR_RUN_ANORMAL}x "
                f"o limite de glifo unico {limite}). A causa medida e a BARRA "
                "VERDE de progresso entrando na mascara e colando o campo "
                "inteiro (M-L). Ela NAO e fatiada: caberiam ate "
                f"{larguras[i] // limite} glifos, e nenhum deles esteve na "
                "tela. O conserto e apertar o recorte VERTICAL ate sobrar so a "
                "linha do texto, ou subir o piso de brilho",
            )

    if len(corridas) < CORRIDAS_MINIMAS_DE_UM_NUMERO:
        return RecusaDeForma(
            MOTIVO_DA_FORMA,
            f"o recorte tem {len(corridas)} corrida(s) ({larguras}), e um "
            "numero desta barra precisa de um icone em cada PONTA mais ao "
            "menos um glifo no meio",
        )

    ultima = len(corridas) - 1
    largas = [i for i, w in enumerate(larguras) if w > limite]
    pontas_largas = [i for i in largas if i in (0, ultima)]
    if len(pontas_largas) != 2:
        return RecusaDeForma(
            MOTIVO_DA_FORMA,
            f"o recorte tem {len(pontas_largas)} corrida(s) larga(s) nas "
            f"PONTAS e precisa de exatamente uma em cada ({larguras}, limite "
            f"{limite}). Zero ou duas significam que o recorte deixou de "
            "conter exatamente um numero: ele comeca ou termina no meio de "
            "outra coisa",
        )

    do_meio = [i for i in largas if i not in (0, ultima)]
    if do_meio:
        vizinhas_da_ponta = [i for i in do_meio if i in (1, ultima - 1)]
        onde = (
            "coladas numa PONTA -- o recorte pegou o campo vizinho junto"
            if vizinhas_da_ponta
            else "no MEIO do numero"
        )
        return RecusaDeForma(
            MOTIVO_DA_FORMA,
            f"ha corrida(s) larga(s) {onde}: indices {do_meio}, larguras "
            f"{[larguras[i] for i in do_meio]} contra o limite {limite} "
            f"({larguras}). Elas NAO sao descartadas: descartar uma corrida "
            "larga que nao esta numa ponta apagaria um digito e devolveria um "
            "numero mais curto e plausivel",
        )

    miolo = corridas[1:ultima]

    # A FAIXA, RECOMPUTADA SOBRE AS COLUNAS SOBREVIVENTES. Este e o M-K virado
    # codigo: a faixa que ENTROU pode carregar a altura do icone, e a que SAI
    # carrega a da fonte.
    colunas = np.zeros(int(np.asarray(mascara).shape[1]), dtype=bool)
    for inicio, fim in miolo:
        colunas[inicio:fim] = True
    linhas = np.flatnonzero(np.asarray(mascara)[:, colunas].any(axis=1))
    if linhas.size == 0:
        return RecusaDeForma(
            MOTIVO_DA_FORMA,
            "as corridas do meio nao tem pixel nenhum depois do descarte dos "
            f"icones (faixa bruta {faixa}); o recorte so continha os icones",
        )

    return GlifosDoNumero(
        faixa=(int(linhas[0]), int(linhas[-1]) + 1),
        runs=tuple(miolo),
    )


# ---------------------------------------------------------------------------
# DE ONDE SAI O `limite` DA PENEIRA -- E ELE NUNCA E UM NUMERO ESCRITO AQUI
# ---------------------------------------------------------------------------
#
# POR QUE ESTAS DUAS FUNCOES MORAM NO MODULO PURO, AO LADO DA PENEIRA. Elas
# nasceram dentro do cortador de moldes (`calibrar_renda_moldes`, do `01-05`),
# que era o unico consumidor da peneira. Ele deixou de ser: o calibrador de
# PISOS (`calibrar_renda`, do `01-03`) tambem classifica a barra pela forma, e
# precisa exatamente do mesmo limite pela mesma razao.
#
# Copiar `limite_de_arranque` para o segundo calibrador teria criado DUAS
# regras de arranque para uma so fonte -- a mesma familia de defeito que
# `_glifos_do_numero` existe para nao ter, uma peca abaixo. E importar um
# calibrador do outro esta proibido por desenho: os dois nao se conhecem, nao
# dividem arquivo, e a ligacao entre eles passa pelo disco. A saida que
# respeita as duas coisas e a que esta feita aqui: a regra desce para o modulo
# PURO, que os dois ja importam, e continua existindo UMA VEZ. As setas
# continuam ferramenta -> puro.

#: O limite veio dos moldes que um humano ja confirmou. E o caso maduro.
LIMITE_VEIO_DOS_MOLDES = "moldes"

#: O limite foi medido no proprio recorte, porque nao ha molde nenhum ainda.
LIMITE_VEIO_DO_ARRANQUE = "arranque"


def limite_de_arranque(runs) -> int | None:
    """O limite de glifo unico da PRIMEIRA rodada, quando nao ha molde nenhum.

    POR QUE ELE PRECISA EXISTIR. `limite_de_glifo_unico({})` devolve `None` -- e
    esta certo, porque sem molde nao ha geometria gravada. Mas a primeira
    rodada tambem precisa fatiar, e e justamente ela que faz o primeiro molde
    nascer. Sem um limite de arranque a ferramenta nunca sairia do zero: um
    cortador que exige moldes para cortar moldes. E o calibrador de PISOS tem a
    mesma necessidade pelo mesmo motivo -- a primeira rodada de todo usuario e
    sem moldes, e uma banda vazia ali o faria concluir que a adena nao tem piso
    nenhum.

    DE ONDE ELE VEM, E ELE E ANUNCIADO. Medido nas quatro fixturas: os icones
    sao as duas corridas das PONTAS, e sao as mais largas do recorte. Entao o
    arranque e a maior largura que NAO esta numa ponta. Nas quatro fixturas
    isso da 6, 4, 6 e 6 -- e em todas as quatro o descarte posicional sai igual.

    E O PONTO CEGO DELE VAI ESCRITO, porque ele e real: num recorte que tenha
    um icone NO MEIO (o caso do M-N), o arranque adotaria a largura DAQUELE
    icone e a peneira o aceitaria como digito. Isso nao passa em silencio -- o
    rotulo daquele recorte vai para o olho humano ampliado, e o que ele veria e
    lixo. Assim que o primeiro molde existir, o limite passa a sair dos moldes.

    MEDIDO DE NOVO NO `01-03`, E O PONTO CEGO TEM UM SEGUNDO ROSTO: num piso
    BAIXO demais, glifos vizinhos colam e o arranque adota a largura do PAR
    colado. Sobre as cinco fixturas de `barra_direita`, varridas de 5 em 5, os
    pisos abaixo de 176 sao aceitos pela forma com arranque 10, 11 ou 12 e com
    uma corrida A MENOS do que o numero tem caracteres. O centro da banda
    contigua e o que salva a escolha -- nas cinco fixturas ele caiu em 181 ou
    186, dentro da banda de glifo medida em campo (180-190, M-J).
    """
    corridas = list(runs or [])
    if len(corridas) < CORRIDAS_MINIMAS_DE_UM_NUMERO:
        return None
    do_meio = [int(fim) - int(inicio) for inicio, fim in corridas[1:-1]]
    if not do_meio:
        return None
    return max(do_meio)


def resolver_o_limite_de_glifo(moldes, runs) -> tuple[int | None, str]:
    """`(limite, de onde ele veio)`. Os moldes mandam; o arranque destrava.

    A ORIGEM SAI JUNTO, E ISSO E O ACHADO M-U VIRADO ASSINATURA. O limite dos
    moldes e DERIVADO do conjunto ja cortado, entao um conjunto incompleto
    produz um limite ESTREITO -- e a peneira recusa o recorte CERTO com uma
    mensagem que culpa o RETANGULO ("o recorte pegou o campo vizinho junto").

    Medido na rodada de moldes de 2026-09-02 (M-U): em ordem alfabetica o
    primeiro recorte e `2.207.577`, cujos digitos sao todos de largura 4
    (convencao exclusiva). O limite trava em 4 e os tres recortes seguintes sao
    recusados, porque `4`, `8` e `9` medem 5 e 6 -- cinco rotulos de onze.
    Reconferido pelo `01-03` do outro lado, com o limite preso em 4 sobre as
    CINCO fixturas de `barra_direita`: duas delas ficam com a banda de forma
    INTEIRAMENTE VAZIA, e as recusas dos pisos 181, 186 e 191 mandam remarcar
    um retangulo que esta correto.

    Quem receber esta tupla e responsavel por NAO repetir a atribuicao errada:
    quando a origem e `LIMITE_VEIO_DOS_MOLDES` e o arranque medido no proprio
    recorte e MAIOR que ela, o retangulo nao e o suspeito -- o limite herdado
    e. Essa comparacao e o discriminador, e ela e derivada dos dois lados:
    nenhum numero desta fonte precisa ser escrito para faze-la.
    """
    dos_moldes = limite_de_glifo_unico(moldes or {})
    if dos_moldes is not None:
        return int(dos_moldes), LIMITE_VEIO_DOS_MOLDES
    return limite_de_arranque(runs), LIMITE_VEIO_DO_ARRANQUE
