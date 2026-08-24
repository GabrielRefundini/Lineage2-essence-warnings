"""Quem e cada membro, pela imagem do nome na tela.

O PROBLEMA QUE ISTO RESOLVE

Sem isto, os nomes vem da lista do config POR POSICAO DE LINHA. Se a ordem da
party muda — alguem sai e as linhas compactam, ou o lider reorganiza — os
alertas saem com o nome errado.

Essa e a pior categoria de falha do produto. Nao e ruido: e uma mentira
plausivel. "Korzis morreu" quando quem morreu foi o Kaus manda a party socorrer
a pessoa errada, e ninguem desconfia porque a mensagem parece perfeitamente
normal.

POR QUE COMPARACAO DE IMAGEM E NAO OCR

Os nomes sao um conjunto FECHADO e conhecido, e o cliente renderiza o texto de
forma deterministica — o mesmo nome produz os mesmos pixels toda vez. Entao nao
precisamos *ler* o nome, precisamos *reconhecer* qual dos N conhecidos esta ali.
Isso e classificacao, nao leitura, e e muito mais confiavel.

OCR seria pior em tres frentes: exige instalador de ~100 MB (contra o "clica e
roda" do projeto), um glifo lido errado inventa um membro fantasma entrando e
saindo da party, e nada disso compra precisao que ja nao tenhamos aqui.

O QUE FEZ A COMPARACAO FUNCIONAR

Medido na tela real, entre capturas separadas por 4 segundos (o cenario muda por
tras do texto, que e transparente):

    cinza bruto, recorte largo    : mesmo nome 0.751  outro 0.707  margem 0.045
    mascara de texto, largo       : mesmo nome 0.831  outro 0.793  margem 0.038
    mascara de texto, recorte justo: mesmo nome 1.000 outro 0.454  margem 0.546

Duas coisas viraram o jogo: **recortar justo** (num recorte largo o terreno
domina a correlacao) e **isolar o texto por claro-e-dessaturado** (o texto e
branco, o terreno e colorido).
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Um pixel conta como texto se for CLARO. So isso.
#
# A versao anterior exigia tambem ser dessaturado, o que funcionava ate o
# usuario virar lider da party: o jogo pinta o nome do lider de AMARELO, com
# saturacao 118, e a regra o rejeitava. O membro simplesmente sumia do
# reconhecimento.
#
# Medido na tela real: texto branco V=206 S=5, texto amarelo do lider V=206
# S=118, terreno V=83 S=96. O brilho separa os tres com folga; a saturacao nao
# separa o amarelo do terreno. Entao o brilho e o unico criterio.
VALOR_MINIMO_DO_TEXTO = 180

# PENDENCIA CONHECIDA — a coroa do lider.
#
# O jogo desenha uma coroa antes do nome do lider, o que desloca o texto. Houve
# uma tentativa de tolerar isso deslizando o casamento (`matchTemplate(...).max()`
# sobre uma regiao de busca alargada). Ela foi removida por duas razoes medidas:
#
#   1. Nao funcionava. A busca alargava para a ESQUERDA e a coroa empurra o
#      texto para a DIREITA. O alinhamento necessario estava fora do recorte.
#   2. Custava caro. Em 8 casamentos CORRETOS medidos (duas calibracoes, dois
#      conjuntos de frames) o deslize rendeu +0.000 — eles sempre vencem no
#      alinhamento calibrado. Nos casamentos ERRADOS rendeu ate +0.373,
#      levando o pior errado a 0.586 contra um limiar de 0.75.
#
# O caso que continua sem cobertura e o membro calibrado SEM coroa que depois
# VIRA lider. Quando houver um frame real dessa transicao, a resposta e gravar
# DUAS assinaturas por membro (com e sem coroa) e continuar pontuando no
# alinhamento fixo. Voltar ao `.max()` irrestrito nao e opcao: ele devolve as
# 24 chances extras de falso positivo que produziram o bug do "entra e sai".

# Abaixo disto, nao afirmamos quem e. Fica bem acima do melhor caso de nomes
# diferentes (0.454) e bem abaixo do pior caso do mesmo nome (1.000).
LIMIAR_DE_CASAMENTO = 0.75

# Se o segundo melhor chega perto do primeiro, o casamento nao e confiavel.
# Melhor dizer "nao sei" do que apontar o nome errado com confianca.
MARGEM_MINIMA_SOBRE_O_SEGUNDO = 0.12

# Recorte com pouquissimo texto e linha vazia, nao nome
PIXELS_MINIMOS_DE_TEXTO = 12

# Quantas vezes o recorte pode ter mais pixels claros que a assinatura antes de
# ser considerado CONTAMINADO.
#
# A mascara de texto so tem piso de brilho (V > 180), sem teto. Quando algo
# claro passa na regiao do nome — medido: V mediano 230, S mediano 6, ou seja
# BRANCO, nao terreno colorido — esses pixels entram na mascara e destroem a
# correlacao. Um teto de saturacao nao ajuda: com S<=30 ainda sobravam 200 dos
# 251 pixels. O sinal confiavel e o TAMANHO da mascara.
#
# Medido nas fixtures, recorte / assinatura:
#     limpo         0.82  0.90  0.92  0.98  1.05  1.09
#     contaminado   3.29  4.90
# Nao ha zona cinzenta. 2.0 fica no meio do vazio.
FATOR_MAXIMO_DE_CONTAMINACAO = 2.0


def mascara_de_texto(bgr: np.ndarray) -> np.ndarray:
    """Marca os pixels que sao texto da UI, descartando o cenario.

    So brilho, de proposito: o nome do LIDER da party e amarelo e seria
    rejeitado por qualquer filtro de saturacao que ainda barrasse o terreno.
    """
    if bgr.size == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return (hsv[:, :, 2] > VALOR_MINIMO_DO_TEXTO).astype(np.uint8)


@dataclass(frozen=True)
class Assinatura:
    """A impressao digital visual do nome de um membro."""

    nome: str
    mascara: np.ndarray  # 0/1, do recorte do nome

    @property
    def pixels_de_texto(self) -> int:
        return int(self.mascara.sum())

    def como_dict(self) -> dict:
        """Serializa para o arquivo de calibracao.

        Guardamos a mascara empacotada em bits: e 8x menor que um PNG e nao
        depende de codec nenhum para voltar.
        """
        altura, largura = self.mascara.shape
        empacotado = np.packbits(self.mascara.flatten())
        return {
            "nome": self.nome,
            "altura": int(altura),
            "largura": int(largura),
            "bits": empacotado.tobytes().hex(),
        }

    @classmethod
    def de_dict(cls, dados: dict) -> "Assinatura":
        altura, largura = int(dados["altura"]), int(dados["largura"])
        bytes_ = bytes.fromhex(dados["bits"])
        plano = np.unpackbits(np.frombuffer(bytes_, dtype=np.uint8))
        return cls(
            nome=dados["nome"],
            mascara=plano[: altura * largura].reshape(altura, largura),
        )


def criar_assinatura(nome: str, recorte_do_nome: np.ndarray) -> Assinatura:
    return Assinatura(nome=nome, mascara=mascara_de_texto(recorte_do_nome))


def _correlacionar(alvo: np.ndarray, molde: np.ndarray) -> float:
    """Compara o recorte com o molde NO ALINHAMENTO CALIBRADO.

    Uma posicao so, de proposito. A versao anterior tomava o MAXIMO sobre 25
    deslocamentos horizontais, e cada deslocamento e uma chance independente de
    um nome errado encontrar um alinhamento sortudo e passar do limiar.

    Medido em 60 frames reais e na fixture, alinhado -> maximo deslizante:

        casamentos CORRETOS   0.877 -> 0.877   0.907 -> 0.907   (+0.000, 8 de 8)
        casamentos ERRADOS    0.213 -> 0.586   0.199 -> 0.530   (ate +0.373)

    O deslize nao dava nada a quem estava certo e dava quase quatro decimos a
    quem estava errado. Ele comia metade da margem ate o limiar de 0.75.
    """
    if alvo.size == 0 or molde.size == 0:
        return 0.0
    if molde.shape[0] > alvo.shape[0] or molde.shape[1] > alvo.shape[1]:
        return 0.0

    fa, fm = alvo.astype(np.float32), molde.astype(np.float32)
    # mascara uniforme (tudo 0 ou tudo 1) tem desvio zero e quebra a correlacao
    if fa.std() < 1e-6 or fm.std() < 1e-6:
        return 0.0
    # [0, 0] e o molde na origem do recorte — a posicao que a calibracao gravou.
    return float(cv2.matchTemplate(fa, fm, cv2.TM_CCOEFF_NORMED)[0, 0])


@dataclass(frozen=True)
class Casamento:
    """Resultado de identificar um recorte de nome."""

    nome: str | None  # None quando nao da para afirmar
    confianca: float
    segundo_melhor: float = 0.0

    @property
    def identificado(self) -> bool:
        return self.nome is not None


def _pontuar(
    recorte: np.ndarray, assinaturas: list[Assinatura]
) -> list[float] | None:
    """Pontuacao do recorte contra cada assinatura, na ordem recebida.

    Devolve None quando o recorte nao tem texto suficiente para ser um nome —
    linha vazia, nao um nome que falhamos em ler.
    """
    mascara = mascara_de_texto(recorte)
    pixels = int(mascara.sum())
    if pixels < PIXELS_MINIMOS_DE_TEXTO:
        return None

    pontos: list[float] = []
    for assinatura in assinaturas:
        # Um recorte com MUITO mais pixels claros do que este nome tem nao pode
        # ser este nome — tem outra coisa dentro dele. Zerar o par e melhor do
        # que deixar uma correlacao degradada disputar a linha: e assim que uma
        # assinatura errada ganha um recorte que ninguem deveria ter ganhado.
        #
        # Note que isto NAO tenta salvar o reconhecimento do membro
        # contaminado. Ele fica sem nome nesse frame, o que e a resposta
        # honesta. O que a regra impede e a vaga vazia ser ocupada por outro.
        excedente = (
            assinatura.pixels_de_texto
            and pixels > assinatura.pixels_de_texto * FATOR_MAXIMO_DE_CONTAMINACAO
        )
        pontos.append(
            0.0 if excedente else _correlacionar(mascara, assinatura.mascara)
        )
    return pontos


def identificar_linhas(
    recortes: dict[int, np.ndarray], assinaturas: list[Assinatura]
) -> dict[int, Casamento]:
    """Resolve o frame INTEIRO de uma vez, com UNICIDADE.

    POR QUE NAO DA PARA DECIDIR UMA LINHA POR VEZ

    Decidindo linha a linha, nada impede a mesma assinatura de ganhar duas
    linhas no mesmo frame. Isso nao e teorico: aconteceu 8 vezes em
    logs/scanner.log, e uma delas foi

        17:21:04  KAUS SAIU DA PARTY
        17:21:09  status: Korzis, Korzis, TioMad, J4guar
        17:21:42  KAUS ENTROU NA PARTY

    O Korzis casou tambem na linha do Kaus. Como o rastreador guarda estado por
    IDENTIDADE, o Kaus simplesmente sumiu do conjunto de presentes, e a mentira
    virou um par de alertas. Numa party estavel isso rendeu 52 eventos falsos em
    25 minutos.

    A pessoa em cada linha e uma pessoa DIFERENTE — essa e uma restricao do
    dominio, e restricao de dominio pertence ao algoritmo, nao a um teste que
    torce para nao acontecer.

    COMO RESOLVE

    Guloso pelo melhor par global: pega a maior pontuacao ainda disponivel,
    confirma que ela passa do limiar e tem margem sobre a melhor alternativa que
    AINDA sobrou para aquela linha, e ai consome a linha E a assinatura. Uma
    assinatura consumida nao volta para a mesa.

    Guloso e nao otimo (Hungarian seria), mas com 4 a 8 linhas a diferenca e
    irrelevante e o resultado e explicavel: da para olhar as pontuacoes e dizer
    por que cada linha recebeu o nome que recebeu.
    """
    resultado = {i: Casamento(nome=None, confianca=0.0) for i in recortes}
    if not assinaturas:
        return resultado

    pontos: dict[int, list[float]] = {}
    for indice, recorte in recortes.items():
        p = _pontuar(recorte, assinaturas)
        if p is not None:
            pontos[indice] = p

    linhas_livres = set(pontos)
    assinaturas_livres = set(range(len(assinaturas)))

    while linhas_livres and assinaturas_livres:
        # O melhor par (linha, assinatura) ainda em jogo. O desempate por
        # indice mantem o resultado deterministico: mesmo frame, mesma saida.
        valor, i, j = max(
            (pontos[i][j], -i, -j)
            for i in linhas_livres
            for j in assinaturas_livres
        )
        i, j = -i, -j

        if valor < LIMIAR_DE_CASAMENTO:
            break

        # A margem e medida contra o que AINDA esta disponivel. Se a segunda
        # opcao ja foi consumida por outra linha, ela nao e mais uma duvida.
        outras = [pontos[i][k] for k in assinaturas_livres if k != j]
        segundo = max(outras) if outras else 0.0

        if valor - segundo < MARGEM_MINIMA_SOBRE_O_SEGUNDO:
            # Dois candidatos empatados significam que a assinatura nao
            # discrimina. Dizer "nao sei" e mais util do que escolher no
            # desempate — e a linha sai de jogo sem consumir assinatura nenhuma.
            resultado[i] = Casamento(None, valor, segundo)
            linhas_livres.discard(i)
            continue

        resultado[i] = Casamento(assinaturas[j].nome, valor, segundo)
        linhas_livres.discard(i)
        assinaturas_livres.discard(j)

    # Sobrou linha sem nome: guardamos a melhor pontuacao mesmo assim, porque e
    # ela que aparece no diagnostico quando alguem pergunta "por que nao
    # reconheceu?".
    for i in linhas_livres:
        ordenado = sorted(pontos[i], reverse=True)
        resultado[i] = Casamento(
            None, ordenado[0], ordenado[1] if len(ordenado) > 1 else 0.0
        )

    return resultado


def identificar(
    recorte_do_nome: np.ndarray, assinaturas: list[Assinatura]
) -> Casamento:
    """De quem e este nome? Caso de uma linha so.

    Devolve `nome=None` quando nao da para afirmar. Isso e deliberado: o
    rastreador degrada para "Membro N", que e feio mas honesto. Chutar um nome
    seria pior do que nao ter nome nenhum — um alerta com o nome errado manda
    a party socorrer a pessoa errada.
    """
    return identificar_linhas({0: recorte_do_nome}, assinaturas)[0]
