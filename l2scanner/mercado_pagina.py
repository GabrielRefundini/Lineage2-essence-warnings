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

O ACORDO ENTRE DOIS FRAMES (LEIT-03), NA VERSAO MINIMA DESTA ONDA
------------------------------------------------------------------
`observar` guarda a TUPLA PARSEADA das linhas aceitas e so devolve
`PaginaAceita` quando o frame seguinte produz a mesma tupla. A linha DESCARTADA
nao entra na comparacao (D-15): ela nao conta como desacordo, senao uma tooltip
passageira impediria para sempre o acordo de uma pagina parada.

O detector de captura CONGELADA (tres janelas bit-identicas) e o minimo de
linhas comparadas (`mercado_minimo_de_linhas_comparadas`) chegam no 02-05.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from .mercado_catalogo import EntradaDoCatalogo
from .mercado_leitura import (
    Descarte,
    LinhaLida,
    casamento_do_cabecalho,
    ler_linha,
)
from .mercado_visao import RastreioDoPainel, cabecalho_de_calibracao

log = logging.getLogger(__name__)


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

    def assinatura(self) -> tuple:
        """A TUPLA PARSEADA que o estabilizador compara entre dois frames.

        So o que foi LIDO entra: indice, chave da serie, total e quantidade. O
        `nome_exibido` fica de fora porque o OCR pode oscilar um caractere sem
        mudar a serie — e a serie e o que a Fase 3 grava. O `serie_nova` fica de
        fora porque ele e verdadeiro no primeiro frame e falso no segundo POR
        CONSTRUCAO: inclui-lo tornaria o acordo impossivel.
        """
        return tuple(
            (
                linha.indice,
                linha.chave_da_serie,
                linha.total_em_centesimos,
                linha.quantidade,
            )
            for linha in self.linhas
        )


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

        self._anterior: tuple | None = None
        self._ultima_leitura: LeituraDaPagina | None = None
        self._layout_ja_recusado = False
        self._falta_ja_avisada = False

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
        """Um tick. `None` enquanto nao houver DOIS frames concordando."""
        self._ultima_leitura = None

        if not self._calibrado():
            self._anterior = None
            return None

        voto = self._rastreio.observar(janela)
        if not voto.aberto or self._rastreio.origem is None:
            # Perder o painel apaga a memoria do frame anterior de proposito:
            # comparar a pagina de antes com a de depois de o painel sumir
            # afirmaria estabilidade sobre uma descontinuidade.
            self._anterior = None
            return None

        origem = self._rastreio.origem
        if not self._layout_confere(janela, origem):
            self._anterior = None
            return None

        leitura = self._ler_a_pagina(janela, origem)
        self._ultima_leitura = leitura

        assinatura = leitura.assinatura()
        anterior, self._anterior = self._anterior, assinatura
        if not assinatura or anterior != assinatura:
            return None

        self._gravar_no_catalogo(leitura.linhas)
        return PaginaAceita(
            linhas=leitura.linhas,
            descartadas=leitura.descartadas,
            motivos=leitura.motivos,
        )

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
                sonda=self._sonda,
                limiar_de_dispersao=self._limiar_de_dispersao,
                tolerancia_do_cruzamento=self._tolerancia_do_cruzamento,
                catalogo=self._catalogo,
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
            if linha.chave_da_serie in self._catalogo:
                continue
            self._catalogo[linha.chave_da_serie] = EntradaDoCatalogo(
                chave=linha.chave_da_serie,
                nome=linha.nome_exibido,
                assinatura=_assinatura_da_chave(linha.chave_da_serie),
            )

    # -- o portao de carga -------------------------------------------------

    def _calibrado(self) -> bool:
        """Falta alguma peca? A leitura simplesmente NAO acontece (feature OFF).

        A conferencia e por AUSENCIA, no arranque de cada tick, e nao por
        `raise`: um `raise` derrubaria o scanner inteiro — que existe para avisar
        que alguem da party morreu — por causa de uma feature de mercado nao
        calibrada.
        """
        faltando = [
            nome
            for nome, valor in (
                ("mercado_grade", self._grade),
                ("mercado_sonda_do_fundo", self._sonda),
                ("mercado_templates_de_digito", self._moldes),
                ("mercado_cabecalho_de_coluna", self._molde_do_cabecalho),
                ("mercado_limiar_do_cabecalho", self._limiar_do_cabecalho),
                ("mercado_limiar_de_leitura_de_glifo", self._piso),
                ("mercado_margem_de_leitura_de_glifo", self._margem),
                ("mercado_corte_de_similaridade", self._corte),
                ("mercado_piso_de_similaridade", self._piso_de_similaridade),
                (
                    "mercado_coluna_do_unitario",
                    self._cal.mercado_coluna_do_unitario,
                ),
            )
            if valor is None or (hasattr(valor, "__len__") and len(valor) == 0)
        ]
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
