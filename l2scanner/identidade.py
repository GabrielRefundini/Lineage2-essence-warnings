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

# Quanto o casamento pode deslizar horizontalmente. O lider ganha uma COROA
# antes do nome, que empurra o texto para a direita — sem tolerancia, virar
# lider fazia o membro deixar de ser reconhecido.
MARGEM_DE_BUSCA = 24

# Abaixo disto, nao afirmamos quem e. Fica bem acima do melhor caso de nomes
# diferentes (0.454) e bem abaixo do pior caso do mesmo nome (1.000).
LIMIAR_DE_CASAMENTO = 0.75

# Se o segundo melhor chega perto do primeiro, o casamento nao e confiavel.
# Melhor dizer "nao sei" do que apontar o nome errado com confianca.
MARGEM_MINIMA_SOBRE_O_SEGUNDO = 0.12

# Recorte com pouquissimo texto e linha vazia, nao nome
PIXELS_MINIMOS_DE_TEXTO = 12


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
    """Procura o molde dentro do alvo, aceitando deslocamento.

    Deslizar em vez de comparar posicao a posicao e o que faz o reconhecimento
    sobreviver a coroa do lider, que empurra o nome alguns pixels para a
    direita. Sem isso, quem virasse lider deixava de ser reconhecido.
    """
    if alvo.size == 0 or molde.size == 0:
        return 0.0
    if molde.shape[0] > alvo.shape[0] or molde.shape[1] > alvo.shape[1]:
        return 0.0

    fa, fm = alvo.astype(np.float32), molde.astype(np.float32)
    # mascara uniforme (tudo 0 ou tudo 1) tem desvio zero e quebra a correlacao
    if fa.std() < 1e-6 or fm.std() < 1e-6:
        return 0.0
    return float(cv2.matchTemplate(fa, fm, cv2.TM_CCOEFF_NORMED).max())


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
