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
import cv2  # noqa: E402
import logging  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
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
from .config import (  # noqa: E402
    ConfigAusente,
    config_do_chatwoot,
    ler_agenda,
    ler_membros,
)
from .captura_janela import (  # noqa: E402
    JanelaNaoEncontrada,
    JanelaSource,
    listar_janelas_do_jogo,
)
from .comandos import (  # noqa: E402
    Comando,
    LeitorDeComandos,
    chave_da_mensagem,
    colisoes_de_telefone,
    comandos_novos,
    texto_de_ajuda,
)
from .console import destacar, moldurar  # noqa: E402
from .loot import (  # noqa: E402
    RegistroDeLoot,
    exibir,
    nick_para_o_aviso,
    responder_atribuicao,
    responder_cancelamento,
    responder_consulta,
    responder_correcao,
    responder_designacao,
)
from . import ocr  # noqa: E402
from .frames import MssSource, Regiao, ReplaySource, SaudeDoFrame  # noqa: E402
from .manutencao import (  # noqa: E402
    SEGUNDOS_ENTRE_LEITURAS,
    VigiaDeManutencao,
    eh_banner_de_manutencao,
    interpretar_banner,
)
from .gravador import Gravador  # noqa: E402
from .notificador import (  # noqa: E402
    USER_AGENT,
    Categoria,
    Despachante,
    NotificadorChatwoot,
    NotificadorDeConsole,
    formatar_console,
)
from .presenca import (  # noqa: E402
    RespostaDePresenca,
    responder_join,
    responder_leave,
)
from .rastreador import EstadoDoMembro, PortaoGlobal, Rastreador  # noqa: E402
from .relogio import Relogio, fonte_chatwoot  # noqa: E402
from .sessao import Sessao  # noqa: E402
from .visao import EstadoDaLinha  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_CALIBRACAO = RAIZ / "calibration.json"
PASTA_GRAVACOES = RAIZ / "recordings"
PASTA_LOGS = RAIZ / "logs"
ARQUIVO_OUTBOX = RAIZ / "outbox.jsonl"
# Marcadores de "este aviso ja saiu". Compartilhada pelas DUAS instancias
# que o usuario roda — e o que impede o grupo de receber tudo em dobro.
PASTA_AGENDA = RAIZ / ".agenda"
# O registro de loot do Solo Boss. Pasta PROPRIA porque o RegistroEmDisco
# poda marcadores com prefixo de data em 3 dias — certo para "ja avisei",
# fatal para estatistica: "quantos loots o J4guar pegou" e para sempre.
PASTA_LOOT = RAIZ / ".loot"

INTERVALO_PADRAO = 1.0

# Quantas leituras cegas seguidas ate sugerir recalibrar. A 1 Hz sao ~30s:
# tempo demais para um alt-tab qualquer, curto o bastante para o usuario
# ainda lembrar do que mexeu.
TICKS_CEGO_PARA_SUGERIR_RECALIBRAR = 30

# Quantas leituras seguidas uma linha pode ficar OCUPADA e SEM NOME antes de o
# scanner reclamar. A 1 Hz sao ~2 minutos.
#
# Bem mais folgado que o de cegueira, e de proposito: o reconhecimento PISCA por
# natureza. Medido nas fixtures, ~20 a 40 pixels claros de cenario invadindo o
# recorte do nome, ou ~40% de perda do texto, ja cruzam o limiar de casamento —
# entao uma linha cair por alguns segundos e normal e nao merece aviso. Dois
# minutos parados nao sao piscada: sao um retrato que parou de casar.
TICKS_SEM_RECONHECER_PARA_AVISAR = 120

# Abaixo disto o desvio nao muda nada que o usuario perceba: a agenda
# trabalha em minutos. Acima, o aviso vira ruido util — e o numero que
# explica por que o TvT saiu na hora errada.
DESVIO_TOLERAVEL_SEGUNDOS = 60.0

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


def montar_vigia_de_manutencao(regiao) -> VigiaDeManutencao | None:
    """Liga o aviso de manutencao, ou explica por que nao ligou. Nunca levanta.

    Mesmo formato de `montar_despachante`: tenta, degrada com log, devolve None
    e deixa o scanner subir. O recurso e opcional; o scanner nao e.

    A DIFERENCA ENTRE OS DOIS LOGS E DELIBERADA. Sem regiao e uma escolha de
    modo (`mss` sem `banner_manutencao` configurado), entao `info` basta. Sem as
    bindings de OCR e um `.venv` desatualizado que o usuario CONSEGUE
    consertar — e se isso sair calado ele vai achar que esta coberto contra a
    proxima manutencao e nao esta.
    """
    if regiao is None:
        log.info(
            "Aviso de manutencao desligado: nao sei onde procurar o banner. "
            "Rode com --janela, ou configure a chave 'banner_manutencao' no "
            "calibration.json."
        )
        return None

    if not ocr.disponivel():
        log.warning(
            "Aviso de manutencao DESATIVADO — %s", ocr.motivo_indisponivel()
        )
        log.warning(
            "Todo o resto do scanner continua igual: morte, saida e "
            "ressurreicao seguem sendo detectadas e entregues."
        )
        return None

    # A LINHA DE ARRANQUE CONTA O ORCAMENTO, e nao so que o recurso ligou.
    # Quem le o log precisa saber o que este recurso vai custar de CPU antes de
    # o farm comecar — e a passada cara so aparecer durante a contagem e
    # justamente o que torna o custo aceitavel (D-e).
    log.info(
        "Aviso de manutencao ativo — lendo o banner em (%d,%d) %dx%d "
        "em duas escalas: cinza 2x a cada %.0fs (~23 ms medidos) e cinza 3x "
        "(~31 ms) so quando a primeira ve o banner. As duas precisam concordar.",
        regiao.esquerda, regiao.topo, regiao.largura, regiao.altura,
        SEGUNDOS_ENTRE_LEITURAS,
    )
    return VigiaDeManutencao(
        ler_texto=ocr.ler_texto,
        ler_texto_conferencia=ocr.ler_texto_ampliado,
    )


def _duracao_legivel(segundos: float) -> str:
    """Segundos viram "3h02min" — "10920s" nao ajuda ninguem a reconhecer o
    proprio problema de dual boot."""
    segundos = int(abs(segundos))
    horas, resto = divmod(segundos, 3600)
    minutos, sobra = divmod(resto, 60)
    if horas:
        return f"{horas}h{minutos:02d}min"
    if minutos:
        return f"{minutos}min{sobra:02d}s"
    return f"{sobra}s"


def montar_relogio(args: argparse.Namespace, fonte=None) -> Relogio:
    """Decide de onde vem a hora da agenda — e NUNCA levanta.

    Espelha `montar_despachante` de proposito: monta, degrada com WARNING, e
    deixa o scanner subir. Sem rede, sem .env e em --dry-run o usuario ainda
    tem que ver o proximo TvT; a fonte de hora nao pode virar mais um motivo
    para o produto nao abrir.

    `fonte` entra por parametro pela mesma disciplina de `agenda.py` e de
    `relogio.py`: e o que permite testar o arranque offline sem tocar no .env
    real do usuario nem encostar na rede.
    """
    if fonte is None:
        try:
            config = config_do_chatwoot()
        except ConfigAusente:
            log.warning(
                "Sem .env do Chatwoot: a hora vem do relogio do Windows, nao "
                "do servidor. Se voce acabou de voltar do Linux, o horario de "
                "TvT/Prime pode sair errado."
            )
            return Relogio()
        fonte = fonte_chatwoot(config.url)

    relogio = Relogio(fonte=fonte)

    # Sincrono e ANTES do laco, de proposito. Se a primeira volta rodasse com
    # o relogio torto, ela poderia gravar um marcador de "ja avisei" com a
    # chave errada — e o marcador e DURAVEL, entao envenenaria o aviso de
    # verdade horas depois.
    if not relogio.sincronizar():
        log.warning("A hora do servidor nao veio — usando o relogio do Windows.")
        log.warning(
            "Se voce acabou de voltar do Linux, o horario de TvT/Prime pode "
            "sair errado ate o Windows se corrigir sozinho."
        )
        return relogio

    desvio = relogio.desvio_do_windows() or 0.0
    if abs(desvio) > DESVIO_TOLERAVEL_SEGUNDOS:
        direcao = "ADIANTADO" if desvio > 0 else "ATRASADO"
        log.warning(
            "O relogio do Windows esta %s %s em relacao ao servidor — a "
            "agenda vai usar a hora do servidor.",
            direcao,
            _duracao_legivel(desvio),
        )
        log.warning(
            "Causa provavel: dual boot. O Linux grava o relogio do hardware "
            "em UTC e o Windows le o mesmo valor como hora local."
        )
    else:
        log.info("Hora ancorada no servidor (o relogio da maquina confere).")

    relogio.iniciar_sincronizacao_periodica()
    return relogio


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

    # No solo, "SEM VISAO" seria mentira por omissao: o scanner nao perdeu
    # nada, nao ha party para ver. Ele esta vigiando VOCE, e o console tem que
    # dizer isso — senao parece quebrado justamente quando esta trabalhando.
    if getattr(rastreador, "modo_solo", False):
        portao = "SOLO - vigiando so voce" 

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

    # O SEGUNDO nivel de autorizacao. Vem do config.toml e nao do .env porque
    # telefone de party-mate nao e segredo — ver o comentario de `ler_membros`.
    # Um bloco `[[membro]]` mal escrito levanta `AgendaInvalida` e derruba o
    # scanner AQUI, com o usuario olhando para o console, que e a unica hora em
    # que ele consegue consertar.
    membros = ler_membros()

    leitor = LeitorDeComandos(
        url=config.url,
        conta=config.conta,
        token=config.token,
        conversas=config.conversas_de_comando,
        telefones=config.telefones_de_comando,
        etiqueta=config.etiqueta_de_comando,
        user_agent=USER_AGENT,
        membros=membros,
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
            "no .env. Para dar so .join/.leave aos party-mates, use os blocos "
            "[[membro]] do config.toml."
        )
    else:
        log.info(
            "Comandos aceitos so de %d numero(s) autorizado(s).",
            len(config.telefones_de_comando),
        )

    # Mesmo motivo do aviso COMANDOS ABERTOS logo acima: quem pode mandar no
    # scanner nao pode ser um estado que se descobre por acidente. Aqui isso
    # vale para o nivel novo — quantos party-mates ganharam .join e .leave.
    if membros:
        log.info(
            "Presenca: %d party-mate(s) podem dar .join/.leave (%s). Nenhum "
            "deles alcanca comando de loot.",
            len(membros),
            ", ".join(m.nick for m in membros),
        )

    for primeiro, segundo in colisoes_de_telefone(config.telefones_de_comando, membros):
        # NAO derruba o scanner, e a proporcao e deliberada: uma colisao entre
        # dois MEMBROS nao escala privilegio nenhum, e recusar a subir por
        # causa dela deixaria o usuario sem vigia por um erro de digitacao. Um
        # aviso alto, nomeando as duas linhas, e o que ele consegue consertar.
        log.warning(
            "TELEFONES AMBIGUOS: '%s' e '%s' terminam nos mesmos 8 digitos e o "
            "scanner nao consegue distinguir os dois.",
            primeiro,
            segundo,
        )
        log.warning(
            "Se um deles for de CHATWOOT_TELEFONES_COMANDO e o outro de um "
            "[[membro]], aquele party-mate alcanca TODOS os comandos, "
            "inclusive .corrigir e .pegou. Troque um dos dois."
        )
    return leitor


def _para_o_console(resposta: str) -> str:
    """A resposta como ela deve aparecer no console e no `scanner.log`.

    UMA RESPOSTA DE VARIAS LINHAS NAO PODE SER MOLDURADA. `moldurar` monta
    `largura = max(LARGURA, len(miolo) + len(carimbo))` sobre a string
    INTEIRA, com as quebras de linha dentro dela: um texto de dezenove linhas
    vira uma borda de centenas de asteriscos no console e no `scanner.log`, e
    a borda desalinhada parece defeito e rouba a atencao do que importa.

    E a mesma razao de D-04 do lado do WhatsApp, aplicada ao SEGUNDO destino.
    Uma regra so para os dois, e nao um caso especial para o `.help` — assim a
    proxima resposta de varias linhas ja nasce certa.
    """
    if "\n" in resposta:
        return resposta
    return destacar(resposta)


def atender_comandos(
    leitor,
    registro,
    eventos_agendados,
    despachante,
    agora: datetime,
    monotonico: float,
    rastreador=None,
    loot=None,
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
        leitor.ler(monotonico),
        registro.enviados(),
        leitor.telefones,
        nicks_conhecidos=loot.nicks_conhecidos() if loot else frozenset(),
        # O ELO DO SEGUNDO NIVEL DE AUTORIZACAO. Sem esta linha, `Membro`,
        # `nick_do_membro`, `COMANDOS_DE_MEMBRO` e os blocos `[[membro]]` do
        # config.toml existem, tem teste verde, e o scanner fica MUDO para os
        # party-mates: `autorizado_para` recebe a tupla vazia por default e
        # recusa todo mundo que nao seja dono. E daqui tambem que sai o
        # `pedido.nick` — o nick do JOGO, que o `.join` poe na lista.
        membros=leitor.membros,
    ):
        # Marca ANTES de agir. Se o processo morrer no meio, o pior caso e um
        # comando perdido — nao um comando obedecido em laco a cada tick.
        if not registro.marcar(chave_da_mensagem(pedido.id)):
            continue

        quem = pedido.autor or "alguem"
        log.info("Comando de %s: %s", quem, pedido.texto.strip())

        if pedido.comando is Comando.CANCELAR_SILENCIO:
            resposta = _obedecer_cancelar(registro, eventos_agendados, agora, quem)
            # CANCELAR muda o que o GRUPO recebe: todo mundo tinha parado de
            # ser avisado por causa daquele silencio. Quem pediu merece a
            # confirmacao, e o grupo precisa saber que voltou.
            avisar_o_grupo = True
        elif pedido.comando is Comando.STATUS:
            resposta = _obedecer_status(
                registro, eventos_agendados, agora, rastreador
            )
            # STATUS e pergunta pessoal. Ecoar no grupo seria ruido para quem
            # nao perguntou nada.
            avisar_o_grupo = False
        elif pedido.comando in (Comando.SOLO, Comando.PARTY):
            solo = pedido.comando is Comando.SOLO
            resposta = _obedecer_modo(rastreador, solo, quem)
            # Muda o que o GRUPO vai receber daqui pra frente: em solo o
            # scanner para de falar sobre a party. Todo mundo merece saber.
            avisar_o_grupo = True
        elif pedido.comando is Comando.LOOT_DESIGNAR:
            if loot is None:
                resposta = "Nao consigo mexer no loot agora."
            else:
                resposta = responder_designacao(
                    loot, eventos_agendados, agora, pedido.argumento
                )
            # O grupo vai ficar sabendo pelo proprio aviso de antecedencia,
            # que sai com "Loot: X" no fim. Ecoar agora seria dizer a mesma
            # coisa duas vezes — e o grupo nem entrega incoming; os comandos
            # chegam pelo privado.
            avisar_o_grupo = False
        elif pedido.comando is Comando.LOOT_CANCELAR:
            if loot is None:
                resposta = "Nao consigo mexer no loot agora."
            else:
                resposta = responder_cancelamento(loot, eventos_agendados, agora)
            # Mesmo racional do LOOT_DESIGNAR logo acima: o grupo fica sabendo
            # pelo proprio aviso de antecedencia, que agora sai SEM a linha
            # "Loot:". Ecoar aqui seria dizer a mesma coisa duas vezes.
            avisar_o_grupo = False
        elif pedido.comando is Comando.LOOT_CORRIGIR:
            if loot is None:
                resposta = "Nao consigo mexer no loot agora."
            else:
                resposta = responder_correcao(
                    loot, eventos_agendados, agora, pedido.argumento
                )
            # Sem eco no grupo, e o motivo aqui e PROPRIO deste ramo: corrigir
            # historico e conserto de contabilidade entre quem ja sabe o que
            # aconteceu no boss. Anunciar no grupo que o loot mudou de dono
            # convidaria exatamente a discussao que o registro existe para
            # encerrar — e quem quiser conferir tem o `.<nick>`.
            avisar_o_grupo = False
        elif pedido.comando is Comando.LOOT_ATRIBUIR:
            if loot is None:
                resposta = "Nao consigo mexer no loot agora."
            else:
                resposta = responder_atribuicao(
                    loot, eventos_agendados, agora, pedido.argumento
                )
            # Sem eco no grupo, e o motivo aqui e PROPRIO deste ramo:
            # registrar loot de um boss que ja passou e conserto de
            # contabilidade entre quem ja estava la e ja sabe o que aconteceu.
            # A confirmacao com o DIA nao serve ao grupo — ela serve a quem
            # digitou, para conferir na hora que acertou o boss, e e por isso
            # que ela precisa chegar onde a pergunta foi feita.
            avisar_o_grupo = False
        elif pedido.comando is Comando.AJUDA:
            resposta = texto_de_ajuda()
            # Pergunta pessoal, mesmo racional ja escrito no ramo do `.status`
            # — e aqui ele pesa mais: sao dezenove linhas. Ecoar a lista
            # inteira no grupo seria despejar um mural de comandos no celular
            # de quem nao perguntou nada.
            avisar_o_grupo = False
        elif pedido.comando is Comando.LOOT_CONSULTA:
            if loot is None:
                resposta = "Nao consigo mexer no loot agora."
            else:
                resposta = responder_consulta(loot, pedido.argumento, agora)
            # Pergunta pessoal, mesmo racional do .status.
            avisar_o_grupo = False
        elif pedido.comando is Comando.JOIN:
            # `pedido.nick` pode ser None — e o DONO que nao se declarou
            # `[[membro]]`, cujo pedido chega porque o nivel de dono alcanca
            # todo comando. O None e repassado inteiro: quem responde e o
            # `presenca.py`, que ja tem esse ramo. Inventar aqui um nick a
            # partir do `sender.name` do Chatwoot poria na lista da party um
            # nome de CONTATO que nao e personagem de ninguem (D-10).
            resposta = responder_join(
                registro, eventos_agendados, agora, pedido.nick
            )
        elif pedido.comando is Comando.LEAVE:
            resposta = responder_leave(
                registro, eventos_agendados, agora, pedido.nick
            )
        else:
            continue

        # UMA LINGUA SO PARA O BLOCO DE DESPACHO: privado mais grupo-ou-None.
        #
        # Os ramos acima produzem `(str, bool)`; os dois de presenca produzem
        # `RespostaDePresenca`. Traduzir os antigos AQUI, num lugar so, em vez
        # de reescrever os oito — o bloco de despacho e o funil por onde TODA
        # resposta de comando passa, e um erro nele nao quebra um recurso: ele
        # muda o destino de todos ao mesmo tempo, em silencio (a mensagem
        # chega, no lugar errado). `tests/test_presenca.py` tem a tabela dos
        # destinos de cada ramo antigo, escrita e verde ANTES desta conversao.
        #
        # `avisar_o_grupo = True` vira "o grupo recebe o MESMO texto do
        # privado", que e exatamente o que ele ja significava.
        if not isinstance(resposta, RespostaDePresenca):
            resposta = RespostaDePresenca(
                privado=resposta,
                grupo=resposta if avisar_o_grupo else None,
            )

        # PRIMEIRA VEZ NO PROJETO EM QUE OS DOIS DESTINOS RECEBEM REDACOES
        # DIFERENTES (D-09), e a lista de presenca e a razao. Ate aqui, ecoar
        # o mesmo texto bastava porque todo comando ecoado mudava algo que o
        # grupo inteiro ja estava vivendo. No `.join` os leitores sao outros:
        # quem digitou precisa saber que CHEGOU — sem esse eco privado, um
        # `.join` recusado por autorizacao e um que funcionou sao
        # indistinguiveis na tela dele, os dois produzem silencio — e o grupo
        # precisa do NICK e do HORARIO, nao de "anotado, voce esta na lista".
        log.info(_para_o_console(resposta.privado))
        if resposta.grupo is not None and resposta.grupo != resposta.privado:
            # Cada um na SUA linha, e cada um pela `_para_o_console`: a regra
            # de nao moldurar texto com quebra de linha vale para os dois.
            log.info(_para_o_console(resposta.grupo))

        if not despachante:
            continue

        # RESPONDE ONDE PERGUNTARAM. Sem isto, um `.status` mandado no privado
        # era respondido no grupo — medido ao vivo: pergunta as 23:04:42 na
        # conversa 1, resposta as 23:04:52 na 13, e o usuario achou que nao
        # tinha funcionado.
        if pedido.conversa:
            despachante.despachar(
                resposta.privado, Categoria.SEMPRE, pedido.conversa
            )
            if resposta.grupo is not None:
                despachante.despachar(resposta.grupo, Categoria.SEMPRE)
        else:
            # Sem conversa de origem sai UMA mensagem so, a do privado, e ela
            # cai no grupo: melhor responder em algum lugar do que em nenhum.
            # Mandar tambem a redacao de grupo aqui faria o mesmo evento
            # aparecer duas vezes no MESMO destino.
            despachante.despachar(resposta.privado, Categoria.SEMPRE)


def _obedecer_cancelar(registro, eventos, agora, quem: str) -> str:
    candidatos = ocorrencias_cancelaveis(agora, eventos, registro.cancelados())
    if not candidatos:
        return f"{quem} pediu para cancelar, mas nao ha silencio ativo nem proximo."

    nome, inicio, rolando = candidatos[0]
    if not registro.cancelar(chave_da_ocorrencia(nome, inicio)):
        return f"O silencio do {nome} ja estava cancelado."
    return f"{quem} cancelou: " + texto_de_cancelamento(nome, inicio, rolando)


def _obedecer_modo(rastreador, solo: bool, quem: str) -> str:
    """Liga ou desliga o modo solo, sem reiniciar nada.

    E o comando que mais faz sentido vir do WhatsApp: a hora de virar solo e
    quando a party se desfaz, e nesse momento o usuario esta no jogo, nao na
    frente do console.
    """
    if rastreador is None:
        return "Nao consigo trocar de modo agora."
    if rastreador.modo_solo == solo:
        atual = "solo" if solo else "party"
        return f"Ja estava no modo {atual}."

    rastreador.modo_solo = solo
    if solo:
        nome = rastreador.nome_proprio or "voce"
        return (
            f"{quem} ligou o modo SOLO. Vou vigiar so o {nome} e parar de "
            f"falar sobre a party. Avisos de TvT e Prime continuam."
        )
    return (
        f"{quem} desligou o modo solo. Voltei a vigiar a party inteira."
    )


def _obedecer_status(registro, eventos, agora, rastreador=None) -> str:
    janela = silencio_ativo(agora, eventos, registro.cancelados())
    proximo = proxima_ocorrencia(agora, eventos)
    partes = []
    if getattr(rastreador, "modo_solo", False):
        nome = getattr(rastreador, "nome_proprio", None) or "voce"
        partes.append(f"modo SOLO, vigiando so o {nome}")
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
    # Processo SEPARADO do scanner, entao monta o proprio relogio: com o
    # relogio do Windows adiantado, --cancelar-silencio escolheria a
    # ocorrencia errada e calaria justamente a que o usuario queria ouvir.
    relogio = montar_relogio(args)
    agora = relogio.agora()
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
    registro_de_loot = RegistroDeLoot(PASTA_LOOT)
    silencio = ControleDoSilencio(eventos, registro)
    leitor = montar_leitor_de_comandos(args)
    # Este e o modo de quem NAO esta com o jogo aberto: aqui o relogio e
    # 100% do produto. Um erro de 3h nao atrasa o aviso, ele o APAGA.
    relogio = montar_relogio(args)

    nomes = ", ".join(e.nome for e in eventos)
    log.info("Modo agenda: vigiando o relogio, nao a tela. Eventos: %s", nomes)
    log.info("O jogo NAO precisa estar aberto. O PC, sim.")
    _anunciar_proximo(eventos, relogio)

    ultimo_anuncio = relogio.agora()
    try:
        while True:
            agora = relogio.agora()
            atender_comandos(
                leitor, registro, eventos, despachante, agora,
                time.monotonic(), loot=registro_de_loot,
            )
            encerrou = silencio.atualizar(agora)
            if encerrou:
                # Loga SEMPRE, despacha se houver para onde. Sem essa
                # separacao, quem roda sem .env e sem --dry-run perdia a
                # mensagem ate no console — silencio que nao deveria existir.
                log.info(destacar(encerrou, hora=agora.strftime("%H:%M")))
                if despachante:
                    despachante.despachar(encerrou, Categoria.SEMPRE)

            # A designacao de loot entra no aviso de antecedencia do Solo
            # Boss. Lida antes do loop, para todos os avisos deste tick
            # enxergarem a mesma.
            designacao = registro_de_loot.designacao()
            for aviso in avisos_devidos(agora, eventos, registro.enviados()):
                if not registro.marcar(aviso.chave):
                    continue
                texto = texto_do_aviso(aviso, nick_para_o_aviso(aviso, designacao))
                log.info(destacar(texto, hora=agora.strftime("%H:%M")))
                if despachante:
                    # A MESMA moldura do console vai para o celular. O aviso
                    # concorre com a conversa do grupo, e uma linha solta no
                    # meio de cem passa batido — o bloco nao passa.
                    # SEMPRE: o lembrete atravessa o silencio. De segunda a
                    # quinta o aviso do TvT das 21h40 cai dentro do silencio do
                    # Prime — sem isto, a funcionalidade se anula sozinha.
                    despachante.despachar(
                        moldurar(texto, agora.strftime("%H:%M")), Categoria.SEMPRE
                    )

            # O horario do boss passou com designacao ativa: registra e some.
            # SO LOG, sem WhatsApp: o Solo Boss ja e 12 ocorrencias/dia, e a
            # disciplina de volume da agenda vale aqui tambem.
            consumida = registro_de_loot.consumir(agora)
            if consumida:
                log.info(
                    destacar(
                        f"Loot do Solo Boss das "
                        f"{consumida.alvo.strftime('%H:%M')} registrado para "
                        f"{exibir(consumida.nick)}"
                    )
                )

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
                _anunciar_proximo(eventos, relogio)
                ultimo_anuncio = agora

            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        log.info("Encerrando o modo agenda.")
    finally:
        if despachante:
            despachante.encerrar()
    return 0


def _anunciar_proximo(eventos, relogio: Relogio) -> None:
    """Diz no console qual e o proximo evento e quanto falta.

    O relogio entra por parametro em vez de ser lido aqui dentro: e o que
    impede esta funcao de ser a ultima do arquivo a perguntar as horas ao
    Windows.
    """
    agora = relogio.agora()
    proximo = proxima_ocorrencia(agora, eventos)
    if not proximo:
        return
    nome, quando = proximo
    faltam = quando - agora
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

    relogio = montar_relogio(args)
    proximo = proxima_ocorrencia(relogio.agora(), eventos)
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


def comando_testar_manutencao(args: argparse.Namespace, cal: Calibracao) -> int:
    """Mostra o que o OCR le no banner AGORA (D-13).

    Esta ferramenta existe por causa de um risco declarado: a precisao do OCR
    na FONTE DO JOGO nunca foi provada. O spike leu um banner sintetico, nao um
    banner de verdade. So uma manutencao real prova o resto — e sem esta
    ferramenta o usuario nao teria como conferir sozinho quando ela acontecer.

    Por isso ela mostra as TRES coisas separadas: qual regiao usou, que pixels
    pegou (o PNG em disco) e o que o OCR e o parser entenderam. Quando algo
    falhar, essas tres respostas dizem QUAL das tres etapas falhou.
    """
    regiao = cal.regiao_do_banner(na_janela=bool(args.janela))
    if regiao is None:
        log.error("O aviso de manutencao esta desligado neste modo.")
        log.error(
            "Rode com --janela, ou configure a chave 'banner_manutencao' no "
            "calibration.json."
        )
        return 2

    # DE ONDE a regiao veio importa tanto quanto qual ela e: sem esta frase o
    # usuario nao sabe se esta conferindo o palpite do scanner ou o ajuste que
    # ele mesmo escreveu.
    origem = (
        "calibrada no calibration.json"
        if cal.banner_manutencao is not None
        else "padrao derivado da party window"
    )
    log.info(
        "Regiao do banner (%s): esquerda=%d topo=%d %dx%d",
        origem, regiao.esquerda, regiao.topo, regiao.largura, regiao.altura,
    )

    fonte = JanelaSource(
        args.janela,
        cal.party_window_na_janela or cal.party_window,
        relativa=cal.party_window_na_janela is not None,
        extras={"banner_manutencao": regiao},
    )
    try:
        frame = fonte.capturar()
        recorte = frame.extras.get("banner_manutencao")
        if recorte is None or getattr(recorte, "size", 0) == 0:
            # Foi o `_extra_para_janela` que decidiu isso: a regiao caiu FORA
            # do frame da janela. Ele devolve None em vez de inventar pixels.
            log.error("A regiao do banner caiu FORA da janela do jogo.")
            log.error(
                "  regiao pedida: esquerda=%d topo=%d %dx%d",
                regiao.esquerda, regiao.topo, regiao.largura, regiao.altura,
            )
            log.error(
                "  janela capturada: %dx%d",
                frame.pixels.shape[1], frame.pixels.shape[0],
            )
            return 2

        agora = datetime.now()
        PASTA_LOGS.mkdir(exist_ok=True)
        destino = PASTA_LOGS / f"banner-manutencao-{agora.strftime('%H%M%S')}.png"
        # CONFERIR O RETORNO NAO E ZELO EXCESSIVO: `cv2.imwrite` devolve False
        # em silencio quando o arquivo esta travado (visualizador de fotos
        # aberto), e o calibrador ja anunciou uma imagem VELHA por causa disso
        # (tarefa 260825-bmw). Anunciar um caminho que nao existe e pior do que
        # nao gravar.
        if cv2.imwrite(str(destino), recorte):
            log.info(
                "Recorte gravado em %s (%s)",
                destino.resolve(), agora.strftime("%H:%M:%S"),
            )
        else:
            log.error(
                "NAO consegui gravar %s — o arquivo esta aberto noutro "
                "programa? Sigo sem a imagem.", destino.resolve(),
            )

        texto = ocr.ler_texto(recorte)
        if texto is None:
            log.error("O OCR nao devolveu nada.")
            log.error("%s", ocr.motivo_indisponivel() or
                      "O motor rodou e nao achou texto nenhum no recorte.")
            return 1

        # AS DUAS ESCALAS, porque o desacordo entre elas e justamente o que esta
        # ferramenta precisa expor: em producao nada e anunciado sem que as duas
        # concordem (D-d), entao ver so a barata esconderia a metade da decisao.
        ampliado = ocr.ler_texto_ampliado(recorte)

        # Delimitadores VISIVEIS porque espaco em branco importa aqui: o OCR
        # comendo um espaco e o que separa `40 minutes` de `40minutes`.
        log.info("Escala de DETECCAO (cinza 2x) leu: >>>%s<<<", texto)
        log.info("Escala de CONFERENCIA (cinza 3x) leu: >>>%s<<<", ampliado)

        eh_banner = eh_banner_de_manutencao(texto)
        duracao = interpretar_banner(texto)
        eh_banner_ampliado = eh_banner_de_manutencao(ampliado)
        duracao_ampliada = interpretar_banner(ampliado)
        log.info(
            "DETECCAO   -> eh_banner_de_manutencao: %s | interpretar_banner: %s",
            eh_banner, duracao,
        )
        log.info(
            "CONFERENCIA -> eh_banner_de_manutencao: %s | interpretar_banner: %s",
            eh_banner_ampliado, duracao_ampliada,
        )

        # A LINHA FINAL E O VEREDITO, e ela existe porque e a unica coisa que o
        # usuario precisa ler para saber se o recurso vai anunciar ou calar.
        if duracao is not None and duracao == duracao_ampliada:
            log.info("As duas escalas CONCORDAM — em producao isto anunciaria.")
        else:
            log.warning(
                "As duas escalas DISCORDAM — em producao isto NAO anunciaria. "
                "Compare os dois textos acima: se so uma escala esta cortando o "
                "banner, o conserto e a faixa (chave 'banner_manutencao' no "
                "calibration.json); se as duas leem torto, e o motor."
            )

        if duracao is not None:
            momento = montar_relogio(args).agora() + duracao
            log.info(
                "Se isto fosse valendo, o servidor cairia as %s",
                momento.strftime("%H:%M:%S"),
            )
        return 0
    finally:
        fonte.fechar()


def _registrar_evento_no_console(evento) -> None:
    """No console, direto e em destaque.

    Deliberadamente diferente do texto do WhatsApp: aqui o usuario esta na
    frente da tela e pode conferir no jogo agora mesmo.
    """
    hora = datetime.fromtimestamp(evento.momento).strftime("%H:%M:%S")
    log.info("%s", destacar(formatar_console(evento), evento.tipo, hora))


def laco_principal(args: argparse.Namespace, cal: Calibracao) -> int:
    """Captura, le, decide e entrega — nesta ordem, a 1 Hz.

    O laco e a prova de falhas: uma excecao em qualquer etapa vira log e a
    proxima iteracao acontece. Um scanner que morre calado e pior do que nenhum
    scanner, porque a party aprende a confiar num silencio que nao significa
    mais nada.
    """
    # O VIGIA DE MANUTENCAO VEM ANTES DA FONTE porque a regiao dele entra no
    # `extras` que a fonte recebe.
    #
    # Em --replay ele NAO e montado: uma sessao gravada nao tem banner nenhum,
    # e os horarios do arquivo ancorariam um instante que nunca existiu.
    if args.replay:
        vigia_manutencao = None
        log.debug("Replay: aviso de manutencao desligado (sessao gravada nao tem banner)")
    else:
        vigia_manutencao = montar_vigia_de_manutencao(
            cal.regiao_do_banner(na_janela=bool(args.janela))
        )

    # UM dicionario de extras para os tres caminhos. O extra do banner so entra
    # quando o vigia existe: no caminho `mss` cada extra custa uma captura
    # PROPRIA por tick, entao pedir um recorte que ninguem le e desperdicio
    # continuo.
    extras: dict[str, Regiao] = {}
    if cal.hp_proprio:
        extras["hp_proprio"] = cal.hp_proprio
    if vigia_manutencao is not None:
        extras["banner_manutencao"] = cal.regiao_do_banner(
            na_janela=bool(args.janela)
        )

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
        fonte = JanelaSource(
            args.janela,
            regiao,
            relativa=cal.party_window_na_janela is not None,
            extras=extras or None,
        )
        log.info("Lendo a janela '%s' — funciona com o jogo coberto", args.janela)
        log.info("Janela MINIMIZADA continua sem funcionar: o Windows para de "
                 "produzir frames e nao ha API que contorne isso.")
    else:
        # No caminho do desktop a barra propria esta em coordenadas da
        # JANELA, entao so da para captura-la pelo caminho --janela.
        # Com extras tambem aqui: D-07 permite explicitamente o caminho `mss`
        # COM a regiao do banner configurada a mao no calibration.json.
        fonte = MssSource(cal.party_window, extras=extras or None)
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
        modo_solo=args.solo,
    )
    if args.solo:
        log.info(
            "MODO SOLO: vigiando so %s. Nao vou reclamar de party ausente.",
            cal.nome_proprio or "voce",
        )
    despachante = montar_despachante(args)
    if despachante:
        despachante.iniciar()

    # A hora que a agenda usa vem daqui, nao do Windows. Montado ANTES do
    # laco porque a primeira volta ja consulta a agenda.
    relogio = montar_relogio(args)

    # A AGENDA: a segunda fonte de eventos do projeto, e a primeira que nao
    # olha para a tela. Ela despacha pelo MESMO Despachante que o rastreador —
    # nunca chamando enviar() direto. E o seam que a Fase 7 vai usar para
    # silenciar; furar ele aqui tornaria o silenciamento impossivel de
    # acrescentar depois sem reescrever isto.
    eventos_agendados = ler_agenda()
    registro_da_agenda = RegistroEmDisco(PASTA_AGENDA)
    registro_de_loot = RegistroDeLoot(PASTA_LOOT)
    silencio = ControleDoSilencio(eventos_agendados, registro_da_agenda)
    leitor_de_comandos = montar_leitor_de_comandos(args)
    if despachante:
        # O corte mora no transporte, nao na deteccao: o rastreador segue
        # decidindo e registrando tudo normalmente, e o que muda e so o
        # que sai para o WhatsApp.
        despachante.em_silencio = silencio.ativo
    if eventos_agendados:
        proximo = proxima_ocorrencia(relogio.agora(), eventos_agendados)
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

    # A SESSAO carrega o que antes eram variaveis locais deste laco. Movidas
    # para um objeto, elas viram construiveis num teste — e e por isso que
    # `tick()` pode ser exercitado com frames fabricados, sem jogo nenhum.
    sessao = Sessao(
        cal=cal,
        rastreador=rastreador,
        eventos_agendados=eventos_agendados,
        registro=registro_da_agenda,
        silencio=silencio,
        despachante=despachante,
        gravador=gravador,
        fonte=fonte,
        ao_registrar=_registrar_evento_no_console,
        loot=registro_de_loot,
        manutencao=vigia_manutencao,
    )

    ultimo_status = 0.0
    erros_seguidos = 0

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

            if frame.saude is not sessao.saude_anterior:
                if frame.saude is SaudeDoFrame.FALHA_DE_CAPTURA:
                    log.warning("Falha de captura — sem visao, nada sera alertado")
                elif frame.saude is SaudeDoFrame.CONGELADO:
                    log.warning("Imagem congelada — jogo travado ou captura presa")

            # A LINHA QUE CONSERTA A AGENDA INTEIRA: este `momento` desce
            # para Sessao.tick, vira datetime e alimenta avisos_devidos e
            # silencio_ativo. A precedencia de frame.momento fica como
            # esta: no replay o horario e o GRAVADO, senao uma sessao de
            # uma hora reproduzida em trinta segundos mediria tudo errado.
            momento = (
                frame.momento if frame.momento is not None else relogio.agora_epoch()
            )

            atender_comandos(
                leitor_de_comandos,
                registro_da_agenda,
                eventos_agendados,
                despachante,
                datetime.fromtimestamp(momento),
                time.monotonic(),
                rastreador,
                loot=registro_de_loot,
            )

            resultado = sessao.tick(frame, momento)

            for texto in resultado.avisos:
                log.info(
                    destacar(texto, hora=relogio.agora().strftime("%H:%M"))
                )

            if resultado.loot_consumado:
                # So log, sem WhatsApp — mesma disciplina de volume do laco
                # da agenda: o Solo Boss ja e 12 ocorrencias por dia.
                consumida = resultado.loot_consumado
                log.info(
                    destacar(
                        f"Loot do Solo Boss das "
                        f"{consumida.alvo.strftime('%H:%M')} registrado para "
                        f"{exibir(consumida.nick)}"
                    )
                )

            if resultado.falhou_ao_analisar:
                log.warning("Erro ao analisar o frame — seguindo")
                time.sleep(args.intervalo)
                continue

            # Cego por muito tempo com o jogo bem ali na frente quase sempre
            # significa calibracao errada, nao alt-tab.
            if sessao.ticks_cego == TICKS_CEGO_PARA_SUGERIR_RECALIBRAR:
                log.warning(
                    "Sem visao da party ha %d leituras seguidas. Se o jogo "
                    "esta aberto e a party window visivel, ela pode ter "
                    "sido ARRASTADA ou o jogo REDIMENSIONADO — nesse caso "
                    "rode calibrar.bat de novo.",
                    sessao.ticks_cego,
                )

            # Enxergar a linha e nao saber quem esta nela e uma falha DIFERENTE
            # de nao enxergar, e ela era invisivel: em 2026-08-25 uma linha
            # passou duas horas como "Membro 1" sem o scanner dizer uma palavra,
            # inclusive atravessando um reinicio. O usuario so descobriu por
            # causa dos alertas errados que vieram depois.
            #
            # O aviso NAO afirma nada sobre a party — ele relata o que o scanner
            # esta vendo e lista as causas possiveis. Afirmar "fulano perdeu o
            # reconhecimento" seria justamente o tipo de mentira plausivel que o
            # projeto inteiro evita.
            for indice, ticks in sorted(sessao.ticks_sem_reconhecer.items()):
                if ticks == TICKS_SEM_RECONHECER_PARA_AVISAR:
                    log.warning(
                        "A linha %d da party window esta ocupada ha %d leituras "
                        "seguidas e eu nao reconheci quem esta nela. Pode ser "
                        "alguem que nao estava na party quando voce calibrou, ou "
                        "alguem que virou LIDER depois (a coroa antes do nome "
                        "muda o desenho). Se for um membro da sua lista, rode "
                        "calibrar.bat de novo para regravar as assinaturas.",
                        indice + 1,
                        ticks,
                    )

            agora = time.monotonic()
            if agora - ultimo_status >= args.status_a_cada:
                log.info(
                    "\n%s",
                    desenhar_status(
                        rastreador, cal, resultado.observacao, silencio
                    ),
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
        if sessao.ultima_observacao is not None:
            log.info(
                "Estado final:\n%s",
                desenhar_status(
                    rastreador, cal, sessao.ultima_observacao, silencio
                ),
            )

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

        total = sum(sessao.contagem.values())
        if total:
            log.info(
                "Resumo: %d frames (%d ok, %d falha de captura, %d congelados), "
                "%d eventos",
                total,
                sessao.contagem[SaudeDoFrame.OK],
                sessao.contagem[SaudeDoFrame.FALHA_DE_CAPTURA],
                sessao.contagem[SaudeDoFrame.CONGELADO],
                sessao.total_eventos,
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
        "--testar-manutencao",
        action="store_true",
        dest="testar_manutencao",
        help=(
            "captura a janela agora e mostra o que o OCR le no banner de "
            "manutencao: a regiao usada, o recorte salvo em disco e o veredito "
            "do parser"
        ),
    )
    parser.add_argument(
        "--solo",
        action="store_true",
        help=(
            "modo solo: vigia so a SUA barra, sem reclamar de party ausente. "
            "A agenda de TvT/Prime continua igual."
        ),
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

    # DEPOIS da calibracao e da resolucao do --janela AUTO, e nao junto do
    # --testar-agenda: diferente da agenda, esta ferramenta precisa das duas.
    if args.testar_manutencao:
        try:
            return comando_testar_manutencao(args, cal)
        except JanelaNaoEncontrada as erro:
            log.error("%s", erro)
            return 2

    try:
        return laco_principal(args, cal)
    except JanelaNaoEncontrada as erro:
        log.error("%s", erro)
        return 2


if __name__ == "__main__":
    sys.exit(main())
