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
    RESOLUCAO_AMBIGUA,
    RESOLUCAO_SEM_CORRESPONDENCIA,
    Evidencia,
    MenorPedidoVisivel,
    ModeloDeMercado,
    menor_pedido_visivel,
    recencia_do_preco,
    resolver_o_nome,
)

if TYPE_CHECKING:  # pragma: no cover - so o verificador de tipos passa aqui
    from .config import ItemDeRota

__all__ = [
    "ESTADOS_DA_ROTA",
    "MARGEM_DE_EMPATE_PERCENTUAL",
    "ROTA_DECIDIDA",
    "ROTA_EMPATADA",
    "ROTA_NOME_AMBIGUO",
    "ROTA_NUNCA_VISTA",
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
# OS NOMES
# ===========================================================================

# As duas vencedoras possiveis. Nomes e nao booleano, porque o empate e um
# terceiro desfecho e um `bool` obrigaria quem exibe a carregar um `None` cujo
# significado nao esta escrito em lugar nenhum.
VENCEDORA_NPC = "npc"
VENCEDORA_MERCADO = "mercado"

# OS QUATRO ESTADOS DE **UMA LINHA**. Cada um se desenha diferente na tela, e
# nenhum deles some: um item configurado que sumisse seria indistinguivel de
# "esqueci de configurar".
ROTA_DECIDIDA = "decidida"
ROTA_EMPATADA = "empatada"
ROTA_NUNCA_VISTA = "nunca vista"
ROTA_NOME_AMBIGUO = "nome ambiguo"

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
ESTADOS_DA_ROTA = (
    ROTA_NOME_AMBIGUO,
    ROTA_NUNCA_VISTA,
    ROTA_EMPATADA,
    ROTA_DECIDIDA,
)


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
    recencia: datetime | None
    idade: timedelta | None
    candidatas: tuple[str, ...]

    @property
    def decidida(self) -> bool:
        return self.estado == ROTA_DECIDIDA


def _sem_rotas(
    estado: str, item: "ItemDeRota", nome_exibido: str, candidatas: tuple[str, ...]
) -> VereditoDeRota:
    """A linha que existe na tela e nao tem numero. Os dois estados de quebra.

    ELA APARECE, e nao some. Um item configurado que sumisse da tela seria
    indistinguivel de "esqueci de configurar", e o usuario ficaria procurando um
    bloco que ja esta la (decisao travada do 02-CONTEXT).
    """
    return VereditoDeRota(
        estado=estado,
        item=item.nome,
        chave=None,
        nome_exibido=nome_exibido,
        npc=None,
        mercado=None,
        vencedora=None,
        diferenca_por_unidade=None,
        diferenca_percentual=None,
        evidencia=None,
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

    OS QUATRO DESFECHOS
    ===================
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
    - as duas rotas existem -> `ROTA_EMPATADA` ou `ROTA_DECIDIDA`, conforme a
      faixa.

    `agora` ENTRA POR PARAMETRO, e vira `idade`. Este modulo continua sem relogio
    do sistema.
    """
    resolucao = resolver_o_nome(modelo, item.nome)

    if resolucao.estado == RESOLUCAO_AMBIGUA:
        return _sem_rotas(
            ROTA_NOME_AMBIGUO, item, item.nome, resolucao.candidatas
        )

    if resolucao.estado == RESOLUCAO_SEM_CORRESPONDENCIA:
        return _sem_rotas(ROTA_NUNCA_VISTA, item, item.nome, ())

    chave = resolucao.chave
    observacoes = modelo.observacoes_de(chave)
    menor = menor_pedido_visivel(observacoes)
    nome_exibido = modelo.nome_exibido_de(chave)

    if menor.unitario is None:
        return _sem_rotas(ROTA_NUNCA_VISTA, item, nome_exibido, ())

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
        evidencia=menor.evidencia,
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
