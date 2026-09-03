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
from types import MappingProxyType

import numpy as np

from .frames import Regiao
from .mercado_leitura import (
    GLIFOS_DO_NUMERO,
    conjunto_descreve_numeros,
    inteiro_de_quantidade,
    ler_glifos,
    limite_de_glifo_unico,
    mascara_de_numero,
    numero_valido,
    segmentar_glifos_no_brilho,
)
from .mercado_visao import glifos_de_calibracao
from .ocr import ler_texto, ler_texto_ampliado

log = logging.getLogger(__name__)

# OS NOMES DOS CAMPOS, e os dois primeiros carregam a mesma mentira que as
# sub-chaves do `calibration.json`: `barra_esquerda` e o EXP e `barra_direita` e
# a ADENA. A mentira fica ESCRITA em vez de consertada em silencio — quem
# renomear renomeia as duas, num commit proprio.
CAMPO_DO_EXP = "exp"
CAMPO_DO_NIVEL = "nivel"
CAMPO_DA_ADENA = "adena"

#: A ORDEM EM QUE OS CAMPOS APARECEM NA TELA DO JOGO, e a MESMA em que
#: `ler_a_renda` procura a primeira recusa. Ela vai declarada em vez de
#: implicita para que duas leituras com o mesmo problema produzam sempre a
#: MESMA recusa: uma ordem que dependesse da iteracao de um dicionario faria a
#: mensagem de erro mudar entre duas rodadas identicas.
ORDEM_DOS_CAMPOS = (CAMPO_DO_NIVEL, CAMPO_DO_EXP, CAMPO_DA_ADENA)

# AS SUB-CHAVES DA ENTRADA DO PERSONAGEM, e as duas primeiras MENTEM. A mentira
# esta documentada no bloco de comentario do campo `renda_por_personagem` em
# `calibracao.py`: `barra_esquerda` descreve o EXP e `barra_direita` descreve a
# ADENA — os nomes vem da era em que os recortes eram duas metades de 520 px.
# Elas moram AQUI, num lugar so, porque quem resolve retangulo e piso e este
# modulo; a ferramenta as importa em vez de escrever a segunda copia.
SUBCHAVE_DO_EXP = "barra_esquerda"
SUBCHAVE_DA_ADENA = "barra_direita"
SUBCHAVE_DO_NIVEL = "nivel"

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

# OS DOIS MOTIVOS QUE SO O CAMINHO DE GLIFO PRODUZ, e eles nao existiam no
# `01-01` porque naquela onda a adena ainda ia sair por OCR.
#
#   conjunto-de-moldes   -> o conjunto de moldes da barra esta AUSENTE ou
#                           INCOMPLETO; o conserto e uma rodada do cortador
#                           (`calibrar-renda-moldes.bat`), e nunca mexer no
#                           piso de brilho
#   pontuacao-dos-glifos -> a forma do recorte estava certa e ao menos um glifo
#                           nao passou no piso OU na margem de leitura; a
#                           leitura cai TUDO OU NADA (LEIT-02) em vez de sair
#                           pela metade
#
# Eles sao SEPARADOS dos outros porque os consertos sao separados, e o custo de
# fundi-los tem tamanho medido: um usuario que visse "gramatica" no lugar de
# "conjunto incompleto" passaria a noite mexendo no piso de brilho quando o que
# falta e rodar o cortador apontando outro campo da barra.
MOTIVO_DO_CONJUNTO_DE_MOLDES = "conjunto-de-moldes"
MOTIVO_DA_PONTUACAO = "pontuacao-dos-glifos"

# AS TRES RECUSAS QUE SO EXISTEM QUANDO HA UM PAR. Elas nao respondem sobre um
# frame: elas respondem sobre DUAS leituras, e por isso nenhuma delas pode ser
# produzida pelos leitores acima. Ver `conferir_o_par`.
MOTIVO_DO_EXP_PARA_TRAS = "exp-andou-para-tras"
MOTIVO_DO_NIVEL_PARA_TRAS = "nivel-andou-para-tras"
MOTIVO_DO_SALTO_DA_ADENA = "adena-saltou-ordem-de-grandeza"


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


@dataclass(frozen=True)
class ValorDaAdena:
    """A adena que virou numero, e ela NAO carrega `escalas`. DE PROPOSITO.

    ELA E UMA CLASSE SEPARADA PORQUE AFIRMAR UMA GUARDA INEXISTENTE E O DEFEITO
    QUE O `T-01-43` EXISTE PARA IMPEDIR. `ValorDaRenda.escalas` significa "por
    quantas leituras INDEPENDENTES este numero foi sustentado", e a adena tem
    UM metodo so: ela e lida por GLIFO, e nao ha segunda escala com que cruzar.
    Um `escalas = 1` aqui seria indistinguivel do `escalas = 1` do nivel, que
    significa outra coisa — la a segunda escala existe e ABSTEVE, aqui ela
    nunca existiu.

    O QUE ELA CARREGA NO LUGAR E `glifos`: quantos simbolos a peneira entregou
    a `ler_glifos` depois de os icones das pontas sairem. E o numero que
    descreve a guarda que este campo REALMENTE tem — a de forma —, e ele e
    conferivel contra a tela: `13.160.684` sao dez glifos, oito digitos e duas
    virgulas.
    """

    campo: str
    valor: int
    glifos: int
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

    E AQUI ESTA A CORRECAO QUE O `01-03` MEDIU, PORQUE O PARAGRAFO ACIMA
    ATRIBUIA O MODO DE FALHA SO A UM CAMPO E SO A UMA CAUSA. Ele dizia que a
    regra "continua CORRETA E OBRIGATORIA para o EXP", e que o que quebrou na
    adena foi ter um sosia ADJACENTE. As duas metades estao certas de menos:
    **o EXP tem o mesmo modo de falha, e o sosia nao precisa estar ao lado —
    basta o CORTE fabricar um.**

    A medicao, sobre `tests/fixtures/renda/montagem_da_janela.png`, retangulo
    do EXP `0,1368 520x24`, piso 160, verdade de campo `8,0012%` (`80012`),
    deslocando a borda ESQUERDA do recorte para dentro:

        ate +82   `80012`  certo,  1-2 escalas
        +83       recusa por discordancia entre escalas
        +84       `30012`  ERRADO, 1 escala
        +85       `10012`  ERRADO, 1 escala
        +86       `10012`  ERRADO, **2 escalas -- AS DUAS CONCORDAM**
        +87 e alem  recusa por gramatica

    Ha uma janela de TRES PIXELS em que a leitura fabrica um EXP
    gramaticalmente perfeito e errado, e no `+86` o cruzamento NAO PEGA:
    cortar o primeiro digito transformou `8` em `3` e depois em `1`, e as duas
    escalas leram o mesmo caractere mutilado. O cruzamento e a ultima guarda
    depois da gramatica, e ali ele concorda no erro.

    O QUE ISSO MUDA, E O QUE ISSO NAO MUDA. Nao muda a regra: exigir
    concordancia tambem nao pegaria o `+86`, e recusaria o nivel da Faerlina
    para sempre. Muda ONDE a guarda mora — ela e do RECORTE e nao da leitura.
    O retangulo vem do calibrador, o calibrador desenha a imagem de
    conferencia, e o olho do usuario e quem ve que o `8` esta cortado. A
    janela e estreita (3 px de 520), mas ela cai exatamente onde uma janela
    levemente movida cairia.

    O LIMITE DESTA MEDICAO VAI JUNTO, para ninguem generalizar dela o que ela
    nao mediu: um campo (o EXP), uma fixtura, um piso, e deslocamento so da
    borda ESQUERDA. Nao mede a borda direita, nem o deslocamento vertical, nem
    os outros dois campos.

    Quem for afrouxa-la ou aperta-la de novo tem de responder ao M-G, ao M-H e
    a esta tabela, e nao apenas ao M-D.

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


# O NIVEL -- por OCR MASCARADO, e a refutacao dos moldes vai escrita aqui
# ---------------------------------------------------------------------------
#
# POR QUE O NIVEL NAO E LIDO POR GLIFO, COM A MEDICAO AO LADO, como o
# `ROADMAP.md` exige de todo numero que caiu. O caminho de glifo desta fase
# exige um conjunto COMPLETO -- `conjunto_descreve_numeros` pede os onze
# rotulos, e a docstring dela mede por que meio conjunto falha ABERTO. Mas os
# moldes de um conjunto sao CORTADOS da tela do proprio usuario, e a regiao do
# nivel exibe DOIS caracteres que mudam uma vez por sessao de farm: nunca
# havera, naquele retangulo, de onde cortar os dez digitos.
#
# Nao e caro: e IMPRATICAVEL, que e outra coisa. Um cortador apontado para o
# nivel colheria `6` e `7` numa noite e esperaria semanas pelos outros oito.
#
# E o precedente e desta propria arvore: os moldes de NOME DE ITEM foram
# abandonados em favor de OCR em 2026-08-29, pela mesma razao de conjunto
# aberto -- um catalogo que nao fecha nao vira conjunto.
#
# O QUE O NIVEL GANHA NO LUGAR e o cruzamento das duas escalas, e a razao de
# cruzar esta na docstring de `numero_valido`: a gramatica pega glifo perdido e
# glifo a mais, e NAO pega SUBSTITUICAO. Um nivel de dois digitos com um deles
# trocado (`66` virando `56`, `86` ou `68`) passa em tudo. Contra substituicao
# existem duas defesas nesta arvore -- o cruzamento e a regra de par --, e o
# cruzamento e a que cabe dentro de UMA leitura.
#
# MEDIDO (M20): `numero_valido("6b")` -- a leitura errada que o proprio
# `ROADMAP.md` cita como exemplo para o nivel -- devolve `False`. A defesa mais
# barata deste campo ja sai de graca da validacao que o CTX-2 exige.


def inteiro_do_nivel(texto: str | None) -> int | None:
    """`67` -> 67. `None` para tudo que nao respeita a gramatica.

    AS DUAS FUNCOES DO MERCADO, E NENHUMA DAS DUAS BASTA SOZINHA. Medido (M22)
    com o XM, que e vizinho de recorte da adena: `numero_valido("58,40")` e
    `True` e `inteiro_de_quantidade("58,40")` e `None` -- a primeira aceita e a
    segunda derruba. Uma virgula de milhar perdida faz o caminho contrario:
    `inteiro_de_quantidade("1234")` devolve 1234 e `numero_valido("1234")` e
    `False`. As duas juntas, e nunca uma.

    ELA SERVE OS DOIS CAMPOS QUE NAO SAO O EXP -- o nivel e a adena --, e serve
    porque a gramatica dos dois E A MESMA: um inteiro na grafia de milhar do
    jogo. Uma segunda funcao para a adena seria uma TERCEIRA gramatica de
    milhar nesta arvore, e o `01-04` nao abre nenhuma.

    A VALIDACAO E SOBRE A STRING INTEIRA, E NAO SOBRE UM PEDACO DELA. Um texto
    com um caractere que nao e digito recusa em vez de virar um numero
    truncado: extrair "os digitos que der" de `(37` devolveria `37`, que e um
    nivel plausivel e errado -- e foi exatamente isso que o OCR desta arvore
    devolveu sobre a regiao do nivel da Faerlina no piso vizinho do calibrado.

    O `strip` existe porque o motor de OCR devolve espaco em volta da palavra e
    espaco nao e leitura. Nada mais e removido: um separador ou uma letra no
    meio continuam derrubando.
    """
    if not texto:
        return None
    limpo = texto.strip()
    if not numero_valido(limpo):
        return None
    return inteiro_de_quantidade(limpo)


def nivel_da_regiao(
    recorte: np.ndarray, *, piso_de_brilho: int
) -> ValorDaRenda | RecusaDaRenda:
    """O nivel do recorte da janela de status, como inteiro. Ou RECUSA NOMEADA.

    A FORMA E A DE `exp_da_barra`, E COPIAR A FORMA E O PONTO. Dois leitores de
    OCR com o mesmo desenho -- mascara com o piso da regiao, as duas escalas
    sempre, gramatica travada, cruzamento por abstencao -- sao UMA superficie de
    manutencao. Dois desenhos diferentes seriam duas, e a proxima correcao
    precisaria ser feita nos dois lugares por quem lembrasse dos dois.

    O PISO E O DO NIVEL, E ELE NAO E O DA ADENA NEM O DO EXP. Medido em campo
    (M-E, e virou o LEIT-08): as bandas em que cada regiao sai correta NAO tem
    intersecao. Passar o piso da adena aqui, ou o contrario, nao produz erro --
    produz o campo SUMINDO em silencio, que e uma recusa de campo vazio
    apontando para o lugar errado.

    O CASO DE CAMPO QUE ESTE LEITOR EXISTE PARA NAO RECUSAR: o nivel da
    Faerlina sai `67` na escala 3x com a 2x devolvendo vazio em toda a banda
    util (M-D). Sob a regra antiga do cruzamento -- "as duas tem de concordar"
    -- este campo seria recusado PARA SEMPRE. `_cruzar_as_escalas` decide por
    ABSTENCAO, e o valor sai com `escalas = 1` para que quem exibe possa marcar
    que ali o cruzamento nao esta pegando substituicao.
    """
    if recorte is None or getattr(recorte, "size", 0) == 0:
        return _recusar(
            CAMPO_DO_NIVEL,
            MOTIVO_DO_CAMPO_VAZIO,
            "o recorte chegou vazio; nao ha pixel para ler",
        )

    tinta = (mascara_de_numero(recorte, int(piso_de_brilho)) * 255).astype(np.uint8)
    leituras = [
        (texto, inteiro_do_nivel(texto))
        for texto in (ler_texto(tinta), ler_texto_ampliado(tinta))
    ]
    return _cruzar_as_escalas(CAMPO_DO_NIVEL, leituras)


# ---------------------------------------------------------------------------
# A ADENA -- por GLIFO, e ela SAIU DO OCR por medicao. NAO E UMA PREFERENCIA
# ---------------------------------------------------------------------------
#
# O `ROADMAP.md` e o `LEIT-03` afirmavam: *"o OCR ja devolve a adena do recorte
# cru, sem pre-processamento"*. AS DUAS METADES DA FRASE CAIRAM, em medicoes
# diferentes, e as duas ficam escritas porque uma refutacao apagada volta.
#
# A PRIMEIRA METADE -- "do recorte CRU" -- caiu com o M-E. No spike o fundo
# atras da barra semitransparente estava escuro; em campo, com grama clara
# atras, o recorte cru devolve texto VAZIO nas DUAS escalas. A mascara nao e
# melhora de qualidade: e o que faz o campo existir.
#
# A SEGUNDA METADE -- "o OCR devolve a adena" -- caiu com o M-G e o M-H, sobre
# o recorte JA MASCARADO:
#
#   M-G  varredura de piso de 5 em 5: num piso a Yazalaque le `106020`
#        (verdade 1.696.020) e no piso vizinho a Faerlina le `91` (verdade
#        13.160.684). Os dois passam em `numero_valido`, os dois sao aceitos
#        pela regra de abstencao, e a banda certa tem largura de UM passo.
#   M-H  e exigir que as duas escalas CONCORDEM tambem nao salva: busca
#        exaustiva sobre 4 topos x 4 alturas x 4 esquerdas x 4 direitas x 12
#        pisos produziu 173 concordancias na Faerlina, TODAS erradas, todas
#        lendo `13091` -- a L-COIN.
#
# A CONCLUSAO E ESTRUTURAL E NAO DE AJUSTE: concordancia entre escalas prova
# que as duas leram A MESMA COISA, e a mesma coisa pode ser o campo do lado.
# NENHUMA REGRA SOBRE DUAS LEITURAS RESOLVE UM PROBLEMA DE QUAL CAMPO. A adena
# e o unico campo desta fase com um SOSIA GRAMATICAL ADJACENTE: medido (M18),
# `numero_valido("13,091")` e `True` e `inteiro_de_quantidade("13,091")` e
# `13091` -- a L-Coin passa na gramatica de milhar inteira.
#
# O QUE SUBSTITUI FOI MEDIDO NO MESMO ADENDO (M-J): `segmentar_glifos_no_brilho`
# segmenta a adena PERFEITAMENTE justo onde o OCR devolve vazio, e numa banda
# LARGA em vez da banda de largura 1 do OCR:
#
#     Yazalaque  icone  1,696,020  icone
#     Faerlina   icone  13,160,684  icone
#
# E A ANCORA QUE MORAVA AQUI NAO NASCEU, E A REFUTACAO FICA NO LUGAR DELA.
# `_ultimo_grupo_valido` existia para pescar a adena de DENTRO do texto de OCR
# da barra direita, onde XM, L-Coin e adena chegam numa string so. No caminho
# de glifo o recorte segmenta em `icone | numero | icone` e SO HA UM NUMERO: a
# ancora nao tem o que ancorar, e uma funcao sem chamador e um convite a alguem
# liga-la. MAS A IDEIA DELA SOBREVIVE E MUDOU DE LUGAR: o que distinguia a
# adena do L-Coin era a POSICAO e nunca a forma (M18), e no caminho de glifo
# isso virou a GUARDA DE FORMA DO RUN de `_glifos_do_numero` -- exatamente um
# run largo em cada ponta e nada largo no meio. Caiu a funcao, e nao a medicao.
#
# E ELA CONTINUA NAO SENDO IMUNE A SUBSTITUICAO -- MEDIDO NESTA ARVORE, E VAI
# ESCRITO EM VEZ DE VENDIDO COMO FECHADO. Varrendo a grade de pisos inteira
# sobre as cinco fixturas versionadas, os tres numeros que a medicao de campo
# capturou errados (`106020`, `91` e as duas L-Coins) NUNCA aparecem. Mas
# ABAIXO da banda calibrada aparece outra coisa: num piso baixo a Yazalaque le
# `1,646,020` no lugar de `1,696,020`, um `9` casado como `4` com a gramatica
# inteira satisfeita. A banda em que as cinco fixturas leem certo tem mais de
# vinte pisos de largura e o piso calibrado esta no meio dela; o que defende
# contra o que sobra e a REGRA DE PAR, e nao a peneira de forma.


def _faltantes_do_conjunto(moldes) -> list[str]:
    """Os rotulos que faltam para o conjunto descrever numeros, POR NOME.

    A LISTA SAI DA MESMA FONTE QUE A GUARDA, e isso nao e detalhe:
    `GLIFOS_DO_NUMERO` e o conjunto que `conjunto_descreve_numeros` compara,
    entao a mensagem nunca pode divergir do portao que a produziu. Uma segunda
    lista escrita a mao aqui envelheceria contra a primeira.

    E ELA SAI POR NOME E NUNCA POR CONTAGEM, pela frase que
    `calibrar_mercado.cobertura_dos_glifos` ja escreve: *"faltam 3" nao diz onde
    procurar; "faltam 6, 8" diz*. (Aquela funcao NAO e importada aqui, e a
    proibicao e do charter deste modulo: ela mora num calibrador, e um modulo de
    producao que importasse um calibrador pagaria `argparse` e a consciencia de
    DPI no import so por existir. O que se copia e a disciplina.)
    """
    return sorted(GLIFOS_DO_NUMERO - set(moldes or {}))


def adena_da_barra(
    recorte: np.ndarray,
    *,
    piso_de_brilho: int,
    moldes,
    piso_de_leitura: float,
    margem_de_leitura: float,
    folga_de_cola: int | None,
) -> ValorDaAdena | RecusaDaRenda:
    """A adena do recorte da barra direita, como inteiro. Ou RECUSA NOMEADA.

    ELA NAO CHAMA OCR EM NENHUM CAMINHO, e a razao esta medida no bloco de
    comentario acima (M-G, M-H). Um teste de arvore de sintaxe prende isso: o
    corpo desta funcao nao referencia o motor de texto em lugar nenhum.

    A CADEIA, NESTA ORDEM:

        conjunto completo? -> mascara -> segmentacao NO MESMO PISO ->
        peneira de forma (descarte dos icones POR LARGURA) -> `ler_glifos` ->
        `numero_valido` + `inteiro_de_quantidade`

    A MASCARA E A SEGMENTACAO RECEBEM O MESMO PISO, E ISSO NAO E DETALHE. A
    docstring de `ler_celula` ja escreve por que: segmentar num piso e pontuar
    em outro produz runs apontando para colunas que a mascara nao tem, e o
    casamento le lixo com confianca.

    POR QUE `ler_celula` NAO E REUSADA, APESAR DE SER A COMPOSICAO PRONTA. Ela
    entrega TODOS os runs a `ler_glifos`, e os icones de moeda das pontas sao
    mais de duas vezes mais largos que o limite de glifo unico desta fonte:

    - com `folga_de_cola` em `None` (o valor gravado, e a guarda FECHADA) os
      icones cairiam na guarda de run largo de `ler_glifos` e derrubariam a
      celula INTEIRA: a adena nunca leria, e a recusa culparia a pontuacao;
    - com uma folga inteira seria PIOR: `particionar_run` fatiaria um icone de
      ponta em TRES digitos de largura de molde, que sao larguras permitidas, e
      a ferramenta FABRICARIA tres digitos a partir de um icone de moeda.

    Por isso a composicao e nomeada aqui e o descarte acontece ANTES da
    pontuacao. Quem vier depois vai olhar `ler_celula` e achar que economizou
    dez linhas; estes dois paragrafos existem para essa pessoa.

    O DESCARTE E POR LARGURA E NUNCA POR APERTAR O RECORTE. Apertar o recorte
    foi exatamente o que produziu as 173 concordancias erradas da Faerlina
    (M-H): um retangulo apertado que encosta no vizinho nao reclama -- ele
    devolve o vizinho. As tres regras posicionais moram em `_glifos_do_numero`,
    que e a peneira UNICA desta fase e e do `01-05`; aqui ela e CONSUMIDA e
    nunca reescrita.

    A GUARDA DO CONJUNTO VEM ANTES DE QUALQUER PIXEL, e ela e a clausula 3 do
    LEIT-09. Conjunto AUSENTE e conjunto INCOMPLETO produzem a MESMA recusa, de
    proposito: o conserto e o mesmo -- uma rodada do cortador -- e quem le a
    tela nao precisa da distincao. A medicao que a justifica ja esta na
    docstring de `conjunto_descreve_numeros`: meio conjunto falha ABERTO, um `8`
    sem molde de `8` casa com `0` a 0,7826 contra piso 0,4698, com folga de
    0,1628 sobre o segundo colocado -- ou seja, A MARGEM TAMBEM NAO PEGA. Um
    conjunto pela metade nao produz meia leitura: ele produz a leitura errada
    com a confianca da certa.

    E O CONSERTO QUE A MENSAGEM ANUNCIA MUDOU, e a mudanca vai escrita em vez de
    o texto antigo sumir. Uma revisao anterior mandava FARMAR ate o digito
    aparecer, porque se acreditava que o `5` e o `7` so viriam com o tempo.
    Medido (M-L e M-O), os dois ja estao na tela em outros campos da MESMA
    barra -- o bonus, o EXP e a L-Coin --, e o cortador colhe de qualquer campo
    por `--campo`. Um conserto que aponta para o TEMPO e um conserto que aponta
    para um COMANDO sao coisas diferentes de dizer a um usuario, e dizer o
    errado custa uma noite.

    TODOS OS LIMIARES CHEGAM POR PARAMETRO SOMENTE-NOMEADO E SEM DEFAULT, pela
    regra do charter. `folga_de_cola` e `None` no conjunto gravado, e a razao e
    medida (M-J): as larguras desta fonte sao limpas, com coluna vazia entre os
    glifos -- nao ha glifo colado a partir.
    """
    if recorte is None or getattr(recorte, "size", 0) == 0:
        return _recusar(
            CAMPO_DA_ADENA,
            MOTIVO_DO_CAMPO_VAZIO,
            "o recorte chegou vazio; nao ha pixel para ler",
        )

    if not conjunto_descreve_numeros(moldes):
        faltam = _faltantes_do_conjunto(moldes)
        return _recusar(
            CAMPO_DA_ADENA,
            MOTIVO_DO_CONJUNTO_DE_MOLDES,
            "o conjunto de moldes da barra nao descreve numeros: faltam "
            f"{', '.join(repr(rotulo) for rotulo in faltam)} "
            f"({len(faltam)} de {len(GLIFOS_DO_NUMERO)} rotulos). Meio conjunto "
            "le ERRADO com a confianca do conjunto inteiro, entao a adena "
            "recusa em vez de adivinhar. O conserto NAO e mexer no piso de "
            "brilho e NAO e esperar o farm: rode `calibrar-renda-moldes.bat` "
            "apontando o campo da barra onde esses rotulos aparecem "
            "(--campo bonus, --campo lcoin, --campo exp)",
        )

    piso = int(piso_de_brilho)
    mascara = mascara_de_numero(recorte, piso)
    faixa_bruta, runs = segmentar_glifos_no_brilho(recorte, piso)

    # CAMPO VAZIO E FORMA ERRADA SAO CONSERTOS DIFERENTES, E POR ISSO A
    # DISTINCAO E FEITA AQUI E NAO DENTRO DA PENEIRA. Sem corrida NENHUMA acima
    # do piso nao ha forma que analisar: o campo simplesmente nao esta na
    # mascara, e o conserto aponta para o RETANGULO ou para o PISO. A peneira do
    # `01-05` chama isso de recusa de forma -- e ela esta certa no vocabulario
    # dela, que so conhece corridas --, mas quem tem campo e este leitor, e o
    # usuario que le `forma-do-recorte` sobre uma tela preta vai procurar um
    # numero que nao esta la. A peneira NAO e alterada por isso: ela continua
    # sendo do `01-05`, e a traducao mora do lado de quem sabe o nome do campo.
    if not runs:
        return _recusar(
            CAMPO_DA_ADENA,
            MOTIVO_DO_CAMPO_VAZIO,
            f"nenhuma coluna do recorte passa do piso de brilho {piso}: ou o "
            "retangulo esta apontando para outro lugar da tela, ou o piso "
            "apagou o campo",
        )

    limite = limite_de_glifo_unico(moldes)
    peneirado = _glifos_do_numero(mascara, faixa_bruta, runs, limite=limite)
    if isinstance(peneirado, RecusaDeForma):
        return _recusar(CAMPO_DA_ADENA, peneirado.motivo, peneirado.detalhe)

    lido = ler_glifos(
        mascara,
        peneirado.faixa,
        list(peneirado.runs),
        moldes,
        float(piso_de_leitura),
        float(margem_de_leitura),
        largura_maxima_de_glifo=int(limite),
        folga_de_cola=folga_de_cola,
    )
    if not lido:
        return _recusar(
            CAMPO_DA_ADENA,
            MOTIVO_DA_PONTUACAO,
            f"a forma do recorte estava certa ({len(peneirado.runs)} glifo(s) "
            "entre os dois icones) e ao menos um deles nao passou no piso "
            f"{piso_de_leitura} OU na margem {margem_de_leitura} de leitura. A "
            "leitura cai TUDO OU NADA: uma adena pela metade convidaria quem le "
            "a completar mentalmente justamente o digito que a maquina nao soube",
        )

    valor = inteiro_do_nivel(lido)
    if valor is None:
        return _recusar(
            CAMPO_DA_ADENA,
            MOTIVO_DA_GRAMATICA,
            f"os glifos produziram {entre_delimitadores(lido)}, que nao "
            "respeita a gramatica de milhar do jogo. A validacao acontece "
            "DEPOIS dos glifos e nao no lugar deles: um glifo perdido ou um a "
            "mais continua produzindo uma sequencia que PARECE numero",
        )

    return ValorDaAdena(
        campo=CAMPO_DA_ADENA,
        valor=valor,
        glifos=len(peneirado.runs),
        texto=lido,
    )


# ---------------------------------------------------------------------------
# OS TRES CAMPOS DE UMA VEZ -- e a leitura e de UM PERSONAGEM NOMEADO
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CamposDaRenda:
    """Os tres campos de uma rodada, cada um inteiro OU recusa.

    POR QUE ELA EXISTE, se `ler_a_renda` ja compoe. O criterio 1 da fase pede
    que o usuario veja OS TRES campos na tela, INCLUSIVE quando um recusou --
    um leitor que abortasse no primeiro problema esconderia os outros dois, e o
    usuario ficaria sem saber se a calibracao inteira esta errada ou so um
    retangulo.

    OS TIPOS SAO DIFERENTES DE PROPOSITO: `nivel` e `exp` saem como
    `ValorDaRenda` (com `escalas`), e `adena` sai como `ValorDaAdena` (com
    `glifos`). Uniformizar os tres numa classe so obrigaria a adena a carregar
    um campo `escalas` que ela nao tem como preencher com verdade, e afirmar
    guarda inexistente e o defeito que o `T-01-43` existe para impedir.
    """

    personagem: str
    nivel: ValorDaRenda | RecusaDaRenda
    exp: ValorDaRenda | RecusaDaRenda
    adena: ValorDaAdena | RecusaDaRenda

    @property
    def por_campo(self) -> dict:
        """Os tres na ORDEM DA TELA, para quem imprime linha a linha."""
        return {
            CAMPO_DO_NIVEL: self.nivel,
            CAMPO_DO_EXP: self.exp,
            CAMPO_DA_ADENA: self.adena,
        }


@dataclass(frozen=True)
class LeituraDaRenda:
    """Uma rodada em que OS TRES campos sairam. Tudo inteiro, e o carimbo entra.

    TUDO INTEIRO, no precedente de `total_em_centesimos`: o nivel e um inteiro
    nu, o EXP viaja em DECIMOS DE MILESIMO de ponto percentual e a adena em
    unidades. Nenhum `float` atravessa esta fronteira -- o produto inteiro da
    milestone e uma DIFERENCA entre duas leituras, e diferenca sobre binario de
    ponto flutuante acumula erro que ninguem consegue ver depois de gravado.

    O CARIMBO ENTRA POR PARAMETRO e este modulo continua sem ler o relogio do
    sistema, pela regra que o `01-01` prendeu com um teste de fonte. Um modulo
    puro que lesse o relogio deixaria de ser testavel contra um instante fixo.
    """

    personagem: str
    nivel: int
    exp: int
    adena: int
    carimbo: float


# ---------------------------------------------------------------------------
# A PORTA DE UM CAMPO COM UM PISO -- e ela e a razao de a varredura do LEIT-10
# custar UMA leitura por tentativa, e nao tres
# ---------------------------------------------------------------------------


def _desempacotar_os_moldes(conjunto: dict) -> dict:
    """Os moldes de glifo em memoria, ou o CONJUNTO VAZIO com a razao no log.

    Um conjunto que nao desempacote vira conjunto VAZIO, e o vazio cai na
    guarda de conjunto incompleto com a mensagem certa; levantar aqui trocaria
    uma recusa nomeada por um traceback no meio do farm. Este comportamento e
    o de `ler_os_tres_campos` desde o `01-04` e esta funcao so lhe da um nome
    para que as duas portas o compartilhem em vez de o repetirem.
    """
    try:
        return glifos_de_calibracao(conjunto.get("moldes"))
    except ValueError as erro:
        log.warning("renda: os moldes da barra nao desempacotaram: %s", erro)
        return {}


def _detalhe_do_personagem_sem_calibracao(calibracao, personagem) -> str:
    """A frase da recusa por personagem, escrita UMA vez e usada pelas duas portas."""
    conhecidos = sorted(getattr(calibracao, "renda_por_personagem", None) or {})
    return (
        f"nao ha calibracao de renda para {personagem!r} "
        f"(calibrados: {', '.join(conhecidos) if conhecidos else '(nenhum)'}). "
        "A leitura NAO cai na calibracao de outro personagem: o retangulo "
        "do vizinho devolve um numero plausivel e errado em vez de um campo "
        "vazio que alguem nota"
    )


#: A TABELA DE QUAIS CAMPOS EXISTEM, e ela e DECLARADA pelo mesmo motivo que
#: `ORDEM_DOS_CAMPOS` e: um `if/elif` de tres ramos seria uma QUARTA verdade
#: sobre os campos da renda, e a quarta e sempre a que esquece de ser
#: atualizada. Cada entrada e `(sub-chave do calibration.json, leitor)`, e os
#: tres leitores tem assinatura UNIFORME -- `(recorte, piso, moldes, conjunto)`
#: -- mesmo que so a adena use os dois ultimos. Uniformizar aqui e o que
#: permite despachar por tabela em vez de por ramo.
#:
#: `MappingProxyType` E NAO `dict` PORQUE O PORTAO DE MEMORIA DESTE ARQUIVO E
#: DE VERDADE: `tests/test_renda_par.py` varre a arvore de sintaxe atras de
#: literal mutavel de nivel de modulo, com controle positivo. Um `dict` nu aqui
#: deixaria o portao vermelho -- e o portao esta certo, porque um mapa mutavel
#: de modulo e memoria esperando para ser escrita.
_PORTA_DO_CAMPO = MappingProxyType(
    {
        CAMPO_DO_NIVEL: (
            SUBCHAVE_DO_NIVEL,
            lambda recorte, piso, moldes, conjunto: nivel_da_regiao(
                recorte, piso_de_brilho=piso
            ),
        ),
        CAMPO_DO_EXP: (
            SUBCHAVE_DO_EXP,
            lambda recorte, piso, moldes, conjunto: exp_da_barra(
                recorte, piso_de_brilho=piso
            ),
        ),
        CAMPO_DA_ADENA: (
            SUBCHAVE_DA_ADENA,
            lambda recorte, piso, moldes, conjunto: adena_da_barra(
                recorte,
                piso_de_brilho=piso,
                moldes=moldes,
                piso_de_leitura=conjunto.get("piso_de_leitura"),
                margem_de_leitura=conjunto.get("margem_de_leitura"),
                folga_de_cola=conjunto.get("folga_de_cola"),
            ),
        ),
    }
)


def ler_um_campo(
    frame,
    *,
    personagem,
    campo,
    calibracao,
    piso_de_brilho=None,
    moldes=None,
):
    """UM campo, com UM piso: o valor, ou a recusa nomeada daquele campo.

    ELA E O `_ler` DE `ler_os_tres_campos`, EXTRAIDO, e nao uma segunda
    implementacao. `ler_os_tres_campos` DELEGA a ela desde o `03-03`, e e isso
    que impede uma segunda verdade sobre como um campo e recortado, mascarado e
    lido -- duas implementacoes do mesmo recorte sao como elas divergem, e a
    divergencia produziria um numero plausivel e errado, que e o unico defeito
    que este workstream trata como inaceitavel.

    POR QUE ELA EXISTE (LEIT-10). A varredura de pisos vizinhos precisa
    experimentar oito pisos NUM campo so. Sem esta porta, cada tentativa
    custaria uma leitura dos TRES campos -- 24 leituras para descobrir um piso
    -- e o requisito nao caberia no orcamento de um tique de 1 s.

    `piso_de_brilho=None` NAO E CONSTANTE MAGICA: `None` e o sinal de "use o
    gravado", e nao um numero por omissao. A distincao e a mesma que
    `RecusaDaRenda` faz entre "recusou" e "nao mediu", e ela importa porque
    MEDIDO nao existe um piso unico -- a banda do nivel (190-220) e a da adena
    por OCR (150) nao tem intersecao nenhuma (M-E), e um default numerico
    serviria a uma regiao e apagaria a outra em silencio.

    `moldes=None` SIGNIFICA "DESEMPACOTE POR CONTA PROPRIA", e o
    desempacotamento so acontece para o campo da ADENA -- os outros dois nao
    tocam nos moldes, e pagar `glifos_de_calibracao` para ler o nivel seria
    trabalho puro jogado fora dentro do caminho em que oito leituras se somam
    num tique so.

    E O CUSTO DESSE DESEMPACOTAMENTO ESTA MEDIDO, NAO ESTIMADO. Nesta arvore,
    contra `tests/fixtures/renda/montagem_completa.png` e a calibracao de
    fixtura (**11** moldes gravados), em 2026-09-03: `glifos_de_calibracao`
    custa **0,017 ms**, contra **5,3 ms** de uma leitura completa da adena --
    tres milesimos dela. Ou seja: desempacotar por campo NAO e o que
    encareceria a delegacao, e a afirmacao de que "o desempacotamento por campo
    triplicaria o custo do caminho de producao" **nao se sustenta nesta
    medicao**. `ler_os_tres_campos` continua desempacotando uma vez mesmo
    assim, porque 0,017 ms tres vezes continua sendo trabalho que ninguem pediu
    e o parametro ja existe -- mas a razao e higiene, e nao orcamento.

    A MEDICAO QUE DECIDE DE VERDADE E OUTRA, e ela vale para o `03-03`: as duas
    formas de ler os tres campos custam **o mesmo dentro do ruido**. Medidas
    intercaladas, 40 rodadas de cada: `ler_os_tres_campos` **36,1 ms** de
    mediana e tres `ler_um_campo` **32,0 ms** (min 16-17, max 118-135 nas
    duas). O OCR domina e varia por um fator de sete; a diferenca entre as duas
    formas some dentro disso. E por isso que o laco pode ler campo a campo
    quando ha piso lembrado sem pagar nada por isso.

    ESTA FUNCAO NAO ACRESCENTA MEMORIA, CACHE NEM ESTADO A ESTE MODULO. A
    Fase 1 definiu-se pura por escrito e ha portao de arvore de sintaxe com
    controle positivo prendendo essa pureza (`tests/test_renda_par.py`). **A
    memoria do piso que funcionou e estado do LACO** (`renda_laco.py`), e nunca
    do leitor: um leitor com memoria mente sobre a tela atual usando a tela
    passada.

    CAMPO DESCONHECIDO LEVANTA `ValueError`, E NAO DEVOLVE RECUSA. E erro de
    programacao do chamador e nao recusa de leitura; uma `RecusaDaRenda` aqui
    esconderia um `typo` dentro dos 79% de recusa normal do nivel, que e
    exatamente onde ninguem o veria. O molde e o de `ganho_do_passo`
    (`renda_conta.py:900-903`): a mensagem nomeia os que existem.
    """
    if campo not in _PORTA_DO_CAMPO:
        raise ValueError(
            f"campo desconhecido: {campo!r}. Os que existem sao "
            f"{ORDEM_DOS_CAMPOS!r}"
        )
    subchave, leitor = _PORTA_DO_CAMPO[campo]

    # A RECUSA POR PERSONAGEM VEM ANTES DE QUALQUER OCR, e a proibicao de queda
    # mora num lugar so (`Calibracao.renda_do_personagem`): nao se gasta o
    # motor para descobrir que nao se sabia de quem era a tela.
    entrada = calibracao.renda_do_personagem(personagem)
    if entrada is None:
        return _recusar(
            campo,
            MOTIVO_DO_PERSONAGEM,
            _detalhe_do_personagem_sem_calibracao(calibracao, personagem),
        )

    bloco = entrada.get(subchave)
    if not isinstance(bloco, dict):
        return _recusar(
            campo,
            MOTIVO_DO_PERSONAGEM,
            f"a entrada de {personagem!r} nao tem a sub-chave {subchave!r}. "
            "Rode o calibrador da renda para este personagem",
        )

    recorte = recortar(frame, Regiao.de_dict(bloco["regiao"]), campo=campo)
    if isinstance(recorte, RecusaDaRenda):
        return recorte

    piso = (
        int(bloco["piso_de_brilho"])
        if piso_de_brilho is None
        else int(piso_de_brilho)
    )
    conjunto = getattr(calibracao, "renda_moldes_da_barra", None) or {}
    if moldes is None and campo == CAMPO_DA_ADENA:
        moldes = _desempacotar_os_moldes(conjunto)
    return leitor(recorte, piso, moldes or {}, conjunto)


def ler_os_tres_campos(frame, *, personagem, calibracao) -> CamposDaRenda:
    """Os tres campos de UM personagem nomeado, com os retangulos e pisos DELE.

    A LEITURA E POR PERSONAGEM E NUNCA CAI NO VIZINHO (LEIT-07). Medido (M-F):
    a janela de status das duas instancias poe o nivel em lugares diferentes.
    Ler uma com o retangulo da outra NAO devolve um campo vazio que alguem nota
    -- devolve `349` ou `112`, que sao numeros desenhados ao lado do nivel e
    passam por qualquer validacao sem reclamar. A proibicao de queda mora num
    lugar so, `Calibracao.renda_do_personagem`, e esta funcao apenas a consome:
    sem entrada, os TRES campos saem como recusa nomeada, ANTES de qualquer OCR
    -- nao se gasta o motor para descobrir que nao se sabia de quem era a tela.

    UM CAMPO QUE RECUSOU NAO IMPEDE OS OUTROS DOIS DE SEREM LIDOS, e e por isso
    que esta funcao devolve `CamposDaRenda` em vez da primeira recusa.

    CADA REGIAO USA O SEU PISO, TRES POR PERSONAGEM (LEIT-08), e as bandas
    medidas nao tem intersecao (M-E). O da adena e agora o piso do caminho de
    GLIFO -- banda larga -- e nao o do caminho de OCR, que tinha largura 1
    (M-J): o campo de calibracao mais fragil da fase virou o mais folgado, e foi
    a TROCA DE LEITOR que fez isso, e nao um ajuste de numero.

    OS MOLDES SAO DESEMPACOTADOS AQUI E NAO DENTRO DE `adena_da_barra`, porque
    quem tem a `Calibracao` e quem le o arquivo -- o leitor recebe o conjunto ja
    em memoria e continua testavel com um dicionario montado a mao. Um conjunto
    que nao desempacote vira conjunto VAZIO, e o vazio cai na guarda de conjunto
    incompleto com a mensagem certa; levantar aqui trocaria uma recusa nomeada
    por um traceback no meio do farm.

    E ELES CONTINUAM SENDO DESEMPACOTADOS **UMA** VEZ, mesmo depois de esta
    funcao passar a DELEGAR a `ler_um_campo` (`03-03`): o conjunto ja
    desempacotado viaja como parametro para a chamada da adena. Se ela delegasse
    sem passar os moldes adiante, o caminho de PRODUCAO -- o de 1 Hz -- pagaria o
    desempacotamento por campo para servir a um caminho que roda em 4,7% dos
    tiques. Ha teste contando as chamadas de `glifos_de_calibracao` numa leitura
    completa e afirmando **1**.

    O QUE ELA DEIXOU DE TER E A IMPLEMENTACAO DO RECORTE; o que ela mantem e a
    ordem da tela, o desempacotamento unico e a recusa antecipada por
    personagem -- que aqui vale para os TRES de uma vez e por isso continua
    sendo feita neste nivel, e nao tres vezes la dentro.
    """
    entrada = calibracao.renda_do_personagem(personagem)
    if entrada is None:
        detalhe = _detalhe_do_personagem_sem_calibracao(calibracao, personagem)
        return CamposDaRenda(
            personagem=personagem or "",
            nivel=_recusar(CAMPO_DO_NIVEL, MOTIVO_DO_PERSONAGEM, detalhe),
            exp=_recusar(CAMPO_DO_EXP, MOTIVO_DO_PERSONAGEM, detalhe),
            adena=_recusar(CAMPO_DA_ADENA, MOTIVO_DO_PERSONAGEM, detalhe),
        )

    conjunto = getattr(calibracao, "renda_moldes_da_barra", None) or {}
    moldes = _desempacotar_os_moldes(conjunto)

    def _ler(campo):
        return ler_um_campo(
            frame,
            personagem=personagem,
            campo=campo,
            calibracao=calibracao,
            moldes=moldes,
        )

    return CamposDaRenda(
        personagem=personagem,
        nivel=_ler(CAMPO_DO_NIVEL),
        exp=_ler(CAMPO_DO_EXP),
        adena=_ler(CAMPO_DA_ADENA),
    )


def ler_a_renda(
    frame, *, personagem, calibracao, carimbo: float
) -> LeituraDaRenda | RecusaDaRenda:
    """`LeituraDaRenda` quando os TRES saem inteiros, ou a PRIMEIRA recusa.

    A ORDEM DA PROCURA E `ORDEM_DOS_CAMPOS`, DECLARADA E NAO IMPLICITA, para que
    duas leituras com o mesmo problema produzam sempre a mesma recusa. Quem
    quiser as TRES respostas de uma vez chama `ler_os_tres_campos`; esta funcao
    e para quem so pode seguir com a leitura completa.
    """
    campos = ler_os_tres_campos(frame, personagem=personagem, calibracao=calibracao)
    por_campo = campos.por_campo
    for campo in ORDEM_DOS_CAMPOS:
        resultado = por_campo[campo]
        if isinstance(resultado, RecusaDaRenda):
            return resultado
    return LeituraDaRenda(
        personagem=campos.personagem,
        nivel=campos.nivel.valor,
        exp=campos.exp.valor,
        adena=campos.adena.valor,
        carimbo=carimbo,
    )


# ---------------------------------------------------------------------------
# AS TRES RECUSAS QUE SO EXISTEM QUANDO HA UM PAR
# ---------------------------------------------------------------------------
#
# ELAS SAO A ULTIMA DEFESA DA FASE CONTRA UM NUMERO VALIDO, PLAUSIVEL E ERRADO,
# e nada mais na Fase 1 enxerga esse modo. A docstring de `numero_valido` ja
# escreve o buraco com todas as letras: a gramatica pega glifo perdido e glifo
# a mais, e NAO pega SUBSTITUICAO; para esse modo servem a margem calibrada, o
# ACORDO ENTRE DOIS FRAMES e a guarda de cruzamento. Estas tres funcoes sao o
# acordo entre dois frames da renda.
#
# OS TRES CASOS DE HONRA, MEDIDOS E NAO INVENTADOS:
#
#   M19    a extracao do ultimo grupo valido sobre `Special 8,786` -- o recorte
#          cru em que a adena NAO aparece -- devolve `8786`, com a gramatica
#          inteira satisfeita. Errado por tres ordens de grandeza.
#   M-G a  a Yazalaque lida como `106.020` contra a verdade `1.696.020` do mesmo
#          frame. E o mais PERIGOSO dos tres, porque `106.020` parece uma adena.
#   M-G b  a Faerlina lida como `91` contra `13.160.684`. E o mais DURO: cinco
#          ordens de grandeza.
#
# E A TROCA DO LEITOR DA ADENA PARA O CAMINHO DE GLIFO NAO OS TORNOU
# REDUNDANTES. A guarda de forma pega recorte que PERDEU o numero; ela nao pega
# recorte deslocado para o CAMPO DO LADO, porque o vizinho tem os proprios
# icones nas proprias pontas e passa na forma exatamente como o campo certo. O
# M-H mediu o quanto isso e provavel: quando o recorte encosta, as duas escalas
# concordaram na L-Coin 173 vezes em 173. Ninguem remove estes testes por
# parecerem historicos.
#
# A FASE 1 CONTINUA SEM ESTADO (CTX-9). As tres sao funcoes PURAS sobre um par
# passado por parametro, e NENHUM caminho de producao desta fase as chama --
# porque uma fase sem memoria nao tem a leitura anterior. Quem as chama e a
# Fase 2. No dia em que alguem ligar um cache dentro do leitor para "fazer elas
# funcionarem", a fase deixou de ser o que o `<domain>` do `CONTEXT.md` fechou.
#
# A ARITMETICA E INTEIRA, no precedente de `centesimos_de_moeda`: nada aqui usa
# `float`, nem para razao.


def o_exp_andou_para_tras(anterior, atual) -> RecusaDaRenda | None:
    """O EXP caiu com o nivel PARADO? Recusa nomeada. Senao, nada.

    ELA SE ABSTEM QUANDO O NIVEL MUDOU, para cima ou para baixo, e a razao vai
    escrita: SUBIR DE NIVEL ZERA O EXP. Com nivel diferente os dois numeros nao
    sao comparaveis, e uma recusa aqui seria ruido em cima do evento mais normal
    do jogo — o par de campo `nivel 66, EXP 68,5632%` -> `nivel 67, EXP 8,0012%`
    e um level up de verdade, gravado nas duas pontas.

    E O CUSTO ASSUMIDO VAI ESCRITO JUNTO: se o jogo tirar EXP na morte DENTRO do
    mesmo nivel, esta regra recusa uma amostra legitima. A troca esta feita de
    proposito — uma recusa custa UMA amostra, e um digito trocado gravado custa
    a taxa inteira dali para a frente. O motivo e nomeado justamente para que a
    Fase 2 possa decidir diferente COM A EVIDENCIA NA MAO, em vez de descobrir
    que nao da para distinguir.

    Ela e PURA sobre o par, e nenhum caminho de producao desta fase a chama
    (CTX-9). Quem a chama e a Fase 2, que e quem tem duas leituras.
    """
    if int(anterior.nivel) != int(atual.nivel):
        return None
    if int(atual.exp) >= int(anterior.exp):
        return None
    return _recusar(
        CAMPO_DO_EXP,
        MOTIVO_DO_EXP_PARA_TRAS,
        f"o EXP caiu de {anterior.exp} para {atual.exp} decimos de milesimo "
        f"com o nivel PARADO em {atual.nivel}. Subir de nivel zera o EXP e a "
        "regra se abstem nesse caso; com o nivel parado, EXP para tras e "
        "leitura duvidosa e nao evento do jogo",
    )


def o_nivel_andou_para_tras(anterior, atual) -> RecusaDaRenda | None:
    """O nivel desceu? Recusa nomeada. Senao, nada.

    A RAZAO VAI COM A MESMA HONESTIDADE DA IRMA: o caminho comum para um nivel
    que desce NAO e o jogo — e uma SUBSTITUICAO DE DIGITO, e substituicao e
    exatamente o que a docstring de `numero_valido` documenta nao pegar. `67`
    virando `57` passa em toda validacao de forma que existe nesta arvore.

    Se o jogo permitir perder nivel, a recusa custa uma amostra e o usuario ve o
    motivo escrito na tela — que e melhor que a alternativa, um nivel errado
    gravado e indistinguivel de um certo.

    ELA SO OLHA PARA BAIXO. Nivel subindo e o evento mais normal do jogo, e o
    par de campo com o level up verdadeiro prova que ela se cala nele.
    """
    if int(atual.nivel) >= int(anterior.nivel):
        return None
    return _recusar(
        CAMPO_DO_NIVEL,
        MOTIVO_DO_NIVEL_PARA_TRAS,
        f"o nivel caiu de {anterior.nivel} para {atual.nivel}. O caminho comum "
        "para isso nao e o jogo: e um digito trocado, que passa em "
        "`numero_valido` inteiro",
    )


def a_adena_saltou_ordem_de_grandeza(
    anterior, atual, *, fator_de_salto: int
) -> RecusaDaRenda | None:
    """A razao entre as duas adenas passou do fator, EM QUALQUER DIRECAO?

    A DIRECAO NAO E CRITERIO, e isso e o desenho e nao um esquecimento. Gastar
    adena e normal — e a Fase 2 ja trata renda negativa —, e ganhar adena de
    loot tambem. O que NAO e normal e a RAZAO entre duas leituras saltar uma
    ordem de grandeza, porque isso e um digito ganho ou perdido e nao uma
    compra. Os tres casos medidos moram exatamente ai: `8786` contra
    `10.673.628` (M19), `106.020` contra `1.696.020` e `91` contra `13.160.684`
    (M-G).

    ARITMETICA INTEIRA, POR MULTIPLICACAO E NUNCA POR DIVISAO, na disciplina do
    CTX-5: uma divisao inteira truncaria e faria o limiar significar coisas
    diferentes em ordens de grandeza diferentes; uma divisao de ponto flutuante
    traria erro binario para dentro de uma comparacao de limiar.

    QUANDO UM DOS LADOS E ZERO A REGRA SE ABSTEM, e a docstring diz por que: nao
    existe ordem de grandeza em relacao a zero — toda razao contra zero e
    infinita, e a regra recusaria SEMPRE. O caso do zero pertence a recusa de
    campo vazio e a de gramatica, que ja existem e apontam para o conserto
    certo.

    `fator_de_salto` E SOMENTE-NOMEADO E SEM DEFAULT, pela regra do charter: um
    default aqui seria um LIMIAR entrando por omissao, e limiar por omissao e a
    definicao de constante magica. Quem tem duas leituras e a Fase 2, e e la que
    o fator vem de cima — do `config.toml` do usuario, e nao deste fonte.
    """
    velha = int(anterior.adena)
    nova = int(atual.adena)
    if velha == 0 or nova == 0:
        return None
    maior, menor = (velha, nova) if velha >= nova else (nova, velha)
    if maior <= menor * int(fator_de_salto):
        return None
    return _recusar(
        CAMPO_DA_ADENA,
        MOTIVO_DO_SALTO_DA_ADENA,
        f"a adena foi de {velha} para {nova}, e a razao entre as duas passa do "
        f"fator {fator_de_salto}. Um salto assim e um digito ganho ou perdido, "
        "e nao uma compra: gastar e ganhar adena sao normais, saltar uma ordem "
        "de grandeza nao e",
    )


def conferir_o_par(
    anterior, atual, *, fator_de_salto: int
) -> tuple[RecusaDaRenda, ...]:
    """As TRES regras sobre o par, e a tupla de TODAS as recusas encontradas.

    DEVOLVER TODAS, E NAO A PRIMEIRA, e o que permite ao chamador dizer "dois
    campos discordam do par anterior" em vez de esconder o segundo problema
    atras do primeiro. Um par em que o nivel desceu E a adena saltou e um caso
    diferente de um par em que so o nivel desceu, e a diferenca importa para
    quem for decidir se aquela sessao inteira e confiavel.

    Tupla VAZIA e o par coerente. Ela e o desfecho do par de campo com o level
    up verdadeiro — o EXP caiu, mas o nivel mudou; o nivel subiu, e a regra so
    olha para baixo; e a adena cresceu bem abaixo de qualquer fator razoavel.

    PURA sobre o par, e sem chamador de producao nesta fase (CTX-9).
    """
    achados = (
        o_exp_andou_para_tras(anterior, atual),
        o_nivel_andou_para_tras(anterior, atual),
        a_adena_saltou_ordem_de_grandeza(
            anterior, atual, fator_de_salto=fator_de_salto
        ),
    )
    return tuple(recusa for recusa in achados if recusa is not None)
