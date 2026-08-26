"""Configuracao do usuario: o .env com os dados do Chatwoot.

Separado da calibracao de proposito: isto aqui e escrito a mao e nunca
sobrescrito por ferramenta; a calibracao e o contrario.

O token nunca aparece em log nem em mensagem de erro.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from .agenda import (
    DIAS_DA_SEMANA,
    TODOS_OS_DIAS,
    AgendaInvalida,
    EventoAgendado,
)

# `Membro` nasce no `comandos.py` e nao aqui por causa da direcao das
# importacoes, que ja e fixa no pacote: `config -> comandos -> loot -> agenda`.
# Definir `Membro` neste arquivo obrigaria `comandos` a importar `config`, e o
# ciclo fecharia no primeiro uso.
from .comandos import DIGITOS_FINAIS_DO_TELEFONE, Membro, so_digitos
from .loot import NICK_VALIDO, apelido
from .notificador import ConfigChatwoot

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_ENV = RAIZ / ".env"


class ConfigAusente(Exception):
    """Falta configuracao para enviar alertas."""


def ler_env(caminho: Path | None = None) -> dict[str, str]:
    """Le o .env sem depender de biblioteca externa."""
    caminho = caminho or ARQUIVO_ENV
    if not caminho.exists():
        return {}

    valores: dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        valores[chave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def config_do_chatwoot(caminho: Path | None = None) -> ConfigChatwoot:
    """Monta a configuracao de envio, ou explica exatamente o que falta."""
    env = ler_env(caminho)

    if not env:
        raise ConfigAusente(
            "Nao encontrei o .env.\n"
            "Copie ENV-EXEMPLO.txt para .env e preencha os dados do Chatwoot."
        )

    faltando = [
        chave
        for chave in ("CHATWOOT_URL", "CHATWOOT_ACCOUNT", "CHATWOOT_TOKEN")
        if not env.get(chave)
    ]
    if faltando:
        raise ConfigAusente("Faltam valores no .env: " + ", ".join(faltando))

    if env["CHATWOOT_TOKEN"] == "cole_seu_token_aqui":
        raise ConfigAusente("O CHATWOOT_TOKEN ainda esta com o valor de exemplo.")

    conversas = [
        pedaco.strip()
        for pedaco in env.get("CHATWOOT_CONVERSAS", "").split(",")
        if pedaco.strip()
    ]
    if not conversas:
        raise ConfigAusente(
            "CHATWOOT_CONVERSAS esta vazio no .env.\n"
            "Rode:  python tools/check_whatsapp.py conversas"
        )

    # Conversas de onde o scanner ACEITA COMANDO. Separada das de aviso de
    # proposito, e vazia por padrao — abrir a volta e abrir superficie, e isso
    # nao pode acontecer por acidente de configuracao.
    #
    # Medido no Chatwoot do usuario: a conta tem 22 conversas e 11 com
    # mensagens de entrada, de CLIENTES REAIS. Ler todas seria obedecer a
    # clientes. Tambem e por isso que sao separadas: o grupo do WhatsApp nao
    # entrega mensagens de entrada (ingestao de grupo desligada na ponte
    # Baileys), entao da para receber comando no privado e responder no grupo.
    conversas_de_comando = [
        pedaco.strip()
        for pedaco in env.get("CHATWOOT_CONVERSAS_COMANDO", "").split(",")
        if pedaco.strip()
    ]

    return ConfigChatwoot(
        url=env["CHATWOOT_URL"].rstrip("/"),
        conta=env["CHATWOOT_ACCOUNT"],
        token=env["CHATWOOT_TOKEN"],
        conversas=conversas,
        conversas_de_comando=conversas_de_comando,
        telefones_de_comando=[
            p.strip()
            for p in env.get("CHATWOOT_TELEFONES_COMANDO", "").split(",")
            if p.strip()
        ],
        etiqueta_de_comando=env.get("CHATWOOT_ETIQUETA_COMANDO", "").strip(),
    )


# ---------------------------------------------------------------------------
# Agenda de eventos do jogo (config.toml)
#
# Arquivo SEPARADO do .env de proposito, e por dois motivos diferentes:
#
# - do .env, porque o .env guarda um segredo (o token do Chatwoot) e o
#   config.toml e feito para ser aberto, editado a mao e ate versionado.
# - do calibration.json, porque aquele arquivo e ESCRITO pela ferramenta de
#   calibracao. Guardar os horarios la significaria que rodar calibrar.bat
#   apagaria a agenda do usuario.
#
# `tomllib` e stdlib desde o 3.11, entao isto nao custa dependencia nenhuma. E
# ele e SOMENTE LEITURA, o que aqui e vantagem: nada no codigo deve escrever
# este arquivo.
# ---------------------------------------------------------------------------

ARQUIVO_CONFIG = RAIZ / "config.toml"


def ler_agenda(caminho: Path | None = None) -> list[EventoAgendado]:
    """Le os eventos agendados do config.toml.

    ARQUIVO AUSENTE NAO E ERRO. O scanner roda sem agenda nenhuma desde a v1 e
    precisa continuar rodando — quem nunca criou o arquivo nao pode ver o
    programa quebrar por causa de uma funcionalidade que nao pediu.

    Arquivo PRESENTE E MAL FORMADO, sim, e erro — e erro de ARRANQUE. Um
    horario com erro de digitacao tem que derrubar o scanner enquanto o usuario
    olha para o console, nunca as 15h enquanto ele esta AFK.
    """
    caminho = caminho or ARQUIVO_CONFIG
    if not caminho.exists():
        return []

    try:
        with caminho.open("rb") as arquivo:
            dados = tomllib.load(arquivo)
    except tomllib.TOMLDecodeError as erro:
        raise AgendaInvalida(
            f"{caminho.name} nao e um TOML valido: {erro}"
        ) from erro

    return [_evento_de_dict(bruto, i) for i, bruto in enumerate(dados.get("evento", []))]


def _evento_de_dict(bruto: dict, indice: int) -> EventoAgendado:
    """Valida um bloco [[evento]] e diz exatamente o que esta errado.

    A mensagem cita o NOME do evento sempre que ele existe. "O terceiro
    [[evento]] esta errado" faz o usuario contar blocos; "o evento 'Prime' tem
    o dia 'sabado?'" ele conserta em cinco segundos.
    """
    onde = f"evento '{bruto['nome']}'" if bruto.get("nome") else f"[[evento]] #{indice + 1}"

    nome = str(bruto.get("nome", "")).strip()
    if not nome:
        raise AgendaInvalida(f"{onde}: falta o campo 'nome'.")

    horarios_brutos = bruto.get("horarios") or []
    if not horarios_brutos:
        raise AgendaInvalida(
            f"{onde}: 'horarios' esta vazio. Exemplo: horarios = [\"15:00\", \"21:50\"]"
        )

    horarios = []
    for texto in horarios_brutos:
        partes = str(texto).split(":")
        if len(partes) != 2 or not all(p.strip().isdigit() for p in partes):
            raise AgendaInvalida(
                f"{onde}: horario '{texto}' nao esta no formato HH:MM."
            )
        hora, minuto = int(partes[0]), int(partes[1])
        if not (0 <= hora <= 23 and 0 <= minuto <= 59):
            raise AgendaInvalida(
                f"{onde}: horario '{texto}' nao existe. Use de 00:00 a 23:59."
            )
        horarios.append((hora, minuto))

    dias_brutos = bruto.get("dias")
    if dias_brutos is None:
        dias = TODOS_OS_DIAS
    else:
        dias = set()
        for texto in dias_brutos:
            chave = str(texto).strip().lower()
            if chave not in DIAS_DA_SEMANA:
                aceitos = "seg, ter, qua, qui, sex, sab, dom"
                raise AgendaInvalida(
                    f"{onde}: dia '{texto}' nao existe. Use: {aceitos}."
                )
            dias.add(DIAS_DA_SEMANA[chave])
        if not dias:
            raise AgendaInvalida(f"{onde}: 'dias' esta vazio.")
        dias = frozenset(dias)

    antes = bruto.get("avisar_minutos_antes", 10)
    if not isinstance(antes, int) or antes < 0:
        raise AgendaInvalida(
            f"{onde}: 'avisar_minutos_antes' precisa ser um numero inteiro >= 0."
        )

    no_horario = bruto.get("avisar_no_horario", True)
    if not isinstance(no_horario, bool):
        raise AgendaInvalida(
            f"{onde}: 'avisar_no_horario' precisa ser true ou false."
        )

    # Booleano rejeitado EXPLICITAMENTE, e isso e a diferenca deliberada em
    # relacao ao bloco de `avisar_minutos_antes` logo acima.
    #
    # `isinstance(True, int)` e verdadeiro em Python. Sem esta linha,
    # `chamar_minutos_antes = true` — a confusao mais provavel, porque o campo
    # irmao `avisar_no_horario` E booleano — passaria como "chamar 1 minuto
    # antes": uma chamada inutil, entregue 12 vezes por dia, sem um unico erro
    # no console. O campo antigo carrega esse buraco e nao e consertado aqui:
    # mudar o comportamento de um campo que o usuario ja usa nao pertence a
    # esta fase.
    chamar = bruto.get("chamar_minutos_antes", 0)
    if isinstance(chamar, bool) or not isinstance(chamar, int) or chamar < 0:
        raise AgendaInvalida(
            f"{onde}: 'chamar_minutos_antes' precisa ser um numero inteiro >= 0 "
            f"(use 0 ou apague a linha para nao chamar ninguem)."
        )

    silenciar = bruto.get("silenciar_minutos", 0)
    if not isinstance(silenciar, int) or silenciar < 0:
        raise AgendaInvalida(
            f"{onde}: 'silenciar_minutos' precisa ser um numero inteiro >= 0."
        )

    return EventoAgendado(
        nome=nome,
        horarios=tuple(horarios),
        dias=frozenset(dias),
        avisar_minutos_antes=antes,
        avisar_no_horario=no_horario,
        chamar_minutos_antes=chamar,
        silenciar_minutos=silenciar,
    )


# ---------------------------------------------------------------------------
# Os party-mates que podem dar `.join` e `.leave` (config.toml, [[membro]])
#
# MORA AQUI, E NAO NO .env, E A ASSIMETRIA COM O `CHATWOOT_TELEFONES_COMANDO`
# E PROPOSITAL. Aquele telefone mora no `.env` porque acompanha o token do
# Chatwoot, e o `.env` e o arquivo que ninguem abre sem motivo. O telefone de
# um party-mate nao e segredo nenhum: ele ja esta na agenda de todo mundo do
# grupo. O que ele precisa e de um arquivo feito para ser aberto e editado a
# mao quando alguem entra ou sai da party — e esse arquivo e o config.toml,
# que ainda por cima aceita comentario explicando o que cada campo faz.
# ---------------------------------------------------------------------------


def ler_membros(caminho: Path | None = None) -> list[Membro]:
    """Le os party-mates do config.toml.

    Mesma disciplina de `ler_agenda`, logo acima, e pelas mesmas razoes.

    ARQUIVO AUSENTE NAO E ERRO: quem nunca criou o config.toml, ou nunca
    declarou um `[[membro]]`, fica com a lista vazia e o scanner continua
    subindo com o nivel de dono funcionando como sempre funcionou.

    ARQUIVO PRESENTE E MAL FORMADO E ERRO DE ARRANQUE. Aqui isso pesa mais que
    na agenda: um telefone com erro de digitacao nao produz mensagem de erro
    nenhuma no meio do farm — ele produz um `.join` que some em silencio, e
    quem digitou conclui que o bot esta quebrado.

    Reusa `AgendaInvalida` em vez de criar excecao propria de proposito: ela ja
    E a excecao de "o config.toml nao faz sentido", ja e capturada onde o
    arranque quer capturar, e ja derruba o scanner com o usuario olhando para o
    console. Uma segunda classe duplicaria esse tratamento sem ganhar nada.
    """
    caminho = caminho or ARQUIVO_CONFIG
    if not caminho.exists():
        return []

    try:
        with caminho.open("rb") as arquivo:
            dados = tomllib.load(arquivo)
    except tomllib.TOMLDecodeError as erro:
        raise AgendaInvalida(f"{caminho.name} nao e um TOML valido: {erro}") from erro

    membros = [
        _membro_de_dict(bruto, i) for i, bruto in enumerate(dados.get("membro", []))
    ]
    _recusar_nicks_repetidos(membros)
    return membros


def _recusar_nicks_repetidos(membros: list[Membro]) -> None:
    """Dois `[[membro]]` nao podem dividir a mesma vaga na lista de presenca.

    A lista e indexada por `apelido(nick)`, entao dois blocos que reduzem ao
    mesmo slug disputam o arquivo `presenca_<chave>_<slug>`: o segundo a mandar
    `.join` recebe "voce ja esta na lista" sem nunca ter entrado, e o `.leave`
    de um tira o outro. `nomes_dos_membros` tambem colapsa em silencio, porque
    e um dict por slug.

    E o MESMO modo de falha que `colisoes_de_telefone` trata no eixo do
    telefone, deixado aberto no eixo do nick — e aqui ele nem precisa de aviso,
    porque nao existe caso legitimo de dois party-mates com o mesmo nick: o
    servidor nao permite.

    A comparacao e pelo SLUG e nao pelo texto: `Kaus` e `kaus` sao dois blocos
    diferentes no TOML e o mesmo arquivo em disco.
    """
    vistos: dict[str, str] = {}
    for membro in membros:
        slug = apelido(membro.nick)
        anterior = vistos.get(slug)
        if anterior is not None:
            raise AgendaInvalida(
                f"membro '{membro.nick}': o nick colide com '{anterior}' — dois "
                f"blocos [[membro]] nao podem dividir a mesma vaga na lista de "
                f"presenca. Use nicks diferentes, ou apague o bloco repetido."
            )
        vistos[slug] = membro.nick


def _membro_de_dict(bruto: object, indice: int) -> Membro:
    """Valida um bloco [[membro]] e diz exatamente o que esta errado.

    Mesmo padrao de `onde` do `_evento_de_dict`: cita o NICK sempre que ele
    existe, porque "o segundo [[membro]] esta errado" faz o usuario contar
    blocos e "o membro 'Korzis' esta sem telefone" ele conserta em cinco
    segundos.

    O nick passa pelo mesmo `NICK_VALIDO` que o `loot.py` usa para designar
    quem pega o loot. Um charset so para os dois lados, senao um nick aceito
    aqui seria recusado no `.loot-<nick>` e o registro de presenca e o de loot
    falariam de pessoas diferentes.

    O `bruto` chega como `object` e a PRIMEIRA coisa que acontece e a checagem
    de tipo. `membro = "Kaus"` no lugar de `[[membro]]` e o erro exato que um
    nao-desenvolvedor comete, e sem esta linha ele produzia
    `AttributeError: 'str' object has no attribute 'get'` — um traceback que
    nao diz uma palavra sobre o config.toml, que e o oposto do contrato escrito
    na docstring de `ler_membros`.

    O telefone precisa de pelo menos `DIGITOS_FINAIS_DO_TELEFONE` digitos.
    Nao e capricho: e o corte que `telefone_equivalente` usa para comparar, e
    um numero mais curto que ele casa por igualdade completa com qualquer
    entrada cujo sufixo bata — quer dizer, uma allowlist configurada com menos
    digitos do que o scanner compara nao e uma allowlist, e um convite.
    """
    if not isinstance(bruto, dict):
        raise AgendaInvalida(
            f"[[membro]] #{indice + 1}: precisa ser um bloco [[membro]] com "
            f"nick e telefone, e nao {type(bruto).__name__}. Escreva assim:\n"
            '  [[membro]]\n  nick = "Kaus"\n  telefone = "+5544999998888"'
        )

    onde = f"membro '{bruto['nick']}'" if bruto.get("nick") else f"[[membro]] #{indice + 1}"

    nick = str(bruto.get("nick", "")).strip()
    if not nick:
        raise AgendaInvalida(f"{onde}: falta o campo 'nick'.")
    if not NICK_VALIDO.fullmatch(nick):
        raise AgendaInvalida(
            f"{onde}: nick '{nick}' nao serve. Use de 2 a 16 letras ou numeros, "
            "sem espaco e sem acento — o mesmo nick que aparece no jogo."
        )

    telefone = str(bruto.get("telefone", "")).strip()
    if not telefone:
        raise AgendaInvalida(
            f"{onde}: falta o campo 'telefone'. Exemplo: telefone = \"+5544999998888\""
        )
    digitos = so_digitos(telefone)
    if not digitos:
        raise AgendaInvalida(
            f"{onde}: telefone '{telefone}' nao tem digito nenhum."
        )
    if len(digitos) < DIGITOS_FINAIS_DO_TELEFONE:
        raise AgendaInvalida(
            f"{onde}: telefone '{telefone}' tem so {len(digitos)} digito(s). "
            f"O scanner compara os {DIGITOS_FINAIS_DO_TELEFONE} digitos finais, "
            f"e um numero mais curto que isso casa com gente demais. "
            'Escreva o numero inteiro, com DDD: "+5544999998888".'
        )

    return Membro(nick=nick, telefone=telefone)
