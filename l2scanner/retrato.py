"""Desenhar a mascara guardada como uma imagem que um humano LE.

POR QUE ISTO EXISTE, NAS PALAVRAS DO DONO

A pergunta do batismo chegava no celular assim:

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

O QUE A VERIFICACAO EM CAMPO DE 01/09/2026 MUDOU AQUI

O primeiro desenho punha o apelido numa FAIXA A ESQUERDA do nome. O envio real
para o grupo do usuario mostrou que o arquivo estava certo e a tela estava
errada: a imagem tinha 836x138 — proporcao ~6:1 — e o WhatsApp CORTA as
laterais no preview da bolha. O apelido estava colado na esquerda e sumiu do
campo de visao. A protecao existia no arquivo e nao existia no olho do dono,
que e o pior tipo de protecao: ela era justamente o cinto de seguranca contra a
legenda se perder.

MEDIDO no mesmo dia: uma imagem de proporcao 1.60:1 NAO sofreu o corte. Por
isso o apelido passou a ser desenhado ACIMA do nome, e a imagem inteira passou
a sair em 3:2 (1.50:1) — do lado seguro do ponto medido, e nao em cima dele.
A largura deixou de crescer com o tamanho do texto do apelido, que era a
propria causa do 6:1.

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

E A AMPLIACAO FOI CONFIRMADA EM CAMPO em 01/09/2026: depois da recompressao do
WhatsApp, o nome saiu NITIDO a 6x com `INTER_NEAREST`. Este e o unico numero
deste modulo que ja passou pelo canal de verdade; nao mexer nele sem repetir o
envio.

POR QUE O APELIDO E DESENHADO DENTRO DA IMAGEM

A legenda tem de viajar JUNTO com os pixels. Depender da ordem em que o cliente
mostra os anexos, ou do nome do arquivo, e depender de uma coisa que o WhatsApp
nao promete — e uma legenda trocada nao produz um erro visivel: produz um
`/batizar` que da o nome de uma pessoa para a assinatura de outra, em silencio.
Essa e a mentira plausivel que este projeto inteiro combate.

E POR QUE ELE VAI ACIMA, E NAO AO LADO

Ao lado, a largura da imagem era `largura_do_nome + largura_do_texto`, e era
essa soma que produzia o 6:1 que o preview cortou. Acima, a largura passa a ser
exatamente a do nome ampliado, e o apelido cresce para OCUPAR essa largura em
vez de disputa-la: ele fica maior do que era, no lugar que o preview mostra
inteiro. O apelido e o que o dono digita em `/batizar <apelido> <nick>`, entao
ele precisa ser legivel SEM abrir a imagem — e agora ele e a coisa mais legivel
que ha nela.

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

# A proporcao (largura / altura) da imagem inteira, moldura incluida.
#
# O NUMERO E MEDIDO, E NAO ESCOLHIDO NO OLHO. Em 01/09/2026, num envio real
# para o grupo do usuario:
#
# - 836x138 (~6.06:1) foi CORTADO nas laterais pelo preview da bolha, e o
#   apelido, que estava colado na esquerda, sumiu da tela;
# - uma imagem de 1.60:1 montada no mesmo dia NAO sofreu o corte.
#
# 1.50 fica do lado SEGURO do unico ponto medido, e nao em cima dele. Ir mais
# alto (mais larga) e caminhar de volta para o desfecho que ja aconteceu; ir
# muito mais baixo so acrescenta branco.
PROPORCAO_DA_BOLHA = 1.5

# A faixa de CIMA, onde o apelido e escrito.
_FONTE = cv2.FONT_HERSHEY_SIMPLEX
# A escala e CALCULADA, e nao constante: o apelido ocupa a largura do nome
# ampliado, menos esta folga de cada lado. Uma escala fixa faria o apelido
# encolher (em termos relativos) toda vez que o recorte do nome fosse mais
# largo — e o apelido e justamente o que precisa ser lido sem abrir a imagem.
_FOLGA_DA_ETIQUETA = 12
# Quantos pixels de traco por unidade de escala. O destino e uma bolha de
# WhatsApp RECOMPRIMIDA: um traco fino e o primeiro a virar cinza no
# reencode, e cinza sobre um `0` e o que o faz parecer um `O`. Dois pixels por
# unidade de escala dao um traco da ordem de 9% da altura da letra, que e o
# peso de uma fonte negrito — o mesmo raciocinio que escolheu `INTER_NEAREST`
# para o nome, aplicado ao rotulo.
_PESO_DO_TRACO = 2
# O piso da faixa do apelido, para o caso degenerado de uma mascara tao alta
# que a proporcao alvo nao deixaria altura nenhuma para ela. Sem o piso, a
# faixa poderia sair com altura zero ou negativa e o apelido simplesmente nao
# seria desenhado — uma legenda que some em silencio.
_ALTURA_MINIMA_DA_ETIQUETA = 40
# Publicos porque um teste precisa recortar a AREA DO NOME sem incluir a
# moldura, e um teste que chutasse esses numeros deixaria de acusar o dia em
# que eles mudassem.
MARGEM = 8  # px de branco em volta de tudo
MOLDURA = 1  # px de cinza, a borda externa
_TOM_DA_MOLDURA = 120
_TOM_DO_SEPARADOR = 160
_ESPESSURA_DO_SEPARADOR = 1


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


def _etiqueta_do_apelido(apelido: str, largura: int, altura: int) -> np.ndarray:
    """A faixa branca com o apelido escrito o maior que couber nela.

    A ESCALA SAI DE UMA MEDICAO, E NAO DE UMA CONSTANTE. `cv2.getTextSize`
    cresce linearmente com `fontScale`, entao medir o texto uma vez na escala
    1.0 da direto o fator que o faz encostar nas duas folgas. A conferencia
    depois e por causa da GROSSURA: o traco engorda o desenho alguns pixels
    alem do que a escala sozinha preve, e um apelido que estourasse a largura
    seria desenhado CORTADO pela propria borda da faixa — a legenda ilegivel
    de novo, agora por dentro.
    """
    faixa = np.full((max(altura, 1), largura), 255, dtype=np.uint8)
    cabe_na_largura = max(largura - 2 * _FOLGA_DA_ETIQUETA, 1)
    cabe_na_altura = max(altura - 2 * _FOLGA_DA_ETIQUETA, 1)

    (largura_a_um, altura_a_um), _ = cv2.getTextSize(apelido, _FONTE, 1.0, 1)
    if largura_a_um <= 0 or altura_a_um <= 0:
        return faixa

    escala = min(cabe_na_largura / largura_a_um, cabe_na_altura / altura_a_um)
    grossura = max(2, round(escala * _PESO_DO_TRACO))
    (largura_do_texto, altura_do_texto), _ = cv2.getTextSize(
        apelido, _FONTE, escala, grossura
    )
    if largura_do_texto > cabe_na_largura:
        escala *= cabe_na_largura / largura_do_texto
        grossura = max(2, round(escala * _PESO_DO_TRACO))
        (largura_do_texto, altura_do_texto), _ = cv2.getTextSize(
            apelido, _FONTE, escala, grossura
        )

    cv2.putText(
        faixa,
        apelido,
        ((largura - largura_do_texto) // 2, (altura + altura_do_texto) // 2),
        _FONTE,
        escala,
        0,
        grossura,
        cv2.LINE_AA,
    )
    return faixa


def _completar_ate_a_proporcao(imagem: np.ndarray, borda: int) -> np.ndarray:
    """Branco ACIMA, ate a imagem inteira ficar em `PROPORCAO_DA_BOLHA`.

    A REDE DE SEGURANCA, e nao o mecanismo principal: quem devia ter acertado a
    proporcao e a altura da faixa do apelido, calculada em `png_do_nome`. Aqui
    fica so o arredondamento e o caso degenerado da mascara alta demais.

    A FOLGA VAI TODA PARA CIMA de proposito. Com ela dividida entre os dois
    lados, a posicao do nome dentro do PNG passaria a depender de uma conta de
    arredondamento, e a unica forma de um teste recortar "a area do nome" seria
    repetir essa conta — ou seja, medir o proprio calculo. Encostado embaixo,
    o nome esta sempre nas ultimas `altura * AMPLIACAO` linhas antes da borda.
    """
    altura, largura = imagem.shape
    altura_alva = round((largura + 2 * borda) / PROPORCAO_DA_BOLHA) - 2 * borda
    if altura_alva > altura:
        return cv2.copyMakeBorder(
            imagem, altura_alva - altura, 0, 0, 0,
            cv2.BORDER_CONSTANT, value=255,
        )
    # Alta demais para a largura que tem: alarga em vez de cortar. Cortar seria
    # comer pixel do jogo para caber num numero.
    largura_alva = round((altura + 2 * borda) * PROPORCAO_DA_BOLHA) - 2 * borda
    if largura_alva > largura:
        sobra = largura_alva - largura
        return cv2.copyMakeBorder(
            imagem, 0, 0, sobra // 2, sobra - sobra // 2,
            cv2.BORDER_CONSTANT, value=255,
        )
    return imagem


def png_do_nome(mascara: np.ndarray, apelido: str) -> bytes:
    """Os bytes de um PNG com o apelido em CIMA e o recorte do nome embaixo.

    Levanta `ValueError` quando a mascara nao tem area. Levantar aqui e o que
    permite a quem monta a pergunta PULAR a entrada e mandar a pergunta assim
    mesmo: uma pessoa que nunca e perguntada fica anonima para sempre, entao
    nenhuma falha de desenho pode virar uma pergunta que nao sai. Devolver um
    PNG de 0x0 em vez de levantar produziria uma bolha vazia no grupo, que e
    pior — parece uma mensagem normal.

    A ORDEM DAS OPERACOES E A PROPRIA GARANTIA DE PROPORCAO: a largura final ja
    esta decidida quando a mascara e ampliada (ela e a do nome, e so), entao a
    altura alvo e conhecida antes de qualquer desenho, e a faixa do apelido
    recebe exatamente a altura que falta. E por isso que a proporcao nao
    depende do tamanho do texto — que era a causa do 6:1 medido em campo.
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

    borda = MARGEM + MOLDURA
    largura_da_imagem = largura * AMPLIACAO
    altura_da_imagem = round((largura_da_imagem + 2 * borda) / PROPORCAO_DA_BOLHA)
    altura_da_etiqueta = max(
        _ALTURA_MINIMA_DA_ETIQUETA,
        altura_da_imagem
        - 2 * borda
        - altura * AMPLIACAO
        - _ESPESSURA_DO_SEPARADOR,
    )

    etiqueta = _etiqueta_do_apelido(
        apelido, largura_da_imagem, altura_da_etiqueta
    )
    # O separador diz onde acaba o rotulo e comeca o que o scanner VIU. Sem
    # ele, o apelido parece parte do nick.
    separador = np.full(
        (_ESPESSURA_DO_SEPARADOR, largura_da_imagem),
        _TOM_DO_SEPARADOR,
        dtype=np.uint8,
    )
    imagem = np.vstack([etiqueta, separador, nome])
    imagem = _completar_ate_a_proporcao(imagem, borda)

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
