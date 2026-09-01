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

# O trecho que a VARREDURA de `tools/medir_oclusao.py` escolheu sobre as 8
# gravacoes, e que ela grava em `mercado_sonda_do_fundo`. Ele NAO e o de cima: a
# pesquisa mediu [180, 510) em tres frames; a varredura mede sobre 478 frames de
# campo e contra o gabarito. O numero mora no `calibration.json` — gitignored, e
# nenhum teste o le —, mas a RELACAO que ele produz fica prendida aqui, para que
# uma mudanca na primitiva nao invalide calado o numero que os planos 02-04 e
# 02-05 consomem.
#
# ELE MUDOU DUAS VEZES POR DEFEITO E UMA POR REDESENHO, e as tres entradas
# ficam aqui porque cada uma custou campo:
#
#   [207, 417)  ate 2026-08-31. Ficava EM CIMA da metade direita da coluna do
#               NOME (159 px, 49% dela) e recusava toda linha de nome comprido
#               como se houvesse tooltip. O gabarito de entao nao tinha um unico
#               nome longo — a tinta mais funda das quatro paginas limpas parava
#               em x=178 —, entao a sobreposicao nunca apareceu na medicao. Em
#               campo apareceu: 31 paginas perdidas na aba Enhancement > Scrolls.
#   [246, 396)  o conserto de 31/08. Nasceu com margem NEGATIVA: encostava em
#               x=246, que e a ponta da tinta de `...Enchant C-grade Armor` (40
#               ch). `...Enchant C-grade Weapon` (41 ch) inka ate x=255, e as
#               DEZ linhas dele foram recusadas. Um caractere de diferenca.
#   a BANDA     2026-09-01. A premissa dos dois primeiros era que existisse uma
#               faixa vazia A DIREITA do nome. Nao existe: as colunas do nome e
#               da quantidade sao adjacentes e o nome cresce para dentro do
#               espaco da sonda. A banda usa a janela INTEIRA em x e mede numa
#               margem VERTICAL, onde o nome nao chega — a linha tem 45 px de
#               altura e o texto ocupa dy[15, 27].
#
# `(dx0, dx1, dy0, dy1, folga)`. Escolhida por `tools/medir_oclusao.py` sobre as
# 9 gravacoes do censo, pela folga no PIOR CASO sob deriva de +-2 px na origem
# da linha.
BANDA_ESCOLHIDA_PELA_VARREDURA = (42, 489, 3, 11, 0)


def _linha(nome: str) -> np.ndarray:
    caminho = FIXTURES / nome
    imagem = cv2.imread(str(caminho))
    assert imagem is not None, f"fixture ausente: {caminho}"
    return cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)


def _sonda(
    cinza: np.ndarray, trecho: tuple[int, int, int] = SONDA_MEDIDA
) -> tuple[int, float]:
    dx0, dx1, folga = trecho
    medido = nivel_de_fundo_da_linha(
        cinza, (dx0, 0, dx1 - dx0, cinza.shape[0]), folga
    )
    assert medido is not None
    return medido


def _banda(
    cinza: np.ndarray,
    faixa: tuple[int, int, int, int, int] = BANDA_ESCOLHIDA_PELA_VARREDURA,
) -> tuple[int, float]:
    """A banda de PRODUCAO: janela inteira em x, faixa fina em y."""
    dx0, dx1, dy0, dy1, folga = faixa
    medido = nivel_de_fundo_da_linha(
        cinza, (dx0, dy0, dx1 - dx0, dy1 - dy0), folga
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


# As oito linhas LIMPAS versionadas, e as duas COBERTAS. As duas ultimas limpas
# entraram em 2026-09-01: sao as paridades de banda de `Protecting Scroll:
# Enchant C-grade Weapon` (41 caracteres, tinta ate x=255), o nome que derrubou
# a sonda de 31/08.
LIMPAS_VERSIONADAS = (
    "linha_limpa_par_f010.png",
    "linha_limpa_impar_f010.png",
    "linha_limpa_no_frame_do_tooltip_f015.png",
    "linha_limpa_no_frame_do_alvo_f024.png",
    "linha_limpa_nome_longo_par_f060.png",
    "linha_limpa_nome_longo_impar_f060.png",
    "linha_limpa_nome_longo_weapon_par_f000.png",
    "linha_limpa_nome_longo_weapon_impar_f000.png",
)
COBERTAS_VERSIONADAS = (
    "linha_sob_tooltip_f015.png",
    "linha_sob_alvo_f024.png",
)


class TestNaBandaQueAVarreduraESCOLHEU:
    """A mesma relacao, na banda que foi para o `calibration.json`.

    Esta e a geometria de PRODUCAO: e ela que o 02-04 usa para recusar linha
    coberta. Sem estas asserções, alterar a primitiva quebraria o numero gravado
    sem quebrar teste nenhum — e o numero so seria reconferido na proxima vez
    que alguem rodasse a varredura, que precisa de `recordings/`.
    """

    def test_sob_tooltip_contra_a_limpa_do_MESMO_frame(self) -> None:
        _, coberta = _banda(_linha("linha_sob_tooltip_f015.png"))
        _, limpa = _banda(_linha("linha_limpa_no_frame_do_tooltip_f015.png"))
        assert coberta > 0.30
        assert coberta > limpa

    def test_sob_a_marcacao_de_alvo_contra_a_limpa_do_MESMO_frame(self) -> None:
        """O CASO APERTADO, e ele deixou de ser apertado.

        Em TODA sonda horizontal ja medida quem apertava era a marcacao de alvo,
        nunca a tooltip: 0,077 / 0,022 / 0,021 contra 0,32 a 0,62. A banda le a
        mesma marcacao em 0,2659, e a causa e geometrica — o marcador e uma
        MOLDURA em volta da linha, e a borda horizontal dela atravessa a largura
        inteira no ALTO. Uma sonda de 150x41 px cruza essa borda em ~2 de 41
        linhas de pixel; a banda de 447x8, em 2 de 8.
        """
        _, coberta = _banda(_linha("linha_sob_alvo_f024.png"))
        _, limpa = _banda(_linha("linha_limpa_no_frame_do_alvo_f024.png"))
        assert coberta > limpa
        assert coberta > 10.0 * limpa

    def test_as_linhas_limpas_ficam_no_chao(self) -> None:
        """TODAS elas, e as duas de `Weapon` sao a razao de este teste existir.

        `linha_limpa_nome_longo_weapon_*_f000` sao as duas paridades de banda de
        `Protecting Scroll: Enchant C-grade Weapon` — 41 caracteres, tinta ate
        x=255, sem tooltip nenhuma. Na sonda [246, 396) elas liam 0,0114 e
        0,0119 contra um limiar de 0,003607, e as dez linhas de cada frame eram
        recusadas. Na banda leem 0,0036 e 0,0020.
        """
        for nome in LIMPAS_VERSIONADAS:
            _, dispersao = _banda(_linha(nome))
            assert dispersao < 0.05, f"{nome} deu {dispersao:.4f}"

    def test_o_COMPRIMENTO_DO_NOME_nao_move_a_leitura(self) -> None:
        """27, 40 e 41 caracteres leem a MESMA coisa. E a propriedade inteira.

        A sonda horizontal nao tinha esta propriedade e nao havia como te-la: a
        dispersao dela era funcao do quanto de glifo caia dentro do recorte,
        entao ela subia com o comprimento do nome por construcao. Foi assim que
        um caractere a mais virou 31 paginas perdidas.

        A banda mede numa faixa de altura onde nome nenhum escreve, entao o
        comprimento nao entra na conta. Aqui isso deixa de ser prosa: as
        paridades PARES de `Armor` (40 ch) e de `Weapon` (41 ch) tem de ler a
        mesma dispersao, dentro de um chao comum.
        """
        _, armor = _banda(_linha("linha_limpa_nome_longo_par_f060.png"))
        _, weapon = _banda(_linha("linha_limpa_nome_longo_weapon_par_f000.png"))
        _, curto = _banda(_linha("linha_limpa_par_f010.png"))
        assert armor < 0.01 and weapon < 0.01 and curto < 0.01
        assert abs(armor - weapon) < 0.002
        assert abs(curto - weapon) < 0.002

    def test_as_duas_populacoes_NAO_se_tocam(self) -> None:
        """O controle negativo do arquivo: uma ordem de grandeza entre elas.

        Um sinal que so precisasse aceitar linha limpa se satisfaria lendo zero
        sempre. Este teste exige que a MENOR cobertura conhecida esteja pelo
        menos 10x acima da MAIOR linha limpa conhecida — a folga que a sonda
        [246, 396) nao tinha (1,8x contra este mesmo material).
        """
        limpas = [_banda(_linha(n))[1] for n in LIMPAS_VERSIONADAS]
        cobertas = [_banda(_linha(n))[1] for n in COBERTAS_VERSIONADAS]
        pior_limpa, melhor_coberta = max(limpas), min(cobertas)
        assert melhor_coberta > 10.0 * pior_limpa, (
            f"pior LIMPA {pior_limpa:.4f}, melhor COBERTA {melhor_coberta:.4f}"
        )


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
