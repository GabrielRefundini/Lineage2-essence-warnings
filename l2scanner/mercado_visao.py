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
143 px para baixo, e ainda assim a mesma arte casou 0.9996.

O QUE O CAMPO DESCOBRIU DEPOIS, E QUE MUDOU O DESENHO (01-04)
-------------------------------------------------------------
As 8 gravacoes de campo (335 frames, `SPIKE-RESPOSTAS.md` secao 8) desmentiram a
arquitetura de UMA ancora — nao o limiar dela:

    pior POSITIVO de campo   0.4110   painel ABERTO, tooltip por cima do titulo
    melhor NEGATIVO de campo 0.4753   painel FECHADO, sessao mercado-fechado
    MARGEM DE CAMPO         -0.0643

A margem e NEGATIVA: um frame com o painel aberto marca MENOS que um frame com
o painel fechado. Nenhum limiar sobre a faixa de titulo separa as duas classes.
A causa nao e o valor 0.73 — e depender de UM retangulo. A tooltip do jogo e
desenhada onde o cursor estiver, **inclusive sobre a faixa de titulo**, e foi
exatamente ali que ela caiu em 20 frames de painel aberto.

O painel tambem percorre 827 x 831 px numa janela de 1720 x 1392 (34 posicoes
distintas), o que descarta tanto o retangulo fixo quanto a busca em faixa: a
faixa que cobrisse esse alcance E a janela.

DESENHO ATUAL — ADQUIRIR, SEGUIR, VOTAR (validado pelo usuario em 2026-08-28)
-----------------------------------------------------------------------------
1. **Aquisicao** (`localizar_painel`, ~45 ms por ancora): varredura da janela
   inteira. So quando nao se sabe onde o painel esta — primeiro tick com o
   mercado aberto, ou depois de uma perda.
2. **Seguimento** (`conferir_painel`, microssegundos): confere as ancoras na
   posicao ja conhecida. Barato porque compara em UMA posicao.
3. **Reaquisicao** (`RastreioDoPainel`): so depois de `TICKS_ATE_REAQUISICAO`
   ticks seguidos perdidos, o que na pratica significa "o usuario arrastou o
   painel" ou "fechou". O usuario confirmou que **o painel reabre onde foi
   fechado**: a posicao e estavel dentro da sessao, e so muda por arrasto
   deliberado. E isso que torna o seguimento o caso comum e a varredura rara.
4. **Votacao pelo MAXIMO** entre ancoras independentes e espalhadas. Uma
   tooltip e um retangulo LOCAL perto do cursor; ela cobre uma ancora, e cobrir
   todas ao mesmo tempo e implausivel.

O limiar de 0.73 continua valido — agora POR ANCORA. Ver
`CASAMENTO_MINIMO_DA_ANCORA`.

A MITIGACAO QUE FOI RECUSADA: o usuario se ofereceu para nao passar o mouse no
meio da lista, mantendo a tooltip longe do titulo. Aceito como REDUCAO DE
RUIDO; recusado como mecanismo de correcao. Este projeto nao troca falha-fechada
por disciplina do usuario — um dia ele esquece, e o modo de falha volta calado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

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
#
# REMEDIDO NO CAMPO (01-04), com as 8 gravacoes do usuario mais os 9 frames de
# janela do incidente 27x. O numero NAO mudou; o que mudou foi o que ele
# significa — ele agora vale POR ANCORA, e a decisao sai da votacao entre elas:
#
#     pior POSITIVO   0.9037   (tooltip cobrindo o titulo; quem salva e o
#                               botao de fechar, no canto oposto)
#     melhor NEGATIVO 0.5337   (adversarial: melhor posicao de CADA ancora em
#                               cada frame sem painel, sobre 91 frames fechados)
#     MARGEM          0.3700
#
# Com a faixa de titulo SOZINHA os mesmos frames dao margem -0.0643. O limiar
# nao estava errado; a arquitetura estava.
CASAMENTO_MINIMO_DA_ANCORA = 0.73

# Cadencia da varredura OCIOSA: quando nao se sabe onde o painel esta, quantos
# ticks esperar entre uma tentativa e a proxima. Precedente direto:
# `SEGUNDOS_ENTRE_BUSCAS_DO_DIALOGO = 5.0` em `captura_janela.py:38-43`, onde
# uma busca na janela inteira tambem custa caro demais para rodar a cada volta.
#
# Contada em TICKS e nao em segundos de proposito: este modulo nao tem relogio
# (ver o charter no topo).
#
# ELA NAO SE APLICA A PERDA DO SEGUIMENTO, e essa distincao foi MEDIDA. A
# primeira versao esperava tres ticks tambem depois de perder a posicao, e o
# replay das gravacoes reais mostrou o preco: na sessao `alvo-sobreposto`, em
# que o usuario arrasta o painel o tempo todo, o rastreio deu 20 de 33 frames
# abertos, e no replay do incidente 27x o `f005` — painel aberto, 181 px a
# esquerda — foi dado como FECHADO. Perder a posicao e a evidencia mais forte
# que existe de que o painel se MEXEU, e adiar a busca justamente ai troca
# precisao por uma economia que nao acontece: um arrasto e um evento raro.
#
# O que a cadencia protege e o caso comum e caro: o mercado fica FECHADO a maior
# parte do tempo, e ali as tres varreduras (~135 ms) sairiam a cada volta do
# laco.
TICKS_ENTRE_VARREDURAS_OCIOSAS = 3


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


def molde_de_hex(
    dados: dict, forma_esperada: tuple[int, int] | None = None
) -> np.ndarray:
    """Desempacota o molde vindo do `calibration.json`.

    O dict e ENTRADA NAO CONFIAVEL: veio de um arquivo que o usuario pode
    editar e que uma ferramenta futura pode gravar errado. As dimensoes
    declaradas sao conferidas contra o tamanho real dos bytes ANTES de
    reformatar — um `reshape` com dimensao mentida devolveria um molde
    silenciosamente errado, e um molde errado nunca casa com nada: o mercado
    ficaria invisivel sem uma linha de erro.

    `forma_esperada` e `(altura, largura)` do retangulo de onde o molde foi
    cortado — `Calibracao.mercado_ancora`. **Passe sempre que tiver.** Sem ela
    a conferencia de bytes e ambigua por construcao: `altura * largura` bate em
    TODA fatoracao do mesmo produto, entao um 100x28 declarado como 28x100
    passa e devolve um molde transposto. Ver o comentario abaixo.
    """
    altura, largura = int(dados["altura"]), int(dados["largura"])
    # Antes do `reshape`: `(-100, -28)` tem produto 2800, passa na conferencia
    # de bytes, e so quebra la dentro com "can only specify one unknown
    # dimension" — uma mensagem que nao ajuda ninguem a recalibrar.
    if altura <= 0 or largura <= 0:
        raise ValueError(
            f"molde da ancora com dimensao nao-positiva ({altura}x{largura}). "
            f"Recalibre o mercado."
        )

    brutos = bytes.fromhex(dados["bytes"])
    if len(brutos) != altura * largura:
        raise ValueError(
            f"molde da ancora corrompido: altura {altura} x largura {largura} "
            f"pedem {altura * largura} bytes, mas ha {len(brutos)}. "
            f"Recalibre o mercado."
        )

    if forma_esperada is not None and (altura, largura) != tuple(forma_esperada):
        # O produto bate em toda fatoracao: 28x100 e 100x28 pedem os mesmos
        # 2800 bytes. Um molde transposto sobrevive ao `reshape`, bate no guard
        # `forma.shape[0] > alvo.shape[0]` de `casamento_da_ancora` e devolve
        # 0.0 para todo frame, para sempre. O mercado sumiria sem uma linha de
        # erro — exatamente o desfecho que a conferencia acima existe para
        # impedir, e que ela sozinha nao impedia.
        raise ValueError(
            f"molde da ancora {altura}x{largura} nao bate com o retangulo "
            f"calibrado {forma_esperada[0]}x{forma_esperada[1]} — parece "
            f"transposto ou cortado de outra regiao. Recalibre o mercado."
        )

    plano = np.frombuffer(brutos, dtype=np.uint8)
    return plano.reshape(altura, largura).copy()


# --------------------------------------------------------------------------
# Multi-ancora: adquirir, seguir, votar
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class AncoraDoPainel:
    """Um pedaco de arte OPACA do painel, e onde ele fica em relacao a origem.

    A ORIGEM do painel, aqui e em toda a calibracao, e o canto superior esquerdo
    da FAIXA DE TITULO — a mesma referencia que o 01-02 gravou em
    `Calibracao.mercado_ancora`. `dx`/`dy` sao deslocamentos a partir dela, e e
    isso que permite mover todas as ancoras juntas quando o painel anda.

    Deslocamentos MEDIDOS no material de campo (janela 1720x1392), para quem
    for calibrar do zero:

        titulo          (   0,    0)  100x28   faixa de titulo "XM Market"
        botao_fechar    ( 494,  -10)   60x60   o "X" do canto superior direito
        canto_inf_dir   ( 494,  665)   60x60   seta de rolagem, canto de baixo

    DUAS ANCORAS FORAM MEDIDAS E DESCARTADAS: o canto superior esquerdo e o
    canto inferior esquerdo do painel sao arte CHAPADA (cinza sobre cinza, sem
    detalhe). Numa varredura da janela inteira sobre frames com o painel
    FECHADO eles casaram 0.8050 e 0.6881 — contra grama. Uma ancora sem textura
    encontra o painel em qualquer lugar, inclusive onde ele nao esta.
    """

    nome: str
    dx: int
    dy: int
    molde: np.ndarray


@dataclass(frozen=True)
class VotoDoPainel:
    """O que as ancoras responderam neste frame.

    `por_ancora` traz so quem PODE ser conferido. Quem caiu fora da janela vai
    para `abstiveram` em vez de entrar com 0.0: 0.0 seria uma leitura inventada
    sobre pixels que nao existem, e o log precisa distinguir "essa ancora nao
    casou" de "essa ancora nao estava na tela".
    """

    aberto: bool
    melhor: float
    origem: tuple[int, int] | None = None
    por_ancora: dict[str, float] = field(default_factory=dict)
    abstiveram: tuple[str, ...] = ()


def _recortar(
    janela: np.ndarray, x: int, y: int, largura: int, altura: int
) -> np.ndarray | None:
    """Recorta, ou devolve None se o retangulo nao cabe INTEIRO na janela.

    A checagem de negativo nao e zelo: `janela[-500:, -500:]` e um recorte
    VALIDO em numpy e devolve o canto oposto da imagem, calado. Um painel
    arrastado para perto da borda produz exatamente essa coordenada, e o
    detector passaria a comparar a ancora com um pedaco aleatorio da tela.
    """
    if x < 0 or y < 0:
        return None
    if y + altura > janela.shape[0] or x + largura > janela.shape[1]:
        return None
    return janela[y : y + altura, x : x + largura]


def buscar_ancora(
    janela: np.ndarray, ancora: AncoraDoPainel
) -> tuple[float, int, int]:
    """Procura a ancora na JANELA INTEIRA. Devolve (casamento, origem_x, origem_y).

    CARA: ~45 ms por chamada numa janela de 1720x1392. Nao rode a cada tick —
    e para isso que existe `RastreioDoPainel`.

    A posicao devolvida ja e a ORIGEM DO PAINEL (o canto da faixa de titulo),
    com o deslocamento da ancora descontado. Devolver a posicao do molde faria
    cada chamador refazer a mesma subtracao, e um deles a faria com o sinal
    trocado.
    """
    import cv2

    if janela.size == 0 or ancora.molde.size == 0:
        return 0.0, 0, 0

    alvo = _em_tons_de_cinza(janela)
    forma = _em_tons_de_cinza(ancora.molde)
    if forma.shape[0] > alvo.shape[0] or forma.shape[1] > alvo.shape[1]:
        return 0.0, 0, 0

    fa, fm = alvo.astype(np.float32), forma.astype(np.float32)
    if fa.std() < 1e-6 or fm.std() < 1e-6:
        return 0.0, 0, 0

    mapa = cv2.matchTemplate(fa, fm, cv2.TM_CCOEFF_NORMED)
    _, maximo, _, posicao = cv2.minMaxLoc(mapa)
    return float(maximo), int(posicao[0]) - ancora.dx, int(posicao[1]) - ancora.dy


def localizar_painel(
    janela: np.ndarray,
    ancoras: list[AncoraDoPainel],
    limiar: float,
    _buscar: Callable[[np.ndarray, AncoraDoPainel], tuple[float, int, int]] = (
        buscar_ancora
    ),
) -> tuple[int, int] | None:
    """AQUISICAO: onde esta o painel? None = nao esta na tela.

    Varre com cada ancora na ordem dada e **para na primeira que passa do
    limiar**. Parar cedo nao e otimizacao prematura: cada varredura custa ~45 ms
    e o caso comum — painel visivel, titulo limpo — resolve na primeira.

    A ordem importa, portanto, e a ordem certa e "a mais confiavel primeiro".
    As ancoras seguintes existem para o caso em que a primeira esta coberta: foi
    assim que 20 frames de painel aberto, com a tooltip apagando o titulo,
    voltaram a ser encontrados.
    """
    for ancora in ancoras:
        casamento, x, y = _buscar(janela, ancora)
        if casamento >= limiar:
            return x, y
    return None


def conferir_painel(
    janela: np.ndarray,
    origem: tuple[int, int],
    ancoras: list[AncoraDoPainel],
    limiar: float,
) -> VotoDoPainel:
    """SEGUIMENTO: o painel ainda esta na posicao conhecida?

    Compara cada ancora em UMA posicao — a origem mais o deslocamento dela. E o
    mesmo alinhamento unico de `casamento_da_ancora`, e pela mesma razao medida:
    deslizar nao ajuda quem esta certo e ajuda quem esta errado.

    O veredito e o MAXIMO, e nao a media nem o consenso. O ruido esperado aqui e
    LOCAL: a tooltip cobre um pedaco do painel, perto do cursor. Media puniria o
    frame inteiro por uma ancora coberta; consenso exigiria que a coberta
    concordasse. O preco do maximo — cada ancora e uma chance independente de um
    alvo errado achar alinhamento sortudo — esta pago em medicao: 0.5337 e o
    melhor que qualquer das tres ancoras conseguiu em 91 frames sem painel.
    """
    ox, oy = origem
    por_ancora: dict[str, float] = {}
    abstiveram: list[str] = []

    for ancora in ancoras:
        altura, largura = _em_tons_de_cinza(ancora.molde).shape
        recorte = _recortar(janela, ox + ancora.dx, oy + ancora.dy, largura, altura)
        if recorte is None:
            abstiveram.append(ancora.nome)
            continue
        por_ancora[ancora.nome] = casamento_da_ancora(recorte, ancora.molde)

    melhor = max(por_ancora.values(), default=0.0)
    return VotoDoPainel(
        aberto=bool(por_ancora) and melhor >= limiar,
        melhor=melhor,
        origem=origem,
        por_ancora=por_ancora,
        abstiveram=tuple(abstiveram),
    )


class RastreioDoPainel:
    """Adquire, segue barato, e volta a procurar no instante em que perde.

    O motivo de seguir em vez de varrer esta medido: a varredura custa ~45 ms
    por ancora e o painel fica PARADO a maior parte do tempo (255 frames de
    campo com o painel visivel em apenas 34 posicoes distintas). Varrer a cada
    tick pagaria caro por uma resposta que quase nunca muda.

    DUAS CADENCIAS, e a diferenca entre elas foi medida no replay das gravacoes:

    - **Perdeu o seguimento -> varre AGORA, na mesma volta.** Perder a posicao
      conhecida e a evidencia mais forte que existe de que o painel se mexeu.
      Esperar ali custou, na versao anterior, 13 dos 33 frames abertos da sessao
      em que o usuario arrasta o painel — e custou o `f005` do incidente 27x.
    - **Nao sabe onde ele esta -> varre a cada
      `TICKS_ENTRE_VARREDURAS_OCIOSAS`.** E o caso comum e caro: com o mercado
      fechado, varrer a cada volta gastaria ~135 ms por tick para sempre.

    Sem ancora nenhuma (instalacao que nunca calibrou o mercado) ele nunca abre
    — a feature fica OFF, que e o unico padrao seguro para um sinal que a Fase 4
    vai usar perto do detector de morte.
    """

    def __init__(
        self,
        ancoras: list[AncoraDoPainel],
        limiar: float = CASAMENTO_MINIMO_DA_ANCORA,
        ticks_entre_varreduras: int = TICKS_ENTRE_VARREDURAS_OCIOSAS,
    ) -> None:
        self._ancoras = list(ancoras)
        self._limiar = limiar
        self._ticks_entre_varreduras = max(1, int(ticks_entre_varreduras))
        self._origem: tuple[int, int] | None = None
        self._desde_a_varredura = self._ticks_entre_varreduras
        self.varreduras = 0

    @property
    def origem(self) -> tuple[int, int] | None:
        """Onde o painel foi visto pela ultima vez. None = nao esta rastreado."""
        return self._origem

    def observar(self, janela: np.ndarray) -> VotoDoPainel:
        if not self._ancoras:
            return VotoDoPainel(aberto=False, melhor=0.0)

        if self._origem is not None:
            voto = conferir_painel(
                janela, self._origem, self._ancoras, self._limiar
            )
            if voto.aberto:
                return voto
            # Saiu de onde estava. Procurar AGORA — nao na proxima volta.
            self._origem = None
            return self._varrer(janela)

        self._desde_a_varredura += 1
        if self._desde_a_varredura < self._ticks_entre_varreduras:
            return VotoDoPainel(aberto=False, melhor=0.0)
        return self._varrer(janela)

    def _varrer(self, janela: np.ndarray) -> VotoDoPainel:
        self._desde_a_varredura = 0
        self.varreduras += 1
        origem = localizar_painel(janela, self._ancoras, self._limiar)
        if origem is None:
            return VotoDoPainel(aberto=False, melhor=0.0)

        self._origem = origem
        return conferir_painel(janela, origem, self._ancoras, self._limiar)


def ancoras_para_calibracao(ancoras: list[AncoraDoPainel]) -> list[dict]:
    """Empacota as ancoras para dentro do `calibration.json`.

    `altura`/`largura` sao gravadas AO LADO do molde, e nao dentro dele, de
    proposito: elas sao a FORMA ESPERADA contra a qual o molde sera conferido
    na volta. Uma dimensao que mora so dentro do proprio molde nao pode
    conferi-lo -- o dado se declararia correto sozinho.

    `AncoraDoPainel` nao guarda largura/altura separadas, entao sem estes dois
    campos nao havia de onde tirar a forma esperada, e `ancoras_de_calibracao`
    chamava `molde_de_hex(molde)` sem ela. Ver WR-01.
    """
    return [
        {
            "nome": a.nome,
            "dx": int(a.dx),
            "dy": int(a.dy),
            "altura": int(a.molde.shape[0]),
            "largura": int(a.molde.shape[1]),
            "molde": molde_para_hex(a.molde),
        }
        for a in ancoras
    ]


def ancoras_de_calibracao(dados: list[dict] | None) -> list[AncoraDoPainel]:
    """Desempacota as ancoras vindas do `calibration.json`.

    ENTRADA NAO CONFIAVEL, pelo mesmo motivo de `molde_de_hex`: o arquivo pode
    ter sido editado a mao ou gravado errado por uma ferramenta futura. Um
    deslocamento em texto (`"494"`) so quebraria dentro da aritmetica de recorte,
    no meio do farm; um nome ausente sumiria do log de diagnostico justamente
    quando alguem estivesse tentando entender por que o mercado nao e visto.

    `None` e lista vazia devolvem lista vazia: e o estado legitimo de "nao
    calibrei o mercado", e com ele o `RastreioDoPainel` nunca abre.
    """
    if not dados:
        return []

    ancoras: list[AncoraDoPainel] = []
    for indice, bruto in enumerate(dados):
        if not isinstance(bruto, dict):
            raise ValueError(
                f"mercado_ancoras[{indice}] precisa ser um objeto, veio "
                f"{type(bruto).__name__}. Recalibre o mercado."
            )
        nome = bruto.get("nome")
        if not isinstance(nome, str) or not nome:
            raise ValueError(
                f"mercado_ancoras[{indice}] esta sem nome utilizavel. O nome e "
                f"o que aparece no log quando o mercado deixa de ser visto. "
                f"Recalibre o mercado."
            )
        deslocamentos = []
        for eixo in ("dx", "dy"):
            valor = bruto.get(eixo)
            if isinstance(valor, bool) or not isinstance(valor, int):
                raise ValueError(
                    f"mercado_ancoras[{indice}] ({nome}): {eixo} precisa ser um "
                    f"inteiro, veio {type(valor).__name__} ({valor!r}). "
                    f"Recalibre o mercado."
                )
            deslocamentos.append(valor)
        molde = bruto.get("molde")
        if not isinstance(molde, dict):
            raise ValueError(
                f"mercado_ancoras[{indice}] ({nome}): molde precisa ser um "
                f"objeto com altura, largura e bytes. Recalibre o mercado."
            )
        # A FORMA ESPERADA, quando o arquivo a traz.
        #
        # `molde_de_hex` ganhou `forma_esperada` e a docstring dele diz "Passe
        # sempre que tiver" -- mas NENHUM chamador de producao passava: so os
        # testes. Este e o caminho que o `RastreioDoPainel` usa de verdade,
        # entao o guard existia sem proteger nada. Um molde transposto (100x28
        # declarado como 28x100) carregava sem erro, batia no guard de tamanho
        # de `casamento_da_ancora` e devolvia 0.0 para todo frame: o mercado
        # sumia sem uma linha de log -- verbatim o desfecho que o guard existe
        # para impedir.
        #
        # `None` quando o arquivo nao traz os campos, e nao recusa: um
        # `calibration.json` gravado antes deste commit continua carregando,
        # pelo mesmo criterio de compatibilidade do `.get` do
        # `banner_manutencao`. Ele so nao ganha a conferencia -- recalibrar o
        # mercado a acrescenta.
        forma = None
        alt, larg = bruto.get("altura"), bruto.get("largura")
        if (
            isinstance(alt, int)
            and isinstance(larg, int)
            and not isinstance(alt, bool)
            and not isinstance(larg, bool)
        ):
            forma = (alt, larg)

        ancoras.append(
            AncoraDoPainel(
                nome=nome,
                dx=deslocamentos[0],
                dy=deslocamentos[1],
                molde=molde_de_hex(molde, forma_esperada=forma),
            )
        )
    return ancoras


# --------------------------------------------------------------------------
# Os moldes de GLIFO: o vocabulario com que a Fase 2 vai ler todo preco
# --------------------------------------------------------------------------


def glifos_para_calibracao(moldes: dict[str, np.ndarray]) -> list[dict]:
    """Empacota os moldes de glifo para dentro do `calibration.json`.

    Trilho identico ao de `ancoras_para_calibracao`: `altura`/`largura` vao AO
    LADO do molde, nao dentro dele, para servirem de forma esperada na volta.

    O molde gravado e a MASCARA BINARIA escalada para 0/255. A correlacao
    normalizada e invariante a media e a escala, entao 0/255 nao muda um decimal
    do casamento e deixa o molde legivel em qualquer visualizador -- util quando
    alguem abrir o arquivo tentando entender por que um `8` virou `0`.

    A representacao binaria nao e gosto, e medicao: sobre os 11 glifos reais, o
    pior par inter-classe da mascara e 0.7171 contra 0.8434 do cinza, e a
    mascara vence o cinza nas TRES convencoes de recorte medidas (0.7858<0.9020,
    0.6953<0.8003, 0.7171<0.8434).

    SEJA HONESTO SOBRE O ALCANCE DOS CAMPOS IRMAOS. Para as ancoras,
    `forma_esperada` tem dentes porque vem de fonte INDEPENDENTE
    (`Calibracao.mercado_ancora`, o retangulo que o usuario arrastou). Um
    recorte de glifo NAO carrega coordenada nenhuma -- e por isso que ele pode
    ser cortado de qualquer frame --, entao aqui nao existe fonte de forma
    independente por item. Estes campos sao REDUNDANCIA: o que eles pegam e
    edicao manual de UMA das duas copias. Uma transposicao coerente, com as duas
    trocadas juntas, passa por eles -- quem a pega e o guard de CONJUNTO em
    `glifos_de_calibracao`.
    """
    return [
        {
            "glifo": rotulo,
            "altura": int(molde.shape[0]),
            "largura": int(molde.shape[1]),
            "molde": molde_para_hex(molde),
        }
        for rotulo, molde in moldes.items()
    ]


def glifos_de_calibracao(dados: list[dict] | None) -> dict[str, np.ndarray]:
    """Desempacota os moldes de glifo vindos do `calibration.json`.

    ENTRADA NAO CONFIAVEL, pelo mesmo criterio de `ancoras_de_calibracao`. Um
    glifo com rotulo repetido faria o segundo sumir calado; um molde corrompido
    nunca casaria com nada, e a Fase 2 descartaria toda linha que o contivesse
    sem uma linha de erro dizendo por que.

    O GUARD DE CONJUNTO E O UNICO COM FONTE INDEPENDENTE NESTE CAMINHO. Todos os
    glifos de uma calibracao saem da MESMA faixa de linhas compartilhada --
    medido: 9 px nas sete marcacoes das duas fixtures --, entao a altura de cada
    molde e conferida contra a altura DOMINANTE do conjunto. Um `(4,9)`
    transposto no meio de um conjunto de `(9,N)` e detectado pelos vizinhos, e
    essa e a unica deteccao de transposicao com fundamento aqui.

    `None` e lista vazia devolvem dicionario vazio: e o estado legitimo de
    "ainda nao cortei glifos", e com ele a leitura da Fase 2 simplesmente nao
    acontece.
    """
    if not dados:
        return {}

    moldes: dict[str, np.ndarray] = {}
    for indice, bruto in enumerate(dados):
        if not isinstance(bruto, dict):
            raise ValueError(
                f"mercado_templates_de_digito[{indice}] precisa ser um objeto, "
                f"veio {type(bruto).__name__}. Recalibre os digitos do mercado."
            )
        rotulo = bruto.get("glifo")
        if not isinstance(rotulo, str) or not rotulo:
            raise ValueError(
                f"mercado_templates_de_digito[{indice}] esta sem rotulo "
                f"utilizavel. O rotulo E a identidade do glifo: sem ele o molde "
                f"nao pode virar digito nenhum. Recalibre os digitos do mercado."
            )
        if rotulo in moldes:
            raise ValueError(
                f"mercado_templates_de_digito tem o rotulo '{rotulo}' repetido. "
                f"Um dos dois moldes seria descartado calado, e nao da para "
                f"saber qual e o certo. Recalibre os digitos do mercado."
            )
        molde = bruto.get("molde")
        if not isinstance(molde, dict):
            raise ValueError(
                f"mercado_templates_de_digito[{indice}] ('{rotulo}'): molde "
                f"precisa ser um objeto com altura, largura e bytes. "
                f"Recalibre os digitos do mercado."
            )

        # A forma irma, quando o arquivo a traz. `None` quando nao traz, e nao
        # recusa: um calibration.json gravado antes desta chave continua
        # carregando, pelo criterio do `banner_manutencao` (D-07).
        forma = None
        alt, larg = bruto.get("altura"), bruto.get("largura")
        if (
            isinstance(alt, int)
            and isinstance(larg, int)
            and not isinstance(alt, bool)
            and not isinstance(larg, bool)
        ):
            forma = (alt, larg)

        try:
            moldes[rotulo] = molde_de_hex(molde, forma_esperada=forma)
        except ValueError as erro:
            raise ValueError(
                f"mercado_templates_de_digito['{rotulo}']: {erro} "
                f"Recalibre os digitos do mercado."
            ) from erro

    _conferir_a_altura_do_conjunto(moldes)
    return moldes


def _conferir_a_altura_do_conjunto(moldes: dict[str, np.ndarray]) -> None:
    """Todos os moldes de uma calibracao tem de ter a MESMA altura.

    Vem de como eles foram cortados: uma faixa de linhas compartilhada por
    marcacao, e a mesma faixa em todas as marcacoes do mesmo frame (9 px
    medidos). Um item que diverge nao e uma variacao de fonte -- e um molde
    transposto, cortado de outra calibracao, ou editado a mao.
    """
    if len(moldes) < 2:
        return

    alturas = [m.shape[0] for m in moldes.values()]
    dominante = max(set(alturas), key=alturas.count)
    divergentes = [r for r, m in moldes.items() if m.shape[0] != dominante]
    if divergentes:
        nomes = ", ".join(f"'{r}' ({moldes[r].shape[0]} px)" for r in divergentes)
        raise ValueError(
            f"mercado_templates_de_digito: {nomes} tem altura diferente da "
            f"altura dominante do conjunto ({dominante} px). Todos os glifos de "
            f"uma calibracao saem da mesma faixa de linhas, entao um item mais "
            f"alto ou mais baixo esta transposto ou veio de outra rodada. "
            f"Recalibre os digitos do mercado."
        )
