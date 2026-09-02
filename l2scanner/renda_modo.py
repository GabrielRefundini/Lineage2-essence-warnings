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

NESTA ONDA ELE IMPRIME SO O EXP. A adena e o nivel entram no plano `01-04`, que
estende este arquivo em vez de reescreve-lo.
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
from .renda_leitura import RecusaDaRenda, exp_da_barra, recortar

SAIDA_OK = 0
SAIDA_OPERACIONAL = 1
SAIDA_RECUSA = 3

# A pausa que a captura por janela precisa para entregar o primeiro frame. E a
# mesma do calibrador do aviso de boss, e ela existe porque a Windows Graphics
# Capture e assincrona: sem ela o primeiro `capturar_completo` volta vazio e a
# ferramenta acusaria "janela minimizada" para uma janela perfeitamente aberta.
PAUSA_ATE_O_PRIMEIRO_FRAME = 0.3

# A sub-chave do EXP dentro da entrada do personagem. O NOME MENTE, e a mentira
# esta documentada no bloco de comentario do campo `renda_por_personagem`:
# `barra_esquerda` descreve o EXP e `barra_direita` descreve a ADENA.
SUBCHAVE_DO_EXP = "barra_esquerda"


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

    bloco = entrada[SUBCHAVE_DO_EXP]
    recorte = recortar(
        frame, Regiao.de_dict(bloco["regiao"]), campo="exp"
    )
    if isinstance(recorte, RecusaDaRenda):
        print(
            f"RECUSADO  exp  ({recorte.motivo}): {recorte.detalhe}",
            file=sys.stderr,
        )
        return SAIDA_RECUSA

    leitura = exp_da_barra(recorte, piso_de_brilho=int(bloco["piso_de_brilho"]))
    if isinstance(leitura, RecusaDaRenda):
        print(
            f"RECUSADO  exp  ({leitura.motivo}): {leitura.detalhe}",
            file=sys.stderr,
        )
        return SAIDA_RECUSA

    # A MARCA DE UMA ESCALA SO, e ela nao e enfeite: nos campos em que uma das
    # escalas abstem sempre, o cruzamento NAO esta pegando substituicao de
    # digito, e o unico verificador que resta e o olho de quem compara o
    # terminal com o monitor. Marcar e barato; nao marcar e afirmar uma guarda
    # que nao esta la.
    marca = " *" if leitura.escalas < 2 else ""
    print(f"{personagem}  EXP {_grafia_do_exp(leitura.valor)}{marca}")
    if marca:
        print("  * sustentado por UMA escala de leitura so (a outra abstem).")
    return SAIDA_OK


if __name__ == "__main__":
    raise SystemExit(main())
