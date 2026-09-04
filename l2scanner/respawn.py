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


# QUANTO TEMPO DE DETECCOES CONTA COMO UM MESMO NASCIMENTO.
#
# ESTA GRANDEZA E PROPRIA, E NAO SAI MAIS DE `respawn_horas_min`. Ate
# 2026-08-31 ela era `respawn_horas_min - 5min`, e esse acoplamento custou dois
# avisos no mesmo dia: com 8 horas escritas no `config.toml` (numero errado; a
# regra do servidor e 6 mais 0 a 2 aleatorias) a janela virou 7h55, o
# nascimento das 14:12 caiu a 7.83h do das 06:22, e o silencio comeu um
# nascimento de verdade. Errar aquele numero pode, no maximo, atrasar uma
# PREVISAO; nao pode APAGAR um aviso. Por isso ele nao entra mais nesta conta.
#
# ELA NAO PRECISA DE HORAS. So precisa cobrir as deteccoes de UM MESMO
# nascimento, e essas se juntam em MINUTOS: sao a linha do servidor persistindo
# no recorte do chat, as duas instancias do usuario ticando com segundos de
# diferenca, e o alvo sendo desmarcado e remarcado.
#
# A MEDIDA, feita em 2026-08-31 sobre os arquivos `nascimento_*` de `.agenda/`
# do repositorio. Vao entre a PRIMEIRA e a ULTIMA deteccao de cada nascimento:
#
#     30/08  tiat-north  22:17 -> 22:29   12 min   (9 deteccoes)
#     30/08  tiat-south  21:59 -> 22:06    7 min   (6 deteccoes)
#     31/08  tiat-north  06:22 -> 06:26    4 min   (4 deteccoes)
#     31/08  tiat-north  14:12 -> 14:19    7 min   (9 deteccoes)
#     31/08  tiat-south  04:07 -> 04:09    2 min   (2 deteccoes)
#     31/08  tiat-south  12:13 -> 12:15    2 min   (3 deteccoes)
#
# MAIOR VAO MEDIDO: 12 MINUTOS. A FOLGA: 25 = 12 (a medida) + 12 (o dobro dela,
# porque seis nascimentos sao amostra pequena e o pior caso plausivel e uma
# sequencia de remarcacoes mais longa que a de 30/08) + 1 (a ancora e gravada
# com resolucao de MINUTO em `<HHMM>`, e o truncamento pode encurtar a
# distancia aparente entre duas ancoras em ate 59 segundos).
#
# A DIRECAO DO ERRO CONTINUA A MESMA de antes, e e o que decide os dois lados
# da folga. Longa demais, dois nascimentos distintos caem no mesmo episodio e o
# segundo e CALADO — a party nao recebe nada e nao tem como saber que deixou de
# receber. Curta demais, uma deteccao atrasada abre um episodio novo e sai UMA
# mensagem repetida, que o usuario le e ignora em dois segundos.
#
# O QUE 25 MINUTOS DEIXA PASSAR, medido e aceito: a ancora isolada de
# `tiat-north` das 07:16 de 31/08 esta 54 minutos depois da das 06:22 e tem uma
# unica deteccao, de chat. E quase certamente a mesma linha do servidor relida
# na tela, e com esta janela ela rende uma mensagem repetida. E o lado barato.
#
# O TETO QUE IMPEDE O INCIDENTE DE VOLTAR mora em
# `config.ler_janela_do_episodio`: o arranque recusa uma janela maior ou igual
# ao menor `respawn_horas_min` configurado, que e exatamente o estado de 31/08.
JANELA_DO_EPISODIO = timedelta(minutes=25)


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
    janela: timedelta = JANELA_DO_EPISODIO,
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

    A JANELA E GRANDEZA PROPRIA, E EM 2026-08-31 ELA DEIXOU DE SAIR DE
    `respawn_horas_min`. A versao anterior desta docstring afirmava:

        "Dois nascimentos consecutivos distam no MINIMO horas_min: a regra do
        servidor conta a partir da MORTE, e a morte e sempre depois do
        nascimento, entao nascimento2 - nascimento1 >= horas_min sempre."

    A frase e VERDADEIRA SOBRE O SERVIDOR e FALSA SOBRE A CONFIGURACAO, e a
    diferenca custou dois avisos em 2026-08-31. `horas_min` nao e a regra do
    servidor: e um numero que uma pessoa digitou num arquivo de texto. Naquele
    dia o `config.toml` dizia 8 (a regra real e 6 mais 0 a 2 aleatorias), a
    janela virou 7h55, e os nascimentos de `Tiat North` das 07:16 e das 14:12
    cairam DENTRO dela. O `O_CREAT|O_EXCL` fez o que devia; a premissa e que
    era falsa, e o custo foi um nascimento de boss que ninguem soube que
    aconteceu.

    A LICAO ESTRUTURAL: um numero de config errado pode atrasar uma PREVISAO,
    e nao pode APAGAR um aviso. Por isso `horas_min` nao chega mais ate aqui
    nem por parametro. O que sobra e uma janela pequena e medida, cujo tamanho
    esta derivado no comentario de `JANELA_DO_EPISODIO`.

    O LIMITE INFERIOR CONTINUA ESTRITO (`>`), E NAO FROUXO, e agora a razao e
    outra: uma ancora exatamente na borda ja pertence ao ciclo anterior por
    definicao da janela, e inclui-la faria a chave do episodio depender de um
    empate de segundo que o nome de arquivo `<HHMM>` nem guarda.

    UMA JANELA DE ZERO DEIXA O EPISODIO DEGENERADO e o boss volta a ser
    anunciado a cada deteccao, que e o defeito de spam de 2026-08-30. E por
    isso que `config.ler_janela_do_episodio` recusa zero no arranque, em vez de
    esta funcao remendar em silencio.
    """
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
    registro,
    boss: str,
    agora: datetime,
    janela: timedelta = JANELA_DO_EPISODIO,
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

    A LISTA DE `[[boss]]` NAO ENTRA MAIS AQUI, e a ausencia dela e o conserto
    de 2026-08-31. Ate aquele dia esta funcao procurava a `regra` do boss so
    para tirar dela o `respawn_horas_min` e derivar o tamanho do episodio; com
    o numero errado no `config.toml`, a janela virou 7h55 e dois nascimentos de
    verdade foram calados. O tamanho do episodio agora entra por `janela`, que
    e grandeza propria e medida, e o valor de `respawn_horas_min` deixou de
    poder alcancar esta decisao POR ASSINATURA, e nao por disciplina. Ele
    continua mandando na PREVISAO (`janelas_devidas`), que e onde erra-lo custa
    o que sempre devia ter custado: um horario adiantado ou atrasado.

    QUALQUER BOSS ANUNCIA A PRIMEIRA DETECCAO, inclusive um que nao esteja em
    `[[boss]]` nenhum. Antes isso era um caso especial escrito a mao; agora e
    consequencia da forma, porque sem ancora anterior o episodio comeca AGORA.
    A escolha e a mesma que `marcar` ja faz no `except OSError`: preferir o
    duplicado ao perdido. A party consegue ignorar uma repeticao, mas nao
    consegue adivinhar um nascimento que ninguem anunciou.

    EPISODIO VAZIO USA `agora`, E ESSE E O CAMINHO DO `--dry-run`. Em simulacao
    `registrar_nascimento` nao escreveu nada, entao nao ha ancora para ler; a
    consequencia (N voltas, N mensagens no console) e a mesma ja aceita em
    `tests/test_janela_no_relogio.py::TestOModoDeSimulacaoNaJanela`, e pela
    mesma razao: o produto inteiro do `--dry-run` e a mensagem aparecer.
    """
    apelido = apelido_do_evento(boss)

    ancoras = ancoras_do_boss(registro.nascimentos(), apelido)
    instante = inicio_do_episodio(ancoras, agora, janela)
    return registro.registrar_anuncio(
        chave_do_anuncio(apelido, instante or agora)
    )


@dataclass(frozen=True)
class AvisoDeJanela:
    """Um aviso de janela que venceu e ainda nao foi enviado.

    `boss` e o NOME do `config.toml` (`Tiat North`), porque e ele que vai para
    a mensagem — o par do `Ancora.boss`, que e o apelido de disco.

    `horas` NAO ENTRA MAIS NA MENSAGEM DESDE 2026-09-03. Ficou escrito aqui que
    ela era "a regra que produziu o alvo, guardada para a mensagem poder dizer
    'sao 6h' sem o texto conhecer o `[[boss]]`" — e esse era o uso unico dela.
    O segundo corte de texto tirou as "8h" das quatro frases, e a razao inteira
    esta em `texto_da_janela`. O CAMPO FICA porque continua sendo o unico
    registro de QUAL das duas regras do `[[boss]]` produziu este `alvo`:
    `tipo` diz se e abertura ou limite e nao diz o numero, entao sem `horas` um
    aviso guardado so se explica reabrindo o `config.toml` — que pode ja ter
    mudado.
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

    AS HORAS DO `[[boss]]` SAIRAM DA FRASE EM 2026-09-03, E ESTA LINHA MUDOU
    COM ELAS. O que estava escrito aqui era: "as horas saem de `aviso.horas`,
    que veio do `[[boss]]`, e nunca de um numero escrito aqui: um boss novo no
    `config.toml` tem que produzir a frase com as horas dele." A metade que
    continua valendo e a segunda: NENHUM numero desta frase pode ser escrito no
    codigo. O que mudou e que as "8h" nao sao mais DITAS — elas sao a regra do
    servidor, identica em toda mensagem de um mesmo boss, todo dia, e quem quer
    o detalhe pergunta ao `/tiat`, que entrega os dois horarios ja calculados
    de `respawn_horas_min` e `respawn_horas_max`. A prova de que o numero vem
    do `[[boss]]` e nao do codigo mora la, em
    `TestAsLinhasDePrevisaoDoConsole::test_as_horas_saem_do_bloco_boss_e_nao_do_codigo`,
    medida sobre um boss de 3h/4h.

    O UNICO NUMERO QUE SOBROU NA FRASE E A HORA DA ANCORA, e ele sai do
    `Ancora.instante`. E o que permite CONFERIR a conta: sem ele a mensagem
    vira uma afirmacao sobre o futuro sem nada por baixo.

    O QUE SAIU DAQUI EM 2026-09-02, E PARA ONDE FOI. O usuario pediu mensagens
    curtas, de leitura rapida no celular no meio do farm. As quatro frases
    tinham de 161 a 248 caracteres, e a maior parte do excedente era UMA
    justificativa aritmetica repetida em todas: "a conta parte do nascimento e
    nao da morte, entao o tempo em que o boss ficou vivo ainda nao entrou
    nela".

    ELA MOROU AQUI POR UM MOTIVO CERTO, e o motivo continua valendo: e a razao
    de os dois avisos sairem CEDO, nunca tarde. Chame de `k` o tempo que o boss
    ficou vivo entre o nascimento e a morte. A previsao conta do NASCIMENTO
    anterior, entao a janela real abre `k` depois do que esta escrito na
    mensagem, e `k` e um numero que o scanner nao tem como medir. Nada disso
    mudou; o que mudou e onde esta escrito.

    O QUE FICOU NA MENSAGEM E A CONSEQUENCIA, que e a unica parte acionavel:
    "Ele ainda pode demorar" na abertura e "Ele pode nascer a qualquer
    momento" no limite. As duas dizem ao leitor o que FAZER com o numero. A
    aritmetica dizia por que o numero e aquele, e quem le no celular durante
    uma luta nao vai refazer a conta: le a ressalva e decide. A justificativa
    ficou aqui, nesta docstring, onde quem for MEXER na conta a encontra.

    O PISO CONTINUA AFIRMADO — MAS A FRASE DELE ENCOLHEU, E A LINHA ANTIGA
    ESTAVA ERRADA. Em 2026-09-02 ficou escrito aqui: "o piso continua afirmado,
    e essa parte nao encolheu. [...] Encurtar em cima dela seria trocar
    informacao por texto." Em 2026-09-03 ela encolheu: "Pode nascer a qualquer
    momento" (30 caracteres) virou "pode nascer agora" (17), e NADA foi trocado
    por texto — as duas dizem que o nascimento pode acontecer neste instante,
    que e a coisa inteira que o leitor FAZ com o limite. O que a linha antiga
    acertou continua de pe: a AFIRMACAO DO PISO nao pode sair, porque ela e o
    substituto de D-19 para a negacao de encerramento, e ela sai literal nas
    duas frases de limite.

    O SEGUNDO CORTE, EM 2026-09-03: DE 115-169 PARA 80 CARACTERES. O pedido foi
    "jogadores ficam recebendo essa mesma mensagem todo dia, nao descarte
    informacoes importante mas reduza o tamanho". O ORCAMENTO SAI DA
    FREQUENCIA, e nao do gosto de quem escreve: estas quatro frases vao para o
    GRUPO, entao cada caractere e pago pelo numero de pessoas VEZES o numero de
    ocorrencias, e o mesmo texto chega todo dia. O teto de 80 esta em
    `tests/test_mensagens_curtas.py` e e medido no PIOR caso — limite, ancora
    de alvo, ancora de ONTEM (que e a unica que carrega data).

    O QUE SAIU, E POR QUE CADA COISA PODIA SAIR:

    - as "8h": a regra do servidor, identica em toda mensagem (acima);
    - "que o servidor anunciou": a atribuicao virou o ROTULO "Nascimento", que
      ja e a palavra do fato PROVADO, contra "Alvo" na outra origem. A
      distincao entre prova e indicio — que e a informacao inteira de D-16 —
      sobrevive nos dois rotulos, e e por eles que os testes a medem;
    - "otimista", de "passou o limite otimista": o adjetivo explicava POR QUE
      ha dois horarios, e quem le no celular no meio de uma luta nao refaz essa
      conta. "limite passou" diz o ESTADO e "pode nascer agora" diz o que
      FAZER com ele;
    - a DATA da ancora, QUANDO ELA E DO MESMO DIA (`_citacao_da_ancora`).

    A ORDEM MUDOU, E E A PARTE DESTE CORTE QUE NAO E SO TAMANHO. A frase agora
    e `<boss>: <estado>, <o que fazer>. <de onde veio o numero>.` — o primeiro
    pedaco, ate o ponto, e a mensagem ACIONAVEL inteira, e o que vem depois e a
    trilha de conferencia. Uma olhada de meio segundo le "Tiat North: janela
    ABERTA, pode demorar." e ja decide; quem quiser conferir a conta le o
    resto. Na ordem antiga a citacao ficava NO MEIO, entre o estado e a
    instrucao, e obrigava a atravessar ~60 caracteres de proveniencia para
    chegar na unica linha que manda alguem fazer alguma coisa.
    """
    # A REFERENCIA E `aviso.alvo`, E NAO UM RELOGIO. E o instante em que esta
    # janela venceu, e a tolerancia de D-22 garante que ele esta a menos de
    # cinco minutos de agora — entao "mesmo dia que o alvo" e "mesmo dia que
    # quem esta lendo". Perguntar as horas ao Windows aqui dentro faria desta a
    # primeira funcao pura do arquivo com relogio proprio, e o portao de AST de
    # `TestSemRelogioProprio` recusaria.
    desde, ressalva = _citacao_da_ancora(aviso.ancora, referencia=aviso.alvo)

    if aviso.tipo is TipoDeJanela.ABRE:
        # "pode demorar" E A CLAUSULA DA MORTE, dita pela consequencia em vez
        # da aritmetica. A aritmetica esta na docstring acima; no celular ela
        # custava 70 caracteres para entregar a mesma unica instrucao
        # operacional, que e nao sair correndo.
        return f"{aviso.boss}: janela ABERTA, pode demorar. {desde}{ressalva}."

    # "pode nascer agora" E O PISO AFIRMADO (D-19), e sai literal nas DUAS
    # frases de limite. Ele nao e enfeite nem justificativa: e a unica coisa
    # que um leitor pode FAZER com o limite, e afirmar o piso e o que substitui
    # a negacao de encerramento que o portao de tokens proibe. O piso pode
    # ENCOLHER — encolheu em 2026-09-03 — mas nao pode SAIR.
    return f"{aviso.boss}: limite passou, pode nascer agora. {desde}{ressalva}."


def _citacao_da_ancora(
    ancora: Ancora, referencia: datetime | None = None
) -> tuple[str, str]:
    """A citacao da origem e a ressalva, na MESMA distincao das quatro frases.

    UMA SO ORIGEM DE TEXTO PARA AS DUAS FAMILIAS, AGORA EM DUAS FORMAS. Desde
    2026-09-02 esta funcao serve `texto_da_janela` (as quatro frases do grupo)
    E `linhas_de_previsao` (a resposta do `/tiat` e o console). Em 2026-09-03
    as duas familias deixaram de caber no MESMO texto, e a razao esta escrita
    em `tests/test_mensagens_curtas.py`: o orcamento sai da FREQUENCIA, e a
    frase do grupo chega a todo mundo todo dia (teto 80) enquanto a linha do
    console e pedida por quem quer o detalhe (teto 160).

    ENTAO POR QUE NAO DUAS FUNCOES. Porque a ressalva do alvo e a distincao
    entre prova e indicio sao D-16, e o defeito que se quer impedir e uma das
    duas familias PERDER a ressalva sem ninguem notar. Com as duas formas neste
    corpo, quem encurtar uma le a outra na linha de baixo; com duas funcoes em
    dois lugares, a primeira pressa apaga uma delas. O que se abriu mao e de
    elas serem o mesmo TEXTO — nao de elas dizerem a mesma coisa.

    `referencia` E O QUE ESCOLHE A FORMA, e nao um segundo parametro de estilo:
    a forma curta so existe porque ha um instante de leitura contra o qual
    "mesmo dia" significa alguma coisa. Sem `referencia`, forma longa.

    O BOSS SAIU DA CITACAO DO ALVO, e o parametro `boss_no_config` com ele. A
    frase antiga era "da ultima vez que seu alvo virou Tiat North, as 14:30 de
    30/08" e as duas familias de mensagem ja COMECAM pelo nome do boss (D-14).
    Repeti-lo no meio custava 13 caracteres para nomear pela segunda vez, na
    mesma frase, a criatura que o leitor acabou de ler. "Desde que virou seu
    alvo" diz a mesma coisa e nao deixa duvida sobre quem virou.

    A RESSALVA ENCOLHEU MAS NAO SAIU, e a distincao importa. "Ter o boss no
    alvo nao prova nascimento, entao este numero pode estar adiantado" virou
    "Alvo nao prova nascimento, pode estar adiantado": 65 caracteres a menos,
    a mesma afirmacao. Ela nao podia sair de jeito nenhum, e a razao esta em
    `texto_da_janela`: o alvo REARMA quando o usuario desmarca e remarca,
    entao uma criatura viva ha uma hora pode gravar ancora nova e reiniciar a
    conta. Com D-15 (cobertura sobre precisao) escolhido, esta linha e a
    unica coisa que mantem o erro LEGIVEL, e o usuario decide sair de casa
    com base nela.

    A CITACAO DO ANUNCIO NAO TEM RESSALVA porque nao ha o que ressalvar: o
    servidor anunciou o nascimento, e isso e prova. Uma ressalva generica nas
    duas diluiria a diferenca entre prova e indicio, que e a informacao
    inteira.

    A FORMA CURTA, DE 2026-09-03, E O QUE SOBROU DE CADA UMA DAS DUAS METADES:

    - a ORIGEM virou um rotulo — "Nascimento" contra "Alvo" — e o rotulo faz
      sozinho o trabalho que "desde o nascimento que o servidor anunciou" e
      "desde que virou seu alvo" faziam em 60 caracteres. Ele abre a frase
      depois do ponto, entao vem com maiuscula;
    - a RESSALVA virou ", pode adiantar", uma clausula da propria citacao em
      vez de uma segunda frase — e aqui houve PERDA MEDIDA, que esta escrita
      logo abaixo.

    A RESSALVA PERDEU UMA METADE, E A LINHA ANTIGA PROMETIA QUE NAO PERDERIA.
    Em 2026-09-02 ficou escrito aqui que "Ter o boss no alvo nao prova
    nascimento, entao este numero pode estar adiantado" virou "Alvo nao prova
    nascimento, pode estar adiantado" com "65 caracteres a menos, A MESMA
    AFIRMACAO". Em 2026-09-03 ela virou ", pode adiantar" (48 caracteres a
    menos) e isso NAO e a mesma afirmacao: o "nao prova nascimento" saiu da
    frase do grupo. O que ficou no lugar dele e o proprio rotulo "Alvo", que
    diz de onde veio o numero, mais a consequencia, que e a parte acionavel. A
    afirmacao inteira continua na LINHA DO CONSOLE (forma longa, logo abaixo),
    que e onde ha 160 caracteres para gasta-la, e a razao de ela nao poder
    sumir das duas esta em `texto_da_janela`: o alvo REARMA quando o usuario
    desmarca e remarca, entao uma criatura viva ha uma hora pode gravar ancora
    nova e reiniciar a conta.

    A DATA SO APARECE QUANDO NAO E A DE HOJE, na forma curta. Custa 6
    caracteres e, com respawn de 8h, a ancora cai no dia anterior em cerca de
    um terco das mensagens — entao nem "sempre" nem "nunca" servem. Sem data,
    uma ancora de 23:00 lida as 07:00 vira um horario no FUTURO e a conta deixa
    de ser conferivel, que e a unica funcao do numero. Com data em toda
    mensagem, dois tercos delas pagam 6 caracteres por "hoje". O formato e o
    mesmo `dd/mm HH:MM` de `_quando`, porque duas formas de data no mesmo bloco
    fariam o usuario decidir, a cada linha, qual campo e o dia.
    """
    instante = ancora.instante
    hora = f"{instante.hour:02d}:{instante.minute:02d}"
    data = f"{instante.day:02d}/{instante.month:02d}"

    if referencia is not None:
        quando = hora if instante.date() == referencia.date() else f"{data} {hora}"
        if ancora.origem is not OrigemDoAviso.ALVO:
            return f"Nascimento {quando}", ""
        return f"Alvo {quando}", ", pode adiantar"

    if ancora.origem is not OrigemDoAviso.ALVO:
        return (
            f"desde o nascimento que o servidor anunciou as {hora} de {data}",
            "",
        )
    return (
        f"desde que virou seu alvo as {hora} de {data}",
        " Alvo nao prova nascimento, pode estar adiantado.",
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

    A REGRA DO SERVIDOR SAIU DA LINHA EM 2026-09-02, a pedido do usuario. Ela
    dizia, POR BOSS: "A regra sao 8h fixas mais ate 2h aleatorias, entao o
    nascimento cai em algum ponto entre os dois horarios acima." A linha
    inteira tinha 349 caracteres e a resposta do `/tiat` com dois bosses
    passava de 700, lida no celular no meio de um farm.

    A REGRA CONTINUA VERDADE, e continua sendo `respawn_horas_min` mais a
    DIFERENCA para `respawn_horas_max`, lidas do `[[boss]]`. O que mudou e o
    julgamento de que ela precisava ser DITA. Ela existia para explicar por que
    ha dois horarios em vez de um, mas a linha ja diz "a janela abre em X e o
    limite passa em Y": um intervalo com dois extremos ja E a resposta, e a
    segunda metade da frase ("o nascimento cai em algum ponto entre os dois
    horarios acima") so repetia com outras palavras o que "janela" significa.
    A primeira metade era aritmetica de servidor, que ninguem refaz no celular.

    O QUE A LINHA CARREGA HOJE, e cada item e acionavel: o NOME do boss (D-14,
    decide para onde a party se desloca), os DOIS horarios, o TEMPO VERBAL de
    cada um (uma janela que ja abriu e um fato diferente de uma que vai abrir),
    e a CITACAO DA ANCORA com a ressalva do alvo quando ela cabe. Nada mais.

    A RESSALVA DO ALVO NAO E ENFEITE e nao pode sumir na proxima limpeza:
    ancora de alvo pode estar adiantada, e o usuario decide sair de casa com
    base nesse numero. Ela vem de `_citacao_da_ancora` — mas o "entao
    encurta-la de um lado encurta dos dois", escrito aqui em 2026-09-02, CAIU
    em 2026-09-03. A funcao continua sendo uma so, e agora tem DUAS FORMAS:
    esta linha usa a longa (teto 160, ela e pedida por quem quer o detalhe) e
    as quatro frases do grupo usam a curta (teto 80, elas chegam a todo mundo
    todo dia). Encurtar a do grupo NAO encurtou esta, de proposito, e o que
    impede as duas de divergirem no que IMPORTA e as duas formas morarem no
    mesmo corpo de funcao, uma embaixo da outra.

    A LINHA SEM ANCORA CONTINUA SEM NUMERO NENHUM (T-02-13), e por isso ela
    tambem nunca teve a regra: a regra e feita de dois numeros, e afrouxar o
    portao de digitos para ela caber abriria a porta pela qual um horario
    inventado entraria depois.
    """
    linhas: list[str] = []
    for boss in bosses:
        ancora = ancoras.get(apelido_do_evento(boss.nome))
        if ancora is None:
            linhas.append(
                f"{boss.nome}: sem nascimento visto, nao tenho janela "
                f"para prever."
            )
            continue

        abre = ancora.instante + timedelta(hours=boss.respawn_horas_min)
        limite = ancora.instante + timedelta(hours=boss.respawn_horas_max)
        desde, ressalva = _citacao_da_ancora(ancora)
        linhas.append(
            f"{boss.nome}: janela "
            f"{'abre' if agora < abre else 'abriu'} {_quando(abre)}, "
            f"limite {'passa' if agora < limite else 'passou'} "
            f"{_quando(limite)}, {desde}.{ressalva}"
        )
    return linhas


def _quando(instante: datetime) -> str:
    """O MESMO formato de `_anunciar_proximo` (`%d/%m %H:%M`).

    Duas formas de data no mesmo bloco de arranque fariam o usuario decidir, a
    cada linha, qual campo e o dia.
    """
    return (
        f"{instante.day:02d}/{instante.month:02d} "
        f"{instante.hour:02d}:{instante.minute:02d}"
    )
