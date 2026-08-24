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

## Traceability

Preenchido durante a criação do roadmap.

**Coverage:**
- v1 requirements: 55 total
- Mapped to phases: pending
- Unmapped: pending

---
*Requirements defined: 2026-08-24*
*Last updated: 2026-08-24 after initial definition*
