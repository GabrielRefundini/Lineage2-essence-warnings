"""Calibracao do World Exchange: ancoras, grade e moldes, sobre um frame GRAVADO.

    python -m l2scanner.calibrar_mercado --gravacao recordings/<pasta>
    python -m l2scanner.calibrar_mercado --frame caminho/do/frame.png

POR QUE UM MODULO NOVO, E NAO MAIS CODIGO EM `calibrar.py`
---------------------------------------------------------
Duas razoes, e nenhuma e estetica.

A primeira e um teste: `test_conferencia_gravada.py::
test_existe_um_unico_ponto_de_escrita_no_modulo` conta as ocorrencias de
gravacao de imagem no FONTE de `l2scanner.calibrar` e exige que todas estejam
dentro de `_gravar_conferencia`. Esse tripwire existe porque a gravacao
acontecia em dois pontos, os dois jogavam o retorno fora, e o calibrador
anunciava uma imagem que nao existia — o usuario conferia A IMAGEM VELHA e
validava uma calibracao errada. Aqui a regra e ainda mais simples: este modulo
nao grava imagem NENHUMA por conta propria. Ele importa `_gravar_conferencia`.

A segunda: `calibrar.py` ja tem mais de 900 linhas, e a mecanica que os dois
calibradores compartilham de verdade — arrastar um retangulo sobre uma captura
reescalada — foi EXTRAIDA para `calibrar._selecionar_regiao` em vez de copiada.
Duas copias da mesma mecanica de recorte envelheceriam separadas, e a que
envelhecesse pior produziria retangulos plausiveis na posicao errada.

POR QUE A FONTE E UM FRAME GRAVADO, E NUNCA A TELA AO VIVO (D-06)
-----------------------------------------------------------------
O painel do mercado so existe enquanto o usuario o mantem aberto, e marcar seis
ou oito retangulos com o mouse leva minutos. Sobre um frame gravado ele pode
errar, refazer e conferir quantas vezes quiser — e a mesma gravacao serve para
recalibrar depois de um patch do jogo, sem precisar reproduzir a cena.

O QUE ESTA FERRAMENTA RECUSA A FAZER
------------------------------------
- Imprimir valores para o usuario colar no `calibration.json`. O criterio 3 do
  ROADMAP e literalmente "sem editar JSON a mao": ela CARREGA a calibracao
  existente, muta so os campos de mercado e REGRAVA o arquivo inteiro.
- Gravar uma calibracao pela metade. Sem calibracao anterior ela recusa
  dizendo o que rodar antes, no tom de `calibrar.py --solo`.
- Aprovar uma watchlist com dois itens que se confundem. Um `+3 Bota X` lido
  como `+4 Bota X` nao acrescenta ruido a uma serie de precos: destroi a serie,
  porque o mesmo nome base valeu de 7,02 a 100,00 conforme o encanto no mesmo
  frame.
"""

from __future__ import annotations

# DPI PRIMEIRO, pelo mesmo motivo de `calibrar.py`: a ferramenta e o scanner
# precisam concordar sobre o que e um pixel.
from .dpi import tornar_consciente_de_dpi

_MODO_DPI = tornar_consciente_de_dpi()

import argparse  # noqa: E402
import sys  # noqa: E402
import tomllib  # noqa: E402
from dataclasses import dataclass, field  # noqa: E402
from pathlib import Path  # noqa: E402

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from .calibracao import Calibracao, CalibracaoInvalida  # noqa: E402
from .calibrar import (  # noqa: E402
    ARQUIVO_CALIBRACAO,
    RAIZ,
    _gravar_conferencia,
    _selecionar_regiao,
)
from .frames import Regiao  # noqa: E402
from .mercado_visao import (  # noqa: E402
    CASAMENTO_MINIMO_DA_ANCORA,
    AncoraDoPainel,
    ancoras_para_calibracao,
    casamento_da_ancora,
    molde_para_hex,
)

ARQUIVO_CONFIG = RAIZ / "config.toml"

# Acima disto, dois moldes da watchlist sao a MESMA COISA para o casamento e
# nenhum limiar os separa.
#
# HONESTIDADE SOBRE ESTE NUMERO: ao contrario de
# `mercado_visao.CASAMENTO_MINIMO_DA_ANCORA`, ele NAO e medido — nao poderia
# ser, porque a watchlist e do usuario e cada uma tem a sua matriz. Ele e uma
# POLITICA: com o pior inter-classe em 0.85, o limiar sugerido pela ferramenta
# fica em 0.925 e sobra uma margem de 0.075 para o casamento correto (que vale
# 1.0 por construcao, ja que o molde e recortado do proprio frame). Acima de
# 0.85 a margem some, e a ferramenta prefere mandar o usuario recortar mais
# largo a entregar uma serie de precos que se corrompe calada.
COLISAO_MAXIMA_ENTRE_TEMPLATES = 0.85

# Os deslocamentos MEDIDOS das ancoras, a partir da origem do painel (o canto
# superior esquerdo da faixa de titulo), na janela de 1720x1392 do usuario.
#
# Sao SUGESTOES pre-preenchidas, nao verdade: a ferramenta mostra cada regiao e
# o usuario confirma ou ajusta. Ver `mercado_visao.AncoraDoPainel` para o que
# cada uma e e para as duas que foram medidas e descartadas.
ANCORAS_SUGERIDAS = (
    ("titulo", 0, 0, 100, 28, "a faixa de titulo 'XM Market'"),
    ("botao_fechar", 494, -10, 60, 60, "o 'X' de fechar, canto superior direito"),
    ("canto_inf_dir", 494, 665, 60, 60, "a seta de rolagem, canto inferior direito"),
)


class MercadoNaoCalibravel(Exception):
    """A ferramenta nao tem como calibrar, e diz por que."""


# --------------------------------------------------------------------------
# Partes PURAS — sao elas que a suite consegue afirmar
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultadoDaConfusao:
    """A matriz de confusao entre os moldes, e o veredito dela."""

    aprovado: bool
    # `None` quando NENHUM par foi comparado. O tipo diz a diferenca entre
    # "medi e deu zero" e "nao medi nada" -- e o `0.0` que estava aqui apagava
    # justamente essa diferenca, imprimindo o valor mais tranquilizador
    # possivel para uma medicao que nao aconteceu.
    pior_score: float | None
    par_colidente: tuple[str, str] | None
    limiar_sugerido: float | None
    matriz: dict[tuple[str, str], float] = field(default_factory=dict)

    @property
    def rodou(self) -> bool:
        """Houve pelo menos UM par comparado.

        Com zero ou um molde a matriz nao tem par nenhum. Aprovar e correto --
        nao ha o que confundir --, mas AFIRMAR um pior score e um limiar
        derivado dele nao e: sao numeros inventados com cara de medidos, e o
        limiar vai para o `calibration.json`, onde a Fase 2 o le como verdade.
        """
        return bool(self.matriz)

    def explicar(self) -> str:
        if not self.rodou:
            return (
                "Matriz de confusao NAO RODOU: 0 pares para comparar. Com "
                "menos de dois moldes de nome nao ha o que confundir -- nenhum "
                "score foi medido e NENHUM limiar de template foi derivado. "
                "O limiar que ja estiver no calibration.json fica como esta."
            )
        if self.aprovado:
            return (
                f"Matriz de confusao APROVADA: o pior score entre dois itens "
                f"diferentes e {self.pior_score:.4f}. Limiar sugerido: "
                f"{self.limiar_sugerido:.4f}."
            )
        a, b = self.par_colidente or ("?", "?")
        return (
            f"Matriz de confusao RECUSADA: '{a}' e '{b}' casam "
            f"{self.pior_score:.4f} um com o outro — acima de "
            f"{COLISAO_MAXIMA_ENTRE_TEMPLATES}, nenhum limiar os separa.\n"
            f"  Conserto 1: recorte os dois mais LARGOS, ate incluir o pedaco "
            f"que os diferencia (o prefixo '+N ' e o fim do nome).\n"
            f"  Conserto 2: tire um dos dois da watchlist do config.toml.\n"
            f"Ler um pelo outro nao acrescenta ruido a serie de precos: "
            f"destroi a serie."
        )


def _alinhar(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Corta os dois ao menor tamanho comum, ancorado no canto superior esquerdo.

    O nome e desenhado alinhado a ESQUERDA dentro da coluna `Goods`, entao o
    canto superior esquerdo e o unico alinhamento com significado.

    Cortar torna a matriz MAIS conservadora, e isso e de proposito: comparar so
    o prefixo comum de `+3 Bota X` e `+4 Bota Xtra` sobe o score dos dois e
    aumenta a chance de recusa. Uma matriz que erra tem de errar para o lado de
    recusar.
    """
    altura = min(a.shape[0], b.shape[0])
    largura = min(a.shape[1], b.shape[1])
    return a[:altura, :largura], b[:altura, :largura]


def matriz_de_confusao(moldes: dict[str, np.ndarray]) -> ResultadoDaConfusao:
    """Todo molde contra todo molde, com a correlacao de posicao UNICA.

    A mesma tecnica de conjunto fechado ja MEDIDA em `identidade._correlacionar`
    (1.000 nos acertos contra 0.454 no melhor erro): comparar em UMA posicao, e
    nao tomar o maximo sobre deslocamentos, porque cada deslocamento e uma
    chance independente de um alvo errado achar alinhamento sortudo.

    Com menos de dois moldes nao ha o que confundir — aprova, mas NAO devolve
    pior score nem limiar: nao houve par nenhum para comparar, e `(1.0+0.0)/2`
    saia daqui como 0.5 direto para o `calibration.json`, apresentado como
    derivado da matriz. Um limiar de 0.5 para casamento de nome casa quase
    tudo — o pior inter-classe que este modulo TOLERA e 0.85. Numero fabricado
    com aparencia de medido, na ferramenta que grava a calibracao.
    """
    nomes = list(moldes)
    if len(nomes) < 2:
        return ResultadoDaConfusao(
            aprovado=True,
            pior_score=None,
            par_colidente=None,
            limiar_sugerido=None,
        )

    matriz: dict[tuple[str, str], float] = {}
    pior = -1.0
    par: tuple[str, str] | None = None
    for i, primeiro in enumerate(nomes):
        for segundo in nomes[i + 1 :]:
            a, b = _alinhar(moldes[primeiro], moldes[segundo])
            score = casamento_da_ancora(a, b)
            matriz[(primeiro, segundo)] = score
            if score > pior:
                pior, par = score, (primeiro, segundo)

    aprovado = pior <= COLISAO_MAXIMA_ENTRE_TEMPLATES
    return ResultadoDaConfusao(
        aprovado=aprovado,
        pior_score=pior,
        par_colidente=par,
        limiar_sugerido=(1.0 + pior) / 2 if aprovado else None,
        matriz=matriz,
    )


def derivar_grade(
    caixa_da_grade: tuple[int, int, int, int],
    caixa_da_primeira_linha: tuple[int, int, int, int],
    layout: str,
    origem_do_painel: tuple[int, int],
) -> dict:
    """Da area da lista e da PRIMEIRA linha sai a grade inteira.

    Marcar dez linhas com o mouse acumularia dez erros humanos; marcar uma e
    derivar o resto acumula um. Os numeros de campo (`SPIKE-RESPOSTAS.md` 1):
    10 linhas na grade de negociacao, passo de 45 px exatos; 9 na tela de busca,
    porque a caixa de busca come a altura de uma.

    `layout` e gravado junto porque NAO EXISTE "a grade": sao tres conjuntos de
    coluna diferentes, e ler a coluna errada com confianca corrompe a serie por
    um fator inteiro.

    A GRADE E GUARDADA EM DESLOCAMENTO, PELA MESMA RAZAO DAS ANCORAS. A primeira
    versao gravava `origem_x`/`origem_y` absolutos, direto do `selectROI`, e isso
    era um defeito silencioso: o painel ANDA 827x831 px (medido em
    `SPIKE-RESPOSTAS.md` 8). Uma calibracao feita com o painel num canto
    apontaria para o vazio assim que o usuario arrastasse — e como o leitor so
    nasce na Fase 2, ninguem descobriria ate a leitura sair errada com
    confianca.

    Encontrado quando o usuario comparou a propria tela ao vivo com o frame
    gravado e viu o painel em outro lugar. As ancoras ja guardavam
    deslocamento; a grade tinha recebido so a metade certa do tratamento.
    """
    gx, gy, glarg, galt = caixa_da_grade
    ox, oy = origem_do_painel
    _, _, _, altura_da_linha = caixa_da_primeira_linha
    if altura_da_linha <= 0:
        raise MercadoNaoCalibravel(
            "a primeira linha ficou com altura zero — remarque o retangulo"
        )
    linhas = max(1, galt // altura_da_linha)
    return {
        "layout": layout,
        "dx": int(gx - ox),
        "dy": int(gy - oy),
        "largura": int(glarg),
        "altura": int(galt),
        "altura_da_linha": int(altura_da_linha),
        "linhas_por_pagina": int(linhas),
    }


def conferir_o_frame(cal: Calibracao, pixels: np.ndarray) -> None:
    """O frame e mesmo uma JANELA COMPLETA desta calibracao?

    RECUSA ALTO em vez de medir a regiao errada calada — a mesma disciplina de
    `Calibracao.conferir_geometria`.

    O erro que isto pega e concreto e ja aconteceu no spike: gravar no modo
    party (recorte de ~174x522) em vez do modo janela. Marcar o painel do
    mercado dentro de um recorte de party window e impossivel, mas uma
    ferramenta descuidada aceitaria o arquivo e gravaria retangulos que nao
    apontam para nada.
    """
    if pixels is None or pixels.size == 0:
        raise MercadoNaoCalibravel("o frame nao pode ser lido (arquivo vazio?)")

    altura, largura = pixels.shape[:2]
    # So o TAMANHO da party window entra aqui, nunca a posicao dela: sem
    # `party_window_na_janela` a posicao esta em coordenadas de DESKTOP e nao
    # limita nada dentro da janela. O tamanho, sim, e a assinatura exata do
    # erro que isto pega — um frame gravado no modo party tem as dimensoes da
    # party window, e nao as da janela.
    referencia = cal.party_window_na_janela or cal.party_window
    if largura <= referencia.largura or altura <= referencia.altura:
        raise MercadoNaoCalibravel(
            f"este frame tem {largura}x{altura} — nao e maior que a party "
            f"window calibrada ({referencia.largura}x{referencia.altura}).\n"
            f"  Provavelmente ele foi gravado no modo party. Regrave com "
            f"--record-janela e use uma pasta de gravacao de JANELA COMPLETA."
        )


def carregar_calibracao(caminho: Path) -> Calibracao:
    """Carrega a calibracao que ja existe, ou explica o que rodar antes.

    Tom e forma copiados de `calibrar.py:643-652` (o modo solo), porque o
    problema e o mesmo: esta ferramenta AJUSTA uma calibracao existente. Ela nao
    sabe onde fica a party window, nem os limiares de cor, que dependem do Gamma
    da tela do usuario e sao desconheciveis a priori.
    """
    if not caminho.exists():
        raise MercadoNaoCalibravel(
            "Nao existe calibracao anterior neste projeto.\n"
            "  A calibracao de mercado ACRESCENTA campos a uma calibracao que\n"
            "  ja existe — ela nao sabe onde fica a sua party window nem os\n"
            "  limiares de cor da sua tela.\n\n"
            "  Rode o calibrar.bat UMA vez, com party na tela.\n"
            "  Depois disso o calibrar-mercado.bat resolve o resto."
        )
    try:
        return Calibracao.carregar(caminho)
    except CalibracaoInvalida as erro:
        raise MercadoNaoCalibravel(str(erro)) from erro


def navegar_e_escolher(quadros: list[Path], comeco: int) -> Path:
    """Deixa o usuario FOLHEAR a gravacao e escolher um frame limpo.

    MEDIDO EM CAMPO, 2026-08-28: o usuario rodou a ferramenta e caiu num frame
    "sujo com outras coisas sobrepondo o mercado". O padrao anterior era o frame
    do MEIO da pasta -- uma escolha arbitraria que nao tem como saber se ali
    havia uma tooltip, a marcacao de alvo ou a lista em transicao por cima do
    painel.

    Calibrar sobre um frame ocluido nasce torto de um jeito silencioso: os
    retangulos ficam gravados no `calibration.json` medindo a coisa errada, e o
    erro so aparece muito depois, como leitura ruim. E a mesma familia do
    incidente 27x -- oclusao parcial produzindo saida confiante e errada.

    A escolha e do OLHO do usuario de proposito. Nao da para pontuar oclusao
    aqui sem ja ter as ancoras, e as ancoras sao justamente o que esta sendo
    calibrado. Com a pessoa na frente da tela, folhear resolve sem precisar
    inventar heuristica.
    """
    indice = max(0, min(comeco, len(quadros) - 1))
    janela = "escolha um frame LIMPO  (D/A ou setas: navegar | ENTER: usar | ESC: cancelar)"

    print(chr(10) + "-" * 60)
    print("  ESCOLHA O FRAME")
    print("  Procure um em que o painel do mercado esteja INTEIRO e")
    print("  SEM NADA POR CIMA: sem tooltip, sem marcacao de alvo, sem")
    print("  a lista no meio de uma rolagem.")
    print("")
    print("    D  ou seta direita  -> proximo frame")
    print("    A  ou seta esquerda -> frame anterior")
    print("    W / S               -> pular de 10 em 10")
    print("    ENTER               -> usar este frame")
    print("    ESC                 -> cancelar sem gravar nada")
    print("-" * 60)

    # WINDOW_AUTOSIZE, nao WINDOW_NORMAL: esta janela existe para o usuario
    # VER se ha tooltip, marcacao de alvo ou rolagem por cima do painel, e uma
    # janela NORMAL nao se dimensiona pela imagem -- ela nasce no tamanho que o
    # Win32 resolver dar e espreme o frame dentro dele. MEDIDO nesta maquina
    # (cv2 4.14.0): imagem 1720x1392 numa janela NORMAL saiu 120x1440; em
    # AUTOSIZE sai 1720x1392 exatos. A 8% do tamanho ninguem enxerga tooltip
    # nenhuma, e o proposito inteiro da funcao vai junto. `moveWindow`
    # posiciona igual sobre AUTOSIZE, entao a janela continua nascendo onde o
    # usuario a encontra. `_reduzir_para_caber` ja garante que ela cabe.
    cv2.namedWindow(janela, cv2.WINDOW_AUTOSIZE)
    cv2.moveWindow(janela, 40, 40)
    try:
        while True:
            pixels = cv2.imread(str(quadros[indice]))
            if pixels is None:
                raise MercadoNaoCalibravel(
                    f"nao consegui decodificar {quadros[indice]}"
                )
            mostra = _reduzir_para_caber(pixels)
            etiqueta = f"{indice + 1}/{len(quadros)}  {quadros[indice].name}"
            cv2.putText(
                mostra, etiqueta, (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA,
            )
            cv2.putText(
                mostra, etiqueta, (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1, cv2.LINE_AA,
            )
            cv2.imshow(janela, mostra)

            tecla = cv2.waitKey(0) & 0xFF
            if tecla in (13, 10):  # ENTER
                cv2.destroyWindow(janela)
                for _ in range(5):
                    cv2.waitKey(1)  # deixa o HighGUI assentar
                print(f"  usando {quadros[indice].name}" + chr(10))
                return quadros[indice]
            if tecla == 27:  # ESC
                cv2.destroyWindow(janela)
                raise MercadoNaoCalibravel(
                    "escolha de frame cancelada -- nada foi gravado"
                )
            if tecla in (ord("d"), ord("D"), 83):
                indice = min(indice + 1, len(quadros) - 1)
            elif tecla in (ord("a"), ord("A"), 81):
                indice = max(indice - 1, 0)
            elif tecla in (ord("w"), ord("W"), 82):
                indice = min(indice + 10, len(quadros) - 1)
            elif tecla in (ord("s"), ord("S"), 84):
                indice = max(indice - 10, 0)
    finally:
        try:
            cv2.destroyWindow(janela)
        except cv2.error:
            pass


def _reduzir_para_caber(pixels: np.ndarray, largura_alvo: int = 1400) -> np.ndarray:
    """Encolhe so para o frame de janela completa caber num monitor."""
    altura, largura = pixels.shape[:2]
    if largura <= largura_alvo:
        return pixels.copy()
    escala = largura_alvo / largura
    return cv2.resize(
        pixels, (largura_alvo, int(altura * escala)), interpolation=cv2.INTER_AREA
    )


def escolher_frame(gravacao: Path | None, frame: Path | None, indice: int | None) -> Path:
    """Qual PNG vai ser calibrado.

    O padrao de `--gravacao` e o frame do MEIO, e nao o primeiro: as gravacoes
    do roteiro comecam com o usuario ainda posicionando a tela, entao o primeiro
    frame e o que tem menos chance de mostrar a cena pedida.
    """
    if frame is not None:
        if not frame.is_file():
            raise MercadoNaoCalibravel(f"nao encontrei o frame {frame}")
        return frame

    if gravacao is None:
        raise MercadoNaoCalibravel(
            "diga de onde ler: --gravacao <pasta> ou --frame <arquivo.png>"
        )
    if not gravacao.is_dir():
        raise MercadoNaoCalibravel(f"nao encontrei a pasta {gravacao}")

    quadros = sorted(gravacao.glob("frame_*.png"))
    if not quadros:
        raise MercadoNaoCalibravel(
            f"{gravacao} nao tem nenhum frame_*.png.\n"
            f"  Essa pasta e mesmo uma gravacao do --record-janela?"
        )
    escolhido = len(quadros) // 2 if indice is None else indice
    if not 0 <= escolhido < len(quadros):
        raise MercadoNaoCalibravel(
            f"--indice {escolhido} fora da faixa: a pasta tem "
            f"{len(quadros)} frames (0 a {len(quadros) - 1})"
        )
    # Um `--indice` explicito e uma escolha ja feita: respeita e nao folheia.
    if indice is not None:
        return quadros[escolhido]
    return navegar_e_escolher(quadros, escolhido)


def ler_watchlist(caminho: Path) -> list[str]:
    """Os itens que o usuario quer acompanhar, do `config.toml`.

    Lista vazia e um estado LEGITIMO, e nao um erro: da para calibrar as
    ancoras e a grade sem watchlist nenhuma, e a Fase 2 e que vai precisar dos
    moldes de nome. A ferramenta diz alto o que deixou de cortar.
    """
    if not caminho.exists():
        return []
    dados = tomllib.loads(caminho.read_text(encoding="utf-8"))
    itens = dados.get("mercado", {}).get("watchlist", [])
    return [str(item) for item in itens if str(item).strip()]


def desenhar_conferencia(
    pixels: np.ndarray, regioes: dict[str, tuple[int, int, int, int]]
) -> np.ndarray:
    """Desenha os retangulos por cima da captura, para o humano OLHAR.

    Numero conferindo com numero nao prova que a regiao esta no lugar certo.
    Ver a imagem prova. Mesmo argumento de `calibrar.conferir_visualmente`.
    """
    tela = pixels.copy()
    for nome, (x, y, largura, altura) in regioes.items():
        cv2.rectangle(tela, (x, y), (x + largura, y + altura), (0, 255, 0), 2)
        cv2.putText(
            tela, nome, (x, max(12, y - 6)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA,
        )
    return tela


def montar_ancoras(
    pixels: np.ndarray, caixas: dict[str, tuple[int, int, int, int]], origem: tuple[int, int]
) -> list[AncoraDoPainel]:
    """Recorta cada ancora do frame e converte a posicao em DESLOCAMENTO.

    Guardar deslocamento, e nao posicao absoluta, e o que permite mover todas as
    ancoras juntas quando o painel anda — e ele anda 827x831 px, medidos.
    """
    ox, oy = origem
    cinza = cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY)
    ancoras = []
    for nome, (x, y, largura, altura) in caixas.items():
        recorte = cinza[y : y + altura, x : x + largura]
        if recorte.size == 0:
            raise MercadoNaoCalibravel(
                f"a ancora '{nome}' ficou vazia — remarque o retangulo"
            )
        ancoras.append(
            AncoraDoPainel(nome=nome, dx=x - ox, dy=y - oy, molde=recorte.copy())
        )
    return ancoras


# --------------------------------------------------------------------------
# O fluxo interativo
# --------------------------------------------------------------------------


def _marcar(
    pixels: np.ndarray, titulo: str, instrucao: str
) -> tuple[int, int, int, int]:
    caixa = _selecionar_regiao(pixels, titulo, instrucao)
    if caixa is None:
        raise MercadoNaoCalibravel("selecao cancelada — nada foi gravado")
    return caixa


def _texto_final_da_conferencia(caminho: Path | None, arquivo: Path) -> None:
    """Fecha a calibracao de mercado dizendo a VERDADE sobre a conferencia.

    O defeito que isto conserta e o FUND-01 verbatim, do outro lado da parede.
    A linha final era `print("\nABRA a imagem de conferencia...")`, incondicional,
    com o retorno de `_gravar_conferencia` descartado. Mas aquela funcao devolve
    tres coisas diferentes:

    - o caminho padrao, quando gravou onde sempre grava;
    - um caminho ALTERNATIVO (`calibracao-conferencia-HHMMSS.png`), quando o
      arquivo de sempre estava travado -- o caso mais comum, porque a propria
      ferramenta manda o usuario abrir a imagem no visualizador de fotos e ele
      costuma deixar a imagem aberta;
    - `None`, quando nao gravou em lugar nenhum.

    Nos dois ultimos casos o usuario era mandado para
    `calibracao-conferencia.png`, que ou nao existe, ou E A IMAGEM DA CALIBRACAO
    ANTERIOR. Conferir a imagem velha e validar a calibracao nova: exatamente o
    desfecho que o docstring de abertura deste modulo diz ter matado.

    A honestidade extra que este caso exige, e que o modo solo nao exige: o
    `cal.salvar` JA RODOU quando chegamos aqui. Nao da para dizer so "a
    conferencia nao aconteceu" -- os retangulos estao gravados e ninguem os
    olhou, e o texto tem de dizer as duas coisas na mesma tela.

    Vive fora do `calibrar()` para poder ser testada sem mouse, no mesmo molde
    de `calibrar._texto_final_do_solo`.
    """
    if caminho is not None:
        print(f"\nABRA {caminho}")
        print("e confira se os retangulos verdes caem onde voce espera: a faixa")
        print("de titulo do painel, o X de fechar, a seta de rolagem, a area da")
        print("lista e a primeira linha.")
        return

    print("\nA CONFERENCIA VISUAL NAO ACONTECEU: nenhuma imagem foi gravada.")
    print(f"Os retangulos acima JA ESTAO em {arquivo.name} e NINGUEM os olhou.")
    # Nenhum nome de arquivo sai daqui, de proposito: e a mesma regra de
    # `calibrar._gravar_conferencia`. Um nome citado numa tela onde nao houve
    # gravacao e mais uma promessa vazia -- e pior, o arquivo de sempre
    # PROVAVELMENTE existe, de uma rodada anterior, entao o usuario o abriria.
    print("Se houver alguma imagem de conferencia na pasta, ela e de OUTRA")
    print("rodada e nao serve para conferir esta.")
    print("Feche o visualizador de fotos e rode de novo antes de confiar nisto.")


def calibrar(args: argparse.Namespace) -> int:
    arquivo = Path(args.calibracao) if args.calibracao else ARQUIVO_CALIBRACAO
    cal = carregar_calibracao(arquivo)

    caminho = escolher_frame(
        Path(args.gravacao) if args.gravacao else None,
        Path(args.frame) if args.frame else None,
        args.indice,
    )
    pixels = cv2.imread(str(caminho))
    if pixels is None:
        raise MercadoNaoCalibravel(f"nao consegui decodificar {caminho}")
    conferir_o_frame(cal, pixels)

    altura, largura = pixels.shape[:2]
    print(f"\nCalibrando o mercado sobre {caminho.name} ({largura}x{altura})")
    print("")
    print("  " + "-" * 58)
    print("  VAO ABRIR 5 JANELAS DE SELECAO, uma de cada vez, no CANTO")
    print("  SUPERIOR ESQUERDO do monitor principal.")
    print("")
    print("  Se nao ver a janela, ela pode estar ATRAS deste terminal")
    print("  ou no outro monitor: procure na barra de tarefas pelo")
    print("  nome que aparece abaixo.")
    print("")
    print("  Em cada uma: arraste o mouse e confirme com ENTER ou ESPACO.")
    print("  NAO feche no X -- fechar no X cancela e nada e gravado.")
    print("  " + "-" * 58)
    print("Abra o painel do World Exchange no frame antes de marcar as regioes.\n")

    # --- as ancoras ---
    caixas: dict[str, tuple[int, int, int, int]] = {}
    for nome, _dx, _dy, larg, alt, descricao in ANCORAS_SUGERIDAS:
        caixas[nome] = _marcar(
            pixels,
            f"Ancora: {nome}",
            f"Marque {descricao} (sugerido: {larg}x{alt}) e tecle ENTER.",
        )
    origem = (caixas["titulo"][0], caixas["titulo"][1])
    ancoras = montar_ancoras(pixels, caixas, origem)

    # --- a grade ---
    layout = args.layout
    caixa_grade = _marcar(
        pixels, "Grade", "Marque a AREA DA LISTA inteira e tecle ENTER."
    )
    caixa_linha = _marcar(
        pixels, "Primeira linha", "Marque a PRIMEIRA LINHA da lista e tecle ENTER."
    )
    grade = derivar_grade(caixa_grade, caixa_linha, layout, origem)

    # --- os moldes da watchlist ---
    watchlist = ler_watchlist(ARQUIVO_CONFIG)
    if not watchlist:
        print(
            "\nSem watchlist no config.toml ([mercado] watchlist = [...]): "
            "nenhum molde de nome foi cortado.\n"
            "As ancoras e a grade acima ja ficam gravadas; rode de novo depois "
            "de escrever a watchlist."
        )
    moldes_de_nome: dict[str, np.ndarray] = {}
    cinza = cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY)
    for item in watchlist:
        x, y, larg, alt = _marcar(
            pixels,
            f"Nome: {item}",
            f"Marque o nome COMO RENDERIZADO de '{item}' — com o prefixo "
            f"'+N ' quando houver — e tecle ENTER.",
        )
        moldes_de_nome[item] = cinza[y : y + alt, x : x + larg].copy()

    resultado = matriz_de_confusao(moldes_de_nome)
    print()
    for (a, b), score in sorted(resultado.matriz.items(), key=lambda kv: -kv[1]):
        print(f"  {score:.4f}  {a}  x  {b}")
    print(resultado.explicar())
    if not resultado.aprovado:
        raise MercadoNaoCalibravel(
            "nada foi gravado: a watchlist precisa ser separavel primeiro"
        )

    # --- grava a conferencia e o arquivo ---
    regioes = dict(caixas)
    regioes["grade"] = caixa_grade
    regioes["linha_1"] = caixa_linha
    conferencia = _gravar_conferencia(desenhar_conferencia(pixels, regioes))

    tx, ty, tlarg, talt = caixas["titulo"]
    cal.mercado_ancora = Regiao(esquerda=tx, topo=ty, largura=tlarg, altura=talt)
    cal.mercado_molde_da_ancora = molde_para_hex(ancoras[0].molde)
    cal.mercado_limiar_da_ancora = CASAMENTO_MINIMO_DA_ANCORA
    cal.mercado_geometria_da_captura = {"largura": int(largura), "altura": int(altura)}
    cal.mercado_ancoras = ancoras_para_calibracao(ancoras)
    cal.mercado_grade = grade
    cal.mercado_templates_de_nome = [
        {"nome": nome, "molde": molde_para_hex(molde)}
        for nome, molde in moldes_de_nome.items()
    ]
    if resultado.limiar_sugerido is not None:
        cal.mercado_limiar_de_template = resultado.limiar_sugerido

    # REGRAVA O ARQUIVO INTEIRO. Nada e impresso para o usuario colar: o
    # criterio 3 do ROADMAP e "sem editar JSON a mao".
    cal.salvar(arquivo)
    print(f"\nCalibracao de mercado gravada em {arquivo.name}")
    print(f"  ancoras      : {', '.join(a.nome for a in ancoras)}")
    print(
        f"  grade        : {grade['linhas_por_pagina']} linhas de "
        f"{grade['altura_da_linha']} px, layout '{grade['layout']}'"
    )
    print(f"  watchlist    : {len(moldes_de_nome)} molde(s) de nome")
    _texto_final_da_conferencia(conferencia, arquivo)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m l2scanner.calibrar_mercado",
        description="Calibra as regioes do World Exchange sobre um frame GRAVADO.",
    )
    parser.add_argument("--gravacao", help="pasta de gravacao de JANELA COMPLETA")
    parser.add_argument("--frame", help="um PNG especifico")
    parser.add_argument(
        "--indice", type=int, default=None,
        help="qual frame da gravacao (padrao: o do meio)",
    )
    parser.add_argument(
        "--layout", default="negociacao",
        choices=("negociacao", "adena", "busca"),
        help="qual dos TRES layouts de coluna esta na tela",
    )
    parser.add_argument("--calibracao", help="outro calibration.json (para teste)")
    args = parser.parse_args(argv)

    try:
        return calibrar(args)
    except MercadoNaoCalibravel as erro:
        print(f"\n{erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
