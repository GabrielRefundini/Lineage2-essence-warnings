"""Extracao pura: de um frame + calibracao para uma observacao.

Esta camada nao tem relogio, nao tem rede, nao abre arquivo e nao decide nada.
Ela so olha os pixels e responde "o que esta na tela agora". Quem decide se
isso e uma morte e o rastreador, na camada de cima.

Essa separacao e o que torna 30 segundos de debounce testaveis em 0,2 ms.

TRES DESCOBERTAS DA CALIBRACAO REAL que moldam o codigo aqui:

1. **A parte vazia da barra e transparente** — mostra o terreno do jogo, nao um
   fundo escuro fixo. O terreno muda (grama, neve, masmorra, lava). Por isso o
   discriminador principal e a SATURACAO, nao o matiz: barra cheia tem S~210,
   terreno tem S~75. Um chao avermelhado enganaria um teste so de matiz.

2. **"HP zerado" e "linha ausente" leem exatamente igual nas barras**: 0%.
   Distinguir os dois e a diferenca entre "Korzis morreu" e "Korzis saiu da PT".
   O desempate vem do icone de classe, que existe independente do HP.

3. **O vermelho da volta no circulo de matiz** — precisa de DUAS faixas
   combinadas (H<=12 ou H>=168). Uma faixa so e a razao classica de um leitor
   de vida "as vezes ler 0%", que aqui viraria alerta falso de morte.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum

import cv2
import numpy as np

from .calibracao import Calibracao, LimiaresDeCor
from .cliente import EstadoDoCliente
from .frames import Frame, Regiao, SaudeDoFrame
from .identidade import identificar_linhas, mascara_de_texto


class EstadoDaLinha(Enum):
    """O que os pixels dizem sobre uma posicao de linha — sem interpretacao."""

    COM_MEMBRO = "com_membro"
    VAZIA = "vazia"


@dataclass(frozen=True)
class LeituraDeLinha:
    """O que foi lido numa posicao de linha da party window."""

    indice: int
    estado: EstadoDaLinha
    hp: float | None  # fracao 0.0-1.0, ou None se a linha esta vazia
    mp: float | None

    # Quem esta nesta linha, reconhecido pela imagem do nome. None quando nao
    # da para afirmar — e ai o rastreador cai para "Membro N", que e feio mas
    # honesto. Chutar um nome manda a party socorrer a pessoa errada.
    nome: str | None = None
    confianca_do_nome: float = 0.0

    @property
    def hp_zerado(self) -> bool:
        """HP em zero COM membro presente. Candidato a morte.

        Note que isto e diferente de `estado is VAZIA`: ali nao ha ninguem.
        """
        return self.estado is EstadoDaLinha.COM_MEMBRO and self.hp == 0.0


@dataclass(frozen=True)
class Observacao:
    """Tudo que um frame diz. Entrada do rastreador."""

    indice_do_frame: int
    ui_visivel: bool
    linhas: tuple[LeituraDeLinha, ...]
    hp_proprio: float | None = None

    # SO PARA MOSTRAR. Nenhuma decisao pode sair deste campo, nunca.
    #
    # Ele carrega a leitura que `barra_propria_legivel` RECUSOU e que o segundo
    # discriminador (`_braco_do_casamento`) ainda assim reconheceu como barra —
    # o caso real e a cena escura, onde a cauda vazia mostra terreno escuro e a
    # moldura despenca para 29.08 com a barra ainda 88.5% cheia. Hoje, nesse
    # regime, o console e o `scanner.log` nao mostram NADA da barra propria
    # durante a descida inteira.
    #
    # POR QUE ELE NAO PODE VIRAR `hp_proprio`, medido em 2026-08-27: tudo que o
    # casamento certifica pode ser um recorte PARCIALMENTE OCLUIDO. `coberta_0`
    # — o inventario cobrindo parte da barra — casa +0.999 e le 86.91%. As duas
    # classes so se ordenam pela moldura (48.00 contra 29.08), e nessa ordem
    # `coberta_2` (28.00) e `coberta_3` (29.00) ficam ABAIXO do unico ponto
    # legitimo que existe: a classe errada dos dois lados.
    #
    # E o custo de tratar isto como leitura de verdade foi SIMULADO contra a
    # maquina de estado, com `Ajustes()` de producao. `hp_proprio` tem TRES
    # consumidores em `rastreador.py` (linhas 454, 496 e 833):
    #
    #   quente com party, inventario 30 ticks -> `voce_sem_party` falso, tick 27
    #   morre e abre o inventario             -> `ressuscitou` falso, tick 34
    #   SOLO: morre e abre o inventario       -> `ressuscitou` falso, tick 34
    #   morrendo (2 de 3), abre e fecha       -> morte ATRASA do tick 18 para o 20
    #
    # Duas classes de alerta falso e um atraso de morte. A `ressuscitou` falsa e
    # literalmente metade do defeito que a quick `260826-dxm` pagou para matar.
    # O usuario abre o inventario o tempo todo: nao e raro, e frequente.
    #
    # A seguranca aqui NAO vem de guardas no rastreador — vem de esta leitura
    # NAO EXISTIR para ele. `rastreador.py` nao le este campo, e ha um tripwire
    # de arquitetura na suite que quebra se ele passar a ler.
    hp_proprio_aparente: float | None = None

    # Em que estado o CLIENTE esta (jogando, tela de login, desconectado).
    # Vem de fora da analise de pixels da party window — o titulo da janela e
    # um sinal do Windows, nao da imagem — por isso entra como campo em vez de
    # ser deduzido aqui. `None` significa "ninguem perguntou", e nunca vira
    # evento.
    estado_do_cliente: EstadoDoCliente | None = None

    # O painel do World Exchange esta aberto por cima do jogo? SO PARA MOSTRAR.
    #
    # `None` significa "ninguem perguntou" — instalacao sem calibracao de
    # mercado, ou o recorte da janela nao chegou neste tick. `False` significa
    # "olhei e ele nao esta". Os dois NAO sao a mesma coisa e nao podem ser
    # achatados: sem a distincao o console calaria justamente quando tem
    # resposta, e a Fase 4 nao conseguiria separar "mercado fechado" de
    # "mercado nao calibrado".
    #
    # VEM DE FORA DE `extrair`, pela mesma razao escrita ao lado de
    # `estado_do_cliente`: o painel nao esta na party window. Ele e procurado na
    # JANELA INTEIRA por `mercado_visao.RastreioDoPainel`, que tem ESTADO (onde
    # o painel foi visto da ultima vez) e cadencia propria — e `extrair` e uma
    # funcao pura, mesmo frame mesma saida. Quem preenche e `sessao.tick`.
    #
    # POR QUE ELE NAO PODE VIRAR DECISAO, e por que isso e a Fase 4 e nao esta:
    # promover um sinal de "tem uma janela por cima" a consumidor do detector de
    # morte e LITERALMENTE a manobra que produziu o incidente 27x — 27 mortes e
    # 27 ressurreicoes falsas, porque o inventario cobria a barra de vida e a
    # leitura de 0% virou alerta. A licao esta medida logo acima, em
    # `hp_proprio_aparente`.
    #
    # Ligar a oclusao de mercado ao rastreador na mesma fase em que a ancora
    # nasce significaria confiar num limiar recem-medido para SUPRIMIR alertas
    # de morte. O consumidor de oclusao chega na Fase 4, junto do DETC-02, com
    # a ancora ja rodada em campo. Ver o bloco `<detc01_reconciliation>` do
    # `01-04-PLAN.md`.
    #
    # A seguranca aqui NAO vem de guardas no rastreador — vem de esta leitura
    # NAO EXISTIR para ele. `rastreador.py` nao le este campo, e
    # `tests/test_mercado_27x.py` tem o tripwire de arquitetura que quebra se
    # ele passar a ler.
    mercado_aberto_aparente: bool | None = None

    # SO PARA APRENDER. Nenhuma DECISAO do rastreador pode sair deste campo,
    # nunca.
    #
    # Ele carrega a mascara de texto do recorte do nome de cada linha, que e o
    # material do qual uma assinatura nova e feita (D-04: a estabilidade e
    # julgada sobre a mascara, nunca sobre os pixels crus — o painel e
    # semitransparente e o cenario anda por tras do texto). A MASCARA, e nao o
    # recorte cru, tambem por desenho: guardar o recorte aqui daria a um
    # consumidor futuro a chance de julgar estabilidade por pixel, que e
    # exatamente a leitura que D-04 proibe.
    #
    # A seguranca aqui NAO vem de guardas no rastreador — vem de esta leitura
    # NAO EXISTIR para ele, a mesma protecao que `hp_proprio_aparente` e
    # `mercado_aberto_aparente` ja tem, com o tripwire de arquitetura em
    # `tests/test_aprendiz.py`.
    #
    # ESTE DICIONARIO PODE TER MAIS CHAVES DO QUE `linhas` TEM LINHAS OCUPADAS.
    # Os recortes sao coletados enquanto o laco varre as posicoes, e
    # `_truncar_no_primeiro_vao` so roda DEPOIS de `identificar_linhas`: uma
    # posicao alem do primeiro vao pode ter deixado uma mascara aqui e ter
    # virado `VAZIA` ali. A LEITURA CORRETA E SEMPRE
    # `mascaras_de_nome[linha.indice]`, partindo de uma linha de
    # `Observacao.linhas` — nunca iterar este dicionario e tratar cada chave
    # como se fosse uma pessoa. Hoje isso e inerte porque quem consome parte das
    # linhas; escrito aqui para que a Fase 3, que herda o campo, nao descubra
    # sozinha.
    mascaras_de_nome: dict[int, np.ndarray] = field(default_factory=dict)

    @property
    def membros_presentes(self) -> int:
        return sum(1 for l in self.linhas if l.estado is EstadoDaLinha.COM_MEMBRO)


def _mascara_de_cor(hsv: np.ndarray, limiares: LimiaresDeCor) -> np.ndarray:
    """Marca os pixels que pertencem ao preenchimento da barra.

    Para o vermelho, `matiz_min` > `matiz_max` sinaliza a volta no circulo e as
    duas faixas sao combinadas com OU.
    """
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    if limiares.matiz_min > limiares.matiz_max:
        no_matiz = (h >= limiares.matiz_min) | (h <= limiares.matiz_max)
    else:
        no_matiz = (h >= limiares.matiz_min) & (h <= limiares.matiz_max)

    return no_matiz & (s >= limiares.saturacao_min) & (v >= limiares.valor_min)


def medir_barra(
    pixels: np.ndarray, regiao: Regiao, limiares: LimiaresDeCor
) -> float:
    """Fracao preenchida de uma barra, de 0.0 a 1.0.

    Mede a CORRIDA INICIAL de colunas cheias, a partir da esquerda — nao o total
    de pixels da cor. Duas razoes:

    - Nunca usar `findContours` aqui: com a barra em 0% nao existe contorno
      nenhum, e 0% e justamente o evento que o scanner existe para detectar.
    - Contar o total deixaria um efeito vermelho do jogo passando por cima da
      barra inflar a leitura. A corrida inicial so aceita preenchimento
      continuo desde a borda, que e como a barra realmente esvazia.

    Uma coluna conta como cheia quando a maioria das suas linhas casa a cor —
    mais robusto do que olhar so a linha do meio, e sobrevive ao antialiasing
    das bordas.
    """
    recorte = pixels[
        regiao.topo : regiao.topo + regiao.altura,
        regiao.esquerda : regiao.esquerda + regiao.largura,
    ]
    if recorte.size == 0:
        return 0.0

    hsv = cv2.cvtColor(recorte, cv2.COLOR_BGR2HSV)
    mascara = _mascara_de_cor(hsv, limiares)

    altura_real = mascara.shape[0]
    colunas_cheias = mascara.sum(axis=0) >= max(1, altura_real / 2)

    corrida = 0
    for cheia in colunas_cheias:
        if not cheia:
            break
        corrida += 1

    return corrida / regiao.largura if regiao.largura else 0.0


def _tem_contraste_de_icone(
    pixels: np.ndarray, regiao: Regiao, desvio_min: float, fracao_escura_min: float
) -> bool:
    """O icone de classe esta nesta posicao?

    O icone e um quadrado escuro com borda clara e simbolo branco: contraste
    alto e muitos pixels escuros. Terreno de jogo nao tem nem um nem outro.

    Medido na tela real do usuario:
      linha com membro : desvio 43-52, escuros 46-52%
      linha vazia      : desvio  9-10, escuros  0%

    A margem e enorme, sem zona cinzenta.
    """
    recorte = pixels[
        regiao.topo : regiao.topo + regiao.altura,
        regiao.esquerda : regiao.esquerda + regiao.largura,
    ]
    if recorte.size == 0:
        return False

    cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    return (
        float(cinza.std()) >= desvio_min
        and float((cinza < 60).mean()) >= fracao_escura_min
    )


# Desvio minimo de cinza para um recorte da barra propria valer como LEGIVEL.
#
# Medido nas fixtures reais da barra do usuario: desvio 38,6. Um recorte preto
# ou uniforme (captura falhando, janela minimizada, jogo entre telas) da 0,00.
# A margem e enorme, entao o piso fica bem baixo de proposito — ele so precisa
# rejeitar o degenerado, nunca uma barra de verdade.
#
# CONTRASTE, e nao saturacao. Saturacao seria tentador (barra cheia da S~200),
# mas a parte VAZIA da barra e transparente e mostra o terreno — uma barra
# quase vazia tem saturacao baixa. Usar saturacao faria o scanner declarar
# "nao consigo ler" exatamente no frame em que voce esta morrendo.
DESVIO_MINIMO_DA_BARRA_PROPRIA = 3.0


# Brilho minimo da MOLDURA para um recorte da barra propria valer como LEGIVEL.
#
# Medido nas fixtures reais em tests/fixtures/barra_propria/, com moldura =
# menor media de cinza entre coluna 0, coluna -1, linha 0 e linha -1:
#
#   coberta pelo inventario : 48.00  48.92  28.00  29.00   -> pior 48.92
#   livre                   : 86.42 nas quatro
#   quase vazia (proxy real): 78.73                        -> pior livre/vazia
#
# Vao de 29.8 pontos, sem zona cinzenta. Da tela ao vivo do usuario (45 livres
# + 9 cobertas) a faixa e a mesma: livre 73.7-86.4, coberta 28.0-48.9.
#
# O limiar fica no PE da faixa, e nao no meio dela (63.8), de proposito: a parte
# vazia da barra mostra o TERRENO, e o proxy foi medido sobre grama. Em masmorra
# escura o terreno pode escurecer, e errar para baixo aqui significa declarar
# ilegivel uma barra vazia DE VERDADE — morte real suprimida, o pior desfecho
# deste projeto. Ver a pendencia
# .planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md
BRILHO_MINIMO_DA_MOLDURA_PROPRIA = 60.0


def _moldura_da_barra_propria(recorte: np.ndarray) -> float:
    """Quao clara e a borda mais escura do recorte da sua barra.

    Menor media de cinza entre as quatro bordas — coluna 0, coluna -1, linha 0
    e linha -1. A MENOR, e nao a media das quatro: o inventario pode cobrir so
    um lado da barra, e uma media diluiria justamente o lado coberto.
    """
    cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    return min(
        float(cinza[:, 0].mean()),
        float(cinza[:, -1].mean()),
        float(cinza[0, :].mean()),
        float(cinza[-1, :].mean()),
    )


def barra_propria_legivel(recorte: np.ndarray | None) -> bool:
    """O recorte da sua barra e uma barra, ou e lixo — ou esta COBERTO?

    `medir_barra` devolve 0.0 tanto para "HP zerado" quanto para um recorte
    preto, e essa confusao ja produziu um alarme falso de verdade: as 18:19 de
    2026-08-24 o scanner anunciou "Yazalaque nao esta mais na party" porque
    noventa segundos de captura ilegivel leram como "minha barra esta la a 0%".

    Uma barra de verdade tem ESTRUTURA — moldura, borda, terreno atras da parte
    vazia — cheia ou vazia. Lixo nao tem.

    Dois portoes EM SERIE, porque nenhum dos dois sozinho basta:

    1. CONTRASTE (desvio-padrao). Rejeita o degenerado: recorte preto, uniforme,
       captura falhando, janela minimizada.

    2. MOLDURA. Rejeita o recorte COBERTO por outra janela do jogo. O portao de
       contraste NAO pega esse caso e isso esta medido: a grade do inventario da
       desvio 36.54 em `coberta_0.png`, MAIOR que os 35.47 de `livre_0.png` —
       qualquer limiar de desvio que rejeite a coberta rejeita tambem a livre.
       Custo do buraco: 27 mortes falsas + 27 ressurreicoes falsas no
       `logs/scanner.log` real, mais que todos os alertas de party somados.

    O contraste continua aqui, e nao foi substituido: `np.full((8,120,3), 60)`
    da moldura exatamente 60.00 e passaria no portao novo — so segue rejeitado
    porque o portao de desvio nao saiu do lugar.

    POLARIDADE INVERTIDA em relacao a `_bordas_da_barra_intactas`, e isto
    precisa estar escrito ou o proximo leitor "conserta" o sinal e reabre o
    defeito:

      * a barra da PARTY rejeita borda CLARA demais, porque olha a coluna
        imediatamente FORA da barra, onde o jogo desenha uma linha ESCURA de
        chrome;
      * a barra PROPRIA rejeita moldura ESCURA demais, porque a regiao calibrada
        nao tem margem sobrando — as quatro bordas do recorte caem DENTRO do
        campo da barra (medido em `livre_0.png`: 89.6% do recorte casa a mascara
        vermelha, e as quatro bordas tem preenchimento). O campo da barra e
        CLARO: pelo vermelho quando cheia, pelo TERRENO que aparece atras quando
        vazia. O painel do inventario, ao contrario, e um overlay ESCURO.
    """
    if recorte is None or recorte.size == 0:
        return False
    cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    return (
        float(cinza.std()) >= DESVIO_MINIMO_DA_BARRA_PROPRIA
        and _moldura_da_barra_propria(recorte) >= BRILHO_MINIMO_DA_MOLDURA_PROPRIA
    )



# ---------------------------------------------------------------------------
# O SEGUNDO discriminador da barra propria — INVARIANTE A BRILHO.
#
# Medido em 2026-08-27 sobre `recordings/escuro_janela.png` (1392x1720, brilho
# medio 58.12), a unica cena escura que o repositorio conhece, resgatada para
# `tests/fixtures/barra_propria/escuro_*.png`.
#
# O PROBLEMA que ele existe para resolver: em cena escura a barra propria e
# declarada ILEGIVEL assim que QUALQUER cauda vazia aparece — medido com a barra
# ainda 88.5% cheia. A parte vazia da barra e transparente e mostra o terreno; em
# masmorra/noite esse terreno e escuro, e a MOLDURA despenca:
#
#   amostra (tela REAL)                fracao cheia   moldura   veredito de HOJE
#   escuro_janela HP  (294,716)        100%           86.42     LEGIVEL
#   escuro_janela MP  (294,741)         88.5%         29.08     ILEGIVEL
#   agora_janela  MP  (294,741)          6.8%         78.73     LEGIVEL
#
# 29.08 cai DENTRO da faixa das cobertas (28.00..48.92). As duas classes se
# SOBREPOEM nesse regime — nenhum limiar de brilho as separa, entao a resposta
# nao e outro numero, e outro discriminador.
#
#   classe                        n    moldura          casamento
#   livre, cheia, dia            45    73.67 .. 86.42   +0.993 .. +1.000
#   livre, cheia, ESCURO          1    86.42            +0.944
#   livre, 88.5% cheia, ESCURO    1    29.08            +0.964
#   livre, 6.8% cheia, dia        1    78.73            +0.979
#   coberta TOTAL, le 0%          8    28.00 .. 48.92   -0.059 .. +0.236
#   coberta parcial, le 86.91%    1    48.00            +0.999
#
# O casamento e INVARIANTE A BRILHO — Pearson e cego a escala e a deslocamento —
# e por isso da +0.964 num recorte cuja moldura despencou para 29.08.
#
# MAS A LEITURA QUE ELE CERTIFICA NAO E CONFIAVEL, e isso precisa estar escrito
# aqui: `coberta_0` (parcialmente ocluida) da +0.999. Casamento alto nao prova
# que o recorte esta LIVRE — prova que a estrutura horizontal da barra esta
# visivel. Por isso o resultado vai para `Observacao.hp_proprio_aparente`, que
# so o console e o log leem, e NUNCA para `hp_proprio`.
# ---------------------------------------------------------------------------

# Media de cinza por LINHA de `livre_0.png`, linhas 2 a 21 — 20 valores, com 2 px
# de folga em cima e embaixo para o casamento poder DESLIZAR. A folga e o que
# compra tolerancia a desalinhamento vertical; sem ela um unico pixel de
# deslocamento derruba a correlacao de +0.972 para -0.179 (medido).
PERFIL_DE_REFERENCIA_DA_BARRA_PROPRIA = (
    72.81, 72.57, 72.31, 72.33, 59.71, 104.48, 85.23, 88.60, 88.44, 94.38,
    85.98, 87.73, 86.40, 89.79, 64.02, 72.60, 72.48, 72.69, 72.69, 72.38,
)  # fmt: skip

# Altura em linhas do recorte calibrado da barra propria. Um recorte de outra
# altura e reamostrado para esta antes de casar — senao a comparacao mediria
# geometria em vez de estrutura.
LINHAS_DO_PERFIL_PROPRIO = 24

# Casamento minimo para o recorte valer como uma barra APARENTE.
#
#   coberta TOTAL (n=8, tela real), maximo  : +0.236  -> folga de 0.164
#   as duas genuinas de cena escura         : +0.944 e +0.964 -> folga de 0.544
#
# O ponto medio das duas classes seria 0.590. O limiar fica ABAIXO dele de
# proposito: errar para cima recusa barra legitima, e a direcao do dano deste
# projeto e o SILENCIO.
CASAMENTO_MINIMO_DO_PERFIL_PROPRIO = 0.40

# Leitura minima para o casamento poder certificar qualquer coisa.
#
# ESTA CONSTANTE E UMA TRAVA DE SEGURANCA, nao um ajuste de qualidade. Um painel
# de inventario cobrindo o LADO ESQUERDO da barra ZERA a leitura (`medir_barra`
# mede a corrida inicial a partir da esquerda) e ainda assim casa +1.000, porque
# o perfil e a media por LINHA e cobrir 5 de 191 colunas mal move essa media.
# Sem esta trava, um inventario aberto viraria leitura de morte — a classe de
# defeito que a quick `260826-dxm` pagou para matar (27 mortes + 27
# ressurreicoes falsas num unico log real).
#
# 0.05 e 2.5x o `Ajustes.fracao_hp_considerada_zero = 0.02` do rastreador,
# ~9.5 de 191 colunas. Verificado por EXAUSTAO nas DUAS direcoes de oclusao:
# 4608 compostos (3 preenchimentos de direita x 4 paineis reais x k de 0 a 191 x
# 2 direcoes), 3279 no regime de morte, ZERO certificados.
#
# O acoplamento com o rastreador esta preso por tripwire em
# `tests/test_inventario_por_cima_da_barra_propria.py`: baixar
# `fracao_hp_considerada_zero` anularia esta trava a distancia, sem tocar aqui.
LEITURA_MINIMA_PARA_O_CASAMENTO = 0.05


def _casamento_do_perfil_proprio(recorte: np.ndarray) -> float:
    """Quanto a estrutura HORIZONTAL do recorte parece a da barra propria.

    Media de cinza por LINHA (o perfil vertical do widget: moldura em cima,
    campo da barra no meio, moldura embaixo), correlacionada por Pearson com
    `PERFIL_DE_REFERENCIA_DA_BARRA_PROPRIA`.

    Duas propriedades, as duas MEDIDAS:

    * INVARIANTE A BRILHO. Pearson normaliza media e escala, entao a mesma barra
      sobre terreno escuro casa igual: +0.964 num recorte cuja moldura caiu para
      29.08. E exatamente por isso que ele serve onde a moldura falha.

    * TOLERA +-2 px de desalinhamento vertical. A referencia tem 20 valores e
      DESLIZA sobre o perfil de 24; o melhor encaixe vence. Medido nas 5 janelas
      reais de `escuro_faixa.png`: +0.964 CONSTANTE ate a terceira casa, enquanto
      a moldura das mesmas 5 pula de 12.64 a 32.33. A versao de posicao FIXA cai
      de +0.972 para -0.179 com UM pixel de deslocamento — o deslizamento nao e
      refinamento, e o que faz a funcao funcionar.

    Em +-3 px o casamento cai para +0.293/+0.364, ambos abaixo do limiar: essa e
    a tolerancia INTEIRA, e nao ha rede alem dela.

    Sem variancia em qualquer um dos dois vetores o denominador de Pearson e
    zero. A funcao devolve 0.0 nesse caso — nunca divide por zero, e nunca
    aprova o degenerado (um recorte uniforme tem perfil constante).
    """
    cinza = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    perfil = cinza.mean(axis=1).astype(np.float64)

    if perfil.size != LINHAS_DO_PERFIL_PROPRIO:
        perfil = np.interp(
            np.linspace(0.0, 1.0, LINHAS_DO_PERFIL_PROPRIO),
            np.linspace(0.0, 1.0, perfil.size),
            perfil,
        )

    referencia = np.asarray(PERFIL_DE_REFERENCIA_DA_BARRA_PROPRIA, dtype=np.float64)
    if perfil.size < referencia.size:
        return 0.0

    centrada = referencia - referencia.mean()
    norma_ref = float(np.sqrt(float((centrada * centrada).sum())))
    if norma_ref == 0.0:
        return 0.0

    melhor = 0.0
    for inicio in range(perfil.size - referencia.size + 1):
        janela = perfil[inicio : inicio + referencia.size]
        desvio = janela - janela.mean()
        norma = float(np.sqrt(float((desvio * desvio).sum())))
        if norma == 0.0:
            continue
        melhor = max(melhor, float((desvio * centrada).sum()) / (norma * norma_ref))

    return melhor


def _braco_do_casamento(recorte: np.ndarray, leitura: float | None) -> bool:
    """O recorte parece uma barra E a leitura NAO esta em regime de morte?

    Funcao separada de proposito: e ELA que carrega a propriedade de seguranca
    desta mudanca, e o teste exaustivo precisa mirar direto nela em vez de
    inferi-la por `extrair`.

    A ordem importa. O portao de LEITURA vem primeiro e e absoluto: um painel
    cobrindo a esquerda da barra zera a leitura e ainda assim casa +1.000. Se o
    casamento pudesse certificar leitura zero, abrir o inventario voltaria a
    produzir morte falsa.

    Isto NAO fecha o buraco simetrico do braco de MOLDURA, que e PRE-EXISTENTE:
    `coberta_2` com o painel cobrindo 5 colunas a esquerda le 0.0000 com moldura
    64.00 e ja e aceito HOJE por `barra_propria_legivel`. Esse buraco nao e
    fechavel por portao de leitura — o braco de moldura PRECISA certificar
    leitura zero, e assim que a morte e anunciada em terreno de dia. Registrado
    em .planning/todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md
    """
    if leitura is None or leitura <= LEITURA_MINIMA_PARA_O_CASAMENTO:
        return False
    return _casamento_do_perfil_proprio(recorte) >= CASAMENTO_MINIMO_DO_PERFIL_PROPRIO


def _bordas_da_barra_intactas(
    pixels: np.ndarray, layout, barra_x: int, barra_y: int, brilho_max: float
) -> bool:
    """A moldura da barra ainda esta la?

    A UI do jogo desenha uma linha escura nas duas pontas de cada barra. Essa
    linha e CHROME, nao preenchimento: ela existe igual com a barra cheia e com
    a barra vazia. So some quando outra janela do jogo — inventario, ficha do
    personagem, loja — e aberta por cima da party window.

    Isso resolve um falso positivo que derrubaria a confianca no scanner
    inteiro: com o inventario aberto, as barras ficam cortadas em ~2% e os
    quatro membros seriam anunciados como mortos ao mesmo tempo. Abrir o
    inventario e algo que se faz o tempo todo farmando.

    Medido na tela real: barra livre da V~8-11 nas duas pontas (cheia OU vazia,
    valores identicos); coberta pelo inventario da V~72-112.
    """
    fim = barra_y + layout.barra_altura

    esquerda = pixels[barra_y:fim, barra_x - 1] if barra_x >= 1 else None
    direita_x = barra_x + layout.barra_largura
    direita = (
        pixels[barra_y:fim, direita_x] if direita_x < pixels.shape[1] else None
    )

    for borda in (esquerda, direita):
        if borda is None or borda.size == 0:
            continue
        cinza = cv2.cvtColor(borda.reshape(1, -1, 3), cv2.COLOR_BGR2GRAY)
        if float(cinza.mean()) > brilho_max:
            return False

    return True


def _recorte_do_nome(
    pixels: np.ndarray, cal: Calibracao, indice: int
) -> np.ndarray | None:
    """O pedaco da tela onde fica o texto do nome desta linha.

    Devolve None quando o recorte cai fora do frame — a calibracao aponta para
    fora, e um recorte cortado produziria um casamento sem sentido.
    """
    # Exatamente a regiao calibrada — nem um pixel a mais. O recorte era
    # alargado 24 px a esquerda para o casamento poder deslizar; ver a nota
    # sobre a coroa do lider em identidade.py para por que isso saiu.
    regiao = cal.regiao_do_nome(indice)
    recorte = pixels[
        regiao.topo : regiao.topo + regiao.altura,
        regiao.esquerda : regiao.esquerda + regiao.largura,
    ]
    if recorte.shape[0] != regiao.altura or recorte.shape[1] != regiao.largura:
        return None
    return recorte


def extrair(frame: Frame, cal: Calibracao) -> Observacao:
    """Le um frame inteiro. Funcao pura: mesmo frame, mesma saida, sempre."""
    layout = cal.layout
    pixels = frame.pixels

    # Frame doente nao produz leitura nenhuma. Um frame preto lido como "todas
    # as barras vazias" viraria um alerta de wipe total que nunca aconteceu.
    if frame.saude is not SaudeDoFrame.OK:
        return Observacao(
            indice_do_frame=frame.indice, ui_visivel=False, linhas=(), hp_proprio=None
        )

    # A ancora fica no TOPO da janela de proposito: a party window e ancorada em
    # cima e encolhe por baixo conforme a PT diminui. Uma ancora na borda
    # inferior sumiria sozinha quando a party passasse de 4 para 3 membros, e o
    # scanner entraria em modo cego sem motivo nenhum.
    ui_visivel = _tem_contraste_de_icone(
        pixels,
        cal.ancora,
        desvio_min=layout.ancora_desvio_min,
        fracao_escura_min=layout.ancora_escuros_min,
    )

    linhas: list[LeituraDeLinha] = []
    recortes_de_nome: dict[int, np.ndarray] = {}
    for i in range(layout.max_linhas):
        deslocamento = i * layout.passo

        regiao_icone = Regiao(
            esquerda=layout.icone_x,
            topo=layout.icone_y + deslocamento,
            largura=layout.icone_tamanho,
            altura=layout.icone_tamanho,
        )

        presente = _tem_contraste_de_icone(
            pixels,
            regiao_icone,
            desvio_min=layout.icone_desvio_min,
            fracao_escura_min=layout.icone_escuros_min,
        )

        if not presente:
            # Primeiro vao: a party window ACABA aqui. A regiao capturada e mais
            # alta que a janela de proposito, entao tudo abaixo deste ponto e
            # chat, minimapa ou terreno.
            #
            # Sair do laco (em vez de continuar) e uma correcao de CORRETUDE,
            # nao de desempenho. Uma linha de chat com contraste alto passa no
            # teste do icone, e ai `_bordas_da_barra_intactas` roda sobre lixo,
            # falha, e derruba `ui_visivel` do frame INTEIRO — cegando o scanner
            # por causa de uma linha que a propria logica ja considera
            # inexistente. `_truncar_no_primeiro_vao` descartava essa linha
            # depois, tarde demais: a cegueira ja tinha acontecido.
            #
            # Medido: 1 frame em 60 entrava em modo cego por isso, e cada um
            # custava ~4 frames de "[reajustando]" com todos os membros em
            # estado desconhecido.
            for j in range(i, layout.max_linhas):
                linhas.append(
                    LeituraDeLinha(
                        indice=j, estado=EstadoDaLinha.VAZIA, hp=None, mp=None
                    )
                )
            break

        regiao_hp = Regiao(
            esquerda=layout.barra_x,
            topo=layout.hp_y + deslocamento,
            largura=layout.barra_largura,
            altura=layout.barra_altura,
        )
        regiao_mp = Regiao(
            esquerda=layout.barra_x,
            topo=layout.mp_y + deslocamento,
            largura=layout.barra_largura,
            altura=layout.barra_altura,
        )

        # Se a moldura da barra sumiu, tem outra janela do jogo por cima e
        # a leitura nao vale nada. Nesse caso NAO tratamos a linha como morta
        # nem como ausente: derrubamos a visibilidade da UI inteira, porque se
        # parte da party window esta coberta nao da para confiar em nenhuma
        # parte dela. O portao de cegueira do rastreador cuida do resto.
        if not _bordas_da_barra_intactas(
            pixels, layout, layout.barra_x, layout.hp_y + deslocamento,
            layout.borda_v_max,
        ):
            ui_visivel = False

        # O recorte do nome e so COLETADO aqui. Quem esta em cada linha e
        # decidido depois, com o frame inteiro na mao — ver abaixo.
        recorte = _recorte_do_nome(pixels, cal, i)
        if recorte is not None:
            recortes_de_nome[i] = recorte

        linhas.append(
            LeituraDeLinha(
                indice=i,
                estado=EstadoDaLinha.COM_MEMBRO,
                hp=medir_barra(pixels, regiao_hp, cal.limiares_hp),
                mp=medir_barra(pixels, regiao_mp, cal.limiares_mp),
            )
        )

    # Identidade pela IMAGEM do nome, nao pela posicao da linha — a party window
    # compacta as linhas quando alguem sai, entao a posicao e um lugar, nao uma
    # identidade.
    #
    # Resolvido para o FRAME INTEIRO de uma vez, e nao linha a linha, porque as
    # linhas nao sao independentes: duas pessoas diferentes nao podem ser a
    # mesma pessoa. Decidindo isoladamente, a mesma assinatura ganhava duas
    # linhas, o membro roubado sumia do conjunto de identidades, e o rastreador
    # anunciava que ele saiu da party. Aconteceu 8 vezes numa sessao de 25
    # minutos com a party parada.
    # A mascara de cada recorte, SO PARA APRENDER — ver o campo homonimo em
    # `Observacao`. Ela e RECALCULADA aqui de proposito: `identificar_linhas` ja
    # calcula a dela por dentro, mas devolver a de la exigiria mudar a
    # assinatura publica de uma funcao que quatro arquivos de teste exercitam, e
    # um `cvtColor` mais um limiar sobre um recorte de ~20x100 a 1 Hz nao
    # aparece em perfil nenhum.
    #
    # `extrair` continua sendo uma FUNCAO PURA — mesmo frame, mesma saida — e
    # isso nao pode mudar: nada de estado, nada de escrita, nada de acervo aqui
    # dentro. Quem grava e o `aprendiz`, chamado pelo `sessao`.
    mascaras_de_nome = {
        indice: mascara_de_texto(recorte)
        for indice, recorte in recortes_de_nome.items()
    }

    casamentos = identificar_linhas(recortes_de_nome, cal.assinaturas)
    for pos, linha in enumerate(linhas):
        casamento = casamentos.get(linha.indice)
        if casamento is None:
            continue
        linhas[pos] = replace(
            linha,
            nome=casamento.nome,
            confianca_do_nome=casamento.confianca,
        )

    linhas = _truncar_no_primeiro_vao(linhas)

    # Uma party window com ZERO membros nao existe: se ela esta na tela, tem
    # pelo menos uma linha. Ver a ancora e nao ver nenhum icone significa que a
    # calibracao aponta para o lugar errado — a party window foi arrastada, o
    # jogo foi redimensionado, ou a UI mudou.
    #
    # Sem esta regra, um deslocamento de 15 a 40 px passa pela ancora e faz
    # TODAS as linhas lerem como vazias — e o rastreador anunciaria que a party
    # inteira saiu. Quatro alertas falsos de uma vez, por causa de um frame
    # arrastado sem querer.
    if ui_visivel and not any(
        l.estado is EstadoDaLinha.COM_MEMBRO for l in linhas
    ):
        ui_visivel = False

    # A barra do proprio personagem vem de um recorte SEPARADO: ela fica no
    # topo da janela, longe da party window. Sem isso, a morte do usuario —
    # justamente quem esta AFK sem ninguem olhando — nunca seria detectada.
    hp_proprio = None
    recorte_proprio = frame.extras.get("hp_proprio")
    # `None` quando o recorte nao e uma barra legivel — nunca 0.0. Confundir os
    # dois faz o scanner anunciar morte de quem esta vivo, ou "voce saiu da
    # party" a partir de uma tela preta.
    if barra_propria_legivel(recorte_proprio):
        regiao_inteira = Regiao(
            esquerda=0,
            topo=0,
            largura=recorte_proprio.shape[1],
            altura=recorte_proprio.shape[0],
        )
        hp_proprio = medir_barra(recorte_proprio, regiao_inteira, cal.limiares_hp)

    # A leitura APARENTE, so para o console e para o log. O bloco acima NAO foi
    # tocado de proposito: o que alimenta a maquina de estado precisa sair daqui
    # byte a byte como saia antes, senao nenhum alerta pode ser garantido.
    #
    # Ela so e calculada quando o portao de hoje RECUSOU — em cena escura, uma
    # barra 88.5% cheia e recusada por moldura 29.08 e some do console durante a
    # descida inteira. Ver `Observacao.hp_proprio_aparente` para a razao de ela
    # nao poder ser promovida a leitura de verdade.
    hp_proprio_aparente = None
    if (
        hp_proprio is None
        and recorte_proprio is not None
        and recorte_proprio.size > 0
    ):
        regiao_aparente = Regiao(
            esquerda=0,
            topo=0,
            largura=recorte_proprio.shape[1],
            altura=recorte_proprio.shape[0],
        )
        leitura_aparente = medir_barra(
            recorte_proprio, regiao_aparente, cal.limiares_hp
        )
        cinza_proprio = cv2.cvtColor(recorte_proprio, cv2.COLOR_BGR2GRAY)
        # O portao de CONTRASTE continua valendo: um recorte preto ou uniforme
        # nao pode virar numero no console mais do que podia virar alerta.
        if float(cinza_proprio.std()) >= DESVIO_MINIMO_DA_BARRA_PROPRIA and (
            _braco_do_casamento(recorte_proprio, leitura_aparente)
        ):
            hp_proprio_aparente = leitura_aparente

    return Observacao(
        indice_do_frame=frame.indice,
        ui_visivel=ui_visivel,
        linhas=tuple(linhas),
        hp_proprio=hp_proprio,
        hp_proprio_aparente=hp_proprio_aparente,
        mascaras_de_nome=mascaras_de_nome,
    )


def _truncar_no_primeiro_vao(
    linhas: list[LeituraDeLinha],
) -> list[LeituraDeLinha]:
    """Forca a VAZIA tudo que vem depois da primeira linha vazia.

    A party window nunca tem buraco: os membros ocupam as linhas de cima para
    baixo, sem pular. "Membro 3 presente, 4 ausente, 5 presente" e impossivel
    no jogo.

    Isso importa porque a regiao capturada e mais alta que a janela de
    proposito (para caber uma party cheia), e o excedente cai em cima do chat e
    do minimapa — que tem contraste alto e poderiam ser lidos como icone de
    classe. Sem essa regra, uma linha de chat colorida viraria um quinto membro
    fantasma, e depois a "saida" dele viraria um alerta que nunca aconteceu.
    """
    resultado: list[LeituraDeLinha] = []
    achou_vao = False

    for linha in linhas:
        if achou_vao:
            resultado.append(
                LeituraDeLinha(
                    indice=linha.indice,
                    estado=EstadoDaLinha.VAZIA,
                    hp=None,
                    mp=None,
                )
            )  # nome descartado junto: linha vazia nao tem dono
            continue

        if linha.estado is EstadoDaLinha.VAZIA:
            achou_vao = True

        resultado.append(linha)

    return resultado
