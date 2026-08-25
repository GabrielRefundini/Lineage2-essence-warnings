---
status: complete
---

# Comandos só do meu número, e etiqueta como interruptor

**Concluído:** 2026-08-24 · 413 testes (398 + 15)

## A resposta à pergunta

*"O bot recebe comandos apenas do meu número?"* — **não recebia.** A trava era
por conversa. No privado dava na mesma; num grupo, os doze membros mandariam.

Agora recebe: `CHATWOOT_TELEFONES_COMANDO=+5544997077000`.

## As duas coisas resolvem problemas diferentes

| | Responde | Onde se muda |
|---|---|---|
| Telefone | *quem* pode mandar | `.env` |
| Etiqueta | *onde* ele escuta | painel do Chatwoot, vale na hora |

## O nono dígito quase quebrou isso em silêncio

Você escreveu `+5544997077000`. O Chatwoot registra o dono do seu grupo como
`554497077000` — **sem o 9**. Mesma pessoa, duas formas, as duas circulando.

Comparação exata falharia sem erro nenhum: o comando seria ignorado e ninguém
saberia por quê. Para uma trava de segurança esse é o pior modo de falha.

Comparo os **últimos 8 dígitos**, o que atravessa código de país, DDD,
formatação e o nono dígito. Preço: dois números com os mesmos 8 dígitos finais
colidem — aceitável numa lista de 2 a 5 pessoas, e está documentado.

## Um bug que o teste pegou

Configuração **só por etiqueta**, sem conversa fixa, nunca lia nada: a guarda
do `ler()` checava `self._conversas` em vez de `self.ativo`. Retornava cedo,
sem erro. O teste de falha de rede foi o que expôs.

## Decisão de segurança

Falha ao listar etiquetas devolve lista **vazia**, não a anterior. Se a
listagem cair, o certo é ouvir **menos**, nunca mais — uma falha de rede não
pode abrir canal nenhum.

## Não feito, de propósito

O scanner não **escreve** etiqueta. Ele é leitor; marcar é ato do admin, e é
justamente isso que torna a etiqueta um interruptor confiável.
