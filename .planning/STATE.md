---
gsd_state_version: '1.0'
status: milestone-v2-definido
progress:
  total_phases: 7
  completed_phases: 7
  total_plans: 6
  completed_plans: 6
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-24)

**Core value:** Quando alguém da party morre ou sai da PT, a galera fica sabendo no WhatsApp em segundos — mesmo quem está AFK.
**Current focus:** Milestone v2 implementado; falta validação em campo

## Current Position

Phase: 4 de 4 — todas implementadas
Status: Código completo, 338 testes. Nenhum bug conhecido em aberto. O que falta é VALIDAÇÃO EM CAMPO, não implementação: a última milha (morte real -> mensagem no WhatsApp na mesma sessão) e ver a agenda/silêncio funcionando num TvT de verdade. A cegueira recorrente teve a causa encontrada e tratada na Fase 5 (era manutenção do servidor).
Last activity: 2026-08-25 — O aviso de agenda vai para o WhatsApp na mesma moldura do console

Progress: [██████████] 100% (7 de 7 fases)

## O que foi construído

| Fase | Entrega | Estado |
|------|---------|--------|
| 1 | Gate de entrega + captura com DPI + gravador | ✓ **entrega confirmada no celular 2026-08-24** |
| 2 | Calibrador automático + leitura das barras | ✓ verificado contra a tela real |
| 3 | Rastreador de estado, debounce, histerese, portão de cegueira | ✓ 226 testes; morte real detectada em campo |
| 4 | Notificador Chatwoot, console ao vivo, replay | ✓ verificado ao vivo |
| 5 | Tela de login e desconexão do servidor viram evento | ✓ verificado ao vivo contra as duas janelas |
| 6 | Agenda de TvT e Prime, rodando sem o jogo aberto | ✓ verificado ao vivo com o cliente fechado |
| 7 | Silêncio durante o evento, com união de janelas | ✓ simulado minuto a minuto de 19:45 a 22:10 |

**446 testes passando**, todos sem precisar do jogo aberto ou de rede.

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

### Aprendizados extraídos

| Fase | Arquivo | D / L / P / S |
|---|---|---|
| 6 — A agenda como fonte de eventos | [06-LEARNINGS.md](phases/06-a-agenda-como-fonte-de-eventos/06-LEARNINGS.md) | 8 / 4 / 4 / 2 |
| 7 — Silenciamento por janela de evento | [07-LEARNINGS.md](phases/07-silenciamento-por-janela-de-evento/07-LEARNINGS.md) | 7 / 5 / 5 / 3 |

**O fio que atravessa as duas fases:** a lógica pura deste projeto está sólida
(rastreador 98%, visão 95%, agenda 94%) e **todo o risco mora na integração**
(`__main__.py` 20%, `captura_janela.py` 19%). Os 3 de 3 warnings do code review
moravam lá. Duas fontes independentes — leitura de código e medição de cobertura
— apontando o mesmo lugar.

**E um padrão que já apareceu quatro vezes:** toda máquina de estado que anuncia
transições precisa distinguir *"mudou"* de *"foi assim que eu encontrei"*.
Entrada de membro, você-em-party, cliente caído e silêncio — todos exigiram um
terceiro estado registrando ter observado o mundo no estado oposto.

### Decisões

- [solo]: **O portão de cegueira fala da PARTY WINDOW, não de você.** Deixá-lo bloquear a avaliação da própria barra confundia "não vejo a party" com "não vejo você" — e upando solo o scanner ficava cego permanentemente. Medido: 30 frames com HP próprio em ZERO produziam ZERO eventos.
- [solo]: **O discriminador de barra legível é CONTRASTE, nunca saturação.** A parte vazia da barra é transparente e mostra o terreno, então uma barra quase vazia tem saturação baixa. Usar saturação faria o scanner declarar "não consigo ler" exatamente no frame em que o usuário morre. Medido: desvio 38,6 na barra real contra 0,00 num recorte preto.
- [agenda]: **`avisar_no_horario` existe por causa do volume.** Solo Boss são 12 ocorrências/dia; com dois avisos cada seriam 24 mensagens, três vezes o volume de TvT e Prime somados. Um teste trava o total diário em 20.
- [whatsapp]: **A ponte Baileys→Chatwoot não ingere mensagens de grupo.** Medido duas vezes: 0 incoming em 20 mensagens, com o usuário confirmando ter mandado. É configuração de servidor. `check_whatsapp.py entrada` diagnostica e diz onde mexer.

- [v2]: **O relógio é uma segunda fonte de eventos, e entra pelo mesmo seam da tela.** A agenda despacha pelo `Despachante`, nunca chamando `enviar()` direto. É a regra 6 do roadmap v1 aplicada à segunda fonte — se a agenda furar o seam, o silenciamento fica impossível de acrescentar depois.
- [v2]: **O silenciamento vive no TRANSPORTE, não na detecção.** Silenciar na detecção corromperia o estado (quem morre e ressuscita durante o silêncio precisa sair do outro lado com o estado certo) e apagaria o log, que é a única ferramenta de depuração pós-farm do projeto.
- [v2]: **Os avisos de agenda atravessam o silêncio sempre.** De segunda a quinta o TvT das 21:50 cai dentro do silêncio do Prime (20:00-22:00); sem essa regra a funcionalidade se anularia sozinha.
- [v2]: **Janelas de silêncio sobrepostas são união, não substituição.** Seg-qui o silêncio termina às 22:05 (TvT 21:50 + 15min), não às 22:00 (fim do Prime).
- [v2]: **"Já avisei este evento hoje" é estado durável e compartilhado.** Sobreviver ao restart e não duplicar entre as duas instâncias do usuário são o mesmo problema com o mesmo remédio.

- [Fase 5]: **O título da janela é o sinal mais confiável do projeto.** `Yazalaque - XM Essence` jogando, `XM Essence` na tela de login. Texto do Windows: sem limiar, sem HSV, sem calibração, imune a mudança de resolução.
- [Fase 5]: **`windows-capture` casa `window_name` por SUBSTRING.** Pedir `XM Essence` devolve o frame de `Faerlina - XM Essence`. A tela de login não é endereçável por nome — é detectada relendo o título do hwnd que já temos.
- [Fase 5]: **O diálogo de desconexão precisa de pixels porque o título não muda com ele aberto.** É o caso mais importante: AFK + caído deixa o diálogo parado para sempre. Margem medida ao vivo: 0.9997 contra 0.5051, limiar 0.90.

- [Fase 2]: **A saturação é o discriminador, não o matiz.** A parte vazia da barra é transparente e mostra o terreno do jogo (S≈75), enquanto a barra cheia é sólida (S≈210). Um chão avermelhado enganaria um teste só de matiz.
- [Fase 2]: **O ícone de classe é o indicador de presença.** "HP zerado" e "linha ausente" leem exatamente igual nas barras (0%). O ícone existe independente do HP: margem medida de 43-52 de desvio contra 9-10 do terreno.
- [Fase 2]: **A âncora fica no topo da janela.** Verificado pelos prints do usuário: a party window é ancorada em cima e encolhe por baixo. Uma âncora embaixo sumiria sozinha quando a PT diminuísse.
- [Fase 2]: **Tudo depois da primeira linha vazia é forçado a vazio.** A região capturada é mais alta que a janela de propósito, e o excedente cai sobre o chat e o minimapa — que têm contraste alto e virariam membro fantasma.
- [Fase 3]: O portão de visibilidade é avaliado antes das linhas; cegueira congela contadores em vez de zerar; ressurreição exige mais confirmações que a morte.
- [Fase 4]: O replay usa os horários gravados, não o relógio — senão uma sessão de uma hora reproduzida em trinta segundos mediria o debounce errado.
- [Fase 1]: `mss` em vez de `dxcam` — `dxcam.grab()` devolve `None` em frame não alterado, e party window parada em AFK é exatamente esse caso.

### Blockers/Concerns

- ~~**[Fase 1 — portão duro] Provedor de WhatsApp**~~ **RESOLVIDO E CONFIRMADO EMPIRICAMENTE 2026-08-24**: fork `fazer-ai/chatwoot` com **Baileys**. As mensagens do scanner chegaram no grupo do WhatsApp (print do usuário: "Scanner ativo — monitorando Korzis, J4guar, TioMad, Kaus, Yazalaque (voce)"). Sem janela de 24h, envio para grupo funciona. `outbox.jsonl` tem 69 mensagens gravadas.
- ~~**[Falso negativo silencioso] HP de membro distante congela?**~~ **RESOLVIDO 2026-08-24 (teste do usuário): atualiza ao vivo.**
- ~~**[Falso positivo] Fora de alcance parece morte?**~~ **RESOLVIDO 2026-08-24 (teste do usuário): distância não altera a barra.**
- ~~**[Aberto — nomeação de eventos]** compactação da party window~~ **MITIGADO POR CONSTRUÇÃO**: a identidade passou a vir da IMAGEM do nome, não da posição da linha (quick task `identidade-por-imagem-do-nome`). Compactar deixou de importar para a nomeação — o nome segue a assinatura visual. Coberto por `tests/test_party_estavel.py:141` (Kaus sai, as de baixo compactam) e verificado ao vivo: saída real detectada com o nome certo.
- ~~**[Aberto] Morte de membro nunca testada contra uma morte real**~~ **RESOLVIDO EM CAMPO 2026-08-24, sessão 13:21-13:42**: 12 eventos de morte/ressurreição num combate real, com HP em gradiente (J4guar 0%, Kaus caindo a 0%, TioMad 72%, Korzis 100% no mesmo frame — assinatura de luta ao vivo, não de tela parada). Nomes corretos e durações plausíveis (`KAUS MORREU 13:39:56` -> `KAUS FOI RESSUSCITADO (ficou 16s morto) 13:40:12`). Os 4 membros morreram e ressuscitaram ao menos uma vez. **Rodou em modo console** — o `outbox.jsonl` só começa às 16:44.
- ~~**[Aberto — limiar de cor]** O matiz muda com o nível de HP?~~ **RESOLVIDO POR OBSERVAÇÃO**: `logs/scanner.log` tem leituras em toda a faixa (0%, 2%, 22%, 32%, 42-56%, 63%, 68%, 72-82%, 88%, 99%, 100%). A calibração lê o gradiente inteiro, não só os extremos.

- ~~**[ABERTO — o mais grave] Cegueira recorrente e longa**~~ **CAUSA ENCONTRADA E TRATADA 2026-08-24 (Fase 5)**: era o SERVIDOR EM MANUTENÇÃO. Os prints do usuário mostram "Server Maintence 00 minutes 00 seconds", "You cannot use this item because the server will restart in a few minutes" e o diálogo "You have been disconnected from the server.<7>". Os 90 s e os 5 min de silêncio eram o cliente caindo. O scanner agora reconhece os dois estados e avisa com o motivo. **A cegueira não era defeito de calibração** — era o jogo fora do ar, e o produto simplesmente não sabia dizer isso.

  Detalhe original, mantido para histórico:

- **[histórico] Cegueira recorrente e longa.** O scanner passa períodos longos sem conseguir ler a party window, e está piorando dentro da mesma sessão:

      18:19:50-18:21:19   90 s sem visão (a barra própria também lendo 0%)
      18:35               "Scanner sem visao da party ha 5min" (registrado no outbox)

  O aviso de cegueira longa FUNCIONA — o produto avisa em vez de calar. Mas cego é cego: nesse período uma morte real não é detectada, que é exatamente o pior modo de falha declarado no roadmap ("morrer calado enquanto a party acha que está coberta"). As correções de hoje impedem que a cegueira vire alarme falso; elas não impedem a cegueira.

  **Hipóteses não testadas**: janela do jogo arrastada ou redimensionada desde a calibração; algo cobrindo a tela; a região calibrada pegando uma posição que não se sustenta. O próprio scanner já emite o aviso apontando para isso.

  **Teste**: comparar `calibration.json` com a posição atual da janela e gravar frames durante uma cegueira.

## Pending Todos

| Severidade | Todo | Área |
|---|---|---|
| minor | [Medir o template do diálogo contra gameplay normal](todos/pending/2026-08-24-medir-o-template-do-dialogo-contra-gameplay-normal.md) | testing |

## Quick Tasks Completed

| Data | Tarefa | Resultado |
|------|--------|-----------|
| 2026-08-25 | moldura do aviso no WhatsApp | O aviso de agenda passou a sair no celular como BLOCO — borda de asteriscos, recuo de dois espaços e carimbo `[HH:MM]` do envio à direita —, o mesmo que já aparecia no console. A geometria virou `console.moldurar()`, pura e sem ANSI, usada pelos dois destinos: uma conta só, então as bordas não divergem. Moldurado no despacho e cru em `resultado.avisos`, senão o console poria bloco dentro de bloco (`876a8e1`). |
| 2026-08-25 | [controle-de-loot-do-solo-boss](quick/260825-cou-controle-de-loot-do-solo-boss-via-comand/260825-cou-SUMMARY.md) | Controle de loot do Solo Boss pelo WhatsApp: `.loot-<nick>` designa quem pega o próximo loot (o aviso de antecedência sai com "Loot: X"), `.<nick>` responde quantos loots o char já pegou e o último horário, e o registro em `.loot/` é durável e à prova de duas instâncias. Consumo automático no horário do boss. |
| 2026-08-25 | TvT das 19:30 | O usuário adicionou um TvT às 19:30 no `config.toml`; os testes da agenda real passaram a conhecê-lo. Config e teste no mesmo commit (`42f3ed3`) — separados, um clone novo teria testes esperando o horário e um config sem ele. Sem colisão com o Prime. |
| 2026-08-25 | [hora-certa-do-servidor](quick/260825-c6g-hora-certa-do-servidor-nao-depender-do-r/260825-c6g-SUMMARY.md) | A agenda parou de perguntar as horas ao Windows. A hora vem do cabeçalho `Date` do Chatwoot, ancorada uma vez e contada pelo monotônico daí em diante — imune ao relógio que desajusta no dual boot (Linux grava o RTC em UTC, Windows lê como local). Sem rede, cai no relógio local e avisa alto. Zero dependência nova. |
| 2026-08-25 | [calibrar-a-imagem-de-conferencia-nao-era](quick/260825-bmw-calibrar-a-imagem-de-conferencia-nao-era/260825-bmw-SUMMARY.md) | A imagem de conferência não era substituída quando o arquivo estava travado (visualizador de fotos aberto): `cv2.imwrite` retornava `False` em silêncio e o calibrador anunciava a imagem VELHA. Agora grava com outro nome, diz o caminho completo e o horário, e cala a legenda quando não gravou nada. |
| 2026-08-24 | [modo-solo-explicito](quick/20260824-modo-solo-explicito/SUMMARY.md) | Modo solo: vigia só o próprio personagem e para de reclamar de party ausente. `--solo`, ou `.solo`/`.party` pelo WhatsApp. A agenda continua igual. |
| 2026-08-24 | [comandos-so-do-meu-numero](quick/20260824-comandos-so-do-meu-numero/SUMMARY.md) | Comandos do WhatsApp travados por telefone (últimos 8 dígitos, por causa do nono dígito brasileiro) e por etiqueta do Chatwoot. Antes qualquer um da conversa mandava no scanner. |
| 2026-08-24 | [identidade-por-imagem-do-nome](quick/20260824-identidade-por-imagem-do-nome/SUMMARY.md) | O nome no alerta vem de reconhecer a IMAGEM do nome na tela, não da posição da linha. Margem medida de 0.546 (mesmo nome 1.000, outros máx 0.454). Resolve o alerta sair com o nome errado quando a ordem da party muda. |

## Próximos passos

1. **Fechar a última milha** — uma morte real com a entrega LIGADA. Detecção (13:39) e entrega (18:17) já foram validadas em campo, mas nunca na mesma sessão. É o único critério do milestone que nenhuma evidência cobre.
3. **Confirmar em farm que os alarmes falsos acabaram** — reiniciar com as correções de hoje e farmar uma sessão inteira sem evento espúrio.

## Session Continuity

Last session: 2026-08-24
Stopped at: Três alarmes falsos corrigidos (arranque inventando entrada, cegueira
lida como saída de party, arranque cego lido como entrada em party). 226 testes.
Commits 589ac84 e 7bb43f0. Sessão em `.planning/debug/alarme-falso-no-arranque.md`.
**O bot precisa ser reiniciado para carregar as correções.**
Resume file: None
