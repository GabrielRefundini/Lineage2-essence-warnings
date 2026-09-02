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
from .mercado_leitura import mascara_de_numero
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
