"""A ferramenta que FUNDE as chaves de serie que o conserto da grade partiu.

O QUE ACONTECEU, E O NUMERO E MEDIDO NO ARQUIVO REAL
=====================================================
O quick `260901-g7k` fez a letra de grade entrar na assinatura de identidade
(`assinatura_por_ocr`, em `l2scanner/mercado_catalogo.py`). Isso estava certo e
valia caro: na loja de NPC do usuario, `B-grade Gemstone` e `C-grade Gemstone`
valem 200.000 e 20.000 adena — dez vezes de diferenca — e ate aquele dia as duas
series FUNDIAM numa mediana so.

A decisao registrada la foi que as chaves novas **convivem** com as antigas, sem
reescrever o `.mercado/`: dado velho inteiro, dado novo correto. O custo dessa
decisao, medido no arquivo do usuario em 2026-09-01:

    Protecting Scroll: Enchant C-grade Armor
      protecting-scroll-enchant-c-grade-armor#     15 linhas   (chave VELHA)
      protecting-scroll-enchant-c-grade-armor#C     5 linhas   (chave NOVA)

    Scroll: Enchant D-grade Weapon
      scroll-enchant-d-grade-weapon#                5 linhas
      scroll-enchant-d-grade-weapon#D               5 linhas

A analise roda so sobre a chave NOVA. As medianas que ele viu diziam `n=5`
havendo 20 observacoes do mesmo item no arquivo. Nao e dado perdido — e dado
ORFAO, e o unico jeito de ele voltar a contar e alguem juntar as duas chaves.

POR QUE UMA FERRAMENTA, E NUNCA O PROGRAMA
===========================================
`mercado_registro` NUNCA reescreve o CSV do usuario, e isso e decisao da Fase 3.
Migracao automatica sobre um arquivo que o usuario edita a mao e importa no
Sheets e exatamente como se corrompe dado calado — a mesma objecao que o
`conferir_o_cabecalho` daquele modulo ja escreve por extenso (D-11, D-12).

O precedente e `tools/medir_oclusao.py`: dry-run por PADRAO, `--gravar` para
persistir, load-mutate-save. O usuario decide, com backup, e nada acontece sem
ele pedir.

A REGRA QUE NAO PODE SER AFROUXADA
===================================
**Funde APENAS quando o `nome_exibido` das duas chaves e IDENTICO.** Isso e
mecanico e nao envolve julgamento. Nunca por similaridade — `similaridade` e
`similaridade_do_resto` existem no catalogo para decidir se duas LEITURAS sao a
mesma serie, e aquele lado e reversivel (serie nova nasce, o usuario ve). Aqui e
o lado irreversivel: fundir no CSV apaga linha. Julgamento sobre identidade de
item e justamente o que o D-06 mantem FORA do programa.

E **a chave com letra de grade VENCE**, porque ela e a que a analise le hoje. Se
o grupo tiver mais de uma candidata com letra, ou nenhuma, o grupo e RECUSADO e
o caso e nomeado — a ferramenta nao escolhe.

AS TRES DECISOES QUE EU (o executor) TOMEI SOZINHO, E POR QUE
==============================================================
O usuario autorizou execucao autonoma e nao estava acordado para decidir. Nos
tres pontos abaixo eu escolhi o lado MAIS CAUTELOSO, e registro aqui que a
escolha foi minha e nao dele:

1. **LINHA QUE NAO VALIDA RECUSA O ARQUIVO INTEIRO, em vez de cair sozinha.**
   Na LEITURA, o D-14 manda a linha ruim cair sozinha com aviso e o resto
   carregar — e esta certo, porque leitura nao destroi nada. Aqui e ESCRITA: a
   ferramenta reescreve o arquivo, e uma linha que ela nao consegue interpretar e
   uma linha que ela nao consegue PROMETER preservar byte a byte (o `csv.writer`
   pode reaspar um campo de forma diferente da original). Entao nada e escrito, a
   linha e NOMEADA, e o usuario conserta e roda de novo. E a mesma inversao que
   `mercado_registro` ja fez com o cabecalho em relacao ao `mercado_catalogo`.

2. **DUPLICATA QUE JA EXISTIA SOB UMA CHAVE SO E PRESERVADA.** So sai de cena a
   linha que colide DEPOIS da fusao com uma linha de OUTRA chave de origem —
   essa duplicata a fusao criou, e desfaze-la e o trabalho. Uma duplicata que ja
   estava no arquivo sob a mesma chave e dado do usuario, anterior a ferramenta,
   e apaga-la seria trabalho que ninguem pediu. Ela e CONTADA e RELATADA, nunca
   removida.

3. **OU OS DOIS ARQUIVOS SAO REESCRITOS, OU NENHUM.** Um `observacoes.csv`
   fundido ao lado de um `catalogo-de-nomes.csv` intacto deixaria linhas
   apontando para uma chave que o catalogo ainda lista como duas — pior do que o
   estado de partida, porque o estado de partida pelo menos e consistente.

O QUE ELA GARANTE NA SAIDA
===========================
- **O cabecalho e CONTRATO** e sai BYTE A BYTE igual ao que entrou: a primeira
  linha fisica do arquivo lido e copiada literalmente, nunca re-serializada.
- **O arquivo TERMINA EM QUEBRA DE LINHA** (D-17), e isso e AFIRMADO sobre o
  texto pronto, antes do `os.replace`. Para o `observacoes.csv` a afirmacao e
  feita pelo MESMO portao que o leitor vai atravessar depois
  (`conferir_o_terminador` e `conferir_o_cabecalho`, importados) — nao por uma
  segunda implementacao que poderia divergir dele.
- **Backup antes de escrever**, byte a byte, com carimbo no nome, na propria
  pasta. Nenhum backup e apagado nem sobrescrito: se o nome ja existir, a
  ferramenta PARA.
- **Escrita atomica** por `.tmp-<pid>` ao lado do destino e `os.replace`, o
  mesmo desenho de `Catalogo.gravar`. Ou fica o arquivo antigo INTEIRO, ou o
  novo INTEIRO, nunca meio.
- **A ORDEM das linhas e preservada** e as linhas nao envolvidas na fusao saem
  com os campos que entraram. So a linha de destino e recalculada.

Uso:

    python tools/fundir_chaves_de_serie.py --pasta .mercado
    python tools/fundir_chaves_de_serie.py --pasta .mercado --gravar

Sem `--gravar` nada e tocado: a ferramenta mostra o que faria e sai.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from l2scanner.mercado_catalogo import (  # noqa: E402
    ARQUIVO_DO_CATALOGO,
    PASTA_DO_MERCADO,
    SEPARADOR,
    SEPARADOR_DA_ASSINATURA,
    assinatura_da_chave,
)
from l2scanner.mercado_catalogo import COLUNAS as COLUNAS_DO_CATALOGO  # noqa: E402
from l2scanner.mercado_registro import (  # noqa: E402
    ARQUIVO_DE_OBSERVACOES,
    ContratoDoArquivoQuebrado,
    chave_dos_campos,
    conferir_o_cabecalho,
    conferir_o_terminador,
)
from l2scanner.mercado_registro import COLUNAS as COLUNAS_DE_OBSERVACOES  # noqa: E402


# Os codigos de saida, NOMEADOS. Um numero cru no `return` obriga quem le o
# roteiro humano a contar linhas para descobrir o que 4 quer dizer.
SAIDA_OK = 0
SAIDA_SEM_PASTA = 2
SAIDA_CONTRATO_QUEBRADO = 3
SAIDA_BACKUP_EXISTENTE = 4

FORMATO_DO_CARIMBO = "%Y%m%d-%H%M%S"


# ===========================================================================
# A METADE PURA: sem disco, sem relogio
# ===========================================================================


@dataclass(frozen=True)
class Fusao:
    """Um grupo aprovado: as origens entram no destino."""

    corpo: str
    destino: str
    origens: tuple[str, ...]


@dataclass(frozen=True)
class Recusa:
    """Um grupo (ou uma chave) que a ferramenta NAO funde, e o motivo por extenso.

    O motivo vem em TEXTO e nao em codigo porque ele e impresso para o usuario,
    que vai olhar o CSV no Sheets logo depois. "recusado" sozinho nao conserta
    nada; "os nomes exibidos diferem: 'X' contra 'Y'" conserta.
    """

    corpo: str
    chaves: tuple[str, ...]
    motivo: str


@dataclass(frozen=True)
class Plano:
    fusoes: tuple[Fusao, ...]
    recusas: tuple[Recusa, ...]

    @property
    def mapa(self) -> dict[str, str]:
        """origem -> destino, achatado, que e o que a aplicacao consome."""
        de_para: dict[str, str] = {}
        for fusao in self.fusoes:
            for origem in fusao.origens:
                de_para[origem] = fusao.destino
        return de_para


def corpo_da_chave(chave: str) -> str:
    """O slug antes do `#`. Chave SEM `#` e o proprio corpo, e isso e proposital.

    `chave_da_serie` sempre anexa o separador, entao uma chave sem ele nao veio
    deste programa. Devolver a chave inteira faz dela um grupo de UM — e um grupo
    de um nunca funde. Se em vez disso ela caisse num corpo vazio, TODAS as
    chaves estranhas do arquivo cairiam no MESMO grupo e passariam a se olhar
    como candidatas umas das outras, que e o oposto do que se quer.
    """
    corpo, separador, _assinatura = chave.rpartition(SEPARADOR_DA_ASSINATURA)
    return corpo if separador else chave


def tem_letra_de_grade(chave: str) -> bool:
    """A assinatura da chave carrega alguma letra ASCII?

    A regra e a mesma de `assinatura_por_ocr`, que so acrescenta `.upper()` de
    caractere ASCII alfabetico — nunca um `С` cirilico, nunca um digito no lugar
    da letra. Ler a assinatura da CHAVE, e nao recalcula-la do nome, e o que
    `assinatura_da_chave` ja documenta: o `nome_exibido` e editavel a mao no
    Sheets e a chave nao e.
    """
    return any(c.isascii() and c.isalpha() for c in assinatura_da_chave(chave))


def planejar(
    nomes_por_chave: Mapping[str, str],
    chaves_observadas: Iterable[str] = (),
) -> Plano:
    """As fusoes aprovadas e as recusas NOMEADAS. Nao toca disco e nao decide gosto.

    `nomes_por_chave` vem do CATALOGO, que e o unico lugar onde cada chave tem
    EXATAMENTE UM `nome_exibido`. O `observacoes.csv` tambem carrega o nome, mas
    la ele oscila linha a linha por causa do OCR (D-03) — comparar por ele faria
    a decisao depender de qual linha se olhou primeiro.

    `chaves_observadas` entra so para a ferramenta ENXERGAR uma chave que esta no
    CSV e nao no catalogo. Ela nunca vira nome: vira RECUSA nomeada, porque sem
    `nome_exibido` nao ha como afirmar identidade, e afirmar sem base e
    exatamente o que esta ferramenta nao faz.
    """
    grupos: dict[str, set[str]] = {}
    for chave in list(nomes_por_chave) + list(chaves_observadas):
        grupos.setdefault(corpo_da_chave(chave), set()).add(chave)

    fusoes: list[Fusao] = []
    recusas: list[Recusa] = []

    for corpo in sorted(grupos):
        chaves = tuple(sorted(grupos[corpo]))
        if len(chaves) < 2:
            continue

        com_letra = [chave for chave in chaves if tem_letra_de_grade(chave)]

        if not com_letra:
            recusas.append(
                Recusa(
                    corpo=corpo,
                    chaves=chaves,
                    motivo=(
                        "NENHUMA das chaves deste grupo tem letra de grade na "
                        "assinatura, entao nao ha para onde fundir. O grupo "
                        "existe por outro motivo (encantamento, nivel), e "
                        "escolher um destino aqui seria a ferramenta decidindo "
                        "por voce qual serie e a verdadeira."
                    ),
                )
            )
            continue

        if len(com_letra) > 1:
            recusas.append(
                Recusa(
                    corpo=corpo,
                    chaves=chaves,
                    motivo=(
                        "MAIS DE UMA chave deste grupo tem letra de grade ("
                        + ", ".join(com_letra)
                        + "). Duas grades diferentes sao dois itens diferentes, "
                        "com precos diferentes -- foi exatamente por isso que a "
                        "letra entrou na assinatura. A ferramenta nao escolhe."
                    ),
                )
            )
            continue

        destino = com_letra[0]

        if destino not in nomes_por_chave:
            recusas.append(
                Recusa(
                    corpo=corpo,
                    chaves=chaves,
                    motivo=(
                        "a chave de destino "
                        + destino
                        + " nao esta no catalogo de nomes, entao nao ha "
                        "`nome_exibido` dela para comparar. Sem os dois lados da "
                        "igualdade nao ha fusao."
                    ),
                )
            )
            continue

        nome_do_destino = nomes_por_chave[destino]
        origens: list[str] = []

        for origem in chaves:
            if origem == destino:
                continue
            if origem not in nomes_por_chave:
                recusas.append(
                    Recusa(
                        corpo=corpo,
                        chaves=(origem, destino),
                        motivo=(
                            "a chave "
                            + origem
                            + " aparece nas observacoes mas NAO esta no catalogo "
                            "de nomes, entao nao ha `nome_exibido` dela para "
                            "comparar com o do destino."
                        ),
                    )
                )
                continue
            if nomes_por_chave[origem] != nome_do_destino:
                recusas.append(
                    Recusa(
                        corpo=corpo,
                        chaves=(origem, destino),
                        motivo=(
                            "os `nome_exibido` DIFEREM: "
                            + repr(nomes_por_chave[origem])
                            + " contra "
                            + repr(nome_do_destino)
                            + ". A fusao no CSV e irreversivel, entao ela so "
                            "acontece na igualdade EXATA -- nunca por "
                            "similaridade."
                        ),
                    )
                )
                continue
            origens.append(origem)

        if origens:
            fusoes.append(
                Fusao(corpo=corpo, destino=destino, origens=tuple(origens))
            )

    return Plano(fusoes=tuple(fusoes), recusas=tuple(recusas))


# -- a aplicacao sobre as linhas cruas --------------------------------------


class LinhaQueNaoValida(Exception):
    """Uma linha de dado que a ferramenta nao consegue interpretar.

    Ela RECUSA O ARQUIVO INTEIRO, e a inversao em relacao ao D-14 esta explicada
    no topo do modulo: aqui e escrita, e o que nao se entende nao se pode
    prometer preservar.
    """


@dataclass
class RelatorioDasObservacoes:
    linhas_reescritas: int = 0
    linhas_removidas: int = 0
    duplicatas_preexistentes: int = 0


def aplicar_nas_observacoes(
    linhas: Sequence[Sequence[str]], mapa: Mapping[str, str]
) -> tuple[list[list[str]], RelatorioDasObservacoes]:
    """As linhas de dado com a chave trocada e as duplicatas DA FUSAO desfeitas.

    A ORDEM DO ARQUIVO E PRESERVADA. O usuario abre isto no Sheets e o arquivo
    cresce por append: reordenar tornaria o diff ilegivel para ele sem ganhar
    nada.

    A LINHA QUE SOBREVIVE A UMA COLISAO E A DE `primeira_vez` MAIS ANTIGA,
    INTEIRA. Nao se monta uma linha nova com o menor carimbo de uma e o residuo
    de outra: cada linha e UMA observacao coerente, e costurar duas produziria um
    registro que nunca existiu. Empate de carimbo mantem a que vinha antes no
    arquivo.

    A duplicata que ja existia sob UMA chave so nao e tocada — decisao 2 do topo.
    """
    relatorio = RelatorioDasObservacoes()
    preparadas: list[tuple[list[str], str, tuple, datetime]] = []

    for numero, campos in enumerate(linhas, start=2):
        campos = list(campos)
        try:
            chave_dos_campos(campos)
        except ValueError as erro:
            raise LinhaQueNaoValida(
                "observacoes.csv, linha " + str(numero) + ": " + str(erro)
                + " -- " + repr(SEPARADOR.join(campos))
            ) from None

        original = campos[COLUNAS_DE_OBSERVACOES.index("chave_da_serie")].strip()
        destino = mapa.get(original)
        if destino is not None:
            campos[COLUNAS_DE_OBSERVACOES.index("chave_da_serie")] = destino
            relatorio.linhas_reescritas += 1

        chave = chave_dos_campos(campos)
        carimbo = datetime.fromisoformat(
            campos[COLUNAS_DE_OBSERVACOES.index("primeira_vez")].strip()
        )
        preparadas.append((campos, original, chave, carimbo))

    posicoes_por_chave: dict[tuple, list[int]] = {}
    for indice, (_campos, _original, chave, _carimbo) in enumerate(preparadas):
        posicoes_por_chave.setdefault(chave, []).append(indice)

    descartadas: set[int] = set()
    for posicoes in posicoes_por_chave.values():
        if len(posicoes) < 2:
            continue
        origens = {preparadas[indice][1] for indice in posicoes}
        if len(origens) < 2:
            # Duplicata ANTERIOR a ferramenta, sob uma chave so. Ela e contada e
            # relatada, e fica onde esta.
            relatorio.duplicatas_preexistentes += len(posicoes) - 1
            continue
        sobrevivente = min(posicoes, key=lambda i: (preparadas[i][3], i))
        for indice in posicoes:
            if indice != sobrevivente:
                descartadas.add(indice)

    relatorio.linhas_removidas = len(descartadas)
    novas = [
        campos
        for indice, (campos, _o, _c, _t) in enumerate(preparadas)
        if indice not in descartadas
    ]
    return novas, relatorio


@dataclass
class RelatorioDoCatalogo:
    linhas_removidas: int = 0
    destinos_atualizados: int = 0


def aplicar_no_catalogo(
    linhas: Sequence[Sequence[str]], mapa: Mapping[str, str]
) -> tuple[list[list[str]], RelatorioDoCatalogo]:
    """As series do catalogo com as origens absorvidas pelo destino.

    `avistamentos` SOMA, `primeira_vez` fica a MAIS ANTIGA e `ultima_vez` a MAIS
    RECENTE — as tres sao a mesma serie vista o tempo todo, so anotada sob dois
    nomes de chave. O `nome_exibido` do destino permanece o dele; ele ja e
    IDENTICO ao das origens, senao `planejar` nao teria aprovado a fusao.

    A linha do destino e recalculada NA POSICAO ORIGINAL dela, e toda linha nao
    envolvida sai com os campos que entrou — inclusive o carimbo escrito
    exatamente como estava, sem passar por `fromisoformat`/`isoformat`.
    """
    relatorio = RelatorioDoCatalogo()
    indice_da_coluna = {nome: i for i, nome in enumerate(COLUNAS_DO_CATALOGO)}

    lidas: list[list[str]] = []
    for numero, campos in enumerate(linhas, start=2):
        campos = list(campos)
        if len(campos) != len(COLUNAS_DO_CATALOGO):
            raise LinhaQueNaoValida(
                ARQUIVO_DO_CATALOGO + ", linha " + str(numero) + ": esperava "
                + str(len(COLUNAS_DO_CATALOGO)) + " campos, veio "
                + str(len(campos)) + " -- " + repr(SEPARADOR.join(campos))
            )
        try:
            datetime.fromisoformat(campos[indice_da_coluna["primeira_vez"]].strip())
            datetime.fromisoformat(campos[indice_da_coluna["ultima_vez"]].strip())
            int(campos[indice_da_coluna["avistamentos"]].strip())
        except ValueError as erro:
            raise LinhaQueNaoValida(
                ARQUIVO_DO_CATALOGO + ", linha " + str(numero) + ": " + str(erro)
                + " -- " + repr(SEPARADOR.join(campos))
            ) from None
        lidas.append(campos)

    absorvidas: dict[str, list[list[str]]] = {}
    for campos in lidas:
        chave = campos[indice_da_coluna["chave"]].strip()
        destino = mapa.get(chave)
        if destino is not None:
            absorvidas.setdefault(destino, []).append(campos)

    novas: list[list[str]] = []
    for campos in lidas:
        chave = campos[indice_da_coluna["chave"]].strip()
        if chave in mapa:
            relatorio.linhas_removidas += 1
            continue
        parcelas = absorvidas.get(chave)
        if not parcelas:
            novas.append(campos)
            continue

        todas = [campos, *parcelas]
        primeira = min(
            datetime.fromisoformat(c[indice_da_coluna["primeira_vez"]].strip())
            for c in todas
        )
        ultima = max(
            datetime.fromisoformat(c[indice_da_coluna["ultima_vez"]].strip())
            for c in todas
        )
        total = sum(
            int(c[indice_da_coluna["avistamentos"]].strip()) for c in todas
        )
        fundida = list(campos)
        fundida[indice_da_coluna["primeira_vez"]] = primeira.isoformat()
        fundida[indice_da_coluna["ultima_vez"]] = ultima.isoformat()
        fundida[indice_da_coluna["avistamentos"]] = str(total)
        novas.append(fundida)
        relatorio.destinos_atualizados += 1

    return novas, relatorio


# ===========================================================================
# A METADE DE DISCO
# ===========================================================================


@dataclass
class ArquivoLido:
    """O texto cru, o cabecalho literal e as linhas de dado ja separadas."""

    caminho: Path
    bruto: str
    cabecalho: str
    linhas: list[list[str]]


def ler_observacoes(caminho: Path) -> ArquivoLido | None:
    """Le e ATRAVESSA O MESMO PORTAO do leitor de producao. Ausente -> `None`.

    `conferir_o_terminador` e `conferir_o_cabecalho` sao IMPORTADOS de
    `mercado_registro`, e nao reimplementados: duas implementacoes do mesmo
    portao seriam duas chances de uma delas nao ter a rede que pega o `'80'`
    truncado para `'8'`.
    """
    try:
        with caminho.open("r", encoding="utf-8", newline="") as fonte:
            bruto = fonte.read()
    except FileNotFoundError:
        return None
    if not bruto:
        return None

    conferir_o_terminador(bruto, caminho)
    linhas = list(csv.reader(io.StringIO(bruto, newline=""), delimiter=SEPARADOR))
    conferir_o_cabecalho(linhas, caminho)

    dados = [
        campos
        for campos in linhas[1:]
        if campos and any(campo.strip() for campo in campos)
    ]
    return ArquivoLido(
        caminho=caminho,
        bruto=bruto,
        cabecalho=_cabecalho_literal(bruto),
        linhas=dados,
    )


def ler_catalogo(caminho: Path) -> ArquivoLido | None:
    """Le o catalogo. Ausente, vazio ou SEM cabecalho -> ver o corpo.

    O cabecalho do catalogo e CONVENIENCIA e nao identidade — esta escrito assim
    em `Catalogo.carregar`. Mas esta ferramenta REESCREVE o arquivo, e reescrever
    sem saber onde comeca o dado e como se apaga a primeira serie do usuario.
    Entao: cabecalho presente segue, cabecalho ausente RECUSA — e a recusa e
    barata de consertar, porque `Catalogo.gravar` sempre escreve um.
    """
    try:
        with caminho.open("r", encoding="utf-8", newline="") as fonte:
            bruto = fonte.read()
    except FileNotFoundError:
        return None
    if not bruto:
        return None

    if not bruto.endswith("\n"):
        raise ContratoDoArquivoQuebrado(
            "FUSAO RECUSADA -- o catalogo " + str(caminho) + " NAO TERMINA EM "
            "QUEBRA DE LINHA, e por isso nada foi lido dele. Um arquivo assim "
            "pode ter a ultima linha truncada, e esta ferramenta REESCREVE o "
            "arquivo: ela nao promove uma linha possivelmente cortada a linha "
            "boa. Abra o arquivo, olhe a ultima linha, complete-a ou apague-a, "
            "e salve COM quebra de linha no fim."
        )

    linhas = list(csv.reader(io.StringIO(bruto, newline=""), delimiter=SEPARADOR))
    encontrado = tuple(campo.strip() for campo in linhas[0]) if linhas else ()
    if encontrado != COLUNAS_DO_CATALOGO:
        raise ContratoDoArquivoQuebrado(
            "FUSAO RECUSADA -- a primeira linha de " + str(caminho) + " nao e o "
            "cabecalho esperado. Esperava " + repr(COLUNAS_DO_CATALOGO)
            + " e encontrei " + repr(encontrado) + ". NENHUM byte foi alterado. "
            "Esta ferramenta reescreve o arquivo, e reescrever sem saber onde "
            "comeca o dado apagaria a primeira serie. Restaure a primeira linha "
            "para o cabecalho esperado e rode de novo."
        )

    dados = [
        campos
        for campos in linhas[1:]
        if campos and any(campo.strip() for campo in campos)
    ]
    return ArquivoLido(
        caminho=caminho,
        bruto=bruto,
        cabecalho=_cabecalho_literal(bruto),
        linhas=dados,
    )


def _cabecalho_literal(bruto: str) -> str:
    """A primeira linha FISICA, com o terminador dela, copiada byte a byte.

    Nao re-serializada: `csv.writer` decide sozinho quando aspar um campo e qual
    terminador usar, e o cabecalho e CONTRATO — ele tem de sair igual ao que
    entrou, inclusive num arquivo que use `\\n` onde o `csv` usaria `\\r\\n`.

    Ela so e chamada DEPOIS de a conferencia de cabecalho passar, e a conferencia
    exige igualdade com `COLUNAS` depois de `strip` — nomes sem separador, sem
    aspas e sem quebra de linha. Logo a primeira linha fisica E o cabecalho.
    """
    corte = bruto.find("\n")
    return bruto if corte < 0 else bruto[: corte + 1]


def render(cabecalho: str, linhas: Sequence[Sequence[str]]) -> str:
    """Cabecalho literal + as linhas pelo `csv.writer`, com `newline=""`.

    `newline=""` no `StringIO` pelo mesmo motivo que ele aparece em toda escrita
    deste projeto: sem ele o modulo `csv` acaba com `\\r\\r\\n` no Windows e nao
    consegue remontar um campo que contem quebra de linha.

    O TERMINADOR DAS LINHAS DE DADO E O DO CABECALHO. O `csv.writer` emite
    `\\r\\n` por padrao, que e o que o proprio programa escreveu no arquivo — mas
    um arquivo que passou por um editor pode ter virado `\\n` inteiro, e devolver
    um arquivo com as duas convencoes misturadas seria a ferramenta deixando uma
    marca sua num arquivo que ela so deveria consertar.
    """
    terminador = "\r\n" if cabecalho.endswith("\r\n") else "\n"
    buffer = io.StringIO(newline="")
    escritor = csv.writer(buffer, delimiter=SEPARADOR, lineterminator=terminador)
    for campos in linhas:
        escritor.writerow(campos)
    return cabecalho + buffer.getvalue()


def conferir_a_saida_das_observacoes(texto: str, cabecalho: str, caminho: Path) -> None:
    """O texto pronto atravessa o MESMO portao que o leitor vai atravessar.

    Afirmar aqui, e nao no teste, e o que faz a garantia valer no arquivo do
    usuario e nao so na suite.
    """
    conferir_o_terminador(texto, caminho)
    linhas = list(csv.reader(io.StringIO(texto, newline=""), delimiter=SEPARADOR))
    conferir_o_cabecalho(linhas, caminho)
    _conferir_o_cabecalho_literal(texto, cabecalho, caminho)


def conferir_a_saida_do_catalogo(texto: str, cabecalho: str, caminho: Path) -> None:
    if not texto.endswith("\n"):
        raise ContratoDoArquivoQuebrado(
            "ABORTADO ANTES DE ESCREVER -- o texto gerado para " + str(caminho)
            + " nao termina em quebra de linha (D-17). Nada foi gravado."
        )
    _conferir_o_cabecalho_literal(texto, cabecalho, caminho)


def _conferir_o_cabecalho_literal(texto: str, cabecalho: str, caminho: Path) -> None:
    if not texto.startswith(cabecalho):
        raise ContratoDoArquivoQuebrado(
            "ABORTADO ANTES DE ESCREVER -- o cabecalho gerado para "
            + str(caminho) + " nao e byte a byte o que foi lido. Esperava "
            + repr(cabecalho) + ". Nada foi gravado."
        )


def caminho_do_backup(arquivo: Path, carimbo: str) -> Path:
    return arquivo.with_name(arquivo.name + ".antes-da-fusao-" + carimbo + ".bak")


def gravar(arquivo: Path, texto: str, carimbo: str) -> Path:
    """Backup byte a byte, depois `.tmp-<pid>` ao lado, depois `os.replace`.

    O temporario NAO vai para o `%TEMP%`: `os.replace` entre volumes diferentes
    nao e atomico e no Windows nem funciona — a razao ja esta escrita em
    `Catalogo.gravar`. O pid no nome impede uma segunda instancia de atropelar o
    temporario da primeira.

    O BACKUP NUNCA E SOBRESCRITO. Se o nome ja existe, a ferramenta LEVANTA em
    vez de apagar: um backup e a unica coisa que separa o usuario de um erro sem
    volta, e a ferramenta nao apaga backup nenhum.
    """
    backup = caminho_do_backup(arquivo, carimbo)
    if backup.exists():
        raise FileExistsError(
            "o backup " + str(backup) + " JA EXISTE e esta ferramenta nunca "
            "sobrescreve backup. Nada foi gravado. Renomeie ou mova o backup "
            "antigo e rode de novo."
        )
    backup.write_bytes(arquivo.read_bytes())

    temporario = arquivo.with_name(arquivo.name + ".tmp-" + str(os.getpid()))
    with temporario.open("w", encoding="utf-8", newline="") as destino:
        destino.write(texto)
    os.replace(temporario, arquivo)
    return backup


# ===========================================================================
# main
# ===========================================================================


def _nomes_do_catalogo(lido: ArquivoLido | None) -> dict[str, str]:
    if lido is None:
        return {}
    indice = {nome: i for i, nome in enumerate(COLUNAS_DO_CATALOGO)}
    nomes: dict[str, str] = {}
    for campos in lido.linhas:
        if len(campos) != len(COLUNAS_DO_CATALOGO):
            continue
        chave = campos[indice["chave"]].strip()
        if chave:
            nomes[chave] = campos[indice["nome_exibido"]]
    return nomes


def _chaves_das_observacoes(lido: ArquivoLido | None) -> list[str]:
    if lido is None:
        return []
    coluna = COLUNAS_DE_OBSERVACOES.index("chave_da_serie")
    return [
        campos[coluna].strip()
        for campos in lido.linhas
        if campos and campos[coluna].strip()
    ]


def construir_analisador() -> argparse.ArgumentParser:
    """O analisador de linha de comando, MONTADO FORA de `main`.

    Ele sai daqui em vez de nascer dentro de `main` para que o teste possa
    afirmar o PADRAO de `--pasta` sem executar a ferramenta. Um teste que
    remontasse o analisador afirmaria a si mesmo: o padrao poderia mudar aqui e
    ele continuaria verde.
    """
    analisador = argparse.ArgumentParser(
        description=(
            "Funde as chaves de serie que o conserto da letra de grade partiu. "
            "Dry-run por padrao: sem --gravar nada e tocado."
        )
    )
    analisador.add_argument("--pasta", default=str(PASTA_DO_MERCADO))
    analisador.add_argument("--gravar", action="store_true")
    return analisador


def main(argv=None) -> int:
    opcoes = construir_analisador().parse_args(argv)

    pasta = Path(opcoes.pasta).resolve()

    print("=" * 78)
    print("FUSAO DE CHAVES DE SERIE - quick 260901-w9c")
    print("=" * 78)
    print("pasta: " + str(pasta))
    print("")

    if not pasta.is_dir():
        print("PASTA INEXISTENTE: " + str(pasta))
        print("  Nada foi lido e nada foi escrito.")
        return SAIDA_SEM_PASTA

    arquivo_de_observacoes = pasta / ARQUIVO_DE_OBSERVACOES
    arquivo_do_catalogo = pasta / ARQUIVO_DO_CATALOGO

    try:
        observacoes = ler_observacoes(arquivo_de_observacoes)
        catalogo = ler_catalogo(arquivo_do_catalogo)
    except ContratoDoArquivoQuebrado as erro:
        print(str(erro))
        return SAIDA_CONTRATO_QUEBRADO

    if catalogo is None:
        print("SEM CATALOGO DE NOMES em " + str(arquivo_do_catalogo) + ".")
        print(
            "  O `nome_exibido` de cada chave mora la, e a fusao so acontece na "
            "igualdade EXATA dele."
        )
        print("  Sem os dois lados da igualdade nao ha nada a fundir.")
        return SAIDA_OK

    nomes = _nomes_do_catalogo(catalogo)
    plano = planejar(nomes, _chaves_das_observacoes(observacoes))

    for recusa in plano.recusas:
        print("RECUSADO  " + recusa.corpo)
        print("  chaves: " + ", ".join(recusa.chaves))
        print("  motivo: " + recusa.motivo)
        print("")

    if not plano.fusoes:
        print("NENHUMA FUSAO A FAZER. Nada foi escrito.")
        return SAIDA_OK

    for fusao in plano.fusoes:
        print("FUNDE     " + fusao.destino)
        for origem in fusao.origens:
            print("  <- " + origem)
    print("")

    mapa = plano.mapa

    try:
        if observacoes is not None:
            linhas_de_observacoes, relatorio_obs = aplicar_nas_observacoes(
                observacoes.linhas, mapa
            )
        else:
            linhas_de_observacoes, relatorio_obs = [], RelatorioDasObservacoes()
        linhas_do_catalogo, relatorio_cat = aplicar_no_catalogo(catalogo.linhas, mapa)
    except LinhaQueNaoValida as erro:
        print("FUSAO RECUSADA -- uma linha de dado nao pode ser interpretada:")
        print("  " + str(erro))
        print(
            "  Esta ferramenta REESCREVE o arquivo, e uma linha que ela nao "
            "entende e uma linha que ela nao pode prometer preservar."
        )
        print("  NADA foi escrito. Conserte a linha no Sheets e rode de novo.")
        return SAIDA_CONTRATO_QUEBRADO

    if observacoes is not None:
        print("observacoes.csv")
        print("  linhas de dado antes  : " + str(len(observacoes.linhas)))
        print("  chaves reescritas     : " + str(relatorio_obs.linhas_reescritas))
        print("  duplicatas desfeitas  : " + str(relatorio_obs.linhas_removidas))
        print("  linhas de dado depois : " + str(len(linhas_de_observacoes)))
        if relatorio_obs.duplicatas_preexistentes:
            print(
                "  (havia "
                + str(relatorio_obs.duplicatas_preexistentes)
                + " duplicata(s) ja no arquivo sob UMA chave so; elas ficam "
                "onde estao -- a ferramenta so desfaz o que a fusao criou)"
            )
    else:
        print("observacoes.csv: ausente ou vazio, nada a fundir nele.")

    print(ARQUIVO_DO_CATALOGO)
    print("  series antes          : " + str(len(catalogo.linhas)))
    print("  destinos atualizados  : " + str(relatorio_cat.destinos_atualizados))
    print("  series absorvidas     : " + str(relatorio_cat.linhas_removidas))
    print("  series depois         : " + str(len(linhas_do_catalogo)))
    print("")

    texto_do_catalogo = render(catalogo.cabecalho, linhas_do_catalogo)
    texto_de_observacoes = (
        render(observacoes.cabecalho, linhas_de_observacoes)
        if observacoes is not None
        else None
    )

    try:
        conferir_a_saida_do_catalogo(
            texto_do_catalogo, catalogo.cabecalho, arquivo_do_catalogo
        )
        if texto_de_observacoes is not None and observacoes is not None:
            conferir_a_saida_das_observacoes(
                texto_de_observacoes, observacoes.cabecalho, arquivo_de_observacoes
            )
    except ContratoDoArquivoQuebrado as erro:
        print(str(erro))
        return SAIDA_CONTRATO_QUEBRADO

    if not opcoes.gravar:
        print("(nada gravado - rode de novo com --gravar para persistir)")
        return SAIDA_OK

    # OU OS DOIS, OU NENHUM: o backup dos dois e feito antes de qualquer
    # `os.replace`, entao uma colisao de nome de backup no segundo arquivo para a
    # ferramenta com os dois arquivos ainda intactos.
    carimbo = datetime.now().strftime(FORMATO_DO_CARIMBO)
    try:
        if texto_de_observacoes is not None:
            _conferir_o_backup(arquivo_de_observacoes, carimbo)
        _conferir_o_backup(arquivo_do_catalogo, carimbo)
    except FileExistsError as erro:
        print("FUSAO ABORTADA: " + str(erro))
        return SAIDA_BACKUP_EXISTENTE

    if texto_de_observacoes is not None:
        backup = gravar(arquivo_de_observacoes, texto_de_observacoes, carimbo)
        print("GRAVADO " + str(arquivo_de_observacoes))
        print("  backup " + str(backup))
    backup = gravar(arquivo_do_catalogo, texto_do_catalogo, carimbo)
    print("GRAVADO " + str(arquivo_do_catalogo))
    print("  backup " + str(backup))
    return SAIDA_OK


def _conferir_o_backup(arquivo: Path, carimbo: str) -> None:
    backup = caminho_do_backup(arquivo, carimbo)
    if backup.exists():
        raise FileExistsError(
            "o backup " + str(backup) + " JA EXISTE e esta ferramenta nunca "
            "sobrescreve backup. NADA foi gravado. Renomeie ou mova o backup "
            "antigo e rode de novo."
        )


if __name__ == "__main__":
    raise SystemExit(main())
