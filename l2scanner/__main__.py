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
from datetime import datetime, timedelta  # noqa: E402
from logging.handlers import RotatingFileHandler  # noqa: E402
from pathlib import Path  # noqa: E402

from .calibracao import (  # noqa: E402
    Calibracao,
    CalibracaoInvalida,
    descrever_geometria_da_tela,
)
from .agenda import (  # noqa: E402
    Aviso,
    JanelaDeSilencio,
    chave_da_ocorrencia,
    ocorrencias_cancelaveis,
    RegistroEmDisco,
    TipoDeAviso,
    avisos_devidos,
    HORAS_PARA_CANCELAR_ANTECIPADO,
    proxima_ocorrencia,
    silencio_ativo,
    texto_de_cancelamento,
    texto_de_encerramento,
    texto_do_aviso,
)
from .config import ConfigAusente, config_do_chatwoot, ler_agenda  # noqa: E402
from .captura_janela import (  # noqa: E402
    JanelaNaoEncontrada,
    JanelaSource,
    listar_janelas_do_jogo,
)
from .comandos import (  # noqa: E402
    Comando,
    LeitorDeComandos,
    chave_da_mensagem,
    comandos_novos,
)
from .console import destacar  # noqa: E402
from .frames import MssSource, ReplaySource, SaudeDoFrame  # noqa: E402
from .gravador import Gravador  # noqa: E402
from .notificador import (  # noqa: E402
    USER_AGENT,
    Categoria,
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
# Marcadores de "este aviso ja saiu". Compartilhada pelas DUAS instancias
# que o usuario roda — e o que impede o grupo de receber tudo em dobro.
PASTA_AGENDA = RAIZ / ".agenda"

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


def desenhar_status(
    rastreador: Rastreador, cal: Calibracao, obs, silencio=None
) -> str:
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

    # MUTE-08. Um scanner calado precisa PARECER calado de proposito. Sem esta
    # linha, "nao chegou nada no WhatsApp" e ambiguo entre "esta tudo bem",
    # "estou em silencio de TvT" e "o scanner quebrou" — e depois de um dia
    # inteiro corrigindo alarme falso, a ambiguidade custa a confianca inteira.
    janela = getattr(silencio, "janela", None)
    if janela is not None:
        linhas.append(
            f"  SILENCIO DE {janela.evento.upper()} ate "
            f"{janela.fim.strftime('%H:%M')} — nada vai para o WhatsApp"
        )

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


class ControleDoSilencio:
    """Sabe se estamos calados agora, e avisa quando o silencio acaba.

    Vive fora dos dois lacos porque os dois precisam dele: o laco principal
    para calar os eventos do rastreador, e o `--so-agenda` para mandar a
    mensagem de encerramento mesmo sem estar vigiando ninguem.
    """

    def __init__(self, eventos, registro=None) -> None:
        self._eventos = eventos
        self._registro = registro
        self._janela: JanelaDeSilencio | None = None
        # Vimos ESTA janela comecar, ou ja subimos dentro dela?
        self._viu_comecar = False
        # Ja observamos ao menos um instante SEM silencio. Sem este terceiro
        # estado, "acabei de entrar na janela" e "subi ja dentro dela" sao
        # indistinguiveis — nos dois casos a janela anterior era None.
        self._esteve_fora = False

    @property
    def janela(self) -> JanelaDeSilencio | None:
        return self._janela

    def ativo(self) -> bool:
        return self._janela is not None

    def atualizar(self, agora) -> str | None:
        """Reavalia. Devolve a mensagem de encerramento, quando ela vence.

        COMECO FRIO: se o scanner sobe JA dentro de uma janela, ele entra em
        silencio mas nao anuncia o encerramento depois. Ele nunca viu o evento
        comecar, e anunciar o fim de algo que nao acompanhou seria inventar
        contexto que ele nao tem — o mesmo erro que produziu tres alarmes
        falsos de arranque mais cedo neste projeto.
        """
        antes = self._janela
        cancelados = self._registro.cancelados() if self._registro else frozenset()
        self._janela = silencio_ativo(agora, self._eventos, cancelados)

        if self._janela is None:
            saindo = antes is not None and self._viu_comecar
            self._viu_comecar = False
            self._esteve_fora = True
            if saindo:
                return texto_de_encerramento(antes)
        elif antes is None and self._esteve_fora:
            self._viu_comecar = True

        return None


def montar_leitor_de_comandos(args: argparse.Namespace):
    """Monta o caminho de ENTRADA, ou None quando ninguem configurou um.

    Vazio por padrao de proposito. Ouvir comando abre superficie de ataque, e
    isso nao pode acontecer por acidente de configuracao — precisa de alguem
    escrevendo CHATWOOT_CONVERSAS_COMANDO no .env.
    """
    if args.dry_run:
        return None
    try:
        config = config_do_chatwoot()
    except ConfigAusente:
        return None
    if not (config.conversas_de_comando or config.etiqueta_de_comando):
        return None

    leitor = LeitorDeComandos(
        url=config.url,
        conta=config.conta,
        token=config.token,
        conversas=config.conversas_de_comando,
        telefones=config.telefones_de_comando,
        etiqueta=config.etiqueta_de_comando,
        user_agent=USER_AGENT,
    )

    onde = []
    if config.conversas_de_comando:
        onde.append(f"{len(config.conversas_de_comando)} conversa(s) fixa(s)")
    if config.etiqueta_de_comando:
        onde.append(f"conversas com a etiqueta '{config.etiqueta_de_comando}'")
    log.info("Ouvindo comandos em: %s. Mande .status para conferir.", " e ".join(onde))

    if leitor.aberto_a_qualquer_um:
        # Nao e erro, e compatibilidade. Mas um scanner que obedece qualquer um
        # nao pode ser um estado que se descobre por acidente.
        log.warning(
            "COMANDOS ABERTOS: qualquer pessoa que escreva nessas conversas pode "
            "mandar no scanner."
        )
        log.warning(
            "Para restringir, ponha o seu numero em CHATWOOT_TELEFONES_COMANDO "
            "no .env."
        )
    else:
        log.info(
            "Comandos aceitos so de %d numero(s) autorizado(s).",
            len(config.telefones_de_comando),
        )
    return leitor


def atender_comandos(
    leitor,
    registro,
    eventos_agendados,
    despachante,
    agora: datetime,
    monotonico: float,
) -> None:
    """Le, obedece e confirma. Nunca levanta.

    DOIS RELOGIOS, E ELES NAO SAO INTERCAMBIAVEIS:

    - `agora` e um `datetime` de parede. E o que a agenda entende — "que horas
      sao" — e num replay ele vem do arquivo, nao do relogio.
    - `monotonico` e segundos corridos. E o que o limitador de taxa entende, e
      ele NAO pode vir do frame: num replay, uma sessao de uma hora reproduzida
      em trinta segundos marteleria a API do Chatwoot, ou nunca a consultaria.

    Passar um so parametro para os dois derrubou o scanner em producao com
    `TypeError: '>=' not supported between 'timedelta' and 'float'`. Os testes
    nao pegaram porque chamavam o leitor direto, com float — o erro so existia
    na COSTURA, que e onde os erros deste projeto moram.

    Uma falha no caminho de entrada nunca levanta: o trabalho do scanner e
    vigiar a party, e ouvir comando e um extra.
    """
    if leitor is None or not leitor.ativo:
        return

    for pedido in comandos_novos(
        leitor.ler(monotonico), registro.enviados(), leitor.telefones
    ):
        # Marca ANTES de agir. Se o processo morrer no meio, o pior caso e um
        # comando perdido — nao um comando obedecido em laco a cada tick.
        if not registro.marcar(chave_da_mensagem(pedido.id)):
            continue

        quem = pedido.autor or "alguem"
        log.info("Comando de %s: %s", quem, pedido.texto.strip())

        if pedido.comando is Comando.CANCELAR_SILENCIO:
            resposta = _obedecer_cancelar(registro, eventos_agendados, agora, quem)
        elif pedido.comando is Comando.STATUS:
            resposta = _obedecer_status(registro, eventos_agendados, agora)
        else:
            continue

        log.info(destacar(resposta))
        if despachante:
            despachante.despachar(resposta, Categoria.SEMPRE)


def _obedecer_cancelar(registro, eventos, agora, quem: str) -> str:
    candidatos = ocorrencias_cancelaveis(agora, eventos, registro.cancelados())
    if not candidatos:
        return f"{quem} pediu para cancelar, mas nao ha silencio ativo nem proximo."

    nome, inicio, rolando = candidatos[0]
    if not registro.cancelar(chave_da_ocorrencia(nome, inicio)):
        return f"O silencio do {nome} ja estava cancelado."
    return f"{quem} cancelou: " + texto_de_cancelamento(nome, inicio, rolando)


def _obedecer_status(registro, eventos, agora) -> str:
    janela = silencio_ativo(agora, eventos, registro.cancelados())
    proximo = proxima_ocorrencia(agora, eventos)
    partes = []
    if janela:
        partes.append(
            f"Em silencio de {janela.evento} ate {janela.fim.strftime('%H:%M')}"
        )
    else:
        partes.append("Vigiando normalmente")
    if proximo:
        partes.append(f"proximo: {proximo[0]} as {proximo[1].strftime('%H:%M')}")
    return "Scanner: " + ", ".join(partes) + "."


def comando_cancelar_silencio(args: argparse.Namespace) -> int:
    """Cancela o silencio de UMA ocorrencia — a que estiver rolando, ou a proxima.

    Existe porque o Prime cala por DUAS HORAS e nem todo dia o usuario vai
    fazer Prime. Sem isto, a unica saida seria editar o config.toml e
    reiniciar, o que desliga o silencio para sempre em vez de para hoje.

    Nao precisa do jogo aberto: e so um marcador em disco. As instancias do
    scanner que ja estiverem rodando o enxergam no proximo tick.
    """
    eventos = ler_agenda()
    if not eventos:
        log.error("Nao ha agenda no config.toml — nao ha silencio para cancelar.")
        return 2

    registro = RegistroEmDisco(PASTA_AGENDA)
    agora = datetime.now()
    candidatos = ocorrencias_cancelaveis(agora, eventos, registro.cancelados())

    if not candidatos:
        log.info("Nenhum silencio para cancelar agora.")
        proximo = proxima_ocorrencia(agora, eventos)
        if proximo:
            log.info(
                "O proximo e %s as %s. Da para cancelar a partir de %dh antes.",
                proximo[0],
                proximo[1].strftime("%d/%m %H:%M"),
                HORAS_PARA_CANCELAR_ANTECIPADO,
            )
        return 0

    # O primeiro e o que esta rolando, se houver — a escolha mais provavel de
    # quem esta pedindo para cancelar.
    nome, inicio, rolando = candidatos[0]
    chave = chave_da_ocorrencia(nome, inicio)

    if not registro.cancelar(chave):
        log.info("O silencio de %s ja estava cancelado.", nome)
        return 0

    if rolando:
        log.info(destacar(f"SILENCIO DE {nome.upper()} CANCELADO - alertas voltaram"))
    else:
        log.info(
            destacar(
                f"{nome.upper()} DE {inicio.strftime('%H:%M')} NAO VAI SILENCIAR HOJE"
            )
        )

    if len(candidatos) > 1:
        restantes = ", ".join(
            f"{n} {i.strftime('%H:%M')}" for n, i, _ in candidatos[1:]
        )
        log.info("Ainda da para cancelar: %s (rode de novo)", restantes)

    despachante = montar_despachante(args)
    if despachante:
        despachante.iniciar()
        despachante.despachar(texto_de_cancelamento(nome, inicio, rolando), Categoria.SEMPRE)
        despachante.encerrar()

    return 0


def laco_da_agenda(args: argparse.Namespace) -> int:
    """So o relogio. Sem jogo, sem calibracao, sem captura, sem rastreador.

    LACO SEPARADO DE PROPOSITO. Seria mais curto enfiar um `if` dentro do laco
    principal, e seria pior: aquele laco e o codigo mais critico do projeto e
    nao pode ganhar ramos que so existem para um modo. Aqui nao ha frame para
    dar errado, entao o corpo cabe em vinte linhas e nao tem como confundir.

    Isto e o que faz AGEN-05 valer: quem mais precisa do lembrete de TvT e
    justamente quem NAO esta online. Se o aviso dependesse do jogo aberto, ele
    so sairia para quem ja esta jogando.
    """
    eventos = ler_agenda()
    if not eventos:
        log.error(
            "Nao ha agenda para rodar. Crie um config.toml com pelo menos um "
            "[[evento]] — veja o exemplo comentado no repositorio."
        )
        return 2

    despachante = montar_despachante(args)
    if despachante:
        despachante.iniciar()

    registro = RegistroEmDisco(PASTA_AGENDA)
    silencio = ControleDoSilencio(eventos, registro)
    leitor = montar_leitor_de_comandos(args)

    nomes = ", ".join(e.nome for e in eventos)
    log.info("Modo agenda: vigiando o relogio, nao a tela. Eventos: %s", nomes)
    log.info("O jogo NAO precisa estar aberto. O PC, sim.")
    _anunciar_proximo(eventos)

    ultimo_anuncio = datetime.now()
    try:
        while True:
            agora = datetime.now()
            atender_comandos(
                leitor, registro, eventos, despachante, agora, time.monotonic()
            )
            encerrou = silencio.atualizar(agora)
            if encerrou:
                # Loga SEMPRE, despacha se houver para onde. Sem essa
                # separacao, quem roda sem .env e sem --dry-run perdia a
                # mensagem ate no console — silencio que nao deveria existir.
                log.info(destacar(encerrou))
                if despachante:
                    despachante.despachar(encerrou, Categoria.SEMPRE)

            for aviso in avisos_devidos(agora, eventos, registro.enviados()):
                if not registro.marcar(aviso.chave):
                    continue
                texto = texto_do_aviso(aviso)
                log.info(destacar(texto))
                if despachante:
                    # SEMPRE: o lembrete atravessa o silencio. De segunda a
                    # quinta o aviso do TvT das 21h40 cai dentro do silencio do
                    # Prime — sem isto, a funcionalidade se anula sozinha.
                    despachante.despachar(texto, Categoria.SEMPRE)

            # De hora em hora, repetir qual e o proximo. Um scanner que nao diz
            # quando vai falar de novo e indistinguivel de um scanner travado.
            if (agora - ultimo_anuncio).total_seconds() >= 3600:
                janela = silencio.janela
                if janela is not None:
                    log.info(
                        "Em silencio de %s ate %s — nada vai para o WhatsApp",
                        janela.evento,
                        janela.fim.strftime("%H:%M"),
                    )
                _anunciar_proximo(eventos)
                ultimo_anuncio = agora

            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        log.info("Encerrando o modo agenda.")
    finally:
        if despachante:
            despachante.encerrar()
    return 0


def _anunciar_proximo(eventos) -> None:
    """Diz no console qual e o proximo evento e quanto falta."""
    proximo = proxima_ocorrencia(datetime.now(), eventos)
    if not proximo:
        return
    nome, quando = proximo
    faltam = quando - datetime.now()
    horas, resto = divmod(int(faltam.total_seconds()), 3600)
    minutos = resto // 60
    log.info(
        "Proximo: %s as %s (em %dh%02dmin)",
        nome,
        quando.strftime("%d/%m %H:%M"),
        horas,
        minutos,
    )


def comando_teste_de_agenda(args: argparse.Namespace) -> int:
    """Despacha um aviso de exemplo agora, para nao ter que esperar as 15h."""
    eventos = ler_agenda()
    if not eventos:
        log.error("Nao ha agenda no config.toml para testar.")
        return 2

    proximo = proxima_ocorrencia(datetime.now(), eventos)
    if proximo is None:
        log.error("A agenda nao tem nenhuma ocorrencia futura.")
        return 2

    nome, quando = proximo
    exemplo = Aviso(
        evento=nome, tipo=TipoDeAviso.ANTES, alvo=quando,
        devido_em=quando - timedelta(minutes=10),
    )
    texto = texto_do_aviso(exemplo)

    despachante = montar_despachante(args)
    if despachante is None:
        log.error("Sem configuracao de entrega — nao ha o que testar.")
        return 1
    despachante.iniciar()
    despachante.despachar(texto)
    despachante.encerrar()

    if despachante.falhados:
        log.error("O envio falhou. Veja o erro acima.")
        return 1
    log.info("Enviado: %s", texto)
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

    # A AGENDA: a segunda fonte de eventos do projeto, e a primeira que nao
    # olha para a tela. Ela despacha pelo MESMO Despachante que o rastreador —
    # nunca chamando enviar() direto. E o seam que a Fase 7 vai usar para
    # silenciar; furar ele aqui tornaria o silenciamento impossivel de
    # acrescentar depois sem reescrever isto.
    eventos_agendados = ler_agenda()
    registro_da_agenda = RegistroEmDisco(PASTA_AGENDA)
    silencio = ControleDoSilencio(eventos_agendados, registro_da_agenda)
    leitor_de_comandos = montar_leitor_de_comandos(args)
    if despachante:
        # O corte mora no transporte, nao na deteccao: o rastreador segue
        # decidindo e registrando tudo normalmente, e o que muda e so o
        # que sai para o WhatsApp.
        despachante.em_silencio = silencio.ativo
    if eventos_agendados:
        proximo = proxima_ocorrencia(datetime.now(), eventos_agendados)
        if proximo:
            log.info(
                "Agenda: %d evento(s). Proximo: %s as %s",
                len(eventos_agendados),
                proximo[0],
                proximo[1].strftime("%d/%m %H:%M"),
            )

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

            # A AGENDA VEM ANTES DA EXTRACAO, e isso e de proposito.
            #
            # Ela nao depende de um unico pixel — o aviso vem do relogio. Se
            # ficasse depois do `try` da extracao, um erro de leitura faria o
            # `continue` engolir o lembrete de TvT junto, o que contradiz a
            # razao inteira de a agenda existir.
            #
            # O tempo vem do FRAME, nao do relogio de parede: num replay isso e
            # o que faz uma sessao gravada durante um TvT reproduzir o silencio
            # daquele TvT.
            momento = frame.momento if frame.momento is not None else time.time()
            agora_do_frame = datetime.fromtimestamp(momento)

            atender_comandos(
                leitor_de_comandos,
                registro_da_agenda,
                eventos_agendados,
                despachante,
                agora_do_frame,
                time.monotonic(),
            )
            encerrou = silencio.atualizar(agora_do_frame)
            if encerrou:
                log.info(destacar(encerrou))
                if despachante:
                    despachante.despachar(encerrou, Categoria.SEMPRE)

            for aviso in avisos_devidos(
                agora_do_frame, eventos_agendados, registro_da_agenda.enviados()
            ):
                if not registro_da_agenda.marcar(aviso.chave):
                    continue
                texto = texto_do_aviso(aviso)
                log.info(destacar(texto))
                if despachante:
                    # SEMPRE: o lembrete atravessa o silencio. De segunda a
                    # quinta o aviso do TvT das 21h40 cai dentro do silencio do
                    # Prime — sem isto, a funcionalidade se anula sozinha.
                    despachante.despachar(texto, Categoria.SEMPRE)

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
                # `momento` ja foi calculado acima, do FRAME e nao do relogio:
                # e o que faz uma sessao de uma hora produzir os mesmos eventos
                # ao ser reproduzida em trinta segundos.
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
                log.info(
                    "\n%s",
                    desenhar_status(rastreador, cal, observacao, silencio),
                )
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
            log.info("Estado final:\n%s", desenhar_status(rastreador, cal, ultima_observacao, silencio))

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
                "Entrega: %d enviados, %d falharam, %d silenciados por evento",
                despachante.entregues,
                despachante.falhados,
                despachante.silenciados,
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
    parser.add_argument(
        "--so-agenda",
        action="store_true",
        dest="so_agenda",
        help=(
            "roda SO os avisos de TvT/Prime, sem vigiar a party. "
            "Nao precisa do jogo aberto nem de calibracao."
        ),
    )
    parser.add_argument(
        "--testar-agenda",
        action="store_true",
        dest="testar_agenda",
        help="envia um aviso de agenda de exemplo e sai, sem esperar o horario",
    )
    parser.add_argument(
        "--cancelar-silencio",
        action="store_true",
        dest="cancelar_silencio",
        help=(
            "cancela o silencio que esta rolando (ou marca o proximo para nao "
            "silenciar). Nao precisa do jogo aberto."
        ),
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

    if args.testar_agenda:
        return comando_teste_de_agenda(args)

    if args.cancelar_silencio:
        return comando_cancelar_silencio(args)

    # O modo agenda sai ANTES de carregar calibracao e de procurar janela:
    # ele nao olha para a tela, entao exigir qualquer uma das duas seria
    # inventar um requisito que a funcionalidade nao tem.
    if args.so_agenda:
        return laco_da_agenda(args)

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
