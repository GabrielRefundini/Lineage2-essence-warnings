"""O laco de producao do modo `--renda` (CONS-01, CONS-02): a QUARTA invocacao.

O QUE ESTE MODULO E
====================
Ele e o CHAMADOR que faltava, na mesma situacao literal de `mercado_modo.py`,
cuja propria docstring usa essa frase. A Fase 1 entregou `ler_os_tres_campos`;
a Fase 2 entregou `passo_entre_campos`, `ContagemDaRenda`, `as_duas_taxas` e
`RegistroDaRenda` — **todos sem chamador de producao, de proposito**. Aqui os
fios ganham um processo que os liga: captura a janela, le os tres campos, conta
o passo, grava UMA linha por tique em `.renda/<apelido>.csv` e diz na tela o
que viu.

**O produto desta fase, do ponto de vista do usuario, e `.renda/` deixando de
estar vazio.**

O QUE ELE NAO E, E AS TRES SAO A TENTACAO
==========================================
1. **Nao usa `rich`.** Ele nao esta instalado, tem zero importacoes em
   `l2scanner/` e nao entra nesta fase (CTX-1).

2. **Nao repinta a tela.** Nao ha `\\r`, nao ha clear e nao ha `print`: o laco
   faz `log.info` e a linha ROLA (C-1). "Ao vivo" nesta casa e uma linha NOVA
   por tique.

3. **Nao usa `capturar_completo()` no tique.** `renda_modo._frame_de_janela` e
   o precedente mais obvio e o ERRADO para um laco (C-5): ele pula a
   classificacao de saude inteira, e sem `SaudeDoFrame` nao ha como distinguir
   FALHA de CONGELADO — o que torna CEGO-01 e CEGO-02 estruturalmente
   impossiveis no `03-02`. Aqui `capturar_completo()` aparece UMA vez, no
   arranque, so para MEDIR a janela; dali em diante e `capturar()`.

A FRONTEIRA DE CHAMADA (LEIT-11, C-8)
======================================
Este modulo chama `renda_conta.passo_entre_campos` e **nunca**
`conferir_o_par`, `o_exp_andou_para_tras`, `o_nivel_andou_para_tras` ou
`a_adena_saltou_ordem_de_grandeza`. O portao de `tests/test_renda_par.py:704`
afirma que o conjunto de chamadores das regras de par e EXATAMENTE
`{renda_conta.py}`, e um segundo chamador seria uma segunda politica de recusa
divergindo no dia em que uma delas mudar. A conta e de la.

OS CODIGOS DE SAIDA, E A TABELA MORA AQUI PORQUE UM CODIGO SEM TABELA E UM
NUMERO QUE SO O AUTOR ENTENDE
==========================================================================

    0   a sessao fechou (fonte acabou, `Ctrl+C`, `ticks_maximos`)
    1   rodou cego: dez erros seguidos de captura
    2   recusa de configuracao: sem personagem no titulo, sem calibracao de
        renda para ele, `[renda]` torto, ou a pasta de destino nao abre

**O laco DEVOLVE o codigo e nunca levanta.**
"""

from __future__ import annotations

import logging
import sys
import time

from .cliente import nome_do_personagem
from .config import AgendaInvalida, ler_ajustes_da_renda
from .frames import Regiao
from .mercado_console import OrcamentoDoTick
from .renda_conta import (
    ContagemDaRenda,
    contar_o_passo,
    passo_entre_campos,
)
from .renda_console import linha_do_tique, resumo_da_sessao_da_renda
from .renda_registro import ORIGEM_INDETERMINADA

log = logging.getLogger("l2scanner")


# O codigo de recusa de configuracao do projeto. `__main__.main` ja devolve 2
# para `CalibracaoInvalida` e para janela ambigua, e `mercado_modo` usa o mesmo
# numero: os portoes daqui sao a mesma familia de recusa.
SAIDA_RECUSADA = 2

# O desfecho de "rodei cego", copiado do laco principal e do do mercado.
SAIDA_CEGA = 1

# Quantos erros seguidos de captura ate desistir, copiado de
# `__main__.laco_principal` e de `mercado_modo`: a captura falha PARCIALMENTE
# (a WGC perde a janela, o usuario fecha o jogo), e um laco que insistisse para
# sempre gastaria a noite escrevendo traceback.
ERROS_SEGUIDOS_PARA_DESISTIR = 10

# O intervalo MINIMO, em milissegundos, entre frames que a WGC entrega a ESTE
# modo. E a alavanca de "o modo renda nao degrada os modos de party":
# `JanelaSource` mantem o padrao `None` e o caminho da party continua
# byte-identico.
#
# 250 E ESCOLHA, E NAO MEDICAO — um numero que nao foi medido precisa dizer que
# nao foi. Ele e copiado de `MS_ENTRE_FRAMES_DO_MERCADO`
# (`mercado_modo.py:128`), cuja justificativa inteira vale igual aqui: a WGC
# entrega ~38 fps (medido) e este modo consome 1 por segundo, entao limitar a
# entrega corta a copia jogada fora sem mudar nada para quem le a 1 Hz.
#
# POR QUE NAO 1000, que seria "a cadencia do laco". Com atualizacao a cada
# ~1000 ms e leitura a cada ~1000 ms, a deriva de fase entrega o MESMO buffer
# varias vezes seguidas, `FRAMES_IDENTICOS_PARA_CONGELADO` dispara e o console
# anuncia captura congelada com o jogo vivo na tela. 250 deixa quatro entregas
# por leitura, que e a margem que impede o falso positivo — e o falso
# congelamento e exatamente o que o `03-02` vai existir para nomear de verdade.
MS_ENTRE_FRAMES_DA_RENDA = 250

# A regiao UNITARIA do arranque. `JanelaSource` exige uma regiao no construtor,
# mas o que interessa neste ponto e `capturar_completo()`, que devolve a JANELA
# INTEIRA e nao o recorte. `relativa=True` porque a origem e o canto da janela:
# arrastar o jogo nao quebra nada, e e o unico modo em que `apontar_para` e
# legal (`captura_janela.py:336-361` levanta `ValueError` quando nao e).
REGIAO_PARA_MEDIR_A_JANELA = Regiao(esquerda=0, topo=0, largura=1, altura=1)

SUBCHAVE_DA_GEOMETRIA = "geometria_da_janela"


def _modulo_do_arranque():
    """As montadoras da casa, SEM re-executar `l2scanner/__main__.py`.

    Copiado literal de `mercado_modo._modulo_do_arranque`, com a razao inteira:
    rodando por `python -m l2scanner`, aquele arquivo ja esta em `sys.modules`
    sob o nome `__main__`, e um `from .__main__ import ...` o importaria DE NOVO
    sob outro nome, executando o arquivo inteiro uma segunda vez — e o `log` da
    copia teria outro logger, sem nenhum dos manipuladores que `configurar_log`
    acabou de instalar. As mensagens de recusa que o usuario PRECISA ver
    sumiriam exatamente no caso em que elas importam.

    A pergunta e por CAPACIDADE e nao por nome de arquivo, porque nome de
    arquivo e o que muda entre os dois casos.
    """
    principal = sys.modules.get("__main__")
    if hasattr(principal, "montar_registro_da_renda"):
        return principal
    from l2scanner import __main__ as principal

    return principal


def _garantir_log(principal) -> None:
    """Nenhuma mensagem deste modo pode sair sem manipulador.

    A CHAMADA E CONDICIONAL, e e o mesmo cuidado de `mercado_modo`: por
    `python -m l2scanner` o `main()` JA chamou `configurar_log`, e chamar de
    novo acrescentaria um segundo `RotatingFileHandler` e um segundo
    `StreamHandler` — toda linha da sessao sairia DUAS vezes. A guarda pergunta
    se ja ha para onde a mensagem ir; na raiz e onde o `caplog` do pytest
    instala o dele, e e o que faz o teste de laco ver o console.
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


def _avisar_se_a_janela_mudou_de_tamanho(entrada, largura, altura) -> None:
    """A geometria GRAVADA e GUARDA, e nunca fonte.

    A CHAVE E OPCIONAL NO ESQUEMA. `calibracao.py:1541-1543` faz
    `entrada.get("geometria_da_janela")` e so valida `if geometria is not
    None`; `:1550` valida `largura` e `altura` uma a uma, com `if campo in
    geometria`. Uma calibracao antiga, uma escrita por versao anterior do
    calibrador ou uma editada a mao pode legitimamente nao ter a chave — ou
    te-la pela metade — e `int(carimbo["largura"])` naquele caso seria um
    `KeyError` no arranque de producao, com o usuario vendo um traceback em vez
    de um scanner.

    E MESMO POPULADA ELA E O CARIMBO DA ULTIMA CALIBRACAO, e nao uma afirmacao
    sobre a janela de agora. Por isso a geometria vem de `frame.shape` da janela
    VIVA e a gravada so serve para discordar.

    ELA ESTA POPULADA NAS DUAS INSTANCIAS DO USUARIO — `{'largura': 1720,
    'altura': 1392}` para Faerlina e para Yazalaque, remedido no checkout
    PRINCIPAL em 2026-09-03 (a medicao anterior, que dizia `{}`, foi feita
    dentro de um WORKTREE, onde `calibration.json` e gitignored e a carga
    devolve defaults). Entao este aviso NAO e codigo morto: ele dispara no dia
    em que a janela mudar de tamanho, que e o caso medido do M-J — a janela
    subiu ~8 px e as tres regioes morreram de uma vez, com o usuario vendo os
    tres campos recusados e nenhuma pista do porque. E a causa numero um de "a
    leitura quebrou do nada", e o usuario nao tem como saber sozinho.
    """
    carimbo = (entrada or {}).get(SUBCHAVE_DA_GEOMETRIA) or {}
    if "largura" not in carimbo or "altura" not in carimbo:
        return
    if (int(carimbo["largura"]), int(carimbo["altura"])) == (largura, altura):
        return

    log.error(
        "A JANELA MUDOU DE TAMANHO desde a ultima calibracao deste "
        "personagem: calibrada em %dx%d e medida agora em %dx%d.",
        int(carimbo["largura"]),
        int(carimbo["altura"]),
        largura,
        altura,
    )
    log.error(
        "OS RETANGULOS ANTIGOS APONTAM PARA LUGARES DIFERENTES NESTA JANELA. "
        "Se os tres campos comecarem a recusar, e isto e nao o OCR: rode "
        "`calibrar-renda.bat` para este personagem com a janela no tamanho de "
        "agora."
    )


def _montar_a_fonte(titulo: str, entrada):
    """`JanelaSource` MEDIDA na janela viva, mirada, e pronta para `capturar()`.

    A ORDEM E A DE "A GEOMETRIA DA JANELA" DO PLANO, e cada passo tem razao:

    1. `Regiao(0,0,1,1)` + `relativa=True` — o molde de
       `renda_modo._frame_de_janela`, e **so essa metade dele**.
    2. `capturar_completo()` UMA vez, so para medir `frame.shape`. E a UNICA
       ocorrencia dela neste modulo.
    3. `apontar_para(Regiao(0, 0, largura, altura))` — legal porque a fonte e
       relativa, e e o espaco de coordenadas em que os retangulos da renda
       foram gravados (M-A).
    4. Dali para a frente, `capturar()` — que classifica `SaudeDoFrame` sobre o
       recorte, e e o que o `03-02` precisa existir.

    O IMPORT DE `captura_janela` MORA DENTRO DESTA FUNCAO, e e o que deixa a
    suite rodar no Python GLOBAL, sem as bindings WinRT — o mesmo cuidado de
    `mercado_modo.py:546-549`.

    Devolve `(fonte, None)` ou `(None, mensagem)`. Nunca levanta.
    """
    from .captura_janela import JanelaSource

    fonte = None
    try:
        fonte = JanelaSource(
            titulo,
            REGIAO_PARA_MEDIR_A_JANELA,
            relativa=True,
            minimum_update_interval=MS_ENTRE_FRAMES_DA_RENDA,
        )
        completo = fonte.capturar_completo()
    except Exception as erro:  # noqa: BLE001 - borda: vira recusa, nao traceback
        if fonte is not None:
            fonte.fechar()
        return None, f"nao consegui abrir a janela {titulo!r}: {erro}"

    if completo is None or completo.size == 0:
        fonte.fechar()
        return None, (
            f"nenhum frame utilizavel chegou da janela {titulo!r}. Ela esta "
            "minimizada? A captura por janela funciona com o jogo COBERTO por "
            "outra janela (medido), mas nao com ele minimizado."
        )

    altura, largura = int(completo.shape[0]), int(completo.shape[1])
    _avisar_se_a_janela_mudou_de_tamanho(entrada, largura, altura)
    fonte.apontar_para(
        Regiao(esquerda=0, topo=0, largura=largura, altura=altura)
    )
    return fonte, None


def laco_da_renda(
    args,
    cal,
    *,
    fonte=None,
    ler_campos=None,
    relogio=None,
    pasta=None,
    ticks_maximos=None,
):
    """Le a renda ate o usuario mandar parar. Devolve o codigo de saida.

    OS PARAMETROS NOMEADOS SAO INJECAO DE DEPENDENCIA, e producao nao passa
    nenhum. Sao CINCO alavancas e e o que permite a suite rodar no Python
    GLOBAL, que nao tem as bindings WinRT nem o motor de OCR, sem tocar a
    `.renda/` do usuario — que e dado acumulado e sem desfazer.

    `ler_campos=` E O SEAM QUE O MERCADO NAO TEM (Achado 9).
    `renda_leitura.py:66` faz `from .ocr import ler_texto, ler_texto_ampliado`
    — import de NOME no topo do modulo, chamado direto —, entao nao ha como
    injetar a leitora de OCR por construtor como o `LeitorDePagina` do mercado
    permite. A injecao sobe um nivel: entra a funcao de leitura INTEIRA, com a
    de producao como default. A alternativa seria monkeypatchar
    `l2scanner.renda_leitura.ler_texto`, que esta casa evita e que faria o
    teste de laco depender do formato interno de outro modulo.

    `ticks_maximos=None` significa laco infinito, que e o caso de producao.
    """
    principal = _modulo_do_arranque()
    _garantir_log(principal)

    # ------------------------------------------------------------------
    # 1. OS PORTOES DE ARRANQUE. Recusam a SUBIR, nunca sobem degradado.
    # ------------------------------------------------------------------

    # O NOME SAI DO TITULO DA JANELA e nunca de um `--personagem`, que seria a
    # segunda verdade sobre a mesma janela. E o que `renda_modo.py:330` ja faz.
    personagem = nome_do_personagem(args.janela)
    if not personagem:
        return _recusar(
            [
                "MODO RENDA NAO VAI SUBIR: nao consegui tirar o nome do "
                f"personagem do titulo {args.janela!r}.",
                "O titulo do cliente tem a forma `<Personagem> - XM Essence`, "
                "e e dele que sai de QUEM e a renda. Sem isso o scanner nao "
                "sabe em qual dos dois arquivos de `.renda/` escrever.",
            ]
        )

    # O PORTAO DA CALIBRACAO. `renda_do_personagem` NUNCA cai no vizinho, e a
    # recusa reusa a frase que `renda_leitura.py:1355-1364` ja escreveu: o
    # retangulo do vizinho devolve `349` ou `112` (M-F), numeros plausiveis que
    # passam por qualquer validacao sem reclamar.
    entrada = cal.renda_do_personagem(personagem)
    if entrada is None:
        conhecidos = sorted(getattr(cal, "renda_por_personagem", None) or {})
        return _recusar(
            [
                "MODO RENDA NAO VAI SUBIR: nao ha calibracao de renda para "
                f"{personagem!r} (calibrados: "
                f"{', '.join(conhecidos) if conhecidos else '(nenhum)'}).",
                "A leitura NAO cai na calibracao de outro personagem: o "
                "retangulo do vizinho devolve um numero plausivel e errado em "
                "vez de um campo vazio que alguem nota.",
                "Rode `calibrar-renda.bat` com a janela deste personagem "
                "aberta.",
            ]
        )

    # OS AJUSTES SAO LIDOS UMA VEZ, NO ARRANQUE. Reler o `config.toml` por
    # tique abriria corrida com o usuario editando o arquivo no meio da sessao
    # — a mesma razao escrita em `mercado_modo.py:522-524`.
    #
    # E UM `[renda]` TORTO RECUSA O ARRANQUE em vez de degradar para os
    # defaults: os cinco numeros sao uma CONTA, e uma conta torta que caisse no
    # padrao entregaria uma taxa perfeitamente formatada e diferente da que o
    # usuario pediu, sem uma linha em lugar nenhum dizendo por que.
    try:
        ajustes = ler_ajustes_da_renda()
    except AgendaInvalida as erro:
        return _recusar(
            [
                "MODO RENDA NAO VAI SUBIR: a secao [renda] do config.toml nao "
                "serve.",
                str(erro),
                "Os cinco numeros dali governam a conta inteira. Conserte a "
                "secao, ou comente-a para o modo subir com os padroes.",
            ]
        )

    # ------------------------------------------------------------------
    # 2. O DESTINO DE ESCRITA, ANTES DA CAPTURA. A razao esta em
    #    `mercado_modo.py:428-431` e vale inteira: descobrir que a pasta
    #    nao abre depois de a janela estar de pe custa uma sessao WGC por
    #    nada.
    # ------------------------------------------------------------------
    registro = principal.montar_registro_da_renda(pasta, personagem)
    if registro is None:
        return _recusar(
            [
                "MODO RENDA NAO VAI SUBIR: o registro da renda nao montou, e "
                "aqui ele NAO e opcional - ele e o produto.",
                "A linha acima diz o que quebrou. Todo o resto do scanner "
                "continua igual: morte, saida e ressurreicao seguem sendo "
                "detectadas e entregues pelos outros processos.",
            ]
        )

    log.info(
        "Modo RENDA ativo para %s - leitura a cada %.1fs, bloco a cada %.0fs, "
        "gravando em %s. Este e o QUARTO processo: ele NAO vigia a party, NAO "
        "le o mercado e nenhum alerta sai daqui.",
        personagem,
        float(args.intervalo),
        float(args.status_a_cada),
        registro.arquivo,
    )

    if relogio is None:
        relogio = principal.montar_relogio(args)

    if ler_campos is None:
        from .renda_leitura import ler_os_tres_campos as ler_campos

    if fonte is None:
        fonte, problema = _montar_a_fonte(args.janela, entrada)
        if fonte is None:
            return _recusar(
                [
                    f"MODO RENDA NAO VAI SUBIR: {problema}",
                    "A captura por janela e a unica que le o jogo coberto por "
                    "outra janela, e ela e o caminho desta fase.",
                ]
            )

    # ------------------------------------------------------------------
    # 3. O ESTADO ENTRE TIQUES, FORA DO `while`. Dentro dele, `contagem` e
    #    `passos` nasceriam vazios a cada volta e a taxa nunca teria `n`.
    # ------------------------------------------------------------------
    anterior = None
    carimbo_anterior = None
    passos = []
    contagem = ContagemDaRenda()
    orcamento = OrcamentoDoTick(limite=float(args.intervalo))
    # `registrar` devolve `bool` e nunca levanta; no primeiro `OSError` ele
    # desliga a gravacao para a sessao inteira. Somar as perdidas com as
    # aceitas apagaria a pergunta, pelo mesmo argumento de `Contagem` no
    # mercado: "descartei 300" sobre uma sessao em que o disco encheu na
    # terceira linha.
    perdidas = 0
    erros_seguidos = 0
    ticks = 0
    saida = 0

    # ------------------------------------------------------------------
    # 4. O TIQUE.
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

            campos = ler_campos(
                frame.pixels, personagem=personagem, calibracao=cal
            )
            # O CARIMBO VEM DO RELOGIO INJETADO e nunca de `datetime.now()`
            # dentro deste laco: e o que torna `relogio-andou-para-tras`
            # atingivel em teste e o que impede a taxa de depender da maquina.
            agora = relogio.agora_epoch()

            # A UNICA PORTA PARA A CONTA (C-8). As quatro regras de par NAO sao
            # chamadas daqui — a decisao sobre o par mora em `renda_conta`.
            passo = passo_entre_campos(
                anterior,
                campos,
                carimbo_anterior=carimbo_anterior,
                carimbo=agora,
                fator_de_salto=ajustes.fator_de_salto_da_adena,
                limiar_de_lacuna_em_segundos=ajustes.lacuna_maxima_segundos,
            )
            contar_o_passo(passo, contagem)

            # UMA LINHA POR TIQUE, SEMPRE, inclusive com campo recusado: ela e
            # o denominador da taxa. A fase NAO constroi um segundo portao de
            # admissao — com 79% de recusa no nivel, um portao aqui entregaria
            # linha em ~4% dos tiques.
            if not registro.registrar(
                campos,
                carimbo=agora,
                descontinuidade=passo.descontinuidade,
                origem_do_ganho=ORIGEM_INDETERMINADA,
            ):
                perdidas += 1

            passos.append(passo)
            anterior, carimbo_anterior = campos, agora

            # A LINHA SAI DEPOIS DO BLOCO DE PROCESSAMENTO: ela mostra o estado
            # DESTE tique, e nunca o do anterior.
            log.info("%s", linha_do_tique(campos, contagem))

            # A MESMA CONTA SERVE A DUAS COISAS: compensar a deriva da cadencia
            # e alimentar o orcamento auto-medido. Medir por fora seria um
            # segundo relogio para envelhecer em desacordo com o primeiro.
            trabalhado = time.monotonic() - inicio
            orcamento.registrar(trabalhado)

            # A CADENCIA COMPENSADA, e nunca `time.sleep(args.intervalo)` puro:
            # com ~110 ms de trabalho o tique viraria 1,11 s e o console
            # mentiria sobre a propria cadencia.
            dormir = float(args.intervalo) - trabalhado
            if dormir > 0:
                time.sleep(dormir)

    except KeyboardInterrupt:
        log.info("Encerrado pelo usuario")

    finally:
        fonte.fechar()
        # O RESUMO SAI SEMPRE, inclusive numa sessao de zero linhas: o
        # `vigiar-renda.bat` do `03-04` nao tem bloco de encerramento nenhum.
        log.info(
            "\n%s", resumo_da_sessao_da_renda(contagem, orcamento, registro)
        )
        if perdidas:
            log.error(
                "%d linha(s) NAO foram gravadas: o registro desligou no "
                "primeiro erro de disco e nao tenta de novo na sessao.",
                perdidas,
            )

    return saida
