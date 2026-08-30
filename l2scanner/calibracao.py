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
    nome_dx: int = 26  # a partir do icone, pulando o emblema de classe
    nome_dy: int = -24
    nome_largura: int = 100
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
    # `{"dx0": int, "dx1": int, "folga": int}`, um trecho SEM TEXTO da linha.
    #
    # O sinal de oclusao e o fundo alternado, e nao a confianca do casamento: a
    # tooltip do jogo e SEMITRANSPARENTE, entao um numero coberto ainda produz
    # glifos plausiveis com boa confianca e valor errado. Recusar pela confianca
    # seria o incidente 27x um nivel acima.
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
        """Quem tem impressao digital visual gravada."""
        return {a.nome for a in self.assinaturas}

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
            versao=versao,
        )

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
) -> float | None:
    """Um limiar do mercado, conferido em tipo e em faixa. `None` passa sempre.

    `None` passa porque ausencia e FEATURE OFF, nunca erro — o default seguro
    deste projeto inteiro. Quem preenche e a ferramenta que mediu.
    """
    valor = dados.get(chave)
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
    if coluna is None:
        return
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
    cabecalho = dados.get("mercado_cabecalho_de_coluna")
    if cabecalho is None:
        return
    if not isinstance(cabecalho, dict):
        raise CalibracaoInvalida(
            f"mercado_cabecalho_de_coluna precisa ser um objeto com layout, "
            f"dy, altura, largura, bytes e corte_de_brilho, veio "
            f"{type(cabecalho).__name__}. {CONSERTO_DO_MERCADO}"
        )

    layout = cabecalho.get("layout")
    if not isinstance(layout, str) or not layout:
        raise CalibracaoInvalida(
            f"mercado_cabecalho_de_coluna esta sem layout utilizavel "
            f"({layout!r}). O layout E o que este molde afirma: sem ele o "
            f"casamento nao decide nada. {CONSERTO_DO_MERCADO}"
        )

    _inteiro_de_mercado(cabecalho, "mercado_cabecalho_de_coluna", "dy")
    altura = _inteiro_de_mercado(cabecalho, "mercado_cabecalho_de_coluna", "altura")
    largura = _inteiro_de_mercado(cabecalho, "mercado_cabecalho_de_coluna", "largura")
    if altura <= 0 or largura <= 0:
        raise CalibracaoInvalida(
            f"mercado_cabecalho_de_coluna tem dimensao nao-positiva "
            f"({altura}x{largura}). {CONSERTO_DO_MERCADO}"
        )

    corte = _inteiro_de_mercado(
        cabecalho, "mercado_cabecalho_de_coluna", "corte_de_brilho"
    )
    if not 0 <= corte <= 255:
        raise CalibracaoInvalida(
            f"mercado_cabecalho_de_coluna.corte_de_brilho={corte} esta fora de "
            f"[0, 255]. Ele e um nivel de brilho de 8 bits, medido no proprio "
            f"frame. {CONSERTO_DO_MERCADO}"
        )

    brutos = cabecalho.get("bytes")
    if not isinstance(brutos, str):
        raise CalibracaoInvalida(
            f"mercado_cabecalho_de_coluna.bytes precisa ser uma string hex, "
            f"veio {type(brutos).__name__}. {CONSERTO_DO_MERCADO}"
        )
    try:
        quantos = len(bytes.fromhex(brutos))
    except ValueError as erro:
        raise CalibracaoInvalida(
            f"mercado_cabecalho_de_coluna.bytes nao e hex valido ({erro}). "
            f"{CONSERTO_DO_MERCADO}"
        ) from erro
    pedidos = altura * largura
    if quantos != pedidos:
        raise CalibracaoInvalida(
            f"mercado_cabecalho_de_coluna corrompido: altura {altura} x "
            f"largura {largura} pedem {pedidos} bytes, mas ha {quantos}. "
            f"{CONSERTO_DO_MERCADO}"
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
