"""O `dashboard.js`, julgado como TEXTO — e o contrato de que ele depende.

POR QUE LER O FONTE, E O QUE ISSO NAO PROVA
============================================
Nao ha navegador nesta arvore, e a casa recusou instalador pesado de automacao
de navegador por doutrina. Entao o que da para afirmar sobre o JS e a forma dele:
que a chamada proibida nao existe, que a chamada obrigatoria existe, que a
refutacao esta escrita ao lado do codigo que ela justifica. A casa ja usa leitura
de fonte como tripwire de arquitetura em `test_dashboard_leitura.py` (o fonte que
abre arquivo nao pode conter modo de escrita) e em
`test_mercado_firewall_de_fase.py`.

A FRONTEIRA, DITA POR EXTENSO: estas assercoes caem se a implementacao estiver
vazia, se o evento errado for registrado ou se a API errada for chamada. Elas
NAO distinguem um zoom por roda que funciona de um registrador que faz a coisa
errada. Nenhuma assercao de fonte consegue. O criterio de zoom do ROADMAP repousa
no `<human-check>` do plano, e isso e verificacao humana DECLARADA, e nao
cobertura automatica disfarcada.

TODA SONDA DE AUSENCIA TEM CONTROLE
====================================
Um `assert x == []` que nunca poderia ser diferente e um guarda cuja saida nao
muda com o fato que ele julga — o padrao de defeito que
`test_mercado_firewall_de_fase.py:449-470` nomeia. Aqui, cada sonda de ausencia
vem com um controle que a faz ACUSAR um exemplo de verdade.

ESTE ARQUIVO E ASCII, como o resto de `tests/`. As frases acentuadas de que ele
precisa sao IMPORTADAS do Python que as define — copiar uma frase para ca seria a
segunda copia que o DASH-03 recusa, e ela envelheceria na primeira correcao de
virgula do outro lado.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from l2scanner import dashboard, dashboard_dados, mercado_registro
from l2scanner.mercado_analise import (
    N_MINIMO_PARA_MEDIANA,
    N_MINIMO_PARA_MENOR,
    N_MINIMO_PARA_TENDENCIA,
)
from l2scanner.mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA, SEPARADOR

# ---------------------------------------------------------------------------
# OS ARQUIVOS SOB JULGAMENTO
# ---------------------------------------------------------------------------

ARQUIVO_DO_JS = dashboard.PASTA_DOS_ESTATICOS / "dashboard.js"
ARQUIVO_DO_CSS = dashboard.PASTA_DOS_ESTATICOS / "dashboard.css"
ARQUIVO_DO_HTML = dashboard.PASTA_DOS_ESTATICOS / "index.html"

TERMINADOR = "\r\n"
AGORA = datetime(2026, 9, 1, 15, 0, 0)


@pytest.fixture(scope="module")
def js() -> str:
    return ARQUIVO_DO_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css() -> str:
    return ARQUIVO_DO_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def html() -> str:
    return ARQUIVO_DO_HTML.read_text(encoding="utf-8")


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    alvo = tmp_path / ".mercado"
    alvo.mkdir()
    return alvo


# ---------------------------------------------------------------------------
# O CSV DE FIXTURE, ESCRITO A MAO
# ---------------------------------------------------------------------------
#
# A MAO E NAO PELO ESCRITOR, no mesmo molde de `test_dashboard_dados.py`:
# construir o arquivo com o `RegistroDeObservacoes` faria estes testes
# dependerem do escritor para julgar o que o leitor produz.


def _linha(carimbo: datetime, total: int = 11600) -> str:
    return SEPARADOR.join(
        (
            CHAVE_DA_SERIE_DA_ADENA,
            "Adena",
            carimbo.isoformat(),
            str(total),
            str(10_000_000),
            "0",
        )
    )


def _escrever_cru(pasta: Path, texto: str) -> Path:
    """`newline=""` obrigatorio: sem ele o Windows traduziria o `\\r\\n`."""
    alvo = pasta / mercado_registro.ARQUIVO_DE_OBSERVACOES
    alvo.write_text(texto, encoding="utf-8", newline="")
    return alvo


def _cabecalho() -> str:
    return SEPARADOR.join(mercado_registro.COLUNAS) + TERMINADOR


def _avisos(pasta: Path, corpo: str) -> list[str]:
    _escrever_cru(pasta, _cabecalho() + corpo)
    return dashboard_dados.payload(pasta, AGORA)["avisos"]


# ---------------------------------------------------------------------------
# AS SONDAS
# ---------------------------------------------------------------------------
#
# Cada uma nomeia UMA familia de defeito, e cada uma tem um exemplo de controle
# ao lado, para que o teste que a usa possa provar que ela morde.

SONDAS_DE_SEGUNDO_FORMATADOR = (
    re.compile(r"\btoFixed\b"),
    re.compile(r"\btoLocaleString\b"),
    re.compile(r"\btoLocaleDateString\b"),
    re.compile(r"\btoPrecision\b"),
    re.compile(r"\bIntl\s*\."),
    re.compile(r"\.replace\s*\("),
)

CONTROLE_DO_SEGUNDO_FORMATADOR = (
    'escrever("xm-texto", Number(dados.destaque.xm.pixel).toFixed(2)'
    '.replace(".", ",") + " XM por 5 milhoes");'
)

SONDAS_DE_MARCACAO = (
    re.compile(r"\binnerHTML\b"),
    re.compile(r"\bouterHTML\b"),
    re.compile(r"\binsertAdjacentHTML\b"),
    re.compile(r"\bdocument\s*\.\s*write\b"),
)

CONTROLE_DA_MARCACAO = 'alvo.innerHTML = "<b>" + serie.titulo + "</b>";'

# A COMPARACAO DE UMA CONTAGEM COM UM PISO — a forma que o estado recalculado no
# cliente teria. Duas formas, porque as duas aparecem na vida real: a contagem
# como propriedade (`ponto.n`) e como variavel solta (`n`).
SONDAS_DE_PISO_RECALCULADO = (
    re.compile(r"\.\s*n\s*(?:<=|>=|<|>)"),
    re.compile(r"\bn\b\s*(?:<=|>=|<|>)\s*\d"),
)

CONTROLE_DO_PISO_RECALCULADO = "if (ponto.n < 5) { escrever(alvo, semEvidencia); }"


def _acusacoes(sondas, texto: str) -> list[str]:
    achados: list[str] = []
    for sonda in sondas:
        achados.extend(sonda.findall(texto))
    return achados


_COMENTARIO_EM_BLOCO = re.compile(r"/\*.*?\*/", re.DOTALL)

# A REGIAO DO COMPONENTE DE SERIE, marcada no proprio fonte.
#
# As sentinelas existem para que a assercao "o componente le EXATAMENTE estas
# propriedades" tenha uma fronteira DECIDIVEL. Sem elas, o teste teria de
# adivinhar onde o componente comeca, e adivinhacao num guarda e o comeco de um
# guarda que nao guarda nada.
ABERTURA_DA_REGIAO = "// <<< COMPONENTE-DE-SERIE"
FECHAMENTO_DA_REGIAO = "// >>> COMPONENTE-DE-SERIE"

# O CONTRATO DE PROPRIEDADES, e as duas divergencias do `01-UI-SPEC.md` estao
# escritas no `dashboard.js`, ao lado da regiao:
#   - `formatador` nao chega porque ele ja foi APLICADO no Python (o texto de
#     cada ponto chega pronto); recebe-lo aqui exigiria reimplementa-lo em JS,
#     que e o segundo formatador que o DASH-03 recusa;
#   - `baldes` chega a mais porque a agregacao do zoom largo e mediana inferior
#     sobre fracao exata, e isso so existe no Python.
PROPRIEDADES_DO_CONTRATO = {
    "titulo",
    "unidade",
    "pontos",
    "baldes",
    "rotulo_principal",
    "rotulo_tipico",
}

# A MESMA EXPRESSAO QUE `test_dashboard_tracer.py` e `test_dashboard_pagina.py`
# ja usam. Mante-la igual nos tres e deliberado: uma paleta clandestina tem a
# mesma forma nos tres arquivos, e tres expressoes diferentes divergiriam na
# primeira correcao.
CACA_HEXADECIMAL = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def _regiao_do_componente(js: str) -> str:
    inicio = js.index(ABERTURA_DA_REGIAO) + len(ABERTURA_DA_REGIAO)
    return js[inicio : js.index(FECHAMENTO_DA_REGIAO)]


def _corpo_da_funcao(js: str, nome: str) -> str:
    """O corpo de uma funcao de topo, ate a chave que fecha na coluna zero.

    So e correto porque este arquivo declara toda funcao na coluna zero e a
    fecha na coluna zero — e ha teste logo abaixo prendendo que o nome pedido
    existe, para que um erro de digitacao nao devolva um corpo vazio que passe
    calado em toda assercao de ausencia.
    """
    marca = "function " + nome + "("
    inicio = js.index(marca)
    fim = js.index("\n}\n", inicio)
    return js[inicio:fim]


def _so_o_codigo(js: str) -> str:
    """O JS sem os comentarios. MEDIDO, E E POR ISSO QUE ESTA FUNCAO EXISTE.

    A primeira versao destas sondas rodava sobre o arquivo inteiro e ACUSOU o
    proprio `dashboard.js` quatro vezes — todas dentro de comentarios que
    explicam por que o defeito NAO esta ali: o paragrafo que diz que o piso do
    menor e o da mediana moram no Python (`n >= 1`, `n >= 5`) e o que diz que
    nao existe indicador giratorio nesta tela.

    Uma sonda que pune o arquivo por NOMEAR o defeito que ele evita ensina a
    apagar a explicacao, e a explicacao e metade do valor do arquivo. Entao as
    sondas de CODIGO leem so o codigo; as de PROSA (a refutacao no topo) leem o
    texto inteiro, de proposito.

    O removedor e deliberadamente simples: linha cujo conteudo comeca com `//`,
    mais blocos `/* */`. Ele so e correto porque o `dashboard.js` nao tem
    comentario no fim de linha de codigo nem barra dupla dentro de string — e
    ha teste logo abaixo prendendo as duas coisas, para que ele nao vire
    silenciosamente errado.
    """
    sem_bloco = _COMENTARIO_EM_BLOCO.sub("", js)
    return "\n".join(
        linha for linha in sem_bloco.splitlines() if not linha.strip().startswith("//")
    )


# ===========================================================================
# O JS NAO E UM SEGUNDO FORMATADOR
# ===========================================================================


class TestOJSNaoEUmSegundoFormatador:
    """A regra mais facil de quebrar sem perceber desta fase inteira.

    Toda a disciplina do console de mercado atravessa a fronteira HTTP como
    string. Um `toFixed(2)` no navegador nao quebra nada no dia em que nasce:
    ele quebra meses depois, quando alguem mexer no formatador do Python e
    ninguem perceber que havia dois.
    """

    def test_nenhuma_reformatacao_de_numero_ou_de_texto_vinda_do_payload(
        self, js: str
    ) -> None:
        assert _acusacoes(SONDAS_DE_SEGUNDO_FORMATADOR, _so_o_codigo(js)) == []

    def test_CONTROLE_as_sondas_ACUSAM_um_segundo_formatador_de_verdade(self) -> None:
        """Sem esta linha, um erro de digitacao numa das expressoes deixaria o
        guarda verde para sempre sobre um JS cheio de `toFixed`."""
        acusacoes = _acusacoes(
            SONDAS_DE_SEGUNDO_FORMATADOR, CONTROLE_DO_SEGUNDO_FORMATADOR
        )
        assert len(acusacoes) >= 2

    def test_o_paragrafo_de_refutacao_esta_no_TOPO_do_arquivo(self, js: str) -> None:
        """A razao mora ao lado do codigo, e nao so no documento de plano.

        Conferido pelas palavras que NOMEIAM a regra, e nao pela frase inteira:
        cobrar a frase literal transformaria qualquer melhoria de redacao em
        falha de teste, e o que importa e que o proximo leitor encontre o nome
        do defeito (`SEGUNDO FORMATADOR`) e o requisito que o proibe.
        """
        topo = "\n".join(js.splitlines()[:60])
        assert "SEGUNDO FORMATADOR" in topo
        assert "DASH-03" in topo

        # A divergencia de acentuacao e INTENCIONAL, e isso tambem esta escrito:
        # sem essa linha, o proximo leitor "conserta" o acento e cria o segundo
        # formatador achando que esta arrumando um defeito.
        assert "INTENCIONAL" in topo


# ===========================================================================
# O JS INSERE TEXTO, E NUNCA MARCACAO
# ===========================================================================


class TestOJSInsereTEXTOeNaoMARCACAO:
    """T-01-22: o `nome_exibido` de uma serie atravessa o OCR sobre a tela do
    jogo, e o resto vem de um CSV que o usuario edita a mao. E conteudo NAO
    CONFIAVEL terminando dentro da pagina."""

    def test_a_contagem_de_atribuicoes_a_propriedade_de_MARCACAO_e_zero(
        self, js: str
    ) -> None:
        assert _acusacoes(SONDAS_DE_MARCACAO, _so_o_codigo(js)) == []

    def test_CONTROLE_as_sondas_ACUSAM_uma_insercao_de_marcacao_de_verdade(
        self,
    ) -> None:
        assert _acusacoes(SONDAS_DE_MARCACAO, CONTROLE_DA_MARCACAO) != []

    def test_o_removedor_de_comentarios_CONTINUA_correto(self, js: str) -> None:
        """A premissa de `_so_o_codigo`, presa antes de ela virar falsa.

        O removedor apaga a linha inteira quando ela COMECA com barra dupla. Se
        alguem escrever um comentario no fim de uma linha de codigo, ou uma
        barra dupla dentro de uma string, o removedor passa a apagar de menos ou
        a mentir — e todas as sondas de codigo passariam a julgar um texto que
        nao e o codigo. Melhor descobrir aqui do que num falso verde.
        """
        for numero, linha in enumerate(js.splitlines(), start=1):
            posicao = linha.find("//")
            if posicao == -1:
                continue
            assert linha[:posicao].strip() == "", (
                f"linha {numero} tem codigo antes da barra dupla; "
                f"`_so_o_codigo` deixaria de ser correto"
            )

    def test_o_texto_do_servidor_entra_por_propriedade_de_TEXTO(self, js: str) -> None:
        """O guarda contra vacuidade do teste acima.

        Um `dashboard.js` VAZIO passaria com louvor na contagem zero de
        marcacao. Esta linha exige que exista, de fato, escrita de texto.
        """
        assert len(re.findall(r"\btextContent\b", _so_o_codigo(js))) >= 1


# ===========================================================================
# O POLLING OBEDECE O INTERVALO DO SERVIDOR
# ===========================================================================


class TestOPollingObedeceOIntervaloDoSERVIDOR:
    def test_o_numero_do_servidor_NAO_aparece_como_literal_no_js(self, js: str) -> None:
        """Um intervalo escrito em dois lugares nao fica errado nos dois: fica
        errado em UM, e a pagina passa a consultar numa frequencia que o
        servidor nao conhece — o modo de falha que ninguem percebe."""
        literal = re.compile(r"\b" + str(dashboard.INTERVALO_DE_POLLING_MS) + r"\b")
        assert literal.findall(_so_o_codigo(js)) == []

        # CONTROLE: a mesma expressao acha o numero onde ele mora de verdade.
        assert literal.findall(str(dashboard.INTERVALO_DE_POLLING_MS))

    def test_o_js_LE_a_chave_do_intervalo_que_vem_no_payload(self, js: str) -> None:
        """Se o servidor mudar a cadencia, o navegador acompanha sozinho."""
        assert "intervalo_de_polling_ms" in js

        # E A CHAVE EXISTE MESMO NO QUE O SERVIDOR SERVE — conferido sobre o
        # payload REAL, e nao sobre uma string copiada para ca. Sem esta linha, o
        # teste acima ficaria verde sobre uma chave que o Python nunca manda, e o
        # navegador leria `undefined` como intervalo.
        pasta = ARQUIVO_DO_JS.parent  # qualquer pasta serve: o arquivo esta ausente
        servido = dashboard.CacheDaLeitura().pronto(pasta, AGORA)
        assert servido["intervalo_de_polling_ms"] == dashboard.INTERVALO_DE_POLLING_MS

    def test_o_polling_NAO_reintroduz_o_estado_de_carregamento(self, js: str) -> None:
        """Polling nao e carregamento.

        O estado de primeira pintura nasce na MARCACAO, com o rotulo de leitura
        em curso no lugar do numero. Se o JS soubesse escrever esse valor de
        atributo, ele poderia repo-lo a cada volta — e a tela piscaria entre
        "tenho um numero" e "estou lendo" para sempre. Nao saber escreve-lo e a
        garantia estrutural de que isso nao acontece.
        """
        assert "primeira_pintura" not in _so_o_codigo(js)
        assert "primeira_pintura" in ARQUIVO_DO_HTML.read_text(encoding="utf-8")

    def test_nao_existe_indicador_giratorio_em_lugar_nenhum(self, js: str) -> None:
        """Girar um indicador a cada dois segundos ao lado do jogo e ruido."""
        codigo = _so_o_codigo(js).lower()
        for palavra in ("spinner", "girat", "loading"):
            assert palavra not in codigo


# ===========================================================================
# O ESTADO E LIDO, E NUNCA RECALCULADO
# ===========================================================================


class TestOEstadoEhLIDOeNaoRECALCULADO:
    """A precedencia fechada dos cinco estados mora no `dashboard_dados`, e os
    pisos de evidencia moram no `mercado_analise`. Duas autoridades sobre a
    mesma pergunta divergem na primeira vez que alguem mexer numa delas."""

    def test_nenhuma_comparacao_de_contagem_com_um_piso_dentro_do_js(
        self, js: str
    ) -> None:
        assert _acusacoes(SONDAS_DE_PISO_RECALCULADO, _so_o_codigo(js)) == []

    def test_CONTROLE_a_sonda_ACUSA_uma_comparacao_de_verdade(self) -> None:
        assert _acusacoes(SONDAS_DE_PISO_RECALCULADO, CONTROLE_DO_PISO_RECALCULADO) != []

    def test_nenhum_dos_tres_pisos_aparece_como_comparacao_no_js(self, js: str) -> None:
        """A forma menos obvia do mesmo defeito: o piso escrito como numero solto.

        Os tres valores sao IMPORTADOS de onde eles moram, e nao copiados: se um
        piso mudar la, esta sonda passa a procurar o valor novo sozinha.
        """
        for piso in (
            N_MINIMO_PARA_MENOR,
            N_MINIMO_PARA_MEDIANA,
            N_MINIMO_PARA_TENDENCIA,
        ):
            sonda = re.compile(r"(?:<=|>=|<|>)\s*" + str(piso) + r"\b")
            assert sonda.findall(_so_o_codigo(js)) == [], (
                f"piso {piso} comparado dentro do JS"
            )


# ===========================================================================
# A ORDEM DOS AVISOS E O CONTRATO DE QUE O JS DEPENDE
# ===========================================================================


class TestAOrdemDosAvisosEhOCONTRATO:
    """`avisos` e uma lista de strings SEM ROTULO, e o JS acha cada frase por
    POSICAO.

    Isto e acoplamento, e ele esta escrito no `dashboard.js` em vez de
    escondido. Achar cada frase pelo TEXTO exigiria copiar as frases do Python
    para dentro do JS — a segunda copia que o DASH-03 recusa. O conserto certo e
    `avisos` virar um objeto com uma chave por lugar da tela, o que exige mexer
    no `dashboard_dados.py`, fora do alcance deste plano.

    ENTAO A ORDEM VIRA CONTRATO, E CONTRATO SE PRENDE COM TESTE. Estas quatro
    assercoes rodam sobre payloads REAIS, montados a partir de arquivos reais em
    `tmp_path`. Se alguem reordenar os avisos no Python, elas ficam vermelhas — e
    e assim que o JS descobre, em vez de passar a escrever a frase errada no
    lugar errado calado.
    """

    def test_a_nota_de_linha_parcial_e_o_PRIMEIRO_aviso(self, pasta: Path) -> None:
        # Cabecalho + uma linha COMPLETA e velha + uma cauda cortada no meio.
        corpo = _linha(AGORA - timedelta(hours=3)) + TERMINADOR + "adena" + SEPARADOR
        avisos = _avisos(pasta, corpo)

        assert avisos[0] == dashboard_dados.NOTA_DE_LINHA_PARCIAL

    def test_o_bloco_do_estado_vazio_tem_TRES_avisos_e_a_prova_e_o_TERCEIRO(
        self, pasta: Path
    ) -> None:
        """O estado vazio e a PRIMEIRA tela que o usuario vai ver, e nao uma
        borda: medido, o CSV de campo tem zero linhas da serie vigiada."""
        corpo = "adena" + SEPARADOR  # so uma cauda cortada: nenhum registro
        avisos = _avisos(pasta, corpo)

        assert avisos[0] == dashboard_dados.NOTA_DE_LINHA_PARCIAL
        assert avisos[1] == dashboard_dados.TITULO_DO_ESTADO_VAZIO
        assert avisos[2] == dashboard_dados.CORPO_DO_ESTADO_VAZIO
        assert avisos[3].startswith("O arquivo foi lido:")

    def test_o_aviso_de_dado_velho_vem_LOGO_DEPOIS_da_nota_de_linha_parcial(
        self, pasta: Path
    ) -> None:
        """Sem cauda cortada, o dado velho e o primeiro; com ela, o segundo.

        O estado vazio e o dado velho sao MUTUAMENTE EXCLUSIVOS — sem nenhuma
        leitura da serie nao existe recencia para envelhecer —, e e por isso que
        o contador do JS pode somar os dois blocos sem nunca ve-los juntos.
        """
        velho = _linha(AGORA - timedelta(hours=3))

        sem_cauda = _avisos(pasta, velho + TERMINADOR)
        assert sem_cauda[0].startswith("Sem leitura nova")

        com_cauda = _avisos(pasta, velho + TERMINADOR + "adena" + SEPARADOR)
        assert com_cauda[0] == dashboard_dados.NOTA_DE_LINHA_PARCIAL
        assert com_cauda[1].startswith("Sem leitura nova")

    def test_a_linha_de_reais_e_SEMPRE_o_ultimo_aviso(self, pasta: Path) -> None:
        """E por isso que o JS nao a le: as duas frases ja nascem na marcacao, e
        o CSS escolhe qual aparece pelo atributo de cambio."""
        casos = (
            "adena" + SEPARADOR,
            _linha(AGORA - timedelta(hours=3)) + TERMINADOR,
            _linha(AGORA - timedelta(minutes=1)) + TERMINADOR,
        )
        for corpo in casos:
            avisos = _avisos(pasta, corpo)
            assert avisos[-1] == dashboard_dados.FRASE_DE_REAIS_INDISPONIVEL

    def test_a_recencia_fresca_NAO_produz_aviso_de_dado_velho(
        self, pasta: Path
    ) -> None:
        """O controle da assercao de ordem acima.

        Sem ele, `avisos[0]` poderia ser a frase de dado velho por acidente — se
        ela fosse acrescentada SEMPRE — e o contador do JS estaria certo pelo
        motivo errado.
        """
        avisos = _avisos(pasta, _linha(AGORA - timedelta(minutes=1)) + TERMINADOR)

        assert len(avisos) == 1
        assert avisos[0] == dashboard_dados.FRASE_DE_REAIS_INDISPONIVEL


# ===========================================================================
# O COMPONENTE DE SERIE E GENERICO (DASH-05)
# ===========================================================================


class TestOComponenteDeSerieEGenerico:
    def test_a_palavra_que_nomeia_a_serie_NAO_esta_no_js_nem_no_css(
        self, js: str, css: str, pasta: Path
    ) -> None:
        """As DUAS metades, e a segunda e a que torna a primeira uma prova.

        Afirmar so a ausencia deixaria o teste verde num projeto onde a palavra
        nao existe em lugar nenhum — genericidade provada pelo motivo errado. A
        segunda assercao mostra que a palavra existe, viva, no que o servidor
        manda: entao a ausencia no JS e no CSS e uma propriedade do DESENHO.
        """
        palavra = CHAVE_DA_SERIE_DA_ADENA.rstrip("#")

        assert palavra not in js.lower()
        assert palavra not in css.lower()

        _escrever_cru(pasta, _cabecalho() + _linha(AGORA) + TERMINADOR)
        servido = json.dumps(dashboard_dados.payload(pasta, AGORA), ensure_ascii=False)
        assert palavra in servido.lower()

    def test_a_contagem_de_hexadecimais_de_cor_no_js_e_zero(self, js: str) -> None:
        assert CACA_HEXADECIMAL.findall(js) == []

        # O CONTROLE NEGATIVO: a mesma expressao, no mesmo diretorio, ACHA
        # hexadecimais no CSS — que e onde a paleta mora.
        assert CACA_HEXADECIMAL.findall(ARQUIVO_DO_CSS.read_text(encoding="utf-8"))

    def test_a_cor_e_PEDIDA_ao_css_por_nome_de_token(self, js: str) -> None:
        """Uma cor sem nome de token e uma cor que o grafico nao consegue pedir.

        Quatro e o piso porque sao quatro os papeis que a configuracao do
        grafico precisa colorir: a linha principal, a da mediana, a grade e o
        rotulo dos eixos.
        """
        leituras = re.findall(r"getPropertyValue\(\s*\"(--[a-z-]+)\"", js)
        assert len(leituras) >= 4
        assert len(set(leituras)) == len(leituras), "o mesmo token pedido duas vezes"

        # E cada token pedido EXISTE no CSS. Um token com erro de digitacao
        # devolve cadeia vazia, e a linha sairia sem cor nenhuma — calada.
        css = ARQUIVO_DO_CSS.read_text(encoding="utf-8")
        for token in leituras:
            assert token + ":" in css, f"o JS pede {token}, que o CSS nao declara"

    def test_a_funcao_de_serie_usa_EXATAMENTE_as_propriedades_do_contrato(
        self, js: str
    ) -> None:
        """Nem uma a menos, nem uma a mais.

        Uma propriedade A MAIS e o componente sabendo algo sobre a serie que o
        contrato nao prometeu — e e assim que um componente generico vira um
        componente de uma serie so, sem ninguem decidir isso.
        """
        regiao = _so_o_codigo(_regiao_do_componente(js))
        lidas = set(re.findall(r"\bserie\.([a-z_]+)", regiao))

        assert lidas == PROPRIEDADES_DO_CONTRATO

    def test_as_duas_linhas_diferem_em_TRACO_alem_de_diferir_em_COR(
        self, js: str
    ) -> None:
        """Traco sobrevive a daltonismo, a monitor mal calibrado e ao gama do
        cliente. Cor sozinha nao sobreviveria a nenhum dos tres."""
        regiao = _so_o_codigo(_regiao_do_componente(js))

        # UMA das duas linhas e tracejada, e exatamente uma: duas tracejadas nao
        # se distinguem, e nenhuma tracejada volta a depender so da cor.
        assert len(re.findall(r"\bdash\s*:", regiao)) == 1

        # E as duas cores continuam diferentes — o traco SOMA a cor, nao a
        # substitui.
        tracos = re.findall(r"stroke\s*:\s*paleta\.(\w+)", regiao)
        assert "principal" in tracos
        assert "tipica" in tracos

    def test_a_dica_sob_o_cursor_vem_das_chaves_de_TEXTO(self, js: str) -> None:
        """O numero no payload e o PIXEL; a string e a VERDADE.

        O `float` existe porque o canvas so aceita numero de JS, e o erro dele
        foi medido (pior caso 1,9e-11). Ele posiciona uma linha; ele nao e para
        ser lido.
        """
        corpo = _so_o_codigo(_corpo_da_funcao(js, "conjuntoCru"))
        assert "textos:" in corpo

        bloco_dos_textos = corpo[corpo.index("textos:") :]
        assert "_texto" in bloco_dos_textos
        assert "_pixel" not in bloco_dos_textos, (
            "a dica esta sendo montada a partir do numero, e nao da string"
        )

        # CONTROLE: o bloco dos DADOS — o que vira pixel — de fato usa os
        # numericos. Sem esta linha, a assercao acima ficaria verde sobre uma
        # funcao que nao usa `_pixel` em lugar nenhum.
        assert "_pixel" in corpo[: corpo.index("textos:")]

    def test_o_botao_de_alcance_total_chama_o_metodo_de_ESCALA(self, js: str) -> None:
        """Sem ele o usuario fica preso no zoom que ele mesmo deu."""
        corpo = _corpo_da_funcao(js, "verTodoOPeriodo")
        assert re.search(r"setScale\(\s*\"x\"", corpo) is not None

        # E o botao da marcacao esta LIGADO a essa funcao.
        assert re.search(
            r"\"ver-todo-o-periodo\"[\s\S]{0,200}addEventListener\(\s*\"click\","
            r"\s*verTodoOPeriodo",
            js,
        ) is not None

    def test_o_grafico_NAO_e_recriado_a_cada_volta_do_polling(self, js: str) -> None:
        """O defeito que nenhum teste de conteudo veria.

        Recriar a instancia a cada resposta jogaria fora, de dois em dois
        segundos, o zoom que o usuario acabou de dar. Ele nao quebra nada, nao
        levanta erro, e aparece so na primeira vez que alguem tenta olhar uma
        tarde especifica.
        """
        corpo = _so_o_codigo(_corpo_da_funcao(js, "desenharUmaSerie"))

        # A instancia so nasce quando nao existe...
        assert "grafico === null" in corpo
        # ...e o caminho de atualizacao entrega dados SEM redefinir a escala.
        assert re.search(r"setData\([^)]*,\s*false\s*\)", corpo) is not None

    def test_o_vao_da_mediana_ausente_e_VAO_e_nunca_zero(self, js: str) -> None:
        """A ausencia da mediana e o caminho NORMAL desta tela, e nao uma borda.

        O payload manda `null` — nunca `0.0` —, e a biblioteca precisa ser
        instruida a NAO ligar os dois lados do vao com uma reta: ligar
        desenharia uma variacao que ninguem observou.
        """
        regiao = _so_o_codigo(_regiao_do_componente(js))
        assert len(re.findall(r"spanGaps\s*:\s*false", regiao)) == 2


# ===========================================================================
# O ZOOM E DE NOS, E O FONTE DIZ POR QUE
# ===========================================================================


class TestOZoomEDeNosEDizPorQue:
    """A biblioteca escolhida NAO faz zoom por roda, e isso foi medido.

    A FRONTEIRA DESTAS ASSERCOES, DITA POR EXTENSO: elas caem se a
    implementacao estiver vazia, se o evento errado for registrado, se ele for
    pendurado no elemento errado ou se a API de escala nao for chamada. Elas NAO
    distinguem um zoom que funciona de um registrador que faz a coisa errada —
    nenhuma assercao sobre texto consegue. O criterio de zoom do ROADMAP repousa
    no roteiro de verificacao humana do plano.
    """

    def test_a_roda_e_registrada_sobre_a_SOBREPOSICAO_do_grafico(self, js: str) -> None:
        corpo = _so_o_codigo(_corpo_da_funcao(js, "ligarOZoomEODeslocamento"))

        # O ouvinte mora na sobreposicao da biblioteca, e nao no contorno da
        # area: e ela que cobre a regiao desenhada e conhece a conversao de
        # pixel para valor.
        assert re.search(r"=\s*instancia\.over\b", corpo) is not None
        assert re.search(r'addEventListener\(\s*"wheel"', corpo) is not None

    def test_a_roda_chama_o_metodo_de_definicao_de_ESCALA(self, js: str) -> None:
        corpo = _so_o_codigo(_corpo_da_funcao(js, "ligarOZoomEODeslocamento"))

        assert re.search(r'setScale\(\s*"x"', corpo) is not None
        # E em torno do CURSOR: sem converter a posicao do ponteiro em valor, o
        # zoom so poderia ser centrado, que e outro comportamento.
        assert "posToVal" in corpo

    def test_o_pedido_de_nao_rolar_a_pagina_e_REGISTRADO_como_nao_passivo(
        self, js: str
    ) -> None:
        """A armadilha silenciosa deste bloco.

        Um ouvinte de roda registrado sem esta opcao e tratado como passivo em
        varios contextos, e ai o `preventDefault` e descartado SEM AVISO: o
        grafico aproximaria e a pagina desceria junto.
        """
        corpo = _so_o_codigo(_corpo_da_funcao(js, "ligarOZoomEODeslocamento"))

        assert "preventDefault" in corpo
        assert re.search(r"passive\s*:\s*false", corpo) is not None

    def test_o_bloco_de_refutacao_traz_a_MEDICAO_e_nao_so_a_conclusao(
        self, js: str
    ) -> None:
        """"A biblioteca nao faz" e uma conclusao; ela envelhece sem deixar
        rastro.

        O que nao envelhece e a contagem e a citacao: quem for atualizar a
        biblioteca um dia pode REFAZER a medicao e comparar. Uma refutacao sem o
        numero obriga o proximo leitor a acreditar; com o numero, ele pode
        conferir.
        """
        # A contagem, para as DUAS candidatas que nao registram o evento.
        assert len(re.findall(r"ZERO `wheel`", js)) == 2
        # E a que registra, para a contagem nao ser vacua.
        assert "2x `wheel`" in js
        # A citacao textual da documentacao oficial.
        assert "No built-in drag scrolling/panning" in js
        # E o motivo de a candidata que trazia o evento pronto ter sido recusada
        # mesmo assim — sem isso, a refutacao parece um argumento a favor dela.
        assert "REGULAR" in js

    def test_o_arrasto_simples_continua_sendo_o_zoom_por_SELECAO_nativo(
        self, js: str
    ) -> None:
        """A colisao de gestos, resolvida e escrita.

        O arrasto com o botao principal ja e o zoom por selecao da biblioteca, e
        o plano manda nao reescreve-lo. Entao o deslocamento tem de morar em
        outro gesto — e o manipulador precisa SAIR quando o gesto nao e o dele.
        """
        corpo = _so_o_codigo(_corpo_da_funcao(js, "ligarOZoomEODeslocamento"))

        assert re.search(r'addEventListener\(\s*"mousedown"', corpo) is not None
        assert "shiftKey" in corpo
        assert "BOTAO_DO_MEIO" in corpo
        assert re.search(r"if\s*\(\s*!\s*querDeslocar\s*\)", corpo) is not None

    def test_o_arrasto_solta_pelo_DOCUMENTO_e_nao_pelo_grafico(self, js: str) -> None:
        """Quem arrasta rapido tira o ponteiro do grafico no meio do gesto.

        Um ouvinte preso ao elemento perderia o `mouseup` e a janela ficaria
        grudada no ponteiro — um defeito que so aparece com a mao apressada.
        """
        corpo = _so_o_codigo(_corpo_da_funcao(js, "ligarOZoomEODeslocamento"))

        assert re.search(r'document\.addEventListener\(\s*"mouseup"', corpo) is not None
        assert re.search(r'document\.removeEventListener\(\s*"mouseup"', corpo) is not None


# ===========================================================================
# O ENVIO DO CAMBIO E INTERCEPTADO
# ===========================================================================


class TestOEnvioDoCambioEInterceptado:
    def test_o_manipulador_de_envio_IMPEDE_o_comportamento_padrao(
        self, js: str, html: str
    ) -> None:
        """Sem isto, a diretiva de destino de formulario bloquearia o envio em
        silencio.

        O formulario da marcacao nao tem destino, e a diretiva servida em toda
        resposta proibe qualquer um. A tecla de confirmacao dispararia um envio
        nativo que o navegador barra, e nada apareceria na tela — so um erro no
        console.
        """
        corpo = _so_o_codigo(_corpo_da_funcao(js, "ligarOFormularioDoCambio"))

        assert re.search(r'addEventListener\(\s*"submit"', corpo) is not None
        assert "preventDefault" in corpo

        # E a outra metade da colisao continua verdadeira na marcacao: o
        # formulario NAO tem destino. Sem esta linha, alguem "consertaria" o
        # formulario dando um destino a ele, e a falha fechada iria embora sem
        # nenhum teste ficar vermelho.
        formulario = re.search(r"<form\b[^>]*>", html)
        assert formulario is not None
        assert "action" not in formulario.group(0)

    def test_no_caminho_de_ERRO_o_valor_digitado_PERMANECE_no_campo(
        self, js: str
    ) -> None:
        """Se a resposta falhar, ninguem redigita o que acabou de escrever."""
        codigo = _so_o_codigo(js)

        # Nenhuma ATRIBUICAO a `value` em caminho nenhum do arquivo — a leitura
        # (`campo.value`) continua existindo, e e o que monta o pedido.
        assert re.findall(r"\.value\s*=(?!=)", codigo) == []
        assert ".reset()" not in codigo
        assert re.search(r"\.value\b", codigo) is not None

    def test_o_botao_troca_de_rotulo_por_ATRIBUTO_e_nao_por_texto(
        self, js: str, html: str
    ) -> None:
        """A copia de interface mora na marcacao, onde ela e conferivel.

        Os dois rotulos do botao estao no `index.html` e o CSS escolhe qual
        aparece pelo atributo. O que ESTE teste prende e a outra metade: que o
        JS nao guarda uma SEGUNDA copia desses textos. Um rotulo escrito daqui
        seria copia que nenhum teste de marcacao ve.
        """
        rotulos = re.findall(
            r'<span class="botao__rotulo[^"]*"[^>]*>([^<]+)</span>', html
        )
        assert len(rotulos) == 2, "os dois rotulos do botao sumiram da marcacao"

        for rotulo in rotulos:
            assert rotulo.strip() != ""
            assert rotulo not in js, f"o rotulo {rotulo!r} tem uma segunda copia no JS"

        # O rotulo de salvamento em curso e o que termina em reticencia — a
        # forma travada no contrato de copia, afirmada sem recopiar a frase.
        assert any(rotulo.strip().endswith("…") for rotulo in rotulos)

        # E o JS so troca o atributo que o CSS le.
        assert len(re.findall(r'setAttribute\(\s*"data-salvando"', js)) == 2

    def test_o_botao_e_desabilitado_durante_o_envio_e_volta_DEPOIS(
        self, js: str
    ) -> None:
        """Ele nao vira indicador giratorio, e ele VOLTA — inclusive na recusa.

        Um botao que fica desabilitado para sempre depois de um erro obriga a
        recarregar a pagina para tentar de novo, que e o oposto de "o valor
        permanece no campo para voce nao redigitar".
        """
        corpo = _so_o_codigo(_corpo_da_funcao(js, "enviarOCambio"))

        assert "disabled = true" in corpo
        assert "disabled = false" in corpo

    def test_a_frase_da_recusa_vem_do_SERVIDOR_e_nao_daqui(self, js: str) -> None:
        """Cada causa tem a sua frase, e elas sao cinco do lado do Python.

        Colapsar as cinco numa mensagem escrita aqui descreveria para o usuario
        um problema que nao e o dele — foi exatamente esse o buraco que a
        separacao das excecoes do cambio fechou.
        """
        corpo = _so_o_codigo(_corpo_da_funcao(js, "enviarOCambio"))

        assert re.search(r'escrever\(\s*"cambio-erro",\s*resultado\.conteudo\.erro',
                         corpo) is not None
        assert re.search(r'escrever\(\s*"cambio-carimbo",\s*resultado\.conteudo\.mensagem',
                         corpo) is not None

        # E o campo do corpo do pedido e o mesmo que o servidor espera.
        assert dashboard.CAMPO_DO_POST in js
        assert dashboard.CAMINHO_DO_CAMBIO in js

    def test_o_salvamento_repinta_SEM_criar_uma_segunda_corrente_de_polling(
        self, js: str
    ) -> None:
        """O R$ aparece sem recarregar — e sem dobrar a frequencia de consulta.

        Chamar a volta COMPLETA aqui repintaria a tela e agendaria mais uma
        corrente de temporizadores, em paralelo com a que ja roda. Cada
        salvamento dobraria a frequencia, para sempre, sem nenhum sintoma
        visivel alem de um servidor mais ocupado.
        """
        corpo = _so_o_codigo(_corpo_da_funcao(js, "enviarOCambio"))

        assert "buscarOsDados()" in corpo
        assert "darUmaVolta()" not in corpo


# ===========================================================================
# O UNICO TESTE DESTE ARQUIVO QUE EXECUTA UM ANALISADOR DE VERDADE
# ===========================================================================


class TestOArquivoAoMenosANALISA:
    """Nenhuma assercao sobre TEXTO ve um erro de sintaxe.

    Todas as sondas acima continuariam verdes sobre um arquivo com uma chave
    faltando — e um arquivo que nao analisa nao executa NADA: a pagina inteira
    fica parada no rotulo de leitura em curso, sem numero, sem grafico e sem
    formulario. E o modo de falha mais caro possivel, e o mais barato de pegar.

    O `node` nao e dependencia deste projeto e nao entra no `requirements.txt`:
    ele e uma ferramenta que a maquina pode ou nao ter. Quando ele existe, este
    teste roda; quando nao existe, ele PULA com a razao dita, em vez de sumir
    calado. Um teste que pula sem dizer por que e um silencio com cara de verde.
    """

    def test_o_dashboard_js_ANALISA_sem_erro(self) -> None:
        node = shutil.which("node")
        if node is None:
            pytest.skip(
                "`node` nao esta nesta maquina, entao a analise sintatica do "
                "dashboard.js nao pode rodar aqui. As sondas de texto deste "
                "arquivo seguem valendo; o que se perde e so a garantia de que "
                "o arquivo analisa."
            )

        concluido = subprocess.run(
            [node, "--check", str(ARQUIVO_DO_JS)],
            capture_output=True,
            text=True,
        )
        assert concluido.returncode == 0, concluido.stderr
