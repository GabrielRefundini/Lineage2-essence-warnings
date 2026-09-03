"""A conta da renda: duas amostras viram um PASSO, e muitos passos uma TAXA.

O QUE ESTE MODULO EXISTE PARA FAZER
===================================
Ele recebe `LeituraDaRenda` por parametro — nunca um pixel, nunca um frame,
nunca o relogio — e devolve dois fatos: o **passo** entre duas amostras
consecutivas, e a **taxa por hora** sobre uma sequencia de passos.

ELE E O UNICO CHAMADOR DE PRODUCAO DAS REGRAS DE PAR DE TODA A ARVORE
=====================================================================
As tres regras de par (`o_exp_andou_para_tras`, `o_nivel_andou_para_tras`,
`a_adena_saltou_ordem_de_grandeza`) e a composicao delas (`conferir_o_par`)
nasceram na Fase 1 **sem chamador**, e de proposito: uma fase sem memoria nao
tem a leitura anterior. `tests/test_renda_par.py` guardava essa ausencia com um
portao de arvore de sintaxe.

A Fase 2 e o chamador legitimo que a mensagem daquele portao ja anunciava, e o
portao foi **INVERTIDO** no mesmo commit que criou este arquivo (C-1): ele
passou de "ninguem chama" para "quem chama existe, e um so, e chama a
COMPOSICAO". Se um segundo modulo de `l2scanner/` chamar as regras, ou se este
aqui passar a chamar uma das tres irmas soltas em vez de `conferir_o_par`,
aquele portao cai — e e para cair.

`conferir_o_par` E NAO AS TRES SOLTAS, e a razao e o que ela devolve: a tupla de
TODAS as recusas encontradas. Um par em que o nivel desceu E a adena saltou e um
caso diferente de um par em que so o nivel desceu, e chamar as irmas uma a uma
convidaria a esconder a segunda atras da primeira.

`ler_a_renda` NAO ATRAVESSA ESTA FRONTEIRA (Pitfall 3)
======================================================
Este modulo fala `LeituraDaRenda` (os tres campos ja inteiros) e `CamposDaRenda`
(cada campo inteiro OU recusa). Ele **nunca** chama `ler_a_renda`, e a razao e
que ela devolve a PRIMEIRA recusa em `ORDEM_DOS_CAMPOS` — e `nivel` e o primeiro
dessa ordem. Uma amostra com EXP e adena perfeitos e o nivel recusado sumiria
inteira por causa do campo mais fragil dos tres, que e exatamente o campo que o
LEIT-11 mediu como o mais fragil: 3 das 4 leituras erradas de nivel passaram por
concordancia das duas escalas. Quem quer os tres campos chama
`ler_os_tres_campos`.

O IMPORT DE `renda_leitura` E DIFERIDO, E O NUMERO ESTA MEDIDO
==============================================================
`import l2scanner.renda_leitura` traz **334 modulos, com `cv2` E `numpy`** —
medido nesta arvore hoje — porque ele importa `mercado_visao` e `ocr`, que sao a
metade de PIXEL da Fase 1. Este modulo e a metade de ARITMETICA e nao tem nada
que ver com pixel: importar aquele modulo no topo faria `import
l2scanner.renda_conta` custar OpenCV inteiro, e a Fase 3 tera de importar os
dois de qualquer jeito, mas quem so quiser a conta (um teste, um script de
bancada, o dashboard de amanha) nao deve pagar por isso.

Entao o import mora DENTRO de `passo_entre`, que e a unica funcao que precisa
dele. Depois da primeira chamada e uma busca em `sys.modules`. A doutrina de
"importados, e nao redefinidos" (`mercado_registro.py:65`) continua inteira: a
definicao de `conferir_o_par` e de `DECIMOS_DE_MILESIMO_POR_PONTO` continua uma
so, ela so nao e paga no topo. Ha criterio de aceitacao medindo que `import
l2scanner.renda_conta` nao traz `cv2` nem `numpy`.

`Evidencia` E IMPORTADA DE `mercado_analise`, E ESSA PODE SER NO TOPO
=====================================================================
Medido do mesmo jeito: `import l2scanner.mercado_analise` traz **102 modulos,
sem `cv2` e sem `numpy`**. Como o import nao arrasta os pesados, a irma local
que o plano autorizava nao e necessaria — e uma segunda `Evidencia` seria duas
definicoes do mesmo conceito, que e como elas divergem.

NENHUM LIMIAR TEM VALOR DE FABRICA
==================================
`fator_de_salto`, `limiar_de_lacuna_em_segundos`, `piso_de_amostras` e
`piso_da_janela_em_segundos` sao **somente-nomeados e sem default**: chamar sem
eles levanta `TypeError`, no molde exato de
`a_adena_saltou_ordem_de_grandeza`. Um limiar por omissao e a definicao de
constante magica. Os cinco numeros moram na secao `[renda]` do `config.toml` e
os defaults deles moram na CASCA (`config.AjustesDaRenda`) — este modulo nao
sabe que o `config.toml` existe, e nao importa `config`.

O RELOGIO ENTRA POR PARAMETRO, SEMPRE (CTX-10)
==============================================
Nao ha `datetime.now()` aqui, nem `time.time()`, nem em comentario. O carimbo
chega dentro da propria `LeituraDaRenda`. O PC do usuario e dual boot e o
Windows volta ~3h adiantado do Linux; uma taxa por hora com relogio que pula e
lixo silencioso. Ha portao de arvore de sintaxe prendendo isso.

O SINAL DE UM DELTA DE TEMPO NUNCA E ABSORVIDO
==============================================
Nao existe `abs()`, `max()` nem `min()` neste arquivo, e os tres estao no mesmo
portao de proposito: `max(0, atual.carimbo - anterior.carimbo)` faz exatamente o
mesmo estrago que `abs(...)` com outro nome. Um intervalo negativo e um EVENTO
NOMEADO (`relogio-andou-para-tras`) e nao um numero a consertar.

A ARITMETICA E EXATA
====================
O intervalo e `float` epoch — a subtracao de dois epochs e exata, e e o
denominador de toda taxa desta fase. Os ganhos sao INTEIROS escalados (EXP em
decimos de milesimo de ponto percentual, adena em unidades). A divisao da taxa e
`Fraction`, no precedente de `mercado_analise.unitario`: a taxa e um numero que
vai a tela e a outros consumidores, e um `float` ali traria erro binario para
dentro de uma comparacao que o usuario faz de cabeca.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Sequence

from .mercado_analise import Evidencia

if TYPE_CHECKING:  # pragma: no cover - so para o verificador de tipos
    # Sob `TYPE_CHECKING` o import NAO acontece em tempo de execucao, entao os
    # tres tipos podem atravessar a assinatura sem que `cv2` entre junto.
    from .renda_leitura import LeituraDaRenda, RecusaDaRenda

# TUPLA E NAO LISTA, e a razao e executavel: o portao `memoria_de_modulo` de
# `tests/test_renda_par.py` acusa todo literal MUTAVEL de nivel de modulo como
# marca de estado vivo, e ele passou a varrer este arquivo tambem.
__all__ = (
    "DESCONTINUIDADE_DA_ANCORA",
    "DESCONTINUIDADE_DA_LACUNA",
    "DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS",
    "DESCONTINUIDADES_QUE_EXCLUEM",
    "GRANDEZA_DA_ADENA",
    "GRANDEZA_DO_EXP",
    "PassoDaRenda",
    "TaxaDaRenda",
    "UNIDADE_DA_JANELA",
    "passo_entre",
    "taxa_por_hora",
)


# ---------------------------------------------------------------------------
# AS DESCONTINUIDADES, E AS QUATRO DESTE PLANO SAO TODAS DE EXCLUSAO
# ---------------------------------------------------------------------------
#
# Uma descontinuidade preenchida quer dizer "o passo nao entra no denominador".
# O `02-02` acrescenta a QUINTA, `nivel-indisponivel-com-exp-subindo`, que e de
# PROCEDENCIA e nao de exclusao — o passo entra, o ganho de EXP e computado, e a
# coluna registra apenas que o nivel nao foi lido naquele tique. Ela nao existe
# ainda, e por isso `DESCONTINUIDADES_QUE_EXCLUEM` e hoje o conjunto inteiro: no
# dia em que a quinta nascer, e este nome que impede que ela seja excluida por
# engano junto com as outras.

# A primeira amostra de uma sequencia nao tem anterior, entao ela e ANCORA e
# nao delta. E o mesmo estado que um reinicio produz — e por isso o REG-02
# ("reiniciar nao inventa nem apaga renda") fecha na CONTA e nao no disco (C-7).
DESCONTINUIDADE_DA_ANCORA = "ancora"

# O intervalo passou do limiar: o scanner ficou cego, e o tempo cego SAI do
# denominador (CTX-2). Ele e contado a parte, porque "a taxa caiu" e "o scanner
# nao viu" sao dois fatos e o usuario nao tem como distingui-los sozinho.
DESCONTINUIDADE_DA_LACUNA = "lacuna"

# O carimbo do atual e MENOR que o do anterior. Nao e um intervalo negativo a
# consertar: e o dual boot do usuario, e ele tem nome.
DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS = "relogio-andou-para-tras"

DESCONTINUIDADES_QUE_EXCLUEM = (
    DESCONTINUIDADE_DA_ANCORA,
    DESCONTINUIDADE_DA_LACUNA,
    DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS,
)

# O passo coerente NAO tem descontinuidade, e o vazio e o valor dele. Uma
# string vazia e nao `None` porque esta mesma palavra vai virar coluna de CSV em
# `renda_registro`, e `None` viraria a string "None" no disco.
SEM_DESCONTINUIDADE = ""


# ---------------------------------------------------------------------------
# AS DUAS GRANDEZAS QUE ESTA FASE MEDE
# ---------------------------------------------------------------------------

# O EXP viaja em DECIMOS DE MILESIMO de ponto percentual, e o nome da grandeza
# carrega a unidade pelo mesmo motivo que `total_em_centesimos` carrega a dela:
# e o que faz `394380` ficar autoexplicativo para quem le sem o fonte na frente.
GRANDEZA_DO_EXP = "exp_em_decimos"
GRANDEZA_DA_ADENA = "adena"

GRANDEZAS = (GRANDEZA_DO_EXP, GRANDEZA_DA_ADENA)

# ---------------------------------------------------------------------------
# A UNIDADE DA JANELA, E ELA E OBRIGATORIA PORQUE A ESCOLHA DELA E O REQUISITO
# ---------------------------------------------------------------------------
#
# O molde e `mercado_analise.UNIDADE_DA_JANELA` ("ofertas distintas"), e a razao
# e a mesma com outro conteudo: sem esta palavra viajando junto do numero, o
# usuario le a janela como MINUTOS DE RELOGIO — e ela nao e isso.
#
# `minutos farmados` e a soma dos intervalos entre amostras consecutivas
# ACEITAS. O tempo em que o scanner ficou cego nao esta ai dentro, porque ele
# nao foi farmado DO PONTO DE VISTA DA MEDICAO (CTX-2). Medido em campo, a
# diferenca entre as duas leituras e enorme: a media de 8h45 deu 226 mil adena/h
# e a janela curta deu 466 mil/h, e a diferenca inteira e tempo parado.
UNIDADE_DA_JANELA = "minutos farmados"

# UNIDADE, E NAO LIMIAR. Uma hora tem 3600 segundos em toda maquina e em todo
# `config.toml`; nao ha nada a calibrar aqui, e por isso este numero pode morar
# no fonte enquanto os cinco limiares nao podem.
SEGUNDOS_POR_HORA = 3_600

# Um nivel inteiro sao 100 pontos percentuais de EXP. Tambem UNIDADE e nao
# limiar: e a definicao da barra, e nao uma escolha nossa.
PONTOS_PERCENTUAIS_DE_UM_NIVEL = 100


# ---------------------------------------------------------------------------
# O PASSO: o que aconteceu entre DUAS amostras
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PassoDaRenda:
    """O delta entre duas amostras consecutivas, com o julgamento do par junto.

    OS CAMPOS DE DELTA SAO `None` QUANDO NAO HOUVE DELTA A CALCULAR, e nao zero.
    Sao fatos diferentes, e colapsa-los mentiria duas vezes: um ganho de zero e
    "medi e nao ganhou nada", e `None` e "nao havia o que medir" — a ancora, a
    lacuna e o relogio para tras. Um zero no lugar de `None` entraria no
    numerador de uma taxa como se fosse medicao.

    `intervalo_em_segundos` GUARDA O SINAL. Num salto do relogio para tras ele
    sai NEGATIVO, e fica negativo: quem exclui o passo do denominador e a
    `descontinuidade`, e nao um `abs()` que apagaria a evidencia do salto.

    `recusas` E A TUPLA QUE `conferir_o_par` DEVOLVEU, inteira. Tupla vazia e o
    par coerente — e e o desfecho do par de campo com o level up verdadeiro.
    """

    anterior: LeituraDaRenda | None
    atual: LeituraDaRenda
    intervalo_em_segundos: float | None
    ganho_de_exp_em_decimos: int | None
    ganho_de_adena: int | None
    gasto_de_adena: int | None
    descontinuidade: str
    recusas: tuple[RecusaDaRenda, ...]

    @property
    def aceito(self) -> bool:
        """Este passo entra no denominador de uma taxa?

        DUAS CONDICOES E AS DUAS SAO NECESSARIAS: nenhuma descontinuidade (o
        tempo dele existiu e e mensuravel) e nenhuma recusa do par (os numeros
        dele sao criveis). Um passo com recusa tem intervalo perfeitamente bom e
        numeros duvidosos; contar o tempo dele e descartar o ganho torceria a
        taxa para baixo, e contar os dois gravaria o numero duvidoso.
        """
        return self.descontinuidade == SEM_DESCONTINUIDADE and not self.recusas


def passo_entre(
    anterior: LeituraDaRenda | None,
    atual: LeituraDaRenda,
    *,
    fator_de_salto: int,
    limiar_de_lacuna_em_segundos: float,
) -> PassoDaRenda:
    """O passo entre duas amostras. `anterior=None` produz a ancora.

    ESTA E A UNICA FUNCAO DE PRODUCAO DE TODA A ARVORE QUE CHAMA AS REGRAS DE
    PAR, e ela chama `conferir_o_par` — a composicao — e nunca uma das tres
    irmas soltas. O portao invertido de `tests/test_renda_par.py` prende as duas
    coisas.

    OS DOIS LIMIARES SAO SOMENTE-NOMEADOS E SEM VALOR DE FABRICA. Chamar sem
    eles levanta `TypeError`, e isso e o desenho: o `fator_de_salto` a Fase 1 ja
    exigia assim, e o limiar de lacuna e a mesma familia de numero — ele decide
    o que e "o scanner ficou cego", e essa fronteira e do usuario e nao deste
    fonte.

    A ORDEM DAS TRES PERGUNTAS IMPORTA, e ela e: existe anterior? o relogio
    andou para tras? o intervalo passou do limiar? Perguntar da lacuna antes do
    salto do relogio classificaria um salto para tras de vinte minutos como
    lacuna, e as duas coisas pedem conserto diferente do usuario.

    O LEVEL UP E `(um nivel inteiro - o EXP de antes) + o EXP de agora`, E SO
    QUANDO O NIVEL REALMENTE SUBIU (CTX-5). O par de campo medido —
    `nivel 66, exp 685_632` -> `nivel 67, exp 80_012` — sai `394_380` decimos,
    que sao os 39,438 pontos percentuais que o usuario viu na tela. A subtracao
    ingenua diria `-605_620`, e um numero negativo desses viraria "a pior hora
    da noite" no registro de quem subiu de nivel.
    """
    # O import mora aqui e nao no topo, e o numero que sustenta isso esta na
    # docstring do modulo: `renda_leitura` traz 334 modulos com `cv2` e `numpy`,
    # e este modulo nao encosta em pixel nenhum. A definicao continua uma so.
    from .renda_leitura import DECIMOS_DE_MILESIMO_POR_PONTO, conferir_o_par

    if anterior is None:
        return PassoDaRenda(
            anterior=None,
            atual=atual,
            intervalo_em_segundos=None,
            ganho_de_exp_em_decimos=None,
            ganho_de_adena=None,
            gasto_de_adena=None,
            descontinuidade=DESCONTINUIDADE_DA_ANCORA,
            recusas=(),
        )

    # SEM `abs`, SEM `max` E SEM `min`. O sinal e o dado.
    intervalo = float(atual.carimbo) - float(anterior.carimbo)

    # As regras de par sao sobre os NUMEROS e nao sobre o relogio, entao elas
    # rodam sempre que ha um par — inclusive num passo que o tempo ja excluiu.
    # Um par cujo nivel desceu continua sendo um par cujo nivel desceu.
    recusas = conferir_o_par(anterior, atual, fator_de_salto=fator_de_salto)

    if intervalo < 0:
        return PassoDaRenda(
            anterior=anterior,
            atual=atual,
            intervalo_em_segundos=intervalo,
            ganho_de_exp_em_decimos=None,
            ganho_de_adena=None,
            gasto_de_adena=None,
            descontinuidade=DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS,
            recusas=recusas,
        )

    if intervalo > float(limiar_de_lacuna_em_segundos):
        # O ganho SAI JUNTO COM O TEMPO, e nao so o tempo. Guardar o ganho de
        # uma lacuna e jogar fora o intervalo dela poria, num denominador de dez
        # minutos, o numerador de meia hora — que e uma taxa inventada.
        return PassoDaRenda(
            anterior=anterior,
            atual=atual,
            intervalo_em_segundos=intervalo,
            ganho_de_exp_em_decimos=None,
            ganho_de_adena=None,
            gasto_de_adena=None,
            descontinuidade=DESCONTINUIDADE_DA_LACUNA,
            recusas=recusas,
        )

    decimos_de_um_nivel = DECIMOS_DE_MILESIMO_POR_PONTO * PONTOS_PERCENTUAIS_DE_UM_NIVEL
    if int(atual.nivel) > int(anterior.nivel):
        ganho_de_exp = (decimos_de_um_nivel - int(anterior.exp)) + int(atual.exp)
    else:
        ganho_de_exp = int(atual.exp) - int(anterior.exp)

    # CTX-6: queda no contador de adena e GASTO, e nao renda negativa. Os dois
    # saem em campos separados, e o ganho bruto e a soma dos deltas positivos.
    # Escrito com `if` e nao com `max(0, delta)` porque o portao de sinal deste
    # plano proibe os tres nomes que absorvem sinal, e com razao: neste arquivo
    # `max` seria certo aqui e catastrofico tres linhas acima.
    delta_de_adena = int(atual.adena) - int(anterior.adena)
    if delta_de_adena < 0:
        ganho_de_adena = 0
        gasto_de_adena = -delta_de_adena
    else:
        ganho_de_adena = delta_de_adena
        gasto_de_adena = 0

    return PassoDaRenda(
        anterior=anterior,
        atual=atual,
        intervalo_em_segundos=intervalo,
        ganho_de_exp_em_decimos=ganho_de_exp,
        ganho_de_adena=ganho_de_adena,
        gasto_de_adena=gasto_de_adena,
        descontinuidade=SEM_DESCONTINUIDADE,
        recusas=recusas,
    )


# ---------------------------------------------------------------------------
# A TAXA: o que muitos passos dizem por hora
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaxaDaRenda:
    """A taxa por hora de uma grandeza, e ela NUNCA e um numero nu (REND-06).

    A FORMA E A DE `Tendencia` E A DE `Evidencia`, e nao a aritmetica delas: a
    `Evidencia` viaja DENTRO do resultado, `por_hora` e `None` sempre que nao ha
    numero a dizer, e `motivo_da_ausencia` diz POR QUE. Quem desenha nunca
    precisa adivinhar o motivo de um campo vazio.

    `janela_farmada_em_segundos` E O DENOMINADOR REAL, e `unidade_da_janela`
    viaja escrita ao lado dele — `minutos farmados`, que e um fato diferente de
    `minutos de relogio`. `lacunas_excluidas` e `segundos_em_lacuna` sao os dois
    fatos que SAIRAM do denominador, e eles ficam visiveis para que "a taxa
    caiu" nunca seja confundido com "o scanner nao viu".

    `ate` E A RECENCIA, E ELA E SEPARADA DO VALOR (REND-06). Um numero bom de
    quarenta minutos atras continua sendo um numero bom; ele so nao e o de
    agora, e quem exibe precisa poder dizer as duas coisas em campos diferentes.
    E o carimbo da ultima amostra que ENTROU na conta, e nao o da ultima
    recebida — uma recencia que contasse amostras recusadas prometeria uma
    frescura que o numero nao tem.
    """

    grandeza: str
    evidencia: Evidencia
    por_hora: Fraction | None
    motivo_da_ausencia: str | None
    janela_farmada_em_segundos: float
    unidade_da_janela: str
    lacunas_excluidas: int
    segundos_em_lacuna: float
    ate: float | None


def _ganho_do_passo(passo: PassoDaRenda, grandeza: str) -> int:
    """O ganho daquele passo NAQUELA grandeza. So para passos aceitos."""
    if grandeza == GRANDEZA_DO_EXP:
        return int(passo.ganho_de_exp_em_decimos)
    if grandeza == GRANDEZA_DA_ADENA:
        return int(passo.ganho_de_adena)
    raise ValueError(
        f"grandeza desconhecida: {grandeza!r}. As que existem sao {GRANDEZAS!r}"
    )


def taxa_por_hora(
    passos: Sequence[PassoDaRenda],
    *,
    grandeza: str,
    piso_de_amostras: int,
    piso_da_janela_em_segundos: float,
) -> TaxaDaRenda:
    """A taxa por hora de uma grandeza sobre uma sequencia de passos.

    OS DOIS PISOS SAO DOIS PORQUE SAO DOIS FATOS DIFERENTES, e um piso so
    deixaria passar exatamente o caso que o requisito nomeia. Oito amostras em
    quarenta segundos e oito amostras em duas horas nao valem o mesmo: o
    primeiro e ruido com cara de taxa horaria, e e ele que o criterio 1 do
    roadmap manda anunciar como ruido. Quando um dos dois falta, o
    `motivo_da_ausencia` diz QUAL — nunca um motivo generico.

    OS DOIS SAO SOMENTE-NOMEADOS E SEM VALOR DE FABRICA, pela mesma regra do
    `fator_de_salto`: eles moram no `config.toml` do usuario e os defaults deles
    moram na casca, nunca aqui.

    O DENOMINADOR E A SOMA DOS INTERVALOS ENTRE AMOSTRAS CONSECUTIVAS ACEITAS
    (CTX-2), e nao o relogio de parede entre a primeira e a ultima. Dividir pelo
    relogio de parede e o padrao silencioso — e por isso esta frase existe: sem
    ela alguem o implementa sem perceber, e a taxa de uma noite com uma pausa
    para o jantar sai artificialmente baixa sem que o usuario tenha como
    distinguir isso de "o farm piorou".

    A DIVISAO E `Fraction`, no precedente de `mercado_analise.unitario`.
    """
    aceitos = [passo for passo in passos if passo.aceito]
    lacunas = [
        passo
        for passo in passos
        if passo.descontinuidade == DESCONTINUIDADE_DA_LACUNA
    ]

    janela_farmada = 0.0
    for passo in aceitos:
        janela_farmada = janela_farmada + float(passo.intervalo_em_segundos)

    segundos_em_lacuna = 0.0
    for passo in lacunas:
        segundos_em_lacuna = segundos_em_lacuna + float(passo.intervalo_em_segundos)

    evidencia = Evidencia(n=len(aceitos), piso=int(piso_de_amostras))
    ate = aceitos[-1].atual.carimbo if aceitos else None

    def _sem_numero(motivo: str) -> TaxaDaRenda:
        return TaxaDaRenda(
            grandeza=grandeza,
            evidencia=evidencia,
            por_hora=None,
            motivo_da_ausencia=motivo,
            janela_farmada_em_segundos=janela_farmada,
            unidade_da_janela=UNIDADE_DA_JANELA,
            lacunas_excluidas=len(lacunas),
            segundos_em_lacuna=segundos_em_lacuna,
            ate=ate,
        )

    if not evidencia.suficiente:
        return _sem_numero(
            f"amostras abaixo do piso: {evidencia.n} passo(s) aceito(s) e o "
            f"piso 'amostras_minimas_para_taxa' e {evidencia.piso}. Faltam "
            f"{evidencia.faltam}."
        )

    if janela_farmada < float(piso_da_janela_em_segundos):
        return _sem_numero(
            f"janela abaixo do piso: {janela_farmada:.1f} segundos de "
            f"{UNIDADE_DA_JANELA} e o piso "
            f"'janela_minima_para_taxa_segundos' e "
            f"{float(piso_da_janela_em_segundos):.1f}."
        )

    if janela_farmada <= 0:
        # So alcancavel com um piso de janela zerado, e mesmo assim: dividir por
        # zero e a unica coisa pior que nao ter numero.
        return _sem_numero(
            "janela farmada de zero segundo: nao ha denominador, e uma taxa "
            "por hora sobre zero segundo nao e um numero grande, e nenhum."
        )

    ganho = 0
    for passo in aceitos:
        ganho = ganho + _ganho_do_passo(passo, grandeza)

    return TaxaDaRenda(
        grandeza=grandeza,
        evidencia=evidencia,
        por_hora=Fraction(ganho) * SEGUNDOS_POR_HORA / Fraction(janela_farmada),
        motivo_da_ausencia=None,
        janela_farmada_em_segundos=janela_farmada,
        unidade_da_janela=UNIDADE_DA_JANELA,
        lacunas_excluidas=len(lacunas),
        segundos_em_lacuna=segundos_em_lacuna,
        ate=ate,
    )
