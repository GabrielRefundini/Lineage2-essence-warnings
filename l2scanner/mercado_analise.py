"""A estatistica honesta sobre as observacoes do World Exchange.

O FATO QUE GOVERNA ESTE MODULO INTEIRO, POR EXTENSO
====================================================
**Uma linha do `observacoes.csv` nao e "o preco as 14:32". E "esta oferta
especifica — este item, este total, esta quantidade — foi vista pela PRIMEIRA
vez as 14:32".**

A chave de dedup da Fase 3 e `(chave_da_serie, total_em_centesimos,
quantidade)`, SEM tempo, de proposito (`mercado_registro.chave_da_observacao`).
As consequencias sao todas do mesmo tipo:

- um anuncio que fica no quadro por uma semana produz UMA linha;
- duas ofertas identicas de vendedores diferentes produzem UMA linha;
- uma oferta que some e volta igual produz UMA linha.

Portanto **NAO existe serie temporal de preco**. Existe uma **sequencia de
OFERTAS DISTINTAS, ordenada pela primeira vez que cada uma apareceu**. Esta fase
NARRA essa limitacao; ela nao a conserta — a serie temporal por dia esta
registrada como ideia adiada no `04-CONTEXT.md`, e conserta-la exigiria mudar a
decisao de dedup da Fase 3.

E por isso que a palavra que qualifica todo `n` daqui e **ofertas distintas**, e
nunca "observacoes ao longo do tempo". Trocar a palavra e repetir o pecado que a
expressao "menor pedido visivel" foi criada para evitar.

ESTE MODULO E PURO
==================
Sem disco, sem relogio do sistema, sem impressao. Entrada: uma lista de
`ObservacaoLida` ja parseada. Saida: dataclasses. E a mesma disciplina que
`mercado_registro.campos_da_observacao` ja segue (D-16, o carimbo entra por
parametro), e e o que permite a suite inteira rodar no Python global, sem WinRT
e sem montar um frame.

`ObservacaoLida` entra so sob `TYPE_CHECKING` e os campos sao lidos POR NOME em
tempo de execucao, no molde literal de `mercado_registro` com `LinhaLida`: e o
que impede este modulo de arrastar a cadeia de visao por conta propria.

OS PISOS DE EVIDENCIA SAO **ESCOLHA**, E NAO MEDICAO
=====================================================
Esta secao existe para que ninguem leia os tres numeros abaixo como resultado de
experimento. **Nenhum piso de evidencia foi medido neste projeto**, e o
`.mercado/observacoes.csv` real ainda nao existe nesta arvore. Os numeros
medidos que existem — 151 paginas lidas contra 189 perdidas no censo, 39 series
distintas, piso de 7 posicoes comparadas — sao todos sobre a **LEITURA**, e nao
servem de substituto: eles dizem quanto da tela conseguimos ler, nao com quantas
ofertas uma mediana deixa de enganar. A medicao que resolveria isso e "quantas
observacoes DISTINTAS por serie o material real produz", e ela nao foi feita.

Cada piso mora numa constante NOMEADA, com a razao por extenso, no molde de
`mercado_pagina.JANELAS_IGUAIS_PARA_CONGELAR`. Quando o usuario rodar `--mercado`
por uma sessao de verdade, ele confere se a mediana aparece para os itens que
quer ver ou se o console cala demais — e ajusta. Cada piso e uma linha.

POR QUE OS PISOS NAO MORAM NO `calibration.json`
=================================================
A doutrina da casa e "nada de constante magica: limiar mora no
`calibration.json`". **Aqui ela nao se aplica, e a tensao fica registrada de
proposito.** Duas razoes:

1. Aquele arquivo e **escrito pela ferramenta de calibracao** e **lido, nunca
   escrito**, pelo modo `--mercado` (decisao travada da Fase 4). Por um piso de
   produto ele nunca passaria a ser escrito por este modo.
2. Estes numeros **nao sao calibracao de pixel** — sao julgamento de produto.
   `HMin` depende do monitor, do gamma e da skin da interface, e por isso e
   dado da maquina. "Com quantas ofertas uma mediana deixa de enganar" nao muda
   de maquina para maquina: muda de opiniao para opiniao.
"""

from __future__ import annotations

import difflib
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from fractions import Fraction
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # pragma: no cover - so o verificador de tipos passa aqui
    from .mercado_registro import ObservacaoLida

__all__ = [
    "ABAIXO_DA_MEDIANA",
    "ACIMA_DA_MEDIANA",
    "SEM_DESTAQUE",
    "Destaque",
    "Evidencia",
    "LinhaDaMargem",
    "MARGEM_AMBIGUA",
    "MARGEM_CALCULADA",
    "MARGEM_SEM_SERIE",
    "MargemDeCraft",
    "MedianaDosUnitarios",
    "MenorPedidoVisivel",
    "ModeloDeMercado",
    "N_MINIMO_PARA_MEDIANA",
    "N_MINIMO_PARA_MENOR",
    "N_MINIMO_PARA_TENDENCIA",
    "PAPEL_COMPONENTE",
    "PAPEL_PRODUTO",
    "RESOLUCAO_AMBIGUA",
    "RESOLUCAO_SEM_CORRESPONDENCIA",
    "RESOLUCAO_UNICA",
    "ResolucaoDeNome",
    "SERIES_NO_TOPO",
    "SerieNoConsole",
    "Tendencia",
    "componente_esta_velho",
    "descrever_a_tendencia",
    "margem_de_craft",
    "mediana_dos_unitarios",
    "menor_pedido_visivel",
    "nome_normalizado",
    "ordenar_para_o_console",
    "recencia_do_preco",
    "resolver_o_nome",
    "tendencia",
    "unitario",
]

# O LIMIAR DE STALENESS DA MARGEM (la embaixo, na secao do ANAL-04) NAO ENTRA
# NESTA LISTA, e a ausencia e deliberada — ao contrario dos pisos de
# evidencia, que entram.
#
# A RAZAO E UM CRITERIO DE VERIFICACAO DO PROPRIO PLANO 04-04. Ele afirma que
# a palavra "escolha" aparece nos 900 caracteres seguintes a PRIMEIRA
# ocorrencia daquele nome no fonte do modulo. Se o nome tambem estivesse
# escrito aqui, a primeira ocorrencia seria esta lista, e a janela de 900
# caracteres cairia no bloco dos pisos de evidencia logo abaixo — que ja dizia
# "ESCOLHA" desde o plano 04-02. O criterio passaria mesmo que a constante
# nascesse muda, e um guarda que passa sem o codigo existir nao e um guarda.
#
# Mantendo o nome fora daqui, a primeira ocorrencia e o proprio sitio da
# definicao e o criterio mede o que ele diz medir. A constante continua
# publica e importavel: `__all__` so governa o `import *`, que este projeto
# nao usa em lugar nenhum.


# ===========================================================================
# OS PISOS DE EVIDENCIA — cada um uma ESCOLHA declarada, nunca uma medicao
# ===========================================================================

# UM MINIMO COM UMA OFERTA SO E UM FATO OBSERVADO, e nao uma estimativa: aquele
# anuncio existiu, naquele total, naquela quantidade, naquele instante. Nao ha
# nada a inferir, entao nao ha piso a exigir.
#
# A HONESTIDADE ESTA NO ROTULO, e o rotulo `n=1` e OBRIGATORIO. Um minimo sem a
# contagem ao lado convida o olho a le-lo como "o preco do item", que e
# precisamente a leitura que ele nao suporta.
#
# ESCOLHA, NAO MEDICAO.
N_MINIMO_PARA_MENOR = 1

# COM CINCO PONTOS O PONTO DE RUPTURA DA MEDIANA E DOIS: duas leituras
# aberrantes nao conseguem move-la para fora do miolo. Com `n=2` a "mediana" e a
# media dos dois — literalmente o numero que engana, que o CONTEXT proibe. Com
# `n=3` uma unica leitura ruim ja e um terco da evidencia.
#
# ESCOLHA, NAO MEDICAO. Ninguem mediu quantas ofertas distintas por serie o
# material real produz; se o console calar demais no uso de verdade, este numero
# desce, e e uma linha.
N_MINIMO_PARA_MEDIANA = 5

# UMA RETA SOBRE TRES PONTOS TEM A MESMA CARA DE UMA SOBRE TREZENTOS, e impedir
# essa confusao e a razao de existir do ANAL-03. Oito e o menor numero em que a
# frase que sai — "caiu tanto por cento ao longo das ultimas oito ofertas
# distintas" — nao parece piada.
#
# ESCOLHA, NAO MEDICAO.
N_MINIMO_PARA_TENDENCIA = 8


# ===========================================================================
# O COMPARAVEL
# ===========================================================================


def unitario(total_em_centesimos: int, quantidade: int) -> Fraction:
    """O unico comparavel entre ofertas de quantidades diferentes. EXATO.

    Comparar `total_em_centesimos` entre ofertas de quantidades diferentes e sem
    sentido: um lote de 100 custa mais que um de 1 sem que nenhum dos dois seja
    "mais caro". O comparavel e o unitario.

    **NUNCA `float`.** O D-02 recusou GUARDAR o unitario porque o que o jogo
    exibe e derivacao ARREDONDADA a duas casas: `40,00` por 48 unidades aparece
    como `0,83`, e `0,83 x 48 = 39,84` — um numero que nunca existiu na tela.
    Derivar na hora de comparar e outra coisa, **desde que nao se arredonde
    antes de comparar**. Divisao em ponto flutuante reintroduziria erro
    exatamente onde o parsing por molde de digito o evitou.

    `Fraction` ordena, compara e entra em `median_low` sem perder um bit. O
    arredondamento acontece SO na formatacao, e o numero exibido carrega a marca
    de derivado.

    QUANTIDADE NAO POSITIVA LEVANTA, com o motivo em texto. O `observacoes.csv`
    e um arquivo que o usuario EDITA A MAO no Sheets e reimporta: uma quantidade
    `0` e entrada possivel, e `Fraction(x, 0)` derrubaria o console inteiro. Uma
    quantidade negativa e pior que um erro — ela inverteria o sinal do unitario
    e faria a oferta ser escolhida como "a mais barata".
    """
    if quantidade <= 0:
        raise ValueError(
            f"quantidade tem de ser positiva para haver unitario, veio {quantidade}"
        )
    return Fraction(total_em_centesimos, quantidade)


def _comparaveis(observacoes: Sequence[ObservacaoLida]) -> list[ObservacaoLida]:
    """As ofertas de que da para derivar unitario. As demais caem, caladas.

    Uma oferta de quantidade nao positiva nao e comparavel com nada, e mante-la
    so daria as duas opcoes ruins: levantar no meio do console, ou deixar um
    unitario de sinal invertido ganhar a disputa do menor. Ela sai da conta e
    sai tambem do `n` — contar como evidencia uma linha que nao entra em conta
    nenhuma seria inflar a evidencia.
    """
    return [obs for obs in observacoes if obs.quantidade > 0]


# ===========================================================================
# A EVIDENCIA QUE VIAJA JUNTO DE TODO RESULTADO
# ===========================================================================


@dataclass(frozen=True)
class Evidencia:
    """Quantas ofertas distintas sustentam este numero, e quantas faltariam.

    ELA VIAJA DENTRO DE TODO RESULTADO, e nao ao lado dele: estatistica sem `n`
    e adivinhacao com cara de numero, e um `n` que quem desenha pode esquecer de
    pedir e um `n` que uma hora nao vai ser exibido.

    ABAIXO DO PISO A RESPOSTA E O QUE FALTA, NUNCA UM NUMERO — e por isso
    `faltam` existe como campo derivado, e nao como conta na cabeca de quem
    exibe. Um `None` mudo obrigaria quem desenha a adivinhar o motivo.
    """

    n: int
    piso: int

    @property
    def suficiente(self) -> bool:
        return self.n >= self.piso

    @property
    def faltam(self) -> int:
        """Quantas ofertas distintas ainda faltam para o piso. Zero se ja da."""
        return max(0, self.piso - self.n)


# ===========================================================================
# O MENOR PEDIDO VISIVEL (ANAL-01)
# ===========================================================================


@dataclass(frozen=True)
class MenorPedidoVisivel:
    """A oferta de menor unitario, com os dois numeros e o carimbo DELA.

    "MENOR PEDIDO VISIVEL", NUNCA "PRECO DE VENDA": o scanner ve OFERTAS, nao
    transacoes. Ninguem comprou por este valor — alguem PEDIU este valor.

    OS DOIS NUMEROS ANDAM JUNTOS. Um total solto e sem significado: `4500` sem a
    quantidade ao lado nao diz se e barato ou caro. Quem exibe recebe os dois e
    o unitario derivado, e nao tem como mostrar um sem o outro.

    O CARIMBO E O DAQUELA OFERTA, NUNCA O DA SERIE. Um minimo de terca-feira ao
    lado de "visto as 14:32" de hoje e a mentira plausivel que este projeto
    inteiro combate — ver `recencia_do_preco`.
    """

    evidencia: Evidencia
    total_em_centesimos: int | None
    quantidade: int | None
    primeira_vez: datetime | None

    @property
    def unitario(self) -> Fraction | None:
        """O comparavel, derivado na hora — nunca guardado (D-02)."""
        if self.total_em_centesimos is None or self.quantidade is None:
            return None
        return unitario(self.total_em_centesimos, self.quantidade)


def menor_pedido_visivel(
    observacoes: Sequence[ObservacaoLida],
) -> MenorPedidoVisivel:
    """A oferta de MENOR UNITARIO da serie, com o carimbo dela e o `n`.

    A ORDEM E PELO UNITARIO E NUNCA PELO TOTAL. `(1000, 1)` tem o menor total e
    o maior unitario da serie; escolher pelo total devolveria o pedido mais
    CARO por unidade com a etiqueta de "menor".

    DESEMPATE PELO CARIMBO MAIS ANTIGO, para o resultado ser deterministico: com
    dois anuncios de unitario identico, a resposta nao pode depender da ordem em
    que o arquivo foi lido.

    `observacoes` sao as ofertas de UMA serie. Agrupar por `chave_da_serie` e de
    quem chama — este modulo nao decide o que e uma serie, so aritmetica sobre
    ela.
    """
    comparaveis = _comparaveis(observacoes)
    evidencia = Evidencia(n=len(comparaveis), piso=N_MINIMO_PARA_MENOR)
    if not evidencia.suficiente:
        return MenorPedidoVisivel(
            evidencia=evidencia,
            total_em_centesimos=None,
            quantidade=None,
            primeira_vez=None,
        )

    escolhida = min(
        comparaveis,
        key=lambda obs: (
            unitario(obs.total_em_centesimos, obs.quantidade),
            obs.primeira_vez,
        ),
    )
    return MenorPedidoVisivel(
        evidencia=evidencia,
        total_em_centesimos=escolhida.total_em_centesimos,
        quantidade=escolhida.quantidade,
        primeira_vez=escolhida.primeira_vez,
    )


# ===========================================================================
# A MEDIANA (ANAL-01)
# ===========================================================================


@dataclass(frozen=True)
class MedianaDosUnitarios:
    """O unitario mediano da serie — sempre um valor que EXISTIU na tela."""

    evidencia: Evidencia
    unitario: Fraction | None


def mediana_dos_unitarios(
    observacoes: Sequence[ObservacaoLida],
) -> MedianaDosUnitarios:
    """`median_low` sobre os unitarios. Abaixo do piso, o que FALTA.

    **`median_low` E NAO `median`, e a razao e a mesma do D-02.** Com `n` par,
    `statistics.median` devolve a MEDIA dos dois valores do meio — um numero que
    nunca esteve em oferta nenhuma, meio centavo inventado exatamente como o
    unitario arredondado que a Fase 3 recusou guardar. `median_low` devolve
    sempre um valor OBSERVADO. E precedente da casa: `calibrar_mercado` ja o usa
    para a referencia de saturacao e para o fim do grupo de texto.

    ABAIXO DE `N_MINIMO_PARA_MEDIANA` A RESPOSTA E O QUE FALTA, e nunca um
    numero. `statistics.median([])` levanta `StatisticsError`; o piso pega
    antes, e o caso vazio nunca chega la.
    """
    comparaveis = _comparaveis(observacoes)
    evidencia = Evidencia(n=len(comparaveis), piso=N_MINIMO_PARA_MEDIANA)
    if not evidencia.suficiente:
        return MedianaDosUnitarios(evidencia=evidencia, unitario=None)

    unitarios = [
        unitario(obs.total_em_centesimos, obs.quantidade) for obs in comparaveis
    ]
    return MedianaDosUnitarios(
        evidencia=evidencia, unitario=statistics.median_low(unitarios)
    )


# ===========================================================================
# A RECENCIA DO PRECO (ANAL-01)
# ===========================================================================


def recencia_do_preco(
    observacoes: Sequence[ObservacaoLida],
) -> datetime | None:
    """`max(primeira_vez)` da serie: "a oferta mais nova que eu vi".

    **A OUTRA RECENCIA, COM QUE ESTA NAO PODE SER CONFUNDIDA:** o `ultima_vez`
    do `catalogo-de-nomes.csv` diz quando o ITEM foi visto pela ultima vez, em
    QUALQUER preco. Ele pode ser de agora mesmo sobre um preco de tres dias
    atras — o item apareceu no painel, mas nenhuma oferta NOVA dele apareceu.
    Sao dois fatos diferentes com nomes parecidos, e trocar um pelo outro e
    mentir com cara de numero.

    Para o ANAL-01, a recencia do PRECO e esta, e so esta.

    E ELA NAO E O CARIMBO DO MENOR PEDIDO VISIVEL. O menor carrega o carimbo
    DELE (ver `MenorPedidoVisivel`); exibir o minimo de terca ao lado da
    recencia de hoje seria a mesma mentira, dentro da mesma linha.

    Serie vazia devolve `None`: nao ha carimbo nenhum a informar, e `max([])`
    levantaria.
    """
    if not observacoes:
        return None
    return max(obs.primeira_vez for obs in observacoes)


# ===========================================================================
# A TENDENCIA (ANAL-03)
# ===========================================================================

# A palavra que qualifica o `n` da tendencia, escrita UMA vez.
#
# ELA E OBRIGATORIA E A ESCOLHA DELA E O REQUISITO. "Ofertas distintas" e o que
# impede o usuario de ler a reta como "o preco caiu tanto por cento nas ultimas
# dez HORAS". Nao existe serie temporal de preco neste CSV — existe uma
# sequencia de anuncios diferentes, e o `n` conta anuncios, nao instantes.
UNIDADE_DA_JANELA = "ofertas distintas"


@dataclass(frozen=True)
class Tendencia:
    """A variacao percentual sobre a janela inteira, com o tamanho dela junto.

    `variacao_percentual` e `None` sempre que nao ha numero a dizer, e
    `motivo_da_ausencia` diz POR QUE — abaixo do piso, ou intercepto zero. Quem
    desenha nunca precisa adivinhar o motivo de um campo vazio.
    """

    evidencia: Evidencia
    variacao_percentual: float | None
    motivo_da_ausencia: str | None


def tendencia(observacoes: Sequence[ObservacaoLida]) -> Tendencia:
    """Regressao linear sobre o ORDINAL das ofertas distintas. ANAL-03.

    **O EIXO `x` E O ORDINAL `1..n`, E ISSO E O CORACAO DESTA FUNCAO.** As
    ofertas sao ordenadas por `primeira_vez` e recebem posicao `1, 2, 3, ...`;
    `y` e o unitario convertido para `float` so no momento da chamada.

    O CARIMBO NAO PODE SER O `x`. `gravar_as_paginas` chama `relogio.agora()`
    POR LINHA (`tools/gerar_observacoes_do_censo.py`), entao as dez linhas de
    uma mesma pagina tem carimbos separados por MICROSSEGUNDOS. Uma regressao
    sobre `x` quase-constante devolve uma inclinacao de magnitude absurda por
    segundo **sem levantar `StatisticsError`** — tecnicamente `x` varia — e essa
    inclinacao, virada percentual sobre a janela, apaga a queda inteira e
    reporta praticamente zero. Numero plausivel e errado e o modo de falha que
    este projeto inteiro combate. Ordinais sao distintos por construcao, entao
    o modo de falha "x is constant" fica IMPOSSIVEL.

    **O QUE SE REPORTA E A VARIACAO PERCENTUAL SOBRE A JANELA INTEIRA**,
    `slope * (n - 1) / intercept`, e nao a inclinacao crua: "tantos centesimos
    por oferta" nao significa nada para quem le. `intercept` igual a zero vira
    caso sem tendencia reportavel, com o motivo nomeado, em vez de deixar uma
    divisao por zero escapar — o CSV e editado a mao e um total zerado e entrada
    possivel.

    `statistics.linear_regression` porque o ANAL-03 pede regressao stdlib
    literalmente; minimos quadrados a mao seria reconstruir o que ja existe.

    ABAIXO DE `N_MINIMO_PARA_TENDENCIA` A RESPOSTA E O QUE FALTA, no mesmo
    padrao de estado explicito do resto do modulo.
    """
    comparaveis = _comparaveis(observacoes)
    evidencia = Evidencia(n=len(comparaveis), piso=N_MINIMO_PARA_TENDENCIA)
    if not evidencia.suficiente:
        return Tendencia(
            evidencia=evidencia,
            variacao_percentual=None,
            motivo_da_ausencia="evidencia insuficiente",
        )

    em_ordem = sorted(comparaveis, key=lambda obs: obs.primeira_vez)
    ordinais = list(range(1, len(em_ordem) + 1))
    unitarios = [
        float(unitario(obs.total_em_centesimos, obs.quantidade)) for obs in em_ordem
    ]

    reta = statistics.linear_regression(ordinais, unitarios)
    if reta.intercept == 0:
        return Tendencia(
            evidencia=evidencia,
            variacao_percentual=None,
            motivo_da_ausencia="intercepto zero, sem base para percentual",
        )

    janela = len(em_ordem) - 1
    return Tendencia(
        evidencia=evidencia,
        variacao_percentual=reta.slope * janela / reta.intercept * 100,
        motivo_da_ausencia=None,
    )


def descrever_a_tendencia(resultado: Tendencia) -> str:
    """O texto da tendencia, com o `n` da janela SEMPRE junto.

    O `n` NAO E OPCIONAL NESTA FRASE, e por isso ele nao chega por parametro
    separado: ele vem dentro do proprio `resultado`, e nao ha como montar a
    frase sem ele. Sem o tamanho da janela, a tendencia de 3 pontos parece a de
    300 — que e exatamente o que o ANAL-03 existe para impedir.

    A UNIDADE E `UNIDADE_DA_JANELA`, e nunca uma palavra de serie temporal: o
    CSV nao tem serie temporal de preco, e chamar o `n` de "observacoes ao longo
    do tempo" faria o usuario ler a reta como variacao ao longo de horas.

    Sem acento e sem travessao, como todo texto que este projeto poe na frente
    do usuario: o console do Windows abre em cp1252.
    """
    n = resultado.evidencia.n
    if resultado.variacao_percentual is None:
        if not resultado.evidencia.suficiente:
            return (
                f"tendencia: evidencia insuficiente com {n} {UNIDADE_DA_JANELA} "
                f"(preciso de {resultado.evidencia.piso})"
            )
        return (
            f"tendencia: nao reportavel em {n} {UNIDADE_DA_JANELA} "
            f"({resultado.motivo_da_ausencia})"
        )
    return (
        f"tendencia: {resultado.variacao_percentual:+.1f}% ao longo das ultimas "
        f"{n} {UNIDADE_DA_JANELA}"
    )


# ===========================================================================
# O DESTAQUE DA LINHA LIDA AGORA (ANAL-02)
# ===========================================================================

# OS TRES ESTADOS SAO TRES, E NAO DOIS MAIS `None`. "Sem destaque" nao e a
# ausencia de resposta: e a resposta "nao ha mediana que sustente um veredito
# sobre esta serie". Um `None` mudo obrigaria quem desenha a adivinhar se o
# item era caro, barato ou desconhecido — e as tres coisas se escrevem
# diferente na tela.
ABAIXO_DA_MEDIANA = "abaixo da mediana"
ACIMA_DA_MEDIANA = "acima da mediana"
SEM_DESTAQUE = "sem destaque"


@dataclass(frozen=True)
class Destaque:
    """O veredito sobre a linha lida AGORA, contra a historia de ANTES dela.

    `mediana_de_referencia` viaja JUNTO do veredito de proposito: sem ela o
    console diria "esta barata" sem dizer barata em relacao a que, e o usuario
    nao teria como discordar. E ela e a mediana de ANTES deste tick — ver
    `ModeloDeMercado.veredito_do_destaque`.
    """

    estado: str
    unitario_da_linha: Fraction | None
    mediana_de_referencia: Fraction | None
    evidencia: Evidencia

    @property
    def abaixo(self) -> bool:
        """O unico estado que o console pinta. Os outros dois so passam."""
        return self.estado == ABAIXO_DA_MEDIANA


# ===========================================================================
# O MODELO EM MEMORIA — a historia agrupada por serie
# ===========================================================================


class ModeloDeMercado:
    """As observacoes ja agrupadas por `chave_da_serie`, em memoria.

    ELE E O QUE PERMITE O `ordenar_para_o_console` E O DESTAQUE DO ANAL-02
    EXISTIREM. As funcoes acima fazem aritmetica sobre UMA serie e nao decidem o
    que e uma serie; este objeto e quem agrupa, e continua PURO: sem disco, sem
    relogio, sem impressao. Quem le o arquivo e o laco (`mercado_modo`), que
    passa a lista pronta para `de_observacoes`.

    ELE E MUTAVEL DE PROPOSITO, e e a unica coisa mutavel deste modulo. O laco
    carrega o CSV UMA vez no arranque e depois so ACRESCENTA cada observacao que
    o registro aceitou. Reler o arquivo a 1 Hz seria trabalho puro sobre
    milhares de linhas e, pior, abriria corrida com o usuario editando o CSV no
    Sheets no meio da sessao.
    """

    def __init__(self, por_serie: dict[str, list]) -> None:
        self._por_serie = por_serie

    @classmethod
    def de_observacoes(cls, observacoes: Sequence[ObservacaoLida]):
        """Agrupa uma lista de `ObservacaoLida` por `chave_da_serie`.

        A ORDEM DENTRO DE CADA SERIE E A DO ARQUIVO, e nao ordenada por carimbo:
        quem precisa de ordem cronologica (a `tendencia`) ordena por conta
        propria, e reordenar aqui esconderia de quem depura o que o CSV diz.
        """
        por_serie: dict[str, list] = {}
        for obs in observacoes:
            por_serie.setdefault(obs.chave_da_serie, []).append(obs)
        return cls(por_serie)

    def series(self) -> list[str]:
        """As chaves conhecidas, na ordem em que apareceram pela primeira vez."""
        return list(self._por_serie)

    def observacoes_de(self, chave: str) -> list:
        """As observacoes de UMA serie. Serie desconhecida devolve lista vazia.

        Lista vazia e nao `KeyError`: a pergunta "o que eu sei sobre esta serie"
        tem resposta ate quando a resposta e "nada", e um `KeyError` obrigaria
        todo chamador a envolver a chamada.
        """
        return list(self._por_serie.get(chave, ()))

    def contagem_de(self, chave: str) -> int:
        """Quantas ofertas distintas esta serie tem no modelo."""
        return len(self._por_serie.get(chave, ()))

    def nome_exibido_de(self, chave: str) -> str:
        """O nome que o usuario LE, tirado da observacao mais recente da serie.

        A MAIS RECENTE, e nao a primeira: o OCR erra e o catalogo corrige o nome
        ao longo da sessao, entao a leitura mais nova e a melhor aposta sobre
        como o item se chama hoje. A chave crua e o desempate quando a serie
        esta vazia — mostrar campo em branco pareceria defeito.
        """
        observacoes = self._por_serie.get(chave)
        if not observacoes:
            return chave
        return max(observacoes, key=lambda obs: obs.primeira_vez).nome_exibido

    def acrescentar(self, observacao: ObservacaoLida) -> None:
        """Uma observacao NOVA entra na historia. So o laco chama isto.

        E o laco quem decide o que e "nova": ele so chama aqui quando
        `registro.registrar(...)` devolveu `True`, que e o unico sinal de que a
        linha nao era duplicada e o registro estava ligado. Acrescentar sem esse
        portao faria a mesma oferta contar duas vezes no `n` — e o `n` e o que a
        fase inteira existe para nao mentir.
        """
        self._por_serie.setdefault(observacao.chave_da_serie, []).append(
            observacao
        )

    def veredito_do_destaque(self, linha) -> Destaque:
        """A linha lida AGORA contra a mediana da serie COMO ELA ESTA. ANAL-02.

        **A MEDIANA E A DE ANTES DESTE TICK, E ESSA E A REGRA INTEIRA.** Quem
        chama tem de perguntar aqui ANTES de gravar a linha e ANTES de chamar
        `acrescentar`. Se as linhas do tick ja tiverem entrado no modelo, o item
        se compara consigo mesmo: uma oferta muito barata puxa a propria mediana
        para baixo e o destaque encolhe ate virar ruido. A ordem esta fixada e
        comentada no laco (`mercado_modo.laco_do_mercado`), porque e o tipo de
        ordem que um refactor futuro desfaz sem perceber.

        **ABAIXO DO PISO DA MEDIANA O VEREDITO E `SEM_DESTAQUE`**, e nao
        "acima" nem "abaixo". Destacar contra uma mediana de duas observacoes
        seria pintar de vermelho um numero inventado — a mesma objecao que faz
        `mediana_dos_unitarios` devolver o que FALTA em vez de um numero.

        **EMPATE NAO E DESTAQUE.** `unitario == mediana` sai como
        `ACIMA_DA_MEDIANA`, porque o que o ANAL-02 promete e "abaixo da mediana
        historica" e um empate nao esta abaixo de nada.

        `linha` e lida POR NOME (`chave_da_serie`, `total_em_centesimos`,
        `quantidade`), no molde do resto do modulo: serve tanto a `LinhaLida` da
        Fase 2 quanto a `ObservacaoLida` da Fase 3, e o modulo continua sem
        arrastar a cadeia de visao.

        QUANTIDADE NAO POSITIVA SAI SEM DESTAQUE, e nao levanta. A grade e
        leitura de TELA: `quantidade=0` e leitura possivel, e um
        `ZeroDivisionError` aqui derrubaria o modo no meio do farm por causa de
        uma celula mal lida.
        """
        observacoes = self._por_serie.get(linha.chave_da_serie, ())
        mediana = mediana_dos_unitarios(observacoes)
        if mediana.unitario is None:
            return Destaque(
                estado=SEM_DESTAQUE,
                unitario_da_linha=None,
                mediana_de_referencia=None,
                evidencia=mediana.evidencia,
            )

        try:
            desta_linha = unitario(linha.total_em_centesimos, linha.quantidade)
        except ValueError:
            return Destaque(
                estado=SEM_DESTAQUE,
                unitario_da_linha=None,
                mediana_de_referencia=mediana.unitario,
                evidencia=mediana.evidencia,
            )

        return Destaque(
            estado=(
                ABAIXO_DA_MEDIANA
                if desta_linha < mediana.unitario
                else ACIMA_DA_MEDIANA
            ),
            unitario_da_linha=desta_linha,
            mediana_de_referencia=mediana.unitario,
            evidencia=mediana.evidencia,
        )

    def vereditos_da_pagina(self, linhas) -> tuple[Destaque, ...]:
        """TODAS as linhas da pagina contra a MESMA referencia CONGELADA.

        O DEFEITO MEDIDO EM PRODUCAO (2026-09-02): quatro ofertas de Adena
        anunciadas NO MESMO SEGUNDO citaram medianas diferentes —
        `11,00 contra 13,87 n=7`, `11,20 contra 13,00 n=8`,
        `11,40 contra 13,00 n=9`, `11,70 contra 12,00 n=10`. O laco julgava
        linha a linha e acrescentava cada uma a populacao antes de comparar a
        seguinte, entao a MESMA oferta era noticia forte na primeira fatia da
        grade e quase nada na ultima.

        O QUE FOI RECUSADO: o veredito dependendo de ONDE A LINHA CALHOU DE
        ESTAR NA GRADE. Isso nao e opiniao sobre preco — e artefato de
        varredura. O usuario nao tem como discordar de um numero que muda de
        significado conforme a ordem em que o scanner leu a tela.

        O CUSTO ACEITO, ESCRITO E NAO ESCONDIDO: uma pagina inteira de ofertas
        baratas passa a anunciar TODAS contra a referencia congelada, em vez de
        a segunda ja se comparar com a primeira. Numa enxurrada de ofertas
        baratas isso e MAIS anuncio, e nao menos. O custo e conhecido e limitado
        a UMA pagina; o defeito trocado por ele nao tinha limite nenhum e era
        invisivel na leitura do log, porque cada linha parecia perfeitamente
        coerente sozinha.

        A REFERENCIA CONGELADA E A DE ANTES DA PAGINA, E NAO A DE ANTES DO TICK.
        Hoje as duas sao a mesma coisa, porque o laco so chama `acrescentar`
        dentro deste bloco — e esta escrito justamente para que um refactor
        futuro nao acredite que a distincao nao existe. No dia em que outra
        fonte alimentar o modelo dentro do tick, e a de antes da PAGINA que vale.

        `veredito_do_destaque` CONTINUA EXISTINDO E PUBLICA — ela e a primitiva
        de UMA linha e ha teste vivo sobre ela —, mas o laco nao a chama mais:
        quem julga pagina julga a pagina inteira de uma vez.

        A TUPLA SAI ALINHADA COM `linhas`, na MESMA ordem, para quem chama poder
        fazer `zip(linhas, vereditos)` sem casar nada a mao. E esta funcao
        continua PURA como o resto do modulo: ela nao escreve, nao chama
        `acrescentar` e nao toca no relogio.
        """
        return tuple(self.veredito_do_destaque(linha) for linha in linhas)


# ===========================================================================
# A ORDENACAO PARA O CONSOLE — a watchlist como DESTAQUE
# ===========================================================================

# Quantas series aparecem no topo por evidencia quando nao ha watchlist.
#
# OITO E ESCOLHA, E NAO MEDICAO — pela mesma disciplina dos pisos acima. A razao
# dela existir: o censo viu 39 series distintas, e despejar 39 blocos de tres
# linhas cada num console repintado seria uma parede que ninguem le. Oito cabe
# numa tela sem rolagem junto com o resumo do laco.
#
# ELE NAO CORTA A WATCHLIST. O corte e do rabo por evidencia; um item que o
# usuario marcou e sumiu por corte seria a watchlist virando porta de SAIDA, que
# e o defeito simetrico ao que a Fase 2 corrigiu na porta de entrada.
SERIES_NO_TOPO = 8


@dataclass(frozen=True)
class SerieNoConsole:
    """Uma linha da lista que o console vai desenhar, ja resolvida."""

    chave: str
    nome_exibido: str
    n: int
    na_watchlist: bool


def nome_normalizado(nome: str) -> str:
    """Caixa dobrada e espacos colapsados. O UNICO criterio de casamento.

    `casefold` e nao `lower` porque ele e a normalizacao de comparacao do
    Unicode; e o `" ".join(split())` colapsa o espaco duplo que o usuario digita
    sem perceber e o espaco que o OCR as vezes acrescenta.

    E SO ISSO — NADA DE SIMILARIDADE FUZZY. O `CLAUDE.md` recomenda `rapidfuzz`
    para nome de membro de party, e para AQUELE problema ele esta certo: la o
    alvo e um conjunto fechado de apelidos e o OCR erra letras. Aqui ele seria
    um defeito: `+3 Dragon Belt` e `+4 Dragon Belt` diferem em UM caractere e
    sao series DELIBERADAMENTE separadas — medido numa unica pagina real, o
    mesmo nome base valia de 7,02 a 100,00 conforme o encanto. Qualquer
    similaridade que tolerasse um caractere juntaria as duas e destruiria as
    duas series.
    """
    return " ".join(nome.split()).casefold()


def ordenar_para_o_console(
    modelo: ModeloDeMercado, watchlist: Sequence[str]
) -> list[SerieNoConsole]:
    """As series a mostrar, watchlist primeiro e MARCADA, resto por evidencia.

    ESTA FUNCAO CONTRARIA A LETRA DO CRITERIO 3 DO ROADMAP DE PROPOSITO, e a
    divergencia esta escrita aqui porque ela precisa ser visivel para quem
    verificar a fase. O criterio 3 diz *"para cada item da watchlist"*. Ele e
    ANTERIOR a Fase 2, que em 2026-08-29 tirou a watchlist da porta de entrada:
    o nome passou a vir por OCR e TUDO que aparece e registrado. O `[mercado]
    watchlist` do `config.toml` continua comentado e o usuario nunca o
    preencheu. Responder so "para cada item da watchlist" seria, hoje, responder
    para NADA.

    O criterio e honrado em SUBSTANCIA, em tres regras:

    1. **Sem watchlist, as series com MAIS EVIDENCIA vem primeiro.** O usuario
       nao precisa configurar nada para ver valor — que e exatamente a premissa
       que fez a Fase 2 trocar a watchlist por OCR.
    2. **Com watchlist, as series dela vem PRIMEIRO e MARCADAS.**
    3. **O resto continua visivel abaixo.** Filtrar de vez esconderia o item
       novo que a Fase 2 existe para descobrir, e o item novo e a razao de o
       scanner ler o quadro inteiro.

    O CASAMENTO E EXATO sobre `nome_normalizado`, nunca fuzzy — a razao esta
    escrita naquela funcao.

    DESEMPATE POR CHAVE quando duas series tem o mesmo `n`: sem ele a ordem
    dependeria da ordem de leitura do arquivo, e o console reembaralharia
    sozinho a cada arranque.
    """
    alvos = {nome_normalizado(nome) for nome in watchlist}

    marcadas: list[SerieNoConsole] = []
    demais: list[SerieNoConsole] = []
    for chave in modelo.series():
        nome = modelo.nome_exibido_de(chave)
        linha = SerieNoConsole(
            chave=chave,
            nome_exibido=nome,
            n=modelo.contagem_de(chave),
            na_watchlist=nome_normalizado(nome) in alvos,
        )
        (marcadas if linha.na_watchlist else demais).append(linha)

    def por_evidencia(linha: SerieNoConsole) -> tuple[int, str]:
        return (-linha.n, linha.chave)

    marcadas.sort(key=por_evidencia)
    demais.sort(key=por_evidencia)
    # A watchlist INTEIRA, e so o rabo por evidencia e cortado. Um item marcado
    # que sumisse por corte seria a watchlist virando porta de saida.
    return marcadas + demais[:SERIES_NO_TOPO]


# ===========================================================================
# A MARGEM DE CRAFT (ANAL-04)
# ===========================================================================

# De quantas horas em diante um componente e marcado como VELHO no console.
#
# VINTE E QUATRO E **ESCOLHA, E NAO MEDICAO** — pela mesma disciplina dos
# pisos de evidencia acima e do `SERIES_NO_TOPO`. Ninguem mediu com que
# frequencia uma serie do World Exchange ganha oferta nova; o censo mediu a
# LEITURA (151 paginas lidas contra 189 perdidas, 39 series), e aqueles
# numeros nao servem de substituto para este.
#
# A RAZAO DE VINTE E QUATRO: um dia e o horizonte em que o usuario ainda
# reconhece o proprio farm. "Vi este preco ontem" e uma frase que ele
# consegue avaliar; "vi ha 31 horas" ja e uma frase sobre um mercado que ele
# nao acompanhou. Se no uso real o console marcar tudo, ou nunca marcar
# nada, este numero muda, e e uma linha.
HORAS_PARA_MARCAR_COMPONENTE_VELHO = 24


def componente_esta_velho(idade: timedelta | None) -> bool:
    """Se esta idade ja cruzou o limiar. O limiar e ESCOLHA, nao medicao.

    IDADE DESCONHECIDA NAO E VELHA. Quando a linha nem tem carimbo, ela ja
    quebrou a margem por outro caminho — marca-la de velha acrescentaria um
    segundo defeito por cima de um que ja esta reportado.

    O LIMIAR CONTA A PARTIR DELE, e nao depois: exatamente 24 h ja e velho.
    Um `>` estrito faria a marca depender do segundo em que o console
    repintou, e "24 h e 0 s" nao e mais fresco que "24 h e 1 s".
    """
    if idade is None:
        return False
    return idade >= timedelta(hours=HORAS_PARA_MARCAR_COMPONENTE_VELHO)


# Os tres desfechos de resolver um nome DIGITADO para uma `chave_da_serie`.
# Cada um tem comportamento NOMEADO, e nenhum deles e "escolhe a mais
# parecida" — ver `resolver_o_nome`.
RESOLUCAO_UNICA = "unica"
RESOLUCAO_SEM_CORRESPONDENCIA = "sem correspondencia"
RESOLUCAO_AMBIGUA = "ambigua"

# Quantos nomes parecidos a mensagem OFERECE quando nada casou. Tres cabe
# numa linha e ja cobre o erro de digitacao tipico; uma lista de dez viraria
# uma parede que o usuario nao le.
SUGESTOES_NA_RECUSA = 3


@dataclass(frozen=True)
class ResolucaoDeNome:
    """O que aconteceu quando se procurou UM nome digitado no modelo."""

    estado: str
    nome_pedido: str
    chave: str | None
    candidatas: tuple[str, ...]
    parecidos: tuple[str, ...]

    @property
    def resolveu(self) -> bool:
        return self.estado == RESOLUCAO_UNICA


def resolver_o_nome(modelo: ModeloDeMercado, nome: str) -> ResolucaoDeNome:
    """O nome que o usuario DIGITOU -> a `chave_da_serie` que o CSV guarda.

    ESTE E O PROBLEMA REAL DO ANAL-04, e nao a aritmetica. O usuario escreve
    `Common Aztac`; o CSV guarda a chave, que e o nome mais um separador mais
    a assinatura de digitos (`mercado_catalogo.assinatura_da_chave`). E o
    `nome_exibido` OSCILA no OCR — e por isso que os dois campos existem
    (`mercado_registro`, D-03).

    O CASAMENTO E IGUALDADE EXATA sobre `nome_normalizado`: caixa dobrada e
    espacos colapsados, e mais nada.

    TRES DESFECHOS, TRES COMPORTAMENTOS, E NENHUM DELES E ADIVINHAR:

    1. **uma serie casa** — usa ela;
    2. **nenhuma casa** — quem chama QUEBRA, e a mensagem OFERECE os nomes
       mais parecidos para o usuario copiar. Oferecer e ajudar; adotar seria
       decidir por ele;
    3. **duas ou mais casam** — quem chama QUEBRA tambem, LISTANDO as
       candidatas.

    O `difflib` aparece aqui SO PARA SUGERIR, e nunca para resolver. Ele nao
    toca o desfecho: `parecidos` so e preenchido no caso em que ja se sabe
    que nada casou, e o valor dele e texto de ajuda. Trocar essa ordem seria
    reintroduzir pela porta dos fundos o casamento aproximado que a funcao
    inteira existe para recusar.
    """
    alvo = nome_normalizado(nome)
    casadas = tuple(
        chave
        for chave in modelo.series()
        if nome_normalizado(modelo.nome_exibido_de(chave)) == alvo
    )

    if len(casadas) == 1:
        return ResolucaoDeNome(
            estado=RESOLUCAO_UNICA,
            nome_pedido=nome,
            chave=casadas[0],
            candidatas=casadas,
            parecidos=(),
        )

    if len(casadas) > 1:
        return ResolucaoDeNome(
            estado=RESOLUCAO_AMBIGUA,
            nome_pedido=nome,
            chave=None,
            # ORDENADAS, porque a mensagem tem de sair igual em toda leitura
            # do mesmo arquivo — senao o usuario ve a lista trocar de ordem
            # a cada arranque e acha que o programa esta indeciso.
            candidatas=tuple(sorted(casadas)),
            parecidos=(),
        )

    disponiveis = [modelo.nome_exibido_de(chave) for chave in modelo.series()]
    return ResolucaoDeNome(
        estado=RESOLUCAO_SEM_CORRESPONDENCIA,
        nome_pedido=nome,
        chave=None,
        candidatas=(),
        parecidos=tuple(
            difflib.get_close_matches(nome, disponiveis, n=SUGESTOES_NA_RECUSA)
        ),
    )


# Os tres estados de uma margem. `MARGEM_CALCULADA` e o unico em que sai
# numero; os outros dois saem com o MOTIVO, e o console nao imprime valor
# nenhum neles.
MARGEM_CALCULADA = "calculada"
MARGEM_SEM_SERIE = "sem observacao"
MARGEM_AMBIGUA = "nome ambiguo"

# Os dois papeis de uma linha da margem. O produto entra na conta somando e
# os componentes subtraindo, mas os dois se desenham igual e os dois tem
# staleness propria — e por isso e um tipo so com um campo de papel, e nao
# dois tipos quase iguais.
PAPEL_PRODUTO = "produto"
PAPEL_COMPONENTE = "componente"


@dataclass(frozen=True)
class LinhaDaMargem:
    """Um lado da conta, com a evidencia e a IDADE PROPRIA dele.

    A IDADE VIAJA AQUI DENTRO, e nao numa tabela paralela, pela mesma razao
    que a `Evidencia` viaja dentro de todo resultado: uma margem calculada
    com um ingrediente visto hoje e outro visto ha uma semana nao e uma
    margem, e quem desenha nao pode ter como esquecer de pedir a idade.
    """

    papel: str
    item: str
    chave: str
    nome_exibido: str
    quantidade_da_receita: int
    menor: MenorPedidoVisivel
    mediana: MedianaDosUnitarios
    idade: timedelta | None

    @property
    def velho(self) -> bool:
        return componente_esta_velho(self.idade)

    @property
    def subtotal(self) -> Fraction | None:
        """O unitario vezes o que a receita pede deste lado. EXATO."""
        unidade = self.menor.unitario
        if unidade is None:
            return None
        return unidade * self.quantidade_da_receita

    @property
    def subtotal_pela_mediana(self) -> Fraction | None:
        if self.mediana.unitario is None:
            return None
        return self.mediana.unitario * self.quantidade_da_receita


@dataclass(frozen=True)
class MargemDeCraft:
    """A diferenca entre os pedidos, com a staleness de cada componente.

    `margem_em_centesimos` E `Fraction`, e nao `int` nem `float`: o unitario
    e uma divisao exata e o arredondamento acontece SO na formatacao. Ver
    `unitario`.

    QUANDO ELA QUEBRA, `margem_em_centesimos` E `None` E `motivo` DIZ O QUE
    FALTOU. Um `None` mudo obrigaria quem desenha a adivinhar entre "faltou
    ingrediente" e "o nome estava ambiguo", e as duas coisas se escrevem
    diferente na tela.
    """

    estado: str
    produto: str
    rende: int
    linhas: tuple[LinhaDaMargem, ...]
    margem_em_centesimos: Fraction | None
    margem_pela_mediana: Fraction | None
    motivo: str
    idade_mais_velha: timedelta | None
    nome_do_mais_velho: str | None

    @property
    def ok(self) -> bool:
        return self.estado == MARGEM_CALCULADA


def margem_de_craft(receita, modelo: ModeloDeMercado, agora: datetime):
    """A margem do ANAL-04: os pedidos do produto menos os dos ingredientes.

    A DEFINICAO, E ELA E A UNICA DEFENSAVEL COM O QUE O CSV TEM
    ============================================================
    O menor pedido visivel do PRODUTO multiplicado pelo quanto a receita
    rende, menos a soma, sobre os componentes, do menor pedido visivel de
    cada um multiplicado pela quantidade que a receita pede. Tudo em
    unitario-`Fraction` antes de multiplicar; o arredondamento so na
    formatacao.

    **OS DOIS LADOS SAO MENOR PEDIDO VISIVEL, OU SEJA OFERTAS.** O numero que
    sai daqui e a diferenca entre o que estao PEDINDO pelo produto e o que
    estao PEDINDO pelos ingredientes. Ninguem comprou nem vendeu por valor
    nenhum destes: o scanner le o quadro de anuncios, e o quadro nao registra
    negocio fechado. Por isso as expressoes que prometem transacao ou ganho
    realizado sao PROIBIDAS neste modulo, exatamente como no resto da fase, e
    ha teste prendendo esta docstring e o resultado devolvido.

    POR QUE "MENOR" E NAO "MEDIANA" COMO CONTA PRINCIPAL: e assim que um
    humano compraria os ingredientes e anunciaria o produto, pelo melhor
    pedido visivel. E porque a mediana exige o piso de cinco POR COMPONENTE,
    o que multiplicaria a chance de a margem inteira cair. A mediana entra
    como linha SECUNDARIA (`margem_pela_mediana`), e ela e `None` sempre que
    qualquer um dos lados nao alcanca o piso.

    A RESOLUCAO DO NOME QUEBRA EM VEZ DE ADIVINHAR
    ===============================================
    Ver `resolver_o_nome`. Nenhuma serie casa -> a margem INTEIRA nao
    aparece, com o nome do que faltou. Duas ou mais casam -> quebra tambem,
    listando as candidatas.

    **NAO SE USA `mercado_catalogo.similaridade` AQUI, e a razao esta
    medida.** Aquele corte (`mercado_corte_de_similaridade = 0.8947`) foi
    calibrado para agrupar duas leituras de OCR DO MESMO PIXEL, e nao para
    casar texto que um humano digitou. Medido nesta arvore: ele daria 0,9286
    para `+3 Dragon Belt` contra `+4 Dragon Belt` e 0,9375 para `B-grade
    Gemstone` contra `C-grade Gemstone` — series deliberadamente separadas,
    porque misturar encantos nao acrescenta ruido, destroi a serie. E daria
    0,88 para `+3 Dragon Belt` contra `Dragon Belt`, abaixo do corte. Ou
    seja: ele nao erra sempre, erra de forma imprevisivel.

    AS CINCO COISAS QUE ESTA CONTA **NAO** RESOLVE, EM VOZ ALTA
    ===========================================================
    1. **Ela nao sabe se a oferta ainda existe.** Um menor pedido visivel de
       vinte minutos atras pode ter sido comprado ha dezenove. O CSV nao
       registra desaparecimento: a dedup e por conteudo, sem tempo de saida.
       Nenhuma margem deste projeto e acionavel sem o usuario conferir na
       tela, e o console diz isso uma vez no cabecalho.
    2. **Ela ignora a comissao do World Exchange e a chance de falha do
       craft.** A diferenca que sai daqui e BRUTA e sobre pedidos.
    3. **Ela nao lida com quantidade minima.** Se o menor pedido de um
       componente e um lote de 100 e a receita precisa de 20, o usuario
       compra 100. Usar o unitario e a simplificacao certa, mas AINDA E uma
       simplificacao, e o console nao finge que nao e.
    4. **Ela herda a fusao de series aberta desde a Fase 2.** Duas variantes
       de grade a 0,9375 podem estar na MESMA serie; se uma delas for
       componente, a margem sai errada e nao ha como o programa saber.
    5. **Ela nao valida que a receita e real.** O programa nao conhece o
       crafting do jogo. Uma receita errada produz um numero perfeitamente
       formatado e completamente falso. A unica defesa que existe contra
       isso e que o usuario escreveu a receita.

    `agora` ENTRA POR PARAMETRO: este modulo continua PURO, sem relogio do
    sistema, sem disco e sem impressao.
    """
    pedidos = [(PAPEL_PRODUTO, receita.produto, receita.rende)]
    pedidos += [
        (PAPEL_COMPONENTE, componente.item, componente.quantidade)
        for componente in receita.componentes
    ]

    linhas: list[LinhaDaMargem] = []
    for papel, item, quantidade in pedidos:
        resolucao = resolver_o_nome(modelo, item)

        if resolucao.estado == RESOLUCAO_AMBIGUA:
            return _margem_quebrada(
                receita,
                MARGEM_AMBIGUA,
                f"'{item}' casa com {len(resolucao.candidatas)} series ao "
                f"mesmo tempo: {', '.join(resolucao.candidatas)}. Escolher "
                f"uma delas daria um numero plausivel e errado. Renomeie a "
                f"receita ou separe as series.",
            )

        if resolucao.estado == RESOLUCAO_SEM_CORRESPONDENCIA:
            ajuda = (
                f" Os nomes parecidos que eu tenho: "
                f"{', '.join(resolucao.parecidos)}."
                if resolucao.parecidos
                else ""
            )
            return _margem_quebrada(
                receita,
                MARGEM_SEM_SERIE,
                f"nao ha observacao nenhuma de '{item}', entao a margem "
                f"inteira nao sai. Calcular sem ele daria um numero "
                f"plausivel e errado.{ajuda}",
            )

        observacoes = modelo.observacoes_de(resolucao.chave)
        menor = menor_pedido_visivel(observacoes)
        if menor.total_em_centesimos is None:
            return _margem_quebrada(
                receita,
                MARGEM_SEM_SERIE,
                f"'{item}' existe no historico mas nao tem nenhuma oferta "
                f"comparavel, entao a margem inteira nao sai.",
            )

        # A IDADE VEM DA RECENCIA DO **PRECO** — `max(primeira_vez)` das
        # ofertas desta serie — e NUNCA do `ultima_vez` do catalogo, que diz
        # quando o ITEM foi visto em qualquer valor e pode ser de agora mesmo
        # sobre uma leitura de tres dias atras. Sao dois fatos diferentes com
        # nomes parecidos, e trocar um pelo outro e mentir com cara de numero.
        quando = recencia_do_preco(observacoes)
        linhas.append(
            LinhaDaMargem(
                papel=papel,
                item=item,
                chave=resolucao.chave,
                nome_exibido=modelo.nome_exibido_de(resolucao.chave),
                quantidade_da_receita=quantidade,
                menor=menor,
                mediana=mediana_dos_unitarios(observacoes),
                idade=None if quando is None else agora - quando,
            )
        )

    produto = linhas[0]
    componentes = linhas[1:]
    margem = produto.subtotal - sum(
        (linha.subtotal for linha in componentes), Fraction(0)
    )

    # A LINHA SECUNDARIA SO SAI INTEIRA OU NAO SAI. Misturar mediana de um
    # lado com menor do outro produziria um terceiro numero que nao e nem uma
    # coisa nem outra, e que ninguem saberia ler.
    pela_mediana = None
    if all(linha.subtotal_pela_mediana is not None for linha in linhas):
        pela_mediana = produto.subtotal_pela_mediana - sum(
            (linha.subtotal_pela_mediana for linha in componentes), Fraction(0)
        )

    # A MAIS VELHA SOBE PARA O TOPO, COM O NOME JUNTO. E o numero que decide
    # se a margem vale alguma coisa, e enterra-lo no meio da lista seria
    # esconde-lo. O PRODUTO CONCORRE junto dos componentes de proposito: um
    # produto com preco de uma semana atras estraga a conta exatamente como
    # um ingrediente estragaria.
    com_idade = [linha for linha in linhas if linha.idade is not None]
    mais_velha = max(com_idade, key=lambda linha: linha.idade, default=None)

    return MargemDeCraft(
        estado=MARGEM_CALCULADA,
        produto=receita.produto,
        rende=receita.rende,
        linhas=tuple(linhas),
        margem_em_centesimos=margem,
        margem_pela_mediana=pela_mediana,
        motivo="",
        idade_mais_velha=None if mais_velha is None else mais_velha.idade,
        nome_do_mais_velho=None if mais_velha is None else mais_velha.item,
    )


def _margem_quebrada(receita, estado: str, motivo: str) -> MargemDeCraft:
    """A margem que nao sai, com o MOTIVO no lugar do numero.

    NENHUM VALOR PARCIAL VIAJA JUNTO. Devolver as linhas que ja tinham
    resolvido convidaria quem desenha a somar o que deu, e "a margem sem o
    Leonard" e precisamente o numero plausivel e errado que este estado
    existe para impedir.
    """
    return MargemDeCraft(
        estado=estado,
        produto=receita.produto,
        rende=receita.rende,
        linhas=(),
        margem_em_centesimos=None,
        margem_pela_mediana=None,
        motivo=motivo,
        idade_mais_velha=None,
        nome_do_mais_velho=None,
    )
