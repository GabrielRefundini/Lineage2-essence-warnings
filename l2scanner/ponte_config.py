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

TIPO ERRADO E RECUSADO, NAO CONVERTIDO. A validacao aqui e escrita a mao, campo
a campo, no molde de `_conferir_as_chaves_de_mercado` (`calibracao.py:519`) e
pelo mesmo motivo: e no arranque, com o usuario olhando o console, que a
mensagem "conserte esta linha" ainda chega a alguem. Nao ha biblioteca de
validacao neste repositorio e nao entra uma aqui — uma dependencia a mais para
onze linhas de `isinstance` seria cara pelo lado errado.

O TOKEN NUNCA APARECE EM MENSAGEM DE ERRO. Ele vem do `.env` pela chave
`DISCORD_TOKEN`, lido pelo `ler_env` de 13 linhas que o repositorio ja tem — e
nao por um segundo parser escrito aqui. A primeira coisa que um usuario faz
quando o programa reclama e fotografar o console e mandar no grupo; uma
mensagem de erro que despeje o `.env` transforma esse reflexo num vazamento
(CONF-01, e a regra ja fixada no cabecalho de `config.py:6`).
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

# A chave que a guarda de higiene consulta. Ela e LIDA e nunca escrita: o
# `notificador.py` e o `__main__.py` nao sao tocados por esta ponte.
CHAVE_DAS_CONVERSAS_DE_COMANDO = "CHATWOOT_CONVERSAS_COMANDO"

# O placeholder que o `config.py:74-75` ja recusa para o CHATWOOT_TOKEN. Mesma
# palavra, mesmo tratamento: quem cola o texto do exemplo merece a linha em
# portugues, e nao um `LoginFailure` em ingles vindo da biblioteca.
VALOR_DE_EXEMPLO_DO_TOKEN = "cole_seu_token_aqui"

# As chaves que NAO tem padrao possivel. `simulacao` fica de fora de proposito:
# ela tem um padrao seguro (`true`, que nao entrega nada a ninguem), e exigir
# uma chave que sabe se virar sozinha so cria arranque abortado por nada.
CHAVES_OBRIGATORIAS = ("guild", "canais", "conversa_de_destino")

# O bloco que a mensagem de erro mostra quando a secao inteira falta. Nomear a
# secao nao basta: quem chegou aqui tem um arquivo que existe e uma secao que
# nao, e ficaria inventando nomes de chave num arquivo que nao escreveu.
BLOCO_DE_EXEMPLO = """[discord]
guild = 936957935572103169
canais = [1536506379752185953, 1538202612762022020]
conversa_de_destino = "28"
simulacao = true"""


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


# ---------------------------------------------------------------------------
# As checagens de tipo, campo a campo
#
# O FORMATO DE TODA MENSAGEM E O MESMO: "nome da chave: o que veio. O
# conserto." Sem o nome, o usuario confere as quatro chaves a olho; sem o que
# veio, ele nao acredita que o erro e dele; sem o conserto, ele fecha a janela.


def _como_veio(valor: object) -> str:
    """Descreve o TIPO em portugues, do jeito que o usuario ve no arquivo.

    `bool` vem antes de `int` de proposito, e nao por estilo: em Python
    `isinstance(True, int)` e verdadeiro, entao a ordem contraria descreveria
    `true` como "um numero" — a mensagem confirmaria para o usuario justamente
    a confusao que a checagem existe para desfazer.
    """
    if isinstance(valor, bool):
        return "true/false"
    if isinstance(valor, int):
        return "um numero"
    if isinstance(valor, float):
        return "um numero com virgula"
    if isinstance(valor, str):
        return "texto entre aspas"
    if isinstance(valor, list):
        return "uma lista"
    return f"um valor do tipo {type(valor).__name__}"


def _exigir_id(valor: object, chave: str, onde: str) -> int:
    """Um id do Discord: inteiro positivo, sem aspas, e NUNCA um booleano.

    A recusa explicita de `bool` e a linha mais importante desta funcao, e ela
    parece redundante ate a hora em que nao e. `isinstance(True, int)` e
    verdadeiro em Python: sem esta linha, `guild = true` passaria como o
    servidor de id 1 — um servidor que existe, que nao e o do usuario, e do
    qual a ponte jamais receberia uma mensagem. A ponte subiria, imprimiria no
    console que esta ouvindo, e ficaria muda para sempre, sem uma unica linha de
    erro. E o mesmo buraco que `calibracao.py:466-480` fecha no
    `chamar_minutos_antes` e que `config.py:229-244` documenta.
    """
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise PonteInvalida(
            f"{onde}: '{chave}' veio como {_como_veio(valor)}, e precisa ser um "
            f"numero inteiro SEM ASPAS.\n"
            f"  Exemplo: {chave} = 936957935572103169\n"
            f"  Para copiar o id: no Discord, Configuracoes do usuario > "
            f"Avancado > Modo de desenvolvedor; depois botao direito no "
            f"servidor ou canal > Copiar ID."
        )
    if valor <= 0:
        raise PonteInvalida(
            f"{onde}: '{chave}' veio como {valor}, e um id do Discord e sempre "
            f"um numero positivo de 17 a 20 digitos."
        )
    return valor


def _exigir_canais(valor: object, onde: str) -> frozenset[int]:
    """A lista de canais: pelo menos um, todos ids, e o repetido nao e erro.

    NADA EXIGE EXATAMENTE DOIS. A lista e do usuario; pinar dois aqui seria
    transformar uma escolha dele em regra do programa, e o primeiro efeito seria
    alguem que so quer ouvir #anuncios ficar sem conseguir subir a ponte.

    Repetir um id, por outro lado, e desatencao com efeito identico ao
    pretendido: o `frozenset` resolve e ninguem precisa saber. Abortar o
    arranque por causa disso seria rigor cobrado da pessoa errada.
    """
    if isinstance(valor, bool) or not isinstance(valor, list):
        raise PonteInvalida(
            f"{onde}: 'canais' veio como {_como_veio(valor)}, e precisa ser uma "
            f"lista de ids entre colchetes.\n"
            f"  Exemplo: canais = [1536506379752185953, 1538202612762022020]"
        )

    if not valor:
        raise PonteInvalida(
            f"{onde}: 'canais' esta vazio, e uma ponte sem canal nenhum nunca "
            f"vai falar.\n"
            f"  Ela subiria, conectaria e ficaria muda para sempre — por isso "
            f"este erro existe.\n"
            f"  Escreva ao menos um id: canais = [1536506379752185953]"
        )

    canais = []
    for posicao, item in enumerate(valor, start=1):
        if isinstance(item, bool) or not isinstance(item, int):
            # NOMEAR O ELEMENTO nao e capricho: com dois ids de 19 digitos lado
            # a lado numa janela de cmd sem quebra de linha, "a lista esta
            # errada" faz o usuario conferir os dois a olho nu.
            raise PonteInvalida(
                f"{onde}: o {posicao}o item de 'canais' e {item!r}, que nao e um "
                f"id valido.\n"
                f"  Ids de canal sao numeros SEM ASPAS. Apague as aspas em volta "
                f"de {item!r} e tente de novo."
            )
        if item <= 0:
            raise PonteInvalida(
                f"{onde}: o {posicao}o item de 'canais' e {item}, e um id do "
                f"Discord e sempre positivo."
            )
        canais.append(item)

    return frozenset(canais)


def _exigir_conversa(valor: object, onde: str) -> str:
    """O id da conversa do Chatwoot e TEXTO neste projeto, e nao numero.

    A assimetria com `guild` e `canais` e deliberada e tem consequencia: as
    conversas do `.env` chegam como texto (`config.py:97-101` parte um CSV com
    `split(",")` e `strip()`), e a guarda de higiene compara texto com texto.
    Aceitar `conversa_de_destino = 28` e converter calado faria `28 != "28"` no
    dia em que alguem escrevesse sem aspas — e a guarda passaria batida
    justamente no caso que ela existe para pegar.
    """
    if not isinstance(valor, str):
        raise PonteInvalida(
            f"{onde}: 'conversa_de_destino' veio como {_como_veio(valor)}, e "
            f"precisa ser texto ENTRE ASPAS.\n"
            f'  Exemplo: conversa_de_destino = "28"\n'
            f"  As aspas nao sao enfeite: o id da conversa viaja como texto no "
            f"resto do projeto, e sem elas a conferencia contra as conversas de "
            f"comando compararia coisas de tipos diferentes e passaria batida."
        )
    return valor


def _exigir_simulacao(secao: dict, onde: str) -> bool:
    """CONF-04: o interruptor e honesto, ou nao existe.

    AUSENTE VALE `true`, que e o padrao que NAO manda mensagem para ninguem.
    Quem esquece a linha nao pode acabar despejando anuncio de guild no WhatsApp
    de sete pessoas sem ter pedido.

    `false` E RECUSADO ENQUANTO A ENTREGA NAO EXISTIR. Na Fase 1 nao ha caminho
    de entrega nenhum escrito. Aceitar a chave e nao fazer nada com ela seria
    pior do que nao ter a chave: o usuario desligaria a simulacao, esperaria as
    mensagens no WhatsApp e nao receberia nada — sem uma linha explicando que a
    entrega ainda nem foi escrita. Uma chave que mente e pior do que uma chave
    ausente.
    """
    if "simulacao" not in secao:
        return True

    valor = secao["simulacao"]
    if not isinstance(valor, bool):
        raise PonteInvalida(
            f"{onde}: 'simulacao' veio como {_como_veio(valor)}, e precisa ser "
            f"true ou false SEM ASPAS.\n"
            f"  Exemplo: simulacao = true"
        )

    if valor is False:
        raise PonteInvalida(
            f"{onde}: 'simulacao = false' ainda nao vale nada nesta versao.\n"
            f"  A entrega no WhatsApp so existe a partir da Fase 3; hoje a ponte "
            f"so mostra no console o que SERIA enviado.\n"
            f"  Deixe 'simulacao = true'. Aceitar false calado faria voce esperar "
            f"mensagens que nao teriam como sair."
        )

    return True


def _conferir_as_chaves_do_discord(secao: dict, onde: str) -> ConfigDaPonte:
    """A validacao inteira da secao `[discord]`, campo a campo, a mao.

    Escrita no molde exato de `_conferir_as_chaves_de_mercado`
    (`calibracao.py:519`): a secao e ENTRADA NAO CONFIAVEL, editada a mao por
    alguem que nao escreveu o programa, e o unico momento em que a mensagem
    "conserte esta linha" ainda alcanca essa pessoa e o arranque.
    """
    faltando = [chave for chave in CHAVES_OBRIGATORIAS if chave not in secao]
    if faltando:
        raise PonteInvalida(
            f"{onde}: faltam chaves na secao [discord]: {', '.join(faltando)}.\n"
            f"  Bloco completo, para conferir:\n\n{BLOCO_DE_EXEMPLO}"
        )

    return ConfigDaPonte(
        guild=_exigir_id(secao["guild"], "guild", onde),
        canais=_exigir_canais(secao["canais"], onde),
        conversa_de_destino=_exigir_conversa(secao["conversa_de_destino"], onde),
        simulacao=_exigir_simulacao(secao, onde),
    )


def ler_config_da_ponte(caminho: Path | None = None) -> ConfigDaPonte:
    """Le e VALIDA a secao `[discord]`. Ausencia e ERRO — ver o cabecalho."""
    caminho = caminho or ARQUIVO_CONFIG
    onde = caminho.name

    if not caminho.exists():
        raise PonteInvalida(
            f"Nao encontrei o {caminho.name}, que e onde fica a secao [discord].\n"
            f"Ele deveria estar na raiz do projeto, ao lado do ponte-discord.bat."
        )

    try:
        with caminho.open("rb") as arquivo:
            dados = tomllib.load(arquivo)
    except tomllib.TOMLDecodeError as erro:
        # NOMEAR O ARQUIVO. Sao dois TOMLs na mesma pasta (`config.toml` e
        # `config.local.toml`): "o TOML esta quebrado" e um convite a editar o
        # que estava certo.
        raise PonteInvalida(f"{caminho.name} nao e um TOML valido: {erro}") from erro

    secao = dados.get("discord")
    if not isinstance(secao, dict):
        raise PonteInvalida(
            f"{onde} nao tem a secao [discord].\n"
            f"A ponte e um processo dedicado: sem essa secao ela nao sabe qual "
            f"servidor abrir nem quais canais ouvir, e subir muda seria pior do "
            f"que nao subir.\n"
            f"Cole este bloco no fim do {onde} e troque os ids pelos seus:\n\n"
            f"{BLOCO_DE_EXEMPLO}"
        )

    return _conferir_as_chaves_do_discord(secao, onde)


def ler_token_do_discord(caminho: Path | None = None) -> str:
    """O token do bot, do `.env`. A mensagem de erro NUNCA cita o valor.

    Reusa o `ler_env` do `config.py` em vez de escrever um segundo parser de
    `.env`: dois parsers do mesmo formato divergem no primeiro caso esquisito
    (aspas, espaco em volta do `=`), e ai o token "existe" para um e nao para o
    outro.

    A CASCATA E DE TRES, como a do `config_do_chatwoot` (`config.py:56-86`), e
    os tres consertos sao DIFERENTES: copiar o exemplo, preencher a linha, ou
    trocar o placeholder por um token de verdade. Uma mensagem so para os tres
    manda dois tercos dos usuarios procurar o que nao esta faltando.

    NENHUMA DAS TRES INTERPOLA O VALOR. Nem para "ajudar a conferir", nem
    truncado, nem no fim de um `f"nao achei nada em {env}"` — e a regra do
    cabecalho de `config.py:6`, e ela existe porque o reflexo de quem ve um erro
    e fotografar o console e mandar no grupo.
    """
    caminho = caminho or (RAIZ / ".env")

    if not caminho.exists():
        raise PonteInvalida(
            f"Nao encontrei o .env, que e onde mora o {CHAVE_DO_TOKEN}.\n"
            f"Copie o ENV-EXEMPLO.txt para .env e preencha a linha "
            f"{CHAVE_DO_TOKEN}=.\n"
            f"Os 4 passos completos estao no PORTAO-DISCORD.txt."
        )

    env = ler_env(caminho)

    if not env.get(CHAVE_DO_TOKEN):
        raise PonteInvalida(
            f"O .env existe, mas falta a linha {CHAVE_DO_TOKEN}= (ou ela esta "
            f"vazia).\n"
            f"O token sai de https://discord.com/developers/applications, na "
            f"pagina Bot da sua aplicacao, no botao Reset Token.\n"
            f"O ENV-EXEMPLO.txt tem a linha pronta para copiar.\n"
            f"Os 4 passos completos estao no PORTAO-DISCORD.txt."
        )

    if env[CHAVE_DO_TOKEN] == VALOR_DE_EXEMPLO_DO_TOKEN:
        raise PonteInvalida(
            f"O {CHAVE_DO_TOKEN} ainda esta com o valor de exemplo.\n"
            f"Troque pelo token de verdade: "
            f"https://discord.com/developers/applications > sua aplicacao > "
            f"Bot > Reset Token > Copy."
        )

    return env[CHAVE_DO_TOKEN]


def _conferir_a_higiene_da_conversa(
    cfg: ConfigDaPonte, caminho_env: Path | None
) -> None:
    """A conversa de destino nao pode ser tambem uma conversa de COMANDO.

    O MOTIVO E ESTE, e so este: quem RESPONDE numa conversa compartilhada manda
    uma mensagem de ENTRADA (`incoming`). Um "ok" ou um "kkkk" de alguem da
    party, numa conversa que tambem esta em `CHATWOOT_CONVERSAS_COMANDO`,
    chegaria ao scanner pelo caminho de comando — e a superficie de comando so
    deve abrir por decisao, nunca por acidente de configuracao.

    E O MOTIVO QUE **NAO** VALE, registrado aqui de proposito: NAO e verdade que
    um anuncio postado pela ponte viraria comando do scanner. Esse caminho ja
    esta fechado por construcao — a ponte posta `outgoing` (`notificador.py:281`)
    e `comandos.py:887` descarta tudo cujo `message_type` nao seja `incoming`,
    regra deliberada e documentada em `comandos.py:20` ("So `incoming`. O
    scanner nunca pode obedecer as proprias mensagens"). Escrever esse risco
    inflado como justificativa seria pior do que nao justificar nada: o primeiro
    leitor que abrisse `comandos.py` veria que e mentira e apagaria a guarda
    inteira, levando junto o risco REAL, que nao e mentira.

    A guarda SOBREVIVEU a revogacao da ENTR-02 (2026-08-28: os anuncios passam a
    ir para a conversa 28, a MESMA dos avisos de morte e saida de party) porque
    ela nunca falou sobre aquilo. Os valores reais do usuario — destino 28,
    comando 1 — nao colidem, entao ela passa e continua de pe para o dia em que
    alguem apontar o destino para a conversa errada.
    """
    if not cfg.conversa_de_destino:
        # Config valida da Fase 1: sem destino, nao ha o que colidir.
        return

    caminho_env = caminho_env or (RAIZ / ".env")
    env = ler_env(caminho_env)

    # `strip()` em cada pedaco, exatamente como `config.py:97-101`: o CSV e
    # escrito a mao, `1, 42` e como uma pessoa escreve, e comparar sem `strip()`
    # deixaria ` 42` diferente de `42` — a guarda ficaria verde, presente e
    # inutil.
    de_comando = {
        pedaco.strip()
        for pedaco in env.get(CHAVE_DAS_CONVERSAS_DE_COMANDO, "").split(",")
        if pedaco.strip()
    }

    if cfg.conversa_de_destino.strip() in de_comando:
        raise PonteInvalida(
            f"conversa_de_destino = \"{cfg.conversa_de_destino}\" tambem esta em "
            f"{CHAVE_DAS_CONVERSAS_DE_COMANDO} no .env.\n"
            f"Quem RESPONDE nessa conversa manda uma mensagem de entrada, e numa "
            f"conversa de comando essa resposta seria lida como comando do "
            f"scanner.\n"
            f"Escolha outra conversa para os anuncios, ou tire este id do "
            f"{CHAVE_DAS_CONVERSAS_DE_COMANDO}."
        )


def conferir_a_configuracao(
    caminho_config: Path | None = None, caminho_env: Path | None = None
) -> tuple[ConfigDaPonte, str]:
    """A PORTA UNICA do arranque: TOML, tipos, segredo e higiene, nesta ordem.

    Uma porta so, e nao duas parecidas, porque o `--conferir` chama exatamente
    esta funcao: com dois caminhos, o modo que existe para provar o arranque
    provaria outro caminho, e a divergencia apareceria justamente no dia em que
    a conferencia dissesse "esta tudo certo" e a ponte nao subisse.

    A ORDEM E PARTE DO CONTRATO. O TOML vem antes do `.env` porque mandar
    preencher o `.env` quando o `config.toml` esta quebrado faz a pessoa mexer no
    arquivo errado e achar que piorou. A higiene vem por ultimo porque ela
    precisa dos dois lados ja lidos.
    """
    cfg = ler_config_da_ponte(caminho_config)
    token = ler_token_do_discord(caminho_env)
    _conferir_a_higiene_da_conversa(cfg, caminho_env)
    return cfg, token


def resumo_da_configuracao(
    cfg: ConfigDaPonte,
    tamanho_do_token: int | None = None,
    caminho_config: Path | None = None,
    caminho_env: Path | None = None,
) -> str:
    """O bloco que o `--conferir` imprime. FUNCAO PURA: nao le arquivo nenhum.

    Pura de proposito. Se ela relesse o `config.toml` por dentro, um
    `--conferir --config outro.toml` imprimiria o arquivo do repositorio e
    afirmaria ter conferido o que nao conferiu — o modo de falha mais caro que
    uma tela de conferencia pode ter.

    A ORIGEM DE CADA VALOR aparece porque sao dois arquivos em jogo: sem dizer
    onde o valor mora, "esse id esta errado" nao diz onde editar.

    O TOKEN NUNCA APARECE. No maximo o resumo diz que ele foi encontrado e
    quantos caracteres tem — o suficiente para o usuario perceber que colou meio
    token, e insuficiente para vazar qualquer coisa num print.
    """
    nome_config = (caminho_config or ARQUIVO_CONFIG).name
    nome_env = (caminho_env or (RAIZ / ".env")).name

    canais = "\n".join(
        f"                          {canal}" for canal in sorted(cfg.canais)
    ).lstrip()

    if tamanho_do_token is None:
        linha_do_token = f"  token                   (nao conferido)   [{nome_env}]"
    else:
        linha_do_token = (
            f"  token                   ENCONTRADO, {tamanho_do_token} "
            f"caracteres   [{nome_env}]"
        )

    destino = cfg.conversa_de_destino or "(vazio — a Fase 1 so simula)"

    return "\n".join(
        [
            "Configuracao da ponte:",
            f"  servidor (guild)        {cfg.guild}   [{nome_config}]",
            f"  canais ouvidos          {canais}   [{nome_config}]",
            f"  conversa_de_destino     {destino}   [{nome_config}]",
            f"  simulacao               {str(cfg.simulacao).lower()}   "
            f"[{nome_config}]",
            linha_do_token,
        ]
    )
