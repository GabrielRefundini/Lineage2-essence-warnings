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
o reconhecimento; a resposta para a CINTILACAO nao e o limiar, e a mensagem que
o usuario le quando ela acontece.

E ESSA MEDICAO NAO GENERALIZA, o que so ficou claro no dia seguinte. Ela foi
tirada com a party parada em GRAMA UNIFORME, que e um fundo benigno: escuro,
liso, sem nada que passe do piso de brilho. Concluir dela que "o limiar 180 esta
certo" foi ir alem do que ela mede, e a versao anterior deste paragrafo dizia
exatamente isso. A segunda rodada, sobre PEDRA CLARA, esta logo abaixo e derruba
a generalizacao: no MESMO limiar, centenas de celulas de cenario entram na
mascara. O que a medicao da grama prova e uma coisa so, e ela continua valendo:
a variacao entre frames de uma party PARADA EM FUNDO ESCURO e serrilhado de
letra, e nao terreno.

A SEGUNDA RODADA, EM PEDRA CLARA: 28 ENTRADAS QUE SAO 5 PESSOAS

Medido em 01/09/2026 contra o acervo real do usuario. A pasta `.identidades/`
tinha 28 assinaturas e a party dele tem de 2 a 5 pessoas. Renderizadas em ASCII
uma a uma, elas nao sao gente diferente:

    PIRULITO       8 copias   107 a 336 px de texto
    TITANDER       8 copias   124 a 399
    Welazkez       5 copias   175 a 515
    Mostarda       3 copias    79 a 178
    WesleySniper   2 copias   155, 159
    lixo pontual   2 copias   uma delas com 843

Todas no mesmo recorte de 20x110 = 2200 celulas, e as 4 assinaturas CALIBRADAS a
mao pelo usuario (PIRULITO 110, Mostarda 114, TITANDER 130, Welazkez 159) sao a
unica verdade de campo conferida por gente. As duas faixas, separadas pelo
render:

    nome legivel, no maximo com serrilhado e a coroa do lider   107 a 175 px
    cenario visivel dentro do recorte                           178 a 843 px

As de 336, 399, 515 e 843 estao cheias de cenario: a party estava em Silent
Valley, sobre pedra clara de alto contraste, e a pedra passa do
`VALOR_MINIMO_DO_TEXTO` e entra na mascara. Nasceram o dia inteiro (12:15,
12:50, 16:30, 19:56, 20:12, 20:59 duas vezes, 21:10), e cada uma queimou um
marcador `perguntado_` e disparou uma pergunta no WhatsApp com uma imagem de
pedra.

E O REMEDIO NAO E MEXER NO LIMIAR DE BRILHO, pela razao de sempre e por uma
nova. A de sempre: as assinaturas calibradas do usuario foram gravadas COM o
limiar atual, e mexer nele afeta o RECONHECIMENTO de todo mundo, nao so o
aprendizado. A nova: mesmo um limiar perfeito nao separaria pedra clara de texto
claro, porque em Silent Valley os dois SAO claros. O que separa e o TAMANHO da
mascara, que e a mesma leitura que `identidade.FATOR_MAXIMO_DE_CONTAMINACAO` ja
fazia no casamento. Ver `TETO_DE_OCUPACAO_DO_NOME`.

O TETO NAO CONSERTA A DUPLICACAO, E ISSO TAMBEM FOI MEDIDO

Fica escrito em voz alta porque a conclusao errada e a comoda: o teto pega as 11
piores entradas e ainda assim o PIRULITO apareceu 8 vezes. As copias LIMPAS dele
tem 107, 120 e 125 px, todas muito abaixo de qualquer teto, e mesmo assim nasceu
uma entrada nova para cada uma.

A razao nao e contaminacao. Correlacionando as 28 entradas do acervo real DUAS A
DUAS, no alinhamento calibrado, o maior valor do triangulo inteiro e 0.72:
NENHUM par chega ao `LIMIAR_DE_CASAMENTO` de 0.75. D-02 nunca teve nada para
vetar, porque nenhuma copia parecia com nenhuma outra.

    A ULTIMA FRASE CAIU EM 2026-09-04, e fica no lugar com a correcao ao lado
    porque um veredito derrubado tem de dizer que foi derrubado. Sobre 57
    assinaturas (as 23 ativas de hoje, 30 esquecidas da mesma pasta e as 4
    calibradas), a producao INTEIRA — nao o `_correlacionar` cru, mas a
    `confianca` de `identificar_linhas`, com os dois passes do ornamento —
    barra 6 entradas na ordem em que elas nasceram. D-02 tem sim o que vetar; o
    que ele nao alcanca sao as OUTRAS 47. Ver a tabela mais abaixo.

O que separa as copias e DESLOCAMENTO HORIZONTAL. As mesmas mascaras, deslizadas
de alguns pixels, casam com folga:

    par                          alinhado   melhor   deslocamento
    PIRULITO 107 x calibrada       0.220     0.918      -2 px
    Mostarda 108 x calibrada       0.431     0.905      -6 px
    Welazkez 175 x calibrada       0.236     0.891      -6 px
    TITANDER 171 x calibrada       0.258     0.980     +13 px
    PIRULITO 107 x PIRULITO 125    0.374     0.880      +4 px

Isso e coerente com o que `_correlacionar` ja diz de si mesmo: ele pontua em UMA
posicao so, e 1 px de erro derruba 1.000 para 0.24.

DUAS DAS OITO JA ESTAO CONSERTADAS, e o conserto e de 2026-09-01. Os
deslocamentos de +13 e +19 px sao a COROA do lider, e baixar
`COLUNAS_DE_LACUNA_DO_ORNAMENTO` de 4 para 3 fez o segundo passe alcanca-las:
rodando `identificar_linhas` hoje, as duas copias coroadas do TITANDER pontuam
0.980 e 0.967 contra a calibrada e D-02 as vetaria. Os deslocamentos de -2 a
-6 px NAO sao coroa; sao a origem da coluna do nome andando entre sessoes.

E O CONSERTO OBVIO FOI MEDIDO E NAO FUNCIONA. "Ancorar as duas mascaras na
primeira coluna com texto antes de correlacionar" e a primeira ideia de todo
mundo, inclusive a minha. Medida sobre estas mesmas mascaras, ela leva os pares
CERTOS a 0.15 ate 0.36, quando o deslizamento livre acha 0.80 a 0.98 nos mesmos
pares. A primeira coluna acesa nao e ancora estavel: uma celula de serrilhado ou
uma sujeira solta na frente do nome muda a ancora e joga a correlacao fora. Nao
implementar essa ideia e resultado, e nao omissao.

O QUE SOBRAVA COMO PROPOSTA, E O QUE A MEDICAO DE 2026-09-04 FEZ COM ELA

Em 2026-09-03, deslizando livre de -25 a +25 px sobre as 28 do acervo daquele
dia, escreveu-se aqui: pior par CERTO 0.753, pior par ERRADO 0.483. Os dois
numeros CAIRAM, e ficam escritos porque um numero que cai tem de dizer que caiu.
Sobre 57 assinaturas reais rotuladas uma a uma no olho (as 23 ativas de
2026-09-04, mais 30 esquecidas da mesma pasta, mais as 4 calibradas), com 236
pares da MESMA pessoa e 1195 pares de pessoas DIFERENTES:

    criterio             pior CERTO   melhor ERRADO   margem ate 0.75
    alinhado (producao)      -0.059           0.598             0.152
    desliza h +-6             0.000           0.619             0.131
    desliza h +-25            0.000           0.634             0.116
    faixa 5 linhas h +-6      0.000           1.000            -0.250
    faixa 8 linhas h +-6      0.000           0.456             0.294
    faixa 10 linhas h +-6     0.000           0.786            -0.036

O "pior par CERTO 0.753" era artefato da populacao de 28: hoje o pior par certo
e 0.000 em TODO criterio. Os conjuntos nao se separam, e nao e por pouco.

A LINHA `faixa 8` E A ARMADILHA DESTA TABELA. Ela tem a maior margem do quadro
e e sorte: isolar a faixa do nome com 5 linhas em vez de 8 da 1.000 para
Mostarda x PIRULITO, que sao DUAS PESSOAS, e com 10 linhas da 0.786. Um
parametro cujos vizinhos imediatos produzem veto errado ACIMA do limiar nao e
regime; e um ponto sortudo em 57 assinaturas.

E O DESLIZAMENTO FUNCIONA E NAO PAGA. Percorrendo o acervo na ordem em que ele
nasceu, com a producao inteira dentro do laco: ela ja barra 6 das 53 hoje;
`+-6` barraria 9, e `+-25` barraria 12. Tres perguntas a mais em 53, ao preco
de o melhor par errado subir de 0.598 para 0.619 — e essa grandeza esta ANDANDO
PARA CIMA conforme o acervo cresce (0.483 sobre 28 em 2026-09-03, 0.619 sobre 57
hoje). Trocar 3 perguntas em 53 por uma margem que encolhe, quando o desfecho de
um veto errado e duas pessoas virarem uma em silencio e para sempre, e o lado
errado da assimetria que `observar` documenta. NAO IMPLEMENTAR e resultado, e
nao omissao — a tabela inteira sai de `tools/aferir_duplicatas.py` e os numeros
estao presos em `tests/test_aferir_duplicatas.py`.

E A RAZAO DE 2026-09-03 CONTINUA DE PE, agora com companhia. O `.max()` sobre 25
deslocamentos foi REMOVIDO deste projeto por levar o pior casamento errado de
0.213 a 0.586, e a medicao de hoje nao desfaz aquilo: ela mostra o mesmo efeito
no mesmo sentido, com o pior errado indo de 0.598 (alinhado) a 0.634 (`+-25`). O
dado que faltava continua com o mesmo nome — gravacao multi-frame de campo com a
party se movendo, para medir a distribuicao dos pares errados sob deslizamento
em vez de estima-la em uma foto do acervo. O que mudou e que agora se sabe o
tamanho do premio: 3 entradas em 53.

E A CAUSA DA DUPLICATA NAO E SEMELHANCA, E ANCORA. Medido no mesmo acervo: em
31 das 57 mais de 10% da tinta cai FORA da faixa do nome — e texto de OUTRA
linha da party window dentro do mesmo recorte — e a faixa de 10 linhas com mais
tinta comeca na linha 0 em 10 delas e da linha 5 em diante em 46. O que muda
entre sessoes e onde o recorte comeca, e nenhum criterio de semelhanca
horizontal alcanca isso. Quem quiser matar a duplicata mexe na ancoragem do
recorte (ver `reancoragem`), e nao no limiar. Ate la, o acervo do usuario
continua ganhando uma entrada por sessao para quem ele ja conhece, e o
`acervo.carregar_identidades` explica por que a resposta NAO e um segundo
criterio de igualdade posto no olho.

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

# Quanto do recorte do nome pode estar aceso e ainda ser SO um nome.
#
# O PISO SOZINHO DEIXOU 24 ENTRADAS DE LIXO ENTRAREM. Ate 02/09/2026 `observar`
# conferia `PIXELS_MINIMOS_DE_TEXTO` e mais nada: um recorte com 843 pixels
# acesos passava direto e virava assinatura permanente. A tabela das 28 esta no
# topo deste modulo e e a base inteira deste numero.
#
# POR QUE O TETO NAO E REAPROVEITADO DE `FATOR_MAXIMO_DE_CONTAMINACAO` DIRETO,
# que e a primeira coisa que se tenta. Aquele fator e uma afirmacao CONTRA UMA
# ASSINATURA ESPECIFICA: "este recorte tem mais que o dobro dos pixels DESTE
# nome, entao nao pode ser ele". O aprendizado nao tem esse segundo termo. Ele
# roda exatamente quando o recorte NAO casou com ninguem (D-02), e numa
# instalacao nova a lista de assinaturas esta VAZIA, que e onde esta fase mais
# importa. Um teto que precisa de uma assinatura de referencia nao existe no
# unico caminho em que ele e indispensavel.
#
# Pior: hoje os dois se contradizem em silencio. `_pontuar_mascara` ZERA a
# pontuacao de um recorte contaminado, e o aprendiz le esse zero como "nao
# conheco ninguem parecido" e GRAVA. A regra que existia para proteger o
# reconhecimento estava alimentando o acervo. As entradas de 320, 336, 397, 399,
# 515 e 843 px pontuam 0.000 contra as quatro calibradas, MEDIDO, e foram
# aprendidas por causa disso.
#
# POR QUE E UMA FRACAO DO RECORTE, E NAO UM NUMERO DE PIXELS. A altura e a
# largura da regiao do nome saem do `calibration.json`: mudam com a resolucao,
# com a escala do Windows e com o tamanho da party window. Um teto em pixels
# absolutos seria a "constante que so vale na maquina de quem mediu" que este
# projeto proibe em todo lugar. Uma fracao da area sobrevive a recalibracao
# porque texto e recorte crescem juntos.
#
# E POR QUE NAO E RELATIVO A LARGURA OCUPADA, que era a outra candidata. Medido
# nas mesmas 28 mais as 4 calibradas, pixels por coluna ocupada:
#
#     nome limpo    1.36 a 3.16 px/coluna
#     contaminada   2.23 a 7.66
#
# As duas faixas se SOBREPOEM, e o motivo e estrutural: a contaminacao que mais
# importa e um risco fino atravessando o recorte inteiro, que aumenta o total e
# DIMINUI a densidade por coluna. Densidade dentro da caixa do texto sobrepoe
# ainda mais (7.54 a 39.53 contra 13.18 a 38.32). O total sobre a area do
# recorte e a unica das tres que ordena as duas faixas sem sobreposicao.
#
# ONDE O CORTE FICA, e aqui nao ha "meio do vazio" para se apoiar, entao a
# escolha vai escrita. Em fracao das 2200 celulas:
#
#     nome limpo (15 mascaras)    4.86% a 7.95%
#     contaminada (14 mascaras)   8.09% a 38.32%
#
# O vazio entre 7.95% e 8.09% e fino demais para ser um vazio: um corte ali
# estaria ajustado a dois pontos vizinhos. Os 10% ficam ACIMA de toda a faixa
# limpa com 26% de folga (220 px contra os 175 do maior nome limpo medido), o
# que cobre um nick uns 25% mais longo que o `WesleySniper` de 12 caracteres,
# com coroa. Custa deixar passar as tres de 178, 200 e 209 px, que sao nome
# dominante mais um risco fino, e pega as 11 piores.
#
# A ASSIMETRIA DECIDE ESSA TROCA, e ela e a mesma ja escrita para
# `celulas_toleradas`. Um teto baixo demais recusa um nick longo de verdade e a
# pessoa NUNCA ganha assinatura, em silencio. Um teto alto demais deixa passar
# mais tres perguntas. Recusar demais e o erro caro aqui, e nao o barato, porque
# a recusa por contaminacao FALA (ver `resumo_da_contaminacao`) enquanto a
# pessoa que nunca e aprendida nao fala.
#
# E A CORROBORACAO QUE FAZ DO NUMERO UM ACHADO, E NAO UMA ESCOLHA:
# `FATOR_MAXIMO_DE_CONTAMINACAO` (2.0) vezes a MENOR assinatura calibrada do
# usuario (PIRULITO, 110 px em 2200 celulas) da exatamente 220 px, que e 10%. As
# duas derivacoes, uma pela faixa das limpas e outra pela constante que o
# casamento ja usava, caem no mesmo lugar. `tests/test_aprendiz.py` prende as
# duas juntas, para nenhuma poder mudar calada.
TETO_DE_OCUPACAO_DO_NOME = 0.10


def teto_de_pixels_de_texto(mascara: np.ndarray) -> int:
    """Quantos pixels de texto ESTE recorte pode ter e ainda ser so um nome.

    Recebe a mascara e nao um numero de celulas porque e a mascara que o
    chamador tem na mao, e porque o teto so faz sentido ao lado do recorte de
    onde ele saiu. No recorte real do usuario (20x110 = 2200 celulas) o teto e
    220 px; num recorte de 20x100 ele e 200.

    O truncamento e para BAIXO (`int`), e nao arredondamento: numa fronteira o
    desfecho mais barato e recusar uma leitura que volta no proximo tick, e nao
    gravar uma a mais num acervo que nao tem comando de esquecer.
    """
    return int(mascara.size * TETO_DE_OCUPACAO_DO_NOME)

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


@dataclass(frozen=True, eq=False)
class Candidata:
    """Uma linha que o scanner esta vendo e nao sabe de quem e.

    O `indice` viaja SO PARA O DIAGNOSTICO — e o que faz a linha de log de D-07
    poder dizer QUAL linha recusou. Ele NUNCA entra em decisao nenhuma: a party
    window compacta quando alguem sai, e a linha 2 de agora pode ser outra
    pessoa daqui a um tick. O contador de estabilidade e por CONTEUDO (D-08), e
    um contador por indice somaria leituras de pessoas diferentes ate atingir N
    e gravaria uma assinatura de ninguem.

    `eq=False` porque a classe carrega um ndarray. O `__eq__` de dataclass
    compara os campos como tupla, `array == array` devolve um ARRAY, e `bool()`
    dele levanta `ValueError`. O atalho de identidade de
    `PyObject_RichCompareBool` esconde isso em quase todo teste, e foi assim que
    o crash de 02/09/2026 chegou ao usuario por `_Vigia`. Ver a docstring de
    `_Vigia` e o portao em `tests/test_dataclass_com_ndarray.py`.
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
class RecusaPorContaminacao:
    """Uma leitura recusada pelo TETO, com o numero que a recusou.

    O NUMERO E O REQUISITO, e nao um detalhe do diagnostico. Um teto que recusa
    calado troca a fila de perguntas de lixo que o usuario esta recebendo por um
    silencio inexplicavel: o aprendizado simplesmente para de acontecer, nada no
    log diz por que, e ele nao teria como saber que e o teto que esta recusando.
    E o mesmo argumento ja escrito para `RecusaPorInstabilidade`, com o mesmo
    desfecho: guardar a MEDIDA junto do fato.

    `celulas` viaja ao lado de `teto` porque o teto e uma FRACAO do recorte, e
    um teto sem o tamanho do recorte e um numero que o usuario nao consegue
    conferir contra nada.
    """

    indice: int
    pixels: int
    teto: int
    celulas: int


@dataclass(frozen=True)
class RetratoDaContaminacao:
    """A faixa dos recortes contaminados desta sessao, para uma linha de log.

    Minimo e maximo, e nao mediana, e a diferenca em relacao a
    `RetratoDasRecusas` tem razao. La a mediana existe porque o usuario vai
    ESCOLHER UM NUMERO a partir dela, e um outlier o faria escolher grande
    demais. Aqui nao ha nada para escolher: o teto e derivado e a acao certa e
    sair do terreno claro. O que o usuario precisa ver e o TAMANHO do estrago
    (o maior recorte que apareceu) e a distancia dele para o teto.

    Tudo vale `None` quando nao houve contaminacao nenhuma, que e o estado
    normal de uma party farmando em fundo escuro.
    """

    recusas: int = 0
    menor: int | None = None
    maior: int | None = None
    teto: int | None = None
    celulas: int | None = None


def resumo_da_contaminacao(retrato: RetratoDaContaminacao) -> str:
    """A linha que o usuario le no `scanner.log`. Sem acento e sem travessao.

    ELA NAO MANDA CONFIGURAR NADA, e essa e a diferenca inteira em relacao a
    `resumo_das_recusas`. A recusa por instabilidade termina numa linha pronta
    para copiar no `config.toml` porque existe um numero que o usuario controla.
    Aqui nao existe: o teto e derivado da area do recorte, e o unico limiar que
    o usuario poderia mexer (`VALOR_MINIMO_DO_TEXTO`) e o brilho minimo do
    texto, que vale para o RECONHECIMENTO de todo mundo e cujas assinaturas
    calibradas foram gravadas com o valor atual. Uma mensagem que mandasse mexer
    nele repetiria, com outra redacao, o defeito de 2026-09-01: obediencia que
    nao conserta e estraga outra coisa.

    Ela diz, entao, as tres coisas que sao verdade: quanto media o recorte, qual
    o teto, e que por isso nada foi gravado. Mais o que fazer, que e ESPERAR ou
    mover a party window, e nao editar arquivo nenhum.

    O ENCURTAMENTO DE 2026-09-02, e por que esta linha era o pior caso do
    projeto inteiro. Ela tinha 940 caracteres e o ultimo paragrafo dizia, com
    todas as letras, "NAO HA O QUE CONFIGURAR". Uma mensagem que termina
    avisando que nao ha nada a fazer nao precisa de 940 caracteres para
    chegar la: ela e RARA e INFORMATIVA, e nessa categoria o texto longo custa
    atencao e nao entrega nada.

    O QUE SAIU FOI O PARAGRAFO `causa` INTEIRO, com a medicao de campo que o
    sustenta: "a mascara de texto so tem PISO de brilho e nao tem teto, entao
    terreno claro passando atras do painel semitransparente entra junto com as
    letras. Medido em 01/09/2026 no acervo real: um nome limpo ocupa de 107 a
    175 pixel(es) no mesmo recorte, e as entradas de 290, 336, 399, 515 e 843
    eram pedra de Silent Valley gravada junto com a pessoa."

    ELE FICA REGISTRADO AQUI, e nao se perde: e a medicao que justifica o teto
    e quem for MEXER no teto precisa dela. Quem le o `scanner.log` no meio de
    um farm, nao. A explicacao de por que baixar `VALOR_MINIMO_DO_TEXTO`
    pioraria o reconhecimento de todo mundo tambem ficou aqui, pelo mesmo
    argumento: ela existe para dissuadir uma acao que a mensagem nao esta mais
    sugerindo.

    O QUE FICOU E O ACIONAVEL: os numeros (quanto mediu, qual o teto), que
    nada foi gravado, e as duas coisas que resolvem, que sao ESPERAR ou mover
    a party window para fundo escuro. Nenhum arquivo para editar, nenhum
    comando para digitar.
    """
    if retrato.maior is None or retrato.menor is None or retrato.teto is None:
        return "Nenhum recorte de nome recusado por contaminacao nesta sessao."

    return (
        f"Nao aprendi assinatura nova: contaminacao do recorte, "
        f"{retrato.recusas} recusa(s). O nome mediu de {retrato.menor} a "
        f"{retrato.maior} pixel(es) de texto e o teto e {retrato.teto}. "
        f"Nao ha o que configurar: volta sozinho quando a party sair do "
        f"terreno claro ou a party window ficar sobre fundo escuro."
    )


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

    O ENCURTAMENTO DE 2026-09-02, e o que ele NAO podia tocar. Esta e a linha
    RARA E ACIONAVEL do projeto: acontece uma vez por incidente e termina numa
    linha que o usuario copia para o `config.toml`. Encurtar aqui e diferente
    de encurtar um alerta de party, porque a instrucao E a mensagem.

    O QUE FICOU INTACTO, palavra por palavra: `celulas_toleradas = <valor>`,
    a mencao a secao `[identidade]` e ao `config.toml`, os quatro numeros (a
    faixa, a mediana, a tolerancia atual e o teto), e a fracao
    `abaixo_do_teto`/`medidas`, que e o numero que DECIDE se vale mexer.
    Nenhum deles e justificativa: sao o que o usuario confere e digita.

    O QUE SAIU FOI SO A EXPLICACAO DE CADA UM. O teto vinha com "que e a maior
    tolerancia que o reconhecimento aceita sem juntar duas pessoas numa
    assinatura so"; a sugestao vinha com "numero medido na SUA tela, e nao um
    palpite, e ja conferido contra o teto"; a turbulencia vinha com "nessa
    distancia o proprio reconhecimento ja trata as duas leituras como pessoas
    DIFERENTES" mais a lista de causas (party se remontando, cegueira,
    inventario por cima do nome). Tudo isso esta escrito nesta docstring e em
    `TETO_DE_CELULAS_TOLERADAS`, que e onde quem for mexer no teto vai olhar.

    A DIFERENCA ENTRE OS DOIS REGIMES CONTINUA GRITADA, porque os conselhos
    sao OPOSTOS: na cintilacao a linha entrega um valor, na turbulencia ela diz
    que subir NAO resolve. Um leitor que confundisse os dois copiaria um numero
    que nao conserta nada, que e o defeito de 2026-09-01 por outra porta.
    """
    cabeca = f"Nao aprendi assinatura nova: instabilidade, {retrato.recusas} recusa(s). "

    if retrato.menor is None or retrato.mediana is None:
        return (
            cabeca + "Sem distancia medida: as leituras tinham FORMAS "
            "diferentes, e entre recortes de tamanhos diferentes nao existe "
            "distancia. Nenhum valor de [identidade] celulas_toleradas muda "
            "isso."
        )

    faixa = (
        f"As leituras diferem de {retrato.menor} a {retrato.maior} celula(s), "
        f"mediana {retrato.mediana:.1f}; tolerancia atual {tolerado}, teto "
        f"{TETO_DE_CELULAS_TOLERADAS} ({retrato.abaixo_do_teto} das "
        f"{retrato.medidas} cabem nele). "
    )

    if retrato.regime == REGIME_DE_CINTILACAO:
        acao = (
            "E cintilacao da borda das letras, e a tolerancia resolve. No "
            "config.toml, secao [identidade], escreva: celulas_toleradas = "
            f"{retrato.sugestao}"
        )
    else:
        acao = (
            "Subir [identidade] celulas_toleradas NAO resolve: a mediana passa "
            "do teto. Isso e a party se remontando, e a saida e esperar ela "
            "estabilizar."
        )

    return cabeca + faixa + acao


@dataclass(frozen=True)
class ResultadoDoAprendiz:
    """O que uma leitura produziu. As tres listas VAZIAS sao o estado normal.

    As DUAS recusas viajam separadas de proposito. Instabilidade e contaminacao
    parecem a mesma coisa ("nao aprendi") e pedem respostas OPOSTAS: uma tem um
    numero no `config.toml` que a resolve, a outra nao tem nada para configurar
    e so passa quando a party sair do terreno claro. Junta-las numa lista so
    obrigaria o leitor a desempatar por um campo, e a primeira mensagem escrita
    depois disso daria o conselho errado para metade dos casos.
    """

    aprendizados: list[Aprendizado] = field(default_factory=list)
    recusas: list[RecusaPorInstabilidade] = field(default_factory=list)
    recusas_por_contaminacao: list[RecusaPorContaminacao] = field(
        default_factory=list
    )


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


@dataclass(eq=False)
class _Vigia:
    """Uma sequencia de leituras em andamento, chaveada pelo CONTEUDO.

    A `ancora` e a PRIMEIRA mascara da sequencia e nunca e atualizada. Ver
    `Aprendiz.observar` para a razao inteira.

    `eq=False` E O CONSERTO DE 02/09/2026, E NAO UM DETALHE DE ESTILO. Com o
    `__eq__` gerado, `disponiveis.remove(vigia)` derrubava o aprendizado da
    sessao inteira:

        File "l2scanner/aprendiz.py", line 1013, in observar
          disponiveis.remove(vigia)
        File "<string>", line 4, in __eq__
        ValueError: The truth value of an array with more than one element is
        ambiguous. Use a.any() or a.all()

    O `__eq__` de dataclass compara os campos como TUPLA, e a comparacao de
    tupla comeca no campo 0, que aqui e um ndarray. `array == array` devolve um
    ARRAY, e `bool()` de um array de 2000 celulas nao existe.

    O ATALHO DE IDENTIDADE DO CPython E O QUE EXPLICA A INTERMITENCIA. `remove`
    (e `in`, e `index`, e `count`) usa `PyObject_RichCompareBool`, que devolve
    `True` sem chamar `__eq__` quando o item da lista E o proprio objeto
    procurado. Com UM vigia na mesa, ou com o alvo na primeira posicao, o
    atalho responde e nada quebra. So estoura quando existe um vigia ANTES do
    alvo, que e o unico que chega a ser comparado. Em campo isso apareceu com
    DUAS linhas nao reconhecidas ao mesmo tempo (`Membro 2` e `Membro 4`), e a
    suite ficou verde por anos porque exercitava um vigia de cada vez.

    A SEMANTICA CORRETA DESTA CLASSE E IDENTIDADE, e nao igualdade estrutural.
    Dois vigias sao DUAS sequencias em andamento, em linhas diferentes da party
    window, contando leituras separadas. Se a ancora igual os tornasse iguais,
    remover um poderia tirar o OUTRO da mesa e a contagem de alguem sumiria sem
    erro nenhum. `eq=False` faz `__eq__` cair para `object.__eq__`, que e
    identidade, que e a resposta certa.

    POR QUE `eq=False` E NAO REMOVER POR INDICE. Trocar o `remove` por um
    `del disponiveis[i]` consertaria aquela linha e deixaria a classe capaz do
    mesmo defeito no proximo `in`, `index`, `count` ou `==` que alguem
    escrevesse, com o atalho de identidade escondendo o erro na maioria dos
    testes. `eq=False` mata a capacidade, e nao a ocorrencia. `tests/
    test_dataclass_com_ndarray.py` estende isso a arvore inteira.
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
        self._pixels_contaminados: list[int] = []
        self._teto_da_contaminacao: int | None = None
        self._celulas_da_contaminacao: int | None = None

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

    def retrato_da_contaminacao(self) -> RetratoDaContaminacao:
        """O acumulado das recusas pelo TETO nesta sessao.

        Separado de `retrato` pela mesma razao que as duas listas de recusa sao
        separadas: as duas faixas nao se misturam, tem unidades diferentes
        (celulas de diferenca contra pixels de texto) e levam a conselhos
        opostos.
        """
        if not self._pixels_contaminados:
            return RetratoDaContaminacao()
        return RetratoDaContaminacao(
            recusas=len(self._pixels_contaminados),
            menor=min(self._pixels_contaminados),
            maior=max(self._pixels_contaminados),
            teto=self._teto_da_contaminacao,
            celulas=self._celulas_da_contaminacao,
        )

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

        2. RECORTE COM TEXTO DEMAIS E DESCARTADO, e este portao e o irmao do de
           cima: o piso pergunta "isto e vazio?" e o teto pergunta "isto e SO um
           nome?". Ele nasceu de uma medicao e nao de uma simetria — 24 das 28
           entradas do acervo real do usuario entraram por aqui, e as piores
           tinham 515 e 843 pixels de pedra de Silent Valley. O detalhe que fecha
           o caso: `_pontuar_mascara` ZERA a pontuacao de um recorte
           contaminado, e sem este portao o passo 3 leria esse zero como "nao
           conheco ninguem parecido" e gravaria. Ver `TETO_DE_OCUPACAO_DO_NOME`.

        3. CASAMENTO ACIMA DO LIMIAR E DESCARTADO (D-02). `Casamento(None, ...)`
           chega por DOIS motivos diferentes, que pedem desfechos opostos:

               melhor pontuacao < 0.75      "nao conheco ninguem parecido"  APRENDE
               >= 0.75 e sem margem         "conheco DOIS parecidos demais"  CALA

           Aprender no segundo caso e o pior desfecho deste workstream:
           acrescentar ao acervo um quase-duplicado de alguem faz essa pessoa
           PARAR de ser reconhecida — as duas assinaturas se sombreiam e as duas
           caem no silencio pela margem. Medido na Fase 1: virando 8 celulas, a
           original casa 1.000 e a copia 0.921, diferenca 0.079, ABAIXO dos 0.12
           de `MARGEM_MINIMA_SOBRE_O_SEGUNDO`.

        4. CASAMENTO COM O VIGIA MAIS PROXIMO DE FORMA IGUAL. Distancia
           `<= celulas_toleradas` conta como "a mesma leitura" e incrementa
           aquele vigia. Distancia maior RECUSA, e a candidata vira um vigia NOVO
           com contagem 1 — que e a forma exata de "instabilidade REINICIA a
           sequencia" de D-08. Nada de media e nada de mediana: uma assinatura
           media de duas leituras diferentes e uma assinatura de ninguem.

        5. VIGIAS QUE NINGUEM CASOU NESTA LEITURA SAO DESCARTADOS. Isso mantem a
           estrutura limitada pelo numero de linhas da party window (T-02-09) e e
           a outra metade do reinicio de D-08.

        6. VIGIA QUE CHEGOU A `leituras_para_aprender` GRAVA, com `nome=""`.

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
        contaminadas: list[RecusaPorContaminacao] = []

        disponiveis = list(self._vigias)
        sobreviventes: list[_Vigia] = []
        tolerado = self._ajustes.celulas_toleradas

        for candidata in sorted(candidatas, key=lambda c: c.indice):
            pixels = int(candidata.mascara.sum())
            if pixels < PIXELS_MINIMOS_DE_TEXTO:
                continue

            teto = teto_de_pixels_de_texto(candidata.mascara)
            if pixels > teto:
                self._pixels_contaminados.append(pixels)
                self._teto_da_contaminacao = teto
                self._celulas_da_contaminacao = int(candidata.mascara.size)
                contaminadas.append(
                    RecusaPorContaminacao(
                        indice=candidata.indice,
                        pixels=pixels,
                        teto=teto,
                        celulas=int(candidata.mascara.size),
                    )
                )
                # O `continue` faz DUAS coisas, e a segunda e a que importa: a
                # candidata nao vira vigia novo E o vigia que ela sustentava
                # fica fora de `sobreviventes`, entao a sequencia REINICIA. E o
                # mesmo desfecho que a instabilidade produz (D-08), pela mesma
                # razao: um frame em que nao da para confiar nos pixels nao e
                # evidencia de nada, e deixa-lo contar faria as cinco leituras
                # somarem frames em que o nome estava debaixo de pedra.
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
        return ResultadoDoAprendiz(
            aprendizados=aprendizados,
            recusas=recusas,
            recusas_por_contaminacao=contaminadas,
        )

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
