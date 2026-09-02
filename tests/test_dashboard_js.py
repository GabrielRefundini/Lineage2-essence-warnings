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

import re
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
    '.replace(".", ",") + " XM por milhao");'
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
