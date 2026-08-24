"""Extracao pura: de um frame + calibracao para uma observacao.

Esta camada nao tem relogio, nao tem rede, nao abre arquivo e nao decide nada.
Ela so olha os pixels e responde "o que esta na tela agora". Quem decide se
isso e uma morte e o rastreador, na camada de cima.

Essa separacao e o que torna 30 segundos de debounce testaveis em 0,2 ms.

TRES DESCOBERTAS DA CALIBRACAO REAL que moldam o codigo aqui:

1. **A parte vazia da barra e transparente** — mostra o terreno do jogo, nao um
   fundo escuro fixo. O terreno muda (grama, neve, masmorra, lava). Por isso o
   discriminador principal e a SATURACAO, nao o matiz: barra cheia tem S~210,
   terreno tem S~75. Um chao avermelhado enganaria um teste so de matiz.

2. **"HP zerado" e "linha ausente" leem exatamente igual nas barras**: 0%.
   Distinguir os dois e a diferenca entre "Korzis morreu" e "Korzis saiu da PT".
   O desempate vem do icone de classe, que existe independente do HP.

3. **O vermelho da volta no circulo de matiz** — precisa de DUAS faixas
   combinadas (H<=12 ou H>=168). Uma faixa so e a razao classica de um leitor
   de vida "as vezes ler 0%", que aqui viraria alerta falso de morte.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np

from .calibracao import Calibracao, LimiaresDeCor
from .identidade import identificar
from .frames import Frame, Regiao, SaudeDoFrame


class EstadoDaLinha(Enum):
    """O que os pixels dizem sobre uma posicao de linha — sem interpretacao."""

    COM_MEMBRO = "com_membro"
    VAZIA = "vazia"


@dataclass(frozen=True)
class LeituraDeLinha:
    """O que foi lido numa posicao de linha da party window."""

    indice: int
    estado: EstadoDaLinha
    hp: float | None  # fracao 0.0-1.0, ou None se a linha esta vazia
    mp: float | None

    # Quem esta nesta linha, reconhecido pela imagem do nome. None quando nao
    # da para afirmar — e ai o rastreador cai para "Membro N", que e feio mas
    # honesto. Chutar um nome manda a party socorrer a pessoa errada.
    nome: str | None = None
    confianca_do_nome: float = 0.0

    @property
    def hp_zerado(self) -> bool:
        """HP em zero COM membro presente. Candidato a morte.

        Note que isto e diferente de `estado is VAZIA`: ali nao ha ninguem.
        """
        return self.estado is EstadoDaLinha.COM_MEMBRO and self.hp == 0.0


@dataclass(frozen=True)
class Observacao:
    """Tudo que um frame diz. Entrada do rastreador."""

    indice_do_frame: int
    ui_visivel: bool
    linhas: tuple[LeituraDeLinha, ...]
    hp_proprio: float | None = None

    @property
    def membros_presentes(self) -> int:
        return sum(1 for l in self.linhas if l.estado is EstadoDaLinha.COM_MEMBRO)


def _mascara_de_cor(hsv: np.ndarray, limiares: LimiaresDeCor) -> np.ndarray:
    """Marca os pixels que pertencem ao preenchimento da barra.

    Para o vermelho, `matiz_min` > `matiz_max` sinaliza a volta no circulo e as
    duas faixas sao combinadas com OU.
    """
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    if limiares.matiz_min > limiares.matiz_max:
        no_matiz = (h >= limiares.matiz_min) | (h <= limiares.matiz_max)
    else:
        no_matiz = (h >= limiares.matiz_min) & (h <= limiares.matiz_max)

    return no_matiz & (s >= limiares.saturacao_min) & (v >= limiares.valor_min)


def medir_barra(
    pixels: np.ndarray, regiao: Regiao, limiares: LimiaresDeCor
) -> float:
    """Fracao preenchida de uma barra, de 0.0 a 1.0.

    Mede a CORRIDA INICIAL de colunas cheias, a partir da esquerda — nao o total
    de pixels da cor. Duas razoes:

    - Nunca usar `findContours` aqui: com a barra em 0% nao existe contorno
      nenhum, e 0% e justamente o evento que o scanner existe para detectar.
    - Contar o total deixaria um efeito vermelho do jogo passando por cima da
      barra inflar a leitura. A corrida inicial so aceita preenchimento
      continuo desde a borda, que e como a barra realmente esvazia.

    Uma coluna conta como cheia quando a maioria das suas linhas casa a cor —
    mais robusto do que olhar so a linha do meio, e sobrevive ao antialiasing
    das bordas.
    """
    recorte = pixels[
        regiao.topo : regiao.topo + regiao.altura,
        regiao.esquerda : regiao.esquerda + regiao.largura,
    ]
    if recorte.size == 0:
        return 0.0

    hsv = cv2.cvtColor(recorte, cv2.COLOR_BGR2HSV)
    mascara = _mascara_de_cor(hsv, limiares)

    altura_real = mascara.shape[0]
    colunas_cheias = mascara.sum(axis=0) >= max(1, altura_real / 2)

    corrida = 0
    for cheia in colunas_cheias:
        if not cheia:
            break
        corrida += 1

    return corrida / regiao.largura if regiao.largura else 0.0


def _tem_contraste_de_icone(
    pixels: np.ndarray, regiao: Regiao, desvio_min: float, fracao_escura_min: float
) -> bool:
    """O icone de classe esta nesta posicao?

    O icone e um quadrado escuro com borda clara e simbolo branco: contraste
    alto e muitos pixels escuros. Terreno de jogo nao tem nem um nem outro.

    Medido na tela real do usuario:
      linha com membro : desvio 43-52, escuros 46-52%
      linha vazia      : desvio  9-10, escuros  0%

    A margem e enorme, sem zona cinzenta.
    """
    recorte = pixels[
        regiao.topo : regiao.topo + regiao.altura,
        regiao.esquerda : regiao.esquerda + regiao.largura,
    ]
    if recorte.size == 0:
        return False

    cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    return (
        float(cinza.std()) >= desvio_min
        and float((cinza < 60).mean()) >= fracao_escura_min
    )


def _bordas_da_barra_intactas(
    pixels: np.ndarray, layout, barra_x: int, barra_y: int, brilho_max: float
) -> bool:
    """A moldura da barra ainda esta la?

    A UI do jogo desenha uma linha escura nas duas pontas de cada barra. Essa
    linha e CHROME, nao preenchimento: ela existe igual com a barra cheia e com
    a barra vazia. So some quando outra janela do jogo — inventario, ficha do
    personagem, loja — e aberta por cima da party window.

    Isso resolve um falso positivo que derrubaria a confianca no scanner
    inteiro: com o inventario aberto, as barras ficam cortadas em ~2% e os
    quatro membros seriam anunciados como mortos ao mesmo tempo. Abrir o
    inventario e algo que se faz o tempo todo farmando.

    Medido na tela real: barra livre da V~8-11 nas duas pontas (cheia OU vazia,
    valores identicos); coberta pelo inventario da V~72-112.
    """
    fim = barra_y + layout.barra_altura

    esquerda = pixels[barra_y:fim, barra_x - 1] if barra_x >= 1 else None
    direita_x = barra_x + layout.barra_largura
    direita = (
        pixels[barra_y:fim, direita_x] if direita_x < pixels.shape[1] else None
    )

    for borda in (esquerda, direita):
        if borda is None or borda.size == 0:
            continue
        cinza = cv2.cvtColor(borda.reshape(1, -1, 3), cv2.COLOR_BGR2GRAY)
        if float(cinza.mean()) > brilho_max:
            return False

    return True


def _identificar_linha(pixels: np.ndarray, cal: Calibracao, indice: int):
    """Reconhece quem esta na linha, se houver assinaturas gravadas."""
    from .identidade import Casamento

    if not cal.assinaturas:
        return Casamento(nome=None, confianca=0.0)

    from .identidade import MARGEM_DE_BUSCA

    # A regiao de BUSCA e mais larga que a do molde, para o casamento poder
    # deslizar e absorver a coroa do lider.
    regiao = cal.regiao_do_nome(indice)
    esquerda = max(0, regiao.esquerda - MARGEM_DE_BUSCA)
    recorte = pixels[
        regiao.topo : regiao.topo + regiao.altura,
        esquerda : regiao.esquerda + regiao.largura,
    ]
    if recorte.shape[0] != regiao.altura or recorte.shape[1] < regiao.largura:
        return Casamento(nome=None, confianca=0.0)

    return identificar(recorte, cal.assinaturas)


def extrair(frame: Frame, cal: Calibracao) -> Observacao:
    """Le um frame inteiro. Funcao pura: mesmo frame, mesma saida, sempre."""
    layout = cal.layout
    pixels = frame.pixels

    # Frame doente nao produz leitura nenhuma. Um frame preto lido como "todas
    # as barras vazias" viraria um alerta de wipe total que nunca aconteceu.
    if frame.saude is not SaudeDoFrame.OK:
        return Observacao(
            indice_do_frame=frame.indice, ui_visivel=False, linhas=(), hp_proprio=None
        )

    # A ancora fica no TOPO da janela de proposito: a party window e ancorada em
    # cima e encolhe por baixo conforme a PT diminui. Uma ancora na borda
    # inferior sumiria sozinha quando a party passasse de 4 para 3 membros, e o
    # scanner entraria em modo cego sem motivo nenhum.
    ui_visivel = _tem_contraste_de_icone(
        pixels,
        cal.ancora,
        desvio_min=layout.ancora_desvio_min,
        fracao_escura_min=layout.ancora_escuros_min,
    )

    linhas: list[LeituraDeLinha] = []
    for i in range(layout.max_linhas):
        deslocamento = i * layout.passo

        regiao_icone = Regiao(
            esquerda=layout.icone_x,
            topo=layout.icone_y + deslocamento,
            largura=layout.icone_tamanho,
            altura=layout.icone_tamanho,
        )

        presente = _tem_contraste_de_icone(
            pixels,
            regiao_icone,
            desvio_min=layout.icone_desvio_min,
            fracao_escura_min=layout.icone_escuros_min,
        )

        if not presente:
            # Primeiro vao: a party window ACABA aqui. A regiao capturada e mais
            # alta que a janela de proposito, entao tudo abaixo deste ponto e
            # chat, minimapa ou terreno.
            #
            # Sair do laco (em vez de continuar) e uma correcao de CORRETUDE,
            # nao de desempenho. Uma linha de chat com contraste alto passa no
            # teste do icone, e ai `_bordas_da_barra_intactas` roda sobre lixo,
            # falha, e derruba `ui_visivel` do frame INTEIRO — cegando o scanner
            # por causa de uma linha que a propria logica ja considera
            # inexistente. `_truncar_no_primeiro_vao` descartava essa linha
            # depois, tarde demais: a cegueira ja tinha acontecido.
            #
            # Medido: 1 frame em 60 entrava em modo cego por isso, e cada um
            # custava ~4 frames de "[reajustando]" com todos os membros em
            # estado desconhecido.
            for j in range(i, layout.max_linhas):
                linhas.append(
                    LeituraDeLinha(
                        indice=j, estado=EstadoDaLinha.VAZIA, hp=None, mp=None
                    )
                )
            break

        regiao_hp = Regiao(
            esquerda=layout.barra_x,
            topo=layout.hp_y + deslocamento,
            largura=layout.barra_largura,
            altura=layout.barra_altura,
        )
        regiao_mp = Regiao(
            esquerda=layout.barra_x,
            topo=layout.mp_y + deslocamento,
            largura=layout.barra_largura,
            altura=layout.barra_altura,
        )

        # Se a moldura da barra sumiu, tem outra janela do jogo por cima e
        # a leitura nao vale nada. Nesse caso NAO tratamos a linha como morta
        # nem como ausente: derrubamos a visibilidade da UI inteira, porque se
        # parte da party window esta coberta nao da para confiar em nenhuma
        # parte dela. O portao de cegueira do rastreador cuida do resto.
        if not _bordas_da_barra_intactas(
            pixels, layout, layout.barra_x, layout.hp_y + deslocamento,
            layout.borda_v_max,
        ):
            ui_visivel = False

        # Identidade pela IMAGEM do nome, nao pela posicao da linha. A party
        # window compacta as linhas quando alguem sai, entao a posicao nao e
        # uma identidade — e so um lugar.
        casamento = _identificar_linha(pixels, cal, i)

        linhas.append(
            LeituraDeLinha(
                indice=i,
                estado=EstadoDaLinha.COM_MEMBRO,
                hp=medir_barra(pixels, regiao_hp, cal.limiares_hp),
                mp=medir_barra(pixels, regiao_mp, cal.limiares_mp),
                nome=casamento.nome,
                confianca_do_nome=casamento.confianca,
            )
        )

    linhas = _truncar_no_primeiro_vao(linhas)

    # Uma party window com ZERO membros nao existe: se ela esta na tela, tem
    # pelo menos uma linha. Ver a ancora e nao ver nenhum icone significa que a
    # calibracao aponta para o lugar errado — a party window foi arrastada, o
    # jogo foi redimensionado, ou a UI mudou.
    #
    # Sem esta regra, um deslocamento de 15 a 40 px passa pela ancora e faz
    # TODAS as linhas lerem como vazias — e o rastreador anunciaria que a party
    # inteira saiu. Quatro alertas falsos de uma vez, por causa de um frame
    # arrastado sem querer.
    if ui_visivel and not any(
        l.estado is EstadoDaLinha.COM_MEMBRO for l in linhas
    ):
        ui_visivel = False

    # A barra do proprio personagem vem de um recorte SEPARADO: ela fica no
    # topo da janela, longe da party window. Sem isso, a morte do usuario —
    # justamente quem esta AFK sem ninguem olhando — nunca seria detectada.
    hp_proprio = None
    recorte_proprio = frame.extras.get("hp_proprio")
    if recorte_proprio is not None and recorte_proprio.size:
        regiao_inteira = Regiao(
            esquerda=0,
            topo=0,
            largura=recorte_proprio.shape[1],
            altura=recorte_proprio.shape[0],
        )
        hp_proprio = medir_barra(recorte_proprio, regiao_inteira, cal.limiares_hp)

    return Observacao(
        indice_do_frame=frame.indice,
        ui_visivel=ui_visivel,
        linhas=tuple(linhas),
        hp_proprio=hp_proprio,
    )


def _truncar_no_primeiro_vao(
    linhas: list[LeituraDeLinha],
) -> list[LeituraDeLinha]:
    """Forca a VAZIA tudo que vem depois da primeira linha vazia.

    A party window nunca tem buraco: os membros ocupam as linhas de cima para
    baixo, sem pular. "Membro 3 presente, 4 ausente, 5 presente" e impossivel
    no jogo.

    Isso importa porque a regiao capturada e mais alta que a janela de
    proposito (para caber uma party cheia), e o excedente cai em cima do chat e
    do minimapa — que tem contraste alto e poderiam ser lidos como icone de
    classe. Sem essa regra, uma linha de chat colorida viraria um quinto membro
    fantasma, e depois a "saida" dele viraria um alerta que nunca aconteceu.
    """
    resultado: list[LeituraDeLinha] = []
    achou_vao = False

    for linha in linhas:
        if achou_vao:
            resultado.append(
                LeituraDeLinha(
                    indice=linha.indice,
                    estado=EstadoDaLinha.VAZIA,
                    hp=None,
                    mp=None,
                )
            )  # nome descartado junto: linha vazia nao tem dono
            continue

        if linha.estado is EstadoDaLinha.VAZIA:
            achou_vao = True

        resultado.append(linha)

    return resultado
