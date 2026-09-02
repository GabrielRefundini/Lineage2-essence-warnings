"""A SUPERFICIE do dashboard, conferida por PARSE e por expressao regular.

O QUE ESTE ARQUIVO PRENDE
=========================
A estrutura das tres regioes, as frases da tela, o tema (paleta, escala
tipografica, escala de espacamento) e o desenho de cada estado. Tudo afirmado
sobre os ARQUIVOS em disco, sem navegador: e a mesma doutrina de prova do resto
da fase, que ja afirma a CSP e o payload sem subir um Chrome.

POR QUE PARSE, E NAO BUSCA DE TEXTO
====================================
`'id="destaque"' in pagina` passaria com o identificador dentro de um
comentario, ou de um atributo de outro elemento, ou de um exemplo em prosa. O
que se quer afirmar e que o ELEMENTO existe na arvore — entao o teste monta a
arvore com o analisador da biblioteca padrao (`html.parser`, o mesmo molde de
`tests/test_dashboard_tracer.py:...`) e pergunta a ela.

A DIVERGENCIA DE ACENTUACAO E INTENCIONAL
==========================================
As frases da MOLDURA sao nossas, sao HTML em UTF-8 e levam acento. As strings de
VALOR chegam prontas do Python em ASCII (`"11,60 XM por milhao de adena
(derivado)"`). Reacentuar no navegador seria o segundo formatador que o DASH-03
proibe. Este arquivo confere as duas convencoes lado a lado, cada uma na sua
fonte, e nao tenta unifica-las.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

import pytest

from l2scanner import dashboard, dashboard_dados

# ---------------------------------------------------------------------------
# OS ARQUIVOS SOB JULGAMENTO
# ---------------------------------------------------------------------------
#
# `vendor/uPlot.min.css` NAO entra em nenhuma assercao de tema. Ele e artefato de
# TERCEIRO, tem hexadecimais e tamanhos de fonte proprios, e cobrar dele a nossa
# escala seria cobrar de quem nao assinou o contrato. O portao que vale para ele
# e outro (VEND-1..4, em `tests/test_firewall_dashboard.py`). O que ESTE arquivo
# cobra do vendor e uma coisa so: que ele seja carregado ANTES do nosso CSS.
PASTA = dashboard.PASTA_DOS_ESTATICOS
ARQUIVO_DO_HTML = PASTA / "index.html"
ARQUIVO_DO_CSS = PASTA / "dashboard.css"
FOLHA_DA_BIBLIOTECA = "vendor/uPlot.min.css"


@pytest.fixture(scope="module")
def html() -> str:
    return ARQUIVO_DO_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css() -> str:
    return ARQUIVO_DO_CSS.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# O ANALISADOR
# ---------------------------------------------------------------------------


class _Arvore(HTMLParser):
    """Coleta o que as assercoes precisam perguntar da arvore, e nada mais.

    Guarda os elementos NA ORDEM em que aparecem, porque uma das afirmacoes
    (a folha da biblioteca antes da nossa) e sobre ordem e nao sobre presenca.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elementos: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        self.elementos.append((tag, dict(attrs)))

    # `<input>`, `<link>` e `<meta>` sao vazios: sem esta linha o analisador os
    # entregaria por `handle_startendtag` e o campo do cambio sumiria do teste.
    def handle_startendtag(self, tag: str, attrs) -> None:  # noqa: ANN001
        self.handle_starttag(tag, attrs)

    def de(self, tag: str) -> list[dict[str, str | None]]:
        return [atributos for nome, atributos in self.elementos if nome == tag]

    def por_id(self, identificador: str) -> dict[str, str | None] | None:
        for _, atributos in self.elementos:
            if atributos.get("id") == identificador:
                return atributos
        return None

    def tag_do_id(self, identificador: str) -> str | None:
        for nome, atributos in self.elementos:
            if atributos.get("id") == identificador:
                return nome
        return None


@pytest.fixture(scope="module")
def arvore(html: str) -> _Arvore:
    analisador = _Arvore()
    analisador.feed(html)
    return analisador


# ---------------------------------------------------------------------------
# AS TRES REGIOES, O FORMULARIO, E O QUE A CSP PROIBE
# ---------------------------------------------------------------------------

# Os identificadores estao TRAVADOS no `01-UI-SPEC.md`, secao `Layout &
# Componentes`. Sao contrato entre esta pagina e o `dashboard.js`, e por isso
# aparecem escritos por extenso aqui: renomear um sem renomear o outro e a
# falha silenciosa que este teste existe para nao permitir.
REGIOES = ("destaque", "serie", "procedencia")


class TestAEstruturaDaPagina:
    def test_as_TRES_regioes_do_contrato_existem_como_ELEMENTO(
        self, arvore: _Arvore
    ) -> None:
        """Por parse, e nao por busca de texto.

        `'id="destaque"' in pagina` ficaria verde com o identificador dentro de
        um comentario — e esta pagina TEM comentarios longos que citam os
        identificadores. A pergunta certa e para a arvore.
        """
        for regiao in REGIOES:
            assert arvore.tag_do_id(regiao) == "section", regiao

    def test_o_envio_do_cambio_e_um_FORMULARIO_de_verdade(
        self, arvore: _Arvore
    ) -> None:
        """A tecla de confirmacao tem de submeter — e a mao do usuario ja espera.

        Um campo solto ao lado de um botao parece igual na tela e e diferente no
        teclado. E o `type="submit"` e parte da afirmacao: um botao sem tipo
        dentro de um formulario submete por acidente do padrao, e nao por
        escolha registrada.
        """
        assert arvore.tag_do_id("form-cambio") == "form"
        assert arvore.tag_do_id("campo-cambio") == "input"

        botao = arvore.por_id("botao-salvar")
        assert botao is not None
        assert botao.get("type") == "submit"

    def test_o_formulario_NAO_declara_destino(self, arvore: _Arvore) -> None:
        """A CSP traz `form-action 'none'`, e a colisao e a falha fechada CERTA.

        O caminho normal e o JS interceptar o envio e fazer o POST. Um envio que
        escapasse do JS, com destino declarado, seria BARRADO pelo navegador em
        vez de levar o cambio para fora — que e exatamente o comportamento que
        se quer quando algo deu errado.
        """
        formulario = arvore.por_id("form-cambio")
        assert formulario is not None
        assert "action" not in formulario

    def test_o_campo_do_cambio_tem_ROTULO_associado_por_vinculo(
        self, arvore: _Arvore
    ) -> None:
        """Rotulo visual ao lado nao e rotulo: o vinculo e que faz o clique no
        texto focar o campo e o leitor de tela anunciar o que se pede ali."""
        rotulos = [
            atributos
            for atributos in arvore.de("label")
            if atributos.get("for") == "campo-cambio"
        ]
        assert len(rotulos) == 1

    def test_o_campo_nasce_VAZIO_com_o_exemplo_so_como_placeholder(
        self, arvore: _Arvore
    ) -> None:
        """O placeholder NUNCA pode ser submetido como valor.

        `0,50` e um exemplo. Se ele nascesse em `value`, um usuario que so
        clicasse em salvar gravaria um cambio que ele nao escolheu — e o R$ da
        tela inteira passaria a ser derivado de um numero inventado pela
        interface. Dinheiro real nao se preenche sozinho.
        """
        campo = arvore.por_id("campo-cambio")
        assert campo is not None
        assert campo.get("placeholder") == "0,50"
        assert campo.get("value", "") == ""
        assert campo.get("inputmode") == "decimal"

    def test_o_campo_do_cambio_tem_LIMITE_de_comprimento(
        self, arvore: _Arvore
    ) -> None:
        """Um numero absurdamente longo e recusado ANTES de virar layout."""
        campo = arvore.por_id("campo-cambio")
        assert campo is not None
        limite = campo.get("maxlength")
        assert limite is not None
        assert 0 < int(limite) <= 32

    def test_todo_script_carrega_por_ARQUIVO(self, arvore: _Arvore) -> None:
        """`script-src 'self'` proibe a forma embutida.

        A primeira linha nao e cerimonia: `all([])` e verdadeiro, entao uma
        pagina que perdesse o `<script>` passaria com louvor no `all` abaixo. E
        o padrao de guarda-vacuo que `test_mercado_firewall_de_fase.py` ja nomeia
        nesta arvore — um guarda cuja saida nao muda com o fato que ele julga.
        """
        scripts = arvore.de("script")
        assert scripts, "o index deixou de carregar qualquer script"
        assert all("src" in atributos for atributos in scripts)

    def test_a_contagem_de_estilos_EMBUTIDOS_e_zero(self, arvore: _Arvore) -> None:
        """`style-src 'self'` proibe o `<style>` e o atributo `style=`.

        As duas formas, e nao so a primeira: um `style="color: ..."` num
        elemento seria a segunda paleta do projeto, escondida na marcacao.
        """
        assert arvore.de("style") == []
        assert [
            atributos
            for _, atributos in arvore.elementos
            if "style" in atributos
        ] == []

    def test_a_contagem_de_atributos_de_EVENTO_e_zero(self, arvore: _Arvore) -> None:
        """A terceira forma que a CSP proibe, e a mais facil de deixar passar.

        `onclick=` num botao nao parece codigo embutido numa revisao rapida — mas
        e, e o navegador o bloquearia calado. Aqui ele falha em voz alta.
        """
        com_evento = [
            (tag, nome)
            for tag, atributos in arvore.elementos
            for nome in atributos
            if nome.startswith("on")
        ]
        assert com_evento == []

    def test_a_folha_da_BIBLIOTECA_vem_antes_da_nossa(self, arvore: _Arvore) -> None:
        """A ordem e a afirmacao, e ela nao aparece em nenhum teste de conteudo.

        Quem vem depois vence a especificidade empatada. O bloco de sobreposicoes
        de tema no fim do `dashboard.css` so consegue retematizar o grafico se o
        `uPlot.min.css` ja tiver sido lido. Inverter as duas linhas quebraria o
        tema sem quebrar mais nada — dai existir um teste da ORDEM.
        """
        folhas = [
            atributos.get("href")
            for atributos in arvore.de("link")
            if atributos.get("rel") == "stylesheet"
        ]
        assert FOLHA_DA_BIBLIOTECA in folhas
        assert "dashboard.css" in folhas
        assert folhas.index(FOLHA_DA_BIBLIOTECA) < folhas.index("dashboard.css")

    def test_a_pagina_declara_pt_BR_e_UTF_8(self, arvore: _Arvore) -> None:
        """As frases da moldura levam acento; sem o charset declarado elas viram
        mojibake e a tela passa a mentir sobre a propria lingua."""
        html_ = arvore.de("html")
        assert html_ and html_[0].get("lang") == "pt-BR"
        assert any(
            atributos.get("charset", "").lower() == "utf-8"
            for atributos in arvore.de("meta")
        )


# ---------------------------------------------------------------------------
# AS FRASES DA TELA
# ---------------------------------------------------------------------------
#
# AS SEIS PRIMEIRAS VEM DAS CONSTANTES DO PYTHON, de proposito. Elas existem nos
# DOIS lados — o servidor as manda em `avisos`, e a marcacao as tem fixas — e a
# unica forma de as duas copias nao divergirem e uma julgar a outra. Repetir a
# string literal aqui deixaria o teste verde no dia em que alguem editasse so um
# dos lados.
FRASES_QUE_O_PYTHON_TAMBEM_CONHECE = {
    "titulo do estado vazio": dashboard_dados.TITULO_DO_ESTADO_VAZIO,
    "corpo do estado vazio": dashboard_dados.CORPO_DO_ESTADO_VAZIO,
    "R$ indisponivel": dashboard_dados.FRASE_DE_REAIS_INDISPONIVEL,
    "aviso do cambio historico": dashboard_dados.AVISO_DO_CAMBIO_HISTORICO,
    "rotulo do menor": dashboard_dados.ROTULO_DO_MENOR,
    "rotulo da tipica": dashboard_dados.ROTULO_DA_TIPICA,
}

# AS DA MOLDURA sao so nossas: o Python nunca as emite, porque nenhuma delas
# descreve um dado. Elas estao travadas no `## Copywriting Contract` do
# `01-UI-SPEC.md` e sao escritas a mao aqui, que e o unico lugar onde podem ser.
FRASES_SO_DA_MARCACAO = {
    "CTA primario": "Salvar câmbio",
    "rotulo do campo": "1 XM = R$",
    "rotulo de salvamento em curso": "Salvando…",
    "rotulo da primeira pintura": "Lendo o arquivo…",
    "restaurar o alcance total": "Ver todo o período",
    "marca de somente leitura": "somente leitura",
    # A do servidor mudo e nossa por definicao: o servidor mudo e o estado em
    # que o Python NAO respondeu, entao ele nao pode ser a fonte da frase. Ela
    # e conferida em dois pedacos porque o tempo decorrido entra no meio.
    "servidor mudo (inicio)": "Sem contato com o servidor local há",
    "servidor mudo (fim)": "A tela mostra a última resposta recebida, não o agora.",
}

# AS PROIBIDAS. ESTA LISTA E ESCRITA A MAO DE PROPOSITO.
#
# Ela nao e derivada de nenhuma constante porque o ponto dela e ser uma segunda
# opiniao: uma lista gerada a partir do mesmo lugar que a producao usa nao
# testaria nada: aprovaria qualquer frase que alguem removesse de la. As tres
# primeiras sao a MESMA mentira — o scanner ve OFERTAS no quadro, e nao
# transacoes concluidas; ninguem COMPROU por este valor, alguem PEDIU este
# valor. A quarta e a de espaco reservado: ausencia se escreve com palavra,
# nunca com zero, porque um `0,00` na tela e indistinguivel de uma leitura real
# de zero.
FRASES_PROIBIDAS_ESCRITAS_A_MAO = (
    "preço de venda",
    "preco de venda",
    "vendido por",
    "valor de mercado",
    "0,00",
)


class TestAsFrasesSaoAsDoContrato:
    @pytest.mark.parametrize(
        "nome", sorted(FRASES_QUE_O_PYTHON_TAMBEM_CONHECE)
    )
    def test_a_frase_que_o_python_tambem_conhece_esta_LITERAL_na_marcacao(
        self, nome: str, html: str
    ) -> None:
        """Uma copia julga a outra. Editar so um dos lados fica vermelho."""
        assert FRASES_QUE_O_PYTHON_TAMBEM_CONHECE[nome] in html

    @pytest.mark.parametrize("nome", sorted(FRASES_SO_DA_MARCACAO))
    def test_a_frase_da_moldura_esta_LITERAL_na_marcacao(
        self, nome: str, html: str
    ) -> None:
        assert FRASES_SO_DA_MARCACAO[nome] in html

    @pytest.mark.parametrize("proibida", FRASES_PROIBIDAS_ESCRITAS_A_MAO)
    def test_a_frase_proibida_nao_aparece_em_lugar_nenhum(
        self, proibida: str, html: str, css: str
    ) -> None:
        """No HTML E no CSS: um `content: "0,00"` num pseudo-elemento seria
        exatamente o espaco reservado com zeros, escrito onde ninguem procura."""
        assert proibida not in html.lower()
        assert proibida not in css.lower()

    def test_a_lista_escrita_a_mao_COBRE_a_do_python(self) -> None:
        """A segunda opiniao nao pode ficar para tras da primeira.

        Se alguem acrescentar uma proibicao no `dashboard_dados`, esta lista tem
        de crescer junto — senao a pagina passaria a poder escrever na tela uma
        frase que o payload ja recusa, e a incoerencia nao apareceria em lugar
        nenhum.
        """
        assert set(dashboard_dados.FRASES_PROIBIDAS) <= set(
            FRASES_PROIBIDAS_ESCRITAS_A_MAO
        )
