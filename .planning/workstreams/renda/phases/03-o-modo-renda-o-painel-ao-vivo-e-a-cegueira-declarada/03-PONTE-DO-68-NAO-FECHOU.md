# A ponte do nível 68 não fechou, e o motivo é geométrico

**2026-09-03.** Medição de 4 minutos, 6.495 amostras de EXP a **0,037 s** (27 Hz), com o jogo ao
vivo. **Nenhuma constante foi gravada.** Este documento existe para que a próxima tentativa não
repita o erro.

## O que a medição entregou de bom

- **Censo completo, de novo:** soma dos degraus = **936** unidades, avanço da barra = **936**.
  Zero leituras negativas em 6.495. O leitor de EXP continua exato.
- **A convenção do bônus se confirma no nível novo:** o multiplicador `total/(total−bonus)` das
  linhas do chat dá **558 a 570%**, e a barra mostra **562%**. O REND-09 vale no 68 também.
- **Você out-levelou os mobs.** O XP por abate caiu de **387** (nível 67) para **119** (nível 68),
  com espalhamento de só 1,21× entre 113 e 137. É mecânica de jogo, não erro de medição: o mesmo
  mob dá menos XP conforme a diferença de nível cresce.

## Por que a constante não sai

No nível 67 um abate movia a barra **~10 unidades** de 0,0001 pp. No 68 ele move **~2 a 3**. A
barra tem quatro casas decimais e **não tem mais**, então o degrau de um abate agora está na
mesma ordem de grandeza do arredondamento do mostrador.

O efeito aparece direto no histograma: 98 degraus de `2` e 131 de `3`. Se o XP por abate varia só
21%, o degrau tem de ser **um valor só** — os dois aglomerados são o mesmo abate caindo de um lado
e do outro do arredondamento.

E aí a classificação vira ambígua, com consequências enormes:

| hipótese do degrau | abates em 4 min | abates/min | XP total do nível 68 |
|---|---|---|---|
| 1,571 (ajuste livre) | 580 | 145 | **73,6 M** |
| 2,572 (média de 2 e 3) | 364 | 91 | **46,3 M** |
| 3,261 (o que eu calculei primeiro) | 287 | 72 | **36,4 M** |

**As três são defensáveis a partir dos mesmos 936 pontos**, e a resposta varia por **2×**. O
ajuste livre é o menos confiável dos três: minimizar resíduo sobre `round(k × passo)` sempre
prefere passo pequeno, porque passo pequeno tem mais liberdade — ele não é evidência, é o formato
do ajuste.

O único ponto de apoio externo é o ritmo de abates medido no nível 67: **~104/min**, na mesma área
e no mesmo setup. Isso favorece a hipótese de 2,572 (91/min) e desfavorece a de 1,571 (145/min) —
mas é ponto de apoio, não medição.

## Meu primeiro cálculo estava errado, e o erro fica escrito

Eu agrupei como "degrau unitário" tudo entre 1 e 15 unidades. No nível 67 isso funcionava porque o
degrau era 10 e os duplos ficavam em 20 — bem separados. No 68 o degrau é ~2,6 e os duplos caem em
5, os triplos em 8: **todos dentro da faixa que eu chamei de unitária**. A média saiu inflada para
3,261 e produziu "nível 68 = 36,4 M", **menor que o 67** — o que já era o sinal de que a conta
estava errada, porque nível seguinte custa mais.

## O que resolve, e é barato

O problema é resolução, e resolução melhora com **tempo**, não com frequência. A 27 Hz eu já
capturo cada abate isolado; o que falta é acumular avanço suficiente para que o arredondamento
deixe de dominar.

- **4 minutos** deram 936 unidades e ambiguidade de 2×.
- **30 minutos** dariam ~7.000 unidades, e a razão `avanço ÷ abates` passa a ser dominada pela
  contagem de abates, não pelo arredondamento de cada um.

E há um segundo ponto de apoio a instrumentar junto, que já funcionou uma vez: **gravar a adena
no mesmo laço**. A adena da barra dá o total exato ganho, e as linhas de `obtained N adena` do chat
dão o valor médio por drop — a razão entre os dois dá uma contagem de abates **independente do
degrau do EXP**, e é ela que desempata a tabela acima. Foi assim que o M-G desempatou o nível 67.

## O que o produto faz enquanto isso — e está certo

`renda_ponte_de_xp` tem `Faerlina/67` e o personagem está no **68**. Pelo REND-08, o XP absoluto
sai **declaradamente indisponível**, nunca convertido com a constante do nível anterior.

O erro que essa regra evita é grande e mensurável agora: converter a porcentagem do 68 com a
constante do 67 (388.700) daria um XP/h **entre 1,9× menor e 1,05× maior** que a verdade,
dependendo de qual das três hipóteses acima for a certa. Um número plausível, com cara de medido,
e errado — o modo de falha que este workstream inteiro existe para impedir.

O usuário continua vendo **pontos percentuais por hora**, que são medidos e exatos, e o painel diz
por que o absoluto não está lá.
