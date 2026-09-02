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

import logging
import re
from decimal import Decimal, InvalidOperation

log = logging.getLogger(__name__)

__all__ = [
    "MENSAGEM_DE_CAMBIO_INVALIDO",
    "MOLDE_DO_CAMBIO",
    "CambioInvalido",
    "interpretar_o_cambio",
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
