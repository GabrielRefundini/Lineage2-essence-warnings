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
from .mercado_catalogo import (
    CHAVE_DA_SERIE_DA_ADENA,
    NOME_EXIBIDO_DA_ADENA,
    EntradaDoCatalogo,
    agrupar,
    assinatura_por_ocr,
)
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


# ---------------------------------------------------------------------------
# A GEOMETRIA DO GLIFO — DERIVADA dos moldes, e nunca de uma chave (02-08)
# ---------------------------------------------------------------------------


def larguras_de_molde(moldes: dict[str, np.ndarray]) -> tuple[int, ...]:
    """As larguras ORDENADAS dos moldes de UM caractere. Sem repeticao.

    Sobre os 13 moldes de producao ela devolve `(1, 4, 6)`: a virgula, os
    digitos, e o `4`. Os moldes de PALAVRA (`Adena` 35 px, `XM Coin` 44 px)
    ficam de fora pela MESMA regra que `pontuar_glifos` ja aplica
    (`len(rotulo) == 1`) — eles nao sao geometria de glifo, e um deles no
    conjunto faria o limite valer 44 e a guarda nunca disparar.

    Ela nasceu em `tools/medir_largura_de_run.py`, que precisou dela primeiro
    para MEDIR, e foi PROMOVIDA para ca quando a producao passou a precisar
    dela — o mesmo caminho de `segmentar_glifos`, `pontuar_glifos`,
    `centesimos_de_moeda` e `mascara_de_numero`. A ferramenta agora IMPORTA
    daqui: duas copias envelheceriam separadas, e a que envelhecesse pior
    mediria com uma convencao enquanto o scanner decide com outra.
    """
    larguras = {
        int(molde.shape[1])
        for rotulo, molde in moldes.items()
        if len(rotulo) == 1 and getattr(molde, "ndim", 0) == 2
    }
    return tuple(sorted(larguras))


def limite_de_glifo_unico(moldes: dict[str, np.ndarray]) -> int | None:
    """A MAIOR largura de um glifo de UM caractere. `None` sem moldes.

    O QUE ELE E. Sobre os moldes de producao ele vale 6, que e a largura do
    molde `4`. Um run mais largo que isso NAO PODE ser um glifo so — e ate o
    02-08 nada perguntava isso, entao ele era casado contra UM molde e virava
    UM digito, com score e margem que atravessavam as duas peneiras.

    POR QUE ELE NAO VIRA CHAVE DO `calibration.json`. Ele e uma FUNCAO dos
    moldes que ja estao la. Gravar uma copia criaria DUAS VERDADES sobre uma so
    geometria, e na recalibracao seguinte a copia envelheceria contra os moldes
    que ela descreve. E o argumento literal que `layout_confere` ja escreve
    sobre o `dx` do cabecalho nao ser gravado duas vezes.

    POR QUE ELE CAI NUM VALE, E NAO NUMA ZONA CINZENTA. MEDIDO em 2026-08-30
    por `tools/medir_largura_de_run.py` sobre as 8 gravacoes do censo — 347
    paginas, 3.458 linhas, 10.374 celulas, portao de layout LIGADO: das 7.099
    celulas que a producao ACEITA hoje nas tres colunas, ZERO tem run de 7, 8,
    9 ou 10 px. As larguras aceitas sao {4, 5, 6} de um lado e {11, 12} do
    outro. Duas populacoes e um vale de quatro niveis entre elas — e por isso o
    custo da guarda e IDENTICO em qualquer limite dentro do vale, que e a
    definicao de um limite bem posto.
    """
    larguras = larguras_de_molde(moldes)
    if not larguras:
        return None
    return int(max(larguras))


def larguras_com_folga(larguras: tuple, folga: int) -> tuple[int, ...]:
    """As larguras permitidas na particao: cada molde, mais ate `folga` colunas.

    A FOLGA DE COLA E O UNICO NUMERO LIVRE DESTE MECANISMO, e por isso ela e a
    unica que mora no `calibration.json`. As larguras vem dos moldes, o limite
    vem das larguras, e so ela nao se deriva de nada: ela conta quantas colunas
    a barra anti-serrilhada de um glifo COMPARTILHA com o vizinho colado. Com
    `folga = 0` a particao so aceita larguras de molde puras; com `folga = 1`
    ela aceita `(1, 2, 4, 5, 6, 7)`.

    AFROUXAR NAO DEGRADA DEVAGAR: ELE ABRE ESPACO PARA INVENTAR. Medido no run
    de 11 px de `053105-mercado-aberto/frame_000105.png` L6, que admite DOIS
    cortes em que TODOS os segmentos passam nas duas peneiras:

        corte   esquerda        direita          texto da celula
        6+5     `4` 0,915       `4` 0,470        `144,44`
        7+4     `4` 0,884       `9` 0,791        `149,44`

    O `0,470` do corte errado esta a 0,0002 ACIMA do piso de leitura 0,4698 — e
    `144,44` passa na gramatica inteira. A aritmetica independente da linha
    (unitario `2,99`, quantidade `50`) exige o total em [149,25; 150,00):
    `149,44` cabe, `144,44` nao. O corte certo e `7+4` — SETE, um a mais que o
    molde —, e e exatamente por isso que a folga existe: o glifo colado ocupa a
    largura do molde MAIS a coluna partilhada.

    `particionar_run` escolhe pelo PIOR segmento, e e isso que a faz preferir
    `7+4` (pior 0,791) a `6+5` (pior 0,470) sem consultar rotulo nenhum. Mas a
    folga so entra MEDIDA: `tools/medir_largura_de_run.py` a varre com passo 1 e
    recusa propor quando UMA celula rotulada le fora do rotulo.
    """
    folga = int(folga)
    permitidas = set()
    for largura in larguras:
        largura = int(largura)
        for extra in range(0, folga + 1):
            permitidas.add(largura + extra)
    return tuple(sorted(w for w in permitidas if w > 0))


def particionar_run(
    mascara: np.ndarray,
    faixa: tuple[int, int],
    inicio: int,
    fim: int,
    moldes: dict[str, np.ndarray],
    piso: float,
    margem: float,
    larguras: tuple,
) -> list[tuple[str, float, float]] | None:
    """O MELHOR corte de um run largo, no formato de `pontuar_glifos`.

    Devolve `[(rotulo, score, margem), ...]` da esquerda para a direita — a
    MESMA forma que `pontuar_glifos` devolve para runs normais, para que
    `ler_glifos` trate os dois casos com um laco so —, ou `None` quando NENHUM
    corte tem todos os segmentos acima do piso E da margem. `None` e falha
    FECHADA, que e o comportamento certo (LEIT-02).

    PROGRAMACAO DINAMICA, E NAO ENUMERACAO DE PARTICOES. `melhor[j]` e o melhor
    par `(pior_score, pior_margem)` para as colunas `[inicio, inicio + j)`, e a
    transicao percorre as larguras permitidas. Cada segmento e PODADO NA HORA
    pelo piso e pela margem — o TUDO OU NADA da celula exigiria isso de qualquer
    jeito, e a poda e o que mantem o custo linear em `W x |larguras|`.

    A ALTERNATIVA FOI MEDIDA E DESCARTADA: a enumeracao de particoes passou de
    10 MINUTOS no censo e foi abortada, porque runs de ate 42 px com larguras de
    1 a 6 dao ate 6^8 composicoes. MEDIDO em 2026-08-30 pelo
    `tools/medir_largura_de_run.py`: a DP custa 7,9 ms por linha larga em media
    e 58,9 ms no PIOR caso do censo — 17x abaixo do tick de 1 Hz. Uma peneira
    que estourasse o tick pararia o scanner de olhar a party, que e o unico
    defeito inaceitavel deste projeto.

    O CRITERIO E O PIOR SEGMENTO, E NAO A SOMA NEM A MEDIA. Um corte com um
    segmento excelente e um pessimo e um corte ERRADO: a celula so entrega texto
    quando TODOS os segmentos passam, entao o que decide entre dois cortes
    validos e o elo mais fraco de cada um. E o que faz `7+4` vencer `6+5` em
    `frame_000105.png` L6 sem consultar rotulo nenhum (ver `larguras_com_folga`).
    """
    largura_total = int(fim) - int(inicio)
    if largura_total <= 0:
        return None
    permitidas = tuple(sorted({int(w) for w in larguras if int(w) > 0}))
    if not permitidas:
        return None

    # `inf` no ponto de partida: `min(inf, score)` e o proprio score, entao o
    # primeiro segmento define o pior sem nenhum caso especial.
    melhor: list[tuple[float, float, tuple] | None] = [None] * (
        largura_total + 1
    )
    melhor[0] = (float("inf"), float("inf"), ())

    for j in range(1, largura_total + 1):
        for largura in permitidas:
            if largura > j:
                break
            anterior = melhor[j - largura]
            if anterior is None:
                continue
            a = int(inicio) + j - largura
            b = int(inicio) + j
            pontuado = pontuar_glifos(mascara, faixa, [(a, b)], moldes)
            if not pontuado:
                continue
            rotulo, score, distancia = pontuado[0]
            if score < piso or distancia < margem:
                continue
            candidato = (
                min(anterior[0], float(score)),
                min(anterior[1], float(distancia)),
                anterior[2] + ((rotulo, float(score), float(distancia)),),
            )
            if melhor[j] is None or candidato[:2] > melhor[j][:2]:
                melhor[j] = candidato

    final = melhor[largura_total]
    if final is None:
        return None
    return list(final[2])


def ler_glifos(
    mascara: np.ndarray,
    faixa: tuple[int, int],
    runs: list[tuple[int, int]],
    moldes: dict[str, np.ndarray],
    piso: float,
    margem: float,
    *,
    largura_maxima_de_glifo: int,
    folga_de_cola: int | None,
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

    A GUARDA DO RUN LARGO MORA AQUI, E O LUGAR FOI ESCOLHIDO POR MEDICAO (02-08)
    ----------------------------------------------------------------------------
    Ate esta onda, um run mais largo que QUALQUER molde era casado contra UM
    molde e virava UM digito. Medido no censo: `44` lia `4`, `149,44` lia
    `14,44`, e nada disso reclamava — falha ABERTA (numero errado e PLAUSIVEL) e
    nao a falha FECHADA que `LEIT-02` exige. Era o unico defeito conhecido da
    Fase 2 que INVENTAVA em vez de descartar.

    A CAUSA E DE GEOMETRIA, E NAO DE BRILHO, E ISSO ESTA VISTO NO PIXEL. A barra
    horizontal do molde `4` ocupa as SEIS colunas da caixa dele. Colado o
    vizinho, a coluna de fronteira fica com tinta, `mascara.any(axis=0)` nao ve
    coluna vazia, e a regra de `segmentar_glifos` — QUALQUER COLUNA VAZIA
    SEPARA, sem tolerancia de lacuna — nao tem o que separar:

        ....#.....#.
        ....#.....#.
        ....#.....#.
        ....#.....#.
        ############   <- as duas barras viraram uma linha continua
        ....#.....#.
        ....#.....#.
        ....#.....#.

    BAIXAR O PISO DE BRILHO NAO RESOLVE: sondado nos pisos 180, 177, 170 e 160 o
    run continua UNICO; subir para 220 separa os dois glifos mas APAGA a coluna
    inteira em outros frames. Mexer no piso de brilho troca um defeito por
    outro, e esta frase existe para poupar uma tarde a quem tentar.

    POR QUE `ler_glifos` E O LUGAR, e nao outra funcao da cadeia. Ela e a UNICA
    que possui as QUATRO coisas que a decisao precisa — a mascara, os moldes, o
    piso e a margem — e ja e dona da regra de TUDO OU NADA, entao a guarda e a
    particao sao a MESMA decisao, no mesmo lugar, sobre o mesmo laco. E ela tem
    UM ponto de chamada de producao (`ler_celula`), contra os 35 de
    `segmentar_glifos` — que alem disso nao tem molde nenhum e nao poderia
    pontuar um corte nem se quisesse. `pontuar_glifos` tambem nao serve: ela nao
    tem piso DE PROPOSITO, para que a medicao dos limiares nao seja circular, e
    a razao ja esta escrita na docstring dela.

    OS DOIS RAMOS, E OS DOIS FALHAM FECHADO. Um run DENTRO do limite segue
    EXATAMENTE o caminho de antes desta onda — quando nenhum run e largo, o
    codigo executado e byte a byte o antigo, e e por isso que as celulas
    estreitas nao mudam um pixel. Um run ACIMA do limite: com `folga_de_cola`
    valendo `None` a celula cai FECHADA (a GUARDA pura, o comportamento SEGURO
    e o default por AUSENCIA da chave); com um inteiro ela e partida por
    `particionar_run`, e cai FECHADA se nenhum corte passar. A diferenca entre
    os dois ramos e so QUANTAS celulas chegam a ler — nunca o que acontece com
    uma leitura duvidosa.

    Os dois parametros novos sao SOMENTE-NOMEADOS e SEM valor de fabrica, pela
    regra do charter deste modulo.
    """
    if not runs:
        return None
    limite = int(largura_maxima_de_glifo)
    ha_run_largo = any(int(fim) - int(inicio) > limite for inicio, fim in runs)

    if not ha_run_largo:
        # O CAMINHO DE ANTES DESTA ONDA, intacto: uma so chamada a
        # `pontuar_glifos` sobre TODOS os runs. Nao e uma reimplementacao
        # equivalente — e o mesmo codigo, e e isso que torna a igualdade das
        # celulas estreitas ESTRUTURAL em vez de estatistica.
        pontuados = pontuar_glifos(mascara, faixa, runs, moldes)
        if not pontuados:
            return None
        lido: list[str] = []
        for rotulo, score, distancia in pontuados:
            if score < piso or distancia < margem:
                return None
            lido.append(rotulo)
        return "".join(lido)

    if folga_de_cola is None:
        # A GUARDA. Sem a folga MEDIDA nao ha como partir o run com seguranca, e
        # entregar o casamento contra UM molde seria a falha ABERTA de novo.
        return None

    permitidas = larguras_com_folga(
        larguras_de_molde(moldes), int(folga_de_cola)
    )
    saida: list[str] = []
    for inicio, fim in runs:
        if int(fim) - int(inicio) <= limite:
            pontuados = pontuar_glifos(mascara, faixa, [(inicio, fim)], moldes)
        else:
            pontuados = particionar_run(
                mascara, faixa, inicio, fim, moldes, piso, margem, permitidas
            )
        if not pontuados:
            return None
        for rotulo, score, distancia in pontuados:
            if score < piso or distancia < margem:
                return None
            saida.append(rotulo)
    return "".join(saida)


def ler_celula(
    bgr: np.ndarray,
    moldes: dict[str, np.ndarray],
    piso: float,
    margem: float,
    *,
    valor_minimo: int,
    folga_de_cola: int | None,
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

    O LIMITE DE GLIFO UNICO E DERIVADO AQUI, E SO AQUI (02-08). Ele NAO entra na
    assinatura desta funcao: `ler_celula` ja recebe os `moldes`, e derivar o
    limite no unico lugar que os tem e o que impede DUAS VERDADES sobre uma so
    geometria. Passa-lo por parametro abriria a porta para o chamador informar
    um limite que nao descreve os moldes que ele mesmo entregou.

    `folga_de_cola` E SOMENTE-NOMEADO E NAO TEM VALOR DE FABRICA, pela mesma
    regra de `valor_minimo`. Ela e apenas REPASSADA: quem decide com ela e
    `ler_glifos`. `None` e legitimo e significa a GUARDA — a celula com run
    largo cai FECHADA —, e e o que a AUSENCIA da chave no `calibration.json`
    produz.
    """
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return None
    try:
        faixa, runs = segmentar_glifos_no_brilho(bgr, valor_minimo)
        if faixa is None or not runs:
            return None
        limite = limite_de_glifo_unico(moldes)
        if limite is None:
            # Sem molde de UM caractere nao ha geometria de glifo — e sem ela
            # `pontuar_glifos` tambem nao teria contra o que casar.
            return None
        mascara = (mascara_de_numero(bgr, valor_minimo) * 255).astype(np.uint8)
        return ler_glifos(
            mascara,
            faixa,
            runs,
            moldes,
            piso,
            margem,
            largura_maxima_de_glifo=limite,
            folga_de_cola=folga_de_cola,
        )
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
    folga_de_cola: int | None,
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
    lido = ler_celula(
        bgr,
        moldes,
        piso,
        margem,
        valor_minimo=valor_minimo,
        folga_de_cola=folga_de_cola,
    )
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
    folga_de_cola: int | None,
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
    lido = ler_celula(
        bgr,
        moldes,
        piso,
        margem,
        valor_minimo=valor_minimo,
        folga_de_cola=folga_de_cola,
    )
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


# Cinco milhoes de adena por incremento — o que a coluna `5 mln increment` da
# aba Adena normaliza.
#
# ELE NAO MORA NO `calibration.json`, PELA MESMA RAZAO DO `SUFIXO_DA_GRADE`
# (`mercado_catalogo.py:99-113`) e do `PISO_DO_RESTO`: `mercado_pagina` EXIGE as
# chaves de mercado presentes e PARA sem elas, entao uma chave nova obrigatoria
# deixaria o scanner MORTO no proximo arranque ate o usuario recalibrar. E este
# aqui nem e numero MEDIDO: e como o jogo ESCREVE a coluna. Quem garante que a
# coluna e essa e o molde de cabecalho, que ja mora na calibracao — grava-lo
# tambem criaria DUAS verdades sobre uma coluna so, e o dia em que elas
# divergissem a quantidade sairia errada por fator inteiro sem nada denunciar.
ADENA_POR_INCREMENTO = 5_000_000


def quantidade_de_adena(
    total: int | None,
    incremento: int | None,
) -> tuple[int, int] | None:
    """A quantidade de adena de uma oferta, DERIVADA das duas colunas de moeda.

    Devolve `(quantidade_em_adena, incrementos)`, ou `None` quando nao da para
    afirmar. FALHA FECHADA, como toda leitura deste modulo.

    (a) A QUANTIDADE NAO E LIDA DA TELA, E ISSO NAO E ATALHO
    ---------------------------------------------------------
    A aba Adena nao tem coluna `Quantity`; quem escreve a quantidade e a coluna
    `Auction List` (`10,000,000 Adena`), e ela **nao se le com os moldes de
    digito deste projeto**. Medido contra `tests/fixtures/mercado/
    janela_adena_f014.png` em SETE pisos de brilho — 180, 200, 210, 220, 230,
    240 e 250 —, `ler_celula` devolve `None` nas dez linhas em todos eles:

        piso 180-200   os digitos de la saem 5-6 px de largura; os moldes,
                       cortados das colunas de moeda, tem 4
        piso 210+      a largura fecha, mas o `0` se PARTE em dois runs de 1-2 px

    O texto da `Auction List` e mais claro e mais grosso (digitos p99 = 246) que
    o das colunas de moeda (Vmax 226-230), de onde os moldes foram cortados. Nao
    ha vale entre as populacoes de largura de run: nao existe piso que resolva.
    O molde de palavra `Adena` tambem nao corresponde — no piso 180 a palavra
    segmenta em QUATRO runs (14, 6, 5, 6), e nao num blob de 35 px.

    (b) AS LEITURAS QUE SUSTENTAM A ROTA DERIVADA
    ----------------------------------------------
    As colunas de moeda, essas, leem EXATAMENTE — com os retangulos de
    NEGOCIACAO, sem tocar um pixel de calibracao. Medido sobre a mesma fixtura,
    `Total Price` e `5 mln increment` linha a linha:

        6200/6200  6499/6499  6500/6500  6600/6600  6700/6700
        6800/6800  6850/6850  7000/7000  7000/7000

    (a decima e a linha 5, tratada em (c)). A coluna `Quantity` de negociacao
    cai sobre VAZIO nas dez e devolve `None` — falha fechada de graca.

    Logo a quantidade vem das duas colunas que leem:
    `ADENA_POR_INCREMENTO x round(total / incremento)`.

    (c) OS DOIS CASOS DIFICEIS, COM AS CONTAS
    ------------------------------------------
        ACEITA   133,33 por 66,66   n=2   |13333 - 2x6666| = 1    limite 1,0
        REJEITA  135,88 por 67,50   n=2   |13588 - 2x6750| = 88   limite 1,0

    O segundo e a LINHA 5 daquela fixtura, e ele e a justificativa desta guarda:
    a tela diz `135,00` e a leitura devolve `13588` — dois `0` lidos como `8`, o
    par de margem mais estreita do sistema (0,0370). A gramatica passa, a sonda
    de oclusao diz limpo (dispersao 0,0000 nas dez linhas) e o acordo entre dois
    frames CONCORDA no erro, porque os dois leem os mesmos pixels. Sem esta
    conta, aquela linha entra no CSV como taxa `135,88` — plausivel e errada.

    ARITMETICA INTEIRA NO JULGAMENTO (T-02-38). O `round` so ESCOLHE o candidato
    `n`; quem DECIDE e a multiplicacao `|total - n x incremento|`, sem divisao
    nenhuma. Ponto flutuante no veredito entraria pela porta dos fundos
    exatamente onde a leitura o evitou.

    O CRITERIO NAO E ESCOLHIDO AQUI: e `limite_derivado_do_cruzamento`, que ja
    existe com a derivacao escrita ao lado. A escala de `n` sao INCREMENTOS e
    nao unidades, e a derivacao continua valendo por construcao — a tela exibe
    `round(total / incrementos, 2)` na coluna do incremento exatamente como
    exibe o unitario na negociacao, entao cada incremento carrega no maximo meio
    centesimo de erro de arredondamento.

    A COMPARACAO E `residuo <= limite`, E O SINAL E LOAD-BEARING. Com `<` o
    caso-bandeira `133,33 / 66,66` REPROVA — residuo 1 contra limite 1,0 — e a
    Adena perde justamente as ofertas de preco quebrado, que sao as que o
    usuario capturou. `<=` tambem e o sentido que `_observar_o_cruzamento` ja
    usa (`if residuo <= limite_derivado_do_cruzamento(quantidade): return`);
    escrever o outro aqui criaria DUAS leituras opostas do MESMO limite.

    (d) O RAMO QUE ACEITA O ARREDONDAMENTO NAO TEM PIXEL NO REPOSITORIO
    -------------------------------------------------------------------
    As nove linhas boas de `janela_adena_f014.png` dividem TODAS exato (residuo
    0). O ramo que aceita residuo > 0 esta exercitado em teste de unidade com
    inteiros literais, o que e nao-vacuo para esta funcao — mas ele e INFERENCIA
    ARITMETICA, e nao medicao sobre pixels. Apertar o limite exigiria material
    com o caso dentro: uma gravacao da aba Adena contendo uma linha cujo
    incremento nao divida o total exatamente (A3).
    """
    if total is None or incremento is None:
        return None
    total = int(total)
    incremento = int(incremento)
    if incremento <= 0 or total <= 0:
        return None
    incrementos = round(total / incremento)
    if incrementos < 1:
        return None
    residuo = abs(total - incrementos * incremento)
    # `<=`, e nao `<`. Ver (c): o caso-bandeira passa por IGUALDADE.
    if residuo <= limite_derivado_do_cruzamento(incrementos):
        return ADENA_POR_INCREMENTO * incrementos, incrementos
    return None


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


class TravaDaObservacao:
    """Que divergencia ja foi observada nesta sessao. Cada uma sai UMA vez.

    O DEFEITO QUE ELA CONSERTA FOI VISTO EM PRODUCAO (sessao de 2026-09-01
    09:38): a pagina do mercado e relida a cada tick, entao a MESMA divergencia
    da MESMA oferta era registrada a 1 Hz. Na sessao real eram DUAS linhas por
    tick — ~7.200 por hora — e o `scanner.log` rotativo perde exatamente a
    forense que ele existe para guardar.

    ELA E IRMA DE `TravaDoDestaque`, E DE PROPOSITO. Mesma doutrina: um anuncio
    por OFERTA distinta, da SESSAO inteira, e `anunciar` devolve o TEXTO em vez
    de um booleano — para nao existir caminho que anuncie sem passar por aqui.
    O destaque foi o primeiro anuncio repetitivo a ganhar trava; esta mensagem
    passou despercebida so por ser outra mensagem.

    A IDENTIDADE E `(total, unitario, quantidade)`, E A DIFERENCA PARA
    `chave_da_observacao` NAO E ESCOLHA — E CONSTRUCAO. Aquela chave e
    `serie + total + quantidade`, e a serie NAO EXISTE neste ponto: o nome e
    lido no passo 5 do pipeline de `ler_linha`, DEPOIS da guarda de cruzamento,
    porque uma linha que a guarda derruba nao deve pagar ~7 ms de OCR. Trocar a
    ordem para alcancar a chave custaria OCR em toda linha recusada, que e o
    oposto do que a ordem foi medida para fazer.

    E OS TRES NUMEROS SAO A IDENTIDADE CERTA PARA ESTA MENSAGEM, e nao um
    substituto pobre: a observacao e sobre a ARITMETICA — `total` contra
    `unitario x quantidade` —, e sao exatamente esses tres que a definem. Duas
    ofertas com a mesma aritmetica tem a mesma divergencia a dizer.

    O INDICE DA GRADE FICA DE FORA. A oferta sobe e desce de linha quando o
    usuario rola o quadro; se o indice travasse, uma rolagem de uma linha
    reanunciaria a pagina inteira — o defeito de volta, disfarcado de
    observacao nova.

    ELA E DO LEITOR, e nao de escopo de modulo: `LeitorDePagina` ja hospeda
    `_layout_ja_recusado`, `_congelamento_ja_avisado` e `_falta_ja_avisada`
    pela mesma razao, e uma trava de modulo faria a segunda sessao sair muda
    sobre divergencias que o usuario nunca viu.

    O CONJUNTO NAO E PODADO. Ele guarda uma tupla de tres inteiros por
    divergencia DISTINTA — e divergencia acima do limite derivado e rara, nao
    a regra —, entao o custo e desprezivel perto do risco de uma poda
    reanunciar o que ja saiu.
    """

    def __init__(self) -> None:
        # PUBLICO, no padrao dos contadores de `LeitorDePagina` e do
        # `ja_anunciadas` de `TravaDoDestaque`: e o que deixa o teste afirmar a
        # identidade escolhida sem espiar o objeto por dentro.
        self.ja_observadas: set[tuple[int, int | None, int]] = set()

    def anunciar(
        self,
        indice: int,
        total: int,
        unitario: int | None,
        quantidade: int,
        residuo: int,
    ) -> str | None:
        """O texto da observacao na PRIMEIRA vez desta divergencia; `None` depois.

        `None` E NAO STRING VAZIA: uma string vazia atravessaria um `if texto:`
        distraido e registraria uma linha em branco por tick.

        QUEM DECIDE SE HA O QUE DIZER E `_observar_o_cruzamento`, e nao esta
        classe. Ela so registra o que ja foi dito: o portao do limite derivado
        e da guarda desligada continua la, um passo acima.

        O INDICE ENTRA NO TEXTO E NAO NA CHAVE — e onde o usuario olha na
        grade, e na primeira ocorrencia ele esta certo.
        """
        chave = (int(total), unitario, int(quantidade))
        if chave in self.ja_observadas:
            return None
        self.ja_observadas.add(chave)
        return (
            f"linha {indice} OBSERVACAO do cruzamento: total={total} "
            f"unitario={unitario} quantidade={quantidade} residuo={residuo} "
            f"acima do limite derivado "
            f"{limite_derivado_do_cruzamento(quantidade):.1f}. A guarda esta "
            f"DESLIGADA (medicao do 02-02 REPROVADA) — nada foi descartado."
        )


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


def sonda_e_uma_banda(sonda: dict | None) -> bool:
    """Esta sonda declara faixa VERTICAL, ou e a geometria antiga?

    Existe para que `mercado_pagina` possa avisar UMA VEZ, na construcao, em vez
    de a cada linha de cada tick. A pergunta e de forma, nao de valor: `dy0` e
    `dy1` presentes e utilizaveis.
    """
    if not sonda:
        return False
    if sonda.get("dy0") is None or sonda.get("dy1") is None:
        return False
    try:
        return int(sonda["dy1"]) > int(sonda["dy0"]) >= 0
    except (TypeError, ValueError):
        return False


def faixa_vertical_da_sonda(
    sonda: dict, altura_da_linha: int
) -> tuple[int | None, int | None]:
    """`(dy0, dy1)` da banda, ou a linha inteira quando a calibracao e antiga.

    `(None, None)` quando `dy0`/`dy1` existem mas nao servem — invertidos,
    negativos, ou nao numericos. Quem chama trata isso como "nao da para medir",
    que e RECUSA, e nunca como "vale a linha inteira": cair no fallback por
    causa de um numero corrompido esconderia o erro em vez de reporta-lo.

    A AUSENCIA dos dois, essa sim, e o fallback legitimo — e a calibracao de
    antes de 2026-09-01, que nao conhecia a banda.
    """
    dy0_bruto = sonda.get("dy0")
    dy1_bruto = sonda.get("dy1")
    if dy0_bruto is None and dy1_bruto is None:
        return 0, int(altura_da_linha)
    try:
        dy0 = int(dy0_bruto)
        dy1 = int(dy1_bruto)
    except (TypeError, ValueError):
        return None, None
    if dy0 < 0 or dy1 <= dy0:
        return None, None
    return dy0, dy1


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

    ONDE ELA MEDE, E POR QUE A DIRECAO MUDOU EM 2026-09-01. A sonda e uma BANDA
    HORIZONTAL FINA que atravessa a linha inteira em x — `dx0..dx1` — dentro de
    uma faixa de altura `dy0..dy1` que fica ACIMA do texto. Ela nao e mais um
    trecho estreito espremido depois da ponta do nome.

    A DIFERENCA E DE PREMISSA, E A PREMISSA ANTIGA ERA FALSA. Ate aqui o desenho
    supunha que existisse uma faixa VERTICAL vazia a direita do nome onde a sonda
    coubesse. Nao existe: a coluna do nome vai de x=42 a x=366 e a de quantidade
    comeca em 366, coladas, e o nome cresce para dentro do espaco que a sonda
    ocuparia. O maior corredor que as linhas limpas deixam livre e de 172 px
    contra frames conferidos, e de 56 a 91 px contra o censo de 3.994 linhas.

    E O CAMPO COBROU ESSA PREMISSA DUAS VEZES, COM UM CARACTERE DE DIFERENCA:

        207..417  ficava sobre 159 px da coluna do nome (49% dela). Morreu
                  contra `Protecting Scroll: Enchant C-grade Armor` — 40
                  caracteres, tinta ate x=246. As quatro linhas dele foram
                  recusadas em 32 ticks seguidos, sobraram 6 linhas contra um
                  piso de 7, e as 31 paginas da sessao morreram. Sem tooltip
                  nenhuma na tela.
        246..396  o conserto de 31/08. Morreu contra `Protecting Scroll: Enchant
                  C-grade Weapon` — 41 caracteres, tinta ate x=255. UM caractere
                  a mais empurrou a tinta 8 px, e a sonda nasceu com margem de
                  -9 px. As DEZ linhas foram recusadas, em todos os frames.

    Mover a sonda uma terceira vez so escolheria qual item quebra a seguir.

    A BANDA NAO DISPUTA ESPACO COM O TEXTO, e e isso que a torna definitiva. A
    linha tem 45 px de altura e o nome ocupa 12 deles. MEDIDO sobre as 120 linhas
    limpas do gabarito ampliado, dentro da janela x[42, 489):

        icone   x[  0, 42)   tinta em dy[ 6, 37]   (fica FORA da janela)
        nome    x[ 42,366)   tinta em dy[15, 26]
        qtd     x[366,489)   tinta em dy[19, 26]
        total   x[489,698)   tinta em dy[ 0, 44]   (fica FORA da janela)
        unit    x[698,872)   tinta em dy[ 0, 44]   (fica FORA da janela)

    Sobram 15 px de margem em cima e 16 embaixo, e NENHUM DOS DOIS ENCOLHE
    QUANDO O NOME CRESCE. A banda escolhida, dy[2, 10), passa 5 px acima do topo
    do texto. Um nome de 60 caracteres continua escrevendo em dy[15, 26].

    A MOLDURA ENTRE LINHAS FOI MEDIDA E REPROVADA, e o registro fica para quem
    tiver a mesma ideia. O separador da grade e desenho fixo da UI, do tamanho
    certo, independente do nome — e mesmo assim nao serve, porque ele e o DEGRAU
    da listra alternada (48 -> 66) e esta primitiva mede UNIFORMIDADE. Sobre um
    degrau a dispersao e ~0,5 por construcao, a mesma magnitude de uma tooltip:
    medido, x[42,489) dy[43,45) le 0,5000 numa linha LIMPA contra 0,4944 sob
    tooltip. Nao ha limiar que separe.

    A BANDA APERTA A PENEIRA EM VEZ DE AFROUXA-LA, e os dois lados foram medidos
    contra o mesmo gabarito ampliado (120 limpas, 10 cobertas):

        sonda           pior LIMPA   tooltip   marca de alvo   folga
        246..396          0,0119     0,3200      0,0208         1,8x
        dy[2,10)          0,0031     0,4944      0,2497        81,2x

    O MARCADOR DE ALVO DEIXA DE SER O GARGALO, e por mecanismo. Em toda sonda
    horizontal o aperto vinha dele (0,077 / 0,022 / 0,021), nunca da tooltip
    (0,32 a 0,62): ele e uma MOLDURA em volta da linha, e uma sonda de 150x41 px
    cruza a borda horizontal dela em ~2 de 41 linhas de pixel. A banda de 447x8
    cruza a mesma borda em 2 de 8 — e le 0,2497, que e 2/8.

    ONDE ELA NAO ALCANCA, E ISSO CONTINUA MEDIDO. A janela e a uniao das colunas
    do nome e da quantidade, entao uma tooltip inteiramente a DIREITA dela passa
    despercebida: em `pagina-cheia/frame_000010` a tooltip cobre a coluna Total
    das linhas 0 a 3 e a dispersao le 0,0000 nas dez. Quem pega esse caso e a
    peneira seguinte (tudo-ou-nada + gramatica), e e por isso que ha tres e nao
    uma. As colunas Total e Unit price NAO podem entrar na janela: a arte delas
    escreve de dy 0 a dy 44 e nao deixa margem vertical nenhuma.

    A DIVIDA DA SONDA ESTREITA ANDA PARA TRAS, e isso e um ganho de graca. O
    bloco `LARGURA_DA_SONDA` de `tools/medir_oclusao.py` registrava que 150 px
    cabem dentro de um vao uniforme do desenho da tooltip com mais facilidade que
    210 px — sonda estreita e sonda que pode se esconder na arte que deveria
    enxergar. A banda tem 447 px de largura: tres vezes mais dificil de esconder.

    SEM `dy0`/`dy1` NA CALIBRACAO, VALE O COMPORTAMENTO ANTIGO — a linha inteira
    em altura. Nao e "aceita tudo": e a geometria de 31/08, que erra caro mas
    erra FECHADO, recusando linha limpa em vez de aprovar linha coberta. O
    usuario que ainda nao rodou `tools/medir_oclusao.py --gravar` fica com ela, e
    `mercado_pagina` avisa uma vez no log em vez de a cada tick.

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

    altura_da_linha = int(cinza_da_linha.shape[0])
    dy0, dy1 = faixa_vertical_da_sonda(sonda, altura_da_linha)
    if dy0 is None or dy1 is None:
        log.warning(
            "mercado_sonda_do_fundo esta com dy0/dy1 impossiveis (%r) — a "
            "leitura de mercado nao acontece. Recalibre o mercado.",
            sonda,
        )
        return True

    medido = nivel_de_fundo_da_linha(
        cinza_da_linha, (dx0, dy0, dx1 - dx0, dy1 - dy0), folga
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
    folga_de_cola: int | None,
    sonda: dict | None,
    limiar_de_dispersao: float,
    tolerancia_do_cruzamento: float | None,
    trava_da_observacao: TravaDaObservacao,
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

    A `trava_da_observacao` CHEGA DE FORA porque ela e da SESSAO e esta funcao e
    do TICK. Ela e quem faz a observacao do passo 4 sair uma vez por divergencia
    em vez de uma vez por tick; sem ela a mesma linha era registrada a 1 Hz
    enquanto a oferta estivesse na tela. Vem sem valor de fabrica, como a
    tolerancia e os dois pisos: um default aqui esconderia quem a forneceu, e um
    `None` silencioso devolveria o defeito inteiro sem nada denunciar.

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

    A FOLGA DE COLA ATRAVESSA A LINHA INTEIRA, E NAO SO UMA COLUNA (02-08). O
    glifo colado nao e um defeito de uma coluna: ele foi medido nas TRES — 14
    celulas de Quantity, 75 de Total e 19 de Unit price entre as que a producao
    aceitava. Entao ela chega uma vez e vai para as tres leituras, como o piso e
    a margem. `None` e legitimo e significa a GUARDA: a celula com run largo cai
    FECHADA, que e o comportamento SEGURO e nao o de antes desta onda.

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
            folga_de_cola=folga_de_cola,
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
            folga_de_cola=folga_de_cola,
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
            folga_de_cola=folga_de_cola,
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
            indice,
            total,
            unitario,
            quantidade,
            residuo,
            tolerancia_do_cruzamento,
            trava_da_observacao,
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


def ler_linha_de_adena(
    indice: int,
    bgr_da_linha: np.ndarray,
    recorte_do_total: np.ndarray,
    recorte_do_incremento: np.ndarray,
    *,
    moldes: dict[str, np.ndarray],
    piso: float,
    margem: float,
    valor_minimo_do_numero: int,
    folga_de_cola: int | None,
    sonda: dict | None,
    limiar_de_dispersao: float,
    catalogo: dict[str, EntradaDoCatalogo],
) -> LinhaLida | Descarte | None:
    """Uma linha da aba ADENA, de pixels a valor. `None` quando ela esta VAZIA.

    NUNCA LEVANTA, no modelo de `ler_linha`: ela roda dentro do tick, e uma
    excecao aqui pararia o scanner que existe para avisar que alguem da party
    morreu (T-05-03).

    A ORDEM DOS PORTOES E A DE `ler_linha` MENOS OS DOIS ULTIMOS PASSOS, e ela
    foi COPIADA e nao reinventada:

        vazia -> oclusao -> Total Price -> 5 mln increment -> cruzamento

    Cada passo esta onde esta pelo mesmo motivo medido de la: a linha vazia marca
    o fim da pagina e nao e descarte; a sonda vem antes de tudo o que custa; as
    colunas de numero custam 13 casamentos por run.

    O QUE ELA NAO TEM E TAO IMPORTANTE QUANTO O QUE ELA TEM
    -------------------------------------------------------
    NAO ha leitura de nome, NAO ha recorte da coluna `Auction List` e NAO ha
    parametro por onde uma funcao de OCR pudesse entrar. A `Auction List` nao se
    le com os moldes deste projeto em piso de brilho nenhum — a varredura esta
    escrita em `quantidade_de_adena` —, e a identidade da serie nao vem de la:
    vem da SENTINELA `CHAVE_DA_SERIE_DA_ADENA`.

    A ADENA E UMA SERIE SO (D-A), e a decisao e do usuario. Derivar a chave do
    nome faria a trava de digitos (D-03) partir a Adena em uma serie por
    quantidade — 5M, 10M e 15M viram tres series e a mediana da taxa nasce
    partida em tres. O argumento inteiro mora ao lado da constante, em
    `mercado_catalogo.py`.

    A DIFERENCA DE STATUS DO CRUZAMENTO E A PARTE QUE IMPORTA (D-C)
    ---------------------------------------------------------------
    Na NEGOCIACAO o cruzamento e OBSERVACAO registrada: a guarda foi REPROVADA
    por medicao (fechamento 0,6525) e `mercado_tolerancia_do_cruzamento` esta
    gravada como `None`, entao `_observar_o_cruzamento` so anuncia no log e a
    linha segue.

    AQUI ele e GUARDA, e derruba a linha. Ele e a UNICA rede entre uma leitura
    errada e uma taxa plausivel no CSV, e o numero que justifica esta medido: na
    linha 5 de `janela_adena_f014.png` a tela diz `135,00`, a leitura devolve
    `13588` (dois `0` lidos como `8`, o par de margem 0,0370), a gramatica passa,
    a sonda diz limpo e o acordo entre dois frames CONCORDA no erro. Sem esta
    guarda aquela linha entra no registro como taxa `135,88`.

    E o criterio nao e escolhido aqui: quem decide e `quantidade_de_adena`, que
    reusa `limite_derivado_do_cruzamento`.

    O INCREMENTO ILEGIVEL DERRUBA A LINHA, E ISSO DIVERGE DE `ler_linha`
    --------------------------------------------------------------------
    La o unitario ilegivel NAO derruba: ele so CALA a guarda, porque `Total` e
    `Quantity` bastam para a observacao. Aqui nao ha `Quantity`: sem incremento
    nao ha quantidade, e sem quantidade nao ha taxa. Falha FECHADA.

    `residuo_do_cruzamento` NA `LinhaLida` E A MESMA GRANDEZA DE LA, so que a
    escala de `n` sao INCREMENTOS de cinco milhoes e nao unidades:
    `|total - incremento x n|` em centesimos. Guardar outra coisa no campo
    homonimo faria a Fase 3 comparar duas grandezas diferentes na mesma coluna.
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
            folga_de_cola=folga_de_cola,
        )
        if total is None:
            return _recusar(
                indice, MOTIVO_DA_GRAMATICA, "a coluna Total Price nao se leu inteira"
            )
        incremento = ler_celula_de_numero(
            recorte_do_incremento,
            moldes,
            piso,
            margem,
            valor_minimo=valor_minimo_do_numero,
            folga_de_cola=folga_de_cola,
        )
        if incremento is None:
            return _recusar(
                indice,
                MOTIVO_DA_GRAMATICA,
                "a coluna 5 mln increment nao se leu inteira",
            )

        derivada = quantidade_de_adena(total, incremento)
        if derivada is None:
            candidato = round(total / incremento) if incremento > 0 else 0
            return _recusar(
                indice,
                MOTIVO_DO_CRUZAMENTO,
                f"total={total} incremento={incremento} n={candidato} "
                f"residuo={residuo_do_cruzamento(total, incremento, candidato)} "
                f"estourou o limite derivado de "
                f"{limite_derivado_do_cruzamento(candidato)} centesimos",
            )
        quantidade, incrementos = derivada

        return LinhaLida(
            indice=indice,
            chave_da_serie=CHAVE_DA_SERIE_DA_ADENA,
            nome_exibido=NOME_EXIBIDO_DA_ADENA,
            total_em_centesimos=total,
            quantidade=quantidade,
            serie_nova=CHAVE_DA_SERIE_DA_ADENA not in catalogo,
            residuo_do_cruzamento=residuo_do_cruzamento(
                total, incremento, incrementos
            ),
        )
    except Exception as erro:  # noqa: BLE001 - roda dentro do tick
        log.debug("leitura da linha %d da adena falhou: %s", indice, erro)
        return _recusar(indice, MOTIVO_DA_GRAMATICA, f"excecao contida: {erro}")


def _observar_o_cruzamento(
    indice: int,
    total: int,
    unitario: int | None,
    quantidade: int,
    residuo: int | None,
    tolerancia: float | None,
    trava: TravaDaObservacao,
) -> None:
    """A rota da guarda REPROVADA: registrar em vez de descartar.

    So fala quando ha o que dizer — quando o residuo estoura o LIMITE DERIVADO,
    que e a unica referencia disponivel enquanto nao ha tolerancia medida que
    preste. Logar toda linha encheria o arquivo rotativo de zeros e afogaria as
    linhas que importam.

    Cala inteiramente com a guarda LIGADA: ali quem fala e o descarte, e dois
    registros para o mesmo evento fariam a contagem do console mentir.

    E FALA UMA VEZ POR DIVERGENCIA, E NAO UMA VEZ POR TICK. A pagina e relida a
    cada segundo, entao sem a `trava` a MESMA observacao saia a 1 Hz enquanto a
    oferta estivesse na tela — medido em producao, ~7.200 linhas por hora. A
    PRIMEIRA continua saindo sempre: o residuo e OBSERVACAO e existe para o
    usuario ver que aquela leitura pode estar torta; suprimi-la apagaria
    informacao, e nao ruido.

    A `trava` CHEGA POR PARAMETRO e sem valor de fabrica, pelo charter deste
    modulo. Ela e do `LeitorDePagina`, que atravessa a sessao; construida aqui
    dentro nasceria vazia a cada linha e nao travaria nada.
    """
    if tolerancia is not None or residuo is None:
        return
    if residuo <= limite_derivado_do_cruzamento(quantidade):
        return
    texto = trava.anunciar(indice, total, unitario, quantidade, residuo)
    if texto is not None:
        log.info("%s", texto)


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
