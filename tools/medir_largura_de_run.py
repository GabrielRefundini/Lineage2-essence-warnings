"""A varredura que MEDE a largura de run, o vale, o custo da guarda e a FOLGA DE COLA.

Ela varre as 8 gravacoes NOMEADAS do censo com o PORTAO DE LAYOUT LIGADO,
recorta as tres colunas calibradas linha a linha, e responde as quatro perguntas
que o 02-08 precisa responder com numero:

    RELATORIO 1  o VALE — a distribuicao de largura MAXIMA por celula, separada
                 entre as celulas que a producao ACEITA hoje e as que recusa
    RELATORIO 2  o CUSTO DA GUARDA por celula, por linha e por pagina
    RELATORIO 3  a FOLGA DE COLA nos tres baldes, contra DOIS rotulos nao
                 circulares, com uma linha por folga candidata e passo 1
    RELATORIO 4  o RELOGIO da particao dentro do tick de 1 Hz

    mercado_folga_de_cola_do_glifo   o UNICO numero livre deste mecanismo

O DEFEITO QUE ELA EXISTE PARA MEDIR
------------------------------------
Um run mais largo que o MAIOR molde de um caractere e casado contra UM molde e
vira UM digito, com score e margem que atravessam as duas peneiras. Medido no
censo do 02-07: `053105-mercado-aberto/frame_000078.png` L3, quantidade 44
(rotulo derivado de Total `56,00` e Unit price `1,27`), sai como UM run de 12 px
em `segmentar_glifos` e le `4`. A gramatica aceita, e o numero errado e
PLAUSIVEL. Essa e a unica falha ABERTA conhecida da Fase 2, e ela viola
`LEIT-02` diretamente.

A CAUSA E GEOMETRIA, E NAO BRILHO, E ISSO ESTA VISTO NO PIXEL
---------------------------------------------------------------
A barra horizontal do molde `4` ocupa as SEIS colunas da caixa dele. Colado o
vizinho, a coluna de fronteira fica com tinta, `mascara.any(axis=0)` nao ve
coluna vazia, e a regra de `segmentar_glifos` — QUALQUER COLUNA VAZIA SEPARA,
sem tolerancia de lacuna — nao tem o que separar:

    ....#.....#.
    ....#.....#.
    ....#.....#.
    ....#.....#.
    ############   <- as duas barras viraram uma linha continua
    ....#.....#.
    ....#.....#.
    ....#.....#.

Sondado nos pisos 180, 177, 170 e 160, o run continua UNICO; nos pisos 200 e 220
os dois glifos reaparecem, mas 220 apaga a coluna inteira em outros frames.
Nenhum piso de brilho conserta isto.

A CONVENCAO DE LARGURA E SEMI-ABERTA, E ERRAR POR UM INVALIDA TUDO
--------------------------------------------------------------------
`segmentar_glifos` guarda `runs.append((inicio, coluna))` com `coluna` sendo a
PRIMEIRA coluna VAZIA. A largura e portanto `fim - inicio`, e NUNCA
`fim - inicio + 1`. O script descartavel que levantou o alarme usou a convencao
inclusiva: ele inflou toda largura em 1 e a faixa "suspeita" dele passou a
engolir TODO `4` legitimo, porque o molde do `4` tem exatamente 6 px.
`tests/test_medir_largura_de_run.py` prende a convencao contra
`glifos_unitario_f010.png`, que le `6,00` com larguras `4, 1, 4, 4`.

OS DOIS ROTULOS SAO NAO CIRCULARES, E SEM ISSO NAO HA MEDICAO
----------------------------------------------------------------
Para a coluna Quantity, `quantidade_derivada(total, unitario)` — do 02-07,
IMPORTADA e nunca reescrita — recebe DOIS inteiros e mais nada: sem recorte, sem
moldes, sem piso. Para as colunas de MOEDA, `total_no_intervalo` e a INVERSA da
mesma aritmetica: quando as OUTRAS duas colunas leem LIMPO (aceitas pela
gramatica E sem nenhum run acima do limite), o total esta preso ao intervalo que
a uniao das hipoteses de truncamento e de arredondamento permite. Ele nao FIXA o
total, mas REJEITA um total inventado — que e exatamente o que precisa ser
medido.

A CONDICAO DE LIMPEZA E O QUE TORNA O ROTULO NAO CIRCULAR. Um rotulo calculado a
partir de uma coluna que TAMBEM esta mentindo mediria a leitura contra ela
mesma, e foi assim que o 02-02 refutou o rotulo por pasta de origem.

O LIMITE E DERIVADO DOS MOLDES, E POR ISSO ELE NAO VAI PARA O calibration.json
--------------------------------------------------------------------------------
`limite_de_glifo_unico` e `max(largura)` sobre os moldes de UM caractere que ja
moram no `calibration.json`. Gravar uma copia criaria DUAS VERDADES para uma so
geometria — o argumento literal que `layout_confere` ja escreve sobre o `dx` do
cabecalho — e na recalibracao seguinte a copia envelheceria contra os moldes que
ela descreve.

O NUMERO LIVRE E OUTRO, E ELE SIM VAI PARA O calibration.json: a FOLGA DE COLA.
Ela conta quantas colunas a barra anti-serrilhada compartilha com o vizinho, nao
se deriva de nada, e por isso e MEDIDA por esta ferramenta — nunca escolhida.

AFROUXAR AS LARGURAS NAO DEGRADA DEVAGAR: INVENTA EM BLOCO
-------------------------------------------------------------
O run de 11 px de `frame_000105.png` L6 admite DOIS cortes que passam nas duas
peneiras: `6+5` da `4` + `4` e produz `144,44`; `7+4` da `4` + `9` e produz
`149,44`. A aritmetica independente da linha (unitario `2,99`, quantidade `50`)
exige o total em [149,25; 150,00): `149,44` cabe e `144,44` nao. Por isso a
proposta so sai com o balde LE ERRADO VAZIO, e por isso a tabela do RELATORIO 3
mostra tambem a folga seguinte — para que se veja o que acontece ao afrouxar.

O CENSO E LIDO UMA VEZ SO, E ISSO E DESENHO E NAO OTIMIZACAO
--------------------------------------------------------------
A segmentacao no piso da coluna NAO depende da folga; so a particao depende.
Entao a colheita guarda mascara, faixa e runs por celula, e as folgas candidatas
sao reclassificadas EM MEMORIA sobre ela. A varredura irma
(`tools/medir_brilho_da_quantidade.py`) varre o censo uma vez POR PISO
CANDIDATO, e e por isso que ela passa de 10 minutos e ja custou uma sessao a um
executor. Reabrir o censo por folga seria pagar o custo alheio sem a razao
alheia.

AS PRIMITIVAS SAO IMPORTADAS, E NUNCA COPIADAS
------------------------------------------------
`segmentar_glifos_no_brilho`, `mascara_de_numero`, `pontuar_glifos`,
`numero_valido`, `centesimos_de_moeda`, `inteiro_de_quantidade`, `ler_celula` e
`layout_confere` vem de `l2scanner.mercado_leitura`; `quantidade_derivada` vem
de `tools/medir_brilho_da_quantidade.py`; e a lista das 8 gravacoes vem de
`tools/medir_oclusao.py`. A seta aponta sempre ferramenta -> puro, e uma copia
local faria esta varredura MEDIR com uma convencao e o scanner DECIDIR com
outra no dia em que uma das duas fosse corrigida.

Uso (no checkout PRINCIPAL — `recordings/` e `calibration.json` sao gitignored):

    .venv/Scripts/python.exe tools/medir_largura_de_run.py
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
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from l2scanner.calibracao import Calibracao  # noqa: E402
from l2scanner.identidade import VALOR_MINIMO_DO_TEXTO  # noqa: E402

# A ARITMETICA E A CLASSIFICACAO SAO IMPORTADAS, E NUNCA REESCRITAS.
from l2scanner.mercado_leitura import (  # noqa: E402
    centesimos_de_moeda,
    inteiro_de_quantidade,
    layout_confere,
    mascara_de_numero,
    numero_valido,
    pontuar_glifos,
    segmentar_glifos_no_brilho,
)
from l2scanner.mercado_visao import (  # noqa: E402
    RastreioDoPainel,
    ancoras_de_calibracao,
    cabecalho_de_calibracao,
    glifos_de_calibracao,
)


def _carregar_a_irma(nome: str):
    """`tools/` nao e pacote, entao o import vem do caminho do arquivo."""
    caminho = RAIZ / "tools" / (nome + ".py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    # Registrar ANTES de executar: `@dataclass` resolve as anotacoes por
    # `sys.modules[cls.__module__]`, e sem isto ele encontra None.
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


# O ROTULO DA QUANTITY VEM DA VARREDURA IRMA, E NAO E REESCRITO AQUI. Duas
# copias da mesma aritmetica envelheceriam separadas, e a que envelhecesse pior
# rotularia a populacao contra a qual tudo o mais e julgado.
_brilho = _carregar_a_irma("medir_brilho_da_quantidade")
quantidade_derivada = _brilho.quantidade_derivada


def _carregar_o_censo():
    """A lista das 8 gravacoes vive numa ferramenta so, e e importada daqui.

    Duplicar a lista seria a porta pela qual as varreduras passariam a medir
    conjuntos diferentes sem ninguem notar — e um limiar medido sobre um
    conjunto nao se compara com um medido sobre outro. `recordings/` tem 16
    pastas, e a `pre-voo` sozinha tem 1.502 PNGs: um glob dominaria qualquer
    distribuicao.

    Ele roda DEPOIS de `_carregar_a_irma`, e a ordem importa: a irma tambem
    registra `medir_oclusao` em `sys.modules`, e quem registra por ULTIMO e quem
    o teste de IDENTIDADE encontra.
    """
    caminho = RAIZ / "tools" / "medir_oclusao.py"
    spec = importlib.util.spec_from_file_location("medir_oclusao", caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["medir_oclusao"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


_oclusao = _carregar_o_censo()
GRAVACOES_DO_CENSO = _oclusao.GRAVACOES_DO_CENSO
MOTIVO_PARA_IGNORAR = _oclusao.MOTIVO_PARA_IGNORAR


# ---------------------------------------------------------------------------
# Os parametros da varredura — cada um com a sua razao
# ---------------------------------------------------------------------------

# O piso de brilho das colunas de MOEDA, importado de onde ele mora.
PISO_COMPARTILHADO = VALOR_MINIMO_DO_TEXTO

# UMA COLUNA POR LINHA DA TABELA. Um passo maior faria a folga gravada ser
# INTERPOLACAO e nao medicao — e uma folga e um numero de COLUNAS, entao nao ha
# nem sentido em meia folga.
PASSO_DA_VARREDURA = 1

# O TETO DA VARREDURA. Com os moldes de producao (larguras 1, 4 e 6) a folga 4
# ja libera TODA largura de 1 a 10, que e mais que o maior run largo observado:
# alem disso a tabela so repetiria a mesma linha. O teto existe para que o
# relatorio mostre os DOIS lados — sem o lado ruim na tabela, a afirmacao "a
# folga tem teto" seria promessa e nao medicao.
TETO_DA_FOLGA = 4

# O TICK do scanner. Uma peneira que estoure isto para o scanner de olhar a
# party, que e o unico defeito inaceitavel deste projeto.
TETO_DE_MILISSEGUNDOS_POR_LINHA = 200.0

# O ORCAMENTO DE RELOGIO DA PROPRIA FERRAMENTA. A sondagem do planejamento mediu
# 43 s para a passagem unica pelo censo e ~4 s por folga candidata sobre as
# linhas largas. Acima disto, o censo esta sendo reaberto por folga — e so isso
# explica uma ordem de grandeza a mais.
TETO_DE_SEGUNDOS_DA_FERRAMENTA = 300.0

AS_TRES_COLUNAS = ("total", "quantidade", "unitario")


# ---------------------------------------------------------------------------
# A GEOMETRIA DO GLIFO — derivada dos moldes, e nunca de uma chave
# ---------------------------------------------------------------------------


def larguras_de_molde(moldes: dict) -> tuple[int, ...]:
    """As larguras ORDENADAS dos moldes de UM caractere. Sem repeticao.

    Sobre os 13 moldes de producao ela devolve `(1, 4, 6)`: a virgula, os
    digitos, e o `4`. Os moldes de PALAVRA (`Adena` 35 px, `XM Coin` 44 px)
    ficam de fora pela MESMA regra que `pontuar_glifos` ja aplica
    (`len(rotulo) == 1`) — eles nao sao geometria de glifo, e um deles no
    conjunto faria o limite valer 44 e a guarda nunca disparar.
    """
    larguras = {
        int(molde.shape[1])
        for rotulo, molde in moldes.items()
        if len(rotulo) == 1 and getattr(molde, "ndim", 0) == 2
    }
    return tuple(sorted(larguras))


def limite_de_glifo_unico(moldes: dict) -> int | None:
    """A MAIOR largura de um glifo de um caractere. `None` sem moldes.

    O QUE ELE E. Sobre os moldes de producao ele vale 6, que e a largura do
    molde `4` — a barra horizontal dele ocupa as seis colunas da caixa. Um run
    mais largo que isso NAO PODE ser um glifo so.

    POR QUE ELE NAO VIRA CHAVE DO `calibration.json`. Ele e uma FUNCAO dos
    moldes que ja estao la. Gravar uma copia criaria duas verdades sobre uma so
    geometria, e na recalibracao seguinte a copia envelheceria contra os moldes
    que ela descreve. E o mesmo argumento que `layout_confere` ja escreve sobre
    o `dx` do cabecalho nao ser gravado duas vezes.

    POR QUE ELE CAI NUM VALE, E NAO NUMA ZONA CINZENTA. Medido no censo pelo
    RELATORIO 1 desta ferramenta: das celulas que a producao ACEITA hoje nas
    tres colunas, NENHUMA tem run entre o limite e o menor run largo observado.
    Duas populacoes e um vale entre elas — e por isso o custo da guarda e
    IDENTICO em qualquer limite dentro do vale, que e a definicao de um limite
    bem posto.
    """
    larguras = larguras_de_molde(moldes)
    if not larguras:
        return None
    return int(max(larguras))


def larguras_com_folga(larguras: tuple, folga: int) -> tuple[int, ...]:
    """As larguras permitidas na particao: cada molde, mais ate `folga` colunas.

    A FOLGA DE COLA E O UNICO NUMERO LIVRE DESTE MECANISMO. As larguras vem dos
    moldes, o limite vem das larguras, e so ela nao se deriva de nada: ela conta
    quantas colunas a barra anti-serrilhada de um glifo compartilha com o
    vizinho colado. Com `folga = 0` a particao so aceita larguras de molde
    puras; com `folga = 1` ela aceita `(1, 2, 4, 5, 6, 7)`.

    AFROUXAR NAO DEGRADA DEVAGAR: INVENTA EM BLOCO. Medido no run de 11 px de
    `053105-mercado-aberto/frame_000105.png` L6, que admite DOIS cortes que
    passam nas duas peneiras:

        corte   esquerda        direita          texto da celula
        6+5     `4` 0,915       `4` 0,470        `144,44`
        7+4     `4` 0,884       `9` 0,791        `149,44`

    O `0,470` do corte errado esta a 0,0002 ACIMA do piso de leitura 0,4698. A
    aritmetica independente da linha (unitario `2,99`, quantidade `50`) exige o
    total em [149,25; 150,00): `149,44` cabe, `144,44` nao. O corte certo e
    `7+4` — SETE, um a mais que o molde —, e e exatamente por isso que a folga
    existe: o glifo colado ocupa a largura do molde MAIS a coluna partilhada.

    A DP escolhe pelo PIOR score do corte inteiro, e e isso que a faz preferir
    `7+4` (pior 0,791) a `6+5` (pior 0,470) sem consultar rotulo nenhum. Mas a
    escolha so e SEGURA com a folga MEDIDA: a sondagem do planejamento mediu que
    permitir toda largura de 1 a 6 escolhe o corte errado em 54 de 59 celulas.
    """
    folga = int(folga)
    permitidas = set()
    for largura in larguras:
        largura = int(largura)
        for extra in range(0, folga + 1):
            permitidas.add(largura + extra)
    return tuple(sorted(w for w in permitidas if w > 0))


# ---------------------------------------------------------------------------
# O ROTULO DAS COLUNAS DE MOEDA — a INVERSA de `quantidade_derivada`
# ---------------------------------------------------------------------------


def total_no_intervalo(
    total: int | None, unitario: int | None, quantidade: int | None
) -> bool | None:
    """O total cabe no intervalo que `Unit price x Quantity` implica?

    ELE E A INVERSA DE `quantidade_derivada`, E A MESMA ARITMETICA. Aquela
    resolve a quantidade a partir do par (total, unitario); esta confere o total
    a partir do par (unitario, quantidade). As duas partem da MESMA uniao de
    hipoteses:

        truncamento     unitario <= total/q < unitario + 1
        arredondamento  unitario - 0,5 <= total/q < unitario + 0,5

    A uniao das duas prende o total em `[(2u - 1)q/2, (u + 1)q)`, que em
    aritmetica INTEIRA e `(2*u - 1)*q // 2 <= total < (u + 1)*q`.

    ELE NAO FIXA O TOTAL, MAS REJEITA UM TOTAL INVENTADO, e e isso que precisa
    ser medido: o intervalo tem largura de `1,5 x q` centesimos, entao ele passa
    por muitos totais plausiveis — e nao passa pelo `144,44` que o corte errado
    de `frame_000105.png` L6 produz, contra o `149,44` que o corte certo produz.

    ARITMETICA INTEIRA, SEM UMA DIVISAO DE PONTO FLUTUANTE, pela mesma razao ja
    escrita em `residuo_do_cruzamento`: um erro de `1e-13` decidiria a fronteira
    de um intervalo.

    `None` — "NAO OPINO" — quando qualquer um dos tres falta ou nao e positivo.
    Ele NUNCA levanta: um rotulo que estoura no meio da varredura nao rotula
    nada. E "nao opino" NUNCA vira veredito: a celula sem rotulo simplesmente
    nao entra na medicao.
    """
    if total is None or unitario is None or quantidade is None:
        return None
    try:
        total = int(total)
        unitario = int(unitario)
        quantidade = int(quantidade)
    except (TypeError, ValueError):
        return None
    if total <= 0 or unitario <= 0 or quantidade <= 0:
        return None
    piso = (2 * unitario - 1) * quantidade // 2
    teto = (unitario + 1) * quantidade
    return bool(piso <= total < teto)


# ---------------------------------------------------------------------------
# A PARTICAO — programacao dinamica sobre as posicoes de corte
# ---------------------------------------------------------------------------


def pontuar_segmento(
    mascara: np.ndarray,
    faixa: tuple[int, int],
    inicio: int,
    fim: int,
    moldes: dict,
    cache: dict | None = None,
) -> tuple[str, float, float] | None:
    """UM segmento pontuado por `pontuar_glifos`. `None` quando incalculavel.

    Ela nao reimplementa o casamento: chama a MESMA `pontuar_glifos` da
    producao, com um run so. Medir de um jeito e decidir com outro seria
    comparar convencoes.

    O `cache` e por CELULA e existe porque a mesma posicao de corte reaparece
    entre as folgas candidatas — e a segmentacao nao depende da folga, so a
    particao depende.
    """
    chave = (int(inicio), int(fim))
    if cache is not None and chave in cache:
        return cache[chave]
    pontuados = pontuar_glifos(mascara, faixa, [chave], moldes)
    resultado = pontuados[0] if pontuados else None
    if cache is not None:
        cache[chave] = resultado
    return resultado


def particionar_por_dp(
    mascara: np.ndarray,
    faixa: tuple[int, int],
    inicio: int,
    fim: int,
    larguras: tuple,
    piso: float,
    margem: float,
    moldes: dict,
    cache: dict | None = None,
) -> tuple[float, float, list[str]] | None:
    """O MELHOR corte de um run largo, ou `None`. Programacao dinamica.

    `melhor[j]` e o melhor par `(pior_score, pior_margem)` para as colunas
    `[inicio, inicio + j)`, e a transicao percorre as larguras permitidas. Cada
    segmento e PODADO NA HORA pelo piso e pela margem — o TUDO OU NADA da celula
    exigiria isso de qualquer jeito, e a poda e o que mantem o custo linear.

    ELA NAO ENUMERA PARTICOES, E A ALTERNATIVA FOI MEDIDA E DESCARTADA: a
    enumeracao passou de 10 MINUTOS no censo e foi abortada, porque runs de ate
    42 px com larguras de 1 a 6 dao ate 6^8 composicoes. O custo aqui e
    `O(W x |larguras|)` chamadas de pontuacao.

    O CRITERIO E O PIOR SEGMENTO, E NAO A SOMA. Um corte com um segmento
    excelente e um pessimo e um corte ERRADO: a celula so entrega texto quando
    TODOS os segmentos passam, entao o que decide entre dois cortes validos e o
    elo mais fraco de cada um. E o que faz `7+4` (pior 0,791) vencer `6+5`
    (pior 0,470) em `frame_000105.png` L6 sem consultar rotulo nenhum.

    Devolve `(pior_score, pior_margem, rotulos)` — os rotulos da esquerda para a
    direita — ou `None` quando NENHUM corte tem todos os segmentos acima do piso
    E da margem. `None` e falha FECHADA, que e o comportamento certo.
    """
    largura_total = int(fim) - int(inicio)
    if largura_total <= 0:
        return None
    permitidas = tuple(sorted({int(w) for w in larguras if int(w) > 0}))
    if not permitidas:
        return None

    # `inf` no ponto de partida: `min(inf, score)` e o proprio score, entao o
    # primeiro segmento define o pior sem nenhum caso especial.
    melhor: list[tuple[float, float, tuple] | None] = [None] * (
        largura_total + 1
    )
    melhor[0] = (float("inf"), float("inf"), ())

    for j in range(1, largura_total + 1):
        for largura in permitidas:
            if largura > j:
                break
            anterior = melhor[j - largura]
            if anterior is None:
                continue
            pontuado = pontuar_segmento(
                mascara,
                faixa,
                int(inicio) + j - largura,
                int(inicio) + j,
                moldes,
                cache,
            )
            if pontuado is None:
                continue
            rotulo, score, distancia = pontuado
            if score < piso or distancia < margem:
                continue
            candidato = (
                min(anterior[0], float(score)),
                min(anterior[1], float(distancia)),
                anterior[2] + (rotulo,),
            )
            if melhor[j] is None or candidato[:2] > melhor[j][:2]:
                melhor[j] = candidato

    final = melhor[largura_total]
    if final is None:
        return None
    return (float(final[0]), float(final[1]), list(final[2]))


def ler_com_particao(
    mascara: np.ndarray,
    faixa: tuple[int, int],
    runs,
    moldes: dict,
    piso: float,
    margem: float,
    limite: int,
    larguras: tuple | None,
    cache: dict | None = None,
) -> str | None:
    """A leitura da celula sob a GUARDA (`larguras=None`) ou sob a PARTICAO.

    Um run DENTRO do limite segue exatamente o caminho de hoje. Um run ACIMA do
    limite: com `larguras` valendo `None` a celula cai FECHADA (a GUARDA pura);
    com uma tupla de larguras ela e partida, e cai FECHADA se nenhum corte
    passar. Nos dois ramos a falha e FECHADA — a diferenca e so quantas celulas
    chegam a ler.
    """
    lido: list[str] = []
    for inicio, fim in runs:
        if int(fim) - int(inicio) <= int(limite):
            pontuado = pontuar_segmento(
                mascara, faixa, inicio, fim, moldes, cache
            )
            if pontuado is None:
                return None
            _rotulo, score, distancia = pontuado
            if score < piso or distancia < margem:
                return None
            lido.append(pontuado[0])
            continue
        if larguras is None:
            return None
        achado = particionar_por_dp(
            mascara, faixa, inicio, fim, larguras, piso, margem, moldes, cache
        )
        if achado is None:
            return None
        lido.extend(achado[2])
    return "".join(lido)


# ---------------------------------------------------------------------------
# A COLHEITA — o censo lido UMA VEZ
# ---------------------------------------------------------------------------


@dataclass
class CelulaColhida:
    """UMA celula de numero, com tudo o que a reclassificacao vai precisar.

    A MASCARA SO E GUARDADA QUANDO A CELULA TEM RUN LARGO, e isso e o que
    mantem a colheita inteira na memoria: as celulas estreitas nunca serao
    reclassificadas, porque quando todo run cabe no limite o caminho novo E o
    caminho antigo.
    """

    chave: tuple
    coluna: str
    valor_minimo: int
    faixa: tuple | None
    runs: tuple
    largura_maxima: int
    texto_hoje: str | None
    valor_hoje: int | None
    tem_run_largo: bool
    mascara: np.ndarray | None = None
    cache: dict = field(default_factory=dict)

    @property
    def aceita_hoje(self) -> bool:
        return self.valor_hoje is not None

    @property
    def limpa(self) -> bool:
        """Aceita pela gramatica E sem nenhum run acima do limite.

        E esta a condicao que torna o rotulo de intervalo NAO CIRCULAR: um
        rotulo calculado a partir de uma coluna que tambem esta mentindo mediria
        a leitura contra ela mesma.
        """
        return self.aceita_hoje and not self.tem_run_largo


@dataclass
class LinhaColhida:
    chave: tuple
    celulas: dict = field(default_factory=dict)


@dataclass
class ResultadoDaVarredura:
    linhas: list = field(default_factory=list)
    abertos_por_gravacao: dict = field(default_factory=dict)
    recusadas_por_layout: dict = field(default_factory=dict)
    paginas: set = field(default_factory=set)
    segundos: float = 0.0

    @property
    def celulas(self) -> list:
        return [c for linha in self.linhas for c in linha.celulas.values()]


def _recorte(janela, ox, topo, altura, coluna) -> np.ndarray | None:
    x = ox + int(coluna["dx"])
    largura = int(coluna["largura"])
    if topo < 0 or x < 0:
        return None
    if topo + altura > janela.shape[0] or x + largura > janela.shape[1]:
        return None
    return janela[topo : topo + altura, x : x + largura]


def _valor_da_coluna(coluna: str, texto: str | None) -> int | None:
    """A gramatica e depois a conversao — as duas dizem `None` na duvida."""
    if not numero_valido(texto):
        return None
    if coluna == "quantidade":
        return inteiro_de_quantidade(texto)
    return centesimos_de_moeda(texto)


def colher_uma_janela(
    janela: np.ndarray,
    origem: tuple[int, int],
    cal: Calibracao,
    moldes: dict,
    limite: int,
    nome_da_gravacao: str,
    nome_do_arquivo: str,
) -> list[LinhaColhida]:
    """As dez linhas de UMA pagina, colhidas UMA VEZ.

    Por celula guarda os runs, o texto lido HOJE e — SO quando ha run largo — a
    mascara e a faixa, que sao o material da reclassificacao por folga.
    """
    grade = cal.mercado_grade or {}
    n_linhas = int(grade["linhas_por_pagina"])
    altura = int(grade["altura_da_linha"])
    piso = float(cal.mercado_limiar_de_leitura_de_glifo)
    margem = float(cal.mercado_margem_de_leitura_de_glifo)
    piso_da_quantidade = int(cal.mercado_limiar_de_brilho_da_quantidade)
    ox, oy = origem
    gy = oy + int(grade["dy"])

    pisos = {
        "total": PISO_COMPARTILHADO,
        "unitario": PISO_COMPARTILHADO,
        "quantidade": piso_da_quantidade,
    }
    atributos = {
        "total": "mercado_coluna_do_total",
        "unitario": "mercado_coluna_do_unitario",
        "quantidade": "mercado_coluna_da_quantidade",
    }

    saida: list[LinhaColhida] = []
    for indice in range(n_linhas):
        topo = gy + indice * altura
        chave = (nome_da_gravacao, nome_do_arquivo, indice)
        linha = LinhaColhida(chave=chave)
        completa = True
        for coluna in AS_TRES_COLUNAS:
            pedaco = _recorte(
                janela, ox, topo, altura, getattr(cal, atributos[coluna])
            )
            if pedaco is None:
                completa = False
                break
            valor_minimo = int(pisos[coluna])
            faixa, runs = segmentar_glifos_no_brilho(pedaco, valor_minimo)
            runs = tuple(runs)
            largura_maxima = (
                max(fim - inicio for inicio, fim in runs) if runs else 0
            )
            tem_largo = largura_maxima > limite
            mascara = None
            texto = None
            if faixa is not None and runs:
                mascara = (
                    mascara_de_numero(pedaco, valor_minimo) * 255
                ).astype(np.uint8)
                cache: dict = {}
                texto = ler_com_particao(
                    mascara,
                    faixa,
                    runs,
                    moldes,
                    piso,
                    margem,
                    # HOJE nao ha guarda: o limite fica maior que qualquer run,
                    # e e por isso que um run largo casa contra UM molde.
                    max(largura_maxima, limite),
                    None,
                    cache,
                )
            linha.celulas[coluna] = CelulaColhida(
                chave=chave,
                coluna=coluna,
                valor_minimo=valor_minimo,
                faixa=faixa,
                runs=runs,
                largura_maxima=int(largura_maxima),
                texto_hoje=texto,
                valor_hoje=_valor_da_coluna(coluna, texto),
                tem_run_largo=bool(tem_largo),
                # A mascara SO fica quando a celula vai ser reclassificada.
                mascara=mascara if tem_largo else None,
                cache=cache if (tem_largo and faixa is not None) else {},
            )
        if completa:
            saida.append(linha)
    return saida


def varrer(gravacoes: Path, cal: Calibracao, limite: int) -> ResultadoDaVarredura:
    """As 8 gravacoes do censo, UMA passagem, com o PORTAO DE LAYOUT LIGADO."""
    ancoras = ancoras_de_calibracao(cal.mercado_ancoras)
    limiar = float(cal.mercado_limiar_da_ancora or 0.73)
    moldes = glifos_de_calibracao(cal.mercado_templates_de_digito)
    cabecalho = cal.mercado_cabecalho_de_coluna
    molde_do_cabecalho = cabecalho_de_calibracao(cabecalho)
    limiar_do_cabecalho = cal.mercado_limiar_do_cabecalho
    dx_da_grade = int((cal.mercado_grade or {})["dx"])

    resultado = ResultadoDaVarredura()
    comeco = time.perf_counter()
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
            # O PORTAO DE LAYOUT ANTES DE FATIAR: medir a coluna Quantity sobre
            # a aba Adena seria medir uma coluna que nem existe la.
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
            resultado.paginas.add((nome, caminho.name))
            resultado.linhas.extend(
                colher_uma_janela(
                    frame,
                    rastreio.origem,
                    cal,
                    moldes,
                    limite,
                    nome,
                    caminho.name,
                )
            )
        resultado.abertos_por_gravacao[nome] = abertos
        resultado.recusadas_por_layout[nome] = recusadas
    resultado.segundos = time.perf_counter() - comeco
    return resultado


# ---------------------------------------------------------------------------
# RELATORIO 1 — o VALE
# ---------------------------------------------------------------------------


def classificar_por_largura(celulas: list, limite: int) -> dict:
    """As celulas separadas em DUAS populacoes, com a distribuicao de cada uma.

    A afirmacao central do plano e que existe um VALE entre elas: as celulas que
    a producao ACEITA hoje tem largura maxima ou DENTRO do limite ou BEM ACIMA
    dele, e nada no meio. Sem mostrar as duas populacoes a afirmacao nao seria
    conferivel.
    """
    saida = {}
    for coluna in AS_TRES_COLUNAS:
        da_coluna = [c for c in celulas if c.coluna == coluna and c.runs]
        aceitas = Counter(
            c.largura_maxima for c in da_coluna if c.aceita_hoje
        )
        recusadas = Counter(
            c.largura_maxima for c in da_coluna if not c.aceita_hoje
        )
        largas = sorted(w for w in aceitas if w > limite)
        saida[coluna] = {
            "aceitas": aceitas,
            "recusadas": recusadas,
            "n_aceitas": sum(aceitas.values()),
            "n_recusadas": sum(recusadas.values()),
            "menor_larga_aceita": largas[0] if largas else None,
        }
    return saida


def niveis_do_vale(distribuicao: dict, limite: int) -> tuple[list, int | None]:
    """Os niveis de largura ENTRE o limite e o menor run largo ACEITO.

    O vale e a razao de o limite ser bem posto: dentro dele a escolha nao muda
    nada, porque nao ha celula aceita em nenhum dos niveis. O gate NAO e
    tautologico — ele pergunta se o nivel `limite + 1` esta VAZIO entre as
    celulas aceitas. Se houver celula aceita com largura maxima exatamente
    `limite + 1`, o limite esta na borda de um nivel POVOADO, nao ha vale, e a
    Task 2 nao comeca.
    """
    largas = [
        d["menor_larga_aceita"]
        for d in distribuicao.values()
        if d["menor_larga_aceita"] is not None
    ]
    if not largas:
        return [], None
    menor = int(min(largas))
    return list(range(limite + 1, menor)), menor


# ---------------------------------------------------------------------------
# RELATORIO 2 — o CUSTO DA GUARDA
# ---------------------------------------------------------------------------


def custo_da_guarda(resultado: ResultadoDaVarredura) -> dict:
    """O que a GUARDA PURA custa, por celula, por linha e por pagina.

    Ela e ESTRITAMENTE DOMINADA pela particao, e por isso ela nao e o produto —
    ela e o ramo de FALLBACK. Mas o custo dela e o piso do custo de tudo: se a
    guarda ja fosse cara, a particao teria de recuperar antes de render.
    """
    por_coluna = {}
    descartados: Counter = Counter()
    for coluna in AS_TRES_COLUNAS:
        aceitas = [
            c
            for linha in resultado.linhas
            for c in [linha.celulas[coluna]]
            if c.aceita_hoje
        ]
        perdidas = [c for c in aceitas if c.tem_run_largo]
        por_coluna[coluna] = {
            "hoje": len(aceitas),
            "com_a_guarda": len(aceitas) - len(perdidas),
            "perdidas": len(perdidas),
        }
        for celula in perdidas:
            descartados[(coluna, celula.texto_hoje)] += 1

    def completa(linha, com_guarda: bool) -> bool:
        for coluna in AS_TRES_COLUNAS:
            celula = linha.celulas[coluna]
            if not celula.aceita_hoje:
                return False
            if com_guarda and celula.tem_run_largo:
                return False
        return True

    linhas_hoje = [linha for linha in resultado.linhas if completa(linha, False)]
    linhas_guarda = [
        linha for linha in resultado.linhas if completa(linha, True)
    ]
    paginas_hoje = {linha.chave[:2] for linha in linhas_hoje}
    paginas_guarda = {linha.chave[:2] for linha in linhas_guarda}
    return {
        "por_coluna": por_coluna,
        "linhas_hoje": len(linhas_hoje),
        "linhas_com_a_guarda": len(linhas_guarda),
        "paginas_hoje": len(paginas_hoje),
        "paginas_com_a_guarda": len(paginas_guarda),
        "paginas_zeradas": len(paginas_hoje - paginas_guarda),
        "descartados": descartados,
    }


# ---------------------------------------------------------------------------
# RELATORIO 3 — A FOLGA DE COLA, nos tres baldes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Baldes:
    """A classificacao de UMA folga candidata contra os rotulos nao circulares.

    LE CERTO      a celula produziu um valor que o rotulo ACEITA
    NAO LE        a celula caiu por piso, margem, particao ou gramatica —
                  falha FECHADA, que e o comportamento seguro
    LE ERRADO     a celula produziu um valor que o rotulo REJEITA

    O terceiro balde e o unico que decide, e por isso ele guarda as celulas e
    nao so a contagem: uma folga recusada tem de poder dizer QUAL celula ela
    erraria, e com que numero.
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


@dataclass
class CelulaLarga:
    """Uma celula COM run largo E COM rotulo — a populacao que decide a folga.

    `rotulo` e o rotulo por IGUALDADE (a quantidade derivada de `Total` e
    `Unit price`). `contexto` e o rotulo por INTERVALO das colunas de MOEDA: as
    duas outras colunas da linha, ja conferidas LIMPAS, contra as quais o valor
    lido e testado por `total_no_intervalo`.

    Uma celula sem nenhum dos dois NAO ENTRA nesta populacao: um rotulo que nao
    existe nao mede nada.
    """

    chave: tuple
    coluna: str
    rotulo: int | None
    lido_hoje: int | None
    lido_por_folga: dict = field(default_factory=dict)
    contexto: dict | None = None

    def veredito(self, lido: int | None) -> str:
        if lido is None:
            return "nao_le"
        if self.rotulo is not None:
            return "certo" if int(lido) == int(self.rotulo) else "errado"
        if self.contexto is not None:
            valores = dict(self.contexto)
            valores[self.coluna] = int(lido)
            aceito = total_no_intervalo(
                valores.get("total"),
                valores.get("unitario"),
                valores.get("quantidade"),
            )
            if aceito is None:
                return "nao_le"
            return "certo" if aceito else "errado"
        return "nao_le"


def rotular_as_celulas_largas(
    resultado: ResultadoDaVarredura,
) -> list[CelulaLarga]:
    """A populacao ROTULADA de celulas com run largo, nas duas formas.

    QUANTITY, pelo rotulo DERIVADO. `quantidade_derivada(total, unitario)` nao
    ve um pixel da coluna Quantity. Ele so e calculado quando as duas colunas de
    moeda leem LIMPO (aceitas E sem run largo): derivar a partir de uma coluna
    que tambem esta mentindo mediria a leitura contra ela mesma.

    MOEDA, pelo rotulo de INTERVALO. Quando as OUTRAS duas colunas da linha leem
    LIMPO, `total_no_intervalo` rejeita um valor inventado sem fixar o certo.
    """
    populacao: list[CelulaLarga] = []
    for linha in resultado.linhas:
        celulas = linha.celulas
        total = celulas["total"]
        unitario = celulas["unitario"]
        quantidade = celulas["quantidade"]

        if quantidade.tem_run_largo and total.limpa and unitario.limpa:
            rotulo = quantidade_derivada(total.valor_hoje, unitario.valor_hoje)
            if rotulo is not None:
                populacao.append(
                    CelulaLarga(
                        chave=linha.chave,
                        coluna="quantidade",
                        rotulo=int(rotulo),
                        lido_hoje=quantidade.valor_hoje,
                    )
                )

        for coluna, celula in (("total", total), ("unitario", unitario)):
            if not celula.tem_run_largo:
                continue
            outras = [c for c in AS_TRES_COLUNAS if c != coluna]
            if not all(celulas[o].limpa for o in outras):
                continue
            contexto = {o: celulas[o].valor_hoje for o in outras}
            # O rotulo tem de existir para o contexto: se `total_no_intervalo`
            # nao opina nem com o valor de hoje, ele nao opinaria com nenhum.
            sonda = dict(contexto)
            sonda[coluna] = celula.valor_hoje if celula.valor_hoje else 1
            if (
                total_no_intervalo(
                    sonda.get("total"),
                    sonda.get("unitario"),
                    sonda.get("quantidade"),
                )
                is None
            ):
                continue
            populacao.append(
                CelulaLarga(
                    chave=linha.chave,
                    coluna=coluna,
                    rotulo=None,
                    lido_hoje=celula.valor_hoje,
                    contexto=contexto,
                )
            )
    return populacao


def reclassificar(
    resultado: ResultadoDaVarredura,
    cal: Calibracao,
    moldes: dict,
    limite: int,
    folgas,
) -> tuple[dict, float]:
    """Le TODAS as celulas com run largo em CADA folga candidata, EM MEMORIA.

    NENHUM PNG E REABERTO AQUI, e isso e desenho e nao otimizacao: a segmentacao
    no piso da coluna nao depende da folga, so a particao depende. A varredura
    irma varre o censo uma vez POR PISO CANDIDATO e por isso passa de 10
    minutos; aqui a estrutura do problema permite o contrario.

    ELA LE TODAS AS CELULAS LARGAS, E NAO SO AS ROTULADAS. Os TRES BALDES so
    olham a populacao rotulada — um rotulo que nao existe nao mede nada —, mas o
    RENDIMENTO em linhas completas depende tambem das celulas que HOJE NAO LEEM
    e que a particao recupera. Medir o rendimento so sobre as rotuladas o
    subestimaria calado, e o rendimento e metade do argumento contra a guarda.

    Devolve `{folga: {(chave, coluna): valor}}` e o relogio da metade.
    """
    piso = float(cal.mercado_limiar_de_leitura_de_glifo)
    margem = float(cal.mercado_margem_de_leitura_de_glifo)
    largas = [
        (linha.chave, coluna, linha.celulas[coluna])
        for linha in resultado.linhas
        for coluna in AS_TRES_COLUNAS
        if linha.celulas[coluna].tem_run_largo
    ]
    comeco = time.perf_counter()
    larguras = larguras_de_molde(moldes)
    leituras: dict = {}
    for folga in folgas:
        permitidas = larguras_com_folga(larguras, folga)
        da_folga: dict = {}
        for chave, coluna, celula in largas:
            if celula.mascara is None or celula.faixa is None:
                da_folga[(chave, coluna)] = None
                continue
            texto = ler_com_particao(
                celula.mascara,
                celula.faixa,
                celula.runs,
                moldes,
                piso,
                margem,
                limite,
                permitidas,
                celula.cache,
            )
            da_folga[(chave, coluna)] = _valor_da_coluna(coluna, texto)
        leituras[folga] = da_folga
    return leituras, time.perf_counter() - comeco


def classificar_folga(populacao: list[CelulaLarga], folga: int) -> Baldes:
    certo = 0
    nao_le = 0
    errado = []
    for larga in populacao:
        lido = larga.lido_por_folga.get(folga)
        veredito = larga.veredito(lido)
        if veredito == "certo":
            certo += 1
        elif veredito == "nao_le":
            nao_le += 1
        else:
            errado.append((larga.chave, larga.coluna, larga.rotulo, lido))
    return Baldes(certo=certo, nao_le=nao_le, errado=tuple(errado))


def baldes_de_hoje(populacao: list[CelulaLarga]) -> Baldes:
    """O comportamento de HOJE: sem guarda e sem particao."""
    certo = 0
    nao_le = 0
    errado = []
    for larga in populacao:
        veredito = larga.veredito(larga.lido_hoje)
        if veredito == "certo":
            certo += 1
        elif veredito == "nao_le":
            nao_le += 1
        else:
            errado.append(
                (larga.chave, larga.coluna, larga.rotulo, larga.lido_hoje)
            )
    return Baldes(certo=certo, nao_le=nao_le, errado=tuple(errado))


def baldes_da_guarda(populacao: list[CelulaLarga]) -> Baldes:
    """A GUARDA PURA: toda celula com run largo cai FECHADA, sem excecao."""
    return Baldes(certo=0, nao_le=len(populacao), errado=())


@dataclass(frozen=True)
class PropostaDaFolga:
    veredito: str
    folga: int | None
    causa: str | None
    tabela: dict
    baldes_da_folga: Baldes | None
    linha_do_veredito: str


def _exemplos(baldes: Baldes, quantos: int = 4) -> str:
    return ", ".join(
        f"{chave[0][9:]}/{chave[1]} L{chave[2]} {coluna} "
        f"rotulo {rotulo if rotulo is not None else 'intervalo'} lido {lido}"
        for chave, coluna, rotulo, lido in baldes.errado[:quantos]
    )


def propor_a_folga(
    populacao: list[CelulaLarga], teto: int | None = None
) -> PropostaDaFolga:
    """A folga com o maior LE CERTO entre as que NAO erram. Passo 1.

    A REGRA E UMA SO, E ELA E DE SEGURANCA ANTES DE RENDIMENTO: uma folga so
    pode ser proposta com o balde LE ERRADO VAZIO. Trocar falha FECHADA por
    numero errado plausivel e pior que o defeito de hoje (LEIT-02), e a
    sondagem do planejamento mediu exatamente isso acontecendo — afrouxar as
    larguras nao degrada devagar, inventa 54 numeros em bloco.

    A FOLGA PROPOSTA TEM A PROPRIA LINHA NA TABELA. Uma folga escolhida entre
    duas medidas seria interpolacao disfarcada de medicao; com passo 1 e sobre
    um numero de COLUNAS, nao existe nem valor entre duas.

    EMPATE DE LE CERTO ESCOLHE A MENOR FOLGA. A folga e o quanto se afrouxa a
    geometria: entre duas que rendem o mesmo, a menor e a que menos amplia o
    espaco de cortes possiveis, e portanto a que menos superficie oferece ao
    proximo frame que ninguem mediu.
    """
    teto = TETO_DA_FOLGA if teto is None else int(teto)
    tabela = {
        folga: classificar_folga(populacao, folga)
        for folga in range(0, teto + 1, PASSO_DA_VARREDURA)
    }

    def _reprovar(causa: str, linha: str) -> PropostaDaFolga:
        return PropostaDaFolga(
            veredito="REPROVADO",
            folga=None,
            causa=causa,
            tabela=tabela,
            baldes_da_folga=None,
            linha_do_veredito=linha,
        )

    if not populacao:
        return _reprovar(
            "populacao rotulada vazia",
            "REPROVADO por POPULACAO ROTULADA VAZIA: nenhuma celula com run "
            "largo tem rotulo nao circular disponivel. Sem rotulo nao ha "
            "medicao — e uma razao contra zero nao e medicao.",
        )

    limpas = [folga for folga in sorted(tabela) if not tabela[folga].erra]
    if not limpas:
        pior = tabela[min(tabela)]
        return _reprovar(
            "nenhuma folga tem o balde LE ERRADO vazio",
            "REPROVADO porque NENHUMA folga candidata de 0 a "
            f"{teto} tem o balde LE ERRADO vazio: a menor delas ja erra em "
            f"{len(pior.errado)} celula(s). Uma folga que inventa numero e pior "
            "que o defeito de hoje, porque troca falha FECHADA por numero "
            f"errado e plausivel (LEIT-02). Exemplos: {_exemplos(pior)}",
        )

    folga = max(limpas, key=lambda f: (tabela[f].certo, -f))
    baldes = tabela[folga]
    return PropostaDaFolga(
        veredito="PROPOSTO",
        folga=int(folga),
        causa=None,
        tabela=tabela,
        baldes_da_folga=baldes,
        linha_do_veredito=(
            f"PROPOSTO mercado_folga_de_cola_do_glifo = {folga} "
            f"(LE CERTO {baldes.certo}, NAO LE {baldes.nao_le}, "
            f"LE ERRADO {len(baldes.errado)} de {baldes.total} celulas "
            "rotuladas com run largo)"
        ),
    )


# ---------------------------------------------------------------------------
# A GRAVACAO — load-mutate-save, UMA chave
# ---------------------------------------------------------------------------


def gravar(caminho: Path, folga: int) -> None:
    """Load-mutate-save de UMA chave. Nunca montar uma `Calibracao` do zero.

    Montar do zero apagaria os 13 moldes de glifo e as 3 ancoras — o modo de
    falha REAL da janela quebrada #13, que custou uma recuperacao a mao ao
    usuario em 2026-08-30. Aqui o arquivo e lido como JSON cru, UMA chave e
    mutada, e o `os.replace` troca o arquivo inteiro de uma vez: uma escrita
    interrompida no meio nao deixa o `calibration.json` em pedacos.

    NO RAMO REPROVADO O QUE SE GRAVA E A FOLGA `0`, e isso e resultado e nao
    silencio: com folga 0 a particao so aceita larguras de MOLDE, que e o
    afrouxamento minimo possivel. Se nem isso passar, a ausencia da chave e o
    comportamento seguro — a GUARDA — e a ferramenta nao grava nada. O
    precedente e literal: o 02-02 gravou `mercado_tolerancia_do_cruzamento` como
    `None`, uma guarda DESLIGADA, com o numero que a derrubou ao lado.
    """
    caminho = Path(caminho)
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados["mercado_folga_de_cola_do_glifo"] = int(folga)
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
# main
# ---------------------------------------------------------------------------


def _linha_da_distribuicao(contagem: Counter, niveis) -> str:
    return "  ".join(f"{nivel}:{contagem.get(nivel, 0):>5}" for nivel in niveis)


def main(argv=None) -> int:
    analisador = argparse.ArgumentParser(
        description=(
            "Mede a largura de run, o vale, o custo da guarda e a folga de "
            "cola sobre as 8 gravacoes do censo, com o portao de layout ligado."
        )
    )
    analisador.add_argument("--gravacoes", default=str(RAIZ / "recordings"))
    analisador.add_argument("--calibracao", default=str(RAIZ / "calibration.json"))
    analisador.add_argument("--gravar", action="store_true")
    opcoes = analisador.parse_args(argv)

    gravacoes = Path(opcoes.gravacoes).resolve()
    calibracao = Path(opcoes.calibracao).resolve()
    relogio_total = time.perf_counter()

    print("=" * 78)
    print("MEDICAO DA LARGURA DE RUN E DA FOLGA DE COLA - 02-08 Task 1")
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
        "mercado_limiar_de_brilho_da_quantidade",
        "mercado_templates_de_digito",
        "mercado_ancoras",
    ):
        if getattr(cal, chave) is None:
            print("")
            print(
                f"ERRO: {chave} esta ausente no calibration.json. Rode "
                "calibrar-mercado.bat."
            )
            return 4

    moldes = glifos_de_calibracao(cal.mercado_templates_de_digito)
    larguras = larguras_de_molde(moldes)
    limite = limite_de_glifo_unico(moldes)
    print("")
    print("A GEOMETRIA DERIVADA DOS MOLDES (nao e chave, e nao vai para o JSON):")
    de_um = [r for r in moldes if len(r) == 1]
    print(f"  moldes de UM caractere   : {len(de_um)} de {len(moldes)}")
    for rotulo, molde in sorted(
        (r, m) for r, m in moldes.items() if len(r) == 1
    ):
        print(f"    {rotulo!r:<6} largura {molde.shape[1]}")
    for rotulo, molde in sorted(
        (r, m) for r, m in moldes.items() if len(r) != 1
    ):
        print(f"    {rotulo!r:<10} largura {molde.shape[1]}  (PALAVRA, fora)")
    print(f"  larguras_de_molde        : {larguras}")
    print(f"  limite_de_glifo_unico    : {limite}")

    print("")
    print("Varrendo o censo UMA VEZ (portao de layout LIGADO)...")
    resultado = varrer(gravacoes, cal, limite)
    celulas = resultado.celulas
    print(f"  paginas no layout calibrado : {len(resultado.paginas)}")
    print(f"  linhas de grade colhidas    : {len(resultado.linhas)}")
    print(f"  celulas de numero colhidas  : {len(celulas)}")
    for nome in GRAVACOES_DO_CENSO:
        print(
            f"  {nome[9:]:<36} "
            f"{resultado.abertos_por_gravacao.get(nome, 0):>4} paginas, "
            f"{resultado.recusadas_por_layout.get(nome, 0):>4} recusadas por "
            "layout"
        )
    if not resultado.linhas:
        print("")
        print("ERRO: nenhuma linha colhida. Sem populacao nao ha medicao.")
        return 5

    # -----------------------------------------------------------------
    # RELATORIO 1 - O VALE
    # -----------------------------------------------------------------
    print("")
    print("=" * 78)
    print("RELATORIO 1 - O VALE: largura MAXIMA por celula, nas duas populacoes")
    print("=" * 78)
    distribuicao = classificar_por_largura(celulas, limite)
    todos = sorted(
        {
            w
            for d in distribuicao.values()
            for contagem in (d["aceitas"], d["recusadas"])
            for w in contagem
        }
    )
    # TODA largura observada entra na tabela. Cortar a cauda esconderia
    # exatamente o lado da populacao que prova que ha DUAS populacoes.
    niveis = todos
    print("  larguras observadas: " + ", ".join(str(w) for w in todos))
    for coluna in AS_TRES_COLUNAS:
        d = distribuicao[coluna]
        print("")
        print(f"  {coluna.upper()}  ({d['n_aceitas']} aceitas hoje, "
              f"{d['n_recusadas']} recusadas hoje)")
        print("    ACEITAS  : " + _linha_da_distribuicao(d["aceitas"], niveis))
        print("    RECUSADAS: " + _linha_da_distribuicao(d["recusadas"], niveis))
        print(
            f"    menor run largo entre as ACEITAS: {d['menor_larga_aceita']}"
        )

    vale, menor_larga = niveis_do_vale(distribuicao, limite)
    print("")
    aceitas_no_vale = sum(
        d["aceitas"].get(w, 0) for d in distribuicao.values() for w in vale
    )
    if menor_larga is None:
        print(
            "  NENHUMA celula aceita tem run acima do limite: nao ha defeito a "
            "medir neste censo."
        )
    else:
        print(
            f"  O VALE vai de {limite + 1} a {menor_larga - 1} "
            f"({len(vale)} nivel(is)), e ele tem {aceitas_no_vale} celula(s) "
            "aceita(s)."
        )
    vale_vazio = bool(vale) and aceitas_no_vale == 0
    if not vale_vazio:
        print("")
        print(
            "  ATENCAO ALTA: O VALE NAO ESTA VAZIO. O limite derivado "
            f"({limite}) esta na borda de um nivel POVOADO, e nao no meio de "
            "um vale. A resposta da pergunta 4 do plano MUDOU: a Task 2 NAO "
            "COMECA e o plano volta a mesa."
        )

    # -----------------------------------------------------------------
    # RELATORIO 2 - O CUSTO DA GUARDA
    # -----------------------------------------------------------------
    print("")
    print("=" * 78)
    print("RELATORIO 2 - O CUSTO DA GUARDA PURA, por celula, linha e pagina")
    print("=" * 78)
    custo = custo_da_guarda(resultado)
    print("  coluna         aceitas hoje   com a guarda   perdidas")
    for coluna in AS_TRES_COLUNAS:
        c = custo["por_coluna"][coluna]
        pct = 100.0 * c["perdidas"] / c["hoje"] if c["hoje"] else 0.0
        print(
            f"  {coluna:<14} {c['hoje']:>12} {c['com_a_guarda']:>14} "
            f"{c['perdidas']:>10}  ({pct:.2f}%)"
        )
    delta = custo["linhas_hoje"] - custo["linhas_com_a_guarda"]
    pct = 100.0 * delta / custo["linhas_hoje"] if custo["linhas_hoje"] else 0.0
    print("")
    print(
        f"  LINHAS com as 3 colunas aceitas : {custo['linhas_hoje']} -> "
        f"{custo['linhas_com_a_guarda']}  (-{delta}, -{pct:.2f}%)"
    )
    print(
        f"  PAGINAS com pelo menos 1 linha  : {custo['paginas_hoje']} -> "
        f"{custo['paginas_com_a_guarda']}"
    )
    print(f"  PAGINAS que ficam com ZERO linha: {custo['paginas_zeradas']}")
    print("")
    print("  OS TEXTOS QUE A GUARDA DESCARTA, agrupados por valor:")
    for (coluna, texto), quantos in custo["descartados"].most_common(25):
        print(f"    {coluna:<12} {texto!r:<14} x{quantos}")

    # -----------------------------------------------------------------
    # RELATORIO 3 - A FOLGA DE COLA
    # -----------------------------------------------------------------
    print("")
    print("=" * 78)
    print("RELATORIO 3 - A FOLGA DE COLA, tres baldes, DOIS rotulos")
    print("=" * 78)
    populacao = rotular_as_celulas_largas(resultado)
    por_populacao = Counter(larga.coluna for larga in populacao)
    largas_totais = sum(
        1 for c in celulas if c.tem_run_largo and c.coluna in AS_TRES_COLUNAS
    )
    print(
        f"  celulas com run largo (todas)          : {largas_totais}"
    )
    print(
        f"  celulas com run largo E COM ROTULO     : {len(populacao)}"
    )
    for coluna in AS_TRES_COLUNAS:
        rotulo = (
            "derivado de Total x Unit price"
            if coluna == "quantidade"
            else "intervalo (as outras duas colunas LIMPAS)"
        )
        print(f"    {coluna:<12} {por_populacao.get(coluna, 0):>5}  rotulo: {rotulo}")
    print(
        "  (um rotulo que nao existe para a populacao nao mede nada; as "
        "celulas sem rotulo ficam FORA da tabela abaixo)"
    )

    folgas = list(range(0, TETO_DA_FOLGA + 1, PASSO_DA_VARREDURA))
    leituras, segundos_da_particao = reclassificar(
        resultado, cal, moldes, limite, folgas
    )
    for larga in populacao:
        for folga in folgas:
            larga.lido_por_folga[folga] = leituras[folga].get(
                (larga.chave, larga.coluna)
            )
    proposta = propor_a_folga(populacao, teto=TETO_DA_FOLGA)

    hoje = baldes_de_hoje(populacao)
    guarda = baldes_da_guarda(populacao)
    print("")
    print("  AS TRES CAUSAS, EM SEPARADO (o numero do ledger nao pode ser")
    print("  atribuido a errada):")
    print(
        f"    HOJE (sem guarda, sem particao) : LE CERTO {hoje.certo:>4}  "
        f"NAO LE {hoje.nao_le:>4}  LE ERRADO {len(hoje.errado):>4}"
    )
    if hoje.erra:
        print(f"      exemplos: {_exemplos(hoje)}")
    print(
        f"    GUARDA PURA (cai FECHADA)       : LE CERTO {guarda.certo:>4}  "
        f"NAO LE {guarda.nao_le:>4}  LE ERRADO {len(guarda.errado):>4}"
    )
    zero = proposta.tabela.get(0)
    if zero is not None:
        print(
            f"    FOLGA 0 (larguras de MOLDE)     : LE CERTO {zero.certo:>4}  "
            f"NAO LE {zero.nao_le:>4}  LE ERRADO {len(zero.errado):>4}"
        )

    print("")
    print(
        f"  A TABELA DE CANDIDATAS (PASSO_DA_VARREDURA = {PASSO_DA_VARREDURA}, "
        "sem saltos):"
    )
    print(
        "    folga  larguras permitidas             CERTO  NAO LE  ERRADO  "
        "celulas largas que MUDARAM de leitura"
    )
    for folga in sorted(proposta.tabela):
        baldes = proposta.tabela[folga]
        marca = "  <=" if folga == proposta.folga else ""
        permitidas = larguras_com_folga(larguras, folga)
        anterior = leituras.get(folga - PASSO_DA_VARREDURA)
        if anterior is None:
            mudaram = "-"
        else:
            mudaram = str(
                sum(
                    1
                    for chave, valor in leituras[folga].items()
                    if anterior.get(chave) != valor
                )
            )
        print(
            f"    {folga:>5}  {str(permitidas):<31} {baldes.certo:>5} "
            f"{baldes.nao_le:>7} {len(baldes.errado):>7}  {mudaram:>8}{marca}"
        )
        if baldes.erra:
            print(f"           erra em: {_exemplos(baldes, 3)}")

    if proposta.folga is not None:
        seguinte = proposta.folga + PASSO_DA_VARREDURA
        if seguinte in proposta.tabela:
            b = proposta.tabela[seguinte]
            print("")
            print(
                f"  A FOLGA IMEDIATAMENTE SEGUINTE ({seguinte}), para que se "
                "veja o que acontece ao afrouxar:"
            )
            print(
                f"    LE CERTO {b.certo}, NAO LE {b.nao_le}, LE ERRADO "
                f"{len(b.errado)}"
            )

    # O RENDIMENTO, nas duas pontas.
    rendimento = rendimento_com_a_folga(resultado, leituras, proposta.folga)
    print("")
    print("  O RENDIMENTO EM LINHAS COMPLETAS (as 3 colunas aceitas):")
    print(f"    hoje                    : {custo['linhas_hoje']}")
    print(f"    com a GUARDA pura       : {custo['linhas_com_a_guarda']}")
    print(f"    com a folga proposta    : {rendimento['linhas']}")
    print(
        f"    paginas com >=1 linha   : {custo['paginas_hoje']} (hoje) -> "
        f"{rendimento['paginas']} (com a folga)"
    )

    # -----------------------------------------------------------------
    # RELATORIO 4 - O RELOGIO DENTRO DO TICK
    # -----------------------------------------------------------------
    print("")
    print("=" * 78)
    print("RELATORIO 4 - O CUSTO DA PARTICAO DENTRO DO TICK DE 1 Hz")
    print("=" * 78)
    linhas_largas = [
        linha
        for linha in resultado.linhas
        if any(linha.celulas[c].tem_run_largo for c in AS_TRES_COLUNAS)
    ]
    pior_ms, medio_ms = custo_por_linha_larga(
        resultado, linhas_largas, cal, moldes, limite,
        larguras_com_folga(larguras, proposta.folga or 0),
    )
    print(f"  linhas de grade colhidas      : {len(resultado.linhas)}")
    print(
        f"  linhas com run largo          : {len(linhas_largas)} "
        f"({100.0 * len(linhas_largas) / max(1, len(resultado.linhas)):.1f}%)"
    )
    print(f"  custo MEDIO por linha larga   : {medio_ms:.2f} ms")
    print(f"  custo do PIOR caso            : {pior_ms:.2f} ms")
    print(
        f"  folga contra o tick de 1 Hz   : {1000.0 / max(pior_ms, 1e-9):.0f}x "
        f"({1000.0 / max(pior_ms, 1e-9):.2e})"
    )
    estourou = pior_ms > TETO_DE_MILISSEGUNDOS_POR_LINHA
    if estourou:
        print("")
        print(
            f"  PARADA: o pior caso ({pior_ms:.1f} ms) passa do teto de "
            f"{TETO_DE_MILISSEGUNDOS_POR_LINHA:.0f} ms. Uma peneira que estoura "
            "o tick para o scanner de olhar a party."
        )

    # -----------------------------------------------------------------
    # O RELOGIO DA FERRAMENTA, NAS DUAS METADES
    # -----------------------------------------------------------------
    total_segundos = time.perf_counter() - relogio_total
    print("")
    print("=" * 78)
    print("O RELOGIO DA FERRAMENTA, NAS DUAS METADES")
    print("=" * 78)
    print(f"  passagem UNICA pelo censo        : {resultado.segundos:>7.1f} s")
    print(
        f"  reclassificacao das {len(folgas)} folgas    : "
        f"{segundos_da_particao:>7.1f} s "
        f"({segundos_da_particao / max(1, len(folgas)):.1f} s por folga)"
    )
    print(f"  TOTAL                            : {total_segundos:>7.1f} s")
    if total_segundos > TETO_DE_SEGUNDOS_DA_FERRAMENTA:
        print(
            f"  ATENCAO: acima do teto de {TETO_DE_SEGUNDOS_DA_FERRAMENTA:.0f} "
            "s. Conferir se o censo esta sendo reaberto por folga — so isso "
            "explica uma ordem de grandeza a mais."
        )

    # -----------------------------------------------------------------
    # O VEREDITO
    # -----------------------------------------------------------------
    linha_final = proposta.linha_do_veredito
    if not vale_vazio:
        linha_final = (
            "REPROVADO porque O VALE NAO ESTA VAZIO: o limite derivado "
            f"({limite}) tem celula(s) aceita(s) logo acima dele, entao ele "
            "esta na borda de um nivel povoado e nao no meio de um vale. A "
            "Task 2 NAO COMECA."
        )
    elif estourou:
        linha_final = (
            f"REPROVADO por RELOGIO: o pior caso da particao ({pior_ms:.1f} ms) "
            f"passa do teto de {TETO_DE_MILISSEGUNDOS_POR_LINHA:.0f} ms por "
            "linha. Uma peneira que estoura o tick para o scanner de olhar a "
            "party."
        )

    print("")
    print("O QUE VAI PARA O calibration.json:")
    if linha_final.startswith("PROPOSTO"):
        print(f"  mercado_folga_de_cola_do_glifo = {proposta.folga}")
    else:
        print(
            "  (NADA. Sem a chave, a producao aplica a GUARDA e a celula com "
            "run largo cai FECHADA — que e o comportamento SEGURO, e nao o de "
            "hoje.)"
        )

    if opcoes.gravar and linha_final.startswith("PROPOSTO"):
        gravar(calibracao, int(proposta.folga))
        print("")
        print("GRAVADO em " + str(calibracao) + " (load-mutate-save).")
    elif opcoes.gravar:
        print("")
        print("(REPROVADO: nada gravado. A ausencia da chave e a guarda.)")
    else:
        print("")
        print("(nada gravado - rode de novo com --gravar para persistir)")

    print("")
    print(linha_final)
    return 0


def rendimento_com_a_folga(
    resultado: ResultadoDaVarredura,
    leituras: dict,
    folga: int | None,
) -> dict:
    """Linhas completas e paginas sob a folga proposta.

    UMA CELULA ESTREITA CONTA COMO HOJE, e uma celula LARGA conta quando a
    particao devolveu valor naquela folga. Sem folga (a GUARDA) nenhuma celula
    larga conta. O ganho vem das celulas que HOJE NAO LEEM e a particao recupera
    — nao apenas das que a guarda perderia.
    """
    da_folga = leituras.get(folga, {}) if folga is not None else {}
    linhas = 0
    paginas = set()
    for linha in resultado.linhas:
        boa = True
        for coluna in AS_TRES_COLUNAS:
            celula = linha.celulas[coluna]
            if celula.tem_run_largo:
                if da_folga.get((linha.chave, coluna)) is None:
                    boa = False
                    break
            elif not celula.aceita_hoje:
                boa = False
                break
        if boa:
            linhas += 1
            paginas.add(linha.chave[:2])
    return {"linhas": linhas, "paginas": len(paginas)}


def custo_por_linha_larga(
    resultado: ResultadoDaVarredura,
    linhas_largas: list,
    cal: Calibracao,
    moldes: dict,
    limite: int,
    larguras: tuple,
) -> tuple[float, float]:
    """O relogio da particao por LINHA, sem o cache — como no tick real.

    O cache da colheita e da FERRAMENTA e nao da producao: no tick cada frame e
    novo. Aqui ele e esvaziado para que o numero medido seja o que o scanner
    pagaria.
    """
    piso = float(cal.mercado_limiar_de_leitura_de_glifo)
    margem = float(cal.mercado_margem_de_leitura_de_glifo)
    pior = 0.0
    soma = 0.0
    contadas = 0
    for linha in linhas_largas:
        comeco = time.perf_counter()
        for coluna in AS_TRES_COLUNAS:
            celula = linha.celulas[coluna]
            if celula.mascara is None or celula.faixa is None:
                continue
            ler_com_particao(
                celula.mascara,
                celula.faixa,
                celula.runs,
                moldes,
                piso,
                margem,
                limite,
                larguras,
                None,
            )
        gasto = (time.perf_counter() - comeco) * 1000.0
        pior = max(pior, gasto)
        soma += gasto
        contadas += 1
    return pior, (soma / contadas if contadas else 0.0)


if __name__ == "__main__":
    raise SystemExit(main())
