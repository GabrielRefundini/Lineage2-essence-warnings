"""O dado do dashboard: le o CSV ao vivo e monta o JSON. UMA fonte, UMA conta.

O QUE ESTE MODULO NAO FAZ, E E ISSO QUE O DEFINE
=================================================
Ele nao tem parser proprio e nao tem formatador proprio. O parser continua sendo
`mercado_registro.observacoes_do_arquivo`; a aritmetica continua sendo
`mercado_analise`; as frases continuam saindo de `mercado_console`. O DASH-03 e
literalmente isto: "mesma fonte, mesma conta, sem um segundo parser".

O que ele acrescenta e SO a leitura AO VIVO — o mercado le o arquivo uma vez, no
arranque; o dashboard le a cada pedido, com o escritor ainda rodando — e a
montagem do dicionario que vira JSON.

ELE E PURO QUANTO DA: sem servidor, sem relogio proprio (o `agora` entra por
parametro), sem escrita. A unica coisa que ele toca no disco e uma leitura em
modo `"r"`, e ha teste de impressao digital prendendo isso.

O INVARIANTE DE LEITURA, ESCRITO POR EXTENSO (DASH-01 / T-01-04)
=================================================================
**Nenhuma funcao deste modulo abre arquivo fora do modo de leitura, e nenhuma
cria pasta.** `RegistroDeObservacoes.carregar` cria o `observacoes.csv` ausente
com cabecalho porque ela e o arranque do ESCRITOR; aqui nao ha escritor nenhum.
Criar o arquivo ou a pasta seria o programa ESCREVENDO num caminho de LEITURA —
o mesmo argumento com que `conferir_o_terminador` recusa truncar a cauda no
disco em vez de "consertar" o arquivo do usuario. Um arquivo que aparece sozinho
porque alguem abriu o dashboard e um efeito colateral que ninguem pediu,
inclusive num diretorio apontado por engano.

DUAS PROVAS PRENDEM ISSO, e nao uma: a impressao digital de tres componentes em
300 leituras (`tests/test_dashboard_leitura.py`) prova o que aconteceu; o
tripwire por leitura de fonte sobre `observacoes_ao_vivo` e sobre
`ArquivoRecortado.open` prova o que o codigo PODE fazer, e pega a regressao no
commit em que ela e escrita.
"""

from __future__ import annotations

import io
import logging
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from fractions import Fraction
from pathlib import Path
from typing import Any

from . import mercado_registro
from .mercado_analise import (
    Evidencia,
    ModeloDeMercado,
    mediana_dos_unitarios,
    menor_pedido_visivel,
    recencia_do_preco,
)
from .mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA

# O `_recencia_em_duas_formas` E PRIVADO, E MESMO ASSIM E ELE QUE VEM.
#
# Ele nasceu privado porque so o desenho do console o usava. Agora ha um segundo
# desenho, e a escolha e entre duas coisas ruins: importar um nome com
# underscore, ou escrever a mesma logica de novo aqui. A segunda e pior, e nao
# por pouco — "ha 8 h (31/08 10:00)" reescrito e exatamente o segundo formatador
# que o DASH-03 proibe, e as duas copias divergiriam no primeiro ajuste de
# limiar. O underscore vira, entao, o aviso correto: nao ha promessa de
# estabilidade nesta assinatura, e quem a mudar tem de olhar para os dois
# chamadores.
#
# Promove-lo a nome publico seria mexer em `mercado_console.py`, que a decisao
# do usuario em 2026-09-01 (CTX-2) nao autoriza esta fase a tocar.
from .mercado_console import _recencia_em_duas_formas, formatador_do_unitario

log = logging.getLogger(__name__)

__all__ = [
    "ArquivoRecortado",
    "LARGURAS_DE_BALDE",
    "LeituraAoVivo",
    "NOTA_DE_LINHA_PARCIAL",
    "PontoDaSerie",
    "ancora_da_meia_noite",
    "baldes",
    "observacoes_ao_vivo",
    "payload",
    "pontos_por_instante",
]


# ===========================================================================
# AS FRASES DA TELA — TODAS CONSTANTES NOMEADAS, TODAS DO PYTHON
# ===========================================================================
#
# ELAS SAO COPIA LITERAL DO `## Copywriting Contract` DO `01-UI-SPEC.md`, e
# moram aqui em vez de literais espalhados pelo corpo das funcoes pela mesma
# razao que `UNIDADE_DA_JANELA` mora no topo de `mercado_analise`: uma frase
# escrita duas vezes e uma frase que diverge no primeiro ajuste, e a divergencia
# aparece na tela do usuario e nao no teste.
#
# ELAS LEVAM ACENTO, e as do `mercado_console` nao — isso e INTENCIONAL e esta
# escrito no UI-SPEC. O console e ASCII por escolha dele (o `cmd` do Windows abre
# em cp1252); esta pagina e HTML em UTF-8 e a moldura e nossa. O que NAO pode
# acontecer e o navegador reacentuar a string que veio pronta do console: isso
# seria o SEGUNDO formatador que o DASH-03 proibe.

# A nota da cauda ignorada. Ela viaja no payload quando `cauda_incompleta` for
# verdadeiro, e chega PRONTA ao JS.
#
# E ELA E REDE DE SEGURANCA, E NAO O CAMINHO NORMAL — a medicao esta na
# docstring de `observacoes_ao_vivo`: ZERO leituras parciais em 22.970 tentativas
# durante 200.000 appends concorrentes. Um aviso que aparecesse toda hora viraria
# ruido, e ruido e indistinguivel de defeito.
NOTA_DE_LINHA_PARCIAL = "Última linha ignorada: incompleta (o scanner estava escrevendo)."


@dataclass(frozen=True)
class ArquivoRecortado:
    """Um objeto com FORMA de `Path`, que entrega texto ja cortado.

    POR QUE ELE EXISTE
    ==================
    `observacoes_do_arquivo` recebe um `Path` e le o arquivo ela mesma
    (`mercado_registro.py:552-556`). O dashboard precisa do MESMO corpo — os
    mesmos dois portoes, as mesmas duas redes por linha — mas sobre um texto que
    ele ja cortou na ultima quebra de linha. Este adaptador e o encaixe: ele diz
    "sim, eu sou um arquivo", devolve o texto recortado no `open()`, e devolve o
    caminho REAL no `__str__`.

    AS QUATRO ROTAS, E POR QUE TRES FORAM RECUSADAS
    ===============================================
    A pesquisa desta fase listou tres saidas para reusar o corpo do parser sobre
    um texto ja cortado, e recomendou a (a). Nenhuma das tres serve:

    (a) EXTRAIR `observacoes_do_texto` DE `mercado_registro.py`, deixando
        `observacoes_do_arquivo` como uma casca que le e delega. E a mais limpa
        das quatro, e seria a escolha obvia — mas ela MEXE em
        `mercado_registro.py`, e a decisao do usuario em 2026-09-01 (CTX-2)
        nomeia `mercado_catalogo.py` como o UNICO arquivo do workstream
        `mercado` que esta fase pode tocar. Recusada por escopo, e nao por
        merito: quando o workstream `mercado` abrir de novo, esta rota deve
        substituir este adaptador.

    (b) ESCREVER O TEXTO CORTADO NUM ARQUIVO TEMPORARIO e passar o caminho dele.
        Recusada porque quebra a mensagem de erro: `conferir_o_cabecalho`
        imprime o caminho que recebeu, e o usuario leria "restaure a primeira
        linha de C:\\Users\\...\\AppData\\Local\\Temp\\tmp8f2a.csv" — um arquivo
        que nao existe mais quando ele for procurar. A instrucao da mensagem so
        vale se ela nomear o arquivo que da para abrir. Ha teste prendendo isso.

    (c) UM SEGUNDO LACO DE `csv.reader` AQUI. Recusada porque e, literalmente, o
        segundo parser que a docstring de `observacoes_do_arquivo` existe para
        nao ter: das cinco truncagens medidas byte a byte na Fase 3, DUAS
        produzem seis campos todos parseaveis, com `80` virando `8`. Duas
        implementacoes de leitura sao duas chances de uma delas nao ter o portao
        do terminador.

    (d) ESTE ADAPTADOR — a escolhida. Zero arquivo do mercado tocado, UM parser,
        os dois portoes continuam sendo chamados, e a mensagem continua nomeando
        `.mercado/observacoes.csv`.

    O PRECO, DITO EM VOZ ALTA: e um acoplamento de FORMA. Este objeto implementa
    `open`, `__str__` e `__fspath__` porque e o que `observacoes_do_arquivo` usa
    hoje; se ela passar a chamar `.stat()` ou `.exists()`, este adaptador quebra
    com `AttributeError`. O antidoto e o teste de equivalencia do tracer, que
    compara o resultado desta rota com a chamada direta do parser sobre o mesmo
    arquivo — se o corpo do parser mudar de forma, o teste cai antes do usuario.
    """

    caminho_real: Path
    texto: str

    def open(self, *args: Any, **kwargs: Any) -> io.StringIO:
        """O texto ja cortado, como se viesse do disco.

        Os argumentos sao ACEITOS E IGNORADOS de proposito: quem chama passa
        `("r", encoding="utf-8", newline="")`, e o texto ja esta decodificado e
        sem traducao de quebra de linha. Recusar os argumentos obrigaria o
        chamador a saber que nao e um `Path` de verdade, que e exatamente o que
        este objeto existe para esconder.
        """
        return io.StringIO(self.texto, newline="")

    def __str__(self) -> str:
        return str(self.caminho_real)

    def __fspath__(self) -> str:
        return str(self.caminho_real)


@dataclass(frozen=True)
class LeituraAoVivo:
    """O que uma leitura ao vivo devolve: o dado E o que houve com o arquivo.

    OS DOIS SINAIS VIAJAM COLADOS no dado, e nao ao lado dele, pela mesma razao
    que a `Evidencia` viaja dentro de cada resultado do `mercado_analise`: quem
    desenha nao pode ser obrigado a LEMBRAR de perguntar se a cauda estava
    cortada. `arquivo_ausente` e `cauda_incompleta` sao fatos sobre a procedencia
    do numero, e o rodape da tela existe para mostra-los.
    """

    observacoes: list = field(default_factory=list)
    cauda_incompleta: bool = False
    arquivo_ausente: bool = False

    # QUANTAS LINHAS DE DADO O TRECHO COMPLETO TINHA — sem o cabecalho, e
    # contando tambem as que o parser descartou.
    #
    # ELA E A PROVA DE QUE A LEITURA ACONTECEU, e e isso que a torna necessaria:
    # no estado vazio a tela precisa dizer "o arquivo foi lido: N linhas, 0 da
    # serie Adena". Sem esse numero, "0 da serie Adena" e indistinguivel de "o
    # dashboard nao conseguiu abrir o arquivo" — que e exatamente o erro que o
    # estado vazio desenhado existe para nao cometer.
    #
    # ELA CONTA REGISTROS, E NAO LINHAS DO ARQUIVO. A frase que ela alimenta poe
    # duas contagens lado a lado ("N linhas, M da serie"), e as duas tem de ser
    # da mesma especie: incluir o cabecalho de um lado e contar observacoes do
    # outro seria comparar coisas diferentes com a mesma palavra.
    #
    # E ELA CONTA A LINHA RUIM TAMBEM. A linha esta no arquivo; quem quiser saber
    # quantas sobreviveram ao parser tem `len(observacoes)` ao lado, e o log
    # NOMEIA cada uma que caiu.
    linhas_completas: int = 0


def observacoes_ao_vivo(arquivo: Path) -> LeituraAoVivo:
    """As observacoes do CSV ATE A ULTIMA LINHA COMPLETA, com o arquivo em uso.

    ESTA FUNCAO DECIDE O CONTRARIO DO QUE A FASE 3 DECIDIU, E A FASE 3 ESTAVA
    CERTA — PARA ELA
    ==================================================================
    `conferir_o_terminador` RECUSA O ARQUIVO INTEIRO quando ele nao termina em
    quebra de linha, e a docstring dela explica por que: la o leitor e o ARRANQUE
    DO ESCRITOR, que vai APENDAR em seguida. Uma cauda ambigua naquele contexto
    vira chave de dedup errada e depois preco errado gravado como bom, para
    sempre. Desligar alto e a resposta certa.

    Aqui o contexto e outro e o oposto e a resposta certa. Este processo NUNCA
    escreve neste arquivo, e o escritor legitimo esta rodando AGORA, no outro
    processo. Recusar o arquivo inteiro por causa de uma cauda de meio segundo
    apagaria o grafico da tela a cada vez que o `--mercado` estivesse no meio de
    um `write` — e o usuario veria o dashboard "quebrar" sozinho, sem causa
    visivel.

    O CORTE ACONTECE ANTES DO PORTAO, E POR ISSO O PORTAO CONTINUA EXISTINDO. O
    texto entregue ao parser termina em quebra de linha POR CONSTRUCAO, entao
    `conferir_o_terminador` e chamada e passa; `conferir_o_cabecalho` e chamada e
    continua desligando alto se o arquivo nao for mais o arquivo deste programa.
    Nenhum dos dois portoes foi afrouxado — o primeiro passou a julgar um texto
    de que a ambiguidade ja foi retirada.

    A FREQUENCIA DO CASO ESTA MEDIDA, E O ROADMAP A SUPERESTIMOU
    ============================================================
    A premissa era "leituras parciais vao acontecer o tempo todo". Ela e FALSA
    para o escritor que este projeto tem. `csv.writer.writerow` seguido de
    `flush` e UMA unica chamada de escrita, e o escritor abre, escreve, da flush
    e fecha por linha. Medido: em **22.970** leituras de cauda durante 200.000
    appends concorrentes, **ZERO** leituras sem terminador e zero erros de
    abertura. Com uma linha de 256 KB, tambem zero.

    E O ZERO E RESULTADO, E NAO CEGUEIRA DA SONDA: um controle positivo que
    escrevia a linha em DUAS chamadas com pausa no meio (`os.write` do texto,
    pausa, `os.write` do terminador) acusou **3.252 de 4.079**. A sonda enxerga
    o defeito quando ele existe; ela nao o viu porque ele nao acontece.

    O QUE ISSO MUDA: esta degradacao e REDE DE SEGURANCA, e nao o caminho
    normal. Ela existe para o arquivo editado a mao no Sheets e salvo sem quebra
    final, e para a queda de energia — nao para a corrida com o escritor, que
    medimos e nao existe. Escrever "o normal e a cauda estar cortada" no fonte
    seria carregar para as proximas fases uma premissa que a medicao ja derrubou.

    ELA NAO CAPTURA `ContratoDoArquivoQuebrado`. O portao do cabecalho continua
    desligando alto, e quem decide o que MOSTRAR nessa hora e a camada de
    payload — engolir a excecao aqui esconderia de todos os chamadores um
    arquivo que deixou de ser este arquivo.
    """
    try:
        with arquivo.open("r", encoding="utf-8", newline="") as fonte:
            bruto = fonte.read()
    except FileNotFoundError:
        # A `.mercado/` nasce vazia, e "ainda nao gravaram nada" e uma resposta
        # legitima — nao um erro. O molde e o de `observacoes_do_arquivo`, que
        # tambem devolve vazio em vez de levantar.
        return LeituraAoVivo(arquivo_ausente=True)

    if not bruto:
        # Zero bytes: nao ha byte do usuario para julgar, e tambem nao ha cauda.
        return LeituraAoVivo()

    corte = bruto.rfind("\n")
    if corte < 0:
        # NENHUMA quebra de linha no arquivo inteiro. Nao ha uma unica linha
        # completa, entao nao ha o que ler — e a cauda e o arquivo todo.
        return LeituraAoVivo(cauda_incompleta=True)

    completo = bruto[: corte + 1]
    cauda = bruto[corte + 1 :]

    return LeituraAoVivo(
        observacoes=mercado_registro.observacoes_do_arquivo(
            ArquivoRecortado(caminho_real=arquivo, texto=completo)
        ),
        # As linhas de DADO do trecho completo: tudo menos o cabecalho, e sem
        # contar as linhas em branco que o parser tambem pula. O `max` protege o
        # unico caso em que o arquivo tem cabecalho e mais nada — subtrair daria
        # `-1`, e uma contagem negativa na frase de prova seria pior que nenhuma.
        linhas_completas=max(
            0, len([linha for linha in completo.splitlines() if linha.strip()]) - 1
        ),
        # `bool(cauda)` e nao `bool(cauda.strip())`: qualquer byte depois do
        # ultimo terminador e uma linha que o programa nao consegue afirmar,
        # inclusive um punhado de espacos. O rodape prefere dizer "ignorei uma
        # cauda" de graca a esconder uma de verdade.
        cauda_incompleta=bool(cauda),
    )


# ===========================================================================
# A AGREGACAO: UM PONTO E UM INSTANTE, E O BALDE NUNCA INVENTA VALOR
# ===========================================================================


@dataclass(frozen=True)
class PontoDaSerie:
    """UM instante de leitura: o menor, a tipica, e a evidencia de cada um.

    A `Evidencia` VIAJA DENTRO DO PONTO, e nao num campo paralelo — o molde e o
    de `mercado_analise:226-254`, e a razao escrita la vale aqui inteira:
    estatistica sem `n` e adivinhacao com cara de numero, e um `n` que quem
    desenha pode esquecer de pedir e um `n` que uma hora nao vai ser exibido.

    SAO DUAS EVIDENCIAS E NAO UMA porque os pisos sao diferentes e o motivo da
    ausencia tambem: o menor pedido e um FATO OBSERVADO (piso 1 — aquele anuncio
    existiu), e a mediana e uma INFERENCIA (piso 5 — com menos de cinco, duas
    leituras aberrantes movem o miolo). Um campo so obrigaria quem desenha a
    adivinhar de qual dos dois numeros aquele `n` estava falando.

    `frozen` porque ninguem reescreve um ponto depois de calcula-lo: o arquivo e
    a verdade e este objeto e uma conta sobre ele.
    """

    instante: datetime
    menor: Fraction | None
    menor_evidencia: Evidencia
    tipica: Fraction | None
    tipica_evidencia: Evidencia
    n: int


def pontos_por_instante(observacoes: Sequence) -> list[PontoDaSerie]:
    """UM PONTO = UM INSTANTE DE LEITURA (`primeira_vez`). Literalmente.

    A DECISAO, A RECOMENDACAO CONTRARIA, E QUEM DECIDIU
    ===================================================
    Esta funcao aplica `menor_pedido_visivel` e `mediana_dos_unitarios` — as
    MESMAS contas do console — ao SUBCONJUNTO de um unico instante. Ela nao e a
    conta que o console faz: o console chama as duas sobre `observacoes_de(chave)`,
    que e a serie INTEIRA.

    A pesquisa desta fase mediu o custo dessa diferenca sobre o dado real: **92
    observacoes com apenas 13 valores distintos de `primeira_vez`**, e a maior
    serie com **15 observacoes em 2 instantes**. Com `N_MINIMO_PARA_MEDIANA`
    valendo 5, agrupar por instante deixa a linha da mediana **AUSENTE na maior
    parte do grafico**. A docstring de `mercado_analise` ja avisava por extenso
    que "nao existe serie temporal de preco neste CSV — existe uma sequencia de
    anuncios diferentes, e o `n` conta anuncios, nao instantes", e e essa frase
    que esta agregacao paga.

    A PESQUISA, POR ISSO, RECOMENDOU A OUTRA LEITURA: o acumulado ATE o instante,
    que bate literalmente com o console ("os numeros batem para o mesmo
    instante", DASH-03) e quase sempre tem mediana.

    **O USUARIO, CONFRONTADO COM ESSA MEDICAO EXATA EM 2026-09-01, MANTEVE A
    LEITURA LITERAL (CTX-1) e recusou o acumulado.** A recusa esta registrada no
    `01-CONTEXT.md` e no bloco `RESOLVIDO` da `Open Question 1` do
    `01-RESEARCH.md`, que termina com "nao reintroduzir (b)".

    CONSEQUENCIA, E ELA E O CAMINHO NORMAL DESTA TELA
    =================================================
    A linha da mediana falta na maior parte do grafico, e onde ela falta o que
    aparece e a **frase de piso vinda do Python** — nunca um numero. Isso NAO e
    um defeito do grafico nem um estado de erro: e a ausencia de evidencia sendo
    dita com palavra em vez de preenchida com zero, que e a disciplina que este
    projeto inteiro segue. Quem vier depois e achar que "esta faltando dado" tem
    de ler este paragrafo antes de "consertar".

    A ORDEM DE SAIDA E POR INSTANTE, e nao a do arquivo. O `ModeloDeMercado`
    preserva de proposito a ordem do CSV — para nao esconder de quem depura o que
    o arquivo diz — mas um eixo do tempo desordenado desenharia a serie indo e
    voltando. Ordenar e responsabilidade desta camada.
    """
    por_instante: dict[datetime, list] = {}
    for observacao in observacoes:
        por_instante.setdefault(observacao.primeira_vez, []).append(observacao)

    pontos: list[PontoDaSerie] = []
    for instante in sorted(por_instante):
        do_instante = por_instante[instante]
        menor = menor_pedido_visivel(do_instante)
        tipica = mediana_dos_unitarios(do_instante)
        pontos.append(
            PontoDaSerie(
                instante=instante,
                menor=menor.unitario,
                menor_evidencia=menor.evidencia,
                tipica=tipica.unitario,
                tipica_evidencia=tipica.evidencia,
                # O `n` do ponto e o das ofertas COMPARAVEIS, e por isso ele sai
                # da evidencia em vez de `len(do_instante)`: uma linha de
                # quantidade nao positiva nao entra em conta nenhuma, e conta-la
                # como evidencia seria inflar a evidencia.
                n=menor.evidencia.n,
            )
        )
    return pontos


# AS TRES LARGURAS DE BALDE, E POR QUE TRES.
#
# O usuario disse a pergunta dele em voz alta, e ela tem duas resolucoes:
# "mostrar em horarios do dia" e "dar zoom-out em dias atras". Uma largura de
# CINCO MINUTOS serve a primeira (dentro de uma sessao de farm, cada releitura do
# painel e um ponto), uma de UM DIA serve a segunda, e UMA HORA e a intermediaria
# sem a qual o salto entre as duas engole a forma da curva de um dia inteiro.
#
# ESCOLHA, NAO MEDICAO — no molde de `N_MINIMO_PARA_MEDIANA`. Ninguem mediu qual
# resolucao o usuario mais usa, porque ainda nao ha uso: a serie da Adena tem
# zero linhas em campo. Se na pratica uma delas nunca for tocada, ela sai daqui,
# e e uma linha.
LARGURAS_DE_BALDE = {
    "cinco_minutos": timedelta(minutes=5),
    "uma_hora": timedelta(hours=1),
    "um_dia": timedelta(days=1),
}


def ancora_da_meia_noite(instante: datetime) -> datetime:
    """A meia-noite LOCAL do dia deste instante. A origem dos baldes.

    MEDIDO, E E POR ISSO QUE ESTA FUNCAO EXISTE: com a ancora posta num instante
    arbitrario — a primeira observacao, por exemplo, as `2026-08-31 15:00` — os
    baldes de `timedelta(days=1)` comecam as **15:00**. Duas leituras do mesmo
    dia civil, uma as 09:00 e outra as 22:00, caem em baldes DIFERENTES, e "dias
    atras" deixa de querer dizer o que um humano acha que quer dizer.

    O erro nao aparece como excecao nem como numero absurdo: aparece como uma
    curva que "parece deslocada", que e a familia de defeito mais cara de achar.
    Ha teste com CONTROLE prendendo os dois lados — a ancora certa junta o dia, a
    ancora de 15:00 o parte.

    HORA LOCAL INGENUA, sem fuso, como todo carimbo deste projeto: o CSV grava
    `agora.isoformat()` sem `tzinfo`, e introduzir fuso aqui criaria duas
    convencoes de tempo na mesma tela.
    """
    return instante.replace(hour=0, minute=0, second=0, microsecond=0)


def baldes(
    pontos: Sequence[tuple[datetime, Fraction]],
    largura: timedelta,
    ancora: datetime,
) -> list[tuple[datetime, Fraction]]:
    """Um valor por balde, e o valor do balde EXISTIU na tela (D-02).

    Recebe pares `(instante, valor)` — e nao `PontoDaSerie` — porque um ponto tem
    DOIS valores (o menor e a tipica) e cada um vira uma linha propria no
    grafico. Passar o ponto inteiro obrigaria esta funcao a escolher qual das
    duas linhas ela esta agregando, e essa escolha e de quem monta a serie.

    O INDICE E INTEIRO EXATO: `(t - ancora) // largura` opera sobre os
    microssegundos inteiros do `timedelta`. `total_seconds()` devolveria `float`
    — medido, **69713.696** contra **69713** inteiro — e `float` e como um
    centavo aparece do nada. Um indice de balde nao tem parte fracionaria nenhuma
    a preservar, entao o `float` aqui so poderia piorar.

    O VALOR DE CADA BALDE E `statistics.median_low`, E A ALTERNATIVA ESTA
    REFUTADA COM O NUMERO: `statistics.median` sobre quatro `Fraction` devolveu
    **13/42**, um valor que **nao esta na lista** — a media dos dois do meio,
    meio centavo inventado, exatamente o que o D-02 recusou quando decidiu nao
    guardar o unitario arredondado. `median_low` devolve sempre um ELEMENTO da
    lista, e cada elemento ja e um unitario que esteve na tela; a composicao
    portanto preserva a disciplina. Ha um `assert in` por balde prendendo isso, e
    ele e a forma executavel do D-02: `median`, `mean` e `median_high` continuam
    devolvendo um numero plausivel e do tamanho certo, e so o `assert in` os pega.

    A ORDEM DE SAIDA E CRONOLOGICA porque `dict` preserva ordem de INSERCAO, e a
    de insercao e a da lista de entrada — que nao e garantidamente ordenada.
    """
    por_balde: dict[int, list[Fraction]] = {}
    for instante, valor in pontos:
        por_balde.setdefault((instante - ancora) // largura, []).append(valor)

    return sorted(
        (ancora + indice * largura, statistics.median_low(valores))
        for indice, valores in por_balde.items()
    )


def payload(pasta_do_mercado: Path, agora: datetime) -> dict:
    """O dicionario que vira o JSON de `GET /dados`. A forma minima do tracer.

    O `agora` ENTRA POR PARAMETRO, e nao sai de `datetime.now()` aqui: e o que
    torna a recencia afirmavel por teste sem congelar o relogio do processo. A
    casa ja faz isso em `mercado_console`, que recebe `agora` em toda funcao de
    desenho.

    O TEXTO NUNCA E MONTADO AQUI. Ele sai de `formatador_do_unitario(chave)`,
    que e o UNICO ponto de decisao entre a taxa da Adena e o unitario comum. Um
    `f-string` local, ou um `round` a mao, imprimiria `0,00` para a Adena com
    toda a confianca do mundo — o modo de falha mais convincente que o
    `mercado_console` tem, e ele esta documentado la.

    SEM EVIDENCIA, A RESPOSTA E O QUE FALTA — NUNCA UM NUMERO. E o caso NORMAL
    desta fase, e nao uma borda: o CSV de campo tem 92 linhas e zero da serie
    `adena#`. Um `0,00` de espaco reservado seria indistinguivel de uma taxa
    real de zero.
    """
    arquivo = pasta_do_mercado / mercado_registro.ARQUIVO_DE_OBSERVACOES
    leitura = observacoes_ao_vivo(arquivo)

    modelo = ModeloDeMercado.de_observacoes(leitura.observacoes)
    da_adena = modelo.observacoes_de(CHAVE_DA_SERIE_DA_ADENA)

    menor = menor_pedido_visivel(da_adena)
    quando = recencia_do_preco(da_adena)

    if menor.unitario is None:
        # A frase de piso e a MESMA de `mercado_console._linha_do_menor`, com o
        # mesmo `n de piso ofertas distintas`. Ela e curta o bastante para nao
        # justificar mais um import privado, e ha teste prendendo que o texto
        # nunca contem `0,00`.
        texto = (
            f"sem evidencia - {menor.evidencia.n} de "
            f"{menor.evidencia.piso} ofertas distintas"
        )
    else:
        texto = formatador_do_unitario(CHAVE_DA_SERIE_DA_ADENA)(menor.unitario)

    return {
        # O tracer conhece dois estados, e so. A tabela de PRECEDENCIA entre
        # vazio, velho, cambio ausente e contrato quebrado e do plano 01-02 —
        # antecipa-la aqui seria escrever a regra sem o teste que a cobra.
        "estado": "sem_evidencia" if menor.unitario is None else "ok",
        "gerado_em": agora.isoformat(),
        "fonte": {
            "arquivo": str(arquivo),
            "cauda_incompleta": leitura.cauda_incompleta,
            "arquivo_ausente": leitura.arquivo_ausente,
            "linhas_completas": leitura.linhas_completas,
        },
        # A frase da cauda ignorada VIAJA PRONTA. O JS a exibe como recebeu;
        # monta-la la seria a segunda copia de um texto que ja existe aqui.
        "avisos": ([NOTA_DE_LINHA_PARCIAL] if leitura.cauda_incompleta else []),
        "destaque": {
            "xm": {
                "texto": texto,
                "n": menor.evidencia.n,
                "recencia": (
                    _recencia_em_duas_formas(quando, agora)
                    if quando is not None
                    else None
                ),
            }
        },
    }
