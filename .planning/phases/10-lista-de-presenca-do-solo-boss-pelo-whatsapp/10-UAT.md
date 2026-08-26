---
phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp
created: 2026-08-26
source: 10-VERIFICATION.md (status human_needed)
mode: end-of-phase
items: 6
---

# Phase 10 — Verificacao humana

`workflow.human_verify_mode` deste projeto e `end-of-phase`, entao a fase rodou
inteira sem checkpoint no meio do caminho e os itens abaixo foram acumulados
para agora.

**O que ja esta provado e nao precisa da sua atencao:** os seis criterios do
ROADMAP e os 34 must-haves dos planos foram demonstrados por execucao, com o
jogo fechado e sem rede (`1051 passed, 2 skipped`, mais probes proprios do
verificador). Ver `10-VERIFICATION.md`.

**O que sobra e o que so voce pode fechar:** a costura com o Chatwoot de
verdade, e o julgamento sobre a redacao das mensagens.

---

## 1. O ciclo completo no WhatsApp de verdade

> *Bloco `<verify><human-check>` da Tarefa 2 do `10-05-PLAN.md`, reproduzido verbatim.*

**O ciclo completo no WhatsApp de verdade — a costura que nenhum teste offline alcanca.**

Toda a fase e demonstravel sem jogo e sem rede, e esta demonstrada: a suite roda
inteira offline. O que falta e a outra coisa — a costura com o Chatwoot real,
que e historicamente onde os defeitos deste projeto moram (`__main__.py` com
19-20% de cobertura, os 3 de 3 warnings do code review morando la, a ponte
Baileys sem ingestao de grupo descoberta so por medicao).

**Antes de comecar, confira que existe:** `CHATWOOT_TELEFONES_COMANDO` e
`CHATWOOT_ETIQUETA_COMANDO` no `.env`, a conversa privada com a etiqueta `CP`
no painel do Chatwoot, e pelo menos um `[[membro]]` no `config.toml` com um
telefone real. Sem isso nada abaixo pode acontecer.

Rode o scanner (ou so `--so-agenda`, que basta e nao exige o jogo aberto) e
confira no celular:

1. A chamada chega no grupo 1h50 antes do proximo Solo Boss, com o horario
   certo, num texto que diz para responder no privado.
2. Um party-mate manda `.join` no privado do bot e recebe de volta uma linha
   curta citando o horario do boss.
3. O grupo recebe a confirmacao com o NICK do `config.toml` — nao com o nome
   do contato do WhatsApp.
4. Um segundo `.join` da mesma pessoa responde no privado e NAO aparece no
   grupo.
5. Um `.leave` tira da lista e o grupo fica sabendo.
6. No horario do boss o grupo recebe a lista fechada com a sugestao de loot.
   **E, com ninguem na lista, NENHUMA mensagem chega.** Confira os dois
   estados: e a promessa de silencio que voce tomou ao desligar
   `avisar_no_horario` no Solo Boss.
7. Esse mesmo party-mate manda `.corrigir-Fulano` e o bot NAO obedece. Este e
   o item de seguranca da fase; o teste automatico o prova, mas ele merece ser
   visto.

Se algo divergir, registre o que foi observado — horario, conversa e texto
exato — antes de propor conserto. E a disciplina de medir antes de opinar que
o projeto ja segue.

**Por que humano:** a ponte Baileys e a entrega no WhatsApp nao existem
offline, e e exatamente onde os defeitos deste projeto historicamente moram.

**Referencia — a mensagem do item 6 medida num ciclo completo fora da suite:**

```
Solo Boss das 20:00 comecando. Confirmaram: J4guar, Kaus, TioMad. Sugestao de loot: J4guar (ainda nenhum).
```

- [ ] Conferido

---

## 2. O bloco `[[membro]]` do config.toml (10-01, D7)

**Teste:** abra o `config.toml` e leia o bloco `[[membro]]` comentado como se
fosse a primeira vez, sem lembrar de nada desta fase.

**Esperado:** um nao-programador consegue preencher nick e telefone sem ajuda —
entende que o nick e o do JOGO, que o telefone aceita as duas grafias, que dois
`[[membro]]` nao podem ter o mesmo nick, e que a variavel vazia no `.env` tira a
contencao inteira.

**Por que humano:** legibilidade para leigo nao e verificavel por grep.

- [ ] Conferido

---

## 3. O texto da chamada (10-02, D7)

**Teste:** leia o texto da chamada como se ele chegasse no grupo do WhatsApp no
meio do farm.

```
Solo Boss as 22:00. Quem vai? Mande .join no PRIVADO do bot para entrar na lista, ou .leave para sair. Aqui no grupo o bot nao le comando.
```

**Esperado:** pergunta clara, horario visivel, e a instrucao de ONDE responder
sem ambiguidade.

**Por que humano:** qualidade de redacao e julgamento.

- [ ] Conferido

---

## 4. As mensagens de `.join` e `.leave` (10-03, D9)

**Teste:** leia os seis desfechos do ponto de vista de um party-mate que so ve
o WhatsApp e nunca leu o codigo:

```
Anotado. Voce esta na lista do Solo Boss das 20:00.
Voce ja esta na lista do Solo Boss das 20:00. Nao precisa mandar de novo.
Nao consegui gravar a sua entrada no Solo Boss das 20:00: deu erro de disco aqui. Mande .join de novo.
Pronto. Voce saiu da lista do Solo Boss das 20:00.
Voce nao estava na lista do Solo Boss das 22:00.
O Solo Boss das 20:00 ja comecou e a lista fechou. Nao da mais para sair dela.
```

**Esperado:** claras e uteis nos seis casos, sem deixar duvida sobre QUAL boss.

**Por que humano:** qualidade de redacao e julgamento.

- [ ] Conferido

---

## 5. O `.join` visto pelos dois lados ao mesmo tempo (10-03b, D7)

**Teste:** um party-mate manda `.join` no privado do bot enquanto voce olha o
grupo.

**Esperado:** ele ve chegar uma resposta util no privado dele, e o grupo ve o
nick entrar na lista — as duas coisas, com redacoes diferentes, na mesma hora.

**Por que humano:** depende do Chatwoot real e de um segundo telefone. (Se
fizer o item 1 por inteiro, este item sai de carona nos passos 2 e 3.)

- [ ] Conferido

---

## 6. A lista fechada no grupo (10-04, D8)

**Teste:** leia a mensagem da lista fechada pensando nas **doze ocorrencias por
dia** do Solo Boss.

```
Solo Boss das 20:00 comecando. Confirmaram: J4guar, TioMad. Sugestao de loot: J4guar (ainda nenhum).
```

**Esperado:** le bem e nao vira ruido. Lembre que o piso e silencio — com
ninguem na lista, zero mensagem —, entao o volume real e "uma por boss que
alguem confirmou", nao doze.

**Por que humano:** percepcao de volume e de ruido e julgamento.

- [ ] Conferido

---

## Depois de fechar os seis

Se tudo passar, a fase esta completa. Se algo divergir, registre **horario,
conversa e texto exato** antes de propor conserto, e rode
`/gsd-plan-phase 10 --gaps`.

Duas recomendacoes de endurecimento ficaram registradas em `10-VERIFICATION.md`
(W-1: derivar o portao de `_PREFIXOS_CONHECIDOS`; W-2: alargar o portao de
import do `loot.py` para `comandos`/`sessao`). Nao bloqueiam nada — as duas
afirmacoes sao verdadeiras hoje, so nao estao guardadas contra amanha. Cabem
num `/gsd-quick`.
