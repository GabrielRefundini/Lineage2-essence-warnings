"""A varredura que MEDE a sonda de oclusao, o limiar de dispersao e o piso.

Esta ferramenta nao decide nada por gosto: ela varre as 8 gravacoes de campo do
censo, mede, e PROPOE tres numeros que vao para o `calibration.json`. Nenhum
deles pode entrar no fonte de producao - a disciplina fundadora do projeto e que
constante magica no codigo garante reescrita na primeira "nao funciona no meu
PC", e um numero escolhido em vez de medido e uma promessa que ninguem conferiu.

    mercado_sonda_do_fundo               o trecho SEM TEXTO da linha (dx0, dx1,
                                         folga), ESCOLHIDO por varredura
    mercado_limiar_de_dispersao_do_fundo acima dele a linha esta COBERTA
    mercado_minimo_de_linhas_comparadas  o piso que impede o ACORDO TRIVIAL do
                                         estabilizador do 02-05

O QUE ELA MEDE, E POR QUE NESSA GRANDEZA
----------------------------------------
O sinal de oclusao e a FAIXA DE FUNDO ALTERNADA da linha, medida num trecho sem
texto (D-14). Ele NAO e a confianca do casamento: a tooltip do jogo e
SEMITRANSPARENTE, entao um numero coberto por ela ainda produz glifos plausiveis
com boa confianca e valor errado - "o incidente das 27 mortes falsas, um nivel
acima".

E a grandeza e DISPERSAO, nunca "a moda e 48 ou 66". MEDIDO em
`tooltip/frame_000015`: nas linhas 2, 4 e 6 a moda continua 48 mesmo cobertas.
Testar a moda aprovaria tres linhas cobertas. A dispersao e auto-referente e nao
depende de conhecer os valores desta pele de jogo. A primitiva que mede e
`mercado_geometria.nivel_de_fundo_da_linha`, e esta ferramenta chama EXATAMENTE
ela - medir de um jeito e decidir com outro seria comparar convencoes.

O CONJUNTO DE MEDICAO E FECHADO, E ISSO E UMA GUARDA
-----------------------------------------------------
`recordings/` tem 16 pastas. O censo de 335 frames da pesquisa cobriu 8, e sao
so essas que entram. A lista e constante deste modulo e as outras pastas sao
IGNORADAS com o motivo impresso. Apontar a ferramenta para o diretorio e deixar
ela iterar subdiretorios mediria sobre material que o censo nunca viu - e a
pasta `pre-voo` sozinha tem 1502 PNGs de outro dia, que dominariam qualquer
distribuicao medida. Uma pasta esperada ausente PARA a ferramenta: medir sobre
um conjunto diferente do censo produz um numero que nao se compara com nenhum
outro numero deste projeto.

Uso (no checkout PRINCIPAL - `recordings/` e gitignored e nao se materializa em
worktree):

    .venv/Scripts/python.exe tools/medir_oclusao.py
        --gravacoes C:/.../recordings --calibracao C:/.../calibration.json
    ... e com --gravar para persistir os tres numeros.

Sai com codigo 0 quando conseguiu propor os numeros, e diferente de zero quando
as populacoes se sobrepoem - um limiar que nao separa e pior que nenhum - ou
quando o gabarito limpo nao exercita a sonda escolhida (codigo 8, ver
`conferir_o_gabarito_limpo`): validar contra nome curto ja
custou 31 paginas de campo uma vez.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from l2scanner.calibracao import Calibracao  # noqa: E402
from l2scanner.identidade import mascara_de_texto  # noqa: E402
from l2scanner.mercado_geometria import nivel_de_fundo_da_linha  # noqa: E402
from l2scanner.mercado_visao import (  # noqa: E402
    RastreioDoPainel,
    ancoras_de_calibracao,
)

# ---------------------------------------------------------------------------
# O CONJUNTO DE MEDICAO - as 8 do censo, e o motivo de cada uma das outras
# ---------------------------------------------------------------------------

GRAVACOES_DO_CENSO = (
    "20260828-053105-mercado-aberto",
    "20260828-055323-mercado-scroll",
    "20260828-060622-mercado-pagina-cheia",
    "20260828-061253-mercado-tooltip",
    "20260828-061409-mercado-alvo-sobreposto",
    "20260828-063240-mercado-farm-com-party",
    "20260828-063409-mercado-scroll-transicao",
    "20260828-063752-mercado-aberto",
)

# As gravacoes com oclusao DELIBERADA. Elas entram na varredura como todas as
# outras; o que muda e o papel que os frames NOMEADOS delas tem no gabarito.
GRAVACAO_DA_TOOLTIP = "20260828-061253-mercado-tooltip"
GRAVACAO_DO_ALVO = "20260828-061409-mercado-alvo-sobreposto"
GRAVACOES_COM_OCLUSAO = (GRAVACAO_DA_TOOLTIP, GRAVACAO_DO_ALVO)

# As 8 que ficam de fora, NOMEADAS com o motivo. Uma pasta fora desta tabela e
# fora do censo tambem e ignorada, e tambem impressa - o que a tabela impede e o
# silencio, nao a existencia.
MOTIVO_PARA_IGNORAR = {
    "20260827-225521-pre-voo": (
        "anterior ao spike e de outro dia; e a MAIOR pasta do diretorio, e um "
        "glob que a arrastasse dominaria sozinho qualquer distribuicao"
    ),
    "20260828-053003-mercado-fechado": (
        "e a gravacao do painel FECHADO: nenhum frame com painel aberto, entao "
        "nao contribui linha nenhuma para limiar nenhum"
    ),
    "20260828-115559-calibragem": "sessao de calibragem, nao de mercado",
    "20260828-115700-calibragem": "sessao de calibragem, nao de mercado",
    "hp_baixo": "vazia - zero PNGs",
    "inv2": "material de inventario, de outro recurso",
    "inv3": "material de inventario; e a base do replay do incidente 27x",
    "inventario": "material de inventario, de outro recurso",
}

# ---------------------------------------------------------------------------
# Os parametros da VARREDURA - de ferramenta, e cada um com a sua medicao
# ---------------------------------------------------------------------------

# De quanto em quanto a sonda desliza dentro da janela derivada das colunas.
#
# ERA 15, E 15 NAO ALCANCAVA A RESPOSTA. A janela comeca em x=42, entao um passo
# de 15 so visita 42, 57, 72, ... 237, 252 - e o trecho que a remedicao de
# 2026-08-31 escolheu comeca em x=246, que nao esta nessa lista. Os vizinhos
# eram 237 (nove px DENTRO da tinta do nome mais comprido do censo, que termina
# em 246) e 252 (seis px alem dela). A grade da propria varredura excluia o
# unico ponto que separa as duas coisas. 12 divide 204 = 246 - 42, e por isso e
# 12: nao por gosto de numero redondo, mas porque a resposta medida cai nele.
#
# O custo e 25 candidatos em vez de 16, ~1,5x a varredura. Ela segue em minutos.
PASSO_DA_VARREDURA = 12

# As linhas de folga em cada ponta do recorte.
#
# Mesmo cuidado de `fim_da_alternancia` (`mercado_geometria.py:470-472`): a linha
# de transicao entre duas bandas nao pertence a nenhuma das duas e diluiria a
# medida. Esta folga e GRAVADA junto do retangulo, no mesmo objeto, porque quem a
# escolheu foi esta varredura.
FOLGA_NAS_PONTAS = 2

# A largura da sonda, em pixels. ELA ENCOLHEU DE 210 PARA 150 EM 2026-08-31, E
# ISSO CUSTOU ALGUMA COISA. Este bloco existe para que o custo nao suma.
#
# Era `FRACAO_DA_JANELA_PARA_A_SONDA = 0.5`, que sobre esta janela de 447 px dava
# 210. O texto que ficava aqui dizia que a sonda "NAO PODE SER PEQUENA", e a
# refutacao que ele citava CONTINUA VALENDO E NAO FOI REVOGADA: varrendo em
# blocos de 30 px sobre `tooltip/frame_000015`, a linha 0 - coberta pela tooltip
# - tem blocos que leem dispersao 0,0000, porque o bloco cabe INTEIRO dentro de
# um buraco do desenho da tooltip. Sonda estreita e sonda que pode se esconder
# num vao da arte que ela deveria enxergar. Esse risco AUMENTOU com 150 px.
#
# O QUE MUDOU E QUE O OUTRO LADO DO PAR DE ERROS DEIXOU DE SER HIPOTETICO. O
# mesmo texto avisava que larga demais "come o texto do nome e a dispersao de uma
# linha limpa sobe ate encostar na de uma coberta" - e foi exatamente isso que
# aconteceu em campo, com 210 px: `Protecting Scroll: Enchant C-grade Armor` (40
# caracteres, tinta ate x=246) punha 40 px de GLIFO dentro da sonda, a linha lia
# 0,0276 contra um limiar de 0,0264 e era recusada sem haver tooltip nenhuma. 31
# paginas perdidas numa sessao, `observacoes.csv` so com o cabecalho.
#
# A VARREDURA 2-D (posicao x largura), com o gabarito ja corrigido, mediu os dois
# lados de uma vez - e a largura nao e um gosto, e um numero:
#
#     largura 210  melhor dx0=192  pior LIMPA 0,0391  folga  2,9x
#     largura 180  melhor dx0=243  pior LIMPA 0,0033  folga  6,9x
#     largura 150  melhor dx0=246  pior LIMPA 0,0007  folga 32,0x
#
# (essa tabela veio de uma varredura de mao, com 4 frames limpos no gabarito.
# Rodando ESTA ferramenta, com os 8 frames limpos que o gabarito tem hoje, a
# largura 150 escolhe o mesmo dx0=246 e mede folga 30,8x - a diferenca e da
# populacao maior, nao do trecho.)
#
# 150 px foi ESCOLHIDO PELO USUARIO em 2026-08-31, com estes numeros na mao, e a
# escolha APERTA a peneira em vez de afrouxa-la: o limiar cai de 0,026377 para
# 0,003607 (7x mais estrito) e a separacao entre uma linha limpa e uma coberta
# sobe de 2,8x para 30,8x. As 10 linhas cobertas conhecidas do gabarito seguem
# recusadas, com ~5x de folga sobre o limiar novo. A alternativa era so remedir o
# limiar em 210 px (0,026377 -> 0,046372), o que consertava o defeito relatado
# AFROUXANDO a guarda: a folga contra a marcacao de alvo caia de 2,9x para 1,7x.
#
# O QUE FICA DE DIVIDA, ESCRITO PARA NAO SUMIR: 150 px cabe dentro de um buraco
# uniforme da arte da tooltip com mais facilidade do que 210 px cabia. O censo
# nao mostra nenhum caso em que isso aconteca - a menor linha coberta conhecida
# le 0,0200, cinco vezes e meia o limiar novo - mas o mecanismo continua de pe,
# e quem for medir a proxima sonda tem de ler isto antes de estreitar mais.
LARGURA_DA_SONDA = 150

# O GABARITO DE CAMPO: quais linhas de quais frames um humano VIU cobertas.
#
# Este e o unico rotulo NAO CIRCULAR disponivel. Rotular "coberta" com o limiar
# que a ferramenta ainda vai propor e ajustar um ate o outro fechar; rotular por
# PASTA tambem nao serve, e a refutacao esta medida nesta execucao:
#
#     MEDIDO, 2026-08-30: as seis gravacoes "sem oclusao deliberada" contem
#     tooltip. A propria pesquisa nomeia `scroll/frame_000084` como um frame com
#     tooltip sobre a faixa de titulo. Rotulando por pasta, a pior linha "limpa"
#     le 0,58-0,72 em TODOS os 214 trechos candidatos varridos, contra 0,30-0,47
#     da menor linha coberta conhecida - as populacoes se sobrepoem em todo
#     lugar, e a sobreposicao e do ROTULO, nao do trecho.
#
# As condicoes abaixo vem da observacao humana registrada na pergunta 4 do
# `02-RESEARCH.md` e nos frames de referencia do `02-CONTEXT.md`.
#
# AQUI ESTAVA A CAUSA-RAIZ DO DEFEITO DE 2026-08-31, E ELA E DE APONTAMENTO, NAO
# DE RACIOCINIO. O comentario que ficava neste lugar dizia, palavra por palavra:
#
#     "Os frames LIMPOS incluem de proposito `scroll-transicao/frame_000016` e
#      `frame_000017` (...): e neles que aparecem os nomes LONGOS (`+6 Agathion
#      Alpha Hunter Sealed`), e sem eles a escolha do trecho seria enganada por
#      um recorte que so parece vazio porque as seis paginas conferidas tinham
#      nome curto."
#
# A GUARDA CONTRA NOME CURTO FOI PENSADA, FOI ESCRITA, E APONTAVA PARA O LUGAR
# ERRADO. Os dois frames foram abertos e conferidos em 2026-08-31: eles mostram
# `Hardin's Soul Crystal Lv. 1` - 27 caracteres, tinta do nome terminando em
# x=169. O nome longo que o comentario prometia esta em `053105/frame_000052`
# (`+6 Agathion Alpha Hunter Sealed`, 31 caracteres, tinta ate x=208), que nao
# estava no gabarito. MEDIDO, a ponta da tinta do nome nos QUATRO frames limpos
# do gabarito antigo: 178, 142, 169 e 169 - nenhum deles chegava sequer perto do
# x=207 onde a sonda proposta comecava (a linha mais funda de TODO o gabarito
# limpo antigo parava em x=215, e era do frame do ALVO, nao dos dois que a prosa
# apontava). A varredura de 02-02 validou 207..417 contra nome CURTO, exatamente
# a falha que o comentario afirmava estar impedindo, e o resultado foi 31 paginas
# perdidas na aba Enhancement > Scrolls. Prosa nao e guarda; a guarda esta em
# `conferir_o_gabarito_limpo`, que MEDE isso e PARA.
#
# Os dois frames de nome curto FICAM: eles sao limpos de verdade e nitidos, e o
# que estava errado nunca foi a presenca deles, foi o papel que a prosa lhes
# dava. O que ENTRA sao os dois frames de `053105-mercado-aberto` que carregam
# de fato os nomes compridos, conferidos a olho no frame inteiro, sem tooltip.
#
# O NOME EXIBIDO ENTRA NA TABELA, E NAO NO COMENTARIO. E essa a licao: o quarto
# campo de cada linha do `GABARITO_LIMPAS` e o nome que aquele frame mostra, e a
# guarda o CONFRONTA COM OS PIXELS. Um apontamento errado como o de 2026-08-30 -
# declarar 31 caracteres num frame cuja tinta para em x=169, enquanto outro
# frame do mesmo gabarito inka ate 215 - deixa de ser prosa que ninguem confere e
# passa a ser uma contradicao que PARA a ferramenta. `None` e um valor legitimo,
# para o frame cujo nome ninguem conferiu a olho; ele so nao pode ser o unico.
GABARITO_COBERTAS = (
    (GRAVACAO_DA_TOOLTIP, "frame_000015.png", tuple(range(0, 8))),
    (GRAVACAO_DO_ALVO, "frame_000024.png", (0, 1)),
)
# (gravacao, arquivo, linhas, NOME EXIBIDO conferido a olho ou None)
GABARITO_LIMPAS = (
    (GRAVACAO_DA_TOOLTIP, "frame_000015.png", (8, 9), None),
    (GRAVACAO_DO_ALVO, "frame_000024.png", tuple(range(2, 10)), None),
    (
        "20260828-060622-mercado-pagina-cheia",
        "frame_000010.png",
        tuple(range(10)),
        None,
    ),
    ("20260828-055323-mercado-scroll", "frame_000014.png", tuple(range(10)), None),
    (
        "20260828-063409-mercado-scroll-transicao",
        "frame_000016.png",
        tuple(range(10)),
        "Hardin's Soul Crystal Lv. 1",
    ),
    (
        "20260828-063409-mercado-scroll-transicao",
        "frame_000017.png",
        tuple(range(10)),
        "Hardin's Soul Crystal Lv. 1",
    ),
    # OS DOIS DE NOME COMPRIDO. Sem eles a varredura escolhe um trecho que so
    # parece vazio porque ninguem lhe mostrou um nome de 40 caracteres.
    (
        "20260828-053105-mercado-aberto",
        "frame_000060.png",
        tuple(range(10)),
        "Protecting Scroll: Enchant C-grade Armor",
    ),
    (
        "20260828-053105-mercado-aberto",
        "frame_000052.png",
        tuple(range(10)),
        "+6 Agathion Alpha Hunter Sealed",
    ),
)

# O nome mais comprido que este projeto ja VIU na grade de negociacao, em
# caracteres. O gabarito limpo tem de conter pelo menos um assim, ou a varredura
# esta escolhendo o trecho sem nunca ter visto o pior caso que o campo produz -
# que e literalmente o defeito de 2026-08-31.
#
# ELE E UM PISO QUE SOBE, NUNCA UMA VERDADE. No dia em que aparecer na aba um
# nome de 45 caracteres, este numero passa a 45 e a varredura precisa de um frame
# novo antes de poder propor sonda de novo. Baixa-lo para fazer a ferramenta
# passar e desligar a guarda.
PIOR_NOME_CONHECIDO_EM_CARACTERES = 40


# ---------------------------------------------------------------------------
# O que a varredura produz
# ---------------------------------------------------------------------------


@dataclass
class LeituraDeFrame:
    """As dispersoes de um frame, em TODAS as sondas candidatas."""

    gravacao: str
    arquivo: str
    # (linhas_por_pagina, numero_de_candidatos); NaN = nao deu para medir
    dispersoes: np.ndarray
    # A ponta da tinta do NOME de cada linha, em x relativo a ESQUERDA DA GRADE
    # (a mesma origem de `mercado_sonda_do_fundo`). -1 quando a linha nao tem
    # tinta nenhuma. E o insumo da guarda de nome curto; ver
    # `conferir_o_gabarito_limpo`.
    pontas_da_tinta: np.ndarray | None = None


@dataclass
class Varredura:
    candidatos: list = field(default_factory=list)
    leituras: list = field(default_factory=list)
    frames_por_gravacao: dict = field(default_factory=dict)
    abertos_por_gravacao: dict = field(default_factory=dict)
    janela_derivada: tuple = (0, 0)
    linhas_por_pagina: int = 0


def _quantis(valores) -> dict:
    if not valores:
        return {}
    arranjo = np.asarray(valores, dtype=np.float64)
    return {
        "n": int(arranjo.size),
        "min": float(arranjo.min()),
        "p5": float(np.percentile(arranjo, 5)),
        "mediana": float(np.median(arranjo)),
        "p95": float(np.percentile(arranjo, 95)),
        "max": float(arranjo.max()),
    }


def _linha_de_distribuicao(rotulo: str, valores) -> str:
    q = _quantis(valores)
    if not q:
        return "  " + rotulo.ljust(34) + " (populacao vazia)"
    return (
        f"  {rotulo:<34} n={q['n']:>5}  min={q['min']:.4f}  p5={q['p5']:.4f}  "
        f"mediana={q['mediana']:.4f}  p95={q['p95']:.4f}  max={q['max']:.4f}"
    )


# ---------------------------------------------------------------------------
# A janela de busca, derivada das COLUNAS CALIBRADAS
# ---------------------------------------------------------------------------


def janela_de_busca(cal: Calibracao) -> tuple:
    """De onde ate onde a sonda pode deslizar, relativo a ESQUERDA da grade.

    A pesquisa apontou o vao entre o FIM da coluna do nome e o COMECO da coluna
    Quantity. Nesta calibracao esse vao tem LARGURA ZERO - as duas colunas sao
    adjacentes por construcao, porque a coluna do nome foi definida no 02-01
    como terminando exatamente no rotulo `Quantity` do cabecalho. A divergencia
    e devolvida junto, para entrar no relatorio em vez de sumir.

    A janela usada, entao, e a UNIAO das duas colunas: o nome e alinhado a
    esquerda e a quantidade a direita, entao o vao real de que a sonda precisa
    esta no MEIO delas - e e a varredura que o encontra, nao esta funcao. A
    janela tambem EXCLUI o icone do item, que fica a esquerda da coluna do nome:
    ele e arte texturada e opaca, e uma sonda pousada nele mediria o icone, nao
    o fundo.
    """
    avisos = []
    grade = cal.mercado_grade or {}
    nome = cal.mercado_coluna_do_nome or {}
    quantidade = cal.mercado_coluna_da_quantidade or {}
    esquerda_da_grade = int(grade["dx"])

    inicio_do_nome = int(nome["dx"]) - esquerda_da_grade
    fim_do_nome = inicio_do_nome + int(nome["largura"])
    inicio_da_quantidade = int(quantidade["dx"]) - esquerda_da_grade
    fim_da_quantidade = inicio_da_quantidade + int(quantidade["largura"])

    vao = inicio_da_quantidade - fim_do_nome
    if vao <= 0:
        avisos.append(
            "DIVERGENCIA: o vao literal entre o fim da coluna do nome "
            f"(x={fim_do_nome}) e o comeco da coluna Quantity "
            f"(x={inicio_da_quantidade}) tem largura {vao} - as duas colunas "
            "sao adjacentes nesta calibracao. A janela de busca passa a ser a "
            "UNIAO das duas colunas, e quem escolhe o trecho e a varredura."
        )
    return inicio_do_nome, fim_da_quantidade, avisos


def candidatos_de_sonda(inicio: int, fim: int) -> tuple:
    """Os trechos que a varredura vai comparar. Todos da MESMA largura."""
    janela = fim - inicio
    largura = min(int(LARGURA_DA_SONDA), janela)
    if largura <= 0:
        return [], 0
    candidatos = [
        (inicio + deslocamento, inicio + deslocamento + largura)
        for deslocamento in range(0, janela - largura + 1, PASSO_DA_VARREDURA)
    ]
    return candidatos, largura


# ---------------------------------------------------------------------------
# A PONTA DA TINTA DO NOME - o insumo da guarda de nome curto
# ---------------------------------------------------------------------------


def ponta_da_tinta_do_nome(
    bgr: np.ndarray,
    coluna_do_nome: dict,
    origem_x: int,
    gx: int,
    topo: int,
    altura: int,
) -> int:
    """Ate onde, em x, o NOME desta linha escreve. -1 quando nao ha tinta.

    O x devolvido e RELATIVO A ESQUERDA DA GRADE, a mesma origem de
    `mercado_sonda_do_fundo` - comparar a ponta da tinta com `dx0` so faz sentido
    se as duas estiverem na mesma regua, e a conversao mora aqui em vez de em
    cada ponto de uso.

    A mascara e `identidade.mascara_de_texto`, a MESMA que o resto do projeto usa
    para dizer "isto e glifo da UI, nao cenario". Inventar aqui um criterio
    proprio de tinta faria a guarda medir uma coisa e o leitor outra.

    ESTA MEDIDA E BRUTA DE PROPOSITO. Ela nao distingue tinta de NOME de tinta de
    TOOLTIP caida por cima da coluna do nome - e nem precisa: quem a consome
    olha so as linhas que o gabarito declara LIMPAS, e nelas nao ha tooltip
    nenhuma por definicao do gabarito.
    """
    if not coluna_do_nome or bgr is None or bgr.size == 0:
        return -1
    nx = origem_x + int(coluna_do_nome["dx"])
    largura = int(coluna_do_nome["largura"])
    recorte = bgr[topo : topo + altura, nx : nx + largura]
    if recorte.size == 0:
        return -1
    colunas = np.flatnonzero(mascara_de_texto(recorte).any(axis=0))
    if colunas.size == 0:
        return -1
    return int(colunas[-1]) + (nx - gx)


# ---------------------------------------------------------------------------
# A varredura
# ---------------------------------------------------------------------------


def varrer(gravacoes: Path, cal: Calibracao) -> Varredura:
    """Todas as linhas de todos os frames com painel aberto das 8 gravacoes."""
    grade = cal.mercado_grade or {}
    linhas = int(grade["linhas_por_pagina"])
    altura_da_linha = int(grade["altura_da_linha"])
    ancoras = ancoras_de_calibracao(cal.mercado_ancoras)
    limiar = float(cal.mercado_limiar_da_ancora or 0.73)
    coluna_do_nome = cal.mercado_coluna_do_nome or {}

    inicio, fim, _ = janela_de_busca(cal)
    candidatos, _largura = candidatos_de_sonda(inicio, fim)

    resultado = Varredura(
        candidatos=candidatos,
        janela_derivada=(inicio, fim),
        linhas_por_pagina=linhas,
    )

    for nome in GRAVACOES_DO_CENSO:
        pasta = gravacoes / nome
        arquivos = sorted(p for p in pasta.glob("frame_*.png") if p.is_file())
        resultado.frames_por_gravacao[nome] = len(arquivos)
        abertos = 0
        # Um rastreio POR GRAVACAO: ele segue barato de frame em frame e volta a
        # varrer no instante em que perde o painel, que e o desenho ja medido.
        rastreio = RastreioDoPainel(ancoras, limiar)
        for caminho in arquivos:
            frame = cv2.imread(str(caminho))
            if frame is None:
                continue
            voto = rastreio.observar(frame)
            if not voto.aberto or rastreio.origem is None:
                continue
            abertos += 1
            origem_x, origem_y = rastreio.origem
            gx = origem_x + int(grade["dx"])
            gy = origem_y + int(grade["dy"])
            cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            dispersoes = np.full((linhas, len(candidatos)), np.nan)
            pontas = np.full(linhas, -1, dtype=int)
            for indice in range(linhas):
                topo = gy + indice * altura_da_linha
                pontas[indice] = ponta_da_tinta_do_nome(
                    frame, coluna_do_nome, origem_x, gx, topo, altura_da_linha
                )
                for coluna, (dx0, dx1) in enumerate(candidatos):
                    medido = nivel_de_fundo_da_linha(
                        cinza,
                        (gx + dx0, topo, dx1 - dx0, altura_da_linha),
                        FOLGA_NAS_PONTAS,
                    )
                    if medido is not None:
                        dispersoes[indice, coluna] = medido[1]
            resultado.leituras.append(
                LeituraDeFrame(nome, caminho.name, dispersoes, pontas)
            )
        resultado.abertos_por_gravacao[nome] = abertos
    return resultado


# ---------------------------------------------------------------------------
# A escolha do trecho, e as duas populacoes
# ---------------------------------------------------------------------------


def _valores_do_gabarito(varredura: Varredura, tabela, sonda: int) -> list:
    """As dispersoes das linhas que o gabarito nomeia, no trecho `sonda`."""
    indice = {
        (leitura.gravacao, leitura.arquivo): leitura
        for leitura in varredura.leituras
    }
    valores = []
    for entrada in tabela:
        # `[:3]` porque o GABARITO_LIMPAS carrega um quarto campo - o nome
        # exibido - que so a guarda de nome curto consome.
        gravacao, arquivo, linhas = entrada[0], entrada[1], entrada[2]
        leitura = indice.get((gravacao, arquivo))
        if leitura is None:
            continue
        for linha in linhas:
            valor = leitura.dispersoes[linha, sonda]
            if not np.isnan(valor):
                valores.append(float(valor))
    return valores


def escolher_o_trecho_sem_texto(varredura: Varredura) -> tuple:
    """O trecho que separa o gabarito com a MAIOR FOLGA RELATIVA.

    A folga e `menor dispersao COBERTA / maior dispersao LIMPA` sobre as linhas
    que o gabarito nomeia. Em razao, e nao em diferenca: a dispersao varre tres
    ordens de grandeza entre uma linha limpa e uma sob tooltip, e uma diferenca
    absoluta trataria 0,50 contra 0,45 como igual a 0,05 contra 0,00.

    UM TRECHO CUJA PIOR LIMPA E EXATAMENTE ZERO E DESCARTADO, e essa recusa e
    deliberada. A razao contra zero nao e uma medicao, e uma divisao por zero
    vestida de resultado: MEDIDO, os trechos que a produzem rejeitam 22,4% de
    TODAS as linhas de campo quando o corte cai onde essa "folga infinita" o
    poe - as seis paginas do gabarito nao exercitaram aquele recorte e o resto
    do material exercitou. Uma separacao que so se consegue expressar como
    "infinita" e uma separacao que nao foi medida.

    Devolve `(indice_escolhido, tabela)`, com a tabela inteira dos candidatos
    para o relatorio - a escolha tem de poder ser conferida, nao acreditada.
    """
    tabela = []
    for coluna in range(len(varredura.candidatos)):
        cobertas = _valores_do_gabarito(varredura, GABARITO_COBERTAS, coluna)
        limpas = _valores_do_gabarito(varredura, GABARITO_LIMPAS, coluna)
        if not cobertas or not limpas:
            continue
        dx0, dx1 = varredura.candidatos[coluna]
        pior_limpa, melhor_coberta = max(limpas), min(cobertas)
        mensuravel = pior_limpa > 0.0
        tabela.append(
            {
                "coluna": coluna,
                "dx0": dx0,
                "dx1": dx1,
                "pior_limpa": pior_limpa,
                "melhor_coberta": melhor_coberta,
                "separa": melhor_coberta > pior_limpa,
                "mensuravel": mensuravel,
                "folga": (
                    melhor_coberta / pior_limpa if mensuravel else float("inf")
                ),
            }
        )

    aptos = [c for c in tabela if c["separa"] and c["mensuravel"]]
    if not aptos:
        return -1, tabela
    melhor = max(aptos, key=lambda c: c["folga"])
    return int(melhor["coluna"]), tabela


# ---------------------------------------------------------------------------
# A GUARDA DE NOME CURTO - a que faltou em 2026-08-30 e custou 31 paginas
# ---------------------------------------------------------------------------


def conferir_o_gabarito_limpo(varredura: Varredura, dx0: int) -> tuple:
    """O gabarito limpo VIU um nome comprido, e e o que ele diz ter visto? PARA.

    O DEFEITO QUE ESTA FUNCAO EXISTE PARA IMPEDIR JA ACONTECEU. Em 2026-08-30 a
    varredura escolheu a sonda 207..417 e mediu, no gabarito limpo, dispersao
    0,0000 em quase toda linha. O numero era verdadeiro e a conclusao era falsa:
    o nome mais comprido de todo o gabarito limpo tinha 31 caracteres, e os dois
    frames que o comentario NOMEAVA como sendo os de nome longo mostravam 27. A
    populacao "limpa" era uma populacao que nunca teve a chance de sujar, e a
    folga calculada sobre ela era um numero sobre coisa nenhuma. Em campo um nome
    de 40 caracteres escreveu ate x=246, a dispersao subiu para 0,0276 contra um
    limiar de 0,0264, e 31 paginas de Enhancement > Scrolls foram perdidas.

    A PROSA JA AVISAVA E NAO ADIANTOU. O comentario do `GABARITO_LIMPAS` dizia,
    desde o primeiro dia, que sem nome longo "a escolha do trecho seria enganada
    por um recorte que so parece vazio". Ele apontava para os frames errados, e
    nada no mundo conferia o apontamento. Uma guarda que so existe em prosa e
    uma guarda que ninguem executa.

    SAO TRES CONFERENCIAS, E A PRIMEIRA E A QUE MORDE.

    (1) PISO DE COMPRIMENTO. O gabarito limpo tem de declarar pelo menos um nome
        com `PIOR_NOME_CONHECIDO_EM_CARACTERES` caracteres. E a pergunta do
        defeito, na grandeza do defeito. Contra o gabarito de 2026-08-30 o maior
        declarado seria 31 contra um piso de 40: REPROVADO, e e so isso que
        precisava ter acontecido.

    (2) A DECLARACAO CONTRA OS PIXELS. O frame que declara o nome mais comprido
        tem de ser tambem o de tinta mais funda entre os limpos. Esta e a
        conferencia que pega o erro de APONTAMENTO, que foi o erro real: em
        2026-08-30 a prosa declarava `scroll-transicao/frame_000016` como o
        frame de nome longo (tinta ate x=169) enquanto `alvo/frame_000024`, sem
        declaracao nenhuma, inkava ate x=215. Declaracao e pixel discordando e
        contradicao, nao detalhe - e a ferramenta PARA e imprime os dois.

    (3) ALCANCE. A tinta mais funda do gabarito limpo tem de chegar ao `dx0` da
        sonda escolhida. Sozinha esta conferencia NAO teria pego o defeito de
        2026-08-30 - a tinta ia a 215 e a sonda comecava em 207, entao ela teria
        passado -, e por isso ela e a terceira e nao a primeira. Ela pega outra
        coisa: sonda que ninguem exercitou com nome nenhum.

        O piso e `min(dx0, a ponta mais funda do CENSO INTEIRO)`, e o `min`
        existe para nao exigir o impossivel: se a sonda pousar a direita de
        qualquer tinta que o material de campo contenha, nao ha nome com que
        exercita-la, e cobrar um seria cobrar um frame que nao existe. Nesse caso
        a guarda passa e IMPRIME o fato, em vez de passar em silencio.

    NADA AQUI E CIRCULAR. Compara-se comprimento declarado com comprimento
    declarado, e ponta de tinta (pixels, `ponta_da_tinta_do_nome`) com ponta de
    tinta. Em ponto nenhum entra a dispersao ou o limiar que a ferramenta ainda
    vai propor; se entrasse, estaria conferindo o resultado com o resultado.

    A regua, para quem ler isto sem ela na mao: x=246 e `Protecting Scroll:
    Enchant C-grade Armor`, 40 caracteres; x=208 e `+6 Agathion Alpha Hunter
    Sealed`, 31; x=169 e `Hardin's Soul Crystal Lv. 1`, 27.

    Devolve `(passou, diagnostico)`.
    """
    indice = {
        (leitura.gravacao, leitura.arquivo): leitura
        for leitura in varredura.leituras
    }

    # A ponta de tinta mais funda POR FRAME do gabarito limpo, e o nome que cada
    # um declara. Os dois lado a lado sao o insumo das conferencias (1) e (2).
    por_frame = []
    for gravacao, arquivo, linhas, nome_exibido in GABARITO_LIMPAS:
        leitura = indice.get((gravacao, arquivo))
        if leitura is None or leitura.pontas_da_tinta is None:
            continue
        pontas = [
            int(leitura.pontas_da_tinta[linha])
            for linha in linhas
            if int(leitura.pontas_da_tinta[linha]) >= 0
        ]
        if not pontas:
            continue
        por_frame.append(
            {
                "frame": f"{gravacao}/{arquivo}",
                "ponta": max(pontas),
                "nome": nome_exibido,
                "caracteres": len(nome_exibido) if nome_exibido else None,
            }
        )

    pontas_do_censo = [
        int(v)
        for leitura in varredura.leituras
        if leitura.pontas_da_tinta is not None
        for v in leitura.pontas_da_tinta
        if int(v) >= 0
    ]
    diagnostico = {
        "dx0": int(dx0),
        "por_frame": por_frame,
        "n_sem_declaracao": sum(1 for f in por_frame if f["caracteres"] is None),
        "ponta_do_censo": max(pontas_do_censo) if pontas_do_censo else -1,
        "piso_de_caracteres": PIOR_NOME_CONHECIDO_EM_CARACTERES,
    }
    if not por_frame:
        diagnostico["motivo"] = (
            "nenhuma linha do gabarito LIMPO tem tinta de nome mensuravel"
        )
        return False, diagnostico

    declarados = [f for f in por_frame if f["caracteres"] is not None]
    mais_comprido = (
        max(declarados, key=lambda f: f["caracteres"]) if declarados else None
    )
    mais_fundo = max(por_frame, key=lambda f: f["ponta"])
    diagnostico["mais_comprido"] = mais_comprido
    diagnostico["mais_fundo"] = mais_fundo

    # (1) piso de comprimento
    if mais_comprido is None:
        diagnostico["motivo"] = (
            "NENHUM frame do GABARITO_LIMPAS declara o nome que exibe. Sem "
            "declaracao nao ha o que conferir, e a varredura escolheria o "
            "trecho sem saber se o pior nome do campo esta representado. Abra "
            "os frames, veja o nome, e escreva-o no quarto campo da tabela."
        )
        return False, diagnostico
    if mais_comprido["caracteres"] < PIOR_NOME_CONHECIDO_EM_CARACTERES:
        diagnostico["motivo"] = (
            "o GABARITO_LIMPAS nao contem nome comprido: o maior declarado tem "
            f"{mais_comprido['caracteres']} caracteres "
            f"(`{mais_comprido['nome']}`, em {mais_comprido['frame']}) contra "
            f"um piso de {PIOR_NOME_CONHECIDO_EM_CARACTERES}. A varredura "
            "estaria escolhendo o trecho sem nunca ter visto o pior caso do "
            "campo, que e literalmente o defeito de 2026-08-31. Ponha na tabela "
            "um frame com nome comprido - "
            "`20260828-053105-mercado-aberto/frame_000060.png` mostra "
            "`Protecting Scroll: Enchant C-grade Armor` nas dez linhas - ou "
            "grave um novo com --record na aba onde os nomes sao longos."
        )
        return False, diagnostico

    # (2) a declaracao contra os pixels
    if mais_fundo["ponta"] > mais_comprido["ponta"]:
        diagnostico["motivo"] = (
            "A DECLARACAO E OS PIXELS DISCORDAM. O frame que declara o nome "
            f"mais comprido do gabarito ({mais_comprido['frame']}, "
            f"`{mais_comprido['nome']}`, {mais_comprido['caracteres']} ch) tem "
            f"tinta ate x={mais_comprido['ponta']}, mas {mais_fundo['frame']} "
            f"inka mais fundo, ate x={mais_fundo['ponta']}. Ou a declaracao "
            "aponta para o frame errado - o erro de 2026-08-30 - ou o outro "
            "frame tem um nome ainda maior que ninguem declarou. Abra os dois."
        )
        return False, diagnostico

    # (3) alcance
    piso = min(int(dx0), diagnostico["ponta_do_censo"])
    diagnostico["piso_de_alcance"] = piso
    diagnostico["sonda_alem_do_censo"] = piso < int(dx0)
    if mais_fundo["ponta"] < piso:
        diagnostico["motivo"] = (
            "o gabarito LIMPO nao contem NENHUMA linha cujo nome alcance a "
            f"sonda escolhida: a tinta mais funda para em "
            f"x={mais_fundo['ponta']} e a sonda comeca em x={dx0}. A sonda "
            "seria escolhida sem que nome nenhum a tivesse exercitado."
        )
        return False, diagnostico
    return True, diagnostico


@dataclass
class Populacoes:
    """As duas populacoes do GABARITO, no trecho escolhido."""

    limpas: list = field(default_factory=list)
    cobertas_tooltip: list = field(default_factory=list)
    cobertas_alvo: list = field(default_factory=list)

    @property
    def cobertas(self) -> list:
        return list(self.cobertas_tooltip) + list(self.cobertas_alvo)


def separar_as_populacoes(varredura: Varredura, sonda: int) -> Populacoes:
    populacoes = Populacoes()
    populacoes.limpas = _valores_do_gabarito(varredura, GABARITO_LIMPAS, sonda)
    for gravacao, arquivo, linhas in GABARITO_COBERTAS:
        valores = _valores_do_gabarito(
            varredura, ((gravacao, arquivo, linhas),), sonda
        )
        if gravacao == GRAVACAO_DA_TOOLTIP:
            populacoes.cobertas_tooltip.extend(valores)
        else:
            populacoes.cobertas_alvo.extend(valores)
    return populacoes


def propor_o_limiar(populacoes: Populacoes) -> tuple:
    """A media GEOMETRICA entre a pior limpa e a melhor coberta do gabarito.

    Ela e, por construcao, o ponto de MAIOR FOLGA RELATIVA entre os dois:
    qualquer outro corte no meio deixa um dos lados com folga menor.

    Devolve `(None, diagnostico)` quando as populacoes se sobrepoem - um limiar
    que nao separa e pior que nenhum.
    """
    if not populacoes.limpas or not populacoes.cobertas:
        return None, {"motivo": "populacao do gabarito vazia"}
    pior_limpa = max(populacoes.limpas)
    melhor_coberta = min(populacoes.cobertas)
    diagnostico = {
        "pior_limpa": pior_limpa,
        "melhor_coberta": melhor_coberta,
        "folga": melhor_coberta / max(pior_limpa, 1e-12),
    }
    if populacoes.cobertas_alvo:
        melhor_alvo = min(populacoes.cobertas_alvo)
        diagnostico["melhor_alvo"] = melhor_alvo
        diagnostico["folga_do_alvo"] = melhor_alvo / max(pior_limpa, 1e-12)
    if melhor_coberta <= pior_limpa:
        diagnostico["motivo"] = "as populacoes se sobrepoem"
        return None, diagnostico
    return float(np.sqrt(pior_limpa * melhor_coberta)), diagnostico


def descarte_por_gravacao(varredura: Varredura, sonda: int, limiar: float) -> dict:
    """Quantas linhas de cada gravacao o limiar recusa. O CUSTO do corte.

    Descarte nao e de graca: ele custa dado que o usuario viu na tela. Este
    numero nao decide nada sozinho, mas sem ele a escolha do trecho seria
    julgada so pela folga do gabarito, que e medida em seis paginas.
    """
    contagem = {}
    for leitura in varredura.leituras:
        coluna = leitura.dispersoes[:, sonda]
        validas = coluna[~np.isnan(coluna)]
        alvo = contagem.setdefault(leitura.gravacao, [0, 0])
        alvo[0] += int(np.count_nonzero(validas > limiar))
        alvo[1] += int(validas.size)
    return {nome: (a, b) for nome, (a, b) in contagem.items()}


# ---------------------------------------------------------------------------
# O piso do estabilizador - na grandeza que o 02-05 JULGA
# ---------------------------------------------------------------------------


def distribuicao_de_linhas_sobreviventes(
    varredura: Varredura, sonda: int, limiar: float
) -> dict:
    """Quantas linhas sobrevivem POR FRAME. Relatada so para conferencia."""
    por_gravacao = {}
    for leitura in varredura.leituras:
        coluna = leitura.dispersoes[:, sonda]
        sobreviventes = sum(
            1
            for valor in coluna
            if not np.isnan(valor) and float(valor) <= limiar
        )
        por_gravacao.setdefault(leitura.gravacao, []).append(sobreviventes)
    return por_gravacao


def intersecao_entre_frames_vizinhos(
    varredura: Varredura, sonda: int, limiar: float
) -> dict:
    """O tamanho da INTERSECAO entre as posicoes aceitas de dois frames vizinhos.

    ESTA e a grandeza que o 02-05 julga, e nao a contagem por frame isolado. Ele
    compara as posicoes aceitas em AMBOS os frames, e a intersecao e sempre menor
    ou igual ao minimo dos dois - medir por frame isolado superestimaria
    sistematicamente e daria um piso alto demais.

    Os pares sao consecutivos DENTRO de cada gravacao: a varredura ja visita os
    frames em sequencia, entao forma-los nao custa nada. Frames sem painel aberto
    nao entram na lista, entao "vizinho" quer dizer "o proximo frame em que o
    painel estava aberto" - que e exatamente o que o estabilizador ve.
    """
    aceitas = {}
    for leitura in varredura.leituras:
        coluna = leitura.dispersoes[:, sonda]
        conjunto = {
            indice
            for indice, valor in enumerate(coluna)
            if not np.isnan(valor) and float(valor) <= limiar
        }
        medidas = int(np.count_nonzero(~np.isnan(coluna)))
        aceitas.setdefault(leitura.gravacao, []).append((conjunto, medidas))

    por_gravacao = {}
    for gravacao, pares in aceitas.items():
        por_gravacao[gravacao] = [
            len(pares[i][0] & pares[i + 1][0]) for i in range(len(pares) - 1)
        ]
    return por_gravacao


def pares_vizinhos_detalhados(
    varredura: Varredura, sonda: int, limiar: float
) -> list:
    """Cada par vizinho com o que e preciso para CLASSIFICA-LO pela medida.

    Devolve tuplas `(gravacao, intersecao, inteiro_dos_dois, coberto_em_algum)`:

    - `inteiro_dos_dois` - os DOIS frames tiveram todas as linhas medidas
      aceitas. E a definicao de "par normal" que o piso usa, e ela e uma
      MEDIDA, nao um rotulo de pasta.
    - `coberto_em_algum` - pelo menos um dos dois teve MAIS DA METADE das
      linhas recusada.

    Classificar por pasta e o erro que esta execucao ja refutou uma vez: as
    seis gravacoes "sem oclusao deliberada" tem tooltip, e o `mercado-aberto`
    sozinho traz pares de intersecao ZERO. Com o rotulo de pasta esses pares
    caiam na populacao "normal" e derrubavam o p5 dela para 0, o que tornava
    impossivel propor qualquer piso.
    """
    aceitas = {}
    for leitura in varredura.leituras:
        coluna = leitura.dispersoes[:, sonda]
        conjunto = {
            indice
            for indice, valor in enumerate(coluna)
            if not np.isnan(valor) and float(valor) <= limiar
        }
        medidas = int(np.count_nonzero(~np.isnan(coluna)))
        aceitas.setdefault(leitura.gravacao, []).append((conjunto, medidas))

    pares = []
    for gravacao, sequencia in aceitas.items():
        for i in range(len(sequencia) - 1):
            (a, medidas_a), (b, medidas_b) = sequencia[i], sequencia[i + 1]
            inteiro = (
                medidas_a > 0
                and medidas_b > 0
                and len(a) == medidas_a
                and len(b) == medidas_b
            )
            coberto = (2 * len(a) < medidas_a) or (2 * len(b) < medidas_b)
            pares.append((gravacao, len(a & b), inteiro, coberto))
    return pares


def propor_o_minimo_comparado(pares: list, linhas_por_pagina: int) -> tuple:
    """O piso que impede o ACORDO TRIVIAL, sobre a distribuicao da INTERSECAO.

    Uma pagina quase toda descartada nao pode ser aceita porque as duas ou tres
    linhas que sobraram concordam. O piso fica ABAIXO do p5 dos pares NORMAIS e
    ACIMA do que os pares majoritariamente COBERTOS produzem.

    As duas populacoes sao definidas pela MEDIDA de cada par, nunca pela pasta
    de onde ele veio (ver `pares_vizinhos_detalhados`):

        normal   os dois frames tiveram TODAS as linhas medidas aceitas - a
                 pagina que o scanner leria inteira
        coberto  pelo menos um dos dois teve MAIS DA METADE das linhas recusada

    Os pares que nao sao nem um nem outro - pagina parcialmente coberta - sao
    contados e reportados, mas nao definem os limites: eles sao justamente a
    faixa cinzenta que o piso existe para atravessar.

    Devolve `(None, diagnostico)` quando as duas populacoes se tocam.
    """
    normais = [t for _, t, inteiro, _ in pares if inteiro]
    cobertos = [t for _, t, _, coberto in pares if coberto]
    parciais = len(pares) - len(normais) - len(cobertos)

    diagnostico = {
        "n_normais": len(normais),
        "n_cobertos": len(cobertos),
        "n_parciais": max(parciais, 0),
    }
    if not normais:
        diagnostico["motivo"] = "nenhum par normal medido"
        return None, diagnostico

    p5_normais = float(np.percentile(np.asarray(normais, dtype=float), 5))
    teto_coberto = max(cobertos) if cobertos else 0
    diagnostico["p5_normais"] = p5_normais
    diagnostico["min_normais"] = int(min(normais))
    diagnostico["teto_coberto"] = int(teto_coberto)

    inferior = teto_coberto + 1
    superior = int(np.floor(p5_normais))
    if p5_normais == float(superior):
        superior -= 1  # ESTRITAMENTE abaixo do p5
    superior = min(superior, linhas_por_pagina)
    if inferior > superior or superior < 1:
        diagnostico["motivo"] = (
            "as duas populacoes se tocam: nao ha inteiro estritamente acima do "
            "teto coberto e abaixo do p5 dos pares normais"
        )
        return None, diagnostico

    piso = max(1, (inferior + superior) // 2)
    diagnostico["faixa"] = (inferior, superior)
    diagnostico["folga_abaixo"] = piso - teto_coberto
    diagnostico["folga_acima"] = p5_normais - piso
    return piso, diagnostico


# ---------------------------------------------------------------------------
# Persistencia - load-mutate-save, nunca montar uma Calibracao do zero
# ---------------------------------------------------------------------------


def gravar(caminho: Path, sonda: dict, limiar: float, minimo: int) -> None:
    """Atribui SO as chaves desta ferramenta, sobre o arquivo lido do disco.

    Montar uma `Calibracao` do zero apagaria os 13 moldes de glifo e as 3
    ancoras - o modo de falha REAL que a janela quebrada 13 causou em campo em
    2026-08-30 e que custou uma recuperacao a mao. Aqui o arquivo e lido como
    JSON, tres chaves sao atribuidas, e o resto atravessa intacto.
    """
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados["mercado_sonda_do_fundo"] = sonda
    dados["mercado_limiar_de_dispersao_do_fundo"] = limiar
    dados["mercado_minimo_de_linhas_comparadas"] = minimo

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=caminho.parent,
        delete=False,
        suffix=".tmp",
    ) as saida:
        json.dump(dados, saida, indent=2, ensure_ascii=False)
        provisorio = Path(saida.name)
    os.replace(provisorio, caminho)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def _conferir_o_conjunto(gravacoes: Path) -> tuple:
    """As 8 esperadas existem? E o que mais ha na pasta?"""
    faltando = [
        nome for nome in GRAVACOES_DO_CENSO if not (gravacoes / nome).is_dir()
    ]
    presentes = sorted(p.name for p in gravacoes.iterdir() if p.is_dir())
    ignoradas = [n for n in presentes if n not in GRAVACOES_DO_CENSO]
    return faltando, ignoradas


def main(argv=None) -> int:
    analisador = argparse.ArgumentParser(
        description=(
            "Mede a sonda de oclusao, o limiar de dispersao do fundo e o piso "
            "de linhas comparadas sobre as 8 gravacoes do censo."
        )
    )
    analisador.add_argument("--gravacoes", default=str(RAIZ / "recordings"))
    analisador.add_argument("--calibracao", default=str(RAIZ / "calibration.json"))
    analisador.add_argument("--gravar", action="store_true")
    opcoes = analisador.parse_args(argv)

    gravacoes = Path(opcoes.gravacoes).resolve()
    calibracao = Path(opcoes.calibracao).resolve()

    print("=" * 78)
    print("MEDICAO DA SONDA DE OCLUSAO - 02-02 Task 1")
    print("=" * 78)
    print("gravacoes : " + str(gravacoes))
    print("calibracao: " + str(calibracao))

    if not gravacoes.is_dir():
        print("ERRO: " + str(gravacoes) + " nao e um diretorio.")
        return 2

    faltando, ignoradas = _conferir_o_conjunto(gravacoes)
    if faltando:
        print("")
        print("ERRO: pasta esperada do censo AUSENTE:")
        for nome in faltando:
            print("  - " + nome)
        print("")
        print(
            "Medir sobre um conjunto diferente do censo produz um numero que "
            "nao se compara com nenhum outro numero deste projeto. PARANDO."
        )
        return 3

    print("")
    print("AS 8 GRAVACOES DO CENSO (as unicas medidas):")
    for nome in GRAVACOES_DO_CENSO:
        quantos = len(list((gravacoes / nome).glob("frame_*.png")))
        print(f"  + {nome:<42} {quantos:>5} PNG")

    print("")
    print(f"AS {len(ignoradas)} PASTAS IGNORADAS, com o motivo de cada uma:")
    for nome in ignoradas:
        motivo = MOTIVO_PARA_IGNORAR.get(
            nome, "fora do censo de 335 frames da pesquisa"
        )
        quantos = len(list((gravacoes / nome).glob("*.png")))
        print(f"  - {nome:<42} {quantos:>5} PNG  {motivo}")

    cal = Calibracao.carregar(calibracao)
    if not cal.mercado_grade or not cal.mercado_coluna_do_nome:
        print("")
        print(
            "ERRO: o calibration.json nao traz mercado_grade com as colunas. "
            "Rode calibrar-mercado.bat sobre um frame da grade de negociacao."
        )
        return 4
    layout = (cal.mercado_grade or {}).get("layout")
    if layout != "negociacao":
        print("")
        print(
            f"ERRO: mercado_grade.layout e '{layout}', e esta fase le a GRADE "
            "DE NEGOCIACAO. Recalibre."
        )
        return 4

    inicio, fim, avisos = janela_de_busca(cal)
    candidatos, largura = candidatos_de_sonda(inicio, fim)
    print("")
    print("A JANELA DE BUSCA, derivada das colunas calibradas:")
    print(
        f"  x em [{inicio}, {fim}) relativo a esquerda da grade "
        f"({fim - inicio} px)"
    )
    for aviso in avisos:
        print("  " + aviso)
    print(
        f"  sonda de {largura} px deslizando de {PASSO_DA_VARREDURA} em "
        f"{PASSO_DA_VARREDURA} px -> {len(candidatos)} candidatos"
    )
    print(
        "  a pesquisa mediu o vao em x em [180, 510); a varredura decide, e "
        "qualquer discordancia fica escrita acima."
    )

    print("")
    print("Varrendo... (le todo frame com painel aberto das 8 gravacoes)")
    varredura = varrer(gravacoes, cal)
    total_abertos = sum(varredura.abertos_por_gravacao.values())
    for nome in GRAVACOES_DO_CENSO:
        print(
            f"  {nome:<42} "
            f"{varredura.abertos_por_gravacao.get(nome, 0):>4} de "
            f"{varredura.frames_por_gravacao.get(nome, 0):>4} com painel aberto"
        )
    print(f"  TOTAL: {total_abertos} frames com painel aberto")
    if total_abertos == 0:
        print("ERRO: nenhum frame com painel aberto. Nada a medir.")
        return 5

    sonda, tabela = escolher_o_trecho_sem_texto(varredura)

    print("")
    print("TODOS OS TRECHOS CANDIDATOS, contra o gabarito de campo:")
    cabecalho = (
        "  " + "trecho".ljust(16) + "pior LIMPA".rjust(12)
        + "melhor COBERTA".rjust(16) + "folga".rjust(10) + "  veredito"
    )
    print(cabecalho)
    for candidato in tabela:
        if not candidato["separa"]:
            veredito = "NAO SEPARA"
        elif not candidato["mensuravel"]:
            veredito = "DESCARTADO: pior limpa e 0, a folga nao e medicao"
        else:
            veredito = "apto"
        folga = f"{candidato['folga']:.2f}x" if candidato["mensuravel"] else "inf"
        marca = "->" if candidato["coluna"] == sonda else "  "
        trecho = f"[{candidato['dx0']},{candidato['dx1']})"
        print(
            marca + trecho.ljust(16)
            + f"{candidato['pior_limpa']:>12.4f}"
            + f"{candidato['melhor_coberta']:>16.4f}"
            + folga.rjust(10) + "  " + veredito
        )

    if sonda < 0:
        print("")
        print(
            "NENHUM TRECHO SEPARA O GABARITO. Nao ha limiar a propor, e um "
            "limiar que nao separa e pior que nenhum. PARANDO."
        )
        return 6

    dx0, dx1 = varredura.candidatos[sonda]
    print("")
    print(
        f"TRECHO SEM TEXTO ESCOLHIDO: x em [{dx0}, {dx1}) relativo a esquerda "
        f"da grade, folga {FOLGA_NAS_PONTAS}"
    )
    print("  (o que separa o gabarito de campo com a MAIOR folga relativa)")

    passou, diag_nome = conferir_o_gabarito_limpo(varredura, dx0)
    print("")
    print("A GUARDA DE NOME CURTO - o gabarito limpo viu o pior nome do campo?")
    print(
        "  " + "frame do gabarito LIMPO".ljust(58)
        + "tinta".rjust(7) + "  nome declarado"
    )
    for ficha in sorted(
        diag_nome["por_frame"], key=lambda f: f["ponta"], reverse=True
    ):
        declarado = (
            f"`{ficha['nome']}` ({ficha['caracteres']} ch)"
            if ficha["nome"]
            else "(nao declarado)"
        )
        print(
            "  " + ficha["frame"].ljust(58)
            + f"x={ficha['ponta']:<5}".rjust(7) + "  " + declarado
        )
    print(
        f"  piso de comprimento {diag_nome['piso_de_caracteres']} caracteres; "
        f"tinta mais funda do CENSO INTEIRO x={diag_nome['ponta_do_censo']}; "
        f"a sonda escolhida comeca em x={dx0}"
    )
    if not passou:
        print("")
        print("O GABARITO LIMPO NAO SERVE PARA ESCOLHER SONDA. PARANDO.")
        print("  " + str(diag_nome.get("motivo", "")))
        return 8
    if diag_nome.get("sonda_alem_do_censo"):
        print(
            "  PASSOU, mas o ALCANCE passou POR AUSENCIA DE MATERIAL: a sonda "
            "pousa a direita de qualquer tinta de nome do censo, entao nao ha "
            "nome com que exercita-la. Nao e o mesmo que ter sido exercitada."
        )
    else:
        print(
            "  PASSOU: o gabarito declara o pior nome conhecido, a declaracao "
            "confere com os pixels, e ha nome escrevendo dentro desta sonda."
        )

    populacoes = separar_as_populacoes(varredura, sonda)
    print("")
    print("DISTRIBUICAO DE DISPERSAO POR CONDICAO (linhas do gabarito):")
    print(_linha_de_distribuicao("linha limpa", populacoes.limpas))
    print(
        _linha_de_distribuicao("coberta por tooltip", populacoes.cobertas_tooltip)
    )
    print(
        _linha_de_distribuicao(
            "coberta por marcacao de alvo", populacoes.cobertas_alvo
        )
    )

    limiar, diagnostico = propor_o_limiar(populacoes)
    if limiar is None:
        print("")
        print("AS POPULACOES SE SOBREPOEM - NENHUM LIMIAR PROPOSTO.")
        print("  " + str(diagnostico))
        print(
            "  Um limiar que nao separa e pior que nenhum. PARANDO sem propor "
            "numero."
        )
        return 6

    print("")
    print(f"LIMIAR PROPOSTO: {limiar:.6f}")
    print(f"  pior linha LIMPA        {diagnostico['pior_limpa']:.4f}")
    print(f"  melhor linha COBERTA    {diagnostico['melhor_coberta']:.4f}")
    print(f"  folga total             {diagnostico['folga']:.1f}x")
    if "folga_do_alvo" in diagnostico:
        print(
            f"  CASO APERTADO - marcacao de alvo: melhor coberta "
            f"{diagnostico['melhor_alvo']:.4f}, folga "
            f"{diagnostico['folga_do_alvo']:.1f}x sobre a pior limpa"
        )

    custo = descarte_por_gravacao(varredura, sonda, limiar)
    recusadas = sum(a for a, _ in custo.values())
    medidas = sum(b for _, b in custo.values())
    print("")
    print("O CUSTO DO CORTE - linhas recusadas por gravacao:")
    for nome in GRAVACOES_DO_CENSO:
        recusa, total = custo.get(nome, (0, 0))
        fatia = 100.0 * recusa / total if total else 0.0
        print(f"  {nome[9:]:<34} {recusa:>5} de {total:>5}  ({fatia:>5.1f}%)")
    fatia_total = 100.0 * recusadas / max(medidas, 1)
    print(
        "  " + "TOTAL".ljust(34) + f" {recusadas:>5} de {medidas:>5}  "
        f"({fatia_total:>5.1f}%)"
    )

    por_frame = distribuicao_de_linhas_sobreviventes(varredura, sonda, limiar)
    intersecoes = intersecao_entre_frames_vizinhos(varredura, sonda, limiar)

    print("")
    print("LINHAS SOBREVIVENTES POR FRAME ISOLADO (so para conferencia):")
    for nome in GRAVACOES_DO_CENSO:
        print(
            _linha_de_distribuicao(
                nome[9:], [float(v) for v in por_frame.get(nome, [])]
            )
        )

    print("")
    print("INTERSECAO ENTRE FRAMES VIZINHOS (a grandeza que o 02-05 julga):")
    for nome in GRAVACOES_DO_CENSO:
        print(
            _linha_de_distribuicao(
                nome[9:], [float(v) for v in intersecoes.get(nome, [])]
            )
        )

    todos_por_frame = [float(v) for vs in por_frame.values() for v in vs]
    todas_intersecoes = [float(v) for vs in intersecoes.values() for v in vs]
    print("")
    print("  AS DUAS GRANDEZAS LADO A LADO:")
    print(_linha_de_distribuicao("por frame isolado", todos_por_frame))
    print(_linha_de_distribuicao("intersecao de vizinhos", todas_intersecoes))
    if todos_por_frame and todas_intersecoes:
        diferenca = float(
            np.median(todos_por_frame) - np.median(todas_intersecoes)
        )
        print(
            f"  diferenca de mediana: {diferenca:+.2f} linhas - se for zero, a "
            "oclusao e ESTAVEL entre frames vizinhos, e isso e um achado."
        )

    pares = pares_vizinhos_detalhados(varredura, sonda, limiar)
    print("")
    print("OS PARES VIZINHOS, classificados pela MEDIDA (nunca pela pasta):")
    print(
        _linha_de_distribuicao(
            "normais (os dois frames inteiros)",
            [float(t) for _, t, inteiro, _ in pares if inteiro],
        )
    )
    print(
        _linha_de_distribuicao(
            "majoritariamente cobertos",
            [float(t) for _, t, _, coberto in pares if coberto],
        )
    )
    print(
        _linha_de_distribuicao(
            "parcialmente cobertos",
            [
                float(t)
                for _, t, inteiro, coberto in pares
                if not inteiro and not coberto
            ],
        )
    )

    minimo, diag_piso = propor_o_minimo_comparado(
        pares, varredura.linhas_por_pagina
    )
    if minimo is None:
        print("")
        print("AS DUAS POPULACOES DE PAR SE TOCAM - NENHUM PISO PROPOSTO.")
        print("  " + str(diag_piso))
        return 7

    print("")
    print(f"PISO DE LINHAS COMPARADAS PROPOSTO: {minimo}")
    print(f"  p5 dos pares normais      {diag_piso['p5_normais']:.2f}")
    print(f"  teto dos pares cobertos   {diag_piso['teto_coberto']}")
    print(f"  faixa possivel            {diag_piso['faixa']}")
    print(
        f"  folga abaixo/acima        {diag_piso['folga_abaixo']} / "
        f"{diag_piso['folga_acima']:.2f}"
    )

    sonda_gravada = {"dx0": int(dx0), "dx1": int(dx1), "folga": FOLGA_NAS_PONTAS}
    print("")
    print("O QUE VAI PARA O calibration.json:")
    print("  mercado_sonda_do_fundo               = " + str(sonda_gravada))
    print(f"  mercado_limiar_de_dispersao_do_fundo = {limiar:.6f}")
    print(f"  mercado_minimo_de_linhas_comparadas  = {minimo}")

    if opcoes.gravar:
        gravar(calibracao, sonda_gravada, float(limiar), int(minimo))
        print("")
        print("GRAVADO em " + str(calibracao) + " (load-mutate-save).")
    else:
        print("")
        print("(nada gravado - rode de novo com --gravar para persistir)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
