# Roadmap: L2 Party Scanner

## Overview

O caminho até "a galera fica sabendo no WhatsApp em segundos" tem uma ordem que não é gosto pessoal — é correção. Primeiro descobrimos se o WhatsApp **consegue** entregar (uma pergunta de um dia que pode invalidar metade do produto) e passamos a **gravar** sessões de farm, porque o evento que o scanner existe para pegar — alguém morrer — é raro e não se reproduz sob demanda; sem verdade gravada, todo ajuste de limiar é chute. Com sessões na mão, o usuário **calibra** regiões e cores com o mouse (sob `Gamma=1.16` os valores HSV certos são desconhecíveis a priori) e o scanner passa a **ler** as barras. Aí nasce o **rastreador**: debounce, histerese, cooldown e o portão de cegueira — tudo isso já é útil imprimindo só no console, sem uma linha de rede para confundir a depuração, e com o replay fechando o ciclo de regressão. Só no fim os eventos ganham transporte e o scanner ganha um vigia para si mesmo, porque o pior modo de falha deste produto não é errar: é morrer calado enquanto a party acha que está coberta.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Gate de entrega e fundação de captura** - Descobrir se o WhatsApp entrega de verdade e começar a gravar sessões de farm hoje
- [x] **Phase 2: Calibração e leitura das barras** - Marcar regiões e cores com o mouse até o scanner ler o HP de cada membro
- [x] **Phase 3: Rastreador, console ao vivo e replay** - Decidir quem morreu, saiu ou ressuscitou — útil já no console, sem rede
- [x] **Phase 4: Entrega no WhatsApp e vigilância do vigia** - Os eventos chegam no celular da party, e o silêncio do scanner passa a significar algo
- [x] **Phase 5: Reconhecer tela de login e desconexão do servidor** - Cegueira com causa conhecida deixa de ser cegueira e vira um aviso com nome

**Milestone v2 — Agenda e Silenciamento** (definido 2026-08-24)

- [x] **Phase 6: A agenda como fonte de eventos** - Lembrete de TvT e Prime nos horários certos, com o jogo fechado
- [x] **Phase 7: Silenciamento por janela de evento** - Durante o evento o scanner cala, porque toda morte é verdadeira e nenhuma é notícia
- [x] **Phase 8: Cancelar o silenciamento pelo WhatsApp** - O silêncio deixa de ser irrevogável: o grupo desliga por comando
- [x] **Phase 9: Tornar o laço principal testável** - O laço principal passa a caber num teste, sem jogo e sem rede

**Milestone v3 — Lista de presença do Solo Boss** (definido 2026-08-26)

- [ ] **Phase 10: Lista de presença do Solo Boss pelo WhatsApp** - O scanner pergunta quem vai, cada um responde `.join` no privado, e a lista se fecha no horário

## Phase Details

### Phase 1: Gate de entrega e fundação de captura

**Goal**: O usuário sabe se o WhatsApp realmente entrega uma mensagem iniciada pelo scanner, e já consegue gravar sessões de farm enquanto o resto é construído
**Depends on**: Nothing (first phase)
**Requirements**: DELV-01, DELV-02, DELV-03, CAPT-01, CAPT-02, CAPT-03, CAPT-04, CAPT-05, CAPT-06, CAPT-07, OPER-01, OPER-08, SAFE-01, SAFE-02, SAFE-03, SAFE-04
**Success Criteria** (what must be TRUE):

  1. O usuário sabe, documentado no log de decisões, qual provedor de WhatsApp está por trás do inbox do Chatwoot e se uma mensagem iniciada pelo scanner chega fora da janela de 24h — confirmada à mão num celular que estava em silêncio há mais de um dia, incluindo o plano B caso a API oficial exija template
  2. O usuário inicia o scanner com um clique, sem ritual de ambiente virtual, e vê a região da party window sendo capturada corretamente com o jogo em janela no segundo monitor — nenhuma coordenada de tela escrita no código
  3. O usuário farma com `--record` ligado e, ao terminar, tem uma pasta com frames e observações da sessão para calibrar e testar depois, sem o jogo aberto
  4. O scanner sobrevive a alt-tab, frame preto e erro em qualquer etapa: ele diz no console que perdeu a visão em vez de concluir que a party inteira morreu, não confunde tela parada com perda de visão, e se recusa a iniciar se a geometria da tela mudou desde a calibração
  5. O token do Chatwoot fica fora do código e fora do controle de versão, nenhuma biblioteca de automação de input entra na lista de dependências (a violação vira estruturalmente impossível), e o README declara honestamente que o scanner é somente leitura — nunca envia input, não lê memória, não injeta e não intercepta tráfego — sem prometer "risco zero"

**Plans**: TBD

**Ordem interna (bloqueante)**: DELV-01/02/03 são o **primeiro** plano da fase e um portão duro — nenhum código de detecção começa antes deles. O gate não precisa de código do projeto (inspeção da API do Chatwoot + um envio de teste), e é resolvível em menos de um dia; descobrir tarde custa uma semana e pode forçar a redesenhar toda a metade de saída. A gravação (CAPT-03) vem logo em seguida porque desbloqueia o usuário: ele já pode farmar com `--record` e bancar uma morte real enquanto as fases seguintes são construídas.

### Phase 2: Calibração e leitura das barras

**Goal**: O usuário calibra regiões e cores arrastando o mouse sobre uma sessão gravada, e o scanner passa a informar o HP de cada membro número a número
**Depends on**: Phase 1
**Requirements**: CALI-01, CALI-02, CALI-03, CALI-04, CALI-05, DTCT-01, DTCT-02, DTCT-03, DTCT-04, DTCT-05, DTCT-06, DTCT-07
**Success Criteria** (what must be TRUE):

  1. O usuário marca as regiões a vigiar (party window, cada linha de membro, âncora da janela, HP do próprio personagem) arrastando o mouse sobre um frame gravado, sem digitar coordenada nenhuma — e a calibração é gravada em arquivo próprio, sem sobrescrever as configurações escritas à mão
  2. O usuário ajusta os limiares de cor com controles visuais, vendo o efeito ao vivo sobre a imagem, até a barra vermelha ler certo em qualquer nível de HP — sem leituras espúrias de 0%
  3. O usuário abre uma imagem com todas as regiões desenhadas por cima e confere visualmente que estão no lugar antes de confiar em qualquer número
  4. O scanner informa o preenchimento de HP de cada membro e do próprio personagem, distinguindo três coisas que se parecem na tela: "HP em 0%", "a linha do membro sumiu" e "a party window não está visível" — esta última por uma âncora independente das barras, para que um wipe total nunca seja lido como alt-tab
  5. O scanner se recusa a iniciar quando todos os membros leem 0% — sinal de calibração errada — em vez de sair medindo tudo errado

**Plans**: TBD

**Ordem interna**: calibração **antes** da extração. Sob o `Gamma=1.16` do cliente, os limiares HSV corretos são desconhecíveis a priori — só saem de um frame capturado. A extração é pura: `(Frame, Calibration) -> Observation`, sem relógio, sem rede, sem arquivo.

### Phase 3: Rastreador, console ao vivo e replay

**Goal**: O scanner decide sozinho quem morreu, quem saiu e quem ressuscitou, mostra tudo ao vivo no console — já é útil sem uma linha de rede — e cada erro de julgamento vira teste permanente
**Depends on**: Phase 2
**Requirements**: ALRT-01, ALRT-02, ALRT-03, ALRT-04, ALRT-05, ALRT-06, ALRT-07, ALRT-08, ALRT-09, ALRT-10, OPER-02, OPER-07, TEST-01, TEST-02, TEST-03, TEST-04
**Success Criteria** (what must be TRUE):

  1. O usuário deixa o console num canto da tela e vê ao vivo o estado de cada membro antes de sair AFK; ao encerrar, recebe um resumo da sessão, e todos os eventos ficam gravados em log estruturado
  2. Uma morte só é confirmada após N leituras seguidas de HP zerado (com N configurável), uma saída só após alguns segundos de linha ausente, e sair do estado morto exige mais confirmações do que entrar — nada de estado piscando
  3. Cada evento gera exatamente um alerta, sempre com o nome do membro vindo da lista configurada pelo usuário (nunca "alguém", nunca leitura de texto da tela): um morto por cinco minutos não vira cinco minutos de mensagens, e fechar o jogo de propósito não anuncia que a party inteira saiu
  4. Um alt-tab durante uma morte não faz o evento sumir — a verificação de visibilidade acontece antes das verificações por membro, nada é enviado enquanto a party window não aparece, e ao voltar a enxergar o scanner ainda avisa do que começou antes, respeitando um período de tolerância para não inventar mortes com a UI meio desenhada
  5. O usuário roda uma sessão gravada de ponta a ponta, sem o jogo aberto e sem rede, e o scanner reproduz exatamente os eventos esperados — inclusive nos casos difíceis (alt-tab durante morte, wipe total, morto por muito tempo, party window sumindo); qualquer falso positivo encontrado no farm vira caso de teste fixo

**Plans**: TBD

**Seam obrigatório**: o limite detecção→transporte (fila + porta `Notifier`) nasce **aqui**, não é retrofit. Se `send_alert()` chegar a ser chamado inline pela detecção, agregação de wipe, dedup e limite de taxa ficam impossíveis de acrescentar depois. Nesta fase o único "notifier" é o console. O replay (TEST-02) fecha o ciclo de regressão **antes** de qualquer código de rede existir.

### Phase 4: Entrega no WhatsApp e vigilância do vigia

**Goal**: Os eventos saem do console e chegam no WhatsApp da party em segundos — e o silêncio do scanner passa a significar "está tudo bem" em vez de "o scanner morreu e ninguém viu"
**Depends on**: Phase 3
**Requirements**: DELV-04, DELV-05, DELV-06, DELV-07, DELV-08, DELV-09, ALRT-11, OPER-03, OPER-04, OPER-05, OPER-06
**Success Criteria** (what must be TRUE):

  1. Quando um membro morre, sai da PT ou ressuscita, a mensagem chega no WhatsApp da party em segundos, em português, com o nome do membro, o que aconteceu e o horário local — fraseada de um jeito que sobreviva a um falso positivo ("HP zerado há 6s — possível morte"), nunca "MORREU"
  2. O usuário dispara `--test-alert` sem o jogo aberto e confirma no celular que a entrega funciona, ou roda em `--dry-run` e vê os alertas só no console, sem enviar nada
  3. Nenhum evento se perde numa queda de rede: cada alerta é gravado em arquivo durável **antes** da tentativa de envio, falha transitória é reenviada com backoff, erro definitivo (4xx) não é reenviado, e qualquer falha de entrega aparece de forma visível no console — nunca em silêncio
  4. A party recebe um aviso quando o scanner começa e quando termina de monitorar; se o scanner ficar cego por vários minutos, isso também vira um aviso, e ao recuperar a visão ele informa por quanto tempo esteve cego
  5. O usuário olha para um indicador fora da área do jogo e sabe num relance que o scanner está vivo, e a tela não entra em suspensão no meio da sessão

**Plans**: TBD

**Replanejar após a Fase 1**: a forma desta fase foi decidida no gate de entrega. Se o caminho confirmado for a API oficial da Meta, entra um sub-plano de criação e aprovação de template (latência externa fora do nosso controle) e o envio para grupo cai em favor de N envios 1:1.

### Phase 5: Reconhecer tela de login e desconexão do servidor

**Goal**: Quando o cliente cai — servidor em manutenção, queda de conexão, volta para a tela de login — a party é avisada do motivo, em vez de receber silêncio ou, pior, um alarme falso de "fulano saiu da party"
**Depends on**: Phase 4
**Requirements**: OPER-02 (estendido), ALRT-11 (estendido)
**Success Criteria** (what must be TRUE):

  1. O scanner distingue três coisas que antes eram todas "sem visão da party": o jogo coberto por outra janela, o cliente na tela de login, e o diálogo de desconexão aberto na tela
  2. A party recebe UMA mensagem dizendo que o jogo caiu, com o motivo, e UMA quando ele volta — nunca uma por leitura
  3. Com o jogo caído, nenhum evento de party é emitido: a party window não está escondida, ela não existe, e concluir "saiu da party" a partir de uma tela de login é o alarme falso que o dia inteiro foi gasto corrigindo
  4. Ligar o scanner com o jogo já na tela de login não anuncia queda nenhuma — o usuário está olhando para a tela
  5. O console mostra o motivo no lugar de "SEM VISAO", porque "SEM VISAO" é verdade e não ajuda

**Plans**: executado direto (fase pequena, sem plano formal)

**Os dois sinais têm forças diferentes, e isso é de projeto:**

O **título da janela** decide "tela de login". Jogando, o cliente se chama `Yazalaque - XM Essence`; na tela de login vira `XM Essence`, sem o prefixo do personagem. É texto do Windows: sem limiar, sem HSV, sem calibração, e não quebra se o usuário mudar a resolução. Verificado ao vivo com as duas instâncias do usuário abertas ao mesmo tempo.

Um **template** decide "desconectado", e esse precisa de pixels porque com o diálogo aberto o cliente continua se chamando `Faerlina - XM Essence` — pela janela, ele ainda está no jogo. É o caso MAIS importante dos dois: se o usuário está AFK quando cai, o diálogo fica parado na tela para sempre e o título nunca muda. Sem o template, AFK + desconectado é silêncio permanente.

**Armadilha medida, não suposta**: `windows-capture` casa `window_name` por SUBSTRING. Pedir `XM Essence` devolve o frame de `Faerlina - XM Essence` — outra janela, outro personagem. Por isso a tela de login nunca é detectada capturando "a janela de login": ela é detectada relendo o título do hwnd que já temos.

**Margem medida ao vivo**: diálogo real 0.9997, tela de login 0.5051, contra limiar 0.90.

### Phase 6: A agenda como fonte de eventos

**Goal**: O grupo recebe lembrete de TvT e Prime nos horários certos, com o jogo fechado, sem ninguém precisar lembrar
**Depends on**: Phase 4 (o caminho de entrega)
**Requirements**: AGEN-01 a AGEN-08, OPER-09, OPER-10, OPER-11
**Success Criteria** (what must be TRUE):

  1. O grupo recebe um aviso 10 minutos antes e outro no horário exato, para TvT (15:00, 17:00, 21:50, todo dia) e Prime (20:00, segunda a quinta)
  2. O usuário muda um horário editando `config.toml` com um comentário do lado, sem tocar em Python — uma atualização do jogo não pode custar um commit de código
  3. O scanner roda a agenda com o jogo FECHADO, numa máquina que não está farmando
  4. Reiniciar o scanner às 14:59 não reenvia o aviso das 14:50 que já saiu, e subir o scanner às 16h não dispara o aviso das 15h atrasado
  5. Com as duas instâncias do usuário rodando lado a lado, o grupo recebe cada aviso uma vez só

**Plans**: [PLAN.md](phases/06-a-agenda-como-fonte-de-eventos/PLAN.md) · [SUMMARY.md](phases/06-a-agenda-como-fonte-de-eventos/SUMMARY.md) — 4 tarefas, concluída

**O relógio é uma fonte de eventos, igual à tela.** A agenda entra pelo `Despachante` que já existe, exatamente como o rastreador entra — nunca chamando `enviar()` direto. Essa é a regra 6 do roadmap v1 ("o seam detecção→transporte nasce com o rastreador, nunca é retrofit"), e ela vale para a segunda fonte tanto quanto valeu para a primeira. Se a agenda furar o seam, o silenciamento da Fase 7 fica impossível de acrescentar depois.

**O estado de "já avisei" é durável e compartilhado.** Duas exigências que parecem separadas — sobreviver ao restart (AGEN-06) e não duplicar entre instâncias (AGEN-07) — são o mesmo problema com o mesmo remédio: um registro em disco de qual evento de qual dia já foi anunciado, que as duas instâncias consultam. Resolver uma sem a outra deixa metade do bug em pé.

**Limite honesto, dito no README**: "independente do jogo" não é "independente do PC". Com a máquina desligada às 15h não há aviso. Um agendamento no servidor resolveria e é outro projeto.

### Phase 7: Silenciamento por janela de evento

**Goal**: Durante TvT e Prime o scanner cala, porque em evento morre todo mundo o tempo todo e cada morte vira uma mensagem que ninguém quer ler
**Depends on**: Phase 6 (as janelas de silêncio SÃO a agenda)
**Requirements**: MUTE-01 a MUTE-08
**Success Criteria** (what must be TRUE):

  1. Durante uma janela de silêncio nenhum evento do scanner chega ao WhatsApp — nem morte, nem saída, nem "o jogo caiu"
  2. TvT silencia por 15 minutos e Prime por 2 horas, contados do horário do evento
  3. De segunda a quinta o silêncio termina às 22:05 e não às 22:00: a janela do TvT das 21:50 se estende além da do Prime, e janelas sobrepostas se comportam como união
  4. O lembrete do TvT das 21:50 chega mesmo caindo dentro do silêncio do Prime — a agenda atravessa o silêncio sempre
  5. Ao fim de cada janela o grupo recebe uma mensagem dizendo que o evento encerrou e que os convites de party estão sendo reenviados
  6. Tudo que foi silenciado continua no log e no console, e o console mostra que está calado de propósito e até quando

**Não é correção de bug — é filtro de relevância.** Os alertas durante um TvT são verdadeiros: as pessoas morreram mesmo. Eles só não são notícia. Essa distinção importa para o desenho: o silenciamento vive no TRANSPORTE, depois do rastreador ter decidido e registrado tudo normalmente. Silenciar na detecção corromperia o estado (um membro que morre e ressuscita durante o silêncio precisa sair do outro lado com o estado certo), e destruiria o log — que é a única ferramenta de depuração pós-farm que o projeto tem.

**Silêncio é do WhatsApp, nunca do registro.** MUTE-07 não é conforto: sem ele, um falso positivo que aconteça durante um TvT fica invisível para sempre.

**A ordem 6 → 7 é obrigatória**: a janela de silêncio é derivada da mesma entrada de agenda que gera o lembrete. Construir o silenciamento antes da agenda significaria escrever a definição de horários duas vezes, e elas divergiriam.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Status | Completed |
|-------|--------|-----------|
| 1. Gate de entrega e fundação de captura | Implementado (falta confirmar envio no celular) | 2026-08-24 |
| 2. Calibração e leitura das barras | Implementado e verificado na tela real | 2026-08-24 |
| 3. Rastreador, console ao vivo e replay | Implementado, 29 testes | 2026-08-24 |
| 4. Entrega no WhatsApp e vigilância do vigia | Implementado e verificado ao vivo | 2026-08-24 |
| 5. Reconhecer tela de login e desconexão | Implementado e verificado ao vivo contra as duas janelas | 2026-08-24 |
| 6. A agenda como fonte de eventos | Implementada, 55 testes novos | 2026-08-24 |
| 7. Silenciamento por janela de evento | Implementada, 25 testes novos | 2026-08-24 |

**255 testes passando.** A entrega no celular está confirmada e uma morte real já
foi detectada em campo (13:39-13:42). Falta as duas coisas na MESMA sessão.

## Coverage

Todos os 55 requisitos v1 estão mapeados para exatamente uma fase. Nenhum órfão, nenhuma duplicata.

| Categoria | Total | Fase 1 | Fase 2 | Fase 3 | Fase 4 |
|-----------|-------|--------|--------|--------|--------|
| DELV (Entrega) | 9 | 3 | - | - | 6 |
| CAPT (Captura) | 7 | 7 | - | - | - |
| CALI (Calibração) | 5 | - | 5 | - | - |
| DTCT (Detecção) | 7 | - | 7 | - | - |
| ALRT (Alerta) | 11 | - | - | 10 | 1 |
| OPER (Operação) | 8 | 2 | - | 2 | 4 |
| TEST (Testabilidade) | 4 | - | - | 4 | - |
| SAFE (Segurança) | 4 | 4 | - | - | - |
| **Total** | **55** | **16** | **12** | **16** | **11** |

## Restrições de ordenação (propriedades de correção, não preferências)

Estas seis regras vieram da pesquisa e não são negociáveis num replanejamento:

1. **O gate de entrega vem antes de tudo** — pode invalidar metade do produto, custa menos de um dia e não exige código do projeto.
2. **Gravação antes de lógica de detecção** — o evento alvo é raro e irreproduzível sob demanda; sem verdade gravada, todo ajuste de limiar é chute.
3. **Calibração antes de extração** — sob `Gamma=1.16` os limiares HSV são desconhecíveis a priori.
4. **Rastreador antes do notificador** — o produto já vale com saída em console, e depurar detecção e rede ao mesmo tempo multiplica as variáveis.
5. **Replay antes da rede** — a partir daí toda mudança é verificada contra regressão.
6. **O seam detecção→transporte nasce com o rastreador** — nunca retrofit.

### Phase 8: Cancelar o silenciamento pelo WhatsApp

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 7
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 8 to break down)

### Phase 9: Tornar o laco principal testavel

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 8
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 9 to break down)

### Phase 10: Lista de presenca do Solo Boss pelo WhatsApp

**Goal**: A party sabe com uma hora e cinquenta de antecedencia quem vai no proximo Solo Boss, sem ninguem perguntar de boca — o scanner pergunta no grupo, cada um responde `.join` no privado, e a lista se fecha sozinha no horario
**Requirements**: TBD (derivar em /gsd-plan-phase)
**Depends on**: Phase 9
**Success Criteria** (what must be TRUE):

  1. A 1h50 do proximo Solo Boss — dez minutos depois do anterior, quando a party ainda esta reunida — chega no grupo uma pergunta com o horario do proximo boss; o aviso de 10 minutos antes continua existindo, porque ele serve a outra coisa (parar o farm e se deslocar)
  2. Um membro manda `.join` no privado do bot e o grupo recebe a confirmacao com o NICK dele — nao com o nome do contato do WhatsApp — e um `.join` repetido nao vira uma segunda mensagem no grupo
  3. Quem desistiu manda `.leave` e sai da lista; o grupo fica sabendo, e um `.leave` de quem nunca deu `.join` responde isso em vez de anunciar coisa nenhuma
  4. Um membro da party consegue dar `.join` do privado dele sem ganhar junto o poder de `.cancelar`, `.loot-<nick>` ou `.corrigir`: a autorizacao passa a ter DOIS niveis, e o de membro alcanca so os comandos da lista de presenca. A descoberta da conversa segue pela etiqueta `CP` que o `LeitorDeComandos` ja implementa
  5. No horario do boss a lista se fecha e o grupo recebe quem confirmou; a lista fechada alimenta o revezamento de loot existente, de modo que a vez do proximo boss so seja sugerida entre quem estava presente
  6. Tudo isso e demonstravel sem o jogo aberto e sem rede: o tempo entra por parametro, a etiqueta e o mapa telefone->nick entram por dado, e a corrida entre as duas instancias do usuario tem teste proprio — a mesma disciplina que `agenda.py` e `loot.py` ja seguem

**Plans**: TBD

**CORRECAO (2026-08-26)**: a descoberta de conversa por etiqueta JA EXISTE — `LeitorDeComandos(etiqueta=...)` e `_por_etiqueta()` em `comandos.py`, ligados por `CHATWOOT_ETIQUETA_COMANDO` no `.env`, redescobrindo a cada leitura. Nao ha polling novo a construir. O que falta e outra coisa: a trava de QUEM (`autor_autorizado`) e global hoje, entao por o telefone de um membro nela daria a ele todos os comandos, inclusive os destrutivos.

**Ordem interna**: o nivel de autorizacao vem PRIMEIRO e sozinho — e a unica parte da fase que mexe numa trava de seguranca, e misturar isso com a feature esconderia o risco no meio do recurso. Depois nasce a chamada (o aviso de 1h50) e a lista de presenca. A integracao com `loot.py` e a ULTIMA, porque e a unica que toca estatistica que nunca e podada.

---
*Roadmap created: 2026-08-24*
