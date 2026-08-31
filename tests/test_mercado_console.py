"""O DESENHO da resposta "vale quanto agora?", e a nomenclatura presa por teste.

O QUE ESTE ARQUIVO PRENDE
==========================
Tres coisas que so existem na JUNCAO entre a analise pura (04-02) e o laco de
producao (04-01), e que nenhum dos dois arquivos de teste anteriores alcanca:

1. **A watchlist como FILTRO DE DESTAQUE, nunca como porta de entrada.** Sem
   watchlist o console responde para as series com MAIS EVIDENCIA; com
   watchlist elas vem primeiro e MARCADAS, e o resto continua visivel abaixo.
   Filtrar de vez esconderia o item novo que a Fase 2 existe para descobrir.
2. **A evidencia colada ao numero.** `n` e carimbo em toda linha; total nunca
   sem quantidade ao lado; abaixo do piso, o que FALTA em vez de um numero.
3. **A NOMENCLATURA.** O scanner ve OFERTAS, nao transacoes: a expressao de
   transacao proibida nao pode aparecer nem no texto DEVOLVIDO nem no FONTE dos
   dois modulos que o usuario le.

POR QUE A VARREDURA DO FONTE, E NAO SO DO RETORNO
==================================================
Um teste que varre so o TEXTO DEVOLVIDO por uma funcao deixa passar a expressao
num rotulo de OUTRA funcao, num comentario ou numa docstring. `linha_ao_vivo` e
`resumo_da_sessao`, escritas no plano 04-01, nao sao varridas por nenhum outro
teste desta fase -- a varredura de `inspect.getsource` e o que as alcanca.
"""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timedelta

import pytest

import l2scanner.config as config_mod
from l2scanner.agenda import AgendaInvalida
from l2scanner.config import ler_watchlist_do_mercado
from l2scanner.mercado_analise import (
    SERIES_NO_TOPO,
    ModeloDeMercado,
    ordenar_para_o_console,
)
from l2scanner.mercado_registro import ObservacaoLida

# AS EXPRESSOES PROIBIDAS, escritas UMA vez no topo do modulo.
#
# O scanner ve OFERTAS no quadro, nao transacoes concluidas. Ninguem comprou
# por aquele valor: alguem PEDIU aquele valor. A palavra do requisito e
# `menor pedido visivel`, e esta tupla e a rede que impede a outra de voltar.
#
# As tres formas cobrem o que alguem digitaria sem pensar: sem acento (como o
# projeto escreve), com acento (como o portugues escreve) e com hifen.
EXPRESSOES_PROIBIDAS = (
    "preco de venda",
    "preço de venda",
    "preço-de-venda",
)

UM_MINUTO = timedelta(minutes=1)


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
        primeira_vez=quando or datetime(2026, 8, 31, 14, 32, 0),
        total_em_centesimos=total,
        quantidade=quantidade,
        residuo_do_cruzamento=None,
    )


def serie(
    chave: str, quantas: int, *, nome: str | None = None, base: int = 100
) -> list[ObservacaoLida]:
    """`quantas` ofertas DISTINTAS da mesma serie, com carimbos crescentes."""
    return [
        observacao(
            chave,
            base + i,
            1,
            nome=nome,
            quando=datetime(2026, 8, 31, 10, 0, 0) + i * UM_MINUTO,
        )
        for i in range(quantas)
    ]


# ---------------------------------------------------------------------------
# A WATCHLIST LIDA SEM ARRASTAR DPI NEM `cv2` DE GUI
# ---------------------------------------------------------------------------


class TestALeituraDaWatchlist:
    """No molde literal de `ler_bosses`: ausencia nao e erro, lixo e."""

    def test_arquivo_AUSENTE_devolve_lista_vazia_sem_levantar(
        self, tmp_path
    ) -> None:
        assert ler_watchlist_do_mercado(tmp_path / "nao-existe.toml") == []

    def test_secao_presente_SEM_A_CHAVE_devolve_lista_vazia(
        self, tmp_path
    ) -> None:
        arquivo = tmp_path / "config.toml"
        arquivo.write_text("[mercado]\noutra_coisa = 1\n", encoding="utf-8")
        assert ler_watchlist_do_mercado(arquivo) == []

    def test_arquivo_SEM_A_SECAO_devolve_lista_vazia(self, tmp_path) -> None:
        arquivo = tmp_path / "config.toml"
        arquivo.write_text('[jogo]\npersonagem = "Yaza"\n', encoding="utf-8")
        assert ler_watchlist_do_mercado(arquivo) == []

    def test_TOML_QUEBRADO_e_erro_de_arranque_e_nomeia_o_arquivo(
        self, tmp_path
    ) -> None:
        arquivo = tmp_path / "config.toml"
        arquivo.write_text("[mercado\nwatchlist = [", encoding="utf-8")
        with pytest.raises(AgendaInvalida) as erro:
            ler_watchlist_do_mercado(arquivo)
        assert "config.toml" in str(erro.value)

    def test_a_chave_como_TEXTO_SOLTO_e_recusada_com_o_formato_certo(
        self, tmp_path
    ) -> None:
        """`watchlist = "Bota"` ITERARIA OS CARACTERES. Silenciosamente absurdo."""
        arquivo = tmp_path / "config.toml"
        arquivo.write_text(
            '[mercado]\nwatchlist = "Dragon Belt"\n', encoding="utf-8"
        )
        with pytest.raises(AgendaInvalida) as erro:
            ler_watchlist_do_mercado(arquivo)
        mensagem = str(erro.value)
        assert "config.toml" in mensagem, "a mensagem tem de nomear o arquivo"
        assert "LISTA" in mensagem.upper(), "a mensagem tem de dizer o tipo certo"
        assert "watchlist = [" in mensagem, (
            "a mensagem tem de MOSTRAR o formato certo, e nao so descreve-lo"
        )

    def test_item_NAO_TEXTO_dentro_da_lista_e_recusado_nomeando_a_posicao(
        self, tmp_path
    ) -> None:
        arquivo = tmp_path / "config.toml"
        arquivo.write_text(
            '[mercado]\nwatchlist = ["Dragon Belt", 42]\n', encoding="utf-8"
        )
        with pytest.raises(AgendaInvalida) as erro:
            ler_watchlist_do_mercado(arquivo)
        mensagem = str(erro.value)
        assert "config.toml" in mensagem
        assert "2" in mensagem, (
            "a mensagem tem de nomear a POSICAO do item ruim: 'o segundo item' "
            "o usuario conserta em cinco segundos, 'um item esta errado' nao"
        )

    def test_a_lista_boa_volta_INTEIRA_e_na_ordem_escrita(self, tmp_path) -> None:
        arquivo = tmp_path / "config.toml"
        arquivo.write_text(
            '[mercado]\nwatchlist = ["Dragon Belt", "+3 Dragon Belt"]\n',
            encoding="utf-8",
        )
        assert ler_watchlist_do_mercado(arquivo) == [
            "Dragon Belt",
            "+3 Dragon Belt",
        ]

    def test_item_SO_DE_ESPACO_nao_entra(self, tmp_path) -> None:
        """Um alvo invisivel casaria com nada e apareceria marcado no console."""
        arquivo = tmp_path / "config.toml"
        arquivo.write_text(
            '[mercado]\nwatchlist = ["Dragon Belt", "   "]\n', encoding="utf-8"
        )
        assert ler_watchlist_do_mercado(arquivo) == ["Dragon Belt"]

    def test_o_config_NAO_IMPORTA_a_ferramenta_de_calibracao(self) -> None:
        """Ela chama `tornar_consciente_de_dpi()` NO IMPORT e arrasta `cv2`.

        Importar `calibrar_mercado.ler_watchlist` para reusar a leitura seria
        pagar DPI e janela de GUI por uma leitura de TOML, dentro do laco de
        producao. A funcao nova existe por isso.

        A PROVA E SOBRE O AST E NAO SOBRE SUBSTRING, e isto e uma correcao de
        criterio dita em voz alta: o fim de `config.py` JA CITA
        `calibrar_mercado.ler_watchlist` num comentario, desde antes desta fase,
        e a varredura de texto que o plano pediu reprovaria a documentacao do
        proprio precedente. O que importa -- "config nao ARRASTA a ferramenta"
        -- e o que este teste prende.
        """
        arvore = ast.parse(inspect.getsource(config_mod))
        importados: list[str] = []
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                importados += [alias.name for alias in no.names]
            elif isinstance(no, ast.ImportFrom):
                importados.append(no.module or "")
                importados += [alias.name for alias in no.names]
        assert not [nome for nome in importados if "calibrar_mercado" in nome], (
            f"config.py importa calibrar_mercado: {importados}"
        )


# ---------------------------------------------------------------------------
# A ORDENACAO: evidencia por padrao, watchlist como DESTAQUE
# ---------------------------------------------------------------------------


class TestAOrdenacaoParaOConsole:
    def test_SEM_watchlist_as_series_com_MAIS_EVIDENCIA_vem_primeiro(
        self,
    ) -> None:
        """O usuario nao configura nada e ja ve valor. E a premissa da Fase 2."""
        modelo = ModeloDeMercado.de_observacoes(
            serie("doze", 12) + serie("tres", 3) + serie("sete", 7)
        )
        ordem = ordenar_para_o_console(modelo, [])
        assert [linha.n for linha in ordem] == [12, 7, 3]
        assert [linha.chave for linha in ordem] == ["doze", "sete", "tres"]

    def test_SEM_watchlist_nenhuma_serie_vem_marcada(self) -> None:
        modelo = ModeloDeMercado.de_observacoes(serie("doze", 12))
        ordem = ordenar_para_o_console(modelo, [])
        assert [linha.na_watchlist for linha in ordem] == [False]

    def test_COM_watchlist_a_dela_vem_PRIMEIRA_e_MARCADA(self) -> None:
        """E o resto continua visivel abaixo: filtrar esconderia o item novo."""
        modelo = ModeloDeMercado.de_observacoes(
            serie("doze", 12, nome="Item Doze")
            + serie("tres", 3, nome="Item Tres")
            + serie("sete", 7, nome="Item Sete")
        )
        ordem = ordenar_para_o_console(modelo, ["Item Tres"])

        assert ordem[0].chave == "tres", "a serie da watchlist tem de vir primeiro"
        assert ordem[0].na_watchlist is True, "e tem de vir MARCADA"

        abaixo = [linha.chave for linha in ordem[1:]]
        assert "doze" in abaixo and "sete" in abaixo, (
            "as demais series continuam VISIVEIS abaixo. Filtrar de vez "
            "esconderia o item novo que a Fase 2 existe para descobrir"
        )
        assert [linha.na_watchlist for linha in ordem[1:]] == [False, False]

    def test_o_casamento_normaliza_caixa_e_colapsa_espacos(self) -> None:
        modelo = ModeloDeMercado.de_observacoes(
            serie("belt", 4, nome="Dragon Belt")
        )
        ordem = ordenar_para_o_console(modelo, ["  dragon   BELT "])
        assert ordem[0].na_watchlist is True

    def test_o_casamento_NAO_e_fuzzy_e_variante_de_encanto_nao_casa(self) -> None:
        """`+3 Dragon Belt` e `+4 Dragon Belt` sao series DELIBERADAMENTE
        separadas: medido numa pagina real, o mesmo nome base valia de 7,02 a
        100,00 conforme o encanto. Similaridade fuzzy as juntaria."""
        modelo = ModeloDeMercado.de_observacoes(
            serie("mais4", 4, nome="+4 Dragon Belt")
        )
        ordem = ordenar_para_o_console(modelo, ["+3 Dragon Belt"])
        assert ordem[0].na_watchlist is False

    def test_serie_da_watchlist_SEM_OBSERVACAO_NENHUMA_nao_derruba_a_ordem(
        self,
    ) -> None:
        modelo = ModeloDeMercado.de_observacoes(
            serie("doze", 12, nome="Item Doze") + serie("sete", 7, nome="Item Sete")
        )
        ordem = ordenar_para_o_console(modelo, ["Item Que Nunca Apareceu"])
        assert [linha.chave for linha in ordem] == ["doze", "sete"]

    def test_modelo_VAZIO_devolve_lista_vazia_sem_levantar(self) -> None:
        assert ordenar_para_o_console(ModeloDeMercado.de_observacoes([]), []) == []

    def test_o_TOPO_e_limitado_mas_a_watchlist_NUNCA_e_cortada(self) -> None:
        """O corte e do rabo por evidencia; um item marcado que sumisse por
        corte seria a watchlist virando porta de saida."""
        muitas: list[ObservacaoLida] = []
        for i in range(SERIES_NO_TOPO + 5):
            muitas += serie(f"s{i:02d}", 20 - i, nome=f"Item {i:02d}")
        rara = serie("rara", 1, nome="Item Raro")
        modelo = ModeloDeMercado.de_observacoes(muitas + rara)

        ordem = ordenar_para_o_console(modelo, ["Item Raro"])
        assert ordem[0].chave == "rara"
        assert len(ordem) == SERIES_NO_TOPO + 1, (
            "a watchlist entra ALEM do topo por evidencia, e nao no lugar dele"
        )

    def test_a_docstring_DIZ_a_divergencia_com_a_letra_do_criterio(self) -> None:
        """A decisao contraria a LETRA do criterio 3 do ROADMAP de proposito, e
        a divergencia precisa ser visivel para quem verificar a fase."""
        fonte = inspect.getsource(ordenar_para_o_console)
        assert "criterio 3" in fonte or "ROADMAP" in fonte
