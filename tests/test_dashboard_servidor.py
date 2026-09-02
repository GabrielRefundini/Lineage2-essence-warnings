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

from l2scanner import dashboard, dashboard_dados, mercado_registro
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
