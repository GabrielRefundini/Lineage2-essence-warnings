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
from dataclasses import dataclass  # noqa: E402
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


def calibrar_selecionando(pixels: np.ndarray, ox: int, oy: int) -> Calibracao | None:
    """Usuario arrasta o mouse em volta da party window; o resto e deduzido."""
    altura, largura = pixels.shape[:2]
    escala = min(1.0, 1600 / largura)
    visao = (
        cv2.resize(pixels, None, fx=escala, fy=escala) if escala < 1.0 else pixels
    )

    print("\nArraste o mouse em volta da party window e tecle ENTER.")
    print("ESC cancela.\n")

    caixa = cv2.selectROI("Marque a party window", visao, showCrosshair=False)
    cv2.destroyAllWindows()

    if caixa[2] == 0 or caixa[3] == 0:
        print("Nada selecionado.")
        return None

    x, y, larg, alt = (int(valor / escala) for valor in caixa)
    recorte = pixels[y : y + alt, x : x + larg]

    # Dentro da area marcada, a deteccao automatica costuma acertar facil
    return calibrar_automatico(recorte, ox + x, oy + y)


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

    destino = RAIZ / "calibracao-conferencia.png"
    ampliado = cv2.resize(recorte, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(str(destino), ampliado)

    print(f"\nImagem de conferencia: {destino.name}")
    print("  amarelo = ancora da janela")
    print("  verde   = icone de classe (indicador de presenca)")
    print("  vermelho= barra de HP")
    print("  azul    = barra de MP")
    print("\nABRA essa imagem e confira se os retangulos batem com a party window.")
    print("Se nao baterem, rode de novo com --selecionar.")


def _conferencia_do_solo(cal: Calibracao, pixels: np.ndarray) -> None:
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
    destino = RAIZ / "calibracao-conferencia.png"
    cv2.imwrite(str(destino), tela)
    print(f"  Imagem de conferencia: {destino.name}")


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
        try:
            _conferencia_do_solo(cal, pixels_da_janela)
        except Exception as erro:  # noqa: BLE001
            print(f"  (nao consegui gerar a imagem de conferencia: {erro})")
        print()
        print("CONFIRA a imagem calibracao-conferencia.png antes de confiar.")
        print("Se o retangulo nao estiver na SUA barra, a busca pegou a barra")
        print("do alvo selecionado — deixe o alvo em branco e rode de novo.")
        print()
        print("A party window da calibracao anterior foi mantida.")
        print("Rode o scanner com --solo. Quando voltar a jogar em grupo,")
        print("rode calibrar.bat normal com a party na tela.")
        return 0

    print("Capturando a tela...")
    pixels, ox, oy = capturar_tela()
    print(f"  {pixels.shape[1]}x{pixels.shape[0]} a partir de ({ox},{oy})\n")

    if args.selecionar:
        cal = calibrar_selecionando(pixels, ox, oy)
    else:
        cal = calibrar_automatico(pixels, ox, oy)

        # O desktop mostra o que esta POR CIMA. Se o inventario, a ficha do
        # personagem ou qualquer painel estiver aberto sobre a party window, a
        # busca falha. Nesse caso olhamos a janela do jogo direto, que enxerga
        # por baixo — assim o usuario nao precisa fechar o que estava fazendo.
        if cal is None:
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