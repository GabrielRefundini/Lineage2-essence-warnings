# Fase 7 — Silenciamento por janela de evento

**Concluída:** 2026-08-24
**Commits:** `6b24e54`, `41465c0`, e o desta tarefa
**Testes:** 310 → 335 (25 novos)

## Critérios de sucesso, um a um

| # | Critério | Verificação |
|---|---|---|
| 1 | Nenhum evento do scanner chega ao WhatsApp durante a janela | Teste do `Despachante` com silêncio ativo; o padrão da categoria é `NORMAL`, então uma fonte nova que esqueça de declarar cai no lado seguro |
| 2 | TvT 15 min, Prime 2h | Varredura minuto a minuto de uma segunda inteira |
| 3 | Seg-qui o silêncio acaba 22:05, não 22:00 | Teste da união + simulação ao vivo |
| 4 | O lembrete do TvT das 21h40 atravessa o silêncio do Prime | Simulação ao vivo e teste de categoria |
| 5 | Uma mensagem no fim, nomeando quem terminou por último | Teste que atravessa a janela inteira e conta 1 |
| 6 | Silenciado continua no log e no console | Teste do outbox + o status mostra até quando |

## A simulação que fecha a fase

```
21:40  AVISO TvT antes  | SILENCIO ate 22:00 (Prime)
21:50  AVISO TvT agora  | SILENCIO ate 22:05 (TvT)
22:00                   | SILENCIO ate 22:05 (TvT)
22:05                   | sem silencio
```

Os três comportamentos difíceis numa tela só: a agenda atravessando, a união
estendendo o fim, e o Prime acabando sem levar o TvT junto.

## O que a execução ensinou

**A distinção "verdadeiro mas irrelevante" decidiu a arquitetura.** Porque os
alertas durante um TvT não estão errados, silenciá-los não pode tocar na
detecção — o rastreador segue decidindo e registrando tudo. O corte é uma
categoria no `despachar()`, e só.

**O padrão da categoria é `NORMAL`, e isso é de segurança.** Uma fonte de
eventos futura que esqueça de declarar categoria fica calada durante o evento,
em vez de vazar.

**O silenciado não entra no outbox.** O outbox existe para garantir que nada se
perca no caminho da rede. Uma mensagem que decidimos não enviar não está a
caminho de lugar nenhum — ela está no log, que é onde pertence.

**Um bug que o próprio teste pegou.** No começo frio, "acabei de entrar na
janela" e "subi já dentro dela" são indistinguíveis: nos dois casos a janela
anterior era `None`. O scanner anunciava o encerramento de um evento que nunca
viu começar — o mesmo erro que produziu três alarmes falsos de arranque mais
cedo hoje. Corrigido com um terceiro estado: só conta como "vi começar" depois
de ter observado ao menos um instante **sem** silêncio.

Esse padrão já apareceu quatro vezes neste projeto. Vale como regra: **toda
máquina de estado que anuncia transições precisa distinguir "mudou" de "foi
assim que eu encontrei".**

## Fronteira respeitada

"Os convites estão sendo reenviados" é **texto**. O scanner nunca envia input ao
jogo. Há um teste que afirma que a mensagem não contém promessa de convidar
ninguém — a restrição está travada por asserção, não só por intenção.
