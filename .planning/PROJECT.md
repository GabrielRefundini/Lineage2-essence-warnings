# L2 Party Scanner

## What This Is

Um "scanner" que vigia a tela do Lineage 2 XM Essence enquanto o usuário farma em party e avisa no WhatsApp quando algo importante acontece: um membro da PT morreu, saiu do grupo ou ressuscitou. O envio de WhatsApp é feito via API do Chatwoot já configurado no servidor do usuário; a detecção é 100% passiva, por captura e análise de tela (sem tocar no processo do jogo).

## Core Value

Quando alguém da party morre ou sai da PT, a galera fica sabendo no WhatsApp em segundos — mesmo quem está AFK.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Detectar morte de membro da party (barra de HP zerada na party window, com moldura/MP ainda presentes)
- [ ] Detectar saída de membro da party (linha do membro sumiu da party window)
- [ ] Detectar ressurreição (HP voltou a subir depois de confirmado morto)
- [ ] Monitorar também o personagem do próprio usuário (barra de HP no topo da tela)
- [ ] Identificar QUEM morreu/saiu pelo nome (OCR dos nomes da party window)
- [ ] Enviar alerta via API do Chatwoot para o grupo/números do WhatsApp da party
- [ ] Modo "cego": suprimir alertas quando a party window inteira some (loading, alt-tab, jogo minimizado) — sem falsos positivos
- [ ] Debounce/histerese: morte confirma após N capturas seguidas; saída após alguns segundos de ausência
- [ ] Cooldown: 1 alerta por evento (não spammar até ressuscitar)
- [ ] Execução manual: usuário inicia o script quando começa a farmar; console mostra status em tempo real

### Out of Scope

- Leitura de memória do processo do jogo — risco de ban e frágil a cada patch; captura de tela resolve
- Sniffing de pacotes — protocolo criptografado, semanas de engenharia reversa para dado que a tela já mostra
- Leitura de log em arquivo — verificado: o cliente não grava chat/eventos em disco (só log de engine)
- Alerta de "perda de visão" no WhatsApp — v1 mostra só no console; usuário optou por não alertar
- Modo "sempre ligado" (autostart com Windows) — v1 é manual; considerar em v2
- Qualquer automação/ação dentro do jogo — o scanner é somente leitura, nunca envia input ao jogo

## Context

- **Jogo**: Lineage 2 XM Essence (cliente Unreal Engine 2), instalado em `C:\Users\refun\Downloads\XM-Essence-Launcher`
- **Configuração do usuário**: jogo em modo janela 1718x1360, aparentemente em segundo monitor (`GamePlayViewportStartX=1713` no Option.ini); Gamma=1.16 (usar limiares de cor em HSV, não RGB)
- **Party window**: mostra até 4+ membros (TioMad, Kaus, Korzis, J4guar no exemplo), cada linha com nome, ícone de classe, barra de HP (vermelha) e MP (azul). A MP serve de verificação de presença da linha: MP presente + HP vazio = morte real; nada presente = saiu ou UI sumiu
- **Chat de sistema**: gera mensagem "X has left the party" (confirmado empiricamente), mas NÃO grava em arquivo e rola rápido durante farm; morte de membro provavelmente não gera mensagem (a confirmar). Chat via OCR fica como sinal complementar futuro
- **Fora de alcance / teleporte (VERIFICADO 2026-08-24)**: o usuário testou — ao teleportar ou se afastar dos membros, as barras da party window **não mudam**: mesma cor, preenchimento normal. Distância NÃO apaga nem acinzenta o HP. Isso elimina o maior risco de falso positivo do projeto (fora-de-alcance sendo confundido com morte). **Fica em aberto o oposto**: se o cliente congela o HP de membro distante (último valor conhecido) em vez de atualizar ao vivo, uma morte longe seria um falso NEGATIVO — a barra ficaria cheia para sempre. A testar: membro distante tomando dano deve fazer a barra cair na tela do usuário
- **Chatwoot**: já configurado no servidor do usuário com fluxo de WhatsApp funcionando; o scanner só precisa dar POST na API
- **Condições de operação**: party window travada em posição fixa; jogo visível (não minimizado — DirectX para de renderizar). Captura da janela via Windows Graphics Capture (janela em background) é evolução futura

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
*Last updated: 2026-08-24 after initialization*
