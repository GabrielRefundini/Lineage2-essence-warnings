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
    apelido_do_evento,
)

# `Boss` e `BossInvalido` nascem em `bosses.py` pela mesma razao de direcao das
# importacoes que trouxe `Membro` do `comandos.py`: `bosses` importa SO stdlib,
# entao `config` importa dele sem risco de ciclo. O contrario — declarar `Boss`
# aqui — obrigaria `bosses` a importar `config`, e o ciclo fecharia no primeiro
# uso.
from .bosses import Boss, BossInvalido

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
# Os bosses vigiados ([[boss]])
#
# QUEM E VIGIADO SAI DO CODIGO E VIRA UMA LINHA DO ARQUIVO. Ate a Fase 1 o
# unico mob possivel era o Tiat, escrito numa constante de `tiat.py`; vigiar
# outro exigia editar `.py`. Agora e um bloco a mais aqui, e o scanner nao
# conhece mob nenhum por nome.
#
# A validacao e o espelho de `_evento_de_dict`, de proposito: mesma forma de
# mensagem ("o boss 'X' tem ..."), mesma recusa de subir, mesma regra de
# "arquivo ausente nao e erro". Duas formas diferentes de recusar config no
# mesmo arquivo obrigariam o usuario a aprender duas.
# ---------------------------------------------------------------------------


def ler_bosses(caminho: Path | None = None) -> list[Boss]:
    """Le os blocos [[boss]] do config.toml.

    ARQUIVO AUSENTE NAO E ERRO, e SECAO AUSENTE TAMBEM NAO. O scanner roda sem
    vigilancia de boss nenhuma desde a v1 e precisa continuar rodando: quem
    nunca escreveu um `[[boss]]` nao pode ver o programa quebrar por causa de
    uma funcionalidade que nao pediu (VIGI-04). Quem chama e que decide o que
    fazer com a lista vazia — ver `montar_vigia_de_bosses`.

    Arquivo PRESENTE E MAL FORMADO, sim, e erro, e e erro de ARRANQUE. Um
    `respawn_horas_max` menor que o `min` tem que derrubar o scanner enquanto o
    usuario olha para o console, nunca produzir uma janela impossivel na Fase 2
    enquanto ele esta AFK.
    """
    caminho = caminho or ARQUIVO_CONFIG
    if not caminho.exists():
        return []

    try:
        with caminho.open("rb") as arquivo:
            dados = tomllib.load(arquivo)
    except tomllib.TOMLDecodeError as erro:
        raise BossInvalido(
            f"{caminho.name} nao e um TOML valido: {erro}"
        ) from erro

    bosses = [_boss_de_dict(bruto, i) for i, bruto in enumerate(dados.get("boss", []))]
    _recusar_bosses_repetidos(bosses)
    return bosses


def _boss_de_dict(bruto: object, indice: int) -> Boss:
    """Valida um bloco [[boss]] e diz exatamente o que esta errado.

    Mesmo padrao de `onde` do `_evento_de_dict`: cita o NOME sempre que ele
    existe, porque "o segundo [[boss]] esta errado" faz o usuario contar blocos
    e "o boss 'Tiat North' tem respawn_horas_max menor que o min" ele conserta
    em cinco segundos.

    Os dois campos de respawn sao OBRIGATORIOS, e nao opcionais com default. Um
    boss sem regra de respawn produziria, na Fase 2, silenciosamente nenhuma
    janela — o usuario acrescentaria o bloco, veria o nascimento ser detectado,
    e nunca receberia a previsao, sem uma linha de erro em lugar nenhum.
    """
    if not isinstance(bruto, dict):
        raise BossInvalido(
            f"[[boss]] #{indice + 1}: precisa ser um bloco [[boss]] com nome e "
            f"horas de respawn, e nao {type(bruto).__name__}. Escreva assim:\n"
            '  [[boss]]\n  nome = "Tiat North"\n'
            "  respawn_horas_min = 6\n  respawn_horas_max = 8"
        )

    onde = f"boss '{bruto['nome']}'" if bruto.get("nome") else f"[[boss]] #{indice + 1}"

    nome = str(bruto.get("nome", "")).strip()
    if not nome:
        raise BossInvalido(
            f"{onde}: falta o campo 'nome'. Escreva o nome como ele aparece no "
            'jogo. Exemplo: nome = "Tiat North"'
        )

    minimo = _horas_de_respawn(bruto, "respawn_horas_min", onde)
    maximo = _horas_de_respawn(bruto, "respawn_horas_max", onde)
    if maximo < minimo:
        raise BossInvalido(
            f"{onde}: 'respawn_horas_max' ({maximo:g}) e menor que "
            f"'respawn_horas_min' ({minimo:g}). O maximo e o limite otimista da "
            f"janela, entao ele nunca pode vir antes do minimo."
        )

    return Boss(
        nome=nome,
        respawn_horas_min=minimo,
        respawn_horas_max=maximo,
    )


def _horas_de_respawn(bruto: dict, campo: str, onde: str) -> float:
    """Uma duracao de respawn valida, ou a recusa que nomeia o campo."""
    valor = bruto.get(campo)
    if valor is None:
        raise BossInvalido(
            f"{onde}: falta o campo '{campo}'. Ele e a regra de respawn do "
            f"servidor em horas — para o Tiat, 6 no minimo e 8 no maximo."
        )

    # Booleano rejeitado EXPLICITAMENTE, e ANTES do teste numerico, porque
    # `isinstance(True, int)` e verdadeiro em Python. Sem esta linha,
    # `respawn_horas_min = true` passaria como "1 hora": uma janela errada,
    # entregue com a mesma cara de uma certa, sem um unico erro no console. E o
    # mesmo buraco que o comentario de `chamar_minutos_antes` ja documenta.
    if isinstance(valor, bool):
        raise BossInvalido(
            f"{onde}: '{campo}' precisa ser um numero de horas maior que zero, "
            f"e nao true/false. Exemplo: {campo} = 6"
        )
    if not isinstance(valor, (int, float)):
        raise BossInvalido(
            f"{onde}: '{campo}' precisa ser um numero de horas maior que zero "
            f"(recebi {valor!r}). Exemplo: {campo} = 6"
        )
    # Zero recusado junto com negativo, de proposito: uma regra de respawn de
    # zero hora nao descreve nada, e recusar os dois de uma vez deixa a
    # mensagem mais clara do que dois erros parecidos.
    if valor <= 0:
        raise BossInvalido(
            f"{onde}: '{campo}' precisa ser MAIOR que zero (recebi {valor:g})."
        )
    return float(valor)


def _recusar_bosses_repetidos(bosses: list[Boss]) -> None:
    """Dois `[[boss]]` nao podem dividir o mesmo nome NEM o mesmo apelido.

    A comparacao IGNORA A CAIXA porque o padrao de reconhecimento e
    `IGNORECASE`: `Tiat North` e `tiat north` sao indistinguiveis para o vigia,
    entao os dois blocos disputariam os mesmos sinais e cada aparicao sairia em
    dobro.

    O SEGUNDO EIXO — O APELIDO — NASCEU NA FASE 2, e ele fecha um furo que o
    primeiro nao alcanca. A partir da janela de respawn o `nome` do `[[boss]]`
    vira NOME DE ARQUIVO DURAVEL em `.agenda/`, por `apelido_do_evento`. Dois
    nomes que o `casefold` considera DIFERENTES podem reduzir ao MESMO apelido
    — por espaco duplo, por pontuacao, por hifen — e ai eles passariam por esta
    funcao e depois compartilhariam a MESMA ANCORA em disco. O nascimento de um
    reancoraria a janela do outro, em silencio, e nenhuma mensagem estaria
    errada o bastante para alguem desconfiar (T-02-05).

    `Tiat  North` (dois espacos) e `Tiat North` sao o caso concreto: nomes
    distintos para o `casefold`, e os dois viram `tiat-north`.

    RECUSA TAMBEM O APELIDO VAZIO, pela mesma razao: um `nome` feito so de
    pontuacao reduz a string vazia e produziria um marcador sem identidade,
    colidindo com qualquer outro nome igualmente vazio.

    ISTO E RECUSA DE ARRANQUE, como todo o resto da validacao de `[[boss]]`:
    derruba o scanner enquanto o usuario esta olhando o console, e nunca
    produz uma previsao trocada as duas da manha. O custo e alto e RUIDOSO; a
    alternativa silenciosa e duas janelas dividindo uma ancora.

    Mesmo molde de `_recusar_nicks_repetidos`, nos dois eixos do boss.
    """
    vistos: dict[str, str] = {}
    apelidos: dict[str, str] = {}
    for boss in bosses:
        chave = boss.nome.casefold()
        anterior = vistos.get(chave)
        if anterior is not None:
            raise BossInvalido(
                f"boss '{boss.nome}': o nome colide com '{anterior}' — o "
                f"reconhecimento ignora maiusculas, entao os dois blocos "
                f"vigiariam o mesmo mob e cada nascimento sairia em dobro. "
                f"Apague o bloco repetido."
            )
        vistos[chave] = boss.nome

        apelido = apelido_do_evento(boss.nome)
        if not apelido:
            raise BossInvalido(
                f"boss '{boss.nome}': o nome nao tem nenhuma letra nem numero, "
                f"entao ele nao produz identificador nenhum em disco — a "
                f"janela de respawn nao teria como saber de quem e a contagem. "
                f"Escreva o nome do boss como ele aparece no jogo."
            )
        gemeo = apelidos.get(apelido)
        if gemeo is not None:
            raise BossInvalido(
                f"boss '{boss.nome}': o nome produz o mesmo identificador em "
                f"disco que '{gemeo}' (os dois viram '{apelido}'), entao os "
                f"dois dividiriam a MESMA ancora de respawn e o nascimento de "
                f"um reiniciaria a contagem do outro em silencio. Diferencie "
                f"os dois nomes."
            )
        apelidos[apelido] = boss.nome


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


# ---------------------------------------------------------------------------
# A watchlist do mercado ([mercado] watchlist)
#
# ELA VOLTA COMO FILTRO DE DESTAQUE, NUNCA COMO PORTA DE ENTRADA. Ate a Fase 2
# ela era a lista fechada do que o scanner conseguia ler: um molde de nome por
# item, e item fora dela nao era lido. Em 2026-08-29 isso caiu — o nome passa a
# vir por OCR e TUDO que aparece no quadro e registrado. O que sobrou para ela
# e o papel que o `02-CONTEXT.md` ja previa: promover no console o que o usuario
# quer olhar primeiro, sem esconder o resto.
#
# POR QUE ESTA FUNCAO EXISTE, SE A FERRAMENTA DE CALIBRACAO JA LE A MESMA CHAVE.
# Aquele modulo chama `tornar_consciente_de_dpi()` NO PROPRIO IMPORT e traz
# `cv2` junto, porque e uma ferramenta de bancada com janela de GUI. Importa-lo
# daqui seria pagar DPI, OpenCV e janela por uma leitura de TOML dentro do laco
# de producao do modo `--mercado`. As duas leituras existem porque os dois
# chamadores tem custos de import diferentes, e a duplicacao esta declarada aqui
# em vez de escondida.
#
# A validacao e o espelho de `ler_bosses` e de `_personagem_do_arquivo`, de
# proposito: arquivo ausente nao e erro, secao ausente nao e erro, TOML quebrado
# E erro de arranque, e a mensagem MOSTRA o formato certo em vez de so
# descreve-lo.
# ---------------------------------------------------------------------------

SECAO_DO_MERCADO = "mercado"
CHAVE_DA_WATCHLIST = "watchlist"

# O exemplo que toda recusa desta secao mostra, escrito UMA vez. Uma mensagem
# que diz "precisa ser uma lista" faz o usuario adivinhar a sintaxe do TOML; uma
# que mostra a linha pronta ele copia.
_EXEMPLO_DA_WATCHLIST = (
    "  Exemplo:\n"
    "    [mercado]\n"
    "    watchlist = [\n"
    '      "Dragon Belt",\n'
    '      "+3 Dragon Belt",\n'
    "    ]"
)


def ler_watchlist_do_mercado(caminho: Path | None = None) -> list[str]:
    """Os itens que o usuario quer ver PRIMEIRO no console do mercado.

    ARQUIVO AUSENTE NAO E ERRO, E SECAO AUSENTE TAMBEM NAO. O `[mercado]
    watchlist` do `config.toml` esta COMENTADO e o usuario nunca o preencheu; o
    modo `--mercado` tem de responder "vale quanto agora?" sem ele, ordenando
    pelas series com mais evidencia. Quem chama e que decide o que fazer com a
    lista vazia — ver `mercado_analise.ordenar_para_o_console`.

    ARQUIVO PRESENTE E MAL FORMADO E ERRO DE ARRANQUE, e reusa `AgendaInvalida`
    pela razao ja escrita em `ler_membros`: ela JA e a excecao de "o config.toml
    nao faz sentido", ja e capturada onde o arranque quer capturar, e uma
    terceira classe duplicaria esse tratamento sem ganhar nada.

    AS DUAS RECUSAS SAO OS DOIS ERROS QUE O USUARIO CONSEGUE ESCREVER:

    - `watchlist = "Dragon Belt"` — texto solto em vez de lista. Ele ITERARIA
      OS CARACTERES: o console marcaria `D`, `r`, `a`, `g`... como itens
      vigiados. Silenciosamente absurdo, e o mesmo defeito que a ferramenta de
      calibracao ja recusa do lado dela.
    - um item que nao e texto (`42`, `true`, uma tabela). A mensagem NOMEIA A
      POSICAO, porque "o item 2 da watchlist" o usuario conserta em cinco
      segundos e "um item esta errado" o faz contar linhas.

    ITEM SO DE ESPACO E AUSENCIA, e nao um alvo chamado "   ": ele nao casaria
    serie nenhuma e apareceria como uma marca invisivel no console.

    A LISTA VOLTA NA ORDEM ESCRITA. Quem ordena e o console, e a ordem entre os
    itens marcados sai da evidencia — mas devolver embaralhado aqui esconderia
    de quem depura o que o arquivo realmente diz.
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

    secao = dados.get(SECAO_DO_MERCADO, {})
    if not isinstance(secao, dict):
        raise AgendaInvalida(
            f"{caminho.name}: [{SECAO_DO_MERCADO}] precisa ser uma SECAO, veio "
            f"{type(secao).__name__}.\n{_EXEMPLO_DA_WATCHLIST}"
        )

    brutos = secao.get(CHAVE_DA_WATCHLIST)
    if brutos is None:
        return []

    if not isinstance(brutos, list):
        raise AgendaInvalida(
            f"{caminho.name}: [{SECAO_DO_MERCADO}] {CHAVE_DA_WATCHLIST} precisa "
            f"ser uma LISTA, veio {type(brutos).__name__}. Um texto solto seria "
            f"lido letra por letra.\n{_EXEMPLO_DA_WATCHLIST}"
        )

    itens: list[str] = []
    for posicao, bruto in enumerate(brutos, start=1):
        if not isinstance(bruto, str):
            raise AgendaInvalida(
                f"{caminho.name}: o item {posicao} de [{SECAO_DO_MERCADO}] "
                f"{CHAVE_DA_WATCHLIST} precisa ser TEXTO, veio "
                f"{type(bruto).__name__}.\n{_EXEMPLO_DA_WATCHLIST}"
            )
        if bruto.strip():
            itens.append(bruto)
    return itens


# ---------------------------------------------------------------------------
# AS RECEITAS DO MERCADO — o `[[receita]]` da margem de craft (ANAL-04)
#
# O MOLDE E `ler_bosses` + `_boss_de_dict`, LITERALMENTE, e nao por gosto:
# arquivo ausente nao e erro, secao ausente nao e erro, TOML presente e mal
# formado E erro de ARRANQUE, e cada recusa NOMEIA a receita quando ha nome
# utilizavel e cita a POSICAO do bloco quando nao ha. Duas formas diferentes de
# recusar config no mesmo arquivo obrigariam o usuario a aprender duas.
#
# POR QUE ERRO DE ARRANQUE, E NAO UM AVISO: uma receita torta tem de parar o
# programa enquanto o usuario olha para o console. O contrario — degradar e
# seguir — produziria uma margem plausivel horas depois, enquanto ele esta AFK,
# e nada no mundo o avisaria de que o numero esta errado.
#
# SEM `[[receita]]` NENHUM A MARGEM SIMPLESMENTE NAO APARECE. Nao e erro e nao
# e aviso: e uma secao opcional que o usuario preenche quando quiser (decisao
# travada no `04-CONTEXT.md`). Quem chama e que decide o que fazer com a lista
# vazia — ver `mercado_console.secao_da_margem`.
#
# ESTE BLOCO E APENDICE PURO. O plano 04-04 fixou que a funcao nova vai no FIM
# do modulo sem tocar nada existente, e por isso o unico import de que ele
# precisa mora AQUI e nao no topo: um `git diff` deste arquivo tem de mostrar
# so linhas ACRESCENTADAS. Ha precedente de import fora do topo no pacote
# (`calibrar.py:61-65`, `calibrar_mercado.py:61-100`), pela mesma razao de
# ordem que aqui e de contencao de diff.
# ---------------------------------------------------------------------------

from dataclasses import dataclass  # noqa: E402

SECAO_DA_RECEITA = "receita"

# O exemplo que TODA recusa desta secao mostra, escrito UMA vez. Uma mensagem
# que diz "precisa ser uma lista de tabelas" faz o usuario adivinhar a sintaxe
# do TOML; uma que mostra o bloco pronto ele copia.
#
# A FORMA E A DE TABELA INLINE, e a escolha tem razao. A alternativa
# (`[[receita.componente]]` em sub-blocos) tambem parseia no `tomllib` — as
# duas foram testadas. Mas COMENTADA ela vira quatro pedacos soltos que o
# usuario descomenta pela metade sem perceber, e o `config.toml` deste projeto
# distribui todas as secoes opcionais comentadas. A inline e um bloco contiguo
# que se comenta e se descomenta como uma UNIDADE, igual ao `watchlist = [...]`
# que ja mora la.
_EXEMPLO_DA_RECEITA = (
    "  Exemplo:\n"
    "    [[receita]]\n"
    '    produto = "Dragon Belt"\n'
    "    rende = 1\n"
    "    componentes = [\n"
    '      { item = "Common Aztac", quantidade = 5 },\n'
    '      { item = "Leonard", quantidade = 20 },\n'
    "    ]"
)


class ReceitaInvalida(Exception):
    """Um bloco `[[receita]]` do config.toml nao serve, e o arranque para.

    CLASSE PROPRIA, e nao `AgendaInvalida` reusada como em `ler_membros` e em
    `ler_watchlist_do_mercado`. A razao e o destino do `except`: aquelas duas
    sao lidas pelo laco do mercado, que as CAPTURA de proposito para nao matar
    a coleta da noite por causa de uma virgula na watchlist — a watchlist e
    filtro de destaque, e nao o produto. A receita e outra coisa: ela e uma
    CONTA, e uma conta escrita errado nao pode degradar para "sem margem" em
    silencio. Uma classe separada e o que permite o chamador tratar os dois
    casos diferente sem inspecionar texto de mensagem.
    """


@dataclass(frozen=True)
class ComponenteDaReceita:
    """Um ingrediente e quanto dele a receita pede.

    `item` e o nome COMO O USUARIO O LE NA TELA, e a resolucao dele para uma
    `chave_da_serie` do CSV acontece na analise, nunca aqui: este modulo le
    TOML e nao sabe o que e uma serie. A resolucao quebra de proposito quando o
    nome nao casa ou casa duas vezes — ver `mercado_analise.margem_de_craft`.
    """

    item: str
    quantidade: int


@dataclass(frozen=True)
class Receita:
    """Um `[[receita]]` validado: o produto, quanto ele rende e o que ele come.

    `FROZEN` porque ninguem reescreve uma receita depois de le-la: o
    `config.toml` e a verdade, e este objeto e uma leitura dele.

    `componentes` E UMA TUPLA e nao uma lista, pelo mesmo motivo: uma lista
    dentro de um `frozen` seria imutabilidade de fachada.
    """

    produto: str
    rende: int
    componentes: tuple[ComponenteDaReceita, ...]


def ler_receitas(caminho: Path | None = None) -> list[Receita]:
    """Le os blocos [[receita]] do config.toml. ANAL-04.

    ARQUIVO AUSENTE NAO E ERRO, E SECAO AUSENTE TAMBEM NAO. A secao
    `[[receita]]` nasce COMENTADA no `config.toml`: o modo `--mercado` roda a
    noite inteira sem receita nenhuma e continua respondendo "vale quanto
    agora?". Sem `[[receita]]` a margem simplesmente NAO APARECE.

    ARQUIVO PRESENTE E MAL FORMADO E ERRO DE ARRANQUE — ver o comentario da
    secao acima.

    A LISTA VOLTA NA ORDEM ESCRITA. Devolver embaralhado esconderia de quem
    depura o que o arquivo realmente diz.
    """
    caminho = caminho or ARQUIVO_CONFIG
    if not caminho.exists():
        return []

    try:
        with caminho.open("rb") as arquivo:
            dados = tomllib.load(arquivo)
    except tomllib.TOMLDecodeError as erro:
        raise ReceitaInvalida(
            f"{caminho.name} nao e um TOML valido: {erro}"
        ) from erro

    brutos = dados.get(SECAO_DA_RECEITA)
    if brutos is None:
        return []

    # `receita = "Dragon Belt"` ITERARIA OS CARACTERES e produziria uma receita
    # por letra. E o mesmo defeito que `ler_watchlist_do_mercado` ja recusa do
    # lado dela, e ele e silenciosamente absurdo em vez de ruidosamente errado.
    if not isinstance(brutos, list):
        raise ReceitaInvalida(
            f"{caminho.name}: [[{SECAO_DA_RECEITA}]] precisa ser um ou mais "
            f"BLOCOS de receita, e nao {type(brutos).__name__}. Um texto solto "
            f"seria lido letra por letra.\n{_EXEMPLO_DA_RECEITA}"
        )

    return [
        _receita_de_dict(bruto, indice) for indice, bruto in enumerate(brutos)
    ]


def _receita_de_dict(bruto: object, indice: int) -> Receita:
    """Valida um bloco [[receita]] e diz exatamente o que esta errado.

    MESMO PADRAO DE `onde` DO `_boss_de_dict`: cita o NOME sempre que ele
    existe, porque "o segundo [[receita]] esta errado" faz o usuario contar
    blocos e "a receita 'Dragon Belt' tem um componente sem 'item'" ele
    conserta em cinco segundos.

    `rende` E OBRIGATORIO, E NAO OPCIONAL COM PADRAO 1. E ESCOLHA, e a
    alternativa trocaria uma linha de verbosidade por risco de numero errado:
    quem crafta cinco de cada vez e esquece o campo receberia uma margem cinco
    vezes menor que a real, perfeitamente formatada, sem uma linha de erro em
    lugar nenhum. E o mesmo argumento que tornou `respawn_horas_*`
    obrigatorios em vez de opcionais.

    `componentes` VAZIO OU AUSENTE TAMBEM E RECUSA, pela mesma familia de
    razao: uma receita sem ingrediente nenhum produziria uma "margem" igual ao
    proprio preco do produto — um numero grande, plausivel e sem significado.
    """
    if not isinstance(bruto, dict):
        raise ReceitaInvalida(
            f"[[{SECAO_DA_RECEITA}]] #{indice + 1}: precisa ser um bloco "
            f"[[{SECAO_DA_RECEITA}]] com produto, rende e componentes, e nao "
            f"{type(bruto).__name__}.\n{_EXEMPLO_DA_RECEITA}"
        )

    produto_bruto = bruto.get("produto")
    produto = (
        str(produto_bruto).strip() if isinstance(produto_bruto, str) else ""
    )
    onde = (
        f"receita '{produto}'"
        if produto
        else f"[[{SECAO_DA_RECEITA}]] #{indice + 1}"
    )

    if not produto:
        raise ReceitaInvalida(
            f"{onde}: falta o campo 'produto'. Escreva o nome do item craftado "
            f"como ele aparece na tela, com o prefixo de encanto quando "
            f"houver.\n{_EXEMPLO_DA_RECEITA}"
        )

    rende = _inteiro_positivo_da_receita(bruto, "rende", onde)

    brutos = bruto.get("componentes")
    if brutos is None:
        raise ReceitaInvalida(
            f"{onde}: falta o campo 'componentes'. Sem ingrediente nenhum nao "
            f"ha margem a calcular.\n{_EXEMPLO_DA_RECEITA}"
        )
    if not isinstance(brutos, list):
        raise ReceitaInvalida(
            f"{onde}: 'componentes' precisa ser uma LISTA de tabelas, veio "
            f"{type(brutos).__name__}.\n{_EXEMPLO_DA_RECEITA}"
        )
    if not brutos:
        raise ReceitaInvalida(
            f"{onde}: 'componentes' esta vazio. Uma receita sem ingrediente "
            f"produziria uma margem igual ao proprio preco do produto - um "
            f"numero grande e sem significado.\n{_EXEMPLO_DA_RECEITA}"
        )

    componentes = tuple(
        _componente_de_dict(componente, posicao, onde)
        for posicao, componente in enumerate(brutos, start=1)
    )
    return Receita(produto=produto, rende=rende, componentes=componentes)


def _componente_de_dict(
    bruto: object, posicao: int, onde: str
) -> ComponenteDaReceita:
    """Um ingrediente valido, ou a recusa que NOMEIA a receita e a posicao."""
    if not isinstance(bruto, dict):
        raise ReceitaInvalida(
            f"{onde}: o componente {posicao} precisa ser uma tabela com 'item' "
            f"e 'quantidade', e nao {type(bruto).__name__}.\n"
            f"{_EXEMPLO_DA_RECEITA}"
        )

    item_bruto = bruto.get("item")
    item = str(item_bruto).strip() if isinstance(item_bruto, str) else ""
    if not item:
        raise ReceitaInvalida(
            f"{onde}: o componente {posicao} nao tem 'item'. Escreva o nome do "
            f"ingrediente como ele aparece na tela.\n{_EXEMPLO_DA_RECEITA}"
        )

    quantidade = _inteiro_positivo_da_receita(
        bruto, "quantidade", f"{onde}, componente '{item}'"
    )
    return ComponenteDaReceita(item=item, quantidade=quantidade)


def _inteiro_positivo_da_receita(bruto: dict, campo: str, onde: str) -> int:
    """Uma contagem valida, ou a recusa que nomeia o campo. Nunca booleana.

    BOOLEANO RECUSADO EXPLICITAMENTE, E ANTES DO TESTE NUMERICO, porque
    `isinstance(True, int)` e verdadeiro em Python. Sem esta ordem,
    `quantidade = true` passaria como "1 unidade" e `rende = true` como "rende
    1": uma margem errada entregue com a mesma cara de uma certa, sem um unico
    erro no console. E o mesmo buraco que o comentario medido de
    `_horas_de_respawn` ja documenta neste mesmo arquivo - este e o segundo
    lugar do projeto onde ele apareceria, e a guarda e copiada de la de
    proposito.

    FRACIONARIO TAMBEM RECUSADO: `rende = 1.5` nao descreve craft nenhum, e
    aceita-lo faria a margem depender de um arredondamento que ninguem
    escolheu. `1.0` cai junto, e de proposito: aceitar o float redondo e
    recusar o quebrado seria uma regra que o usuario descobre por tentativa.
    """
    valor = bruto.get(campo)
    if valor is None:
        raise ReceitaInvalida(
            f"{onde}: falta o campo '{campo}'. Ele e um numero INTEIRO maior "
            f"que zero.\n{_EXEMPLO_DA_RECEITA}"
        )

    if isinstance(valor, bool):
        raise ReceitaInvalida(
            f"{onde}: '{campo}' precisa ser um numero inteiro maior que zero, "
            f"e nao true/false. Exemplo: {campo} = 5"
        )
    if not isinstance(valor, int):
        raise ReceitaInvalida(
            f"{onde}: '{campo}' precisa ser um numero INTEIRO maior que zero "
            f"(recebi {valor!r}). Exemplo: {campo} = 5"
        )
    if valor <= 0:
        raise ReceitaInvalida(
            f"{onde}: '{campo}' precisa ser MAIOR que zero (recebi {valor})."
        )
    return valor
