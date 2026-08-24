# L2 Party Scanner

## What This Is

Um "scanner" que vigia a tela do Lineage 2 XM Essence enquanto o usuário farma em party e avisa no WhatsApp quando algo importante acontece: um membro da PT morreu, saiu do grupo ou ressuscitou. A partir do milestone v2 ele também vigia o **relógio**: avisa a party dos eventos agendados do jogo (TvT e Prime) e cala os alertas durante esses eventos, porque em evento morre todo mundo o tempo todo. O envio de WhatsApp é feito via API do Chatwoot já configurado no servidor do usuário; a detecção é 100% passiva, por captura e análise de tela (sem tocar no processo do jogo).

## Core Value

Quando alguém da party morre ou sai da PT, a galera fica sabendo no WhatsApp em segundos — mesmo quem está AFK.

## Requirements

### Validated

<!-- Milestone v1, entregue 2026-08-24. 255 testes. -->

- ✓ Detectar morte de membro da party — Fase 3, verificado em campo (12 eventos num combate real, 13:39-13:42)
- ✓ Detectar saída de membro da party — Fase 3, verificado com o nome certo
- ✓ Detectar ressurreição — Fase 3, verificado em campo
- ✓ Monitorar o personagem do próprio usuário — Fase 2/3
- ✓ Identificar QUEM morreu/saiu pelo nome — Fase 3, mas **por template da imagem do nome, não por OCR** (ver Key Decisions)
- ✓ Enviar alerta via API do Chatwoot — Fase 4, entrega confirmada no celular
- ✓ Modo "cego" sem falsos positivos — Fases 3 a 5, quatro rodadas de correção
- ✓ Debounce e histerese assimétrica — Fase 3
- ✓ Cooldown de um alerta por evento — Fase 3
- ✓ Execução manual com console ao vivo — Fase 3
- ✓ Reconhecer tela de login e desconexão do servidor — Fase 5

### Active

<!-- Milestone v2 — "Agenda e Silenciamento", definido 2026-08-24. -->

- [ ] Avisar a party 10 min antes e no horário de cada evento agendado do jogo
- [ ] TvT às 15:00, 17:00 e 21:50, todo dia; Prime às 20:00, de segunda a quinta
- [ ] Horários e dias em `config.toml`, editáveis à mão — uma atualização do jogo não pode custar um commit de código
- [ ] A agenda funciona com o jogo FECHADO: o aviso vem do relógio, não da tela
- [ ] Silenciar por completo os alertas do scanner durante o evento — 15 min no TvT, 2h no Prime
- [ ] Janelas de silêncio sobrepostas se comportam como união
- [ ] Os avisos de agenda atravessam o silêncio sempre
- [ ] Uma mensagem ao fim de cada silêncio, dizendo que o evento encerrou e que os convites de party estão sendo reenviados
- [ ] Nada de duplicar avisos: nem ao reiniciar o scanner, nem entre as duas instâncias que o usuário roda

### Out of Scope

- Leitura de memória do processo do jogo — risco de ban e frágil a cada patch; captura de tela resolve
- Sniffing de pacotes — protocolo criptografado, semanas de engenharia reversa para dado que a tela já mostra
- Leitura de log em arquivo — verificado: o cliente não grava chat/eventos em disco (só log de engine)
- Alerta de "perda de visão" no WhatsApp — v1 mostra só no console; usuário optou por não alertar
- Modo "sempre ligado" (autostart com Windows) — v1 é manual; considerar em v2
- Qualquer automação/ação dentro do jogo — o scanner é somente leitura, nunca envia input ao jogo
- Enviar convite de party no jogo — cai direto na linha acima. A mensagem de fim de evento apenas AVISA que os convites estão sendo reenviados; quem convida é uma pessoa
- Detectar na tela que o TvT começou — o relógio já sabe a hora; ler a tela seria calibração nova para responder o que já é de graça
- Rodar com o PC desligado — "independente do jogo" não é "independente do PC". Um agendamento no servidor resolveria, e é outro projeto
- Ajustar sozinho os horários depois de uma atualização do jogo — não há fonte confiável para lê-los; por isso os horários são configuráveis à mão

## Context

- **Jogo**: Lineage 2 XM Essence (cliente Unreal Engine 2), instalado em `C:\Users\refun\Downloads\XM-Essence-Launcher`
- **Configuração do usuário**: jogo em modo janela 1718x1360, aparentemente em segundo monitor (`GamePlayViewportStartX=1713` no Option.ini); Gamma=1.16 (usar limiares de cor em HSV, não RGB)
- **Party window**: mostra até 4+ membros (TioMad, Kaus, Korzis, J4guar no exemplo), cada linha com nome, ícone de classe, barra de HP (vermelha) e MP (azul). A MP serve de verificação de presença da linha: MP presente + HP vazio = morte real; nada presente = saiu ou UI sumiu
- **Chat de sistema**: gera mensagem "X has left the party" (confirmado empiricamente), mas NÃO grava em arquivo e rola rápido durante farm; morte de membro provavelmente não gera mensagem (a confirmar). Chat via OCR fica como sinal complementar futuro
- **Fora de alcance / teleporte (VERIFICADO 2026-08-24)**: o usuário testou — ao teleportar ou se afastar dos membros, as barras da party window **não mudam**: mesma cor, preenchimento normal. Distância NÃO apaga nem acinzenta o HP. Isso elimina o maior risco de falso positivo do projeto (fora-de-alcance sendo confundido com morte)
- **Atualização ao vivo de membro distante (VERIFICADO 2026-08-24)**: o HP de membro distante **atualiza ao vivo**, não congela. Elimina o risco espelhado de falso negativo silencioso — uma morte longe do observador é detectável normalmente
- **Geometria da party window (VERIFICADO 2026-08-24, par de prints antes/depois)**: a janela é **ancorada no topo e encolhe por baixo** — a altura varia com o número de membros. Consequência de design: a âncora de visibilidade da UI deve ficar no TOPO da janela, nunca na borda inferior, senão ela some sozinha quando a PT diminui. **Ainda não verificado**: se as linhas compactam quando sai alguém do MEIO (o teste feito teve o último membro saindo, caso em que compactar e preservar posição são indistinguíveis)
- **Chatwoot**: já configurado no servidor do usuário com fluxo de WhatsApp funcionando; o scanner só precisa dar POST na API
- **Condições de operação**: party window travada em posição fixa; jogo visível (não minimizado — DirectX para de renderizar). Captura da janela via Windows Graphics Capture (janela em background) é evolução futura

- **Estado real em 2026-08-24 (fim do v1)**: o texto acima descreve as suposições do começo do projeto e várias foram superadas. O que vale hoje: captura é por **janela** (Windows Graphics Capture), funciona com o jogo coberto e não depende mais de "jogo visível"; **janela minimizada continua impossível** e não há API que contorne. A identificação de nome **não usa OCR** — usa template da imagem do nome, decidido depois que OCR se mostrou desnecessário para um conjunto fechado de 4-8 nomes. O usuário roda **duas instâncias** (Yazalaque e Faerlina) lado a lado, o que é a razão de AGEN-07 existir.
- **Eventos agendados do jogo (informado pelo usuário, 2026-08-24)**: TvT acontece às 15:00, 17:00 e 21:50 todos os dias; Prime às 20:00 de segunda a quinta. **Os horários mudam com atualizações do jogo** — foi o próprio usuário quem levantou isso, e é a razão de eles viverem em `config.toml` e não no código.
- **Por que o silenciamento existe**: durante TvT e Prime as pessoas morrem e reorganizam party o tempo todo. Os alertas não ficam errados — ficam verdadeiros e irrelevantes. É a primeira vez que o projeto precisa de um filtro de RELEVÂNCIA em vez de um filtro de correção, e por isso ele vive no transporte, nunca na detecção.

## Constraints

- **Segurança**: detecção passiva por captura de tela apenas — nunca injetar, ler memória ou enviar input ao jogo (risco de ban zero)
- **Tech stack**: Python no PC do usuário (Windows 11) — mss/dxcam para captura, OpenCV para análise de cor, Tesseract para OCR de nomes, requests para API do Chatwoot
- **Ambiente**: Windows 11, jogo em janela em segundo monitor; script roda na mesma máquina do jogo
- **Latência**: alerta deve chegar em segundos (captura ~1 Hz + debounce ~2-5s + POST no Chatwoot)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Detecção via captura de tela da party window (não memória/pacotes/log) | Passivo, sem risco de ban, robusto a patches; cliente não grava logs em disco (verificado) | — Pending |
| Barra de MP como verificação de presença da linha | Distingue "morte real" (MP presente + HP vazio) de "linha sumiu" (saiu da PT) e "UI ausente" (modo cego) | — Pending |
| OCR de nomes só na inicialização e em mudança de composição | Nome não muda a cada frame; evita custo de OCR contínuo | — Pending |
| Limiar de cor em HSV | Imune ao Gamma=1.16 do cliente | — Pending |
| Chatwoot como único canal de saída | WhatsApp já funcionando no servidor do usuário; scanner só faz POST | — Pending |
| Canal confirmado: fork `fazer-ai/chatwoot` com Baileys, na VPS do projeto Atenda | Bridge **não-oficial** → sem a janela de 24h da Meta, mensagem livre a qualquer hora, e o fork tem conversas de grupo nativas. Elimina o maior risco do projeto | ✓ Good |
| v1 manual (usuário inicia o script) | Simplicidade; autostart fica para v2 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-24 after milestone v2 definition (Agenda e Silenciamento) — anteriormente: initialization*
