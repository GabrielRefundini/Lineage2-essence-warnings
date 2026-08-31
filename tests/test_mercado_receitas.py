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


# ===========================================================================
# TASK 2 — `margem_de_craft`: quebra em vez de adivinhar
# ===========================================================================


def observacao(
    chave: str,
    total: int,
    quantidade: int,
    *,
    nome: str | None = None,
    quando: datetime | None = None,
) -> ObservacaoLida:
    """Uma linha do CSV ja tipada, sem tocar disco."""
    return ObservacaoLida(
        chave_da_serie=chave,
        nome_exibido=nome if nome is not None else chave,
        primeira_vez=quando if quando is not None else AGORA,
        total_em_centesimos=total,
        quantidade=quantidade,
        residuo_do_cruzamento=None,
    )


def receita(
    produto: str = "Dragon Belt",
    rende: int = 1,
    componentes=(("Common Aztac", 5), ("Leonard", 20)),
) -> Receita:
    return Receita(
        produto=produto,
        rende=rende,
        componentes=tuple(
            ComponenteDaReceita(item=item, quantidade=quantidade)
            for item, quantidade in componentes
        ),
    )


# O MUNDO PADRAO DOS TESTES DA MARGEM, com os tres precos escolhidos para que a
# conta caia numa `Fraction` que NAO e inteira — se ela caisse redonda, um
# `float` passaria pelo teste e a prova de exatidao nao provaria nada.
#
#   produto      Dragon Belt    1.480,00 por 1   -> unitario 148000
#   componente   Common Aztac      62,00 por 48  -> unitario 6200/48 = 775/6
#   componente   Leonard            4,50 por 100 -> unitario 450/100 = 9/2
#
#   margem = 148000*1 - (775/6*5 + 9/2*20) = 148000 - 4415/6 = 883585/6
MARGEM_ESPERADA = Fraction(883585, 6)


def mundo(
    *,
    idade_do_produto=timedelta(minutes=22),
    idade_do_aztac=timedelta(minutes=8),
    idade_do_leonard=timedelta(hours=3),
):
    return analise.ModeloDeMercado.de_observacoes(
        [
            observacao(
                "dragon-belt#0",
                148000,
                1,
                nome="Dragon Belt",
                quando=AGORA - idade_do_produto,
            ),
            observacao(
                "common-aztac#0",
                6200,
                48,
                nome="Common Aztac",
                quando=AGORA - idade_do_aztac,
            ),
            observacao(
                "leonard#0",
                450,
                100,
                nome="Leonard",
                quando=AGORA - idade_do_leonard,
            ),
        ]
    )


class TestAContaSaiEXATA:
    def test_a_margem_e_o_valor_esperado(self):
        resultado = analise.margem_de_craft(receita(), mundo(), AGORA)
        assert resultado.estado == analise.MARGEM_CALCULADA
        assert resultado.margem_em_centesimos == MARGEM_ESPERADA

    def test_o_tipo_intermediario_e_Fraction_e_NUNCA_float(self):
        resultado = analise.margem_de_craft(receita(), mundo(), AGORA)
        assert isinstance(resultado.margem_em_centesimos, Fraction)
        assert not isinstance(resultado.margem_em_centesimos, float)
        for linha in resultado.linhas:
            assert isinstance(linha.subtotal, Fraction)

        # O DISCRIMINANTE: a conta em `float` DIVERGE da exata. Sem esta linha
        # o teste acima seria satisfeito por qualquer implementacao que por
        # acaso devolvesse um `Fraction` construido de um `float`.
        em_float = 148000.0 - (6200 / 48 * 5 + 450 / 100 * 20)
        assert Fraction(em_float) != MARGEM_ESPERADA

    def test_o_rende_MULTIPLICA_o_lado_do_produto(self):
        # Rende 5 e a razao de `rende` ser obrigatorio: com padrao silencioso
        # de 1 esta margem sairia quatro produtos menor.
        resultado = analise.margem_de_craft(
            receita(rende=5), mundo(), AGORA
        )
        assert resultado.margem_em_centesimos == 148000 * 5 - Fraction(4415, 6)

    def test_a_quantidade_do_componente_MULTIPLICA_o_custo(self):
        resultado = analise.margem_de_craft(
            receita(componentes=(("Common Aztac", 1), ("Leonard", 1))),
            mundo(),
            AGORA,
        )
        assert resultado.margem_em_centesimos == 148000 - (
            Fraction(775, 6) + Fraction(9, 2)
        )


class TestOIngredienteSemObservacaoQUEBRA_A_MARGEM_INTEIRA:
    """Calcular com um buraco daria numero plausivel e errado."""

    def test_o_estado_e_quebrado_e_o_NOME_do_que_faltou_aparece(self):
        resultado = analise.margem_de_craft(
            receita(componentes=(("Common Aztac", 5), ("Adamantine", 2))),
            mundo(),
            AGORA,
        )
        assert resultado.estado == analise.MARGEM_SEM_SERIE
        assert not resultado.ok
        assert "Adamantine" in resultado.motivo

    def test_NENHUM_numero_de_margem_sai_quando_ela_quebra(self):
        resultado = analise.margem_de_craft(
            receita(componentes=(("Adamantine", 2),)), mundo(), AGORA
        )
        assert resultado.margem_em_centesimos is None
        assert resultado.margem_pela_mediana is None

    def test_o_PRODUTO_sem_observacao_quebra_pelo_mesmo_caminho(self):
        resultado = analise.margem_de_craft(
            receita(produto="Blessed Scroll"), mundo(), AGORA
        )
        assert resultado.estado == analise.MARGEM_SEM_SERIE
        assert "Blessed Scroll" in resultado.motivo

    def test_a_mensagem_SUGERE_os_nomes_disponiveis_para_o_usuario_copiar(self):
        resultado = analise.margem_de_craft(
            receita(componentes=(("Leonarde", 2),)), mundo(), AGORA
        )
        # Ajuda sem decidir: o nome parecido e OFERECIDO, nunca ADOTADO.
        assert "Leonard" in resultado.motivo
        assert resultado.margem_em_centesimos is None


class TestONomeAmbiguoQUEBRA_LISTANDO_AS_CANDIDATAS:
    """Escolher a mais parecida produziria uma margem plausivel e errada."""

    def _modelo_com_duas_series_do_mesmo_nome(self):
        return analise.ModeloDeMercado.de_observacoes(
            [
                observacao(
                    "dragon-belt#0", 148000, 1, nome="Dragon Belt"
                ),
                observacao("leonard#0", 450, 100, nome="Leonard"),
                # A MESMA GRAFIA, DUAS CHAVES. E o caso real da fusao aberta
                # desde a Fase 2 e o do `nome_exibido` que oscila no OCR.
                observacao("leonard#1", 900, 100, nome="  leonard  "),
            ]
        )

    def test_o_estado_e_ambiguo(self):
        resultado = analise.margem_de_craft(
            receita(componentes=(("Leonard", 20),)),
            self._modelo_com_duas_series_do_mesmo_nome(),
            AGORA,
        )
        assert resultado.estado == analise.MARGEM_AMBIGUA
        assert resultado.margem_em_centesimos is None

    def test_AS_DUAS_chaves_candidatas_aparecem_LISTADAS(self):
        resultado = analise.margem_de_craft(
            receita(componentes=(("Leonard", 20),)),
            self._modelo_com_duas_series_do_mesmo_nome(),
            AGORA,
        )
        assert "leonard#0" in resultado.motivo
        assert "leonard#1" in resultado.motivo


class TestOCasamentoEEXATO_COM_CAIXA_NORMALIZADA:
    def test_caixa_diferente_e_espacos_duplicados_CASAM(self):
        resultado = analise.margem_de_craft(
            receita(componentes=(("  cOmMoN   aztac ", 5), ("LEONARD", 20))),
            mundo(),
            AGORA,
        )
        assert resultado.estado == analise.MARGEM_CALCULADA
        assert resultado.margem_em_centesimos == MARGEM_ESPERADA

    def test_prefixo_de_encanto_NAO_CASA_com_o_item_base(self):
        # `+3 Dragon Belt` e `Dragon Belt` sao series DELIBERADAMENTE
        # separadas: medido numa unica pagina real, o mesmo nome base valia de
        # 7,02 a 100,00 conforme o encanto. Qualquer similaridade que
        # tolerasse tres caracteres juntaria as duas e destruiria as duas.
        resultado = analise.margem_de_craft(
            receita(produto="+3 Dragon Belt"), mundo(), AGORA
        )
        assert resultado.estado == analise.MARGEM_SEM_SERIE

    def test_o_CORTE_CALIBRADO_DE_SIMILARIDADE_juntaria_series_SEPARADAS(self):
        """O controle negativo do casamento fuzzy, MEDIDO nesta sessao.

        O `mercado_catalogo.similaridade` e calibrado
        (`mercado_corte_de_similaridade = 0.8947`) e existe para agrupar duas
        leituras de OCR DO MESMO PIXEL. Este teste roda a alternativa ERRADA e
        afirma que ela erra.

        OS TRES NUMEROS SAO MEDIDOS, e nao estimados:

        - `+3 Dragon Belt` x `+4 Dragon Belt` -> **0,9286**, acima do corte.
          Sao series DELIBERADAMENTE separadas: numa unica pagina real o mesmo
          nome base valia de 7,02 a 100,00 conforme o encanto.
        - `B-grade Gemstone` x `C-grade Gemstone` -> **0,9375**, acima do
          corte. E exatamente a fusao que continua ABERTA desde a Fase 2.
        - `Leonard` x `Leonarde` -> **0,9333**, acima do corte: um erro de
          digitacao do usuario seria ADOTADO em silencio, e a margem sairia
          sobre a serie errada.

        E o `+3 Dragon Belt` x `Dragon Belt` mede **0,88** — ABAIXO do corte.
        Isso e o que torna o fuzzy pior que inutil aqui: ele nao erra sempre,
        ele erra de forma imprevisivel, entao o usuario nao consegue nem
        aprender a regra.
        """
        from l2scanner.mercado_catalogo import similaridade

        assert similaridade("+3 Dragon Belt", "+4 Dragon Belt") >= 0.8947
        assert similaridade("B-grade Gemstone", "C-grade Gemstone") >= 0.8947
        assert similaridade("Leonard", "Leonarde") >= 0.8947
        assert similaridade("+3 Dragon Belt", "Dragon Belt") < 0.8947


class TestAStalenessEPOR_COMPONENTE:
    def test_cada_linha_carrega_a_PROPRIA_idade(self):
        resultado = analise.margem_de_craft(receita(), mundo(), AGORA)
        idades = {linha.item: linha.idade for linha in resultado.linhas}
        assert idades["Dragon Belt"] == timedelta(minutes=22)
        assert idades["Common Aztac"] == timedelta(minutes=8)
        assert idades["Leonard"] == timedelta(hours=3)

    def test_a_MAIS_VELHA_sobe_para_o_resultado_COM_O_NOME_JUNTO(self):
        resultado = analise.margem_de_craft(receita(), mundo(), AGORA)
        assert resultado.idade_mais_velha == timedelta(hours=3)
        assert resultado.nome_do_mais_velho == "Leonard"

    def test_a_idade_vem_da_recencia_do_PRECO_e_nao_da_oferta_escolhida(self):
        # Duas ofertas da mesma serie: a mais BARATA e velha, a mais NOVA e
        # cara. A idade da serie e a da oferta mais NOVA (`max(primeira_vez)`),
        # e nao a da que ganhou a disputa do menor pedido visivel.
        modelo = analise.ModeloDeMercado.de_observacoes(
            [
                observacao("dragon-belt#0", 148000, 1, nome="Dragon Belt"),
                observacao(
                    "leonard#0",
                    450,
                    100,
                    nome="Leonard",
                    quando=AGORA - timedelta(days=9),
                ),
                observacao(
                    "leonard#0",
                    900,
                    100,
                    nome="Leonard",
                    quando=AGORA - timedelta(hours=2),
                ),
            ]
        )
        resultado = analise.margem_de_craft(
            receita(componentes=(("Leonard", 20),)), modelo, AGORA
        )
        linha = [x for x in resultado.linhas if x.item == "Leonard"][0]
        assert linha.idade == timedelta(hours=2)
        # E o menor pedido visivel continua sendo o de 4,50 — os dois fatos
        # convivem, e trocar um pelo outro seria a mentira plausivel.
        assert linha.menor.total_em_centesimos == 450

    def test_o_marcador_NAO_aparece_abaixo_do_limiar(self):
        resultado = analise.margem_de_craft(
            receita(), mundo(idade_do_leonard=timedelta(hours=23)), AGORA
        )
        assert not any(linha.velho for linha in resultado.linhas)

    def test_o_marcador_APARECE_acima_do_limiar(self):
        resultado = analise.margem_de_craft(
            receita(), mundo(idade_do_leonard=timedelta(hours=25)), AGORA
        )
        velhos = [linha.item for linha in resultado.linhas if linha.velho]
        assert velhos == ["Leonard"]

    def test_EXATAMENTE_no_limiar_ja_conta_como_velho(self):
        resultado = analise.margem_de_craft(
            receita(),
            mundo(
                idade_do_leonard=timedelta(
                    hours=analise.HORAS_PARA_MARCAR_COMPONENTE_VELHO
                )
            ),
            AGORA,
        )
        assert [x.item for x in resultado.linhas if x.velho] == ["Leonard"]


class TestALinhaSECUNDARIA_DA_MEDIANA:
    def test_sem_o_piso_de_cinco_por_componente_a_mediana_e_None(self):
        resultado = analise.margem_de_craft(receita(), mundo(), AGORA)
        # A conta PRINCIPAL sai (piso do menor e 1); a mediana nao (piso 5).
        assert resultado.margem_em_centesimos is not None
        assert resultado.margem_pela_mediana is None

    def test_com_evidencia_suficiente_a_mediana_sai(self):
        linhas = [
            observacao(
                "dragon-belt#0", 148000 + i, 1, nome="Dragon Belt"
            )
            for i in range(5)
        ]
        linhas += [
            observacao("leonard#0", 450 + i, 100, nome="Leonard")
            for i in range(5)
        ]
        modelo = analise.ModeloDeMercado.de_observacoes(linhas)
        resultado = analise.margem_de_craft(
            receita(componentes=(("Leonard", 20),)), modelo, AGORA
        )
        assert isinstance(resultado.margem_pela_mediana, Fraction)


class TestONomeDoLIMIAR:
    def test_o_limiar_e_vinte_e_quatro_horas(self):
        assert analise.HORAS_PARA_MARCAR_COMPONENTE_VELHO == 24

    def test_a_vizinhanca_do_SITIO_DA_DEFINICAO_diz_que_e_ESCOLHA(self):
        """O criterio do plano, com o discriminante ao lado.

        O criterio como escrito usa `fonte.index(...)` — a PRIMEIRA ocorrencia
        do nome no modulo, que e a entrada do `__all__`, la no topo. A janela
        de 900 caracteres depois dela cai no bloco dos pisos de evidencia, que
        ja dizia "ESCOLHA" desde o plano 04-02. Ou seja: o criterio literal
        passaria mesmo que a constante nascesse muda. Medido nesta sessao.

        Este afirma sobre o SITIO DA DEFINICAO (`rindex`), que e onde a razao
        precisa estar para quem le o codigo.
        """
        fonte = inspect.getsource(analise)
        i = fonte.rindex("HORAS_PARA_MARCAR_COMPONENTE_VELHO = ")
        janela = fonte[i - 1200 : i + 900].lower()
        assert "escolha" in janela
        assert "nao medicao" in janela or "e nao medicao" in janela


class TestANomenclaturaNaoPrometeTRANSACAO:
    """T-04-22: os dois lados da conta sao PEDIDOS visiveis, nao transacoes."""

    def _todos_os_textos(self) -> dict[str, str]:
        return {
            "resultado calculado": str(
                analise.margem_de_craft(receita(), mundo(), AGORA)
            ),
            "resultado sem serie": str(
                analise.margem_de_craft(
                    receita(componentes=(("Adamantine", 2),)), mundo(), AGORA
                )
            ),
            "docstring de margem_de_craft": analise.margem_de_craft.__doc__
            or "",
        }

    def test_nenhuma_expressao_proibida_no_resultado_nem_na_docstring(self):
        for onde, texto in self._todos_os_textos().items():
            baixo = texto.lower()
            for proibida in EXPRESSOES_PROIBIDAS_DA_MARGEM:
                assert proibida.lower() not in baixo, (
                    f"{onde} usou a expressao proibida {proibida!r}. Os dois "
                    f"lados da conta sao menor pedido visivel, ou seja "
                    f"OFERTAS: ninguem comprou por aquele valor, alguem PEDIU "
                    f"aquele valor."
                )

    def test_a_tupla_proibida_tem_EXATAMENTE_os_quatro_itens(self):
        assert EXPRESSOES_PROIBIDAS_DA_MARGEM == (
            "lucro",
            "preco de venda",
            "preço de venda",
            "lucro bruto",
        )

    def test_o_CONTROLE_NEGATIVO_da_rede_proibida(self):
        """A rede pega quando ha o que pegar — senao ela nao e rede.

        Sem esta linha, `EXPRESSOES_PROIBIDAS_DA_MARGEM = ()` faria o teste
        acima passar para sempre sem afirmar nada.
        """
        assert EXPRESSOES_PROIBIDAS_DA_MARGEM
        impostor = "o lucro desta operacao"
        pegos = [
            p for p in EXPRESSOES_PROIBIDAS_DA_MARGEM if p.lower() in impostor
        ]
        assert pegos == ["lucro"]


class TestAS_CINCO_LIMITACOES_ESTAO_ESCRITAS:
    def test_a_razao_de_NAO_usar_fuzzy_esta_no_fonte_da_funcao(self):
        fonte = inspect.getsource(analise.margem_de_craft)
        assert "similaridade" in fonte

    def test_as_cinco_limitacoes_aparecem_na_docstring(self):
        doc = (analise.margem_de_craft.__doc__ or "").lower()
        # (1) a oferta pode ja ter sido comprada
        assert "ainda existe" in doc
        # (2) comissao e chance de falha do craft
        assert "comissao" in doc
        # (3) quantidade minima / lote
        assert "lote" in doc
        # (4) a fusao de series aberta desde a Fase 2
        assert "fusao" in doc
        # (5) o programa nao conhece o crafting do jogo
        assert "o usuario escreveu a receita" in doc
