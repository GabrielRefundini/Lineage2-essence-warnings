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

import logging
from types import SimpleNamespace

import numpy as np

from l2scanner import recaptura
from l2scanner.frames import Frame, Regiao, SaudeDoFrame
from l2scanner.recaptura import (
    CONGELADOS_SEGUIDOS_PARA_RELIGAR,
    SEGUNDOS_ENTRE_TENTATIVAS,
    TENTATIVAS_DE_RELIGACAO,
    FonteRecuperavel,
)


class Contador:
    """Quantas fontes nasceram e quantas foram fechadas. E a prova inteira."""

    def __init__(self) -> None:
        self.construcoes = 0
        self.fechamentos = 0
        # Quantas vezes a FABRICA foi chamada — sobe tambem quando ela explode
        # e nenhuma fonte chega a nascer. E o que prova que o teto conta
        # TENTATIVAS, e nao sucessos.
        self.chamadas_da_fabrica = 0
        # Cada fonte que nasceu, na ordem. `nascidas[-1]` e a viva.
        self.nascidas: list = []


class RelogioFalso:
    """Um relogio que so anda quando o teste manda.

    Sem ele o portao de espera so seria testavel dormindo de verdade, e um
    teste que dorme 30 s por caso e um teste que ninguem roda.
    """

    def __init__(self) -> None:
        self.agora = 0.0

    def __call__(self) -> float:
        return self.agora

    def avancar(self, segundos: float) -> None:
        self.agora += segundos


class FonteFalsa:
    """Uma `FrameSource` que so devolve a saude que o teste mandar.

    NAO reimplementa nada da producao: nao classifica, nao conta congelados,
    nao decide religacao. Um teste que reimplementa a producao mede a propria
    copia.
    """

    def __init__(self, contador: Contador, saude: SaudeDoFrame) -> None:
        contador.construcoes += 1
        contador.nascidas.append(self)
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


class FonteRoteirizada(FonteFalsa):
    """Uma fonte falsa com um ROTEIRO de saudes: a ultima repete para sempre.

    Serve para o unico caso que uma saude fixa nao cobre: a fonte que religou,
    entregou UM frame bom e voltou a congelar horas depois — que e o episodio de
    campo.
    """

    def __init__(self, contador: Contador, saudes) -> None:
        super().__init__(contador, saudes[0])
        self._roteiro = list(saudes)

    def capturar(self) -> Frame:
        self._saude = (
            self._roteiro[0] if len(self._roteiro) == 1 else self._roteiro.pop(0)
        )
        return super().capturar()


def fabrica_de(contador: Contador, saude_por_construcao):
    """Devolve a fabrica sem argumentos que o envelope chama."""

    def construir() -> FonteFalsa:
        contador.chamadas_da_fabrica += 1
        return FonteFalsa(contador, saude_por_construcao(contador.construcoes + 1))

    return construir


def fabrica_roteirizada(contador: Contador, roteiro_por_construcao):
    def construir() -> FonteRoteirizada:
        contador.chamadas_da_fabrica += 1
        return FonteRoteirizada(
            contador, roteiro_por_construcao(contador.construcoes + 1)
        )

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


def rodar(envelope, relogio: RelogioFalso, ticks: int) -> None:
    """Ticks com o relogio andando o bastante para a espera nunca ser o freio."""
    for _ in range(ticks):
        envelope.capturar()
        relogio.avancar(SEGUNDOS_ENTRE_TENTATIVAS)


def ticks_para_gastar_o_orcamento() -> int:
    """Com folga de dez vezes: o teto tem de segurar por mais que se ande."""
    return CONGELADOS_SEGUIDOS_PARA_RELIGAR * TENTATIVAS_DE_RELIGACAO * 10


class TestOTetoEMedidoNaoPrometido:
    """Sem teto, uma fabrica que nunca cura martelaria a WGC por tick, eterno."""

    def test_o_total_de_construcoes_para_no_teto(self) -> None:
        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO)), relogio=relogio
        )

        rodar(envelope, relogio, ticks_para_gastar_o_orcamento())

        assert contador.construcoes == 1 + TENTATIVAS_DE_RELIGACAO

    def test_o_teto_nao_anda_com_dez_vezes_mais_ticks(self) -> None:
        """A mesma medicao DUAS vezes: o numero tem de ser o mesmo.

        Este par tambem e a prova de que o reset do orcamento esta ancorado no
        FRAME SAUDAVEL e nao no `__init__` ter retornado. Aqui toda fonte nova
        CONSTROI sem erro — e continua morta, que e o caso de campo. Se o reset
        olhasse para a construcao, o teto nunca seria alcancado e este numero
        cresceria sem parar.
        """
        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO)), relogio=relogio
        )

        rodar(envelope, relogio, ticks_para_gastar_o_orcamento())
        no_teto = contador.construcoes
        rodar(envelope, relogio, ticks_para_gastar_o_orcamento() * 10)

        assert contador.construcoes == no_teto

    def test_esgotado_o_teto_sai_UM_error_e_nao_um_por_tick(self, caplog) -> None:
        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO)), relogio=relogio
        )

        with caplog.at_level(logging.ERROR, logger="l2scanner.recaptura"):
            rodar(envelope, relogio, ticks_para_gastar_o_orcamento())

        erros = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(erros) == 1

    def test_esgotado_o_teto_capturar_continua_devolvendo_frame(self) -> None:
        """Nao sai, nao levanta, nao silencia: segue cego e honesto."""
        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO)), relogio=relogio
        )

        rodar(envelope, relogio, ticks_para_gastar_o_orcamento())

        assert isinstance(envelope.capturar(), Frame)


class TestAEsperaEntreTentativas:
    def test_o_relogio_parado_impede_a_segunda_tentativa(self) -> None:
        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO)), relogio=relogio
        )

        for _ in range(ticks_para_gastar_o_orcamento()):
            envelope.capturar()

        assert contador.construcoes == 2

    def test_avancar_o_relogio_libera_a_proxima_tentativa(self) -> None:
        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO)), relogio=relogio
        )

        for _ in range(CONGELADOS_SEGUIDOS_PARA_RELIGAR):
            envelope.capturar()
        assert contador.construcoes == 2

        relogio.avancar(SEGUNDOS_ENTRE_TENTATIVAS)
        envelope.capturar()

        assert contador.construcoes == 3

    def test_o_envelope_nunca_dorme(self, monkeypatch) -> None:
        """`time.sleep` aqui atrasaria os comandos e a agenda do mesmo tick."""

        def explodir(_segundos):  # pragma: no cover - existe para NAO rodar
            raise AssertionError(
                "o envelope chamou time.sleep — o laco ja dorme por tick"
            )

        monkeypatch.setattr(recaptura.time, "sleep", explodir)

        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO)), relogio=relogio
        )

        rodar(envelope, relogio, ticks_para_gastar_o_orcamento())


class TestUmaReconstrucaoQueExplode:
    """A excecao morre dentro do envelope. O braco `except` do laco nao e usado."""

    @staticmethod
    def _fabrica_que_explode_depois_da_primeira(contador: Contador):
        def construir():
            contador.chamadas_da_fabrica += 1
            if contador.chamadas_da_fabrica > 1:
                raise RuntimeError("a WGC recusou a sessao nova")
            return FonteFalsa(contador, SaudeDoFrame.CONGELADO)

        return construir

    def test_capturar_devolve_frame_sem_propagar(self) -> None:
        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            self._fabrica_que_explode_depois_da_primeira(contador), relogio=relogio
        )

        rodar(envelope, relogio, ticks_para_gastar_o_orcamento())

        assert isinstance(envelope.capturar(), Frame)

    def test_o_interior_continua_sendo_a_fonte_antiga(self) -> None:
        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            self._fabrica_que_explode_depois_da_primeira(contador), relogio=relogio
        )

        rodar(envelope, relogio, ticks_para_gastar_o_orcamento())

        # `indice` e o numero da construcao: 1 significa "a de sempre".
        assert envelope.capturar().indice == 1
        assert contador.construcoes == 1

    def test_a_antiga_nao_e_fechada_quando_a_nova_nao_nasce(self) -> None:
        """Construir ANTES de fechar: falhar em religar nao pode deixar o
        scanner sem fonte nenhuma."""
        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            self._fabrica_que_explode_depois_da_primeira(contador), relogio=relogio
        )

        rodar(envelope, relogio, ticks_para_gastar_o_orcamento())

        assert contador.fechamentos == 0

    def test_a_falha_conta_tentativa_e_o_teto_e_respeitado(self) -> None:
        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            self._fabrica_que_explode_depois_da_primeira(contador), relogio=relogio
        )

        rodar(envelope, relogio, ticks_para_gastar_o_orcamento())

        # 1 chamada do arranque + TENTATIVAS_DE_RELIGACAO que explodiram.
        assert contador.chamadas_da_fabrica == 1 + TENTATIVAS_DE_RELIGACAO


class TestOOrcamentoVoltaInteiro:
    """Um congelamento novo horas depois compra um orcamento CHEIO de novo."""

    @staticmethod
    def _roteiro_que_cura_uma_vez(numero: int):
        # A segunda fonte entrega UM frame bom e volta a congelar — o episodio
        # de campo: a sessao nova nasce viva e morre depois.
        if numero == 2:
            return [SaudeDoFrame.OK, SaudeDoFrame.CONGELADO]
        return [SaudeDoFrame.CONGELADO]

    def test_um_frame_saudavel_devolve_o_orcamento(self) -> None:
        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            fabrica_roteirizada(contador, self._roteiro_que_cura_uma_vez),
            relogio=relogio,
        )

        rodar(envelope, relogio, ticks_para_gastar_o_orcamento())

        # 1 do arranque + 1 da religacao que curou + TENTATIVAS do orcamento
        # NOVO que o frame saudavel comprou. Sem o reset o total pararia em
        # 1 + TENTATIVAS.
        assert contador.construcoes == 2 + TENTATIVAS_DE_RELIGACAO

    def test_sem_frame_saudavel_o_total_e_estritamente_menor(self) -> None:
        """O par honesto: mesma bancada, unica diferenca o frame bom."""
        contador = Contador()
        relogio = RelogioFalso()
        envelope = FonteRecuperavel(
            fabrica_de(contador, sempre(SaudeDoFrame.CONGELADO)), relogio=relogio
        )

        rodar(envelope, relogio, ticks_para_gastar_o_orcamento())

        assert contador.construcoes == 1 + TENTATIVAS_DE_RELIGACAO


class FonteRica(FonteFalsa):
    """Uma falsa com o resto da superficie da `JanelaSource`.

    Cada resposta carrega o NUMERO DA CONSTRUCAO, entao o teste sabe qual
    instancia atendeu sem espiar o interior do envelope.
    """

    def __init__(self, contador: Contador, saude: SaudeDoFrame) -> None:
        super().__init__(contador, saude)
        self.regiao = None

    def capturar_completo(self):
        return f"completo-{self.numero}"

    def completo_do_frame_atual(self):
        return f"atual-{self.numero}"

    def apontar_para(self, regiao) -> None:
        self.regiao = regiao


class FonteRicaComCliente(FonteRica):
    def estado_do_cliente(self):
        return f"cliente-{self.numero}"


class FonteQueRecusaReapontar(FonteRica):
    """A recusa de `apontar_para` numa fonte de coordenadas de desktop.

    `JanelaSource.apontar_para` levanta `ValueError` quando a regiao nao e
    relativa a janela. Essa recusa nao pode virar crash de religacao.
    """

    def apontar_para(self, regiao) -> None:
        if self.numero >= 2:
            raise ValueError("regiao de desktop nao pode ser reapontada")
        self.regiao = regiao


def fabrica_rica(contador: Contador, classe=FonteRica, saude=SaudeDoFrame.CONGELADO):
    def construir():
        contador.chamadas_da_fabrica += 1
        return classe(contador, saude)

    return construir


def forcar_religacao(envelope) -> None:
    for _ in range(CONGELADOS_SEGUIDOS_PARA_RELIGAR):
        envelope.capturar()


class TestOsDonosDeReferenciaSobrevivemATroca:
    """Sem isto, religar rebindaria so a variavel local e os tres donos da
    referencia ficariam apontando para o objeto morto — o defeito de hoje,
    agora em tres lugares."""

    def test_metodo_ligado_colhido_antes_entrega_a_fonte_nova(self) -> None:
        """O padrao EXATO do `Gravador`, que colhe o metodo na construcao."""
        contador = Contador()
        envelope = FonteRecuperavel(fabrica_rica(contador))

        fonte_completa = envelope.completo_do_frame_atual  # como o Gravador faz
        forcar_religacao(envelope)

        assert contador.construcoes == 2
        assert fonte_completa() == "atual-2"

    def test_capturar_completo_chega_a_fonte_viva(self) -> None:
        """O padrao do `Reancorador`, que guarda a fonte na construcao."""
        contador = Contador()
        envelope = FonteRecuperavel(fabrica_rica(contador))

        forcar_religacao(envelope)

        assert envelope.capturar_completo() == "completo-2"

    def test_apontar_para_chega_a_fonte_viva(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(fabrica_rica(contador))
        forcar_religacao(envelope)

        envelope.apontar_para("regiao-nova")

        assert contador.nascidas[-1].regiao == "regiao-nova"


class TestOHasattrRespondePeloInterior:
    """`sessao.py:453` decide por `hasattr(fonte, "estado_do_cliente")`.

    `MssSource` nao tem esse metodo. Um metodo DECLARADO no envelope faria o
    caminho de desktop prometer um estado de cliente que nao existe e estourar
    dentro do `try` de analise — por isso a delegacao e por `__getattr__`.
    """

    def test_e_False_quando_o_interior_nao_tem(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(fabrica_rica(contador, FonteRica))

        assert not hasattr(envelope, "estado_do_cliente")

    def test_e_True_quando_o_interior_tem(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(fabrica_rica(contador, FonteRicaComCliente))

        assert hasattr(envelope, "estado_do_cliente")

    def test_a_chamada_devolve_o_valor_do_interior_vivo(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(fabrica_rica(contador, FonteRicaComCliente))

        assert envelope.estado_do_cliente() == "cliente-1"
        forcar_religacao(envelope)
        assert envelope.estado_do_cliente() == "cliente-2"


class TestAGeometriaReancoradaSobreviveARELIGACAO:
    """Sem isto, um congelamento depois de um reancoramento devolveria o scanner
    a ler o lugar antigo — ler um lugar com a regua de outro, que
    `reancoragem.py:359` chama de pior que nao reancorar."""

    def test_a_fonte_nova_recebe_a_regiao_reancorada(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(fabrica_rica(contador))

        envelope.apontar_para("regiao-reancorada")
        forcar_religacao(envelope)

        assert contador.construcoes == 2
        assert contador.nascidas[-1].regiao == "regiao-reancorada"

    def test_sem_reancoramento_nada_e_reaplicado(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(fabrica_rica(contador))

        forcar_religacao(envelope)

        assert contador.nascidas[-1].regiao is None

    def test_uma_recusa_de_reapontar_nao_derruba_a_religacao(self) -> None:
        contador = Contador()
        envelope = FonteRecuperavel(
            fabrica_rica(contador, FonteQueRecusaReapontar)
        )

        envelope.apontar_para("regiao-de-desktop")
        forcar_religacao(envelope)

        # A religacao aconteceu e foi ADOTADA, apesar da recusa.
        assert contador.construcoes == 2
        assert envelope.capturar_completo() == "completo-2"


def _args(replay=None, janela=None) -> SimpleNamespace:
    return SimpleNamespace(replay=replay, janela=janela)


def _cal(na_janela: bool = True) -> SimpleNamespace:
    regiao = Regiao(esquerda=0, topo=0, largura=10, altura=10)
    return SimpleNamespace(
        party_window=regiao,
        party_window_na_janela=regiao if na_janela else None,
        hp_proprio=None,
    )


def _janela_falsa(contador: Contador):
    class JanelaSourceFalsa(FonteRica):
        def __init__(self, titulo, regiao, relativa=False, extras=None) -> None:
            super().__init__(contador, SaudeDoFrame.OK)
            self.titulo = titulo
            self.relativa = relativa

    return JanelaSourceFalsa


def _mss_falsa(contador: Contador):
    class MssSourceFalsa(FonteRica):
        def __init__(self, regiao, extras=None) -> None:
            super().__init__(contador, SaudeDoFrame.OK)
            self.regiao_pedida = regiao

    return MssSourceFalsa


class TestOsDoisBackendsPassamPeloMesmoCano:
    """`--janela` e `mss` sao embrulhados pela MESMA `FonteRecuperavel`.

    O replay fica de fora de proposito: reconstruir um replay reiniciaria a
    gravacao, e o fim dele ja e `StopIteration` no laco.
    """

    def test_o_caminho_da_janela_devolve_o_envelope(self, monkeypatch) -> None:
        from l2scanner import __main__ as principal

        contador = Contador()
        monkeypatch.setattr(principal, "JanelaSource", _janela_falsa(contador))

        fonte = principal.montar_fonte(_args(janela="Lineage II"), _cal(), {})

        assert isinstance(fonte, FonteRecuperavel)
        assert contador.construcoes == 1

    def test_o_caminho_do_desktop_devolve_o_envelope(self, monkeypatch) -> None:
        from l2scanner import __main__ as principal

        contador = Contador()
        monkeypatch.setattr(principal, "MssSource", _mss_falsa(contador))

        fonte = principal.montar_fonte(_args(), _cal(na_janela=False), {})

        assert isinstance(fonte, FonteRecuperavel)
        assert contador.construcoes == 1

    def test_o_replay_fica_fora_do_envelope(self, monkeypatch) -> None:
        from l2scanner import __main__ as principal

        class ReplaySourceFalsa:
            def __init__(self, pasta) -> None:
                self.pasta = pasta

            def __len__(self) -> int:
                return 7

        monkeypatch.setattr(principal, "ReplaySource", ReplaySourceFalsa)

        fonte = principal.montar_fonte(_args(replay="recordings/x"), _cal(), {})

        assert isinstance(fonte, ReplaySourceFalsa)
        assert not isinstance(fonte, FonteRecuperavel)

    def test_a_religacao_da_janela_usa_a_mesma_fabrica(self, monkeypatch) -> None:
        """A lista de argumentos existe UMA vez: a segunda fonte nasce igual."""
        from l2scanner import __main__ as principal

        contador = Contador()
        monkeypatch.setattr(principal, "JanelaSource", _janela_falsa(contador))
        fonte = principal.montar_fonte(_args(janela="Lineage II"), _cal(), {})

        # A falsa devolve OK; congelamos empurrando CONGELADO na instancia viva.
        for _ in range(CONGELADOS_SEGUIDOS_PARA_RELIGAR):
            contador.nascidas[-1]._saude = SaudeDoFrame.CONGELADO
            fonte.capturar()

        assert contador.construcoes == 2
        assert contador.nascidas[-1].titulo == "Lineage II"
        assert contador.nascidas[-1].relativa is True
