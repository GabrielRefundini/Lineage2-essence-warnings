"""A sonda de fundo da linha, afirmada contra pixels REAIS do jogo.

Tudo aqui roda sobre seis fixtures RESGATADAS de gravacoes de verdade e
versionadas em `tests/fixtures/mercado/`, e NUNCA sobre `recordings/` — a pasta
e gitignored e nao vem de clone limpo, entao um teste que dependesse dela
ficaria verde nesta maquina e amarelo em toda outra. A varredura que PRODUZ os
numeros (`tools/medir_oclusao.py`) e outra coisa e roda no checkout principal:
produzir o dado e producao de dado; prender a regressao e teste.

DE ONDE VEIO CADA UMA
---------------------
Cada fixture e a LINHA INTEIRA da grade (944x45 px), cortada depois de o painel
ser localizado pelas ancoras do `calibration.json` e a grade derivada do
deslocamento gravado (`mercado_grade`, layout `negociacao`, 10 linhas de 45 px):

    linha_limpa_par_f010.png                 pagina-cheia/frame_000010, linha 0
        banda de fundo PAR (moda 48), pagina cheia, sem nada por cima
    linha_limpa_impar_f010.png               pagina-cheia/frame_000010, linha 1
        banda de fundo IMPAR (moda 66) — o par dela existe para provar que a
        sonda NAO depende de conhecer 48 e 66
    linha_sob_tooltip_f015.png               tooltip/frame_000015, linha 0
        coberta pela tooltip semitransparente
    linha_limpa_no_frame_do_tooltip_f015.png tooltip/frame_000015, linha 9
        o MESMO frame, uma linha que a tooltip nao alcanca
    linha_sob_alvo_f024.png                  alvo-sobreposto/frame_000024, linha 0
        coberta pela marcacao de alvo — o caso APERTADO
    linha_limpa_no_frame_do_alvo_f024.png    alvo-sobreposto/frame_000024, linha 5
        o MESMO frame, limpa

POR QUE DISPERSAO, E NAO "A MODA E 48 OU 66"
--------------------------------------------
MEDIDO em `tooltip/frame_000015`: nas linhas 2, 4 e 6 a moda continua 48 mesmo
com a tooltip por cima. Um teste de moda passaria em tres linhas cobertas. O
que separa e a DISPERSAO — a fracao de pixels que se afasta da moda —, que e
auto-referente e nao precisa saber quanto vale o fundo desta pele de jogo.

O TRECHO SEM TEXTO USADO AQUI
-----------------------------
`SONDA_MEDIDA` e o vao entre o fim do nome do item e o comeco dos numeros,
medido pela pesquisa em x ∈ [180, 510) relativo a esquerda da grade. Ele e um
trecho HONESTO para afirmar a primitiva, e nao o valor de producao: quem
escolhe o de producao e a varredura de `tools/medir_oclusao.py` sobre as 8
gravacoes, e o numero dela mora no `calibration.json`. Os testes abaixo afirmam
RELACAO e FAIXA, nunca um valor exato preso — um valor exato viraria refem do
recorte e convidaria ao ajuste circular.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.mercado_geometria import nivel_de_fundo_da_linha

FIXTURES = Path(__file__).parent / "fixtures" / "mercado"

# (dx0, dx1, folga) — o trecho sem texto e as linhas de folga nas pontas.
SONDA_MEDIDA = (180, 510, 2)


def _linha(nome: str) -> np.ndarray:
    caminho = FIXTURES / nome
    imagem = cv2.imread(str(caminho))
    assert imagem is not None, f"fixture ausente: {caminho}"
    return cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)


def _sonda(cinza: np.ndarray) -> tuple[int, float]:
    dx0, dx1, folga = SONDA_MEDIDA
    medido = nivel_de_fundo_da_linha(
        cinza, (dx0, 0, dx1 - dx0, cinza.shape[0]), folga
    )
    assert medido is not None
    return medido


class TestALinhaLimpa:
    """Sem nada por cima, a dispersao fica no chao."""

    @pytest.mark.parametrize(
        "nome",
        [
            "linha_limpa_par_f010.png",
            "linha_limpa_impar_f010.png",
            "linha_limpa_no_frame_do_tooltip_f015.png",
            "linha_limpa_no_frame_do_alvo_f024.png",
        ],
    )
    def test_dispersao_abaixo_de_um_decimo(self, nome: str) -> None:
        _, dispersao = _sonda(_linha(nome))
        assert dispersao < 0.10, f"{nome} deu {dispersao:.4f}"

    def test_a_moda_das_duas_bandas_e_DIFERENTE_e_a_dispersao_NAO(self) -> None:
        """A par le 48, a impar le 66 — e as duas dispersoes sao comparaveis.

        E a propriedade que torna a sonda auto-referente: o resultado nao
        depende de conhecer os dois niveis do layout. Trocar a pele do jogo
        mudaria as duas modas e nao mudaria a decisao.
        """
        moda_par, disp_par = _sonda(_linha("linha_limpa_par_f010.png"))
        moda_impar, disp_impar = _sonda(_linha("linha_limpa_impar_f010.png"))

        assert moda_par != moda_impar
        assert abs(int(moda_par) - int(moda_impar)) >= 8
        assert disp_par < 0.10 and disp_impar < 0.10
        assert abs(disp_par - disp_impar) < 0.05


class TestALinhaCOBERTA:
    """O sinal que a Fase 4 vai usar perto do detector de morte."""

    def test_sob_tooltip_a_dispersao_passa_de_quatro_decimos(self) -> None:
        _, dispersao = _sonda(_linha("linha_sob_tooltip_f015.png"))
        assert dispersao > 0.40, f"tooltip deu {dispersao:.4f}"

    def test_sob_tooltip_contra_a_limpa_do_MESMO_frame(self) -> None:
        _, coberta = _sonda(_linha("linha_sob_tooltip_f015.png"))
        _, limpa = _sonda(_linha("linha_limpa_no_frame_do_tooltip_f015.png"))
        assert coberta > limpa

    def test_sob_a_marcacao_de_alvo_contra_a_limpa_do_MESMO_frame(self) -> None:
        """O caso APERTADO, e por isso a assertiva e a RELACAO.

        A marcacao de alvo e opaca mas cobre menos da linha que a tooltip. O
        valor absoluto e faixa (ele muda com o trecho escolhido); o que nao pode
        mudar e a ordem: coberta acima de limpa, no mesmo frame, com o mesmo
        recorte.
        """
        _, coberta = _sonda(_linha("linha_sob_alvo_f024.png"))
        _, limpa = _sonda(_linha("linha_limpa_no_frame_do_alvo_f024.png"))
        assert coberta > limpa
        assert coberta > 2.0 * limpa


class TestOQueNaoDaPARA_MEDIR:
    """Devolve `None` e nunca levanta — o arquivo inteiro reporta em vez de
    levantar, e o charter dele proibe abrir janela, ler teclado ou escrever."""

    def test_largura_zero(self) -> None:
        cinza = _linha("linha_limpa_par_f010.png")
        assert nivel_de_fundo_da_linha(cinza, (180, 0, 0, 45), 2) is None

    def test_altura_zero(self) -> None:
        cinza = _linha("linha_limpa_par_f010.png")
        assert nivel_de_fundo_da_linha(cinza, (180, 0, 330, 0), 2) is None

    def test_fora_da_imagem_a_direita(self) -> None:
        cinza = _linha("linha_limpa_par_f010.png")
        largura = cinza.shape[1]
        assert nivel_de_fundo_da_linha(cinza, (largura - 5, 0, 330, 45), 2) is None

    def test_comeco_negativo(self) -> None:
        cinza = _linha("linha_limpa_par_f010.png")
        assert nivel_de_fundo_da_linha(cinza, (-10, 0, 330, 45), 2) is None

    def test_folga_que_come_a_linha_inteira(self) -> None:
        cinza = _linha("linha_limpa_par_f010.png")
        assert nivel_de_fundo_da_linha(cinza, (180, 0, 330, 45), 30) is None

    def test_folga_negativa(self) -> None:
        cinza = _linha("linha_limpa_par_f010.png")
        assert nivel_de_fundo_da_linha(cinza, (180, 0, 330, 45), -1) is None


class TestOCharterDoModulo:
    """A geometria MEDE; o limiar de decisao mora no `calibration.json`."""

    def test_nenhum_limiar_de_oclusao_no_fonte(self) -> None:
        import inspect

        import l2scanner.mercado_geometria as geometria

        fonte = inspect.getsource(geometria)
        assert "cv2.imshow" not in fonte
        assert "input(" not in fonte
        assert "LIMIAR_DE_DISPERSAO" not in fonte
        assert "LIMIAR_DE_OCLUSAO" not in fonte
