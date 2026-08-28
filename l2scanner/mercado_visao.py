"""Ancora POSITIVA do painel do mercado: de um recorte para "e o painel?".

Esta camada nao tem relogio, nao tem rede, nao abre arquivo e nao decide nada.
Ela so olha os pixels e responde "quanto isto se parece com a faixa de titulo
do painel". Quem decide o que fazer com essa resposta e a camada de cima.

O mesmo charter de `visao.py:1-7`, e pelo mesmo motivo: uma funcao pura de
pixels e testavel contra fixtures em milissegundos, sem jogo aberto.

PROIBICAO HERDADA, e ela e a razao de este modulo existir separado
--------------------------------------------------------------------
Este e um sinal POSITIVO e PROPRIO: "a arte do painel do mercado esta aqui".
JAMAIS estenda `barra_propria_legivel`, `_moldura_da_barra_propria` ou
`_bordas_da_barra_intactas` de `visao.py` para detectar o mercado.

A licao esta MEDIDA em `visao.py:85-111`: promover um sinal a um segundo
consumidor produziu 2 classes de alerta falso e atraso de morte. E o gate de
brilho e um sinal NEGATIVO ambiguo — inventario, ficha e loja leem igual, e
`coberta_0` casa +0.999 COM o painel por cima da barra. Detectar o mercado por
"a barra ficou estranha" e exatamente o caminho que produziu as 27 mortes
falsas deste projeto.

O QUE A MEDICAO DESTA FASE DESCOBRIU
------------------------------------
Medido sobre `recordings/inv3/` (o incidente 27x), buscando o molde na janela
inteira de cada frame de 1720x1392:

    f000   1.0000 @ (912, 350)    painel ABERTO
    f005   0.9996 @ (731, 493)    painel ABERTO, em OUTRA POSICAO
    f010..f040  0.32..0.41        painel FECHADO (o f020 mostra o INVENTARIO)

**O painel ANDA.** Entre f000 e f005 ele se deslocou 181 px para a esquerda e
143 px para baixo, e ainda assim a mesma arte casou 0.9996. Consequencia direta
para quem consumir este modulo: um retangulo fixo gravado na calibracao NAO
encontra o painel numa segunda posicao. O consumidor precisa LOCALIZAR (busca
do molde na faixa, com cadencia limitada — precedente
`SEGUNDOS_ENTRE_BUSCAS_DO_DIALOGO = 5.0` em `captura_janela.py`) e so entao
comparar aqui. Este modulo mede o casamento; achar onde comparar e do chamador.
"""

from __future__ import annotations

import numpy as np


def _em_tons_de_cinza(pixels: np.ndarray) -> np.ndarray:
    """BGR vira cinza; cinza passa direto.

    O consumidor da Fase 4 entrega o recorte como veio do frame, que e BGR.
    Comparar um array de 3 canais com um molde de 1 canal nao levanta erro —
    devolve um numero, e um numero errado calado e o modo de falha que este
    projeto inteiro existe para eliminar.
    """
    if pixels.ndim == 3:
        import cv2

        return cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY)
    return pixels


def casamento_da_ancora(recorte: np.ndarray, molde: np.ndarray) -> float:
    """Compara o recorte com o molde NO ALINHAMENTO DADO. Uma posicao so.

    Copia literal de `identidade._correlacionar`, guards inclusive, e pela mesma
    razao medida la: tomar o MAXIMO sobre deslocamentos da a cada deslocamento
    uma chance independente de um alvo errado achar um alinhamento sortudo.

        casamentos CORRETOS   0.877 -> 0.877   (+0.000, 8 de 8)
        casamentos ERRADOS    0.213 -> 0.586   (ate +0.373)

    Deslizar nao dava nada a quem estava certo e dava quase quatro decimos a
    quem estava errado. Aqui vale igual: quando o chamador ja localizou o
    painel, comparar em UMA posicao e o que preserva a margem.

    Degenerado devolve 0.0 — falha FECHADA. Recorte vazio, molde maior que o
    alvo e desvio ~zero (captura falhando, janela minimizada, retangulo chapado)
    nunca podem virar "mercado aberto".
    """
    import cv2

    if recorte.size == 0 or molde.size == 0:
        return 0.0

    alvo = _em_tons_de_cinza(recorte)
    forma = _em_tons_de_cinza(molde)

    if forma.shape[0] > alvo.shape[0] or forma.shape[1] > alvo.shape[1]:
        return 0.0

    fa, fm = alvo.astype(np.float32), forma.astype(np.float32)
    # recorte uniforme tem desvio zero e quebra a correlacao
    if fa.std() < 1e-6 or fm.std() < 1e-6:
        return 0.0
    # [0, 0] e o molde na origem do recorte — a posicao que o chamador escolheu.
    return float(cv2.matchTemplate(fa, fm, cv2.TM_CCOEFF_NORMED)[0, 0])


# Casamento minimo para um recorte valer como "faixa de titulo do XM Market".
#
# MEDIDO sobre a gravacao do incidente 27x (`recordings/inv3/`, 1720x1392) e
# sobre os frames de janela sem o painel. Os negativos foram cortados na posicao
# de MELHOR casamento de cada frame — o ponto mais parecido com a faixa de
# titulo naquele frame inteiro, que e o numero que um consumidor com busca
# precisa vencer:
#
#     pior POSITIVO   0.9996   (f005, com o painel em posicao deslocada)
#     melhor NEGATIVO 0.4624   (banner de sistema "...on XM Market!", sem painel)
#     MARGEM          0.5372
#
# O limiar fica no MEIO da margem. Nao ha zona cinzenta: os 10 negativos ficam
# entre 0.3253 e 0.4624 e os 2 positivos acima de 0.9996.
#
# O negativo mais caro merece ser lido duas vezes: e o banner "Someone has
# registered an item on XM Market!" no log do jogo — as MESMAS PALAVRAS na tela,
# com o painel FECHADO. Um detector que procurasse o texto dispararia ali. Este
# casa a ARTE do painel, e le 0.4624.
CASAMENTO_MINIMO_DA_ANCORA = 0.73


def mercado_aberto(recorte: np.ndarray, molde: np.ndarray, limiar: float) -> bool:
    """O painel do mercado esta neste recorte?

    O limiar entra por parametro (vem de `calibration.json`) em vez de ser lido
    da constante aqui dentro: a calibracao do usuario e a autoridade sobre a
    tela dele. `CASAMENTO_MINIMO_DA_ANCORA` e o padrao medido, para quem ainda
    nao calibrou o mercado.
    """
    return casamento_da_ancora(recorte, molde) >= limiar


def molde_para_hex(molde: np.ndarray) -> dict:
    """Empacota o molde para dentro do `calibration.json`.

    Padrao `Assinatura.como_dict` (`identidade.py:157-180`), adaptado: la a
    mascara e 0/1 e cabe em `packbits`; aqui sao tons de cinza, entao vao os
    BYTES CRUS em hex, com altura e largura declaradas.

    Nao depende de codec nenhum para voltar — que e a razao inteira de nao
    guardar um PNG. A ancora de 100x28 sai a cerca de 5,6 KB de hex, tamanho
    trivial dentro de um arquivo de calibracao.
    """
    cinza = _em_tons_de_cinza(molde)
    altura, largura = cinza.shape
    return {
        "altura": int(altura),
        "largura": int(largura),
        "bytes": cinza.astype(np.uint8).tobytes().hex(),
    }


def molde_de_hex(dados: dict) -> np.ndarray:
    """Desempacota o molde vindo do `calibration.json`.

    O dict e ENTRADA NAO CONFIAVEL: veio de um arquivo que o usuario pode
    editar e que uma ferramenta futura pode gravar errado. As dimensoes
    declaradas sao conferidas contra o tamanho real dos bytes ANTES de
    reformatar — um `reshape` com dimensao mentida devolveria um molde
    silenciosamente errado, e um molde errado nunca casa com nada: o mercado
    ficaria invisivel sem uma linha de erro.
    """
    altura, largura = int(dados["altura"]), int(dados["largura"])
    brutos = bytes.fromhex(dados["bytes"])
    if len(brutos) != altura * largura:
        raise ValueError(
            f"molde da ancora corrompido: altura {altura} x largura {largura} "
            f"pedem {altura * largura} bytes, mas ha {len(brutos)}. "
            f"Recalibre o mercado."
        )
    plano = np.frombuffer(brutos, dtype=np.uint8)
    return plano.reshape(altura, largura).copy()
