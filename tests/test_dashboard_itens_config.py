"""O `[[dashboard.item]]` do `config.toml`: o leitor que DERRUBA o arranque.

NADA AQUI TOCA O `config.toml` REAL PARA JULGAR O LEITOR. Todo TOML de recusa
nasce em `tmp_path`, no mesmo molde de `tests/test_mercado_receitas.py` — e o
que permite a suite inteira rodar no Python global, sem WinRT e sem frame. O
arquivo distribuido e lido, sim, mas so em modo leitura e so para afirmar que a
secao entrou COMENTADA.

O QUE ESTES TESTES PRENDEM, EM UMA FRASE
=========================================
Que um preco de NPC torto **derruba o arranque em vez de virar um veredito**.
Um `preco_npc_adena = true` que passasse viraria "1 adena", e a calculadora
elegeria o NPC como vencedor com toda a confianca do mundo — um numero
perfeitamente formatado e completamente falso, que e o unico modo de falha que
esta fase existe para combater.

TODA RECUSA E CONFERIDA PELA MENSAGEM, E NAO SO PELO TIPO DA EXCECAO. Um
`pytest.raises` sozinho ficaria verde com uma mensagem que nao diz qual item nem
qual campo esta errado — e a mensagem E o produto aqui: quem le e um usuario que
nao programa, olhando um console que acabou de fechar.

ESTE ARQUIVO E ASCII, como o resto de `tests/`.
"""

from __future__ import annotations

import logging
import tomllib

import pytest

from l2scanner.config import (
    CHAVE_DOS_ITENS,
    SECAO_DO_DASHBOARD,
    TETO_DA_QUANTIDADE_DO_PACOTE,
    TETO_DO_PRECO_DO_NPC,
    ItemDeRota,
    ItemDeRotaInvalido,
    _inteiro_positivo_do_item,
    ler_itens_de_rota,
)
from l2scanner.raiz import RAIZ

# ---------------------------------------------------------------------------
# O MATERIAL
# ---------------------------------------------------------------------------

BLOCO_VALIDO = (
    "[[dashboard.item]]\n"
    'nome = "Gemstone C"\n'
    "preco_npc_adena = 15000\n"
    "quantidade_do_pacote = 1\n"
)

BLOCO_DA_GEMSTONE_B = (
    "[[dashboard.item]]\n"
    'nome = "Gemstone B"\n'
    "preco_npc_adena = 30000\n"
    "quantidade_do_pacote = 1\n"
)


def _escrever(tmp_path, texto: str, nome: str = "config.toml"):
    caminho = tmp_path / nome
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def _recusa(tmp_path, texto: str) -> str:
    """O texto da recusa de UM arquivo. Falha o teste se ele NAO recusar."""
    caminho = _escrever(tmp_path, texto)
    with pytest.raises(ItemDeRotaInvalido) as erro:
        ler_itens_de_rota(caminho)
    return str(erro.value)


def _bloco(campo: str, valor: str) -> str:
    """Um bloco valido com UM campo trocado pelo texto TOML dado."""
    campos = {
        "nome": '"Gemstone C"',
        "preco_npc_adena": "15000",
        "quantidade_do_pacote": "1",
    }
    campos[campo] = valor
    linhas = "".join(f"{chave} = {texto}\n" for chave, texto in campos.items())
    return "[[dashboard.item]]\n" + linhas


def _bloco_sem(campo: str) -> str:
    campos = {
        "nome": '"Gemstone C"',
        "preco_npc_adena": "15000",
        "quantidade_do_pacote": "1",
    }
    del campos[campo]
    linhas = "".join(f"{chave} = {texto}\n" for chave, texto in campos.items())
    return "[[dashboard.item]]\n" + linhas


CAMPOS_NUMERICOS = ("preco_npc_adena", "quantidade_do_pacote")


# ===========================================================================
# O QUE NAO E ERRO
# ===========================================================================


class TestOSilencioQueNaoEErro:
    """Arquivo ausente e secao ausente sao os dois estados NORMAIS.

    A secao nasce COMENTADA no `config.toml`: o dashboard inteiro da Fase 1
    responde "quanto valem 5 milhoes de adena" sem um unico `[[dashboard.item]]`
    configurado, e tem de continuar respondendo.
    """

    def test_arquivo_ausente_devolve_lista_vazia_sem_levantar(self, tmp_path):
        assert ler_itens_de_rota(tmp_path / "nao-existe.toml") == []

    def test_a_leitura_NAO_CRIA_o_arquivo_ausente(self, tmp_path):
        """O dashboard e somente leitura, e isso vale tambem para o config."""
        caminho = tmp_path / "nao-existe.toml"
        ler_itens_de_rota(caminho)
        assert not caminho.exists()

    def test_secao_ausente_devolve_lista_vazia(self, tmp_path):
        caminho = _escrever(tmp_path, '[jogo]\npersonagem = "Yazalaque"\n')
        assert ler_itens_de_rota(caminho) == []

    def test_secao_presente_SEM_a_chave_dos_itens_devolve_lista_vazia(
        self, tmp_path
    ):
        """`[dashboard]` pode um dia ganhar outras chaves. Sem `item`, nada."""
        caminho = _escrever(tmp_path, "[dashboard]\noutra_coisa = 1\n")
        assert ler_itens_de_rota(caminho) == []


# ===========================================================================
# O ACESSO ANINHADO — o controle que impede um leitor sempre-vazio de passar
# ===========================================================================


class TestOAcessoEANINHADO:
    def test_CONTROLE_o_tomllib_so_entrega_a_lista_por_DOIS_niveis(self):
        """A medicao que desenha `_blocos_de_item`, presa como teste.

        SEM ESTE CONTROLE, UM LEITOR QUEBRADO PASSARIA EM TUDO. Quem copiar
        `_blocos_de_receita` sem ler vai chamar `get(CHAVE_DOS_ITENS)` no nivel
        de cima e receber `None` para sempre — e um leitor que devolve lista
        vazia SEMPRE fica verde em todos os testes de "secao ausente" acima.
        """
        dados = tomllib.loads(BLOCO_VALIDO)

        assert dados.get(CHAVE_DOS_ITENS) is None
        assert isinstance(dados.get(SECAO_DO_DASHBOARD), dict)
        assert isinstance(dados[SECAO_DO_DASHBOARD][CHAVE_DOS_ITENS], list)

    def test_um_bloco_valido_vira_um_ItemDeRota(self, tmp_path):
        caminho = _escrever(tmp_path, BLOCO_VALIDO)
        assert ler_itens_de_rota(caminho) == [
            ItemDeRota(
                nome="Gemstone C", preco_npc_adena=15000, quantidade_do_pacote=1
            )
        ]

    def test_a_ordem_devolvida_e_a_ordem_ESCRITA_no_arquivo(self, tmp_path):
        """Devolver embaralhado esconderia de quem depura o que o arquivo diz."""
        caminho = _escrever(tmp_path, BLOCO_VALIDO + "\n" + BLOCO_DA_GEMSTONE_B)
        assert [item.nome for item in ler_itens_de_rota(caminho)] == [
            "Gemstone C",
            "Gemstone B",
        ]


# ===========================================================================
# AS FORMAS TORTAS DA SECAO
# ===========================================================================


class TestAsFormasTortasDaSecao:
    def test_toml_quebrado_levanta_com_o_NOME_DO_ARQUIVO(self, tmp_path):
        """Com dois arquivos em jogo, "o TOML esta quebrado" sem dizer qual e um
        convite a editar o errado."""
        mensagem = _recusa(tmp_path, "[[dashboard.item]\nnome = ")
        assert "config.toml" in mensagem

    def test_a_secao_que_nao_e_TABELA_levanta_em_vez_de_estourar(self, tmp_path):
        """`dashboard = "ligado"` nao pode virar um estouro de atributo la
        dentro."""
        mensagem = _recusa(tmp_path, 'dashboard = "ligado"\n')
        assert SECAO_DO_DASHBOARD in mensagem
        assert "str" in mensagem

    def test_a_chave_dos_itens_que_nao_e_LISTA_levanta(self, tmp_path):
        """MEDIDO: `item = "solto"` devolve a string, e ela ITERARIA por letra.

        Sem esta guarda nasceriam cinco "itens" chamados `s`, `o`, `l`, `t`,
        `o` — silenciosamente absurdo em vez de ruidosamente errado.
        """
        mensagem = _recusa(tmp_path, '[dashboard]\nitem = "solto"\n')
        assert CHAVE_DOS_ITENS in mensagem
        assert "str" in mensagem

    def test_um_bloco_que_nao_e_TABELA_nomeia_a_POSICAO(self, tmp_path):
        mensagem = _recusa(tmp_path, '[dashboard]\nitem = [ "Gemstone C" ]\n')
        assert "#1" in mensagem


# ===========================================================================
# O NOME
# ===========================================================================


class TestONome:
    def test_nome_ausente_levanta_CITANDO_A_POSICAO_DO_BLOCO(self, tmp_path):
        """Sem nome nao ha como citar o item — entao cita-se a posicao."""
        mensagem = _recusa(
            tmp_path,
            "[[dashboard.item]]\n"
            "preco_npc_adena = 15000\n"
            "quantidade_do_pacote = 1\n",
        )
        assert "#1" in mensagem
        assert "nome" in mensagem

    def test_nome_VAZIO_levanta_e_a_mensagem_MOSTRA_O_FORMATO(self, tmp_path):
        mensagem = _recusa(
            tmp_path,
            "[[dashboard.item]]\n"
            'nome = "   "\n'
            "preco_npc_adena = 15000\n"
            "quantidade_do_pacote = 1\n",
        )
        assert "nome" in mensagem
        assert "[[dashboard.item]]" in mensagem


# ===========================================================================
# OS DOIS NUMEROS — cada recusa NOMEIA o item E o campo
# ===========================================================================


class TestOsDoisNumeros:
    @pytest.mark.parametrize("campo", CAMPOS_NUMERICOS)
    def test_ausente_levanta_nomeando_o_ITEM_e_o_CAMPO(self, tmp_path, campo):
        mensagem = _recusa(tmp_path, _bloco_sem(campo))
        assert "Gemstone C" in mensagem
        assert campo in mensagem

    @pytest.mark.parametrize("campo", CAMPOS_NUMERICOS)
    def test_BOOLEANO_levanta_nomeando_o_ITEM_e_o_CAMPO(self, tmp_path, campo):
        """`preco_npc_adena = true` viraria "1 adena" sem esta guarda."""
        mensagem = _recusa(tmp_path, _bloco(campo, "true"))
        assert "Gemstone C" in mensagem
        assert campo in mensagem

    @pytest.mark.parametrize("campo", CAMPOS_NUMERICOS)
    def test_FRACIONARIO_levanta_inclusive_o_redondo(self, tmp_path, campo):
        """`1.0` cai junto com `1.5`: aceitar o redondo e recusar o quebrado
        seria uma regra que o usuario descobre por tentativa."""
        assert "Gemstone C" in _recusa(tmp_path, _bloco(campo, "1.5"))
        assert "Gemstone C" in _recusa(tmp_path, _bloco(campo, "1.0"))

    @pytest.mark.parametrize("campo", CAMPOS_NUMERICOS)
    def test_ZERO_e_NEGATIVO_levantam(self, tmp_path, campo):
        for valor in ("0", "-1"):
            mensagem = _recusa(tmp_path, _bloco(campo, valor))
            assert "Gemstone C" in mensagem
            assert campo in mensagem

    def test_o_preco_ACIMA_DO_TETO_levanta_nomeando_o_teto(self, tmp_path):
        mensagem = _recusa(
            tmp_path, _bloco("preco_npc_adena", str(TETO_DO_PRECO_DO_NPC + 1))
        )
        assert "Gemstone C" in mensagem
        assert "preco_npc_adena" in mensagem
        assert str(TETO_DO_PRECO_DO_NPC) in mensagem

    def test_a_quantidade_ACIMA_DO_TETO_levanta_nomeando_o_teto(self, tmp_path):
        mensagem = _recusa(
            tmp_path,
            _bloco("quantidade_do_pacote", str(TETO_DA_QUANTIDADE_DO_PACOTE + 1)),
        )
        assert "Gemstone C" in mensagem
        assert "quantidade_do_pacote" in mensagem
        assert str(TETO_DA_QUANTIDADE_DO_PACOTE) in mensagem

    def test_EXATAMENTE_no_teto_PASSA(self, tmp_path):
        """O teto e INCLUSIVO, e isso e uma decisao a prender.

        Um `>=` faria o maior valor legitimo ser recusado, e a mensagem nao teria
        como explicar por que o numero que ela mesma cita como teto nao serve.
        """
        caminho = _escrever(
            tmp_path, _bloco("preco_npc_adena", str(TETO_DO_PRECO_DO_NPC))
        )
        assert (
            ler_itens_de_rota(caminho)[0].preco_npc_adena == TETO_DO_PRECO_DO_NPC
        )


class TestAOrdemDaGuardaDeBooleano:
    """A guarda de booleano vem ANTES do teste de inteiro, e o controle MEDE
    por que."""

    def test_o_booleano_e_recusado(self, tmp_path):
        assert "preco_npc_adena" in _recusa(
            tmp_path, _bloco("preco_npc_adena", "true")
        )

    def test_CONTROLE_sem_a_ordem_o_true_passaria_valendo_UM(self):
        """A razao da ordem, MEDIDA em vez de afirmada.

        Em Python `True` E um `int` de valor 1. Se a guarda de booleano viesse
        DEPOIS do `isinstance(valor, int)`, o `preco_npc_adena = true` passaria
        pelo teste de tipo, passaria pelo teste de positivo, e chegaria na
        calculadora como "1 adena por unidade" — o NPC venceria toda comparacao
        que existe, com um numero perfeitamente formatado.

        Este teste nao afirma que a ordem esta certa; ele afirma o FATO DA
        LINGUAGEM que torna a ordem necessaria. Quem inverter a ordem quebra o
        teste acima; quem ler este entende por que.
        """
        assert isinstance(True, int)
        assert int(True) == 1
        assert True > 0

    def test_o_helper_do_inteiro_ACEITA_um_inteiro_de_verdade(self):
        """O controle do lado positivo: a guarda recusa `True` e nao recusa 5."""
        assert (
            _inteiro_positivo_do_item(
                {"preco_npc_adena": 5},
                "preco_npc_adena",
                "config.toml: item 'Gemstone C'",
                TETO_DO_PRECO_DO_NPC,
            )
            == 5
        )

    def test_o_helper_do_inteiro_RECUSA_o_booleano(self):
        with pytest.raises(ItemDeRotaInvalido):
            _inteiro_positivo_do_item(
                {"preco_npc_adena": True},
                "preco_npc_adena",
                "config.toml: item 'Gemstone C'",
                TETO_DO_PRECO_DO_NPC,
            )


# ===========================================================================
# O NOME REPETIDO
# ===========================================================================


class TestONomeRepetido:
    def test_dois_blocos_com_o_mesmo_nome_sao_RECUSADOS_listando_os_dois(
        self, tmp_path
    ):
        """Duas entradas do mesmo item dariam duas linhas na tela com dois
        vereditos e nenhuma forma de saber qual vale."""
        mensagem = _recusa(tmp_path, BLOCO_VALIDO + "\n" + BLOCO_VALIDO)
        assert mensagem.count("Gemstone C") >= 2

    def test_a_comparacao_IGNORA_caixa_e_espaco_duplo(self, tmp_path):
        """Pelo mesmo criterio do casamento com a serie: caixa e espaco nao
        podem fazer duas entradas parecerem distintas."""
        mensagem = _recusa(
            tmp_path,
            BLOCO_VALIDO
            + "\n[[dashboard.item]]\n"
            'nome = "gemstone  c"\n'
            "preco_npc_adena = 99000\n"
            "quantidade_do_pacote = 1\n",
        )
        assert "Gemstone C" in mensagem
        assert "gemstone  c" in mensagem

    def test_nomes_REALMENTE_diferentes_passam(self, tmp_path):
        """O controle: a recusa de repetido nao pode pegar Gemstone B e C."""
        caminho = _escrever(tmp_path, BLOCO_VALIDO + "\n" + BLOCO_DA_GEMSTONE_B)
        assert len(ler_itens_de_rota(caminho)) == 2


# ===========================================================================
# OS DOIS ARQUIVOS
# ===========================================================================


class TestOLocalVence:
    def test_o_local_VENCE_e_o_aviso_NOMEIA_o_vencedor(self, tmp_path, caplog):
        versionado = _escrever(tmp_path, BLOCO_VALIDO)
        local = _escrever(tmp_path, BLOCO_DA_GEMSTONE_B, nome="config.local.toml")

        with caplog.at_level(logging.WARNING):
            itens = ler_itens_de_rota(versionado, local)

        assert [item.nome for item in itens] == ["Gemstone B"]
        assert "config.local.toml" in caplog.text

    def test_o_bloco_TORTO_do_PERDEDOR_nao_derruba_nada(self, tmp_path):
        """Validar o perdedor derrubaria o arranque por causa de um bloco que ja
        nao tem efeito nenhum — o defeito que o analogo da receita documenta."""
        versionado = _escrever(
            tmp_path,
            "[[dashboard.item]]\n"
            'nome = "Gemstone C"\n'
            "preco_npc_adena = true\n"
            "quantidade_do_pacote = 1\n",
        )
        local = _escrever(tmp_path, BLOCO_DA_GEMSTONE_B, nome="config.local.toml")

        assert [item.nome for item in ler_itens_de_rota(versionado, local)] == [
            "Gemstone B"
        ]

    def test_um_caminho_EXPLICITO_le_so_aquele_arquivo(self, tmp_path):
        """Sem vizinho: `ler_itens_de_rota(x)` nunca procura um `config.local`
        ao lado, porque a suite inteira depende disso para nao ler o arquivo do
        usuario."""
        _escrever(tmp_path, BLOCO_DA_GEMSTONE_B, nome="config.local.toml")
        caminho = _escrever(tmp_path, BLOCO_VALIDO)
        assert [item.nome for item in ler_itens_de_rota(caminho)] == ["Gemstone C"]


# ===========================================================================
# O ARQUIVO DO USUARIO
# ===========================================================================


class TestOConfigDeDistribuicaoEntraCOMENTADO:
    def test_nenhuma_linha_VIVA_do_config_toml_declara_a_secao(self):
        """A contagem IGNORA comentario justamente porque o bloco E comentario.

        Um bloco vivo no arquivo distribuido seria um preco de NPC que ninguem
        conferiu virando veredito de dinheiro na primeira abertura do dashboard.
        """
        texto = (RAIZ / "config.toml").read_text(encoding="utf-8")
        vivas = [
            linha
            for linha in texto.splitlines()
            if not linha.lstrip().startswith("#") and "dashboard.item" in linha
        ]
        assert vivas == []

    def test_o_config_toml_ENSINA_a_secao_em_comentario(self):
        """O controle da assercao acima: ela ficaria verde num arquivo que nao
        menciona a secao em lugar nenhum — genericidade provada pelo motivo
        errado."""
        texto = (RAIZ / "config.toml").read_text(encoding="utf-8")
        assert "# [[dashboard.item]]" in texto
        assert "# nome = " in texto
        assert "# preco_npc_adena = " in texto
        assert "# quantidade_do_pacote = " in texto

    def test_as_duas_primeiras_instancias_estao_no_arquivo(self):
        texto = (RAIZ / "config.toml").read_text(encoding="utf-8")
        assert "Gemstone C" in texto
        assert "Gemstone B" in texto

    def test_o_arquivo_MANDA_conferir_o_preco_no_NPC(self):
        """Os precos entram como EXEMPLO, e o arquivo diz isso.

        Ninguem nesta arvore sabe quanto o NPC cobra. Escrever um numero
        plausivel no arquivo que o usuario vai usar seria fabricar um numero de
        dinheiro — o oposto do que esta fase existe para fazer.
        """
        texto = (RAIZ / "config.toml").read_text(encoding="utf-8").lower()
        assert "exemplo" in texto
        assert "confira" in texto or "conferir" in texto

    def test_o_arquivo_do_usuario_continua_SEM_ACENTO(self):
        """Todo texto que este projeto poe na frente do usuario em terminal e
        ASCII: o `cmd` do Windows abre em cp1252."""
        texto = (RAIZ / "config.toml").read_text(encoding="utf-8")
        assert texto.isascii()


class TestAsMensagensSaoASCII:
    def test_toda_recusa_desta_secao_e_ASCII(self, tmp_path):
        """Elas saem no console do `.bat`, e nao na pagina."""
        assert _recusa(tmp_path, _bloco("preco_npc_adena", "true")).isascii()
        assert _recusa(tmp_path, '[dashboard]\nitem = "solto"\n').isascii()
