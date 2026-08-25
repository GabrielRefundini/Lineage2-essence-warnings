# Quick: comandos só do meu número, e etiqueta como interruptor

**Pedido:** "o bot recebe comandos apenas do meu numero? +5544997077000 — dá para
por uma tag/etiqueta da conversa no meu contato do Chatwoot admin"

**Resposta à pergunta:** hoje **não**. A trava é por CONVERSA, não por quem
escreve. No privado dá na mesma; num grupo, qualquer membro mandaria no scanner.

## As duas coisas resolvem problemas diferentes

| | Responde | Onde muda |
|---|---|---|
| **Telefone** | *quem* pode mandar | `.env` |
| **Etiqueta** | *onde* ele escuta | painel do Chatwoot |

O telefone é a fronteira de segurança de verdade — vale até dentro de um grupo.
A etiqueta é conveniência de administração: marcar/desmarcar no painel, sem
editar arquivo e sem reiniciar.

## A armadilha do nono dígito

O usuário escreveu `+5544997077000`. O Chatwoot registra o dono do grupo como
`554497077000@s.whatsapp.net` — **sem o 9**. É a mesma pessoa e as duas formas
circulam: celulares brasileiros ganharam um nono dígito e a base do WhatsApp
tem os dois.

Comparação exata falharia em silêncio — o pior modo, porque o comando
simplesmente seria ignorado sem erro nenhum.

**Solução:** comparar os **últimos 8 dígitos**. Verificado nos dois formatos:

```
+5544997077000 -> 97077000
 554497077000  -> 97077000
```

Absorve código de país, DDD, parênteses, traços e o nono dígito. O preço é que
dois números diferentes com os mesmos 8 dígitos finais colidem — aceitável
numa allowlist de 2 a 5 pessoas, e documentado.

## Tarefas

1. **`telefone_equivalente()`** puro, em `comandos.py`. Normaliza e compara por
   sufixo. Testes com todas as formas que circulam.
2. **Allowlist de telefone** (`CHATWOOT_TELEFONES_COMANDO`). Vazia = aceita
   qualquer um da conversa permitida, com AVISO no arranque — porque quem ligou
   comandos sem restringir número provavelmente não pensou nisso.
3. **Etiqueta** (`CHATWOOT_ETIQUETA_COMANDO`). Conversas com essa etiqueta
   viram canal de comando, somadas às configuradas por id.
4. **Diagnóstico** mostra qual número e qual etiqueta estão valendo, e avisa
   quando comandos estão abertos a qualquer um.

## Fora de escopo

- Escrever a etiqueta pelo scanner. Ele é leitor; marcar é ato do admin, e é
  justamente isso que torna a etiqueta um interruptor confiável.
- Bloquear por `sender.id` do Chatwoot. O telefone é o que o usuário conhece e
  o que sobrevive a recriar o contato.
