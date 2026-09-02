"""A FATIA FINA do dashboard: do byte do CSV ao numero na tela, um caminho so.

O QUE ESTE ARQUIVO PRENDE, E POR QUE ELE E O PRIMEIRO
======================================================
Ele atravessa TODAS as camadas da fase uma vez, para o caminho feliz do destaque
em XM: leitura ao vivo do `.mercado/observacoes.csv`, o parser UNICO do mercado,
o formatador UNICO do mercado, a montagem do JSON, o servidor `http.server`, o
estatico servido com CSP, e o JS que exibe a string como recebeu.

Se a arquitetura estiver errada, ela erra AQUI, num commit — e nao depois de
seis camadas ja escritas em cima dela.

A ASSERCAO QUE CARREGA O PESO E A DE IGUALDADE DE STRING
=========================================================
`test_o_texto_do_destaque_e_IDENTICO_ao_que_o_console_imprime` compara, byte a
byte, o texto servido em `GET /dados` com `mercado_console.formatar_taxa_derivada`
chamado direto sobre as MESMAS observacoes. Ela existe para falhar no instante em
que alguem reformatar o numero no caminho — que e exatamente o "segundo
formatador" que o DASH-03 proibe. Uma assercao de "parece certo" nao pegaria
isso; uma de igualdade pega.

NADA AQUI TOCA A `.mercado/` REAL, pela mesma razao escrita em
`tests/test_mercado_registro.py:1-11`: toda fixture mora em `tmp_path`. E o CSV
de fixture e montado A MAO, no molde de `tests/test_mercado_analise.py:283-300`,
porque o que se quer provar e a leitura — construir o arquivo com o escritor
faria o teste depender do escritor para julgar o leitor.

`http.client` E NAO `urllib.request`, e a razao e do plano 01-04: `urllib`
NORMALIZA a URL antes de enviar, e esconderia metade das sondas de travessia de
caminho que aquele plano vai mandar. Escolher o cliente certo agora evita
reescrever a fixture inteira la.
"""

from __future__ import annotations

import hashlib
import http.client
import json
import re
import threading
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import pytest

from l2scanner import dashboard, dashboard_dados, mercado_console, mercado_registro
from l2scanner.mercado_analise import menor_pedido_visivel
from l2scanner.mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA, SEPARADOR

# O terminador que `csv.writer` emite, e por isso o que a fixture escreve. Ler
# um arquivo com `\n` puro esconderia a diferenca entre o que o escritor produz
# e o que o leitor aceita.
TERMINADOR = "\r\n"


# ---------------------------------------------------------------------------
# O CSV DE FIXTURE, MONTADO A MAO
# ---------------------------------------------------------------------------
#
# As quatro linhas de dado, e o que cada uma existe para provar:
#
#   1. adena#  11600 / 10.000.000  -> o MENOR unitario da serie; e dela que o
#      destaque sai. `11600 / 10.000.000 * 1.000.000 = 1.160 centesimos`, que o
#      `formatar_taxa_derivada` imprime como `11,60 XM por milhao`.
#   2. adena#  30000 / 15.000.000  -> unitario MAIOR e total MAIOR. Ela prova
#      que a ordem e pelo UNITARIO: escolher pelo total nao mudaria nada aqui,
#      mas a linha 3 fecha esse buraco.
#   3. adena#  12000 / 10.000.000  -> unitario maior que a 1 com total PROXIMO.
#   4. common-aztac#0             -> uma serie que NAO e a Adena, para provar
#      que o agrupamento por `chave_da_serie` acontece e que o destaque nao
#      soma peras com macas. Sem ela, `observacoes_de` estaria sendo exercitado
#      sobre um arquivo de uma serie so, e passaria por acidente.
LINHAS_DE_FIXTURE = (
    (CHAVE_DA_SERIE_DA_ADENA, "Adena", "2026-09-01T14:00:00", "11600", "10000000", "0"),
    (CHAVE_DA_SERIE_DA_ADENA, "Adena", "2026-09-01T14:05:00", "30000", "15000000", "0"),
    (CHAVE_DA_SERIE_DA_ADENA, "Adena", "2026-09-01T14:10:00", "12000", "10000000", "0"),
    ("common-aztac#0", "Common Aztac", "2026-09-01T13:00:00", "6200", "48", "0"),
)


def _csv_de_fixture() -> str:
    """O texto exato do arquivo, com cabecalho e terminador em toda linha."""
    linhas = [SEPARADOR.join(mercado_registro.COLUNAS)]
    linhas.extend(SEPARADOR.join(campos) for campos in LINHAS_DE_FIXTURE)
    return "".join(linha + TERMINADOR for linha in linhas)


def _escrever(arquivo: Path, texto: str) -> None:
    """`newline=""` obrigatorio: sem ele o Windows traduz `\\n` e o `\\r\\n` da
    fixture viraria `\\r\\r\\n`, que nao e o que o escritor produz."""
    arquivo.write_text(texto, encoding="utf-8", newline="")


def _ler(arquivo: Path) -> str:
    """O texto CRU, sem traducao de quebra de linha.

    `Path.read_text(newline="")` so existe a partir do 3.13, e esta arvore roda
    3.12 — dai o `open` explicito. Sem o `newline=""` o Python traduziria os
    `\\r\\n` da fixture para `\\n` na leitura, e os testes de corte estariam
    medindo o texto traduzido em vez do que esta no disco.
    """
    with arquivo.open("r", encoding="utf-8", newline="") as fonte:
        return fonte.read()


def _impressao_do_arquivo(caminho: Path) -> tuple[int, int, str]:
    """(tamanho, mtime_ns, sha256) — a impressao digital de UM arquivo.

    O MOLDE E DE `tests/test_mercado_firewall_de_fase.py:481`, e a razao dos
    TRES juntos e a mesma que esta escrita la: uma reescrita com bytes identicos
    nao muda o hash, e "escreveu por cima com o mesmo conteudo" continua sendo
    escrita; o `mtime_ns` pega esse caso, e o sha256 pega o caso em que o
    relogio do sistema de arquivos e grosso demais para separar duas escritas.
    """
    bruto = caminho.read_bytes()
    estado = caminho.stat()
    return (estado.st_size, estado.st_mtime_ns, hashlib.sha256(bruto).hexdigest())


@pytest.fixture
def pasta_do_mercado(tmp_path: Path) -> Path:
    pasta = tmp_path / ".mercado"
    pasta.mkdir()
    _escrever(pasta / mercado_registro.ARQUIVO_DE_OBSERVACOES, _csv_de_fixture())
    return pasta


@pytest.fixture
def arquivo(pasta_do_mercado: Path) -> Path:
    return pasta_do_mercado / mercado_registro.ARQUIVO_DE_OBSERVACOES


@pytest.fixture
def porta(pasta_do_mercado: Path):
    """Porta EFEMERA (0), nunca a fixa: a suite nao pode brigar com o dashboard
    que o usuario deixou aberto, e duas rodadas em paralelo nao podem colidir.

    `poll_interval` MEDIDO na pesquisa desta fase: com o padrao (0,5 s) cada
    `shutdown()` custa 449 ms; com 0,05 s custa 45,1 ms; com 0,01 s custa
    9,7 ms. Numa suite de milhares de testes, meio segundo por servidor e um
    custo que ninguem perdoa — e o numero esta aqui para o proximo a mexer nao
    "arredondar" de volta para o padrao achando que tanto faz.
    """
    servidor = dashboard.montar_servidor(porta=0, pasta_do_mercado=pasta_do_mercado)
    tarefa = threading.Thread(
        target=servidor.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    tarefa.start()
    try:
        yield servidor.server_address[1]
    finally:
        servidor.shutdown()
        servidor.server_close()
        tarefa.join(timeout=5)
        # A thread MORTA e parte da afirmacao: um servidor que sobrevive ao
        # teste vaza para o proximo e transforma falha em flake.
        assert not tarefa.is_alive()


def _get(porta: int, caminho: str):
    """(status, cabecalhos, corpo) de um GET cru."""
    conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
    try:
        conexao.request("GET", caminho)
        resposta = conexao.getresponse()
        return resposta.status, resposta.headers, resposta.read()
    finally:
        conexao.close()


# ---------------------------------------------------------------------------
# A TRAVESSIA INTEIRA: o numero servido e o numero do console
# ---------------------------------------------------------------------------


class TestUmaFonteUmaConta:
    def test_o_texto_do_destaque_e_IDENTICO_ao_que_o_console_imprime(
        self, porta: int, arquivo: Path
    ) -> None:
        """IGUALDADE DE STRING, e nao "o numero bate".

        Esta e a assercao que o DASH-03 existe para ter. Ela falha no instante
        em que alguem reacentuar, re-arredondar ou remontar a frase no caminho
        entre o `mercado_console` e o navegador — e o modo de falha que ela pega
        e justamente o silencioso, aquele em que o numero continua plausivel.
        """
        status, _, corpo = _get(porta, "/dados")
        assert status == 200
        servido = json.loads(corpo)["destaque"]["xm"]["texto"]

        so_a_adena = [
            observacao
            for observacao in mercado_registro.observacoes_do_arquivo(arquivo)
            if observacao.chave_da_serie == CHAVE_DA_SERIE_DA_ADENA
        ]
        esperado = mercado_console.formatar_taxa_derivada(
            menor_pedido_visivel(so_a_adena).unitario
        )

        assert servido == esperado
        # E o valor CONCRETO, para a fixture nao poder derivar em silencio junto
        # com o codigo: se os dois mudarem juntos, a igualdade acima continuaria
        # verde sobre um numero errado.
        assert servido == "11,60 XM por milhao de adena (derivado)"

    def test_o_destaque_carrega_n_e_recencia_colados_no_numero(
        self, porta: int
    ) -> None:
        """Estatistica sem `n` e adivinhacao com cara de numero (ANAL-01)."""
        _, _, corpo = _get(porta, "/dados")
        xm = json.loads(corpo)["destaque"]["xm"]
        assert xm["n"] == 3
        assert "01/09 14:10" in xm["recencia"]


# ---------------------------------------------------------------------------
# A LEITURA AO VIVO: ate a ultima linha COMPLETA, e nem um byte escrito
# ---------------------------------------------------------------------------


class TestALeituraAoVivo:
    def test_a_cauda_cortada_no_MEIO_da_ultima_linha_nao_derruba_a_serie(
        self, arquivo: Path
    ) -> None:
        """A degradacao correta: a ultima linha completa manda, a cauda cai.

        E a REDE DE SEGURANCA, e nao o caminho normal — a frequencia esta
        medida e escrita na docstring de `observacoes_ao_vivo`.
        """
        antes = dashboard_dados.observacoes_ao_vivo(arquivo)
        bruto = _ler(arquivo)

        fim_da_penultima = bruto.rfind(TERMINADOR, 0, len(bruto) - len(TERMINADOR))
        fim_da_penultima += len(TERMINADOR)
        ultima = bruto[fim_da_penultima:]
        _escrever(arquivo, bruto[:fim_da_penultima] + ultima[: len(ultima) // 2])

        depois = dashboard_dados.observacoes_ao_vivo(arquivo)
        assert depois.cauda_incompleta is True
        assert len(depois.observacoes) == len(antes.observacoes) - 1
        assert antes.cauda_incompleta is False

    def test_o_cabecalho_trocado_LEVANTA_nomeando_o_arquivo_REAL(
        self, arquivo: Path
    ) -> None:
        """A prova de que o adaptador nao trocou o nome do arquivo na mensagem.

        E o risco inteiro da rota escolhida na §2: um recorte feito por
        temporario faria o portao do cabecalho acusar um caminho em `AppData`
        que o usuario nao consegue abrir. Aqui a mensagem tem de nomear o CSV de
        verdade, porque a instrucao dela ("restaure a primeira linha") so serve
        se o usuario souber QUAL arquivo abrir.
        """
        bruto = _ler(arquivo)
        linhas = bruto.split(TERMINADOR)
        linhas[0] = SEPARADOR.join(("chave", "nome", "quando", "total", "qtd", "res"))
        _escrever(arquivo, TERMINADOR.join(linhas))

        with pytest.raises(mercado_registro.ContratoDoArquivoQuebrado) as erro:
            dashboard_dados.observacoes_ao_vivo(arquivo)

        assert str(arquivo) in str(erro.value)

    def test_cinquenta_leituras_nao_mudam_um_BYTE_do_arquivo(
        self, arquivo: Path
    ) -> None:
        """DASH-01 em numero: o CSV e do usuario, e este processo so LE.

        Cinquenta e nao uma: uma leitura que abrisse em `"r+"` por engano
        poderia nao mudar nada na primeira passada e truncar na decima.
        """
        antes = _impressao_do_arquivo(arquivo)
        for _ in range(50):
            dashboard_dados.observacoes_ao_vivo(arquivo)
        assert _impressao_do_arquivo(arquivo) == antes

    def test_arquivo_ausente_devolve_leitura_VAZIA_e_nao_levanta(
        self, tmp_path: Path
    ) -> None:
        """A `.mercado/` nasce vazia; a tela tem de dizer "sem evidencia"."""
        leitura = dashboard_dados.observacoes_ao_vivo(tmp_path / "nao-existe.csv")
        assert leitura.arquivo_ausente is True
        assert leitura.observacoes == []


# ---------------------------------------------------------------------------
# O SERVIDOR E A PAGINA
# ---------------------------------------------------------------------------


class TestOServidorEAPagina:
    def test_a_CSP_do_VEND_4_viaja_em_TODA_resposta(self, porta: int) -> None:
        """Afirmavel sem navegador, que e a doutrina de prova desta fase."""
        for caminho in ("/index.html", "/dados", "/dashboard.css", "/dashboard.js"):
            status, cabecalhos, _ = _get(porta, caminho)
            assert status == 200, caminho
            csp = cabecalhos.get("Content-Security-Policy")
            assert csp is not None, caminho
            assert "default-src 'none'" in csp, caminho
            assert "connect-src 'self'" in csp, caminho

    def test_o_servidor_nao_entrega_a_versao_do_Python(self, porta: int) -> None:
        """T-01-02: o cabecalho `Server` e superficie de reconhecimento."""
        _, cabecalhos, _ = _get(porta, "/index.html")
        assert "Python" not in cabecalhos.get("Server", "")

    def test_o_index_so_carrega_script_e_estilo_por_ARQUIVO(self) -> None:
        """A CSP `script-src 'self'` proibe as duas formas inline.

        A prova e uma assercao em Python sobre o AST do HTML, e nao um olhar:
        um `<script>` inline acrescentado num plano futuro passaria despercebido
        numa revisao e sairia BLOQUEADO no navegador, que e o pior lugar para
        descobrir.
        """
        pagina = (dashboard.PASTA_DOS_ESTATICOS / "index.html").read_text(
            encoding="utf-8"
        )

        class _Coletor(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.scripts: list[dict[str, str | None]] = []
                self.estilos_embutidos = 0

            def handle_starttag(self, tag, attrs):
                if tag == "script":
                    self.scripts.append(dict(attrs))
                elif tag == "style":
                    self.estilos_embutidos += 1

        coletor = _Coletor()
        coletor.feed(pagina)

        # SEM ESTA LINHA O TESTE SERIA VACUO: `all([])` e verdadeiro, entao uma
        # pagina sem script nenhum passaria com louvor no `all` abaixo. E o
        # padrao de defeito que `test_mercado_firewall_de_fase.py:449-470` ja
        # nomeia — um guarda cuja saida nao muda com o fato que ele julga.
        assert coletor.scripts, "o index deixou de carregar qualquer script"
        assert all("src" in atributos for atributos in coletor.scripts)
        assert coletor.estilos_embutidos == 0

    def test_o_js_nao_carrega_paleta_PROPRIA(self) -> None:
        """A cor mora SO no CSS, e a razao nao e estetica.

        O `dashboard.js` e obrigado a pedir cor por `getPropertyValue`, e uma
        cor sem nome de token e uma cor que o grafico nao consegue pedir. Um
        hexadecimal solto no JS seria a segunda paleta do projeto, e ela
        divergiria da primeira no dia em que o tema mudasse.
        """
        caca_hexadecimal = re.compile(r"#[0-9a-fA-F]{3,8}\b")
        codigo = (dashboard.PASTA_DOS_ESTATICOS / "dashboard.js").read_text(
            encoding="utf-8"
        )
        assert caca_hexadecimal.findall(codigo) == []

        # O CONTROLE NEGATIVO, e ele e o que torna a assercao acima uma prova:
        # a mesma expressao, no mesmo diretorio, ACHA hexadecimais no CSS. Sem
        # ele, um erro de digitacao na expressao deixaria o guarda verde para
        # sempre sobre um JS cheio de cor.
        estilo = (dashboard.PASTA_DOS_ESTATICOS / "dashboard.css").read_text(
            encoding="utf-8"
        )
        assert caca_hexadecimal.findall(estilo)


# ---------------------------------------------------------------------------
# O PAYLOAD, SEM SERVIDOR
# ---------------------------------------------------------------------------


class TestOPayloadEPuroQuantoDa:
    def test_sem_leitura_da_adena_o_texto_e_a_FRASE_de_piso_e_nunca_um_numero(
        self, tmp_path: Path
    ) -> None:
        """O estado NORMAL desta fase, e nao um caso de borda (CTX-1).

        Hoje o CSV de campo tem 92 linhas e ZERO da serie `adena#`. Um payload
        que devolvesse `0,00` aqui seria a mentira plausivel que o projeto
        inteiro combate: ausencia se escreve com palavra, nunca com zero.
        """
        pasta = tmp_path / ".mercado"
        pasta.mkdir()
        _escrever(
            pasta / mercado_registro.ARQUIVO_DE_OBSERVACOES,
            SEPARADOR.join(mercado_registro.COLUNAS) + TERMINADOR,
        )

        pronto = dashboard_dados.payload(pasta, datetime(2026, 9, 1, 15, 0, 0))
        texto = pronto["destaque"]["xm"]["texto"]

        assert "sem evidencia" in texto
        assert "0,00" not in texto
        assert pronto["destaque"]["xm"]["recencia"] is None

    def test_a_fonte_declara_o_arquivo_e_o_estado_da_cauda(
        self, pasta_do_mercado: Path
    ) -> None:
        """A procedencia viaja no payload, e nao no folclore de quem desenha."""
        pronto = dashboard_dados.payload(
            pasta_do_mercado, datetime(2026, 9, 1, 15, 0, 0)
        )
        assert pronto["fonte"]["arquivo"].endswith(
            mercado_registro.ARQUIVO_DE_OBSERVACOES
        )
        assert pronto["fonte"]["cauda_incompleta"] is False
        assert pronto["gerado_em"] == "2026-09-01T15:00:00"
