"""O DESENHO do modo `--renda`: a linha do tique e o resumo da sessao.

ELAS DEVOLVEM TEXTO E NUNCA IMPRIMEM
=====================================
O molde e `mercado_console.py:1-10`, palavra por palavra: quem imprime e o
laco, com `log.info`, e assim a MESMA string vai para o console E para o
`scanner.log` rotativo — que e onde a forense de uma noite de farm mora. Um
`print` aqui entregaria a linha ao console e a esconderia do arquivo,
exatamente no caso em que ela importa.

AS TRES COISAS QUE ESTA TELA NAO E, E AS TRES SAO A TENTACAO
=============================================================
1. **Nao e `rich`.** `rich` NAO esta instalado nesta arvore
   (`ModuleNotFoundError`), tem zero importacoes em `l2scanner/` e nao entra
   nesta fase (CTX-1). O `ROADMAP.md` e o `CLAUDE.md` que citam `rich.Live`
   como se ele ja fosse a convencao desta casa estao VELHOS, e o criterio 1 da
   fase sobrevive inteiro sem ele.

2. **Nao e painel repintado.** Nao ha `\\r`, nao ha clear e nao ha `print` em
   caminho de tela nesta arvore inteira (C-1). O laco faz `log.info` e a linha
   ROLA. "Atualizando ao vivo" nesta casa e **uma linha nova por tique**, e nao
   um retangulo que pisca.

3. **Nao e uma linha densa com tudo.** MEDIDO (CTX-2), com os valores reais do
   usuario: `nivel 67 | EXP 79,2568% | adena 17.592.060 | 2,41 M XP/h | 466 mil
   adena/h | falta 3h20` mede **87 colunas** e foi REFUTADA. A largura real de
   console que este fonte cita com razao ao lado e **76**
   (`LARGURA_DO_AVISO`, `mercado_console.py:748`); `console.LARGURA = 58` so
   aparece dentro de `moldurar` como `max(LARGURA, ...)`, que e **PISO** e
   nunca teto (C-2, `console.py:110`).

LOGO A TELA E DUAS COISAS, E A DIVISAO E A DO `D-02`
=====================================================
- **Uma linha por tique** com o que a tela do jogo **AFIRMA** — nivel, EXP,
  adena — mais o estado. Ela mede 58 a 72 colunas com os valores reais.
- **Um bloco por intervalo** com o que o programa **CALCULOU** — as taxas com
  `n` e recencia, o ETA, a duracao da sessao. Derivacao carrega `n`, e `n` nao
  cabe numa linha.
"""

from __future__ import annotations

import textwrap
from datetime import datetime

from . import console
from .mercado_console import LARGURA_DO_AVISO
from .renda_conta import (
    MOTIVO_DA_TAXA_DE_EXP_NEGATIVA,
    MOTIVO_DA_TAXA_DE_EXP_ZERADA,
)
from .renda_leitura import (
    CAMPO_DA_ADENA,
    CAMPO_DO_EXP,
    CAMPO_DO_NIVEL,
    RecusaDaRenda,
)

# ---------------------------------------------------------------------------
# A GRAFIA DOS TRES NUMEROS -- e ela mora AQUI e nao em `renda_modo.py`
# ---------------------------------------------------------------------------
#
# ELAS NASCERAM NO `01-04`, DENTRO DE `renda_modo.py`, E MUDARAM DE CASA AQUI.
# O motivo e MEDIDO e nao estetico: `import l2scanner.renda_modo` custa 0,974 s
# e traz 344 modulos, `cv2` incluido, porque aquele modulo e a FERRAMENTA de
# linha de comando (ele importa `argparse` e `cv2` no topo). O laco da renda e
# o console dele nao podem pagar um `cv2` e um `argparse` para escrever
# `17.592.060` — medido no mesmo processo, `renda_conta` + `console` custam
# 0,198 s e 279 modulos.
#
# E DUAS GRAFIAS DO MESMO NUMERO SERIA PIOR QUE O IMPORT CARO. O criterio 1 da
# Fase 1 e uma COMPARACAO entre o terminal e o monitor; se a ferramenta
# escrevesse `13.160.684` e o laco `13160684`, a comparacao deixaria de
# funcionar exatamente na tela que roda a noite inteira. Entao ha UMA verdade,
# num lugar so, e `renda_modo.py` importa daqui.


def _grafia_do_exp(valor: int) -> str:
    """`80012` -> `8,0012%`, na grafia que o olho compara com o monitor.

    A grafia mora na BORDA e o inteiro mora no modulo puro, e a divisao nao e
    arbitraria: o inteiro e o que a Fase 2 consome, e uma string formatada
    atravessando a fronteira obrigaria quem consome a fazer o caminho de volta.
    """
    pontos, decimos = divmod(int(valor), 10_000)
    return f"{pontos},{decimos:04d}%"


def _grafia_da_adena(valor: int) -> str:
    """`13160684` -> `13.160.684`, com o separador de milhar que o JOGO escreve.

    O PONTO E O SEPARADOR DA TELA, e a virgula e o do OCR e dos glifos. Medido
    (M21): `numero_valido("10.673.628")` e `False` — as funcoes do mercado
    falam VIRGULA. Aqui a conversao vai no sentido contrario, do inteiro para a
    tela, e ela e o que faz o criterio 1 ser conferivel: o usuario le
    `13.160.684` no monitor e `13.160.684` no terminal, sem traduzir nada.

    A separacao vem de `format`, e nao de uma aritmetica escrita a mao: um laco
    de milhar aqui seria uma segunda gramatica de milhar nesta arvore.
    """
    return f"{int(valor):,}".replace(",", ".")


def _grafia_do_nivel(valor: int) -> str:
    """`67` -> `67`. Inteiro NU, porque e assim que a tela do jogo o escreve."""
    return str(int(valor))


GRAFIA_POR_CAMPO = {
    CAMPO_DO_NIVEL: _grafia_do_nivel,
    CAMPO_DO_EXP: _grafia_do_exp,
    CAMPO_DA_ADENA: _grafia_da_adena,
}


# ---------------------------------------------------------------------------
# A LINHA DO TIQUE
# ---------------------------------------------------------------------------

# O prefixo que deixa a linha da renda reconhecivel no `scanner.log` rotativo,
# onde ela divide o arquivo com as linhas da party e as do mercado. O molde e
# `mercado_console.linha_ao_vivo`, que abre com `mercado | `.
PREFIXO_DA_LINHA = "renda"

SEPARADOR_DA_LINHA = " | "

# O que um campo RECUSADO mostra. Nunca espaco vazio, que parece defeito de
# formatacao, e NUNCA zero: zero e uma afirmacao sobre o jogo ("voce tem zero
# adena"), e recusa e uma afirmacao sobre a MEDICAO ("nao consegui ler").
SEM_LEITURA = "--"

ESTADO_LENDO = "LENDO"

# O ORCAMENTO DE LARGURA DA LINHA DO TIQUE, e ele e MEDICAO e nao escolha.
#
# 76 e a largura de console que este fonte cita com razao ao lado
# (`LARGURA_DO_AVISO`, `mercado_console.py:748`: "a largura em que ela cabe num
# console padrao de 80"). 72 e o teto da banda medida no planejamento desta
# fase com os valores reais do usuario (`03-CONTEXT.md:142-143`):
#
#   renda | nivel 67 | EXP 79,2568% | adena 17.592.060 | LENDO            58
#   renda | nivel -- | EXP 79,2568% | adena 17.592.060 | nivel: campo-... 71
#   renda | nivel -- | EXP -- | adena -- | nivel, EXP, adena: campo-vazio 69
#
# ELE NAO E `console.LARGURA`. Aquele e 58 e e PISO de `moldurar`; a linha ao
# vivo nunca passou por `moldurar`, nao trunca e nao quebra — a do mercado ja
# roda 84 colunas normalmente e 255 com o aviso de layout colado (C-2).
LARGURA_MAXIMA_DA_LINHA_DO_TIQUE = 72

# O que fica no lugar do que foi cortado. Uma truncagem invisivel transformaria
# `discordancia-entre-escalas` em `discordanci`, que parece um motivo inteiro e
# nao existe em lugar nenhum do fonte.
MARCA_DE_TRUNCAGEM = "~"

# OS ROTULOS DA LINHA AO VIVO SAO OUTROS QUE OS DA TABELA DE `renda_modo`.
# La `ROTULO_DO_CAMPO[CAMPO_DO_EXP]` e `"EXP  "`, com dois espacos, porque
# aquilo e uma TABELA de tres linhas alinhadas em coluna. Aqui e uma linha so,
# separada por `|`, e o espaco de alinhamento viraria buraco no meio do texto.
# Dois usos diferentes, dois dicionarios — e nao um com `.strip()` espalhado.
ROTULO_NA_LINHA = {
    CAMPO_DO_NIVEL: "nivel",
    CAMPO_DO_EXP: "EXP",
    CAMPO_DA_ADENA: "adena",
}


def _encurtar(texto: str, largura: int) -> str:
    """Corta pelo fim e MARCA o corte. Nunca corta em silencio."""
    if largura <= 0:
        return ""
    if len(texto) <= largura:
        return texto
    return texto[: largura - len(MARCA_DE_TRUNCAGEM)] + MARCA_DE_TRUNCAGEM


def _celula(resultado) -> str:
    """O numero na grafia do jogo, OU `--` quando o campo recusou."""
    if isinstance(resultado, RecusaDaRenda):
        return SEM_LEITURA
    return GRAFIA_POR_CAMPO[resultado.campo](resultado.valor)


def estado_da_leitura(campos) -> str:
    """`LENDO`, ou os campos que recusaram COM o motivo deles.

    O MOTIVO VAI NA LINHA E NAO SO NO CSV. Sem ele o usuario ve `--` a noite
    inteira sem nenhuma pista do conserto — e `campo-vazio` (recalibre o
    retangulo) e `discordancia-entre-escalas` (o OCR leu duas coisas) pedem
    consertos OPOSTOS.

    OS MOTIVOS SAO DEDUPLICADOS PRESERVANDO A ORDEM porque o caso majoritario e
    tres campos com o mesmo motivo: `nivel, EXP, adena: campo-vazio` custa 30
    colunas e `nivel: campo-vazio, EXP: campo-vazio, ...` custaria 56.
    """
    recusados = [
        (campo, resultado)
        for campo, resultado in campos.por_campo.items()
        if isinstance(resultado, RecusaDaRenda)
    ]
    if not recusados:
        return ESTADO_LENDO

    nomes = ", ".join(ROTULO_NA_LINHA[campo] for campo, _ in recusados)
    motivos = ", ".join(
        dict.fromkeys(resultado.motivo for _, resultado in recusados)
    )
    return f"{nomes}: {motivos}"


def linha_do_tique(campos, contagem, *, estado: str | None = None) -> str:
    """A linha de UM tique: o que a tela do jogo AFIRMA, mais o estado.

    ELA SAI TODO TIQUE, e nao atras de um portao. O mercado esconde a linha
    dele quando o painel do World Exchange esta fechado, porque painel fechado
    e o estado majoritario de um farm real; a barra de EXP esta **sempre** na
    tela, entao aqui nao ha analogo daquele latch.

    `estado` E O SEAM DO `03-02` E AINDA NAO FAZ NADA EM PRODUCAO. Quem passar
    um texto aqui substitui o estado calculado — e assim a cegueira
    (`PAUSADO: JOGO CAIU`) e o parado (`PARADO ha 4min12`) entram sem mexer na
    assinatura. Ele nasce agora pelo precedente literal das cinco chaves que o
    `02-01` deixou lidas e sem consumidor.

    `contagem` VIAJA E AINDA NAO ENTRA NA LINHA, pela mesma disciplina e pelo
    mesmo motivo medido: a linha limpa ja mede 58 colunas e o orcamento e 72,
    entao um `n=142` colado aqui estouraria o teto no tique com recusa — que e
    o tique MAJORITARIO (79% de recusa no nivel, medido na Fase 1). O `n` mora
    no bloco por intervalo, colado na taxa que ele sustenta, que e onde o
    CONS-01 o pede.
    """
    partes = [PREFIXO_DA_LINHA]
    for campo, resultado in campos.por_campo.items():
        partes.append(f"{ROTULO_NA_LINHA[campo]} {_celula(resultado)}")

    prefixo = SEPARADOR_DA_LINHA.join(partes)
    texto = estado_da_leitura(campos) if estado is None else estado

    folga = (
        LARGURA_MAXIMA_DA_LINHA_DO_TIQUE
        - len(prefixo)
        - len(SEPARADOR_DA_LINHA)
    )
    return prefixo + SEPARADOR_DA_LINHA + _encurtar(texto, folga)


# ---------------------------------------------------------------------------
# O BLOCO POR INTERVALO -- o que o programa CALCULOU (CONS-01)
# ---------------------------------------------------------------------------

# A largura da coluna de rotulos dos blocos, copiada de `resumo_da_sessao`
# (`mercado_console.py:694`): trinta e dois alinha os numeros numa coluna so
# sem empurrar nenhum rotulo desta fase para a linha seguinte.
COLUNA_DO_ROTULO = 32

# A largura do bloco e IMPORTADA e nao recopiada. `LARGURA_DO_AVISO = 76`
# (`mercado_console.py:748`) diz por escrito *"a largura em que ela cabe num
# console padrao de 80"*, e e o unico numero de largura de console que este
# fonte cita com razao ao lado. Dois setenta-e-seis seriam dois numeros para
# divergir no dia em que alguem mexesse num deles.
LARGURA_DO_BLOCO = LARGURA_DO_AVISO

# O recuo das linhas de continuacao de um motivo dobrado. Ele e MAIOR que o das
# linhas normais para que a continuacao seja visivelmente subordinada ao rotulo
# que a gerou, e nao pareca um item novo da lista.
RECUO_DA_CONTINUACAO = 6

# Os tres textos de ausencia do ETA, e sao TRES porque o CONSERTO DO USUARIO e
# diferente em cada um — a razao ja escrita em `renda_conta.py:1128-1139`:
#
#   taxa zerada    -> "voce nao esta ganhando EXP" ... va farmar
#   taxa negativa  -> "voce esta PERDENDO EXP" ...... pare de morrer
#   sem evidencia  -> "ainda nao da para dizer" ..... espere mais um pouco
#
# Fundir dois deles faria dois consertos diferentes virarem a mesma mensagem.
TEXTO_DA_TAXA_ZERADA = (
    "sem previsao: voce nao esta ganhando EXP. Va farmar."
)
TEXTO_DA_TAXA_NEGATIVA = (
    "sem previsao: voce esta PERDENDO EXP. Pare de morrer."
)
TEXTO_SEM_EVIDENCIA = "sem previsao: ainda nao da para dizer."


def duracao_curta(segundos: float) -> str:
    """`17520.696` -> `4h52`. Inteiro, e a partir de EPOCHS SUBTRAIDOS.

    ELA NASCEU PRIVADA NO `03-01` E FICOU PUBLICA NO `03-02`, e a razao e uma
    so: `renda_estado.texto_do_parado` escreve `PARADO ha 4min` na MESMA tela
    em que este arquivo escreve `ha 4min` na recencia da taxa. Duas gramaticas
    de duracao lado a lado fariam a mesma grandeza aparecer escrita de dois
    jeitos -- e a alternativa (copiar as seis linhas para o modulo puro) e
    exatamente a segunda verdade que a mudanca de casa das tres grafias, no
    `03-01`, existiu para impedir.

    O `int()` NA ENTRADA E O PONTO. `dashboard_dados.py:624-628` mediu
    `total_seconds()` devolvendo `69713.696` onde o inteiro dizia `69713`; um
    `timedelta` no meio deste caminho traz aquele erro de volta, e a casa
    decimal pendurada aparece na tela como `4h52.0`. A aritmetica desta fase e
    subtracao de epochs, que e exata.
    """
    segundos = int(abs(segundos))
    horas, resto = divmod(segundos, 3600)
    minutos, sobra = divmod(resto, 60)
    if horas:
        return f"{horas}h{minutos:02d}"
    if minutos:
        return f"{minutos}min"
    return f"{sobra}s"


def _grafia_curta(valor) -> str:
    """`2410000` -> `2,41 M`; `466000` -> `466 mil`.

    A CONVERSAO DE `Fraction` PARA TEXTO ACONTECE SO AQUI, NA BORDA. A
    disciplina de `Fraction` que a Fase 2 imps existe para que a diferenca
    entre duas leituras nao acumule erro de ponto flutuante; desfaze-la um
    passo antes do fim, por um `float` de conveniencia, jogaria fora a conta
    inteira. Entao a reducao de escala e feita em inteiros.

    ELA TRUNCA E NAO ARREDONDA, e a direcao e deliberada: truncar nunca
    SUPERESTIMA a renda. Um numero que o usuario usa para decidir se continua
    farmando erra para o lado seguro.

    A VIRGULA DECIMAL E A QUE O JOGO USA e a que o resto deste repositorio
    escreve.
    """
    negativo = valor < 0
    n = -valor if negativo else valor

    if n >= 1_000_000_000:
        escala, unidade, casas = 1_000_000_000, " bi", 2
    elif n >= 1_000_000:
        escala, unidade, casas = 1_000_000, " M", 2
    elif n >= 1_000:
        escala, unidade, casas = 1_000, " mil", 0
    else:
        escala, unidade, casas = 1, "", 0

    if casas:
        centesimos = int(n * 100 / escala)
        inteiro, resto = divmod(centesimos, 100)
        texto = f"{inteiro},{resto:02d}"
    else:
        texto = str(int(n / escala))

    return ("-" if negativo else "") + texto + unidade


def _grafia_da_porcentagem(parte: int, total: int) -> str:
    """`79/100` -> `79%`; `1/1000` -> `0,1%`. Nunca `0%` sobre parte > 0.

    ARREDONDAR UMA RECUSA RARA PARA ZERO APAGARIA A UNICA EVIDENCIA de que o
    campo chegou a falhar. `0%` e uma AFIRMACAO ("este campo nunca recusou") e
    tem de continuar significando isso.
    """
    if total <= 0:
        return "0%"
    porcentagem = 100.0 * parte / total
    if porcentagem == int(porcentagem):
        return f"{int(porcentagem)}%"
    if parte > 0 and round(porcentagem, 1) == 0.0:
        return "<0,1%"
    return f"{porcentagem:.1f}%".replace(".", ",")


def _linha(rotulo: str, valor: str) -> str:
    return f"  {rotulo:<{COLUNA_DO_ROTULO}} {valor}"


def _dobrar(texto: str) -> list[str]:
    """O motivo INTEIRO, em linhas de continuacao. Nunca truncado.

    O motivo de `taxa_por_hora` nomeia QUAL piso faltou e quantas amostras
    faltam — `"amostras abaixo do piso: 3 passo(s) aceito(s) e o piso
    'amostras_minimas_para_taxa' e 8. Faltam 5."`, uns 95 caracteres. Cortar
    esse texto ao meio tiraria dele exatamente a parte que ensina o conserto.
    Aqui ele dobra; na LINHA DO TIQUE, onde nao ha continuacao possivel, ele
    trunca com marca — e sao dois lugares com restricoes diferentes.
    """
    recuo = " " * RECUO_DA_CONTINUACAO
    return [
        f"{recuo}{pedaco}"
        for pedaco in textwrap.wrap(
            texto, width=LARGURA_DO_BLOCO - RECUO_DA_CONTINUACAO
        )
    ]


def _linhas_de_uma_taxa(rotulo_base: str, sufixo: str, taxa, agora) -> list[str]:
    """Uma taxa: o numero COM `n` e recencia colados, ou o motivo DELA.

    `n` E RECENCIA VAO COLADOS NO NUMERO E NUNCA EM RODAPE. E o que o CONS-01
    pede com todas as letras — *"com `n` e recencia colados nos numeros como o
    `--mercado` ja faz"* —, e a razao esta na docstring de `TaxaDaRenda`: um
    numero bom de quarenta minutos atras continua bom; ele so nao e o de agora,
    e quem le precisa poder dizer as duas coisas.

    UMA TAXA SEM NUMERO SAI COMO O MOTIVO DELA, e nunca como `0` nem como `--`.
    Zero seria uma afirmacao sobre o FARM ("voce nao ganhou nada"); ausencia e
    uma afirmacao sobre a MEDICAO ("ainda nao da para dizer"), e os dois pedem
    reacoes opostas do usuario.
    """
    rotulo = f"{rotulo_base} {sufixo}"
    if taxa.por_hora is None:
        return [_linha(rotulo, "").rstrip()] + _dobrar(
            f"sem numero: {taxa.motivo_da_ausencia}"
        )

    recencia = "agora" if taxa.ate is None else f"ha {duracao_curta(agora - taxa.ate)}"
    numero = _grafia_curta(taxa.por_hora)
    return [_linha(rotulo, f"{numero:<9} (n={taxa.evidencia.n}, {recencia})")]


def _sufixo_da_janela(taxa) -> str:
    return f"janela ({duracao_curta(taxa.janela_farmada_em_segundos)})"


def _sufixo_da_sessao(taxa) -> str:
    return (
        f"sessao ({duracao_curta(taxa.janela_farmada_em_segundos)} farmadas)"
    )


def _linhas_do_eta(eta, campos, agora) -> list[str]:
    """`falta 3h20`, ou UM DOS TRES motivos — e os tres tem textos diferentes."""
    alvo = campos.nivel
    rotulo = (
        f"falta para o nivel {int(alvo.valor) + 1}"
        if not isinstance(alvo, RecusaDaRenda)
        else "falta para o proximo nivel"
    )

    if eta.segundos is not None:
        return [_linha(rotulo, duracao_curta(float(eta.segundos)))]

    motivo = eta.motivo_da_ausencia or ""
    if motivo == MOTIVO_DA_TAXA_DE_EXP_ZERADA:
        return [_linha(rotulo, TEXTO_DA_TAXA_ZERADA)]
    if motivo == MOTIVO_DA_TAXA_DE_EXP_NEGATIVA:
        return [_linha(rotulo, TEXTO_DA_TAXA_NEGATIVA)]
    # O TERCEIRO CASO HERDA O MOTIVO DA TAXA em vez de escrever um novo: a
    # previsao NAO PODE SER MAIS CONFIANTE QUE O NUMERO DE QUE ELA SAI, e dois
    # textos para a mesma causa divergiriam no dia em que um deles mudasse.
    return [_linha(rotulo, TEXTO_SEM_EVIDENCIA)] + _dobrar(motivo)


def bloco_da_renda(
    campos,
    taxas_de_exp,
    taxas_de_adena,
    eta,
    contagem,
    *,
    desde: float,
    agora: float,
    recusas_por_campo: dict,
    tiques: int,
) -> str:
    """O que o programa CALCULOU, por INTERVALO e nunca por tique.

    A CADENCIA E `--status-a-cada` E A RAZAO ESTA ESCRITA em
    `mercado_console.py:490-496`: *"Repintar um bloco de dezenas de linhas por
    segundo afogaria a linha ao vivo"*. A linha do tique responde "o modo esta
    vivo?"; este bloco responde "quanto isso rende?", e a segunda resposta so
    muda quando a sequencia ganha amostras.

    `recusas_por_campo` E `tiques` ENTRAM POR PARAMETRO, E ISSO E UMA CORRECAO
    MEDIDA DO PLANO. Ele mandava tirar as taxas de recusa por campo de
    `contagem.recusadas_por_motivo` — e elas NAO estao la. Aquele dicionario e
    somado em `contar_o_passo` a partir de `passo.recusas`, que e *"A TUPLA QUE
    `conferir_o_par` DEVOLVEU"* (`renda_conta.py:342-347`): sao as recusas das
    REGRAS DE PAR, e a propria docstring diz que ela *"sai vazia no caminho de
    `CamposDaRenda` com um campo recusado"*. Ou seja: os 79% do nivel, 21% da
    adena e 0% do EXP medidos na Fase 1 nao passam por ali em nenhum tique.
    Eles vem de `CamposDaRenda.por_campo`, e quem os conta e o laco.

    `contagem` viaja para os dois numeros que SAO dela — passos aceitos e
    lacunas — e para o `03-03`, que acrescenta o piso usado.
    """
    hora = datetime.fromtimestamp(agora).strftime("%H:%M")
    linhas = [
        console.moldurar(f"RENDA - {campos.personagem}", hora),
        "",
        "O QUE A TELA AFIRMA:",
    ]
    for campo, resultado in campos.por_campo.items():
        rotulo = ROTULO_NA_LINHA[campo]
        if isinstance(resultado, RecusaDaRenda):
            linhas.append(
                _linha(rotulo, f"{SEM_LEITURA} ({resultado.motivo})")
            )
        else:
            linhas.append(
                _linha(rotulo, GRAFIA_POR_CAMPO[campo](resultado.valor))
            )

    # OS DOIS TEMPOS, E ELES SAO DOIS E NUNCA UM.
    #
    # `de pe` e o que o criterio 1 do `ROADMAP.md` pede — "ha quanto tempo a
    # sessao corre" — e conta do arranque ao agora. `farmadas` e o DENOMINADOR
    # da taxa, com as lacunas ja subtraidas (`unidade_da_janela` diz "minutos
    # farmados", e nao "minutos de relogio"). Numa noite com 40 minutos cegos
    # eles divergem em 40 minutos, e mostrar so o farmado responde uma pergunta
    # que o usuario nao fez enquanto cala a que ele fez.
    #
    # NUMA SESSAO SEM LACUNA OS DOIS SAO IGUAIS, E SAEM ASSIM MESMO: a
    # igualdade e um fato sobre a noite (nao houve cegueira), e esconde-la
    # faria o usuario adivinhar se o segundo numero sumiu ou coincidiu.
    #
    # O FARMADO SAI DO DENOMINADOR DO EXP, e a escolha tem numero atras: o EXP
    # foi o campo com 0% de recusa nas 14 amostras medidas na Fase 1, entao o
    # denominador dele e o mais proximo de "tempo realmente farmado". O da
    # adena e menor por causa dos 21% de recusa DELA, que e um fato sobre a
    # leitura da adena e nao sobre a noite — e ele continua visivel, colado na
    # propria taxa da adena logo abaixo.
    linhas += [
        "",
        "HA QUANTO TEMPO A SESSAO CORRE:",
        "  sessao de pe "
        f"{duracao_curta(agora - desde)} "
        f"({duracao_curta(taxas_de_exp.sessao.janela_farmada_em_segundos)}"
        " farmadas)",
        "",
        f"O QUE ISSO RENDE (denominador em {taxas_de_exp.sessao.unidade_da_janela}, "
        "e nao de relogio):",
    ]

    # AS DUAS TAXAS DE CADA GRANDEZA SAEM JUNTAS (CTX-4). A janela responde "o
    # que esta acontecendo agora" e a sessao responde "o que a noite rendeu";
    # apresentar so uma MENTE POR OMISSAO, e o tamanho da mentira esta medido:
    # 226 mil adena/h contra 466 mil/h, um fator de dois, e a diferenca inteira
    # e TEMPO PARADO.
    for rotulo_base, duas in (
        ("XP/h", taxas_de_exp),
        ("adena/h", taxas_de_adena),
    ):
        linhas += _linhas_de_uma_taxa(
            rotulo_base, _sufixo_da_janela(duas.janela), duas.janela, agora
        )
        linhas += _linhas_de_uma_taxa(
            rotulo_base, _sufixo_da_sessao(duas.sessao), duas.sessao, agora
        )
    linhas += _linhas_do_eta(eta, campos, agora)

    # O QUE SAIU DO DENOMINADOR. Sem estes dois numeros, "a taxa caiu" e "o
    # scanner nao viu" ficam indistinguiveis — e sao consertos opostos.
    sessao = taxas_de_exp.sessao
    linhas += [
        "",
        "O QUE SAIU DO DENOMINADOR:",
        _linha(
            "lacunas excluidas",
            f"{sessao.lacunas_excluidas} "
            f"({duracao_curta(sessao.segundos_em_lacuna)} cegos)",
        ),
        _linha("passos aceitos na sessao", str(contagem.aceitas)),
    ]

    # POR QUE O `n` E ESSE. Medido em campo: nivel 79%, adena 21%, EXP 0%. Um
    # painel que esconde estes numeros faz o usuario concluir que o scanner
    # travou — e isso JA ACONTECEU EM PRODUCAO, em 2026-09-01, com o aviso de
    # layout do mercado, e virou o comentario de `mercado_modo.py:748-751`.
    #
    # O CAMPO COM ZERO RECUSA SAI MESMO ASSIM: sumir com ele faria parecer que
    # ele nao foi medido, que e outra coisa.
    linhas += ["", "POR QUE O `n` E ESSE (recusa por campo, nesta sessao):"]
    for campo in ROTULO_NA_LINHA:
        linhas.append(
            _linha(
                ROTULO_NA_LINHA[campo],
                _grafia_da_porcentagem(
                    int(recusas_por_campo.get(campo, 0)), int(tiques)
                ),
            )
        )

    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# O RESUMO DA SESSAO
# ---------------------------------------------------------------------------


def resumo_da_sessao_da_renda(
    contagem,
    orcamento,
    registro,
    *,
    recusas_por_campo: dict,
    tiques: int,
) -> str:
    """O fim da sessao, contando o que foi ao DISCO e o que ele custou.

    ELE SAI SEMPRE, e inclusive numa sessao de zero linhas gravadas: o
    `vigiar-renda.bat` do `03-04` nao tem bloco de encerramento nenhum, pela
    mesma decisao ja escrita no `vigiar-mercado.bat:129-135` — *"o resumo da
    sessao sai do proprio programa"*. Um resumo condicional deixaria a janela
    do `.bat` fechar em silencio exatamente na sessao que deu errado.

    OS QUATRO NUMEROS DE `ContagemDaRenda` NAO SE SOMAM, e por isso saem em
    linhas separadas: "o scanner nao viu" (lacuna) e "o scanner viu e recusou"
    (recusa) pedem consertos OPOSTOS do usuario.

    AS DUAS SECOES DE RECUSA SAO DUAS, E OS TITULOS DIZEM O PORQUE. Uma conta
    RECUSA POR CAMPO (o nivel nao virou numero neste tique) e sai de
    `CamposDaRenda`; a outra conta RECUSA DE PAR (o EXP andou para tras entre
    dois tiques) e sai de `contagem.recusadas_por_motivo`, que e alimentado por
    `passo.recusas` — *"A TUPLA QUE `conferir_o_par` DEVOLVEU"*. Sao fatos
    diferentes com consertos diferentes: a primeira e calibracao, a segunda e
    leitura errada que a guarda pegou. As duas ja tiveram o MESMO titulo neste
    arquivo por uma revisao, e o defeito apareceu na hora: um leitor que
    procurasse o numero por titulo achava o outro.
    """
    linhas = [
        console.moldurar(
            "RESUMO DA SESSAO DE RENDA", datetime.now().strftime("%H:%M")
        ),
        "",
        "O QUE FOI PARA O DISCO:",
        f"  {'passos ACEITOS':<{COLUNA_DO_ROTULO}} {contagem.aceitas}",
        f"  {'lacunas (o scanner nao viu)':<{COLUNA_DO_ROTULO}} "
        f"{contagem.lacunas}",
        "",
        "RECUSA POR CAMPO (o pixel nao virou numero), sobre "
        f"{tiques} tique(s):",
    ]
    for campo in ROTULO_NA_LINHA:
        linhas.append(
            _linha(
                ROTULO_NA_LINHA[campo],
                _grafia_da_porcentagem(
                    int(recusas_por_campo.get(campo, 0)), int(tiques)
                ),
            )
        )

    linhas += [
        "",
        "RECUSA DE PAR (a guarda pegou um numero incrivel), somada na sessao:",
    ]
    if contagem.recusadas_por_motivo:
        for motivo, quantas in sorted(
            contagem.recusadas_por_motivo.items(),
            key=lambda par: (-par[1], par[0]),
        ):
            linhas.append(f"  {motivo:<{COLUNA_DO_ROTULO}} {quantas}")
    else:
        linhas.append("  nenhum par foi recusado nesta sessao")

    linhas += [
        "",
        "O QUE ESTE PROCESSO CUSTOU POR TIQUE:",
        f"  {'p50':<{COLUNA_DO_ROTULO}} {orcamento.p50 * 1000:.0f} ms",
        f"  {'p95':<{COLUNA_DO_ROTULO}} {orcamento.p95 * 1000:.0f} ms",
        f"  {'maximo':<{COLUNA_DO_ROTULO}} {orcamento.maximo * 1000:.0f} ms",
        f"  {'tiques que estouraram':<{COLUNA_DO_ROTULO}} "
        f"{orcamento.estouros} de {orcamento.total} "
        f"(orcamento: {orcamento.limite:.1f}s)",
        "",
        "  Estes numeros dizem o que ESTE processo custou, e so isso.",
        "  Contencao entre os processos (duas partys, o mercado e a renda) e",
        "  propriedade do SISTEMA - CPU, GPU, sessoes de captura, agendador do",
        "  Windows - e nenhum numero daqui a alcanca.",
        "",
        f"  Arquivo desta sessao: {registro.arquivo}",
    ]
    return "\n".join(linhas)
