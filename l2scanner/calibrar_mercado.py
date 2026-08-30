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
from .mercado_geometria import (  # noqa: E402
    GradeMedida,
    ancora_deslocada,
    localizar_o_titulo,
    medir_a_grade,
)
from .mercado_visao import (  # noqa: E402
    CASAMENTO_MINIMO_DA_ANCORA,
    AncoraDoPainel,
    ancoras_de_calibracao,
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
    # ARREDONDA, NAO TRUNCA — e a diferenca custa uma linha inteira de dados.
    #
    # MEDIDO EM CAMPO 2026-08-29, na primeira calibracao completa por mao
    # humana. O usuario desenhou a area da lista CERTA: a conferencia visual
    # mostra o retangulo cobrindo as dez linhas, com o cabecalho de fora. Mas
    # ele saiu com 447 px em vez de 450, e `447 // 45` devolve 9.
    #
    # Tres pixels. Nenhuma mao acerta 450 exatos arrastando um mouse, e o preco
    # de errar por baixo era perder um anuncio inteiro por pagina, calado, la na
    # frente na leitura. `round(447 / 45)` devolve 10, que e o que os olhos veem.
    #
    # Isto NAO afrouxa a guarda: quem pega retangulo genuinamente errado e a
    # divergencia contra o layout medido, logo abaixo. Com o cabecalho engolido
    # a altura vai a ~495 px, e `round(495 / 45)` continua 11 — o aviso dispara
    # igual. O arredondamento absorve erro de mao; a divergencia acusa erro de
    # interpretacao. Sao coisas diferentes e cada uma tem seu mecanismo.
    linhas = max(1, round(galt / altura_da_linha))

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


def _avisar_divergencia_da_grade(
    medida: GradeMedida | None,
    caixa_da_grade: tuple[int, int, int, int],
    caixa_da_primeira_linha: tuple[int, int, int, int],
) -> None:
    """Diz ALTO quando o desenho do usuario se afasta muito do que foi medido.

    INFORMACAO, NUNCA RECUSA. O usuario e a autoridade: a medicao veio de UM
    frame e de uma janela, e ha layouts e resolucoes que ela nao viu. O papel da
    ferramenta e tornar a resposta certa facil e a errada VISIVEL -- se ela
    recusasse, o unico caminho de correcao seria editar o JSON a mao, que e
    literalmente o que o criterio 3 do ROADMAP proibe.

    Vale como rede junto de `derivar_grade`, que ja compara a contagem de linhas
    com `LINHAS_ESPERADAS`. A diferenca e a cobertura: aquela guarda so existe
    para layouts com contagem medida em campo; esta compara com o que foi medido
    NESTE frame, e portanto vale para qualquer layout.

    A tolerancia e de meia linha (o passo dividido por 2). Abaixo disso a
    divergencia e ajuste fino de borda; acima, e sinal de que um retangulo pegou
    o cabecalho junto -- que foi o erro medido em campo em 2026-08-29, e vale
    exatamente uma linha inteira.
    """
    if medida is None:
        return
    tolerancia = max(2, medida.passo // 2)
    esperado_topo = medida.topo
    _, topo, _, altura = caixa_da_grade
    _, _, _, altura_da_linha = caixa_da_primeira_linha

    avisos: list[str] = []
    if abs(topo - esperado_topo) > tolerancia:
        avisos.append(
            f"o TOPO da area ficou em y={topo}, e eu medi a primeira linha de "
            f"dados em y={esperado_topo} (diferenca de {abs(topo - esperado_topo)} px)."
        )
    if abs(altura - medida.altura) > tolerancia:
        avisos.append(
            f"a ALTURA da area ficou em {altura} px, e eu medi "
            f"{medida.altura} px ({medida.linhas} x {medida.passo})."
        )
    if abs(altura_da_linha - medida.passo) > tolerancia:
        avisos.append(
            f"a altura da PRIMEIRA LINHA ficou em {altura_da_linha} px, e eu "
            f"medi o passo entre linhas em {medida.passo} px."
        )
    if not avisos:
        return

    print("")
    print("  " + "!" * 58)
    print("  O QUE VOCE DESENHOU DIVERGE DO QUE EU MEDI NOS PIXELS:")
    for aviso in avisos:
        print(f"    - {aviso}")
    print("")
    print("  Isto NAO e recusa: o seu desenho vale. E aviso porque a causa mais")
    print("  provavel e o cabecalho ter entrado na area da lista, e esse erro")
    print("  desloca TODAS as linhas -- em silencio, ate a leitura de precos.")
    print("  Confira a imagem de conferencia antes de confiar nesta grade.")
    print("  " + "!" * 58)


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
    pixels: np.ndarray,
    titulo: str,
    instrucao: str,
    sugestao: tuple[int, int, int, int] | None = None,
) -> tuple[int, int, int, int]:
    caixa = _selecionar_regiao(pixels, titulo, instrucao, sugestao)
    if caixa is None:
        raise MercadoNaoCalibravel("selecao cancelada — nada foi gravado")
    return caixa


def sugerir_as_ancoras(
    forma_do_frame: tuple[int, int],
    origem: tuple[int, int],
    conhecidas: list[AncoraDoPainel],
) -> dict[str, tuple[int, int, int, int] | None]:
    """O retangulo sugerido de cada ancora, a partir da origem do painel.

    Prefere os deslocamentos da CALIBRACAO ANTERIOR do usuario aos de
    `ANCORAS_SUGERIDAS`, e a diferenca importa: as constantes foram medidas numa
    janela e num posicionamento; o `calibration.json` do usuario foi medido na
    maquina dele. Quando a anterior existe, ela e a evidencia melhor. Quando nao
    existe -- primeira calibracao --, as constantes ainda entregam uma sugestao
    util, porque o painel e a mesma arte.

    O nome `titulo` sai de fora de proposito: ele nao e derivado da origem, ele
    E a origem.
    """
    por_nome = {a.nome: a for a in conhecidas}
    saida: dict[str, tuple[int, int, int, int] | None] = {}
    for nome, dx, dy, largura, altura, _descricao in ANCORAS_SUGERIDAS:
        if nome == "titulo":
            continue
        anterior = por_nome.get(nome)
        if anterior is not None and anterior.molde.size:
            dx, dy = anterior.dx, anterior.dy
            altura, largura = anterior.molde.shape[:2]
        saida[nome] = ancora_deslocada(
            origem, (dx, dy), (largura, altura), forma_do_frame
        )
    return saida


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


# --------------------------------------------------------------------------
# A COLUNA DE PRECO, ACHADA PELOS PIXELS — para a ferramenta PROPOR o retangulo
# --------------------------------------------------------------------------

# Colunas vazias que ainda contam como DENTRO da mesma palavra.
#
# MEDIDO em `frame_000012`: dentro de `59,00` a maior lacuna entre dois glifos
# vizinhos e de 1 coluna (a docstring de `segmentar_glifos` registra isso: sem
# tolerancia nenhuma ela separou 8 numeros em 8 acertos). Entre o fim do numero
# e o comeco do `XM Coin` ao lado ha ~2 colunas, mas o sufixo nao entra nesta
# mascara -- ele fica INTEIRO abaixo do piso de 180 (V maximo 173). O que 8
# separa de verdade sao as COLUNAS da tabela, que distam centenas de pixels:
# 749-776 (icone), 785-880 (nome), 1274-1299 (preco), 1572-1597 (incremento),
# 1639-1657 (carrinho). Qualquer valor entre 2 e 200 daria os mesmos cinco
# grupos nas dez linhas; 8 fica bem dentro desse platô.
LACUNA_ENTRE_GRUPOS_DE_TEXTO = 8

# A palavra de sufixo tem de ter pelo menos isto de largura para valer.
#
# MEDIDO: `XM Coin` sai com 35-36 px em todas as linhas conferidas. 12 rejeita
# respingo de antialias sem chegar perto do valor real.
LARGURA_MINIMA_DO_SUFIXO = 12

# Folga em volta do retangulo proposto para um numero.
#
# Colunas vazias nas pontas NAO criam run em `segmentar_glifos` (ela separa por
# coluna vazia), entao a folga nao muda a contagem de glifos; ela so faz o
# retangulo desenhado na tela ficar legivel para o olho humano em vez de colado
# no desenho.
MARGEM_DO_RETANGULO_DE_PRECO = 2

# Piso e MARGEM para a ferramenta arriscar PROPOR a leitura de um glifo.
#
# Os dois juntos, e nao so o piso -- copia deliberada do par ja medido em
# `identidade.LIMIAR_DE_CASAMENTO` (0.75) + `MARGEM_MINIMA_SOBRE_O_SEGUNDO`
# (0.12), pela mesma razao: num conjunto fechado, "o quanto pareceu" vale menos
# que "o quanto pareceu MAIS que o segundo colocado".
#
# OS NUMEROS SAO MEDIDOS, e a primeira tentativa (piso unico de 0.95) foi
# derrubada pela medicao. Eu supus que o mesmo digito no mesmo frame casaria
# 1.000 por ser o mesmo desenho. Ele nao casa: o FUNDO da linha alterna entre 48
# e 66 (e o que `mercado_geometria` usa para achar a grade), e a mascara de
# brilho recorta o antialias do glifo um pouco diferente sobre cada fundo.
# Medido nas 10 linhas de `frame_000012`, comparando cada glifo com o molde da
# linha anterior:
#
#     acerto  PIOR    0.837  (o `9` contra o `9` da linha de fundo oposto)
#     acerto  tipico  0.886 a 1.000
#     ERRO    MELHOR  0.717  (o `5` contra o `6`)
#
# Com 0.95 a ferramenta nao propunha NADA -- feature morta e ninguem saberia.
# Com 0.80 + margem 0.12: o pior acerto passa com 0.037 de folga, e o melhor
# erro precisaria subir 0.083 E abrir 0.12 sobre o segundo colocado para
# enganar. Nos dados medidos a margem do pior acerto e 0.169.
#
# E a proposta NUNCA e gravada sozinha: ela e escrita na tela, o usuario le, e
# so entra com ENTER -- ou ele digita outra coisa e a dele vale. A conferencia
# de contagem de `_pedir_rotulo` continua valendo por cima, e a montagem
# ampliada da conferencia visual continua sendo o portao final.
MINIMO_PARA_PROPOR_ROTULO = 0.80
MARGEM_MINIMA_PARA_PROPOR = 0.12


def _grupos_de_colunas(
    presenca: np.ndarray, lacuna: int
) -> list[tuple[int, int]]:
    """Os intervalos `[inicio, fim)` de colunas com pixel, tolerando `lacuna`.

    Irmao de `segmentar_glifos`, com UMA diferenca deliberada: aquela separa em
    QUALQUER coluna vazia, porque la a pergunta e "onde acaba um glifo"; aqui a
    pergunta e "onde acaba uma COLUNA DA TABELA", e um numero inteiro tem
    colunas vazias no meio por construcao.
    """
    grupos: list[tuple[int, int]] = []
    inicio: int | None = None
    vazias = 0
    for coluna, tem in enumerate(presenca):
        if tem:
            if inicio is None:
                inicio = coluna
            vazias = 0
        elif inicio is not None:
            vazias += 1
            if vazias >= lacuna:
                grupos.append((inicio, coluna - vazias + 1))
                inicio = None
    if inicio is not None:
        grupos.append((inicio, int(len(presenca))))
    return grupos


def _cauda_apagada(
    so_apagado: np.ndarray, tem_claro: np.ndarray, inicio: int
) -> int:
    """Quantas colunas de texto APAGADO seguem a direita, ANTES do proximo claro.

    A parada no primeiro texto claro e a regra inteira, e ela veio de uma
    medicao que derrubou a primeira versao desta deteccao.

    A tentativa anterior procurava "uma mancha apagada que COMECE depois do fim
    do numero". Nao funciona nas duas pontas:

    * a mancha do `XM Coin` COMECA DENTRO do preco (medido: o grupo apagado sai
      em 1278..1343, e o preco vai de 1274 a 1298) — porque as colunas entre um
      digito e o proximo nao tem pixel claro, so o antialias apagado. Com isso o
      preco de verdade era REJEITADO;
    * e a mancha que segue o ICONE da linha (o antialias do nome dourado
      `5,000,000 Adena` logo adiante) tem 59 colunas de largura, entao o icone
      era ACEITO como se fosse um preco com moeda ao lado.

    Cortar no primeiro claro resolve as duas: medido em `frame_000012`, a cauda
    do preco tem **44** colunas limpas ate o fim do `XM Coin`, e a do icone tem
    **9** — ela esbarra no nome nove colunas adiante. As outras tres colunas da
    tabela (nome, incremento, carrinho) dao 0, 1 e 1.

    `LACUNA_ENTRE_GRUPOS_DE_TEXTO` colunas seguidas sem nada tambem encerram a
    cauda: e o vao entre o numero e a palavra (5 px medidos) que precisa ser
    tolerado, nao um deserto.
    """
    ultimo: int | None = None
    vazias = 0
    for coluna in range(int(inicio), int(len(so_apagado))):
        if tem_claro[coluna]:
            break
        if so_apagado[coluna]:
            ultimo = coluna
            vazias = 0
            continue
        vazias += 1
        if vazias >= LACUNA_ENTRE_GRUPOS_DE_TEXTO:
            break
    if ultimo is None:
        return 0
    return ultimo + 1 - int(inicio)


def numeros_com_sufixo(faixa: np.ndarray) -> list[tuple[int, int, int]]:
    """Os grupos de texto CLARO seguidos de uma palavra APAGADA. Um preco, em suma.

    E aqui que a diferenca de brilho medida no plano 01-05 vira ferramenta em
    vez de armadilha. Na coluna `Total Price` o numero e claro (V ate 255) e o
    `XM Coin` ao lado dele fica INTEIRO abaixo de 180 (V maximo 173, p99 148).
    Duas consequencias:

    1. `mascara_de_texto` (V>180) ve o numero e NAO ve o sufixo -- por isso o
       grupo sai justo, sem o `XM Coin` grudado, que era uma das cinco duvidas
       que o usuario relatou em campo ("com o icone? com o `XM Coin`?").
    2. `mascara_do_sufixo` (V>120) MENOS a de texto isola exatamente a palavra
       apagada. Um grupo claro que tem uma dessas manchas logo a direita e um
       numero com moeda ao lado; e essa a assinatura da coluna de preco.

    MEDIDO nas dez linhas de `frame_000012`: cinco grupos claros por linha
    (icone, nome, preco, incremento, carrinho) e SO UM deles passa neste teste
    -- o preco em 1274..1299, com a mancha de `XM Coin` em 1300..1343. O nome
    `5,000,000 Adena` nao passa porque a palavra `Adena` e dourada e CLARA:
    entra no proprio grupo, sem cauda apagada. A coluna de incremento nao passa
    porque nao tem moeda escrita ao lado.

    Devolve `(inicio, fim, cauda)` por numero achado: as duas primeiras sao as
    colunas do NUMERO e a terceira e o comprimento da palavra apagada a direita
    dele, para o chamador poder propor tambem o retangulo do `XM Coin` -- que
    era a quinta duvida do relato de campo ("uma ocorrencia, ou todas?").

    Devolve `[]` quando nada casa -- o chamador entende isso como "nao sei
    propor", nunca como "nao ha preco".
    """
    if faixa.size == 0:
        return []
    claro = mascara_de_texto(faixa).astype(bool)
    if claro.size == 0:
        return []
    apagado = mascara_do_sufixo(faixa).astype(bool) & ~claro

    tem_claro = claro.any(axis=0)
    so_apagado = apagado.any(axis=0) & ~tem_claro

    achados: list[tuple[int, int, int]] = []
    for inicio, fim in _grupos_de_colunas(tem_claro, LACUNA_ENTRE_GRUPOS_DE_TEXTO):
        cauda = _cauda_apagada(so_apagado, tem_claro, fim)
        if cauda >= LARGURA_MINIMA_DO_SUFIXO:
            achados.append((inicio, fim, cauda))
    return achados


def sugerir_a_coluna_de_preco(
    pixels: np.ndarray, grade
) -> tuple[list[tuple[int, int, int, int]], list[tuple[int, int, int, int]]]:
    """Um retangulo por linha da grade: `(numeros, palavras_de_sufixo)`.

    Este e o coracao da inversao pedida em campo. Antes, a ferramenta descrevia
    o retangulo em prosa -- *"Marque UM numero da coluna de preco (sem o
    sufixo)"* -- e aceitava calada o que viesse: com o icone junto, com o
    `XM Coin` junto, meio digito cortado. Agora ela DESENHA o retangulo e o
    usuario confirma. O humano continua sendo a autoridade (ele pode redesenhar
    qualquer um), mas deixou de ser quem adivinha o que a frase queria dizer.

    A coluna e escolhida por VOTO entre as linhas, e nao pela primeira que
    casar: `numeros_com_sufixo` roda em cada linha da grade e a coluna
    vencedora e a que aparece em mais linhas. Uma tooltip cobrindo quatro linhas
    -- exatamente o que acontece em `frame_000010` -- derruba aquelas quatro e
    nao muda o veredito. Mesma logica de `agrupar_em_party`, e da votacao entre
    ancoras do 01-04.

    O VOTO E NA BORDA DIREITA, E ISSO FOI MEDIDO, NAO ESCOLHIDO. A primeira
    versao votava no par `(inicio, fim)` inteiro e funcionou em
    `frame_000012` -- onde os dez precos tem 5 glifos e a mesma largura -- e
    quebrou em `frame_000010`, onde `100,00`, `18,90` e `3,00` convivem na mesma
    coluna: o preco e alinhado a DIREITA, entao cada largura virava um candidato
    diferente e os votos se dividiam 3-2-1. Resultado medido: 3 das 6 linhas com
    preco eram propostas, e as tres perdidas eram justamente as mais longas --
    as que trazem os digitos que faltam no conjunto. Votando so na borda
    direita, as 6 voltam, cada uma com o retangulo justo do SEU numero.

    A palavra de sufixo sai da MESMA passagem, e nao de uma segunda deteccao: a
    cauda apagada ja foi medida para decidir que aquela coluna era preco. Propo-
    la fecha a quinta duvida do relato de campo -- *"Marque a palavra 'XM Coin'
    INTEIRA -- uma ocorrencia, ou todas?"* -- mostrando exatamente uma.

    Devolve `([], [])` quando nenhuma coluna se repete o bastante. Nao ha
    proposta honesta a dar ali, e sugerir um retangulo errado e pior que nao
    sugerir: o usuario aperta ENTER confiando nele.
    """
    vazio: tuple[list, list] = ([], [])
    if pixels is None or pixels.size == 0 or grade is None:
        return vazio

    altura_do_frame, largura_do_frame = pixels.shape[:2]
    esquerda = max(0, grade.esquerda)
    direita = min(largura_do_frame, grade.esquerda + grade.largura)
    if direita <= esquerda:
        return vazio

    votos: dict[int, list[tuple[int, int, int]]] = {}
    for indice in range(grade.linhas):
        _, topo, _, altura = grade.linha(indice)
        if topo < 0 or topo + altura > altura_do_frame:
            continue
        faixa = pixels[topo : topo + altura, esquerda:direita]
        for inicio, fim, cauda in numeros_com_sufixo(faixa):
            votos.setdefault(fim, []).append((indice, inicio, cauda))

    if not votos:
        return vazio
    # Empate desfeito pela borda mais a DIREITA: numa tabela de mercado a coluna
    # de preco fica depois do nome do item, e um empate so acontece quando duas
    # colunas tem moeda ao lado -- caso em que a da direita e a de preco total.
    borda, linhas = max(votos.items(), key=lambda item: (len(item[1]), item[0]))
    fim_absoluto = min(direita, esquerda + borda + MARGEM_DO_RETANGULO_DE_PRECO)

    numeros: list[tuple[int, int, int, int]] = []
    sufixos: list[tuple[int, int, int, int]] = []
    for indice, inicio, cauda in linhas:
        _, topo, _, altura = grade.linha(indice)
        x = max(esquerda, esquerda + inicio - MARGEM_DO_RETANGULO_DE_PRECO)
        if fim_absoluto <= x:
            continue
        numeros.append((x, topo, fim_absoluto - x, altura))
        # O retangulo do sufixo comeca EXATAMENTE onde o numero acaba, sem
        # margem a esquerda: uma folga ali puxaria o ultimo digito para dentro
        # do molde da palavra.
        inicio_do_sufixo = esquerda + borda
        fim_do_sufixo = min(direita, inicio_do_sufixo + cauda)
        if fim_do_sufixo > inicio_do_sufixo:
            sufixos.append(
                (inicio_do_sufixo, topo, fim_do_sufixo - inicio_do_sufixo, altura)
            )
    return numeros, sufixos


# --------------------------------------------------------------------------
# O cabecalho de coluna e as quatro colunas (Fase 02, LEIT-05 e D-11)
# --------------------------------------------------------------------------

# A BANDA DO CABECALHO, MEDIDA NA PESQUISA: `[topo_da_grade - 32, topo_da_grade
# - 2)`, por toda a largura da grade.
#
# Estes dois numeros vivem AQUI, na ferramenta, e nao no leitor: eles sao o que
# a ferramenta usa UMA VEZ para propor o recorte a um humano. O que atravessa
# para a producao e o `dy` e a `altura` GRAVADOS no `calibration.json` junto do
# molde — o leitor nunca recalcula a banda, ele le a que foi confirmada.
ACIMA_DO_TOPO_DA_GRADE = 32
FOLGA_ACIMA_DO_TOPO_DA_GRADE = 2


def retangulo_da_banda_do_cabecalho(
    grade, forma_do_frame: tuple[int, int]
) -> tuple[int, int, int, int] | None:
    """Onde fica a faixa `Goods | Quantity | Total | Unit price | Buy`.

    `None` quando ela nao cabe no frame — e nao um retangulo cortado. Um molde
    de cabecalho pela metade casaria pior que um molde inteiro sem dizer por
    que, e o portao de layout recusaria a pagina calado.
    """
    if grade is None:
        return None
    altura_do_frame, largura_do_frame = forma_do_frame[:2]
    topo = int(grade.topo) - ACIMA_DO_TOPO_DA_GRADE
    base = int(grade.topo) - FOLGA_ACIMA_DO_TOPO_DA_GRADE
    esquerda = int(grade.esquerda)
    direita = esquerda + int(grade.largura)
    if topo < 0 or base > altura_do_frame or base <= topo:
        return None
    if esquerda < 0 or direita > largura_do_frame or direita <= esquerda:
        return None
    return esquerda, topo, direita - esquerda, base - topo


def _valor_da_banda(banda: np.ndarray) -> np.ndarray:
    """O canal V da banda. O corte de brilho e um nivel de V, nao de cinza."""
    if banda.ndim == 2:
        return banda
    return cv2.cvtColor(banda, cv2.COLOR_BGR2HSV)[:, :, 2]


def grupos_do_cabecalho(
    banda: np.ndarray, corte: int | None
) -> list[tuple[int, int]]:
    """Os grupos de coluna claros da banda. Com `corte`, acima dele; sem, o
    piso compartilhado de `mascara_de_texto`.

    Passar `corte=None` NAO e um caso degenerado: e como se ve o que o corte
    REMOVEU. O teste que prova que a seta de ordenacao sai do molde compara os
    dois conjuntos.
    """
    if banda is None or banda.size == 0:
        return []
    if corte is None:
        presenca = mascara_de_texto(banda).astype(bool).any(axis=0)
    else:
        presenca = (_valor_da_banda(banda) > int(corte)).any(axis=0)
    return _grupos_de_colunas(presenca, LACUNA_ENTRE_GRUPOS_DE_TEXTO)


def medir_o_corte_de_brilho_do_cabecalho(banda: np.ndarray) -> int | None:
    """O nivel de brilho que separa os ROTULOS da SETA DE ORDENACAO.

    MEDIDO NESTA BANDA, nunca herdado. A pesquisa mediu, numa unica resolucao e
    numa unica pele: rotulos de coluna com V maximo 229, a seta com 181, a
    borda esquerda da faixa com 201. Escrever 210 no fonte seria transformar uma
    medicao de UMA maquina em promessa para todas — por isso o valor vai para o
    `calibration.json` e o que mora no codigo e o METODO.

    O METODO E O MAIOR VAO. Os picos de brilho dos grupos da banda formam dois
    aglomerados — o do texto que interessa e o do que nao interessa — e o corte
    e o meio do maior vao entre picos consecutivos. Nao ha constante nenhuma
    nisso: uma pele mais clara move os dois aglomerados juntos e o vao continua
    onde estava.

    POR QUE ISTO IMPORTA MAIS DO QUE PARECE: a seta fica DENTRO da celula de
    cabecalho e ANDA de coluna conforme o usuario ordena (medido na secao 3 do
    spike, e no par de fixtures `goods` x `unitprice`). Um molde cortado COM a
    seta casa a ordenacao em que foi cortado e recusa a outra — e o portao de
    layout recusaria a pagina inteira, para sempre, sem uma linha de erro.

    `None` quando nao ha dois picos: sem vao nao ha o que medir, e propor um
    corte inventado e pior que nao propor.
    """
    if banda is None or banda.size == 0:
        return None
    grupos = grupos_do_cabecalho(banda, None)
    if len(grupos) < 2:
        return None
    valor = _valor_da_banda(banda)
    picos = sorted({int(valor[:, a:b].max()) for a, b in grupos})
    if len(picos) < 2:
        return None
    baixo, alto = max(zip(picos, picos[1:]), key=lambda par: par[1] - par[0])
    corte = (baixo + alto) // 2
    # O corte tem de ficar ESTRITAMENTE dentro do vao: igual ao pico de baixo
    # ele nao remove nada, igual ao de cima ele remove tudo.
    if not baixo < corte < alto:
        return None
    return int(corte)


def sugerir_o_molde_do_cabecalho(
    banda: np.ndarray, layout: str, dy: int, corte: int | None
) -> dict | None:
    """O dict de `mercado_cabecalho_de_coluna`, cortado da mascara de brilho.

    O molde guardado NAO e a banda crua: e a banda com o corte aplicado, tudo
    abaixo dele zerado. E o mesmo desenho que o portao de layout vai produzir a
    partir do frame ao vivo, com o mesmo corte lido do arquivo — comparar o cru
    com o cortado seria comparar convencoes.

    `dy` e relativo a ORIGEM DO PAINEL, como a grade e as ancoras, e pela mesma
    razao medida: o painel anda 827x831 px. O `dx` nao e gravado porque a banda
    tem exatamente a largura da grade e comeca onde ela comeca.
    """
    if banda is None or banda.size == 0 or corte is None:
        return None
    valor = _valor_da_banda(banda)
    molde = np.where(valor > int(corte), valor, 0).astype(np.uint8)
    empacotado = molde_para_hex(molde)
    return {
        "layout": str(layout),
        "dy": int(dy),
        "corte_de_brilho": int(corte),
        "altura": empacotado["altura"],
        "largura": empacotado["largura"],
        "bytes": empacotado["bytes"],
    }


def _grupos_claros_por_linha(
    pixels: np.ndarray, grade
) -> list[list[tuple[int, int]]]:
    """Os grupos de texto claro de cada linha CHEIA, relativos a grade.

    Linha vazia nao entra: ela nao tem icone nem nome, entao nao tem o que
    dizer sobre onde uma coluna comeca. E a mesma decisao ja escrita no CONTEXT:
    linha vazia se reconhece por AUSENCIA DE CONTEUDO, nunca por cor de fundo.
    """
    if pixels is None or pixels.size == 0 or grade is None:
        return []
    altura_do_frame, largura_do_frame = pixels.shape[:2]
    esquerda, largura = int(grade.esquerda), int(grade.largura)
    if esquerda < 0 or largura <= 0 or esquerda + largura > largura_do_frame:
        return []

    saida: list[list[tuple[int, int]]] = []
    for indice in range(int(grade.linhas)):
        _, topo, _, altura = grade.linha(indice)
        if topo < 0 or topo + altura > altura_do_frame:
            continue
        faixa = pixels[topo : topo + altura, esquerda : esquerda + largura]
        mascara = mascara_de_texto(faixa).astype(bool)
        if mascara.size == 0:
            continue
        grupos = _grupos_de_colunas(
            mascara.any(axis=0), LACUNA_ENTRE_GRUPOS_DE_TEXTO
        )
        if len(grupos) >= 2:
            saida.append(grupos)
    return saida


def _borda_votada(cheias: list[list[tuple[int, int]]], k: int) -> tuple[int, int]:
    """A coluna `k` como as linhas a mostram: voto na BORDA DIREITA.

    O VOTO E NA DIREITA, E ISSO FOI MEDIDO, NAO ESCOLHIDO — a razao inteira
    esta na docstring de `sugerir_a_coluna_de_preco`: o numero e alinhado a
    DIREITA, entao a borda esquerda muda com o comprimento e votar nela divide
    os votos entre `100,00` e `3,00`. Com a direita decidida, a esquerda e a
    MENOR entre as linhas que votaram nela — a que cabe o numero mais longo.
    """
    direitas = [linha[k][1] for linha in cheias]
    direita = max(set(direitas), key=lambda v: (direitas.count(v), v))
    esquerda = min(
        linha[k][0] for linha in cheias if linha[k][1] == direita
    )
    return int(esquerda), int(direita)


def sugerir_as_colunas(
    pixels: np.ndarray, grade
) -> dict[str, tuple[int, int, int, int]]:
    """Os retangulos das QUATRO colunas: nome, quantidade, total e unitario.

    Devolve `{}` quando a medicao nao fecha, e ai as janelas abrem VAZIAS. Uma
    sugestao errada e pior que sugestao nenhuma: o usuario aperta ENTER
    confiando nela.

    A GUARDA QUE FAZ ISTO VALER E O CRUZAMENTO DE DUAS MEDICOES INDEPENDENTES.
    O cabecalho diz quantas colunas ha (um grupo claro por rotulo, depois de a
    seta de ordenacao sair pelo corte de brilho); as linhas dizem quantos
    grupos de conteudo ha (o icone, mais um por coluna). Quando os dois numeros
    nao batem, a leitura da grade nao e a que o cabecalho descreve — outro
    layout, um frame cortado, uma janela por cima — e nada e proposto.

    A COLUNA DO NOME E O CASO ESPECIAL, E ELE E MEDIDO. As tres de numero sao
    limitadas pelo proprio conteudo, porque numero e alinhado a DIREITA e a
    coluna acaba onde o numero mais longo acaba. O NOME e alinhado a esquerda e
    varia de comprimento: nesta pagina os dez nomes sao o mesmo
    `Earth Spirit Evolution Stone` e medir por eles daria 263 px. Medido em
    campo, um nome num recorte de 143 px saiu truncado
    (`Common Mafia Leader Lucia`) e com 270 px saiu inteiro — cortar do nosso
    lado e um modo de falha conhecido. Por isso o limite direito do nome e o
    COMECO DO ROTULO `Quantity` no cabecalho: o pixel mais a esquerda que
    aquela coluna chega a desenhar.
    """
    vazio: dict[str, tuple[int, int, int, int]] = {}
    if pixels is None or pixels.size == 0 or grade is None:
        return vazio

    caixa = retangulo_da_banda_do_cabecalho(grade, pixels.shape[:2])
    if caixa is None:
        return vazio
    bx, by, blarg, balt = caixa
    banda = pixels[by : by + balt, bx : bx + blarg]
    corte = medir_o_corte_de_brilho_do_cabecalho(banda)
    if corte is None:
        return vazio
    rotulos = grupos_do_cabecalho(banda, corte)
    if len(rotulos) < 4:
        return vazio

    esperado = len(rotulos) + 1
    cheias = [
        linha for linha in _grupos_claros_por_linha(pixels, grade)
        if len(linha) == esperado
    ]
    if len(cheias) < 2:
        return vazio

    bordas = [_borda_votada(cheias, k) for k in range(esperado)]
    esquerda_da_grade = int(grade.esquerda)
    limite_da_grade = esquerda_da_grade + int(grade.largura)
    topo, altura = int(grade.topo), int(grade.altura)

    inicio_da_quantidade = esquerda_da_grade + rotulos[1][0]
    fim_do_icone = esquerda_da_grade + bordas[0][1]
    if inicio_da_quantidade <= fim_do_icone:
        return vazio

    colunas = {
        "nome": (fim_do_icone, inicio_da_quantidade),
    }
    anterior = inicio_da_quantidade
    for nome, k in (("quantidade", 2), ("total", 3), ("unitario", 4)):
        if k >= esperado:
            return vazio
        _, direita = bordas[k]
        proxima = bordas[k + 1][0] if k + 1 < esperado else int(grade.largura)
        fim = esquerda_da_grade + (direita + proxima) // 2
        fim = min(fim, limite_da_grade)
        if fim <= anterior:
            return vazio
        colunas[nome] = (anterior, fim)
        anterior = fim

    return {
        nome: (inicio, topo, fim - inicio, altura)
        for nome, (inicio, fim) in colunas.items()
    }


def sugerir_a_coluna_do_nome(
    pixels: np.ndarray, grade
) -> tuple[int, int, int, int] | None:
    """O retangulo da COLUNA DO NOME (LEIT-05), ou `None` quando nao da.

    Sai da mesma medicao que as outras tres — `sugerir_as_colunas` — e nao de
    uma passagem propria, porque as quatro sao decididas JUNTAS: a fronteira
    entre o nome e a quantidade e uma so, e mede-la duas vezes em dois lugares
    seria autorizar que as duas discordassem.

    Devolve o retangulo em coordenadas do FRAME, com a altura da grade inteira,
    porque e uma COLUNA e e assim que o olho a confere. O que vai para o
    `calibration.json` e so `{"dx": x - origem_x, "largura": largura}`.
    """
    return sugerir_as_colunas(pixels, grade).get("nome")


def conferir_a_coluna_na_grade(
    nome: str,
    caixa: tuple[int, int, int, int],
    caixa_da_grade: tuple[int, int, int, int],
) -> None:
    """Recusa NA HORA um retangulo de coluna que caiu fora da grade (T-02-02).

    Um `dx` fora da grade nao quebra nada visivel: ele faz a leitura recortar
    OUTRA coluna e devolver um numero plausivel, errado por um fator inteiro.
    Uma serie de precos corrompida assim nao se distingue de uma correta
    olhando para o CSV — e o CSV e o produto.

    Recusar aqui, com o usuario ainda na frente da ferramenta, e o unico momento
    em que ele pode simplesmente remarcar.
    """
    x, _y, largura, _altura = caixa
    gx, _gy, glargura, _galtura = caixa_da_grade
    if largura <= 0:
        raise MercadoNaoCalibravel(
            f"a coluna '{nome}' ficou com largura zero. Remarque o retangulo."
        )
    if x < gx or x + largura > gx + glargura:
        raise MercadoNaoCalibravel(
            f"a coluna '{nome}' vai de x={x} a x={x + largura}, e a area da "
            f"lista vai de x={gx} a x={gx + glargura} — ela caiu FORA da "
            f"grade.\n"
            f"  Uma coluna fora da grade recorta outra coisa e devolve numero "
            f"plausivel, errado por um fator inteiro. Remarque o retangulo "
            f"dentro da lista."
        )


# A ORDEM E A DA TELA, da esquerda para a direita, e a descricao e o que o
# usuario le enquanto o retangulo verde ja esta desenhado.
#
# O UNITARIO ESTA AQUI E NAO E SOBRA. Ele nao vai para o CSV — a Fase 3 guarda
# `Total` e `Quantity`, porque reconstruir o total a partir do unitario devolve
# um numero que nunca existiu (`0,83 x 48 = 39,84` onde a tela diz `40,00`). Ele
# e lido porque e a unica LEITURA INDEPENDENTE do mesmo fato que o `Total`
# afirma, e por isso e a materia-prima da guarda de cruzamento contra o par
# `0`x`8`: margem medida de 0,0370, a mais estreita do sistema, e o unico modo de
# falha que a gramatica do numero nao pega — um `0` lido como `8` mantem a
# gramatica intacta. Apagar esta linha por parecer sobra custaria a guarda.
COLUNAS_A_MARCAR = (
    ("nome", "do NOME do item (depois do icone, sem invadir Quantity)"),
    ("quantidade", "Quantity"),
    ("total", "Total"),
    ("unitario", "Unit price"),
)


def _grade_do_desenho(
    caixa_da_grade: tuple[int, int, int, int],
    caixa_da_primeira_linha: tuple[int, int, int, int],
) -> GradeMedida:
    """A grade como o USUARIO acabou de desenha-la.

    As propostas de coluna saem DESTA e nao de `medir_a_grade`, e a diferenca
    nao e estetica: `conferir_a_coluna_na_grade` recusa o que cair fora do
    retangulo desenhado. Propor a partir da medicao e conferir contra o desenho
    deixaria a ferramenta recusando a propria sugestao quando os dois divergem
    — e divergir e o caso normal, e por isso existe
    `_avisar_divergencia_da_grade`.
    """
    gx, gy, glargura, galtura = caixa_da_grade
    _, _, _, passo = caixa_da_primeira_linha
    passo = max(1, int(passo))
    linhas = max(1, round(galtura / passo))
    return GradeMedida(
        esquerda=int(gx),
        topo=int(gy),
        largura=int(glargura),
        passo=passo,
        linhas=int(linhas),
    )


def _cortar_o_cabecalho(
    pixels: np.ndarray,
    caixa: tuple[int, int, int, int],
    layout: str,
    origem: tuple[int, int],
) -> tuple[dict | None, float | None]:
    """O molde do cabecalho e o limiar proposto para ele. `(None, None)` se nao da.

    O LIMIAR SAI DAQUI PROVISORIO, E ISSO PRECISA ESTAR ESCRITO ONDE ELE NASCE.
    A conferencia abaixo e AUTORREFERENTE: o molde e comparado com o proprio
    frame de onde foi cortado, o que da ~1,0 por construcao e nao prova nada
    sobre casar OUTRO frame. Ela serve so para pegar o erro grosseiro (recorte
    vazio, corte que apagou tudo). A confirmacao de verdade e o portao de
    layout rodando este molde contra bandas de negociacao em duas ordenacoes e
    contra Adena e busca; se ele nao separar la, volta para ca.

    `CASAMENTO_MINIMO_DA_ANCORA` e a PROPOSTA, pelo precedente das ancoras: e o
    unico limiar de casamento ja medido em campo neste projeto.
    """
    x, y, largura, altura = caixa
    banda = pixels[y : y + altura, x : x + largura]
    if banda.size == 0:
        print("\nAVISO: a banda do cabecalho ficou vazia — nada foi cortado.")
        return None, None

    corte = medir_o_corte_de_brilho_do_cabecalho(banda)
    if corte is None:
        print(
            "\nAVISO: nao consegui MEDIR o corte de brilho nesta banda — os "
            "grupos de texto nao se separaram em dois niveis.\n"
            "  O molde do cabecalho NAO foi gravado, e o portao de layout fica "
            "OFF. Tudo o mais desta rodada e gravado normalmente.\n"
            "  Tente um frame com os quatro rotulos de coluna inteiros na "
            "faixa (`Goods`, `Quantity`, `Total`, `Unit price`)."
        )
        return None, None

    molde = sugerir_o_molde_do_cabecalho(banda, layout, y - origem[1], corte)
    if molde is None:
        return None, None

    valor = _valor_da_banda(banda)
    cortada = np.where(valor > corte, valor, 0).astype(np.uint8)
    score = casamento_da_ancora(cortada, cortada)
    rotulos = grupos_do_cabecalho(banda, corte)
    print(
        f"\nCabecalho cortado: corte de brilho MEDIDO em {corte}, "
        f"{len(rotulos)} rotulo(s) de coluna acima dele."
    )
    print(
        f"  Casamento contra o proprio frame: {score:.4f} — este numero e "
        f"AUTORREFERENTE e nao prova nada sobre outro frame."
    )
    return molde, CASAMENTO_MINIMO_DA_ANCORA


def propor_rotulo(
    mascara: np.ndarray,
    faixa: tuple[int, int],
    runs: list[tuple[int, int]],
    moldes: dict[str, np.ndarray],
) -> str | None:
    """A leitura que a ferramenta ARRISCA propor, ou `None` quando nao arrisca.

    Cada run e comparado com os moldes de UM CARACTERE ja gravados, na mesma
    representacao e no mesmo alinhamento da matriz de confusao -- mascara
    binaria e preenchimento ate a maior caixa. Reaproveitar exatamente a
    mecanica da matriz e o que faz o numero significar a mesma coisa dos dois
    lados; medir de um jeito e decidir com o outro seria comparar convencoes.

    TUDO OU NADA, de proposito: basta um run que nao passe no piso E na margem
    para a funcao devolver `None` e o usuario ser perguntado do zero. Uma
    proposta parcial (`6?,00`) convida ao ENTER distraido justamente sobre a
    parte que a ferramenta NAO sabia.

    Isto e uma SUGESTAO, nunca uma gravacao. Quem certifica que o recorte
    rotulado `8` e mesmo um `8` continua sendo o olho humano -- e essa e a razao
    de o portao existir.
    """
    de_um_caractere = {r: m for r, m in moldes.items() if len(r) == 1}
    if not de_um_caractere or not runs:
        return None

    topo, base = faixa
    lido: list[str] = []
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
        if melhor_score < MINIMO_PARA_PROPOR_ROTULO:
            return None
        segundo = pontuados[1][0] if len(pontuados) > 1 else -1.0
        if melhor_score - segundo < MARGEM_MINIMA_PARA_PROPOR:
            return None
        lido.append(melhor_rotulo)
    return "".join(lido)


def _pedir_rotulo(
    ler, quantos_glifos: int, proposta: str | None = None
) -> str | None:
    """Le o numero como o usuario o LE na tela, e confere contra a contagem.

    ESTA CONFERENCIA E O CORACAO DO MODO DE DIGITOS. Ela transforma um erro de
    marcacao -- o retangulo que cortou meio digito, ou que pegou o `X` de
    `XM Coin` junto -- em recusa IMEDIATA, em vez de num molde errado gravado
    com a mesma confianca de um certo. Um `8` cortado pela metade viraria o
    molde oficial do `8`, e todo preco que o contivesse sairia errado, calado.

    COM `proposta`, O USUARIO VIRA REVISOR EM VEZ DE OPERADOR. A ferramenta ja
    leu o numero comparando cada glifo com os que ele mesmo ja certificou (ver
    `propor_rotulo`), e o ENTER vazio confirma. Digitar continua valendo e
    continua vencendo -- a proposta e um rascunho, nunca uma decisao.

    SEM `proposta`, o ENTER vazio segue sendo RECUSA, exatamente como antes.
    Silencio nao pode virar concordancia quando nao ha nada com que concordar --
    e a mesma regra que faz `_selecionar_regiao` so reinterpretar `(0,0,0,0)`
    quando existe sugestao na tela.

    Devolve `None` quando a marcacao deve ser descartada.
    """
    if proposta is None:
        pergunta = "  digite o numero como voce o LE na tela (com a virgula): "
    else:
        pergunta = (
            f"  eu li '{proposta}' -- [ENTER] confirma, "
            f"ou digite o numero certo: "
        )
    rotulo = str(ler(pergunta)).strip()
    if not rotulo and proposta is not None:
        rotulo = proposta

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
    grade=None,
) -> dict[str, np.ndarray]:
    """O laco de marcacao dos glifos. Devolve SO o que foi cortado nesta rodada.

    O usuario CONFERE um numero por vez -- ele nunca marca dez retangulos, um
    por digito. E a mesma economia de erro humano que ja deriva dez linhas de
    uma linha marcada (D-06): marcar dez acumula dez erros, marcar um e derivar
    acumula um.

    COM `grade`, A FERRAMENTA PROPOE E O USUARIO CONFIRMA. `grade` e a
    `GradeMedida` derivada dos pixels; dela sai um retangulo por linha em volta
    do numero da coluna de preco e um em volta da palavra de moeda ao lado
    (`sugerir_a_coluna_de_preco`). Cada `_marcar` abre com o retangulo ja
    desenhado e o ENTER aceita. Medido: 10 de 10 linhas em `frame_000012` e 6 de
    6 em `frame_000010` -- as quatro linhas cobertas pela tooltip caem fora
    sozinhas, sem regra especial. As contagens de glifo saem 5,5,5,5,5,5,5,5,5,5
    e 6,4,5,4,5,4, batendo caractere a caractere com os precos que estao na tela.

    Sem `grade` -- ou quando a medicao nao fecha -- o laco e EXATAMENTE o de
    antes: `_marcar` sem sugestao, prosa e arrasto. Nenhum caminho foi removido.

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
    numeros_propostos, sufixos_propostos = sugerir_a_coluna_de_preco(pixels, grade)

    print("")
    print("  " + "-" * 58)
    print("  CORTE DOS GLIFOS DE PRECO")
    print("")
    if numeros_propostos:
        print(f"  ACHEI {len(numeros_propostos)} numero(s) na coluna de preco e")
        print("  vou DESENHAR um por vez. Confira e tecle ENTER para aceitar;")
        print("  qualquer outra tecla deixa voce arrastar o retangulo a mao.")
        print("")
        print("  Depois diga que numero e esse. Quando eu conseguir le-lo pelos")
        print("  glifos que voce ja certificou, eu proponho a leitura e o ENTER")
        print("  confirma -- mas o que voce digitar sempre vence.")
    else:
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
            # A fila de propostas e consumida em ordem; esgotada, o caminho
            # volta a ser o arrasto descrito em prosa, sem sugestao.
            proposto = numeros_propostos.pop(0) if numeros_propostos else None
            x, y, larg, alt = _marcar(
                pixels,
                "Numero da coluna de preco",
                (
                    "Confira o numero desenhado na coluna de preco."
                    if proposto
                    else "Marque UM numero da coluna de preco (sem o sufixo) e tecle ENTER."
                ),
                proposto,
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
            mascara = (mascara_de_texto(recorte) * 255).astype(np.uint8)
            # A leitura proposta usa os glifos JA CERTIFICADOS -- os da
            # calibracao anterior mais os desta rodada. Na primeira volta nao ha
            # nenhum e a proposta e `None`, que e como deve ser: nao da para
            # propor uma leitura sem ter visto um digito antes.
            proposta = propor_rotulo(
                mascara, faixa, runs, {**ja_gravados, **cortados}
            )
            rotulo = _pedir_rotulo(ler, len(runs), proposta)
            if rotulo is None:
                continue

            topo, base = faixa
            for caractere, (inicio, fim) in zip(rotulo, runs):
                cortados[caractere] = mascara[topo:base, inicio:fim].copy()
            print(f"  ok: {rotulo}")
            continue

        if escolha in ("x", "a", "xm", "adena"):
            # A ferramenta PERGUNTA qual palavra esta sendo marcada em vez de
            # deduzir: deduzir erraria calado, e um `Adena` gravado como
            # `XM Coin` inverteria a convencao da virgula em toda leitura.
            palavra = "XM Coin" if escolha in ("x", "xm") else "Adena"
            sufixo_proposto = (
                sufixos_propostos.pop(0) if sufixos_propostos else None
            )
            x, y, larg, alt = _marcar(
                pixels,
                f"Palavra: {palavra}",
                (
                    f"Confira o retangulo desenhado: e a palavra '{palavra}'?"
                    if sufixo_proposto
                    else f"Marque a palavra '{palavra}' INTEIRA e tecle ENTER."
                ),
                sufixo_proposto,
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
    ancoras_anteriores: list[AncoraDoPainel] | None = None,
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

    # A GRADE E MEDIDA DE NOVO AQUI, E ISSO NAO CONTRADIZ O "NAO SAO TOCADAS".
    #
    # Nada dela e gravado -- ela existe so para a ferramenta saber ONDE
    # desenhar os retangulos de preco NESTE frame, que e outro frame, com o
    # painel em outra posicao (medido: `frame_000010` tem o titulo em
    # (1015, 212) contra (1176, 362) no frame de calibragem). Sem isto, o modo
    # que existe justamente para completar o conjunto de glifos seria o unico
    # sem proposta -- e ele e o que o usuario roda por ultimo, cansado.
    achado = localizar_o_titulo(pixels, ancoras_anteriores or [])
    medida = medir_a_grade(pixels, achado[0]) if achado is not None else None
    if medida is not None:
        print(f"  achei a grade neste frame: {medida.linhas} linhas de "
              f"{medida.passo} px a partir de y={medida.topo}")

    cortados = cortar_glifos(pixels, glifos_anteriores, grade=medida)
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
    # As ancoras da rodada anterior, que sao o que permite PROPOR os retangulos
    # em vez de descreve-los em prosa. Lista vazia e um estado legitimo (a
    # primeira calibracao de mercado da vida) e o fluxo continua pedindo o
    # arrasto -- so sem a sugestao do titulo.
    ancoras_anteriores = ancoras_de_calibracao(cal.mercado_ancoras)

    if getattr(args, "so_digitos", False):
        return _calibrar_so_digitos(args, cal, arquivo, caminho, pixels,
                                    glifos_anteriores, ancoras_anteriores)

    # O PASSO DA WATCHLIST NAO EXISTE MAIS AQUI, E ELE MORREU POR MEDICAO.
    #
    # Ate 2026-08-29 a ferramenta lia `[mercado] watchlist` do `config.toml`
    # neste ponto e pedia um recorte por item, para casar o nome por molde. A
    # quick `260829-rd9` reescreveu LEIT-01: o nome do item passou a ser lido
    # por OCR e agrupado por similaridade contra os nomes ja vistos, e item
    # desconhecido vira serie nova sem o usuario configurar nada. A evidencia e
    # que o OCR do Windows le os NOMES de forma estavel nas gravacoes de campo
    # (e NAO le os numeros -- ele perde a virgula decimal).
    #
    # `mercado_templates_de_nome` e `mercado_limiar_de_template` ficam `None`
    # para sempre, e esta funcao nao os toca. `ler_watchlist` e
    # `matriz_de_confusao` CONTINUAM no arquivo, sem chamador no fluxo
    # principal: elas sao o precedente medido citado por outros textos, e apagar
    # a funcao apagaria a medicao junto.

    altura, largura = pixels.shape[:2]
    print(f"\nCalibrando o mercado sobre {caminho.name} ({largura}x{altura})")
    print("")
    print("  " + "-" * 58)
    print("  VAO ABRIR 10 JANELAS DE SELECAO, uma de cada vez, no CANTO")
    print("  SUPERIOR ESQUERDO do monitor principal.")
    print("")
    print("  Se nao ver a janela, ela pode estar ATRAS deste terminal")
    print("  ou no outro monitor: procure na barra de tarefas pelo")
    print("  nome que aparece abaixo.")
    print("")
    print("  Cada uma abre com o retangulo que eu MEDI ja desenhado em")
    print("  verde. Voce nao precisa interpretar descricao nenhuma:")
    print("")
    print("    ENTER                -> aceita o retangulo desenhado")
    print("    qualquer outra tecla -> deixa voce arrastar o seu")
    print("    ESC                  -> cancela e nada e gravado")
    print("")
    print("  Quando eu nao conseguir medir alguma regiao neste frame, a")
    print("  janela abre vazia e voce arrasta -- como antes.")
    print("  NAO feche no X -- fechar no X cancela e nada e gravado.")
    print("  " + "-" * 58)
    print("Abra o painel do World Exchange no frame antes de marcar as regioes.\n")

    # --- as ancoras ---
    #
    # A FAIXA DE TITULO E PROCURADA ANTES DE PEDIR QUALQUER COISA. Com a
    # calibracao anterior em maos, `localizar_o_titulo` acha o painel por
    # casamento de molde (0.9999 medido no frame de calibragem) e as outras
    # quatro regioes saem da posicao dele. Sem calibracao anterior -- primeira
    # rodada da vida -- nao ha molde e o usuario desenha o titulo; a partir do
    # que ELE desenhou, as outras quatro voltam a ser propostas.
    achado = localizar_o_titulo(pixels, ancoras_anteriores)
    if achado is not None:
        _sugerido, _score, _por = achado
        print(
            f"\nAchei a faixa de titulo em {_sugerido} pela ancora "
            f"'{_por}' (casamento {_score:.4f})."
        )
        print("  As regioes vao aparecer PRE-DESENHADAS. Confira e aceite.")

    caixas: dict[str, tuple[int, int, int, int]] = {}
    caixas["titulo"] = _marcar(
        pixels,
        "Ancora: titulo",
        "Confira a faixa de titulo 'XM Market' (sugerido: 100x28).",
        achado[0] if achado is not None else None,
    )
    origem = (caixas["titulo"][0], caixas["titulo"][1])

    sugestoes_de_ancora = sugerir_as_ancoras(
        pixels.shape[:2], origem, ancoras_anteriores
    )
    for nome, _dx, _dy, larg, alt, descricao in ANCORAS_SUGERIDAS:
        if nome == "titulo":
            continue
        caixas[nome] = _marcar(
            pixels,
            f"Ancora: {nome}",
            f"Confira {descricao} (sugerido: {larg}x{alt}).",
            sugestoes_de_ancora.get(nome),
        )
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
    medida = medir_a_grade(pixels, caixas["titulo"])
    print("")
    print("  " + "-" * 58)
    print("  A AREA DA LISTA COMECA NA PRIMEIRA LINHA DE DADOS.")
    print("")
    print("  NAO inclua a faixa de cabecalho (`Auction List | Total Price |")
    print("  5 mln increment | Buy`): ela nao e uma linha, e engoli-la desloca")
    print("  todas as 10 linhas para baixo.")
    print("")
    if medida is not None:
        print(f"  MEDI a grade nos pixels: {medida.linhas} linhas de "
              f"{medida.passo} px, de y={medida.topo} a "
              f"y={medida.topo + medida.altura}.")
        print("  O cabecalho JA ESTA de fora — a contagem de linhas veio da")
        print("  alternancia do fundo, que comeca na primeira linha de dados.")
    else:
        print("  NAO consegui medir a grade neste frame — marque a mao.")
        print("  Comece no topo da PRIMEIRA linha de dados e termine na base da")
        print("  ultima. De preferencia pare antes da barra de rolagem.")
    print("  " + "-" * 58)
    caixa_grade = _marcar(
        pixels,
        "Grade",
        "Confira a AREA DA LISTA (SEM o cabecalho).",
        medida.retangulo() if medida is not None else None,
    )
    print("")
    print("  Agora SO a primeira linha: a mesma largura, a altura de UMA linha.")
    print("  E dela que sai o passo entre linhas, e dai quantas cabem na pagina.")
    caixa_linha = _marcar(
        pixels,
        "Primeira linha",
        "Confira SO a PRIMEIRA LINHA da lista.",
        medida.retangulo_da_primeira_linha() if medida is not None else None,
    )
    grade = derivar_grade(caixa_grade, caixa_linha, layout, origem)
    _avisar_divergencia_da_grade(medida, caixa_grade, caixa_linha)

    # --- as quatro colunas ---
    #
    # A GRADE MEDIDA PROPOE; O USUARIO CONFIRMA. As propostas saem de
    # `sugerir_as_colunas`, que cruza duas medicoes independentes (os rotulos do
    # cabecalho e o conteudo das linhas). Quando elas nao batem, o dicionario
    # volta vazio, a janela abre sem retangulo e o usuario arrasta o dele.
    grade_desenhada = _grade_do_desenho(caixa_grade, caixa_linha)
    propostas = sugerir_as_colunas(pixels, grade_desenhada)
    print("")
    print("  " + "-" * 58)
    print("  AGORA AS QUATRO COLUNAS, uma de cada vez.")
    print("")
    print("  A do NOME tem de comecar DEPOIS do icone do item e terminar")
    print("  depois do fim do nome MAIS LONGO da pagina, sem invadir a")
    print("  coluna Quantity. Medido em campo: um nome num recorte de 143 px")
    print("  saiu truncado; com 270 px saiu inteiro. Se o verde parecer")
    print("  curto, arraste mais largo — cortar do nosso lado e um modo de")
    print("  falha conhecido e medido.")
    print("  " + "-" * 58)

    caixas_de_coluna: dict[str, tuple[int, int, int, int]] = {}
    for nome, descricao in COLUNAS_A_MARCAR:
        caixa = _marcar(
            pixels,
            f"Coluna: {nome}",
            f"Confira a coluna {descricao}.",
            propostas.get(nome),
        )
        conferir_a_coluna_na_grade(nome, caixa, caixa_grade)
        caixas_de_coluna[nome] = caixa

    # --- a banda do cabecalho ---
    #
    # O MOLDE DO CABECALHO E O PORTAO DE LAYOUT (D-11), e o corte de brilho que
    # o limpa e MEDIDO nesta banda, nunca herdado de constante. A seta de
    # ordenacao fica DENTRO da celula e ANDA de coluna conforme o usuario
    # ordena: um molde cortado com ela casa uma ordenacao e recusa a outra.
    caixa_cabecalho = _marcar(
        pixels,
        "Cabecalho de coluna",
        "Confira a FAIXA DE CABECALHO (Goods | Quantity | Total | Unit price).",
        retangulo_da_banda_do_cabecalho(grade_desenhada, pixels.shape[:2]),
    )
    cabecalho, limiar_do_cabecalho = _cortar_o_cabecalho(
        pixels, caixa_cabecalho, layout, origem
    )

    # --- os glifos de preco ---
    glifos_cortados = cortar_glifos(pixels, glifos_anteriores, grade=medida)
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
    for nome, caixa in caixas_de_coluna.items():
        regioes[f"coluna_{nome}"] = caixa
    regioes["cabecalho"] = caixa_cabecalho
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

    # AS QUATRO COLUNAS, EM DESLOCAMENTO A PARTIR DA ORIGEM DO PAINEL.
    #
    # Nunca em coordenada absoluta, pela razao ja escrita na docstring de
    # `derivar_grade`: o painel ANDA 827x831 px, e uma coluna gravada em
    # absoluto apontaria para o vazio assim que o usuario arrastasse a janela.
    # O sintoma seria numero plausivel lido da coluna errada.
    ox, oy = origem
    for nome, campo in (
        ("nome", "mercado_coluna_do_nome"),
        ("quantidade", "mercado_coluna_da_quantidade"),
        ("total", "mercado_coluna_do_total"),
        ("unitario", "mercado_coluna_do_unitario"),
    ):
        x, _y, larg, _alt = caixas_de_coluna[nome]
        setattr(cal, campo, {"dx": int(x - ox), "largura": int(larg)})

    # O MOLDE DO CABECALHO SO SUBSTITUI QUANDO HOUVE MOLDE NOVO, no mesmo
    # criterio aditivo do CR-04 logo abaixo: uma rodada em que o corte nao
    # pode ser medido nao apaga o portao de layout de uma rodada anterior.
    if cabecalho is not None:
        cal.mercado_cabecalho_de_coluna = cabecalho
        cal.mercado_limiar_do_cabecalho = limiar_do_cabecalho
    elif cal.mercado_cabecalho_de_coluna:
        print(
            "\nMantido o molde de cabecalho da calibracao anterior — nesta "
            "rodada o corte de brilho nao pode ser medido."
        )

    # OS MOLDES DE NOME NAO SAO MAIS TOCADOS AQUI — NEM PARA ESCREVER, NEM PARA
    # APAGAR —, E A GUARDA DO CR-04 PASSA A VALER POR OMISSAO.
    #
    # O CR-04 consertou o unico caminho do projeto que apagava calibracao sem
    # perguntar: `cal.mercado_templates_de_nome = [...]` era incondicional, e
    # com a watchlist vazia isso regravava o arquivo INTEIRO com uma lista
    # vazia -- os moldes de uma calibracao anterior desapareciam, calados, e
    # cada um deles custou um arrasto de mouse sobre um frame gravado.
    #
    # Agora o passo saiu do fluxo e `cal` chega ate `salvar` com o valor que
    # veio do disco: quem tinha moldes os mantem, quem nao tinha continua com
    # `None`. `mercado_limiar_de_template` segue a mesma sorte e pela mesma
    # razao. O cabecalho deste modulo promete "muta so os campos de mercado" --
    # e nao mutar e a unica forma de nunca destruir.
    if cal.mercado_templates_de_nome:
        print(
            f"\nMantidos os {len(cal.mercado_templates_de_nome)} molde(s) de "
            f"nome da calibracao anterior — desde 2026-08-29 o nome do item e "
            f"lido por OCR e esta ferramenta nao corta mais molde de nome."
        )

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
    for nome, campo in (
        ("nome", "mercado_coluna_do_nome"),
        ("quantidade", "mercado_coluna_da_quantidade"),
        ("total", "mercado_coluna_do_total"),
        ("unitario", "mercado_coluna_do_unitario"),
    ):
        coluna = getattr(cal, campo)
        print(
            f"  coluna {nome:<6}: dx={coluna['dx']}, "
            f"largura={coluna['largura']} px"
        )
    if cal.mercado_cabecalho_de_coluna:
        cab = cal.mercado_cabecalho_de_coluna
        print(
            f"  cabecalho    : {cab['altura']}x{cab['largura']} px, corte de "
            f"brilho {cab['corte_de_brilho']}, layout '{cab['layout']}'"
        )
    else:
        print("  cabecalho    : NAO gravado — o portao de layout fica OFF")
    # O QUE SUBSTITUIU O PASSO DA WATCHLIST, dito onde o usuario procurava a
    # contagem de moldes de nome. Sem esta linha o passo simplesmente some, e
    # a ausencia parece defeito.
    print(
        "  nomes        : lidos por OCR e agrupados por similaridade — nao ha "
        "mais lista para escrever (LEIT-01, ver REQUIREMENTS.md)"
    )
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
        help=(
            "qual dos TRES layouts de coluna esta na tela "
            "(padrao: negociacao — o unico que tem nome de item, e o de ~283 "
            "dos ~308 frames com painel aberto no censo das gravacoes)"
        ),
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
