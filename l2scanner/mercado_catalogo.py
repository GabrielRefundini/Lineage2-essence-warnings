"""O agrupamento de nome de item do World Exchange, e o catalogo em disco.

Duas metades, e a ordem em que elas nasceram esta registrada porque explica o
desenho. Ate o 02-04 este modulo era SO de predicados: ele respondia "estas duas
leituras sao a mesma serie?" e "qual e a chave dela?", sem tocar em arquivo
nenhum. O 02-05 acrescentou a segunda metade — `Catalogo`, o arquivo duravel em
`.mercado/catalogo-de-nomes.csv`.

A SEPARACAO SOBREVIVEU A JUNCAO, E ELA E O QUE IMPORTA: as funcoes puras
(`agrupar`, `similaridade`, `chave_da_serie`, `assinatura_por_ocr`) continuam
sem saber que existe disco, e `Catalogo` continua sem saber decidir se duas
leituras sao a mesma serie. Cada metade da para afirmar sozinha.

A FRONTEIRA COM A FASE 3, QUE NAO SE MEXE
==========================================
**A Fase 2 escreve o catalogo de NOMES; a Fase 3 escreve o CSV de OBSERVACOES.**
Dois arquivos, dois donos, nenhum compartilhado. Este modulo nao conhece o nome
do arquivo da fase seguinte, e nao e por descuido: um segundo escritor para um
arquivo que ja tem dono e o modo de falha que a fronteira existe para impedir.

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

A TRAVA DE DIGITOS E DE GRADE, E POR QUE NENHUM CORTE A SUBSTITUI (D-03)
=========================================================================
As duas ultimas linhas da tabela sao o achado que decide o desenho: o MESMO
0,9630 teria de decidir coisas OPOSTAS — separar `Lv. 1` de `Lv. 3` e agrupar
`Lv. I` com `Lv. 1`. Nenhum corte escalar resolve isso, em nenhuma metrica de
distancia de edicao, e os tres casos aparecem juntos num frame real.

Por isso a sequencia de digitos do nome tem de bater EXATAMENTE antes de a
similaridade ser consultada. `+6 X` != `+4 X` e `Lv. 1` != `Lv. 3` por
CONSTRUCAO, nao por limiar. A similaridade decide so o resto do nome.

A LETRA DE GRADE ENTROU NA MESMA ASSINATURA EM 2026-09-01, pela mesma razao e
sem mecanismo novo: `B-grade Gemstone` e `C-grade Gemstone` valem 200.000 e
20.000 adena na loja de NPC do usuario e FUNDIAM (0,9375 >= corte 0,8947),
porque a trava de digitos nao via letra e a trava por palavra lia `B-grade` x
`C-grade` como um token com um caractere torto (0,8571, acima do piso 0,4500).
A medicao inteira, o custo e a decisao sobre as chaves antigas estao em
`assinatura_por_ocr`.

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

import csv
import difflib
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Sequence

from .config import RAIZ

log = logging.getLogger(__name__)

# Os dez digitos que a tela do jogo desenha. `str.isdigit()` NAO serve: ele
# devolve True para `²`, `٣` e mais uma centena de pontos Unicode que o motor de
# OCR pode cuspir num recorte ruim, e um deles virando assinatura criaria uma
# serie fantasma que ninguem consegue reproduzir olhando a tela.
DIGITOS = "0123456789"

# O sufixo que marca a LETRA DE GRADE, comparado em MINUSCULAS porque so a
# LETRA carrega identidade — `C-grade`, `C-Grade` e `C-GRADE` sao a mesma coisa.
#
# ELE NAO MORA NO `calibration.json`, PELA MESMA RAZAO DO `PISO_DO_RESTO`:
# `mercado_pagina` EXIGE as chaves de mercado presentes e PARA sem elas, entao
# uma chave nova obrigatoria deixaria o scanner MORTO no proximo arranque ate o
# usuario rodar a recalibracao. E este aqui nem e um numero medido: e como o
# jogo escreve a palavra.
SUFIXO_DA_GRADE = "-grade"

# O separador entre o slug do nome e a assinatura, DENTRO da chave. Ele existe
# para que a fusao de duas series seja impossivel na propria chave, e nao so no
# predicado: quem olhar `agathion-alpha-hunter-sealed#6` no CSV ve o encanto sem
# precisar do codigo. `#` porque nao aparece em nome de item nem colide com o
# separador `;` que a Fase 3 usa no CSV.
SEPARADOR_DA_ASSINATURA = "#"

# O piso da TRAVA POR PALAVRA (D-09). Abaixo dele o candidato e VETADO e nem
# chega a ser comparado pela similaridade do nome inteiro.
#
# A POPULACAO CONTRA A QUAL ELE FOI MEDIDO, E POR QUE E ESSA
# -----------------------------------------------------------
# Um par cuja similaridade do NOME INTEIRO ja fica ABAIXO do piso global vira
# serie nova sozinho — a trava nao muda o veredito dele. Entao a trava so
# precisa acertar nos pares que CHEGAM a faixa cinzenta (>= 0,8837). Medir sobre
# os 44 pares do catalogo inteiro misturaria 41 pares que a trava nem alcanca e
# produziria um piso calibrado contra a populacao errada.
#
# Medido em 2026-09-01 sobre `.mercado/catalogo-de-nomes.csv` do usuario mais o
# ruido de OCR que o repositorio NOMEIA por medicao (`Chll`/`Doll`, `Kng`/`King`,
# `Evolution`/`Ewlution`, `Hunteds`/`Hunter's`, `St«kings`/`Stockings`):
#
#     metrica                   pior AGRUPAR   pior SEPARAR       VAO
#     similaridade do nome         0,8889         0,8889       0,0000
#     similaridade do RESTO        0,5000         0,4000      +0,1000
#
#     piso do resto = (0,4000 + 0,5000) / 2 = 0,4500
#
# A primeira linha e a refutacao da recalibracao: o pior par que precisa agrupar
# e o pior que precisa separar sao o MESMO NUMERO, com quatro casas. Nao existe
# vao para calibrar, e nenhuma quantidade de material novo cria um.
#
# QUEM ENCOSTA NAS DUAS BORDAS, para a proxima medicao nao precisar redescobrir:
#     0,5000  `Chll` x `Doll`      PRECISA AGRUPAR (2 caracteres tortos em 4)
#     0,4000  `Earth` x `Water`    PRECISA SEPARAR (palavras inteiras distintas)
# A folga do lado de AGRUPAR e de 0,05, e ela e apertada porque `Doll` e curto:
# um token de 3 letras com 2 tortas daria 0,3333 e seria vetado. O erro nessa
# direcao cria SERIE NOVA, nunca fusao — e o lado barato do D-06.
#
# ELE NAO MORA NO `calibration.json`, E ISSO E DELIBERADO. `mercado_pagina`
# EXIGE as chaves de mercado presentes e PARA sem elas: uma chave nova
# obrigatoria deixaria o scanner morto no proximo start ate o usuario rodar a
# recalibracao. O numero entra aqui, com a medicao ao lado, e `agrupar` o aceita
# por nome para a ferramenta poder varre-lo. Move-lo para a calibracao depois
# nao exige reescrever nada.
PISO_DO_RESTO = 0.45


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


def _e_letra_ascii(caractere: str) -> bool:
    """Letra `A`-`Z` ou `a`-`z`, e mais nada. `str.isalpha()` NAO serve.

    Mesma razao de `DIGITOS` existir em vez de `str.isdigit()`: `isalpha()` e
    True para o `С` CIRILICO, que a tela desenha identico ao `C` latino. Um
    ponto Unicode parecido virando assinatura criaria uma serie que ninguem
    consegue reproduzir olhando o jogo.
    """
    return caractere.isascii() and caractere.isalpha()


def assinatura_por_ocr(nome: str | None) -> str:
    """Os digitos E as letras de grade do nome LIDO, na ordem. A trava de D-03.

    ORDEM DE APARICAO, e nao ordenacao: `Lv. 12` e `Lv. 21` sao series
    diferentes, e ordenar os digitos colapsaria as duas numa assinatura `12`
    unica — a fusao que a trava existe para impedir. A letra entra na mesma
    sequencia, pela mesma razao: `+5 B-grade Sword Lv. 3` da `5B3`.

    Nome sem digito e sem grade devolve `""`, que e uma assinatura legitima: e a
    de todo item sem encanto, sem nivel e sem grade. Ela so bate com outra `""`.

    A LETRA DE GRADE ENTROU EM 2026-09-01, E ELA E O D-03 ESTENDIDO (nao um
    quarto mecanismo)
    ====================================================================
    O DEFEITO, medido no catalogo real do usuario:

        B-grade Gemstone  x  C-grade Gemstone   ->  FUNDIA

    e na loja de NPC dele os dois valem **200.000 e 20.000 adena** — dez vezes
    de diferenca, com a mediana da serie fundida misturando precos sem relacao.

    POR QUE NENHUMA DAS DUAS TRAVAS DE ENTAO PEGAVA ESTE PAR:

        trava de DIGITOS (D-03)   assinatura `''` nos dois: ela nao via letra
        trava por PALAVRA (D-09)  `B-grade` x `C-grade` e 1 caractere torto em
                                  7 -> resto 0,8571, MUITO acima do piso
                                  0,4500. Ela via ruido onde havia identidade.
        similaridade do nome      0,9375 >= corte 0,8947  ->  funde

    A letra de grade carrega identidade EXATAMENTE como o digito de
    encantamento. Logo ela entra na assinatura comparada por igualdade EXATA,
    ANTES de a similaridade opinar — e nunca num limiar. `corte`, `piso` e
    `PISO_DO_RESTO` continuam intocados: o conserto e por MECANISMO.

    A LETRA TEM DE ESTAR SOLTA ANTES DO SUFIXO, e isso e a borda que importa:
    `Non-grade` NAO tem letra de grade, porque o `n` vem colado num `No`. Sem
    essa checagem, toda palavra terminada em letra seguida de `-grade`
    entregaria a ultima letra dela como se fosse a grade.

    A CAIXA E DOBRADA PARA MAIUSCULA, e a escolha e segura por CONSTRUCAO: nao
    existe par de grades do jogo que difira so na caixa, entao dobrar nao pode
    FUNDIR duas grades distintas. O precedente e o `_slug`, que ja dobra a caixa
    do corpo da chave — `D-grade Crystal` e `D-grade crystal` ja produziam UMA
    chave antes disto. Maiuscula, e nao minuscula, para a letra saltar aos olhos
    dentro da chave: `b-grade-gemstone#B`.

    NAO HA LISTA DE GRADES VALIDAS (`D`/`C`/`B`/`A`/`S`), DE PROPOSITO. Uma
    lista viraria divida na proxima grade que o jogo adicionar, e o custo de
    NAO ter e barato: um `O-grade` lido no lugar de `D-grade` cria SERIE NOVA,
    que e o lado reversivel do D-06. Uma lista, ao recusar o desconhecido,
    empurraria para `''` — que e o lado da FUSAO.

    O CUSTO, MEDIDO E NAO ESTIMADO: se uma escala de OCR ler `C-grade` e a outra
    comer o sufixo, as duas assinaturas discordam e a linha MORRE — o mesmo
    conflito D-02/D-03 que o paragrafo abaixo ja registra para digitos. A
    evidencia de que o sufixo sobrevive ao OCR na pratica esta no `.mercado/` do
    usuario: `protecting-scroll-enchant-c-grade-armor#` acumulou 280
    avistamentos numa chave so, e `scroll-enchant-d-grade-weapon#` outros 40.
    Sufixo comido devolve `""`, que e o comportamento ANTERIOR a esta mudanca —
    o conserto degrada para o estado de ontem, nunca para uma assinatura
    inventada.

    A CHAVE DA SERIE MUDA PARA ITEM COM GRADE, E A DECISAO ESTA REGISTRADA. As
    duas series acima ganham chave NOVA (`...#C` e `...#D`) e as antigas, de
    assinatura `''`, param de casar com elas em `agrupar` — sao filtradas antes,
    na igualdade exata. As duas CONVIVEM: o dado velho fica inteiro no CSV do
    usuario e o dado novo nasce correto. NADA reescreve o `.mercado/` dele; uma
    migracao automatica teria de decidir por ele que duas chaves sao o mesmo
    item, que e exatamente o julgamento que o D-06 mantem fora do programa.

    ATENCAO, E ESTA E A MEDICAO QUE A TASK 2 DO 02-03 POE NA MESA: aplicada a
    leitura de OCR, esta funcao devolve `""` para `Hardin's Soul Crystal Lv. I`
    e `"1"` para `... Lv. 1`. As duas nao batem, as duas escalas caem em series
    diferentes, e a linha morre — exatamente o ruido que D-02 foi escrito para
    absorver. O conflito e real, esta medido, e nao esta escondido aqui dentro.
    """
    if not nome:
        return ""
    marcas: list[str] = []
    for posicao, caractere in enumerate(nome):
        if caractere in DIGITOS:
            marcas.append(caractere)
            continue
        if not _e_letra_ascii(caractere):
            continue
        if posicao and _e_letra_ascii(nome[posicao - 1]):
            # `Non-grade`: o `n` esta colado num `No`, entao nao e grade.
            continue
        depois = nome[posicao + 1 : posicao + 1 + len(SUFIXO_DA_GRADE)]
        if depois.lower() != SUFIXO_DA_GRADE:
            continue
        marcas.append(caractere.upper())
    return "".join(marcas)


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


def _resto_apos_tokens_iguais(a: str, b: str) -> tuple[list[str], list[str]]:
    """Os tokens de cada lado depois de remover os que sao IDENTICOS nos dois.

    MULTICONJUNTO, e nao conjunto: `Coin Coin Azul` contra `Coin Azul` tem de
    deixar UM `Coin` sobrando do lado esquerdo. Com conjunto os dois lados
    ficariam vazios e o par viraria identico, que e a fusao que a trava existe
    para impedir.

    A ORDEM DE APARICAO E PRESERVADA nos dois lados. Ela nao muda o veredito de
    `difflib` na maioria dos casos, mas ordenar aqui faria duas execucoes sobre
    o mesmo frame poderem comparar strings diferentes — o mesmo motivo pelo qual
    `assinatura_por_ocr` nao ordena os digitos.
    """
    resto_a: list[str] = []
    sobra_b = b.split()
    for token in a.split():
        if token in sobra_b:
            sobra_b.remove(token)
        else:
            resto_a.append(token)
    return resto_a, sobra_b


def similaridade_do_resto(a: str | None, b: str | None) -> float:
    """A similaridade do que SOBRA depois que as palavras identicas saem. Nunca levanta.

    A TRAVA POR PALAVRA (D-09), e ela e a trava de digitos do D-03 um nivel
    acima: o que bate por igualdade EXATA sai da conta ANTES, e a similaridade
    decide so o RESTO. La o que sai e a sequencia de digitos; aqui sao os TOKENS.

    POR QUE A SIMILARIDADE DO NOME INTEIRO NAO PODE DECIDIR SOZINHA
    ================================================================
    `difflib.ratio()` e uma RAZAO, entao ela dilui a diferenca no prefixo
    compartilhado. Medido, e este par de numeros e o defeito inteiro:

        'Hunteds Tunic'     x  "Hunter's Tunic"     = 0,8889   MESMO item
        '...C-grade Weapon' x  '...C-grade Armor'   = 0,8889   itens DIFERENTES

    O MESMO numero, com quatro casas, precisa decidir coisas OPOSTAS. A
    refutacao e ARITMETICA e nao empirica: `Protecting Scroll: Enchant C-grade `
    sao 34 caracteres iguais, entao uma PALAVRA trocada (6 caracteres) vale o
    mesmo que UM caractere torto num nome de 13. **Nenhum par (piso, corte)
    sobre esta metrica separa os dois casos**, por mais material que se junte.

    O resto e escala-livre em relacao ao prefixo, e ai o vao aparece:

        resto('...C-grade Weapon', '...C-grade Armor')  ->  'Weapon' x 'Armor'
        resto('Hunteds Tunic',     "Hunter's Tunic")    ->  'Hunteds' x "Hunter's"

    `Armor` e `Weapon` sao TOKENS INTEIROS diferentes; `St«kings` x `Stockings` e
    UM token com 2 caracteres tortos. A separacao passa a ser por MECANISMO.

    VAZIO DOS DOIS LADOS E 1,0, E NAO 0,0. `similaridade` devolve 0,0 para vazio
    contra vazio de proposito, e herdar esse 0,0 aqui vetaria uma leitura contra
    ela mesma — exatamente o oposto do que a trava faz.

    VAZIO DE UM LADO SO E 0,0, por heranca de `similaridade`, e isso e o
    veredito CERTO: `Common Aztac` contra `Common Aztac M. Def. +200` deixa `''`
    contra `'M. Def. +200'`, e os dois precisam separar (D-05, o par que
    derrubou o `WRatio` com corte 88 fundindo-os a 90,00).
    """
    if not a or not b:
        return 0.0
    resto_a, resto_b = _resto_apos_tokens_iguais(a, b)
    if not resto_a and not resto_b:
        return 1.0
    return similaridade(" ".join(resto_a), " ".join(resto_b))


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

    ESTA FUNCAO NAO E A FONTE DA ASSINATURA, E O REGISTRO DE POR QUE FICA AQUI
    ==========================================================================
    Em 2026-08-30 o usuario escolheu, no portao do 02-03, que a assinatura da
    chave da serie vem do OCR (`assinatura_por_ocr`). Esta funcao FOI MEDIDA e
    perdeu, e o numero que a derrubou e o seguinte: com a posicao do digito dada
    DE FORA ela acerta 9 de 9 contra o gabarito de encanto
    `+6/+4/+2/+7/(nenhum)/+5/+7/+5/+7/+6`; com a regra que a producao teria de
    usar — cada run sozinho, digito quando passa no piso e na margem — ela acerta
    **0 de 10** e devolve `7655` onde a resposta e `6`.

    A CAUSA: os 13 moldes do `calibration.json` sao `0`-`9`, `,`, `XM Coin` e
    `Adena`. NAO HA MOLDE DE LETRA, entao o conjunto nao tem classe de rejeicao e
    toda letra e forcada sobre o digito mais parecido. O que sai nao e uma
    sequencia de digitos: e uma impressao digital do nome, que muda conforme
    quais letras calharam de passar no piso naquele frame (medido: `Adena`
    duplicou em `adena#55` e `adena#555`).

    O CAMINHO DE VOLTA, COM OS DOIS NUMEROS, PARA NAO PRECISAR REMEDIR
    ------------------------------------------------------------------
    A rota nao e impossivel — ela e so INCOMPLETA, e falta exatamente UM numero.
    Medido na mesma varredura, sobre 60 paginas distintas e 427 linhas da COLUNA
    DO NOME, com cada run reclassificado na propria faixa:

        VERDADEIRO (o digito de um prefixo `+N `)   n=28   min 0,8510   max 0,9439
        FALSO      (todo run aprovado num nome
                    em que nenhuma escala viu digito)  n=451  min 0,4752  max 0,6947

    **Ha vao: +0,1563 entre 0,6947 e 0,8510.** Um piso PROPRIO da coluna do nome,
    medido nessa faixa, separaria digito de letra e devolveria a esta rota os
    95,32% que ela mostrou (contra 82,44% da escolhida) — agora com chave
    honesta. O piso que existe hoje, `mercado_limiar_de_leitura_de_glifo`
    = 0,4698, NAO serve: ele foi medido sobre as colunas de NUMERO, onde nao ha
    letra para rejeitar, e por isso deixa passar o `5` que o motor le dentro de
    `Agathion Alpha Hunter Sealed`.

    Quem for medir esse piso: a chave seria nova (algo como
    `mercado_limiar_de_digito_no_nome`), e a decisao da FONTE volta a ser um
    portao — trocar a fonte orfana toda serie ja gravada no CSV.
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
    *,
    piso_do_resto: float = PISO_DO_RESTO,
) -> ResultadoDoAgrupamento:
    """Em que serie esta leitura cai — ou por que ela nao cai em nenhuma.

    A ORDEM DAS TRES DECISOES E O DESENHO INTEIRO:

    1. A TRAVA DE DIGITOS E DE GRADE filtra os candidatos por igualdade EXATA da
       assinatura. `+6 X` nunca chega perto de `+4 X`, por mais alta que seja a
       similaridade (medida: 0,9677), e `B-grade Gemstone` nunca chega perto de
       `C-grade Gemstone` (medida: 0,9375) — os dois valem dez vezes um do
       outro na loja de NPC.
    2. A TRAVA POR PALAVRA (D-09) veta os candidatos cujo RESTO — o que sobra
       depois de remover as palavras identicas — nao chega a `piso_do_resto`.
       `...C-grade Weapon` nunca chega perto de `...C-grade Armor`, porque o
       resto e `Weapon` contra `Armor` (0,1818), por mais que o nome inteiro
       diga 0,8889.
    3. A SIMILARIDADE DO NOME INTEIRO decide so o resto, entre os que sobraram.

    AS DUAS TRAVAS SAO A MESMA IDEIA EM DOIS NIVEIS: o que bate por igualdade
    EXATA sai da conta ANTES, e a similaridade decide so o que sobrou. No D-03
    o que sai e a sequencia de DIGITOS E LETRAS DE GRADE; no D-09 sao as
    PALAVRAS INTEIRAS.

    O `...C-grade Weapon` x `...C-grade Armor` continua sendo separado pela
    trava por PALAVRA, e nao pela letra: a grade e a MESMA nos dois. Os dois
    mecanismos nao se substituem, e cada par cai no seu.

    A TRAVA POR PALAVRA SO REMOVE CANDIDATO, NUNCA ACRESCENTA
    ----------------------------------------------------------
    Isso e propriedade de CONSTRUCAO, e nao resultado de teste: ela e um filtro
    sobre a lista de candidatos, entao nenhum par que hoje nao funde pode passar
    a fundir por causa dela. E o que a deixa honrar a assimetria do D-06 —
    fusao no CSV e irreversivel, descarte e serie nova nao sao. O caminho que
    ela abre e sempre da FAIXA CINZENTA para a SERIE NOVA, nunca para a fusao.

    O DEFEITO QUE ELA CONSERTA, com o numero que o nomeia
    ------------------------------------------------------
    Sessao do usuario de 2026-09-01 04:32: 10 de 10 linhas recusadas por
    `faixa-cinzenta`, com as DUAS escalas de OCR concordando e lendo o nome
    CERTO. `Protecting Scroll: Enchant C-grade Weapon` dava 0,8889 contra o
    `...C-grade Armor` que ja estava no catalogo, e 0,8837 <= 0,8889 < 0,8947.
    Enquanto o `Armor` existisse, o `Weapon` NUNCA agrupava e NUNCA criava
    serie. Nao era transitorio, e a faixa que o engoliu tem 0,011 de largura.

    Recalibrar nao resolvia, e a refutacao esta em `similaridade_do_resto`: o
    MESMO 0,8889 e "mesmo item" em `'Hunteds Tunic'` x `"Hunter's Tunic"`.

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

    mesma_assinatura = [
        entrada for entrada in catalogo if entrada.assinatura == assinatura
    ]
    candidatos = [
        entrada
        for entrada in mesma_assinatura
        if similaridade_do_resto(leitura, entrada.nome) >= piso_do_resto
    ]
    vetados = len(mesma_assinatura) - len(candidatos)

    pontuados = sorted(
        ((similaridade(leitura, entrada.nome), entrada.chave) for entrada in candidatos),
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

    # O motivo diz quantos candidatos a TRAVA POR PALAVRA vetou, e nao so que
    # ninguem chegou ao piso. Sem esse numero, "serie nova" fica indistinguivel
    # entre "o catalogo nao tinha nada parecido" e "tinha, e a trava mordeu" —
    # e sao as duas leituras que o log rotativo precisa separar depois do farm.
    porque_vetados = (
        f", {vetados} vetado(s) pela trava por palavra (piso do resto "
        f"{piso_do_resto:.4f})"
        if vetados
        else ""
    )
    return ResultadoDoAgrupamento(
        chave_nova,
        (
            f"serie NOVA {chave_nova}: nenhum candidato de assinatura "
            f"{assinatura!r} chegou ao piso {piso:.4f}{porque_vetados}"
        ),
        True,
    )


# ===========================================================================
# A METADE DE ARQUIVO (02-05): o catalogo duravel
# ===========================================================================

# `.mercado/` e o TERCEIRO diretorio-ponto de estado local duravel deste
# repositorio, ao lado de `.loot/` e `.agenda/`, e ele entra no `.gitignore`
# pela mesma razao que eles: versionar misturaria a estatistica de maquinas
# diferentes. O caminho vem SEMPRE da RAIZ do projeto e NUNCA de entrada do
# usuario — um caminho vindo de fora seria uma travessia de diretorio de graca,
# e nada aqui precisa dessa liberdade.
PASTA_DO_MERCADO = RAIZ / ".mercado"
ARQUIVO_DO_CATALOGO = "catalogo-de-nomes.csv"

# PONTO-E-VIRGULA, E NAO VIRGULA, e a escolha vale por dois: a Fase 3 herda
# este dialeto. A decisao travada da exibicao usa VIRGULA DECIMAL (`62,00`), e
# um CSV separado por virgula colapsaria a planilha inteira numa coluna so no
# instante em que o usuario abrisse o arquivo no Sheets.
SEPARADOR = ";"

COLUNAS = ("chave", "nome_exibido", "primeira_vez", "ultima_vez", "avistamentos")


@dataclass
class SerieDeNome:
    """Uma serie do catalogo, com a estatistica que o usuario julga no Sheets.

    `chave` e a identidade e nunca muda. `nome_exibido` e ROTULO: o usuario
    pode corrigi-lo a mao no Sheets, e por isso ele volta como entrada NAO
    CONFIAVEL na releitura seguinte.

    `avistamentos` e `primeira_vez` existem por causa de D-08: nome novo entra
    DIRETO como serie nova, sem quarentena, porque a quarentena esconderia a
    primeira aparicao — que e justamente o evento que o usuario quer ver. A
    contagem e o que deixa ele julgar a serie nova sem que o programa julgue
    por ele.
    """

    chave: str
    nome_exibido: str
    primeira_vez: datetime
    ultima_vez: datetime
    avistamentos: int


class Catalogo:
    """O catalogo de nomes em `.mercado/catalogo-de-nomes.csv`.

    A FRONTEIRA COM A FASE 3, ESCRITA PARA NAO SE PERDER
    -----------------------------------------------------
    **A Fase 2 escreve o catalogo de NOMES; a Fase 3 escreve o CSV de
    OBSERVACOES.** Dois arquivos, dois donos, nenhum compartilhado. A Fase 3 LE
    a chave que esta fase produziu e NUNCA escreve aqui; se ela encontrar uma
    chave que nao esta no catalogo, isso e erro de programa e nao caso de uso.

    NAO TEM PODA, DE PROPOSITO: estatistica de item e para sempre, igual ao
    `.loot/`. O volume e de milhares de linhas, nao de milhoes (T-02-28).

    ELE NAO MORA NO `calibration.json`, E ISSO E D-07: aquele arquivo e
    reescrito INTEIRO pela ferramenta de calibracao, e o catalogo e dado
    ACUMULADO — sumiria na primeira recalibracao.
    """

    def __init__(self, pasta: Path) -> None:
        # A pasta chega no construtor, e nao derivada aqui dentro, pelo mesmo
        # motivo de `RegistroDeLoot.__init__`: e o que permite ao teste apontar
        # para `tmp_path` sem nunca tocar a `.mercado/` do usuario, que e dado
        # acumulado e sem desfazer. Producao passa `PASTA_DO_MERCADO`.
        self._pasta = pasta
        self._pasta.mkdir(parents=True, exist_ok=True)
        self.series: dict[str, SerieDeNome] = {}
        self.carregar()

    @property
    def arquivo(self) -> Path:
        return self._pasta / ARQUIVO_DO_CATALOGO

    # -- leitura ------------------------------------------------------------

    def carregar(self) -> dict[str, SerieDeNome]:
        """Le o arquivo. Ausente -> vazio. Linha ruim -> so ela cai, com aviso.

        A REGRA E LITERAL E ELA E A MITIGACAO DE T-02-22: descartar a linha
        malformada com aviso, e NUNCA tratar o arquivo inteiro como corrompido.
        Um append interrompido trunca a ultima linha, e essa e a mesma familia
        do FUND-01 — o dado parcial nao pode virar dado plausivel. Mas o resto
        do arquivo esta inteiro, e jogar fora meses de estatistica por causa de
        uma linha seria trocar uma perda pequena por uma total.

        Catalogo inexistente carrega VAZIO e nao levanta: a primeira execucao
        numa maquina limpa e um estado legitimo, nao um erro.

        O `newline=""` nao e enfeite: sem ele o modulo `csv` nao consegue
        remontar um campo que contem quebra de linha, e um `nome_exibido`
        colado do Sheets traz uma junto mais vezes do que se imagina.
        """
        self.series = {}
        try:
            with self.arquivo.open("r", encoding="utf-8", newline="") as fonte:
                linhas = list(csv.reader(fonte, delimiter=SEPARADOR))
        except FileNotFoundError:
            return self.series
        except OSError as erro:
            log.warning(
                "Nao consegui ler o catalogo de nomes em %s (%s). A leitura "
                "segue com o catalogo VAZIO desta sessao; o arquivo em disco "
                "nao foi tocado.",
                self.arquivo,
                erro,
            )
            return self.series

        for numero, campos in enumerate(linhas, start=1):
            if not campos or all(not campo.strip() for campo in campos):
                continue
            if numero == 1 and tuple(campo.strip() for campo in campos) == COLUNAS:
                # O cabecalho. Ele e conveniencia para o olho humano, nao a
                # identidade do arquivo — um arquivo sem ele ainda carrega.
                continue
            serie = self._serie_da_linha(campos, numero)
            if serie is None:
                continue
            self.series[serie.chave] = serie
        return self.series

    def _serie_da_linha(
        self, campos: list[str], numero: int
    ) -> SerieDeNome | None:
        """Uma linha -> serie, ou `None` com aviso que NOMEIA a linha.

        O aviso diz o numero da linha e o que ela tinha porque a forense deste
        projeto acontece DEPOIS do farm, com o log na mao: sem o numero, o
        usuario nao acha a linha para consertar no Sheets.
        """

        def recusar(motivo: str) -> None:
            log.warning(
                "Catalogo de nomes, linha %d DESCARTADA (%s): %r. As demais "
                "linhas do arquivo carregaram normalmente — uma linha ruim "
                "nunca condena o arquivo inteiro.",
                numero,
                motivo,
                SEPARADOR.join(campos),
            )

        if len(campos) != len(COLUNAS):
            recusar(f"esperava {len(COLUNAS)} campos, veio {len(campos)}")
            return None

        chave, nome, primeira, ultima, avistamentos = campos
        chave = chave.strip()
        if not chave:
            recusar("chave vazia")
            return None
        try:
            nascimento = datetime.fromisoformat(primeira.strip())
            visto = datetime.fromisoformat(ultima.strip())
        except ValueError:
            recusar("data que nao e ISO-8601")
            return None
        try:
            contagem = int(avistamentos.strip())
        except ValueError:
            recusar("avistamentos que nao e inteiro")
            return None
        if contagem < 1:
            recusar("avistamentos menor que 1")
            return None

        return SerieDeNome(
            chave=chave,
            nome_exibido=nome,
            primeira_vez=min(nascimento, visto),
            ultima_vez=max(nascimento, visto),
            avistamentos=contagem,
        )

    # -- escrita ------------------------------------------------------------

    def registrar(
        self, chave: str | None, nome_exibido: str, agora: datetime
    ) -> SerieDeNome | None:
        """Um avistamento. Nome novo vira serie NOVA na hora, sem quarentena.

        `None` quando nao ha chave: `chave_da_serie` ja devolve `None` para
        leitura vazia, e uma chave vazia que virasse linha do CSV seria
        referenciada pela Fase 3 como se fosse item.

        `primeira_vez` e MIN e `ultima_vez` e MAX, e nao "a que chegou por
        ultimo": horario de verao e ajuste de NTP andam para tras de verdade, e
        um tick com relogio atrasado nao pode fazer a serie parecer mais nova
        nem mais velha do que o material prova.
        """
        if not chave:
            return None
        serie = self.series.get(chave)
        if serie is None:
            serie = SerieDeNome(
                chave=chave,
                nome_exibido=nome_exibido,
                primeira_vez=agora,
                ultima_vez=agora,
                avistamentos=1,
            )
            self.series[chave] = serie
            return serie
        serie.nome_exibido = nome_exibido
        serie.primeira_vez = min(serie.primeira_vez, agora)
        serie.ultima_vez = max(serie.ultima_vez, agora)
        serie.avistamentos += 1
        return serie

    def gravar(self) -> None:
        """Reescreve o catalogo INTEIRO, de forma ATOMICA.

        O precedente e `loot.py:264-281`: um `.tmp-<pid>` AO LADO do destino,
        seguido de `os.replace`. O temporario NAO vai para o `%TEMP%` porque
        `os.replace` entre volumes diferentes nao e atomico e no Windows nem
        funciona — a razao ja esta escrita por extenso em `calibracao.py:433-441`.
        O pid no nome impede uma segunda instancia de atropelar o tmp da
        primeira. Ou fica o arquivo antigo INTEIRO, ou o novo INTEIRO, nunca
        meio (T-02-24).

        Reescrever tudo em vez de dar append e o que permite `avistamentos`
        subir sem o arquivo crescer uma linha por avistamento — e o que faz a
        ORDEM ser estavel: as linhas saem ordenadas pela CHAVE, e nao pela
        ordem de insercao do dicionario, para que duas execucoes sobre o mesmo
        material produzam o mesmo arquivo byte a byte.

        O modo e `"w"` com `newline=""`: `"w"` porque o destino aqui e o
        TEMPORARIO, que acabou de ganhar um nome com o pid dentro e nao pode
        existir de antes; `newline=""` porque o modulo `csv` escreve o seu
        proprio terminador e deixar o Python traduzir por cima produziria `\r\r\n`
        no Windows.
        """
        temporario = self._pasta / f"{ARQUIVO_DO_CATALOGO}.tmp-{os.getpid()}"
        with temporario.open("w", encoding="utf-8", newline="") as destino:
            escritor = csv.writer(destino, delimiter=SEPARADOR)
            escritor.writerow(COLUNAS)
            for chave in sorted(self.series):
                serie = self.series[chave]
                escritor.writerow(
                    (
                        serie.chave,
                        serie.nome_exibido,
                        serie.primeira_vez.isoformat(),
                        serie.ultima_vez.isoformat(),
                        serie.avistamentos,
                    )
                )
        os.replace(temporario, self.arquivo)

    # -- a ponte com os predicados -----------------------------------------

    def entradas(self) -> dict[str, EntradaDoCatalogo]:
        """As series no formato que `agrupar` consome.

        Duas formas para a mesma coisa e um cheiro, e aqui ele e deliberado:
        `SerieDeNome` carrega a ESTATISTICA (que so o arquivo precisa) e
        `EntradaDoCatalogo` carrega a IDENTIDADE (que so o predicado precisa).
        Fundir as duas obrigaria o predicado puro a conhecer datas e contagens
        para responder "estas duas leituras sao a mesma serie?".
        """
        return {
            chave: EntradaDoCatalogo(
                chave=chave,
                nome=serie.nome_exibido,
                assinatura=assinatura_da_chave(chave),
            )
            for chave, serie in self.series.items()
        }


def assinatura_da_chave(chave: str) -> str:
    """A assinatura de digitos que `chave_da_serie` anexou depois do `#`.

    Ela e RECUPERADA da chave em vez de recalculada a partir do nome, e a
    diferenca importa: o `nome_exibido` e editavel pelo usuario no Sheets, e
    recalcular a assinatura a partir de um nome corrigido a mao mudaria a
    identidade de uma serie que ja esta gravada. A chave e imutavel; o rotulo
    nao e.
    """
    _corpo, _sep, assinatura = chave.rpartition(SEPARADOR_DA_ASSINATURA)
    return assinatura
