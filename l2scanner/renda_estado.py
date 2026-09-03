"""A camada de VALOR da cegueira: "nao vejo" contra "vejo e nao mudou".

O QUE ESTE MODULO E
====================
O classificador que responde, a cada tique, **qual das quatro coisas esta
acontecendo** -- e ele nao detecta nenhuma delas de novo. Os quatro sinais
crus chegam prontos da casca (CTX-4):

    `SaudeDoFrame`          -> `frames.py:132-150`, hash blake2b, 30 iguais
    `EstadoDoCliente`       -> `cliente.py:242-276`, titulo + dialogo modal
    `esta_minimizada`       -> `captura_janela.py:203-204`, `IsIconic`
    `CamposDaRenda`         -> `renda_leitura.ler_os_tres_campos`, Fase 1

Quatro rodadas de correcao no v1 estao atras dos tres primeiros. Esta fase
**classifica e nomeia**; reescrever qualquer um deles seria passivo.

A UNICA PECA GENUINAMENTE NOVA E A STALENESS DE **VALOR**
==========================================================
Os tres detectores de staleness que a arvore ja tinha sao os tres de PIXEL --
`frames._ClassificadorDeSaude` (30 frames byte-identicos),
`recaptura.FonteRecuperavel` (3 congelados seguidos) e `mercado_pagina`
(3 janelas identicas). **Nenhum deles compara o VALOR LIDO.** `RastreioDoValor`
e essa camada, e ela vive acima da de pixel: uma tela de jogo viva sempre muda
alguma coisa (grama, nuvem, animacao), entao o frame passa como saudavel
enquanto o usuario esta parado ha uma hora.

OS QUATRO ESTADOS, E O QUINTO CASO QUE FAZ O TERCEIRO FUNCIONAR
================================================================
| estado             | o que ele diz                                | o disco |
|--------------------|----------------------------------------------|---------|
| LENDO              | frame bom, EXP lido, valor mudou             | grava   |
| PARADO             | frame bom, EXP lido, bit-identico ha T       | grava   |
| SEM LEITURA        | frame bom, os campos RECUSARAM               | grava   |
| SEM LEITURA (EXP)  | frame bom, o EXP recusou (os outros nao)     | grava   |
| PAUSADO            | o frame nao mostra o jogo                    | NAO     |

**So PAUSADO suspende a gravacao (CEGO-01).** Renda zero e um fato legitimo
sobre o farm e cegueira e uma falha da medicao; se "parado" virasse recusa, o
arquivo perderia justamente a evidencia de que o usuario ficou uma hora parado
-- e a taxa da sessao mentiria PARA CIMA, porque o denominador encolheria. O
tamanho da mentira esta medido: 226 mil contra 466 mil adena/h.

**"PAUSADO" e a palavra da TELA e "cego" e a palavra do CODIGO.** O
`ROADMAP.md:441` e o `REQUIREMENTS.md:307` dizem "pausa declarada" e "pausado",
e e o que o usuario le.

O QUE ESTE MODULO NAO FAZ, E AS QUATRO SAO TENTACAO
====================================================
1. **Nao le relogio.** O carimbo entra por parametro em tudo. Sem isso,
   `PARADO ha 4min` so seria demonstravel dormindo quatro minutos.
2. **Nao chama `fonte.capturar()` nem `estado_do_cliente()`.** A coleta e da
   casca -- *"logica que decide alguma coisa nao pode viver num modulo que so
   um jogo aberto consegue exercitar"* (`captura_janela.py:470-473`).
3. **Nao imprime.** Ele devolve texto; quem imprime e o laco, com `log.info`,
   e assim a mesma string vai para o console E para o `scanner.log`.
4. **Nao tem estado de MODULO.** O rastreio e do OBJETO; o portao de ausencia
   de memoria da Fase 1 varre este arquivo e nao acha `global` nem literal
   mutavel de nivel de modulo -- e e por isso que os mapas de texto sao
   `MappingProxyType` e nao `dict` nu.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from .cliente import EstadoDoCliente
from .frames import SaudeDoFrame
from .renda_console import ROTULO_NA_LINHA, duracao_curta
from .renda_leitura import CAMPO_DO_EXP, RecusaDaRenda

__all__ = (
    "EstadoDaRenda",
    "RastreioDoValor",
    "VeredictoDoRastreio",
    "VisaoDaRenda",
    "classificar_a_visao",
    "motivo_da_pausa",
)


class EstadoDaRenda(Enum):
    """O que o tique E, do ponto de vista de quem le a tela as 4 da manha."""

    LENDO = "lendo"
    PARADO = "parado"
    SEM_LEITURA = "sem_leitura"
    PAUSADO = "pausado"


# ---------------------------------------------------------------------------
# OS MOTIVOS -- e sao SEIS de pausa porque o CONSERTO DO USUARIO e outro
# ---------------------------------------------------------------------------
#
# A regra e a que `__main__.py:840-849` ja escreveu com todas as letras:
# *"SEM VISAO" e verdade mas nao ajuda; "JOGO CAIU - TELA DE LOGIN" diz o que
# fazer a respeito*. Minimizado pede restaurar a janela; tela de login pede
# logar de novo; congelado pede olhar se o jogo travou; frame preto pede
# conferir se o monitor nao apagou. Fundir dois deles faria dois consertos
# diferentes virarem a mesma mensagem -- a mesma razao pela qual `campo-vazio`
# e `gramatica` sao motivos separados na Fase 1.

MOTIVO_DA_JANELA_MINIMIZADA = "minimizada"
MOTIVO_DA_TELA_DE_LOGIN = "tela-de-login"
MOTIVO_DA_DESCONEXAO = "desconectado"
MOTIVO_DA_JANELA_SUMIDA = "janela-sumiu"
MOTIVO_DO_FRAME_PRETO = "frame-preto"
MOTIVO_DO_CONGELAMENTO = "congelado"

# OS DOIS MOTIVOS DE SEM LEITURA. Eles compartilham o valor de enum -- mesmo
# efeito no disco, mesmo tipo de conserto -- e o que muda e o campo nomeado no
# texto. Um enum proprio para o segundo faria a soma dos contadores da sessao
# ter cinco parcelas para tres tipos de conserto.
MOTIVO_DOS_CAMPOS_SEM_LEITURA = "campos-sem-leitura"
MOTIVO_DO_EXP_SEM_LEITURA = "exp-sem-leitura"


# ---------------------------------------------------------------------------
# OS TEXTOS -- o CURTO rola por tique, o ALTO sai UMA vez por transicao
# ---------------------------------------------------------------------------
#
# SAO DOIS PORQUE A LARGURA E MEDIDA E NAO OPINIAO. A linha do tique tem
# orcamento de 76 colunas (`LARGURA_DO_AVISO`) e o prefixo com os valores reais
# do usuario -- `renda | nivel 68 | EXP 48,0075% | adena 23.986.985 | ` -- come
# 53 delas. Sobram 23, e a frase acionavel de minimizado tem 160 caracteres:
# ela sairia truncada em `PAUSADO: A JANELA DO JOGO E~`, cortando exatamente a
# parte acionavel, que e a razao de ela existir.
#
# Entao o texto CURTO rola em toda linha de tique (o usuario ve o estado o
# tempo todo) e o texto ALTO sai UMA vez, na transicao, num bloco de
# `console.moldurar` que tem as 76 colunas so para ele. E o mesmo latch de
# `mercado_pagina.py:796-814`: *"congelamento e um ESTADO, e nao um evento. Uma
# linha de log por tick, para sempre, nao acrescenta forense nenhuma -- so
# afoga o resto do log."*

TEXTO_CURTO_DA_PAUSA = MappingProxyType(
    {
        MOTIVO_DA_JANELA_MINIMIZADA: "PAUSADO: minimizada",
        MOTIVO_DA_TELA_DE_LOGIN: "PAUSADO: tela de login",
        MOTIVO_DA_DESCONEXAO: "PAUSADO: desconectado",
        MOTIVO_DA_JANELA_SUMIDA: "PAUSADO: janela sumiu",
        MOTIVO_DO_FRAME_PRETO: "PAUSADO: frame preto",
        MOTIVO_DO_CONGELAMENTO: "PAUSADO: congelado",
    }
)

AVISO_DA_PAUSA = MappingProxyType(
    {
        MOTIVO_DA_JANELA_MINIMIZADA: (
            "PAUSADO: A JANELA DO JOGO ESTA MINIMIZADA. Restaure a janela - "
            "ela pode ficar COBERTA por outra (isso e medido e funciona), mas "
            "minimizada ela para de produzir frame e nenhuma API do Windows "
            "contorna isso. Nada sera gravado em .renda/ ate ela voltar."
        ),
        MOTIVO_DA_TELA_DE_LOGIN: (
            "PAUSADO: O JOGO CAIU - TELA DE LOGIN. Logue de novo com este "
            "personagem. Nada sera gravado em .renda/ ate a barra de EXP "
            "voltar a tela."
        ),
        MOTIVO_DA_DESCONEXAO: (
            "PAUSADO: O JOGO CAIU - DESCONECTADO DO SERVIDOR. O dialogo de "
            "desconexao esta na tela: clique nele e logue de novo. Nada sera "
            "gravado em .renda/ ate la."
        ),
        MOTIVO_DA_JANELA_SUMIDA: (
            "PAUSADO: NAO SEI O QUE ESTA NA TELA - o titulo da janela nao "
            "responde mais. Ela foi fechada, ou o handle morreu. O scanner NAO "
            "vai supor o que aconteceu; confira se o cliente ainda esta "
            "aberto. Nada sera gravado em .renda/ ate ele responder."
        ),
        MOTIVO_DO_FRAME_PRETO: (
            "PAUSADO: A CAPTURA VEIO PRETA (brilho medio abaixo do minimo). O "
            "monitor apagou, a tela bloqueou, ou a janela parou de desenhar. "
            "Nada sera gravado em .renda/ ate a imagem voltar."
        ),
        MOTIVO_DO_CONGELAMENTO: (
            "PAUSADO: A IMAGEM ESTA CONGELADA - 30 frames byte-identicos "
            "seguidos. Sao DUAS causas com consertos diferentes: a sessao de "
            "captura morreu com o jogo vivo (medido em 2026-09-01, e o scanner "
            "tenta religar sozinho), ou o jogo parou de renderizar. Se o jogo "
            "esta vivo na tela e isto persiste, quem parou foi a captura. Nada "
            "sera gravado em .renda/ ate a imagem mudar."
        ),
    }
)

AVISO_DOS_CAMPOS_SEM_LEITURA = (
    "SEM LEITURA: nenhum dos tres campos virou numero, e o frame esta "
    "SAUDAVEL - o scanner esta vendo o jogo e nao esta conseguindo ler. A "
    "linha CONTINUA sendo gravada, com o motivo. Se isto persistir, o suspeito "
    "e o RETANGULO e nao o brilho: medido em 2026-09-03, o painel de status "
    "moveu ~90 px e os retangulos gravados passaram a apontar para grama pura. "
    "Rode `calibrar-renda.bat` para este personagem."
)

AVISO_DO_EXP_SEM_LEITURA = (
    "SEM LEITURA (EXP): o EXP nao esta saindo. Ele e o campo sobre o qual "
    "'parado' e uma AFIRMACAO - enquanto ele nao voltar, o painel NAO SABE se "
    "voce esta parado, e dizer PARADO ali seria afirmar sobre um numero que "
    "nao foi lido. A linha CONTINUA sendo gravada e a serie de staleness fica "
    "CONGELADA: quando o EXP voltar, o `PARADO ha ...` retoma de onde parou."
)

AVISO_DO_PARADO = (
    "PARADO: o EXP esta bit-identico ha tempo demais - voce parou de matar. A "
    "gravacao CONTINUA, e de proposito: renda zero e um fato sobre o farm e "
    "nao uma falha da medicao, e suprimir estas linhas faria a taxa da sessao "
    "mentir PARA CIMA (medido: 226 mil contra 466 mil adena/h)."
)

AVISO_DA_VOLTA = (
    "LENDO: o EXP voltou a mudar e as linhas continuam indo para .renda/."
)

# O PREFIXO DE CADA ESTADO NA LINHA DO TIQUE, e a distincao e por PREFIXO e nao
# por cor. `console._pintar` desliga a cor quando `isatty()` e falso -- que e o
# caso do `caplog`, de um pipe e do redirecionamento para `scanner.log`, que e
# exatamente onde o usuario vai olhar de manha. Um estado que so se
# distinguisse por cor sumiria justamente ali.
PREFIXO_DO_PARADO = "PARADO"
PREFIXO_DA_SEM_LEITURA = "SEM LEITURA"
PREFIXO_DA_PAUSA = "PAUSADO"


@dataclass(frozen=True)
class VeredictoDoRastreio:
    """O que a serie de valores diz AGORA. Nunca um booleano nu.

    `segundos` e `amostras` viajam JUNTO com `parado` pela mesma disciplina de
    `n` e recencia que o `--mercado` aplica a todo numero que vai a tela: o
    tempo e o que o usuario quer saber e a contagem e a letra do CEGO-02
    ("bit-identicos por N amostras"). Devolver so `parado` obrigaria quem exibe
    a abrir o objeto por dentro.
    """

    parado: bool
    segundos: float
    amostras: int


@dataclass(frozen=True)
class VisaoDaRenda:
    """O veredito de UM tique: o nome, o motivo e os dois textos.

    `texto` E `None` NO CASO LENDO, E ISSO E DESENHO E NAO OMISSAO. A
    `linha_do_tique` do `03-01` calcula o proprio estado quando `estado=None`, e
    o que ela calcula e `LENDO` OU `nivel: campo-vazio` -- com o MOTIVO da
    recusa. Nos 79% de tiques em que o nivel recusa com o EXP subindo, o estado
    e LENDO e o motivo daquela recusa e a unica pista de conserto na tela;
    sobrescreve-lo com a palavra `LENDO` trocaria a pista por uma palavra que
    nao ajuda.

    `aviso` e o texto ALTO, e ele sai UMA vez por transicao. Ver o comentario
    dos dois textos, acima: a frase acionavel nao cabe na linha do tique e
    truncada ela perde exatamente a parte acionavel.
    """

    estado: EstadoDaRenda
    motivo: str | None
    texto: str | None
    aviso: str


class RastreioDoValor:
    """O ultimo EXP lido, quando ele mudou, e quantas amostras se passaram.

    OBJETO MUTADO NO LUGAR, no molde de `ContagemDaRenda`: o estado e do
    OBJETO e nunca do modulo, e duas instancias nao se enxergam.

    AS TRES REGRAS, E A TERCEIRA E A QUE O ACHADO 5 OBRIGA
    ======================================================
    1. **O campo e o EXP**, e nao a adena nem o nivel. Medido na Fase 1: o EXP
       recusa em **0%** dos tiques, a adena em **21%** e o nivel em **79%**.
       Medir staleness no campo que recusa em quatro de cada cinco tiques seria
       medir a recusa e chamar de parado.
    2. **`valor_atual == valor_anterior` e a comparacao inteira.** O EXP viaja
       em decimos de milesimo de ponto percentual e o degrau de UM abate mede
       **10 unidades** (censo de 55 Hz, `renda_ponte.py:33-35`). "Bit-identico"
       e literal, barato, e nao precisa de tolerancia -- uma tolerancia aqui
       esconderia justamente o abate solitario que prova que o usuario nao
       parou.
    3. **`valor is None` -- a recusa -- NAO incrementa e NAO zera a serie.** Ela
       e contada num terceiro campo. As tres saidas sao tres fatos: "mudou",
       "nao mudou" e "nao sei". Se a recusa zerasse a serie, uma unica recusa
       apagaria dez minutos de evidencia de parado; se incrementasse, a recusa
       viraria parado -- que e o defeito nomeado no Achado 5.

    O LIMIAR ENTRA SOMENTE-NOMEADO E SEM VALOR DE FABRICA. Ele e uma
    propriedade do DETECTOR, mora como constante nomeada no laco (o molde
    literal de `FRAMES_IDENTICOS_PARA_CONGELADO = 30`, que e o detector irmao),
    e este modulo nao sabe que `config.toml` existe.
    """

    def __init__(self) -> None:
        # O ultimo valor LIDO. `None` significa "ainda nao li nenhum", e nunca
        # "o ultimo foi recusado" -- a recusa nao encosta neste campo.
        self.valor: int | None = None
        # O carimbo em que o valor mudou pela ultima vez.
        self.desde: float | None = None
        # O carimbo da ultima leitura CONSUMIDA. A recusa nao o move, e e por
        # isso que a serie congela em vez de crescer durante uma sequencia de
        # recusas.
        self.ate: float | None = None
        self.amostras = 0
        self.sem_leitura_seguidas = 0

    def observar(
        self,
        valor: int | None,
        *,
        carimbo: float,
        segundos_para_parado: float,
    ) -> VeredictoDoRastreio:
        """Uma amostra do EXP -- ou a ausencia dela -- e o veredito de agora."""
        if valor is None:
            # REGRA 3: congela. Nao zera (uma recusa nao e prova de que o
            # usuario voltou a matar) e nao avanca (nao ha valor novo com que
            # comparar).
            self.sem_leitura_seguidas += 1
            return self._veredito(segundos_para_parado)

        self.sem_leitura_seguidas = 0
        inteiro = int(valor)
        if self.valor is None or inteiro != self.valor:
            self.valor = inteiro
            self.desde = float(carimbo)
            self.amostras = 1
        else:
            self.amostras += 1
        self.ate = float(carimbo)
        return self._veredito(segundos_para_parado)

    def _veredito(self, segundos_para_parado: float) -> VeredictoDoRastreio:
        if self.desde is None or self.ate is None:
            return VeredictoDoRastreio(parado=False, segundos=0.0, amostras=0)

        segundos = self.ate - self.desde
        # DUAS AMOSTRAS E O PISO, e ele nao e defensivo: "bit-identicos por N
        # amostras" so e afirmavel a partir de duas. Com uma so, `segundos` e
        # zero e um limiar de zero declararia PARADO na PRIMEIRA leitura da
        # sessao.
        #
        # E O `segundos` NEGATIVO NAO VIRA PARADO: o carimbo andando para tras
        # e o dual boot do usuario, e ele ja tem nome proprio na Fase 2
        # (`DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS`). Ele nao pode virar uma
        # afirmacao sobre o farm.
        parado = self.amostras >= 2 and segundos >= float(segundos_para_parado)
        return VeredictoDoRastreio(
            parado=parado, segundos=segundos, amostras=self.amostras
        )


def motivo_da_pausa(
    *,
    saude: SaudeDoFrame,
    estado_do_cliente: EstadoDoCliente | None,
    minimizada: bool,
) -> str | None:
    """O motivo da cegueira, ou `None` se o frame mostra o jogo.

    A ORDEM E DO SINAL MAIS ESPECIFICO PARA O MAIS GENERICO, porque um sinal
    generico chegando primeiro rouba a palavra do especifico:

    1. **`minimizada`** vem primeiro. E o unico estado que o `PROJECT.md`
       declara impossivel de contornar, e o unico que o usuario causou DE
       PROPOSITO. Sem esta precedencia o painel esperaria os 30 frames de
       `FRAMES_IDENTICOS_PARA_CONGELADO` -- ~30 s a 1 Hz -- para dizer
       "congelado" sobre uma janela que o usuario acabou de minimizar (C-7).
    2. **`estado_do_cliente`**: login, desconectado e "a janela sumiu". Os
       tres sao imediatos e os tres tem conserto proprio.
    3. **`saude`**: frame preto e congelado, que sao a REDE embaixo dos dois
       primeiros.

    `estado_do_cliente=None` E `DESCONHECIDO` SAO FATOS DIFERENTES.
    `DESCONHECIDO` e "eu perguntei e o cliente nao respondeu" -- a janela sumiu,
    e isso pausa. `None` e "eu nao perguntei": a fonte nem tem o metodo (o caso
    do `MssSource`, protegido por `hasattr` em `sessao.py:468`). Colapsar os
    dois pausaria a sessao inteira de qualquer fonte que nao fosse
    `JanelaSource`.

    "COBERTO POR OUTRA JANELA" NAO ESTA AQUI, E ISSO E MEDICAO. Toda a medicao
    de campo da Fase 1 foi feita com o jogo atras do navegador, nas duas
    instancias: o `mss` devolvia a tela do browser e a `JanelaSource` leu o jogo
    normalmente (`01-MEDICOES-DE-CAMPO.md:1-6`).
    """
    if minimizada:
        return MOTIVO_DA_JANELA_MINIMIZADA

    if estado_do_cliente is EstadoDoCliente.TELA_DE_LOGIN:
        return MOTIVO_DA_TELA_DE_LOGIN
    if estado_do_cliente is EstadoDoCliente.DESCONECTADO:
        return MOTIVO_DA_DESCONEXAO
    if estado_do_cliente is EstadoDoCliente.DESCONHECIDO:
        return MOTIVO_DA_JANELA_SUMIDA

    if saude is SaudeDoFrame.FALHA_DE_CAPTURA:
        return MOTIVO_DO_FRAME_PRETO
    if saude is SaudeDoFrame.CONGELADO:
        return MOTIVO_DO_CONGELAMENTO

    return None


def _valor_do_exp(campos) -> int | None:
    """O EXP como inteiro, ou `None` quando o campo recusou."""
    if isinstance(campos.exp, RecusaDaRenda):
        return None
    return int(campos.exp.valor)


def texto_do_parado(veredito: VeredictoDoRastreio) -> str:
    """`PARADO ha 4min n=247` -- o tempo primeiro, a contagem depois.

    OS DOIS NUMEROS, e a ordem e por importancia porque a linha PODE truncar:
    o tempo e o que o usuario quer saber as 4 da manha, e a contagem e a letra
    do CEGO-02. Se a linha estourar as 76 colunas, quem se perde e a contagem e
    nunca o tempo.

    A GRAFIA DA DURACAO E `duracao_curta`, a mesma do bloco e do resumo. Uma
    segunda gramatica de duracao aqui (`4min12` em vez de `4min`) faria a mesma
    grandeza aparecer escrita de dois jeitos na MESMA tela.
    """
    return (
        f"{PREFIXO_DO_PARADO} ha {duracao_curta(veredito.segundos)} "
        f"n={veredito.amostras}"
    )


def classificar_a_visao(
    *,
    saude: SaudeDoFrame,
    estado_do_cliente: EstadoDoCliente | None,
    minimizada: bool,
    campos,
    rastreio: RastreioDoValor,
    carimbo: float,
    segundos_para_parado: float,
) -> VisaoDaRenda:
    """Os quatro sinais crus entram, um estado NOMEADO sai.

    A OBSERVACAO DO RASTREIO MORA AQUI DENTRO, E ISSO E O PONTO. A casca nao
    pode ser quem decide se a amostra deste tique entra na serie, porque a
    resposta depende da cegueira -- e um frame CONGELADO devolve os MESMOS
    pixels, logo os mesmos numeros. Uma casca que observasse antes de perguntar
    alimentaria a serie durante os 33 minutos de captura morta e sairia da
    cegueira anunciando `PARADO ha 33min` sobre um tempo em que ninguem estava
    vendo nada. A decisao mora no puro; a coleta mora na casca.

    OS QUATRO PASSOS, e o terceiro e o QUINTO CASO:

    1. cego? -> PAUSADO, com o motivo. **A serie nao e tocada.**
    2. nenhum campo saiu -> SEM LEITURA, nomeando os campos.
    3. o EXP recusou (os outros tendo saido ou nao) -> SEM LEITURA (EXP), com a
       serie CONGELADA. Este ramo vem ANTES do veredito do rastreio porque e
       justamente o caso em que o rastreio nao tem o que dizer: sem ele, quem
       estava PARADO continua sendo reportado PARADO com o EXP ja nao saindo, e
       quem nunca teve serie cai em LENDO para sempre.
    4. o EXP saiu -> o veredito do rastreio, LENDO ou PARADO.
    """
    motivo = motivo_da_pausa(
        saude=saude,
        estado_do_cliente=estado_do_cliente,
        minimizada=minimizada,
    )
    if motivo is not None:
        return VisaoDaRenda(
            estado=EstadoDaRenda.PAUSADO,
            motivo=motivo,
            texto=TEXTO_CURTO_DA_PAUSA[motivo],
            aviso=AVISO_DA_PAUSA[motivo],
        )

    valor = _valor_do_exp(campos)
    veredito = rastreio.observar(
        valor, carimbo=carimbo, segundos_para_parado=segundos_para_parado
    )

    por_campo = campos.por_campo
    recusados = [
        campo
        for campo, resultado in por_campo.items()
        if isinstance(resultado, RecusaDaRenda)
    ]
    if len(recusados) == len(por_campo):
        nomes = ", ".join(ROTULO_NA_LINHA[campo] for campo in recusados)
        return VisaoDaRenda(
            estado=EstadoDaRenda.SEM_LEITURA,
            motivo=MOTIVO_DOS_CAMPOS_SEM_LEITURA,
            texto=f"{PREFIXO_DA_SEM_LEITURA} ({nomes})",
            aviso=AVISO_DOS_CAMPOS_SEM_LEITURA,
        )

    if valor is None:
        return VisaoDaRenda(
            estado=EstadoDaRenda.SEM_LEITURA,
            motivo=MOTIVO_DO_EXP_SEM_LEITURA,
            texto=(
                f"{PREFIXO_DA_SEM_LEITURA} ({ROTULO_NA_LINHA[CAMPO_DO_EXP]})"
            ),
            aviso=AVISO_DO_EXP_SEM_LEITURA,
        )

    if veredito.parado:
        return VisaoDaRenda(
            estado=EstadoDaRenda.PARADO,
            motivo=None,
            texto=texto_do_parado(veredito),
            aviso=AVISO_DO_PARADO,
        )

    return VisaoDaRenda(
        estado=EstadoDaRenda.LENDO,
        motivo=None,
        texto=None,
        aviso=AVISO_DA_VOLTA,
    )
