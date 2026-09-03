"""A varredura que MEDE o piso e a margem de LEITURA, e julga a guarda.

Ela varre as 8 gravacoes NOMEADAS do censo, recorta as tres colunas CALIBRADAS
linha a linha, segmenta com `segmentar_glifos` e classifica cada run contra os
13 moldes com `_alinhar_por_preenchimento` + `casamento_da_ancora` - exatamente
a mecanica de `propor_rotulo`, sem reescrever nenhuma. Reaproveitar a mecanica e
o que faz o numero significar a mesma coisa dos dois lados; medir de um jeito e
decidir com outro seria comparar convencoes.

    mercado_limiar_de_leitura_de_glifo   o piso de LEITURA
    mercado_margem_de_leitura_de_glifo   a margem sobre o segundo colocado
    mercado_tolerancia_do_cruzamento     centesimos por unidade, ou None

O PISO DE LEITURA NAO E `mercado_limiar_de_glifo`, E ISSO E MEDICAO
--------------------------------------------------------------------
`mercado_limiar_de_glifo = 0.8555` e o limiar de COLISAO: ele sai de
`(1.0 + pior_par)/2` sobre molde-contra-molde (`calibrar_mercado.py:284-291`) e
certifica que o CONJUNTO de moldes e separavel. Ele nunca foi medido sobre glifo
REAL de tela. A pesquisa mediu 2.057 glifos de campo:

    score:  min=0,0818  p1=0,1918  p5=0,7242  mediana=1,0000
    margem: min=0,0370  p1=0,0607  p5=0,0607  mediana=0,3451
    abaixo de 0,8555: 370 de 2.057 = 18,0%
    o `8` tem MEDIANA 0,7242 contra o proprio molde

Um piso em 0,8555 rejeitaria praticamente todo `8` da tela - `135,88` cairia. E
`0,12` de margem, herdado de `identidade.py`, e maior que a margem minima medida
do par `0`x`8` (0,0370), que e o par mais estreito do sistema inteiro. Os dois
numeros vao para chaves PROPRIAS: aliasar faria o afrouxamento de um viajar para
o outro, que e a razao ja escrita em `calibrar_mercado.py:344-350`.

A GUARDA DE CRUZAMENTO E DECIDIVEL, E OS DOIS CRITERIOS SAO OBRIGATORIOS
-------------------------------------------------------------------------
O unitario exibido e `Total / Quantity` TRUNCADO a duas casas (medido em campo
em 2026-09-02: quatro linhas discriminantes, as quatro truncando), entao o
residuo `|total - unitario x quantidade|` e limitado por UM centesimo por
unidade - em centesimos, a propria `quantidade`. Caso conhecido do spike:
`40,00` por 48 unidades exibindo `0,83` da residuo 16 contra limite 48.

    FECHAMENTO  >= 0,99, com a tolerancia proposta cabendo em 1x o limite
                derivado. O fator era 2x enquanto o truncamento era hipotese; ele
                caiu para 1x quando o truncamento virou a propria derivacao, para
                a mesma folga nao ser contada duas vezes. O TETO em centesimos
                por unidade e o mesmo dos dois lados: 0,5 x 2,0 = 1,0 x 1,0 = 1,0.
                Abaixo disso a guarda descartaria linha boa em volume,
                e descarte custa dado que o usuario viu na tela. Se a tolerancia
                precisa ser muito mais larga para fechar, a guarda virou peneira
                e aprovaria tambem a substituicao que existe para pegar.
    DETECCAO    >= 0,90 sobre trocas `0`<->`8` injetadas no Total. E o modo de
                falha que a gramatica do numero NAO pega, porque a substituicao
                mantem a gramatica intacta. Uma guarda avaliada so pela taxa de
                fechamento seria aprovada por uma tolerancia infinita.

Com qualquer criterio reprovado a ferramenta grava
`mercado_tolerancia_do_cruzamento = None` - guarda DESLIGADA - e imprime QUAL
caiu, com o numero. Falha fechada vale para a guarda tambem: uma guarda que nao
se provou nao pode descartar dado, porque ai ela e o defeito.

Uso (no checkout PRINCIPAL - `recordings/` e gitignored):

    .venv/Scripts/python.exe tools/medir_leitura_de_glifo.py
        --gravacoes C:/.../recordings --calibracao C:/.../calibration.json
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
from l2scanner.identidade import mascara_de_texto  # noqa: E402

# ESTAS FUNCOES NASCERAM AQUI E FORAM PROMOVIDAS NO 02-04. A producao passou a
# precisar delas, e uma ferramenta nao pode ser a fonte de verdade de um numero
# que decide preco no tick. Elas sao IMPORTADAS, e nao duplicadas: os testes
# desta ferramenta (`tests/test_medir_leitura_de_glifo.py`) continuam apontando
# para `ferramenta.centesimos_de_moeda` e viraram o detector de regressao da
# mudanca de casa.
from l2scanner.mercado_leitura import (  # noqa: E402
    LIMITE_DERIVADO_POR_UNIDADE,
    centesimos_de_moeda,
    inteiro_de_quantidade,
    limite_derivado_do_cruzamento,
    pontuar_glifos,
    residuo_do_cruzamento,
    segmentar_glifos,
)
from l2scanner.mercado_leitura import ler_celula as classificar_celula  # noqa: E402,F401

# O PORTAO DE LAYOUT E CHAMADO, E NUNCA REIMPLEMENTADO AQUI.
#
# A varredura precisa saber QUAL aba esta em cada frame para julgar a guarda so
# sobre a negociacao. A tentacao e escrever aqui um casamento de cabecalho de
# dez linhas - e uma copia do portao mediria outra coisa que a producao decide.
# No dia em que os limiares, o empate ou o conjunto de candidatos mudassem em
# `LeitorDePagina`, esta ferramenta continuaria aprovando ou reprovando a guarda
# com a regra ANTIGA, e o numero sairia com o nome certo e o significado errado.
#
# E E EXATAMENTE O DEFEITO QUE O DEBT-07 FECHOU: um teste que media a propria
# copia em vez do original. A seta aqui aponta producao -> ferramenta, o inverso
# da promocao do 02-06, e pela mesma razao: uma grandeza so pode ter uma casa.
from l2scanner.mercado_pagina import LeitorDePagina  # noqa: E402
from l2scanner.mercado_visao import (  # noqa: E402
    RastreioDoPainel,
    ancoras_de_calibracao,
    glifos_de_calibracao,
)


def _carregar_o_censo():
    """A lista das 8 gravacoes vive numa ferramenta so, e e importada daqui.

    Duplicar a lista seria a porta pela qual as duas varreduras passariam a
    medir conjuntos diferentes sem ninguem notar - e um limiar medido sobre um
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
# Os criterios da guarda - escritos aqui para serem CONFERIVEIS, nao julgados
# ---------------------------------------------------------------------------

# UM centesimo por unidade. NAO e escolha: e o limite DERIVADO do TRUNCAMENTO a
# duas casas. `unitario = trunc(total/quantidade, 2)` erra ate um centesimo
# inteiro por unidade, entao o residuo total erra ate `quantidade` centesimos.
# Ate 2026-09-02 este apelido valia meio centesimo, pela hipotese do
# arredondamento; a prova de campo daquele dia mostrou que a tela TRUNCA — quatro
# linhas discriminantes, as quatro truncando, sobre uma pagina cujas dez linhas
# foram declaradas por escrito ANTES da leitura.
#
# O NUMERO E A ARITMETICA MUDARAM DE CASA NO 02-06, e este nome e so um apelido
# local. `limite_derivado_do_cruzamento` e `residuo_do_cruzamento` nasceram aqui,
# para MEDIR a guarda, e viraram producao quando a guarda foi instalada. A seta
# aponta ferramenta -> puro, como nos outros nove precedentes desta fase: manter
# duas copias da mesma aritmetica deixaria a ferramenta e o scanner medindo
# coisas ligeiramente diferentes no dia em que uma delas fosse corrigida.
LIMITE_POR_UNIDADE = LIMITE_DERIVADO_POR_UNIDADE

# A tolerancia proposta tem de caber em 1x o limite derivado.
#
# ELE ERA 2,0 ATE 2026-09-02, E BAIXOU NO MESMO COMMIT EM QUE A CONSTANTE
# DOBROU. O 2x existia para deixar espaco EXATAMENTE para a possibilidade do
# truncamento, que naquele momento era suspeita sobre uma fixtura so. Com o
# truncamento virando a PROPRIA derivacao, manter o 2x empilharia a mesma folga
# duas vezes e afrouxaria a guarda como efeito colateral de um conserto — que e
# o modo de falha que este projeto existe para evitar.
#
# O TETO ABSOLUTO NAO SE MOVE, E E ELE QUE IMPORTA: o produto
# `LIMITE_POR_UNIDADE x FATOR_MAXIMO_SOBRE_O_LIMITE_DERIVADO` valia
# `0,5 x 2,0 = 1,0` centesimo por unidade antes e vale `1,0 x 1,0 = 1,0` depois.
# A linha de veredito continua dizendo `maximo 1.0`, e o 02-02 continua reprovado
# pelo MESMO numero contra o MESMO teto. `TestOTetoAbsolutoDaTolerancia` afirma o
# PRODUTO, e nao os fatores: afirmar so um deles deixaria a proxima mudanca de
# constante mover o teto em silencio.
#
# A ALTERNATIVA FOI RECUSADA POR ESCRITO: manter 2,0 levaria o teto a 2,0
# centesimos por unidade — o dobro do que qualquer pessoa decidiu — e uma guarda
# duas vezes mais frouxa teria nascido de um commit cujo assunto era corrigir uma
# derivacao. Um afrouxamento que ninguem escolheu e um afrouxamento que ninguem
# revisa.
FATOR_MAXIMO_SOBRE_O_LIMITE_DERIVADO = 1.0

# Fracao minima das linhas que leram nas tres colunas e cujo residuo cabe na
# tolerancia. Abaixo disso a guarda descarta linha boa em volume.
FECHAMENTO_MINIMO = 0.99

# Fracao minima das substituicoes `0`<->`8` injetadas que a guarda PEGA.
DETECCAO_MINIMA = 0.90

# Os digitos que a substituicao troca. `0` e `8` porque o par tem a menor margem
# do sistema (0,0370 medidos) e porque a troca mantem a gramatica do numero
# intacta - ela nao muda a contagem de digitos nem a posicao da virgula.
PAR_DA_SUBSTITUICAO = ("0", "8")


# ---------------------------------------------------------------------------
# A gramatica do numero
# ---------------------------------------------------------------------------


def texto_de_moeda(centesimos: int) -> str:
    """O inverso de `centesimos_de_moeda`, SEM separador de milhar.

    Sem separador de proposito: este texto so existe para a injecao de
    substituicao, e o separador nao e um digito - ele nao participa da troca
    `0`<->`8` e so atrapalharia os indices.
    """
    return f"{centesimos // 100},{centesimos % 100:02d}"


# ---------------------------------------------------------------------------
# A classificacao de uma celula - a mecanica de `propor_rotulo`, reaproveitada
# ---------------------------------------------------------------------------


def pontuar_celula(recorte: np.ndarray, moldes: dict) -> list | None:
    """Cada run da celula com `(rotulo, score, margem)`. `None` se nao da.

    Sem piso e sem margem: quem decide e quem chama. Esta funcao existe para
    PRODUZIR a distribuicao a partir da qual o piso vai ser medido, e aplicar um
    piso aqui tornaria a medicao circular.

    A mecanica mudou de casa no 02-04 (`mercado_leitura.pontuar_glifos`) e aqui
    ficou so a montagem da mascara. Continuar com uma copia local faria a
    ferramenta MEDIR com uma convencao e a producao DECIDIR com outra, que e
    exatamente o erro que a docstring de `segmentar_glifos` existe para impedir.
    """
    if recorte.size == 0:
        return None
    faixa, runs = segmentar_glifos(recorte)
    if faixa is None or not runs:
        return None
    mascara = (mascara_de_texto(recorte) * 255).astype(np.uint8)
    return pontuar_glifos(mascara, faixa, runs, moldes)


# ---------------------------------------------------------------------------
# O cruzamento `Total / Quantity` contra o unitario exibido
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LinhaMedida:
    gravacao: str
    arquivo: str
    linha: int
    total: int | None
    quantidade: int | None
    unitario: int | None

    @property
    def completa(self) -> bool:
        return (
            self.total is not None
            and self.quantidade is not None
            and self.unitario is not None
            and self.quantidade > 0
        )


def _tolerancia_que_cobre(por_unidade: list, cobertura: float) -> float:
    """O menor valor por unidade que cobre `cobertura` das linhas.

    Percentil interpolado NAO serve aqui: com poucas linhas ele cai ENTRE dois
    residuos observados e o fechamento medido logo em seguida sai abaixo do
    alvo, o que faria a ferramenta reprovar a propria proposta. O k-esimo menor
    e exato.
    """
    if not por_unidade:
        return 0.0
    ordenados = sorted(por_unidade)
    indice = int(np.ceil(cobertura * len(ordenados))) - 1
    indice = min(max(indice, 0), len(ordenados) - 1)
    return float(ordenados[indice])


def medir_o_cruzamento_do_unitario(linhas: list) -> dict:
    """A distribuicao do residuo, e a tolerancia que fecha `FECHAMENTO_MINIMO`."""
    completas = [linha for linha in linhas if linha.completa]
    if not completas:
        return {"n": 0, "tolerancia": None, "fechamento": 0.0}

    residuos = [
        residuo_do_cruzamento(linha.total, linha.unitario, linha.quantidade)
        for linha in completas
    ]
    por_unidade = [
        residuo / linha.quantidade
        for residuo, linha in zip(residuos, completas)
    ]
    tolerancia = _tolerancia_que_cobre(por_unidade, FECHAMENTO_MINIMO)
    dentro = sum(
        1
        for residuo, linha in zip(residuos, completas)
        if residuo <= tolerancia * linha.quantidade + 1e-9
    )
    dentro_do_derivado = sum(
        1
        for residuo, linha in zip(residuos, completas)
        if residuo <= limite_derivado_do_cruzamento(linha.quantidade) + 1e-9
    )
    arranjo = np.asarray(por_unidade, dtype=np.float64)
    return {
        "n": len(completas),
        "tolerancia": tolerancia,
        "fechamento": dentro / len(completas),
        "fechamento_no_limite_derivado": dentro_do_derivado / len(completas),
        "residuo_max": int(max(residuos)),
        "por_unidade_mediana": float(np.median(arranjo)),
        "por_unidade_p95": float(np.percentile(arranjo, 95)),
        "por_unidade_max": float(arranjo.max()),
    }


def poder_de_deteccao_do_cruzamento(linhas: list, tolerancia: float) -> dict:
    """Que fracao das trocas `0`<->`8` no Total a guarda PEGARIA.

    Cada troca e injetada uma de cada vez sobre o texto do total, e a linha
    resultante e submetida a mesma comparacao que a guarda faria. Uma troca e
    PEGA quando o residuo passa a estourar a tolerancia.

    Este e o unico dos dois criterios que mede o que a guarda PEGA. Sem ele uma
    tolerancia enorme teria fechamento 1,0 e seria aprovada sem pegar nada.
    """
    completas = [linha for linha in linhas if linha.completa]
    casos = 0
    pegos = 0
    for linha in completas:
        texto = texto_de_moeda(linha.total)
        for posicao, caractere in enumerate(texto):
            if caractere not in PAR_DA_SUBSTITUICAO:
                continue
            trocado = (
                PAR_DA_SUBSTITUICAO[1]
                if caractere == PAR_DA_SUBSTITUICAO[0]
                else PAR_DA_SUBSTITUICAO[0]
            )
            adulterado = centesimos_de_moeda(
                texto[:posicao] + trocado + texto[posicao + 1 :]
            )
            if adulterado is None or adulterado == linha.total:
                continue
            casos += 1
            residuo = residuo_do_cruzamento(
                adulterado, linha.unitario, linha.quantidade
            )
            if residuo > tolerancia * linha.quantidade + 1e-9:
                pegos += 1
    return {
        "casos": casos,
        "pegos": pegos,
        "deteccao": (pegos / casos) if casos else 0.0,
    }


def veredito_da_guarda(linhas: list) -> dict:
    """APROVADA so quando os DOIS criterios fecham. Senao, `None` e a razao.

    A linha `linha_do_veredito` tem FORMATO FIXO: a Task 4 do 02-04 le
    exatamente ela para saber se liga o mecanismo ou se registra a refutacao.
    """
    limite_aceitavel = LIMITE_POR_UNIDADE * FATOR_MAXIMO_SOBRE_O_LIMITE_DERIVADO
    medida = medir_o_cruzamento_do_unitario(linhas)
    veredito = {
        "n": medida["n"],
        "tolerancia": medida["tolerancia"],
        "fechamento": medida["fechamento"],
        "limite_aceitavel_por_unidade": limite_aceitavel,
        "deteccao": 0.0,
        "casos_injetados": 0,
        "aprovada": False,
        "criterio_que_caiu": None,
        "tolerancia_gravada": None,
        "medida": medida,
    }

    if medida["n"] == 0 or medida["tolerancia"] is None:
        veredito["criterio_que_caiu"] = "sem linha medida"
        veredito["linha_do_veredito"] = (
            "GUARDA REPROVADA por sem linha medida, 0 linhas com as tres "
            "colunas lidas"
        )
        return veredito

    poder = poder_de_deteccao_do_cruzamento(linhas, medida["tolerancia"])
    veredito["deteccao"] = poder["deteccao"]
    veredito["casos_injetados"] = poder["casos"]

    if medida["fechamento"] < FECHAMENTO_MINIMO:
        veredito["criterio_que_caiu"] = "fechamento"
        veredito["linha_do_veredito"] = (
            f"GUARDA REPROVADA por fechamento, {medida['fechamento']:.4f} "
            f"(minimo {FECHAMENTO_MINIMO})"
        )
        return veredito

    if medida["tolerancia"] > limite_aceitavel:
        veredito["criterio_que_caiu"] = "tolerancia"
        veredito["linha_do_veredito"] = (
            f"GUARDA REPROVADA por tolerancia, {medida['tolerancia']:.4f} "
            f"centesimos por unidade (maximo {limite_aceitavel})"
        )
        return veredito

    if poder["deteccao"] < DETECCAO_MINIMA:
        veredito["criterio_que_caiu"] = "deteccao"
        veredito["linha_do_veredito"] = (
            f"GUARDA REPROVADA por deteccao, {poder['deteccao']:.4f} "
            f"(minimo {DETECCAO_MINIMA}, sobre {poder['casos']} substituicoes "
            f"injetadas)"
        )
        return veredito

    veredito["aprovada"] = True
    veredito["tolerancia_gravada"] = float(medida["tolerancia"])
    veredito["linha_do_veredito"] = (
        f"GUARDA APROVADA, tolerancia={medida['tolerancia']:.4f} centesimos por "
        f"unidade, fechamento={medida['fechamento']:.4f}, "
        f"deteccao={poder['deteccao']:.4f}"
    )
    return veredito


# ---------------------------------------------------------------------------
# A varredura
# ---------------------------------------------------------------------------


@dataclass
class Amostra:
    """Um run classificado, com a origem para poder ser reconferido."""

    gravacao: str
    arquivo: str
    linha: int
    coluna: str
    rotulo: str
    score: float
    margem: float


@dataclass
class ResultadoDaVarredura:
    amostras: list = field(default_factory=list)
    linhas: list = field(default_factory=list)
    # (gravacao, arquivo, linha) -> {coluna: [(rotulo, score, margem), ...]}
    celulas: dict = field(default_factory=dict)
    abertos_por_gravacao: dict = field(default_factory=dict)
    runs_da_quantidade: list = field(default_factory=list)
    extremos_da_quantidade: dict = field(default_factory=dict)
    # (gravacao, arquivo) -> "negociacao" | "adena" | None, direto do portao de
    # PRODUCAO. `None` e resposta: nenhum layout passou o proprio limiar, ou
    # houve empate - e `LeitorDePagina` devolve `None` no empate de proposito.
    layout_por_frame: dict = field(default_factory=dict)
    # veredito do portao -> quantos frames com painel aberto. A chave `None`
    # entra na contagem: um relatorio que so contasse os frames classificados
    # esconderia justamente a calibracao torta que faz o portao nao opinar.
    abertos_por_layout: dict = field(default_factory=dict)


def varrer(gravacoes: Path, cal: Calibracao) -> ResultadoDaVarredura:
    """Todas as celulas das tres colunas calibradas, das 8 gravacoes."""
    grade = cal.mercado_grade or {}
    n_linhas = int(grade["linhas_por_pagina"])
    altura = int(grade["altura_da_linha"])
    ancoras = ancoras_de_calibracao(cal.mercado_ancoras)
    limiar = float(cal.mercado_limiar_da_ancora or 0.73)
    moldes = glifos_de_calibracao(cal.mercado_templates_de_digito)

    colunas = {
        "total": cal.mercado_coluna_do_total,
        "quantidade": cal.mercado_coluna_da_quantidade,
        "unitario": cal.mercado_coluna_do_unitario,
    }

    resultado = ResultadoDaVarredura()
    esquerda_min, direita_max = None, None

    for nome in GRAVACOES_DO_CENSO:
        rastreio = RastreioDoPainel(ancoras, limiar)
        # UM leitor de PRODUCAO por gravacao, com o rastreio DAQUELA gravacao.
        #
        # Catalogo vazio e as duas leitoras de texto em `None` porque a varredura
        # NUNCA chama OCR: aqui so se usa `_casamento_do_layout`, que olha a
        # banda do cabecalho e mais nada. Construi-lo por gravacao, e nao por
        # frame, e o que a producao faz - o molde do cabecalho e ~28 KB de hex
        # decodificados uma vez no arranque, e refaze-lo por frame seria
        # trabalho puro sobre 478 frames.
        leitor = LeitorDePagina(rastreio, {}, None, None, cal)
        abertos = 0
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
            abertos += 1
            ox, oy = rastreio.origem
            gy = oy + int(grade["dy"])

            # O PORTAO DE PRODUCAO, CHAMADO. Uma vez por frame com painel
            # aberto, com a mesma origem que a varredura ja usa para recortar.
            layout = leitor._casamento_do_layout(frame, rastreio.origem)
            resultado.layout_por_frame[(nome, caminho.name)] = layout
            resultado.abertos_por_layout[layout] = (
                resultado.abertos_por_layout.get(layout, 0) + 1
            )

            for indice in range(n_linhas):
                topo = gy + indice * altura
                leitura = {}
                for rotulo_da_coluna, coluna in colunas.items():
                    x = ox + int(coluna["dx"])
                    largura = int(coluna["largura"])
                    if (
                        topo < 0
                        or x < 0
                        or topo + altura > frame.shape[0]
                        or x + largura > frame.shape[1]
                    ):
                        continue
                    recorte = frame[topo : topo + altura, x : x + largura]
                    pontuados = pontuar_celula(recorte, moldes)
                    if not pontuados:
                        continue
                    leitura[rotulo_da_coluna] = pontuados
                    for r, score, margem in pontuados:
                        resultado.amostras.append(
                            Amostra(
                                nome,
                                caminho.name,
                                indice,
                                rotulo_da_coluna,
                                r,
                                score,
                                margem,
                            )
                        )
                    if rotulo_da_coluna == "quantidade":
                        _, runs = segmentar_glifos(recorte)
                        resultado.runs_da_quantidade.append(len(runs))
                        if runs:
                            a = min(inicio for inicio, _ in runs)
                            b = max(fim for _, fim in runs)
                            esquerda_min = a if esquerda_min is None else min(
                                esquerda_min, a
                            )
                            direita_max = b if direita_max is None else max(
                                direita_max, b
                            )
                if leitura:
                    resultado.celulas[(nome, caminho.name, indice)] = leitura
        resultado.abertos_por_gravacao[nome] = abertos

    resultado.extremos_da_quantidade = {
        "esquerda_min": esquerda_min,
        "direita_max": direita_max,
        "largura_da_coluna": int(colunas["quantidade"]["largura"]),
    }
    return resultado


def linhas_do_cruzamento(
    resultado: ResultadoDaVarredura,
    piso: float | None = None,
    margem: float | None = None,
) -> list:
    """As linhas em que as TRES colunas leram, na gramatica E NA NEGOCIACAO.

    Com `piso` e `margem`, a celula que tiver UM run reprovado derruba a linha
    inteira - o mesmo tudo-ou-nada de `classificar_celula`. Esse filtro importa
    para o VEREDITO: em producao a guarda so ve linha que ja passou pelo piso e
    pela margem, e julga-la sobre linha que a leitura teria descartado seria
    medir uma populacao que ela nunca vai encontrar. Sem os dois parametros a
    funcao devolve tudo, que e o que a etapa ANTERIOR precisa - o piso ainda nao
    existe quando as linhas confirmadas sao escolhidas.

    O PORTAO DE LAYOUT FILTRA AQUI, E SO AQUI. A identidade que esta populacao
    existe para julgar e `total = unitario x quantidade`, e ela NAO VALE na aba
    Adena por construcao: la a terceira coluna e `5 mln increment`, normalizada
    por cinco milhoes de adena e nao por unidade. Uma linha de Adena entrando na
    medicao nao e leitura errada - e outra aritmetica sendo julgada pela regua
    errada, e ela reprovava a guarda sem nada a ver com a qualidade da leitura.

    A ALTERNATIVA FOI RECUSADA POR ESCRITO: filtrar a VARREDURA inteira por
    layout, e nao so o cruzamento. Ela custaria caro e por nada. A producao le
    `Total Price` e `5 mln increment` da aba Adena com os MESMOS retangulos de
    negociacao - medido no 05-01, dez linhas exatas sem tocar um pixel de
    calibracao -, entao a populacao de GLIFO e a mesma nos dois layouts. Tirar os
    frames de Adena da varredura removeria do piso e da margem glifos que a
    producao REALMENTE le, e um piso medido sobre menos material que o de campo e
    um piso que vai recusar leitura boa no primeiro tick fora do censo.

    As duas populacoes ficam separadas de proposito: `resultado.amostras`
    (glifo, todos os layouts) e esta (cruzamento, so negociacao).
    """
    linhas = []
    for (gravacao, arquivo, indice), leitura in resultado.celulas.items():
        if not {"total", "quantidade", "unitario"} <= set(leitura):
            continue
        if resultado.layout_por_frame.get((gravacao, arquivo)) != "negociacao":
            continue
        if piso is not None and margem is not None:
            reprovada = any(
                score < piso or distancia < margem
                for pontuados in leitura.values()
                for _, score, distancia in pontuados
            )
            if reprovada:
                continue
        texto = {
            coluna: "".join(r for r, _, _ in pontuados)
            for coluna, pontuados in leitura.items()
        }
        linhas.append(
            LinhaMedida(
                gravacao,
                arquivo,
                indice,
                centesimos_de_moeda(texto["total"]),
                inteiro_de_quantidade(texto["quantidade"]),
                centesimos_de_moeda(texto["unitario"]),
            )
        )
    return linhas


def quebra_do_cruzamento_por_layout(
    resultado: ResultadoDaVarredura,
    piso: float | None = None,
    margem: float | None = None,
) -> dict:
    """Quantas linhas COMPLETAS cada layout tem, ANTES do descarte do portao.

    Ela existe para o relatorio poder dizer o TAMANHO DO EFEITO do portao, e nao
    so que ele existe: `{"negociacao": n, "adena": m, None: k}` responde de uma
    vez quantas linhas o portao tirou da populacao do cruzamento e de onde elas
    vinham. Sem esse numero, uma varredura em que o portao nao removeu NADA sairia
    identica a uma em que ele removeu metade - e essas duas dizem coisas opostas
    sobre a hipotese de contaminacao pela aba Adena.

    Os mesmos criterios de `linhas_do_cruzamento` (tres colunas, gramatica, piso e
    margem), MENOS o descarte por layout - que e justamente o que se quer medir.
    """
    quebra: dict = {}
    for (gravacao, arquivo, _indice), leitura in resultado.celulas.items():
        if not {"total", "quantidade", "unitario"} <= set(leitura):
            continue
        if piso is not None and margem is not None:
            reprovada = any(
                score < piso or distancia < margem
                for pontuados in leitura.values()
                for _, score, distancia in pontuados
            )
            if reprovada:
                continue
        texto = {
            coluna: "".join(r for r, _, _ in pontuados)
            for coluna, pontuados in leitura.items()
        }
        linha = LinhaMedida(
            gravacao,
            arquivo,
            _indice,
            centesimos_de_moeda(texto["total"]),
            inteiro_de_quantidade(texto["quantidade"]),
            centesimos_de_moeda(texto["unitario"]),
        )
        if not linha.completa:
            continue
        layout = resultado.layout_por_frame.get((gravacao, arquivo))
        quebra[layout] = quebra.get(layout, 0) + 1
    return quebra


def propor_piso_e_margem(
    resultado: ResultadoDaVarredura, confirmadas: set
) -> tuple:
    """O maior par (piso, margem) que ainda aceita todo glifo CONFIRMADO.

    "Confirmado" nao e um rotulo digitado a mao sobre 4.800 linhas: e a linha
    cujas TRES colunas leram, respeitam a gramatica do numero, e fecham o
    cruzamento `Total = unitario x quantidade` dentro do limite DERIVADO do
    TRUNCAMENTO. Tres leituras independentes que concordam aritmeticamente
    nao concordam por acaso - a chance de dois digitos errados se compensarem
    ate um centesimo por unidade e desprezivel.

    O par proposto e o MENOR score e a MENOR margem observados nessa populacao:
    qualquer par maior recusaria um glifo que o cruzamento confirmou correto, e
    recusar leitura boa custa dado que o usuario viu na tela.
    """
    acerto = [
        a
        for a in resultado.amostras
        if (a.gravacao, a.arquivo, a.linha) in confirmadas
    ]
    suspeita = [
        a
        for a in resultado.amostras
        if (a.gravacao, a.arquivo, a.linha) not in confirmadas
    ]
    diagnostico = {"n_acerto": len(acerto), "n_suspeita": len(suspeita)}
    if not acerto:
        diagnostico["motivo"] = "nenhuma linha confirmada pelo cruzamento"
        return None, None, diagnostico

    piso = min(a.score for a in acerto)
    margem = min(a.margem for a in acerto)
    diagnostico["piso"] = piso
    diagnostico["margem"] = margem
    if suspeita:
        recusados = sum(
            1 for a in suspeita if a.score < piso or a.margem < margem
        )
        diagnostico["suspeita_recusada"] = recusados / len(suspeita)
    return piso, margem, diagnostico


# ---------------------------------------------------------------------------
# Relatorio
# ---------------------------------------------------------------------------


def _quantis(valores) -> str:
    if not valores:
        return "(populacao vazia)"
    a = np.asarray(valores, dtype=np.float64)
    return (
        f"n={a.size:>6}  min={a.min():.4f}  p1={np.percentile(a, 1):.4f}  "
        f"p5={np.percentile(a, 5):.4f}  mediana={np.median(a):.4f}  "
        f"max={a.max():.4f}"
    )


def fragilidade_por_rotulo(amostras, piso, margem_minima) -> list:
    """A distribuicao QUEBRADA POR ROTULO, ordenada por TAXA DE RECUSA.

    PURA: recebe as `Amostra` que `varrer` ja produziu e devolve uma lista de
    dicionarios. Nao varre, nao le arquivo, nao imprime, e nao mexe na lista
    recebida.

    A CHAVE E A TAXA DE RECUSA, E AS QUATRO ALTERNATIVAS FORAM REJEITADAS
    ---------------------------------------------------------------------
    O relatorio agregado diz `score p1=0,1918` sobre 2.057 glifos e nao diz de
    QUEM e esse p1. Um agregado nunca aponta um culpado; ele so informa que
    existe um. A chave que quebra o agregado tem de ser escolhida, e a escolha e:

    1. ELA ESTA NAS MESMAS UNIDADES DA DECISAO. `mercado_limiar_de_leitura_de_
       glifo` e `mercado_margem_de_leitura_de_glifo` sao as duas travas que a
       PRODUCAO usa para recusar um glifo. Ordenar por quantas vezes um rotulo
       as encosta poe no topo exatamente o rotulo que a producao mais recusa.
       Qualquer outra chave mede uma grandeza que a decisao nao consulta, e o
       topo dela seria uma curiosidade em vez de uma pista.

    2. ELA E NORMALIZADA POR `n`. Uma chave por CONTAGEM de recusas enterraria
       um rotulo raro e fragil debaixo de um comum e sadio - 3 recusas em 4
       amostras perderiam para 20 em 400 - e coroaria o comum so pelo volume. A
       virgula e o `9` sao justamente os candidatos a raro.

    3. O PIOR SCORE SOZINHO FOI REJEITADO. Um unico recorte ocluido, meio
       rolado ou pego na troca de pagina coroaria um rotulo saudavel. Chave de
       amostra unica e amplificador de ruido, e este relatorio existe para ser
       acreditado sem segunda fonte.

    4. A MEDIANA FOI REJEITADA. Ela esconde a cauda, e o `8` e a prova: mediana
       0,7242 contra o proprio molde com a producao lendo bem. Uma chave que
       elege o `8` como o mais doente em TODA execucao e uma chave que ninguem
       le duas vezes.

    5. O DESEMPATE E DETERMINISTICO - `score_p1` crescente, depois `margem_p1`
       crescente, depois o rotulo. Um relatorio cuja ordem anda entre duas
       execucoes sobre a mesma populacao nao pode ser comparado com o da semana
       passada, e comparar duas execucoes e o unico uso que ele tem.

    A UNIAO CONTA UMA VEZ. A amostra que cai nas duas travas e recusada UMA vez
    pela producao, entao a taxa e `|abaixo do piso U abaixo da margem| / n`.
    Somar as duas contagens deixaria a taxa passar de 1,0, que e um numero que
    nao existe.

    TRAVA AUSENTE NAO E TRAVA EM ZERO. Com `piso` ou `margem_minima` em `None`
    a contagem correspondente sai `None` e a `taxa_de_recusa` tambem - nunca
    zero, e nunca um numero proprio inventado no lugar. Zero e uma medicao
    ("nada foi recusado"); ausente e a falta de uma. E uma taxa computada com
    METADE das travas subestimaria em silencio, que e pior do que nao ter.

    A RESSALVA QUE DECIDE SE O `9` E ACUSADO OU INOCENTADO
    ------------------------------------------------------
    OS BALDES SAO PELO ROTULO QUE A FERRAMENTA PROPOS, NUNCA PELA VERDADE. A
    varredura nao tem gabarito: ela nao sabe o que estava na tela, so o que os
    moldes disseram. Um `9` lido como `4` cai no balde do `4` e NUNCA aparece no
    do `9`. Ler este relatorio como se os baldes fossem a verdade e a leitura
    errada dele, e ela leva para o lado oposto do defeito.

        INOCENTA POR AUSENCIA  se o balde do `9` tiver taxa de recusa baixa e
        margens fundas, o erro de campo nao veio do score do `9` estar fraco - o
        `9` que a ferramenta viu, ela leu com folga. A busca se move para a
        SEGMENTACAO (`segmentar_glifos`) e para a geometria da coluna, que sao
        os dois lugares onde um `9` deixa de virar um run de `9`.

        ACUSA POR CAUDA  se o balde do `4` carregar uma cauda de margem baixa, e
        nessa cauda que um glifo estrangeiro estaria sentado: lido como `4` por
        pouco, com o segundo colocado colado. E cada `Amostra` guarda
        `(gravacao, arquivo, linha, coluna)`, entao a cauda pode ser reconferida
        frame a frame em vez de discutida.
    """
    do_rotulo: dict = {}
    for amostra in amostras:
        do_rotulo.setdefault(amostra.rotulo, []).append(amostra)

    linhas = []
    for rotulo, suas in do_rotulo.items():
        scores = np.asarray([a.score for a in suas], dtype=np.float64)
        margens = np.asarray([a.margem for a in suas], dtype=np.float64)

        abaixo_do_piso = (
            None if piso is None else int(sum(1 for a in suas if a.score < piso))
        )
        abaixo_da_margem = (
            None
            if margem_minima is None
            else int(sum(1 for a in suas if a.margem < margem_minima))
        )
        if piso is None or margem_minima is None:
            taxa = None
        else:
            recusadas = sum(
                1
                for a in suas
                if a.score < piso or a.margem < margem_minima
            )
            taxa = recusadas / len(suas)

        linhas.append(
            {
                "rotulo": rotulo,
                "n": len(suas),
                "score_min": float(scores.min()),
                "score_p1": float(np.percentile(scores, 1)),
                "score_p5": float(np.percentile(scores, 5)),
                "score_mediana": float(np.median(scores)),
                "margem_min": float(margens.min()),
                "margem_p1": float(np.percentile(margens, 1)),
                "margem_p5": float(np.percentile(margens, 5)),
                "margem_mediana": float(np.median(margens)),
                "abaixo_do_piso": abaixo_do_piso,
                "abaixo_da_margem": abaixo_da_margem,
                "taxa_de_recusa": taxa,
                # A populacao do rotulo viaja junto para o impressor poder
                # reusar `_quantis` sem reagrupar - e sem uma SEGUNDA copia do
                # formato `n/min/p1/p5/mediana/max`, que e por onde os dois
                # relatorios passariam a formatar diferente o mesmo numero.
                "scores": [float(v) for v in scores],
                "margens": [float(v) for v in margens],
            }
        )

    # `-1.0` no lugar de `None` so para ORDENAR: com a trava ausente todas as
    # taxas sao `None` juntas, entao a ordem cai inteira no desempate por
    # `score_p1`. O valor devolvido continua `None`.
    linhas.sort(
        key=lambda linha: (
            -(
                linha["taxa_de_recusa"]
                if linha["taxa_de_recusa"] is not None
                else -1.0
            ),
            linha["score_p1"],
            linha["margem_p1"],
            linha["rotulo"],
        )
    )
    return linhas


def _trava(valor) -> str:
    return "AUSENTE" if valor is None else f"{valor:.4f}"


def _contagem(valor) -> str:
    return "AUSENTE" if valor is None else str(valor)


def imprimir_a_fragilidade_por_rotulo(amostras, piso, margem_minima) -> None:
    """O relatorio por rotulo. So a impressao mora aqui; a conta e a de cima."""
    linhas = fragilidade_por_rotulo(amostras, piso, margem_minima)
    print("")
    print("=" * 78)
    print("RELATORIO POR ROTULO - QUEM ESTA EM APUROS, ORDENADO POR RECUSA")
    print("=" * 78)
    print(
        f"  as travas CONFIGURADAS: piso {_trava(piso)}  "
        f"margem {_trava(margem_minima)}"
    )
    print(
        "  (sao as da calibracao, as que estao VALENDO - nunca o par PROPOSTO "
        "pelo RELATORIO 1, que e hipotese)"
    )
    print(
        "  os baldes sao pelo rotulo PROPOSTO, nunca pela verdade: um `9` lido "
        "como `4` cai no balde do `4`."
    )
    print("")
    for linha in linhas:
        taxa = (
            "AUSENTE"
            if linha["taxa_de_recusa"] is None
            else f"{100.0 * linha['taxa_de_recusa']:.1f}%"
        )
        print(
            f"  '{linha['rotulo']}'  n={linha['n']:<6} "
            f"abaixo do piso {_contagem(linha['abaixo_do_piso']):<7} "
            f"abaixo da margem {_contagem(linha['abaixo_da_margem']):<7} "
            f"recusa {taxa}"
        )
        print("      score  " + _quantis(linha["scores"]))
        print("      margem " + _quantis(linha["margens"]))


def gravar(caminho: Path, piso: float, margem: float, tolerancia) -> None:
    """Load-mutate-save. Nunca montar uma `Calibracao` do zero.

    Montar do zero apagaria os 13 moldes de glifo e as 3 ancoras - o modo de
    falha REAL da janela quebrada 13, que custou uma recuperacao a mao em
    2026-08-30.
    """
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados["mercado_limiar_de_leitura_de_glifo"] = piso
    dados["mercado_margem_de_leitura_de_glifo"] = margem
    dados["mercado_tolerancia_do_cruzamento"] = tolerancia
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


def construir_analisador() -> argparse.ArgumentParser:
    """As chaves da linha de comando, numa casa so para o teste alcancar.

    `--por-rotulo` e ADITIVA e nasce FALSA: sem ela a ferramenta imprime
    exatamente o que sempre imprimiu, nem uma linha a mais nem a menos.
    """
    analisador = argparse.ArgumentParser(
        description=(
            "Mede o piso e a margem de LEITURA de glifo e julga a guarda de "
            "cruzamento sobre as 8 gravacoes do censo."
        )
    )
    analisador.add_argument("--gravacoes", default=str(RAIZ / "recordings"))
    analisador.add_argument("--calibracao", default=str(RAIZ / "calibration.json"))
    analisador.add_argument("--gravar", action="store_true")
    analisador.add_argument("--por-rotulo", action="store_true")
    return analisador


def main(argv=None) -> int:
    opcoes = construir_analisador().parse_args(argv)

    gravacoes = Path(opcoes.gravacoes).resolve()
    calibracao = Path(opcoes.calibracao).resolve()

    print("=" * 78)
    print("MEDICAO DA LEITURA DE GLIFO - 02-02 Task 2")
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
    ):
        if getattr(cal, chave) is None:
            print("")
            print(
                f"ERRO: {chave} esta ausente no calibration.json. As tres sao "
                "necessarias: as duas primeiras para o piso e a margem, e a "
                "terceira para o veredito da guarda. Rode calibrar-mercado.bat."
            )
            return 4
    moldes = glifos_de_calibracao(cal.mercado_templates_de_digito)
    de_um = sorted(r for r in moldes if len(r) == 1)
    print("")
    print(f"MOLDES DE UM CARACTERE: {len(de_um)} -> {de_um}")
    if not de_um:
        print("ERRO: sem molde de digito nao ha leitura a medir.")
        return 4

    print("")
    print("Varrendo... (tres colunas calibradas, linha a linha)")
    resultado = varrer(gravacoes, cal)
    print(f"  celulas com leitura: {len(resultado.celulas)} linhas de grade")
    print(f"  runs classificados : {len(resultado.amostras)}")
    for nome in GRAVACOES_DO_CENSO:
        print(
            f"  {nome:<42} {resultado.abertos_por_gravacao.get(nome, 0):>4} "
            "frames com painel aberto"
        )
    if not resultado.amostras:
        print("ERRO: nenhum glifo classificado. Nada a medir.")
        return 5

    # -----------------------------------------------------------------
    # RELATORIO 1 - a distribuicao, e o par (piso, margem)
    # -----------------------------------------------------------------
    linhas = linhas_do_cruzamento(resultado)
    confirmadas = {
        (linha.gravacao, linha.arquivo, linha.linha)
        for linha in linhas
        if linha.completa
        and residuo_do_cruzamento(linha.total, linha.unitario, linha.quantidade)
        <= limite_derivado_do_cruzamento(linha.quantidade) + 1e-9
    }

    print("")
    print("=" * 78)
    print("RELATORIO 1 - A DISTRIBUICAO DE SCORE E MARGEM")
    print("=" * 78)
    print("  score  " + _quantis([a.score for a in resultado.amostras]))
    print("  margem " + _quantis([a.margem for a in resultado.amostras]))
    print("")
    print("  O PIOR POR ROTULO (score / margem):")
    for rotulo in sorted({a.rotulo for a in resultado.amostras}):
        do_rotulo = [a for a in resultado.amostras if a.rotulo == rotulo]
        print(
            f"    '{rotulo}'  n={len(do_rotulo):>6}  "
            f"pior score {min(a.score for a in do_rotulo):.4f}  "
            f"pior margem {min(a.margem for a in do_rotulo):.4f}  "
            f"mediana do score {np.median([a.score for a in do_rotulo]):.4f}"
        )

    limiar_de_colisao = cal.mercado_limiar_de_glifo
    if limiar_de_colisao is not None:
        abaixo = sum(1 for a in resultado.amostras if a.score < limiar_de_colisao)
        print("")
        print(
            f"  O LIMIAR DE COLISAO {limiar_de_colisao:.4f} rejeitaria "
            f"{abaixo} de {len(resultado.amostras)} glifos reais "
            f"({100.0 * abaixo / len(resultado.amostras):.1f}%)."
        )
        print(
            "  Ele e `(1.0 + pior_par)/2` sobre molde-contra-molde. Nao e piso "
            "de leitura, e este numero e a razao."
        )
        abaixo_da_margem = sum(1 for a in resultado.amostras if a.margem < 0.12)
        print(
            f"  A MARGEM 0,12 herdada de identidade.py rejeitaria "
            f"{abaixo_da_margem} de {len(resultado.amostras)} "
            f"({100.0 * abaixo_da_margem / len(resultado.amostras):.1f}%)."
        )

    piso, margem, diag = propor_piso_e_margem(resultado, confirmadas)
    print("")
    print(
        f"  linhas CONFIRMADAS pelo cruzamento: {len(confirmadas)} de "
        f"{len(resultado.celulas)}"
    )
    if piso is None:
        print("  NENHUM PAR PROPOSTO: " + str(diag))
        return 6
    print(f"  PISO DE LEITURA PROPOSTO   {piso:.6f}")
    print(f"  MARGEM DE LEITURA PROPOSTA {margem:.6f}")
    print(
        f"  (o maior par que aceita os {diag['n_acerto']} glifos de linha "
        f"confirmada; ele recusa "
        f"{100.0 * diag.get('suspeita_recusada', 0.0):.1f}% dos "
        f"{diag['n_suspeita']} glifos de linha NAO confirmada)"
    )
    print("")
    print("  O PAR `0` x `8`, o mais estreito do sistema:")
    for rotulo in ("0", "8"):
        do_rotulo = [a for a in resultado.amostras if a.rotulo == rotulo]
        if do_rotulo:
            print(
                f"    lido como '{rotulo}': n={len(do_rotulo)}, "
                f"pior margem {min(a.margem for a in do_rotulo):.4f}"
            )

    # -----------------------------------------------------------------
    # RELATORIO POR ROTULO - so sob a chave, e sobre a MESMA populacao
    # -----------------------------------------------------------------
    if opcoes.por_rotulo:
        imprimir_a_fragilidade_por_rotulo(
            resultado.amostras,
            cal.mercado_limiar_de_leitura_de_glifo,
            cal.mercado_margem_de_leitura_de_glifo,
        )

    # -----------------------------------------------------------------
    # RELATORIO 2 - a coluna Quantity, que a pesquisa nunca mediu
    # -----------------------------------------------------------------
    print("")
    print("=" * 78)
    print("RELATORIO 2 - A COLUNA QUANTITY (A7 era DEDUCAO, nao medicao)")
    print("=" * 78)
    runs = resultado.runs_da_quantidade
    if runs:
        contagem = {}
        for quantos in runs:
            contagem[quantos] = contagem.get(quantos, 0) + 1
        print(f"  celulas de quantidade lidas: {len(runs)}")
        print("  runs por celula: " + str(dict(sorted(contagem.items()))))
    quantidades = [
        "".join(r for r, _, _ in leitura["quantidade"])
        for leitura in resultado.celulas.values()
        if "quantidade" in leitura
    ]
    com_virgula = [q for q in quantidades if "," in q]
    print(
        f"  leituras com SEPARADOR DE MILHAR: {len(com_virgula)} de "
        f"{len(quantidades)}"
    )
    if com_virgula:
        print("    exemplos: " + ", ".join(sorted(set(com_virgula))[:8]))
    extremos = resultado.extremos_da_quantidade
    print(
        f"  os glifos ocupam x em [{extremos['esquerda_min']}, "
        f"{extremos['direita_max']}) dentro de uma coluna de "
        f"{extremos['largura_da_coluna']} px"
    )
    print(
        "  -> o carimbo de quantidade desenhado sobre o ICONE fica FORA do "
        "retangulo calibrado: a coluna comeca depois do nome, e o icone fica "
        "antes dele."
        if extremos["esquerda_min"] is not None and extremos["esquerda_min"] > 0
        else "  -> ATENCAO: ha glifo encostado na borda esquerda da coluna."
    )
    gabarito = {
        ("20260828-063409-mercado-scroll-transicao", "frame_000012.png", 5): "10",
        ("20260828-063409-mercado-scroll-transicao", "frame_000012.png", 6): "48",
        ("20260828-063409-mercado-scroll-transicao", "frame_000012.png", 7): "5",
    }
    print("")
    print("  CONTRA O GABARITO DA SECAO 4 DO SPIKE-RESPOSTAS:")
    acertos = 0
    for chave, esperado in gabarito.items():
        leitura = resultado.celulas.get(chave, {}).get("quantidade")
        lido = "".join(r for r, _, _ in leitura) if leitura else None
        estado = "OK " if lido == esperado else "NAO"
        acertos += 1 if lido == esperado else 0
        print(f"    {estado} linha {chave[2]}: esperado {esperado!r}, lido {lido!r}")
    print(f"    {acertos} de {len(gabarito)}")

    # -----------------------------------------------------------------
    # RELATORIO 3 - o veredito da guarda de cruzamento
    # -----------------------------------------------------------------
    print("")
    print("=" * 78)
    print("RELATORIO 3 - O VEREDITO DA GUARDA DE CRUZAMENTO")
    print("=" * 78)
    completas = [linha for linha in linhas if linha.completa]
    print(f"  linhas com as tres colunas lidas e na gramatica: {len(completas)}")

    # O veredito e julgado sobre a populacao que a guarda REALMENTE vai ver em
    # producao: linha que ja passou pelo piso e pela margem. Julga-la sobre a
    # populacao crua mediria a leitura, nao a guarda - e a leitura crua traz
    # linha coberta que virou numero plausivel, que e exatamente o que o piso
    # existe para tirar do caminho antes.
    filtradas = linhas_do_cruzamento(resultado, piso, margem)
    completas_filtradas = [linha for linha in filtradas if linha.completa]
    print(
        f"  dessas, as que passam no piso {piso:.4f} e na margem "
        f"{margem:.4f}: {len(completas_filtradas)}"
    )
    veredito_cru = veredito_da_guarda(linhas)
    print("  (populacao CRUA, para conferencia: " + veredito_cru["linha_do_veredito"] + ")")

    veredito = veredito_da_guarda(filtradas)
    medida = veredito["medida"]
    if medida["n"]:
        print(
            f"  residuo por unidade: mediana "
            f"{medida['por_unidade_mediana']:.4f}, p95 "
            f"{medida['por_unidade_p95']:.4f}, max "
            f"{medida['por_unidade_max']:.4f}"
        )
        # O numero DERIVA de `LIMITE_POR_UNIDADE` em vez de ser repetido a mao.
        # A versao anterior escrevia `0,5/unidade` literal e teria continuado
        # escrevendo isso depois de a constante dobrar - um relatorio que mente
        # sobre a propria regua e pior que um relatorio ausente.
        print(
            f"  fechamento no LIMITE DERIVADO ({LIMITE_POR_UNIDADE}/unidade): "
            f"{medida['fechamento_no_limite_derivado']:.4f}"
        )
    print(
        f"  criterios: fechamento >= {FECHAMENTO_MINIMO}, tolerancia <= "
        f"{veredito['limite_aceitavel_por_unidade']}, deteccao >= "
        f"{DETECCAO_MINIMA}"
    )
    print(
        f"  medido: fechamento={veredito['fechamento']:.4f}, "
        f"tolerancia={veredito['tolerancia']}, "
        f"deteccao={veredito['deteccao']:.4f} sobre "
        f"{veredito['casos_injetados']} substituicoes injetadas"
    )
    # A QUEBRA POR LAYOUT, MEDIDA. Ate 2026-09-02 este lugar imprimia um aviso
    # dizendo que o portao de layout ainda nao existia e que a varredura media
    # sobre TODOS os layouts. Ele existe desde o 02-04, e agora e CHAMADO aqui -
    # entao o aviso virou numero.
    print("")
    print("  O PORTAO DE LAYOUT DE PRODUCAO, CHAMADO UMA VEZ POR FRAME ABERTO:")
    total_aberto = sum(resultado.abertos_por_layout.values())
    for veredito_do_portao, quantos in sorted(
        resultado.abertos_por_layout.items(), key=lambda par: str(par[0])
    ):
        rotulo = (
            "NENHUM (nao casou, ou empate)"
            if veredito_do_portao is None
            else veredito_do_portao
        )
        print(f"    {rotulo:<32} {quantos:>5} frames")
    print(f"    {'TOTAL com painel aberto':<32} {total_aberto:>5} frames")

    quebra = quebra_do_cruzamento_por_layout(resultado, piso, margem)
    de_negociacao = quebra.get("negociacao", 0)
    tiradas = sum(
        quantas for chave, quantas in quebra.items() if chave != "negociacao"
    )
    print("")
    print("  LINHAS COMPLETAS DO CRUZAMENTO, POR LAYOUT (apos piso e margem):")
    for veredito_do_portao, quantas in sorted(
        quebra.items(), key=lambda par: str(par[0])
    ):
        rotulo = (
            "NENHUM (nao casou, ou empate)"
            if veredito_do_portao is None
            else veredito_do_portao
        )
        print(f"    {rotulo:<32} {quantas:>5} linhas")
    print(
        f"    -> o portao TIROU {tiradas} linhas da populacao do cruzamento e "
        f"deixou {de_negociacao}."
    )
    if tiradas == 0:
        print(
            "    -> ZERO linhas tiradas E RESPOSTA, e ela DESMONTA a hipotese de "
            "contaminacao pela aba Adena: se o fechamento continuar baixo, a "
            "causa esta em outro lugar."
        )
    if de_negociacao == 0:
        print("")
        print(
            "  ####################################################################"
        )
        print(
            "  ATENCAO: NENHUM frame venceu como `negociacao`. A medicao da guarda "
            "ficou SEM POPULACAO."
        )
        print(
            "  Isto NAO e uma guarda reprovada - e uma guarda NAO MEDIDA, e "
            "confundir as duas gravaria `None` por engano."
        )
        print(
            "  Causas provaveis: `mercado_cabecalho_de_coluna` ausente no "
            "calibration.json (sem molde o portao nao tem candidato de "
            "negociacao), ou o bloco `mercado_layouts` ausente/torto."
        )
        print(
            "  ####################################################################"
        )

    print("")
    print("  FECHAMENTO NO LIMITE DERIVADO, POR GRAVACAO:")
    print(
        "  (so linhas de `negociacao`: o portao de PRODUCAO "
        "`LeitorDePagina._casamento_do_layout` ja filtrou a populacao. Na aba "
        "Adena a terceira coluna e `5 mln increment`, normalizada por 5 milhoes "
        "de adena e NAO por unidade - ali a relacao `total = unitario x "
        "quantidade` nao vale, e por construcao, nao por erro de leitura.)"
    )
    for nome in GRAVACOES_DO_CENSO:
        da_gravacao = [
            linha for linha in completas_filtradas if linha.gravacao == nome
        ]
        if not da_gravacao:
            print(f"    {nome[9:]:<34} (nenhuma linha)")
            continue
        fecham = sum(
            1
            for linha in da_gravacao
            if residuo_do_cruzamento(
                linha.total, linha.unitario, linha.quantidade
            )
            <= limite_derivado_do_cruzamento(linha.quantidade) + 1e-9
        )
        print(
            f"    {nome[9:]:<34} {fecham:>5} de {len(da_gravacao):>5}  "
            f"({100.0 * fecham / len(da_gravacao):>5.1f}%)"
        )

    print("")
    print("  " + veredito["linha_do_veredito"])

    print("")
    print("O QUE VAI PARA O calibration.json:")
    print(f"  mercado_limiar_de_leitura_de_glifo = {piso:.6f}")
    print(f"  mercado_margem_de_leitura_de_glifo = {margem:.6f}")
    print(
        "  mercado_tolerancia_do_cruzamento   = "
        + str(veredito["tolerancia_gravada"])
    )

    if opcoes.gravar:
        gravar(
            calibracao,
            float(piso),
            float(margem),
            veredito["tolerancia_gravada"],
        )
        print("")
        print("GRAVADO em " + str(calibracao) + " (load-mutate-save).")
    else:
        print("")
        print("(nada gravado - rode de novo com --gravar para persistir)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
