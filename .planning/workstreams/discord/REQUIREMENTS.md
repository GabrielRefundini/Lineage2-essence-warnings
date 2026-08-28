# Requirements: Ponte Discord

**Defined:** 2026-08-28
**Milestone:** v1.0 — Ponte Discord
**Workstream:** discord
**Core Value:** Quem nao abre o Discord fica sabendo do anuncio no WhatsApp, em segundos.

## Contexto herdado (nao repesquisar)

A metade de saida JA EXISTE E RODA EM PRODUCAO neste repo:

- `l2scanner/notificador.py:249` — `NotificadorChatwoot`, um POST por conversa.
- `l2scanner/notificador.py:255` — `enviar(texto, conversa_alvo)` ja aceita
  destino por parametro. Mandar para UMA conversa especifica e chamada direta,
  nao mudanca de codigo.
- `l2scanner/notificador.py:275` — `_postar` usa `urllib` da stdlib e o header
  plano `api_access_token`. Nao usa `requests`.
- `l2scanner/notificador.py:241` — `ErroDeEntrega` ja separa transitorio de
  definitivo (4xx definitivo, 5xx e 429 transitorio).

Consequencia: a ponte NAO altera `notificador.py`, e a unica dependencia nova
do projeto e a do lado Discord.

**Pesquisa de dominio pulada de proposito.** `.planning/research/` e
COMPARTILHADO entre workstreams e ja carrega 220 KB da pesquisa que a fase 1 do
workstream `mercado` consome. Rodar os 4 agentes de pesquisa sobrescreveria
`STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md` e `SUMMARY.md`. Como
a stack aqui ja e conhecida (bot do Discord de um lado, cliente Chatwoot pronto
do outro), a pesquisa custaria a pesquisa do mercado e nao compraria nada.

## Alvos configurados

| Item | Valor |
|------|-------|
| Guild | `936957935572103169` (XM Games) |
| Canal A | `1536506379752185953` |
| Canal B | `1538202612762022020` |
| Destino | UMA conversa do Chatwoot, propria, separada dos avisos de party |

## v1 Requirements

### Ponte

- [ ] **PONTE-01**: A ponte conecta no Discord com um token de bot proprio e
      permanece conectada enquanto o processo roda.
- [ ] **PONTE-02**: A ponte le mensagens novas dos dois canais configurados e
      ignora todo o resto do servidor.
- [ ] **PONTE-03**: TODA mensagem postada nesses canais e replicada — sem filtro
      de autor, de cargo ou de mencao.
- [ ] **PONTE-04**: A ponte ignora as mensagens que ela mesma enviou, mas ACEITA
      mensagens de outros bots e webhooks — anuncio de guild costuma ser postado
      por bot, e descartar bot descartaria o caso principal.
- [ ] **PONTE-05**: A ponte roda como processo separado do scanner. Subir, cair
      ou reiniciar um nao afeta o outro.

### Formato

- [ ] **FORM-01**: A mensagem no WhatsApp identifica o canal de origem, para que
      dois canais no mesmo destino nao virem uma pilha ambigua.
- [ ] **FORM-02**: A mensagem identifica quem postou no Discord.
- [ ] **FORM-03**: Marcacao crua do Discord vira texto legivel: `<@123>` e
      `<@&123>` viram o nome da pessoa ou do cargo, `<#123>` vira o nome do
      canal, `<:nome:123>` vira `:nome:`. Sem isso o anuncio chega no celular
      cheio de numero e ninguem entende.
- [ ] **FORM-04**: Mensagem sem texto (so anexo ou so imagem) gera um aviso curto
      dizendo que houve uma postagem com imagem no canal. Ela NAO carrega o
      anexo — mas tambem nao pode sumir calada, porque cartaz de evento e
      exatamente o anuncio que nao pode ser perdido.
- [ ] **FORM-05**: Mensagem longa demais para uma entrega e truncada com marca
      visivel de corte, em vez de ser recusada pela API e perdida.

### Entrega

- [ ] **ENTR-01**: A entrega reusa `NotificadorChatwoot` sem alterar
      `l2scanner/notificador.py`.
- [ ] **ENTR-02**: Os anuncios caem numa conversa do Chatwoot separada da que
      recebe morte e saida de party — anuncio de guild nao pode diluir alerta de
      morte.
- [ ] **ENTR-03**: Falha transitoria de entrega (5xx, 429, rede) e repetida com
      espera crescente; falha definitiva (4xx) e registrada e a ponte segue viva.
- [ ] **ENTR-04**: Um mesmo anuncio nunca e entregue duas vezes, mesmo se a ponte
      reiniciar ou o Discord reenviar o evento.

### Configuracao

- [ ] **CONF-01**: O token do bot do Discord fica no `.env`, nunca no
      `config.toml` — mesma regra que ja vale para o token do Chatwoot.
- [ ] **CONF-02**: Guild, canais e conversa de destino ficam no `config.toml`,
      em secao propria.
- [ ] **CONF-03**: Config invalida ou faltando falha no ARRANQUE, alto e claro,
      dizendo qual chave falta e como consertar. Nunca silenciosamente sem
      replicar.
- [ ] **CONF-04**: Existe modo simulacao que mostra no console o que SERIA
      enviado, sem postar no WhatsApp — para testar sem incomodar o grupo.

### Operacao

- [ ] **OPER-01**: A ponte sobe por um `.bat` proprio, no mesmo padrao dos
      `.bat` que ja existem na raiz.
- [ ] **OPER-02**: A ponte escreve log rotativo proprio, separado do log do
      scanner.
- [ ] **OPER-03**: O console mostra que a ponte esta viva e conectada, e a
      ultima mensagem replicada.

## Future Requirements

- **MIDIA-01**: Reenviar imagem e anexo como midia de verdade (endpoint
  multipart do Chatwoot, nao o POST simples de `content`).
- **VIA-01**: Via inversa — responder do WhatsApp para o canal do Discord.
- **EDIT-01**: Refletir edicao e exclusao de mensagem feita no Discord.

## Out of Scope

| Item | Motivo |
|------|--------|
| Reenviar o anexo como midia | Exige o caminho multipart do Chatwoot; `content` simples resolve o texto, que e o anuncio. Vai para MIDIA-01. |
| Via inversa (WhatsApp -> Discord) | Abre superficie de comando e de abuso. O scanner ja tem canal de comando com etiqueta e lista de telefone; misturar as duas coisas aqui e risco sem pedido. |
| Historico retroativo | A ponte replica o que for postado DEPOIS que ela subir. Varrer historico transformaria um restart num flood no grupo. |
| Threads e posts de forum | Nenhum dos dois canais alvo usa. Adicionar sem caso de uso e complexidade morta. |
| Webhook do Discord como fonte | Webhook do Discord so ENVIA, nao LE. Nao serve para esta direcao. Por isso a ponte precisa mesmo de um bot com a intent Message Content. |
| Qualquer alteracao em `l2scanner/__main__.py` | O workstream `mercado` edita esse arquivo de 2047 linhas em paralelo. Entrypoint proprio evita o unico conflito de merge real — e e a arquitetura certa de qualquer forma: a ponte e async e orientada a evento, o scanner e um laco sincrono de 1 Hz. |
| Rodar os 4 agentes de pesquisa | `.planning/research/` e compartilhado e sobrescreveria a pesquisa do workstream `mercado`. Ver "Contexto herdado" acima. |
| Qualquer biblioteca de sintese de input | Invariante fundador do projeto. `tests/test_firewall_escopo.py` e o portao executavel — e uma banlist, entao a dependencia do Discord passa limpo. |

## Traceability

Preenchida na criacao do roadmap.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PONTE-01 | — | Pending |
| PONTE-02 | — | Pending |
| PONTE-03 | — | Pending |
| PONTE-04 | — | Pending |
| PONTE-05 | — | Pending |
| FORM-01 | — | Pending |
| FORM-02 | — | Pending |
| FORM-03 | — | Pending |
| FORM-04 | — | Pending |
| FORM-05 | — | Pending |
| ENTR-01 | — | Pending |
| ENTR-02 | — | Pending |
| ENTR-03 | — | Pending |
| ENTR-04 | — | Pending |
| CONF-01 | — | Pending |
| CONF-02 | — | Pending |
| CONF-03 | — | Pending |
| CONF-04 | — | Pending |
| OPER-01 | — | Pending |
| OPER-02 | — | Pending |
| OPER-03 | — | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 0
- Unmapped: 21 (roadmap pendente)

## Portao humano — o que so voce pode fazer

A ponte nao sobe sem isto, e nenhum agente consegue fazer no seu lugar:

1. Criar uma aplicacao em `discord.com/developers/applications`, adicionar um
   Bot e copiar o token.
2. Ligar a intent **MESSAGE CONTENT** no painel do bot. Sem ela o `on_message`
   chega com o texto VAZIO — a ponte conecta, parece saudavel, e replica mensagem
   em branco para sempre. E o modo de falha mais caro deste projeto.
3. Convidar o bot para o servidor XM Games com permissao de ler os dois canais
   (`View Channel` + `Read Message History`).
4. Dizer qual `conversation_id` do Chatwoot recebe os anuncios.

---
*Requirements defined: 2026-08-28*
