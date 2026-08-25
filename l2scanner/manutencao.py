"""O aviso de manutencao do servidor, lido do banner que o jogo mostra na tela.

POR QUE ESTE ARQUIVO EXISTE
===========================

Em 2026-08-24 o scanner passou 90 s e depois 5 min repetindo "sem visao da
party" sem nunca dizer o motivo. O motivo era o servidor em manutencao. A
Fase 5 nasceu disso — e ela sabe reconhecer o servidor DEPOIS que ele cai.

Esta e a outra metade. O jogo ANUNCIA a manutencao com 40 minutos de
antecedencia, em texto, na tela, por cima da party window:

    Server Maintence 40 minutes 26 seconds Please avoid entering instance

O scanner atravessava esse anuncio inteiro sem ver. Quem esta AFK farmando
perde o loot do chao, perde o buff e cai no meio de uma instance por falta de
um aviso que estava escrito na tela o tempo todo.

A DISCIPLINA DESTE MODULO, com o mesmo peso do proposito
========================================================

Tempo por PARAMETRO, sem relogio proprio. Sem disco. Sem OCR. Sem pixels.
E a mesma disciplina de `agenda.py` e `loot.py`, e pela mesma razao: testar
"faltam 5 minutos" nao pode exigir esperar 35 minutos, e testar "o aviso sai
mesmo com o OCR cego" nao pode exigir uma manutencao real.

IMPORTS PROIBIDOS AQUI: `winrt`, `cv2` e `l2scanner.ocr`. Nao e preferencia —
`tests/test_manutencao.py` le a arvore de imports com `ast` e falha se algum
aparecer. Uma regra de arquitetura que so vive num comentario e uma regra que
ja quebrou.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

# Cadencia do OCR. O MESMO numero e o MESMO motivo do
# `SEGUNDOS_ENTRE_BUSCAS_DO_DIALOGO`: uma busca cara rodando a cada tick comeria
# o CPU do scanner inteiro, e ela nao precisa dessa frequencia — um banner de
# manutencao nao pisca, ele aparece e FICA (D-06).
SEGUNDOS_ENTRE_LEITURAS = 5.0

# Quanto dois momentos implicados podem diferir e ainda serem "a mesma
# manutencao". Folgada de proposito contra o atraso da leitura e do parse;
# minuscula contra um digito comido pelo OCR — 4 minutos contra 40 minutos sao
# 36 minutos de diferenca, mil vezes esta tolerancia (D-05).
TOLERANCIA_DO_CONSENSO = timedelta(seconds=60)

# Quando sai o SEGUNDO aviso (GOAL-02).
ANTECEDENCIA = timedelta(minutes=5)

# Quanto tempo a ancora sobrevive ao proprio momento antes de ser esquecida.
# Sem a expiracao o vigia carregaria para sempre um horario que ja passou, e a
# manutencao do dia seguinte nunca seria anunciada (D-10).
FOLGA_APOS_A_MANUTENCAO = timedelta(minutes=10)

# A raiz que cobre `maintence` (o typo do jogo) e `maintenance` de uma vez.
_RAIZ = "mainten"

_HORAS = re.compile(r"(\d+)\s*hour")
_MINUTOS = re.compile(r"(\d+)\s*minut")
_SEGUNDOS = re.compile(r"(\d+)\s*second")

# Leitura acima disto e lixo do OCR, nao manutencao. O jogo anuncia com dezenas
# de minutos, nunca com dias.
_TETO = timedelta(hours=24)

# As confusoes classicas do OCR, aplicadas SO em contexto de digito.
_TROCAS = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "S": "5", "s": "5"})


def eh_banner_de_manutencao(texto: str | None) -> bool:
    """A primeira das TRES portas contra inventar uma manutencao.

    As outras duas sao exigir uma duracao interpretavel (`interpretar_banner`)
    e exigir o consenso de duas leituras (`VigiaDeManutencao`). Nenhuma delas
    sozinha basta, e e por isso que sao tres.

    A raiz `mainten` sozinha basta porque ela e o token mais RARO da tela: nem
    o chat, nem um nome de personagem, nem o nome de um item a produzem por
    acidente. Exigir tambem a palavra `server` seria PIOR, nao melhor — um
    `5erver` mal lido pelo OCR derrubaria a deteccao inteira, e `server`
    aparece em frases que nao sao o banner (`the server will restart in a few
    minutes`, dos prints do usuario) sem trazer nenhum poder de discriminacao.
    """
    if not texto:
        return False
    return _RAIZ in texto.lower()


def _normalizar_digitos(texto: str) -> str:
    """O/l/I/S viram digito SO em token que ja tem um digito de verdade.

    A exigencia do digito real e o ponto inteiro: sem ela `SO` viraria `50` e
    qualquer palavra da tela poderia virar numero. Com ela, `seconds` sai
    INTACTA — que e o requisito literal de D-03, porque e a palavra que da
    sentido ao numero ao lado.
    """
    return " ".join(
        token.translate(_TROCAS) if any(c.isdigit() for c in token) else token
        for token in texto.split()
    )


def interpretar_banner(texto: str | None) -> timedelta | None:
    """Quanto falta, segundo o texto do banner. None quando nao da para dizer.

    Procura PREFIXOS (`minut`, `second`, `hour`) e nao palavras inteiras, para
    tolerar plural e o truncamento que o OCR faz no fim da palavra.

    `timedelta(0)` e resultado LEGITIMO e nao pode virar None: os prints do
    usuario tem `00 minutes 00 seconds`, que significa "agora".
    """
    if not texto:
        return None

    normalizado = _normalizar_digitos(texto).lower()

    componentes = (
        (_HORAS, 3600),
        (_MINUTOS, 60),
        (_SEGUNDOS, 1),
    )
    total = 0
    achou = False
    for padrao, fator in componentes:
        casou = padrao.search(normalizado)
        if casou:
            achou = True
            total += int(casou.group(1)) * fator

    if not achou:
        return None

    duracao = timedelta(seconds=total)
    if duracao > _TETO:
        return None  # leitura de lixo; melhor calar do que anunciar besteira
    return duracao


def _plural(quantidade: int, singular: str, plural: str) -> str:
    return f"{quantidade} {singular if quantidade == 1 else plural}"


def descrever_duracao(d: timedelta) -> str:
    """O tempo COMO ESTA NA TELA (GOAL-01) — entao nao arredonda.

    Arredondar "40 minutos e 26 segundos" para "40 minutos" pareceria mais
    limpo e seria pior: o usuario pediu o tempo que o jogo mostrou, e e por
    esse numero que ele vai conferir se o scanner leu certo.
    """
    total = max(0, int(d.total_seconds()))
    horas, resto = divmod(total, 3600)
    minutos, segundos = divmod(resto, 60)

    partes = []
    if horas:
        partes.append(_plural(horas, "hora", "horas"))
    if minutos:
        partes.append(_plural(minutos, "minuto", "minutos"))
    if segundos:
        partes.append(_plural(segundos, "segundo", "segundos"))

    if not partes:
        return "menos de 1 segundo"
    if len(partes) == 1:
        return partes[0]
    return ", ".join(partes[:-1]) + " e " + partes[-1]


class TipoDeAvisoDeManutencao(Enum):
    """Os dois avisos. OS VALORES ENTRAM NA CHAVE do marcador — nao os mude.

    Mudar um valor faz um aviso ja enviado voltar a parecer novo, e a party
    recebe em dobro. E a mesma razao de `Aviso.chave` da agenda ser
    estruturada e nunca o texto da mensagem.
    """

    ANUNCIADA = "anunciada"
    FALTAM5 = "faltam5"


def chave_do_marcador(momento: datetime, tipo: TipoDeAvisoDeManutencao) -> str:
    """Identidade duravel do aviso, derivada do MOMENTO DA MANUTENCAO.

    A DATA VEM NA FRENTE porque o `RegistroEmDisco.podar` faz
    `date.fromisoformat(nome.split("_", 1)[0])` e da `continue` quando levanta.
    Sem o prefixo, o marcador nunca seria apagado e a pasta cresceria para
    sempre — devagar, mas para sempre.

    Derivar do momento da MANUTENCAO, e nao do momento do aviso, e o que faz as
    DUAS instancias do usuario (Yazalaque e Faerlina) convergirem para a mesma
    chave e o grupo receber uma mensagem so.

    ARESTA ACEITA: as duas instancias podem implicar momentos separados por
    ~1 s e, se esse instante cair em cima de um `:30`, cada uma arredonda para
    um lado e o grupo recebe em dobro. O `RegistroEmDisco` ja declara a mesma
    preferencia ("preferir o aviso duplicado ao aviso perdido"), e aqui o aviso
    perdido e uma manutencao que ninguem soube.
    """
    arredondado = (momento + timedelta(seconds=30)).replace(second=0, microsecond=0)
    return (
        f"{arredondado.date().isoformat()}"
        f"_manutencao-{arredondado.hour:02d}{arredondado.minute:02d}"
        f"_{tipo.value}"
    )


@dataclass(frozen=True)
class AvisoDeManutencao:
    """Um aviso que venceu. Estruturado, nunca so texto.

    Pelo mesmo motivo de `ResultadoDoTick.despachos` existir: teste afirma
    estrutura, nao redacao.
    """

    tipo: TipoDeAvisoDeManutencao
    momento: datetime  # quando o servidor cai
    texto: str

    @property
    def chave(self) -> str:
        return chave_do_marcador(self.momento, self.tipo)


def texto_de_anuncio(momento: datetime, duracao: timedelta) -> str:
    """Carrega OS DOIS fatos, e nao um: a duracao lida e a hora de parede.

    A duracao e o que o usuario pediu ("o tempo como esta na tela"). A hora de
    parede e o que permite a party se organizar — quem le "40 minutos" cinco
    minutos depois da mensagem chegar precisa saber que sao 40 minutos a partir
    de OUTRO instante.

    A instrucao de nao entrar em instance e o que o proprio banner diz, e e o
    conselho mais caro de ignorar: cair no meio de uma instance custa a entrada.
    """
    return (
        f"MANUTENCAO DO SERVIDOR em {descrever_duracao(duracao)} "
        f"(as {momento.strftime('%H:%M')}). Nao entre em instance."
    )


class VigiaDeManutencao:
    """Le o banner com CADENCIA e ancora a manutencao no RELOGIO.

    A ANCORA (D-04) e o link central deste recurso. Numa leitura bem sucedida,
    `momento_da_manutencao = agora + tempo_lido`. Dai em diante os avisos saem
    do relogio, NUNCA da tela. E o que faz o aviso de 5 minutos sobreviver ao
    banner sumir, ao jogo ficar coberto e ao OCR passar a devolver None.

    O CONSENSO (D-05) e o que impede a ancora de nascer errada: sao precisas
    DUAS leituras cujos momentos implicados batam dentro da tolerancia. Sem
    ele, um digito comido pelo OCR anunciaria "faltam 4 minutos" quando faltam
    40 — e a party largaria o farm por nada.

    `ler_texto` entra por PARAMETRO e e obrigatorio. E o que mantem este modulo
    sem OCR nenhum e o que permite os testes injetarem texto no Python da
    suite, que nao tem as bindings do WinRT.
    """

    def __init__(
        self,
        ler_texto,
        segundos_entre_leituras: float = SEGUNDOS_ENTRE_LEITURAS,
        tolerancia: timedelta = TOLERANCIA_DO_CONSENSO,
    ) -> None:
        self._ler_texto = ler_texto
        self._intervalo = segundos_entre_leituras
        self._tolerancia = tolerancia

        self._ultima_leitura: datetime | None = None
        self._ancora: datetime | None = None
        self._candidata: datetime | None = None
        self._duracao_confirmada: timedelta | None = None
        self._emitidos: set[TipoDeAvisoDeManutencao] = set()

    @property
    def momento(self) -> datetime | None:
        """O instante em que o servidor cai, ou None se nada esta ancorado."""
        return self._ancora

    def avaliar(self, obter_pixels, agora: datetime) -> list[AvisoDeManutencao]:
        """`obter_pixels` so e chamado quando a cadencia vence.

        Passar um CHAMAVEL em vez dos pixels e o que faz a cadencia valer
        alguma coisa: nos ticks sem busca o recorte nem chega a ser tocado.
        """
        vencido = (
            self._ultima_leitura is None
            or (agora - self._ultima_leitura).total_seconds() >= self._intervalo
        )
        if vencido:
            self._ultima_leitura = agora
            pixels = obter_pixels()
            if pixels is not None:
                texto = self._ler(pixels)
                if eh_banner_de_manutencao(texto):
                    duracao = interpretar_banner(texto)
                    if duracao is not None:
                        self._registrar(agora + duracao, duracao)

        return self._avisos_devidos(agora)

    def _ler(self, pixels) -> str | None:
        """Cinto E suspensorio: `ocr.ler_texto` ja promete nao levantar.

        A promessa nao basta porque este vigia roda DENTRO do tick de captura,
        e uma excecao aqui pararia o scanner de olhar a party — o unico defeito
        que este projeto trata como inaceitavel.
        """
        try:
            return self._ler_texto(pixels)
        except Exception:
            return None

    def _registrar(self, implicado: datetime, duracao: timedelta) -> None:
        """Aplica o consenso de D-05 a uma leitura bem sucedida."""
        if self._candidata is not None and self._bate(implicado, self._candidata):
            self._ancora = implicado
            self._duracao_confirmada = duracao
            self._candidata = None
        else:
            self._candidata = implicado

    def _bate(self, a: datetime, b: datetime) -> bool:
        return abs(a - b) <= self._tolerancia

    def _avisos_devidos(self, agora: datetime) -> list[AvisoDeManutencao]:
        """Montado a partir da ANCORA, e nao da leitura — sempre.

        Este passo roda TAMBEM nos ticks em que nao houve leitura nenhuma. E
        ele, e so ele, que faz o aviso sobreviver a cegueira (D-10).
        """
        if self._ancora is None:
            return []

        avisos: list[AvisoDeManutencao] = []

        if TipoDeAvisoDeManutencao.ANUNCIADA not in self._emitidos:
            duracao = self._duracao_confirmada
            if duracao is None:
                duracao = max(timedelta(0), self._ancora - agora)
            self._emitidos.add(TipoDeAvisoDeManutencao.ANUNCIADA)
            avisos.append(
                AvisoDeManutencao(
                    tipo=TipoDeAvisoDeManutencao.ANUNCIADA,
                    momento=self._ancora,
                    texto=texto_de_anuncio(self._ancora, duracao),
                )
            )

        return avisos
