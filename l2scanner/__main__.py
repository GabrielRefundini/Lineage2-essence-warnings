"""Ponto de entrada do L2 Party Scanner.

A PRIMEIRA coisa executavel aqui e declarar consciencia de DPI, antes de
qualquer import que toque na tela. Isso nao e estilo — e a diferenca entre
capturar a regiao certa e capturar uma regiao deslocada sem nenhum aviso.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# DPI PRIMEIRO. Nao mova, nao adicione imports de tela acima desta linha.
from .dpi import tornar_consciente_de_dpi

_MODO_DPI = tornar_consciente_de_dpi()
# ---------------------------------------------------------------------------

import argparse  # noqa: E402
import logging  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from logging.handlers import RotatingFileHandler  # noqa: E402
from pathlib import Path  # noqa: E402

from .calibracao import (  # noqa: E402
    Calibracao,
    CalibracaoInvalida,
    descrever_geometria_da_tela,
)
from .frames import MssSource, Regiao, SaudeDoFrame  # noqa: E402
from .gravador import Gravador  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_CALIBRACAO = RAIZ / "calibration.json"
PASTA_GRAVACOES = RAIZ / "recordings"
PASTA_LOGS = RAIZ / "logs"

INTERVALO_PADRAO = 1.0  # segundos entre capturas

log = logging.getLogger("l2scanner")


def configurar_log(verboso: bool) -> None:
    """Log em arquivo rotativo + console.

    O arquivo importa: quando o scanner morre calado durante um farm de tres
    horas, o log e a unica forma de descobrir o porque depois.
    """
    PASTA_LOGS.mkdir(exist_ok=True)

    formato = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S"
    )

    arquivo = RotatingFileHandler(
        PASTA_LOGS / "scanner.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    arquivo.setFormatter(formato)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formato)

    log.setLevel(logging.DEBUG if verboso else logging.INFO)
    log.addHandler(arquivo)
    log.addHandler(console)


def calibracao_provisoria(regiao: Regiao) -> Calibracao:
    """Calibracao minima para gravar antes da Fase 2 existir.

    A ferramenta visual de calibracao chega na Fase 2. Ate la, `--regiao`
    permite comecar a gravar sessoes hoje — que e o ponto todo de ter o
    gravador antes da deteccao.
    """
    return Calibracao(
        party_window=regiao,
        # Ancora provisoria: faixa superior da propria janela. Na Fase 2 ela
        # vira uma marca escolhida no olho. Fica no TOPO porque a party window
        # e ancorada em cima e encolhe por baixo quando a PT diminui.
        ancora=Regiao(esquerda=0, topo=0, largura=regiao.largura, altura=8),
        geometria_da_tela=descrever_geometria_da_tela(),
    )


def resolver_calibracao(args: argparse.Namespace) -> Calibracao:
    if args.regiao:
        try:
            e, t, l, a = (int(p) for p in args.regiao.split(","))
        except ValueError:
            raise CalibracaoInvalida(
                "--regiao espera quatro inteiros: esquerda,topo,largura,altura\n"
                "Ex.: --regiao 1713,330,450,300"
            )
        cal = calibracao_provisoria(Regiao(e, t, l, a))
        cal.salvar(ARQUIVO_CALIBRACAO)
        log.info("Calibracao provisoria gravada em %s", ARQUIVO_CALIBRACAO.name)
        return cal

    cal = Calibracao.carregar(ARQUIVO_CALIBRACAO)
    cal.conferir_geometria(descrever_geometria_da_tela())
    return cal


def laco_principal(args: argparse.Namespace, cal: Calibracao) -> int:
    """Captura em intervalo fixo, opcionalmente gravando.

    O laco e a prova de falhas: uma excecao em qualquer etapa vira log e a
    proxima iteracao acontece. Um scanner que morre calado e pior do que nenhum
    scanner, porque a party aprende a confiar num silencio que nao significa
    mais nada.
    """
    fonte = MssSource(cal.party_window)
    gravador = Gravador(PASTA_GRAVACOES, args.rotulo) if args.record else None

    if gravador:
        log.info("Gravando em %s", gravador.pasta)

    log.info(
        "Vigiando regiao %dx%d em (%d,%d) a cada %.1fs. Ctrl+C para parar.",
        cal.party_window.largura,
        cal.party_window.altura,
        cal.party_window.esquerda,
        cal.party_window.topo,
        args.intervalo,
    )

    contagem = {estado: 0 for estado in SaudeDoFrame}
    saude_anterior: SaudeDoFrame | None = None
    erros_seguidos = 0

    try:
        while True:
            inicio = time.monotonic()

            try:
                frame = fonte.capturar()
                erros_seguidos = 0

                contagem[frame.saude] += 1

                # So fala quando o estado MUDA — senao vira spam a 1 Hz
                if frame.saude is not saude_anterior:
                    if frame.saude is SaudeDoFrame.OK:
                        log.info("Visao OK")
                    elif frame.saude is SaudeDoFrame.FALHA_DE_CAPTURA:
                        log.warning(
                            "Falha de captura (frame preto/vazio) — "
                            "sem visao, nenhum alerta seria enviado agora"
                        )
                    elif frame.saude is SaudeDoFrame.CONGELADO:
                        log.warning(
                            "Imagem congelada ha %d frames — jogo travado "
                            "ou captura presa",
                            30,
                        )
                    saude_anterior = frame.saude

                if gravador:
                    gravador.gravar(frame, time.time())

            except Exception:
                erros_seguidos += 1
                log.exception("Erro na iteracao (seguidos: %d)", erros_seguidos)
                if erros_seguidos >= 10:
                    log.error("10 erros seguidos — encerrando para nao rodar cego")
                    return 1

            dormir = args.intervalo - (time.monotonic() - inicio)
            if dormir > 0:
                time.sleep(dormir)

    except KeyboardInterrupt:
        log.info("Encerrado pelo usuario")

    finally:
        fonte.fechar()
        if gravador:
            gravador.fechar()
            log.info(
                "Sessao gravada: %d frames em %s",
                gravador.frames_gravados,
                gravador.pasta,
            )

        total = sum(contagem.values())
        if total:
            log.info(
                "Resumo: %d frames — %d ok, %d falha de captura, %d congelados",
                total,
                contagem[SaudeDoFrame.OK],
                contagem[SaudeDoFrame.FALHA_DE_CAPTURA],
                contagem[SaudeDoFrame.CONGELADO],
            )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="l2scanner",
        description="Vigia a party window do Lineage 2 e avisa no WhatsApp.",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="grava a sessao em disco (frames + observacoes)",
    )
    parser.add_argument(
        "--rotulo",
        help="nome para identificar a gravacao (ex.: 'farm-noturno')",
    )
    parser.add_argument(
        "--regiao",
        help=(
            "calibracao provisoria: esquerda,topo,largura,altura da party window. "
            "Grava calibration.json e ja comeca a rodar."
        ),
    )
    parser.add_argument(
        "--intervalo",
        type=float,
        default=INTERVALO_PADRAO,
        help=f"segundos entre capturas (padrao: {INTERVALO_PADRAO})",
    )
    parser.add_argument("-v", "--verboso", action="store_true", help="log detalhado")

    args = parser.parse_args()
    configurar_log(args.verboso)

    log.debug("Consciencia de DPI: %s", _MODO_DPI)
    if _MODO_DPI.startswith("FALHOU"):
        log.warning(
            "Nao consegui declarar consciencia de DPI. Se a sua escala de tela "
            "nao for 100%%, as coordenadas podem sair deslocadas."
        )

    try:
        cal = resolver_calibracao(args)
    except CalibracaoInvalida as erro:
        log.error("%s", erro)
        return 2

    return laco_principal(args, cal)


if __name__ == "__main__":
    sys.exit(main())
