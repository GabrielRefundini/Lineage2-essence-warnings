"""Calibracao do World Exchange: ancoras, grade e moldes, sobre um frame GRAVADO.

    python -m l2scanner.calibrar_mercado --gravacao recordings/<pasta>
    python -m l2scanner.calibrar_mercado --frame caminho/do/frame.png

POR QUE UM MODULO NOVO, E NAO MAIS CODIGO EM `calibrar.py`
---------------------------------------------------------
Duas razoes, e nenhuma e estetica.

A primeira e um teste: `test_conferencia_gravada.py::
test_existe_um_unico_ponto_de_escrita_no_modulo` conta as ocorrencias de
gravacao de imagem no FONTE de `l2scanner.calibrar` e exige que todas estejam
dentro de `_gravar_conferencia`. Esse tripwire existe porque a gravacao
acontecia em dois pontos, os dois jogavam o retorno fora, e o calibrador
anunciava uma imagem que nao existia — o usuario conferia A IMAGEM VELHA e
validava uma calibracao errada. Aqui a regra e ainda mais simples: este modulo
nao grava imagem NENHUMA por conta propria. Ele importa `_gravar_conferencia`.

A segunda: `calibrar.py` ja tem mais de 900 linhas, e a mecanica que os dois
calibradores compartilham de verdade — arrastar um retangulo sobre uma captura
reescalada — foi EXTRAIDA para `calibrar._selecionar_regiao` em vez de copiada.
Duas copias da mesma mecanica de recorte envelheceriam separadas, e a que
envelhecesse pior produziria retangulos plausiveis na posicao errada.

POR QUE A FONTE E UM FRAME GRAVADO, E NUNCA A TELA AO VIVO (D-06)
-----------------------------------------------------------------
O painel do mercado so existe enquanto o usuario o mantem aberto, e marcar seis
ou oito retangulos com o mouse leva minutos. Sobre um frame gravado ele pode
errar, refazer e conferir quantas vezes quiser — e a mesma gravacao serve para
recalibrar depois de um patch do jogo, sem precisar reproduzir a cena.

O QUE ESTA FERRAMENTA RECUSA A FAZER
------------------------------------
- Imprimir valores para o usuario colar no `calibration.json`. O criterio 3 do
  ROADMAP e literalmente "sem editar JSON a mao": ela CARREGA a calibracao
  existente, muta so os campos de mercado e REGRAVA o arquivo inteiro.
- Gravar uma calibracao pela metade. Sem calibracao anterior ela recusa
  dizendo o que rodar antes, no tom de `calibrar.py --solo`.
- Aprovar uma watchlist com dois itens que se confundem. Um `+3 Bota X` lido
  como `+4 Bota X` nao acrescenta ruido a uma serie de precos: destroi a serie,
  porque o mesmo nome base valeu de 7,02 a 100,00 conforme o encanto no mesmo
  frame.
"""

from __future__ import annotations

# DPI PRIMEIRO, pelo mesmo motivo de `calibrar.py`: a ferramenta e o scanner
# precisam concordar sobre o que e um pixel.
from .dpi import tornar_consciente_de_dpi

_MODO_DPI = tornar_consciente_de_dpi()

import argparse  # noqa: E402
import sys  # noqa: E402
import tomllib  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from pathlib import Path  # noqa: E402

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from .calibracao import Calibracao, CalibracaoInvalida  # noqa: E402
from .calibrar import (  # noqa: E402
    ARQUIVO_CALIBRACAO,
    RAIZ,
    _gravar_conferencia,
    _selecionar_regiao,
)
from .frames import Regiao  # noqa: E402

# A MESMA mascara de brilho ja medida para os nomes de party, e nao uma copia:
# ela carrega no docstring a razao de ser SO brilho (o nome do lider e amarelo e
# qualquer filtro de saturacao o rejeitava). A propriedade que valia para o
# amarelo do lider vale aqui para o dourado do `Adena` e o ciano da linha
# destacada do mercado.
from .identidade import mascara_de_texto  # noqa: E402
from .mercado_visao import (  # noqa: E402
    CASAMENTO_MINIMO_DA_ANCORA,
    AncoraDoPainel,
    ancoras_para_calibracao,
    casamento_da_ancora,
    glifos_de_calibracao,
    glifos_para_calibracao,
    molde_para_hex,
)

ARQUIVO_CONFIG = RAIZ / "config.toml"

# Acima disto, dois moldes da watchlist sao a MESMA COISA para o casamento e
# nenhum limiar os separa.
#
# HONESTIDADE SOBRE ESTE NUMERO: ao contrario de
# `mercado_visao.CASAMENTO_MINIMO_DA_ANCORA`, ele NAO e medido — nao poderia
# ser, porque a watchlist e do usuario e cada uma tem a sua matriz. Ele e uma
# POLITICA: com o pior inter-classe em 0.85, o limiar sugerido pela ferramenta
# fica em 0.925 e sobra uma margem de 0.075 para o casamento correto (que vale
# 1.0 por construcao, ja que o molde e recortado do proprio frame). Acima de
# 0.85 a margem some, e a ferramenta prefere mandar o usuario recortar mais
# largo a entregar uma serie de precos que se corrompe calada.
COLISAO_MAXIMA_ENTRE_TEMPLATES = 0.85

# Os deslocamentos MEDIDOS das ancoras, a partir da origem do painel (o canto
# superior esquerdo da faixa de titulo), na janela de 1720x1392 do usuario.
#
# Sao SUGESTOES, nao verdade -- e o que a ferramenta faz com elas hoje e MENOS
# do que este comentario ja afirmou. A versao anterior dizia "a ferramenta
# mostra cada regiao e o usuario confirma ou ajusta"; ela nao mostra. Os `dx` e
# `dy` sao desempacotados e DESCARTADOS no laco de selecao, nada e pre-desenhado
# sobre o frame, e o `selectROI` abre vazio. A unica coisa que sobrevive das
# medicoes de campo e o tamanho impresso na instrucao ("sugerido: 100x28").
#
# Ficou assim de proposito, e nao por esquecimento: pre-desenhar o retangulo
# sugerido exigiria mexer em `calibrar._selecionar_regiao`, que e COMPARTILHADA
# com a calibracao de party e funciona hoje. Enquanto ninguem paga esse custo, o
# comentario diz o que o codigo faz.
#
# Ver `mercado_visao.AncoraDoPainel` para o que cada ancora e e para as duas que
# foram medidas e descartadas.
ANCORAS_SUGERIDAS = (
    ("titulo", 0, 0, 100, 28, "a faixa de titulo 'XM Market'"),
    ("botao_fechar", 494, -10, 60, 60, "o 'X' de fechar, canto superior direito"),
    ("canto_inf_dir", 494, 665, 60, 60, "a seta de rolagem, canto inferior direito"),
)


class MercadoNaoCalibravel(Exception):
    """A ferramenta nao tem como calibrar, e diz por que."""


# Quantas linhas cada layout tem, MEDIDO em campo (SPIKE-RESPOSTAS.md 1): 10 na
# grade de negociacao (abas Adena, Equipment, Enhancement), com passo de 45 px
# exatos; 9 na tela de busca, porque a caixa de busca come a altura de uma.
#
# Serve para CONFERIR o que saiu do arrasto do mouse, nao para substitui-lo: a
# medicao veio de UMA janela, e uma resolucao diferente muda os pixels. Por isso
# a divergencia e AVISO alto, e nao recusa.
LINHAS_ESPERADAS = {"negociacao": 10, "adena": 10, "busca": 9}


# AS SETAS DO NAVEGADOR DE FRAMES, MEDIDAS -- nao copiadas de um blog.
#
# O codigo anterior tratava 81/82/83/84 como as setas. Esses sao os codigos do
# backend GTK/Linux, e em ASCII eles sao `Q`, `R`, `S`, `T`. Duas consequencias
# nesta unica plataforma suportada pelo projeto:
#
#   * `ord("S") == 83` estava no ramo do "proximo frame" JUNTO com o `d`. Um
#     `S` maiusculo andava para FRENTE em vez de voltar dez, e o `ord("S")` do
#     ultimo ramo era codigo morto, inalcancavel.
#   * As setas nunca chegavam. As quatro linhas de ajuda impressas prometiam
#     teclas mortas.
#
# MEDIDO nesta maquina (cv2 4.14.0, Windows 11), injetando VK_LEFT/RIGHT/UP/
# DOWN por `PostMessageW` na janela do HighGUI:
#
#     seta       cv2.waitKey   cv2.waitKeyEx        (& 0xFF)
#     direita        0           2555904 (0x270000)     0
#     esquerda       0           2424832 (0x250000)     0
#     cima           0           2490368 (0x260000)     0
#     baixo          0           2621440 (0x280000)     0
#
# `waitKey` devolve 0 para todas -- e por isso `& 0xFF` zerava tudo. So o
# `waitKeyEx` entrega o codigo cheio. Como o byte baixo das quatro e 0, elas
# nao colidem com letra nenhuma.
SETA_DIREITA = 2555904
SETA_ESQUERDA = 2424832
SETA_CIMA = 2490368
SETA_BAIXO = 2621440


# --------------------------------------------------------------------------
# Partes PURAS — sao elas que a suite consegue afirmar
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultadoDaConfusao:
    """A matriz de confusao entre os moldes, e o veredito dela."""

    aprovado: bool
    # `None` quando NENHUM par foi comparado. O tipo diz a diferenca entre
    # "medi e deu zero" e "nao medi nada" -- e o `0.0` que estava aqui apagava
    # justamente essa diferenca, imprimindo o valor mais tranquilizador
    # possivel para uma medicao que nao aconteceu.
    pior_score: float | None
    par_colidente: tuple[str, str] | None
    limiar_sugerido: float | None
    matriz: dict[tuple[str, str], float] = field(default_factory=dict)
    # Os pares que NAO PUDERAM ser medidos -- vazio, molde maior que o alvo, ou
    # desvio abaixo de `1e-6`. Eles ficam FORA da `matriz`, porque uma
    # comparacao que nao aconteceu nao e uma comparacao sem colisao, e contar
    # zero para ela seria o resultado mais tranquilizador possivel para a pior
    # situacao possivel. Campo com padrao vazio, entao a rota dos NOMES
    # (`matriz_de_confusao`) segue construindo o dataclass exatamente como
    # antes; quem o preenche e `matriz_de_confusao_de_glifos`.
    pares_incalculaveis: tuple[tuple[str, str], ...] = ()

    @property
    def rodou(self) -> bool:
        """Houve pelo menos UM par comparado.

        Com zero ou um molde a matriz nao tem par nenhum. Aprovar e correto --
        nao ha o que confundir --, mas AFIRMAR um pior score e um limiar
        derivado dele nao e: sao numeros inventados com cara de medidos, e o
        limiar vai para o `calibration.json`, onde a Fase 2 o le como verdade.
        """
        return bool(self.matriz)

    def explicar(self) -> str:
        if not self.rodou:
            return (
                "Matriz de confusao NAO RODOU: 0 pares para comparar. Com "
                "menos de dois moldes de nome nao ha o que confundir -- nenhum "
                "score foi medido e NENHUM limiar de template foi derivado. "
                "O limiar que ja estiver no calibration.json fica como esta."
            )
        if self.aprovado:
            return (
                f"Matriz de confusao APROVADA: o pior score entre dois itens "
                f"diferentes e {self.pior_score:.4f}. Limiar sugerido: "
                f"{self.limiar_sugerido:.4f}."
            )
        a, b = self.par_colidente or ("?", "?")
        return (
            f"Matriz de confusao RECUSADA: '{a}' e '{b}' casam "
            f"{self.pior_score:.4f} um com o outro — acima de "
            f"{COLISAO_MAXIMA_ENTRE_TEMPLATES}, nenhum limiar os separa.\n"
            f"  Conserto 1: recorte os dois mais LARGOS, ate incluir o pedaco "
            f"que os diferencia (o prefixo '+N ' e o fim do nome).\n"
            f"  Conserto 2: tire um dos dois da watchlist do config.toml.\n"
            f"Ler um pelo outro nao acrescenta ruido a serie de precos: "
            f"destroi a serie."
        )


def _alinhar(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Corta os dois ao menor tamanho comum, ancorado no canto superior esquerdo.

    O nome e desenhado alinhado a ESQUERDA dentro da coluna `Goods`, entao o
    canto superior esquerdo e o unico alinhamento com significado.

    Cortar torna a matriz MAIS conservadora, e isso e de proposito: comparar so
    o prefixo comum de `+3 Bota X` e `+4 Bota Xtra` sobe o score dos dois e
    aumenta a chance de recusa. Uma matriz que erra tem de errar para o lado de
    recusar.
    """
    altura = min(a.shape[0], b.shape[0])
    largura = min(a.shape[1], b.shape[1])
    return a[:altura, :largura], b[:altura, :largura]


def matriz_de_confusao(moldes: dict[str, np.ndarray]) -> ResultadoDaConfusao:
    """Todo molde contra todo molde, com a correlacao de posicao UNICA.

    A mesma tecnica de conjunto fechado ja MEDIDA em `identidade._correlacionar`
    (1.000 nos acertos contra 0.454 no melhor erro): comparar em UMA posicao, e
    nao tomar o maximo sobre deslocamentos, porque cada deslocamento e uma
    chance independente de um alvo errado achar alinhamento sortudo.

    Com menos de dois moldes nao ha o que confundir — aprova, mas NAO devolve
    pior score nem limiar: nao houve par nenhum para comparar, e `(1.0+0.0)/2`
    saia daqui como 0.5 direto para o `calibration.json`, apresentado como
    derivado da matriz. Um limiar de 0.5 para casamento de nome casa quase
    tudo — o pior inter-classe que este modulo TOLERA e 0.85. Numero fabricado
    com aparencia de medido, na ferramenta que grava a calibracao.
    """
    nomes = list(moldes)
    if len(nomes) < 2:
        return ResultadoDaConfusao(
            aprovado=True,
            pior_score=None,
            par_colidente=None,
            limiar_sugerido=None,
        )

    matriz: dict[tuple[str, str], float] = {}
    pior = -1.0
    par: tuple[str, str] | None = None
    for i, primeiro in enumerate(nomes):
        for segundo in nomes[i + 1 :]:
            a, b = _alinhar(moldes[primeiro], moldes[segundo])
            score = casamento_da_ancora(a, b)
            matriz[(primeiro, segundo)] = score
            if score > pior:
                pior, par = score, (primeiro, segundo)

    aprovado = pior <= COLISAO_MAXIMA_ENTRE_TEMPLATES
    return ResultadoDaConfusao(
        aprovado=aprovado,
        pior_score=pior,
        par_colidente=par,
        limiar_sugerido=(1.0 + pior) / 2 if aprovado else None,
        matriz=matriz,
    )



# --------------------------------------------------------------------------
# O corte de GLIFOS: segmentacao, matriz propria, e o alinhamento certo
# --------------------------------------------------------------------------

# Acima disto, dois glifos sao a MESMA COISA para o casamento e nenhum limiar os
# separa. Um `0` lido como `8` num preco nao acrescenta ruido a serie: corrompe
# a serie inteira, calado.
#
# 1. O PIOR PAR MEDIDO, E A CONVENCAO QUE O PRODUZIU. Sobre os 11 glifos reais
#    recortados das duas fixtures NA CONVENCAO LINHA-JUSTA COMPARTILHADA (uma
#    faixa de linhas por retangulo marcado, cada glifo com os seus proprios
#    limites de coluna dentro dela):
#
#        representacao              pior par inter-classe    margem ate 1.0
#        tons de cinza nativo       0.8434                       0.1566
#        MASCARA BINARIA (V>180)    0.7171                       0.2829
#
#    Sem a convencao ao lado o numero nao significa nada -- ele MUDA com o
#    recorte, e foi assim que a primeira versao do plano 01-05 errou.
#
# 2. POR QUE A MASCARA, E NAO O CINZA. O par nomeado e o valor absoluto mudam
#    com a convencao; a ORDEM nao muda em nenhuma das tres medidas:
#
#        convencao de recorte                  cinza     mascara   diferenca
#        banda completa de 45 px               0.9020    0.7858      0.1162
#        linha-justa POR GLIFO (virgula 3px)   0.8003    0.6953      0.1050
#        LINHA-JUSTA COMPARTILHADA (esta)      0.8434    0.7171      0.1263
#
#    A mascara vence em todas, por 0.10 a 0.13. E a escolha da representacao que
#    e forcada pela evidencia; o numero absoluto nao e.
#
# 3. POR QUE ELA E SEPARADA DE `COLISAO_MAXIMA_ENTRE_TEMPLATES`, mesmo comecando
#    com o mesmo valor. Nao e porque uma medicao proibisse -- nao proibe. E
#    porque os dois conjuntos fechados divergem por construcao e vao divergir de
#    novo: a watchlist e do USUARIO e muda a cada edicao do `config.toml`, com
#    uma matriz por watchlist; o conjunto de glifos e fixo pela FONTE DO JOGO e
#    so muda quando o jogo muda. Aliasar as duas faria o afrouxamento de um
#    viajar para o outro na primeira vez que alguem folgasse um deles.
#
# 0.85 fica 0.13 acima do pior par medido (folga para outra resolucao ou skin) e
# 0.15 abaixo do casamento perfeito.
#
# O ALINHAMENTO E POR PREENCHIMENTO, E ISSO TAMBEM E MEDIDO. Cortar ao menor
# tamanho comum -- o que `_alinhar` faz para os NOMES, corretamente, porque nome
# e texto alinhado a esquerda -- reduz aqui todo par que envolva a virgula a UMA
# coluna, e comparar um digito de 4 px pela sua primeira coluna nao e comparar o
# digito. Medido nesta convencao: `,` x `2` vale 0.1918 com preenchimento e
# 0.5000 com corte. O erro anda na direcao de similaridade FABRICADA, justamente
# sobre o glifo cuja confusao e mais cara. Sob a convencao de linha-justa por
# glifo o corte fica pior ainda: a revisao mediu `,` x `9` em 0.9986 em cinza
# (uma quase-colisao inventada) e 10 pares em 0.0 duro na mascara, com o guard de
# desvio disparando sobre comparacoes que nao aconteceram.
COLISAO_MAXIMA_ENTRE_GLIFOS = 0.85


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
    """
    if recorte.size == 0:
        return None, []

    mascara = mascara_de_texto(recorte)
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


def matriz_de_confusao_de_glifos(
    moldes: dict[str, np.ndarray],
) -> ResultadoDaConfusao:
    """Todo glifo contra todo glifo, na MASCARA e com alinhamento por preenchimento.

    Nasce AO LADO de `matriz_de_confusao`, e nao por dentro: aquela e a rota dos
    moldes de NOME, testada e corrigida em CR-03/CR-04, e as tres diferencas
    daqui sao todas obrigatorias.

    1. Os moldes chegam ja na representacao escolhida por medicao (a mascara
       binaria, ver `COLISAO_MAXIMA_ENTRE_GLIFOS`).
    2. O alinhamento PREENCHE ate a maior caixa em vez de cortar ao menor --
       cortar compara a virgula de 1 px contra a primeira coluna do digito.
    3. Um par realmente incalculavel NAO entra na matriz como medicao. Ele e
       contado a parte, em `pares_incalculaveis`, e faz o veredito RECUSAR:
       aprovar por omissao daria o resultado mais tranquilizador possivel para a
       situacao em que menos se sabe.

    A incalculabilidade e decidida por `_par_incalculavel` -- pelas
    pre-condicoes re-checadas no par ja alinhado, NUNCA comparando o score
    devolvido a `0.0`. Leia o docstring dela antes de mexer nisto: o conjunto
    correto de glifos contem quatro zeros legitimos, e testar o score os
    classificaria como nao-mensuraveis e recusaria a melhor separacao que o
    conjunto tem.

    Com menos de dois moldes aprova, mas NAO afirma pior score nem deriva
    limiar: e a licao do CR-03, e o limiar iria para o `calibration.json` onde a
    Fase 2 o le como verdade.
    """
    # ORDENADOS, e nao na ordem de corte -- outra diferenca deliberada em
    # relacao a `matriz_de_confusao`. La a ordem e a da watchlist, que e do
    # usuario e tem significado para ele. Aqui a ordem de insercao seria a ordem
    # em que o usuario marcou os numeros, que nao significa nada e muda a cada
    # rodada: com ela, a MESMA calibracao imprimiria a matriz em ordem
    # diferente, e a chave de um par sairia ora `(',','0')` ora `('0',',')`.
    # Ordenar deixa a saida comparavel entre rodadas e da a cada par uma chave
    # unica -- o que importa quando alguem for conferir um par nomeado num
    # relatorio contra o que a ferramenta imprimiu.
    rotulos = sorted(moldes)
    if len(rotulos) < 2:
        return ResultadoDaConfusao(
            aprovado=True,
            pior_score=None,
            par_colidente=None,
            limiar_sugerido=None,
        )

    matriz: dict[tuple[str, str], float] = {}
    incalculaveis: list[tuple[str, str]] = []
    pior = -1.0
    par: tuple[str, str] | None = None
    for indice, primeiro in enumerate(rotulos):
        for segundo in rotulos[indice + 1 :]:
            a, b = _alinhar_por_preenchimento(moldes[primeiro], moldes[segundo])
            if _par_incalculavel(a, b):
                incalculaveis.append((primeiro, segundo))
                continue
            score = casamento_da_ancora(a, b)
            matriz[(primeiro, segundo)] = score
            if score > pior:
                pior, par = score, (primeiro, segundo)

    if not matriz:
        # Nenhum par mediu. Nao ha score a afirmar nem limiar a derivar -- e se
        # houve par incalculavel, tambem nao ha o que aprovar.
        return ResultadoDaConfusao(
            aprovado=not incalculaveis,
            pior_score=None,
            par_colidente=None,
            limiar_sugerido=None,
            pares_incalculaveis=tuple(incalculaveis),
        )

    aprovado = pior <= COLISAO_MAXIMA_ENTRE_GLIFOS and not incalculaveis
    return ResultadoDaConfusao(
        aprovado=aprovado,
        pior_score=pior,
        par_colidente=par,
        limiar_sugerido=(1.0 + pior) / 2 if aprovado else None,
        matriz=matriz,
        pares_incalculaveis=tuple(incalculaveis),
    )


def explicar_glifos(resultado: ResultadoDaConfusao) -> str:
    """O veredito da matriz DOS GLIFOS, no vocabulario dos glifos.

    `ResultadoDaConfusao.explicar` fala de watchlist e do `config.toml`, e manda
    o usuario recortar mais largo ou tirar um item da lista -- conselhos certos
    para moldes de NOME e inuteis para um digito, que o usuario nao escolheu e
    nao pode tirar de lugar nenhum. O dataclass e compartilhado; a prosa nao.
    """
    if resultado.pares_incalculaveis:
        pares = ", ".join(f"'{a}' x '{b}'" for a, b in resultado.pares_incalculaveis)
        return (
            f"Matriz de glifos RECUSADA: {len(resultado.pares_incalculaveis)} "
            f"par(es) NAO PUDERAM ser medidos -- {pares}.\n"
            f"  Um molde vazio, chapado ou de tamanho incompativel nao se "
            f"compara com nada, e um par que nao foi medido NAO e um par sem "
            f"colisao.\n"
            f"  Conserto: remarque esses glifos, com o retangulo pegando o "
            f"desenho inteiro e nada alem dele."
        )
    if not resultado.rodou:
        return (
            "Matriz de glifos NAO RODOU: 0 pares para comparar. Com menos de "
            "dois glifos nao ha o que confundir -- nenhum score foi medido e "
            "NENHUM limiar de glifo foi derivado. O limiar que ja estiver no "
            "calibration.json fica como esta."
        )
    if resultado.aprovado:
        return (
            f"Matriz de glifos APROVADA: o pior score entre dois glifos "
            f"diferentes e {resultado.pior_score:.4f} (medido no frame de "
            f"referencia: 0.7171 na mascara, 0.8434 em cinza, na convencao "
            f"linha-justa compartilhada). Limiar sugerido: "
            f"{resultado.limiar_sugerido:.4f}."
        )
    a, b = resultado.par_colidente or ("?", "?")
    return (
        f"Matriz de glifos RECUSADA: '{a}' e '{b}' casam "
        f"{resultado.pior_score:.4f} um com o outro — acima de "
        f"{COLISAO_MAXIMA_ENTRE_GLIFOS}, nenhum limiar os separa.\n"
        f"  Conserto: remarque os dois numeros que contem esses glifos, com "
        f"mais folga vertical, para a faixa de linhas pegar o desenho inteiro.\n"
        f"Ler um digito pelo outro nao acrescenta ruido ao preco: troca o preco."
    )



def derivar_grade(
    caixa_da_grade: tuple[int, int, int, int],
    caixa_da_primeira_linha: tuple[int, int, int, int],
    layout: str,
    origem_do_painel: tuple[int, int],
) -> dict:
    """Da area da lista e da PRIMEIRA linha sai a grade inteira.

    Marcar dez linhas com o mouse acumularia dez erros humanos; marcar uma e
    derivar o resto acumula um. Os numeros de campo (`SPIKE-RESPOSTAS.md` 1):
    10 linhas na grade de negociacao, passo de 45 px exatos; 9 na tela de busca,
    porque a caixa de busca come a altura de uma.

    `layout` e gravado junto porque NAO EXISTE "a grade": sao tres conjuntos de
    coluna diferentes, e ler a coluna errada com confianca corrompe a serie por
    um fator inteiro.

    A GRADE E GUARDADA EM DESLOCAMENTO, PELA MESMA RAZAO DAS ANCORAS. A primeira
    versao gravava `origem_x`/`origem_y` absolutos, direto do `selectROI`, e isso
    era um defeito silencioso: o painel ANDA 827x831 px (medido em
    `SPIKE-RESPOSTAS.md` 8). Uma calibracao feita com o painel num canto
    apontaria para o vazio assim que o usuario arrastasse — e como o leitor so
    nasce na Fase 2, ninguem descobriria ate a leitura sair errada com
    confianca.

    Encontrado quando o usuario comparou a propria tela ao vivo com o frame
    gravado e viu o painel em outro lugar. As ancoras ja guardavam
    deslocamento; a grade tinha recebido so a metade certa do tratamento.
    """
    gx, gy, glarg, galt = caixa_da_grade
    ox, oy = origem_do_painel
    _, _, _, altura_da_linha = caixa_da_primeira_linha
    if altura_da_linha <= 0:
        raise MercadoNaoCalibravel(
            "a primeira linha ficou com altura zero — remarque o retangulo"
        )
    # UMA GRADE DEGENERADA E UM RETANGULO MARCADO ERRADO, NAO UMA GRADE DE 1.
    #
    # O `max(1, ...)` transformava "a area da lista e MENOR que uma linha" --
    # que so acontece se os dois retangulos estiverem trocados ou se um deles
    # sair minusculo -- em `linhas_por_pagina: 1`, gravado com a mesma
    # confianca de um valor correto. Confirmado: grade de 20 px com linha de
    # 45 px devolvia 1.
    if altura_da_linha > galt:
        raise MercadoNaoCalibravel(
            f"a primeira linha ({altura_da_linha} px) e mais alta que a area "
            f"da lista ({galt} px) — os dois retangulos parecem trocados. "
            f"Remarque: primeiro a LISTA INTEIRA, depois SO a primeira linha."
        )
    linhas = galt // altura_da_linha

    # E A DIVERGENCIA DO NUMERO MEDIDO SAI ALTA, mesmo quando nao e recusa.
    #
    # A docstring desta funcao JA sabe a resposta certa (SPIKE-RESPOSTAS 1: 10
    # linhas na grade de negociacao, passo de 45 px exatos; 9 na busca), mas
    # `layout` so era gravado, nunca usado para conferir. Errar a altura da
    # primeira linha em 5 px sobre 450 px de grade ja troca 10 por 9 --
    # silenciosamente, e a Fase 2 leria uma linha a menos por pagina para
    # sempre. Nao e recusa porque a medicao veio de UMA janela; e aviso porque
    # divergir do campo e a hipotese mais provavel de erro de marcacao.
    esperado = LINHAS_ESPERADAS.get(layout)
    if esperado is not None and linhas != esperado:
        print(
            f"\nATENCAO: sairam {linhas} linhas por pagina, e o layout "
            f"'{layout}' foi MEDIDO em campo com {esperado} (passo de 45 px).\n"
            f"  Confira a imagem de conferencia antes de confiar nesta grade."
        )
    return {
        "layout": layout,
        "dx": int(gx - ox),
        "dy": int(gy - oy),
        "largura": int(glarg),
        "altura": int(galt),
        "altura_da_linha": int(altura_da_linha),
        "linhas_por_pagina": int(linhas),
    }


def conferir_o_frame(cal: Calibracao, pixels: np.ndarray) -> None:
    """O frame e mesmo uma JANELA COMPLETA desta calibracao?

    RECUSA ALTO em vez de medir a regiao errada calada — a mesma disciplina de
    `Calibracao.conferir_geometria`.

    O erro que isto pega e concreto e ja aconteceu no spike: gravar no modo
    party (recorte de ~174x522) em vez do modo janela. Marcar o painel do
    mercado dentro de um recorte de party window e impossivel, mas uma
    ferramenta descuidada aceitaria o arquivo e gravaria retangulos que nao
    apontam para nada.
    """
    if pixels is None or pixels.size == 0:
        raise MercadoNaoCalibravel("o frame nao pode ser lido (arquivo vazio?)")

    altura, largura = pixels.shape[:2]
    # So o TAMANHO da party window entra aqui, nunca a posicao dela: sem
    # `party_window_na_janela` a posicao esta em coordenadas de DESKTOP e nao
    # limita nada dentro da janela. O tamanho, sim, e a assinatura exata do
    # erro que isto pega — um frame gravado no modo party tem as dimensoes da
    # party window, e nao as da janela.
    referencia = cal.party_window_na_janela or cal.party_window
    if largura <= referencia.largura or altura <= referencia.altura:
        raise MercadoNaoCalibravel(
            f"este frame tem {largura}x{altura} — nao e maior que a party "
            f"window calibrada ({referencia.largura}x{referencia.altura}).\n"
            f"  Provavelmente ele foi gravado no modo party. Regrave com "
            f"--record-janela e use uma pasta de gravacao de JANELA COMPLETA."
        )


def carregar_calibracao(caminho: Path) -> Calibracao:
    """Carrega a calibracao que ja existe, ou explica o que rodar antes.

    Tom e forma copiados de `calibrar.py:643-652` (o modo solo), porque o
    problema e o mesmo: esta ferramenta AJUSTA uma calibracao existente. Ela nao
    sabe onde fica a party window, nem os limiares de cor, que dependem do Gamma
    da tela do usuario e sao desconheciveis a priori.
    """
    if not caminho.exists():
        raise MercadoNaoCalibravel(
            "Nao existe calibracao anterior neste projeto.\n"
            "  A calibracao de mercado ACRESCENTA campos a uma calibracao que\n"
            "  ja existe — ela nao sabe onde fica a sua party window nem os\n"
            "  limiares de cor da sua tela.\n\n"
            "  Rode o calibrar.bat UMA vez, com party na tela.\n"
            "  Depois disso o calibrar-mercado.bat resolve o resto."
        )
    try:
        return Calibracao.carregar(caminho)
    except CalibracaoInvalida as erro:
        raise MercadoNaoCalibravel(str(erro)) from erro


def _a_janela_sumiu(janela: str) -> bool:
    """O usuario fechou a janela no X?

    `WND_PROP_VISIBLE` cai abaixo de 1 quando a janela deixa de existir. Um
    `cv2.error` aqui significa a mesma coisa por outro caminho -- a janela nao
    responde mais --, entao os dois viram o mesmo `True`: um navegador sem
    janela nao tem como receber tecla nenhuma.
    """
    try:
        return cv2.getWindowProperty(janela, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:  # pragma: no cover - depende do backend
        return True


def navegar_e_escolher(quadros: list[Path], comeco: int) -> Path:
    """Deixa o usuario FOLHEAR a gravacao e escolher um frame limpo.

    MEDIDO EM CAMPO, 2026-08-28: o usuario rodou a ferramenta e caiu num frame
    "sujo com outras coisas sobrepondo o mercado". O padrao anterior era o frame
    do MEIO da pasta -- uma escolha arbitraria que nao tem como saber se ali
    havia uma tooltip, a marcacao de alvo ou a lista em transicao por cima do
    painel.

    Calibrar sobre um frame ocluido nasce torto de um jeito silencioso: os
    retangulos ficam gravados no `calibration.json` medindo a coisa errada, e o
    erro so aparece muito depois, como leitura ruim. E a mesma familia do
    incidente 27x -- oclusao parcial produzindo saida confiante e errada.

    A escolha e do OLHO do usuario de proposito. Nao da para pontuar oclusao
    aqui sem ja ter as ancoras, e as ancoras sao justamente o que esta sendo
    calibrado. Com a pessoa na frente da tela, folhear resolve sem precisar
    inventar heuristica.
    """
    indice = max(0, min(comeco, len(quadros) - 1))
    janela = "escolha um frame LIMPO  (D/A ou setas: navegar | ENTER: usar | ESC: cancelar)"

    print(chr(10) + "-" * 60)
    print("  ESCOLHA O FRAME")
    print("  Procure um em que o painel do mercado esteja INTEIRO e")
    print("  SEM NADA POR CIMA: sem tooltip, sem marcacao de alvo, sem")
    print("  a lista no meio de uma rolagem.")
    print("")
    print("    D  ou seta direita  -> proximo frame")
    print("    A  ou seta esquerda -> frame anterior")
    print("    W / S               -> pular de 10 em 10")
    print("    ENTER               -> usar este frame")
    print("    ESC                 -> cancelar sem gravar nada")
    print("")
    print("  NAO feche a janela no X -- use ESC para cancelar.")
    print("-" * 60)

    # WINDOW_AUTOSIZE, nao WINDOW_NORMAL: esta janela existe para o usuario
    # VER se ha tooltip, marcacao de alvo ou rolagem por cima do painel, e uma
    # janela NORMAL nao se dimensiona pela imagem -- ela nasce no tamanho que o
    # Win32 resolver dar e espreme o frame dentro dele. MEDIDO nesta maquina
    # (cv2 4.14.0): imagem 1720x1392 numa janela NORMAL saiu 120x1440; em
    # AUTOSIZE sai 1720x1392 exatos. A 8% do tamanho ninguem enxerga tooltip
    # nenhuma, e o proposito inteiro da funcao vai junto. `moveWindow`
    # posiciona igual sobre AUTOSIZE, entao a janela continua nascendo onde o
    # usuario a encontra. `_reduzir_para_caber` ja garante que ela cabe.
    cv2.namedWindow(janela, cv2.WINDOW_AUTOSIZE)
    cv2.moveWindow(janela, 40, 40)
    try:
        desenhado: int | None = None
        while True:
            # So redecodifica o PNG quando o indice mudou. O laco agora gira a
            # cada 50 ms (ver a sondagem de janela fechada abaixo) e reler um
            # frame de 1720x1392 vinte vezes por segundo seria desperdicio puro.
            if desenhado != indice:
                pixels = cv2.imread(str(quadros[indice]))
                if pixels is None:
                    raise MercadoNaoCalibravel(
                        f"nao consegui decodificar {quadros[indice]}"
                    )
                mostra = _reduzir_para_caber(pixels)
                etiqueta = f"{indice + 1}/{len(quadros)}  {quadros[indice].name}"
                cv2.putText(
                    mostra, etiqueta, (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA,
                )
                cv2.putText(
                    mostra, etiqueta, (12, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1, cv2.LINE_AA,
                )
                cv2.imshow(janela, mostra)
                desenhado = indice

            # LER O CODIGO CHEIO ANTES DE MASCARAR. `waitKey` devolve 0 para
            # as setas no Windows e `& 0xFF` apagava isso -- ver a medicao em
            # SETA_DIREITA. `waitKeyEx` entrega os quatro codigos completos.
            #
            # E COM PRAZO, nao `0`. `waitKeyEx(0)` bloqueia INDEFINIDAMENTE: se
            # o usuario fechasse a janela no X -- coisa que o texto acima nao
            # proibia, ao contrario do bloco de selecao, que avisa "NAO feche no
            # X" -- nao havia mais janela para receber tecla e a chamada nunca
            # retornava. O console ficava parado na tela de instrucoes, sem
            # janela e sem mensagem, e a unica saida era Ctrl-C.
            bruto = cv2.waitKeyEx(50)
            if _a_janela_sumiu(janela):
                raise MercadoNaoCalibravel(
                    "a janela do navegador foi fechada -- nada foi gravado.\n"
                    "  Use ESC para cancelar ou ENTER para escolher o frame."
                )
            if bruto == -1:
                continue
            tecla = bruto & 0xFF
            if tecla in (13, 10):  # ENTER
                cv2.destroyWindow(janela)
                for _ in range(5):
                    cv2.waitKey(1)  # deixa o HighGUI assentar
                print(f"  usando {quadros[indice].name}" + chr(10))
                return quadros[indice]
            if tecla == 27:  # ESC
                cv2.destroyWindow(janela)
                raise MercadoNaoCalibravel(
                    "escolha de frame cancelada -- nada foi gravado"
                )
            if tecla in (ord("d"), ord("D")) or bruto == SETA_DIREITA:
                indice = min(indice + 1, len(quadros) - 1)
            elif tecla in (ord("a"), ord("A")) or bruto == SETA_ESQUERDA:
                indice = max(indice - 1, 0)
            elif tecla in (ord("w"), ord("W")) or bruto == SETA_CIMA:
                indice = min(indice + 10, len(quadros) - 1)
            elif tecla in (ord("s"), ord("S")) or bruto == SETA_BAIXO:
                indice = max(indice - 10, 0)
    finally:
        try:
            cv2.destroyWindow(janela)
        except cv2.error:
            pass


def _reduzir_para_caber(pixels: np.ndarray, largura_alvo: int = 1400) -> np.ndarray:
    """Encolhe so para o frame de janela completa caber num monitor."""
    altura, largura = pixels.shape[:2]
    if largura <= largura_alvo:
        return pixels.copy()
    escala = largura_alvo / largura
    return cv2.resize(
        pixels, (largura_alvo, int(altura * escala)), interpolation=cv2.INTER_AREA
    )


def escolher_frame(gravacao: Path | None, frame: Path | None, indice: int | None) -> Path:
    """Qual PNG vai ser calibrado.

    O padrao de `--gravacao` e o frame do MEIO, e nao o primeiro: as gravacoes
    do roteiro comecam com o usuario ainda posicionando a tela, entao o primeiro
    frame e o que tem menos chance de mostrar a cena pedida.
    """
    if frame is not None:
        if not frame.is_file():
            raise MercadoNaoCalibravel(f"nao encontrei o frame {frame}")
        return frame

    if gravacao is None:
        raise MercadoNaoCalibravel(
            "diga de onde ler: --gravacao <pasta> ou --frame <arquivo.png>"
        )
    if not gravacao.is_dir():
        raise MercadoNaoCalibravel(f"nao encontrei a pasta {gravacao}")

    quadros = sorted(gravacao.glob("frame_*.png"))
    if not quadros:
        raise MercadoNaoCalibravel(
            f"{gravacao} nao tem nenhum frame_*.png.\n"
            f"  Essa pasta e mesmo uma gravacao do --record-janela?"
        )
    escolhido = len(quadros) // 2 if indice is None else indice
    if not 0 <= escolhido < len(quadros):
        raise MercadoNaoCalibravel(
            f"--indice {escolhido} fora da faixa: a pasta tem "
            f"{len(quadros)} frames (0 a {len(quadros) - 1})"
        )
    # Um `--indice` explicito e uma escolha ja feita: respeita e nao folheia.
    if indice is not None:
        return quadros[escolhido]
    return navegar_e_escolher(quadros, escolhido)


def ler_watchlist(caminho: Path) -> list[str]:
    """Os itens que o usuario quer acompanhar, do `config.toml`.

    Lista vazia e um estado LEGITIMO, e nao um erro: da para calibrar as
    ancoras e a grade sem watchlist nenhuma, e a Fase 2 e que vai precisar dos
    moldes de nome. A ferramenta diz alto o que deixou de cortar.
    """
    if not caminho.exists():
        return []

    # AS TRES RECUSAS ABAIXO SAO EXPLICADAS, E NAO TRACEBACK.
    #
    # Esta funcao roda DEPOIS das ancoras e da grade -- cinco arrastos de mouse
    # ja gastos. Um `config.toml` com erro de sintaxe levantava
    # `TOMLDecodeError`, que `main` nao captura (ele so pega
    # `MercadoNaoCalibravel`), e o usuario perdia tudo para um traceback.
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError as erro:
        raise MercadoNaoCalibravel(
            f"nao consegui ler {caminho.name}: {erro}"
        ) from erro
    try:
        dados = tomllib.loads(texto)
    except tomllib.TOMLDecodeError as erro:
        raise MercadoNaoCalibravel(
            f"{caminho.name} nao e um TOML valido: {erro}\n"
            f"  Conserte o arquivo e rode de novo."
        ) from erro

    itens = dados.get("mercado", {}).get("watchlist", [])
    # `watchlist = "Bota"` (string em vez de lista) ITERAVA OS CARACTERES: a
    # ferramenta pedia quatro recortes -- `B`, `o`, `t`, `a` -- e montava uma
    # matriz de confusao sobre eles. Silenciosamente absurdo.
    if not isinstance(itens, list):
        raise MercadoNaoCalibravel(
            f"[mercado] watchlist precisa ser uma LISTA, veio "
            f"{type(itens).__name__}.\n"
            f'  Exemplo: watchlist = ["+3 Bota X", "Chapeu Y"]'
        )
    return [str(item) for item in itens if str(item).strip()]


def desenhar_conferencia(
    pixels: np.ndarray, regioes: dict[str, tuple[int, int, int, int]]
) -> np.ndarray:
    """Desenha os retangulos por cima da captura, para o humano OLHAR.

    Numero conferindo com numero nao prova que a regiao esta no lugar certo.
    Ver a imagem prova. Mesmo argumento de `calibrar.conferir_visualmente`.
    """
    tela = pixels.copy()
    for nome, (x, y, largura, altura) in regioes.items():
        cv2.rectangle(tela, (x, y), (x + largura, y + altura), (0, 255, 0), 2)
        cv2.putText(
            tela, nome, (x, max(12, y - 6)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA,
        )
    return tela


def montar_ancoras(
    pixels: np.ndarray, caixas: dict[str, tuple[int, int, int, int]], origem: tuple[int, int]
) -> list[AncoraDoPainel]:
    """Recorta cada ancora do frame e converte a posicao em DESLOCAMENTO.

    Guardar deslocamento, e nao posicao absoluta, e o que permite mover todas as
    ancoras juntas quando o painel anda — e ele anda 827x831 px, medidos.
    """
    ox, oy = origem
    cinza = cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY)
    ancoras = []
    for nome, (x, y, largura, altura) in caixas.items():
        recorte = cinza[y : y + altura, x : x + largura]
        if recorte.size == 0:
            raise MercadoNaoCalibravel(
                f"a ancora '{nome}' ficou vazia — remarque o retangulo"
            )
        ancoras.append(
            AncoraDoPainel(nome=nome, dx=x - ox, dy=y - oy, molde=recorte.copy())
        )
    return ancoras


# --------------------------------------------------------------------------
# O fluxo interativo
# --------------------------------------------------------------------------


def _marcar(
    pixels: np.ndarray, titulo: str, instrucao: str
) -> tuple[int, int, int, int]:
    caixa = _selecionar_regiao(pixels, titulo, instrucao)
    if caixa is None:
        raise MercadoNaoCalibravel("selecao cancelada — nada foi gravado")
    return caixa


def _texto_final_da_conferencia(caminho: Path | None, arquivo: Path) -> None:
    """Fecha a calibracao de mercado dizendo a VERDADE sobre a conferencia.

    O defeito que isto conserta e o FUND-01 verbatim, do outro lado da parede.
    A linha final era `print("\nABRA a imagem de conferencia...")`, incondicional,
    com o retorno de `_gravar_conferencia` descartado. Mas aquela funcao devolve
    tres coisas diferentes:

    - o caminho padrao, quando gravou onde sempre grava;
    - um caminho ALTERNATIVO (`calibracao-conferencia-HHMMSS.png`), quando o
      arquivo de sempre estava travado -- o caso mais comum, porque a propria
      ferramenta manda o usuario abrir a imagem no visualizador de fotos e ele
      costuma deixar a imagem aberta;
    - `None`, quando nao gravou em lugar nenhum.

    Nos dois ultimos casos o usuario era mandado para
    `calibracao-conferencia.png`, que ou nao existe, ou E A IMAGEM DA CALIBRACAO
    ANTERIOR. Conferir a imagem velha e validar a calibracao nova: exatamente o
    desfecho que o docstring de abertura deste modulo diz ter matado.

    A honestidade extra que este caso exige, e que o modo solo nao exige: o
    `cal.salvar` JA RODOU quando chegamos aqui. Nao da para dizer so "a
    conferencia nao aconteceu" -- os retangulos estao gravados e ninguem os
    olhou, e o texto tem de dizer as duas coisas na mesma tela.

    Vive fora do `calibrar()` para poder ser testada sem mouse, no mesmo molde
    de `calibrar._texto_final_do_solo`.
    """
    if caminho is not None:
        print(f"\nABRA {caminho}")
        print("e confira se os retangulos verdes caem onde voce espera: a faixa")
        print("de titulo do painel, o X de fechar, a seta de rolagem, a area da")
        print("lista e a primeira linha.")
        return

    print("\nA CONFERENCIA VISUAL NAO ACONTECEU: nenhuma imagem foi gravada.")
    print(f"Os retangulos acima JA ESTAO em {arquivo.name} e NINGUEM os olhou.")
    # Nenhum nome de arquivo sai daqui, de proposito: e a mesma regra de
    # `calibrar._gravar_conferencia`. Um nome citado numa tela onde nao houve
    # gravacao e mais uma promessa vazia -- e pior, o arquivo de sempre
    # PROVAVELMENTE existe, de uma rodada anterior, entao o usuario o abriria.
    print("Se houver alguma imagem de conferencia na pasta, ela e de OUTRA")
    print("rodada e nao serve para conferir esta.")
    print("Feche o visualizador de fotos e rode de novo antes de confiar nisto.")



# O conjunto fechado que a Fase 2 (LEIT-02) precisa para ler um preco.
#
# Nao e invencao deste plano: e literalmente o conteudo declarado pela docstring
# de `Calibracao.mercado_templates_de_digito`, e a resposta VALIDADA da secao 2
# do `SPIKE-RESPOSTAS.md`.
#
# AS DUAS PALAVRAS NAO SAO DECORACAO. A virgula e separador de MILHAR e de
# DECIMAL na mesma linha -- `5,000,000 Adena` ao lado de `62,00 XM Coin` --, e
# quem desambigua as duas convencoes e o SUFIXO, nao o numero. Sem elas, a
# leitura teria de adivinhar se `62,00` vale sessenta e dois ou seiscentos e
# vinte mil.
#
# Mesma disciplina de `LINHAS_ESPERADAS`: o que foi medido em campo, com a
# citacao da secao ao lado.
GLIFOS_EXIGIDOS = (
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ",",
    "XM Coin", "Adena",
)

# O que o rotulo digitado pode conter. Aceitar uma letra aqui aceitaria o `X` de
# `XM Coin` marcado por engano junto do preco -- e a conferencia de contagem
# ainda fecharia, gravando um molde errado com cara de certo.
CARACTERES_DO_ROTULO = frozenset("0123456789,")


def cobertura_dos_glifos(
    presentes: dict[str, np.ndarray] | set[str],
) -> tuple[list[str], list[str]]:
    """Quais de `GLIFOS_EXIGIDOS` ja existem, e quais faltam -- NOMEADOS.

    Devolver os faltantes por nome, e nao so a contagem, e o que permite ao
    usuario decidir o que marcar em seguida. "Faltam 3" nao diz onde procurar;
    "faltam 6, 8, Adena" diz.
    """
    tem = set(presentes)
    existem = [g for g in GLIFOS_EXIGIDOS if g in tem]
    faltam = [g for g in GLIFOS_EXIGIDOS if g not in tem]
    return existem, faltam


def fundir_glifos(
    anteriores: dict[str, np.ndarray], desta_rodada: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
    """Funde por ROTULO: o corte novo vence, o ausente e PRESERVADO.

    Precedente direto do CR-04, que consertou exatamente este defeito no caminho
    dos moldes de NOME, e pela mesma razao: cada molde custou um arrasto de
    mouse sobre um frame gravado, e este e o unico caminho do projeto capaz de
    apagar trabalho de calibracao sem perguntar.

    O caso que isto protege e comum, nao exotico: o frame que calibra a grade
    NAO tem os dez digitos (medido -- o `8` nao aparece em nenhuma das 24
    capturas da gravacao de calibragem), entao a segunda rodada corta um
    SUBCONJUNTO por construcao. Sem fusao, ela apagaria os nove que ja estavam.
    """
    return {**anteriores, **desta_rodada}


def _pedir_rotulo(
    ler, quantos_glifos: int
) -> str | None:
    """Le o numero como o usuario o LE na tela, e confere contra a contagem.

    ESTA CONFERENCIA E O CORACAO DO MODO DE DIGITOS. Ela transforma um erro de
    marcacao -- o retangulo que cortou meio digito, ou que pegou o `X` de
    `XM Coin` junto -- em recusa IMEDIATA, em vez de num molde errado gravado
    com a mesma confianca de um certo. Um `8` cortado pela metade viraria o
    molde oficial do `8`, e todo preco que o contivesse sairia errado, calado.

    Devolve `None` quando a marcacao deve ser descartada.
    """
    rotulo = str(ler("  digite o numero como voce o LE na tela (com a virgula): "))
    rotulo = rotulo.strip()

    if not rotulo or any(c not in CARACTERES_DO_ROTULO for c in rotulo):
        print(
            "  RECUSADO: o rotulo aceita apenas DIGITOS e a VIRGULA "
            "(exemplo: 18,90). Marque de novo."
        )
        return None

    if len(rotulo) != quantos_glifos:
        print(
            f"  RECUSADO: vi {quantos_glifos} glifo(s) no retangulo, mas voce "
            f"digitou {len(rotulo)} caractere(s).\n"
            f"  Os dois numeros tem de bater. Provavelmente o retangulo cortou "
            f"um digito pela metade, pegou o sufixo de moeda junto, ou deixou "
            f"um digito de fora. Marque de novo, com folga em cima e embaixo."
        )
        return None

    return rotulo


def cortar_glifos(
    pixels: np.ndarray,
    ja_gravados: dict[str, np.ndarray],
    ler=None,
) -> dict[str, np.ndarray]:
    """O laco de marcacao dos glifos. Devolve SO o que foi cortado nesta rodada.

    O usuario marca UM NUMERO e digita o que le -- ele nunca marca dez
    retangulos, um por digito. E a mesma economia de erro humano que ja deriva
    dez linhas de uma linha marcada (D-06): marcar dez acumula dez erros,
    marcar um e derivar acumula um.

    Terminar com o conjunto INCOMPLETO e permitido e esperado: o frame que
    calibra a grade nao contem os dez digitos (medido -- o `8` nao aparece em
    nenhuma das 24 capturas daquela gravacao). Quem completa e uma segunda
    rodada com `--so-digitos` sobre outro frame, e a fusao preserva as duas.

    A fusao NAO acontece aqui de proposito: esta funcao devolve o corte cru, e
    quem funde e `fundir_glifos`, chamada por `calibrar`. Assim o laco continua
    testavel sem calibracao nenhuma em disco.

    `ler` e resolvido AQUI, e nao no valor padrao da assinatura: um `ler=input`
    no cabecalho amarra o `input` que existia no momento em que o modulo foi
    importado, e quem o substituisse depois -- um teste, ou uma ponte futura que
    leia de outro lugar -- seria ignorado calado.
    """
    ler = ler or input
    cortados: dict[str, np.ndarray] = {}

    print("")
    print("  " + "-" * 58)
    print("  CORTE DOS GLIFOS DE PRECO")
    print("")
    print("  Marque UM numero inteiro da coluna de preco por vez -- SEM o")
    print("  sufixo de moeda ao lado e SEM o icone. Depois digite esse numero")
    print("  como voce o le na tela, com a virgula.")
    print("")
    print("  A ferramenta confere a contagem: se o que voce digitou nao tiver")
    print("  o mesmo tanto de caracteres que os glifos vistos, a marcacao e")
    print("  descartada e voce marca de novo.")
    print("  " + "-" * 58)

    while True:
        existem, faltam = cobertura_dos_glifos(
            set(ja_gravados) | set(cortados)
        )
        print("")
        print(f"  ja tenho ({len(existem)}): {', '.join(existem) or '-'}")
        if faltam:
            print(f"  ainda FALTA ({len(faltam)}): {', '.join(faltam)}")
        else:
            print("  conjunto COMPLETO.")

        escolha = str(
            ler("  [n] numero  [x] XM Coin  [a] Adena  [f] terminar: ")
        ).strip().lower()

        if escolha in ("f", "fim", "terminar"):
            return cortados

        if escolha in ("n", "numero", "número"):
            x, y, larg, alt = _marcar(
                pixels,
                "Numero da coluna de preco",
                "Marque UM numero da coluna de preco (sem o sufixo) e tecle ENTER.",
            )
            recorte = pixels[y : y + alt, x : x + larg]
            faixa, runs = segmentar_glifos(recorte)
            if faixa is None or not runs:
                print(
                    "  RECUSADO: nao vi texto nenhum nesse retangulo. Remarque "
                    "por cima dos digitos."
                )
                continue

            print(f"  vi {len(runs)} glifo(s) nesse retangulo.")
            rotulo = _pedir_rotulo(ler, len(runs))
            if rotulo is None:
                continue

            topo, base = faixa
            mascara = (mascara_de_texto(recorte) * 255).astype(np.uint8)
            for caractere, (inicio, fim) in zip(rotulo, runs):
                cortados[caractere] = mascara[topo:base, inicio:fim].copy()
            print(f"  ok: {rotulo}")
            continue

        if escolha in ("x", "a", "xm", "adena"):
            # A ferramenta PERGUNTA qual palavra esta sendo marcada em vez de
            # deduzir: deduzir erraria calado, e um `Adena` gravado como
            # `XM Coin` inverteria a convencao da virgula em toda leitura.
            palavra = "XM Coin" if escolha in ("x", "xm") else "Adena"
            x, y, larg, alt = _marcar(
                pixels,
                f"Palavra: {palavra}",
                f"Marque a palavra '{palavra}' INTEIRA e tecle ENTER.",
            )
            molde = recortar_sufixo(pixels[y : y + alt, x : x + larg])
            if molde is None:
                print(
                    f"  RECUSADO: nao vi texto nenhum nesse retangulo. Remarque "
                    f"por cima da palavra '{palavra}'."
                )
                continue
            cortados[palavra] = molde
            print(f"  ok: {palavra}")
            continue

        print("  opcao desconhecida. Use n, x, a ou f.")


def montar_glifos(moldes: dict[str, np.ndarray], escala: int = 6) -> np.ndarray:
    """A montagem dos glifos para o OLHO humano conferir, cada um com o rotulo.

    Numero conferindo com numero nao prova que o molde certo levou o rotulo
    certo -- so o olho prova que o que esta escrito `8` e mesmo um `8`. Mesmo
    argumento de `desenhar_conferencia`, um nivel abaixo.

    Ampliada porque um glifo tem 4 px de largura: no tamanho nativo ninguem
    confere nada.
    """
    if not moldes:
        return np.zeros((0, 0, 3), dtype=np.uint8)

    celulas = []
    for rotulo in sorted(moldes):
        molde = moldes[rotulo]
        if molde.size == 0:
            continue
        ampliado = cv2.resize(
            molde,
            (max(1, molde.shape[1] * escala), max(1, molde.shape[0] * escala)),
            interpolation=cv2.INTER_NEAREST,
        )
        colorido = cv2.cvtColor(ampliado, cv2.COLOR_GRAY2BGR)
        # Uma celula com espaco embaixo para o rotulo desenhado.
        celula = np.zeros((colorido.shape[0] + 28, max(colorido.shape[1], 90), 3),
                          dtype=np.uint8)
        celula[: colorido.shape[0], : colorido.shape[1]] = colorido
        cv2.putText(
            celula, rotulo, (2, celula.shape[0] - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA,
        )
        celulas.append(celula)

    if not celulas:
        return np.zeros((0, 0, 3), dtype=np.uint8)

    altura = max(c.shape[0] for c in celulas)
    faixa = np.zeros((altura, sum(c.shape[1] + 6 for c in celulas), 3), dtype=np.uint8)
    cursor = 0
    for celula in celulas:
        faixa[: celula.shape[0], cursor : cursor + celula.shape[1]] = celula
        cursor += celula.shape[1] + 6
    return faixa


def _empilhar(topo: np.ndarray, base: np.ndarray) -> np.ndarray:
    """Uma tela so, para UMA chamada de `_gravar_conferencia`.

    Ela grava num nome FIXO: chamar duas vezes na mesma rodada apagaria a
    primeira imagem, e o usuario conferiria metade da calibracao achando que
    conferiu tudo. Entao os retangulos e a montagem dos glifos vao juntos.
    """
    if topo.size == 0:
        return base
    if base.size == 0:
        return topo
    largura = max(topo.shape[1], base.shape[1])
    tela = np.zeros((topo.shape[0] + base.shape[0], largura, 3), dtype=np.uint8)
    tela[: topo.shape[0], : topo.shape[1]] = topo
    tela[topo.shape[0] :, : base.shape[1]] = base
    return tela




def _conferir_os_glifos(fundidos: dict[str, np.ndarray]) -> ResultadoDaConfusao:
    """Roda a matriz sobre o conjunto FUNDIDO e recusa alto quando ela reprova.

    DUAS MATRIZES, E NAO UMA, porque sao duas confusoes REALMENTE ALCANCAVEIS e
    diferentes:

    - entre os GLIFOS DE UM CARACTERE, que e de onde um preco e lido. Confundir
      `0` com `8` troca o preco;
    - entre as duas PALAVRAS de sufixo, que e o que decide se a virgula e
      separador de milhar ou decimal. Confundir `XM Coin` com `Adena` inverte a
      convencao da linha inteira.

    Um digito NUNCA e candidato a casar com uma palavra: em campo eles moram em
    colunas diferentes e o leitor sabe qual esta lendo. Misturar os dois numa
    matriz so tambem mediria mal -- o alinhamento por preenchimento poria um
    digito de 4 px dentro de uma caixa de 35 px, e o resultado seria dominado
    pela area vazia, nao pelo desenho.

    O limiar devolvido e o dos DIGITOS: e o conjunto de onde sai um preco.
    """
    de_um_caractere = {r: m for r, m in fundidos.items() if len(r) == 1}
    palavras = {r: m for r, m in fundidos.items() if len(r) > 1}

    resultado = matriz_de_confusao_de_glifos(de_um_caractere)
    print()
    for (a, b), score in sorted(resultado.matriz.items(), key=lambda kv: -kv[1]):
        print(f"  {score:.4f}  {a}  x  {b}")
    print(explicar_glifos(resultado))
    if not resultado.aprovado:
        raise MercadoNaoCalibravel(
            "nada foi gravado: os glifos precisam ser separaveis primeiro"
        )

    if len(palavras) > 1:
        das_palavras = matriz_de_confusao_de_glifos(palavras)
        for (a, b), score in sorted(das_palavras.matriz.items(), key=lambda kv: -kv[1]):
            print(f"  {score:.4f}  {a}  x  {b}")
        print(explicar_glifos(das_palavras))
        if not das_palavras.aprovado:
            raise MercadoNaoCalibravel(
                "nada foi gravado: as palavras de sufixo precisam ser "
                "separaveis primeiro — confundi-las inverte a convencao da "
                "virgula em toda leitura"
            )

    return resultado


def _gravar_os_glifos(
    cal: Calibracao,
    cortados: dict[str, np.ndarray],
    fundidos: dict[str, np.ndarray],
    resultado: ResultadoDaConfusao,
) -> None:
    """Escreve os glifos e o limiar deles -- FUNDINDO, nunca substituindo.

    Mesma guarda que o CR-04 instalou para os moldes de nome, pela mesma razao:
    lista vazia jamais sobrescreve lista nao-vazia. A diferenca e que aqui a
    rodada de subconjunto e o caso NORMAL, nao a excecao -- o frame que calibra
    a grade nao tem os dez digitos.
    """
    if cortados:
        cal.mercado_templates_de_digito = glifos_para_calibracao(fundidos)
    elif cal.mercado_templates_de_digito:
        print(
            f"\nMantidos os {len(cal.mercado_templates_de_digito)} molde(s) de "
            f"glifo da calibracao anterior — nenhum foi recortado nesta rodada."
        )

    # So quando a matriz DERIVOU um limiar. Com menos de dois glifos ela nao
    # deriva, e um numero inventado aqui iria para o `calibration.json` onde a
    # Fase 2 o le como verdade medida (a licao do CR-03).
    if resultado.limiar_sugerido is not None:
        cal.mercado_limiar_de_glifo = resultado.limiar_sugerido


def _anunciar_o_que_faltou(fundidos: dict[str, np.ndarray]) -> None:
    """O bloco alto do fim, com os faltantes NOMEADOS.

    Repetido aqui, DEPOIS da linha de calibracao gravada, e nao so no meio da
    sessao: no meio ele rola para fora da tela junto com a matriz, e o usuario
    fecha o terminal achando que terminou.
    """
    _existem, faltam = cobertura_dos_glifos(fundidos)
    if not faltam:
        print("  conjunto de glifos COMPLETO.")
        return

    print("")
    print("  " + "!" * 58)
    print(f"  FALTAM {len(faltam)} GLIFO(S): {', '.join(faltam)}")
    print("")
    print("  A leitura de precos da Fase 2 vai DESCARTAR toda linha que")
    print("  contenha um glifo nao gravado — ela nao chuta.")
    print("")
    print("  Complete o conjunto com um frame que tenha os que faltam:")
    print("    .\\calibrar-mercado.bat --so-digitos --frame <outro-frame.png>")
    print("  " + "!" * 58)


def _calibrar_so_digitos(
    args: argparse.Namespace,
    cal: Calibracao,
    arquivo: Path,
    caminho: Path,
    pixels: np.ndarray,
    glifos_anteriores: dict[str, np.ndarray],
) -> int:
    """O modo de corte ISOLADO: so os glifos, sem refazer ancoras e grade.

    ELE EXISTE POR UM FATO MEDIDO, NAO POR CONVENIENCIA. O frame que calibrou a
    grade atual (`20260828-115700-calibragem`) NAO contem o digito `8`: conferi
    as 24 capturas daquela gravacao e as tres zonas numericas da grade estao
    congeladas -- diferenca maxima de 2 a 3 niveis por pixel ao longo das 24 --,
    entao sao os mesmos precos em todas elas e nenhuma traz o `8`. Sem esta
    flag, completar o conjunto obrigaria o usuario a refazer os CINCO arrastos
    de ancora e grade a cada frame visitado.

    Trocar de frame nao acopla nada: moldes de glifo nao carregam coordenada
    nenhuma -- sao recortes de imagem. A unica exigencia e a geometria da
    janela, que `conferir_o_frame` ja checou antes de chegarmos aqui.
    """
    altura, largura = pixels.shape[:2]
    print(f"\nCortando GLIFOS sobre {caminho.name} ({largura}x{altura})")
    print("  (modo --so-digitos: ancoras, grade e watchlist NAO sao tocadas)")

    cortados = cortar_glifos(pixels, glifos_anteriores)
    fundidos = fundir_glifos(glifos_anteriores, cortados)
    resultado = _conferir_os_glifos(fundidos)

    # Uma unica chamada, com SO a montagem: nao ha retangulo novo a conferir
    # neste modo.
    conferencia = _gravar_conferencia(montar_glifos(fundidos))

    _gravar_os_glifos(cal, cortados, fundidos, resultado)

    try:
        cal.salvar(arquivo)
    except OSError as erro:
        raise MercadoNaoCalibravel(
            f"nao consegui gravar {arquivo}: {erro}\n"
            f"  A calibracao NAO foi salva. O motivo mais comum e o arquivo "
            f"estar aberto noutro programa, ou a pasta ser somente-leitura."
        ) from erro

    print(f"\nCalibracao de mercado gravada em {arquivo.name}")
    print(f"  glifos       : {len(fundidos)} molde(s) de glifo")
    _anunciar_o_que_faltou(fundidos)
    _texto_final_da_conferencia(conferencia, arquivo)
    return 0



def calibrar(args: argparse.Namespace) -> int:
    arquivo = Path(args.calibracao) if args.calibracao else ARQUIVO_CALIBRACAO
    cal = carregar_calibracao(arquivo)

    caminho = escolher_frame(
        Path(args.gravacao) if args.gravacao else None,
        Path(args.frame) if args.frame else None,
        args.indice,
    )
    pixels = cv2.imread(str(caminho))
    if pixels is None:
        raise MercadoNaoCalibravel(f"nao consegui decodificar {caminho}")
    # VALE TAMBEM NO MODO ISOLADO: o tamanho da FONTE depende do tamanho da
    # janela, entao cortar glifos de um frame de outra geometria produziria
    # moldes que nunca casam.
    conferir_o_frame(cal, pixels)

    # Os glifos ja gravados, para a cobertura e para a FUSAO. Decodificados
    # cedo: um `mercado_templates_de_digito` corrompido tem de recusar ANTES de
    # o usuario gastar o trabalho de mouse, e nao depois.
    glifos_anteriores = glifos_de_calibracao(cal.mercado_templates_de_digito)

    if getattr(args, "so_digitos", False):
        return _calibrar_so_digitos(args, cal, arquivo, caminho, pixels,
                                    glifos_anteriores)

    # A WATCHLIST E LIDA AQUI, ANTES DA PRIMEIRA JANELA DE SELECAO.
    #
    # Ela so e USADA la embaixo, depois das ancoras e da grade -- mas e onde ela
    # era LIDA que estava o problema: um `config.toml` com erro de sintaxe, ou
    # com `watchlist` do tipo errado, so era descoberto depois de cinco arrastos
    # de mouse. Falhar antes de o usuario gastar o trabalho e mais barato que
    # falhar depois, e nao custa nada.
    watchlist = ler_watchlist(ARQUIVO_CONFIG)

    altura, largura = pixels.shape[:2]
    print(f"\nCalibrando o mercado sobre {caminho.name} ({largura}x{altura})")
    print("")
    print("  " + "-" * 58)
    print("  VAO ABRIR 5 JANELAS DE SELECAO, uma de cada vez, no CANTO")
    print("  SUPERIOR ESQUERDO do monitor principal.")
    print("")
    print("  Se nao ver a janela, ela pode estar ATRAS deste terminal")
    print("  ou no outro monitor: procure na barra de tarefas pelo")
    print("  nome que aparece abaixo.")
    print("")
    print("  Em cada uma: arraste o mouse e confirme com ENTER ou ESPACO.")
    print("  NAO feche no X -- fechar no X cancela e nada e gravado.")
    print("  " + "-" * 58)
    print("Abra o painel do World Exchange no frame antes de marcar as regioes.\n")

    # --- as ancoras ---
    caixas: dict[str, tuple[int, int, int, int]] = {}
    for nome, _dx, _dy, larg, alt, descricao in ANCORAS_SUGERIDAS:
        caixas[nome] = _marcar(
            pixels,
            f"Ancora: {nome}",
            f"Marque {descricao} (sugerido: {larg}x{alt}) e tecle ENTER.",
        )
    origem = (caixas["titulo"][0], caixas["titulo"][1])
    ancoras = montar_ancoras(pixels, caixas, origem)

    # --- a grade ---
    #
    # O AVISO DO CABECALHO EXISTE POR ERRO MEDIDO EM CAMPO, 2026-08-29.
    #
    # Na primeira marcacao humana desta ferramenta o usuario incluiu a faixa
    # `Auction List | Total Price | 5 mln increment | Buy` dentro da area da
    # lista. E o engano natural: visualmente o cabecalho parece a borda de cima
    # da tabela. Mas ele nao e uma linha de dados, e `derivar_grade` conta as
    # linhas a partir do TOPO desta area -- entao engoli-lo desloca as DEZ, e o
    # erro so apareceria na Fase 2, lendo preco alguns pixels fora do lugar.
    #
    # Custa duas linhas de texto avisar antes; custa uma sessao inteira de
    # marcacao descobrir depois.
    layout = args.layout
    print("")
    print("  " + "-" * 58)
    print("  A AREA DA LISTA COMECA NA PRIMEIRA LINHA DE DADOS.")
    print("")
    print("  NAO inclua a faixa de cabecalho (`Auction List | Total Price |")
    print("  5 mln increment | Buy`): ela nao e uma linha, e engoli-la desloca")
    print("  todas as 10 linhas para baixo.")
    print("")
    print("  Comece no topo da PRIMEIRA linha de dados e termine na base da")
    print("  ultima. De preferencia pare antes da barra de rolagem, a direita.")
    print("  " + "-" * 58)
    caixa_grade = _marcar(
        pixels, "Grade", "Marque a AREA DA LISTA (SEM o cabecalho) e tecle ENTER."
    )
    print("")
    print("  Agora SO a primeira linha: a mesma largura, a altura de UMA linha.")
    print("  E dela que sai o passo entre linhas, e dai quantas cabem na pagina.")
    caixa_linha = _marcar(
        pixels, "Primeira linha", "Marque SO a PRIMEIRA LINHA da lista e tecle ENTER."
    )
    grade = derivar_grade(caixa_grade, caixa_linha, layout, origem)

    # --- os moldes da watchlist (lida la em cima, antes das janelas) ---
    if not watchlist:
        print(
            "\nSem watchlist no config.toml ([mercado] watchlist = [...]): "
            "nenhum molde de nome foi cortado.\n"
            "As ancoras e a grade ficam gravadas e os moldes de nome de uma "
            "calibracao ANTERIOR sao preservados; rode de novo depois de "
            "escrever a watchlist."
        )
    moldes_de_nome: dict[str, np.ndarray] = {}
    cinza = cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY)
    for item in watchlist:
        x, y, larg, alt = _marcar(
            pixels,
            f"Nome: {item}",
            f"Marque o nome COMO RENDERIZADO de '{item}' — com o prefixo "
            f"'+N ' quando houver — e tecle ENTER.",
        )
        moldes_de_nome[item] = cinza[y : y + alt, x : x + larg].copy()

    resultado = matriz_de_confusao(moldes_de_nome)
    print()
    for (a, b), score in sorted(resultado.matriz.items(), key=lambda kv: -kv[1]):
        print(f"  {score:.4f}  {a}  x  {b}")
    print(resultado.explicar())
    if not resultado.aprovado:
        raise MercadoNaoCalibravel(
            "nada foi gravado: a watchlist precisa ser separavel primeiro"
        )

    # --- os glifos de preco ---
    glifos_cortados = cortar_glifos(pixels, glifos_anteriores)
    glifos_fundidos = fundir_glifos(glifos_anteriores, glifos_cortados)
    resultado_glifos = _conferir_os_glifos(glifos_fundidos)

    # --- grava a conferencia e o arquivo ---
    #
    # UMA UNICA CHAMADA POR RODADA. `_gravar_conferencia` grava num nome FIXO:
    # a segunda chamada apagaria a primeira imagem, e o usuario conferiria
    # metade da calibracao achando que conferiu tudo. Entao os retangulos e a
    # montagem dos glifos vao empilhados na MESMA tela.
    regioes = dict(caixas)
    regioes["grade"] = caixa_grade
    regioes["linha_1"] = caixa_linha
    conferencia = _gravar_conferencia(
        _empilhar(
            desenhar_conferencia(pixels, regioes),
            montar_glifos(glifos_fundidos),
        )
    )

    tx, ty, tlarg, talt = caixas["titulo"]
    cal.mercado_ancora = Regiao(esquerda=tx, topo=ty, largura=tlarg, altura=talt)
    # POR NOME, NAO POR POSICAO. `ancoras[0]` so era o `titulo` porque `caixas`
    # preserva a ordem de insercao de ANCORAS_SUGERIDAS e `titulo` esta
    # primeiro. Reordenar aquela constante -- o que a docstring de
    # `localizar_painel` INCENTIVA ("a ordem certa e a mais confiavel
    # primeiro") -- passaria a gravar o molde de uma ancora ao lado do
    # retangulo de outra, em `mercado_ancora`. Erro calado, e a duas linhas de
    # distancia do `caixas["titulo"]` logo acima, que ja acerta por nome.
    molde_do_titulo = next(a.molde for a in ancoras if a.nome == "titulo")
    cal.mercado_molde_da_ancora = molde_para_hex(molde_do_titulo)
    cal.mercado_limiar_da_ancora = CASAMENTO_MINIMO_DA_ANCORA
    cal.mercado_geometria_da_captura = {"largura": int(largura), "altura": int(altura)}
    cal.mercado_ancoras = ancoras_para_calibracao(ancoras)
    cal.mercado_grade = grade
    # SO ESCREVE O QUE FOI CORTADO NESTA RODADA.
    #
    # Sem a guarda, uma rodada sem watchlist atribuia `[]` aqui e o
    # `cal.salvar` logo abaixo regravava o arquivo INTEIRO: os moldes de uma
    # calibracao anterior desapareciam, calados. O caminho e trivial de
    # alcancar -- `ler_watchlist` devolve `[]` quando o `config.toml` nao
    # existe (outro checkout, um worktree), quando o usuario comentou a
    # watchlist para reajustar so uma ancora, ou quando ele escreveu
    # `[mercado]` sem a chave.
    #
    # E o console dizia o contrario: "as ancoras e a grade ja ficam gravadas"
    # afirma um comportamento ADITIVO. Este era o unico caminho do projeto que
    # apagava trabalho de calibracao sem perguntar, e o prejuizo e proporcional
    # a watchlist: cada molde custou um arrasto de mouse sobre um frame
    # gravado. O cabecalho deste modulo promete "muta so os campos de mercado"
    # -- mutar para vazio e destruir.
    if moldes_de_nome:
        cal.mercado_templates_de_nome = [
            {"nome": nome, "molde": molde_para_hex(molde)}
            for nome, molde in moldes_de_nome.items()
        ]
    elif cal.mercado_templates_de_nome:
        print(
            f"\nMantidos os {len(cal.mercado_templates_de_nome)} molde(s) de "
            f"nome da calibracao anterior — nenhum foi recortado nesta rodada."
        )
    if resultado.limiar_sugerido is not None:
        cal.mercado_limiar_de_template = resultado.limiar_sugerido

    _gravar_os_glifos(cal, glifos_cortados, glifos_fundidos, resultado_glifos)

    # REGRAVA O ARQUIVO INTEIRO. Nada e impresso para o usuario colar: o
    # criterio 3 do ROADMAP e "sem editar JSON a mao".
    #
    # Pasta somente-leitura, disco cheio ou arquivo travado por antivirus
    # produziam um `OSError` cru -- traceback depois de todo o trabalho de
    # mouse. `MercadoNaoCalibravel` ja imprime limpo e devolve 1, e o `.bat` ja
    # trata o `errorlevel`.
    try:
        cal.salvar(arquivo)
    except OSError as erro:
        raise MercadoNaoCalibravel(
            f"nao consegui gravar {arquivo}: {erro}\n"
            f"  A calibracao NAO foi salva. O motivo mais comum e o arquivo "
            f"estar aberto noutro programa, ou a pasta ser somente-leitura."
        ) from erro
    print(f"\nCalibracao de mercado gravada em {arquivo.name}")
    print(f"  ancoras      : {', '.join(a.nome for a in ancoras)}")
    print(
        f"  grade        : {grade['linhas_por_pagina']} linhas de "
        f"{grade['altura_da_linha']} px, layout '{grade['layout']}'"
    )
    print(f"  watchlist    : {len(moldes_de_nome)} molde(s) de nome")
    print(f"  glifos       : {len(glifos_fundidos)} molde(s) de glifo")
    _anunciar_o_que_faltou(glifos_fundidos)
    _texto_final_da_conferencia(conferencia, arquivo)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m l2scanner.calibrar_mercado",
        description="Calibra as regioes do World Exchange sobre um frame GRAVADO.",
    )
    parser.add_argument("--gravacao", help="pasta de gravacao de JANELA COMPLETA")
    parser.add_argument("--frame", help="um PNG especifico")
    parser.add_argument(
        "--indice", type=int, default=None,
        help="qual frame da gravacao (padrao: o do meio)",
    )
    parser.add_argument(
        "--layout", default="negociacao",
        choices=("negociacao", "adena", "busca"),
        help="qual dos TRES layouts de coluna esta na tela",
    )
    parser.add_argument("--calibracao", help="outro calibration.json (para teste)")
    # A FLAG EXISTE POR UM FATO MEDIDO. O frame que calibrou a grade atual nao
    # contem o digito `8` (conferidas as 24 capturas daquela gravacao), entao
    # completar o conjunto de glifos exige visitar outro frame -- e sem esta
    # flag isso obrigaria a refazer os cinco arrastos de ancora e grade a cada
    # visita. Moldes de glifo nao carregam coordenada, entao trocar de frame nao
    # acopla nada.
    parser.add_argument(
        "--so-digitos", action="store_true", dest="so_digitos",
        help="corta SO os glifos de preco, sem tocar em ancoras, grade e watchlist",
    )
    args = parser.parse_args(argv)

    # O AVISO DE DPI VALE MAIS AQUI DO QUE NOS OUTROS DOIS LUGARES QUE O TEM.
    #
    # `calibrar.py` e `__main__.py` ja testavam `_MODO_DPI`; este modulo
    # calculava a variavel e nunca a conferia -- ela ficava sem uso. Numa falha
    # de DPI o scanner apenas le errado NAQUELA execucao; o calibrador GRAVA as
    # coordenadas erradas no calibration.json, onde elas ficam. Era a instancia
    # em que o aviso mais importa, e a unica das tres que nao o tinha.
    if _MODO_DPI.startswith("FALHOU"):
        print("AVISO: nao consegui declarar consciencia de DPI.")
        print("Se a escala da sua tela nao for 100%, as coordenadas sairao erradas")
        print("-- e esta ferramenta as GRAVA no calibration.json.\n")

    try:
        return calibrar(args)
    except MercadoNaoCalibravel as erro:
        print(f"\n{erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
