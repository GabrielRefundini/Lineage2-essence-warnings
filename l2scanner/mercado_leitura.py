"""O transform PURO da leitura de uma linha do World Exchange: pixels -> valor.

Este modulo nao abre janela, nao le teclado, nao escreve arquivo e nao tem
relogio. Ele olha um recorte e responde "esta linha diz `18,90` por 2 unidades
do item X", ou diz POR QUE nao respondeu. Quem mostra isso a um humano e quem
aceita a correcao dele e `calibrar_mercado.py`; quem junta as linhas numa pagina
e `mercado_pagina.py`.

ESTE MODULO NASCEU DE UMA PROMOCAO, E NAO DE UMA COPIA
------------------------------------------------------
`segmentar_glifos`, `mascara_do_sufixo`, `recortar_sufixo`,
`_alinhar_por_preenchimento`, `_par_incalculavel` e `MARGEM_DO_RETANGULO_DE_PRECO`
foram MOVIDAS de `calibrar_mercado.py`, com as docstrings inteiras — e a
docstring e onde a medicao que justifica cada uma vive. `centesimos_de_moeda`,
`inteiro_de_quantidade` e a mecanica de `pontuar_celula` foram MOVIDAS de
`tools/medir_leitura_de_glifo.py`, que as mediu.

A seta agora aponta ferramenta -> puro, como o repositorio ja mantem em quatro
precedentes (`identidade.mascara_de_texto`, `mercado_geometria.medir_a_grade`,
`mercado_visao.casamento_da_ancora`, `calibrar.ARQUIVO_CALIBRACAO`). A razao NAO
e estetica: `calibrar_mercado.py` chama `tornar_consciente_de_dpi()` NO IMPORT e
carrega `argparse` e as chamadas de JANELA do OpenCV. Um modulo de producao que o
importasse pagaria esse efeito colateral so por existir, e uma janela de
conferencia acabaria abrindo dentro do tick de captura.

(As chamadas de janela nao aparecem NEM POR NOME neste arquivo, nem em
comentario: `tests/test_mercado_leitura.py` varre o fonte inteiro atras delas, e
um teste de fonte que aceitasse mencao em comentario deixaria de pegar a chamada
de verdade no dia em que ela entrasse comentada e fosse descomentada.)

Copiar em vez de mover teria produzido duas versoes da mesma primitiva
envelhecendo separadas, e a que envelhecesse pior daria numero plausivel e
errado. `tests/test_mercado_glifos.py` e o detector de regressao do movimento:
ele importa daqui e afirma a convencao de recorte contra pixels reais.

TODO LIMIAR CHEGA POR PARAMETRO, SEM VALOR DE FABRICA
-----------------------------------------------------
`piso`, `margem`, o limiar de dispersao da sonda e o limiar do cabecalho vem
todos do `calibration.json`, medidos no frame do proprio usuario. Nenhum deles
tem default: um default e um numero magico que entra por omissao, e este projeto
ja perdeu uma medicao assim (`MINIMO_PARA_PROPOR_ROTULO = 0.95` deixava a
ferramenta muda e ninguem saberia). `mercado_limiar_de_glifo = 0.8555` em
especial NAO e piso de leitura: ele e o limiar de COLISAO entre moldes, medido
molde-contra-molde, e usado como piso rejeitaria 18% dos glifos reais de tela.

A FALHA E FECHADA, EM TRES PENEIRAS, NESTA ORDEM
-------------------------------------------------
1. A SONDA DE OCLUSAO, antes de tudo o que custa. Uma linha coberta cai sem
   pagar ~7 ms de OCR, e a recusa NUNCA vem da confianca do casamento.
2. O TUDO-OU-NADA da celula: um run que reprove no piso E na margem derruba a
   celula inteira. Preco nunca e inventado (LEIT-02).
3. A GRAMATICA do numero: milhar em blocos de exatamente 3, decimal com
   exatamente 2. Ela pega glifo perdido e glifo a mais.

A quarta — a guarda de cruzamento contra `Unit price x Quantity`, a unica que
pega SUBSTITUICAO — e do 02-06, e depende do veredito que o 02-02 mediu.

NADA AQUI LEVANTA POR PIXEL RUIM
---------------------------------
Pelo mesmo motivo de `ocr._ler`: isto roda DENTRO do tick. Uma excecao aqui
pararia o scanner de olhar a party, e a proxima morte real passaria despercebida
— o unico defeito que este projeto trata como inaceitavel.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

from .identidade import VALOR_MINIMO_DO_TEXTO
from .mercado_catalogo import EntradaDoCatalogo, agrupar, assinatura_por_ocr
from .mercado_geometria import nivel_de_fundo_da_linha
from .mercado_visao import casamento_da_ancora

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PROMOVIDAS de `calibrar_mercado.py` — a segmentacao e o alinhamento de glifo
# ---------------------------------------------------------------------------
def segmentar_glifos(
    recorte: np.ndarray,
) -> tuple[tuple[int, int] | None, list[tuple[int, int]]]:
    """Separa os glifos de UM numero marcado, por projecao da mascara de texto.

    Devolve `(faixa_de_linhas, runs_de_coluna)`:

    - `faixa_de_linhas` e `(topo, base)`, UMA SO para o retangulo inteiro, e
      `None` quando nao ha pixel de texto nenhum;
    - `runs_de_coluna` sao os pares `(inicio, fim)` de cada glifo, da esquerda
      para a direita.

    A FAIXA E COMPARTILHADA DE PROPOSITO, E ISSO E PARTE DA ASSINATURA. Recortar
    cada glifo justo na PROPRIA altura deixaria a virgula com 3 px e o digito
    com 8, descartando a posicao vertical relativa -- que e precisamente o que
    distingue uma virgula (baixa) de um digito (altura cheia). Deixar a
    convencao implicita tambem convida ao teste circular: os numeros da matriz
    de confusao MUDAM com o recorte, e quem escolhe o recorte depois de ver a
    matriz ajusta um ate o outro fechar.

    MECANICA. A mascara vem de `identidade.mascara_de_texto` (V > 180), e nao e
    reimplementada aqui: ela ja carrega a razao medida de ser so brilho (o nome
    do lider da party e amarelo). Aqui essa mesma propriedade serve ao dourado
    do `Adena` e ao ciano da linha destacada. A faixa sai de
    `flatnonzero(mascara.any(axis=1))`, do primeiro ao ultimo inclusive. As
    colunas saem de `mascara.any(axis=0)`, e QUALQUER COLUNA VAZIA SEPARA -- sem
    tolerancia de lacuna, porque a menor lacuna real medida entre dois glifos
    vizinhos e de exatamente uma coluna.

    MEDIDO em `recordings/20260828-060622-mercado-pagina-cheia/frame_000010.png`:

        preco       glifos do rotulo    runs encontrados
        100,00            6                    6
        3,00              4                    4
        18,90             5                    5
        7,50              4                    4
        18,00             5                    5
        2,45              4                    4
        6,00 (Unit)       4                    4
        9,45 (Unit)       4                    4

    8 de 8. Geometria sob esta convencao: faixa de 9 px em todas as marcacoes;
    digitos de 4 px, com o `4` em 6 px; a virgula em 1 px.

    Recorte vazio ou sem pixel de texto devolve `(None, [])` e NAO levanta: o
    laco interativo trata isso como "remarque", nao como defeito.

    ELA E UMA CASCA FINA DESDE O 02-07, E A ASSINATURA FICA INTACTA DE
    PROPOSITO. O corpo mudou de casa para `segmentar_glifos_no_brilho`, que
    recebe o piso por parametro; aqui fica a chamada com o piso COMPARTILHADO.
    Manter a assinatura nao e conservadorismo: ela tem 35 pontos de chamada (60
    mencoes em 11 arquivos, contados) em producao, ferramentas e testes, e TODOS
    querem o piso compartilhado. Quebrar os 35 por causa de UMA coluna seria
    custo sem informacao — e este e o unico lugar do repositorio que nomeia o
    piso compartilhado para a leitura de mercado, porque nomear uma vez e o
    contrario de espalhar.
    """
    return segmentar_glifos_no_brilho(recorte, VALOR_MINIMO_DO_TEXTO)


def mascara_de_numero(bgr: np.ndarray, valor_minimo: int) -> np.ndarray:
    """A mascara de brilho de um recorte de numero, no piso RECEBIDO.

    A IRMA de `mascara_do_sufixo`, e nasce ao lado dela pela mesma razao: a
    mecanica e a de `identidade.mascara_de_texto` — so o canal V, sem filtro de
    saturacao —, e o que muda e de onde vem o piso. Ali ele e uma constante de
    modulo medida para as PALAVRAS; aqui ele vem de FORA, porque cada coluna de
    numero tem o seu e o da Quantity foi medido no censo (02-07).

    Com `valor_minimo = identidade.VALOR_MINIMO_DO_TEXTO` ela e IGUAL a
    `mascara_de_texto` pixel a pixel sobre o mesmo recorte — e e essa igualdade
    que prova que NADA muda para quem nao pediu piso proprio, as colunas de
    moeda inclusive.

    Recorte vazio devolve matriz vazia e NAO levanta: isto roda dentro do tick.
    """
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return (hsv[:, :, 2] > int(valor_minimo)).astype(np.uint8)


def segmentar_glifos_no_brilho(
    recorte: np.ndarray, valor_minimo: int
) -> tuple[tuple[int, int] | None, list[tuple[int, int]]]:
    """`segmentar_glifos` com o piso de brilho por parametro.

    O corpo que morava em `segmentar_glifos` mora aqui desde o 02-07, e a
    CONVENCAO DE FAIXA COMPARTILHADA fica intacta: uma so faixa de linhas para o
    retangulo inteiro, porque e a posicao vertical relativa que distingue a
    virgula (baixa) do digito (altura cheia). Qualquer coluna vazia separa, sem
    tolerancia de lacuna — a menor lacuna real medida entre dois glifos vizinhos
    e de exatamente uma coluna.

    POR QUE UM PISO POR COLUNA, E NAO UM GLOBAL. Medido no 02-04: o tronco do
    `1` da coluna Quantity e desenhado a V = 177, ABAIXO do piso 180, enquanto o
    MESMO `1` da coluna Total tem V = 205. E a coluna Total NAO pode descer
    junto: ela carrega a palavra de sufixo dentro do proprio recorte, e a palavra
    vive entre V = 120 e V = 173 (ver `VALOR_MINIMO_DO_SUFIXO`). Sondado, `18,90`
    vira `18,907` ja no piso 170. As duas faixas sao DISJUNTAS.

    `valor_minimo` NAO tem valor de fabrica onde ele decide leitura de producao;
    aqui ele e posicional e obrigatorio pela mesma razao.
    """
    if recorte is None or getattr(recorte, "size", 0) == 0:
        return None, []

    mascara = mascara_de_numero(recorte, valor_minimo)
    if mascara.size == 0:
        return None, []

    linhas = np.flatnonzero(mascara.any(axis=1))
    if linhas.size == 0:
        return None, []
    faixa = (int(linhas[0]), int(linhas[-1]) + 1)

    runs: list[tuple[int, int]] = []
    inicio: int | None = None
    for coluna, tem_texto in enumerate(mascara.any(axis=0)):
        if tem_texto and inicio is None:
            inicio = coluna
        elif not tem_texto and inicio is not None:
            runs.append((inicio, coluna))
            inicio = None
    if inicio is not None:
        runs.append((inicio, int(mascara.shape[1])))

    return faixa, runs


# O piso de brilho das PALAVRAS DE SUFIXO (`XM Coin`, `Adena`), que NAO e o dos
# digitos -- e a diferenca foi medida, nao suposta.
#
# `identidade.VALOR_MINIMO_DO_TEXTO` vale 180 e foi medido sobre texto de party,
# que e claro. O preco do mercado tambem e claro (V ate 255). A palavra de
# sufixo ao lado dele NAO E: medido em `frame_000010`, na coluna a direita do
# preco, a palavra `XM Coin` tem V MAXIMO 173 e p99 148. Ela fica INTEIRA abaixo
# de 180 -- com o piso dos digitos a mascara dela sai VAZIA, e um molde vazio
# nao casa com nada. Sem piso proprio, marcar a palavra produziria um molde nulo
# que so seria descoberto no fim de toda a marcacao.
#
# 120 fica no meio de um platô medido e largo: com qualquer piso entre 100 e 140
# a palavra sai com a MESMA faixa de 8 px e largura 35-36 px, identica nas seis
# linhas do frame. E o fundo nao invade em nenhum deles -- 0 pixel de fundo
# acima do piso, nos tres pontos conferidos (100, 120, 140), sobre 4500 pixels
# de area sem texto. Nao ha zona cinzenta a dividir aqui: ha um vale vazio.
#
# A faixa de 8 px da palavra contra os 9 px do digito e a razao de o guard de
# altura de `mercado_visao._conferir_a_altura_do_conjunto` parar nos glifos de
# UM caractere. Exigir a mesma altura dos dois grupos recusaria a calibracao
# correta.
VALOR_MINIMO_DO_SUFIXO = 120


def mascara_do_sufixo(bgr: np.ndarray) -> np.ndarray:
    """A mascara das palavras de sufixo, no piso proprio delas.

    Mesma mecanica de `identidade.mascara_de_texto` -- so brilho, sem filtro de
    saturacao --, com o piso medido para o texto APAGADO do sufixo. Ver
    `VALOR_MINIMO_DO_SUFIXO` para os numeros.
    """
    if bgr.size == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return (hsv[:, :, 2] > VALOR_MINIMO_DO_SUFIXO).astype(np.uint8)


def recortar_sufixo(recorte: np.ndarray) -> np.ndarray | None:
    """O molde de uma PALAVRA inteira, sem segmentar em letras.

    `XM Coin` e `Adena` entram no conjunto como palavras porque e o SUFIXO que
    desambigua a convencao da virgula, nao o numero (`SPIKE-RESPOSTAS.md` 2): a
    virgula e separador de milhar E de decimal na mesma linha (`5,000,000 Adena`
    ao lado de `62,00 XM Coin`). Segmentar em letras nao serviria a isso e
    multiplicaria por seis as chances de colisao.

    Mesma convencao de recorte dos digitos -- faixa de linhas justa e span de
    colunas do primeiro ao ultimo pixel de texto --, mas no piso de brilho da
    palavra. Devolve `None` quando nao ha texto nenhum no retangulo, para o laco
    interativo pedir que se remarque em vez de gravar um molde vazio.
    """
    if recorte.size == 0:
        return None

    mascara = mascara_do_sufixo(recorte)
    if mascara.size == 0:
        return None

    linhas = np.flatnonzero(mascara.any(axis=1))
    colunas = np.flatnonzero(mascara.any(axis=0))
    if linhas.size == 0 or colunas.size == 0:
        return None

    recortada = mascara[
        int(linhas[0]) : int(linhas[-1]) + 1, int(colunas[0]) : int(colunas[-1]) + 1
    ]
    return (recortada * 255).astype(np.uint8)


def _alinhar_por_preenchimento(
    a: np.ndarray, b: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Iguala os dois PREENCHENDO ate a maior caixa comum, com zeros.

    O oposto de `_alinhar`, que corta ao menor comum -- e a diferenca e
    deliberada, nao inconsistencia. Um nome e texto alinhado a esquerda dentro
    de uma coluna larga, e cortar o compara pelo prefixo comum, o que torna a
    matriz dos NOMES mais conservadora. Um glifo tem 1 a 6 px de largura: cortar
    `,` (1 px) contra `2` (4 px) compara o `2` pela sua PRIMEIRA COLUNA, o que
    nao e comparar o `2`. Medido: 0.1918 preenchendo, 0.5000 cortando.

    Preencher com zero e o que a mascara ja significa: fora do glifo nao ha
    texto. O canto superior esquerdo ancora os dois, pela mesma razao de
    `_alinhar` -- e o unico alinhamento com significado aqui, ja que a faixa de
    linhas compartilhada ja poe os dois na mesma linha de base.
    """
    altura = max(a.shape[0], b.shape[0])
    largura = max(a.shape[1], b.shape[1])
    saida = []
    for arranjo in (a, b):
        caixa = np.zeros((altura, largura), dtype=arranjo.dtype)
        if arranjo.size:
            caixa[: arranjo.shape[0], : arranjo.shape[1]] = arranjo
        saida.append(caixa)
    return saida[0], saida[1]


def _par_incalculavel(a: np.ndarray, b: np.ndarray) -> bool:
    """O par pode ser MEDIDO? Decidido pelas PRE-CONDICOES, nunca pelo score.

    NAO TESTE `casamento_da_ancora(...) == 0.0` PARA RESPONDER ISTO. Aquele
    retorno e um float PELADO cujo `0.0` esta sobrecarregado em QUATRO saidas:
    recorte vazio, molde maior que o alvo, desvio abaixo de `1e-6`, e correlacao
    GENUINAMENTE NULA. As tres primeiras sao ausencia de medicao; a quarta e a
    MELHOR medicao que um par de classes diferentes pode dar.

    E o conjunto CORRETO de 11 glifos tem quatro zeros do quarto tipo, medidos
    na mascara:

        par            score    desvio dos dois lados    guard dispara?
        (',', '0')     0.0      70.478 / 120.208             NAO
        (',', '6')     0.0      70.478 / 120.208             NAO
        (',', '9')     0.0      70.478 / 120.208             NAO
        ('0', '7')     0.0      120.208 / 110.418            NAO

    Cinco ordens de grandeza acima do piso de `1e-6`, e nenhum vazio. Sao os
    pares MELHOR separados que o conjunto tem. Uma implementacao que os
    classificasse como nao-mensuraveis pelo score RECUSARIA o conjunto correto
    de glifos -- o unico artefato que este plano existe para produzir. (Em tons
    de cinza nao ha nenhum: os quatro sao um fenomeno da mascara. E o score
    tambem nao tem `0.0` como piso -- o minimo medido em cinza e -0.1849.)

    Por isso a resposta vem de re-checar as pre-condicoes no par JA ALINHADO,
    ANTES de chamar. E o `.rodou` do CR-03 descido ao nivel do par, pela porta
    certa.
    """
    if a.size == 0 or b.size == 0:
        return True
    if b.shape[0] > a.shape[0] or b.shape[1] > a.shape[1]:
        return True
    if a.shape[0] > b.shape[0] or a.shape[1] > b.shape[1]:
        return True
    return bool(
        a.astype(np.float32).std() < 1e-6 or b.astype(np.float32).std() < 1e-6
    )


# Folga em volta do retangulo proposto para um numero.
#
# Colunas vazias nas pontas NAO criam run em `segmentar_glifos` (ela separa por
# coluna vazia), entao a folga nao muda a contagem de glifos; ela so faz o
# retangulo desenhado na tela ficar legivel para o olho humano em vez de colado
# no desenho.
MARGEM_DO_RETANGULO_DE_PRECO = 2


# ---------------------------------------------------------------------------
# PROMOVIDAS de `tools/medir_leitura_de_glifo.py` — a gramatica do numero
# ---------------------------------------------------------------------------
def centesimos_de_moeda(texto: str) -> int | None:
    """`100,00` -> 10000. `None` para tudo que nao respeita a gramatica.

    A virgula do jogo faz DUAS coisas - separador decimal com exatamente 2 casas
    e separador de milhar com grupos de exatamente 3 - e as duas aparecem na
    mesma linha da mesma tela (`5,000,000 Adena` ao lado de `62,00 XM Coin`).
    Aqui so a leitura de MOEDA e aceita: ela sempre termina em `,dd`.

    A gramatica e uma TRAVA DE VALIDACAO, nao so uma regra de parsing: um digito
    perdido pelo casamento de molde produz `5,00,000` ou `62,000`, que violam a
    regra e derrubam a linha - em vez de virar um numero plausivel e errado.
    """
    if not texto or "," not in texto:
        return None
    partes = texto.split(",")
    decimal = partes[-1]
    if len(decimal) != 2 or not decimal.isdigit():
        return None
    inteiro = partes[:-1]
    if not inteiro or not inteiro[0] or not inteiro[0].isdigit():
        return None
    if len(inteiro[0]) > 3:
        return None
    for grupo in inteiro[1:]:
        if len(grupo) != 3 or not grupo.isdigit():
            return None
    return int("".join(inteiro)) * 100 + int(decimal)


def inteiro_de_quantidade(texto: str) -> int | None:
    """`48` -> 48, `5,000,000` -> 5000000. Quantidade nao tem casa decimal."""
    if not texto:
        return None
    partes = texto.split(",")
    if any((not p) or (not p.isdigit()) for p in partes):
        return None
    if len(partes) == 1:
        return int(partes[0])
    if len(partes[0]) > 3:
        return None
    for grupo in partes[1:]:
        if len(grupo) != 3:
            return None
    return int("".join(partes))



def numero_valido(lido: str | None) -> bool:
    """A gramatica travada do numero do jogo. Tres linhas, e vale a pena.

    Aceita `NNN` (ate 3 digitos), depois grupos de EXATAMENTE 3 separados por
    virgula, e permite que o ULTIMO grupo tenha 2 — que e a casa decimal. Assim
    `100,00`, `5,000,000`, `62,000` e `48` passam, e `5,00,000` (bloco de milhar
    com 2), `1234` (a virgula do milhar perdida) e `1,0000` (grupo com 4) caem.

    O QUE ELA PEGA: GLIFO PERDIDO E GLIFO A MAIS. E o modo de falha que a
    classificacao nao pega sozinha, porque um run a menos ou a mais continua
    produzindo uma sequencia de digitos que parece numero.

    O QUE ELA NAO PEGA: SUBSTITUICAO. `0` virando `8` mantem a gramatica
    intacta — `100,00` e `180,00` sao os dois validos — e o par `0`x`8` e o mais
    estreito do sistema (margem medida 0,0370). Para esse modo servem a margem
    calibrada, o acordo entre dois frames, e a guarda de cruzamento contra
    `Unit price x Quantity`, que chega no 02-06. Escrever o alcance dela aqui
    evita a confusao cara de achar que a gramatica cobre a leitura inteira.

    Ela NAO substitui `centesimos_de_moeda` nem `inteiro_de_quantidade`: aquelas
    CONVERTEM sob uma leitura escolhida da virgula (decimal ou milhar), esta so
    afirma que a forma esta inteira. A coluna Quantity e onde ela ganha o
    salario: `inteiro_de_quantidade("1234")` devolve 1234, mas a tela escreveria
    `1,234` — a virgula perdida so aparece aqui.
    """
    if not lido:
        return False
    partes = lido.split(",")
    if any((not parte) or (not parte.isdigit()) for parte in partes):
        return False
    if len(partes[0]) > 3:
        return False
    for indice, grupo in enumerate(partes[1:], start=1):
        ultimo = indice == len(partes) - 1
        if len(grupo) == 3:
            continue
        if ultimo and len(grupo) == 2:
            continue
        return False
    return True


def pontuar_glifos(
    mascara: np.ndarray,
    faixa: tuple[int, int],
    runs: list[tuple[int, int]],
    moldes: dict[str, np.ndarray],
) -> list[tuple[str, float, float]] | None:
    """Cada run com `(rotulo, score, margem_sobre_o_segundo)`. Sem piso.

    Sem piso e sem margem de proposito: quem decide e quem chama. Foi assim que
    a varredura do 02-02 pode MEDIR o piso a partir da distribuicao — aplicar o
    corte aqui dentro tornaria a medicao circular.

    A mecanica e a de `calibrar_mercado.propor_rotulo`, na mesma representacao
    (mascara binaria) e no mesmo alinhamento (preenchimento ate a maior caixa).
    Reaproveitar exatamente a mecanica e o que faz o numero significar a mesma
    coisa dos dois lados; medir de um jeito e decidir com o outro seria comparar
    convencoes.
    """
    de_um_caractere = {r: m for r, m in moldes.items() if len(r) == 1}
    if not de_um_caractere or not runs:
        return None

    topo, base = faixa
    saida: list[tuple[str, float, float]] = []
    for inicio, fim in runs:
        recorte = mascara[topo:base, inicio:fim]
        pontuados: list[tuple[float, str]] = []
        for rotulo, molde in de_um_caractere.items():
            a, b = _alinhar_por_preenchimento(recorte, molde)
            if _par_incalculavel(a, b):
                continue
            pontuados.append((casamento_da_ancora(a, b), rotulo))
        if not pontuados:
            return None
        pontuados.sort(reverse=True)
        melhor_score, melhor_rotulo = pontuados[0]
        segundo = pontuados[1][0] if len(pontuados) > 1 else -1.0
        saida.append(
            (melhor_rotulo, float(melhor_score), float(melhor_score - segundo))
        )
    return saida


def ler_glifos(
    mascara: np.ndarray,
    faixa: tuple[int, int],
    runs: list[tuple[int, int]],
    moldes: dict[str, np.ndarray],
    piso: float,
    margem: float,
) -> str | None:
    """A leitura de producao dos glifos, ou `None`. TUDO OU NADA (LEIT-02).

    A gemea de `calibrar_mercado.propor_rotulo`, e ela nasce AO LADO em vez de
    substitui-la porque os limiares sao outros: aquela usa os numeros de PROPOR
    (0,80 e 0,12, medidos para o portao humano da calibracao) e esta recebe os
    de LEITURA (`mercado_limiar_de_leitura_de_glifo` e
    `mercado_margem_de_leitura_de_glifo`, medidos sobre 2.057 glifos de campo).
    Aliasar os dois faria o afrouxamento de um viajar para o outro.

    `piso` e `margem` NAO tem default. Um default aqui seria constante magica no
    caminho que decide o preco.

    Basta um run que nao passe no piso E na margem para a funcao devolver
    `None`. Uma leitura parcial (`6?,00`) e pior que nenhuma: ela convida quem
    le a completar mentalmente justamente a parte que a maquina NAO soube.
    """
    pontuados = pontuar_glifos(mascara, faixa, runs, moldes)
    if not pontuados:
        return None
    lido: list[str] = []
    for rotulo, score, distancia in pontuados:
        if score < piso or distancia < margem:
            return None
        lido.append(rotulo)
    return "".join(lido)


def ler_celula(
    bgr: np.ndarray,
    moldes: dict[str, np.ndarray],
    piso: float,
    margem: float,
    *,
    valor_minimo: int,
) -> str | None:
    """O texto de UMA celula de numero, ou `None`. Nunca levanta.

    Segmenta com `segmentar_glifos_no_brilho` (a convencao de faixa
    compartilhada) e classifica com `ler_glifos`. E so a composicao das duas —
    existe para que o chamador nao precise repetir a sequencia e escolher a
    mascara errada.

    `valor_minimo` E SOMENTE-NOMEADO E NAO TEM VALOR DE FABRICA. Ele e o piso de
    brilho da mascara, e cada coluna de numero tem o seu: o das colunas de moeda
    e `identidade.VALOR_MINIMO_DO_TEXTO`, e o da coluna Quantity e
    `mercado_limiar_de_brilho_da_quantidade`, MEDIDO no censo pelo 02-07. Um
    default aqui seria constante magica no caminho que decide preco e
    quantidade.

    A MASCARA E A SEGMENTACAO RECEBEM O MESMO `valor_minimo`, e isso nao e
    detalhe: segmentar num piso e pontuar em outro produziria runs apontando
    para colunas que a mascara nao tem, e o casamento leria lixo com confianca.
    """
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return None
    try:
        faixa, runs = segmentar_glifos_no_brilho(bgr, valor_minimo)
        if faixa is None or not runs:
            return None
        mascara = (mascara_de_numero(bgr, valor_minimo) * 255).astype(np.uint8)
        return ler_glifos(mascara, faixa, runs, moldes, piso, margem)
    except Exception as erro:  # noqa: BLE001 - roda dentro do tick
        log.debug("leitura de celula falhou neste recorte: %s", erro)
        return None


def ler_celula_de_numero(
    bgr: np.ndarray,
    moldes: dict[str, np.ndarray],
    piso: float,
    margem: float,
    *,
    valor_minimo: int,
) -> int | None:
    """O valor da celula de MOEDA, em CENTESIMOS como inteiro. Nunca float.

    Inteiro e nao float porque a acumulacao de erro de ponto flutuante entraria
    pela porta dos fundos exatamente onde o parsing a evitou: a Fase 3 soma e
    compara esses valores ao longo de dias.

    A VIRGULA E AMBIGUA E A DESAMBIGUACAO VEM DO SUFIXO, NAO DO NUMERO.
    `5,000,000 Adena` e `62,00 XM Coin` aparecem na mesma tela, e `XM Coin` e
    `Adena` sao moldes de primeira classe entre os 13 ja cortados. Nenhum PONTO
    apareceu como separador em 335 frames do censo. Nesta coluna — o `Total` do
    layout de negociacao — a leitura e sempre de MOEDA, e por isso ela sempre
    termina em `,dd`; a leitura de sufixo entra quando a fase suportar a aba
    Adena, que hoje o portao de layout recusa inteira.

    Duas peneiras, nesta ordem: a gramatica (`numero_valido`) e a conversao de
    moeda. As duas dizem `None` na duvida.

    O `valor_minimo` DESTA COLUNA CONTINUA SENDO O COMPARTILHADO (180), e o
    02-07 nao o mexeu — ele so deixou de ser implicito. A razao e medida: a
    palavra de sufixo (`XM Coin`, `Adena`) vive DENTRO deste recorte, entre
    V = 120 e V = 173, e o piso 180 e exatamente o que a mantem FORA da celula.
    Sondado em tres frames, com o piso em 170 o `18,90` vira `18,907` e o score
    cai de 1,000 para 0,293. Baixar o piso desta coluna nao melhora nada e
    quebra tudo.
    """
    lido = ler_celula(bgr, moldes, piso, margem, valor_minimo=valor_minimo)
    if not numero_valido(lido):
        return None
    return centesimos_de_moeda(lido)


def ler_celula_de_quantidade(
    bgr: np.ndarray,
    moldes: dict[str, np.ndarray],
    piso: float,
    margem: float,
    *,
    valor_minimo: int,
) -> int | None:
    """A quantidade da linha, inteira. `None` quando nao da para afirmar.

    Ela existe separada de `ler_celula_de_numero` porque a coluna Quantity NAO
    tem casa decimal: `48` e quarenta e oito, e nao quarenta e oito centesimos.
    Ler as duas colunas pela mesma funcao teria dividido a quantidade por cem
    calado, que e o tipo de erro que sobrevive a revisao por parecer um numero.

    `numero_valido` e obrigatoria aqui e nao e redundante:
    `inteiro_de_quantidade` sozinha aceita `1234`, mas a tela escreveria
    `1,234` — e um `1234` lido significa que a virgula do milhar caiu. E a
    gramatica que ve isso.

    O DIGITO `1` DESTA COLUNA NAO SE LE, E ISSO ESTA MEDIDO. O texto da coluna
    Quantity e desenhado mais APAGADO que o da coluna Total: em
    `pagina-cheia/frame_000010` o tronco do `1` da quantidade tem V = 177,
    ABAIXO do piso 180 de `identidade.mascara_de_texto`, enquanto o tronco do
    `1` do `100,00` da coluna Total tem V = 205. A mascara fica so com a serifa
    e a base, o casamento devolve 0,2988 contra o molde `1` (que vale -0,1810),
    o piso de leitura 0,4698 reprova, e a celula cai INTEIRA. A falha e FECHADA,
    que e o comportamento certo — mas o custo e alto, porque a maioria das
    linhas do mercado tem quantidade 1.

    O CONSERTO CHEGOU NO 02-07, E ELE E UM NUMERO MEDIDO. Ele segue o mesmo
    padrao que `VALOR_MINIMO_DO_SUFIXO` ja usou para as palavras `XM Coin` e
    `Adena` (piso 120, medido, porque elas ficam inteiras abaixo de 180): um
    piso de brilho PROPRIO da coluna, que chega por `valor_minimo` a partir de
    `mercado_limiar_de_brilho_da_quantidade` no `calibration.json`. Ele nao e
    inventado aqui — escrever um numero novo sem medi-lo e exatamente a
    constante magica que este projeto recusa —, e a medicao que o produziu esta
    no SUMMARY do 02-07, com a tabela de TODOS os pisos candidatos, os tres
    baldes de cada um e as DUAS folgas.

    O PISO TEM TETO, E O TETO E O QUE DIMENSIONA O RISCO. Baixa-lo demais nao
    volta a falhar FECHADO: passa a falhar ABERTO. Sondado em
    `scroll-transicao/frame_000016`, com o piso em 150 o `30` da quantidade vira
    `38` com score 0,724 e margem 0,127 — os dois ACIMA do piso de leitura
    0,4698 e da margem 0,0370, entao ele atravessa as duas peneiras e vira
    numero errado no CSV. Por isso a ferramenta que mediu o piso recusa propor
    quando existe UMA leitura divergente do rotulo derivado, e por isso o piso
    gravado e sempre um piso que foi MEDIDO — nunca um ponto entre dois que
    foram.
    """
    lido = ler_celula(bgr, moldes, piso, margem, valor_minimo=valor_minimo)
    if not numero_valido(lido):
        return None
    return inteiro_de_quantidade(lido)


# ---------------------------------------------------------------------------
# A guarda de cruzamento: o `Total` confrontado com `Unit price x Quantity`
# ---------------------------------------------------------------------------
#
# POR QUE ELA EXISTE, e por que nenhuma outra peneira faz o servico dela.
#
# O par `0`x`8` e o mais estreito do sistema inteiro: margem minima MEDIDA de
# 0,0370 sobre recortes reais, com o pior `0` casando 0,8249 contra o molde do
# `8`. Uma substituicao `0` -> `8` no `Total` MANTEM a gramatica do numero
# intacta, entao `numero_valido` nao a pega; e o estabilizador de pagina compara
# duas leituras do MESMO motor sobre a MESMA pagina, entao ele tambem nao — dois
# frames concordam no mesmo erro. O cruzamento e a unica conferencia disponivel
# que vem de OUTRO lugar da tela.
#
# ESTA MEDICAO FOI FEITA, E ELA REPROVOU. O registro da refutacao fica aqui de
# proposito, no padrao de `ocr.py:34-52`: este projeto documenta numero medido, e
# UM NUMERO QUE CAIU PRECISA DIZER QUE CAIU, senao ele volta na proxima leitura.
#
# `tools/medir_leitura_de_glifo.py` varreu 478 frames e 55.342 glifos das 8
# gravacoes de campo (02-02) e emitiu, na linha de formato fixo que o 02-06 le:
#
#     GUARDA REPROVADA por tolerancia, 1273.0000 centesimos por unidade
#     (maximo 1.0)
#
#     criterio      exigido                          medido
#     fechamento    >= 0,99                          0,9992 — so com tol. 1273
#     tolerancia    <= 1,0 centesimo por unidade     1273,0    CAIU
#     deteccao      >= 0,90                          0,0164    tambem cairia
#
# O fechamento no LIMITE DERIVADO (0,5 por unidade, o que a aritmetica do
# arredondamento permite) fica em apenas 0,6525. Para chegar a 0,99 a tolerancia
# precisaria de 1273 centesimos por unidade — 2.546 vezes o limite derivado. Com
# uma peneira dessas a guarda aprovaria tambem a substituicao que ela existe para
# pegar, e a deteccao de 0,0164 sobre 1.893 substituicoes `0`<->`8` injetadas
# confirma isso diretamente.
#
# ENTAO `mercado_tolerancia_do_cruzamento` ESTA GRAVADA COMO `None`, E A GUARDA
# NAO DESCARTA NADA. Falha fechada vale para a guarda tambem: descartar dado bom
# com um sinal que nao se provou faz da guarda o defeito. O mecanismo degrada
# para OBSERVACAO — o residuo continua sendo calculado, guardado em
# `LinhaLida.residuo_do_cruzamento` e registrado no log —, porque a evidencia
# nao pode se perder so porque a guarda nao ligou.
#
# O QUE FALTA PARA REMEDIR: o portao de LAYOUT so nasceu no 02-04, depois desta
# varredura, entao ela mediu sobre frames de TODOS os layouts. Na aba Adena a
# terceira coluna e `5 mln increment`, normalizada por cinco milhoes de adena e
# NAO por unidade — ali a relacao nao vale por construcao, e nao por erro de
# leitura. Isso explica parte da queda, mas nao toda: mesmo `pagina-cheia`, que e
# negociacao pura, para em 84,2%. O veredito e robusto.

# Meio centesimo por unidade — a DERIVACAO, e nunca a tolerancia de producao.
LIMITE_DERIVADO_POR_UNIDADE = 0.5


def limite_derivado_do_cruzamento(quantidade: int) -> float:
    """O maximo que o residuo pode valer se o unitario e um arredondamento.

    NAO e uma tolerancia escolhida: e a consequencia aritmetica de a tela exibir
    `round(total / quantidade, 2)`. Cada unidade carrega no maximo meio centesimo
    de erro de arredondamento; `quantidade` unidades carregam `quantidade / 2`.

    O caso conhecido do spike fecha: `40,00` por 48 unidades aparece como `0,83`,
    o residuo e `|4000 - 83 x 48| = 16`, e o limite derivado e 24.

    ELE E REFERENCIA, E NAO PENEIRA, e a diferenca importa: o numero que liga a
    guarda em producao e o MEDIDO pelo 02-02 e gravado no `calibration.json`. A
    derivacao existe para dizer se o medido faz sentido — e foi ela que mostrou
    que 1273 nao fazia.

    E O PROPRIO ARREDONDAMENTO E SUSPEITO, MEDIDO NAS FIXTURAS: em
    `janela_negociacao_f005.png`, linha 5, a tela mostra `11,39` por 6 unidades
    com unitario `1,89` — mas `1139 / 6 = 1,8983`, que ARREDONDA para `1,90`. O
    cliente parece TRUNCAR, e nao arredondar, o que dobraria o limite (um
    centesimo por unidade em vez de meio). O residuo ali e 5 contra limite
    derivado 3. Uma observacao sobre uma fixtura nao vira lei — mas ela e mais
    uma explicacao para o fechamento de 0,6525 que reprovou a guarda, e o dia em
    que alguem remedir tem de comecar por aqui.
    """
    return float(quantidade) * LIMITE_DERIVADO_POR_UNIDADE


def residuo_do_cruzamento(
    total: int | None,
    unitario: int | None,
    quantidade: int | None,
) -> int | None:
    """`|total - unitario x quantidade|` em CENTESIMOS. `None` = nao da para dizer.

    ARITMETICA INTEIRA, SEM UMA UNICA DIVISAO (T-02-38). Ponto flutuante entraria
    pela porta dos fundos exatamente onde a leitura o evitou, e um residuo de
    `1e-13` viraria divergencia num numero que fecha.

    `None` quando qualquer um dos tres nao leu, e `None` quando a quantidade e
    zero: multiplicar por zero devolveria o proprio total como "residuo", que e
    uma afirmacao que ninguem fez.
    """
    if total is None or unitario is None or quantidade is None:
        return None
    if int(quantidade) == 0:
        return None
    return abs(int(total) - int(unitario) * int(quantidade))


def cruzamento_confere(
    total: int | None,
    unitario: int | None,
    quantidade: int | None,
    tolerancia: float | None,
) -> bool | None:
    """O `Total` bate com `Unit price x Quantity`? `None` e "NAO OPINO".

    `tolerancia` e em CENTESIMOS POR UNIDADE e NAO TEM VALOR DE FABRICA. Um
    default aqui seria a constante magica que este projeto recusa: o unico numero
    que pode ligar esta guarda e um que alguem mediu, e quem o mediu tem de
    aparecer na chamada. Ele vem de `mercado_tolerancia_do_cruzamento`, no
    `calibration.json`.

    `None` — "nao opino" — sempre que o residuo for `None` (unitario ilegivel,
    linha coberta, coluna vazia, quantidade zero) OU a tolerancia for `None` (a
    guarda esta desligada). E "NAO OPINO" NUNCA VIRA DESCARTE (T-02-36): falha
    fechada e sobre o DADO ilegivel, jamais sobre a ausencia de uma segunda
    opiniao. Quem transforma abstencao em recusa mata linha boa com o silencio de
    uma conferencia que nao existia.

    Hoje ela responde `None` em producao, porque a medicao do 02-02 reprovou e a
    tolerancia esta gravada como `None`. Os numeros da reprovacao estao no bloco
    acima.
    """
    residuo = residuo_do_cruzamento(total, unitario, quantidade)
    if residuo is None or tolerancia is None:
        return None
    return residuo <= float(tolerancia) * int(quantidade)


# ---------------------------------------------------------------------------
# Os cinco motivos de recusa desta fase (D-17)
# ---------------------------------------------------------------------------

# Sao CINCO peneiras com causas diferentes e consertos diferentes, e o usuario
# precisa ler no log qual delas pegou o que:
#
#   oclusao        -> mova a tooltip, ou espere ela sair
#   numero         -> glifo faltando ou a mais na celula; recalibre os moldes
#   cruzamento     -> o Total nao bate com `Unit price x Quantity`; um digito foi
#                     lido por outro sem quebrar a gramatica (tipicamente `0`x`8`)
#   faixa-cinzenta -> nome novo ambiguo demais para agrupar com seguranca
#   discordancia   -> o OCR esta instavel naquela linha
#
# Um motivo unico ("linha ruim") faria os cinco consertos parecerem o mesmo. O do
# cruzamento so aparece com a guarda LIGADA — e ela esta desligada por medicao.
MOTIVO_DA_OCLUSAO = "oclusao"
MOTIVO_DA_GRAMATICA = "numero"
MOTIVO_DO_CRUZAMENTO = "cruzamento"
MOTIVO_DA_FAIXA_CINZENTA = "faixa-cinzenta"
MOTIVO_DA_DISCORDANCIA = "discordancia-entre-escalas"


@dataclass(frozen=True)
class LinhaLida:
    """Uma linha da grade que atravessou as peneiras.

    `total_em_centesimos` e INTEIRO, sempre. `quantidade` e inteiro. Os dois vem
    de colunas lidas de forma independente.

    O UNITARIO EXIBIDO NAO ESTA AQUI, E NUNCA VAI ESTAR. Ele e derivacao
    ARREDONDADA, nao dado: a tela mostra `round(total/quantidade, 2)`, e
    reconstruir o total a partir dele devolve um numero que nunca existiu —
    medido no spike, `40,00` por 48 unidades aparece como `0,83`, e
    `0,83 x 48 = 39,84`. A Fase 3 guarda `Total` e `Quantity`, que sao o que a
    tela afirma. O unitario e LIDO no 02-06, para a guarda de cruzamento
    conferir a aritmetica, e mesmo la ele nao e gravado como preco.

    `residuo_do_cruzamento` E O QUE SOBROU DESSA CONFERENCIA, e nao um preco:
    `|total - unitario x quantidade|` em centesimos, ou `None` quando alguma das
    tres celulas nao leu. Ele e informacao da FASE 2 sobre a propria leitura —
    "estas duas colunas discordam em 80 centesimos" — e existe porque a guarda
    esta DESLIGADA por medicao e a evidencia nao pode se perder por isso.

    SE ELE VAI PARA O CSV E DECISAO DA FASE 3, E ELA NAO SE TOMA AQUI. A Fase 2
    nao persiste nada; o CSV de observacoes e da fase seguinte, e a fronteira nao
    se mexe neste plano.
    """

    indice: int
    chave_da_serie: str
    nome_exibido: str
    total_em_centesimos: int
    quantidade: int
    serie_nova: bool
    residuo_do_cruzamento: int | None


@dataclass(frozen=True)
class Descarte:
    """Uma linha que NAO virou dado, e a peneira que a pegou.

    Descarte nao e leitura e nao e linha vazia: sao tres estados distintos. A
    contagem "li 7, perdi 3" do console (Fase 4) conta descarte como perda e
    linha vazia como nada — confundir os dois faria o fim de uma pagina curta
    parecer falha de leitura.

    NADA disto vai para o CSV (D-17): escrever a linha recusada misturaria
    descarte com dado, que e a confusao que a falha fechada existe para evitar.
    """

    indice: int
    motivo: str


def linha_ocluida(
    cinza_da_linha: np.ndarray,
    sonda: dict | None,
    limiar: float,
) -> bool:
    """Ha alguma coisa desenhada POR CIMA desta linha? Falha FECHADA.

    A RECUSA NUNCA VEM DA CONFIANCA DO CASAMENTO, e esta e a licao do incidente
    27x um nivel acima. A tooltip do jogo e SEMITRANSPARENTE: ela nao apaga o
    numero, ela o mistura — e um numero misturado ainda produz glifos plausiveis,
    com boa confianca e valor errado. Confianca alta sobre pixel adulterado e
    exatamente o modo de falha que esta fase existe para impedir, e nenhum piso
    de casamento o alcanca.

    O SINAL E A UNIFORMIDADE DO FUNDO, e ele e AUTO-REFERENTE: nao precisa saber
    quanto vale o fundo desta pele, desta resolucao ou deste layout. Testar se a
    moda e 48 ou 66 (os dois niveis da listra alternada) FALHA, e a refutacao
    esta medida em `mercado_geometria.nivel_de_fundo_da_linha`: com a tooltip por
    cima, as linhas 2, 4 e 6 de `tooltip/frame_000015` continuam lendo moda 48.

    O limiar de decisao mora AQUI e o numero vem do `calibration.json`
    (`mercado_limiar_de_dispersao_do_fundo`, medido pela varredura do 02-02
    sobre as 8 gravacoes); a MEDICAO mora em `mercado_geometria`. Um corte
    escrito no fonte viajaria de layout em layout sem ser remedido.

    ONDE ELA NAO ALCANCA, E ISSO E MEDIDO. A sonda ve o trecho `dx0..dx1` da
    grade — a metade ESQUERDA, entre o fim dos nomes e o inicio dos numeros.
    Uma tooltip inteiramente a DIREITA dela passa despercebida: em
    `pagina-cheia/frame_000010` a tooltip cobre a coluna Total das linhas 0 a 3
    e a dispersao le 0,0000 nas dez linhas. Quem pega esse caso e a peneira
    seguinte (tudo-ou-nada + gramatica), e e por isso que ha tres e nao uma.

    Sem sonda calibrada, ou com a medicao impossivel, a resposta e `True`:
    "nao da para medir" NAO e "esta limpa", e feature OFF e o unico default
    seguro para um sinal que a Fase 4 vai usar perto do detector de morte.
    """
    if not sonda:
        return True
    if cinza_da_linha is None or getattr(cinza_da_linha, "size", 0) == 0:
        return True
    try:
        dx0 = int(sonda["dx0"])
        dx1 = int(sonda["dx1"])
        folga = int(sonda["folga"])
    except (KeyError, TypeError, ValueError):
        log.warning(
            "mercado_sonda_do_fundo esta sem dx0/dx1/folga utilizaveis (%r) — "
            "a leitura de mercado nao acontece. Recalibre o mercado.",
            sonda,
        )
        return True

    altura = int(cinza_da_linha.shape[0])
    medido = nivel_de_fundo_da_linha(
        cinza_da_linha, (dx0, 0, dx1 - dx0, altura), folga
    )
    if medido is None:
        return True
    return bool(medido[1] > limiar)


def linha_vazia(bgr_da_linha: np.ndarray) -> bool:
    """Nao ha CONTEUDO nenhum neste retangulo — nem icone, nem glifo (D-12).

    DECIDIDA POR AUSENCIA DE CONTEUDO, NUNCA POR COR DE FUNDO. A grade tem
    listra alternada, entao ha DOIS fundos para linha cheia e DOIS para linha
    vazia; um teste de cor decidiria pelo motivo errado e acertaria por acidente
    ate parar de acertar.

    O piso usado e o MAIS PERMISSIVO dos dois que este projeto ja mediu — o do
    sufixo (V > 120), e nao o do texto (V > 180) —, porque a afirmacao aqui e a
    mais forte possivel: nem no piso mais baixo ha pixel de conteudo. Medido nas
    duas paridades de banda de `pagina-cheia/frame_000028`:

        linha vazia  (banda impar)   V maximo  68   pixels acima de 120:     0
        linha vazia  (banda par)     V maximo  55   pixels acima de 120:     0
        linha cheia  (banda impar)   V maximo 255   pixels acima de 120: 1.771
        linha cheia  (banda par)     V maximo 255   pixels acima de 120: 2.445

    Nao ha zona cinzenta a dividir: ha um vale vazio entre 68 e 120.

    ELA NAO RECEBE OS MOLDES, e a omissao e deliberada. O plano previa
    `linha_vazia(bgr, moldes)`, mas nenhum molde participa da decisao: a
    pergunta e "ha pixel de conteudo", nao "ha glifo conhecido". Um parametro
    que a funcao nao usa e uma promessa que ela nao cumpre, e o proximo
    mantenedor gastaria tempo procurando onde os moldes entram.

    Linha vazia marca o FIM DA PAGINA. Ela nao e descarte (nao houve falha) nem
    leitura (nao ha dado), e a distincao importa para a contagem do console.
    """
    if bgr_da_linha is None or getattr(bgr_da_linha, "size", 0) == 0:
        return True
    return not bool(mascara_do_sufixo(bgr_da_linha).any())


def ler_linha(
    indice: int,
    bgr_da_linha: np.ndarray,
    recorte_do_nome: np.ndarray,
    recorte_do_total: np.ndarray,
    recorte_da_quantidade: np.ndarray,
    recorte_do_unitario: np.ndarray,
    *,
    moldes: dict[str, np.ndarray],
    piso: float,
    margem: float,
    valor_minimo_do_numero: int,
    valor_minimo_da_quantidade: int,
    sonda: dict | None,
    limiar_de_dispersao: float,
    tolerancia_do_cruzamento: float | None,
    catalogo: dict[str, EntradaDoCatalogo],
    corte_de_similaridade: float,
    piso_de_similaridade: float,
    ler_texto,
    ler_texto_conferencia,
) -> LinhaLida | Descarte | None:
    """Uma linha da grade, de pixels a valor. `None` quando ela esta VAZIA.

    NUNCA LEVANTA, no modelo de `ocr._ler`: ela roda dentro do tick. Uma excecao
    aqui pararia o scanner de olhar a party.

    A ORDEM DO PIPELINE E A DECISAO PRINCIPAL DESTA FUNCAO, e cada passo esta
    onde esta por um motivo medido:

    1. LINHA VAZIA. Nao ha o que ler nem o que recusar; o laco da pagina para.
    2. SONDA DE OCLUSAO, antes de tudo o que custa. Uma linha coberta cai sem
       pagar ~7 ms de OCR por ela. E o recorte de coluna sozinho NAO fecha o
       buraco: medido, com a tooltip por cima da propria coluna do nome, o OCR
       devolveu frases inteiras da tooltip como se fossem nome de item. LEIT-05
       reduz a superficie; a sonda e que a fecha.
    3. AS TRES COLUNAS DE NUMERO, que custam 13 casamentos por run — ordens de
       grandeza menos que os ~7 ms do OCR. Uma linha cujo preco nao se le nao vai
       virar dado de jeito nenhum, entao pagar OCR por ela seria pagar por nada.
    4. A GUARDA DE CRUZAMENTO, depois das tres celulas e depois da gramatica, e
       ainda ANTES do nome. A ordem tem razao: a gramatica pega glifo perdido ou
       a mais e custa tres linhas, enquanto a guarda pega SUBSTITUICAO e custa
       uma leitura de coluna a mais — gastar a cara antes da barata seria
       desperdicio, e mascararia qual das duas recusou. E ela vem antes do OCR
       pela mesma razao do passo 3: uma linha que a guarda derruba nunca vira
       dado.
    5. O NOME, lido pelas DUAS escalas, e o acordo entre elas.

    A TERCEIRA COLUNA DE NUMERO E O UNITARIO, E ELA ENTROU NO 02-06 — com o seu
    unico consumidor, a guarda de cruzamento. Ate a onda anterior ler essa coluna
    teria sido leitura morta, e leitura morta envelhece sem que nada denuncie.
    Ela e lida para CONFERIR e nunca guardada como preco: reconstruir o total a
    partir dela devolveria `0,83 x 48 = 39,84` onde a tela diz `40,00`.

    O unitario ILEGIVEL nao derruba a linha — ele so cala a guarda.

    SAO DOIS PISOS DE BRILHO E NAO UM, E A RAZAO E MEDIDA. As colunas de MOEDA
    (`Total` e `Unit price`) recebem `valor_minimo_do_numero`, o piso
    COMPARTILHADO; a coluna Quantity recebe `valor_minimo_da_quantidade`, o piso
    PROPRIO dela, medido no censo pelo 02-07. As duas faixas sao DISJUNTAS:
    a coluna de moeda carrega a palavra de sufixo DENTRO do proprio recorte, e a
    palavra vive entre V = 120 e V = 173 — sondado, `18,90` vira `18,907` ja no
    piso 170 —, enquanto o tronco do `1` da Quantity fica a V = 177 e exige um
    piso ABAIXO dele. Nao existe piso global, e um parametro so seria uma
    afirmacao de que existe.

    Os dois chegam SEM VALOR DE FABRICA, pela regra do charter deste modulo.

    NAO HA RAMO DEDICADO A MARCACAO DE ALVO (D-16). Ela e opaca e previsivel, e
    o mesmo detector de fundo que pega a tooltip pega ela. Um `if` proprio seria
    um caminho a mais para manter e uma promessa a mais para quebrar.
    """
    try:
        if linha_vazia(bgr_da_linha):
            return None

        cinza = (
            bgr_da_linha
            if bgr_da_linha.ndim == 2
            else cv2.cvtColor(bgr_da_linha, cv2.COLOR_BGR2GRAY)
        )
        if linha_ocluida(cinza, sonda, limiar_de_dispersao):
            return _recusar(indice, MOTIVO_DA_OCLUSAO, "fundo nao uniforme")

        total = ler_celula_de_numero(
            recorte_do_total,
            moldes,
            piso,
            margem,
            valor_minimo=valor_minimo_do_numero,
        )
        if total is None:
            return _recusar(
                indice, MOTIVO_DA_GRAMATICA, "a coluna Total nao se leu inteira"
            )
        quantidade = ler_celula_de_quantidade(
            recorte_da_quantidade,
            moldes,
            piso,
            margem,
            valor_minimo=valor_minimo_da_quantidade,
        )
        if quantidade is None:
            return _recusar(
                indice,
                MOTIVO_DA_GRAMATICA,
                "a coluna Quantity nao se leu inteira",
            )
        # A TERCEIRA leitura. Ela usa a MESMA `ler_celula_de_numero` das outras
        # duas, com o mesmo piso, a mesma margem E O MESMO PISO DE BRILHO do
        # `Total`: o unitario tambem e moeda, carrega a mesma palavra de sufixo
        # dentro do recorte, e uma segunda opiniao lida por regra diferente
        # seria outra opiniao sobre outra coisa.
        unitario = ler_celula_de_numero(
            recorte_do_unitario,
            moldes,
            piso,
            margem,
            valor_minimo=valor_minimo_do_numero,
        )

        residuo = residuo_do_cruzamento(total, unitario, quantidade)
        confere = cruzamento_confere(
            total, unitario, quantidade, tolerancia_do_cruzamento
        )
        if confere is False:
            return _recusar(
                indice,
                MOTIVO_DO_CRUZAMENTO,
                f"total={total} unitario={unitario} quantidade={quantidade} "
                f"residuo={residuo} estourou a tolerancia medida de "
                f"{tolerancia_do_cruzamento} centesimos por unidade "
                f"(limite {float(tolerancia_do_cruzamento) * quantidade})",
            )
        _observar_o_cruzamento(
            indice, total, unitario, quantidade, residuo, tolerancia_do_cruzamento
        )

        return _ler_o_nome(
            indice,
            recorte_do_nome,
            total,
            quantidade,
            residuo,
            catalogo,
            corte_de_similaridade,
            piso_de_similaridade,
            ler_texto,
            ler_texto_conferencia,
        )
    except Exception as erro:  # noqa: BLE001 - roda dentro do tick
        log.debug("leitura da linha %d falhou: %s", indice, erro)
        return _recusar(indice, MOTIVO_DA_GRAMATICA, f"excecao contida: {erro}")


def _observar_o_cruzamento(
    indice: int,
    total: int,
    unitario: int | None,
    quantidade: int,
    residuo: int | None,
    tolerancia: float | None,
) -> None:
    """A rota da guarda REPROVADA: registrar em vez de descartar.

    So fala quando ha o que dizer — quando o residuo estoura o LIMITE DERIVADO,
    que e a unica referencia disponivel enquanto nao ha tolerancia medida que
    preste. Logar toda linha encheria o arquivo rotativo de zeros e afogaria as
    linhas que importam.

    Cala inteiramente com a guarda LIGADA: ali quem fala e o descarte, e dois
    registros para o mesmo evento fariam a contagem do console mentir.
    """
    if tolerancia is not None or residuo is None:
        return
    if residuo <= limite_derivado_do_cruzamento(quantidade):
        return
    log.info(
        "linha %d OBSERVACAO do cruzamento: total=%d unitario=%s quantidade=%d "
        "residuo=%d acima do limite derivado %.1f. A guarda esta DESLIGADA "
        "(medicao do 02-02 REPROVADA) — nada foi descartado.",
        indice,
        total,
        unitario,
        quantidade,
        residuo,
        limite_derivado_do_cruzamento(quantidade),
    )


def _ler_o_nome(
    indice: int,
    recorte_do_nome: np.ndarray,
    total: int,
    quantidade: int,
    residuo_do_cruzamento_da_linha: int | None,
    catalogo: dict[str, EntradaDoCatalogo],
    corte_de_similaridade: float,
    piso_de_similaridade: float,
    ler_texto,
    ler_texto_conferencia,
) -> LinhaLida | Descarte:
    """O ACORDO ENTRE AS DUAS ESCALAS — o mecanismo inteiro de D-01 e D-02.

    A coluna do nome e recortada UMA vez e lida DUAS: com a escala barata (2x) e
    com a de conferencia (3x). CADA leitura e agrupada contra o catalogo, e a
    linha so passa quando as duas caem na MESMA `chave_da_serie`.

    ISTO PRECISA ESTAR ESCRITO, e o motivo e estrutural: duas leitoras injetadas
    e nunca confrontadas produzem uma pagina aceita que passa em TODO teste
    desta fase, porque o resultado de uma leitura so tambem e uma `LinhaLida`
    valida. Uma segunda opiniao que nunca e pedida e indistinguivel de nao ter
    segunda opiniao. O criterio que prende isto conta, sobre fixtura conhecida,
    as linhas em que AMBAS foram chamadas.

    O PREDICADO E "MESMA SERIE", NAO IGUALDADE DE STRING, e a diferenca esta
    medida: a igualdade estrita acerta 30 de 60 linhas em 6 frames, e em
    `scroll-transicao/frame_000016` acerta 0 de 10 — a pagina inteira perdida por
    um `I` contra um `1`. A diversidade de metodo de D-01 fica preservada porque
    um erro de metodo REAL (um nome lido como OUTRO item) leva as duas escalas a
    series diferentes e a linha cai; o ruido de 1 a 2 caracteres nao.

    A RESSALVA MEDIDA EM 2026-08-30: o exemplo que D-02 citava — `Lv. I` contra
    `Lv. 1` — NAO e absorvido, porque a trava de digitos de `agrupar` chega antes
    da similaridade e as assinaturas sao `''` e `'1'`. Sao 311 de 3.511 linhas
    limpas (8,86%) que morrem assim, e o usuario aceitou o custo de olhos abertos
    ao escolher `ocr-estrito` no portao do 02-03. O que o agrupamento absorve e o
    ruido SEM digito (`Chll`/`Doll`, `Kng`/`King`).

    O `nome_exibido` VEM SEMPRE DA ESCALA DE CONFERENCIA (3x), por regra escrita
    e nao por acaso de ordem: duas execucoes sobre o mesmo frame tem de gravar o
    mesmo rotulo, e escolher "a primeira que leu" faria o rotulo depender da
    ordem em que o codigo calha de chamar as duas.

    A 3x MANDA E A 2X CONFERE, COM UMA ENTRADA PROVISORIA. A ordem importa e nao
    e arbitraria — esta e a mecanica que `tools/medir_agrupamento_de_nome.py`
    MEDIU nas 8 gravacoes, e ela e reproduzida aqui, nao reinventada. Com as duas
    leituras resolvidas contra o MESMO catalogo antigo, uma PRIMEIRA aparicao em
    que as escalas discordam num caractere criaria DUAS series novas de chaves
    diferentes e a linha morreria: nenhum item novo cujas duas leituras nao
    fossem identicas entraria jamais no catalogo, e a faixa de ruido que D-02
    existe para absorver nunca seria exercitada — o predicado teria virado
    igualdade de string pela porta dos fundos, que e exatamente a rota
    `ocr-igualdade` que o 02-03 recusou por dominancia estrita.

    Entao: a 3x resolve primeiro; se ela abre serie nova, essa serie entra como
    PROVISORIA na lista contra a qual a 2x e resolvida. Se a 2x cair nela, a
    linha passa; se nao cair, a provisoria e jogada fora e nada e gravado.
    """
    barato = ler_texto(recorte_do_nome)
    caro = ler_texto_conferencia(recorte_do_nome)

    entradas = list(catalogo.values())
    veredito_caro = agrupar(
        caro,
        assinatura_por_ocr(caro),
        entradas,
        corte_de_similaridade,
        piso_de_similaridade,
    )
    if veredito_caro.chave is not None and veredito_caro.nova:
        entradas = entradas + [
            EntradaDoCatalogo(
                chave=veredito_caro.chave,
                nome=caro,
                assinatura=assinatura_por_ocr(caro),
            )
        ]
    veredito_barato = agrupar(
        barato,
        assinatura_por_ocr(barato),
        entradas,
        corte_de_similaridade,
        piso_de_similaridade,
    )

    if veredito_barato.chave is None or veredito_caro.chave is None:
        # A faixa cinzenta e a leitura vazia chegam as duas por aqui, e sao
        # causas diferentes: a primeira e um nome novo ambiguo demais, a segunda
        # e o OCR nao ter lido nada. `agrupar` ja distingue as duas no texto do
        # motivo, e a distincao vale porque os consertos sao diferentes.
        if _e_faixa_cinzenta(veredito_barato) or _e_faixa_cinzenta(veredito_caro):
            return _recusar(
                indice,
                MOTIVO_DA_FAIXA_CINZENTA,
                f"2x=>>>{barato}<<< 3x=>>>{caro}<<<",
            )
        return _recusar(
            indice,
            MOTIVO_DA_DISCORDANCIA,
            f"uma escala so leu. 2x=>>>{barato}<<< 3x=>>>{caro}<<<",
        )

    if veredito_barato.chave != veredito_caro.chave:
        return _recusar(
            indice,
            MOTIVO_DA_DISCORDANCIA,
            f"2x=>>>{barato}<<< ({veredito_barato.chave}) "
            f"3x=>>>{caro}<<< ({veredito_caro.chave})",
        )

    return LinhaLida(
        indice=indice,
        chave_da_serie=veredito_caro.chave,
        nome_exibido=caro,
        total_em_centesimos=total,
        quantidade=quantidade,
        serie_nova=bool(veredito_caro.nova),
        residuo_do_cruzamento=residuo_do_cruzamento_da_linha,
    )


def _e_faixa_cinzenta(veredito) -> bool:
    """A faixa cinzenta de `agrupar`: nao agrupou E nao criou serie."""
    return veredito.chave is None and "FAIXA CINZENTA" in veredito.motivo


def _recusar(indice: int, motivo: str, detalhe: str) -> Descarte:
    """A recusa vai para o log com os delimitadores `>>><<<`, sem rate-limit.

    A forma e a de `manutencao._registrar_desacordo` (`:506-527`), e as duas
    decisoes dele valem aqui pelas mesmas razoes: os delimitadores porque espaco
    em branco importa (`Lv. 1` e `Lv.1` sao leituras diferentes), e a AUSENCIA de
    limitacao de repeticao porque o log rotativo e a unica ferramenta de forense
    pos-farm do projeto — sao exatamente estas linhas que respondem "por que nao
    gravou".
    """
    log.warning("linha %d RECUSADA (%s): %s", indice, motivo, detalhe)
    return Descarte(indice=indice, motivo=motivo)


# ---------------------------------------------------------------------------
# O portao de layout (D-09 e D-11)
# ---------------------------------------------------------------------------


def mascara_do_cabecalho(banda: np.ndarray, corte: int) -> np.ndarray:
    """A banda do cabecalho com o corte de brilho aplicado, tudo abaixo zerado.

    E EXATAMENTE o desenho que `calibrar_mercado.sugerir_o_molde_do_cabecalho`
    gravou no `calibration.json`: `np.where(V > corte, V, 0)` sobre o canal V.
    Comparar o cru com o cortado seria comparar convencoes, e o numero deixaria
    de significar a mesma coisa dos dois lados.

    O CORTE E O QUE REMOVE A SETA DE ORDENACAO. Ela mora DENTRO da celula do
    cabecalho e ANDA de coluna conforme o usuario reordena a tabela; sem o corte,
    o molde casaria uma ordenacao e recusaria a outra. Medido: a mesma janela
    ordenada por `Goods` e por `Unit price` casa 1,0000 nas duas com o corte
    aplicado.

    O corte vem do ARQUIVO e nao do fonte porque foi medido em UMA resolucao e
    UMA pele (a suposicao A2 da pesquisa, mitigada e nao fechada).
    """
    valor = banda if banda.ndim == 2 else cv2.cvtColor(banda, cv2.COLOR_BGR2HSV)[
        :, :, 2
    ]
    return np.where(valor > int(corte), valor, 0).astype(np.uint8)


def casamento_do_cabecalho(
    banda: np.ndarray, molde: np.ndarray, corte: int
) -> float:
    """O quanto esta banda parece o cabecalho calibrado. `0.0` no degenerado.

    UMA POSICAO SO, com `casamento_da_ancora`, que e o padrao da casa e reusa
    codigo ja medido: quem chama ja localizou o painel, entao deslizar o molde
    nao daria nada a quem esta certo e daria quase quatro decimos a quem esta
    errado (`mercado_visao.casamento_da_ancora` carrega a medicao).

    Medido sobre as quatro bandas versionadas, com o molde de negociacao:

        cabecalho_negociacao_goods.png       1,0000   PASSA
        cabecalho_negociacao_unitprice.png   1,0000   PASSA
        cabecalho_adena.png                  0,1331   recusa
        cabecalho_busca.png                 -0,0027   recusa

    O vao e enorme e o limiar de 0,73 (herdado de `CASAMENTO_MINIMO_DA_ANCORA`,
    o unico limiar de casamento ja medido em campo neste projeto) cai bem no meio
    dele.
    """
    if banda is None or getattr(banda, "size", 0) == 0:
        return 0.0
    if molde is None or getattr(molde, "size", 0) == 0:
        return 0.0
    return casamento_da_ancora(mascara_do_cabecalho(banda, corte), molde)


def layout_confere(
    janela: np.ndarray,
    origem: tuple[int, int],
    dx_da_grade: int,
    cabecalho: dict | None,
    molde: np.ndarray | None,
    limiar: float | None,
) -> bool:
    """A pagina na tela E o layout calibrado? Falha FECHADA, nunca `raise`.

    Recorta a banda do cabecalho na posicao CONHECIDA — o `dy`, a `altura` e a
    `largura` gravados, mais o `dx` da grade — aplica o corte de brilho gravado e
    casa contra o molde numa posicao so.

    O `dx_da_grade` chega por parametro porque ele NAO esta no dict do cabecalho,
    e a ausencia e deliberada: a banda tem exatamente a largura da grade e comeca
    onde ela comeca, entao gravar o `dx` duas vezes criaria duas verdades para
    uma so geometria — e um dia elas discordariam.

    SEM `mercado_cabecalho_de_coluna`, SEM LIMIAR, OU COM A BANDA FORA DA JANELA,
    A RESPOSTA E `False` — a leitura de mercado simplesmente nao acontece, com
    aviso alto de quem chama, e NUNCA um `raise` no arranque. Feature OFF e o
    unico default seguro para um sinal que a Fase 4 vai usar perto do detector de
    morte (`mercado_visao.py:465-467`).
    """
    if not cabecalho or molde is None or not limiar:
        return False
    if janela is None or getattr(janela, "size", 0) == 0:
        return False
    try:
        ox, oy = origem
        x = ox + int(dx_da_grade)
        y = oy + int(cabecalho["dy"])
        altura = int(cabecalho["altura"])
        largura = int(cabecalho["largura"])
    except (KeyError, TypeError, ValueError):
        return False
    if altura <= 0 or largura <= 0 or x < 0 or y < 0:
        return False
    if y + altura > janela.shape[0] or x + largura > janela.shape[1]:
        return False

    banda = janela[y : y + altura, x : x + largura]
    corte = int(cabecalho.get("corte_de_brilho", 0))
    return casamento_do_cabecalho(banda, molde, corte) >= float(limiar)
