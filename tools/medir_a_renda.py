"""A BANCADA DA RENDA: a varredura de piso reproduzida por codigo, e o censo dos
quatro desfechos com denominador.

    RELATORIO 1  a VARREDURA DE PISO por regiao e por PERSONAGEM, com a BANDA
                 UTIL, a LARGURA dela, o aviso de banda FRAGIL, e a comparacao
                 lado a lado contra a tabela lida a olho em
                 `01-MEDICOES-DE-CAMPO.md` (M-E)
    RELATORIO 2  o CENSO DOS QUATRO DESFECHOS com denominador explicito, sobre
                 todos os pisos varridos de todos os frames compativeis, mais a
                 quinta contagem: de todas as leituras ACEITAS, quantas estavam
                 ERRADAS contra a verdade de campo

CINCO DAS SEIS PERGUNTAS DESTA BANCADA JA FORAM RESPONDIDAS EM CAMPO
=====================================================================
Nao remeca o que ja esta medido. Em 2026-09-02, com as DUAS instancias vivas, a
madrugada respondeu cinco das seis perguntas que esta ferramenta existia para
responder. Elas estao em
`.planning/workstreams/renda/phases/01-a-leitura-da-barra-pixel-vira-n-mero-ou-recusa/01-MEDICOES-DE-CAMPO.md`,
com nome de achado:

    M-A  as coordenadas do spike sobrevivem ao espaco da janela
    M-B  a Faerlina subiu de nivel entre o spike e a medicao (o caso do REND-03)
    M-D  o cruzamento por IGUALDADE estava errado; a regra e por ABSTENCAO
    M-E  nao existe piso de brilho unico: um por regiao, e por personagem
    M-F  a janela de status fica em lugar DIFERENTE em cada instancia

E o Adendo (M-G a M-J) e a correcao dele (M-K a M-Q) tiraram a ADENA do OCR
(LEIT-09) e derrubaram o retangulo `1500,1360 200x32` em favor de
`1540,1358 160x34`.

A pergunta que SOBROU, e a unica que esta ferramenta mede de novo, e:
**com que frequencia, com denominador, duas leituras de gramatica VALIDA dos
MESMOS pixels produzem inteiros DIFERENTES?** O EXP e o nivel ficaram no OCR sem
plano B -- a regiao do nivel nunca mostrara dez digitos para cortar moldes, e o
EXP e um decimal com sinal de porcentagem --, entao para eles o cruzamento
2x x 3x e a UNICA defesa que cabe dentro de uma leitura unica. Uma guarda que
recusa se justifica por TAXA, e nao por caso.

A GRADE ANDA DE 5 EM 5, E O PASSO DE 10 E UM DEFEITO MEDIDO
=============================================================
Quem for encurtar o tempo da varredura vai olhar o passo primeiro. Entao o
motivo mora ao lado dele: a varredura do M-E andou de 10 em 10, **pulou o 155**,
e concluiu que a Yazalaque nao lia a adena -- quando ela lia. Refeita de 5 em 5
(M-G), `vmin=155` da a leitura certa nas duas escalas e `vmin=150` da `106.020`,
que e gramaticalmente valido e errado por seis ordens de grandeza. Uma
reproducao que herdasse o passo herdaria a conclusao. `conferir_o_passo` recusa
passo maior que 5 por este motivo, com a mensagem dizendo o numero.

A CONVENCAO DA LARGURA DE BANDA E DECLARADA, PORQUE UM PIXEL JA CUSTOU UMA
REFUTACAO A ESTA FASE (M-P)
===========================================================================
A **largura da banda** desta ferramenta e a CONTAGEM DE PISOS DA GRADE que o
cruzamento aceitou, INCLUSIVA nos dois extremos: a banda `180..190` com passo 5
tem largura **3** (180, 185, 190). E a mesma convencao que o campo
`largura_da_banda` do `calibration.json` ja usa. A saida imprime tambem o vao em
NIVEIS DE V (`fim - inicio`, exclusivo) ao lado, porque os dois numeros
descrevem a mesma banda e diferem por definicao.

Ela NAO e a convencao de `larguras_de_molde`, que mede largura de RUN DE GLIFO
por `fim - inicio` (exclusiva) -- e ela nao e comparavel com aquela, porque nao
sao a mesma grandeza. O `01-MEDICOES-DE-CAMPO.md` relata larguras de glifo numa
convencao INCLUSIVA (digito 5/6/7) enquanto o codigo mede na EXCLUSIVA (4/5/6);
foi exatamente um numero sem convencao declarada -- o "17" do M-I -- que
produziu uma refutacao nesta fase. Por isso esta declaracao existe mesmo
tratando de outra grandeza.

O CENSO USA A DECISAO DE PRODUCAO, E NAO UMA PARTICAO PROPRIA
===============================================================
Os quatro desfechos saem de `renda_leitura._cruzar_as_escalas`, importada. Se
esta ferramenta escrevesse a sua propria particao, o censo mediria a FERRAMENTA
e nao o PRODUTO, e no dia em que a regra de producao mudasse os dois
divergiriam em silencio. `desfecho_do_cruzamento` apenas LE o que aquela funcao
devolveu (o tipo, o `motivo`, o `escalas`) -- ela nao decide nada.

A GRAMATICA DO NIVEL E DA ADENA VEM DO MERCADO, E ISSO E DITO EM VOZ ALTA
==========================================================================
`renda_leitura` tem a gramatica do EXP (`decimos_de_milesimo`) e mais nenhuma: a
do nivel nasce no `01-04` e a da adena por glifo no `01-05`. Entao o censo le
esses dois campos com `mercado_leitura.numero_valido` +
`inteiro_de_quantidade` -- que e EXATAMENTE a gramatica que o M-G mediu em campo
quando escreveu "`106.020` e `91` passam em `numero_valido`". Nada foi
reescrito aqui; a seta continua apontando ferramenta -> puro.

O separador entra como CLASSE e nunca como caractere: o jogo escreve milhar com
ponto e o motor devolve virgula (medido nesta arvore, no MESMO recorte da adena
da Faerlina: piso 155 devolve `13,160,684` e piso 160 devolve `13,160.684`).
Quem decide o significado e a CONTAGEM de digitos, nunca o caractere -- a mesma
regra que a gramatica do EXP ja escreve.

O QUE ESTA FERRAMENTA NAO MEDE, E ISSO E DECISAO E NAO ESQUECIMENTO
=====================================================================
Ela **nao** mede o caminho de GLIFO. Ele nasce na onda 2 (`01-03`, o cortador de
moldes) e na onda 3 (`01-04`), e medi-lo aqui obrigaria esta bancada a esperar
por eles. O censo mede o que a producao do OCR faz -- e para a adena isso e um
OBITUARIO COM NUMERO, nao uma medicao de um caminho vivo.

A FERRAMENTA LE `recordings/`; OS TESTES NAO
==============================================
`recordings/` e gitignored e nao vem de clone limpo. Esta ferramenta a le porque
e ferramenta, no precedente de `tools/medir_largura_de_run.py`. Nenhum teste de
`tests/test_medir_a_renda.py` a abre -- a disciplina esta escrita em
`tests/test_mercado_glifos.py:4-8`, e um teste apoiado nela ficaria verde nesta
maquina e amarelo em qualquer outra.

Uso (no checkout PRINCIPAL, onde `recordings/` existe):

    PYTHONPATH=. .venv/Scripts/python.exe tools/medir_a_renda.py
        --relatorio 1 --gravacoes recordings/20260902-004500-renda-duas-instancias
        --personagem Faerlina

    PYTHONPATH=. .venv/Scripts/python.exe tools/medir_a_renda.py
        --relatorio 2 --gravacoes recordings
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from l2scanner.calibracao import REGIOES_DA_RENDA, Calibracao  # noqa: E402
from l2scanner.frames import Regiao  # noqa: E402
from l2scanner.mercado_leitura import (  # noqa: E402
    inteiro_de_quantidade,
    mascara_de_numero,
    numero_valido,
)
from l2scanner.ocr import ler_texto, ler_texto_ampliado  # noqa: E402

# A DECISAO DE PRODUCAO, IMPORTADA E NUNCA REESCRITA.
from l2scanner.renda_leitura import (  # noqa: E402
    MOTIVO_DA_DISCORDANCIA,
    RecusaDaRenda,
    ValorDaRenda,
    _cruzar_as_escalas,
    decimos_de_milesimo,
    recortar,
)

# ---------------------------------------------------------------------------
# A GRADE
# ---------------------------------------------------------------------------
PASSO_DA_GRADE = 5
PISO_MINIMO_DA_GRADE = 100
PISO_MAXIMO_DA_GRADE = 250

# Largura 1 ou 2 nao e margem, e sorte. A barra e SEMITRANSPARENTE e o cenario
# atras dela muda com o lugar de farm: a adena da Faerlina foi medida com banda
# de UM valor no caminho de OCR porque naquele instante o fundo era grama clara
# (M-E). Um piso calibrado numa banda dessas nao sobrevive a uma troca de mapa.
LARGURA_DE_BANDA_FRAGIL = 2
RAZAO_DA_BANDA_FRAGIL = (
    "banda estreita NAO e margem, e sorte: a barra e semitransparente e o "
    "cenario atras dela muda com o lugar de farm, entao a banda muda junto "
    "(M-E). Um piso calibrado aqui pode nao valer no mapa seguinte."
)

# Os apelidos das regioes, porque DOIS DOS TRES NOMES MENTEM: `barra_esquerda` e
# o EXP e `barra_direita` e a ADENA. A mentira esta documentada no
# `calibration.json`, no `renda_leitura` e no LEIA-ME das fixturas; repeti-la
# aqui e mais barato que um leitor achar que "esquerda" e "metade da barra".
APELIDO_DA_REGIAO = {
    "barra_esquerda": "EXP",
    "barra_direita": "ADENA",
    "nivel": "NIVEL",
}

# A ADENA SAIU DO OCR (LEIT-09), e continua no censo por UM motivo: e o unico
# lugar onde o numero que a derrubou ganha denominador. O Adendo tem quatro
# linhas de tabela; o censo tem todos os frames em todos os pisos.
ROTULO_DE_CAMINHO_ABANDONADO = (
    "CAMINHO ABANDONADO (LEIT-09): a adena saiu do OCR e passou a ser lida por "
    "GLIFO. Ela e contada aqui so para dar denominador ao numero que a derrubou."
)

# ---------------------------------------------------------------------------
# A VERDADE DE CAMPO -- lida a olho nos recortes ampliados, com procedencia
# ---------------------------------------------------------------------------
#
# Fonte: `01-MEDICOES-DE-CAMPO.md`, tabela de verdade de campo (2026-09-02,
# 00h45) e a segunda rodada de campo (2026-09-02, 09h30). O EXP viaja em DECIMOS
# DE MILESIMO, que e a unidade interna de `decimos_de_milesimo`.
#
# ONDE NAO HA VERDADE ESCRITA, A CHAVE SIMPLESMENTE NAO EXISTE, e a linha sai
# como "sem verdade de campo" -- NUNCA como errada. Tratar ausencia de gabarito
# como erro inflaria a taxa pelo lado errado, e seria a mesma fabricacao de
# numero que esta fase inteira existe para nao cometer.
VERDADE_DE_CAMPO: dict[tuple[str, str], dict[str, int]] = {
    ("20260902-004500-renda-duas-instancias", "frame_000000_faerlina.png"): {
        "nivel": 67,
        "barra_esquerda": 80012,
        "barra_direita": 13160684,
    },
    ("20260902-004500-renda-duas-instancias", "frame_000001_yazalaque.png"): {
        "nivel": 69,
        "barra_esquerda": 766646,
        "barra_direita": 1696020,
    },
    ("20260902-093000-renda-segundo-cenario", "frame_faerlina.png"): {
        "barra_direita": 15134779,
    },
    ("20260902-093000-renda-segundo-cenario", "frame_yazalaque.png"): {
        "barra_esquerda": 852845,
    },
}

# ---------------------------------------------------------------------------
# A TABELA LIDA A OLHO -- o que esta varredura vai REPRODUZIR ou DERRUBAR
# ---------------------------------------------------------------------------
#
# Achado M-E de `01-MEDICOES-DE-CAMPO.md`: a banda em que a leitura sai
# CORRETA, varrida de 100 a 250 DE 10 EM 10. O passo grosso e parte do dado, e
# nao um detalhe: foi ele que pulou o 155.
#
# Cada entrada e uma tupla de intervalos FECHADOS, porque a adena da Yazalaque
# nao e contigua no M-E (110 e 150, com vazio entre eles).
#
# UMA REPRODUCAO QUE SO PODE CONCORDAR NAO PROVA NADA. Esta tabela existe para
# ser comparada e, se for o caso, DERRUBADA -- e o veredicto sai escrito nos
# dois casos, com as duas leituras lado a lado.
BANDA_DE_CAMPO: dict[tuple[str, str], tuple[tuple[int, int], ...]] = {
    ("Faerlina", "barra_esquerda"): ((150, 170),),
    ("Faerlina", "barra_direita"): ((150, 150),),
    ("Faerlina", "nivel"): ((190, 220),),
    ("Yazalaque", "barra_esquerda"): ((130, 170),),
    ("Yazalaque", "barra_direita"): ((110, 110), (150, 150)),
    ("Yazalaque", "nivel"): ((170, 210),),
}

# Os quatro desfechos, com os nomes que o relatorio imprime. Eles sao os quatro
# que `_cruzar_as_escalas` distingue, e nao uma particao nova.
ACEITA_DUAS_ESCALAS = "ACEITA-2-ESCALAS"
ACEITA_UMA_ESCALA = "ACEITA-1-ESCALA"
RECUSA_ILEGIVEL = "RECUSA-ILEGIVEL"
RECUSA_DISCORDANCIA = "RECUSA-DISCORDANCIA"
OS_QUATRO_DESFECHOS = (
    ACEITA_DUAS_ESCALAS,
    ACEITA_UMA_ESCALA,
    RECUSA_ILEGIVEL,
    RECUSA_DISCORDANCIA,
)

# Um token numerico: digitos, com separadores POSSIVEIS no meio. A ancora dos
# dois lados e a mesma disciplina de `_EXP_DA_BARRA` -- sem ela a expressao casa
# DENTRO de um numero maior, e o OCR desta arvore cola numero vizinho na frente
# o tempo todo (`76 EXP 80012% 592%` e leitura real de campo).
_TOKEN_NUMERICO = re.compile(
    r"(?<![\d.,])\d[\d.,]*\d(?![\d.,])|(?<![\d.,])\d(?![\d.,])"
)


def conferir_o_passo(passo: int) -> int:
    """O passo da grade. MAIOR QUE 5 E RECUSADO, e a recusa diz o numero.

    Este nao e zelo abstrato: o M-E varreu de 10 em 10, PULOU O 155, e concluiu
    que a Yazalaque nao lia a adena. Medido depois de 5 em 5 (M-G), `vmin=150`
    devolve `106.020` -- gramaticalmente valido e errado por seis ordens de
    grandeza -- e `vmin=155` devolve `1.696.020`, que e a verdade de campo, nas
    duas escalas. A conclusao inteira do M-E sobre aquele campo veio do passo.

    Quem for encurtar o tempo da varredura vai olhar o passo primeiro, e vai
    encontrar esta recusa antes de encontrar a conclusao errada.
    """
    if passo < 1:
        raise ValueError(f"o passo da grade tem de ser positivo, veio {passo}")
    if passo > PASSO_DA_GRADE:
        raise ValueError(
            f"passo {passo} RECUSADO. A grade anda de {PASSO_DA_GRADE} em "
            f"{PASSO_DA_GRADE}, e o motivo esta medido: a varredura de 10 em 10 "
            f"do M-E PULOU o piso 155 e concluiu que a Yazalaque nao lia a "
            f"adena. No piso 150 a leitura sai 106.020 (valida e errada por "
            f"seis ordens de grandeza); no 155 ela sai 1.696.020, que e a "
            f"verdade de campo. Um passo grosso nao erra para o lado seguro."
        )
    return passo


def grade_de_pisos(minimo: int, maximo: int, passo: int) -> tuple[int, ...]:
    """Os pisos varridos, INCLUSIVOS nos dois extremos.

    Inclusiva porque a banda util e reportada pelos EXTREMOS dela, e um extremo
    que a grade nunca visitou nao pode ser nomeado.
    """
    conferir_o_passo(passo)
    if maximo < minimo:
        raise ValueError(f"a grade vai de {minimo} a {maximo}, que esta invertida")
    return tuple(range(minimo, maximo + 1, passo))


def personagem_do_arquivo(nome_do_arquivo: str, personagens) -> str | None:
    """De quem e esta tela, pelo NOME do arquivo. `None` quando nao da para saber.

    A PENEIRA BARATA VEM PRIMEIRO, E ISSO E DESENHO. O lote de `recordings/` tem
    dezenas de gravacoes de mercado e de party cujos frames nao tem personagem
    no nome; decidir por NOME antes de abrir o PNG evita ler centenas de imagens
    de 4 MB so para descobrir que nao servem.

    E `None` NAO e "use o vizinho". Medido (M-F), a janela de status da Faerlina
    poe o nivel em `246,736` e a da Yazalaque em `236,750`: ler uma com o
    retangulo da outra nao devolve campo vazio que alguem note -- devolve `349`
    ou `112`, numeros plausiveis desenhados ao lado. Um frame sem dono e PULADO
    e CONTADO, nunca adivinhado.
    """
    minusculo = nome_do_arquivo.lower()
    achados = [nome for nome in personagens if nome and nome.lower() in minusculo]
    if len(achados) != 1:
        # ZERO e nao ha dono. MAIS DE UM e ambiguidade, e ela pula em vez de
        # escolher -- a escolha seria pela ordem das chaves do arquivo de
        # calibracao, e essa ordem nao e informacao sobre a tela.
        return None
    return achados[0]


def frame_tem_a_forma(forma, geometria: dict | None) -> bool:
    """A janela carimbada bate com este frame?

    Um recorte parcial no meio do lote nao levanta erro: ele produz um recorte
    fora do lugar, e `recortar` recusaria -- mas em silencio, uma linha de
    recusa por vez, silenciando metade do censo sem que a contagem diga.
    Conferir aqui transforma isso num numero impresso.

    Sem carimbo nao ha o que conferir, e a resposta e `True`: o carimbo e
    opcional no esquema, e recusar por ausencia dele desligaria a bancada em
    toda calibracao antiga.
    """
    if not geometria:
        return True
    largura = geometria.get("largura")
    altura = geometria.get("altura")
    if largura is None or altura is None:
        return True
    return bool(forma is not None and forma[0] == altura and forma[1] == largura)


def candidatos_inteiros(texto: str | None) -> set[int]:
    """Todos os inteiros DISTINTOS que a gramatica de numero aceita neste texto.

    O separador entra como CLASSE e nunca como caractere. Medido nesta arvore,
    no MESMO recorte da adena da Faerlina: piso 155 devolve `13,160,684` e piso
    160 devolve `13,160.684`. O jogo escreve o milhar com ponto, o motor devolve
    virgula, e as duas grafias descrevem a mesma tela. Quem decide o significado
    e a CONTAGEM de digitos depois do separador -- que e o que `numero_valido`
    confere --, nunca o caractere.
    """
    if not texto:
        return set()
    achados = set()
    for token in _TOKEN_NUMERICO.findall(texto):
        normalizado = token.replace(".", ",").strip(",")
        if not normalizado or not numero_valido(normalizado):
            continue
        valor = inteiro_de_quantidade(normalizado)
        if valor is not None:
            achados.add(valor)
    return achados


def inteiro_do_texto(texto: str | None) -> int | None:
    """O inteiro deste texto, ou `None`. AMBIGUIDADE RECUSA, e nao escolhe.

    E a mesma disciplina de `decimos_de_milesimo`: zero candidatos e "nao ha o
    que ler"; MAIS DE UM e ambiguidade, e pegar o primeiro seria uma decisao
    tomada pela ordem em que o motor devolveu as palavras -- e essa ordem nao e
    informacao sobre a tela.

    ISTO PODE DIVERGIR DO M-G, E A DIVERGENCIA VAI MEDIDA EM VEZ DE ESCONDIDA:
    aquele achado leu com um retangulo que ja foi refutado (`1500,1360 200x32`,
    ver M-N/M-O/M-Q), e o relatorio conta quantas leituras foram recusadas por
    ambiguidade justamente para que o confundidor fique visivel na saida.
    """
    candidatos = candidatos_inteiros(texto)
    if len(candidatos) != 1:
        return None
    return candidatos.pop()


def valor_do_campo(texto: str | None, regiao: str) -> int | None:
    """A gramatica DAQUELE campo: o EXP pela de producao, os outros pela do mercado.

    O EXP usa `renda_leitura.decimos_de_milesimo`, que e a gramatica que a
    producao usa hoje. O nivel e a adena usam a do mercado, e o motivo esta no
    charter deste arquivo: `renda_leitura` ainda NAO tem gramatica para eles --
    a do nivel nasce no `01-04` e a da adena por glifo no `01-05`. A do mercado
    e exatamente a que o M-G mediu em campo quando escreveu que `106.020` e `91`
    passam em `numero_valido`.
    """
    if regiao == "barra_esquerda":
        return decimos_de_milesimo(texto)
    return inteiro_do_texto(texto)


def desfecho_do_cruzamento(resultado) -> str:
    """QUAL dos quatro desfechos a decisao de producao produziu. Ela nao decide.

    Esta funcao LE `_cruzar_as_escalas`: o tipo devolvido, o `motivo` da recusa
    e o `escalas` do valor. Ela nao reimplementa a regra, e essa e a propriedade
    inteira desta bancada -- uma segunda particao mediria a FERRAMENTA e nao o
    PRODUTO, e no dia em que a regra de producao mudasse as duas divergiriam sem
    que ninguem visse.

    `campo-vazio` e `gramatica` sao motivos DISTINTOS na producao, porque os
    consertos sao distintos, e o relatorio imprime os dois no cru. No censo dos
    quatro desfechos eles somam em ZERO VALIDAS, que e o desfecho que o plano
    nomeia como recusa por ilegibilidade.
    """
    if isinstance(resultado, ValorDaRenda):
        return ACEITA_DUAS_ESCALAS if resultado.escalas >= 2 else ACEITA_UMA_ESCALA
    if isinstance(resultado, RecusaDaRenda):
        if resultado.motivo == MOTIVO_DA_DISCORDANCIA:
            return RECUSA_DISCORDANCIA
        return RECUSA_ILEGIVEL
    raise TypeError(
        f"_cruzar_as_escalas devolveu {type(resultado).__name__}, que nao e "
        f"ValorDaRenda nem RecusaDaRenda. A bancada NAO adivinha desfecho."
    )


@dataclass(frozen=True)
class Leitura:
    """Um piso varrido de uma regiao de um frame. Ela CARREGA A PROCEDENCIA.

    Sem gravacao, frame e personagem em cada linha, o relatorio vira folclore em
    duas semanas -- que e exatamente o que o modulo de OCR deste projeto mantem
    no fonte, marcado como REFUTADO, para nao virar folclore de novo.
    """

    gravacao: str
    frame: str
    personagem: str
    regiao: str
    piso: int
    texto_2x: str | None
    texto_3x: str | None
    valor_2x: int | None
    valor_3x: int | None
    desfecho: str
    valor: int | None
    verdade: int | None
    candidatos_2x: int
    candidatos_3x: int

    @property
    def aceita(self) -> bool:
        return self.desfecho in (ACEITA_DUAS_ESCALAS, ACEITA_UMA_ESCALA)

    @property
    def certa(self) -> bool | None:
        """`None` sem verdade de campo escrita. NUNCA `False` por ausencia."""
        if not self.aceita or self.verdade is None:
            return None
        return self.valor == self.verdade

    @property
    def escala_que_sustentou(self) -> str | None:
        if self.desfecho != ACEITA_UMA_ESCALA:
            return None
        return "2x" if self.valor_2x is not None else "3x"


@dataclass(frozen=True)
class Banda:
    """A banda util e a LARGURA dela, na convencao declarada no topo do arquivo.

    `largura` conta PISOS DA GRADE, inclusiva nos dois extremos: `180..190` com
    passo 5 vale 3. `vao_em_v` e `fim - inicio`, exclusivo, em niveis de V. Os
    dois descrevem a mesma banda e diferem por definicao -- imprimir os dois e
    o que impede a proxima refutacao por um pixel (M-P).
    """

    inicio: int | None
    fim: int | None
    largura: int
    fragil: bool

    @property
    def vao_em_v(self) -> int:
        if self.inicio is None or self.fim is None:
            return 0
        return self.fim - self.inicio


def marcar_fragil(largura: int) -> bool:
    """Largura 1 ou 2 e FRAGIL. Largura 0 nao e fragil -- e ausencia de banda."""
    return 1 <= largura <= LARGURA_DE_BANDA_FRAGIL


def resumir_a_banda(pisos_bons, passo: int = PASSO_DA_GRADE) -> Banda:
    """A MAIOR corrida CONTIGUA de pisos, e a largura dela em pisos da grade.

    CONTIGUA, e nao "todos os pisos que deram certo": um piso solto no meio de
    uma regiao morta e ruido, e reporta-lo como se fosse banda daria ao
    calibrador a impressao de margem onde nao ha nenhuma. Empate de comprimento
    fica com a PRIMEIRA corrida, a de menor brilho -- nao ha razao para preferir
    uma; o que importa e que a regra esteja escrita e seja estavel.
    """
    ordenados = sorted({int(piso) for piso in pisos_bons})
    if not ordenados:
        return Banda(inicio=None, fim=None, largura=0, fragil=False)

    melhor = (ordenados[0], ordenados[0])
    inicio = ordenados[0]
    anterior = ordenados[0]
    for piso in ordenados[1:]:
        if piso - anterior == passo:
            anterior = piso
        else:
            if (anterior - inicio) > (melhor[1] - melhor[0]):
                melhor = (inicio, anterior)
            inicio = piso
            anterior = piso
    if (anterior - inicio) > (melhor[1] - melhor[0]):
        melhor = (inicio, anterior)

    largura = (melhor[1] - melhor[0]) // passo + 1
    return Banda(
        inicio=melhor[0],
        fim=melhor[1],
        largura=largura,
        fragil=marcar_fragil(largura),
    )


def banda_bate_com_o_campo(banda: Banda, intervalos) -> str:
    """BATE, DISCORDA ou SEM-TABELA. O veredicto sai escrito nos tres casos.

    Uma reproducao que so pode concordar nao prova nada. Esta compara os
    EXTREMOS contra a tabela lida a olho, e quando eles nao batem quem cai e a
    tabela -- ou esta varredura --, e o relatorio imprime as duas para que quem
    ler decida com os dois numeros na frente.
    """
    if not intervalos:
        return "SEM-TABELA"
    if banda.inicio is None:
        return "DISCORDA"
    return "BATE" if (banda.inicio, banda.fim) in tuple(intervalos) else "DISCORDA"


def contar_o_censo(desfechos) -> dict[str, int]:
    """Os quatro desfechos com DENOMINADOR. `n` sempre sai, mesmo valendo zero.

    Uma contagem sem denominador nao e taxa, e anedota com numero. `n = 0` e um
    resultado -- ele diz que nao houve leitura, o que e diferente de "nao houve
    discordancia".
    """
    contagem = {nome: 0 for nome in OS_QUATRO_DESFECHOS}
    total = 0
    for desfecho in desfechos:
        total += 1
        if desfecho not in contagem:
            raise ValueError(
                f"desfecho {desfecho!r} nao e um dos quatro que "
                f"`_cruzar_as_escalas` distingue: {OS_QUATRO_DESFECHOS}"
            )
        contagem[desfecho] += 1
    contagem["n"] = total
    return contagem


def por_cento(parte: int, total: int) -> str:
    """A fracao como texto. Denominador zero sai `-`, e nunca `0,0%`."""
    if total <= 0:
        return "-"
    return f"{100.0 * parte / total:.1f}%"


# ---------------------------------------------------------------------------
# A PARTE QUE TOCA DISCO E OCR
# ---------------------------------------------------------------------------


@dataclass
class Candidato:
    gravacao: str
    frame: str
    personagem: str
    caminho: Path


@dataclass
class Pulados:
    """Quantos frames o lote perdeu, e POR QUE. Contados, e nunca calados."""

    sem_personagem: int = 0
    sem_calibracao: int = 0
    forma_incompativel: int = 0
    ilegivel_em_disco: int = 0

    @property
    def total(self) -> int:
        return (
            self.sem_personagem
            + self.sem_calibracao
            + self.forma_incompativel
            + self.ilegivel_em_disco
        )

    def imprimir(self) -> None:
        print(f"  frames PULADOS: {self.total}")
        print(f"    sem personagem no nome do arquivo : {self.sem_personagem}")
        print(f"    personagem sem calibracao de renda: {self.sem_calibracao}")
        print(f"    forma != janela carimbada         : {self.forma_incompativel}")
        print(f"    ilegivel em disco                 : {self.ilegivel_em_disco}")


def achar_os_candidatos(raiz: Path, personagens, filtro: str | None):
    """Os PNGs cujo nome nomeia um personagem calibrado. Peneira barata primeiro."""
    pulados = Pulados()
    candidatos = []
    arquivos = sorted(raiz.rglob("*.png")) if raiz.is_dir() else [raiz]
    for caminho in arquivos:
        dono = personagem_do_arquivo(caminho.name, personagens)
        if dono is None:
            pulados.sem_personagem += 1
            continue
        if filtro and dono.lower() != filtro.lower():
            continue
        candidatos.append(
            Candidato(
                gravacao=caminho.parent.name,
                frame=caminho.name,
                personagem=dono,
                caminho=caminho,
            )
        )
    return candidatos, pulados


def regiao_da_entrada(bloco: dict) -> Regiao:
    """O retangulo vem da CALIBRACAO CARREGADA, e nunca de constante embutida."""
    bruto = bloco["regiao"]
    return Regiao(
        esquerda=int(bruto["esquerda"]),
        topo=int(bruto["topo"]),
        largura=int(bruto["largura"]),
        altura=int(bruto["altura"]),
    )


def varrer_um_frame(candidato: Candidato, entrada: dict, pisos, pulados: Pulados):
    """As leituras de um frame: cada regiao, cada piso, as DUAS escalas SEMPRE.

    As duas escalas rodam SEMPRE porque foi medido que elas se REVEZAM (M-D): o
    nivel da Faerlina so sai na 3x, com a 2x devolvendo vazio em toda a banda
    util. Um curto-circuito na escala barata nunca chegaria a perguntar a cara,
    e calaria metade dos campos -- que e o defeito que a producao ja corrigiu, e
    uma bancada com outra ordem mediria outra coisa.
    """
    frame = cv2.imread(str(candidato.caminho))
    if frame is None:
        pulados.ilegivel_em_disco += 1
        return []
    if not frame_tem_a_forma(frame.shape, entrada.get("geometria_da_janela")):
        pulados.forma_incompativel += 1
        return []

    verdades = VERDADE_DE_CAMPO.get((candidato.gravacao, candidato.frame), {})
    leituras = []
    for regiao in REGIOES_DA_RENDA:
        recorte = recortar(
            frame, regiao_da_entrada(entrada[regiao]), campo=f"{regiao}(bancada)"
        )
        if isinstance(recorte, RecusaDaRenda):
            # O retangulo nao cabe nesta janela. E recusa NOMEADA da producao, e
            # ela vale para a regiao inteira -- nao ha piso que a conserte.
            print(
                f"  {candidato.gravacao}/{candidato.frame} "
                f"{candidato.personagem} {regiao}: RECORTE RECUSADO -- "
                f"{recorte.detalhe}"
            )
            continue
        for piso in pisos:
            tinta = (mascara_de_numero(recorte, int(piso)) * 255).astype(np.uint8)
            texto_2x = ler_texto(tinta)
            texto_3x = ler_texto_ampliado(tinta)
            valor_2x = valor_do_campo(texto_2x, regiao)
            valor_3x = valor_do_campo(texto_3x, regiao)
            resultado = _cruzar_as_escalas(
                f"{regiao}@{candidato.personagem}",
                [(texto_2x, valor_2x), (texto_3x, valor_3x)],
            )
            leituras.append(
                Leitura(
                    gravacao=candidato.gravacao,
                    frame=candidato.frame,
                    personagem=candidato.personagem,
                    regiao=regiao,
                    piso=piso,
                    texto_2x=texto_2x,
                    texto_3x=texto_3x,
                    valor_2x=valor_2x,
                    valor_3x=valor_3x,
                    desfecho=desfecho_do_cruzamento(resultado),
                    valor=(
                        resultado.valor
                        if isinstance(resultado, ValorDaRenda)
                        else None
                    ),
                    verdade=verdades.get(regiao),
                    candidatos_2x=len(candidatos_inteiros(texto_2x)),
                    candidatos_3x=len(candidatos_inteiros(texto_3x)),
                )
            )
    return leituras


def varrer(calibracao: Calibracao, raiz: Path, filtro: str | None, pisos):
    """O lote inteiro. O personagem entra em TODA leitura, e nao ha caminho sem ele."""
    personagens = tuple((calibracao.renda_por_personagem or {}).keys())
    candidatos, pulados = achar_os_candidatos(raiz, personagens, filtro)
    leituras = []
    for candidato in candidatos:
        entrada = calibracao.renda_do_personagem(candidato.personagem)
        if entrada is None:
            pulados.sem_calibracao += 1
            continue
        leituras.extend(varrer_um_frame(candidato, entrada, pisos, pulados))
    return leituras, pulados


# ---------------------------------------------------------------------------
# OS DOIS RELATORIOS
# ---------------------------------------------------------------------------


def _cru(texto: str | None) -> str:
    """`>>>o que o OCR viu<<<`. Espaco em branco distingue duas leituras parecidas."""
    return f">>>{texto if texto is not None else ''}<<<"


def imprimir_banda(rotulo: str, banda: Banda, passo: int) -> None:
    if banda.inicio is None:
        print(f"    {rotulo:<14} (nenhum piso da grade)   largura=0")
        return
    print(
        f"    {rotulo:<14} {banda.inicio}..{banda.fim}   "
        f"largura={banda.largura} pisos da grade (passo {passo}, contagem "
        f"INCLUSIVA), vao={banda.vao_em_v} niveis de V   "
        f"primeiro={banda.inicio} ultimo={banda.fim}"
    )
    if banda.fragil:
        print(f"    {'':<14} *** FRAGIL *** {RAZAO_DA_BANDA_FRAGIL}")


def relatorio_1(leituras, pulados: Pulados, passo: int) -> None:
    print("=" * 100)
    print("RELATORIO 1 -- a varredura de piso por REGIAO e por PERSONAGEM")
    print("=" * 100)
    print(
        "A largura da banda conta PISOS DA GRADE, INCLUSIVA nos dois extremos "
        f"(passo {passo}): 180..190 vale 3."
    )
    print(
        "Ela NAO e a convencao de `larguras_de_molde` (largura de run de glifo, "
        "`fim - inicio`, EXCLUSIVA) -- nao sao a mesma grandeza (M-P)."
    )
    print()
    pulados.imprimir()
    print()

    if not leituras:
        print("  NENHUM frame compativel neste lote. Nao ha varredura a fazer.")
        return

    chaves = []
    for leitura in leituras:
        chave = (leitura.personagem, leitura.gravacao, leitura.frame, leitura.regiao)
        if chave not in chaves:
            chaves.append(chave)

    for personagem, gravacao, frame, regiao in chaves:
        do_grupo = [
            leitura
            for leitura in leituras
            if (leitura.personagem, leitura.gravacao, leitura.frame, leitura.regiao)
            == (personagem, gravacao, frame, regiao)
        ]
        print("-" * 100)
        print(
            f"{personagem}  {regiao} ({APELIDO_DA_REGIAO[regiao]})  "
            f"{gravacao}/{frame}"
        )
        if regiao == "barra_direita":
            print(f"  {ROTULO_DE_CAMINHO_ABANDONADO}")
        verdade = do_grupo[0].verdade
        print(
            "  verdade de campo: "
            + (str(verdade) if verdade is not None else "NAO ESCRITA para este frame")
        )
        for leitura in do_grupo:
            veredicto = {True: "CERTO", False: "ERRADO E ACEITO", None: ""}[
                leitura.certa
            ]
            print(
                f"  piso={leitura.piso:<4} "
                f"2x={_cru(leitura.texto_2x):<34} "
                f"3x={_cru(leitura.texto_3x):<34} "
                f"n2x={str(leitura.valor_2x):<10} "
                f"n3x={str(leitura.valor_3x):<10} "
                f"{leitura.desfecho:<20} valor={str(leitura.valor):<10} {veredicto}"
            )

        aceita = resumir_a_banda(
            [leitura.piso for leitura in do_grupo if leitura.aceita], passo
        )
        certos = resumir_a_banda(
            [leitura.piso for leitura in do_grupo if leitura.certa is True], passo
        )
        imprimir_banda("BANDA ACEITA", aceita, passo)
        if verdade is None:
            print(
                "    BANDA CERTA    (sem verdade de campo escrita para este "
                "frame: a banda de ACERTO nao e mensuravel aqui)"
            )
        else:
            imprimir_banda("BANDA CERTA", certos, passo)

        intervalos = BANDA_DE_CAMPO.get((personagem, regiao), ())
        do_campo = (
            ", ".join(f"{a}..{b}" for a, b in intervalos) if intervalos else "(nenhuma)"
        )
        comparavel = certos if verdade is not None else aceita
        veredicto = banda_bate_com_o_campo(comparavel, intervalos)
        print(f"    CAMPO (M-E)    {do_campo}   [lida a olho, varrida de 10 em 10]")
        print(
            f"    VEREDICTO      {veredicto}"
            + (
                ""
                if veredicto == "BATE"
                else "  <- a tabela de campo e esta varredura NAO dizem a mesma "
                "coisa; as duas estao impressas acima, e quem ler decide com os "
                "dois numeros na frente"
            )
        )


def relatorio_2(leituras, pulados: Pulados, passo: int) -> None:
    print("=" * 100)
    print("RELATORIO 2 -- o censo dos QUATRO desfechos, com denominador")
    print("=" * 100)
    print(
        "A unidade do censo e (gravacao, frame, personagem, regiao, PISO). Um "
        "censo restrito ao piso ja calibrado teria denominador 4 e nao mediria "
        "nada -- a pergunta e sobre leituras dos MESMOS pixels, e cada piso da "
        f"grade (passo {passo}) e uma leitura desses mesmos pixels."
    )
    print(
        "Os quatro desfechos saem de `renda_leitura._cruzar_as_escalas`: esta "
        "ferramenta LE a decisao de producao e nao escreve uma segunda."
    )
    print()
    pulados.imprimir()
    print()

    if not leituras:
        print(
            "  NENHUM frame compativel neste lote. Nao ha censo a contar, e "
            "isso nao e um erro: e um lote sem gravacao de renda."
        )
        return

    for regiao in REGIOES_DA_RENDA:
        do_campo = [leitura for leitura in leituras if leitura.regiao == regiao]
        contagem = contar_o_censo([leitura.desfecho for leitura in do_campo])
        n = contagem["n"]
        print("-" * 100)
        print(f"{regiao} ({APELIDO_DA_REGIAO[regiao]})")
        if regiao == "barra_direita":
            print(f"  {ROTULO_DE_CAMINHO_ABANDONADO}")
        for nome in OS_QUATRO_DESFECHOS:
            marca = (
                "  <- O NUMERO QUE ESTE CENSO EXISTE PARA PRODUZIR"
                if nome == RECUSA_DISCORDANCIA
                else ""
            )
            print(
                f"  {nome:<22} {contagem[nome]:>5} / {n:<5} "
                f"({por_cento(contagem[nome], n)}){marca}"
            )

        de_uma_escala = [
            leitura for leitura in do_campo if leitura.desfecho == ACEITA_UMA_ESCALA
        ]
        por_2x = sum(
            1 for leitura in de_uma_escala if leitura.escala_que_sustentou == "2x"
        )
        por_3x = len(de_uma_escala) - por_2x
        print(
            f"  quem sustentou o ACEITA-1-ESCALA: 2x={por_2x} 3x={por_3x} "
            f"(de {len(de_uma_escala)})"
        )

        ambiguas = sum(
            1
            for leitura in do_campo
            if leitura.candidatos_2x > 1 or leitura.candidatos_3x > 1
        )
        print(
            f"  leituras com MAIS DE UM candidato de gramatica (ambiguidade, "
            f"que ABSTEM em vez de escolher): {ambiguas} / {n}"
        )

        com_verdade = [
            leitura
            for leitura in do_campo
            if leitura.aceita and leitura.verdade is not None
        ]
        erradas = [
            leitura for leitura in com_verdade if leitura.valor != leitura.verdade
        ]
        print(
            f"  A QUINTA CONTAGEM -- de todas as leituras ACEITAS com verdade "
            f"de campo escrita, quantas estavam ERRADAS: {len(erradas)} / "
            f"{len(com_verdade)} ({por_cento(len(erradas), len(com_verdade))})"
        )
        for leitura in erradas:
            print(
                f"    ERRADA E ACEITA  {leitura.gravacao}/{leitura.frame} "
                f"{leitura.personagem} piso={leitura.piso} "
                f"leu={leitura.valor} verdade={leitura.verdade} "
                f"({leitura.desfecho})"
            )

        divergentes = [
            leitura for leitura in do_campo if leitura.desfecho == RECUSA_DISCORDANCIA
        ]
        if divergentes:
            print("  OS FRAMES DA DISCORDANCIA (cada um e uma fixtura futura):")
            for leitura in divergentes:
                print(
                    f"    {leitura.gravacao}/{leitura.frame} "
                    f"{leitura.personagem} piso={leitura.piso} "
                    f"2x={leitura.valor_2x} 3x={leitura.valor_3x}  "
                    f"cru 2x={_cru(leitura.texto_2x)} "
                    f"cru 3x={_cru(leitura.texto_3x)}"
                )
        else:
            print(
                "  OS FRAMES DA DISCORDANCIA: nenhum. ZERO tambem e resultado, "
                "e com o denominador acima ele diz que a guarda DORME nesta "
                "arvore -- que e diferente de dizer que ela SOBRA."
            )
    print()
    print(
        "O caminho de GLIFO nao esta medido aqui, e isso e decisao: ele nasce "
        "no `01-03` e no `01-04`, e medi-lo obrigaria esta bancada a esperar "
        "por eles."
    )


def analisar_argumentos(argv=None) -> argparse.Namespace:
    analisador = argparse.ArgumentParser(
        description="A bancada da renda: varredura de piso e censo dos desfechos."
    )
    analisador.add_argument("--relatorio", choices=["1", "2"], required=True)
    analisador.add_argument(
        "--gravacoes",
        required=True,
        help="a pasta de gravacoes, uma gravacao, ou um PNG",
    )
    analisador.add_argument(
        "--calibracao",
        default=str(
            RAIZ / "tests" / "fixtures" / "renda" / "calibracao_de_fixture.json"
        ),
        help=(
            "o calibration.json a usar. O padrao e a fixtura VERSIONADA, que "
            "carrega os retangulos que o M-O produziu: o calibration.json real "
            "e gitignored e nao vem de clone limpo"
        ),
    )
    analisador.add_argument("--personagem", default=None)
    analisador.add_argument("--piso-min", type=int, default=PISO_MINIMO_DA_GRADE)
    analisador.add_argument("--piso-max", type=int, default=PISO_MAXIMO_DA_GRADE)
    analisador.add_argument("--passo", type=int, default=PASSO_DA_GRADE)
    return analisador.parse_args(argv)


def calar_o_log_de_recusa_da_producao() -> None:
    """O `warning` de cada recusa e SILENCIADO nesta bancada, e so nela.

    `renda_leitura._recusar` grava um `warning` por recusa, deliberadamente sem
    limitacao de repeticao, porque o log rotativo e a unica forense pos-farm
    deste projeto. Aqui isso seria RUIDO QUE ESCONDE O RELATORIO: uma varredura
    de 31 pisos x 3 regioes x 4 frames produz centenas de linhas identicas em
    stderr, intercaladas com a saida.

    E NAO SE PERDE INFORMACAO NENHUMA: o relatorio imprime, para CADA piso, os
    dois textos crus entre `>>><<<`, os dois inteiros, o desfecho, o valor e o
    veredicto contra a verdade de campo -- com gravacao, frame e personagem na
    linha. Isso e estritamente mais que o `warning` calado, e com procedencia.
    Silenciar aqui nao muda uma virgula do que a PRODUCAO grava.
    """
    logging.getLogger("l2scanner.renda_leitura").setLevel(logging.ERROR)


def main(argv=None) -> int:
    argumentos = analisar_argumentos(argv)
    calar_o_log_de_recusa_da_producao()
    raiz = Path(argumentos.gravacoes)
    if not raiz.exists():
        print(f"a pasta de gravacoes {raiz} nao existe.")
        return 1

    calibracao = Calibracao.carregar(Path(argumentos.calibracao))
    if not calibracao.renda_por_personagem:
        print(
            f"{argumentos.calibracao} nao tem `renda_por_personagem`. A bancada "
            f"nao adivinha retangulo: eles vem da calibracao carregada."
        )
        return 1

    pisos = grade_de_pisos(argumentos.piso_min, argumentos.piso_max, argumentos.passo)
    print(
        f"calibracao: {argumentos.calibracao}\n"
        f"gravacoes : {raiz}\n"
        f"personagem: {argumentos.personagem or '(todos os calibrados)'}\n"
        f"grade     : {pisos[0]}..{pisos[-1]} de {argumentos.passo} em "
        f"{argumentos.passo} ({len(pisos)} pisos)\n"
    )

    leituras, pulados = varrer(calibracao, raiz, argumentos.personagem, pisos)
    if argumentos.relatorio == "1":
        relatorio_1(leituras, pulados, argumentos.passo)
    else:
        relatorio_2(leituras, pulados, argumentos.passo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
