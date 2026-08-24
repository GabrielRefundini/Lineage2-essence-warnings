---
gsd_state_version: '1.0'
status: implementado
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 6
  completed_plans: 6
  percent: 95
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-24)

**Core value:** Quando alguém da party morre ou sai da PT, a galera fica sabendo no WhatsApp em segundos — mesmo quem está AFK.
**Current focus:** Aguardando validação em farm real

## Current Position

Phase: 4 de 4 — todas implementadas
Status: Código completo e verificado ao vivo. Falta apenas validação humana.
Last activity: 2026-08-24 — Fases 1 a 4 construídas e testadas contra a tela real

Progress: [█████████░] 95%

## O que foi construído

| Fase | Entrega | Estado |
|------|---------|--------|
| 1 | Gate de entrega + captura com DPI + gravador | ✓ código pronto, falta confirmar envio no celular |
| 2 | Calibrador automático + leitura das barras | ✓ verificado contra a tela real |
| 3 | Rastreador de estado, debounce, histerese, portão de cegueira | ✓ 29 testes |
| 4 | Notificador Chatwoot, console ao vivo, replay | ✓ verificado ao vivo |

**102 testes passando**, todos sem precisar do jogo aberto ou de rede.

## Calibração real medida (2026-08-24)

Cliente XM Essence, janela do Yazalaque em (1713,0), monitor ultrawide 3440x1440.
O usuário roda **duas instâncias** (Yazalaque e Faerlina) lado a lado.

| Elemento | Medida |
|----------|--------|
| Barras de HP | x 1780–1899, 120x8 px |
| Barra de MP | 11 px abaixo do HP |
| Ícone de classe | (1750, 359), 24x24 px |
| Passo entre membros | 61 px |
| Âncora da janela | canto da moldura em (1718, 328) |
| HSV do vermelho cheio | H=5, S≈210, V≈144 |

## Accumulated Context

### Decisões

- [Fase 2]: **A saturação é o discriminador, não o matiz.** A parte vazia da barra é transparente e mostra o terreno do jogo (S≈75), enquanto a barra cheia é sólida (S≈210). Um chão avermelhado enganaria um teste só de matiz.
- [Fase 2]: **O ícone de classe é o indicador de presença.** "HP zerado" e "linha ausente" leem exatamente igual nas barras (0%). O ícone existe independente do HP: margem medida de 43-52 de desvio contra 9-10 do terreno.
- [Fase 2]: **A âncora fica no topo da janela.** Verificado pelos prints do usuário: a party window é ancorada em cima e encolhe por baixo. Uma âncora embaixo sumiria sozinha quando a PT diminuísse.
- [Fase 2]: **Tudo depois da primeira linha vazia é forçado a vazio.** A região capturada é mais alta que a janela de propósito, e o excedente cai sobre o chat e o minimapa — que têm contraste alto e virariam membro fantasma.
- [Fase 3]: O portão de visibilidade é avaliado antes das linhas; cegueira congela contadores em vez de zerar; ressurreição exige mais confirmações que a morte.
- [Fase 4]: O replay usa os horários gravados, não o relógio — senão uma sessão de uma hora reproduzida em trinta segundos mediria o debounce errado.
- [Fase 1]: `mss` em vez de `dxcam` — `dxcam.grab()` devolve `None` em frame não alterado, e party window parada em AFK é exatamente esse caso.

### Blockers/Concerns

- ~~**[Fase 1 — portão duro] Provedor de WhatsApp**~~ **RESOLVIDO**: o usuário roda o fork `fazer-ai/chatwoot` com **Baileys** na VPS do projeto Atenda. Bridge não-oficial → sem a janela de 24h da Meta, mensagem livre a qualquer hora, envio para grupo funciona. **Falta a confirmação empírica** (rodar `check_whatsapp.py` e ver a mensagem chegar no celular).
- ~~**[Falso negativo silencioso] HP de membro distante congela?**~~ **RESOLVIDO 2026-08-24 (teste do usuário): atualiza ao vivo.**
- ~~**[Falso positivo] Fora de alcance parece morte?**~~ **RESOLVIDO 2026-08-24 (teste do usuário): distância não altera a barra.**
- **[Aberto — nomeação de eventos]** A party window compacta as linhas quando sai alguém do MEIO? O teste do usuário foi inconclusivo: quem saiu (J4guar) era o último da lista, caso em que compactar e preservar posição produzem a mesma imagem. **Impacto limitado**: se compactar, um evento pode ser atribuído ao nome errado depois de alguém sair. **Teste**: sair o Kaus (com Korzis abaixo) e ver se o Korzis sobe.
- **[Aberto — não testável agora]** Morte de membro: o usuário não conseguiu testar. Toda a lógica de morte foi verificada com frames sintéticos, mas **nunca contra uma morte real**. É o que a gravação de sessão existe para resolver.
- **[Aberto — limiar de cor]** O matiz da barra de HP muda com o nível? Na captura real todos estavam em 100%. Uma sessão gravada com HP variando resolve.

## Quick Tasks Completed

| Data | Tarefa | Resultado |
|------|--------|-----------|
| 2026-08-24 | [identidade-por-imagem-do-nome](quick/20260824-identidade-por-imagem-do-nome/SUMMARY.md) | O nome no alerta vem de reconhecer a IMAGEM do nome na tela, não da posição da linha. Margem medida de 0.546 (mesmo nome 1.000, outros máx 0.454). Resolve o alerta sair com o nome errado quando a ordem da party muda. |

## Próximos passos

1. **Confirmar o gate de entrega** — `.env` + `check_whatsapp.py inboxes/conversas/enviar`, confirmando no celular
2. **Farmar com `--record` ligado** até bancar uma morte real
3. **Rodar o replay** dessa sessão e conferir se o alerta de morte dispara na hora certa
4. **Testar a compactação** — alguém do meio sair da PT

## Session Continuity

Last session: 2026-08-24
Stopped at: Fases 1-4 implementadas, 102 testes passando, verificado ao vivo contra o cliente aberto
Resume file: None
