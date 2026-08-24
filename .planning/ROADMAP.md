# Roadmap: L2 Party Scanner

## Overview

O caminho até "a galera fica sabendo no WhatsApp em segundos" tem uma ordem que não é gosto pessoal — é correção. Primeiro descobrimos se o WhatsApp **consegue** entregar (uma pergunta de um dia que pode invalidar metade do produto) e passamos a **gravar** sessões de farm, porque o evento que o scanner existe para pegar — alguém morrer — é raro e não se reproduz sob demanda; sem verdade gravada, todo ajuste de limiar é chute. Com sessões na mão, o usuário **calibra** regiões e cores com o mouse (sob `Gamma=1.16` os valores HSV certos são desconhecíveis a priori) e o scanner passa a **ler** as barras. Aí nasce o **rastreador**: debounce, histerese, cooldown e o portão de cegueira — tudo isso já é útil imprimindo só no console, sem uma linha de rede para confundir a depuração, e com o replay fechando o ciclo de regressão. Só no fim os eventos ganham transporte e o scanner ganha um vigia para si mesmo, porque o pior modo de falha deste produto não é errar: é morrer calado enquanto a party acha que está coberta.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Gate de entrega e fundação de captura** - Descobrir se o WhatsApp entrega de verdade e começar a gravar sessões de farm hoje
- [ ] **Phase 2: Calibração e leitura das barras** - Marcar regiões e cores com o mouse até o scanner ler o HP de cada membro
- [ ] **Phase 3: Rastreador, console ao vivo e replay** - Decidir quem morreu, saiu ou ressuscitou — útil já no console, sem rede
- [ ] **Phase 4: Entrega no WhatsApp e vigilância do vigia** - Os eventos chegam no celular da party, e o silêncio do scanner passa a significar algo

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

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Gate de entrega e fundação de captura | 0/TBD | Not started | - |
| 2. Calibração e leitura das barras | 0/TBD | Not started | - |
| 3. Rastreador, console ao vivo e replay | 0/TBD | Not started | - |
| 4. Entrega no WhatsApp e vigilância do vigia | 0/TBD | Not started | - |

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

---
*Roadmap created: 2026-08-24*
