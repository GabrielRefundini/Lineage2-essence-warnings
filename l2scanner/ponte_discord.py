"""A metade de ENTRADA da ponte: o unico arquivo do projeto com `import discord`.

O scanner e um laco sincrono de 1 Hz; esta ponte e async e orientada a evento.
Sao PROCESSOS SEPARADOS de proposito (PONTE-05): subir, cair ou reiniciar um nao
afeta o outro, nenhum dos dois toca o `__main__.py` de 2047 linhas, e os dois so
dividem o `.venv`.

POR QUE ESTE ARQUIVO E FINO. Medido: o `pytest` deste repositorio roda no Python
GLOBAL (3.12.10, com pytest e cv2) e o `discord` foi instalado no `.venv` de
producao, que NAO tem pytest. Todo arquivo de teste que importasse `discord`,
direta ou transitivamente, morreria na COLETA e derrubaria a suite inteira. Por
isso a decisao e a de estrutura, nao de gosto: toda a decisao mora no
`ponte_nucleo.py` (stdlib pura, testado), e aqui ficam so a traducao de
`discord.Message` para `MensagemRecebida` e os ganchos de ciclo de vida. A
beirada async nao decide nada.

Fase 1 para no console: sem formato (Fase 2), sem entrega (Fase 3), sem livro de
ja-vistos (`01-03-PLAN.md`). O objetivo unico e o usuario VER o texto de verdade
aparecendo — porque o modo de falha mais caro deste milestone e a ponte parecer
saudavel replicando branco.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import discord

from .ponte_config import (
    ConfigDaPonte,
    PonteInvalida,
    conferir_a_configuracao,
    resumo_da_configuracao,
)
from .ponte_nucleo import (
    CONSERTO_DA_INTENT,
    SAIDA_SE_O_PRE_VOO_ESTIVER_ERRADO,
    Decisao,
    IntentDeConteudoDesligada,
    MensagemRecebida,
    NucleoDaPonte,
    VereditoDoPreVoo,
    veredito_do_pre_voo,
)

log = logging.getLogger("l2scanner.ponte_discord")

# ---------------------------------------------------------------------------
# ASSINATURA MINIMA DE INTENTS. `none()` e a base, e cada bit ligado tem o
# motivo escrito ao lado. Ligar intent "por garantia" amplia a superficie do
# bot E acrescenta clique no portao humano, que e o recurso mais caro da fase.
INTENCOES = discord.Intents.none()
INTENCOES.guilds = True  # 1 << 0  — sem ela, cargo e canal viram "deleted" na Fase 2
INTENCOES.guild_messages = True  # 1 << 9  — e o que dispara o on_message
INTENCOES.message_content = True  # 1 << 15 — PRIVILEGIADA: o texto em si
# valor final: 1 | 512 | 32768 == 33281
#
# A intent SERVER MEMBERS fica DE FORA de proposito: o fallback do
# `clean_content` via `Message.mentions` ja entrega um `Member` com apelido de
# servidor, entao a segunda intent privilegiada seria mais um clique no portao
# humano por nada.


class Ponte(discord.Client):
    """O cliente. Traduz e delega; nao julga.

    Recebe a `ConfigDaPonte` e um `NucleoDaPonte` ja montados. O nucleo nasce
    ANTES desta classe rodar `run()`, e nesse instante `Client.user` ainda e
    `None` — por isso o `on_ready` tem uma responsabilidade que parece
    arrumacao e nao e.
    """

    def __init__(
        self,
        config: ConfigDaPonte,
        nucleo: NucleoDaPonte,
        ignorar_pre_voo: bool = False,
    ) -> None:
        super().__init__(intents=INTENCOES)
        self.config = config
        self.nucleo = nucleo
        self.ignorar_pre_voo = ignorar_pre_voo
        self.ultima_vista: str = "(nenhuma ainda)"

    # -- ciclo de vida ------------------------------------------------------

    async def setup_hook(self) -> None:
        """O PRE-VOO: le as flags da aplicacao ANTES de o WebSocket abrir.

        `Client.login()` chama `GET /applications/@me` e preenche
        `self.application_flags` antes de rodar este gancho e antes do IDENTIFY
        (fonte lida: `client.py:679-693`). Ou seja: aqui da para saber, sem
        adivinhar e sem conectar, se o botao do painel esta ligado.

        A LEITURA E DEFENSIVA DE PROPOSITO. Se `application_flags` nao existir,
        for `None` ou nao tiver os atributos esperados, isso e
        `flags_lidas=False` — "nao consegui ler" — e NUNCA "esta desligada". A
        diferenca entre as duas leituras e a diferenca entre um aviso e um
        milestone travado: recusar aqui por um numero que nao chegou mostraria
        ao usuario uma tela mandando refazer os quatro passos do portao que ele
        acabou de fazer.

        ONDE FICA A LINHA, E POR QUE ELA FICA AI. MEDIDO no `discord.py` 2.7.1
        desta maquina: `ApplicationFlags(0)` e um objeto VALIDO e FALSY, e o
        `login()` faz `if not self._connection.application_flags:
        self._connection.application_flags = self._application.flags` logo antes
        de chamar este gancho. Ou seja, um inteiro 0 depois de um login bem
        sucedido nao se distingue de "o campo nao veio" — e e tambem o estado
        REAL de uma aplicacao recem-criada com a intent desligada, que e
        exatamente o caso que este pre-voo existe para pegar.

        Tratar o 0 como "nao consegui ler" deixaria o pre-voo mudo justamente na
        situacao mais comum, e o criterio da fase (a ponte morre ANTES de abrir o
        WebSocket, com a nossa mensagem) nunca seria cumprido. Entao: objeto de
        flags presente e uma LEITURA, e um 0 lido significa intent desligada.

        O que desarma o risco da leitura errada nao e fingir duvida — e a SAIDA.
        A recusa carrega `SAIDA_SE_O_PRE_VOO_ESTIVER_ERRADO`, que ensina o
        `--ignorar-pre-voo` na propria tela. O medo legitimo do pre-voo
        deterministico era "o usuario fica sem por onde passar"; com a saida
        impressa junto do erro, ele nunca fica.

        ISTO NAO SUBSTITUI A EXCECAO DA BIBLIOTECA. Se a API de flags mentir, o
        gateway ainda fecha com 4014 e a `PrivilegedIntentsRequired` ainda
        aborta o laco mesmo com reconexao ligada (`client.py:773-779`). O
        pre-voo existe para que a mensagem que o usuario LE seja a nossa, em
        portugues, com os cliques — e para que ela chegue antes de a ponte
        parecer saudavel.
        """
        flags_lidas = True
        verificada = False
        limitada = False
        try:
            flags = self.application_flags
            verificada = bool(flags.gateway_message_content)
            limitada = bool(flags.gateway_message_content_limited)
        except (AttributeError, TypeError):
            # `None`, um objeto de outro formato, ou uma versao da biblioteca
            # que renomeou os atributos. Nenhum desses casos e "desligada".
            flags_lidas = False

        veredito = veredito_do_pre_voo(
            flags_lidas=flags_lidas,
            verificada=verificada,
            limitada=limitada,
            ignorar=self.ignorar_pre_voo,
        )

        if veredito is VereditoDoPreVoo.RECUSAR:
            raise IntentDeConteudoDesligada(
                f"{CONSERTO_DA_INTENT}\n\n{SAIDA_SE_O_PRE_VOO_ESTIVER_ERRADO}"
            )

        if veredito is VereditoDoPreVoo.SEGUIR_COM_AVISO:
            motivo = (
                "voce pediu --ignorar-pre-voo"
                if self.ignorar_pre_voo
                else "nao consegui ler as flags da aplicacao no Discord"
            )
            log.warning(
                "%s",
                destacar_no_console(
                    f"PRE-VOO PULADO: {motivo}. A ponte vai subir assim mesmo. "
                    f"Se a intent MESSAGE CONTENT estiver mesmo desligada, a "
                    f"biblioteca vai fechar a conexao e o aviso completo aparece "
                    f"na primeira mensagem vazia."
                ),
            )
            return

        # Caso espelhado: ligada no painel, mas nao declarada no nosso codigo.
        # Sao dois interruptores diferentes e ambos precisam estar ligados; sem
        # esta linha, apagar `INTENCOES.message_content` por engano daria
        # exatamente o mesmo sintoma da intent desligada, com o painel certo.
        if not INTENCOES.message_content:
            raise IntentDeConteudoDesligada(
                "A intent MESSAGE CONTENT esta ligada no painel do Discord, mas "
                "a ponte nao a declarou em INTENCOES.\n"
                "Isso e um erro NOSSO, nao seu: o painel esta certo. Avise quem "
                "cuida do codigo — a linha e INTENCOES.message_content em "
                "l2scanner/ponte_discord.py."
            )

        log.debug("Pre-voo ok: MESSAGE CONTENT ligada no painel.")

    async def on_ready(self) -> None:
        """PRIMEIRO injeta o proprio id no nucleo, DEPOIS loga. Nesta ordem.

        A primeira chamada NAO e arrumacao: e o que faz a PONTE-04 existir fora
        dos testes. O `main` monta o nucleo antes do `run`, quando `self.user`
        ainda e `None`, entao o unico id que o construtor consegue receber e
        `None`. Sem esta injecao o filtro do proprio id NUNCA dispara no
        processo de verdade, enquanto todos os testes seguem verdes — porque
        teste passa o id na mao. Um filtro que so funciona no teste e pior do
        que filtro nenhum, porque ninguem vai procurar por ele; o sintoma
        apareceria so na Fase 3, como laco de entrega.

        O `on_ready` roda de novo a cada IDENTIFY, entao a chamada e
        idempotente de proposito.
        """
        if self.user is not None:
            self.nucleo.definir_id_da_ponte(self.user.id)

        canais = ", ".join(str(canal) for canal in sorted(self.config.canais))
        log.info("Ponte conectada como %s (id %s).", self.user, self.nucleo.id_da_ponte)
        log.info("Servidor: %s", self.config.guild)
        log.info("Ouvindo os canais: %s", canais)

    async def on_resumed(self) -> None:
        log.info("Sessao RETOMADA — nada foi perdido no intervalo.")

    async def on_disconnect(self) -> None:
        # Dispara tambem no ciclo NORMAL de RESUME. Nao e alarme por si so, e
        # por isso e debug: um ERROR aqui treinaria o usuario a ignorar ERROR.
        log.debug("Socket caiu; a biblioteca retoma sozinha.")

    # -- recebimento --------------------------------------------------------

    async def on_message(self, mensagem: discord.Message) -> None:
        """UMA coisa: normaliza e entrega ao nucleo. O aviso NAO engole nada."""
        resultado = self.nucleo.receber(normalizar(mensagem))

        if resultado.decisao is not Decisao.ACEITA:
            return

        self.ultima_vista = resultado.linha
        log.info("%s", resultado.linha)

        if resultado.suspeita_de_intent_desligada:
            # A ORDEM IMPORTA: a linha da mensagem ja foi impressa acima, e e
            # ela que faz o sintoma virar diagnostico — o usuario VE a mensagem
            # vazia e entende o aviso. Trocar a ordem, ou pior, engolir a
            # mensagem, transformaria o detector no proprio problema.
            log.error(
                "%s",
                destacar_no_console(
                    f"MENSAGEM VAZIA de {mensagem.author} no canal "
                    f"{mensagem.channel.id}. Causa provavel: a intent "
                    f"MESSAGE CONTENT foi desligada no painel."
                ),
            )
            log.error("%s", CONSERTO_DA_INTENT)


def destacar_no_console(texto: str) -> str:
    """A moldura do `console.py`, com o import ADIADO e com rede embaixo.

    O `console.destacar` e o certo para isto: `console.py:1-9` diz, com todas as
    letras, que um evento nao pode se perder no meio das linhas de log — e um
    aviso de intent e exatamente esse tipo de evento.

    MAS O IMPORT E ADIADO E PROTEGIDO, e o motivo foi MEDIDO, nao suposto:
    `console` importa `rastreador`, que importa `visao`, que importa `cv2` e
    `numpy`. Um import no topo deste arquivo faria a ponte — um processo que
    so fala com o Discord — morrer no arranque por causa de uma DLL do OpenCV
    quebrada, que nao tem nada a ver com ela. Isso contraria a PONTE-05, que diz
    que subir, cair ou reiniciar um processo nao afeta o outro.

    A rede tambem nao pode falhar calada: se o `console` nao carregar, o aviso
    sai sem moldura, porque um aviso feio ainda avisa e um aviso engolido nao.
    """
    try:
        from .console import destacar

        return destacar(texto)
    except Exception:  # noqa: BLE001
        return f"\n{'*' * 58}\n  {texto}\n{'*' * 58}\n"


def normalizar(mensagem: discord.Message) -> MensagemRecebida:
    """`discord.Message` -> `MensagemRecebida`. A unica traducao do projeto.

    Ela existe para que o nucleo (e portanto toda a suite) nunca precise de um
    objeto do `discord`. Cada campo e lido uma vez, aqui, e daqui para frente a
    mensagem e um dado congelado de stdlib.
    """
    return MensagemRecebida(
        id=mensagem.id,
        canal=mensagem.channel.id,
        autor=mensagem.author.id,
        autor_nome=str(mensagem.author),
        texto=mensagem.content,
        tem_anexo=bool(mensagem.attachments),
        tem_embed=bool(mensagem.embeds),
        tem_figurinha=bool(mensagem.stickers),
        tem_componente=bool(mensagem.components),
        tem_enquete=mensagem.poll is not None,
        e_encaminhamento=bool(mensagem.message_snapshots),
        e_mensagem_de_sistema=mensagem.is_system(),
    )


def configurar_log() -> None:
    """Log de console. O arquivo rotativo proprio da ponte e o OPER-02.

    Copiado (nao importado) de `__main__.py:145-176`, de proposito: importar
    de la amarraria a ponte ao modulo de 2047 linhas que a nota de arquitetura
    do roadmap manda nao tocar, e que esta sendo editado em paralelo.

    O `reconfigure` de stdout importa MAIS aqui do que no scanner. O console do
    Windows abre em cp1252, e esta ponte imprime texto ARBITRARIO de terceiro:
    emoji, cirilico, o que a pessoa digitar no Discord. Sem ele, a primeira
    mensagem com emoji levanta `UnicodeEncodeError` e derruba o handler — a
    ponte ficaria muda por causa de um caractere. O `errors="replace"` e a
    rede: o que a fonte do console nao tem vira `?`, nunca excecao.
    """
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    formato = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S"
    )
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formato)

    log.setLevel(logging.INFO)
    log.addHandler(console)


def montar_argumentos() -> argparse.ArgumentParser:
    """As quatro opcoes da linha de comando. `argparse` da stdlib, e so.

    O `ponte-discord.bat` ja repassa `%*`, entao tudo isto chega ao usuario que
    so da dois cliques — inclusive a valvula de escape, que e o ponto.
    """
    analisador = argparse.ArgumentParser(
        prog="ponte-discord",
        description=(
            "A ponte que repete anuncio do Discord. Sem argumentos, ela conecta."
        ),
    )
    analisador.add_argument(
        "--conferir",
        action="store_true",
        help=(
            "Confere a configuracao e o segredo e sai, SEM conectar em nada. "
            "Nao prova que a intent esta ligada nem que o token e valido: as "
            "duas coisas exigem falar com o Discord."
        ),
    )
    analisador.add_argument(
        "--ignorar-pre-voo",
        action="store_true",
        dest="ignorar_pre_voo",
        help=(
            "Pula a conferencia da intent MESSAGE CONTENT feita antes de "
            "conectar. Use se a ponte recusar subir dizendo que a intent esta "
            "desligada e voce tiver certeza de que ela esta LIGADA no painel. "
            "Isto nao esconde o problema: se ela estiver mesmo desligada, a "
            "biblioteca ainda vai fechar a conexao com o erro dela."
        ),
    )
    analisador.add_argument(
        "--config",
        dest="caminho_config",
        default=None,
        help="Caminho do config.toml. Padrao: o da raiz do projeto.",
    )
    analisador.add_argument(
        "--env",
        dest="caminho_env",
        default=None,
        help="Caminho do .env. Padrao: o da raiz do projeto.",
    )
    return analisador


def main(argumentos: list[str] | None = None) -> int:
    """0 = saiu limpo, 2 = erro de configuracao. No molde de `calibrar.py:943`.

    `--conferir` VALIDA E SAI, sem construir cliente e sem abrir socket. E
    honesto sobre o proprio alcance: ele NAO prova que a intent esta ligada nem
    que o token e valido, porque as duas coisas exigem falar com o Discord.
    Prometer mais do que se confere e exatamente o defeito que este modo existe
    para nao ter.
    """
    configurar_log()
    opcoes = montar_argumentos().parse_args(argumentos)

    caminho_config = Path(opcoes.caminho_config) if opcoes.caminho_config else None
    caminho_env = Path(opcoes.caminho_env) if opcoes.caminho_env else None

    try:
        config, token = conferir_a_configuracao(caminho_config, caminho_env)
    except PonteInvalida as erro:
        # Idioma de `__main__.py:1994-2002`: a mensagem, nunca o traceback cru.
        log.error("%s", erro)
        return 2

    if opcoes.conferir:
        log.info(
            "%s",
            resumo_da_configuracao(
                config,
                tamanho_do_token=len(token),
                caminho_config=caminho_config,
                caminho_env=caminho_env,
            ),
        )
        log.info(
            "Configuracao e segredo estao no lugar. Isto NAO prova que a intent "
            "MESSAGE CONTENT esta ligada nem que o token e valido — as duas "
            "coisas so aparecem ao conectar de verdade."
        )
        return 0

    ponte = Ponte(
        config,
        NucleoDaPonte(config.guild, config.canais, id_da_ponte=None),
        ignorar_pre_voo=opcoes.ignorar_pre_voo,
    )

    try:
        # `log_handler=None` NAO e detalhe. O padrao do parametro e `MISSING`,
        # que nao e `None`, e com ele a propria biblioteca instala um
        # StreamHandler proprio no logger `discord` — um log paralelo que a
        # ponte nao controla, e que o `01-03-PLAN.md` (OPER-02) precisa nao ter.
        #
        # NAO troque a politica de event loop do asyncio: o ProactorEventLoop e
        # o padrao certo no Windows. A receita de trocar para o seletor vem de
        # problemas com `aiodns`, que este projeto nao usa, e custa um teto de
        # 512 sockets.
        ponte.run(token, log_handler=None)
    except IntentDeConteudoDesligada as erro:
        # A NOSSA recusa, vinda do pre-voo em `setup_hook`, antes do IDENTIFY.
        log.error("%s", destacar_no_console("A PONTE NAO VAI SUBIR"))
        log.error("%s", erro)
        return 2
    except discord.PrivilegedIntentsRequired as erro:
        # A REDE DE SEGURANCA. Se a API de flags mentir, o pre-voo deixa passar
        # e o gateway ainda fecha com 4014 — e a biblioteca aborta o laco mesmo
        # com reconexao ligada (`client.py:773-779`). A mensagem dela vem em
        # ingles, entao ela vai acompanhada do nosso texto de conserto.
        log.error("%s", erro)
        log.error("%s", CONSERTO_DA_INTENT)
        return 2
    except discord.LoginFailure:
        log.error(
            "DISCORD_TOKEN invalido ou revogado.\n"
            "Gere outro em https://discord.com/developers/applications > Bot > "
            "Reset Token e cole no .env."
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
