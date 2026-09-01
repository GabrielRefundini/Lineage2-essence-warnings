"""Desenhar a mascara guardada como uma imagem que um humano LE.

POR QUE ISTO EXISTE, NAS PALAVRAS DO DONO

A pergunta do batismo chega no celular assim:

    Aprendi 3 pessoas que ainda estao sem nome:
      0dcf6f
      15caec
      f19e3c

E a pergunta dele foi "como vou saber qual hash representa qual nome?". Nao ha
resposta boa hoje: ele adivinharia por eliminacao. E a resposta natural NAO e
OCR — e MOSTRAR o recorte, porque o olho dele le exatamente o nick que o OCR
erra. O acervo ja tem tudo de que isto precisa: a mascara de cada entrada esta
em disco desde a Fase 2, inclusive das aprendidas em sessoes passadas. Nenhuma
captura nova, nenhum modelo, nenhuma dependencia.

O DESENHO FOI MEDIDO A MAO ANTES DE VIRAR CODIGO

Em 01/09/2026 as 15 entradas de `.identidades/` foram reconstruidas para PNG e
lidas sem esforco: `Welazkez`, `PIRULITO`, e tambem os lixos (`Show Options`,
um recorte com `Kills: 4 Deaths` por cima). Ou seja, a imagem tambem responde a
pergunta absurda de T-02-07 — o dono VE que aquilo nao e gente e simplesmente
nao responde.

POR QUE `INTER_NEAREST`, E NAO A INTERPOLACAO PADRAO

A mascara e binaria e a fonte do jogo tem 20 px de altura. Qualquer suavizacao
inventa cinza entre dois pixels do jogo, e cinza inventado nessa escala e
exatamente o que transforma um `l` num `I` e um `0` num `O` — o erro que o
recurso inteiro existe para evitar. NEAREST mantem cada pixel gravado como um
quadrado, entao o que o dono ve e o que o scanner guardou, e nao um palpite do
redimensionador.

POR QUE 6x, E NAO OS 3x DA PROVA A MAO

3x (330 px de largura) foi o que se leu confortavelmente NUM MONITOR. O destino
e uma bolha de WhatsApp: ~360 px logicos de largura num celular de densidade
3x, ou seja ~1080 px reais. A 3x o cliente teria de AMPLIAR a imagem, e a
ampliacao dele e suave — jogaria fora justamente a nitidez que o NEAREST
comprou. A 6x a area do nome tem 660 px e a imagem inteira ~760 px, que cabe no
orcamento real da bolha sem o cliente inventar pixel nenhum. Como a ampliacao
continua NEAREST, 6x nao e um palpite novo: e o MESMO desenho de 3x com cada
quadrado duas vezes maior.

MEDIDO: as 15 entradas reais dao PNG de 3.9 KB a 6.4 KB nesta configuracao
(media 4.8 KB). O tamanho nunca foi o problema; a legibilidade era.

POR QUE O APELIDO E DESENHADO DENTRO DA IMAGEM

A legenda tem de viajar JUNTO com os pixels. Depender da ordem em que o cliente
mostra os anexos, ou do nome do arquivo, e depender de uma coisa que o WhatsApp
nao promete — e uma legenda trocada nao produz um erro visivel: produz um
`/batizar` que da o nome de uma pessoa para a assinatura de outra, em silencio.
Essa e a mentira plausivel que este projeto inteiro combate.

O QUE ESTE MODULO NAO CONHECE

Ele fala `numpy`, `cv2` e stdlib, e so. Nao importa `notificador`, nao sabe o
que e Chatwoot e nao tem relogio. `Anexo` mora AQUI, e nao no transporte,
porque quem MONTA um anexo e quem sabe o que ele contem; o transporte so
precisa dos tres campos.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Quantas vezes cada pixel da mascara e repetido. Ver a docstring do modulo:
# 3x foi provado a mao num monitor, 6x e esse mesmo desenho no orcamento de
# pixels reais de uma bolha de WhatsApp.
AMPLIACAO = 6

# A faixa da esquerda, onde o apelido e escrito.
_FONTE = cv2.FONT_HERSHEY_SIMPLEX
_ESCALA = 1.1
_GROSSURA = 2
_FOLGA_DA_FAIXA = 28  # px, somados a largura do texto
# Publicos porque um teste precisa recortar a AREA DO NOME sem incluir a
# moldura, e um teste que chutasse esses numeros deixaria de acusar o dia em
# que eles mudassem.
MARGEM = 8  # px de branco em volta de tudo
MOLDURA = 1  # px de cinza, a borda externa
_TOM_DA_MOLDURA = 120
_TOM_DO_SEPARADOR = 160


@dataclass(frozen=True)
class Anexo:
    """Um arquivo que viaja junto com a mensagem.

    Frozen e com os tres campos NOMEADOS de proposito: uma tupla
    `(nome, bytes)` posicional e a forma mais barata de um dia trocar o
    conteudo de uma pessoa pelo rotulo de outra num `zip` distraido.
    """

    nome_do_arquivo: str
    conteudo: bytes
    tipo: str = "image/png"


def png_do_nome(mascara: np.ndarray, apelido: str) -> bytes:
    """Os bytes de um PNG com o recorte do nome e o apelido ao lado.

    Levanta `ValueError` quando a mascara nao tem area. Levantar aqui e o que
    permite a quem monta a pergunta PULAR a entrada e mandar a pergunta assim
    mesmo: uma pessoa que nunca e perguntada fica anonima para sempre, entao
    nenhuma falha de desenho pode virar uma pergunta que nao sai. Devolver um
    PNG de 0x0 em vez de levantar produziria uma bolha vazia no grupo, que e
    pior — parece uma mensagem normal.
    """
    if mascara is None or mascara.ndim != 2 or mascara.size == 0:
        raise ValueError("mascara sem area: nao ha o que desenhar")

    altura, largura = mascara.shape
    nome = cv2.resize(
        (mascara.astype(np.uint8) * 255),
        (largura * AMPLIACAO, altura * AMPLIACAO),
        interpolation=cv2.INTER_NEAREST,
    )
    # Texto PRETO no BRANCO: a mascara nasce como texto aceso sobre fundo
    # apagado, e no papel (ou numa bolha clara de WhatsApp) o negativo disso e
    # o que o olho le mais rapido.
    nome = 255 - nome

    (largura_do_texto, altura_do_texto), _ = cv2.getTextSize(
        apelido, _FONTE, _ESCALA, _GROSSURA
    )
    largura_da_faixa = largura_do_texto + _FOLGA_DA_FAIXA
    alto = altura * AMPLIACAO
    faixa = np.full((alto, largura_da_faixa), 255, dtype=np.uint8)
    cv2.putText(
        faixa,
        apelido,
        (_FOLGA_DA_FAIXA // 2, (alto + altura_do_texto) // 2),
        _FONTE,
        _ESCALA,
        0,
        _GROSSURA,
        cv2.LINE_AA,
    )

    imagem = np.hstack([faixa, nome])
    # O separador diz onde acaba o rotulo e comeca o que o scanner VIU. Sem
    # ele, o apelido parece parte do nick.
    cv2.line(
        imagem,
        (largura_da_faixa - 1, 0),
        (largura_da_faixa - 1, alto - 1),
        _TOM_DO_SEPARADOR,
        1,
    )
    imagem = cv2.copyMakeBorder(
        imagem, MARGEM, MARGEM, MARGEM, MARGEM,
        cv2.BORDER_CONSTANT, value=255,
    )
    # A moldura existe porque a imagem e quase toda branca: sem ela, sobre o
    # fundo claro do WhatsApp, nao da para ver onde a imagem termina.
    imagem = cv2.copyMakeBorder(
        imagem, MOLDURA, MOLDURA, MOLDURA, MOLDURA,
        cv2.BORDER_CONSTANT, value=_TOM_DA_MOLDURA,
    )

    certo, buffer = cv2.imencode(".png", imagem)
    if not certo:
        raise ValueError("o PNG nao codificou")
    return buffer.tobytes()


def anexo_do_nome(apelido: str, mascara: np.ndarray) -> Anexo:
    """O anexo pronto para o transporte, com o apelido tambem no arquivo.

    O apelido aparece DUAS vezes de proposito: desenhado nos pixels (que e a
    legenda que sobrevive a qualquer cliente) e no nome do arquivo (que e o que
    aparece na pre-visualizacao e no Chatwoot do dono). Redundancia barata num
    lugar onde a confusao custa um batismo errado.
    """
    return Anexo(
        nome_do_arquivo=f"{apelido}.png", conteudo=png_do_nome(mascara, apelido)
    )
