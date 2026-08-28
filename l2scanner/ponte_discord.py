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

import logging
import sys

import discord

from .ponte_config import ConfigDaPonte, PonteInvalida, ler_config_da_ponte, ler_token_do_discord
from .ponte_nucleo import Decisao, MensagemRecebida, NucleoDaPonte

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

    def __init__(self, config: ConfigDaPonte, nucleo: NucleoDaPonte) -> None:
        super().__init__(intents=INTENCOES)
        self.config = config
        self.nucleo = nucleo
        self.ultima_vista: str = "(nenhuma ainda)"

    # -- ciclo de vida ------------------------------------------------------

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
        """UMA coisa: normaliza e entrega ao nucleo."""
        resultado = self.nucleo.receber(normalizar(mensagem))

        if resultado.decisao is Decisao.ACEITA:
            self.ultima_vista = resultado.linha
            log.info("%s", resultado.linha)


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


def main() -> int:
    """0 = saiu limpo, 2 = erro de configuracao. No molde de `calibrar.py:943`."""
    configurar_log()

    try:
        config = ler_config_da_ponte()
        token = ler_token_do_discord()
    except PonteInvalida as erro:
        # Idioma de `__main__.py:1994-2002`: a mensagem, nunca o traceback cru.
        log.error("%s", erro)
        return 2

    ponte = Ponte(config, NucleoDaPonte(config.guild, config.canais, id_da_ponte=None))

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
    except discord.PrivilegedIntentsRequired as erro:
        log.error(
            "%s\n\n"
            "A intent MESSAGE CONTENT esta DESLIGADA no painel do Discord.\n"
            "Sem ela o bot conecta, parece saudavel, e recebe toda mensagem com "
            "o texto VAZIO.\n"
            "Conserto: https://discord.com/developers/applications > sua "
            "aplicacao > Bot > Privileged Gateway Intents > MESSAGE CONTENT "
            "INTENT > Save Changes.\n"
            "Os 4 passos completos estao no PORTAO-DISCORD.txt.",
            erro,
        )
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
