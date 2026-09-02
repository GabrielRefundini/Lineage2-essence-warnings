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
import os  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

from .acervo import AcervoDeIdentidades, carregar_identidades  # noqa: E402
from .aprendiz import AjustesDoAprendiz, Aprendiz, ToleranciaAlemDoTeto  # noqa: E402
from .batismo import (  # noqa: E402
    montar_pergunta_com_imagens,
    pendentes_do_acervo,
    responder_batismo,
)
from .calibracao import (  # noqa: E402
    Calibracao,
    CalibracaoInvalida,
    descrever_geometria_da_tela,
)
from .esquecimento import responder_esquecimento  # noqa: E402
from .agenda import (  # noqa: E402
    Aviso,
    JanelaDeSilencio,
    chave_da_ocorrencia,
    ocorrencias_cancelaveis,
    RegistroEmDisco,
    TipoDeAviso,
    avisos_devidos,
    HORAS_PARA_CANCELAR_ANTECIPADO,
    NOME_DO_SOLO_BOSS,
    apelido_do_evento,
    nomes_dos_eventos,
    proxima_ocorrencia,
    responder_lista_de_presenca,
    responder_silenciamento,
    silencio_ativo,
    texto_de_cancelamento,
    texto_de_encerramento,
    texto_do_aviso,
)
from .config import (  # noqa: E402
    ConfigAusente,
    config_do_chatwoot,
    ler_agenda,
    ler_ajustes_do_aprendiz,
    ler_bosses,
    ler_janela_do_episodio,
    ler_membros,
)
from .captura_janela import (  # noqa: E402
    JanelaNaoEncontrada,
    JanelaSource,
    listar_janelas_do_jogo,
)
from .comandos import (  # noqa: E402
    DIGITOS_FINAIS_DO_TELEFONE,
    Comando,
    ConfiguracaoPerigosa,
    LeitorDeComandos,
    chave_da_mensagem,
    colisoes_de_telefone,
    comandos_novos,
    so_digitos,
    texto_de_ajuda,
)
from .conferencia_do_proprio import avisar_no_arranque  # noqa: E402
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
from .recaptura import FonteRecuperavel  # noqa: E402
from .manutencao import (  # noqa: E402
    CONSELHO_QUANDO_NAO_ANUNCIA,
    SEGUNDOS_ENTRE_LEITURAS,
    VigiaDeManutencao,
    eh_banner_de_manutencao,
    interpretar_banner,
    julgar_as_duas_escalas,
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
    fechar_e_narrar,
    responder_join,
    responder_leave,
)
from .rastreador import EstadoDoMembro, PortaoGlobal, Rastreador  # noqa: E402
# O reancoramento (ADVC-02). `reancoragem` NAO importa `calibrar` no topo: ele
# faz import tardio la dentro, para o arranque do scanner nao pagar pelo `cv2`
# das ferramentas interativas nem pelo efeito colateral de DPI que `calibrar.py`
# executa no import. Ver a docstring de `reancoragem.Reancorador`.
from .reancoragem import Reancorador  # noqa: E402
# Modulo FOLHA (nao importa nada do pacote), pelo mesmo criterio de `raiz.py`:
# `configurar_log` roda como PRIMEIRA coisa do arranque, e a decisao de qual
# arquivo abrir nao pode depender de `cv2`.
from .registro_de_log import (  # noqa: E402
    montar_arquivo_rotativo,
    nome_da_instancia,
)
from .relogio import Relogio, fonte_chatwoot  # noqa: E402
from .respawn import (  # noqa: E402
    ancoras_mais_recentes,
    anunciar_janelas,
    linhas_de_previsao,
)
from .sessao import Sessao  # noqa: E402
from .bosses import BossInvalido, VigiaDeBosses  # noqa: E402
from .visao import EstadoDaLinha  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_CALIBRACAO = RAIZ / "calibration.json"
PASTA_GRAVACOES = RAIZ / "recordings"

# A pasta de log, com UM DESVIO POR VARIAVEL DE AMBIENTE.
#
# ELA EXISTE POR CAUSA DE UM TESTE DE SUBPROCESSO, e a razao merece ficar
# escrita porque parece contorcionismo e nao e.
# `tests/test_agenda.py::TestModoAgendaSemJogo` roda `python -m l2scanner
# --testar-agenda --dry-run` DE VERDADE, num processo filho - e essa e a prova
# de ponta a ponta de que a agenda funciona sem jogo e sem calibracao, que
# nenhum teste em processo consegue dar. Um processo filho nao ve `monkeypatch`
# nenhum, entao ele escrevia no `logs/scanner.log` de campo, e o que caia la era
# exatamente o tipo de linha que ja custou duas cacas a fantasma:
#
#     Modo simulacao: alertas so no console. Nada e enviado...
#     Enviado: TvT comeca em 10 minutos, as 19:30.
#
# Indistinguivel de saida de campo, lida como saida de campo. Variavel de
# ambiente e o unico canal que atravessa a fronteira do processo sem o teste
# precisar lembrar de nada: `subprocess.run` herda o ambiente do pai por padrao,
# entao o desvio vale para todo subprocesso que a suite subir, hoje e amanha.
#
# E UM DESVIO, E NUNCA UM PADRAO: sem a variavel, o caminho e `<repo>/logs`,
# byte por byte o de antes. Quem nunca ouviu falar dela nao percebe diferenca.
PASTA_LOGS = Path(os.environ.get("L2SCANNER_PASTA_DE_LOGS") or (RAIZ / "logs"))
ARQUIVO_OUTBOX = RAIZ / "outbox.jsonl"
# Marcadores de "este aviso ja saiu". Compartilhada pelas DUAS instancias
# que o usuario roda — e o que impede o grupo de receber tudo em dobro.
PASTA_AGENDA = RAIZ / ".agenda"
# O registro de loot do Solo Boss. Pasta PROPRIA porque o RegistroEmDisco
# poda marcadores com prefixo de data em 3 dias — certo para "ja avisei",
# fatal para estatistica: "quantos loots o J4guar pegou" e para sempre.
PASTA_LOOT = RAIZ / ".loot"
# O acervo de assinaturas visuais. IRMA de `.agenda/` e `.loot/`, e nunca
# dentro delas: o RegistroEmDisco poda marcadores com prefixo de data em 3
# dias, e uma assinatura e como estatistica de loot — uma pergunta sobre
# MESES, nao sobre a semana. Fora do `calibration.json` pelo mesmo raciocinio
# invertido: `calibrar.bat` reescreve aquele arquivo inteiro e `assinaturas`
# e campo da party, entao la dentro o acervo morreria por desenho.
PASTA_IDENTIDADES = RAIZ / ".identidades"

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


def configurar_log(verboso: bool, janela: str | None = None) -> None:
    """Log em arquivo rotativo + console, com UM ARQUIVO POR INSTANCIA.

    O arquivo importa: quando o scanner morre calado durante um farm de tres
    horas, o log e a unica forma de descobrir o porque depois.

    O `janela` E O QUE SEPARA AS DUAS INSTANCIAS DO USUARIO. Ate hoje as duas
    (Yazalaque e Faerlina) apontavam o mesmo `RotatingFileHandler` para
    `logs/scanner.log`, e no Windows o `os.rename` de um arquivo que outro
    processo mantem aberto levanta WinError 32 - um traceback POR LINHA logada,
    inundando o console e engolindo o registro. O criterio de nome, as
    alternativas recusadas e o desfecho da rotacao que falha estao em
    `registro_de_log.py`, que e onde a decisao mora.

    O parametro e OPCIONAL de proposito: `mercado_modo._garantir_log` e as
    ferramentas de bancada chamam `configurar_log(False)` sem janela nenhuma, e
    todas continuam valendo sem mudar uma linha.
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

    arquivo = montar_arquivo_rotativo(
        PASTA_LOGS,
        janela=janela,
        arquivo_de_calibracao=ARQUIVO_CALIBRACAO,
    )
    arquivo.setFormatter(formato)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formato)

    log.setLevel(logging.DEBUG if verboso else logging.INFO)
    log.addHandler(arquivo)
    log.addHandler(console)

    # A PRIMEIRA LINHA DIZ DE QUEM E O ARQUIVO, e ela e a outra metade do
    # conserto. Separar os arquivos por instancia resolve a disputa de rotacao;
    # nao resolve a pericia. Investigando a party sumindo em 2026-09-02, nao
    # houve como dizer se os blocos `[vigiando]` VAZIOS eram da instancia do
    # Yazalaque (defeito) ou da Faerlina, que nao esta em party nenhuma
    # (normal), e a investigacao parou ali. Quem abrir este arquivo daqui a seis
    # meses le o dono na linha 1, sem deduzir pelo nome do arquivo e sem confiar
    # em quem o copiou para outro lugar. No console, com as duas janelas lado a
    # lado, ela diz qual e qual.
    #
    # "sem nome" e dito em voz alta, e nao maquiado: um rotulo inventado para o
    # caminho `mss` sem calibracao seria pior que nenhum, porque seria CRIVEL.
    quem = nome_da_instancia(janela, ARQUIVO_CALIBRACAO)
    log.info(
        "Instancia: %s | log: %s", quem or "sem nome", arquivo.baseFilename
    )


def montar_despachante(args: argparse.Namespace) -> Despachante | None:
    """Monta o caminho de entrega, ou None se o scanner roda so no console."""

    def avisar_falha(texto: str, erro: str) -> None:
        # Falha de entrega NUNCA e silenciosa: silencio treina a party a
        # confiar num sinal que nao significa mais nada.
        log.error("FALHA DE ENTREGA — %s | alerta: %s", erro, texto)

    if args.dry_run:
        # A frase diz o DISCO, e nao so o envio. Ela prometia "nada e enviado"
        # e calava que a simulacao gravava marcador na .agenda/ compartilhada
        # — do jeito que estava, quem lesse isto acharia seguro rodar um
        # --dry-run ao lado do scanner de verdade, que e exatamente o que
        # quase apagou o aviso de TvT das 19:30 em 2026-08-26.
        # A LINHA DA `.identidades/` DIZ O QUE O `simulando` DE FATO GARANTE, e
        # nao mais do que isso.
        #
        # A tentacao e escrever que nada e gravado tambem la, e isso e FALSO: o
        # `Aprendiz` roda em `--dry-run` e `acervo.gravar` escreve
        # `assinatura_*` na pasta compartilhada. Essa frase reintroduziria
        # exatamente a promessa mentirosa que este bloco existe para consertar.
        #
        # O que o `simulando` garante e outra coisa, e ela e a que importa:
        # nenhuma PERGUNTA e queimada. O marcador `perguntado_*` nao e criado,
        # entao a simulacao nao rouba a unica pergunta que cada assinatura tem.
        log.info(
            "Modo simulacao: alertas so no console. Nada e enviado e nada e "
            "gravado em .agenda/, e nenhuma pergunta de identidade e queimada "
            "em .identidades/, entao da para rodar junto com o scanner de "
            "verdade."
        )
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


def montar_gravador(args, fonte) -> Gravador | None:
    """Monta o gravador, ou explica por que nao montou. Nunca levanta.

    Mesmo trilho de `montar_despachante` e `montar_vigia_de_manutencao`: tenta,
    degrada com log, devolve None e deixa o scanner subir. O recurso e
    opcional; o scanner nao e.

    `Gravador.__init__` faz `mkdir` e `open`, e era construido fora de qualquer
    try. `main()` so pega `JanelaNaoEncontrada` e `ConfiguracaoPerigosa`, entao
    um `recordings/` somente-leitura, um disco cheio, um caminho travado pelo
    antivirus ou um arquivo ocupando o nome `recordings` derrubavam o scanner
    inteiro com um traceback cru. Gravar e a feature mais opcional do projeto e
    era a unica capaz de impedir o produto de subir.

    ERROR e nao WARNING de proposito: quem esta seguindo o ROTEIRO-SPIKE.md
    precisa abortar e consertar, nao farmar 60 segundos gravando em lugar
    nenhum.
    """
    if not args.record:
        return None

    # `completo_do_frame_atual`, e nao `capturar_completo`: o PNG precisa ser a
    # janela que produziu a linha do indice, nao a mais recente que a WGC
    # empurrou desde entao.
    fonte_completa = fonte.completo_do_frame_atual if args.record_janela else None
    try:
        gravador = Gravador(
            PASTA_GRAVACOES, args.rotulo, fonte_completa=fonte_completa
        )
    except OSError as erro:
        log.error("GRAVACAO DESATIVADA — nao consegui criar a pasta: %s", erro)
        log.error(
            "Todo o resto do scanner continua igual: morte, saida e "
            "ressurreicao seguem sendo detectadas e entregues."
        )
        return None

    if fonte_completa is not None:
        # O sinal de alarme e um PNG de ~170 KB onde deveria haver ~3,5 MB:
        # seria o recorte da party window de novo, e a sessao do usuario teria
        # sido gasta a toa.
        log.info(
            "Gravando a JANELA COMPLETA em %s — cerca de 3,5 MB por frame, "
            "cerca de 210 MB por minuto a 1 Hz. Prefira sessoes de 30 a 60 "
            "segundos e confira o tamanho do primeiro PNG.",
            gravador.pasta,
        )
    else:
        log.info("Gravando em %s", gravador.pasta)
    return gravador


def alarme_de_divergencia(frames_gravados: int, no_disco: int) -> str:
    """A frase de alarme quando o contador e o disco discordam, ou "".

    Funcao pura, e separada de proposito: o resumo antes CALCULAVA `no_disco`
    corretamente, imprimia os dois numeros lado a lado, e nunca os comparava —
    a severidade saia so de `falhas_de_gravacao`. Uma sessao que diz 118 e tem
    40 PNGs no disco (o cenario que abre a docstring de
    `tests/test_gravador_honesto.py`) era emitida em INFO, no meio das linhas
    de rotina, depois de uma hora de farm.

    E o contador em memoria e justamente a testemunha que nao da para
    interrogar aqui: era ele que ficava em zero enquanto um frame se perdia.
    Derivar o alarme dele e fail-open. Imprimir dois numeros lado a lado so e
    uma conferencia se alguma coisa ler os dois.
    """
    if no_disco == frames_gravados:
        return ""
    return (
        "  <-- DIVERGIU: o contador e o disco discordam, nao confie nesta sessao"
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


def montar_vigia_de_bosses(
    cal: Calibracao, na_janela: bool, bosses
) -> VigiaDeBosses | None:
    """Liga o aviso de nascimento de boss, ou diz por que nao ligou.

    Mesmo formato de `montar_vigia_de_manutencao`: tenta, degrada com log,
    devolve `None`, e o scanner sobe do mesmo jeito.

    A LISTA VAZIA E A PRIMEIRA RECUSA, e a ordem e deliberada: sem bloco
    `[[boss]]` nenhum nao ha o que vigiar, mesmo com chat, alvo e OCR todos
    prontos. Conferir a calibracao antes mandaria o usuario recalibrar — quer
    dizer, consertar o que nao esta quebrado — quando o que falta e uma linha
    no `config.toml`.
    """
    if not bosses:
        # `info`, e nao `warning`: nunca ter escrito um `[[boss]]` nao e erro,
        # e o scanner roda sem vigilancia de boss nenhuma desde a v1 (VIGI-04).
        # A mensagem DIZ COMO LIGAR porque um recurso que se desliga sozinho
        # sem explicar como acender e indistinguivel de um recurso quebrado.
        log.info(
            "Vigilancia de boss desligada: nao ha nenhum bloco [[boss]] no "
            "config.toml. Para ligar, acrescente um bloco com 'nome' (como o "
            "mob aparece no jogo), 'respawn_horas_min' e 'respawn_horas_max'."
        )
        return None
    if not cal.tiat_chat and not cal.tiat_alvo:
        log.info(
            "Vigilancia de boss desligada: rode calibrar-tiat.bat para marcar "
            "o chat e/ou o nome do alvo."
        )
        return None
    if not na_janela:
        log.warning("Vigilancia de boss desligada: ela precisa de --janela.")
        return None
    if not ocr.disponivel():
        log.warning(
            "Vigilancia de boss DESATIVADA — %s", ocr.motivo_indisponivel()
        )
        return None

    partes = []
    if cal.tiat_chat:
        partes.append("chat")
    if cal.tiat_alvo:
        partes.append("alvo")
    # A LINHA NOMEIA OS BOSSES, e nao os conta. E a metade de OPER-02 que esta
    # fase entrega; a Fase 2 completa a outra metade acrescentando a proxima
    # janela prevista de cada um — e para isso o nome precisa ja ser a ancora
    # do texto. Trocar por "vigiando 2 bosses" fecharia essa porta.
    log.info(
        "Vigilancia de boss ativa — %s; lendo %s a cada 2s; um aviso por "
        "nascimento.",
        ", ".join(boss.nome for boss in bosses),
        " e ".join(partes),
    )
    return VigiaDeBosses(ocr.ler_texto, bosses=bosses)


def montar_vigia_do_mercado(cal: Calibracao, na_janela: bool):
    """Liga a leitura do painel do World Exchange, ou diz por que nao ligou.

    Mesmo formato de `montar_vigia_de_manutencao`: tenta, degrada com log,
    devolve `None` e deixa o scanner subir. O recurso e opcional; o scanner nao
    e — e este em particular so produz TEXTO no console (DETC-01 entrega o sinal
    e a superficie dele; o consumidor de oclusao e a Fase 4).

    SO NO CAMINHO `--janela`. O painel e procurado na janela INTEIRA do jogo, e
    e so ali que existe um frame completo para varrer. No caminho `mss` cada
    extra custa uma captura propria por tick — capturar 1720x1392 a cada
    segundo para escrever uma linha de console seria caro pelo motivo errado.

    NUNCA LEVANTA: os moldes vem de `calibration.json`, que e entrada nao
    confiavel. `ancoras_de_calibracao` recusa alto e com nome do campo — e essa
    recusa nao pode derrubar a deteccao de morte, que e o scanner inteiro.
    """
    if not cal.mercado_ancoras:
        return None

    if not na_janela:
        log.info(
            "Leitura do mercado desligada: ela precisa da janela inteira do "
            "jogo. Rode com --janela para ver 'MERCADO ABERTO' no console."
        )
        return None

    from .mercado_visao import (
        CASAMENTO_MINIMO_DA_ANCORA,
        TICKS_ENTRE_VARREDURAS_OCIOSAS,
        RastreioDoPainel,
        ancoras_de_calibracao,
    )

    try:
        ancoras = ancoras_de_calibracao(cal.mercado_ancoras)
    except (ValueError, TypeError) as erro:
        log.warning("Leitura do mercado DESATIVADA — %s", erro)
        log.warning(
            "Todo o resto do scanner continua igual: morte, saida e "
            "ressurreicao seguem sendo detectadas e entregues."
        )
        return None

    limiar = cal.mercado_limiar_da_ancora or CASAMENTO_MINIMO_DA_ANCORA

    # A LINHA DE ARRANQUE CONTA O ORCAMENTO, no precedente do vigia de
    # manutencao: quem le o log precisa saber o que o recurso custa antes de o
    # farm comecar. ~45 ms por ancora numa varredura da janela inteira, e por
    # isso ela nao roda a cada volta.
    log.info(
        "Leitura do mercado ativa — %d ancoras (%s), limiar %.2f por ancora, "
        "varredura ociosa a cada %d ticks (~45 ms por ancora). "
        "SO MOSTRA no console: nenhum alerta sai deste sinal.",
        len(ancoras),
        ", ".join(a.nome for a in ancoras),
        limiar,
        TICKS_ENTRE_VARREDURAS_OCIOSAS,
    )
    return RastreioDoPainel(ancoras, limiar=limiar)


def montar_registro_de_mercado(pasta: Path | None = None):
    """Monta o registro de observacoes, ou diz por que nao montou.

    Devolve um `RegistroDeObservacoes` ou `None`, e NUNCA levanta. Mesmo trilho
    de `montar_gravador` e de `montar_vigia_do_mercado` logo acima: tenta,
    degrada com log alto, devolve `None` e deixa o scanner subir. O recurso e
    opcional; o scanner nao e.

    O TIPO DE RETORNO NAO E ANOTADO, pelo mesmo motivo de
    `montar_vigia_do_mercado`: ele so existe atras do import ADIADO, e anota-lo
    aqui deixaria no modulo um nome que `typing.get_type_hints` nao resolve.

    O CONSTRUTOR NAO SE DEFENDE, DE PROPOSITO, e esta escrito na docstring dele.
    Medido nesta maquina: o `mkdir(parents=True, exist_ok=True)` dele levanta
    `FileExistsError` (errno 17, winerror 183) quando um ARQUIVO ocupa o nome da
    pasta, e isso roda antes de qualquer `try`. Sem esta funcao esse traceback
    subiria cru do arranque e levaria a deteccao de morte da party junto com o
    mercado — o modo de falha exato que `montar_gravador` foi escrito para
    consertar e que o PERS-03 proibe. Por isso o `try` envolve o construtor
    INTEIRO, `mkdir` incluido.

    A CAPTURA DIVERGE DA REGRA DA CASA EM UM TIPO, E A DIVERGENCIA E
    DELIBERADA. `OSError` cobre os quatro modos medidos: `PermissionError`
    (errno 13) para arquivo somente-leitura e para nome ocupado por diretorio,
    `FileNotFoundError` (errno 2) para pasta inexistente, e o `FileExistsError`
    acima. `ContratoDoArquivoQuebrado` nao e nenhum deles — nao e falha de
    sistema de arquivos, e uma recusa DELIBERADA de escrever desalinhado, ou de
    ler um arquivo cujo fim o programa nao consegue afirmar, sobre dado que o
    usuario acumulou e edita a mao. Ela chega por DOIS motivos, cabecalho
    divergente (D-12) e arquivo que nao termina em quebra de linha (D-17), e
    como o desfecho e o mesmo — feature desligada, scanner de pe — o tratamento
    e o mesmo. A captura continua ESTREITA: dois tipos NOMEADOS, nunca
    `except Exception`, que esconderia um `AttributeError` de refactor futuro
    como se fosse disco cheio.

    O texto do contrato quebrado ja saiu no log do proprio modulo, com as duas
    hipoteses por extenso e a instrucao de conserto que o 03-01 escreveu. Esta
    funcao NAO O REESCREVE: ela so acrescenta por cima as duas mensagens da
    casa, e `configurar_log` faz as tres chegarem ao console E ao arquivo.

    ERROR e nao WARNING pelo precedente ja escrito em `montar_gravador`:
    `warning` e para linha descartada, `error` e para feature desligada — e quem
    esta lendo o console precisa saber que nao vai ter dado no fim da sessao.

    ELA NASCE SEM CHAMADOR, E ISSO E DESENHO. `montar_gravador` tem um portao de
    curto-circuito na entrada (`if not args.record`) porque existe a flag
    `--record`; aqui nao ha flag, porque `--mercado` e DETC-02, Fase 4. Quem
    ligar isto la vai encontrar a funcao pronta e no trilho.
    """
    from .mercado_registro import (
        ARQUIVO_DE_OBSERVACOES,
        PASTA_DO_MERCADO,
        ContratoDoArquivoQuebrado,
        RegistroDeObservacoes,
    )

    # A pasta padrao e resolvida em tempo de CHAMADA, e nao no topo do modulo: e
    # o que permite ao teste apontar para `tmp_path` sem nunca tocar a
    # `.mercado/` do usuario, que e dado acumulado e sem desfazer.
    destino = PASTA_DO_MERCADO if pasta is None else pasta

    try:
        registro = RegistroDeObservacoes(destino)
    except (OSError, ContratoDoArquivoQuebrado) as erro:
        log.error(
            "REGISTRO DE MERCADO DESLIGADO — nao consegui abrir %s: %s",
            destino / ARQUIVO_DE_OBSERVACOES,
            erro,
        )
        log.error(
            "Todo o resto do scanner continua igual: morte, saida e "
            "ressurreicao seguem sendo detectadas e entregues."
        )
        return None

    return registro


def montar_catalogo_de_mercado(pasta: Path | None = None):
    """Monta o catalogo de nomes, ou diz por que nao montou. NUNCA levanta.

    Trilho IDENTICO ao de `montar_registro_de_mercado` logo acima, e pelo mesmo
    motivo medido: o `mkdir(parents=True, exist_ok=True)` do `Catalogo.__init__`
    roda HOJE fora de qualquer `try`, e levanta `FileExistsError` (errno 17,
    winerror 183) quando um ARQUIVO ocupa o nome da pasta. Por isso o `try`
    envolve o construtor INTEIRO, `mkdir` incluido.

    O tipo de retorno nao e anotado pelo mesmo motivo de la: o nome so existe
    atras do import ADIADO. A pasta padrao resolve em tempo de CHAMADA, para o
    teste apontar `tmp_path` sem tocar a `.mercado/` do usuario.
    """
    from .mercado_catalogo import ARQUIVO_DO_CATALOGO, Catalogo, PASTA_DO_MERCADO

    destino = PASTA_DO_MERCADO if pasta is None else pasta
    try:
        return Catalogo(destino)
    except OSError as erro:
        log.error(
            "CATALOGO DE NOMES DESLIGADO - nao consegui abrir %s: %s",
            destino / ARQUIVO_DO_CATALOGO,
            erro,
        )
        log.error(
            "Todo o resto do scanner continua igual: morte, saida e "
            "ressurreicao seguem sendo detectadas e entregues."
        )
        return None


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
    elif obs.hp_proprio_aparente is not None and cal.nome_proprio:
        # ESTA LINHA E A UNICA CONSUMIDORA DE `hp_proprio_aparente` no projeto
        # inteiro, e e essa unicidade que mantem a mudanca inofensiva: a leitura
        # pode vir de um recorte parcialmente ocluido, entao ela pode virar
        # TEXTO e nada mais. `rastreador.py` nao le o campo, e a suite tem um
        # tripwire de arquitetura que quebra se ele passar a ler.
        #
        # O caso real: cena escura. A cauda vazia da barra mostra terreno
        # escuro, a moldura despenca para 29.08 com a barra ainda 88.5% cheia e
        # o portao de legibilidade recusa — hoje o console e o log ficam sem
        # NADA da barra propria durante a descida inteira, que e justamente
        # quando a informacao mais importa.
        #
        # A MARCA e obrigatoria. Um numero sem marca no `scanner.log` vira
        # evidencia falsa numa investigacao pos-farm: o proximo leitor
        # concluiria que o scanner estava vendo a barra quando nao estava.
        estado_proprio = rastreador.estado_de_membro(f"@{cal.nome_proprio}")
        rotulo = f"{cal.nome_proprio} (voce)"
        linhas.append(
            f"  {rotulo:<12s} {simbolos[estado_proprio]:<6s} "
            f"HP ~{obs.hp_proprio_aparente:4.0%} (aparente)"
        )

    # ESTA LINHA E A UNICA CONSUMIDORA DE `mercado_aberto_aparente` no projeto
    # inteiro, e e essa unicidade que a mantem inofensiva — a mesma garantia que
    # `hp_proprio_aparente` tem logo acima. O sinal pode virar TEXTO e nada
    # mais; `rastreador.py` nao le o campo e a suite tem um tripwire de
    # arquitetura que quebra se ele passar a ler.
    #
    # SO FALA QUANDO ESTA ABERTO. `False` e o estado normal — o mercado fica
    # fechado a maior parte do farm — e uma linha permanente dizendo "mercado
    # fechado" empurraria para fora da tela justamente as linhas de HP que o
    # usuario abre o console para ver.
    #
    # A MARCA `(aparente)` e obrigatoria, pela mesma razao escrita acima: um
    # veredito sem marca no `scanner.log` vira evidencia falsa numa
    # investigacao pos-farm. O proximo leitor precisa saber que o scanner viu
    # arte de painel — nao que o scanner sabe o que voce estava fazendo.
    if obs.mercado_aberto_aparente:
        linhas.append("  WORLD EXCHANGE ABERTO (aparente)")

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
    log.info("Ouvindo comandos em: %s. Mande /status para conferir.", " e ".join(onde))

    if leitor.aberto_a_qualquer_um:
        # Nao e erro, e compatibilidade. Mas um scanner que obedece qualquer um
        # nao pode ser um estado que se descobre por acidente.
        log.warning(
            "COMANDOS ABERTOS: qualquer pessoa que escreva nessas conversas pode "
            "mandar no scanner."
        )
        log.warning(
            "Para restringir, ponha o seu numero em CHATWOOT_TELEFONES_COMANDO "
            "no .env. Para dar so /entrar e /sair aos party-mates, use os blocos "
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
    #
    # A AFIRMACAO E CONDICIONADA AO ESTADO QUE A SUSTENTA. "Nenhum deles
    # alcanca comando de loot" so e verdade quando existe allowlist de dono:
    # com `CHATWOOT_TELEFONES_COMANDO` vazia, `autor_autorizado` devolve True
    # para QUALQUER remetente e `autorizado_para` pergunta por ela primeiro —
    # entao todo mundo, membro ou nao, alcanca `.corrigir` e `.pegou`. Dizer o
    # contrario justamente ai era mentir na frase que da confianca ao usuario.
    if membros:
        if config.telefones_de_comando:
            log.info(
                "Presenca: %d party-mate(s) podem dar /entrar e /sair (%s). Nenhum "
                "deles alcanca comando de loot.",
                len(membros),
                ", ".join(m.nick for m in membros),
            )
        else:
            log.warning(
                "Presenca: os %d [[membro]] (%s) NAO estao contidos — com "
                "CHATWOOT_TELEFONES_COMANDO vazio qualquer remetente alcanca "
                "TODO comando, inclusive /corrigir e /pegou.",
                len(membros),
                ", ".join(m.nick for m in membros),
            )

    _recusar_telefones_de_dono_curtos(config.telefones_de_comando)

    perigosas = []
    for colisao in colisoes_de_telefone(config.telefones_de_comando, membros):
        # A PROPORCAO E O ASSUNTO DESTE BLOCO, e ela mudou onde precisava.
        #
        # Colisao membro contra membro (ou dono contra dono) continua sendo
        # AVISO: ninguem ganha poder, e derrubar o scanner por um erro de
        # digitacao deixaria o usuario sem vigia. Colisao dono contra membro e
        # outra coisa — e uma escalada de privilegio silenciosa para dentro de
        # `.corrigir`/`.pegou`, que reescrevem o `.loot/`, pasta que nunca e
        # podada e nao tem backup. Um `log.warning` num console que rola nao e
        # mitigacao para isso: quem esta farmando nao le o console.
        log.warning(
            "TELEFONES AMBIGUOS: '%s' (%s) e '%s' (%s) terminam nos mesmos %d "
            "digitos e o scanner nao consegue distinguir os dois.",
            colisao.primeiro,
            colisao.origem_do_primeiro,
            colisao.segundo,
            colisao.origem_do_segundo,
            DIGITOS_FINAIS_DO_TELEFONE,
        )
        if colisao.escala_privilegio:
            perigosas.append(colisao)
        else:
            log.warning(
                "Os dois sao do mesmo nivel (%s): ninguem ganha comando novo, "
                "mas um /entrar pode ser creditado ao nick errado. Troque um "
                "dos dois.",
                colisao.origem_do_primeiro,
            )

    if perigosas:
        linhas = "\n".join(
            f"  - '{c.primeiro}' ({c.origem_do_primeiro}) e "
            f"'{c.segundo}' ({c.origem_do_segundo})"
            for c in perigosas
        )
        raise ConfiguracaoPerigosa(
            "ESCALADA DE PRIVILEGIO NA CONFIGURACAO — o scanner nao vai subir.\n"
            f"{linhas}\n"
            "Um lado veio de CHATWOOT_TELEFONES_COMANDO (.env) e o outro de um "
            "[[membro]] (config.toml), e o scanner nao consegue distinguir os "
            "dois. Aquele party-mate alcancaria /corrigir e /pegou, que "
            "reescrevem a estatistica do .loot/ — pasta que nunca e podada e "
            "nao tem backup.\n"
            "Escreva os dois numeros por inteiro (com +55 e DDD), ou tire um "
            "dos dois lados."
        )
    return leitor


def _recusar_telefones_de_dono_curtos(telefones: list[str]) -> None:
    """Um numero de dono mais curto que o corte de comparacao nao e allowlist.

    `telefone_equivalente` compara os `DIGITOS_FINAIS_DO_TELEFONE` finais; uma
    entrada com menos digitos que isso cai no ramo de igualdade completa e
    passa a casar com o SUFIXO de qualquer telefone que termine igual — quer
    dizer, com meio mundo. E o mesmo corte que `_membro_de_dict` ja exige do
    lado do `config.toml`; exigir dos dois lados e o que impede a allowlist de
    ser mais frouxa que a comparacao que ela alimenta.
    """
    curtos = [
        t for t in telefones if 0 < len(so_digitos(t)) < DIGITOS_FINAIS_DO_TELEFONE
    ]
    if not curtos:
        return
    raise ConfiguracaoPerigosa(
        "CHATWOOT_TELEFONES_COMANDO tem numero curto demais: "
        + ", ".join(f"'{t}'" for t in curtos)
        + f".\nO scanner compara os {DIGITOS_FINAIS_DO_TELEFONE} digitos "
        "finais, e um numero mais curto que isso autoriza gente que voce nao "
        'escreveu. Ponha o numero inteiro, com DDD: "+5544999998888".'
    )


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
    bosses=(),
    acervo=None,
    assinaturas_vivas=None,
    forma_esperada=None,
) -> None:
    """Le, obedece e confirma. Nunca levanta.

    `acervo` E `assinaturas_vivas` SAO O BATISMO, e chegam com o mesmo registro
    de comentario que o `bosses` ja tem: os defaults existem so para os testes
    antigos continuarem medindo o que mediam, e em producao os DOIS lacos
    passam o acervo.

    OS DOIS, E NAO SO O PRINCIPAL. O marcador `comando_<id>` da `.agenda/` e
    COMPARTILHADO: exatamente uma instancia obedece cada comando. Se o laco da
    agenda receber a mensagem primeiro e nao tiver acervo, ele consome o
    marcador, responde "nao consigo mexer nas identidades agora" e o batismo do
    usuario e PERDIDO. Logica certa ligada num caminho so e a familia de
    defeito que este projeto ja pagou duas vezes.

    `assinaturas_vivas` e `None` no laco da agenda, e a ausencia e honesta: la
    nao existe lista viva nem rastreador porque nao existe tela. O disco e
    escrito do mesmo jeito, e o nome vale a partir do proximo arranque do
    scanner (T-03-07).

    `forma_esperada` E A REGIAO DE NOME DE AGORA, e ela existe so para o LOTE
    do `/esquecer`. Ela tambem e `None` no laco da agenda, e essa ausencia e da
    mesma familia da de cima mas de outro tamanho: o `--so-agenda` e o modo de
    quem esta com o jogo FECHADO e nao le calibracao nenhuma de proposito (ver
    a docstring de `laco_da_agenda`). Sem geometria o lote e RECUSADO com uma
    frase que diz onde ele funciona, em vez de adivinhar — adivinhar aqui e o
    comando escolhendo sozinho o que esta morto, e a escolha errada tira de
    circulacao gente viva.

    LER A CALIBRACAO DENTRO DO LACO DA AGENDA SO PARA FECHAR ESSA LACUNA SERIA
    PIOR, e a tentacao e obvia: `calibration.json` e um arquivo, e o
    `--so-agenda` roda no mesmo PC. Mas aquele modo sobe HOJE sem calibracao
    nenhuma, e passar a le-la daria a ele um modo de falha novo (arquivo
    ausente ou torto) em troca de um comando que quem esta com o jogo fechado
    nao tem como conferir. A recusa custa uma mensagem; o outro caminho custa o
    arranque.

    `bosses` E A LISTA DO `config.toml`, e ela chega dos DOIS lacos. O default
    vazio existe so para os testes antigos que nao passam nada continuarem
    medindo o que mediam; em producao os dois chamadores passam a lista de
    verdade, e ha portao de AST em `tests/test_janela_sob_demanda.py` exigindo
    isso dos dois. A razao do portao: com a lista vazia o `/tiat` responde "nao
    ha boss vigiado" em vez de falhar, e do lado de quem perguntou isso e
    indistinguivel de config errado — logica certa ligada num caminho so e a
    familia de defeito que este projeto ja pagou duas vezes.

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

        # DEFAULT EXPLICITO, POR ITERACAO. `avisar_o_grupo` e uma variavel de
        # escopo de FUNCAO atribuida dentro dos ramos e lida no bloco de
        # despacho. Os dois ramos de presenca nao a atribuem, e hoje isso e
        # inofensivo so porque eles produzem `RespostaDePresenca` e o
        # `isinstance` curto-circuita antes da leitura — uma coincidencia que
        # nada no codigo preserva. O primeiro ramo futuro que devolver `str`
        # sem setar a flag herdaria EM SILENCIO o valor do comando ANTERIOR da
        # mesma volta do laco, e o efeito e uma resposta privada vazando para o
        # grupo (ou o contrario). O comentario logo abaixo do bloco ja diz que
        # um erro ali "muda o destino de todos ao mesmo tempo, em silencio".
        avisar_o_grupo = False

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
        elif pedido.comando in (
            Comando.DESATIVAR_SOLO_BOSS,
            Comando.ATIVAR_SOLO_BOSS,
        ):
            calar = pedido.comando is Comando.DESATIVAR_SOLO_BOSS
            resposta = responder_silenciamento(
                registro, eventos_agendados, NOME_DO_SOLO_BOSS, calar, quem
            )
            # Muda o que o GRUPO recebe daqui pra frente — mesmo racional do
            # `.cancelar` e do `.solo`. Aqui pesa mais: sao 12 chamadas por dia
            # da party inteira, e o efeito e a AUSENCIA de mensagem. Calar isso
            # em segredo faria os outros concluirem que o bot caiu.
            avisar_o_grupo = True
        elif pedido.comando in (
            Comando.DESATIVAR_LISTA,
            Comando.ATIVAR_LISTA,
        ):
            desligar = pedido.comando is Comando.DESATIVAR_LISTA
            resposta = responder_lista_de_presenca(
                registro, eventos_agendados, NOME_DO_SOLO_BOSS, desligar, quem
            )
            # Mesmo racional do ramo acima: muda o que o GRUPO recebe daqui pra
            # frente — a chamada "Quem vai?" para de sair para todo mundo, e o
            # /entrar de qualquer um passa a ser recusado. O efeito e a
            # AUSENCIA de mensagem, que do lado dos outros e indistinguivel do
            # bot ter caido.
            avisar_o_grupo = True
        elif pedido.comando is Comando.LOOT_DESIGNAR:
            if loot is None:
                resposta = "Nao consigo mexer no loot agora."
            else:
                # `presenca=registro` e o `RegistroEmDisco` da agenda, que ja
                # chega aqui nos DOIS lacos. Ele so ACRESCENTA um aviso quando
                # o designado nao confirmou presenca — nunca recusa (D-13).
                resposta = responder_designacao(
                    loot,
                    eventos_agendados,
                    agora,
                    pedido.argumento,
                    presenca=registro,
                    # UM BOOLEANO, e nao o conjunto cru: o frozenset e truthy
                    # com a lista de QUALQUER evento desligada. Aqui nao existe
                    # local de tick, entao a leitura e na hora.
                    lista_desligada=(
                        apelido_do_evento(NOME_DO_SOLO_BOSS)
                        in registro.listas_desligadas()
                    ),
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
        elif pedido.comando is Comando.JANELA:
            resposta = _obedecer_janela(registro, bosses, agora)
            # Pergunta pessoal, mesmo racional ja escrito no ramo do `.status`.
            # Aqui ha um agravante proprio: este texto o grupo JA RECEBE
            # sozinho, uma vez por janela vencida, pelo caminho de
            # `_avisar_janelas_de_respawn`. Ecoar a consulta seria mandar duas
            # vezes a mesma informacao para quem nao perguntou — e treinar a
            # party a ignorar justamente a mensagem que importa, a que sai no
            # vencimento.
            #
            # A FLAG E ATRIBUIDA E NAO HERDADA, e o comentario do topo deste
            # laco diz por que: este e um ramo que devolve `str`, e sem a
            # atribuicao ele herdaria em silencio o valor do comando ANTERIOR
            # da mesma volta. Ha portao de AST em
            # `tests/test_janela_sob_demanda.py`.
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
        elif pedido.comando is Comando.BATIZAR:
            if acervo is None:
                resposta = "Nao consigo mexer nas identidades agora."
            else:
                batismo = responder_batismo(
                    acervo,
                    pedido.argumento,
                    assinaturas_vivas=assinaturas_vivas,
                    # O TERCEIRO ELO (D-08). Sem o snapshot, um nick batizado
                    # que TAMBEM esteja em `cal.nomes` continua sendo
                    # emprestado por POSICAO para qualquer linha nao
                    # reconhecida — dois nomes iguais na tela, e um deles
                    # mentira. `None` no laco da agenda, onde nao ha
                    # rastreador porque nao ha tela.
                    nomes_reservados=(
                        rastreador.nomes_reservados
                        if rastreador is not None
                        else None
                    ),
                )
                resposta = RespostaDePresenca(
                    privado=batismo.privado, grupo=batismo.grupo
                )
            # A ATRIBUICAO E OBRIGATORIA MESMO SENDO INERTE NO CAMINHO FELIZ.
            #
            # Ali este ramo devolve `RespostaDePresenca` e o `isinstance` do
            # bloco de despacho curto-circuita antes de a flag ser lida —
            # exatamente a "coincidencia que nada no codigo preserva" que o
            # comentario do topo deste laco descreve. No ramo sem acervo ele
            # devolve `str`, e ai a flag e lida de verdade: uma recusa privada
            # nao pode vazar para o grupo.
            #
            # `False` porque a recusa e entre quem digitou e o scanner. O eco
            # no grupo do caminho feliz vem da redacao PROPRIA de
            # `RespostaDoBatismo.grupo`, e nao desta flag: a pergunta foi
            # publica, entao a confirmacao fecha o circuito onde ele foi
            # aberto, com um texto curto e diferente.
            avisar_o_grupo = False
        elif pedido.comando is Comando.ESQUECER:
            if acervo is None:
                resposta = "Nao consigo mexer nas identidades agora."
            else:
                esquecimento = responder_esquecimento(
                    acervo,
                    pedido.argumento,
                    # A LISTA VIVA, e aqui ela e o analogo do que o batismo
                    # ja faz (D-08), na direcao contraria: sem ela o disco
                    # esquece e a TELA continua reconhecendo ate o proximo
                    # arranque, e o usuario manda o comando de novo achando
                    # que falhou. `None` no laco da agenda, onde nao ha tela.
                    assinaturas_vivas=assinaturas_vivas,
                    # A GEOMETRIA DE AGORA, e ela existe so para o LOTE.
                    # `None` no laco da agenda, e la o lote e recusado em vez
                    # de adivinhar o que esta morto. Ver a docstring desta
                    # funcao.
                    forma_esperada=forma_esperada,
                )
                resposta = RespostaDePresenca(
                    privado=esquecimento.privado, grupo=esquecimento.grupo
                )
            # A ATRIBUICAO E OBRIGATORIA, pela mesma razao escrita no ramo do
            # batismo logo acima: no caminho feliz este ramo devolve
            # `RespostaDePresenca` e o `isinstance` do bloco de despacho
            # curto-circuita antes de a flag ser lida, mas no ramo sem acervo
            # ele devolve `str` e a flag e lida de verdade.
            #
            # `False` E O VALOR FINAL DOS DOIS RAMOS, e nao so do de recusa. Ao
            # contrario do batismo, aqui NENHUM desfecho ecoa no grupo:
            # `RespostaDoEsquecimento.grupo` e sempre `None`. O batismo ecoa
            # porque a PERGUNTA foi publica e ficaria pendurada no grupo;
            # esquecer nao responde pergunta nenhuma, e o grupo nao tem o que
            # fazer com a informacao de que uma assinatura saiu de circulacao.
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
            # Sem conversa de origem sai UMA mensagem so, e o destino dela e o
            # GRUPO — entao mande a redacao FEITA para o grupo, e caia no
            # privado so quando nao houver uma.
            #
            # Para os oito comandos antigos isso e indiferente: os dois textos
            # sao o mesmo. Para presenca era a escolha errada das duas — o
            # grupo recebia "Anotado. Voce esta na lista do Solo Boss das
            # 22:00.", sem nick, inutil para quem le, e a redacao feita para o
            # grupo ("J4guar vai no Solo Boss das 22:00.") era DESCARTADA.
            #
            # Mandar as duas aqui faria o mesmo evento aparecer duas vezes no
            # MESMO destino, que e o defeito que este ramo sempre evitou.
            despachante.despachar(
                resposta.grupo or resposta.privado, Categoria.SEMPRE
            )


def _obedecer_cancelar(registro, eventos, agora, quem: str) -> str:
    candidatos = ocorrencias_cancelaveis(agora, eventos, registro.cancelados())
    if not candidatos:
        return f"{quem} pediu para cancelar, mas nao ha silencio ativo nem proximo."

    nome, inicio, rolando = candidatos[0]
    if not registro.cancelar(chave_da_ocorrencia(nome, inicio)):
        return f"O silencio do {nome} ja estava cancelado."
    return f"{quem} cancelou: " + texto_de_cancelamento(nome, inicio, rolando)


def _obedecer_janela(registro, bosses, agora: datetime) -> str:
    """A previsao de janela, respondida a quem perguntou.

    NAO HA TEXTO NOVO AQUI, e essa e a decisao inteira desta funcao. Ela chama
    a MESMA `respawn.linhas_de_previsao` que o console imprime no arranque e de
    hora em hora — a irma desta chamada e `_anunciar_previsao_de_janelas`, e as
    duas leem o mesmo disco e produzem o mesmo texto. Uma segunda redacao,
    escrita aqui para o WhatsApp, seria a quinta origem de texto desta fase e a
    primeira livre para divergir das outras quatro: no dia em que o servidor
    trocasse a regra de respawn, o console e o celular passariam a dizer coisas
    diferentes sobre o mesmo boss, e ninguem descobriria qual dos dois estava
    errado. E a mesma razao ja escrita em `respawn.anunciar_janelas` para os
    dois lacos compartilharem uma implementacao so.

    A LEITURA DE DISCO E SEGURA AQUI pela razao ja escrita em
    `_anunciar_previsao_de_janelas`: esta funcao SO LE. Nao marca, nao despacha
    e nao decide nada, e a proibicao de D-21 e sobre CHECAR ANTES DE MARCAR.

    O `agora` ENTRA POR PARAMETRO, como em todo o resto do arquivo. Ele vem do
    laco — que num replay le o horario GRAVADO — e decide o tempo verbal das
    linhas.

    SEM BOSS NENHUM A RESPOSTA DIZ ISSO, e nao devolve vazio.
    `linhas_de_previsao` devolve lista vazia sem boss e esta certa: quem imprime
    no console e um laco, e uma linha a mais ali repetiria o que
    `montar_vigia_de_bosses` ja diz. Aqui a lista vazia viraria uma mensagem em
    BRANCO no WhatsApp, e do lado de quem perguntou isso e indistinguivel do
    bot ter caido. O texto aponta o `config.toml` porque e la que se conserta.

    SEM ANCORA A RESPOSTA NAO INVENTA HORARIO — quem garante isso e
    `linhas_de_previsao`, que ja se cala por boss, e T-02-13 explica por que.
    Nada aqui pode passar por cima daquilo.
    """
    linhas = linhas_de_previsao(
        agora, bosses, ancoras_mais_recentes(registro.nascimentos())
    )
    if not linhas:
        return (
            "Nao ha nenhum boss vigiado: o config.toml esta sem bloco [[boss]], "
            "entao nao tenho janela de respawn para prever."
        )
    return "\n".join(linhas)


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
    # UM OFF-SWITCH QUE PERSISTE E QUE O STATUS NAO MOSTRA E ESTADO ESCONDIDO.
    # O `/desativarsoloboss` sobrevive a reiniciar o scanner, entao esta linha
    # e a unica coisa entre o usuario que esqueceu que desligou e um boss
    # perdido em silencio.
    calados = nomes_dos_eventos(eventos, registro.eventos_calados())
    if calados:
        partes.append("avisos DESATIVADOS de " + ", ".join(calados))
    # AS DUAS CHAVES APARECEM SEPARADAS, e isso e correcao e nao verbosidade:
    # cada uma e desfeita por um COMANDO DIFERENTE. Fundi-las num "tudo
    # desligado" deixaria o usuario sem saber se manda /ativarsoloboss ou
    # /ativarlista — e mandar o errado devolve "ja estava ligado", que le como
    # bot quebrado. O silencio maior vem primeiro.
    sem_lista = nomes_dos_eventos(eventos, registro.listas_desligadas())
    if sem_lista:
        partes.append("lista de presenca DESLIGADA de " + ", ".join(sem_lista))
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


def _fechar_listas_de_presenca(
    registro, eventos, agora, membros, despachante, loot=None
) -> list:
    """Fecha as listas que venceram e conta ao grupo quem confirmou (D-12).

    EXTRAIDA DO CORPO DO LACO de proposito. O `--so-agenda` esta em 19-20% de
    cobertura — foi onde os tres warnings do code review moravam — e um
    fechamento escrito la dentro nasceria sem teste nenhum, justamente no modo
    que faz este recurso valer. Fora do laco, ele e exercitavel sem relogio,
    sem rede e sem jogo.

    DIFERENCA DELIBERADA EM RELACAO AO CONSUMO DE LOOT LOGO ACIMA no laco, que
    e "SO LOG, sem WhatsApp": a lista fechada VAI para o grupo. Ela e o
    desfecho da pergunta que a chamada fez la 1h50 antes, e deixa-la so no
    console deixaria a party sem a resposta. O volume nao e o mesmo problema,
    porque zero confirmacoes produz zero mensagem: o piso e silencio, e nao
    doze mensagens por dia.

    LOGA SEMPRE, DESPACHA SE HOUVER PARA ONDE — a mesma separacao que o laco ja
    faz com o encerramento de silencio, pela razao ja escrita ali: quem roda
    sem `.env` e sem `--dry-run` perdia a mensagem ate no console.

    O `loot` e OPCIONAL e default `None`: sem ele a lista fecha e sai igual ao
    plano 10-04, so sem a sugestao. Quem roda `--so-agenda` e justamente quem
    esta longe do jogo, e perder a lista fechada por falta de uma estatistica
    de conveniencia seria o pior negocio possivel.

    A DECISAO E O TEXTO MORAM EM `presenca.fechar_e_narrar`, e nao aqui
    (WR-08): esta sequencia estava duplicada literalmente com
    `sessao.Sessao._processar_agenda`. As duas copias escrevem no MESMO
    `.agenda/` e falam no MESMO grupo, e o usuario roda os dois modos — um
    conserto aplicado so de um lado faria `--so-agenda` e o laco principal
    anunciarem coisas diferentes sobre o mesmo boss. Aqui fica so o que e deste
    modo: o log e o despacho.
    """
    hora = agora.strftime("%H:%M")
    fechados = []
    for fechamento, texto in fechar_e_narrar(
        registro, eventos, agora, membros, loot
    ):
        fechados.append(fechamento)
        log.info(destacar(texto, hora=hora))
        if despachante:
            # A MESMA moldura do console vai para o celular, e `SEMPRE`: a
            # lista fechada e organizacao de party, nao alerta de morte, e
            # silencia-la dentro do Prime esconderia quem esta indo.
            despachante.despachar(moldurar(texto, hora), Categoria.SEMPRE)
    return fechados


def _avisar_janelas_de_respawn(registro, bosses, agora, despachante) -> list:
    """Anuncia as janelas de respawn que venceram, no modo do relogio (JANE-05).

    Tres razoes para esta funcao existir, e as tres ja foram pagas neste
    repositorio:

    EXTRAIDA DO CORPO DO LACO, a mesma razao de `_fechar_listas_de_presenca`. O
    `--so-agenda` esta em 19-20% de cobertura e foi onde o incidente de
    2026-08-26 19:30 aconteceu. Codigo escrito dentro do `while` nasce sem teste
    justamente no modo que faz o recurso valer — e este e o modo que entrega a
    janela para quem esta com o jogo FECHADO, que e o publico inteiro de
    JANE-05.

    A DECISAO E O TEXTO NAO MORAM AQUI, a mesma razao de
    `presenca.fechar_e_narrar` (WR-08). Eles moram em `respawn.anunciar_janelas`,
    e os dois lacos chamam a MESMA funcao. As duas copias de `presenca`
    escreviam na MESMA `.agenda/` e falavam no MESMO grupo, e o usuario roda os
    dois modos — um conserto aplicado so de um lado fazia os dois anunciarem
    coisas diferentes sobre o mesmo boss. Aqui fica so o log e o despacho.

    NENHUMA CHECAGEM ANTERIOR AO `marcar` (D-21). Esta funcao NAO pergunta se o
    aviso ja saiu. Quem decide e o `marcar` la dentro, e a docstring de
    `RegistroEmDisco.marcar` proibe por escrito qualquer outra forma: uma
    consulta previa reintroduziria a janela de corrida entre ler e escrever que
    o `O_CREAT|O_EXCL` existe para fechar, e o sintoma seria um aviso PERDIDO e
    nao duplicado — as duas instancias do usuario se veriam livres para calar
    achando que a outra falou. O portao de AST em
    `tests/test_janela_no_relogio.py` impede que a checagem volte.

    LOGA SEMPRE, DESPACHA SE HOUVER PARA ONDE — a mesma separacao que o laco ja
    faz com o encerramento de silencio e com a lista fechada, pela razao ja
    escrita ali: quem roda sem `.env` e sem `--dry-run` perdia a mensagem ate no
    console.

    Devolve a lista de avisos, para o teste poder afirmar sobre estrutura em vez
    de vasculhar log.
    """
    hora = agora.strftime("%H:%M")
    avisados = []
    for aviso, texto in anunciar_janelas(registro, bosses, agora):
        avisados.append(aviso)
        log.info(destacar(texto, hora=hora))
        if despachante:
            # A MESMA moldura do console vai para o celular, e `SEMPRE`
            # (D-23): um boss nascendo durante o Prime e exatamente a
            # informacao que ninguem quer perder.
            despachante.despachar(moldurar(texto, hora), Categoria.SEMPRE)
    return avisados


def _anunciar_previsao_de_janelas(registro, bosses, agora: datetime) -> None:
    """Diz no console, para cada boss vigiado, quando a janela dele abre.

    OPER-02, no molde de `_anunciar_proximo`: o instante entra por PARAMETRO em
    vez de ser lido aqui dentro, pela mesma razao ja escrita ali — e o que
    impede este caminho de ser o ultimo do arquivo a perguntar as horas ao
    Windows. O texto mora em `respawn.linhas_de_previsao`, que e pura; aqui fica
    so o log.

    A UNICA LEITURA DE DISCO QUE OS CAMINHOS DE JANELA FAZEM FORA DE
    `anunciar_janelas` E ESTE `registro.nascimentos()`, e a excecao e segura
    porque esta funcao SO IMPRIME: ela nao marca, nao despacha e nao decide
    nada. A proibicao de D-21 e sobre CHECAR ANTES DE MARCAR, e nao ha `marcar`
    nenhum neste caminho.
    """
    for linha in linhas_de_previsao(
        agora, bosses, ancoras_mais_recentes(registro.nascimentos())
    ):
        log.info(linha)


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
    # A lista de bosses vem do `config.toml`, lida AQUI e ao lado da agenda pelo
    # mesmo motivo que no `laco_principal`: as duas sao a mesma coisa — dado que
    # o usuario escreve a mao e que o arranque tem que conferir antes de subir.
    #
    # `ler_bosses` levanta `BossInvalido` para um bloco torto, e `main()` ja
    # trata e devolve 2. NAO capturado aqui de proposito (T-02-15): derrubar o
    # arranque enquanto o usuario olha o console e melhor que subir vigiando
    # errado em silencio, e e o que o laco principal ja faz desde a Fase 1.
    bosses = ler_bosses()
    if not eventos and not bosses:
        # A RECUSA PASSOU A EXIGIR AS DUAS AUSENCIAS (T-02-14). Ate a Fase 2 ela
        # so olhava a agenda, e a partir daqui isso esta errado: quem so vigia
        # boss e nao configurou nenhum `[[evento]]` ficaria sem o unico modo que
        # entrega a janela com o jogo fechado — e ele e o publico inteiro de
        # JANE-05.
        # SEM TRAVESSAO no texto que o usuario le: o console do Windows ja
        # entregou travessao como lixo neste projeto, e num texto de erro um
        # caractere corrompido faz o usuario duvidar da mensagem inteira.
        log.error(
            "Nao ha nada para o relogio vigiar. Crie um config.toml com pelo "
            "menos um [[evento]] (os lembretes de horario) ou um [[boss]] (a "
            "janela de respawn). Veja o exemplo comentado no repositorio."
        )
        return 2

    despachante = montar_despachante(args)
    if despachante:
        despachante.iniciar()

    # `simulando` entra AQUI, na construcao, e nao perto de cada `marcar`: o
    # laco continua sem saber que o conceito existe. Ver a docstring de
    # `RegistroEmDisco.marcar` e o incidente de 2026-08-26 19:30.
    registro = RegistroEmDisco(PASTA_AGENDA, simulando=args.dry_run)
    registro_de_loot = RegistroDeLoot(PASTA_LOOT)
    # O ACERVO ENTRA NESTE LACO SO PARA A RESPOSTA, e nunca para a pergunta.
    #
    # O marcador `comando_<id>` da `.agenda/` e COMPARTILHADO: exatamente uma
    # instancia obedece cada comando. Se este laco receber o `/batizar`
    # primeiro e nao tiver acervo, ele consome o marcador, responde "nao
    # consigo mexer nas identidades agora" e o batismo do usuario e PERDIDO.
    # Logica certa ligada num caminho so e a familia de defeito que este
    # projeto ja pagou duas vezes.
    #
    # `--so-agenda` NAO VARRE O ACERVO, e a ausencia e deliberada: este e o
    # modo de quem esta com o jogo FECHADO, e uma pergunta "quem e a pessoa da
    # linha 4" chegando com ninguem na frente do jogo convida uma resposta
    # sobre alguem que nao da para ver. O que os dois lacos precisam
    # compartilhar e a RESPOSTA, e ela esta ligada nos dois.
    #
    # `simulando` aqui pela mesma razao do `RegistroEmDisco` logo acima: um
    # `--so-agenda --dry-run` rodando ao lado do scanner de verdade nao pode
    # queimar as perguntas dele.
    acervo = AcervoDeIdentidades(PASTA_IDENTIDADES, simulando=args.dry_run)
    silencio = ControleDoSilencio(eventos, registro)
    leitor = montar_leitor_de_comandos(args)
    # Este e o modo de quem NAO esta com o jogo aberto: aqui o relogio e
    # 100% do produto. Um erro de 3h nao atrasa o aviso, ele o APAGA.
    relogio = montar_relogio(args)

    if eventos:
        nomes = ", ".join(e.nome for e in eventos)
        log.info("Modo agenda: vigiando o relogio, nao a tela. Eventos: %s", nomes)
    else:
        # SEM EVENTO, A LINHA TEM QUE DIZER O QUE ESTA ACONTECENDO. A frase
        # antiga listava eventos e, com a lista vazia, sairia mentindo sobre
        # uma agenda que nao existe — para um usuario que acabou de ganhar o
        # direito de subir este modo so com `[[boss]]`.
        log.info(
            "Modo agenda: vigiando o relogio, nao a tela. Sem nenhum "
            "[[evento]] no config.toml: o que esta sendo vigiado aqui e a "
            "janela de respawn dos bosses."
        )
    log.info("O jogo NAO precisa estar aberto. O PC, sim.")
    _anunciar_proximo(eventos, relogio)
    _anunciar_previsao_de_janelas(registro, bosses, relogio.agora())

    ultimo_anuncio = relogio.agora()
    try:
        while True:
            agora = relogio.agora()
            atender_comandos(
                leitor, registro, eventos, despachante, agora,
                time.monotonic(), loot=registro_de_loot,
                # A MESMA lista que `_avisar_janelas_de_respawn` e
                # `_anunciar_previsao_de_janelas` recebem neste laco. Sem ela o
                # `/tiat` responde "nao ha boss vigiado" no modo `--so-agenda`,
                # que e justamente o modo de quem esta com o jogo FECHADO — o
                # publico inteiro deste comando.
                bosses=bosses,
                # O BATISMO, so a metade da RESPOSTA. `assinaturas_vivas` fica
                # de fora porque aqui nao existe lista viva nem rastreador:
                # nao existe tela. O disco e escrito do mesmo jeito, e o nome
                # vale a partir do proximo arranque do scanner (T-03-07).
                acervo=acervo,
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
            # UMA leitura por tick, do disco e sem cache: o comando pode chegar
            # na OUTRA instancia do usuario. Serve ao gate da chamada e a linha
            # de loot logo abaixo.
            desligadas = registro.listas_desligadas()
            for aviso in avisos_devidos(
                agora, eventos, registro.enviados(),
                eventos_calados=registro.eventos_calados(),
                listas_desligadas=desligadas,
            ):
                if not registro.marcar(aviso.chave):
                    continue
                texto = texto_do_aviso(
                    aviso,
                    nick_para_o_aviso(
                        aviso,
                        designacao,
                        # BOOLEANO, nunca o conjunto: o frozenset cru e truthy
                        # com a lista de qualquer evento desligada e tiraria a
                        # linha `Loot:` do TvT junto, sem erro nenhum.
                        lista_desligada=(
                            apelido_do_evento(NOME_DO_SOLO_BOSS) in desligadas
                        ),
                    ),
                )
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

            # E entao a lista de presenca, na MESMA ordem do tick: depois do
            # consumo de loot, porque no plano 10-05 o fechamento passa a
            # depender do que o consumo acabou de registrar.
            #
            # Este e o laco que faz o recurso valer com o jogo FECHADO, que e a
            # mesma razao pela qual AGEN-05 existe: quem mais precisa saber
            # quem vai no boss e justamente quem nao esta online.
            _fechar_listas_de_presenca(
                registro,
                eventos,
                agora,
                leitor.membros if leitor else (),
                despachante,
                loot=registro_de_loot,
            )

            # E entao a janela de respawn, DEPOIS do fechamento e sempre nesta
            # posicao. A ordem nao muda resultado — os dois namespaces em disco
            # sao disjuntos e nao ha estado compartilhado entre eles — mas
            # fixa-la torna o tick deterministico para o teste, que e a mesma
            # razao ja escrita acima para a posicao do consumo de loot.
            #
            # ESTE e o laco que faz JANE-05 valer, pela mesma razao que AGEN-05
            # existe: quem mais precisa saber que a janela do boss abriu e
            # justamente quem NAO esta com o jogo aberto.
            _avisar_janelas_de_respawn(registro, bosses, agora, despachante)

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
                # A previsao de janela entra na MESMA repeticao horaria, e nao
                # so no arranque: o `--so-agenda` roda por DIAS, e o ROADMAP e
                # explicito em que este e "o modo de quem mais precisa da
                # linha". Repetir so o proximo evento deixaria de fora
                # justamente a informacao deste workstream.
                _anunciar_previsao_de_janelas(registro, bosses, agora)
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

    Esta ferramenta nasceu de um risco declarado: a precisao do OCR na FONTE
    DO JOGO nunca tinha sido provada, porque o spike leu um banner sintetico.

    O RISCO SE REALIZOU EM 31/08/2026, E FOI ESTA FERRAMENTA QUE MEDIU. Com o
    servidor entrando em manutencao as ~18:20 e o banner na tela por quase uma
    hora, quatro rodadas daqui produziram as oito leituras que estao hoje
    fixadas em `tests/test_manutencao.py`. Elas mostraram que o `M` de
    Maintence nunca sobrevive ao motor e que a porta 1 nunca fechava. Sem esta
    ferramenta o defeito continuaria invisivel: de fora, o scanner parecia
    estar funcionando.

    Por isso ela mostra as TRES coisas separadas: qual regiao usou, que pixels
    pegou (o PNG em disco) e o que o OCR e o parser entenderam. Quando algo
    falhar, essas tres respostas dizem QUAL das tres etapas falhou.

    E o VEREDITO final nao e calculado aqui — ver o comentario ao lado dele.
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
        #
        # ELA VEM DE `julgar_as_duas_escalas`, A MESMA FUNCAO QUE O PRODUTO
        # CHAMA. Aqui morava um `if` proprio, e ele DIVERGIU: em 31/08 as duas
        # escalas leram texto IDENTICO, as duas devolveram None, e esta linha
        # imprimiu "as duas escalas discordam". Elas concordavam, e o usuario
        # foi mandado conferir uma faixa que ja estava certa. Um diagnostico
        # com logica propria e um diagnostico que um dia mente.
        veredito = julgar_as_duas_escalas(texto, ampliado)
        if veredito.anunciaria:
            log.info("%s Em producao isto ANUNCIARIA.", veredito.explicacao)
        else:
            log.warning(
                "%s Em producao isto NAO anunciaria. %s",
                veredito.explicacao,
                CONSELHO_QUANDO_NAO_ANUNCIA,
            )

        if veredito.duracao is not None:
            momento = montar_relogio(args).agora() + veredito.duracao
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


def montar_fonte(args, cal, extras: dict[str, Regiao] | None = None):
    """Escolhe o backend de captura e devolve a fonte pronta para o laco.

    O QUE MUDOU AQUI, e por que. Ate 2026-09-01 este bloco construia a fonte
    UMA vez e ninguem nunca a reconstruia: quando a sessao de captura morria
    com o jogo vivo, o laco seguia chamando `capturar()` num cadaver para
    sempre (33 minutos medidos — ver o cabecalho de `recaptura.py`). Agora cada
    caminho VIVO vira uma FABRICA sem argumentos, e a fabrica e o unico lugar
    onde a lista de argumentos da fonte existe: arranque e religacao chamam a
    MESMA funcao, entao os dois sites nao tem como divergir em silencio. Em
    particular a chamada de `JanelaSource` continua sem mencionar
    `minimum_update_interval`, byte-identica a de antes, e o padrao `None` segue
    valendo (`tests/test_mercado_firewall_de_fase.py`).
    """
    extras = extras or {}

    if args.replay:
        fonte = ReplaySource(Path(args.replay))
        log.info("Reproduzindo %s (%d frames)", args.replay, len(fonte))
        # O REPLAY FICA FORA DO ENVELOPE DE PROPOSITO. Reconstruir uma
        # `ReplaySource` reiniciaria a gravacao do primeiro frame, e um replay
        # que recomeca sozinho reproduziria os mesmos eventos de novo — o
        # harness de regressao deixaria de provar qualquer coisa. Alem disso o
        # fim de uma gravacao ja tem tratamento proprio no laco
        # (`StopIteration` -> "Fim da sessao gravada"), e frames repetidos numa
        # gravacao sao DADO, nao falha de captura.
        return fonte

    if args.janela:
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

        def construir():
            return JanelaSource(
                args.janela,
                regiao,
                relativa=cal.party_window_na_janela is not None,
                extras=extras or None,
            )

        fonte = FonteRecuperavel(construir)
        log.info("Lendo a janela '%s' — funciona com o jogo coberto", args.janela)
        log.info("Janela MINIMIZADA continua sem funcionar: o Windows para de "
                 "produzir frames e nao ha API que contorne isso.")
    else:
        # No caminho do desktop a barra propria esta em coordenadas da
        # JANELA, entao so da para captura-la pelo caminho --janela.
        # Com extras tambem aqui: D-07 permite explicitamente o caminho `mss`
        # COM a regiao do banner configurada a mao no calibration.json.
        def construir():
            return MssSource(cal.party_window, extras=extras or None)

        fonte = FonteRecuperavel(construir)
        if cal.hp_proprio:
            log.warning(
                "A barra do seu personagem so e lida com --janela. "
                "Sem ela, a SUA morte nao sera detectada."
            )
        log.info("Lendo o desktop — o jogo precisa estar visivel. "
                 "Use --janela para funcionar com ele coberto.")

    return fonte


def laco_principal(
    args: argparse.Namespace,
    cal: Calibracao,
    ajustes_do_aprendiz: AjustesDoAprendiz | None = None,
) -> int:
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

    # A lista de bosses vem do `config.toml` e nao do codigo (VIGI-01). Lida
    # aqui, ao lado da agenda, porque as duas sao a mesma coisa: dado que o
    # usuario escreve a mao e que o arranque tem que conferir antes de subir.
    #
    # UMA LEITURA SO, EM VARIAVEL, e ela tem dois consumidores que precisam
    # enxergar a MESMA lista: o vigia (que reconhece o nascimento na tela) e as
    # regras de respawn da `Sessao` (que preveem a janela pelo relogio). Duas
    # chamadas a `ler_bosses()` abririam a possibilidade de o usuario editar o
    # arquivo entre elas e o scanner subir vigiando um conjunto de bosses e
    # prevendo outro.
    regras_de_respawn = ler_bosses()
    # A JANELA ANTI-REPETICAO DO ANUNCIO, conferida CONTRA a lista que acabou de
    # ser lida, e nao contra uma releitura. Ela levanta `BossInvalido` quando o
    # valor escrito engoliria o nascimento seguinte de algum boss, e `main()`
    # ja trata e devolve 2 — a mesma recusa de arranque de um `[[boss]]` torto,
    # e pela mesma razao: o modo de falha aqui e o scanner MUDO, e ninguem
    # percebe um alerta que nao chegou.
    janela_do_episodio = ler_janela_do_episodio(regras_de_respawn)
    vigia_bosses = montar_vigia_de_bosses(
        cal, na_janela=bool(args.janela), bosses=regras_de_respawn
    )
    if vigia_bosses is not None:
        if cal.tiat_chat:
            extras["tiat_chat"] = cal.tiat_chat
        if cal.tiat_alvo:
            extras["tiat_alvo"] = cal.tiat_alvo

    # O MERCADO PEDE A JANELA INTEIRA, e nao o retangulo da ancora.
    #
    # O painel ANDA: entre dois frames do incidente 27x ele apareceu 181 px a
    # esquerda e 143 px abaixo, com a mesma arte casando 0.9996. Um extra fixo
    # no retangulo calibrado mediria grama na maior parte dos frames e o console
    # diria "mercado fechado" com o mercado aberto na tela.
    #
    # O tamanho vem do CARIMBO da calibracao (`mercado_geometria_da_captura`),
    # que e a janela sob a qual os moldes foram recortados. Com a janela em
    # outro tamanho o recorte nao bate, `_extra_para_janela` devolve `None`
    # (falha fechada ja existente) e o `Sessao` avisa UMA vez para recalibrar.
    vigia_mercado = montar_vigia_do_mercado(cal, na_janela=bool(args.janela))
    if vigia_mercado is not None:
        carimbo = cal.mercado_geometria_da_captura or {}
        largura, altura = carimbo.get("largura"), carimbo.get("altura")
        if isinstance(largura, int) and isinstance(altura, int):
            extras["mercado_janela"] = Regiao(
                esquerda=0, topo=0, largura=largura, altura=altura
            )
        else:
            log.warning(
                "Leitura do mercado DESATIVADA — a calibracao nao guarda as "
                "dimensoes da janela sob a qual os moldes foram recortados. "
                "Rode calibrar-mercado.bat."
            )
            vigia_mercado = None

    fonte = montar_fonte(args, cal, extras)

    # A CONFERENCIA DA BARRA PROPRIA, UMA VEZ, AQUI.
    #
    # O INCIDENTE, medido em 2026-08-31: `hp_proprio` gravado em (298,701) e a
    # barra vermelha de verdade em `topo=711`. Dez pixels acima, a regiao caia
    # sobre a barra de CP e o console mostrava "Yazalaque (voce) ok HP 8%" com a
    # barra CHEIA (5418/5418). 8% e MAIOR QUE ZERO, entao
    # `_ja_viu_a_propria_barra_viva` virou True e a unica guarda que protegia o
    # usuario saiu do caminho: dali em diante uma oscilacao da lasca vermelha
    # ate zero anunciaria a MORTE dele com ele intacto. A causa do desvio
    # continua desconhecida (ver o cabecalho de `conferencia_do_proprio.py`); o
    # que esta garantido aqui e que o desfecho nao acontece calado.
    #
    # AS DUAS CONDICOES SAO NECESSARIAS. `--janela` porque a conferencia precisa
    # de `capturar_completo()`, que so a `JanelaSource` tem, e porque `hp_proprio`
    # esta em coordenadas da JANELA -- no caminho `mss` a barra propria nem e
    # capturavel, e o aviso logo acima ja diz isso. `not --replay` porque uma
    # sessao gravada nao tem janela para varrer.
    #
    # ELA SO AVISA, NUNCA CORRIGE: nada e reescrito, nem em disco nem em
    # memoria. Ver o item 2 do cabecalho daquele modulo.
    if not args.replay and args.janela:
        avisar_no_arranque(cal, fonte)

    # `--record-janela` ja foi validado no parse: implica --record e exige
    # --janela, entao aqui a fonte e sempre uma JanelaSource.
    gravador = montar_gravador(args, fonte)

    # O REANCORAMENTO (ADVC-02), e as tres condicoes sao todas necessarias.
    #
    # `--janela` porque a busca precisa de `capturar_completo()`, que so a
    # `JanelaSource` tem; `party_window_na_janela` porque e o unico referencial
    # que sobrevive a arrastar o jogo e o unico que a busca (feita com
    # `ox=oy=0`) produz; e `not --replay` porque uma sessao gravada nao tem
    # janela para varrer.
    #
    # A CONDICAO DE `--janela` TAMBEM E A CONTENCAO. A `JanelaSource` captura
    # POR TITULO (`window_name=` na `WindowsCapture`), entao a varredura fica
    # dentro de UMA janela. No caminho `mss` procurar significaria varrer o
    # desktop, e o usuario roda DOIS clientes: a busca poderia achar a party
    # window do OUTRO e o scanner passaria a vigiar a party errada em silencio.
    # Por isso ali o recurso simplesmente nao existe.
    reancorador = None
    if not args.replay and args.janela and cal.party_window_na_janela is not None:
        reancorador = Reancorador(fonte=fonte)

    # O ACERVO ENTRA AQUI, ANTES DO RASTREADOR, e a atribuicao e EM MEMORIA.
    #
    # `cal.assinaturas` passa a ser a fusao "calibradas primeiro, acervo
    # depois" — e o `calibration.json` NAO e regravado por este caminho, nem
    # pode passar a ser. Escrever o acervo de volta no arquivo que o
    # `calibrar.bat` reescreve desfaria pelo lado de dentro a unica razao de a
    # pasta ser propria.
    # `simulando` entra AQUI, na construcao, e nao perto de cada uso — mesma
    # disciplina do `RegistroEmDisco` logo abaixo, e pela mesma razao: um
    # `if dry_run` em cada ponto de chamada resolveria os de hoje e garantiria
    # que o proximo nascesse errado.
    acervo = AcervoDeIdentidades(PASTA_IDENTIDADES, simulando=args.dry_run)
    # A FORMA ESPERADA VEM DE `regiao_do_nome`, e nao do `layout` direto, porque
    # e ela que `visao._recorte_do_nome` usa para cortar. Ler do mesmo lugar que
    # producao corta e o que impede o aviso de acusar uma divergencia que nao
    # existe, ou calar sobre uma que existe.
    regiao_do_nome = cal.regiao_do_nome(0)
    identidades = carregar_identidades(
        list(cal.assinaturas),
        acervo,
        forma_esperada=(regiao_do_nome.altura, regiao_do_nome.largura),
    )
    cal.assinaturas = identidades.assinaturas
    log.info("%s", identidades.resumo)
    # UMA VEZ, NO ARRANQUE, e nao a cada frame. Uma assinatura de forma antiga
    # nunca mais casa, entao o aviso nao muda enquanto o processo vive — repeti-
    # lo no laco viraria ruido, e ruido e como um aviso deixa de ser lido.
    if identidades.aviso_de_forma:
        log.warning("%s", identidades.aviso_de_forma)

    # O APRENDIZ RECEBE A MESMA INSTANCIA DE ACERVO QUE A CARGA USOU. Construir
    # uma segunda seriam duas verdades sobre a mesma pasta.
    #
    # OS AJUSTES CHEGAM DE FORA E NUNCA SAO LIDOS AQUI DENTRO. `laco_principal`
    # constroi a fonte de captura logo acima, entao qualquer leitura de
    # configuracao feita aqui so poderia ser exercitada com tela viva — e a
    # recusa por tolerancia alem do teto (D-06) tem de ser demonstravel com o
    # jogo fechado. Quem le e `main()`, antes de olhar para a tela.
    aprendiz = Aprendiz(acervo, ajustes_do_aprendiz or AjustesDoAprendiz())

    rastreador = Rastreador(
        nomes=list(cal.nomes),
        nome_proprio=cal.nome_proprio,
        nomes_reservados=cal.nomes_com_assinatura,
        modo_solo=args.solo,
        # O ELO QUE FALTAVA. Ate 2026-08-31 este argumento nao era passado em
        # lugar nenhum de producao: o campo tinha default `False` e so os
        # testes o atribuiam. Ou seja, o silencio do `#linhaN` estava provado
        # na suite e DESLIGADO em campo, e uma linha nao reconhecida pegava
        # emprestado `nomes[indice]` para anunciar uma morte com o nome errado.
        assinaturas_configuradas=identidades.configuradas,
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
    # Mesmo `simulando` do `laco_da_agenda`: a Sessao recebe um registro que ja
    # sabe se e para valer, e por isso `sessao.py` nao conhece `dry_run`.
    registro_da_agenda = RegistroEmDisco(PASTA_AGENDA, simulando=args.dry_run)
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

    # A PREVISAO DE JANELA, DELIBERADAMENTE FORA DE `montar_vigia_de_bosses` E
    # FORA DE QUALQUER `if`.
    #
    # Ela depende so da ancora em disco e do relogio, entao tem que sair mesmo
    # quando o vigia esta `None` por falta de calibracao ou de OCR. Amarra-la ao
    # vigia faria uma calibracao quebrada APAGAR, em silencio, a previsao de uma
    # ancora que continua perfeitamente correta em disco — que e a mesma razao
    # pela qual a `Sessao` recebe `regras_de_respawn` separado de `bosses`.
    #
    # A linha de `montar_vigia_de_bosses` que NOMEIA os bosses vigiados nao
    # muda: ela e a metade "quem esta sendo vigiado" que a Fase 1 entregou, e
    # estas linhas sao a metade "qual a proxima janela". As duas juntas sao
    # OPER-02 inteiro.
    _anunciar_previsao_de_janelas(
        registro_da_agenda, regras_de_respawn, relogio.agora()
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

    # A VARREDURA DE ARRANQUE (BATI-01), e ela e o que faz esta fase valer para
    # o que JA ESTA EM DISCO.
    #
    # POR QUE ELA NAO E REDUNDANTE COM O GATILHO DO APRENDIZADO. Uma entrada
    # anonima que ja estava no acervo entra em `cal.assinaturas` na carga logo
    # acima, e no proximo `extrair` a linha dela casa ~1.000 contra ela mesma.
    # `Casamento.nome` de uma entrada anonima e a string VAZIA e nao `None`, e
    # `_candidatas_para_aprender` exige `is None` — entao ela NUNCA vira
    # candidata, o `Aprendiz` nunca a ve, e nenhum `Aprendizado` nasce. Sem
    # esta varredura, as duas pessoas que a Fase 2 aprendeu em campo ficariam
    # "Membro N" para sempre.
    #
    # Ela e tambem a rede de seguranca de toda pergunta que se perdeu: uma
    # entrada criada por um `--dry-run`, uma pergunta cortada por falha de
    # disco, uma sessao que subiu sem `.env`. A varredura olha as anonimas SEM
    # marcador e nao se importa com qual processo as gravou.
    #
    # A POSICAO IMPORTA: depois do `despachante.iniciar()`, para haver para
    # onde mandar, e depois do aperto de mao, para o grupo ler primeiro que o
    # scanner subiu.
    #
    # O `if despachante` E A TRAVA DE D-05 ESTENDIDA, e ele nao e um detalhe.
    # `montar_pergunta` MARCA. Chama-la sem despachante queimaria o marcador de
    # uma pergunta que nao vai para lugar nenhum, e o marcador e PARA SEMPRE: a
    # pessoa ficaria "Membro N" ate alguem apagar um arquivo a mao. Quem roda
    # sem `.env` e sem `--dry-run` simplesmente ainda nao perguntou, e vai
    # perguntar no dia em que configurar a entrega.
    #
    # A VARREDURA PERGUNTA POR UMA, E NAO POR TODAS, desde a verificacao em
    # campo de 01/09/2026: duas imagens numa mensagem so chegaram como UMA, e o
    # provedor de WhatsApp entrega um anexo por mensagem. As demais anonimas
    # vao para a fila da `Sessao` logo abaixo e saem uma por
    # `INTERVALO_ENTRE_PERGUNTAS` — sem esta entrega elas esperariam o PROXIMO
    # arranque do scanner, uma por reinicio.
    pendentes_de_batismo = pendentes_do_acervo(acervo)
    momento_da_ultima_pergunta = None
    if despachante is not None:
        pergunta = montar_pergunta_com_imagens(acervo, pendentes_de_batismo)
        if pergunta:
            log.info(
                "Ha %d assinatura(s) sem nome no acervo. Perguntando por uma "
                "de cada vez, uma vez so por assinatura, com a imagem do nome.",
                len(pendentes_de_batismo),
            )
            # `Categoria.SEMPRE` pela mesma razao do gatilho do aprendizado: o
            # marcador ja foi queimado dentro de `montar_pergunta_com_imagens`,
            # entao uma mensagem cortada pelo silencio de TvT seria uma
            # pergunta perdida para sempre.
            #
            # ESTE E O CAMINHO QUE MAIS PRECISA DA IMAGEM. As entradas que ja
            # estavam no disco sao as unicas que existem no acervo real do
            # usuario, e sao exatamente as que ele nao consegue reconhecer pelo
            # hash — foi olhando para elas que ele perguntou "como vou saber
            # qual hash representa qual nome?".
            despachante.despachar(
                pergunta.texto,
                Categoria.SEMPRE,
                anexos=pergunta.imagens,
                texto_sem_anexos=pergunta.texto_sem_imagens,
            )
            # O RELOGIO DA MESMA ESCALA DO TICK. `Sessao.tick` mede o
            # espacamento contra `momento`, que e `time.time()` do frame — e
            # nao `monotonic`. Misturar as duas escalas aqui daria uma
            # diferenca da ordem de decadas e liberaria a segunda pergunta no
            # primeiro tick, que e exatamente a rajada que este numero desfaz.
            momento_da_ultima_pergunta = time.time()

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
        bosses=vigia_bosses,
        # As REGRAS de respawn entram separadas do vigia, de proposito: a
        # previsao da janela so depende do relogio e da ancora em disco, e tem
        # que continuar valendo quando o vigia esta `None` por falta de
        # calibracao ou de OCR.
        regras_de_respawn=regras_de_respawn,
        # E A JANELA DO EPISODIO ENTRA SEPARADA DAS REGRAS, que e o conserto de
        # 2026-08-31 visivel na fiacao: um `respawn_horas_min` errado pode
        # atrasar a previsao ali de cima, e nao pode mais calar um nascimento.
        janela_do_episodio=janela_do_episodio,
        # O sinal do mercado entra por AQUI e sai no console, e so. O
        # `rastreador` nao o recebe, nao o le e nao tem como: ver o tripwire de
        # arquitetura em `tests/test_mercado_27x.py`.
        mercado=vigia_mercado,
        # Os `[[membro]]` chegam ate a lista fechada por AQUI. Sem esta linha o
        # mapa `nomes_dos_membros` existe, tem teste verde, e a lista sai com a
        # caixa do slug — o mesmo modo de falha que deixou o nivel de membro
        # inalcancavel no plano 10-01.
        membros=leitor_de_comandos.membros if leitor_de_comandos else (),
        # O aprendizado de identidades. Ele entra por AQUI e sai no acervo e no
        # `scanner.log`, e so: nenhum alerta novo nasce dele. O `rastreador` nao
        # o recebe e nao o le — ver o tripwire de arquitetura em
        # `tests/test_aprendiz.py`.
        aprendiz=aprendiz,
        # A MESMA instancia de acervo que a carga, o aprendiz e a varredura de
        # arranque usam. Ela entra so para a `Sessao` poder PERGUNTAR quem e a
        # pessoa que o aprendiz acabou de gravar (BATI-01); `sessao.py` fala
        # com o `batismo` e nunca com o `acervo`.
        acervo=acervo,
        # O QUE A VARREDURA DE ARRANQUE NAO PERGUNTOU. A lista inteira entra,
        # inclusive a pessoa que acabou de sair na mensagem acima: quem ja tem
        # marcador nao produz mensagem nenhuma e some da fila sem custo, e
        # deixar o filtro para o `O_CREAT|O_EXCL` e o que mantem UM dono da
        # decisao "ja perguntei" (D-04). Sem esta linha, as anonimas que
        # sobraram esperariam o PROXIMO arranque do scanner — uma por reinicio.
        pendentes_de_batismo=pendentes_de_batismo,
        # E O INSTANTE DA PERGUNTA DO ARRANQUE, para o espacamento comecar a
        # contar dali. Sem ele o primeiro tick mandaria a segunda bolha no
        # mesmo segundo em que o scanner subiu.
        momento_da_ultima_pergunta=momento_da_ultima_pergunta,
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
                # A MESMA lista que `_anunciar_previsao_de_janelas` recebe no
                # arranque deste laco, e aqui ela se chama `regras_de_respawn`
                # e nao `bosses` — o nome `bosses` ja e o VIGIA nesta funcao. O
                # portao de AST afirma a FORMA (uma variavel, nao um literal) e
                # nao o nome, exatamente por isso.
                bosses=regras_de_respawn,
                # O BATISMO. A MESMA instancia que a carga, o aprendiz e a
                # varredura usam, e a MESMA lista viva que o `extrair` le —
                # e por isso que o nome vale no proximo tick, sem reiniciar
                # (D-08).
                acervo=acervo,
                assinaturas_vivas=cal.assinaturas,
                # A GEOMETRIA DE AGORA, para o lote do `/esquecer`.
                #
                # SAI DE `regiao_do_nome` E NAO DO `layout` DIRETO, e a fonte e
                # a MESMA que `carregar_identidades` usou para montar o aviso
                # de arranque ("7 assinatura(s) foram gravadas com a regiao de
                # nome 20x100 e a atual e 20x110"). Ler de outro lugar faria o
                # aviso e o lote discordarem sobre quem esta morto, e o usuario
                # acreditaria no aviso: ele mandaria esquecer sete e receberia
                # seis, sem nenhuma explicacao possivel.
                forma_esperada=(regiao_do_nome.altura, regiao_do_nome.largura),
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

            # DEPOIS do aviso acima, e a ordem e a decisao: o usuario le a
            # verdade honesta ("nao estou vendo a party") aos 30 ticks, e so
            # aos 45 o scanner comeca a PROCURAR a party window na janela.
            #
            # O laco entrega o numero de ticks cegos e recebe uma calibracao
            # nova ou `None`; quem decide se procura, se adota e o que adotar e
            # o `reancoragem`, e ele reaponta a fonte junto. Aqui so trocamos o
            # `cal` que o status desenha e o que a sessao le a partir do proximo
            # frame.
            #
            # O `try` existe porque esta busca e um EXTRA: um scanner que morre
            # calado e pior do que nenhum scanner, e nada nela pode derrubar o
            # laco que vigia a party.
            if reancorador is not None:
                try:
                    adotada = reancorador.talvez_reancorar(sessao.ticks_cego, cal)
                except Exception:
                    log.exception(
                        "A busca da party window falhou. Sigo com a "
                        "calibracao de sempre."
                    )
                else:
                    if adotada is not None:
                        cal = adotada
                        sessao.cal = adotada

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
            # A verdade do disco ao lado do contador. O criterio da fase e "o
            # contador bate com os arquivos no disco", e a unica forma de
            # provar isso sem sair do console e imprimir os dois numeros lado
            # a lado — mesma filosofia do "snapshots hoje" ser um COUNT(*).
            # `is_file` de proposito: um diretorio com nome de PNG (o modo de
            # falha deterministico dos testes) seria contado por um glob cru,
            # reintroduzindo a mentira dentro da propria conferencia.
            no_disco = sum(
                1 for caminho in gravador.pasta.glob("frame_*.png") if caminho.is_file()
            )
            # Com falhas OU com divergencia o bloco sobe para ERROR: uma sessao
            # parcialmente perdida no fim de uma hora de farm nao pode passar
            # despercebida no meio das linhas de rotina. A divergencia entra na
            # conta porque o contador em memoria e a testemunha que nao da para
            # interrogar aqui — ele ja ficou em zero com um frame se perdendo.
            divergiu = alarme_de_divergencia(gravador.frames_gravados, no_disco)
            registrar = (
                log.error
                if (gravador.falhas_de_gravacao or divergiu)
                else log.info
            )
            registrar(
                "Sessao gravada: %d frames confirmados, %d falhas de escrita, "
                "em %s (no disco: %d frame_*.png)%s",
                gravador.frames_gravados,
                gravador.falhas_de_gravacao,
                gravador.pasta,
                no_disco,
                divergiu,
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
    parser.add_argument(
        "--record-janela",
        action="store_true",
        dest="record_janela",
        help=(
            "grava a JANELA COMPLETA do jogo em vez do recorte da party "
            "window (implica --record, exige --janela). Necessario para o "
            "spike do mercado: o painel so cabe num frame completo. "
            "CUSTO MEDIDO: cerca de 3,5 MB por frame, cerca de 210 MB por "
            "minuto a 1 Hz — use sessoes de 30 a 60 segundos."
        ),
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
    parser.add_argument(
        "--mercado",
        action="store_true",
        help=(
            "roda SO a leitura do World Exchange, como TERCEIRA invocacao ao "
            "lado das duas de party. NAO vigia a party e NAO envia alerta "
            "nenhum: so le o painel e grava em .mercado/. Exige --janela."
        ),
    )
    parser.add_argument("-v", "--verboso", action="store_true", help="log detalhado")

    args = parser.parse_args()

    # Pedir a janela completa e pedir gravacao — obrigar as duas flags juntas
    # so criaria uma combinacao errada a mais para o usuario acertar.
    args.record = args.record or args.record_janela
    # O --replay vem ANTES do --janela: com uma sessao gravada nao existe
    # janela nenhuma, e mandar acrescentar --janela seria conselho errado.
    if args.record_janela and args.replay:
        parser.error(
            "--record-janela nao funciona com --replay: uma sessao gravada "
            "nao tem janela para capturar, so os PNGs que ja estao no disco."
        )
    if args.record_janela and not args.janela:
        parser.error(
            "--record-janela exige --janela: so o caminho da janela expoe a "
            "janela completa (capturar_completo). O caminho `mss` captura o "
            "desktop composto e nao tem a janela do jogo como unidade."
        )
    if args.mercado and not args.janela:
        parser.error(
            "--mercado exige --janela: o painel do World Exchange e procurado "
            "na JANELA INTEIRA porque ele anda, e so o caminho da janela a "
            "expoe como unidade."
        )

    # A JANELA VAI JUNTO, e e o que da um arquivo de log a cada instancia.
    #
    # Aqui `args.janela` ainda pode ser `"AUTO"` - a resolucao contra
    # `cal.janela` so acontece depois de a calibracao carregar, e ela NAO pode
    # subir para antes: a recusa de `ToleranciaAlemDoTeto` e a de
    # `CalibracaoInvalida` precisam de um manipulador de log JA instalado para
    # chegar ao usuario sem virar traceback cru. Por isso `nome_da_instancia`
    # espia o `calibration.json` por conta propria, de forma tolerante: o
    # arranque mais comum do usuario (`vigiar-party.bat`, que passa `--janela`
    # sem valor) e exatamente o caso `"AUTO"`, e sem essa espiada as duas
    # instancias voltariam a dividir o mesmo arquivo.
    configurar_log(args.verboso, janela=args.janela)

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
        try:
            return laco_da_agenda(args)
        except ConfiguracaoPerigosa as erro:
            log.error("%s", erro)
            return 2

    # OS AJUSTES DO APRENDIZ SAO LIDOS AQUI, E A POSICAO E METADE DO CONSERTO.
    #
    # ANTES de qualquer fonte de captura, e antes ate da calibracao: a recusa
    # por configuracao tem de acontecer antes de o programa olhar para a tela,
    # porque e antes de olhar para a tela que o usuario ainda esta no console.
    # Dentro de `laco_principal` a leitura ficaria depois de `MssSource` /
    # `JanelaSource`, e provar "codigo 2 e sem traceback" exigiria uma fonte de
    # captura viva — quebrando "demonstravel com o jogo fechado" justamente onde
    # essa linha custa alguma coisa.
    #
    # O `try` E LOCAL, E NAO O BLOCO GRANDE LA EMBAIXO, e a razao e a POSICAO.
    # Aquele `try` comeca depois do `--mercado`, que constroi fonte de captura;
    # a recusa por tolerancia tem de acontecer ANTES dela. O desfecho e o mesmo
    # de `BossInvalido` e de `ConfiguracaoPerigosa`, e de proposito: mensagem,
    # sem traceback, codigo 2. Uma tolerancia alem do teto produziria
    # assinaturas de duas pessoas misturadas num acervo IRREVERSIVEL, e o
    # estrago so apareceria depois, como uma pessoa que parou de ser
    # reconhecida em silencio. Subir com ela e pior do que nao subir.
    try:
        ajustes_do_aprendiz = ler_ajustes_do_aprendiz()
    except ToleranciaAlemDoTeto as erro:
        log.error("%s", erro)
        return 2

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

    # AQUI, e nao junto do --so-agenda: ao contrario da agenda, este modo OLHA
    # para a tela, e sair antes duplicaria a verdade sobre como a janela e
    # escolhida.
    if args.mercado:
        from .mercado_modo import laco_do_mercado

        return laco_do_mercado(args, cal)

    # DEPOIS da calibracao e da resolucao do --janela AUTO, e nao junto do
    # --testar-agenda: diferente da agenda, esta ferramenta precisa das duas.
    if args.testar_manutencao:
        try:
            return comando_testar_manutencao(args, cal)
        except JanelaNaoEncontrada as erro:
            log.error("%s", erro)
            return 2

    try:
        return laco_principal(args, cal, ajustes_do_aprendiz)
    except JanelaNaoEncontrada as erro:
        log.error("%s", erro)
        return 2
    except BossInvalido as erro:
        # RECUSAR A SUBIR, com a mensagem e sem traceback (VIGI-03). Um
        # `[[boss]]` torto tem que parar o arranque enquanto o usuario olha
        # para o console — nunca virar, na Fase 2, uma janela de respawn
        # impossivel entregue horas depois com a mesma cara de uma certa.
        #
        # Isto e deliberadamente MELHOR do que o que `AgendaInvalida` faz hoje
        # (sobe como traceback), e o precedente esta neste mesmo bloco:
        # `CalibracaoInvalida` e `ConfiguracaoPerigosa` sao as duas recusas de
        # configuracao do projeto e as duas fazem exatamente isto.
        # `AgendaInvalida` e a excecao, nao o modelo — e nao e consertada aqui,
        # porque mexer no desfecho de um campo que o usuario ja usa nao
        # pertence a esta fase.
        log.error("%s", erro)
        return 2
    except ConfiguracaoPerigosa as erro:
        # RECUSAR A SUBIR e o desfecho certo, e nao um aviso: enquanto a
        # colisao dono contra membro existir, um party-mate alcanca .corrigir
        # e .pegou. Um scanner que nao liga ate o numero ser desambiguado e
        # menos ruim que uma escalada de privilegio dentro de uma estatistica
        # permanente que ninguem faz backup.
        log.error("%s", erro)
        return 2


if __name__ == "__main__":
    sys.exit(main())
