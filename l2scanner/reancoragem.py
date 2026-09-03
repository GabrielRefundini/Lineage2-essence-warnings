"""Reencontrar a party window sozinho quando ela e movida (ADVC-02).

O INCIDENTE, medido em campo em 2026-08-31: o usuario arrastou a party window
dentro do jogo e o scanner passou a ler os pixels errados. A unica saida era
ele PERCEBER e rodar `calibrar.bat` a mao.

Um deslocamento tem dois desfechos, os dois ruins:

  - GRANDE: a ancora some, `ui_visivel` cai e o scanner fica cego. Honesto, e
    sem alerta nenhum ate alguem perceber.
  - PEQUENO (15 a 40 px, ja medido e documentado em `visao.py:744`): passa pela
    ancora e faz TODAS as linhas lerem errado.

A REGRA QUE MANDA EM TODAS AS OUTRAS DESTE ARQUIVO
==================================================
UM REANCORAMENTO ERRADO E PIOR QUE FICAR CEGO. Cegueira e honesta: o usuario
nao recebe alerta e o console diz por que. Um reancoramento errado faz o
scanner ler COM CONFIANCA um lugar que nao e a party window, e ai ele mente --
"a party inteira saiu" a partir de grama. Toda duvida resolve em NAO reancorar,
e e por isso que este modulo tem oito criterios de recusa e um caminho de
adocao.

O QUE ESTE MODULO NAO FAZ, E POR QUE
====================================
1. NAO DETECTA NADA POR CONTA PROPRIA. Quem acha a party window nos pixels e
   `calibrar.calibrar_automatico`, a mesma funcao do `calibrar.bat --auto` que
   calibrou a maquina do usuario. Um segundo detector seria uma segunda verdade
   sobre a mesma tela.

2. NAO ADOTA A `Calibracao` INTEIRA que aquele detector devolve. Ver
   `adotar_geometria` -- e o WINDOWS #13.

3. NAO ESCREVE EM DISCO. A adocao vale para a SESSAO, em memoria. Persistir
   faria um reancoramento errado sobreviver ao reinicio, e o usuario perderia a
   calibracao boa sem ter pedido nada. O log diz, alto e uma vez, que rodar
   `calibrar.bat` e o que torna a mudanca permanente.

4. NAO OLHA A TELA. A busca le `fonte.capturar_completo()`, e a fonte do
   caminho `--janela` e uma `JanelaSource`, que captura POR TITULO
   (`window_name=` na `WindowsCapture`, ver `captura_janela.py`) e devolve
   sempre UMA janela. CONFERIDO NO CODIGO, e a conferencia importa: o usuario
   roda DOIS clientes, e uma varredura de desktop poderia achar a party window
   do OUTRO cliente e passar a vigiar a party errada em silencio. O gate
   `tests/test_reancoragem.py::test_o_modulo_nao_captura_a_tela` prende isso.
"""

from __future__ import annotations

import contextlib
import io
import logging
from dataclasses import replace

from .calibracao import Calibracao, LayoutDaParty
from .frames import Regiao

log = logging.getLogger("l2scanner")


# Quantas leituras cegas seguidas ate COMECAR a procurar a party window.
#
# A 1 Hz sao ~45 s, e o numero vem DEPOIS dos 30 de
# `TICKS_CEGO_PARA_SUGERIR_RECALIBRAR` de proposito: o aviso honesto ("nao
# estou vendo a party, pode ter sido arrastada") chega ao usuario primeiro, e a
# busca so entra se a cegueira insistir.
#
# Nao ha razao para varrer a janela a cada tick, e ha razao para nao varrer: as
# causas comuns de cegueira sao tela de loading, alt-tab e janela do jogo
# coberta pelo proprio inventario, e NENHUMA delas moveu a party window. Buscar
# cedo e buscar durante um loading, que e justamente quando o padrao de barras
# nao esta na tela e a busca so pode dar errado.
TICKS_CEGO_PARA_PROCURAR = 45

# De quantas em quantas leituras cegas repetir a busca depois da primeira.
#
# MEDIDO nesta maquina: `calibrar_automatico` custa 113 ms sobre um frame de
# 1920x1080 (`achar_barras_vermelhas` sozinho leva 91 ms). O frame da medicao e
# RUIDO SINTETICO, que e o pior caso para `connectedComponentsWithStats` -- a
# janela real tem menos componentes. A 1 Hz, buscar a cada tick gastaria 11% do
# orcamento do laco enquanto a cegueira durasse; a cada 15 ticks gasta 0,8%.
TICKS_ENTRE_BUSCAS = 15


# -- os criterios de plausibilidade -------------------------------------------

# Quanto o passo entre linhas pode diferir, em pixels.
#
# O passo e propriedade do SKIN da UI, nao da posicao: arrastar uma janela nunca
# reespaca o que esta dentro dela. Passo diferente nao e a party window movida,
# e outra coisa na tela (linhas de chat, barras de buff, a party do outro
# cliente). A folga de 2 px existe so para o tremor de um pixel no topo do
# componente conexo entre um frame e outro.
TOLERANCIA_DO_PASSO = 2

# Quanto a largura da barra pode diferir, em fracao.
#
# DUAS RAZOES, e a segunda e a que importa. (a) a barra nao muda de tamanho
# quando a janela e arrastada, entao largura muito outra e outro elemento.
# (b) `achar_barras_vermelhas` mede a parte PREENCHIDA da barra: uma party
# detectada com HP parcial devolve uma barra mais estreita do que a real, e
# adotar aquela geometria inflaria toda leitura de HP -- um membro com 90% leria
# 100%. Recusar mantem o scanner honesto, e a proxima deteccao com a party
# inteira de pe reancora sem custo nenhum.
TOLERANCIA_DA_LARGURA_DA_BARRA = 0.10

# Quanto a largura da JANELA pode diferir, em fracao.
#
# Mais frouxa que a da barra, e a assimetria e deliberada: a largura da janela
# inclui as margens que o detector inventa (12 px de cada lado) e o recorte do
# icone, entao uma calibracao feita com `--selecionar` (arrasto de mouse)
# emoldura a mesma party window com alguns pixels a mais ou a menos. A ALTURA
# nao e comparada pelo mesmo motivo invertido: o detector sempre monta uma
# janela alta o bastante para 8 linhas, enquanto um arrasto humano costuma
# abracar so a party de hoje -- comparar alturas recusaria toda calibracao
# manual por um motivo que nada tem a ver com a deteccao estar certa.
TOLERANCIA_DA_LARGURA_DA_JANELA = 0.20

# Os campos do layout que descrevem ONDE as coisas estao dentro da janela.
# Sao os unicos que a adocao troca. Ver `adotar_geometria`.
CAMPOS_DE_POSICAO = ("icone_x", "icone_y", "barra_x", "hp_y", "mp_y", "passo")


def linhas_que_cabem(janela: Regiao, layout: LayoutDaParty) -> int:
    """Quantas linhas de membro cabem INTEIRAS dentro desta janela.

    Conta pelo fundo da primeira linha (o mais baixo entre icone, HP e MP) mais
    os passos que ainda couberem. E o numero que diz quantos membros o scanner
    consegue enxergar com esta geometria.
    """
    if layout.passo <= 0:
        return 0

    fundo_da_primeira = max(
        layout.icone_y + layout.icone_tamanho,
        layout.hp_y + layout.barra_altura,
        layout.mp_y + layout.barra_altura,
    )
    if janela.altura < fundo_da_primeira:
        return 0

    return 1 + (janela.altura - fundo_da_primeira) // layout.passo


def motivo_para_recusar(
    antiga: Calibracao, nova: Calibracao, forma_do_frame: tuple[int, int]
) -> str | None:
    """Por que esta geometria NAO pode ser adotada. `None` = pode.

    Devolve texto e nao um booleano porque o motivo vai INTEIRO para o log: sem
    ele o usuario nao distingue "procurei e nao achei" de "achei e recusei", e
    as duas situacoes pedem coisas diferentes dele.

    `forma_do_frame` e `(altura, largura)` da janela do jogo que foi varrida.

    A ORDEM DOS CRITERIOS E DELIBERADA: do mais especifico para o mais geral,
    para que a primeira mensagem seja a mais util. O mais especifico de todos e
    "achei no mesmo lugar", que nao e falha nenhuma -- e o diagnostico de que a
    cegueira tem outra causa.
    """
    velha = antiga.party_window_na_janela
    if velha is None:
        # Sem a posicao dentro da JANELA nao ha referencial comum: a busca le a
        # janela por dentro e a `party_window` de desktop so vale enquanto o
        # jogo nao se mexer. Este e o caminho `mss`, onde reancorar exigiria
        # varrer a tela -- e varrer a tela pode achar o outro cliente.
        return (
            "esta calibracao nao guarda a posicao da party window DENTRO da "
            "janela do jogo (rode calibrar.bat para gravar)"
        )

    janela = nova.party_window
    layout_novo = nova.layout
    layout_velho = antiga.layout

    if (
        janela.esquerda == velha.esquerda
        and janela.topo == velha.topo
        and janela.largura == velha.largura
        and janela.altura == velha.altura
    ):
        return (
            "achei a party window no MESMO lugar em que a calibracao ja diz "
            "que ela esta, entao a cegueira tem outra causa (janela coberta, "
            "tela de loading ou alt-tab)"
        )

    if abs(layout_novo.passo - layout_velho.passo) > TOLERANCIA_DO_PASSO:
        return (
            f"o passo entre linhas deu {layout_novo.passo} px e a calibracao "
            f"tem {layout_velho.passo} px, entao isto nao e a party window "
            f"movida, e outra coisa na tela"
        )

    folga_da_barra = layout_velho.barra_largura * TOLERANCIA_DA_LARGURA_DA_BARRA
    if abs(layout_novo.barra_largura - layout_velho.barra_largura) > folga_da_barra:
        return (
            f"a barra de HP deu {layout_novo.barra_largura} px de largura e a "
            f"calibracao tem {layout_velho.barra_largura} px (pode ser outro "
            f"elemento, ou a party com HP parcial, que estreita a barra medida)"
        )

    folga_da_janela = velha.largura * TOLERANCIA_DA_LARGURA_DA_JANELA
    if abs(janela.largura - velha.largura) > folga_da_janela:
        return (
            f"a janela achada tem {janela.largura} px de largura e a calibrada "
            f"tem {velha.largura} px"
        )

    altura_do_frame, largura_do_frame = forma_do_frame
    if (
        janela.esquerda < 0
        or janela.topo < 0
        or janela.esquerda + janela.largura > largura_do_frame
        or janela.topo + janela.altura > altura_do_frame
    ):
        # Um retangulo que sai da janela do jogo nao produz leitura ruim: ele
        # produz FALHA_DE_CAPTURA em todo tick, para sempre. Adotar isso seria
        # trocar cegueira por cegueira permanente.
        return (
            f"a janela achada ({janela.largura}x{janela.altura} em "
            f"({janela.esquerda},{janela.topo})) nao cabe dentro da janela do "
            f"jogo ({largura_do_frame}x{altura_do_frame})"
        )

    # A COERENCIA DA MISTURA. A adocao mantem a FORMA antiga (largura e altura
    # das barras, tamanho do icone) e troca so as POSICOES, entao e preciso
    # conferir que a forma antiga cabe na janela nova. So a PRIMEIRA linha e
    # conferida aqui; o resto da altura e o criterio seguinte.
    fundo_da_primeira = max(
        layout_novo.icone_y + layout_velho.icone_tamanho,
        layout_novo.hp_y + layout_velho.barra_altura,
        layout_novo.mp_y + layout_velho.barra_altura,
    )
    direita = max(
        layout_novo.icone_x + layout_velho.icone_tamanho,
        layout_novo.barra_x + layout_velho.barra_largura,
    )
    if direita > janela.largura or fundo_da_primeira > janela.altura:
        return (
            f"a forma calibrada (icone de {layout_velho.icone_tamanho} px e "
            f"barra de {layout_velho.barra_largura} px) nao cabe na janela "
            f"achada ({janela.largura}x{janela.altura})"
        )

    cabem_agora = linhas_que_cabem(janela, _layout_adotado(antiga, nova))
    cabiam_antes = min(
        linhas_que_cabem(velha, layout_velho), layout_velho.max_linhas
    )
    if cabem_agora < cabiam_antes:
        # Menos linhas nao e degradacao aceitavel: os membros que sobram somem
        # do scanner EM SILENCIO, e sumir em silencio e a definicao do defeito
        # que este projeto inteiro evita.
        return (
            f"na janela achada cabem {cabem_agora} linha(s) de membro e a "
            f"calibracao lia {cabiam_antes}"
        )

    return None


def _layout_adotado(antiga: Calibracao, nova: Calibracao) -> LayoutDaParty:
    """A forma ANTIGA nas posicoes NOVAS."""
    return replace(
        antiga.layout,
        **{campo: getattr(nova.layout, campo) for campo in CAMPOS_DE_POSICAO},
    )


def adotar_geometria(antiga: Calibracao, nova: Calibracao) -> Calibracao:
    """A calibracao ANTIGA com a geometria NOVA. Nada mais muda.

    POR QUE NAO SE ADOTA O OBJETO INTEIRO -- WINDOWS #13, medido em campo em
    2026-08-30. `calibrar_automatico` monta uma `Calibracao` DO ZERO, e todo
    campo que a party window nao possui nasce `None` nela. Naquele dia isso
    custou ao usuario 13 moldes de glifo, 3 ancoras do painel de mercado, a
    grade de negociacao e dois limiares -- cada molde e um arrasto de mouse mais
    um rotulo digitado, e o arquivo e gitignored, entao nao ha `git checkout`
    que os traga de volta (o resgate foi manual). Aquilo aconteceu com o usuario
    tendo pedido uma calibracao; aqui nao haveria nem comando para culpar.

    ENTAO A ADOCAO E POR LISTA BRANCA, e a lista e curta:

      - `party_window_na_janela`: onde recortar dentro da janela do jogo
      - `ancora`: o retangulo de visibilidade, que e relativo a party window e
        portanto se muda junto com ela
      - as POSICOES do layout (`CAMPOS_DE_POSICAO`)

    O QUE FICA DA CALIBRACAO ANTIGA, E NAO POR ESQUECIMENTO:

      - assinaturas, nomes e `nome_proprio`: identidade nao e geometria
      - `limiares_hp` / `limiares_mp` e todos os limiares que moram DENTRO do
        layout (`icone_desvio_min`, `ancora_desvio_min`, `borda_v_max`): sao
        medicoes de cor e contraste da tela deste usuario
      - o recorte do nome (`nome_dx`, `nome_dy`, `nome_largura`, `nome_altura`):
        as assinaturas foram gravadas COM ele. O detector sempre devolve os
        defaults de hoje, e adota-los mudaria o recorte por baixo de assinaturas
        que continuam validas -- a versao para IDENTIDADE do WINDOWS #13
      - a FORMA das barras e do icone (`barra_largura`, `barra_altura`,
        `icone_tamanho`): ver `TOLERANCIA_DA_LARGURA_DA_BARRA`, a barra medida
        estreita quando a party esta com HP parcial
      - `max_linhas`: e politica de quantas linhas ler, nao geometria
      - `hp_proprio`, `banner_manutencao`, `tiat_*` e todo o bloco de mercado:
        outros recursos, outras regioes, medidos por outras ferramentas

    A `party_window` de DESKTOP tambem fica como estava, de proposito. A busca
    so acontece no caminho `--janela`, onde quem recorta e
    `party_window_na_janela`; a de desktop e um retrato de onde a janela do jogo
    estava no dia da calibracao, e so `calibrar.bat` pode refresca-la
    honestamente.

    A LISTA DE ASSINATURAS CONTINUA SENDO O MESMO OBJETO. `replace` copia
    referencias, e isso e requisito: o batismo e o aprendiz mutam essa lista em
    memoria (D-08), e uma copia faria o nome aprendido depois do reancoramento
    valer para uma calibracao que ninguem mais le.
    """
    return replace(
        antiga,
        party_window_na_janela=nova.party_window,
        ancora=nova.ancora,
        layout=_layout_adotado(antiga, nova),
    )


class Reancorador:
    """Procura a party window quando o scanner esta cego, e adota se puder.

    `detector` e `calibrar.calibrar_automatico` por padrao, e entra por
    parametro para o teste poder construir a situacao sem jogo aberto.

    O IMPORT DELE E TARDIO, dentro de `_detectar`, e isso e necessidade e nao
    estilo: `calibrar.py` roda `tornar_consciente_de_dpi()` NO IMPORT, e arrasta
    junto o `cv2` das ferramentas interativas. Importa-lo no topo faria todo
    arranque do scanner pagar por um caminho que so roda depois de 45 leituras
    cegas, e poria um efeito colateral de DPI numa ordem que ninguem controla.
    E o mesmo molde do import tardio de `texto_do_evento` em `sessao.py`.
    """

    def __init__(
        self,
        fonte,
        detector=None,
        ticks_para_procurar: int = TICKS_CEGO_PARA_PROCURAR,
        ticks_entre_buscas: int = TICKS_ENTRE_BUSCAS,
    ) -> None:
        self._fonte = fonte
        self._detector = detector
        self._ticks_para_procurar = ticks_para_procurar
        self._ticks_entre_buscas = max(1, ticks_entre_buscas)
        # Ja avisamos, nesta rodada de cegueira, que procuramos e nao adotamos?
        # Uma vez, e so uma: uma linha por busca durante um farm de tres horas e
        # a forma mais confiavel de o aviso nao ser lido. Volta a `False` quando
        # o scanner enxerga de novo, porque ai a proxima cegueira e outra
        # historia.
        self._ja_avisou_que_nao_adotou = False

    def talvez_reancorar(self, ticks_cego: int, cal: Calibracao) -> Calibracao | None:
        """Devolve a calibracao NOVA se reancorou, ou `None` se nao reancorou.

        Quando reancora, tambem reaponta a fonte: adotar a geometria e deixar a
        fonte recortando o retangulo antigo deixaria o scanner lendo um lugar
        com a regua de outro, que e pior do que nao reancorar.
        """
        if ticks_cego <= 0:
            self._ja_avisou_que_nao_adotou = False
            return None

        if ticks_cego < self._ticks_para_procurar:
            return None

        if (ticks_cego - self._ticks_para_procurar) % self._ticks_entre_buscas:
            return None

        completo = self._fonte.capturar_completo()
        if completo is None or completo.size == 0:
            self._avisar_que_nao_adotou(
                "nenhum frame utilizavel chegou da janela do jogo"
            )
            return None

        nova = self._detectar(completo)
        if nova is None:
            self._avisar_que_nao_adotou(
                "nao achei o padrao de barras da party window dentro da janela"
            )
            return None

        motivo = motivo_para_recusar(cal, nova, completo.shape[:2])
        if motivo is not None:
            self._avisar_que_nao_adotou(motivo)
            return None

        adotada = adotar_geometria(cal, nova)
        velha = cal.party_window_na_janela
        atual = adotada.party_window_na_janela
        # O QUE SAIU DAQUI EM 2026-09-02: "entao reiniciar o scanner volta ao
        # lugar antigo". E o desdobramento de "o calibration.json nao foi
        # tocado", que ficou: quem le o nome do arquivo ja sabe o que um
        # arquivo intocado significa, e a acao ("rode calibrar.bat") e a mesma
        # com ou sem a frase. O NOME DO ARQUIVO NAO PODE SAIR - ele e a unica
        # coisa aqui que diz ONDE a mudanca nao foi gravada.
        log.warning(
            "A party window MUDOU DE LUGAR dentro da janela do jogo: de "
            "%dx%d em (%d,%d) para %dx%d em (%d,%d), deslocamento de "
            "(%+d,%+d) px. Passei a ler no lugar novo, SO nesta sessao (o "
            "calibration.json nao mudou). Rode calibrar.bat para fixar.",
            velha.largura, velha.altura, velha.esquerda, velha.topo,
            atual.largura, atual.altura, atual.esquerda, atual.topo,
            atual.esquerda - velha.esquerda, atual.topo - velha.topo,
        )

        self._fonte.apontar_para(atual)
        self._ja_avisou_que_nao_adotou = False
        return adotada

    # -- interno ------------------------------------------------------------

    def _detectar(self, completo) -> Calibracao | None:
        """Roda o detector do `calibrar.bat --auto` sobre a janela do jogo.

        `ox=oy=0` de proposito: assim a geometria sai em coordenadas DA JANELA,
        que e o referencial de `party_window_na_janela` e o unico que sobrevive
        a arrastar o jogo pela tela.

        A CONVERSA DO DETECTOR VAI PARA O LOG EM DEBUG, e nao para o console. Ele
        foi escrito para uma ferramenta de terminal e imprime uma duzia de
        linhas por chamada; despejar isso no console do scanner a cada busca
        soterraria justamente os alertas que o usuario esta esperando.
        """
        detector = self._detector
        if detector is None:
            from .calibrar import calibrar_automatico  # import tardio, ver a classe

            detector = calibrar_automatico

        conversa = io.StringIO()
        try:
            with contextlib.redirect_stdout(conversa):
                nova = detector(completo, 0, 0)
        except Exception as erro:  # noqa: BLE001
            # Um scanner que morre calado e pior do que nenhum scanner, e esta
            # busca e um extra: ela nunca pode derrubar o laco que vigia a
            # party. O traceback fica em DEBUG, no arquivo de log.
            log.debug("A busca da party window explodiu", exc_info=True)
            self._avisar_que_nao_adotou(f"a busca falhou: {erro}")
            return None
        finally:
            for linha in conversa.getvalue().splitlines():
                log.debug("busca da party window: %s", linha)

        return nova

    def _avisar_que_nao_adotou(self, motivo: str) -> None:
        """UMA vez por rodada de cegueira. Ver `_ja_avisou_que_nao_adotou`.

        O aviso existe para o usuario distinguir "procurei e nao achei" de "nem
        procurei" -- sem ele, silencio e silencio, e as duas situacoes pedem
        coisas diferentes dele.
        """
        if self._ja_avisou_que_nao_adotou:
            return
        self._ja_avisou_que_nao_adotou = True
        log.warning(
            "Procurei a party window e NAO adotei nada: %s. Sigo cego. Se ela "
            "esta visivel na tela, rode calibrar.bat.",
            motivo,
        )
