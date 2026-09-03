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

import ast
import logging
from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.ocr as ocr
from l2scanner import renda_leitura as rl
from l2scanner.calibracao import Calibracao
from l2scanner.renda_laco import (
    RECUSAS_SEGUIDAS_PARA_VARRER,
    TETO_DA_CARENCIA,
)
from l2scanner.renda_leitura import (
    CAMPO_DA_ADENA,
    CAMPO_DO_EXP,
    CAMPO_DO_NIVEL,
    MOTIVO_DO_PERSONAGEM,
    ORDEM_DOS_CAMPOS,
    CamposDaRenda,
    RecusaDaRenda,
    ValorDaAdena,
    ValorDaRenda,
)

FIXTURAS = Path(__file__).parent / "fixtures" / "renda"
CALIBRACAO_DE_FIXTURE = FIXTURAS / "calibracao_de_fixture.json"
MONTAGEM_COMPLETA = FIXTURAS / "montagem_completa.png"

FONTE_DO_LEITOR = (
    Path(__file__).parent.parent / "l2scanner" / "renda_leitura.py"
)
FONTE_DO_LACO = Path(__file__).parent.parent / "l2scanner" / "renda_laco.py"

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


# ---------------------------------------------------------------------------
# TAREFA 3 -- A VARREDURA NO LACO
# ---------------------------------------------------------------------------

# OS PISOS GRAVADOS DA FAERLINA na calibracao de fixtura. Escritos aqui e nao
# lidos do arquivo DE PROPOSITO: eles sao a ORIGEM da grade, e o teste precisa
# saber de cor onde a varredura comeca para poder afirmar a ORDEM dela. Ha um
# teste logo abaixo conferindo que estes numeros ainda sao os do arquivo -- sem
# ele, uma recalibracao da fixtura tornaria o resto silenciosamente vazio.
PISO_GRAVADO = {
    CAMPO_DO_NIVEL: 200,
    CAMPO_DO_EXP: 160,
    CAMPO_DA_ADENA: 185,
}

#: Os oito vizinhos do nivel, na ordem que `pisos_vizinhos` produz a partir de
#: 200. Escritos por extenso porque a ORDEM e metade do requisito.
VIZINHOS_DO_NIVEL = (205, 195, 210, 190, 215, 185, 220, 180)

#: Quantas leituras de campo uma varredura completa custa.
TENTATIVAS_DE_UMA_VARREDURA = len(VIZINHOS_DO_NIVEL)


class TelaFalsa:
    """A tela do teste: cada campo sai APENAS no piso certo DELE, e ela conta.

    ELA E AS DUAS ALAVANCAS AO MESMO TEMPO -- `ler_campos=` e `ler_campo=` --
    e isso e deliberado: duas dubles separadas poderiam discordar sobre o que a
    tela mostra neste tique, e a discordancia passaria por comportamento do
    laco. Aqui ha UMA verdade sobre a tela e os dois caminhos de leitura a
    consultam.

    `leituras` CONTA LEITURA DE CAMPO, E NAO CHAMADA DE FUNCAO, e a escolha da
    unidade e o teste inteiro. Uma leitura de campo e um recorte + uma mascara
    + (no nivel e no EXP) uma passada de OCR -- e ela que o orcamento do tique
    paga, e MEDIDO: 8,9 ms o nivel, 23,4 ms o EXP, 5,3 ms a adena. Contar
    "chamadas de `ler_um_campo`" mediria a FORMA do codigo e ficaria vermelho na
    primeira refatoracao; contar leituras de campo mede o CUSTO, que e o que o
    requisito trata.
    """

    def __init__(self, *, roteiro, personagem="Faerlina"):
        # `roteiro`: dict campo -> piso que produz leitura, OU um callable
        # (numero do tique) -> esse dict. `None` num campo significa "este
        # campo nao sai em piso NENHUM" -- o caso do M-Y, o retangulo apontando
        # para grama, em que varrer perde as oito tentativas por construcao.
        self._roteiro = roteiro
        self.personagem = personagem
        self.leituras = {campo: 0 for campo in ORDEM_DOS_CAMPOS}
        self.pisos_pedidos = {campo: [] for campo in ORDEM_DOS_CAMPOS}

    @property
    def tiques(self) -> int:
        """O EXP e lido UMA vez por tique nos roteiros deste arquivo, entao a
        contagem de leituras dele E a contagem de tiques."""
        return self.leituras[CAMPO_DO_EXP]

    def _piso_certo(self, campo):
        mapa = (
            self._roteiro(self.tiques)
            if callable(self._roteiro)
            else self._roteiro
        )
        return mapa.get(campo)

    def _ler(self, campo, piso):
        self.leituras[campo] += 1
        self.pisos_pedidos[campo].append(piso)
        if self._piso_certo(campo) != piso:
            return RecusaDaRenda(
                campo=campo,
                motivo="campo-vazio",
                detalhe=f"a mascara em piso {piso} nao deixou nada de pe",
            )
        if campo == CAMPO_DO_NIVEL:
            return ValorDaRenda(campo=campo, valor=67, escalas=2, texto="67")
        if campo == CAMPO_DO_EXP:
            # O EXP SOBE A CADA TIQUE, senao o rastreio do `03-02` declara
            # PARADO e o teste passaria a medir outra coisa.
            valor = 500_000 + self.leituras[CAMPO_DO_EXP] * 10
            return ValorDaRenda(
                campo=campo, valor=valor, escalas=2, texto=str(valor)
            )
        valor = 17_000_000 + self.leituras[CAMPO_DA_ADENA] * 1_000
        return ValorDaAdena(
            campo=campo, valor=valor, glifos=10, texto=str(valor)
        )

    def os_tres(self, frame, *, personagem, calibracao):
        """A porta de producao, com os pisos GRAVADOS. `ler_campos=`."""
        lidos = {
            campo: self._ler(campo, PISO_GRAVADO[campo])
            for campo in ORDEM_DOS_CAMPOS
        }
        return CamposDaRenda(
            personagem=personagem,
            nivel=lidos[CAMPO_DO_NIVEL],
            exp=lidos[CAMPO_DO_EXP],
            adena=lidos[CAMPO_DA_ADENA],
        )

    def um(
        self,
        frame,
        *,
        personagem,
        campo,
        calibracao,
        piso_de_brilho=None,
        moldes=None,
    ):
        """A porta de UM campo. `ler_campo=`."""
        return self._ler(
            campo,
            PISO_GRAVADO[campo] if piso_de_brilho is None else piso_de_brilho,
        )


def rodar_o_laco(cal, tmp_path, tela, *, ticks, **extras):
    """O laco de PRODUCAO, com as duas alavancas apontando para a MESMA tela.

    As dubles de fonte, relogio e argumentos vem IMPORTADAS de
    `tests/test_renda_laco.py`, e nao copiadas: duas `FonteFalsa` sao como elas
    divergem, e a divergencia apareceria como "o laco se comporta diferente nos
    dois arquivos de teste".
    """
    from l2scanner.renda_laco import laco_da_renda

    from tests.test_renda_laco import FonteFalsa, RelogioFalso, argumentos

    return laco_da_renda(
        argumentos(**extras),
        cal,
        fonte=FonteFalsa(ticks),
        ler_campos=tela.os_tres,
        ler_campo=tela.um,
        relogio=RelogioFalso([1_000.0 + i for i in range(ticks + 5)]),
        pasta=tmp_path,
        ticks_maximos=ticks,
    )


def so_o_nivel_recusa(piso_do_nivel=None):
    """O roteiro mais usado: EXP e adena saem no piso gravado, o nivel nao."""
    return {
        CAMPO_DO_NIVEL: piso_do_nivel,
        CAMPO_DO_EXP: PISO_GRAVADO[CAMPO_DO_EXP],
        CAMPO_DA_ADENA: PISO_GRAVADO[CAMPO_DA_ADENA],
    }


class TestOsPisosGravadosDaFixturaNaoMudaram:
    """O portao do portao: se a fixtura for recalibrada, os testes abaixo
    passariam a afirmar sobre pisos que nao existem mais, e passariam por
    construcao."""

    def test_A_FIXTURA_AINDA_TEM_OS_PISOS_QUE_ESTE_ARQUIVO_SUPOE(self, cal):
        from l2scanner.renda_leitura import SUBCHAVE_POR_CAMPO

        entrada = cal.renda_do_personagem("Faerlina")
        for campo, piso in PISO_GRAVADO.items():
            assert int(entrada[SUBCHAVE_POR_CAMPO[campo]]["piso_de_brilho"]) == piso

    def test_OS_VIZINHOS_ESCRITOS_A_MAO_SAO_OS_QUE_O_PLANEJADOR_PRODUZ(self, cal):
        from l2scanner.renda_pisos import pisos_vizinhos

        assert (
            pisos_vizinhos(
                piso=PISO_GRAVADO[CAMPO_DO_NIVEL], largura_da_banda=4
            )
            == VIZINHOS_DO_NIVEL
        )


class TestOGatilhoNaoDisparaNaRecusaISOLADA:
    """O caminho de 79% dos tiques do nivel, e ele nao pode engordar."""

    def test_UMA_RECUSA_NAO_VARRE(self, cal, tmp_path):
        tela = TelaFalsa(roteiro=so_o_nivel_recusa())
        rodar_o_laco(cal, tmp_path, tela, ticks=1)
        assert tela.leituras == {
            CAMPO_DO_NIVEL: 1,
            CAMPO_DO_EXP: 1,
            CAMPO_DA_ADENA: 1,
        }

    def test_DOZE_RECUSAS_SEGUIDAS_AINDA_NAO_VARREM(self, cal, tmp_path):
        """Doze, e nao "algumas": o limiar e 13, e um teste com "poucas"
        passaria com qualquer limiar maior que o numero escolhido."""
        tela = TelaFalsa(roteiro=so_o_nivel_recusa())
        rodar_o_laco(
            cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER - 1
        )
        assert tela.leituras[CAMPO_DO_NIVEL] == RECUSAS_SEGUIDAS_PARA_VARRER - 1

    def test_A_TREDECIMA_VARRE(self, cal, tmp_path):
        tela = TelaFalsa(roteiro=so_o_nivel_recusa())
        rodar_o_laco(cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER)
        assert tela.leituras[CAMPO_DO_NIVEL] == (
            RECUSAS_SEGUIDAS_PARA_VARRER + TENTATIVAS_DE_UMA_VARREDURA
        )

    def test_A_VARREDURA_E_DAQUELE_CAMPO_E_OS_OUTROS_DOIS_NAO_PAGAM_NADA(
        self, cal, tmp_path
    ):
        tela = TelaFalsa(roteiro=so_o_nivel_recusa())
        rodar_o_laco(cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER)
        assert tela.leituras[CAMPO_DO_EXP] == RECUSAS_SEGUIDAS_PARA_VARRER
        assert tela.leituras[CAMPO_DA_ADENA] == RECUSAS_SEGUIDAS_PARA_VARRER

    def test_A_VARREDURA_TENTA_OS_VIZINHOS_NA_ORDEM_DO_PLANEJADOR(
        self, cal, tmp_path
    ):
        tela = TelaFalsa(roteiro=so_o_nivel_recusa())
        rodar_o_laco(cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER)
        pedidos = tela.pisos_pedidos[CAMPO_DO_NIVEL]
        assert tuple(pedidos[-TENTATIVAS_DE_UMA_VARREDURA:]) == VIZINHOS_DO_NIVEL

    def test_O_LIMIAR_VALE_13_E_A_CONTA_ESTA_NO_FONTE(self):
        """O valor **e** a aritmetica que o produziu.

        Um `K` de 3 -- o valor dos dois moldes irmaos, `JANELAS_IGUAIS_PARA_
        CONGELAR` e `CONGELADOS_SEGUIDOS_PARA_RELIGAR` -- dispararia a varredura
        em `0,79^3 = 49%` dos tiques. O comentario tem de carregar a conta, o
        alvo de 5% e a hipotese de independencia pelo nome, porque o numero e
        DERIVADO e nao arbitrado -- e um numero derivado sem a derivacao ao lado
        e indistinguivel de um chute.
        """
        assert RECUSAS_SEGUIDAS_PARA_VARRER == 13
        fonte = FONTE_DO_LACO.read_text(encoding="utf-8")
        assert "0,79" in fonte
        assert "4,7%" in fonte or "4,67%" in fonte
        assert "5%" in fonte
        assert "independen" in fonte.lower()
        assert 0.79 ** RECUSAS_SEGUIDAS_PARA_VARRER < 0.05
        assert 0.79 ** (RECUSAS_SEGUIDAS_PARA_VARRER - 1) > 0.05


class TestAVarreduraParaNaPrimeiraValida:
    def test_COM_O_PRIMEIRO_VIZINHO_FUNCIONANDO_SAO_DUAS_LEITURAS_E_NAO_NOVE(
        self, cal, tmp_path
    ):
        tela = TelaFalsa(roteiro=so_o_nivel_recusa(VIZINHOS_DO_NIVEL[0]))
        rodar_o_laco(cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER)
        # doze tiques de UMA leitura, mais o tique do gatilho com DUAS.
        assert tela.leituras[CAMPO_DO_NIVEL] == (
            RECUSAS_SEGUIDAS_PARA_VARRER + 1
        )

    def test_COM_O_QUARTO_VIZINHO_FUNCIONANDO_SAO_QUATRO_TENTATIVAS(
        self, cal, tmp_path
    ):
        tela = TelaFalsa(roteiro=so_o_nivel_recusa(VIZINHOS_DO_NIVEL[3]))
        rodar_o_laco(cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER)
        assert tela.leituras[CAMPO_DO_NIVEL] == (
            RECUSAS_SEGUIDAS_PARA_VARRER + 4
        )
        assert tuple(tela.pisos_pedidos[CAMPO_DO_NIVEL][-4:]) == (
            VIZINHOS_DO_NIVEL[:4]
        )


class TestAMemoriaDoPisoQueFuncionou:
    def test_O_PISO_QUE_VENCEU_E_TENTADO_PRIMEIRO_NOS_TIQUES_SEGUINTES(
        self, cal, tmp_path
    ):
        vencedor = VIZINHOS_DO_NIVEL[3]
        tela = TelaFalsa(roteiro=so_o_nivel_recusa(vencedor))
        rodar_o_laco(
            cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER + 2
        )
        # Os dois tiques depois da vitoria: UMA leitura por campo, no piso
        # LEMBRADO -- e nao nove, e nao no gravado.
        assert tela.pisos_pedidos[CAMPO_DO_NIVEL][-2:] == [vencedor, vencedor]

    def test_DEPOIS_DA_VITORIA_O_REGIME_VOLTA_A_UMA_LEITURA_POR_CAMPO(
        self, cal, tmp_path
    ):
        vencedor = VIZINHOS_DO_NIVEL[0]
        tela = TelaFalsa(roteiro=so_o_nivel_recusa(vencedor))
        extras = RECUSAS_SEGUIDAS_PARA_VARRER + 5
        rodar_o_laco(cal, tmp_path, tela, ticks=extras)
        # 13 tiques de leitura + 1 tentativa vencedora + 5 tiques de UMA.
        assert tela.leituras[CAMPO_DO_NIVEL] == extras + 1
        assert tela.leituras[CAMPO_DO_EXP] == extras

    def test_OS_OUTROS_CAMPOS_CONTINUAM_NO_PISO_GRAVADO(self, cal, tmp_path):
        """A memoria e POR CAMPO: um piso lembrado no nivel nao move o EXP."""
        tela = TelaFalsa(roteiro=so_o_nivel_recusa(VIZINHOS_DO_NIVEL[0]))
        rodar_o_laco(
            cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER + 3
        )
        assert set(tela.pisos_pedidos[CAMPO_DO_EXP]) == {
            PISO_GRAVADO[CAMPO_DO_EXP]
        }

    def test_O_PISO_LEMBRADO_E_ESQUECIDO_E_A_SERIE_RECOMECA_DO_GRAVADO(
        self, cal, tmp_path
    ):
        """Sem o esquecimento a memoria viraria uma calibracao PARALELA e
        invisivel, que envelhece sozinha -- e a proxima mudanca de cenario seria
        varrida a partir de um ponto que ninguem escolheu.

        O vencedor e o QUARTO vizinho (190) de proposito: se a varredura
        seguinte partisse do LEMBRADO, ela tentaria 195 primeiro; partindo do
        GRAVADO, tenta 205. Um vencedor que fosse o primeiro vizinho tornaria os
        dois casos indistinguiveis.
        """
        vencedor = VIZINHOS_DO_NIVEL[3]
        assert vencedor == 190

        def roteiro(tique):
            # Ate o tique 20 o vencedor funciona; depois dele, nada funciona.
            return so_o_nivel_recusa(vencedor if tique <= 20 else None)

        tela = TelaFalsa(roteiro=roteiro)
        rodar_o_laco(cal, tmp_path, tela, ticks=20 + RECUSAS_SEGUIDAS_PARA_VARRER)
        segunda_varredura = tela.pisos_pedidos[CAMPO_DO_NIVEL][
            -TENTATIVAS_DE_UMA_VARREDURA:
        ]
        assert tuple(segunda_varredura) == VIZINHOS_DO_NIVEL

    def test_A_MEMORIA_ATRAVESSA_A_RECUSA_ISOLADA(self, cal, tmp_path):
        """Ela NAO e esquecida na primeira recusa, e este e o ponto do desenho.

        O nivel recusa 79% dos tiques POR NATUREZA. Uma memoria que se apagasse
        na primeira recusa nao sobreviveria a UM tique naquele campo, e a
        varredura seria paga de novo a cada 13 tiques pelo resto da noite. O
        esquecimento acontece no GATILHO -- quando o campo parou de sair de
        novo --, e nao na recusa avulsa.
        """
        vencedor = VIZINHOS_DO_NIVEL[0]

        def roteiro(tique):
            # Depois da vitoria, o vencedor falha em tiques alternados.
            if tique <= RECUSAS_SEGUIDAS_PARA_VARRER:
                return so_o_nivel_recusa(vencedor)
            return so_o_nivel_recusa(vencedor if tique % 2 == 0 else None)

        tela = TelaFalsa(roteiro=roteiro)
        rodar_o_laco(
            cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER + 6
        )
        assert set(
            tela.pisos_pedidos[CAMPO_DO_NIVEL][-6:]
        ) == {vencedor}


class TestACarenciaDepoisDeUmaVarreduraPERDIDA:
    """O teste mais importante do arquivo.

    Sem o reset da serie e a carencia multiplicativa, `recusas_seguidas`
    continuaria `>= K` e a varredura re-rodaria as oito tentativas em TODO
    tique seguinte, pelo resto da noite, num campo que recusa 79% das vezes
    **por natureza**. O `OrcamentoDoTick` acusaria estouro em ~79% dos tiques e
    a cadencia de 1 Hz morreria -- o defeito que `mercado_modo.py:781-783`
    existe para impedir.
    """

    def test_UMA_VARREDURA_PERDIDA_NAO_SE_REPETE_NO_TIQUE_SEGUINTE(
        self, cal, tmp_path
    ):
        tela = TelaFalsa(roteiro=so_o_nivel_recusa(None))
        seguintes = 7
        rodar_o_laco(
            cal,
            tmp_path,
            tela,
            ticks=RECUSAS_SEGUIDAS_PARA_VARRER + seguintes,
        )
        assert tela.leituras[CAMPO_DO_NIVEL] == (
            RECUSAS_SEGUIDAS_PARA_VARRER
            + TENTATIVAS_DE_UMA_VARREDURA
            + seguintes
        ), (
            "a varredura perdida se repetiu: o esperado sao UMA leitura por "
            "tique depois dela, e nao nove"
        )

    def test_A_SEGUNDA_VARREDURA_EXIGE_O_DOBRO_DA_CORRIDA(self, cal, tmp_path):
        """`K` e depois `2K`, contados a partir do ZERO -- a serie reinicia."""
        tela = TelaFalsa(roteiro=so_o_nivel_recusa(None))
        # A primeira varredura no tique 13; a segunda 26 tiques DEPOIS.
        um_a_menos = RECUSAS_SEGUIDAS_PARA_VARRER * 3 - 1  # 38
        rodar_o_laco(cal, tmp_path, tela, ticks=um_a_menos)
        assert tela.leituras[CAMPO_DO_NIVEL] == (
            um_a_menos + TENTATIVAS_DE_UMA_VARREDURA
        )

        exata = TelaFalsa(roteiro=so_o_nivel_recusa(None))
        rodar_o_laco(cal, tmp_path, exata, ticks=um_a_menos + 1)
        assert exata.leituras[CAMPO_DO_NIVEL] == (
            um_a_menos + 1 + 2 * TENTATIVAS_DE_UMA_VARREDURA
        )

    def test_O_MULTIPLICADOR_PARA_NO_TETO_DE_QUATRO(self, cal, tmp_path):
        """As corridas sao 13, 26, 52, 104, 104, ... e nunca 208.

        Os gatilhos caem nos tiques 13, 39, 91, 195 e 299. Se o multiplicador
        nao tivesse teto, o quinto cairia no 403 e o teste com 299 tiques veria
        QUATRO varreduras em vez de cinco.
        """
        gatilhos = (13, 39, 91, 195, 299)
        assert TETO_DA_CARENCIA == 4

        tela = TelaFalsa(roteiro=so_o_nivel_recusa(None))
        rodar_o_laco(cal, tmp_path, tela, ticks=gatilhos[-1])
        assert tela.leituras[CAMPO_DO_NIVEL] == (
            gatilhos[-1] + len(gatilhos) * TENTATIVAS_DE_UMA_VARREDURA
        )

        antes = TelaFalsa(roteiro=so_o_nivel_recusa(None))
        rodar_o_laco(cal, tmp_path, antes, ticks=gatilhos[-1] - 1)
        assert antes.leituras[CAMPO_DO_NIVEL] == (
            gatilhos[-1] - 1 + (len(gatilhos) - 1) * TENTATIVAS_DE_UMA_VARREDURA
        )

    def test_UMA_LEITURA_VALIDA_DEVOLVE_O_MULTIPLICADOR_A_UM(
        self, cal, tmp_path
    ):
        """Se o campo leu, a situacao mudou, e a punicao acumulada deixa de
        valer: a varredura seguinte volta a disparar em `K`, e nao em `2K`."""

        def roteiro(tique):
            # Perde a varredura no 13; o campo volta a sair no 14; para de sair
            # de novo a partir do 15.
            if tique == 14:
                return so_o_nivel_recusa(PISO_GRAVADO[CAMPO_DO_NIVEL])
            return so_o_nivel_recusa(None)

        tela = TelaFalsa(roteiro=roteiro)
        # 14 + 13 = 27: a segunda varredura cai no tique 27 se o multiplicador
        # voltou a 1, e no 40 se nao voltou.
        rodar_o_laco(cal, tmp_path, tela, ticks=27)
        assert tela.leituras[CAMPO_DO_NIVEL] == (
            27 + 2 * TENTATIVAS_DE_UMA_VARREDURA
        )

    def test_A_CARENCIA_E_POR_CAMPO(self, cal, tmp_path):
        """Uma varredura perdida no nivel nao adia a varredura da adena."""

        def roteiro(_tique):
            return {
                CAMPO_DO_NIVEL: None,
                CAMPO_DO_EXP: PISO_GRAVADO[CAMPO_DO_EXP],
                CAMPO_DA_ADENA: None,
            }

        tela = TelaFalsa(roteiro=roteiro)
        rodar_o_laco(cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER)
        assert tela.leituras[CAMPO_DO_NIVEL] == (
            RECUSAS_SEGUIDAS_PARA_VARRER + TENTATIVAS_DE_UMA_VARREDURA
        )
        assert tela.leituras[CAMPO_DA_ADENA] == (
            RECUSAS_SEGUIDAS_PARA_VARRER + TENTATIVAS_DE_UMA_VARREDURA
        )


class TestOQueOUsuarioVE:
    def test_A_MUDANCA_DE_PISO_SAI_UMA_VEZ_NO_LOG_COM_A_FRASE_ACIONAVEL(
        self, cal, tmp_path, caplog
    ):
        vencedor = VIZINHOS_DO_NIVEL[2]  # 210, desvio de +10
        tela = TelaFalsa(roteiro=so_o_nivel_recusa(vencedor))
        with caplog.at_level(logging.INFO, logger="l2scanner"):
            rodar_o_laco(
                cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER + 10
            )
        anuncios = [
            linha
            for linha in caplog.text.splitlines()
            if "voltou a sair com o piso" in linha
        ]
        assert len(anuncios) == 1, anuncios
        linha = anuncios[0]
        assert "210" in linha and "200" in linha and "+10" in linha
        # A FRASE IMPORTA MAIS QUE O NUMERO: o usuario nao deduz "recalibre" de
        # `piso 210`. O criterio e o de `__main__.py:776-784` -- a mensagem tem
        # de dizer o que fazer a respeito.
        assert "envelhec" in linha
        assert "calibrar-renda.bat" in linha

    def test_A_VARREDURA_PERDIDA_DIZ_QUE_O_SUSPEITO_E_O_RETANGULO(
        self, cal, tmp_path, caplog
    ):
        """O M-Y, e ele e a razao de esta mensagem existir.

        Os dois modos de falha se parecem de fora -- o campo para de sair -- e
        pedem consertos OPOSTOS. Perder em TODOS os pisos do alcance e a
        evidencia que separa os dois, e e a unica hora em que o produto pode
        dizer "o retangulo, e nao o brilho" com prova na mao.
        """
        tela = TelaFalsa(roteiro=so_o_nivel_recusa(None))
        with caplog.at_level(logging.INFO, logger="l2scanner"):
            rodar_o_laco(
                cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER
            )
        perdidas = [
            linha
            for linha in caplog.text.splitlines()
            if "RETANGULO" in linha and "varredura" in linha.lower()
        ]
        assert len(perdidas) == 1, caplog.text
        linha = perdidas[0]
        assert "calibrar-renda.bat" in linha
        assert "grama" in linha

    def test_O_BLOCO_POR_INTERVALO_MOSTRA_O_PISO_EM_USO_E_O_DESVIO(
        self, cal, tmp_path, caplog
    ):
        vencedor = VIZINHOS_DO_NIVEL[2]  # 210
        tela = TelaFalsa(roteiro=so_o_nivel_recusa(vencedor))
        with caplog.at_level(logging.INFO, logger="l2scanner"):
            rodar_o_laco(
                cal,
                tmp_path,
                tela,
                ticks=RECUSAS_SEGUIDAS_PARA_VARRER + 3,
                status_a_cada=0.0,
            )
        assert "piso 210 (gravado 200, +10)" in caplog.text

    def test_A_SECAO_DO_PISO_NAO_APARECE_QUANDO_NINGUEM_SAIU_DO_GRAVADO(
        self, cal, tmp_path, caplog
    ):
        """Uma secao vazia todo minuto seria ruido; uma secao que APARECE e o
        aviso."""
        tela = TelaFalsa(
            roteiro=so_o_nivel_recusa(PISO_GRAVADO[CAMPO_DO_NIVEL])
        )
        with caplog.at_level(logging.INFO, logger="l2scanner"):
            rodar_o_laco(
                cal, tmp_path, tela, ticks=3, status_a_cada=0.0
            )
        assert "PISO DE BRILHO EM USO" not in caplog.text

    def test_O_MARCADOR_DE_PISO_NAO_MONTA_NA_LINHA_DO_TIQUE(
        self, cal, tmp_path, caplog
    ):
        """MEDIDO no `03-01`/`03-02`: a largura real desta casa e 76 colunas, e
        a linha do tique com o marcador colado mede 78. Ele sai no bloco por
        intervalo e numa linha de log com latch -- nunca aqui."""
        from l2scanner.renda_console import (
            LARGURA_MAXIMA_DA_LINHA_DO_TIQUE,
            MARCA_DE_TRUNCAGEM,
            PREFIXO_DA_LINHA,
        )

        vencedor = VIZINHOS_DO_NIVEL[2]
        tela = TelaFalsa(roteiro=so_o_nivel_recusa(vencedor))
        with caplog.at_level(logging.INFO, logger="l2scanner"):
            rodar_o_laco(
                cal, tmp_path, tela, ticks=RECUSAS_SEGUIDAS_PARA_VARRER + 5
            )
        linhas = [
            linha[linha.index(PREFIXO_DA_LINHA) :]
            for linha in caplog.text.splitlines()
            if PREFIXO_DA_LINHA + " |" in linha
        ]
        assert linhas
        for linha in linhas:
            assert len(linha) <= LARGURA_MAXIMA_DA_LINHA_DO_TIQUE, linha
            assert MARCA_DE_TRUNCAGEM not in linha, linha
            assert "piso" not in linha, linha

    def test_O_RESUMO_TRAZ_OS_TRES_FATOS_DA_VARREDURA(
        self, cal, tmp_path, caplog
    ):
        """Tres fatos que NAO se somam: quantas rodaram, quantas venceram e em
        que desvio -- no molde de `ContagemDaRenda`."""
        vencedor = VIZINHOS_DO_NIVEL[2]

        def roteiro(tique):
            # A primeira varredura perde (nada sai) e a segunda vence.
            return so_o_nivel_recusa(vencedor if tique > 20 else None)

        tela = TelaFalsa(roteiro=roteiro)
        with caplog.at_level(logging.INFO, logger="l2scanner"):
            rodar_o_laco(cal, tmp_path, tela, ticks=40)
        assert "varreduras de piso" in caplog.text
        assert "2" in caplog.text and "1" in caplog.text
        assert "nivel" in caplog.text


class TestOPortaoDeQueONadaVoltaAoDisco:
    """CTX-6, e o argumento e um incidente MEDIDO.

    Em 2026-08-30 um escritor de calibracao montou do zero o que devia ter
    carregado e apagou **treze moldes de glifo, tres ancoras e a grade de
    negociacao**; o `calibration.json` e gitignored e nao existe `git checkout`
    que traga nada de volta. Um escritor a mais naquele arquivo, rodando a noite
    inteira sem supervisao, e a pior versao possivel daquele incidente.
    """

    def test_RENDA_LACO_NAO_ESCREVE_CALIBRACAO_POR_NENHUM_DOS_QUATRO_CAMINHOS(
        self,
    ):
        achados = escritas_de_calibracao(FONTE_DO_LACO)
        assert not achados, (
            "renda_laco.py passou a escrever calibracao:\n  "
            + "\n  ".join(achados)
        )

    def test_RENDA_PISOS_TAMBEM_NAO(self):
        assert not escritas_de_calibracao(
            Path(__file__).parent.parent / "l2scanner" / "renda_pisos.py"
        )

    @pytest.mark.parametrize(
        "corpo",
        [
            "def f(cal):\n    cal.salvar()\n",
            'def f(cal):\n    getattr(cal, "salvar")()\n',
            "from l2scanner.calibracao import salvar\n\ndef f(cal):\n    salvar(cal)\n",
            'def f():\n    open("calibration.json", "w").write("{}")\n',
        ],
    )
    def test_CONTROLE_POSITIVO_OS_QUATRO_CAMINHOS_SAO_ACUSADOS(
        self, tmp_path, corpo
    ):
        """Os QUATRO, e nao so a chamada obvia.

        Um `grep -c "\\.salvar("` ve o primeiro e perde os tres outros -- e era
        exatamente esse `grep` que ocupava o `<verify>` desta tarefa. Um portao
        fraco ao lado de um forte ensina que o fraco basta.
        """
        alvo = tmp_path / "escritor.py"
        alvo.write_text(corpo, encoding="utf-8")
        assert escritas_de_calibracao(alvo), corpo


def escritas_de_calibracao(caminho: Path) -> list[str]:
    """Todo caminho por que um fonte poderia reescrever o `calibration.json`.

    Compartilhada pelo portao e pelos quatro controles positivos, pela mesma
    razao de `memoria_de_modulo` e `chamadores_das_regras` em
    `tests/test_renda_par.py`: um controle que chamasse outra funcao provaria
    outra coisa.

    OS QUATRO CAMINHOS:

    1. `cal.salvar()` -- a chamada obvia, por atributo;
    2. `getattr(cal, "salvar")()` -- a mesma chamada por nome dinamico;
    3. `salvar(cal)` -- a funcao importada por nome e chamada solta;
    4. `calibration.json` como literal DENTRO DE UMA CHAMADA -- que pega o
       `open(...)`, o `Path(...).write_text` e o `json.dump` direto.

    O QUARTO CAMINHO OLHA DENTRO DA CHAMADA E NAO O ARQUIVO INTEIRO, e a razao
    e a licao medida do `03-02`: um portao textual sobre este arquivo devolveu
    **9 linhas para 1 chamada**, e sete delas eram a prosa que explica o
    mecanismo. Um portao que acusasse prosa cobraria o preco de ENFRAQUECER a
    documentacao para ficar verde -- e a documentacao e onde as razoes moram.
    Aqui a prosa atravessa e a chamada nao.
    """
    achados: list[str] = []
    arvore = ast.parse(Path(caminho).read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        nome = getattr(no.func, "attr", None) or getattr(no.func, "id", None)
        if nome == "salvar":
            achados.append(f"linha {no.lineno}: chamada a `salvar`")
        if nome == "getattr" and len(no.args) >= 2:
            alvo = no.args[1]
            if isinstance(alvo, ast.Constant) and alvo.value == "salvar":
                achados.append(f"linha {no.lineno}: `getattr(..., 'salvar')`")
        for dentro in ast.walk(no):
            if (
                isinstance(dentro, ast.Constant)
                and isinstance(dentro.value, str)
                and "calibration.json" in dentro.value
            ):
                achados.append(
                    f"linha {no.lineno}: `calibration.json` dentro de uma "
                    f"chamada a `{nome}`"
                )
    return achados
