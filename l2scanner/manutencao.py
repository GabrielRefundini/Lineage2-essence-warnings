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

import difflib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

log = logging.getLogger(__name__)

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
# ELA NAO BASTA — ver `eh_banner_de_manutencao`. Continua aqui porque e o
# CAMINHO RAPIDO: quando o OCR entrega a palavra inteira, nenhuma conta de
# semelhanca precisa rodar.
_RAIZ = "mainten"

# As duas grafias inteiras, para a comparacao POR SEMELHANCA. O jogo escreve
# `Maintence`; `Maintenance` esta aqui para o dia em que ele corrigir o typo.
_GRAFIAS = ("maintence", "maintenance")

# A ANCORA. Medida em 31/08 nas oito leituras reais: aparece em 8 de 8, e limpa
# em 7. E o trecho mais confiavel do banner inteiro — mais que o titulo.
_ANCORA = "avoid entering instance"

# UM CORTE SO PARA OS DOIS RAMOS, e ele esta preso a uma colisao medida.
# Ver a tabela em `eh_banner_de_manutencao`: `aintence` da 0,941, `aiptence` da
# 0,824 e `main entrance` da 0,833. O corte tem de ficar ACIMA de 0,833, entao
# 0,85. O `aiptence` fica de fora de proposito e e recuperado pela ancora.
_CORTE_DA_SEMELHANCA = 0.85

# Quanto a janela de comparacao pode encolher ou crescer em relacao ao alvo.
# 2 caracteres cobrem o lixo que o OCR gruda nas bordas da palavra
# (`Servergqaiptenceatl`, `"aintencea2J`) sem varrer a tela inteira.
_FOLGA_DA_JANELA = 2

# DOIS JOGOS DE PADROES, E A SEPARACAO E A CORRECAO INTEIRA.
#
# Antes havia um jogo so, que respondia "numero + unidade" e "a unidade
# apareceu?" ao mesmo tempo. Por isso "unidade sem numero" sumia em silencio: o
# padrao nao casava, o parser somava o que sobrou e devolvia uma resposta com
# cara de boa. Medido: `__40nin? es 26 seconds` virava 26 segundos.
#
# CAPTURA — numero + unidade. Roda sobre o texto NORMALIZADO.
#
# `[mn]` recupera o `ninutes` que o motor produz de verdade (medido em cinza
# 2x). O `\s*` (zero ou mais, nunca um ou mais) recupera o `40ninutes` grudado.
# As classes `[o0]` e `[5s]` existem porque `_normalizar_digitos` traduz DENTRO
# de um token que ja tem digito: `26seconds` grudado vira `265ec0nd5`, e o
# retrocesso do regex ainda captura o 26 ali.
_HORAS = re.compile(r"(\d+)\s*h[o0]ur")
_MINUTOS = re.compile(r"(\d+)\s*[mn]inut")
_SEGUNDOS = re.compile(r"(\d+)\s*[5s]ec[o0]nd")

# PRESENCA — a unidade apareceu, com ou sem numero acoplado.
#
# `[mn]in` e deliberadamente frouxo E comprovadamente seguro no contexto. Nem
# `maintence` (m-a-i-n-t-e-n-c-e) nem `maintenance` (m-a-i-n-t-e-n-a-n-c-e)
# contem `min` ou `nin` — confira letra a letra —, e o unico texto que chega
# aqui ja passou por `eh_banner_de_manutencao`.
#
# A ASSIMETRIA DE CUSTO E O QUE AUTORIZA A FROUXIDAO: um falso positivo da
# presenca custa UMA leitura, ou seja 5 segundos ate a proxima cadencia. Um
# falso negativo faz 40 minutos virarem 26 segundos e a party inteira largar o
# farm por nada.
#
# O PRECO ACEITO, escrito para nao virar surpresa: se um nome de personagem ou
# um texto vizinho dentro da faixa contiver `min`/`nin`, a guarda dispara e a
# leitura se perde. De proposito — sempre para o lado seguro.
#
# A presenca de HORAS espelha a forma da de minutos sem inventar evidencia: o
# jogo anuncia com dezenas de MINUTOS, e nunca foi observado embaralhando
# `hour`. Simetria por consistencia, nao por medicao.
_PALAVRA_DE_HORAS = re.compile(r"h[o0]ur")
_PALAVRA_DE_MINUTOS = re.compile(r"[mn]in")

# Leitura acima disto e lixo do OCR, nao manutencao. O jogo anuncia com dezenas
# de minutos, nunca com dias.
_TETO = timedelta(hours=24)

# As confusoes classicas do OCR, aplicadas SO em contexto de digito.
_TROCAS = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "S": "5", "s": "5"})


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


def _semelhanca_maxima(alvo: str, texto: str) -> float:
    """O melhor pedaco de `texto` que se parece com `alvo`, de 0,0 a 1,0.

    JANELA DESLIZANTE, E NAO COMPARACAO POR TOKEN, porque o defeito que esta
    funcao existe para vencer GRUDA palavras: o motor entregou
    `Servergqaiptenceatl` e `"aintencea2J` como UM token so. Comparar token
    contra token afogaria `aintence` no lixo colado nele.

    A METRICA E `difflib.SequenceMatcher`, DA STDLIB, E NAO `rapidfuzz`.
    Mesmo motivo ja registrado em `mercado_catalogo` (D-04): `rapidfuzz` NAO
    esta instalado e NAO esta no `requirements.txt` deste projeto, e a arvore de
    dependencias e guardada por `tests/test_firewall_escopo.py`. Sobre alvos de
    9 a 23 caracteres as duas metricas dao praticamente o mesmo numero, e uma
    dependencia nova para isso seria paga em risco sem nada em troca.

    CUSTO MEDIDO: 3,4 ms para varrer um texto de ~100 caracteres contra as duas
    grafias E a ancora. A cadencia e de 5 s e a passada de OCR que produz o
    texto custa 23 ms, entao isto e ruido. E o caminho rapido de
    `eh_banner_de_manutencao` nem chega aqui quando a palavra veio inteira.
    """
    alvo = alvo.lower()
    texto = texto.lower()
    tamanho = len(alvo)
    melhor = 0.0
    medidor = difflib.SequenceMatcher(autojunk=False)
    medidor.set_seq1(alvo)
    for largura in range(max(1, tamanho - _FOLGA_DA_JANELA), tamanho + _FOLGA_DA_JANELA + 1):
        for inicio in range(0, max(1, len(texto) - largura + 1)):
            medidor.set_seq2(texto[inicio : inicio + largura])
            # Os dois limites SUPERIORES baratos do proprio difflib, na ordem
            # de custo. E o que mantem a varredura em milissegundos.
            if medidor.real_quick_ratio() <= melhor or medidor.quick_ratio() <= melhor:
                continue
            razao = medidor.ratio()
            if razao > melhor:
                melhor = razao
    return melhor


def parece_palavra_de_manutencao(texto: str | None) -> bool:
    """`Maintence` mesmo com o OCR comendo letras. PUBLICA de proposito.

    Ela e um dos DOIS ramos da porta 1 e tem uma medicao propria (a colisao com
    `main entrance`), entao precisa poder ser cobrada sozinha por teste. Cobrar
    so a porta inteira deixaria o ramo passar a valer por acidente, pela ancora.
    """
    if not texto:
        return False
    if _RAIZ in texto.lower():
        return True  # caminho rapido: a palavra veio inteira
    return any(
        _semelhanca_maxima(grafia, texto) >= _CORTE_DA_SEMELHANCA
        for grafia in _GRAFIAS
    )


def _tem_a_ancora(texto: str) -> bool:
    """`avoid entering instance`, inteira ou embaralhada."""
    if _ANCORA in texto.lower():
        return True  # caminho rapido: 7 das 8 leituras de campo param aqui
    return _semelhanca_maxima(_ANCORA, texto) >= _CORTE_DA_SEMELHANCA


def _tem_contagem(texto: str) -> bool:
    """Existe numero colado numa unidade de tempo neste texto?

    Reusa as MESMAS capturas de `interpretar_banner` de proposito: se a porta 1
    aceitasse uma forma de contagem que o parser nao entende, ela abriria a
    porta para uma leitura que nunca vira aviso — barulho no log e nada mais.
    """
    normalizado = _normalizar_digitos(texto).lower()
    return any(
        padrao.search(normalizado) for padrao in (_HORAS, _MINUTOS, _SEGUNDOS)
    )


def eh_banner_de_manutencao(texto: str | None) -> bool:
    """A primeira das TRES portas contra inventar uma manutencao.

    As outras duas sao exigir uma duracao interpretavel (`interpretar_banner`)
    e exigir consenso (`VigiaDeManutencao`). Nenhuma sozinha basta, e e por
    isso que sao tres. Elas continuam sendo tres depois deste conserto.

    A RAZAO ANTIGA CAIU EM CAMPO, ENTAO ELA FICA ESCRITA AQUI
    =========================================================
    Ate 31/08/2026 esta porta era `"mainten" in texto.lower()`, com o argumento
    de que a raiz e o token mais RARO da tela. O raciocinio estava certo e o
    TOKEN estava errado. Em 31/08 o servidor entrou em manutencao as ~18:20,
    o banner ficou na tela por quase uma hora, o scanner nao anunciou NADA, e
    quatro rodadas de `--testar-manutencao --janela` mediram por que:

        escala  o que o motor leu, no trecho do titulo   contem `mainten`?
        2x      `Servergqaiptenceatl`                    NAO
        3x      `Server` (a palavra sumiu inteira)       NAO
        2x      (a palavra sumiu inteira)                NAO
        3x      (a palavra sumiu inteira)                NAO
        2x      (a palavra sumiu inteira)                NAO
        3x      `Server "aintencea2J`                    NAO
        2x      (a palavra sumiu inteira)                NAO
        3x      `Server "aintencea,QJ`                   NAO

    O `M` maiusculo NUNCA sobreviveu: 8 leituras, 8 ausencias da raiz. A porta
    1 nunca fechava, e as outras duas portas nem chegavam a ser consultadas.

    DOIS RAMOS INDEPENDENTES, E CADA UM COBRE O QUE O OUTRO PERDE
    =============================================================
    RAMO A — a PALAVRA, por semelhanca (`parece_palavra_de_manutencao`).
    Medido com `difflib` contra `maintence`/`maintenance`:

        `aintence`       0,941  -> passa
        `main entrance`  0,833  -> NAO passa
        `aiptence`       0,824  -> NAO passa
        `instance`       0,706  -> NAO passa

    O corte e 0,85 porque tem de ficar ACIMA de 0,833. E NENHUM corte escalar
    resolveria melhor: `aiptence` (0,824) esta ABAIXO de `main entrance`
    (0,833), entao aceitar o embaralhado obrigaria a aceitar a colisao junto.
    HONESTIDADE SOBRE A PROVENIENCIA: `aintence` e `aiptence` sao leituras
    reais do jogo; `main entrance` e uma string ADVERSARIAL construida aqui, a
    colisao mais proxima que consegui montar com texto plausivel de jogo. Ela
    nao foi vista na tela, e mesmo assim manda no corte, porque o custo de uma
    manutencao inventada e uma mensagem falsa no grupo.

    RAMO B — a ANCORA `avoid entering instance` MAIS uma contagem.
    Medida nas mesmas oito leituras: aparece em 8 de 8, limpa em 7, e na oitava
    (`4—vvaÅZidentering instance`) da 0,889 por semelhanca. E o trecho mais
    confiavel do banner inteiro, mais que o proprio titulo — e e ele que
    recupera as leituras em que a palavra sumiu.

    A CONTAGEM E OBRIGATORIA NESTE RAMO, e nao e detalhe: a frase sozinha JA
    aparecia na lista de textos que NAO sao o banner
    (`test_texto_que_nao_e_o_banner_nao_vira_nada`), porque o jogo a diz em
    outros contextos. Ancora E contagem, nunca ancora sozinha.

    O QUE NAO MUDOU, e continua valendo pelo mesmo motivo de antes: exigir a
    palavra `server` seria PIOR, nao melhor. Um `5erver` mal lido derrubaria a
    deteccao, e `server` aparece em frases que nao sao o banner (`the server
    will restart in a few minutes`, dos prints do usuario).
    """
    if not texto:
        return False
    if parece_palavra_de_manutencao(texto):
        return True
    return _tem_a_ancora(texto) and _tem_contagem(texto)


def interpretar_banner(texto: str | None) -> timedelta | None:
    """Quanto falta, segundo o texto do banner. None quando nao da para dizer.

    A GUARDA ESTRUTURAL (D-b) e o coracao desta funcao, e ela nasceu de uma
    medicao. Contra `tests/fixtures/manutencao/banner_40min26s.png`, com a
    imagem em COR, o motor leu:

        12 Server Maintence __40nin? es 26 seconds Please avoid entering ...

    A versao antiga procurava numero-colado-em-unidade, nao achava minuto
    nenhum, achava `26 seconds` e devolvia 26 SEGUNDOS — quando faltavam 40
    minutos e 26 segundos. E o pior tipo de erro: plausivel.

    A regra que corrige isso: se a UNIDADE aparece e o NUMERO dela nao pode ser
    extraido, a leitura e inconfiavel e a funcao CALA. Jamais cair para "entao e
    so os segundos" — foi exatamente assim que 40min26s virou 26s.

    A conta que justifica calar: perder uma leitura custa 5 segundos, uma
    cadencia, numa contagem que dura 40 minutos. Anunciar manutencao iminente
    sem motivo custa a farm da party inteira.

    A ORDEM DOS PASSOS E DELIBERADA e esta escrita abaixo passo a passo. A
    guarda vem ANTES de somar qualquer componente — depois da soma, a queda para
    "so os segundos" ja aconteceu.

    Procura PREFIXOS (`minut`, `[5s]ec[o0]nd`, `h[o0]ur`) e nao palavras
    inteiras, para tolerar plural e o truncamento que o OCR faz no fim da
    palavra.

    `timedelta(0)` e resultado LEGITIMO e nao pode virar None: os prints do
    usuario tem `00 minutes 00 seconds`, que significa "agora".
    """
    if not texto:
        return None

    # O texto CRU (so em minusculas) e o texto NORMALIZADO servem a papeis
    # diferentes, e por isso os dois existem aqui.
    cru = texto.lower()
    normalizado = _normalizar_digitos(texto).lower()

    # CAPTURA sempre no normalizado: e nele que `4O` ja virou `40`.
    horas = _HORAS.search(normalizado)
    minutos = _MINUTOS.search(normalizado)
    segundos = _SEGUNDOS.search(normalizado)

    # PRESENCA nos DOIS textos, bastando casar num deles. E o detalhe que faz a
    # correcao inteira funcionar: `_normalizar_digitos` so transforma tokens que
    # ja tem digito, entao um `40MINUTES` grudado viraria `40m1nute5` e a
    # unidade DESAPARECERIA do texto normalizado — a guarda nao dispararia e o
    # bug voltaria por uma porta lateral. Checar tambem no cru garante o
    # invariante que queremos: a normalizacao so pode nos custar uma leitura,
    # nunca nos dar uma leitura ERRADA.
    def _presente(padrao) -> bool:
        return padrao.search(cru) is not None or padrao.search(normalizado) is not None

    if _presente(_PALAVRA_DE_HORAS) and horas is None:
        return None
    if _presente(_PALAVRA_DE_MINUTOS) and minutos is None:
        return None

    total = 0
    achou = False
    for casou, fator in ((horas, 3600), (minutos, 60), (segundos, 1)):
        if casou:
            achou = True
            total += int(casou.group(1)) * fator

    if not achou:
        return None

    duracao = timedelta(seconds=total)
    if duracao > _TETO:
        return None  # leitura de lixo; melhor calar do que anunciar besteira
    return duracao


class MotivoDoVeredito(Enum):
    """Por que as duas escalas anunciariam, ou por que nao anunciariam.

    NOMEAR CADA DESFECHO E O CONSERTO DE UM DEFEITO, nao enfeite. O
    `--testar-manutencao` tinha logica propria para dar o veredito, e ela
    divergiu: em 31/08 as duas escalas leram texto IDENTICO, as duas
    devolveram None, e a ferramenta imprimiu "As duas escalas DISCORDAM". Elas
    concordavam. O usuario foi mandado conferir a faixa por causa de uma frase
    errada, num dia em que a faixa ja estava certa.
    """

    SEM_BANNER = "sem_banner"
    ACORDO = "acordo"
    SO_A_CONFERENCIA = "so_a_conferencia"
    SO_A_DETECCAO = "so_a_deteccao"
    CONTRADICAO = "contradicao"
    ILEGIVEL = "ilegivel"


# SEM TRAVESSAO E SEM ACENTO: estas frases saem no console do usuario, que e
# cp1252, e tambem no log rotativo.
_EXPLICACOES = {
    MotivoDoVeredito.SEM_BANNER: (
        "A escala de DETECCAO nao viu banner nenhum. Em producao a de "
        "conferencia nem chega a rodar."
    ),
    MotivoDoVeredito.ACORDO: (
        "As duas escalas leram a MESMA duracao. Em producao isto alimenta o "
        "consenso temporal."
    ),
    MotivoDoVeredito.SO_A_CONFERENCIA: (
        "So a escala de CONFERENCIA leu a duracao; a de deteccao se absteve. "
        "Abstencao nao e desacordo, entao a leitura vale."
    ),
    MotivoDoVeredito.SO_A_DETECCAO: (
        "So a escala de DETECCAO leu a duracao; a de conferencia se absteve. "
        "A leitura NAO vale: a de conferencia e a que foi medida acertando."
    ),
    MotivoDoVeredito.CONTRADICAO: (
        "As duas escalas leram duracoes DIFERENTES. Nada sera anunciado."
    ),
    MotivoDoVeredito.ILEGIVEL: (
        "As duas escalas viram o banner e NENHUMA conseguiu ler a duracao. "
        "Nada sera anunciado."
    ),
}

# O conselho que acompanha todo veredito que nao anuncia. Uma frase so, e a
# mesma no log e no console, porque as duas saidas respondem a mesma pergunta
# do usuario: onde eu mexo agora.
CONSELHO_QUANDO_NAO_ANUNCIA = (
    "Compare os dois textos: se uma escala esta cortando o banner, o conserto "
    "e a faixa (chave 'banner_manutencao' no calibration.json); se as duas "
    "leem torto, e o motor de OCR."
)


@dataclass(frozen=True)
class Veredito:
    """O que as DUAS escalas decidem sobre UM frame. Estrutura, nunca texto.

    `anunciaria` e derivado de `duracao` de proposito, e nao um campo proprio:
    assim e IMPOSSIVEL existir um veredito que anuncia sem duracao, ou uma
    duracao aprovada que nao anuncia.
    """

    motivo: MotivoDoVeredito
    duracao: timedelta | None

    @property
    def anunciaria(self) -> bool:
        return self.duracao is not None

    @property
    def explicacao(self) -> str:
        return _EXPLICACOES[self.motivo]


def julgar_as_duas_escalas(
    deteccao: str | None,
    conferencia: str | None,
    tolerancia: timedelta = TOLERANCIA_DO_CONSENSO,
) -> Veredito:
    """A PORTA 3, primeira metade: as duas escalas sobre o MESMO frame.

    Funcao PURA e publica, e as duas coisas por um motivo so: o
    `--testar-manutencao` chama exatamente esta funcao, entao o diagnostico
    nao tem como divergir do produto. Era essa divergencia que fazia a
    ferramenta mentir.

    A REGRA MUDOU EM 31/08, E O QUE MUDOU FOI A REGRA, NAO A PORTA
    ===============================================================
    ANTES: as duas escalas tinham de produzir a MESMA duracao. Medido nas
    quatro rodadas de campo, com o banner na tela:

        rodada   deteccao (2x)   conferencia (3x)   a regra antiga dizia
        1        abstem          20 min 27 s        descarta
        2        abstem          04 min 13 s        descarta
        3        04 min 12 s     04 min 12 s        aceita
        4        abstem          04 min 11 s        descarta

    A 2x acertou 1 de 4; a 3x acertou 4 de 4. E as tres falhas da 2x foram
    ABSTENCAO (`minutes` saiu com a vogal trocada e a guarda estrutural calou),
    NUNCA um numero errado. As duas escalas nunca se contradisseram. A regra
    antiga jogou fora tres leituras boas por uma discordancia que nao existia.

    AGORA: ABSTENCAO NAO E DESACORDO. Quem nao leu nada nao contradisse nada.
    Contradicao e uma coisa so, e continua barrada: duas duracoes DIFERENTES.

    O QUE NAO FOI AFROUXADO, e o outro lado pesa igual
    ===================================================
    1. Quem le SOZINHA tem de ser a de CONFERENCIA. Medido: 4 de 4 contra
       1 de 4. Perder uma leitura solitaria da escala pior custa uma cadencia,
       5 s numa contagem de 40 minutos; ancorar nela custa a farm da party.
    2. O CONSENSO TEMPORAL segue intocado. Nenhum caminho aqui ancora nada
       sozinho: `_registrar` continua exigindo DUAS leituras concordantes.
       O que este veredito produz e uma leitura, nunca uma ancora.
    3. O caso que criou esta guarda (a passada em cor lendo 26 s contra a em
       cinza lendo 40min26s) continua pego, porque sao duas duracoes
       diferentes. E ele hoje esta coberto DUAS vezes: a guarda estrutural de
       `interpretar_banner` transforma aquele texto em abstencao antes mesmo de
       chegar aqui. Foi essa segunda cobertura que tornou seguro afrouxar a
       primeira.

    A ORDEM D-e VIVE AQUI TAMBEM: se a deteccao nao viu banner, o veredito e
    SEM_BANNER sem sequer olhar a conferencia. Em producao a cara nem roda, e
    um diagnostico que ignorasse isso diria "anunciaria" para um caso que
    nunca chega a ser lido.
    """
    if not eh_banner_de_manutencao(deteccao):
        return Veredito(MotivoDoVeredito.SEM_BANNER, None)

    da_deteccao = interpretar_banner(deteccao)
    da_conferencia = (
        interpretar_banner(conferencia)
        if eh_banner_de_manutencao(conferencia)
        else None
    )

    if da_deteccao is not None and da_conferencia is not None:
        if abs(da_deteccao - da_conferencia) > tolerancia:
            return Veredito(MotivoDoVeredito.CONTRADICAO, None)
        # Aprovado, VENCE A LEITURA DE CONFERENCIA. E a que pagamos para ter e
        # a que as medicoes mostraram acertando.
        return Veredito(MotivoDoVeredito.ACORDO, da_conferencia)

    if da_conferencia is not None:
        return Veredito(MotivoDoVeredito.SO_A_CONFERENCIA, da_conferencia)
    if da_deteccao is not None:
        return Veredito(MotivoDoVeredito.SO_A_DETECCAO, None)
    return Veredito(MotivoDoVeredito.ILEGIVEL, None)


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


def texto_de_5_minutos(momento: datetime, restante: timedelta) -> str:
    """Diz os minutos REAIS que faltam, calculados da ancora.

    POR QUE ELE NAO PODE DIZER "5" FIXO: quando o scanner sobe no meio de uma
    contagem de 3 minutos, os dois avisos saem juntos e atrasados. Cravar "5"
    ali seria mentir sobre o unico numero que importa — e o grupo se
    programaria para dois minutos que nao existem.
    """
    return (
        f"MANUTENCAO DO SERVIDOR em {descrever_duracao(restante)} "
        f"(as {momento.strftime('%H:%M')}). Saia da instance e recolha o loot do chao."
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

    O CRUZAMENTO DE ESCALAS (D-d) e a segunda guarda, e ela e COMPLEMENTAR ao
    consenso temporal — nunca substituta. A REGRA dele mudou em 31/08 e a
    razao inteira, com os numeros de campo, esta em `julgar_as_duas_escalas`:
    em resumo, ABSTENCAO DE UMA ESCALA NAO E DESACORDO (a regra antiga
    descartava 3 de 4 leituras boas), e duas duracoes DIFERENTES continuam
    barradas. Os dois cruzamentos pegam falhas de classes diferentes, e guardar
    so um deixaria uma classe inteira descoberta:

    - Cruzar ESCALAS pega ERRO DE METODO: o motor lendo mal a MESMA imagem.
      Medido em duas imagens reais: em COR o motor erra (le `MO-mi u` e
      `__40nin? es`), e em CINZA acerta de 2x para cima — mas em cinza 1x ele
      ABSTEM. Duas condicoes de leitura honestas chegaram a vereditos opostos
      sobre a MESMA fonte, que e a evidencia mais forte a favor desta guarda.
      O consenso temporal e CEGO a isso, porque duas leituras pelo mesmo
      metodo, com 5 s de intervalo, concordam no MESMO erro sistematico.
      Foi exatamente assim que "40 minutos e 26 segundos" viraria "26 segundos"
      com as duas leituras concordando.
      HOJE esse mesmo texto vira ABSTENCAO antes de chegar aqui, porque a
      guarda estrutural de `interpretar_banner` cala no lugar de cair para "so
      os segundos". E essa cobertura dupla que torna seguro tratar abstencao e
      contradicao de formas diferentes sem reabrir a porta.
    - Repetir no TEMPO pega ERRO DE FRAME: uma captura no meio do desenho do
      banner, um frame sujo, o jogo engasgando. O cruzamento de escalas e CEGO
      a isso, porque as duas escalas leem os MESMOS pixels.

    Custo de manter os dois: uma cadencia, 5 s numa contagem de 40 minutos.

    AS DUAS LEITORAS entram por PARAMETRO e as DUAS sao OBRIGATORIAS. E o que
    mantem este modulo sem OCR nenhum e o que permite os testes injetarem texto
    no Python da suite, que nao tem as bindings do WinRT.

    Obrigatorias, e nao opcionais com queda para uma so: a guarda de cruzamento
    e a razao de existir desta classe, e um argumento opcional convida a que ela
    fique desligada em silencio — que e o modo de falha que este recurso inteiro
    existe para evitar.

    O vigia segue sem saber o que "escala" significa. Ele recebe duas maneiras
    INDEPENDENTES de ler o mesmo recorte, e nada mais.
    """

    def __init__(
        self,
        ler_texto,
        ler_texto_conferencia,
        segundos_entre_leituras: float = SEGUNDOS_ENTRE_LEITURAS,
        tolerancia: timedelta = TOLERANCIA_DO_CONSENSO,
    ) -> None:
        self._ler_texto = ler_texto
        self._ler_texto_conferencia = ler_texto_conferencia
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

        A ORDEM E DELIBERADA: expirar, ler, registrar, montar. Montar por
        ultimo e a partir da ANCORA — nunca da leitura — e o que faz o aviso de
        5 minutos sair num tick em que o OCR nao leu nada.
        """
        self._expirar(agora)

        vencido = (
            self._ultima_leitura is None
            or (agora - self._ultima_leitura).total_seconds() >= self._intervalo
        )
        if vencido:
            self._ultima_leitura = agora
            pixels = obter_pixels()
            if pixels is not None:
                acordo = self._ler_com_as_duas_escalas(pixels, agora)
                if acordo is not None:
                    implicado, duracao = acordo
                    self._registrar(implicado, duracao)

        return self._avisos_devidos(agora)

    def _expirar(self, agora: datetime) -> None:
        """Esquece a manutencao depois que o momento passou, com folga (D-10).

        LIMPAR `_emitidos` AQUI E OBRIGATORIO. Sem isso a proxima manutencao de
        verdade seria detectada, ancorada — e nunca anunciada, porque o vigia
        acharia que ja tinha avisado. E o pior modo de falha deste projeto,
        porque de fora ele parece estar funcionando.
        """
        if self._ancora is None:
            return
        if agora <= self._ancora + FOLGA_APOS_A_MANUTENCAO:
            return
        self._ancora = None
        self._candidata = None
        self._duracao_confirmada = None
        self._emitidos.clear()

    def _ler(self, leitora, pixels) -> str | None:
        """Cinto E suspensorio: `ocr.ler_texto` ja promete nao levantar.

        A promessa nao basta porque este vigia roda DENTRO do tick de captura,
        e uma excecao aqui pararia o scanner de olhar a party — o unico defeito
        que este projeto trata como inaceitavel.

        AS DUAS leitoras passam por aqui. A protecao vale para a cara tambem:
        ela e a que roda menos e a que menos foi exercitada em campo.
        """
        try:
            return leitora(pixels)
        except Exception:
            return None

    def _ler_com_as_duas_escalas(self, pixels, agora: datetime):
        """O veredito de D-d, dentro do tick. Devolve (implicado, duracao) ou None.

        A DECISAO NAO MORA AQUI, e isso e o conserto de 31/08: ela mora em
        `julgar_as_duas_escalas`, que e pura e publica, e o `--testar-manutencao`
        chama a MESMA funcao. Enquanto a ferramenta tinha logica propria ela
        divergiu e passou a mentir sobre o proprio diagnostico.

        A ORDEM IMPORTA, mas NAO POR ORCAMENTO — e vale dizer, porque a razao
        antiga caiu. A passada de deteccao custa 23 ms e a de conferencia 31 ms
        (medidos na banda de producao, ja aquecidos): rodar as duas sempre
        caberia folgado no tick. O que a ordem preserva e DIVERSIDADE DE
        METODO — duas leituras independentes dos MESMOS pixels, uma podendo
        contradizer a outra — e a disciplina de nao gastar trabalho para ler o
        chao quando nao ha banner nenhum na tela.

        QUALQUER REPROVACAO DEVOLVE None SEM TOCAR EM `_candidata` NEM NA
        ANCORA. Uma reprovacao nao confirma e tambem nao destroi: se ela
        zerasse a candidata, um unico frame ruim no meio de uma contagem de 40
        minutos adiaria o anuncio indefinidamente.
        """
        barato = self._ler(self._ler_texto, pixels)
        if not eh_banner_de_manutencao(barato):
            return None  # D-e: a cara nem e tocada

        caro = self._ler(self._ler_texto_conferencia, pixels)
        veredito = julgar_as_duas_escalas(barato, caro, self._tolerancia)
        self._registrar_veredito(veredito, barato, caro)
        if not veredito.anunciaria:
            return None

        return agora + veredito.duracao, veredito.duracao

    def _registrar_veredito(
        self, veredito: Veredito, barato: str | None, caro: str | None
    ) -> None:
        """O banner ESTA na tela: nada aqui pode ser silencioso.

        DOIS NIVEIS, e a fronteira entre eles e "isto anuncia?":

        - NAO anuncia -> `warning`. E o estado mais perigoso deste recurso: o
          aviso estava escrito na tela e a party nao vai saber. Vai junto o
          conselho de onde mexer, porque a pergunta seguinte do usuario e
          sempre essa.
        - Anuncia com UMA escala so -> `info`. Caminho novo de 31/08, aceito
          com razao medida (a conferencia acertou 4 de 4), e mesmo assim o log
          registra que a ancora nasceu de uma escala so. Se um dia ela nascer
          errada, esta linha e a unica forma de descobrir por onde entrou.
        - Anuncia com as duas de acordo -> silencio. E o caminho normal.

        Os DOIS textos crus, entre delimitadores visiveis, porque espaco em
        branco importa aqui: `40 minutes` e `40minutes` sao leituras
        diferentes. E o log rotativo (5 MB x 3) e a unica ferramenta de forense
        pos-farm do projeto — sem estas linhas, "por que nao avisou" nao tem
        resposta em lugar nenhum.

        ESCOLHA DELIBERADA: NAO ha limitacao de repeticao. Durante uma contagem
        de 40 minutos isto pode render centenas de linhas, e sao exatamente as
        linhas que o usuario vai precisar.
        """
        if veredito.motivo is MotivoDoVeredito.ACORDO:
            return
        if veredito.anunciaria:
            log.info(
                "%s deteccao=>>>%s<<< conferencia=>>>%s<<<",
                veredito.explicacao,
                barato,
                caro,
            )
            return
        log.warning(
            "%s %s deteccao=>>>%s<<< conferencia=>>>%s<<<",
            veredito.explicacao,
            CONSELHO_QUANDO_NAO_ANUNCIA,
            barato,
            caro,
        )

    def _registrar(self, implicado: datetime, duracao: timedelta) -> None:
        """Aplica o consenso de D-05 a uma leitura bem sucedida.

        Tres situacoes, e a do meio e a que protege o usuario:

        - JA ANCORADO E DENTRO DA TOLERANCIA -> re-ancora. E a mesma
          manutencao, so que medida mais perto do fim: a leitura mais recente e
          a mais precisa (D-04). `_emitidos` fica intacto, senao o grupo
          receberia o mesmo anuncio a cada 5 s.
        - JA ANCORADO E FORA DA TOLERANCIA -> NAO move a ancora. Uma leitura so
          nunca derruba um horario ja confirmado por duas. Se DUAS leituras
          seguidas concordarem no horario novo, e uma manutencao REMARCADA e ai
          sim a ancora troca, com `_emitidos` zerado — a ancora velha nao pode
          prender o vigia num horario que nao existe mais.
        - SEM ANCORA -> a segunda leitura concordante confirma. E a porta de
          D-05: um digito comido pelo OCR sozinho nunca anuncia nada.
        """
        if self._ancora is not None:
            if self._bate(implicado, self._ancora):
                self._ancora = implicado
                self._duracao_confirmada = duracao
                self._candidata = None
                return
            if self._candidata is not None and self._bate(implicado, self._candidata):
                self._ancora = implicado
                self._duracao_confirmada = duracao
                self._candidata = None
                self._emitidos.clear()
                return
            self._candidata = implicado
            return

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

        restante = self._ancora - agora
        if (
            restante <= ANTECEDENCIA
            and TipoDeAvisoDeManutencao.FALTAM5 not in self._emitidos
        ):
            self._emitidos.add(TipoDeAvisoDeManutencao.FALTAM5)
            avisos.append(
                AvisoDeManutencao(
                    tipo=TipoDeAvisoDeManutencao.FALTAM5,
                    momento=self._ancora,
                    texto=texto_de_5_minutos(self._ancora, max(timedelta(0), restante)),
                )
            )

        return avisos
