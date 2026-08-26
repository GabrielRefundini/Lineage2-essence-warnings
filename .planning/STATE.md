---
gsd_state_version: 1.0
current_phase: 10
current_phase_name: Lista de presenca do Solo Boss pelo WhatsApp
status: phase-10-implemented-pending-field-validation
stopped_at: "Fase 10 implementada e verificada offline (1052 testes); falta validacao em campo no WhatsApp"
last_updated: "2026-08-26T14:48:51.328Z"
last_activity: 2026-08-26
last_activity_desc: Phase 10 execution started
state_head: bf00d63b89a446cb01dc356c6b65746599df2347
progress:
  total_phases: 10
  completed_phases: 0
  total_plans: 9
  completed_plans: 2
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-24)

**Core value:** Quando alguém da party morre ou sai da PT, a galera fica sabendo no WhatsApp em segundos — mesmo quem está AFK.
**Current focus:** Phase 10 — Lista de presenca do Solo Boss pelo WhatsApp

## Current Position

Phase: 10 (Lista de presenca do Solo Boss pelo WhatsApp) — EXECUTING
Status: Executing Phase 10
Last activity: 2026-08-26 — Phase 10 execution started

Progress: [██████████] 100% (9 de 9 fases)

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

### Roadmap Evolution

- Phase 10 planejada (2026-08-26): 6 planos em 6 ondas sequenciais, branch `feat/solo-boss-join`. 15 requisitos `PRES-*` derivados em `## v3 Requirements`. Plan-checker: 0 blocker, 5 warning, todos aplicados.

- Phase 10 added (2026-08-26): Lista de presenca do Solo Boss pelo WhatsApp — aviso 1h50 antes, `.join`/`.leave` no privado, autorizacao por etiqueta `CP` do Chatwoot, lista fechada no horario alimentando o revezamento de loot. Abre o milestone v3.
- Correcao de indice (2026-08-26): Phases 8 e 9 existiam em "Phase Details" mas nunca entraram na lista de fases do topo do ROADMAP. Restauradas.

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
| major | [A moldura da barra própria em terreno escuro](todos/pending/2026-08-26-a-moldura-da-barra-propria-em-terreno-escuro.md) | detection |

## Quick Tasks Completed

| Data | Tarefa | Resultado |
|------|--------|-----------|
| 2026-08-26 | [fechar-as-pendencias](quick/260826-es0-fechar-as-pendencias-template-do-dialogo/260826-es0-SUMMARY.md) | Duas pendências fechadas com dado real, não com opinião. **(1)** O template do diálogo de desconexão nunca tinha sido medido contra gameplay normal — medido em 10 frames da tela real, o pior caso (inventário e mercado abertos, que são caixas cinzas com botões) dá **0.4618** contra o limiar de 0.90: margem de 0.43. Fixture da faixa de busca presa no repo, com tripwire que quebra se `FAIXA_DO_DIALOGO` mudar sem remedir. **(2)** A divergência do ledger (`.pegou` com data sem ano) foi **julgada rodando as duas regras lado a lado**, não carimbada: as regras só divergem onde o recuo de ano irrestrito gravaria estado permanente e inalcançável em `.loot/`; implementado está certo, waived com a razão. Ledger: open_count 1 → 0. Também registrada uma ideia REFUTADA (amostrar chrome fora da região da barra própria: separa pior, 7 pontos contra 25). 780 → 783 testes. |
| 2026-08-26 | [inventario-por-cima-da-propria-barra](quick/260826-dxm-inventario-por-cima-da-propria-barra-vir/260826-dxm-SUMMARY.md) | **O maior falso positivo do projeto, achado por gravação ao vivo da tela do usuário.** Inventário/mercado aberto por cima da barra de vida própria fazia o scanner ler HP 0% e anunciar "YAZALAQUE MORREU" — **27 vezes** no log real, mais que todos os alertas de party somados. `barra_propria_legivel` usava só desvio-padrão de cinza, e a grade do inventário passava. Medido em 45 amostras livres + 9 cobertas: o desvio-padrão **não separa** (livre 34.8-36.2, coberta 17.4-36.5, sobrepostas); o **brilho da moldura separa limpo** (livre 73.7-86.4, coberta 28.0-48.9). Portão novo em série com o antigo, limiar 60. **Polaridade INVERTIDA** em relação a `_bordas_da_barra_intactas` da party (lá se rejeita borda clara demais, aqui moldura escura demais) — documentado no código porque é o detalhe mais fácil de reabrir por engano. Morte real preservada e provada: a barra quase vazia real lê 0% e continua legível. 758 → 780 testes. |
| 2026-08-25 | [comando-help](quick/260825-t1n-comando-help-listando-todos-os-comandos-/260825-t1n-SUMMARY.md) | `.help` (e `.ajuda`, `.comandos`, `.?`) responde com **a lista de todos os comandos** direto no WhatsApp — e a lista **não é escrita à mão**: ela é derivada de uma tabela chaveada pelo enum `Comando`, com um **tripwire** (`set(_AJUDA) == set(Comando)`) que quebra a suíte no dia em que alguém acrescentar um comando sem documentá-lo. O tripwire foi provado por **mutação** — um membro descartável no enum fez o teste falhar dizendo o nome dele. A tabela é chaveada pelo ENUM e não pelo `_VOCABULARIO` porque os cinco comandos dinâmicos (`.loot-<nick>`, `.<nick>`, `.corrigir-`, `.pegou`) não moram no vocabulário. Cada sintaxe anunciada volta pelo `comandos_novos` REAL, com as cinco travas ligadas, como o comando que a ajuda promete. Pegou um defeito de passagem: `destacar` moldurava a resposta no log e a conta de largura de `moldurar` roda sobre a string inteira — as dezenove linhas sairiam no `scanner.log` com uma borda de **725 caracteres** (medido). Resposta só na conversa de origem, sem portão novo (as cinco travas já bastam). 730 → 746 testes. `.solo` e `.party` finalmente entraram na tabela do README — o mesmo envelhecimento que o tripwire agora previne do lado do bot. |
| 2026-08-25 | [corrigir-o-ocr-contra-a-fonte-real](quick/260825-psq-corrigir-o-ocr-de-manutencao-contra-a-fo/260825-psq-SUMMARY.md) | **O aviso de manutenção entregue horas antes estava quebrado contra a fonte real do jogo.** Medido no screenshot real: o OCR lia o banner mas embaralhava "minutes", e o parser concluía **26 segundos** onde faltavam **40 minutos e 26 segundos** — erro plausível, e o consenso temporal não pegava, porque duas leituras do mesmo método concordam no mesmo erro sistemático. Correções: conversão para cinza; **guarda estrutural** (unidade de minutos presente sem número extraível ⇒ leitura descartada, nunca "só os segundos"); tolerância às formas embaralhadas reais (`40ninutes`, `nin es`); e **acordo entre duas escalas** (2× detecção + 3× conferência) sobre o mesmo frame, que é o que pega erro de método. O screenshot virou fixture no repo — única amostra da fonte do jogo. 683 → 730 testes. Lição: a medição de escala do plano foi REFUTADA na execução (1× não lê os dígitos); o executor parou no checkpoint em vez de assumir, senão o recurso gravaria desacordo a cada 5 s e nunca avisaria. |
| 2026-08-25 | [pegou-horario-nick](quick/260825-pik-adicionar-comando-pegou-horario-nick-par/260825-pik-SUMMARY.md) | `.pegou 18:00 Korzis` registra quem pegou o loot de um Solo Boss que **já passou**, mesmo quando ninguém tinha marcado nada — o caso que era impossível por construção, porque um `pegou_*` só nascia de designação prévia e o `.corrigir` só alcança o registro mais recente. O horário digitado é **encaixado** numa ocorrência real da agenda (tolerância 30 min) e o registro usa o horário do boss: `18h20` grava o das 18:00, e `19:00` — ambíguo entre 18:00 e 20:00 — recusa e diz quais horários existem, porque registro órfão numa pasta sem poda é permanente. Sem data, resolve para a ocorrência mais recente que já passou (às 2h, "18:00" é ontem) e a resposta **sempre diz o dia** de volta. As quatro linhas que podiam destruir dado foram conferidas por MUTAÇÃO; uma delas sobreviveu e virou teste novo (o boss que ainda não nasceu não pode ser encaixado). 683 → 715 testes. |
| 2026-08-25 | [aviso-de-manutencao-do-servidor](quick/260825-onz-aviso-de-manutencao-do-servidor-lendo-o-/260825-onz-SUMMARY.md) | O scanner passou a ler o banner "Server Maintence" do jogo por OCR do Windows (`winrt-Windows.Media.Ocr`, zero instalador) e avisar o grupo duas vezes: ao aparecer o anúncio, com o tempo como está na tela, e quando faltam 5 minutos. **Âncora no relógio**: a contagem é lida da tela uma vez e o resto sai do relógio ancorado, então o aviso de 5 min sobrevive a cegueira, alt-tab ou banner coberto. **Consenso de duas leituras** antes de anunciar, senão um dígito comido pelo OCR anunciaria "faltam 4 minutos" quando faltam 40. Sem os bindings, o recurso se desliga e o arranque avisa alto — nunca derruba o scanner. 598 → 683 testes. Risco aberto: a precisão do OCR na FONTE DO JOGO não foi provada; `--testar-manutencao` existe para o usuário validar sozinho na próxima manutenção real. |
| 2026-08-25 | [corrigir-um-loot-ja-consumado](quick/260825-ehc-corrigir-um-loot-ja-consumado-com-corrig/260825-ehc-SUMMARY.md) | `.corrigir-<nick>` reatribui o loot JÁ consumado — o boss passou no nome do designado, mas quem pegou foi outro. Toca só o registro MAIS RECENTE, e a resposta nomeia o que mudou ("de hoje as 10:00, do Tiomad para o Kaus") porque esse texto é a única rede contra corrigir o registro errado. Duas linhas podiam destruir dado e foram conferidas por MUTAÇÃO: criar-antes-de-apagar (o inverso perde o loot em silêncio) e a guarda do mesmo apelido (sem ela, corrigir para o próprio dono apagava o único registro e ainda respondia sucesso). 581 → 598 testes. Limitação aceita: o dono antigo sai com caixa do slug ("Tiomad"), porque o nome digitado não sobrevive ao consumo. |
| 2026-08-25 | moldura do aviso no WhatsApp | O aviso de agenda passou a sair no celular como BLOCO — borda de asteriscos, recuo de dois espaços e carimbo `[HH:MM]` do envio à direita —, o mesmo que já aparecia no console. A geometria virou `console.moldurar()`, pura e sem ANSI, usada pelos dois destinos: uma conta só, então as bordas não divergem. Moldurado no despacho e cru em `resultado.avisos`, senão o console poria bloco dentro de bloco (`876a8e1`). |
| 2026-08-25 | [cancelar-a-designacao-de-loot](quick/260825-dwp-cancelar-a-designacao-de-loot-do-solo-bo/260825-dwp-SUMMARY.md) | O `.loot-` passou a APAGAR a designação do próximo Solo Boss — o registro volta a "sem dono" pelo WhatsApp e o aviso de antecedência sai sem a linha "Loot:". Valem também `.loot-cancelar/ninguem/nenhum/limpar`; `.loot` sozinho continua sendo nada, porque comando sem argumento não pode ser destrutivo. Cancelar toca só a VEZ: os `pegou_*` e `nick_*` ficam intactos. Pegou um bug real de caminho: `.loot cancelar` **designava** um personagem chamado "cancelar". 566 → 581 testes. |
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

Last session: 2026-08-26T00:14:35.713Z
Stopped at: Quick 260825-t1n concluida: o .help responde com a lista de comandos, derivada do enum
lida como saída de party, arranque cego lido como entrada em party). 226 testes.
Commits 589ac84 e 7bb43f0. Sessão em `.planning/debug/resolved/alarme-falso-no-arranque.md`.
**O bot precisa ser reiniciado para carregar as correções.**
Resume file: None

## Decisions

- [Phase 4]: [loot]: O horario do `.pegou` e ENCAIXADO numa ocorrencia real do Solo Boss (tolerancia 30 min) e o registro usa o horario da ocorrencia, nunca o digitado. Sem boss por perto o comando recusa e lista os horarios — a pasta .loot/ nunca e podada, entao um registro orfao seria permanente e inalcancavel.
- [Phase 4]: [loot]: Data sem ano resolve para a leitura de calendario MAIS PROXIMA de agora, e so entao precisa ter passado. Em janeiro "30/12" e dezembro passado; em agosto o mesmo "30/12" recusa em vez de gravar oito meses atras. Recuar sempre para o ano anterior gravaria estado permanente por um dedo escorregado.
- [Phase 9]: [comandos]: O texto da ajuda e DERIVADO de uma tabela chaveada pelo enum Comando, com tripwire set(_AJUDA) == set(Comando). Cinco comandos nasceram em um dia; ajuda escrita a mao envelheceria antes do fim da semana, e ajuda desatualizada ensina sintaxe que nao funciona. O tripwire foi provado por MUTACAO, nao por leitura.
- [Phase 9]: [console]: Resposta com quebra de linha nunca e moldurada. moldurar faz max(LARGURA, len(miolo) + len(carimbo)) sobre a string INTEIRA, entao a ajuda de dezenove linhas sairia no log com uma borda de 725 caracteres — medido. A regra vale pela FORMA do texto, nao pelo comando de origem.

## Deferred Verification

| Phase | State | Resume |
|-------|-------|--------|
| 10 | verification_deferred_human | /gsd-verify-work 10 |

A Fase 10 passou em 40/40 must-haves por execucao, com o jogo fechado e sem
rede. O que ficou aberto sao 6 itens que exigem a ponte Baileys real: o ciclo
`.join`/`.leave` no WhatsApp, o silencio com lista vazia, a recusa do
`.corrigir` vindo de um membro, e a legibilidade do bloco `[[membro]]` para
leigo. Ver `.planning/phases/10-.../10-UAT.md`.

Branch: `feat/solo-boss-join` (nao mesclada — aguarda validacao em campo e o
fim do trabalho da outra instancia no master).
