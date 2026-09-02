"""Um arquivo de log POR INSTANCIA, e uma rotacao que nao inunda o console.

O DEFEITO DE CAMPO, COM O TRACEBACK QUE O USUARIO COLOU
=======================================================
O usuario roda DUAS instancias do scanner (Yazalaque e Faerlina) lado a lado,
por desenho e desde a Fase 1 - e a razao inteira de AGEN-07 existir. As duas
apontavam o MESMO `RotatingFileHandler` para `logs/scanner.log`. No Windows,
`os.rename` de um arquivo que outro processo mantem ABERTO falha:

    --- Logging error ---
    Traceback (most recent call last):
      File "...\\logging\\handlers.py", line 74, in emit
        self.doRollover()
      File "...\\logging\\handlers.py", line 179, in doRollover
        self.rotate(self.baseFilename, dfn)
      File "...\\logging\\handlers.py", line 115, in rotate
        os.rename(source, dest)
    PermissionError: [WinError 32] O arquivo ja esta sendo usado por outro
    processo: 'logs\\scanner.log' -> 'logs\\scanner.log.1'
    Message: '\\n%s'
    Arguments: ('[vigiando]',)

E nao acontecia uma vez. Acontecia A CADA LINHA logada depois de o arquivo
passar do limite, porque `BaseRotatingHandler.emit` consulta `shouldRollover`
toda vez e o arquivo nunca encolhia. O console do usuario ficava inundado e o
`[vigiando]` que ele deveria estar lendo se perdia no meio. E pior que barulho:
`emit` desvia para `handleError` ANTES de chegar ao `FileHandler.emit`, entao a
linha daquele registro era PERDIDA - o oposto exato do que um arquivo de log
existe para fazer num farm de tres horas.

MEDIDO COM DOIS PROCESSOS DE VERDADE (um segurando o arquivo aberto, o outro
rotacionando; WinError 32 real, sem nenhum simulacro), dez linhas `[vigiando]`
logadas apos o limite:

    manipulador do stdlib   8 tracebacks no console, e SO os ticks 0 e 1
                            sobreviveram no arquivo - os ticks 2 a 9 sumiram
    este manipulador        1 linha de aviso, e os DEZ ticks no arquivo

Perder 8 de 10 linhas e o custo real do defeito, e ele nunca aparecia como
"perdi linhas": aparecia como um log com buracos, que e a pior evidencia
possivel para quem esta tentando descobrir por que a party sumiu.

POR QUE ESTE MODULO E FOLHA
============================
Ele nao importa NADA de dentro do pacote, pelo mesmo criterio de `raiz.py`. O
`configurar_log` roda como PRIMEIRA coisa do arranque, antes da calibracao e
antes de qualquer fonte de captura; puxar `calibracao.py` ou `calibrar.py` daqui
arrastaria `cv2` e `numpy` para dentro da decisao de "qual arquivo abrir", e
qualquer falha na cadeia deixaria o usuario sem manipulador de log justamente
no caminho em que a mensagem de recusa e a unica coisa que ele tem.

E por isso a derivacao do nome do personagem a partir do titulo da janela e
COPIADA (`calibrar.py:1544`, `cal.janela.split(" - ")[0]`), e nao importada. A
regra e uma linha; a cadeia de import que ela custaria nao e.
"""

from __future__ import annotations

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

__all__ = [
    "ARQUIVO_PADRAO",
    "ArquivoRotativoTolerante",
    "montar_arquivo_rotativo",
    "nome_da_instancia",
    "nome_do_arquivo_de_log",
]

# O nome de hoje, mantido como PADRAO de proposito.
#
# `logs/scanner.log`, `.1` e `.3` existem na maquina do usuario e ja foram
# evidencia varias vezes. Quem roda UMA instancia e nunca gravou nome nenhum
# continua escrevendo exatamente no mesmo arquivo, entao nao ha migracao, nao ha
# renomeacao e nao ha historico perdido: o nome por instancia NASCE AO LADO.
ARQUIVO_PADRAO = "scanner.log"

MAX_BYTES = 2_000_000
BACKUPS = 3

# Limite do miolo do nome. Bem abaixo dos 255 do NTFS de proposito: o caminho
# INTEIRO e que tem teto (260 por padrao no Windows), e o titulo de janela e
# texto de terceiro - o jogo pode escrever o que quiser ali.
MAXIMO_DE_CARACTERES = 32

# A peneira e uma LISTA DE PERMISSAO, e nao uma lista de proibicao. Titulo de
# janela nao e nosso: proibir `: ? * / \ < > |` deixaria passar o proximo
# caractere que o Windows recusar, mais espaco, acento e byte de controle.
_PERMITIDOS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
)


def _peneirar(nome: str) -> str | None:
    """So o que e seguro em nome de arquivo no Windows. `None` se nao sobrar."""
    limpo = "".join(c for c in nome if c in _PERMITIDOS).strip("._-")
    limpo = limpo[:MAXIMO_DE_CARACTERES].strip("._-")
    return limpo or None


def _do_titulo(titulo: str) -> str | None:
    """`"Yazalaque - XM Essence"` -> `"Yazalaque"`.

    Mesma regra de `calibrar.py:1544`, copiada e nao importada (ver o cabecalho
    do modulo). O titulo INTEIRO foi recusado como nome de arquivo por duas
    razoes medidas: a metade ` - XM Essence` e IDENTICA nas duas instancias,
    entao ela nao distingue nada; e ela poe espaco e hifen-com-espacos num nome
    que um humano vai digitar no console para abrir.
    """
    return _peneirar(titulo.split(" - ")[0])


def _da_calibracao(arquivo) -> str | None:
    """Uma espiada TOLERANTE no `calibration.json`. Nunca levanta.

    POR QUE NAO `Calibracao.carregar`: aquele carregador e ESTRITO de proposito
    (recusa versao de esquema diferente com `CalibracaoInvalida`) e roda depois,
    ja com o log configurado. Se a decisao do nome do arquivo dependesse dele, a
    mensagem de recusa - que e o unico texto que o usuario tem quando a
    calibracao esta torta - nao teria para onde ir, e voltaria a sair como
    traceback cru. Aqui a pergunta e outra e muito menor: "ha um nome de
    personagem escrito neste arquivo?". Nao havendo, ou nao dando para ler, cai
    no padrao e o arranque segue.

    `nome_proprio` ANTES de `janela` porque e o campo mais especifico, e porque
    e o que `calibrar.py` grava quando o usuario passa `--eu` a mao - caso em
    que o titulo da janela pode nem bater com o personagem.
    """
    if arquivo is None:
        return None
    try:
        dados = json.loads(Path(arquivo).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(dados, dict):
        return None

    proprio = dados.get("nome_proprio")
    if isinstance(proprio, str) and proprio.strip():
        peneirado = _peneirar(proprio)
        if peneirado:
            return peneirado

    janela = dados.get("janela")
    if isinstance(janela, str) and janela.strip():
        return _do_titulo(janela)
    return None


def nome_da_instancia(janela: str | None, arquivo_de_calibracao=None) -> str | None:
    """QUEM esta escrevendo neste log. `None` quando nao ha como saber.

    O CRITERIO E O NOME DO PERSONAGEM, e as alternativas caem com motivo:

    O PID (`scanner-24316.log`) foi recusado porque nao SOBREVIVE A REINICIO. Um
    arquivo novo a cada arranque faz `backupCount=3` cobrir tres arquivos de
    nada, e `scanner.log.1` para de significar "a hora anterior" - que e
    exatamente o que a pericia de campo usa. E ninguem procurando "o log do
    Yazalaque" reconhece um numero de processo.

    O TITULO INTEIRO DA JANELA foi recusado porque metade dele (` - XM Essence`)
    e igual nas duas instancias e nao distingue nada, e porque titulo aceita
    `:` e `?`, que o Windows recusa em nome de arquivo.

    O NOME DO PERSONAGEM ganha nos tres criterios de uma vez: e estavel entre
    arranques (a rotacao volta a acumular historia de verdade), e legivel, e e
    exatamente o campo que o usuario ja digita para separar as duas instancias.

    A ORDEM DAS FONTES SEGUE A CONFIANCA:

    1. `--janela "Yazalaque - XM Essence"` explicito. E o que o proprio usuario
       digitou AGORA para dizer qual cliente esta vigiando: nada no disco pode
       saber mais do que isso.
    2. O `calibration.json`. Cobre os DOIS arranques em que o passo 1 nao diz
       nada: `--janela` sem valor (que vira `"AUTO"`, e e como o
       `vigiar-party.bat` sobe) e o caminho `mss`, sem `--janela` nenhum. Sem
       este passo a instancia mais comum do usuario ficaria sem nome.
    3. Nada. Devolve `None`, e o chamador cai em `scanner.log` - o nome de
       hoje, sem regressao para quem roda uma instancia so.

    O caminho `mss` sem calibracao com nome cai no passo 3 e isso e HONESTO: ali
    nao existe janela nomeada, e inventar um rotulo seria um nome de arquivo que
    nao corresponde a personagem nenhum. Quando duas instancias caem juntas no
    passo 3, quem segura o estrago e o `ArquivoRotativoTolerante` abaixo.
    """
    if janela and janela != "AUTO":
        do_argumento = _do_titulo(janela)
        if do_argumento:
            return do_argumento
    return _da_calibracao(arquivo_de_calibracao)


def nome_do_arquivo_de_log(janela: str | None, arquivo_de_calibracao=None) -> str:
    """O nome do arquivo, ja resolvido. Sempre devolve algo abrivel."""
    nome = nome_da_instancia(janela, arquivo_de_calibracao)
    return f"scanner-{nome}.log" if nome else ARQUIVO_PADRAO


class ArquivoRotativoTolerante(RotatingFileHandler):
    """Uma rotacao que falha NO MAXIMO UMA VEZ, e nunca perde a linha.

    O DESFECHO ESCOLHIDO: desistir da rotacao, continuar escrevendo no mesmo
    arquivo, e avisar UMA vez - no console e dentro do proprio log.

    As alternativas, e por que cada uma e pior:

      - Deixar o traceback sair (o estado de hoje): inunda o console a cada
        linha logada, para sempre, e PERDE o registro daquela linha. Ver o
        cabecalho do modulo.
      - Calar e seguir sem avisar: o arquivo passa a crescer sem teto e ninguem
        sabe. Silencio treina o usuario a confiar num sinal que nao significa
        mais nada, que e a mesma doutrina que `avisar_falha` ja segue para a
        entrega no Chatwoot.
      - Derrubar o scanner: um problema de LOG nao pode matar a vigilancia da
        party. O log e o acessorio; o alerta de morte e o produto. Este e o
        mesmo trilho de `montar_gravador` e `montar_despachante` - tenta,
        degrada com log, deixa o scanner subir.

    A DESISTENCIA E ESTRUTURAL, E NAO UM CONTADOR DE AVISOS. `maxBytes = 0` faz
    o `shouldRollover` do stdlib devolver `False` para sempre, entao
    `doRollover` nao e chamado uma segunda vez: nao ha 3.600 tentativas
    silenciosas de renomear por hora a 1 Hz, e nao ha estado extra para alguem
    esquecer de conferir.

    Com um arquivo por instancia isto vira raro, mas nao impossivel: o usuario
    pode subir dois scanners do MESMO personagem por engano, e ai os dois
    apontam de novo para o mesmo caminho.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rotacao_desistiu = False

    def doRollover(self) -> None:
        if self.rotacao_desistiu:
            return
        try:
            super().doRollover()
        except OSError as erro:
            # `OSError` e nao `PermissionError`: o WinError 32 das duas
            # instancias e so o caso conhecido. Disco cheio (ENOSPC) e o
            # antivirus segurando o arquivo entram pela mesma porta, e prender
            # so o `PermissionError` deixaria os outros dois voltarem a inundar
            # o console exatamente como antes.
            self._desistir_da_rotacao(erro)

    def _desistir_da_rotacao(self, erro: OSError) -> None:
        self.rotacao_desistiu = True
        self.maxBytes = 0

        # `doRollover` fecha o fluxo ANTES de renomear, entao a esta altura ele
        # e `None`. Sem reabrir aqui, a linha que disparou a rotacao dependeria
        # do socorro do `FileHandler.emit` - que existe, mas e detalhe interno
        # de outra classe. Reabrir e explicito e barato.
        if self.stream is None:
            self.stream = self._open()

        aviso = (
            f"Nao consegui rotacionar {self.baseFilename}: {erro}. "
            "No Windows isso quase sempre e OUTRO scanner com o mesmo arquivo "
            "aberto. Sigo escrevendo NESTE arquivo, sem rotacionar, e nao "
            "repito este aviso. Para voltar a rotacionar, de um nome proprio a "
            'cada instancia: --janela "Personagem - XM Essence".'
        )

        # NO CONSOLE E DENTRO DO ARQUIVO, e as duas por razoes diferentes. O
        # console e para o usuario que esta olhando agora; o arquivo e para a
        # pericia de daqui a seis meses, que vai abrir um log que parou de
        # rotacionar sem nenhuma pista do porque - e um log que parou de
        # rotacionar e um log que pode ter engolido o resto da sessao.
        #
        # ESCRITA DIRETA NO FLUXO, e nunca `log.warning`: um registro emitido de
        # dentro do `emit` deste mesmo manipulador reentra aqui.
        print(aviso, file=sys.stderr)
        try:
            registro = logging.LogRecord(
                name="l2scanner", level=logging.WARNING, pathname=__file__,
                lineno=0, msg="%s", args=(aviso,), exc_info=None,
            )
            self.stream.write(self.format(registro) + self.terminator)
            self.flush()
        except (OSError, ValueError):
            # O arquivo sumiu debaixo dos pes. O console ja recebeu o aviso, e
            # derrubar o scanner por causa da anotacao do aviso seria trocar um
            # log incompleto por uma party sem vigia.
            pass


def montar_arquivo_rotativo(
    pasta,
    *,
    janela: str | None = None,
    arquivo_de_calibracao=None,
    max_bytes: int = MAX_BYTES,
    backups: int = BACKUPS,
) -> ArquivoRotativoTolerante:
    """O manipulador de arquivo do arranque, ja com dono e ja tolerante."""
    caminho = Path(pasta) / nome_do_arquivo_de_log(janela, arquivo_de_calibracao)
    return ArquivoRotativoTolerante(
        caminho, maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
    )
