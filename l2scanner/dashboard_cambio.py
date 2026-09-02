"""O cambio XM -> BRL: o unico numero da tela que o jogo nao sustenta.

POR QUE ESTE MODULO E FOLHA DO LADO DO DASHBOARD
================================================
Ele NAO importa `dashboard_dados`, e `dashboard_dados` NAO importa ele. O cambio
entra no payload por PARAMETRO, e quem junta os dois e o servidor.

Nos dois sentidos seria um ciclo de import. Num sentido so — `dashboard_dados`
importando daqui — seria pior de um jeito menos obvio: `payload` e hoje uma
funcao PURA, sem disco, e ha teste de impressao digital prendendo que ela nao
muda um byte do CSV. No instante em que o modulo do dado passasse a carregar o
modulo que LE E ESCREVE arquivo, montar o JSON deixaria de ser testavel sem
disco. A separacao custa um parametro; ela compra a pureza do outro lado.

POR QUE ESTE ARQUIVO E MAIS PARANOICO QUE OS VIZINHOS
=====================================================
Todo numero desta tela sai de uma leitura do cliente do jogo, e o usuario pode
conferir olhando a tela. O cambio nao: ele e o unico numero que o jogo nao
sustenta, e ele MULTIPLICA todos os outros. Um digito errado aqui nao produz um
valor estranho — produz um valor plausivel, errado por um fator de dez ou de
mil, e a decisao de dinheiro real sai dele.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

log = logging.getLogger(__name__)

__all__ = [
    "ARQUIVO_DO_CAMBIO",
    "MENSAGEM_DE_CAMBIO_INVALIDO",
    "MOLDE_DO_CAMBIO",
    "SUFIXO_TEMPORARIO",
    "Cambio",
    "CambioInvalido",
    "HistoricoDoCambioIlegivel",
    "gravar_o_cambio",
    "interpretar_o_cambio",
    "ler_o_cambio",
]


# ===========================================================================
# O PORTAO DE DUAS CAMADAS: a FORMA antes do VALOR
# ===========================================================================

# TETO DE DIGITOS INTEIROS. Sete casas param em R$ 9.999.999 por 1 XM. O valor
# real hoje e R$ 0,50 — sete ordens de grandeza de folga e generosidade de
# sobra, e mesmo assim um teto: a colagem acidental de um numero de telefone ou
# de um id de conversa no campo e recusada em vez de virar layout quebrado e
# uma multiplicacao absurda em cima de toda a serie.
#
# ESCOLHA, NAO MEDICAO. Ninguem mediu quanto o XM pode valer; se o mercado
# enlouquecer, este numero sobe, e e uma linha.
TETO_DE_DIGITOS_INTEIROS = 7

# TETO DE CASAS DECIMAIS. Quatro casas descem a centesimo de centavo, duas
# ordens abaixo do que o usuario consegue distinguir num preco de XM. Existe
# para o mesmo fim que o de cima: por um teto em vez de deixar o campo aceitar
# qualquer comprimento.
#
# ESCOLHA, NAO MEDICAO.
TETO_DE_CASAS_DECIMAIS = 4

# A PRIMEIRA CAMADA: ela julga a FORMA, e so a forma.
#
# O QUE CADA PEDACO RECUSA, E POR QUE ELE PRECISA RECUSAR
# =======================================================
# `re.ASCII`  -> DIGITO NAO-ASCII. Sem a flag, `\d` casa com `٥` (cinco
#                arabe-indico) e `５` (cinco de largura inteira), e `Decimal`
#                converte os dois em 5. Medido nesta arvore, Python 3.12.10.
#                Isto REFUTA a linha "digitos Unicode -> recusado" da tabela da
#                pesquisa: la a recusa vinha do SEPARADOR Unicode (`٠٫٥`,
#                `０．５`), nao do digito. Um digito Unicode SOZINHO passa pelas
#                duas camadas se a flag sair.
# `^` e `$`    -> QUALQUER COISA EM VOLTA. Sem as ancoras, `re.search` acharia
#                um numero valido no meio de um texto qualquer.
# `\d{1,7}`    -> VAZIO, SINAL (`+0.5`, `-1`), SUBLINHADO (`1_0`) e EXPOENTE
#                (`1e3`), porque nenhum deles e digito. Estas tres ultimas sao
#                as formas caras: ver a medicao logo abaixo.
# `[.,]`       -> qualquer outro separador, e mais de um (`0,5,0` tem dois).
# `\d{1,4}`    -> parte decimal vazia (`0,`) e longa demais.
# grupo `?`    -> nada: o separador inteiro e opcional, entao `11` e valido.
#
# A MEDICAO QUE OBRIGA O MOLDE A EXISTIR
# ======================================
# A segunda camada SOZINHA — `Decimal(texto)`, conferindo `is_finite()` e `> 0`,
# que e a validacao que qualquer um escreveria — ACEITA estas cinco entradas
# (medido, `[VERIFICADO: probe nesta arvore, 3.12.10]`):
#
#     '1e3'             -> Decimal('1E+3')            = mil
#     '1_0'             -> Decimal('10')              = dez
#     '+0.5'            -> Decimal('0.5')
#     '1234567890123,5' -> Decimal('1234567890123.5')
#     '٥'               -> Decimal('5')               = cinco
#
# A segunda linha e a que importa. O usuario digita `1_0` querendo `1,0`, e a
# tela passa a mostrar R$ VINTE VEZES maior que o pretendido — sem erro, sem
# aviso, com toda a aparencia de estar funcionando. O sinal de alerta, quando
# acontecer em campo, sera um R$ que muda de ordem de grandeza depois de o
# usuario "so corrigir um digito".
MOLDE_DO_CAMBIO = re.compile(
    rf"^\d{{1,{TETO_DE_DIGITOS_INTEIROS}}}([.,]\d{{1,{TETO_DE_CASAS_DECIMAIS}}})?$",
    re.ASCII,
)

# A FRASE E A TRAVADA no `## Copywriting Contract` da `01-UI-SPEC.md`, e o resto
# segue a anatomia de falha fechada da casa (`mercado_registro.py:472-479`): o
# que aconteceu, que NADA foi alterado, O QUE FAZER, e o que continua
# funcionando. SEM ACENTO, como todo texto que este projeto poe na frente do
# usuario.
MENSAGEM_DE_CAMBIO_INVALIDO = (
    "Cambio nao salvo: informe um numero maior que zero, como 0,50. O cambio "
    "anterior continua valendo, e o R$ na tela continua sendo o dele: nenhum "
    "valor foi calculado a partir do texto recusado. O QUE FAZER: digite "
    "quantos reais vale 1 XM em forma decimal simples, com uma virgula ou um "
    "ponto e nada mais (0,50 ou 0.50); notacao de expoente, sublinhado e sinal "
    "nao sao aceitos porque valeriam outro numero. Enquanto isso, a leitura do "
    "mercado e o resto da pagina seguem funcionando normalmente."
)


class CambioInvalido(ValueError):
    """O texto digitado nao e um numero positivo em forma decimal simples.

    Ela carrega SEMPRE `MENSAGEM_DE_CAMBIO_INVALIDO`, e nao uma mensagem
    montada no ponto da recusa. O motivo e o mesmo do DASH-03: duas frases para
    o mesmo estado divergem no primeiro ajuste, e a que o usuario le passa a
    depender de qual ramo do `if` ele caiu.
    """

    def __init__(self, mensagem: str = MENSAGEM_DE_CAMBIO_INVALIDO) -> None:
        super().__init__(mensagem)


def _apenas_o_valor(texto: str) -> Decimal:
    """A SEGUNDA CAMADA, sozinha. Julga o VALOR, e nao a forma.

    Ela existe como funcao separada por UM motivo: o controle negativo da suite
    precisa chama-la SEM o molde na frente, para afirmar que ela aceita `1e3` e
    `1_0`. Se essa prova chamasse uma reimplementacao, ela provaria apenas que a
    reimplementacao e permissiva — que nao e a afirmacao que interessa.

    NAO CHAMAR DIRETO. O ponto de entrada e `interpretar_o_cambio`.
    """
    try:
        valor = Decimal(texto.replace(",", "."))
    except (InvalidOperation, ValueError, ArithmeticError) as erro:
        raise CambioInvalido() from erro
    if not valor.is_finite() or valor <= 0:
        raise CambioInvalido()
    return valor


def interpretar_o_cambio(texto: str) -> Decimal:
    """O texto digitado -> reais por 1 XM. Falha fechada: recusa levanta.

    A ORDEM E O PRODUTO, E ELA NAO PODE INVERTER. `MOLDE_DO_CAMBIO` julga a
    FORMA primeiro; so o que sobrevive a ele chega ao `Decimal`, que julga o
    VALOR. Inverter — ou tirar o molde — devolve exatamente a permissividade que
    ele existe para tirar: as cinco entradas medidas no comentario do molde
    voltam a ser aceitas, e uma delas vale vinte vezes o que o usuario quis
    dizer.

    O ESPACO EM VOLTA E TOLERADO, o do meio nao. `Decimal` ja ignora espaco nas
    pontas, e `conferir_o_cabecalho` (`mercado_registro.py`) ja faz `strip()` no
    mesmo espirito: colar `"0,50 "` de outra janela e um acidente comum e
    inofensivo, e recusar isso com a frase "informe um numero maior que zero"
    para quem digitou exatamente um numero maior que zero seria uma mensagem
    mentindo. O `strip()` remove SO espaco em branco — ele nao consegue
    transformar nenhuma das formas recusadas numa aceita.
    """
    limpo = texto.strip() if isinstance(texto, str) else ""
    if MOLDE_DO_CAMBIO.fullmatch(limpo) is None:
        raise CambioInvalido()
    return _apenas_o_valor(limpo)


# ===========================================================================
# A PERSISTENCIA: uma lista que SO CRESCE, escrita atomicamente
# ===========================================================================

# `.mercado/cambio.json` e o UNICO arquivo que o processo do dashboard escreve.
# O `observacoes.csv` ao lado dele e aberto so em modo leitura, e ha teste de
# impressao digital prendendo isso.
ARQUIVO_DO_CAMBIO = "cambio.json"

# O temporario mora AO LADO do destino, com o pid no nome. Ver `_escrever` para
# as duas razoes (volume e concorrencia); o sufixo e constante porque a suite
# conta o que sobrou na pasta, e derivar essa contagem de um literal repetido
# no teste faria o teste concordar com qualquer coisa.
SUFIXO_TEMPORARIO = ".tmp-"

# As chaves do registro. Nomeadas porque sao lidas em tres lugares (escrita,
# leitura e teste) e um erro de digitacao numa delas so apareceria em campo,
# como um cambio que "sumiu".
CAMPO_DO_VALOR = "reais_por_xm"
CAMPO_DO_CARIMBO = "informado_em"


class HistoricoDoCambioIlegivel(OSError):
    """O `cambio.json` existe e NAO e a lista que este programa escreve.

    Ela so aparece no caminho da ESCRITA, e existe para nao haver nenhuma acao
    destrutiva nesta fase. Na LEITURA um arquivo assim vira `None` com aviso — a
    pagina cai para "R$ indisponivel" e segue funcionando. Na escrita nao da
    para ser tao gentil: gravar por cima do que nao foi entendido APAGARIA o
    historico do usuario em silencio, e esse historico e a unica resposta a
    pergunta "qual cambio estava valendo quando".
    """


@dataclass(frozen=True)
class Cambio:
    """A taxa vigente e QUANDO ela foi informada. As duas juntas, sempre.

    O carimbo nao e enfeite de auditoria: o DASH-02 exige que todo valor em R$
    apareca na tela declarado como *informado por voce, em tal data*, e nunca
    como medido. Um `Cambio` sem `informado_em` tornaria essa frase impossivel
    de montar, e a tela passaria a exibir um numero de procedencia calada.
    """

    reais_por_xm: Decimal
    informado_em: datetime


def _escrever(caminho: Path, texto: str) -> None:
    """ESCRITA ATOMICA, o padrao que os tres escritores desta arvore ja usam.

    `calibracao.py:764-768`, `loot.py:269-280` e `acervo.py:534-549` fazem a
    mesma coisa, e a frase operacional e deles:

        `os.replace` e atomico no mesmo volume: ou fica o arquivo antigo
        inteiro, ou o novo inteiro. Nunca meio. O temporario vive AO LADO do
        destino, e nao no `%TEMP%`, porque `os.replace` entre volumes
        diferentes nao e atomico (e no Windows nem funciona).

    O PID NO NOME vem do `loot.py`: duas abas do navegador, ou duas instancias
    do dashboard, salvando ao mesmo tempo nao podem atropelar o temporario uma
    da outra.

    O `fsync` E A UNICA COISA A MAIS, e ele diverge dos tres analogos de
    proposito. Sem ele o `os.replace` e atomico quanto ao NOME mas nao quanto
    aos BYTES: numa queda de energia logo depois da troca, o diretorio pode
    apontar para um arquivo cujo conteudo ainda nao desceu do cache. A pesquisa
    mediu o custo em 9,18 ms — irrelevante para uma escrita por clique, e este e
    o unico arquivo que este processo escreve.

    SE ALGO FALHAR, O TEMPORARIO NAO FICA PARA TRAS. Ele nao e lido por ninguem,
    mas lixo numa pasta que nunca e podada e lixo para sempre (`acervo.py:551`).
    """
    temporario = caminho.with_name(
        f"{caminho.name}{SUFIXO_TEMPORARIO}{os.getpid()}"
    )
    try:
        with open(temporario, "w", encoding="utf-8", newline="\n") as saida:
            saida.write(texto)
            saida.flush()
            os.fsync(saida.fileno())
        os.replace(temporario, caminho)
    except OSError:
        try:
            temporario.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _historico(caminho: Path) -> list[dict]:
    """A lista crua do arquivo. Ausente -> lista vazia. Ilegivel -> LEVANTA.

    A assimetria com `ler_o_cambio` e o desenho, e nao um descuido: esta funcao
    so e chamada no caminho da ESCRITA, onde devolver lista vazia significaria
    "comece do zero por cima do que voce nao entendeu".
    """
    try:
        bruto = caminho.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    try:
        historico = json.loads(bruto)
    except ValueError as erro:
        raise HistoricoDoCambioIlegivel(
            f"O arquivo {caminho} existe e nao e uma lista JSON valida ({erro}). "
            f"NENHUM byte dele foi alterado: gravar por cima apagaria em "
            f"silencio o historico de cambios que voce ja informou. O QUE "
            f"FAZER: abra o arquivo e conserte, ou renomeie-o para o programa "
            f"criar um novo. Enquanto isso, a leitura do mercado e o resto da "
            f"pagina seguem funcionando; so o R$ fica indisponivel."
        ) from erro
    if not isinstance(historico, list):
        raise HistoricoDoCambioIlegivel(
            f"O arquivo {caminho} existe e carrega {type(historico).__name__}, "
            f"e nao a LISTA de registros que este programa escreve. NENHUM byte "
            f"foi alterado. O QUE FAZER: renomeie o arquivo para o programa "
            f"criar um novo. Enquanto isso, so o R$ fica indisponivel."
        )
    return historico


def gravar_o_cambio(pasta: Path, texto: str, agora: datetime) -> Cambio:
    """Valida o texto, APENDA o registro carimbado, e devolve o novo vigente.

    APENDA, E NAO SOBRESCREVE, E ISSO E UMA DECISAO DECLARADA. Guardar so o
    valor corrente custaria a mesma linha e perderia duas coisas:

    1. A resposta a "qual cambio estava valendo quando" (T-01-12). Hoje isso
       parece luxo; no dia em que um R$ da tela parecer errado, e a unica forma
       de saber se o cambio mudou ou se o mercado mudou.
    2. A forma que a COLETA AUTOMATICA vai preencher. O listener dos grupos de
       venda do WhatsApp (adiado para o v2, em
       `.planning/seeds/cambio-xm-brl-pelo-listener-do-whatsapp.md`) produz uma
       SERIE de cotacoes com carimbo, nao um valor. A estrutura ja esta certa.

    A ultima entrada e a vigente. Nada e sobrescrito e nada e apagado — que e o
    que a linha de "confirmacao destrutiva" do UI-SPEC afirma por extenso.

    O VALOR VIAJA COMO STRING no JSON, e a conversao esta declarada aqui porque
    e a fronteira: JSON nao tem `Decimal`. Serializar como numero faria o
    `json.load` devolver `float`, e `0.50` deixaria de ser exatamente `0.50` no
    caminho de volta — reintroduzindo, na fronteira do disco, o erro de
    representacao que o `Decimal` existe para tirar.
    """
    valor = interpretar_o_cambio(texto)  # a recusa acontece ANTES de tocar disco
    caminho = Path(pasta) / ARQUIVO_DO_CAMBIO
    historico = _historico(caminho)
    historico.append(
        {CAMPO_DO_VALOR: str(valor), CAMPO_DO_CARIMBO: agora.isoformat()}
    )
    _escrever(caminho, json.dumps(historico, indent=2, ensure_ascii=False) + "\n")
    return Cambio(reais_por_xm=valor, informado_em=agora)


def ler_o_cambio(pasta: Path) -> Cambio | None:
    """O cambio vigente, ou `None`. NUNCA levanta, NUNCA cria, NUNCA apaga.

    `None` E A FALHA FECHADA CORRETA AQUI, e nao um buraco. Sem cambio
    informado, a pagina mostra o XM normalmente e diz `R$ indisponivel —
    nenhum cambio informado`, com o campo logo abaixo. Um valor padrao chutado
    faria a tela exibir R$ com a mesma confianca de um valor informado, e a
    decisao de dinheiro real sairia de um numero que ninguem escolheu. O DASH-02
    exige isso com todas as letras: *nenhum valor padrao e chutado*.

    ARQUIVO CORROMPIDO TAMBEM DEVOLVE `None`, com aviso no log (o molde do aviso
    de linha descartada de `mercado_registro.py:576-583`: nomeia o arquivo, diz
    o motivo, e diz o que continua funcionando). E ELE NAO E APAGADO NEM
    CONSERTADO: e um arquivo de texto na pasta do usuario, ele pode te-lo
    editado a mao, e o pior aceitavel e perder o R$ da tela — nunca o registro.

    O VALOR GUARDADO ATRAVESSA O MESMO PORTAO DO CAMPO (T-01-13). Um `1e3`
    escrito a mao dentro do JSON passa por `json.loads` sem esforco; se a
    leitura confiasse no arquivo por ele ser "nosso", a validacao do formulario
    viraria enfeite contornavel por um editor de texto.
    """
    caminho = Path(pasta) / ARQUIVO_DO_CAMBIO
    try:
        bruto = caminho.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as erro:
        log.warning(
            "Nao consegui LER o %s (%s). O R$ fica indisponivel nesta volta e a "
            "pagina segue mostrando o XM normalmente; nenhum valor padrao foi "
            "chutado e o arquivo nao foi tocado.",
            caminho,
            erro,
        )
        return None

    try:
        historico = json.loads(bruto)
    except ValueError as erro:
        log.warning(
            "O %s nao e um JSON valido (%s) e por isso NENHUM cambio foi lido "
            "dele. O arquivo esta INTACTO no disco: nenhum byte foi removido, "
            "reparado ou reescrito. O QUE FAZER: conserte-o ou renomeie-o para "
            "o programa criar um novo. Enquanto isso a pagina mostra o XM "
            "normalmente e diz que o R$ esta indisponivel.",
            caminho,
            erro,
        )
        return None

    if not isinstance(historico, list):
        log.warning(
            "O %s carrega %s, e nao a LISTA de registros que este programa "
            "escreve; nenhum cambio foi lido dele e o arquivo esta INTACTO. A "
            "pagina segue mostrando o XM e diz que o R$ esta indisponivel.",
            caminho,
            type(historico).__name__,
        )
        return None

    if not historico:
        # Lista vazia nao e defeito: e "nenhum cambio informado ainda", que e
        # exatamente o que `None` significa. Avisar aqui seria ruido no log a
        # cada leitura, na maquina de quem nunca preencheu o campo.
        return None

    ultimo = historico[-1]
    try:
        valor = interpretar_o_cambio(str(ultimo[CAMPO_DO_VALOR]))
        carimbo = datetime.fromisoformat(str(ultimo[CAMPO_DO_CARIMBO]))
    except (CambioInvalido, KeyError, TypeError, IndexError, ValueError) as erro:
        log.warning(
            "O ultimo registro do %s nao passou pelo mesmo portao do campo do "
            "formulario (%s) e por isso NENHUM cambio foi lido dele. O arquivo "
            "esta INTACTO. O QUE FAZER: informe o cambio de novo pela pagina, "
            "que grava um registro novo sem apagar os antigos. Enquanto isso a "
            "pagina mostra o XM e diz que o R$ esta indisponivel.",
            caminho,
            erro,
        )
        return None

    return Cambio(reais_por_xm=valor, informado_em=carimbo)
