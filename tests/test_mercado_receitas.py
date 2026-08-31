"""O `[[receita]]`, a margem de craft e o desenho dela. ANAL-04.

NADA AQUI TOCA O `config.toml` REAL NEM A `.mercado/` REAL. Todo TOML nasce em
`tmp_path` e toda observacao e montada a mao — e o que permite a suite inteira
rodar no Python global, sem WinRT, sem frame e sem o material de producao do
usuario.

O QUE ESTES TESTES PRENDEM, EM UMA FRASE
=========================================
Que a margem **quebra em vez de adivinhar**. Um ingrediente sem observacao, um
nome ambiguo, um `rende = true`: cada um deles, se passasse, produziria um
numero perfeitamente formatado e completamente falso. Esse e o unico modo de
falha que esta fase existe para combater, e ele nao da erro em lugar nenhum —
ele sai bonito no console.
"""

from __future__ import annotations

import inspect
import logging
from datetime import datetime, timedelta
from fractions import Fraction

import pytest

from l2scanner import mercado_analise as analise
from l2scanner.config import (
    ComponenteDaReceita,
    Receita,
    ReceitaInvalida,
    ler_receitas,
)
from l2scanner.mercado_registro import ObservacaoLida

# Ingenuos, hora local, sem `tzinfo` — e o que `Relogio.agora()` devolve e o que
# `campos_da_observacao` escreve com `.isoformat()`.
AGORA = datetime(2026, 8, 31, 21, 15, 0)


# ===========================================================================
# A NOMENCLATURA PROIBIDA — a tupla que a Task 2 prende item por item
# ===========================================================================

# OS DOIS LADOS DA CONTA SAO MENOR PEDIDO VISIVEL, OU SEJA **OFERTAS**. O
# scanner ve o que estao PEDINDO no quadro; ele nao ve transacao nenhuma. Uma
# margem que se chamasse "lucro" prometeria um ganho que ninguem realizou, e
# "preco de venda" prometeria uma venda que ninguem fez.
#
# A comparacao e em CAIXA BAIXA dos dois lados, e o acento entra nas duas
# formas porque o texto do console e ASCII mas a docstring de um autor
# distraido nao seria.
EXPRESSOES_PROIBIDAS_DA_MARGEM = (
    "lucro",
    "preco de venda",
    "preço de venda",
    "lucro bruto",
)


# ===========================================================================
# TASK 1 — `ler_receitas`, no molde de `ler_bosses` + `_boss_de_dict`
# ===========================================================================


def _escrever(tmp_path, texto: str):
    caminho = tmp_path / "config.toml"
    caminho.write_text(texto, encoding="utf-8")
    return caminho


RECEITA_VALIDA = """
[[receita]]
produto = "Dragon Belt"
rende = 1
componentes = [
  { item = "Common Aztac", quantidade = 5 },
  { item = "Leonard", quantidade = 20 },
]
"""


class TestArquivoOuSecaoAusenteNaoEErro:
    """Sem `[[receita]]` a margem simplesmente NAO APARECE.

    Nao e erro e nao e aviso: e uma secao opcional que o usuario preenche
    quando quiser. Decisao travada no `04-CONTEXT.md`.
    """

    def test_arquivo_ausente_devolve_lista_vazia_sem_levantar(self, tmp_path):
        assert ler_receitas(tmp_path / "nao-existe.toml") == []

    def test_arquivo_sem_nenhum_bloco_de_receita_devolve_lista_vazia(
        self, tmp_path
    ):
        caminho = _escrever(tmp_path, '[jogo]\npersonagem = "Yazalaque"\n')
        assert ler_receitas(caminho) == []

    def test_a_leitura_NAO_CRIA_o_arquivo_ausente(self, tmp_path):
        caminho = tmp_path / "nao-existe.toml"
        ler_receitas(caminho)
        assert not caminho.exists()


class TestTomlQuebradoRecusaOArranque:
    def test_toml_quebrado_levanta_com_o_NOME_DO_ARQUIVO(self, tmp_path):
        caminho = _escrever(tmp_path, "[[receita]\nproduto = ")
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        assert caminho.name in str(erro.value)


class TestOBlocoQueNaoEBloco:
    def test_receita_que_nao_e_lista_de_tabelas_levanta(self, tmp_path):
        caminho = _escrever(tmp_path, 'receita = "Dragon Belt"\n')
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        # Um texto solto ITERARIA OS CARACTERES: `D`, `r`, `a`, `g`... viraria
        # uma receita por letra. A recusa tem de dizer o que se esperava.
        assert "receita" in str(erro.value).lower()

    def test_bloco_que_nao_e_tabela_NOMEIA_A_POSICAO(self, tmp_path):
        caminho = _escrever(tmp_path, 'receita = [ "Dragon Belt" ]\n')
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        assert "#1" in str(erro.value)


class TestOProdutoEObrigatorio:
    def test_produto_ausente_levanta_CITANDO_A_POSICAO_DO_BLOCO(self, tmp_path):
        caminho = _escrever(
            tmp_path,
            "[[receita]]\nrende = 1\n"
            'componentes = [ { item = "Leonard", quantidade = 2 } ]\n',
        )
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        # Sem nome utilizavel a mensagem cita a POSICAO — "o segundo bloco esta
        # errado" faria o usuario contar blocos.
        assert "#1" in str(erro.value)

    def test_produto_vazio_levanta_e_a_mensagem_MOSTRA_O_FORMATO(self, tmp_path):
        caminho = _escrever(
            tmp_path,
            '[[receita]]\nproduto = "   "\nrende = 1\n'
            'componentes = [ { item = "Leonard", quantidade = 2 } ]\n',
        )
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        texto = str(erro.value)
        assert "produto" in texto
        # A mensagem MOSTRA a linha pronta em vez de so descreve-la.
        assert "[[receita]]" in texto


class TestORendeEObrigatorioENuncaBooleano:
    def test_rende_ausente_levanta_e_NAO_vira_um(self, tmp_path):
        caminho = _escrever(
            tmp_path,
            '[[receita]]\nproduto = "Dragon Belt"\n'
            'componentes = [ { item = "Leonard", quantidade = 2 } ]\n',
        )
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        assert "rende" in str(erro.value)
        assert "Dragon Belt" in str(erro.value)

    def test_rende_true_LEVANTA_e_o_valor_NAO_virou_um(self, tmp_path):
        caminho = _escrever(
            tmp_path,
            '[[receita]]\nproduto = "Dragon Belt"\nrende = true\n'
            'componentes = [ { item = "Leonard", quantidade = 2 } ]\n',
        )
        with pytest.raises(ReceitaInvalida):
            ler_receitas(caminho)

        # A METADE QUE IMPORTA: a prova de que a guarda `isinstance(bool)` esta
        # ANTES do teste numerico. Sem ela `True` passaria por `int` e por
        # `> 0` e viraria `1` — uma receita que rende 1 quando o usuario
        # escreveu um disparate, com a mesma cara de uma certa.
        #
        # O CONTROLE NEGATIVO E MECANICO: aqui roda a alternativa ERRADA (o
        # teste numerico sem a guarda) e afirma-se que ela ERRA. Um teste que
        # so afirmasse `raises` nao distinguiria "recusou por ser booleano" de
        # "recusou por outro motivo qualquer".
        import tomllib

        with caminho.open("rb") as arquivo:
            bruto = tomllib.load(arquivo)["receita"][0]
        sem_a_guarda = bruto["rende"]
        assert isinstance(sem_a_guarda, int)  # `True` E `int` em Python
        assert sem_a_guarda > 0  # e passa no teste de positivo
        assert int(sem_a_guarda) == 1  # e viraria `1` em silencio

    @pytest.mark.parametrize("valor", ["0", "-2"])
    def test_rende_nao_positivo_levanta(self, tmp_path, valor):
        caminho = _escrever(
            tmp_path,
            f'[[receita]]\nproduto = "Dragon Belt"\nrende = {valor}\n'
            'componentes = [ { item = "Leonard", quantidade = 2 } ]\n',
        )
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        assert "rende" in str(erro.value)


class TestOsComponentes:
    def test_componentes_que_nao_e_lista_levanta(self, tmp_path):
        caminho = _escrever(
            tmp_path,
            '[[receita]]\nproduto = "Dragon Belt"\nrende = 1\n'
            'componentes = "Leonard"\n',
        )
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        assert "componentes" in str(erro.value)

    def test_componentes_ausente_levanta(self, tmp_path):
        caminho = _escrever(
            tmp_path, '[[receita]]\nproduto = "Dragon Belt"\nrende = 1\n'
        )
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        assert "componentes" in str(erro.value)

    def test_componentes_vazio_levanta(self, tmp_path):
        caminho = _escrever(
            tmp_path,
            '[[receita]]\nproduto = "Dragon Belt"\nrende = 1\n'
            "componentes = []\n",
        )
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        assert "componentes" in str(erro.value)

    def test_componente_sem_item_levanta_NOMEANDO_A_RECEITA(self, tmp_path):
        caminho = _escrever(
            tmp_path,
            '[[receita]]\nproduto = "Dragon Belt"\nrende = 1\n'
            "componentes = [ { quantidade = 5 } ]\n",
        )
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        assert "Dragon Belt" in str(erro.value)

    def test_quantidade_true_LEVANTA_e_o_valor_NAO_virou_um(self, tmp_path):
        caminho = _escrever(
            tmp_path,
            '[[receita]]\nproduto = "Dragon Belt"\nrende = 1\n'
            'componentes = [ { item = "Leonard", quantidade = true } ]\n',
        )
        with pytest.raises(ReceitaInvalida):
            ler_receitas(caminho)

        import tomllib

        with caminho.open("rb") as arquivo:
            bruto = tomllib.load(arquivo)["receita"][0]["componentes"][0]
        sem_a_guarda = bruto["quantidade"]
        assert isinstance(sem_a_guarda, int)
        assert int(sem_a_guarda) == 1

    def test_quantidade_ausente_levanta(self, tmp_path):
        caminho = _escrever(
            tmp_path,
            '[[receita]]\nproduto = "Dragon Belt"\nrende = 1\n'
            'componentes = [ { item = "Leonard" } ]\n',
        )
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        assert "quantidade" in str(erro.value)

    def test_componente_que_nao_e_tabela_levanta_NOMEANDO_A_RECEITA(
        self, tmp_path
    ):
        caminho = _escrever(
            tmp_path,
            '[[receita]]\nproduto = "Dragon Belt"\nrende = 1\n'
            'componentes = [ "Leonard" ]\n',
        )
        with pytest.raises(ReceitaInvalida) as erro:
            ler_receitas(caminho)
        assert "Dragon Belt" in str(erro.value)


class TestAReceitaValidaParseia:
    def test_dois_componentes_em_tabela_inline_voltam_INTEIROS(self, tmp_path):
        caminho = _escrever(tmp_path, RECEITA_VALIDA)
        receitas = ler_receitas(caminho)

        assert len(receitas) == 1
        receita = receitas[0]
        assert receita.produto == "Dragon Belt"
        assert receita.rende == 1
        assert len(receita.componentes) == 2
        assert receita.componentes[0].item == "Common Aztac"
        assert receita.componentes[0].quantidade == 5
        assert receita.componentes[1].item == "Leonard"
        assert receita.componentes[1].quantidade == 20

    def test_rende_maior_que_um_e_lido_como_escrito(self, tmp_path):
        caminho = _escrever(
            tmp_path,
            '[[receita]]\nproduto = "Leonard"\nrende = 5\n'
            'componentes = [ { item = "Stem", quantidade = 3 } ]\n',
        )
        assert ler_receitas(caminho)[0].rende == 5

    def test_duas_receitas_voltam_na_ORDEM_ESCRITA(self, tmp_path):
        caminho = _escrever(
            tmp_path,
            RECEITA_VALIDA
            + '\n[[receita]]\nproduto = "Leonard"\nrende = 5\n'
            'componentes = [ { item = "Stem", quantidade = 3 } ]\n',
        )
        receitas = ler_receitas(caminho)
        assert [r.produto for r in receitas] == ["Dragon Belt", "Leonard"]


class TestAGuardaDoBooleanoEstaNO_FONTE:
    """O criterio de `grep` do plano, com o discriminante ao lado.

    O criterio como escrito no `04-04-PLAN.md` e
    `assert 'bool' in inspect.getsource(c)` — o modulo INTEIRO. Ele **ja
    passava na arvore pristina**, medido nesta sessao antes de uma linha ser
    escrita, porque `_horas_de_respawn` ja usa `isinstance(valor, bool)` desde
    a Fase 2 de bosses. Um criterio que passa sem o codigo existir nao prova
    nada, entao ele fica ao lado do discriminante — que olha para a funcao
    NOVA.
    """

    def test_a_guarda_esta_na_funcao_que_valida_os_numeros_da_receita(self):
        from l2scanner import config

        fonte = inspect.getsource(config._inteiro_positivo_da_receita)
        assert "isinstance" in fonte
        assert "bool" in fonte
        # O DISCRIMINANTE: a guarda vem ANTES do teste de positivo. Trocar a
        # ordem faria `True` passar, e a ordem e a unica coisa que importa.
        assert fonte.index("bool") < fonte.index("<= 0")
