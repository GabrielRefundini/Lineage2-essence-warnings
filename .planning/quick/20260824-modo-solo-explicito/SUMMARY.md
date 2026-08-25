---
status: complete
---

# Modo solo explícito (`soloPlay`)

**Concluído:** 2026-08-24 · 446 testes (433 + 13)

## O que o usuário pediu

"Ativar uma função chamada soloPlay, onde não estou em party e deve somente
avisar se eu morri, monitorar apenas o Yazalaque e continuar com a agenda
normalmente."

## Metade já existia

A detecção da morte própria sem party window foi feita na Fase 8. O que faltava
era o **modo** — parar de reclamar de uma party que ele decidiu não ter.

## A distinção que organiza tudo

| | O scanner sabe... | Reclamar é... |
|---|---|---|
| Party window sumiu | não sabe se você saiu, se a UI travou, se o jogo caiu | **certo** |
| Modo solo | sabe que não há party — você disse | **ruído**, a cada tick |

Por isso o solo suprime exatamente dois avisos, e só eles:

- `VOCE_SEM_PARTY` — a pergunta não tem sentido, a resposta é "não, por escolha"
- `CEGUEIRA_LONGA` — não há party window para enxergar

Medido, no cenário real (farmando em party → sai → 400 ticks solo → morre):

```
modo_solo=False -> ['voce_sem_party', 'cegueira_longa', 'morreu']
modo_solo=True  -> ['morreu']
```

## O que NÃO muda

Morte e ressurreição com o **mesmo debounce** — não há motivo para a morte dele
ser julgada com critério diferente. A guarda do recorte ilegível vale igual. E
a agenda de TvT/Prime/Solo Boss continua idêntica.

## Três formas de ligar

| Como | Quando |
|---|---|
| `--solo` no arranque | já sabe que vai upar sozinho |
| `.solo` no WhatsApp | a party desfez agora, e você está no jogo |
| `.party` no WhatsApp | voltou pro grupo |

O comando é o que mais faz sentido: a hora de virar solo é quando a party se
desfaz, e nesse momento o usuário está no jogo, não na frente do console.

## O console deixa de mentir por omissão

`[SEM VISAO]` viraria mentira: o scanner não perdeu nada. Agora mostra
`[SOLO - vigiando so voce]` — senão parece quebrado justamente quando está
trabalhando.

## Uma sutileza que um teste expôs

Desligar o solo **não** faz o scanner anunciar imediatamente que você saiu da
party. Em solo a avaliação "você está em party?" é pulada, então `_voce_em_party`
fica indefinido — e a primeira conclusão depois de desligar é começo frio, que
por princípio não anuncia.

Ele precisa **ver** a party primeiro para depois poder dizer que você saiu dela.
Meu teste inicial assumia o contrário e falhou; o comportamento é que estava
certo. Ficaram dois testes travando as duas metades.
