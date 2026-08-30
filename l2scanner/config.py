"""Configuracao do usuario: o .env com os dados do Chatwoot.

Separado da calibracao de proposito: isto aqui e escrito a mao e nunca
sobrescrito por ferramenta; a calibracao e o contrario.

O token nunca aparece em log nem em mensagem de erro.
"""

from __future__ import annotations

import logging
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

log = logging.getLogger(__name__)

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

# O irmao IGNORADO pelo git do `config.toml`. So os `[[membro]]` moram
# aqui — o porque esta no comentario da secao de membros, la embaixo.
ARQUIVO_CONFIG_LOCAL = RAIZ / "config.local.toml"

# A secao e a chave da MIRA DA CALIBRACAO, em constante e nao em literal
# repetido. Isto nao e estilo: `tomllib` nao le comentario, entao um teste que
# queira afirmar "a chave DOCUMENTADA e a chave LIDA" so tem como se ancorar no
# TEXTO do `config.toml` — e as duas pontas precisam sair da MESMA constante
# para que renomear qualquer um dos lados quebre o guarda. Uma chave
# documentada com um nome que o codigo nao le deixa o usuario reeditando para
# sempre uma linha que nao faz nada, e nada no mundo o avisa.
SECAO_DO_JOGO = "jogo"
CHAVE_DO_PERSONAGEM = "personagem"


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
# Os party-mates que podem dar `.join` e `.leave` ([[membro]])
#
# MORA NUM TOML, E NAO NO .env, E A ASSIMETRIA COM O `CHATWOOT_TELEFONES_COMANDO`
# E PROPOSITAL. Aquele telefone mora no `.env` porque acompanha o token do
# Chatwoot, e o `.env` e o arquivo que ninguem abre sem motivo. O telefone de
# um party-mate nao e segredo nenhum: ele ja esta na agenda de todo mundo do
# grupo. O que ele precisa e de um arquivo feito para ser aberto e editado a
# mao quando alguem entra ou sai da party — e um TOML ainda por cima aceita
# comentario explicando o que cada campo faz.
#
# MAS NAO NO `config.toml`, QUE E VERSIONADO. Nao ser segredo nao e o mesmo que
# ser do repositorio: o telefone e de OUTRA PESSOA, e o que entra em historico
# de git nao sai mais nem apagando depois. Por isso existe o
# `config.local.toml`, que o .gitignore cobre.
#
# E por que nao foi so por o `config.toml` inteiro no .gitignore, que era mais
# simples: porque `tests/test_agenda.py::TestAgendaRealDoUsuario` le o
# `config.toml` DO REPOSITORIO para afirmar os horarios de TvT, Prime e Solo
# Boss — um dedo errado ali significa a party esperando um TvT que nao vai
# acontecer. Fora do git, aquele guarda passaria a vigiar um exemplo que
# ninguem edita: continuaria verde e pararia de guardar, que e pior do que nao
# existir, porque parece protecao.
#
# Entao a divisao e a mesma que o projeto ja faz entre `config.toml` e
# `calibration.json`: o que e do PROJETO fica versionado (a agenda), o que e da
# MAQUINA nao (a calibracao, e agora os telefones).
# ---------------------------------------------------------------------------


def ler_membros(
    caminho: Path | None = None, caminho_local: Path | None = None
) -> list[Membro]:
    """Le os party-mates do `config.local.toml`, ou do `config.toml`.

    Mesma disciplina de `ler_agenda`, logo acima, e pelas mesmas razoes.

    ARQUIVO AUSENTE NAO E ERRO: quem nunca criou os arquivos, ou nunca declarou
    um `[[membro]]`, fica com a lista vazia e o scanner continua subindo com o
    nivel de dono funcionando como sempre funcionou.

    ARQUIVO PRESENTE E MAL FORMADO E ERRO DE ARRANQUE. Aqui isso pesa mais que
    na agenda: um telefone com erro de digitacao nao produz mensagem de erro
    nenhuma no meio do farm — ele produz um `.join` que some em silencio, e
    quem digitou conclui que o bot esta quebrado.

    Reusa `AgendaInvalida` em vez de criar excecao propria de proposito: ela ja
    E a excecao de "o config.toml nao faz sentido", ja e capturada onde o
    arranque quer capturar, e ja derruba o scanner com o usuario olhando para o
    console. Uma segunda classe duplicaria esse tratamento sem ganhar nada.

    UM ARQUIVO OU O OUTRO, NUNCA A SOMA. Se o `config.local.toml` tem
    `[[membro]]`, ele e a fonte INTEIRA e o `config.toml` e ignorado. Somar os
    dois faria um nick apagado do `config.toml` reaparecer pelo local sem
    ninguem entender por que, e poria a validacao de nick repetido para decidir
    qual dos dois arquivos ganha — decisao que nao tem resposta obvia e que
    ninguem quer descobrir as 2h da manha.

    Quando os DOIS tem bloco, o arranque avisa alto e nomeia o vencedor. Um
    bloco que nao faz nada e invisivel; um bloco que nao faz nada e nao avisa e
    uma armadilha — o usuario reedita a noite inteira o arquivo errado.

    UM `caminho` EXPLICITO LE SO AQUELE ARQUIVO, sem procurar vizinho. E disso
    que depende o guarda que afirma que o `config.toml` do repositorio nao
    carrega telefone de ninguem: se um caminho explicito arrastasse junto o
    `config.local.toml` ao lado, aquele teste passaria a ler a maquina de quem
    o roda. Os dois `None` — que e como o `__main__` chama — sao o unico caso
    em que a precedencia entre os dois arquivos padrao vale.
    """
    if caminho is None and caminho_local is None:
        caminho_local = ARQUIVO_CONFIG_LOCAL
    caminho = caminho or ARQUIVO_CONFIG

    do_versionado = _blocos_de_membro(caminho)
    do_local = _blocos_de_membro(caminho_local)

    if do_local and do_versionado:
        log.warning(
            "ATENCAO: %s e %s tem [[membro]]. Vale o %s; os blocos do %s estao "
            "sendo IGNORADOS e nao autorizam ninguem. Para voltar a usar o %s, "
            "apague os [[membro]] do %s (ou o arquivo).",
            caminho.name,
            caminho_local.name,
            caminho_local.name,
            caminho.name,
            caminho.name,
            caminho_local.name,
        )

    # `or` e a precedencia inteira, escrita numa linha: o local quando ele tem
    # bloco, o versionado quando nao tem. E a validacao abaixo e UMA so, entao
    # nick repetido e telefone curto derrubam o arranque venha de onde vier.
    membros = [
        _membro_de_dict(bruto, i) for i, bruto in enumerate(do_local or do_versionado)
    ]
    _recusar_nicks_repetidos(membros)
    return membros


def _blocos_de_membro(caminho: Path | None) -> object:
    """Os `[[membro]]` crus de um arquivo, ainda sem validar bloco nenhum.

    A leitura e separada da validacao por causa da precedencia: para saber qual
    dos dois arquivos manda e preciso primeiro saber quais tem bloco, e so o
    VENCEDOR e validado. Validar o perdedor derrubaria o arranque por causa de
    um bloco que ja nao tem efeito nenhum — erro que aponta para o arquivo
    errado, que e pior do que erro nenhum.

    Devolve o valor cru de `dados["membro"]` sem normalizar de proposito:
    `membro = "Kaus"` no lugar de `[[membro]]` precisa continuar chegando em
    `_membro_de_dict`, que e quem sabe explicar esse erro exato.

    `caminho` `None` ou ausente e lista vazia, nao erro — ver `ler_membros`.
    TOML quebrado, sim, e erro de arranque, e cita o nome do arquivo, porque
    com dois arquivos em jogo "o TOML esta quebrado" sem dizer qual e um
    convite a editar o errado.
    """
    if caminho is None or not caminho.exists():
        return []

    try:
        with caminho.open("rb") as arquivo:
            dados = tomllib.load(arquivo)
    except tomllib.TOMLDecodeError as erro:
        raise AgendaInvalida(f"{caminho.name} nao e um TOML valido: {erro}") from erro

    return dados.get("membro", [])


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


def ler_personagem_do_jogo(
    caminho: Path | None = None, caminho_local: Path | None = None
) -> str | None:
    """O personagem que a CALIBRACAO deve mirar, vindo de `[jogo] personagem`.

    POR QUE ISSO EXISTE: o usuario roda DOIS clientes ao mesmo tempo. A
    calibracao automatica capturava o desktop inteiro e procurava faixas
    vermelhas na imagem TODA, entao com duas party windows visiveis ela podia
    agrupar barras dos DOIS clientes e deduzir uma geometria que nao e de
    nenhum — gravada CALADA, porque cada passo interno parecia dar certo.

    O NOME VEM DAQUI E SO DAQUI (ou do `--janela` na linha de comando). Um
    `"Yazalaque"` escrito no fonte seria constante magica, certa para uma
    pessoa e errada para todas as outras.

    E o NOME DO PERSONAGEM, nao o titulo inteiro da janela: jogando, o titulo e
    `Personagem - XM Essence`; na tela de login ele COLAPSA para `XM Essence`
    (`cliente.esta_na_tela_de_login`). Uma chave com o titulo inteiro casaria
    nada nesse estado, e a recusa diria "nao achei essa janela" quando a
    verdade e "seu cliente esta no login".

    Mesma disciplina de `ler_membros`, logo acima, e pelas mesmas razoes.

    ARQUIVO, SECAO OU CHAVE AUSENTE NAO E ERRO: sem chave e sem `--janela` nao
    ha mira nenhuma, e a calibracao segue exatamente como sempre seguiu. Quem
    tem um cliente so nao pode ver o `--auto` quebrar por causa de uma
    funcionalidade que nao pediu.

    ARQUIVO PRESENTE E MAL FORMADO E ERRO, e reusa `AgendaInvalida` pelo motivo
    ja escrito na docstring de `ler_membros`: ela JA e a excecao de "o
    config.toml nao faz sentido", ja e capturada onde o arranque quer capturar,
    e uma segunda classe duplicaria esse tratamento sem ganhar nada.

    `config.local.toml` VENCE o `config.toml`, e quando os DOIS trazem a chave
    o aviso nomeia o vencedor. Uma chave que nao faz nada e invisivel; uma
    chave que nao faz nada e nao avisa e uma armadilha — o usuario reedita a
    noite inteira o arquivo errado.

    UM `caminho` EXPLICITO LE SO AQUELE ARQUIVO, sem procurar vizinho. E disso
    que depende o guarda que afirma que o `config.toml` do repositorio nao
    carrega o personagem de ninguem: se um caminho explicito arrastasse junto o
    `config.local.toml` ao lado, aquele teste passaria a ler a maquina de quem
    o roda.
    """
    if caminho is None and caminho_local is None:
        caminho_local = ARQUIVO_CONFIG_LOCAL
    caminho = caminho or ARQUIVO_CONFIG

    do_versionado = _personagem_do_arquivo(caminho)
    do_local = _personagem_do_arquivo(caminho_local)

    if do_local and do_versionado:
        log.warning(
            "ATENCAO: %s e %s tem [%s] %s. Vale o %s ('%s'); o do %s esta "
            "sendo IGNORADO e nao mira ninguem. Para voltar a usar o %s, "
            "apague a chave do %s.",
            caminho.name,
            caminho_local.name,
            SECAO_DO_JOGO,
            CHAVE_DO_PERSONAGEM,
            caminho_local.name,
            do_local,
            caminho.name,
            caminho.name,
            caminho_local.name,
        )

    return do_local or do_versionado


def _personagem_do_arquivo(caminho: Path | None) -> str | None:
    """A chave `[jogo] personagem` de UM arquivo, ja com `strip` aplicado.

    A leitura e separada da precedencia pelo mesmo motivo de
    `_blocos_de_membro`: para saber qual dos dois arquivos manda e preciso
    primeiro saber quais tem a chave.

    Texto so de espacos e AUSENCIA, e nao um alvo chamado "   ": uma mira vazia
    nao casaria janela nenhuma e a recusa citaria um personagem invisivel.
    """
    if caminho is None or not caminho.exists():
        return None

    try:
        with caminho.open("rb") as arquivo:
            dados = tomllib.load(arquivo)
    except tomllib.TOMLDecodeError as erro:
        raise AgendaInvalida(f"{caminho.name} nao e um TOML valido: {erro}") from erro

    bruto = dados.get(SECAO_DO_JOGO, {}).get(CHAVE_DO_PERSONAGEM)
    if bruto is None:
        return None
    # `personagem = ["Alfa", "Beta"]` produziria um alvo que e uma LISTA, e a
    # comparacao com titulo de janela nunca casaria — em silencio, porque nada
    # levanta ao comparar tipos diferentes. Mesmo espirito da recusa que
    # `calibrar_mercado.ler_watchlist` faz para `watchlist` string.
    if not isinstance(bruto, str):
        raise AgendaInvalida(
            f"{caminho.name}: [{SECAO_DO_JOGO}] {CHAVE_DO_PERSONAGEM} precisa "
            f"ser TEXTO, veio {type(bruto).__name__}.\n"
            f'  Exemplo: {CHAVE_DO_PERSONAGEM} = "Yazalaque"'
        )
    return bruto.strip() or None
