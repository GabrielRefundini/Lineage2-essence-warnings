"""O dado do dashboard: le o CSV ao vivo e monta o JSON. UMA fonte, UMA conta.

O QUE ESTE MODULO NAO FAZ, E E ISSO QUE O DEFINE
=================================================
Ele nao tem parser proprio e nao tem formatador proprio. O parser continua sendo
`mercado_registro.observacoes_do_arquivo`; a aritmetica continua sendo
`mercado_analise`; as frases continuam saindo de `mercado_console`. O DASH-03 e
literalmente isto: "mesma fonte, mesma conta, sem um segundo parser".

O que ele acrescenta e SO a leitura AO VIVO — o mercado le o arquivo uma vez, no
arranque; o dashboard le a cada pedido, com o escritor ainda rodando — e a
montagem do dicionario que vira JSON.

ELE E PURO QUANTO DA: sem servidor, sem relogio proprio (o `agora` entra por
parametro), sem escrita. A unica coisa que ele toca no disco e uma leitura em
modo `"r"`, e ha teste de impressao digital prendendo isso.

O INVARIANTE DE LEITURA, ESCRITO POR EXTENSO (DASH-01 / T-01-04)
=================================================================
**Nenhuma funcao deste modulo abre arquivo fora do modo de leitura, e nenhuma
cria pasta.** `RegistroDeObservacoes.carregar` cria o `observacoes.csv` ausente
com cabecalho porque ela e o arranque do ESCRITOR; aqui nao ha escritor nenhum.
Criar o arquivo ou a pasta seria o programa ESCREVENDO num caminho de LEITURA —
o mesmo argumento com que `conferir_o_terminador` recusa truncar a cauda no
disco em vez de "consertar" o arquivo do usuario. Um arquivo que aparece sozinho
porque alguem abriu o dashboard e um efeito colateral que ninguem pediu,
inclusive num diretorio apontado por engano.

DUAS PROVAS PRENDEM ISSO, e nao uma: a impressao digital de tres componentes em
300 leituras (`tests/test_dashboard_leitura.py`) prova o que aconteceu; o
tripwire por leitura de fonte sobre `observacoes_ao_vivo` e sobre
`ArquivoRecortado.open` prova o que o codigo PODE fazer, e pega a regressao no
commit em que ela e escrita.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from . import mercado_registro
from .mercado_analise import (
    ModeloDeMercado,
    menor_pedido_visivel,
    recencia_do_preco,
)
from .mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA

# O `_recencia_em_duas_formas` E PRIVADO, E MESMO ASSIM E ELE QUE VEM.
#
# Ele nasceu privado porque so o desenho do console o usava. Agora ha um segundo
# desenho, e a escolha e entre duas coisas ruins: importar um nome com
# underscore, ou escrever a mesma logica de novo aqui. A segunda e pior, e nao
# por pouco — "ha 8 h (31/08 10:00)" reescrito e exatamente o segundo formatador
# que o DASH-03 proibe, e as duas copias divergiriam no primeiro ajuste de
# limiar. O underscore vira, entao, o aviso correto: nao ha promessa de
# estabilidade nesta assinatura, e quem a mudar tem de olhar para os dois
# chamadores.
#
# Promove-lo a nome publico seria mexer em `mercado_console.py`, que a decisao
# do usuario em 2026-09-01 (CTX-2) nao autoriza esta fase a tocar.
from .mercado_console import _recencia_em_duas_formas, formatador_do_unitario

log = logging.getLogger(__name__)

__all__ = [
    "ArquivoRecortado",
    "LeituraAoVivo",
    "NOTA_DE_LINHA_PARCIAL",
    "observacoes_ao_vivo",
    "payload",
]


# ===========================================================================
# AS FRASES DA TELA — TODAS CONSTANTES NOMEADAS, TODAS DO PYTHON
# ===========================================================================
#
# ELAS SAO COPIA LITERAL DO `## Copywriting Contract` DO `01-UI-SPEC.md`, e
# moram aqui em vez de literais espalhados pelo corpo das funcoes pela mesma
# razao que `UNIDADE_DA_JANELA` mora no topo de `mercado_analise`: uma frase
# escrita duas vezes e uma frase que diverge no primeiro ajuste, e a divergencia
# aparece na tela do usuario e nao no teste.
#
# ELAS LEVAM ACENTO, e as do `mercado_console` nao — isso e INTENCIONAL e esta
# escrito no UI-SPEC. O console e ASCII por escolha dele (o `cmd` do Windows abre
# em cp1252); esta pagina e HTML em UTF-8 e a moldura e nossa. O que NAO pode
# acontecer e o navegador reacentuar a string que veio pronta do console: isso
# seria o SEGUNDO formatador que o DASH-03 proibe.

# A nota da cauda ignorada. Ela viaja no payload quando `cauda_incompleta` for
# verdadeiro, e chega PRONTA ao JS.
#
# E ELA E REDE DE SEGURANCA, E NAO O CAMINHO NORMAL — a medicao esta na
# docstring de `observacoes_ao_vivo`: ZERO leituras parciais em 22.970 tentativas
# durante 200.000 appends concorrentes. Um aviso que aparecesse toda hora viraria
# ruido, e ruido e indistinguivel de defeito.
NOTA_DE_LINHA_PARCIAL = "Última linha ignorada: incompleta (o scanner estava escrevendo)."


@dataclass(frozen=True)
class ArquivoRecortado:
    """Um objeto com FORMA de `Path`, que entrega texto ja cortado.

    POR QUE ELE EXISTE
    ==================
    `observacoes_do_arquivo` recebe um `Path` e le o arquivo ela mesma
    (`mercado_registro.py:552-556`). O dashboard precisa do MESMO corpo — os
    mesmos dois portoes, as mesmas duas redes por linha — mas sobre um texto que
    ele ja cortou na ultima quebra de linha. Este adaptador e o encaixe: ele diz
    "sim, eu sou um arquivo", devolve o texto recortado no `open()`, e devolve o
    caminho REAL no `__str__`.

    AS QUATRO ROTAS, E POR QUE TRES FORAM RECUSADAS
    ===============================================
    A pesquisa desta fase listou tres saidas para reusar o corpo do parser sobre
    um texto ja cortado, e recomendou a (a). Nenhuma das tres serve:

    (a) EXTRAIR `observacoes_do_texto` DE `mercado_registro.py`, deixando
        `observacoes_do_arquivo` como uma casca que le e delega. E a mais limpa
        das quatro, e seria a escolha obvia — mas ela MEXE em
        `mercado_registro.py`, e a decisao do usuario em 2026-09-01 (CTX-2)
        nomeia `mercado_catalogo.py` como o UNICO arquivo do workstream
        `mercado` que esta fase pode tocar. Recusada por escopo, e nao por
        merito: quando o workstream `mercado` abrir de novo, esta rota deve
        substituir este adaptador.

    (b) ESCREVER O TEXTO CORTADO NUM ARQUIVO TEMPORARIO e passar o caminho dele.
        Recusada porque quebra a mensagem de erro: `conferir_o_cabecalho`
        imprime o caminho que recebeu, e o usuario leria "restaure a primeira
        linha de C:\\Users\\...\\AppData\\Local\\Temp\\tmp8f2a.csv" — um arquivo
        que nao existe mais quando ele for procurar. A instrucao da mensagem so
        vale se ela nomear o arquivo que da para abrir. Ha teste prendendo isso.

    (c) UM SEGUNDO LACO DE `csv.reader` AQUI. Recusada porque e, literalmente, o
        segundo parser que a docstring de `observacoes_do_arquivo` existe para
        nao ter: das cinco truncagens medidas byte a byte na Fase 3, DUAS
        produzem seis campos todos parseaveis, com `80` virando `8`. Duas
        implementacoes de leitura sao duas chances de uma delas nao ter o portao
        do terminador.

    (d) ESTE ADAPTADOR — a escolhida. Zero arquivo do mercado tocado, UM parser,
        os dois portoes continuam sendo chamados, e a mensagem continua nomeando
        `.mercado/observacoes.csv`.

    O PRECO, DITO EM VOZ ALTA: e um acoplamento de FORMA. Este objeto implementa
    `open`, `__str__` e `__fspath__` porque e o que `observacoes_do_arquivo` usa
    hoje; se ela passar a chamar `.stat()` ou `.exists()`, este adaptador quebra
    com `AttributeError`. O antidoto e o teste de equivalencia do tracer, que
    compara o resultado desta rota com a chamada direta do parser sobre o mesmo
    arquivo — se o corpo do parser mudar de forma, o teste cai antes do usuario.
    """

    caminho_real: Path
    texto: str

    def open(self, *args: Any, **kwargs: Any) -> io.StringIO:
        """O texto ja cortado, como se viesse do disco.

        Os argumentos sao ACEITOS E IGNORADOS de proposito: quem chama passa
        `("r", encoding="utf-8", newline="")`, e o texto ja esta decodificado e
        sem traducao de quebra de linha. Recusar os argumentos obrigaria o
        chamador a saber que nao e um `Path` de verdade, que e exatamente o que
        este objeto existe para esconder.
        """
        return io.StringIO(self.texto, newline="")

    def __str__(self) -> str:
        return str(self.caminho_real)

    def __fspath__(self) -> str:
        return str(self.caminho_real)


@dataclass(frozen=True)
class LeituraAoVivo:
    """O que uma leitura ao vivo devolve: o dado E o que houve com o arquivo.

    OS DOIS SINAIS VIAJAM COLADOS no dado, e nao ao lado dele, pela mesma razao
    que a `Evidencia` viaja dentro de cada resultado do `mercado_analise`: quem
    desenha nao pode ser obrigado a LEMBRAR de perguntar se a cauda estava
    cortada. `arquivo_ausente` e `cauda_incompleta` sao fatos sobre a procedencia
    do numero, e o rodape da tela existe para mostra-los.
    """

    observacoes: list = field(default_factory=list)
    cauda_incompleta: bool = False
    arquivo_ausente: bool = False

    # QUANTAS LINHAS DE DADO O TRECHO COMPLETO TINHA — sem o cabecalho, e
    # contando tambem as que o parser descartou.
    #
    # ELA E A PROVA DE QUE A LEITURA ACONTECEU, e e isso que a torna necessaria:
    # no estado vazio a tela precisa dizer "o arquivo foi lido: N linhas, 0 da
    # serie Adena". Sem esse numero, "0 da serie Adena" e indistinguivel de "o
    # dashboard nao conseguiu abrir o arquivo" — que e exatamente o erro que o
    # estado vazio desenhado existe para nao cometer.
    #
    # ELA CONTA REGISTROS, E NAO LINHAS DO ARQUIVO. A frase que ela alimenta poe
    # duas contagens lado a lado ("N linhas, M da serie"), e as duas tem de ser
    # da mesma especie: incluir o cabecalho de um lado e contar observacoes do
    # outro seria comparar coisas diferentes com a mesma palavra.
    #
    # E ELA CONTA A LINHA RUIM TAMBEM. A linha esta no arquivo; quem quiser saber
    # quantas sobreviveram ao parser tem `len(observacoes)` ao lado, e o log
    # NOMEIA cada uma que caiu.
    linhas_completas: int = 0


def observacoes_ao_vivo(arquivo: Path) -> LeituraAoVivo:
    """As observacoes do CSV ATE A ULTIMA LINHA COMPLETA, com o arquivo em uso.

    ESTA FUNCAO DECIDE O CONTRARIO DO QUE A FASE 3 DECIDIU, E A FASE 3 ESTAVA
    CERTA — PARA ELA
    ==================================================================
    `conferir_o_terminador` RECUSA O ARQUIVO INTEIRO quando ele nao termina em
    quebra de linha, e a docstring dela explica por que: la o leitor e o ARRANQUE
    DO ESCRITOR, que vai APENDAR em seguida. Uma cauda ambigua naquele contexto
    vira chave de dedup errada e depois preco errado gravado como bom, para
    sempre. Desligar alto e a resposta certa.

    Aqui o contexto e outro e o oposto e a resposta certa. Este processo NUNCA
    escreve neste arquivo, e o escritor legitimo esta rodando AGORA, no outro
    processo. Recusar o arquivo inteiro por causa de uma cauda de meio segundo
    apagaria o grafico da tela a cada vez que o `--mercado` estivesse no meio de
    um `write` — e o usuario veria o dashboard "quebrar" sozinho, sem causa
    visivel.

    O CORTE ACONTECE ANTES DO PORTAO, E POR ISSO O PORTAO CONTINUA EXISTINDO. O
    texto entregue ao parser termina em quebra de linha POR CONSTRUCAO, entao
    `conferir_o_terminador` e chamada e passa; `conferir_o_cabecalho` e chamada e
    continua desligando alto se o arquivo nao for mais o arquivo deste programa.
    Nenhum dos dois portoes foi afrouxado — o primeiro passou a julgar um texto
    de que a ambiguidade ja foi retirada.

    A FREQUENCIA DO CASO ESTA MEDIDA, E O ROADMAP A SUPERESTIMOU
    ============================================================
    A premissa era "leituras parciais vao acontecer o tempo todo". Ela e FALSA
    para o escritor que este projeto tem. `csv.writer.writerow` seguido de
    `flush` e UMA unica chamada de escrita, e o escritor abre, escreve, da flush
    e fecha por linha. Medido: em **22.970** leituras de cauda durante 200.000
    appends concorrentes, **ZERO** leituras sem terminador e zero erros de
    abertura. Com uma linha de 256 KB, tambem zero.

    E O ZERO E RESULTADO, E NAO CEGUEIRA DA SONDA: um controle positivo que
    escrevia a linha em DUAS chamadas com pausa no meio (`os.write` do texto,
    pausa, `os.write` do terminador) acusou **3.252 de 4.079**. A sonda enxerga
    o defeito quando ele existe; ela nao o viu porque ele nao acontece.

    O QUE ISSO MUDA: esta degradacao e REDE DE SEGURANCA, e nao o caminho
    normal. Ela existe para o arquivo editado a mao no Sheets e salvo sem quebra
    final, e para a queda de energia — nao para a corrida com o escritor, que
    medimos e nao existe. Escrever "o normal e a cauda estar cortada" no fonte
    seria carregar para as proximas fases uma premissa que a medicao ja derrubou.

    ELA NAO CAPTURA `ContratoDoArquivoQuebrado`. O portao do cabecalho continua
    desligando alto, e quem decide o que MOSTRAR nessa hora e a camada de
    payload — engolir a excecao aqui esconderia de todos os chamadores um
    arquivo que deixou de ser este arquivo.
    """
    try:
        with arquivo.open("r", encoding="utf-8", newline="") as fonte:
            bruto = fonte.read()
    except FileNotFoundError:
        # A `.mercado/` nasce vazia, e "ainda nao gravaram nada" e uma resposta
        # legitima — nao um erro. O molde e o de `observacoes_do_arquivo`, que
        # tambem devolve vazio em vez de levantar.
        return LeituraAoVivo(arquivo_ausente=True)

    if not bruto:
        # Zero bytes: nao ha byte do usuario para julgar, e tambem nao ha cauda.
        return LeituraAoVivo()

    corte = bruto.rfind("\n")
    if corte < 0:
        # NENHUMA quebra de linha no arquivo inteiro. Nao ha uma unica linha
        # completa, entao nao ha o que ler — e a cauda e o arquivo todo.
        return LeituraAoVivo(cauda_incompleta=True)

    completo = bruto[: corte + 1]
    cauda = bruto[corte + 1 :]

    return LeituraAoVivo(
        observacoes=mercado_registro.observacoes_do_arquivo(
            ArquivoRecortado(caminho_real=arquivo, texto=completo)
        ),
        # As linhas de DADO do trecho completo: tudo menos o cabecalho, e sem
        # contar as linhas em branco que o parser tambem pula. O `max` protege o
        # unico caso em que o arquivo tem cabecalho e mais nada — subtrair daria
        # `-1`, e uma contagem negativa na frase de prova seria pior que nenhuma.
        linhas_completas=max(
            0, len([linha for linha in completo.splitlines() if linha.strip()]) - 1
        ),
        # `bool(cauda)` e nao `bool(cauda.strip())`: qualquer byte depois do
        # ultimo terminador e uma linha que o programa nao consegue afirmar,
        # inclusive um punhado de espacos. O rodape prefere dizer "ignorei uma
        # cauda" de graca a esconder uma de verdade.
        cauda_incompleta=bool(cauda),
    )


def payload(pasta_do_mercado: Path, agora: datetime) -> dict:
    """O dicionario que vira o JSON de `GET /dados`. A forma minima do tracer.

    O `agora` ENTRA POR PARAMETRO, e nao sai de `datetime.now()` aqui: e o que
    torna a recencia afirmavel por teste sem congelar o relogio do processo. A
    casa ja faz isso em `mercado_console`, que recebe `agora` em toda funcao de
    desenho.

    O TEXTO NUNCA E MONTADO AQUI. Ele sai de `formatador_do_unitario(chave)`,
    que e o UNICO ponto de decisao entre a taxa da Adena e o unitario comum. Um
    `f-string` local, ou um `round` a mao, imprimiria `0,00` para a Adena com
    toda a confianca do mundo — o modo de falha mais convincente que o
    `mercado_console` tem, e ele esta documentado la.

    SEM EVIDENCIA, A RESPOSTA E O QUE FALTA — NUNCA UM NUMERO. E o caso NORMAL
    desta fase, e nao uma borda: o CSV de campo tem 92 linhas e zero da serie
    `adena#`. Um `0,00` de espaco reservado seria indistinguivel de uma taxa
    real de zero.
    """
    arquivo = pasta_do_mercado / mercado_registro.ARQUIVO_DE_OBSERVACOES
    leitura = observacoes_ao_vivo(arquivo)

    modelo = ModeloDeMercado.de_observacoes(leitura.observacoes)
    da_adena = modelo.observacoes_de(CHAVE_DA_SERIE_DA_ADENA)

    menor = menor_pedido_visivel(da_adena)
    quando = recencia_do_preco(da_adena)

    if menor.unitario is None:
        # A frase de piso e a MESMA de `mercado_console._linha_do_menor`, com o
        # mesmo `n de piso ofertas distintas`. Ela e curta o bastante para nao
        # justificar mais um import privado, e ha teste prendendo que o texto
        # nunca contem `0,00`.
        texto = (
            f"sem evidencia - {menor.evidencia.n} de "
            f"{menor.evidencia.piso} ofertas distintas"
        )
    else:
        texto = formatador_do_unitario(CHAVE_DA_SERIE_DA_ADENA)(menor.unitario)

    return {
        # O tracer conhece dois estados, e so. A tabela de PRECEDENCIA entre
        # vazio, velho, cambio ausente e contrato quebrado e do plano 01-02 —
        # antecipa-la aqui seria escrever a regra sem o teste que a cobra.
        "estado": "sem_evidencia" if menor.unitario is None else "ok",
        "gerado_em": agora.isoformat(),
        "fonte": {
            "arquivo": str(arquivo),
            "cauda_incompleta": leitura.cauda_incompleta,
            "arquivo_ausente": leitura.arquivo_ausente,
            "linhas_completas": leitura.linhas_completas,
        },
        # A frase da cauda ignorada VIAJA PRONTA. O JS a exibe como recebeu;
        # monta-la la seria a segunda copia de um texto que ja existe aqui.
        "avisos": ([NOTA_DE_LINHA_PARCIAL] if leitura.cauda_incompleta else []),
        "destaque": {
            "xm": {
                "texto": texto,
                "n": menor.evidencia.n,
                "recencia": (
                    _recencia_em_duas_formas(quando, agora)
                    if quando is not None
                    else None
                ),
            }
        },
    }
