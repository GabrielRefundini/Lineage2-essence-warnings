"""Poe a constante medida da ponte XP<->porcentagem no `calibration.json`.

QUATRO PASSOS E NADA MAIS: ler os argumentos, `Calibracao.carregar`, `semear`, e
— se e so se o estado for `semeado` — `Calibracao.salvar`.

A DECISAO NAO MORA AQUI, E ISSO E DE PROPOSITO. O que muda, o que fica, e o que
exige confirmacao vive em `l2scanner/renda_semeadura.py`, que e o que os testes
importam. Regra de negocio dentro de um `argparse` e regra que nenhum teste
alcanca — e as duas garantias desta operacao (nao apagar chave alheia, nao
sobrescrever calada) sao regra de negocio.

ELA NUNCA ESCREVE O ARQUIVO A MAO, e a razao vale estar aqui em cima. O
`calibration.json` e compartilhado por QUATRO features e um `write_text` direto
sobre o destino deixa um JSON **truncado** se a escrita for interrompida —
Ctrl-C impaciente, disco cheio, antivirus segurando o handle. O que morre nao e
a renda: e o **scanner de alertas de party inteiro**, que e o produto. Por isso
a gravacao passa pelo `Calibracao.salvar`, que ja escreve em `.tmp` ao lado e
troca por `os.replace` — atomico no mesmo volume: ou fica o arquivo antigo
inteiro, ou o novo inteiro, nunca meio.

ELA NAO MEDE NADA. Medir a ponte exige ler o chat em cadencia alta, e isso e
ferramenta de calibracao — Fase 3 ou tarefa propria, deferida pelo
`02-CONTEXT.md`. Esta aqui so poe no arquivo um numero que ja foi medido, e a
procedencia dele viaja junto: 388.700 XP por ponto percentual, Faerlina nivel
67, 2026-09-02, 55 Hz, censo completo, 114 abates, 240 linhas de chat. Todos
esses numeros estao versionados em
`.planning/workstreams/renda/REQUIREMENTS.md`, REND-08.

USO:

    PYTHONPATH=. .venv/Scripts/python.exe tools/semear_a_ponte_de_xp.py
    PYTHONPATH=. .venv/Scripts/python.exe tools/semear_a_ponte_de_xp.py --confirmar
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from l2scanner.calibracao import Calibracao  # noqa: E402
from l2scanner.renda_semeadura import (  # noqa: E402
    ENTRADA_MEDIDA,
    SEMEADO,
    semear,
)

ARQUIVO_CALIBRACAO = RAIZ / "calibration.json"


def _argumentos(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Poe a constante medida da ponte XP<->porcentagem no "
            "calibration.json, pelo caminho atomico que ja existe."
        )
    )
    parser.add_argument(
        "--calibracao",
        type=Path,
        default=ARQUIVO_CALIBRACAO,
        help="outro calibration.json (para teste)",
    )
    parser.add_argument(
        "--confirmar",
        action="store_true",
        help=(
            "sobrescreve uma constante ja existente para o mesmo personagem e "
            "nivel. Sem isto a ferramenta recusa e mostra as duas lado a lado: "
            "uma constante recalibrada com mais tempo de medicao e melhor que "
            "a semeada, e nao pode morrer em silencio."
        ),
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    argumentos = _argumentos(argv)
    calibracao = Calibracao.carregar(argumentos.calibracao)
    resultado = semear(
        calibracao, ENTRADA_MEDIDA, confirmar=argumentos.confirmar
    )

    if resultado.estado != SEMEADO:
        print(f"RECUSADO: {resultado.estado}")
        print(
            f"  ja existe uma constante para {ENTRADA_MEDIDA.personagem} "
            f"no nivel {ENTRADA_MEDIDA.nivel}, e ela NAO foi sobrescrita."
        )
        print(f"  existente: {resultado.existente}")
        print(f"  entrando : {resultado.entrando}")
        print(
            "  Se a que entra e a melhor medicao, rode de novo com --confirmar."
        )
        return 1

    resultado.calibracao.salvar(argumentos.calibracao)
    print(
        f"SEMEADO: {ENTRADA_MEDIDA.personagem} nivel {ENTRADA_MEDIDA.nivel} = "
        f"{ENTRADA_MEDIDA.valores['xp_por_ponto']} XP por ponto percentual"
    )
    print(f"  gravado em {argumentos.calibracao} (via .tmp + troca atomica)")
    if resultado.existente is not None:
        print(f"  a anterior era: {resultado.existente}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
