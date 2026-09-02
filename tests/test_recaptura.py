"""Testes da religacao da captura — sem jogo, sem tela, sem rede.

O DEFEITO QUE ESTES TESTES FECHAM, medido em campo em 2026-09-01 as 23:18:39:
o scanner logou `Imagem congelada` e ficou 33 minutos em `[SEM VISAO]` com o
jogo VIVO — janela existindo e nao minimizada, geometria batendo com a
calibracao, quatro membros legiveis no recorte, `HP 5915/5915` na barra propria,
o `mss` vendo a tela MUDAR (diffs 174.087 e 120.828) e uma `JanelaSource` NOVA,
construida naquele mesmo instante, funcionando (diffs 150.453 e 149.983). So o
objeto de captura preso no processo estava morto, e nada nunca o reconstruiu.

A PROVA AQUI E CONTAGEM DE CONSTRUCOES, e nao existencia de funcao. A fonte
falsa incrementa um contador no proprio `__init__`; o teste central afirma que
esse numero SUBIU. Um criterio que apenas afirmasse que `_religar` existe
passaria com a chamada removida — e foi exatamente assim que doze defeitos
nasceram nesta sessao.
"""

from __future__ import annotations

import numpy as np

from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.recaptura import (
    CONGELADOS_SEGUIDOS_PARA_RELIGAR,
    FonteRecuperavel,
)


class Contador:
    """Quantas fontes nasceram e quantas foram fechadas. E a prova inteira."""

    def __init__(self) -> None:
        self.construcoes = 0
        self.fechamentos = 0


class FonteFalsa:
    """Uma `FrameSource` que so devolve a saude que o teste mandar.

    NAO reimplementa nada da producao: nao classifica, nao conta congelados,
    nao decide religacao. Um teste que reimplementa a producao mede a propria
    copia.
    """

    def __init__(self, contador: Contador, saude: SaudeDoFrame) -> None:
        contador.construcoes += 1
        self.numero = contador.construcoes
        self._contador = contador
        self._saude = saude
        self.fechada = False

    def capturar(self) -> Frame:
        # `indice` carrega o NUMERO DA CONSTRUCAO: e assim que o teste sabe
        # qual instancia respondeu, sem espiar o interior do envelope.
        return Frame(
            pixels=np.zeros((1, 1, 3), dtype=np.uint8),
            indice=self.numero,
            saude=self._saude,
        )

    def fechar(self) -> None:
        self.fechada = True
        self._contador.fechamentos += 1


def fabrica_de(contador: Contador, saude_por_construcao):
    """Devolve a fabrica sem argumentos que o envelope chama."""

    def construir() -> FonteFalsa:
        return FonteFalsa(contador, saude_por_construcao(contador.construcoes + 1))

    return construir


def sempre(saude: SaudeDoFrame):
    return lambda _numero: saude


class TestNCongeladosReconstroemAFonte:
    """O buraco de 33 minutos: congelou, ninguem reconstruiu, ninguem voltou."""

    def test_o_arranque_constroi_uma_vez(self) -> None:
        contador = Contador()
        FonteRecuperavel(fabrica_de(contador, sempre(SaudeDoFrame.OK)))
        assert contador.construcoes == 1

    def test_n_congelados_seguidos_reconstroem_a_fonte(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO))
        )

        for _ in range(CONGELADOS_SEGUIDOS_PARA_RELIGAR):
            envelope.capturar()

        assert contador.construcoes == 2

    def test_frames_ok_nunca_religam(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(fabrica_de(contador, sempre(SaudeDoFrame.OK)))

        for _ in range(CONGELADOS_SEGUIDOS_PARA_RELIGAR * 10):
            envelope.capturar()

        assert contador.construcoes == 1

    def test_congelados_intercalados_com_ok_nao_religam(self) -> None:
        """A contagem zera em qualquer saude que nao seja CONGELADO."""
        contador = Contador()
        saudes = [SaudeDoFrame.CONGELADO] * (CONGELADOS_SEGUIDOS_PARA_RELIGAR - 1)
        saudes += [SaudeDoFrame.OK]
        ciclo = iter(saudes * 20)

        class FonteAlternada(FonteFalsa):
            def capturar(self) -> Frame:
                self._saude = next(ciclo)
                return super().capturar()

        def construir() -> FonteAlternada:
            return FonteAlternada(contador, SaudeDoFrame.OK)

        envelope = FonteRecuperavel(construir)
        for _ in range(len(saudes) * 10):
            envelope.capturar()

        assert contador.construcoes == 1

    def test_a_fonte_antiga_e_fechada_exatamente_uma_vez(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO))
        )

        for _ in range(CONGELADOS_SEGUIDOS_PARA_RELIGAR):
            envelope.capturar()

        assert contador.fechamentos == 1

    def test_a_instancia_nova_passa_a_responder(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO))
        )

        for _ in range(CONGELADOS_SEGUIDOS_PARA_RELIGAR):
            envelope.capturar()

        # `indice` e o numero da construcao que produziu o frame.
        assert envelope.capturar().indice == 2

    def test_capturar_devolve_frame_ate_no_tick_da_reconstrucao(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO))
        )

        frames = [
            envelope.capturar() for _ in range(CONGELADOS_SEGUIDOS_PARA_RELIGAR)
        ]

        assert all(isinstance(frame, Frame) for frame in frames)
