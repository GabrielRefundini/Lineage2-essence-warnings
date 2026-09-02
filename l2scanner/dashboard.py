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
    "TETO_DO_CORPO_DO_POST",
    "CacheDaLeitura",
    "Manipulador",
    "Servidor",
    "main",
    "montar_servidor",
    "origem_permitida",
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
# O PORTAO DE ORIGEM — a defesa que a CSP NAO cobre
# ===========================================================================

# O NOME DO CAMPO NO CORPO DO POST. Constante e nao literal: o `dashboard.js` tem
# a mesma string do outro lado.
CAMPO_DO_POST = "cambio"

# O TETO DO CORPO DO POST. O maior corpo LEGITIMO e o envelope JSON em volta de
# um valor de no maximo `TETO_DE_DIGITOS_INTEIROS + 1 + TETO_DE_CASAS_DECIMAIS`
# = 12 caracteres, o que da algo em torno de 30 bytes. Mil e vinte e quatro e
# umas trinta vezes isso: folga demais para recusar qualquer pedido honesto, e
# ainda assim um teto — o `Content-Length` e conferido ANTES da leitura, entao um
# corpo de um megabyte nunca chega a existir na memoria deste processo.
#
# ESCOLHA, NAO MEDICAO. Ninguem mediu quanto corpo esta maquina aguenta; o ponto
# nao e capacidade, e recusar de graca o que so pode ser ataque ou defeito.
TETO_DO_CORPO_DO_POST = 1024

# O CABECALHO MODERNO que os navegadores mandam dizendo se o pedido saiu do mesmo
# sitio. Nomeado porque ele e lido em um lugar e afirmado no teste, e um erro de
# digitacao aqui abriria o portao em silencio — `get` de um nome errado devolve
# `None`, e `None` cai no ramo permissivo.
CABECALHO_DO_DESTINO = "Sec-Fetch-Site"
DESTINO_DA_MESMA_ORIGEM = "same-origin"


def origem_permitida(cabecalhos, porta: int) -> bool:
    """O UNICO ponto de decisao do portao. Funcao PURA, e por isso afirmavel.

    O ACHADO QUE NENHUM DOCUMENTO ANTERIOR DESTA FASE LEVANTOU
    ===========================================================
    A politica de seguranca de conteudo (a CSP, VEND-4) protege a NOSSA pagina de
    carregar coisa de fora. Ela **nao** impede uma pagina de fora de mandar um
    POST para a NOSSA API. Qualquer aba aberta no navegador do usuario —
    incluindo um anuncio dentro de um site qualquer — pode disparar um pedido
    para `127.0.0.1`, e o navegador vai entregar.

    Numa maquina onde o `.env` com o token do Chatwoot mora ao lado, uma API
    local que ESCREVE arquivo sem conferir quem pediu e uma superficie de
    verdade. A conferencia custa oito linhas e e afirmavel em teste — basta
    mandar um `Origin` errado e exigir 403 —, e por isso ela existe.

    OS DOIS SINAIS SAO CONFERIDOS, E NAO O PRIMEIRO QUE CASAR
    =========================================================
    `Sec-Fetch-Site` e o sinal moderno, e o navegador o preenche sozinho: o
    codigo da pagina nao consegue forja-lo. Quando ele estiver presente e disser
    qualquer coisa que nao seja mesma origem, a resposta e nao — mesmo que o
    `Origin` esteja certo.

    A AUSENCIA DELE, NO ENTANTO, NAO PODE VIRAR NENHUM DOS DOIS EXTREMOS. Exigir o
    cabecalho recusaria todo cliente que nao o envia (um `curl` do proprio
    usuario, um navegador antigo); ignora-lo quando ele diz "cross-site" jogaria
    fora o unico sinal infalsificavel. Por isso: presente, ele manda; ausente, a
    decisao cai para o `Origin`. As duas metades tem assercao propria no controle
    negativo, porque as duas sao omissiveis sem a suite reclamar.

    SO `127.0.0.1`, E NAO `localhost`
    ==================================
    O lancador abre o navegador em `http://127.0.0.1:<porta>/`, entao o caminho
    honesto sempre casa. Aceitar tambem `localhost` acrescentaria um nome que
    passa por resolucao de DNS — e um nome resolvivel e a porta de entrada
    classica para um site externo apontar um dominio proprio para o endereco
    local. O numero nao resolve nada; ele so e.

    `cabecalhos` E O `email.message.Message` DE `self.headers`, e o `.get` dele e
    insensivel a caixa — que e obrigatorio, porque `origin:` em minusculas e um
    pedido igualmente valido.
    """
    destino = cabecalhos.get(CABECALHO_DO_DESTINO)
    if destino is not None and destino != DESTINO_DA_MESMA_ORIGEM:
        return False
    return cabecalhos.get("Origin") == f"http://127.0.0.1:{porta}"


# As frases das recusas. CADA CAUSA TEM A SUA, e isso nao e capricho: a frase de
# cambio invalido diz "informe um numero maior que zero", e serve-la para quem
# mandou um corpo ilegivel ou para quem tem um `cambio.json` corrompido
# descreveria um problema que nao e o dele — foi exatamente esse o buraco que o
# `01-03` apontou por nome ao separar `HistoricoDoCambioIlegivel` de
# `CambioInvalido`. Todas na anatomia da casa e todas sem acento.
MENSAGEM_DE_ORIGEM_RECUSADA = (
    "Pedido recusado: ele nao veio da pagina do dashboard aberta nesta maquina. "
    "NADA foi gravado e o cambio anterior continua valendo. O QUE FAZER: se voce "
    "quis salvar um cambio, use a pagina do dashboard (a que o programa abriu em "
    "127.0.0.1); se voce nao fez nada, foi outra aba do navegador tentando "
    "escrever aqui, e ela foi barrada. A leitura do mercado segue normal."
)

MENSAGEM_DE_CORPO_GRANDE_DEMAIS = (
    f"Pedido recusado: o corpo enviado passa do limite de "
    f"{TETO_DO_CORPO_DO_POST} bytes e nem chegou a ser lido. NADA foi gravado. O "
    f"QUE FAZER: o campo do cambio espera um numero curto, como 0,50 — se voce "
    f"colou um texto grande la, apague e digite so o numero. A leitura do "
    f"mercado segue normal."
)

MENSAGEM_DE_CORPO_ILEGIVEL = (
    "Cambio nao salvo: o pedido chegou num formato que este programa nao "
    "entende, e por isso nem foi interpretado como numero. NADA foi gravado e o "
    "cambio anterior continua valendo. O QUE FAZER: salve pelo campo da pagina "
    "do dashboard, que monta o pedido no formato certo. A leitura do mercado e o "
    "resto da pagina seguem funcionando."
)

MENSAGEM_DE_GRAVACAO_FALHOU = (
    "Cambio nao salvo: o programa nao conseguiu escrever o arquivo do cambio. O "
    "cambio anterior continua valendo, e nenhum arquivo seu foi alterado ou "
    "apagado. O QUE FAZER: confira se a pasta .mercado existe e nao esta somente "
    "leitura, e tente de novo. A leitura do mercado segue funcionando."
)

# A CONFIRMACAO. O `## Copywriting Contract` trava `Cambio salvo - 1 XM = R$
# 0,50, informado por voce em 01/09 14:32.`, e o texto sai DAQUI e nao do
# navegador: reescrever a frase no JS seria o segundo formatador que o DASH-03
# proibe. Sem acento, na mesma forma que o `01-03` ja deu a
# `MENSAGEM_DE_CAMBIO_INVALIDO` — as duas aparecem no MESMO canto da tela, e duas
# frases irmas com acentuacao diferente sao um defeito visivel.
MOLDE_DE_CAMBIO_SALVO = "Cambio salvo - 1 XM = R$ {valor}, informado por voce em {quando}."


def _cambio_em_texto(valor) -> str:
    """O `Decimal` virando a forma que o brasileiro le. UM lugar so.

    A VIRGULA E DECISAO DE APRESENTACAO, e ela mora aqui porque este e o unico
    ponto em que o cambio vira texto para a tela. Fazer isso no navegador seria o
    segundo formatador; fazer em dois lugares do Python seria a mesma coisa com
    outro nome.
    """
    return str(valor).replace(".", ",")


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

    def do_POST(self) -> None:
        """A UNICA escrita em disco deste servidor, e a mais defendida.

        A FALHA FECHADA MORA AQUI, NO SERVIDOR. A validacao que o `dashboard.js`
        faz no campo e CONVENIENCIA: ela evita uma ida ao servidor para um texto
        que ja da para recusar na hora, e nada mais. Um POST montado a mao, por
        fora do formulario — que e como os testes das formas perigosas fazem —
        tem de ser recusado exatamente igual, porque em campo ele vai chegar de
        onde ninguem previu.

        A ORDEM DOS PORTOES E O PRODUTO:

        1. O CAMINHO. Qualquer outro POST e 404.
        2. A ORIGEM. Recusada, responde 403 **sem ler o corpo** — pagar o custo
           de carregar o ataque na memoria para so entao dizer nao seria pagar
           duas vezes.
        3. O TAMANHO. Conferido no `Content-Length`, tambem antes da leitura.
        4. O FORMATO do corpo.
        5. O VALOR, que e o portao de duas camadas do `dashboard_cambio` — ele
           nao e repetido aqui, ele e CHAMADO.

        CADA FALHA TEM UMA RESPOSTA PROPRIA, e nunca a frase da vizinha. Ver o
        bloco de mensagens acima para a razao inteira.
        """
        if self.path.split("?", 1)[0] != CAMINHO_DO_CAMBIO:
            self.send_error(404, "File not found")
            return

        if not origem_permitida(self.headers, self.server.server_address[1]):
            log.warning(
                "POST recusado por origem (%r) vindo de %s. Nada foi gravado.",
                self.headers.get("Origin"),
                self.address_string(),
            )
            self._recusar(403, MENSAGEM_DE_ORIGEM_RECUSADA)
            return

        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            tamanho = -1
        if tamanho < 0 or tamanho > TETO_DO_CORPO_DO_POST:
            self._recusar(413, MENSAGEM_DE_CORPO_GRANDE_DEMAIS)
            return

        bruto = self.rfile.read(tamanho)
        try:
            pedido = json.loads(bruto.decode("utf-8"))
            texto = pedido[CAMPO_DO_POST]
        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            self._recusar(400, MENSAGEM_DE_CORPO_ILEGIVEL)
            return

        try:
            cambio = dashboard_cambio.gravar_o_cambio(
                self.pasta_do_mercado, texto, datetime.now()
            )
        except dashboard_cambio.CambioInvalido as erro:
            self._recusar(400, str(erro))
            return
        except dashboard_cambio.HistoricoDoCambioIlegivel as erro:
            # 409 e nao 400: o pedido esta certo, o estado do disco e que nao
            # esta. Um 400 diria ao usuario que ele digitou errado.
            self._recusar(409, str(erro))
            return
        except OSError as erro:
            log.warning("Nao consegui gravar o cambio (%s).", erro)
            self._recusar(500, MENSAGEM_DE_GRAVACAO_FALHOU)
            return

        # OS DOIS ARQUIVOS TEM TEMPOS DE VIDA DIFERENTES, e o cache do CSV nao
        # sabe nada sobre o cambio. Sem esta linha, o R$ so apareceria na tela
        # quando o `observacoes.csv` mudasse — o que pode demorar minutos —, e o
        # usuario clicaria em salvar sem ver nada acontecer.
        self.server.cache.invalidar()

        self._responder_json(
            {
                # STRING, E NAO NUMERO, e a razao e a mesma que o
                # `dashboard_cambio` escreve na fronteira do disco: JSON nao tem
                # `Decimal`. Serializar como numero faria `0.50` voltar `float`
                # do outro lado, reintroduzindo na fronteira HTTP o erro de
                # representacao que o `Decimal` existe para tirar. Aqui a
                # conversao esta declarada em voz alta, no ponto exato.
                "reais_por_xm": str(cambio.reais_por_xm),
                "informado_em": cambio.informado_em.isoformat(),
                "mensagem": MOLDE_DE_CAMBIO_SALVO.format(
                    valor=_cambio_em_texto(cambio.reais_por_xm),
                    quando=cambio.informado_em.strftime("%d/%m %H:%M"),
                ),
            }
        )

    def _recusar(self, status: int, mensagem: str) -> None:
        """A recusa em JSON, com a frase inteira no corpo.

        `close_connection` LIGADO porque as recusas de origem e de tamanho
        respondem SEM ter lido o corpo: os bytes do pedido continuam no soquete,
        e reaproveitar a conexao faria o proximo pedido comecar no meio do corpo
        do anterior. Fechar e a saida honesta.
        """
        corpo = json.dumps({"erro": mensagem}, ensure_ascii=False).encode("utf-8")
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

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
