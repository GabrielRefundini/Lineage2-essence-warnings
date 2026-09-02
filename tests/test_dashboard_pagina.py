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

import re
from html.parser import HTMLParser

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

    def test_a_BIBLIOTECA_do_grafico_carrega_ANTES_do_nosso_script(
        self, arvore: _Arvore
    ) -> None:
        """A folha do vendor tinha guarda de ORDEM; o script do vendor nao tinha.

        A ASSIMETRIA FOI MEDIDA na verificacao da fase, em 2026-09-02: nenhum
        teste desta suite nomeava a tag do `uPlot.iife.min.js` nem o carregador
        de reserva do `dashboard.js`. Apagar OS DOIS deixava a suite inteira
        verde e o grafico nunca desenhava — o guarda-vacuo exato que o
        `test_todo_script_carrega_por_ARQUIVO` acima descreve, repetido um nivel
        adiante: `all(...)` continuaria verdadeiro sobre a lista que sobrasse.

        A ORDEM E O QUE SE AFIRMA, e nao apenas a presenca. Dois `defer`
        executam na ordem do documento, entao a tag do vendor tem de vir ANTES
        da nossa: invertidas, `window.uPlot` seria `undefined` quando
        `comecar()` roda, e a pagina cairia no carregador de reserva sem que
        nada acusasse. E a mesma razao pela qual a FOLHA do vendor ja tinha
        teste de ordem — esta e a metade que faltava.

        O CARREGADOR DE RESERVA NAO E TESTADO AQUI de proposito: ele vive no
        `dashboard.js` e e afirmado la. As duas rotas sao deliberadamente
        compativeis (ele confere `window.uPlot` antes de agir), e por isso
        nenhuma das duas pode ser a unica prova de que o grafico consegue
        existir.
        """
        fontes = [atributos.get("src", "") for atributos in arvore.de("script")]
        assert "vendor/uPlot.iife.min.js" in fontes, (
            "o index parou de carregar a biblioteca do grafico"
        )
        assert "dashboard.js" in fontes
        assert fontes.index("vendor/uPlot.iife.min.js") < fontes.index(
            "dashboard.js"
        ), "a biblioteca tem de vir antes do nosso script — dois defer rodam em ordem"

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


# ---------------------------------------------------------------------------
# O TEMA
# ---------------------------------------------------------------------------
#
# TUDO AQUI JULGA SO O `dashboard.css`. O `vendor/uPlot.min.css` tem
# hexadecimais, `system-ui` e peso 600 proprios, e cobrar dele a nossa escala
# seria cobrar de quem nao assinou o contrato. O que a tela FINAL mostra e
# corrigido pelo bloco nomeado de sobreposicoes no fim do nosso arquivo — e e
# por isso que aquele bloco existe.

# O bloco de tokens em raiz. Uma expressao e nao um `split`, porque o que se
# quer e o TRECHO entre as chaves, e o arquivo tem outras chaves depois.
_INICIO_DA_RAIZ = ":root {"


def _bloco_de_tokens(css: str) -> str:
    """O texto entre as chaves do `:root`, e nada mais.

    O bloco nao tem chaves aninhadas, entao o primeiro `}` fecha. Se um dia
    tiver, esta funcao passa a devolver menos do que devia — e o teste de
    controle negativo abaixo (que exige achar hexadecimais AQUI DENTRO) e o que
    faria essa quebra aparecer, em vez de virar uma aprovacao silenciosa.
    """
    inicio = css.index(_INICIO_DA_RAIZ) + len(_INICIO_DA_RAIZ)
    return css[inicio : css.index("}", inicio)]


def _fora_do_bloco_de_tokens(css: str) -> str:
    inicio = css.index(_INICIO_DA_RAIZ)
    fim = css.index("}", inicio + len(_INICIO_DA_RAIZ)) + 1
    return css[:inicio] + css[fim:]


# A MESMA EXPRESSAO QUE `test_dashboard_tracer.py` ja usa sobre o JS. Manter as
# duas iguais e deliberado: uma paleta clandestina tem a mesma forma nos dois
# arquivos, e duas expressoes diferentes divergiriam na primeira correcao.
CACA_HEXADECIMAL = re.compile(r"#[0-9a-fA-F]{3,8}\b")

# A escala de 4 pontos, em numero. Um conjunto e nao uma lista: a pergunta e de
# pertencimento.
ESCALA_DE_ESPACAMENTO = {4, 8, 16, 24, 32, 48, 64}

# AS PROPRIEDADES QUE SAO ESPACO. Fora desta lista, um `px` e outra coisa —
# tipografia, traco, raio ou sombra — e nao responde a escala de espacamento.
PROPRIEDADES_DE_ESPACO = frozenset(
    {
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "gap",
        "row-gap",
        "column-gap",
        "inset",
    }
)

# AS TRES EXCECOES DECLARADAS NO `01-UI-SPEC.md`, nomeadas uma a uma. Elas NAO
# sao espacamento — sao TRACO — e por isso nenhuma delas aparece na lista acima:
#
#   1. Larguras de borda (1px e 2px), usadas pelo relevo das placas. Vivem em
#      `border`, `border-top` e `border-bottom`.
#   2. Espessura de linha do grafico (2px no menor pedido, 1.5px na mediana).
#      Sao parametros de configuracao da biblioteca, e nem sequer entram no CSS.
#   3. O anel de foco: 2px de traco com 2px de deslocamento, em `outline` e
#      `outline-offset`.
#
# Estao escritas aqui para que a tolerancia seja EXPLICITA e conferivel, em vez
# de virar um "o teste nao pega isso" que ninguem sabe se foi decidido ou
# esquecido.
EXCECOES_DE_TRACO = (
    "border / border-top / border-bottom — largura de borda, 1px e 2px",
    "espessura de linha do grafico — 2px e 1.5px, config da biblioteca",
    "outline / outline-offset — anel de foco, 2px e 2px",
)

_DECLARACAO = re.compile(r"(?m)^\s*([a-z-]+)\s*:\s*([^;{}]+);")
_PIXEL = re.compile(r"(\d+(?:\.\d+)?)px")


def _espacamentos_fora_da_escala(css: str) -> list[tuple[str, str]]:
    """(propriedade, valor) de todo espacamento em px que nao esta na escala."""
    fora: list[tuple[str, str]] = []
    for propriedade, valor in _DECLARACAO.findall(css):
        if propriedade not in PROPRIEDADES_DE_ESPACO:
            continue
        for medida in _PIXEL.findall(valor):
            if float(medida) not in ESCALA_DE_ESPACAMENTO:
                fora.append((propriedade, valor.strip()))
    return fora


class TestOTemaObedeceOContrato:
    def test_nenhum_hexadecimal_vive_FORA_do_bloco_de_tokens(self, css: str) -> None:
        """A paleta mora num lugar so, e a razao nao e estetica.

        O `dashboard.js` pede cor por `getPropertyValue`, e uma cor sem nome de
        token e uma cor que o grafico NAO CONSEGUE PEDIR. Um hexadecimal solto
        aqui seria a segunda paleta do projeto, e ela divergiria da primeira no
        dia em que o tema mudasse.
        """
        assert CACA_HEXADECIMAL.findall(_fora_do_bloco_de_tokens(css)) == []

    def test_o_bloco_de_tokens_TEM_hexadecimais(self, css: str) -> None:
        """O CONTROLE NEGATIVO, e e ele que torna a assercao acima uma prova.

        A mesma expressao, no mesmo arquivo, ACHA hexadecimais dentro do bloco.
        Sem esta linha, um erro de digitacao na expressao — ou um `:root` que
        deixasse de ser encontrado — deixaria o guarda verde para sempre sobre
        um CSS cheio de cor solta.
        """
        assert CACA_HEXADECIMAL.findall(_bloco_de_tokens(css))

    def test_a_marcacao_nao_declara_UMA_cor(self, html: str) -> None:
        """Cor no HTML seria a terceira paleta, escondida na marcacao."""
        assert CACA_HEXADECIMAL.findall(html) == []

    def test_todo_espacamento_em_px_pertence_a_ESCALA_de_quatro_pontos(
        self, css: str
    ) -> None:
        assert _espacamentos_fora_da_escala(css) == []

    def test_o_leitor_de_espacamento_ACUSA_um_valor_fora_da_escala(self) -> None:
        """O CONTROLE POSITIVO do leitor acima.

        Um teste que so afirma "nao achei nada" e indistinguivel de um leitor
        quebrado que nunca acha nada. Este exercita o leitor contra um CSS
        sintetico com um `13px` de propositio, e exige que ele ACUSE.
        """
        assert _espacamentos_fora_da_escala(".x {\n  padding: 13px;\n}") == [
            ("padding", "13px")
        ]

    def test_as_tres_excecoes_de_traco_estao_NOMEADAS(self) -> None:
        """A tolerancia e explicita, e nao um silencio do teste.

        Sem esta lista escrita, "o teste nao cobra a borda" seria indistinguivel
        de "alguem esqueceu de cobrar a borda".
        """
        assert len(EXCECOES_DE_TRACO) == 3
        assert all(excecao.strip() for excecao in EXCECOES_DE_TRACO)

    def test_a_escala_tipografica_tem_no_maximo_QUATRO_tamanhos(
        self, css: str
    ) -> None:
        """Body, Label, Heading e Display — e nada alem disso.

        O `clamp` do Display conta como UM, e nao como dois: o piso e o teto sao
        extremos do MESMO papel da escala. Ler `32px` e `48px` como dois
        tamanhos e o erro que o proprio checker do UI-SPEC ja levantou uma vez.
        """
        tamanhos = {
            " ".join(valor.split())
            for propriedade, valor in _DECLARACAO.findall(css)
            if propriedade == "font-size"
        }
        assert len(tamanhos) <= 4, sorted(tamanhos)

    def test_a_escala_tipografica_tem_no_maximo_DOIS_pesos(self, css: str) -> None:
        pesos = {
            valor.strip()
            for propriedade, valor in _DECLARACAO.findall(css)
            if propriedade == "font-weight"
        }
        assert len(pesos) <= 2, sorted(pesos)

    def test_todo_numero_da_tela_usa_LARGURA_TABULAR(self, css: str) -> None:
        """Sem largura tabular, um numero que se atualiza a cada 2 s DANCA
        horizontalmente — ruido puro ao lado do jogo.

        A regra e sobre o papel Display, que e o numero que decide dinheiro: se
        ele existe, ele e monoespacado e tabular.
        """
        assert "font-variant-numeric: tabular-nums" in css
        display = css[css.index(".cartao__valor {") : css.index(".cartao__valor--xm")]
        assert "font-family: var(--font-num)" in display
        assert "font-variant-numeric: tabular-nums" in display
        assert "clamp(32px, 6vw, 48px)" in display

    @pytest.mark.parametrize("arquivo", ["css", "html"])
    def test_a_pagina_nao_pede_UM_BYTE_a_rede(self, arquivo: str, css: str, html: str) -> None:
        """Nenhuma requisicao de rede alem das do proprio servidor.

        Tres formas, e nao uma: um `@import`, um `@font-face` com `src:` e uma
        URL absoluta em `url(...)` ou em `href`. A CSP `default-src 'none'`
        barraria as tres no navegador — mas barrar no navegador e descobrir
        tarde, e uma fonte que nao carrega vira uma tela sem tema sem ninguem
        entender por que.
        """
        texto = css if arquivo == "css" else html
        assert "://" not in texto
        assert "@import" not in texto
        assert "@font-face" not in texto

    def test_a_regra_de_MOVIMENTO_REDUZIDO_zera_pulso_e_transicao(
        self, css: str
    ) -> None:
        """Sem excecao — e um `0.01ms` "porque e praticamente nada" seria uma
        excecao disfarcada de numero."""
        gatilho = "@media (prefers-reduced-motion: reduce)"
        assert gatilho in css
        bloco = css[css.index(gatilho) :]
        bloco = bloco[: bloco.index("\n}\n", bloco.index("{"))]
        assert "animation: none" in bloco
        assert "transition: none" in bloco

    def test_o_CSS_INTEIRO_nao_escreve_o_nome_da_serie(self, css: str) -> None:
        """DASH-05: o componente de serie e generico.

        A busca e sobre o ARQUIVO INTEIRO e nao so sobre os seletores, e essa
        severidade e deliberada — e a letra do `01-UI-SPEC.md` ("a palavra nao
        aparece no CSS"). Um comentario que explica uma regra "para o caso da
        Adena" e o primeiro passo para um seletor que so serve para a Adena; a
        busca literal nao deixa o primeiro passo acontecer.

        Uma segunda serie instanciada usa os MESMOS seletores. A escolha da cor
        e de quem chama, e a paleta e do tema, nao do componente.
        """
        assert "adena" not in css.lower()


# ---------------------------------------------------------------------------
# O CONTRASTE, RECALCULADO
# ---------------------------------------------------------------------------
#
# ESTE BLOCO NAO REPETE AS RAZOES DO `01-UI-SPEC.md` — ele as REFAZ, a partir dos
# tokens que estao no CSS. E a diferenca entre uma tabela que envelhece em
# silencio e uma que falha quando alguem mexe numa cor. O contrato manda por
# extenso: "se o executor trocar um valor, a razao tem que ser recalculada, nao
# estimada no olho".

_TOKEN_DE_COR = re.compile(r"(--cor-[a-z-]+):\s*(#[0-9a-fA-F]{6})\s*;")


def _canal_linear(valor: int) -> float:
    """A linearizacao sRGB da WCAG 2.x, byte a byte."""
    proporcao = valor / 255.0
    if proporcao <= 0.04045:
        return proporcao / 12.92
    return ((proporcao + 0.055) / 1.055) ** 2.4


def _luminancia(hexadecimal: str) -> float:
    bruto = hexadecimal.lstrip("#")
    vermelho, verde, azul = (int(bruto[i : i + 2], 16) for i in (0, 2, 4))
    return (
        0.2126 * _canal_linear(vermelho)
        + 0.7152 * _canal_linear(verde)
        + 0.0722 * _canal_linear(azul)
    )


def razao_de_contraste(frente: str, fundo: str) -> float:
    """A razao da WCAG entre duas cores hexadecimais. FUNCAO PURA, de proposito.

    Ela nao le arquivo, nao conhece token e nao sabe desta tela: e so a formula.
    Quem a alimenta e o teste, com os valores lidos do bloco de tokens — e e
    essa separacao que faz "trocar uma cor refaz a conta" ser verdade.
    """
    clara, escura = sorted((_luminancia(frente), _luminancia(fundo)), reverse=True)
    return (clara + 0.05) / (escura + 0.05)


# OS PARES DA TABELA DO `01-UI-SPEC.md`, com o piso COBRADO e a medicao
# PUBLICADA. Os dois, e nao so o piso:
#
#   - o PISO e o que o par tem de cumprir para o texto ser legivel;
#   - a MEDICAO publicada e conferida junto para que um token trocado nao possa
#     baixar a razao ate a beira do piso sem ninguem notar. Passar raspando e um
#     resultado diferente de passar com folga, e a tabela do contrato afirma a
#     folga.
#
# SOBRE `texto-fraco` E `alerta`: a coluna "Piso" do contrato os rotula como
# `AAA (corpo)` e `AA+`, mas a aritmetica da WCAG e clara — AAA para texto de
# corpo exige 7:1, e 6,12 e 5,25 nao chegam la. As MEDICOES do contrato estao
# certas; os ROTULOS delas e que sao generosos. O que se cobra aqui e o numero,
# e o numero cumpre com folga o piso duro que o contrato escreve em prosa
# ("nenhum texto da tela fica abaixo de 4,5:1"). Registrar a divergencia e mais
# honesto que copiar o rotulo e fingir que 6,12 e AAA.
PARES_DE_CONTRASTE = (
    ("--cor-texto", "--cor-fundo", 7.0, 14.34),
    ("--cor-texto", "--cor-painel", 7.0, 13.16),
    ("--cor-serie-tipica", "--cor-painel", 7.0, 9.46),
    ("--cor-ouro", "--cor-painel", 7.0, 8.89),
    ("--cor-frio", "--cor-painel", 7.0, 7.80),
    ("--cor-texto-fraco", "--cor-painel", 4.5, 6.12),
    ("--cor-alerta", "--cor-painel", 4.5, 5.25),
    # O EXTREMO MAIS CLARO DO GRADIENTE DA PLACA. Medir so contra `--cor-painel`
    # deixaria de fora o topo do gradiente, que e o pior caso para um texto
    # claro — e o painel inteiro e gradiente, entao esse pior caso EXISTE na
    # tela. Aqui ele e cobrado.
    ("--cor-serie-tipica", "--cor-relevo-topo", 7.0, 9.03),
)


@pytest.fixture(scope="module")
def tokens(css: str) -> dict[str, str]:
    """As cores LIDAS do bloco de tokens do CSS — nunca repetidas aqui.

    Repetir os valores neste arquivo faria o teste conferir a si mesmo: trocar
    uma cor no CSS deixaria a suite verde sobre a paleta antiga.
    """
    achados = dict(_TOKEN_DE_COR.findall(_bloco_de_tokens(css)))
    assert achados, "o bloco de tokens deixou de declarar cor"
    return achados


class TestOContrasteFoiRecalculado:
    @pytest.mark.parametrize(
        ("frente", "fundo", "piso", "publicada"), PARES_DE_CONTRASTE
    )
    def test_o_par_cumpre_o_piso_do_contrato(
        self,
        frente: str,
        fundo: str,
        piso: float,
        publicada: float,
        tokens: dict[str, str],
    ) -> None:
        """LE os tokens do CSS e REFAZ a conta. Nao repete o numero da tabela.

        Trocar um token no `dashboard.css` faz este teste recalcular a razao — e
        falhar se o piso cair. E o oposto de uma tabela de contraste em Markdown,
        que continua verde para sempre porque ninguem a executa.
        """
        razao = razao_de_contraste(tokens[frente], tokens[fundo])
        assert razao >= piso, f"{frente} sobre {fundo}: {razao:.2f}"
        assert abs(razao - publicada) < 0.05, (
            f"{frente} sobre {fundo}: medido {razao:.2f}, "
            f"contrato publica {publicada:.2f}"
        )

    def test_NENHUM_par_da_tabela_fica_abaixo_de_quatro_e_meio(
        self, tokens: dict[str, str]
    ) -> None:
        """O piso duro que o contrato escreve em prosa, cobrado de uma vez.

        E o que "o tema nunca custa legibilidade" significa em numero, em vez de
        em promessa.
        """
        for frente, fundo, _, _ in PARES_DE_CONTRASTE:
            assert razao_de_contraste(tokens[frente], tokens[fundo]) >= 4.5

    def test_a_formula_de_contraste_conhece_os_DOIS_extremos(self) -> None:
        """O CONTROLE da formula, com os unicos dois valores que ela nao pode
        errar: branco sobre preto da 21, e uma cor sobre ela mesma da 1.

        Sem ele, uma formula quebrada que devolvesse sempre um numero grande
        aprovaria a tabela inteira.
        """
        assert abs(razao_de_contraste("#FFFFFF", "#000000") - 21.0) < 0.01
        assert abs(razao_de_contraste("#E0B450", "#E0B450") - 1.0) < 0.01


# ---------------------------------------------------------------------------
# OS ESTADOS DESENHADOS
# ---------------------------------------------------------------------------
#
# CADA ESTADO TEM DESENHO NO CSS, E O JS SO TROCA UM ATRIBUTO. Uma condicao de
# tela escrita em JavaScript e uma condicao que NAO aparece na folha de estilo,
# e as duas versoes da verdade divergem no primeiro ajuste — sem que nada quebre
# em voz alta. Estes testes cobram a ancora de cada estado no CSS.

# O seletor que ancora cada estado. Escrito por extenso e nao montado por
# `f-string`: o que se quer afirmar e que ESTE texto esta la, e uma montagem
# esconderia um erro de digitacao no proprio molde.
ESTADOS_DESENHADOS = {
    "estado vazio": 'body[data-estado="sem_leitura"]',
    "sem cambio informado": 'body[data-cambio="ausente"]',
    "dado velho": 'body[data-velho="sim"]',
    "servidor mudo": 'body[data-servidor="mudo"]',
    "primeira pintura": 'body[data-estado="primeira_pintura"]',
    "salvamento em curso": '#botao-salvar[data-salvando="sim"]',
}

# DE ONDE VEM A COPIA DE CADA ESTADO. As duas procedencias sao afirmadas de
# formas OPOSTAS, de proposito:
#
#   "marcacao" — a frase TEM de estar literal no HTML. E nossa, o Python nunca a
#                emite, e o CSS so alterna a visibilidade dela.
#   "servidor" — a frase NAO PODE estar no HTML. Ela vem pronta do Python, e uma
#                copia na marcacao seria a segunda fonte da mesma frase: as duas
#                divergiriam no primeiro ajuste de texto, e a tela passaria a
#                mostrar uma versao que o servidor ja abandonou.
COPIA_DE_CADA_ESTADO = {
    "estado vazio": ("marcacao", dashboard_dados.TITULO_DO_ESTADO_VAZIO),
    "sem cambio informado": ("marcacao", dashboard_dados.FRASE_DE_REAIS_INDISPONIVEL),
    "dado velho": ("servidor", "O valor abaixo é dessa leitura, não de agora."),
    "servidor mudo": ("marcacao", "Sem contato com o servidor local há"),
    "primeira pintura": ("marcacao", "Lendo o arquivo…"),
    "salvamento em curso": ("marcacao", "Salvando…"),
}


class TestOsEstadosTemDesenho:
    @pytest.mark.parametrize("estado", sorted(ESTADOS_DESENHADOS))
    def test_o_estado_tem_regra_ancorada_no_ATRIBUTO_de_estado(
        self, estado: str, css: str
    ) -> None:
        """Sem a ancora no CSS, o desenho do estado so pode estar no JS."""
        assert ESTADOS_DESENHADOS[estado] in css

    @pytest.mark.parametrize("estado", sorted(COPIA_DE_CADA_ESTADO))
    def test_a_copia_do_estado_esta_onde_declarado(
        self, estado: str, html: str
    ) -> None:
        procedencia, frase = COPIA_DE_CADA_ESTADO[estado]
        if procedencia == "marcacao":
            assert frase in html
        else:
            assert frase not in html

    def test_a_frase_de_dado_velho_e_MESMO_do_python(self) -> None:
        """A contraparte da assercao negativa acima.

        "Nao esta no HTML" sozinho ficaria verde se a frase nao existisse em
        lugar NENHUM. Esta linha prova que ela existe — no Python, que e onde
        ela deve estar.
        """
        _, frase = COPIA_DE_CADA_ESTADO["dado velho"]
        assert frase in dashboard_dados.MOLDE_DO_DADO_VELHO

    def test_o_body_nasce_com_os_QUATRO_atributos_de_estado(
        self, arvore: _Arvore
    ) -> None:
        """Um atributo ausente e um seletor que nunca casa — e um estado que
        nunca desenha. Eles nascem na marcacao com o valor mais conservador:
        ainda lendo, sem cambio, nao velho, servidor de pe."""
        corpo = arvore.de("body")
        assert len(corpo) == 1
        assert corpo[0]["data-estado"] == "primeira_pintura"
        assert corpo[0]["data-cambio"] == "ausente"
        assert corpo[0]["data-velho"] == "nao"
        assert corpo[0]["data-servidor"] == "ok"

    def test_o_cartao_de_reais_SAI_da_tela_sem_cambio_informado(
        self, arvore: _Arvore, css: str
    ) -> None:
        """Ele nao fica cinza e nao fica zerado: SOME.

        Um valor apagado ainda e um valor, e um zero e uma posicao no eixo. Duas
        assercoes, porque a regra depende das duas pontas: o cartao existe na
        marcacao E o CSS o retira sob o atributo de estado.
        """
        assert arvore.por_id("cartao-reais") is not None
        assert 'body[data-cambio="ausente"] #cartao-reais' in css
        assert 'body[data-cambio="ausente"] #cartao-xm' in css

    def test_a_regra_de_dado_velho_troca_a_COR_e_nao_esconde_o_numero(
        self, css: str
    ) -> None:
        """O que sai e a AFIRMACAO de agora, e nao o valor.

        Esconder o numero transformaria "nao posso garantir que e de agora" em
        "nao sei de nada" — uma perda de informacao que ninguem pediu, e o
        oposto do que o estado significa.
        """
        regras = _regras_ancoradas_em(css, 'body[data-velho="sim"]')
        assert any(
            ".cartao__recencia" in seletor and "var(--cor-frio)" in corpo
            for seletor, corpo in regras
        )
        # E o valor NUNCA e retirado por este estado.
        assert not any(
            ".cartao__valor" in seletor and "display: none" in corpo
            for seletor, corpo in regras
        )

    def test_o_botao_de_salvar_troca_de_ROTULO_sem_o_JS_escrever_texto(
        self, arvore: _Arvore, css: str
    ) -> None:
        """Os dois rotulos moram na marcacao; o CSS escolhe qual aparece.

        E o que mantem a copia de interface conferivel por teste sobre o HTML —
        um rotulo escrito pelo JS seria copia que nenhum teste desta suite ve.
        O botao NAO vira indicador giratorio.
        """
        botao = arvore.por_id("botao-salvar")
        assert botao is not None
        assert botao["data-salvando"] == "nao"
        assert '#botao-salvar[data-salvando="nao"] .botao__rotulo--salvando' in css
        assert '#botao-salvar[data-salvando="sim"] .botao__rotulo--parado' in css


def _regras_ancoradas_em(css: str, ancora: str) -> list[tuple[str, str]]:
    """(seletor, corpo) de toda regra cujo seletor contem a ancora."""
    achadas: list[tuple[str, str]] = []
    for bruto in css.split("}"):
        if "{" not in bruto:
            continue
        seletor, corpo = bruto.rsplit("{", 1)
        if ancora in seletor:
            achadas.append((seletor.strip(), corpo.strip()))
    return achadas


class TestOEstadoVazioEConteudo:
    """A PRIMEIRA TELA que o usuario vai ver — medido, e nao suposto.

    O CSV de campo tem 93 linhas e ZERO da serie vigiada. O estado vazio nao e
    um caso de borda desta fase: e o caso NORMAL dela, e por isso ele e provado
    estruturalmente em vez de ficar no "deve estar ok".
    """

    def test_a_placa_de_estado_vazio_esta_na_MARCACAO_mesmo_escondida(
        self, arvore: _Arvore, css: str
    ) -> None:
        """Ela NAO e criada pelo JS.

        Uma placa que so existe depois que o JS roda e uma placa que nao existe
        quando o JS falha — e o momento em que o JS falha e exatamente o momento
        em que o usuario mais precisa de uma tela que explique o que houve.
        """
        assert arvore.por_id("serie-vazio") is not None
        assert arvore.por_id("serie-vazio-prova") is not None
        # Escondida por padrao, e revelada pelo estado: as duas pontas.
        assert ".serie__vazio {" in css
        assert 'body[data-estado="sem_leitura"] .serie__vazio' in css

    def test_a_placa_carrega_TITULO_CORPO_e_o_lugar_da_linha_de_prova(
        self, html: str, arvore: _Arvore
    ) -> None:
        """A linha de prova e o que separa "nao ha o que mostrar" de "o
        dashboard nao conseguiu abrir o arquivo". Os numeros dela vem do
        servidor; o LUGAR dela e da marcacao."""
        assert dashboard_dados.TITULO_DO_ESTADO_VAZIO in html
        assert dashboard_dados.CORPO_DO_ESTADO_VAZIO in html
        assert arvore.tag_do_id("serie-vazio-prova") == "p"

    def test_o_molde_da_linha_de_prova_NAO_foi_copiado_para_a_marcacao(
        self, html: str
    ) -> None:
        """Os numeros sao reais e vem do endpoint. Uma copia do molde no HTML
        seria uma segunda frase de prova, capaz de divergir da primeira."""
        assert "O arquivo foi lido:" not in html

    def test_a_LEGENDA_das_duas_linhas_esta_na_marcacao(self, html: str) -> None:
        """Ja visivel no estado vazio, para o usuario saber o que vai aparecer.

        Sem ela, o quadro vazio nao diz nem o que ele MOSTRARIA — e a espera
        vira uma aposta.
        """
        assert dashboard_dados.ROTULO_DO_MENOR in html
        assert dashboard_dados.ROTULO_DA_TIPICA in html
        assert "serie__amostra--principal" in html
        assert "serie__amostra--tipica" in html

    def test_a_area_do_grafico_desenha_GRADE_no_estado_vazio(self, css: str) -> None:
        """GRAFICO VAZIO MUDO ESTA PROIBIDO.

        A grade e os eixos sao a prova de que a area existe e esta viva. Um
        retangulo em branco e indistinguivel de "o dashboard quebrou" — que e
        exatamente o erro que esta fase existe para nao cometer.
        """
        regras = _regras_ancoradas_em(css, 'body[data-estado="sem_leitura"]')
        do_grafico = [
            corpo for seletor, corpo in regras if ".serie__grafico" in seletor
        ]
        assert do_grafico, "o estado vazio deixou de desenhar a area do grafico"
        desenho = do_grafico[0]
        assert "var(--cor-grade)" in desenho
        assert "repeating-linear-gradient" in desenho
        assert "border-left" in desenho and "border-bottom" in desenho

    def test_a_legenda_fica_VISIVEL_no_estado_vazio(self, css: str) -> None:
        """Em cor de texto fraco, e nao escondida: o contrato pede que ela ja
        esteja la. Nenhuma regra do estado vazio a retira."""
        regras = _regras_ancoradas_em(css, 'body[data-estado="sem_leitura"]')
        assert not any(
            "legenda" in seletor and "display: none" in corpo
            for seletor, corpo in regras
        )
        assert any(
            "serie__legenda-rotulo" in seletor and "var(--cor-texto-fraco)" in corpo
            for seletor, corpo in regras
        )
