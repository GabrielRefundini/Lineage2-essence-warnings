"""Aprender sozinho a assinatura de quem o scanner nunca viu.

POR QUE ESTE MODULO CONTA LEITURAS E NAO SEGUNDOS

O tick nao e garantido. A captura mira ~1 Hz, mas um frame doente, uma cegueira
ou uma varredura de mercado mudam o intervalo real, e "N segundos" viraria uma
dependencia de RELOGIO dentro da unica logica nova desta fase. Contando
leituras, um `--replay` de uma sessao gravada produz o MESMO acervo que a sessao
ao vivo produziu, que e a propriedade que torna esta fase depuravel sem morrer
no jogo de novo.

Este modulo nao tem relogio nenhum — nem `datetime.now()`, nem `time.time()` — e
a proibicao esta presa pelo portao AST de `tests/test_presenca.py`, ao lado de
`agenda`, `loot`, `presenca`, `bosses`, `respawn` e `acervo`.

POR QUE A ESTABILIDADE E JULGADA SOBRE A MASCARA E NUNCA SOBRE OS PIXELS CRUS

O texto do nome e opaco e o painel da party window e SEMITRANSPARENTE. O cenario
que anda por tras muda os pixels crus a cada frame e nao muda a mascara —
`identidade.mascara_de_texto` e so um piso de brilho (`V > 180`). Julgar por
pixel cru seria julgar o CENARIO: num campo aberto de dia o candidato nunca
seria estavel, e a feature simplesmente nao aconteceria, sem erro em lugar
nenhum e sem uma linha de log dizendo por que.

O QUE A CINTILACAO E, MEDIDO EM 2026-09-01, E O QUE ELA NAO E

A mascara nao sai identica entre dois frames, e por dois anos a hipotese
corrente para isso foi "o cenario esta vazando pela mascara, entao sobe o
`identidade.VALOR_MINIMO_DO_TEXTO`". Ela circulou em duas sessoes de trabalho e
esta ERRADA. Fica escrita aqui, com a medida que a derruba, porque uma hipotese
plausivel e nao registrada volta na terceira sessao.

Medido contra a tela real do usuario, 12 frames consecutivos com 1 s de
intervalo, party estavel, mascara de 2200 celulas:

    linha   px de texto   distancia entre frames: min / MEDIANA / max
      0         165                 3   /   8   /  25
      1         123                 0   /   2   /  31
      2         105                 1   /   3   /  99
      3         106                 0   /   0   / 176

E a NATUREZA dessa variacao, medida com `cv2.distanceTransform` sobre o nucleo
estavel dos 8 primeiros frames, perguntando a que distancia em pixels cada
celula cintilante esta do texto que nao cintila:

    linha 0: 23 celulas cintilantes, 23 delas (100%) COLADAS no texto (<= 1.5 px)
    linha 2: 17 celulas cintilantes, 10 (59%) coladas, 5 longe (> 3 px)

Cem por cento colado na linha 0 nao e cenario vazando: e SERRILHADO na borda das
letras, o anti-aliasing do proprio glifo oscilando em volta do piso de brilho.
Subir o `VALOR_MINIMO_DO_TEXTO` para caca-lo comeria texto de verdade e pioraria
o reconhecimento. O limiar 180 esta CERTO e nao e o que precisa mudar; o que
precisava mudar era a mensagem que o usuario le quando isso acontece.

A OUTRA COISA QUE A MEDIDA SEPAROU: DOIS REGIMES, E SO UM DELES E CONFIGURAVEL

As medianas em regime estavel ficam entre 0 e 8 celulas. A mediana de 298.5
relatada em 2026-08-31 nao pertence a essa familia: foi medida com a party se
remontando apos um disconnect. Uma e a mesma pessoa cintilando e a tolerancia
resolve; a outra sao recortes de gente diferente, e nenhuma tolerancia conserta.
O discriminante entre os dois NAO e um numero novo: e o proprio
`TETO_DE_CELULAS_TOLERADAS`, porque acima dele o reconhecedor ja considera as
duas leituras pessoas diferentes. As duas medidas de campo caem uma de cada lado
do 12 com folga (8 contra 298.5), que e o que faz do teto um discriminante
medido em vez de uma constante escolhida. Ver `retrato_das_distancias`.

POR QUE A GRAVACAO PREFERE NAO ACONTECER QUANDO HA DUVIDA

O acervo e IRREVERSIVEL no v1: nao ha comando de esquecer (decisao da Fase 1 —
o usuario viu os 562 bytes por assinatura e dispensou a limpeza). Uma pessoa nao
aprendida custa um "Membro N" no console; uma entrada de lixo gravada fica para
sempre, conta na linha de arranque, e ainda pode SOMBRAR gente de verdade pela
margem — e uma pessoa sombreada para de ser reconhecida em silencio.

O QUE ESTE MODULO NAO CONHECE

Ele nao importa `visao`, `sessao`, `rastreador` nem `calibracao`. Fala
`Assinatura` e `AcervoDeIdentidades`, e so — o mesmo isolamento que o `acervo`
conquistou. Quem sabe o que e uma linha da party window e o `sessao`, e e la que
a candidatura por `COM_MEMBRO` e por `ui_visivel` mora (D-01).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from .acervo import AcervoDeIdentidades, chave_da_assinatura
from .identidade import LIMIAR_DE_CASAMENTO, PIXELS_MINIMOS_DE_TEXTO, Assinatura

# Quantas leituras seguidas com o recorte estavel bastam para gravar.
#
# O NUMERO E DERIVADO DO QUE O PROJETO JA MEDIU, E NAO ESCOLHIDO NO OLHO.
# `rastreador.Ajustes` tem duas familias de confirmacao, e a docstring dele
# chama isso de histerese assimetrica: as direcoes BARATAS de reverter custam 3
# leituras (`confirmacoes_para_morte`, `confirmacoes_para_entrada`) e as CARAS
# custam 5 (`confirmacoes_para_ressurreicao`, `confirmacoes_para_saida`).
#
# Gravar num acervo irreversivel e a direcao cara POR DEFINICAO — nao existe
# desfazer — entao ela paga o preco da familia cara. A ~1 Hz sao ~5 segundos:
# quem vai ficar horas na party espera cinco segundos, e uma linha que pisca por
# quatro leituras nunca chega a ser gravada.
LEITURAS_PARA_APRENDER = 5

# O maior `celulas_toleradas` que ainda nao mistura duas pessoas numa mesma
# assinatura. DERIVADO da medida da Fase 1, e nao escolhido.
#
# A tolerancia diz "estas duas leituras sao a MESMA pessoa". O reconhecedor
# tambem responde essa pergunta, e as duas respostas nao podem se contradizer:
# uma tolerancia MAIOR do que o ponto em que o RECONHECEDOR passa a distinguir
# duas mascaras chamaria de estaveis duas leituras que ele considera pessoas
# diferentes, e a assinatura gravada seria uma media de duas pessoas.
#
# Medido na Fase 1 (`tests/test_acervo.py`, bloco de `BITS_VIRADOS`), virando
# bits de uma mascara `20x100` — 2000 celulas, com 48 PIXELS DE TEXTO:
#
#     celulas viradas   calibrada   copia    margem    desfecho
#            1            1.0000    0.9895   0.0105    SILENCIO
#            3            1.0000    0.9694   0.0306    SILENCIO
#            8            1.0000    0.9212   0.0788    SILENCIO
#           12            1.0000    0.8879   0.1121    SILENCIO
#           20            1.0000    0.8306   0.1694    o nome SAI
#           40            1.0000    0.7237   0.2763    o nome SAI
#
# Em 12 celulas o reconhecedor ainda se RECUSA a distinguir as duas (margem
# 0.1121, abaixo dos 0.12 de `MARGEM_MINIMA_SOBRE_O_SEGUNDO`); em 20 ele ja
# distingue (margem 0.1694). A transicao esta entre 12 e 20, e 12 e o maior
# ponto MEDIDO que ainda cai do lado seguro. O teto e esse numero, e nao um
# arredondamento dele: se um dia a medicao for refeita com mais pontos, e a
# MEDICAO que muda o teto.
#
# A CONDICAO DE VALIDADE, E ELA NAO PODE FICAR DE FORA.
#
# Os 48 pixels de texto sao a BASE da medida, e nao um detalhe da fixture. Doze
# celulas sao 25% do sinal DAQUELA mascara; num nick curto, com 20 pixels de
# texto, as mesmas 12 celulas sao 60% do sinal e destroem a assinatura muito
# antes de o reconhecedor chegar perto da faixa medida. Ou seja: este teto e um
# limite superior aferido num nome de tamanho MEDIO, e nao uma propriedade
# universal do reconhecedor. Ele protege contra o erro grosseiro — uma
# tolerancia de 30, de 50 celulas — e nao promete seguranca para todo nick em
# toda tolerancia abaixo dele. Quem subir a tolerancia perto do teto com uma
# party de nicks curtos esta fora da faixa em que a medida foi feita.
#
# Refazer a medida por faixa de pixels de texto e o caminho honesto quando
# houver gravacao multi-frame de campo; ate la, o default continua sendo zero.
TETO_DE_CELULAS_TOLERADAS = 12

# Os dois regimes de instabilidade, separados pelo TETO e nao por um numero novo.
#
# `CINTILACAO` e o serrilhado da borda das letras: mediana medida de 0 a 8
# celulas nas quatro linhas da tela real (ver a medicao de 2026-09-01 no topo
# deste arquivo). Ele e normal, acontece em party parada, e a tolerancia existe
# exatamente para absorve-lo.
#
# `TURBULENCIA` e tudo que passa do teto: a party se remontando apos um
# disconnect (mediana 298.5 medida em 2026-08-31), uma cegueira, o inventario
# aberto por cima. Acima do teto o RECONHECEDOR ja trata as duas leituras como
# pessoas diferentes, entao chamar isso de "a mesma pessoa cintilando" seria
# contradize-lo. Nenhuma tolerancia legal conserta este regime, e a resposta
# certa e ESPERAR, nao configurar. Mandar o usuario configurar aqui foi o
# defeito consertado em 2026-09-01.
REGIME_DE_CINTILACAO = "cintilacao"
REGIME_DE_TURBULENCIA = "turbulencia"


class ToleranciaAlemDoTeto(Exception):
    """A configuracao pediria assinaturas de duas pessoas misturadas.

    Recusada NO ARRANQUE, com mensagem e sem traceback, no precedente de
    `BossInvalido` e de `ConfiguracaoPerigosa`: subir com ela seria pior do que
    nao subir, porque o estrago vai para um acervo IRREVERSIVEL e so aparece
    depois, como uma pessoa que parou de ser reconhecida em silencio.
    """


@dataclass(frozen=True)
class AjustesDoAprendiz:
    """Os dois numeros que governam o aprendizado.

    `celulas_toleradas` NASCE ZERO, e o zero e a decisao (D-05). Quando a fase
    foi escrita a razao era a AUSENCIA de medida: nao existia gravacao
    multi-frame da party no repositorio, so imagens soltas, e adotar uma
    tolerancia inventada seria adotar exatamente o tipo de constante que este
    projeto proibe.

    A MEDIDA CHEGOU EM 2026-09-01, E O ZERO FICOU. A razao mudou, e por isso ela
    esta reescrita aqui em vez de apagada. As duas metades, em voz alta:

    CONTRA O ZERO, e o argumento e forte. As medianas medidas na tela real sao
    8, 2, 3 e 0 celulas nas quatro linhas (a tabela esta no topo deste arquivo).
    Com tolerancia zero, "a mesma leitura" quer dizer a mesma chave de conteudo,
    EXATAMENTE, e tres das quatro linhas nunca fecham cinco leituras iguais
    seguidas. Ou seja, hoje o aprendizado dispara por SORTE, e nao por desenho.

    A FAVOR DO ZERO, e o que decidiu. Tres razoes, em ordem de peso:

    1. A medida e de UMA maquina, UMA sessao, UMA party, 12 frames. O default
       vai para toda instalacao. A amplitude do serrilhado depende da fonte, do
       `Gamma`, da resolucao, da escala do Windows e do comprimento do nick, e
       ela ja variou 4x ENTRE AS QUATRO LINHAS DA MESMA TELA (mediana 0 na linha
       3, mediana 8 na linha 0). Um default tirado dai e precisamente a
       "constante que so vale na maquina de quem mediu" que este projeto proibe
       em todo lugar (ver os limiares de HSV no `calibration.json`).

    2. Os dois modos de falha sao ASSIMETRICOS, e so um deles fala. Default
       baixo demais: a feature nao dispara, o `scanner.log` diz isso com numero
       e com a linha pronta para copiar, o usuario sobe e resolve. Custo: um
       "Membro N" por uma sessao. Default alto demais na maquina de outra
       pessoa: entra uma assinatura no acervo IRREVERSIVEL, sem comando de
       esquecer, e o estrago aparece semanas depois como alguem que parou de ser
       reconhecido em silencio. Quando uma direcao se anuncia e a outra nao, o
       default fica do lado que se anuncia.

    3. A condicao de validade do teto vale para o default tambem. Os 12 foram
       aferidos numa mascara com 48 pixels de texto; as linhas medidas hoje tem
       105 a 165 px. Num nick curto as mesmas celulas sao uma fracao MAIOR do
       sinal, e um default nao-zero levaria a medida para fora da faixa em que
       ela foi feita, sem ninguem pedir.

    O QUE PAGA A CONTA DO ZERO e a mensagem, e nao a esperanca. O numero certo
    para a maquina do usuario sai do `scanner.log` da primeira sessao real: toda
    recusa registra a DISTANCIA MEDIDA, e desde 2026-09-01 o resumo entrega um
    valor CONCRETO, ja conferido contra o teto, na forma de uma linha pronta
    para copiar. E o circuito de D-07 fechado: o modo de falha de um default
    conservador e auto-diagnostico, e nao silencio. Ver `resumo_das_recusas`.

    REABRIR ISTO PEDE DADO NOVO, e o dado tem nome: a mesma medicao de 12 frames
    feita em pelo menos duas maquinas diferentes, com nicks de comprimentos
    diferentes. Ate la, mexer no default e trocar uma falha que fala por uma que
    cala.
    """

    leituras_para_aprender: int = LEITURAS_PARA_APRENDER
    celulas_toleradas: int = 0

    def __post_init__(self) -> None:
        """A validacao mora AQUI, e nao no leitor do `config.toml`.

        O teto nao e uma pergunta de sintaxe de arquivo: e uma propriedade
        MEDIDA do reconhecedor, e ela tem de valer para TODO caminho de
        construcao — inclusive um teste, um script ou um chamador futuro que
        nunca encoste no `config.toml`. Validar so na leitura deixaria a porta
        aberta para todos os outros.

        As mensagens sao para o USUARIO: portugues sem acento, sem travessao,
        dizendo o valor recebido, o limite, a unidade e o que fazer.
        """
        if self.celulas_toleradas < 0:
            raise ToleranciaAlemDoTeto(
                f"[identidade] celulas_toleradas = {self.celulas_toleradas} nao "
                "faz sentido: a unidade e CELULA da mascara do nome, e um "
                "numero de celulas nunca e negativo. Use 0 (o padrao) para "
                "exigir leituras identicas."
            )
        if self.celulas_toleradas > TETO_DE_CELULAS_TOLERADAS:
            raise ToleranciaAlemDoTeto(
                f"[identidade] celulas_toleradas = {self.celulas_toleradas} "
                f"passa do teto de {TETO_DE_CELULAS_TOLERADAS} celulas da "
                "mascara do nome. Acima dele o proprio reconhecedor ja trata as "
                "duas leituras como pessoas DIFERENTES, e a assinatura gravada "
                "seria a media de duas pessoas, num acervo que nao tem comando "
                f"de esquecer. Use um valor de 0 a {TETO_DE_CELULAS_TOLERADAS}."
            )
        if self.leituras_para_aprender < 1:
            raise ToleranciaAlemDoTeto(
                f"[identidade] leituras_para_aprender = "
                f"{self.leituras_para_aprender} nao pode ser menor que 1: com "
                "zero o scanner gravaria a assinatura no PRIMEIRO frame, sem "
                "nenhuma confirmacao de que a leitura e estavel. O padrao e "
                f"{LEITURAS_PARA_APRENDER} leitura(s)."
            )


@dataclass(frozen=True)
class Candidata:
    """Uma linha que o scanner esta vendo e nao sabe de quem e.

    O `indice` viaja SO PARA O DIAGNOSTICO — e o que faz a linha de log de D-07
    poder dizer QUAL linha recusou. Ele NUNCA entra em decisao nenhuma: a party
    window compacta quando alguem sai, e a linha 2 de agora pode ser outra
    pessoa daqui a um tick. O contador de estabilidade e por CONTEUDO (D-08), e
    um contador por indice somaria leituras de pessoas diferentes ate atingir N
    e gravaria uma assinatura de ninguem.
    """

    indice: int
    mascara: np.ndarray
    confianca: float


@dataclass(frozen=True)
class Aprendizado:
    """Uma entrada que ESTE tick fez existir no acervo.

    Estruturado, e nao texto, pelo mesmo motivo que `ResultadoDoTick.despachos`
    e estruturado: o teste afirma estrutura, e a redacao muda toda vez que
    alguem a melhora.

    O CAMPO `confianca` NAO E ENFEITE. Ele e a melhor pontuacao que aquela linha
    teve contra tudo que o scanner ja conhecia no instante em que decidiu
    aprender. Ele existe porque D-02 so guarda UMA das duas fronteiras: veta
    acima do limiar, e nao tem nada a dizer sobre uma pessoa que volta
    correlacionando 0.70 contra a propria entrada ja gravada. Nesse caso ela E
    candidata, uma SEGUNDA entrada da mesma pessoa nasce, e as duas depois se
    sombreiam pela margem.

    Nao ha medida de campo do drift entre sessoes para fechar essa porta agora
    (e por isso que a tolerancia nasce em zero), entao o que esta fase pode fazer
    e o mesmo que D-07 faz pela recusa: gravar o NUMERO junto do fato. Uma
    sequencia de aprendizados com confianca em torno de 0.70 e a assinatura
    desse caso; sem o numero no log ele e invisivel. Um aprendizado sem confianca
    registrada, num acervo irreversivel, tem como unico modo de falha o
    silencio. Ver T-02-18 no plano 02-02.
    """

    chave: str
    indice: int
    desfecho: str
    assinatura: Assinatura
    confianca: float


@dataclass(frozen=True)
class RecusaPorInstabilidade:
    """Uma leitura que NAO continuou a sequencia, com a distancia que mediu.

    Sem este numero, o desfecho de um `celulas_toleradas` errado e a feature
    simplesmente NAO ACONTECER, em silencio, sem nada no log dizendo por que. O
    default e zero porque esta fase nao tem medicao de campo do ruido entre
    frames consecutivos — nao existe gravacao multi-frame da party no
    repositorio, so imagens soltas — e inventar uma tolerancia seria adotar
    exatamente o tipo de constante que este projeto proibe.

    Registrar a distancia MEDIDA troca esse silencio por auto-diagnostico: o
    `scanner.log` da primeira sessao real diz, com numero, o quanto as leituras
    diferem entre si, e o usuario sobe a tolerancia com um numero medido em vez
    de tentar valores. E por isso que isto e requisito de plano, e nao um "nice
    to have": ele substitui uma ferramenta de spike que nao foi escrita.

    `distancia` e `None` quando nao havia nenhum vigia de FORMA IGUAL para
    comparar. Forma diferente nao e "muito diferente": e uma pergunta sem
    sentido, porque as duas mascaras nao descrevem o mesmo retangulo de tela.
    """

    indice: int
    distancia: int | None
    tolerado: int


@dataclass(frozen=True)
class RetratoDasRecusas:
    """A faixa das distancias medidas nesta sessao, para uma linha de log.

    A MEDIANA entra ao lado do minimo e do maximo porque um unico outlier — um
    frame com o inventario passando por cima do nome — esticaria o maximo e
    faria o usuario escolher uma tolerancia grande demais. O par (minimo,
    mediana) e o que descreve o ruido normal.

    OS QUATRO CAMPOS DE BAIXO NASCERAM DO DEFEITO DE 2026-09-01, e cada um
    responde a uma pergunta que a faixa sozinha nao respondia:

    `medidas` e quantas recusas tinham distancia. Ele nao e igual a `recusas`:
    uma recusa por FORMA diferente nao mede distancia nenhuma, e usar o total
    como denominador faria a fracao mentir para baixo.

    `abaixo_do_teto` e o numero que DECIDE se vale mexer. Se 90 de 104 recusas
    cabem no teto, subir a tolerancia resolve; se 1 de 6 cabe, subir nao
    resolve, e o usuario precisa ler isso em vez de tentar valores no escuro.

    `sugestao` e um valor CONCRETO que o `__post_init__` aceita, ou `None`. E a
    correcao literal do defeito: a mensagem antiga mandava escolher "um valor
    dentro dessa faixa" numa faixa que ia ate 1067, e o teto e 12, entao quase
    toda obediencia levantava `ToleranciaAlemDoTeto` no arranque seguinte.

    `regime` e em qual dos dois mundos o usuario esta, `REGIME_DE_CINTILACAO` ou
    `REGIME_DE_TURBULENCIA`. Sem ele a mesma mensagem serviria para "sobe a
    tolerancia e resolve" e para "espera a party parar", que sao conselhos
    opostos. Vale `None` quando nao houve distancia nenhuma para medir.
    """

    recusas: int = 0
    menor: int | None = None
    maior: int | None = None
    mediana: float | None = None
    medidas: int = 0
    abaixo_do_teto: int = 0
    sugestao: int | None = None
    regime: str | None = None


def _mediana(ordenadas: Sequence[int]) -> float:
    """A mediana de uma sequencia JA ORDENADA e nao vazia."""
    meio = len(ordenadas) // 2
    if len(ordenadas) % 2:
        return float(ordenadas[meio])
    return (ordenadas[meio - 1] + ordenadas[meio]) / 2


def retrato_das_distancias(
    distancias: Sequence[int], recusas: int
) -> RetratoDasRecusas:
    """Le a faixa medida e decide o que dizer ao usuario. Pura, sem relogio.

    O REGIME SAI DO TETO, E NAO DE UM LIMIAR NOVO. `TETO_DE_CELULAS_TOLERADAS`
    ja e o ponto em que o RECONHECEDOR passa a tratar duas mascaras como pessoas
    diferentes. Uma mediana acima dele, portanto, nao pode ser descrita como "a
    mesma pessoa cintilando" sem contradizer o reconhecedor. Usar qualquer outro
    numero aqui seria inventar uma constante para dizer o que o teto ja diz.

    As duas medidas de campo caem uma de cada lado com folga: 8 celulas de
    mediana em party parada (2026-09-01) e 298.5 com a party se remontando apos
    um disconnect (2026-08-31). O teto de 12 separa as duas sem encostar em
    nenhuma, que e o que torna o corte medido em vez de escolhido.

    A SUGESTAO SAI DA MEDIANA DAS RECUSAS QUE CABEM NO TETO, e nao da mediana de
    todas. Na linha 0 medida hoje as distancias vao de 3 a 25: os 20 e os 25 sao
    frames com algo por cima do nome, e nao a cintilacao que a tolerancia existe
    para absorver. Incluir os outliers empurraria a sugestao contra o teto sem
    ganhar nada, e a folga ate o teto e a unica margem que protege um nick curto
    (ver a condicao de validade em `TETO_DE_CELULAS_TOLERADAS`).

    O ARREDONDAMENTO E PARA CIMA porque a sugestao precisa TOLERAR a leitura
    mediana, e nao empatar com ela: com mediana 5.5, um valor 5 recusaria
    metade das leituras que a sugestao existe para aceitar.

    NA TURBULENCIA A SUGESTAO E `None`, DE PROPOSITO. Mesmo quando algumas
    recusas cabem no teto, entregar um valor ali seria repetir o defeito com
    outra redacao: o usuario copiaria o numero, o aprendizado continuaria nao
    acontecendo, e ele voltaria a perguntar. Um campo que so tem valor quando o
    valor RESOLVE e um campo que o chamador nao consegue usar errado.
    """
    ordenadas = sorted(distancias)
    if not ordenadas:
        return RetratoDasRecusas(recusas=recusas)

    mediana = _mediana(ordenadas)
    cabem = [d for d in ordenadas if d <= TETO_DE_CELULAS_TOLERADAS]
    cintila = mediana <= TETO_DE_CELULAS_TOLERADAS

    return RetratoDasRecusas(
        recusas=recusas,
        menor=ordenadas[0],
        maior=ordenadas[-1],
        mediana=mediana,
        medidas=len(ordenadas),
        abaixo_do_teto=len(cabem),
        sugestao=math.ceil(_mediana(cabem)) if cintila and cabem else None,
        regime=REGIME_DE_CINTILACAO if cintila else REGIME_DE_TURBULENCIA,
    )


def resumo_das_recusas(retrato: RetratoDasRecusas, tolerado: int) -> str:
    """A linha que o usuario le no `scanner.log`. Sem acento e sem travessao.

    O DEFEITO QUE ESTE TEXTO CONSERTA, escrito por extenso porque a redacao
    antiga parecia certa: ela terminava em "suba [identidade] celulas_toleradas
    para um valor dentro dessa faixa", e a faixa relatada em campo ia de 1 a
    1067 celulas. O teto aceito e 12. Quase todo valor "dentro dessa faixa"
    levantava `ToleranciaAlemDoTeto` no arranque seguinte, e o usuario que
    obedeceu a mensagem teve de vir perguntar o que fazer.

    TRES COISAS MUDARAM, e cada uma tem um caso em `tests/test_aprendiz.py`:

    1. O TETO APARECE JUNTO DA FAIXA, com quantas das recusas medidas cabem
       embaixo dele. Esse segundo numero e o que decide se vale mexer, e a faixa
       sozinha nunca o dava.
    2. O TEXTO ENTREGA UM VALOR, ja conferido contra o teto, na forma de uma
       linha pronta para copiar. E o idioma de `_EXEMPLO_DA_IDENTIDADE` no
       `config.py`: uma mensagem que diz "escolha um numero" faz adivinhar, uma
       que mostra a linha pronta e copiada.
    3. NA TURBULENCIA ELE NAO ENTREGA VALOR NENHUM, e diz por que. Nesse regime
       a acao certa e esperar a party estabilizar; qualquer numero aqui seria
       uma obediencia que nao conserta nada.
    """
    cabeca = (
        f"Nao aprendi assinatura nova por instabilidade: {retrato.recusas} "
        "recusa(s) nesta sessao, "
    )

    if retrato.menor is None or retrato.mediana is None:
        return (
            cabeca + "sem distancia medida ainda (as leituras tinham formas "
            f"diferentes), e a tolerancia atual e {tolerado}. Forma diferente "
            "nao e uma distancia grande: sao recortes de retangulos diferentes, "
            "e a distancia entre eles nao existe. Nenhum valor de [identidade] "
            "celulas_toleradas muda isso, e nao ha o que ajustar com esta linha."
        )

    faixa = (
        f"as leituras diferem de {retrato.menor} a {retrato.maior} celula(s), "
        f"mediana {retrato.mediana:.1f}, e a tolerancia atual e {tolerado}. "
    )
    teto = (
        f"{retrato.abaixo_do_teto} das {retrato.medidas} recusa(s) medidas "
        f"cabem no teto de {TETO_DE_CELULAS_TOLERADAS} celula(s), que e a maior "
        "tolerancia que o reconhecimento aceita sem juntar duas pessoas numa "
        "assinatura so. "
    )

    if retrato.regime == REGIME_DE_CINTILACAO:
        acao = (
            "Isso e cintilacao da borda das letras, e a tolerancia resolve. "
            "Escreva no config.toml, na secao [identidade], esta linha: "
            f"celulas_toleradas = {retrato.sugestao} "
            "(numero medido na SUA tela, e nao um palpite, e ja conferido "
            "contra o teto)."
        )
    else:
        acao = (
            "Subir [identidade] celulas_toleradas NAO resolve o seu caso: uma "
            f"mediana de {retrato.mediana:.1f} celula(s) passa do teto, e nessa "
            "distancia o proprio reconhecimento ja trata as duas leituras como "
            "pessoas DIFERENTES. Isso nao e cintilacao da borda das letras: e a "
            "party se remontando, uma cegueira ou o inventario aberto por cima "
            "do nome. A resposta certa e esperar a party estabilizar e ler esta "
            "linha de novo, e nao mexer no config.toml."
        )

    return cabeca + faixa + teto + acao


@dataclass(frozen=True)
class ResultadoDoAprendiz:
    """O que uma leitura produziu. As duas listas VAZIAS sao o estado normal."""

    aprendizados: list[Aprendizado] = field(default_factory=list)
    recusas: list[RecusaPorInstabilidade] = field(default_factory=list)


def distancia_de_hamming(a: np.ndarray, b: np.ndarray) -> int | None:
    """Em quantas CELULAS as duas mascaras diferem, ou `None` se nem da.

    A unidade e a celula porque e a unidade em que a unica medida que este
    projeto tem foi feita: 8 e 12 celulas viradas numa mascara de 2000 (Fase 1,
    bloco `BITS_VIRADOS` de `tests/test_acervo.py`). Comparar contra ela e
    comparar contra o perigo real, e nao contra uma fracao inventada.

    FORMA DIFERENTE DEVOLVE `None`, e nao um numero grande. "Muito diferente"
    seria uma resposta errada com cara de certa: duas mascaras de retangulos
    diferentes nao sao duas leituras da mesma coisa, e a distancia entre elas
    nao existe.
    """
    if a.shape != b.shape:
        return None
    return int(np.count_nonzero(a != b))


@dataclass
class _Vigia:
    """Uma sequencia de leituras em andamento, chaveada pelo CONTEUDO.

    A `ancora` e a PRIMEIRA mascara da sequencia e nunca e atualizada. Ver
    `Aprendiz.observar` para a razao inteira.
    """

    ancora: np.ndarray
    leituras: int
    indice: int


class Aprendiz:
    """Grava sozinho a assinatura de quem ficou parado tempo suficiente.

    Recebe `Candidata`s — linhas que o `sessao` ja julgou candidatas por D-01 —
    e devolve o que aconteceu. Nao sabe o que e uma linha, um frame ou um tick.
    """

    def __init__(
        self,
        acervo: AcervoDeIdentidades,
        ajustes: AjustesDoAprendiz | None = None,
    ) -> None:
        self._acervo = acervo
        self._ajustes = ajustes or AjustesDoAprendiz()
        self._vigias: list[_Vigia] = []
        self._distancias: list[int] = []
        self._recusas = 0

    @property
    def ajustes(self) -> AjustesDoAprendiz:
        return self._ajustes

    def retrato(self) -> RetratoDasRecusas:
        """O acumulado da sessao, ignorando as distancias que nao existem.

        A LEITURA MORA NA FUNCAO PURA, e nao aqui, porque ela precisa ser
        exercitada com as distancias MEDIDAS EM CAMPO sem montar um `Aprendiz`
        inteiro para chegar nelas. As duas medicoes que decidiram o desenho (a
        de 2026-09-01 e a turbulencia de 2026-08-31) entram em teste como duas
        tuplas de inteiros, que e a forma mais barata de nao perde-las.
        """
        return retrato_das_distancias(self._distancias, self._recusas)

    def observar(self, candidatas: Sequence[Candidata]) -> ResultadoDoAprendiz:
        """Uma leitura. Devolve o que gravou e o que recusou.

        A ORDEM DOS PORTOES E A REGRA, e cada um tem uma razao propria.

        1. RECORTE QUASE SEM TEXTO E DESCARTADO. O motivo nao e obvio:
           `identificar_linhas` devolve `Casamento(None, 0.0)` para uma linha sem
           texto suficiente, e `0.0` passa folgado na condicao de D-02. Pior,
           com a lista de assinaturas VAZIA — a instalacao nova, que e onde esta
           fase mais importa — `identificar_linhas` retorna cedo e o portao de
           pixel de `_pontuar_mascara` nem chega a rodar. O portao daqui e o
           UNICO que existe nesse caminho, e sem ele a primeira coisa que o
           scanner aprenderia numa instalacao nova seria uma linha vazia.

        2. CASAMENTO ACIMA DO LIMIAR E DESCARTADO (D-02). `Casamento(None, ...)`
           chega por DOIS motivos diferentes, que pedem desfechos opostos:

               melhor pontuacao < 0.75      "nao conheco ninguem parecido"  APRENDE
               >= 0.75 e sem margem         "conheco DOIS parecidos demais"  CALA

           Aprender no segundo caso e o pior desfecho deste workstream:
           acrescentar ao acervo um quase-duplicado de alguem faz essa pessoa
           PARAR de ser reconhecida — as duas assinaturas se sombreiam e as duas
           caem no silencio pela margem. Medido na Fase 1: virando 8 celulas, a
           original casa 1.000 e a copia 0.921, diferenca 0.079, ABAIXO dos 0.12
           de `MARGEM_MINIMA_SOBRE_O_SEGUNDO`.

        3. CASAMENTO COM O VIGIA MAIS PROXIMO DE FORMA IGUAL. Distancia
           `<= celulas_toleradas` conta como "a mesma leitura" e incrementa
           aquele vigia. Distancia maior RECUSA, e a candidata vira um vigia NOVO
           com contagem 1 — que e a forma exata de "instabilidade REINICIA a
           sequencia" de D-08. Nada de media e nada de mediana: uma assinatura
           media de duas leituras diferentes e uma assinatura de ninguem.

        4. VIGIAS QUE NINGUEM CASOU NESTA LEITURA SAO DESCARTADOS. Isso mantem a
           estrutura limitada pelo numero de linhas da party window (T-02-09) e e
           a outra metade do reinicio de D-08.

        5. VIGIA QUE CHEGOU A `leituras_para_aprender` GRAVA, com `nome=""`.

        A MASCARA GRAVADA E A ANCORA DA SEQUENCIA, E NAO A ULTIMA LEITURA. Com
        `celulas_toleradas` maior que zero, comparar cada leitura com a ANTERIOR
        deixaria uma deriva de uma celula por leitura somar N celulas ao longo da
        sequencia, e a sequencia seria chamada de estavel com a ultima leitura
        longe da primeira. Comparando com a ancora, a deriva total fica limitada
        pela propria tolerancia — que e o unico numero desta fase com um teto
        medido.

        UMA PRIMEIRA APARICAO NAO E UMA RECUSA. Quando nao havia vigia nenhum
        sobrando para comparar, a candidata simplesmente comeca uma sequencia:
        chamar isso de `RecusaPorInstabilidade` poria, no retrato de D-07, um
        evento que nao mediu instabilidade nenhuma — e o retrato existe
        justamente para o usuario ler a faixa real das distancias.
        """
        aprendizados: list[Aprendizado] = []
        recusas: list[RecusaPorInstabilidade] = []

        disponiveis = list(self._vigias)
        sobreviventes: list[_Vigia] = []
        tolerado = self._ajustes.celulas_toleradas

        for candidata in sorted(candidatas, key=lambda c: c.indice):
            if int(candidata.mascara.sum()) < PIXELS_MINIMOS_DE_TEXTO:
                continue
            if candidata.confianca >= LIMIAR_DE_CASAMENTO:
                continue

            havia_com_quem_comparar = bool(disponiveis)
            vigia, distancia = self._mais_proximo(disponiveis, candidata.mascara)

            if vigia is not None and distancia is not None and distancia <= tolerado:
                disponiveis.remove(vigia)
                vigia.leituras += 1
                vigia.indice = candidata.indice
            else:
                if havia_com_quem_comparar:
                    self._recusas += 1
                    if distancia is not None:
                        self._distancias.append(distancia)
                    recusas.append(
                        RecusaPorInstabilidade(
                            indice=candidata.indice,
                            distancia=distancia,
                            tolerado=tolerado,
                        )
                    )
                sobreviventes.append(
                    _Vigia(
                        ancora=candidata.mascara,
                        leituras=1,
                        indice=candidata.indice,
                    )
                )
                continue

            if vigia.leituras < self._ajustes.leituras_para_aprender:
                sobreviventes.append(vigia)
                continue

            aprendizado = self._gravar(vigia, candidata.confianca)
            if aprendizado is not None:
                aprendizados.append(aprendizado)
            # O vigia sai da mesa nos TRES desfechos. Em `criado` e em
            # `ja_existia` porque a entrada existe; em `falhou` porque a proxima
            # sequencia tem de comecar do zero, e nao repetir a gravacao a cada
            # tick para sempre.

        self._vigias = sobreviventes
        return ResultadoDoAprendiz(aprendizados=aprendizados, recusas=recusas)

    @staticmethod
    def _mais_proximo(
        vigias: list[_Vigia], mascara: np.ndarray
    ) -> tuple[_Vigia | None, int | None]:
        """O vigia de FORMA IGUAL mais perto desta mascara, e a distancia.

        Devolve `(None, None)` quando nenhum vigia tem a mesma forma — e o caso
        em que a distancia nao existe, e nao o caso em que ela e grande.
        """
        melhor: _Vigia | None = None
        menor: int | None = None
        for vigia in vigias:
            distancia = distancia_de_hamming(mascara, vigia.ancora)
            if distancia is None:
                continue
            if menor is None or distancia < menor:
                melhor, menor = vigia, distancia
        return melhor, menor

    def _gravar(self, vigia: _Vigia, confianca: float) -> Aprendizado | None:
        """Grava a ANCORA no acervo. `falhou` NAO conta como aprendido.

        `ja_existia` CONTA como sucesso, e a razao esta escrita na docstring de
        `acervo.gravar`: o usuario roda DUAS instancias (Yazalaque e Faerlina)
        sobre a mesma pasta, e o `O_CREAT|O_EXCL` decide a corrida. Tratar
        `ja_existia` como motivo para tentar de novo faria a instancia perdedora
        ficar tentando para sempre, e a entrada JA esta em disco — o objetivo foi
        cumprido, so nao por este processo.

        `falhou` e o oposto, e colapsa-lo em `criado` faria esta fase acreditar
        que aprendeu uma pessoa que nao esta em disco: ela pararia de ser
        candidata, ninguem perguntaria por ela na Fase 3, e ela ficaria anonima
        para sempre sem erro em lugar nenhum.
        """
        assinatura = Assinatura(nome="", mascara=vigia.ancora)
        desfecho = self._acervo.gravar(assinatura)
        if desfecho == "falhou":
            return None
        return Aprendizado(
            chave=chave_da_assinatura(assinatura),
            indice=vigia.indice,
            desfecho=desfecho,
            assinatura=assinatura,
            confianca=confianca,
        )
