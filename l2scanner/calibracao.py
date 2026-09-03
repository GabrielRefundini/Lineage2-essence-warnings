"""Calibracao: onde ficam as coisas na tela e que cores contam como barra cheia.

Separada da configuracao escrita a mao de proposito. A calibracao e gerada por
ferramenta e sobrescrita a cada recalibragem; a configuracao e escrita pelo
usuario. Se morassem no mesmo arquivo, a ferramenta apagaria os ajustes manuais
na primeira vez que rodasse.

A calibracao guarda a geometria de tela sob a qual foi feita. Se a resolucao ou
o arranjo de monitores mudar, os retangulos gravados nao significam mais a mesma
coisa — e o scanner se recusa a iniciar em vez de medir a regiao errada calado.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .frames import Regiao
from .identidade import Assinatura

VERSAO_DO_ESQUEMA = 2

# O TETO da `mercado_folga_de_cola_do_glifo`, e ele e UMA VERDADE SO: a
# varredura `tools/medir_largura_de_run.py` varre de 0 ate ele com passo 1, e a
# carga cobra a mesma faixa. Dois numeros aqui deixariam a ferramenta propor um
# valor que o arranque recusa.
#
# POR QUE 4. Com os moldes de producao (larguras 1, 4 e 6) a folga 4 ja libera
# TODA largura de 1 a 10, que passa do maior run largo observado no censo (12
# px, que e `4`+`4`). Acima disso a tabela de candidatas so repetiria a mesma
# linha, e o teto existe para que o relatorio mostre os DOIS lados do vao — sem
# o lado ruim na tabela, "a folga tem teto" seria promessa e nao medicao.
TETO_DA_FOLGA_DE_COLA = 4

# Faixa padrao onde procurar o banner de manutencao, derivada da party window.
#
# O banner do jogo aparece POR CIMA da party window, na faixa superior
# esquerda, e e MUITO mais largo que as barras (o texto tem umas 60 colunas
# contra os 120 px das barras).
#
# ESTES NUMEROS DEIXARAM DE SER PALPITE (D-f). Agora existe a conta, feita
# contra a calibracao REAL do usuario (`party_window_na_janela` topo=222,
# medida em 2026-08-24) e contra a estimativa do banner no screenshot dele:
#
#     numeros antigos (60/140) -> faixa em y 162..302 na janela
#     banner estimado          -> y ~168..253
#     folga no topo            -> ~6 px
#
# SEIS PIXELS DE FOLGA CONTRA UMA ESTIMATIVA QUE TEM INCERTEZA. Errar por 6 px
# corta o titulo `Server Maintence`, que e literalmente o que
# `eh_banner_de_manutencao` procura — e o recurso inteiro cala, sem sintoma
# nenhum alem do silencio.
#
#     numeros novos (130/240)  -> faixa em y 92..332
#     folga                    -> ~76 px em cima, ~79 px embaixo
#
# A MEDICAO QUE AUTORIZA A FOLGA: area extra NAO piora a precisao. Na fixture
# real, a imagem INTEIRA em cinza tambem leu 0:40:26 — o motor nao se perde por
# receber vizinhanca.
#
# O CUSTO DA FAIXA MAIOR FOI MEDIDO, e nao extrapolado: na banda de 732x240 ja
# aquecida, a passada de deteccao (cinza 2x) custa 23 ms e a de conferencia
# (3x) custa 31 ms. A cada 5 s isso e ~0,5% de um nucleo. A folga vertical sai
# de graca.
#
# O PRECO NOVO QUE A FOLGA CRIA, real e aceito: mais area significa mais texto
# vizinho dentro da faixa, e a guarda estrutural de `interpretar_banner` (D-b)
# prefere calar a arriscar. Se um texto vizinho trouxer uma forma que pareca
# unidade de minutos sem numero, a leitura se perde. Perder uma leitura custa 5
# segundos; cortar o titulo custa o recurso inteiro.
#
# Generoso e melhor que justo aqui: veja `Calibracao.regiao_do_banner`.
MARGEM_ESQUERDA_DO_BANNER = 40
MARGEM_ACIMA_DO_BANNER = 130
LARGURA_EXTRA_DO_BANNER = 560
ALTURA_DA_FAIXA_DO_BANNER = 240


class CalibracaoInvalida(Exception):
    """A calibracao nao existe, esta corrompida ou nao vale para esta tela."""


@dataclass(frozen=True)
class LimiaresDeCor:
    """Que pixels contam como preenchimento de uma barra.

    A SATURACAO e o discriminador principal, nao o matiz. Motivo medido na tela
    real: a parte vazia da barra e transparente e mostra o terreno do jogo
    (S~75), enquanto a barra cheia e solida (S~210). O terreno muda de cor entre
    zonas, mas nunca fica saturado como a barra.

    Para o vermelho, `matiz_min` > `matiz_max` sinaliza a volta no circulo de
    matiz: a faixa vale de matiz_min ate 179 E de 0 ate matiz_max.
    """

    matiz_min: int
    matiz_max: int
    saturacao_min: int
    valor_min: int


@dataclass(frozen=True)
class LayoutDaParty:
    """Geometria das linhas de membro, tudo RELATIVO a party_window.

    As linhas sao uniformes e igualmente espacadas, entao um passo unico
    descreve todas — nao e preciso listar retangulo por retangulo.
    """

    # Icone de classe — o indicador de presenca da linha
    icone_x: int
    icone_y: int  # do primeiro membro
    icone_tamanho: int

    # Barras (HP e MP compartilham x, largura e altura)
    barra_x: int
    barra_largura: int
    barra_altura: int
    hp_y: int  # do primeiro membro
    mp_y: int  # do primeiro membro

    passo: int  # distancia vertical entre membros consecutivos
    max_linhas: int

    # Recorte do NOME, relativo ao icone da mesma linha. Fica logo acima dele.
    # O recorte precisa ser JUSTO: medido na tela real, um recorte largo deixa
    # o terreno dominar a comparacao e a margem entre nomes cai de 0.55 para
    # 0.04 — a diferenca entre funcionar e nao funcionar.
    #
    # A MEDICAO QUE FIXA ESTES DOIS NUMEROS. Colunas da JANELA, tela viva do
    # usuario em 2026-08-31, com `icone_x = 12`:
    #
    #     emblema de classe      13 a 26
    #     nome SEM coroa         comeca em 30
    #     coroa do lider         31 a 44
    #     nome COM coroa         comeca em 48
    #     recorte com dx = 26    comecava em 38   <- 8 colunas do nome perdidas
    #
    # Com `nome_dx = 26` a esquerda caia em 12+26 = 38, ou seja DENTRO do nome,
    # e cada assinatura era gravada mutilada: "TANDER", "RULTO", "elazkez". O
    # corte era CONSTANTE, entao ele nao aparecia — o pedaco gravado casava com
    # o mesmo pedaco na tela. O que ele quebrava era a MUDANCA de lider: a coroa
    # desloca o nome 18 colunas, e com 8 ja perdidas na esquerda o pedaco que
    # sobra dentro do recorte deixa de ser o mesmo. Visto em campo: os dois
    # membros que o scanner perdeu foram exatamente os dois cuja condicao de
    # lider mudou entre a calibracao e o dia do teste.
    #
    # `nome_dx = 16` poe a esquerda em 28, dois pixels depois do fim do emblema.
    # `nome_largura = 110` devolve as mesmas 10 colunas na direita, entao a
    # borda direita continua em 138 e o fim do nome do lider (coluna 93) segue
    # dentro. O recorte anda para a esquerda sem ficar mais largo do que era.
    nome_dx: int = 16  # a partir do icone, logo apos o emblema de classe
    nome_dy: int = -24
    nome_largura: int = 110
    nome_altura: int = 20

    # Limiares de contraste para "tem icone aqui".
    # Medidos na tela real: linha com membro da desvio 43-52 e 46-52% de pixels
    # escuros; linha vazia da desvio 9-10 e 0% escuros. O corte fica no meio da
    # margem, bem longe dos dois lados.
    icone_desvio_min: float = 25.0
    icone_escuros_min: float = 0.15

    # A ancora da janela e mais fraca que o icone (moldura fina), entao seu
    # corte e mais baixo. Medido: canto da moldura da desvio 35, terreno da 8-12.
    ancora_desvio_min: float = 20.0
    ancora_escuros_min: float = 0.02

    # Brilho maximo da borda vertical da barra para ela contar como intacta.
    # A UI desenha uma linha escura nas duas pontas de cada barra, e ela existe
    # igual com a barra cheia ou vazia — e chrome, nao preenchimento. Some
    # apenas quando outra janela do jogo cobre a party window.
    # Medido na tela real: barra livre da V~8-11 (cheia OU vazia, identico),
    # coberta pelo inventario da V~72-112. O corte fica no meio dessa margem.
    borda_v_max: float = 40.0


@dataclass
class Calibracao:
    """Onde ficam as coisas na tela deste usuario."""

    # A janela inteira da party — e o que o scanner captura a cada tick
    party_window: Regiao

    # Ancora de visibilidade da UI, RELATIVA a party_window.
    # Fica no TOPO porque a janela e ancorada em cima e encolhe por baixo
    # conforme a PT diminui; uma ancora embaixo sumiria sozinha com menos gente.
    ancora: Regiao

    layout: LayoutDaParty
    limiares_hp: LimiaresDeCor
    limiares_mp: LimiaresDeCor

    # Geometria da tela quando isto foi calibrado, para detectar mudanca
    geometria_da_tela: str

    # Barra de HP do proprio personagem. Fica no TOPO da janela do jogo, longe
    # da party window — o usuario nao aparece na propria party window, entao
    # sem isto a morte DELE nunca seria detectada. E justamente quem tem mais
    # chance de morrer AFK, porque e o unico sem outra pessoa olhando.
    #
    # Guardada em coordenadas RELATIVAS a janela do jogo, como a party window.
    hp_proprio: Regiao | None = None

    # Nome do proprio personagem, para o alerta dizer quem morreu.
    nome_proprio: str | None = None

    # Nomes dos membros, em ordem de linha. Fonte da verdade para identidade —
    # nunca leitura de texto da tela, que erraria um glifo e inventaria um
    # membro fantasma entrando e saindo da party.
    nomes: list[str] = field(default_factory=list)

    # Assinaturas visuais dos nomes, gravadas na calibracao. Sao elas que
    # permitem dizer QUEM morreu mesmo quando a ordem da party muda — sem elas
    # a identidade viria da posicao da linha, e um alerta com o nome errado
    # manda a party socorrer a pessoa errada.
    assinaturas: list = field(default_factory=list)

    # Titulo da janela do jogo a que esta party window pertence. Descoberto
    # pela calibracao. Com duas instancias abertas, adivinhar daria errado — e
    # errar aqui significa vigiar a party do personagem errado.
    janela: str | None = None

    # A MESMA party window, mas em coordenadas relativas ao canto da janela do
    # jogo. `party_window` esta em coordenadas de desktop, que so valem
    # enquanto a janela nao se mexer; esta aqui sobrevive a arrastar o jogo
    # para outro lugar da tela, porque acompanha a janela.
    party_window_na_janela: Regiao | None = None

    # Onde o banner de manutencao aparece, se o usuario quiser dizer.
    #
    # OPCIONAL de proposito, e por isso a VERSAO_DO_ESQUEMA SEGUE EM 2: o
    # `carregar` recusa qualquer versao diferente da constante, entao subir para
    # 3 invalidaria o `calibration.json` que o usuario mediu a mao e o obrigaria
    # a recalibrar tudo por causa de um campo opcional.
    #
    # A regiao padrao (`regiao_do_banner`) e um palpite educado sobre onde o
    # banner cai, e `python -m l2scanner --testar-manutencao` e como o usuario
    # descobre se o palpite acertou. Errando, ele corrige AQUI — sem tocar em
    # codigo.
    #
    # REFERENCIAL: como `hp_proprio`, esta regiao vale para o caminho
    # `--janela` (coordenadas relativas ao canto da janela do jogo). Quem
    # configurar a mao para o caminho `mss` precisa escrever coordenadas de
    # DESKTOP. O `--testar-manutencao` imprime a regiao justamente para essa
    # conferencia.
    banner_manutencao: Regiao | None = None

    # Regioes, relativas a janela do jogo, para o aviso de Tiat. Nao ha
    # coordenada padrao honesta: chat e alvo mudam conforme o HUD do jogador.
    # Sao opcionais para uma calibracao anterior continuar funcionando igual.
    tiat_chat: Regiao | None = None
    tiat_alvo: Regiao | None = None

    # --- Mercado (World Exchange / "XM Market") ---
    #
    # OPCIONAIS de proposito, e por isso a VERSAO_DO_ESQUEMA SEGUE EM 2, pelo
    # mesmo motivo escrito acima para o `banner_manutencao`: o `carregar` recusa
    # qualquer versao diferente da constante, entao subir para 3 invalidaria o
    # `calibration.json` que o usuario mediu a mao e o obrigaria a recalibrar
    # tudo por causa de campos que ele talvez nem use. Uma instalacao sem
    # calibracao de mercado carrega igual e a feature simplesmente fica OFF.
    #
    # Onde fica a faixa de titulo do painel, em coordenadas da JANELA do jogo.
    #
    # ATENCAO, medido em `recordings/inv3/`: o painel ANDA. Entre dois frames da
    # mesma gravacao ele apareceu 181 px a esquerda e 143 px abaixo, com a mesma
    # arte casando 0.9996. Este retangulo e a posicao de REFERENCIA de onde o
    # molde foi cortado — nao a promessa de que o painel estara sempre ali. Quem
    # consome precisa localizar antes de comparar (ver `mercado_visao`).
    mercado_ancora: Regiao | None = None

    # O molde da ancora empacotado: {"altura", "largura", "bytes" em hex}.
    #
    # Guardado como dict CRU, sem decodificar. Decodificar aqui obrigaria
    # `calibracao.py` a importar numpy so para carregar um arquivo de
    # configuracao. Quem decodifica e `mercado_visao.molde_de_hex`, que ja
    # confere as dimensoes declaradas contra o tamanho real dos bytes.
    mercado_molde_da_ancora: dict | None = None

    # O limiar de casamento desta instalacao. A calibracao do usuario e a
    # autoridade sobre a tela dele; `mercado_visao.CASAMENTO_MINIMO_DA_ANCORA`
    # e so o padrao medido para quem ainda nao calibrou.
    mercado_limiar_da_ancora: float | None = None

    # Carimbo de contexto da captura: as dimensoes da janela no momento em que o
    # molde foi cortado. Com a janela em outro tamanho, o molde foi cortado numa
    # escala diferente e o casamento cai sem explicacao. Isto existe para o
    # arranque RECUSAR a leitura de mercado com "recalibre", em vez de ler
    # degradado calado.
    mercado_geometria_da_captura: dict | None = None

    # As ANCORAS do painel, cada uma com nome, deslocamento a partir da origem
    # (o canto da faixa de titulo) e molde empacotado.
    #
    # POR QUE MAIS DE UMA, medido nas 8 gravacoes de campo: a tooltip do jogo e
    # desenhada onde o cursor estiver, INCLUSIVE sobre a faixa de titulo. Com a
    # faixa sozinha, um frame de painel ABERTO marcou 0.4110 e um de painel
    # FECHADO marcou 0.4753 — margem NEGATIVA, as classes se sobrepondo. Com
    # varias ancoras espalhadas e votacao pelo maximo, a margem volta a +0.3700.
    # Ver `mercado_visao.AncoraDoPainel` e o 01-04-SUMMARY.
    #
    # Lista CRUA, sem decodificar, pela mesma razao de `mercado_molde_da_ancora`:
    # decodificar aqui obrigaria um modulo de configuracao a importar numpy.
    mercado_ancoras: list | None = None

    # Geometria da grade de negociacao: origem, altura de linha, linhas por
    # pagina e os retangulos das colunas.
    #
    # NAO EXISTE "a grade": existem TRES layouts de coluna (grade de negociacao,
    # aba Adena, tela de busca), com numeros e significados de coluna
    # diferentes. Por isso este dict guarda tambem QUAL layout foi calibrado —
    # ler a coluna errada com confianca e o modo de falha caro aqui.
    mercado_grade: dict | None = None

    # Um molde por item da watchlist, com o nome COMO RENDERIZADO — prefixo
    # `+N ` incluso quando houver. O item sem encanto nao escreve `+0`: o molde
    # dele e o nome puro. Misturar `+3` e `+4` na mesma serie nao acrescenta
    # ruido, destroi a serie: medido, o mesmo item base valia de 7,02 a 100,00
    # na mesma pagina conforme o encanto.
    mercado_templates_de_nome: list | None = None

    # Um molde por glifo: os dez digitos e a virgula, mais as palavras `XM Coin`
    # e `Adena`. As duas palavras nao sao decoracao — a virgula e separador de
    # MILHAR e de DECIMAL na mesma linha (`5,000,000 Adena` ao lado de
    # `62,00 XM Coin`), e quem desambigua e o sufixo, nao o numero.
    mercado_templates_de_digito: list | None = None

    # O SEGUNDO conjunto de moldes, cortado sobre texto CROMATICO (o ciano dos
    # precos), e uma CHAVE PROPRIA e nao um apendice do conjunto de cima.
    #
    # SEPARADA POR MEDICAO, E NAO POR ARRUMACAO. Os moldes de cima foram
    # cortados com piso de brilho ABSOLUTO (V > 180) sobre texto BRANCO de pico
    # 226-230; o ciano desenha o MESMO glifo com pico 255, e a borda
    # antisserrilhada — que fica a ~0,62 do caminho entre o fundo e o pico —
    # atravessa o piso. O `0` branco e gravado como um anel PARTIDO de 8 px; o
    # `0` ciano observado e um anel FECHADO de 16 px, e anel fechado casa com
    # `8` (0,7242) melhor que com o `0` partido (0,5976). A forma que um molde
    # codifica so se reproduz no brilho em que ele foi cortado.
    #
    # E POR ISSO ELAS NAO PODEM COMPARTILHAR CHAVE: `fundir_glifos` funde por
    # ROTULO, entao cortar treze glifos cianos na mesma lista APAGARIA os treze
    # brancos, calado, e o caminho branco — que e o que hoje vira dado — sairia
    # ilegivel de uma sessao de calibracao que o usuario acharia bem-sucedida.
    # Com duas chaves isso deixa de ser uma regra a lembrar e passa a ser
    # impossivel.
    mercado_templates_de_digito_cromatico: list | None = None

    # O limiar SUGERIDO pela matriz de confusao medida na calibracao, com
    # margem sobre o pior score inter-classe daquela watchlist.
    mercado_limiar_de_template: float | None = None

    # O limiar dos GLIFOS, derivado da matriz de confusao DELES.
    #
    # CHAVE SEPARADA da de template, e nao duplicacao: sao dois conjuntos
    # fechados diferentes, com matrizes diferentes e piores pares diferentes. A
    # watchlist e do usuario e muda a cada edicao do `config.toml`; o conjunto
    # de glifos e fixo pela fonte do jogo. Um numero unico servindo aos dois
    # seria derivado de uma medicao e aplicado a outra.
    #
    # Opcional via `.get` (D-07), no precedente do `banner_manutencao`: uma
    # instalacao que ainda nao cortou glifos continua carregando.
    mercado_limiar_de_glifo: float | None = None

    # --- Leitura de pagina (Fase 02) ---
    #
    # AS QUATORZE ABAIXO SEGUEM O MESMO TRILHO DAS DE CIMA, E PELO MESMO MOTIVO:
    # campo opcional, `.get` no `carregar`, `VERSAO_DO_ESQUEMA` INTACTA em 2. O
    # `calibration.json` da maquina do usuario carrega 13 moldes de glifo e 3
    # ancoras que so a mao dele produz; um bump de versao os apagaria por causa
    # de campos que uma instalacao sem leitura de mercado nem preenche.
    #
    # AS QUATRO COLUNAS: `{"dx": int, "largura": int}`, deslocamento em x
    # relativo a ORIGEM DO PAINEL (o canto da faixa de titulo) e largura em px.
    # Deslocamento e nao coordenada absoluta, pela mesma razao ja escrita na
    # docstring de `calibrar_mercado.derivar_grade`: o painel ANDA 827x831 px
    # entre dois frames da mesma gravacao. Uma coluna gravada em absoluto
    # apontaria para o vazio assim que o usuario arrastasse a janela, e o
    # sintoma seria numero plausivel lido da coluna errada.
    mercado_coluna_do_nome: dict | None = None
    mercado_coluna_da_quantidade: dict | None = None
    mercado_coluna_do_total: dict | None = None

    # A COLUNA DO UNITARIO NAO VAI PARA O CSV, E AINDA ASSIM E LIDA.
    #
    # Ela e a unica LEITURA INDEPENDENTE do mesmo fato que o `Total` afirma, e
    # por isso e a materia-prima da guarda de cruzamento contra o par `0`x`8` —
    # cuja margem medida e 0,0370, a mais estreita do sistema inteiro, e o unico
    # modo de falha que a gramatica do numero NAO pega: um `0` lido como `8`
    # mantem a gramatica intacta.
    #
    # O que sai da leitura continua sendo `Total` e `Quantity`. Reconstruir o
    # total a partir do unitario devolveria um numero que nunca existiu — a tela
    # mostra `0,83` para `40,00 / 48`, e `0,83 x 48` da `39,84`.
    mercado_coluna_do_unitario: dict | None = None

    # O molde do CABECALHO DE COLUNA, que e como o layout e reconhecido (D-11):
    # `{"layout", "dy", "altura", "largura", "bytes" em hex, "corte_de_brilho"}`.
    #
    # Dict CRU, sem decodificar, pela mesma razao de `mercado_molde_da_ancora`:
    # decodificar aqui obrigaria um modulo de configuracao a importar numpy.
    # Quem decodifica e `mercado_visao.cabecalho_de_calibracao`.
    #
    # `corte_de_brilho` MORA NO ARQUIVO E NAO NO FONTE porque ele foi medido em
    # UMA resolucao (1720x1392) e UMA pele. A medicao da pesquisa: rotulos de
    # coluna com V maximo 229, a seta de ordenacao com 181, a borda da banda com
    # 201 — um corte no meio remove a seta E a borda sem uma linha de geometria.
    # A seta anda de celula conforme a ordenacao, e um molde cortado COM ela nao
    # casa a mesma coluna sem ela.
    mercado_cabecalho_de_coluna: dict | None = None

    # O limiar de casamento do molde do cabecalho.
    #
    # PROVISORIO POR CONSTRUCAO na rodada em que e gravado: o molde casa contra
    # o proprio frame de onde foi cortado, o que da ~1,0 e nao prova nada sobre
    # casar OUTRO frame. Quem confirma e o portao de layout, rodando-o contra
    # bandas de negociacao em duas ordenacoes e contra Adena e busca.
    mercado_limiar_do_cabecalho: float | None = None

    # Onde medir a FAIXA DE FUNDO da linha para detectar oclusao:
    # `{"dx0": int, "dx1": int, "dy0": int, "dy1": int, "folga": int}` — uma
    # BANDA horizontal fina, atravessando a linha inteira em x, dentro de uma
    # faixa de altura que fica ACIMA do texto.
    #
    # O sinal de oclusao e o fundo alternado, e nao a confianca do casamento: a
    # tooltip do jogo e SEMITRANSPARENTE, entao um numero coberto ainda produz
    # glifos plausiveis com boa confianca e valor errado. Recusar pela confianca
    # seria o incidente 27x um nivel acima.
    #
    # `dy0`/`dy1` ENTRARAM EM 2026-09-01 e sao OPCIONAIS, de proposito. Sem eles
    # vale a linha inteira em altura, que e a geometria de 31/08 — a que o campo
    # quebrou duas vezes, mas que erra FECHADO. Uma calibracao antiga nao pode
    # impedir o programa de subir; ela so precisa ser recalibrada, e
    # `mercado_pagina` avisa isso no log uma vez.
    #
    # A razao de a faixa vertical existir: o nome do item cresce em X e nao em
    # Y. Sonda vertical (a linha inteira, num trecho estreito de x) compete com
    # o texto e perde na primeira aba de nomes compridos; banda horizontal fina
    # numa margem vertical nunca compete. Ver `mercado_leitura.linha_ocluida`.
    mercado_sonda_do_fundo: dict | None = None

    # Acima desta dispersao, o trecho de fundo nao e fundo: ha algo desenhado
    # por cima e a linha e descartada. Faixa valida `[0.0, 1.0]`.
    mercado_limiar_de_dispersao_do_fundo: float | None = None

    # O PISO e a MARGEM da leitura de glifo EM PRODUCAO.
    #
    # NAO SAO `mercado_limiar_de_glifo`, e a confusao entre os dois e cara o
    # bastante para merecer o registro. Aquele e derivado de `(1.0 + pior_par)/2`
    # e certifica que o CONJUNTO de moldes e separavel — medido molde contra
    # molde, NUNCA contra glifo de tela.
    #
    # A MEDICAO QUE REFUTA O REAPROVEITAMENTO: sobre 2.057 glifos reais das
    # gravacoes, o `8` casou o proprio molde com mediana 0,7242. O valor gravado
    # na maquina do usuario e 0,8555 — um piso ali rejeitaria praticamente todo
    # `8` da tela, e a leitura morreria calada. O registro fica aqui no padrao de
    # `ocr.py:36-39`: um numero que caiu precisa dizer que caiu, senao ele volta
    # na proxima leitura.
    #
    # Os dois sao MEDIDOS pela ferramenta do plano 02-02, nunca escritos a mao.
    mercado_limiar_de_leitura_de_glifo: float | None = None
    mercado_margem_de_leitura_de_glifo: float | None = None

    # O CORTE e o PISO do agrupamento de nomes por similaridade (`difflib`).
    #
    # Acima do corte, duas leituras sao a mesma serie. Abaixo do piso, sao series
    # diferentes. ENTRE OS DOIS fica a faixa cinzenta, onde a linha nao agrupa
    # NEM cria serie: e descartada com aviso. Fusao no CSV e irreversivel;
    # descarte nao e.
    #
    # O 88 do `rapidfuzz.WRatio` NAO vale aqui e o registro da refutacao fica
    # junto: trocada a metrica, o numero e heranca de outro contexto. Medidos
    # pela ferramenta do 02-02, nunca escolhidos.
    mercado_corte_de_similaridade: float | None = None
    mercado_piso_de_similaridade: float | None = None

    # A tolerancia da GUARDA DE CRUZAMENTO: `Total` contra `Unit price x
    # Quantity`, em centesimos por unidade.
    #
    # AUSENTE OU `None` NAO E ERRO NEM ESQUECIMENTO: e a guarda DESLIGADA, e esse
    # e o default seguro. Quem decide se ela liga e a MEDICAO do plano 02-02,
    # nunca o autor do codigo — o unitario exibido e arredondado, entao a folga
    # honesta so se conhece medindo a distribuicao do erro de arredondamento
    # sobre as gravacoes.
    #
    # Uma guarda desligada e honesta; uma guarda cega, com tolerancia larga
    # demais, e uma peneira que aprova exatamente a substituicao `0`->`8` que ela
    # existe para pegar. Por isso a faixa valida e `>= 0` e o negativo e recusado.
    mercado_tolerancia_do_cruzamento: float | None = None

    # O PISO DE LINHAS COMPARADAS do estabilizador de pagina.
    #
    # Ele impede o ACORDO TRIVIAL: quando quase toda linha de uma pagina e
    # descartada por oclusao, as poucas que sobram concordam entre dois frames
    # POR FALTA DE MATERIAL, e uma pagina praticamente nao lida seria aceita.
    #
    # MORA AQUI, ao lado das outras, e NAO no plano que o consome, porque um
    # numero declarado no consumidor nasce sem ferramenta que o meca. Ele e
    # proposto pela varredura de oclusao do 02-02, que ja conta linha recusada
    # por pagina e e a unica que tem a distribuicao.
    #
    # Faixa valida `>= 1` e `<= mercado_grade.linhas_por_pagina`: um piso maior
    # que a pagina desligaria a leitura CALADO.
    mercado_minimo_de_linhas_comparadas: int | None = None

    # O PISO DE BRILHO PROPRIO DA COLUNA QUANTITY, em niveis de V (0-255).
    #
    # POR QUE ELE EXISTE, MEDIDO E NAO SUPOSTO: o texto da coluna Quantity e
    # desenhado mais APAGADO que o das colunas de moeda. Em
    # `pagina-cheia/frame_000010` o tronco do `1` da quantidade tem V = 177,
    # ABAIXO do piso 180 de `identidade.mascara_de_texto`, enquanto o tronco do
    # `1` do `100,00` da coluna Total tem V = 205. A mascara fica so com a
    # serifa e a base, o casamento devolve 0,2988 e o piso de leitura 0,4698
    # reprova. Falha FECHADA, comportamento certo, custo alto: `1` e o caso
    # COMUM do mercado, e sem este piso as gravacoes de tooltip e de alvo
    # sobreposto nao entregam uma linha.
    #
    # ELE E PROPRIO DA COLUNA E NUNCA GLOBAL, e a razao tambem esta medida: as
    # colunas de moeda carregam a palavra de sufixo (`XM Coin`, `Adena`) DENTRO
    # do proprio recorte, e a palavra vive entre V = 120 e V = 173 — o piso 180
    # e o que a mantem FORA da celula. Baixar o piso delas arrasta a palavra
    # para dentro: sondado, `18,90` vira `18,907` ja no piso 170. As duas
    # colunas pedem faixas DISJUNTAS.
    #
    # FAIXA VALIDA `[1, 254]`. Um piso 0 faz a mascara CHEIA e toda celula vira
    # ruido; um piso 255 faz a mascara VAZIA e toda celula cai — os dois
    # desligariam a leitura CALADOS, que e o modo de falha caro.
    #
    # QUEM O MEDE E `tools/medir_brilho_da_quantidade.py`, por varredura sobre
    # as 8 gravacoes do censo com passo 1, rotulo derivado de `Total` e
    # `Unit price`, e recusa quando existe UMA leitura divergente. AUSENTE ou
    # `None` e feature OFF, o default seguro: sem ele a leitura de mercado
    # simplesmente nao acontece, com aviso alto.
    mercado_limiar_de_brilho_da_quantidade: int | None = None

    # A FOLGA DE COLA DO GLIFO -- quantas colunas a barra anti-serrilhada de um
    # glifo COMPARTILHA com o vizinho colado (02-08).
    #
    # Ela e o UNICO numero LIVRE do mecanismo de particao de run largo: as
    # larguras permitidas vem dos moldes, o limite de glifo unico vem das
    # larguras, e so ela nao se deriva de nada. Por isso ela e a unica que mora
    # aqui -- gravar o LIMITE tambem criaria duas verdades sobre uma so
    # geometria, e na recalibracao seguinte a copia envelheceria contra os
    # moldes que ela descreve.
    #
    # FAIXA VALIDA `[0, TETO_DA_FOLGA_DE_COLA]`. O `0` e LEGITIMO e nao e
    # desligar: ele e a particao com as larguras de MOLDE puras, o afrouxamento
    # minimo possivel. Quem desliga e a AUSENCIA -- e a ausencia degrada para
    # MAIS SEGURO, porque sem a chave a producao aplica a GUARDA e a celula com
    # run largo cai FECHADA.
    #
    # QUEM A MEDE E `tools/medir_largura_de_run.py`, por varredura sobre as 8
    # gravacoes do censo com passo 1, contra DOIS rotulos nao circulares (a
    # quantidade derivada de `Total` x `Unit price`, e o intervalo aritmetico
    # nas colunas de moeda), recusando propor quando UMA celula rotulada le fora
    # do rotulo.
    mercado_folga_de_cola_do_glifo: int | None = None

    # OS LAYOUTS ALEM DA NEGOCIACAO, aninhados por nome: `{"adena": {...}}`.
    #
    # OPCIONAL de proposito, e por isso a VERSAO_DO_ESQUEMA SEGUE EM 2, pelo
    # mesmo motivo escrito acima para o `banner_manutencao` e para o bloco de
    # mercado: `carregar` recusa qualquer versao diferente da constante, entao
    # subir para 3 apagaria os 13 moldes de glifo e as 3 ancoras que so a mao do
    # usuario produz — por causa de um campo que ele talvez nem use.
    #
    # A AUSENCIA E O ESTADO NORMAL, e ela NAO AVISA NADA. Isto a separa da
    # `mercado_folga_de_cola_do_glifo`, cuja falta custa 6,08% das linhas e por
    # isso avisa alto: aqui a falta nao degrada coisa nenhuma. Um clone que
    # nunca calibrou a Adena le a negociacao exatamente como lia antes desta
    # fase, e e assim que tem de ser — o ADEN-01 e literalmente "conviver".
    #
    # A NEGOCIACAO NAO MORA AQUI. Ela mora nas chaves de TOPO
    # (`mercado_grade`, `mercado_coluna_do_*`, `mercado_cabecalho_de_coluna`), e
    # `_conferir_os_layouts_de_mercado` recusa `negociacao` como chave aninhada:
    # duas verdades sobre a mesma grade divergem, e a divergencia aqui e a
    # leitura da coluna errada com confianca.
    #
    # A FORMA de cada bloco: `{"cabecalho": {...}, "limiar_do_cabecalho": float,
    # "colunas": {"total": {"dx","largura"}, ...}, "grade": {...opcional}}`.
    # O `grade` sai CURTO ou ausente de proposito: os campos que faltam sao
    # HERDADOS de `mercado_grade` na leitura, porque hoje eles sao identicos e
    # duas copias do mesmo numero envelhecem separadas.
    mercado_layouts: dict | None = None

    # --- Renda (a barra inferior: EXP, adena e o nivel na janela de status) ---
    #
    # OPCIONAL de proposito, e por isso a VERSAO_DO_ESQUEMA SEGUE EM 2, pela
    # razao ja escrita para o `banner_manutencao` (`:234-248`) e repetida pelo
    # mercado: subir a versao invalidaria o `calibration.json` que o usuario
    # mediu a mao e o obrigaria a recalibrar tudo por causa de um campo que ele
    # talvez nem use. Ausente carrega inteiro, com o campo em `None`, e a
    # feature simplesmente fica OFF.
    #
    # REFERENCIAL: o canto da JANELA do jogo, nunca o desktop — como
    # `hp_proprio` e `tiat_*`. O frame da `JanelaSource` e janela-relativo e
    # mede 1720x1392 nas duas instancias medidas (M-A).
    #
    # A CHAVE DE PRIMEIRO NIVEL E O NOME DO PERSONAGEM, e isto e medicao e nao
    # arrumacao (M-F, 2026-09-02, com as duas instancias vivas): a janela de
    # status da Faerlina poe o nivel em `246,736 30x20` e a da Yazalaque em
    # `236,750 30x20`. Sao 14 px de diferenca na vertical e 10 na horizontal,
    # porque o usuario posicionou a UI de cada cliente a mao, e nao ha razao
    # para elas coincidirem nem hoje nem depois de ele arrastar um painel.
    #
    # Um retangulo UNICO le o nivel certo de uma instancia e LIXO da outra — e
    # o lixo aqui e o pior caso possivel: a regiao vizinha mostra `349` na
    # Yazalaque e `112` na Faerlina, numeros plausiveis que passariam em
    # qualquer validacao de numero sem reclamar. Nao e um campo vazio que
    # alguem nota; e um numero.
    #
    # POR QUE UMA CHAVE E NAO SEIS ACHATADAS POR PERSONAGEM: seis por
    # personagem seriam `6N` linhas na enumeracao literal do `salvar` e um
    # commit por personagem novo, que e exatamente o que o LEIT-05 proibe. O
    # pressuposto que caiu foi o de uma calibracao unica (CTX-6), e ele cai
    # citado e nao apagado.
    #
    # A FORMA, por nome de personagem:
    #
    #     {"Faerlina": {
    #         "barra_esquerda": {"regiao": {...}, "piso_de_brilho": 160,
    #                            "largura_da_banda": 3},
    #         "barra_direita":  {"regiao": {...}, "piso_de_brilho": 185,
    #                            "largura_da_banda": 3},
    #         "nivel":          {"regiao": {...}, "piso_de_brilho": 200,
    #                            "largura_da_banda": 4},
    #         "geometria_da_janela": {"largura": 1720, "altura": 1392}}}
    #
    # OS NOMES DAS DUAS SUB-CHAVES MENTEM, E A MENTIRA FICA ESCRITA EM VEZ DE
    # CONSERTADA EM SILENCIO. `barra_esquerda` descreve o **EXP** e
    # `barra_direita` descreve a **ADENA** — nao "as metades da barra". Os
    # nomes vem da era em que os recortes eram duas metades de 520 px; hoje o
    # da adena tem 200 px e um numero so. Renomear UMA sem a outra deixaria
    # duas convencoes dentro da mesma chave, que e pior que um nome velho
    # documentado: quem renomear renomeia AS DUAS, para `exp` e `adena`, num
    # commit proprio.
    #
    # EXISTE UM PISO DE BRILHO POR REGIAO, E NUNCA UM PISO UNICO (M-E). Medido
    # com `vmin` de 100 a 250 nas duas instancias, a banda em que a leitura sai
    # CORRETA e 190-220 para o nivel e 150 para a adena por OCR: elas nao tem
    # INTERSECAO NENHUMA. Um piso unico nao e ruim, e impossivel.
    #
    # E O PISO DA `barra_direita` E O DO CAMINHO DE GLIFO, NAO O DO OCR (M-J).
    # Aquele campo trocou de leitor: o OCR ali aceitava numero errado (`106020`
    # no lugar de `1.696.020`, `91` no lugar de `13.160.684` — M-G) e a
    # segmentacao por glifo acerta numa banda LARGA, 180-190. O valor de
    # exemplo mudou de `150` para o meio dessa banda. NAO HA UM SEGUNDO PISO
    # ALI: um piso sem consumidor de producao e uma segunda verdade esperando
    # que alguem a passe para a funcao errada, e passar o piso de uma regiao em
    # outra faz o campo sumir em silencio.
    #
    # E O RETANGULO DA `barra_direita` JA CAIU DUAS VEZES. O `1200,1368 520x24`
    # era o da era do OCR. O `1500,1360 200x32` que o substituiu foi medido em
    # UMA fixtura e caiu na segunda rodada de campo (M-N/M-O): ele pega o icone
    # da moeda de ouro DENTRO do recorte, e a peneira de forma da leitura por
    # glifo — um run largo em cada ponta e nada largo no meio — recusa isso.
    # Conferido nas QUATRO fixturas de campo e nos pisos 180/185/190, o antigo
    # devolve um run de 17 no MEIO em todas elas. O que vale e `1540,1358
    # 160x34`, e a contagem do meio bate com a verdade de campo caractere por
    # caractere nas quatro. Ele nao e "o retangulo certo": e o retangulo que
    # sobreviveu a quatro cenarios, e quem o trocar de novo troca contra quatro.
    #
    # O CARIMBO DE GEOMETRIA MORA DENTRO DA ENTRADA DO PERSONAGEM, e nao fora:
    # as duas janelas medem 1720x1392 hoje, mas a coincidencia e do usuario e
    # nao do jogo, e um carimbo unico voltaria a misturar as duas instancias
    # pela porta dos fundos.
    #
    # Guardado como dict CRU, sem decodificar, no precedente de
    # `mercado_molde_da_ancora` e `mercado_geometria_da_captura`: decodificar
    # aqui obrigaria `calibracao.py` a importar numpy so para carregar um
    # arquivo de configuracao. Quem decodifica e `renda_leitura`, que ja
    # precisa do numpy.
    renda_por_personagem: dict | None = None

    # Os MOLDES DE GLIFO da fonte da barra inferior.
    #
    # ELA NAO MORA DENTRO DE `renda_por_personagem`, E A RAZAO E MEDIDA: a
    # fonte e do CLIENTE e nao do personagem: a mesma tipografia sai nas DUAS
    # instancias, em todo piso, e em todos os campos da barra — bonus, EXP,
    # L-Coin e adena (M-K, M-L). Moldes por personagem obrigariam o usuario a
    # colher a mesma tipografia duas vezes, por zero beneficio medido.
    #
    # MAS O DIGITO DESTA FONTE NAO TEM UMA LARGURA SO, E ISTO JA ERRO DUAS
    # VEZES NESTA FASE. O M-I mediu "altura 17" sobre um recorte contaminado
    # pelos icones das pontas; o M-K corrigiu para 10 e escreveu "largura 5"; e
    # a segunda rodada de campo (M-O) derrubou o "5" tambem — na segunda
    # fixtura o `4`, o `7` e o `9` saem mais largos, e uma peneira que exigisse
    # UMA largura de digito recusaria `15,134,779` inteiro.
    #
    # Conferido nesta arvore com `segmentar_glifos_no_brilho`, cuja convencao
    # de largura e `fim - inicio` — a MESMA de `larguras_de_molde`, e portanto a
    # que a peneira vai usar: digito 4, 5 ou 6; virgula 1; icones de ponta 14 e
    # 15. O `01-MEDICOES-DE-CAMPO.md` relata os mesmos runs numa convencao
    # INCLUSIVA (5/6/7, 2, 15/16). As duas descrevem a mesma tela e diferem por
    # um pixel; quem escrever uma guarda precisa dizer em qual convencao esta,
    # porque foi exatamente um numero sem convencao — o "17" — que ja custou
    # uma refutacao a esta fase.
    #
    # E ELA NAO SE FUNDE COM `mercado_templates_de_digito`, e a proibicao ja
    # esta escrita neste repositorio com endereco: `calibrar_mercado.py`
    # (commit `e09a860`) — "se a renda precisar de moldes, ela precisa de chave
    # propria, nunca fundir com a do mercado", porque a chave do mercado e de
    # topo e a NEGOCIACAO depende dela.
    #
    # E OS MOLDES DO MERCADO NAO SERVIRIAM DE QUALQUER FORMA: eles sao
    # `altura: 9, largura: 4` e o glifo desta barra e mais alto (M-I no
    # veredicto, M-K no numero). Escrever a distancia CERTA importa: uma guarda
    # de altura escrita contra o 17 contaminado recusaria TODO molde legitimo
    # desta barra, e o modo de falha seria um cortador que nunca corta nada.
    #
    # A FORMA, curta de proposito:
    #
    #     {"moldes": [ {"glifo": "0", "altura": 10, "largura": 5,
    #                   "molde": {"altura": 10, "largura": 5, "bytes": "ff..."}}, ...],
    #      "piso_de_leitura": 0.47,
    #      "margem_de_leitura": 0.037,
    #      "folga_de_cola": null}
    #
    # `moldes` no formato EXATO de `mercado_visao.glifos_para_calibracao` —
    # reusar o formato e o que faz `glifos_de_calibracao` tratar a lista como
    # entrada nao confiavel de graca: ele ja confere altura dominante, rotulo
    # repetido e dimensao declarada. `piso_de_leitura` e `margem_de_leitura`
    # sao os dois limiares que `ler_glifos` exige SEM default, e moram no topo
    # pelo precedente literal de `mercado_limiar_de_leitura_de_glifo` e
    # `mercado_margem_de_leitura_de_glifo`: eles descrevem o CONJUNTO de
    # moldes, e nao o personagem. `folga_de_cola` nasce `null`, que e a guarda
    # FECHADA, e a razao e medida: as larguras da barra sao `5` e `2` limpas,
    # com coluna vazia entre elas (M-J) — nao ha glifo colado a partir. Uma
    # folga inteira aqui autorizaria fatiar um icone de 15 px em tres digitos
    # de 5, que e fabricacao de numero e nao leitura.
    #
    # NADA DERIVAVEL DOS MOLDES ENTRA AQUI: nem a altura de faixa, nem o limite
    # de glifo unico, nem a lista de digitos que faltam. A regra ja esta
    # escrita, com estas palavras, na docstring de
    # `mercado_leitura.limite_de_glifo_unico`: "gravar uma copia criaria DUAS
    # VERDADES sobre uma so geometria, e na recalibracao seguinte a copia
    # envelheceria contra os moldes que ela descreve."
    #
    # E ELA TEM TRES POSICOES LEGITIMAS, NAO DUAS: ausente, completa e
    # INCOMPLETA. Um conjunto com oito dos onze rotulos e um arquivo
    # perfeitamente bem formado — e o estado do usuario entre uma rodada do
    # cortador e a seguinte. A conferencia do arranque confere a FORMA e nunca
    # a COMPLETUDE; quem confere completude e a leitura, por
    # `mercado_leitura.conjunto_descreve_numeros`, e ela recusa com motivo
    # proprio nomeando os que faltam. Derrubar o arranque por um conjunto pela
    # metade trocaria uma recusa nomeada por uma ferramenta que nao abre.
    renda_moldes_da_barra: dict | None = None

    # A PONTE XP <-> PORCENTAGEM: quantos pontos de XP vale UM ponto percentual
    # do nivel (REND-08, CTX-8).
    #
    # A FORMA e por personagem E POR NIVEL:
    #
    #     {"Faerlina": {"67": {"xp_por_ponto": 388700,
    #                          "medido_em": "2026-09-02",
    #                          "n_abates": 114,
    #                          "n_linhas_de_chat": 240,
    #                          "janela_em_segundos": 150,
    #                          "observacao": "<a procedencia por extenso>"}}}
    #
    # POR NIVEL porque o custo do nivel MUDA, e a constante do 66 aplicada ao
    # 67 produz um numero com a mesma cara e errado. POR PERSONAGEM porque o
    # multiplicador de XP e do personagem — a barra da Faerlina exibe 562% ao
    # lado do EXP, e outra instancia com outro multiplicador tem outra
    # constante para o MESMO nivel.
    #
    # A PROCEDENCIA VIAJA JUNTO E NAO E OPCIONAL, e a razao esta na CTX-8: uma
    # constante medida em seis minutos e uma medida em tres horas parecem o
    # mesmo numero e nao valem o mesmo. Sem `n_abates`, `n_linhas_de_chat` e
    # `janela_em_segundos` ao lado, ninguem consegue auditar depois qual das
    # duas esta no arquivo. E a mesma disciplina de `n` e recencia que o
    # `--mercado` aplica a todo numero que vai a tela, aplicada a um numero que
    # vai ao `calibration.json`.
    #
    # A ARMADILHA DESTA FORMA E A CHAVE DE NIVEL, E ELA NAO LEVANTA. JSON nao
    # tem chave inteira: `{67: ...}` gravado sai `{"67": ...}`. Um leitor que
    # comparasse o inteiro 67 com a chave de texto nao daria erro nenhum — ele
    # so devolveria nada, e o painel diria "XP absoluto indisponivel" para
    # sempre sem ninguem entender por que. Quem normaliza e `ponte_do_nivel`,
    # em um lugar so, e ha teste prendendo os dois lados.
    #
    # A `VERSAO_DO_ESQUEMA` FICA EM 2: a chave e opcional, ausente e o estado
    # legitimo de "nao medi a ponte deste nivel", e a Fase 1 ja provou este
    # caminho duas vezes com as duas irmas acima. Ninguem e obrigado a
    # recalibrar — e o arquivo do usuario carrega treze moldes de glifo e as
    # assinaturas de nome, que so a mao dele produz.
    #
    # Guardada como dict CRU, sem reconstrucao, no molde exato das irmas.
    renda_ponte_de_xp: dict | None = None

    versao: int = VERSAO_DO_ESQUEMA

    def regiao_do_nome(self, indice: int) -> Regiao:
        """Onde fica o texto do nome da linha `indice`, dentro da party window."""
        lay = self.layout
        deslocamento = indice * lay.passo
        return Regiao(
            esquerda=lay.icone_x + lay.nome_dx,
            topo=lay.icone_y + deslocamento + lay.nome_dy,
            largura=lay.nome_largura,
            altura=lay.nome_altura,
        )

    @property
    def nomes_com_assinatura(self) -> set[str]:
        """Quem tem impressao digital visual gravada.

        Assinatura ANONIMA nao entra: o acervo em disco carrega entradas sem
        nome, e a string vazia dentro deste conjunto seria lixo esperando virar
        um bug de nome errado na proxima comparacao que alguem escrever contra
        ele.
        """
        return {a.nome for a in self.assinaturas if a.nome}

    def nome_da_linha(self, indice: int) -> str:
        """Rotulo de uma linha que NAO foi reconhecida.

        Um nome que tem assinatura gravada nunca pode ser usado aqui. A
        assinatura e a autoridade sobre onde aquela pessoa esta: se ela nao
        casou nesta linha, esta linha nao e dela.

        Sem esta regra o rotulo por posicao mente exatamente como o alerta
        mentia. Visto ao vivo: Korzis reconhecido na linha 0, linha 1 sem
        reconhecimento e com HP 0% — e `nomes[1]` era "Korzis". O scanner
        estava a um debounce de anunciar "Korzis morreu" com o Korzis vivo a
        57% na linha de cima.

        Sem assinatura NENHUMA, o nome por posicao volta a valer: e o modo
        antigo, e ali ele e o melhor palpite disponivel.
        """
        if 0 <= indice < len(self.nomes):
            nome = self.nomes[indice]
            if nome not in self.nomes_com_assinatura:
                return nome
        return f"Membro {indice + 1}"

    def regiao_do_banner(self, na_janela: bool) -> Regiao | None:
        """Onde procurar o banner de manutencao. None = o recurso nao liga.

        Tres respostas, nesta ordem:

        1. A regiao CALIBRADA, quando o usuario configurou uma. Ela vence
           sempre — foi ele que olhou o PNG do `--testar-manutencao` e viu onde
           o banner cai de verdade.
        2. Uma faixa derivada da party window, no caminho `--janela`. O banner
           aparece POR CIMA da party window e e mais largo que as barras.
        3. None, no caminho `mss` sem configuracao (D-07). Ali nao existe
           janela de referencia, entao qualquer padrao seria um palpite sobre
           coordenadas de desktop — e inventar deteccao onde nao ha pixels e
           pior do que nao ligar o recurso.

        A faixa derivada e GENEROSA de proposito, e nao justa. Texto vizinho
        que caia dentro dela e so ruido: `eh_banner_de_manutencao` exige a raiz
        `mainten`, que nada mais na tela produz. Uma faixa apertada, ao
        contrario, erra por pouco e nao le NADA — e o modo de falha caro e
        esse.
        """
        if self.banner_manutencao is not None:
            return self.banner_manutencao
        if not na_janela or self.party_window_na_janela is None:
            return None

        party = self.party_window_na_janela
        return Regiao(
            esquerda=max(0, party.esquerda - MARGEM_ESQUERDA_DO_BANNER),
            topo=max(0, party.topo - MARGEM_ACIMA_DO_BANNER),
            largura=party.largura + LARGURA_EXTRA_DO_BANNER,
            altura=ALTURA_DA_FAIXA_DO_BANNER,
        )

    def salvar(self, caminho: Path) -> None:
        dados = {
            "versao": self.versao,
            "geometria_da_tela": self.geometria_da_tela,
            "party_window": self.party_window.como_dict(),
            "ancora": self.ancora.como_dict(),
            "layout": asdict(self.layout),
            "limiares_hp": asdict(self.limiares_hp),
            "limiares_mp": asdict(self.limiares_mp),
            "hp_proprio": self.hp_proprio.como_dict() if self.hp_proprio else None,
            "nome_proprio": self.nome_proprio,
            "nomes": self.nomes,
            "assinaturas": [a.como_dict() for a in self.assinaturas],
            "janela": self.janela,
            "party_window_na_janela": (
                self.party_window_na_janela.como_dict()
                if self.party_window_na_janela
                else None
            ),
            "banner_manutencao": (
                self.banner_manutencao.como_dict() if self.banner_manutencao else None
            ),
            "tiat_chat": self.tiat_chat.como_dict() if self.tiat_chat else None,
            "tiat_alvo": self.tiat_alvo.como_dict() if self.tiat_alvo else None,
            # Serializacao condicional, trilho do `banner_manutencao`: um campo
            # nao preenchido vira `null` e o `.get` do `carregar` o devolve como
            # None, sem migracao.
            "mercado_ancora": (
                self.mercado_ancora.como_dict() if self.mercado_ancora else None
            ),
            "mercado_molde_da_ancora": self.mercado_molde_da_ancora,
            "mercado_limiar_da_ancora": self.mercado_limiar_da_ancora,
            "mercado_geometria_da_captura": self.mercado_geometria_da_captura,
            "mercado_ancoras": self.mercado_ancoras,
            "mercado_grade": self.mercado_grade,
            "mercado_templates_de_nome": self.mercado_templates_de_nome,
            "mercado_templates_de_digito": self.mercado_templates_de_digito,
            "mercado_templates_de_digito_cromatico": (
                self.mercado_templates_de_digito_cromatico
            ),
            "mercado_limiar_de_template": self.mercado_limiar_de_template,
            "mercado_limiar_de_glifo": self.mercado_limiar_de_glifo,
            # As quatorze da leitura de pagina, no MESMO trilho: um campo nao
            # preenchido vira `null` e o `.get` do `carregar` o devolve como
            # None, sem migracao.
            "mercado_coluna_do_nome": self.mercado_coluna_do_nome,
            "mercado_coluna_da_quantidade": self.mercado_coluna_da_quantidade,
            "mercado_coluna_do_total": self.mercado_coluna_do_total,
            "mercado_coluna_do_unitario": self.mercado_coluna_do_unitario,
            "mercado_cabecalho_de_coluna": self.mercado_cabecalho_de_coluna,
            "mercado_limiar_do_cabecalho": self.mercado_limiar_do_cabecalho,
            "mercado_sonda_do_fundo": self.mercado_sonda_do_fundo,
            "mercado_limiar_de_dispersao_do_fundo": (
                self.mercado_limiar_de_dispersao_do_fundo
            ),
            "mercado_limiar_de_leitura_de_glifo": (
                self.mercado_limiar_de_leitura_de_glifo
            ),
            "mercado_margem_de_leitura_de_glifo": (
                self.mercado_margem_de_leitura_de_glifo
            ),
            "mercado_corte_de_similaridade": self.mercado_corte_de_similaridade,
            "mercado_piso_de_similaridade": self.mercado_piso_de_similaridade,
            "mercado_tolerancia_do_cruzamento": (
                self.mercado_tolerancia_do_cruzamento
            ),
            "mercado_minimo_de_linhas_comparadas": (
                self.mercado_minimo_de_linhas_comparadas
            ),
            "mercado_limiar_de_brilho_da_quantidade": (
                self.mercado_limiar_de_brilho_da_quantidade
            ),
            "mercado_folga_de_cola_do_glifo": (
                self.mercado_folga_de_cola_do_glifo
            ),
            "mercado_layouts": self.mercado_layouts,
            # As TRES da renda, no MESMO trilho condicional das irmas: um campo
            # nao preenchido vira `null` e o `.get` do `carregar` o devolve como
            # None, sem migracao. Guardadas como dict CRU, sem reconstrucao
            # campo a campo — e e isso que faz uma sub-chave que este codigo
            # ainda nao conhece SOBREVIVER a ida e volta, em vez de sumir
            # calada no dia em que o calibrador gravar uma a mais.
            "renda_por_personagem": self.renda_por_personagem,
            "renda_moldes_da_barra": self.renda_moldes_da_barra,
            "renda_ponte_de_xp": self.renda_ponte_de_xp,
        }
        # ESCRITA ATOMICA, NO LUGAR ONDE TODOS OS ESCRITORES HERDAM.
        #
        # `caminho.write_text` direto sobre o arquivo final deixa um JSON
        # TRUNCADO se a escrita for interrompida no meio -- Ctrl-C impaciente,
        # disco cheio, antivirus segurando o handle. A proxima carga levanta
        # "esta corrompido: recalibre", e nao so para o mercado: para o SCANNER
        # DE PARTY INTEIRO. O que se perde e a party window, os limiares HSV
        # afinados a mao contra o Gamma da tela do usuario, o `hp_proprio` e as
        # assinaturas de nome -- tudo desconhecivel a priori e caro de refazer.
        #
        # O risco ja existia; o que mudou foi o PERFIL dele. O calibration.json
        # era escrito uma vez, na calibracao inicial. Agora ha um segundo
        # escritor (`calibrar_mercado`) que o usuario roda repetidamente, e que
        # pode recusar no meio do caminho.
        #
        # `os.replace` e atomico no mesmo volume: ou fica o arquivo antigo
        # inteiro, ou o novo inteiro. Nunca meio. O temporario vive ao lado do
        # destino, e nao no %TEMP%, porque `os.replace` entre volumes
        # diferentes nao e atomico (e no Windows nem funciona).
        temporario = caminho.with_name(caminho.name + ".tmp")
        temporario.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        os.replace(temporario, caminho)

    @classmethod
    def carregar(cls, caminho: Path) -> "Calibracao":
        if not caminho.exists():
            raise CalibracaoInvalida(
                f"Nao encontrei {caminho}.\n"
                f"Rode a calibracao:  python -m l2scanner.calibrar"
            )

        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except json.JSONDecodeError as erro:
            raise CalibracaoInvalida(f"{caminho} esta corrompido: {erro}") from erro

        versao = dados.get("versao")
        if versao != VERSAO_DO_ESQUEMA:
            raise CalibracaoInvalida(
                f"{caminho} foi gravado no formato v{versao}, "
                f"mas este scanner espera v{VERSAO_DO_ESQUEMA}. Recalibre."
            )

        _conferir_as_chaves_de_mercado(dados)
        _conferir_as_chaves_da_renda(dados)

        return cls(
            party_window=Regiao.de_dict(dados["party_window"]),
            ancora=Regiao.de_dict(dados["ancora"]),
            layout=LayoutDaParty(**dados["layout"]),
            limiares_hp=LimiaresDeCor(**dados["limiares_hp"]),
            limiares_mp=LimiaresDeCor(**dados["limiares_mp"]),
            geometria_da_tela=dados["geometria_da_tela"],
            hp_proprio=(
                Regiao.de_dict(dados["hp_proprio"]) if dados.get("hp_proprio") else None
            ),
            nome_proprio=dados.get("nome_proprio"),
            nomes=list(dados.get("nomes", [])),
            assinaturas=[
                Assinatura.de_dict(a) for a in dados.get("assinaturas", [])
            ],
            janela=dados.get("janela"),
            party_window_na_janela=(
                Regiao.de_dict(dados["party_window_na_janela"])
                if dados.get("party_window_na_janela")
                else None
            ),
            # `.get`, exatamente como `hp_proprio`: e o que faz um
            # calibration.json v2 gravado antes desta funcionalidade carregar
            # sem uma linha de migracao.
            banner_manutencao=(
                Regiao.de_dict(dados["banner_manutencao"])
                if dados.get("banner_manutencao")
                else None
            ),
            tiat_chat=(
                Regiao.de_dict(dados["tiat_chat"])
                if dados.get("tiat_chat")
                else None
            ),
            tiat_alvo=(
                Regiao.de_dict(dados["tiat_alvo"])
                if dados.get("tiat_alvo")
                else None
            ),
            # As quatro de mercado seguem o MESMO `.get`: e o que faz um
            # calibration.json v2 gravado antes desta funcionalidade carregar
            # sem uma linha de migracao.
            mercado_ancora=(
                Regiao.de_dict(dados["mercado_ancora"])
                if dados.get("mercado_ancora")
                else None
            ),
            mercado_molde_da_ancora=dados.get("mercado_molde_da_ancora"),
            mercado_limiar_da_ancora=dados.get("mercado_limiar_da_ancora"),
            mercado_geometria_da_captura=dados.get("mercado_geometria_da_captura"),
            mercado_ancoras=dados.get("mercado_ancoras"),
            mercado_grade=dados.get("mercado_grade"),
            mercado_templates_de_nome=dados.get("mercado_templates_de_nome"),
            mercado_templates_de_digito=dados.get("mercado_templates_de_digito"),
            mercado_templates_de_digito_cromatico=dados.get(
                "mercado_templates_de_digito_cromatico"
            ),
            mercado_limiar_de_template=dados.get("mercado_limiar_de_template"),
            mercado_limiar_de_glifo=dados.get("mercado_limiar_de_glifo"),
            # E as quatorze da leitura de pagina, pelo MESMO `.get` e pelo mesmo
            # motivo — e este e o ponto em que a regra deixa de ser estilo e
            # passa a ser dinheiro: uma unica `dados["..."]` aqui faria o
            # calibration.json do usuario, que nao tem nenhuma delas, levantar
            # KeyError no arranque e levar junto os 13 moldes de glifo e as 3
            # ancoras que so a mao dele produz.
            mercado_coluna_do_nome=dados.get("mercado_coluna_do_nome"),
            mercado_coluna_da_quantidade=dados.get("mercado_coluna_da_quantidade"),
            mercado_coluna_do_total=dados.get("mercado_coluna_do_total"),
            mercado_coluna_do_unitario=dados.get("mercado_coluna_do_unitario"),
            mercado_cabecalho_de_coluna=dados.get("mercado_cabecalho_de_coluna"),
            mercado_limiar_do_cabecalho=dados.get("mercado_limiar_do_cabecalho"),
            mercado_sonda_do_fundo=dados.get("mercado_sonda_do_fundo"),
            mercado_limiar_de_dispersao_do_fundo=dados.get(
                "mercado_limiar_de_dispersao_do_fundo"
            ),
            mercado_limiar_de_leitura_de_glifo=dados.get(
                "mercado_limiar_de_leitura_de_glifo"
            ),
            mercado_margem_de_leitura_de_glifo=dados.get(
                "mercado_margem_de_leitura_de_glifo"
            ),
            mercado_corte_de_similaridade=dados.get("mercado_corte_de_similaridade"),
            mercado_piso_de_similaridade=dados.get("mercado_piso_de_similaridade"),
            mercado_tolerancia_do_cruzamento=dados.get(
                "mercado_tolerancia_do_cruzamento"
            ),
            mercado_minimo_de_linhas_comparadas=dados.get(
                "mercado_minimo_de_linhas_comparadas"
            ),
            # `.get` e nao indexacao: um `calibration.json` de ANTES do 02-07
            # carrega inteiro, com o campo em `None`, e `VERSAO_DO_ESQUEMA`
            # segue em 2. O arquivo do usuario tem 13 moldes e 3 ancoras que so
            # a mao dele produz, e um bump custaria uma tarde dele.
            mercado_limiar_de_brilho_da_quantidade=dados.get(
                "mercado_limiar_de_brilho_da_quantidade"
            ),
            # `.get` e nao indexacao, pela mesma razao da irma acima: um
            # `calibration.json` de ANTES do 02-08 carrega inteiro, com o campo
            # em `None` -- que e a GUARDA, o comportamento SEGURO -- e
            # `VERSAO_DO_ESQUEMA` segue em 2.
            mercado_folga_de_cola_do_glifo=dados.get(
                "mercado_folga_de_cola_do_glifo"
            ),
            # `.get` e nao indexacao, pela MESMA razao das duas irmas acima. Aqui
            # ela e ainda mais barata de defender: TODO `calibration.json` que
            # existe hoje no mundo esta sem esta chave, entao uma indexacao
            # mataria o arranque de cada instalacao ate a proxima recalibracao.
            mercado_layouts=dados.get("mercado_layouts"),
            # `.get` e nao indexacao, pela MESMA razao das irmas de mercado:
            # TODO `calibration.json` que existe hoje no mundo esta sem estas
            # tres chaves, entao uma indexacao mataria o arranque de cada
            # instalacao ate a proxima recalibracao — e levaria junto os moldes
            # de glifo e as ancoras que so a mao do usuario produz.
            renda_por_personagem=dados.get("renda_por_personagem"),
            renda_moldes_da_barra=dados.get("renda_moldes_da_barra"),
            renda_ponte_de_xp=dados.get("renda_ponte_de_xp"),
            versao=versao,
        )

    def renda_do_personagem(self, nome: str | None) -> dict | None:
        """A calibracao de renda DESTE personagem, ou nada. NUNCA a de outro.

        A PROIBICAO DE QUEDA MORA EM UM LUGAR SO, e e por isso que isto e uma
        funcao e nao um `.get` espalhado por tres leitores. Medido (M-F): a
        janela de status da Faerlina poe o nivel em `246,736` e a da Yazalaque
        em `236,750`. Ler a Faerlina com o retangulo da Yazalaque nao devolve
        um campo vazio que alguem nota — devolve `349` ou `112`, que sao os
        numeros desenhados ao lado do nivel e passam por qualquer validacao de
        numero sem reclamar.

        Sugerir o retangulo do vizinho como PONTO DE PARTIDA no calibrador e
        legitimo, porque o usuario confirma com o olho. Cair nele em silencio
        na hora de LER e produzir um numero plausivel e errado, que e o unico
        defeito que esta fase trata como inaceitavel.

        `None` quando a feature nao foi calibrada, quando o nome nao veio, e
        quando o nome veio e nao esta no arquivo. Os tres sao "nao sei ler esta
        tela", e quem chama transforma isso em recusa NOMEADA.
        """
        if not self.renda_por_personagem or not nome:
            return None
        entrada = self.renda_por_personagem.get(nome)
        return entrada if isinstance(entrada, dict) else None

    def ponte_do_nivel(self, nome: str | None, nivel: int | None) -> dict | None:
        """A ponte XP<->porcentagem DESTE personagem NESTE nivel, ou nada.

        A PROIBICAO DE QUEDA MORA EM UM LUGAR SO, como na irma acima, e aqui
        ela e o defeito que a CTX-8 proibe com todas as letras: **nunca a
        constante do nivel anterior**. O custo do nivel muda justamente entre
        um nivel e o seguinte, e a constante do 66 aplicada ao 67 nao produz um
        campo vazio que alguem nota — produz um XP absoluto com a mesma cara de
        certo e alguns por cento errado, que ninguem consegue distinguir de um
        certo depois de gravado.

        A disciplina e a do cambio XM->BRL do `dashboard`: sem taxa informada,
        mostra a moeda de origem e DIZ que a outra esta indisponivel. Aqui:
        sem constante para o nivel atual, o painel mostra pontos percentuais e
        diz por que o absoluto nao esta la. Quem transforma este `None` em
        recusa NOMEADA e `renda_ponte`.

        A BUSCA MORA EM `renda_ponte.constante_do_nivel` E ESTE METODO DELEGA,
        em vez de repeti-la. A chave do nivel e TEXTO no JSON — `{67: ...}`
        gravado volta `{"67": ...}` — e uma segunda normalizacao escrita aqui
        seria uma segunda verdade sobre a mesma forma: na primeira mudanca de
        formato, uma das duas envelheceria calada. O import e barato: aquele
        modulo e aritmetica pura e nao arrasta nada.

        `None` quando a ponte nao foi medida, quando o nome nao veio, quando o
        nivel nao veio, quando o personagem nao esta no arquivo e quando o
        NIVEL daquele personagem nao esta no arquivo. Os cinco sao "nao sei
        converter esta tela"; quem precisa do motivo NOMEADO chama
        `renda_ponte` direto, que devolve os dois.
        """
        from .renda_ponte import constante_do_nivel

        entrada, _motivo = constante_do_nivel(self.renda_ponte_de_xp, nome, nivel)
        return entrada

    def conferir_geometria_do_mercado(self, largura: int, altura: int) -> None:
        """Recusa a leitura de mercado se a JANELA mudou de tamanho.

        O molde da ancora foi recortado sob uma janela de dimensoes conhecidas.
        Com a janela em outro tamanho, a mesma arte esta desenhada em outra
        escala: o casamento cai, o painel some, e nao ha uma linha de erro
        explicando por que. Falhar alto aqui, no arranque, com o usuario olhando
        o console, e o unico momento em que a mensagem "recalibre o mercado"
        chega a alguem.

        Sem carimbo gravado nao ha o que conferir: uma instalacao que nunca
        calibrou o mercado sobe igual, com a feature simplesmente OFF.
        """
        if not self.mercado_geometria_da_captura:
            return
        gravada = self.mercado_geometria_da_captura
        esperada = (gravada.get("largura"), gravada.get("altura"))
        if esperada != (largura, altura):
            raise CalibracaoInvalida(
                "A janela do jogo mudou de tamanho desde a calibracao do "
                "mercado.\n"
                f"  calibrado sob: {esperada[0]}x{esperada[1]}\n"
                f"  agora:         {largura}x{altura}\n"
                "O molde da ancora foi recortado noutra escala e nao vai casar. "
                "Recalibre o mercado: calibrar-mercado.bat"
            )

    def conferir_geometria(self, atual: str) -> None:
        """Recusa se a tela mudou desde a calibracao (CAPT-07).

        Falhar alto aqui e muito melhor do que medir a regiao errada calado.
        """
        if self.geometria_da_tela != atual:
            raise CalibracaoInvalida(
                "A configuracao de tela mudou desde a calibracao.\n"
                f"  calibrado sob: {self.geometria_da_tela}\n"
                f"  agora:         {atual}\n"
                "As coordenadas gravadas nao valem mais. Recalibre."
            )


def _conferir_as_chaves_de_mercado(dados: dict) -> None:
    """As chaves de mercado sao ENTRADA NAO CONFIAVEL. Confere tipo e faixa.

    Mora AQUI, ao lado do portao de versao, e nao no consumidor, porque e no
    arranque que a mensagem ainda pode dizer "recalibre" com o usuario olhando
    para o console. O consumidor roda as duas da manha, no meio do farm.

    As tres chaves saiam de `dados.get(...)` direto para dentro da `Calibracao`
    sem uma checagem. `molde_de_hex` ja tratava o dict como entrada nao
    confiavel e a versao ja tinha portao; o LIMIAR nao tinha nada, e e o mais
    perigoso dos tres:

    - `mercado_limiar_da_ancora: 0` ou `-1` faz `mercado_aberto` devolver True
      para TODO recorte. O detector deixa de detectar e passa a AFIRMAR — o
      fail-open exato que o charter do `mercado_visao` existe para impedir.
    - `mercado_limiar_da_ancora: "0.73"` (numero entre aspas, o deslize de
      edicao mais comum) viraria `TypeError: '>=' not supported between
      'float' and 'str'` dentro de `mercado_aberto`, no meio do farm.
    - `mercado_molde_da_ancora: [1, 2, 3]` viraria `TypeError: list indices
      must be integers` dentro de `molde_de_hex`.

    `None` sempre passa: e o estado legitimo de "nao calibrei o mercado", e uma
    instalacao sem calibracao de mercado precisa continuar subindo igual.
    """
    limiar = dados.get("mercado_limiar_da_ancora")
    if limiar is not None:
        # `bool` e subclasse de `int`: `True` passaria como numero e viraria
        # limiar 1.0 calado.
        if isinstance(limiar, bool) or not isinstance(limiar, (int, float)):
            raise CalibracaoInvalida(
                f"mercado_limiar_da_ancora precisa ser um numero, veio "
                f"{type(limiar).__name__} ({limiar!r}). Recalibre o mercado."
            )
        if not 0.0 < limiar <= 1.0:
            raise CalibracaoInvalida(
                f"mercado_limiar_da_ancora={limiar} esta fora de (0, 1]. Um "
                f"limiar <= 0 faz TODO recorte virar 'mercado aberto'. O "
                f"padrao medido e 0.73. Recalibre o mercado."
            )

    molde = dados.get("mercado_molde_da_ancora")
    if molde is not None and not isinstance(molde, dict):
        raise CalibracaoInvalida(
            f"mercado_molde_da_ancora precisa ser um objeto com altura, "
            f"largura e bytes, veio {type(molde).__name__}. Recalibre o "
            f"mercado."
        )

    geometria = dados.get("mercado_geometria_da_captura")
    if geometria is not None and not isinstance(geometria, dict):
        raise CalibracaoInvalida(
            f"mercado_geometria_da_captura precisa ser um objeto, veio "
            f"{type(geometria).__name__}. Recalibre o mercado."
        )

    limiar_template = dados.get("mercado_limiar_de_template")
    if limiar_template is not None:
        if isinstance(limiar_template, bool) or not isinstance(
            limiar_template, (int, float)
        ):
            raise CalibracaoInvalida(
                f"mercado_limiar_de_template precisa ser um numero, veio "
                f"{type(limiar_template).__name__} ({limiar_template!r}). "
                f"Recalibre o mercado."
            )
        if not 0.0 < limiar_template <= 1.0:
            raise CalibracaoInvalida(
                f"mercado_limiar_de_template={limiar_template} esta fora de "
                f"(0, 1]. Um limiar <= 0 faz TODO recorte casar com TODO item "
                f"da watchlist, e um preco lido do item errado corrompe a serie "
                f"inteira. Recalibre o mercado."
            )

    # Espelho do de cima, e chave SEPARADA de proposito: sao dois conjuntos
    # fechados diferentes (a watchlist e do usuario e muda a cada config.toml; o
    # conjunto de glifos e fixo pela fonte do jogo), com matrizes e piores pares
    # diferentes. Um numero servindo aos dois seria derivado de uma medicao e
    # aplicado a outra.
    limiar_glifo = dados.get("mercado_limiar_de_glifo")
    if limiar_glifo is not None:
        if isinstance(limiar_glifo, bool) or not isinstance(
            limiar_glifo, (int, float)
        ):
            raise CalibracaoInvalida(
                f"mercado_limiar_de_glifo precisa ser um numero, veio "
                f"{type(limiar_glifo).__name__} ({limiar_glifo!r}). "
                f"Recalibre os digitos do mercado."
            )
        if not 0.0 < limiar_glifo <= 1.0:
            raise CalibracaoInvalida(
                f"mercado_limiar_de_glifo={limiar_glifo} esta fora de (0, 1]. "
                f"Um limiar frouxo faz TODO recorte casar com TODO glifo, e um "
                f"digito lido errado corrompe o preco CALADO — um `0` lido como "
                f"`8` nao acrescenta ruido a serie, troca o numero. "
                f"Recalibre os digitos do mercado."
            )

    # As tres listas e a grade: so a FORMA e conferida aqui. O conteudo de cada
    # molde e conferido por `mercado_visao.molde_de_hex` / `ancoras_de_calibracao`
    # na hora de decodificar — e la que a dimensao declarada encontra os bytes.
    for chave in (
        "mercado_ancoras",
        "mercado_templates_de_nome",
        "mercado_templates_de_digito",
        "mercado_templates_de_digito_cromatico",
    ):
        valor = dados.get(chave)
        if valor is not None and not isinstance(valor, list):
            raise CalibracaoInvalida(
                f"{chave} precisa ser uma lista, veio "
                f"{type(valor).__name__}. Recalibre o mercado."
            )

    grade = dados.get("mercado_grade")
    if grade is not None and not isinstance(grade, dict):
        raise CalibracaoInvalida(
            f"mercado_grade precisa ser um objeto, veio "
            f"{type(grade).__name__}. Recalibre o mercado."
        )

    ancora = dados.get("mercado_ancora")
    if isinstance(ancora, dict):
        # `Regiao.de_dict` aceita largura/altura <= 0, e faz bem em nao
        # reclamar de `esquerda`/`topo` negativos (monitor a esquerda do
        # principal). Mas uma ancora de area zero ou negativa nao recorta nada.
        #
        # ONDE A FORMA DO MOLDE E CONFERIDA, PARA O COMENTARIO NAO MENTIR: nao
        # e aqui, e nao e contra este retangulo. `mercado_ancora` e a REGIAO na
        # janela; a conferencia de forma acontece em
        # `mercado_visao.ancoras_de_calibracao`, que passa `forma_esperada` a
        # `molde_de_hex` a partir dos campos `altura`/`largura` gravados ao
        # lado de cada molde em `mercado_ancoras`. Este comentario ja afirmou o
        # contrario enquanto NENHUM chamador de producao passava o argumento
        # (WR-01).
        try:
            largura, altura = int(ancora["largura"]), int(ancora["altura"])
        except (KeyError, TypeError, ValueError) as erro:
            raise CalibracaoInvalida(
                f"mercado_ancora nao tem largura/altura inteiras utilizaveis "
                f"({erro}). Recalibre o mercado."
            ) from erro
        if largura <= 0 or altura <= 0:
            raise CalibracaoInvalida(
                f"mercado_ancora tem dimensao nao-positiva "
                f"({largura}x{altura}). Recalibre o mercado."
            )

    _conferir_as_chaves_da_leitura_de_pagina(dados)


# O CONSERTO da renda, escrito uma vez e citado por toda recusa dela, no mesmo
# trilho do `CONSERTO_DO_MERCADO` logo abaixo: repetir a mao em dez lugares
# garantiria que no dia em que ele mudasse, nove ficariam mentindo.
CONSERTO_DA_RENDA = 'Recalibre a renda: calibrar-renda.bat --janela "TITULO"'

# As TRES regioes de uma entrada de personagem. Os dois primeiros nomes MENTEM
# — `barra_esquerda` e o EXP e `barra_direita` e a ADENA —, e a mentira esta
# documentada no bloco de comentario do campo `renda_por_personagem`.
REGIOES_DA_RENDA = ("barra_esquerda", "barra_direita", "nivel")

# A faixa fechada dos dois lados de todo piso de brilho da renda, em niveis de
# V (0-255). E a MESMA de `_conferir_o_piso_de_brilho_da_quantidade`, e pelas
# MESMAS duas razoes medidas la: piso `0` faz a mascara CHEIA — todo pixel vira
# tinta, o texto se dissolve no fundo e o OCR le ruido com confianca —, e piso
# `255` faz a mascara VAZIA, e o campo some sem uma linha de log.
PISO_DE_BRILHO_MINIMO_DA_RENDA = 1
PISO_DE_BRILHO_MAXIMO_DA_RENDA = 254


def _inteiro_da_renda(valor, onde: str) -> int:
    """Um inteiro de verdade. `bool` recusado por ser subclasse de `int`."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise CalibracaoInvalida(
            f"{onde} precisa ser um inteiro, veio "
            f"{type(valor).__name__} ({valor!r}). {CONSERTO_DA_RENDA}"
        )
    return valor


def _conferir_um_piso_de_brilho_da_renda(valor, onde: str) -> None:
    """Um nivel de V em `[1, 254]`, inteiro, com `bool` recusado explicitamente.

    `bool` E RECUSADO POR NOME porque e subclasse de `int`: `True` passaria por
    `isinstance(valor, int)` e viraria piso 1 calado, que e o caso `0`
    disfarcado — a mascara cheia, com todo pixel virando tinta.

    OS DOIS EXTREMOS DESLIGAM A LEITURA CALADOS, e e por isso que a faixa e
    fechada dos DOIS lados. No piso de baixo a mascara fica cheia e o texto se
    dissolve no fundo; no piso de cima a mascara fica vazia e o campo some sem
    uma linha de log. Os dois produzem "nao li" sem dizer por que, que e
    exatamente o modo de falha que esta fase existe para nao ter.
    """
    piso = _inteiro_da_renda(valor, onde)
    if not PISO_DE_BRILHO_MINIMO_DA_RENDA <= piso <= PISO_DE_BRILHO_MAXIMO_DA_RENDA:
        raise CalibracaoInvalida(
            f"{onde}={piso} esta fora de [{PISO_DE_BRILHO_MINIMO_DA_RENDA}, "
            f"{PISO_DE_BRILHO_MAXIMO_DA_RENDA}]. Um piso de baixo faz a mascara "
            f"CHEIA e o texto se dissolve no fundo; um piso de cima faz a "
            f"mascara VAZIA e o campo some sem uma linha de log. Os dois "
            f"desligariam a leitura CALADOS. {CONSERTO_DA_RENDA}"
        )


def _conferir_uma_regiao_da_renda(bruto, onde: str) -> None:
    """`{"esquerda": int, "topo": int, "largura": >0, "altura": >0}`.

    `esquerda` e `topo` podem ser NEGATIVOS e isso e legitimo — a regra e a de
    `Regiao`, e recusar negativo aqui mataria um HUD posicionado a esquerda da
    origem. `largura` e `altura` NAO podem: uma dimensao zero nao recorta nada,
    e a leitura ficaria vazia sem uma linha de erro (precedente de
    `_conferir_uma_coluna`).
    """
    if not isinstance(bruto, dict):
        raise CalibracaoInvalida(
            f"{onde} precisa ser um objeto com esquerda, topo, largura e "
            f"altura, veio {type(bruto).__name__}. {CONSERTO_DA_RENDA}"
        )
    for campo in ("esquerda", "topo", "largura", "altura"):
        if campo not in bruto:
            raise CalibracaoInvalida(
                f"{onde} esta sem `{campo}`. Um retangulo pela metade nao "
                f"levanta erro: ele recorta o lugar errado e devolve um numero "
                f"plausivel. {CONSERTO_DA_RENDA}"
            )
        _inteiro_da_renda(bruto[campo], f"{onde}.{campo}")
    for campo in ("largura", "altura"):
        if bruto[campo] <= 0:
            raise CalibracaoInvalida(
                f"{onde}.{campo}={bruto[campo]} nao e positivo. Um retangulo "
                f"de dimensao zero nao recorta nada, e a leitura ficaria vazia "
                f"sem uma linha de erro. {CONSERTO_DA_RENDA}"
            )


def _conferir_a_renda_por_personagem(por_personagem) -> None:
    """A calibracao de renda de cada personagem, conferida no ARRANQUE.

    A REGRA DE AUSENCIA TEM DOIS NIVEIS, E A DIFERENCA E O PONTO DESTA FUNCAO.
    O campo inteiro ausente ou `None` PASSA: a feature fica desligada e ninguem
    e obrigado a recalibrar. Uma ENTRADA DE PERSONAGEM presente porem
    incompleta ou fora de faixa e RECUSADA ALTO, aqui, porque o arquivo e
    editavel a mao e um retangulo malformado nao produz erro — produz um
    recorte plausivel no lugar errado, que e o modo de falha inteiro do M-F.
    Presente tem de estar certo; ausente e legitimo.

    ELA CONFERE SO O QUE CONHECE. Uma sub-chave que este codigo ainda nao
    conhece atravessa sem ser tocada, e sobrevive a ida e volta pelo `salvar`
    porque o dict e reemitido cru — e essa e a diferenca entre um campo novo
    do calibrador nascer PRESERVADO e nascer apagado.
    """
    if por_personagem is None:
        return
    if not isinstance(por_personagem, dict):
        raise CalibracaoInvalida(
            f"renda_por_personagem precisa ser um objeto com uma entrada por "
            f"nome de personagem, veio {type(por_personagem).__name__}. "
            f"{CONSERTO_DA_RENDA}"
        )

    for nome, entrada in por_personagem.items():
        if not isinstance(nome, str) or not nome:
            raise CalibracaoInvalida(
                f"renda_por_personagem tem uma chave que nao e nome de "
                f"personagem ({nome!r}). A chave E a identidade da instancia: "
                f"sem ela a leitura nao sabe de quem e a tela. "
                f"{CONSERTO_DA_RENDA}"
            )
        onde = f"renda_por_personagem[{nome!r}]"
        if not isinstance(entrada, dict):
            raise CalibracaoInvalida(
                f"{onde} precisa ser um objeto com as tres regioes, veio "
                f"{type(entrada).__name__}. {CONSERTO_DA_RENDA}"
            )
        for regiao in REGIOES_DA_RENDA:
            if regiao not in entrada:
                raise CalibracaoInvalida(
                    f"{onde} esta sem `{regiao}`. Uma entrada pela metade e "
                    f"pior que uma entrada ausente: a ausente desliga a "
                    f"feature, a pela metade faz a leitura procurar um campo "
                    f"que nao tem endereco. {CONSERTO_DA_RENDA}"
                )
            bloco = entrada[regiao]
            if not isinstance(bloco, dict):
                raise CalibracaoInvalida(
                    f"{onde}.{regiao} precisa ser um objeto com `regiao` e "
                    f"`piso_de_brilho`, veio {type(bloco).__name__}. "
                    f"{CONSERTO_DA_RENDA}"
                )
            if "regiao" not in bloco:
                raise CalibracaoInvalida(
                    f"{onde}.{regiao} esta sem `regiao`. {CONSERTO_DA_RENDA}"
                )
            _conferir_uma_regiao_da_renda(bloco["regiao"], f"{onde}.{regiao}.regiao")
            if "piso_de_brilho" not in bloco:
                raise CalibracaoInvalida(
                    f"{onde}.{regiao} esta sem `piso_de_brilho`. Cada regiao "
                    f"tem o SEU piso e nunca existe um piso unico: medido, a "
                    f"banda util do nivel (190-220) e a da adena (150) nao tem "
                    f"intersecao nenhuma (M-E). {CONSERTO_DA_RENDA}"
                )
            _conferir_um_piso_de_brilho_da_renda(
                bloco["piso_de_brilho"], f"{onde}.{regiao}.piso_de_brilho"
            )
            if "largura_da_banda" in bloco and bloco["largura_da_banda"] is not None:
                largura = _inteiro_da_renda(
                    bloco["largura_da_banda"], f"{onde}.{regiao}.largura_da_banda"
                )
                if largura < 1:
                    raise CalibracaoInvalida(
                        f"{onde}.{regiao}.largura_da_banda={largura} nao faz "
                        f"sentido: a banda em que a leitura sai correta tem ao "
                        f"menos o proprio piso dentro dela. {CONSERTO_DA_RENDA}"
                    )

        geometria = entrada.get("geometria_da_janela")
        if geometria is not None:
            if not isinstance(geometria, dict):
                raise CalibracaoInvalida(
                    f"{onde}.geometria_da_janela precisa ser um objeto com "
                    f"largura e altura, veio {type(geometria).__name__}. "
                    f"{CONSERTO_DA_RENDA}"
                )
            for campo in ("largura", "altura"):
                if campo in geometria:
                    valor = _inteiro_da_renda(
                        geometria[campo], f"{onde}.geometria_da_janela.{campo}"
                    )
                    if valor <= 0:
                        raise CalibracaoInvalida(
                            f"{onde}.geometria_da_janela.{campo}={valor} nao e "
                            f"positivo. {CONSERTO_DA_RENDA}"
                        )


def _conferir_os_moldes_da_barra(conjunto) -> None:
    """Os moldes da fonte da barra: confere a FORMA, e NUNCA a completude.

    A SEPARACAO E DELIBERADA E ELA E O CORACAO DESTA FUNCAO. Um conjunto com
    oito dos onze rotulos e um arquivo perfeitamente bem formado — e o estado
    em que o usuario fica entre uma rodada do cortador e a seguinte. Recusar
    aqui trocaria uma recusa nomeada por uma ferramenta que nao abre: um
    conjunto incompleto nao impede o scanner de subir e de ler o EXP e o nivel,
    ele impede UM campo de ser lido. Quem confere completude e a LEITURA, por
    `mercado_leitura.conjunto_descreve_numeros`, e ela recusa nomeando os que
    faltam.

    (A razao que este estado tinha ganhado — "esperar o farm produzir um `5` e
    um `7`" — CAIU, e cai citada: o M-L mediu os dois na tela AGORA, no bonus
    da Faerlina (`592%`) e no EXP da Yazalaque (`76.6646%`). O estado continua
    legitimo; ele so deixou de ser o estado ESPERADO.)

    O QUE E FORMA: rotulo de UM caractere, altura e largura positivas, altura
    dominante coerente entre os moldes, rotulo nao repetido, e as duas soleiras
    em `[0, 1]`. Sao as mesmas guardas que `mercado_visao.glifos_de_calibracao`
    ja faz na volta — repetidas aqui porque e no arranque que a mensagem ainda
    pode dizer "recalibre" com o usuario olhando para o console.
    """
    if conjunto is None:
        return
    if not isinstance(conjunto, dict):
        raise CalibracaoInvalida(
            f"renda_moldes_da_barra precisa ser um objeto com `moldes`, "
            f"`piso_de_leitura` e `margem_de_leitura`, veio "
            f"{type(conjunto).__name__}. {CONSERTO_DA_RENDA}"
        )

    moldes = conjunto.get("moldes")
    if moldes is not None and not isinstance(moldes, list):
        raise CalibracaoInvalida(
            f"renda_moldes_da_barra.moldes precisa ser uma lista, veio "
            f"{type(moldes).__name__}. {CONSERTO_DA_RENDA}"
        )

    alturas: list[int] = []
    vistos: set[str] = set()
    for indice, bruto in enumerate(moldes or []):
        onde = f"renda_moldes_da_barra.moldes[{indice}]"
        if not isinstance(bruto, dict):
            raise CalibracaoInvalida(
                f"{onde} precisa ser um objeto, veio {type(bruto).__name__}. "
                f"{CONSERTO_DA_RENDA}"
            )
        rotulo = bruto.get("glifo")
        if not isinstance(rotulo, str) or len(rotulo) != 1:
            raise CalibracaoInvalida(
                f"{onde} tem rotulo {rotulo!r}, que nao e UM caractere. O "
                f"rotulo E a identidade do glifo: um rotulo de dois caracteres "
                f"nunca vira digito nenhum, e o molde ficaria no arquivo sem "
                f"nunca ser usado. {CONSERTO_DA_RENDA}"
            )
        if rotulo in vistos:
            raise CalibracaoInvalida(
                f"renda_moldes_da_barra tem o rotulo {rotulo!r} repetido. Um "
                f"dos dois moldes seria descartado calado, e nao da para saber "
                f"qual e o certo. {CONSERTO_DA_RENDA}"
            )
        vistos.add(rotulo)
        altura = _inteiro_da_renda(bruto.get("altura"), f"{onde}.altura")
        largura = _inteiro_da_renda(bruto.get("largura"), f"{onde}.largura")
        if altura <= 0 or largura <= 0:
            raise CalibracaoInvalida(
                f"{onde} ({rotulo!r}) declara {largura}x{altura}, que nao e uma "
                f"forma. {CONSERTO_DA_RENDA}"
            )
        if not isinstance(bruto.get("molde"), dict):
            raise CalibracaoInvalida(
                f"{onde} ({rotulo!r}): `molde` precisa ser um objeto com "
                f"altura, largura e bytes. {CONSERTO_DA_RENDA}"
            )
        alturas.append(altura)

    # A ALTURA DOMINANTE, e ela e a unica deteccao de transposicao com
    # fundamento aqui: todo glifo de uma calibracao sai da MESMA faixa de
    # linhas compartilhada — medido 10 px nas duas instancias e em todo piso
    # (M-K) —, entao um molde de altura diferente foi cortado de outro lugar ou
    # esta transposto. O argumento e literalmente o de
    # `mercado_visao.glifos_de_calibracao`.
    if alturas:
        dominante = max(set(alturas), key=alturas.count)
        fora = [a for a in alturas if a != dominante]
        if fora:
            raise CalibracaoInvalida(
                f"renda_moldes_da_barra tem molde de altura {sorted(set(fora))} "
                f"num conjunto de altura dominante {dominante}. Todo glifo sai "
                f"da MESMA faixa de linhas compartilhada: uma altura diferente "
                f"foi cortada de outro lugar, ou esta transposta. "
                f"{CONSERTO_DA_RENDA}"
            )

    for chave in ("piso_de_leitura", "margem_de_leitura"):
        valor = conjunto.get(chave)
        if valor is None:
            if moldes:
                raise CalibracaoInvalida(
                    f"renda_moldes_da_barra tem {len(moldes)} molde(s) e esta "
                    f"sem `{chave}`. As duas soleiras sao exigidas SEM default "
                    f"pela leitura de glifo: um default e um numero magico que "
                    f"entra por omissao. {CONSERTO_DA_RENDA}"
                )
            continue
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise CalibracaoInvalida(
                f"renda_moldes_da_barra.{chave} precisa ser um numero, veio "
                f"{type(valor).__name__} ({valor!r}). {CONSERTO_DA_RENDA}"
            )
        if not 0.0 <= float(valor) <= 1.0:
            raise CalibracaoInvalida(
                f"renda_moldes_da_barra.{chave}={valor} esta fora de [0, 1]. "
                f"Ela e uma pontuacao de casamento normalizada, e nada fora "
                f"dessa faixa significa alguma coisa. {CONSERTO_DA_RENDA}"
            )

    folga = conjunto.get("folga_de_cola")
    if folga is not None:
        # `null` E A GUARDA FECHADA, e e assim que a chave nasce: as larguras
        # da barra sao `5` e `2` limpas, com coluna vazia entre elas (M-J) —
        # nao ha glifo colado a partir. Uma folga inteira aqui autorizaria
        # fatiar um icone de 15 px em tres digitos de 5, que e fabricacao de
        # numero e nao leitura.
        valor = _inteiro_da_renda(folga, "renda_moldes_da_barra.folga_de_cola")
        if valor < 0:
            raise CalibracaoInvalida(
                f"renda_moldes_da_barra.folga_de_cola={valor} e negativa. "
                f"{CONSERTO_DA_RENDA}"
            )


# Os TRES numeros de procedencia que toda entrada da ponte carrega.
#
# ELES SAO OBRIGATORIOS E NAO OPCIONAIS, e a razao e a CTX-8: uma constante
# medida em seis minutos e uma medida em tres horas sao o mesmo numero na tela e
# nao valem o mesmo. Sem os denominadores ao lado, ninguem consegue auditar
# depois qual das duas esta no arquivo — e uma constante que ninguem consegue
# auditar e um chute com cara de medicao.
PROCEDENCIA_DA_PONTE = ("n_abates", "n_linhas_de_chat", "janela_em_segundos")


def _conferir_uma_entrada_da_ponte(entrada, onde: str) -> None:
    """`xp_por_ponto` positivo mais a procedencia inteira. FORMA, nunca plausibilidade.

    O validador nao tem como saber se 388.700 e o numero certo para o nivel 67
    — isso e medicao de campo. O que ele sabe e que uma entrada sem
    `xp_por_ponto`, com `xp_por_ponto` zero, ou sem os denominadores da
    procedencia nao e uma constante: e um lugar onde alguem ia escrever uma.
    """
    if not isinstance(entrada, dict):
        raise CalibracaoInvalida(
            f"{onde} precisa ser um objeto com `xp_por_ponto` e a procedencia, "
            f"veio {type(entrada).__name__}. {CONSERTO_DA_RENDA}"
        )

    if "xp_por_ponto" not in entrada:
        raise CalibracaoInvalida(
            f"{onde} esta sem `xp_por_ponto`. E o unico numero que a ponte "
            f"converte: sem ele a entrada existe e nao serve para nada, o que e "
            f"pior que a entrada ausente — a ausente desliga o XP absoluto com "
            f"motivo nomeado. {CONSERTO_DA_RENDA}"
        )
    # `bool` recusado ANTES do teste de inteiro, e a razao e que `True` e um
    # `int` de valor 1: uma ponte de 1 XP por ponto percentual converteria 8
    # pontos de nivel em 8 XP e passaria calada por qualquer teste de "e um
    # inteiro positivo".
    xp = _inteiro_da_renda(entrada["xp_por_ponto"], f"{onde}.xp_por_ponto")
    if xp <= 0:
        raise CalibracaoInvalida(
            f"{onde}.xp_por_ponto={xp} nao e positivo. Uma ponte de zero ou "
            f"menos converteria todo ganho de EXP em zero XP, que e um numero "
            f"perfeitamente formatado e sempre errado. {CONSERTO_DA_RENDA}"
        )

    if "medido_em" not in entrada:
        raise CalibracaoInvalida(
            f"{onde} esta sem `medido_em`. QUANDO a constante foi medida e "
            f"procedencia tanto quanto com quantos abates: uma ponte de tres "
            f"level ups atras descreve outro personagem. {CONSERTO_DA_RENDA}"
        )
    if not isinstance(entrada["medido_em"], str) or not entrada["medido_em"]:
        raise CalibracaoInvalida(
            f"{onde}.medido_em precisa ser uma data em texto (AAAA-MM-DD), "
            f"veio {type(entrada['medido_em']).__name__} "
            f"({entrada['medido_em']!r}). {CONSERTO_DA_RENDA}"
        )

    for campo in PROCEDENCIA_DA_PONTE:
        if campo not in entrada:
            raise CalibracaoInvalida(
                f"{onde} esta sem `{campo}`. A PROCEDENCIA E OBRIGATORIA: uma "
                f"constante medida em seis minutos e uma medida em tres horas "
                f"sao o mesmo numero na tela e nao valem o mesmo, e sem o "
                f"denominador ao lado ninguem consegue saber qual e qual. "
                f"{CONSERTO_DA_RENDA}"
            )
        valor = _inteiro_da_renda(entrada[campo], f"{onde}.{campo}")
        if valor <= 0:
            raise CalibracaoInvalida(
                f"{onde}.{campo}={valor} nao e positivo. Zero abate, zero "
                f"linha de chat ou zero segundo de janela nao e procedencia: e "
                f"ausencia com cara de numero. {CONSERTO_DA_RENDA}"
            )


def _conferir_a_ponte_de_xp(ponte) -> None:
    """A ponte XP<->porcentagem, por personagem e por nivel, conferida no ARRANQUE.

    A REGRA DE AUSENCIA E A DAS IRMAS: a chave inteira ausente ou `None` PASSA
    — e o estado legitimo de "ainda nao medi a ponte", e o consumidor o
    transforma em recusa NOMEADA. Uma entrada PRESENTE porem malformada e
    recusada alto, aqui, com o usuario olhando o console.

    E ELA CONFERE SO O QUE CONHECE. Uma sub-chave que este codigo ainda nao
    conhece atravessa sem ser tocada e sobrevive a ida e volta, porque o dict e
    reemitido cru pelo `salvar`.
    """
    if ponte is None:
        return
    if not isinstance(ponte, dict):
        raise CalibracaoInvalida(
            f"renda_ponte_de_xp precisa ser um objeto com uma entrada por nome "
            f"de personagem, veio {type(ponte).__name__}. {CONSERTO_DA_RENDA}"
        )

    for nome, por_nivel in ponte.items():
        if not isinstance(nome, str) or not nome:
            raise CalibracaoInvalida(
                f"renda_ponte_de_xp tem uma chave que nao e nome de personagem "
                f"({nome!r}). O multiplicador de XP e do PERSONAGEM — a barra "
                f"da Faerlina exibe 562% —, entao a constante nao existe sem "
                f"saber de quem ela e. {CONSERTO_DA_RENDA}"
            )
        onde_do_nome = f"renda_ponte_de_xp[{nome!r}]"
        if not isinstance(por_nivel, dict):
            raise CalibracaoInvalida(
                f"{onde_do_nome} precisa ser um objeto com uma entrada por "
                f"NIVEL, veio {type(por_nivel).__name__}. A constante e por "
                f"nivel porque o custo do nivel muda. {CONSERTO_DA_RENDA}"
            )

        for chave, entrada in por_nivel.items():
            # `bool` fora antes de tudo: `True` e um `int`, e `str(True)` seria
            # a chave `'True'` — um nivel que nao existe entrando calado.
            if isinstance(chave, bool) or not isinstance(chave, (str, int)):
                raise CalibracaoInvalida(
                    f"{onde_do_nome} tem uma chave de nivel que nao e numero "
                    f"({chave!r}). Esperava-se o NIVEL do personagem, como "
                    f"`\"67\"`. {CONSERTO_DA_RENDA}"
                )
            texto = str(chave)
            if not texto.isdigit() or int(texto) <= 0:
                raise CalibracaoInvalida(
                    f"{onde_do_nome} tem uma chave de nivel que nao e numero "
                    f"({chave!r}). Esperava-se o NIVEL do personagem, como "
                    f"`\"67\"`. {CONSERTO_DA_RENDA}"
                )
            _conferir_uma_entrada_da_ponte(
                entrada, f"{onde_do_nome}[{texto!r}]"
            )


def _conferir_as_chaves_da_renda(dados: dict) -> None:
    """As tres chaves da renda sao ENTRADA NAO CONFIAVEL, como as do mercado.

    Mora AQUI, ao lado do portao de versao, e nao no consumidor, pela razao que
    `_conferir_as_chaves_de_mercado` ja escreveu: e no arranque que a mensagem
    ainda pode dizer "recalibre" com o usuario olhando para o console. O
    consumidor roda as duas da manha, no meio do farm.

    As tres chaves ausentes ou `None` passam: e o estado legitimo de "nao
    calibrei a renda", e uma instalacao sem elas precisa continuar subindo
    igual — com a `VERSAO_DO_ESQUEMA` intacta em 2.
    """
    _conferir_a_renda_por_personagem(dados.get("renda_por_personagem"))
    _conferir_os_moldes_da_barra(dados.get("renda_moldes_da_barra"))
    _conferir_a_ponte_de_xp(dados.get("renda_ponte_de_xp"))


# O CONSERTO, escrito uma vez e citado por toda recusa da leitura de pagina.
#
# Toda mensagem deste modulo termina no conserto (`ocr.py:88-98` e o precedente),
# e aqui o conserto e sempre o mesmo comando. Repeti-lo a mao em quinze lugares
# garantiria que o dia em que ele mudasse, catorze ficariam mentindo.
CONSERTO_DO_MERCADO = (
    "Recalibre o mercado: calibrar-mercado.bat --gravacao recordings\\<pasta>"
)


def _numero_de_mercado(
    dados: dict,
    chave: str,
    minimo: float,
    maximo: float | None,
    inclui_o_minimo: bool,
    porque: str,
    campo: str | None = None,
) -> float | None:
    """Um limiar do mercado, conferido em tipo e em faixa. `None` passa sempre.

    `None` passa porque ausencia e FEATURE OFF, nunca erro — o default seguro
    deste projeto inteiro. Quem preenche e a ferramenta que mediu.

    `campo` separa O QUE SE PROCURA de COMO SE CHAMA na mensagem, e entrou no
    05-02 porque os limiares aninhados de `mercado_layouts` se chamam
    `limiar_do_cabecalho` dentro do bloco mas precisam aparecer como
    `mercado_layouts.adena.limiar_do_cabecalho` no erro — senao o usuario abre o
    arquivo e procura uma chave que nao existe naquele nivel. Sem esta
    separacao, passar o nome pontuado como chave de busca faria o `.get`
    devolver `None` e a conferencia inteira PASSAR SEMPRE, calada.
    """
    valor = dados.get(chave if campo is None else campo)
    if valor is None:
        return None
    # `bool` e subclasse de `int`: `True` passaria como numero e viraria limiar
    # 1.0 calado. A exclusao e explicita, como em `glifos_de_calibracao`.
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise CalibracaoInvalida(
            f"{chave} precisa ser um numero, veio {type(valor).__name__} "
            f"({valor!r}). {CONSERTO_DO_MERCADO}"
        )
    baixo = valor < minimo if inclui_o_minimo else valor <= minimo
    alto = maximo is not None and valor > maximo
    if baixo or alto:
        limite = (
            f"[{minimo}, {maximo}]"
            if inclui_o_minimo and maximo is not None
            else f"({minimo}, {maximo}]"
            if maximo is not None
            else f">= {minimo}"
        )
        raise CalibracaoInvalida(
            f"{chave}={valor} esta fora de {limite}. {porque} "
            f"{CONSERTO_DO_MERCADO}"
        )
    return valor


def _inteiro_de_mercado(bruto, chave: str, campo: str) -> int:
    """Um campo inteiro dentro de um objeto do mercado. `bool` fica de fora."""
    valor = bruto.get(campo)
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise CalibracaoInvalida(
            f"{chave}.{campo} precisa ser um inteiro, veio "
            f"{type(valor).__name__} ({valor!r}). {CONSERTO_DO_MERCADO}"
        )
    return valor


def _conferir_a_forma_de_uma_coluna(coluna, chave: str) -> tuple[int, int] | None:
    """A FORMA de uma coluna: `{"dx": int, "largura": int}` com `largura > 0`.

    EXTRAIDA de `_conferir_uma_coluna` no 05-02, e extraida em vez de copiada:
    o bloco aninhado de `mercado_layouts` confere exatamente esta forma, e duas
    validacoes parecidas sobre a mesma forma divergem — e o argumento que este
    arquivo ja faz duas vezes (o `CONSERTO_DO_MERCADO` escrito uma vez so, e a
    lista unica de `pecas_de_calibracao_de_mercado_faltando`).

    O que ficou FORA e a conferencia contra a grade, e de proposito: a coluna de
    topo se confere contra `mercado_grade`, e a aninhada contra a grade DELA,
    que pode ser herdada. Um limite so para as duas seria o limite errado para
    uma delas.

    `dx` NEGATIVO E LEGITIMO: ele e deslocamento a partir da origem do painel, e
    a coluna do nome de negociacao ja e `-385`. Recusar negativo aqui mataria a
    calibracao que funciona hoje.

    Devolve `(dx, largura)`, ou `None` quando a coluna esta ausente.
    """
    if coluna is None:
        return None
    if not isinstance(coluna, dict):
        raise CalibracaoInvalida(
            f"{chave} precisa ser um objeto com dx e largura, veio "
            f"{type(coluna).__name__}. {CONSERTO_DO_MERCADO}"
        )
    dx = _inteiro_de_mercado(coluna, chave, "dx")
    largura = _inteiro_de_mercado(coluna, chave, "largura")
    if largura <= 0:
        raise CalibracaoInvalida(
            f"{chave} tem largura nao-positiva ({largura}). Uma coluna de "
            f"largura zero nao recorta nada, e a leitura ficaria vazia sem uma "
            f"linha de erro. {CONSERTO_DO_MERCADO}"
        )
    return dx, largura


def _conferir_uma_coluna(dados: dict, chave: str) -> None:
    """Uma das quatro colunas: `{"dx": int, "largura": int}` dentro da grade.

    O RETANGULO E CONFERIDO CONTRA A GRADE, e nao so contra o zero (T-02-02).
    Um `dx` mentido nao quebra nada visivel: ele faz a leitura recortar OUTRA
    coluna e devolver um numero plausivel, errado por um fator inteiro. Uma
    serie de precos corrompida assim nao se distingue de uma correta olhando
    para o CSV.

    A conferencia so acontece quando a grade tras numeros utilizaveis. Sem
    grade nao ha limite conhecido, e inventar um seria pior que nao conferir.
    """
    coluna = dados.get(chave)
    forma = _conferir_a_forma_de_uma_coluna(coluna, chave)
    if forma is None:
        return
    dx, largura = forma

    grade = dados.get("mercado_grade")
    if not isinstance(grade, dict):
        return
    grade_dx, grade_largura = grade.get("dx"), grade.get("largura")
    if (
        isinstance(grade_dx, bool)
        or isinstance(grade_largura, bool)
        or not isinstance(grade_dx, int)
        or not isinstance(grade_largura, int)
        or grade_largura <= 0
    ):
        return
    if dx < grade_dx or dx + largura > grade_dx + grade_largura:
        raise CalibracaoInvalida(
            f"{chave} (dx={dx}, largura={largura}) cai FORA da grade, que vai "
            f"de dx={grade_dx} a dx={grade_dx + grade_largura}. Uma coluna "
            f"fora da grade recorta outra coisa e devolve numero plausivel. "
            f"{CONSERTO_DO_MERCADO}"
        )


def _conferir_o_cabecalho_de_coluna(dados: dict) -> None:
    """O molde do cabecalho, conferido ANTES de qualquer reshape (T-02-01).

    A contagem de bytes e conferida AQUI, e nao so no consumidor, porque um
    `reshape` sobre dimensao mentida devolve um molde silenciosamente errado —
    e um molde errado nunca casa com nada: o portao de layout recusaria TODA
    pagina, para sempre, sem uma linha de erro. `mercado_visao` repete a
    conferencia na hora de decodificar; esta e a que o usuario chega a ler, no
    arranque, com o console na frente.
    """
    _conferir_um_molde_de_cabecalho(
        dados.get("mercado_cabecalho_de_coluna"), "mercado_cabecalho_de_coluna"
    )


def _conferir_um_molde_de_cabecalho(cabecalho, chave: str) -> None:
    """O corpo comum da conferencia de UM molde de cabecalho.

    EXTRAIDO de `_conferir_o_cabecalho_de_coluna` no 05-02, pelo mesmo motivo de
    `_conferir_a_forma_de_uma_coluna`: o molde aninhado de `mercado_layouts` tem
    de herdar ESTA disciplina, e uma copia dela envelheceria contra a original.
    A contagem de bytes contra `altura * largura` e o coracao, e ela e o que
    impede um `reshape` sobre dimensao mentida de produzir um molde
    silenciosamente errado — que nunca casa com nada e recusaria TODA pagina,
    para sempre, sem uma linha de erro.

    `chave` entra por parametro so para a mensagem dizer QUAL molde caiu: com
    layouts aninhados existem varios, e "mercado_cabecalho_de_coluna corrompido"
    mandaria o usuario olhar o lugar errado do arquivo.
    """
    if cabecalho is None:
        return
    if not isinstance(cabecalho, dict):
        raise CalibracaoInvalida(
            f"{chave} precisa ser um objeto com layout, "
            f"dy, altura, largura, bytes e corte_de_brilho, veio "
            f"{type(cabecalho).__name__}. {CONSERTO_DO_MERCADO}"
        )

    layout = cabecalho.get("layout")
    if not isinstance(layout, str) or not layout:
        raise CalibracaoInvalida(
            f"{chave} esta sem layout utilizavel "
            f"({layout!r}). O layout E o que este molde afirma: sem ele o "
            f"casamento nao decide nada. {CONSERTO_DO_MERCADO}"
        )

    _inteiro_de_mercado(cabecalho, chave, "dy")
    altura = _inteiro_de_mercado(cabecalho, chave, "altura")
    largura = _inteiro_de_mercado(cabecalho, chave, "largura")
    if altura <= 0 or largura <= 0:
        raise CalibracaoInvalida(
            f"{chave} tem dimensao nao-positiva "
            f"({altura}x{largura}). {CONSERTO_DO_MERCADO}"
        )

    corte = _inteiro_de_mercado(cabecalho, chave, "corte_de_brilho")
    if not 0 <= corte <= 255:
        raise CalibracaoInvalida(
            f"{chave}.corte_de_brilho={corte} esta fora de "
            f"[0, 255]. Ele e um nivel de brilho de 8 bits, medido no proprio "
            f"frame. {CONSERTO_DO_MERCADO}"
        )

    brutos = cabecalho.get("bytes")
    if not isinstance(brutos, str):
        raise CalibracaoInvalida(
            f"{chave}.bytes precisa ser uma string hex, "
            f"veio {type(brutos).__name__}. {CONSERTO_DO_MERCADO}"
        )
    try:
        quantos = len(bytes.fromhex(brutos))
    except ValueError as erro:
        raise CalibracaoInvalida(
            f"{chave}.bytes nao e hex valido ({erro}). "
            f"{CONSERTO_DO_MERCADO}"
        ) from erro
    pedidos = altura * largura
    if quantos != pedidos:
        raise CalibracaoInvalida(
            f"{chave} corrompido: altura {altura} x "
            f"largura {largura} pedem {pedidos} bytes, mas ha {quantos}. "
            f"{CONSERTO_DO_MERCADO}"
        )


def _conferir_os_layouts_de_mercado(dados: dict) -> None:
    """Os layouts ALEM da negociacao, aninhados por nome. Ausencia passa sempre.

    POR QUE ELA EXISTE, e por que no ARRANQUE: o `calibration.json` e entrada
    NAO CONFIAVEL — o usuario edita a mao, e o `bytes` hex e o campo mais facil
    de truncar num copiar-colar. Sem esta conferencia, um hex torto so levanta
    la dentro do construtor do `LeitorDePagina`, quando `cabecalho_de_calibracao`
    tenta o `reshape` — e aquele caminho, por desenho, vira FEATURE OFF COM
    AVISO. O usuario veria "a leitura de mercado nao vai acontecer" e nunca a
    causa. Aqui, no arranque, a mensagem ainda pode dizer "recalibre" com ele
    olhando o console (T-05-04).

    A `negociacao` NAO PODE APARECER como chave aninhada. Ela mora nas chaves de
    TOPO, e aceitar as duas formas criaria duas verdades sobre a mesma grade: no
    dia em que discordassem, a leitura sairia da coluna errada com a mesma
    confianca da certa, e uma serie de precos corrompida por fator inteiro nao
    se distingue de uma correta olhando para o CSV.

    O `grade` PODE SAIR CURTO ou ausente, e isto vai escrito aqui para o dia em
    que alguem procurar por que o bloco e mais magro que `mercado_grade`: os
    campos que faltam sao HERDADOS de `mercado_grade` na leitura (`dx`, `dy`,
    `largura`, `altura_da_linha`, `linhas_por_pagina`). Hoje eles sao IDENTICOS
    aos da negociacao — medido no 05-02 — e herdar e o que impede duas copias do
    mesmo numero de envelhecerem separadas.
    """
    layouts = dados.get("mercado_layouts")
    if layouts is None:
        return
    if not isinstance(layouts, dict):
        raise CalibracaoInvalida(
            f"mercado_layouts precisa ser um objeto de layouts por nome, veio "
            f"{type(layouts).__name__}. {CONSERTO_DO_MERCADO}"
        )

    for nome, bloco in layouts.items():
        chave = f"mercado_layouts.{nome}"
        if nome == "negociacao":
            raise CalibracaoInvalida(
                f"mercado_layouts traz 'negociacao', e ela NAO mora ai: a "
                f"negociacao e as chaves de TOPO (mercado_grade, "
                f"mercado_coluna_do_*, mercado_cabecalho_de_coluna). Duas "
                f"verdades sobre a mesma grade divergem, e a divergencia aqui "
                f"e ler a coluna errada com confianca. Apague este bloco. "
                f"{CONSERTO_DO_MERCADO}"
            )
        if not isinstance(bloco, dict):
            raise CalibracaoInvalida(
                f"{chave} precisa ser um objeto com cabecalho, "
                f"limiar_do_cabecalho e colunas, veio "
                f"{type(bloco).__name__}. {CONSERTO_DO_MERCADO}"
            )

        _conferir_um_molde_de_cabecalho(bloco.get("cabecalho"), f"{chave}.cabecalho")
        _numero_de_mercado(
            bloco,
            f"{chave}.limiar_do_cabecalho",
            0.0,
            1.0,
            inclui_o_minimo=False,
            porque=(
                "Um limiar <= 0 faz TODA banda casar com TODO layout, e com "
                "MAIS de um layout calibrado isso deixa de ser 'le demais' e "
                "passa a ser 'le com o modelo de coluna do outro'."
            ),
            campo="limiar_do_cabecalho",
        )

        colunas = bloco.get("colunas")
        if colunas is not None:
            if not isinstance(colunas, dict):
                raise CalibracaoInvalida(
                    f"{chave}.colunas precisa ser um objeto de colunas por "
                    f"nome, veio {type(colunas).__name__}. "
                    f"{CONSERTO_DO_MERCADO}"
                )
            for coluna, valor in colunas.items():
                _conferir_a_forma_de_uma_coluna(valor, f"{chave}.colunas.{coluna}")

        grade = bloco.get("grade")
        if grade is not None and not isinstance(grade, dict):
            raise CalibracaoInvalida(
                f"{chave}.grade precisa ser um objeto, veio "
                f"{type(grade).__name__}. Ela pode sair CURTA ou ausente — os "
                f"campos que faltam sao herdados de mercado_grade —, mas o que "
                f"vier tem de ser um objeto. {CONSERTO_DO_MERCADO}"
            )


def _conferir_a_sonda_do_fundo(dados: dict) -> None:
    """O trecho SEM TEXTO onde o nivel de fundo da linha e medido."""
    sonda = dados.get("mercado_sonda_do_fundo")
    if sonda is None:
        return
    if not isinstance(sonda, dict):
        raise CalibracaoInvalida(
            f"mercado_sonda_do_fundo precisa ser um objeto com dx0, dx1 e "
            f"folga, veio {type(sonda).__name__}. {CONSERTO_DO_MERCADO}"
        )
    dx0 = _inteiro_de_mercado(sonda, "mercado_sonda_do_fundo", "dx0")
    dx1 = _inteiro_de_mercado(sonda, "mercado_sonda_do_fundo", "dx1")
    folga = _inteiro_de_mercado(sonda, "mercado_sonda_do_fundo", "folga")
    if dx1 <= dx0:
        raise CalibracaoInvalida(
            f"mercado_sonda_do_fundo tem dx1={dx1} <= dx0={dx0}: o trecho de "
            f"fundo teria largura zero ou negativa, e a medida de oclusao sairia "
            f"de um recorte vazio. {CONSERTO_DO_MERCADO}"
        )
    if folga < 0:
        raise CalibracaoInvalida(
            f"mercado_sonda_do_fundo tem folga negativa ({folga}). "
            f"{CONSERTO_DO_MERCADO}"
        )

    # A FAIXA VERTICAL e opcional, mas nao pela metade. Uma sonda com `dy0` e
    # sem `dy1` nao e uma calibracao antiga: e uma calibracao QUEBRADA, e
    # deixa-la cair calada no fallback da linha inteira mediria uma geometria
    # que ninguem pediu.
    tem_dy0 = sonda.get("dy0") is not None
    tem_dy1 = sonda.get("dy1") is not None
    if tem_dy0 != tem_dy1:
        raise CalibracaoInvalida(
            f"mercado_sonda_do_fundo traz dy0={sonda.get('dy0')!r} e "
            f"dy1={sonda.get('dy1')!r}: a faixa vertical da banda e opcional, "
            f"mas os dois vem juntos ou nenhum vem. {CONSERTO_DO_MERCADO}"
        )
    if tem_dy0 and tem_dy1:
        dy0 = _inteiro_de_mercado(sonda, "mercado_sonda_do_fundo", "dy0")
        dy1 = _inteiro_de_mercado(sonda, "mercado_sonda_do_fundo", "dy1")
        if dy0 < 0:
            raise CalibracaoInvalida(
                f"mercado_sonda_do_fundo tem dy0 negativo ({dy0}): a banda "
                f"comecaria fora da linha. {CONSERTO_DO_MERCADO}"
            )
        if dy1 <= dy0:
            raise CalibracaoInvalida(
                f"mercado_sonda_do_fundo tem dy1={dy1} <= dy0={dy0}: a banda "
                f"teria altura zero ou negativa, e a medida de oclusao sairia "
                f"de um recorte vazio. {CONSERTO_DO_MERCADO}"
            )


def _conferir_o_piso_de_linhas_comparadas(dados: dict) -> None:
    """O piso do estabilizador: `>= 1` e `<= linhas_por_pagina`.

    Um piso ZERO aceitaria o ACORDO TRIVIAL — duas paginas em que tudo foi
    descartado "concordam" por falta de material. Um piso MAIOR QUE A PAGINA
    desligaria a leitura calado, que e pior: o produto sobe, nao reclama de
    nada, e nunca aceita uma pagina.
    """
    piso = dados.get("mercado_minimo_de_linhas_comparadas")
    if piso is None:
        return
    if isinstance(piso, bool) or not isinstance(piso, int):
        raise CalibracaoInvalida(
            f"mercado_minimo_de_linhas_comparadas precisa ser um inteiro, veio "
            f"{type(piso).__name__} ({piso!r}). {CONSERTO_DO_MERCADO}"
        )
    if piso < 1:
        raise CalibracaoInvalida(
            f"mercado_minimo_de_linhas_comparadas={piso} e menor que 1. Um piso "
            f"zero aceita o acordo trivial: duas paginas sem nenhuma linha lida "
            f"'concordam' por falta de material. {CONSERTO_DO_MERCADO}"
        )
    grade = dados.get("mercado_grade")
    if not isinstance(grade, dict):
        return
    por_pagina = grade.get("linhas_por_pagina")
    if isinstance(por_pagina, bool) or not isinstance(por_pagina, int):
        return
    if por_pagina > 0 and piso > por_pagina:
        raise CalibracaoInvalida(
            f"mercado_minimo_de_linhas_comparadas={piso} e maior que as "
            f"{por_pagina} linhas da pagina. Nenhuma pagina jamais alcancaria "
            f"esse piso, e a leitura ficaria desligada CALADA. "
            f"{CONSERTO_DO_MERCADO}"
        )


def _conferir_o_piso_de_brilho_da_quantidade(dados: dict) -> None:
    """O piso de brilho da coluna Quantity: inteiro em `[1, 254]`.

    ELE E O UNICO LIMIAR DE MERCADO QUE E UM NIVEL DE V E NAO UMA FRACAO, entao
    ele tem conferencia propria em vez de entrar em `_numero_de_mercado`: ali
    `float` passa, e aqui um `165.5` nao significa nada — a mascara compara
    `hsv[:, :, 2] > piso` sobre um `uint8`.

    OS DOIS EXTREMOS DESLIGAM A LEITURA CALADOS, que e a razao de a faixa ser
    fechada dos dois lados:

    - piso `0` faz a mascara CHEIA. Toda coluna do recorte "tem texto", a
      segmentacao devolve UM run gigante, e toda celula vira ruido classificado
      com confianca.
    - piso `255` faz a mascara VAZIA. Nao ha faixa, nao ha run, e toda celula
      cai — a leitura de quantidade some sem uma linha de log dizendo por que.

    `bool` e recusado EXPLICITAMENTE porque e subclasse de `int`: `True` passaria
    por `isinstance(valor, int)` e viraria piso 1 calado, que e o caso `0`
    disfarcado.

    `None` sempre passa: e feature OFF, o estado legitimo de "ainda nao medi".
    """
    piso = dados.get("mercado_limiar_de_brilho_da_quantidade")
    if piso is None:
        return
    conserto = (
        "Rode `python tools/medir_brilho_da_quantidade.py --gravar` para MEDIR "
        "este piso; ele nunca se escreve a mao."
    )
    if isinstance(piso, bool) or not isinstance(piso, int):
        raise CalibracaoInvalida(
            f"mercado_limiar_de_brilho_da_quantidade precisa ser um inteiro "
            f"(um nivel de V, 0-255), veio {type(piso).__name__} ({piso!r}). "
            f"{conserto}"
        )
    if not 1 <= piso <= 254:
        raise CalibracaoInvalida(
            f"mercado_limiar_de_brilho_da_quantidade={piso} esta fora de "
            f"[1, 254]. Um piso 0 faz a mascara CHEIA e toda celula vira ruido; "
            f"um piso 255 faz a mascara VAZIA e toda celula cai. Os dois "
            f"desligariam a leitura de quantidade CALADOS. {conserto}"
        )


def _conferir_a_folga_de_cola_do_glifo(dados: dict) -> None:
    """A folga de cola: inteiro em `[0, TETO_DA_FOLGA_DE_COLA]`.

    ELA TEM CONFERENCIA PROPRIA, e nao entra em `_numero_de_mercado`, pela mesma
    razao da irma acima: ali `float` passa, e aqui um `1.5` nao significa nada --
    a folga e um numero de COLUNAS, e nao existe meia coluna.

    O `0` E LEGITIMO AQUI, E ISSO E A DIFERENCA PARA A IRMA. No piso de brilho o
    `0` desligava a leitura calado (mascara CHEIA); aqui ele e a particao com as
    larguras de MOLDE puras, que e o afrouxamento MINIMO possivel e um resultado
    de medicao perfeitamente legitimo.

    O TETO E O QUE DIMENSIONA O RISCO. Uma folga grande demais nao volta a
    falhar FECHADO: ela libera cortes que a geometria nao sustenta e abre espaco
    para INVENTAR numero -- medido, o run de 11 px de `frame_000105.png` L6
    admite um corte `6+5` que produz `144,44` e passa nas duas peneiras, contra
    o corte certo `7+4` que produz `149,44`.

    `bool` e recusado EXPLICITAMENTE porque e subclasse de `int`: `True`
    passaria por `isinstance(valor, int)` e viraria folga 1 calada.

    `None` sempre passa: e a GUARDA, o estado legitimo de "ainda nao medi" -- e
    aqui a ausencia degrada para MAIS SEGURO, e nao para o comportamento antigo.
    """
    folga = dados.get("mercado_folga_de_cola_do_glifo")
    if folga is None:
        return
    conserto = (
        "Rode `python tools/medir_largura_de_run.py --gravar` para MEDIR esta "
        "folga; ela nunca se escreve a mao."
    )
    if isinstance(folga, bool) or not isinstance(folga, int):
        raise CalibracaoInvalida(
            f"mercado_folga_de_cola_do_glifo precisa ser um inteiro (um numero "
            f"de COLUNAS), veio {type(folga).__name__} ({folga!r}). {conserto}"
        )
    if not 0 <= folga <= TETO_DA_FOLGA_DE_COLA:
        raise CalibracaoInvalida(
            f"mercado_folga_de_cola_do_glifo={folga} esta fora de "
            f"[0, {TETO_DA_FOLGA_DE_COLA}]. Uma folga negativa nao significa "
            f"nada, e uma folga acima do teto libera cortes que a geometria do "
            f"glifo nao sustenta -- ela nao falha FECHADO, ela INVENTA numero. "
            f"{conserto}"
        )


def _conferir_as_chaves_da_leitura_de_pagina(dados: dict) -> None:
    """As quatorze chaves da Fase 02, na mesma disciplina das irmas.

    Tipo, faixa, `bool` excluido do `int`, e toda mensagem terminando no
    conserto. AUSENCIA NUNCA E ERRO: e feature OFF, o unico default seguro para
    um sinal que a Fase 4 vai usar perto do detector de morte.
    """
    for chave in (
        "mercado_coluna_do_nome",
        "mercado_coluna_da_quantidade",
        "mercado_coluna_do_total",
        "mercado_coluna_do_unitario",
    ):
        _conferir_uma_coluna(dados, chave)

    _conferir_o_cabecalho_de_coluna(dados)
    _conferir_os_layouts_de_mercado(dados)
    _conferir_a_sonda_do_fundo(dados)

    _numero_de_mercado(
        dados,
        "mercado_limiar_do_cabecalho",
        0.0,
        1.0,
        inclui_o_minimo=False,
        porque=(
            "Um limiar <= 0 faz TODA banda casar com TODO layout, e ler a "
            "coluna errada com confianca e o modo de falha que esta fase existe "
            "para impedir."
        ),
    )
    _numero_de_mercado(
        dados,
        "mercado_limiar_de_dispersao_do_fundo",
        0.0,
        1.0,
        inclui_o_minimo=True,
        porque=(
            "Ele e uma dispersao normalizada do nivel de fundo: fora de [0, 1] "
            "nao significa nada, e um valor alto demais aceitaria linha coberta "
            "por tooltip como linha limpa."
        ),
    )
    piso_de_glifo = _numero_de_mercado(
        dados,
        "mercado_limiar_de_leitura_de_glifo",
        0.0,
        1.0,
        inclui_o_minimo=False,
        porque=(
            "Um piso frouxo faz TODO recorte casar com TODO glifo; um `0` lido "
            "como `8` nao acrescenta ruido a serie, TROCA o numero."
        ),
    )
    _numero_de_mercado(
        dados,
        "mercado_margem_de_leitura_de_glifo",
        0.0,
        1.0,
        inclui_o_minimo=True,
        porque=(
            "Ela e a distancia minima entre o primeiro e o segundo colocado, na "
            "mesma escala do casamento."
        ),
    )
    corte = _numero_de_mercado(
        dados,
        "mercado_corte_de_similaridade",
        0.0,
        1.0,
        inclui_o_minimo=False,
        porque=(
            "Acima dele duas leituras viram a MESMA serie; um corte <= 0 "
            "fundiria o catalogo inteiro numa serie so, e fusao no CSV e "
            "irreversivel."
        ),
    )
    piso_de_similaridade = _numero_de_mercado(
        dados,
        "mercado_piso_de_similaridade",
        0.0,
        1.0,
        inclui_o_minimo=True,
        porque="Ele e uma similaridade, na mesma escala do corte.",
    )
    if (
        corte is not None
        and piso_de_similaridade is not None
        and piso_de_similaridade > corte
    ):
        raise CalibracaoInvalida(
            f"mercado_piso_de_similaridade={piso_de_similaridade} e maior que "
            f"mercado_corte_de_similaridade={corte}. A faixa cinzenta ficaria "
            f"invertida e nao existiria descarte nenhum — toda leitura duvidosa "
            f"viraria serie. {CONSERTO_DO_MERCADO}"
        )
    # `piso_de_glifo` e lido para conferir a faixa; nao ha relacao a afirmar
    # entre ele e a margem antes de o 02-02 medir as duas juntas.
    del piso_de_glifo

    _numero_de_mercado(
        dados,
        "mercado_tolerancia_do_cruzamento",
        0.0,
        None,
        inclui_o_minimo=True,
        porque=(
            "Ela e uma folga em centesimos por unidade: negativa nao significa "
            "nada. AUSENTE ou nula e a guarda DESLIGADA, que e o default seguro."
        ),
    )
    _conferir_o_piso_de_linhas_comparadas(dados)
    _conferir_o_piso_de_brilho_da_quantidade(dados)
    _conferir_a_folga_de_cola_do_glifo(dados)


def descrever_geometria_da_tela() -> str:
    """Assinatura estavel do arranjo de monitores."""
    import mss

    with mss.mss() as sct:
        partes = [
            f"{m['width']}x{m['height']}+{m['left']}+{m['top']}"
            for m in sct.monitors[1:]
        ]
    return ";".join(partes)


# Valores medidos na tela real do usuario em 2026-08-24, cliente XM Essence,
# janela do Yazalaque em (1713,0) num monitor de 3440x1440. Servem de ponto de
# partida; a ferramenta de calibracao regrava tudo isto.
LIMIARES_HP_PADRAO = LimiaresDeCor(
    matiz_min=168,  # > matiz_max: volta no circulo, duas faixas combinadas
    matiz_max=12,
    saturacao_min=120,  # barra cheia da ~210, terreno da ~75
    valor_min=60,
)

LIMIARES_MP_PADRAO = LimiaresDeCor(
    matiz_min=95,
    matiz_max=130,
    saturacao_min=120,  # barra cheia da ~195
    valor_min=60,
)
