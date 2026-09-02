"""O cortador dos moldes de digito da fonte da BARRA. A maquina propoe, o
humano confirma.

O QUE ESTA FERRAMENTA ENTREGA, E O QUE ELA NAO ENTREGA
======================================================
Ela entrega a FERRAMENTA e a suite sintetica que a prende. Quem fecha o LEIT-09
e a RODADA — um humano olhando cada recorte ampliado e dizendo se aquilo e um
`6` ou um `8`. Um conjunto de moldes gerado por codigo de teste seria a falha
aberta do LEIT-09 entrando pela suite, e por isso ele nao sai daqui nem por
conveniencia.

POR QUE ELA EXISTE, E POR QUE O ARGUMENTO DE ALTURA CAIU DUAS VEZES
===================================================================
O M-I mediu a altura da fonte da barra sobre um recorte que continha os icones
de moeda das duas pontas, e `segmentar_glifos` devolve UMA faixa de linhas para
o retangulo inteiro — decisao de projeto dela, documentada —, entao o icone,
mais alto, empurrou o topo e a base. O numero que circulou por uma revisao
inteira desta fase como se fosse a altura da fonte — 17 — **esta refutado**, e a
refutacao e do M-K. A consequencia e o motivo de ela morar no fonte e nao so no
plano: uma
guarda de altura escrita contra a altura contaminada recusaria TODO molde
legitimo desta barra, e o modo de falha seria um cortador que roda, sai com
codigo 0 e nunca corta nada — a pior forma de defeito, porque ela PARECE
funcionar.

**E O NUMERO DA CORRECAO TAMBEM ESTAVA NUMA CONVENCAO, MEDIDO AQUI.** O M-P
pegou a divergencia entre a convencao inclusiva do documento de campo e a
exclusiva do codigo nas LARGURAS de run; ela vale igual para a ALTURA de faixa.
Reconferido sobre as QUATRO fixturas versionadas
(`tests/fixtures/renda/*__barra_direita.png`), nos pisos 180, 185 e 190 —
**doze medicoes, resultado invariavel**:

    faixa bruta      (com os icones dentro)  -> 16
    faixa peneirada  (depois do descarte)    ->  9
    larguras de run  no meio                 -> {1, 4, 5, 6}

Os moldes de digito do mercado sao `altura: 9, largura: 4`, e
`larguras_de_molde` sobre eles da `(1, 4, 6)`. **Entao a GEOMETRIA sozinha nao
separa mais os dois conjuntos** — o argumento do M-I era de altura, e a altura
empatou. O que continua separando esta medido e ja estava escrito no
repositorio: os moldes do mercado foram cortados de texto BRANCO com pico de
brilho 226-230, e a curva tonal decide o desenho tanto quanto a forma — o mesmo
`0` desenhado com pico mais alto vira um anel FECHADO e passa a casar melhor com
o `8` (ver o bloco "A COR DA TINTA" em `mercado_leitura`, com o numero: 0,7242
contra 0,5976, margem 0,1266, falha ABERTA). A barra e semitransparente e e
mascarada num piso proprio; e outra tinta.

**O que muda na pratica: nada, e isso e o desenho funcionando.** Esta ferramenta
nunca compara altura contra um literal — `conferir_a_altura` compara contra a
altura DOMINANTE dos moldes ja gravados. Um numero de fonte errado no fonte
custaria um cortador que nunca corta; um numero errado numa DOCSTRING custa uma
docstring. Por isso a correcao vai escrita onde o numero errado estava, em vez
de o numero ser trocado em silencio.

O argumento ja existia no repositorio com endereco:
`calibrar_mercado._conferir_os_glifos:2469-2473` proibe misturar geometrias
diferentes na mesma matriz porque `_alinhar_por_preenchimento` poe o glifo
pequeno numa caixa grande e o casamento passa a ser dominado por area vazia.

E POR QUE O CAMINHO EXISTE. `segmentar_glifos_no_brilho` segmenta a barra
PERFEITAMENTE na banda de brilho 180-190, justo onde o OCR devolve vazio, com
as larguras batendo com a verdade de campo nas quatro fixturas (M-J, M-O). A
materia-prima esta la; o que falta e o conjunto de moldes.

A COLHEITA E DA BARRA INTEIRA, E NAO DA REGIAO DA ADENA
=======================================================
`--campo` aceita `adena`, `lcoin`, `bonus` e `exp`. A medicao que autoriza isso:
largura de digito confirmada por segmentacao no bonus da Faerlina, no bonus da
Yazalaque e no EXP da Yazalaque — **e uma fonte so na barra inteira** (M-L).

E O BLOQUEIO QUE CAIU, com a razao de ele ter existido. A revisao anterior desta
ferramenta registrou que faltavam o `5` e o `7` e que eles so apareceriam "com o
tempo de farm", e desenhou um plano B de varrer gravacoes antigas de fundo
escuro. **Medido, os dois estao na tela agora**: o `5` no bonus da Faerlina
(`592%`), o `7` na L-Coin da Yazalaque (`9.790`) e no EXP dela (`76.6646%`) — e
os DOIS na adena da Faerlina de 09h30, que a segunda rodada de campo mediu como
`15.134.779` (M-O). O bloqueio era artefato de restringir a colheita a uma
regiao, e cai com o `--campo`. Com ele cai o plano B, e a tentacao de fundir
iluminacoes diferentes perde o motivo — que e a melhor forma de fechar aquele
risco, melhor que qualquer guarda. A proibicao de fundir continua escrita
(`calibrar_mercado.py:3125-3131`) e nao se reabre.

O RECORTE PRECISA TER A FORMA QUE A LEITURA ACEITA -- E ISSO NAO E RESTRICAO,
E O PONTO
=============================================================================
A peneira e UMA so nesta fase: `renda_leitura._glifos_do_numero`, IMPORTADA e
nunca copiada. Ela exige exatamente uma corrida larga em cada PONTA (o icone) e
so larguras de glifo no meio. Um recorte que ela recusa e PULADO com o frame
nomeado — e nao cortado assim mesmo.

Se os moldes fossem cortados de recortes que a leitura RECUSA, eles seriam
cortados de um conjunto de corridas e lidos de outro, e o desalinhamento nao
apareceria como erro: apareceria como PONTUACAO BAIXA, que e a forma de defeito
que alguem "conserta" baixando o piso de leitura — trocando um defeito visivel
por um invisivel. Entao: **enquadre qualquer campo de icone a icone.** Quando
nao der, a ferramenta diz por que, e o campo seguinte e mais barato que uma
segunda peneira.

A RESSALVA DO M-L ENTRA COMO COMPORTAMENTO
==========================================
A regiao do EXP da Yazalaque, em piso alto e recorte largo, cola tudo num run
unico de 141 px porque a BARRA VERDE de progresso entra na mascara. A ferramenta
PULA esse recorte, nomeia a largura, escreve a causa e imprime a sugestao
medida. Ela NAO fatia: 141 px em glifos desta fonte dariam vinte e oito digitos
que nunca estiveram na tela.

O QUE ELA NUNCA FAZ, COM A MEDICAO AO LADO DE CADA PROIBICAO
============================================================
Nao inventa molde vazio para completar o conjunto; nao copia molde da chave de
digitos do mercado (geometria errada, e proibido por escrito em
`calibrar_mercado.py:3125-3131`); e nao grava rotulo sem confirmacao humana. As
tres proibicoes existem contra o MESMO modo de falha, e ele esta medido na
docstring de `conjunto_descreve_numeros`: um conjunto pela metade **falha
ABERTO** — um `8` sem molde de `8` casa com `0` a 0,7826 contra piso 0,4698, com
folga de 0,1628 sobre o segundo colocado, o que significa que **nem a margem
pega**. Um conjunto completado com lixo nao produz meia leitura: produz a
leitura errada com a confianca da certa.

E ELA TRABALHA COM O CONJUNTO INCOMPLETO SEM TRAVAR. Travar a gravacao ate os
onze estarem la jogaria fora moldes ja conferidos por um humano por causa de uma
rodada interrompida ou de um campo ainda nao varrido. Entao: **grava incompleto,
e anuncia por nome** — com a consequencia (a adena vai RECUSAR ate os faltantes
entrarem) e com o conserto NOVO, que e varrer outro campo da barra, e nao
esperar o farm.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .calibracao import Calibracao
from .calibrar import ARQUIVO_CALIBRACAO
from .calibrar_mercado import (
    _pedir_rotulo,
    cobertura_dos_glifos,
    explicar_glifos,
    matriz_de_confusao_de_glifos,
    propor_rotulo,
)
from .frames import Regiao
from .mercado_leitura import (
    conjunto_descreve_numeros,
    limite_de_glifo_unico,
    mascara_de_numero,
    segmentar_glifos_no_brilho,
)
from .mercado_visao import glifos_de_calibracao, glifos_para_calibracao
from .renda_leitura import (
    MOTIVO_DO_RUN_ANORMAL,
    RecusaDeForma,
    _glifos_do_numero,
    recortar,
)

#: Os quatro campos da barra inferior. A colheita e de qualquer um deles, e nao
#: so da adena — e uma fonte so na barra inteira (M-L).
CAMPOS_DA_BARRA = ("adena", "lcoin", "bonus", "exp")

#: Os dois campos que o `01-01` ja calibrou por personagem. Os nomes MENTEM —
#: `barra_esquerda` e o EXP e `barra_direita` e a adena —, e a mentira fica
#: escrita em vez de consertada em silencio: quem renomear renomeia as duas.
#: `lcoin` e `bonus` nao tem retangulo calibrado, e por isso exigem `--recorte`.
SUBCHAVE_CALIBRADA = {"adena": "barra_direita", "exp": "barra_esquerda"}

MOTIVO_DA_ALTURA = "altura-de-faixa"
MOTIVO_DA_FORMA_DO_RECORTE = "forma-do-recorte"

#: ONDE PROCURAR CADA ROTULO NA TELA, medido — e nao adivinhado.
#:
#: Esta tabela e o que transforma "faltam 2" em "faltam 5 e 7, e eles estao no
#: bonus da Faerlina e na L-Coin da Yazalaque". A frase que justifica a forma da
#: saida esta em `cobertura_dos_glifos`: "faltam 3" nao diz onde procurar;
#: "faltam 6, 8, Adena" diz.
#:
#: Fontes: M-J e M-O (adena das quatro fixturas), M-K (L-Coin sem icone) e M-L
#: (bonus e EXP).
ONDE_CADA_ROTULO_FOI_MEDIDO = {
    "0": ("adena da Faerlina 00h45 (13.160.684)", "L-Coin da Faerlina (13.091)"),
    "1": ("adena da Faerlina 00h45 (13.160.684)", "adena da Yazalaque (1.696.020)"),
    "2": ("adena da Yazalaque 00h45 (1.696.020)", "bonus da Faerlina (592%)"),
    "3": ("adena da Faerlina 09h30 (15.134.779)", "L-Coin da Faerlina (13.091)"),
    "4": ("adena da Faerlina 00h45 (13.160.684)", "adena da Faerlina 09h30"),
    "5": ("bonus da Faerlina (592%)", "adena da Faerlina 09h30 (15.134.779)"),
    "6": ("adena da Yazalaque 00h45 (1.696.020)", "bonus da Yazalaque (612%)"),
    "7": (
        "L-Coin da Yazalaque (9.790), sem icone e sem barra verde",
        "adena da Faerlina 09h30 (15.134.779)",
    ),
    "8": ("adena da Faerlina 00h45 (13.160.684)",),
    "9": ("adena da Yazalaque 00h45 (1.696.020)", "L-Coin da Yazalaque (9.790)"),
    ",": ("qualquer valor de milhar da barra",),
}


class RendaNaoCalibravel(RuntimeError):
    """A rodada nao gravou nada, e a mensagem diz por que.

    Mesmo contrato de `MercadoNaoCalibravel`, com o nome do assunto certo: o
    valor da excecao e afirmar ao usuario que o estado ANTERIOR esta intacto.
    """


@dataclass(frozen=True)
class RecorteDaBarra:
    """Um recorte de UM campo, de UM frame, com o piso de brilho DAQUELE campo.

    O piso viaja com o recorte porque nao existe piso unico: a banda em que o
    nivel sai correto e 190-220 e a da adena por glifo e 180-190, e elas nao tem
    intersecao nenhuma (M-E). Um default aqui serviria a um campo e apagaria o
    outro em silencio.
    """

    frame: str
    campo: str
    pixels: np.ndarray
    piso_de_brilho: int


@dataclass(frozen=True)
class Pulo:
    """Um recorte que NAO virou molde, com o frame e o motivo nomeados."""

    frame: str
    motivo: str
    detalhe: str


@dataclass
class RodadaDeCorte:
    """O que UMA rodada produziu. `cortados` e so o corte DESTA rodada.

    A fusao com o conjunto anterior nao acontece aqui, de proposito — mesmo
    desenho de `cortar_glifos`: assim o laco continua testavel sem calibracao
    nenhuma em disco.
    """

    cortados: dict[str, np.ndarray] = field(default_factory=dict)
    pulos: list[Pulo] = field(default_factory=list)
    propostas: list[str | None] = field(default_factory=list)


def conserto_do_run_colado() -> str:
    """A sugestao MEDIDA para o campo colado num run so.

    Ela e uma frase, e nao um limiar: nenhum numero daqui decide coisa alguma no
    codigo. O recorte vertical citado e o que o M-L mediu funcionando.
    """
    return (
        "aperte o recorte VERTICAL ate sobrar so a linha do texto — o M-L mediu "
        "`1366:1386` funcionando no EXP da Yazalaque — ou suba o piso de "
        "brilho. E a saida barata: o bonus nao tem barra verde e sozinho ja "
        "entrega o `5`, e a L-Coin da Yazalaque entrega o `7` sem icone e sem "
        "barra verde."
    )


def limite_de_arranque(runs) -> int | None:
    """O limite de glifo unico da PRIMEIRA rodada, quando nao ha molde nenhum.

    POR QUE ELE PRECISA EXISTIR. `limite_de_glifo_unico({})` devolve `None` — e
    esta certo, porque sem molde nao ha geometria gravada. Mas a primeira rodada
    tambem precisa fatiar, e e justamente ela que faz o primeiro molde nascer.
    Sem um limite de arranque a ferramenta nunca sairia do zero: um cortador que
    exige moldes para cortar moldes.

    DE ONDE ELE VEM, E ELE E ANUNCIADO. Medido nas quatro fixturas: os icones
    sao as duas corridas das PONTAS, e sao as mais largas do recorte. Entao o
    arranque e a maior largura que NAO esta numa ponta. Nas quatro fixturas isso
    da 6, 4, 6 e 6 — e em todas as quatro o descarte posicional sai igual.

    E O PONTO CEGO DELE VAI ESCRITO, porque ele e real: num recorte que tenha um
    icone NO MEIO (o caso do M-N), o arranque adotaria a largura DAQUELE icone e
    a peneira o aceitaria como digito. Isso nao passa em silencio — o rotulo
    daquele recorte vai para o olho humano ampliado, e o que ele veria e lixo.
    Assim que o primeiro molde existir, o limite passa a sair dos moldes e este
    caminho nunca mais e usado.
    """
    corridas = list(runs or [])
    if len(corridas) < 3:
        return None
    do_meio = [int(fim) - int(inicio) for inicio, fim in corridas[1:-1]]
    if not do_meio:
        return None
    return max(do_meio)


def altura_dominante(moldes: dict[str, np.ndarray]) -> int | None:
    """A altura que MANDA no conjunto ja gravado. `None` sem moldes."""
    alturas = [int(m.shape[0]) for m in moldes.values() if getattr(m, "ndim", 0) == 2]
    if not alturas:
        return None
    return max(set(alturas), key=alturas.count)


def conferir_a_altura(
    faixa: tuple[int, int], moldes: dict[str, np.ndarray]
) -> str | None:
    """A faixa PENEIRADA bate com a altura dominante dos moldes? `None` se sim.

    A ORDEM E A GUARDA INTEIRA, E ELA VAI ESCRITA. A altura comparada e a que a
    peneira devolveu, ja DEPOIS do descarte dos icones. Medir a altura sobre a
    faixa bruta e reproduzir o M-I por dentro da ferramenta que existe para nao
    reproduzi-lo: foi o icone dentro do recorte que contaminou a faixa unica de
    uma fonte de altura 10 (M-K, refutando M-I).

    A ALTURA NAO VIRA CHAVE DO `calibration.json`. Ela sai dos proprios moldes,
    pela regra que a docstring de `limite_de_glifo_unico` ja escreve: gravar uma
    copia de algo derivado dos moldes cria duas verdades sobre uma so geometria,
    e a copia envelhece na recalibracao seguinte.

    Sem molde nenhum nao ha com que comparar, e a guarda se cala — inventar uma
    altura de referencia aqui seria fixar a geometria da fonte por adivinhacao.
    """
    dominante = altura_dominante(moldes)
    if dominante is None:
        return None
    altura = int(faixa[1]) - int(faixa[0])
    if altura == dominante:
        return None
    return (
        f"a faixa peneirada tem altura {altura} e os moldes ja gravados tem "
        f"altura dominante {dominante}. Todo glifo de um conjunto sai da MESMA "
        f"faixa de linhas compartilhada: uma altura diferente foi cortada de "
        f"outro lugar da tela, ou de outro campo. Nada foi gravado deste recorte"
    )


def glifos_do_recorte(
    pixels: np.ndarray, *, piso_de_brilho: int, moldes: dict[str, np.ndarray]
):
    """`(mascara, GlifosDoNumero)` ou `RecusaDeForma`. A peneira e IMPORTADA.

    O limite sai de `limite_de_glifo_unico(moldes)` quando ha moldes, e de
    `limite_de_arranque(runs)` quando nao ha. Nenhuma geometria desta fonte
    entra aqui como constante.
    """
    mascara = mascara_de_numero(pixels, int(piso_de_brilho))
    _faixa_bruta, runs = segmentar_glifos_no_brilho(pixels, int(piso_de_brilho))
    limite = limite_de_glifo_unico(moldes) or limite_de_arranque(runs)
    peneirado = _glifos_do_numero(mascara, _faixa_bruta, runs, limite=limite)
    if isinstance(peneirado, RecusaDeForma):
        return peneirado
    return mascara, peneirado


def cobertura_da_barra(presentes) -> tuple[list[str], list[str]]:
    """Os ONZE rotulos desta fonte: quais existem e quais faltam, NOMEADOS.

    Ela DELEGA a `cobertura_dos_glifos` e depois tira os rotulos de mais de um
    caractere. A delegacao e o que faz a disciplina ser a mesma dos dois lados —
    faltante sai por nome, nunca por contagem. O filtro existe porque as duas
    PALAVRAS de sufixo (`Adena`, `XM Coin`) sao da GRADE do mercado: elas nao
    existem nesta barra, e conta-las como faltantes mandaria o usuario procurar
    para sempre por algo que nao esta na tela dele.
    """
    existem, faltam = cobertura_dos_glifos(presentes)
    return (
        [rotulo for rotulo in existem if len(rotulo) == 1],
        [rotulo for rotulo in faltam if len(rotulo) == 1],
    )


def onde_procurar(faltam) -> list[str]:
    """Uma linha por rotulo faltante, dizendo em que CAMPO ele foi medido.

    O conserto MUDOU com o M-L, e a mudanca vai na mensagem: ele deixou de ser
    "esperar o farm produzir o digito" e passou a ser "varrer outro campo da
    barra". Um conserto que manda esperar nao e um conserto.
    """
    linhas = []
    for rotulo in faltam:
        onde = ONDE_CADA_ROTULO_FOI_MEDIDO.get(rotulo)
        if not onde:
            linhas.append(f"  {rotulo!r}: nao foi medido em nenhum campo ainda")
            continue
        linhas.append(f"  {rotulo!r}: {'; '.join(onde)}")
    return linhas


def anunciar_a_cobertura(moldes: dict[str, np.ndarray]) -> list[str]:
    """O anuncio do conjunto, e ele sai EM VOZ ALTA quando esta incompleto.

    Um conjunto incompleto e um desfecho LEGITIMO — e o LEIT-09 funcionando —,
    mas ele nao pode ser silencioso: o usuario descobriria no meio do farm que a
    adena nao le. Entao a ferramenta roda `conjunto_descreve_numeros` sobre o
    que gravou e, quando ela devolve `False`, escreve a consequencia e o
    conserto.
    """
    existem, faltam = cobertura_da_barra(set(moldes))
    linhas = [f"  ja tenho ({len(existem)}): {', '.join(existem) or '-'}"]
    if conjunto_descreve_numeros(moldes):
        linhas.append("  conjunto COMPLETO: os onze rotulos da barra estao la.")
        return linhas
    linhas.append(f"  ainda FALTA ({len(faltam)}): {', '.join(faltam)}")
    linhas.append("")
    linhas.append(
        "  ENQUANTO FALTAR ROTULO, A ADENA VAI **RECUSAR** EM VEZ DE SER LIDA."
    )
    linhas.append(
        "  Isso nao e um defeito: e a peneira funcionando. Meio conjunto falha "
        "ABERTO"
    )
    linhas.append(
        "  — um `8` sem molde de `8` casa com `0` a 0,7826 contra piso 0,4698, "
        "e a"
    )
    linhas.append("  folga de 0,1628 significa que nem a margem pega.")
    linhas.append("")
    linhas.append("  ONDE PROCURAR o que falta (medido, e nao esperar o farm):")
    linhas.extend(onde_procurar(faltam))
    return linhas


def _mostrar_o_recorte(titulo: str, pixels: np.ndarray) -> None:
    """A ampliacao que torna a confirmacao humana possivel.

    Sem ela o ENTER seria as cegas, e um rotulo confirmado errado nao produz
    meia leitura: produz a leitura errada com a confianca da certa.
    """
    ampliado = cv2.resize(
        pixels, None, fx=8, fy=8, interpolation=cv2.INTER_NEAREST
    )
    cv2.imshow(titulo, ampliado)
    cv2.waitKey(1)


def propor_e_confirmar(
    recortes,
    ja_gravados: dict[str, np.ndarray],
    *,
    ler=None,
    mostrar=None,
    so_propor: bool = False,
) -> RodadaDeCorte:
    """O laco central: um recorte por vez, a maquina propoe e o humano confirma.

    E o `cortar_glifos` do mercado com um CAMPO no lugar de uma tabela, e as
    decisoes dele valem aqui pelas mesmas razoes.

    TUDO OU NADA, e a razao esta escrita na propria `propor_rotulo`: basta um
    run que nao passe no piso E na margem para a proposta cair inteira, porque
    uma proposta parcial (`6?,00`) convida ao ENTER distraido justamente sobre a
    parte que a ferramenta NAO sabia.

    NA PRIMEIRA RODADA NAO HA MOLDE E NAO HA PROPOSTA, e a ferramenta DIZ isso
    em vez de propor vazio: o humano digita o numero inteiro, que e o unico
    jeito de o primeiro molde nascer certo.

    `ler` e `mostrar` sao resolvidos AQUI, e nao no valor padrao da assinatura:
    um `ler=input` no cabecalho amarraria o `input` que existia no momento em
    que o modulo foi importado, e quem o substituisse depois seria ignorado
    calado.
    """
    ler = ler or input
    mostrar = mostrar or _mostrar_o_recorte
    rodada = RodadaDeCorte()

    for item in recortes:
        moldes = {**ja_gravados, **rodada.cortados}
        peneirado = glifos_do_recorte(
            item.pixels, piso_de_brilho=item.piso_de_brilho, moldes=moldes
        )
        if isinstance(peneirado, RecusaDeForma):
            detalhe = peneirado.detalhe
            if peneirado.motivo == MOTIVO_DO_RUN_ANORMAL:
                detalhe = f"{detalhe}. {conserto_do_run_colado()}"
            rodada.pulos.append(
                Pulo(frame=item.frame, motivo=peneirado.motivo, detalhe=detalhe)
            )
            print(f"  PULADO {item.frame} ({item.campo}): {detalhe}")
            continue

        mascara, glifos = peneirado
        problema = conferir_a_altura(glifos.faixa, moldes)
        if problema is not None:
            rodada.pulos.append(
                Pulo(frame=item.frame, motivo=MOTIVO_DA_ALTURA, detalhe=problema)
            )
            print(f"  PULADO {item.frame} ({item.campo}): {problema}")
            continue

        tinta = (mascara * 255).astype(np.uint8)
        proposta = propor_rotulo(tinta, glifos.faixa, list(glifos.runs), moldes)
        rodada.propostas.append(proposta)

        if so_propor:
            dito = proposta or "nenhuma (ainda nao ha molde que sustente uma)"
            print(
                f"  {item.frame} ({item.campo}): {len(glifos.runs)} glifo(s), "
                f"proposta = {dito}"
            )
            continue

        ampliar = tinta[
            glifos.faixa[0] : glifos.faixa[1],
            glifos.runs[0][0] : glifos.runs[-1][1],
        ]
        mostrar(f"{item.frame} :: {item.campo}", ampliar)
        print(f"  {item.frame} ({item.campo}): vi {len(glifos.runs)} glifo(s).")
        rotulo = _pedir_rotulo(ler, len(glifos.runs), proposta)
        if rotulo is None:
            continue

        topo, base = glifos.faixa
        for caractere, (inicio, fim) in zip(rotulo, glifos.runs):
            rodada.cortados[caractere] = tinta[topo:base, inicio:fim].copy()
        print(f"  ok: {rotulo}")

    return rodada


def conferir_os_moldes(fundidos: dict[str, np.ndarray]):
    """A matriz de confusao ANTES de gravar. Nao separaveis: nao grava.

    Molde de `_conferir_os_glifos`, sem a metade das PALAVRAS: esta barra nao
    tem sufixo de moeda, e uma matriz que misturasse geometrias diferentes
    mediria area vazia em vez de desenho — o argumento literal de
    `_conferir_os_glifos:2469-2473`, que e o mesmo do M-I uma medicao depois.

    A mensagem e a daquela funcao de proposito: ela diz ao usuario que o estado
    anterior esta INTACTO.
    """
    de_um_caractere = {r: m for r, m in fundidos.items() if len(r) == 1}
    resultado = matriz_de_confusao_de_glifos(de_um_caractere)
    for (a, b), score in sorted(resultado.matriz.items(), key=lambda kv: -kv[1]):
        print(f"  {score:.4f}  {a}  x  {b}")
    veredito = explicar_glifos(resultado)
    print(veredito)
    if not resultado.aprovado:
        raise RendaNaoCalibravel(
            "nada foi gravado: os glifos precisam ser separaveis primeiro.\n"
            f"{veredito}"
        )
    return resultado


def gravar_os_moldes(
    moldes: dict[str, np.ndarray],
    *,
    piso_de_leitura: float,
    margem_de_leitura: float,
    caminho: Path | None = None,
) -> dict:
    """Escreve UMA chave de topo, `renda_moldes_da_barra`, e mais nada.

    CARREGA NA PRIMEIRA LINHA UTIL, MUTA SO O QUE E SEU, REEMITE TUDO — molde
    literal de `calibrar.py:1188` e `:1234-1236`. O arquivo e dividido com a
    party, o mercado, o tiat e o calibrador de regioes da renda, e uma escrita
    que montasse o objeto do zero apagaria o trabalho de todos eles.

    ELA NAO SE FUNDE COM A CHAVE DE DIGITOS DO MERCADO, e a proibicao ja esta
    escrita no repositorio com endereco (`calibrar_mercado.py:3125-3131`): a
    chave do mercado e de topo e a NEGOCIACAO depende dela.

    `folga_de_cola` nasce e permanece `null`, que e a guarda FECHADA: sem ela,
    `particionar_run` poderia fatiar um icone em digitos, que e fabricacao de
    numero e nao leitura.
    """
    alvo = caminho or ARQUIVO_CALIBRACAO
    cal = Calibracao.carregar(alvo)
    conjunto = {
        "moldes": glifos_para_calibracao(moldes),
        "piso_de_leitura": float(piso_de_leitura),
        "margem_de_leitura": float(margem_de_leitura),
        "folga_de_cola": None,
    }
    cal.renda_moldes_da_barra = conjunto
    try:
        cal.salvar(alvo)
    except OSError as erro:
        raise RendaNaoCalibravel(
            f"a calibracao NAO foi salva ({erro}). O estado anterior do "
            f"{alvo} continua intacto, e os moldes desta rodada se perderam: "
            f"rode de novo depois de liberar o arquivo"
        ) from erro
    return conjunto


# ---------------------------------------------------------------------------
# A linha de comando
# ---------------------------------------------------------------------------


def _regiao_de_texto(texto: str) -> Regiao:
    """`esquerda,topo,larguraxaltura` -> `Regiao`. Sem default, e por isso.

    Nenhuma coordenada desta barra entra no fonte: quem a conhece e o
    `calibration.json` do usuario, ou o proprio usuario na linha de comando.
    """
    try:
        posicao, tamanho = texto.split(",")[0:2], texto.split(",")[2]
        largura, altura = tamanho.lower().split("x")
        return Regiao(
            esquerda=int(posicao[0]),
            topo=int(posicao[1]),
            largura=int(largura),
            altura=int(altura),
        )
    except (ValueError, IndexError) as erro:
        raise RendaNaoCalibravel(
            f"--recorte {texto!r} nao tem a forma `esquerda,topo,LARGxALT` "
            f"(exemplo: 1540,1358,160x34), e nao e a palavra `inteiro`"
        ) from erro


def recortes_da_pasta(
    pasta: Path,
    *,
    campo: str,
    regiao: Regiao | None,
    piso_de_brilho: int,
    filtro: str | None = None,
) -> list[RecorteDaBarra]:
    """Varre a pasta no idioma de `tools/medir_largura_de_run.py`.

    `regiao=None` significa que os arquivos JA SAO o recorte — e o caminho que
    permite colher das fixturas versionadas em `tests/fixtures/renda/`, sem
    `recordings/`, que e gitignored e nao vem de clone limpo.
    """
    arquivos = sorted(
        p
        for p in pasta.glob("*")
        if p.suffix.lower() in (".png", ".jpg", ".jpeg")
        and (filtro is None or filtro in p.name)
    )
    recortes: list[RecorteDaBarra] = []
    for arquivo in arquivos:
        pixels = cv2.imread(str(arquivo))
        if pixels is None:
            print(f"  PULADO {arquivo.name}: nao consegui ler a imagem")
            continue
        if regiao is not None:
            cortado = recortar(pixels, regiao, campo=campo)
            if not isinstance(cortado, np.ndarray):
                print(f"  PULADO {arquivo.name}: {cortado.detalhe}")
                continue
            pixels = cortado
        recortes.append(
            RecorteDaBarra(
                frame=arquivo.name,
                campo=campo,
                pixels=pixels,
                piso_de_brilho=int(piso_de_brilho),
            )
        )
    return recortes


def _soleiras(cal: Calibracao, args) -> tuple[float, float]:
    """De onde saem `piso_de_leitura` e `margem_de_leitura` — e a honestidade
    sobre isso vai impressa.

    Elas NAO sao derivaveis dos moldes: um piso de separabilidade entre MOLDES
    nao e um piso medido contra glifo de TELA, e a refutacao esta escrita em
    `calibracao.py:440-464` com numero — o limiar do mercado gravado na maquina
    do usuario rejeitaria praticamente todo `8` da tela.

    A ordem de resolucao, da mais especifica para a mais generica:

    1. o que a linha de comando disser;
    2. o que uma rodada anterior ja gravou em `renda_moldes_da_barra`;
    3. o par MEDIDO do mercado, sobre 2.057 glifos de campo DESTE cliente,
       emprestado e ANUNCIADO como emprestimo. Ele descreve a regra de leitura
       (uma correlacao normalizada), e nao a geometria — e a geometria e
       exatamente o que NAO transfere e esta sendo cortada aqui de novo.

    Nao havendo nenhum dos tres, a ferramenta RECUSA e nomeia as duas opcoes.
    Inventar uma soleira seria escolher, por omissao, entre uma leitura que
    recusa tudo e uma que aceita qualquer coisa.
    """
    anterior = (cal.renda_moldes_da_barra or {}) if cal else {}
    piso = args.piso_de_leitura
    margem = args.margem_de_leitura
    if piso is None:
        piso = anterior.get("piso_de_leitura")
    if margem is None:
        margem = anterior.get("margem_de_leitura")
    if piso is None:
        piso = cal.mercado_limiar_de_leitura_de_glifo
        if piso is not None:
            print(
                "  AVISO: `piso_de_leitura` foi EMPRESTADO do par medido do "
                "mercado. Ele descreve a regra de leitura, nao a geometria — "
                "mas ninguem o mediu contra glifo desta barra ainda."
            )
    if margem is None:
        margem = cal.mercado_margem_de_leitura_de_glifo
    if piso is None or margem is None:
        raise RendaNaoCalibravel(
            "nao ha de onde tirar `piso_de_leitura` e `margem_de_leitura`, e "
            "elas sao exigidas SEM default pela leitura de glifo. Passe "
            "--piso-de-leitura e --margem-de-leitura, ou calibre o mercado "
            "antes para haver um par medido a emprestar"
        )
    return float(piso), float(margem)


def _construir_argumentos(argv):
    p = argparse.ArgumentParser(
        prog="calibrar-renda-moldes",
        description=(
            "Corta os moldes de digito da fonte da BARRA. A maquina propoe, "
            "voce confirma. Rode de novo, apontando outro --campo, quando a "
            "saida disser que faltam rotulos."
        ),
    )
    p.add_argument("--gravacoes", required=True, help="pasta com os frames")
    p.add_argument("--campo", required=True, choices=CAMPOS_DA_BARRA)
    p.add_argument("--personagem", default=None)
    p.add_argument(
        "--recorte",
        default=None,
        help="`esquerda,topo,LARGxALT`, ou `inteiro` quando o arquivo ja e o recorte",
    )
    p.add_argument("--piso", type=int, default=None, help="piso de brilho")
    p.add_argument("--filtro", default=None, help="so arquivos com este trecho no nome")
    p.add_argument("--piso-de-leitura", type=float, default=None)
    p.add_argument("--margem-de-leitura", type=float, default=None)
    p.add_argument(
        "--propor",
        action="store_true",
        help="imprime o que proporia, frame a frame, e NAO escreve no disco",
    )
    return p.parse_args(list(argv))


def _resolver_o_recorte(cal: Calibracao, args):
    """Retangulo e piso de brilho, do `calibration.json` ou da linha de comando.

    `adena` e `exp` tem retangulo calibrado por personagem (`01-01`). `lcoin` e
    `bonus` NAO tem, e por isso exigem `--recorte` e `--piso`: inventar um
    retangulo para eles aqui seria plantar coordenada no fonte, que e
    exatamente o que esta fase proibe.
    """
    if args.recorte == "inteiro":
        if args.piso is None:
            raise RendaNaoCalibravel(
                "--recorte inteiro exige --piso: o arquivo ja e o recorte, "
                "entao nao ha calibracao de onde tirar o piso de brilho"
            )
        return None, int(args.piso)
    if args.recorte:
        if args.piso is None:
            raise RendaNaoCalibravel("--recorte exige --piso junto")
        return _regiao_de_texto(args.recorte), int(args.piso)

    subchave = SUBCHAVE_CALIBRADA.get(args.campo)
    if subchave is None:
        raise RendaNaoCalibravel(
            f"o campo `{args.campo}` nao tem retangulo calibrado (so `adena` e "
            f"`exp` tem, pelo 01-01). Passe --recorte e --piso, enquadrando o "
            f"campo de icone a icone — a peneira e a MESMA da leitura, e um "
            f"molde cortado de um recorte que a leitura recusa seria cortado de "
            f"um conjunto de corridas e lido de outro"
        )
    if not args.personagem:
        raise RendaNaoCalibravel(
            "sem --recorte, o retangulo vem da calibracao daquele personagem: "
            "passe --personagem"
        )
    entrada = cal.renda_do_personagem(args.personagem)
    if not entrada or subchave not in entrada:
        raise RendaNaoCalibravel(
            f"o personagem {args.personagem!r} nao tem `{subchave}` calibrado. "
            f"Rode o calibrador de regioes da renda antes, ou passe --recorte"
        )
    bruto = entrada[subchave]
    regiao = Regiao(**bruto["regiao"])
    piso = int(args.piso if args.piso is not None else bruto["piso_de_brilho"])
    return regiao, piso


def main(argv=None) -> int:
    args = _construir_argumentos(sys.argv[1:] if argv is None else argv)
    try:
        cal = Calibracao.carregar(ARQUIVO_CALIBRACAO)
        regiao, piso = _resolver_o_recorte(cal, args)
        pasta = Path(args.gravacoes)
        if not pasta.is_dir():
            raise RendaNaoCalibravel(f"{pasta} nao e uma pasta")

        recortes = recortes_da_pasta(
            pasta,
            campo=args.campo,
            regiao=regiao,
            piso_de_brilho=piso,
            filtro=args.filtro,
        )
        if not recortes:
            raise RendaNaoCalibravel(
                f"nenhuma imagem utilizavel em {pasta} (filtro={args.filtro!r})"
            )

        ja_gravados = glifos_de_calibracao(
            (cal.renda_moldes_da_barra or {}).get("moldes")
        )
        print(f"  {len(recortes)} recorte(s) de `{args.campo}`.")
        for linha in anunciar_a_cobertura(ja_gravados):
            print(linha)

        rodada = propor_e_confirmar(
            recortes, ja_gravados, so_propor=bool(args.propor)
        )

        if args.propor:
            print("")
            print("  --propor: NADA foi escrito no disco.")
            return 0

        if not rodada.cortados:
            print("")
            print("  nenhum rotulo foi confirmado nesta rodada; nada gravado.")
            return 0

        fundidos = {**ja_gravados, **rodada.cortados}
        conferir_os_moldes(fundidos)
        piso_de_leitura, margem_de_leitura = _soleiras(cal, args)
        gravar_os_moldes(
            fundidos,
            piso_de_leitura=piso_de_leitura,
            margem_de_leitura=margem_de_leitura,
        )
        print("")
        print(f"  gravado em {ARQUIVO_CALIBRACAO}")
        for linha in anunciar_a_cobertura(fundidos):
            print(linha)
        return 0
    except RendaNaoCalibravel as erro:
        print("")
        print(f"  {erro}")
        return 1
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":  # pragma: no cover - ponto de entrada
    raise SystemExit(main())
