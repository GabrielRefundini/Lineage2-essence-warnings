"""Diagnostico do `selectROI` que volta caixa vazia na calibracao de mercado.

NAO GRAVA NADA. Nao encosta no calibration.json. So mede e conta.

Por que esta ferramenta existe: duas correcoes ja foram aplicadas as cegas,
sem reproduzir o defeito antes, e as duas custaram uma rodada do usuario sem
resolver. Esta ferramenta troca "tenta mais um fix" por "mede qual das duas
hipoteses e a verdadeira", numa unica execucao.

MEDIDO NESTA MAQUINA, 2026-08-28 (fora do fluxo real, com teclas injetadas):
o `cv2.selectROI` devolve (0,0,0,0) NA HORA se, e somente se, uma tecla
ENTER (13), ESPACO (32) ou ESC (27) chega na janela dele. Nenhum outro
estado testado produz esse sintoma -- nem janela preexistente criada com
`namedWindow`, nem `moveWindow`, nem `imshow` antes. Entao o sintoma
relatado E uma tecla chegando. O que falta descobrir e DE ONDE ela vem.

As duas fases abaixo separam exatamente isso:

  fase 1 (sem-navegador)  frame escolhido por indice, o navegador NAO roda.
  fase 2 (com-navegador)  o navegador roda e voce confirma o frame com ENTER.

  fase 1 passa e fase 2 falha  -> a tecla vem do navegador de frames.
  as duas falham               -> a tecla nao vem do navegador; o suspeito
                                  passa a ser o bloco namedWindow/moveWindow.
  as duas passam               -> o defeito ja nao existe no codigo de hoje.

Uso:
    .venv\\Scripts\\python.exe -m tools.diagnosticar_selecao --gravacao recordings\\<pasta>
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import cv2

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from l2scanner.calibrar import _selecionar_regiao  # noqa: E402
from l2scanner.calibrar_mercado import (  # noqa: E402
    MercadoNaoCalibravel,
    escolher_frame,
)

# Abaixo disto o `selectROI` nao esperou por gente nenhuma: ele voltou
# sozinho. Um arrasto humano nao acontece em meio segundo.
LIMITE_INSTANTANEO = 0.5


def _pescar_teclas_pendentes(milissegundos: int = 300) -> list[int]:
    """Bombeia o HighGUI e DIZ que teclas estavam na fila.

    E o mesmo bombeamento que o `_selecionar_regiao` ja faz hoje, com duas
    diferencas que sao justamente o valor do diagnostico: ele nao para no
    primeiro -1 (uma tecla pode chegar alguns milissegundos depois) e ele
    IMPRIME o que achou, em vez de engolir calado.

    Se isto imprimir 13, 32 ou 27, a tecla vazada esta pega em flagrante.
    """
    achadas: list[int] = []
    fim = time.perf_counter() + milissegundos / 1000
    while time.perf_counter() < fim:
        tecla = cv2.waitKey(1)
        if tecla != -1:
            achadas.append(tecla)
    return achadas


def _rodar_fase(gravacao: Path, fase: str, indice: int) -> int:
    """Uma fase isolada, no proprio processo. Devolve codigo de saida."""
    print(f"\n{'=' * 62}")
    print(f"  FASE: {fase}")
    print(f"{'=' * 62}")

    try:
        if fase == "sem-navegador":
            print(f"  O navegador de frames NAO vai rodar (indice {indice}).")
            caminho = escolher_frame(gravacao, None, indice)
        else:
            print("  O navegador de frames VAI rodar. Confirme um frame com ENTER.")
            caminho = escolher_frame(gravacao, None, None)
    except MercadoNaoCalibravel as erro:
        print(f"  nao deu para escolher o frame: {erro}")
        return 2

    pixels = cv2.imread(str(caminho))
    if pixels is None:
        print(f"  nao consegui decodificar {caminho}")
        return 2
    print(f"  frame: {caminho.name}")

    pendentes = _pescar_teclas_pendentes()
    if pendentes:
        print(f"  >>> TECLAS PENDENTES NA FILA DO HIGHGUI: {pendentes}")
        print("  >>> (13=ENTER 32=ESPACO 27=ESC -- qualquer uma delas aborta")
        print("  >>>  o selectROI na hora. Isto e o vazamento, pego em flagrante.)")
    else:
        print("  fila do HighGUI vazia antes da selecao.")

    print("\n  Vai abrir UMA janela de selecao.")
    print("  - Se ela sumir sozinha sem voce fazer nada: o defeito aconteceu.")
    print("  - Se ela ficar esperando: tecle ESC. O teste ja terminou.\n")

    comeco = time.perf_counter()
    caixa = _selecionar_regiao(
        pixels,
        "Ancora: titulo",
        "DIAGNOSTICO: marque qualquer retangulo, ou tecle ESC.",
    )
    demorou = time.perf_counter() - comeco

    print(f"\n  selectROI devolveu {caixa} em {demorou:.2f}s")
    if demorou < LIMITE_INSTANTANEO:
        print(f"  VEREDITO {fase}: FALHOU -- voltou sozinho, sem esperar ninguem.")
        return 1
    print(f"  VEREDITO {fase}: PASSOU -- esperou a interacao normalmente.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Diagnostica o selectROI da calibracao de mercado. Nao grava nada."
    )
    parser.add_argument("--gravacao", required=True, help="pasta com frame_*.png")
    parser.add_argument("--indice", type=int, default=12)
    parser.add_argument("--fase", choices=["sem-navegador", "com-navegador"])
    args = parser.parse_args(argv)

    gravacao = Path(args.gravacao)

    # Uma fase pedida na mao roda aqui mesmo.
    if args.fase:
        return _rodar_fase(gravacao, args.fase, args.indice)

    # O modo normal roda as duas fases em processos SEPARADOS, de proposito:
    # estado de HighGUI que sobra de uma fase contaminaria a outra, e e
    # exatamente contaminacao de estado que esta sob suspeita aqui.
    vereditos: dict[str, int] = {}
    for fase in ("sem-navegador", "com-navegador"):
        resultado = subprocess.run(
            [
                sys.executable, "-u", "-m", "tools.diagnosticar_selecao",
                "--gravacao", str(gravacao),
                "--indice", str(args.indice),
                "--fase", fase,
            ],
            cwd=str(RAIZ),
        )
        vereditos[fase] = resultado.returncode

    sem, com = vereditos["sem-navegador"], vereditos["com-navegador"]
    print(f"\n{'=' * 62}")
    print("  RESUMO")
    print(f"{'=' * 62}")
    for fase, codigo in vereditos.items():
        rotulo = {0: "PASSOU", 1: "FALHOU", 2: "ERRO"}.get(codigo, "?")
        print(f"  {fase:16s} -> {rotulo}")

    print()
    if sem == 0 and com == 1:
        print("  CONCLUSAO: a tecla vem do NAVEGADOR DE FRAMES.")
        print("  O bloco namedWindow/moveWindow esta inocente.")
    elif sem == 1 and com == 1:
        print("  CONCLUSAO: o navegador esta inocente -- falha ate sem ele.")
        print("  O suspeito passa a ser o namedWindow/moveWindow do")
        print("  _selecionar_regiao, que e o que mudou em 6de5d22.")
    elif sem == 0 and com == 0:
        print("  CONCLUSAO: o defeito NAO acontece mais no codigo de hoje.")
        print("  As duas fases esperaram a interacao normalmente.")
    else:
        print("  CONCLUSAO: resultado misto ou erro de leitura -- veja as fases acima.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
