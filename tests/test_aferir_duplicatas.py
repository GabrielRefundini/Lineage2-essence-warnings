"""O QUE A MEDICAO DE 2026-09-04 DECIDIU: NAO VETAR DUPLICATA.

O PEDIDO: o usuario recebe a mesma pergunta varias vezes. Na `.identidades/`
dele havia 23 assinaturas ativas para 11 pessoas — PIRULITO com 6 copias,
Mostarda com 4 — e 61 marcadores `perguntado_`. Todas abaixo do teto de
contaminacao de 220 px, entao o teto nao e o culpado.

O DESFECHO: NENHUM criterio medido separa "mesma pessoa" de "pessoas
diferentes" com margem que sustente um veto. Este arquivo guarda os numeros
que sustentam esse NAO, para que ele nao seja refeito de memoria — e para que
quem quiser desfaze-lo tenha de derrubar medida, e nao opiniao.

OS TRES NUMEROS QUE DECIDEM

1. OS CONJUNTOS NAO SE SEPARAM. Em todo criterio, o pior par da MESMA pessoa
   fica em 0.000 (ou abaixo) enquanto o melhor par de pessoas DIFERENTES fica
   perto de 0.6. Nao existe corte que aceite um conjunto e recuse o outro.

2. O CRITERIO DE MAIOR MARGEM E SORTE, E ISSO E MEDIDO E NAO OPINADO. Isolar a
   faixa do nome antes de correlacionar da margem 0.294 com altura 8 — e com
   altura 5 da 1.000 para Mostarda x PIRULITO, que sao DUAS PESSOAS, e com
   altura 10 da 0.786. Um parametro cujos vizinhos imediatos produzem veto
   errado acima do limiar nao e um regime: e um ponto sortudo em 57
   assinaturas.

3. O DESLIZAMENTO FUNCIONA E NAO PAGA. Com `+-6` colunas ele barraria 9
   entradas das 53 contra as 6 que a producao ja barra hoje: TRES perguntas
   pouparia, de 53. O preco e o melhor par ERRADO subir de 0.598 para 0.619, e
   essa grandeza esta ANDANDO NA DIRECAO ERRADA conforme o acervo cresce — ela
   foi medida em 0.483 sobre 28 assinaturas em 2026-09-03 e esta em 0.619 sobre
   57 hoje. Trocar 3 perguntas em 53 por uma margem que encolhe, quando o
   desfecho de um veto errado e duas pessoas virarem uma em silencio e para
   sempre, e o lado errado da assimetria que `aprendiz.observar` ja documenta.

E A CAUSA REAL, QUE NENHUM CRITERIO DE SEMELHANCA ALCANCA: as copias nao sao
recortes parecidos com ruido. Em 31 das 57 mais de 10% da tinta cai FORA da
faixa do nome — e texto de OUTRA linha da party window dentro do mesmo recorte
— e a faixa comeca na linha 0 em 10 delas e da linha 5 em diante em 46. O que
varia entre sessoes e a ANCORA do recorte, nao a aparencia do nome. Quem
quiser matar a duplicata mexe na ancoragem, e nao no limiar.

A FIXTURE E O ACERVO REAL, copiado em 2026-09-04: 23 `assinatura_*` ativas mais
30 `esquecida_*` de 20x110, com os rotulos de campo em
`duplicatas_2026_09_04.json` (quem o OLHO le em cada uma) e a ordem de
nascimento em `nascimento_2026_09_04.json` (o git nao guarda mtime). Nada aqui
le a `.identidades/` do usuario.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from l2scanner.identidade import (
    LIMIAR_DE_CASAMENTO,
    Assinatura,
    _correlacionar,
    _deslocar_para_a_esquerda,
    mascara_de_texto,
)
from tools.aferir_duplicatas import (
    bgr_da_mascara,
    carregar,
    criterio_deslizante,
    criterio_por_faixa,
    deslocar,
    ler_assinaturas,
    retrato_dos_recortes,
    simulacao_de_nascimento,
    tabela_dos_pares,
)

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "tests" / "fixtures" / "acervo_real_2026_09_04"


@pytest.fixture(scope="module")
def acervo() -> dict[str, np.ndarray]:
    """As 53 assinaturas da fixture, por prefixo de chave."""
    return {chave[:8]: a.mascara for chave, a in ler_assinaturas(PASTA)}


@pytest.fixture(scope="module")
def simulacao() -> dict:
    itens, nascimento = carregar(PASTA)
    return simulacao_de_nascimento(itens, nascimento)


@pytest.fixture(scope="module")
def tabela() -> dict:
    """So os dois criterios que sustentam a decisao.

    A tabela inteira e a saida da ferramenta, e leva 16 segundos: nove
    criterios sobre 1431 pares. Aqui rodam os dois que decidem — a linha de
    base e o candidato que chegou mais perto de valer a pena.
    """
    itens, _ = carregar(PASTA)
    return tabela_dos_pares(itens, apenas=("alinhado (producao)", "desliza h +-6"))


# ---------------------------------------------------------------------------
# 1. A FERRAMENTA MEDE COM A PRODUCAO, e nao com uma copia dela
# ---------------------------------------------------------------------------


class TestAMedicaoNaoRederivaAProducao:
    """A licao 1 do CLAUDE.md, virada teste.

    Tres medicoes de improviso sairam erradas em 2026-09-02, todas
    re-derivando o que a producao ja faz por dentro. As duas pecas que esta
    ferramenta precisou escrever ficam AMARRADAS as de producao aqui.
    """

    def test_o_deslocamento_para_a_esquerda_e_o_da_producao(self, acervo):
        """Onde os dois sentidos se encontram, os dois resultados sao iguais."""
        mascara = acervo["2d85b9d1"]
        for colunas in (1, 2, 3, 6, 25):
            producao = _deslocar_para_a_esquerda(mascara, colunas)
            assert producao is not None
            assert np.array_equal(deslocar(mascara, -colunas), producao), (
                f"deslocar(-{colunas}) divergiu de `_deslocar_para_a_esquerda`: "
                f"1 px de diferenca derruba a correlacao de 1.000 para 0.24"
            )

    def test_o_deslocamento_para_a_direita_e_o_espelho(self, acervo):
        mascara = acervo["2d85b9d1"]
        espelhado = deslocar(deslocar(mascara, 4), -4)
        assert np.array_equal(espelhado[:, : 110 - 4], mascara[:, : 110 - 4])

    def test_a_ponte_para_o_recorte_volta_a_mesma_mascara(self, acervo):
        """Sem isto a linha de base mediria outra coisa que nao a producao."""
        for chave in ("2d85b9d1", "1023b462", "ceafac77"):
            assert np.array_equal(
                mascara_de_texto(bgr_da_mascara(acervo[chave])), acervo[chave]
            )


# ---------------------------------------------------------------------------
# 2. OS ROTULOS DE CAMPO — a verdade contra a qual tudo aqui e medido
# ---------------------------------------------------------------------------


class TestOsRotulosDeCampo:
    def test_a_fixture_tem_as_53_do_acervo_real(self, acervo):
        assert len(acervo) == 53

    def test_todas_tem_rotulo_e_data_de_nascimento(self, acervo):
        rotulos = json.loads(
            (RAIZ / "tests/fixtures/duplicatas_2026_09_04.json").read_text("utf-8")
        )
        nascimento = json.loads(
            (RAIZ / "tests/fixtures/nascimento_2026_09_04.json").read_text("utf-8")
        )
        assert len(rotulos) == 53
        assert len(nascimento) == 53
        assert {c[:8] for c in rotulos} == set(acervo)

    def test_as_seis_copias_do_PIRULITO_estao_todas_la(self):
        """O caso que o usuario relatou: seis perguntas para a mesma pessoa."""
        rotulos = json.loads(
            (RAIZ / "tests/fixtures/duplicatas_2026_09_04.json").read_text("utf-8")
        )
        ativas = {
            c.name.split("_", 1)[1].removesuffix(".json")
            for c in PASTA.glob("assinatura_*.json")
        }
        pirulitos = [c for c in ativas if rotulos[c] == "PIRULITO"]
        assert len(pirulitos) == 6


# ---------------------------------------------------------------------------
# 3. A REFUTACAO DA IDEIA DE MAIOR MARGEM
# ---------------------------------------------------------------------------


class TestIsolarAFaixaDoNomeEUmPontoSortudo:
    """Ela ganha a tabela e perde a vizinhanca. Fica refutada por escrito.

    Ela e a ideia obvia depois que a primeira (ancorar na primeira coluna com
    texto) ja tinha caido em 2026-09-03. Esta cai por outro motivo, e ele e
    pior: ela nao erra pouco, ela erra CATASTROFICAMENTE um passo ao lado.
    """

    def test_com_altura_5_duas_pessoas_diferentes_pontuam_1_000(self, acervo):
        pontuar = criterio_por_faixa(5, 6)
        valor = pontuar(acervo["1023b462"], acervo["7838f437"])
        assert valor == pytest.approx(1.0, abs=0.001), (
            f"Mostarda x PIRULITO deu {valor:.3f}. O 1.000 medido e o motivo de "
            f"esta familia estar recusada"
        )

    def test_com_altura_10_um_par_errado_ja_passa_do_limiar(self, acervo):
        pontuar = criterio_por_faixa(10, 6)
        valor = pontuar(acervo["7838f437"], acervo["e09bfcb6"])
        assert valor >= LIMIAR_DE_CASAMENTO, (
            "PIRULITO x TITANDER passou do limiar com altura 10; se algum dia "
            "nao passar, a vizinhanca mudou e a medicao inteira precisa voltar"
        )

    def test_a_altura_8_e_a_UNICA_que_parece_boa(self, acervo):
        """A margem de 0.294 existe. Ela so nao sobrevive a um passo ao lado."""
        pontuar = criterio_por_faixa(8, 6)
        assert pontuar(acervo["1023b462"], acervo["7838f437"]) < LIMIAR_DE_CASAMENTO


# ---------------------------------------------------------------------------
# 4. O DESLIZAMENTO: funciona, e nao paga
# ---------------------------------------------------------------------------


class TestODeslizamentoFuncionaENaoPaga:
    def test_o_par_que_o_alinhamento_perde_o_deslizamento_acha(self, acervo):
        """PIRULITO 107 px contra PIRULITO 125 px: a mesma pessoa, 2 px ao lado."""
        alinhado = _correlacionar(acervo["2d85b9d1"], acervo["f4aee0a1"])
        deslizado = criterio_deslizante(6)(acervo["2d85b9d1"], acervo["f4aee0a1"])
        assert alinhado < LIMIAR_DE_CASAMENTO
        assert deslizado >= LIMIAR_DE_CASAMENTO
        assert deslizado - alinhado > 0.5, (
            "o ganho do deslizamento nesta copia era 0.880 contra 0.336"
        )

    def test_e_o_MESMO_deslizamento_aproxima_duas_pessoas_diferentes(self, acervo):
        """O preco, no mesmo numero: PIRULITO x TITANDER sobe para 0.619.

        0.619 e 0.131 abaixo do limiar. A mesma grandeza foi medida em 0.483
        sobre 28 assinaturas em 2026-09-03: ela anda para cima conforme o
        acervo cresce, e e por isso que os 0.131 nao sao margem para apostar.
        """
        valor = criterio_deslizante(6)(acervo["7838f437"], acervo["e09bfcb6"])
        assert valor == pytest.approx(0.619, abs=0.002)
        assert valor < LIMIAR_DE_CASAMENTO


# ---------------------------------------------------------------------------
# 5. A SIMULACAO DE NASCIMENTO — o numero que decide
# ---------------------------------------------------------------------------


class TestASimulacaoDeNascimento:
    """Percorre o acervo na ordem em que ele nasceu, com a producao inteira.

    E o contrafactual honesto: no instante em que cada entrada nasceu, o acervo
    tinha as anteriores dentro dele.
    """

    def test_a_producao_de_hoje_ja_barra_seis(self, simulacao):
        """A linha de base nao e zero, e comecar por ela evita superestimar."""
        assert len(simulacao["producao hoje"]["vetadas"]) == 6

    def test_deslizar_dois_pixels_nao_barra_nada_a_mais(self, simulacao):
        assert len(simulacao["producao + desliza h +-2"]["vetadas"]) == 6

    def test_deslizar_seis_barra_TRES_a_mais_em_53(self, simulacao):
        """Tres perguntas pouparia. E o tamanho real do premio."""
        assert len(simulacao["producao + desliza h +-6"]["vetadas"]) == 9

    def test_nenhum_veto_da_simulacao_e_de_pessoas_diferentes(self, simulacao):
        """O que NAO aconteceu, e que por isso mesmo precisa ficar escrito.

        Todos os vetos das quatro variantes sao da mesma pessoa que a barrou —
        conferido no olho, uma imagem por par, em 2026-09-04. E por isso que a
        recusa nao e "o criterio erra": e "o criterio acerta pouco e a margem
        que protege o acerto esta encolhendo".
        """
        for linha in simulacao.values():
            assert linha["vetadas"], "uma variante sem veto nenhum nao mede nada"


# ---------------------------------------------------------------------------
# 6. O QUE AS COPIAS SAO — a causa, medida
# ---------------------------------------------------------------------------


class TestACausaEAAncoraDoRecorte:
    def test_metade_do_acervo_carrega_texto_de_OUTRA_linha(self):
        itens, _ = carregar(PASTA)
        retrato = retrato_dos_recortes(itens)
        assert retrato["sujas"] == 31, (
            "31 de 57 tinham mais de 10% da tinta fora da faixa do nome. Se "
            "este numero mudou, a fixture mudou"
        )

    def test_a_faixa_do_nome_comeca_em_lugares_diferentes(self):
        """Se a ancora fosse estavel, este histograma teria uma coluna so."""
        itens, _ = carregar(PASTA)
        inicios = retrato_dos_recortes(itens)["inicios"]
        assert len(inicios) >= 6, (
            "a faixa do nome comecava em 8 linhas diferentes das 11 possiveis"
        )
        assert inicios[0] == 10


# ---------------------------------------------------------------------------
# 7. O VEREDITO, no formato em que a ferramenta o entrega
# ---------------------------------------------------------------------------


class TestATabelaSustentaONao:
    def test_nem_a_producao_nem_o_deslizamento_separam_os_conjuntos(self, tabela):
        """A pergunta que o encargo fez, respondida em uma linha.

        Os OUTROS sete criterios estao na saida de `tools/aferir_duplicatas.py`
        e nao aqui, por tempo de suite; os dois que decidem estao aqui. A
        familia da faixa, que e a que mais parecia boa, esta refutada logo
        acima com pares nomeados, que e uma prova mais forte do que uma media.
        """
        for nome, linha in tabela.items():
            assert linha["pior_certo"] < linha["melhor_errado"], (
                f"{nome} separou os conjuntos. Se isto ficou verde, o dado "
                f"mudou e a decisao de nao implementar precisa ser refeita"
            )

    def test_o_deslizamento_de_6_tem_margem_de_0_131(self, tabela):
        linha = tabela["desliza h +-6"]
        assert linha["melhor_errado"] == pytest.approx(0.619, abs=0.002)
        assert linha["margem"] == pytest.approx(0.131, abs=0.002)

    def test_a_producao_de_hoje_tem_margem_MAIOR(self, tabela):
        """Deslizar CUSTA margem. E o outro lado da conta."""
        assert tabela["alinhado (producao)"]["margem"] > tabela["desliza h +-6"]["margem"]
