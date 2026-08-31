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
from dataclasses import dataclass, field

from . import ocr
from .frames import Regiao
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
                    "Rode pelo .venv (vigiar-party.bat ja faz isso). Sem OCR "
                    "nao ha nome de item, e sem nome nao ha serie.",
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
    ultimo_item = None
    paginas_desde_a_gravacao = 0
    erros_seguidos = 0
    ticks = 0
    saida = 0

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

            if pagina is not None:
                agora = relogio.agora()
                for linha in pagina.linhas:
                    contagem.series.add(linha.chave_da_serie)
                    # O CATALOGO PRIMEIRO, e a ordem nao e arbitraria: a Fase 3
                    # LE a chave que a Fase 2 produziu, e uma observacao gravada
                    # sobre uma chave que nao esta no catalogo e uma linha do CSV
                    # que ninguem consegue nomear depois.
                    catalogo.registrar(
                        linha.chave_da_serie, linha.nome_exibido, agora
                    )
                    if registro.registrar(linha, agora):
                        contagem.observacoes += 1
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

                log.info(
                    "paginas lidas %d | perdidas %d | ultimo item: %s",
                    leitor.paginas_lidas,
                    leitor.paginas_perdidas,
                    ultimo_item or "(nenhum)",
                )

            # A CADENCIA COMPENSADA, e nunca `time.sleep(args.intervalo)` puro:
            # com ~110 ms de trabalho o tick viraria 1,11 s e o console mentiria
            # sobre a propria cadencia. Copiada de `__main__.laco_principal`.
            dormir = float(args.intervalo) - (time.monotonic() - inicio)
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
            "Resumo: %d paginas lidas, %d perdidas (%d ticks com o painel "
            "aberto).",
            leitor.paginas_lidas,
            leitor.paginas_perdidas,
            leitor.ticks_com_painel_aberto,
        )
        log.info(
            "Gravei %d observacoes novas, descartei %d ja conhecidas, perdi "
            "%d por registro desligado. %d series distintas nesta sessao.",
            contagem.observacoes,
            contagem.duplicadas,
            contagem.perdidas,
            len(contagem.series),
        )
        log.info("Arquivos: %s e %s", registro.arquivo, catalogo.arquivo)

    return saida
