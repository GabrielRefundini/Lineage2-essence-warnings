"""O DESENHO do modo mercado: linha ao vivo e resumo da sessao (LEIT-04).

ELAS DEVOLVEM TEXTO E NUNCA IMPRIMEM
=====================================
E a disciplina que `console.moldurar` ja segue neste projeto, e o que torna o
desenho afirmavel por teste sem capturar stdout e sem montar um laco. Quem
imprime e o laco, com `log.info`, e assim a mesma string vai para o console E
para o `scanner.log` rotativo - que e onde a forense de um farm de tres horas
mora.

TEXTO PURO, SEM DEPENDENCIA NOVA
=================================
O `CLAUDE.md` recomenda `rich`, e ele NAO esta instalado. A razao de nao
instala-lo e DOUTRINA DE ZERO-INSTALL - o `vigiar-party.bat` roda
`pip install -r requirements.txt` na primeira execucao, e cada dependencia nova
e um jeito novo de esse arranque falhar na maquina do usuario.

A JUSTIFICATIVA ERRADA, CORRIGIDA POR ESCRITO: a primeira redacao do
`04-CONTEXT.md` dizia que o FIRE-01 barraria o `rich`. NAO BARRARIA. A banlist
do FIRE-01 (`tests/test_firewall_escopo.py`) e so de SINTESE DE INPUT -
`pyautogui`, `pynput`, `keyboard`, `mouse`, `pydirectinput`, autoit - e ela nao
tem nada a dizer sobre uma biblioteca de console. A decisao continua de pe pelo
zero-install; o argumento que a sustentava caiu, e um argumento que cai precisa
dizer que caiu.

AS DUAS METADES, SEMPRE
========================
No censo, 151 paginas lidas contra 189 PERDIDAS. Um console que mostrasse so a
metade boa faria o usuario confiar numa cobertura que nao existe e sair do farm
achando que coletou o dobro. Por isso "perdidas" aparece na linha ao vivo, no
resumo, e mesmo quando "lidas" e zero.
"""

from __future__ import annotations

import textwrap
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from fractions import Fraction

from . import console
from .mercado_analise import (
    PAPEL_PRODUTO,
    descrever_a_tendencia,
    margem_de_craft,
    mediana_dos_unitarios,
    menor_pedido_visivel,
    ordenar_para_o_console,
    recencia_do_preco,
    tendencia,
)

# A SENTINELA DA SERIE DA ADENA (05-01). Ela e a UNICA coisa que a exibicao
# precisa saber sobre a aba Adena, e ela chega sem aresta de import nova:
# `mercado_catalogo` so importa `.config`, entao nao ha ciclo por aqui.
from .mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA

# A IDENTIDADE DE UMA OFERTA VEM DO REGISTRO, e nao e reescrita aqui: e a mesma
# `serie + total + quantidade` com que o CSV dedupa (D-05), e a `TravaDoDestaque`
# usa exatamente ela. Nao ha ciclo: `mercado_registro` so importa
# `mercado_catalogo` em tempo de execucao e nunca este modulo.
from .mercado_registro import chave_da_observacao

# Os SETE contadores publicos do `LeitorDePagina`, com o rotulo que o usuario le.
# A ordem e a da leitura humana: primeiro as duas metades que julgam a sessao,
# depois os tres estados que explicam o que aconteceu com o resto, e por fim os
# dois sinais de saude da captura.
ROTULOS_DOS_CONTADORES = (
    ("paginas_lidas", "paginas lidas"),
    ("paginas_perdidas", "paginas PERDIDAS"),
    ("paginas_vazias", "paginas vazias (sem conteudo)"),
    ("paginas_de_outro_layout", "paginas de outro layout"),
    ("ticks_com_painel_aberto", "ticks com o painel aberto"),
    ("frames_congelados", "frames congelados"),
    ("linhas_descartadas", "linhas descartadas"),
)


@dataclass
class OrcamentoDoTick:
    """Quanto tempo cada volta custou, e quantas estouraram o intervalo.

    E a metade de DETC-02 que o programa PODE afirmar sobre si mesmo. O laco ja
    calcula `agora - inicio` para compensar a deriva da cadencia; guardar essa
    lista custa um `append` por tick e transforma "acho que nao pesou" num
    numero que o usuario le no fim da sessao.

    O que ela NAO mede esta escrito no resumo: contencao entre TRES processos e
    propriedade do SISTEMA (CPU, GPU, sessoes WGC, agendador do Windows), e so o
    portao humano de campo a fecha.
    """

    limite: float
    tempos: list[float] = field(default_factory=list)

    def registrar(self, segundos: float) -> None:
        self.tempos.append(float(segundos))

    @property
    def total(self) -> int:
        return len(self.tempos)

    @property
    def estouros(self) -> int:
        return sum(1 for t in self.tempos if t > self.limite)

    def _quantil(self, fracao: float) -> float:
        """Indexacao sobre a lista ORDENADA, sem dependencia nova.

        `statistics.quantiles` interpola e precisa de pelo menos dois pontos;
        aqui a amostra pode ter UM tick (o usuario fechou logo), e um resumo que
        levantasse ali seria pior que um numero grosseiro. O metodo e o do
        percentil mais proximo, que e o que se espera de "o tick tipico".
        """
        if not self.tempos:
            return 0.0
        ordenados = sorted(self.tempos)
        indice = min(len(ordenados) - 1, int(fracao * len(ordenados)))
        return ordenados[indice]

    @property
    def p50(self) -> float:
        return self._quantil(0.50)

    @property
    def p95(self) -> float:
        return self._quantil(0.95)

    @property
    def maximo(self) -> float:
        return max(self.tempos) if self.tempos else 0.0


def acumular_motivos(acumulados: Counter, leitura) -> None:
    """Soma os motivos de descarte DESTE tick no acumulado da SESSAO.

    O campo `motivos` de uma leitura carrega so o que aquele frame produziu, e
    nao um acumulado - somar por sessao e trabalho de quem chama, e e por isso
    que isto e uma funcao e nao uma propriedade do leitor. Sem ela o resumo
    diria "oclusao: 1" depois de uma hora com a tooltip aberta.

    `leitura` pode ser `None` (tick sem pagina lida) e isso nao e caso especial:
    nao havia motivo nenhum para somar.
    """
    if leitura is None:
        return
    acumulados.update(getattr(leitura, "motivos", ()) or ())


# O ESTADO que a linha ao vivo NOMEIA quando o painel esta aberto e o layout
# recusado. Ele e uma CONSTANTE, e nao uma string montada no lugar, para que o
# teste de controle negativo possa afirmar a AUSENCIA dele sem transcrever o
# texto (uma transcricao envelheceria em silencio no dia em que a frase mudasse).
#
# ELE DIZ O QUE FAZER, e nao so o que houve. "Layout recusado" sozinho e um
# diagnostico que o usuario nao sabe atender; o aviso alto de `mercado_pagina`
# ja explica a razao inteira uma vez, e o que esta linha precisa carregar por
# tick e a acao.
AVISO_DO_LAYOUT_RECUSADO = (
    "PARADO: esta aba NAO e o layout calibrado, entao nenhuma linha e lida. "
    "Abra a grade de negociacao do World Exchange, ou recalibre o mercado "
    "no layout que voce quer ler."
)


def linha_ao_vivo(leitor, contagem, ultimo_item, *, layout_recusado: bool) -> str:
    """A repintada de 1 Hz: as DUAS metades e o ultimo item reconhecido.

    Ela devolve UMA linha, e quem chama a emite A CADA TICK COM O PAINEL
    ABERTO - na cadencia da CAPTURA, e nunca por pagina aceita. A distincao e o
    requisito: por pagina aceita, o console emudeceria justamente no tick em que
    a metade PERDIDA cresce, e no censo foram 151 lidas contra 189 perdidas.
    Com o painel FECHADO ela nao sai, porque ali quem responde "o modo esta
    vivo?" e a linha de transicao (ver `laco_do_mercado`).

    NUMERO CONGELADO PARECE DEFEITO — E A MESMA CLASSE DO CAMPO VAZIO. Medido em
    producao (2026-09-01 09:38): com a aba Adena aberta, esta linha saia a cada
    tick com `lidas 85 | perdidas 2 | gravadas 2` parados e nada dizia por que.
    O aviso de layout de `mercado_pagina` tem LATCH — sai UMA vez na transicao,
    o que e certo para nao poluir o log —, mas ele rola para fora da tela, e o
    que sobra parece o scanner ter travado. O usuario chegou a concluir isso, e
    nao era verdade. Por isso o ESTADO viaja na linha que JA SAI, e nao como um
    aviso novo por tick: e o mesmo remedio do `(nenhum ainda)` logo abaixo.

    `layout_recusado` NAO TEM VALOR DE FABRICA, e a ausencia e o mecanismo. Um
    default deixaria o laco esquecer de passa-lo e o defeito voltaria inteiro
    com esta funcao verde no teste de unidade — a mesma razao pela qual
    `TravaDoDestaque.anunciar` devolve o TEXTO em vez de um booleano.

    O QUE ELA NAO MOSTRA, E POR QUE: o `residuo_do_cruzamento`. A guarda de
    cruzamento esta DESLIGADA por medicao (02-02), entao o residuo e observacao
    e nao veredito; ele ja esta em coluna propria no CSV, para o usuario olhar no
    Sheets com calma. Num repintar de um segundo ele so competiria por atencao
    com os dois numeros que julgam a sessao.

    `ultimo_item` pode ser `None` no comeco, e ai a linha diz isso por extenso em
    vez de mostrar campo vazio: campo vazio parece defeito.
    """
    linha = (
        f"mercado | lidas {leitor.paginas_lidas} | "
        f"perdidas {leitor.paginas_perdidas} | "
        f"gravadas {contagem.observacoes} | "
        f"ultimo item: {ultimo_item if ultimo_item else '(nenhum ainda)'}"
    )
    # O ESTADO ACRESCENTA, E NUNCA SUBSTITUI as duas metades: elas sao o que
    # julga a sessao, e some-las aqui faria o usuario perder a contagem
    # justamente no minuto em que ele precisa saber quanto ja tinha coletado.
    if layout_recusado:
        linha = f"{linha} | {AVISO_DO_LAYOUT_RECUSADO}"
    return linha


# ---------------------------------------------------------------------------
# OS NUMEROS, ESCRITOS DE UM JEITO SO
# ---------------------------------------------------------------------------


def formatar_centesimos(centesimos: int) -> str:
    """Centesimos inteiros -> `1.480,00`, no formato que o jogo mostra.

    O CSV guarda INTEIRO em centesimos de proposito (Fase 3): ponto flutuante
    para dinheiro e a fonte classica de um centavo que aparece do nada. A
    conversao para virgula acontece SO aqui, na formatacao, e nunca antes de
    comparar.
    """
    inteiro, resto = divmod(int(centesimos), 100)
    return f"{inteiro:,}".replace(",", ".") + f",{resto:02d}"


def formatar_unitario_derivado(unitario: Fraction) -> str:
    """O unitario com a MARCA DE DERIVADO colada, e o arredondamento so aqui.

    ELE NAO ESTA NO CSV, E ISSO E DECISAO (D-02): o que o jogo exibe e derivacao
    ARREDONDADA a duas casas, e reconstruir o total a partir dela devolve um
    numero que nunca existiu na tela - medido, `40,00` por 48 unidades aparece
    como `0,83`, e `0,83 x 48 = 39,84`. A Fase 3 guarda o que a tela AFIRMA.

    A MARCA `(derivado)` NO TEXTO E O QUE IMPEDE ALGUEM DE TRATA-LO COMO DADO
    GRAVADO. Sem ela, alguem copia a linha para o WhatsApp e o numero derivado
    vira "o que o scanner leu", que e falso.

    O arredondamento acontece SO nesta funcao, sobre a `Fraction` exata: a
    comparacao entre ofertas ja aconteceu, e ela aconteceu sem perder um bit.
    """
    return f"{formatar_centesimos(round(unitario))} por unidade (derivado)"


# A UNIDADE UTIL DA TAXA DE CAMBIO, E A UNICA COISA QUE A EXIBICAO PRECISA
# SABER SOBRE A ABA ADENA (ADEN-04).
#
# Uma oferta de adena e da ordem de dez milhoes de unidades, entao o unitario
# por ADENA e da ordem de um milesimo de centesimo — inexibivel em duas casas.
# O milhao e a escala em que o numero volta a ser legivel por um humano: "11,60
# XM por milhao" e o que o usuario diz em voz alta.
#
# ELA MORA AQUI E NAO NO `calibration.json` porque nao e medicao nem limiar: e
# a escala em que a taxa se fala, do mesmo jeito que `ADENA_POR_INCREMENTO`
# mora no fonte por ser como o jogo escreve a coluna. Grava-la na calibracao
# criaria duas verdades sobre uma unidade so.
#
# E ELA E DE EXIBICAO, SO. `mercado_analise` continua sem saber que existe aba:
# menor pedido, mediana e tendencia comparam `Fraction(total, quantidade)`
# exata, e a escala nao muda ordenacao nenhuma.
UNIDADE_DA_TAXA = 1_000_000


def formatar_taxa_derivada(taxa: Fraction) -> str:
    """A taxa da Adena em XM por MILHAO de adena, com a marca de derivado.

    IRMA DE `formatar_unitario_derivado`, E NAO UM PARAMETRO COM DEFAULT — e a
    razao esta MEDIDA: `round(Fraction(11600, 10_000_000))` vale **zero**. A
    taxa por unidade nao e apenas pequena, ela e INEXIBIVEL em centesimos, e
    chamar o formatador errado imprimiria `0,00 por unidade (derivado)` com
    toda a confianca do mundo. Um default e uma chamada que alguem esquece de
    passar; duas funcoes com nomes diferentes sao duas coisas que ninguem
    confunde por omissao.

    A CONTA, ESCRITA POR EXTENSO porque a pesquisa a errou por um fator de dez
    (`05-RESEARCH.md:621` diz `116,00`):

        10.000.000 de adena por 116,00 XM
          -> taxa = Fraction(11600, 10_000_000) centesimos POR ADENA
          -> x 1.000.000 = 1.160 centesimos por milhao
          -> 1.160 centesimos = 11,60 XM por milhao

    O erro da pesquisa foi carregar o `11600` intacto para depois da
    multiplicacao, como se ele ja fosse o resultado dela. O ROADMAP e o
    `05-CONTEXT.md` trazem o `11,60`, e ha teste sobre os dois pares que o
    usuario viu na tela (`10M/116,00 -> 11,60` e `15M/300,00 -> 20,00`).

    A MARCA `(derivado)` PELA MESMA RAZAO DA IRMA: o CSV guarda `total` e
    `quantidade`, e a taxa e derivacao. Sem o rotulo, alguem copia a linha para
    o WhatsApp e o numero derivado vira "o que o scanner leu", que e falso.

    O ARREDONDAMENTO ACONTECE SO AQUI, sobre a `Fraction` exata — a comparacao
    entre ofertas ja aconteceu, e ela aconteceu sem perder um bit.
    """
    return (
        f"{formatar_centesimos(round(taxa * UNIDADE_DA_TAXA))} "
        f"XM por milhao de adena (derivado)"
    )


def formatador_do_unitario(chave_da_serie: str):
    """A serie -> qual das duas irmas a desenha. UM ponto de decisao, e so um.

    QUATRO `if` ESPALHADOS PELOS QUATRO PONTOS DE CHAMADA DIVERGIRIAM, e o dia
    em que um deles divergisse ele imprimiria `0,00` — o modo de falha mais
    convincente que este modulo tem. Concentrar a escolha aqui e o que faz
    "menor pedido" e "mediana" da MESMA serie nao poderem sair em unidades
    diferentes.

    O CRITERIO E A `chave_da_serie` CONTRA `CHAVE_DA_SERIE_DA_ADENA` (D-A), e
    nao o nome exibido: o nome e rotulo e o OCR o faz oscilar, enquanto a chave
    da Adena e uma SENTINELA — ela nao vem de leitura nenhuma, foi escrita pelo
    05-01 exatamente para carregar esta identidade.
    """
    if chave_da_serie == CHAVE_DA_SERIE_DA_ADENA:
        return formatar_taxa_derivada
    return formatar_unitario_derivado


def descrever_a_quantidade(chave_da_serie: str, quantidade: int) -> str:
    """`6 unidades` para um item, `10.000.000 de adena` para a Adena.

    PELO MESMO CRITERIO DO FORMATADOR, e por isso as duas frases nunca podem
    discordar sobre o que a linha esta contando: chamar dez milhoes de adena de
    "unidades" e a mesma familia de mentira plausivel que o `0,00`, porque o
    numero continua certo e so a palavra fica errada.

    O SINGULAR DE HOJE E PRESERVADO. `_linha_do_menor` montava esta frase
    inline; ela saiu para ca para virar uma verdade so, e `1 unidade` continua
    saindo no singular.
    """
    if chave_da_serie == CHAVE_DA_SERIE_DA_ADENA:
        return f"{quantidade:,}".replace(",", ".") + " de adena"
    return f"{quantidade} {'unidade' if quantidade == 1 else 'unidades'}"


def destaque_ao_vivo(
    nome: str, chave_da_serie: str, destaque, agora: datetime
) -> str:
    """O bloco que aparece NA HORA quando uma leitura entra abaixo da mediana.

    ANAL-02, e ele so existe acima do piso da mediana - quem decide isso e
    `ModeloDeMercado.veredito_do_destaque`, que devolve `sem destaque` quando
    nao ha mediana que sustente um veredito. Esta funcao so desenha o que ja foi
    julgado.

    A MEDIANA DE REFERENCIA E O `n` VEM JUNTO, e nao como enfeite: "esta barata"
    sem dizer barata EM RELACAO A QUE e uma opiniao com cara de medicao, e o
    usuario nao teria como discordar. Com os dois numeros na tela ele discorda
    em um segundo.

    `console.moldurar` E NAO UMA REGUA DE CARACTERES MONTADA A MAO: a geometria
    da moldura ja e uma so no projeto, e um bloco desalinhado ao lado dos
    outros pareceria outro programa.

    `agora` ENTRA POR PARAMETRO e vem do `Relogio`, nunca de `datetime.now()`:
    num dual boot a hora crua do Windows esta errada, e o `Relogio` existe
    exatamente para corrigir isso.

    `chave_da_serie` VEM JUNTO DO NOME, e nao e derivada dele: quem chama e
    `TravaDoDestaque.anunciar`, que tem `linha.chave_da_serie` na mao. Ela
    escolhe o formatador, e este bloco e justamente o texto que o usuario mais
    copia para o WhatsApp — uma taxa de Adena impressa como `0,00 por unidade`
    aqui seria a copia mais convincente do erro.
    """
    formatar = formatador_do_unitario(chave_da_serie)
    linha = (
        f"{nome} ABAIXO DA MEDIANA: "
        f"{formatar(destaque.unitario_da_linha)}, "
        f"contra mediana de "
        f"{formatar(destaque.mediana_de_referencia)} "
        f"com n={destaque.evidencia.n}"
    )
    return "\n" + console.moldurar(linha, agora.strftime("%H:%M"))


class TravaDoDestaque:
    """Quem ja foi anunciado nesta sessao. O destaque e NOTICIA, e sai UMA vez.

    O DEFEITO QUE ELA CONSERTA FOI VISTO EM PRODUCAO (sessao de 2026-09-01
    05:37): a pagina do mercado e reaceita a cada tick, entao `destaque_ao_vivo`
    era chamada por LINHA a 1 Hz e o MESMO destaque, da MESMA oferta, saia a
    cada segundo enquanto ela estivesse na tela — cada um dentro de uma moldura.
    Com tres destaques por tick sao ~10.800 linhas por hora, e o `scanner.log`
    perde exatamente a forense que ele existe para guardar.

    O PRECEDENTE NAO E NOVO, E ELA E A QUINTA: `transicao_do_painel` trava a
    transicao do painel no proprio laco, e `mercado_pagina` trava outras tres
    (`_layout_ja_recusado`, `_congelamento_ja_avisado`, `_falta_ja_avisada`). O
    destaque era o unico anuncio repetitivo do modo SEM trava. A diferenca de
    forma — um CONJUNTO aqui, um booleano la — e so porque aqueles sao um
    estado do modo (ligado/desligado) e este e um estado POR OFERTA.

    A TRAVA E POR OFERTA, E TRAVAR POR SERIE SERIA O ERRO OPOSTO. Uma segunda
    oferta do mesmo item, mais barata que a primeira, e a noticia MAIS
    importante que o modo tem para dar; uma trava por `chave_da_serie` a
    engoliria justamente por o item ja ter aparecido uma vez.

    A IDENTIDADE E `chave_da_observacao`, E NAO UMA PARECIDA ESCRITA AQUI:
    serie + total + quantidade e a MESMA chave com que o registro dedupa o
    CSV (D-05). Reusar a funcao — em vez de repetir a tupla — e o que garante
    que, se um dia a identidade de uma oferta mudar, o console e o arquivo nao
    passem a discordar em silencio sobre o que ja foi visto.

    ELA E DA SESSAO, e nao uma janela de tempo: enquanto a oferta estiver no
    quadro ela sera relida a cada tick, e uma trava que expirasse so trocaria
    milhares de linhas repetidas por dezenas de linhas repetidas.

    O CONJUNTO NAO E PODADO, e isso e decisao. Ele guarda uma tupla curta por
    oferta DISTINTA ja anunciada abaixo da mediana — pelo censo, dezenas numa
    sessao longa, e nao milhares — entao o custo e desprezivel perto do risco
    de uma poda reanunciar o que ja saiu.
    """

    def __init__(self) -> None:
        # PUBLICO, no padrao dos contadores de `LeitorDePagina`: e o que deixa
        # o teste afirmar a identidade escolhida sem espiar o objeto por dentro.
        self.ja_anunciadas: set[tuple[str, int, int]] = set()

    def anunciar(self, linha, destaque, agora: datetime) -> str | None:
        """O bloco do destaque na PRIMEIRA vez desta oferta; `None` depois.

        DEVOLVER O TEXTO, e nao so um booleano, e o que impede a trava de virar
        um portao que alguem esquece de fechar: quem chama nao TEM como
        anunciar sem passar por aqui, porque e daqui que sai o texto.

        `None` E NAO STRING VAZIA: uma string vazia atravessaria um `if texto:`
        distraido e imprimiria uma moldura em branco por tick.

        QUEM DECIDE `abaixo` E O MODELO, E NAO ESTA CLASSE. Ela so registra o
        que foi anunciado; o veredito continua sendo de
        `ModeloDeMercado.veredito_do_destaque`, e o laco so chega aqui quando
        ele deu `abaixo`.
        """
        chave = chave_da_observacao(linha)
        if chave in self.ja_anunciadas:
            return None
        self.ja_anunciadas.add(chave)
        return destaque_ao_vivo(
            linha.nome_exibido, linha.chave_da_serie, destaque, agora
        )


def transicao_do_painel(aberto: bool) -> str:
    """A UNICA linha que uma mudanca de estado do painel produz.

    Painel fechado e o estado NORMAL e majoritario de um farm real: uma linha
    por tick seriam 3.600 por hora, e o log rotativo perderia a forense que ele
    existe para guardar. O laco usa LATCH nas duas transicoes, no precedente ja
    usado tres vezes em `mercado_pagina.py` (`_layout_ja_recusado`,
    `_congelamento_ja_avisado`, `_falta_ja_avisada`).
    """
    if aberto:
        return "o painel do mercado ABRIU - lendo a grade a cada tick"
    return (
        "o painel do mercado esta FECHADO - nada a ler, e isto e normal. "
        "Abra o World Exchange na aba de negociacao para o modo coletar."
    )


# ---------------------------------------------------------------------------
# "VALE QUANTO AGORA?" - a resposta que o usuario abre o programa para ver
# ---------------------------------------------------------------------------

# A marca da watchlist, escrita UMA vez. Ela e o que distingue "eu pedi para
# olhar isto" de "isto apareceu muito", e as duas coisas sao razoes DIFERENTES
# de uma serie estar no topo.
MARCA_DA_WATCHLIST = "[watchlist]"

# O aviso que sai UMA vez no cabecalho quando o `Relogio` nao tem ancora.
#
# SEM ELE, "ha 12 min" PODE ESTAR TRES HORAS ERRADO. Num dual boot o relogio do
# Windows volta com o fuso do outro sistema, e o `Relogio` existe exatamente
# para corrigir isso - mas quando ele nao consegue ancorar, ele degrada para a
# hora crua e AVISA. Um carimbo exibido sem repetir esse aviso aqui seria um
# numero preciso e errado, que e o modo de falha desta fase inteira.
AVISO_DO_RELOGIO_SEM_ANCORA = (
    "ATENCAO: o relogio nao tem ancora - as horas abaixo vem do Windows e "
    "podem estar erradas."
)

# De quantos em quantos segundos a secao repinta.
#
# ELA NAO SAI POR TICK, E ISSO E DECISAO. A `linha_ao_vivo` e a que responde "o
# modo esta vivo?" e por isso repinta a 1 Hz com o painel aberto; esta
# responde "vale quanto?", e a
# resposta so muda quando uma serie ganha observacao nova - o que, pelo censo,
# acontece a cada dezenas de segundos no melhor caso. Repintar um bloco de
# dezenas de linhas por segundo afogaria a linha ao vivo que o LEIT-04 exige.
#
# SESSENTA E ESCOLHA, E NAO MEDICAO, pela mesma disciplina dos pisos de
# `mercado_analise`.
SEGUNDOS_ENTRE_SECOES = 60.0


def _recencia_em_duas_formas(quando: datetime, agora: datetime) -> str:
    """`ha 8 h (31/08 10:00)` - as DUAS formas, sempre juntas.

    A RELATIVA E O QUE O OLHO LE ("ha 8 h" responde na hora se o numero ainda
    vale). A ABSOLUTA E O QUE SOBREVIVE A COPIAR A LINHA para o WhatsApp: um
    "ha 8 h" colado num grupo as 23h nao diz mais nada no dia seguinte.

    Carimbo no FUTURO sai como "agora mesmo" em vez de um relativo negativo: o
    CSV e editado a mao e uma data adiante e entrada possivel, e "ha -3 h" seria
    um numero que nao quer dizer nada.
    """
    segundos = (agora - quando).total_seconds()
    absoluta = quando.strftime("%d/%m %H:%M")
    if segundos < 60:
        return f"agora mesmo ({absoluta})"
    if segundos < 3600:
        return f"ha {int(segundos // 60)} min ({absoluta})"
    if segundos < 86400:
        return f"ha {int(segundos // 3600)} h ({absoluta})"
    return f"ha {int(segundos // 86400)} dias ({absoluta})"


def _linha_do_menor(observacoes, agora: datetime, chave_da_serie: str) -> str:
    """O menor pedido visivel: total E quantidade juntos, `n` e carimbo DELE.

    O ROTULO E `menor pedido visivel`, E ESSA E A PALAVRA DO REQUISITO. A razao
    e honestidade: o scanner ve OFERTAS no quadro, nao transacoes concluidas.
    Ninguem comprou por este valor - alguem PEDIU este valor. Ha teste prendendo
    as expressoes proibidas, sobre o texto devolvido E sobre o fonte deste
    modulo; o teste e a rede, e esta linha e a razao de a rede existir.

    O TOTAL NUNCA SAI SEM A QUANTIDADE AO LADO. Um total solto e sem
    significado, porque um lote de 100 custa mais que um de 1 sem que nenhum dos
    dois seja mais caro - e foi assim que a leitura de `4,50` para um item de
    `1.480,00` virou um pitfall nomeado na pesquisa.

    O CARIMBO E O DAQUELA OFERTA, e nunca `recencia_do_preco` (que e o
    `max(primeira_vez)` da SERIE). Exibir um minimo de manha ao lado da recencia
    de agora e a mentira plausivel que este projeto inteiro combate.

    `chave_da_serie` ENTRA POR PARAMETRO e escolhe as DUAS frases da linha — o
    formatador do unitario e a descricao da quantidade. Ela vem de `serie.chave`
    no laco de `secao_do_vale_quanto`, que ja a tem: derivar a aba do nome
    exibido seria confiar num rotulo que o OCR faz oscilar.
    """
    menor = menor_pedido_visivel(observacoes)
    if menor.total_em_centesimos is None:
        return (
            f"    menor pedido visivel: sem evidencia - "
            f"{menor.evidencia.n} de {menor.evidencia.piso} ofertas distintas"
        )
    return (
        f"    menor pedido visivel: "
        f"{formatar_centesimos(menor.total_em_centesimos)} por "
        f"{descrever_a_quantidade(chave_da_serie, menor.quantidade)} = "
        f"{formatador_do_unitario(chave_da_serie)(menor.unitario)} | "
        f"n={menor.evidencia.n} | "
        f"{_recencia_em_duas_formas(menor.primeira_vez, agora)}"
    )


def _linha_da_mediana(observacoes, agora: datetime, chave_da_serie: str) -> str:
    """A mediana com `n` e a recencia da SERIE, ou o que FALTA para existir.

    ABAIXO DO PISO O TEXTO DIZ O QUE FALTA, e nao um numero. Uma mediana de duas
    observacoes e um numero que engana - a contagem atual e a necessaria valem
    mais para o usuario que um valor que ele nao pode usar.

    AQUI a recencia e a do PRECO (`max(primeira_vez)` do `observacoes.csv`): "a
    oferta mais nova que eu vi desta serie". Ela NAO e o `ultima_vez` do
    catalogo, que diz quando o ITEM foi visto em qualquer valor e pode ser de
    agora mesmo sobre uma leitura de tres dias atras. Sao dois fatos diferentes
    com nomes parecidos, e este modulo so conhece o primeiro.

    `chave_da_serie` ENTRA PELA MESMA RAZAO DE `_linha_do_menor`, e ela e a
    razao de a escolha ser UMA funcao e nao um `if` por ponto de chamada: o
    menor pedido e a mediana da MESMA serie saindo em unidades diferentes seria
    pior que os dois errados, porque o usuario compararia um com o outro.
    """
    mediana = mediana_dos_unitarios(observacoes)
    if mediana.unitario is None:
        return (
            f"    mediana: sem evidencia - {mediana.evidencia.n} de "
            f"{mediana.evidencia.piso} ofertas distintas, faltam "
            f"{mediana.evidencia.faltam}"
        )
    quando = recencia_do_preco(observacoes)
    carimbo = (
        f" | oferta mais nova {_recencia_em_duas_formas(quando, agora)}"
        if quando is not None
        else ""
    )
    return (
        f"    mediana: "
        f"{formatador_do_unitario(chave_da_serie)(mediana.unitario)} | "
        f"n={mediana.evidencia.n}{carimbo}"
    )


def secao_do_vale_quanto(
    modelo,
    watchlist,
    agora: datetime,
    *,
    relogio_confiavel: bool = True,
) -> str:
    """A resposta a "vale quanto agora?", em texto puro. DEVOLVE, nao imprime.

    TRES LINHAS POR SERIE - menor pedido visivel, mediana e tendencia - e cada
    numero viaja com a evidencia COLADA: a contagem de ofertas distintas e o
    carimbo. Estatistica sem `n` e sem data e adivinhacao com cara de numero, e
    a unica defesa contra isso e o `n` nao ser opcional em lugar nenhum.

    O QUE ELA NAO MOSTRA, E POR QUE: o `residuo_do_cruzamento`. A guarda de
    cruzamento esta DESLIGADA por medicao (02-02), entao o residuo e observacao
    e nao veredito. Ele ja esta em coluna propria no CSV, para o usuario olhar
    no Sheets com calma; imprimir aqui um numero que o proprio projeto declarou
    nao-decidivel seria convidar a interpretacao errada.

    A ORDEM VEM DE `ordenar_para_o_console`, que promove a watchlist sem
    esconder o resto - a divergencia deliberada com a letra do criterio 3 do
    ROADMAP esta escrita LA, junto da decisao.

    `agora` E `relogio_confiavel` ENTRAM POR PARAMETRO, os dois: este modulo
    nao chama o relogio do sistema, pela mesma disciplina que `mercado_analise`
    ja segue. Quem os tem e o laco, que segura o `Relogio`.
    """
    linhas = [
        console.moldurar("VALE QUANTO AGORA?", agora.strftime("%H:%M")),
        "",
    ]
    if not relogio_confiavel:
        linhas += [f"  {AVISO_DO_RELOGIO_SEM_ANCORA}", ""]

    series = ordenar_para_o_console(modelo, watchlist)
    if not series:
        # AS DUAS ABAS, e nao so uma: depois da Fase 5 o modo le a grade de
        # negociacao E a aba Adena, e uma instrucao que cita so a primeira
        # esconderia metade do que o scanner faz de quem esta olhando um
        # console vazio e tentando descobrir o que abrir.
        linhas.append(
            "  Nenhuma observacao ainda. Abra o World Exchange na aba de "
            "negociacao (ou na aba Adena, para a taxa de cambio) e deixe o "
            "painel aberto."
        )
        return "\n".join(linhas)

    for serie in series:
        marca = f" {MARCA_DA_WATCHLIST}" if serie.na_watchlist else ""
        observacoes = modelo.observacoes_de(serie.chave)
        linhas += [
            f"  {serie.nome_exibido}{marca}",
            # `serie.chave` E O UNICO CRITERIO de unidade, e as duas linhas do
            # bloco recebem a MESMA: e o que impede o menor pedido e a mediana
            # da mesma serie de sairem em unidades diferentes.
            _linha_do_menor(observacoes, agora, serie.chave),
            _linha_da_mediana(observacoes, agora, serie.chave),
            # A TENDENCIA SAI COM O TAMANHO DA JANELA SEMPRE JUNTO, e a unidade
            # e "ofertas distintas". As duas coisas moram em
            # `descrever_a_tendencia`, que ja e a unica frase de tendencia do
            # projeto: montar a frase aqui seria a segunda, e uma delas
            # esqueceria o `n` um dia.
            f"    {descrever_a_tendencia(tendencia(observacoes))}",
            "",
        ]
    return "\n".join(linhas)


def resumo_da_sessao(leitor, contagem, motivos, orcamento) -> str:
    """O fim da sessao, contando AS DUAS METADES e o que cada uma custou.

    TRES BLOCOS, e a separacao e o conteudo:

    1. Os SETE contadores do leitor - o que a TELA entregou.
    2. As tres contagens de escrita - o que foi para o DISCO. `observacoes`,
       `duplicadas` e `perdidas` sao fatos DIFERENTES e nao se somam: `registrar`
       devolve `False` para chave ja conhecida E para registro desligado, e somar
       os dois faria o resumo dizer "descartei 300 duplicadas" sobre uma sessao
       em que o disco encheu na terceira linha.
    3. Os motivos de descarte agregados por SESSAO, com a contagem de cada um -
       e o que diz ao usuario se vale mover a tooltip ou recalibrar. Os nomes sao
       as CONSTANTES de `mercado_leitura.py` (`oclusao`, `numero`, `cruzamento`,
       `faixa-cinzenta`, `discordancia-entre-escalas`), nunca as palavras do
       CONTEXT, que divergem delas.
    4. O orcamento de tick auto-medido.
    """
    linhas = [
        console.moldurar(
            "RESUMO DA SESSAO DE MERCADO", datetime.now().strftime("%H:%M")
        ),
        "",
        "O QUE A TELA ENTREGOU:",
    ]
    for atributo, rotulo in ROTULOS_DOS_CONTADORES:
        linhas.append(f"  {rotulo:<32} {getattr(leitor, atributo)}")

    linhas += [
        "",
        "O QUE FOI PARA O DISCO (tres fatos diferentes, que nao se somam):",
        f"  observacoes GRAVADAS             {contagem.observacoes}",
        f"  duplicadas descartadas           {contagem.duplicadas}",
        f"  PERDIDAS (registro desligado)    {contagem.perdidas}",
        f"  series distintas nesta sessao    {len(contagem.series)}",
    ]

    linhas += ["", "POR QUE AS LINHAS FORAM DESCARTADAS (somado na sessao):"]
    if motivos:
        for motivo, quantas in sorted(
            motivos.items(), key=lambda par: (-par[1], par[0])
        ):
            linhas.append(f"  {motivo:<32} {quantas}")
    else:
        linhas.append("  nenhuma linha foi descartada nesta sessao")

    linhas += [
        "",
        "O QUE ESTE PROCESSO CUSTOU POR TICK:",
        f"  p50                              {orcamento.p50 * 1000:.0f} ms",
        f"  p95                              {orcamento.p95 * 1000:.0f} ms",
        f"  maximo                           {orcamento.maximo * 1000:.0f} ms",
        f"  ticks que estouraram o orcamento {orcamento.estouros} "
        f"de {orcamento.total} (orcamento: {orcamento.limite:.1f}s)",
        "",
        "  Estes numeros dizem o que ESTE processo custou, e so isso. "
        "Contencao entre",
        "  os tres processos (duas partys mais o mercado) e propriedade do "
        "SISTEMA -",
        "  CPU, GPU, sessoes de captura, agendador do Windows - e nenhum "
        "numero daqui",
        "  a alcanca. Quem fecha isso e conferir os tres no Gerenciador de "
        "Tarefas.",
    ]
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# A MARGEM DE CRAFT DESENHADA (ANAL-04)
# ---------------------------------------------------------------------------

# O marcador do componente mais velho. Escrito UMA vez, e em ASCII: o console
# do Windows engasga em acento e em seta unicode, e um marcador que sai como
# `?` nao marca nada.
MARCA_DO_COMPONENTE_VELHO = "<--"

# Em quantas colunas a advertencia do cabecalho quebra. Setenta e seis e a
# largura em que ela cabe num console padrao de 80 sem quebrar sozinha num
# lugar imprevisivel — e uma quebra imprevisivel e o que faz um paragrafo
# parecer defeito de formatacao em vez de aviso.
LARGURA_DO_AVISO = 76

# A advertencia que sai UMA VEZ no cabecalho da secao, e nao por receita.
#
# ELA E A LIMITACAO NUMERO 1 DA `margem_de_craft`, TRAZIDA PARA ONDE O USUARIO
# LE. O programa nao sabe se a oferta ainda existe: a dedup da Fase 3 e por
# CONTEUDO e sem tempo de saida, entao o CSV nunca registra o desaparecimento
# de um anuncio. Um menor pedido visivel de vinte minutos atras pode ter sido
# comprado ha dezenove, e o registro nao teria como saber.
#
# UMA VEZ, E NAO UMA POR RECEITA: repetida em cada bloco ela vira ruido que o
# olho aprende a pular, e ai ela deixa de advertir. E o mesmo argumento que faz
# `transicao_do_painel` sair por LATCH em vez de por tick.
AVISO_DE_OFERTA_TALVEZ_COMPRADA = (
    "ATENCAO: o programa nao sabe se estas ofertas ainda existem - o registro "
    "nao anota desaparecimento. Um pedido de 20 min atras pode ter sido "
    "comprado ha 19. Confira na tela antes de agir."
)


def _idade_em_uma_palavra(idade: timedelta | None) -> str:
    """`ha 8 min`, `ha 3 h`, `ha 3 dias`. UMA unidade, e so ela.

    E A DECISAO DE LAYOUT QUE MANTEM A TABELA LEGIVEL com cinco ingredientes.
    A `_recencia_em_duas_formas` existe e esta certa onde ela e usada: la a
    forma absoluta e o que sobrevive a copiar a linha para o WhatsApp. Aqui
    sao ate seis linhas empilhadas e alinhadas por coluna, e um `(31/08
    10:00)` por linha empurraria a coluna da idade para fora da tela.

    IDADE NEGATIVA SAI COMO `agora mesmo`, e nao como `ha -3 h`: o CSV e
    editado a mao no Sheets e uma data adiante e entrada possivel.
    """
    if idade is None:
        return "sem carimbo"
    segundos = idade.total_seconds()
    if segundos < 60:
        return "agora mesmo"
    if segundos < 3600:
        return f"ha {int(segundos // 60)} min"
    if segundos < 86400:
        return f"ha {int(segundos // 3600)} h"
    dias = int(segundos // 86400)
    return f"ha {dias} dia" if dias == 1 else f"ha {dias} dias"


def _formatar_margem(valor: Fraction) -> str:
    """A margem com o SINAL sempre explicito e a marca de derivada.

    O SINAL SAI SEPARADO DO NUMERO de proposito. `formatar_centesimos` faz
    `divmod`, e `divmod(-450, 100)` e `(-5, 50)` — o que sairia como `-5,50`
    para quatro reais e cinquenta negativos. Formatar o modulo e prefixar o
    sinal e a unica forma que nao inventa um centavo.

    O `+` EXPLICITO NO POSITIVO porque a coluna vai ser lida de relance: sem
    ele, `1.163,50` e `-1.163,50` diferem por um caractere facil de perder, e
    os dois querem dizer coisas opostas.

    `(derivado)` PELA MESMA RAZAO DE `formatar_unitario_derivado`: este numero
    nao esta no CSV. Ele nasce de unitarios, que ja sao derivacao, e sem a
    marca alguem copia a linha e ele vira "o que o scanner leu".
    """
    centesimos = round(valor)
    sinal = "-" if centesimos < 0 else "+"
    return f"{sinal}{formatar_centesimos(abs(centesimos))} (derivado)"


# Onde a coluna do NOME comeca, contada da margem esquerda. Uma constante e
# nao um numero solto em duas f-strings: o produto e os componentes tem recuos
# DIFERENTES (a hierarquia se le pelo recuo), e sem um ponto de partida comum
# as colunas de `menor`, `n` e idade sairiam escalonadas — que e exatamente o
# que uma tabela existe para nao fazer.
COLUNA_DO_NOME = 16


def _linha_de_item(rotulo: str, linha, recuo: str) -> str:
    """Um lado da conta: total E quantidade juntos, o `n` e a idade.

    A MESMA DISCIPLINA DA SECAO "VALE QUANTO AGORA": um total solto e sem
    significado, porque um lote de 100 custa mais que um de 1 sem que nenhum
    dos dois seja mais caro; e um numero sem `n` e adivinhacao com cara de
    numero. Os tres andam juntos ou nao andam.

    A IDADE E A ULTIMA COLUNA, e o marcador vem depois dela — assim a marca
    fica na borda direita, onde o olho a encontra varrendo a coluna em vez de
    lendo cada linha inteira.
    """
    menor = linha.menor
    unidades = "unidade" if menor.quantidade == 1 else "unidades"
    marca = f"  {MARCA_DO_COMPONENTE_VELHO}" if linha.velho else ""
    # O rotulo ocupa o que sobra ate `COLUNA_DO_NOME`, e por isso o campo
    # encolhe quando o recuo cresce. E o que faz a coluna do nome — e todas as
    # depois dela — cair no MESMO lugar no produto e nos componentes.
    largura = max(1, COLUNA_DO_NOME - len(recuo))
    return (
        f"{recuo}{rotulo:<{largura}}{linha.nome_exibido:<22}"
        f"menor {formatar_centesimos(menor.total_em_centesimos)} por "
        f"{menor.quantidade} {unidades} "
        f"| n={menor.evidencia.n} "
        f"| {_idade_em_uma_palavra(linha.idade)}{marca}"
    )


def _bloco_da_margem(receita, modelo, agora: datetime) -> list[str]:
    """Um bloco por receita: o cabecalho dela, as linhas e a margem OU o motivo."""
    resultado = margem_de_craft(receita, modelo, agora)
    titulo = f"  {receita.produto} (rende {receita.rende})"

    # QUANDO ELA QUEBRA, O MOTIVO OCUPA O LUGAR DO NUMERO — e nao aparece ao
    # lado dele. Imprimir "a margem e X, mas faltou o Leonard" deixaria o X na
    # tela, e o X e exatamente o numero plausivel e errado que a quebra existe
    # para impedir.
    if not resultado.ok:
        return [titulo, f"    sem margem: {resultado.motivo}", ""]

    linhas = [titulo]
    for linha in resultado.linhas:
        if linha.papel == PAPEL_PRODUTO:
            linhas.append(_linha_de_item("produto", linha, "    "))
        else:
            linhas.append(
                _linha_de_item(
                    f"- {linha.quantidade_da_receita}x", linha, "      "
                )
            )

    # A MAIS VELHA SOBE PARA A LINHA DA MARGEM, COM O NOME DO COMPONENTE. E o
    # numero que decide se a margem vale alguma coisa: enterra-lo no meio da
    # lista seria esconde-lo atras de quatro linhas que o olho pula.
    if resultado.idade_mais_velha is not None:
        selo = (
            f" | evidencia mais velha: "
            f"{_idade_em_uma_palavra(resultado.idade_mais_velha)} "
            f"({resultado.nome_do_mais_velho})"
        )
    else:
        selo = ""
    linhas.append(
        f"    {'margem':<12}"
        f"{_formatar_margem(resultado.margem_em_centesimos)}{selo}"
    )

    # A MEDIANA E LINHA SECUNDARIA, e nao a conta principal: ela exige o piso
    # de cinco POR componente, o que multiplicaria a chance de a resposta
    # inteira cair. Quando ela nao alcanca o piso, a linha simplesmente nao
    # sai — dizer "sem mediana" em toda margem seria ruido constante sobre uma
    # linha que ja e opcional.
    if resultado.margem_pela_mediana is not None:
        linhas.append(
            f"    {'pela mediana':<12}"
            f"{_formatar_margem(resultado.margem_pela_mediana)}"
        )
    linhas.append("")
    return linhas


def secao_da_margem(receitas, modelo, agora: datetime) -> str:
    """A margem de craft do ANAL-04, em texto puro. DEVOLVE, nao imprime.

    SEM RECEITA, TEXTO VAZIO — e nao um aviso, e nao um erro. A secao e
    OPCIONAL: o `[[receita]]` nasce comentado no `config.toml` e o usuario o
    preenche quando quiser. Um "voce nao configurou receitas" a cada repintar
    seria o programa cobrando do usuario uma coisa que ele nao pediu, e o
    console tem uma resposta a dar sem ela. Decisao travada no `04-CONTEXT.md`.

    A ADVERTENCIA DO CABECALHO SAI UMA VEZ — ver
    `AVISO_DE_OFERTA_TALVEZ_COMPRADA`.

    A STALENESS E POR COMPONENTE, com a mais velha promovida a linha da
    margem. O requisito exige essa granularidade porque uma margem com um
    ingrediente visto hoje e outro visto ha uma semana nao e uma margem, e um
    unico carimbo no rodape nao deixaria o usuario ver QUAL metade envelheceu.

    `agora` ENTRA POR PARAMETRO, no molde do resto do modulo: quem tem o
    `Relogio` e o laco.
    """
    if not receitas:
        return ""

    linhas = [
        console.moldurar("MARGEM DE CRAFT", agora.strftime("%H:%M")),
        "",
        # QUEBRADA, e nao numa linha so de 180 caracteres. Uma advertencia que
        # rola para fora da janela do console e uma advertencia que ninguem le,
        # e esta e a unica defesa contra o numero abaixo dela parecer acionavel.
        *textwrap.wrap(
            AVISO_DE_OFERTA_TALVEZ_COMPRADA,
            width=LARGURA_DO_AVISO,
            initial_indent="  ",
            subsequent_indent="  ",
        ),
        "",
    ]
    for receita in receitas:
        linhas += _bloco_da_margem(receita, modelo, agora)
    return "\n".join(linhas)
