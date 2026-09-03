"""O planejador puro da varredura: quais pisos tentar, e em que ORDEM.

O QUE ESTE ARQUIVO PRENDE
=========================
1. **Que o alcance nao encolha para a `largura_da_banda` gravada.** E a
   tentacao obvia — a banda esta no arquivo, e usa-la parece a leitura fiel da
   calibracao. Mas as larguras gravadas sao 4/3/5, que dao meia-banda de 2/1/2
   passos, e o M-S mediu deslocamento de **4 passos**. Andar so dentro da banda
   gravada **nao teria salvo o caso real**, e um alcance que nao alcanca o
   unico caso medido e um requisito cumprido no papel.
2. **Que a ordem nao vire "todos os de cima, depois todos os de baixo".** Do
   mais perto para o mais longe porque a banda ANDA e nao salta; alternando o
   sinal porque o deslocamento foi medido subindo e o cenario muda nos dois
   sentidos. A ordem decide quantas leituras de OCR o pior caso custa.
3. **Que o modulo nao arraste o mundo.** Ele recebe inteiros e devolve
   inteiros. O portao e por ARVORE DE SINTAXE e enumera `ast.Import` **e**
   `ast.ImportFrom`, porque um `grep -E "^import cv2"` nao pega
   `from cv2 import ...`, nem `from . import calibracao`, nem
   `import l2scanner.calibracao` — as tres formas por que o OpenCV entraria
   sem ninguem ver.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from l2scanner.renda_pisos import (
    ALCANCE_EM_PASSOS,
    PASSO_DA_GRADE,
    PISO_MAXIMO,
    PISO_MINIMO,
    pisos_vizinhos,
)

FONTE_DOS_PISOS = Path(__file__).parent.parent / "l2scanner" / "renda_pisos.py"

# OS TRES CAMPOS DA CALIBRACAO REAL, com a `largura_da_banda` que cada um tem
# gravada. Escritos aqui e nao importados: sao a VERDADE DE CAMPO contra a qual
# o alcance foi decidido, e importa-los do modulo que eles julgam faria o teste
# concordar consigo mesmo.
BANDAS_GRAVADAS = (
    ("EXP (barra_esquerda)", 155, 4),
    ("adena (barra_direita)", 190, 3),
    ("nivel", 210, 5),
)

# O M-S, e ele e a procedencia do alcance: a banda util do EXP da Faerlina
# andou de `140..170` para `160..180` em 8,5 h -- **20 unidades de brilho**, que
# sao 4 passos de 5.
DESLOCAMENTO_MEDIDO_EM_PASSOS = 4


class TestASequencia:
    def test_A_ORDEM_E_DO_MAIS_PERTO_AO_MAIS_LONGE_ALTERNANDO_O_SINAL(self):
        assert pisos_vizinhos(piso=155, largura_da_banda=4) == (
            160,
            150,
            165,
            145,
            170,
            140,
            175,
            135,
        )

    def test_O_PISO_GRAVADO_NAO_ESTA_NA_SEQUENCIA(self):
        """Ele ja foi tentado no proprio tique; repeti-lo custaria uma leitura
        de OCR para saber o que ja se sabe."""
        for _rotulo, piso, largura in BANDAS_GRAVADAS:
            assert piso not in pisos_vizinhos(
                piso=piso, largura_da_banda=largura
            )

    def test_SAO_OITO_TENTATIVAS_NO_PIOR_CASO(self):
        for _rotulo, piso, largura in BANDAS_GRAVADAS:
            assert (
                len(pisos_vizinhos(piso=piso, largura_da_banda=largura))
                == 2 * ALCANCE_EM_PASSOS
            )

    def test_A_SEQUENCIA_NAO_TEM_REPETIDOS(self):
        vizinhos = pisos_vizinhos(piso=155, largura_da_banda=4)
        assert len(set(vizinhos)) == len(vizinhos)


class TestOAlcanceNaoSaiDaLarguraGravada:
    """C-11: a `largura_da_banda` e a ORIGEM da grade e nunca o limite dela."""

    def test_A_LARGURA_GRAVADA_NAO_ENCOLHE_A_SEQUENCIA(self):
        """Os tres campos reais, com as tres larguras reais, dao a MESMA
        quantidade de vizinhos — 8 — apesar de as larguras serem 4, 3 e 5."""
        tamanhos = {
            len(pisos_vizinhos(piso=piso, largura_da_banda=largura))
            for _rotulo, piso, largura in BANDAS_GRAVADAS
        }
        assert tamanhos == {8}

    def test_A_LARGURA_AUSENTE_DA_A_MESMA_SEQUENCIA(self):
        """`largura_da_banda` e OPCIONAL no esquema (`calibracao.py:1530`) e
        calibracoes antigas nao a tem. O alcance de fabrica NAO depende dela."""
        assert pisos_vizinhos(
            piso=155, largura_da_banda=None
        ) == pisos_vizinhos(piso=155, largura_da_banda=4)

    def test_O_ALCANCE_ALCANCA_O_UNICO_CASO_MEDIDO(self):
        """O M-S: a banda do EXP andou de `140..170` para `160..180`.

        O piso gravado e 155 (o centro da banda velha) e o centro da banda NOVA
        e 170. Se a sequencia nao contivesse 170, a varredura teria perdido o
        unico deslocamento que alguem mediu — e o requisito seria cumprido no
        papel.
        """
        assert 170 in pisos_vizinhos(piso=155, largura_da_banda=4)

    def test_A_MEIA_BANDA_GRAVADA_TERIA_PERDIDO_O_CASO_MEDIDO(self):
        """O CONTROLE do teste acima, e ele e o que da sentido ao numero.

        Com alcance igual a meia-banda gravada (4 // 2 = 2 passos), 170 fica de
        fora. E a refutacao executavel de "use a largura que esta no arquivo".
        """
        meia_banda = 4 // 2
        assert meia_banda < DESLOCAMENTO_MEDIDO_EM_PASSOS
        assert 170 not in pisos_vizinhos(
            piso=155, largura_da_banda=4, alcance=meia_banda
        )


class TestOTruncamentoDeOitoBits:
    """Um piso fora de `0..255` produz mascara vazia ou cheia: leitura
    garantidamente perdida, e tempo de OCR jogado fora num tique em apuros."""

    def test_NENHUM_PISO_NEGATIVO_E_A_SEQUENCIA_ENCURTA_EM_VEZ_DE_LEVANTAR(self):
        vizinhos = pisos_vizinhos(piso=3, largura_da_banda=None)
        assert vizinhos == (8, 13, 18, 23)
        assert all(v >= PISO_MINIMO for v in vizinhos)

    def test_NENHUM_PISO_ACIMA_DE_255(self):
        """Tres dos oito caem fora do teto e a sequencia fica com CINCO.

        Ela nao e recompletada com vizinhos mais distantes do lado que ainda
        cabe: o alcance e uma afirmacao sobre quanto a banda ANDOU, e nao uma
        cota de oito tentativas a cumprir.
        """
        vizinhos = pisos_vizinhos(piso=250, largura_da_banda=None)
        assert vizinhos == (255, 245, 240, 235, 230)
        assert all(v <= PISO_MAXIMO for v in vizinhos)

    def test_UM_PISO_NO_EXTREMO_NAO_DEVOLVE_SEQUENCIA_VAZIA_SEM_RAZAO(self):
        assert pisos_vizinhos(piso=0, largura_da_banda=None) == (5, 10, 15, 20)


class TestOPassoEParametroPorqueAIncertezaA1EstaDeclarada:
    """A leitura "largura e contagem de passos de 5, piso gravado e centro" foi
    DERIVADA do fonte do calibrador e nao ha teste afirmando-a de fora. Se ela
    cair, muda-se UM lugar."""

    def test_O_PASSO_DE_FABRICA_CONCORDA_COM_O_DO_CALIBRADOR(self):
        """Duas definicoes do mesmo passo e como elas divergem.

        O valor e COPIADO e nao importado, e a medicao esta no fonte: importar
        `calibrar_renda` arrasta **353 modulos** e **~1,0 s**, com `cv2`,
        `numpy` e `argparse` dentro (medido em 2026-09-03). Este teste e o que
        paga o preco de importar o calibrador — uma vez, na suite — para que a
        producao nao pague.
        """
        from l2scanner.calibrar_renda import PASSO_DA_GRADE_DE_PISOS

        assert PASSO_DA_GRADE == PASSO_DA_GRADE_DE_PISOS

    def test_UM_PASSO_DIFERENTE_PRODUZ_A_GRADE_DAQUELE_PASSO(self):
        assert pisos_vizinhos(piso=155, largura_da_banda=4, passo=10) == (
            165,
            145,
            175,
            135,
            185,
            125,
            195,
            115,
        )

    def test_O_ALCANCE_DE_FABRICA_E_O_DESLOCAMENTO_MEDIDO(self):
        assert ALCANCE_EM_PASSOS == DESLOCAMENTO_MEDIDO_EM_PASSOS

    def test_O_ALCANCE_CITA_A_PROCEDENCIA_NO_FONTE(self):
        """O numero e MEDICAO e nao escolha, e um numero medido tem de dizer de
        onde veio — senao a proxima pessoa o ajusta por gosto."""
        fonte = FONTE_DOS_PISOS.read_text(encoding="utf-8")
        assert "01-MEDICOES-DE-CAMPO.md" in fonte
        assert "140..170" in fonte and "160..180" in fonte
        assert "8,5" in fonte


def importados_por(caminho: Path) -> set[str]:
    """Os modulos de TOPO que um fonte importa, por arvore de sintaxe.

    Compartilhada pelo portao e pelo controle positivo, pela mesma razao de
    `memoria_de_modulo` em `tests/test_renda_par.py`: um controle que chamasse
    outra funcao provaria outra coisa.

    ELA ENUMERA `ast.Import` **E** `ast.ImportFrom`, e devolve **todos os
    segmentos** de cada caminho pontuado, e nao so o primeiro.

    O SEGUNDO PONTO CAIU PELO CONTROLE POSITIVO, E FICA ESCRITO PORQUE E O
    RESULTADO. A primeira versao desta funcao guardava so o primeiro segmento e
    o caminho inteiro — e com isso `import l2scanner.calibracao` virava
    `{"l2scanner", "l2scanner.calibracao"}`, sem `calibracao` em lugar nenhum, e
    passava direto pelo portao. Dois dos seis controles ficaram vermelhos na
    primeira rodada e derrubaram a funcao. **Um portao que so o autor testa e um
    portao que so o autor acredita.**
    """
    nomes: set[str] = set()

    def _guardar(caminho_pontuado: str) -> None:
        nomes.add(caminho_pontuado)
        nomes.update(caminho_pontuado.split("."))

    arvore = ast.parse(Path(caminho).read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                _guardar(alias.name)
        elif isinstance(no, ast.ImportFrom):
            if no.module:
                _guardar(no.module)
            # `from . import calibracao` -- o modulo esta nos ALIASES, e sem
            # esta linha o import relativo por nome entraria sem ser visto.
            for alias in no.names:
                _guardar(alias.name)
    return nomes


PESADOS = ("cv2", "numpy", "np", "calibracao", "calibrar_renda", "ocr")


class TestOPortaoDoModuloLeve:
    def test_RENDA_PISOS_NAO_IMPORTA_NADA_PESADO(self):
        achados = sorted(importados_por(FONTE_DOS_PISOS) & set(PESADOS))
        assert not achados, (
            "renda_pisos.py passou a arrastar "
            f"{achados} — ele recebe inteiros e devolve inteiros"
        )

    @pytest.mark.parametrize(
        "linha",
        [
            "import cv2",
            "from cv2 import imread",
            "from . import calibracao",
            "from .calibracao import Calibracao",
            "import l2scanner.calibracao",
            "from l2scanner.ocr import ler_texto",
        ],
    )
    def test_CONTROLE_POSITIVO_AS_SEIS_FORMAS_DE_ARRASTAR_SAO_ACUSADAS(
        self, tmp_path, linha
    ):
        """As seis, e nao a obvia: e o defeito do `grep` ancorado em
        `^import X` que esta revisao removeu do `<verify>` deste plano."""
        alvo = tmp_path / "pesado.py"
        alvo.write_text(linha + "\n", encoding="utf-8")
        assert importados_por(alvo) & set(PESADOS)

    def test_O_MODULO_NAO_TEM_MEMORIA(self):
        from tests.test_renda_par import memoria_de_modulo

        achados = memoria_de_modulo(FONTE_DOS_PISOS)
        assert not achados, (
            "renda_pisos.py ganhou memoria:\n  " + "\n  ".join(achados)
        )
