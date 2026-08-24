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

# Um pixel conta como texto se for claro E dessaturado. O texto da UI e branco
# com contorno escuro; o terreno do jogo e colorido. Sao os dois eixos que
# separam melhor — medido na tela real.
VALOR_MINIMO_DO_TEXTO = 165
SATURACAO_MAXIMA_DO_TEXTO = 70

# Abaixo disto, nao afirmamos quem e. Fica bem acima do melhor caso de nomes
# diferentes (0.454) e bem abaixo do pior caso do mesmo nome (1.000).
LIMIAR_DE_CASAMENTO = 0.75

# Se o segundo melhor chega perto do primeiro, o casamento nao e confiavel.
# Melhor dizer "nao sei" do que apontar o nome errado com confianca.
MARGEM_MINIMA_SOBRE_O_SEGUNDO = 0.12

# Recorte com pouquissimo texto e linha vazia, nao nome
PIXELS_MINIMOS_DE_TEXTO = 12


def mascara_de_texto(bgr: np.ndarray) -> np.ndarray:
    """Marca os pixels que sao texto da UI, descartando o cenario."""
    if bgr.size == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    e_texto = (hsv[:, :, 2] > VALOR_MINIMO_DO_TEXTO) & (
        hsv[:, :, 1] < SATURACAO_MAXIMA_DO_TEXTO
    )
    return e_texto.astype(np.uint8)


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


def _correlacionar(a: np.ndarray, b: np.ndarray) -> float:
    """Quanto duas mascaras se parecem, de -1 a 1."""
    if a.shape != b.shape or a.size == 0:
        return 0.0
    fa, fb = a.astype(np.float32), b.astype(np.float32)
    # mascara toda igual (tudo 0 ou tudo 1) tem desvio zero e quebra a
    # correlacao normalizada; nesse caso so a igualdade exata conta
    if fa.std() < 1e-6 or fb.std() < 1e-6:
        return 1.0 if np.array_equal(a, b) else 0.0
    return float(cv2.matchTemplate(fa, fb, cv2.TM_CCOEFF_NORMED)[0][0])


@dataclass(frozen=True)
class Casamento:
    """Resultado de identificar um recorte de nome."""

    nome: str | None  # None quando nao da para afirmar
    confianca: float
    segundo_melhor: float = 0.0

    @property
    def identificado(self) -> bool:
        return self.nome is not None


def identificar(
    recorte_do_nome: np.ndarray, assinaturas: list[Assinatura]
) -> Casamento:
    """Descobre de quem e este nome, entre os conhecidos.

    Devolve `nome=None` quando nao da para afirmar. Isso e deliberado: o
    rastreador degrada para "Membro N", que e feio mas honesto. Chutar um nome
    seria pior do que nao ter nome nenhum — um alerta com o nome errado manda
    a party socorrer a pessoa errada.
    """
    if not assinaturas:
        return Casamento(nome=None, confianca=0.0)

    mascara = mascara_de_texto(recorte_do_nome)

    # Recorte quase sem texto e linha vazia, nao um nome que falhamos em ler
    if int(mascara.sum()) < PIXELS_MINIMOS_DE_TEXTO:
        return Casamento(nome=None, confianca=0.0)

    pontuacoes = sorted(
        ((_correlacionar(mascara, a.mascara), a.nome) for a in assinaturas),
        reverse=True,
    )

    melhor, nome = pontuacoes[0]
    segundo = pontuacoes[1][0] if len(pontuacoes) > 1 else 0.0

    if melhor < LIMIAR_DE_CASAMENTO:
        return Casamento(nome=None, confianca=melhor, segundo_melhor=segundo)

    # Dois candidatos empatados significam que a assinatura nao discrimina —
    # dizer "nao sei" e mais util do que escolher no desempate.
    if melhor - segundo < MARGEM_MINIMA_SOBRE_O_SEGUNDO:
        return Casamento(nome=None, confianca=melhor, segundo_melhor=segundo)

    return Casamento(nome=nome, confianca=melhor, segundo_melhor=segundo)
