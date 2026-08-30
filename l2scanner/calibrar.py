"""Ferramenta de calibracao: descobre onde fica a party window na sua tela.

Duas formas de usar, da mais facil para a mais manual:

    python -m l2scanner.calibrar --auto
        Procura a janela do jogo, varre a tela atras do padrao de barras da
        party window e deduz todo o layout sozinho. E o caminho normal.

    python -m l2scanner.calibrar --selecionar
        Abre a captura da tela e voce arrasta o mouse em volta da party window.
        Use se a deteccao automatica errar.

Por que deteccao automatica e nao so arrastar o mouse: as barras da party window
sao um padrao muito caracteristico — faixas horizontais saturadas, todas com a
mesma largura e o mesmo x, igualmente espacadas. Achar isso nos pixels e mais
confiavel do que a mao humana marcando retangulo de 8 pixels de altura.
"""

from __future__ import annotations

# DPI PRIMEIRO — a ferramenta e o scanner precisam concordar sobre o que e um
# pixel, senao as coordenadas gravadas aqui nao significam nada la.
from .dpi import tornar_consciente_de_dpi

_MODO_DPI = tornar_consciente_de_dpi()

import argparse  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from dataclasses import dataclass, fields  # noqa: E402
from pathlib import Path  # noqa: E402

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from .calibracao import (  # noqa: E402
    LIMIARES_HP_PADRAO,
    LIMIARES_MP_PADRAO,
    Calibracao,
    LayoutDaParty,
    descrever_geometria_da_tela,
)
from .captura_janela import (  # noqa: E402
    JanelaSource,
    janela_que_contem,
    listar_janelas_do_jogo,
    origem_da_janela,
    achar_janela,
)
from .agenda import AgendaInvalida  # noqa: E402
from .cliente import esta_na_tela_de_login, nome_do_personagem  # noqa: E402
from .config import ler_personagem_do_jogo  # noqa: E402
from .identidade import criar_assinatura  # noqa: E402
from .frames import Regiao  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_CALIBRACAO = RAIZ / "calibration.json"

# Uma barra de party precisa ter pelo menos isto de largura para nao ser
# confundida com um detalhe colorido do cenario
LARGURA_MINIMA_DE_BARRA = 40


@dataclass
class BarraEncontrada:
    x: int
    y: int
    largura: int
    altura: int


def capturar_tela() -> tuple[np.ndarray, int, int]:
    """Captura o desktop inteiro. Devolve (pixels, offset_x, offset_y)."""
    import mss

    with mss.mss() as sct:
        todos = sct.monitors[0]
        bruto = sct.grab(todos)
        pixels = np.asarray(bruto, dtype=np.uint8)[:, :, :3]
        return pixels, todos["left"], todos["top"]


def achar_barras_vermelhas(pixels: np.ndarray) -> list[BarraEncontrada]:
    """Acha faixas horizontais de vermelho saturado — candidatas a barra de HP.

    A saturacao e o filtro principal, nao o matiz: a parte vazia da barra e
    transparente e mostra o cenario, entao o que distingue barra de terreno e
    ser uma cor solida, nao ser vermelha.
    """
    hsv = cv2.cvtColor(pixels, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    # vermelho da a volta no circulo: duas faixas
    mascara = ((h <= 12) | (h >= 168)) & (s > 150) & (v > 60)

    achadas: list[BarraEncontrada] = []
    numero, rotulos, estatisticas, _ = cv2.connectedComponentsWithStats(
        mascara.astype(np.uint8), connectivity=8
    )

    for i in range(1, numero):
        x, y, larg, alt, area = estatisticas[i]
        if larg < LARGURA_MINIMA_DE_BARRA:
            continue
        if alt < 3 or alt > 30:
            continue
        if larg < alt * 3:  # barra e larga e baixa
            continue
        if area < larg * alt * 0.6:  # retangulo cheio, nao um contorno
            continue
        achadas.append(BarraEncontrada(int(x), int(y), int(larg), int(alt)))

    return achadas


def agrupar_em_party(barras: list[BarraEncontrada]) -> list[BarraEncontrada]:
    """Fica so com o maior grupo de barras alinhadas e igualmente espacadas.

    A party window e o unico lugar da tela com varias barras identicas
    empilhadas com espacamento constante. Barra de alvo, de pet e de mob
    aparecem sozinhas ou em pares, e caem fora aqui.
    """
    if not barras:
        return []

    # agrupa por (x, largura): membros da mesma party compartilham os dois
    grupos: dict[tuple[int, int], list[BarraEncontrada]] = {}
    for barra in barras:
        chave = (barra.x, barra.largura)
        grupos.setdefault(chave, []).append(barra)

    maior = max(grupos.values(), key=len)
    return sorted(maior, key=lambda b: b.y)


def deduzir_passo(barras: list[BarraEncontrada]) -> int | None:
    """Espacamento vertical entre membros consecutivos.

    Tolera VAOS de proposito. Um membro morto tem a barra de HP vazia, entao
    ele nao aparece na lista de barras vermelhas — e a distancia ate o proximo
    vira o dobro do passo. Exigir espacamento perfeitamente regular faria a
    calibracao falhar justamente quando alguem da party esta morto, que e
    quando o usuario mais quer o scanner funcionando.

    Entao o passo e a MENOR distancia observada, e as demais precisam ser
    multiplos aproximados dela.
    """
    if len(barras) < 2:
        return None

    distancias = [barras[i + 1].y - barras[i].y for i in range(len(barras) - 1)]
    passo = min(distancias)

    if passo < 10:  # barras coladas nao sao linhas de party
        return None

    for distancia in distancias:
        multiplo = round(distancia / passo)
        if multiplo < 1 or abs(distancia - multiplo * passo) > 3:
            return None

    return int(passo)


def achar_barra_azul_abaixo(
    pixels: np.ndarray, hp: BarraEncontrada
) -> BarraEncontrada | None:
    """Acha a barra de MP logo abaixo de uma barra de HP."""
    hsv = cv2.cvtColor(pixels, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    azul = (h >= 95) & (h <= 130) & (s > 150) & (v > 60)

    # procura nas ~25 linhas abaixo do fim do HP
    inicio = hp.y + hp.altura
    for y in range(inicio, min(inicio + 25, pixels.shape[0])):
        faixa = azul[y, hp.x : hp.x + hp.largura]
        if faixa.any():
            return BarraEncontrada(hp.x, y, hp.largura, hp.altura)
    return None


def achar_icone_a_esquerda(
    pixels: np.ndarray, hp: BarraEncontrada
) -> Regiao | None:
    """Acha o icone de classe a esquerda das barras.

    O icone e o indicador de presenca da linha — o unico sinal que distingue
    "HP zerado" (morte) de "linha nao existe" (saiu da PT), porque nas barras
    os dois leem 0%.
    """
    tamanho = 24
    # o icone fica alinhado com o topo da barra de HP, um pouco acima
    topo = max(0, hp.y - 6)

    melhor = None
    melhor_desvio = 0.0

    for x in range(max(0, hp.x - 60), hp.x - 10):
        recorte = pixels[topo : topo + tamanho, x : x + tamanho]
        if recorte.shape[0] < tamanho or recorte.shape[1] < tamanho:
            continue
        cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
        desvio = float(cinza.std())
        escuros = float((cinza < 60).mean())

        if desvio > melhor_desvio and escuros > 0.20:
            melhor_desvio = desvio
            melhor = Regiao(x, topo, tamanho, tamanho)

    return melhor if melhor_desvio > 30 else None


def achar_barra_do_proprio(
    pixels: np.ndarray, origem_janela: tuple[int, int] = (0, 0)
) -> Regiao | None:
    """Acha a barra de HP do proprio personagem, no topo da janela.

    Ela e visualmente diferente das da party: bem mais alta (~24 px contra 8),
    e tem o texto "HP 3597/3597" desenhado por cima. A altura e o que a
    identifica sem ambiguidade — nada mais na tela e uma faixa vermelha
    saturada tao grossa.

    O texto por cima nao atrapalha a medicao: a barra e alta o bastante para
    que as letras nao ocupem metade de nenhuma coluna.
    """
    # A BUSCA COBRE A JANELA INTEIRA, e nao so o topo.
    #
    # Ela olhava apenas os primeiros 260 px, porque a UI do jogo nasce com a
    # barra no canto superior esquerdo. Mas a UI do Lineage 2 e ARRASTAVEL: o
    # usuario moveu a barra dele para baixo e a busca parou de achar — nem o
    # calibrar.bat resolvia mais, e a regiao gravada passou a apontar para
    # grama, o que produziu um "Yazalaque MORTO" com ele vivo e com 3537/3537
    # de HP na tela.
    #
    # Alargar e seguro, e isso foi MEDIDO na janela real: 299 componentes
    # vermelhos na janela inteira, e EXATAMENTE UM passa nos criterios abaixo.
    # A assinatura da barra — faixa vermelha saturada, larga, com 14 a 40 px de
    # altura, mais de 3x mais larga que alta e mais de metade preenchida — nao
    # tem concorrente na tela.
    #
    # A janela continua sendo o limite: num arranjo de tres monitores a imagem
    # do desktop inclui telas vizinhas, e procurar nelas acharia a barra do
    # OUTRO cliente.
    jx, jy = origem_janela
    altura, largura = pixels.shape[:2]
    recorte = pixels[jy:altura, jx:largura]
    if recorte.size == 0:
        return None
    hsv = cv2.cvtColor(recorte, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    vermelho = (((h <= 12) | (h >= 168)) & (s > 150) & (v > 60)).astype(np.uint8)

    numero, _, estatisticas, _ = cv2.connectedComponentsWithStats(
        vermelho, connectivity=8
    )
    candidatas = []
    for i in range(1, numero):
        x, y, larg, alt, area = estatisticas[i]
        if larg < 80 or not (14 <= alt <= 40):
            continue
        if larg < alt * 3:
            continue
        if area < larg * alt * 0.5:
            continue
        candidatas.append((int(x), int(y), int(larg), int(alt)))

    if not candidatas:
        return None

    # A barra do proprio personagem e a MAIS A ESQUERDA. Nao a mais larga:
    # quando ha um alvo selecionado, a barra dele aparece ao CENTRO e e mais
    # larga que a nossa — escolher pela largura pegava o monstro em vez do
    # jogador.
    #
    # Continua sendo a mais a esquerda mesmo depois de a busca passar a cobrir
    # a janela inteira: a barra do alvo e a da party ficam mais ao centro e a
    # direita. O desempate por altura mudou para o MENOR y so para manter o
    # comportamento antigo quando ha empate horizontal.
    x, y, larg, alt = min(candidatas, key=lambda c: (c[0], c[1]))
    # devolve em coordenadas RELATIVAS a janela, como a party window
    return Regiao(esquerda=x, topo=y, largura=larg, altura=alt)


def calibrar_automatico(pixels: np.ndarray, ox: int, oy: int) -> Calibracao | None:
    """Deduz toda a calibracao a partir de uma captura da tela."""
    print("Procurando barras de HP na tela...")
    barras = achar_barras_vermelhas(pixels)
    print(f"  {len(barras)} faixa(s) vermelha(s) candidata(s)")

    party = agrupar_em_party(barras)
    if len(party) < 2:
        print("  Nao achei um grupo de barras empilhadas.")
        print("  A party window esta visivel na tela? Voce esta em party?")
        return None

    passo = deduzir_passo(party)
    if passo is None:
        print(f"  Achei {len(party)} barras, mas o espacamento nao e regular.")
        print("  Isso normalmente significa que peguei coisa que nao e party.")
        return None

    vaos = sum(round((party[i+1].y - party[i].y) / passo) - 1
               for i in range(len(party) - 1))
    print(f"  {len(party)} barras visiveis, espacamento de {passo} px")
    if vaos:
        print(f"  {vaos} vao(s) — provavelmente membro morto, barra vazia")

    primeira = party[0]
    mp = achar_barra_azul_abaixo(pixels, primeira)
    if mp is None:
        print("  Nao achei a barra de MP abaixo da de HP.")
        return None
    print(f"  MP a {mp.y - primeira.y} px abaixo do HP")

    icone = achar_icone_a_esquerda(pixels, primeira)
    if icone is None:
        print("  Nao achei o icone de classe a esquerda das barras.")
        print("  Sem ele nao da para distinguir morte de saida da party.")
        return None
    print(f"  Icone de classe em x={icone.esquerda + ox}")

    # A janela vai da esquerda do icone ate a direita das barras, com folga.
    # Alta o bastante para uma party cheia: linhas extras leem como vazias,
    # que e o comportamento correto.
    margem = 12
    janela_esq = max(0, icone.esquerda - margem)
    janela_topo = max(0, min(icone.topo, primeira.y) - 34)
    janela_larg = (primeira.x + primeira.largura + margem) - janela_esq
    janela_alt = 34 + passo * 8

    party_window = Regiao(
        esquerda=janela_esq + ox,
        topo=janela_topo + oy,
        largura=janela_larg,
        altura=min(janela_alt, pixels.shape[0] - janela_topo),
    )

    # A ancora fica no TOPO da janela porque a party window e ancorada em cima
    # e encolhe por baixo conforme a PT diminui. Uma ancora embaixo sumiria
    # sozinha quando alguem saisse, e o scanner entraria em modo cego a toa.
    ancora = Regiao(esquerda=0, topo=0, largura=min(40, janela_larg), altura=28)

    layout = LayoutDaParty(
        icone_x=icone.esquerda - janela_esq,
        icone_y=icone.topo - janela_topo,
        icone_tamanho=icone.largura,
        barra_x=primeira.x - janela_esq,
        barra_largura=primeira.largura,
        barra_altura=primeira.altura,
        hp_y=primeira.y - janela_topo,
        mp_y=mp.y - janela_topo,
        passo=passo,
        max_linhas=8,
    )

    return Calibracao(
        party_window=party_window,
        ancora=ancora,
        layout=layout,
        limiares_hp=LIMIARES_HP_PADRAO,
        limiares_mp=LIMIARES_MP_PADRAO,
        geometria_da_tela=descrever_geometria_da_tela(),
    )


DRENO_DA_FILA_DE_TECLAS = 0.15
"""Segundos bombeando a fila do HighGUI antes de abrir uma selecao.

NAO e "ate a primeira sondagem vazia". A ferramenta que DIAGNOSTICOU o
vazamento de ENTER (`tools/diagnosticar_selecao.py`) registra, medido, que uma
tecla pode chegar alguns milissegundos DEPOIS de a janela anterior fechar -- e
por isso ela mesma dreno por 300 ms, e nao por primeira leitura vazia.

O valor tem folga sobre o zero e e imperceptivel para quem esta com a mao no
mouse: 0,15 s por selecao, contra os 5+N arrastos que uma calibracao de mercado
custa.
"""


def esvaziar_a_fila_de_teclas(segundos: float = DRENO_DA_FILA_DE_TECLAS) -> int:
    """Bombeia o event loop do HighGUI POR TEMPO, e devolve quantas teclas saiu.

    Por que por tempo e nao ate o primeiro `-1`: o laco anterior era

        for _ in range(20):
            if cv2.waitKey(1) == -1:
                break

    e ele saia na PRIMEIRA sondagem vazia -- cerca de 1 ms de bombeamento. Uma
    tecla que chegasse 3 ms depois passava direto.

    O caminho de risco nao e so o navegador de frames. `calibrar()` faz 5 + N
    selecoes seguidas, e a tecla que confirma a selecao *k* e candidata a vazar
    para a *k+1*. Quando isso acontece, `selectROI` devolve (0,0,0,0), `_marcar`
    levanta `MercadoNaoCalibravel("selecao cancelada -- nada foi gravado")` e
    TODOS os retangulos ja marcados sao perdidos. E o sintoma original de
    2026-08-28, so que no meio do fluxo em vez de no comeco.

    MEDIDO durante aquela investigacao, e e o que torna este dreno confiavel:
    `cv2.waitKey(300)` demora os 300 ms pedidos mesmo SEM nenhuma janela aberta
    (308,5 ms sem janela; 303,4 ms com; 311,5 ms depois de `destroyAllWindows`).
    Ele nao retorna cedo, entao bombeia o tempo todo.
    """
    drenadas = 0
    fim = time.perf_counter() + segundos
    while time.perf_counter() < fim:
        if cv2.waitKey(1) != -1:
            drenadas += 1
    return drenadas


def _decidir_sobre_a_sugestao(titulo: str) -> str:
    """ENTER aceita a sugestao, ESC cancela, qualquer outra tecla redesenha.

    Vive FORA de `_selecionar_regiao` por duas razoes, e as duas sao concretas.

    A primeira e um tripwire: `test_janela_de_selecao.py::
    test_o_selecionar_regiao_usa_o_dreno_por_tempo` proibe a palavra `break`
    dentro do fonte de `_selecionar_regiao`, porque foi um laco com `break` que
    esvaziava a fila de teclas cedo demais e deixava um ENTER vazar para a
    selecao seguinte. Um laco de teclado precisa de `break`; este mora aqui.

    A segunda e a razao de existir uma pergunta de teclado ANTES do
    `selectROI`, em vez de interpretar o retorno dele. MEDIDO no OpenCV 4.14:
    `cv2.selectROI` devolve `(0,0,0,0)` tanto no ESC quanto no ENTER-sem-
    arrasto, e nao expoe qual tecla encerrou. Com uma sugestao na tela,
    "confirmar sem arrastar" significa ACEITAR e ESC significa CANCELAR --
    duas intencoes opostas com a mesma assinatura. Adivinhar entre elas seria
    exatamente o "aceitar calado" que esta ferramenta veio consertar; perguntar
    antes torna as duas distinguiveis sem tirar do usuario o direito de
    redesenhar.

    A sondagem e com PRAZO (`waitKeyEx(50)`) e confere se a janela ainda
    existe, pela licao ja registrada em `calibrar_mercado.navegar_e_escolher`:
    `waitKeyEx(0)` bloqueia para sempre, e se o usuario fechar a janela no X
    nao ha mais quem receba tecla -- o console fica parado sem mensagem e a
    unica saida e Ctrl-C.
    """
    while True:
        bruto = cv2.waitKeyEx(50)
        try:
            visivel = cv2.getWindowProperty(titulo, cv2.WND_PROP_VISIBLE) >= 1
        except cv2.error:  # pragma: no cover - depende do backend
            visivel = False
        if not visivel:
            return "cancela"
        if bruto == -1:
            continue
        tecla = bruto & 0xFF
        if tecla in (13, 10):  # ENTER
            return "aceita"
        if tecla == 27:  # ESC
            return "cancela"
        return "redesenha"


def _desenhar_a_sugestao(
    visao: np.ndarray, sugestao: tuple[int, int, int, int], escala: float
) -> np.ndarray:
    """A sugestao desenhada sobre uma COPIA da visualizacao, ja reescalada.

    Copia, e nao a visualizacao original: quem redesenha recebe a imagem limpa,
    sem um retangulo verde antigo grudado por cima do frame durante o arrasto.
    """
    tela = visao.copy()
    x, y, largura, altura = (int(round(valor * escala)) for valor in sugestao)
    cv2.rectangle(tela, (x, y), (x + largura, y + altura), (0, 255, 0), 2)
    cv2.putText(
        tela, "ENTER aceita", (x, max(14, y - 8)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA,
    )
    return tela


def _selecionar_regiao(
    pixels: np.ndarray,
    titulo: str,
    instrucao: str,
    sugestao: tuple[int, int, int, int] | None = None,
) -> tuple[int, int, int, int] | None:
    """Usuario arrasta um retangulo; devolve (x, y, largura, altura) NO ORIGINAL.

    Extraida de `calibrar_selecionando`, que era o unico lugar do projeto com
    esta mecanica. A calibracao do mercado precisa de tres ou mais selecoes
    independentes e nao devolve `Calibracao` nenhuma, entao ela nao podia
    reaproveitar aquela funcao como estava — e duplicar `selectROI` num modulo
    novo criaria duas mecanicas de recorte que envelheceriam separadas.

    A REESCALA E A PARTE QUE NAO PODE SER DUPLICADA. Uma janela de jogo em
    3440 px nao cabe na tela onde ela e mostrada, entao a visualizacao e
    encolhida para caber em 1600 px de largura — e a caixa que o usuario
    desenha volta multiplicada. Errar essa divisao produz um retangulo
    plausivel na posicao errada, que e o defeito mais caro que uma ferramenta
    de calibracao pode ter.

    Caixa degenerada (largura ou altura zero) devolve None, que e como o
    usuario cancela: `cv2.selectROI` devolve (0,0,0,0) no ESC.

    `sugestao` E OPCIONAL, E O PADRAO `None` E UMA PROMESSA
    ------------------------------------------------------
    Sem sugestao, esta funcao faz EXATAMENTE o que fazia antes -- nenhuma
    janela a mais, nenhuma tecla a mais, nenhum caminho novo. Isso nao e
    elegancia: `calibrar_selecionando` (a party window) passa por aqui e
    FUNCIONA hoje, depois de o CR-01 ter consertado a janela em escala errada
    que corrompia qualquer retangulo desenhado a mao. O planejador do 01-05
    recusou esta ideia (WR-08) justamente por temer mexer numa funcao
    compartilhada; o parametro opcional e a resposta a esse medo, e o teste
    `test_a_party_nao_ganha_janela_de_sugestao` e a prova.

    COM sugestao, o retangulo aparece PRE-DESENHADO e o usuario decide antes de
    tocar no mouse: ENTER aceita, ESC cancela, qualquer outra tecla abre o
    arrasto normal. A razao de ser assim e MEDIDA em campo (2026-08-29): cada
    instrucao em prosa desta ferramenta -- "marque a AREA DA LISTA inteira",
    "marque UM numero da coluna de preco" -- gerou uma interpretacao diferente e
    um retangulo errado aceito em silencio. A ferramenta ja sabia onde as coisas
    estavam; ela so nao mostrava.

    Por que a decisao vem ANTES do `selectROI` e nao do retorno dele: aquele
    retorno nao distingue ESC de ENTER-sem-arrasto -- os dois valem `(0,0,0,0)`.
    Ver `_decidir_sobre_a_sugestao`. E sem sugestao `(0,0,0,0)` continua
    significando cancelar, exatamente como antes; cancelamento nunca vira
    aceitacao por omissao.
    """
    largura_original = pixels.shape[1]
    escala = min(1.0, 1600 / largura_original)
    visao = (
        cv2.resize(pixels, None, fx=escala, fy=escala) if escala < 1.0 else pixels
    )

    print(f"\n{instrucao}")
    if sugestao is not None:
        print(f"SUGESTAO ja desenhada na tela: {sugestao}")
        print("ENTER aceita a sugestao | qualquer outra tecla deixa voce arrastar")
    print("ESC cancela.\n")

    # (1) ESVAZIA A FILA DE TECLAS ANTES DE ABRIR A SELECAO.
    #
    # MEDIDO EM CAMPO 2026-08-28: o usuario confirmava o frame com ENTER no
    # navegador de gravacao e o `selectROI` abria em seguida ja recebendo
    # AQUELE MESMO ENTER, ainda pendente na fila do HighGUI. Para o
    # `selectROI`, ENTER significa 'confirmar a selecao' -- e como nao havia
    # selecao nenhuma, ele devolvia (0,0,0,0) e a ferramenta abortava com
    # 'Nada selecionado' antes de o usuario poder encostar no mouse.
    #
    # O sintoma era indistinguivel de 'a janela nao abriu': o console dizia
    # que abriu, a janela piscava, e nada era gravado.
    #
    # O dreno e POR TEMPO, nao ate a primeira sondagem vazia -- ver
    # `esvaziar_a_fila_de_teclas`, que registra a medicao.
    esvaziar_a_fila_de_teclas()

    # (2) A JANELA E CRIADA E POSICIONADA ANTES, DE PROPOSITO -- E EM
    #     WINDOW_AUTOSIZE, QUE E A METADE QUE IMPORTA DESTA LINHA.
    #
    # Por que criar a janela antes: MEDIDO EM CAMPO 2026-08-28, o usuario
    # rodou a calibracao de mercado, passou pelo navegador de frames e
    # relatou que as janelas de selecao 'nao apareceram'. Elas apareciam --
    # o log prova que selectROI foi chamado tres vezes --, mas o
    # cv2.selectROI sozinho nao diz onde se posiciona, e numa maquina de
    # DOIS MONITORES a janela pode nascer atras do terminal ou no monitor
    # onde o jogo esta. Uma ferramenta interativa cuja janela o usuario nao
    # acha e indistinguivel de uma ferramenta travada. namedWindow +
    # moveWindow com o MESMO titulo faz o selectROI REUSAR esta janela, em
    # vez de criar a dele em lugar nenhum previsivel.
    #
    # Por que AUTOSIZE e nao NORMAL: uma janela WINDOW_NORMAL **nao se
    # redimensiona para a imagem** -- ela nasce no tamanho que o Win32
    # resolver dar, e a imagem e espremida dentro dele. MEDIDO nesta
    # maquina (cv2 4.14.0, `getWindowImageRect` no caminho real desta
    # funcao, com o selectROI dublado):
    #
    #     visao 1600x1295 | WINDOW_NORMAL   -> janela 120x1440
    #     visao 1600x1295 | WINDOW_AUTOSIZE -> janela 1600x1295
    #     visao 1720x1392 | WINDOW_NORMAL   -> janela 120x1440
    #     visao 1720x1392 | WINDOW_AUTOSIZE -> janela 1720x1392
    #
    # O numero do NORMAL nao e estavel entre execucoes (ja saiu 304x281
    # numa outra medicao) justamente porque nao vem da imagem: vem do
    # Win32. O AUTOSIZE bate a imagem exatamente, em toda dimensao testada.
    #
    # Com a janela encolhida, cada pixel de mouse do usuario vale varios
    # pixels da visualizacao -- que ja e uma visualizacao reescalada -- e
    # esse segundo encolhimento nao entra na divisao por `escala` la
    # embaixo. O resultado e o defeito que o docstring desta funcao chama
    # de mais caro que existe: 'um retangulo plausivel na posicao errada'.
    # E a `calibrar_selecionando` da PARTY passa por aqui tambem.
    #
    # `moveWindow` posiciona igual sobre AUTOSIZE, entao a janela continua
    # nascendo onde o usuario a encontra: nada foi perdido.
    cv2.namedWindow(titulo, cv2.WINDOW_AUTOSIZE)
    cv2.moveWindow(titulo, 40, 40)

    # (3) COM SUGESTAO: mostra o retangulo proposto e pergunta, ANTES do
    #     arrasto. Sem sugestao este bloco inteiro nao existe e o caminho e o
    #     mesmo de sempre -- ver o docstring, e o teste que prova a promessa.
    if sugestao is not None:
        cv2.imshow(titulo, _desenhar_a_sugestao(visao, sugestao, escala))
        cv2.waitKey(1)
        decisao = _decidir_sobre_a_sugestao(titulo)
        if decisao == "aceita":
            cv2.destroyAllWindows()
            print(f"  usando a sugestao {sugestao}")
            return sugestao
        if decisao == "cancela":
            cv2.destroyAllWindows()
            print("Nada selecionado.")
            return None

    cv2.imshow(titulo, visao)
    cv2.waitKey(1)

    caixa = cv2.selectROI(titulo, visao, showCrosshair=False)
    cv2.destroyAllWindows()

    if caixa[2] == 0 or caixa[3] == 0:
        print("Nada selecionado.")
        return None

    x, y, larg, alt = (int(valor / escala) for valor in caixa)
    return x, y, larg, alt


def calibrar_selecionando(pixels: np.ndarray, ox: int, oy: int) -> Calibracao | None:
    """Usuario arrasta o mouse em volta da party window; o resto e deduzido."""
    caixa = _selecionar_regiao(
        pixels,
        "Marque a party window",
        "Arraste o mouse em volta da party window e tecle ENTER.",
    )
    if caixa is None:
        return None

    x, y, larg, alt = caixa
    recorte = pixels[y : y + alt, x : x + larg]

    # Dentro da area marcada, a deteccao automatica costuma acertar facil
    return calibrar_automatico(recorte, ox + x, oy + y)


def _gravar_conferencia(imagem: np.ndarray) -> Path | None:
    """Grava a imagem de conferencia, ou diz alto que nao conseguiu.

    Este e o UNICO lugar do modulo que escreve imagem, e a duplicacao e
    justamente o que precisava acabar: a gravacao acontecia em DOIS pontos e os
    dois jogavam o retorno de `cv2.imwrite` fora. Com o erro calado nos dois
    lugares, o calibrador anunciava uma imagem que nao existia e o usuario
    conferia A IMAGEM VELHA — validando uma calibracao errada.

    O gatilho real e o proprio conselho da ferramenta: ela manda ABRIR a
    imagem, e com ela aberta no visualizador de fotos a gravacao seguinte
    falha. Medido nesta maquina: destino somente-leitura, destino ocupado por
    um diretorio e pasta inexistente devolvem `False`, e nenhum dos tres
    levanta excecao — por isso ninguem percebia.

    `RAIZ` e lido como global de proposito. Capturado em argumento com valor
    padrao, o teste nao conseguiria redirecionar a escrita para um tmp_path.
    """

    def tentar(caminho: Path) -> bool:
        # O try/except existe ALEM do retorno booleano para que o `False`
        # documentado e uma excecao inesperada caiam no MESMO caminho de
        # falha. Tratar so um dos dois deixaria a outra metade calada, que e
        # exatamente o defeito que esta funcao veio consertar.
        try:
            return bool(cv2.imwrite(str(caminho), imagem))
        except Exception:  # noqa: BLE001
            return False

    def anunciar(caminho: Path) -> Path:
        # O horario sai do mtime do ARQUIVO, nunca do relogio no momento da
        # chamada. A pergunta que o usuario faz olhando a tela e "essa imagem
        # e nova?", e so o mtime responde isso — o relogio responderia "sim"
        # com a mesma confianca para um arquivo de ontem.
        horario = time.strftime("%H:%M:%S", time.localtime(caminho.stat().st_mtime))
        print(f"\nImagem de conferencia: {caminho}")
        print(f"  gravada agora, as {horario}")
        return caminho

    padrao = RAIZ / "calibracao-conferencia.png"
    if tentar(padrao):
        return anunciar(padrao)

    # Este aviso nao cita nome de arquivo nenhum de proposito: se a tentativa
    # alternativa logo abaixo tambem falhar, um nome citado aqui seria mais uma
    # promessa vazia na tela — o bug de novo, so que uma linha acima.
    print("\nO arquivo de conferencia de sempre esta travado.")
    print("O motivo mais comum e ele estar aberto no visualizador de fotos;")
    print("feche a imagem antes da proxima calibracao.")
    print("Gravando a conferencia desta rodada com outro nome...")

    alternativo = RAIZ / f"calibracao-conferencia-{time.strftime('%H%M%S')}.png"
    if tentar(alternativo):
        return anunciar(alternativo)

    print("\nNAO consegui gravar imagem de conferencia nenhuma.")
    print("Nao existe imagem para voce conferir nesta rodada — se houver alguma")
    print("na pasta, ela e de outra calibracao e nao serve para conferir esta.")
    return None


def conferir_visualmente(cal: Calibracao, pixels: np.ndarray, ox: int, oy: int) -> None:
    """Desenha as regioes por cima da captura, para o humano OLHAR.

    Numero conferindo com numero nao prova que a regiao esta no lugar certo.
    Ver a imagem prova.
    """
    pw = cal.party_window
    recorte = pixels[
        pw.topo - oy : pw.topo - oy + pw.altura,
        pw.esquerda - ox : pw.esquerda - ox + pw.largura,
    ].copy()

    lay = cal.layout
    cv2.rectangle(
        recorte,
        (cal.ancora.esquerda, cal.ancora.topo),
        (
            cal.ancora.esquerda + cal.ancora.largura,
            cal.ancora.topo + cal.ancora.altura,
        ),
        (0, 255, 255),
        1,
    )

    for i in range(lay.max_linhas):
        dy = i * lay.passo
        cv2.rectangle(
            recorte,
            (lay.icone_x, lay.icone_y + dy),
            (lay.icone_x + lay.icone_tamanho, lay.icone_y + lay.icone_tamanho + dy),
            (0, 255, 0),
            1,
        )
        cv2.rectangle(
            recorte,
            (lay.barra_x, lay.hp_y + dy),
            (lay.barra_x + lay.barra_largura, lay.hp_y + lay.barra_altura + dy),
            (0, 0, 255),
            1,
        )
        cv2.rectangle(
            recorte,
            (lay.barra_x, lay.mp_y + dy),
            (lay.barra_x + lay.barra_largura, lay.mp_y + lay.barra_altura + dy),
            (255, 0, 0),
            1,
        )

    ampliado = cv2.resize(recorte, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_NEAREST)
    caminho = _gravar_conferencia(ampliado)

    # Todo o texto abaixo so faz sentido se houver imagem. Ele saia
    # incondicionalmente, e era assim que a falha de gravacao virava mentira:
    # a legenda das cores dava ar de que algo tinha sido desenhado em algum
    # lugar.
    if caminho is None:
        print("A conferencia visual NAO aconteceu.")
        print("Os numeros impressos acima sao tudo o que ha para conferir agora.")
        return

    print("  amarelo = ancora da janela")
    print("  verde   = icone de classe (indicador de presenca)")
    print("  vermelho= barra de HP")
    print("  azul    = barra de MP")
    print(f"\nABRA {caminho}")
    print("e confira se os retangulos batem com a party window.")
    print("Se nao baterem, rode de novo com --selecionar.")


def _conferencia_do_solo(cal: Calibracao, pixels: np.ndarray) -> Path | None:
    """Desenha a barra encontrada, para o usuario conferir antes de confiar.

    O calibrador normal desenha a party window inteira; aqui so ha uma coisa
    para mostrar. E ela precisa ser mostrada: a busca escolhe a barra MAIS A
    ESQUERDA, e se o usuario tiver um alvo selecionado a barra dele tambem
    qualifica. Um retangulo no lugar errado e obvio na imagem e invisivel no
    JSON.
    """
    r = cal.hp_proprio
    tela = pixels.copy()
    cv2.rectangle(
        tela,
        (r.esquerda, r.topo),
        (r.esquerda + r.largura, r.topo + r.altura),
        (0, 255, 0),
        2,
    )
    cv2.putText(
        tela,
        "SUA BARRA DE HP",
        (r.esquerda, max(14, r.topo - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 0),
        1,
    )
    # A gravacao vai toda pelo auxiliar. Era aqui que morava o SEGUNDO ponto de
    # escrita do modulo, e ter dois foi o que permitiu os dois ignorarem o erro
    # em silencio. O nome da funcao de escrita nao e citado aqui de proposito:
    # o teste estrutural conta as ocorrencias no texto do modulo, e uma mencao
    # solta em comentario o derrubaria sem que houvesse gravacao nenhuma.
    return _gravar_conferencia(tela)


def _texto_final_do_solo(caminho: Path | None) -> None:
    """Fecha o modo solo dizendo a verdade sobre a conferencia.

    Vive fora do `main()` para poder ser testada: a frase "CONFIRA a imagem"
    saia incondicionalmente e com o nome do arquivo escrito a mao no codigo,
    entao ela aparecia igualzinha mesmo quando nada tinha sido gravado.
    """
    if caminho is not None:
        print()
        print(f"CONFIRA {caminho}")
        print("antes de confiar nesta calibracao.")
        print("Se o retangulo nao estiver na SUA barra, a busca pegou a barra")
        print("do alvo selecionado — deixe o alvo em branco e rode de novo.")
        return

    print()
    print("A conferencia visual NAO aconteceu: ninguem olhou o retangulo.")
    # O alerta abaixo ja valia antes; sem imagem ele vale MAIS, porque virou o
    # unico aviso restante sobre o modo de erro mais provavel desta busca.
    print("Isso deixa em aberto o risco de sempre: a busca pega a barra MAIS A")
    print("ESQUERDA, e a barra do alvo selecionado tambem qualifica. Se voce")
    print("estava com alvo na tela, deixe o alvo em branco e rode de novo.")


def calibrar_so_a_propria_barra(titulo: str | None = None):
    """Calibra SO a sua barra, para quem esta jogando sozinho.

    O caminho normal deduz tudo a partir da party window: ela da a posicao, o
    passo entre membros, o icone de classe. Sem party nao ha nada disso, e a
    calibracao inteira desistia — inclusive a parte que so depende de VOCE.

    Isso tornava o modo solo inutilizavel para quem precisasse recalibrar, que
    e exatamente quem mais precisa dele: o usuario moveu a barra na UI, a
    regiao gravada virou grama, e o unico jeito de consertar era arrumar uma
    party emprestada.

    O que sai daqui e uma calibracao PARCIAL e honesta sobre isso: barra
    propria e nome, sem party window. O scanner roda com ela em `--solo`, e
    quando o usuario voltar a jogar em grupo basta rodar o calibrar normal.
    """
    janelas = listar_janelas_do_jogo()
    if titulo:
        janelas = [j for j in janelas if j == titulo]
    if not janelas:
        print("  Nenhuma janela do jogo aberta.")
        return None, None
    if len(janelas) > 1:
        print("  Ha mais de uma janela do jogo aberta:")
        for j in janelas:
            print(f'    --janela "{j}"')
        print("  Diga qual e a sua com --janela.")
        return None, None

    alvo = janelas[0]
    print(f"  Lendo a janela {alvo!r}...")
    try:
        hwnd = achar_janela(alvo)
        ox, oy = origem_da_janela(hwnd)
        fonte = JanelaSource(alvo, Regiao(ox, oy, 1, 1))
    except Exception as erro:  # noqa: BLE001
        print(f"  Nao consegui ler a janela: {erro}")
        return None, None

    try:
        import time

        time.sleep(0.3)  # a WGC empurra frames; dar tempo do primeiro chegar
        pixels = fonte.capturar_completo()
    finally:
        fonte.fechar()

    if pixels is None:
        print("  Nenhum frame chegou da janela.")
        return None, None

    barra = achar_barra_do_proprio(pixels, (0, 0))
    if barra is None:
        print("  Nao achei a sua barra de HP nesta janela.")
        print("  Ela esta visivel? A UI do jogo pode estar escondida (Alt+Z).")
        return None, None

    print(f"  Barra encontrada em ({barra.esquerda},{barra.topo}), "
          f"{barra.largura}x{barra.altura}")

    # PARTIMOS DA CALIBRACAO QUE JA EXISTE, e nao de valores inventados.
    #
    # Os limiares de cor foram medidos na tela DESTE usuario, sob o Gamma dele.
    # Recriar do zero significaria chutar HSV, e o proprio projeto proibe isso:
    # sob Gamma=1.16 os valores certos sao desconheciveis a priori. Aqui so
    # trocamos o que o modo solo sabe: a janela, a barra e o nome.
    if not ARQUIVO_CALIBRACAO.exists():
        print()
        print("  Nao existe calibracao anterior neste projeto.")
        print("  O modo solo AJUSTA uma calibracao que ja existe — ele nao")
        print("  consegue deduzir os limiares de cor sozinho, porque eles")
        print("  dependem do Gamma da sua tela e saem da party window.")
        print()
        print("  Rode o calibrar.bat normal UMA vez, com party na tela.")
        print("  Depois disso o --solo resolve sozinho para sempre.")
        return None, None

    cal = Calibracao.carregar(ARQUIVO_CALIBRACAO)
    anterior = cal.hp_proprio
    cal.janela = alvo
    cal.hp_proprio = barra
    if " - " in alvo:
        cal.nome_proprio = alvo.split(" - ")[0].strip()

    if anterior and (anterior.esquerda, anterior.topo) != (barra.esquerda, barra.topo):
        print(f"  (antes estava em ({anterior.esquerda},{anterior.topo}) — "
              f"voce moveu a barra)")
    return cal, pixels


class MiraNaoResolvida(Exception):
    """A mira nao resolveu para exatamente UMA janela do jogo.

    A mensagem que esta excecao carrega e PRONTA PARA O USUARIO: quem a captura
    so imprime e devolve 1. Nada de traceback — a ferramenta e disparada por um
    clique no `calibrar.bat`, e um traceback ali nao ensina nada a ninguem.
    """


def escolher_janela_do_jogo(
    janelas: list[str], pedido: str | None, personagem: str | None
) -> str | None:
    """Qual das janelas do jogo a calibracao deve ler. `None` = nao ha mira.

    FUNCAO PURA: a lista de titulos ENTRA por parametro e nao ha chamada Win32
    aqui dentro. E o que permite testar as quatro recusas com o jogo fechado.

    `pedido` e `personagem` NAO TEM VALOR PADRAO de proposito. E a prova
    estrutural de que nenhum nome de personagem esta escrito neste arquivo:
    sem valor padrao nao existe onde um se esconder. Um `"Yazalaque"` aqui
    estaria errado para qualquer outra pessoa que usasse o projeto.

    PRECEDENCIA: `pedido` (o `--janela` da linha de comando, TITULO EXATO)
    vence `personagem` (a chave do `config.toml`, NOME DO PERSONAGEM). O
    `--janela` continua com semantica de titulo exato porque `--solo` e
    `--tiat` ja comparam `j == titulo`: dar ao mesmo argumento um segundo
    significado dentro da mesma ferramenta seria pior que a assimetria.

    A comparacao por personagem IGNORA A CAIXA, depois de `strip`. O servidor
    nao permite dois personagens cujos nomes so diferem em caixa, entao ignorar
    a caixa nao pode criar ambiguidade que ja nao existisse — e recusar um
    `yazalaque` digitado em minusculas seria crueldade sem ganho.

    OS DOIS AUSENTES DEVOLVEM `None`: sem mira nao ha o que recusar. A recusa
    fechada so existe quando alguem PEDIU um alvo.

    ZERO OU DUAS OU MAIS JANELAS CASANDO LEVANTA. Escolher uma das duas seria
    reinventar o `_tentar_pelas_janelas_do_jogo` ("a primeira que funcionar")
    dentro da propria mira — e nunca cair para a varredura do desktop, que e
    exatamente o defeito que a mira existe para fechar.
    """
    pedido = (pedido or "").strip() or None
    personagem = (personagem or "").strip() or None

    if pedido is None and personagem is None:
        return None

    alvo = pedido or personagem

    # (a) NENHUMA JANELA DO JOGO. Listar o vazio nao diz nada; perguntar diz.
    if not janelas:
        raise MiraNaoResolvida(
            f"Pedi para mirar '{alvo}', mas nao ha nenhuma janela do XM "
            f"Essence aberta.\n"
            f"  O jogo esta aberto?"
        )

    if pedido is not None:
        casadas = [j for j in janelas if j == pedido]
    else:
        procurado = personagem.casefold()
        casadas = [
            j
            for j in janelas
            if (nome_do_personagem(j) or "").strip().casefold() == procurado
        ]

    if len(casadas) == 1:
        return casadas[0]

    # (c) O TITULO PEDIDO NAO EXISTE. Frase propria porque o `--janela` compara
    # titulo INTEIRO: dizer "personagem" aqui mandaria o usuario conferir a
    # grafia do nick quando o que falta e o sufixo " - XM Essence".
    if not casadas and pedido is not None:
        raise MiraNaoResolvida(
            f"Nao existe janela do jogo com o titulo exato '{pedido}'.\n"
            f"  Janelas do jogo abertas agora:\n"
            f"{_linhas_de_janela(janelas)}"
            f"{_nota_de_login(janelas)}"
        )

    # (b) HA JANELAS, NENHUMA E DESSE PERSONAGEM.
    if not casadas:
        raise MiraNaoResolvida(
            f"Nenhuma janela do jogo e do personagem '{personagem}'.\n"
            f"  Janelas do jogo abertas agora:\n"
            f"{_linhas_de_janela(janelas)}"
            f"{_nota_de_login(janelas)}"
        )

    # (d) DUAS OU MAIS CASANDO. Escolher uma seria a "primeira que funcionar".
    raise MiraNaoResolvida(
        f"'{alvo}' casa mais de uma janela do jogo, e eu nao tenho como "
        f"escolher por voce:\n"
        f"{_linhas_de_janela(casadas)}\n"
        f"  Desambigue com --janela, ou feche o cliente que nao interessa."
    )


def _linhas_de_janela(janelas: list[str]) -> str:
    """As janelas, uma por linha, com o argumento pronto para copiar.

    Mesmo formato de `calibrar_so_a_propria_barra`: o usuario nao tem de
    redigitar um titulo que leu numa mensagem de erro — ele copia a linha.
    """
    return "\n".join(f'    --janela "{j}"' for j in janelas)


def _nota_de_login(janelas: list[str]) -> str:
    """Diz que ha cliente na TELA DE LOGIN, quando ha. Vazio quando nao ha.

    Sem esta nota a recusa mente por omissao: ela diz "nao achei essa janela"
    quando a janela esta ali, e do jogo, e so nao tem personagem no titulo
    ainda — jogando o titulo e `Personagem - XM Essence`, no login ele COLAPSA
    para `XM Essence`. O usuario ficaria conferindo a grafia do nick contra um
    cliente que nem entrou no mundo.
    """
    if not any(esta_na_tela_de_login(j) for j in janelas):
        return ""
    return (
        "\n  Ha cliente na TELA DE LOGIN: nesse estado o titulo nao traz "
        "personagem\n  nenhum. Entre no mundo com o personagem e rode de novo."
    )


def capturar_a_janela_mirada(titulo: str) -> tuple[np.ndarray, int, int]:
    """O frame da janela mirada, e a origem dela em coordenadas de desktop.

    DEVOLVE A MESMA TRINCA QUE `capturar_tela()`: `(pixels, ox, oy)`. E isso
    que a torna um DROP-IN no unico ponto de captura de `main()` — a conta
    `origem = (jx - ox, jy - oy)`, o `party_window_na_janela` e os recortes de
    assinatura continuam valendo sem uma linha de edicao, porque nenhum deles
    sabe (nem precisa saber) de onde os pixels vieram. O contrato ja esta
    provado em campo por `_tentar_pelas_janelas_do_jogo`, que usa exatamente
    esse par.

    Ler a janela POR DENTRO tambem enxerga por baixo de outro programa que
    esteja por cima — mas nao por baixo da UI do proprio jogo, que e desenhada
    por ele.
    """
    try:
        hwnd = achar_janela(titulo)
        ox, oy = origem_da_janela(hwnd)
        fonte = JanelaSource(titulo, Regiao(ox, oy, 1, 1))
    except MiraNaoResolvida:
        raise
    except Exception as erro:  # noqa: BLE001
        # SEM TRACEBACK: a causa mais provavel aqui e janela minimizada, que e
        # o erro que o usuario comete com mais frequencia. Deixar essa subir
        # crua faria a mensagem mais comum de todas sair como pilha de chamada.
        raise MiraNaoResolvida(
            f"Nao consegui ler a janela '{titulo}': {erro}"
        ) from erro

    try:
        time.sleep(0.6)  # deixa chegar um frame de verdade
        pixels = fonte.capturar_completo()
    finally:
        fonte.fechar()

    if pixels is None or pixels.size == 0:
        raise MiraNaoResolvida(
            f"Nenhum frame utilizavel chegou de '{titulo}'.\n"
            "  A janela esta minimizada? Janela minimizada nao produz frame — "
            "nenhuma API do Windows contorna isso."
        )

    return pixels, ox, oy


def _tentar_pelas_janelas_do_jogo() -> Calibracao | None:
    """Procura a party window lendo cada janela do jogo por dentro.

    Serve para quando algo esta cobrindo a party window na tela: a captura por
    janela ve o jogo por baixo do que estiver em cima.
    """
    janelas = listar_janelas_do_jogo()
    if not janelas:
        return None

    print()
    print("Nada achado no desktop — outra JANELA pode estar por cima.")
    print("Tentando ler as janelas do jogo por dentro...")
    print("(isto enxerga atras de outros programas, mas NAO atras da UI")
    print(" do proprio jogo: inventario e ficha sao desenhados por ele)")
    print()

    for titulo in janelas:
        print(f"  {titulo}")
        try:
            hwnd = achar_janela(titulo)
            ox, oy = origem_da_janela(hwnd)
            # A regiao aqui e irrelevante: usamos o frame completo, porque
            # ainda nao sabemos onde a party window esta — e o que vamos achar.
            fonte = JanelaSource(titulo, Regiao(ox, oy, 1, 1))
        except Exception as erro:
            print(f"    nao consegui ler: {erro}")
            continue

        try:
            import time

            time.sleep(0.6)  # deixa chegar um frame de verdade
            completo = fonte.capturar_completo()
        finally:
            fonte.fechar()

        if completo is None or completo.size == 0:
            print("    nenhum frame utilizavel")
            continue

        print(f"    janela lida: {completo.shape[1]}x{completo.shape[0]}")
        cal = calibrar_automatico(completo, ox, oy)
        if cal is not None:
            cal.janela = titulo
            return cal

    return None


def calibrar_tiat(titulo: str | None = None) -> int:
    """Marca, na janela do jogo, o chat e/ou o texto do alvo para o Tiat.

    Nao existe posicao universal para essas partes do HUD. A selecao manual e
    curta e pode ser feita com qualquer alvo; o OCR so procura por ``Tiat``
    depois, quando o scanner esta rodando.
    """
    try:
        cal = Calibracao.carregar(ARQUIVO_CALIBRACAO)
    except Exception as erro:  # a ferramenta precisa explicar sem traceback
        print(f"Nao consegui abrir a calibracao existente: {erro}")
        return 1

    alvo = titulo or cal.janela
    if not alvo:
        janelas = listar_janelas_do_jogo()
        if len(janelas) != 1:
            print("Nao sei qual janela do jogo calibrar para o Tiat.")
            print("Use: python -m l2scanner.calibrar --tiat --janela \"TITULO\"")
            return 1
        alvo = janelas[0]

    try:
        fonte = JanelaSource(alvo, Regiao(0, 0, 1, 1))
        time.sleep(0.3)
        pixels = fonte.capturar_completo()
    except Exception as erro:  # noqa: BLE001 - borda da ferramenta interativa
        print(f"Nao consegui ler a janela {alvo!r}: {erro}")
        return 1
    finally:
        if "fonte" in locals():
            fonte.fechar()

    if pixels is None or pixels.size == 0:
        print("Nenhum frame utilizavel chegou da janela. Ela esta minimizada?")
        return 1

    print("1/2 — marque as linhas do CHAT onde aparece o anuncio de Tiat.")
    print("      ENTER confirma; ESC deixa este sinal desligado.")
    chat = _selecionar_regiao(
        pixels, "Tiat: chat", "Arraste somente sobre as linhas do chat."
    )
    print("2/2 — marque APENAS o NOME do alvo selecionado (nao a barra inteira).")
    print("      ENTER confirma; ESC deixa este sinal desligado.")
    alvo_regiao = _selecionar_regiao(
        pixels, "Tiat: alvo", "Arraste somente sobre o texto do nome do alvo."
    )
    if chat is None and alvo_regiao is None:
        print("Nenhuma regiao marcada; a calibracao anterior foi mantida.")
        return 1

    cal.janela = alvo
    cal.tiat_chat = Regiao(*chat) if chat is not None else None
    cal.tiat_alvo = Regiao(*alvo_regiao) if alvo_regiao is not None else None
    cal.salvar(ARQUIVO_CALIBRACAO)

    conferencia = pixels.copy()
    for regiao, texto, cor in (
        (cal.tiat_chat, "TIAT CHAT", (0, 255, 255)),
        (cal.tiat_alvo, "TIAT ALVO", (0, 255, 0)),
    ):
        if regiao is None:
            continue
        cv2.rectangle(
            conferencia,
            (regiao.esquerda, regiao.topo),
            (regiao.esquerda + regiao.largura, regiao.topo + regiao.altura),
            cor,
            2,
        )
        cv2.putText(
            conferencia, texto, (regiao.esquerda, max(16, regiao.topo - 6)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 1,
        )
    caminho = _gravar_conferencia(conferencia)
    print(f"Aviso de Tiat calibrado para {alvo!r}.")
    if caminho:
        print(f"CONFIRA {caminho}: amarelo = chat; verde = nome do alvo.")
    else:
        print("A calibracao foi salva, mas nao consegui gravar a imagem de conferencia.")
    return 0


# OS TREZE CAMPOS QUE A CALIBRACAO DE PARTY POSSUI.
#
# A LISTA E DE DONOS, E NAO DE PRESERVADOS, e a diferenca custou 13 moldes de
# glifo em 2026-08-30. Uma lista de PRESERVADOS exigiria que quem criasse o
# proximo campo opcional se lembrasse de inscreve-lo nela — e o esquecimento
# reproduz o incidente exatamente. Com uma lista de DONOS, o campo novo nasce
# PRESERVADO por omissao, porque o preservado sai por SUBTRACAO de
# `dataclasses.fields(Calibracao)`. O default de um campo desconhecido tem de
# ser SOBREVIVER, nunca ser apagado.
#
# OS OUTROS DOIS PONTOS DE GRAVACAO DESTE MODULO NAO PRECISAM DISTO, e nao
# devem ser "consertados" na proxima leitura: `calibrar_tiat` e o ramo `--solo`
# ja partem de `Calibracao.carregar(ARQUIVO_CALIBRACAO)` e ja preservam tudo o
# que nao e deles. So o caminho `--auto` / `--selecionar` montava a `Calibracao`
# do zero.
CAMPOS_DA_PARTY = frozenset(
    {
        "party_window",
        "ancora",
        "layout",
        "limiares_hp",
        "limiares_mp",
        "geometria_da_tela",
        "hp_proprio",
        "nome_proprio",
        "nomes",
        "assinaturas",
        "janela",
        "party_window_na_janela",
        "versao",
    }
)


def fundir_com_a_calibracao_em_disco(nova: Calibracao, caminho: Path) -> Calibracao:
    """Devolve `nova` com os campos que a party NAO possui vindos do disco.

    O INCIDENTE QUE ESTA FUNCAO EXISTE PARA IMPEDIR, medido em 2026-08-30: uma
    rodada de `calibrar.bat` apagou do `calibration.json` os 13 moldes de glifo,
    as 3 ancoras do painel, a grade de negociacao e o `mercado_limiar_de_glifo`
    — mais `banner_manutencao`, `tiat_chat` e `tiat_alvo`, pelo mesmo mecanismo.
    `calibrar_automatico` monta uma `Calibracao` DO ZERO, e o `salvar` grava o
    objeto inteiro: este caminho era load-mutate-save SEM o load. O arquivo e
    gitignored, entao nada disso volta por `git checkout`; o resgate foi manual.

    O lado do MERCADO ja tinha recebido este mesmo conserto (CR-04) — ver
    `calibrar_mercado.calibrar`, que carrega, muta so o que e seu, e grava. O
    lado da party ficou aberto porque nada o prendia.

    Arquivo inexistente e o estado legitimo da PRIMEIRA calibracao da vida:
    devolve `nova` sem dizer nada.
    """
    if not caminho.exists():
        return nova

    try:
        do_disco = Calibracao.carregar(caminho)
    except Exception as erro:  # noqa: BLE001
        # NAO PROPAGAR: esta e a rota de recuperacao do usuario. Se a party
        # parasse de gravar por causa de um arquivo ruim — corrompido, de outra
        # versao, travado por antivirus —, ele ficaria sem saida nenhuma.
        # Mas tambem NAO CALAR: seguir em silencio seria repetir o defeito
        # original com uma camada a mais por cima.
        print()
        print("AVISO: NAO CONSEGUI PRESERVAR o que ja estava no calibration.json.")
        print(f"  motivo: {erro}")
        print("  em risco: a calibracao de MERCADO (moldes de glifo, ancoras,")
        print("            grade e limiares) e as REGIOES DO TIAT (chat e alvo).")
        print("  a calibracao de party vai ser gravada mesmo assim — e o unico")
        print("  jeito de voce sair de um arquivo ruim. Se o mercado era")
        print("  importante, recalibre-o depois com calibrar-mercado.bat.")
        print()
        return nova

    for campo in fields(Calibracao):
        if campo.name in CAMPOS_DA_PARTY:
            continue
        setattr(nova, campo.name, getattr(do_disco, campo.name))
    return nova


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="l2scanner.calibrar",
        description="Descobre onde fica a party window na sua tela.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="detecta a party window sozinho (padrao)",
    )
    parser.add_argument(
        "--selecionar",
        action="store_true",
        help="voce marca a party window com o mouse",
    )
    parser.add_argument(
        "--solo",
        action="store_true",
        help=(
            "calibra SO a sua barra, para quem joga sozinho. "
            "Nao precisa de party na tela."
        ),
    )
    parser.add_argument(
        "--tiat",
        action="store_true",
        help=(
            "marca as regioes do chat e do alvo para o aviso de Tiat; "
            "nao altera a calibracao da party"
        ),
    )
    parser.add_argument(
        "--janela",
        help="titulo da janela do jogo (quando ha mais de uma aberta)",
    )
    parser.add_argument(
        "--eu",
        help="nome do SEU personagem (se omitido, sai do titulo da janela)",
    )
    parser.add_argument(
        "--nomes",
        help="nomes dos membros em ordem, separados por virgula "
        "(ex.: J4guar,Kaus,TioMad,Korzis)",
    )
    args = parser.parse_args()

    if _MODO_DPI.startswith("FALHOU"):
        print("AVISO: nao consegui declarar consciencia de DPI.")
        print("Se a escala da sua tela nao for 100%, as coordenadas sairao erradas.\n")

    if args.tiat:
        return calibrar_tiat(args.janela)

    if args.solo:
        print("Modo solo: procurando so a SUA barra de HP.")
        print()
        cal, pixels_da_janela = calibrar_so_a_propria_barra(args.janela)
        if cal is None:
            print()
            print("Calibracao solo nao concluida.")
            return 1
        if args.eu:
            cal.nome_proprio = args.eu.strip()
        cal.salvar(ARQUIVO_CALIBRACAO)
        print()
        print(f"Gravado em {ARQUIVO_CALIBRACAO}")
        print(f"  personagem : {cal.nome_proprio}")
        print(f"  barra de HP: {cal.hp_proprio}")
        print()
        # Este try/except NAO virou redundancia com o tratamento dentro de
        # _gravar_conferencia: ele cobre falha ao DESENHAR (um recorte fora da
        # tela, por exemplo), que acontece antes de existir imagem para gravar.
        # Sao dois modos de falha diferentes — nao remova achando que sobrou.
        try:
            conferencia = _conferencia_do_solo(cal, pixels_da_janela)
        except Exception as erro:  # noqa: BLE001
            print(f"  (nao consegui gerar a imagem de conferencia: {erro})")
            conferencia = None
        _texto_final_do_solo(conferencia)
        print()
        print("A party window da calibracao anterior foi mantida.")
        print("Rode o scanner com --solo. Quando voltar a jogar em grupo,")
        print("rode calibrar.bat normal com a party na tela.")
        return 0

    # A MIRA. Com dois clientes abertos, varrer o desktop deixa `calibrar_
    # automatico` agrupar barras dos DOIS e deduzir uma geometria que nao e de
    # nenhum — gravada calada. Mirar uma janela fecha isso na origem: os pixels
    # do outro cliente nunca entram na imagem analisada.
    #
    # O `try` cobre a RESOLUCAO e a CAPTURA de proposito: `capturar_a_janela_
    # mirada` tambem levanta `MiraNaoResolvida` (janela minimizada), e deixa-la
    # de fora faria a mensagem mais provavel de todas sair como traceback.
    alvo: str | None = None
    try:
        personagem = ler_personagem_do_jogo()
        # SO ENUMERA JANELAS QUANDO ALGUEM PEDIU ALVO. Sem este curto-circuito,
        # o caminho SEM mira passaria a fazer um EnumWindows que hoje nao
        # acontece aqui — mudando o comportamento de quem nao pediu nada.
        if args.janela or personagem:
            alvo = escolher_janela_do_jogo(
                listar_janelas_do_jogo(), args.janela, personagem
            )

        if alvo:
            de_onde = "--janela" if args.janela else "config.toml"
            print(f"Mirando a janela {alvo!r} (a mira veio de {de_onde}).")
            pixels, ox, oy = capturar_a_janela_mirada(alvo)
        else:
            print("Capturando a tela...")
            pixels, ox, oy = capturar_tela()
    except (MiraNaoResolvida, AgendaInvalida) as erro:
        print()
        print(erro)
        return 1

    print(f"  {pixels.shape[1]}x{pixels.shape[0]} a partir de ({ox},{oy})\n")

    if args.selecionar:
        cal = calibrar_selecionando(pixels, ox, oy)
    else:
        cal = calibrar_automatico(pixels, ox, oy)

        # O desktop mostra o que esta POR CIMA. Se o inventario, a ficha do
        # personagem ou qualquer painel estiver aberto sobre a party window, a
        # busca falha. Nesse caso olhamos a janela do jogo direto, que enxerga
        # por baixo — assim o usuario nao precisa fechar o que estava fazendo.
        #
        # COM MIRA ATIVA ISSO NAO RODA: ler a janela mirada por dentro ja E o
        # que o fallback faz. O que sobraria dele seria so a parte errada —
        # iterar todas as janelas aceitando a primeira que funcionar, que e o
        # defeito do desktop em miniatura e uma desobediencia direta a mira.
        if cal is None and alvo is None:
            cal = _tentar_pelas_janelas_do_jogo()

    if cal is None:
        print("\nCalibracao nao concluida.")
        print("Deixe a party window visivel na tela e tente de novo.")
        print("Se a deteccao automatica insistir em errar, use --selecionar.")
        return 1

    if args.nomes:
        cal.nomes = [n.strip() for n in args.nomes.split(",") if n.strip()]

    # Descobre a qual cliente esta party window pertence. Com duas instancias
    # abertas, adivinhar significaria vigiar o personagem errado.
    # Decide pela janela que contem o CENTRO da party window, nao o canto.
    # O canto e fragil: a deteccao automatica pode marca-lo alguns pixels a
    # esquerda da borda real, e com duas instancias lado a lado isso atribui a
    # party a instancia vizinha — foi o que aconteceu, o canto caiu 12 px
    # dentro da janela da Faerlina e a calibracao inteira saiu no cliente
    # errado.
    #
    # COM MIRA, O PALPITE GEOMETRICO NAO E CONSULTADO. Os pixels vieram do
    # frame daquela janela POR CONSTRUCAO, entao a dona e conhecida com
    # certeza, e adivinhar so pode subtrair certeza: com os dois clientes
    # SOBREPOSTOS — justamente o cenario que ler a janela por dentro resolve —
    # a party window achada tem coordenadas de desktop que caem dentro do
    # retangulo do cliente de CIMA, e `janela_que_contem` devolveria esse. Dali
    # para baixo `party_window_na_janela`, `nome_proprio` e o SCANNER EM
    # PRODUCAO herdariam o cliente errado, gravado calado.
    if alvo:
        cal.janela = alvo
    else:
        cal.janela = janela_que_contem(
            cal.party_window.esquerda + cal.party_window.largura // 2,
            cal.party_window.topo + cal.party_window.altura // 2,
        )

    # A barra do proprio personagem. Sem ela a morte do usuario nunca e
    # detectada — e ele e quem tem mais chance de morrer AFK, porque e o unico
    # sem outra pessoa olhando por ele.
    origem = (0, 0)
    if cal.janela:
        try:
            jx, jy = origem_da_janela(achar_janela(cal.janela))
            # `pixels` pode ser o desktop (offset ox,oy) ou o frame da janela
            # (ja com origem nela). Descobrimos por qual caminho viemos.
            origem = (jx - ox, jy - oy)
        except Exception:
            origem = (0, 0)
    propria = achar_barra_do_proprio(pixels, origem)
    if propria is not None:
        cal.hp_proprio = Regiao(
            esquerda=propria.esquerda,
            topo=propria.topo,
            largura=propria.largura,
            altura=propria.altura,
        )
    if args.eu:
        cal.nome_proprio = args.eu.strip()
    elif cal.janela and " - " in cal.janela:
        # o titulo da janela e "Personagem - XM Essence"
        cal.nome_proprio = cal.janela.split(" - ")[0].strip()


    # Guarda a party window TAMBEM em coordenadas relativas ao canto da janela
    # do jogo. As coordenadas de desktop so valem enquanto a janela nao se
    # mexer; as relativas acompanham o jogo se ele for arrastado.
    if cal.janela:
        try:
            jx, jy = origem_da_janela(achar_janela(cal.janela))
            cal.party_window_na_janela = Regiao(
                esquerda=cal.party_window.esquerda - jx,
                topo=cal.party_window.topo - jy,
                largura=cal.party_window.largura,
                altura=cal.party_window.altura,
            )
        except Exception:
            cal.party_window_na_janela = None

    # Grava a impressao digital visual do nome de cada membro. E isso que
    # permite dizer QUEM morreu quando a ordem da party muda — sem isso a
    # identidade viria da posicao da linha, e um alerta com o nome errado manda
    # a party socorrer a pessoa errada.
    if cal.nomes:
        pw = cal.party_window
        janela_px = pixels[
            pw.topo - oy : pw.topo - oy + pw.altura,
            pw.esquerda - ox : pw.esquerda - ox + pw.largura,
        ]
        assinaturas = []
        for indice, nome in enumerate(cal.nomes):
            regiao = cal.regiao_do_nome(indice)
            recorte = janela_px[
                regiao.topo : regiao.topo + regiao.altura,
                regiao.esquerda : regiao.esquerda + regiao.largura,
            ]
            if recorte.shape[0] != regiao.altura:
                print(f"  aviso: recorte do nome de {nome} caiu fora da janela")
                continue
            assinatura = criar_assinatura(nome, recorte)
            if assinatura.pixels_de_texto < 12:
                print(
                    f"  aviso: quase nenhum texto no recorte de {nome} — "
                    f"a linha {indice + 1} estava vazia?"
                )
                continue
            assinaturas.append(assinatura)
        cal.assinaturas = assinaturas

    # O SEAM: os tres caminhos de entrada (`--auto`, `--selecionar` e
    # `_tentar_pelas_janelas_do_jogo`) passam por aqui, porque os tres montam o
    # objeto pela mesma `calibrar_automatico`. Sem esta linha, gravar a party
    # apaga a calibracao de mercado e as regioes do Tiat.
    cal = fundir_com_a_calibracao_em_disco(cal, ARQUIVO_CALIBRACAO)
    cal.salvar(ARQUIVO_CALIBRACAO)

    pw = cal.party_window
    print(f"\nCalibracao gravada em {ARQUIVO_CALIBRACAO.name}")
    print(f"  party window : {pw.largura}x{pw.altura} em ({pw.esquerda},{pw.topo})")
    print(f"  barras       : {cal.layout.barra_largura}x{cal.layout.barra_altura}")
    print(f"  espacamento  : {cal.layout.passo} px entre membros")
    if cal.hp_proprio:
        r = cal.hp_proprio
        quem = cal.nome_proprio or "(nome nao identificado)"
        print(f"  voce         : {quem} — barra em ({r.esquerda},{r.topo}) {r.largura}x{r.altura}")
    else:
        print("  voce         : barra propria NAO encontrada — sua morte nao")
        print("                 sera detectada. A barra de HP do topo esta visivel?")
    if cal.janela:
        print(f"  janela       : {cal.janela}")
        if cal.party_window_na_janela:
            rel = cal.party_window_na_janela
            print(
                f"  dentro dela  : ({rel.esquerda},{rel.topo}) — o scanner "
                f"acompanha se voce arrastar o jogo"
            )
    else:
        print("  janela       : nao identificada — --janela precisara do titulo")
    if cal.nomes:
        print(f"  membros      : {', '.join(cal.nomes)}")
        if cal.assinaturas:
            print(
                f"  identidade   : {len(cal.assinaturas)} nome(s) gravados por "
                f"imagem — a ordem da party pode mudar sem errar o alerta"
            )
        else:
            print("  identidade   : nenhuma assinatura gravada; o nome virá da")
            print("                 ORDEM da lista, e mudar a ordem erra o alerta")
    else:
        print("  membros      : nenhum nome configurado")
        print("                 (use --nomes para os alertas dizerem quem morreu)")

    conferir_visualmente(cal, pixels, ox, oy)
    return 0


if __name__ == "__main__":
    sys.exit(main())
