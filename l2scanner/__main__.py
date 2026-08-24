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
from dataclasses import replace  # noqa: E402
from datetime import datetime  # noqa: E402
from logging.handlers import RotatingFileHandler  # noqa: E402
from pathlib import Path  # noqa: E402

from .calibracao import (  # noqa: E402
    Calibracao,
    CalibracaoInvalida,
    descrever_geometria_da_tela,
)
from .config import ConfigAusente, config_do_chatwoot  # noqa: E402
from .captura_janela import (  # noqa: E402
    JanelaNaoEncontrada,
    JanelaSource,
    listar_janelas_do_jogo,
)
from .console import destacar  # noqa: E402
from .frames import MssSource, ReplaySource, SaudeDoFrame  # noqa: E402
from .gravador import Gravador  # noqa: E402
from .notificador import (  # noqa: E402
    Despachante,
    NotificadorChatwoot,
    NotificadorDeConsole,
    formatar,
    formatar_console,
)
from .rastreador import EstadoDoMembro, PortaoGlobal, Rastreador  # noqa: E402
from .visao import EstadoDaLinha, extrair  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_CALIBRACAO = RAIZ / "calibration.json"
PASTA_GRAVACOES = RAIZ / "recordings"
PASTA_LOGS = RAIZ / "logs"
ARQUIVO_OUTBOX = RAIZ / "outbox.jsonl"

INTERVALO_PADRAO = 1.0

# Quantas leituras cegas seguidas ate sugerir recalibrar. A 1 Hz sao ~30s:
# tempo demais para um alt-tab qualquer, curto o bastante para o usuario
# ainda lembrar do que mexeu.
TICKS_CEGO_PARA_SUGERIR_RECALIBRAR = 30

log = logging.getLogger("l2scanner")


def configurar_log(verboso: bool) -> None:
    """Log em arquivo rotativo + console.

    O arquivo importa: quando o scanner morre calado durante um farm de tres
    horas, o log e a unica forma de descobrir o porque depois.
    """
    PASTA_LOGS.mkdir(exist_ok=True)

    # O console do Windows abre em cp1252 por padrao e engasga em acento e
    # travessao — que aparecem no texto dos alertas. Sem isto, a mensagem que
    # o usuario le no console fica cheia de caractere quebrado.
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

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


def montar_despachante(args: argparse.Namespace) -> Despachante | None:
    """Monta o caminho de entrega, ou None se o scanner roda so no console."""

    def avisar_falha(texto: str, erro: str) -> None:
        # Falha de entrega NUNCA e silenciosa: silencio treina a party a
        # confiar num sinal que nao significa mais nada.
        log.error("FALHA DE ENTREGA — %s | alerta: %s", erro, texto)

    if args.dry_run:
        log.info("Modo simulacao: alertas so no console, nada e enviado")
        return Despachante(NotificadorDeConsole(), ao_falhar=avisar_falha)

    try:
        config = config_do_chatwoot()
    except ConfigAusente as erro:
        log.warning("Entrega no WhatsApp desativada — %s", erro)
        log.warning("O scanner continua util no console. Use --dry-run para calar isto.")
        return None

    log.info(
        "Entrega ativa: %d conversa(s) no Chatwoot", len(config.conversas)
    )
    return Despachante(
        NotificadorChatwoot(config),
        arquivo_outbox=ARQUIVO_OUTBOX,
        ao_falhar=avisar_falha,
    )


def desenhar_status(rastreador: Rastreador, cal: Calibracao, obs) -> str:
    """Bloco de status para o usuario conferir antes de sair AFK."""
    simbolos = {
        EstadoDoMembro.VIVO: "ok  ",
        EstadoDoMembro.MORTO: "MORTO",
        EstadoDoMembro.AUSENTE: "--  ",
        EstadoDoMembro.DESCONHECIDO: "?   ",
    }

    portao = {
        PortaoGlobal.RASTREANDO: "vigiando",
        PortaoGlobal.CEGO: "SEM VISAO",
        PortaoGlobal.REAQUISICAO: "reajustando",
    }[rastreador.portao]

    # Quando o cliente caiu, o motivo VENCE o portao. "SEM VISAO" e verdade mas
    # nao ajuda; "JOGO CAIU - TELA DE LOGIN" diz o que fazer a respeito. Foi a
    # falta disso que deixou o usuario olhando 90 s de "SEM VISAO" enquanto o
    # servidor estava em manutencao.
    from .cliente import EstadoDoCliente

    if obs.estado_do_cliente is EstadoDoCliente.TELA_DE_LOGIN:
        portao = "JOGO CAIU - TELA DE LOGIN"
    elif obs.estado_do_cliente is EstadoDoCliente.DESCONECTADO:
        portao = "JOGO CAIU - DESCONECTADO DO SERVIDOR"

    linhas = [f"[{portao}]"]
    for leitura in obs.linhas:
        if leitura.estado is EstadoDaLinha.VAZIA:
            continue
        # O nome reconhecido pela imagem vence a posicao da linha: a party
        # window reordena, e mostrar o nome por posicao seria mentir na tela
        # do mesmo jeito que mentia no alerta.
        nome = leitura.nome or cal.nome_da_linha(leitura.indice)
        estado = rastreador.estado_de(leitura.indice)
        hp = f"{leitura.hp:5.0%}" if leitura.hp is not None else "  -- "
        linhas.append(f"  {nome:<12s} {simbolos[estado]:<6s} HP {hp}")

    # Voce nao aparece na sua propria party window, entao entra numa linha
    # separada — mas com o mesmo rastreio e o mesmo debounce dos outros.
    if obs.hp_proprio is not None and cal.nome_proprio:
        estado_proprio = rastreador.estado_de_membro(f"@{cal.nome_proprio}")
        rotulo = f"{cal.nome_proprio} (voce)"
        linhas.append(
            f"  {rotulo:<12s} {simbolos[estado_proprio]:<6s} "
            f"HP {obs.hp_proprio:5.0%}"
        )

    return "\n".join(linhas)


def comando_teste_de_alerta(args: argparse.Namespace) -> int:
    """DELV-04: prova a entrega sem precisar do jogo aberto."""
    despachante = montar_despachante(args)
    if despachante is None:
        log.error("Sem configuracao de entrega — nao ha o que testar.")
        return 1

    despachante.iniciar()
    despachante.despachar(
        "Teste do L2 Party Scanner. Se voce recebeu isso sem ter falado "
        "comigo antes, o caminho de alerta esta funcionando."
    )
    despachante.encerrar()

    if despachante.falhados:
        log.error("O envio falhou. Veja o erro acima.")
        return 1

    log.info("Enviado. Agora confirme no celular: 200 do Chatwoot nao prova entrega.")
    return 0


def laco_principal(args: argparse.Namespace, cal: Calibracao) -> int:
    """Captura, le, decide e entrega — nesta ordem, a 1 Hz.

    O laco e a prova de falhas: uma excecao em qualquer etapa vira log e a
    proxima iteracao acontece. Um scanner que morre calado e pior do que nenhum
    scanner, porque a party aprende a confiar num silencio que nao significa
    mais nada.
    """
    if args.replay:
        fonte = ReplaySource(Path(args.replay))
        log.info("Reproduzindo %s (%d frames)", args.replay, len(fonte))
    elif args.janela:
        # Captura a janela do jogo direto, em vez do desktop composto: assim
        # cobrir o jogo com o navegador nao cega mais o scanner.
        # A regiao relativa a janela sobrevive a arrastar o jogo; a de
        # desktop so vale enquanto ele nao se mexer.
        regiao = cal.party_window_na_janela or cal.party_window
        if cal.party_window_na_janela is None:
            log.warning(
                "Esta calibracao e antiga e nao guarda a posicao dentro da "
                "janela. Vai funcionar, mas ARRASTAR o jogo quebra a leitura. "
                "Rode calibrar.bat para corrigir."
            )
        extras = {"hp_proprio": cal.hp_proprio} if cal.hp_proprio else None
        fonte = JanelaSource(
            args.janela,
            regiao,
            relativa=cal.party_window_na_janela is not None,
            extras=extras,
        )
        log.info("Lendo a janela '%s' — funciona com o jogo coberto", args.janela)
        log.info("Janela MINIMIZADA continua sem funcionar: o Windows para de "
                 "produzir frames e nao ha API que contorne isso.")
    else:
        # No caminho do desktop a barra propria esta em coordenadas da
        # JANELA, entao so da para captura-la pelo caminho --janela.
        fonte = MssSource(cal.party_window)
        if cal.hp_proprio:
            log.warning(
                "A barra do seu personagem so e lida com --janela. "
                "Sem ela, a SUA morte nao sera detectada."
            )
        log.info("Lendo o desktop — o jogo precisa estar visivel. "
                 "Use --janela para funcionar com ele coberto.")

    gravador = Gravador(PASTA_GRAVACOES, args.rotulo) if args.record else None
    if gravador:
        log.info("Gravando em %s", gravador.pasta)

    rastreador = Rastreador(
        nomes=list(cal.nomes),
        nome_proprio=cal.nome_proprio,
        nomes_reservados=cal.nomes_com_assinatura,
    )
    despachante = montar_despachante(args)
    if despachante:
        despachante.iniciar()

    todos = list(cal.nomes)
    if cal.nome_proprio and cal.hp_proprio:
        todos.append(f"{cal.nome_proprio} (voce)")
    nomes = ", ".join(todos) if todos else "(sem lista configurada)"
    log.info("Monitorando: %s", nomes)

    # Aperto de mao inicial: e o que faz o silencio significar alguma coisa.
    # Sem ele, "nao recebi nada" e ambiguo entre "esta tudo bem" e "o scanner
    # nem esta rodando".
    if despachante and not args.sem_aviso_de_inicio:
        despachante.despachar(f"Scanner ativo — monitorando {nomes}.")

    contagem = {estado: 0 for estado in SaudeDoFrame}
    saude_anterior = None
    ultimo_status = 0.0
    erros_seguidos = 0
    total_eventos = 0
    ultima_observacao = None
    ticks_cego = 0

    try:
        while True:
            inicio = time.monotonic()

            try:
                frame = fonte.capturar()
            except StopIteration:
                log.info("Fim da sessao gravada")
                break
            except Exception:
                erros_seguidos += 1
                log.exception("Erro na captura (seguidos: %d)", erros_seguidos)
                if erros_seguidos >= 10:
                    log.error("10 erros seguidos — encerrando para nao rodar cego")
                    return 1
                time.sleep(args.intervalo)
                continue

            erros_seguidos = 0
            contagem[frame.saude] += 1

            if frame.saude is not saude_anterior:
                if frame.saude is SaudeDoFrame.FALHA_DE_CAPTURA:
                    log.warning("Falha de captura — sem visao, nada sera alertado")
                elif frame.saude is SaudeDoFrame.CONGELADO:
                    log.warning("Imagem congelada — jogo travado ou captura presa")
                saude_anterior = frame.saude

            if gravador:
                gravador.gravar(frame, time.time())

            try:
                observacao = extrair(frame, cal)
                # O estado do CLIENTE vem da fonte, nao da analise de pixels da
                # party window: o titulo da janela e sinal do Windows, e o
                # dialogo de desconexao aparece longe da regiao calibrada. So a
                # captura por janela tem as duas coisas.
                if hasattr(fonte, "estado_do_cliente"):
                    observacao = replace(
                        observacao, estado_do_cliente=fonte.estado_do_cliente()
                    )
                # Num replay o tempo vem do arquivo, nao do relogio: e o que
                # faz uma sessao de uma hora produzir os mesmos eventos ao ser
                # reproduzida em trinta segundos.
                momento = frame.momento if frame.momento is not None else time.time()
                eventos = rastreador.observar(observacao, momento)
                ultima_observacao = observacao
            except Exception:
                log.exception("Erro ao analisar o frame — seguindo")
                time.sleep(args.intervalo)
                continue

            # Cego por muito tempo com o jogo bem ali na frente quase sempre
            # significa calibracao errada, nao alt-tab. Vale dizer isso em vez
            # de deixar o usuario olhando "SEM VISAO" sem saber o porque.
            if not observacao.ui_visivel:
                ticks_cego += 1
                if ticks_cego == TICKS_CEGO_PARA_SUGERIR_RECALIBRAR:
                    log.warning(
                        "Sem visao da party ha %d leituras seguidas. Se o jogo "
                        "esta aberto e a party window visivel, ela pode ter "
                        "sido ARRASTADA ou o jogo REDIMENSIONADO — nesse caso "
                        "rode calibrar.bat de novo.",
                        ticks_cego,
                    )
            else:
                ticks_cego = 0

            for evento in eventos:
                total_eventos += 1

                # No console, direto e em destaque: o usuario esta na frente da
                # tela e pode conferir no jogo agora mesmo.
                hora = datetime.fromtimestamp(evento.momento).strftime("%H:%M:%S")
                log.info(
                    "%s", destacar(formatar_console(evento), evento.tipo, hora)
                )

                # No WhatsApp, cauteloso: quem le esta longe e nao tem como
                # conferir, entao a redacao precisa sobreviver a um erro.
                if despachante:
                    despachante.despachar(formatar(evento))

            agora = time.monotonic()
            if agora - ultimo_status >= args.status_a_cada:
                log.info("\n%s", desenhar_status(rastreador, cal, observacao))
                ultimo_status = agora

            dormir = args.intervalo - (time.monotonic() - inicio)
            if dormir > 0:
                time.sleep(dormir)

    except KeyboardInterrupt:
        log.info("Encerrado pelo usuario")

    finally:
        # Estado final sempre, independente do intervalo de status: num replay
        # rapido o intervalo de relogio nunca fecha, e o usuario ficaria sem
        # saber como a sessao terminou.
        if ultima_observacao is not None:
            log.info("Estado final:\n%s", desenhar_status(rastreador, cal, ultima_observacao))

        fonte.fechar()
        if gravador:
            gravador.fechar()
            log.info(
                "Sessao gravada: %d frames em %s",
                gravador.frames_gravados,
                gravador.pasta,
            )

        if despachante:
            if not args.sem_aviso_de_inicio:
                despachante.despachar("Scanner encerrado — nao estou mais vigiando.")
            despachante.encerrar()
            log.info(
                "Entrega: %d enviados, %d falharam",
                despachante.entregues,
                despachante.falhados,
            )

        total = sum(contagem.values())
        if total:
            log.info(
                "Resumo: %d frames (%d ok, %d falha de captura, %d congelados), "
                "%d eventos",
                total,
                contagem[SaudeDoFrame.OK],
                contagem[SaudeDoFrame.FALHA_DE_CAPTURA],
                contagem[SaudeDoFrame.CONGELADO],
                total_eventos,
            )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="l2scanner",
        description="Vigia a party window do Lineage 2 e avisa no WhatsApp.",
    )
    parser.add_argument(
        "--test-alert",
        action="store_true",
        dest="test_alert",
        help="envia um alerta de teste e sai (nao precisa do jogo aberto)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="mostra os alertas no console sem enviar nada",
    )
    parser.add_argument(
        "--record", action="store_true", help="grava a sessao em disco"
    )
    parser.add_argument("--rotulo", help="nome para identificar a gravacao")
    parser.add_argument(
        "--replay", help="reproduz uma pasta de sessao gravada, sem o jogo"
    )
    parser.add_argument(
        "--janela",
        nargs="?",
        const="AUTO",
        help=(
            "le a janela do jogo direto, funcionando com ela coberta por "
            "outras janelas. Sem valor, escolhe a unica janela do XM "
            "Essence aberta. Nao funciona com a janela minimizada."
        ),
    )
    parser.add_argument(
        "--intervalo",
        type=float,
        default=INTERVALO_PADRAO,
        help=f"segundos entre capturas (padrao: {INTERVALO_PADRAO})",
    )
    parser.add_argument(
        "--status-a-cada",
        type=float,
        default=30.0,
        dest="status_a_cada",
        help="segundos entre blocos de status no console",
    )
    parser.add_argument(
        "--sem-aviso-de-inicio",
        action="store_true",
        dest="sem_aviso_de_inicio",
        help="nao avisar no WhatsApp ao iniciar e encerrar",
    )
    parser.add_argument("-v", "--verboso", action="store_true", help="log detalhado")

    args = parser.parse_args()
    configurar_log(args.verboso)

    log.debug("Consciencia de DPI: %s", _MODO_DPI)
    if _MODO_DPI.startswith("FALHOU"):
        log.warning(
            "Nao consegui declarar consciencia de DPI. Se a escala de tela nao "
            "for 100%%, as coordenadas podem sair deslocadas."
        )

    if args.test_alert:
        return comando_teste_de_alerta(args)

    janela_pedida = args.janela == "AUTO"

    try:
        cal = Calibracao.carregar(ARQUIVO_CALIBRACAO)
        # Sessao gravada foi feita noutra hora; conferir a tela de agora nao faz
        # sentido nesse caso.
        if not args.replay:
            cal.conferir_geometria(descrever_geometria_da_tela())
    except CalibracaoInvalida as erro:
        log.error("%s", erro)
        return 2

    if janela_pedida:
        # A calibracao sabe a qual cliente a party window pertence. Com duas
        # instancias abertas, adivinhar significaria vigiar o char errado.
        if cal.janela:
            args.janela = cal.janela
        else:
            janelas = listar_janelas_do_jogo()
            if not janelas:
                log.error("Nenhuma janela do jogo aberta. O jogo esta rodando?")
                return 2
            if len(janelas) > 1:
                log.error("Ha mais de uma janela do jogo aberta:")
                for titulo in janelas:
                    log.error('   --janela "%s"', titulo)
                log.error("Escolha uma, ou recalibre para gravar qual e.")
                return 2
            args.janela = janelas[0]

    try:
        return laco_principal(args, cal)
    except JanelaNaoEncontrada as erro:
        log.error("%s", erro)
        return 2


if __name__ == "__main__":
    sys.exit(main())
