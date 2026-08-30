"""A varredura que MEDE o piso de brilho PROPRIO da coluna Quantity.

Ela varre as 8 gravacoes NOMEADAS do censo com o PORTAO DE LAYOUT LIGADO,
recorta as tres colunas calibradas linha a linha, deriva o rotulo de cada linha
a partir de `Total` e `Unit price` — duas colunas que a coluna Quantity nao
toca — e classifica a leitura da Quantity em TODO nivel de brilho de uma faixa
declarada, com passo 1.

    mercado_limiar_de_brilho_da_quantidade   o piso PROPRIO da coluna Quantity

O DEFEITO QUE ELA EXISTE PARA MEDIR
------------------------------------
O 02-04 mediu, em `pagina-cheia/frame_000010`: o tronco do `1` da coluna
Quantity e desenhado a V = 177, ABAIXO do piso 180 de
`identidade.mascara_de_texto`, enquanto o MESMO `1` da coluna Total tem V = 205.
A mascara fica so com a serifa e a base, o casamento devolve 0,2988 (o proprio
molde `1` vale −0,1810) e o piso de leitura 0,4698 reprova. A falha e FECHADA —
nada errado e gravado — mas o custo e alto: nas gravacoes de tooltip e de alvo
sobreposto ZERO linhas atravessam por causa disso, porque toda quantidade ali e
`1`, e `1` e o caso comum do mercado.

O ROTULO E NAO CIRCULAR, E SEM ISSO NAO HA MEDICAO
----------------------------------------------------
`quantidade_derivada(total, unitario)` recebe DOIS inteiros e mais nada: sem
recorte, sem moldes, sem piso. Ela nao ve um unico pixel da coluna que esta
sendo medida. Rotular pelo que a propria coluna le seria medir a leitura contra
ela mesma, e foi assim que o 02-02 REFUTOU o rotulo por pasta de origem.

Ela reaproveita `limite_derivado_do_cruzamento` e `residuo_do_cruzamento`, que
moram em `l2scanner.mercado_leitura` desde o 02-06 — a seta aponta sempre
ferramenta -> puro, e reescrever a aritmetica faria a ferramenta MEDIR com uma
convencao e a producao DECIDIR com outra.

ELA E ROTULO DE MEDICAO, E NUNCA GUARDA DE PRODUCAO. A guarda de cruzamento
REPROVOU no 02-02 (tolerancia de 1273 centesimos por unidade contra o maximo
1,0) e continua DESLIGADA. A diferenca de criterio e o ponto: um ROTULO precisa
de precisao alta e pode ter recall baixo — a linha que nao fecha simplesmente
nao entra na medicao —, enquanto uma GUARDA precisa das duas coisas, porque toda
linha que ela nao fecha e uma linha descartada. Sao criterios diferentes sobre a
mesma aritmetica, e confundi-los seria ressuscitar por acidente um mecanismo que
o usuario ja viu reprovar.

O PISO TEM CHAO E TEM TETO, E O TETO E O QUE DIMENSIONA O RISCO
----------------------------------------------------------------
Baixar o piso demais nao volta a falhar FECHADO: passa a falhar ABERTO. Sondado
pelo planejador em `scroll-transicao/frame_000016`, com o piso em 150 o `30` da
quantidade vira `38` com score 0,724 e margem 0,127 — os dois ACIMA do piso de
leitura 0,4698 e da margem 0,0370. Ele atravessa as duas peneiras e vira numero
errado no CSV, na coluna que diz quantas unidades o preco cobre.

Por isso a proposta e pelo VAO entre a pior leitura CERTA e a melhor leitura
ERRADA contra o rotulo derivado, e nao por "o mais baixo que ainda le". Um piso
que produza UMA leitura divergente e pior que o defeito de hoje, porque troca
falha FECHADA por numero errado plausivel (LEIT-02).

O PISO E PROPRIO DA COLUNA, E NAO EXISTE PISO GLOBAL
------------------------------------------------------
A coluna Total carrega a palavra de sufixo (`XM Coin`, `Adena`) DENTRO do
proprio recorte, e a palavra vive entre V = 120 e V = 173 — e por isso
`mercado_leitura.VALOR_MINIMO_DO_SUFIXO = 120` existe. O piso 180 das colunas de
moeda e o que mantem o sufixo FORA da celula; baixa-lo arrasta a palavra para
dentro (sondado: `18,90` vira `18,907` ja no piso 170). As duas colunas pedem
faixas DISJUNTAS. O RELATORIO 3 quantifica esse custo no censo inteiro.

O PORTAO DE LAYOUT ESTA LIGADO, DIFERENTEMENTE DO 02-02
---------------------------------------------------------
Aquela varredura mediu necessariamente sobre TODOS os layouts, porque o portao
so nasceu no 02-04. Medir a coluna Quantity sobre a aba Adena seria medir uma
coluna que nem existe la (`5 mln increment`), e o rotulo derivado nao vale por
construcao naquela aba.

DUAS PRIMITIVAS NASCEM AQUI E SAO PROMOVIDAS NA TASK 2
--------------------------------------------------------
`mascara_de_numero` e `segmentar_glifos_no_brilho` sao a mecanica de
`identidade.mascara_de_texto` e de `mercado_leitura.segmentar_glifos` com o piso
vindo de FORA em vez de constante de modulo. Elas nascem aqui porque e aqui que
o piso variavel e necessario primeiro, e sao MOVIDAS para
`l2scanner.mercado_leitura` na Task 2 deste mesmo plano — o mesmo caminho de
`segmentar_glifos`, `pontuar_glifos`, `centesimos_de_moeda` e
`limite_derivado_do_cruzamento`, todas nascidas em ferramenta e promovidas
quando a producao passou a precisar delas. Depois da promocao este modulo as
IMPORTA; nunca ha duas copias.

Uso (no checkout PRINCIPAL — `recordings/` e `calibration.json` sao gitignored):

    .venv/Scripts/python.exe tools/medir_brilho_da_quantidade.py
        --gravacoes C:/.../recordings --calibracao C:/.../calibration.json
        [--gravar]
"""

from __future__ import annotations

import argparse
import importlib.util
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
from l2scanner.identidade import VALOR_MINIMO_DO_TEXTO  # noqa: E402

# A ARITMETICA E A CLASSIFICACAO SAO IMPORTADAS, E NUNCA REESCRITAS. A seta
# aponta ferramenta -> puro, e uma copia local faria esta varredura medir com
# uma convencao e o scanner decidir com outra no dia em que uma das duas fosse
# corrigida.
from l2scanner.mercado_leitura import (  # noqa: E402
    LIMITE_DERIVADO_POR_UNIDADE,  # noqa: F401 - conferido por teste de fonte
    centesimos_de_moeda,
    inteiro_de_quantidade,
    layout_confere,
    limite_derivado_do_cruzamento,
    ler_glifos,
    numero_valido,
    pontuar_glifos,
    residuo_do_cruzamento,
)
from l2scanner.mercado_visao import (  # noqa: E402
    RastreioDoPainel,
    ancoras_de_calibracao,
    cabecalho_de_calibracao,
    glifos_de_calibracao,
)


def _carregar_o_censo():
    """A lista das 8 gravacoes vive numa ferramenta so, e e importada daqui.

    Duplicar a lista seria a porta pela qual as varreduras passariam a medir
    conjuntos diferentes sem ninguem notar — e um limiar medido sobre um
    conjunto nao se compara com um medido sobre outro.
    """
    caminho = RAIZ / "tools" / "medir_oclusao.py"
    spec = importlib.util.spec_from_file_location("medir_oclusao", caminho)
    modulo = importlib.util.module_from_spec(spec)
    # Registrar ANTES de executar: `@dataclass` resolve as anotacoes por
    # `sys.modules[cls.__module__]`, e sem isto ele encontra None.
    sys.modules["medir_oclusao"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


_oclusao = _carregar_o_censo()
GRAVACOES_DO_CENSO = _oclusao.GRAVACOES_DO_CENSO
MOTIVO_PARA_IGNORAR = _oclusao.MOTIVO_PARA_IGNORAR


# ---------------------------------------------------------------------------
# Os parametros da varredura — cada um com a sua razao MEDIDA
# ---------------------------------------------------------------------------

# O piso que TODA leitura de mercado usa hoje, importado de onde ele mora. As
# colunas de MOEDA continuam com ele depois desta onda; quem ganha piso proprio
# e so a Quantity.
PISO_COMPARTILHADO = VALOR_MINIMO_DO_TEXTO

# UM NIVEL DE V POR LINHA DA TABELA. Um passo maior faria o piso gravado ser
# INTERPOLACAO e nao medicao, e a leitura NAO e monotona no piso: sondado, o
# `30` da quantidade vale 0,882 / 1,000 / 0,756 / 0,724 nos pisos 180 / 170 /
# 160 / 150. O que nao e monotono nao se interpola.
PASSO_DA_VARREDURA = 1

# O fundo da faixa. Ele fica BEM ABAIXO do tronco medido do `1` (177) e abaixo
# do primeiro piso em que a sondagem viu leitura ERRADA (150), para que o
# relatorio mostre os DOIS lados do vao — sem o lado ruim na tabela, a
# afirmacao "existe um teto" seria promessa e nao medicao.
PISO_MAIS_BAIXO_DA_FAIXA = 145

# O tronco do `1` medido pelo 02-04 na sondagem. Ele e SEMENTE, e nao verdade:
# o RELATORIO 1 o remede no censo inteiro, e e o numero REMEDIDO que entra na
# folga (b). Onde a medicao em escala contradisser a sondagem, a medicao manda.
TRONCO_SONDADO_DO_UM = 177


def faixa_de_candidatos() -> np.ndarray:
    """Todo nivel de V de `PISO_COMPARTILHADO` ate o fundo da faixa, passo 1."""
    return np.arange(
        PISO_COMPARTILHADO,
        PISO_MAIS_BAIXO_DA_FAIXA - 1,
        -PASSO_DA_VARREDURA,
        dtype=int,
    )


# ---------------------------------------------------------------------------
# As duas primitivas que NASCEM AQUI e sao PROMOVIDAS na Task 2
# ---------------------------------------------------------------------------


def mascara_de_numero(bgr: np.ndarray, valor_minimo: int) -> np.ndarray:
    """A mascara de brilho de um recorte de numero, no piso RECEBIDO.

    Mesma mecanica de `identidade.mascara_de_texto` — so o canal V, sem filtro
    de saturacao — com o piso vindo de fora em vez de constante de modulo. Com
    `valor_minimo = PISO_COMPARTILHADO` ela e IGUAL a `mascara_de_texto` pixel a
    pixel, e e essa igualdade que prova que nada muda para quem nao pediu piso
    proprio.
    """
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return (hsv[:, :, 2] > int(valor_minimo)).astype(np.uint8)


def segmentar_glifos_no_brilho(
    recorte: np.ndarray, valor_minimo: int
) -> tuple[tuple[int, int] | None, list[tuple[int, int]]]:
    """`segmentar_glifos` com o piso de brilho por parametro.

    A convencao de FAIXA COMPARTILHADA fica intacta e nao e negociavel: uma so
    faixa de linhas para o retangulo inteiro, porque e a posicao vertical
    relativa que distingue a virgula (baixa) do digito (altura cheia). Qualquer
    coluna vazia separa, sem tolerancia de lacuna.
    """
    if recorte is None or getattr(recorte, "size", 0) == 0:
        return None, []
    mascara = mascara_de_numero(recorte, valor_minimo)
    if mascara.size == 0:
        return None, []
    linhas = np.flatnonzero(mascara.any(axis=1))
    if linhas.size == 0:
        return None, []
    faixa = (int(linhas[0]), int(linhas[-1]) + 1)

    runs: list[tuple[int, int]] = []
    inicio: int | None = None
    for coluna, tem_texto in enumerate(mascara.any(axis=0)):
        if tem_texto and inicio is None:
            inicio = coluna
        elif not tem_texto and inicio is not None:
            runs.append((inicio, coluna))
            inicio = None
    if inicio is not None:
        runs.append((inicio, int(mascara.shape[1])))
    return faixa, runs


def ler_celula_no_brilho(
    bgr: np.ndarray,
    moldes: dict,
    piso: float,
    margem: float,
    valor_minimo: int,
) -> str | None:
    """O texto de UMA celula no piso de brilho dado, ou `None`. Nunca levanta.

    A MASCARA E A SEGMENTACAO USAM O MESMO `valor_minimo`: segmentar num piso e
    pontuar em outro produziria runs apontando para colunas que a mascara nao
    tem.
    """
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return None
    try:
        faixa, runs = segmentar_glifos_no_brilho(bgr, valor_minimo)
        if faixa is None or not runs:
            return None
        mascara = (mascara_de_numero(bgr, valor_minimo) * 255).astype(np.uint8)
        return ler_glifos(mascara, faixa, runs, moldes, piso, margem)
    except Exception:  # noqa: BLE001 — a varredura nao para por um recorte ruim
        return None


def pior_score_e_margem(
    bgr: np.ndarray, moldes: dict, valor_minimo: int
) -> tuple[float, float] | None:
    """O pior par `(score, margem)` da celula, SEM piso — para a distribuicao.

    Sem piso de proposito: aplicar o corte aqui tornaria a medicao circular. E a
    mesma razao ja escrita em `mercado_leitura.pontuar_glifos`.
    """
    faixa, runs = segmentar_glifos_no_brilho(bgr, valor_minimo)
    if faixa is None or not runs:
        return None
    mascara = (mascara_de_numero(bgr, valor_minimo) * 255).astype(np.uint8)
    pontuados = pontuar_glifos(mascara, faixa, runs, moldes)
    if not pontuados:
        return None
    return (
        min(score for _r, score, _m in pontuados),
        min(margem for _r, _s, margem in pontuados),
    )


# ---------------------------------------------------------------------------
# O ROTULO — derivado de duas colunas que a Quantity nao toca
# ---------------------------------------------------------------------------


def quantidade_derivada(total: int | None, unitario: int | None) -> int | None:
    """A quantidade que `Total` e `Unit price` implicam. `None` na duvida.

    ESTE E O UNICO ROTULO NAO CIRCULAR DISPONIVEL. Ela recebe DOIS INTEIROS e
    mais nada: sem recorte, sem moldes, sem piso de brilho. Nao ha por onde um
    pixel da coluna Quantity entrar, e e essa a propriedade que a torna um
    gabarito em vez de um espelho.

    A tela exibe `unitario = round(total / quantidade, 2)`, entao a quantidade
    e `round(total / unitario)` — aceita SO quando o residuo cabe no limite
    DERIVADO do arredondamento a duas casas. A aritmetica vem de
    `l2scanner.mercado_leitura`, onde ela mora desde o 02-06; ela nao e
    reescrita aqui nem puxada pela ferramenta irma, o que inverteria a seta.

    ROTULO DE MEDICAO, E NUNCA GUARDA DE PRODUCAO. A guarda de cruzamento
    REPROVOU no 02-02 — tolerancia de 1273 centesimos por unidade contra o
    maximo 1,0 — e `mercado_tolerancia_do_cruzamento` segue gravada como `None`.
    A diferenca e de CRITERIO, e ela e o motivo de a mesma aritmetica servir
    aqui: um rotulo precisa de precisao alta e pode ter recall baixo, porque a
    linha que nao fecha simplesmente NAO ENTRA na medicao; uma guarda precisa
    das duas, porque toda linha que ela nao fecha e uma linha DESCARTADA.
    Confundi-los seria ressuscitar por acidente um mecanismo que ja reprovou.
    """
    if total is None or unitario is None:
        return None
    if int(unitario) <= 0 or int(total) <= 0:
        return None
    quantidade = int(round(int(total) / int(unitario)))
    if quantidade <= 0:
        return None
    residuo = residuo_do_cruzamento(total, unitario, quantidade)
    if residuo is None:
        return None
    if residuo > limite_derivado_do_cruzamento(quantidade) + 1e-9:
        return None
    return quantidade


# ---------------------------------------------------------------------------
# A VARREDURA
# ---------------------------------------------------------------------------


@dataclass
class ResultadoDaVarredura:
    celulas: list = field(default_factory=list)
    abertos_por_gravacao: dict = field(default_factory=dict)
    recusadas_por_layout: dict = field(default_factory=dict)
    picos_por_coluna: dict = field(default_factory=dict)
    troncos_do_um: list = field(default_factory=list)


def _recorte(janela, ox, topo, altura, coluna) -> np.ndarray | None:
    x = ox + int(coluna["dx"])
    largura = int(coluna["largura"])
    if topo < 0 or x < 0:
        return None
    if topo + altura > janela.shape[0] or x + largura > janela.shape[1]:
        return None
    return janela[topo : topo + altura, x : x + largura]


def _pico_de_v(bgr: np.ndarray) -> int | None:
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return None
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return int(hsv[:, :, 2].max())


def tronco_do_um(bgr: np.ndarray) -> int | None:
    """O brilho do TRACO VERTICAL de um `1`, medido na linha do MEIO do glifo.

    A linha do meio de um `1` contem SO o tronco: a serifa fica no topo e a base
    no rodape, e as duas sao mais claras — foi por isso que a mascara de 180
    deixou o `1` com serifa e base e sem tronco, no achado do 02-04.

    O glifo e localizado no piso MAIS BAIXO da faixa, para que a medida nao
    dependa do piso que esta sendo escolhido. `None` quando o recorte nao tem
    exatamente um glifo — dois runs nao sao um `1`.
    """
    faixa, runs = segmentar_glifos_no_brilho(bgr, PISO_MAIS_BAIXO_DA_FAIXA)
    if faixa is None or len(runs) != 1:
        return None
    topo, base = faixa
    if base - topo < 3:
        return None
    meio = (topo + base) // 2
    inicio, fim = runs[0]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return int(hsv[meio, inicio:fim, 2].max())


def varrer_uma_janela(
    janela: np.ndarray,
    origem: tuple[int, int],
    cal: Calibracao,
    moldes: dict,
    nome_da_gravacao: str,
    nome_do_arquivo: str,
) -> list:
    """As dez linhas de UMA pagina, em toda a faixa de candidatos.

    Devolve uma lista de dicts, um por linha da grade, com o ROTULO derivado
    (ou `None`), o texto lido da Quantity em CADA piso candidato, os textos das
    duas colunas de MOEDA em cada piso (para o RELATORIO 3), e o pior par
    `(score, margem)` da Quantity no piso compartilhado.
    """
    grade = cal.mercado_grade or {}
    n_linhas = int(grade["linhas_por_pagina"])
    altura = int(grade["altura_da_linha"])
    piso = float(cal.mercado_limiar_de_leitura_de_glifo)
    margem = float(cal.mercado_margem_de_leitura_de_glifo)
    ox, oy = origem
    gy = oy + int(grade["dy"])
    candidatos = faixa_de_candidatos()

    saida = []
    for indice in range(n_linhas):
        topo = gy + indice * altura
        recortes = {}
        for chave, atributo in (
            ("total", "mercado_coluna_do_total"),
            ("unitario", "mercado_coluna_do_unitario"),
            ("quantidade", "mercado_coluna_da_quantidade"),
        ):
            pedaco = _recorte(janela, ox, topo, altura, getattr(cal, atributo))
            if pedaco is None:
                break
            recortes[chave] = pedaco
        if len(recortes) != 3:
            continue

        total = _inteiro_de_moeda(
            ler_celula_no_brilho(
                recortes["total"], moldes, piso, margem, PISO_COMPARTILHADO
            )
        )
        unitario = _inteiro_de_moeda(
            ler_celula_no_brilho(
                recortes["unitario"], moldes, piso, margem, PISO_COMPARTILHADO
            )
        )
        rotulo = quantidade_derivada(total, unitario)

        lido = {}
        moeda = {}
        for valor_minimo in candidatos:
            valor_minimo = int(valor_minimo)
            lido[valor_minimo] = ler_celula_no_brilho(
                recortes["quantidade"], moldes, piso, margem, valor_minimo
            )
            moeda[valor_minimo] = (
                ler_celula_no_brilho(
                    recortes["total"], moldes, piso, margem, valor_minimo
                ),
                ler_celula_no_brilho(
                    recortes["unitario"], moldes, piso, margem, valor_minimo
                ),
            )

        saida.append(
            {
                "chave": (nome_da_gravacao, nome_do_arquivo, indice),
                "rotulo": rotulo,
                "total": total,
                "unitario": unitario,
                "lido": lido,
                "moeda": moeda,
                "picos": {
                    nome: _pico_de_v(pedaco)
                    for nome, pedaco in recortes.items()
                },
                "pior_par": pior_score_e_margem(
                    recortes["quantidade"], moldes, PISO_COMPARTILHADO
                ),
                "tronco": (
                    tronco_do_um(recortes["quantidade"]) if rotulo == 1 else None
                ),
            }
        )
    return saida


def _inteiro_de_moeda(texto: str | None) -> int | None:
    """A gramatica e depois a conversao — as duas dizem `None` na duvida."""
    if not numero_valido(texto):
        return None
    return centesimos_de_moeda(texto)


def _inteiro_de_quantidade_valido(texto: str | None) -> int | None:
    if not numero_valido(texto):
        return None
    return inteiro_de_quantidade(texto)


def varrer(gravacoes: Path, cal: Calibracao) -> ResultadoDaVarredura:
    """As 8 gravacoes do censo, com o PORTAO DE LAYOUT LIGADO."""
    ancoras = ancoras_de_calibracao(cal.mercado_ancoras)
    limiar = float(cal.mercado_limiar_da_ancora or 0.73)
    moldes = glifos_de_calibracao(cal.mercado_templates_de_digito)
    cabecalho = cal.mercado_cabecalho_de_coluna
    molde_do_cabecalho = cabecalho_de_calibracao(cabecalho)
    limiar_do_cabecalho = cal.mercado_limiar_do_cabecalho
    dx_da_grade = int((cal.mercado_grade or {})["dx"])

    resultado = ResultadoDaVarredura()
    picos = {"total": [], "unitario": [], "quantidade": []}
    picos_da_quantidade_por_gravacao: dict = {}

    for nome in GRAVACOES_DO_CENSO:
        rastreio = RastreioDoPainel(ancoras, limiar)
        abertos = 0
        recusadas = 0
        arquivos = sorted(
            p for p in (gravacoes / nome).glob("frame_*.png") if p.is_file()
        )
        for caminho in arquivos:
            frame = cv2.imread(str(caminho))
            if frame is None:
                continue
            voto = rastreio.observar(frame)
            if not voto.aberto or rastreio.origem is None:
                continue
            # O PORTAO DE LAYOUT ANTES DE FATIAR. Medir a coluna Quantity sobre
            # a aba Adena seria medir uma coluna que nem existe la, e o rotulo
            # derivado nao vale por construcao naquela aba.
            if not layout_confere(
                frame,
                rastreio.origem,
                dx_da_grade,
                cabecalho,
                molde_do_cabecalho,
                limiar_do_cabecalho,
            ):
                recusadas += 1
                continue
            abertos += 1
            for celula in varrer_uma_janela(
                frame, rastreio.origem, cal, moldes, nome, caminho.name
            ):
                resultado.celulas.append(celula)
                for coluna, pico in celula["picos"].items():
                    if pico is not None:
                        picos[coluna].append(pico)
                if celula["picos"].get("quantidade") is not None:
                    picos_da_quantidade_por_gravacao.setdefault(nome, []).append(
                        celula["picos"]["quantidade"]
                    )
                if celula["tronco"] is not None:
                    resultado.troncos_do_um.append(celula["tronco"])
        resultado.abertos_por_gravacao[nome] = abertos
        resultado.recusadas_por_layout[nome] = recusadas

    resultado.picos_por_coluna = picos
    resultado.picos_por_coluna["quantidade_por_gravacao"] = (
        picos_da_quantidade_por_gravacao
    )
    return resultado


# ---------------------------------------------------------------------------
# OS TRES BALDES, A REGIAO SEGURA, E A PROPOSTA
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Baldes:
    """A classificacao de UM piso candidato contra o rotulo derivado.

    LE CERTO      o texto lido, na gramatica, e igual ao rotulo
    NAO LE        a celula caiu pelo piso, pela margem ou pela gramatica —
                  falha FECHADA, que e o comportamento de hoje
    LE ERRADO     a celula produziu um inteiro DIFERENTE do rotulo

    O terceiro balde e o unico que importa para a decisao, e por isso ele guarda
    as celulas e nao so a contagem: um piso recusado tem de poder dizer QUAL
    linha ele erraria.
    """

    certo: int
    nao_le: int
    errado: tuple

    @property
    def erra(self) -> bool:
        return len(self.errado) > 0

    @property
    def total(self) -> int:
        return self.certo + self.nao_le + len(self.errado)


def classificar(celulas: list, valor_minimo: int) -> Baldes:
    """As celulas ROTULADAS, classificadas nos tres baldes neste piso."""
    certo = 0
    nao_le = 0
    errado = []
    for celula in celulas:
        rotulo = celula["rotulo"]
        if rotulo is None:
            continue
        lido = _inteiro_de_quantidade_valido(celula["lido"].get(valor_minimo))
        if lido is None:
            nao_le += 1
        elif lido == rotulo:
            certo += 1
        else:
            errado.append((celula["chave"], rotulo, lido))
    return Baldes(certo=certo, nao_le=nao_le, errado=tuple(errado))


def tabela_de_candidatos(celulas: list) -> dict:
    """`{piso: Baldes}` para TODO nivel de V da faixa, sem saltos."""
    return {
        int(piso): classificar(celulas, int(piso))
        for piso in faixa_de_candidatos()
    }


def regiao_segura(baldes_por_piso: dict) -> tuple:
    """O maior PREFIXO DESCENDENTE de pisos com o balde LE ERRADO vazio.

    Comeca no piso COMPARTILHADO e desce de um em um enquanto o balde LE ERRADO
    estiver vazio. O retorno e CONTIGUO POR CONSTRUCAO — e por isso o teste de
    descontinuidade NAO pode ser feito sobre ele (ver
    `ha_seguro_abaixo_do_primeiro_que_erra`).
    """
    prefixo = []
    piso = PISO_COMPARTILHADO
    while piso in baldes_por_piso and not baldes_por_piso[piso].erra:
        prefixo.append(piso)
        piso -= PASSO_DA_VARREDURA
    return tuple(prefixo)


def ha_seguro_abaixo_do_primeiro_que_erra(baldes_por_piso: dict) -> bool:
    """Existe piso seguro ABAIXO do primeiro que erra? Esta e a pergunta.

    O PREDICADO E SOBRE O CONJUNTO SEGURO INTEIRO, e nao sobre o retorno de
    `regiao_segura`. Escrito sobre o retorno, o `if` NUNCA dispararia — aquele
    prefixo e contiguo por construcao — e o caso viraria codigo morto que os
    testes aprovam.

    A razao de ele reprovar: a leitura NAO e monotona no piso. Sobre um conjunto
    descontinuo o pior seguro fica ABAIXO do melhor que erra, o vao se INVERTE,
    e qualquer escolha calculada dentro dele cai na zona de erro com aparencia
    de proposta legitima.
    """
    pisos = sorted(baldes_por_piso, reverse=True)
    primeiro_que_erra = next(
        (piso for piso in pisos if baldes_por_piso[piso].erra), None
    )
    if primeiro_que_erra is None:
        return False
    return any(
        piso < primeiro_que_erra and not baldes_por_piso[piso].erra
        for piso in pisos
    )


@dataclass(frozen=True)
class Proposta:
    veredito: str
    piso: int | None
    causa: str | None
    folga_ate_o_primeiro_que_erra: int | None
    folga_ate_o_tronco: int | None
    captura_o_um: bool | None
    baldes_do_piso: Baldes | None
    baldes_do_compartilhado: Baldes | None
    linha_do_veredito: str


def propor_o_piso(
    baldes_por_piso: dict,
    tronco_do_um: int | None = None,
    reclassificar=None,
) -> Proposta:
    """O ULTIMO PISO SEGURO, ou `None` com a causa da recusa. Em quatro passos.

    ZERO. O balde LE ERRADO do PISO COMPARTILHADO. Se ele nao esta vazio, o
    comportamento de HOJE ja erra naquela celula, a regiao segura sai vazia por
    uma causa que este plano nao esta medindo, e a mensagem diz isso com essas
    palavras — nao e o piso novo que falhou, e o numero que for para o
    `WINDOWS.md #16` nao pode ser atribuido a ele.

    PRIMEIRO. `regiao_segura` toma o maior prefixo descendente com o balde LE
    ERRADO vazio.

    SEGUNDO. A DESCONTINUIDADE, testada sobre o CONJUNTO seguro inteiro.

    TERCEIRO. O piso e o ULTIMO PISO DA REGIAO SEGURA, e NUNCA a media entre ele
    e o primeiro que erra. Com `PASSO_DA_VARREDURA = 1` os dois sao inteiros
    ADJACENTES e nao existe inteiro entre eles: uma media arredondando para
    baixo escolheria justamente o piso que ERRA, a reclassificacao o reprovaria,
    e a ferramenta devolveria REPROVADO por ARITMETICA em vez de por medicao.
    Arredondar sempre para o lado SEGURO — e com passo 1 o lado seguro E o
    ultimo seguro.

    QUARTO. O piso escolhido e RECLASSIFICADO nos tres baldes, e a proposta so
    sai se o balde LE ERRADO DELE estiver vazio. Um piso proposto sem a propria
    linha na tabela e interpolacao disfarcada de medicao. Com a `regiao_segura`
    de hoje esta conferencia e defesa em profundidade — ela dispara no dia em
    que as duas discordarem —, e o `reclassificar` opcional existe para que ela
    seja um caminho VIVO e nao um `if` que ninguem consegue executar.

    AS DUAS FOLGAS, as duas em niveis de V, e a segunda e a que informa:

    (a) ate o primeiro piso que ERRA — vale 1 por construcao com passo 1, e diz
        so quao no limite a escolha esta;
    (b) ate o TRONCO MEDIDO do `1` da Quantity — e ela que dimensiona a
        confianca, porque diz quanta margem o piso tem contra a variacao do
        proprio glifo que ele existe para capturar. A mascara e `V > piso`, entao
        capturar um tronco em `t` exige `piso < t`: folga (b) NULA OU NEGATIVA e
        um piso que NAO captura o `1`, e a ferramenta diz isso ALTO em vez de
        propor um numero que passa nos baldes e falha no proposito.
    """
    do_compartilhado = baldes_por_piso.get(PISO_COMPARTILHADO)

    def _reprovar(causa: str, linha: str) -> Proposta:
        return Proposta(
            veredito="REPROVADO",
            piso=None,
            causa=causa,
            folga_ate_o_primeiro_que_erra=None,
            folga_ate_o_tronco=None,
            captura_o_um=None,
            baldes_do_piso=None,
            baldes_do_compartilhado=do_compartilhado,
            linha_do_veredito=linha,
        )

    if do_compartilhado is not None and do_compartilhado.erra:
        exemplos = ", ".join(
            f"{chave[0][9:]}/{chave[1]} L{chave[2]} rotulo {rotulo} lido {lido}"
            for chave, rotulo, lido in do_compartilhado.errado[:3]
        )
        return _reprovar(
            "o piso compartilhado JA ERRA",
            "REPROVADO porque o PISO COMPARTILHADO "
            f"({PISO_COMPARTILHADO}) ja tem {len(do_compartilhado.errado)} "
            "leitura(s) divergente(s) do rotulo derivado: e o comportamento de "
            "HOJE que erra naquela celula, e NAO o piso novo que falhou. O "
            "numero que for para o WINDOWS.md #16 nao pode ser atribuido ao "
            f"piso novo. Exemplos: {exemplos}",
        )

    regiao = regiao_segura(baldes_por_piso)
    if not regiao:
        return _reprovar(
            "regiao segura vazia",
            "REPROVADO por REGIAO SEGURA VAZIA: nao ha piso a partir do "
            f"compartilhado ({PISO_COMPARTILHADO}) na tabela de candidatos. "
            "Sem populacao rotulada nao ha medicao — e uma razao contra zero "
            "nao e medicao.",
        )

    if ha_seguro_abaixo_do_primeiro_que_erra(baldes_por_piso):
        pisos = sorted(baldes_por_piso, reverse=True)
        primeiro_que_erra = next(
            piso for piso in pisos if baldes_por_piso[piso].erra
        )
        abaixo = [
            piso
            for piso in pisos
            if piso < primeiro_que_erra and not baldes_por_piso[piso].erra
        ]
        return _reprovar(
            "conjunto seguro DESCONTINUO",
            "REPROVADO por CONJUNTO SEGURO DESCONTINUO: o primeiro piso que "
            f"erra e {primeiro_que_erra}, e ainda ha piso(s) SEGURO(s) abaixo "
            f"dele ({abaixo[0]}..{abaixo[-1]}). Sobre um conjunto descontinuo o "
            "pior seguro fica ABAIXO do melhor que erra, o vao se INVERTE, e "
            "qualquer escolha calculada dentro dele cai na zona de erro com "
            "aparencia de proposta legitima.",
        )

    piso = regiao[-1]
    baldes_do_piso = (
        reclassificar(piso) if reclassificar is not None else baldes_por_piso[piso]
    )
    if baldes_do_piso.erra:
        return _reprovar(
            "a reclassificacao do piso escolhido REPROVOU",
            f"REPROVADO na RECLASSIFICACAO do piso {piso}: o balde LE ERRADO "
            f"DELE tem {len(baldes_do_piso.errado)} leitura(s). Nao basta que "
            "os vizinhos estejam limpos — um piso proposto e um piso MEDIDO, e "
            "a linha dele na tabela e a medicao.",
        )

    folga_ate_erro = 1 if PASSO_DA_VARREDURA == 1 else PASSO_DA_VARREDURA
    primeiro_que_erra = piso - PASSO_DA_VARREDURA
    if primeiro_que_erra in baldes_por_piso:
        folga_ate_erro = piso - primeiro_que_erra
    else:
        # A faixa acabou sem nenhum piso que erra: nao ha "primeiro que erra",
        # e dizer 1 seria inventar uma fronteira que a medicao nao encontrou.
        folga_ate_erro = None

    folga_ate_tronco = None
    captura = None
    if tronco_do_um is not None:
        folga_ate_tronco = int(tronco_do_um) - int(piso)
        captura = folga_ate_tronco > 0

    if captura is False:
        return Proposta(
            veredito="REPROVADO",
            piso=None,
            causa="o piso NAO CAPTURA o tronco do `1`",
            folga_ate_o_primeiro_que_erra=folga_ate_erro,
            folga_ate_o_tronco=folga_ate_tronco,
            captura_o_um=False,
            baldes_do_piso=baldes_do_piso,
            baldes_do_compartilhado=do_compartilhado,
            linha_do_veredito=(
                f"REPROVADO: o piso {piso} NAO CAPTURA o tronco medido do `1` "
                f"({tronco_do_um}). A mascara e `V > piso`, entao a folga ate o "
                f"tronco vale {folga_ate_tronco} e o proprio tronco fica FORA. "
                "Um piso que passa nos tres baldes e falha no proposito nao e "
                "uma proposta."
            ),
        )

    return Proposta(
        veredito="PROPOSTO",
        piso=piso,
        causa=None,
        folga_ate_o_primeiro_que_erra=folga_ate_erro,
        folga_ate_o_tronco=folga_ate_tronco,
        captura_o_um=captura,
        baldes_do_piso=baldes_do_piso,
        baldes_do_compartilhado=do_compartilhado,
        linha_do_veredito=(
            f"PROPOSTO piso={piso}, folga ate o primeiro que erra="
            f"{folga_ate_erro}, folga ate o tronco medido do `1`="
            f"{folga_ate_tronco} (tronco={tronco_do_um}), balde LE ERRADO do "
            f"proprio piso VAZIO sobre {baldes_do_piso.total} celulas rotuladas"
        ),
    )


# ---------------------------------------------------------------------------
# O CUSTO DE UM PISO GLOBAL na coluna de MOEDA
# ---------------------------------------------------------------------------


def custo_na_coluna_de_moeda(celulas: list, valor_minimo: int) -> dict:
    """Quantas celulas de MOEDA que LEEM hoje deixam de ler sob este piso.

    Ele responde a pergunta 1 do plano com numero: as duas colunas pedem faixas
    DISJUNTAS, porque a coluna de moeda carrega a palavra de sufixo DENTRO do
    proprio recorte e um piso mais baixo a arrasta para dentro da celula.

    Com o piso compartilhado o custo e ZERO por construcao — e essa e a
    conferencia de que a conta esta medindo o que diz medir.
    """
    deixaram = 0
    trocaram = 0
    exemplos = []
    for celula in celulas:
        for posicao, coluna in enumerate(("total", "unitario")):
            base = celula["moeda"].get(PISO_COMPARTILHADO)
            candidato = celula["moeda"].get(valor_minimo)
            if base is None or candidato is None:
                continue
            antes, depois = base[posicao], candidato[posicao]
            if antes is None:
                continue
            if depois is None:
                deixaram += 1
                if len(exemplos) < 6:
                    exemplos.append((celula["chave"], coluna, antes, None))
            elif depois != antes:
                trocaram += 1
                if len(exemplos) < 6:
                    exemplos.append((celula["chave"], coluna, antes, depois))
    return {
        "deixaram_de_ler": deixaram,
        "passaram_a_ler_outra_coisa": trocaram,
        "exemplos": exemplos,
    }


# ---------------------------------------------------------------------------
# A GRAVACAO — load-mutate-save, UMA chave
# ---------------------------------------------------------------------------


def gravar(caminho: Path, piso: int) -> None:
    """Load-mutate-save de UMA chave. Nunca montar uma `Calibracao` do zero.

    Montar do zero apagaria os 13 moldes de glifo e as 3 ancoras — o modo de
    falha REAL da janela quebrada #13, que custou uma recuperacao a mao ao
    usuario em 2026-08-30. Aqui o arquivo e lido como JSON cru, UMA chave e
    mutada, e o `os.replace` troca o arquivo inteiro de uma vez: uma escrita
    interrompida no meio nao deixa o `calibration.json` em pedacos.

    NO RAMO REPROVADO O QUE SE GRAVA E O PISO COMPARTILHADO, e isso e resultado
    e nao silencio. O piso compartilhado E o comportamento de hoje: ele falha
    FECHADA, e grava-lo como o piso da coluna e o que permite a producao nao
    carregar nenhum ramo de fallback nem nenhum numero de fabrica. O precedente
    e literal — o 02-02 gravou `mercado_tolerancia_do_cruzamento = None`, uma
    guarda DESLIGADA, com o numero que a derrubou ao lado.
    """
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados["mercado_limiar_de_brilho_da_quantidade"] = int(piso)
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
# Os relatorios
# ---------------------------------------------------------------------------


def _quantis(valores) -> str:
    if not valores:
        return "(populacao vazia)"
    a = np.asarray(valores, dtype=np.float64)
    return (
        f"n={a.size:>7}  min={a.min():>5.0f}  p5={np.percentile(a, 5):>5.0f}  "
        f"mediana={np.median(a):>5.0f}  p95={np.percentile(a, 95):>5.0f}  "
        f"max={a.max():>5.0f}"
    )


def main(argv=None) -> int:
    analisador = argparse.ArgumentParser(
        description=(
            "Mede o piso de brilho PROPRIO da coluna Quantity sobre as 8 "
            "gravacoes do censo, com o portao de layout ligado."
        )
    )
    analisador.add_argument("--gravacoes", default=str(RAIZ / "recordings"))
    analisador.add_argument("--calibracao", default=str(RAIZ / "calibration.json"))
    analisador.add_argument("--gravar", action="store_true")
    opcoes = analisador.parse_args(argv)

    gravacoes = Path(opcoes.gravacoes).resolve()
    calibracao = Path(opcoes.calibracao).resolve()

    print("=" * 78)
    print("MEDICAO DO PISO DE BRILHO DA COLUNA QUANTITY - 02-07 Task 1")
    print("=" * 78)
    print("gravacoes : " + str(gravacoes))
    print("calibracao: " + str(calibracao))

    if not gravacoes.is_dir():
        print("ERRO: " + str(gravacoes) + " nao e um diretorio.")
        return 2

    faltando = [
        nome for nome in GRAVACOES_DO_CENSO if not (gravacoes / nome).is_dir()
    ]
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

    presentes = sorted(p.name for p in gravacoes.iterdir() if p.is_dir())
    ignoradas = [n for n in presentes if n not in GRAVACOES_DO_CENSO]
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
        print(f"  - {nome:<42} {motivo}")

    cal = Calibracao.carregar(calibracao)
    for chave in (
        "mercado_coluna_do_total",
        "mercado_coluna_da_quantidade",
        "mercado_coluna_do_unitario",
        "mercado_cabecalho_de_coluna",
        "mercado_limiar_do_cabecalho",
        "mercado_limiar_de_leitura_de_glifo",
        "mercado_margem_de_leitura_de_glifo",
    ):
        if getattr(cal, chave) is None:
            print("")
            print(
                f"ERRO: {chave} esta ausente no calibration.json. As tres "
                "colunas dao o rotulo e a medicao; o cabecalho liga o portao de "
                "layout; o piso e a margem sao a leitura de producao. Rode "
                "calibrar-mercado.bat."
            )
            return 4

    candidatos = faixa_de_candidatos()
    print("")
    print(
        f"FAIXA DE CANDIDATOS: {candidatos[0]} ate {candidatos[-1]}, "
        f"PASSO_DA_VARREDURA = {PASSO_DA_VARREDURA} "
        f"({len(candidatos)} niveis de V, sem saltos)"
    )
    print("Varrendo... (portao de layout LIGADO, tres colunas calibradas)")
    resultado = varrer(gravacoes, cal)
    rotuladas = [c for c in resultado.celulas if c["rotulo"] is not None]
    print(f"  celulas de grade varridas : {len(resultado.celulas)}")
    print(f"  celulas ROTULADAS         : {len(rotuladas)}")
    for nome in GRAVACOES_DO_CENSO:
        print(
            f"  {nome[9:]:<36} "
            f"{resultado.abertos_por_gravacao.get(nome, 0):>4} paginas no "
            f"layout calibrado, "
            f"{resultado.recusadas_por_layout.get(nome, 0):>4} recusadas por "
            "layout"
        )
    if not rotuladas:
        print("")
        print(
            "ERRO: nenhuma celula rotulada. Sem rotulo derivado nao ha medicao "
            "possivel — e um rotulo tirado da propria coluna seria circular."
        )
        return 5

    # -----------------------------------------------------------------
    # RELATORIO 1 - o pico por coluna, e o tronco do `1` REMEDIDO
    # -----------------------------------------------------------------
    print("")
    print("=" * 78)
    print("RELATORIO 1 - O PICO DE V POR COLUNA, E O TRONCO DO `1`")
    print("=" * 78)
    for coluna in ("quantidade", "total", "unitario"):
        print(f"  {coluna:<12} " + _quantis(resultado.picos_por_coluna[coluna]))

    troncos = resultado.troncos_do_um
    tronco_medido = int(min(troncos)) if troncos else None
    print("")
    if troncos:
        print("  O TRONCO DO `1` (linha do MEIO do glifo, so o traco vertical):")
        print("  " + _quantis(troncos))
        print(
            f"  -> o tronco MAIS ESCURO medido no censo e {tronco_medido}; a "
            f"sondagem do planejamento dizia {TRONCO_SONDADO_DO_UM}."
        )
    else:
        print(
            "  ATENCAO: nenhum tronco de `1` medido — nao ha celula rotulada "
            "com quantidade 1 e um glifo so. A folga (b) fica INDISPONIVEL, e "
            "ela e a que informa."
        )

    print("")
    print("  A DISPERSAO DO PICO DA QUANTITY, POR GRAVACAO:")
    por_gravacao = resultado.picos_por_coluna["quantidade_por_gravacao"]
    medianas = []
    for nome in GRAVACOES_DO_CENSO:
        valores = por_gravacao.get(nome, [])
        if not valores:
            print(f"    {nome[9:]:<36} (nenhuma celula)")
            continue
        mediana = float(np.median(valores))
        medianas.append(mediana)
        print(
            f"    {nome[9:]:<36} n={len(valores):>6} mediana={mediana:>6.1f} "
            f"min={min(valores):>4} max={max(valores):>4}"
        )
    dispersao = (max(medianas) - min(medianas)) if len(medianas) > 1 else 0.0
    print(
        f"  -> dispersao da MEDIANA do pico entre gravacoes: {dispersao:.1f} "
        "niveis de V"
    )

    # -----------------------------------------------------------------
    # RELATORIO 2 - TODOS os pisos candidatos, com os tres baldes
    # -----------------------------------------------------------------
    tabela = tabela_de_candidatos(resultado.celulas)
    proposta = propor_o_piso(tabela, tronco_do_um=tronco_medido)

    print("")
    print("=" * 78)
    print("RELATORIO 2 - TODOS OS PISOS CANDIDATOS, COM OS TRES BALDES")
    print("=" * 78)
    print(f"  PASSO_DA_VARREDURA = {PASSO_DA_VARREDURA} (uma linha por nivel de V)")
    print(f"  celulas ROTULADAS  = {len(rotuladas)}")
    print("")
    print("   piso  LE CERTO    NAO LE  LE ERRADO   veredito")
    for piso in sorted(tabela, reverse=True):
        baldes = tabela[piso]
        marca = " <== ESCOLHIDO" if piso == proposta.piso else ""
        if piso == PISO_COMPARTILHADO:
            marca += " (PISO COMPARTILHADO, o comportamento de HOJE)"
        estado = "ERRA" if baldes.erra else "seguro"
        print(
            f"  {piso:>5}  {baldes.certo:>8}  {baldes.nao_le:>8}  "
            f"{len(baldes.errado):>9}   {estado}{marca}"
        )

    do_compartilhado = tabela[PISO_COMPARTILHADO]
    print("")
    print("  O BALDE DO PISO COMPARTILHADO, EM SEPARADO:")
    print(
        f"    LE CERTO {do_compartilhado.certo}, NAO LE {do_compartilhado.nao_le}, "
        f"LE ERRADO {len(do_compartilhado.errado)}"
    )
    if do_compartilhado.erra:
        print(
            "    -> o comportamento de HOJE ja erra nestas celulas; a causa NAO "
            "e o piso novo."
        )
        for chave, rotulo, lido in do_compartilhado.errado[:10]:
            print(
                f"       {chave[0][9:]}/{chave[1]} L{chave[2]}: rotulo "
                f"{rotulo}, lido {lido}"
            )

    print("")
    print("  AS DUAS FOLGAS:")
    print(
        f"    (a) ate o primeiro piso que ERRA : "
        f"{proposta.folga_ate_o_primeiro_que_erra}"
    )
    print(
        f"    (b) ate o TRONCO MEDIDO do `1`   : "
        f"{proposta.folga_ate_o_tronco}  (tronco={tronco_medido})"
    )
    print(
        "    a (b) e a que informa: ela diz quanta margem o piso tem contra a "
        "variacao do proprio glifo que ele existe para capturar."
    )
    if (
        proposta.piso is not None
        and proposta.folga_ate_o_tronco is not None
        and dispersao > proposta.folga_ate_o_tronco
    ):
        print("")
        print(
            f"  ATENCAO ALTA: a dispersao do pico da Quantity ({dispersao:.1f}) "
            f"e MAIOR que a folga do piso proposto "
            f"({proposta.folga_ate_o_tronco}). A resposta da pergunta 2 mudou: "
            "um piso FIXO por coluna deixou de servir, e o plano tem de voltar "
            "a mesa antes da Task 2."
        )

    # -----------------------------------------------------------------
    # RELATORIO 3 - o custo de um piso GLOBAL na coluna de moeda
    # -----------------------------------------------------------------
    piso_a_cobrar = proposta.piso if proposta.piso is not None else None
    print("")
    print("=" * 78)
    print("RELATORIO 3 - O CUSTO DE UM PISO GLOBAL NA COLUNA DE MOEDA")
    print("=" * 78)
    de_controle = custo_na_coluna_de_moeda(
        resultado.celulas, PISO_COMPARTILHADO
    )
    print(
        f"  no piso compartilhado ({PISO_COMPARTILHADO}): "
        f"{de_controle['deixaram_de_ler']} deixaram de ler, "
        f"{de_controle['passaram_a_ler_outra_coisa']} passaram a ler outra "
        "coisa  (ZERO por construcao — a conferencia da conta)"
    )
    for piso_de_amostra in (
        [piso_a_cobrar] if piso_a_cobrar is not None else []
    ) + [175, 170, 165, 160, 155, 150]:
        if piso_de_amostra is None or piso_de_amostra not in tabela:
            continue
        custo = custo_na_coluna_de_moeda(resultado.celulas, piso_de_amostra)
        marca = " <== o piso proposto" if piso_de_amostra == piso_a_cobrar else ""
        print(
            f"  no piso {piso_de_amostra:>3}: "
            f"{custo['deixaram_de_ler']:>6} deixaram de ler, "
            f"{custo['passaram_a_ler_outra_coisa']:>6} passaram a ler outra "
            f"coisa{marca}"
        )
        for chave, coluna, antes, depois in custo["exemplos"][:3]:
            print(
                f"      {chave[0][9:]}/{chave[1]} L{chave[2]} {coluna}: "
                f"{antes} -> {depois}"
            )

    print("")
    print("  O RENDIMENTO DA COLUNA QUANTITY, POR GRAVACAO (antes -> depois):")
    for nome in GRAVACOES_DO_CENSO:
        da_gravacao = [c for c in rotuladas if c["chave"][0] == nome]
        if not da_gravacao:
            print(f"    {nome[9:]:<36} (nenhuma celula rotulada)")
            continue
        antes = sum(
            1
            for c in da_gravacao
            if _inteiro_de_quantidade_valido(c["lido"][PISO_COMPARTILHADO])
            == c["rotulo"]
        )
        depois = (
            sum(
                1
                for c in da_gravacao
                if _inteiro_de_quantidade_valido(c["lido"][piso_a_cobrar])
                == c["rotulo"]
            )
            if piso_a_cobrar is not None
            else antes
        )
        print(
            f"    {nome[9:]:<36} {antes:>6} -> {depois:>6}  de "
            f"{len(da_gravacao):>6} rotuladas"
        )

    print("")
    print("  A TAXA DE LEITURA POR DIGITO DO ROTULO (antes -> depois):")
    for rotulo in sorted({c["rotulo"] for c in rotuladas}):
        do_rotulo = [c for c in rotuladas if c["rotulo"] == rotulo]
        antes = sum(
            1
            for c in do_rotulo
            if _inteiro_de_quantidade_valido(c["lido"][PISO_COMPARTILHADO])
            == rotulo
        )
        depois = (
            sum(
                1
                for c in do_rotulo
                if _inteiro_de_quantidade_valido(c["lido"][piso_a_cobrar])
                == rotulo
            )
            if piso_a_cobrar is not None
            else antes
        )
        print(
            f"    rotulo {rotulo:<8} n={len(do_rotulo):>6}  {antes:>6} -> "
            f"{depois:>6}"
        )

    # -----------------------------------------------------------------
    # O VEREDITO
    # -----------------------------------------------------------------
    a_gravar = proposta.piso if proposta.piso is not None else PISO_COMPARTILHADO
    print("")
    print("O QUE VAI PARA O calibration.json:")
    print(f"  mercado_limiar_de_brilho_da_quantidade = {a_gravar}")
    if proposta.piso is None:
        print(
            "  (o piso COMPARTILHADO, porque a proposta REPROVOU. Ele E o "
            "comportamento de hoje, que falha FECHADA, e grava-lo como o piso "
            "da coluna e o que permite a producao nao carregar ramo de fallback "
            "nem numero de fabrica.)"
        )

    if opcoes.gravar:
        gravar(calibracao, int(a_gravar))
        print("")
        print("GRAVADO em " + str(calibracao) + " (load-mutate-save).")
    else:
        print("")
        print("(nada gravado - rode de novo com --gravar para persistir)")

    print("")
    print(proposta.linha_do_veredito)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
