"""Testes da identidade por imagem do nome.

O que estes testes protegem: sem identidade visual, o nome do membro vem da
POSICAO da linha. A party window compacta as linhas quando alguem sai, entao a
posicao nao e uma identidade — e so um lugar. O resultado seria "Korzis morreu"
quando quem morreu foi o Kaus, e a party socorreria a pessoa errada sem
desconfiar, porque a mensagem parece perfeitamente normal.

A fixture e um frame REAL da party do usuario, com as assinaturas gravadas pela
calibracao contra a mesma tela.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.identidade import (
    LIMIAR_DE_CASAMENTO,
    Assinatura,
    criar_assinatura,
    identificar,
    mascara_de_texto,
)
from l2scanner.visao import EstadoDaLinha, extrair

FIXTURES = Path(__file__).parent / "fixtures" / "identidade"


@pytest.fixture
def calibracao() -> Calibracao:
    return Calibracao.carregar(FIXTURES / "calibracao.json")


@pytest.fixture
def pixels() -> np.ndarray:
    px = cv2.imread(str(FIXTURES / "party_ordem_original.png"), cv2.IMREAD_COLOR)
    assert px is not None, "fixture da party nao pode ser lida"
    return px


def remontar(px: np.ndarray, cal: Calibracao, ordem: list[int]) -> np.ndarray:
    """Reordena as linhas da party window, simulando a party reorganizada."""
    lay = cal.layout
    novo = px.copy()

    def topo_de(i: int) -> int:
        return lay.icone_y + i * lay.passo + lay.nome_dy - 4

    blocos = [px[topo_de(i) : topo_de(i) + lay.passo].copy() for i in range(4)]
    for destino, origem in enumerate(ordem):
        inicio = topo_de(destino)
        novo[inicio : inicio + lay.passo] = blocos[origem]
    return novo


class TestMascaraDeTexto:
    """O texto e claro e dessaturado; o cenario e colorido."""

    def test_texto_branco_e_marcado(self):
        branco = np.full((10, 10, 3), 240, dtype=np.uint8)
        assert mascara_de_texto(branco).all()

    def test_terreno_colorido_nao_e_marcado(self):
        # verde de grama: claro o bastante, mas saturado
        grama = np.full((10, 10, 3), (60, 130, 70), dtype=np.uint8)
        assert not mascara_de_texto(grama).any()

    def test_sombra_escura_nao_e_marcada(self):
        escuro = np.full((10, 10, 3), 40, dtype=np.uint8)
        assert not mascara_de_texto(escuro).any()

    def test_recorte_vazio_nao_quebra(self):
        vazio = np.zeros((0, 0, 3), dtype=np.uint8)
        assert mascara_de_texto(vazio).size == 0


class TestAssinatura:
    def test_ida_e_volta_pela_serializacao(self):
        gerador = np.random.default_rng(3)
        recorte = gerador.integers(0, 255, (20, 100, 3), dtype=np.uint8)
        original = criar_assinatura("TioMad", recorte)

        voltou = Assinatura.de_dict(original.como_dict())

        assert voltou.nome == "TioMad"
        assert voltou.mascara.shape == original.mascara.shape
        assert np.array_equal(voltou.mascara, original.mascara)

    def test_assinatura_de_verdade_tem_texto(self, pixels, calibracao):
        regiao = calibracao.regiao_do_nome(0)
        recorte = pixels[
            regiao.topo : regiao.topo + regiao.altura,
            regiao.esquerda : regiao.esquerda + regiao.largura,
        ]
        assert criar_assinatura("J4guar", recorte).pixels_de_texto > 12


class TestIdentificacao:
    def test_reconhece_cada_membro_no_frame_real(self, pixels, calibracao):
        obs = extrair(
            Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK), calibracao
        )
        reconhecidos = [l.nome for l in obs.linhas[:4]]
        assert reconhecidos == calibracao.nomes

    def test_confianca_alta_nos_acertos(self, pixels, calibracao):
        obs = extrair(
            Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK), calibracao
        )
        for linha in obs.linhas[:4]:
            assert linha.confianca_do_nome > LIMIAR_DE_CASAMENTO

    def test_sem_assinaturas_nao_reconhece_e_nao_quebra(self, pixels, calibracao):
        """Calibracao antiga, sem assinaturas: degrada para o nome por ordem."""
        calibracao.assinaturas = []
        obs = extrair(
            Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK), calibracao
        )
        assert all(l.nome is None for l in obs.linhas)
        assert obs.membros_presentes == 4  # o resto continua funcionando

    def test_recorte_sem_texto_nao_e_identificado(self, calibracao):
        """Linha vazia nao pode ser atribuida a ninguem."""
        terreno = np.full((20, 100, 3), (60, 130, 70), dtype=np.uint8)
        casamento = identificar(terreno, calibracao.assinaturas)
        assert casamento.nome is None

    def test_nome_desconhecido_nao_e_chutado(self, calibracao):
        """Um membro novo, sem assinatura gravada, nao pode virar outro.

        Chutar seria pior do que nao saber: o alerta sairia com o nome de quem
        nao morreu.
        """
        # texto sintetico que nao corresponde a nenhuma assinatura
        estranho = np.zeros((20, 100, 3), dtype=np.uint8)
        estranho[4:16, 5:95] = 255  # bloco solido, nada parecido com um nome

        casamento = identificar(estranho, calibracao.assinaturas)
        assert casamento.nome is None


class TestOrdemDaParty:
    """O motivo de tudo isto existir."""

    @pytest.mark.parametrize(
        "descricao,ordem",
        [
            ("ordem original", [0, 1, 2, 3]),
            ("dois membros trocados", [0, 3, 2, 1]),
            ("ordem invertida", [3, 2, 1, 0]),
            ("primeiro saiu, os outros sobem", [1, 2, 3, 3]),
        ],
    )
    def test_o_nome_segue_o_membro_e_nao_a_linha(
        self, pixels, calibracao, descricao, ordem
    ):
        reordenado = remontar(pixels, calibracao, ordem)
        obs = extrair(
            Frame(pixels=reordenado, indice=0, saude=SaudeDoFrame.OK), calibracao
        )

        reconhecidos = [l.nome for l in obs.linhas[:4]]
        esperados = [calibracao.nomes[i] for i in ordem]

        assert reconhecidos == esperados, (
            f"{descricao}: o nome ficou preso a posicao da linha em vez de "
            f"seguir o membro — foi exatamente isto que a identidade visual "
            f"veio resolver"
        )

    def test_sem_identidade_visual_a_ordem_engana(self, pixels, calibracao):
        """Prova que o problema era real, e nao teorico.

        Com as assinaturas removidas, o nome volta a vir da posicao — e uma
        party reordenada produz atribuicao errada.
        """
        reordenado = remontar(pixels, calibracao, [3, 2, 1, 0])
        calibracao.assinaturas = []

        obs = extrair(
            Frame(pixels=reordenado, indice=0, saude=SaudeDoFrame.OK), calibracao
        )

        # sem assinatura nenhuma linha e identificada, e quem chama cairia no
        # nome por posicao — que aqui esta invertido em relacao a realidade
        assert all(l.nome is None for l in obs.linhas)
        nomes_por_posicao = [calibracao.nome_da_linha(i) for i in range(4)]
        nomes_reais = [calibracao.nomes[i] for i in [3, 2, 1, 0]]
        assert nomes_por_posicao != nomes_reais


class TestRastreadorUsaONomeReconhecido:
    def test_evento_leva_o_nome_reconhecido_e_nao_o_da_posicao(self):
        from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento
        from l2scanner.visao import LeituraDeLinha, Observacao

        def obs(hp_linha0: float, nome_linha0: str) -> Observacao:
            return Observacao(
                indice_do_frame=0,
                ui_visivel=True,
                linhas=(
                    LeituraDeLinha(
                        indice=0,
                        estado=EstadoDaLinha.COM_MEMBRO,
                        hp=hp_linha0,
                        mp=1.0,
                        nome=nome_linha0,
                        confianca_do_nome=0.98,
                    ),
                ),
            )

        # a lista diz que a linha 0 e do J4guar, mas a imagem diz que e o Korzis
        rastreador = Rastreador(
            nomes=["J4guar"], ajustes=Ajustes(confirmacoes_para_morte=2)
        )
        for i in range(15):
            rastreador.observar(obs(1.0, "Korzis"), -100 + i)

        eventos = []
        for i in range(3):
            eventos.extend(rastreador.observar(obs(0.0, "Korzis"), 10 + i))

        mortes = [e for e in eventos if e.tipo is TipoDeEvento.MORREU]
        assert len(mortes) == 1
        assert mortes[0].membro == "Korzis", (
            "o alerta precisa nomear quem a IMAGEM identificou, nao quem a "
            "lista diz que ocupa aquela posicao"
        )


class TestReordenacaoDaPartyNoRastreador:
    """O falso positivo que aconteceu de verdade, em 2026-08-24.

    O TioMad saiu da party e o alerta anunciou: "Korzis: saiu da party".

    Causa: o rastreador guardava estado por POSICAO DE LINHA. Quando a party
    reordenou para [Korzis, J4guar, Kaus] e a linha 3 esvaziou, ele buscou o
    nome na posicao 3 da lista configurada — "Korzis".

    A identidade visual sozinha nao resolvia: ela rotulava a linha, mas a
    maquina de estados continuava indexada por posicao. So passou a funcionar
    quando o ESTADO tambem passou a ser guardado por pessoa.
    """

    NOMES = ["J4guar", "Kaus", "TioMad", "Korzis"]

    def _obs(self, nomes_por_linha, hp=None):
        from l2scanner.visao import LeituraDeLinha, Observacao

        hp = hp or {}
        linhas = []
        for i, nome in enumerate(nomes_por_linha):
            if nome is None:
                linhas.append(
                    LeituraDeLinha(i, EstadoDaLinha.VAZIA, None, None)
                )
            else:
                linhas.append(
                    LeituraDeLinha(
                        i,
                        EstadoDaLinha.COM_MEMBRO,
                        hp.get(nome, 1.0),
                        1.0,
                        nome=nome,
                        confianca_do_nome=0.98,
                    )
                )
        return Observacao(0, True, tuple(linhas))

    def _rastreador_aquecido(self):
        from l2scanner.rastreador import Ajustes, Rastreador

        r = Rastreador(
            nomes=list(self.NOMES),
            ajustes=Ajustes(confirmacoes_para_saida=3, confirmacoes_para_morte=3),
        )
        for i in range(15):
            r.observar(self._obs(self.NOMES), -100 + i)
        return r

    def test_saida_e_atribuida_a_quem_saiu_mesmo_com_a_party_reordenada(self):
        from l2scanner.rastreador import TipoDeEvento

        r = self._rastreador_aquecido()

        # o caso exato: TioMad sai e a party vira [Korzis, J4guar, Kaus]
        eventos = []
        for i in range(6):
            eventos.extend(
                r.observar(self._obs(["Korzis", "J4guar", "Kaus", None]), 10 + i)
            )

        saidas = [e.membro for e in eventos if e.tipo is TipoDeEvento.SAIU]
        assert saidas == ["TioMad"], (
            "quem saiu foi o TioMad; atribuir a outro manda a party socorrer "
            "a pessoa errada e ninguem desconfia"
        )

    def test_reordenar_sozinho_nao_gera_evento_nenhum(self):
        """Trocar de posicao nao e sair nem entrar."""
        r = self._rastreador_aquecido()

        eventos = []
        for i in range(10):
            eventos.extend(
                r.observar(self._obs(["Korzis", "TioMad", "Kaus", "J4guar"]), 10 + i)
            )

        assert eventos == []

    def test_morte_apos_reordenacao_nomeia_o_membro_certo(self):
        from l2scanner.rastreador import TipoDeEvento

        r = self._rastreador_aquecido()

        # party reordena e, depois, o J4guar morre na linha 1
        for i in range(6):
            r.observar(self._obs(["Korzis", "J4guar", "Kaus", None]), 10 + i)

        eventos = []
        for i in range(6):
            eventos.extend(
                r.observar(
                    self._obs(
                        ["Korzis", "J4guar", "Kaus", None], hp={"J4guar": 0.0}
                    ),
                    30 + i,
                )
            )

        mortes = [e.membro for e in eventos if e.tipo is TipoDeEvento.MORREU]
        assert mortes == ["J4guar"]

    def test_sem_reconhecimento_o_nome_ainda_vem_da_lista(self):
        """Degrada em vez de mostrar a chave interna.

        Sem nome reconhecido o estado e chaveado por posicao — pior, mas o
        alerta ainda diz um nome de gente, nao "#linha2".
        """
        from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento
        from l2scanner.visao import LeituraDeLinha, Observacao

        def sem_nome(hps):
            linhas = [
                LeituraDeLinha(i, EstadoDaLinha.COM_MEMBRO, hp, 1.0)
                for i, hp in enumerate(hps)
            ]
            return Observacao(0, True, tuple(linhas))

        r = Rastreador(
            nomes=list(self.NOMES), ajustes=Ajustes(confirmacoes_para_morte=2)
        )
        for i in range(15):
            r.observar(sem_nome([1.0, 1.0, 1.0, 1.0]), -100 + i)

        eventos = []
        for i in range(4):
            eventos.extend(r.observar(sem_nome([1.0, 1.0, 0.0, 1.0]), 10 + i))

        mortes = [e.membro for e in eventos if e.tipo is TipoDeEvento.MORREU]
        assert mortes == ["TioMad"]
        assert not any("#linha" in (e.membro or "") for e in eventos)


class TestLiderDaParty:
    """O lider da party quebrava o reconhecimento de duas formas.

    Aconteceu de verdade: o Korzis virou lider e o scanner parou de reconhece-lo,
    mostrando "J4guar" duas vezes no console.

    1. O jogo pinta o nome do lider de AMARELO. A mascara exigia "claro E
       dessaturado", e o amarelo tem saturacao 118 — era rejeitado inteiro.
    2. O lider ganha uma COROA antes do nome, que empurra o texto para a
       direita. Comparar posicao a posicao nao sobrevive a esse deslocamento.

    A correcao foi mascara so por brilho (o brilho separa texto de terreno com
    folga: 206 contra 83) e casamento deslizante.
    """

    PASTA = FIXTURES

    @pytest.fixture
    def calibracao(self):
        return Calibracao.carregar(self.PASTA / "calibracao.json")

    @pytest.fixture
    def frame_com_lider(self):
        px = cv2.imread(str(self.PASTA / "party_com_lider.png"), cv2.IMREAD_COLOR)
        assert px is not None
        return Frame(pixels=px, indice=0, saude=SaudeDoFrame.OK)

    def test_o_lider_e_reconhecido(self, frame_com_lider, calibracao):
        obs = extrair(frame_com_lider, calibracao)
        nomes = [l.nome for l in obs.linhas[:4]]
        assert nomes == calibracao.nomes, (
            "o lider tem nome amarelo e coroa; se o reconhecimento nao "
            "aguentar isso, ele some da lista e outro membro aparece duplicado"
        )

    def test_ninguem_aparece_duplicado(self, frame_com_lider, calibracao):
        """O sintoma que o usuario viu: o mesmo nome em duas linhas."""
        obs = extrair(frame_com_lider, calibracao)
        reconhecidos = [l.nome for l in obs.linhas if l.nome]
        assert len(reconhecidos) == len(set(reconhecidos))

    def test_texto_amarelo_entra_na_mascara(self):
        """Amarelo do lider: claro, mas saturado."""
        import numpy as np

        amarelo = np.full((10, 10, 3), (40, 200, 220), dtype=np.uint8)
        assert mascara_de_texto(amarelo).all(), (
            "o nome do lider e amarelo — rejeita-lo apaga o membro do "
            "reconhecimento inteiro"
        )

    def test_terreno_continua_fora_da_mascara(self):
        """A regra ficou mais permissiva, mas nao pode deixar o cenario entrar."""
        import numpy as np

        # verde de grama medido na tela real: V~83
        grama = np.full((10, 10, 3), (70, 110, 75), dtype=np.uint8)
        assert not mascara_de_texto(grama).any()
