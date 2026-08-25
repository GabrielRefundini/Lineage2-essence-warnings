"""Comandos vindos do WhatsApp: o scanner passa a OUVIR, nao so a falar.

Ate aqui o caminho era de mao unica. Isto abre a volta — e abrir a volta e
abrir uma superficie de ataque, entao o desenho comeca pela seguranca e nao
pela funcionalidade.

TRES TRAVAS, E NENHUMA E OPCIONAL:

1. **Allowlist de conversa.** So conversas explicitamente configuradas em
   `CHATWOOT_CONVERSAS_COMANDO` sao lidas. Medido no Chatwoot do usuario: a
   conta tem 22 conversas, 11 com mensagens de entrada, e sao CLIENTES REAIS —
   uma delas, do Joao Pedro, diz literalmente "Quero cancelar". Um leitor que
   varresse a conta inteira obedeceria a ele.

2. **Prefixo estrito.** Comandos comecam com ponto (`.cancelar`), a mesma
   convencao que o grupo do usuario ja usa (`.offline`). Sem o prefixo,
   qualquer conversa sobre "cancelar o silencio" viraria uma acao.

3. **So `incoming`.** `message_type == 0`. O scanner nunca pode obedecer as
   proprias mensagens — um comando ecoado viraria laco infinito.

E UMA QUARTA, contra repeticao: cada mensagem so e obedecida uma vez, por id.
O registro e o mesmo `.agenda/`, entao vale entre reinicios e entre as duas
instancias do usuario.

NOTA DE CAMPO (2026-08-24): o grupo do usuario NAO entrega mensagens de entrada
ao Chatwoot — a ponte Baileys vem com ingestao de grupo desligada. Conversas
1-a-1 entregam normalmente. Por isso a conversa de comandos e configuravel
separada da de avisos: da para receber comando no privado e responder no grupo.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum

from .loot import NICK_VALIDO, apelido, interpretar_pegou

# Todo comando comeca com isto. Mesma convencao do `.offline` que o grupo ja
# usa, entao nao e vocabulario novo para ninguem.
PREFIXO = "."

# Chatwoot usa INT em message_type. 0 = incoming (pessoa), 1 = outgoing (bot).
# Descoberto lendo a API de verdade — a documentacao fala em strings.
MESSAGE_TYPE_INCOMING = 0

# Quantos digitos FINAIS do telefone comparar.
#
# Nao e preguica — e o unico jeito que funciona no Brasil. Celulares ganharam um
# NONO DIGITO e a base do WhatsApp carrega as duas formas da mesma pessoa.
# Medido nesta conta: o usuario se identifica como +5544997077000 e o Chatwoot
# registra o dono do grupo dele como 554497077000, sem o 9.
#
#   +5544997077000 -> 97077000
#    554497077000  -> 97077000
#
# Comparacao exata falharia em SILENCIO: o comando seria ignorado sem erro
# nenhum, que e o pior modo de falha possivel para uma trava de seguranca.
#
# O preco: dois numeros diferentes com os mesmos 8 digitos finais colidem. Numa
# allowlist de duas a cinco pessoas isso e aceitavel, e esta documentado.
DIGITOS_FINAIS_DO_TELEFONE = 8


class Comando(Enum):
    """O que o scanner aceita obedecer. Fechado de proposito.

    Cada item aqui e uma coisa que qualquer pessoa do grupo pode mandar o
    scanner fazer. A lista curta nao e falta de imaginacao — e o limite do
    estrago possivel.
    """

    CANCELAR_SILENCIO = "cancelar_silencio"
    STATUS = "status"

    # Entrar e sair do modo solo sem reiniciar. E o comando que mais faz
    # sentido vir do WhatsApp: a hora de virar solo e quando a party se
    # desfaz, e nesse momento o usuario esta no jogo, nao no console.
    SOLO = "solo"
    PARTY = "party"

    # O controle de loot do Solo Boss. Sao os dois primeiros comandos com
    # ARGUMENTO (o nick), e por isso nao moram no _VOCABULARIO — quem os
    # reconhece e `interpretar_dinamico`.
    LOOT_DESIGNAR = "loot_designar"
    LOOT_CONSULTA = "loot_consulta"

    # O UNICO comando DESTRUTIVO da superficie dinamica: ele APAGA estado
    # duravel em vez de escrever por cima. Por isso a sintaxe dele e
    # explicita (hifen ou palavra reservada) e `.loot` sozinho nao serve —
    # ver D-02 em `interpretar_dinamico`.
    LOOT_CANCELAR = "loot_cancelar"

    # O PRIMEIRO comando que reescreve HISTORICO. Os outros tres mexem na VEZ
    # do proximo boss — estado que expira sozinho quando o horario passa. Este
    # mexe na estatistica, que nunca e podada e nao tem backup. E por isso que
    # o alcance dele para no registro MAIS RECENTE: o limite do estrago
    # possivel nao pode depender de quem digita lembrar de ter cuidado.
    LOOT_CORRIGIR = "loot_corrigir"

    # O SEGUNDO comando que reescreve historico, e o limite dele e de outra
    # natureza. O `.corrigir` e contido por NAO TER SINTAXE que alcance o
    # passado: nao ha como digitar um horario, entao nao ha como errar de
    # boss por meses. O `.pegou` tem exatamente essa sintaxe — e o motivo dele
    # existir, porque o `.corrigir` nao alcanca "nao ha registro nenhum" —, e
    # paga por ela com duas protecoes proprias: o horario tem que ENCAIXAR
    # numa ocorrencia real do Solo Boss (nunca nasce registro orfao) e a
    # resposta sempre diz o DIA de volta, para quem digitou conferir na hora
    # que acertou o boss. Os dois limites sao reais e sao diferentes; e por
    # isso que os dois comandos coexistem em vez de um substituir o outro.
    LOOT_ATRIBUIR = "loot_atribuir"


# As formas escritas que valem para cada comando. Varias por comando porque
# ninguem lembra a sintaxe exata no meio de um farm.
_VOCABULARIO: dict[str, Comando] = {
    "cancelar": Comando.CANCELAR_SILENCIO,
    "cancelarsilencio": Comando.CANCELAR_SILENCIO,
    "silencio": Comando.CANCELAR_SILENCIO,
    "voltar": Comando.CANCELAR_SILENCIO,
    "status": Comando.STATUS,
    "scanner": Comando.STATUS,
    "solo": Comando.SOLO,
    "soloplay": Comando.SOLO,
    "party": Comando.PARTY,
    "pt": Comando.PARTY,
    "grupo": Comando.PARTY,
}


@dataclass(frozen=True)
class MensagemDeComando:
    """Uma mensagem que pede alguma coisa ao scanner."""

    id: int
    comando: Comando
    autor: str | None
    texto: str

    # De qual conversa o pedido veio. E o que permite RESPONDER onde
    # perguntaram, em vez de responder sempre no grupo de avisos.
    conversa: str | None = None

    # O argumento dos comandos dinamicos, SEMPRE COMO FOI DIGITADO: o nick,
    # na maioria deles, e o argumento inteiro do `.pegou` ("18:00 Korzis"),
    # ainda cru. A resposta mostra o que a pessoa escreveu; normalizar — e,
    # no caso do `.pegou`, reler a gramatica — e trabalho de quem consome.
    argumento: str | None = None


def so_digitos(telefone: str | None) -> str:
    """Descarta tudo que nao e digito: +, espaco, parentese, traco."""
    return "".join(c for c in str(telefone or "") if c.isdigit())


def telefone_equivalente(a: str | None, b: str | None) -> bool:
    """Os dois textos sao o mesmo telefone?

    Compara pelos digitos FINAIS, para atravessar codigo de pais, DDD,
    formatacao e o nono digito brasileiro. Ver DIGITOS_FINAIS_DO_TELEFONE.
    """
    da, db = so_digitos(a), so_digitos(b)
    if not da or not db:
        return False
    corte = DIGITOS_FINAIS_DO_TELEFONE
    if len(da) < corte or len(db) < corte:
        # Numero curto demais para o sufixo valer: exige igualdade completa,
        # em vez de comparar um pedaco pequeno e casar com meio mundo.
        return da == db
    return da[-corte:] == db[-corte:]


def autor_autorizado(remetente: dict, telefones: list[str]) -> bool:
    """Quem mandou pode mandar?

    Lista VAZIA aceita qualquer um — e a compatibilidade com quem ja tinha
    configurado comandos so por conversa. O aviso de arranque cuida de deixar
    isso visivel, porque "qualquer um pode mandar no scanner" nao pode ser um
    estado que se descobre por acidente.
    """
    if not telefones:
        return True
    numero = remetente.get("phone_number")
    return any(telefone_equivalente(numero, permitido) for permitido in telefones)


def interpretar(texto: str | None) -> Comando | None:
    """Que comando este texto pede? None quando nao pede nenhum.

    Exige o prefixo. "vamos cancelar o silencio?" nao e comando; ".cancelar" e.
    A diferenca entre conversar sobre uma acao e pedir a acao tem que ser
    visivel no texto, senao o scanner age no meio de uma conversa.
    """
    if not texto:
        return None

    primeira = texto.strip().split()
    if not primeira:
        return None

    palavra = primeira[0]
    if not palavra.startswith(PREFIXO):
        return None

    # `.cancelar` e `.cancelar silencio` sao o mesmo pedido — juntamos as duas
    # primeiras palavras para aceitar as duas formas sem gramatica nenhuma.
    miolo = palavra[len(PREFIXO) :].lower()
    if len(primeira) > 1:
        junto = (miolo + primeira[1].lower()).replace("-", "").replace("_", "")
        if junto in _VOCABULARIO:
            return _VOCABULARIO[junto]

    return _VOCABULARIO.get(miolo.replace("-", "").replace("_", ""))


# O nome privado sobrevive porque os seis usos deste arquivo ja falam essa
# lingua. A DEFINICAO (e o comentario que explica o charset do L2 e o minimo
# de 2 caracteres) mudou para o `loot.py`, porque `interpretar_pegou` precisa
# dela e o `loot` nao pode importar `comandos` sem fechar um ciclo.
_NICK_VALIDO = NICK_VALIDO

# `.offline` e convencao humana do grupo — quem digita esta avisando GENTE,
# nao o bot. Excluido por nome para jamais virar consulta de nick, nem que
# um dia exista um personagem chamado Offline.
_PALAVRA_HUMANA = "offline"

# As palavras que, no lugar do nick, querem dizer "ninguem" — o `.loot-`
# escrito por extenso, para quem nao lembra que o hifen sozinho basta.
#
# O PRECO, ACEITO E DOCUMENTADO: um personagem chamado "Cancelar" (ou
# "Ninguem", "Nenhum", "Limpar") nao pode ser designado por `.loot-<nick>`.
# E barato perto da alternativa — `.loot-cancelar` DESIGNANDO um personagem
# inexistente chamado "Cancelar" e deixando a party sem jeito de desmarcar.
_PALAVRAS_DE_CANCELAMENTO = frozenset({"cancelar", "ninguem", "nenhum", "limpar"})


def interpretar_dinamico(
    texto: str | None, nicks_conhecidos: frozenset[str]
) -> tuple[Comando, str] | None:
    """Os comandos com argumento: `.loot-<nick>` e `.<nick>`.

    Olha a PRIMEIRA PALAVRA CRUA, com hifens — de proposito. `interpretar`
    remove hifens do miolo, e e por isso que `.loot-j4guar` passa ileso por
    ele; reaproveitar aquele miolo aqui perderia a fronteira entre o comando
    e o nick.

    Superficie dinamica CONTIDA: nick restrito a [A-Za-z0-9]{2,16}, consulta
    so de nick conhecido, vocabulario fixo com precedencia (garantida pelo
    chamador, que tenta `interpretar` primeiro) e `.offline` excluido por
    nome. Um `.palavra` arbitrario continua morrendo em silencio.
    """
    if not texto:
        return None

    palavras = texto.strip().split()
    if not palavras:
        return None

    primeira = palavras[0]
    if not primeira.startswith(PREFIXO):
        return None
    crua = primeira[len(PREFIXO) :]

    # `.loot-<nick>` e `.loot <nick>`: o comando e case-insensitive, o nick
    # e preservado como digitado.
    if crua.lower().startswith("loot-"):
        nick = crua[len("loot-") :]
        # A ORDEM E A COISA MAIS IMPORTANTE DESTE RAMO: o cancelamento vem
        # ANTES do `_NICK_VALIDO`, porque "cancelar" casa o charset de nick
        # e viraria uma designacao para um personagem que nao existe.
        if not nick or nick.lower() in _PALAVRAS_DE_CANCELAMENTO:
            return (Comando.LOOT_CANCELAR, "")
        if _NICK_VALIDO.fullmatch(nick):
            return (Comando.LOOT_DESIGNAR, nick)
        return None
    if crua.lower() == "loot":
        # Mesma ordem do ramo com hifen, pela mesma razao: sem isto,
        # `.loot cancelar` DESIGNARIA um personagem chamado "cancelar".
        if len(palavras) > 1 and palavras[1].lower() in _PALAVRAS_DE_CANCELAMENTO:
            return (Comando.LOOT_CANCELAR, "")
        if len(palavras) > 1 and _NICK_VALIDO.fullmatch(palavras[1]):
            return (Comando.LOOT_DESIGNAR, palavras[1])
        # D-02, E ISTO NAO E ESQUECIMENTO: `.loot` SOZINHO nao faz nada.
        # Comando sem argumento nao pode ser destrutivo — quem digita `.loot`
        # no meio de um farm quase sempre esta PERGUNTANDO de quem e a vez,
        # nao mandando apagar. Um dia alguem vai querer "consertar" esta
        # linha fazendo-a cancelar; nao consertem.
        return None

    # `.corrigir-<nick>`: troca o dono do ultimo loot ja consumado. Sem
    # palavras reservadas aqui — `.corrigir` nao tem forma destrutiva sem
    # argumento, entao nao existe a colisao que obrigou o
    # `_PALAVRAS_DE_CANCELAMENTO` a nascer.
    if crua.lower().startswith("corrigir-"):
        nick = crua[len("corrigir-") :]
        if _NICK_VALIDO.fullmatch(nick):
            return (Comando.LOOT_CORRIGIR, nick)
        return None
    if crua.lower() == "corrigir":
        if len(palavras) > 1 and _NICK_VALIDO.fullmatch(palavras[1]):
            return (Comando.LOOT_CORRIGIR, palavras[1])
        # O `return None` NAO e redundancia: sem ele o fluxo cai no ramo de
        # consulta logo abaixo, onde `_NICK_VALIDO` casa a palavra "corrigir"
        # e um nick homonimo transformaria o comando numa consulta.
        #
        # E este ramo inteiro existe porque tratar SO o hifen foi exatamente o
        # erro que fez `.loot cancelar` DESIGNAR um personagem chamado
        # "cancelar" na tarefa anterior. A forma de duas palavras nunca e
        # opcional num comando que mexe em estado duravel.
        return None

    # `.pegou-18:00 Korzis` faz o mesmo que `.pegou 18:00 Korzis`. As duas
    # formas existem porque a mao do usuario ja aprendeu `.loot-` e
    # `.corrigir-`, e porque tratar so uma delas foi exatamente o erro que fez
    # `.loot cancelar` DESIGNAR um personagem chamado "cancelar": a forma de
    # duas palavras nunca e opcional num comando que mexe em estado duravel.
    if crua.lower().startswith("pegou-"):
        argumento = " ".join([crua[len("pegou-") :], *palavras[1:]]).strip()
        if interpretar_pegou(argumento) is not None:
            return (Comando.LOOT_ATRIBUIR, argumento)
        return None

    # `.pegou <hora> <nick>`: registra o loot de um boss que JA PASSOU. Quem
    # decide se a gramatica esta certa e `interpretar_pegou`, la no `loot.py`
    # — uma gramatica so, que valida aqui e le no responder. Duas divergiriam
    # no primeiro ajuste e o comando passaria a aceitar o que nao executa.
    if crua.lower() == "pegou":
        argumento = " ".join(palavras[1:])
        if interpretar_pegou(argumento) is not None:
            return (Comando.LOOT_ATRIBUIR, argumento)
        # O `return None` NAO e redundancia, pela mesma razao do `.corrigir`
        # logo acima: sem ele o fluxo cai no ramo de consulta, onde
        # `_NICK_VALIDO` casa a palavra "pegou" e um personagem homonimo
        # transformaria o comando numa consulta dele.
        return None

    # `.{nick}` sozinho: o portao por nick conhecido e decisao do usuario —
    # sem ele o scanner responderia a qualquer `.palavra` do grupo.
    if len(palavras) == 1 and _NICK_VALIDO.fullmatch(crua):
        baixo = crua.lower()
        if baixo in _VOCABULARIO or baixo == _PALAVRA_HUMANA:
            return None
        if apelido(crua) in nicks_conhecidos:
            return (Comando.LOOT_CONSULTA, crua)
    return None


def comandos_novos(
    mensagens: list[dict],
    ja_obedecidos: set[str],
    telefones: list[str] | None = None,
    nicks_conhecidos: frozenset[str] = frozenset(),
) -> list[MensagemDeComando]:
    """Filtra o que veio da API e devolve so o que deve ser obedecido.

    Funcao pura — recebe a resposta ja decodificada. E o que permite testar
    todas as travas sem rede e sem um Chatwoot de verdade.
    """
    achados: list[MensagemDeComando] = []
    for bruta in mensagens:
        # TRAVA 3: nunca obedecer as proprias mensagens.
        if bruta.get("message_type") != MESSAGE_TYPE_INCOMING:
            continue
        # Nota privada de agente nao e pedido de ninguem do grupo.
        if bruta.get("private"):
            continue

        identificador = bruta.get("id")
        if identificador is None:
            continue
        if chave_da_mensagem(identificador) in ja_obedecidos:
            continue

        # O vocabulario FIXO vem primeiro — precedencia explicita, para um
        # nick homonimo de comando jamais sombrear o comando.
        argumento = None
        comando = interpretar(bruta.get("content"))
        if comando is None:
            dinamico = interpretar_dinamico(bruta.get("content"), nicks_conhecidos)
            if dinamico is None:
                continue
            comando, argumento = dinamico

        # TRAVA 5: quem mandou pode mandar? Vale ate dentro de um grupo, onde a
        # allowlist de conversa sozinha liberaria todo mundo.
        remetente = bruta.get("sender") or {}
        if not autor_autorizado(remetente, telefones or []):
            continue
        achados.append(
            MensagemDeComando(
                id=int(identificador),
                comando=comando,
                autor=remetente.get("name"),
                texto=str(bruta.get("content", "")),
                conversa=bruta.get("conversation_id"),
                argumento=argumento,
            )
        )

    achados.sort(key=lambda m: m.id)
    return achados


def chave_da_mensagem(identificador: int | str) -> str:
    """Chave duravel de 'ja obedeci esta mensagem'.

    Prefixo proprio para nao se confundir com os marcadores de aviso e de
    cancelamento, que dividem o mesmo diretorio.
    """
    return f"comando_{identificador}"


class LeitorDeComandos:
    """Puxa mensagens novas do Chatwoot, com cadencia.

    Cadencia porque isto e rede: a 1 Hz seriam 86 mil requisicoes por dia por
    instancia, para um comando que o usuario manda uma vez por semana. A
    latencia de alguns segundos e irrelevante para "cancele o silencio".
    """

    def __init__(
        self,
        url: str,
        conta: str,
        token: str,
        conversas: list[str],
        segundos_entre_leituras: float = 20.0,
        user_agent: str = "",
        telefones: list[str] | None = None,
        etiqueta: str = "",
    ) -> None:
        self._url = url.rstrip("/")
        self._conta = conta
        self._token = token
        self._conversas = list(conversas)
        self._intervalo = segundos_entre_leituras
        self._user_agent = user_agent
        self.telefones = list(telefones or [])
        # Etiqueta que transforma uma conversa em canal de comando. Redescoberta
        # a cada leitura de proposito: e o que faz marcar/desmarcar no painel do
        # Chatwoot valer NA HORA, sem editar arquivo e sem reiniciar o scanner.
        self._etiqueta = etiqueta.strip().lower()
        self._ultima_leitura: float | None = None
        self.falhas = 0

    @property
    def ativo(self) -> bool:
        """Ha de onde ouvir? Por id fixo, ou por etiqueta."""
        return bool(self._conversas or self._etiqueta)

    @property
    def aberto_a_qualquer_um(self) -> bool:
        """Esta ouvindo sem restringir quem pode mandar?

        Nao e erro — e compatibilidade. Mas precisa aparecer no arranque: um
        scanner que obedece qualquer um nao pode ser um estado que se descobre
        por acidente.
        """
        return self.ativo and not self.telefones

    def vencido(self, agora: float) -> bool:
        return (
            self._ultima_leitura is None
            or agora - self._ultima_leitura >= self._intervalo
        )

    def ler(self, agora: float) -> list[dict]:
        """Mensagens cruas das conversas de comando. Vazio se nao venceu.

        NUNCA levanta. Uma falha de rede no caminho de ENTRADA nao pode
        derrubar o scanner — o trabalho dele e vigiar a party, e ouvir comando
        e um extra. As falhas sao contadas para o resumo de sessao.
        """
        # `ativo`, e nao `_conversas`: uma configuracao so por ETIQUETA nao tem
        # conversa fixa nenhuma, e olhar a lista errada aqui fazia o leitor
        # nunca ler nada — silenciosamente.
        if not self.ativo or not self.vencido(agora):
            return []
        self._ultima_leitura = agora

        alvos = list(self._conversas)
        if self._etiqueta:
            alvos.extend(c for c in self._por_etiqueta() if c not in alvos)

        tudo: list[dict] = []
        for conversa in alvos:
            try:
                # Carimba a origem: a resposta tem de sair onde a pergunta
                # chegou. A API devolve a mensagem sem dizer de qual conversa
                # ela veio quando pedimos conversa a conversa.
                for bruta in self._puxar(conversa):
                    bruta["conversation_id"] = str(conversa)
                    tudo.append(bruta)
            except Exception:  # noqa: BLE001 — ver docstring
                self.falhas += 1
        return tudo

    def _por_etiqueta(self) -> list[str]:
        """Conversas marcadas com a etiqueta configurada.

        Falha em silencio devolvendo vazio: se a listagem cair, o certo e ouvir
        MENOS, nunca mais. Uma falha de rede nao pode abrir canal nenhum.
        """
        try:
            dados = self._get("/conversations")
        except Exception:  # noqa: BLE001 — ver docstring
            self.falhas += 1
            return []

        bruto = dados.get("data", dados) if isinstance(dados, dict) else dados
        conversas = (
            bruto.get("payload", bruto) if isinstance(bruto, dict) else bruto or []
        )
        marcadas = []
        for conversa in conversas:
            etiquetas = conversa.get("labels") or []
            if any(str(e).strip().lower() == self._etiqueta for e in etiquetas):
                marcadas.append(str(conversa.get("id")))
        return marcadas

    def _get(self, caminho: str):
        alvo = f"{self._url}/api/v1/accounts/{self._conta}{caminho}"
        req = urllib.request.Request(alvo, method="GET")
        req.add_header("api_access_token", self._token)
        req.add_header("Accept", "application/json")
        if self._user_agent:
            req.add_header("User-Agent", self._user_agent)
        with urllib.request.urlopen(req, timeout=10) as resposta:
            return json.loads(resposta.read())

    def _puxar(self, conversa: str) -> list[dict]:
        dados = self._get(f"/conversations/{conversa}/messages")
        return dados.get("payload", []) if isinstance(dados, dict) else []
