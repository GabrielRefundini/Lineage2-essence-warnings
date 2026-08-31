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

import statistics
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # pragma: no cover - so o verificador de tipos passa aqui
    from .mercado_registro import ObservacaoLida

__all__ = [
    "Evidencia",
    "MedianaDosUnitarios",
    "MenorPedidoVisivel",
    "ModeloDeMercado",
    "N_MINIMO_PARA_MEDIANA",
    "N_MINIMO_PARA_MENOR",
    "N_MINIMO_PARA_TENDENCIA",
    "SERIES_NO_TOPO",
    "SerieNoConsole",
    "Tendencia",
    "descrever_a_tendencia",
    "mediana_dos_unitarios",
    "menor_pedido_visivel",
    "nome_normalizado",
    "ordenar_para_o_console",
    "recencia_do_preco",
    "tendencia",
    "unitario",
]


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
