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
    from .renda_leitura import CamposDaRenda, LeituraDaRenda, RecusaDaRenda

# TUPLA E NAO LISTA, e a razao e executavel: o portao `memoria_de_modulo` de
# `tests/test_renda_par.py` acusa todo literal MUTAVEL de nivel de modulo como
# marca de estado vivo, e ele passou a varrer este arquivo tambem.
__all__ = (
    "AsDuasTaxas",
    "ContagemDaRenda",
    "DESCONTINUIDADE_DA_ADENA_INDISPONIVEL",
    "DESCONTINUIDADE_DA_ANCORA",
    "DESCONTINUIDADE_DA_LACUNA",
    "DESCONTINUIDADE_DO_EXP_INDISPONIVEL",
    "DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_CAINDO",
    "DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_SUBINDO",
    "DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS",
    "DESCONTINUIDADES_DE_PROCEDENCIA",
    "DESCONTINUIDADES_DO_TEMPO",
    "DESCONTINUIDADES_QUE_EXCLUEM",
    "GRANDEZA_DA_ADENA",
    "GRANDEZA_DO_EXP",
    "MOTIVO_DA_TAXA_DE_EXP_NEGATIVA",
    "MOTIVO_DA_TAXA_DE_EXP_ZERADA",
    "PassoDaRenda",
    "TaxaDaRenda",
    "TempoAteONivel",
    "UNIDADE_DA_JANELA",
    "as_duas_taxas",
    "contar_o_passo",
    "ganho_do_passo",
    "passo_entre",
    "passo_entre_campos",
    "passos_da_janela",
    "taxa_por_hora",
    "tempo_ate_o_nivel",
)


# ---------------------------------------------------------------------------
# AS DESCONTINUIDADES, E UMA DELAS NAO EXCLUI NADA
# ---------------------------------------------------------------------------
#
# Uma descontinuidade preenchida quer dizer, quase sempre, "o passo nao entra no
# denominador". A EXCECAO e `nivel-indisponivel-com-exp-subindo`, que o `02-02`
# acrescentou e que e de PROCEDENCIA e nao de exclusao: o passo entra, o ganho de
# EXP e computado, e a coluna registra apenas que o nivel nao foi lido naquele
# tique. E por causa dela que `DESCONTINUIDADES_QUE_EXCLUEM` existe com este nome
# em vez de ser "todas" — sem o nome, ela seria excluida por engano junto com as
# outras, e o preco disso esta medido logo abaixo.
#
# ELAS SE PARTEM EM DUAS FAMILIAS, e a diferenca e por GRANDEZA:
#
#   DESCONTINUIDADES_DO_TEMPO   -> o INTERVALO nao existe ou nao e mensuravel,
#                                  entao NENHUMA grandeza pode ser medida ali
#   as demais que excluem       -> o intervalo e bom e falta UM campo; a grandeza
#                                  daquele campo sai do denominador e as outras
#                                  CONTINUAM. E o que faz o nivel recusado — 79%
#                                  dos tiques, `02-CONTEXT.md:150` — nao derrubar
#                                  a adena junto.

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

# O NIVEL NAO FOI LIDO E O EXP CAIU (CTX-5, LEIT-11, T-02-09). A tentacao e
# chamar de level up, e e exatamente ai que a alternativa registrada da CTX-5
# erra: MORRER tambem derruba o EXP muito. E o nivel e o pior campo possivel
# para adivinhar — o LEIT-11 mediu que 3 das 4 leituras erradas de nivel foram
# aceitas POR CONCORDANCIA das duas escalas de OCR, entao ali "parece certo"
# prova menos que em qualquer outro campo. Inventar um level up e pior que
# perder um: o inventado entra na taxa como ~100 pontos percentuais de ganho.
DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_CAINDO = (
    "nivel-indisponivel-com-exp-caindo"
)

# O NIVEL NAO FOI LIDO E O EXP SUBIU. Este NAO exclui: e PROCEDENCIA.
#
# Um level up faz o EXP CAIR. A CTX-5 proibe INVENTAR um level up, e inventar um
# exige o EXP caindo — com o EXP subindo nao existe level up a supor, e a regra
# que suprimia este ramo cobrava sem proteger.
#
# E O LIMIAR DE LACUNA E O QUE FECHA O ARGUMENTO, com numero: o intervalo de um
# passo aceito e no maximo `lacuna_maxima_segundos` (60 por omissao); acima disso
# o passo ja saiu como lacuna. A ~104 abates por minuto e 0,001011 ponto
# percentual por abate (REND-08), a barra anda ~0,1 PONTO PERCENTUAL em sessenta
# segundos. Para o EXP subir ATRAVESSANDO um nivel dentro de um passo aceito, ela
# teria de andar ~100 pontos no mesmo intervalo — tres ordens de grandeza acima
# do medido. QUEM LEVANTAR `lacuna_maxima_segundos` PARA HORAS REABRE ESTE CASO,
# e o lugar de reabri-lo e aqui.
#
# O que a regra suprimida custava era o requisito inteiro: com o nivel recusado
# em 79% dos tiques (`02-CONTEXT.md:150`), exigir nivel nos DOIS lados do par
# deixaria o passo de EXP valer em 0,21 x 0,21 = 4,4% dos pares — a ~1 Hz, dez
# minutos de farm dariam ~26 passos e ~26 segundos de janela farmada, ABAIXO do
# piso de 120 s, e a taxa de XP sairia sem numero na quase totalidade das
# sessoes.
DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_SUBINDO = (
    "nivel-indisponivel-com-exp-subindo"
)

# OS DOIS CAMPOS QUE TAMBEM PODEM FALTAR, e eles precisam de nome pela mesma
# razao que o nivel: sem marcador, um passo em que a adena nao foi lida sairia
# com a descontinuidade VAZIA e pareceria um passo limpo. A recusa de LEITURA
# daquele campo ja viaja na coluna propria (`motivo_do_exp`, `motivo_da_adena`);
# o que estes dois dizem e o fato de PAR: aquela grandeza nao tem passo aqui.
#
# A adena recusa em 21% dos tiques (`02-CONTEXT.md:150`), entao este nao e um
# caso raro — ele e um em cada cinco.
DESCONTINUIDADE_DO_EXP_INDISPONIVEL = "exp-indisponivel"
DESCONTINUIDADE_DA_ADENA_INDISPONIVEL = "adena-indisponivel"

# O TEMPO NAO EXISTIU OU NAO E MENSURAVEL: nenhuma grandeza sobrevive a estas
# tres, porque nao ha intervalo com que dividir.
DESCONTINUIDADES_DO_TEMPO = (
    DESCONTINUIDADE_DA_ANCORA,
    DESCONTINUIDADE_DA_LACUNA,
    DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS,
)

# AS QUE EXCLUEM AO MENOS UMA GRANDEZA. `PassoDaRenda.aceito` — que e o "passo
# INTEIRO aproveitavel" — se apoia nesta tupla; o denominador POR GRANDEZA se
# apoia em `aceito_para`, que e mais fino.
DESCONTINUIDADES_QUE_EXCLUEM = DESCONTINUIDADES_DO_TEMPO + (
    DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_CAINDO,
    DESCONTINUIDADE_DO_EXP_INDISPONIVEL,
    DESCONTINUIDADE_DA_ADENA_INDISPONIVEL,
)

# A QUE NAO EXCLUI NADA. Ela existe como TUPLA e nao como comentario para que
# "esta descontinuidade conta" seja uma afirmacao executavel, e para que somar
# uma sexta descontinuidade obrigue quem a escrever a dizer de que lado ela cai.
DESCONTINUIDADES_DE_PROCEDENCIA = (
    DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_SUBINDO,
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

# A mesma coisa, e pela mesma razao: sessenta minutos por hora nao e calibravel.
MINUTOS_POR_HORA = 60

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
    par coerente — e e o desfecho do par de campo com o level up verdadeiro. Ela
    tambem sai vazia no caminho de `CamposDaRenda` com um campo recusado, e ali
    isso NAO quer dizer "o par foi conferido e esta bom": quer dizer que nao
    havia par a conferir. Quem distingue os dois e a `descontinuidade`.

    `carimbo` E O DA AMOSTRA ATUAL, E ELE VIVE NO PASSO. Poderia sair de
    `atual.carimbo` quando `atual` e uma `LeituraDaRenda` — mas no caminho de
    `CamposDaRenda` esse campo NAO EXISTE (a Fase 1 nao carimba o objeto de tres
    campos), e a recencia da taxa nao pode depender de qual dos dois caminhos
    produziu o passo.

    `niveis_ganhos` E `None` QUANDO NAO SE SABE, e zero quando se sabe que
    ninguem subiu. Com o nivel recusado nao ha o que afirmar, e um zero ali seria
    a afirmacao "nao houve level up" feita por quem nao leu o nivel.
    """

    anterior: LeituraDaRenda | CamposDaRenda | None
    atual: LeituraDaRenda | CamposDaRenda
    carimbo: float
    intervalo_em_segundos: float | None
    ganho_de_exp_em_decimos: int | None
    niveis_ganhos: int | None
    ganho_de_adena: int | None
    gasto_de_adena: int | None
    descontinuidade: str
    recusas: tuple[RecusaDaRenda, ...]

    @property
    def aceito(self) -> bool:
        """Este passo esta INTEIRO — todas as grandezas dele sao aproveitaveis?

        DUAS CONDICOES E AS DUAS SAO NECESSARIAS: nenhuma descontinuidade que
        exclua (o tempo dele existiu, e mensuravel, e nenhum campo faltou) e
        nenhuma recusa do par (os numeros dele sao criveis). Um passo com recusa
        tem intervalo perfeitamente bom e numeros duvidosos; contar o tempo dele
        e descartar o ganho torceria a taxa para baixo, e contar os dois gravaria
        o numero duvidoso.

        ELE NAO E O CRITERIO DO DENOMINADOR — `aceito_para` e. A diferenca e o
        nivel recusado: um passo com `nivel-indisponivel-com-exp-caindo` nao esta
        inteiro (o EXP dele nao existe) e mesmo assim tem uma adena perfeitamente
        boa, que continua contando. Colapsar os dois criterios num so faria o
        campo mais fragil dos tres derrubar os outros dois em 79% dos tiques.
        """
        return (
            self.descontinuidade not in DESCONTINUIDADES_QUE_EXCLUEM
            and not self.recusas
        )

    def aceito_para(self, grandeza: str) -> bool:
        """Este passo entra no denominador DAQUELA grandeza?

        TRES CONDICOES: o intervalo existe e e mensuravel (nenhuma das tres
        descontinuidades de TEMPO), o par nao foi recusado, e AQUELA grandeza
        produziu ganho. A terceira e o que torna o denominador por grandeza:
        `ganho is None` e como o passo diz "esta eu nao medi", e ela e a mesma
        frase para o campo que recusou, para o EXP que caiu sem nivel, e para
        qualquer outro caso que venha depois.
        """
        return (
            self.descontinuidade not in DESCONTINUIDADES_DO_TEMPO
            and not self.recusas
            and ganho_do_passo(self, grandeza) is not None
        )


def _decimos_de_um_nivel() -> int:
    """Os cem pontos percentuais de um nivel, EM DECIMOS DE MILESIMO.

    ELE E DERIVADO E NUNCA ESCRITO A MAO. `1_000_000` como literal seria uma
    SEGUNDA verdade sobre a mesma unidade — a Fase 1 ja declarou a escala em
    `DECIMOS_DE_MILESIMO_POR_PONTO`, e no dia em que ela mudar so uma das duas
    mudaria. Ha portao de arvore de sintaxe afirmando que o literal nao aparece.

    O import e DIFERIDO pela razao medida na docstring do modulo, e por isso ele
    esta escondido atras de uma funcao: quem so quer a janela movel ou a
    contagem nao paga `cv2` para ter os cem pontos percentuais.
    """
    from .renda_leitura import DECIMOS_DE_MILESIMO_POR_PONTO

    return DECIMOS_DE_MILESIMO_POR_PONTO * PONTOS_PERCENTUAIS_DE_UM_NIVEL


def _exp_do_par(
    nivel_anterior: int, exp_anterior: int, nivel_atual: int, exp_atual: int
) -> tuple[int, int]:
    """O ganho de EXP e quantos niveis foram ganhos. Os DOIS lados com nivel.

    A AFIRMACAO `atual.nivel > anterior.nivel` E DESTA FASE. Nenhuma linha de
    `renda_leitura.py` a faz: aquele modulo apenas SE CALA quando o nivel muda —
    `o_exp_andou_para_tras` se abstem em qualquer direcao e
    `o_nivel_andou_para_tras` so olha para baixo. O que falta la e a AFIRMACAO e
    a CONTA, e as duas moram aqui.

    OS NIVEIS ATRAVESSADOS CONTAM, E NAO SO O ULTIMO. Dois niveis num passo so
    acontece com o scanner cego no meio, e uma formula que somasse sempre um
    nivel devolveria um numero menor sem avisar — o pior tipo de erro que existe
    nesta arvore, porque ele e plausivel.

    `niveis_ganhos` NUNCA SAI NEGATIVO. Um nivel que desce nao e o jogo: e um
    digito trocado, e a recusa da Fase 1 ja o pegou. Devolver `-1` daqui
    convidaria alguem a soma-lo em algum lugar.
    """
    niveis = nivel_atual - nivel_anterior
    if niveis > 0:
        um_nivel = _decimos_de_um_nivel()
        atravessados = (niveis - 1) * um_nivel
        return (um_nivel - exp_anterior) + exp_atual + atravessados, niveis
    return exp_atual - exp_anterior, 0


def _adena_do_par(adena_anterior: int, adena_atual: int) -> tuple[int, int]:
    """`(ganho, gasto)`, e os dois sao POSITIVOS ou zero — nunca o mesmo numero.

    CTX-6: queda no contador de adena e GASTO, e nao renda negativa. Os dois
    saem em campos separados pela mesma razao que `duplicadas` e `perdidas` sao
    campos separados em `mercado_modo.Contagem`: sao fatos diferentes, e somar um
    no outro apaga a pergunta que o usuario tem.

    ESCRITO COM `if` E NAO COM `max(0, delta)` / `abs(delta)`. Os dois nomes
    ABSORVEM O SINAL, e absorver e o defeito — neste mesmo arquivo `max` seria
    certo aqui e catastrofico no intervalo do relogio, e um leitor apressado nao
    tem como distinguir os dois usos. O ramo explicito e mais longo de escrever,
    e e exatamente esse o ponto: o sinal vira DECISAO visivel no fonte.
    """
    delta = adena_atual - adena_anterior
    if delta < 0:
        return 0, -delta
    return delta, 0


def _valor_do_campo(campo) -> int | None:
    """O inteiro daquele campo, ou `None` se ele saiu como RECUSA.

    `ValorDaRenda` e `ValorDaAdena` tem `valor`; `RecusaDaRenda` tem `campo`,
    `motivo` e `detalhe` e NAO tem. A pergunta e feita por atributo e nao por
    `isinstance` de proposito: `isinstance` exigiria importar `renda_leitura`
    aqui, e este caminho — o do campo recusado — e o que roda em 79% dos tiques
    justamente quando NAO ha nada de pixel a fazer. Pagar `cv2` para descobrir
    que o nivel nao leu seria o custo no lugar errado.
    """
    return getattr(campo, "valor", None)


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
    from .renda_leitura import conferir_o_par

    if anterior is None:
        return ancora_da_sequencia(atual, carimbo=atual.carimbo)

    # SEM `abs`, SEM `max` E SEM `min`. O sinal e o dado.
    intervalo = atual.carimbo - anterior.carimbo

    # As regras de par sao sobre os NUMEROS e nao sobre o relogio, entao elas
    # rodam sempre que ha um par — inclusive num passo que o tempo ja excluiu.
    # Um par cujo nivel desceu continua sendo um par cujo nivel desceu.
    recusas = conferir_o_par(anterior, atual, fator_de_salto=fator_de_salto)

    sem_delta = _passo_sem_delta(
        anterior,
        atual,
        carimbo=atual.carimbo,
        intervalo=intervalo,
        limiar_de_lacuna_em_segundos=limiar_de_lacuna_em_segundos,
        recusas=recusas,
    )
    if sem_delta is not None:
        return sem_delta

    ganho_de_exp, niveis_ganhos = _exp_do_par(
        anterior.nivel, anterior.exp, atual.nivel, atual.exp
    )
    ganho_de_adena, gasto_de_adena = _adena_do_par(anterior.adena, atual.adena)

    return PassoDaRenda(
        anterior=anterior,
        atual=atual,
        carimbo=atual.carimbo,
        intervalo_em_segundos=intervalo,
        ganho_de_exp_em_decimos=ganho_de_exp,
        niveis_ganhos=niveis_ganhos,
        ganho_de_adena=ganho_de_adena,
        gasto_de_adena=gasto_de_adena,
        descontinuidade=SEM_DESCONTINUIDADE,
        recusas=recusas,
    )


def ancora_da_sequencia(atual, *, carimbo: float) -> PassoDaRenda:
    """A primeira amostra de uma sequencia: passo SEM delta (REG-02, C-7).

    ELA E A GARANTIA INTEIRA DO REG-02 — "reiniciar nao inventa nem apaga
    renda" —, e a garantia mora na CONTA e nao no disco. Reiniciar o scanner
    produz uma sequencia nova cuja primeira amostra nao tem anterior; sem
    anterior nao ha delta; sem delta nao ha numero atravessando o buraco. Nao ha
    peca de persistencia a escrever para isso, e o `ROADMAP.md:39-41` ja tinha
    dito com essas palavras: "REG-02 e uma regra de taxa vestida de
    persistencia".

    E O FONTE ESCREVE TAMBEM ONDE A GARANTIA **NAO** ESTA, porque e la que a
    proxima pessoa vai procurar: no `.mercado/` a nao-duplicacao vem do indice em
    memoria reconstruido do CSV, e essa e exatamente a peca que a C-3 manda NAO
    copiar (la a dedup e regra de negocio; aqui uma linha por tique E o produto,
    porque ela e o denominador da taxa).
    """
    return PassoDaRenda(
        anterior=None,
        atual=atual,
        carimbo=carimbo,
        intervalo_em_segundos=None,
        ganho_de_exp_em_decimos=None,
        niveis_ganhos=None,
        ganho_de_adena=None,
        gasto_de_adena=None,
        descontinuidade=DESCONTINUIDADE_DA_ANCORA,
        recusas=(),
    )


def _passo_sem_delta(
    anterior,
    atual,
    *,
    carimbo: float,
    intervalo: float,
    limiar_de_lacuna_em_segundos: float,
    recusas: tuple,
) -> PassoDaRenda | None:
    """As duas descontinuidades de TEMPO, ou `None` quando o intervalo e bom.

    A ORDEM DAS DUAS PERGUNTAS IMPORTA, e ela e: o relogio andou para tras? o
    intervalo passou do limiar? Perguntar da lacuna antes do salto do relogio
    classificaria um salto para tras de vinte minutos como lacuna, e as duas
    coisas pedem conserto diferente do usuario — uma e o dual boot, a outra e o
    jogo ter sumido da tela.

    O GANHO SAI JUNTO COM O TEMPO nos dois casos, e nao so o tempo. Guardar o
    ganho de uma lacuna e jogar fora o intervalo dela poria, num denominador de
    dez minutos, o numerador de meia hora — que e uma taxa inventada.
    """
    if intervalo < 0:
        descontinuidade = DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS
    elif intervalo > limiar_de_lacuna_em_segundos:
        descontinuidade = DESCONTINUIDADE_DA_LACUNA
    else:
        return None

    return PassoDaRenda(
        anterior=anterior,
        atual=atual,
        carimbo=carimbo,
        intervalo_em_segundos=intervalo,
        ganho_de_exp_em_decimos=None,
        niveis_ganhos=None,
        ganho_de_adena=None,
        gasto_de_adena=None,
        descontinuidade=descontinuidade,
        recusas=recusas,
    )


def passo_entre_campos(
    anterior: CamposDaRenda | None,
    atual: CamposDaRenda,
    *,
    carimbo_anterior: float | None,
    carimbo: float,
    fator_de_salto: int,
    limiar_de_lacuna_em_segundos: float,
) -> PassoDaRenda:
    """O passo quando UM DOS TRES CAMPOS PODE TER RECUSADO (CTX-5, LEIT-11).

    POR QUE ESTA FUNCAO EXISTE, e a razao e estrutural e nao de conveniencia.
    As quatro regras de par exigem `LeituraDaRenda`, que exige os TRES campos
    inteiros. Com o nivel recusado esse objeto NAO EXISTE — entao
    `conferir_o_par` nao pode ser chamada, e a decisao de o que fazer com o par
    mora AQUI, sobre `CamposDaRenda`, e nao dentro daquela composicao.

    E ISSO NAO E CASO RARO: a Fase 1 mediu recusa de **79% no nivel**, 21% na
    adena e 0% no EXP (`02-CONTEXT.md:150`, sobre 14 amostras). Um caminho que
    so soubesse lidar com a amostra completa entregaria taxa em ~4% dos pares.

    O CARIMBO CHEGA POR PARAMETRO porque `CamposDaRenda` NAO TEM CARIMBO: a Fase
    1 carimba `LeituraDaRenda` e nao o objeto de tres campos. E o mesmo desenho
    de `RegistroDaRenda.registrar`, que tambem recebe o carimbo ao lado dos
    campos — e o mesmo motivo pelo qual este modulo nunca le o relogio.

    QUANDO OS TRES CAMPOS ESTAO PRESENTES NOS DOIS LADOS, esta funcao DELEGA a
    `passo_entre`. Nao ha uma segunda aritmetica: a conta do level up, a
    separacao ganho/gasto e a chamada de `conferir_o_par` continuam morando num
    lugar so, e este caminho e apenas quem descobre se aquele lugar pode ser
    usado.

    O QUE SE PERDE NO RAMO INCOMPLETO, E VAI ESCRITO EM VEZ DE ESCONDIDO: sem
    `LeituraDaRenda` nao ha `conferir_o_par`, entao a regra de SALTO DE ORDEM DE
    GRANDEZA DA ADENA nao roda naquele passo. O ganho de adena sai da subtracao
    sem essa rede. A alternativa seria chamar `a_adena_saltou_ordem_de_grandeza`
    solta daqui, e ela esta RECUSADA por dois motivos: o portao invertido de
    `tests/test_renda_par.py` exige que producao chame a COMPOSICAO e nunca uma
    das tres irmas, e uma segunda porta de entrada para as regras seria uma
    segunda politica de recusa divergindo no dia em que uma delas mudar. O
    conserto certo — uma composicao que aceite o par PARCIAL — e trabalho de quem
    for dono de `renda_leitura.py`, e nao deste plano.
    """
    if anterior is None:
        return ancora_da_sequencia(atual, carimbo=carimbo)

    nivel_anterior = _valor_do_campo(anterior.nivel)
    nivel_atual = _valor_do_campo(atual.nivel)
    exp_anterior = _valor_do_campo(anterior.exp)
    exp_atual = _valor_do_campo(atual.exp)
    adena_anterior = _valor_do_campo(anterior.adena)
    adena_atual = _valor_do_campo(atual.adena)

    completos = None not in (
        nivel_anterior,
        nivel_atual,
        exp_anterior,
        exp_atual,
        adena_anterior,
        adena_atual,
    )
    if completos:
        from .renda_leitura import LeituraDaRenda as _Leitura

        return passo_entre(
            _Leitura(
                personagem=anterior.personagem,
                nivel=nivel_anterior,
                exp=exp_anterior,
                adena=adena_anterior,
                carimbo=carimbo_anterior,
            ),
            _Leitura(
                personagem=atual.personagem,
                nivel=nivel_atual,
                exp=exp_atual,
                adena=adena_atual,
                carimbo=carimbo,
            ),
            fator_de_salto=fator_de_salto,
            limiar_de_lacuna_em_segundos=limiar_de_lacuna_em_segundos,
        )

    # SEM `abs`, SEM `max` E SEM `min`. O sinal e o dado, tambem aqui.
    intervalo = carimbo - carimbo_anterior

    sem_delta = _passo_sem_delta(
        anterior,
        atual,
        carimbo=carimbo,
        intervalo=intervalo,
        limiar_de_lacuna_em_segundos=limiar_de_lacuna_em_segundos,
        recusas=(),
    )
    if sem_delta is not None:
        return sem_delta

    ganho_de_exp, niveis_ganhos = _exp_sem_um_dos_lados(
        nivel_anterior, exp_anterior, nivel_atual, exp_atual
    )

    if adena_anterior is None or adena_atual is None:
        ganho_de_adena, gasto_de_adena = None, None
    else:
        ganho_de_adena, gasto_de_adena = _adena_do_par(adena_anterior, adena_atual)

    return PassoDaRenda(
        anterior=anterior,
        atual=atual,
        carimbo=carimbo,
        intervalo_em_segundos=intervalo,
        ganho_de_exp_em_decimos=ganho_de_exp,
        niveis_ganhos=niveis_ganhos,
        ganho_de_adena=ganho_de_adena,
        gasto_de_adena=gasto_de_adena,
        descontinuidade=_marcador_do_campo_ausente(
            nivel_anterior,
            exp_anterior,
            nivel_atual,
            exp_atual,
            adena_anterior,
            adena_atual,
        ),
        # TUPLA VAZIA, e ela NAO quer dizer "o par foi conferido e esta bom":
        # quer dizer que nao havia par a conferir. Quem distingue os dois e a
        # `descontinuidade`, que neste caminho sai sempre preenchida.
        recusas=(),
    )


def _exp_sem_um_dos_lados(
    nivel_anterior: int | None,
    exp_anterior: int | None,
    nivel_atual: int | None,
    exp_atual: int | None,
) -> tuple[int | None, int | None]:
    """O ganho de EXP quando o NIVEL pode nao ter sido lido. As duas decisoes.

    **EXP AUSENTE: nao ha ganho a computar**, e nao ha o que decidir.

    **EXP CAINDO COM O NIVEL AUSENTE: nao se computa ganho.** A tentacao e
    chamar de level up, e e exatamente ai que a alternativa registrada da CTX-5
    erra: MORRER tambem derruba o EXP muito. E o nivel e o campo em que "parece
    certo" prova menos — o LEIT-11 mediu que 3 das 4 leituras erradas de nivel
    foram aceitas POR CONCORDANCIA das duas escalas de OCR.

    **EXP QUE NAO CAIU COM O NIVEL AUSENTE: computa-se o ganho NORMALMENTE.** Um
    level up faz o EXP CAIR; com o EXP subindo (ou parado) nao existe level up a
    supor, entao a guarda nao protegeria de nada — ela so cobraria. E o limiar de
    lacuna fecha o argumento com numero, e a dependencia vai escrita: o intervalo
    de um passo aceito e no maximo `lacuna_maxima_segundos`, e a ~104 abates por
    minuto com 0,001011 ponto percentual por abate (REND-08) a barra anda ~0,1
    ponto percentual em sessenta segundos, contra os ~100 que um level up
    exigiria. QUEM LEVANTAR `lacuna_maxima_segundos` PARA HORAS REABRE ESTE CASO.

    O EXP EXATAMENTE IGUAL NAS DUAS PONTAS cai no ramo do "nao caiu", e o ganho
    dele e ZERO — que e uma medicao legitima e nao uma ausencia. Excluir o passo
    ali o tiraria do denominador e INFLARIA a taxa, que e o erro oposto e igual.

    `niveis_ganhos` SAI `None` SEMPRE QUE UM DOS LADOS NAO TROUXE O NIVEL: um
    zero ali seria a afirmacao "nao houve level up" feita por quem nao leu o
    nivel, e esta fase inteira existe para nao fazer esse tipo de afirmacao.
    """
    if exp_anterior is None or exp_atual is None:
        return None, None
    if nivel_anterior is None or nivel_atual is None:
        if exp_atual < exp_anterior:
            return None, None
        return exp_atual - exp_anterior, None
    return _exp_do_par(nivel_anterior, exp_anterior, nivel_atual, exp_atual)


def _marcador_do_campo_ausente(
    nivel_anterior: int | None,
    exp_anterior: int | None,
    nivel_atual: int | None,
    exp_atual: int | None,
    adena_anterior: int | None,
    adena_atual: int | None,
) -> str:
    """UM marcador por passo, escolhido por prioridade. E a prioridade e escrita.

    A `descontinuidade` e UMA palavra porque ela vira UMA coluna do CSV, e a
    recusa de LEITURA de cada campo ja viaja na coluna PROPRIA dele
    (`motivo_do_nivel`, `motivo_do_exp`, `motivo_da_adena`, do `02-01`). O que
    este marcador diz e o fato de PAR — e por isso ele pode ser um so sem perder
    informacao: a verdade campo a campo esta ao lado, no mesmo registro.

    A ORDEM E: nivel (porque e a decisao da CTX-5, e a que carrega o SENTIDO do
    EXP junto), depois EXP, depois adena. Quando o EXP tambem falta, o marcador
    do EXP ganha do marcador do nivel — sem o EXP nao ha sentido a nomear, e
    `nivel-indisponivel-com-exp-...` mentiria sobre uma direcao que ninguem leu.
    """
    if nivel_anterior is None or nivel_atual is None:
        if exp_anterior is not None and exp_atual is not None:
            if exp_atual < exp_anterior:
                return DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_CAINDO
            return DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_SUBINDO
    if exp_anterior is None or exp_atual is None:
        return DESCONTINUIDADE_DO_EXP_INDISPONIVEL
    return DESCONTINUIDADE_DA_ADENA_INDISPONIVEL


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

    `por_minuto` E `por_hora / 60` E VIAJA JUNTO, e nao e conveniencia: as duas
    respondem a mesma pergunta em escalas que o usuario usa em momentos
    diferentes — "quanto rende esta noite" e por hora, "quanto rendeu este mob"
    e por minuto. Deixar a divisao para quem exibe convidaria um `float` a
    entrar na conta bem no fim, depois de toda a disciplina de `Fraction`.

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
    por_minuto: Fraction | None
    motivo_da_ausencia: str | None
    janela_farmada_em_segundos: float
    unidade_da_janela: str
    lacunas_excluidas: int
    segundos_em_lacuna: float
    ate: float | None


def ganho_do_passo(passo: PassoDaRenda, grandeza: str) -> int | None:
    """O ganho daquele passo NAQUELA grandeza, ou `None` se ele nao a mediu.

    `None` E O DADO E NAO A AUSENCIA DE DADO: ele e como o passo diz "esta eu
    nao medi" — porque o campo recusou, porque o EXP caiu sem nivel, ou porque
    o tempo daquele passo nao existiu. Um zero no lugar entraria no numerador
    como se fosse medicao, e uma noite de recusas viraria uma taxa de zero em
    vez de uma taxa com `n` pequeno e o motivo escrito ao lado.
    """
    if grandeza == GRANDEZA_DO_EXP:
        return passo.ganho_de_exp_em_decimos
    if grandeza == GRANDEZA_DA_ADENA:
        return passo.ganho_de_adena
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
    # O CRITERIO E `aceito_para` E NAO `aceito`, e a diferenca e o requisito:
    # o denominador e POR GRANDEZA. Um passo em que o nivel recusou e o EXP caiu
    # sai do denominador do EXP e CONTINUA no da adena — com o nivel recusado em
    # 79% dos tiques, o criterio grosso faria o campo mais fragil dos tres
    # derrubar os outros dois quase sempre.
    aceitos = [passo for passo in passos if passo.aceito_para(grandeza)]
    lacunas = [
        passo
        for passo in passos
        if passo.descontinuidade == DESCONTINUIDADE_DA_LACUNA
    ]

    janela_farmada = 0.0
    for passo in aceitos:
        janela_farmada = janela_farmada + passo.intervalo_em_segundos

    segundos_em_lacuna = 0.0
    for passo in lacunas:
        segundos_em_lacuna = segundos_em_lacuna + passo.intervalo_em_segundos

    evidencia = Evidencia(n=len(aceitos), piso=int(piso_de_amostras))

    # A RECENCIA SAI DO ULTIMO PASSO DA SEQUENCIA ORDENADA, e nunca de um `max`
    # sobre os carimbos: `max` absorveria uma sequencia fora de ordem em silencio,
    # devolvendo um `ate` que nao corresponde a nenhum passo que entrou na conta.
    # E ela e o carimbo do passo, e nao `atual.carimbo`, porque `CamposDaRenda`
    # nao tem carimbo — a recencia nao pode depender de qual caminho produziu o
    # passo.
    ate = aceitos[-1].carimbo if aceitos else None

    def _sem_numero(motivo: str) -> TaxaDaRenda:
        return TaxaDaRenda(
            grandeza=grandeza,
            evidencia=evidencia,
            por_hora=None,
            por_minuto=None,
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

    if janela_farmada < piso_da_janela_em_segundos:
        return _sem_numero(
            f"janela abaixo do piso: {janela_farmada:.1f} segundos de "
            f"{UNIDADE_DA_JANELA} e o piso "
            f"'janela_minima_para_taxa_segundos' e "
            f"{piso_da_janela_em_segundos:.1f}."
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
        ganho = ganho + ganho_do_passo(passo, grandeza)

    por_hora = Fraction(ganho) * SEGUNDOS_POR_HORA / Fraction(janela_farmada)

    return TaxaDaRenda(
        grandeza=grandeza,
        evidencia=evidencia,
        por_hora=por_hora,
        por_minuto=por_hora / MINUTOS_POR_HORA,
        motivo_da_ausencia=None,
        janela_farmada_em_segundos=janela_farmada,
        unidade_da_janela=UNIDADE_DA_JANELA,
        lacunas_excluidas=len(lacunas),
        segundos_em_lacuna=segundos_em_lacuna,
        ate=ate,
    )


# ---------------------------------------------------------------------------
# A JANELA MOVEL, E ELA E POR TEMPO (CTX-1)
# ---------------------------------------------------------------------------


def passos_da_janela(
    passos: Sequence[PassoDaRenda], *, janela_em_segundos: float
) -> tuple[PassoDaRenda, ...]:
    """Os passos dentro da janela, contada A PARTIR DO MAIS RECENTE PARA TRAS.

    A JANELA E POR TEMPO E NAO POR CONTAGEM, e a alternativa vai registrada aqui
    porque ela e o PADRAO SILENCIOSO — alguem a implementa sem perceber.
    "Ultimos dez minutos" e o que o usuario entende; "ultimas quarenta amostras"
    muda de significado toda vez que a cadencia muda, e a Fase 3 tem cadencia
    variavel POR NATUREZA: o OCR custa dezenas de milissegundos e o jogo as vezes
    some da tela. Uma janela por contagem encolheria em segundos exatamente
    quando o scanner esta com dificuldade — que e quando o usuario mais precisa
    do numero estar certo.

    O CORTE E `>` E NAO `>=`: um passo cujo carimbo cai EXATAMENTE no limite da
    janela pertence ao instante anterior a ela. Com a janela igual ao vao inteiro
    da sequencia isso deixa a ancora de fora, que e o desfecho certo — ela nao
    tem intervalo e nao entraria em denominador nenhum de qualquer jeito.

    A SEQUENCIA E ASSUMIDA CRONOLOGICA, que e como o laco de captura a produz.
    Ordenar aqui esconderia um relogio embaralhado — e o relogio embaralhado tem
    nome proprio nesta fase (`relogio-andou-para-tras`) e nao pode ser corrigido
    em silencio.
    """
    if not passos:
        return ()
    limite = passos[-1].carimbo - janela_em_segundos
    return tuple(passo for passo in passos if passo.carimbo > limite)


@dataclass(frozen=True)
class AsDuasTaxas:
    """A da JANELA MOVEL e a da SESSAO INTEIRA, e as duas saem juntas (CTX-4).

    ELAS RESPONDEM PERGUNTAS DIFERENTES: a janela responde "o que esta
    acontecendo agora" e a sessao responde "o que a noite rendeu". Apresentar so
    uma MENTE POR OMISSAO, e o tamanho da mentira esta medido: a media de 8h45
    deu ~226 mil adena/h e a janela curta deu 466 mil/h — um fator de dois, e a
    diferenca inteira e TEMPO PARADO.

    As duas carregam a propria `Evidencia`, a propria janela farmada e a propria
    recencia, porque sao duas medicoes e nao duas vistas da mesma.
    """

    janela: TaxaDaRenda
    sessao: TaxaDaRenda


def as_duas_taxas(
    passos: Sequence[PassoDaRenda],
    *,
    grandeza: str,
    janela_em_segundos: float,
    piso_de_amostras: int,
    piso_da_janela_em_segundos: float,
) -> AsDuasTaxas:
    """As duas taxas da mesma sequencia, com janelas diferentes.

    A DA SESSAO E A SEQUENCIA INTEIRA e nao "desde que o processo subiu": a
    sessao e delimitada por LACUNA e nunca por processo (herdado do `02-01`), e e
    quem monta a sequencia que decide onde ela comeca. Este modulo nao sabe o que
    e um processo, e nao deve saber.

    `janela_em_segundos` NAO TEM VALOR DE FABRICA, pela mesma regra dos outros
    limiares: ele e `janela_movel_minutos` da secao `[renda]` do `config.toml`,
    convertido a segundos por quem le o arquivo. O `02-01` deixou aquela chave
    lida e validada e SEM CONSUMIDOR, com "AINDA NAO FAZ NADA" escrito ao lado —
    este e o consumidor.
    """
    return AsDuasTaxas(
        janela=taxa_por_hora(
            passos_da_janela(passos, janela_em_segundos=janela_em_segundos),
            grandeza=grandeza,
            piso_de_amostras=piso_de_amostras,
            piso_da_janela_em_segundos=piso_da_janela_em_segundos,
        ),
        sessao=taxa_por_hora(
            passos,
            grandeza=grandeza,
            piso_de_amostras=piso_de_amostras,
            piso_da_janela_em_segundos=piso_da_janela_em_segundos,
        ),
    )
