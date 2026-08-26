# Phase 10: Lista de presenca do Solo Boss pelo WhatsApp - Context

**Gathered:** 2026-08-26
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — 3 areas, 12 decisoes, todas aceitas como propostas

<domain>
## Phase Boundary

A party passa a saber com antecedencia quem vai no proximo Solo Boss, sem ninguem
perguntar de boca. O scanner CHAMA no grupo 1h50 antes de cada ocorrencia, cada
membro responde `.join` no privado do bot, e cada confirmacao aparece no grupo com
o NICK do jogador. `.leave` desfaz. No horario do boss a lista fecha e alimenta o
revezamento de loot que ja existe.

DENTRO DA FASE: um terceiro tipo de aviso na agenda; um segundo nivel de
autorizacao de comando; os comandos `.join` e `.leave`; a lista de presenca em
disco; o fechamento no horario; a leitura dessa lista pelo `loot.py`.

FORA DA FASE: qualquer mudanca na deteccao de tela, no rastreador, na captura ou
no silenciamento. Nenhum evento alem do Solo Boss ganha chamada nesta fase (o
mecanismo e generico, a configuracao e que liga).

</domain>

<decisions>
## Implementation Decisions

### Area 1: A chamada (o aviso de 1h50)

- **Um terceiro `TipoDeAviso`, nao uma lista de antecedencias.** Nasce
  `TipoDeAviso.CHAMADA` ao lado de `ANTES` e `AGORA`, alimentado por um campo novo
  `chamar_minutos_antes` no `[[evento]]`. A razao e a `Aviso.chave`, que ja carrega
  `self.tipo.value`: o marcador duravel do aviso novo sai de graca, distinto do
  marcador do aviso de 10 minutos, e nenhum marcador ja gravado em `.agenda/` e
  invalidado. Transformar `avisar_minutos_antes` numa lista faria o contrario —
  reescreveria `avisos_devidos` e mudaria o significado de chaves ja em disco.
- **Opt-in por evento.** So ganha chamada o `[[evento]]` que declarar
  `chamar_minutos_antes`. Hoje isso e so o Solo Boss (`110`). TvT e Prime nao
  mudam de comportamento em nada.
- **Mecanismo generico, configuracao especifica.** A agenda nunca escreve
  "Solo Boss" no codigo — mesma linha que `avisar_no_horario` ja segue. Quem
  decide que evento tem chamada e o `config.toml`.
- **O aviso de 10 minutos continua intocado.** Ele serve a outra acao (parar o
  farm e se deslocar); a chamada serve a uma terceira (decidir se vai). Um nao
  substitui o outro, e juntar os dois textos treinaria a party a ignorar ambos.

### Area 2: O `.join` e quem pode dar

- **Autorizacao em DOIS NIVEIS — o coracao da fase.** Hoje `autor_autorizado` e
  global: um telefone na allowlist pode TUDO, inclusive `.corrigir` e `.pegou`,
  que reescrevem estatistica permanente. Por os telefones de 4-8 party-mates la
  daria a todos eles esse poder. Entao: `[[membro]]` no `config.toml` (nick +
  telefone) autoriza **exclusivamente** `.join` e `.leave`;
  `CHATWOOT_TELEFONES_COMANDO` continua sendo o nivel que alcanca todo o resto.
  Ninguem ganha comando destrutivo de carona numa feature de presenca.
- **A descoberta da conversa NAO muda.** `LeitorDeComandos(etiqueta=...)` e
  `_por_etiqueta()` ja existem e ja redescobrem conversas marcadas a cada leitura,
  ligados por `CHATWOOT_ETIQUETA_COMANDO`. A etiqueta `CP` do usuario ja funciona.
  Nada de polling novo.
- **`.join` fora da janela e aceito.** Vale para a proxima ocorrencia e a resposta
  diz QUAL horario pegou. Quem lembrou tres horas antes nao pode ser punido por
  lembrar cedo — e a resposta que diz o horario e o que impede o mal-entendido.
- **`.join` repetido nao repete no grupo.** Responde no privado "voce ja esta na
  lista" e para ai. O grupo e o recurso caro desta fase: 12 ocorrencias por dia
  ja foram a razao de o usuario desligar `avisar_no_horario` no Solo Boss.
- **A confirmacao sai nos DOIS lugares.** No grupo (`CHATWOOT_CONVERSAS`), que e o
  ponto da feature, e uma linha curta no privado de quem mandou, para ele saber
  que chegou. Sem o eco privado, um `.join` que falhou por autorizacao e um que
  funcionou sao indistinguiveis para quem digitou.
- **O nick vem do mapa, nunca do WhatsApp.** O nome do contato do Chatwoot nao e o
  nick do jogo. Mesma disciplina dos ALRT-* da Fase 3: nome sempre da lista
  configurada, nunca lido de fora.

### Area 3: A lista, o fechamento e o loot

- **A lista mora no `.agenda/`, com prefixo proprio.**
  `presenca_<chave-da-ocorrencia>_<apelido>`, arquivo vazio criado com
  `O_CREAT|O_EXCL` como todo o resto da pasta — a atomicidade entre as duas
  instancias do usuario vem junto de graca. A poda de 3 dias e CORRETA aqui, ao
  contrario do `.loot/`: a lista morre quando o boss passa. A estatistica de loot
  continua no `.loot/`, que nunca e podado.
- **Fecha no horario do boss, e so fala se alguem joinou.** Zero joins produz zero
  mensagem. Isso preserva exatamente a decisao que o usuario ja tinha tomado ao
  por `avisar_no_horario = false` no Solo Boss: um boss que ninguem confirmou nao
  merece uma mensagem no grupo. E o fechamento NAO depende de ligar
  `avisar_no_horario`.
- **A lista SUGERE ao loot, nao manda nele.** A vez do proximo boss so e sugerida
  entre quem esta na lista fechada; mas `.loot-<nick>` de alguem que nao joinou
  AVISA e OBEDECE. A autoridade e o usuario, nao o registro — e um bloqueio aqui
  transformaria uma feature de conveniencia em obstaculo no pior momento (alguem
  chegou sem avisar e a party precisa designar).
- **`.leave` depois do fechamento e recusado**, dizendo que o boss ja comecou. Uma
  lista fechada e historico; reabrir historico e a categoria de bug que o
  `.corrigir` do `loot.py` ja documenta como cara.

### Claude's Discretion

- Redacao exata das mensagens (chamada, confirmacao, lista final, recusas).
- Nome do campo do config para o mapa de membros (`[[membro]]` e a proposta).
- Se `.join` e `.leave` entram no `_VOCABULARIO` fixo ou no `interpretar_dinamico`.
- Formato da lista final (uma linha com nicks separados por virgula vs. lista).
- Como o `.help` (derivado do enum, com tripwire) apresenta os comandos novos.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`agenda.TipoDeAviso` / `Aviso.chave`** — a chave duravel ja inclui
  `tipo.value`. Um tipo novo ganha marcador distinto sem tocar em nada.
- **`agenda.RegistroEmDisco`** — `marcar()` com `O_CREAT|O_EXCL` resolve restart E
  corrida entre as duas instancias de uma vez. A lista de presenca reusa isso.
- **`agenda.chave_da_ocorrencia(nome, alvo)`** — ja existe e ja e o idioma de
  identidade de ocorrencia usado pelo `.loot/`.
- **`comandos.LeitorDeComandos(etiqueta=...)` + `_por_etiqueta()`** — descoberta de
  conversa por label do Chatwoot, redescoberta a cada leitura. JA IMPLEMENTADO.
- **`comandos.autor_autorizado` / `telefone_equivalente`** — comparacao pelos 8
  digitos finais, que e o unico jeito que funciona com o nono digito brasileiro.
  O nivel novo reusa `telefone_equivalente`, nao reimplementa.
- **`loot.apelido()` / `NICK_VALIDO`** — slug e validacao de nick, ja compartilhados
  entre `loot` e `comandos`.
- **`loot.proxima_ocorrencia` / `eh_solo_boss` / `horarios_do_solo_boss`** — o
  vocabulario de "qual e o proximo Solo Boss" ja existe inteiro.

### Established Patterns

- **O tempo entra por parametro em tudo.** Nenhum `datetime.now()` dentro de
  `agenda.py` ou `loot.py`. E o que permite testar a corrida das duas instancias e
  o fechamento atrasado em milissegundos.
- **Funcoes puras primeiro, IO na borda.** `avisos_devidos`, `comandos_novos`,
  `interpretar_dinamico` sao puras e recebem dados ja decodificados.
- **Nome sempre da configuracao, nunca lido da tela ou do WhatsApp.**
- **Docstrings que explicam POR QUE, com medidas de campo** (o nono digito, as 22
  conversas de clientes reais, a ponte Baileys sem ingestao de grupo).
- **`loot.py` NUNCA importa `comandos` nem `sessao`** — a direcao da dependencia e
  fixa e um ciclo mataria os dois. O codigo novo tem que respeitar isso.

### Integration Points

- `l2scanner/agenda.py` — `TipoDeAviso`, `EventoAgendado`, `avisos_devidos`,
  `texto_do_aviso`.
- `l2scanner/comandos.py` — `Comando` (enum + tabela `_AJUDA`, com tripwire),
  `interpretar`/`interpretar_dinamico`, `comandos_novos`, `autor_autorizado`.
- `l2scanner/loot.py` — leitura da lista fechada para sugerir a vez.
- `l2scanner/config.py` — `[[membro]]` e `chamar_minutos_antes`.
- `l2scanner/sessao.py` — onde os avisos devidos viram envio e onde o comando vira
  resposta; e onde o fechamento no horario precisa ser disparado.
- `config.toml` — `chamar_minutos_antes = 110` no `[[evento]]` do Solo Boss.

</code_context>

<specifics>
## Specific Ideas

- O pedido original: "1h50m antes do proximo Solo Boss o Bot deve perguntar no
  grupo quem vai participar do proximo <horario>, os jogadores digitam `.join`,
  respondem no privado do bot, e o bot confirma no grupo que <nick> joinou".
- 1h50 antes NAO e um numero solto: com o boss de duas em duas horas, e dez
  minutos DEPOIS do boss anterior — o instante em que a party ainda esta reunida e
  ainda esta olhando o WhatsApp. E o unico momento do ciclo em que a pergunta pega
  todo mundo junto.
- O privado nao foi escolha de desenho: e imposicao. A ponte Baileys desta conta
  vem com ingestao de grupo desligada (medido 2026-08-24: os 11 grupos nao
  entregam entrada, so as conversas 1-a-1). Comando SO chega no privado.

</specifics>

<deferred>
## Deferred Ideas

- Chamada para TvT e Prime. O mecanismo fica generico nesta fase, mas ligar em
  outros eventos e decisao de outro dia — e outro volume de mensagem.
- `.join` de convidado que nao esta no `[[membro]]`. Hoje ele e simplesmente
  ignorado; um fluxo de convite e uma fase propria.
- Estatistica de presenca ("quantos Solo Boss o J4guar foi"). A lista e podada em
  3 dias de proposito; virar estatistica exigiria pasta sem poda, como o `.loot/`.
- Lembrar no privado de quem NAO respondeu. Cutuca individual e uma superficie
  nova de mensagem e merece decisao separada.

</deferred>
