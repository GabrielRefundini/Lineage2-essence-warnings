# Itens adiados da Fase 05 — fora do escopo dos planos que os encontraram

Registro de coisas encontradas durante a execucao que NAO foram consertadas, com
o motivo. A regra de escopo e a da casa: so se conserta o que a propria task
quebrou. O resto vira linha aqui em vez de virar diff furtivo.

Cada item traz os NUMEROS MEDIDOS, e nao a impressao. Onde a medicao desta fase
CONTRADIZ o que o plano supunha, a contradicao esta escrita — e o numero que
fica e o medido.

---

## 1. `135,00` lido como `13588` — divida do v1, achada agora, e ela atinge a negociacao tambem

**Encontrado em:** 05-01, na medicao previa da fixtura da Adena (2026-09-01).
Registrado aqui pelo 05-03, que e o plano que carrega o `deferred-items.md` da
fase.

**Sintoma.** Em `tests/fixtures/mercado/janela_adena_f014.png`, **linha 5**, a
tela diz `135,00` e `ler_celula_de_numero` devolve `13588`. Medido nesta arvore
com o codigo de producao (moldes e retangulos de NEGOCIACAO, `RastreioDoPainel`
para a origem), as dez linhas da coluna `Total Price`:

```
    linha   Total Price   Vmax da celula
      0        6200            230
      1        6499            230
      2        6500            230
      3        6600            226
      4        6700            230
      5       13588            255   <=== a tela diz 135,00, e e a UNICA a 255
      6        6800            226
      7        6850            230
      8        7000            230
      9        7000            230
```

Os dez valores reproduzem EXATAMENTE a tabela que o 05-01 gravou na docstring de
`tests/test_mercado_adena.py` — e essa coincidencia e o controle do instrumento:
sem ela, os `Vmax` acima seriam numeros de uma medicao que ninguem sabe se
apontava para os pixels certos.

**Causa, lida no fonte e nos pixels.** E o par `0`x`8`, a margem mais estreita
do sistema: **0,0370**. Ele cai na linha DESTACADA — a unica celula de `Total`
da pagina com `Vmax = 255`, contra `226`/`230` nas outras nove. No piso de
brilho de producao os tracos da linha destacada saem mais grossos e o miolo do
`0` estreita ate ele casar melhor com o molde do `8`.

**Nenhuma peneira de hoje o pega, e as quatro foram conferidas uma a uma:**

- **A gramatica passa.** `135,88` e um numero perfeitamente valido.
- **`linha_ocluida` diz limpo.** Dispersao `0,0000` nas dez linhas.
- **O acordo entre duas escalas de OCR CONCORDA no erro**, porque os dois
  frames leem os mesmos pixels e a linha continua destacada no frame seguinte.
  Uma segunda opiniao sobre a mesma evidencia nao e uma segunda evidencia.
- **A guarda de cruzamento esta DESLIGADA:**
  `mercado_tolerancia_do_cruzamento: None` em `calibracao.py:471`, reprovada
  por medicao no 02-02 (fechamento de 0,6525).

**O que a Fase 5 fez, e o que ela NAO fez.** A guarda aritmetica do 05-01
(`quantidade_de_adena`, criterio `limite_derivado_do_cruzamento`) derruba esta
linha **so na Adena**: residuo `88` contra limite `1,0`. **Na aba de negociacao
o defeito continua ATIVO**, porque la nao ha uma segunda coluna de moeda com que
cruzar e a guarda configuravel segue desligada.

**O que falta medir — e a resposta parcial que ESTA fase produziu.** O plano
desta fase mandava escrever que "a fixtura de negociacao nao tem nenhuma linha
destacada (Vmax 215/226/230 uniformes)". **Isso e falso, e a medicao esta
abaixo.** Sobre a coluna `Total`, com o mesmo instrumento:

```
  janela_negociacao_f005.png:  226 226 230 230 230 230 230 230 230 230
                               -> nenhuma linha destacada. Os dez totais leem.

  janela_negociacao_f010.png:  255 220 220 220 255 226 230 230 230 230
                               -> DUAS linhas a 255 (L0 e L4).
```

Logo a afirmacao correta e mais fraca e mais honesta: **`f005` nao tem linha
destacada; `f010` tem duas.** E a atribuicao delas ainda NAO esta fechada,
porque `f010` e um frame CONFUNDIDO: `tests/test_mercado_leitura.py:36-49` ja
documenta que naquele frame uma tooltip cobre a coluna `Total` das linhas 0 a 3.
O `Vmax = 255` da L0 e portanto indistinguivel entre "linha destacada" e
"tooltip clara por cima". A L4 fica FORA do trecho documentado da tooltip e le
`10000`, sem verdade de referencia no repositorio contra a qual conferir.

**O que fecharia a pergunta:** uma captura da aba de NEGOCIACAO, sem tooltip,
com uma linha selecionada/destacada e um valor conhecido terminado em `0` na
coluna `Total`. E o mesmo material que fecharia o item 2.

**Por que NAO foi consertado aqui.** O escopo desta fase e a Adena — decisao do
usuario, escrita no `05-CONTEXT.md`. Consertar na negociacao significa LIGAR a
guarda de cruzamento la, e ligar exige **remedir a tolerancia**, que e a medicao
do 02-02 inteira (a que reprovou o numero `1273` e mediu o fechamento de
0,6525). Isso e uma fase, nao um item.

**Preco de consertar depois.** Ou (a) remedir a tolerancia do cruzamento sobre
uma populacao de frames de negociacao com linhas destacadas — e ai o
`mercado_tolerancia_do_cruzamento` deixa de ser `None`; ou (b) cortar um segundo
conjunto de moldes de digito para o piso de brilho da linha destacada, o que
resolve a CAUSA em vez de peneirar a consequencia, e serve tambem ao item 3.

**O que NAO fazer:** afrouxar a margem de leitura de glifo para "resolver" o
`0`x`8`. A margem 0,0370 e a mais estreita do sistema justamente porque esses
dois glifos sao parecidos; afrouxa-la troca um erro raro por muitos.

---

## 2. O caso de arredondamento nao tem um pixel no repositorio (A3)

**Encontrado em:** 05-01 Task 1, e deixado explicito pelo executor daquela onda
na secao "Pergunta aberta ao usuario".

**Sintoma.** O ramo de `quantidade_de_adena` que **ACEITA** um arredondamento
(residuo > 0) esta exercitado apenas com **inteiros literais**. O par que o
exercita e `133,33 / 66,66` — `13333` de `Total Price` contra `6666` de
`5 mln increment` —, e ele vem da captura de tela do usuario de 2026-09-01, 17h,
que **nao esta versionada**.

**Os numeros, e a margem e ZERO:**

```
    133,33 / 66,66  ->  n = round(13333/6666) = 2
                        residuo = |13333 - 2 x 6666| = 1
                        limite  = limite_derivado_do_cruzamento(2) = 1,0
                        1 <= 1,0  ->  ACEITA, por IGUALDADE
```

Nao ha folga nenhuma: com `<` em vez de `<=` este caso legitimo REPROVARIA, e a
Adena perderia toda oferta de preco quebrado. O 05-01 prende os dois lados disso
em `TestOSinalDaComparacao`.

**E as nove linhas boas da fixtura NAO exercitam este ramo.** Medido: as nove
linhas de `janela_adena_f014.png` que atravessam dividem TODAS exato — residuo
`0` em todas. O unico residuo diferente de zero na fixtura e o `88` da linha 5,
que e o caso de REJEICAO.

**A consequencia:** o ramo de aceitacao e **inferencia aritmetica verificada em
teste de unidade, e NAO medicao sobre pixels**. Ele esta certo sobre a
aritmetica que o `05-CONTEXT.md` descreve; ele nunca foi confrontado com um
frame real em que a divisao nao fecha.

**O que fecharia:** uma gravacao curta da aba Adena com a coluna
`5 mln increment` ordenada, contendo pelo menos uma linha cujo incremento **nao
divida o total exatamente** — uma oferta de preco quebrado, como o
`133,33 / 66,66` que o usuario viu.

**A consequencia de errar, e ela e maior que este item.** A suspeita ja
registrada no fonte (`mercado_leitura.py:1042-1049`) e que **o cliente TRUNCA em
vez de arredondar**: em `janela_negociacao_f005.png`, linha 5, a tela mostra
`11,39` por 6 unidades com unitario `1,89`, mas `1139 / 6 = 1,8983`, que
ARREDONDA para `1,90`. O residuo ali e `5` contra limite derivado `3`. Se a
truncagem se confirmar, o limite **dobra** (um centesimo por unidade em vez de
meio) — e essa mudanca toca `limite_derivado_do_cruzamento`, que a negociacao
tambem usa.

**Por que NAO foi consertado aqui:** nao ha o que consertar sem material novo. O
ramo esta implementado e testado; o que falta e evidencia, e evidencia nao se
escreve, se captura.

---

## 3. A `Auction List` continua nao sendo lida

**Encontrado em:** 05-01, na varredura de piso de brilho.

**Sintoma.** A coluna `Auction List` da aba Adena escreve a quantidade por
extenso (`10,000,000 Adena`) e **nao se le com os moldes deste projeto**:
`ler_celula` devolve `None` nas dez linhas em **sete** pisos de brilho —
180, 200, 210, 220, 230, 240, 250.

**Causa.** Nao e ajuste de piso, e isso e o achado. A varredura nao encontrou
**vale** entre a populacao de pisos em que o glifo esta gordo (runs de 5-6 px
contra os 4 px dos moldes) e a populacao em que ele ja se partiu. Nao existe um
piso "certo" ali para achar.

**O que custaria consertar:** um SEGUNDO conjunto de moldes de digito cortados
daquela celula — 10 digitos, mais a virgula, mais a palavra `Adena`, doze moldes
—, mais uma chave OPCIONAL no `calibration.json` para aponta-los (opcional pelo
padrao da casa: chave obrigatoria deixa o scanner morto no proximo arranque ate
o usuario recalibrar).

**Consequencia de nao ler, e ela e aceitavel:** ofertas de adena que nao sejam
multiplo de 5.000.000 sao **recusadas**. E falha fechada — perde dado, nao
inventa (A2), e nao houve contraexemplo ate hoje.

**Por que NAO foi consertado aqui:** a decisao travada do 05-01 e que a
quantidade da Adena e **derivada** das duas colunas de moeda que leem, e nao
lida. Cortar um segundo conjunto de moldes agora seria construir o caminho que a
fase decidiu nao usar.

---

## 4. A aba `busca` continua fora, e o calibrador ja grava para ela

**Encontrado em:** 05-CONTEXT, e reafirmado no planejamento da fase.

**Sintoma.** `tools/calibrar_mercado.py` aceita `--layout busca`
(`choices=("negociacao","adena","busca")`, com `LINHAS_ESPERADAS` de 10/10/**9**),
e o `busca` grava geometria que **nenhuma leitora consome**. O usuario pode
calibrar uma aba que o scanner nao le, e nada lhe diz isso.

**Por que NAO foi consertado aqui:** ninguem pediu a aba `busca` — esta escrito
como deferido no `05-CONTEXT.md`. E o escopo desta fase e a taxa de cambio.

**O que custaria:** ou dar-lhe uma leitora (um terceiro modelo de colunas, no
molde do que o 05-01/05-02 fizeram para a Adena), ou fazer o calibrador AVISAR
que `busca` grava geometria orfa. A segunda e barata e honesta, e nao precisa de
fase: cabe num `/gsd-quick`.

---

**Nada aqui virou codigo nesta fase.** Os quatro itens sao registro; o unico
deles que a Fase 5 encosta e o item 1, e ela o encosta **so na Adena**, pela
guarda do 05-01.
