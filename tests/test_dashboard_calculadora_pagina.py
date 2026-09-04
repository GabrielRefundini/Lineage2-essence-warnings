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

import pytest

from l2scanner import dashboard_dados
from tests.test_dashboard_rotas_tracer import (  # noqa: F401
    ARQUIVO_DO_CSS,
    ARQUIVO_DO_HTML,
    ARQUIVO_DO_JS,
    ID_DA_REGIAO,
    ID_DO_INSTANTE,
    ID_DO_MOLDE,
    _Arvore,
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
