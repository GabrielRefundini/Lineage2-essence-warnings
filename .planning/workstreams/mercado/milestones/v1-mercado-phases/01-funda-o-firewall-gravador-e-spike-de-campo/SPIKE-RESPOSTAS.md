# SPIKE-RESPOSTAS — o que as 8 gravações do World Exchange mostraram

**Para quem lê:** você. Eu analisei os 335 frames que você gravou em 2026-08-28 e
**proponho** as respostas abaixo. Quem valida é você — é a decisão D-04, e ela é travada:
nenhum código consome estas respostas antes do seu "validado".

**Como ler:** cada pergunta é uma seção numerada, com um selo e o caminho do frame que
sustenta a resposta. Se eu selei alguma coisa com confiança demais, rebaixe. Se eu errei,
corrija direto no arquivo — a correção é o objetivo do portão, não um acidente.

**Onde estão os frames:** `recordings/` está no `.gitignore` e vive só no seu checkout
principal, em `C:\Users\refun\Desktop\Lineage2-warnings\recordings\`. Todo caminho citado
aqui foi resolvido no disco por `python tools/conferir_spike_respostas.py` — o portão
recusa uma resposta selada que cite frame que não existe.

## Legenda dos selos

| Selo | Significa |
|---|---|
| VERIFICADO | eu vi no frame citado |
| PARCIAL | eu vi, mas só numa aba, numa condição ou numa parte da pergunta |
| NAO RESPONDIDO | o frame não mostra; digo abaixo o que faltou gravar |

## Como as respostas foram obtidas

Localizei o painel em cada um dos 335 frames buscando o molde da âncora
(`tests/fixtures/mercado/molde_da_ancora.png`, a faixa de título "XM Market", 100×28) na
janela inteira, com a mesma técnica de `l2scanner/mercado_visao.py`. Depois recortei e
ampliei as regiões para olhar. Nada foi escrito em `recordings/` — os recortes de inspeção
foram para uma área temporária e não entram no repositório.

Duas medições dão sustentação a várias respostas e ficam registradas aqui uma vez só:

- **O corpo do painel é arte opaca e estável.** Em 9 frames consecutivos de
  `recordings/20260828-061409-mercado-alvo-sobreposto/frame_000000.png` a
  `recordings/20260828-061409-mercado-alvo-sobreposto/frame_000008.png`, com o painel
  parado na mesma posição, o retângulo da âncora é **bit a bit idêntico** (diferença
  máxima por pixel: **0**), enquanto uma região do mundo fora do painel variava até **255**
  no mesmo intervalo. Isso é o que permite usar o corpo do painel como juiz independente
  da faixa de título.
- **A faixa de título não pode julgar a si mesma.** Onde eu precisei decidir "o painel
  está aberto neste frame?" sem usar a âncora, comparei manchas de arte opaca do painel
  (borda esquerda, borda inferior, canto superior esquerdo, início da faixa de abas) na
  posição conhecida, e tomei a **melhor** delas. O motivo de tomar a melhor, e não a
  média: uma tooltip é um retângulo **local**, perto do cursor — ela não cobre o painel
  inteiro, então basta uma mancha limpa para provar que o painel está lá.

---

## 1. Linhas por página e aparência do slot vazio

**Selo: VERIFICADO**

**São 10 linhas por página na grade de negociação, e 9 na tela de busca.**

A grade de negociação (abas Adena, Equipment, Enhancement) mostra **exatamente 10 linhas**,
com passo de **45 px** entre os centros — medido sobre as 10 linhas de
`recordings/20260828-060622-mercado-pagina-cheia/frame_000010.png`, todas preenchidas
(400 px do centro da linha 1 ao centro da linha 10, divididos por 9 intervalos = 45 px
exatos). A mesma contagem e o mesmo passo valem na aba Adena, em
`recordings/20260828-055323-mercado-scroll/frame_000014.png`.

A tela de busca (o ícone de casinha) tem **9 linhas**, não 10: a caixa de busca ocupa a
altura de uma. Está em `recordings/20260828-055323-mercado-scroll/frame_000048.png`.

**O slot vazio é uma faixa lisa: sem ícone, sem texto, sem número.** Ele mantém a listra
alternada clara/escura do fundo da grade, então uma página parcialmente preenchida parece
uma lista normal que simplesmente para. O exemplo limpo é
`recordings/20260828-055323-mercado-scroll/frame_000009.png`: uma busca por "dragon belt"
com **1 linha preenchida e 8 vazias**. O slot vazio não é distinguível por cor de fundo —
só pela ausência de conteúdo.

**Consequência para a Fase 2:** "linha vazia" tem que ser decidida por ausência de ícone
ou de texto dentro do retângulo da linha, nunca por cor de fundo, porque a listra
alternada dá dois fundos diferentes para linhas cheias e dois para linhas vazias.

---

## 2. Separador de milhar, casas decimais e moeda

**Selo: VERIFICADO**

**A vírgula faz as duas coisas, e às vezes na mesma linha.** Este é o achado mais perigoso
desta seção e o motivo de ela existir.

Em `recordings/20260828-055323-mercado-scroll/frame_000014.png`, aba **Adena**, uma linha
inteira diz:

```
5,000,000 Adena          62,00 XM Coin          62,00
```

- `5,000,000` — a vírgula é **separador de milhar**, sem casas decimais;
- `62,00` — a vírgula é **separador decimal**, com **2 casas**.

As duas convenções coexistem **na mesma linha da mesma tela**. Um leitor que decida "a
vírgula é decimal" transforma cinco milhões em cinco; um que decida "a vírgula é milhar"
transforma 62 moedas em 6.200.

**Moeda:** o preço é em **`XM Coin`** nas duas abas — inclusive na aba Adena, onde a
mercadoria é adena e o pagamento é em XM Coin. A palavra `XM Coin` aparece como sufixo
depois do número, num tom mais apagado que o número. Confirmado em
`recordings/20260828-063752-mercado-aberto/frame_000000.png` (Equipment) e em
`recordings/20260828-055323-mercado-scroll/frame_000014.png` (Adena). A quantidade
negociada na aba Adena leva o sufixo **`Adena`**, em texto amarelo/dourado.

**Terceiro formato, e ele não tem nem vírgula nem moeda:** na tela de busca, a coluna
"Minimal price (per unit)" traz **inteiros crus** — `41`, `39`, `45`, `92`, `74`, `114`,
`42`, `73`, `120` em
`recordings/20260828-055323-mercado-scroll/frame_000048.png`. Sem separador, sem casas
decimais, sem sufixo de moeda.

**Glifos que a Fase 2 precisa cortar:** os dez dígitos, a **vírgula**, e os sufixos
`XM Coin` e `Adena` como palavras inteiras (para saber qual convenção aplicar). Nenhum
ponto apareceu como separador em nenhum dos 335 frames.

### VALIDADO PELO USUÁRIO (2026-08-28) — e o enquadramento corrigido

O usuário revisou esta seção e confirmou o fato: **o jogo usa vírgula para tudo, ponto em
lugar nenhum.** Confirmou também o enquadramento correto, que corrige o exagero da redação
original: isto **não é um problema**, é uma especificação. Só seria perigoso para um parser
ingênuo que escolhesse uma regra global; com as duas convenções conhecidas e distinguíveis,
a leitura é determinística.

**O ganho real, que a redação original não destacou:** a regra de agrupamento vira uma
TRAVA DE VALIDAÇÃO, não só uma regra de parsing. Milhar agrupa sempre em blocos de
exatamente 3 dígitos; decimal tem sempre exatamente 2. Um dígito perdido pelo template
matching (`5,00,000` ou `62,000`) viola a regra e a linha é DESCARTADA — em vez de virar um
número plausível e errado no banco. É a falha-fechada da LEIT-02 saindo de graça do formato.

**DECISÃO DE EXIBIÇÃO — padrão brasileiro no nosso console.** O jogo mostra `5,000,000` e
`62,00`; nós mostramos `5.000.000` e `62,00`. Só o separador de milhar muda — o decimal já
coincide, porque em pt-BR a vírgula também é decimal.

**DECISÃO DE ARMAZENAMENTO — inteiros, nunca float.** `62,00 XM Coin` é guardado como o
inteiro `6200` (centésimos); `5,000,000 Adena` como o inteiro `5000000` na coluna de
quantidade. Guardar como ponto flutuante reintroduziria por acumulação o erro que o parsing
acabou de evitar. Isso alinha com as colunas INTEGER separadas (total e quantidade) que a
pesquisa já exigia para a Fase 3.

**O RISCO QUE PERMANECE NESTA TELA NÃO É A VÍRGULA.** Na linha destacada de
`recordings/20260828-055323-mercado-scroll/frame_000014.png`, `10,000,000 Adena` custa
`135,00 XM Coin` — e a terceira coluna mostra `67,50`, que é o preço NORMALIZADO por 5
milhões, calculado pelo jogo. Confundir a coluna normalizada com o preço total corrompe a
série por um fator de 2, e nenhuma regra de vírgula protege disso: é preciso ler a coluna
certa. Ver a seção 4, que trata total vs unitário.

---

## 3. Colunas da grade e sua ordem

**Selo: VERIFICADO**

**Não existe "a grade": existem três layouts de coluna diferentes**, e a diferença não é
cosmética — o número e o significado das colunas mudam.

| Onde | Colunas, na ordem |
|---|---|
| Grade de negociação (Equipment, Enhancement) | `Goods` \| `Quantity` \| `Total` \| `Unit price` \| `Buy` |
| Aba **Adena** | `Auction List` \| `Total Price` \| `5 mln increment` \| `Buy` |
| Tela de busca / catálogo (ícone de casinha) | `Goods` \| `Minimal price (per unit)` \| `Auction List` \| `Search` |

Evidência, uma por layout:
`recordings/20260828-060622-mercado-pagina-cheia/frame_000010.png`,
`recordings/20260828-055323-mercado-scroll/frame_000014.png`,
`recordings/20260828-055323-mercado-scroll/frame_000048.png`.

A pré-resposta da pesquisa (`Goods | Quantity | Total | Unit price | Buy`) está certa —
**para a grade de negociação**. A aba Adena, que é a que interessa para preçar adena, não
tem nenhuma dessas quatro primeiras colunas com o mesmo nome.

**A ordenação é do usuário, e a seta anda.** A seta `▲` fica **dentro da célula de
cabeçalho** da coluna ordenada, e muda de coluna: está sobre `Goods` em
`recordings/20260828-063752-mercado-aberto/frame_000000.png` e sobre `Unit price` em
`recordings/20260828-063752-mercado-aberto/frame_000020.png`, na mesma sessão. Na aba
Adena ela está sobre `5 mln increment`.

**Consequência:** a ordem das linhas não é estável entre leituras e não carrega informação.
E o molde do cabeçalho de coluna muda de pixels quando a seta entra ou sai dele — um
template de cabeçalho cortado com a seta não casa a mesma coluna sem ela.

---

## 4. Preço total e preço unitário

**Selo: VERIFICADO**

**As duas colunas coexistem na grade de negociação — e o unitário é uma derivação
ARREDONDADA, não um dado.**

A prova está em `recordings/20260828-063409-mercado-scroll-transicao/frame_000012.png`:

| Total | Quantity | Unit price mostrado | Total ÷ Quantity de verdade |
|---|---|---|---|
| `24,90` | 10 | `2,49` | 2,49 |
| `17,00` | 5 | `3,40` | 3,40 |
| **`40,00`** | **48** | **`0,83`** | **0,8333…** |

A terceira linha é a que importa: o jogo mostra `0,83` para um valor que é 0,8333…
**O unitário exibido perde precisão.** Reconstruir o total a partir dele (0,83 × 48 =
39,84) devolve um número que nunca existiu.

O mesmo se vê em `recordings/20260828-060622-mercado-pagina-cheia/frame_000010.png`, onde
`18,90 ÷ 2 = 9,45` e `18,00 ÷ 3 = 6,00` fecham exatos — o arredondamento só aparece quando
a divisão não é exata, que é justamente quando ele engana.

**Nenhuma das duas some por aba, mas elas mudam de nome.** Na aba Adena o par é
`Total Price` + `5 mln increment`, e o segundo é o preço **normalizado por 5 milhões de
adena**, não por unidade. Em
`recordings/20260828-055323-mercado-scroll/frame_000014.png`, a linha de `10,000,000 Adena`
custa `135,00` no total e mostra `67,50` no incremento — 135,00 dividido por 2, porque 10
milhões são dois incrementos de 5 milhões.

**Diferença de formatação entre as duas colunas:** o total leva o sufixo `XM Coin`; o
unitário é só o número, sem sufixo.

---

## 5. Preço médio embutido: onde fica?

**Selo: VERIFICADO**

> Promovido na validação do usuário (era um selo fraco): a pergunta tem resposta definitiva
> — não existe preço médio — e a fonte vizinha foi explicitamente recusada. Não há mais nada
> em aberto aqui.

**Não existe preço MÉDIO em nenhum dos 335 frames.** O que existe é um **mínimo**, e é
outra coisa.

Na tela de busca, a coluna **`Minimal price (per unit)`** traz o menor preço unitário
praticado para aquele item, ao lado de `Auction List`, que é a **quantidade de anúncios
ativos** daquele item. Está em
`recordings/20260828-055323-mercado-scroll/frame_000048.png` (uma busca por "doll", nove
itens com seus mínimos e um anúncio cada) e em
`recordings/20260828-055323-mercado-scroll/frame_000009.png`.

Duas ressalvas que valem mais que a resposta:

1. **É mínimo, não média.** Um mínimo é dominado por um único anúncio barato; uma série
   histórica construída sobre ele mede o outlier, não o mercado.
2. **É inteiro.** `73` na tela de busca não distingue 73,00 de 73,99. A precisão de duas
   casas que a grade de negociação dá está perdida aqui.

A pergunta era sobre preço **médio** e a resposta honesta é que ele não aparece. Se existe
uma média em algum lugar, ela não está em nenhuma das telas que estas 8 sessões abriram.

### VALIDADO PELO USUÁRIO (2026-08-28)

**1. A ausência é confirmada, e é a razão de o projeto existir.** O usuário confirmou que o
jogo não tem preço médio, nem histórico, nem as outras informações necessárias para avaliar
preço e negociar. Isso não é uma lacuna do spike — é o problema que este milestone resolve.
Alinha com o que a pesquisa já havia lido do código Mobius: o cliente não tem histórico, e o
"preço médio" nativo de outras bases é média não-ponderada de lotes ativos.

**2. DECISÃO TRAVADA — a tela de busca é RECUSADA como fonte de dados.** O usuário
classificou `Minimal price (per unit)` + `Auction List` como **informação não confiável** e
decidiu: ignorar esses dados, usar apenas a **lista completa** (a grade de negociação).

Consequências que valem para as Fases 2, 3 e 4:

- Não existe tabela `sondagem`, nem segunda fonte de preço. O schema tem UMA origem de
  observação: a grade.
- `ler_pagina()` só parseia a grade de negociação. Se o frame estiver na tela de busca, a
  página é ignorada — não é erro, é uma tela que não nos interessa.
- "Menor pedido visível" (ANAL-01) sai sempre da grade, com as 2 casas decimais. Nunca do
  inteiro truncado da busca.
- Os dois motivos da recusa continuam registrados: é um **mínimo** (dominado por um único
  anúncio barato, mede o outlier e não o mercado) e é **inteiro** (`73` não distingue 73,00
  de 73,99, perdendo a precisão que a grade dá).

**Nota de escopo:** isto é uma pré-recusa deliberada, no mesmo espírito das entradas de Out
of Scope do REQUIREMENTS.md — a tela de busca vai parecer tentadora na Fase 4 (nove itens de
uma vez, sem paginar), e a decisão de não usá-la está tomada com a evidência na mão.

---

## 6. A idade do anúncio é exibida?

**Selo: NAO RESPONDIDO**

Nenhum dos três layouts de coluna tem coluna de tempo, data ou idade — nem
`Goods | Quantity | Total | Unit price | Buy`, nem
`Auction List | Total Price | 5 mln increment | Buy`, nem
`Goods | Minimal price (per unit) | Auction List | Search`. Nenhuma tooltip de item que eu
abri nos frames mostra "listado há N horas": as tooltips trazem peso, atributos,
compounding e restrições de comércio, como em
`recordings/20260828-055323-mercado-scroll/frame_000060.png` e
`recordings/20260828-061253-mercado-tooltip/frame_000015.png`.

**Por que isso não vira "não é exibida":** as 8 sessões nunca abriram a tela de **detalhe
ou de confirmação de compra** de um anúncio. Se a idade existir, é ali que ela estaria, e
esse material não foi gravado. Ausência em três listagens não é prova de ausência no
sistema.

**O que faltaria gravar para fechar esta pergunta:** clicar no botão `Buy` de uma linha e
gravar a tela de confirmação que aparece (sem concluir a compra), mais um clique na lupa
de `Search` da tela de busca, que leva ao detalhe do item. Trinta segundos de gravação.

### VALIDADO PELO USUÁRIO (2026-08-28) — a pergunta perde a urgência

**O usuário confirmou: o jogo não dá o tempo explicitamente.** A pergunta original fica
respondida por essa confirmação, mas o selo permanece o mais fraco de propósito — não vimos
a tela de detalhe/confirmação de compra em nenhuma das 8 sessões, então não podemos afirmar
que ela não mostra nada. O que podemos afirmar: nas telas que o scanner vai ler (a grade),
não há idade de anúncio.

**A idade deixa de importar, porque a série resolve o mesmo problema por outro caminho.** O
usuário propôs: em vez de tentar datar cada anúncio, registrar os itens e valores vistos a
cada abertura do mercado, carimbando com o nosso relógio (GMT-3, que o jogo não fornece).
Com isso a variação de preço por data sai da própria série.

**Isso é exatamente a arquitetura já travada** — a proposta do usuário e o desenho da
pesquisa convergiram de forma independente:

| A proposta | Já é |
|---|---|
| carimbar com o nosso relógio | PERS-01 — snapshot com carimbo do relógio ancorado (`relogio.py` ancora fora e conta pelo monotônico) |
| "podemos acabar pegando duplicado" | PERS-02 — `INSERT OR IGNORE` por chave de conteúdo; reabrir a mesma página não duplica |
| "sabemos a variação por data do preço" | ANAL-03 — tendência por item, sustentada pelo carimbo de cada snapshot |

Nada muda no plano. A convergência é a confirmação.

**RESSALVA DE NOMENCLATURA, no espírito de "menor pedido visível":** o dado é *"o que estava
na tela quando o usuário abriu o mercado"*, nunca *"o que existia no mercado naquele dia"*.
Uma única abertura às 9h produz um ponto às 9h, não uma cobertura do dia. A saída da Fase 4
tem de carregar isso no nome e na recência exibida, como já faz com n e "visto às 14:32".

### IDEIA ADIADA — o anúncio no chat como fonte de evento

O usuário observou que o jogo anuncia no chat quando um item é posto à venda. As linhas
existem nos frames, por exemplo em
`recordings/20260828-055323-mercado-scroll/frame_000014.png`:
`→ Dragon Belt - 1 pcs: added on the market [68,00 XM Coin]`.

Isso captura algo que o snapshot **não pega**: um item anunciado e vendido *entre* duas
aberturas do mercado. É uma fonte de EVENTO, não de estado.

**Adiada, não descartada.** Dois custos concretos: exige **OCR aberto** de texto arbitrário,
que está em Out of Scope no REQUIREMENTS.md (a watchlist é conjunto fechado por template — a
decisão validada do v1); e o chat rola rápido durante o farm, o que o PROJECT.md já
registra. Reavaliar em v2, se a série por snapshot deixar um buraco que justifique o custo.

---

## 7. Renderização do encanto — validação da D-05

**Selo: VERIFICADO**

> Promovido na validação do usuário: a metade que faltava (truncamento) foi respondida por
> conhecimento de campo dele, e a trava estrutural abaixo cobre o caso mesmo se o jogo mudar.

**A parte que a D-05 depende está confirmada; a parte do truncamento não apareceu.**

**Confirmado — o encanto é um prefixo de texto `+N ` no nome, exatamente como você
descreveu.** `recordings/20260828-063752-mercado-aberto/frame_000000.png` mostra dez
linhas do mesmo item base em níveis diferentes:

```
+6 Agathion Alpha Hunter Sealed      40,00
+4 Agathion Alpha Hunter Sealed      28,00
+2 Agathion Alpha Hunter Sealed      20,00
+7 Agathion Alpha Hunter Sealed      77,00
   Agathion Alpha Hunter Sealed       7,02
+5 Agathion Alpha Hunter Sealed      14,00
+7 Agathion Alpha Hunter Sealed      70,00
+5 Agathion Alpha Hunter Sealed      30,00
+7 Agathion Alpha Hunter Sealed     100,00
+6 Agathion Alpha Hunter Sealed      29,00
```

Três coisas ficam provadas por este frame só:

1. **O item sem encanto não escreve `+0` — ele não escreve prefixo nenhum.** O template do
   item base é o nome puro; o template do `+3` é `+3 ` mais o nome.
2. **A D-05 está certa e o custo de errar está medido.** O mesmo nome, na mesma página, no
   mesmo segundo, vale de **7,02 a 100,00** conforme o encanto. Misturar `+3` e `+4` na
   mesma série não introduz ruído: destrói a série. Mínimo, mediana e tendência de um
   agregado desses não descrevem nada.
3. **Há um segundo sinal, independente do texto:** o ícone carrega uma etiqueta `+N` no
   canto inferior esquerdo. Não é preciso usá-la, mas ela existe e serve de conferência
   cruzada barata se o recorte do nome ficar ambíguo. O mesmo canto do ícone carrega a
   quantidade nos itens empilháveis, como em
   `recordings/20260828-063409-mercado-scroll-transicao/frame_000012.png`.

**Não confirmado — o truncamento.** Nenhum nome truncado apareceu nos 335 frames. Medi a
área de texto da coluna `Goods` em **263 px**; o nome legítimo mais longo que apareceu é
`Common Mafia Leader Luciano Doll`, em
`recordings/20260828-061409-mercado-alvo-sobreposto/frame_000024.png`, e ele ocupa cerca
de **168 px** — sobram uns 95 px, e ele termina limpo, sem reticências.

A primeira medição automática desta folga deu "262 de 263 px, folga de 1 px" e estava
errada: o vencedor era uma **tooltip** por cima da coluna `Goods`, não um nome. Registro o
erro porque ele é o modo de falha desta medição inteira — em material com sobreposição,
"o pixel mais à direita da coluna" não é "o fim do nome".

Então: **não sei o que acontece com um nome mais longo que 263 px.** O que faltou gravar é
um item de nome realmente longo (`Enhanced ...`, `Blessed ...`, um nome com sufixo de
grau) **com** prefixo de encanto. Isso importa porque truncamento é a única forma de dois
itens diferentes virarem a mesma string e se fundirem numa série só.

### VALIDADO PELO USUÁRIO (2026-08-28) — o truncamento não tem população

**O usuário respondeu por conhecimento de campo: nenhum item tem nome com reticências, nem
nome tão grande.** A dúvida não é uma lacuna de gravação — é uma preocupação sem população.
Bate com o que foi medido: o nome legítimo mais longo dos 335 frames ocupa ~168 px numa
coluna de 263 px, e ninguém chegou perto do limite.

**TRAVA ESTRUTURAL ASSIM MESMO — nunca truncar do nosso lado.** Aceita porque custa zero e
não depende de a afirmação continuar verdadeira depois de um patch do jogo: o casamento do
nome exige a linha inteira até a borda da coluna `Goods`. Se o pixel na borda não for fundo
— isto é, se houver texto encostando no limite — a linha é DESCARTADA, não lida pela metade.

Isso transforma um desconhecido em falha-fechada: mesmo que o jogo passe a truncar um dia, o
scanner recusa a linha em vez de fundir duas séries de preço. É a mesma disciplina da
LEIT-02 (frame ilegível é descartado, preço nunca é inventado) aplicada ao nome.

**Consequência para a Fase 2:** o template de cada entrada da watchlist é o nome COMO
RENDERIZADO, prefixo `+N ` incluso, e o casamento é rejection-first contra a borda da
coluna. O ícone com a etiqueta `+N` no canto inferior esquerdo fica como conferência cruzada
disponível, não obrigatória.

---

## 8. Posição do painel: fixa ou arrastável? — a pergunta A1

**Selo: VERIFICADO**

**O painel é arrastável e percorre praticamente a janela inteira. A âncora em retângulo
fixo está descartada, e a busca em faixa também.**

Medi a posição da âncora nos 335 frames. Nos 255 frames em que ela casa acima de 0,99:

```
posições distintas   34
x                    412 .. 1239     amplitude  827 px
y                     79 ..  910     amplitude  831 px
janela do jogo             1720 x 1392
```

Os extremos, cada um num frame que existe no disco:

| Extremo | Posição da âncora | Frame |
|---|---|---|
| x mínimo | (412, 325) | `recordings/20260828-061409-mercado-alvo-sobreposto/frame_000029.png` |
| x máximo | (1239, 578) | `recordings/20260828-063240-mercado-farm-com-party/frame_000021.png` |
| y mínimo | (984, 79) | `recordings/20260828-063409-mercado-scroll-transicao/frame_000006.png` |
| y máximo | (821, 910) | `recordings/20260828-063240-mercado-farm-com-party/frame_000023.png` |

A medição do plano 01-02 sobre o incidente 27x já dizia que o painel anda (181 px de
deslocamento entre dois frames). O campo mostra que aquilo era o piso: **827 × 831 px de
alcance**. Uma faixa que cobrisse esse alcance é a janela.

### E há um problema muito maior escondido aqui

Enquanto media o alcance, o mesmo censo mostrou uma coisa que o plano 01-04 precisa saber
antes de calibrar qualquer coisa: **a margem medida da âncora no campo é NEGATIVA.**

Classifiquei cada frame que ficou abaixo do limiar de 0,73 usando o juiz independente
descrito no topo deste arquivo (manchas de arte opaca do painel na posição conhecida).
Resultado:

```
pior POSITIVO REAL   0.4110   painel ABERTO, tooltip por cima da faixa de título
melhor NEGATIVO REAL 0.4753   painel FECHADO, sessão mercado-fechado (33 frames)
MARGEM DE CAMPO     -0.0643

o 01-02 media +0.5372 sobre as fixtures do incidente 27x
```

**As duas classes se sobrepõem.** Nenhum limiar sobre a faixa de título separa "painel
aberto" de "painel fechado" neste material — não é o valor 0,73 que está errado, é a ideia
de que um único retângulo resolve.

**19 frames com o painel comprovadamente aberto ficam abaixo de 0,73.** Os dois piores:

- `recordings/20260828-055323-mercado-scroll/frame_000084.png` — âncora **0,4110**. Olhei:
  o painel está inteiro na tela, a tooltip de "Enhanced Aztacan Doll" cobre a metade
  esquerda da faixa de título e o texto "XM Market" some. As manchas de arte do painel
  casam **1,000** na posição conhecida.
- `recordings/20260828-055323-mercado-scroll/frame_000088.png` — âncora **0,4796**, painel
  aberto, tooltip de "Common Samurai Doll" sobre o título.

O melhor negativo verdadeiro, para comparar, é
`recordings/20260828-053003-mercado-fechado/frame_000010.png`, com **0,4753** — a sessão em
que o painel nunca foi aberto.

Isto contradiz uma decisão registrada no 01-02: *"a âncora é a faixa de TÍTULO, não a linha
de cabeçalhos de coluna: tooltip e marcação de alvo caem sobre as LINHAS"*. A tooltip cai
onde o cursor estiver, **inclusive sobre a faixa de título**. A escolha do título continua
melhor que a do cabeçalho de colunas, mas ela não é imune.

### O que fica em aberto nesta pergunta

O fecha-reabre que o roteiro pediu não é isolável neste material: no
`mercado-aberto` mais recente o painel permanece aberto em (1037, 220) do início ao fim, e
os frames de score baixo no meio da sessão são tooltip, não fechamento. Então **não sei se
o painel reabre onde foi fechado ou numa posição padrão**. Isso muda o custo da busca (um
palpite bom na posição anterior versus varredura), mas não muda a arquitetura: a busca é
necessária de qualquer jeito.

### VALIDADO PELO USUÁRIO (2026-08-28) — e o desenho da detecção muda por causa disto

**1. O painel é livre, mas tende a uma região.** O usuário confirma que pode arrastá-lo para
onde quiser; na prática ele fica numa região habitual. Os 827 x 831 px de deslocamento
medidos são o alcance possível, não o comportamento típico.

**2. AO FECHAR E REABRIR, ELE VOLTA ONDE ESTAVA.** Esta é a informação de desenho mais
valiosa desta seção: a posição é ESTÁVEL dentro de uma sessão. Ela só muda quando o usuário
arrasta, e arrastar é um ato deliberado e raro.

**DECISÃO DE DESENHO — adquirir e depois seguir, em vez de procurar sempre.** A busca na
janela inteira custa ~45 ms e não pode rodar a cada volta do laço. Com a posição estável:

- **Aquisição** (cara, rara): varredura da janela inteira quando não se sabe onde o painel
  está — no primeiro tick com o mercado aberto, ou depois de uma perda.
- **Seguimento** (barato, todo tick): confere a posição já conhecida.
- **Reaquisição:** só quando o seguimento falha N ticks seguidos, o que na prática significa
  "o usuário arrastou o painel" ou "fechou".

Isso resolve o custo sem depender do painel ser fixo — que ele comprovadamente não é.

**3. A TOOLTIP, E POR QUE A MITIGAÇÃO DO USUÁRIO NÃO PODE SER A SOLUÇÃO.** O usuário
observou que a tooltip segue o mouse e se ofereceu para evitar passar o cursor sobre os itens
no meio da lista, mantendo-a perto da borda de rolagem, longe de cobrir item e valor.

A oferta é útil e reduz a frequência do problema — mas **não pode ser o mecanismo de
correção**. Este projeto não troca falha-fechada por disciplina do usuário: um dia ele
esquece, e o modo de falha volta silencioso. A mitigação entra como redução de ruído, não
como garantia.

**A causa real da margem negativa é outra, e tem conserto estrutural.** O que quebrou a
medição foi a tooltip cobrindo justamente a FAIXA DE TÍTULO — o único retângulo que a âncora
olhava. A correção é não depender de um ponto só: usar VÁRIOS pontos de âncora
independentes (faixa de título, barra de abas, cabeçalho de colunas) e decidir por votação.
Uma tooltip cobre um deles; cobrir todos ao mesmo tempo é implausível.

**Consequência para a Fase 2 (e para a Wave 4 desta fase):** `mercado_aberto()` deixa de ser
"casar um retângulo contra um limiar" e passa a ser "aquisição por varredura + seguimento
barato + votação entre âncoras". O limiar 0,73 medido no 01-02 continua válido POR ÂNCORA;
o que estava errado era supor que uma âncora só bastava.

---

## 9. Opacidade do painel (A5) e o que tooltip e marcação de alvo cobrem

**Selo: VERIFICADO**

**O painel é opaco — inclusive a faixa de título, e isso é medida, não impressão.**

Em 9 frames consecutivos com o painel parado em (796, 225), de
`recordings/20260828-061409-mercado-alvo-sobreposto/frame_000000.png` a
`recordings/20260828-061409-mercado-alvo-sobreposto/frame_000008.png`:

| Região | Diferença máxima por pixel entre frames |
|---|---|
| retângulo da âncora (faixa de título, 100×28) | **0** |
| fundo entre as linhas da grade | 0 a 2 |
| faixa de abas | 0 a 2 |
| banner de arte do topo | 13 a 20 |
| **mundo, fora do painel** | **255** |

O mundo atrás mudou completamente e o retângulo da âncora não mudou **um bit**. A
suposição A5 está confirmada para a faixa de título e para o corpo da grade. O banner de
arte decorativo do topo varia um pouco (13 a 20 níveis) e por isso não serve de âncora —
o que reforça a escolha já feita no 01-02.

**A tooltip é o problema, e ela vai a qualquer lugar.** Ela é desenhada **por cima** do
painel, é um retângulo local perto do cursor, e é **semitransparente**: dá para ver o texto
do painel fantasmando por baixo dela. Onde eu a vi cair:

| O que ela cobriu | Frame |
|---|---|
| a **faixa de título** (a âncora) | `recordings/20260828-055323-mercado-scroll/frame_000084.png` |
| a coluna `Goods` de 8 linhas seguidas + o cabeçalho de colunas + a linha de sub-abas | `recordings/20260828-061253-mercado-tooltip/frame_000015.png` |
| as colunas `Total` e `Unit price` das linhas de cima | `recordings/20260828-060622-mercado-pagina-cheia/frame_000010.png` |
| a faixa de abas e parte do título ao mesmo tempo | `recordings/20260828-063752-mercado-aberto/frame_000006.png` |

Como ela é semitransparente, o valor por baixo continua **parcialmente legível** — que é
pior do que se ela fosse opaca. Um leitor de dígitos vai extrair *alguma coisa* de um
número coberto, com boa confiança e valor errado. É literalmente o incidente das 27 mortes
falsas, um nível acima.

**A marcação de alvo é mais bem-comportada.** Em
`recordings/20260828-061409-mercado-alvo-sobreposto/frame_000024.png` a barra do alvo
"Shooter of Greed" fica sobre o painel e cobre o **cabeçalho da coluna `Goods` e o nome da
linha 1**. Ela é opaca, tem posição previsível (topo da área do painel, onde o jogo desenha
o alvo) e, nas 47 gravações desse cenário, **nunca alcançou a faixa de título** — a âncora
ficou em 0,9997 em todos os frames com o painel aberto e o alvo marcado.

---

## Impacto no planejamento das Fases 2, 3 e 4

Uma linha por consequência. As três primeiras mudam desenho, não ajuste.

1. **A âncora do 01-04 não pode ser só a faixa de título.** A margem de campo é **−0,0643**:
   um frame com o painel aberto e tooltip sobre o título (0,4110) marca **menos** que um
   frame com o painel fechado (0,4753). Precisa de um segundo sinal — a proposta que os
   dados sustentam é confirmar com manchas de arte opaca do painel e aceitar a **melhor**
   delas, que foi exatamente o juiz que usei aqui e que classificou 19 de 19 corretamente.
2. **A busca do painel é na janela inteira, não numa faixa.** Alcance medido de 827 × 831 px
   numa janela de 1720 × 1392. Com a busca custando ~45 ms, ela não roda a cada volta: entra
   com cadência limitada, no precedente do `SEGUNDOS_ENTRE_BUSCAS_DO_DIALOGO = 5.0`, e com
   memória da última posição, porque em 255 frames houve só 34 posições distintas — o painel
   fica parado a maior parte do tempo.
3. **`mercado_grade` não é uma grade só: são três.** As colunas mudam entre a grade de
   negociação, a aba Adena e a tela de busca. A calibração precisa gravar qual layout está
   sendo lido, e a leitura precisa recusar a página quando o layout não é o esperado, em vez
   de ler a coluna errada com confiança.
4. **A vírgula é ambígua e a desambiguação vem do sufixo, não do número.** `5,000,000 Adena`
   e `62,00 XM Coin` na mesma linha. `mercado_templates_de_digito` precisa dos dez dígitos e
   da vírgula, e a leitura precisa reconhecer as palavras `XM Coin` e `Adena` para escolher a
   convenção. Nenhum ponto apareceu como separador em 335 frames.
5. **O banco da Fase 3 guarda `Total` e `Quantity`, e deriva o unitário.** O unitário exibido
   é arredondado a 2 casas (40,00 ÷ 48 aparece como 0,83) e não reconstrói o total.
6. **Cada variante de encanto é uma série independente, e o template inclui o prefixo `+N `.**
   O item sem encanto não tem prefixo — o template dele é o nome puro, e não `+0 `. A D-05
   fica confirmada com o custo medido: 7,02 a 100,00 para o mesmo nome na mesma página.
7. **O estabilizador de página da Fase 2 não pode esperar por uma página "rasgada".** Em
   `recordings/20260828-063409-mercado-scroll-transicao/frame_000016.png` e
   `recordings/20260828-063409-mercado-scroll-transicao/frame_000017.png`, dois frames
   consecutivos durante rolagem contínua, o conteúdo é **completamente diferente** e as duas
   páginas estão **nítidas e alinhadas ao mesmo grid de linhas**. A lista salta de página em
   página; não existe meia-linha para detectar. A página só se prova parada comparando frames
   consecutivos entre si.
8. **A leitura precisa recusar a linha coberta.** A tooltip é semitransparente, então um
   número coberto ainda produz glifos plausíveis. A recusa tem que vir de um sinal de
   oclusão, não da confiança do casamento — que é o que o incidente 27x já ensinou uma vez.
9. **O consumidor de oclusão da Fase 4 ganha o sinal que queria, e mais barato do que se
   esperava.** O painel é opaco e grande (a borda esquerda fica em `x` da âncora −434 e a
   borda inferior em `y` da âncora +729, medidos), então "o World Exchange está aberto"
   cobre uma área conhecida da tela e a party window sob ele é ilegível por construção, não
   por heurística.
10. **Duas perguntas ficam devendo material, e as duas custam ~1 minuto de gravação:** a tela
    de detalhe/confirmação de compra (para fechar a idade do anúncio, seção 6) e um item de
    nome longo com prefixo de encanto (para fechar o truncamento, seção 7).

---

*Fase 01, workstream mercado. Análise proposta por Claude sobre as 8 gravações de*
*2026-08-28; validação do usuário pendente (D-04).*
