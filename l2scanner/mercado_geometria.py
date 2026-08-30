"""Onde ficam as regioes do painel do mercado, MEDIDAS a partir dos pixels.

Este modulo nao abre janela, nao le teclado, nao escreve arquivo e nao pergunta
nada. Ele olha um frame gravado e responde "a grade comeca aqui, tem tantas
linhas de tanto". Quem mostra isso a um humano e quem aceita a correcao dele e
`calibrar_mercado.py`.

POR QUE ELE EXISTE — E O CUSTO MEDIDO QUE O MOTIVOU
---------------------------------------------------
MEDIDO EM CAMPO, 2026-08-29, na primeira vez que uma mao humana tentou a
calibracao de mercado inteira. O relato foi literal: *"esta muito dificil
calibrar isso e e muito facil eu errar na interpretacao do que esta sendo
pedido"*. Cada instrucao em prosa custou uma ida e volta:

    "Marque a faixa de titulo 'XM Market'"   -> so o texto, ou a barra toda?
    "Marque a AREA DA LISTA inteira"         -> o usuario INCLUIU o cabecalho,
                                                e a grade saiu com 11 linhas
                                                contra as 10 medidas do layout
    "Marque a PRIMEIRA LINHA"                -> largura inteira, ou so o preco?
    "Marque UM numero da coluna de preco"    -> com o icone? com o 'XM Coin'?
    "Marque a palavra 'XM Coin' INTEIRA"     -> uma ocorrencia, ou todas?

O diagnostico que importa nao e a ergonomia: e que a ferramenta violava a
disciplina fundadora do projeto. Em todo lugar deste codigo se MEDE em vez de
supor — e o calibrador fazia o contrario: pedia que o humano adivinhasse o que
uma frase queria dizer e aceitava o retangulo resultante calado. O erro das 11
linhas so foi pego porque `derivar_grade` tinha, por acaso, uma expectativa
medida para aquele campo (`LINHAS_ESPERADAS`); os outros quatro retangulos nao
tem guarda nenhuma, e um deles errado teria sido gravado sem uma palavra.

A capacidade ja existia e simplesmente nao era oferecida ao usuario: um agente
localizou a ancora de titulo por casamento de molde a **0.9999** e derivou as
bordas da grade do perfil vertical de intensidade, sem tocar no mouse. Este
modulo e essa capacidade, escrita para ser usada.

O QUE FOI MEDIDO, E ONDE
------------------------
Tudo abaixo em `recordings/20260828-115700-calibragem/frame_000012.png`
(1720x1392, aba Adena, painel limpo):

    ancora de titulo   casamento 0.9999 em (1176, 362), molde de 100x28
    separador do       y=617, valor 100 numa faixa continua de x=744 a x=1702
      cabecalho        (e a borda de cima da tabela; a lista comeca em 618)
    fundo das linhas   alterna 48 / 66 a cada banda, dez vezes
    bordas de banda    618, 663, 706, 753, 796, 843, 886, 933, 976, 1023, 1066
    passo              (1066-618)/10 = 44.8  ->  45 px exatos
    grade              topo 618, 10 linhas de 45 px, base 618+450 = 1068
    fim da alternancia x=1687; a barra de rolagem comeca em 1688 e le 48/48
                       nas duas bandas (nao alterna, por isso cai fora)

O cabecalho `Auction List | Total Price | 5 mln increment | Buy` fica ACIMA de
617 e por construcao nunca entra: a grade comeca na primeira linha de dados.
Era exatamente esse o erro humano de 2026-08-29.

DUAS DIVERGENCIAS HONESTAS em relacao aos numeros que me foram entregues como
alvo de verificacao — as duas medidas, com a evidencia ao lado:

1. `x=1664` foi descrito como "o separador vertical antes da barra de
   rolagem". Ele nao e: 1633 e 1664 leem 92 nas duas bandas porque sao as
   bordas ESQUERDA e DIREITA do botao de carrinho da coluna `Buy`. O fundo
   alternado da linha continua ate 1687, e a barra de rolagem comeca em 1688.
   Cortar em 1664 amputaria a coluna `Buy` da grade. A borda direita medida e
   1688 (exclusiva), e nao 1664.
2. `x=744` reproduz exato, mas por outra evidencia que a esperada: a coluna 744
   le 48 nas DUAS bandas (nao alterna) e so entra porque e o ultimo pixel do
   separador do cabecalho, que vale 77 ali contra 68 da moldura em 743. A
   primeira coluna que alterna de verdade e a 745. Os dois numeros descrevem a
   mesma borda; o que responde "onde a tabela comeca" e a linha do cabecalho,
   nao a alternancia, e e por ela que a borda esquerda e derivada.

O QUE ESTE MODULO NAO FAZ
-------------------------
Nao grava nada e nao decide nada sozinho. Toda medicao daqui vira SUGESTAO
pre-desenhada na janela de selecao; o usuario aceita com ENTER ou redesenha. A
autoridade continua sendo a mao humana — o trabalho da ferramenta e tornar a
resposta certa facil e a errada visivel, nunca recusar a correcao.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .mercado_visao import (
    CASAMENTO_MINIMO_DA_ANCORA,
    AncoraDoPainel,
    _em_tons_de_cinza,
    buscar_ancora,
)

# O degrau minimo, em niveis de cinza, para dois niveis de fundo serem
# DIFERENTES.
#
# MEDIDO: o fundo das linhas alterna entre 48 e 66 — 18 niveis de diferenca.
# O limiar em 8 fica bem abaixo disso e bem acima da variacao DENTRO de uma
# banda, que a mediana por coluna zera (ver `perfil_por_mediana`).
DEGRAU_MINIMO_DE_BANDA = 8

# Quanto o perfil pode variar dentro de UMA banda e ainda ser a mesma banda.
#
# MEDIDO com a mediana por coluna: dentro de uma banda o valor e CONSTANTE
# (48 ou 66 cravados nas 44 linhas). 3 e folga para outra pele de jogo, e fica
# a 15 niveis da diferenca real entre bandas.
TOLERANCIA_DE_NIVEL = 3

# Um trecho de perfil mais curto que isto NAO e uma banda.
#
# ESTE NUMERO SUBSTITUI UMA DETECCAO POR DERIVADA QUE ERA FRAGIL, e a troca foi
# forcada por medicao. A versao anterior marcava borda onde o perfil dava um
# degrau, e colapsava bordas vizinhas ficando com a de MAIOR degrau. Funcionava
# no frame real por coincidencia de magnitudes: ali o separador do cabecalho
# entra com 23 niveis e sai com 52, entao a borda gravada era a de baixo (a
# correta, o topo da primeira linha de dados). Num painel com mais contraste
# acima do separador -- 70 niveis para entrar contra 52 para sair -- a borda
# gravada passava a ser a de CIMA, a cadeia se desalinhava em 1 px e a grade
# saia com NOVE linhas comecando na linha do separador.
#
# A deteccao agora e por TRECHOS DE NIVEL CONSTANTE: uma banda e um trecho
# longo, e a linha de transicao e o separador do cabecalho sao trechos de 1
# linha, que caem fora sozinhos. As bordas sao o INICIO de cada trecho longo
# mais o FIM+1 de cada um -- o fim importa porque a ultima banda da grade e
# seguida por rodape, e sem ela a cadeia perde o decimo elo.
#
# 10 fica bem abaixo do passo minimo aceito (20) e bem acima das transicoes de
# 1 linha que precisam ser descartadas.
LINHAS_MINIMAS_DE_BANDA = 10

# A faixa de passos aceitos para uma linha de lista, em pixels. O passo medido e
# 45; a folga cobre outra resolucao de janela sem admitir "duas linhas de texto
# do chat" como grade.
PASSO_MINIMO_DE_LINHA = 20
PASSO_MAXIMO_DE_LINHA = 120

# Quanto uma borda pode se afastar da posicao prevista pela cadeia e ainda
# contar. MEDIDO: a transicao de claro-para-escuro dispara uma linha antes da de
# escuro-para-claro (a linha do meio vale 52), entao as bordas reais alternam
# +0 / -2 em torno do passo perfeito. 3 cobre isso com uma folga de 1.
TOLERANCIA_DA_CADEIA = 3

# Abaixo disto nao e uma grade, e uma coincidencia. O menor layout medido em
# campo tem 9 linhas (a tela de busca, `LINHAS_ESPERADAS`); 4 e metade disso e
# ainda assim exige quatro bandas igualmente espacadas em fila.
LINHAS_MINIMAS_DA_GRADE = 4

# Quanto um pixel do separador do cabecalho pode se afastar do valor de platô e
# ainda contar como parte da linha.
#
# MEDIDO na linha 617: o platô vale 100 dentro da tabela; a moldura interna do
# painel vale 68 em x=743 e 1704, e o fundo em volta vale 49. A borda da tabela
# em x=744 e x=1702 sai suavizada (77 e 95). Uma tolerancia de 25 aceita 75..125
# — pega as duas bordas suavizadas e rejeita a moldura de 68 por 7 niveis.
TOLERANCIA_DO_SEPARADOR = 25


@dataclass(frozen=True)
class GradeMedida:
    """A grade como os pixels a mostram. Tudo em coordenadas do frame."""

    esquerda: int
    topo: int
    largura: int
    passo: int
    linhas: int

    @property
    def altura(self) -> int:
        """Multiplo EXATO do passo, de proposito.

        `derivar_grade` conta linhas com `altura // altura_da_linha`. Propor uma
        altura que nao seja multiplo do passo faria a propria ferramenta
        entregar uma grade que a sua propria conferencia arredondaria — e o
        arredondamento e justamente onde o erro das 11 linhas se escondeu.
        """
        return self.passo * self.linhas

    def retangulo(self) -> tuple[int, int, int, int]:
        return self.esquerda, self.topo, self.largura, self.altura

    def retangulo_da_primeira_linha(self) -> tuple[int, int, int, int]:
        return self.esquerda, self.topo, self.largura, self.passo

    def linha(self, indice: int) -> tuple[int, int, int, int]:
        """O retangulo da linha `indice` (0 = a primeira)."""
        return (
            self.esquerda,
            self.topo + indice * self.passo,
            self.largura,
            self.passo,
        )


def perfil_por_mediana(
    cinza: np.ndarray, coluna_inicial: int, coluna_final: int
) -> np.ndarray:
    """O nivel de fundo de cada LINHA, imune ao texto que passa por cima.

    MEDIANA e nao media, e a diferenca e a funcao inteira. O texto da linha
    ocupa poucas colunas e e muito mais claro que o fundo; a media o dilui para
    dentro do perfil e transforma um degrau limpo de 18 niveis numa rampa. A
    mediana simplesmente nao o ve — MEDIDO, o perfil por mediana sobre as 100
    colunas da ancora devolve 48 e 66 cravados, com uma unica linha de
    transicao em 52 ou 53, enquanto o perfil por media oscila 47..79 dentro da
    MESMA banda por causa dos digitos do preco.
    """
    recorte = cinza[:, coluna_inicial:coluna_final]
    if recorte.size == 0:
        return np.zeros(cinza.shape[0], dtype=np.float64)
    return np.median(recorte.astype(np.float64), axis=1)


def trechos_de_nivel(
    perfil: np.ndarray, primeira_linha: int, ultima_linha: int
) -> list[tuple[int, int]]:
    """Os trechos `[inicio, fim)` em que o perfil fica no MESMO nivel.

    A banda de uma linha da lista e um trecho longo e chapado; a linha de
    transicao entre duas bandas e o separador do cabecalho sao trechos de UMA
    linha. Separar por trecho, e nao por derivada, e o que torna a deteccao
    indiferente a QUAL lado do separador tem mais contraste -- que era a
    fragilidade da versao anterior (ver `LINHAS_MINIMAS_DE_BANDA`).
    """
    inicio = max(0, int(primeira_linha))
    fim = min(int(ultima_linha), int(perfil.size))
    if fim <= inicio:
        return []

    trechos: list[tuple[int, int]] = []
    comeco = inicio
    nivel = float(perfil[inicio])
    for y in range(inicio + 1, fim):
        if abs(float(perfil[y]) - nivel) > TOLERANCIA_DE_NIVEL:
            trechos.append((comeco, y))
            comeco, nivel = y, float(perfil[y])
    trechos.append((comeco, fim))
    return trechos


def bordas_de_banda(
    perfil: np.ndarray, primeira_linha: int, ultima_linha: int
) -> list[int]:
    """As linhas onde uma BANDA comeca ou termina, sem as de transicao.

    Devolve o inicio de cada trecho longo E o fim+1 de cada um. O fim nao e
    redundante: a ultima banda da grade e seguida pelo rodape do painel, que
    tem outro nivel e outro comprimento -- sem o fim+1 dela a cadeia periodica
    fica com dez elos em vez de onze e a grade sai com NOVE linhas.
    """
    bordas: set[int] = set()
    for comeco, fim in trechos_de_nivel(perfil, primeira_linha, ultima_linha):
        if fim - comeco < LINHAS_MINIMAS_DE_BANDA:
            continue
        bordas.add(comeco)
        bordas.add(fim)
    return sorted(bordas)


def cadeia_periodica(bordas: list[int]) -> list[int]:
    """A maior sequencia de bordas IGUALMENTE ESPACADAS. Lista vazia se nao ha.

    Por que uma cadeia e nao "todas as bordas": acima da lista existem a borda
    do cabecalho, a linha do filtro `All`, a do botao `Refresh` e a moldura do
    painel — todas bordas legitimas do perfil, e nenhuma delas periodica. A
    lista e o UNICO lugar do painel com bandas iguais empilhadas em fila, que e
    a mesma propriedade que `calibrar.agrupar_em_party` usa para achar a party
    window entre as barras coloridas da tela.

    As posicoes previstas saem SEMPRE da primeira borda (`base + k * passo`), e
    nunca da anterior aceita. Encadear a partir da anterior acumularia o jitter
    de +-2 px da linha de transicao e a cadeia se perderia por volta da setima
    banda.

    O EMPATE E DESFEITO PELO ERRO TOTAL, e nao pela ordem de iteracao. A borda
    de cima e a de baixo do separador do cabecalho estao a 1 px uma da outra e
    as duas geram cadeias do mesmo comprimento quando ha poucas bandas; sem
    criterio, vencia a que aparecesse primeiro na lista -- ou seja, a linha do
    separador, deslocando a grade inteira em 1 px. Com bandas o bastante a
    periodicidade ja resolve sozinha (medido: 11 elos contra 5 no frame real),
    mas depender disso e depender de sorte.
    """
    if len(bordas) < 2:
        return []

    ordenadas = sorted(bordas)
    conjunto = np.array(ordenadas)
    melhor: list[int] = []
    melhor_erro = float("inf")

    for i, base in enumerate(ordenadas):
        for candidato in ordenadas[i + 1 :]:
            passo = candidato - base
            if not PASSO_MINIMO_DE_LINHA <= passo <= PASSO_MAXIMO_DE_LINHA:
                continue
            cadeia = [base]
            erro = 0.0
            k = 1
            while True:
                alvo = base + k * passo
                distancias = np.abs(conjunto - alvo)
                mais_proxima = int(np.argmin(distancias))
                if distancias[mais_proxima] > TOLERANCIA_DA_CADEIA:
                    break
                cadeia.append(int(conjunto[mais_proxima]))
                erro += float(distancias[mais_proxima])
                k += 1
            if len(cadeia) > len(melhor) or (
                len(cadeia) == len(melhor) and erro < melhor_erro
            ):
                melhor, melhor_erro = cadeia, erro
    return melhor


def extensao_do_separador(
    cinza: np.ndarray, linha: int
) -> tuple[int, int] | None:
    """De onde ate onde vai a linha clara logo acima da grade.

    E ela que responde "onde a TABELA comeca e termina" — nao a alternancia do
    fundo, que a barra de rolagem interrompe. MEDIDO em y=617: valor 100 sem
    interrupcao de x=744 a x=1702, contra 68 da moldura interna do painel e 49
    do fundo em volta.

    O valor de platô sai da MODA da linha inteira, e nao de um limiar fixo: o
    separador e, de longe, a coisa mais repetida numa linha que atravessa a
    tabela toda (958 das 1720 colunas medidas), e a moda o encontra sem que
    ninguem precise saber de antemao quanto vale claro nesta pele de jogo.
    """
    if not 0 <= linha < cinza.shape[0]:
        return None
    valores = cinza[linha, :].astype(np.int32)
    if valores.size == 0:
        return None

    niveis, contagens = np.unique(valores, return_counts=True)
    plato = int(niveis[int(np.argmax(contagens))])

    dentro = np.abs(valores - plato) <= TOLERANCIA_DO_SEPARADOR
    melhor: tuple[int, int] | None = None
    inicio: int | None = None
    for x, ok in enumerate(dentro):
        if ok and inicio is None:
            inicio = x
        elif not ok and inicio is not None:
            if melhor is None or (x - inicio) > (melhor[1] - melhor[0]):
                melhor = (inicio, x)
            inicio = None
    if inicio is not None:
        if melhor is None or (len(dentro) - inicio) > (melhor[1] - melhor[0]):
            melhor = (inicio, int(len(dentro)))
    return melhor


def fim_da_alternancia(
    cinza: np.ndarray,
    bordas: list[int],
    coluna_inicial: int,
    coluna_final: int,
) -> int | None:
    """A ultima coluna +1 em que o fundo ainda ALTERNA entre as bandas.

    E isto que exclui a barra de rolagem sem precisar saber que ela existe: ela
    e desenhada por cima do fundo da lista e nao alterna — MEDIDO, x=1688..1703
    le 48 nas duas bandas, enquanto 745..1687 le 48 numa e 66 na outra.

    A mediana por coluna dentro de cada banda ignora o texto pelo mesmo motivo
    de `perfil_por_mediana`, e ignora tambem o icone e o botao de carrinho, que
    sao opacos mas ocupam uma minoria das linhas da banda... quando ocupam a
    MAIORIA (o icone de moeda cobre quase toda a altura da banda), a coluna
    simplesmente nao alterna e cai fora — por isso a borda ESQUERDA vem do
    separador do cabecalho e nao daqui.
    """
    if len(bordas) < 3:
        return None
    janela = cinza[:, coluna_inicial:coluna_final].astype(np.int32)
    if janela.size == 0:
        return None

    pares: list[list[np.ndarray]] = [[], []]
    for indice in range(len(bordas) - 1):
        topo, base = bordas[indice], bordas[indice + 1]
        # Duas linhas de folga em cada ponta: a linha de transicao entre bandas
        # nao pertence a nenhuma das duas e diluiria as duas medianas.
        if base - topo <= 4:
            continue
        pares[indice % 2].append(janela[topo + 2 : base - 2, :])

    if not pares[0] or not pares[1]:
        return None

    primeira = np.median(np.concatenate(pares[0], axis=0), axis=0)
    segunda = np.median(np.concatenate(pares[1], axis=0), axis=0)
    alterna = np.abs(segunda - primeira) >= DEGRAU_MINIMO_DE_BANDA
    colunas = np.flatnonzero(alterna)
    if colunas.size == 0:
        return None
    return coluna_inicial + int(colunas[-1]) + 1


def nivel_de_fundo_da_linha(
    cinza: np.ndarray, retangulo: tuple[int, int, int, int], folga: int
) -> tuple[int, float] | None:
    """A moda do fundo de um trecho SEM TEXTO da linha, e o quanto ele se suja.

    Devolve `(moda, dispersao)`, onde `dispersao` e a FRACAO de pixels que se
    afastam da moda por mais de `TOLERANCIA_DE_NIVEL`. Sobre fundo limpo ela
    fica no chao; sobre qualquer coisa desenhada por cima ela sobe.

    O LIMIAR DE DECISAO NAO MORA AQUI. Esta funcao MEDE; quem decide "esta linha
    esta coberta, descarte-a" e `mercado_leitura.py`, com o numero vindo do
    `calibration.json` (`mercado_limiar_de_dispersao_do_fundo`), produzido pela
    varredura de `tools/medir_oclusao.py` sobre as 8 gravacoes de campo. Um
    corte escrito aqui seria constante magica no fonte de producao — a coisa que
    este projeto nao faz — e viajaria de layout em layout sem ser remedido.

    POR QUE DISPERSAO, E NAO "A MODA E 48 OU 66"
    --------------------------------------------
    O fundo das linhas alterna entre 48 e 66 (o comentario de
    `DEGRAU_MINIMO_DE_BANDA` registra a medicao), e a tentacao obvia e testar se
    a moda e um desses dois. ELA FALHA, e a refutacao esta medida:

        MEDIDO em `recordings/20260828-061253-mercado-tooltip/frame_000015.png`:
        com a tooltip semitransparente por cima, as linhas 2, 4 e 6 continuam
        lendo moda 48. Um teste de moda aprovaria tres linhas cobertas.

    A tooltip e SEMITRANSPARENTE: ela nao substitui o fundo, ela o mistura — e
    onde a mistura calha de cair perto do valor original a moda sobrevive. O que
    NAO sobrevive e a uniformidade: o fundo limpo e chapado (a mediana por
    coluna le 48 e 66 cravados, ver `perfil_por_mediana`) e o fundo misturado
    nao e. A dispersao mede exatamente isso, e ela e AUTO-REFERENTE: nao precisa
    saber quanto vale o fundo desta pele de jogo, desta resolucao ou deste
    layout. Medido no mesmo frame, no vao sem texto: 0,0024 nas linhas limpas
    contra 0,5157 na linha 0 coberta.

    A FOLGA NAS PONTAS e o mesmo cuidado de `fim_da_alternancia` (:470-472): a
    linha de transicao entre duas bandas nao pertence a nenhuma das duas e
    diluiria a medida. Ela vem por parametro, e nao como constante, porque quem
    a escolheu foi a varredura que produziu a sonda — e ela e gravada junto do
    retangulo, no mesmo objeto (`mercado_sonda_do_fundo`).

    `None` — nunca uma excecao — quando o recorte fica vazio, sai da imagem, ou
    a folga come a linha inteira. O charter deste modulo e reportar: ele nao
    abre janela, nao le teclado, nao escreve arquivo e nao levanta por geometria
    ruim. Quem chama trata `None` como "esta linha nao da para medir", que e uma
    resposta legitima e diferente de "esta linha esta limpa".
    """
    if cinza.size == 0 or cinza.ndim != 2:
        return None

    x, y, largura, altura = (int(v) for v in retangulo)
    folga = int(folga)
    if folga < 0 or largura <= 0 or altura <= 0:
        return None

    altura_da_imagem, largura_da_imagem = cinza.shape[:2]
    if x < 0 or y < 0:
        return None
    if x + largura > largura_da_imagem or y + altura > altura_da_imagem:
        return None

    topo, base = y + folga, y + altura - folga
    if base <= topo:
        return None

    recorte = cinza[topo:base, x : x + largura]
    if recorte.size == 0:
        return None

    valores = recorte.astype(np.int32).ravel()
    niveis, contagens = np.unique(valores, return_counts=True)
    moda = int(niveis[int(np.argmax(contagens))])
    fora = np.abs(valores - moda) > TOLERANCIA_DE_NIVEL
    return moda, float(np.count_nonzero(fora) / valores.size)


def medir_a_grade(
    pixels: np.ndarray, ancora_do_titulo: tuple[int, int, int, int]
) -> GradeMedida | None:
    """A grade inteira, a partir do retangulo da faixa de titulo. `None` se nao da.

    `ancora_do_titulo` e `(x, y, largura, altura)` — venha ele do casamento de
    molde ou do arrasto do usuario, tanto faz. As COLUNAS da ancora servem de
    janela para o perfil vertical porque a faixa de titulo e desenhada
    centralizada no painel e a lista ocupa quase toda a largura dele: as colunas
    do titulo caem dentro da lista por construcao.

    Devolve `None` — e nao um palpite — quando a evidencia nao fecha. Uma
    sugestao errada e pior que sugestao nenhuma: o usuario aperta ENTER
    confiando nela.
    """
    if pixels is None or pixels.size == 0:
        return None
    cinza = _em_tons_de_cinza(pixels)
    altura_do_frame, largura_do_frame = cinza.shape[:2]

    x, y, largura_do_titulo, altura_do_titulo = ancora_do_titulo
    coluna_inicial = max(0, int(x))
    coluna_final = min(largura_do_frame, int(x) + max(1, int(largura_do_titulo)))
    if coluna_final <= coluna_inicial:
        return None

    perfil = perfil_por_mediana(cinza, coluna_inicial, coluna_final)
    primeira_linha = max(1, int(y) + max(0, int(altura_do_titulo)))
    bordas = bordas_de_banda(perfil, primeira_linha, altura_do_frame)
    cadeia = cadeia_periodica(bordas)
    if len(cadeia) - 1 < LINHAS_MINIMAS_DA_GRADE:
        return None

    topo = cadeia[0]
    linhas = len(cadeia) - 1
    passo = int(round((cadeia[-1] - cadeia[0]) / linhas))
    if not PASSO_MINIMO_DE_LINHA <= passo <= PASSO_MAXIMO_DE_LINHA:
        return None
    if topo + passo * linhas > altura_do_frame:
        return None

    faixa = extensao_do_separador(cinza, topo - 1)
    if faixa is None:
        return None
    esquerda, limite = faixa

    direita = fim_da_alternancia(cinza, cadeia, esquerda, limite)
    if direita is None or direita <= esquerda:
        direita = limite
    if direita - esquerda < 2:
        return None

    return GradeMedida(
        esquerda=int(esquerda),
        topo=int(topo),
        largura=int(direita - esquerda),
        passo=int(passo),
        linhas=int(linhas),
    )


def localizar_o_titulo(
    pixels: np.ndarray, ancoras: list[AncoraDoPainel]
) -> tuple[tuple[int, int, int, int], float, str] | None:
    """Onde esta a faixa de titulo, pela ancora que casar MELHOR. `None` se nenhuma.

    Varre TODAS as ancoras conhecidas e fica com a de maior casamento, em vez de
    parar na primeira que passa do limiar como faz `localizar_painel`. A razao e
    a diferenca de proposito: la a pergunta e "o painel esta na tela?" e parar
    cedo economiza os ~45 ms por varredura num laco que roda a cada tick; aqui a
    pergunta e "qual retangulo eu proponho a um humano?", roda uma vez por
    calibracao, e a ancora mais parecida e a que menos chance tem de estar
    coberta por uma tooltip.

    A origem sai com o deslocamento da ancora ja descontado (`buscar_ancora`
    faz isso), entao a faixa de titulo e sempre `(origem, tamanho do molde do
    titulo)` — mesmo quando quem a encontrou foi o botao de fechar do canto
    oposto. E a votacao entre ancoras do 01-04 pagando de novo.
    """
    if pixels is None or pixels.size == 0 or not ancoras:
        return None

    titulo = next((a for a in ancoras if a.nome == "titulo"), None)
    if titulo is None or titulo.molde.size == 0:
        return None

    melhor_score = -1.0
    melhor_origem: tuple[int, int] | None = None
    melhor_nome = ""
    for ancora in ancoras:
        score, ox, oy = buscar_ancora(pixels, ancora)
        if score > melhor_score:
            melhor_score, melhor_origem, melhor_nome = score, (ox, oy), ancora.nome

    if melhor_origem is None or melhor_score < CASAMENTO_MINIMO_DA_ANCORA:
        return None

    ox, oy = melhor_origem
    altura, largura = titulo.molde.shape[:2]
    x = ox + titulo.dx
    y = oy + titulo.dy
    if x < 0 or y < 0:
        return None
    if y + altura > pixels.shape[0] or x + largura > pixels.shape[1]:
        return None
    return (int(x), int(y), int(largura), int(altura)), float(melhor_score), melhor_nome


def ancora_deslocada(
    origem: tuple[int, int],
    deslocamento: tuple[int, int],
    tamanho: tuple[int, int],
    forma_do_frame: tuple[int, int],
) -> tuple[int, int, int, int] | None:
    """`origem + deslocamento`, EMPURRADO para dentro do frame; `None` se nao cabe.

    Um retangulo com coordenada negativa ou que passe da borda e um recorte
    VALIDO em numpy — `janela[-500:, -500:]` devolve o canto oposto da imagem,
    calado (a licao de `mercado_visao._recortar`). Propor esse retangulo a um
    humano que vai apertar ENTER e a forma mais direta de gravar uma ancora que
    aponta para lugar nenhum.

    EMPURRAR, E NAO RECUSAR, E O QUE A MEDICAO PEDIU. Os deslocamentos de
    `ANCORAS_SUGERIDAS` foram medidos com o painel no meio da janela; em
    `frame_000012` ele esta encostado na direita — a moldura dele termina em
    x=1711 num frame de 1720 — e a caixa de 60x60 do `X` de fechar cairia em
    1670..1730, dez pixels alem da borda. Recusar ali deixaria o usuario sem
    sugestao justamente no frame de calibracao. Empurrada para 1660..1720, ela
    contem o `X` inteiro (medido em 1685..1710), que e o que a ancora precisa.

    Empurrar preserva o TAMANHO; cortar mudaria a forma do molde sem avisar. Se
    nem empurrando cabe (retangulo maior que o frame), devolve `None` — nao ha
    sugestao honesta a dar.
    """
    ox, oy = origem
    dx, dy = deslocamento
    largura, altura = int(tamanho[0]), int(tamanho[1])
    altura_do_frame, largura_do_frame = forma_do_frame
    if largura <= 0 or altura <= 0:
        return None
    if largura > largura_do_frame or altura > altura_do_frame:
        return None
    x = min(max(int(ox) + int(dx), 0), largura_do_frame - largura)
    y = min(max(int(oy) + int(dy), 0), altura_do_frame - altura)
    return x, y, largura, altura
