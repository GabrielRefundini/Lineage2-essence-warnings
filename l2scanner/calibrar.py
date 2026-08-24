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
from .captura_janela import janela_que_contem  # noqa: E402
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
        "--nomes",
        help="nomes dos membros em ordem, separados por virgula "
        "(ex.: J4guar,Kaus,TioMad,Korzis)",
    )
    args = parser.parse_args()

    if _MODO_DPI.startswith("FALHOU"):
        print("AVISO: nao consegui declarar consciencia de DPI.")
        print("Se a escala da sua tela nao for 100%, as coordenadas sairao erradas.\n")

    print("Capturando a tela...")
    pixels, ox, oy = capturar_tela()
    print(f"  {pixels.shape[1]}x{pixels.shape[0]} a partir de ({ox},{oy})\n")

    if args.selecionar:
        cal = calibrar_selecionando(pixels, ox, oy)
    else:
        cal = calibrar_automatico(pixels, ox, oy)

    if cal is None:
        print("\nCalibracao nao concluida.")
        print("Deixe a party window visivel na tela e tente de novo.")
        print("Se a deteccao automatica insistir em errar, use --selecionar.")
        return 1

    if args.nomes:
        cal.nomes = [n.strip() for n in args.nomes.split(",") if n.strip()]

    # Descobre a qual cliente esta party window pertence. Com duas instancias
    # abertas, adivinhar significaria vigiar o personagem errado.
    cal.janela = janela_que_contem(cal.party_window.esquerda, cal.party_window.topo)

    cal.salvar(ARQUIVO_CALIBRACAO)

    pw = cal.party_window
    print(f"\nCalibracao gravada em {ARQUIVO_CALIBRACAO.name}")
    print(f"  party window : {pw.largura}x{pw.altura} em ({pw.esquerda},{pw.topo})")
    print(f"  barras       : {cal.layout.barra_largura}x{cal.layout.barra_altura}")
    print(f"  espacamento  : {cal.layout.passo} px entre membros")
    if cal.janela:
        print(f"  janela       : {cal.janela}")
    else:
        print("  janela       : nao identificada — --janela precisara do titulo")
    if cal.nomes:
        print(f"  membros      : {', '.join(cal.nomes)}")
    else:
        print("  membros      : nenhum nome configurado")
        print("                 (use --nomes para os alertas dizerem quem morreu)")

    conferir_visualmente(cal, pixels, ox, oy)
    return 0


if __name__ == "__main__":
    sys.exit(main())
