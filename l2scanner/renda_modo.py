"""O comando de LEITURA UNICA da renda: um frame entra, um numero sai.

O QUE ESTE MODULO E
===================
Ele e a ferramenta, e `renda_leitura.py` e o modulo puro. A seta aponta
FERRAMENTA -> PURO e nunca o contrario: aqui se le argumento de linha de
comando, se resolve a fonte de pixel e se imprime; la nao se faz nenhuma das
tres coisas.

DUAS FONTES DE PIXEL, E A PRIMEIRA E O QUE TORNA A FATIA VERIFICAVEL
=====================================================================
`--imagem` le um PNG do disco. E ela que permite provar o caminho inteiro —
calibracao validada, recorte com guarda, mascara com piso calibrado, duas
escalas, gramatica com trava, inteiro escalado — **sem o jogo aberto**, contra
uma fixtura resgatada de uma gravacao real.

`--janela` le a janela do jogo pelo titulo, no molde que o calibrador do aviso
de boss ja usa. O alvo cai para `cal.janela` quando o titulo nao vem.

ELE PRECISA SABER DE QUEM E A TELA ANTES DE LER
================================================
No caminho `--janela` o nome sai do titulo. No caminho `--imagem` nao ha
titulo, entao `--personagem` e **obrigatorio** — sem default, sem "o unico que
estiver no arquivo", sem cair no primeiro. Medido (M-F): as duas instancias
poem a janela de status em lugares diferentes, e ler uma com o retangulo da
outra nao devolve um campo vazio que alguem nota — devolve `349` ou `112`, que
sao numeros desenhados ao lado do nivel e passam por qualquer validacao sem
reclamar. Um leitor offline que adivinha o personagem le o retangulo do
vizinho.

A recusa de personagem ausente e NOMEADA e sai **antes de qualquer OCR**: nao
se gasta o motor para descobrir que nao se sabia de quem era a tela.

OS CODIGOS DE SAIDA, E A TABELA MORA AQUI PORQUE UM CODIGO SEM TABELA E UM
NUMERO QUE SO O AUTOR ENTENDE
==========================================================================

    0   a leitura fechou
    1   FALHA OPERACIONAL: sem frame, calibracao invalida, personagem
        desconhecido, OCR indisponivel -- a ferramenta nao chegou a ler
    3   RECUSA NOMEADA: a ferramenta funcionou e o pixel nao deu o campo; a
        saida diz qual campo e por que

A separacao entre 1 e 3 e o que impede o desastre de suporte mais comum desta
familia de ferramenta: "recusou" e "quebrou" precisam ser distinguiveis de
fora, porque quem vai olhar o codigo de saida e a fase seguinte e nao um
humano. Um campo recusado NAO e um erro do programa.

DESDE O `01-04` ELE IMPRIME OS TRES CAMPOS, e a GRAFIA e o produto daquela
onda. O modulo puro devolve INTEIRO — e o inteiro e o que a Fase 2 vai gravar e
o que o `dashboard` vai consumir. Quem escreve o numero de volta na grafia que o
jogo usa na tela e a FERRAMENTA, porque o criterio 1 e uma comparacao entre o
terminal e o monitor, e uma comparacao so funciona se as duas grafias forem a
mesma: o nivel como inteiro nu, o EXP com as quatro casas e o sinal de
porcentagem, a adena com o separador de milhar que o jogo escreve. Um usuario
nao deveria ter de traduzir mentalmente um inteiro sem separadores para
conferir uma leitura.

E UM CAMPO QUE RECUSOU IMPRIME A RECUSA, e nunca um espaco vazio. E o criterio
3 aparecendo na TELA e nao so no log: os consertos sao diferentes e o usuario
precisa distinguir qual e o dele.

    campo-vazio           -> o retangulo ou o piso de brilho
    gramatica             -> so o piso de brilho
    personagem            -> rodar `calibrar-renda.bat` para este personagem
    conjunto-de-moldes    -> rodar `calibrar-renda-moldes.bat` apontando o
                             campo da barra onde os rotulos que faltam aparecem

O QUARTO E NOVO NO `01-04`, e e o unico cujo conserto nao aponta para um
retangulo nem para um piso: ele aponta para uma RODADA DO CORTADOR. Um usuario
que visse "recusa de gramatica" ali passaria a noite mexendo em piso de brilho.
E o conserto que ele anuncia MUDOU nesta revisao: ate o M-L ele era *farme ate
o digito aparecer*, e medido, o `5` e o `7` ja estao na tela em outros campos
da mesma barra. Um motivo generico aqui custa uma noite de suporte.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

from .calibracao import Calibracao, CalibracaoInvalida
from .cliente import nome_do_personagem
from .frames import Regiao
from .renda_leitura import (
    CAMPO_DA_ADENA,
    CAMPO_DO_EXP,
    CAMPO_DO_NIVEL,
    MOTIVO_DO_CAMPO_VAZIO,
    MOTIVO_DO_CONJUNTO_DE_MOLDES,
    MOTIVO_DO_PERSONAGEM,
    RecusaDaRenda,
    ValorDaRenda,
    ler_os_tres_campos,
)

SAIDA_OK = 0
SAIDA_OPERACIONAL = 1
SAIDA_RECUSA = 3

# A pausa que a captura por janela precisa para entregar o primeiro frame. E a
# mesma do calibrador do aviso de boss, e ela existe porque a Windows Graphics
# Capture e assincrona: sem ela o primeiro `capturar_completo` volta vazio e a
# ferramenta acusaria "janela minimizada" para uma janela perfeitamente aberta.
PAUSA_ATE_O_PRIMEIRO_FRAME = 0.3

# O ROTULO DE CADA CAMPO NA TELA, na ordem em que eles aparecem no jogo.
# Alinhados na mesma largura para que o olho desca a coluna dos numeros sem
# tropecar — o criterio 1 e uma comparacao visual, e uma coluna torta e uma
# comparacao mais lenta.
ROTULO_DO_CAMPO = {
    CAMPO_DO_NIVEL: "nivel",
    CAMPO_DO_EXP: "EXP  ",
    CAMPO_DA_ADENA: "adena",
}

# A MARCA DO CAMPO SUSTENTADO POR UMA ESCALA SO. Ela e a mesma disciplina de
# `n` e recencia que o `--mercado` cola em todo numero que vai a tela, e ela
# existe pela razao MEDIDA (M-D): nos campos em que uma escala abstem sempre, o
# cruzamento NAO esta pegando substituicao de digito, e o unico verificador que
# resta e o olho de quem compara o terminal com o monitor. Marcar e barato; nao
# marcar e afirmar uma guarda que nao esta la.
MARCA_DE_UMA_ESCALA = " *"

# O CONSERTO DE CADA RECUSA, e eles sao DIFERENTES — que e a razao inteira de
# os motivos serem distintos. Um motivo generico aqui custa uma noite de
# suporte a quem seguir a mensagem errada.
CONSERTO_POR_MOTIVO = {
    MOTIVO_DO_CAMPO_VAZIO: (
        "o campo nao apareceu na mascara: confira o RETANGULO ou o PISO DE "
        "BRILHO desta regiao com `calibrar-renda.bat`"
    ),
    MOTIVO_DO_PERSONAGEM: (
        "este personagem nao esta calibrado: rode `calibrar-renda.bat` para ele"
    ),
    MOTIVO_DO_CONJUNTO_DE_MOLDES: (
        "rode `calibrar-renda-moldes.bat` apontando o campo da barra onde os "
        "rotulos que faltam aparecem (--campo bonus, --campo lcoin, --campo exp)"
    ),
}


def montar_analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(
        prog="python -m l2scanner.renda_modo",
        description="Le a renda de UM frame e imprime o EXP com quatro casas.",
    )
    fonte = analisador.add_mutually_exclusive_group(required=True)
    fonte.add_argument(
        "--imagem",
        type=Path,
        help="um PNG de janela inteira; exige --personagem junto",
    )
    fonte.add_argument(
        "--janela",
        nargs="?",
        const="",
        help="o titulo da janela do jogo (sem valor: usa o da calibracao)",
    )
    analisador.add_argument(
        "--personagem",
        help="de quem e esta tela. OBRIGATORIO com --imagem, porque um PNG nao "
        "carrega titulo e a calibracao da renda e POR PERSONAGEM",
    )
    analisador.add_argument(
        "--calibracao",
        type=Path,
        help="um calibration.json alternativo (default: o do usuario)",
    )
    return analisador


def _grafia_do_exp(valor: int) -> str:
    """`80012` -> `8,0012%`, na grafia que o olho compara com o monitor.

    A grafia mora AQUI e o inteiro mora no modulo puro, e a divisao nao e
    arbitraria: o inteiro e o que a Fase 2 vai consumir, e uma string formatada
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
    de milhar aqui seria uma segunda gramatica de milhar nesta arvore, e o
    `01-04` nao abre nenhuma.
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


def _linha_do_campo(campo: str, resultado) -> str:
    """Uma linha da tabela: o rotulo, e o numero OU a recusa nomeada.

    A RECUSA VAI NA PROPRIA LINHA DO CAMPO, e nao no lugar da tabela inteira.
    Um leitor que abortasse no primeiro problema esconderia os outros dois, e o
    usuario ficaria sem saber se a calibracao inteira esta errada ou so um
    retangulo.
    """
    rotulo = ROTULO_DO_CAMPO[campo]
    if isinstance(resultado, RecusaDaRenda):
        return f"  {rotulo}  RECUSADO ({resultado.motivo}): {resultado.detalhe}"

    grafia = GRAFIA_POR_CAMPO[campo](resultado.valor)
    # A MARCA SO EXISTE ONDE HA CRUZAMENTO. A adena e lida por UM metodo so e
    # nao carrega `escalas`: marca-la afirmaria uma guarda enfraquecida onde
    # nunca houve guarda nenhuma, e nao marca-la seria mentir por omissao. Ela
    # simplesmente nao entra nessa conversa, e a legenda diz isso.
    marca = ""
    if isinstance(resultado, ValorDaRenda) and resultado.escalas < 2:
        marca = MARCA_DE_UMA_ESCALA
    return f"  {rotulo}  {grafia}{marca}"


def _carregar_calibracao(caminho: Path | None):
    """O `calibration.json` pedido, ou o do usuario.

    O import de `calibrar` mora DENTRO do ramo que precisa dele, e nao no topo
    do arquivo: aquele modulo chama `tornar_consciente_de_dpi()` no import.
    Quem passa `--calibracao` — a suite inteira, entre outros — nao deve pagar
    um efeito colateral de processo por um caminho de arquivo.
    """
    if caminho is not None:
        return Calibracao.carregar(caminho)
    from .calibrar import ARQUIVO_CALIBRACAO

    return Calibracao.carregar(ARQUIVO_CALIBRACAO)


def _frame_de_imagem(caminho: Path):
    if not caminho.exists():
        return None, f"Nao encontrei a imagem {caminho}."
    frame = cv2.imread(str(caminho))
    if frame is None or frame.size == 0:
        return None, f"Nao consegui ler {caminho} como imagem."
    return frame, None


def _frame_de_janela(titulo: str):
    from .captura_janela import JanelaSource

    fonte = None
    try:
        # A REGIAO UNITARIA COM `relativa` LIGADO e o molde que o calibrador do
        # aviso de boss ja usa: o que interessa e `capturar_completo`, que
        # devolve a JANELA INTEIRA, e a regiao so existe porque a fonte pede
        # uma. Os retangulos da renda sao janela-relativos (M-A), entao o frame
        # inteiro e exatamente o espaco de coordenadas da calibracao.
        fonte = JanelaSource(titulo, Regiao(0, 0, 1, 1), relativa=True)
        time.sleep(PAUSA_ATE_O_PRIMEIRO_FRAME)
        frame = fonte.capturar_completo()
    except Exception as erro:  # noqa: BLE001 - borda da ferramenta
        return None, f"Nao consegui ler a janela {titulo!r}: {erro}"
    finally:
        if fonte is not None:
            fonte.fechar()
    if frame is None or frame.size == 0:
        return None, (
            f"Nenhum frame utilizavel chegou da janela {titulo!r}. "
            f"Ela esta minimizada?"
        )
    return frame, None


def main(argv: list[str] | None = None) -> int:
    args = montar_analisador().parse_args(argv)

    try:
        cal = _carregar_calibracao(args.calibracao)
    except CalibracaoInvalida as erro:
        print(f"A calibracao nao serve: {erro}", file=sys.stderr)
        return SAIDA_OPERACIONAL
    except Exception as erro:  # noqa: BLE001 - a ferramenta explica sem traceback
        print(f"Nao consegui abrir a calibracao: {erro}", file=sys.stderr)
        return SAIDA_OPERACIONAL

    if args.imagem is not None:
        if not args.personagem:
            print(
                "--personagem e OBRIGATORIO junto de --imagem.\n"
                "  Um PNG nao carrega titulo de janela, e a calibracao da renda "
                "e POR PERSONAGEM:\n"
                "  as duas instancias poem a janela de status em lugares "
                "diferentes (14 px na\n"
                "  vertical, medido), e ler uma com o retangulo da outra "
                "devolve um numero\n"
                "  plausivel e errado em vez de um campo vazio que alguem nota.",
                file=sys.stderr,
            )
            return SAIDA_OPERACIONAL
        personagem = args.personagem
        fonte_de_pixel = args.imagem.name
        frame, erro = _frame_de_imagem(args.imagem)
    else:
        titulo = args.janela or cal.janela
        if not titulo:
            print(
                "Nao sei qual janela ler: --janela veio sem titulo e a "
                "calibracao nao tem um gravado.",
                file=sys.stderr,
            )
            return SAIDA_OPERACIONAL
        # O NOME SAI DO TITULO, e nao de um argumento: com duas instancias
        # abertas, adivinhar daria errado, e `--personagem` aqui seria uma
        # segunda verdade sobre a mesma janela.
        personagem = args.personagem or nome_do_personagem(titulo)
        fonte_de_pixel = f"janela {titulo!r}"
        frame, erro = _frame_de_janela(titulo)

    if erro is not None:
        print(erro, file=sys.stderr)
        return SAIDA_OPERACIONAL

    if not personagem:
        print(
            "Nao sei de quem e esta tela. Sem nome nao ha leitura: a "
            "calibracao da renda e por personagem.",
            file=sys.stderr,
        )
        return SAIDA_OPERACIONAL

    # A RECUSA DE PERSONAGEM SAI ANTES DE QUALQUER OCR. Nao se gasta o motor
    # para descobrir que nao se sabia de quem era a tela — e, principalmente,
    # nao se cai na entrada do vizinho: ela devolve numero plausivel e errado.
    entrada = cal.renda_do_personagem(personagem)
    if entrada is None:
        conhecidos = sorted(cal.renda_por_personagem or {})
        print(
            f"Nao ha calibracao de renda para {personagem!r}.\n"
            f"  Calibrados neste arquivo: "
            f"{', '.join(conhecidos) if conhecidos else '(nenhum)'}\n"
            f"  A leitura NAO cai na calibracao de outro personagem: o "
            f"retangulo do vizinho\n"
            f"  devolve um numero plausivel e errado. Calibre este personagem.",
            file=sys.stderr,
        )
        return SAIDA_OPERACIONAL

    campos = ler_os_tres_campos(frame, personagem=personagem, calibracao=cal)

    # O CABECALHO NOMEIA A LEITURA. Com duas instancias abertas, uma leitura
    # anonima nao descreve ninguem — e a FONTE DE PIXEL entra junto porque
    # `--imagem` e `--janela` provam coisas diferentes: a primeira prova o
    # caminho contra uma fixtura, a segunda prova a tela de agora.
    print(f"{personagem}  ({fonte_de_pixel})")

    por_campo = campos.por_campo
    for campo in ROTULO_DO_CAMPO:
        print(_linha_do_campo(campo, por_campo[campo]))

    rodape = []
    if any(
        isinstance(r, ValorDaRenda) and r.escalas < 2 for r in por_campo.values()
    ):
        rodape.append(
            f" {MARCA_DE_UMA_ESCALA.strip()} sustentado por UMA escala de "
            "leitura so (a outra abstem): ali o cruzamento nao esta pegando "
            "substituicao de digito, e quem confere e o seu olho."
        )
    for resultado in por_campo.values():
        conserto = (
            CONSERTO_POR_MOTIVO.get(resultado.motivo)
            if isinstance(resultado, RecusaDaRenda)
            else None
        )
        if conserto and conserto not in rodape:
            rodape.append(f" -> {conserto}")
    for linha in rodape:
        print(linha)

    # OS TRES DESFECHOS, e a separacao entre os dois ultimos e o que impede o
    # desastre de suporte mais comum desta familia de ferramenta: quem vai ler
    # o codigo de saida e a fase seguinte, e nao um humano. UM CAMPO RECUSADO
    # NAO E UM ERRO DO PROGRAMA.
    if any(isinstance(r, RecusaDaRenda) for r in por_campo.values()):
        return SAIDA_RECUSA
    return SAIDA_OK


if __name__ == "__main__":
    raise SystemExit(main())
