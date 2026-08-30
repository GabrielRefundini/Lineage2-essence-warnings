"""Os predicados PUROS do agrupamento de nome de item do World Exchange.

Este modulo nao abre janela, nao le teclado, nao escreve arquivo e nao pergunta
nada. Ele responde "estas duas leituras sao a mesma serie?" e "qual e a chave
dela?". Quem guarda o catalogo em disco e quem mostra a recusa a um humano vem
depois (02-05); quem produz os pixels e `mercado_leitura.py` (02-04).

PRIMEIRA ETAPA, DE PROPOSITO: SO OS PREDICADOS
===============================================
Nada de I/O aqui ainda. O arquivo do catalogo tem escrita atomica, leitura
defensiva e formato a decidir, e misturar isso com a regra de agrupamento faria
um modulo em que nao da para afirmar a regra sem montar um arquivo.

A METRICA E `difflib.SequenceMatcher`, E NAO `rapidfuzz` (D-04)
================================================================
`rapidfuzz` nao esta instalado, nao esta no `requirements.txt`, e sobre estes
nomes — curtos, sem tokens reordenados, diferencas de 1-2 caracteres — as duas
metricas dao praticamente o mesmo numero. Medido: `Earth Spirit Evolution Stone`
contra `Earth Spirit Ewlution Stone` da 94,55 nas duas. Nao vale uma dependencia
nova para 10 linhas por segundo contra um catalogo de algumas centenas de nomes,
e `tests/test_firewall_escopo.py` existe justamente para manter a arvore fechada.

E NAO E `rapidfuzz.WRatio`, QUE FOI REFUTADO POR MEDICAO (D-05)
----------------------------------------------------------------
UM NUMERO QUE CAIU PRECISA DIZER QUE CAIU. A proposta original era `WRatio` com
corte 88. Rodada contra a implementacao de referencia do proprio rapidfuzz:

    par                                         WRatio   difflib   precisa
    Common Aztac x Common Aztac M. Def. +200     90,00    64,86    separar
    +6 Agathion ... x +4 Agathion ...            96,77    96,77    separar
    Hardin's Soul Crystal Lv. 1 x Lv. 3          96,30    96,30    separar
    Hardin's Soul Crystal Lv. I x Lv. 1          96,30    96,30    AGRUPAR

O `WRatio` cai no ramo do `partial_ratio` quando as strings tem razao de tamanho
>= 1,5, e `Common Aztac` sendo substring PERFEITA de `Common Aztac M. Def. +200`
produz `100 x 0,9 = 90,00` — acima do corte 88, fundindo exatamente as duas
series que o corte existia para separar.

A TRAVA DE DIGITOS, E POR QUE NENHUM CORTE A SUBSTITUI (D-03)
==============================================================
As duas ultimas linhas da tabela sao o achado que decide o desenho: o MESMO
0,9630 teria de decidir coisas OPOSTAS — separar `Lv. 1` de `Lv. 3` e agrupar
`Lv. I` com `Lv. 1`. Nenhum corte escalar resolve isso, em nenhuma metrica de
distancia de edicao, e os tres casos aparecem juntos num frame real.

Por isso a sequencia de digitos do nome tem de bater EXATAMENTE antes de a
similaridade ser consultada. `+6 X` != `+4 X` e `Lv. 1` != `Lv. 3` por
CONSTRUCAO, nao por limiar. A similaridade decide so o resto do nome.

O parente mais proximo no repositorio e `manutencao._normalizar_digitos`, e ele
NAO serve aqui: aquele troca `O/l/I/S` por digito dentro de um token que JA tem
digito de verdade, entao `Lv. I` sai intacto dele. Ele resolve o problema oposto.

A FONTE DA ASSINATURA E DECISAO DO CHAMADOR, NAO DESTE MODULO
==============================================================
`chave_da_serie` e `agrupar` recebem a assinatura JA CALCULADA. Duas fontes
candidatas moram aqui — `assinatura_por_ocr` e `assinatura_por_molde` — e
nenhuma esta ligada a chave. Isso e deliberado: a escolha entre elas e uma porta
de MAO UNICA (a chave vai para o disco e a Fase 3 a referencia em cada
observacao), entao ela e do usuario, e deixa-la no chamador e o que permite
decidi-la sem reescrever este modulo.

A FAIXA CINZENTA (D-06)
========================
Entre o piso e o corte a linha nao agrupa NEM cria serie: e descartada com
aviso. Fusao no CSV e irreversivel; descarte nao e.
"""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

log = logging.getLogger(__name__)

# Os dez digitos que a tela do jogo desenha. `str.isdigit()` NAO serve: ele
# devolve True para `²`, `٣` e mais uma centena de pontos Unicode que o motor de
# OCR pode cuspir num recorte ruim, e um deles virando assinatura criaria uma
# serie fantasma que ninguem consegue reproduzir olhando a tela.
DIGITOS = "0123456789"

# O separador entre o slug do nome e a assinatura, DENTRO da chave. Ele existe
# para que a fusao de duas series seja impossivel na propria chave, e nao so no
# predicado: quem olhar `agathion-alpha-hunter-sealed#6` no CSV ve o encanto sem
# precisar do codigo. `#` porque nao aparece em nome de item nem colide com o
# separador `;` que a Fase 3 usa no CSV.
SEPARADOR_DA_ASSINATURA = "#"


@dataclass(frozen=True)
class EntradaDoCatalogo:
    """Uma serie ja vista. `chave` e a identidade; `nome` e o rotulo exibido."""

    chave: str
    nome: str
    assinatura: str


@dataclass(frozen=True)
class ResultadoDoAgrupamento:
    """O veredito sobre UMA leitura.

    `chave is None` significa NADA GRAVADO — nem agrupamento nem serie nova. E
    o estado da faixa cinzenta e o da leitura vazia, e os dois sao legitimos.
    `motivo` sempre diz por que, porque a recusa nunca e silenciosa.
    """

    chave: str | None
    motivo: str
    nova: bool


def assinatura_por_ocr(nome: str | None) -> str:
    """Os digitos do nome LIDO, na ordem em que aparecem. A trava de D-03.

    ORDEM DE APARICAO, e nao ordenacao: `Lv. 12` e `Lv. 21` sao series
    diferentes, e ordenar os digitos colapsaria as duas numa assinatura `12`
    unica — a fusao que a trava existe para impedir.

    Nome sem digito devolve `""`, que e uma assinatura legitima: e a de todo
    item sem encanto e sem nivel. Ela so bate com outra `""`.

    ATENCAO, E ESTA E A MEDICAO QUE A TASK 2 DO 02-03 POE NA MESA: aplicada a
    leitura de OCR, esta funcao devolve `""` para `Hardin's Soul Crystal Lv. I`
    e `"1"` para `... Lv. 1`. As duas nao batem, as duas escalas caem em series
    diferentes, e a linha morre — exatamente o ruido que D-02 foi escrito para
    absorver. O conflito e real, esta medido, e nao esta escondido aqui dentro.
    """
    if not nome:
        return ""
    return "".join(caractere for caractere in nome if caractere in DIGITOS)


def similaridade(a: str | None, b: str | None) -> float:
    """`difflib.SequenceMatcher(None, a, b).ratio()`. Nunca levanta.

    Vazio contra qualquer coisa devolve 0,0 em vez de deixar o `SequenceMatcher`
    decidir: `ratio()` de duas strings vazias e 0,0 mas `ratio()` de uma vazia
    contra outra tambem, e depender desse detalhe faria o predicado da linha
    vazia morar na biblioteca padrao em vez de aqui, onde da para le-lo.
    """
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _slug(nome: str) -> str:
    """O nome reduzido a um identificador estavel, sem espaco.

    Minusculas, alfanumerico preservado, todo o resto virando `-`, com os `-`
    colapsados e aparados. `+6 Agathion Alpha Hunter Sealed` ->
    `6-agathion-alpha-hunter-sealed`.
    """
    pedacos: list[str] = []
    for caractere in nome.lower():
        pedacos.append(caractere if caractere.isalnum() and caractere.isascii() else "-")
    return "-".join(parte for parte in "".join(pedacos).split("-") if parte)


def chave_da_serie(nome: str | None, assinatura: str) -> str | None:
    """A identidade estavel da serie, ou `None` quando nao ha nome.

    A assinatura entra ANEXADA e explicita, e nao so implicita no slug: o slug
    de `Lv. I` e o de `Lv. 1` diferem, mas o de um nome truncado pelo OCR
    poderia coincidir com o de outro, e a assinatura e a ultima linha de defesa
    contra duas series virarem uma na propria chave.

    `None` para nome vazio, so espaco, ou `None`. Uma leitura vazia nunca produz
    chave nem serie — e nao produzir e diferente de produzir uma chave vazia,
    que iria para o CSV e a Fase 3 referenciaria como se fosse item.
    """
    if not nome or not nome.strip():
        return None
    corpo = _slug(nome)
    if not corpo:
        # Nome com conteudo mas sem alfanumerico nenhum (`+++`). Ele e um nome
        # estranho, nao a ausencia de nome, e a distincao importa: `None` e
        # reservado para "nao ha o que gravar".
        corpo = "sem-alfanumerico"
    return corpo + SEPARADOR_DA_ASSINATURA + assinatura


def assinatura_por_molde(
    recorte_bgr,
    moldes,
    piso: float,
    margem: float,
    *,
    pontuar_runs: Callable[[object, object], Sequence[tuple[str, float, float]] | None],
) -> str | None:
    """Os digitos do recorte lidos pelos MOLDES, ou `None`. NUNCA levanta.

    TUDO OU NADA, o mesmo de `propor_rotulo`: basta um run que nao passe no piso
    E na margem, ou que nao seja digito, para a leitura inteira cair. Uma
    assinatura parcial seria pior que nenhuma — ela viraria a chave de uma serie
    que ninguem consegue reproduzir.

    O MOTOR DE GLIFO CHEGA INJETADO, e a razao e estrutural. `segmentar_glifos`,
    `_alinhar_por_preenchimento` e `_par_incalculavel` moram hoje em
    `calibrar_mercado.py`, que e FERRAMENTA: ela chama
    `tornar_consciente_de_dpi()` NO IMPORT, carrega `argparse` e `cv2.imshow`, e
    o repositorio mantem em tres precedentes a seta apontando sempre da
    ferramenta para o modulo puro, nunca o contrario. A promocao dessas
    primitivas para um modulo puro e trabalho do 02-04. Ate la, injetar e o
    padrao ja usado por `VigiaDeManutencao.__init__`, que recebe as duas
    leitoras em vez de importar `ocr` — injecao de leitora, nao monkeypatch.

    `pontuar_runs(recorte_bgr, moldes)` devolve `[(rotulo, score, margem), ...]`
    na ordem dos runs, ou `None`. Ele NAO aplica piso nem margem: quem decide e
    esta funcao, e aplicar o corte dentro do motor tornaria a medicao circular.
    """
    if recorte_bgr is None or getattr(recorte_bgr, "size", 0) == 0:
        return None
    try:
        pontuados = pontuar_runs(recorte_bgr, moldes)
    except Exception as erro:
        # Pelo mesmo motivo de `ocr._ler`: este predicado roda dentro do tick de
        # leitura, e uma excecao aqui pararia o scanner de olhar a party.
        log.debug("motor de glifo falhou neste recorte: %s", erro)
        return None
    if not pontuados:
        return None

    lido: list[str] = []
    for rotulo, score, distancia in pontuados:
        if rotulo not in DIGITOS:
            # O `+` do prefixo de encanto nao tem molde. Ele nao pode virar
            # digito nem ser pulado em silencio: pular faria `+6` e `6` terem a
            # mesma assinatura por caminhos diferentes.
            return None
        if score < piso or distancia < margem:
            return None
        lido.append(rotulo)
    return "".join(lido)


def agrupar(
    leitura: str | None,
    assinatura: str,
    catalogo: Iterable[EntradaDoCatalogo],
    corte: float,
    piso: float,
) -> ResultadoDoAgrupamento:
    """Em que serie esta leitura cai — ou por que ela nao cai em nenhuma.

    A ORDEM DAS DUAS DECISOES E O DESENHO INTEIRO:

    1. A TRAVA DE DIGITOS filtra os candidatos por igualdade EXATA da
       assinatura. `+6 X` nunca chega perto de `+4 X`, por mais alta que seja a
       similaridade (medida: 0,9677).
    2. A SIMILARIDADE decide so o resto, entre os que sobraram.

    Os tres desfechos:

        s >= corte          agrupa na serie existente
        piso <= s < corte   FAIXA CINZENTA: descarta, sem agrupar e sem criar
        s < piso            serie nova
        catalogo vazio      serie nova (a primeira nasce dai, e isso e legitimo)

    Empate EXATAMENTE no corte AGRUPA (`>=`); empate exatamente no piso DESCARTA
    (a faixa cinzenta e fechada embaixo). As duas bordas sao escolha, nao acaso:
    a faixa cinzenta existe para absorver a duvida, entao a duvida cabe nela.

    O DESEMPATE E DETERMINISTICO: maior score, e depois a ordem lexicografica da
    CHAVE — nunca a ordem de insercao do dicionario. Sem isso, duas execucoes
    sobre o mesmo frame poderiam gravar series diferentes conforme a ordem em
    que o catalogo foi carregado do disco.
    """
    chave_nova = chave_da_serie(leitura, assinatura)
    if chave_nova is None:
        return ResultadoDoAgrupamento(
            None, "leitura vazia: nem chave nem serie", False
        )

    pontuados = sorted(
        (
            (similaridade(leitura, entrada.nome), entrada.chave)
            for entrada in catalogo
            if entrada.assinatura == assinatura
        ),
        key=lambda par: (-par[0], par[1]),
    )

    if pontuados:
        melhor, chave = pontuados[0]
        if melhor >= corte:
            return ResultadoDoAgrupamento(
                chave,
                f"agrupada em {chave}: similaridade {melhor:.4f} >= corte {corte:.4f}",
                False,
            )
        if melhor >= piso:
            return ResultadoDoAgrupamento(
                None,
                f"FAIXA CINZENTA, descartada: similaridade {melhor:.4f} contra "
                f"{chave} fica entre o piso {piso:.4f} e o corte {corte:.4f}",
                False,
            )

    return ResultadoDoAgrupamento(
        chave_nova,
        (
            f"serie NOVA {chave_nova}: nenhum candidato de assinatura "
            f"{assinatura!r} chegou ao piso {piso:.4f}"
        ),
        True,
    )
