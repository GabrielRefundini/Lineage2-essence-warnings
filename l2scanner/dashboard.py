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

O ENDURECIMENTO CHEGOU, E CADA PECA VEIO COM O TESTE QUE A COBRA
=================================================================
O tracer (01-01) deixou escrito que `allow_reuse_address = False`, a listagem de
diretorio desligada, o `POST /cambio`, o portao de origem, o cache por
`(tamanho, mtime_ns)` e o `main` ficariam para os planos 01-04 e 01-05, "cada um
com o teste que o cobra". Eles estao aqui agora, e `tests/test_dashboard_servidor.py`
e o teste que os cobra.

POR QUE O BIND E SO EM `127.0.0.1`, E NUNCA EM `0.0.0.0`
=========================================================
Esta maquina roda o jogo e esta na rede da casa. Um `0.0.0.0` publicaria, para
qualquer aparelho do wi-fi, um servico que LE a pasta do mercado do usuario e
ESCREVE um arquivo nela — e faria isso de graca, sem ninguem ter pedido. O
CONTEXT desta fase travou o endereco de retorno local como decisao, e o criterio
de aceitacao do 01-05 poe um portao de AST sobre o fonte deste arquivo afirmando
que a string `0.0.0.0` nao aparece nele.

**Acesso pela rede, ou pelo celular, esta explicitamente FORA do escopo desta
fase.** Nao e um esquecimento a ser corrigido num commit rapido: um servidor sem
autenticacao, com escrita em disco, exposto na rede da casa, e uma decisao de
seguranca inteira — e ela nao foi tomada. Quem for abrir isso um dia tem de
trazer autenticacao junto, e nao apenas trocar o endereco de bind.
"""

from __future__ import annotations

import argparse
import errno
import functools
import http.server
import json
import logging
import threading
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

from . import dashboard_cambio, dashboard_dados, mercado_registro
from .raiz import RAIZ

log = logging.getLogger(__name__)

__all__ = [
    "CAMINHO_DO_CAMBIO",
    "CAMINHO_DOS_DADOS",
    "CSP",
    "INTERVALO_DE_POLLING_MS",
    "MENSAGEM_DE_PORTA_OCUPADA",
    "MENSAGEM_DE_PORTA_RESERVADA",
    "PASTA_DOS_ESTATICOS",
    "PORTA_PADRAO",
    "CacheDaLeitura",
    "Manipulador",
    "Servidor",
    "main",
    "montar_servidor",
]

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

# O caminho da gravacao do cambio. Mesma razao da constante acima, com um peso a
# mais: este caminho e o UNICO deste servidor que ESCREVE em disco.
CAMINHO_DO_CAMBIO = "/cambio"


# ===========================================================================
# AS CONSTANTES DO LANCAMENTO
# ===========================================================================

# A PORTA PADRAO. Tres restricoes a prendem, e nenhuma delas e gosto:
#
# 1. ABAIXO DE 49152. Acima disso comeca a faixa dinamica, de onde o proprio
#    Windows tira portas efemeras — e ele RESERVA blocos inteiros dela para o
#    WinNAT/Hyper-V. Medido nesta maquina hoje (`netsh interface ipv4 show
#    excludedportrange protocol=tcp`): 5357, 49152-49251, 50000-50059,
#    53409-53508, 53609-53708, 53709-53808, 53918-54017, 54543-54642,
#    64051-64150. Uma porta fixa dentro de uma dessas faixas nao falha por estar
#    "em uso": ela falha por estar EXCLUIDA, e o usuario nao tem nada a fazer.
# 2. FORA DAS PORTAS DE DESENVOLVIMENTO MAIS DISPUTADAS. 3000, 5000, 8000 e 8080
#    estavam livres na medicao, mas sao exatamente as que qualquer outra
#    ferramenta que o usuario abrir vai querer. A vizinhanca 8700-8800 e quieta.
# 3. LIVRE NA MEDICAO. `8787` bindou limpo nesta maquina hoje.
#
# AS FAIXAS EXCLUIDAS MUDAM A CADA REINICIALIZACAO. Isso e o que torna a lista
# acima uma fotografia, e nao uma garantia — e e por isso que a numero 1 e uma
# faixa inteira ("abaixo de 49152") e nao uma porta especifica: escolher pela
# faixa sobrevive ao proximo boot, escolher pela lista nao.
#
# ESCOLHA, NAO MEDICAO. Ninguem mediu que 8787 e a melhor porta do mundo; ela e
# uma porta quieta que passa nas tres restricoes. Se ela colidir com alguma
# ferramenta do usuario, o `--porta` da linha de comando resolve na hora e este
# numero desce ou sobe numa linha. O lancador sonda antes de subir, e a mensagem
# de porta ocupada diz o que fazer.
PORTA_PADRAO = 8787

# O INTERVALO DE POLLING, SERVIDO DENTRO DO PAYLOAD. O CONTEXT travou "~2s"; o
# numero mora AQUI e viaja no JSON para o navegador nao ter um segundo numero
# proprio. Um intervalo escrito em dois lugares nao fica errado nos dois: fica
# errado em UM, que e o modo de falha que ninguem percebe — a pagina passa a
# consultar com uma frequencia que o servidor nao conhece, e a conversa sobre
# custo de releitura (o cache logo abaixo) passa a ser sobre um numero que nao e
# o real.
#
# ESCOLHA, NAO MEDICAO. Dois segundos e o que o CONTEXT travou para uma coleta
# que roda a 1 Hz; medir nao mudaria nada, porque o limite aqui e o quanto o
# usuario aguenta esperar para ver o numero novo, e nao o quanto a maquina
# aguenta responder.
INTERVALO_DE_POLLING_MS = 2000

# A frase da porta ocupada, na ANATOMIA DA CASA (`mercado_registro.py:472-479`):
# o que aconteceu, que NADA foi alterado, O QUE FAZER, e o que continua
# funcionando. Sem acento, como todo texto que este projeto poe na frente do
# usuario. Ela e um MOLDE porque tem de citar a porta: uma mensagem que diz
# "a porta esta ocupada" sem dizer QUAL nao ajuda quem tem duas janelas abertas.
MENSAGEM_DE_PORTA_OCUPADA = (
    "O dashboard ja esta aberto nesta maquina (porta {porta} ocupada). NADA foi "
    "alterado: nenhum arquivo seu foi tocado e a janela anterior continua "
    "funcionando normalmente. O QUE FAZER: use a aba do navegador que ja esta "
    "aberta, ou feche a janela preta anterior e abra esta de novo. Se voce quer "
    "mesmo dois dashboards, rode com --porta seguido de outro numero. Enquanto "
    "isso, a coleta do --mercado segue rodando: ela nunca dependeu do dashboard."
)

# A SEGUNDA FALHA DE BIND, e ela NAO e a mesma coisa. Medido nesta maquina hoje:
# bindar 49200 ou 53500 — dentro das faixas que o `netsh` lista como excluidas —
# levanta `PermissionError`, `errno 13`, `winerror 10013`, e NAO `10048`. Se as
# duas caissem na mesma frase, o usuario leria "o dashboard ja esta aberto" para
# uma porta em que nao ha dashboard nenhum, iria fechar janelas que nao existem,
# e a instrucao seria uma mentira educada.
MENSAGEM_DE_PORTA_RESERVADA = (
    "A porta {porta} esta RESERVADA pelo Windows nesta maquina, e por isso o "
    "dashboard nao conseguiu subir nela. Ela nao esta em uso por ninguem: o "
    "sistema simplesmente nao a empresta. NADA foi alterado. O QUE FAZER: rode "
    "com --porta seguido de outro numero (por exemplo 8788); as faixas "
    "reservadas mudam a cada reinicializacao do Windows, e voce pode ve-las com "
    "'netsh interface ipv4 show excludedportrange protocol=tcp'. Enquanto isso, "
    "a coleta do --mercado segue rodando: ela nunca dependeu do dashboard."
)


# ===========================================================================
# O CACHE DA LEITURA
# ===========================================================================

# A RESOLUCAO DO CACHE NO EIXO DO TEMPO, e ela existe porque o payload NAO
# depende so do arquivo. Ver a docstring de `CacheDaLeitura` para o defeito que
# ela evita. Um minuto e a menor unidade que qualquer texto derivado de tempo
# neste payload chega a mostrar (`ha 8 h (31/08 10:00)`), entao recalcular mais
# de uma vez por minuto nao muda um caractere do que o usuario le.
#
# ESCOLHA, NAO MEDICAO — mas com a conta escrita: a 2 s de polling, isso troca
# 30 recalculos por minuto por UM. Com o arquivo de 60.000 linhas medido na
# pesquisa (540 ms por recalculo), isso e a diferenca entre ~27% de um nucleo e
# ~0,9%, na mesma maquina que roda o jogo.
RESOLUCAO_DO_CACHE = timedelta(minutes=1)


def _truncado(instante: datetime, largura: timedelta) -> datetime:
    """O instante arredondado PARA BAIXO num multiplo de `largura`.

    A divisao INTEIRA de `timedelta` por `timedelta` devolve `int` exato — e o
    mesmo motivo pelo qual `baldes` do `dashboard_dados` usa `//` em vez de
    `total_seconds()`, que devolveria `float` e traria erro de representacao
    pela porta dos fundos (medido na pesquisa: `69713.696` contra `69713`).
    Aqui o valor nem chega a ser exibido, mas a chave de um cache tem de ser
    ESTAVEL, e `float` e a forma mais barata de fazer duas chamadas iguais
    parecerem diferentes.
    """
    return datetime.min + ((instante - datetime.min) // largura) * largura


class CacheDaLeitura:
    """O payload montado, guardado ate o arquivo (ou o minuto) mudar.

    POR QUE ELE EXISTE HOJE, SE HOJE ELE E DESNECESSARIO
    =====================================================
    Medido na pesquisa desta fase, sobre o arquivo real de 92 observacoes: uma
    leitura completa custa **0,519 ms**. A esse tamanho o cache nao paga nem o
    proprio comentario.

    Medido tambem a **60.000 linhas (2,9 MB)**: parse **366 ms** mais
    `menor+mediana+recencia` **174 ms** = **540 ms por pedido**. A 2 s de
    polling, isso e ~27% de um nucleo permanentemente ocupado — na mesma maquina
    que esta rodando o jogo, que e a maquina cujo desempenho o usuario percebe.
    O arquivo SO CRESCE, e ninguem o poda.

    Cinco linhas hoje; uma divida evitada depois. E o mesmo argumento com que a
    escrita atomica entrou no `dashboard_cambio` antes de existir uma queda de
    energia para justifica-la.

    A CHAVE NAO E SO `(tamanho, mtime_ns)`, E A DIFERENCA E UM DEFEITO REAL
    =======================================================================
    O plano pedia a chave por `(st_size, st_mtime_ns)`. Ela sozinha **congela o
    aviso de dado velho**: `payload` decide `velho` comparando `agora` com o
    carimbo da ultima observacao, entao um CSV parado as 14:10 devolveria, as
    19:00, o mesmo dicionario com `velho=False` — e a tela afirmaria frescor
    sobre um numero de cinco horas atras. Esse e literalmente o modo de falha que
    o DASH-04 e o `## Copywriting Contract` existem para proibir ("a tela nunca
    afirma 'agora'"), e ele apareceria SO depois de uma hora de janela aberta,
    que e quando ninguem esta olhando para descobrir.

    Por isso a chave carrega tambem o MINUTO de `agora` e a identidade do
    cambio. O `gerado_em`, esse, e reescrito com o instante REAL a cada resposta
    — nunca sai do cache — porque um carimbo congelado por ate 59 s seria lido
    pela pagina como servidor mudo.

    O CAMBIO ENTRA NA CHAVE, E NAO SO NO `invalidar()`
    ==================================================
    Os dois arquivos tem tempos de vida diferentes: o `observacoes.csv` cresce
    sozinho, e o `cambio.json` muda quando o usuario clica. O cache do CSV nao
    sabe nada sobre o cambio — entao o cambio entra na chave, e um cambio novo
    invalida a entrada por CONSTRUCAO, inclusive quando ele foi editado a mao no
    arquivo por fora do formulario.

    A TRAVA E DE VERDADE. `ThreadingHTTPServer` atende cada pedido numa thread, e
    duas voltas de polling podem se cruzar. Sem a trava, duas threads leriam o
    cache pela metade; com ela, duas voltas simultaneas sobre um arquivo grande
    fazem UM parse em vez de dois — o que e o ponto.
    """

    def __init__(self) -> None:
        self._trava = threading.Lock()
        self._chave: tuple | None = None
        self._pronto: dict | None = None

    @staticmethod
    def _impressao(arquivo: Path) -> tuple[int, int] | None:
        """`(tamanho, mtime_ns)` do CSV, ou `None` se ele nao existe.

        `None` E UMA CHAVE VALIDA, e nao um erro: "o arquivo nao existe" e um
        estado que o `payload` sabe representar (`arquivo_ausente`), e ele
        tambem merece cache. Quando o arquivo nascer, a impressao deixa de ser
        `None` e a chave muda sozinha.
        """
        try:
            estado = arquivo.stat()
        except OSError:
            return None
        return (estado.st_size, estado.st_mtime_ns)

    @staticmethod
    def _identidade_do_cambio(cambio) -> tuple | None:
        """O cambio reduzido ao par que o payload usa. `None` continua `None`.

        `str(reais_por_xm)` e nao o `Decimal`: a chave vive num `dict` e precisa
        ser hashavel e estavel, e `Decimal('0.50')` e `Decimal('0.5')` sao
        valores diferentes que o usuario digitou diferente — a string preserva
        essa distincao sem inventar uma comparacao numerica que ninguem pediu.
        """
        if cambio is None:
            return None
        return (str(cambio.reais_por_xm), cambio.informado_em)

    def invalidar(self) -> None:
        """Esquece o que estava guardado. Chamado apos uma gravacao de cambio.

        REDUNDANTE COM A CHAVE NO CAMINHO NORMAL, e de proposito: a chave ja
        carrega a identidade do cambio, entao o `GET /dados` seguinte a um POST
        bem-sucedido ja recalcularia. Esta linha cobre o caso em que a gravacao
        mudou algo que a chave NAO ve, e custa uma chamada por clique.
        """
        with self._trava:
            self._chave = None
            self._pronto = None

    def pronto(self, pasta_do_mercado: Path, agora: datetime, cambio=None) -> dict:
        """O payload de `GET /dados`, do cache ou recalculado.

        O `gerado_em` E SEMPRE O INSTANTE DE VERDADE, mesmo quando o resto veio
        do cache: ele e o unico campo que a pagina pode usar para saber se o
        servidor respondeu agora, e um valor de ate um minuto atras seria lido
        como servidor mudo.

        O `intervalo_de_polling_ms` E ACRESCENTADO AQUI, e nao no
        `dashboard_dados`, porque ele nao e um dado do mercado: e um parametro do
        TRANSPORTE, e quem o conhece e quem serve. `payload` continua puro e
        continua testavel sem servidor.
        """
        arquivo = pasta_do_mercado / mercado_registro.ARQUIVO_DE_OBSERVACOES
        chave = (
            self._impressao(arquivo),
            _truncado(agora, RESOLUCAO_DO_CACHE),
            self._identidade_do_cambio(cambio),
        )
        with self._trava:
            if chave != self._chave or self._pronto is None:
                self._pronto = dashboard_dados.payload(pasta_do_mercado, agora, cambio)
                self._chave = chave
            guardado = self._pronto
        # A copia RASA e a resposta: as chaves aninhadas sao compartilhadas com a
        # entrada do cache e ninguem as altera, mas as duas de cima trocam a cada
        # resposta e nao podem ser escritas dentro do que esta guardado.
        return {
            **guardado,
            "gerado_em": agora.isoformat(),
            "intervalo_de_polling_ms": INTERVALO_DE_POLLING_MS,
        }


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

    def list_directory(self, path):
        """A LISTAGEM DE DIRETORIO NUNCA APARECE. Sempre 404.

        Sem esta sobrescrita, um `GET` de um diretorio SEM arquivo de indice —
        `/vendor/`, por exemplo — devolve a ARVORE DE ARQUIVOS em HTML. Isso nao
        vaza nada de fora da pasta dos estaticos (o `directory=` continua
        valendo), mas entrega de graca o inventario do que existe la dentro,
        inclusive nomes de arquivos que uma versao futura acrescente sem ninguem
        pensar no assunto.

        404 E NAO 403, de proposito: "existe mas voce nao pode ver" e uma
        informacao; "nao existe" nao e. Nao ha aqui um usuario a quem explicar a
        diferenca — o unico cliente legitimo e a nossa propria pagina, que nunca
        pede um diretorio.
        """
        self.send_error(404, "File not found")
        return None

    def do_GET(self) -> None:
        # A querystring e cortada antes da comparacao: `/dados?t=1725190000` e o
        # que um navegador manda quando quer furar o cache, e um `==` cru
        # devolveria 404 para ele.
        if self.path.split("?", 1)[0] == CAMINHO_DOS_DADOS:
            # O CAMBIO ENTRA POR PARAMETRO, e e AQUI que os dois modulos folha se
            # encontram — em nenhum outro lugar. `dashboard_dados` nao importa
            # `dashboard_cambio` e vice-versa; quem junta os dois e o servidor, e
            # e isso que mantem os dois testaveis um sem o outro.
            self._responder_json(
                self.server.cache.pronto(
                    self.pasta_do_mercado,
                    datetime.now(),
                    dashboard_cambio.ler_o_cambio(self.pasta_do_mercado),
                )
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
    """Uma thread por pedido, todas daemon, e a porta NAO roubavel.

    `daemon_threads` LIGADO para que um pedido pendurado nao segure o desligamento
    do processo. Sem ele, fechar o `.bat` poderia deixar o Python vivo esperando
    um `fetch` que o navegador ja abandonou.
    """

    # O BIND EXCLUSIVO. ISTO NAO E ESTILO, E A MEDICAO ESTA LOGO ABAIXO.
    #
    # `HTTPServer` liga `allow_reuse_address` por PADRAO — medido nesta arvore
    # hoje, `http.server.HTTPServer.allow_reuse_address` vale `1`. No Windows,
    # `SO_REUSEADDR` nao significa "reaproveitar um socket em TIME_WAIT", como
    # significa no Unix: ele significa ROUBAR a porta de quem ja esta escutando.
    #
    # Medido nesta arvore hoje, reproduzindo a pesquisa desta fase:
    #
    #     allow_reuse_address padrao de HTTPServer: 1
    #     primeiro bind OK ('127.0.0.1', 8791)
    #     !!! SEGUNDO BIND TAMBEM PASSOU ('127.0.0.1', 8791)
    #     com allow_reuse_address=False: OSError errno=10048 winerror=10048
    #
    # O usuario da dois cliques no `.bat` duas vezes. Com o padrao, NENHUM erro
    # aparece: sobem dois servidores na mesma porta, e quem responde ao navegador
    # e quem ganhar a corrida do `accept`. O sintoma em campo e um numero que
    # "as vezes atrasa" e dois `python.exe` no gerenciador de tarefas — um
    # defeito que nao da para diagnosticar de dentro do programa.
    #
    # Com `False`, o segundo bind levanta `errno 10048`, e um erro e a UNICA
    # coisa que da para mostrar ao usuario. `MENSAGEM_DE_PORTA_OCUPADA` e a
    # traducao dele.
    allow_reuse_address = False

    # `allow_reuse_port` NAO E TOCADO, e isso e deliberado. Ele existe desde o
    # 3.11 (medido: `hasattr` verdadeiro, valor `False`) e mapeia `SO_REUSEPORT`,
    # que NAO EXISTE no Windows. Mexer nele aqui seria escrever uma linha que nao
    # faz nada na unica plataforma em que este programa roda.

    daemon_threads = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # O CACHE MORA NO SERVIDOR, e nao no manipulador, porque o
        # `HTTPServer` INSTANCIA UM MANIPULADOR NOVO A CADA PEDIDO — um cache
        # ali dentro nasceria vazio toda vez e seria um cache com cara de cache.
        self.cache = CacheDaLeitura()


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


# ===========================================================================
# O LANCAMENTO
# ===========================================================================


def main(argv: list[str] | None = None) -> int:
    """Sobe o dashboard, abre o navegador, e serve ate `Ctrl+C`.

    ELE DEVOLVE UM CODIGO, E NAO LEVANTA. Quem chama e um `.bat` na frente de um
    usuario que nao programa: um traceback ali nao e diagnostico, e ruido que
    esconde a unica linha que interessa. As duas falhas de bind que este projeto
    sabe nomear — porta ocupada e porta reservada pelo Windows — viram frase e
    codigo 1; o resto vira frase com o motivo do sistema operacional colado, que
    e a informacao honesta quando nao sabemos o que aconteceu.

    O `Ctrl+C` E O DESLIGAMENTO NORMAL, e nao uma excecao a tratar. Chamar
    `shutdown()` da MESMA thread que rodava `serve_forever` parece um travamento
    esperando para acontecer — mas nao e, e isto foi MEDIDO nesta arvore hoje:
    o `finally` de `serve_forever` marca o evento de parada antes de a excecao
    subir, entao o `shutdown()` seguinte volta em 0,0000 s. `server_close()`
    depois dele e o que devolve a porta ao sistema.
    """
    analisador = argparse.ArgumentParser(
        prog="python -m l2scanner.dashboard",
        description=(
            "Abre o dashboard do mercado no navegador, em 127.0.0.1. Somente "
            "leitura do observacoes.csv; a unica escrita e o cambio.json."
        ),
    )
    analisador.add_argument(
        "--porta",
        type=int,
        default=PORTA_PADRAO,
        help=f"porta local (padrao: {PORTA_PADRAO})",
    )
    analisador.add_argument(
        "--sem-navegador",
        action="store_true",
        help="sobe o servidor sem abrir o navegador",
    )
    opcoes = analisador.parse_args(argv)

    try:
        servidor = montar_servidor(opcoes.porta, mercado_registro.PASTA_DO_MERCADO)
    except OSError as erro:
        # As duas familias sao SEPARADAS de proposito: ver
        # `MENSAGEM_DE_PORTA_RESERVADA` para a medicao que mostra que elas
        # chegam com `errno` diferentes e pedem instrucoes diferentes.
        if erro.errno == errno.EADDRINUSE:
            print(MENSAGEM_DE_PORTA_OCUPADA.format(porta=opcoes.porta))
        elif erro.errno == errno.EACCES:
            print(MENSAGEM_DE_PORTA_RESERVADA.format(porta=opcoes.porta))
        else:
            print(
                f"Nao consegui subir o dashboard na porta {opcoes.porta}: "
                f"{erro}. NADA foi alterado. O QUE FAZER: tente outra porta com "
                f"--porta seguido de um numero. Enquanto isso, a coleta do "
                f"--mercado segue rodando: ela nunca dependeu do dashboard."
            )
        return 1

    endereco = f"http://127.0.0.1:{servidor.server_address[1]}/"
    print(f"Dashboard no ar: {endereco}")
    print("Para fechar, volte nesta janela e aperte Ctrl+C.")
    if not opcoes.sem_navegador:
        webbrowser.open(endereco)

    try:
        servidor.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("\nDashboard encerrado. Nenhum arquivo foi alterado por esta janela.")
    finally:
        servidor.shutdown()
        servidor.server_close()
    return 0


# O BLOCO DE EXECUCAO DIRETA, e ele e o DASH-06 virando estrutura: o lancador
# chama `python -m l2scanner.dashboard`, e por isso `l2scanner/__main__.py` — que
# e o caminho do `--mercado` — nao precisa mudar UMA LINHA para o dashboard
# existir. Derrubar um nao derruba o outro porque eles nao se encontram.
if __name__ == "__main__":  # pragma: no cover - exercitado pelo lancador
    raise SystemExit(main())
