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

from datetime import datetime

from . import console
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
# O RESUMO DA SESSAO
# ---------------------------------------------------------------------------

# A largura da coluna de rotulos dos blocos, copiada de `resumo_da_sessao`
# (`mercado_console.py:694`): trinta e dois alinha os numeros numa coluna so
# sem empurrar nenhum rotulo desta fase para a linha seguinte.
COLUNA_DO_ROTULO = 32


def resumo_da_sessao_da_renda(contagem, orcamento, registro) -> str:
    """O fim da sessao, contando o que foi ao DISCO e o que ele custou.

    ELE SAI SEMPRE, e inclusive numa sessao de zero linhas gravadas: o
    `vigiar-renda.bat` do `03-04` nao tem bloco de encerramento nenhum, pela
    mesma decisao ja escrita no `vigiar-mercado.bat:129-135` — *"o resumo da
    sessao sai do proprio programa"*. Um resumo condicional deixaria a janela
    do `.bat` fechar em silencio exatamente na sessao que deu errado.

    OS QUATRO NUMEROS DE `ContagemDaRenda` NAO SE SOMAM, e por isso saem em
    linhas separadas: "o scanner nao viu" (lacuna) e "o scanner viu e recusou"
    (recusa) pedem consertos OPOSTOS do usuario.
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
        "POR QUE O `n` E ESSE (recusa por campo, somada na sessao):",
    ]

    if contagem.recusadas_por_motivo:
        for motivo, quantas in sorted(
            contagem.recusadas_por_motivo.items(),
            key=lambda par: (-par[1], par[0]),
        ):
            linhas.append(f"  {motivo:<{COLUNA_DO_ROTULO}} {quantas}")
    else:
        linhas.append("  nenhum campo foi recusado nesta sessao")

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
