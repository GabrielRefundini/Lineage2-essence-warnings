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
    LIMIAR_DO_ORNAMENTO,
    MARGEM_DO_ORNAMENTO,
    Assinatura,
    criar_assinatura,
    Casamento,
    _inicio_do_nome_apos_ornamento,
    _pontuar,
    _primeira_coluna_com_texto,
    _reancorar_apos_ornamento,
    _pontuar_com_ornamento,
    _segundo_passe_do_ornamento,
    identificar,
    identificar_linhas,
    mascara_de_texto,
)
from l2scanner.visao import EstadoDaLinha, _recorte_do_nome, extrair

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
    """Reordena as linhas da party window, simulando a party reorganizada.

    Uma `ordem` mais curta que 4 significa que a party ENCOLHEU: as linhas
    sobrantes sao apagadas, como o jogo faz. Deixa-las com o conteudo antigo
    criaria um membro em duas linhas ao mesmo tempo — um estado que nao existe
    no jogo e que so confundiria o teste.
    """
    lay = cal.layout
    novo = px.copy()

    def topo_de(i: int) -> int:
        return lay.icone_y + i * lay.passo + lay.nome_dy - 4

    blocos = [px[topo_de(i) : topo_de(i) + lay.passo].copy() for i in range(4)]
    for destino, origem in enumerate(ordem):
        inicio = topo_de(destino)
        novo[inicio : inicio + lay.passo] = blocos[origem]

    for vazia in range(len(ordem), 4):
        inicio = topo_de(vazia)
        # cinza escuro e liso: sem contraste, sem pixels claros. E como uma
        # posicao sem membro se parece para o detector de icone.
        novo[inicio : inicio + lay.passo] = 30
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


class TestPontuacaoNoAlinhamentoCalibrado:
    """Correcao B.

    Houve uma tentativa de tolerar a coroa do lider deslizando o casamento:
    `matchTemplate(...).max()` sobre uma regiao de busca alargada. Cada
    deslocamento e uma chance INDEPENDENTE de um nome errado achar um
    alinhamento sortudo e passar do limiar — e eram 25 deles.

    Medido nesta mesma fixture, alinhado -> maximo deslizante:

        casamentos CORRETOS   +0.000 em 8 de 8 (vencem sempre no alinhamento)
        casamentos ERRADOS    ate +0.373, levando o pior errado a 0.586

    Com o limiar em 0.75, o deslize reduzia a folga de 0.379 para 0.164. Junte
    um recorte contaminado (que derruba o casamento certo para ~0.43) e a
    ultrapassagem acontece — foi o que produziu o "entra e sai" em looping.
    """

    LIMITE_DO_ERRADO = 0.50

    def test_nome_errado_fica_longe_do_limiar(self, pixels, calibracao):
        """A regressao mede a FOLGA, nao so o veredito.

        Um teste que so olhasse o nome reconhecido continuaria verde com o
        deslize ligado — ele passava, so que por pouco. O que quebrou em
        producao foi a margem, entao e a margem que precisa ser vigiada.
        """
        piores = []
        for indice in range(4):
            recorte = _recorte_do_nome(pixels, calibracao, indice)
            assert recorte is not None
            pontos = _pontuar(recorte, calibracao.assinaturas)
            assert pontos is not None
            certo = calibracao.nomes[indice]
            piores += [
                (v, indice, a.nome)
                for a, v in zip(calibracao.assinaturas, pontos)
                if a.nome != certo
            ]

        pior, indice, nome = max(piores)
        assert pior <= self.LIMITE_DO_ERRADO, (
            f"linha {indice} pontuou {pior:.3f} contra a assinatura do {nome}. "
            f"Com o casamento deslizante isto chegava a 0.586, a 0.164 do "
            f"limiar de {LIMIAR_DE_CASAMENTO}"
        )

    def test_o_casamento_certo_nao_perde_nada_sem_o_deslize(
        self, pixels, calibracao
    ):
        """O deslize custava caro e nao comprava nada: +0.000 em 8 de 8."""
        for indice in range(4):
            recorte = _recorte_do_nome(pixels, calibracao, indice)
            pontos = _pontuar(recorte, calibracao.assinaturas)
            certo = dict(zip([a.nome for a in calibracao.assinaturas], pontos))
            assert certo[calibracao.nomes[indice]] > 0.90


class TestOrdemDaParty:
    """O motivo de tudo isto existir."""

    @pytest.mark.parametrize(
        "descricao,ordem",
        [
            ("ordem original", [0, 1, 2, 3]),
            ("dois membros trocados", [0, 3, 2, 1]),
            ("ordem invertida", [3, 2, 1, 0]),
            ("primeiro saiu, os outros sobem", [1, 2, 3]),
        ],
    )
    def test_o_nome_segue_o_membro_e_nao_a_linha(
        self, pixels, calibracao, descricao, ordem
    ):
        reordenado = remontar(pixels, calibracao, ordem)
        obs = extrair(
            Frame(pixels=reordenado, indice=0, saude=SaudeDoFrame.OK), calibracao
        )

        reconhecidos = [l.nome for l in obs.linhas[: len(ordem)]]
        esperados = [calibracao.nomes[i] for i in ordem]

        assert reconhecidos == esperados, (
            f"{descricao}: o nome ficou preso a posicao da linha em vez de "
            f"seguir o membro — foi exatamente isto que a identidade visual "
            f"veio resolver"
        )

    def test_a_mesma_pessoa_nunca_ocupa_duas_linhas(self, pixels, calibracao):
        """Correcao A, contra um frame que contem o nome do TioMad duas vezes.

        Este frame nao existe no jogo — duas linhas sao duas pessoas. Mas era
        exatamente o que o reconhecimento PRODUZIA quando decidia linha a linha,
        e o custo era alto: o membro roubado sumia do conjunto de identidades e
        o rastreador anunciava que ele tinha saido da party.

        A resposta certa nao e "reconhecer os dois", e sim dar o nome a UMA
        linha e admitir "nao sei" na outra.
        """
        duplicado = remontar(pixels, calibracao, [0, 1, 3, 3])
        obs = extrair(
            Frame(pixels=duplicado, indice=0, saude=SaudeDoFrame.OK), calibracao
        )

        reconhecidos = [l.nome for l in obs.linhas if l.nome]
        assert len(reconhecidos) == len(set(reconhecidos)), (
            f"a mesma assinatura foi usada duas vezes: {reconhecidos}"
        )
        assert "TioMad" in reconhecidos

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


class TestMembroQueViraLider:
    """O caso que identidade.py declarava sem cobertura — e que aconteceu.

    Em 2026-08-25 o usuario era LIDER quando calibrou. O lider nao aparece na
    propria party window, entao NENHUMA das quatro assinaturas gravadas tem
    coroa. As 10:03 ele entrou numa party alheia, e o membro que passou a ocupar
    a linha do lider virou "Membro 1" — e ficou assim por DUAS HORAS, incluindo
    um reinicio do scanner (logs/scanner.log 10:03:24 a 11:59, com o reinicio as
    10:46:57). A assinatura gravada nao muda, entao esperar nao resolve.

    Medido com os pixels reais da coroa: o membro casa 0.266 contra a PROPRIA
    assinatura enquanto os outros tres da mesma party casam 0.960 / 0.957 /
    0.992. `_correlacionar` pontua no alinhamento calibrado, e a coroa empurra o
    texto 10 px para a direita — 1 px ja bastaria (medido: 1.000 -> 0.24).

    A fixture ajuda: nela o Korzis E o lider, entao os pixels da coroa sao
    REAIS. O que estes testes fabricam e o outro lado — a assinatura dele como
    teria sido gravada ANTES de ele virar lider.
    """

    PASTA = FIXTURES
    DESVIO_DA_COROA = 10  # medido: coroa em 0..5, lacuna de 4, nome a partir de 10

    @pytest.fixture
    def calibracao(self):
        return Calibracao.carregar(self.PASTA / "calibracao.json")

    @pytest.fixture
    def recortes(self, pixels, calibracao):
        return {i: _recorte_do_nome(pixels, calibracao, i) for i in range(4)}

    def assinatura_sem_coroa(self, recortes, margem: int = 0) -> Assinatura:
        """O Korzis como teria sido calibrado ANTES de virar lider.

        Tira a coroa do recorte real e traz o nome para `margem`, que e onde uma
        assinatura de verdade comeca — medido, entre a coluna 0 e a 1 conforme o
        nome.
        """
        com_coroa = mascara_de_texto(recortes[0])
        corpo = com_coroa[:, self.DESVIO_DA_COROA :]
        sem_coroa = np.zeros_like(com_coroa)
        largura = min(corpo.shape[1], sem_coroa.shape[1] - margem)
        sem_coroa[:, margem : margem + largura] = corpo[:, :largura]
        return Assinatura(nome="Korzis", mascara=sem_coroa.astype(np.uint8))

    def test_o_membro_que_virou_lider_volta_a_ser_reconhecido(
        self, recortes, calibracao
    ):
        """A reproducao. Antes da correcao: None, com confianca 0.266."""
        assinaturas = [self.assinatura_sem_coroa(recortes)] + list(
            calibracao.assinaturas[1:]
        )

        res = identificar_linhas(recortes, assinaturas)

        assert [res[i].nome for i in range(4)] == calibracao.nomes, (
            "o membro calibrado sem coroa que virou lider tem que voltar. "
            "Sem isso ele fica 'Membro N' para sempre, e — pela limitacao "
            "travada em TestUmaSaidaRealNaoViraVariosAlertas — a saida real "
            "dele passa calada."
        )

    @pytest.mark.parametrize("margem", [0, 1, 2])
    def test_o_alinhamento_respeita_a_margem_da_propria_assinatura(
        self, recortes, calibracao, margem
    ):
        """Vizinhos de fronteira: assinaturas reais comecam na coluna 0 OU 1.

        Reancorar na coluna 0 "e o que parece obvio" e esta errado: 1 px de erro
        derruba a correlacao de 1.000 para 0.24. O deslocamento tem que ser
        medido contra a primeira coluna DA ASSINATURA, nao contra a origem.
        """
        assinaturas = [self.assinatura_sem_coroa(recortes, margem)] + list(
            calibracao.assinaturas[1:]
        )

        res = identificar_linhas(recortes, assinaturas)

        assert res[0].nome == "Korzis", f"quebrou com a assinatura na coluna {margem}"

    def test_lider_de_fora_da_lista_nao_ganha_nome_emprestado(
        self, recortes, calibracao
    ):
        """A trava que importa: um estranho de coroa continua sem nome.

        Parties de verdade tem gente que nao esta na calibracao. Se o segundo
        passe emprestasse um nome para eles, teriamos trocado um silencio por
        uma mentira plausivel — o pior defeito possivel neste projeto.
        """
        sem_o_korzis = list(calibracao.assinaturas[1:])

        res = identificar_linhas(recortes, sem_o_korzis)

        assert res[0].nome is None
        assert [res[i].nome for i in range(1, 4)] == calibracao.nomes[1:]

    def test_linha_sem_ornamento_nem_entra_no_segundo_passe(
        self, recortes, calibracao
    ):
        """A trava que faz quase todo o trabalho, e de graca.

        Um nome sem coroa e UM bloco de texto — medido em 9 de 10 assinaturas
        reais de 3 calibracoes. Sem lacuna, sem segundo passe.
        """
        for i in (1, 2, 3):
            mascara = mascara_de_texto(recortes[i])
            assert _pontuar_com_ornamento(mascara, calibracao.assinaturas) is None, (
                f"a linha {i} nao tem coroa e nao podia ser reancorada"
            )

    def test_a_linha_do_lider_tem_a_lacuna_que_delata_a_coroa(self, recortes):
        """O discriminador, medido no pixel real: coroa 0..5, lacuna 4, nome 10."""
        mascara = mascara_de_texto(recortes[0])

        assert _inicio_do_nome_apos_ornamento(mascara) == self.DESVIO_DA_COROA

    def test_o_segundo_passe_nao_mexe_no_que_o_primeiro_resolveu(
        self, recortes, calibracao
    ):
        """Controle: com a calibracao normal, nada pode mudar.

        O segundo passe e estritamente aditivo. Se ele conseguisse alterar uma
        linha ja resolvida, teria virado exatamente o casamento deslizante que
        foi removido por produzir o bug do "entra e sai".
        """
        res = identificar_linhas(recortes, calibracao.assinaturas)

        assert [res[i].nome for i in range(4)] == calibracao.nomes
        assert all(res[i].confianca > 0.90 for i in range(4))

    def test_o_segundo_passe_nunca_RENOMEIA_uma_linha_ja_resolvida(
        self, recortes, calibracao
    ):
        """"Estritamente aditivo" e a trava principal, entao ela tem teste.

        Aqui a linha 0 ja e resolvida pelo primeiro passe (0.946), e existe uma
        assinatura de OUTRO nome que casaria quase perfeito se a mesma linha
        fosse reavaliada com o desconto da coroa. O segundo passe nao pode nem
        olhar para ela.

        Se pudesse, ele teria virado o casamento deslizante com outro nome: uma
        segunda chance de trocar um nome CERTO por um errado, que e o defeito
        que este projeto trata como o pior de todos.
        """
        intruso = Assinatura(
            nome="Intruso", mascara=self.assinatura_sem_coroa(recortes).mascara
        )
        assinaturas = list(calibracao.assinaturas) + [intruso]

        res = identificar_linhas(recortes, assinaturas)

        assert res[0].nome == "Korzis", (
            f"a linha 0 ja estava resolvida e virou {res[0].nome!r} — o segundo "
            f"passe so pode preencher vazio, nunca reescrever"
        )
        assert [res[i].nome for i in range(4)] == calibracao.nomes

    def test_assinatura_ja_consumida_nao_volta_para_a_mesa(
        self, recortes, calibracao
    ):
        """Unicidade tambem no segundo passe: duas linhas sao duas pessoas.

        Foi o mesmo nome em duas linhas que rendeu 52 eventos falsos em 25
        minutos (ver o docstring de `identificar_linhas`). O segundo passe so
        pode pescar no que sobrou — se ele pudesse reusar uma assinatura ja
        consumida, teria reaberto exatamente aquele buraco.

        Testado direto na funcao porque e ai que a invariante mora: mesma linha,
        mesma assinatura, e a UNICA diferenca e ela estar ou nao disponivel.
        """
        assinaturas = [self.assinatura_sem_coroa(recortes)] + list(
            calibracao.assinaturas[1:]
        )
        mascaras = {i: mascara_de_texto(recortes[i]) for i in range(4)}

        def repescar(assinaturas_livres):
            resultado = {i: Casamento(None, 0.0) for i in range(4)}
            _segundo_passe_do_ornamento(
                mascaras, assinaturas, resultado, {0}, assinaturas_livres
            )
            return resultado[0].nome

        assert repescar({0, 1, 2, 3}) == "Korzis", "com a assinatura livre, pesca"
        assert repescar({1, 2, 3}) is None, (
            "a assinatura do Korzis ja foi consumida por outra linha — a linha "
            "do lider tem que ficar sem nome, e nao pegar o nome de outro"
        )
        assert repescar(set()) is None, "sem assinatura sobrando, nao ha o que pescar"

    def test_so_reancora_para_a_DIREITA(self, recortes, calibracao):
        """Um ornamento empurra o texto para a direita. Nunca para a esquerda.

        Sem esta trava, uma assinatura que comeca depois do inicio do nome no
        recorte seria testada tambem num alinhamento invertido — um alinhamento
        que a coroa nao produz, e portanto pura chance extra de erro. E o mesmo
        raciocinio que tirou o casamento deslizante: cada alinhamento a mais e
        uma chance a mais de um nome errado dar sorte.
        """
        mascara = mascara_de_texto(recortes[0])
        assinatura = calibracao.assinaturas[1]
        coluna = _primeira_coluna_com_texto(assinatura.mascara)

        para_a_direita = _reancorar_apos_ornamento(
            mascara, coluna + 5, assinatura
        )
        na_mesma_coluna = _reancorar_apos_ornamento(mascara, coluna, assinatura)
        para_a_esquerda = _reancorar_apos_ornamento(
            mascara, max(coluna - 3, 0), assinatura
        )

        assert para_a_direita is not None
        assert na_mesma_coluna is None, "deslocamento zero nao e ornamento"
        assert para_a_esquerda is None, "a coroa nunca puxa o nome para tras"

    def test_a_coroa_e_a_PRIMEIRA_lacuna_e_nao_qualquer_uma(self):
        """Um nome largo pode ter lacunas internas. A coroa vem antes de todas.

        Pegar a ultima lacuna reancoraria no meio do nome — um alinhamento que
        casa com pedaco nenhum, e que so serve para dar chances extras.
        """
        mascara = np.zeros((20, 100), dtype=np.uint8)
        mascara[5:15, 0:4] = 1  # o ornamento
        mascara[5:15, 12:18] = 1  # comeco do nome, apos a lacuna
        mascara[5:15, 26:32] = 1  # lacuna INTERNA do nome, maior ainda

        assert _inicio_do_nome_apos_ornamento(mascara) == 12

    def test_pontuacao_fraca_nao_passa_so_por_estar_sozinha(
        self, recortes, calibracao
    ):
        """O limiar tem que barrar sozinho, sem depender da margem.

        Um candidato unico tem margem enorme por construcao — nao ha segundo
        para disputar. Se o limiar nao barrasse, "e o unico parecido" viraria
        prova suficiente, e o segundo passe passaria a chutar sempre que
        houvesse exatamente uma assinatura sobrando.
        """
        gerador = np.random.default_rng(5)
        mascara_boa = self.assinatura_sem_coroa(recortes).mascara
        # meio nome apagado: casa por volta de 0.70, longe do limiar de 0.85 e
        # ainda assim muito acima de qualquer concorrente
        meio_apagado = mascara_boa.copy()
        acesos = np.argwhere(meio_apagado > 0)
        escolhidos = gerador.choice(len(acesos), len(acesos) // 2, replace=False)
        for y, x in acesos[escolhidos]:
            meio_apagado[y, x] = 0

        assinaturas = [Assinatura(nome="Korzis", mascara=meio_apagado)]
        (pontuou,) = _pontuar_com_ornamento(
            mascara_de_texto(recortes[0]), assinaturas
        )

        # o cenario so vale se a margem estiver satisfeita: candidato unico, sem
        # segundo para disputar. Quem precisa barrar aqui e o LIMIAR.
        assert pontuou - 0.0 >= MARGEM_DO_ORNAMENTO, "margem folgada, como o teste exige"
        assert pontuou < LIMIAR_DO_ORNAMENTO, f"pontuou {pontuou:.3f}, refaca o cenario"

        res = identificar_linhas({0: recortes[0]}, assinaturas)

        assert res[0].nome is None, (
            f"casou {pontuou:.3f} sendo o unico candidato — o limiar de "
            f"{LIMIAR_DO_ORNAMENTO} tem que barrar por conta propria"
        )

    def test_dois_candidatos_empatados_nao_viram_cara_ou_coroa(
        self, recortes, calibracao
    ):
        """A margem tem que barrar sozinha, sem depender do limiar.

        Duas assinaturas praticamente identicas pontuam altissimo as duas. Sem a
        margem, o segundo passe escolheria no desempate por indice — ou seja,
        daria um nome com confianca 1.000 numa disputa que era um cara ou coroa.
        E o pior defeito possivel aqui: uma mentira que parece certeza.
        """
        boa = self.assinatura_sem_coroa(recortes).mascara
        gemea = boa.copy()
        assinaturas = [
            Assinatura(nome="Korzis", mascara=boa),
            Assinatura(nome="Kaus", mascara=gemea),
        ]

        pontos = _pontuar_com_ornamento(mascara_de_texto(recortes[0]), assinaturas)

        # o cenario so vale se o LIMIAR tiver sido cumprido pelos dois: quem
        # precisa barrar aqui e a MARGEM.
        assert min(pontos) >= LIMIAR_DO_ORNAMENTO, f"pontos {pontos}"
        assert max(pontos) - min(pontos) < MARGEM_DO_ORNAMENTO

        res = identificar_linhas({0: recortes[0]}, assinaturas)

        assert res[0].nome is None, (
            f"escolheu {res[0].nome!r} entre duas assinaturas identicas — a "
            f"margem de {MARGEM_DO_ORNAMENTO} tem que recusar o empate"
        )

    def test_com_o_recorte_sujo_o_lider_some_mas_nunca_vira_outro(
        self, recortes, calibracao
    ):
        """O modo de falha certo e o silencio, nao o nome errado.

        Cenario claro invadindo o recorte degrada o casamento do lider ate ele
        cair. O que NAO pode acontecer, em nenhum nivel de ruido, e a linha
        receber o nome de outra pessoa.
        """
        assinaturas = [self.assinatura_sem_coroa(recortes)] + list(
            calibracao.assinaturas[1:]
        )
        gerador = np.random.default_rng(11)

        for ruido in (5, 10, 20, 30, 60):
            for _ in range(20):
                sujo = recortes[0].copy()
                ys = gerador.integers(0, sujo.shape[0], ruido)
                xs = gerador.integers(0, sujo.shape[1], ruido)
                sujo[ys, xs] = 255

                res = identificar_linhas({**recortes, 0: sujo}, assinaturas)

                assert res[0].nome in (None, "Korzis"), (
                    f"com {ruido}px de ruido a linha do lider virou "
                    f"{res[0].nome!r} — trocamos silencio por mentira"
                )


class TestPiscarDeReconhecimento:
    """Um frame sem reconhecer nao pode virar "fulano saiu da party".

    Aconteceu de verdade em 2026-08-24: o reconhecimento falhou num frame
    durante a reaquisicao e o scanner anunciou "Korzis: saiu da party" com o
    Korzis na tela.

    Com o estado chaveado por identidade, uma linha nao reconhecida vira
    `#linha0` e o "Korzis" some do conjunto de presentes — o rastreador conclui
    que ele saiu. A correcao: se alguma linha OCUPADA nao foi reconhecida, nao
    da para afirmar que ninguem saiu, porque o membro "sumido" pode ser
    exatamente quem esta nela.
    """

    NOMES = ["Korzis", "J4guar", "Kaus", "TioMad"]

    def _obs(self, nomes_por_linha):
        from l2scanner.visao import LeituraDeLinha, Observacao

        linhas = []
        for i, nome in enumerate(nomes_por_linha):
            if nome is None:
                linhas.append(LeituraDeLinha(i, EstadoDaLinha.VAZIA, None, None))
            else:
                # string vazia = linha ocupada, mas nao reconhecida
                reconhecido = nome or None
                linhas.append(
                    LeituraDeLinha(
                        i,
                        EstadoDaLinha.COM_MEMBRO,
                        1.0,
                        1.0,
                        nome=reconhecido,
                        confianca_do_nome=0.98 if reconhecido else 0.0,
                    )
                )
        return Observacao(0, True, tuple(linhas))

    def _aquecido(self):
        from l2scanner.rastreador import Ajustes, Rastreador

        r = Rastreador(
            nomes=list(self.NOMES), ajustes=Ajustes(confirmacoes_para_saida=3)
        )
        for i in range(15):
            r.observar(self._obs(self.NOMES), -100 + i)
        return r

    def test_linha_nao_reconhecida_nao_gera_saida(self):
        from l2scanner.rastreador import TipoDeEvento

        r = self._aquecido()

        # o Korzis continua na tela, mas a imagem falha em reconhece-lo
        eventos = []
        for i in range(10):
            eventos.extend(
                r.observar(self._obs(["", "J4guar", "Kaus", "TioMad"]), 10 + i)
            )

        saidas = [e for e in eventos if e.tipo is TipoDeEvento.SAIU]
        assert saidas == [], (
            "o Korzis esta na tela; falhar em reconhece-lo nao pode virar "
            "um anuncio de que ele saiu da party"
        )

    def test_saida_de_verdade_ainda_e_detectada(self):
        """A protecao nao pode cegar o scanner para saidas reais."""
        from l2scanner.rastreador import TipoDeEvento

        r = self._aquecido()

        eventos = []
        for i in range(10):
            eventos.extend(
                r.observar(self._obs(["Korzis", "J4guar", "Kaus", None]), 10 + i)
            )

        saidas = [e.membro for e in eventos if e.tipo is TipoDeEvento.SAIU]
        assert saidas == ["TioMad"]

    def test_reconhecimento_volta_e_nada_e_anunciado(self):
        """Piscar e voltar nao deixa rastro."""
        r = self._aquecido()

        eventos = []
        for i in range(4):
            eventos.extend(
                r.observar(self._obs(["", "J4guar", "Kaus", "TioMad"]), 10 + i)
            )
        for i in range(6):
            eventos.extend(r.observar(self._obs(self.NOMES), 20 + i))

        assert eventos == []


class TestLinhaDesconhecidaNaoRoubaNome:
    """Uma linha nao reconhecida jamais pode usar o nome de outra pessoa.

    A lista `nomes` do config e ordenada por POSICAO, e posicao nao e
    identidade. Com identidade visual em jogo, usar `nomes[1]` para uma linha
    desconhecida faz o alerta sair com o nome de quem esta vivo noutra linha.

    Quase aconteceu: a linha 1, nao reconhecida e com HP ZERADO, estava
    rotulada "Korzis" enquanto o Korzis real aparecia vivo na linha 0. Faltava
    um debounce para anunciar a morte de quem estava vivo.

    "Membro 2" e feio. Anunciar a morte da pessoa errada e pior.
    """

    def _obs(self, pares):
        from l2scanner.visao import LeituraDeLinha, Observacao

        linhas = []
        for i, (nome, hp) in enumerate(pares):
            linhas.append(
                LeituraDeLinha(
                    i,
                    EstadoDaLinha.COM_MEMBRO,
                    hp,
                    1.0,
                    nome=nome,
                    confianca_do_nome=0.98 if nome else 0.0,
                )
            )
        return Observacao(0, True, tuple(linhas))

    def test_morte_em_linha_desconhecida_nao_usa_nome_de_outro(self):
        from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento

        r = Rastreador(
            nomes=["Kaus", "Korzis"],
            assinaturas_configuradas=True,
            ajustes=Ajustes(confirmacoes_para_morte=2),
        )
        # linha 0 = Korzis reconhecido e vivo; linha 1 = desconhecida, HP zerado
        for i in range(15):
            r.observar(self._obs([("Korzis", 1.0), (None, 1.0)]), -100 + i)

        eventos = []
        for i in range(5):
            eventos.extend(r.observar(self._obs([("Korzis", 1.0), (None, 0.0)]), 10 + i))

        mortes = [e.membro for e in eventos if e.tipo is TipoDeEvento.MORREU]
        assert mortes, "a morte na linha desconhecida precisa ser reportada"
        assert "Korzis" not in mortes, (
            "o Korzis esta VIVO na linha 0; a linha 1 nao pode usar o nome dele"
        )
        assert mortes == ["Membro 2"]

    def test_sem_assinaturas_o_nome_por_posicao_ainda_vale(self):
        """Sem identidade visual, o nome por posicao e a unica informacao."""
        from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento

        r = Rastreador(
            nomes=["Kaus", "Korzis"],
            assinaturas_configuradas=False,
            ajustes=Ajustes(confirmacoes_para_morte=2),
        )
        for i in range(15):
            r.observar(self._obs([(None, 1.0), (None, 1.0)]), -100 + i)

        eventos = []
        for i in range(5):
            eventos.extend(r.observar(self._obs([(None, 1.0), (None, 0.0)]), 10 + i))

        mortes = [e.membro for e in eventos if e.tipo is TipoDeEvento.MORREU]
        assert mortes == ["Korzis"]


class TestPassarAReconhecerNaoEEntrar:
    """Reconhecer alguem que ja estava la nao e uma entrada.

    Visto ao vivo: no arranque de uma sessao com a party PARADA, o scanner
    anunciou "Kaus entrou na party" — o Kaus estava na party o tempo todo, so
    nao vinha sendo reconhecido.

    Uma identidade nova aparece por dois motivos bem diferentes: alguem entrou
    (a party window ganha uma linha) ou o reconhecimento passou a funcionar
    (a contagem de linhas nao muda). O sinal que separa os dois e o mesmo que
    separa saida real de falha de reconhecimento — a janela crescer ou encolher.
    """

    def _obs(self, nomes):
        from l2scanner.visao import LeituraDeLinha, Observacao

        linhas = tuple(
            LeituraDeLinha(
                i,
                EstadoDaLinha.COM_MEMBRO,
                1.0,
                1.0,
                nome=n,
                confianca_do_nome=0.98 if n else 0.0,
            )
            for i, n in enumerate(nomes)
        )
        return Observacao(0, True, linhas)

    def test_reconhecer_alguem_que_ja_estava_la_nao_gera_entrada(self):
        from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento

        r = Rastreador(
            nomes=["Kaus"],
            assinaturas_configuradas=True,
            ajustes=Ajustes(confirmacoes_para_entrada=3),
        )
        # 4 linhas o tempo todo; no comeco nenhuma e reconhecida
        for i in range(15):
            r.observar(self._obs([None, None, None, None]), -100 + i)

        # o reconhecimento passa a funcionar para a linha 3 — mesma contagem
        eventos = []
        for i in range(10):
            eventos.extend(r.observar(self._obs([None, None, None, "Kaus"]), 10 + i))

        entradas = [e for e in eventos if e.tipo is TipoDeEvento.ENTROU]
        assert entradas == [], (
            "a party continuou com 4 linhas; o Kaus so passou a ser "
            "reconhecido, nao entrou"
        )

    def test_entrada_de_verdade_continua_sendo_detectada(self):
        """A party CRESCE quando alguem entra — esse sinal precisa sobreviver."""
        from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento

        r = Rastreador(
            nomes=["Kaus", "Korzis"],
            assinaturas_configuradas=True,
            ajustes=Ajustes(confirmacoes_para_entrada=3),
        )
        for i in range(15):
            r.observar(self._obs(["Kaus"]), -100 + i)

        eventos = []
        for i in range(6):
            eventos.extend(r.observar(self._obs(["Kaus", "Korzis"]), 10 + i))

        entradas = [e.membro for e in eventos if e.tipo is TipoDeEvento.ENTROU]
        assert entradas == ["Korzis"]


class TestArranqueNaoInventaEntrada:
    """A linha de base da contagem de linhas nao pode nascer em ZERO.

    Visto ao vivo as 18:18: a party estava fixa desde antes do scanner ligar e
    mesmo assim saiu "TioMad entrou na party" 7 segundos depois do arranque,
    entregue no WhatsApp.

    O mecanismo: `_ultima_contagem_estavel` comecava em 0 e so era escrito no
    fim de `_processar`. No PRIMEIRO frame rastreado, `linhas_agora > 0` era
    verdade para todo mundo, entao `apareceu_com_crescimento` era gravado True
    para cada membro. Esse flag e guardado de proposito (a entrada so confirma
    depois de N leituras), entao o valor errado virava permanente.

    Os membros reconhecidos desde o primeiro frame escapavam porque confirmavam
    juntos, enquanto `_aquecido` ainda era False. Bastava UM frame de falha de
    reconhecimento para atrasar alguem para o lado errado dessa porta.

    Sem linha de base nao existe crescimento. O primeiro frame so a estabelece.
    """

    NOMES = ["Korzis", "J4guar", "TioMad", "Kaus"]

    def _obs(self, nomes):
        from l2scanner.visao import LeituraDeLinha, Observacao

        linhas = tuple(
            LeituraDeLinha(
                i,
                EstadoDaLinha.COM_MEMBRO,
                1.0,
                1.0,
                nome=n,
                confianca_do_nome=0.98 if n else 0.0,
            )
            for i, n in enumerate(nomes)
        )
        return Observacao(0, True, linhas, hp_proprio=1.0)

    def _novo(self):
        from l2scanner.rastreador import Ajustes, Rastreador

        return Rastreador(
            nomes=list(self.NOMES),
            nome_proprio="Yazalaque",
            assinaturas_configuradas=True,
            nomes_reservados=set(self.NOMES),
            ajustes=Ajustes(confirmacoes_para_entrada=3),
        )

    @pytest.mark.parametrize("frame_da_piscada", [4, 5, 6, 7])
    def test_piscada_no_arranque_nao_vira_entrada(self, frame_da_piscada):
        """Party PARADA em 4 linhas. Um frame sem reconhecer o TioMad.

        A contagem de linhas nunca muda — ninguem entrou. O parametro varre o
        atraso, porque o bug so aparecia quando a confirmacao do membro
        atrasado cruzava o instante em que `_aquecido` virava True.
        """
        from l2scanner.rastreador import TipoDeEvento

        r = self._novo()
        eventos = []
        for n in range(16):
            nomes = list(self.NOMES)
            if n == frame_da_piscada:
                nomes[2] = None  # linha OCUPADA, so nao reconhecida
            eventos.extend(r.observar(self._obs(nomes), float(n)))

        entradas = [
            f"{e.membro}" for e in eventos if e.tipo is TipoDeEvento.ENTROU
        ]
        assert entradas == [], (
            f"a party window teve 4 linhas em 100% dos frames; um frame de "
            f"falha de reconhecimento nao pode virar entrada. Saiu: {entradas}"
        )

    def test_entrada_de_verdade_no_arranque_ainda_funciona(self):
        """A linha de base nao pode DESLIGAR a deteccao — so atrasa um frame."""
        from l2scanner.rastreador import TipoDeEvento

        r = self._novo()
        for n in range(12):
            r.observar(self._obs(self.NOMES[:3]), float(n))

        eventos = []
        for n in range(8):
            eventos.extend(r.observar(self._obs(self.NOMES), 100.0 + n))

        entradas = [e.membro for e in eventos if e.tipo is TipoDeEvento.ENTROU]
        assert entradas == ["Kaus"], (
            "a party cresceu de 3 para 4 linhas — isso e uma entrada de verdade"
        )


class TestUmaSaidaRealNaoViraVariosAlertas:
    """A lei de conservacao da party window.

    O falso positivo de 2026-08-25, entregue no WhatsApp:

        10:17:32  Membro 1  Membro 2  Membro 3  Korzis     (4 linhas)
        10:17:44  J4GUAR SAIU DA PARTY
        10:17:44  KAUS   SAIU DA PARTY
        10:17:44  KORZIS SAIU DA PARTY
        10:18:02  Membro 1  Membro 2  Membro 3            (3 linhas)

    A janela caiu de 4 para 3 — UMA pessoa saiu. Saiu tres nomes, no mesmo
    segundo, dois deles errados.

    O mecanismo: `linhas_quando_visto` guardava quantas linhas a janela tinha da
    ultima vez que aquele membro foi RECONHECIDO, e a guarda de saida comparava
    contra esse retrato a CADA frame. Com o reconhecimento piscando desde as
    10:03, J4guar e Kaus passaram minutos fora de `presentes` com o retrato
    preso em 4. A pergunta deixou de ser

        "a janela encolheu quando ele sumiu?"

    e virou

        "a janela encolheu em ALGUM momento desde a ultima vez que eu consegui
         reconhece-lo?"

    A segunda vira verdadeira para TODOS os obsoletos de uma vez, no instante da
    primeira saida real de qualquer pessoa.

    E a mesma familia de [[alarme-falso-no-arranque]] e
    [[resolved-party-entra-sai-em-loop]]: tratar mudanca de RECONHECIMENTO como
    mudanca de REALIDADE. Aqui com um agravante — o retrato envelhecido guarda a
    mentira ate o dia em que ela pode ser contada.

    O oraculo destes testes e DERIVADO do dominio, nao de um numero observado: a
    party window perde exatamente uma linha por pessoa que sai, entao o numero
    de alertas de saida nunca pode passar de quanto a janela encolheu.
    """

    NOMES = ["Korzis", "J4guar", "Kaus", "TioMad"]

    def _obs(self, nomes_por_linha, ui_visivel=True, hp_proprio=None):
        """`""` = linha ocupada mas nao reconhecida. `None` = linha vazia."""
        from l2scanner.visao import LeituraDeLinha, Observacao

        linhas = []
        for i, nome in enumerate(nomes_por_linha):
            if nome is None:
                linhas.append(LeituraDeLinha(i, EstadoDaLinha.VAZIA, None, None))
            else:
                reconhecido = nome or None
                linhas.append(
                    LeituraDeLinha(
                        i,
                        EstadoDaLinha.COM_MEMBRO,
                        1.0,
                        1.0,
                        nome=reconhecido,
                        confianca_do_nome=0.98 if reconhecido else 0.0,
                    )
                )
        return Observacao(0, ui_visivel, tuple(linhas), hp_proprio=hp_proprio)

    def _aquecido(self, nomes=None, **ajustes):
        from l2scanner.rastreador import Ajustes, Rastreador

        r = Rastreador(
            nomes=list(self.NOMES),
            assinaturas_configuradas=True,
            nomes_reservados=set(self.NOMES),
            ajustes=Ajustes(**ajustes),
        )
        for i in range(15):
            r.observar(self._obs(nomes or self.NOMES), float(i))
        return r

    def _rodar(self, r, quadros, inicio):
        eventos = []
        for n, nomes in enumerate(quadros):
            eventos.extend(r.observar(self._obs(nomes), inicio + n))
        return eventos

    def _saidas(self, eventos):
        from l2scanner.rastreador import TipoDeEvento

        return [e.membro for e in eventos if e.tipo is TipoDeEvento.SAIU]

    # --- o caso reportado -------------------------------------------------

    def test_o_caso_das_10h17_uma_saida_vira_um_alerta(self):
        """Tres membros fora do reconhecimento; o quarto sai de verdade."""
        r = self._aquecido()

        # 12 frames com so o Korzis reconhecido. A janela fica em 4 linhas o
        # tempo todo — ninguem saiu, so o reconhecimento degradou.
        degradacao = self._rodar(r, [["", "", "", "Korzis"]] * 12, 100.0)
        assert self._saidas(degradacao) == [], (
            "reconhecimento ruim com a janela parada nao e saida de ninguem"
        )

        # agora o Korzis sai DE VERDADE: 4 -> 3 linhas
        saida = self._rodar(r, [["", "", "", None]] * 8, 200.0)

        assert self._saidas(saida) == ["Korzis"], (
            "a janela perdeu UMA linha, entao UMA pessoa saiu. Antes da "
            "correcao saiam quatro alertas no mesmo frame, tres com o nome "
            "errado — exatamente o que chegou no WhatsApp as 10:17:44"
        )

    @pytest.mark.parametrize("obsoletos", [1, 2, 3])
    def test_encolher_uma_linha_nunca_anuncia_mais_de_um(self, obsoletos):
        """Varre o numero de identidades obsoletas: 1, 2 e 3 de 4.

        Antes da correcao o numero de alertas falsos crescia junto com
        `obsoletos` — era literalmente "um evento real vira N alertas".
        """
        r = self._aquecido()

        # os `obsoletos` primeiros somem do reconhecimento; os demais ficam
        linhas = ["" if i < obsoletos else n for i, n in enumerate(self.NOMES)]
        self._rodar(r, [linhas] * 12, 100.0)

        # o ULTIMO da lista sai de verdade: 4 -> 3 linhas
        saida = self._rodar(r, [linhas[:-1] + [None]] * 8, 200.0)

        assert self._saidas(saida) == [self.NOMES[-1]], (
            f"com {obsoletos} identidade(s) obsoleta(s), um encolhimento de "
            f"uma linha ainda e uma saida so. Saiu: {self._saidas(saida)}"
        )

    # --- a deteccao real nao pode ser desligada ---------------------------

    def test_saida_do_meio_da_lista_nomeia_quem_saiu(self):
        """Quem esta ABAIXO sobe uma linha, e isso nao e evento nenhum.

        A reproducao pedida no relato: quem sai NAO e o da ultima linha, entao
        a party inteira compacta para cima.
        """
        r = self._aquecido()

        # J4guar (linha 1) sai; Kaus e TioMad sobem para as linhas 1 e 2
        saida = self._rodar(r, [["Korzis", "Kaus", "TioMad", None]] * 8, 100.0)

        assert self._saidas(saida) == ["J4guar"], (
            "subir de linha nao e sair da party; quem saiu foi o J4guar"
        )

    def test_duas_saidas_reais_no_mesmo_frame_geram_dois_alertas(self):
        """A conservacao e um TETO, nao um limite de um.

        Se a janela perde duas linhas, duas pessoas sairam — e as duas tem que
        ser anunciadas. Uma guarda que so deixasse passar um alerta por frame
        estaria trocando um erro por outro.
        """
        r = self._aquecido()

        saida = self._rodar(r, [["Korzis", "J4guar", None, None]] * 8, 100.0)

        assert sorted(self._saidas(saida)) == ["Kaus", "TioMad"]

    @pytest.mark.parametrize("tamanho", [2, 3, 4])
    def test_qualquer_tamanho_de_party_perde_um_por_vez(self, tamanho):
        """Vizinhos de fronteira: party minima (2->1) ate a calibrada (4->3)."""
        nomes = self.NOMES[:tamanho]
        r = self._aquecido(nomes=nomes)

        saida = self._rodar(r, [nomes[:-1] + [None]] * 8, 100.0)

        assert self._saidas(saida) == [nomes[-1]]

    def test_saida_durante_a_cegueira_ainda_e_detectada_na_volta(self):
        """Cegueira CONGELA, nao zera — a propriedade 3 do modulo.

        Se alguem sai enquanto o scanner esta cego, o alerta tem que sair
        quando a visao voltar. Zerar o retrato do ultimo frame na reaquisicao
        perderia justamente esse evento.
        """
        r = self._aquecido(confirmacoes_para_saida=3)

        for n in range(20):
            r.observar(self._obs(self.NOMES, ui_visivel=False), 100.0 + n)

        # a visao volta com uma linha a menos. Os primeiros frames caem na
        # tolerancia da reaquisicao e nao concluem nada.
        saida = self._rodar(r, [["Korzis", "J4guar", "Kaus", None]] * 12, 200.0)

        assert self._saidas(saida) == ["TioMad"]

    # --- o que a correcao deliberadamente CALA -----------------------------

    def test_saida_real_com_piscada_junto_congela_em_vez_de_chutar(self):
        """Dois sumiram, a janela perdeu uma linha. Nao da para saber qual.

        Um dos dois esta atras de uma linha nao reconhecida e o outro saiu —
        mas os pixels nao dizem quem e quem. Anunciar um dos dois seria acertar
        na moeda; anunciar os dois seria o bug original de volta.
        """
        r = self._aquecido()

        # TioMad sai (4 -> 3 linhas) e o Kaus para de ser reconhecido no MESMO
        # frame. O Kaus continua na tela, na linha 2.
        saida = self._rodar(r, [["Korzis", "J4guar", "", None]] * 10, 100.0)

        assert self._saidas(saida) == [], (
            "com dois candidatos para um encolhimento de uma linha, calar e a "
            "resposta honesta — um alerta que nao veio e recuperavel, um com o "
            "nome errado destroi a confianca na ferramenta"
        )

    def test_saida_de_quem_ja_estava_fora_do_reconhecimento_passa_calada(self):
        """O preco aceito, gravado aqui para nao ser 'consertado' sem querer.

        Quem ja estava sem reconhecimento ha varios frames deixa de ser
        candidato a saida. Se essa pessoa sai de verdade, ninguem e anunciado.

        A alternativa e a que produziu o bug: deixar identidades obsoletas
        elegiveis e anunciar N nomes, quase todos errados, no primeiro
        encolhimento. Silencio e estritamente melhor que mentira plausivel.
        """
        r = self._aquecido()

        # o Kaus (linha 2) some do reconhecimento, mas continua na tela
        self._rodar(r, [["Korzis", "J4guar", "", "TioMad"]] * 10, 100.0)

        # e agora sai de verdade: 4 -> 3 linhas, os de baixo sobem
        saida = self._rodar(r, [["Korzis", "J4guar", "TioMad", None]] * 10, 200.0)

        assert self._saidas(saida) == [], (
            "nao ha como saber que foi o Kaus quem saiu — ele ja estava "
            "invisivel para o reconhecimento antes do encolhimento"
        )

    # --- a invariante, sobre uma sessao inteira ---------------------------

    def test_nunca_mais_alertas_do_que_linhas_perdidas(self):
        """A invariante do dominio, medida sobre uma sessao roteirizada.

        Vale independente do que o reconhecimento faca: alertas de saida <=
        soma de tudo que a janela encolheu.
        """
        r = self._aquecido()

        roteiro = (
            [["", "", "", "Korzis"]] * 6            # reconhecimento pisca
            + [["Korzis", "", "Kaus", ""]] * 6      # pisca diferente
            + [["", "", "", None]] * 8              # 4 -> 3: UMA saida real
            + [["Korzis", "", None, None]] * 6      # 3 -> 2: outra saida real
        )

        eventos = []
        contagens = [4]
        for n, nomes in enumerate(roteiro):
            obs = self._obs(nomes)
            eventos.extend(r.observar(obs, 100.0 + n))
            contagens.append(obs.membros_presentes)

        encolhimento_total = sum(
            max(0, antes - depois)
            for antes, depois in zip(contagens, contagens[1:])
        )
        saidas = self._saidas(eventos)

        assert len(saidas) <= encolhimento_total, (
            f"a party window perdeu {encolhimento_total} linha(s) na sessao "
            f"inteira, entao no maximo {encolhimento_total} pessoa(s) sairam. "
            f"Anunciados: {saidas}"
        )

    def _com_voce(self, linhas_iniciais):
        from l2scanner.rastreador import Ajustes, Rastreador

        r = Rastreador(
            nomes=list(self.NOMES),
            nome_proprio="Yazalaque",
            assinaturas_configuradas=True,
            nomes_reservados=set(self.NOMES),
            ajustes=Ajustes(),
        )
        for i in range(15):
            r.observar(self._obs(linhas_iniciais, hp_proprio=1.0), float(i))
        return r

    def test_voce_nunca_sai_pela_lista_de_linhas(self):
        """Voce nao aparece na propria party window.

        Entao nenhuma leitura das LINHAS pode concluir que voce saiu — quem
        responde essa pergunta e `_avaliar_se_voce_esta_em_party`, com a sua
        propria barra e um debounce proprio. Sem esta guarda, a sua chave
        (`@Yazalaque`) some de `presentes` assim que o recorte da sua barra
        fica ilegivel, e um encolhimento da janela no mesmo frame poe o SEU
        nome na fila de saidas de membro.
        """
        r = self._com_voce(self.NOMES)

        eventos = []
        for n in range(10):
            eventos.extend(
                r.observar(
                    self._obs(["Korzis", "J4guar", "Kaus", None], hp_proprio=None),
                    100.0 + n,
                )
            )

        assert "Yazalaque" not in self._saidas(eventos)

    def test_voce_nao_sai_nem_quando_e_o_unico_candidato(self):
        """O caso que a lei de conservacao NAO cobre.

        Aqui quem sai e uma linha nao reconhecida — que nunca pode ser
        anunciada — entao a sua chave fica sozinha como candidata e o teto por
        encolhimento (1 candidato <= 1 linha perdida) deixa passar. So a guarda
        do `@` impede "YAZALAQUE SAIU DA PARTY" a partir de um recorte de barra
        ilegivel.
        """
        r = self._com_voce(["Korzis", "J4guar", "", ""])

        eventos = []
        for n in range(10):
            eventos.extend(
                r.observar(
                    self._obs(["Korzis", "J4guar", ""], hp_proprio=None),
                    100.0 + n,
                )
            )

        assert self._saidas(eventos) == [], (
            "a janela perdeu uma linha NAO RECONHECIDA; a unica identidade "
            f"que sumiu junto foi a sua. Anunciados: {self._saidas(eventos)}"
        )
