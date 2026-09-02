"""O calibrador da RENDA: tres retangulos e tres pisos de brilho, por personagem.

Ele e irmao curto de `calibrar.calibrar_tiat` — carrega o `calibration.json`
inteiro, muta SO o que e dele, e reemite tudo. A ordem daquelas sete etapas nao
e estilo: e o que faz a nao-destruicao ser ESTRUTURAL em vez de prometida.

O INCIDENTE QUE ESTA ORDEM IMPEDE, e ele nao e hipotetico: em 2026-08-30 uma
rodada de `calibrar.bat` apagou treze moldes de glifo cortados a mao, tres
ancoras e a grade de negociacao, porque aquele caminho montava uma `Calibracao`
DO ZERO e o `salvar` gravava o objeto inteiro. Era load-mutate-save **sem o
load**. O `calibration.json` e gitignored, entao nao existe `git checkout` que
traga nada de volta — o resgate daquele dia foi manual, e o arquivo dele ainda
esta na raiz deste repositorio com o nome que o denuncia.

A CALIBRACAO DA RENDA E POR PERSONAGEM, E ISSO MUDA O QUE "SO O QUE E DELE"
QUER DIZER
===========================================================================
Ate agora, nao destruir significava nao apagar as FEATURES vizinhas. Agora
significa tambem nao apagar o PERSONAGEM vizinho, que mora dentro da mesma
chave `renda_por_personagem` e que nenhum teste de superficie deste repositorio
enxerga: um calibrador que remontasse aquele dicionario a partir do personagem
que acabou de calibrar apagaria o outro com o campo continuando presente, a
versao continuando 2 e o `carregar` continuando feliz.

E o mesmo incidente uma camada abaixo, com a mesma forma: um escritor montando
do zero o que devia ter carregado. Por isso a mutacao aqui e por **copia com
substituicao da chave do personagem**, e nunca por reconstrucao do dicionario.

Medido (M-F): as duas instancias poem a janela de status em `246,736` e em
`236,750` — 14 px na vertical e 10 na horizontal. Ler uma com o retangulo da
outra nao devolve campo vazio que alguem nota: devolve `349` ou `112`, numeros
desenhados ao lado do nivel que passam por qualquer validacao sem reclamar. Por
isso este calibrador **nao comeca sem saber de quem e a tela**.

SUGERIR E CONFIRMADO POR UM HUMANO; CAIR E SILENCIOSO
=====================================================
A sugestao de cada retangulo vem do DISCO — da entrada do proprio personagem, e
so na falta dela da entrada de um vizinho, sempre anunciada como tal. As duas
coisas parecem a mesma e nao sao: a sugestao do vizinho aparece desenhada na
tela e o usuario confirma com o olho; a LEITURA cair no vizinho e o que o
`renda_modo` proibe, porque ninguem ve acontecer.

E e por isso que nenhum retangulo deste arquivo e um literal: a primeira
calibracao de um personagem nao tem sugestao e o usuario arrasta; da segunda em
diante a sugestao e o que ele mesmo marcou. Os numeros do spike ficam onde ja
estao — na fixtura de calibracao dos testes e no `calibration.json` do usuario.

O DESTINO DE ESCRITA E UNICO, DE PROPOSITO
===========================================
`ARQUIVO_CALIBRACAO` e o unico lugar onde este modulo grava. `--partir-de` le
de outro arquivo e por isso e legal SOMENTE junto de `--so-medir`: um
calibrador que le de um arquivo e escreve em outro fabrica uma calibracao que o
scanner nunca ve, e o sintoma e "calibrei e o scanner nao ve" — que o usuario
nao tem como ligar na causa.

A `barra_direita` E VARRIDA POR FORMA, E A PENEIRA E IMPORTADA
===============================================================
A adena trocou de leitor (LEIT-09): ela e classificada pelo veredicto de GLIFO,
pela peneira de forma `renda_leitura._glifos_do_numero`, e nao pelos quatro
desfechos do cruzamento de escalas. Este modulo IMPORTA aquela peneira e nunca
escreve uma segunda: duas peneiras seriam duas formas, e os moldes do cortador
seriam cortados de um conjunto de corridas e lidos de outro. Pior: as larguras
deste projeto vivem em DUAS convencoes (M-P) — `larguras_de_molde` mede
`fim - inicio` (digito 4/5/6, virgula 1, icones 14/15) e o
`01-MEDICOES-DE-CAMPO.md` relata `fim - inicio + 1` (5/6/7, 2, 15/16) —, e uma
peneira escrita contra a convencao errada recusa o digito mais largo e aceita
icone estreito, calada nos dois sentidos.

A varredura da adena roda INTEIRA SEM MOLDE NENHUM, que e o estado da primeira
rodada de todo usuario: sem moldes a forma decide sozinha, `ler_glifos` nao e
chamada, e a ORDEM DE OPERACAO sai no terminal — ver `ordem_de_operacao`. Com
moldes, o valor lido aparece como coluna INFORMATIVA e o dentro/fora da banda
nao muda.
"""

from __future__ import annotations

# DPI PRIMEIRO, e ele chega pelo import de `calibrar`, que o executa no import
# do modulo. A ferramenta e o scanner precisam concordar sobre o que e um pixel:
# sem isso as coordenadas gravadas aqui nao significam nada la.
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .calibracao import (
    PISO_DE_BRILHO_MAXIMO_DA_RENDA,
    PISO_DE_BRILHO_MINIMO_DA_RENDA,
    REGIOES_DA_RENDA,
    Calibracao,
    CalibracaoInvalida,
)
from .calibrar import (
    _gravar_conferencia,
    _selecionar_regiao,
    listar_janelas_do_jogo,
)
from .cliente import nome_do_personagem
from .frames import Regiao
from .mercado_leitura import (
    ler_glifos,
    mascara_de_numero,
    numero_valido,
    segmentar_glifos_no_brilho,
)
from .mercado_visao import glifos_de_calibracao
from .ocr import ler_texto, ler_texto_ampliado
from .renda_leitura import (
    CORRIDAS_MINIMAS_DE_UM_NUMERO,
    LIMITE_VEIO_DOS_MOLDES,
    MOTIVO_DA_DISCORDANCIA,
    MOTIVO_DA_GRAMATICA,
    MOTIVO_DO_CAMPO_VAZIO,
    GlifosDoNumero,
    RecusaDaRenda,
    ValorDaRenda,
    _cruzar_as_escalas,
    _glifos_do_numero,
    entre_delimitadores,
    limite_de_arranque,
    resolver_o_limite_de_glifo,
)

RAIZ = Path(__file__).resolve().parent.parent

# O UNICO DESTINO DE ESCRITA DESTE MODULO, no idioma de `calibrar.py`. Um
# argumento que redirecionasse onde a calibracao aterrissa e armadilha de
# suporte de primeira ordem. A suite chega aqui por monkeypatch desta
# constante, que e como os arquivos de nao-destruicao precedentes ja fazem.
ARQUIVO_CALIBRACAO = RAIZ / "calibration.json"

SAIDA_OK = 0
SAIDA_OPERACIONAL = 1

# Os nomes que o usuario le, por sub-chave. OS DOIS PRIMEIROS MENTEM —
# `barra_esquerda` e o EXP e `barra_direita` e a ADENA —, e a mentira fica
# ESCRITA em vez de consertada em silencio: quem renomear renomeia as duas
# (aqui, no `calibracao.py`, no `renda_leitura.py` e no `renda_modo.py`), num
# commit proprio.
ROTULO_DA_REGIAO = {
    "barra_esquerda": "EXP (barra inferior esquerda)",
    "barra_direita": "ADENA (barra inferior direita)",
    "nivel": "NIVEL (a janela de status)",
}

INSTRUCAO_DA_REGIAO = {
    "barra_esquerda": "Arraste sobre o campo do EXP, na barra inferior.",
    "barra_direita": (
        "Arraste sobre o campo da ADENA. Termine ANTES do icone seguinte: "
        "medido, um recorte que pega o icone estica a faixa de glifo e trava "
        "o cortador de moldes."
    ),
    "nivel": "Arraste sobre o numero do NIVEL, na janela de status.",
}

# As cores da imagem de conferencia, uma por regiao, em BGR.
COR_DA_REGIAO = {
    "barra_esquerda": (0, 255, 255),
    "barra_direita": (0, 255, 0),
    "nivel": (255, 128, 0),
}

# Os nomes das DUAS escalas de OCR que a producao cruza. Eles viajam na saida
# da varredura porque uma banda sustentada por UMA escala so e uma calibracao
# com uma guarda a menos, e o usuario tem direito de saber disso ANTES de
# gravar — nao depois, no meio do farm.
ESCALA_DE_DETECCAO = "2x"
ESCALA_DE_CONFERENCIA = "3x"
ESCALAS_DE_PRODUCAO = (ESCALA_DE_DETECCAO, ESCALA_DE_CONFERENCIA)


# ---------------------------------------------------------------------------
# A GRADE DE PISOS -- E O PASSO E 5, QUE E UMA CORRECAO MEDIDA
# ---------------------------------------------------------------------------
#
# A varredura de campo que produziu a tabela de bandas do M-E andou de DEZ em
# DEZ, e por isso PULOU O 155. Refeita de 5 em 5 (M-G), a Yazalaque le a adena
# corretamente em `vmin=155` nas duas escalas — a linha "110 (3x), 150 (2x)"
# daquela tabela e uma leitura ERRADA (`106.020` contra a verdade `1.696.020`)
# que passou por certa porque o passo grosso nunca experimentou o vizinho certo.
#
# UM PASSO GROSSO NAO ERRA PARA O LADO SEGURO. Ele produz uma conclusao errada
# com a aparencia de uma medicao — e aquela conclusao entrou num documento, e do
# documento entrou num plano. Quem for otimizar o tempo desta varredura vai
# olhar o passo primeiro: este paragrafo e para essa pessoa.
PASSO_DA_GRADE_DE_PISOS = 5

# Uma banda de largura 1 ou 2 nao e margem, e sorte -- e o aviso existe por
# MEDICAO. O M-E mediu a banda util da adena da Faerlina com largura 1: um
# unico `vmin` funcionava e os vizinhos nao. O motivo estava visivel no
# recorte, e ele nao e do codigo: a barra e semitransparente e naquele instante
# o fundo atras da adena era grama clara em vez do fundo escuro do spike. A
# BANDA UTIL MUDA COM O CENARIO, e uma calibracao de largura 1 vai quebrar
# quando o usuario mudar de lugar de farm.
#
# E O CASO QUE OBRIGOU ESTE AVISO A EXISTIR JA MORREU, E ISSO FICA ESCRITO
# PORQUE E UM RESULTADO. Aquela banda de largura 1 era da adena NO CAMINHO DE
# OCR. Medido depois (M-J), a segmentacao por GLIFO do mesmo campo e estavel de
# 180 a 190 nas duas instancias — banda larga. A troca de leitor consertou a
# fragilidade que o aviso media. O aviso fica inteiro e obrigatorio, porque ele
# agora guarda o EXP e o nivel; o que mudou e que o exemplo canonico dele
# deixou de ser a adena. Um aviso cujo unico caso morreu e um aviso que alguem
# apaga em seis meses; um aviso com a historia escrita fica.
LARGURA_MAXIMA_DE_BANDA_FRAGIL = 2

# A partir de que fracao da largura do ICONE uma corrida do MEIO deixa de poder
# ser digito. Ela existe para o AVISO de recorte contaminado, e nunca para
# decidir leitura -- quem decide forma e a peneira do `01-05`.
#
# MEDIDO nas quatro fixturas de campo, na convencao EXCLUSIVA: os icones de
# ponta valem 14 e 15, e o digito mais largo desta fonte vale 6 (o `4`, o `7` e
# o `9`). Metade do icone e 7,0-7,5, entao o digito mais largo passa com folga
# de um pixel e o `18` que o retangulo refutado do M-N produzia no meio nao
# passa. A folga e pequena de proposito: um aviso que so dispara no caso
# extremo deixa passar o caso que de fato aconteceu em campo.
FRACAO_DO_ICONE_QUE_AINDA_E_DIGITO = 0.5


def grade_de_pisos(primeiro: int, ultimo: int) -> tuple[int, ...]:
    """Os pisos a experimentar, de `PASSO_DA_GRADE_DE_PISOS` em passo.

    Fechada dos dois lados quando `ultimo` cai na grade — a varredura de campo
    reporta bandas por extremos inclusivos, e uma grade meio-aberta faria a
    saida do calibrador discordar do documento que a justifica.
    """
    return tuple(range(int(primeiro), int(ultimo) + 1, PASSO_DA_GRADE_DE_PISOS))


# ---------------------------------------------------------------------------
# OS TRES VEREDICTOS -- e sao TRES porque os consertos sao tres
# ---------------------------------------------------------------------------
#
# "Nao leu" e "leu errado" apontam para consertos DIFERENTES: campo vazio
# aponta para o retangulo, ou para o jogo estar em outra tela; leitura que nao
# respeita a gramatica aponta para o piso de brilho. Um calibrador que dissesse
# apenas "leu alguma coisa" aceitaria de bom grado o piso do meio da curva do
# roadmap — aquele em que a tela diz um numero e a ferramenta le `6b`.
#
# O LIMITE HONESTO DESTA GUARDA, medido pela pesquisa desta fase (Armadilha 5):
# ela pega o `6b` porque o caractere errado NAO E DIGITO. Ela NAO pegaria a
# substituicao de um digito por outro — `66` lido onde a tela diz `68` passa
# inteiro. E exatamente por isso que a decisao final e do olho do usuario, e por
# isso que a tira de pixels de conferencia existe.
VEREDICTO_VAZIO = "vazio"
VEREDICTO_NAO_E_NUMERO = "nao-e-numero"
VEREDICTO_NUMERO = "numero"

VEREDICTOS = (VEREDICTO_VAZIO, VEREDICTO_NAO_E_NUMERO, VEREDICTO_NUMERO)


def inteiro_pela_gramatica_do_jogo(texto: str | None) -> int | None:
    """`66` -> 66, `6b` -> None, `13,160,684` -> 13160684.

    A gramatica e `mercado_leitura.numero_valido`, IMPORTADA e nao reescrita.
    Uma segunda expressao regular de numero neste arquivo mediria a ferramenta
    e nao o produto: o piso calibrado descreveria uma gramatica que a producao
    nao aplica.
    """
    if not numero_valido(texto):
        return None
    return int(str(texto).replace(",", ""))


@dataclass(frozen=True)
class Leitura:
    """O que UMA escala viu num piso, ja classificado."""

    escala: str
    texto: str | None
    veredicto: str
    valor: int | None


def classificar_a_leitura(texto: str | None, *, gramatica) -> str:
    """VAZIO, NAO E NUMERO ou NUMERO. `gramatica` chega por parametro.

    `gramatica` nao tem valor de fabrica de proposito: o EXP tem a gramatica de
    quatro casas com sinal de porcentagem (`renda_leitura.decimos_de_milesimo`)
    e o nivel tem a de inteiro do jogo, e um default aqui escolheria uma das
    duas por omissao — que e o mesmo defeito do piso de brilho com default, uma
    camada acima.
    """
    if gramatica(texto) is not None:
        return VEREDICTO_NUMERO
    if not (texto or "").strip():
        return VEREDICTO_VAZIO
    return VEREDICTO_NAO_E_NUMERO


@dataclass(frozen=True)
class LinhaDaVarredura:
    """Uma linha da curva: um piso, o que cada escala viu, e o desfecho.

    NENHUMA LEITURA SAI SEM O PISO AO LADO. Uma linha sem o valor que a produziu
    e inutil para o usuario, que esta comparando a saida com a tela do jogo.
    """

    piso: int
    leituras: tuple[Leitura, ...]
    aceito: bool
    desfecho: str
    valor: int | None
    escalas_que_sustentaram: tuple[str, ...]

    def como_texto(self) -> str:
        cruas = "  ".join(
            f"{leitura.escala}={entre_delimitadores(leitura.texto)}"
            for leitura in self.leituras
        )
        valor = "-" if self.valor is None else str(self.valor)
        return (
            f"  piso {self.piso:>3}  {'ACEITO' if self.aceito else 'fora  '}  "
            f"{self.desfecho:<28}  valor={valor:<12} {cruas}"
        )


def linha_da_varredura(
    piso: int, textos: dict[str, str | None], *, campo: str, gramatica
) -> LinhaDaVarredura:
    """Uma linha da curva, com o desfecho vindo de `_cruzar_as_escalas`.

    A DECISAO E A DE PRODUCAO, E NAO UMA COMPARACAO ESCRITA AQUI. Uma segunda
    particao de desfechos neste arquivo mediria a ferramenta e nao o produto: o
    piso calibrado descreveria uma regra que o leitor nao aplica, e a diferenca
    apareceria em campo como "calibrei e nao le".

    ABSTENCAO NAO E DISCORDANCIA, e a regra chega de graca por vir de la. E ela
    e o que salva um campo inteiro: medido (M-D), o nivel da Faerlina so sai na
    escala 3x, com a 2x devolvendo vazio em TODA a banda util. Com a regra
    antiga — "as duas leituras tem que dar o mesmo numero" — a banda util
    daquele campo seria VAZIA e o calibrador nao teria piso nenhum para gravar.
    """
    leituras = tuple(
        Leitura(
            escala=escala,
            texto=texto,
            veredicto=classificar_a_leitura(texto, gramatica=gramatica),
            valor=gramatica(texto),
        )
        for escala, texto in textos.items()
    )
    resultado = _cruzar_as_escalas(
        campo, [(leitura.texto, leitura.valor) for leitura in leituras]
    )
    sustentaram = tuple(
        leitura.escala for leitura in leituras if leitura.valor is not None
    )
    if isinstance(resultado, ValorDaRenda):
        desfecho = (
            f"aceito por {len(sustentaram)} escala(s)"
            if len(sustentaram) < len(leituras)
            else "aceito pelas duas escalas"
        )
        return LinhaDaVarredura(
            piso=int(piso),
            leituras=leituras,
            aceito=True,
            desfecho=desfecho,
            valor=resultado.valor,
            escalas_que_sustentaram=sustentaram,
        )
    return LinhaDaVarredura(
        piso=int(piso),
        leituras=leituras,
        aceito=False,
        desfecho=_DESFECHO_DA_RECUSA[resultado.motivo],
        valor=None,
        escalas_que_sustentaram=(),
    )


# Os motivos de recusa de `_cruzar_as_escalas` traduzidos para a linha da tela.
# Eles sao um MAPA e nao uma segunda particao: as chaves vem das constantes do
# modulo puro, entao um desfecho novo la aparece aqui como KeyError alto e nao
# como linha silenciosamente rotulada errado.
_DESFECHO_DA_RECUSA = {
    MOTIVO_DO_CAMPO_VAZIO: "campo vazio (o piso apagou tudo)",
    MOTIVO_DA_GRAMATICA: "NAO E NUMERO (leu, e a forma nao bate)",
    MOTIVO_DA_DISCORDANCIA: "as escalas leram numeros DIFERENTES",
}


def varrer_o_piso(
    recorte: np.ndarray, pisos, *, campo: str, gramatica, ler_escalas=None
) -> list[LinhaDaVarredura]:
    """Uma linha por piso, com as DUAS escalas lidas SEMPRE.

    Nao uma leitura so, e nao um curto-circuito na escala barata: o que o
    calibrador mede tem de ser o que o leitor vai fazer, senao o piso calibrado
    descreve outra coisa. A mascara e `mercado_leitura.mascara_de_numero`, a
    MESMA que a producao aplica — se fossem duas, o piso calibrado nao
    descreveria a leitura.

    `ler_escalas` existe para que os testes puros desta varredura rodem SEM o
    motor de OCR e sem disco, montando os textos a mao. Ele nao e um atalho: e
    a fronteira que separa o laco de OCR das funcoes puras, e e ela que faz
    `tests/test_calibrar_renda.py` rodar em qualquer clone.
    """
    if ler_escalas is None:
        ler_escalas = _ler_as_duas_escalas
    return [
        linha_da_varredura(
            piso, ler_escalas(recorte, int(piso)), campo=campo, gramatica=gramatica
        )
        for piso in pisos
    ]


def _ler_as_duas_escalas(recorte: np.ndarray, piso: int) -> dict[str, str | None]:
    """As duas escalas de producao sobre o recorte mascarado naquele piso.

    A mascara sai em 0/1 e o motor de OCR espera tinta visivel, entao ela vira
    0/255 — a mesma conversao de `renda_leitura.exp_da_barra`. Sem isso o
    recorte chega quase preto e as duas escalas abstem, o que seria uma recusa
    por campo vazio apontando para o lugar errado.
    """
    tinta = (mascara_de_numero(recorte, int(piso)) * 255).astype(np.uint8)
    return {
        ESCALA_DE_DETECCAO: ler_texto(tinta),
        ESCALA_DE_CONFERENCIA: ler_texto_ampliado(tinta),
    }


@dataclass(frozen=True)
class BandaUtil:
    """O maior trecho CONTIGUO em que o cruzamento aceitou, com a largura.

    CONTIGUO, e nao "todos os pisos que funcionaram": dois pisos que funcionam
    com um buraco no meio nao sao uma banda, sao coincidencia — e o centro
    entre eles cai dentro do buraco.

    A LARGURA E PRODUTO DE PRIMEIRA CLASSE e vai gravada junto do piso no
    `calibration.json`. Ver `LARGURA_MAXIMA_DE_BANDA_FRAGIL` para a medicao que
    obrigou o aviso, e para o registro de que o caso canonico dela foi resolvido
    por outro caminho.

    A FUNCAO `intersecao_das_bandas` NAO EXISTE, E A REFUTACAO FICA ESCRITA EM
    VEZ DE A FUNCAO SUMIR SEM EXPLICACAO. Ela era o ramo que o item M9 do
    `01-01` obrigava: as duas metades da barra dividiam UM campo de calibracao,
    e o M9 mostrava uma metade lendo num piso em que a outra nao lia; o
    calibrador recusaria gravar e diria que "as duas metades precisam de pisos
    separados, e isso e mudanca de codigo". O achado M-E transformou a hipotese
    em fato e a mudanca de codigo foi feita: a banda do nivel (190-220) e a da
    adena (150) NAO TEM INTERSECAO NENHUMA — nao e "as vezes nao se cruzam", e
    "nao se cruzam". O esquema carrega UM PISO POR REGIAO, e a situacao que
    aquele ramo detectava deixou de ser possivel. Nao existe, e nao pode voltar
    a existir, funcao neste arquivo que combine bandas de regioes diferentes.
    """

    pisos: tuple[int, ...]
    sustentada_por: tuple[str, ...]

    @property
    def largura(self) -> int:
        return len(self.pisos)

    @property
    def vazia(self) -> bool:
        return not self.pisos

    @property
    def fragil(self) -> bool:
        return 0 < self.largura <= LARGURA_MAXIMA_DE_BANDA_FRAGIL

    @property
    def de_uma_escala_so(self) -> bool:
        """A banda inteira foi sustentada por UMA escala.

        E uma calibracao com uma guarda a menos: naquele campo o cruzamento
        deixa de pegar substituicao de digito, e o unico verificador que resta e
        o olho de quem compara o terminal com o monitor. O usuario tem direito
        de saber disso antes de aceitar.
        """
        return bool(self.pisos) and len(set(self.sustentada_por)) == 1


def resumir_a_banda_util(linhas) -> BandaUtil:
    """O maior trecho contiguo de linhas ACEITAS. Empate fica com a primeira.

    Empate com a primeira, e nao com a ultima, porque a saida ja imprime a
    curva inteira: quando duas bandas empatam em largura o usuario ve as duas e
    decide, e uma regra estavel vale mais que uma regra esperta.
    """
    melhor: list[LinhaDaVarredura] = []
    corrente: list[LinhaDaVarredura] = []
    for linha in linhas:
        if linha.aceito:
            corrente.append(linha)
            if len(corrente) > len(melhor):
                melhor = list(corrente)
        else:
            corrente = []
    return BandaUtil(
        pisos=tuple(linha.piso for linha in melhor),
        sustentada_por=tuple(
            escala for linha in melhor for escala in linha.escalas_que_sustentaram
        ),
    )


def escolher_o_piso(banda: BandaUtil) -> int | None:
    """O CENTRO da banda, e nunca o primeiro valor que leu.

    Um piso na borda da banda funciona hoje e esta a uma mudanca de gamma, de
    monitor ou de skin de cair fora dela. O centro e o unico ponto que tem folga
    dos dois lados.

    Em banda de largura par o centro escolhido e o superior — arbitrario, e
    declarado aqui em vez de deixado para quem for ler a divisao inteira.
    """
    if banda.vazia:
        return None
    return banda.pisos[banda.largura // 2]


def descrever_a_banda(campo: str, banda: BandaUtil) -> list[str]:
    """O que o usuario le sobre a banda, incluindo os avisos em voz alta."""
    if banda.vazia:
        return [
            f"{campo}: NENHUM piso da grade produziu leitura valida.",
            "  Ou o retangulo nao esta sobre o campo, ou o jogo esta em outra",
            "  tela. A curva acima diz qual dos dois: linhas 'campo vazio' em",
            "  todos os pisos apontam para o retangulo; linhas 'NAO E NUMERO'",
            "  apontam para o piso de brilho.",
        ]
    linhas = [
        f"{campo}: banda util {banda.pisos[0]}-{banda.pisos[-1]} "
        f"(largura {banda.largura}), piso escolhido {escolher_o_piso(banda)} "
        f"-- o CENTRO dela.",
    ]
    if banda.fragil:
        linhas += [
            f"  AVISO: banda de largura {banda.largura}. Isso nao e margem, e",
            "  sorte. Medido (M-E): a barra e semitransparente, e a banda util",
            "  MUDA COM O CENARIO -- com grama clara atras do campo o contraste",
            "  despenca. Esta calibracao vai quebrar quando voce mudar de lugar",
            "  de farm, e voce vai querer saber que foi isso, e nao um defeito",
            "  do scanner. Recalibre neste lugar novo quando acontecer.",
        ]
    if banda.de_uma_escala_so:
        linhas += [
            f"  AVISO: a banda inteira foi sustentada pela escala "
            f"{banda.sustentada_por[0]} sozinha (a outra abstem).",
            "  A leitura continua valendo -- abstencao nao e discordancia --, mas",
            "  o cruzamento entre escalas NAO esta pegando substituicao de",
            "  digito neste campo. Confira o numero com o olho na tela do jogo.",
        ]
    return linhas


def ordem_de_operacao() -> list[str]:
    """A ordem que o usuario nao tem como adivinhar, impressa no terminal dele.

    Ela mora aqui e nao so num plano porque quem roda o calibrador nao le
    plano nenhum: ele ve tres retangulos, um numero, e nao tem como saber que
    falta um passo entre esta rodada e a leitura da adena funcionando.
    """
    return [
        "A ORDEM DE OPERACAO desta fase, e ela tem TRES passos:",
        "  1) calibrar-renda.bat            marca os tres retangulos e grava",
        "                                   os tres pisos -- o do EXP e o do",
        "                                   nivel por OCR, o da adena por FORMA",
        "                                   de glifo, que roda sem molde (agora)",
        "  2) calibrar-renda-moldes.bat     corta os moldes da fonte da barra,",
        "                                   colhendo de --campo adena, --campo",
        "                                   bonus e --campo lcoin ate os onze",
        "                                   rotulos fecharem",
        "  3) calibrar-renda.bat --so-medir de novo, agora COM moldes: a banda",
        "                                   da adena sai confirmada e com o",
        "                                   valor ao lado da forma",
        "A adena NAO e lida por OCR (LEIT-09): ela e lida por GLIFO, e o piso",
        "dela sai do passo 2. Medido, os dois pisos nem se tocam -- 150 no OCR",
        "contra 180-190 no glifo.",
    ]


# ---------------------------------------------------------------------------
# A `barra_direita` E VARRIDA POR FORMA DE GLIFO, E NAO POR CRUZAMENTO DE OCR
# ---------------------------------------------------------------------------
#
# A adena trocou de leitor (LEIT-09): ela e classificada pela FORMA das
# corridas, pela peneira `renda_leitura._glifos_do_numero`, e nao pelos quatro
# desfechos do cruzamento de escalas. Varrer OCR num campo lido por glifo
# calibraria um piso que a producao nao usa — medido, os dois nem se tocam:
# 150 no OCR contra 180-190 no glifo.
#
# A PENEIRA E UMA SO NESTA FASE E ELA E IMPORTADA. Este arquivo nao a define
# em lugar nenhum, e ha um portao de teste sobre isso -- por ARVORE DE SINTAXE
# e por texto cru, porque o criterio do plano e um `grep`. Duas peneiras
# seriam duas formas, e os moldes do cortador seriam cortados de um conjunto de
# corridas e lidos de outro. Pior: as larguras deste projeto vivem em DUAS
# convencoes (M-P) — `larguras_de_molde` mede `fim - inicio` (EXCLUSIVA: digito
# 4/5/6, virgula 1, icones 14/15) e o `01-MEDICOES-DE-CAMPO.md` relata
# `fim - inicio + 1` (INCLUSIVA: 5/6/7, 2, 15/16) —, e uma peneira escrita
# contra a convencao errada recusa o digito mais largo e aceita icone estreito,
# calada nos dois sentidos.
REGIOES_VARRIDAS_POR_OCR = ("barra_esquerda", "nivel")
REGIAO_VARRIDA_POR_GLIFO = "barra_direita"

#: O metodo de cada regiao, escrito para SAIR NA TELA. Ele nao e enfeite: um
#: usuario que veja duas curvas parecidas e uma so palavra "piso" conclui que
#: os dois numeros sao comparaveis, e eles nao sao — um e de OCR e outro e de
#: glifo, e as bandas nem se tocam.
METODO_POR_GLIFO = "FORMA DAS CORRIDAS (glifo)"
METODO_POR_OCR = "cruzamento das escalas de OCR"


@dataclass(frozen=True)
class LinhaDaForma:
    """Uma linha da curva de GLIFO: um piso, a forma que saiu, e o veredicto.

    ELA NAO E `LinhaDaVarredura` COM OUTROS CAMPOS, E ISSO E DE PROPOSITO. As
    duas curvas medem coisas diferentes por caminhos diferentes: aquela cruza
    duas leituras de OCR, esta olha corridas. Fundi-las numa classe so obrigaria
    a inventar um "texto" para a forma e um "veredicto de forma" para o OCR, e o
    primeiro leitor a mexer nisso ia acabar comparando piso de OCR com piso de
    glifo — que e exatamente o erro que os dois pisos separados existem para
    impedir (M-E: as bandas nem se tocam).
    """

    piso: int
    aceito: bool
    desfecho: str
    larguras: tuple[int, ...]
    altura_da_faixa: int | None
    corridas_do_numero: int | None
    limite: int | None
    origem_do_limite: str
    arranque: int | None
    valor: str | None

    @property
    def escalas_que_sustentaram(self) -> tuple[str, ...]:
        """SEMPRE VAZIA, e a propriedade existe para dizer isso EM CODIGO.

        `resumir_a_banda_util` e a definicao unica de "banda contigua" desta
        casa, e ela e reusada aqui de proposito: duas definicoes de banda seriam
        duas regras de centro, e o piso gravado de um campo deixaria de ser
        comparavel com o do outro. O que ela le de cada linha e `aceito`, `piso`
        e as escalas que sustentaram — e nesta curva NAO HA ESCALA NENHUMA: quem
        aceita e a forma, sozinha.

        Devolver a tupla vazia nao e um buraco tapado: e a afirmacao de que o
        aviso "a banda inteira foi sustentada por uma escala so" NAO se aplica a
        este campo, porque aqui nao existe segunda opiniao a perder.
        """
        return ()

    @property
    def culpa_o_retangulo_sem_razao(self) -> bool:
        """A recusa acusa o retangulo, e o retangulo NAO e o culpado (M-U).

        SAO DUAS PERGUNTAS, E O CASO SO E DO M-U QUANDO AS DUAS RESPONDEM SIM.

        1. **O limite e ESTREITO DEMAIS para este recorte?** O limite dos
           moldes e a maior largura do conjunto JA CORTADO; o arranque e a maior
           largura do MIOLO DESTE recorte. O arranque maior que o limite quer
           dizer que ha aqui um glifo mais largo que qualquer molde gravado.
        2. **A corrida que sobra ainda PODE ser um digito?** Se ela tem largura
           de ICONE, o recorte pegou mesmo o campo vizinho — e ai a peneira esta
           certa e o conserto E o retangulo. E o caso do M-N, e ele nao pode ser
           confundido com este.

        A segunda pergunta usa `FRACAO_DO_ICONE_QUE_AINDA_E_DIGITO`, a mesma que
        o aviso de recorte contaminado usa, pela mesma medicao: os icones de
        ponta valem 14 e 15 na convencao exclusiva e o digito mais largo desta
        fonte vale 6, entao metade do icone (7,0-7,5) separa as duas populacoes
        com folga de um pixel. Sem esta segunda pergunta o aviso dispararia no
        caso M-N e mandaria o usuario deixar quieto um retangulo errado — que e
        o mesmo dano do M-U, virado do avesso.
        """
        if self.aceito or self.origem_do_limite != LIMITE_VEIO_DOS_MOLDES:
            return False
        if self.limite is None or self.arranque is None:
            return False
        if self.arranque <= self.limite:
            return False
        if len(self.larguras) < CORRIDAS_MINIMAS_DE_UM_NUMERO:
            return False
        icone = max(self.larguras[0], self.larguras[-1])
        return self.arranque <= icone * FRACAO_DO_ICONE_QUE_AINDA_E_DIGITO

    def como_texto(self) -> str:
        altura = "-" if self.altura_da_faixa is None else str(self.altura_da_faixa)
        corridas = (
            "-" if self.corridas_do_numero is None else str(self.corridas_do_numero)
        )
        valor = "(sem moldes)" if self.valor is None else self.valor
        return (
            f"  piso {self.piso:>3}  {'ACEITO' if self.aceito else 'fora  '}  "
            f"faixa={altura:<3} glifos={corridas:<3} limite="
            f"{self.limite}({self.origem_do_limite})  valor={valor:<12} "
            f"{self.desfecho}"
        )


def _medir_as_corridas(recorte: np.ndarray, piso: int):
    """`(mascara, faixa bruta, corridas)` naquele piso. So cv2, sem veredicto.

    A mascara e `mercado_leitura.mascara_de_numero` e a segmentacao e
    `segmentar_glifos_no_brilho` — as MESMAS que o cortador de moldes aplica.
    Se fossem duas, o piso calibrado aqui descreveria uma segmentacao e os
    moldes seriam cortados de outra.
    """
    return (
        mascara_de_numero(recorte, int(piso)),
        *segmentar_glifos_no_brilho(recorte, int(piso)),
    )


def _ler_o_valor_com_moldes(mascara, peneirado, conjunto: dict, limite: int):
    """A coluna INFORMATIVA: o que os moldes leem naquele piso. Ou `None`.

    Ela nao decide nada. O dentro/fora da banda ja foi decidido pela FORMA
    quando esta funcao e chamada, e tem de continuar assim: se a banda passasse
    a depender do valor, o piso gravado mudaria conforme o conjunto de moldes
    estivesse completo ou nao, e a calibracao dependeria de um artefato que ela
    mesma nao produz.
    """
    moldes = glifos_de_calibracao((conjunto or {}).get("moldes"))
    if not moldes:
        return None
    return ler_glifos(
        mascara,
        peneirado.faixa,
        list(peneirado.runs),
        moldes,
        float(conjunto["piso_de_leitura"]),
        float(conjunto["margem_de_leitura"]),
        largura_maxima_de_glifo=int(limite),
        folga_de_cola=conjunto.get("folga_de_cola"),
    )


def varrer_a_forma(
    recorte: np.ndarray,
    pisos,
    *,
    moldes_da_barra: dict | None = None,
    medir=None,
    ler_valor=None,
) -> list[LinhaDaForma]:
    """Uma linha por piso, classificada pela FORMA, com a peneira IMPORTADA.

    O QUE ESTA VARREDURA AFIRMA E O QUE ELA NAO AFIRMA. Ela afirma que aquele
    piso faz a barra SEGMENTAR como um numero: um run largo em cada ponta,
    nada largo no meio, e o miolo em larguras de digito e de virgula. Ela NAO
    afirma que o numero lido esta certo — ler o valor exige moldes, e a
    conferencia final e do olho do usuario contra a tela do jogo.

    E ELA RODA INTEIRA SEM MOLDE NENHUM, que e o estado da PRIMEIRA rodada de
    todo usuario. Este e o buraco de ordem que a suite sintetica nao pegaria:
    `ler_glifos` sem moldes nao le nada, e uma varredura acoplada ao VALOR
    devolveria banda vazia em todos os pisos na estreia — o usuario concluiria
    que a adena nao tem piso nenhum, enquanto os testes montados a mao
    continuariam verdes. Sem moldes, `ler_glifos` NAO E CHAMADA e a coluna de
    valor sai vazia; a forma decide sozinha.

    `medir` e `ler_valor` existem para que os testes puros rodem sem pixel e
    sem disco, no mesmo idioma de `ler_escalas` em `varrer_o_piso`. Eles nao
    sao atalhos de teste: sao a fronteira entre o laco que olha pixel e as
    funcoes que decidem, e e ela que faz este arquivo rodar em qualquer clone.
    """
    if medir is None:
        medir = _medir_as_corridas
    if ler_valor is None:
        ler_valor = _ler_o_valor_com_moldes

    conjunto = moldes_da_barra or None
    moldes = glifos_de_calibracao((conjunto or {}).get("moldes")) if conjunto else {}

    linhas: list[LinhaDaForma] = []
    for piso in pisos:
        mascara, faixa_bruta, corridas = medir(recorte, int(piso))
        corridas = [(int(inicio), int(fim)) for inicio, fim in (corridas or [])]
        larguras = tuple(fim - inicio for inicio, fim in corridas)
        limite, origem = resolver_o_limite_de_glifo(moldes, corridas)
        peneirado = _glifos_do_numero(mascara, faixa_bruta, corridas, limite=limite)

        if not isinstance(peneirado, GlifosDoNumero):
            linhas.append(
                LinhaDaForma(
                    piso=int(piso),
                    aceito=False,
                    desfecho=f"{peneirado.motivo}: {peneirado.detalhe}",
                    larguras=larguras,
                    altura_da_faixa=None,
                    corridas_do_numero=None,
                    limite=limite,
                    origem_do_limite=origem,
                    arranque=limite_de_arranque(corridas),
                    valor=None,
                )
            )
            continue

        # A LEITURA VEM DEPOIS DO VEREDICTO, E A ORDEM E O CONTRATO. A linha ja
        # esta ACEITA quando o valor e lido; nenhum ramo abaixo pode voltar
        # atras disso.
        valor = None
        if conjunto and moldes and limite is not None:
            valor = ler_valor(mascara, peneirado, conjunto, limite)

        linhas.append(
            LinhaDaForma(
                piso=int(piso),
                aceito=True,
                desfecho="segmenta como um numero",
                larguras=larguras,
                altura_da_faixa=peneirado.faixa[1] - peneirado.faixa[0],
                corridas_do_numero=len(peneirado.runs),
                limite=limite,
                origem_do_limite=origem,
                arranque=limite_de_arranque(corridas),
                valor=valor,
            )
        )
    return linhas


def avisar_sobre_o_limite_herdado(linhas) -> list[str]:
    """O achado M-U dito na tela, para a recusa nao culpar o inocente.

    A MENSAGEM DA PENEIRA CULPA O RETANGULO, e em campo o retangulo estava
    certo. Medido na rodada de moldes de 2026-09-02: cortando em ordem
    alfabetica, o primeiro recorte e `2.207.577`, so com digitos de largura 4;
    o limite trava em 4 e os tres recortes seguintes sao RECUSADOS porque `4`,
    `8` e `9` medem 5 e 6. A recusa dizia "o recorte pegou o campo vizinho
    junto" — e o que estava estreito era o limite herdado, nao o retangulo.

    Reconferido deste lado, com o limite preso em 4 sobre as CINCO fixturas de
    `barra_direita`: DUAS ficam com a banda inteiramente vazia, e as recusas
    dos pisos 181, 186 e 191 mandariam o usuario remarcar um retangulo correto.

    Um aviso que so repetisse a recusa da peneira seria pior que silencio: ele
    daria autoridade a atribuicao errada.
    """
    culpadas = [linha for linha in linhas if linha.culpa_o_retangulo_sem_razao]
    if not culpadas:
        return []
    primeira = culpadas[0]
    return [
        "  ATENCAO -- A RECUSA ACIMA PROVAVELMENTE CULPA O RETANGULO SEM RAZAO.",
        f"  O limite {primeira.limite} nao foi medido neste recorte: ele e a",
        "  MAIOR largura entre os moldes JA GRAVADOS. Neste recorte ha corrida",
        f"  de ate {primeira.arranque} colunas no meio -- mais larga que "
        f"qualquer molde",
        "  do conjunto. Isso quer dizer que FALTA MOLDE, e nao que o retangulo",
        "  esta errado (M-U, medido em 2026-09-02).",
        "  O conserto e cortar os moldes que faltam, COMECANDO PELO RECORTE MAIS",
        "  LARGO -- `calibrar-renda-moldes.bat`. Nao remarque o retangulo por",
        "  causa desta linha.",
    ]


def descrever_a_forma(campo: str, linhas) -> list[str]:
    """O que o usuario le sobre a curva de glifo, alem da banda.

    A ALTURA DE FAIXA SAI COM A CONVENCAO DECLARADA, e ela ja custou duas
    refutacoes a esta fase. A altura impressa e a PENEIRADA — a que sobra
    depois de os icones sairem —, medida como `fim - inicio` (EXCLUSIVA, a
    mesma de `larguras_de_molde`). Medida nas CINCO fixturas de campo, nos
    pisos da banda, ela vale **9** e nao muda; a INCLUSIVA (`+1`) vale 10, e e
    esse o "10" do M-K. A faixa BRUTA, com os dois icones dentro, vale 16
    exclusiva e 17 inclusiva — e esse e o "17" do M-I.

    Quem escrever guarda contra qualquer um desses quatro numeros tem de dizer
    em qual convencao esta: uma guarda calibrada contra 10 rodando na convencao
    do codigo recusaria TODO molde legitimo desta barra, e o modo de falha
    seria um cortador que roda, sai com codigo 0 e nunca corta nada.
    """
    alturas = sorted({linha.altura_da_faixa for linha in linhas if linha.aceito})
    if not alturas:
        return []
    return [
        f"  altura de faixa PENEIRADA nos pisos aceitos: {alturas} "
        f"(convencao EXCLUSIVA, `fim - inicio`;",
        f"  inclusive vale {[altura + 1 for altura in alturas]} -- e o `10` do "
        f"M-K esta nesta segunda).",
        f"  {campo} e classificado por {METODO_POR_GLIFO}, e nao por "
        f"{METODO_POR_OCR}.",
    ]


def _gramatica_da_regiao(regiao: str):
    """A gramatica de producao daquele campo, IMPORTADA e nunca reescrita.

    O EXP tem a sua — quatro casas decimais ancoradas dos dois lados, com o
    sinal de porcentagem —, e o nivel tem a de inteiro do jogo. Sao gramaticas
    diferentes porque sao campos diferentes, e uma so, parametrizada, teria de
    afrouxar a trava de um dos dois: e a trava que faz a leitura derrubar uma
    linha em vez de inventar um numero plausivel.
    """
    from .renda_leitura import decimos_de_milesimo

    if regiao == "barra_esquerda":
        return decimos_de_milesimo
    return inteiro_pela_gramatica_do_jogo


def _bloco_da_regiao(entrada: dict | None, regiao: str) -> dict | None:
    if not entrada:
        return None
    bloco = entrada.get(regiao)
    return bloco if isinstance(bloco, dict) else None


def _sugestao_de_retangulo(
    cal: Calibracao, personagem: str, regiao: str
) -> tuple[tuple[int, int, int, int] | None, str | None]:
    """O retangulo de partida daquela regiao, e DE QUEM ele veio.

    A sugestao pode vir do personagem vizinho; a LEITURA nunca pode. As duas
    parecem a mesma coisa e nao sao, e a diferenca e quem confirma: a sugestao
    aparece desenhada na tela e o usuario aperta ENTER ou arrasta por cima
    dela; cair no vizinho e silencioso. Medido, o vizinho e um bom chute — a
    barra inferior coincidiu nas duas instancias e a janela de status errou por
    14 px (M-F) —, e por isso ele e oferecido em vez de escondido. Mas ele e
    ANUNCIADO, sempre.
    """
    por_personagem = cal.renda_por_personagem or {}
    bloco = _bloco_da_regiao(por_personagem.get(personagem), regiao)
    if bloco is None:
        for vizinho, entrada in sorted(por_personagem.items()):
            if vizinho == personagem:
                continue
            bloco = _bloco_da_regiao(entrada, regiao)
            if bloco is not None:
                caixa = Regiao.de_dict(bloco["regiao"])
                return (
                    (caixa.esquerda, caixa.topo, caixa.largura, caixa.altura),
                    vizinho,
                )
        return None, None
    caixa = Regiao.de_dict(bloco["regiao"])
    return (caixa.esquerda, caixa.topo, caixa.largura, caixa.altura), None


def avisar_sobre_a_geometria(entrada: dict | None, frame) -> list[str]:
    """A janela mudou de tamanho desde a ultima calibracao DESTE personagem?

    Quando nao ha carimbo, NAO se diz nada: e a primeira calibracao daquele
    personagem, e um aviso ali seria ruido no unico momento em que o usuario
    esta aprendendo a ferramenta.

    O carimbo e POR PERSONAGEM e nao global. As duas janelas medem 1720x1392
    hoje, mas a coincidencia e do usuario e nao do jogo, e um carimbo unico
    voltaria a misturar as duas instancias pela porta dos fundos — que e
    exatamente o dano que a chave por personagem existe para impedir.
    """
    gravada = (entrada or {}).get("geometria_da_janela")
    if not isinstance(gravada, dict):
        return []
    altura, largura = int(frame.shape[0]), int(frame.shape[1])
    if (
        int(gravada.get("largura", largura)) == largura
        and int(gravada.get("altura", altura)) == altura
    ):
        return []
    return [
        "",
        "A JANELA MUDOU DE TAMANHO desde a ultima calibracao deste personagem:",
        f"  gravada: {gravada.get('largura')}x{gravada.get('altura')}"
        f"   agora: {largura}x{altura}",
        "  Os retangulos antigos apontam para lugares diferentes nesta janela.",
        "  Esta e a causa numero um de 'a leitura quebrou do nada', e voce nao",
        "  tem como saber sozinho -- por isso este aviso sai ANTES da primeira",
        "  selecao. Confira cada retangulo com o olho antes de aceitar.",
        "",
    ]


def _resolver_a_fonte(args, cal: Calibracao):
    """(frame, personagem, titulo_da_janela, erro). Sem captura antes da recusa.

    O NOME DO PERSONAGEM E PRE-REQUISITO DA RODADA, e nao enfeite do cabecalho
    (LEIT-07). No caminho `--janela` ele sai do titulo por
    `cliente.nome_do_personagem`, que ja e usado assim pelo `--mercado`. No
    caminho `--imagem` nao ha titulo, entao `--personagem` e OBRIGATORIO — sem
    default, sem "o unico que estiver no arquivo", sem cair no primeiro.

    A razao vai com o numero ao lado: as duas instancias poem a janela de
    status em `246,736` e em `236,750`, e um calibrador que adivinha o
    personagem grava o retangulo de um por cima do outro. Essa e a unica
    maneira de este calibrador causar exatamente o dano que ele existe para
    impedir.
    """
    from .renda_modo import _frame_de_imagem, _frame_de_janela

    if args.imagem is not None:
        if not args.personagem:
            return None, None, None, (
                "O calibrador precisa saber DE QUEM E A TELA antes de comecar.\n"
                "  --personagem e OBRIGATORIO junto de --imagem: um PNG nao\n"
                "  carrega titulo de janela, e a calibracao da renda e POR\n"
                "  PERSONAGEM. As duas instancias poem a janela de status em\n"
                "  lugares diferentes (14 px na vertical, medido), e calibrar\n"
                "  sem saber de quem e a tela grava o retangulo de um por cima\n"
                "  do outro."
            )
        frame, erro = _frame_de_imagem(args.imagem)
        return frame, args.personagem, None, erro

    titulo = args.janela or cal.janela
    if not titulo:
        janelas = listar_janelas_do_jogo()
        if len(janelas) != 1:
            return None, None, None, (
                "Nao sei qual janela do jogo calibrar para a renda.\n"
                f"  janelas encontradas: {janelas or '(nenhuma)'}\n"
                '  Use: calibrar-renda.bat --janela "TITULO"'
            )
        titulo = janelas[0]

    personagem = args.personagem or nome_do_personagem(titulo)
    if not personagem:
        return None, None, None, (
            f"Nao consegui tirar o nome do personagem do titulo {titulo!r}.\n"
            "  A calibracao da renda e POR PERSONAGEM e nao comeca sem saber de\n"
            "  quem e a tela. Passe --personagem NOME."
        )
    frame, erro = _frame_de_janela(titulo)
    return frame, personagem, titulo, erro


def _varrer_as_regioes_de_ocr(frame, entrada: dict, pisos) -> dict:
    """A varredura de OCR de cada regiao que ainda e lida por OCR.

    SAO VARREDURAS SEPARADAS, UMA POR REGIAO, e cada uma produz o SEU proprio
    piso (LEIT-08). Nao existe um caminho que varra "a barra" como uma coisa
    so, nem um piso que sirva duas regioes: medido (M-E), a banda do nivel
    (190-220) e a da adena (150) nao tem intersecao nenhuma.
    """
    from .renda_leitura import recortar

    resultado = {}
    for regiao in REGIOES_VARRIDAS_POR_OCR:
        bloco = _bloco_da_regiao(entrada, regiao)
        if bloco is None:
            continue
        recorte = recortar(frame, Regiao.de_dict(bloco["regiao"]), campo=regiao)
        if isinstance(recorte, RecusaDaRenda):
            resultado[regiao] = (None, recorte)
            continue
        linhas = varrer_o_piso(
            recorte,
            pisos,
            campo=regiao,
            gramatica=_gramatica_da_regiao(regiao),
        )
        resultado[regiao] = (linhas, None)
    return resultado


def _imprimir_a_varredura(varreduras: dict) -> dict:
    """Imprime a curva de cada regiao e devolve a banda util de cada uma."""
    bandas = {}
    for regiao, (linhas, recusa) in varreduras.items():
        print()
        print(f"--- {ROTULO_DA_REGIAO[regiao]} ---")
        if recusa is not None:
            print(f"  RECUSADO ({recusa.motivo}): {recusa.detalhe}")
            continue
        for linha in linhas:
            print(linha.como_texto())
        banda = resumir_a_banda_util(linhas)
        bandas[regiao] = banda
        print()
        for texto in descrever_a_banda(ROTULO_DA_REGIAO[regiao], banda):
            print(texto)
    return bandas


def medir_a_forma_da_adena(frame, bloco: dict | None) -> list[str]:
    """A altura de faixa e as larguras das corridas do recorte ESCOLHIDO.

    ESTA FUNCAO MEDE E NAO CLASSIFICA, e a distincao e o que a mantem deste
    lado da fronteira. Ela nao decide se a forma e valida — quem decide e a
    peneira `renda_leitura._glifos_do_numero`, do `01-05`, e escrever uma
    segunda aqui seria criar duas formas para os mesmos moldes. Ela imprime os
    numeros crus para o OLHO do usuario comparar.

    POR QUE ELA EXISTE MESMO ASSIM, e e uma ameaca nomeada (T-01-61): quem
    escolhe o retangulo aqui escolhe a ALTURA DE FAIXA que a guarda do `01-05`
    vai usar. Medido (M-K), em `1560:1690` um run de largura 9 ainda entra no
    fim e estica a faixa; um recorte que pega o icone seguinte travaria o
    cortador de moldes inteiro, e o conserto seria AQUI, no retangulo, e nao la.
    Sem esta medicao na tela, o usuario so descobriria isso duas ferramentas
    depois.

    A CONVENCAO DE LARGURA VAI DECLARADA, e ela ja custou duas refutacoes a
    esta fase (o "17" do M-I e o "5" do M-O). Estes numeros saem de
    `segmentar_glifos_no_brilho`, cuja convencao e `fim - inicio` —
    **EXCLUSIVA**, a mesma de `larguras_de_molde`. O `01-MEDICOES-DE-CAMPO.md`
    relata os mesmos runs na convencao INCLUSIVA (`fim - inicio + 1`), e as
    duas descrevem a mesma tela diferindo por um pixel.
    """
    if not bloco or "regiao" not in bloco or "piso_de_brilho" not in bloco:
        return []
    from .renda_leitura import recortar

    recorte = recortar(
        frame, Regiao.de_dict(bloco["regiao"]), campo=REGIAO_VARRIDA_POR_GLIFO
    )
    if isinstance(recorte, RecusaDaRenda):
        return [f"  RECUSADO ({recorte.motivo}): {recorte.detalhe}"]

    faixa, corridas = segmentar_glifos_no_brilho(recorte, int(bloco["piso_de_brilho"]))
    if faixa is None or not corridas:
        return [
            f"  No piso {bloco['piso_de_brilho']} este recorte nao tem tinta "
            f"nenhuma.",
            "  Ou o retangulo nao esta sobre a adena, ou o piso apagou o campo.",
        ]
    larguras = [fim - inicio for inicio, fim in corridas]
    linhas = [
        f"  piso {bloco['piso_de_brilho']}  altura de faixa {faixa[1] - faixa[0]}"
        f"  {len(corridas)} corridas",
        f"  larguras (convencao EXCLUSIVA, `fim - inicio`): {larguras}",
        "  Esperado: um run LARGO em cada ponta (os icones de moeda, 14 e 15) e",
        "  no meio so larguras de digito (4, 5 ou 6) e de virgula (1).",
    ]
    if (
        len(larguras) > 2
        and max(larguras[1:-1])
        > max(larguras[0], larguras[-1]) * FRACAO_DO_ICONE_QUE_AINDA_E_DIGITO
    ):
        linhas += [
            "  AVISO: ha um run LARGO NO MEIO. O recorte esta pegando o icone da",
            "  moeda de ouro, ou a cauda da L-Coin -- foi exatamente assim que o",
            "  retangulo `1500,1360 200x32` foi refutado (M-N, M-Q). Marque um",
            "  recorte que COMECE depois do icone e TERMINE antes do seguinte.",
        ]
    return linhas


def _varrer_a_adena(frame, bloco: dict | None, pisos, cal: Calibracao):
    """A varredura de FORMA da `barra_direita`. `None` sem retangulo.

    Ela e separada de `_varrer_as_regioes_de_ocr` e nao um ramo dentro dela: as
    duas classificam por metodos diferentes, e um `if` no meio de um laco
    comum seria o convite para alguem "unificar" as duas curvas e comparar
    pisos que nao sao comparaveis.
    """
    if not bloco or "regiao" not in bloco:
        return None
    from .renda_leitura import recortar

    recorte = recortar(
        frame, Regiao.de_dict(bloco["regiao"]), campo=REGIAO_VARRIDA_POR_GLIFO
    )
    if isinstance(recorte, RecusaDaRenda):
        return recorte
    return varrer_a_forma(
        recorte, pisos, moldes_da_barra=cal.renda_moldes_da_barra
    )


def _imprimir_a_varredura_da_adena(
    cal: Calibracao, frame=None, bloco=None, pisos=()
) -> BandaUtil | None:
    """A curva de glifo na tela, e a banda util dela. Ou o motivo de nao haver.

    O QUE ELA DIZ EM VOZ ALTA QUANDO NAO HA MOLDES: que a banda acima e de
    FORMA e nao de VALOR, e a ORDEM DE OPERACAO — a informacao que o usuario
    nao tem como adivinhar e que precisa aparecer no terminal dele, e nao so
    num plano. Sem os moldes o valor nao foi lido, e dizer "confirmado" aqui
    seria a mesma mentira que o `.bat` do mercado ja pagou em campo: anunciar
    uma conferencia que nao aconteceu.
    """
    print()
    print(f"--- {ROTULO_DA_REGIAO[REGIAO_VARRIDA_POR_GLIFO]} ---")
    print(f"  metodo: {METODO_POR_GLIFO} -- nao ha {METODO_POR_OCR} neste campo.")
    if frame is not None:
        for texto in medir_a_forma_da_adena(frame, bloco):
            print(texto)

    conjunto = cal.renda_moldes_da_barra
    if conjunto is None:
        print("  Moldes da fonte da barra: NENHUM gravado ainda.")
    else:
        print(
            f"  Moldes da fonte da barra: "
            f"{len((conjunto or {}).get('moldes') or [])} gravado(s)."
        )

    linhas = _varrer_a_adena(frame, bloco, pisos, cal) if frame is not None else None
    if isinstance(linhas, RecusaDaRenda):
        print(f"  RECUSADO ({linhas.motivo}): {linhas.detalhe}")
        return None
    if linhas is None:
        print("  Sem retangulo para este campo, nao ha o que varrer.")
        print()
        for texto in ordem_de_operacao():
            print(texto)
        return None

    print()
    for linha in linhas:
        print(linha.como_texto())
    for texto in avisar_sobre_o_limite_herdado(linhas):
        print(texto)

    banda = resumir_a_banda_util(linhas)
    print()
    for texto in descrever_a_banda(ROTULO_DA_REGIAO[REGIAO_VARRIDA_POR_GLIFO], banda):
        print(texto)
    for texto in descrever_a_forma(ROTULO_DA_REGIAO[REGIAO_VARRIDA_POR_GLIFO], linhas):
        print(texto)

    print()
    print("  ESTA BANDA AFIRMA QUE O PISO SEGMENTA COMO UM NUMERO, e nada alem")
    print("  disso. Que o numero lido esta CERTO e o seu olho que confirma, na")
    print("  imagem de conferencia contra a tela do jogo.")
    if conjunto is None:
        print("  O VALOR NAO FOI LIDO nesta rodada: ler exige moldes, e nao ha")
        print("  molde nenhum gravado. A banda acima e de FORMA, e ela vale.")
        print()
        for texto in ordem_de_operacao():
            print(texto)
    return banda


def _mutar_a_entrada_do_personagem(
    cal: Calibracao,
    personagem: str,
    *,
    retangulos: dict,
    pisos: dict,
    geometria: dict,
) -> None:
    """Copia com SUBSTITUICAO da chave do personagem. Nunca reconstrucao.

    Um dicionario remontado a partir do que ESTE codigo conhece apaga a
    sub-chave que uma versao futura tiver acrescentado — e apaga o personagem
    vizinho inteiro, que e a mesma familia de defeito do `salvar` uma camada
    acima e a mesma forma do incidente de 2026-08-30: um escritor montando do
    zero o que devia ter carregado.

    Por isso cada nivel e copiado com `dict(...)` e so as chaves desta rodada
    sao trocadas: o vizinho sobrevive porque nunca foi tocado, e a sub-chave
    desconhecida sobrevive porque a copia a carrega junto.
    """
    por_personagem = dict(cal.renda_por_personagem or {})
    entrada = dict(por_personagem.get(personagem) or {})
    for regiao in REGIOES_DA_RENDA:
        bloco = dict(_bloco_da_regiao(entrada, regiao) or {})
        if retangulos.get(regiao) is not None:
            bloco["regiao"] = Regiao(*retangulos[regiao]).como_dict()
        if pisos.get(regiao) is not None:
            piso, largura = pisos[regiao]
            bloco["piso_de_brilho"] = int(piso)
            bloco["largura_da_banda"] = int(largura)
        entrada[regiao] = bloco
    entrada["geometria_da_janela"] = geometria
    por_personagem[personagem] = entrada
    cal.renda_por_personagem = por_personagem


def _desenhar_a_conferencia(frame, entrada: dict):
    """Os tres retangulos em cores distintas, rotulados, sobre uma COPIA."""
    tela = frame.copy()
    for regiao in REGIOES_DA_RENDA:
        bloco = _bloco_da_regiao(entrada, regiao)
        if bloco is None:
            continue
        caixa = Regiao.de_dict(bloco["regiao"])
        cor = COR_DA_REGIAO[regiao]
        cv2.rectangle(
            tela,
            (caixa.esquerda, caixa.topo),
            (caixa.esquerda + caixa.largura, caixa.topo + caixa.altura),
            cor,
            2,
        )
        cv2.putText(
            tela,
            regiao,
            (caixa.esquerda, max(16, caixa.topo - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            cor,
            1,
        )
    return tela


def montar_analisador() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(
        prog="python -m l2scanner.calibrar_renda",
        description=(
            "Marca as tres regioes da renda e mede o piso de brilho de cada "
            "uma. A calibracao e POR PERSONAGEM."
        ),
    )
    fonte = analisador.add_mutually_exclusive_group()
    fonte.add_argument(
        "--janela",
        nargs="?",
        const="",
        help="o titulo da janela do jogo (sem valor: usa o da calibracao)",
    )
    fonte.add_argument(
        "--imagem",
        type=Path,
        help="um PNG de janela inteira; exige --personagem junto",
    )
    analisador.add_argument(
        "--personagem",
        help="de quem e esta tela. OBRIGATORIO com --imagem",
    )
    analisador.add_argument(
        "--so-medir",
        action="store_true",
        help="imprime a varredura de piso e NAO escreve no disco",
    )
    analisador.add_argument(
        "--partir-de",
        type=Path,
        help="le a calibracao de PARTIDA de outro arquivo. So com --so-medir",
    )
    return analisador


def calibrar_renda(args) -> int:
    """Carrega, muta so a entrada DESTE personagem, e reemite tudo.

    A ORDEM DAS ETAPAS E O PRODUTO, e nao um detalhe de organizacao:

      1. recusar a combinacao ilegal de argumentos, antes de tudo;
      2. CARREGAR o `calibration.json` inteiro — a primeira linha util;
      3. descobrir de quem e a tela, e so entao capturar pixel;
      4. avisar se a janela mudou de tamanho, ANTES da primeira selecao;
      5. tres selecoes, com a sugestao vinda do disco;
      6. varrer o piso de cada regiao lida por OCR;
      7. mutar SO a entrada daquele personagem, e gravar.

    Toda a nao-destruicao desta fase pende da etapa 2 acontecer antes da 7.
    """
    # `--partir-de` sem `--so-medir` e RECUSADO, e a recusa e nomeada. Um
    # calibrador que le de um arquivo e escreve em outro fabrica uma calibracao
    # que o scanner nunca ve — o sintoma e "calibrei e o scanner nao ve", e o
    # usuario nao tem como ligar uma coisa na outra.
    if args.partir_de is not None and not args.so_medir:
        print(
            "--partir-de e legal SOMENTE junto de --so-medir.\n"
            "  Esta combinacao -- ler a calibracao de um arquivo e gravar em "
            "outro --\n"
            "  fabrica uma calibracao que o scanner nunca ve. O destino de "
            "escrita\n"
            f"  deste calibrador e sempre {ARQUIVO_CALIBRACAO}.",
            file=sys.stderr,
        )
        return SAIDA_OPERACIONAL

    origem = args.partir_de or ARQUIVO_CALIBRACAO
    try:
        cal = Calibracao.carregar(origem)
    except CalibracaoInvalida as erro:
        print(f"A calibracao existente nao serve: {erro}", file=sys.stderr)
        return SAIDA_OPERACIONAL
    except Exception as erro:  # noqa: BLE001 - a ferramenta explica sem traceback
        print(f"Nao consegui abrir a calibracao existente: {erro}", file=sys.stderr)
        return SAIDA_OPERACIONAL

    frame, personagem, titulo, erro = _resolver_a_fonte(args, cal)
    if erro is not None:
        print(erro, file=sys.stderr)
        return SAIDA_OPERACIONAL
    if frame is None or getattr(frame, "size", 0) == 0:
        print("Nenhum frame utilizavel chegou da fonte.", file=sys.stderr)
        return SAIDA_OPERACIONAL

    print(f"Calibrando a renda de {personagem!r}.")
    entrada_em_disco = (cal.renda_por_personagem or {}).get(personagem)
    for linha in avisar_sobre_a_geometria(entrada_em_disco, frame):
        print(linha)

    pisos_da_grade = grade_de_pisos(
        PISO_DE_BRILHO_MINIMO_DA_RENDA, PISO_DE_BRILHO_MAXIMO_DA_RENDA
    )

    if args.so_medir:
        if not entrada_em_disco:
            print(
                f"Nao ha calibracao de renda para {personagem!r} neste arquivo, "
                f"entao nao ha retangulo para medir.\n"
                f"  Rode o calibrador sem --so-medir uma vez primeiro.",
                file=sys.stderr,
            )
            return SAIDA_OPERACIONAL
        _imprimir_a_varredura(
            _varrer_as_regioes_de_ocr(frame, entrada_em_disco, pisos_da_grade)
        )
        _imprimir_a_varredura_da_adena(
            cal,
            frame,
            _bloco_da_regiao(entrada_em_disco, REGIAO_VARRIDA_POR_GLIFO),
            pisos_da_grade,
        )
        print()
        print("--so-medir: NADA foi escrito no disco.")
        return SAIDA_OK

    retangulos: dict[str, tuple[int, int, int, int] | None] = {}
    for indice, regiao in enumerate(REGIOES_DA_RENDA, start=1):
        sugestao, vizinho = _sugestao_de_retangulo(cal, personagem, regiao)
        print()
        print(f"{indice}/{len(REGIOES_DA_RENDA)} - {ROTULO_DA_REGIAO[regiao]}")
        if vizinho is not None:
            # SUGERIR E CONFIRMADO POR UM HUMANO; CAIR E SILENCIOSO. O aviso e
            # o que separa os dois, e ele nao e opcional: sem ele o usuario
            # aceitaria com ENTER um retangulo de outra instancia achando que
            # era o dele.
            print(
                f"      A SUGESTAO DESENHADA VEIO DE OUTRO PERSONAGEM "
                f"({vizinho!r}) --"
            )
            print(
                "      este ainda nao tem retangulo gravado. Confira com o olho "
                "antes de aceitar."
            )
        caixa = _selecionar_regiao(
            frame, ROTULO_DA_REGIAO[regiao], INSTRUCAO_DA_REGIAO[regiao], sugestao
        )
        retangulos[regiao] = caixa
        if caixa is None:
            # ESC PRESERVA, e nunca zera: uma regiao zerada e indistinguivel de
            # uma regiao nunca calibrada, e quem apertou ESC por engano perderia
            # trabalho sem uma linha de aviso.
            print("      ESC: o retangulo anterior desta regiao foi PRESERVADO.")

    efetiva: dict[str, dict] = {}
    for regiao in REGIOES_DA_RENDA:
        bloco = dict(_bloco_da_regiao(entrada_em_disco, regiao) or {})
        if retangulos[regiao] is not None:
            bloco["regiao"] = Regiao(*retangulos[regiao]).como_dict()
        if "regiao" in bloco:
            efetiva[regiao] = bloco

    bandas = _imprimir_a_varredura(
        _varrer_as_regioes_de_ocr(frame, efetiva, pisos_da_grade)
    )
    # A ADENA ENTRA NO MESMO DICIONARIO DE BANDAS, E SO AQUI OS DOIS METODOS SE
    # ENCONTRAM: cada regiao ja tem a SUA banda, medida do SEU jeito, e o que
    # este dicionario faz e gravar cada uma no seu lugar. Nenhuma funcao
    # combina bandas de regioes diferentes -- medido (M-E), a banda do nivel e
    # a da adena nao tem intersecao nenhuma.
    banda_da_adena = _imprimir_a_varredura_da_adena(
        cal, frame, efetiva.get(REGIAO_VARRIDA_POR_GLIFO), pisos_da_grade
    )
    if banda_da_adena is not None:
        bandas[REGIAO_VARRIDA_POR_GLIFO] = banda_da_adena

    pisos = {
        regiao: (escolher_o_piso(banda), banda.largura)
        for regiao, banda in bandas.items()
        if escolher_o_piso(banda) is not None
    }

    if not any(caixa is not None for caixa in retangulos.values()) and not pisos:
        print()
        print(
            "Nenhuma regiao marcada e nenhum piso medido; a calibracao anterior "
            "foi mantida.",
            file=sys.stderr,
        )
        return SAIDA_OPERACIONAL

    faltando = [
        regiao
        for regiao in REGIOES_DA_RENDA
        if not (
            (
                retangulos[regiao] is not None
                or "regiao" in (_bloco_da_regiao(entrada_em_disco, regiao) or {})
            )
            and (
                regiao in pisos
                or "piso_de_brilho"
                in (_bloco_da_regiao(entrada_em_disco, regiao) or {})
            )
        )
    ]
    if faltando:
        print()
        print(
            "NADA FOI GRAVADO. Estas regioes ficariam sem retangulo ou sem "
            f"piso de brilho: {', '.join(faltando)}.\n"
            "  Uma entrada pela metade e pior que uma entrada ausente: a "
            "ausente desliga\n"
            "  a feature, a pela metade faz a leitura procurar um campo que "
            "nao tem endereco.\n"
            "  A ordem de operacao acima diz de onde vem o que esta faltando.",
            file=sys.stderr,
        )
        return SAIDA_OPERACIONAL

    if titulo:
        # O UNICO EMPRESTIMO LEGITIMO fora da chave da renda, e o
        # `calibrar_tiat` ja o faz: a janela mirada e do processo inteiro e
        # nao desta feature.
        cal.janela = titulo
    _mutar_a_entrada_do_personagem(
        cal,
        personagem,
        retangulos=retangulos,
        pisos=pisos,
        geometria={
            "largura": int(frame.shape[1]),
            "altura": int(frame.shape[0]),
        },
    )

    try:
        cal.salvar(ARQUIVO_CALIBRACAO)
    except OSError as erro:
        print(
            f"A calibracao NAO foi salva: {erro}\n"
            f"  O motivo mais comum e o {ARQUIVO_CALIBRACAO.name} estar aberto "
            f"noutro programa\n"
            f"  ou o disco estar somente-leitura. Feche e rode de novo -- nada "
            f"foi perdido.",
            file=sys.stderr,
        )
        return SAIDA_OPERACIONAL

    caminho = _gravar_conferencia(
        _desenhar_a_conferencia(frame, cal.renda_por_personagem[personagem])
    )
    print()
    print(f"Renda de {personagem!r} calibrada e gravada.")
    if caminho:
        print(
            f"CONFIRA {caminho}: amarelo = EXP; verde = adena; azul = nivel."
        )
    else:
        print(
            "A calibracao foi salva, mas NAO consegui gravar imagem de "
            "conferencia nenhuma."
        )
    return SAIDA_OK


def main(argv: list[str] | None = None) -> int:
    return calibrar_renda(montar_analisador().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
