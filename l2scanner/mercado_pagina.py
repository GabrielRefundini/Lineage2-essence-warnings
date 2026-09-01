"""A maquina de estado da PAGINA do World Exchange: frames -> pagina aceita.

Este modulo nao abre janela, nao le teclado e nao escreve arquivo. Ele recebe a
janela capturada, localiza o painel, confere o layout, fatia a grade e devolve
`PaginaAceita` — e SO quando dois frames consecutivos concordaram.

ELE NAO REIMPLEMENTA NADA QUE JA EXISTE
----------------------------------------
- A memoria de posicao do painel e `mercado_visao.RastreioDoPainel`, INSTANCIADO
  e nao copiado. Ele ja foi medido: a varredura custa ~45 ms por ancora e o
  painel fica parado a maior parte do tempo (255 frames de campo em 34 posicoes
  distintas), entao ele segue barato por ancora e so volta a varrer quando
  perde. Reescrever isso aqui daria uma segunda memoria de posicao para
  envelhecer.
- A geometria da grade e das colunas vem do `calibration.json`, em DESLOCAMENTO
  a partir da origem do painel. Nunca em coordenada absoluta: o painel anda
  827x831 px nas gravacoes de campo, e uma coluna absoluta apontaria para o
  vazio assim que o usuario arrastasse a janela.
- A leitura de uma linha e `mercado_leitura.ler_linha`.

AS DUAS LEITORAS DE OCR CHEGAM POR INJECAO, E NAO POR IMPORT
-------------------------------------------------------------
Igual a `VigiaDeManutencao.__init__` (`manutencao.py:384-402`): o leitor nao sabe
o que "escala" significa, ele recebe duas maneiras INDEPENDENTES de ler o mesmo
recorte. Isso e o que permite a suite rodar no Python GLOBAL, que nao tem as
bindings WinRT — e, mais importante, e o que permite CONTAR as chamadas e provar
que as duas foram feitas.

O ACORDO ENTRE DOIS FRAMES (LEIT-03)
-------------------------------------
`observar` guarda a leitura anterior e so devolve `PaginaAceita` quando o frame
seguinte produz a MESMA TUPLA PARSEADA nas posicoes aceitas em AMBOS. A linha
DESCARTADA nao entra na comparacao (D-15): ela nao conta como desacordo, senao
uma tooltip passageira impediria para sempre o acordo de uma pagina parada.

Isso abre um buraco que tem fechadura propria: se sobrarem POUCAS posicoes, um
acordo trivial aceitaria uma pagina praticamente nao lida (T-02-26). Por isso o
minimo de posicoes comparadas e LIDO do `calibration.json`, e a chave ausente
DESLIGA a leitura em vez de valer zero.

O CONGELAMENTO OLHA A JANELA INTEIRA, E ISSO CONTRADIZ A LEITURA INGENUA
------------------------------------------------------------------------
D-19, e ele e MEDIDO: a secao 9 do spike provou que o painel e BIT-ESTAVEL — o
mundo atras mudou completamente e o retangulo da ancora nao mudou um bit. Grade
identica entre frames e o caso NORMAL de uma pagina parada, e usa-la como sinal
de congelamento daria falso alarme o tempo todo. O que se mexe e o MUNDO ATRAS
do painel; entao a comparacao e sobre a JANELA INTEIRA, e tres janelas
consecutivas bit-identicas sao captura congelada.

A CADENCIA, MEDIDA E NAO SUPOSTA
---------------------------------
A busca do painel usa a memoria da ultima posicao com rebusca a cada 5 s,
reusando `RastreioDoPainel` e o precedente `SEGUNDOS_ENTRE_BUSCAS_DO_DIALOGO`
(`captura_janela.py:43`); medido, a varredura custa ~45 ms numa janela de
1720x1392 e em 255 frames houve so 34 posicoes distintas. A leitura roda a 1 Hz,
igual ao resto do scanner, e o orcamento do pior tick foi medido em ~110 ms de
1000 ms.

NADA AQUI TOCA `rastreador.py` NEM O GATE DE BRILHO DA BARRA PROPRIA
---------------------------------------------------------------------
Acoplar o sinal de mercado ao detector de morte e precisamente a manobra que
causou o incidente das 27 mortes falsas. O consumidor de oclusao e DETC-02, na
Fase 4, e ha tripwire de arquitetura em `tests/test_mercado_27x.py`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from .identidade import VALOR_MINIMO_DO_TEXTO
from .mercado_catalogo import EntradaDoCatalogo
from .mercado_leitura import (
    Descarte,
    LinhaLida,
    TravaDaObservacao,
    casamento_do_cabecalho,
    ler_linha,
    sonda_e_uma_banda,
)
from .mercado_visao import RastreioDoPainel, cabecalho_de_calibracao

log = logging.getLogger(__name__)

# TRES janelas consecutivas bit-identicas sao captura congelada (D-19).
#
# POR QUE TRES E NAO DUAS: duas janelas iguais acontecem de verdade quando nada
# se mexe atras do painel por um tick — o jogo pausado no alt-tab, por exemplo.
# Tres seguidas a 1 Hz sao tres segundos de tela literalmente identica, incluindo
# o mundo do jogo, e isso nao e um estado que um cliente vivo produz.
JANELAS_IGUAIS_PARA_CONGELAR = 3


# ---------------------------------------------------------------------------
# A VERDADE UNICA SOBRE "CALIBRADO PARA MERCADO"
# ---------------------------------------------------------------------------


def _peca_ausente(valor) -> bool:
    """Ausente e `None` ou vazio, e vazio conta como ausente de proposito.

    Um `{}` gravado no lugar de uma grade nao e uma grade pequena: e a mesma
    falta escrita de outro jeito. `hasattr(valor, "__len__")` deixa numero e
    booleano passarem pela primeira metade sem levantar.
    """
    return valor is None or (hasattr(valor, "__len__") and len(valor) == 0)


def pecas_de_calibracao_de_mercado_faltando(cal) -> list[str]:
    """Que chaves faltam no `calibration.json` para LER o mercado. Em ordem.

    ESTA E A UNICA VERDADE SOBRE "CALIBRADO PARA MERCADO", e ela existe porque
    ate agora havia DUAS: `LeitorDePagina._calibrado` conferia as doze chaves do
    tick, e o arranque do scanner conferia outras tres em tres lugares
    diferentes do `__main__.py`. Duas listas parecidas sobre a mesma pergunta
    divergem, e a divergencia aqui significa um modo `--mercado` que sobe
    dizendo que esta calibrado e nao le uma linha.

    Ela NAO levanta e NAO avisa: e uma pergunta, e quem chama decide o desfecho.
    O leitor transforma a resposta em feature OFF com aviso; o modo `--mercado`
    transforma a mesma resposta em recusa de subir, porque la a feature E o
    produto.

    NOTA DE CONTAGEM, porque um numero que caiu precisa dizer que caiu: o plano
    da Fase 4 falava em ONZE chaves do leitor e QUATORZE no total. Sao DOZE e
    QUINZE. Os comentarios do 02-07 e do 02-05 aqui embaixo numeram a "decima" e
    a "decima primeira" sem contar `mercado_grade`, que entra na conferencia
    assim mesmo, e o plano herdou a conta.

    AS RAZOES, chave por chave:

    - `mercado_grade`, `mercado_sonda_do_fundo`, `mercado_cabecalho_de_coluna`,
      `mercado_limiar_do_cabecalho`, `mercado_templates_de_digito`: sem geometria,
      sem sonda de fundo, sem molde de cabecalho e sem molde de digito nao ha o
      que fatiar nem com que comparar.
    - `mercado_limiar_de_leitura_de_glifo`, `mercado_margem_de_leitura_de_glifo`,
      `mercado_corte_de_similaridade`, `mercado_piso_de_similaridade`: os quatro
      limiares que decidem se um glifo foi lido. Um valor de fabrica aqui seria a
      constante magica que o `calibration.json` existe para nao ter.
    - `mercado_coluna_do_unitario` (02-06): sem ela a TERCEIRA leitura de numero
      nao acontece e a fatia da linha levantaria dentro do tick.
    - `mercado_limiar_de_brilho_da_quantidade` (02-07): `ler_celula_de_quantidade`
      o exige SEM valor de fabrica; o portao por AUSENCIA transforma a falta em
      feature OFF com aviso em vez de `TypeError` no meio do tick.
    - `mercado_minimo_de_linhas_comparadas` (02-05): ela ENTRA, ao contrario da
      folga de cola, porque a ausencia dela NAO degrada para mais seguro. Degrada
      para o ACORDO TRIVIAL (T-02-26), que aceita como lida uma pagina em que
      quase nada atravessou.
    - `mercado_ancoras` e `mercado_limiar_da_ancora` (NOVAS aqui): sem as duas
      nao ha `RastreioDoPainel`, e sem ele ninguem sabe ONDE o painel esta na
      janela. O painel anda 827x831 px nas gravacoes de campo.
    - `mercado_geometria_da_captura` (NOVA aqui): sem ela nao ha `Regiao` para
      pedir a JANELA INTEIRA a captura, e o mercado precisa da janela inteira
      justamente porque o painel anda.

    A `mercado_folga_de_cola_do_glifo` continua FORA, e isso e o 02-08: a
    ausencia dela degrada para MAIS SEGURO (a guarda de glifo colado liga e a
    celula duvidosa cai fechada), entao desligar a leitura inteira por causa dela
    seria trocar uma falha fechada por outra, maior.
    """
    return [
        nome
        for nome, valor in (
            ("mercado_grade", cal.mercado_grade),
            ("mercado_sonda_do_fundo", cal.mercado_sonda_do_fundo),
            ("mercado_templates_de_digito", cal.mercado_templates_de_digito),
            ("mercado_cabecalho_de_coluna", cal.mercado_cabecalho_de_coluna),
            ("mercado_limiar_do_cabecalho", cal.mercado_limiar_do_cabecalho),
            (
                "mercado_limiar_de_leitura_de_glifo",
                cal.mercado_limiar_de_leitura_de_glifo,
            ),
            (
                "mercado_margem_de_leitura_de_glifo",
                cal.mercado_margem_de_leitura_de_glifo,
            ),
            ("mercado_corte_de_similaridade", cal.mercado_corte_de_similaridade),
            ("mercado_piso_de_similaridade", cal.mercado_piso_de_similaridade),
            ("mercado_coluna_do_unitario", cal.mercado_coluna_do_unitario),
            (
                "mercado_limiar_de_brilho_da_quantidade",
                cal.mercado_limiar_de_brilho_da_quantidade,
            ),
            (
                "mercado_minimo_de_linhas_comparadas",
                cal.mercado_minimo_de_linhas_comparadas,
            ),
            ("mercado_ancoras", cal.mercado_ancoras),
            ("mercado_limiar_da_ancora", cal.mercado_limiar_da_ancora),
            (
                "mercado_geometria_da_captura",
                cal.mercado_geometria_da_captura,
            ),
        )
        if _peca_ausente(valor)
    ]


def tupla_comparavel(linha: LinhaLida) -> tuple:
    """O que de uma linha entra na comparacao entre dois frames (D-18).

    A chave da serie, o total em centesimos e a quantidade — NUNCA pixels, ja
    travado por LEIT-03.

    O `nome_exibido` fica de FORA porque o OCR pode oscilar um caractere sem
    mudar a serie, e a serie e o que a Fase 3 grava. O `serie_nova` fica de fora
    porque ele e verdadeiro no primeiro frame e falso no segundo POR
    CONSTRUCAO: inclui-lo tornaria o acordo IMPOSSIVEL. O
    `residuo_do_cruzamento` fica de fora porque ele e OBSERVACAO da Fase 2 sobre
    a propria leitura, e nao dado da linha — dois frames podem discordar nele
    sem discordar do que a tela diz.

    O INDICE tambem fica de fora, e por um motivo diferente dos outros: ele nao
    e conteudo, e ENDERECO. Ele e a chave pela qual as duas leituras se alinham,
    e por isso vive fora da tupla que se compara.
    """
    return (
        linha.chave_da_serie,
        linha.total_em_centesimos,
        linha.quantidade,
    )


def posicoes_comparaveis(
    anterior: "LeituraDaPagina", atual: "LeituraDaPagina"
) -> list[int]:
    """As posicoes aceitas em AMBOS os frames, em ordem. A leitura fiel de D-15.

    A linha DESCARTADA num dos frames fica FORA da comparacao e nao conta como
    desacordo. Quando a linha 3 cai no frame A e passa no frame B, as duas
    listas tem TAMANHOS diferentes — e comparar as listas inteiras faria uma
    tooltip passageira impedir para sempre o acordo de uma pagina parada.

    E a INTERSECAO, e nunca a uniao: uma posicao que so um dos frames leu nao
    tem contra o que ser conferida, e conta-la seria contar uma leitura unica
    como se duas a tivessem confirmado.
    """
    de_antes = {linha.indice for linha in anterior.linhas}
    de_agora = {linha.indice for linha in atual.linhas}
    return sorted(de_antes & de_agora)


def paginas_concordam(
    anterior: "LeituraDaPagina", atual: "LeituraDaPagina"
) -> bool:
    """As duas leituras dizem o MESMO nas posicoes aceitas em ambas?

    Ela NAO julga se ha material suficiente — esse e o piso de
    `mercado_minimo_de_linhas_comparadas`, e ele mora no chamador de proposito.
    Misturar os dois aqui faria "concordam" devolver False para uma pagina que
    concorda de verdade mas em poucas linhas, e o motivo da recusa se perderia.
    """
    de_antes = {linha.indice: tupla_comparavel(linha) for linha in anterior.linhas}
    de_agora = {linha.indice: tupla_comparavel(linha) for linha in atual.linhas}
    return all(
        de_antes[indice] == de_agora[indice]
        for indice in posicoes_comparaveis(anterior, atual)
    )


@dataclass(frozen=True)
class LeituraDaPagina:
    """O que ESTE frame produziu, aceito ou nao. Tres estados, nao dois.

    `linhas` sao as que viraram dado, `descartadas` as que uma peneira pegou, e
    `vazias` as que simplesmente nao tem conteudo. A separacao existe para a
    contagem do console da Fase 4: uma pagina com 3 itens e 7 linhas vazias leu
    3 de 3, e nao 3 de 10.
    """

    linhas: tuple[LinhaLida, ...] = ()
    descartadas: tuple[int, ...] = ()
    motivos: tuple[str, ...] = ()
    vazias: tuple[int, ...] = ()

    def inteiramente_vazia(self) -> bool:
        """Nenhuma linha lida E nenhuma descartada: a pagina nao tinha conteudo.

        Ela nao e aceita e NAO conta como perda — nao houve o que perder. Uma
        pagina com zero lidas mas com descartes e outra coisa: ali havia
        conteudo e uma peneira o pegou, e isso E perda.
        """
        return not self.linhas and not self.descartadas


@dataclass(frozen=True)
class PaginaAceita:
    """Uma pagina que DOIS frames consecutivos afirmaram igual."""

    linhas: tuple[LinhaLida, ...]
    descartadas: tuple[int, ...] = ()
    motivos: tuple[str, ...] = ()


class LeitorDePagina:
    """Le a pagina do mercado a cada tick, e so afirma o que dois frames viram.

    Sem ancora calibrada, sem grade, sem colunas ou sem molde de cabecalho, ele
    simplesmente nao le — feature OFF com aviso alto, nunca `raise` no arranque.
    E o padrao ja escrito em `mercado_visao.py:465-467`, e o unico default seguro
    para um sinal que a Fase 4 vai usar perto do detector de morte.
    """

    def __init__(
        self,
        rastreio: RastreioDoPainel,
        catalogo: dict[str, EntradaDoCatalogo],
        ler_texto,
        ler_texto_conferencia,
        cal,
    ) -> None:
        self._rastreio = rastreio
        self._catalogo = catalogo
        self._ler_texto = ler_texto
        self._ler_texto_conferencia = ler_texto_conferencia
        self._cal = cal

        self._grade = cal.mercado_grade or {}
        self._sonda = cal.mercado_sonda_do_fundo
        self._limiar_de_dispersao = float(
            cal.mercado_limiar_de_dispersao_do_fundo or 0.0
        )
        self._piso = cal.mercado_limiar_de_leitura_de_glifo
        self._margem = cal.mercado_margem_de_leitura_de_glifo
        # OS DOIS PISOS DE BRILHO, e eles nao sao o mesmo numero. As colunas de
        # MOEDA usam o COMPARTILHADO, nomeado a partir de `identidade` — e o
        # unico lugar da leitura de pagina que o nomeia. A coluna Quantity usa o
        # PROPRIO dela, medido no censo pelo 02-07, porque o tronco do `1` fica
        # a V=177 e o compartilhado (180) o corta fora. Um piso global nao
        # existe: a coluna de moeda carrega a palavra de sufixo dentro do
        # recorte, e ela vive entre V=120 e V=173.
        self._valor_minimo_do_numero = VALOR_MINIMO_DO_TEXTO
        self._valor_minimo_da_quantidade = (
            cal.mercado_limiar_de_brilho_da_quantidade
        )
        # A FOLGA DE COLA, E O PORTAO DELA E POR AUSENCIA (02-08).
        #
        # ELA E A UNICA CHAVE DESTA FASE CUJA AUSENCIA NAO DESLIGA A LEITURA, e
        # a razao e que aqui a ausencia degrada para MAIS SEGURO e nao para o
        # comportamento antigo: sem ela `ler_glifos` aplica a GUARDA, e a celula
        # com run largo cai FECHADA em vez de virar numero errado e plausivel.
        # Por isso ela NAO entra na conferencia de `_calibrado` — desligar a
        # leitura inteira por falta de um recurso que so ACRESCENTA celulas
        # seria trocar uma falha fechada por outra, maior.
        #
        # O aviso e ALTO mesmo assim: o custo medido da guarda pura sobre o
        # censo e de 69 linhas em 1.135 (-6,08%), e quem farma tem direito de
        # saber que esta pagando isso por uma chave que uma varredura de um
        # minuto produz.
        self._folga_de_cola = cal.mercado_folga_de_cola_do_glifo
        if self._folga_de_cola is None:
            log.warning(
                "mercado_folga_de_cola_do_glifo esta AUSENTE no "
                "calibration.json: a leitura de mercado vai rodar com a GUARDA "
                "de glifo colado, e toda celula com dois digitos grudados cai "
                "FECHADA (medido: -6,08%% das linhas). E o comportamento "
                "SEGURO. Rode `python tools/medir_largura_de_run.py --gravar` "
                "para MEDIR a folga e recuperar essas linhas."
            )
        self._corte = cal.mercado_corte_de_similaridade
        self._piso_de_similaridade = cal.mercado_piso_de_similaridade
        # `None` mantem a guarda de cruzamento DESLIGADA, que e o estado que a
        # medicao do 02-02 deixou (GUARDA REPROVADA por tolerancia). Ela nao
        # entra na conferencia de `_calibrado`: uma guarda que nao se provou nao
        # pode impedir a leitura de acontecer.
        self._tolerancia_do_cruzamento = cal.mercado_tolerancia_do_cruzamento

        from .mercado_visao import glifos_de_calibracao

        self._moldes = glifos_de_calibracao(cal.mercado_templates_de_digito)

        # O molde do cabecalho e decodificado UMA VEZ, no arranque, e nao a cada
        # tick: ele e ~28 KB de hex, e refaze-lo 3.600 vezes por hora de farm
        # seria trabalho puro. Entrada nao confiavel continua sendo tratada como
        # tal — `cabecalho_de_calibracao` levanta, e aqui isso vira feature OFF.
        self._cabecalho = cal.mercado_cabecalho_de_coluna
        self._limiar_do_cabecalho = cal.mercado_limiar_do_cabecalho
        try:
            self._molde_do_cabecalho = cabecalho_de_calibracao(self._cabecalho)
        except ValueError as erro:
            log.warning(
                "O molde de cabecalho do mercado esta corrompido (%s) — a "
                "leitura de mercado NAO vai acontecer. Recalibre o mercado.",
                erro,
            )
            self._molde_do_cabecalho = None

        # O PISO DE POSICOES COMPARADAS (T-02-26). Ele NAO se escolhe aqui: foi
        # MEDIDO pela varredura de oclusao do 02-02 sobre a MESMA grandeza que
        # esta comparacao julga — o tamanho da INTERSECAO entre as posicoes
        # sobreviventes de dois frames vizinhos, e nao a contagem por frame
        # isolado (essa superestimaria, porque a intersecao e sempre menor ou
        # igual ao minimo dos dois).
        #
        # Chave nula DESLIGA a leitura, e por isso ela entra em `_calibrado`.
        # Um piso ausente valeria ZERO, e zero e o acordo trivial de volta:
        # duas paginas em que tudo foi descartado "concordam" por falta de
        # material.
        self._minimo_comparado = cal.mercado_minimo_de_linhas_comparadas

        # A SONDA DE OCLUSAO E UMA BANDA DESDE 2026-09-01, e uma calibracao
        # anterior a isso ainda funciona -- cai no comportamento antigo, que
        # erra FECHADO. So que ela erra fechado CARO: e a geometria que recusou
        # as dez linhas de `Protecting Scroll: Enchant C-grade Weapon` e matou
        # 31 paginas de campo. O aviso sai UMA VEZ, na construcao, e nao a cada
        # linha de cada tick: um aviso por captura seria ruido, e ruido some.
        if cal.mercado_sonda_do_fundo and not sonda_e_uma_banda(
            cal.mercado_sonda_do_fundo
        ):
            log.warning(
                "mercado_sonda_do_fundo ainda e a sonda HORIZONTAL antiga "
                "(%r): ela mede a linha inteira em altura e recusa linha limpa "
                "de nome comprido como se houvesse tooltip. Rode "
                "`tools/medir_oclusao.py --gravar` para remedir a banda.",
                cal.mercado_sonda_do_fundo,
            )

        self._anterior: LeituraDaPagina | None = None
        self._ultima_leitura: LeituraDaPagina | None = None
        self._layout_ja_recusado = False
        self._falta_ja_avisada = False

        # A QUARTA TRAVA DESTE LEITOR, e a unica POR OFERTA em vez de por
        # estado do modo. Ela mora aqui, e nao em `ler_linha`, porque a
        # repeticao que ela suprime e do TICK: a pagina e relida a cada segundo
        # e a mesma divergencia era registrada a 1 Hz (~7.200 linhas por hora,
        # medido em producao 2026-09-01 09:38). Construida dentro do laco de
        # linhas ela nasceria vazia a cada linha e nao travaria nada.
        #
        # PUBLICA, no padrao dos contadores logo abaixo: e o que deixa o teste
        # afirmar que ESTA trava foi a que chegou a `ler_linha`.
        self.trava_da_observacao = TravaDaObservacao()

        # A JANELA ANTERIOR e a corrida de iguais, para o congelamento.
        # Guardamos UM frame e um contador — e por isso `np.array_equal` (0,89
        # ms medido) basta e sha256 (3,70 ms) ou blake2b (6,81 ms) so custariam
        # de 4 a 15 vezes mais sem comprar nada. Hash paga por lembrar de
        # MUITOS frames; a regra aqui pede lembrar de UM.
        self._janela_anterior: np.ndarray | None = None
        self._janelas_iguais_seguidas = 0
        self._congelamento_ja_avisado = False

        # OS CONTADORES PUBLICOS, no padrao de `RastreioDoPainel.varreduras`:
        # eles deixam o teste afirmar comportamento sem relogio, e sao a
        # superficie que LEIT-04 (Fase 4) vai exibir como "li 7, perdi 3".
        # ESTA FASE PRODUZ O NUMERO E NAO DESENHA CONSOLE.
        self.paginas_lidas = 0
        self.paginas_perdidas = 0
        self.paginas_vazias = 0
        self.paginas_de_outro_layout = 0
        self.ticks_com_painel_aberto = 0
        self.frames_congelados = 0
        self.linhas_descartadas = 0
        self.ultimo_motivo_de_perda: str | None = None

    @property
    def ultima_leitura(self) -> LeituraDaPagina | None:
        """O que o ULTIMO frame produziu, tenha havido acordo ou nao.

        Ela existe porque a contagem "li 7, perdi 3" do console e por FRAME, e
        nao por pagina aceita: um usuario com a tooltip aberta precisa ver que o
        scanner esta vivo e recusando, e nao um silencio indistinguivel de
        travamento.
        """
        return self._ultima_leitura

    def observar(self, janela: np.ndarray) -> PaginaAceita | None:
        """Um tick. `None` enquanto nao houver DOIS frames concordando.

        A ORDEM DOS PORTOES E O DESENHO:

        1. calibrado?           nao -> feature OFF, com aviso
        2. captura congelada?   sim -> aviso alto, nenhuma pagina
        3. painel aberto?       nao -> nada (e a memoria do anterior morre)
        4. layout calibrado?    nao -> recusa alta, nenhuma linha lida
        5. le a pagina, e so entao compara com o frame anterior

        O CONGELAMENTO VEM ANTES DA BUSCA DO PAINEL de proposito: captura
        congelada e propriedade da CAPTURA, e nao da pagina. Procurar o painel
        num frame que sabemos ser repetido gastaria a varredura e — pior —
        produziria um voto "aberto" perfeitamente convincente sobre pixels
        mortos.
        """
        self._ultima_leitura = None

        if not self._calibrado():
            self._anterior = None
            self._esquecer_a_janela()
            return None

        if self._captura_congelada(janela):
            self._anterior = None
            return None

        voto = self._rastreio.observar(janela)
        if not voto.aberto or self._rastreio.origem is None:
            # Perder o painel apaga a memoria do frame anterior de proposito:
            # comparar a pagina de antes com a de depois de o painel sumir
            # afirmaria estabilidade sobre uma descontinuidade.
            self._anterior = None
            return None

        self.ticks_com_painel_aberto += 1

        origem = self._rastreio.origem
        if not self._layout_confere(janela, origem):
            self.paginas_de_outro_layout += 1
            self._anterior = None
            return None

        leitura = self._ler_a_pagina(janela, origem)
        self._ultima_leitura = leitura
        self.linhas_descartadas += len(leitura.descartadas)

        anterior, self._anterior = self._anterior, leitura

        if leitura.inteiramente_vazia():
            # Nao ha o que perder: a pagina nao tinha conteudo. Ela nao e aceita
            # e nao conta como perda — contar aqui faria o fim de uma pagina
            # curta parecer falha de leitura.
            self.paginas_vazias += 1
            return None

        motivo = self._por_que_nao_aceitar(anterior, leitura)
        if motivo is not None:
            self.paginas_perdidas += 1
            self.ultimo_motivo_de_perda = motivo
            log.debug("pagina PERDIDA: %s", motivo)
            return None

        self._gravar_no_catalogo(leitura.linhas)
        self.paginas_lidas += 1
        return PaginaAceita(
            linhas=leitura.linhas,
            descartadas=leitura.descartadas,
            motivos=leitura.motivos,
        )

    # -- o congelamento de captura -----------------------------------------

    def _captura_congelada(self, janela: np.ndarray) -> bool:
        """Tres janelas consecutivas bit-identicas (D-19).

        `np.array_equal` responde False para formas diferentes sem levantar,
        o que importa de verdade: o usuario redimensiona a janela do jogo e o
        tick seguinte chega com outra forma. Um `==` elemento a elemento
        levantaria aqui dentro, no meio do tick.
        """
        anterior = self._janela_anterior
        # A JANELA E GUARDADA POR COPIA, e isso nao e zelo: um backend de
        # captura que REUSE o proprio buffer entre frames faria a comparacao dar
        # sempre igual se guardassemos a referencia — um congelamento eterno
        # sobre uma captura perfeitamente viva, que e o falso positivo exato que
        # este detector existe para nao produzir, invertido. O custo e um
        # memcpy de ~7,2 MB, o mesmo que ja se paga para capturar.
        self._janela_anterior = janela.copy()

        if anterior is not None and np.array_equal(anterior, janela):
            self._janelas_iguais_seguidas += 1
        else:
            self._janelas_iguais_seguidas = 1
            if self._congelamento_ja_avisado:
                log.warning(
                    "A captura VOLTOU a mudar — a leitura de mercado "
                    "recomecou."
                )
            self._congelamento_ja_avisado = False

        if self._janelas_iguais_seguidas < JANELAS_IGUAIS_PARA_CONGELAR:
            return False

        self.frames_congelados += 1
        if not self._congelamento_ja_avisado:
            # LATCH, igual ao portao de layout: congelamento e um ESTADO, e nao
            # um evento. Uma linha de log por tick, para sempre, nao acrescenta
            # forense nenhuma — so afoga o resto do log.
            log.warning(
                "CAPTURA CONGELADA: %d janelas consecutivas bit-identicas. "
                "Nenhuma pagina do mercado sera aceita ate a janela mudar. A "
                "comparacao e sobre a JANELA INTEIRA e nao sobre a grade — "
                "medido, o painel e bit-estavel e grade parada e o caso NORMAL "
                "de uma pagina que ninguem rolou; o que se mexe e o mundo atras "
                "do painel. Se o jogo esta vivo na tela e esta mensagem "
                "persiste, quem parou foi a captura.",
                self._janelas_iguais_seguidas,
            )
        self._congelamento_ja_avisado = True
        return True

    def _esquecer_a_janela(self) -> None:
        self._janela_anterior = None
        self._janelas_iguais_seguidas = 0

    # -- o acordo entre dois frames ----------------------------------------

    def _por_que_nao_aceitar(
        self, anterior: LeituraDaPagina | None, atual: LeituraDaPagina
    ) -> str | None:
        """`None` quando a pagina pode ser aceita; o motivo quando nao.

        Devolver o MOTIVO em vez de um booleano e o que permite ao console da
        Fase 4 dizer por que perdeu, e ao log guardar forense do que aconteceu
        naquele tick. "Perdi 3" sem motivo e indistinguivel de um bug.
        """
        if anterior is None:
            return (
                "primeiro frame com esta pagina: nao ha leitura anterior para "
                "comparar. Um frame sozinho nunca vira pagina aceita (LEIT-03)"
            )

        posicoes = posicoes_comparaveis(anterior, atual)
        minimo = int(self._minimo_comparado)
        if len(posicoes) < minimo:
            return (
                f"so {len(posicoes)} posicoes foram aceitas nos DOIS frames, "
                f"abaixo do minimo de {minimo} "
                f"(mercado_minimo_de_linhas_comparadas). Aceitar aqui seria o "
                f"acordo trivial: poucas linhas concordando sobre uma pagina "
                f"praticamente nao lida"
            )

        if not paginas_concordam(anterior, atual):
            return (
                f"os dois frames DISCORDAM em pelo menos uma das {len(posicoes)} "
                f"posicoes comparadas. O frame novo vira a nova referencia"
            )
        return None

    # -- o portao de layout ------------------------------------------------

    def _layout_confere(self, janela: np.ndarray, origem: tuple[int, int]) -> bool:
        """A pagina na tela E a grade calibrada? Roda ANTES de fatiar (D-09).

        A ORDEM IMPORTA E ELA E MEDIDA: em `scroll/frame_000009` a sonda de fundo
        leu modas de 47 e 65 com a paridade invertida, porque aquele frame e a
        TELA DE BUSCA e aplicar a grade calibrada ali produz lixo. O portao de
        layout tem de vir antes da sonda de oclusao, senao a sonda mede sobre uma
        geometria que nao vale.

        A recusa e ALTA e diz o que houve, mas com LATCH: ela e registrada quando
        o veredito MUDA, e nao a cada tick. A diferenca com
        `manutencao._registrar_desacordo`, que deliberadamente nao tem limite, e
        que aquele evento e episodico e este e um ESTADO — um usuario com a aba
        Adena aberta produziria uma linha de log por captura, para sempre, e a
        mensagem repetida nao acrescenta forense nenhuma.
        """
        confere = self._casamento_do_layout(janela, origem)
        if confere:
            if self._layout_ja_recusado:
                log.warning(
                    "A pagina na tela voltou a ser o layout calibrado ('%s') — "
                    "a leitura de mercado recomecou.",
                    (self._cabecalho or {}).get("layout"),
                )
            self._layout_ja_recusado = False
            return True

        if not self._layout_ja_recusado:
            log.warning(
                "A pagina do mercado na tela NAO e o layout calibrado ('%s') — "
                "nenhuma linha sera lida. O v1 le SOMENTE o layout calibrado: "
                "ler a coluna errada com confianca corrompe a serie por um fator "
                "inteiro (na aba Adena a coluna e '5 mln increment', normalizada "
                "por cinco milhoes de adena e NAO por unidade). Abra a grade de "
                "negociacao, ou recalibre o mercado no layout que voce quer ler.",
                (self._cabecalho or {}).get("layout"),
            )
        self._layout_ja_recusado = True
        return False

    def _casamento_do_layout(
        self, janela: np.ndarray, origem: tuple[int, int]
    ) -> bool:
        if self._molde_do_cabecalho is None or not self._limiar_do_cabecalho:
            return False
        banda = self._banda_do_cabecalho(janela, origem)
        if banda is None:
            return False
        score = casamento_do_cabecalho(
            banda,
            self._molde_do_cabecalho,
            int(self._cabecalho["corte_de_brilho"]),
        )
        return score >= float(self._limiar_do_cabecalho)

    def _banda_do_cabecalho(
        self, janela: np.ndarray, origem: tuple[int, int]
    ) -> np.ndarray | None:
        """A faixa `Goods | Quantity | Total | Unit price | Buy`, na posicao dada.

        O `dx` NAO esta gravado no molde do cabecalho, e nao por esquecimento: a
        banda tem exatamente a largura da grade e comeca onde ela comeca, entao
        o `dx` dela E o `dx` da grade. Duplicar o numero criaria duas verdades
        para uma so geometria.
        """
        ox, oy = origem
        x = ox + int(self._grade["dx"])
        y = oy + int(self._cabecalho["dy"])
        altura = int(self._cabecalho["altura"])
        largura = int(self._cabecalho["largura"])
        if x < 0 or y < 0:
            return None
        if y + altura > janela.shape[0] or x + largura > janela.shape[1]:
            return None
        return janela[y : y + altura, x : x + largura]

    # -- a fatia da grade --------------------------------------------------

    def _ler_a_pagina(
        self, janela: np.ndarray, origem: tuple[int, int]
    ) -> LeituraDaPagina:
        linhas: list[LinhaLida] = []
        descartadas: list[int] = []
        motivos: list[str] = []
        vazias: list[int] = []

        # O CATALOGO PROVISORIO DA PAGINA. Uma pagina de mercado tem VARIAS
        # ofertas do mesmo item, e sem esta copia a serie que a linha 0 cria e
        # invisivel para a linha 1 da MESMA passada: `_gravar_no_catalogo` so
        # roda depois da pagina inteira, e ate la todas as linhas resolveriam
        # contra o mesmo catalogo antigo. Foi assim que a sessao de 2026-08-31
        # 17:05 gravou `+4 Hunter's Stockings` e `+4 Hunter's St«kings` como
        # duas series com `primeira_vez` byte a byte identico — o preco de um
        # item repartido em duas chaves, e o `n` da mediana pela metade, calado.
        #
        # E A MESMA MECANICA QUE `_ler_o_nome` JA USA UM NIVEL ABAIXO (a 3x abre
        # uma entrada provisoria e a 2x resolve contra ela), levantada para o
        # nivel da pagina — nao um mecanismo novo.
        #
        # A COPIA E O QUE PRESERVA A GARANTIA DE DOIS FRAMES. Mutar
        # `self._catalogo` aqui seria mais curto e estaria ERRADO: a serie
        # nasceria de uma pagina que o frame seguinte ainda pode desmentir, e
        # serie no catalogo e irreversivel para o CSV da Fase 3. A provisoria
        # morre com a pagina recusada; quem promove continua sendo
        # `_gravar_no_catalogo`, e so depois do acordo entre os dois frames.
        catalogo_da_pagina = dict(self._catalogo)

        ox, oy = origem
        gx = ox + int(self._grade["dx"])
        gy = oy + int(self._grade["dy"])
        largura = int(self._grade["largura"])
        altura = int(self._grade["altura_da_linha"])

        for indice in range(int(self._grade["linhas_por_pagina"])):
            topo = gy + indice * altura
            if gx < 0 or topo < 0:
                break
            if topo + altura > janela.shape[0] or gx + largura > janela.shape[1]:
                break

            bgr_da_linha = janela[topo : topo + altura, gx : gx + largura]
            recortes = self._recortes_de_coluna(janela, ox, topo, altura)
            if recortes is None:
                break

            resultado = ler_linha(
                indice,
                bgr_da_linha,
                recortes["nome"],
                recortes["total"],
                recortes["quantidade"],
                recortes["unitario"],
                moldes=self._moldes,
                piso=float(self._piso),
                margem=float(self._margem),
                valor_minimo_do_numero=int(self._valor_minimo_do_numero),
                valor_minimo_da_quantidade=int(
                    self._valor_minimo_da_quantidade
                ),
                folga_de_cola=self._folga_de_cola,
                sonda=self._sonda,
                limiar_de_dispersao=self._limiar_de_dispersao,
                tolerancia_do_cruzamento=self._tolerancia_do_cruzamento,
                # A TRAVA DO LEITOR, e nao uma nova: e a mesma em todos os
                # ticks da sessao, e e isso que faz cada divergencia ser
                # registrada uma vez em vez de uma vez por segundo.
                trava_da_observacao=self.trava_da_observacao,
                catalogo=catalogo_da_pagina,
                corte_de_similaridade=float(self._corte),
                piso_de_similaridade=float(self._piso_de_similaridade),
                ler_texto=self._ler_texto,
                ler_texto_conferencia=self._ler_texto_conferencia,
            )

            if resultado is None:
                # Linha vazia: o FIM DA PAGINA. Ela nao e perda, e as linhas
                # abaixo dela nao existem — continuar mediria fundo de tabela.
                vazias.extend(
                    range(indice, int(self._grade["linhas_por_pagina"]))
                )
                break
            if isinstance(resultado, Descarte):
                descartadas.append(resultado.indice)
                motivos.append(resultado.motivo)
                continue
            linhas.append(resultado)
            # A serie desta linha ja vale para as linhas ABAIXO dela.
            _acrescentar_serie(catalogo_da_pagina, resultado)

        return LeituraDaPagina(
            linhas=tuple(linhas),
            descartadas=tuple(descartadas),
            motivos=tuple(motivos),
            vazias=tuple(vazias),
        )

    def _recortes_de_coluna(
        self, janela: np.ndarray, ox: int, topo: int, altura: int
    ) -> dict[str, np.ndarray] | None:
        """As colunas desta linha, meio-abertas em `[dx, dx + largura)`.

        A mesma convencao de `segmentar_glifos`, e por isso colunas vizinhas
        nunca compartilham um pixel. `None` quando um retangulo nao cabe INTEIRO
        na janela: um recorte cortado seria lido com a mesma confianca de um
        inteiro, e `janela[-500:]` e um recorte VALIDO em numpy que devolve o
        canto oposto da imagem, calado.

        A coluna do UNITARIO entrou no 02-06, junto do seu unico consumidor —
        a guarda de cruzamento. Ela e a TERCEIRA celula de numero da linha, e
        sem este recorte a guarda responderia "nao opino" em toda linha e viraria
        codigo morto que os testes aprovam (T-02-39).
        """
        saida: dict[str, np.ndarray] = {}
        for nome, chave in (
            ("nome", "mercado_coluna_do_nome"),
            ("quantidade", "mercado_coluna_da_quantidade"),
            ("total", "mercado_coluna_do_total"),
            ("unitario", "mercado_coluna_do_unitario"),
        ):
            coluna = getattr(self._cal, chave)
            x = ox + int(coluna["dx"])
            largura = int(coluna["largura"])
            if largura <= 0 or x < 0 or x + largura > janela.shape[1]:
                return None
            saida[nome] = janela[topo : topo + altura, x : x + largura]
        return saida

    # -- o catalogo em memoria (o arquivo e o 02-05) -----------------------

    def _gravar_no_catalogo(self, linhas: tuple[LinhaLida, ...]) -> None:
        """A serie so nasce quando a PAGINA foi aceita, nunca antes.

        Gravar no primeiro frame criaria serie a partir de uma leitura que o
        segundo frame ainda pode desmentir — e serie no catalogo e irreversivel
        do ponto de vista do CSV que a Fase 3 escreve.
        """
        for linha in linhas:
            _acrescentar_serie(self._catalogo, linha)

    # -- o portao de carga -------------------------------------------------

    def _calibrado(self) -> bool:
        """Falta alguma peca? A leitura simplesmente NAO acontece (feature OFF).

        A conferencia e por AUSENCIA, no arranque de cada tick, e nao por
        `raise`: um `raise` derrubaria o scanner inteiro — que existe para avisar
        que alguem da party morreu — por causa de uma feature de mercado nao
        calibrada.

        A LISTA NAO MORA MAIS AQUI: ela e
        `pecas_de_calibracao_de_mercado_faltando`, no topo do modulo, porque o
        modo `--mercado` da Fase 4 precisa da MESMA resposta antes de subir e
        duas listas parecidas divergiriam. O que continua sendo daqui e o
        DESFECHO — feature OFF, aviso uma vez so — e ele e diferente do de la,
        onde a mesma falta e recusa de subir.

        AS DUAS PECAS DECODIFICADAS SAO CONFERIDAS DE NOVO, e isso nao e
        repeticao: a funcao de modulo le o `calibration.json` cru, e um molde de
        cabecalho presente mas com hex CORROMPIDO passa por ela e chega aqui como
        `None`, porque `cabecalho_de_calibracao` levantou no construtor. Sem esta
        segunda conferencia o leitor recusaria toda pagina para sempre sem uma
        linha dizendo por que.
        """
        faltando = pecas_de_calibracao_de_mercado_faltando(self._cal)
        for nome, decodificado in (
            ("mercado_templates_de_digito", self._moldes),
            ("mercado_cabecalho_de_coluna", self._molde_do_cabecalho),
        ):
            if _peca_ausente(decodificado) and nome not in faltando:
                faltando.append(nome)
        if faltando:
            if not self._falta_ja_avisada:
                log.warning(
                    "A leitura de mercado NAO vai acontecer: falta %s no "
                    "calibration.json. Rode "
                    "`python -m l2scanner.calibrar_mercado`.",
                    ", ".join(faltando),
                )
            self._falta_ja_avisada = True
            return False
        return True


def _assinatura_da_chave(chave: str) -> str:
    """A assinatura de digitos que `chave_da_serie` anexou depois do `#`."""
    _corpo, _sep, assinatura = chave.rpartition("#")
    return assinatura


def _acrescentar_serie(
    catalogo: dict[str, EntradaDoCatalogo], linha: LinhaLida
) -> None:
    """A serie desta linha entra no catalogo, se ela ainda nao estiver la.

    ELA E COMPARTILHADA POR DOIS CHAMADORES DE PROPOSITO, e a razao e o defeito
    que ela conserta: o catalogo PROVISORIO da pagina (`_ler_a_pagina`) e o
    catalogo do LEITOR (`_gravar_no_catalogo`) tem de acrescentar serie do MESMO
    jeito. Duas copias parecidas divergiriam — bastaria uma delas passar a
    derivar a assinatura do nome em vez da chave para as duas discordarem sobre
    a identidade da mesma linha, e a discordancia so apareceria em producao.

    O `nome_exibido` da PRIMEIRA linha e o que fica: quem chega depois agrupou
    nela, entao a serie ja tem rotulo. Sobrescrever faria o rotulo depender de
    qual oferta a grade calhou de listar por ultimo.
    """
    if linha.chave_da_serie in catalogo:
        return
    catalogo[linha.chave_da_serie] = EntradaDoCatalogo(
        chave=linha.chave_da_serie,
        nome=linha.nome_exibido,
        assinatura=_assinatura_da_chave(linha.chave_da_serie),
    )
