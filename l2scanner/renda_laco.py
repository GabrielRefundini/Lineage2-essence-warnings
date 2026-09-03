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

from . import renda_console
from .cliente import nome_do_personagem
from .config import AgendaInvalida, ler_ajustes_da_renda
from .frames import Regiao
from .mercado_console import OrcamentoDoTick
from .renda_conta import (
    GRANDEZA_DA_ADENA,
    GRANDEZA_DO_EXP,
    ContagemDaRenda,
    TempoAteONivel,
    as_duas_taxas,
    contar_o_passo,
    passo_entre_campos,
    tempo_ate_o_nivel,
)
from .recaptura import FonteRecuperavel
from .renda_console import (
    RECORTE_DO_EXP_SEM_LEITURA,
    aviso_da_transicao,
    linha_do_tique,
    resumo_da_sessao_da_renda,
)
from .renda_estado import (
    MOTIVO_DO_EXP_SEM_LEITURA,
    EstadoDaRenda,
    RastreioDoValor,
    classificar_a_visao,
)
from .renda_leitura import RecusaDaRenda
from .renda_registro import ORIGEM_INDETERMINADA

log = logging.getLogger("l2scanner")

# `janela_movel_minutos` chega em MINUTOS do `config.toml` e `as_duas_taxas`
# pede SEGUNDOS. A conversao mora aqui, na casca, exatamente como a docstring
# daquela funcao manda: *"convertido a segundos por quem le o arquivo"*.
SEGUNDOS_POR_MINUTO = 60


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

# QUANTO TEMPO DE EXP BIT-IDENTICO ATE O PAINEL DIZER `PARADO`.
#
# ELE MORA AQUI E NAO NA SECAO `[renda]` DO `config.toml` (C-4). O detector
# IRMAO, `FRAMES_IDENTICOS_PARA_CONGELADO = 30`, e constante nomeada em
# `frames.py` com a razao escrita ao lado -- porque e uma propriedade DO
# DETECTOR e nao um numero de farm que o usuario ajusta. A staleness de valor e
# o mesmo tipo de numero. O modulo puro o recebe somente-nomeado e SEM valor de
# fabrica; quem escolhe e este arquivo.
#
# 120 E ESCOLHA E NAO MEDICAO -- um numero que nao foi medido precisa dizer que
# nao foi, a mesma disciplina de `MS_ENTRE_FRAMES_DA_RENDA` logo acima. O que
# ESTA medido e o que o sustenta: o degrau de UM abate mede 10 unidades de EXP
# (censo de 55 Hz, `renda_ponte.py:33-35`) e um farm ativo mata ~104 mobs por
# minuto. Dois minutos sem UMA unidade de EXP nao sao cadencia: sao ninguem
# matando nada.
#
# E ELE E TEMPO E NAO NUMERO DE AMOSTRAS, pela CTX-1 da Fase 2: com
# `--intervalo` mudavel, `N=120` sao dois minutos a 1 Hz e dez a 5 Hz. A tela
# mostra OS DOIS -- `PARADO ha 4min n=247` --, o que cumpre a letra do CEGO-02
# ("bit-identicos por N amostras") sem herdar o defeito de contar amostras.
#
# *Alternativa registrada:* acrescentar `segundos_para_parado` a `[renda]`.
# Custa a constante, o campo do dataclass, o `_inteiro_da_renda`, o
# `_EXEMPLO_DA_RENDA`, o `config.toml` comentado e o teste -- seis lugares --
# por um numero que ninguem pediu para ajustar. O modulo puro ja esta pronto
# para receber outro valor no dia em que alguem pedir.
SEGUNDOS_PARA_DECLARAR_PARADO = 120.0


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


def _a_janela_esta_minimizada(fonte) -> bool:
    """`IsIconic` na fonte CORRENTE. E O PRIMEIRO CHAMADOR DAQUELA FUNCAO (C-7).

    `esta_minimizada` esta escrita em `captura_janela.py:203-204` desde o v1 e
    nao tinha chamador nenhum em toda a arvore. Ela e o unico caminho para dizer
    "minimizado" no SEGUNDO em que o usuario minimiza; sem ela o painel esperaria
    os 30 frames de `FRAMES_IDENTICOS_PARA_CONGELADO` -- ~30 s a 1 Hz -- para
    dizer `congelado`, que e a palavra ERRADA para uma janela que o usuario
    acabou de minimizar de proposito.

    O HWND VEM DA FONTE, E NUNCA DE UM `achar_janela(titulo)` PROPRIO. Recusado
    por medicao de risco: `achar_janela` faz `EnumWindows` e casa por titulo, e
    com DUAS instancias abertas ele pode devolver uma janela DIFERENTE da que a
    fonte esta lendo, se o usuario abrir a segunda no meio da sessao. Perguntar
    a fonte qual hwnd ELA esta lendo e a unica resposta que nao pode divergir --
    e ler a instancia errada e exatamente o defeito que `--janela` existe para
    impedir. Atraves do envelope, `__getattr__` entrega o hwnd do interior
    CORRENTE, o que importa depois de uma religacao (P-3).

    A AUSENCIA DE HWND VIRA `False` E NUNCA `True`: uma fonte que nao tem hwnd
    (o caso do `MssSource` e o das fontes de teste) nao esta minimizada -- ela
    so nao sabe responder, e "nao sei" nao pode virar uma pausa que suspende a
    gravacao da noite inteira.

    O IMPORT MORA DENTRO DA FUNCAO pelo mesmo cuidado de `_montar_a_fonte`:
    `captura_janela` faz `ctypes.windll.user32` no topo, e a suite roda no
    Python GLOBAL.
    """
    hwnd = getattr(fonte, "hwnd", None)
    if not hwnd:
        return False
    from . import captura_janela

    return bool(captura_janela.esta_minimizada(hwnd))


def _o_estado_do_cliente(fonte):
    """Jogando, no login, desconectado -- ou `None` quando nem da para perguntar.

    A PERGUNTA E FEITA COM `hasattr`, EXATAMENTE COMO `sessao.py:468` FAZ, e
    pela mesma razao: `MssSource` nao tem o metodo, e uma fonte de teste
    tambem pode nao ter.

    `None` E `DESCONHECIDO` SAO FATOS DIFERENTES E NAO PODEM COLAPSAR.
    `DESCONHECIDO` e *"eu perguntei e o cliente nao respondeu"* -- a janela
    sumiu, e isso PAUSA. `None` e *"eu nao perguntei"*, e nao pausa nada.
    Colapsar os dois suspenderia a gravacao de qualquer fonte que nao fosse
    `JanelaSource`.

    A CADENCIA DE 5 s DO `matchTemplate` JA MORA DENTRO DE
    `VigiaDoCliente.avaliar` (`cliente.py:250-252`) E ESTE LACO NAO A
    REIMPLEMENTA. O titulo custa ~0,001 ms e e relido todo tique; o
    `matchTemplate` custa ~45 ms e so roda quando a cadencia de la dentro vence.
    """
    if not hasattr(fonte, "estado_do_cliente"):
        return None
    try:
        return fonte.estado_do_cliente()
    except Exception:
        # A COLETA FALHANDO NAO PODE DERRUBAR O TIQUE, e tambem nao pode virar
        # um estado inventado: ela vira "nao perguntei". A cegueira de verdade
        # continua chegando pela `SaudeDoFrame`, que e a rede embaixo desta
        # pergunta.
        log.debug("nao consegui ler o estado do cliente", exc_info=True)
        return None


def _montar_a_fonte(titulo: str, entrada, *, construir_janela=None):
    """A fonte da noite inteira: MEDIDA, MIRADA e ENVELOPADA em `FonteRecuperavel`.

    A BEHAVIOUR E A DA PARTY, E ESSA ESCOLHA E O CASO DE USO
    ========================================================
    A arvore tem DUAS behaviours prontas e esta fase nao inventa uma terceira: o
    mercado congela em silencio e a party RELIGA. Fica a da party, e o argumento
    e um numero -- o incidente medido em `recaptura.py:3-17` foram **33 minutos
    cegos** com o jogo VIVO na tela, a janela existindo, a calibracao certa e
    uma `JanelaSource` NOVA funcionando naquele mesmo instante. So o objeto de
    captura preso no processo estava morto. O mercado herda esse defeito porque
    roda com o usuario olhando; esta fase existe para a farmada NOTURNA, que e
    exatamente quando ninguem esta olhando.

    A FABRICA E O UNICO LUGAR ONDE A LISTA DE ARGUMENTOS DA FONTE EXISTE.
    Arranque e religacao chamam a MESMA funcao, e e isso que impede os dois
    sites de divergirem em silencio.

    E A MIRA MORA DENTRO DELA, e este e o cuidado que decide tudo: a fonte nasce
    com `Regiao(0,0,1,1)`, mede a janela viva e so entao `apontar_para` a regiao
    completa. Se esses tres passos ficassem FORA de `construir()`, a fonte
    reconstruida voltaria olhando para o retangulo UNITARIO e o laco leria UM
    PIXEL pelo resto da noite -- o mesmo defeito que `_regiao_reancorada` existe
    para impedir do lado da party.

    A ORDEM DOS TRES PASSOS, e cada um tem razao:

    1. `Regiao(0,0,1,1)` + `relativa=True` — o molde de
       `renda_modo._frame_de_janela`, e **so essa metade dele**.
    2. `capturar_completo()` UMA vez, so para medir `frame.shape`. E a UNICA
       ocorrencia dela neste modulo.
    3. `apontar_para(Regiao(0, 0, largura, altura))` — legal porque a fonte e
       relativa, e e o espaco de coordenadas em que os retangulos da renda
       foram gravados (M-A). Dali para a frente e `capturar()`, que classifica
       `SaudeDoFrame` sobre o recorte — e e o que torna CEGO-01/02 possiveis.

    E A GEOMETRIA E RECONFERIDA A CADA RECONSTRUCAO, de graca: se a janela
    mudou de tamanho no meio da noite, o aviso sai de novo com o numero de
    agora.

    `construir_janela=` E INJECAO DE DEPENDENCIA e producao nao passa nada. Ele
    e o que permite provar, sem WinRT e sem jogo aberto, que a fonte nasce
    envelopada E que a reconstruida nasce mirada -- as duas afirmacoes que a
    docstring acima faz.

    O IMPORT DE `captura_janela` MORA DENTRO DESTA FUNCAO, e e o que deixa a
    suite rodar no Python GLOBAL, sem as bindings WinRT — o mesmo cuidado de
    `mercado_modo.py:546-549`.

    Devolve `(fonte, None)` ou `(None, mensagem)`. Nunca levanta.
    """
    if construir_janela is None:
        from .captura_janela import JanelaSource as construir_janela

    def construir():
        fonte = construir_janela(
            titulo,
            REGIAO_PARA_MEDIR_A_JANELA,
            relativa=True,
            minimum_update_interval=MS_ENTRE_FRAMES_DA_RENDA,
        )
        try:
            completo = fonte.capturar_completo()
            if completo is None or completo.size == 0:
                raise RuntimeError(
                    "nenhum frame utilizavel chegou dela. Ela esta "
                    "minimizada? A captura por janela funciona com o jogo "
                    "COBERTO por outra janela (medido), mas nao com ele "
                    "minimizado."
                )
            altura, largura = int(completo.shape[0]), int(completo.shape[1])
            _avisar_se_a_janela_mudou_de_tamanho(entrada, largura, altura)
            fonte.apontar_para(
                Regiao(esquerda=0, topo=0, largura=largura, altura=altura)
            )
        except Exception:
            # UMA FABRICA QUE EXPLODE NAO PODE VAZAR A SESSAO DE CAPTURA que ja
            # abriu. Na religacao isso acontece dentro do `try` de
            # `recaptura._religar`, que segue com a fonte ANTIGA.
            fonte.fechar()
            raise
        return fonte

    try:
        return FonteRecuperavel(construir), None
    except Exception as erro:  # noqa: BLE001 - borda: vira recusa, nao traceback
        return None, f"nao consegui abrir a janela {titulo!r}: {erro}"


def _tempo_ate_o_nivel(campos, passos, ajustes):
    """O ETA sobre a taxa da JANELA, ou a ausencia com o motivo dela.

    A JANELA E NAO A SESSAO, e a escolha responde a pergunta que o usuario
    esta fazendo: *"em quanto tempo eu subo, no ritmo de AGORA"*. A taxa da
    sessao inteira responde outra ("o que a noite rendeu") e daria uma previsao
    de uma noite que ja passou, com o tempo parado do jantar dentro dela.

    SEM O EXP LIDO NAO HA O QUE PREVER, e a ausencia herda o motivo em vez de
    inventar um novo: a previsao NAO PODE SER MAIS CONFIANTE QUE O NUMERO DE
    QUE ELA SAI.
    """
    if isinstance(campos.exp, RecusaDaRenda):
        return TempoAteONivel(
            segundos=None,
            motivo_da_ausencia=(
                f"o EXP deste tique recusou ({campos.exp.motivo}), e sem o "
                "ponto de partida nao ha o que subtrair"
            ),
        )

    taxas = as_duas_taxas(
        passos,
        grandeza=GRANDEZA_DO_EXP,
        janela_em_segundos=ajustes.janela_movel_minutos * SEGUNDOS_POR_MINUTO,
        piso_de_amostras=ajustes.amostras_minimas_para_taxa,
        piso_da_janela_em_segundos=ajustes.janela_minima_para_taxa_segundos,
    )
    return tempo_ate_o_nivel(
        exp_atual_em_decimos=int(campos.exp.valor), taxa=taxas.janela
    )


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
    # AS RECUSAS POR CAMPO SAO CONTADAS AQUI, E NAO EM `ContagemDaRenda`.
    #
    # Aquele objeto tem `recusadas_por_motivo`, mas ele NAO carrega este fato:
    # `contar_o_passo` o soma a partir de `passo.recusas`, que e *"A TUPLA QUE
    # `conferir_o_par` DEVOLVEU"* (`renda_conta.py:342-347`) — as recusas das
    # REGRAS DE PAR. A propria docstring diz que ela *"sai vazia no caminho de
    # `CamposDaRenda` com um campo recusado"*. Ou seja: os 79% de recusa do
    # nivel, 21% da adena e 0% do EXP medidos na Fase 1 nao passam por aquele
    # dicionario em tique nenhum.
    #
    # ELAS SAO SOMADAS TODO TIQUE, e nao so nos aceitos — a mesma disciplina de
    # `acumular_motivos` no mercado (`mercado_modo.py:710-712`): a leitura
    # recusada e justamente a que carrega o motivo, e ler so as aceitas
    # esconderia a metade perdida.
    recusas_por_campo = {}
    # O ARRANQUE DA SESSAO, para o "ha quanto tempo a sessao corre" do criterio
    # 1. Ele e o carimbo do PRIMEIRO tique e nao um `time.monotonic()`: o outro
    # numero da mesma linha (o tempo farmado) sai de epochs subtraidos, e
    # misturar duas bases de tempo na mesma linha e como elas divergem.
    desde = None
    # `registrar` devolve `bool` e nunca levanta; no primeiro `OSError` ele
    # desliga a gravacao para a sessao inteira. Somar as perdidas com as
    # aceitas apagaria a pergunta, pelo mesmo argumento de `Contagem` no
    # mercado: "descartei 300" sobre uma sessao em que o disco encheu na
    # terceira linha.
    perdidas = 0
    erros_seguidos = 0
    ticks = 0
    saida = 0
    # O RASTREIO DE VALOR E O UNICO ESTADO GENUINAMENTE NOVO DESTA FASE. Os
    # tres detectores de staleness que a arvore ja tinha sao os tres de PIXEL
    # (`frames._ClassificadorDeSaude`, `recaptura.FonteRecuperavel`,
    # `mercado_pagina`), e NENHUM deles compara o VALOR LIDO. Ele vive FORA do
    # `while` pela mesma razao de `contagem` e `passos`: dentro, nasceria zerado
    # a cada volta e `PARADO` seria inalcancavel.
    rastreio = RastreioDoValor()
    # O LATCH DA TRANSICAO NASCE EM LENDO, e nao em `None`: uma sessao que sobe
    # normal nao pode abrir com um bloco alto anunciando que esta lendo -- isso
    # e o estado esperado. Uma sessao que sobe JA cega anuncia no primeiro
    # tique, que e exatamente quando o usuario precisa saber.
    estado_do_latch = EstadoDaRenda.LENDO
    motivo_do_latch = None
    # OS QUATRO CONTADORES QUE NAO SE SOMAM, no molde de `Contagem` do mercado e
    # de `ContagemDaRenda`: sao perguntas diferentes com consertos diferentes, e
    # somar duas delas apaga a pergunta. O quinto valor
    # (`sem_leitura_do_exp`) e um RECORTE de `sem_leitura` e nao uma quinta
    # parcela -- por isso ele nao entra na soma.
    tiques_por_estado: dict = {}

    # O BLOCO SAI POR INTERVALO E NUNCA POR TIQUE, pela razao escrita em
    # `mercado_console.py:490-496`: *"Repintar um bloco de dezenas de linhas
    # por segundo afogaria a linha ao vivo"*. A cadencia e `--status-a-cada`,
    # que JA EXISTE (P-4) com default de 30 s e que o usuario ja sabe o que faz
    # nos outros modos — nenhuma chave nova entra no `config.toml` (C-4).
    #
    # E ELE SAI JA NA PRIMEIRA VOLTA: `proxima` comeca no agora, entao o
    # primeiro tique ja o dispara. Sem isso o usuario esperaria trinta segundos
    # olhando para linhas de tique sem saber se o calculo esta vivo. Ele nao
    # pode sair ANTES do primeiro tique porque nao ha `CamposDaRenda` ainda —
    # o irmao do mercado consegue porque desenha a analise do DISCO, e a renda
    # nao tem analise de historico nesta fase.
    proximo_bloco = time.monotonic()

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
            if desde is None:
                desde = agora

            # OS QUATRO SINAIS CRUS, NA ORDEM DO CUSTO E NAO DA GRAVIDADE.
            #
            # `frame.saude` ja veio DENTRO do `Frame` e custa zero;
            # `esta_minimizada` e um `IsIconic` (microssegundos);
            # `estado_do_cliente()` le o titulo (~0,001 ms) e so paga o
            # `matchTemplate` (~45 ms) quando a cadencia de 5 s DELE vence --
            # e essa cadencia ja mora la dentro (`cliente.py:250-252`), entao
            # este laco NAO a reimplementa.
            #
            # NENHUM DELES E DETECCAO NOVA (CTX-4). Quatro rodadas de correcao
            # no v1 estao atras dos tres primeiros; esta fase CLASSIFICA e
            # NOMEIA.
            #
            # A INCERTEZA A2 DO ASSUMPTIONS LOG, REGISTRADA POR ESCRITO: *"jogo
            # fechado ou minimizado no meio manifesta-se como CONGELADO em ~30
            # ticks e nunca como excecao"* foi INFERIDO de
            # `captura_janela.py:281-296` + `frames.py:139-148` e NAO foi
            # reproduzido em campo nesta rodada. E por isso que
            # `esta_minimizada` e consultada em vez de se confiar no
            # congelamento: ela e o caminho MEDIDO, e o congelamento e a rede.
            visao = classificar_a_visao(
                saude=frame.saude,
                estado_do_cliente=_o_estado_do_cliente(fonte),
                minimizada=_a_janela_esta_minimizada(fonte),
                campos=campos,
                rastreio=rastreio,
                carimbo=agora,
                segundos_para_parado=SEGUNDOS_PARA_DECLARAR_PARADO,
            )
            tiques_por_estado[visao.estado.value] = (
                tiques_por_estado.get(visao.estado.value, 0) + 1
            )
            if visao.motivo == MOTIVO_DO_EXP_SEM_LEITURA:
                tiques_por_estado[RECORTE_DO_EXP_SEM_LEITURA] = (
                    tiques_por_estado.get(RECORTE_DO_EXP_SEM_LEITURA, 0) + 1
                )

            # O LATCH DA TRANSICAO: UMA linha alta por MUDANCA, e nunca por
            # tique. O molde e `mercado_pagina.py:796-814`, e a razao e a
            # mesma: um aviso repetido a cada tique vira ruido que o olho
            # aprende a pular, e ai ele deixa de avisar. Foi exatamente essa
            # licao que o mercado aprendeu em producao em 2026-09-01, com o
            # usuario concluindo que o scanner tinha parado.
            #
            # O QUE FICA NA TELA ENTRE DUAS TRANSICOES E A LINHA DO TIQUE, e e
            # por isso que ela passa a carregar o estado.
            if (visao.estado, visao.motivo) != (
                estado_do_latch,
                motivo_do_latch,
            ):
                estado_do_latch, motivo_do_latch = visao.estado, visao.motivo
                if visao.estado is EstadoDaRenda.LENDO:
                    log.info("%s", aviso_da_transicao(visao))
                else:
                    log.warning("%s", aviso_da_transicao(visao))

            if visao.estado is EstadoDaRenda.PAUSADO:
                # CEGO-01 E A AUSENCIA DE UMA CHAMADA, E E POR ISSO QUE ELE E
                # BARATO (C-6). Zero coluna nova, zero valor de
                # `descontinuidade` novo, zero segundo portao de admissao.
                #
                # O laco NAO chama `registrar`, NAO conta a recusa por campo
                # (ela nao e recusa de leitura: e cegueira, e soma-la
                # envenenaria os 79%/21%/0% do painel), NAO monta passo e --
                # a linha que faz tudo funcionar -- NAO atualiza `anterior`
                # nem `carimbo_anterior`. Mantido o carimbo de ANTES da
                # cegueira, o primeiro par depois dela tem intervalo maior que
                # `lacuna_maxima_segundos` (60) e `passo_entre_campos` marca
                # `lacuna` SOZINHO; `DESCONTINUIDADES_DO_TEMPO` tira o passo do
                # denominador e `lacunas_excluidas` / `segundos_em_lacuna`
                # mostram na tela quanto tempo foi cego.
                #
                # E O LACO CONTINUA RODANDO. CEGO-01 diz "pausa declarada", e
                # nunca "encerra": os dois precedentes da arvore concordam --
                # a party religa e depois roda cega sem sair, o mercado congela
                # em silencio, e os dois so saem por dez excecoes seguidas de
                # CAPTURA.
                pass
            else:
                for campo, resultado in campos.por_campo.items():
                    if isinstance(resultado, RecusaDaRenda):
                        recusas_por_campo[campo] = (
                            recusas_por_campo.get(campo, 0) + 1
                        )

                # A UNICA PORTA PARA A CONTA (C-8). As quatro regras de par NAO
                # sao chamadas daqui - a decisao sobre o par mora em
                # `renda_conta`.
                passo = passo_entre_campos(
                    anterior,
                    campos,
                    carimbo_anterior=carimbo_anterior,
                    carimbo=agora,
                    fator_de_salto=ajustes.fator_de_salto_da_adena,
                    limiar_de_lacuna_em_segundos=(
                        ajustes.lacuna_maxima_segundos
                    ),
                )
                contar_o_passo(passo, contagem)

                # UMA LINHA POR TIQUE, SEMPRE, inclusive com campo recusado e
                # inclusive PARADO: ela e o denominador da taxa (CTX-3). A fase
                # NAO constroi um segundo portao de admissao - com 79% de
                # recusa no nivel, um portao aqui entregaria linha em ~4% dos
                # tiques, e suprimir as linhas do tempo parado faria a taxa da
                # sessao mentir PARA CIMA (medido: 226 mil contra 466 mil
                # adena/h).
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
            #
            # `estado=` E O SEAM QUE O `03-01` DEIXOU NASCIDO E SEM CONSUMIDOR,
            # e aqui ele ganha o consumidor sem que a assinatura mude.
            # `visao.texto` e `None` no caso LENDO, e ai `linha_do_tique`
            # calcula o texto dela mesma -- que e o que preserva o motivo da
            # recusa na tela nos 79% de tiques em que o nivel recusa com o EXP
            # subindo.
            log.info("%s", linha_do_tique(campos, contagem, estado=visao.texto))

            if time.monotonic() >= proximo_bloco:
                # AS TAXAS SAO CALCULADAS AQUI E NAO POR TIQUE: `as_duas_taxas`
                # varre a sequencia inteira, e a resposta so muda quando ela
                # ganha amostras. Calcular por tique seria trabalho puro sobre
                # milhares de passos, para uma tela que sai a cada 30 s.
                log.info(
                    "\n%s",
                    renda_console.bloco_da_renda(
                        campos,
                        as_duas_taxas(
                            passos,
                            grandeza=GRANDEZA_DO_EXP,
                            janela_em_segundos=ajustes.janela_movel_minutos
                            * SEGUNDOS_POR_MINUTO,
                            piso_de_amostras=ajustes.amostras_minimas_para_taxa,
                            piso_da_janela_em_segundos=(
                                ajustes.janela_minima_para_taxa_segundos
                            ),
                        ),
                        as_duas_taxas(
                            passos,
                            grandeza=GRANDEZA_DA_ADENA,
                            janela_em_segundos=ajustes.janela_movel_minutos
                            * SEGUNDOS_POR_MINUTO,
                            piso_de_amostras=ajustes.amostras_minimas_para_taxa,
                            piso_da_janela_em_segundos=(
                                ajustes.janela_minima_para_taxa_segundos
                            ),
                        ),
                        _tempo_ate_o_nivel(campos, passos, ajustes),
                        contagem,
                        desde=desde,
                        agora=agora,
                        recusas_por_campo=recusas_por_campo,
                        tiques=ticks,
                    ),
                )
                proximo_bloco = time.monotonic() + float(args.status_a_cada)

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
            "\n%s",
            resumo_da_sessao_da_renda(
                contagem,
                orcamento,
                registro,
                recusas_por_campo=recusas_por_campo,
                tiques=ticks,
                tiques_por_estado=tiques_por_estado,
            ),
        )
        if perdidas:
            log.error(
                "%d linha(s) NAO foram gravadas: o registro desligou no "
                "primeiro erro de disco e nao tenta de novo na sessao.",
                perdidas,
            )

    return saida
