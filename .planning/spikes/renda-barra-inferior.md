# Spike: a renda nao precisa do chat — a barra inferior ja tem tudo

Data: 2026-09-01, madrugada. Feito ANTES de planejar, com a tela do usuario ao vivo.

## A pergunta

O usuario pediu XP/min, XP/h, adena/min, adena/h, nivel e adena total, e
sugeriu ler os numeros que sobem no CHAT ("You have acquired 405 XP...",
"You have obtained 88 adena."), com a propria ressalva de que "eles sobem
bem rapido".

## O achado que muda o desenho

O chat e a fonte ERRADA. A barra de status inferior do cliente ja exibe,
em texto branco sobre fundo escuro, permanentemente e sem rolagem:

    EXP   68.5632%   642%   83        Special   [XM] 58,40   [L] 13.091   [adena] 10.673.628

E a janela de status do personagem exibe o NIVEL (66) sob o retrato.

Ler o chat exige acompanhar rolagem rapida, deduplicar linhas e aceitar
que uma linha perdida e renda perdida para sempre. Ler a barra e uma
DIFERENCA entre duas amostras: nenhuma amostra perdida corrompe o total,
porque o total esta na tela, nao na soma dos eventos.

## Medicoes (nao suposicoes)

Windows OCR (`l2scanner.ocr`, ja no projeto) sobre recortes crus:

| regiao | recorte (fisico) | leitura |
|---|---|---|
| barra esquerda | 0,1368 500x26 | `EXP 68.6738% 582% : 83` (escala 2x) |
| barra direita  | 1230,1368 470x26 | `Special 58,40 13,091 10,679,769` (escala 1x) |
| nivel | 246,736 30x20 | `''` cru — **precisa de mascara** |

O nivel fica sobre o retrato (fundo ocupado). Com mascara de branco
`inRange(HSV, (0,0,vmin), (179,70,255))` invertida:

| vmin | leitura |
|---|---|
| 170 | `''` |
| 190 | `6b` |
| 210 | `66` OK |

Duas amostras com ~1 min de intervalo, provando que os campos SE MOVEM:

| campo | t0 | t1 |
|---|---|---|
| EXP % | 68,5632 | 68,6738 |
| adena | 10.673.628 | 10.679.769 |
| L-Coin | 13.091 | 13.091 |

## O que isso entrega de graca

- **Tempo ate o nivel**: `(100 - exp%) / (exp% por hora)`. Exato, sem tabela
  de XP por nivel. E literalmente o "quanto tempo vai levar" que o usuario pediu.
- **adena/h**: diferenca do contador, nao soma de eventos.

## As duas armadilhas que o plano precisa cobrir

1. **Level up zera o EXP%.** Delta negativo em EXP nao e renda negativa: e
   `(100 - anterior) + atual` e um nivel a mais. Sem isso, subir de nivel
   registra -68% de renda.
2. **Adena cai quando o usuario GASTA.** Delta negativo em adena nao e renda
   negativa. Ganho bruto = soma dos deltas positivos; a queda vira "gasto"
   registrado a parte. Vender no mercado tambem entra como ganho — e correto,
   mas precisa ser distinguivel do farm no registro.

## Fica de fora (por ora)

XP ABSOLUTO (405 XP, nao 0,0106%) so existe no chat. Se o dashboard pedir o
numero absoluto, o chat volta como ENRIQUECIMENTO opcional sobre um tronco
que ja funciona — nunca como fonte primaria.
