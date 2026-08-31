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
import logging
from datetime import datetime, timedelta

import pytest

import l2scanner.config as config_mod
import l2scanner.mercado_console as mercado_console
import l2scanner.mercado_modo as mercado_modo
from l2scanner.agenda import AgendaInvalida
from l2scanner.config import ler_watchlist_do_mercado
from l2scanner.mercado_analise import (
    N_MINIMO_PARA_MEDIANA,
    N_MINIMO_PARA_TENDENCIA,
    SERIES_NO_TOPO,
    ModeloDeMercado,
    ordenar_para_o_console,
)
from l2scanner.mercado_console import secao_do_vale_quanto
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


class TestAWatchlistTambemOlhaOConfigLocal:
    """O MESMO precedente de `ler_membros` e `ler_personagem_do_jogo`.

    O usuario TEM um `config.local.toml` (o `.gitignore` o cobre, e e onde os
    telefones moram). Uma `watchlist` escrita la era silenciosamente ignorada,
    porque esta funcao so olhava o `ARQUIVO_CONFIG` — o desfecho MUDO que a
    propria doutrina do modulo declara inaceitavel.

    NAO E UMA TERCEIRA CONVENCAO: e a que ja existe, item por item. Um arquivo
    ou o outro, nunca a soma; o local vence; e quando os dois trazem a chave o
    arranque AVISA nomeando o vencedor.
    """

    VERSIONADO = '[mercado]\nwatchlist = ["Dragon Belt"]\n'
    LOCAL = '[mercado]\nwatchlist = ["Phantom Mask Sealed"]\n'

    def _arquivos(self, tmp_path, versionado, local):
        caminho = tmp_path / "config.toml"
        caminho_local = tmp_path / "config.local.toml"
        if versionado is not None:
            caminho.write_text(versionado, encoding="utf-8")
        if local is not None:
            caminho_local.write_text(local, encoding="utf-8")
        return caminho, caminho_local

    def test_so_o_local_LE_DO_LOCAL(self, tmp_path) -> None:
        """O caso do usuario: a watchlist so no arquivo que nao vai pro git."""
        caminho, local = self._arquivos(tmp_path, None, self.LOCAL)
        assert ler_watchlist_do_mercado(caminho, local) == [
            "Phantom Mask Sealed"
        ]

    def test_so_o_versionado_le_do_versionado(self, tmp_path) -> None:
        caminho, local = self._arquivos(tmp_path, self.VERSIONADO, None)
        assert ler_watchlist_do_mercado(caminho, local) == ["Dragon Belt"]

    def test_os_dois_o_local_VENCE_e_NAO_soma(self, tmp_path) -> None:
        """Somar poria o console a marcar item que o usuario apagou."""
        caminho, local = self._arquivos(tmp_path, self.VERSIONADO, self.LOCAL)
        assert ler_watchlist_do_mercado(caminho, local) == [
            "Phantom Mask Sealed"
        ]

    def test_os_dois_o_arranque_AVISA_nomeando_os_dois_arquivos(
        self, tmp_path, caplog
    ) -> None:
        caminho, local = self._arquivos(tmp_path, self.VERSIONADO, self.LOCAL)
        with caplog.at_level(logging.WARNING, logger="l2scanner"):
            ler_watchlist_do_mercado(caminho, local)
        assert "config.toml" in caplog.text
        assert "config.local.toml" in caplog.text

    def test_so_o_versionado_NAO_avisa(self, tmp_path, caplog) -> None:
        """Aviso sem conflito e aviso que se aprende a ignorar."""
        caminho, local = self._arquivos(tmp_path, self.VERSIONADO, None)
        with caplog.at_level(logging.WARNING, logger="l2scanner"):
            ler_watchlist_do_mercado(caminho, local)
        assert caplog.text == ""

    def test_nenhum_dos_dois_e_lista_vazia_sem_excecao(self, tmp_path) -> None:
        caminho, local = self._arquivos(tmp_path, None, None)
        assert ler_watchlist_do_mercado(caminho, local) == []

    def test_a_validacao_vale_igual_vinda_do_LOCAL(self, tmp_path) -> None:
        """A regra e escrita UMA vez: lixo derruba venha de onde vier.

        Um segundo caminho de leitura com validacao propria e como a regra
        morre: ela continua no arquivo antigo e some no novo, que e justamente
        o que todo mundo passa a usar.
        """
        caminho, local = self._arquivos(
            tmp_path, None, '[mercado]\nwatchlist = "Dragon Belt"\n'
        )
        with pytest.raises(AgendaInvalida) as erro:
            ler_watchlist_do_mercado(caminho, local)
        assert "config.local.toml" in str(erro.value), (
            "a recusa tem de nomear o arquivo que REALMENTE tem o erro"
        )

    def test_um_caminho_EXPLICITO_nao_arrasta_o_vizinho(self, tmp_path) -> None:
        """O guarda de que depende todo teste que passa um caminho so.

        Se um `caminho` explicito fosse buscar o `config.local.toml` ao lado, os
        testes acima passariam a ler a maquina de quem os roda.
        """
        caminho, _ = self._arquivos(tmp_path, self.VERSIONADO, self.LOCAL)
        assert ler_watchlist_do_mercado(caminho) == ["Dragon Belt"]

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


# ---------------------------------------------------------------------------
# "VALE QUANTO AGORA?" -- o desenho, com a evidencia colada ao numero
# ---------------------------------------------------------------------------

AGORA = datetime(2026, 8, 31, 18, 2, 0)


def serie_rica(chave: str = "belt", *, nome: str = "Dragon Belt"):
    """Doze ofertas: a mais BARATA por unidade e a mais ANTIGA.

    O cenario e montado para os DOIS carimbos diferirem -- o da oferta escolhida
    (10:00) e o `max(primeira_vez)` da serie (18:00). Sem isso, um teste de
    recencia ficaria verde sobre a implementacao errada.
    """
    barata = observacao(
        chave,
        4500,
        100,
        nome=nome,
        quando=datetime(2026, 8, 31, 10, 0, 0),
    )
    caras = [
        observacao(
            chave,
            900_000 + i * 1000,
            1,
            nome=nome,
            quando=datetime(2026, 8, 31, 18, 0, 0) - (10 - i) * UM_MINUTO,
        )
        for i in range(11)
    ]
    return [barata] + caras


def serie_magra(chave: str = "raro", *, nome: str = "Item Raro"):
    """Tres ofertas: acima do piso do menor (1) e abaixo do da mediana (5)."""
    return [
        observacao(
            chave,
            700 + i * 100,
            1,
            nome=nome,
            quando=datetime(2026, 8, 31, 17, 0, 0) + i * UM_MINUTO,
        )
        for i in range(3)
    ]


def linha_com(texto: str, marca: str) -> str:
    """A UNICA linha do texto que contem `marca`. Falha se nao houver uma so.

    Assercao sobre a LINHA e nao sobre o texto inteiro: `"10:00" in texto` fica
    verde quando o carimbo certo aparece em QUALQUER outro lugar do bloco, que
    e exatamente o engano que o criterio da recencia existe para pegar.
    """
    achadas = [linha for linha in texto.splitlines() if marca in linha]
    assert len(achadas) == 1, f"esperava UMA linha com {marca!r}, achei {achadas}"
    return achadas[0]


class TestANomenclaturaEstaPresa:
    """T-04-16: o scanner ve OFERTAS, nao transacoes."""

    def test_nenhuma_EXPRESSAO_PROIBIDA_no_texto_devolvido(self) -> None:
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes(serie_rica() + serie_magra()),
            [],
            AGORA,
        )
        baixo = texto.lower()
        for proibida in EXPRESSOES_PROIBIDAS:
            assert proibida.lower() not in baixo, (
                f"a secao usou a expressao proibida {proibida!r}. O scanner ve "
                f"OFERTAS, nao transacoes: a palavra do requisito e "
                f"'menor pedido visivel'"
            )

    def test_nenhuma_EXPRESSAO_PROIBIDA_no_FONTE_dos_dois_modulos(self) -> None:
        """A varredura do RETORNO nao alcanca `linha_ao_vivo` nem
        `resumo_da_sessao`, escritas no plano 04-01: nenhum outro teste desta
        fase as varre. E ela tambem nao alcanca rotulo de outra funcao,
        comentario nem docstring -- os tres lugares de onde a expressao volta."""
        for modulo in (mercado_console, mercado_modo):
            fonte = inspect.getsource(modulo).lower()
            for proibida in EXPRESSOES_PROIBIDAS:
                assert proibida.lower() not in fonte, (
                    f"a expressao proibida {proibida!r} aparece no fonte de "
                    f"{modulo.__name__}"
                )

    def test_o_rotulo_do_requisito_ESTA_no_texto(self) -> None:
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes(serie_rica()), [], AGORA
        )
        assert "menor pedido visivel" in texto.lower()


class TestAEvidenciaViajaColadaAoNumero:
    def test_o_n_e_o_TOTAL_com_a_QUANTIDADE_ao_lado(self) -> None:
        """Nunca um total solto: um lote de 100 custa mais que um de 1 sem que
        nenhum dos dois seja mais caro. Foi assim que a leitura de `4,50` para
        um item de `1.480,00` virou um pitfall nomeado na pesquisa."""
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes(serie_rica()), [], AGORA
        )
        menor = linha_com(texto, "menor pedido visivel")
        assert "n=12" in texto
        assert "45,00" in menor, "o TOTAL daquela oferta tem de aparecer"
        assert "100" in menor, "a QUANTIDADE tem de aparecer ao lado do total"

    def test_o_unitario_aparece_MARCADO_COMO_DERIVADO(self) -> None:
        """Ele nao esta no CSV de proposito (D-02): o que o jogo exibe e
        derivacao arredondada, e a marca e o que impede alguem de o tratar como
        dado gravado."""
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes(serie_rica()), [], AGORA
        )
        assert "derivado" in linha_com(texto, "menor pedido visivel")

    def test_o_carimbo_do_menor_e_o_DAQUELA_OFERTA_e_nao_o_da_serie(
        self,
    ) -> None:
        """A oferta escolhida foi vista as 10:00; a mais NOVA da serie, as
        18:00. Um minimo de manha ao lado da recencia de agora e a mentira
        plausivel que este projeto inteiro combate."""
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes(serie_rica()), [], AGORA
        )
        menor = linha_com(texto, "menor pedido visivel")
        assert "10:00" in menor
        assert "18:00" not in menor, (
            "a linha do menor esta carregando o max(primeira_vez) da SERIE"
        )

    def test_a_recencia_sai_nas_DUAS_formas_relativa_e_absoluta(self) -> None:
        """O relativo e o que o olho le; o absoluto e o que sobrevive a copiar
        a linha para o WhatsApp."""
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes(serie_rica()), [], AGORA
        )
        menor = linha_com(texto, "menor pedido visivel")
        assert "ha " in menor, "falta a forma RELATIVA"
        assert "31/08 10:00" in menor, "falta a forma ABSOLUTA"


class TestAbaixoDoPisoOTextoDIZ_O_QUE_FALTA:
    def test_serie_de_TRES_informa_a_contagem_e_o_PISO_sem_imprimir_mediana(
        self,
    ) -> None:
        """Uma mediana de tres observacoes e um numero que engana."""
        observacoes = serie_magra()
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes(observacoes), [], AGORA
        )
        mediana = linha_com(texto, "mediana")
        assert "3" in mediana, "a contagem ATUAL tem de aparecer"
        assert str(N_MINIMO_PARA_MEDIANA) in mediana, "o PISO tem de aparecer"
        # O valor que `median_low` devolveria se o piso fosse ignorado: 800
        # centesimos por unidade -> `8,00`. Ele NAO pode ser impresso.
        assert "8,00" not in texto, (
            "um valor de mediana foi impresso para uma serie abaixo do piso"
        )

    def test_a_tendencia_carrega_o_TAMANHO_DA_JANELA(self) -> None:
        """Sem o tamanho, a reta de 3 pontos parece a de 300."""
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes(serie_rica()), [], AGORA
        )
        tendencia = linha_com(texto, "tendencia")
        assert "12" in tendencia, "o n da janela tem de aparecer"
        assert "ofertas distintas" in tendencia, (
            "a unidade tem de designar OFERTAS DISTINTAS, e nao instantes: o "
            "CSV nao tem serie temporal de preco"
        )

    def test_com_menos_que_o_piso_da_tendencia_o_texto_diz_o_que_falta(
        self,
    ) -> None:
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes(serie_magra()), [], AGORA
        )
        tendencia = linha_com(texto, "tendencia")
        assert str(N_MINIMO_PARA_TENDENCIA) in tendencia


class TestOAvisoDoRelogioSaiUMA_VEZ:
    def test_relogio_SEM_ANCORA_avisa_exatamente_uma_vez(self) -> None:
        """Sem esse aviso, "ha 12 min" pode estar tres horas errado num dual
        boot -- que e o defeito que o `Relogio` existe para corrigir."""
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes(serie_rica() + serie_magra()),
            [],
            AGORA,
            relogio_confiavel=False,
        )
        assert texto.count(mercado_console.AVISO_DO_RELOGIO_SEM_ANCORA) == 1

    def test_relogio_ANCORADO_nao_avisa_nada(self) -> None:
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes(serie_rica()),
            [],
            AGORA,
            relogio_confiavel=True,
        )
        assert mercado_console.AVISO_DO_RELOGIO_SEM_ANCORA not in texto


class TestASecaoNaoQuebraEMarcaAWatchlist:
    def test_modelo_VAZIO_diz_que_ainda_nao_ha_nada_em_vez_de_sair_em_branco(
        self,
    ) -> None:
        """Bloco em branco parece defeito; o usuario precisa ver que o modo
        esta vivo e ainda nao achou nada."""
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes([]), [], AGORA
        )
        assert "nenhuma observacao" in texto.lower()

    def test_a_serie_da_watchlist_vem_PRIMEIRA_e_MARCADA_no_texto(self) -> None:
        modelo = ModeloDeMercado.de_observacoes(serie_rica() + serie_magra())
        texto = secao_do_vale_quanto(modelo, ["Item Raro"], AGORA)
        assert mercado_console.MARCA_DA_WATCHLIST in linha_com(
            texto, "Item Raro"
        )
        assert texto.index("Item Raro") < texto.index("Dragon Belt")

    def test_o_console_NAO_USA_o_ultima_vez_do_catalogo(self) -> None:
        """T-04-14: a recencia do ITEM exibida como recencia do PRECO.

        O `ultima_vez` do `catalogo-de-nomes.csv` diz quando o item foi visto
        pela ultima vez em QUALQUER valor, e pode ser de agora mesmo sobre uma
        leitura de tres dias atras. A recencia que o ANAL-01 pede e a do PRECO,
        `max(primeira_vez)` do `observacoes.csv`.

        CORRECAO DE CRITERIO, DITA EM VOZ ALTA. O plano pedia
        `grep -n "ultima_vez" l2scanner/mercado_console.py` sem ocorrencia. Esse
        criterio, ao pe da letra, e INSATISFAZIVEL junto com a decisao que o
        plano 04-02 ja travou POR TESTE
        (`test_a_docstring_NOMEIA_a_outra_recencia_para_ninguem_confundir`):
        la a docstring de `recencia_do_preco` e OBRIGADA a citar `ultima_vez`,
        justamente para ninguem trocar um pelo outro. Apagar a mesma prosa deste
        modulo para satisfazer o grep tiraria o aviso do lugar onde ele protege,
        e deixaria o proximo leitor sem saber que existem duas recencias.

        A PROVA AQUI E SOBRE O CODIGO EXECUTAVEL, com docstrings e comentarios
        arrancados pelo AST -- estritamente mais forte que a varredura de texto,
        que reprova a documentacao e nao distingue um USO de uma MENCAO. E a
        mesma tecnica que `tests/test_mercado_firewall_de_fase.py` ja estabeleceu
        nesta arvore para exatamente esta classe de problema.
        """
        arvore = ast.parse(inspect.getsource(mercado_console))
        for no in list(ast.walk(arvore)):
            corpo = getattr(no, "body", None)
            if not isinstance(corpo, list) or not corpo:
                continue
            primeiro = corpo[0]
            if (
                isinstance(primeiro, ast.Expr)
                and isinstance(primeiro.value, ast.Constant)
                and isinstance(primeiro.value.value, str)
            ):
                corpo.pop(0)
        codigo = ast.unparse(arvore)

        assert "ultima_vez" not in codigo, (
            "o console USA o `ultima_vez` do catalogo; a recencia do ANAL-01 e "
            "`max(primeira_vez)` do observacoes.csv"
        )
        # O controle: a mencao em PROSA continua la, e e ela que impede a
        # confusao. Um teste que so afirmasse a ausencia no codigo ficaria
        # verde tambem se alguem apagasse o aviso inteiro.
        assert "ultima_vez" in inspect.getsource(mercado_console), (
            "o aviso que NOMEIA a outra recencia sumiu do modulo"
        )

    def test_o_residuo_do_cruzamento_NAO_aparece(self) -> None:
        """A guarda de cruzamento esta DESLIGADA por medicao: o residuo e
        observacao e nao veredito, e ja esta no CSV para o usuario olhar no
        Sheets. Mostrar um numero que o proprio projeto declarou nao-decidivel
        e convidar a interpretacao errada."""
        texto = secao_do_vale_quanto(
            ModeloDeMercado.de_observacoes(serie_rica()), [], AGORA
        )
        assert "residuo" not in texto.lower()
