"""As provas do SERVIDOR, todas SEM NAVEGADOR.

O QUE ESTE ARQUIVO COBRA, E POR QUE CADA PECA PRECISA DE PROVA PROPRIA
======================================================================
O `test_dashboard_tracer.py` ja atravessou a fase inteira uma vez, do byte do CSV
ao numero servido. Este arquivo cuida do que aquele deixou de proposito para
depois: o bind exclusivo, a listagem desligada, o cache, o portao de origem do
`POST /cambio`, os cabecalhos de seguranca, a travessia de caminho e o
desligamento limpo.

Sao TRES SUPERFICIES REAIS, e as tres foram medidas na pesquisa desta fase antes
de qualquer linha ser escrita:

1. **Travessia de caminho.** Este processo enxerga a raiz da arvore, e la mora o
   `.env` com o token do Chatwoot.
2. **POST de origem estranha.** Qualquer aba do navegador do usuario pode mandar
   um POST para `127.0.0.1`, e a CSP NAO impede isso — ela protege a nossa
   pagina, e nao a nossa API.
3. **Dois processos na mesma porta.** Medido: com o padrao da biblioteca, o
   segundo bind passa CALADO.

`http.client` E NAO `urllib.request`, E ISSO NAO E GOSTO
=========================================================
`urllib` NORMALIZA a URL antes de enviar: ele resolve os `..` do lado do cliente,
e mandaria para o servidor um caminho ja limpo. Metade das sondas de travessia
deste arquivo chegaria ao servidor como `/`, e passaria — provando nada. Com
`http.client.HTTPConnection.putrequest(..., skip_accept_encoding=True)` o caminho
cru sai na linha de pedido do jeito que foi escrito.

`tmp_path` SEMPRE, e a `.mercado/` real nunca e tocada — a mesma razao escrita em
`tests/test_mercado_registro.py:1-11`: dado acumulado e sem poda nao tem desfazer.
"""

from __future__ import annotations

import ast
import email.message
import errno
import hashlib
import http.client
import http.server
import inspect
import json
import os
import socket
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from l2scanner import dashboard, dashboard_cambio, dashboard_dados, mercado_registro
from l2scanner.mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA, SEPARADOR
from l2scanner.raiz import RAIZ

# O terminador que `csv.writer` emite, e por isso o que a fixture escreve.
TERMINADOR = "\r\n"

# Um instante fixo para o cache: com `agora` congelado, o unico eixo que pode
# invalidar a entrada e o arquivo — que e exatamente o que os testes de cache
# querem medir.
AGORA = datetime(2026, 9, 1, 15, 0, 0)

LINHAS_DE_FIXTURE = (
    (CHAVE_DA_SERIE_DA_ADENA, "Adena", "2026-09-01T14:00:00", "11600", "10000000", "0"),
    (CHAVE_DA_SERIE_DA_ADENA, "Adena", "2026-09-01T14:05:00", "30000", "15000000", "0"),
    (CHAVE_DA_SERIE_DA_ADENA, "Adena", "2026-09-01T14:10:00", "12000", "10000000", "0"),
    ("common-aztac#0", "Common Aztac", "2026-09-01T13:00:00", "6200", "48", "0"),
)


def _csv_de_fixture() -> str:
    linhas = [SEPARADOR.join(mercado_registro.COLUNAS)]
    linhas.extend(SEPARADOR.join(campos) for campos in LINHAS_DE_FIXTURE)
    return "".join(linha + TERMINADOR for linha in linhas)


def _escrever(arquivo: Path, texto: str) -> None:
    """`newline=""` obrigatorio: sem ele o Windows traduz `\\n` e o `\\r\\n` da
    fixture viraria `\\r\\r\\n`, que nao e o que o escritor produz."""
    arquivo.write_text(texto, encoding="utf-8", newline="")


def _impressao_do_arquivo(caminho: Path) -> tuple[int, int, str]:
    """(tamanho, mtime_ns, sha256) — a impressao digital de UM arquivo.

    O molde e de `tests/test_mercado_firewall_de_fase.py:481`, e a razao dos TRES
    juntos e a mesma que esta escrita la: uma reescrita com bytes identicos nao
    muda o hash, e "escreveu por cima com o mesmo conteudo" continua sendo
    escrita — o `mtime_ns` pega esse caso; e o sha256 pega o caso em que o
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
def servidor(pasta_do_mercado: Path):
    """O servidor de pe, e o numero da porta EFEMERA que ele conseguiu.

    PORTA ZERO, NUNCA A FIXA. A suite nao pode brigar com o dashboard que o
    usuario deixou aberto na `PORTA_PADRAO`, e duas rodadas em paralelo nao podem
    colidir uma com a outra.

    `poll_interval` MEDIDO na pesquisa desta fase: com o padrao (0,5 s) cada
    `shutdown()` custa 449 ms; com 0,05 s custa 45,1 ms; com 0,01 s custa 9,7 ms.
    Numa suite de milhares de testes, meio segundo por servidor e um custo que
    ninguem perdoa — e o numero esta aqui para o proximo a mexer nao "arredondar"
    de volta para o padrao achando que tanto faz.
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
        # A thread MORTA e parte da afirmacao: um servidor que sobrevive ao teste
        # vaza para o proximo e transforma falha em flake.
        assert not tarefa.is_alive()


@pytest.fixture
def porta(servidor) -> int:
    return servidor.server_address[1]


def _get(porta: int, caminho: str):
    """(status, cabecalhos, corpo) de um GET com o caminho CRU.

    `putrequest` em vez de `request` porque `skip_accept_encoding` so existe
    nele, e porque e a forma que deixa o caminho sair sem normalizacao nenhuma —
    ver a docstring do modulo.
    """
    conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
    try:
        conexao.putrequest("GET", caminho, skip_accept_encoding=True)
        conexao.endheaders()
        resposta = conexao.getresponse()
        return resposta.status, resposta.headers, resposta.read()
    finally:
        conexao.close()


# ===========================================================================
# TAREFA 1 — A PORTA, A LISTAGEM, O CACHE E O `main`
# ===========================================================================


class TestAPortaNaoEDIVISIVEL:
    """Dois dashboards na mesma porta tem de falhar EM VOZ ALTA.

    A pesquisa mediu que, com o padrao da biblioteca, o segundo bind passa sem
    erro nenhum e o navegador fala com quem ganhar a corrida do `accept`. O
    sintoma em campo seria "o numero as vezes atrasa" — um defeito que nao da
    para diagnosticar de dentro do programa.
    """

    def test_o_SEGUNDO_bind_na_mesma_porta_LEVANTA_endereco_em_uso(
        self, servidor, pasta_do_mercado: Path
    ) -> None:
        """A prova direta de que `allow_reuse_address` esta DESLIGADO."""
        ocupada = servidor.server_address[1]
        with pytest.raises(OSError) as erro:
            dashboard.montar_servidor(
                porta=ocupada, pasta_do_mercado=pasta_do_mercado
            ).server_close()
        # `errno.EADDRINUSE` e nao o `10048` cru: o numero do Windows esta
        # escrito no fonte com a medicao ao lado, e o teste nao precisa repetir a
        # plataforma para afirmar o desfecho.
        assert erro.value.errno == errno.EADDRINUSE

    def test_o_reuso_de_endereco_esta_desligado_na_CLASSE_e_nao_por_acaso(
        self,
    ) -> None:
        """O CONTROLE que separa "o bind falhou" de "a defesa existe".

        Sem esta linha, o teste acima passaria tambem num mundo em que o segundo
        bind falha por outro motivo qualquer. Aqui a afirmacao e sobre a
        DECISAO — e o valor de referencia ao lado prova que ela e uma decisao, e
        nao o padrao herdado.
        """
        assert dashboard.Servidor.allow_reuse_address is False
        assert http.server.HTTPServer.allow_reuse_address == 1

    def test_a_PORTA_PADRAO_fica_abaixo_da_faixa_dinamica_do_Windows(self) -> None:
        """49152 e o piso da faixa dinamica, e o Windows RESERVA blocos dela.

        Uma porta fixa la dentro nao falha por estar em uso: ela falha por estar
        EXCLUIDA, e o usuario nao tem nada a fazer a respeito. As faixas mudam a
        cada boot, entao o teste prende a FAIXA e nao a lista medida.
        """
        assert dashboard.PORTA_PADRAO < 49152
        assert dashboard.PORTA_PADRAO > 1024  # nada de porta privilegiada

    def test_a_MENSAGEM_DE_PORTA_OCUPADA_cita_a_porta_e_diz_O_QUE_FAZER(self) -> None:
        """A anatomia da casa: o que houve, que nada mudou, o que fazer, e o que
        continua funcionando."""
        frase = dashboard.MENSAGEM_DE_PORTA_OCUPADA.format(porta=8787)
        assert "8787" in frase
        assert "O QUE FAZER" in frase
        assert "--porta" in frase
        assert "--mercado" in frase  # o que continua funcionando
        # Sem acento, como todo texto que este projeto poe na frente do usuario.
        assert frase.isascii()

    def test_a_MENSAGEM_DE_PORTA_RESERVADA_NAO_manda_fechar_janela_nenhuma(
        self,
    ) -> None:
        """As duas falhas de bind sao DIFERENTES, e a instrucao tambem.

        Medido: uma porta dentro das faixas excluidas pelo Windows levanta
        `errno 13` (winerror 10013), e nao `10048`. Se as duas caissem na mesma
        frase, o usuario leria "o dashboard ja esta aberto" para uma porta em que
        nao ha dashboard nenhum, e iria fechar janelas que nao existem.
        """
        frase = dashboard.MENSAGEM_DE_PORTA_RESERVADA.format(porta=49200)
        assert "49200" in frase
        assert "RESERVADA" in frase
        assert "ja esta aberto" not in frase
        assert frase.isascii()

    def test_a_resposta_servida_na_porta_nao_entrega_a_versao_do_Python(
        self, porta: int
    ) -> None:
        """T-01-02: o cabecalho `Server` e reconhecimento de graca."""
        _, cabecalhos, _ = _get(porta, "/index.html")
        apresentacao = cabecalhos.get("Server", "")
        assert "Python" not in apresentacao
        assert sys.version.split()[0] not in apresentacao


class TestAListagemDeDiretorioNuncaAparece:
    """Um diretorio sem arquivo de indice responde 404, e nao a arvore."""

    def test_um_diretorio_SEM_indice_responde_404_e_nao_a_listagem(
        self, porta: int
    ) -> None:
        """`vendor/` e o diretorio real sem indice que a arvore ja tem.

        Usar o que existe, em vez de criar um subdiretorio de teste dentro dos
        estaticos, evita escrever na arvore do usuario para provar uma coisa que
        ja da para provar sem escrever nada.
        """
        # O GUARDA: se um plano futuro puser um indice em `vendor/`, este teste
        # deixa de medir o que ele acha que mede — e cai aqui, dizendo isso.
        assert not (dashboard.PASTA_DOS_ESTATICOS / "vendor" / "index.html").exists()

        status, _, corpo = _get(porta, "/vendor/")
        assert status == 404
        assert b"uPlot" not in corpo  # nenhum nome de arquivo vazou

    def test_o_CONTROLE_POSITIVO_o_mesmo_diretorio_serve_seus_ARQUIVOS(
        self, porta: int
    ) -> None:
        """Sem ele, um servidor que respondesse 404 para tudo passaria acima.

        Este teste prova que `vendor/` E alcancavel e E servido — logo, o 404 do
        pedido de diretorio e a sobrescrita de `list_directory`, e nao a ausencia
        da pasta.
        """
        status, _, corpo = _get(porta, "/vendor/uPlot.min.css")
        assert status == 200
        assert corpo


class TestOCacheDaLeitura:
    """A releitura so acontece quando o arquivo (ou o minuto) muda."""

    @staticmethod
    def _contando(monkeypatch) -> list:
        """Envolve `dashboard_dados.payload` num contador, sem trocar o corpo.

        Contar a funcao REAL e nao um dublê: o que se quer afirmar e quantas
        vezes a leitura cara aconteceu, e um dublê provaria apenas que o cache
        chama o dublê.
        """
        chamadas: list = []
        original = dashboard_dados.payload

        def contando(*args, **kwargs):
            chamadas.append(1)
            return original(*args, **kwargs)

        monkeypatch.setattr(dashboard_dados, "payload", contando)
        return chamadas

    def test_duas_requisicoes_sobre_um_CSV_PARADO_fazem_UMA_leitura(
        self, monkeypatch, pasta_do_mercado: Path
    ) -> None:
        chamadas = self._contando(monkeypatch)
        cache = dashboard.CacheDaLeitura()

        cache.pronto(pasta_do_mercado, AGORA)
        cache.pronto(pasta_do_mercado, AGORA)

        assert len(chamadas) == 1

    def test_TOCAR_o_arquivo_faz_a_leitura_acontecer_DE_NOVO(
        self, monkeypatch, pasta_do_mercado: Path, arquivo: Path
    ) -> None:
        """O controle que impede o cache de virar um congelamento.

        Sem ele, um cache que NUNCA recalcula passaria no teste de cima com
        louvor — e a pagina mostraria para sempre o primeiro payload da sessao.
        """
        chamadas = self._contando(monkeypatch)
        cache = dashboard.CacheDaLeitura()
        cache.pronto(pasta_do_mercado, AGORA)
        assert len(chamadas) == 1

        # `os.utime` com um valor EXPLICITO, e nao um `touch`: a granularidade do
        # relogio do sistema de arquivos no Windows pode nao separar duas
        # escritas seguidas, e o teste ficaria intermitente por um motivo que nao
        # tem nada a ver com o cache.
        antigo = arquivo.stat().st_mtime_ns
        os.utime(arquivo, ns=(antigo + 5_000_000_000, antigo + 5_000_000_000))

        cache.pronto(pasta_do_mercado, AGORA)
        assert len(chamadas) == 2

    def test_o_MINUTO_novo_recalcula_mesmo_com_o_arquivo_PARADO(
        self, monkeypatch, pasta_do_mercado: Path
    ) -> None:
        """O DEFEITO QUE A CHAVE SO-DE-ARQUIVO CRIARIA, preso por teste.

        Uma chave apenas `(tamanho, mtime_ns)` congelaria o aviso de dado velho:
        um CSV parado as 14:10 devolveria, as 19:00, o mesmo dicionario com
        `velho=False`, e a tela afirmaria frescor sobre um numero de cinco horas
        atras. Isso e literalmente o que o DASH-04 e o contrato de copy proibem.
        """
        chamadas = self._contando(monkeypatch)
        cache = dashboard.CacheDaLeitura()

        cache.pronto(pasta_do_mercado, AGORA)
        cache.pronto(pasta_do_mercado, AGORA + timedelta(seconds=30))
        assert len(chamadas) == 1, "meio minuto depois ainda e o mesmo minuto"

        cache.pronto(pasta_do_mercado, AGORA + timedelta(minutes=1))
        assert len(chamadas) == 2

    def test_o_aviso_de_DADO_VELHO_aparece_mesmo_com_o_arquivo_PARADO(
        self, pasta_do_mercado: Path
    ) -> None:
        """A consequencia visivel do teste acima, afirmada no texto servido."""
        cache = dashboard.CacheDaLeitura()
        fresco = cache.pronto(pasta_do_mercado, AGORA)
        assert fresco["destaque"]["xm"]["velho"] is False

        # Cinco horas depois, com o MESMO arquivo, sem um byte mudado.
        velho = cache.pronto(pasta_do_mercado, AGORA + timedelta(hours=5))
        assert velho["destaque"]["xm"]["velho"] is True

    def test_o_gerado_em_do_cache_e_SEMPRE_o_instante_de_verdade(
        self, pasta_do_mercado: Path
    ) -> None:
        """Um carimbo congelado seria lido pela pagina como servidor mudo."""
        cache = dashboard.CacheDaLeitura()
        cache.pronto(pasta_do_mercado, AGORA)
        depois = AGORA + timedelta(seconds=17)
        assert cache.pronto(pasta_do_mercado, depois)["gerado_em"] == depois.isoformat()

    def test_o_cache_serve_o_INTERVALO_DE_POLLING_para_o_navegador(
        self, porta: int
    ) -> None:
        """O intervalo mora em UM lugar so, e viaja no JSON.

        Um intervalo escrito no Python e no JS nao fica errado nos dois: fica
        errado em UM, e ninguem percebe.
        """
        _, _, corpo = _get(porta, dashboard.CAMINHO_DOS_DADOS)
        servido = json.loads(corpo)["intervalo_de_polling_ms"]
        assert servido == dashboard.INTERVALO_DE_POLLING_MS

    def test_o_cache_de_um_arquivo_AUSENTE_tambem_e_cache(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        """"O arquivo nao existe" e um estado, e ele tambem merece cache.

        E o estado NORMAL de uma maquina que nunca rodou o `--mercado`; deixa-lo
        fora do cache seria pagar o caminho caro justamente em quem ainda nao tem
        dado nenhum.
        """
        chamadas = self._contando(monkeypatch)
        cache = dashboard.CacheDaLeitura()
        vazia = tmp_path / "sem-mercado"
        vazia.mkdir()

        primeiro = cache.pronto(vazia, AGORA)
        cache.pronto(vazia, AGORA)

        assert len(chamadas) == 1
        assert primeiro["estado"] == dashboard_dados.ESTADO_ARQUIVO_AUSENTE


class TestOMainSobeECaiEmVozAlta:
    """O `main` e o que o `.bat` chama: ele devolve codigo, nunca traceback."""

    def test_main_sobre_uma_porta_ja_OCUPADA_devolve_1_sem_levantar(
        self, capsys
    ) -> None:
        """A traducao do `errno 10048` para uma frase acionavel.

        O soquete de bloqueio e criado aqui a mao, e nao por um segundo
        `montar_servidor`, para o teste medir a reacao do `main` a uma porta
        ocupada por QUALQUER coisa — que e o caso real: pode ser outro dashboard,
        pode ser outro programa do usuario.
        """
        bloqueador = socket.socket()
        bloqueador.bind(("127.0.0.1", 0))
        bloqueador.listen(1)
        ocupada = bloqueador.getsockname()[1]
        try:
            codigo = dashboard.main(
                ["--porta", str(ocupada), "--sem-navegador"]
            )
        finally:
            bloqueador.close()

        assert codigo == 1
        saida = capsys.readouterr().out
        assert str(ocupada) in saida
        assert "O QUE FAZER" in saida
        assert "Traceback" not in saida

    def test_main_aceita_a_porta_pela_LINHA_DE_COMANDO_com_o_padrao_da_constante(
        self,
    ) -> None:
        """O padrao vem da constante, e nao de um literal repetido no `main`.

        A prova e por leitura de fonte porque subir o servidor na porta fixa
        dentro da suite e exatamente o que a fixture de porta efemera existe para
        nao fazer.
        """
        fonte = inspect.getsource(dashboard.main)
        assert "default=PORTA_PADRAO" in fonte
        assert "8787" not in fonte

    def test_o_modulo_tem_o_bloco_de_EXECUCAO_DIRETA_que_o_lancador_chama(
        self,
    ) -> None:
        """DASH-06: `python -m l2scanner.dashboard` sem tocar o `__main__.py`.

        O `__main__.py` e o caminho do `--mercado`. Se o dashboard entrasse por
        la, derrubar um passaria a poder derrubar o outro — e o requisito exige o
        contrario.
        """
        fonte = (RAIZ / "l2scanner" / "dashboard.py").read_text(encoding="utf-8")
        assert 'if __name__ == "__main__":' in fonte
        assert "raise SystemExit(main())" in fonte

        # E o `__main__.py` NAO conhece o dashboard: a independencia e nos dois
        # sentidos, e uma so das metades nao e independencia.
        principal = (RAIZ / "l2scanner" / "__main__.py").read_text(encoding="utf-8")
        assert "dashboard" not in principal


class TestOBindENoEnderecoDeRetornoLocal:
    """T-01-20: nunca em todas as interfaces, e a prova e sobre o FONTE."""

    def test_o_fonte_do_dashboard_nao_contem_o_endereco_de_TODAS_as_interfaces(
        self,
    ) -> None:
        """Por AST, e nao por `grep`: um comentario explicando que nao usamos
        `0.0.0.0` contem a string, e um `grep` cru cairia sobre ele.

        A afirmacao e sobre as CONSTANTES do modulo — o que o codigo pode passar
        para o `bind` — e nao sobre o texto do arquivo.
        """
        arvore = ast.parse(
            (RAIZ / "l2scanner" / "dashboard.py").read_text(encoding="utf-8")
        )
        alvos = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Constant) and no.value == "0.0.0.0"
        ]
        assert alvos == []

    def test_o_servidor_de_pe_esta_escutando_em_127_0_0_1(self, servidor) -> None:
        """O complemento do teste acima: o fonte nao contem a string E o soquete
        de verdade esta no endereco de retorno local."""
        assert servidor.server_address[0] == "127.0.0.1"


# ===========================================================================
# TAREFA 2 — O `POST /cambio` E O PORTAO DE ORIGEM
# ===========================================================================
#
# A DEFESA QUE A CSP NAO COBRE. A politica de seguranca de conteudo impede a
# NOSSA pagina de carregar coisa de fora; ela nao impede uma pagina de fora de
# mandar um POST para a NOSSA API. Numa maquina onde o `.env` do Chatwoot mora ao
# lado, uma API local que ESCREVE arquivo sem conferir a origem e uma superficie
# de verdade — e o unico jeito de fechar isso e conferindo os cabecalhos.


def _post(
    porta: int,
    caminho: str,
    corpo,
    *,
    origem=None,
    destino=None,
    tamanho_declarado=None,
):
    """(status, cabecalhos, corpo) de um POST montado A MAO.

    `putheader` um a um, e nao `request(..., headers=...)`, porque estes testes
    precisam OMITIR cabecalhos — e "ausente" e um dos casos que o portao tem de
    decidir. Um dicionario com `None` dentro mandaria a string `None`.

    `tamanho_declarado` existe para o teste do teto: ele deixa declarar um
    `Content-Length` MAIOR que os bytes efetivamente enviados, que e como se
    prova que o servidor recusa ANTES de tentar ler o corpo. Se ele lesse, a
    leitura ficaria pendurada esperando bytes que nunca chegam e o teste falharia
    por tempo esgotado — que e exatamente o desfecho que se quer poder distinguir.
    """
    dados = corpo.encode("utf-8") if isinstance(corpo, str) else corpo
    conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
    try:
        conexao.putrequest("POST", caminho, skip_accept_encoding=True)
        conexao.putheader("Content-Type", "application/json")
        conexao.putheader(
            "Content-Length",
            str(len(dados) if tamanho_declarado is None else tamanho_declarado),
        )
        if origem is not None:
            conexao.putheader("Origin", origem)
        if destino is not None:
            conexao.putheader("Sec-Fetch-Site", destino)
        conexao.endheaders()
        conexao.send(dados)
        resposta = conexao.getresponse()
        return resposta.status, resposta.headers, resposta.read()
    finally:
        conexao.close()


def _corpo_do_cambio(texto: str) -> str:
    return json.dumps({dashboard.CAMPO_DO_POST: texto})


class TestOPortaoDeOrigemEUmaFuncaoPURA:
    """O CONTROLE NEGATIVO, sem servidor nenhum.

    SEIS ASSERCOES, e as duas ultimas sao a razao de esta classe existir. As
    quatro primeiras (origem certa, origem de fora, origem ausente, porta errada)
    passariam numa implementacao que ignorasse `Sec-Fetch-Site` inteiro. As duas
    ultimas prendem a metade do destino de requisicao nos DOIS sentidos: ela nao
    pode ser omitida (senao um pedido cross-site com Origin forjavel passaria) e
    nao pode ser invertida (senao a ausencia do cabecalho recusaria todo mundo, e
    um cliente que nao o envia ficaria de fora sem ninguem entender por que).
    """

    PORTA = 8787

    def _cabecalhos(self, **pares):
        """Um `email.message.Message`, que e o tipo REAL de `self.headers`.

        Um `dict` passaria no teste e mentiria: `Message.get` e insensivel a
        caixa, e um portao escrito contra `dict` quebraria com o `origin:` em
        minusculas que qualquer cliente pode mandar.
        """
        cabecalhos = email.message.Message()
        for nome, valor in pares.items():
            if valor is not None:
                cabecalhos[nome.replace("_", "-")] = valor
        return cabecalhos

    def test_1_a_origem_CERTA_e_aceita(self) -> None:
        assert (
            dashboard.origem_permitida(
                self._cabecalhos(Origin=f"http://127.0.0.1:{self.PORTA}"), self.PORTA
            )
            is True
        )

    def test_2_a_origem_de_OUTRO_SITE_e_recusada(self) -> None:
        assert (
            dashboard.origem_permitida(
                self._cabecalhos(Origin="https://algum-site.example"), self.PORTA
            )
            is False
        )

    def test_3_a_origem_AUSENTE_e_recusada(self) -> None:
        """A ausencia NAO vale como permissao.

        Um portao que aceitasse "sem Origin" seria contornavel por qualquer
        cliente que simplesmente nao mandasse o cabecalho — que e todo cliente
        que nao seja um navegador.
        """
        assert dashboard.origem_permitida(self._cabecalhos(), self.PORTA) is False

    def test_4_a_origem_local_em_OUTRA_PORTA_e_recusada(self) -> None:
        assert (
            dashboard.origem_permitida(
                self._cabecalhos(Origin=f"http://127.0.0.1:{self.PORTA + 1}"),
                self.PORTA,
            )
            is False
        )

    def test_5_o_destino_CROSS_SITE_recusa_mesmo_com_a_origem_CERTA(self) -> None:
        """OS DOIS SINAIS SAO CONFERIDOS, e nao o primeiro que casar."""
        assert (
            dashboard.origem_permitida(
                self._cabecalhos(
                    Origin=f"http://127.0.0.1:{self.PORTA}",
                    Sec_Fetch_Site="cross-site",
                ),
                self.PORTA,
            )
            is False
        )

    def test_6_o_destino_AUSENTE_cai_para_a_decisao_da_ORIGEM(self) -> None:
        """A ausencia do sinal moderno nao pode virar recusa universal.

        `Sec-Fetch-Site` e recente; um cliente que nao o envie tem de ser julgado
        pela origem, que e o sinal que sempre existiu. Sem esta assercao, uma
        implementacao que exigisse o cabecalho passaria nas cinco de cima e
        recusaria todo mundo em campo.
        """
        assert (
            dashboard.origem_permitida(
                self._cabecalhos(
                    Origin=f"http://127.0.0.1:{self.PORTA}", Sec_Fetch_Site=None
                ),
                self.PORTA,
            )
            is True
        )


class TestOPOSTDoCambio:
    """O caminho inteiro, pelo soquete, com o cabecalho escolhido a mao."""

    def test_a_origem_CERTA_grava_e_responde_200_com_o_carimbo(
        self, porta: int, pasta_do_mercado: Path
    ) -> None:
        status, _, corpo = _post(
            porta,
            dashboard.CAMINHO_DO_CAMBIO,
            _corpo_do_cambio("0,50"),
            origem=f"http://127.0.0.1:{porta}",
            destino="same-origin",
        )
        assert status == 200

        resposta = json.loads(corpo)
        # O VALOR VIAJA COMO STRING: `Decimal` nao atravessa JSON, e serializar
        # como numero faria `0.50` voltar `float` do outro lado.
        assert resposta["reais_por_xm"] == "0.50"
        assert isinstance(resposta["reais_por_xm"], str)
        assert resposta["informado_em"]
        assert "0,50" in resposta["mensagem"]

        # E o arquivo no disco concorda com a resposta.
        gravado = dashboard_cambio.ler_o_cambio(pasta_do_mercado)
        assert gravado is not None
        assert str(gravado.reais_por_xm) == "0.50"

    def test_a_origem_de_OUTRO_SITE_e_recusada_com_403_e_NADA_e_gravado(
        self, porta: int, pasta_do_mercado: Path
    ) -> None:
        """A prova de que o 403 nao e so um numero: o disco continua igual."""
        dashboard_cambio.gravar_o_cambio(pasta_do_mercado, "0,50", AGORA)
        antes = dashboard_cambio.ler_o_cambio(pasta_do_mercado)

        status, _, _ = _post(
            porta,
            dashboard.CAMINHO_DO_CAMBIO,
            _corpo_do_cambio("9,99"),
            origem="https://algum-site.example",
        )
        assert status == 403

        depois = dashboard_cambio.ler_o_cambio(pasta_do_mercado)
        assert depois is not None
        assert depois.reais_por_xm == antes.reais_por_xm
        assert depois.informado_em == antes.informado_em

    def test_a_origem_AUSENTE_e_recusada_com_403(self, porta: int) -> None:
        status, _, _ = _post(
            porta, dashboard.CAMINHO_DO_CAMBIO, _corpo_do_cambio("0,50"), origem=None
        )
        assert status == 403

    def test_a_origem_local_em_OUTRA_PORTA_e_recusada_com_403(
        self, porta: int
    ) -> None:
        status, _, _ = _post(
            porta,
            dashboard.CAMINHO_DO_CAMBIO,
            _corpo_do_cambio("0,50"),
            origem=f"http://127.0.0.1:{porta + 1}",
        )
        assert status == 403

    def test_o_destino_CROSS_SITE_e_recusado_mesmo_com_a_origem_CERTA(
        self, porta: int
    ) -> None:
        status, _, _ = _post(
            porta,
            dashboard.CAMINHO_DO_CAMBIO,
            _corpo_do_cambio("0,50"),
            origem=f"http://127.0.0.1:{porta}",
            destino="cross-site",
        )
        assert status == 403

    def test_SEM_o_destino_a_origem_certa_e_ACEITA(
        self, porta: int, pasta_do_mercado: Path
    ) -> None:
        status, _, _ = _post(
            porta,
            dashboard.CAMINHO_DO_CAMBIO,
            _corpo_do_cambio("0,50"),
            origem=f"http://127.0.0.1:{porta}",
            destino=None,
        )
        assert status == 200
        assert dashboard_cambio.ler_o_cambio(pasta_do_mercado) is not None

    @pytest.mark.parametrize("perigosa", ["1e3", "1_0", "+0.5", "1234567890123,5"])
    def test_uma_forma_PERIGOSA_medida_e_recusada_com_400_e_a_frase_travada(
        self, porta: int, pasta_do_mercado: Path, perigosa: str
    ) -> None:
        """As quatro que `Decimal` sozinho ACEITA, medidas na pesquisa.

        `1_0` e a pior delas: o usuario queria `1,0` e o R$ da tela ficaria VINTE
        VEZES maior, sem erro, sem aviso, com toda a aparencia de funcionar.

        E ELAS NAO PASSAM PELO FORMULARIO: este teste manda o POST direto pelo
        soquete, que e o que prova que a falha fechada mora no SERVIDOR e nao na
        validacao do navegador.
        """
        dashboard_cambio.gravar_o_cambio(pasta_do_mercado, "0,50", AGORA)

        status, _, corpo = _post(
            porta,
            dashboard.CAMINHO_DO_CAMBIO,
            _corpo_do_cambio(perigosa),
            origem=f"http://127.0.0.1:{porta}",
        )
        assert status == 400
        assert dashboard_cambio.MENSAGEM_DE_CAMBIO_INVALIDO in corpo.decode("utf-8")

        # O CAMBIO ANTERIOR CONTINUA VIGENTE — e continua sendo o que a leitura
        # devolve. Recusar sem preservar seria trocar um erro por outro.
        vigente = dashboard_cambio.ler_o_cambio(pasta_do_mercado)
        assert str(vigente.reais_por_xm) == "0.50"

    def test_um_corpo_MAIOR_que_o_teto_e_recusado_sem_ser_lido(
        self, porta: int
    ) -> None:
        """O `Content-Length` declara mais do que os bytes enviados.

        Se o servidor tentasse ler o corpo inteiro, ele ficaria pendurado
        esperando bytes que nunca chegam, e este teste falharia por tempo
        esgotado. A resposta rapida E a prova.
        """
        status, _, _ = _post(
            porta,
            dashboard.CAMINHO_DO_CAMBIO,
            _corpo_do_cambio("0,50"),
            origem=f"http://127.0.0.1:{porta}",
            tamanho_declarado=dashboard.TETO_DO_CORPO_DO_POST + 1,
        )
        assert status == 413

    def test_um_GET_no_caminho_do_cambio_NAO_grava_nada(
        self, porta: int, pasta_do_mercado: Path
    ) -> None:
        """O caminho da escrita e o POST, e so ele."""
        antes = sorted(p.name for p in pasta_do_mercado.iterdir())
        _get(porta, dashboard.CAMINHO_DO_CAMBIO)
        assert sorted(p.name for p in pasta_do_mercado.iterdir()) == antes
        assert dashboard_cambio.ler_o_cambio(pasta_do_mercado) is None

    def test_um_POST_em_OUTRO_caminho_responde_404(self, porta: int) -> None:
        status, _, _ = _post(
            porta,
            "/qualquer-outra-coisa",
            _corpo_do_cambio("0,50"),
            origem=f"http://127.0.0.1:{porta}",
        )
        assert status == 404

    def test_um_corpo_ILEGIVEL_nao_recebe_a_frase_de_cambio_invalido(
        self, porta: int
    ) -> None:
        """A causa tem de bater com a frase.

        Um corpo que nao e JSON nao e "um numero menor ou igual a zero"; dizer ao
        usuario para "informar um numero maior que zero" descreveria um problema
        que nao e o dele. E a mesma razao pela qual o `01-03` separou
        `HistoricoDoCambioIlegivel` de `CambioInvalido`.
        """
        status, _, corpo = _post(
            porta,
            dashboard.CAMINHO_DO_CAMBIO,
            "isto nao e json",
            origem=f"http://127.0.0.1:{porta}",
        )
        assert status == 400
        texto = corpo.decode("utf-8")
        assert dashboard_cambio.MENSAGEM_DE_CAMBIO_INVALIDO not in texto
        assert "O QUE FAZER" in texto

    def test_o_historico_ILEGIVEL_tem_resposta_PROPRIA_e_o_arquivo_fica_INTACTO(
        self, porta: int, pasta_do_mercado: Path
    ) -> None:
        """A SEGUNDA falha possivel do POST, apontada pelo `01-03` por nome.

        `HistoricoDoCambioIlegivel` nao e culpa do que o usuario digitou — a
        frase de cambio invalido mentiria sobre a causa. E o arquivo nao pode ser
        tocado: ele e o unico registro de qual cambio valia quando.
        """
        arquivo = pasta_do_mercado / dashboard_cambio.ARQUIVO_DO_CAMBIO
        arquivo.write_text("isto nao e uma lista JSON", encoding="utf-8")
        antes = _impressao_do_arquivo(arquivo)

        status, _, corpo = _post(
            porta,
            dashboard.CAMINHO_DO_CAMBIO,
            _corpo_do_cambio("0,50"),
            origem=f"http://127.0.0.1:{porta}",
        )

        assert status == 409
        texto = corpo.decode("utf-8")
        assert dashboard_cambio.MENSAGEM_DE_CAMBIO_INVALIDO not in texto
        assert "O QUE FAZER" in texto
        assert _impressao_do_arquivo(arquivo) == antes

    def test_o_GET_dados_seguinte_a_um_POST_ja_traz_o_R_dolar(
        self, porta: int
    ) -> None:
        """O cache do CSV nao sabe nada sobre o cambio — e nao pode atrapalhar.

        Sem invalidacao, o R$ so apareceria na tela quando o `observacoes.csv`
        mudasse, o que pode demorar minutos. O usuario clicaria em salvar e nao
        veria nada acontecer.
        """
        _, _, antes = _get(porta, dashboard.CAMINHO_DOS_DADOS)
        assert json.loads(antes)["destaque"]["reais"] is None

        _post(
            porta,
            dashboard.CAMINHO_DO_CAMBIO,
            _corpo_do_cambio("0,50"),
            origem=f"http://127.0.0.1:{porta}",
        )

        _, _, depois = _get(porta, dashboard.CAMINHO_DOS_DADOS)
        reais = json.loads(depois)["destaque"]["reais"]
        assert reais is not None
        assert reais["derivado"] is True
        assert reais["texto"]

    def test_a_recusa_por_origem_NAO_le_o_corpo(self, porta: int) -> None:
        """403 ANTES do corpo, e a prova e a mesma do teto.

        Um corpo enorme vindo de uma origem estranha nao pode nem ser carregado
        na memoria: recusar depois de ler seria pagar o custo do ataque para so
        entao dizer nao.
        """
        status, _, _ = _post(
            porta,
            dashboard.CAMINHO_DO_CAMBIO,
            _corpo_do_cambio("0,50"),
            origem="https://algum-site.example",
            tamanho_declarado=dashboard.TETO_DO_CORPO_DO_POST - 1,
        )
        assert status == 403
