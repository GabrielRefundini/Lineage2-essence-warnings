"""Conferir, no arranque, se a regiao gravada da SUA barra de HP bate com a tela.

O INCIDENTE, medido em campo em 2026-08-31
==========================================
O `calibration.json` tinha `hp_proprio = 191x24 em (298,701)`. A barra vermelha
de verdade estava em `topo=711`. Dez pixels acima, a regiao caia sobre a barra
de CP (amarela) e so encostava numa lasca vermelha do topo da HP.

O console mostrava `Yazalaque (voce) ok HP 8%` com a barra CHEIA na tela
(5418/5418).

POR QUE ISSO ERA PERIGOSO E NAO SO FEIO. 8% e MAIOR QUE ZERO, entao
`Rastreador._avaliar_so_o_proprio` marcou `_ja_viu_a_propria_barra_viva` como
True. Aquela guarda so protege quem NUNCA foi visto vivo: satisfeita, ela sai
do caminho, e a partir dali qualquer oscilacao da lasca vermelha ate zero
teria disparado MORTE do usuario com ele intacto. Esse e o pior modo de falha
deste produto, e o incidente parou a um pixel de distancia dele.

A CAUSA NAO FOI DETERMINADA, e este modulo existe por causa disso
================================================================
O erro medido e (+9,-10): sinais OPOSTOS nos dois eixos, e nenhum valor de
origem produz isso, porque somar uma origem desloca os dois eixos no mesmo
sentido. Ha uma suspeita nao demonstrada (a origem do DWM em
`calibrar.origem_da_janela` exclui a borda invisivel de ~7-8 px, e a janela que
a WGC entrega comeca em outro lugar) que explicaria o eixo HORIZONTAL e nao
explica o vertical. Nao ha explicacao escrita aqui porque nao ha explicacao
medida, e uma docstring que inventa uma causa e pior que uma que admite nao
saber: a inventada faz a proxima pessoa parar de procurar.

Enquanto a causa nao for achada, o que da para garantir e que o desfecho nao
acontece CALADO. Uma calibracao que aponta para o lugar errado passa a ser uma
coisa que o usuario LE no arranque, e nao uma coisa que ele descobre por um
alerta de morte falso.

O QUE ESTE MODULO NAO FAZ, E POR QUE
====================================
1. NAO DETECTA NADA POR CONTA PROPRIA. Quem acha a barra e
   `calibrar.achar_barra_do_proprio`, a MESMA funcao que o `calibrar.bat`
   usa para gravar a regiao. Conferido contra a janela real em 31/08: ela
   devolve `(289,711) 191x24`, que e a barra certa. Um segundo detector seria
   uma segunda verdade sobre a mesma tela, e as duas discordariam justamente no
   dia em que a resposta importa.

2. NAO CORRIGE. Nem o `calibration.json`, nem a `Calibracao` em memoria. Trocar
   a regiao de HP proprio por conta propria e da MESMA familia de risco que
   este aviso cobre: um detector que erra passaria a mandar no que o rastreador
   le sobre a vida do usuario, e nao ha aqui as oito conferencias de
   plausibilidade que `l2scanner/reancoragem.py` tem antes de adotar geometria.
   O texto diz o que achou, o que esta gravado, e manda rodar `calibrar.bat`.

3. NAO AVISA QUANDO NAO ACHA BARRA NENHUMA. UI escondida com Alt+Z, personagem
   morto na tela de arranque, jogo em loading: em nenhum desses casos ha barra
   vermelha na tela, e nenhum deles diz nada sobre a regiao gravada estar certa
   ou errada. Isso e AUSENCIA DE EVIDENCIA, e nao divergencia. Avisar neles
   transformaria o arranque normal de quem esconde a UI num alarme, e um alarme
   que toca sem motivo e um alarme que ninguem le no dia em que ele estiver
   certo. Degradacao silenciosa e proibida neste projeto; ruido tambem.

4. SO VALE NO CAMINHO `--janela`. No caminho `mss` a barra propria nem e
   capturavel (`__main__.py` ja avisa: "a barra do seu personagem so e lida com
   --janela"), entao conferir ali seria prometer cobertura que nao existe.

O IMPORT DE `calibrar` E TARDIO, dentro de `_achar`, e isso e necessidade e nao
estilo: `calibrar.py` roda `tornar_consciente_de_dpi()` NO IMPORT e arrasta
junto o `cv2` das ferramentas interativas. Importa-lo no topo faria todo
arranque do scanner pagar por ele e poria um efeito colateral de DPI numa ordem
que ninguem controla. Mesmo molde do `Reancorador` em `reancoragem.py`.
"""

from __future__ import annotations

import logging

from .calibracao import Calibracao
from .frames import Regiao

log = logging.getLogger("l2scanner")


# Quantos pixels o canto da barra pode diferir sem virar aviso.
#
# COMPARAMOS O CANTO (topo e esquerda) E IGNORAMOS A LARGURA, de proposito.
# `achar_barra_do_proprio` acha o componente conexo PREENCHIDO: com HP parcial a
# barra medida e mais estreita que a gravada, e a diferenca chega a ser a barra
# inteira quando o usuario esta quase morto. Comparar largura acusaria
# divergencia toda vez que ele tomasse dano, que e a forma mais rapida de um
# aviso deixar de ser lido. O canto nao depende do preenchimento: a barra enche
# da esquerda para a direita a partir de uma origem fixa. A ALTURA e ignorada
# pela mesma razao invertida, ela e propriedade do skin e nao acrescenta sinal.
#
# POR QUE 4 E NAO 1. Sobra tremor legitimo de um ou dois pixels no retangulo do
# componente conexo: a moldura da barra tem bevel de cor diferente e o texto
# "HP 5418/5418" desenhado por cima morde a primeira linha, entao a linha de
# cima do componente pode aparecer e sumir entre um frame e outro. E o mesmo
# motivo da folga de 2 px em `reancoragem.TOLERANCIA_DO_PASSO`, com margem.
#
# POR QUE 4 E NAO 8. O caso REAL que precisa disparar e (-9,+10). Ficar em 4
# deixa mais que o dobro de margem abaixo do desvio medido em campo, o que
# significa que um desvio menor e mais sutil que aquele ainda e pego. Uma
# tolerancia perto de 9 pegaria o incidente de 31/08 por sorte e deixaria
# passar o proximo, que nao tem obrigacao nenhuma de ser tao grande.
TOLERANCIA_DE_POSICAO = 4


# O texto vai INTEIRO para o usuario, numa linha so de WARNING.
#
# Ele diz TRES coisas, nesta ordem, e cada uma responde a uma pergunta que o
# usuario faria: o que esta gravado (o que o scanner acredita), o que foi achado
# agora (o que a tela mostra), e o que fazer (rodar `calibrar.bat`). A frase do
# meio existe porque sem ela um desvio de 10 px parece cosmetico: 8% de HP lido
# com a barra cheia foi o que o incidente produziu, e 8% e vivo o bastante para
# destravar o alerta de morte.
#
# SEM TRAVESSAO e SEM ACENTO: o console do Windows e cp1252, e ha teste
# prendendo isso.
TEXTO_DO_AVISO = (
    "A REGIAO DA SUA BARRA DE HP NAO BATE COM A TELA. Gravado no "
    "calibration.json: %dx%d em (%d,%d). Achado agora na janela do jogo: "
    "(%d,%d), um desvio de (%+d,%+d) px. Comparo so o canto, porque a largura "
    "medida encolhe junto com o seu HP. NAO vou trocar a regiao sozinho, e ate "
    "voce conferir nao confie em alerta nenhum sobre VOCE: em 31/08 uma regiao "
    "10 px fora da barra leu HP 8%% com a barra CHEIA na tela, e 8%% e vivo o "
    "bastante para destravar o alerta de MORTE. Rode calibrar.bat para "
    "regravar a regiao."
)


def conferir_a_barra_do_proprio(
    cal: Calibracao, completo, detector=None
) -> str | None:
    """O texto do aviso, ou `None` quando nao ha nada honesto a dizer.

    `completo` e a janela do jogo INTEIRA, em coordenadas da janela, que e o
    referencial em que `hp_proprio` esta gravado.

    `detector` entra por parametro so para o teste poder montar a situacao sem
    jogo aberto. O padrao e `calibrar.achar_barra_do_proprio`, por import
    tardio (ver o cabecalho do modulo).

    OS QUATRO SILENCIOS, e nenhum deles e degradacao:

      - `hp_proprio` nao calibrado: nao ha regiao gravada para conferir.
      - frame ausente ou vazio: a captura falhou, e uma captura que falhou nao
        e evidencia de posicao nenhuma.
      - detector nao achou barra: Alt+Z, loading ou morto no arranque.
      - canto dentro da tolerancia: esta certo.
    """
    gravada = cal.hp_proprio
    if gravada is None:
        return None

    if completo is None or getattr(completo, "size", 0) == 0:
        return None

    achada = _achar(completo, detector)
    if achada is None:
        # AUSENCIA DE EVIDENCIA. Ver o item 3 do cabecalho do modulo: nao achar
        # a barra nao diz nada sobre a regiao gravada, e avisar aqui faria o
        # arranque de quem joga com a UI escondida virar um alarme diario.
        log.debug(
            "Conferencia da barra propria: nenhuma barra vermelha na janela "
            "(UI escondida, loading ou personagem morto). Nada a dizer."
        )
        return None

    dx = achada.esquerda - gravada.esquerda
    dy = achada.topo - gravada.topo
    if abs(dx) <= TOLERANCIA_DE_POSICAO and abs(dy) <= TOLERANCIA_DE_POSICAO:
        return None

    return TEXTO_DO_AVISO % (
        gravada.largura,
        gravada.altura,
        gravada.esquerda,
        gravada.topo,
        achada.esquerda,
        achada.topo,
        dx,
        dy,
    )


def avisar_no_arranque(cal: Calibracao, fonte, detector=None) -> str | None:
    """Confere contra um frame da fonte e registra o aviso. Devolve o texto.

    UMA VEZ, NO ARRANQUE, e nao a cada tick. A regiao gravada nao muda enquanto
    o processo vive, entao repetir a conferencia no laco so poderia produzir a
    mesma linha mil vezes, e mil linhas iguais e como um aviso deixa de ser
    lido. Se a barra estiver escondida na hora do arranque a conferencia cala e
    nao volta: o preco de nao insistir e nao virar ruido, e quem esconde a UI o
    tempo todo ja convive com a barra propria nao sendo lida.

    Devolve o texto (e nao um booleano) para o teste poder afirmar sobre ele sem
    ler o log, e para um chamador futuro poder mandar o mesmo texto por outro
    caminho sem duplicar a redacao.
    """
    if cal.hp_proprio is None:
        # Antes de pedir o frame: sem regiao gravada a captura seria trabalho
        # jogado fora.
        return None

    texto = conferir_a_barra_do_proprio(cal, fonte.capturar_completo(), detector)
    if texto is None:
        return None

    log.warning("%s", texto)
    return texto


# -- interno ------------------------------------------------------------------


def _achar(completo, detector) -> Regiao | None:
    """Roda o detector do `calibrar.bat` sobre a janela do jogo.

    `origem=(0,0)` de proposito: assim a posicao sai em coordenadas DA JANELA,
    que e o referencial de `hp_proprio` e o unico que sobrevive a arrastar o
    jogo pela tela.

    UMA EXCECAO AQUI NAO PODE DERRUBAR O ARRANQUE. Esta conferencia e um extra;
    um scanner que nao sobe por causa dela deixaria a party sem vigia nenhum,
    que e infinitamente pior do que uma regiao desalinhada. O traceback fica em
    DEBUG, no `scanner.log`.
    """
    if detector is None:
        from .calibrar import achar_barra_do_proprio  # tardio, ver o cabecalho

        detector = achar_barra_do_proprio

    try:
        return detector(completo, (0, 0))
    except Exception:  # noqa: BLE001
        log.debug("A conferencia da barra propria explodiu", exc_info=True)
        return None
