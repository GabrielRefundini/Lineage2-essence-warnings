"""A janela de respawn: o scanner deixa de so RELATAR e passa a PREVER.

Ate aqui o projeto tinha duas fontes de fato — a tela (`rastreador`, `bosses`)
e o relogio (`agenda`). Esta camada tem uma terceira, e ela e a mais estranha
das tres: **o disco**. Um nascimento visto as 14:30 vira um arquivo vazio em
`.agenda/`, e seis horas depois esse arquivo — e nao uma variavel, e nao uma
sessao — e o que produz a mensagem no grupo.

POR QUE O DISCO E NAO A MEMORIA. O ciclo de respawn dura de 6 a 8 horas e o
usuario reinicia o scanner varias vezes por sessao (troca de personagem, queda
do cliente, ajuste de calibracao). Um instante guardado em memoria morre no
primeiro reinicio, e o modo de falha nao e um erro: e o silencio. A party
simplesmente nunca receberia o aviso, e ninguem teria como saber que ele foi
perdido. Gravado em disco, derrubar e subir o processo faz a contagem partir do
MESMO instante, porque o instante nunca esteve em memoria de processo nenhum.

MESMA DISCIPLINA DO RESTO DO PACOTE: **nao ha relogio proprio.** O tempo entra
por parametro, e aqui a regra tem um dente a mais do que em `agenda.py` — o
instante da ancora foi LIDO DE DISCO horas antes, entao uma divergencia entre o
relogio do calculo e o relogio da ancora produz uma previsao errada com cara de
certa. O portao de AST em `tests/test_presenca.py::TestSemRelogioProprio`
guarda isto por estrutura, e nao por politica.

O NOME DO MODULO. `janela.py` foi recusado: `--janela`, `JanelaDeSilencio` e
`janela_de_selecao.py` ja usam a palavra para a JANELA DO WINDOWS, e um
terceiro sentido no mesmo pacote seria ambiguidade permanente. `respawn` e a
palavra que o proprio `config.toml` do usuario ja usa (`respawn_horas_min`).

A PALAVRA `EPISODIO`, e por que ela e uma palavra nova. Um EPISODIO e um
nascimento e TODAS as deteccoes dele — as do chat, as do alvo, as das duas
instancias do usuario, espalhadas por minutos. O campo mediu isso em
2026-08-30: tres deteccoes de chat as 21:59 e tres de alvo entre 22:01 e 22:02,
para um unico Tiat South, seis mensagens no grupo. A nocao precisava de nome
proprio e nao pode reusar nenhum dos que ja existem aqui: `janela` ja significa
a JANELA DO WINDOWS e a JANELA DE RESPAWN, e `ciclo` ja significa o par
abre/limite. Um quarto sentido para uma palavra existente seria ambiguidade
permanente — a mesma razao escrita acima para este modulo nao se chamar
`janela.py`.

A DIRECAO DE IMPORTACAO E `respawn -> {agenda, bosses}`, e nenhum dos dois
importa `respawn`. Um ciclo aqui nao degradaria nada: mataria os tres modulos
com `ImportError` no arranque.

A CONTA E ANCORADA NO NASCIMENTO, E NAO NA MORTE — e essa e a fonte de todo o
cuidado com a redacao das mensagens. A regra do servidor conta a partir da
MORTE do boss, mas o unico instante que o scanner consegue observar e o
NASCIMENTO. Entre os dois ha `k`, o tempo que o boss ficou vivo, que o scanner
nao tem como medir. A consequencia e que os dois avisos saem `k` CEDO, nunca
tarde: no instante do limite otimista a janela real pode nem ter aberto. Por
isso nenhuma mensagem daqui pode afirmar que a janela fechou ou que a party
perdeu o boss (D-19) — a afirmacao seria falsa na direcao que custa caro, e
mandaria a party desistir de um boss que ainda vai nascer.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .agenda import TOLERANCIA_MINUTOS, apelido_do_evento
from .bosses import Boss, OrigemDoAviso


class TipoDeJanela(Enum):
    """Os dois avisos de um ciclo (D-17). Nao ha lembrete de antecedencia.

    O `.value` de cada membro vira SUFIXO DE NOME DE ARQUIVO DURAVEL em
    `.agenda/`, e por isso e escolhido uma unica vez.
    """

    ABRE = "abre"

    # O MEMBRO DO LIMITE NAO SE CHAMA COM UM VERBO DE ENCERRAMENTO, e isto e
    # deliberado. `FECHA` seria o nome obvio e seria mentira: no instante do
    # limite otimista a janela pode nem ter aberto, porque a conta parte do
    # nascimento e nao da morte. Pior que a imprecisao, um nome que afirme
    # encerramento SEMEARIA A REDACAO ERRADA em quem for escrever a mensagem
    # daqui a seis meses — a pessoa leria `FECHA` e escreveria "a janela
    # fechou", que e exatamente o que D-19 proibe. O nome do simbolo e a
    # primeira linha de defesa da mensagem.
    LIMITE = "limite"


# O PESO DE CADA ORIGEM NO DESEMPATE, e ele so vale quando os instantes empatam.
#
# As duas instancias do usuario (Yazalaque e Faerlina) podem gravar a MESMA
# deteccao com origens diferentes: uma leu a linha do chat, a outra so viu o
# boss no alvo. O anuncio do servidor e PROVA de nascimento; o alvo nao e (ver
# T-02-02). Deixar o desempate para a ordem de leitura do diretorio faria a
# mesma pasta produzir citacoes diferentes em maquinas diferentes — e a citacao
# E a ressalva (D-16), entao a maquina que perdesse o sorteio entregaria uma
# mensagem menos honesta sobre o mesmo fato.
_PESO_DA_ORIGEM = {
    OrigemDoAviso.ALVO: 0,
    OrigemDoAviso.CHAT: 1,
    OrigemDoAviso.CHAT_E_ALVO: 2,
}


# QUANTO A JANELA DO EPISODIO E MAIS CURTA QUE O MINIMO DO SERVIDOR.
#
# A janela do episodio e `respawn_horas_min - MARGEM_DO_EPISODIO`, e a direcao
# do erro e deliberada. Longa demais, dois nascimentos distintos caem no mesmo
# episodio e o segundo e CALADO — a party nao recebe nada e nao tem como saber
# que deixou de receber. Curta demais, uma remarcacao tardia de alvo abre um
# episodio novo e sai UMA mensagem repetida, que o usuario le e ignora em dois
# segundos. O falso negativo silencioso e o erro caro, entao a margem vai para
# o lado CURTO (T-03-01).
#
# Cinco minutos porque a ancora e gravada com resolucao de MINUTO (`<HHMM>`), e
# o truncamento pode encurtar a distancia aparente entre duas ancoras em ate 59
# segundos. Cinco e folga confortavel sobre esse limite e ainda deixa 5h55 de
# cobertura de remarcacao para o Tiat — muito alem de qualquer remarcacao
# plausivel, ja que o boss precisa estar vivo para ser alvejado.
MARGEM_DO_EPISODIO = timedelta(minutes=5)


@dataclass(frozen=True)
class Ancora:
    """Um nascimento observado, como ele volta do disco.

    `boss` e o APELIDO (`tiat-north`), e nao o nome do `config.toml`, porque e
    o apelido que o disco tem — a mesma separacao entre o que se GUARDA e o que
    se MOSTRA que `presenca.Fechamento.nicks` ja faz com os slugs. O nome
    bonito para a mensagem entra depois, vindo do `[[boss]]`.
    """

    boss: str
    instante: datetime
    origem: OrigemDoAviso


def chave_do_nascimento(
    nome: str, instante: datetime, origem: OrigemDoAviso
) -> str:
    """A identidade duravel de uma ancora, SEM o prefixo (D-18).

    Forma: `<YYYY-MM-DD>_<boss-slug>-<HHMM>_<origem>`.

    Quem poe o prefixo e `RegistroEmDisco.registrar_nascimento`, exatamente
    como `cancelar` poe o dele — o modulo que escreve o namespace e o dono do
    prefixo.

    A ORIGEM ENTRA NO NOME E NAO NO CONTEUDO. A mensagem que sai seis a oito
    horas depois precisa citar qual sinal ancorou (D-16), e essa informacao tem
    que sobreviver a um reinicio. Guarda-la no conteudo exigiria um "cria e
    depois escreve", e entre as duas operacoes existe uma janela em que a outra
    instancia le um arquivo vazio e nao sabe a origem — destruindo a
    propriedade que sustenta a pasta inteira, que e o marcador VAZIO cuja
    criacao atomica E a decisao de despacho.
    """
    apelido = apelido_do_evento(nome)
    return (
        f"{instante.date().isoformat()}"
        f"_{apelido}-{instante.hour:02d}{instante.minute:02d}"
        f"_{origem.value}"
    )


def ancora_de_chave(chave: str) -> Ancora | None:
    """O caminho de volta. Devolve `None` para qualquer nome torto, e NUNCA
    levanta.

    `.agenda/` e uma pasta comum que o usuario pode abrir, renomear e editar —
    ele ja o faz para religar um evento calado. Um arquivo criado a mao, um
    resto de uma versao anterior do formato ou um nome truncado por uma copia
    interrompida nao podem derrubar o laco que anuncia MORTE DE PARTY. O custo
    de ignorar um arquivo torto e uma previsao perdida; o custo de levantar e o
    scanner inteiro parado (T-02-07).

    A PARTIDA E EM TRES CAMPOS, COM `maxsplit=2`, e o detalhe nao e estetico: a
    origem `chat_e_alvo` CONTEM sublinhados, que sao o proprio separador. Um
    `split("_")` sem limite devolveria cinco campos e a origem voltaria
    truncada em `chat` — a mensagem citaria metade do sinal que ancorou, e nada
    levantaria.

    O CAMPO DO MEIO E PARTIDO PELO ULTIMO HIFEN, pela razao simetrica: o
    apelido contem hifens (`tiat-north`). Partir pelo primeiro devolveria
    `tiat` como boss e `north-1430` como hora.
    """
    partes = chave.split("_", 2)
    if len(partes) != 3:
        return None
    dia, meio, origem_crua = partes

    apelido, _, hora_crua = meio.rpartition("-")
    if not apelido or len(hora_crua) != 4 or not hora_crua.isdigit():
        return None

    try:
        data = datetime.fromisoformat(dia).date()
        instante = datetime(
            data.year,
            data.month,
            data.day,
            int(hora_crua[:2]),
            int(hora_crua[2:]),
        )
        origem = OrigemDoAviso(origem_crua)
    except ValueError:
        return None

    return Ancora(boss=apelido, instante=instante, origem=origem)


def ancoras_mais_recentes(chaves: Iterable[str]) -> dict[str, Ancora]:
    """A ancora que VALE para cada boss: a mais recente, por apelido.

    ESTA FUNCAO E JANE-04 INTEIRO (D-20), e o que ela faz de mais importante e
    o que ela NAO faz: nao existe marcador de cancelamento, e nao deve existir.

    Quando um nascimento novo e detectado antes de os avisos do ciclo anterior
    sairem, uma ancora nova e gravada; a partir dai a chave dos avisos velhos
    simplesmente NAO E MAIS GERADA, e eles param de vencer sozinhos. Cancelar
    por AUSENCIA e mais barato e mais correto que cancelar por marcador, porque
    nao ha um segundo estado que possa divergir do primeiro — nao existe o caso
    "o cancelamento nao foi gravado e o aviso velho saiu", que e exatamente a
    familia de defeito que um marcador de cancelamento traria de volta.

    Chaves tortas somem em silencio, por `ancora_de_chave`.
    """
    melhores: dict[str, Ancora] = {}
    for chave in chaves:
        ancora = ancora_de_chave(chave)
        if ancora is None:
            continue
        atual = melhores.get(ancora.boss)
        if atual is None or _ordem(ancora) > _ordem(atual):
            melhores[ancora.boss] = ancora
    return melhores


def _ordem(ancora: Ancora) -> tuple[datetime, int]:
    return (ancora.instante, _PESO_DA_ORIGEM[ancora.origem])


# ---------------------------------------------------------------------------
# O EPISODIO — um nascimento, uma mensagem.
# ---------------------------------------------------------------------------


def ancoras_do_boss(chaves: Iterable[str], apelido: str) -> list[Ancora]:
    """Todas as ancoras de UM boss, e nao so a que vale.

    E a irma pobre de `ancoras_mais_recentes` e existe separada por ser o unico
    pedaco reusavel entre a PREVISAO e o ANUNCIO — e porque um teste consegue
    afirma-la sozinha. A diferenca com a irma e o ponto inteiro: aquela reduz a
    UMA ancora por boss, e esta preserva todas, porque o episodio precisa da
    MAIS ANTIGA e a previsao precisa da mais recente.

    Chaves tortas somem em silencio, por `ancora_de_chave`.
    """
    achadas = []
    for chave in chaves:
        ancora = ancora_de_chave(chave)
        if ancora is not None and ancora.boss == apelido:
            achadas.append(ancora)
    return achadas


def inicio_do_episodio(
    ancoras: Iterable[Ancora],
    agora: datetime,
    horas_min: float,
    margem: timedelta = MARGEM_DO_EPISODIO,
) -> datetime | None:
    """O instante da ancora MAIS ANTIGA do episodio corrente, ou `None`.

    POR QUE A MAIS ANTIGA, E NAO QUALQUER OUTRA (D-28). A chave do marcador de
    anuncio precisa ser a MESMA string em todas as deteccoes de um nascimento,
    senao cada deteccao ganha o proprio marcador e o `O_CREAT|O_EXCL` nao
    impede nada. As candidatas obvias falham:

    - **O instante da deteccao**: a instancia que ticou as 21:59 e a que ticou
      as 22:00 produzem chaves diferentes. Duas mensagens.
    - **A ancora que esta deteccao acabou de escrever**: uma remarcacao de alvo
      escreve ancora nova (D-15), logo chave nova. Uma mensagem por remarcacao,
      que e o defeito de campo intacto.
    - **`ancoras_mais_recentes`**: mesmo problema. Ela existe para a PREVISAO,
      onde reancorar e o comportamento DESEJADO (JANE-04 / D-20); reusa-la aqui
      importaria o comportamento errado.

    A mais antiga e estavel por construcao: ancoras so sao escritas no
    presente, entao a mais antiga de um episodio nunca muda depois que o
    episodio comeca. As duas instancias, lendo a mesma pasta, calculam a mesma
    string — inclusive a que perdeu a corrida do `O_CREAT|O_EXCL` da propria
    ancora, porque o arquivo da vencedora ja esta la.

    O LIMITE INFERIOR E ESTRITO (`>`), E NAO FROUXO. Dois nascimentos
    consecutivos distam no MINIMO `horas_min`: a regra do servidor conta a
    partir da MORTE, e a morte e sempre depois do nascimento, entao
    `nascimento2 - nascimento1 >= horas_min` sempre. Com o limite frouxo, dois
    nascimentos exatamente no minimo cairiam no mesmo episodio e o segundo
    seria calado — a supressao virando perda, que e T-03-01.

    O `max(timedelta(0), ...)` protege um `[[boss]]` com `respawn_horas_min`
    menor que a margem: o episodio vira degenerado e o boss volta a ser
    anunciado a cada deteccao. E o comportamento de hoje, ruidoso e nao mudo —
    de novo o lado certo do erro.
    """
    janela = max(timedelta(0), timedelta(hours=horas_min) - margem)
    piso = agora - janela
    candidatos = [a.instante for a in ancoras if piso < a.instante <= agora]
    return min(candidatos) if candidatos else None


def chave_do_anuncio(apelido: str, instante: datetime) -> str:
    """A identidade duravel do anuncio de um episodio, SEM o prefixo (D-28).

    Forma: `<YYYY-MM-DD>_<boss-slug>-<HHMM>`, com a data e a hora do INICIO DO
    EPISODIO. Quem poe o prefixo e `RegistroEmDisco.registrar_anuncio`,
    exatamente como `cancelar` e `registrar_nascimento` poem os deles.

    A DATA VEM PRIMEIRO PORQUE A PODA A LE DAI. `agenda.podar` retira qualquer
    prefixo conhecido e entao le `YYYY-MM-DD` do inicio do que sobra; sem a
    data na frente o marcador nasceria imortal, e um marcador de silencio
    imortal e um boss que nunca mais e anunciado (T-03-03).

    A UNICA COLISAO CONCEBIVEL, e por que ela nao acontece: a raiz
    `<data>_<apelido>-<HHMM>` e a mesma de `Aviso.chave` e de
    `AvisoDeJanela.chave`. Mas aquelas duas nunca tem prefixo e sempre tem
    sufixo de tipo (`_agora`, `_abre`, `_limite`), e esta sempre tem prefixo e
    nunca tem sufixo. Os conjuntos de NOMES DE ARQUIVO sao disjuntos por
    construcao.
    """
    return (
        f"{instante.date().isoformat()}"
        f"_{apelido}-{instante.hour:02d}{instante.minute:02d}"
    )


def anunciar_nascimento(
    registro, boss: str, agora: datetime, regras: Iterable[Boss]
) -> bool:
    """True se ESTE processo deve anunciar o nascimento. Irma de
    `anunciar_janelas`.

    O `registrar_anuncio` E A DECISAO, E NAO HA CHECAGEM ANTERIOR NENHUMA AQUI.
    A leitura de `registro.nascimentos()` PARECE uma, e nao e: ela nao pergunta
    se o aviso ja saiu — ela CALCULA A CHAVE. A distincao e sutil e um leitor
    apressado vai confundi-la com o padrao proibido, entao fica escrita: esta
    funcao nao pode passar a ler `registro.enviados()`, nem um `anuncios()` que
    de proposito nao existe. Ai sim seria o read-then-write que a docstring de
    `RegistroEmDisco.marcar` proibe, e o sintoma seria um aviso PERDIDO e nao
    duplicado — as duas instancias se veriam livres para calar achando que a
    outra falou, e cada uma ficaria verde sozinha. O portao de
    `tests/test_anuncio_unico.py` afirma isso por AST.

    SEM A REGRA DO `[[boss]]`, ANUNCIA. Nao ha como saber o tamanho do episodio
    sem `respawn_horas_min`, e a escolha e a mesma que `marcar` ja faz no
    `except OSError`: preferir o duplicado ao perdido. A party consegue ignorar
    uma repeticao, mas nao consegue adivinhar um nascimento que ninguem
    anunciou. Na pratica o caso nao acontece — o vigia e construido da MESMA
    lista que vira `regras_de_respawn` — e a linha existe para o dia em que
    essa premissa mudar sem ninguem notar.

    EPISODIO VAZIO USA `agora`, E ESSE E O CAMINHO DO `--dry-run`. Em simulacao
    `registrar_nascimento` nao escreveu nada, entao nao ha ancora para ler; a
    consequencia (N voltas, N mensagens no console) e a mesma ja aceita em
    `tests/test_janela_no_relogio.py::TestOModoDeSimulacaoNaJanela`, e pela
    mesma razao: o produto inteiro do `--dry-run` e a mensagem aparecer.
    """
    apelido = apelido_do_evento(boss)

    regra = next((r for r in regras if r.nome == boss), None)
    if regra is None:
        return registro.registrar_anuncio(chave_do_anuncio(apelido, agora))

    ancoras = ancoras_do_boss(registro.nascimentos(), apelido)
    instante = inicio_do_episodio(ancoras, agora, regra.respawn_horas_min)
    return registro.registrar_anuncio(
        chave_do_anuncio(apelido, instante or agora)
    )


@dataclass(frozen=True)
class AvisoDeJanela:
    """Um aviso de janela que venceu e ainda nao foi enviado.

    `boss` e o NOME do `config.toml` (`Tiat North`), porque e ele que vai para
    a mensagem — o par do `Ancora.boss`, que e o apelido de disco. `horas` e a
    regra que produziu o alvo, guardada para a mensagem poder dizer "sao 6h"
    sem o texto conhecer o `[[boss]]`.
    """

    boss: str
    tipo: TipoDeJanela
    ancora: Ancora
    alvo: datetime
    horas: float

    @property
    def chave(self) -> str:
        """Identidade duravel do aviso: a data e a hora DA ANCORA, e o tipo.

        A CHAVE SAI DA ANCORA E NUNCA DO ALVO DO AVISO, e sao tres razoes:

        (a) **E o que faz D-20 funcionar sem marcador de cancelamento.** Uma
            ancora nova produz chaves novas, entao os avisos do ciclo anterior
            deixam de existir em vez de precisarem ser cancelados. Derivada do
            alvo, a chave do ciclo velho continuaria sendo gerada e o aviso
            obsoleto continuaria vencendo.

        (b) **A data da ancora e a que a poda de 3 dias tem que enxergar**, e
            ela e sempre menor ou igual a do alvo. Uma ancora das 22:00 abre as
            04:00 do dia seguinte: derivada do alvo, a poda leria uma data um
            dia a frente da que o marcador representa.

        (c) **E a mesma forma de `Aviso.chave`** — `<data>_<apelido>-<HHMM>_
            <tipo>` — entao um arquivo de aviso de janela e um de aviso de
            agenda podam pela MESMA linha de codigo, sem regra nova.

        A UNICA COLISAO CONCEBIVEL, e por que ela nao acontece: um `[[evento]]`
        chamado como um `[[boss]]`, vencendo no mesmo minuto, produziria a mesma
        raiz. Os sufixos de tipo sao disjuntos (`antes`/`agora`/`chamada`
        contra `abre`/`limite`), entao os nomes de arquivo nunca coincidem.
        """
        return (
            f"{self.ancora.instante.date().isoformat()}"
            f"_{self.ancora.boss}"
            f"-{self.ancora.instante.hour:02d}{self.ancora.instante.minute:02d}"
            f"_{self.tipo.value}"
        )


def janelas_devidas(
    agora: datetime,
    bosses: Iterable[Boss],
    ancoras: dict[str, Ancora],
    ja_enviados: set[str] | frozenset[str],
    tolerancia_minutos: int = TOLERANCIA_MINUTOS,
) -> list[AvisoDeJanela]:
    """Quais avisos de janela venceram agora e ainda nao sairam.

    Funcao PURA, no molde de `agenda.avisos_devidos`: mesmo instante, mesmas
    regras, mesmas ancoras, mesmo conjunto de enviados -> mesma lista, sempre.
    Sem disco, sem rede, sem relogio. E o que permite afirmar as quatro bordas
    de tolerancia em milissegundos, com o jogo fechado.

    O LACO E SOBRE OS BOSSES, E NAO SOBRE AS ANCORAS. Um `[[boss]]` que o
    usuario apagou do `config.toml` pode ter deixado a ancora dele em disco:
    varrendo as ancoras, essa orfa procuraria uma regra de respawn que nao
    existe mais. Varrendo os bosses, ela e ignorada ate a poda a levar.

    A JANELA DE TOLERANCIA E D-22, e a consequencia dela e DELIBERADA: um
    processo desligado durante os cinco minutos inteiros PERDE aquele aviso
    para sempre. Isso e preferivel a um lembrete de uma janela que abriu ha
    tres horas chegando quando o usuario sobe o scanner as 22h — e e a mesma
    regra escrita na terceira aresta da docstring de modulo de `agenda.py`.
    """
    devidos: list[AvisoDeJanela] = []
    tolerancia = timedelta(minutes=tolerancia_minutos)

    for boss in bosses:
        ancora = ancoras.get(apelido_do_evento(boss.nome))
        if ancora is None:
            continue
        candidatos = (
            (TipoDeJanela.ABRE, boss.respawn_horas_min),
            (TipoDeJanela.LIMITE, boss.respawn_horas_max),
        )
        for tipo, horas in candidatos:
            alvo = ancora.instante + timedelta(hours=horas)
            if not (alvo <= agora < alvo + tolerancia):
                continue
            aviso = AvisoDeJanela(
                boss=boss.nome,
                tipo=tipo,
                ancora=ancora,
                alvo=alvo,
                horas=horas,
            )
            if aviso.chave in ja_enviados:
                continue
            devidos.append(aviso)

    devidos.sort(key=lambda a: (a.alvo, a.tipo.value))
    return devidos


def anunciar_janelas(
    registro, bosses: Iterable[Boss], agora: datetime
) -> list[tuple[AvisoDeJanela, str]]:
    """As janelas que ESTE processo anunciou agora, ja com o texto pronto.

    UMA IMPLEMENTACAO PARA OS DOIS LACOS, e ela existe pelo motivo pelo qual
    `presenca.fechar_e_narrar` existe: o laco principal e o `--so-agenda`
    escrevem na MESMA pasta `.agenda/` e falam no MESMO grupo, entao duas
    copias desta sequencia fariam os dois modos do scanner anunciarem coisas
    diferentes sobre o mesmo boss no dia em que alguem consertasse so uma. O
    usuario deste projeto e exatamente quem roda os dois modos.

    O QUE FICA COM O CHAMADOR e o que e mesmo dele: o log, a moldura, o
    despacho e o `ResultadoDoTick`. Aqui mora so a decisao e o texto.

    O `marcar` E A DECISAO DE DESPACHAR (D-21), E O `ja_enviados` NAO E A
    GARANTIA. O filtro por `enviados()` existe so para o caminho comum nao
    criar arquivo a toa; entre aquela leitura e o `marcar`, a outra instancia
    do usuario pode ter escrito. Trocar o `marcar` por uma checagem anterior
    reintroduziria o read-then-write que a docstring de
    `RegistroEmDisco.marcar` proibe por escrito — e o resultado seria um aviso
    PERDIDO e nao duplicado, porque as duas instancias se veriam livres para
    calar achando que a outra falou.
    """
    ancoras = ancoras_mais_recentes(registro.nascimentos())
    devidos = janelas_devidas(agora, bosses, ancoras, registro.enviados())

    anunciados: list[tuple[AvisoDeJanela, str]] = []
    for aviso in devidos:
        if not registro.marcar(aviso.chave):
            continue
        anunciados.append((aviso, texto_da_janela(aviso)))
    return anunciados


def texto_da_janela(aviso: AvisoDeJanela) -> str:
    """A mensagem que a party le no grupo.

    A MENSAGEM COMECA PELO NOME DO BOSS (D-14), como todo o resto desta
    familia: e a informacao que decide para onde a party se desloca.

    A CITACAO DA ORIGEM E A RESSALVA (D-16), e nao ha uma quinta frase generica
    de aviso. O usuario escolheu COBERTURA sobre precisao (D-15) — os dois
    sinais ancoram, inclusive o alvo — com a condicao de o erro ser LEGIVEL, e
    a linha que atribui a citacao ao alvo e onde ele fica legivel.

    A MEDIDA DE CAMPO QUE TORNA ISSO NECESSARIO: em 2026-08-30, as 14h30, um
    `Tiat South` estava no alvo do usuario no meio da luta, sem ter acabado de
    nascer. Ter o boss marcado nao prova nascimento, e o alvo REARMA quando o
    usuario desmarca e remarca — entao a mesma criatura, ja viva ha uma hora,
    pode gravar uma ancora nova e reiniciar a conta. Uma ressalva generica
    acrescentada as quatro frases diluiria a diferenca entre as duas origens,
    que e a informacao inteira: quem le precisa saber se o numero veio de uma
    prova ou de um indicio, para julgar sozinho o quanto confiar nele.

    `CHAT_E_ALVO` CAI NO CAMINHO DO ANUNCIO. Quando os dois sinais estao
    presentes, o anuncio ja e prova de nascimento e o alvo nao acrescenta nada
    a honestidade do numero — uma quinta frase citando os dois daria a
    impressao de mais certeza sem haver mais certeza.

    NENHUMA DAS QUATRO FRASES AFIRMA QUE A JANELA FECHOU OU QUE A PARTY PERDEU
    O BOSS (D-19). A frase do limite AFIRMA O PISO ("dele para a frente ele
    pode nascer a qualquer momento") em vez de NEGAR um encerramento, e a
    escolha e deliberada: a negacao seria igualmente honesta, mas poria dentro
    do texto de PRODUCAO as palavras que o portao de
    `tests/test_respawn.py::TestNenhumaAfirmacaoDeEncerramento` existe para
    proibir, e o portao passaria a acusar justamente a frase que deveria
    aprovar. Afirmar o piso diz a mesma coisa, melhor, e deixa o portao limpo.

    AS HORAS SAEM DE `aviso.horas`, que veio do `[[boss]]`, e nunca de um
    numero escrito aqui: um boss novo no `config.toml` tem que produzir a frase
    com as horas dele.
    """
    instante = aviso.ancora.instante
    hora = f"{instante.hour:02d}:{instante.minute:02d}"
    data = f"{instante.day:02d}/{instante.month:02d}"
    horas = f"{aviso.horas:g}h"

    ancorado_no_anuncio = aviso.ancora.origem is not OrigemDoAviso.ALVO
    if ancorado_no_anuncio:
        desde = f"desde o nascimento anterior, que o servidor anunciou as {hora} de {data}"
        ressalva = ""
    else:
        desde = (
            f"desde a ultima vez que seu alvo virou {aviso.boss}, "
            f"as {hora} de {data}"
        )
        ressalva = (
            " Ter o boss no alvo nao prova que ele tinha acabado de nascer, "
            "entao este numero pode estar adiantado."
        )

    if aviso.tipo is TipoDeJanela.ABRE:
        return (
            f"{aviso.boss}: a janela abriu. Antes de agora ele nao nascia; "
            f"sao {horas} {desde}.{ressalva} "
            f"A conta parte do nascimento e nao da morte, entao ele ainda "
            f"pode demorar."
        )

    if ancorado_no_anuncio:
        return (
            f"{aviso.boss}: passaram as {horas} {desde}. "
            f"Esse era o limite otimista da conta, e dele para a frente ele "
            f"pode nascer a qualquer momento: a conta parte do nascimento e "
            f"nao da morte, entao o tempo em que o boss ficou vivo ainda nao "
            f"entrou nela."
        )
    # A CLAUSULA DA MORTE ENTRA AQUI TAMBEM, e a razao e que esta era a UNICA
    # das quatro frases sem ela. As outras tres dizem "a conta parte do
    # nascimento e nao da morte"; esta dizia so a ressalva do alvo.
    #
    # E justamente a frase que mais precisa: ela junta as DUAS fontes de atraso
    # da previsao. A ressalva do alvo cobre uma (o boss podia estar de pe ha
    # horas quando foi alvejado) e a clausula da morte cobre a outra (o tempo
    # em que ele ficou vivo depois do nascimento nunca entrou na conta). Sem a
    # segunda, quem le atribui o adiantamento inteiro ao alvo e conclui que um
    # aviso ancorado no chat seria exato — e nao seria.
    return (
        f"{aviso.boss}: passaram as {horas} {desde}.{ressalva} "
        f"Esse era o limite otimista da conta, e dele para a frente ele pode "
        f"nascer a qualquer momento: a conta parte do nascimento e nao da "
        f"morte, entao o tempo em que o boss ficou vivo ainda nao entrou nela."
    )


def _citacao_da_ancora(boss_no_config: str, ancora: Ancora) -> tuple[str, str]:
    """A citacao da origem e a ressalva, na MESMA distincao das quatro frases.

    Extraida para o console e a mensagem do grupo nao poderem divergir na
    unica coisa que D-16 protege: quem le o console tem que poder julgar o
    numero com a mesma informacao de quem le o grupo.
    """
    instante = ancora.instante
    hora = f"{instante.hour:02d}:{instante.minute:02d}"
    data = f"{instante.day:02d}/{instante.month:02d}"

    if ancora.origem is not OrigemDoAviso.ALVO:
        return (
            f"do nascimento que o servidor anunciou as {hora} de {data}",
            "",
        )
    return (
        f"da ultima vez que seu alvo virou {boss_no_config}, "
        f"as {hora} de {data}",
        " Ter o boss no alvo nao prova nascimento, entao este numero pode "
        "estar adiantado.",
    )


def linhas_de_previsao(
    agora: datetime, bosses: Iterable[Boss], ancoras: dict[str, Ancora]
) -> list[str]:
    """O que o console diz no arranque sobre cada boss vigiado (OPER-02).

    FUNCAO PURA, no molde de `texto_da_janela`: devolve texto e quem imprime e
    o chamador — a mesma disciplina que faz `presenca.texto_de_fechamento` so
    formatar. Uma linha por `Boss`, na ordem do `config.toml`, porque uma ordem
    que muda entre arranques faria o usuario reler a lista inteira toda vez.

    A METADE QUE JA EXISTIA. `montar_vigia_de_bosses` NOMEIA os bosses vigiados
    desde a Fase 1, e a linha dela foi escrita assim de proposito para o nome
    poder virar a ancora deste texto. As duas juntas sao OPER-02 inteiro; esta
    aqui e a metade "qual a proxima janela".

    A LINHA DE QUEM NAO TEM ANCORA NAO CONTEM HORARIO NENHUM, e isso e a coisa
    mais importante desta funcao. O console dizendo "ainda nao vi nascimento
    deste boss" e a RESPOSTA CORRETA, e nao uma degradacao: um horario
    inventado ali seria a mesma familia de defeito que a poda de tres dias
    existe para impedir — uma afirmacao sobre o futuro que ninguem tem como
    conferir — so que na tela em vez de no grupo (T-02-13).

    LISTA DE BOSSES VAZIA DEVOLVE LISTA VAZIA, e nao uma linha dizendo que nao
    ha bosses: `montar_vigia_de_bosses` ja diz isso, e com o texto que ensina a
    ligar. Repetir treinaria o usuario a ignorar as duas.

    O `agora` ENTRA POR PARAMETRO e nao e lido aqui dentro, pela razao ja
    escrita em `_anunciar_proximo`: e o que impede esta funcao de ser a ultima
    do arquivo a perguntar as horas ao Windows. Ele decide so o TEMPO VERBAL —
    uma janela que abre daqui a pouco e uma que ja abriu sao fatos diferentes,
    e o console que os confunde manda a party sair na hora errada.

    NENHUMA LINHA AFIRMA ENCERRAMENTO (D-19), pela mesma aritmetica das quatro
    frases: a conta parte do NASCIMENTO e nao da morte, entao o limite otimista
    passa `k` cedo, onde `k` e o tempo que o boss ficou vivo. As linhas entram
    no MESMO portao de tokens de `tests/test_respawn.py`, e nao num segundo que
    poderia divergir dele.

    A LINHA COM ANCORA TERMINA PELA REGRA (`_regra_da_janela`), e a razao de a
    frase morar aqui — e nao so na resposta do comando `/tiat` — esta escrita
    naquela funcao. A LINHA SEM ANCORA NAO A RECEBE, e a assimetria e
    deliberada: T-02-13 exige que ela nao contenha numero NENHUM, e a regra e
    feita de dois numeros. Alem disso, ela nao teria o que explicar — nao ha
    intervalo previsto para justificar.
    """
    linhas: list[str] = []
    for boss in bosses:
        ancora = ancoras.get(apelido_do_evento(boss.nome))
        if ancora is None:
            linhas.append(
                f"{boss.nome}: ainda nao vi nascimento nenhum deste boss, "
                f"entao nao tenho previsao de janela para ele."
            )
            continue

        abre = ancora.instante + timedelta(hours=boss.respawn_horas_min)
        limite = ancora.instante + timedelta(hours=boss.respawn_horas_max)
        desde, ressalva = _citacao_da_ancora(boss.nome, ancora)
        linhas.append(
            f"{boss.nome}: a janela "
            f"{'abre' if agora < abre else 'abriu'} em {_quando(abre)} e o "
            f"limite otimista "
            f"{'passa' if agora < limite else 'passou'} em {_quando(limite)}, "
            f"contados {desde}.{ressalva} {_regra_da_janela(boss)}"
        )
    return linhas


def _regra_da_janela(boss: Boss) -> str:
    """A regra do servidor por extenso: a parte FIXA mais o SORTEIO.

    POR QUE ESTA FRASE EXISTE. A linha antiga entregava dois horarios e nenhuma
    explicacao para eles serem dois. Quem le um intervalo sem a regra que o
    produziu inventa a explicacao sozinho, e a mais natural — "o bot esta em
    duvida entre dois horarios" — e falsa: o scanner nao esta incerto sobre a
    conta, o SERVIDOR e que sorteia dentro da faixa. A diferenca decide o que a
    party faz: uma conta duvidosa se ignora, um sorteio se espera.

    POR QUE ELA MORA AQUI, DENTRO DA PREVISAO, E NAO SO NA RESPOSTA DO COMANDO.
    Foi uma escolha entre duas, e as duas tinham argumento. Contra: o console e
    o anuncio horario ficam com uma frase a mais que ninguem pediu. A favor, e
    e o que decidiu: e a MESMA disciplina de `_citacao_da_ancora`, escrita ali
    por D-16 — quem le o console tem que poder julgar o numero com a mesma
    informacao de quem le o WhatsApp. A regra e parte de como julgar o numero,
    e nao enfeite; posta so na resposta do comando, ela seria a primeira coisa
    desta familia a existir num canal e faltar no outro, e a segunda copia
    nasceria livre para divergir da primeira no dia em que o servidor trocasse
    a regra de novo. Uma frase a mais no console e barato; duas versoes da
    mesma verdade nao e.

    OS DOIS NUMEROS SAO CALCULADOS E NUNCA ESCRITOS. A parte fixa e
    `respawn_horas_min`; a aleatoria e a DIFERENCA entre os dois campos do
    `[[boss]]`. O servidor ja mudou a regra uma vez — era 6h fixas mais ate 2h,
    virou 8h mais ate 2h — e vai mudar de novo. Um literal aqui viraria uma
    mentira que passa em todos os testes, porque nenhum deles compara o texto
    com o `config.toml`.

    FAIXA ZERO NAO ANUNCIA SORTEIO. `ler_bosses` so recusa `max` MENOR que
    `min`, entao `max == min` e uma configuracao legal. A frase generica sairia
    como "mais ate 0h aleatorias", que e pior que nao dizer nada: ela promete
    um sorteio inexistente e manda o leitor procurar uma faixa de largura zero.

    NAO AFIRMA ENCERRAMENTO (D-19) e nao pode passar a afirmar. Ela descreve a
    regra do servidor, que conta a partir da MORTE; a previsao conta a partir
    do NASCIMENTO. Dizer aqui que "depois de 10h ele ja nasceu" seria juntar as
    duas contas e produzir exatamente a afirmacao que o portao de tokens de
    `tests/test_respawn.py` recusa.
    """
    fixas = boss.respawn_horas_min
    aleatorias = boss.respawn_horas_max - boss.respawn_horas_min
    if aleatorias <= 0:
        return (
            f"A regra deste boss sao {fixas:g}h cravadas, sem parte sorteada: "
            f"os dois horarios acima sao o mesmo instante."
        )
    return (
        f"A regra sao {fixas:g}h fixas mais ate {aleatorias:g}h aleatorias, "
        f"entao o nascimento cai em algum ponto entre os dois horarios acima."
    )


def _quando(instante: datetime) -> str:
    """O MESMO formato de `_anunciar_proximo` (`%d/%m %H:%M`).

    Duas formas de data no mesmo bloco de arranque fariam o usuario decidir, a
    cada linha, qual campo e o dia.
    """
    return (
        f"{instante.day:02d}/{instante.month:02d} "
        f"{instante.hour:02d}:{instante.minute:02d}"
    )
