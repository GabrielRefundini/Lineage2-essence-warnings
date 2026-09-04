"""A quarta regiao NA TELA: a marcacao, o tema dos seis estados, e a pintura.

O QUE ESTE ARQUIVO PRENDE, EM UMA FRASE
========================================
Que o veredito que o payload ja sabia responder vira uma coisa que uma pessoa
consegue CONFERIR com o dedo na tela — as duas rotas sempre visiveis com a
vencedora marcada, a procedencia do preco do NPC declarada sem carimbo
inventado, e a diferenca em R$ sumindo sozinha pelo mesmo atributo que ja retira
o cartao de R$ do destaque.

DE ONDE VEM A FORMA MINIMA DAS SONDAS DE CSS, E POR QUE ELA NAO FOI COPIADA
===========================================================================
As tres sondas de CSS deste arquivo — a que afirma que nenhuma regra esconde o
lado perdedor, a que afirma que a marca de vencedora tem regra, e a que afirma
que a quarta regiao nao ganhou regra propria de falha fechada — **nasceram no
plano 02-01**, como funcoes de modulo em `tests/test_dashboard_rotas_tracer.py`,
escritas de proposito para serem ESTENDIDAS aqui.

Elas sao IMPORTADAS, e nao reimplementadas. Duas copias da mesma invariante e o
defeito que este paragrafo existe para impedir: elas divergem na primeira
correcao, uma das duas fica verde por engano, e a mais fraca e a que a proxima
pessoa com pressa apaga achando que esta removendo duplicacao. Um criterio que
apenas verificasse "as duas passam" NAO pegaria isso — duas copias divergentes
tambem passam, ate o dia em que uma para de passar sozinha.

ESTE ARQUIVO NAO LEVA LETRA ACENTUADA, como o resto de `tests/`. As frases
acentuadas de que ele precisa sao IMPORTADAS do Python que as define, ou
montadas por escape — copiar uma frase acentuada para ca seria a segunda copia
que o DASH-03 recusa.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from l2scanner import dashboard_dados, dashboard_rotas
from tests.test_dashboard_rotas_tracer import (  # noqa: F401
    ARQUIVO_DO_CSS,
    ARQUIVO_DO_HTML,
    ARQUIVO_DO_JS,
    ID_DA_REGIAO,
    ID_DO_INSTANTE,
    ID_DO_MOLDE,
    _Arvore,
    regras_do_css,
    sonda_da_falha_fechada,
    sonda_da_marca_da_vencedora,
    sonda_do_lado_perdedor_escondido,
)

# As letras acentuadas de que as sondas precisam, montadas por escape para o
# arquivo continuar sem letra acentuada no fonte.
_E_CIRCUNFLEXO = "\u00ea"
VOCE = "voc" + _E_CIRCUNFLEXO

ID_DA_LEGENDA_DA_MEDIANA = "rotas-mediana-legenda"
CLASSE_DA_PROCEDENCIA_DO_NPC = "rota__procedencia-npc"
ARQUIVO_DE_CONFIGURACAO = "config.toml"

# Os vaos das TRES partes da diferenca. Cada um no proprio elemento: um vao
# unico obrigaria o navegador a COMPOR a frase, e compor no navegador e o
# segundo formatador que o DASH-03 proibe.
VAOS_DA_DIFERENCA = ("diferenca-xm", "diferenca-percentual", "diferenca-reais")


@pytest.fixture(scope="module")
def html() -> str:
    return ARQUIVO_DO_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css() -> str:
    return ARQUIVO_DO_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def js() -> str:
    return ARQUIVO_DO_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def arvore(html: str) -> _Arvore:
    analisador = _Arvore()
    analisador.feed(html)
    return analisador


# ===========================================================================
# AS SONDAS SOBRE A MARCACAO
# ===========================================================================


def sem_comentario(marcacao: str) -> str:
    """A marcacao sem os comentarios de HTML.

    O QUE ESTA LIMPEZA E, E POR QUE ELA E OBRIGATORIA: comentario nao chega a
    tela. O `index.html` desta regiao EXPLICA em prosa varias coisas que ele nao
    faz — inclusive por que nao ha data escrita a mao aqui. Uma sonda que punisse
    o arquivo por NOMEAR o defeito que ele evita ensinaria a apagar a
    explicacao, que e o oposto do que este projeto quer.
    """
    return re.sub(r"<!--.*?-->", "", marcacao, flags=re.DOTALL)


def molde_da_linha(html: str) -> str:
    """So o `<template>` da linha, comentarios fora."""
    inicio = html.index('id="' + ID_DO_MOLDE + '"')
    fim = html.index("</template>", inicio)
    return sem_comentario(html[inicio:fim])


def sonda_da_procedencia_do_npc(html: str) -> list[str]:
    """As linhas do molde que declaram o preco do NPC como INFORMADO POR VOCE.

    Vazio = o numero do NPC aparece na tela sem dizer de onde veio, e o CALC-02
    nao esta na tela.
    """
    achados = []
    for linha in molde_da_linha(html).splitlines():
        if VOCE in linha or CLASSE_DA_PROCEDENCIA_DO_NPC in linha:
            achados.append(linha.strip())
    return achados


# O molde de uma data escrita a mao. As tres formas que o projeto usa: a curta
# do `_recencia_em_duas_formas` (`03/09 20:14`), a ISO, e a hora solta.
_DATA_ESCRITA_A_MAO = re.compile(r"\d{2}/\d{2}|\d{4}-\d{2}-\d{2}|\b\d{1,2}:\d{2}\b")


def sonda_de_data_escrita_a_mao(marcacao: str) -> list[str]:
    """Toda data que a MARCACAO carrega por conta propria.

    Tem de sair VAZIA. O instante da leitura e um fato do programa e chega pelo
    payload, num vao; uma data no HTML seria um numero que nao responde a
    ninguem e que envelheceria calada.
    """
    return _DATA_ESCRITA_A_MAO.findall(sem_comentario(marcacao))


def vaos_de(marcacao: str) -> list[str]:
    """Os nomes de `data-vao` presentes, na ordem do documento."""
    return re.findall(r'data-vao="([^"]+)"', sem_comentario(marcacao))


# ===========================================================================
# TAREFA 1 — A MARCACAO DA LINHA
# ===========================================================================


class TestAProcedenciaDoPrecoDoNPC:
    """O CALC-02 na tela: o numero do NPC nao foi medido por ninguem."""

    def test_a_linha_de_procedencia_existe_DENTRO_do_molde(self, html: str):
        achados = sonda_da_procedencia_do_npc(html)
        assert achados, (
            "o molde da linha nao declara de onde vem o preco do NPC; o numero "
            "apareceria na tela com cara de medido"
        )

    def test_CONTROLE_a_sonda_ACUSA_um_molde_SEM_a_linha(self):
        """Sem o controle, a busca passaria sobre qualquer arquivo que contivesse
        a palavra por acaso — inclusive fora do molde."""
        mentira = (
            '<template id="' + ID_DO_MOLDE + '">'
            '<li class="rota"><p class="rota__valor" data-vao="npc-valor"></p></li>'
            "</template>"
        )
        assert sonda_da_procedencia_do_npc(mentira) == []

    def test_CONTROLE_a_sonda_NAO_se_satisfaz_com_a_frase_num_COMENTARIO(self):
        """A segunda metade do controle, e ela e a que quase passou.

        Um comentario dizendo "informado por voce" nao chega a tela. Se a sonda
        o aceitasse, apagar o elemento e deixar a prosa manteria o teste verde.
        """
        mentira = (
            '<template id="' + ID_DO_MOLDE + '">'
            "<!-- o preco e informado por " + VOCE + " -->"
            '<li class="rota"></li>'
            "</template>"
        )
        assert sonda_da_procedencia_do_npc(mentira) == []

    def test_ela_NOMEIA_o_arquivo_de_configuracao(self, html: str):
        """De onde o numero veio, com o nome do arquivo."""
        assert ARQUIVO_DE_CONFIGURACAO in " ".join(
            sonda_da_procedencia_do_npc(html)
        )

    def test_ela_diz_INFORMADO_POR_VOCE_e_nunca_MEDIDO(self, html: str):
        assert "informado por " + VOCE in molde_da_linha(html)


class TestNenhumaDataMoraNaMARCACAO:
    def test_o_molde_da_linha_NAO_carrega_data_escrita_a_mao(self, html: str):
        """O instante da leitura chega pelo payload, num vao — ele nao mora aqui.

        Uma data no HTML seria plausivel e falsa ao mesmo tempo: ela nao
        responderia a leitura nenhuma e envelheceria calada.
        """
        assert sonda_de_data_escrita_a_mao(molde_da_linha(html)) == []

    def test_CONTROLE_a_sonda_de_data_ACUSA_um_molde_que_traz_uma(self):
        mentira = '<p class="rota__procedencia-npc">informado em 03/09 20:14</p>'
        assert sonda_de_data_escrita_a_mao(mentira) == ["03/09", "20:14"]


class TestOParDeProcedenciaNaoCOLAPSA:
    """Dois fatos com nomes parecidos, e trocar um pelo outro e mentir com cara
    de numero — a mesma armadilha que `recencia_do_preco` ja documenta."""

    def test_o_texto_do_instante_fala_em_LEITURA_e_nao_em_INFORME(self):
        """A assercao e por substring contra a CONSTANTE do Python, importada.

        Uma copia da frase escrita aqui mediria a copia, e continuaria verde no
        dia em que o Python passasse a dizer outra coisa.
        """
        molde = dashboard_dados.MOLDE_DA_LEITURA_DA_CONFIGURACAO
        assert "lidos do" in molde
        assert "informado" not in molde.lower()
        assert "informou" not in molde.lower()

    def test_o_vao_do_instante_esta_em_NIVEL_DE_REGIAO(self, arvore: _Arvore):
        """A primeira metade. Sozinha ela passaria tambem sobre um vao
        DUPLICADO dentro da linha."""
        achado = arvore.por_id(ID_DO_INSTANTE)
        assert achado is not None
        _, _, ancestrais = achado
        assert any(a.endswith("#" + ID_DA_REGIAO) for a in ancestrais)
        assert not any("template" in a for a in ancestrais)

    def test_o_vao_do_instante_esta_AUSENTE_do_molde_da_linha(self, html: str):
        """A segunda metade, e ela e a que esta tarefa poderia ter quebrado.

        Mexer na procedencia e a ocasiao exata para alguem migrar o instante
        para dentro da linha "porque e procedencia tambem". Repetido por item, a
        mesma frase sairia N vezes e criaria a impressao falsa de que cada item
        foi lido num instante proprio.
        """
        assert ID_DO_INSTANTE not in molde_da_linha(html)

    def test_as_DUAS_metades_do_par_sao_textos_DISTINTOS(self, html: str):
        """O rotulo por linha existe na linha, e ele nao e o texto do instante.

        Se os dois colapsassem num so, ou a linha passaria a afirmar um instante
        que nao e dela, ou o bloco perderia o unico sinal de que a configuracao
        nao foi relida.
        """
        molde = molde_da_linha(html)
        assert "informado por " + VOCE in molde
        assert "lidos do" not in molde


class TestOVereditoTemOsTRESPedacosDaDiferenca:
    def test_cada_parte_da_diferenca_tem_o_PROPRIO_vao(self, html: str):
        """Tres vaos e nao um.

        Um vao unico obrigaria o navegador a compor a frase juntando as tres
        partes — o segundo formatador que o DASH-03 proibe.
        """
        vaos = vaos_de(molde_da_linha(html))
        for vao in VAOS_DA_DIFERENCA:
            assert vao in vaos, (vao, vaos)

    def test_CONTROLE_a_sonda_dos_vaos_ACUSA_um_vao_UNICO(self):
        """Sem o controle, `in` sobre uma lista qualquer nao provaria nada."""
        mentira = '<p class="rota__diferenca" data-vao="diferenca"></p>'
        vaos = vaos_de(mentira)
        assert vaos == ["diferenca"]
        assert not [vao for vao in VAOS_DA_DIFERENCA if vao in vaos]

    def test_o_vao_da_MEDIANA_de_contexto_existe_na_linha(self, html: str):
        vaos = vaos_de(molde_da_linha(html))
        assert "mediana" in vaos
        assert "mediana-n" in vaos

    def test_NENHUM_vao_do_molde_esta_REPETIDO(self, html: str):
        """Dois elementos com o mesmo `data-vao` fariam o `querySelector`
        escrever so no primeiro e deixar o outro mudo."""
        vaos = vaos_de(molde_da_linha(html))
        assert len(vaos) == len(set(vaos)), sorted(vaos)


class TestALegendaDizQueAMedianaEhContexto:
    def test_a_legenda_da_regiao_existe(self, arvore: _Arvore):
        assert arvore.por_id(ID_DA_LEGENDA_DA_MEDIANA) is not None

    def test_ela_esta_em_NIVEL_DE_REGIAO_e_FORA_do_molde(self, arvore: _Arvore):
        """O usuario tem de saber o que aquele numero e ANTES de ele aparecer —
        a mesma funcao da legenda das duas linhas na regiao do grafico."""
        _, _, ancestrais = arvore.por_id(ID_DA_LEGENDA_DA_MEDIANA)
        assert any(a.endswith("#" + ID_DA_REGIAO) for a in ancestrais)
        assert not any("template" in a for a in ancestrais)

    def test_ela_diz_que_a_mediana_NAO_decide(self, html: str):
        """Um numero sem rotulo ao lado de um veredito sobre dinheiro e lido
        como parte do veredito."""
        inicio = html.index('id="' + ID_DA_LEGENDA_DA_MEDIANA + '"')
        texto = sem_comentario(html[inicio : html.index("</p>", inicio)])
        assert "contexto" in texto.lower()
        assert "veredito" in texto.lower()


# ===========================================================================
# TAREFA 2 — O TEMA DOS SEIS ESTADOS, E A ROTA PERDEDORA QUE NAO PODE SUMIR
# ===========================================================================
#
# O CONJUNTO DE RECONHECIMENTO, ENUMERADO. Uma regra de CSS aposenta um elemento
# por MUITOS caminhos, e um controle unico so estabelece discriminacao para o
# caminho que ele usa. As sete formas que a sonda reconhece:
#
#   1. `display: none`         — retira da caixa
#   2. `visibility: hidden`    — esconde, mantendo o espaco
#   3. `opacity: 0`            — invisivel, ainda ocupando lugar
#   4. `width`/`height` zerada — colapsa a caixa
#   5. `content-visibility: hidden` — o navegador pula a pintura
#   6. `clip-path` recortando a nada — `inset(100%)`, `circle(0)`
#   7. posicionamento que joga o elemento para fora da tela — `left: -9999px`
#
# O CONJUNTO MORA EM `_SOME_DA_TELA`, no arquivo do tracer, e e UM SO. Ele nao e
# copiado para ca; as sondas sao IMPORTADAS. Aqui ficam os CONTROLES — um por
# forma, e cada um tem de ser ACUSADO.
A_FRONTEIRA_DESTA_VARREDURA = (
    "regra escrita dentro de uma consulta de midia: a varredura nao interpreta "
    "`@media`, entao uma regra que esconda o lado perdedor so numa largura de "
    "tela passa por ela sem ser vista",
    "classe aplicada por OUTRO seletor: a sonda le o texto do CSS, e quem "
    "resolve `.rota__lado.oculto` e o navegador, com uma classe que so existe "
    "em tempo de execucao",
    "valor vindo de propriedade personalizada de nome opaco: `display: "
    "var(--modo-do-lado)` nao diz o que faz, e o valor mora em outro lugar",
)


class TestAFronteiraDestaVarreduraEstaDECLARADA:
    """Uma reserva de verificacao que nao esta escrita nao existe.

    E a mesma disciplina do cabecalho de `PRIMITIVAS` em
    `tests/test_firewall_dashboard.py`, que declara ser uma varredura LITERAL e
    nomeia o que escapa dela. Sem isto, o verde daqui e lido como prova de mais
    do que ele mede.
    """

    def test_a_fronteira_nomeia_TRES_formas_que_a_sonda_NAO_pega(self):
        assert len(A_FRONTEIRA_DESTA_VARREDURA) == 3
        assert all(limite.strip() for limite in A_FRONTEIRA_DESTA_VARREDURA)

    def test_o_conjunto_de_reconhecimento_tem_SETE_formas(self):
        """Eram TRES no 02-01. Se alguem apagar uma forma, este numero cai."""
        from tests.test_dashboard_rotas_tracer import _SOME_DA_TELA

        assert len(_SOME_DA_TELA) == 7


# Uma folha de MENTIRA por forma. Cada uma esconde o lado perdedor por um
# caminho diferente, e a sonda tem de ACUSAR as sete.
_ALVO = '.rota[data-vencedora="npc"] .rota__lado--mercado'
MENTIRAS_POR_FORMA = {
    "display": _ALVO + " { display: none; }",
    "visibility": _ALVO + " { visibility: hidden; }",
    "opacity": _ALVO + " { opacity: 0; }",
    "largura-zero": _ALVO + " { width: 0; }",
    "altura-zero": _ALVO + " { height: 0px; }",
    "content-visibility": _ALVO + " { content-visibility: hidden; }",
    "clip-path": _ALVO + " { clip-path: inset(100%); }",
    "fora-da-tela": _ALVO + " { position: absolute; left: -9999px; }",
}


class TestAsDuasRotasFicamSEMPREVisiveis:
    """Esconder a perdedora impede conferir a conta, e esta conta e sobre
    dinheiro real — decisao travada do `02-CONTEXT`."""

    def test_NENHUMA_regra_do_css_real_esconde_o_lado_perdedor(self, css: str):
        assert sonda_do_lado_perdedor_escondido(css) == []

    @pytest.mark.parametrize("forma", sorted(MENTIRAS_POR_FORMA))
    def test_CONTROLE_a_sonda_ACUSA_a_folha_de_mentira_de_CADA_forma(
        self, forma: str
    ):
        """UM CONTROLE POR FORMA, e nao um controle unico.

        Um controle so estabelece discriminacao para o caminho que ele usa: com
        apenas o de `display`, uma regra que zerasse a largura do lado perdedor
        passaria pela sonda e pelo teste, e o numero sumiria da tela com a suite
        verde.
        """
        assert sonda_do_lado_perdedor_escondido(MENTIRAS_POR_FORMA[forma]) == [
            _ALVO
        ], forma

    def test_CONTROLE_a_sonda_NAO_acusa_a_regra_que_MANTEM_os_dois_lados(self):
        """O outro sentido, e ele quase caiu.

        `.rota__lado` usa `min-width: 0` para poder encolher — sem o lookbehind
        do conjunto de reconhecimento, a sonda leria isso como "largura zero" e
        acusaria justamente a regra que mantem os dois lados na tela. Uma sonda
        que acusa tudo nao discrimina nada.
        """
        honesta = ".rota__lado { display: flex; flex: 1 1 0; min-width: 0; }"
        assert sonda_do_lado_perdedor_escondido(honesta) == []


class TestAMarcaDaVencedoraNaoEhSoCOR:
    def test_existe_regra_ligando_o_ATRIBUTO_de_vencedora_a_marca(self, css: str):
        assert sonda_da_marca_da_vencedora(css)

    def test_a_marca_NASCE_ESCONDIDA_e_o_atributo_a_MOSTRA(self, css: str):
        """As DUAS metades do mecanismo, e a primeira e a que quase faltou.

        A PRIMEIRA VERSAO DESTE TESTE CAIU NUMA PROVA DE MUTACAO, E O REGISTRO
        FICA AQUI. Ela perguntava "existe alguma regra que fale de
        `rota__marca` e declare uma propriedade que nao seja de cor?". Isso e
        VERDADE mesmo numa folha quebrada: a regra do atributo declara
        `display: block`, entao a busca a encontrava e passava. Medido: com a
        regra base reduzida a `.rota__marca { margin: 0; color: ... }` — ou
        seja, com a marca "mais barato" VISIVEL NOS DOIS LADOS ao mesmo tempo —
        a suite inteira ficava VERDE (52 passed).

        O que este teste mede agora e o MECANISMO: a marca nasce fora da tela, e
        e o atributo da linha que a traz. Esse e o canal que nao e cor — e por
        isso ele sobrevive a daltonismo, a monitor mal calibrado e ao gama do
        cliente, que e o mesmo argumento que o UI-SPEC ja fez para as duas
        linhas do grafico. A cor dourada e reforco.
        """
        assert self._regras_que_escondem_a_marca(css), (
            "a marca da vencedora nao nasce escondida: ela apareceria nos DOIS "
            "lados, e a linha marcaria as duas rotas como mais baratas"
        )
        assert sonda_da_marca_da_vencedora(css), (
            "nenhuma regra liga o atributo de vencedora a exibicao da marca"
        )

    @staticmethod
    def _regras_que_escondem_a_marca(css: str) -> list[str]:
        """A regra BASE da marca — a que nao depende do atributo de vencedora.

        O conjunto de reconhecimento e o mesmo `_SOME_DA_TELA` das outras
        sondas: uma autoridade so sobre o que "sumiu da tela" quer dizer.
        """
        from tests.test_dashboard_rotas_tracer import _SOME_DA_TELA

        return [
            seletor
            for seletor, corpo in regras_do_css(css)
            if "rota__marca" in seletor
            and "data-vencedora" not in seletor
            and any(sonda.search(corpo) for sonda in _SOME_DA_TELA)
        ]

    def test_CONTROLE_ACUSA_a_folha_em_que_a_marca_esta_SEMPRE_visivel(self):
        """A folha exata da mutacao que derrubou a versao anterior deste teste."""
        mentira = (
            ".rota__marca { margin: 0; color: var(--cor-ouro); }\n"
            '.rota[data-vencedora="npc"] .rota__lado--npc .rota__marca '
            "{ display: block; }\n"
        )
        assert self._regras_que_escondem_a_marca(mentira) == []
        # E a outra metade continua verde na mentira — que e precisamente por
        # que ela sozinha nao provava nada.
        assert sonda_da_marca_da_vencedora(mentira)

    def test_CONTROLE_ACUSA_a_folha_em_que_a_marca_NUNCA_aparece(self):
        """O outro sentido: escondida e nunca revelada."""
        mentira = ".rota__marca { display: none; }"
        assert self._regras_que_escondem_a_marca(mentira)
        assert sonda_da_marca_da_vencedora(mentira) == []


class TestAQuartaRegiaoNaoCompeteComAPrecedenciaDaFase1:
    def test_a_lista_de_seletores_de_falha_fechada_esta_INALTERADA(
        self, css: str
    ):
        """Ela some pelas duas regras de `.painel` que JA existiam.

        Uma regra propria para a quarta regiao seria uma segunda verdade sobre
        um fato que ja tem uma — e as duas divergiriam no primeiro ajuste.
        """
        seletores = sonda_da_falha_fechada(css)
        assert seletores == [
            'body[data-estado="erro_de_contrato"] .painel, '
            'body[data-estado="arquivo_ausente"] .painel'
        ]
        assert ID_DA_REGIAO not in " ".join(seletores)

    def test_CONTROLE_a_sonda_ACUSA_uma_regra_NOVA_de_falha_fechada(self):
        mentira = (
            'body[data-estado="erro_de_contrato"] .painel { display: none; }\n'
            'body[data-estado="arquivo_ausente"] #rotas { display: none; }\n'
        )
        assert len(sonda_da_falha_fechada(mentira)) == 2


# O seletor de atributo, com o OPERADOR — e nao so o valor.
#
# POR QUE O OPERADOR IMPORTA AQUI: um dos seis estados nao pode ser escrito por
# extenso no `dashboard.css`. O token dele CONTEM o nome da serie sentinela, e o
# DASH-05 proibe esse nome de aparecer naquele arquivo em qualquer lugar,
# comentario inclusive — ha duas sondas na suite cobrando isso, e elas ACUSARAM
# a primeira versao desta fase. A saida foi casar por PREFIXO no CSS, com a
# colisao escrita ao lado da regra.
#
# ENTAO ESTE TESTE NAO PODE SER UMA BUSCA LITERAL: ele PERGUNTA se existe regra
# que se APLICA aquele estado, que e a coisa que a truth afirma. Uma busca por
# `data-estado="<valor>"` reprovaria uma folha correta, e o conserto obvio seria
# afrouxar a proibicao do DASH-05 — trocar um guarda por outro.
_SELETOR_DE_ESTADO = re.compile(
    r"data-estado\s*(=|\^=|\*=|\$=)\s*\"([^\"]*)\""
)


def estados_cobertos_por(css: str, estados) -> dict:
    """Para cada estado, os seletores de LINHA cujo casamento o inclui."""
    cobertura = {estado: [] for estado in estados}
    for seletor, _ in regras_do_css(css):
        if ".rota[" not in seletor:
            continue
        for operador, valor in _SELETOR_DE_ESTADO.findall(seletor):
            for estado in estados:
                casa = (
                    estado == valor
                    if operador == "="
                    else estado.startswith(valor)
                    if operador == "^="
                    else valor in estado
                    if operador == "*="
                    else estado.endswith(valor)
                )
                if casa:
                    cobertura[estado].append(seletor)
    return cobertura


class TestOsSEISEstadosTemDesenho:
    def test_cada_estado_da_lista_do_PYTHON_tem_ao_menos_uma_regra(
        self, css: str
    ):
        """A lista dos seis vem do modulo Python, IMPORTADA.

        Copia-la para dentro do teste faria um setimo estado novo — que ninguem
        desenhasse — passar despercebido, porque a copia nao cresceria junto.
        """
        cobertura = estados_cobertos_por(css, dashboard_rotas.ESTADOS_DA_ROTA)
        sem_regra = [estado for estado, regras in cobertura.items() if not regras]
        assert sem_regra == [], sem_regra

    def test_a_lista_do_python_tem_mesmo_SEIS(self):
        """A metade que impede o teste acima de passar por vacuidade: com a
        tupla vazia, `sem_regra` sairia vazio sobre qualquer folha."""
        assert len(dashboard_rotas.ESTADOS_DA_ROTA) == 6

    def test_o_casamento_por_PREFIXO_cobre_UM_estado_so(self, css: str):
        """O custo do seletor por prefixo, MEDIDO em vez de suposto.

        Ele designa hoje um unico estado. No dia em que dois estados comecarem
        com as mesmas palavras, um deles herdaria o desenho do outro em silencio
        — e este teste fica vermelho antes disso chegar a tela.
        """
        por_prefixo = [
            seletor
            for seletor, _ in regras_do_css(css)
            if ".rota[" in seletor and 'data-estado^="' in seletor
        ]
        for seletor in por_prefixo:
            (valor,) = re.findall(r"data-estado\^=\"([^\"]*)\"", seletor)
            casados = [
                estado
                for estado in dashboard_rotas.ESTADOS_DA_ROTA
                if estado.startswith(valor)
            ]
            assert len(casados) == 1, (seletor, casados)

    def test_CONTROLE_a_busca_ACUSA_uma_folha_que_desenha_so_UM_estado(self):
        so_um = '.rota[data-estado="decidida"] .rota__diferenca { color: red; }'
        cobertura = estados_cobertos_por(so_um, dashboard_rotas.ESTADOS_DA_ROTA)
        sem_regra = [estado for estado, regras in cobertura.items() if not regras]
        assert len(sem_regra) == 5

    def test_CONTROLE_o_casador_NAO_confunde_um_prefixo_com_uma_igualdade(self):
        """Sem esta metade, um casador que devolvesse SEMPRE tudo passaria nos
        dois testes acima."""
        estados = ("decidida", "e a propria coisa")
        exato = '.rota[data-estado="e a propria"] .rota__item { color: red; }'
        assert estados_cobertos_por(exato, estados)["e a propria coisa"] == []

        prefixo = '.rota[data-estado^="e a propria"] .rota__item { color: red; }'
        assert estados_cobertos_por(prefixo, estados)["e a propria coisa"]
        assert estados_cobertos_por(prefixo, estados)["decidida"] == []


class TestOReaisSomePeloMESMOSeletorDoCartao:
    def test_os_dois_estao_no_MESMO_agrupamento_de_seletores(self, css: str):
        """A prova e que os dois aparecem na MESMA regra.

        Um teste que so verificasse "existe alguma regra escondendo a linha"
        passaria sobre um mecanismo paralelo — e dois mecanismos para a mesma
        ausencia divergem no primeiro ajuste, com o cartao sumindo la em cima e a
        linha ficando aqui embaixo, sobre o MESMO cambio que nao existe.
        """
        juntos = [
            seletor
            for seletor, corpo in regras_do_css(css)
            if "#cartao-reais" in seletor
            and "rota__diferenca-reais" in seletor
            and "display" in corpo
        ]
        assert juntos, (
            "a linha de R$ da diferenca nao esta no mesmo agrupamento de "
            "seletores que o cartao de R$ do destaque"
        )

    def test_o_seletor_de_estado_dos_dois_e_o_MESMO_ortogonal(self, css: str):
        (seletor,) = [
            seletor
            for seletor, corpo in regras_do_css(css)
            if "#cartao-reais" in seletor and "rota__diferenca-reais" in seletor
        ]
        assert seletor.count('body[data-cambio="ausente"]') == 2

    def test_CONTROLE_a_busca_ACUSA_um_mecanismo_PARALELO(self):
        """Duas regras separadas, cada uma escondendo um dos dois: e o defeito
        que este par de testes existe para pegar, e ele passaria num teste que so
        perguntasse "a linha some?"."""
        mentira = (
            'body[data-cambio="ausente"] #cartao-reais { display: none; }\n'
            ".rota__diferenca-reais:empty { display: none; }\n"
        )
        juntos = [
            seletor
            for seletor, _ in regras_do_css(mentira)
            if "#cartao-reais" in seletor and "rota__diferenca-reais" in seletor
        ]
        assert juntos == []


class TestNenhumHexadecimalNovoEntrou:
    def test_a_contagem_de_literais_de_cor_FORA_dos_tokens_continua_ZERO(
        self, css: str
    ):
        """O valor de antes deste plano: ZERO fora do bloco de tokens, e 14
        dentro dele.

        A medicao e sobre os CORPOS das regras, e nao sobre o texto cru — assim
        um identificador como `#cartao-reais` no seletor nunca e lido como cor.
        """
        fora = []
        for seletor, corpo in regras_do_css(css):
            if seletor.strip() == ":root":
                continue
            fora.extend(re.findall(r"#[0-9A-Fa-f]{3,8}\b", corpo))
        assert fora == [], fora

    def test_o_bloco_de_tokens_continua_com_os_MESMOS_14_hexadecimais(
        self, css: str
    ):
        """A outra metade: sem ela, apagar o bloco de tokens inteiro deixaria o
        teste acima verde."""
        dentro = [
            achado
            for seletor, corpo in regras_do_css(css)
            if seletor.strip() == ":root"
            for achado in re.findall(r"#[0-9A-Fa-f]{3,8}\b", corpo)
        ]
        assert len(dentro) == 14, dentro


class TestUmaAutoridadeSoSobreCadaInvarianteDeCSS:
    """Duas copias divergentes tambem passam — ate o dia em que uma para de
    passar sozinha, e alguem apaga a que incomoda.

    Por isso o criterio aqui NAO e "as duas sondas passam", e sim "existe UMA
    definicao de cada sonda na suite inteira, e os dois arquivos a chamam".
    """

    NOMES = (
        "sonda_do_lado_perdedor_escondido",
        "sonda_da_marca_da_vencedora",
        "sonda_da_falha_fechada",
    )

    @staticmethod
    def _fontes():
        pasta = Path(__file__).parent
        return {
            arquivo.name: arquivo.read_text(encoding="utf-8")
            for arquivo in sorted(pasta.glob("test_*.py"))
        }

    @pytest.mark.parametrize("nome", NOMES)
    def test_o_CORPO_de_cada_sonda_aparece_UMA_VEZ_na_suite_inteira(
        self, nome: str
    ):
        definicoes = {
            arquivo: len(
                re.findall(r"^def " + nome + r"\(", fonte, flags=re.MULTILINE)
            )
            for arquivo, fonte in self._fontes().items()
        }
        assert sum(definicoes.values()) == 1, definicoes

    @pytest.mark.parametrize("nome", NOMES)
    def test_os_DOIS_arquivos_de_teste_CHAMAM_a_mesma_sonda(self, nome: str):
        chamam = {
            arquivo
            for arquivo, fonte in self._fontes().items()
            if re.search(r"(?<!def )" + nome + r"\(", fonte)
        }
        assert "test_dashboard_rotas_tracer.py" in chamam, chamam
        assert "test_dashboard_calculadora_pagina.py" in chamam, chamam

    def test_CONTROLE_a_contagem_de_definicoes_ACUSA_uma_SEGUNDA_copia(self):
        """Sem o controle, a contagem passaria tambem sobre uma expressao que
        nunca casasse com nada."""
        fabricado = (
            "def sonda_do_lado_perdedor_escondido(css):\n"
            "    return []\n"
            "def sonda_do_lado_perdedor_escondido(css):\n"
            "    return []\n"
        )
        achados = re.findall(
            r"^def sonda_do_lado_perdedor_escondido\(",
            fabricado,
            flags=re.MULTILINE,
        )
        assert len(achados) == 2
