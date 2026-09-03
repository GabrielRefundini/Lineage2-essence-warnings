"""O planejador PURO da varredura de pisos (LEIT-10): quais tentar, e em que ordem.

O QUE ESTE MODULO E, E O QUE ELE NAO E
=======================================
Ele recebe **um inteiro** e devolve **inteiros**. Nao le pixel, nao captura
tela, nao abre `calibration.json`, nao mede tempo e nao sabe o que e um campo
da renda. A decisao — *"em que ordem vale a pena experimentar"* — mora aqui,
onde e testavel sem jogo aberto, sem OCR e sem calibracao; a EXECUCAO e o
CUSTO moram na casca (`renda_laco.py`), que e quem paga OCR por tentativa.

POR QUE A VARREDURA EXISTE (o problema medido tres vezes)
==========================================================
A banda util de brilho **anda com o cenario**, porque a barra do jogo e
semitransparente e o que esta atras dela muda quando o personagem anda. Medido
(M-S, `01-MEDICOES-DE-CAMPO.md:423-435`): a banda util do EXP da Faerlina foi de
`140..170` para `160..180` em **8,5 horas** de farm. O usuario calibra numa
area, muda de mapa, e o numero para de sair **sem que nada tenha quebrado** —
nem o calibrador esta errado, nem a leitura.

O ALCANCE E MEDICAO, E NAO ESCOLHA -- E ELE CONTRADIZ A LEITURA OBVIA DA
CALIBRACAO
========================================================================
A tentacao e derivar o alcance da `largura_da_banda` gravada, que esta no
arquivo e parece a leitura fiel da calibracao. **As larguras gravadas sao 4, 3 e
5** (EXP, adena, nivel), e como o piso gravado e o CENTRO da banda
(`calibrar_renda.escolher_o_piso:504-516`), elas dao meia-banda de **2, 1 e 2**
passos:

    campo                  piso   largura   banda reconstruida        meia-banda
    EXP (barra_esquerda)    155      4      145 150 [155] 160          2 passos
    adena (barra_direita)   190      3          185 [190] 195          1 passo
    nivel                   210      5      200 205 [210] 215 220      2 passos

**E o M-S mediu deslocamento de 4 passos.** Andar so dentro da banda gravada
alcanca 1 a 2 — **menos do que o unico caso medido**. Um alcance derivado da
largura gravada seria um requisito cumprido no papel e inutil no incidente que o
motivou. Por isso `ALCANCE_EM_PASSOS = 4`, que e o deslocamento MEDIDO, e a
`largura_da_banda` entra como ORIGEM da grade e nunca como limite dela.

O QUE A VARREDURA **NAO** CONSERTA -- e os dois casos se parecem de fora (M-Y)
==============================================================================
Medido em 2026-09-03, com o jogo aberto: a Faerlina subiu de nivel, o painel de
status moveu **~90 px** e o retangulo gravado do nivel passou a apontar para
**grama pura**. **Nenhum piso, em nenhum alcance, le um numero em grama.**

    o que mudou           como se ve                          conserto
    brilho do fundo       o campo sai num piso vizinho        varredura (aqui)
    posicao do painel     o campo nao sai em piso NENHUM      `calibrar-renda.bat`

Os dois se manifestam identicos de fora — o campo para de sair — e pedem
consertos OPOSTOS. E por isso que perder em TODOS os pisos do alcance nao e um
fracasso mudo: e a evidencia de que o suspeito passou a ser o RETANGULO. Quem
diz isso ao usuario e o laco, porque so ele sabe que a varredura rodou e perdeu.

INCERTEZA A1 DO ASSUMPTIONS LOG, DECLARADA AQUI PORQUE E AQUI QUE ELA CUSTA
===========================================================================
A leitura *"`largura_da_banda` e contagem de passos de 5 e o piso gravado e o
centro"* foi **derivada** de `calibrar_renda.py:457-459` (`largura` e
`len(self.pisos)`), `:189` (`PASSO_DA_GRADE_DE_PISOS = 5`) e `:504-516`
(`escolher_o_piso` devolve o centro) — e **nao ha teste afirmando essa leitura
de fora**. Se ela estiver errada, a varredura anda no passo errado e nao acha
nada, e o sintoma seria *"a varredura roda e nunca resolve"*.

E por isso que o passo e **parametro nomeado** e nao literal espalhado: quando
alguem descobrir o numero certo, muda-se **um** lugar, e os testes deste modulo
ja provam que a grade obedece ao parametro.
"""

from __future__ import annotations

__all__ = (
    "ALCANCE_EM_PASSOS",
    "PASSO_DA_GRADE",
    "PISO_MAXIMO",
    "PISO_MINIMO",
    "pisos_vizinhos",
)

# O PASSO DA GRADE DE PISOS. **COPIADO** de
# `calibrar_renda.PASSO_DA_GRADE_DE_PISOS`, e nao importado.
#
# A COPIA E MEDICAO E NAO PREGUICA: importar `calibrar_renda` arrasta **353
# modulos** e custa **~1,0 s**, com `cv2`, `numpy` e `argparse` dentro (medido
# nesta arvore em 2026-09-03). O modulo de calibracao tambem chama
# `tornar_consciente_de_dpi()` e carrega as chamadas de JANELA do OpenCV; um
# planejador de tres linhas que arrastasse tudo isso pagaria o efeito colateral
# so por existir, e a seta desta casa aponta FERRAMENTA -> PURO e nunca o
# contrario.
#
# DUAS DEFINICOES DO MESMO PASSO SAO COMO ELAS DIVERGEM — o precedente literal e
# `mercado_registro.py:65` (*"Duas definicoes do mesmo ponto-e-virgula e como
# elas divergem"*). Por isso **ha teste afirmando que os dois valores
# concordam** (`tests/test_renda_pisos.py`), e e a SUITE que paga o import do
# calibrador, uma vez, para que a producao nao pague.
#
# E O VALOR 5 TEM HISTORIA: a varredura de campo original andou de DEZ em DEZ e
# **pulou o 155**, produzindo a leitura errada `106.020` no lugar de `1.696.020`
# — uma conclusao errada com a aparencia de medicao, que entrou num documento e
# do documento entrou num plano (`calibrar_renda.py:179-188`).
PASSO_DA_GRADE = 5

# O ALCANCE DA VARREDURA, EM PASSOS DA GRADE. **ELE E MEDICAO, E NAO ESCOLHA.**
#
# A PROCEDENCIA, com todas as letras: `01-MEDICOES-DE-CAMPO.md:423-435` (o M-S)
# mediu a banda util do EXP da Faerlina indo de `140..170` para `160..180` em
# **8,5 horas** de farm — **20 unidades de brilho**, que sao **4 passos de 5**.
#
# E A FRASE QUE ESTE NUMERO EXISTE PARA NAO SER ESQUECIDA: as
# `largura_da_banda` gravadas sao **4/3/5** e dao meia-banda de **2/1/2**
# passos, entao **andar so dentro da banda gravada NAO teria salvo o caso real**
# (C-11). Quem for "consertar" este numero olhando a calibracao vai encontrar 4,
# 3 e 5 no arquivo e concluir que 4 e coincidencia. Nao e: 4 e o deslocamento
# medido, e a coincidencia com a largura do EXP e coincidencia.
#
# O CUSTO DELE: `2 x ALCANCE` tentativas no pior caso — oito leituras de UM
# campo. Quem paga esse custo e o laco, e e la que esta escrito quando ele vale
# a pena (`RECUSAS_SEGUIDAS_PARA_VARRER`).
ALCANCE_EM_PASSOS = 4

# A FAIXA DE UM PIXEL DE 8 BITS. O truncamento NAO e defensividade — e
# aritmetica: um piso negativo aceita tudo e um piso acima de 255 nao aceita
# nada, ou seja os dois produzem uma leitura **garantidamente** perdida. E uma
# tentativa que nao pode dar certo e tempo de OCR jogado fora dentro de um tique
# que ja esta em apuros, que e exatamente o tique em que a varredura roda.
PISO_MINIMO = 0
PISO_MAXIMO = 255


def pisos_vizinhos(
    *,
    piso: int,
    largura_da_banda: int | None,
    passo: int = PASSO_DA_GRADE,
    alcance: int = ALCANCE_EM_PASSOS,
) -> tuple[int, ...]:
    """Os pisos a experimentar quando um campo parou de sair, NA ORDEM.

    A ORDEM E METADE DO VALOR DESTA FUNCAO, porque a varredura **para na
    primeira leitura valida** — entao a ordem decide quantas leituras de OCR o
    caso tipico custa.

    - **Do mais perto para o mais longe**, porque a banda **anda** e nao salta:
      o piso certo de amanha e vizinho do de hoje. Comecar pelo extremo
      pagaria as tentativas caras primeiro para achar a resposta barata por
      ultimo.
    - **Alternando o sinal** (`+5, -5, +10, -10, ...`), porque o M-S mediu a
      banda **subindo** e o M-K/M-I mediram o cenario mudando nos **dois**
      sentidos. Presumir a direcao seria adivinhar metade do problema — e a
      metade errada custaria as oito tentativas para so entao virar-se.

    O PISO GRAVADO **NAO** ESTA NA SEQUENCIA: ele acabou de ser tentado no
    proprio tique (foi a recusa dele que disparou a varredura), e repeti-lo
    custaria uma leitura de OCR para saber o que ja se sabe.

    `largura_da_banda` ENTRA E **NAO GOVERNA**, e receber sem usar como teto e
    DELIBERADO. Ela e a origem da grade — o piso gravado e o centro da banda
    dela — e esta na assinatura para que quem ler pergunte por que ela nao
    limita, e leia a resposta na docstring do modulo (C-11). **Omiti-la faria a
    proxima pessoa reintroduzir o limite achando que estava consertando um
    esquecimento**, e o limite reintroduzido perderia o unico caso medido.
    Ela e opcional no esquema (`calibracao.py:1530`) e calibracoes antigas nao a
    tem: `None` entra e a sequencia sai a mesma.

    A SEQUENCIA **ENCURTA** NO EXTREMO EM VEZ DE LEVANTAR, e nao e recompletada
    do lado que ainda cabe: o alcance e uma afirmacao sobre quanto a banda
    ANDOU, e nao uma cota de oito tentativas a cumprir.
    """
    del largura_da_banda  # ver a docstring: ORIGEM da grade, nunca o limite

    piso = int(piso)
    passo = int(passo)
    vizinhos = []
    for distancia in range(1, int(alcance) + 1):
        for sinal in (1, -1):
            candidato = piso + sinal * distancia * passo
            if PISO_MINIMO <= candidato <= PISO_MAXIMO:
                vizinhos.append(candidato)
    return tuple(vizinhos)
