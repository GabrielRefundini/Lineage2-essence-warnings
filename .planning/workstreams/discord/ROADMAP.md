# Roadmap: Ponte Discord (v1.0)

**Workstream:** discord (`.planning/workstreams/discord/`)
**Milestone:** v1.0 — Ponte Discord
**Created:** 2026-08-28
**Core Value:** Quem nao abre o Discord fica sabendo do anuncio no WhatsApp, em segundos.

## Overview

O milestone constroi UM processo novo que ouve dois canais do servidor XM Games e
repete cada postagem numa conversa dedicada do Chatwoot. A metade de saida ja
existe e roda em producao (`NotificadorChatwoot`), entao o trabalho de verdade
esta todo na metade de entrada — e a metade de entrada tem um portao humano que
nao da para contornar.

A sequencia sai desse portao. A intent **MESSAGE CONTENT** so pode ser ligada
por uma pessoa no painel do Discord. Sem ela o bot conecta, aparece saudavel, e
entrega mensagem em BRANCO para sempre. Esse e o modo de falha mais caro do
milestone, e por isso a Fase 1 nao formata nada e nao entrega nada: ela existe
para provar, com o usuario olhando o console, que texto de verdade esta chegando.
So depois disso a Fase 2 investe em deixar o texto legivel no celular e a Fase 3
liga a saida. Formatar antes de provar o texto seria formatar o vazio.

ENTR-04 (nunca entregar o mesmo anuncio duas vezes) fica na Fase 1 de proposito,
apesar de ser uma exigencia de ENTREGA. O livro de "ja vistos" decide como cada
mensagem recebida e identificada e persistida — e isso e a PRIMEIRA linha do
caminho de recebimento, nao a ultima. Deixar para a Fase 3 significaria reescrever
o caminho de recebimento inteiro quando o primeiro restart duplicasse a fila.

**Nota de arquitetura:** a ponte NAO toca `l2scanner/__main__.py` (2047 linhas,
editado em paralelo pelo workstream `mercado`) e NAO toca `l2scanner/notificador.py`.
Modulo proprio, entrypoint proprio, `.bat` proprio. Alem de evitar o unico
conflito de merge real, e a arquitetura certa: a ponte e async e orientada a
evento, o scanner e um laco sincrono de 1 Hz.

**Nota de nomenclatura:** o modulo novo segue o idioma do repo — portugues sem
acento (`ponte_discord`, ao lado de `notificador`, `presenca`, `rastreador`,
`gravador`). Os slugs de diretorio das fases levam o prefixo `discord-`
(ex.: `phases/01-discord-ponte-viva/`) para que escopos de commit nunca colidam
com as fases dos workstreams `mercado` e `default`.

**Nota de dependencia:** a unica dependencia nova do projeto (a biblioteca
cliente do Discord) entra na Fase 1, junto do teste `tests/test_firewall_escopo.py`
rodando verde. O firewall e uma BANLIST de bibliotecas de sintese de input, entao
a dependencia passa limpa — mas isso e para se VER passando, nao para se supor.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Ponte viva — conexao provada e texto real** - Processo proprio que conecta, ouve so os dois canais, mostra o texto de verdade no console e nunca reprocessa o que ja viu
- [ ] **Phase 2: Texto legivel no celular** - Origem, autor, mencoes resolvidas, postagem so-com-imagem que nao some, e mensagem longa truncada em vez de perdida
- [ ] **Phase 3: Entrega no WhatsApp** - Reuso do `NotificadorChatwoot` numa conversa dedicada, com repeticao de falha transitoria e ponte que sobrevive a falha definitiva

## Phase Details

### Phase 1: Ponte viva — conexao provada e texto real

**Goal**: O usuario ve, no console, o texto REAL de uma mensagem que ele acabou de postar no Discord — e com isso o portao humano fica provado antes de qualquer linha de formatacao ou de entrega existir.
**Depends on**: Nothing (first phase)
**Requirements**: PONTE-01, PONTE-02, PONTE-03, PONTE-04, PONTE-05, CONF-01, CONF-02, CONF-03, CONF-04, ENTR-04, OPER-01, OPER-02, OPER-03
**Success Criteria** (what must be TRUE):

  1. O usuario da duplo clique no `.bat` novo da raiz e ve no console que a ponte conectou no servidor XM Games com o token do `.env` e esta ouvindo os dois canais configurados; o `vigiar-party.bat` continua rodando ao lado, intocado, e nenhum dos dois sente o outro subir ou cair
  2. **PORTAO HUMANO — este criterio NAO pode ser conferido antes dos 4 passos do "Portao humano" do REQUIREMENTS.md.** Com a intent MESSAGE CONTENT ligada pelo usuario, uma mensagem postada em qualquer um dos dois canais aparece no console em segundos com o TEXTO de verdade, e o console mostra que a ponte esta viva e qual foi a ultima mensagem vista. Se o texto chegar VAZIO, a ponte diz isso alto e nomeia a intent como causa provavel — ela nunca finge estar saudavel replicando branco
  3. Mensagem postada em qualquer OUTRO canal do servidor nao aparece; mensagem postada por bot ou webhook nos dois canais alvo APARECE (e o caso principal — anuncio de guild costuma vir de bot); mensagem que a propria ponte enviou nao volta; e nao existe filtro de autor, cargo ou mencao descartando nada alem disso
  4. O usuario mata a ponte e sobe de novo: as mensagens que ela ja tinha visto antes do restart nao reaparecem, e o log rotativo proprio da ponte (separado do log do scanner) mostra a mesma sessao do console
  5. Apagar o token do `.env`, ou uma chave da secao do `config.toml` (guild, canal, conversa de destino), faz a ponte MORRER no arranque dizendo qual chave falta e como consertar — nunca subir muda. E `tests/test_firewall_escopo.py` continua verde com a dependencia nova do Discord na arvore

**Plans**: TBD

**Bloqueio externo — explicito:** os 4 passos do portao humano (criar a aplicacao,
ligar MESSAGE CONTENT, convidar o bot com `View Channel` + `Read Message History`,
informar o `conversation_id` de destino) so o USUARIO pode fazer. O criterio 2
desta fase fica pendente ate la, mesmo que todo o codigo esteja pronto. A Fase 2
nao deve ser planejada em detalhe antes do criterio 2 estar conferido — formatar
texto que nunca se provou existir e trabalho em cima de suposicao.

**Nota sobre CONF-04 e ENTR-04:** o modo simulacao (CONF-04) nasce aqui porque e
ele que torna o criterio 2 conferivel sem incomodar o grupo do WhatsApp — nesta
fase a ponte SO simula. E ENTR-04 mora aqui, e nao na Fase 3, porque o livro de
ja-vistos define como a mensagem recebida e identificada logo na entrada; enfiar
isso depois custaria reescrever o caminho de recebimento inteiro.

### Phase 2: Texto legivel no celular

**Goal**: O que aparece no console em modo simulacao ja e a mensagem que uma pessoa leria no celular e entenderia sem abrir o Discord.
**Depends on**: Phase 1 (caminho de recebimento provado, modo simulacao, texto real chegando)
**Requirements**: FORM-01, FORM-02, FORM-03, FORM-04, FORM-05
**Success Criteria** (what must be TRUE):

  1. Com a ponte em modo simulacao, o usuario posta no Canal A e depois no Canal B e consegue dizer, olhando so o console, de qual canal veio cada uma e quem postou — os dois canais no mesmo destino nao viram uma pilha ambigua
  2. Uma mensagem contendo `@pessoa`, `@cargo`, `#canal` e emoji custom aparece com o nome da pessoa, o nome do cargo, o nome do canal e `:nome:` — zero numero cru de ID sobra no texto
  3. Uma mencao que a ponte nao consegue resolver (pessoa que saiu, cargo apagado) vira algo legivel em vez de `<@123456>` cru, e nao derruba a ponte nem engole a mensagem inteira
  4. Uma postagem SO com imagem ou anexo, sem texto nenhum, ainda produz uma linha curta avisando que houve postagem com imagem naquele canal — cartaz de evento nao pode sumir calado, mesmo sem a imagem viajar junto
  5. Uma mensagem longa demais para uma entrega sai truncada com marca visivel de corte no fim; o usuario consegue provocar isso postando um texto gigante e ver que a mensagem chegou cortada, nunca recusada nem perdida

**Plans**: TBD

### Phase 3: Entrega no WhatsApp

**Goal**: O anuncio postado no Discord chega no grupo do WhatsApp em segundos, na conversa certa, e nenhuma falha do Chatwoot derruba a ponte nem duplica a mensagem.
**Depends on**: Phase 2 (texto ja formatado), Phase 1 (livro de ja-vistos)
**Requirements**: ENTR-01, ENTR-02, ENTR-03
**Success Criteria** (what must be TRUE):

  1. Com o modo simulacao DESLIGADO, o usuario posta no canal do Discord e le a mensagem ja formatada no grupo do WhatsApp em segundos
  2. O anuncio cai na conversa dedicada do Chatwoot e a conversa que recebe morte e saida de party nao recebe NADA de anuncio de guild — o usuario confere abrindo as duas conversas lado a lado
  3. `l2scanner/notificador.py` fica byte-identico ao fim do milestone: `git diff` nesse arquivo volta vazio, e a entrega e uma chamada de `NotificadorChatwoot.enviar(texto, conversa_alvo)` com a conversa dedicada como alvo
  4. Com o Chatwoot fora do ar (5xx, timeout, rede), o anuncio e reentregue com espera crescente e chega quando o Chatwoot volta; com um `conversation_id` errado (4xx), o erro aparece no console e no log da ponte e a ponte SEGUE VIVA recebendo as proximas mensagens
  5. Uma reentrega apos falha transitoria nao gera mensagem dobrada no grupo — o usuario derruba o Chatwoot no meio de um envio, deixa voltar, e conta UMA mensagem no WhatsApp

**Plans**: TBD

## Progress

**Execution Order:** 1 → 2 → 3 (serial por construcao — a Fase 2 formata o texto
que a Fase 1 provou existir, e a Fase 3 entrega o texto que a Fase 2 formatou).

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Ponte viva — conexao provada e texto real | 0/TBD | Not started | - |
| 2. Texto legivel no celular | 0/TBD | Not started | - |
| 3. Entrega no WhatsApp | 0/TBD | Not started | - |

## Coverage

As 21 exigencias v1 mapeadas, cada uma em exatamente uma fase:

| Category | Requirements | Phase |
|----------|--------------|-------|
| Ponte | PONTE-01, PONTE-02, PONTE-03, PONTE-04, PONTE-05 | 1 |
| Configuracao | CONF-01, CONF-02, CONF-03, CONF-04 | 1 |
| Entrega | ENTR-04 | 1 |
| Operacao | OPER-01, OPER-02, OPER-03 | 1 |
| Formato | FORM-01, FORM-02, FORM-03, FORM-04, FORM-05 | 2 |
| Entrega | ENTR-01, ENTR-02, ENTR-03 | 3 |

**Total:** 21/21 mapeadas. Nenhuma orfa, nenhuma duplicada.

---
*Roadmap created: 2026-08-28 — awaiting user approval (orchestrator commits)*
