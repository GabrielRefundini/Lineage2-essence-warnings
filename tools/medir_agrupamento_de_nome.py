"""A varredura que MEDE o corte de agrupamento e a fonte da assinatura de digitos.

Ela varre as 8 gravacoes NOMEADAS do censo, recorta a COLUNA DO NOME calibrada
de cada linha, le com as duas escalas de OCR pelo caminho PUBLICO de `ocr.py`
(`ler_texto` 2x e `ler_texto_ampliado` 3x, os dois prometem nunca levantar), e
produz QUATRO relatorios:

    1  HISTOGRAMA DA SIMILARIDADE, com e sem a trava de digitos, e a proposta de
       `mercado_corte_de_similaridade` e `mercado_piso_de_similaridade`
    2  CENSO DO CONFLITO entre as escalas: quantas linhas D-02 e D-03 matam
       juntas quando a assinatura vem do OCR
    3  A FONTE DA ASSINATURA, medida contra o gabarito de encanto conhecido
       (a suposicao A8 da pesquisa, marcada como risco ALTO)
    4  RENDIMENTO DAS TRES ROTAS, com as series duplicadas que cada uma deixa no
       catalogo, nomeadas com as duas grafias lado a lado

ELA IMPORTA OS PREDICADOS DE PRODUCAO, NAO TEM COPIA DE NENHUM
================================================================
`similaridade`, `assinatura_por_ocr`, `assinatura_por_molde`, `chave_da_serie` e
`agrupar` vem de `l2scanner/mercado_catalogo.py`. Medir com uma implementacao e
decidir com outra seria comparar convencoes — a mesma razao ja escrita em
`propor_rotulo` e reaproveitada por `tools/medir_leitura_de_glifo.py`.

O motor de glifo (`pontuar_runs`) mora AQUI e e INJETADO no predicado, porque
`segmentar_glifos` e os dois alinhadores ainda vivem em `calibrar_mercado.py`,
que e ferramenta: ela chama `tornar_consciente_de_dpi()` no import. A seta
aponta sempre da ferramenta para o modulo puro. A promocao e o 02-04.

OS DOIS ROTULOS DA MEDICAO, E O QUE CADA UM VALE
=================================================
PRECISA AGRUPAR — as duas escalas sobre a MESMA linha do MESMO frame, quando
elas discordam em ATE 2 CARACTERES. O rotulo e inatacavel: sao os mesmos pixels
lidos duas vezes, e a pesquisa mediu que toda discordancia real de OCR neste
material e de 1-2 caracteres (`Lv. I`/`Lv. 1`, `Kng`/`King`). Uma discordancia
MAIOR nao e ruido, e erro de METODO — um nome lido como outro item — e nessa
hora a linha DEVE cair (D-01). Conta-la como "precisa agrupar" pediria ao corte
que fundisse duas coisas diferentes.

PRECISA SEPARAR — leituras de LINHAS DIFERENTES do mesmo frame, com textos
diferentes. O rotulo e mais fraco, e a honestidade custa dizer: duas linhas da
mesma pagina PODEM ser o mesmo item anunciado duas vezes. Os pares de texto
identico saem fora (a dupla ocorrencia visivel), e o residual contamina a
populacao na direcao que APERTA o corte. Errar apertando descarta; errar
afrouxando funde, e fusao no CSV e irreversivel (D-06).

O CONJUNTO DE MEDICAO E FECHADO
================================
`recordings/` tem 16 pastas; o censo de 335 frames da pesquisa cobriu 8, e sao
so essas que entram. A lista e importada de `tools/medir_oclusao.py` — duplica-la
seria a porta pela qual duas varreduras passariam a medir conjuntos diferentes
sem ninguem notar. A `pre-voo` sozinha tem 1502 PNGs e dominaria qualquer
distribuicao. Se uma pasta esperada faltar, a ferramenta PARA.

Uso (no checkout PRINCIPAL — `recordings/` e gitignored, e o motor de OCR so
responde no `.venv`):

    .venv/Scripts/python.exe tools/medir_agrupamento_de_nome.py
        --gravacoes C:/.../recordings --calibracao C:/.../calibration.json
"""

from __future__ import annotations

import argparse
import difflib
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

from l2scanner import ocr  # noqa: E402
from l2scanner.calibracao import Calibracao  # noqa: E402
from l2scanner.calibrar_mercado import (  # noqa: E402
    _alinhar_por_preenchimento,
    _par_incalculavel,
    segmentar_glifos,
)
from l2scanner.identidade import mascara_de_texto  # noqa: E402
from l2scanner.mercado_geometria import nivel_de_fundo_da_linha  # noqa: E402
from l2scanner.mercado_catalogo import (  # noqa: E402
    DIGITOS,
    EntradaDoCatalogo,
    agrupar,
    assinatura_por_molde,
    assinatura_por_ocr,
    chave_da_serie,
    similaridade,
)
from l2scanner.mercado_visao import (  # noqa: E402
    RastreioDoPainel,
    ancoras_de_calibracao,
    casamento_da_ancora,
    glifos_de_calibracao,
)


def _carregar_o_censo():
    """A lista das 8 gravacoes vive numa ferramenta so, e e importada daqui."""
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

# Ate 2 caracteres de diferenca entre as duas escalas e RUIDO do motor; acima
# disso e erro de METODO e a linha cai por desenho (D-01). O numero vem da
# pesquisa, que mediu as discordancias reais deste material: `Lv. I`/`Lv. 1`
# (1 caractere) e `Kng`/`King` (1 caractere).
DISTANCIA_MAXIMA_DE_RUIDO = 2

# ---------------------------------------------------------------------------
# O gabarito de encanto — observacao humana, nao saida de ferramenta
# ---------------------------------------------------------------------------

# As dez linhas de `20260828-063752-mercado-aberto/frame_000000`, o MESMO frame
# de que saiu a calibracao que o usuario conferiu e aprovou. O gabarito e o que
# os olhos leem na tela; ele nao vem de nenhuma medicao deste projeto, e e por
# isso que ele pode julgar as duas fontes candidatas sem circularidade.
FRAME_DO_GABARITO = ("20260828-063752-mercado-aberto", "frame_000000.png")
GABARITO_DE_ENCANTO = ("6", "4", "2", "7", "", "5", "7", "5", "7", "6")

# O caso em que o digito NAO fica no prefixo: ele fica no fim do nome, depois de
# `Lv.`. A pesquisa nomeia `scroll-transicao/frame_000016` como o frame em que a
# igualdade estrita entre escalas acertou 0 de 10 por causa dele.
MARCA_DO_NIVEL = "Lv."

# A mesma pagina se repete por centenas de frames enquanto o usuario fica
# parado. A medicao de MOLDE — que custa 13 casamentos por run e ha ~33 runs por
# nome — roda sobre PAGINAS DISTINTAS, e nao sobre as repeticoes: contar cada
# repeticao daria peso ao tempo parado em vez de ao material.
MAXIMO_DE_PAGINAS_DISTINTAS = 60


# ---------------------------------------------------------------------------
# O motor de glifo — a mecanica de `propor_rotulo`, reaproveitada e injetada
# ---------------------------------------------------------------------------


def pontuar_runs(recorte, moldes):
    """Cada run do recorte com `(rotulo, score, margem)`. `None` se nao da.

    Sem piso e sem margem: quem decide e `assinatura_por_molde`. Aplicar o corte
    aqui tornaria a medicao circular — e esta funcao existe justamente para
    PRODUZIR a distribuicao contra a qual o corte e julgado.

    Identica em mecanica a `pontuar_celula` de `tools/medir_leitura_de_glifo.py`
    e a `propor_rotulo`: mascara binaria, preenchimento ate a maior caixa comum,
    `casamento_da_ancora`, faixa de linhas COMPARTILHADA por todos os runs do
    recorte que ela recebe.
    """
    if recorte is None or getattr(recorte, "size", 0) == 0:
        return None
    faixa, runs = segmentar_glifos(recorte)
    if faixa is None or not runs:
        return None
    topo, base = faixa
    mascara = (mascara_de_texto(recorte) * 255).astype(np.uint8)
    de_um_caractere = {r: m for r, m in moldes.items() if len(r) == 1}
    if not de_um_caractere:
        return None

    saida = []
    for inicio, fim in runs:
        glifo = mascara[topo:base, inicio:fim]
        pontuados = []
        for rotulo, molde in de_um_caractere.items():
            a, b = _alinhar_por_preenchimento(glifo, molde)
            if _par_incalculavel(a, b):
                continue
            pontuados.append((casamento_da_ancora(a, b), rotulo))
        if not pontuados:
            return None
        pontuados.sort(reverse=True)
        melhor_score, melhor_rotulo = pontuados[0]
        segundo = pontuados[1][0] if len(pontuados) > 1 else -1.0
        saida.append(
            (melhor_rotulo, float(melhor_score), float(melhor_score - segundo))
        )
    return saida


def recorte_de_runs(recorte, runs, inicio: int, fim: int):
    """O sub-recorte que cobre `runs[inicio:fim]`, na largura.

    A FAIXA DE LINHAS E RECALCULADA SOBRE O SUB-RECORTE, E ISSO E O EXPERIMENTO.
    `segmentar_glifos` deriva UMA faixa compartilhada por todos os runs do
    recorte que recebe. No nome inteiro essa faixa e esticada pelas ascendentes e
    descendentes das LETRAS (medido: 11 px em `063752/frame_000000`), e um digito
    medido dentro dela nao casa com um molde cortado de uma coluna que so tem
    digito. Isolado, o mesmo digito recupera a propria banda — e o score sobe de
    0,31 para 0,89 no `+6` da linha 0. A diferenca entre as duas variantes NAO e
    detalhe de recorte: e o resultado.
    """
    if not runs or inicio >= fim or fim > len(runs) or inicio < 0:
        return None
    return recorte[:, runs[inicio][0] : runs[fim - 1][1]]


def assinatura_de_molde_da_linha(recorte, moldes, piso: float, margem: float):
    """A assinatura que a rota `molde` produziria para a linha inteira.

    REGRA: cada run e reclassificado SOZINHO (faixa propria), e vira digito
    quando passa no piso E na margem. Os que nao passam sao tratados como "nao e
    digito" — que e a unica leitura possivel, porque o conjunto de 13 moldes NAO
    TEM CLASSE DE REJEICAO: nao ha molde de letra, entao toda letra e forcada
    sobre o digito mais parecido e sai com algum score.

    Devolve `(assinatura, aprovados)`, com `aprovados` = `[(indice, rotulo,
    score, margem), ...]` para que o relatorio possa mostrar QUAIS runs passaram
    — e nao so o resultado.
    """
    if recorte is None or getattr(recorte, "size", 0) == 0:
        return None, []
    _, runs = segmentar_glifos(recorte)
    if not runs:
        return None, []
    aprovados = []
    lido = []
    for indice in range(len(runs)):
        sub = recorte_de_runs(recorte, runs, indice, indice + 1)
        pontuados = pontuar_runs(sub, moldes)
        if not pontuados:
            continue
        rotulo, score, distancia = pontuados[0]
        if rotulo in DIGITOS and score >= piso and distancia >= margem:
            aprovados.append((indice, rotulo, score, distancia))
            lido.append(rotulo)
    return "".join(lido), aprovados


# ---------------------------------------------------------------------------
# A varredura
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeituraDeNome:
    """O nome de UMA linha, lido pelas duas escalas."""

    gravacao: str
    arquivo: str
    linha: int
    texto2x: str
    texto3x: str

    @property
    def origem(self) -> tuple[str, str, int]:
        return (self.gravacao, self.arquivo, self.linha)

    @property
    def frame(self) -> tuple[str, str]:
        return (self.gravacao, self.arquivo)

    @property
    def concordam(self) -> bool:
        return self.texto2x == self.texto3x


@dataclass
class ResultadoDaVarredura:
    leituras: list = field(default_factory=list)
    abertos_por_gravacao: dict = field(default_factory=dict)
    vazias: int = 0
    meia_leitura: int = 0
    cobertas: int = 0
    sem_sonda: int = 0
    exemplos_de_coberta: list = field(default_factory=list)


def _texto(bruto) -> str:
    """O que o motor devolveu, normalizado. `None` e vazio viram `""`.

    Quebra de linha vira espaco: o motor entrega o texto com `\\n` quando acha
    mais de uma linha no recorte, e um `\\n` no meio de um nome quebraria o slug
    da chave sem dizer por que.
    """
    if not bruto:
        return ""
    return " ".join(str(bruto).split())


def distancia_de_edicao(a: str, b: str) -> int:
    """Quantos caracteres separam as duas leituras, por `difflib.opcodes`.

    Nao e Levenshtein exata: e a contagem de caracteres tocados pelos blocos de
    diferenca que o MESMO `SequenceMatcher` que decide a similaridade encontrou.
    Usar o mesmo motor das duas coisas evita que o rotulo da populacao e a
    metrica que ela julga discordem sobre o que e "uma diferenca".
    """
    total = 0
    for etiqueta, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, a, b
    ).get_opcodes():
        if etiqueta != "equal":
            total += max(i2 - i1, j2 - j1)
    return total


def varrer(gravacoes: Path, cal: Calibracao) -> ResultadoDaVarredura:
    """A coluna do nome de toda linha LIMPA de todo frame com painel aberto.

    A SONDA DE OCLUSAO DO 02-02 FILTRA A VARREDURA, E ISSO NAO E ZELO: E O QUE
    FAZ O NUMERO SIGNIFICAR ALGUMA COISA. Medido sem ela, sobre as 8 gravacoes,
    a populacao "precisa separar" ficava contaminada por linhas em que a tooltip
    comeu ou acrescentou pedaco do nome — `'Common Mafia der Luciano Doll'`
    contra `'Common Mafia Leader Luciano Doll'` (0,9508),
    `"Aden's Soul Crystal Lv. 1 - W"` contra `"... - Weapon"` (0,9206),
    `'mate Common Mafia Leader Luciano Doll'` (vazamento de tooltip) — todas o
    MESMO item de uma linha vizinha, com a leitura corrompida por oclusao. Com
    esse rotulo as duas populacoes se sobrepunham em 1.338 pares e nenhum corte
    era proponivel.

    Em producao essas linhas NAO CHEGAM ao agrupamento: a sonda as descarta
    antes (D-14). Medir o corte sobre elas seria calibrar sobre uma populacao
    que a producao nunca ve — o mesmo erro que o 02-02 corrigiu ao julgar a
    guarda de cruzamento sobre a populacao pos-piso, e nao sobre a crua.

    Linha que a sonda nao consegue MEDIR tambem sai, e e contada a parte: "nao
    da para medir" e uma resposta legitima, e diferente de "esta limpa".
    """
    grade = cal.mercado_grade or {}
    n_linhas = int(grade["linhas_por_pagina"])
    altura = int(grade["altura_da_linha"])
    ancoras = ancoras_de_calibracao(cal.mercado_ancoras)
    limiar = float(cal.mercado_limiar_da_ancora or 0.73)
    coluna = cal.mercado_coluna_do_nome
    sonda = cal.mercado_sonda_do_fundo or {}
    limiar_de_dispersao = float(cal.mercado_limiar_de_dispersao_do_fundo)

    resultado = ResultadoDaVarredura()
    for nome in GRAVACOES_DO_CENSO:
        rastreio = RastreioDoPainel(ancoras, limiar)
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
            gx = ox + int(grade["dx"])
            gy = oy + int(grade["dy"])
            x = ox + int(coluna["dx"])
            largura = int(coluna["largura"])
            cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            for indice in range(n_linhas):
                topo = gy + indice * altura
                if (
                    topo < 0
                    or x < 0
                    or topo + altura > frame.shape[0]
                    or x + largura > frame.shape[1]
                ):
                    continue
                medido = nivel_de_fundo_da_linha(
                    cinza,
                    (
                        gx + int(sonda["dx0"]),
                        topo,
                        int(sonda["dx1"]) - int(sonda["dx0"]),
                        altura,
                    ),
                    int(sonda["folga"]),
                )
                if medido is None:
                    resultado.sem_sonda += 1
                    continue
                if medido[1] > limiar_de_dispersao:
                    resultado.cobertas += 1
                    if len(resultado.exemplos_de_coberta) < 6:
                        recorte = frame[topo : topo + altura, x : x + largura]
                        resultado.exemplos_de_coberta.append(
                            (
                                f"{nome[9:]}/{caminho.name}:{indice}",
                                medido[1],
                                _texto(ocr.ler_texto_ampliado(recorte)),
                            )
                        )
                    continue
                recorte = frame[topo : topo + altura, x : x + largura]
                dois = _texto(ocr.ler_texto(recorte))
                tres = _texto(ocr.ler_texto_ampliado(recorte))
                if not dois and not tres:
                    resultado.vazias += 1
                    continue
                if not dois or not tres:
                    # Uma escala leu e a outra nao. Em producao a linha cai; aqui
                    # ela e contada e sai da distribuicao, porque um par com um
                    # lado vazio tem similaridade 0,0 por definicao e poluiria a
                    # populacao com um zero que nao mede leitura nenhuma.
                    resultado.meia_leitura += 1
                    continue
                resultado.leituras.append(
                    LeituraDeNome(nome, caminho.name, indice, dois, tres)
                )
        resultado.abertos_por_gravacao[nome] = abertos
    return resultado


def paginas_distintas(leituras, maximo: int = MAXIMO_DE_PAGINAS_DISTINTAS) -> list:
    """Um frame por CONTEUDO de pagina distinto, na ordem da varredura.

    A pagina parada se repete por centenas de frames. Medir cada repeticao daria
    peso ao tempo em que o usuario ficou olhando, e nao ao material.
    """
    por_frame: dict = {}
    for leitura in leituras:
        por_frame.setdefault(leitura.frame, []).append(leitura)
    vistas: set = set()
    escolhidas = []
    for frame in sorted(por_frame):
        assinatura = tuple(
            (le.linha, le.texto3x) for le in sorted(por_frame[frame], key=lambda le: le.linha)
        )
        if assinatura in vistas:
            continue
        vistas.add(assinatura)
        escolhidas.append(frame)
        if len(escolhidas) >= maximo:
            break
    return escolhidas


# ---------------------------------------------------------------------------
# RELATORIO 1 — o histograma e a proposta
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Par:
    """Duas leituras que a medicao compara, com o rotulo do que elas PRECISAM."""

    a: str
    b: str
    score: float
    origem: str


def vocabulario_de_consenso(leituras) -> set:
    """Os nomes que as DUAS escalas leram identicos em alguma linha limpa.

    E a unica nocao de "leitura confiavel" que este material sustenta, e ela e a
    propria D-d: duas leituras pelo MESMO metodo concordam no mesmo erro, entao
    o acordo entre DOIS metodos diferentes sobre a mesma string e evidencia de
    que a string existe na tela. As duas populacoes do RELATORIO 1 se apoiam
    nela, e por isso o criterio de confianca dos dois lados e o MESMO.
    """
    return {le.texto3x for le in leituras if le.concordam}


def pares_que_precisam_agrupar(leituras, com_trava: bool, consenso: set) -> tuple:
    """As duas escalas sobre a MESMA linha, quando discordam em ATE 2 caracteres.

    Devolve `(pares, descartados_por_metodo, sem_consenso)`.

    OS DESCARTADOS POR METODO sao as discordancias GRANDES: elas nao entram
    porque a linha delas DEVE cair (D-01, diversidade de metodo), e pedi-las ao
    corte seria pedir uma fusao.

    OS SEM CONSENSO sao os pares em que NENHUM dos dois lados e um nome que o
    acordo entre as duas escalas confirmou em algum lugar. Medido, o pior deles
    era `'\\ufffdano'` x `'-ano'` — quatro caracteres, o resto do nome comido —
    e ele sozinho puxava o corte de 0,8947 para 0,7500. Um par assim nao e uma
    leitura ruidosa de um NOME: sao duas leituras FALHADAS, e uma leitura
    falhada nao pode ensinar nada ao corte. Eles saem da populacao, mas nao do
    relatorio: `main` confere se o corte proposto os aceitaria mesmo assim.

    Com a trava ligada, o par cujas assinaturas de digito diferem tambem nao
    entra: ele nunca chega a similaridade em producao — a linha morre antes.
    Esse par e o assunto do RELATORIO 2, e conta-lo aqui misturaria o custo da
    trava com a escolha do corte.
    """
    pares = []
    por_metodo = []
    sem_consenso = []
    for leitura in leituras:
        if com_trava and assinatura_por_ocr(leitura.texto2x) != assinatura_por_ocr(
            leitura.texto3x
        ):
            continue
        if distancia_de_edicao(leitura.texto2x, leitura.texto3x) > (
            DISTANCIA_MAXIMA_DE_RUIDO
        ):
            por_metodo.append(leitura)
            continue
        par = Par(
            leitura.texto2x,
            leitura.texto3x,
            similaridade(leitura.texto2x, leitura.texto3x),
            f"{leitura.gravacao[9:]}/{leitura.arquivo}:{leitura.linha}",
        )
        if par.a in consenso or par.b in consenso:
            pares.append(par)
        else:
            sem_consenso.append(par)
    return pares, por_metodo, sem_consenso


def pares_que_precisam_separar(leituras, com_trava: bool) -> tuple:
    """Leituras de LINHAS DIFERENTES do mesmo frame, com textos diferentes.

    Devolve `(pares, indecidiveis)`.

    So a escala 3x entra, e nao as duas: as duas juntas dobrariam a populacao com
    pares quase-identicos e dariam peso extra ao ruido do motor dentro de uma
    populacao que existe para medir ITENS diferentes.

    Com a trava ligada, os pares de assinatura diferente saem: eles ja estao
    separados POR CONSTRUCAO e a similaridade nunca os ve.

    OS INDECIDIVEIS SAIRAM DA POPULACAO, E ISSO E MEDICAO, NAO CONVENIENCIA.
    Um par de linhas diferentes que discorda em ATE 2 CARACTERES nao pode ser
    rotulado a partir do texto: e a MESMA faixa de diferenca que, dentro de uma
    linha, este arquivo chama de ruido de OCR. Medido em
    `scroll-transicao/frame_000005`, com a trava JA ligada, o par que sobrava no
    topo era `'D-grade Crystal'` x `'D-grade crystal'` — duas linhas da mesma
    pagina, o MESMO item, diferindo so na caixa da inicial. Chamar isso de
    "precisa separar" seria pedir ao corte que separasse um item de si mesmo, e
    o corte que saisse dali fundiria e descartaria pelos motivos errados.

    Eles nao sao ignorados: `main` imprime a populacao inteira com o veredito
    que o corte proposto lhes daria, para que o custo da exclusao seja
    conferivel em vez de acreditado.

    SO LINHAS DE CONSENSO ENTRAM, E ESSA E A SEGUNDA CORRECAO POR MEDICAO. Uma
    linha que so UMA escala leu daquele jeito nao autoriza ninguem a dizer "estes
    sao dois itens diferentes". Sem esse filtro, os pares no topo da populacao
    eram todos o MESMO item de uma linha vizinha com a leitura corrompida por
    oclusao que a sonda nao alcanca — `'Cohi nn Mafia Leader Luciano Doll'`
    contra `'Common Mafia Leader Luciano Doll'` (0,8923),
    `'Common Mafia Leader-Luce Doll'` (0,8852) — e eles empurravam o piso para
    cima de itens que precisam de serie propria. Com o filtro, o topo passa a
    ser `'Water Spirit Evolution Stone'` x `'Wind Spirit Evolution Stone'`
    (0,8727), que sao mesmo dois itens diferentes.

    (A sonda do 02-02 mede um trecho a DIREITA do inicio do nome; a marcacao de
    alvo corrompe o INICIO. Ela nao alcanca esse caso, e isso e material para o
    02-04, que e quem poe a sonda no lugar certo do pipeline.)
    """
    por_frame: dict = {}
    for leitura in leituras:
        if not leitura.concordam:
            continue
        por_frame.setdefault(leitura.frame, []).append(leitura)

    pares = []
    indecidiveis = []
    for (gravacao, arquivo), do_frame in por_frame.items():
        for i in range(len(do_frame)):
            for j in range(i + 1, len(do_frame)):
                a, b = do_frame[i].texto3x, do_frame[j].texto3x
                if a == b:
                    continue
                if com_trava and assinatura_por_ocr(a) != assinatura_por_ocr(b):
                    continue
                par = Par(
                    a,
                    b,
                    similaridade(a, b),
                    f"{gravacao[9:]}/{arquivo}:"
                    f"{do_frame[i].linha}x{do_frame[j].linha}",
                )
                if distancia_de_edicao(a, b) <= DISTANCIA_MAXIMA_DE_RUIDO:
                    indecidiveis.append(par)
                else:
                    pares.append(par)
    return pares, indecidiveis


def fusoes_no_corte(consenso: set, corte: float) -> list:
    """Os pares de nomes CONFIRMADOS que o corte proposto fundiria numa serie so.

    O vocabulario de consenso e o conjunto fechado dos nomes que as duas escalas
    confirmaram. Dois deles com a MESMA assinatura de digito e similaridade
    `>= corte` cairiam na mesma serie — e como sao dois nomes que a tela
    realmente mostrou, cada par aqui e uma FUSAO CANDIDATA, exatamente o defeito
    que D-06 chama de irreversivel.

    Esta lista existe porque um corte so pode ser julgado junto com o que ele
    fundiria. Ela nao decide nada: nem toda fusao e erro (`'D-grade Crystal'` e
    `'D-grade crystal'` sao o mesmo item, e agrupa-los e o certo). Quem le a
    lista e quem sabe distinguir, e essa e a razao de ela ser IMPRESSA INTEIRA.
    """
    nomes = sorted(consenso)
    achados = []
    for i in range(len(nomes)):
        for j in range(i + 1, len(nomes)):
            a, b = nomes[i], nomes[j]
            if assinatura_por_ocr(a) != assinatura_por_ocr(b):
                continue
            score = similaridade(a, b)
            if score >= corte:
                achados.append((score, a, b))
    achados.sort(reverse=True)
    return achados


def propor_corte_e_piso(agrupam, separam) -> dict:
    """O corte e o piso, das duas populacoes rotuladas.

        corte = min(precisa agrupar)                  — empate no corte AGRUPA
        piso  = (max(precisa separar) + corte) / 2    — o MEIO DO VAO

    O CORTE E O MINIMO DA POPULACAO QUE PRECISA AGRUPAR, e a margem dele e zero
    de proposito: `>=` faz o pior par cair do lado que agrupa. Escolher qualquer
    numero acima disso recusaria um par que os mesmos pixels produziram duas
    vezes — uma discordancia de 1-2 caracteres sobre um nome confirmado — e essa
    e exatamente a perda que D-02 foi revisado para evitar.

    O PISO E O MEIO DO VAO, E NAO `max(separar)`. A primeira tentativa foi
    `piso = max(separar)`, com o argumento de que a faixa cinzenta ficaria com o
    vao inteiro e a duvida toda cairia do lado que descarta (D-06). ELA FOI
    DERRUBADA POR UM CASO CONCRETO: com `piso = max(separar)`, o pior par que
    precisa separar cai EXATAMENTE no piso, e "empate no piso descarta" — entao
    `'Wind Spirit Evolution Stone'`, medido em 0,8727 contra
    `'Water Spirit Evolution Stone'`, seria descartado toda vez em vez de virar
    serie nova. O item ficaria PERMANENTEMENTE invisivel no catalogo. Descarte
    nao e irreversivel quando acontece uma vez; e irreversivel quando acontece
    SEMPRE para o mesmo item.

    O meio do vao e a construcao que este projeto ja usa para
    `mercado_limiar_de_glifo`, que e `(1.0 + pior_par) / 2` — margem igual para
    os dois lados. A faixa cinzenta continua existindo, com metade do vao.

    Sobreposicao (`max(separam) >= min(agrupam)`) NAO produz proposta. Um corte
    escolhido dentro da sobreposicao decidiria coisas opostas com o mesmo
    numero, que e exatamente o defeito que derrubou o `WRatio` com corte 88.
    """
    diagnostico = {
        "n_agrupam": len(agrupam),
        "n_separam": len(separam),
        "corte": None,
        "piso": None,
        "pior_separar": None,
        "folga": None,
        "sobrepostos": [],
    }
    if not agrupam:
        diagnostico["motivo"] = "nenhum par que precisa agrupar"
        return diagnostico
    if not separam:
        diagnostico["motivo"] = "nenhum par que precisa separar"
        return diagnostico

    corte = min(par.score for par in agrupam)
    pior_separar = max(par.score for par in separam)
    diagnostico["corte"] = corte
    diagnostico["pior_separar"] = pior_separar
    diagnostico["piso"] = (pior_separar + corte) / 2.0
    diagnostico["folga"] = corte - pior_separar
    if pior_separar >= corte:
        diagnostico["sobrepostos"] = sorted(
            [par for par in separam if par.score >= corte], key=lambda par: -par.score
        )
        diagnostico["motivo"] = "as duas populacoes se SOBREPOEM"
    return diagnostico


# ---------------------------------------------------------------------------
# RELATORIO 2 — o censo do conflito entre as escalas
# ---------------------------------------------------------------------------


def censo_do_conflito(leituras) -> dict:
    """Quantas linhas D-02 e D-03 matam juntas quando a assinatura vem do OCR.

    Uma linha em que as duas escalas produzem assinaturas de digito DIFERENTES
    nunca chega a similaridade: a trava separa antes, as duas leituras caem em
    series diferentes, e a linha morre. Esse e o custo exato de `ocr-estrito`.
    """
    conflitos = []
    for leitura in leituras:
        a = assinatura_por_ocr(leitura.texto2x)
        b = assinatura_por_ocr(leitura.texto3x)
        if a != b:
            conflitos.append((leitura, a, b))

    por_frame: dict = {}
    for leitura, a, b in conflitos:
        por_frame.setdefault(leitura.frame, []).append(
            (leitura.linha, a, b, leitura.texto2x, leitura.texto3x)
        )
    linhas_por_frame: dict = {}
    for leitura in leituras:
        linhas_por_frame[leitura.frame] = linhas_por_frame.get(leitura.frame, 0) + 1

    return {
        "n_linhas": len(leituras),
        "n_conflitos": len(conflitos),
        "conflitos": conflitos,
        "por_frame": por_frame,
        "linhas_por_frame": linhas_por_frame,
    }


# ---------------------------------------------------------------------------
# RELATORIO 3 — a fonte da assinatura (a suposicao A8)
# ---------------------------------------------------------------------------


def _geometria(cal: Calibracao):
    grade = cal.mercado_grade or {}
    return (
        int(grade["altura_da_linha"]),
        int(grade["dy"]),
        int(cal.mercado_coluna_do_nome["dx"]),
        int(cal.mercado_coluna_do_nome["largura"]),
        ancoras_de_calibracao(cal.mercado_ancoras),
        float(cal.mercado_limiar_da_ancora or 0.73),
    )


def _recortes_do_frame(gravacoes: Path, cal: Calibracao, frame_id) -> dict:
    """`{linha: recorte_bgr}` da coluna do nome. `{}` quando o painel nao abre."""
    altura, dy, dx, largura, ancoras, limiar = _geometria(cal)
    caminho = gravacoes / frame_id[0] / frame_id[1]
    frame = cv2.imread(str(caminho))
    if frame is None:
        return {}
    rastreio = RastreioDoPainel(ancoras, limiar)
    if not rastreio.observar(frame).aberto or rastreio.origem is None:
        return {}
    ox, oy = rastreio.origem
    gy = oy + dy
    x = ox + dx
    recortes = {}
    for indice in range(int((cal.mercado_grade or {})["linhas_por_pagina"])):
        topo = gy + indice * altura
        if (
            topo < 0
            or x < 0
            or topo + altura > frame.shape[0]
            or x + largura > frame.shape[1]
        ):
            continue
        recortes[indice] = frame[topo : topo + altura, x : x + largura]
    return recortes


def medir_moldes_nas_paginas(gravacoes: Path, cal: Calibracao, leituras, paginas):
    """A assinatura de MOLDE de cada linha das paginas distintas escolhidas.

    Devolve `{origem: {"assinatura", "aprovados", "runs"}}`.
    """
    moldes = glifos_de_calibracao(cal.mercado_templates_de_digito)
    piso = float(cal.mercado_limiar_de_leitura_de_glifo)
    margem = float(cal.mercado_margem_de_leitura_de_glifo)
    por_frame: dict = {}
    for leitura in leituras:
        por_frame.setdefault(leitura.frame, []).append(leitura)

    saida: dict = {}
    for frame_id in paginas:
        recortes = _recortes_do_frame(gravacoes, cal, frame_id)
        for leitura in por_frame.get(frame_id, []):
            recorte = recortes.get(leitura.linha)
            if recorte is None:
                continue
            assinatura, aprovados = assinatura_de_molde_da_linha(
                recorte, moldes, piso, margem
            )
            _, runs = segmentar_glifos(recorte)
            saida[leitura.origem] = {
                "assinatura": assinatura,
                "aprovados": aprovados,
                "runs": len(runs),
            }
    return saida


def medir_a_fonte_da_assinatura(gravacoes: Path, cal: Calibracao, leituras, moldados):
    """`assinatura_por_molde` contra o gabarito de encanto, e o caso `Lv. N`.

    A pesquisa marcou isto como suposicao A8 de risco ALTO e nunca a mediu: os
    13 moldes de digito foram cortados das colunas de NUMERO, e o texto do NOME
    tem outra vizinhanca. O gabarito `+6/+4/+2/+7/(nenhum)/+5/+7/+5/+7/+6` e
    observacao humana sobre o mesmo frame que o usuario calibrou, entao ele
    julga as duas fontes sem circularidade.

    Tres variantes de recorte, porque a diferenca entre elas E o resultado:

        PREFIXO   os dois primeiros runs (`+` e o digito) juntos
        DIGITO    so o segundo run, isolado — o TETO do que a rota poderia dar
                  se alguem soubesse de antemao qual run e o digito
        LINHA     a regra que a rota `molde` teria de usar em producao: cada run
                  sozinho, digito quando passa no piso E na margem

    A terceira e a unica honesta, porque em producao ninguem sabe qual run e o
    digito antes de le-lo.
    """
    moldes = glifos_de_calibracao(cal.mercado_templates_de_digito)
    piso = float(cal.mercado_limiar_de_leitura_de_glifo)
    margem = float(cal.mercado_margem_de_leitura_de_glifo)
    pasta, arquivo = FRAME_DO_GABARITO
    saida = {
        "frame": f"{pasta}/{arquivo}",
        "piso": piso,
        "margem": margem,
        "linhas": [],
        "molde_acerto": 0,
        "molde_descarte": 0,
        "molde_erro": 0,
        "linha_acerto": 0,
        "linha_erro": 0,
        "ocr_acerto": 0,
        "ocr_erro": 0,
        "nivel": [],
        "verdadeiros": [],
        "falsos": [],
    }
    recortes = _recortes_do_frame(gravacoes, cal, FRAME_DO_GABARITO)
    if not recortes:
        saida["erro"] = f"o painel nao abriu em {pasta}/{arquivo}"
        return saida

    por_linha = {
        le.linha: le for le in leituras if le.frame == FRAME_DO_GABARITO
    }
    for indice, esperada in enumerate(GABARITO_DE_ENCANTO):
        recorte = recortes.get(indice)
        if recorte is None:
            continue
        _, runs = segmentar_glifos(recorte)
        por_prefixo = assinatura_por_molde(
            recorte_de_runs(recorte, runs, 0, 2),
            moldes,
            piso,
            margem,
            pontuar_runs=pontuar_runs,
        )
        por_digito = assinatura_por_molde(
            recorte_de_runs(recorte, runs, 1, 2),
            moldes,
            piso,
            margem,
            pontuar_runs=pontuar_runs,
        )
        da_linha, aprovados = assinatura_de_molde_da_linha(
            recorte, moldes, piso, margem
        )
        leitura = por_linha.get(indice)
        por_ocr = assinatura_por_ocr(leitura.texto3x) if leitura else None
        saida["linhas"].append(
            {
                "linha": indice,
                "esperada": esperada,
                "molde_prefixo": por_prefixo,
                "molde_digito": por_digito,
                "molde_linha": da_linha,
                "aprovados": aprovados,
                "ocr": por_ocr,
                "texto3x": leitura.texto3x if leitura else None,
            }
        )
        if esperada:
            if por_digito is None:
                saida["molde_descarte"] += 1
            elif por_digito == esperada:
                saida["molde_acerto"] += 1
            else:
                saida["molde_erro"] += 1
            saida["ocr_acerto" if por_ocr == esperada else "ocr_erro"] += 1
        saida["linha_acerto" if da_linha == esperada else "linha_erro"] += 1

    # ------------------------------------------------------------------
    # As duas populacoes que decidem se existe piso possivel para o NOME
    # ------------------------------------------------------------------
    # FALSO: todo run aprovado numa linha em que NENHUMA das duas escalas viu
    # digito. Nao precisa de alinhamento entre run e caractere — se nao ha
    # digito no nome, todo digito lido e falso, e ponto.
    # VERDADEIRO: o run 1 de uma linha cujo texto comeca com `+N ` — o digito do
    # prefixo de encanto, cuja posicao a propria grafia entrega.
    por_origem = {le.origem: le for le in leituras}
    for origem, dados in moldados.items():
        leitura = por_origem.get(origem)
        if leitura is None:
            continue
        sem_digito = not assinatura_por_ocr(leitura.texto2x) and not (
            assinatura_por_ocr(leitura.texto3x)
        )
        if sem_digito:
            for indice, rotulo, score, distancia in dados["aprovados"]:
                saida["falsos"].append(
                    (score, distancia, rotulo, indice, leitura.texto3x, origem)
                )
        texto = leitura.texto3x
        if len(texto) > 2 and texto[0] == "+" and texto[1] in DIGITOS:
            for indice, rotulo, score, distancia in dados["aprovados"]:
                if indice == 1:
                    saida["verdadeiros"].append(
                        (score, distancia, rotulo, texto[1], texto, origem)
                    )
    saida["falsos"].sort(reverse=True)
    saida["verdadeiros"].sort()

    # O caso `Lv. N`: o digito fica no FIM do nome, e nao no prefixo.
    vistos: set = set()
    for leitura in leituras:
        if MARCA_DO_NIVEL not in leitura.texto3x:
            continue
        if not assinatura_por_ocr(leitura.texto3x):
            continue
        if leitura.frame in vistos:
            continue
        vistos.add(leitura.frame)
        recortes = _recortes_do_frame(gravacoes, cal, leitura.frame)
        recorte = recortes.get(leitura.linha)
        if recorte is None:
            continue
        _, runs = segmentar_glifos(recorte)
        ultimo = assinatura_por_molde(
            recorte_de_runs(recorte, runs, len(runs) - 1, len(runs)),
            moldes,
            piso,
            margem,
            pontuar_runs=pontuar_runs,
        )
        da_linha, _ = assinatura_de_molde_da_linha(recorte, moldes, piso, margem)
        saida["nivel"].append(
            {
                "origem": f"{leitura.gravacao[9:]}/{leitura.arquivo}:{leitura.linha}",
                "texto2x": leitura.texto2x,
                "texto3x": leitura.texto3x,
                "ocr2x": assinatura_por_ocr(leitura.texto2x),
                "ocr3x": assinatura_por_ocr(leitura.texto3x),
                "molde_ultimo_run": ultimo,
                "molde_linha": da_linha,
            }
        )
        if len(saida["nivel"]) >= 6:
            break
    return saida


# ---------------------------------------------------------------------------
# RELATORIO 4 — o rendimento das TRES ROTAS
# ---------------------------------------------------------------------------

ROTAS = ("molde", "ocr-estrito", "ocr-igualdade")


def rendimento_de_uma_rota(
    rota: str, leituras, corte: float, piso: float, moldados: dict | None = None
) -> dict:
    """'Li N, perdi M' para UMA rota, com o catalogo crescendo pelo caminho.

    As leituras sao percorridas em ordem DETERMINISTICA (gravacao, arquivo,
    linha) — o catalogo e estado acumulado, e uma ordem instavel daria um numero
    diferente a cada rodada.

    Uma linha SOBREVIVE quando as duas escalas caem na MESMA chave (D-02). Chave
    `None` (faixa cinzenta ou leitura vazia) e perda. Quando as duas concordam e
    a serie e nova, ela nasce ali — com o texto da escala 3x como rotulo
    exibido, por regra escrita e nao por acaso de ordem.

    As tres rotas diferem SO na assinatura e no predicado do acordo:

        molde          a assinatura vem dos moldes e e a MESMA para as duas
                       escalas, por construcao (ela sai dos pixels, nao do texto)
        ocr-estrito    a assinatura vem do OCR de cada escala; assinaturas
                       diferentes derrubam a linha
        ocr-igualdade  idem, mas nome COM digito sai da rota de similaridade e
                       exige igualdade exata de string entre as escalas
    """
    catalogo: dict = {}
    lidas = 0
    perdidas = 0
    motivos: dict = {}
    perdas_por_frame: dict = {}

    def perder(motivo: str, leitura) -> None:
        nonlocal perdidas
        perdidas += 1
        motivos[motivo] = motivos.get(motivo, 0) + 1
        perdas_por_frame[leitura.frame] = perdas_por_frame.get(leitura.frame, 0) + 1

    for leitura in sorted(leituras, key=lambda le: le.origem):
        if rota == "ocr-igualdade" and (
            assinatura_por_ocr(leitura.texto2x) or assinatura_por_ocr(leitura.texto3x)
        ):
            if leitura.texto2x != leitura.texto3x:
                perder("igualdade estrita recusou (nome com digito)", leitura)
                continue
            assinatura = assinatura_por_ocr(leitura.texto3x)
            chave = chave_da_serie(leitura.texto3x, assinatura)
            if chave is None:
                perder("leitura vazia", leitura)
                continue
            catalogo.setdefault(
                chave, EntradaDoCatalogo(chave, leitura.texto3x, assinatura)
            )
            lidas += 1
            continue

        if rota == "molde":
            dados = (moldados or {}).get(leitura.origem)
            if dados is None:
                perder("fora das paginas distintas medidas", leitura)
                continue
            if dados["assinatura"] is None:
                perder("o molde nao segmentou a linha", leitura)
                continue
            duas = tres = dados["assinatura"]
        else:
            duas = assinatura_por_ocr(leitura.texto2x)
            tres = assinatura_por_ocr(leitura.texto3x)

        # A 3x MANDA, e a 2x confere. A ordem importa e nao e arbitraria: com as
        # duas resolvidas contra o MESMO catalogo antigo, uma primeira aparicao
        # em que as escalas discordam em um caractere criaria DUAS series novas
        # de chaves diferentes e a linha morreria — nenhum item novo cujas duas
        # leituras nao fossem identicas entraria jamais no catalogo, e a faixa
        # de ruido que D-02 existe para absorver nunca seria exercitada. Aqui a
        # 3x cria a serie PROVISORIA (ela e a que da o nome exibido, por regra
        # escrita) e a 2x tem de cair NELA. Se nao cair, a provisoria e
        # descartada e nada e gravado.
        entradas = list(catalogo.values())
        b = agrupar(leitura.texto3x, tres, entradas, corte, piso)
        if b.chave is None:
            perder("faixa cinzenta ou leitura vazia (3x)", leitura)
            continue
        provisoria = None
        if b.nova:
            provisoria = EntradaDoCatalogo(b.chave, leitura.texto3x, tres)
            entradas = entradas + [provisoria]
        a = agrupar(leitura.texto2x, duas, entradas, corte, piso)
        if a.chave is None:
            perder("faixa cinzenta ou leitura vazia (2x)", leitura)
            continue
        if a.chave != b.chave:
            perder("as duas escalas cairam em series diferentes", leitura)
            continue
        lidas += 1
        if provisoria is not None:
            catalogo[b.chave] = provisoria

    total = lidas + perdidas
    return {
        "rota": rota,
        "lidas": lidas,
        "perdidas": perdidas,
        "total": total,
        "taxa": (lidas / total) if total else 0.0,
        "series": len(catalogo),
        "catalogo": catalogo,
        "motivos": motivos,
        "perdas_por_frame": perdas_por_frame,
    }


# As confusoes que o motor de OCR REALMENTE comete neste material, medidas nas
# 8 gravacoes: `I`/`1` em `Lv. I` x `Lv. 1`, e a caixa da inicial em
# `D-grade Crystal` x `D-grade crystal`. As demais (`O`/`0`, `S`/`5`, `B`/`8`)
# entram porque sao as mesmas que `manutencao._normalizar_digitos` ja lista, e
# porque a normalizacao so pode ERRAR PARA MAIS aqui: ela junta series que
# talvez nao fossem a mesma, o que INFLA a contagem de duplicatas de cada rota.
# Uma contagem que erra para mais nao favorece a rota que ela julga.
CONFUSOES_DO_OCR = {"i": "1", "l": "1", "|": "1", "o": "0", "s": "5", "b": "8"}


def _grafia_normalizada(nome: str) -> str:
    """O nome reduzido ao que sobra quando as confusoes de OCR sao desfeitas."""
    return "".join(
        CONFUSOES_DO_OCR.get(caractere, caractere) for caractere in nome.lower()
    )


def series_duplicadas_projetadas(catalogo: dict, corte: float) -> list:
    """As series que sao o MESMO item com o digito (ou a letra) lido de dois jeitos.

    O CRITERIO NAO E SIMILARIDADE, E ISSO E CORRECAO DE UMA PRIMEIRA TENTATIVA.
    A primeira versao chamava de duplicata todo par de nomes acima do corte
    ignorando a trava — e ela acusava `+2 Agathion Alpha Hunter Sealed` e
    `+4 Agathion ...` como duplicata um do outro. Eles sao itens DIFERENTES: a
    trava de digitos existe justamente para separa-los. Contar isso como lixo
    puniria todas as rotas por acertarem.

    O criterio que ficou: duas series sao a mesma quando as grafias, desfeitas
    as confusoes conhecidas do motor (`I`/`1`, `O`/`0`, `S`/`5`, `B`/`8`, `l`/`1`
    e a caixa), viram a MESMA string. `Lv. I` e `Lv. 1` colapsam; `Lv. 1` e
    `Lv. 3` nao. E exatamente "o mesmo item lido de dois jeitos", e nada alem.

    Devolve os grupos com mais de uma serie, com as grafias lado a lado.
    """
    grupos: dict = {}
    for entrada in sorted(catalogo.values(), key=lambda e: e.chave):
        grupos.setdefault(_grafia_normalizada(entrada.nome), []).append(entrada)
    return [g for g in grupos.values() if len(g) > 1]


# ---------------------------------------------------------------------------
# Gravacao e relatorio
# ---------------------------------------------------------------------------


def gravar(caminho: Path, corte: float, piso: float) -> None:
    """Load-mutate-save. Nunca montar uma `Calibracao` do zero.

    Montar do zero apagaria os 13 moldes de glifo e as 3 ancoras — o modo de
    falha REAL da janela quebrada 13, que custou uma recuperacao a mao em
    2026-08-30. E `os.replace` grava o arquivo INTEIRO, entao esta gravacao nao
    pode cruzar com a do 02-02: por isso este plano depende dele.
    """
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados["mercado_corte_de_similaridade"] = corte
    dados["mercado_piso_de_similaridade"] = piso
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=caminho.parent, delete=False, suffix=".tmp"
    ) as saida:
        json.dump(dados, saida, indent=2, ensure_ascii=False)
        provisorio = Path(saida.name)
    os.replace(provisorio, caminho)


def _quantis(valores) -> str:
    if not valores:
        return "(populacao vazia)"
    a = np.asarray(valores, dtype=np.float64)
    return (
        f"n={a.size:>7}  min={a.min():.4f}  p1={np.percentile(a, 1):.4f}  "
        f"p5={np.percentile(a, 5):.4f}  mediana={np.median(a):.4f}  "
        f"p95={np.percentile(a, 95):.4f}  max={a.max():.4f}"
    )


def _histograma_ascii(valores, largura: int = 44) -> list:
    """Dez baldes de 0,0 a 1,0. O olho pega sobreposicao mais rapido que o p95."""
    if not valores:
        return ["    (populacao vazia)"]
    baldes = [0] * 10
    for v in valores:
        baldes[min(9, max(0, int(v * 10)))] += 1
    topo = max(baldes) or 1
    linhas = []
    for i, quantos in enumerate(baldes):
        barra = "#" * int(round(largura * quantos / topo))
        linhas.append(f"    [{i / 10:.1f},{(i + 1) / 10:.1f})  {quantos:>7}  {barra}")
    return linhas


def main(argv=None) -> int:
    analisador = argparse.ArgumentParser(
        description=(
            "Mede o corte e o piso de similaridade do agrupamento de nome, e a "
            "fonte da assinatura de digitos, sobre as 8 gravacoes do censo."
        )
    )
    analisador.add_argument("--gravacoes", default=str(RAIZ / "recordings"))
    analisador.add_argument("--calibracao", default=str(RAIZ / "calibration.json"))
    analisador.add_argument("--gravar", action="store_true")
    analisador.add_argument(
        "--despejar-leituras",
        default=None,
        help="grava as leituras 2x/3x num JSON, para virar fixture versionada",
    )
    opcoes = analisador.parse_args(argv)

    gravacoes = Path(opcoes.gravacoes).resolve()
    calibracao = Path(opcoes.calibracao).resolve()

    print("=" * 78)
    print("MEDICAO DO AGRUPAMENTO DE NOME - 02-03 Task 1")
    print("=" * 78)
    print("gravacoes : " + str(gravacoes))
    print("calibracao: " + str(calibracao))

    if not gravacoes.is_dir():
        print("ERRO: " + str(gravacoes) + " nao e um diretorio.")
        return 2

    faltando = [n for n in GRAVACOES_DO_CENSO if not (gravacoes / n).is_dir()]
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
    if cal.mercado_coluna_do_nome is None:
        print("")
        print(
            "ERRO: mercado_coluna_do_nome esta ausente no calibration.json. "
            "Rode calibrar-mercado.bat."
        )
        return 4
    if (cal.mercado_grade or {}).get("layout") != "negociacao":
        print("")
        print(
            "ERRO: mercado_grade.layout nao e 'negociacao'. LEIT-01 e LEIT-05 "
            "nao tem objeto na aba Adena. Recalibre sobre a grade de negociacao."
        )
        return 4
    for chave, ferramenta in (
        ("mercado_limiar_de_leitura_de_glifo", "medir_leitura_de_glifo"),
        ("mercado_margem_de_leitura_de_glifo", "medir_leitura_de_glifo"),
        ("mercado_sonda_do_fundo", "medir_oclusao"),
        ("mercado_limiar_de_dispersao_do_fundo", "medir_oclusao"),
    ):
        if getattr(cal, chave) is None:
            print("")
            print(
                f"ERRO: {chave} esta ausente no calibration.json. Rode antes "
                f"tools/{ferramenta}.py --gravar (02-02) — sem a sonda de "
                "oclusao a varredura mediria sobre linha coberta, e sem o piso "
                "de leitura nao ha rota `molde` para comparar."
            )
            return 4
    if not ocr.disponivel():
        print("")
        print("ERRO: o motor de OCR nao respondeu neste interpretador.")
        print("  " + str(ocr.motivo_indisponivel()))
        print("  Rode pelo .venv: .venv/Scripts/python.exe tools/...")
        return 5

    print("")
    print("Varrendo... (coluna do nome, 2x e 3x, linha a linha - isto demora)")
    resultado = varrer(gravacoes, cal)
    leituras = resultado.leituras
    print(f"  linhas com nome lido pelas DUAS escalas: {len(leituras)}")
    print(f"  linhas sem texto nenhum (grade vazia)  : {resultado.vazias}")
    print(f"  linhas em que so UMA escala leu        : {resultado.meia_leitura}")
    print(
        f"  linhas COBERTAS, descartadas pela sonda : {resultado.cobertas}  "
        f"(dispersao > {cal.mercado_limiar_de_dispersao_do_fundo:.6f}, 02-02)"
    )
    print(f"  linhas em que a sonda nao pode medir   : {resultado.sem_sonda}")
    for origem, dispersao, texto in resultado.exemplos_de_coberta:
        print(f"      {origem}  dispersao {dispersao:.4f}  3x={texto!r}")
    for nome in GRAVACOES_DO_CENSO:
        print(
            f"  {nome:<42} {resultado.abertos_por_gravacao.get(nome, 0):>4} "
            "frames com painel aberto"
        )
    if not leituras:
        print("ERRO: nenhum nome lido. Nada a medir.")
        return 6

    if opcoes.despejar_leituras:
        destino = Path(opcoes.despejar_leituras).resolve()
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(
            json.dumps(
                [
                    {
                        "gravacao": le.gravacao,
                        "arquivo": le.arquivo,
                        "linha": le.linha,
                        "texto2x": le.texto2x,
                        "texto3x": le.texto3x,
                    }
                    for le in sorted(leituras, key=lambda le: le.origem)
                ],
                indent=1,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"  leituras despejadas em {destino}")

    # -----------------------------------------------------------------
    # RELATORIO 1 - o histograma e a proposta
    # -----------------------------------------------------------------
    print("")
    print("=" * 78)
    print("RELATORIO 1 - HISTOGRAMA DA SIMILARIDADE E A PROPOSTA DE CORTE/PISO")
    print("=" * 78)
    consenso = vocabulario_de_consenso(leituras)
    print("")
    print(
        f"  VOCABULARIO DE CONSENSO: {len(consenso)} nomes distintos que as DUAS "
        "escalas leram identicos em alguma linha limpa. E a nocao de leitura "
        "confiavel usada dos DOIS lados da medicao."
    )
    diagnosticos = {}
    for com_trava in (False, True):
        rotulo = "COM a trava de digitos" if com_trava else "SEM a trava de digitos"
        agrupam, por_metodo, sem_consenso = pares_que_precisam_agrupar(
            leituras, com_trava, consenso
        )
        separam, indecidiveis = pares_que_precisam_separar(leituras, com_trava)
        diag = propor_corte_e_piso(agrupam, separam)
        diagnosticos[com_trava] = (
            diag,
            agrupam,
            separam,
            por_metodo,
            indecidiveis,
            sem_consenso,
        )
        print("")
        print(f"  --- {rotulo} ---")
        iguais = sum(1 for par in agrupam if par.a == par.b)
        print("  PRECISAM AGRUPAR (as duas escalas, mesma linha, ate 2 caracteres)")
        print("    " + _quantis([par.score for par in agrupam]))
        print(
            f"    dos {len(agrupam)}, {iguais} sao texto IDENTICO (score 1,0) e "
            f"{len(agrupam) - iguais} sao discordancia real"
        )
        print(
            f"    FORA da populacao, por discordarem em MAIS de "
            f"{DISTANCIA_MAXIMA_DE_RUIDO} caracteres: {len(por_metodo)} linhas "
            "(erro de METODO — a linha cai por desenho, nao por limiar)"
        )
        print(
            f"    FORA da populacao, por nenhum dos dois lados ser nome de "
            f"consenso: {len(sem_consenso)} pares (duas leituras FALHADAS nao "
            "ensinam nada ao corte)"
        )
        for linha in _histograma_ascii([par.score for par in agrupam]):
            print(linha)
        print(
            "  PRECISAM SEPARAR (linhas diferentes do mesmo frame, texto "
            f"diferente em MAIS de {DISTANCIA_MAXIMA_DE_RUIDO} caracteres)"
        )
        print("    " + _quantis([par.score for par in separam]))
        for linha in _histograma_ascii([par.score for par in separam]):
            print(linha)
        print(
            f"  INDECIDIVEIS (linhas diferentes, ate {DISTANCIA_MAXIMA_DE_RUIDO} "
            f"caracteres de diferenca): {len(indecidiveis)}"
        )
        print("    " + _quantis([par.score for par in indecidiveis]))
        print(
            "    Nao entram em populacao nenhuma: e a MESMA faixa de diferenca "
            "que dentro de uma linha se chama ruido de OCR."
        )
        for par in sorted(set(indecidiveis), key=lambda p: -p.score)[:4]:
            print(f"      {par.score:.4f}  {par.a!r} x {par.b!r}  ({par.origem})")
        if diag["corte"] is None:
            print("    SEM PROPOSTA: " + str(diag.get("motivo")))
            continue
        print(
            f"    min(agrupar)={diag['corte']:.6f}   "
            f"max(separar)={diag['pior_separar']:.6f}   folga={diag['folga']:+.6f}"
        )
        if diag["sobrepostos"]:
            print(
                f"    SOBREPOSICAO: {len(diag['sobrepostos'])} pares que PRECISAM "
                "SEPARAR estao no nivel do pior par que precisa agrupar."
            )
            for par in diag["sobrepostos"][:8]:
                print(f"      {par.score:.4f}  {par.origem}")
                print(f"        a={par.a!r}")
                print(f"        b={par.b!r}")

    diag, agrupam, separam, por_metodo, indecidiveis, sem_consenso = diagnosticos[True]
    if diag["corte"] is None or diag["sobrepostos"]:
        print("")
        print(
            "NENHUM CORTE PROPOSTO com a trava ligada: um corte dentro da "
            "sobreposicao decidiria coisas opostas com o mesmo numero, que e "
            "exatamente o defeito que derrubou o WRatio com corte 88. PARANDO."
        )
        return 7
    corte = float(diag["corte"])
    piso = float(diag["piso"])
    print("")
    print(f"  CORTE PROPOSTO {corte:.6f}   (empate no corte AGRUPA)")
    print(f"  PISO  PROPOSTO {piso:.6f}   (empate no piso DESCARTA)")
    print(f"  FAIXA CINZENTA [{piso:.6f}, {corte:.6f})")
    print(
        f"  VAO ENTRE AS POPULACOES {diag['folga']:.6f}  "
        f"(max(separar)={diag['pior_separar']:.6f}); o piso e o MEIO dele, pela "
        "mesma construcao de `mercado_limiar_de_glifo`"
    )
    pior = min(agrupam, key=lambda par: par.score)
    print("  O pior par de 'precisa agrupar', que o corte tem de aceitar:")
    print(f"    {pior.score:.4f}  {pior.origem}")
    print(f"      2x={pior.a!r}")
    print(f"      3x={pior.b!r}")
    melhor = max(separam, key=lambda par: par.score)
    print("  O melhor par de 'precisa separar', que tem de ficar sob o piso:")
    print(f"    {melhor.score:.4f}  {melhor.origem}")
    print(f"      a={melhor.a!r}")
    print(f"      b={melhor.b!r}")

    # A conferencia dura: nenhuma das duas populacoes pode estar do lado errado
    # do numero proposto. Sem ela a proposta seria uma afirmacao sobre extremos,
    # e nao sobre as populacoes inteiras.
    agrupam_errados = [par for par in agrupam if par.score < corte]
    separam_errados = [par for par in separam if par.score >= piso]
    print("")
    print("  CONFERENCIA DA PROPOSTA (as populacoes INTEIRAS, nao so os extremos):")
    print(
        f"    'precisa agrupar' abaixo do corte: {len(agrupam_errados)} de "
        f"{len(agrupam)}"
    )
    print(
        f"    'precisa separar' no piso ou acima: {len(separam_errados)} de "
        f"{len(separam)}"
    )
    if agrupam_errados or separam_errados:
        print("    A PROPOSTA NAO SE SUSTENTA SOBRE A PROPRIA POPULACAO. PARANDO.")
        return 9

    print("")
    print(
        "  O QUE O CORTE PROPOSTO FARIA COM OS PARES SEM CONSENSO (o custo da "
        "exclusao):"
    )
    fora = [par for par in sem_consenso if par.score < corte]
    print(
        f"    dos {len(sem_consenso)} excluidos, {len(sem_consenso) - len(fora)} "
        f"agrupariam mesmo assim e {len(fora)} nao"
    )
    for par in sorted(set(fora), key=lambda p: p.score)[:6]:
        print(f"      {par.score:.4f}  {par.a!r} x {par.b!r}  ({par.origem})")
    print("")
    print("  O QUE O CORTE PROPOSTO FARIA COM OS INDECIDIVEIS (o custo da exclusao):")
    agrupados = [par for par in indecidiveis if par.score >= corte]
    cinzentos = [par for par in indecidiveis if piso <= par.score < corte]
    novos = [par for par in indecidiveis if par.score < piso]
    print(
        f"    agrupariam: {len(agrupados)}   cairiam na faixa cinzenta: "
        f"{len(cinzentos)}   virariam serie nova: {len(novos)}"
    )

    print("")
    print(
        "  AS FUSOES QUE O CORTE PROPOSTO PRODUZ, TODAS, SOBRE O VOCABULARIO "
        "CONFIRMADO"
    )
    print(
        "  (pares de nomes que as duas escalas confirmaram, com a MESMA "
        "assinatura de digito e similaridade >= corte: eles cairiam na mesma "
        "serie. Nem toda fusao e erro — 'D-grade Crystal' e 'D-grade crystal' "
        "sao o mesmo item. Quem sabe distinguir e quem le, e por isso a lista "
        "sai INTEIRA.)"
    )
    fusoes = fusoes_no_corte(consenso, corte)
    print(f"    {len(fusoes)} pares, de {len(consenso)} nomes confirmados")
    for score, a, b in fusoes:
        print(f"      {score:.4f}  {a!r}")
        print(f"              x {b!r}")

    # -----------------------------------------------------------------
    # RELATORIO 2 - o censo do conflito entre as escalas
    # -----------------------------------------------------------------
    print("")
    print("=" * 78)
    print("RELATORIO 2 - CENSO DO CONFLITO ENTRE AS ESCALAS (D-02 x D-03)")
    print("=" * 78)
    censo = censo_do_conflito(leituras)
    print(
        f"  linhas em que as assinaturas de digito DIFEREM entre 2x e 3x: "
        f"{censo['n_conflitos']} de {censo['n_linhas']} "
        f"({100.0 * censo['n_conflitos'] / max(censo['n_linhas'], 1):.2f}%)"
    )
    print("  Cada uma dessas linhas MORRE na rota `ocr-estrito`.")
    piores = sorted(censo["por_frame"].items(), key=lambda item: -len(item[1]))[:8]
    if piores:
        print("")
        print("  OS FRAMES MAIS ATINGIDOS:")
        for (gravacao, arquivo), linhas in piores:
            total = censo["linhas_por_frame"].get((gravacao, arquivo), 0)
            print(f"    {gravacao[9:]}/{arquivo}: {len(linhas)} de {total} linhas")
            for numero, a, b, t2, t3 in linhas[:2]:
                print(f"      linha {numero}: {a!r} x {b!r}")
                print(f"        2x={t2!r}")
                print(f"        3x={t3!r}")

    # -----------------------------------------------------------------
    # RELATORIO 3 - a fonte da assinatura (A8)
    # -----------------------------------------------------------------
    print("")
    print("=" * 78)
    print("RELATORIO 3 - A FONTE DA ASSINATURA, MEDIDA (suposicao A8)")
    print("=" * 78)
    paginas = paginas_distintas(leituras)
    print(
        f"  medindo molde sobre {len(paginas)} PAGINAS DISTINTAS "
        f"(de {len(censo['linhas_por_frame'])} frames com painel aberto): a "
        "pagina parada se repete e contar a repeticao mediria o tempo, nao o "
        "material"
    )
    moldados = medir_moldes_nas_paginas(gravacoes, cal, leituras, paginas)
    print(f"  linhas com leitura de molde: {len(moldados)}")
    fonte = medir_a_fonte_da_assinatura(gravacoes, cal, leituras, moldados)
    if fonte.get("erro"):
        print("  ERRO: " + fonte["erro"])
        return 8
    print("")
    print(f"  frame do gabarito: {fonte['frame']}")
    print(
        f"  piso {fonte['piso']:.6f} e margem {fonte['margem']:.6f} — os do "
        "02-02, medidos sobre 55.342 glifos das colunas de NUMERO"
    )
    print("")
    print("  linha gabarito  molde[+N]  molde[N]  molde[LINHA INTEIRA]   OCR")
    for item in fonte["linhas"]:
        print(
            f"    {item['linha']:>2}  {item['esperada']!r:>8}  "
            f"{str(item['molde_prefixo']):>9}  {str(item['molde_digito']):>8}  "
            f"{str(item['molde_linha']):>20}   {item['ocr']!r}"
        )
    com_encanto = sum(1 for e in GABARITO_DE_ENCANTO if e)
    print("")
    print(
        f"  MOLDE[N] (digito ISOLADO, com a posicao dada de fora) contra o "
        f"gabarito, {com_encanto} linhas com encanto:"
    )
    print(
        f"    {fonte['molde_acerto']} acerto, {fonte['molde_descarte']} descarte, "
        f"{fonte['molde_erro']} erro"
    )
    print(
        "  MOLDE[LINHA INTEIRA] (a regra que a rota usaria em PRODUCAO) contra "
        "as 10 linhas:"
    )
    print(f"    {fonte['linha_acerto']} acerto, {fonte['linha_erro']} erro")
    print(
        f"  OCR contra o gabarito, {com_encanto} linhas com encanto: "
        f"{fonte['ocr_acerto']} acerto, {fonte['ocr_erro']} erro"
    )
    print("")
    print("  OS RUNS QUE PASSARAM NO PISO, LINHA A LINHA (indice/rotulo/score):")
    for item in fonte["linhas"]:
        aprovados = ", ".join(
            f"#{i}->{r} {s:.3f}" for i, r, s, _ in item["aprovados"]
        )
        print(f"    linha {item['linha']}: {aprovados or '(nenhum)'}")

    print("")
    print("  EXISTE UM PISO QUE SEPARA DIGITO DE LETRA NA COLUNA DO NOME?")
    print(
        "  (VERDADEIRO = o run 1 de um nome que comeca com `+N `, cuja posicao a"
    )
    print("   propria grafia entrega. FALSO = todo run aprovado num nome em que")
    print("   NENHUMA escala viu digito — se nao ha digito, todo digito e falso.)")
    verdadeiros = [linha[0] for linha in fonte["verdadeiros"]]
    falsos = [linha[0] for linha in fonte["falsos"]]
    print("    VERDADEIRO  " + _quantis(verdadeiros))
    print("    FALSO       " + _quantis(falsos))
    if verdadeiros and falsos:
        folga_do_piso = min(verdadeiros) - max(falsos)
        print(
            f"    min(VERDADEIRO)={min(verdadeiros):.4f}  "
            f"max(FALSO)={max(falsos):.4f}  folga={folga_do_piso:+.4f}"
        )
        if folga_do_piso > 0:
            print(
                "    HA VAO. Um piso proprio da coluna do NOME separaria as duas "
                "populacoes — mas ele seria um numero NOVO, e o piso que este "
                "projeto tem hoje (0,4698, medido sobre colunas de NUMERO) NAO "
                "separa: ver a coluna molde[LINHA INTEIRA] acima."
            )
        else:
            print(
                "    NAO HA VAO. Nenhum piso escalar separa digito de letra na "
                "coluna do nome com os 13 moldes atuais — eles nao tem classe de "
                "rejeicao, entao toda letra e forcada sobre o digito mais parecido."
            )
    print("    OS 8 PIORES FALSOS POSITIVOS (o que a rota `molde` inventaria):")
    for score, distancia, rotulo, indice, texto, _ in fonte["falsos"][:8]:
        print(
            f"      {score:.4f}/{distancia:.4f}  run #{indice} lido como "
            f"{rotulo!r} em {texto!r}"
        )

    print("")
    print("  O CASO `Lv. N` — o digito no MEIO do nome, e nao no prefixo:")
    if not fonte["nivel"]:
        print("    (nenhuma linha com `Lv.` e digito na varredura)")
    for item in fonte["nivel"]:
        print(f"    {item['origem']}")
        print(f"      2x={item['texto2x']!r}  ->  assinatura {item['ocr2x']!r}")
        print(f"      3x={item['texto3x']!r}  ->  assinatura {item['ocr3x']!r}")
        print(
            f"      molde[ultimo run]={item['molde_ultimo_run']!r}  "
            f"molde[LINHA INTEIRA]={item['molde_linha']!r}"
        )

    # -----------------------------------------------------------------
    # RELATORIO 4 - o rendimento das TRES ROTAS
    # -----------------------------------------------------------------
    print("")
    print("=" * 78)
    print("RELATORIO 4 - RENDIMENTO DAS TRES ROTAS ('li N, perdi M')")
    print("=" * 78)
    das_paginas = [le for le in leituras if le.frame in set(paginas)]
    print(
        f"  As TRES rotas sao comparadas sobre as MESMAS {len(das_paginas)} "
        f"linhas das {len(paginas)} paginas distintas — a rota `molde` custa 13 "
        "casamentos por run e nao roda sobre as repeticoes, e comparar rotas "
        "sobre populacoes diferentes nao compara nada."
    )
    rendimentos = {}
    for rota in ROTAS:
        rendimentos[rota] = rendimento_de_uma_rota(
            rota, das_paginas, corte, piso, moldados
        )
    for rota in ROTAS:
        r = rendimentos[rota]
        print("")
        print(
            f"  {rota:<14} li {r['lidas']}, perdi {r['perdidas']}  "
            f"({100.0 * r['taxa']:.2f}% de {r['total']})   "
            f"series criadas: {r['series']}"
        )
        for motivo, quantos in sorted(r["motivos"].items(), key=lambda kv: -kv[1]):
            print(f"      {quantos:>6}  {motivo}")

    print("")
    print("  AS DUAS ROTAS DE OCR SOBRE A VARREDURA INTEIRA (para conferencia):")
    for rota in ("ocr-estrito", "ocr-igualdade"):
        r = rendimento_de_uma_rota(rota, leituras, corte, piso, moldados)
        print(
            f"    {rota:<14} li {r['lidas']}, perdi {r['perdidas']}  "
            f"({100.0 * r['taxa']:.2f}% de {r['total']})   "
            f"series criadas: {r['series']}"
        )
        rendimentos[rota + "/completo"] = r

    print("")
    print("  AS SERIES DUPLICADAS QUE CADA ROTA DEIXA NO CATALOGO")
    print(
        "  (criterio: duas grafias que colapsam quando as confusoes conhecidas "
        "do motor sao desfeitas — I/1, O/0, S/5, B/8, l/1 e a caixa. `Lv. I` e "
        "`Lv. 1` colapsam; `Lv. 1` e `Lv. 3` nao, e `+2 X` e `+4 X` tambem nao: "
        "esses sao itens diferentes e conta-los seria punir a rota por acertar)"
    )
    for rotulo in list(ROTAS) + ["ocr-estrito/completo", "ocr-igualdade/completo"]:
        r = rendimentos[rotulo]
        grupos = series_duplicadas_projetadas(r["catalogo"], corte)
        extras = sum(len(g) - 1 for g in grupos)
        print("")
        print(
            f"    {rotulo:<24} {len(grupos)} grupos duplicados, {extras} series a "
            f"mais que o necessario (de {r['series']})"
        )
        for grupo in grupos[:10]:
            print("      grupo:")
            for entrada in grupo:
                print(f"        {entrada.chave:<52} {entrada.nome!r}")

    print("")
    print("O QUE VAI PARA O calibration.json:")
    print(f"  mercado_corte_de_similaridade = {corte:.6f}")
    print(f"  mercado_piso_de_similaridade  = {piso:.6f}")

    if opcoes.gravar:
        gravar(calibracao, corte, piso)
        print("")
        print("GRAVADO em " + str(calibracao) + " (load-mutate-save).")
    else:
        print("")
        print("(nada gravado - rode de novo com --gravar para persistir)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
