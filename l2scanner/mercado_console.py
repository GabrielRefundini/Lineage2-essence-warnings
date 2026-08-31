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

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from fractions import Fraction

from . import console
from .mercado_analise import (
    descrever_a_tendencia,
    mediana_dos_unitarios,
    menor_pedido_visivel,
    ordenar_para_o_console,
    recencia_do_preco,
    tendencia,
)

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


def linha_ao_vivo(leitor, contagem, ultimo_item) -> str:
    """A repintada de 1 Hz: as DUAS metades e o ultimo item reconhecido.

    Ela devolve UMA linha, na cadencia da captura - a mesma do resto do scanner.

    O QUE ELA NAO MOSTRA, E POR QUE: o `residuo_do_cruzamento`. A guarda de
    cruzamento esta DESLIGADA por medicao (02-02), entao o residuo e observacao
    e nao veredito; ele ja esta em coluna propria no CSV, para o usuario olhar no
    Sheets com calma. Num repintar de um segundo ele so competiria por atencao
    com os dois numeros que julgam a sessao.

    `ultimo_item` pode ser `None` no comeco, e ai a linha diz isso por extenso em
    vez de mostrar campo vazio: campo vazio parece defeito.
    """
    return (
        f"mercado | lidas {leitor.paginas_lidas} | "
        f"perdidas {leitor.paginas_perdidas} | "
        f"gravadas {contagem.observacoes} | "
        f"ultimo item: {ultimo_item if ultimo_item else '(nenhum ainda)'}"
    )


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


def destaque_ao_vivo(nome: str, destaque, agora: datetime) -> str:
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
    """
    linha = (
        f"{nome} ABAIXO DA MEDIANA: "
        f"{formatar_unitario_derivado(destaque.unitario_da_linha)}, "
        f"contra mediana de "
        f"{formatar_unitario_derivado(destaque.mediana_de_referencia)} "
        f"com n={destaque.evidencia.n}"
    )
    return "\n" + console.moldurar(linha, agora.strftime("%H:%M"))


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
# modo esta vivo?" e por isso repinta a 1 Hz; esta responde "vale quanto?", e a
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


def _linha_do_menor(observacoes, agora: datetime) -> str:
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
    """
    menor = menor_pedido_visivel(observacoes)
    if menor.total_em_centesimos is None:
        return (
            f"    menor pedido visivel: sem evidencia - "
            f"{menor.evidencia.n} de {menor.evidencia.piso} ofertas distintas"
        )
    unidades = "unidade" if menor.quantidade == 1 else "unidades"
    return (
        f"    menor pedido visivel: "
        f"{formatar_centesimos(menor.total_em_centesimos)} por "
        f"{menor.quantidade} {unidades} = "
        f"{formatar_unitario_derivado(menor.unitario)} | "
        f"n={menor.evidencia.n} | "
        f"{_recencia_em_duas_formas(menor.primeira_vez, agora)}"
    )


def _linha_da_mediana(observacoes, agora: datetime) -> str:
    """A mediana com `n` e a recencia da SERIE, ou o que FALTA para existir.

    ABAIXO DO PISO O TEXTO DIZ O QUE FALTA, e nao um numero. Uma mediana de duas
    observacoes e um numero que engana - a contagem atual e a necessaria valem
    mais para o usuario que um valor que ele nao pode usar.

    AQUI a recencia e a do PRECO (`max(primeira_vez)` do `observacoes.csv`): "a
    oferta mais nova que eu vi desta serie". Ela NAO e o `ultima_vez` do
    catalogo, que diz quando o ITEM foi visto em qualquer valor e pode ser de
    agora mesmo sobre uma leitura de tres dias atras. Sao dois fatos diferentes
    com nomes parecidos, e este modulo so conhece o primeiro.
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
        f"    mediana: {formatar_unitario_derivado(mediana.unitario)} | "
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
        linhas.append(
            "  Nenhuma observacao ainda. Abra o World Exchange na aba de "
            "negociacao e deixe o painel aberto."
        )
        return "\n".join(linhas)

    for serie in series:
        marca = f" {MARCA_DA_WATCHLIST}" if serie.na_watchlist else ""
        observacoes = modelo.observacoes_de(serie.chave)
        linhas += [
            f"  {serie.nome_exibido}{marca}",
            _linha_do_menor(observacoes, agora),
            _linha_da_mediana(observacoes, agora),
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
