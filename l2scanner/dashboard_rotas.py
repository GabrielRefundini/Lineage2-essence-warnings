"""As duas rotas de compra de um item, comparadas em XM exata. CALC-01/CALC-02.

A PERGUNTA, EM UMA LINHA: sai mais barato comprar este item do NPC pagando
ADENA, ou no World Exchange pagando XM?

ELE E PURO
==========
Sem disco, sem relogio proprio (o instante entra por parametro), sem impressao.
E a mesma disciplina que o cabecalho de `mercado_analise` declara e que
`dashboard_dados` repete, e ela nao e estilo: e o que permite a suite inteira
exercitar a conta sem montar servidor, sem escrever arquivo e sem congelar o
relogio do processo.

O CONTRATO COM O ITEM CONFIGURADO E POR FORMA, E NAO POR IMPORT
================================================================
Este modulo **nao importa `config`**. Ele consome qualquer objeto com tres
atributos — `nome`, `preco_npc_adena`, `quantidade_do_pacote` — e o tipo entra
so sob `TYPE_CHECKING`, no molde literal com que `mercado_analise` consome
`ObservacaoLida` e com que `dashboard_dados.payload` consome o cambio.

A razao: uma dependencia entre o CALCULO e o LEITOR DE ARQUIVO tornaria a conta
nao-testavel sem disco, e nenhum dos dois lados pediu isso. Ha teste afirmando
que importar este modulo NAO traz `l2scanner.config` junto — o contrato e
verificado, e nao so afirmado.

A UNIDADE EM QUE A CONTA ACONTECE, ESCRITA POR EXTENSO
======================================================
E a coisa que mais facilmente se erra por um fator de dez aqui, entao ela fica
escrita antes de qualquer codigo. As duas rotas terminam em **centesimos de XM
por UMA unidade do item**, e as duas chegam la por caminhos DIFERENTES:

  ROTA DO MERCADO — ja e isso de saida. `mercado_analise.unitario` sobre a serie
  do item devolve `Fraction(total_em_centesimos, quantidade)`, que e centesimos
  de XM por unidade. Nada a converter.

  ROTA DO NPC — sai de ADENA e precisa da taxa. A taxa e o unitario do menor
  pedido visivel da serie da Adena, ou seja **centesimos de XM por UMA adena** —
  exatamente o numero que o destaque da pagina ja exibe, so que la ele aparece
  multiplicado por cinco milhoes para virar legivel.

A derivacao com os numeros REAIS medidos nesta arvore em 2026-09-03, no molde da
docstring de `formatar_taxa_derivada` (que documenta a propria conta assim porque
a pesquisa dela errou por um fator de dez):

    menor pedido da Adena: 45,00 XM por 5.000.000 de adena
      -> taxa = Fraction(4500, 5_000_000) = Fraction(9, 10000)
         centesimos de XM POR ADENA

    um item de NPC a 15.000 adena o pacote, pacote de 1 unidade
      -> total do pacote = 15000 x Fraction(9, 10000) = Fraction(27, 2)
         centesimos de XM pelo pacote inteiro
      -> unitario        = Fraction(27, 2) / 1 = Fraction(27, 2)
         centesimos de XM por unidade, ou seja 13,50

    o mesmo item no mercado, menor pedido de 59,00 por unidade
      -> unitario = Fraction(5900, 1) centesimos por unidade

    o NPC sai 5.886,50 centesimos mais barato POR UNIDADE.

O ERRO POSSIVEL AQUI E MULTIPLICAR A TAXA PELA ESCALA DE EXIBICAO antes de
comparar — 5.000.000 vezes o valor certo. Ele nao daria erro em lugar nenhum:
daria um veredito invertido, bem formatado. Por isso a taxa entra crua, por
adena, e a escala de exibicao nunca aparece neste arquivo.

O ACHADO QUE DESENHA ESTE MODULO: O CAMBIO CANCELA
===================================================
As duas rotas terminam multiplicadas pelo MESMO `reais_por_xm`:

    rota NPC     = preco_npc_adena x taxa_xm_por_adena x reais_por_xm
    rota mercado = preco_mercado_xm                    x reais_por_xm

Entao **o veredito nao depende do cambio** — ele se cancela na comparacao. Por
isso a conta inteira deste modulo e em XM e **nao existe nenhum parametro de
cambio aqui**. O R$ e uma multiplicacao de EXIBICAO, e ela mora do lado de quem
exibe.

Uma versao deste modulo que comparasse em BRL perderia o veredito exatamente no
dia em que o usuario esquecesse de atualizar o cambio — que e o dia em que ele
mais precisa dele. A ausencia do parametro e a garantia estrutural disso, e nao
uma promessa em comentario.

AS QUATRO COISAS QUE ESTA CONTA **NAO** RESOLVE, EM VOZ ALTA
=============================================================
1. **Ela nao sabe se a oferta do mercado ainda existe.** Um menor pedido visivel
   de vinte minutos atras pode ter sido comprado ha dezenove. O CSV nao registra
   desaparecimento. Nenhum veredito daqui e acionavel sem o usuario conferir na
   tela — e por isso as duas rotas ficam SEMPRE visiveis, com `n` e recencia ao
   lado de cada numero.
2. **Ela nao sabe se o preco do NPC ainda e aquele.** Ele foi digitado a mao no
   `config.toml`, uma vez. E por isso que o instante da LEITURA da configuracao
   viaja ate a tela — ver `dashboard_dados`.
3. **Ela ignora a comissao do World Exchange.** A diferenca que sai daqui e
   BRUTA.
4. **Ela nao lida com quantidade minima.** Se o menor pedido do mercado e um
   lote de 100 e o usuario quer 5, ele compra 100. Usar o unitario e a
   simplificacao certa, mas AINDA E uma simplificacao.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from fractions import Fraction
from typing import TYPE_CHECKING, Sequence

from .mercado_analise import (
    N_MINIMO_PARA_MEDIANA,
    RESOLUCAO_AMBIGUA,
    RESOLUCAO_SEM_CORRESPONDENCIA,
    Evidencia,
    MedianaDosUnitarios,
    MenorPedidoVisivel,
    ModeloDeMercado,
    mediana_dos_unitarios,
    menor_pedido_visivel,
    recencia_do_preco,
    resolver_o_nome,
)
from .mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA

if TYPE_CHECKING:  # pragma: no cover - so o verificador de tipos passa aqui
    from .config import ItemDeRota

__all__ = [
    "ESTADOS_DA_ROTA",
    "MARGEM_DE_EMPATE_PERCENTUAL",
    "N_MINIMO_PARA_O_VEREDITO",
    "ROTA_DECIDIDA",
    "ROTA_EMPATADA",
    "ROTA_E_A_PROPRIA_ADENA",
    "ROTA_NOME_AMBIGUO",
    "ROTA_NUNCA_VISTA",
    "ROTA_SEM_EVIDENCIA",
    "VENCEDORA_MERCADO",
    "VENCEDORA_NPC",
    "CustoDaRota",
    "VereditoDeRota",
    "custo_da_rota_do_mercado",
    "custo_da_rota_do_npc",
    "veredito_de_uma_rota",
    "vereditos_das_rotas",
]


# ===========================================================================
# A FAIXA DE EMPATE — **ESCOLHA, E NAO MEDICAO**
# ===========================================================================

# ELA E UMA FRACAO DE UM, e nao "3" solto: `Fraction(3, 100)` e tres por cento.
# A diferenca percentual com que ela e comparada esta na MESMA escala, e as duas
# se movem juntas porque ha teste derivando a borda DESTA constante em vez de
# escrever o numero da borda a mao.
#
# POR QUE EXISTE UMA FAIXA: o veredito repousa no MENOR PEDIDO VISIVEL, que e
# **UMA oferta** — `N_MINIMO_PARA_MENOR` vale um, e vale um porque um minimo com
# uma oferta so e um fato observado, e nao uma estimativa. Eleger um vencedor por
# tres decimos por cento em cima de UMA oferta afirmaria uma precisao que o dado
# nao tem. Dentro da faixa a tela diz EMPATADO, que e a resposta honesta.
#
# O QUE FOI MEDIDO, COM O ROTULO DE QUE ISSO **NAO** MEDE A FAIXA: no
# `.mercado/observacoes.csv` real de 2026-09-03, a segunda oferta mais barata da
# serie `common-fafurion-doll#` esta cerca de 9,2% acima da mais barata, pelo
# mesmo denominador que a tela usa. Isso diz que o menor pedido visivel SE MOVE
# em dezenas por cento quando alguem compra a oferta de baixo — ou seja, que
# existe imprecisao a respeitar. **Nao diz que ela vale tres por cento.** A
# medicao que resolveria isto seria "de quanto o menor pedido de uma serie se
# move entre duas leituras consecutivas, ao longo de uma semana", e ela nao
# existe: o CSV tem oito ofertas dessa serie.
#
# ESCOLHA, NAO MEDICAO, no molde de `N_MINIMO_PARA_MEDIANA`. Se na pratica a
# tela empatar demais — ou de menos — este numero muda, e e uma linha.
MARGEM_DE_EMPATE_PERCENTUAL = Fraction(3, 100)


# ===========================================================================
# O PISO DE EVIDENCIA DO VEREDITO — **ESCOLHA, E NAO MEDICAO**
# ===========================================================================
#
# O CALC-04 diz duas coisas que, lidas cruas, parecem se contradizer: que o
# piso do veredito sao "os `N_MINIMO_*` que ja existem", e que "um veredito
# chutado sobre `n=1` seria pior que nenhum veredito". Mas `N_MINIMO_PARA_MENOR`
# **vale um**, e o veredito repousa no menor pedido visivel — reusar aquele piso
# LITERALMENTE produziria exatamente o veredito sobre uma oferta so que a mesma
# frase proibe.
#
# `N_MINIMO_PARA_MENOR` VALER UM ESTA CERTO PARA O QUE AQUELE PISO GUARDA. Um
# minimo com uma oferta so e um FATO OBSERVADO: aquele anuncio existiu, naquele
# total, naquela quantidade, naquele instante. Nao ha nada a inferir, entao nao
# ha piso a exigir — e a honestidade mora no rotulo `n=1` ao lado do numero.
#
# AQUI A PERGUNTA E OUTRA. O numero nao esta sendo EXIBIDO com o `n` ao lado:
# ele esta ELEGENDO UMA ROTA DE COMPRA, com dinheiro real do outro lado. Uma
# vencedora eleita sobre uma unica oferta e uma afirmacao sobre o mercado
# vestida de conta, e o CALC-04 a nomeia como pior que nenhuma resposta.
#
# A LIGACAO E AO PISO DA MEDIANA, E NAO A UM NUMERO NOVO. `mercado_analise` ja
# tem uma resposta para "quanta evidencia sustenta uma AFIRMACAO sobre o mercado
# deste item", e ela e `N_MINIMO_PARA_MEDIANA`. Ligar em vez de copiar mantem
# **uma autoridade so** sobre essa pergunta.
#
# A CONSEQUENCIA DA LIGACAO E DELIBERADA: no dia em que o usuario baixar o piso
# da mediana porque o console cala demais, o piso do veredito desce junto, sem
# ninguem precisar lembrar. E o contrario do que aconteceria com um `5` copiado
# a mao, que ficaria para tras em silencio.
#
# **ESCOLHA, NAO MEDICAO.** Ninguem mediu quantas ofertas distintas por serie o
# material real produz — a secao de pisos de `mercado_analise` diz isso das tres
# constantes de la, e vale igual para esta. Se um dia as duas perguntas
# precisarem de pisos DIFERENTES, esta linha vira um numero proprio, e a razao
# da separacao tem de vir escrita junto com ele.
N_MINIMO_PARA_O_VEREDITO = N_MINIMO_PARA_MEDIANA


# ===========================================================================
# OS NOMES
# ===========================================================================

# As duas vencedoras possiveis. Nomes e nao booleano, porque o empate e um
# terceiro desfecho e um `bool` obrigaria quem exibe a carregar um `None` cujo
# significado nao esta escrito em lugar nenhum.
VENCEDORA_NPC = "npc"
VENCEDORA_MERCADO = "mercado"

# OS SEIS ESTADOS DE **UMA LINHA**. Cada um se desenha diferente na tela, e
# nenhum deles some: um item configurado que sumisse seria indistinguivel de
# "esqueci de configurar".
#
# ERAM QUATRO ATE O PLANO 02-01. Os dois de baixo entraram no 02-02, e cada um
# tem a razao escrita ao lado.
ROTA_DECIDIDA = "decidida"
ROTA_EMPATADA = "empatada"
ROTA_NUNCA_VISTA = "nunca vista"
ROTA_NOME_AMBIGUO = "nome ambiguo"

# A SERIE EXISTE E TEM PRECO, MAS NAO TEM EVIDENCIA QUE SUSTENTE UMA ELEICAO.
# Ele e DIFERENTE de `ROTA_NUNCA_VISTA` e a diferenca importa na tela: em
# "nunca vista" o usuario tem de abrir a aba do item no cliente; aqui ele ja
# abriu, e o que falta e o scanner ver mais ofertas. Mandar quem ja fez a coisa
# certa fazer de novo e o defeito que este estado proprio evita.
ROTA_SEM_EVIDENCIA = "sem evidencia"

# O NOME DO ITEM RESOLVEU PARA A PROPRIA SERIE DA ADENA.
#
# O DEFEITO QUE ELE EVITA, PELO NOME: um bloco `[[dashboard.item]]` chamado
# "Adena" produziria uma comparacao de ADENA CONTRA ADENA — a rota do NPC seria
# `preco_em_adena x taxa` e a do mercado seria a MESMA taxa, ou seja um numero
# perfeitamente calculado, bem formatado, e sem significado nenhum. Nada
# quebraria em voz alta.
#
# O CRITERIO E A CHAVE RESOLVIDA CONTRA `CHAVE_DA_SERIE_DA_ADENA`, que e uma
# SENTINELA — ela nao vem de leitura nenhuma, foi escrita para carregar esta
# identidade, e por isso e o unico criterio estavel. Comparar o NOME EXIBIDO
# seria comparar texto que o OCR faz oscilar.

ROTA_E_A_PROPRIA_ADENA = "e a propria adena"

# A ORDEM E DE PRECEDENCIA, E ELA E FECHADA — no molde do bloco `ESTADOS` do
# `dashboard_dados`.
#
# VARIOS PODEM SER VERDADE AO MESMO TEMPO: um nome ambiguo tambem nao tem uma
# serie unica de onde tirar preco, e portanto tambem "nunca foi visto" no sentido
# util. A ordem escrita NUM LUGAR SO e o que impede quatro `if` em telas
# diferentes darem quatro respostas para o mesmo item.
#
# A ORDEM E A DA GRAVIDADE DA IGNORANCIA: primeiro "o nome que voce escreveu
# aponta para duas coisas" (nao da para afirmar NADA sem escolher por voce),
# depois "o nome nao aponta para nada que eu tenha visto", depois "as duas rotas
# existem e estao perto demais para eu eleger uma", e so entao "ha um vencedor".
#
# ONDE OS DOIS ESTADOS NOVOS ENTRARAM, E POR QUE NESSAS POSICOES
# ===============================================================
# `ROTA_E_A_PROPRIA_ADENA` vem **primeiro entre os estados que dependem da
# chave ja resolvida**: um item que E a propria adena nao ganha nada em ser
# avaliado por evidencia — a serie da Adena e a mais densa do arquivo, entao ele
# passaria pelo piso com folga e produziria o numero sem significado. Perguntar
# "isso e a adena?" antes de "isso tem evidencia?" e o que impede a linha de
# cair no estado errado justamente no caso em que os dados sobram.
#
# `ROTA_SEM_EVIDENCIA` vem **depois de nunca visto e antes de empatado**. Depois
# de nunca visto porque "eu nunca vi este item" e uma ignorancia mais grave que
# "eu vi pouco". Antes de empatado porque nao ha sentido em perguntar se duas
# rotas empatam quando uma delas nao tem evidencia que a sustente — o empate e
# uma AFIRMACAO ("elas custam praticamente o mesmo"), e nao um silencio.
ESTADOS_DA_ROTA = (
    ROTA_NOME_AMBIGUO,
    ROTA_NUNCA_VISTA,
    ROTA_E_A_PROPRIA_ADENA,
    ROTA_SEM_EVIDENCIA,
    ROTA_EMPATADA,
    ROTA_DECIDIDA,
)

# OS MOTIVOS, NO MOLDE DE `MargemDeCraft.motivo`. Quando o veredito quebra,
# `vencedora` e nulo e `motivo` diz O QUE faltou.
#
# POR QUE ELE EXISTE SE JA HA `estado`: e o mesmo argumento que fez
# `MargemDeCraft` carregar os dois. O `estado` e o token que a tela consome para
# ESCOLHER O DESENHO; o `motivo` e a frase curta que sobrevive num log, numa
# mensagem de erro ou numa linha copiada — e um `None` mudo obrigaria quem
# desenha a adivinhar entre QUATRO causas, que se escrevem diferente na tela.
#
# ELES SAO CURTOS E SEM ACENTO de proposito: nao sao copy de interface (essa
# mora no `dashboard_dados`), sao o rotulo tecnico da quebra.
MOTIVO_NOME_AMBIGUO = "o nome casa com mais de uma serie"
MOTIVO_NUNCA_VISTA = "nenhuma oferta comparavel desta serie"
MOTIVO_E_A_PROPRIA_ADENA = "o item resolve para a propria serie da adena"
MOTIVO_SEM_EVIDENCIA = "ofertas distintas abaixo do piso do veredito"


# ===========================================================================
# OS DOIS LADOS DA COMPARACAO
# ===========================================================================


@dataclass(frozen=True)
class CustoDaRota:
    """Um lado da comparacao, nos DOIS numeros que ele tem na vida real.

    OS TRES CAMPOS ANDAM JUNTOS PELA MESMA RAZAO DE `MenorPedidoVisivel`: um
    unitario solto e sem procedencia. O NPC vende PACOTE, e "13,50 por unidade"
    sem o "15.000 de adena por 1 unidade" ao lado nao da ao usuario como conferir
    a conta na janela do NPC.

    `unitario` E `Fraction`, SEMPRE, e o arredondamento acontece SO no
    formatador. E o mesmo D-02 que `mercado_analise.unitario` documenta: divisao
    em ponto flutuante reintroduziria erro exatamente onde a comparacao precisa
    dele zero.
    """

    unitario: Fraction
    total_do_pacote: Fraction
    quantidade: int

    # SO A ROTA DO NPC TEM ESTE CAMPO, e a assimetria e um FATO e nao um
    # esquecimento: a rota do NPC e paga em ADENA e a do mercado em XM. Este e o
    # numero que o usuario escreveu no `config.toml` e o unico que ele consegue
    # conferir na janela do NPC — o `total_do_pacote` ja esta convertido para
    # centesimos de XM e nao aparece em lugar nenhum daquela janela.
    #
    # `None` do lado do mercado, e nao zero: zero seria um preco.
    preco_em_adena: int | None = None


def custo_da_rota_do_npc(item: "ItemDeRota", taxa: Fraction) -> CustoDaRota:
    """O preco em adena convertido para centesimos de XM por unidade. EXATO.

    `taxa` E CENTESIMOS DE XM POR **UMA** ADENA — o `unitario` cru do menor
    pedido visivel da serie da Adena, e nunca o numero que a tela exibe (que ja
    esta multiplicado pela escala de cinco milhoes). Ver a derivacao no cabecalho
    deste modulo: multiplicar pela escala aqui daria um veredito invertido sem
    uma linha de erro em lugar nenhum.

    A ORDEM DAS OPERACOES NAO ARREDONDA EM PONTO NENHUM porque tudo e `Fraction`:
    o total do pacote e o preco vezes a taxa, e o unitario e o total dividido
    pela quantidade. Fazer a divisao antes ou depois da multiplicacao da o MESMO
    valor exato — o que nao seria verdade em `float`.

    A QUANTIDADE JA VEIO VALIDADA COMO MAIOR QUE ZERO pelo leitor do
    `config.toml`, entao nao ha divisao por zero a guardar aqui. Guardar de novo
    seria uma segunda autoridade sobre a mesma regra, e a segunda e a que ninguem
    atualiza.
    """
    total = Fraction(item.preco_npc_adena) * taxa
    return CustoDaRota(
        unitario=total / item.quantidade_do_pacote,
        total_do_pacote=total,
        quantidade=item.quantidade_do_pacote,
        preco_em_adena=item.preco_npc_adena,
    )


def custo_da_rota_do_mercado(menor: MenorPedidoVisivel) -> CustoDaRota:
    """O menor pedido visivel da serie do item, no mesmo denominador.

    ELE JA CHEGA NA UNIDADE CERTA: `MenorPedidoVisivel.unitario` e
    `Fraction(total_em_centesimos, quantidade)`, que e centesimos de XM por
    unidade. Nao ha conversao nenhuma deste lado, e e por isso que a rota do
    mercado nao tem como errar por fator de dez enquanto a do NPC tem.

    QUEM CHAMA JA CONFERIU QUE HA UNITARIO. Esta funcao nao aceita um menor sem
    oferta: um `CustoDaRota` com `None` dentro obrigaria toda a aritmetica
    seguinte a testar por nulo, e a linha SEM oferta ja tem estado proprio
    (`ROTA_NUNCA_VISTA`) que se desenha diferente.
    """
    return CustoDaRota(
        unitario=menor.unitario,
        total_do_pacote=Fraction(menor.total_em_centesimos),
        quantidade=menor.quantidade,
    )


# ===========================================================================
# O VEREDITO
# ===========================================================================


@dataclass(frozen=True)
class VereditoDeRota:
    """Uma linha da calculadora: as duas rotas, a vencedora, e a procedencia.

    A `Evidencia` E A IDADE VIAJAM AQUI DENTRO, e nao numa tabela paralela — a
    mesma regra que `LinhaDaMargem` ja aplica, pela mesma razao: um veredito
    apoiado numa unica oferta de tres dias atras nao vale o mesmo que um apoiado
    em vinte de agora, e quem desenha nao pode ter como esquecer de pedir.

    `npc` e `mercado` sao `None` juntos, e nunca um so. Quando o nome nao resolve
    para uma serie, nao ha rota do mercado — e uma tela com a rota do NPC sozinha
    convidaria a ler o numero dela como veredito, que e exatamente o que o estado
    da linha esta dizendo que nao da para fazer.

    `diferenca_percentual` E FRACAO DE UM (0,25 e vinte e cinco por cento), na
    mesma escala de `MARGEM_DE_EMPATE_PERCENTUAL`. Quem exibe multiplica por cem;
    guardar ja multiplicado faria a comparacao com a margem depender de duas
    escalas concordarem.

    `mediana` E **CONTEXTO, E NUNCA DECISAO**
    =========================================
    Ela responde *"o mercado deste item esta caro hoje?"*, que e uma pergunta
    DIFERENTE da que esta linha responde. A vencedora continua sendo eleita pelo
    MENOR PEDIDO VISIVEL — que e o que o usuario pagaria se comprasse agora, e e
    a decisao travada do `02-CONTEXT`. Trocar a mediana por um valor absurdo nao
    move a vencedora, e ha teste de controle medindo exatamente isso; sem ele,
    "a mediana e contexto" seria uma frase e nao um fato.
    ELA VEM COM O PROPRIO PISO DENTRO (`N_MINIMO_PARA_MEDIANA`) e a propria
    frase de falta, porque os dois pisos podem discordar: uma serie pode ter
    evidencia para o veredito e nao ter para a mediana no dia em que os dois
    numeros deixarem de ser o mesmo.

    `mediana` NUNCA E NULA, MESMO NAS QUEBRAS. `mediana_dos_unitarios` sobre
    lista vazia devolve um objeto com `unitario=None` e `Evidencia(n=0)` — o que
    FALTA, que e a resposta honesta. Um campo opcional aqui obrigaria toda tela
    a testar por nulo antes de ler um `n` que sempre existe.

    `motivo` DIZ O QUE FALTOU quando `vencedora` e nulo, e e `""` quando a linha
    decidiu. Ver o bloco dos `MOTIVO_*` acima.
    """

    estado: str
    item: str
    chave: str | None
    nome_exibido: str
    npc: CustoDaRota | None
    mercado: CustoDaRota | None
    vencedora: str | None
    diferenca_por_unidade: Fraction | None
    diferenca_percentual: Fraction | None
    evidencia: Evidencia | None
    mediana: MedianaDosUnitarios
    motivo: str
    recencia: datetime | None
    idade: timedelta | None
    candidatas: tuple[str, ...]

    @property
    def decidida(self) -> bool:
        return self.estado == ROTA_DECIDIDA


def _sem_rotas(
    estado: str,
    item: "ItemDeRota",
    nome_exibido: str,
    candidatas: tuple[str, ...],
    motivo: str,
    chave: str | None = None,
    evidencia: Evidencia | None = None,
    observacoes: Sequence = (),
) -> VereditoDeRota:
    """A linha que existe na tela e nao tem numero. Os QUATRO estados de quebra.

    ELA APARECE, e nao some. Um item configurado que sumisse da tela seria
    indistinguivel de "esqueci de configurar", e o usuario ficaria procurando um
    bloco que ja esta la (decisao travada do 02-CONTEXT).

    **NENHUM VALOR PARCIAL VIAJA JUNTO**, e a razao e a de `_margem_quebrada`:
    devolver a rota do NPC sozinha — que ate existiria, porque o preco esta no
    `config.toml` — convidaria a ler aquele numero como veredito, que e
    precisamente o que o estado da linha esta dizendo que nao da para fazer.
    Isso vale tambem para `ROTA_SEM_EVIDENCIA`: exibir os dois numeros e recusar
    a vencedora deixaria o usuario fazer a subtracao de cabeca, e a recusa
    viraria decoracao.

    A MEDIANA SAI DAQUI TAMBEM, sobre as observacoes que existirem — nas quebras
    de nome elas sao vazias e o objeto devolvido diz `0 de 5`, que e o que falta.
    """
    return VereditoDeRota(
        estado=estado,
        item=item.nome,
        chave=chave,
        nome_exibido=nome_exibido,
        npc=None,
        mercado=None,
        vencedora=None,
        diferenca_por_unidade=None,
        diferenca_percentual=None,
        evidencia=evidencia,
        mediana=mediana_dos_unitarios(observacoes),
        motivo=motivo,
        recencia=None,
        idade=None,
        candidatas=candidatas,
    )


def veredito_de_uma_rota(
    item: "ItemDeRota",
    modelo: ModeloDeMercado,
    taxa: Fraction,
    agora: datetime,
) -> VereditoDeRota:
    """As duas rotas de UM item, com a vencedora eleita em `Fraction`.

    O CASAMENTO DO NOME E `resolver_o_nome`, CHAMADO E NAO REIMPLEMENTADO
    =====================================================================
    Igualdade EXATA sobre `nome_normalizado`, com ambiguidade QUEBRANDO e
    listando as candidatas. Ele ja existe, ja tem teste, e ja carrega a razao de
    ser exato.

    **A REFUTACAO, COM O NUMERO, PORQUE A TENTACAO E REAL.** O outro caminho
    obvio seria `mercado_catalogo.similaridade` com o corte calibrado
    (`mercado_corte_de_similaridade = 0.8947`), e ele esta ERRADO aqui. Aquele
    corte foi calibrado para agrupar **duas leituras de OCR DOS MESMOS PIXELS** —
    o mesmo item lido duas vezes, com uma letra oscilando. Aplicado a texto que um
    HUMANO digitou, ele junta itens deliberadamente separados: medido no
    workstream `mercado`, ele da **0,9286 para `+3 Dragon Belt` contra `+4 Dragon
    Belt`** e **0,9375 para `B-grade Gemstone` contra `C-grade Gemstone`** — os
    dois acima do corte, os dois series distintas.

    Aplicado NESTA fase, ele juntaria **Gemstone B com Gemstone C**, que sao
    exatamente as duas primeiras instancias que esta calculadora existe para
    comparar. O usuario pediria o preco de uma e receberia o veredito da outra,
    bem formatado. O casamento exato com quebra por ambiguidade e precisamente o
    que impede isso.

    OS SEIS DESFECHOS
    =================
    - o nome casa com DUAS ou mais series -> `ROTA_NOME_AMBIGUO`, com as
      candidatas ORDENADAS. O dashboard nao escolhe por ele: escolher daria um
      numero plausivel e errado.
    - o nome nao casa com nenhuma -> `ROTA_NUNCA_VISTA`, com o nome que o USUARIO
      escreveu (e nao com a chave), porque e o texto dele que ele vai procurar no
      `config.toml` para conferir.
    - a serie casa mas nao tem oferta comparavel -> `ROTA_NUNCA_VISTA` tambem, e
      pela mesma razao pratica: nao ha preco de mercado a comparar. Uma serie so
      chega aqui sem unitario quando TODAS as ofertas dela tem quantidade nao
      positiva, que e a linha editada a mao no Sheets que `_comparaveis` ja
      descarta.
    - a chave resolvida E a da Adena -> `ROTA_E_A_PROPRIA_ADENA`.
    - a serie tem preco mas menos ofertas distintas que `N_MINIMO_PARA_O_VEREDITO`
      -> `ROTA_SEM_EVIDENCIA`, com a `Evidencia` dizendo quantas faltam.
    - as duas rotas existem e ha evidencia -> `ROTA_EMPATADA` ou `ROTA_DECIDIDA`,
      conforme a faixa.

    A `Evidencia` DO VEREDITO E CONSTRUIDA COM O PISO DO VEREDITO, e nao e a que
    veio dentro do `MenorPedidoVisivel` — aquela carrega o piso do MENOR, que
    vale um. **`piso` e um CAMPO da `Evidencia` de proposito**: construir uma com
    outro piso e o uso previsto do tipo, e nao um desvio. O campo `faltam` sai
    derivado dai, e quem exibe nao faz conta de cabeca.

    `agora` ENTRA POR PARAMETRO, e vira `idade`. Este modulo continua sem relogio
    do sistema.
    """
    resolucao = resolver_o_nome(modelo, item.nome)

    if resolucao.estado == RESOLUCAO_AMBIGUA:
        return _sem_rotas(
            ROTA_NOME_AMBIGUO,
            item,
            item.nome,
            resolucao.candidatas,
            MOTIVO_NOME_AMBIGUO,
        )

    if resolucao.estado == RESOLUCAO_SEM_CORRESPONDENCIA:
        return _sem_rotas(
            ROTA_NUNCA_VISTA, item, item.nome, (), MOTIVO_NUNCA_VISTA
        )

    chave = resolucao.chave
    observacoes = modelo.observacoes_de(chave)
    menor = menor_pedido_visivel(observacoes)
    nome_exibido = modelo.nome_exibido_de(chave)

    # A EVIDENCIA DESTE VEREDITO, com o piso DELE. Ver a docstring acima.
    evidencia = Evidencia(n=menor.evidencia.n, piso=N_MINIMO_PARA_O_VEREDITO)

    if menor.unitario is None:
        return _sem_rotas(
            ROTA_NUNCA_VISTA,
            item,
            nome_exibido,
            (),
            MOTIVO_NUNCA_VISTA,
            chave=chave,
            evidencia=evidencia,
            observacoes=observacoes,
        )

    # A ADENA VEM ANTES DA EVIDENCIA, e a razao esta no bloco de `ESTADOS_DA_ROTA`:
    # a serie da Adena e a mais densa do arquivo, entao um item chamado "Adena"
    # passaria pelo piso com folga e produziria a comparacao de adena contra
    # adena — bem formatada e sem significado nenhum.
    if chave == CHAVE_DA_SERIE_DA_ADENA:
        return _sem_rotas(
            ROTA_E_A_PROPRIA_ADENA,
            item,
            nome_exibido,
            (),
            MOTIVO_E_A_PROPRIA_ADENA,
            chave=chave,
            evidencia=evidencia,
            observacoes=observacoes,
        )

    if not evidencia.suficiente:
        return _sem_rotas(
            ROTA_SEM_EVIDENCIA,
            item,
            nome_exibido,
            (),
            MOTIVO_SEM_EVIDENCIA,
            chave=chave,
            evidencia=evidencia,
            observacoes=observacoes,
        )

    npc = custo_da_rota_do_npc(item, taxa)
    mercado = custo_da_rota_do_mercado(menor)
    quando = recencia_do_preco(observacoes)

    estado, vencedora, diferenca, percentual = _eleger(npc, mercado)

    return VereditoDeRota(
        estado=estado,
        item=item.nome,
        chave=chave,
        nome_exibido=nome_exibido,
        npc=npc,
        mercado=mercado,
        vencedora=vencedora,
        diferenca_por_unidade=diferenca,
        diferenca_percentual=percentual,
        evidencia=evidencia,
        # A MEDIANA E CONTEXTO. Ela sai da MESMA funcao que o console e o
        # grafico ja usam — uma segunda implementacao de "o tipico da serie"
        # divergiria da primeira na correcao seguinte, e as duas telas passariam
        # a discordar sobre o mesmo item.
        mediana=mediana_dos_unitarios(observacoes),
        motivo="",
        recencia=quando,
        idade=None if quando is None else agora - quando,
        candidatas=(),
    )


def _eleger(npc: CustoDaRota, mercado: CustoDaRota):
    """Qual das duas e mais barata, ou se elas empatam. TUDO em `Fraction`.

    O DENOMINADOR DO PERCENTUAL E A ROTA **MAIS CARA**, E A ESCOLHA TEM RAZAO.
    ========================================================================
    Dividir pela mais cara responde *"quanto eu economizo escolhendo a barata"*,
    que e a pergunta que o usuario esta fazendo quando abre esta tela. Dividir
    pela mais barata responde *"quanto a cara e mais cara"*, e infla o numero:

        uma rota que custa 100 e outra que custa 200
          -> pelo denominador CARO   (200): economizo 50,0%
          -> pelo denominador BARATO (100): a outra e 100,0% mais cara

    Sao os dois numeros certos para duas perguntas diferentes, e o MAIOR e o que
    agrada — que e exatamente por que a escolha precisa estar escrita e nao
    deixada ao acaso de quem digitou a divisao.

    **A FAIXA DE EMPATE COMPARA CONTRA ESTE MESMO DENOMINADOR.** Se ela usasse o
    outro, a tela poderia dizer "empatado" ao lado de um percentual acima da
    margem — e isso pareceria defeito, com razao.

    O CASO DEGENERADO ESTA GUARDADO, E COM A RAZAO. Se a rota mais cara custa
    ZERO, as duas custam zero (a mais barata nao pode ser negativa: preco e
    quantidade sao positivos dos dois lados). Zero contra zero E empate, e a
    divisao simplesmente nao acontece — nao ha percentual a calcular quando nao
    ha nada a dividir.

    O EMPATE INCLUI A BORDA (`<=`), pelo mesmo criterio de
    `componente_esta_velho`: exatamente na margem ja e empate. Um `<` estrito
    faria o desfecho depender do ultimo bit de uma fracao, e "3,0000%" nao e mais
    decidido que "2,9999%".
    """
    diferenca = abs(npc.unitario - mercado.unitario)
    mais_cara = max(npc.unitario, mercado.unitario)

    if mais_cara == 0:
        return ROTA_EMPATADA, None, diferenca, None

    percentual = diferenca / mais_cara
    if percentual <= MARGEM_DE_EMPATE_PERCENTUAL:
        return ROTA_EMPATADA, None, diferenca, percentual

    vencedora = (
        VENCEDORA_NPC if npc.unitario < mercado.unitario else VENCEDORA_MERCADO
    )
    return ROTA_DECIDIDA, vencedora, diferenca, percentual


def vereditos_das_rotas(
    itens: Sequence["ItemDeRota"],
    modelo: ModeloDeMercado,
    taxa: Fraction,
    agora: datetime,
) -> tuple[VereditoDeRota, ...]:
    """Um veredito por item, NA ORDEM ESCRITA NO `config.toml`.

    A ORDEM E A DO ARQUIVO e nao a do resultado — nao se ordena por "quem tem
    maior economia". A tela e uma lista curta que o usuario escreveu, e
    reordena-la a cada volta de polling faria as linhas trocarem de lugar debaixo
    do dedo dele no meio de uma conferencia.

    SEM ITENS, DEVOLVE VAZIO. Quem transforma isso na frase que a tela mostra e
    `dashboard_dados` — este modulo nao escreve texto de interface.
    """
    return tuple(
        veredito_de_uma_rota(item, modelo, taxa, agora) for item in itens
    )
