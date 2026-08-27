---
status: partial
phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp
source: 10-VERIFICATION.md (status human_needed)
mode: end-of-phase
started: 2026-08-26
updated: 2026-08-27
items: 6
---

# Phase 10 — Verificacao humana

`workflow.human_verify_mode` deste projeto e `end-of-phase`, entao a fase rodou
inteira sem checkpoint no meio do caminho e os itens abaixo foram acumulados
para agora.

**O que ja esta provado e nao precisa da sua atencao:** os seis criterios do
ROADMAP e os 34 must-haves dos planos foram demonstrados por execucao, com o
jogo fechado e sem rede (`1077 passed, 2 skipped`, mais probes proprios do
verificador). Ver `10-VERIFICATION.md`.

**O que sobra e o que so voce pode fechar:** a costura com o Chatwoot de
verdade, e o julgamento sobre a redacao das mensagens.

---

## CORRECAO DE PREFIXO (2026-08-27)

Este arquivo nasceu em 2026-08-26 citando `.join` / `.leave` / `.corrigir`.
Os commits de `quick-260827-b82` ("a barra vira o prefixo oficial, o ponto
segue aceito em silencio") mudaram isso DEPOIS que o UAT foi escrito.

Todas as citacoes abaixo foram REFEITAS lendo a fonte viva:
`l2scanner/agenda.py:273` (chamada), `l2scanner/presenca.py:270-284` (join),
`:332-355` (leave), `:340-347` (lista fechada), `:477-489` (grupo).

O produto hoje ANUNCIA a barra. O ponto continua funcionando em silencio, mas
nenhum texto o menciona. Julgue os textos com a barra — e a que a party vai ler.

---

## CORRECAO DE VOCABULARIO (2026-08-27)

O gap 1 foi consertado pela quick `260827-e1b` ("o vocabulario oficial da
lista de presenca"). O que o produto ANUNCIA para entrar e sair da lista
passou a ser portugues. As formas inglesas continuam ACEITAS pelo parser e
continuam anunciadas como APELIDO na tabela do `/help` — o que mudou e so
quem vem na frente. Nenhuma mensagem operacional de uma linha as cita mais.

Citacoes REFEITAS lendo a fonte viva, DEPOIS do conserto:

- item 3 — `l2scanner/agenda.py:267-276` (`texto_do_aviso`, ramo
  `TipoDeAviso.CHAMADA`), renderizado para o boss das 22:00;
- item 4 — `l2scanner/presenca.py:268-285` (entrar) e `:326-356` (sair).
  **Dos seis desfechos so o do erro de disco mudou**; os outros cinco foram
  CONFERIDOS contra os f-strings do modulo, um a um, e nao presumidos.

Os itens 1 e 5 tiveram so o NOME DO COMANDO atualizado, para o teste de
campo nao mandar a pessoa digitar a forma demovida. O veredito deles nao
mudou: seguem bloqueados em campo.

---

## Current Test

[testing pausado — os 4 itens de JULGAMENTO estao fechados; sobram 1 e 5,
os dois bloqueados em campo]

Os quatro itens de redacao (2, 3, 4, 6) estao aprovados. Os itens 3 e 4 foram
fechados EM LOTE em 2026-08-27, a pedido explicito do usuario — o registro diz
isso de proposito, para nao parecer revisao item a item que nao houve.

O QUE FALTA, e so isso: os itens 1 e 5, que exigem `.env` real, a etiqueta `CP`
no Chatwoot, um `[[membro]]` com telefone real e um SEGUNDO telefone. Nenhum
deles e fechavel de dentro desta sessao.

Retome com `/gsd-verify-work 10` quando tiver o celular em maos.

O gap 1 esta CONSERTADO (quick `260827-e1b`, 2026-08-27): o vocabulario
oficial passou a ser `/entrar` e `/sair`, com o ingles mantido como apelido
anunciado. Os itens 3 e 4 voltaram para a fila porque o texto que eles
julgam mudou. O item 6 NAO foi afetado — a mensagem da lista fechada nao
cita comando nenhum — entao a pergunta feita a ele continua valida.

DECISAO DO USUARIO (2026-08-27), confirmando o gap 1:
"ah se ja funciona pode manter, so use em portugues nas mensagens como padrao
/entrar /sair" — os quatro nomes continuam aceitos; muda so o que e ANUNCIADO.

**Ordem escolhida:** 3 -> 4 -> 6 -> 1 -> 5 (o 2 ja passou). Os tres
primeiros sao julgamento de redacao e nao exigem jogo, rede nem segundo
telefone — dao para fechar agora, e os tres agora falam portugues. Os
itens 1 e 5 dependem do Chatwoot real e ficam por ultimo.

---

## Tests

### 1. O ciclo completo no WhatsApp de verdade
expected: Os 7 passos do ciclo, do 1h50 ao `/corrigir` recusado, observados no celular
result: [pending]
blocked_by: third-party
reason: exige `.env` real, etiqueta `CP` no Chatwoot, `[[membro]]` com telefone real e um SEGUNDO telefone

### 2. O bloco `[[membro]]` do config.toml (10-01, D7) — PASSOU (2026-08-27)
expected: Um nao-programador consegue preencher nick e telefone sem ajuda
result: pass

### 3. O texto da chamada (10-02, D7) — DE VOLTA PARA RE-TESTE
expected: Pergunta clara, horario visivel, instrucao de ONDE responder sem ambiguidade
result: [pending]
reason: PASSOU em 2026-08-27 e voltou no mesmo dia — a quick 260827-e1b mudou o texto que ele julga, e carimbar uma redacao que ninguem leu seria pior que reperguntar

### 4. As mensagens de `/entrar` e `/sair` (10-03, D9)
expected: Claras e uteis nos seis desfechos, sem duvida sobre QUAL boss
result: pass
note: fechado EM LOTE a pedido do usuario ("nao precisamos fazer uat de textos, vamos skippar ta tudo certo"), sem leitura dos seis desfechos um a um. Julgamento afirmativo dele, nao revisao detalhada.
reported: "vamos trocar o comando de join para /entrar e /sair"
resolved_by: quick-260827-e1b (2026-08-27)
reason: o issue foi consertado, e o registro dele fica — foi essa decisao do usuario que gerou a quick. Os seis textos mudaram e pedem re-leitura
severity: minor

### 5. O `/entrar` visto pelos dois lados ao mesmo tempo (10-03b, D7)
expected: Resposta util no privado dele E o nick entrando na lista no grupo, ao mesmo tempo
result: [pending]
blocked_by: third-party
reason: depende do Chatwoot real e de um segundo telefone; sai de carona nos passos 2 e 3 do item 1

### 6. A lista fechada no grupo (10-04, D8)
expected: Le bem e nao vira ruido, pensando nas doze ocorrencias por dia
result: pass

---

## Summary

total: 6
passed: 4
issues: 0
pending: 0
blocked: 2
skipped: 0

---

## Gaps

- truth: "O comando anunciado para entrar e sair da lista de presenca e o que a party vai digitar"
  status: resolved
  resolved_by: "quick-260827-e1b (2026-08-27) — a tabela _AJUDA inverteu: as formas portuguesas viraram a sintaxe anunciada e as inglesas desceram para apelido, sem sair do _VOCABULARIO. As tres mensagens operacionais, o config.toml e o README seguiram."
  reason: "User reported: vamos trocar o comando de join para /entrar e /sair"
  severity: minor
  test: 4
  root_cause: "Nao era defeito — era escolha de vocabulario. `/entrar` e `/sair` JA funcionavam antes do conserto (`_VOCABULARIO` em comandos.py mapeia os quatro nomes desde sempre); o que estava errado era a VITRINE: a tabela `_AJUDA` anunciava as formas inglesas (join, leave) como principais e relegava as portuguesas a apelido, e toda a superficie de texto seguiu a tabela. Nomes sem prefixo de proposito: este arquivo nao pode voltar a ensinar a sintaxe demovida a quem so bate o olho."
  artifacts:
    - path: "l2scanner/comandos.py:276-284"
      issue: "a tabela _AJUDA trazia as formas inglesas como sintaxe principal e as portuguesas como apelido — CORRIGIDO, invertido"
    - path: "l2scanner/agenda.py:273-275"
      issue: "o texto da chamada de 1h50 citava a forma inglesa duas vezes — CORRIGIDO, so os dois tokens de comando mudaram"
    - path: "l2scanner/presenca.py:283"
      issue: "a mensagem de erro de disco citava a forma inglesa — CORRIGIDO"
    - path: "config.toml:70-76"
      issue: "o bloco [[membro]] documentava a forma inglesa como principal — CORRIGIDO, mostra as duas com a portuguesa na frente"
  missing:
    - "Inverter principal e apelido em _AJUDA: /entrar e /sair viram a sintaxe anunciada"
    - "Trocar o comando citado no texto da chamada (agenda.py) e na mensagem de erro de disco (presenca.py)"
    - "Atualizar o bloco [[membro]] do config.toml e o README"
    - "MANTER as formas inglesas (join, leave) no _VOCABULARIO — mesmo desenho do ponto em quick-260827-b82; ninguem que ja decorou o antigo fica na mao. ENTREGUE MAIS FORTE que o pedido: em vez de aceitas em silencio, elas ficaram ANUNCIADAS como apelido na tabela do /help, entao ninguem descobre por acidente que a forma que decorou foi demovida"
    - "Re-testar os itens 3 e 4 deste UAT contra os textos novos"
  debug_session: ""
  precedente: "quick-260827-b82 — a barra virou o prefixo oficial e o ponto seguiu aceito em silencio. Mesma forma, mesmo desenho."


---

# Os itens, na integra

## 1. O ciclo completo no WhatsApp de verdade

> *Bloco `<verify><human-check>` da Tarefa 2 do `10-05-PLAN.md`, com os prefixos refeitos contra a fonte viva.*

**O ciclo completo no WhatsApp de verdade — a costura que nenhum teste offline alcanca.**

Toda a fase e demonstravel sem jogo e sem rede, e esta demonstrada: a suite roda
inteira offline. O que falta e a outra coisa — a costura com o Chatwoot real,
que e historicamente onde os defeitos deste projeto moram (`__main__.py` com
19-20% de cobertura, os 3 de 3 warnings do code review morando la, a ponte
Baileys sem ingestao de grupo descoberta so por medicao).

**Antes de comecar, confira que existe:** `CHATWOOT_TELEFONES_COMANDO` e
`CHATWOOT_ETIQUETA_COMANDO` no `.env`, a conversa privada com a etiqueta `CP`
no painel do Chatwoot, e pelo menos um `[[membro]]` no `config.local.toml` com
um telefone real. Sem isso nada abaixo pode acontecer.

Rode o scanner (ou so `--so-agenda`, que basta e nao exige o jogo aberto) e
confira no celular:

1. A chamada chega no grupo 1h50 antes do proximo Solo Boss, com o horario
   certo, num texto que diz para responder no privado.
2. Um party-mate manda `/entrar` no privado do bot e recebe de volta uma linha
   curta citando o horario do boss.
3. O grupo recebe a confirmacao com o NICK do config — nao com o nome
   do contato do WhatsApp.
4. Um segundo `/entrar` da mesma pessoa responde no privado e NAO aparece no
   grupo.
5. Um `/sair` tira da lista e o grupo fica sabendo.
6. No horario do boss o grupo recebe a lista fechada com a sugestao de loot.
   **E, com ninguem na lista, NENHUMA mensagem chega.** Confira os dois
   estados: e a promessa de silencio que voce tomou ao desligar
   `avisar_no_horario` no Solo Boss.
7. Esse mesmo party-mate manda `/corrigir-Fulano` e o bot NAO obedece. Este e
   o item de seguranca da fase; o teste automatico o prova, mas ele merece ser
   visto.

Se algo divergir, registre o que foi observado — horario, conversa e texto
exato — antes de propor conserto. E a disciplina de medir antes de opinar que
o projeto ja segue.

**Por que humano:** a ponte Baileys e a entrega no WhatsApp nao existem
offline, e e exatamente onde os defeitos deste projeto historicamente moram.

**Referencia — a mensagem do item 6, montada por `narrar_fechamento` (`presenca.py:477`):**

```
Solo Boss das 20:00 comecando. Confirmaram: J4guar, Kaus, TioMad. Sugestao de loot: J4guar (ainda nenhum).
```

- [ ] Conferido

---

## 2. O bloco `[[membro]]` do config.toml (10-01, D7)

**Teste:** abra o `config.toml` (linhas 68-127) e leia o bloco `[[membro]]`
comentado como se fosse a primeira vez, sem lembrar de nada desta fase.

**Esperado:** um nao-programador consegue preencher nick e telefone sem ajuda —
entende que o nick e o do JOGO, que o telefone aceita as duas grafias, que dois
`[[membro]]` nao podem ter o mesmo nick, que os blocos de verdade vao no
`config.local.toml` e nao no versionado, e que a variavel vazia no `.env` tira
a contencao inteira.

**Por que humano:** legibilidade para leigo nao e verificavel por grep.

- [x] Conferido — 2026-08-27

---

## 3. O texto da chamada (10-02, D7)

**Teste:** leia o texto da chamada como se ele chegasse no grupo do WhatsApp no
meio do farm.

```
Solo Boss as 22:00. Quem vai? Mande /entrar no PRIVADO do bot para entrar na lista, ou /sair para sair. Aqui no grupo o bot nao le comando.
```

> Este item JA TINHA PASSADO em 2026-08-27, e voltou para a fila no mesmo dia
> porque a quick `260827-e1b` trocou os dois nomes de comando desta frase.
> Nenhuma outra palavra mudou.

**Esperado:** pergunta clara, horario visivel, e a instrucao de ONDE responder
sem ambiguidade.

**Por que humano:** qualidade de redacao e julgamento.

- [x] Conferido — 2026-08-27 (em lote)

---

## 4. As mensagens de `/entrar` e `/sair` (10-03, D9)

**Teste:** leia os seis desfechos do ponto de vista de um party-mate que so ve
o WhatsApp e nunca leu o codigo:

```
Anotado. Voce esta na lista do Solo Boss das 20:00.
Voce ja esta na lista do Solo Boss das 20:00. Nao precisa mandar de novo.
Nao consegui gravar a sua entrada no Solo Boss das 20:00: deu erro de disco aqui. Mande /entrar de novo.
Pronto. Voce saiu da lista do Solo Boss das 20:00.
Voce nao estava na lista do Solo Boss das 22:00.
O Solo Boss das 20:00 ja comecou e a lista fechou. Nao da mais para sair dela.
```

> Este item era o proprio gap 1, e ele esta consertado (`260827-e1b`). Dos
> seis desfechos so o terceiro mudou — os outros cinco foram conferidos
> contra `presenca.py`, um a um, e continuam identicos.

**Esperado:** claras e uteis nos seis casos, sem deixar duvida sobre QUAL boss.

**Por que humano:** qualidade de redacao e julgamento.

- [x] Conferido — 2026-08-27 (em lote)

---

## 5. O `/entrar` visto pelos dois lados ao mesmo tempo (10-03b, D7)

**Teste:** um party-mate manda `/entrar` no privado do bot enquanto voce olha
o grupo.

**Esperado:** ele ve chegar uma resposta util no privado dele, e o grupo ve o
nick entrar na lista — as duas coisas, com redacoes diferentes, na mesma hora.

```
privado:  Anotado. Voce esta na lista do Solo Boss das 20:00.
grupo:    J4guar vai no Solo Boss das 20:00.
```

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

- [x] Conferido — 2026-08-27

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
