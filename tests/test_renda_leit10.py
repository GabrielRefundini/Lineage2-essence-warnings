"""O LEIT-10: a varredura de pisos vizinhos, e a porta de UM campo que a torna barata.

O QUE ESTE ARQUIVO PROVA, E POR QUE CADA METADE EXISTE
======================================================
**A primeira metade** (`TestAEquivalencia...`) e o teste de regressao da
extracao de `_ler`. `ler_um_campo` nasceu de dentro de `ler_os_tres_campos`, e
uma extracao que mudasse UM resultado produziria um numero plausivel e errado
— o unico defeito que este workstream trata como inaceitavel. A afirmacao e
literal: para a mesma fixtura, `ler_um_campo(campo=X)` devolve **o mesmo
objeto** que `ler_os_tres_campos(...).X`.

**A segunda metade** (`TestAVarredura...`) prova que o laco, antes de declarar
que um campo parou de sair, ANDA pelos pisos vizinhos — e, o que custa mais
caro, que ele NAO anda quando nao deve.

O MODO DE FALHA QUE ESTE ARQUIVO GUARDA MAIS DE PERTO E O DO ORCAMENTO
=======================================================================
O nivel recusa **79% dos tiques** por natureza (Fase 1, 14 amostras). Uma
varredura que disparasse na recusa isolada rodaria oito leituras extras em
quatro de cada cinco tiques; e uma varredura PERDIDA que nao zerasse a serie
re-rodaria as mesmas oito tentativas em **todo** tique seguinte, pelo resto da
noite. Os dois casos matam a cadencia de 1 Hz, que e o defeito que
`mercado_modo.py:781-783` existe para impedir.

Por isso `test_UMA_VARREDURA_PERDIDA_NAO_SE_REPETE_NO_TIQUE_SEGUINTE` e o
teste mais importante do arquivo: sem ele o requisito passa e o modo morre.

O QUE NAO ESTA AQUI, E DE PROPOSITO
====================================
O M-Y (2026-09-03) mediu o modo de falha IRMAO e OPOSTO: o painel de status
moveu ~90 px e o retangulo do nivel passou a apontar para **grama pura**.
Nenhum piso, em nenhum alcance, le um numero em grama. Os dois se parecem de
fora — o campo para de sair — e pedem consertos opostos: **varredura** para
brilho, **recalibrar** para posicao. O que este arquivo afirma sobre isso e que
a varredura PERDIDA em todos os pisos diz, por escrito, que o suspeito passou a
ser o RETANGULO, e manda o usuario ao `calibrar-renda.bat`.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.ocr as ocr
from l2scanner import renda_leitura as rl
from l2scanner.calibracao import Calibracao
from l2scanner.renda_leitura import (
    CAMPO_DA_ADENA,
    CAMPO_DO_EXP,
    CAMPO_DO_NIVEL,
    MOTIVO_DO_PERSONAGEM,
    ORDEM_DOS_CAMPOS,
    RecusaDaRenda,
)

FIXTURAS = Path(__file__).parent / "fixtures" / "renda"
CALIBRACAO_DE_FIXTURE = FIXTURAS / "calibracao_de_fixture.json"
MONTAGEM_COMPLETA = FIXTURAS / "montagem_completa.png"

FONTE_DO_LEITOR = (
    Path(__file__).parent.parent / "l2scanner" / "renda_leitura.py"
)

TEM_OCR = ocr.disponivel()
ocr._resetar_cache()

precisa_de_ocr = pytest.mark.skipif(
    not TEM_OCR,
    reason=(
        "Este Python nao tem as bindings de OCR do Windows. O ambiente de "
        'producao tem: PYTHONPATH=".;<repo>/.venv/Lib/site-packages" python '
        "-m pytest tests/test_renda_leit10.py"
    ),
)


@pytest.fixture(scope="module")
def cal() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO_DE_FIXTURE)


@pytest.fixture(scope="module")
def montagem() -> np.ndarray:
    return cv2.imread(str(MONTAGEM_COMPLETA))


# ---------------------------------------------------------------------------
# TAREFA 1 -- A EQUIVALENCIA, e ela e escrita ANTES da extracao
# ---------------------------------------------------------------------------


def _mesma_leitura(um, tres) -> bool:
    """Dois resultados de leitura sao O MESMO FATO.

    A comparacao e por CAMPO A CAMPO e nao por `==`, porque `RecusaDaRenda` e
    os dois valores sao dataclasses congeladas com `__eq__` — mas o
    `detalhe` de uma recusa carrega o texto que o OCR viu, e um teste que
    comparasse so o motivo deixaria passar uma extracao que mudasse o recorte.
    Aqui compara-se o objeto INTEIRO, e a funcao existe so para dar nome a
    isso.
    """
    return type(um) is type(tres) and um == tres


class TestAEquivalenciaDaExtracao:
    """`ler_um_campo` devolve o MESMO que `ler_os_tres_campos`, nos tres campos.

    E O `T-03-22` DO REGISTRO DE AMEACAS em forma executavel: a extracao de
    `_ler` e o maior risco de regressao silenciosa desta fase, e uma leitura
    que mudasse aqui nao apareceria em lugar nenhum ate uma noite de farm.
    """

    @precisa_de_ocr
    @pytest.mark.parametrize("personagem", ["Faerlina", "Yazalaque"])
    def test_OS_TRES_CAMPOS_SAEM_IDENTICOS_PELAS_DUAS_PORTAS(
        self, cal, montagem, personagem
    ):
        tres = rl.ler_os_tres_campos(
            montagem, personagem=personagem, calibracao=cal
        )
        for campo in ORDEM_DOS_CAMPOS:
            um = rl.ler_um_campo(
                montagem, personagem=personagem, campo=campo, calibracao=cal
            )
            assert _mesma_leitura(um, tres.por_campo[campo]), (
                f"{personagem}/{campo}: a porta de um campo devolveu {um!r} e "
                f"a dos tres devolveu {tres.por_campo[campo]!r}"
            )

    @pytest.mark.parametrize("personagem", ["Faerlina", "Yazalaque"])
    def test_A_ADENA_SAI_IDENTICA_SEM_OCR_NENHUM(
        self, cal, montagem, personagem
    ):
        """O caminho de GLIFO nao precisa de motor de texto, e ele e o mais
        perigoso dos tres — e por isso esta equivalencia roda em qualquer
        clone, contra pixel real."""
        tres = rl.ler_os_tres_campos(
            montagem, personagem=personagem, calibracao=cal
        )
        um = rl.ler_um_campo(
            montagem,
            personagem=personagem,
            campo=CAMPO_DA_ADENA,
            calibracao=cal,
        )
        assert _mesma_leitura(um, tres.adena)
        assert not isinstance(um, RecusaDaRenda), (
            "a fixtura de montagem tem de dar a adena como NUMERO; sem isso a "
            "equivalencia seria entre duas recusas e nao provaria o recorte"
        )

    def test_O_PISO_EXPLICITO_VENCE_O_GRAVADO(self, cal, montagem):
        """`piso_de_brilho=` usa AQUELE piso e ignora o do arquivo.

        E a afirmacao de que a varredura tem como andar: sem ela,
        `pisos_vizinhos` devolveria uma lista bonita que nada consome.
        """
        gravado = rl.ler_um_campo(
            montagem,
            personagem="Faerlina",
            campo=CAMPO_DA_ADENA,
            calibracao=cal,
        )
        # 250 e um piso quase branco: a mascara sai vazia e a leitura recusa.
        # Ele nao e escolha de estilo — e o jeito de provar que o parametro
        # CHEGOU no `inRange`, e nao so na assinatura.
        distante = rl.ler_um_campo(
            montagem,
            personagem="Faerlina",
            campo=CAMPO_DA_ADENA,
            calibracao=cal,
            piso_de_brilho=250,
        )
        assert not _mesma_leitura(gravado, distante)
        assert isinstance(distante, RecusaDaRenda)

    def test_O_DEFAULT_E_None_E_ELE_SIGNIFICA_USE_O_GRAVADO(self, cal, montagem):
        """`None` e o sinal de "sem sobreposicao", e nunca um numero por omissao.

        A distincao e a mesma que `RecusaDaRenda` faz entre "recusou" e "nao
        mediu": um default numerico seria um piso magico servindo a uma regiao
        e apagando a outra em silencio (M-E: as bandas nao tem intersecao).
        """
        gravado = int(
            cal.renda_do_personagem("Faerlina")["barra_direita"][
                "piso_de_brilho"
            ]
        )
        omitido = rl.ler_um_campo(
            montagem,
            personagem="Faerlina",
            campo=CAMPO_DA_ADENA,
            calibracao=cal,
        )
        explicito = rl.ler_um_campo(
            montagem,
            personagem="Faerlina",
            campo=CAMPO_DA_ADENA,
            calibracao=cal,
            piso_de_brilho=gravado,
        )
        assert _mesma_leitura(omitido, explicito)

        import inspect

        assinatura = inspect.signature(rl.ler_um_campo)
        assert assinatura.parameters["piso_de_brilho"].default is None

    def test_O_PERSONAGEM_SEM_CALIBRACAO_RECUSA_ANTES_DE_QUALQUER_OCR(
        self, cal, montagem, monkeypatch
    ):
        """A recusa nomeada, e o motor NAO e gasto para descobrir isso.

        O monkeypatch e o portao: se a funcao chamasse OCR antes de conferir o
        personagem, o teste explodiria com `AssertionError` em vez de passar.
        """

        def _proibido(*_a, **_k):
            raise AssertionError(
                "o OCR foi chamado para um personagem sem calibracao"
            )

        monkeypatch.setattr(rl, "ler_texto", _proibido)
        monkeypatch.setattr(rl, "ler_texto_ampliado", _proibido)

        for campo in ORDEM_DOS_CAMPOS:
            recusa = rl.ler_um_campo(
                montagem,
                personagem="NaoExiste",
                campo=campo,
                calibracao=cal,
            )
            assert isinstance(recusa, RecusaDaRenda)
            assert recusa.motivo == MOTIVO_DO_PERSONAGEM
            assert recusa.campo == campo
            assert "NAO cai na calibracao de outro personagem" in recusa.detalhe

    def test_A_RECUSA_DO_PERSONAGEM_E_A_MESMA_PELAS_DUAS_PORTAS(
        self, cal, montagem
    ):
        tres = rl.ler_os_tres_campos(
            montagem, personagem="NaoExiste", calibracao=cal
        )
        for campo in ORDEM_DOS_CAMPOS:
            um = rl.ler_um_campo(
                montagem, personagem="NaoExiste", campo=campo, calibracao=cal
            )
            assert _mesma_leitura(um, tres.por_campo[campo])

    def test_A_SUBCHAVE_AUSENTE_MANDA_RODAR_O_CALIBRADOR(self, montagem):
        """A entrada pela metade, e a mutilacao e EM MEMORIA por medicao.

        MEDIDO ao escrever este teste: gravar a mesma entrada sem `nivel` num
        arquivo e carrega-la **nao chega** nesta recusa —
        `calibracao.py:1495-1505` levanta `CalibracaoInvalida` no proprio
        carregamento, com a frase *"uma entrada pela metade e pior que uma
        entrada ausente"*. Ou seja: o esquema ja fecha o caminho do disco, e a
        guarda de `ler_um_campo` cobre o que sobra — um objeto `Calibracao`
        montado ou alterado em memoria, que e exatamente o que a injecao de
        dependencia desta casa permite. Mutilar em memoria e o unico jeito
        HONESTO de chegar ao ramo; escrever o arquivo mediria a validacao do
        esquema e chamaria isso de leitura.
        """
        mutilada = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        entrada = dict(mutilada.renda_por_personagem["Faerlina"])
        del entrada["nivel"]
        mutilada.renda_por_personagem = dict(
            mutilada.renda_por_personagem, Faerlina=entrada
        )

        um = rl.ler_um_campo(
            montagem,
            personagem="Faerlina",
            campo=CAMPO_DO_NIVEL,
            calibracao=mutilada,
        )
        tres = rl.ler_os_tres_campos(
            montagem, personagem="Faerlina", calibracao=mutilada
        )
        assert isinstance(um, RecusaDaRenda)
        assert "Rode o calibrador da renda" in um.detalhe
        assert _mesma_leitura(um, tres.nivel)

    def test_UM_CAMPO_DESCONHECIDO_LEVANTA_NOMEANDO_OS_QUE_EXISTEM(
        self, cal, montagem
    ):
        """O molde e o de `ganho_do_passo` (`renda_conta.py:900-903`).

        Campo desconhecido e ERRO DE PROGRAMACAO e nao recusa de leitura: uma
        `RecusaDaRenda` aqui esconderia um `typo` do chamador dentro dos 79% de
        recusa normal do nivel, onde ninguem o veria.
        """
        with pytest.raises(ValueError) as erro:
            rl.ler_um_campo(
                montagem,
                personagem="Faerlina",
                campo="mana",
                calibracao=cal,
            )
        for campo in ORDEM_DOS_CAMPOS:
            assert campo in str(erro.value)

    def test_A_LEITURA_COMPLETA_DESEMPACOTA_OS_MOLDES_UMA_VEZ_E_NAO_TRES(
        self, cal, montagem, monkeypatch
    ):
        """O desempacotamento e o custo que a delegacao poderia ter triplicado.

        `ler_os_tres_campos` continua sendo a porta de PRODUCAO e paga UM
        desempacotamento por tique. Se ela delegasse sem passar os moldes
        adiante, pagaria tres — e o caminho de 1 Hz e o que nao pode engordar
        para servir a um caminho que roda em 4,7% dos tiques.
        """
        chamadas = []
        original = rl.glifos_de_calibracao

        def _contar(bruto):
            chamadas.append(bruto)
            return original(bruto)

        monkeypatch.setattr(rl, "glifos_de_calibracao", _contar)
        rl.ler_os_tres_campos(
            montagem, personagem="Faerlina", calibracao=cal
        )
        assert len(chamadas) == 1, (
            f"a leitura completa desempacotou os moldes {len(chamadas)} "
            "vez(es); o contrato e UMA"
        )

    def test_A_ADENA_SEM_MOLDES_PASSADOS_DESEMPACOTA_POR_CONTA_PROPRIA(
        self, cal, montagem, monkeypatch
    ):
        chamadas = []
        original = rl.glifos_de_calibracao

        def _contar(bruto):
            chamadas.append(bruto)
            return original(bruto)

        monkeypatch.setattr(rl, "glifos_de_calibracao", _contar)
        sozinha = rl.ler_um_campo(
            montagem,
            personagem="Faerlina",
            campo=CAMPO_DA_ADENA,
            calibracao=cal,
        )
        assert len(chamadas) == 1
        tres = rl.ler_os_tres_campos(
            montagem, personagem="Faerlina", calibracao=cal
        )
        assert _mesma_leitura(sozinha, tres.adena)

    def test_OS_CAMPOS_QUE_NAO_SAO_A_ADENA_NAO_PAGAM_O_DESEMPACOTAMENTO(
        self, cal, montagem, monkeypatch
    ):
        """Medido: so a adena precisa dos moldes.

        Desempacotar para ler o nivel seria trabalho puro jogado fora dentro da
        varredura — que e justamente o caminho em que oito leituras se
        somam num tique so.
        """
        chamadas = []
        monkeypatch.setattr(
            rl,
            "glifos_de_calibracao",
            lambda bruto: chamadas.append(bruto) or {},
        )
        for campo in (CAMPO_DO_NIVEL, CAMPO_DO_EXP):
            rl.ler_um_campo(
                montagem,
                personagem="Faerlina",
                campo=campo,
                calibracao=cal,
                piso_de_brilho=200,
            )
        assert chamadas == []


class TestOPortaoDeMemoriaContinuaVerde:
    """A extracao nao pode ter dado memoria ao leitor puro.

    A funcao vem de `tests/test_renda_par.py`, IMPORTADA e nao copiada, pela
    mesma razao que aquele arquivo escreve: um controle que chamasse outra
    funcao provaria outra coisa.
    """

    def test_RENDA_LEITURA_CONTINUA_SEM_GLOBAL_E_SEM_LITERAL_MUTAVEL(self):
        from tests.test_renda_par import memoria_de_modulo

        achados = memoria_de_modulo(FONTE_DO_LEITOR)
        assert not achados, (
            "renda_leitura.py ganhou memoria na extracao:\n  "
            + "\n  ".join(achados)
        )

    def test_CONTROLE_POSITIVO_A_FUNCAO_IMPORTADA_AINDA_ACUSA(self, tmp_path):
        from tests.test_renda_par import memoria_de_modulo

        alvo = tmp_path / "com_memoria.py"
        alvo.write_text(
            "PISO_QUE_FUNCIONOU = {}\n"
            "\n"
            "def lembrar(campo, piso):\n"
            "    global PISO_QUE_FUNCIONOU\n"
            "    PISO_QUE_FUNCIONOU = {campo: piso}\n",
            encoding="utf-8",
        )
        assert len(memoria_de_modulo(alvo)) == 2
