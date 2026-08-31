"""O laco de producao do modo `--mercado` (DETC-02): a TERCEIRA invocacao.

O QUE ESTE MODULO E
====================
Ele e o CHAMADOR que faltava. A Fase 2 entregou `LeitorDePagina` e `Catalogo`
sem chamador de producao; a Fase 3 entregou `RegistroDeObservacoes` e
`montar_registro_de_mercado` sem chamador, de proposito. Aqui os tres fios
ganham um processo que os liga: captura a janela, le a pagina, grava a serie no
catalogo de nomes E a observacao no CSV, e conta honestamente as duas metades do
que viu.

O precedente literal e `tools/gerar_observacoes_do_censo.py`, que ja faz isto
sobre PNG de disco. A diferenca e a fonte (tela ao vivo em vez de arquivo), a
cadencia (um tick por segundo em vez de tao rapido quanto o disco entrega) e o
desfecho (o modo nao para no fim de uma pasta).

O QUE ELE NAO E, E ESTA E A LINHA QUE NAO SE CRUZA
===================================================
Ele NAO vigia party, NAO envia alerta e NAO conhece o detector de morte. Nada
aqui importa `rastreador`, `visao`, `sessao` ou `presenca`, e ha tripwire de
importacao prendendo isso nas duas direcoes (`tests/test_mercado_27x.py` prova o
lado do rastreador, `tests/test_mercado_firewall_de_fase.py` prova este lado).
Acoplar o sinal de mercado ao detector de morte e precisamente a manobra que
causou o incidente das 27 mortes falsas.

Ele tambem NAO ESCREVE `calibration.json`: le, e so. Quem escreve e a ferramenta
de calibracao.

ELE RECUSA A SUBIR, E NUNCA SOBE DEGRADADO
===========================================
No scanner de party, mercado e um recurso opcional e a montagem que falha
degrada para `None` com o scanner de pe — porque o produto la e o alerta de
morte. AQUI A FEATURE E O PRODUTO. Um `--mercado` que subisse sem OCR, sem
calibracao ou sobre o layout errado ficaria uma hora piscando no console sem
gravar uma linha, e o usuario sairia do farm achando que coletou. Por isso os
portoes de arranque saem com codigo 2, o mesmo que o `__main__` ja usa para
recusa de configuracao.

A NUMERACAO NOMEADA DA FERRAMENTA DO CENSO (`SAIDA_SEM_OCR`, `SAIDA_SEM_...`)
NAO VEM JUNTO. La ela existe porque uma ferramenta de bancada tem oito desfechos
que um roteiro humano precisa distinguir; aqui ha um so ("nao da para ler o
mercado assim") e importar a segunda convencao daria ao produto duas.

NAO HA `--saida`, E A AUSENCIA E DELIBERADA
============================================
`razao_para_recusar_a_saida`, na ferramenta do censo, existe para impedir que
uma linha derivada de replay entre na `.mercado/` com carimbo de AGORA sobre um
preco visto dias atras. Uma flag de destino aqui furaria essa protecao pelo
outro lado: quem quisesse contaminar o registro so precisaria apontar o modo ao
vivo para a pasta de rascunho e voltar. A pasta e a de producao, sempre; so o
TESTE injeta `pasta=tmp_path`, pelo parametro nomeado, que a linha de comando
nao alcanca.
"""

from __future__ import annotations

import logging
import sys
import time
from collections import Counter
from dataclasses import dataclass, field

from . import mercado_registro, ocr
from .agenda import AgendaInvalida
from .config import ReceitaInvalida, ler_receitas, ler_watchlist_do_mercado
from .frames import Regiao
from .mercado_analise import ModeloDeMercado
from .mercado_console import (
    SEGUNDOS_ENTRE_SECOES,
    OrcamentoDoTick,
    acumular_motivos,
    destaque_ao_vivo,
    linha_ao_vivo,
    resumo_da_sessao,
    secao_da_margem,
    secao_do_vale_quanto,
    transicao_do_painel,
)
from .mercado_pagina import (
    LeitorDePagina,
    pecas_de_calibracao_de_mercado_faltando,
)
from .mercado_visao import RastreioDoPainel, ancoras_de_calibracao

log = logging.getLogger(__name__)


# O codigo de recusa de configuracao do projeto. `__main__.main` ja devolve 2
# para `CalibracaoInvalida`, para `ConfiguracaoPerigosa` e para janela ambigua;
# os portoes daqui sao a mesma familia de recusa e usam o mesmo numero.
SAIDA_RECUSADA = 2

# O desfecho de "rodei cego": copiado do laco principal, que devolve 1 depois de
# dez erros seguidos de captura.
SAIDA_CEGA = 1

# A cada quantas paginas aceitas o catalogo tambem e gravado, alem do `finally`.
#
# VINTE E ESCOLHA, E NAO MEDICAO — um numero que nao foi medido precisa dizer
# que nao foi. A razao dele existir: `Catalogo.gravar()` reescreve o arquivo
# INTEIRO de forma atomica, entao grava-lo por tick seria trabalho puro; mas um
# encerramento por `taskkill` (que nao roda `finally`) nao pode custar as series
# da sessao inteira. Vinte paginas aceitas sao, pelo censo, da ordem de uma a
# duas dezenas de minutos de painel aberto.
PAGINAS_ENTRE_GRAVACOES_DO_CATALOGO = 20

# O intervalo MINIMO, em milissegundos, entre frames que a WGC entrega a ESTE
# modo. E a unica alavanca real de DETC-02 ("o modo mercado nao degrada o modo
# party"), e ela e ligada SO aqui: `JanelaSource` mantem o padrao `None`, e o
# caminho da party continua byte-identico ao de sempre.
#
# O QUE ELE COMPRA. A WGC entrega ~38 fps (medido) e este modo consome 1 por
# segundo. Cada frame da JANELA INTEIRA custa um memcpy da ordem de 7,2 MB, ou
# seja da ordem de 273 MB/s de copia jogada fora - numero DERIVADO (38 x 7,2 MB),
# nao medido. A 250 ms a entrega cai para ~4 fps: cerca de 9,5x menos copia,
# sem mudar nada para quem le a 1 Hz.
#
# POR QUE NAO 1000. Com atualizacao a cada ~1000 ms e leitura a cada ~1000 ms,
# a deriva de fase entrega o MESMO buffer varias vezes seguidas;
# `JANELAS_IGUAIS_PARA_CONGELAR` (tres) dispara e o console anuncia CAPTURA
# CONGELADA com o jogo vivo na tela. 250 ms deixa quatro entregas por leitura,
# que e a margem que impede o falso positivo.
#
# 250 E ESCOLHA, E NAO MEDICAO. Ninguem cronometrou 250 contra 200 ou 300 nesta
# maquina; o que foi medido e a taxa da WGC, o tamanho do frame e o gatilho de
# congelamento. Um numero que nao foi medido precisa dizer que nao foi, senao
# vira folclore na proxima fase.
MS_ENTRE_FRAMES_DO_MERCADO = 250

# Quantos erros seguidos de captura ate desistir, copiado de
# `__main__.laco_principal`: a captura falha PARCIALMENTE (a WGC perde a janela,
# o usuario fecha o jogo), e um laco que insistisse para sempre gastaria a noite
# escrevendo traceback.
ERROS_SEGUIDOS_PARA_DESISTIR = 10


@dataclass
class Contagem:
    """O que a costura viu, em tres numeros que nao se disfarcam um do outro.

    Copiada de `tools/gerar_observacoes_do_censo.py`, com a razao junto:
    `duplicadas` e `perdidas` sao FATOS DIFERENTES e por isso sao campos
    diferentes. `registrar` devolve `False` nos dois casos - chave ja conhecida e
    registro desligado - e somar os dois faria o resumo dizer "descartei 300
    duplicadas" sobre uma sessao em que o disco encheu na terceira linha.
    """

    observacoes: int = 0
    duplicadas: int = 0
    perdidas: int = 0
    series: set[str] = field(default_factory=set)


def _modulo_do_arranque():
    """As montadoras da casa, SEM re-executar `l2scanner/__main__.py`.

    Rodando por `python -m l2scanner`, aquele arquivo ja esta em `sys.modules`
    sob o nome `__main__`. Um `from .__main__ import ...` faria o Python
    importa-lo DE NOVO sob o nome `l2scanner.__main__`, executando o arquivo
    inteiro uma segunda vez - e o `log` da copia teria outro nome de logger, sem
    nenhum dos manipuladores que `configurar_log` acabou de instalar. As duas
    mensagens de erro que o PERS-03 exige que o usuario VEJA sumiriam do console
    exatamente no caso em que elas importam.

    Fora do `python -m` (teste, ferramenta de bancada) o `__main__` e outro
    modulo e o import normal e o certo. A pergunta e por CAPACIDADE e nao por
    nome de arquivo, porque nome de arquivo e o que muda entre os dois casos.
    """
    principal = sys.modules.get("__main__")
    if hasattr(principal, "montar_registro_de_mercado"):
        return principal
    from l2scanner import __main__ as principal

    return principal


def _garantir_log(principal) -> None:
    """Nenhuma mensagem deste modo pode sair sem manipulador.

    `gerar_observacoes_do_censo.py:400` faz `configurar_log` antes da montagem
    pela mesma razao: sem manipulador, o `log.error` que diz por que a feature
    desligou nao chega ao console, e o criterio da fase e literalmente "o
    usuario VE o aviso alto".

    A CHAMADA E CONDICIONAL, e isto e uma correcao do plano. Por
    `python -m l2scanner` o `main()` JA chamou `configurar_log(args.verboso)`
    antes de chegar aqui; chamar de novo acrescentaria um segundo
    `RotatingFileHandler` e um segundo `StreamHandler`, e toda linha da sessao
    sairia DUAS vezes no console e DUAS vezes no arquivo. A guarda pergunta se
    ja ha para onde a mensagem ir - na raiz (onde o `caplog` do pytest instala
    o dele) ou no logger do arranque - e so configura quando nao ha.
    """
    if logging.getLogger().handlers:
        return
    if getattr(principal, "log", None) is not None and principal.log.handlers:
        return
    principal.configurar_log(False)


def _recusar(mensagens: list[str]) -> int:
    """Recusa de arranque: as linhas em ERROR e o codigo 2. Nunca `raise`."""
    for mensagem in mensagens:
        log.error("%s", mensagem)
    return SAIDA_RECUSADA


def laco_do_mercado(
    args,
    cal,
    *,
    fonte=None,
    ler_texto=None,
    ler_texto_conferencia=None,
    relogio=None,
    pasta=None,
    ticks_maximos=None,
    watchlist=None,
    receitas=None,
):
    """Le o World Exchange ate o usuario mandar parar. Devolve o codigo de saida.

    OS PARAMETROS NOMEADOS SAO INJECAO DE DEPENDENCIA, e producao nao passa
    nenhum. O precedente ja escrito e `montar_relogio(args, fonte=None)` e
    `Catalogo(pasta)`: e o que permite a suite rodar no Python GLOBAL, que nao
    tem as bindings WinRT, sobre fixturas versionadas, sem tocar a `.mercado/` do
    usuario e sem encostar na rede.

    `ticks_maximos=None` significa laco infinito, que e o caso de producao.
    """
    principal = _modulo_do_arranque()
    _garantir_log(principal)

    # ------------------------------------------------------------------
    # 1. OS PORTOES DE ARRANQUE. Recusam a SUBIR, nunca sobem degradado.
    # ------------------------------------------------------------------

    # O portao do OCR pergunta pelo motor SO quando ninguem injetou leitora.
    # Injetar leitora E ter OCR: e a mesma disciplina de `LeitorDePagina`, que
    # recebe duas maneiras INDEPENDENTES de ler o mesmo recorte e nao sabe de
    # onde elas vem. Producao nunca injeta, entao producao sempre pergunta.
    if ler_texto is None or ler_texto_conferencia is None:
        if not ocr.disponivel():
            return _recusar(
                [
                    "MODO MERCADO NAO VAI SUBIR: o motor de OCR nao respondeu "
                    "neste interpretador.",
                    str(ocr.motivo_indisponivel()),
                    "Rode pelo vigiar-mercado.bat — ele usa o .venv e "
                    "reinstala sozinho. Sem OCR nao ha nome de item, e sem "
                    "nome nao ha serie.",
                ]
            )
        ler_texto = ocr.ler_texto
        ler_texto_conferencia = ocr.ler_texto_ampliado

    faltando = pecas_de_calibracao_de_mercado_faltando(cal)
    if faltando:
        return _recusar(
            [
                "MODO MERCADO NAO VAI SUBIR: falta no calibration.json: "
                + ", ".join(faltando),
                "Rode calibrar-mercado.bat sobre um frame da GRADE DE "
                "NEGOCIACAO do World Exchange.",
                "Subir cego seria pior que nao subir: voce acharia que esta "
                "coletando e sairia do farm sem uma linha gravada.",
            ]
        )

    layout = (cal.mercado_grade or {}).get("layout")
    if layout != "negociacao":
        return _recusar(
            [
                "MODO MERCADO NAO VAI SUBIR: mercado_grade.layout esta gravado "
                "como '" + str(layout) + "', e o v1 le SOMENTE a grade de "
                "negociacao.",
                "Recalibre com calibrar-mercado.bat sobre a aba de negociacao.",
            ]
        )

    # ------------------------------------------------------------------
    # 2. A LINHA DE ARRANQUE QUE CONTA O ORCAMENTO.
    #    Precedente literal de `montar_vigia_do_mercado`: quem le o log
    #    precisa saber o que o recurso custa ANTES de o farm comecar.
    # ------------------------------------------------------------------
    log.info(
        "Modo MERCADO ativo - leitura do World Exchange a cada %.1fs. "
        "Pior tick medido no censo: ~110 ms de 1000. Este e o TERCEIRO "
        "processo: a party NAO le este modo e este modo NAO le a party, e "
        "nenhum alerta sai daqui.",
        float(args.intervalo),
    )

    # ------------------------------------------------------------------
    # 3. A FIACAO. Os dois destinos de escrita ANTES da captura: descobrir
    #    que a pasta nao abre depois de a janela estar de pe custaria uma
    #    sessao WGC por nada.
    # ------------------------------------------------------------------
    registro = principal.montar_registro_de_mercado(pasta)
    if registro is None:
        return _recusar(
            [
                "MODO MERCADO NAO VAI SUBIR: o registro de observacoes nao "
                "montou, e aqui ele NAO e opcional - ele e o produto.",
                "As duas linhas acima dizem o que quebrou e o que continua "
                "funcionando.",
            ]
        )

    catalogo = principal.montar_catalogo_de_mercado(pasta)
    if catalogo is None:
        return _recusar(
            [
                "MODO MERCADO NAO VAI SUBIR: o catalogo de nomes nao montou, e "
                "sem ele a serie do item nao tem onde nascer.",
                "As duas linhas acima dizem o que quebrou e o que continua "
                "funcionando.",
            ]
        )

    # A CARGA DO MODELO E UNICA, E ACONTECE AQUI, NO ARRANQUE.
    #
    # NAO RELEIA O CSV A 1 Hz. Duas razoes, e a segunda e a grave: releitura por
    # tick seria trabalho puro sobre milhares de linhas, e abriria CORRIDA com o
    # usuario editando o arquivo no Sheets no meio da sessao - o `.mercado/` e
    # feito para ele abrir. O contrato do arquivo ja e "lido no arranque"
    # (`RegistroDeObservacoes.carregar` monta o indice de dedup uma vez, e so);
    # a analise segue o MESMO contrato, e a partir daqui a historia cresce por
    # `acrescentar`, uma observacao aceita de cada vez.
    #
    # A CHAMADA E PELO MODULO (`mercado_registro.observacoes_do_arquivo`) e nao
    # por um nome importado: e o que permite ao teste envolver a funcao num
    # contador e AFIRMAR "uma vez", em vez de confiar na leitura do fonte.
    try:
        modelo = ModeloDeMercado.de_observacoes(
            mercado_registro.observacoes_do_arquivo(registro.arquivo)
        )
    except (mercado_registro.ContratoDoArquivoQuebrado, OSError) as erro:
        # DEGRADA A ANALISE, E NAO O MODO. Aqui, ao contrario dos portoes de
        # arranque acima, a montagem que falha degrada - e a assimetria e
        # deliberada. O produto do modo e COLETAR; a analise e uma LEITURA do
        # que ja foi coletado, e recusar a subir por causa dela desligaria a
        # coleta por causa da vista. As duas mensagens seguem o padrao da casa:
        # o que quebrou, e o que continua funcionando.
        log.error("Nao consegui ler o historico para a analise: %s", erro)
        log.error(
            "A COLETA CONTINUA NORMAL - o modo segue gravando em %s. O que "
            "fica de fora e so a secao de analise do console.",
            registro.arquivo,
        )
        modelo = ModeloDeMercado.de_observacoes([])

    # AS DUAS LEITURAS ABAIXO OLHAM O `config.local.toml` ANTES do `config.toml`,
    # pela precedencia que `ler_membros` ja estabeleceu. O usuario TEM o arquivo
    # local, e uma watchlist ou uma receita escrita la era ignorada em silencio.
    #
    # A WATCHLIST E FILTRO DE DESTAQUE, E NAO O PRODUTO - e por isso um
    # config quebrado NAO derruba a coleta. `ler_watchlist_do_mercado`
    # LEVANTA de proposito para TOML invalido e para tipo errado (T-04-11),
    # porque do lado de quem edita o arquivo a recusa alta e o certo; aqui,
    # deixar esse `raise` escapar mataria o modo `--mercado` inteiro por causa
    # de uma virgula, e o que o usuario perderia seria a COLETA da noite.
    if watchlist is None:
        try:
            watchlist = ler_watchlist_do_mercado()
        except AgendaInvalida as erro:
            log.error("A watchlist do mercado nao foi lida: %s", erro)
            log.error(
                "A COLETA CONTINUA NORMAL - a watchlist so promove series no "
                "console, e sem ela o topo sai por evidencia."
            )
            watchlist = []

    # AS RECEITAS SAO LIDAS UMA VEZ, NO ARRANQUE, JUNTO DA WATCHLIST — e nao a
    # cada repintar: reler o `config.toml` por secao abriria corrida com o
    # usuario editando o arquivo no meio da sessao, exatamente como reler o
    # CSV a 1 Hz abriria com o Sheets.
    #
    # E AQUI ELA **RECUSA O ARRANQUE**, AO CONTRARIO DA WATCHLIST LOGO ACIMA.
    # A assimetria e deliberada e tem uma razao so: a watchlist apenas PROMOVE
    # series no console, entao um erro nela nao pode custar a coleta da noite;
    # a receita e uma CONTA, e uma conta torta que degradasse para "sem margem"
    # sairia calada. O usuario descomentaria um bloco, nao veria margem nenhuma
    # e nao teria uma linha em lugar nenhum dizendo por que.
    #
    # E RECUSAR AQUI NAO CUSTA COLETA: nenhum frame foi capturado ainda. Uma
    # receita torta para o programa enquanto o usuario olha para o console, que
    # e o unico momento em que ele pode conserta-la.
    if receitas is None:
        try:
            receitas = ler_receitas()
        except ReceitaInvalida as erro:
            return _recusar(
                [
                    # O NOME DO ARQUIVO SAI DO `str(erro)` LOGO ABAIXO, e nao
                    # daqui: a receita pode vir do `config.toml` OU do
                    # `config.local.toml`, e cravar um dos dois nesta linha
                    # mandaria metade dos usuarios editar o arquivo errado.
                    "MODO MERCADO NAO VAI SUBIR: um bloco [[receita]] nao "
                    "serve.",
                    str(erro),
                    "A margem de craft e uma conta: uma receita torta daria "
                    "um numero perfeitamente formatado e completamente falso. "
                    "Conserte o bloco, ou comente-o para o modo subir sem "
                    "margem nenhuma.",
                ]
            )

    if relogio is None:
        relogio = principal.montar_relogio(args)

    carimbo = cal.mercado_geometria_da_captura or {}
    if fonte is None:
        from .captura_janela import JanelaSource

        # A JANELA INTEIRA, e nao o retangulo da ancora: o painel ANDA (827x831
        # px nas gravacoes de campo), e um recorte fixo mediria grama na maior
        # parte dos frames. `relativa=True` porque a origem e o canto da JANELA,
        # entao arrastar o jogo nao quebra nada.
        fonte = JanelaSource(
            args.janela,
            Regiao(
                esquerda=0,
                topo=0,
                largura=int(carimbo["largura"]),
                altura=int(carimbo["altura"]),
            ),
            relativa=True,
            minimum_update_interval=MS_ENTRE_FRAMES_DO_MERCADO,
        )

    leitor = LeitorDePagina(
        RastreioDoPainel(
            ancoras_de_calibracao(cal.mercado_ancoras),
            float(cal.mercado_limiar_da_ancora),
        ),
        # O SNAPSHOT do catalogo, e nao o `Catalogo`: `entradas()` devolve um
        # dicionario DESCONECTADO, e e por isso que a serie so entra no arquivo
        # pelo `catalogo.registrar` do tick, depois de a pagina ser aceita.
        catalogo.entradas(),
        ler_texto,
        ler_texto_conferencia,
        cal,
    )

    contagem = Contagem()
    motivos = Counter()
    orcamento = OrcamentoDoTick(limite=float(args.intervalo))
    ultimo_item = None
    paginas_desde_a_gravacao = 0
    erros_seguidos = 0
    ticks = 0
    saida = 0
    # O LATCH do painel, no precedente de `_layout_ja_recusado`. `None` e
    # "ainda nao sei", e a primeira volta ja e transicao: o usuario precisa ver
    # que o modo esta vivo e nao esta achando nada, o que e diferente de
    # silencio.
    painel_aberto_antes = None
    ticks_com_painel_antes = leitor.ticks_com_painel_aberto

    def desenhar_a_analise() -> None:
        """A secao "vale quanto agora", com o carimbo e a confianca do RELOGIO.

        `relogio.confiavel` viaja junto de proposito: sem ancora a hora e a crua
        do Windows, e num dual boot ela pode estar horas errada. Um carimbo
        exibido sem esse aviso seria um numero preciso e errado.
        """
        agora = relogio.agora()
        log.info(
            "\n%s",
            secao_do_vale_quanto(
                modelo,
                watchlist,
                agora,
                relogio_confiavel=relogio.confiavel,
            ),
        )
        # A MARGEM SAI NA MESMA CADENCIA, E NAO NUMA PROPRIA. Ela responde a
        # mesma pergunta que a secao acima — "vale quanto?" — so que sobre uma
        # receita, e as duas so mudam quando uma serie ganha observacao nova.
        # Um segundo temporizador aqui seria um segundo relogio para
        # envelhecer em desacordo com o primeiro.
        #
        # `agora` E O MESMO CARIMBO DAS DUAS: pedir a hora duas vezes faria as
        # duas secoes do MESMO repintar dizerem horarios diferentes.
        #
        # SEM RECEITA `secao_da_margem` DEVOLVE VAZIO, e a guarda esta AQUI
        # para nao emitir uma linha de log em branco a cada minuto.
        margem = secao_da_margem(receitas, modelo, agora)
        if margem:
            log.info("\n%s", margem)

    # ELA SAI JA NO ARRANQUE, ANTES DO PRIMEIRO TICK: o usuario abre o programa
    # para perguntar "vale quanto agora?", e a resposta ja existe no disco da
    # sessao passada. Esperar o primeiro tick faria um modo com meses de
    # historico gravado parecer vazio no segundo em que ele abre.
    desenhar_a_analise()
    # E DEPOIS POR INTERVALO, NUNCA POR TICK. A `linha_ao_vivo` e a que responde
    # "o modo esta vivo?" e repinta a 1 Hz com o painel aberto; esta responde
    # "vale quanto?", e a
    # resposta so muda quando uma serie ganha observacao nova. O precedente e
    # `desenhar_status` do laco principal, que tambem sai por intervalo.
    proxima_secao = time.monotonic() + SEGUNDOS_ENTRE_SECOES

    # ------------------------------------------------------------------
    # 4. O TICK.
    # ------------------------------------------------------------------
    try:
        while ticks_maximos is None or ticks < ticks_maximos:
            ticks += 1
            inicio = time.monotonic()

            try:
                frame = fonte.capturar()
            except StopIteration:
                log.info("A fonte de frames acabou - encerrando.")
                break
            except Exception:
                erros_seguidos += 1
                log.exception("Erro na captura (seguidos: %d)", erros_seguidos)
                if erros_seguidos >= ERROS_SEGUIDOS_PARA_DESISTIR:
                    log.error(
                        "%d erros seguidos - encerrando para nao rodar cego.",
                        ERROS_SEGUIDOS_PARA_DESISTIR,
                    )
                    saida = SAIDA_CEGA
                    break
                time.sleep(max(0.0, float(args.intervalo)))
                continue

            erros_seguidos = 0
            pagina = leitor.observar(frame.pixels)

            # O ESTADO DO PAINEL SEM ESPIAR O LEITOR POR DENTRO: ele so
            # incrementa `ticks_com_painel_aberto` quando o voto deu aberto,
            # entao a diferenca entre duas voltas E a resposta. Perguntar por um
            # atributo privado acoplaria este laco ao que o leitor existe para
            # nao expor.
            aberto_agora = leitor.ticks_com_painel_aberto > ticks_com_painel_antes
            ticks_com_painel_antes = leitor.ticks_com_painel_aberto
            if aberto_agora != painel_aberto_antes:
                log.info("%s", transicao_do_painel(aberto_agora))
                painel_aberto_antes = aberto_agora

            # OS MOTIVOS SAO SOMADOS TODO TICK, e nao so quando a pagina e
            # aceita: a leitura recusada e justamente a que carrega o motivo, e
            # ler so as aceitas esconderia a metade perdida do LEIT-04.
            acumular_motivos(motivos, leitor.ultima_leitura)

            if pagina is not None:
                agora = relogio.agora()
                for linha in pagina.linhas:
                    contagem.series.add(linha.chave_da_serie)

                    # ---------------------------------------------------------
                    # PASSO 1 - O DESTAQUE, CONTRA O MODELO COMO ELE ESTA.
                    #
                    # ESTA CHAMADA VEM ANTES DE QUALQUER ESCRITA, E A ORDEM E O
                    # CORACAO DO ANAL-02. Se as linhas deste tick ja tiverem
                    # entrado no modelo, o item se compara CONSIGO MESMO: uma
                    # oferta muito barata puxa a propria mediana para baixo, o
                    # veredito encolhe, e o destaque vira ruido - exatamente a
                    # informacao que o requisito existe para dar.
                    #
                    # E o tipo de ordem que um refactor futuro desfaz sem
                    # perceber ("por que julgar antes de gravar?"), e por isso a
                    # razao esta escrita aqui e nao so no teste.
                    # ---------------------------------------------------------
                    destaque = modelo.veredito_do_destaque(linha)
                    if destaque.abaixo:
                        # SO O `abaixo` SAI NO LOG. "Acima da mediana" e o caso
                        # comum e imprimi-lo afogaria o unico que o usuario quer
                        # ver; "sem destaque" nao e um fato sobre o preco, e sim
                        # sobre a evidencia, e ele ja aparece na secao de
                        # analise com o que FALTA escrito por extenso.
                        log.info(
                            "%s",
                            destaque_ao_vivo(
                                linha.nome_exibido, destaque, agora
                            ),
                        )

                    # PASSO 2 - O CATALOGO. A ordem contra o registro nao e
                    # arbitraria: a Fase 3 LE a chave que a Fase 2 produziu, e
                    # uma observacao gravada sobre uma chave que nao esta no
                    # catalogo e uma linha do CSV que ninguem consegue nomear
                    # depois.
                    catalogo.registrar(
                        linha.chave_da_serie, linha.nome_exibido, agora
                    )

                    # PASSO 3 - O REGISTRO, e PASSO 4 - o modelo, SO quando o
                    # passo 3 devolveu `True`. `registrar` devolve `False` para
                    # duplicada E para registro desligado; acrescentar fora
                    # desse portao faria a mesma oferta contar duas vezes no
                    # `n`, e o `n` e o numero que esta fase existe para nao
                    # mentir.
                    if registro.registrar(linha, agora):
                        contagem.observacoes += 1
                        # A observacao montada AQUI e campo a campo a mesma que
                        # `campos_da_observacao` acabou de escrever no CSV, com
                        # o MESMO `agora`: a historia em memoria e o arquivo
                        # concordam por construcao, e nao por coincidencia.
                        modelo.acrescentar(
                            mercado_registro.ObservacaoLida(
                                chave_da_serie=linha.chave_da_serie,
                                nome_exibido=linha.nome_exibido,
                                primeira_vez=agora,
                                total_em_centesimos=linha.total_em_centesimos,
                                quantidade=linha.quantidade,
                                residuo_do_cruzamento=(
                                    linha.residuo_do_cruzamento
                                ),
                            )
                        )
                    elif registro.ligado:
                        contagem.duplicadas += 1
                    else:
                        contagem.perdidas += 1
                    ultimo_item = linha.nome_exibido

                paginas_desde_a_gravacao += 1
                if (
                    paginas_desde_a_gravacao
                    >= PAGINAS_ENTRE_GRAVACOES_DO_CATALOGO
                ):
                    catalogo.gravar()
                    paginas_desde_a_gravacao = 0

            # A LINHA AO VIVO SAI POR TICK COM O PAINEL ABERTO, E NAO POR
            # PAGINA ACEITA - e a diferenca entre as duas e o requisito.
            #
            # Emitida de dentro do `if pagina is not None`, ela calava o console
            # exatamente no tick em que a metade PERDIDA cresce, que e a metade
            # que o LEIT-04 existe para nao deixar esconder: no censo foram 151
            # lidas contra 189 perdidas. Quem estivesse olhando veria a linha
            # congelar e nao teria como distinguir "o painel fechou", "a captura
            # travou" e "as ultimas dez leituras foram todas recusadas" - tres
            # coisas com respostas diferentes.
            #
            # ELA FICA DEPOIS DO BLOCO DA PAGINA, e nao antes: `contagem` e
            # `ultimo_item` tem de ser os DESTE tick. Antes, a linha mostraria
            # sempre o estado do tick anterior.
            #
            # O PORTAO E O PAINEL ABERTO, e nao "todo tick". Painel fechado e o
            # estado normal e majoritario de um farm real, e uma linha por tick
            # ali seriam 3.600 por hora afogando a forense do log rotativo -
            # mesmo raciocinio do latch de `transicao_do_painel`. Com o painel
            # fechado quem responde "o modo esta vivo?" e a linha de transicao,
            # que ja saiu.
            if aberto_agora:
                log.info("%s", linha_ao_vivo(leitor, contagem, ultimo_item))

            if time.monotonic() >= proxima_secao:
                desenhar_a_analise()
                proxima_secao = time.monotonic() + SEGUNDOS_ENTRE_SECOES

            # A MESMA CONTA SERVE A DUAS COISAS: compensar a deriva da cadencia
            # e alimentar o orcamento auto-medido. Medir por fora seria um
            # segundo relogio para envelhecer em desacordo com o primeiro.
            trabalhado = time.monotonic() - inicio
            orcamento.registrar(trabalhado)

            # A CADENCIA COMPENSADA, e nunca `time.sleep(args.intervalo)` puro:
            # com ~110 ms de trabalho o tick viraria 1,11 s e o console mentiria
            # sobre a propria cadencia. Copiada de `__main__.laco_principal`.
            dormir = float(args.intervalo) - trabalhado
            if dormir > 0:
                time.sleep(dormir)

    except KeyboardInterrupt:
        log.info("Encerrado pelo usuario")

    finally:
        fonte.fechar()
        # A GRAVACAO ATOMICA DO CATALOGO SO AQUI (e a cada 20 paginas): ela
        # reescreve o arquivo INTEIRO, entao por tick seria trabalho puro.
        catalogo.gravar()
        log.info(
            "\n%s", resumo_da_sessao(leitor, contagem, motivos, orcamento)
        )
        log.info("Arquivos: %s e %s", registro.arquivo, catalogo.arquivo)

    return saida
