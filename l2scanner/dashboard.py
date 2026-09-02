"""O servidor local do dashboard: `http.server` da stdlib, e nada mais.

ZERO DEPENDENCIA NOVA, e a razao e a doutrina de ZERO-INSTALL que este projeto
ja segue em `mercado_console` para recusar o `rich`: o `.bat` roda
`pip install -r requirements.txt` na primeira execucao, e cada dependencia nova
e um jeito novo de esse arranque falhar na maquina do usuario. Um servidor que
responde a um navegador local, a 1 pedido a cada 2 s, e exatamente o que a
`http.server` faz bem.

A FORMA DESTE ARQUIVO FOI MEDIDA ANTES DE ESCRITA. Nao havia servidor nenhum
nesta arvore, entao a pesquisa desta fase montou um de prova e colou a saida:
`GET /index.html -> 200 com CSP presente`, `GET /../SEGREDO.env -> 404, vazou:
False`, `shutdown+server_close+join -> 500 ms`. O que esta aqui e aquela forma,
com o minimo do tracer.

O QUE **NAO** ESTA AQUI, E DE PROPOSITO: `allow_reuse_address = False` (o bind
exclusivo), a listagem de diretorio desligada, o `POST /cambio`, o portao de
origem, o cache por `(tamanho, mtime_ns)` e o `main`. Todos sao dos planos
01-04 e 01-05, cada um com o teste que o cobra. Antecipar codigo de seguranca
sem o teste ao lado e como nao ter escrito.
"""

from __future__ import annotations

import functools
import http.server
import json
import logging
from datetime import datetime
from pathlib import Path

from . import dashboard_dados
from .raiz import RAIZ

log = logging.getLogger(__name__)

__all__ = ["CSP", "PASTA_DOS_ESTATICOS", "Manipulador", "Servidor", "montar_servidor"]

# A CSP LITERAL DO VEND-4, e o motivo de cada diretiva:
#
#   default-src 'none'  -- nada carrega por omissao; tudo abaixo e permissao
#                          EXPLICITA. E o que faz a lista ser fechada.
#   script-src 'self'   -- so `.js` servido por este processo. Proibe, junto,
#                          `<script>` inline — ha teste sobre o HTML afirmando
#                          que todo script tem `src`.
#   style-src  'self'   -- idem para `<style>` inline.
#   connect-src 'self'  -- o `fetch` do polling so fala com este servidor. Uma
#                          biblioteca vendorizada que tentasse telemetria sai
#                          bloqueada pelo navegador, e nao pela nossa confianca
#                          na leitura que fizemos do fonte dela.
#   img-src 'self' data: -- `data:` porque um icone embutido nao e rede.
#   base-uri 'none'     -- ninguem reescreve a base das URLs relativas.
#   form-action 'none'  -- nenhum `<form>` desta pagina submete para lugar
#                          nenhum. O cambio vai por `fetch`, e o plano 01-07
#                          tem de olhar esta linha antes de escrever um form de
#                          verdade: a colisao ja esta prevista.
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; "
    "connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'"
)

# Os estaticos moram DENTRO do pacote, e o caminho vem da RAIZ do projeto —
# nunca do diretorio de trabalho. `SimpleHTTPRequestHandler` sem `directory=`
# serviria o cwd, que e a raiz do repo, que contem o `.env` com o token do
# Chatwoot (T-01-01).
PASTA_DOS_ESTATICOS = RAIZ / "l2scanner" / "recursos" / "dashboard"

# O caminho do JSON. Uma constante e nao um literal espalhado: o `dashboard.js`
# tem a mesma string do outro lado, e as duas so podem divergir de um jeito —
# silenciosamente.
CAMINHO_DOS_DADOS = "/dados"


class Manipulador(http.server.SimpleHTTPRequestHandler):
    """Serve os tres estaticos e responde `GET /dados` com o payload."""

    # SEM A VERSAO DO PYTHON NO CABECALHO `Server` (T-01-02). O padrao entrega
    # `SimpleHTTP/0.6 Python/3.12.10`, que e reconhecimento de graca para quem
    # varre a rede local. `sys_version` vazio e o que remove a segunda metade.
    server_version = "L2Dashboard"
    sys_version = ""

    def __init__(self, *args, pasta_do_mercado: Path, **kwargs) -> None:
        # ANTES do `super().__init__`, e isto NAO e estilo: o construtor de
        # `BaseHTTPRequestHandler` CHAMA `handle()` dentro dele mesmo, entao
        # qualquer atributo definido depois da chamada nao existiria durante o
        # atendimento do pedido.
        self.pasta_do_mercado = pasta_do_mercado
        super().__init__(*args, **kwargs)

    def end_headers(self) -> None:
        """Os cabecalhos de seguranca em TODA resposta, estatica ou JSON.

        Aqui e nao em cada `do_*`, e a diferenca importa: `end_headers` e o
        funil por onde passa toda resposta que esta classe produz, inclusive as
        de erro (404, 501) que o `SimpleHTTPRequestHandler` gera sozinho. Pendurar
        a CSP em cada rota deixaria as respostas de erro descobertas, e elas sao
        HTML que o navegador renderiza.
        """
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_GET(self) -> None:
        # A querystring e cortada antes da comparacao: `/dados?t=1725190000` e o
        # que um navegador manda quando quer furar o cache, e um `==` cru
        # devolveria 404 para ele.
        if self.path.split("?", 1)[0] == CAMINHO_DOS_DADOS:
            self._responder_json(
                dashboard_dados.payload(self.pasta_do_mercado, datetime.now())
            )
            return
        super().do_GET()

    def _responder_json(self, conteudo: dict) -> None:
        """`ensure_ascii=False`, e o motivo e o mesmo do UI-SPEC.

        As strings vindas do Python ja estao em ASCII (`11,60 XM por milhao`), e
        as que nao estiverem sao do nosso proprio texto em pt-BR. Escapar tudo
        para `\\uXXXX` so engordaria o corpo e esconderia a divergencia de
        acentuacao que este projeto declarou INTENCIONAL.
        """
        corpo = json.dumps(conteudo, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, formato: str, *args) -> None:
        """Para o `logging` do projeto, e nao para o `stderr` cru.

        O padrao de `BaseHTTPRequestHandler` escreve direto no `stderr`, o que
        polui a suite e ignora o `scanner.log` rotativo — que e onde a forense
        deste projeto mora. `debug` e nao `info` porque uma linha por pedido, a
        cada 2 s, afogaria qualquer coisa util no arquivo.
        """
        log.debug("dashboard %s - %s", self.address_string(), formato % args)


class Servidor(http.server.ThreadingHTTPServer):
    """Uma thread por pedido, todas daemon.

    `daemon_threads` LIGADO para que um pedido pendurado nao segure o desligamento
    do processo. Sem ele, fechar o `.bat` poderia deixar o Python vivo esperando
    um `fetch` que o navegador ja abandonou.
    """

    daemon_threads = True


def montar_servidor(porta: int, pasta_do_mercado: Path) -> Servidor:
    """O servidor pronto para `serve_forever`, sem ainda estar servindo.

    ELE NAO SOBE SOZINHO, e e isso que torna a fixture de teste possivel: quem
    chama escolhe a thread, o `poll_interval` e a hora do `shutdown`.

    `porta=0` PEDE UMA PORTA EFEMERA ao sistema, e o numero de verdade sai em
    `servidor.server_address[1]`. E o que a suite usa, para nunca brigar com o
    dashboard que o usuario deixou aberto na porta fixa.

    O `functools.partial` e a unica forma de passar argumentos a esta classe: o
    `HTTPServer` INSTANCIA o manipulador a cada pedido, entao o que ele recebe e
    uma fabrica, e nao um objeto.
    """
    return Servidor(
        ("127.0.0.1", porta),
        functools.partial(
            Manipulador,
            directory=str(PASTA_DOS_ESTATICOS),
            pasta_do_mercado=Path(pasta_do_mercado),
        ),
    )
