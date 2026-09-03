"""A prova do DASH-05 SEM NAVEGADOR: uma SEGUNDA serie atravessa a pilha.

O requisito diz que a Adena e a PRIMEIRA INSTANCIA de um componente generico, e
nao um caso especial no codigo -- e que instanciar uma segunda serie (qualquer
item da aba de negociacao) NAO exige codigo de grafico novo. O v1 mostra so a
Adena na tela por decisao travada, entao a generalidade nao pode ser conferida
olhando: ela tem de ser PROVADA.

O QUE ESTA PROVA COBRE, e ela cobre isso de ponta a ponta:
  1. o DADO -- um CSV com observacoes de duas series produz DOIS elementos na
     lista de series do payload;
  2. o CONTRATO -- os dois elementos tem conjuntos de chaves IDENTICOS, entao
     nenhuma chave existe so para a Adena;
  3. a CONTA -- o formatador de cada serie sai do PONTO DE DECISAO UNICO do
     mercado, e os textos resultantes diferem em FORMA e nao so em digito;
  4. o SERVIDOR -- os dois elementos atravessam o endpoint com o mesmo
     contrato;
  5. o NAVEGADOR, por leitura de fonte -- toda propriedade que a funcao de
     instanciacao de serie do `dashboard.js` consome existe nos DOIS elementos.

O QUE ESTA PROVA **NAO** COBRE, dito por extenso para nao ser confundido com o
que ela cobre: ela NAO mostra que duas series DESENHADAS AO MESMO TEMPO ficam
legiveis na tela -- que as duas linhas se distinguem, que a legenda cabe, que as
cores escolhidas pelo chamador nao brigam. Isso exige um navegador de verdade, e
esta casa recusou instalador pesado de automacao de navegador por decisao
travada no `01-CONTEXT.md`. Essa metade e VERIFICACAO HUMANA DECLARADA, esta
registrada como tal no `01-UI-SPEC.md` (linha `zero-one-many`) e no SUMMARY deste
plano, e nao esta escondida atras de um teste verde.

O ELO 5 E O QUE FECHA A PROVA. Sem ele, os quatro primeiros mostrariam que o
SERVIDOR e generico e nao que o DESENHO e -- o `dashboard.js` poderia estar
lendo `serie.adena_pontos` que ninguem perceberia. E o elo 5 so vale porque o
extrator dele tem CONTROLE NEGATIVO: um extrator que devolvesse conjunto vazio
por um erro de expressao regular faria a comparacao passar por VACUIDADE, que e
exatamente o modo de falha que a Tarefa 3 do plano 01-01 existiu para eliminar.
"""

from __future__ import annotations

import http.client
import json
import re
import threading
from datetime import datetime
from pathlib import Path

import pytest

from l2scanner import dashboard, dashboard_dados, mercado_registro
from l2scanner.mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA, SEPARADOR
from l2scanner.mercado_console import formatador_do_unitario

JS = (
    Path(__file__).resolve().parent.parent
    / "l2scanner"
    / "recursos"
    / "dashboard"
    / "dashboard.js"
)

ESTE_ARQUIVO = Path(__file__).resolve()

# O terminador que `csv.writer` emite, e por isso o que a fixture escreve.
# Molde de `tests/test_dashboard_servidor.py`.
TERMINADOR = "\r\n"

AGORA = datetime(2026, 9, 1, 15, 0, 0)

# A SEGUNDA SERIE E UM ITEM QUALQUER DA ABA DE NEGOCIACAO, e a escolha e
# deliberadamente sem graca: se a generalidade dependesse de escolher um item
# especial, ela nao seria generalidade.
CHAVE_DA_SEGUNDA_SERIE = "common-aztac#0"

# CINCO OFERTAS DISTINTAS POR INSTANTE de proposito: o piso de evidencia da
# MEDIANA e 5 (o do menor e 1). Com menos, `tipica_texto` viria como frase de
# piso em vez de numero formatado, e a comparacao de FORMA abaixo estaria
# medindo a frase de piso -- que e igual nas duas series -- em vez do
# formatador, que e o que ela existe para medir.
_OFERTAS_DA_ADENA = (
    ("11600", "10000000"),
    ("30000", "15000000"),
    ("12000", "10000000"),
    ("23400", "20000000"),
    ("5900", "5000000"),
)
_OFERTAS_DO_ITEM = (
    ("6200", "48"),
    ("5900", "48"),
    ("6400", "50"),
    ("6100", "47"),
    ("6300", "49"),
)

LINHAS_DE_FIXTURE = (
    *[
        (CHAVE_DA_SERIE_DA_ADENA, "Adena", "2026-09-01T14:00:00", total, qtd, "0")
        for total, qtd in _OFERTAS_DA_ADENA
    ],
    *[
        (CHAVE_DA_SEGUNDA_SERIE, "Common Aztac", "2026-09-01T13:00:00", total, qtd, "0")
        for total, qtd in _OFERTAS_DO_ITEM
    ],
    # Um segundo instante em cada serie, para a serie ter mais de um ponto e os
    # baldes terem o que agregar.
    (CHAVE_DA_SERIE_DA_ADENA, "Adena", "2026-09-01T14:30:00", "11400", "10000000", "0"),
    (CHAVE_DA_SEGUNDA_SERIE, "Common Aztac", "2026-09-01T13:30:00", "5800", "48", "0"),
)


def _csv_de_fixture() -> str:
    linhas = [SEPARADOR.join(mercado_registro.COLUNAS)]
    linhas.extend(SEPARADOR.join(campos) for campos in LINHAS_DE_FIXTURE)
    return "".join(linha + TERMINADOR for linha in linhas)


def _escrever(arquivo: Path, texto: str) -> None:
    """`newline=""` obrigatorio: sem ele o Windows traduz `\\n` e o `\\r\\n` da
    fixture viraria `\\r\\r\\n`, que nao e o que o escritor produz."""
    arquivo.write_text(texto, encoding="utf-8", newline="")


@pytest.fixture
def pasta_do_mercado(tmp_path: Path) -> Path:
    """Duas series em disco, e NADA alem disso.

    Sem frame, sem OCR, sem captura: a prova do DASH-05 acontece inteira sobre
    um CSV escrito a mao e o JSON que sai dele.
    """
    pasta = tmp_path / ".mercado"
    pasta.mkdir()
    _escrever(pasta / mercado_registro.ARQUIVO_DE_OBSERVACOES, _csv_de_fixture())
    return pasta


@pytest.fixture
def series(pasta_do_mercado: Path) -> list[dict]:
    return dashboard_dados.payload(pasta_do_mercado, AGORA)["series"]


@pytest.fixture
def servidor(pasta_do_mercado: Path):
    """Molde LITERAL de `tests/test_dashboard_servidor.py`.

    PORTA ZERO, NUNCA A FIXA: a suite nao pode brigar com o dashboard que o
    usuario deixou aberto na `PORTA_PADRAO`. `poll_interval=0.01` foi MEDIDO na
    pesquisa desta fase -- com o padrao de 0,5 s cada `shutdown()` custa 449 ms.
    """
    servidor = dashboard.montar_servidor(porta=0, pasta_do_mercado=pasta_do_mercado)
    tarefa = threading.Thread(
        target=servidor.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    tarefa.start()
    try:
        yield servidor
    finally:
        servidor.shutdown()
        servidor.server_close()
        tarefa.join(timeout=5)
        assert not tarefa.is_alive()


def _pedir_json(porta: int, caminho: str) -> dict:
    conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
    try:
        conexao.request("GET", caminho)
        resposta = conexao.getresponse()
        assert resposta.status == 200, f"{caminho} respondeu {resposta.status}"
        return json.loads(resposta.read().decode("utf-8"))
    finally:
        conexao.close()


def _forma(texto: str) -> str:
    """O texto SEM OS DIGITOS -- a forma, e nao o valor.

    Comparar os textos crus provaria pouco: duas series quaisquer tem numeros
    diferentes. O que este teste precisa mostrar e que a UNIDADE e a MOLDURA
    mudaram, ou seja, que um formatador DIFERENTE foi chamado.
    """
    return re.sub(r"[0-9]", "", texto)


def _sem_comentarios(js: str) -> str:
    """Comentario nao e codigo consumido.

    O `dashboard.js` tem JSDoc citando propriedades da serie na prosa. Sem esta
    limpeza, o extrator abaixo colheria nomes que o navegador nunca le -- e a
    comparacao seguinte ficaria vermelha por causa de um comentario, que e o
    jeito mais rapido de alguem apagar o teste.
    """
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", js, flags=re.MULTILINE)


def _propriedades_da_serie_consumidas(js: str) -> set[str]:
    """Os nomes de propriedade que a instanciacao de serie do JS LE.

    O corte e por PARAMETRO chamado `serie`: toda funcao de topo que recebe uma
    serie faz parte da instanciacao, e o `desenharUmaSerie` sozinho nao bastaria
    -- ele delega a leitura de `unidade` e dos dois rotulos para quem monta as
    opcoes do grafico, e a de `baldes` para quem agrega o zoom.

    O RECORTE E POR `function` NA COLUNA ZERO, e nao por contagem de chaves:
    contar `{` e `}` quebra em cima da primeira chave dentro de uma string, e
    este arquivo tem varias. As funcoes deste JS sao todas de topo, entao o
    recorte simples e o correto E o robusto.

    Devolve conjunto VAZIO quando nao ha funcao de serie nenhuma -- e o
    `test_o_extrator_de_propriedades_ACUSA_o_que_diz_medir` e o que prova que
    esse vazio significa ausencia, e nao cegueira.
    """
    achados: set[str] = set()
    for pedaco in re.split(r"^(?=function\s)", _sem_comentarios(js), flags=re.MULTILINE):
        cabecalho = re.match(r"function\s+[A-Za-z_$][\w$]*\s*\(([^)]*)\)", pedaco)
        if cabecalho is None:
            continue
        parametros = [p.strip() for p in cabecalho.group(1).split(",")]
        if "serie" not in parametros:
            continue
        for casamento in re.finditer(
            r"\bserie\.([A-Za-z_$][\w$]*)", pedaco[cabecalho.end() :]
        ):
            achados.add(casamento.group(1))
    return achados


class TestDuasSeriesAtravessamODado:
    """A generalidade comeca no dado, e ela e observavel sem nada em volta."""

    def test_o_payload_traz_DUAS_series(self, series):
        assert len(series) == 2, (
            f"o payload trouxe {len(series)} serie(s) para um CSV com duas. A "
            f"lista de series nao esta saindo do modelo do mercado."
        )

    def test_os_dois_elementos_tem_conjuntos_de_chaves_IDENTICOS(self, series):
        """ESTA E A FORMA CORRETA DE PROVAR GENERALIDADE, e a razao e direta:

        se existisse UMA chave so da Adena -- um `taxa_derivada`, um
        `xm_por_5_milhoes` --, entao instanciar a segunda serie exigiria codigo
        novo do lado do desenho para lidar com a ausencia dela. E o requisito
        proibe exatamente isso: "instanciar uma segunda serie nao exige codigo
        de grafico novo".

        Comparar CONJUNTOS, e nao "as chaves da Adena estao na outra": a
        inclusao em um sentido so deixaria passar uma chave que existisse
        apenas na segunda serie, que e o mesmo defeito espelhado.
        """
        primeira, segunda = series
        assert set(primeira) == set(segunda), (
            f"os dois elementos divergem em chave: so na primeira "
            f"{sorted(set(primeira) - set(segunda))}, so na segunda "
            f"{sorted(set(segunda) - set(primeira))}"
        )

    def test_a_segunda_serie_tem_pontos_e_baldes_como_a_primeira(self, series):
        """A igualdade de chaves seria satisfeita por duas series VAZIAS.

        Sem esta assercao, um payload que devolvesse `pontos: []` para as duas
        passaria no teste acima com folga -- e a generalidade estaria provada
        sobre o nada.
        """
        for serie in series:
            assert serie["pontos"], f"a serie {serie['chave']!r} veio sem ponto"
            assert serie["baldes"], f"a serie {serie['chave']!r} veio sem balde"
        primeira, segunda = series
        assert set(primeira["baldes"]) == set(segunda["baldes"])
        assert set(primeira["pontos"][0]) == set(segunda["pontos"][0])

    def test_as_DUAS_series_ganham_escada_de_eixo_na_forma_de_DINHEIRO(
        self, series
    ):
        """A escada do eixo e generica, e o item comum PROVA que ela e.

        E a mesma decisao de escopo que o resto deste arquivo cobra: consertar o
        eixo so da Adena deixaria o item comum com o rotulo dizendo
        `centesimos por unidade` e as marcas do eixo em outra forma -- o MESMO
        defeito que este plano veio corrigir, so que na outra serie. O DASH-05
        proibe a excecao com forma de Adena, e este teste e onde a proibicao
        vira medida.

        Os textos das duas saem em forma de dinheiro brasileiro porque as duas
        passam por `formatar_centesimos` -- a mesma funcao, e nao duas parecidas.
        As `unidade` continuam DIFERENTES entre si, e isso tambem e afirmado:
        generico nao quer dizer indistinguivel.
        """
        molde_de_dinheiro = re.compile(r"^\d{1,3}(?:\.\d{3})*,\d{2}$")

        for serie in series:
            escadas = serie["escadas_do_eixo"]
            assert escadas, f"a serie {serie['chave']!r} veio sem escada de eixo"
            for escada in escadas:
                for marca in escada["marcas"]:
                    assert molde_de_dinheiro.match(marca["texto"]), (
                        serie["chave"],
                        marca,
                    )

        primeira, segunda = series
        assert primeira["unidade"] != segunda["unidade"]


class TestOFormatadorSaiDoPontoDeDecisaoUNICO:
    """Chamar o formatador errado imprimiria um numero zerado com toda a
    confianca do mundo.

    `formatador_do_unitario` e o UNICO ponto de decisao entre a taxa da Adena e
    o unitario comum, e ele existe precisamente para que nao haja quatro `if`
    espalhados que um dia divirjam. Se a serie da Adena recebesse o formatador
    de unitario comum, a tela mostraria `0,00 por unidade` para uma taxa de
    58,00 -- calada e errada.
    """

    def test_o_ponto_de_decisao_devolve_formatadores_DIFERENTES(self):
        """A prova mais direta, e ela nao passa pelo payload.

        Comparacao por IDENTIDADE, e nao por resultado: e assim que
        `dashboard_dados._e_a_taxa` decide, e um teste que medisse outra coisa
        nao estaria prendendo o mesmo criterio.
        """
        assert formatador_do_unitario(
            CHAVE_DA_SERIE_DA_ADENA
        ) is not formatador_do_unitario(CHAVE_DA_SEGUNDA_SERIE)

    def test_os_textos_das_duas_series_diferem_em_FORMA(self, series):
        primeira, segunda = series
        forma_da_primeira = _forma(primeira["pontos"][0]["menor_texto"])
        forma_da_segunda = _forma(segunda["pontos"][0]["menor_texto"])
        assert forma_da_primeira.strip(), "a primeira serie veio com texto vazio"
        assert forma_da_segunda.strip(), "a segunda serie veio com texto vazio"
        assert forma_da_primeira != forma_da_segunda, (
            "os textos das duas series tem a MESMA forma "
            f"({forma_da_primeira!r}): as duas foram formatadas pela mesma "
            "funcao, entao o ponto de decisao unico nao foi consultado"
        )

    def test_a_TIPICA_tambem_atravessa_o_formatador_escolhido(self, series):
        """A mediana passa pelo mesmo formatador, e por isso a mesma prova vale.

        Ela esta aqui separada porque a `tipica` tem piso de evidencia proprio
        (5, contra 1 do menor): um dia em que a fixture perder ofertas, este
        teste avisa antes que a comparacao de forma comece a medir a frase de
        piso -- que e IGUAL nas duas series -- em vez do formatador.
        """
        primeira, segunda = series
        for serie in series:
            assert "sem evidencia" not in serie["pontos"][0]["tipica_texto"], (
                f"a serie {serie['chave']!r} caiu abaixo do piso da mediana; a "
                f"fixture precisa de mais ofertas distintas"
            )
        assert _forma(primeira["pontos"][0]["tipica_texto"]) != _forma(
            segunda["pontos"][0]["tipica_texto"]
        )

    def test_a_unidade_exibida_muda_com_a_serie(self, series):
        """A unidade e propriedade do objeto, e nao constante do JS.

        E ela que vira rotulo do eixo vertical. Uma unidade constante no arquivo
        de grafico seria o "codigo de grafico novo" que o requisito proibe --
        alguem teria de ir la trocar a string para a segunda instancia.
        """
        primeira, segunda = series
        assert primeira["unidade"] != segunda["unidade"]
        assert primeira["titulo"] != segunda["titulo"]


class TestASegundaSerieAtravessaOServidor:
    def test_o_endpoint_devolve_os_DOIS_elementos_com_o_mesmo_contrato(
        self, servidor
    ):
        """A travessia de verdade, com soquete e JSON serializado.

        O payload em memoria pode conter tipos que nao sobrevivem ao JSON (esta
        arvore ja teve `Fraction` e `Decimal` na fronteira). Provar a
        generalidade so em memoria deixaria de fora justamente a serializacao,
        que e por onde o navegador recebe.
        """
        porta = servidor.server_address[1]
        dados = _pedir_json(porta, "/dados")
        assert len(dados["series"]) == 2
        primeira, segunda = dados["series"]
        assert set(primeira) == set(segunda)
        chaves = {serie["chave"] for serie in dados["series"]}
        assert chaves == {CHAVE_DA_SERIE_DA_ADENA, CHAVE_DA_SEGUNDA_SERIE}


class TestOQueONavegadorCONSOME:
    """O elo que fecha a prova: o lado do desenho, por leitura de fonte."""

    def test_toda_propriedade_consumida_pelo_JS_existe_nos_DOIS_elementos(
        self, series
    ):
        """A assercao de NAO-VAZIO vem ANTES da comparacao, e e obrigatoria.

        Com o conjunto vazio, `vazio <= qualquer_coisa` e VERDADE: a comparacao
        passaria sobre um `dashboard.js` que nao tivesse funcao de serie
        nenhuma, sobre um arquivo apagado, e sobre um extrator quebrado. Um
        teste que passa por vacuidade e pior que teste nenhum, porque ele
        anuncia uma garantia que nao existe -- e e o mesmo defeito que a Tarefa
        3 do plano 01-01 consertou no tripwire do grafo de import.
        """
        consumidas = _propriedades_da_serie_consumidas(JS.read_text(encoding="utf-8"))

        assert consumidas, (
            "o extrator nao achou NENHUMA propriedade de serie no dashboard.js. "
            "Ou a funcao de instanciacao sumiu, ou o extrator parou de enxergar "
            "-- nos dois casos a comparacao abaixo passaria por vacuidade e "
            "nao provaria nada."
        )

        for serie in series:
            faltando = consumidas - set(serie)
            assert not faltando, (
                f"o dashboard.js le {sorted(faltando)} e a serie "
                f"{serie['chave']!r} nao tem essa(s) chave(s): instanciar esta "
                f"serie exigiria codigo de grafico novo, que e o que o DASH-05 "
                f"proibe"
            )

    def test_o_extrator_de_propriedades_ACUSA_o_que_diz_medir(self):
        """CONTROLE NEGATIVO do extrator, nos dois sentidos.

        A mutacao acontece sobre JS fabricado AQUI, e nao sobre o arquivo real:
        e a unica forma de provar que o extrator enxerga sem depender do que ele
        deveria estar medindo.
        """
        fabricado = (
            "function desenharUmaSerie(serie) {\n"
            '  escrever("serie-titulo", serie.titulo);\n'
            "  if (serie.pontos.length === 0) { return; }\n"
            "}\n"
            "function conjuntoDeBalde(serie, nome) {\n"
            "  return serie.baldes[nome];\n"
            "}\n"
        )
        assert _propriedades_da_serie_consumidas(fabricado) == {
            "titulo",
            "pontos",
            "baldes",
        }

        # O outro sentido: sem funcao de serie nenhuma, conjunto VAZIO. Sem esta
        # metade, um extrator que devolvesse SEMPRE o mesmo conjunto tambem
        # passaria na assercao de cima.
        sem_serie = (
            "function pintar(dados) {\n"
            "  return dados.destaque.xm.texto;\n"
            "}\n"
        )
        assert _propriedades_da_serie_consumidas(sem_serie) == set()

        # E a terceira: comentario nao conta. Uma propriedade citada so na prosa
        # do JSDoc nao e consumida pelo navegador, e colhe-la faria o teste
        # acima ficar vermelho por causa de um comentario.
        so_em_comentario = (
            "/** O componente le serie.propriedade_que_nao_existe. */\n"
            "function desenharUmaSerie(serie) {\n"
            "  return serie.titulo;\n"
            "}\n"
        )
        assert _propriedades_da_serie_consumidas(so_em_comentario) == {"titulo"}


class TestAFronteiraDestaProvaEstaDECLARADA:
    def test_o_cabecalho_diz_por_extenso_o_que_esta_prova_NAO_cobre(self):
        """Uma reserva de verificacao que nao esta escrita nao existe.

        O `01-UI-SPEC.md` marcou `zero-one-many` como reserva justamente porque
        "muitas series" nao tem tela no v1. Se o cabecalho deste arquivo perder
        a frase, o proximo leitor vai achar que o verde aqui cobre o desenho --
        e a metade que so o olho ve some do registro sem ninguem decidir isso.
        """
        cabecalho = ESTE_ARQUIVO.read_text(encoding="utf-8").split('"""')[1]
        assert "NAO** COBRE" in cabecalho or "NAO COBRE" in cabecalho
        assert "VERIFICACAO HUMANA DECLARADA" in cabecalho
        assert "legiveis na tela" in cabecalho
