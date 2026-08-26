# Requirements: L2 Party Scanner

**Defined:** 2026-08-24
**Core Value:** Quando alguém da party morre ou sai da PT, a galera fica sabendo no WhatsApp em segundos — mesmo quem está AFK.

## v1 Requirements

### Entrega (Delivery)

- [ ] **DELV-01**: O projeto identifica qual provedor de WhatsApp está por trás do inbox do Chatwoot antes de qualquer código de detecção ser escrito
- [ ] **DELV-02**: O envio de alerta é validado com um teste de janela fria — número em silêncio há mais de 24h, com confirmação manual de que o celular recebeu
- [ ] **DELV-03**: O caminho de entrega escolhido está documentado no log de decisões, incluindo a estratégia de fallback caso a API oficial exija template
- [ ] **DELV-04**: O usuário pode disparar um alerta de teste sob demanda (`--test-alert`) sem precisar do jogo aberto
- [ ] **DELV-05**: O usuário pode rodar o scanner em modo simulação (`--dry-run`), vendo os alertas no console sem enviar nada
- [ ] **DELV-06**: Falha de entrega ao Chatwoot é reportada de forma visível no console — nunca falha em silêncio
- [ ] **DELV-07**: Cada alerta é gravado em um arquivo de saída durável antes da tentativa de envio, de modo que nenhum evento se perca numa queda de rede
- [ ] **DELV-08**: Falhas de rede transitórias são reenviadas com backoff; erros definitivos (4xx) não são reenviados
- [ ] **DELV-09**: O alerta chega em português, com nome do membro, o que aconteceu e o horário local

### Captura (Capture)

- [ ] **CAPT-01**: O scanner captura a região da party window a partir de coordenadas de um arquivo de calibração — nenhuma coordenada fixa no código
- [ ] **CAPT-02**: A captura funciona corretamente com o jogo em janela no segundo monitor, sem distorção por escala de DPI
- [ ] **CAPT-03**: O scanner grava sessões de jogo (`--record`) em frames + observações, para servir de base de calibração e teste
- [ ] **CAPT-04**: Frame preto ou corrompido é classificado como falha de captura, nunca como "todas as barras vazias"
- [ ] **CAPT-05**: Uma tela estática (party parada, todo mundo com HP cheio) não é confundida com perda de visão
- [ ] **CAPT-06**: O laço principal sobrevive a exceções — um erro em qualquer etapa não derruba o scanner
- [ ] **CAPT-07**: O scanner se recusa a iniciar se a geometria de tela mudou desde a calibração

### Calibração (Calibration)

- [ ] **CALI-01**: O usuário define as regiões a vigiar arrastando o mouse sobre uma imagem, sem editar coordenadas à mão
- [ ] **CALI-02**: O usuário ajusta os limiares de cor das barras com controles visuais, vendo o efeito ao vivo
- [ ] **CALI-03**: A calibração pode ser feita sobre uma sessão gravada, sem o jogo aberto
- [ ] **CALI-04**: O usuário pode ver uma imagem com todas as regiões desenhadas por cima, para conferir visualmente antes de confiar
- [ ] **CALI-05**: A calibração é gravada separada das configurações escritas à mão, sem sobrescrever uma a outra

### Detecção (Detection)

- [ ] **DTCT-01**: O scanner mede o preenchimento da barra de HP de cada membro da party
- [ ] **DTCT-02**: A leitura da barra vermelha trata a volta do matiz, sem leituras espúrias de 0%
- [ ] **DTCT-03**: A medição de 0% de HP é distinguível de "linha ausente"
- [ ] **DTCT-04**: O scanner detecta se a party window está visível por uma âncora independente das barras dos membros — de modo que um wipe total nunca seja confundido com alt-tab
- [ ] **DTCT-05**: O scanner detecta se a linha de um membro sumiu da party window
- [ ] **DTCT-06**: O scanner monitora também a barra de HP do próprio personagem do usuário
- [ ] **DTCT-07**: O scanner se recusa a iniciar se todos os membros lerem 0% — sinal de calibração errada

### Alerta (Alerting)

- [ ] **ALRT-01**: Morte só é confirmada após N leituras consecutivas de HP zerado, com N configurável
- [ ] **ALRT-02**: Saída da PT só é confirmada após alguns segundos de linha ausente
- [ ] **ALRT-03**: Ressurreição exige mais confirmações para sair do estado morto do que para entrar, evitando alerta oscilante
- [ ] **ALRT-04**: Cada evento gera exatamente um alerta — um morto por cinco minutos não vira cinco minutos de mensagens
- [ ] **ALRT-05**: Enquanto a party window não está visível, nenhum alerta é enviado, e a verificação de visibilidade acontece antes das verificações por membro
- [ ] **ALRT-06**: Um evento que começou pouco antes de uma perda de visão ainda é alertado quando a visão volta
- [ ] **ALRT-07**: Ao voltar de uma perda de visão, o scanner concede um período de tolerância antes de voltar a alertar
- [ ] **ALRT-08**: Cada alerta identifica o membro pelo nome, nunca "alguém"
- [ ] **ALRT-09**: A identidade do membro vem de uma lista configurada pelo usuário, não de leitura de texto da tela
- [ ] **ALRT-10**: Fechar o jogo intencionalmente não dispara alertas de saída para todos os membros
- [ ] **ALRT-11**: O texto do alerta é fraseado de forma que sobreviva a um falso positivo (ex.: "HP zerado há 6s — possível morte")

### Operação (Operations)

- [ ] **OPER-01**: O usuário inicia o scanner com um clique, sem rituais de ambiente virtual
- [ ] **OPER-02**: O console mostra o estado ao vivo de cada membro, para conferência antes de sair AFK
- [ ] **OPER-03**: O scanner avisa no WhatsApp quando começa e quando termina de monitorar, para que o silêncio signifique algo
- [ ] **OPER-04**: Uma perda de visão longa (além de alguns minutos) gera um aviso no WhatsApp, e ao voltar informa por quanto tempo esteve cego
- [ ] **OPER-05**: Um indicador de atividade fica visível fora da área do jogo, para o usuário saber num relance que o scanner está vivo
- [ ] **OPER-06**: A tela não entra em suspensão enquanto o scanner está rodando
- [ ] **OPER-07**: Eventos são gravados em log estruturado, e ao encerrar o scanner apresenta um resumo da sessão
- [ ] **OPER-08**: O token da API do Chatwoot fica fora do código e fora do controle de versão, e nunca aparece em log

### Testabilidade (Testability)

- [ ] **TEST-01**: A lógica de detecção e decisão é testável sem o jogo aberto e sem rede
- [ ] **TEST-02**: Uma sessão gravada pode ser reproduzida e verificada contra os eventos esperados
- [ ] **TEST-03**: Um falso positivo encontrado na prática pode virar caso de teste permanente
- [ ] **TEST-04**: Os casos difíceis têm teste dedicado: alt-tab durante morte, wipe total, morto por muito tempo, party window sumindo

### Segurança (Safety)

- [ ] **SAFE-01**: O scanner nunca envia input ao jogo, não lê memória do processo, não injeta código e não intercepta tráfego
- [ ] **SAFE-02**: Nenhuma biblioteca de automação de input entra na lista de dependências, tornando a violação estruturalmente impossível
- [ ] **SAFE-03**: A documentação do projeto declara honestamente o risco residual, sem afirmar "risco zero"
- [ ] **SAFE-04**: Imagens da tela do jogo nunca são enviadas para serviços de terceiros fora do Chatwoot do próprio usuário

## v2 Requirements

Adiado para depois da v1. Rastreado mas fora do roadmap atual.

### Identificação

- **OCRN-01**: Os nomes dos membros são lidos da tela automaticamente, dispensando configuração manual da lista
- **OCRN-02**: A lista de membros se reajusta sozinha quando a composição da party muda
- **OCRN-03**: O alerta inclui um recorte da tela no momento do evento, como evidência

### Captura avançada

- **ADVC-01**: O scanner funciona com a janela do jogo coberta por outras janelas
- **ADVC-02**: O scanner reencontra a party window sozinho se ela for movida
- **ADVC-03**: O scanner inicia junto com o Windows e detecta sozinho quando o jogo abre

### Sinais complementares

- **CORR-01**: As mensagens do chat de sistema são lidas como sinal de confirmação dos eventos
- **CORR-02**: Um serviço externo detecta se o PC do usuário travou ou desligou
- **CORR-03**: Mortes simultâneas são consolidadas em um único aviso de wipe
- **CORR-04**: Cada membro pode receber alertas em um destino diferente

## Out of Scope

| Feature | Reason |
|---------|--------|
| Leitura de memória do processo | Risco de ban e quebra a cada patch; captura de tela resolve |
| Sniffing de pacotes | Protocolo criptografado; semanas de trabalho para dado que a tela já mostra |
| Leitura de log em arquivo | Verificado: o cliente não grava chat nem eventos em disco |
| Qualquer automação dentro do jogo | O scanner é somente leitura — é o vetor de ban concreto |
| Overlay gráfico dentro do jogo | Exige hook de renderização, que é território de ban |
| Aviso de "está morrendo" (HP baixo) | Spam contínuo de cruzamento de limiar; faz o grupo silenciar as notificações |
| Comandos de volta pelo WhatsApp | Escopo de bot bidirecional, sem relação com o valor central |
| Alerta sonoro local | O usuário está AFK por premissa — não há ninguém para ouvir |
| Upload de screenshot para serviços externos | Privacidade; a tela do usuário não sai do Chatwoot dele |
| OCR contínuo a cada frame | Ponto quente de CPU e maior fonte de falso positivo |

## v2 Requirements — Milestone "Agenda e Silenciamento"

**Definido:** 2026-08-24
**Por que este milestone existe:** as fases 1-5 responderam "o que aconteceu na
tela". Este milestone responde uma pergunta diferente e complementar: "que horas
sao, e isso muda o que vale a pena dizer". Nenhum pixel esta envolvido.

A segunda metade e a mais valiosa e foi o usuario quem a formulou: os alertas
durante um TvT **nao sao falsos** — sao verdadeiros e irrelevantes. Em TvT morre
todo mundo o tempo todo. E filtro de RELEVANCIA, nao correcao de bug, e e uma
categoria de problema que o projeto ainda nao tinha.

### Agenda (AGEN)

- [x] **AGEN-01**: O scanner avisa no WhatsApp 10 minutos antes de cada evento agendado, e de novo no horario exato do evento
- [x] **AGEN-02**: TvT esta agendado para 15:00, 17:00 e 21:50, todos os sete dias da semana
- [x] **AGEN-03**: Prime esta agendado para 20:00, de segunda a quinta-feira
- [x] **AGEN-04**: Os horarios, os dias e os nomes dos eventos ficam em `config.toml`, editaveis a mao com comentario — nunca no codigo. Uma atualizacao do jogo que mude os horarios nao pode exigir mexer em Python
- [x] **AGEN-05**: A agenda funciona com o jogo FECHADO. O aviso vem do relogio, nao da tela, e quem mais precisa do lembrete e justamente quem nao esta online
- [x] **AGEN-06**: Reiniciar o scanner nao reenvia um aviso ja enviado. O estado de "ja avisei este evento hoje" sobrevive ao processo
- [x] **AGEN-07**: Com duas instancias do scanner rodando (o usuario roda Yazalaque e Faerlina lado a lado), o grupo recebe cada aviso UMA vez, nao duas
- [x] **AGEN-08**: Um evento cujo horario ja passou quando o scanner sobe nao dispara aviso atrasado

### Silenciamento (MUTE)

- [x] **MUTE-01**: Durante um evento agendado, os eventos do scanner sao silenciados por completo — morte, ressurreicao, saida, entrada, jogo caiu, cegueira e voce-sem-party
- [x] **MUTE-02**: A janela de silencio do TvT dura 15 minutos a partir do horario do evento
- [x] **MUTE-03**: A janela de silencio do Prime dura 2 horas a partir do horario do evento
- [x] **MUTE-04**: Janelas de silencio sobrepostas se comportam como UNIAO. De segunda a quinta o Prime (20:00-22:00) engole o TvT das 21:50, cuja janela vai ate 22:05 — o silencio termina as 22:05, nunca as 22:00
- [x] **MUTE-05**: Os avisos de AGENDA atravessam o silencio SEMPRE. Sem isto, de segunda a quinta o lembrete do TvT das 21:50 cairia dentro do silencio do Prime e a funcionalidade se anularia sozinha
- [x] **MUTE-06**: Ao fim de cada janela de silencio, o grupo recebe UMA mensagem dizendo que o evento encerrou e que os convites de party estao sendo reenviados. Sem resumo do que foi engolido
- [x] **MUTE-07**: O que foi silenciado continua indo para o log e para o console. Silencio e do WhatsApp, nunca do registro — depurar um farm depois exige o registro completo
- [x] **MUTE-08**: O console mostra que esta em janela de silencio, e ate quando. Um scanner calado precisa parecer calado de proposito

### Operacao (OPER, continuando a numeracao)

- [x] **OPER-09**: O usuario pode rodar so a agenda, sem vigilancia de party e sem o jogo aberto
- [x] **OPER-10**: O usuario pode testar um aviso de agenda sob demanda, sem esperar as 15h
- [x] **OPER-11**: `--dry-run` cobre a agenda e o silenciamento igual cobre o resto: tudo no console, nada enviado

## Out of Scope (deste milestone)

| Feature | Reason |
|---------|--------|
| Enviar convite de party no jogo | Restricao dura do projeto: o scanner e somente leitura e NUNCA envia input ao jogo. A mensagem de encerramento so AVISA que os convites estao sendo reenviados — quem convida e uma pessoa |
| Detectar na tela que o TvT comecou | A agenda ja sabe a hora. Ler a tela para confirmar seria trabalho novo de calibracao para responder o que o relogio ja responde de graca |
| Resumo do que foi silenciado | Usuario escolheu explicitamente: so o aviso de encerramento. Menos mensagem no grupo |
| Rodar com o PC desligado | "Independente do jogo" nao e "independente do PC". Se a maquina estiver desligada as 15h nao ha aviso. Um agendamento no servidor resolveria, mas e outro projeto |
| Ajuste automatico de horario apos atualizacao do jogo | Nao ha fonte confiavel para ler os horarios novos. O usuario edita `config.toml`, que e justamente por que AGEN-04 existe |
| Fuso horario configuravel | Os horarios sao a hora local da maquina, que e a mesma do usuario. O Brasil nao tem mais horario de verao desde 2019, entao nao ha deslocamento sazonal a tratar |

## Traceability — Milestone v2

| Requisito | Fase | Status |
|---|---|---|
| AGEN-01 a AGEN-04 | Fase 6 | Completo |
| AGEN-05, OPER-09, OPER-10, OPER-11 | Fase 6 | Completo |
| AGEN-06, AGEN-07, AGEN-08 | Fase 6 | Completo |
| MUTE-01 a MUTE-08 | Fase 7 | Completo |

**Cobertura v2:** 19 de 19 mapeados e implementados. 80 testes novos.

**Falta validação humana**, não implementação:
- Deixar `--so-agenda` rodando e ver um aviso real chegar no WhatsApp
- Atravessar um TvT de verdade e confirmar que o silêncio cala e o encerramento chega

## v3 Requirements — Milestone "Lista de presença do Solo Boss"

**Definido:** 2026-08-26 (derivado em `/gsd-plan-phase 10`)
**Por que este milestone existe:** o milestone v1 respondeu "o que aconteceu
na tela" e o v2 respondeu "que horas são". Este responde uma terceira: "quem
vai". Nenhum pixel está envolvido, e o dado novo não vem do jogo nem do
relógio — vem das pessoas, pelo WhatsApp.

O coração da fase não é a lista: é a **autorização em dois níveis**. Hoje
`autor_autorizado` é global, e pôr o telefone de quatro a oito party-mates
nela daria a todos eles `.corrigir` e `.pegou`, que reescrevem estatística
permanente numa pasta sem poda e sem backup. É por isso que o nível novo vem
primeiro e sozinho no roadmap.

### Presença (PRES)

- [ ] **PRES-01**: A 1h50 antes de cada ocorrência de Solo Boss o grupo recebe uma chamada com o horário do próximo boss, e o aviso de 10 minutos antes continua saindo intacto
- [ ] **PRES-02**: A chamada é opt-in por evento: só o `[[evento]]` que declarar `chamar_minutos_antes` ganha o aviso novo — TvT e Prime não mudam de comportamento em nada
- [ ] **PRES-03**: Um telefone declarado em `[[membro]]` no `config.toml` alcança exclusivamente `.join` e `.leave`; `.cancelar`, `.solo`, `.party`, `.status`, `.loot-<nick>`, `.<nick>`, `.corrigir-<nick>`, `.pegou` e `.help` são recusados para ele
- [ ] **PRES-04**: O nível de dono (`CHATWOOT_TELEFONES_COMANDO`) continua alcançando TODOS os comandos, inclusive `.join` e `.leave` — o nível de membro é ADITIVO, nunca exclusivo
- [ ] **PRES-05**: Um `.join` no privado do bot põe o nick do remetente na lista da próxima ocorrência, e o grupo recebe a confirmação com o NICK configurado, nunca com o nome do contato do WhatsApp
- [ ] **PRES-06**: `.join` repetido responde no privado que a pessoa já está na lista e NÃO produz uma segunda mensagem no grupo
- [ ] **PRES-07**: `.join` fora de qualquer janela é aceito e vale para a próxima ocorrência; a resposta sempre diz QUAL horário pegou
- [ ] **PRES-08**: `.leave` tira quem desistiu da lista e o grupo fica sabendo; `.leave` de quem nunca deu `.join` responde isso e não anuncia nada
- [ ] **PRES-09**: A confirmação sai nos dois lugares com redações DIFERENTES: uma linha curta no privado de quem mandou e a confirmação no grupo
- [ ] **PRES-10**: A lista mora no `.agenda/` com prefixo próprio, criada com `O_CREAT|O_EXCL`, e as duas instâncias do usuário nunca produzem uma confirmação em dobro
- [ ] **PRES-11**: Marcadores de presença são podados junto com os demais depois de 3 dias — a lista morre quando o boss passa, ao contrário da estatística de loot
- [ ] **PRES-12**: No horário do boss a lista fecha e o grupo recebe quem confirmou; zero confirmações produz zero mensagem, e o fechamento não depende de ligar `avisar_no_horario`
- [ ] **PRES-13**: `.leave` depois do fechamento é recusado, dizendo que o boss já começou
- [ ] **PRES-14**: A vez do próximo loot é SUGERIDA entre quem estava na lista fechada; `.loot-<nick>` de quem não joinou avisa e OBEDECE — nunca recusa
- [ ] **PRES-15**: Tudo é demonstrável com o jogo fechado e sem rede: o tempo entra por parâmetro, o mapa telefone→nick entra por dado, e a corrida entre as duas instâncias tem teste próprio

## Out of Scope (deste milestone)

| Feature | Reason |
|---------|--------|
| Chamada para TvT e Prime | O mecanismo fica genérico nesta fase, mas ligar em outros eventos é outro volume de mensagem e decisão de outro dia |
| `.join` de convidado fora do `[[membro]]` | Hoje ele é simplesmente ignorado; um fluxo de convite é uma fase própria |
| Estatística de presença ("quantos Solo Boss o J4guar foi") | A lista é podada em 3 dias de propósito; virar estatística exigiria pasta sem poda, como o `.loot/` |
| Cutucar no privado quem não respondeu | Superfície nova de mensagem, individual, e merece decisão separada |
| Bloquear `.loot-<nick>` de quem não joinou | A autoridade é o usuário, não o registro. Bloquear transformaria conveniência em obstáculo no pior momento |
| Consertar a poda dos marcadores `comando_<id>` | Observado nesta fase: eles também nunca são podados, porque não têm data no nome. Resolver exige outro desenho de chave |

### Traceability — Milestone v3

| Requisito | Plano | Status |
|---|---|---|
| PRES-03, PRES-04 | 10-01 | Pending |
| PRES-01, PRES-02 | 10-02 | Pending |
| PRES-07, PRES-10, PRES-11, PRES-13, PRES-15 | 10-03 | Pending |
| PRES-05, PRES-06, PRES-08, PRES-09 | 10-03b | Pending |
| PRES-12 | 10-04 | Pending |
| PRES-14, PRES-15 | 10-05 | Pending |

**Cobertura v3:** 15 de 15 mapeados. Nenhum requisito sem plano, nenhum plano
sem requisito.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DELV-01 | Phase 1 | Pending |
| DELV-02 | Phase 1 | Pending |
| DELV-03 | Phase 1 | Pending |
| DELV-04 | Phase 4 | Pending |
| DELV-05 | Phase 4 | Pending |
| DELV-06 | Phase 4 | Pending |
| DELV-07 | Phase 4 | Pending |
| DELV-08 | Phase 4 | Pending |
| DELV-09 | Phase 4 | Pending |
| CAPT-01 | Phase 1 | Pending |
| CAPT-02 | Phase 1 | Pending |
| CAPT-03 | Phase 1 | Pending |
| CAPT-04 | Phase 1 | Pending |
| CAPT-05 | Phase 1 | Pending |
| CAPT-06 | Phase 1 | Pending |
| CAPT-07 | Phase 1 | Pending |
| CALI-01 | Phase 2 | Pending |
| CALI-02 | Phase 2 | Pending |
| CALI-03 | Phase 2 | Pending |
| CALI-04 | Phase 2 | Pending |
| CALI-05 | Phase 2 | Pending |
| DTCT-01 | Phase 2 | Pending |
| DTCT-02 | Phase 2 | Pending |
| DTCT-03 | Phase 2 | Pending |
| DTCT-04 | Phase 2 | Pending |
| DTCT-05 | Phase 2 | Pending |
| DTCT-06 | Phase 2 | Pending |
| DTCT-07 | Phase 2 | Pending |
| ALRT-01 | Phase 3 | Pending |
| ALRT-02 | Phase 3 | Pending |
| ALRT-03 | Phase 3 | Pending |
| ALRT-04 | Phase 3 | Pending |
| ALRT-05 | Phase 3 | Pending |
| ALRT-06 | Phase 3 | Pending |
| ALRT-07 | Phase 3 | Pending |
| ALRT-08 | Phase 3 | Pending |
| ALRT-09 | Phase 3 | Pending |
| ALRT-10 | Phase 3 | Pending |
| ALRT-11 | Phase 4 | Pending |
| OPER-01 | Phase 1 | Pending |
| OPER-02 | Phase 3 | Pending |
| OPER-03 | Phase 4 | Pending |
| OPER-04 | Phase 4 | Pending |
| OPER-05 | Phase 4 | Pending |
| OPER-06 | Phase 4 | Pending |
| OPER-07 | Phase 3 | Pending |
| OPER-08 | Phase 1 | Pending |
| TEST-01 | Phase 3 | Pending |
| TEST-02 | Phase 3 | Pending |
| TEST-03 | Phase 3 | Pending |
| TEST-04 | Phase 3 | Pending |
| SAFE-01 | Phase 1 | Pending |
| SAFE-02 | Phase 1 | Pending |
| SAFE-03 | Phase 1 | Pending |
| SAFE-04 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 55 total
- Mapped to phases: 55 (Fase 1: 16, Fase 2: 12, Fase 3: 16, Fase 4: 11)
- Unmapped: 0

---
*Requirements defined: 2026-08-24*
*Last updated: 2026-08-24 after roadmap creation (traceability filled)*
