"""O recorte do nome comecava DENTRO do nome, e cortava a primeira letra.

O QUE FOI MEDIDO, e onde
------------------------
Contra a tela viva do usuario em 2026-08-31, com a party window calibrada e
`icone_x = 12`. Colunas da JANELA:

    emblema de classe      13 a 26
    nome SEM coroa         comeca em 30
    coroa do lider         31 a 44
    nome COM coroa         comeca em 48
    recorte de entao       comecava em 38   <- 8 colunas do nome perdidas

`Calibracao.regiao_do_nome` faz `esquerda = icone_x + nome_dx`, e `nome_dx`
valia 26. Com `icone_x = 12` isso da 38 — ou seja, o recorte comecava DEPOIS do
inicio do nome, e cada assinatura era gravada ja mutilada:

    Titander -> "TANDER"    Pirulito -> "RULTO"    Welazkez -> "elazkez"

POR QUE ISSO NAO APARECIA
-------------------------
O corte era CONSTANTE. "TANDER" gravado casa com "TANDER" na tela, e os tres
casam 0.95+. O que ele quebrava era a MUDANCA de lider: a coroa desloca o nome
18 colunas, e com 8 colunas ja perdidas na esquerda o pedaco que sobra dentro
do recorte deixa de ser o mesmo pedaco. Em campo, os DOIS membros que falharam
foram exatamente os dois cuja condicao de lider mudou entre a calibracao e o
dia do teste.

A CONTA DO CONSERTO
-------------------
`nome_dx` 26 -> 16 poe a esquerda em 28, dois pixels depois do fim do emblema
de classe. `nome_largura` 100 -> 110 devolve as mesmas 10 colunas na direita,
entao a borda direita continua em 138 e o fim do nome do lider (coluna 93 na
tela do usuario) segue dentro.

A MESMA ESTRUTURA ESTA NA FIXTURE, e e contra ela que estes testes medem:
emblema em 12..25, colunas 26 e 27 em branco, nome comecando em 28, 29 ou 30
conforme a linha. Nao ha numero chutado aqui — todos saem de
`_blocos_de_texto_da_linha` lendo os pixels.
"""

from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.calibracao import Calibracao, LayoutDaParty
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.identidade import (
    LIMIAR_DE_CASAMENTO,
    Assinatura,
    criar_assinatura,
    identificar_linhas,
    mascara_de_texto,
)
from l2scanner.visao import _recorte_do_nome, extrair

FIXTURES = Path(__file__).parent / "fixtures" / "identidade"

# Quantas colunas em branco separam o emblema de classe do nome. Medido na
# fixture, nas 4 linhas: o emblema termina em 25 e o nome comeca em 28, 29 ou
# 30 — entao um vao de 2 ja separa os dois, e vaos INTERNOS do nome chegam a 2
# (linha 0: 57 -> 60). O corte fica em "maior que 2", que separa o emblema sem
# picar o nome em pedacos.
VAO_QUE_SEPARA_O_EMBLEMA = 2


@pytest.fixture
def calibracao() -> Calibracao:
    return Calibracao.carregar(FIXTURES / "calibracao.json")


@pytest.fixture
def pixels() -> np.ndarray:
    px = cv2.imread(str(FIXTURES / "party_ordem_original.png"), cv2.IMREAD_COLOR)
    assert px is not None, "fixture da party nao pode ser lida"
    return px


@pytest.fixture
def pixels_com_lider() -> np.ndarray:
    px = cv2.imread(str(FIXTURES / "party_com_lider.png"), cv2.IMREAD_COLOR)
    assert px is not None, "fixture do lider nao pode ser lida"
    return px


def com_a_geometria_padrao(cal: Calibracao) -> Calibracao:
    """A mesma calibracao, mas com o recorte do nome nos valores PADRAO.

    A fixture grava `nome_dx` e `nome_largura` explicitos, como o
    `calibration.json` do usuario. Ler os defaults da dataclass — em vez de
    escrever 16 e 110 aqui — e o que faz este arquivo julgar o codigo, e nao
    repetir uma copia dele que pode divergir sem ninguem notar.
    """
    padrao = {
        campo.name: campo.default
        for campo in fields(LayoutDaParty)
        if campo.name.startswith("nome_")
    }
    return replace(cal, layout=replace(cal.layout, **padrao))


def _blocos_de_texto_da_linha(
    pixels: np.ndarray, cal: Calibracao, indice: int
) -> list[tuple[int, int]]:
    """Os blocos de texto da LINHA INTEIRA, em colunas da party window.

    Le a faixa horizontal completa, e nao o recorte — o recorte e justamente o
    que esta em julgamento aqui. Devolve pares (primeira coluna, ultima coluna).
    """
    lay = cal.layout
    topo = lay.icone_y + indice * lay.passo + lay.nome_dy
    mascara = mascara_de_texto(pixels[topo : topo + lay.nome_altura, :])
    colunas = np.flatnonzero(mascara.any(axis=0))
    if colunas.size == 0:
        return []

    blocos: list[tuple[int, int]] = []
    inicio = anterior = int(colunas[0])
    for coluna in map(int, colunas[1:]):
        if coluna - anterior > VAO_QUE_SEPARA_O_EMBLEMA:
            blocos.append((inicio, anterior))
            inicio = coluna
        anterior = coluna
    blocos.append((inicio, anterior))
    return blocos


class TestOndeAsCoisasEstaoNaLinha:
    """Primeiro a medicao, depois o julgamento. Sem isto o resto e chute."""

    def test_o_emblema_de_classe_e_o_primeiro_bloco_e_termina_sempre_no_mesmo_lugar(
        self, pixels, calibracao
    ):
        fins = {
            _blocos_de_texto_da_linha(pixels, calibracao, i)[0][1] for i in range(4)
        }

        assert len(fins) == 1, (
            f"o emblema de classe tem de terminar na mesma coluna em todas as "
            f"linhas — terminou em {sorted(fins)}"
        )

    def test_ha_um_vao_em_branco_entre_o_emblema_e_o_nome(self, pixels, calibracao):
        """E o vao que da onde ancorar o recorte sem cortar nem sujar."""
        for i in range(4):
            emblema, primeiro_do_nome = _blocos_de_texto_da_linha(
                pixels, calibracao, i
            )[:2]

            assert primeiro_do_nome[0] > emblema[1] + 1, (
                f"linha {i}: sem vao entre o emblema {emblema} e o nome "
                f"{primeiro_do_nome} nao ha onde comecar o recorte"
            )


class TestORecortePadraoNaoCortaONome:
    """A correcao do defeito de campo, medida contra os pixels da fixture."""

    def test_o_recorte_comeca_depois_do_emblema_e_nunca_dentro_do_nome(
        self, pixels, calibracao
    ):
        """A reproducao. Com `nome_dx = 26` a esquerda cai em 38, dentro do nome.

        E o defeito inteiro em uma assertiva: a borda esquerda tem de ficar no
        vao — depois da ultima coluna do emblema e antes da primeira coluna de
        qualquer coisa que venha depois dele (nome ou coroa).
        """
        cal = com_a_geometria_padrao(calibracao)
        esquerda = cal.regiao_do_nome(0).esquerda

        for i in range(4):
            blocos = _blocos_de_texto_da_linha(pixels, cal, i)
            fim_do_emblema = blocos[0][1]
            inicio_do_resto = blocos[1][0]

            assert fim_do_emblema < esquerda <= inicio_do_resto, (
                f"linha {i}: o recorte comeca em {esquerda}, e o emblema "
                f"termina em {fim_do_emblema} e o nome comeca em "
                f"{inicio_do_resto}. Comecar depois de {inicio_do_resto} corta "
                f"a primeira letra; comecar antes de {fim_do_emblema} mete o "
                f"emblema de classe dentro da assinatura"
            )

    def test_o_recorte_termina_depois_da_ultima_coluna_do_nome_mais_longo(
        self, pixels, calibracao
    ):
        """A outra ponta: mover a esquerda sem alargar perderia o fim do nome.

        Vale sobretudo para o LIDER, que e o nome mais deslocado para a direita
        — na tela do usuario ele vai ate a coluna 93, e na fixture ate a 74.
        """
        cal = com_a_geometria_padrao(calibracao)
        regiao = cal.regiao_do_nome(0)
        direita = regiao.esquerda + regiao.largura

        for i in range(4):
            fim = _blocos_de_texto_da_linha(pixels, cal, i)[-1][1]

            assert fim < direita, (
                f"linha {i}: o nome termina em {fim} e o recorte acaba em "
                f"{direita} — o fim do nome ficou de fora"
            )

    def test_o_recorte_padrao_cabe_no_frame(self, pixels, calibracao):
        """Alargar so vale se o recorte continuar existindo.

        `_recorte_do_nome` devolve None quando a regiao cai fora do frame, e
        None ali significa linha nao reconhecida — a mesma cegueira silenciosa
        que o alargamento existe para evitar.
        """
        cal = com_a_geometria_padrao(calibracao)

        for i in range(4):
            assert _recorte_do_nome(pixels, cal, i) is not None, (
                f"a linha {i} deixou de caber no frame com o recorte padrao"
            )


class TestAGeometriaPadraoContinuaReconhecendo:
    """Alargar o recorte nao pode custar a margem que faz o casamento valer.

    A nota de `LayoutDaParty` avisa que um recorte LARGO deixa o terreno
    dominar a correlacao: medido na epoca, a margem entre nomes caiu de 0.55
    para 0.04. Estas 10 colunas a mais sao emblema e vao em branco, nao
    terreno, mas "nao e terreno" e argumento — a margem e medicao.
    """

    def assinaturas_regravadas(
        self, pixels: np.ndarray, cal: Calibracao
    ) -> list[Assinatura]:
        """As 4 assinaturas como `calibrar.bat` as gravaria hoje."""
        return [
            criar_assinatura(cal.nomes[i], _recorte_do_nome(pixels, cal, i))
            for i in range(4)
        ]

    def test_todo_mundo_e_reconhecido_com_a_geometria_padrao(
        self, pixels, pixels_com_lider, calibracao
    ):
        cal = com_a_geometria_padrao(calibracao)
        cal.assinaturas = self.assinaturas_regravadas(pixels, cal)

        obs = extrair(
            Frame(pixels=pixels_com_lider, indice=0, saude=SaudeDoFrame.OK), cal
        )

        assert [linha.nome for linha in obs.linhas[:4]] == cal.nomes

    def test_a_margem_ate_o_nome_errado_continua_larga(
        self, pixels, pixels_com_lider, calibracao
    ):
        """O numero que importa, e nao so o desfecho.

        Medido: com a geometria antiga o pior nome ERRADO chega a 0.375; com a
        padrao, 0.381. O certo casa 1.000 nas duas. A folga ate
        LIMIAR_DE_CASAMENTO nao encolheu.
        """
        cal = com_a_geometria_padrao(calibracao)
        assinaturas = self.assinaturas_regravadas(pixels, cal)
        recortes = {i: _recorte_do_nome(pixels_com_lider, cal, i) for i in range(4)}

        res = identificar_linhas(recortes, assinaturas)

        for i in range(4):
            assert res[i].segundo_melhor < LIMIAR_DE_CASAMENTO, (
                f"linha {i}: o segundo melhor chegou a "
                f"{res[i].segundo_melhor:.3f}, colado no limiar"
            )
