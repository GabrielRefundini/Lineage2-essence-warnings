"""O que a ponte precisa saber antes de conectar: a secao `[discord]` e o token.

ZERO IMPORT DE TERCEIRO NESTE ARQUIVO, e o motivo e medido, nao estetico. O
`pytest` deste repositorio roda no Python GLOBAL (3.12.10, com pytest e cv2); o
`discord` foi instalado no `.venv` de producao, que NAO tem pytest. Qualquer
arquivo de teste que importasse `discord`, mesmo por tabela, morreria na COLETA
e levaria a suite inteira junto. Por isso a ponte e tres modulos: este e o
`ponte_nucleo.py` sao stdlib pura, e so o `ponte_discord.py` escreve
`import discord`.

ARQUIVO OU SECAO AUSENTE E ERRO — e aqui esta o CONTRASTE DELIBERADO com o
resto do repositorio. `ler_agenda` (`config.py:144-151`) decidiu que "arquivo
ausente nao e erro", e esta certa: a agenda e um ACESSORIO de um scanner que
roda perfeitamente sem ela, e o mercado seguiu o mesmo caminho pela mesma razao.
A ponte nao e acessorio de nada: e um PROCESSO DEDICADO que nao tem o que fazer
sem saber quais canais ouvir. Subir muda seria o pior resultado possivel — o
usuario olhando um console vivo, esperando um anuncio que nunca poderia chegar.
Falhar no arranque, com o nome da chave que falta, e o unico desfecho honesto
(CONF-03).

O TOKEN NUNCA APARECE EM MENSAGEM DE ERRO. Ele vem do `.env` pela chave
`DISCORD_TOKEN`, lido pelo `ler_env` de 13 linhas que o repositorio ja tem — e
nao por um segundo parser escrito aqui. A primeira coisa que um usuario faz
quando o programa reclama e fotografar o console e mandar no grupo; uma
mensagem de erro que despeje o `.env` transforma esse reflexo num vazamento
(CONF-01).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .config import ler_env

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_CONFIG = RAIZ / "config.toml"

# A chave do segredo. Segue o formato das que ja existem no `.env`
# (`CHATWOOT_URL`, `CHATWOOT_ACCOUNT`, `CHATWOOT_TOKEN`): MAIUSCULA com
# underscore, prefixada pelo servico.
CHAVE_DO_TOKEN = "DISCORD_TOKEN"

# As chaves obrigatorias da secao, na ordem em que o usuario as le no arquivo.
CHAVES_OBRIGATORIAS = ("guild", "canais", "conversa_de_destino", "simulacao")


class PonteInvalida(Exception):
    """Falta configuracao para a ponte subir, ou ela esta mal escrita.

    Irma de `AgendaInvalida` e `CalibracaoInvalida`: substantivo + adjetivo, em
    portugues, e capturada no `main` com `log.error("%s", erro); return 2` —
    nunca um traceback cru na cara de quem so deu dois cliques num `.bat`.
    """


@dataclass(frozen=True)
class ConfigDaPonte:
    """Tudo que a ponte precisa e que NAO e segredo.

    Ids de canal e de servidor moram no `config.toml` versionado de proposito,
    pelo mesmo raciocinio de `config.py:266-289`: eles nao sao segredo, e
    versiona-los e o que permite um teste ler o arquivo de verdade e pegar um
    id quebrado antes do farm. Segredo e so o token, e ele mora no `.env`.
    """

    guild: int
    canais: frozenset[int]
    conversa_de_destino: str
    simulacao: bool


def ler_config_da_ponte(caminho: Path | None = None) -> ConfigDaPonte:
    """Le a secao `[discord]` do config.toml. Ausencia e ERRO — ver o modulo.

    Nesta fase a validacao e o minimo que faz a fatia rodar: chave que falta
    levanta nomeando a chave. O rigor completo (tipo, faixa, a armadilha de
    `bool` ser subclasse de `int`, e o guarda de higiene da conversa de
    destino) e o `01-02-PLAN.md`, que existe justamente para "morrer alto no
    arranque" ser tratado como trabalho de verdade e nao como enfeite.
    """
    caminho = caminho or ARQUIVO_CONFIG

    if not caminho.exists():
        raise PonteInvalida(
            f"Nao encontrei o {caminho.name}, que e onde fica a secao [discord].\n"
            f"Ele deveria estar na raiz do projeto, ao lado do ponte-discord.bat."
        )

    try:
        with caminho.open("rb") as arquivo:
            dados = tomllib.load(arquivo)
    except tomllib.TOMLDecodeError as erro:
        raise PonteInvalida(f"{caminho.name} nao e um TOML valido: {erro}") from erro

    secao = dados.get("discord")
    if not isinstance(secao, dict):
        raise PonteInvalida(
            f"{caminho.name} nao tem a secao [discord].\n"
            f"A ponte e um processo dedicado: sem essa secao ela nao sabe qual "
            f"servidor abrir nem quais canais ouvir, e subir muda seria pior do "
            f"que nao subir. Copie o bloco [discord] do config.toml do "
            f"repositorio e preencha."
        )

    faltando = [chave for chave in CHAVES_OBRIGATORIAS if chave not in secao]
    if faltando:
        raise PonteInvalida(
            f"Faltam chaves na secao [discord] do {caminho.name}: "
            f"{', '.join(faltando)}."
        )

    return ConfigDaPonte(
        guild=int(secao["guild"]),
        canais=frozenset(int(canal) for canal in secao["canais"]),
        conversa_de_destino=str(secao["conversa_de_destino"]),
        simulacao=bool(secao["simulacao"]),
    )


def ler_token_do_discord(caminho: Path | None = None) -> str:
    """O token do bot, do `.env`. A mensagem de erro NUNCA cita o valor.

    Reusa o `ler_env` do `config.py` em vez de escrever um segundo parser de
    `.env`: dois parsers do mesmo formato divergem no primeiro caso esquisito
    (aspas, espaco em volta do `=`), e ai o token "existe" para um e nao para o
    outro.
    """
    env = ler_env(caminho)

    if not env.get(CHAVE_DO_TOKEN):
        raise PonteInvalida(
            f"Falta o {CHAVE_DO_TOKEN} no .env.\n"
            f"Copie o ENV-EXEMPLO.txt para .env e preencha a linha "
            f"{CHAVE_DO_TOKEN}=.\n"
            f"O token sai de https://discord.com/developers/applications, na "
            f"pagina Bot da sua aplicacao, no botao Reset Token.\n"
            f"Os 4 passos completos estao no PORTAO-DISCORD.txt."
        )

    return env[CHAVE_DO_TOKEN]
