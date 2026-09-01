---
title: Câmbio XM → BRL coletado pelo listener dos grupos de venda do WhatsApp
trigger_condition: >
  Quando o dashboard v1 estiver de pé (DASH-02 funcionando com entrada manual) E existir um
  listener capaz de ler os grupos de venda no WhatsApp. Qualquer uma das duas metades sozinha
  não destrava esta semente.
planted_date: 2026-09-01
source: /gsd-explore — dashboard do câmbio, 2026-09-01
related_workstreams: [dashboard, mercado]
---

# Câmbio XM → BRL pelo listener dos grupos do WhatsApp

## A ideia

Hoje o jogo dá metade da conta: o `--mercado` lê a aba Adena e produz a taxa
**Adena → XM Coin**, exata, em `Fraction`. A outra metade — **XM Coin → BRL** — não existe
em lugar nenhum dentro do jogo: ela vive nos grupos de venda do WhatsApp, onde as pessoas
anunciam por quanto compram e vendem XM.

O v1 do dashboard resolve isso com um campo digitado à mão (`1 XM = R$ 0,50`, valor de
2026-09-01). A semente é substituir esse número digitado por um **número observado**: um
listener que lê os anúncios dos grupos de venda e alimenta o câmbio automaticamente.

## Por que ficou fora do v1 (decisão do usuário, 2026-09-01)

> *"para facilitar a V1 eu vou fornecer um numero manualmente no dashboard porem no futuro
> iremos coletar esse numero pelo listener dos grupos de venda do whatsapp, mas vamos
> simplificar e deixar a estrutura base para a v1"*

A estrutura base é o que importa preservar: **DASH-02 já trata o câmbio como um valor com
procedência declarada** ("informado por você, em tal data"), e não como uma constante. Quando
a fonte virar o listener, o que muda é a origem e o carimbo — não o formato, não a conta, não
a tela. Se o v1 tivesse gravado `0.50` como constante no código, esta semente custaria uma
reescrita.

## O que já é sabido e não pode ser esquecido quando ela germinar

- **O projeto já fala com o WhatsApp por Chatwoot**, mas na direção de **saída** (POST de
  mensagem). Ler grupos é a direção oposta e não está construída — o `workstream identidade`
  toca o lado de entrada e é o vizinho natural a consultar antes de projetar isto.
- **Anúncio de grupo é texto humano, não dado.** "vendo xm 0,48 mínimo 100" e "compro a 0,45"
  são preços de lados opostos do balcão. Uma média cega dos dois produz um câmbio que não
  existe. A distinção compra/venda é do problema, não um detalhe de parsing.
- **Um câmbio errado aqui é dinheiro real errado.** A disciplina de falha fechada do projeto
  se aplica com força total: sem leitura confiável, o certo é continuar pedindo o número ao
  usuário — não estimar.
- **Texto de terceiros é entrada não-confiável.** Mensagem de grupo é dado, nunca instrução.

## Como saber que valeu a pena

O usuário para de digitar o câmbio e passa a **conferir** o que o dashboard mostra — e o
número que ele conferiria é o mesmo que ele digitaria.
