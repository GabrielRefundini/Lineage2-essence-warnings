"""A varredura que MEDE a sonda de oclusao, o limiar de dispersao e o piso.

Esta ferramenta nao decide nada por gosto: ela varre as 9 gravacoes de campo
que `GRAVACOES_DA_VARREDURA` nomeia, mede, e PROPOE tres numeros que vao para o `calibration.json`. Nenhum
deles pode entrar no fonte de producao - a disciplina fundadora do projeto e que
constante magica no codigo garante reescrita na primeira "nao funciona no meu
PC", e um numero escolhido em vez de medido e uma promessa que ninguem conferiu.

    mercado_sonda_do_fundo               a BANDA sem texto da linha (dx0, dx1,
                                         dy0, dy1, folga), ESCOLHIDA por
                                         varredura
    mercado_limiar_de_dispersao_do_fundo acima dele a linha esta COBERTA
    mercado_minimo_de_linhas_comparadas  o piso que impede o ACORDO TRIVIAL do
                                         estabilizador do 02-05

A DIRECAO MUDOU EM 2026-09-01, E E A MUDANCA PRINCIPAL DESTE ARQUIVO
--------------------------------------------------------------------
A sonda era um trecho estreito em X, alto quanto a linha, e esta varredura o
deslizava HORIZONTALMENTE procurando um vao a direita do nome do item. A
premissa era que existisse tal vao. Nao existe - a coluna do nome e a de
quantidade sao adjacentes, e o nome cresce para dentro do espaco que a sonda
ocuparia -, e o campo cobrou a premissa duas vezes com um caractere de
diferenca:

    207..417  morreu contra `...Enchant C-grade Armor`  (40 ch, tinta ate x=246)
    246..396  morreu contra `...Enchant C-grade Weapon` (41 ch, tinta ate x=255)

Agora a sonda e uma BANDA: a janela inteira em X, dentro de uma faixa fina de
altura acima do texto. O nome cresce em X e nao em Y, entao a banda nao disputa
espaco com ele e nao tem "proximo item mais comprido". Nao ha mais `dx0` a
escolher; a varredura desliza em Y, e escolhe pela folga NO PIOR CASO sob uma
deriva de +-2 px na origem da linha.

A MOLDURA ENTRE LINHAS foi medida como alternativa e REPROVADA: ela e o degrau
da listra alternada, e sobre um degrau a dispersao e ~0,5 por construcao - uma
linha LIMPA le 0,5000 ali contra 0,4944 sob tooltip. Nao ha limiar que separe.

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
`recordings/` tem 17 pastas. O censo de 335 frames da pesquisa cobriu 8, e ESTA
ferramenta mede essas 8 mais UMA, gravada em 2026-09-01 porque e o unico
material que contem o pior nome que o campo ja produziu. As duas listas sao
separadas de proposito (`GRAVACOES_DO_CENSO` e `GRAVACOES_DA_VARREDURA`): o
censo e um artefato historico que outras tres ferramentas importam daqui, e uma
delas tem fixture versionado preso a ele. Sao so essas nove que entram. A lista e constante deste modulo e as outras pastas sao
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
# O CONJUNTO DE MEDICAO - as 8 do censo, a de nome longo, e o motivo das outras
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

# A GRAVACAO DE 2026-09-01, e ela NAO ENTRA no censo acima. A distincao e
# deliberada e custou uma decisao; o registro fica para nao ser desfeita.
#
# `GRAVACOES_DO_CENSO` nao e "o material que as ferramentas medem": e o CENSO DE
# 335 FRAMES DA PESQUISA, um artefato historico datado. Outras tres ferramentas
# o IMPORTAM deste modulo, e uma delas - `medir_agrupamento_de_nome.py` - tem um
# fixture VERSIONADO (`leituras_de_nome.json`, 3.511 linhas lidas por OCR) cujo
# teste afirma que ele cobre exatamente essas oito. Empurrar a nona para dentro
# do censo quebraria esse fixture calado, e "consertar" o teste exigiria
# reprocessar 3.511 linhas com o motor de OCR - trabalho que nao tem nada a ver
# com a sonda de oclusao.
#
# Ela e material NOVO, gravado em 2026-09-01 PARA ESTA MEDICAO, e e o unico que
# contem o pior nome que o campo ja produziu: `Protecting Scroll: Enchant
# C-grade Weapon`, 41 caracteres, tinta ate x=255. Sao 5 frames de janela
# completa com o painel aberto na aba Enhancement > Scrolls.
GRAVACAO_DO_NOME_LONGO = "20260901-000043-nome-longo-weapon"

# O QUE ESTA FERRAMENTA MEDE. Reescrever isto como um glob desfaz a guarda
# inteira: `pre-voo` sozinha tem 1.502 PNGs de outro dia e dominaria qualquer
# distribuicao. A lista e NOMEADA, e crescer nela e um ato, nao um acidente.
GRAVACOES_DA_VARREDURA = GRAVACOES_DO_CENSO + (GRAVACAO_DO_NOME_LONGO,)

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

# A DIRECAO DA VARREDURA MUDOU EM 2026-09-01, E ESSA E A MUDANCA INTEIRA.
#
# Ate aqui a sonda era um trecho ESTREITO EM X e alto quanto a linha, e a
# varredura o deslizava horizontalmente procurando um vao a direita do nome. A
# premissa era que existisse tal vao. NAO EXISTE, e o campo cobrou duas vezes:
#
#     207..417   morreu contra `...Enchant C-grade Armor`  (40 ch, tinta x=246)
#     246..396   morreu contra `...Enchant C-grade Weapon` (41 ch, tinta x=255)
#
# UM caractere entre as duas. O maior corredor livre e de 172 px contra frames
# conferidos e de 56 a 91 px contra o censo de 3.994 linhas; a sonda precisava
# de 150. Deslizar de novo so escolheria qual item quebra a seguir.
#
# AGORA A SONDA E UMA BANDA: a JANELA INTEIRA em x, dentro de uma faixa fina de
# altura. O nome cresce em X e nao em Y - a linha tem 45 px de altura e o nome
# ocupa 12 deles -, entao uma banda numa margem vertical nao disputa espaco com
# o texto e nao tem "proximo item mais comprido".
#
# NAO HA MAIS `dx0` A ESCOLHER, e por isso nao ha mais passo horizontal: a banda
# usa `janela_de_busca` do comeco ao fim. A varredura desliza em Y.

# As alturas de banda comparadas, em pixels. A faixa util tem 15 px em cima e 16
# embaixo (medido: dentro da janela x[42,489) a tinta vive em dy[15,26]), entao
# alturas acima de 14 nao cabem em margem nenhuma sem comer texto.
ALTURAS_DA_BANDA = (4, 6, 8, 10, 12)

# A DERIVA CONFERIDA, em pixels, na origem vertical da linha. E o criterio que
# nao existia nas duas escolhas anteriores, e a falta dele e o formato do
# defeito: uma escolha equilibrada no fio da navalha passa na medicao e morre no
# campo.
#
# MEDIDO, e e por isso que ele entra: a banda dy[0,8) tem a MELHOR folga
# estatica de todas (112,7x) e desaba para 0,9x quando a linha anda 2 px, porque
# a -2 px ela come a moldura da linha de cima. A banda dy[2,10) mede 81,2x
# estatica e SEGURA 52,6x sob deriva. Escolher pela folga estatica escolheria a
# primeira.
#
# 2 px nao e chute. `altura_da_linha` e um inteiro (45) para um passo que a UI
# nao promete ser inteiro, e o erro acumula ate a decima linha; e a origem vem
# de casamento de molde em pixel inteiro, cujo pior positivo de campo e 0,41
# (tooltip por cima da faixa de titulo).
DERIVA_CONFERIDA = 2

# A folga MINIMA, em pixels, entre a banda e a tinta da linha. Abaixo disto a
# guarda PARA: uma banda encostada no texto e a sonda de 31/08 outra vez, so que
# no outro eixo.
FOLGA_VERTICAL_MINIMA = 2

# As linhas de folga em cada ponta do recorte. ELA E ZERO AGORA, E ISSO NAO E
# DESLIGAR A PROTECAO - E MUDAR ONDE ELA MORA.
#
# A folga existia para manter fora do recorte a linha de TRANSICAO entre duas
# bandas da listra alternada, que nao pertence a nenhuma das duas e diluiria a
# medida. Com a sonda antiga - alta quanto a linha inteira - a transicao estava
# necessariamente dentro do retangulo, e so dava para apara-la.
#
# A banda nao tem esse problema: ela e ESCOLHIDA longe da transicao, e a guarda
# de folga vertical CONFERE que ela ficou. Aparar 2 px de uma banda de 8 jogaria
# fora um quarto do sinal para proteger contra uma coisa que ja nao esta la.
# MEDIDO: a transicao vive em dy[43,45); a banda escolhida esta em dy[2,10).
FOLGA_NAS_PONTAS = 0

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
    # OS CINCO DO PIOR NOME CONHECIDO, gravados em 2026-09-01. Sao eles que
    # provam que a banda nao depende do comprimento do nome: 41 caracteres,
    # tinta ate x=255, e a banda le 0,0017 a 0,0031 nas cinquenta linhas.
    #
    # Os CINCO frames entram, e nao um. O defeito de 31/08 foi medido em UM
    # frame por condicao, e um frame nao mostra se a leitura e estavel. Cinco
    # frames da mesma pagina mostram, e custam 50 linhas de populacao.
    (
        "20260901-000043-nome-longo-weapon",
        "frame_000000.png",
        tuple(range(10)),
        "Protecting Scroll: Enchant C-grade Weapon",
    ),
    (
        "20260901-000043-nome-longo-weapon",
        "frame_000001.png",
        tuple(range(10)),
        "Protecting Scroll: Enchant C-grade Weapon",
    ),
    (
        "20260901-000043-nome-longo-weapon",
        "frame_000002.png",
        tuple(range(10)),
        "Protecting Scroll: Enchant C-grade Weapon",
    ),
    (
        "20260901-000043-nome-longo-weapon",
        "frame_000003.png",
        tuple(range(10)),
        "Protecting Scroll: Enchant C-grade Weapon",
    ),
    (
        "20260901-000043-nome-longo-weapon",
        "frame_000004.png",
        tuple(range(10)),
        "Protecting Scroll: Enchant C-grade Weapon",
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
#
# SUBIU DE 40 PARA 41 EM 2026-09-01, e a subida de UM caractere e a historia
# toda: `...Enchant C-grade Armor` (40) inka ate x=246 e `...Enchant C-grade
# Weapon` (41) inka ate x=255. Oito pixels por um caractere, e a sonda horizontal
# de 31/08 comecava em 246.
#
# COM A BANDA, ESTE PISO DEIXA DE SER A DEFESA PRINCIPAL, e continua aqui de
# proposito. A banda nao depende do comprimento do nome, mas a guarda que
# CONFERE isso (a folga vertical, em `conferir_o_gabarito_limpo`) precisa de um
# gabarito que contenha nome comprido para ter o que conferir. Sem ele a folga
# vertical seria medida contra nome curto e diria "sobra espaco" sobre coisa
# nenhuma - exatamente o erro de 2026-08-30, um eixo adiante.
PIOR_NOME_CONHECIDO_EM_CARACTERES = 41


# ---------------------------------------------------------------------------
# O que a varredura produz
# ---------------------------------------------------------------------------


def frames_do_gabarito() -> set:
    """Os `(gravacao, arquivo)` que participam da ESCOLHA da banda.

    So eles pagam a medicao com deriva. Derivar todos os 522 frames triplicaria
    a varredura para produzir numero que ninguem le: a escolha e feita contra o
    gabarito, e o resto do censo entra depois, na conta do CUSTO do corte.
    """
    return {(g, a) for g, a, _ in GABARITO_COBERTAS} | {
        (g, a) for g, a, _, _ in GABARITO_LIMPAS
    }


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
    # A FAIXA DE dy com tinta de cada linha, DENTRO da janela de busca:
    # `(topo, base)` por linha, `(-1, -1)` quando a linha nao tem tinta. E o
    # insumo da guarda de FOLGA VERTICAL - a que substituiu a de alcance quando
    # a sonda virou banda.
    faixas_da_tinta: np.ndarray | None = None
    # As mesmas dispersoes, medidas com a origem da linha DESLOCADA. Chave =
    # deslocamento em px; so os frames do GABARITO a preenchem, porque so eles
    # participam da escolha. Vazio nos demais.
    dispersoes_por_deriva: dict = field(default_factory=dict)


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


def candidatos_de_banda(altura_da_linha: int) -> list:
    """As bandas que a varredura vai comparar: `(dy0, dy1)`, todas em Y.

    A largura NAO entra: toda banda usa `janela_de_busca` inteira. Era essa
    escolha - onde por os 150 px - que o campo derrubou duas vezes, e ela deixou
    de existir. O que sobra a escolher e a ALTURA e a POSICAO VERTICAL, e nenhuma
    das duas depende do nome do item.
    """
    candidatos = []
    for altura in ALTURAS_DA_BANDA:
        if altura > altura_da_linha:
            continue
        for dy0 in range(0, int(altura_da_linha) - int(altura) + 1):
            candidatos.append((dy0, dy0 + int(altura)))
    return candidatos


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


def faixa_da_tinta_da_linha(
    bgr: np.ndarray,
    gx: int,
    topo: int,
    altura: int,
    dx0: int,
    dx1: int,
) -> tuple[int, int]:
    """Em que dy a tinta desta linha COMECA e ACABA, dentro da janela de busca.

    E a medida gemea de `ponta_da_tinta_do_nome`, no outro eixo, e existe pelo
    mesmo motivo: a guarda precisa confrontar a banda escolhida com PIXEIS, e nao
    com a promessa de que "sobra espaco em cima do texto".

    A janela e a de busca, e nao a linha inteira. As colunas Total e Unit price
    ficam de fora dela porque a arte delas escreve de dy 0 a dy 44 - MEDIDO nas
    120 linhas limpas do gabarito - e nao deixa margem vertical nenhuma. Medir
    contra a linha inteira diria "nao ha margem" sobre uma janela que tem 15 px
    dela.

    A mascara e `identidade.mascara_de_texto`, a MESMA do resto do projeto.
    `(-1, -1)` quando nao ha tinta - linha vazia e uma resposta legitima.
    """
    if bgr is None or bgr.size == 0:
        return -1, -1
    recorte = bgr[topo : topo + altura, gx + dx0 : gx + dx1]
    if recorte.size == 0:
        return -1, -1
    linhas = np.flatnonzero(mascara_de_texto(recorte).any(axis=1))
    if linhas.size == 0:
        return -1, -1
    return int(linhas[0]), int(linhas[-1])


# ---------------------------------------------------------------------------
# A varredura
# ---------------------------------------------------------------------------


def varrer(gravacoes: Path, cal: Calibracao) -> Varredura:
    """Todas as linhas de todos os frames com painel aberto das 9 gravacoes.

    Cada frame recebe a dispersao de TODAS as bandas candidatas na origem
    calibrada. Os frames do GABARITO recebem tambem a dispersao com a origem
    DESLOCADA de +-`DERIVA_CONFERIDA` px, porque e sobre a deriva que a escolha
    se decide - e so o gabarito participa da escolha, entao so ele paga.
    """
    grade = cal.mercado_grade or {}
    linhas = int(grade["linhas_por_pagina"])
    altura_da_linha = int(grade["altura_da_linha"])
    ancoras = ancoras_de_calibracao(cal.mercado_ancoras)
    limiar = float(cal.mercado_limiar_da_ancora or 0.73)
    coluna_do_nome = cal.mercado_coluna_do_nome or {}

    inicio, fim, _ = janela_de_busca(cal)
    candidatos = candidatos_de_banda(altura_da_linha)
    derivas = [
        d
        for d in range(-DERIVA_CONFERIDA, DERIVA_CONFERIDA + 1)
        if d != 0
    ]
    do_gabarito = frames_do_gabarito()

    resultado = Varredura(
        candidatos=candidatos,
        janela_derivada=(inicio, fim),
        linhas_por_pagina=linhas,
    )

    for nome in GRAVACOES_DA_VARREDURA:
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
            e_do_gabarito = (nome, caminho.name) in do_gabarito

            dispersoes = np.full((linhas, len(candidatos)), np.nan)
            por_deriva = {
                d: np.full((linhas, len(candidatos)), np.nan) for d in derivas
            } if e_do_gabarito else {}
            pontas = np.full(linhas, -1, dtype=int)
            faixas = np.full((linhas, 2), -1, dtype=int)
            for indice in range(linhas):
                topo = gy + indice * altura_da_linha
                pontas[indice] = ponta_da_tinta_do_nome(
                    frame, coluna_do_nome, origem_x, gx, topo, altura_da_linha
                )
                faixas[indice] = faixa_da_tinta_da_linha(
                    frame, gx, topo, altura_da_linha, inicio, fim
                )
                for coluna, (dy0, dy1) in enumerate(candidatos):
                    medido = nivel_de_fundo_da_linha(
                        cinza,
                        (gx + inicio, topo + dy0, fim - inicio, dy1 - dy0),
                        FOLGA_NAS_PONTAS,
                    )
                    if medido is not None:
                        dispersoes[indice, coluna] = medido[1]
                    for deriva in por_deriva:
                        movido = nivel_de_fundo_da_linha(
                            cinza,
                            (
                                gx + inicio,
                                topo + deriva + dy0,
                                fim - inicio,
                                dy1 - dy0,
                            ),
                            FOLGA_NAS_PONTAS,
                        )
                        if movido is not None:
                            por_deriva[deriva][indice, coluna] = movido[1]
            resultado.leituras.append(
                LeituraDeFrame(
                    nome,
                    caminho.name,
                    dispersoes,
                    pontas,
                    faixas,
                    por_deriva,
                )
            )
        resultado.abertos_por_gravacao[nome] = abertos
    return resultado


# ---------------------------------------------------------------------------
# A escolha do trecho, e as duas populacoes
# ---------------------------------------------------------------------------


def _valores_do_gabarito(
    varredura: Varredura, tabela, sonda: int, deriva: int = 0
) -> list:
    """As dispersoes das linhas que o gabarito nomeia, na banda `sonda`.

    `deriva` diferente de zero le a matriz medida com a origem da linha
    deslocada. Vazio quando aquele frame nao mediu deriva - o que so acontece
    fora do gabarito, e o gabarito e tudo o que esta funcao le.
    """
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
        matriz = (
            leitura.dispersoes
            if deriva == 0
            else leitura.dispersoes_por_deriva.get(deriva)
        )
        if matriz is None:
            continue
        for linha in linhas:
            valor = matriz[linha, sonda]
            if not np.isnan(valor):
                valores.append(float(valor))
    return valores


def escolher_a_banda(varredura: Varredura) -> tuple:
    """A banda que separa o gabarito com a maior folga NO PIOR CASO SOB DERIVA.

    A folga e `menor dispersao COBERTA / maior dispersao LIMPA` sobre as linhas
    que o gabarito nomeia. Em razao, e nao em diferenca: a dispersao varre tres
    ordens de grandeza entre uma linha limpa e uma sob tooltip, e uma diferenca
    absoluta trataria 0,50 contra 0,45 como igual a 0,05 contra 0,00.

    A NOVIDADE DE 2026-09-01 E QUE A FOLGA E TOMADA NO PIOR CASO SOBRE A DERIVA,
    e nao no ponto calibrado. Esta e a correcao do FORMATO do defeito, e nao do
    defeito: as duas escolhas anteriores foram feitas por folga no ponto, e as
    duas nasceram equilibradas numa margem que o campo desfez. MEDIDO aqui:

        banda dy[0, 8)   folga no ponto 112,7x   sob deriva de 2 px   0,9x
        banda dy[2,10)   folga no ponto  81,2x   sob deriva de 2 px  52,6x

    Escolher pelo primeiro numero escolheria a banda que encosta na moldura da
    linha de cima e perde a separacao inteira ao andar 2 px. A banda que ganha
    e a que ainda separa quando a linha nao esta onde a calibracao diz.

    UMA BANDA QUE SO SEPARA NA ORIGEM EXATA E DESCARTADA, e a recusa e a mesma
    em espirito do descarte da "folga infinita": uma separacao que so existe sob
    condicao perfeita nao foi medida, foi encenada.

    UMA BANDA CUJA PIOR LIMPA E EXATAMENTE ZERO TAMBEM E DESCARTADA. A razao
    contra zero nao e uma medicao, e uma divisao por zero vestida de resultado.

    Devolve `(indice_escolhido, tabela)`, com a tabela inteira dos candidatos
    para o relatorio - a escolha tem de poder ser conferida, nao acreditada.
    """
    derivas = [
        d for d in range(-DERIVA_CONFERIDA, DERIVA_CONFERIDA + 1) if d != 0
    ]
    tabela = []
    for coluna in range(len(varredura.candidatos)):
        cobertas = _valores_do_gabarito(varredura, GABARITO_COBERTAS, coluna)
        limpas = _valores_do_gabarito(varredura, GABARITO_LIMPAS, coluna)
        if not cobertas or not limpas:
            continue
        dy0, dy1 = varredura.candidatos[coluna]
        pior_limpa, melhor_coberta = max(limpas), min(cobertas)
        mensuravel = pior_limpa > 0.0

        pior_limpa_derivada = pior_limpa
        melhor_coberta_derivada = melhor_coberta
        for deriva in derivas:
            limpas_movidas = _valores_do_gabarito(
                varredura, GABARITO_LIMPAS, coluna, deriva
            )
            cobertas_movidas = _valores_do_gabarito(
                varredura, GABARITO_COBERTAS, coluna, deriva
            )
            if limpas_movidas:
                pior_limpa_derivada = max(
                    pior_limpa_derivada, max(limpas_movidas)
                )
            if cobertas_movidas:
                melhor_coberta_derivada = min(
                    melhor_coberta_derivada, min(cobertas_movidas)
                )
        mensuravel_derivada = pior_limpa_derivada > 0.0
        separa_derivada = (
            melhor_coberta_derivada > pior_limpa_derivada
            and mensuravel_derivada
        )
        tabela.append(
            {
                "coluna": coluna,
                "dy0": dy0,
                "dy1": dy1,
                "pior_limpa": pior_limpa,
                "melhor_coberta": melhor_coberta,
                "separa": melhor_coberta > pior_limpa,
                "mensuravel": mensuravel,
                "folga": (
                    melhor_coberta / pior_limpa if mensuravel else float("inf")
                ),
                "pior_limpa_derivada": pior_limpa_derivada,
                "melhor_coberta_derivada": melhor_coberta_derivada,
                "separa_derivada": separa_derivada,
                "folga_derivada": (
                    melhor_coberta_derivada / pior_limpa_derivada
                    if mensuravel_derivada
                    else float("inf")
                ),
            }
        )

    aptos = [
        c
        for c in tabela
        if c["separa"] and c["mensuravel"] and c["separa_derivada"]
    ]
    if not aptos:
        return -1, tabela
    melhor = max(aptos, key=lambda c: c["folga_derivada"])
    return int(melhor["coluna"]), tabela


# ---------------------------------------------------------------------------
# A GUARDA DE NOME CURTO - a que faltou em 2026-08-30 e custou 31 paginas
# ---------------------------------------------------------------------------


def conferir_o_gabarito_limpo(varredura: Varredura, banda: tuple) -> tuple:
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

    (3) FOLGA VERTICAL. A banda escolhida tem de ficar fora da faixa de dy onde
        a tinta das linhas LIMPAS mora, com pelo menos `FOLGA_VERTICAL_MINIMA`
        px de sobra dos dois lados que existirem.

        ESTA CONFERENCIA SUBSTITUIU A DE ALCANCE em 2026-09-01, e a substituicao
        e obrigatoria porque o eixo mudou. A de alcance perguntava "a tinta do
        nome chega ao `dx0` da sonda?", e com uma banda que usa a janela inteira
        em x a resposta e sempre sim, para qualquer nome - a pergunta virou
        vacua, e uma guarda vacua e pior que nenhuma porque parece verde.

        A pergunta certa, no eixo certo, e a MESMA pergunta: a sonda esta em
        cima do texto? Antes se media em x, agora em y. MEDIDO nas 120 linhas
        limpas do gabarito, dentro da janela de busca, a tinta vive em dy[15,26]
        - entao a banda dy[2,10) tem 5 px de folga contra o topo do texto, e a
        guarda imprime esse numero em vez de prometer que ele existe.

        A folga de baixo e contra `dy` = 0, que e onde a moldura da linha
        anterior acaba. A banda nao pode encostar la tambem: MEDIDO, dy[0,8)
        perde a separacao inteira quando a linha anda 2 px para cima.

    NADA AQUI E CIRCULAR. Compara-se comprimento declarado com comprimento
    declarado, e ponta de tinta (pixels, `ponta_da_tinta_do_nome`) com ponta de
    tinta. Em ponto nenhum entra a dispersao ou o limiar que a ferramenta ainda
    vai propor; se entrasse, estaria conferindo o resultado com o resultado.

    A regua, para quem ler isto sem ela na mao: x=255 e `Protecting Scroll:
    Enchant C-grade Weapon`, 41 caracteres; x=246 e o mesmo com `Armor`, 40;
    x=208 e `+6 Agathion Alpha Hunter Sealed`, 31; x=169 e `Hardin's Soul
    Crystal Lv. 1`, 27.

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
    # A FAIXA DE TINTA das linhas LIMPAS, em dy, dentro da janela de busca. E o
    # insumo da conferencia (3), e ela le so as linhas que o gabarito declara
    # limpas: numa linha coberta a "tinta" e a tooltip, e ela cobre tudo.
    topos, bases = [], []
    for gravacao, arquivo, linhas, _nome in GABARITO_LIMPAS:
        leitura = indice.get((gravacao, arquivo))
        if leitura is None or leitura.faixas_da_tinta is None:
            continue
        for linha in linhas:
            topo, base = (int(v) for v in leitura.faixas_da_tinta[linha])
            if topo < 0:
                continue
            topos.append(topo)
            bases.append(base)

    dy0, dy1 = (int(v) for v in banda)
    diagnostico = {
        "banda": (dy0, dy1),
        "tinta_topo": min(topos) if topos else -1,
        "tinta_base": max(bases) if bases else -1,
        "n_linhas_com_tinta": len(topos),
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

    # (3) folga vertical
    if not topos:
        diagnostico["motivo"] = (
            "nenhuma linha do gabarito LIMPO tem tinta mensuravel DENTRO da "
            "janela de busca. Sem tinta nao ha do que a banda se afastar, e a "
            "folga vertical seria medida contra coisa nenhuma."
        )
        return False, diagnostico

    tinta_topo, tinta_base = diagnostico["tinta_topo"], diagnostico["tinta_base"]
    folga_acima = tinta_topo - dy1  # banda inteiramente ACIMA do texto
    folga_abaixo = dy0 - tinta_base  # banda inteiramente ABAIXO do texto
    diagnostico["folga_acima_do_texto"] = folga_acima
    diagnostico["folga_abaixo_do_texto"] = folga_abaixo
    diagnostico["folga_da_moldura"] = dy0
    diagnostico["folga_vertical_minima"] = FOLGA_VERTICAL_MINIMA

    if folga_acima < 0 and folga_abaixo < 0:
        diagnostico["motivo"] = (
            f"A BANDA ESTA EM CIMA DO TEXTO. Ela ocupa dy[{dy0}, {dy1}) e a "
            f"tinta das linhas LIMPAS vive em dy[{tinta_topo}, {tinta_base}] "
            "dentro da janela de busca. Uma banda sobre o texto recusa linha "
            "limpa por ela ser legivel - e o defeito de 2026-08-31 outra vez, "
            "no outro eixo."
        )
        return False, diagnostico

    folga_do_texto = max(folga_acima, folga_abaixo)
    diagnostico["folga_do_texto"] = folga_do_texto
    if folga_do_texto < FOLGA_VERTICAL_MINIMA:
        diagnostico["motivo"] = (
            f"a banda dy[{dy0}, {dy1}) fica a apenas {folga_do_texto} px da "
            f"tinta (dy[{tinta_topo}, {tinta_base}]), contra um minimo de "
            f"{FOLGA_VERTICAL_MINIMA}. Margem de um pixel e o formato do "
            "defeito que ja custou 31 paginas: ela passa na medicao e some no "
            "primeiro frame em que a linha nao esta onde a calibracao diz."
        )
        return False, diagnostico
    if dy0 < FOLGA_VERTICAL_MINIMA and folga_abaixo < 0:
        diagnostico["motivo"] = (
            f"a banda comeca em dy={dy0}, a menos de {FOLGA_VERTICAL_MINIMA} "
            "px da moldura da linha anterior. MEDIDO, a moldura e o DEGRAU da "
            "listra alternada e le dispersao ~0,5 mesmo numa linha limpa: uma "
            "banda que a alcance ao derivar perde a separacao inteira."
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


def sensibilidade_do_corte(
    varredura: Varredura, sonda: int, limiar: float
) -> list:
    """Quantas linhas do CENSO INTEIRO caem de cada lado, em varios limiares.

    ESTA SECAO NASCEU DE UMA PERGUNTA QUE PRECISAVA DE RESPOSTA MEDIDA. Quando a
    sonda virou banda, o limiar proposto SUBIU em valor absoluto - de 0,003607
    para ~0,030 - e "o limiar subiu" soa como "a peneira afrouxou". Nao e a
    mesma coisa, e a diferenca so aparece com numero:

    - o limiar sobe porque a populacao COBERTA sobe (a banda le a moldura do
      marcador de alvo em 0,2497, onde a sonda horizontal lia 0,0208). O corte
      acompanha o sinal que ele corta.
    - a peneira aperta ou afrouxa conforme a FOLGA, e ela vai de 1,8x para 68x.

    Mas nada disso responde a pergunta que importa: existe massa de linhas de
    campo ENTRE a pior limpa e o limiar? Se existir, o limiar esta engolindo
    linhas que antes eram recusadas, e ai sim ele afrouxou. Se o vale for vazio,
    o limiar pousa num deserto e mover-lo nao muda nada.

    Devolve `[(fator, limiar, recusadas, total)]`, com o limiar proposto
    multiplicado e dividido - a leitura util e a coluna `recusadas`: ela quase
    nao pode mudar entre 0,25x e 4x, ou o corte esta em cima de uma ladeira.
    """
    fatores = (0.25, 0.5, 1.0, 2.0, 4.0)
    todas = []
    for leitura in varredura.leituras:
        coluna = leitura.dispersoes[:, sonda]
        todas.extend(float(v) for v in coluna if not np.isnan(v))
    arranjo = np.asarray(todas, dtype=np.float64)
    return [
        (
            fator,
            limiar * fator,
            int(np.count_nonzero(arranjo > limiar * fator)),
            int(arranjo.size),
        )
        for fator in fatores
    ]


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
        nome
        for nome in GRAVACOES_DA_VARREDURA
        if not (gravacoes / nome).is_dir()
    ]
    presentes = sorted(p.name for p in gravacoes.iterdir() if p.is_dir())
    ignoradas = [n for n in presentes if n not in GRAVACOES_DA_VARREDURA]
    return faltando, ignoradas


def main(argv=None) -> int:
    analisador = argparse.ArgumentParser(
        description=(
            "Mede a sonda de oclusao, o limiar de dispersao do fundo e o piso "
            "de linhas comparadas sobre as 8 gravacoes do censo mais a "
            "gravacao de nome longo."
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
    print(
        f"AS {len(GRAVACOES_DA_VARREDURA)} GRAVACOES MEDIDAS "
        f"(as {len(GRAVACOES_DO_CENSO)} do censo mais a de nome longo):"
    )
    for nome in GRAVACOES_DA_VARREDURA:
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
    altura_da_linha = int((cal.mercado_grade or {})["altura_da_linha"])
    candidatos = candidatos_de_banda(altura_da_linha)
    print("")
    print("A JANELA DE BUSCA, derivada das colunas calibradas:")
    print(
        f"  x em [{inicio}, {fim}) relativo a esquerda da grade "
        f"({fim - inicio} px) - a banda usa a janela INTEIRA, nao ha dx0 a "
        "escolher"
    )
    for aviso in avisos:
        print("  " + aviso)
    print(
        f"  bandas de {ALTURAS_DA_BANDA} px deslizando em Y dentro dos "
        f"{altura_da_linha} px da linha -> {len(candidatos)} candidatos"
    )
    print(
        f"  cada candidato e medido tambem com a origem da linha deslocada de "
        f"+-{DERIVA_CONFERIDA} px, e a escolha usa a folga do PIOR caso"
    )

    print("")
    print(
        f"Varrendo... (le todo frame com painel aberto das "
        f"{len(GRAVACOES_DA_VARREDURA)} gravacoes)"
    )
    varredura = varrer(gravacoes, cal)
    total_abertos = sum(varredura.abertos_por_gravacao.values())
    for nome in GRAVACOES_DA_VARREDURA:
        print(
            f"  {nome:<42} "
            f"{varredura.abertos_por_gravacao.get(nome, 0):>4} de "
            f"{varredura.frames_por_gravacao.get(nome, 0):>4} com painel aberto"
        )
    print(f"  TOTAL: {total_abertos} frames com painel aberto")
    if total_abertos == 0:
        print("ERRO: nenhum frame com painel aberto. Nada a medir.")
        return 5

    sonda, tabela = escolher_a_banda(varredura)

    print("")
    print("AS BANDAS CANDIDATAS, contra o gabarito de campo:")
    print("  (as 20 melhores por folga SOB DERIVA, das " + str(len(tabela)) + ")")
    cabecalho = (
        "  " + "banda dy".ljust(14) + "pior LIMPA".rjust(12)
        + "melhor COBERTA".rjust(16) + "folga".rjust(10)
        + "folga s/deriva".rjust(16) + "  veredito"
    )
    print(cabecalho)
    ordenada = sorted(
        tabela,
        key=lambda c: (
            c["folga_derivada"] if c.get("separa_derivada") else -1.0
        ),
        reverse=True,
    )
    for candidato in ordenada[:20]:
        if not candidato["separa"]:
            veredito = "NAO SEPARA"
        elif not candidato["mensuravel"]:
            veredito = "DESCARTADO: pior limpa e 0, a folga nao e medicao"
        elif not candidato["separa_derivada"]:
            veredito = (
                f"DESCARTADO: so separa na origem exata (a +-"
                f"{DERIVA_CONFERIDA} px as populacoes se tocam)"
            )
        else:
            veredito = "apto"
        folga = f"{candidato['folga']:.2f}x" if candidato["mensuravel"] else "inf"
        folga_d = (
            f"{candidato['folga_derivada']:.2f}x"
            if candidato["separa_derivada"]
            else "-"
        )
        marca = "->" if candidato["coluna"] == sonda else "  "
        trecho = f"[{candidato['dy0']},{candidato['dy1']})"
        print(
            marca + trecho.ljust(14)
            + f"{candidato['pior_limpa']:>12.4f}"
            + f"{candidato['melhor_coberta']:>16.4f}"
            + folga.rjust(10) + folga_d.rjust(16) + "  " + veredito
        )

    if sonda < 0:
        print("")
        print(
            "NENHUMA BANDA SEPARA O GABARITO SOB DERIVA. Nao ha limiar a "
            "propor, e um limiar que so separa quando a linha esta no pixel "
            "exato da calibracao e pior que nenhum. PARANDO."
        )
        return 6

    dy0, dy1 = varredura.candidatos[sonda]
    inicio_da_banda, fim_da_banda = varredura.janela_derivada
    escolhida = next(c for c in tabela if c["coluna"] == sonda)
    print("")
    print(
        f"BANDA ESCOLHIDA: x em [{inicio_da_banda}, {fim_da_banda}) e dy em "
        f"[{dy0}, {dy1}) relativo ao canto superior esquerdo da linha, folga "
        f"{FOLGA_NAS_PONTAS}"
    )
    print(
        f"  (a que separa o gabarito com a maior folga SOB DERIVA de "
        f"+-{DERIVA_CONFERIDA} px: {escolhida['folga_derivada']:.1f}x, contra "
        f"{escolhida['folga']:.1f}x na origem calibrada)"
    )

    passou, diag_nome = conferir_o_gabarito_limpo(varredura, (dy0, dy1))
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
        f"tinta mais funda do CENSO INTEIRO x={diag_nome['ponta_do_censo']}"
    )
    print("")
    print("  A FOLGA VERTICAL - a banda esta em cima do texto?")
    print(
        f"    tinta das linhas LIMPAS, dentro da janela de busca: "
        f"dy[{diag_nome['tinta_topo']}, {diag_nome['tinta_base']}] "
        f"({diag_nome['n_linhas_com_tinta']} linhas medidas)"
    )
    print(f"    banda escolhida: dy[{dy0}, {dy1})")
    if "folga_do_texto" in diag_nome:
        print(
            f"    folga ate o texto {diag_nome['folga_do_texto']} px, folga ate "
            f"a moldura da linha anterior {diag_nome['folga_da_moldura']} px, "
            f"minimo exigido {diag_nome['folga_vertical_minima']} px"
        )
    if not passou:
        print("")
        print("O GABARITO LIMPO NAO SERVE PARA ESCOLHER SONDA. PARANDO.")
        print("  " + str(diag_nome.get("motivo", "")))
        return 8
    print(
        "  PASSOU: o gabarito declara o pior nome conhecido, a declaracao "
        "confere com os pixels, e a banda esta fora da faixa de tinta."
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
    for nome in GRAVACOES_DA_VARREDURA:
        recusa, total = custo.get(nome, (0, 0))
        fatia = 100.0 * recusa / total if total else 0.0
        print(f"  {nome[9:]:<34} {recusa:>5} de {total:>5}  ({fatia:>5.1f}%)")
    fatia_total = 100.0 * recusadas / max(medidas, 1)
    print(
        "  " + "TOTAL".ljust(34) + f" {recusadas:>5} de {medidas:>5}  "
        f"({fatia_total:>5.1f}%)"
    )

    print("")
    print("A SENSIBILIDADE DO CORTE - o limiar pousa num vale ou numa ladeira?")
    print(
        "  " + "fator".ljust(8) + "limiar".rjust(12) + "recusadas".rjust(12)
        + "  de " + "  (fatia)"
    )
    for fator, valor, recusa, total in sensibilidade_do_corte(
        varredura, sonda, limiar
    ):
        marca = "->" if fator == 1.0 else "  "
        fatia = 100.0 * recusa / max(total, 1)
        print(
            marca + f"{fator:>6.2f}x".ljust(8) + f"{valor:>12.6f}"
            + f"{recusa:>12}" + f"  de {total:>5}" + f"  ({fatia:>5.1f}%)"
        )
    print(
        "  Se a coluna `recusadas` quase nao muda entre 0,25x e 4x, o limiar "
        "esta num vale vazio e a escolha exata dele nao decide nada. Se ela "
        "muda muito, ha massa de linhas de campo encostada no corte."
    )

    por_frame = distribuicao_de_linhas_sobreviventes(varredura, sonda, limiar)
    intersecoes = intersecao_entre_frames_vizinhos(varredura, sonda, limiar)

    print("")
    print("LINHAS SOBREVIVENTES POR FRAME ISOLADO (so para conferencia):")
    for nome in GRAVACOES_DA_VARREDURA:
        print(
            _linha_de_distribuicao(
                nome[9:], [float(v) for v in por_frame.get(nome, [])]
            )
        )

    print("")
    print("INTERSECAO ENTRE FRAMES VIZINHOS (a grandeza que o 02-05 julga):")
    for nome in GRAVACOES_DA_VARREDURA:
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

    sonda_gravada = {
        "dx0": int(inicio_da_banda),
        "dx1": int(fim_da_banda),
        "dy0": int(dy0),
        "dy1": int(dy1),
        "folga": FOLGA_NAS_PONTAS,
    }
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
