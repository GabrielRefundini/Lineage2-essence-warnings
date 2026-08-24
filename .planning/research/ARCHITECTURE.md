# Architecture Research

**Domain:** Monitor local de tela em tempo real → detecção de eventos → alerta externo (screen-scanning event detection & alerting)
**Researched:** 2026-08-24
**Confidence:** MEDIUM (padrão de pipeline é convergente e bem estabelecido; detalhes de API do Chatwoot e semântica do dxcam verificados contra documentação primária; especificidades da party window do L2 XM Essence não verificadas — dependem de captura real)

---

## Standard Architecture

O domínio tem um pipeline canônico. Todo scanner de tela que detecta eventos e dispara alertas converge para a mesma forma, com nomes diferentes:

```
     FONTE                    DETECÇÃO (puro)                 DECISÃO           ENTREGA
┌──────────────┐   Frame   ┌──────────────────┐  Observation ┌──────────┐ Event ┌───────────┐
│ FrameSource  │──────────▶│  Vision/Extract  │─────────────▶│ Tracker  │──────▶│ Dispatcher│
│  (port)      │           │  (funções puras) │              │ (FSM)    │  queue│  (thread) │
└──────┬───────┘           └────────┬─────────┘              └────┬─────┘       └─────┬─────┘
       │                            │                             │                   │
       │ adapters                   │ lê                          │ consulta          │ port
       ▼                            ▼                             ▼                   ▼
┌──────────────┐           ┌──────────────────┐            ┌──────────┐        ┌───────────┐
│ dxcam / mss  │           │  calibration.json│            │  Roster  │        │ Chatwoot  │
│ replay(disk) │           │  (read-only)     │            │ Resolver │        │ Console   │
│ synthetic    │           └──────────────────┘            │  (OCR)   │        │ Recording │
└──────────────┘                                           └──────────┘        └───────────┘
```

Em camadas, com a regra de dependência apontando para dentro:

```
┌─────────────────────────────────────────────────────────────┐
│                    APP / RUNTIME (impuro)                    │
│   runner.py (loop + clock real) · console.py · wiring.py     │
├─────────────────────────────────────────────────────────────┤
│                    ADAPTERS (I/O, laterais)                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │ capture │  │ recorder│  │  ocr    │  │ notify  │         │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘         │
├───────┴────────────┴────────────┴────────────┴──────────────┤
│                    CORE (puro, sem I/O, sem relógio)         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  vision.extract · core.roster · core.tracker (FSM)   │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                    CONTRACTS (dataclasses frozen)            │
│  ┌──────────┐  ┌──────────────┐  ┌─────────┐  ┌─────────┐   │
│  │  Frame   │  │ Observation  │  │Snapshot │  │  Event  │   │
│  └──────────┘  └──────────────┘  └─────────┘  └─────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**A regra que sustenta tudo:** o CORE não importa `time`, não importa `requests`, não importa `cv2.imshow`, não abre arquivo. Recebe `Frame` + `now: float` e devolve `Event`s. Todo o resto é periferia substituível. É isso que torna o sistema testável sem o jogo rodando.

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **FrameSource** (port) | Entregar um `Frame(image, ts, seq)` da região configurada. Nada mais. | Protocol/ABC com `grab() -> Frame \| None`. Adapters: `DxcamSource`, `MssSource`, `ReplaySource`, `SyntheticSource` |
| **Recorder** | Gravar frames + observações em disco para virar fixture. Ligado por flag. | Escreve `session/NNNNNN.png` + `observations.jsonl` |
| **Calibration** | Artefato de dados: bboxes das regiões, thresholds HSV, geometria da tela. Produzido por um passo separado, **só lido** em runtime. | `calibration.json` versionado + dataclass de carga com validação |
| **Vision/Extract** | `(Frame, Calibration) -> Observation`. Recorte, máscara HSV, razão de preenchimento das barras, presença de linha, âncora de UI. Puro. | numpy + OpenCV, funções livres |
| **UI Anchor** | Responder "a party window está renderizada?" por um sinal **independente** dos membros. | Template matching ou assinatura de cor de um elemento estático da moldura |
| **RosterResolver** | Mapear `slot_index -> nome`. Redetecta quando a composição muda (linhas compactam). | Lista de nomes do config + OCR sob demanda |
| **Tracker (FSM)** | Estado por membro + estado global BLIND, contadores de debounce, cooldown/dedupe. Emite `Event`. Puro, relógio injetado. | `(state, snapshot, now) -> (state', [Event])` |
| **Dispatcher** | Drenar a fila de eventos numa thread própria, formatar mensagem, chamar o Notifier com retry/backoff, gravar outbox. | `queue.Queue` + daemon thread |
| **Notifier** (port) | Entregar uma mensagem. | `ChatwootNotifier` (HTTP POST), `ConsoleNotifier` (dry-run), `RecordingNotifier` (testes) |
| **Runner** | Wiring, loop, relógio real, pacing, shutdown limpo, render do console. | `while not stop: tick()` |
| **Settings** | Config em arquivo, segredo em env. Valida na partida e falha alto. | YAML/JSON + `os.environ` + `python-dotenv` |

---

## Recommended Project Structure

```
l2scanner/
├── __main__.py               # entrypoint: python -m l2scanner
├── contracts.py              # Frame, Observation, PartySnapshot, PartyEvent, MemberState
├── app/
│   ├── runner.py             # loop principal, pacing, shutdown
│   ├── wiring.py             # constrói o grafo de objetos a partir do Settings
│   └── console.py            # tabela de status ao vivo (rich)
├── config/
│   ├── settings.py           # config.yaml + env; validação e fail-fast
│   └── calibration.py        # carga/validação de calibration.json
├── capture/
│   ├── port.py               # Protocol FrameSource
│   ├── dxcam_source.py       # adapter primário (Desktop Duplication)
│   ├── mss_source.py         # fallback portátil
│   ├── replay_source.py      # lê PNGs de uma pasta — testes e replay
│   ├── synthetic_source.py   # gera frames desenhados — testes de borda
│   └── recorder.py           # --record: dump de frames + observações
├── vision/
│   ├── color.py              # conversão HSV, máscaras, razão de barra
│   ├── anchor.py             # a party window está visível? (sinal independente)
│   ├── extract.py            # Frame + Calibration -> Observation  [PURO]
│   └── ocr.py                # Tesseract; chamado raramente, sob demanda
├── core/
│   ├── clock.py              # Clock protocol: RealClock / FakeClock
│   ├── roster.py             # slot_index -> nome; reconciliação de reshuffle
│   ├── tracker.py            # a máquina de estados  [PURO]
│   └── rules.py              # thresholds e contadores de debounce (dados)
├── notify/
│   ├── port.py               # Protocol Notifier
│   ├── chatwoot.py           # POST + retry/backoff
│   ├── console.py            # dry-run
│   ├── outbox.py             # JSONL append-only, durabilidade + auditoria
│   ├── format.py             # Event -> texto da mensagem (pt-BR)  [PURO]
│   └── dispatcher.py         # fila + thread + rate-limit guard
└── tools/
    ├── calibrate.py          # passo de setup: gera calibration.json
    └── replay.py             # roda o pipeline sobre uma sessão gravada

tests/
├── unit/
│   ├── test_tracker.py       # o coração: FSM sem imagem nenhuma
│   ├── test_color.py         # matemática das barras em frames sintéticos
│   ├── test_roster.py        # reshuffle de linhas
│   └── test_chatwoot.py      # retry/no-retry com requests-mock
├── golden/
│   └── test_extract.py       # frames reais -> Observation esperada
└── fixtures/
    ├── frames/               # PNGs individuais + .expected.json ao lado
    └── sessions/             # sessões gravadas inteiras + events.expected.json

config.example.yaml           # commitado
config.yaml                   # gitignored
.env.example                  # commitado (CHATWOOT_API_TOKEN=)
.env                          # gitignored
calibration.json              # gitignored (específico da máquina)
```

### Structure Rationale

- **`contracts.py` na raiz, sem dependências:** todos os módulos importam daqui e ninguém importa de volta. Elimina import circular por construção e deixa o formato dos dados óbvio para quem chega no projeto.
- **`capture/` como port + adapters:** captura é a parte mais frágil e mais provável de mudar (dxcam → Windows Graphics Capture quando quiser janela em background). Isolar agora custa 20 linhas; isolar depois custa refatorar tudo.
- **`vision/` separado de `core/`:** `vision` entende pixels e não entende party; `core` entende party e nunca vê um pixel. Se um dia a fonte do sinal mudar (OCR do chat, por exemplo), o `core` não muda.
- **`core/` puro:** é onde estão as regras de negócio de verdade (debounce, cego, cooldown) e é onde os bugs vão morar. Puro = testável exaustivamente em milissegundos.
- **`notify/` como port:** permite `--dry-run` real (troca de adapter, não `if` espalhado) e testes que não tocam a rede.
- **`tools/` fora do runtime:** calibração e replay são entrypoints separados. O runtime nunca escreve calibração; só lê.
- **`tests/fixtures/sessions/` versionado:** as gravações de sessões reais são o ativo mais valioso do projeto. Uma morte gravada é irreprodutível sob demanda — trate como código.

---

## Architectural Patterns

### Pattern 1: Núcleo puro com relógio injetado ("functional core, imperative shell")

**What:** O tracker não chama `time.time()` nem `time.sleep()`. Recebe `now: float` como argumento e devolve `(novo_estado, eventos)`. O runner é quem tem o relógio.

**When to use:** Sempre que houver debounce, histerese, cooldown ou timeout — ou seja, aqui.

**Trade-offs:** Custa um parâmetro extra em cada chamada e disciplina para não "pegar o tempo ali rapidinho". Em troca, você testa 30 segundos de debounce em 0,2 ms e de forma determinística. Sem isso, testar "morte confirma após 3 capturas" vira `sleep(3)` no teste — lento, flaky e ninguém escreve o segundo caso.

**Example:**
```python
# core/tracker.py — nenhum import de time, requests ou cv2
@dataclass(frozen=True)
class TrackerState:
    members: Mapping[str, MemberState]
    blind_since: float | None
    reacquire_until: float | None

def step(state: TrackerState, snap: PartySnapshot, now: float,
         rules: Rules) -> tuple[TrackerState, list[PartyEvent]]:
    ...

# app/runner.py — aqui sim existe relógio
now = clock.now()
state, events = step(state, snapshot, now, rules)
for e in events:
    dispatcher.submit(e)
```

O mesmo vale para `Clock` no dispatcher (backoff) — `FakeClock` faz os testes de retry rodarem instantaneamente.

### Pattern 2: Cegueira como gate global independente, não derivado dos membros

**What:** `Observation.ui_visible` vem de uma **âncora** — um elemento estático da moldura da party window (borda, título, ícone fixo) verificado por template matching ou assinatura de cor. Nunca de "nenhum membro tem MP".

**When to use:** Sempre. Este é o ponto onde este tipo de projeto mais erra.

**Trade-offs:** Exige escolher e calibrar uma âncora (mais um campo no `calibration.json`). Sem isso, um **wipe da party inteira** é pixel-a-pixel indistinguível de um alt-tab — e o sistema fica silencioso exatamente no evento mais importante que ele existe para reportar.

Semântica do gate — três estados globais:

| Estado global | Condição | Efeito nas FSMs por membro |
|---|---|---|
| `TRACKING` | âncora presente | transições normais, eventos emitidos |
| `BLIND` | âncora ausente por ≥ `N_blind` obs | contadores **congelados** (não zerados), zero eventos |
| `REACQUIRE` | âncora voltou, por `T_grace` (~2-3 s) | observações consumidas, **nenhuma** transição dispara |

`REACQUIRE` existe porque a UI reaparece parcialmente desenhada saindo de loading/alt-tab: por 1-2 frames as barras podem ler zero. Sem a janela de graça, todo alt-tab gera 4 falsos "morreu".

**Congelar em vez de zerar** os contadores importa: se alguém morre e você alt-tabbeia 200 ms depois, o contador preservado faz o alerta sair ao voltar, em vez de o evento sumir.

**Example:**
```python
def step(state, snap, now, rules):
    if not snap.ui_visible:
        return _enter_or_stay_blind(state, now, rules), []   # congela, não emite
    if state.blind_since is not None:
        return _start_reacquire(state, now, rules), []       # graça
    if state.reacquire_until and now < state.reacquire_until:
        return state, []                                     # consome, não transita
    return _advance_members(state, snap, now, rules)
```

### Pattern 3: Identidade por nome, não por índice de slot

**What:** Um `RosterResolver` fica entre `Observation` (indexada por slot) e o tracker (chaveado por nome), produzindo um `PartySnapshot` name-keyed.

**When to use:** Obrigatório em qualquer UI que **compacta linhas** quando um item some — que é o caso da party window do L2.

**Trade-offs:** Adiciona um componente e um momento de ambiguidade (quando 4 linhas viram 3, quem saiu?). Sem ele, o bug é silencioso e grave: o membro do slot 3 vira slot 2, e a morte do Korzis é anunciada como morte do Kaus.

Estratégia recomendada, em duas camadas para desacoplar de OCR:
1. **Baseline por config:** o usuário lista os nomes da party em ordem no `config.yaml` no início da farm. Mapeamento posicional imediato, zero OCR, zero flake.
2. **Reconciliação sob demanda:** quando `slot_count` muda ou o layout desloca, dispara **uma** passada de OCR nas linhas presentes para re-ancorar o mapa. Só então o evento `left` é emitido, já com o nome certo.

Isso mantém o OCR fora do caminho quente e fora do caminho de correção — ele vira uma melhoria de ergonomia, não um pré-requisito.

**Example:**
```python
# core/roster.py
def resolve(obs: Observation, roster: Roster,
            ocr: Callable[[Frame, int], str] | None) -> tuple[PartySnapshot, Roster]:
    present = [s.index for s in obs.slots if s.frame_present]
    if present == roster.known_slots:
        return roster.apply(obs), roster          # caminho comum: nada muda
    roster = roster.reconcile(obs, ocr)           # raro: re-ancora (OCR aqui)
    return roster.apply(obs), roster
```

### Pattern 4: Fila one-way entre detecção e entrega

**What:** O tracker faz `queue.put_nowait(event)`. Uma thread dispatcher drena, formata e faz o POST. O loop de detecção nunca espera pela rede.

**When to use:** Sempre que a entrega for I/O de rede com latência e retry — ou seja, aqui.

**Trade-offs:** Uma thread e uma fila a mais para pensar em shutdown. Em troca: um timeout de 30 s do Chatwoot não congela a detecção, e você não perde a próxima morte porque estava esperando um POST. Chamada direta parece mais simples até o primeiro blip de rede.

Detalhes que importam:
- `Queue(maxsize=100)` e `put_nowait` com `except queue.Full: log + drop`. **Nunca bloquear o produtor** — melhor perder um alerta do que travar a detecção.
- Escreva no **outbox JSONL antes** de tentar o POST. Dá durabilidade contra crash, log de auditoria e oráculo de teste de graça (uma linha de código).
- Sentinela `None` na fila para shutdown limpo; `join()` com timeout no `finally`.

**Example:**
```python
# notify/dispatcher.py
def _worker(self):
    while (item := self.q.get()) is not None:
        self.outbox.append(item)                  # durável primeiro
        try:
            self._send_with_retry(item)
            self.outbox.mark_sent(item.id)
        except Exception as exc:
            log.error("alerta não entregue: %s", exc)  # fica no outbox
        finally:
            self.q.task_done()
```

### Pattern 5: Retry com backoff só nos erros que valem retry

**What:** 3 tentativas, backoff exponencial com jitter (1 s / 2 s / 4 s ± jitter), `timeout=(3, 10)` no `requests`.

**Retry:** `ConnectionError`, `Timeout`, HTTP 5xx, HTTP 429 (respeitando `Retry-After`).
**Não retry:** 4xx em geral. Token inválido ou `conversation_id` errado não melhoram na terceira tentativa — logue alto uma vez, marque o notifier como degradado e mostre no console.

**Trade-offs:** Retry cego em 4xx queima tempo e esconde erro de configuração. Sem jitter, N eventos simultâneos (wipe) reagendam no mesmo instante.

**Example:**
```python
RETRYABLE = (requests.ConnectionError, requests.Timeout)

@retry(retry=retry_if_exception_type(RETRYABLE) | retry_if_result(_is_5xx),
       wait=wait_exponential_jitter(initial=1, max=8),
       stop=stop_after_attempt(3), reraise=True)
def _post(self, payload): ...
```

### Pattern 6: Calibração como artefato de dados, produzida fora do runtime

**What:** `python -m l2scanner.tools.calibrate` abre um **frame gravado** (não o jogo ao vivo), o usuário marca as regiões, a ferramenta amostra as cores das barras e escreve `calibration.json`. O runtime só lê.

**Trade-offs:** Dois entrypoints em vez de um. Em troca, calibrar deixa de exigir estar logado no jogo, vira reproduzível e revisável, e as coordenadas saem do código-fonte.

O artefato precisa carregar o contexto em que foi feito, e o runtime precisa recusar rodar fora dele:
```json
{
  "schema_version": 1,
  "created_at": "2026-08-24T11:00:00Z",
  "source_frame": "fixtures/frames/calib-base.png",
  "screen": { "monitor_index": 2, "width": 1718, "height": 1360, "origin_x": 1713 },
  "anchor": { "bbox": [12, 8, 40, 20], "template": "anchor.png", "min_score": 0.85 },
  "party": {
    "bbox": [10, 30, 230, 190],
    "row_height": 38,
    "slots": 4,
    "hp_bar":  { "dx": 46, "dy": 14, "w": 120, "h": 6 },
    "mp_bar":  { "dx": 46, "dy": 22, "w": 120, "h": 4 },
    "name":    { "dx": 46, "dy": 0,  "w": 120, "h": 12 }
  },
  "self_hp": { "bbox": [820, 20, 1000, 30] },
  "hsv": {
    "hp": { "lo": [0, 120, 70],   "hi": [10, 255, 255] },
    "mp": { "lo": [100, 120, 70], "hi": [130, 255, 255] }
  }
}
```
Se a geometria atual não bater com `screen`, **falhe na partida com mensagem clara** ("resolução mudou, recalibre"). Regiões silenciosamente erradas produzem um scanner que parece funcionar e nunca alerta — o pior modo de falha possível.

### Pattern 7: Gravação como feature de primeira classe

**What:** `--record out/session-<ts>/` grava cada frame (ou cada N-ésimo) como PNG mais um `observations.jsonl` com o que a visão extraiu naquele frame.

**When to use:** Desde o primeiro dia, antes de existir qualquer lógica de detecção.

**Trade-offs:** ~50-200 KB por frame; a 1 Hz uma hora de farm gera algumas centenas de MB (PNG de região pequena é bem menor). Gerenciável com recorte da região e rotação. O custo é trivial perto do benefício.

Isto não é conveniência de debug — é **o único caminho para ter ground truth**. O usuário não consegue reproduzir uma morte sob demanda. Ele consegue farmar uma hora com gravação ligada. Aquela sessão vira fixture permanente de regressão. Sem isso, todo ajuste de threshold é chute e toda regressão só aparece em produção, no meio do farm.

---

## Data Flow

### Tick Flow (o caminho quente, ~1 Hz)

```
[t = clock.now()]
      ↓
FrameSource.grab(region)  ──────────────────────────────► Frame(image, ts, seq)
      ↓                          (adapter normaliza "sem frame novo")
Recorder.maybe_write(frame)      [opcional, flag --record]
      ↓
vision.anchor.is_visible(frame, calib)  ─────────────────► ui_visible: bool
vision.extract.observe(frame, calib)    ─────────────────► Observation
      │   por slot: frame_present, mp_present, hp_ratio, mp_ratio
      ↓
core.roster.resolve(obs, roster, ocr?)  ─────────────────► PartySnapshot (por NOME)
      ↓                                    └─ OCR só se a composição mudou
core.tracker.step(state, snapshot, now, rules)
      ↓
   state'          +          [PartyEvent, ...]
      ↓                              ↓
app.console.render(state')     dispatcher.submit(e)   ── put_nowait, nunca bloqueia
                                     ↓
                          ═══════ FRONTEIRA DE THREAD ═══════
                                     ↓
                              queue.Queue(maxsize=100)
                                     ↓
                          [dispatcher thread]
                                     ↓
                          outbox.append(e)          ── JSONL, durável, ANTES do POST
                                     ↓
                          notify.format.render(e)   ── puro: Event -> texto pt-BR
                                     ↓
                          Notifier.send(msg)        ── retry/backoff
                                     ↓
                          POST /api/v1/accounts/{id}/conversations/{cid}/messages
                                     ↓
                          outbox.mark_sent(e.id)
```

### State Flow (por membro, dentro do gate global)

```
                    ┌──────── gate global ────────┐
                    │  TRACKING / BLIND / REACQUIRE│
                    └──────────────┬───────────────┘
                                   │ só transita em TRACKING
                                   ▼
                              ┌─────────┐
                              │ UNKNOWN │
                              └────┬────┘
                    hp>0, mp ok    │
                                   ▼
   ┌───────────────────────────►┌───────┐
   │  hp_ratio > rez_eps        │ ALIVE │
   │  por N_rez obs             └───┬───┘
   │                                │
   │        hp_ratio ≤ dead_eps AND mp_present
   │        por N_death obs (≈3 @1Hz)
   │                                ▼
   │                            ┌──────┐     emite death (1x, cooldown até sair de DEAD)
   └────────────────────────────│ DEAD │
                                └───┬──┘
                                    │  frame_present == False
                                    │  por N_gone obs (≈5 s)
              (de ALIVE ou DEAD)    ▼
                                ┌──────┐     emite left  ── dispara re-OCR antes de nomear
                                │ GONE │
                                └───┬──┘
                                    │ linha reaparece com o mesmo nome
                                    └──────────► ALIVE (emite rejoin, opcional)
```

Notas de projeto embutidas no diagrama:
- **`mp_present` é o discriminador.** HP zerado **com** MP presente = morte. Linha inteira ausente = saiu. Âncora ausente = cego. Três sinais, três causas — sem isso as três colapsam numa só.
- **Cooldown mora na FSM, não no notifier.** "Um alerta por evento até ressuscitar" é propriedade de *estado* (você já está em `DEAD`, já alertou), não de entrega. O notifier fica burro.
- **Mas mantenha um rate-limit guard no dispatcher** (ex.: máx. 10 msg/min). Defesa em profundidade: se um bug de detecção oscilar, o guard impede spam no WhatsApp da party.

### Test Flow (o mesmo pipeline, periferia trocada)

```
ReplaySource(fixtures/sessions/wipe-01/)   FakeClock(step=1.0)   RecordingNotifier()
              │                                    │                     │
              └──────────────► [MESMO CORE, byte a byte] ◄───────────────┘
                                        ↓
                          assert events == expected.json
```

Nenhuma linha do `core` sabe que está num teste. É exatamente por isso que o teste tem valor.

---

## Threading Model

**Recomendação para v1: duas threads.** Nem uma, nem quatro.

| Thread | Responsabilidade | Por quê |
|---|---|---|
| **Main** | grab → extract → resolve → step → render do console | A 1-5 Hz há folga enorme; síncrono é muito mais fácil de raciocinar e depurar |
| **Dispatcher** | drenar fila → outbox → POST com retry | HTTP é o único I/O com latência imprevisível (200 ms a 30 s com retries). Não pode ficar no caminho da detecção |

Orçamento de um tick a 1 Hz (1000 ms disponíveis):

| Etapa | Custo típico | Observação |
|---|---|---|
| `grab` de região pequena | 5-15 ms | Desktop Duplication é rápido |
| crop + conversão HSV + máscara | 1-5 ms | região de ~220x160 px é trivial para numpy |
| tracker step | < 0,1 ms | aritmética de inteiros |
| render do console | 1-5 ms | |
| **OCR (Tesseract), por nome** | **50-300 ms** | **por isso não pode rodar por frame** |

Sobram ~950 ms. Não há pressão de performance nenhuma — há pressão de *correção*. Otimize para depurabilidade.

**Decisões relacionadas:**

- **Não use o modo threaded da lib de captura no v1.** `dxcam.start()` sobe uma thread própria com ring buffer, feita para 60 fps de gameplay. A 1 Hz isso só adiciona uma thread que você não controla e um buffer entre você e a realidade. Use `camera.grab(region=..., new_frame_only=False)` de forma síncrona.
- **`new_frame_only=False` não é detalhe, é correção.** Por padrão o `grab()` do dxcam retorna `None` quando nada foi renderizado desde a última captura. Uma party window parada (todo mundo full HP, ninguém se movendo) é *exatamente* esse caso. Um loop ingênuo veria `None` por minutos, não produziria observações, e os contadores de debounce nunca avançariam. O adapter tem que normalizar isso — devolver o último frame válido — e o pipeline tem que ser idempotente sobre frames repetidos. *(Verificado no README oficial do DXcam.)*
- **OCR: síncrono mas raro no v1.** Roda na partida e quando a composição muda. Se um dia precisar ser frequente, promova para uma terceira thread com fila de requisições e resultado assíncrono — mas não antes de precisar.
- **Não use asyncio.** OpenCV e as libs de captura são bloqueantes e CPU-bound; existe exatamente uma chamada de I/O de rede no sistema todo. asyncio não compra nada e custa um modelo mental inteiro.
- **Shutdown:** `signal.SIGINT` → flag `stop` → sai do loop → `queue.put(None)` → `dispatcher.join(timeout=15)` → relatório final do outbox. Ctrl+C não pode perder um alerta que já estava na fila.

---

## Configuration & Secrets

| Artefato | Conteúdo | Git |
|---|---|---|
| `config.example.yaml` | template com todos os campos e comentários | **commitado** |
| `config.yaml` | poll_hz, thresholds, contadores de debounce, nomes da party, `chatwoot: {base_url, account_id, inbox_id, conversation_id}` | **gitignored** |
| `.env.example` | `CHATWOOT_API_TOKEN=` | **commitado** |
| `.env` | o token real | **gitignored** |
| `calibration.json` | geometria e cores — específico da máquina | **gitignored** |

Regras:
- **Token só por variável de ambiente** (`os.environ["CHATWOOT_API_TOKEN"]`, com `python-dotenv` carregando `.env` como conveniência). Nunca em `config.yaml`, porque config é a coisa que as pessoas colam num fórum pedindo ajuda.
- **`.gitignore` no primeiro commit**, antes de existir um `.env`. Segredo commitado não se desfaz com `git rm`.
- **Redação em log:** o logger nunca imprime o header de auth. Ao logar erro de HTTP, logue status e corpo, não os headers.
- **Validação na partida, fail-fast:** falta token, `conversation_id` ausente, `calibration.json` incompatível com a tela → mensagem clara e saída, antes do primeiro frame. Um scanner que sobe e nunca alerta é pior que um que não sobe.
- **`--dry-run` troca o adapter**, não liga um `if`. `ConsoleNotifier` no lugar do `ChatwootNotifier`: o usuário exercita o pipeline inteiro sem mandar mensagem pra party.
- **Resolva `conversation_id` uma vez.** O caminho quente do alerta deve ser um único POST idempotente. Criar contato/conversa (`POST /contacts` → `POST /conversations`) é setup, não runtime. *(Verificado contra a API reference do Chatwoot.)*

---

## Testability Without the Game

Este é o requisito de arquitetura mais importante do projeto: **o usuário não consegue reproduzir uma morte sob demanda.** Cinco camadas, da mais rápida à mais realista:

| # | Camada | O que cobre | Custo | Precisa do jogo? |
|---|---|---|---|---|
| 1 | **Unit puro do tracker** | debounce, cego, reacquire, cooldown, dedupe, reshuffle | ms | não |
| 2 | **Frames sintéticos** | matemática de razão de barra, casos de borda (0 px, 1 px, 100%, gamma) | ms | não |
| 3 | **Golden frames** | extração real: HSV, presença, âncora | ~s | não (usa PNGs gravados) |
| 4 | **Replay de sessão** | pipeline ponta a ponta, incluindo timing | ~s | não (usa gravação) |
| 5 | **Contrato do notifier** | retry em 5xx, no-retry em 401, formatação da mensagem | ms | não |

**1. Unit do tracker — onde moram os bugs de verdade.** Sem imagem nenhuma:
```python
def test_alt_tab_durante_morte_nao_perde_o_alerta():
    s = tracker.initial(["TioMad", "Kaus"])
    s, ev = feed(s, dead("TioMad"), ticks=2)      # 2 de 3 do debounce
    assert ev == []
    s, ev = feed(s, blind(), ticks=10)            # alt-tab
    assert ev == []                                # nada emitido no escuro
    s, ev = feed(s, dead("TioMad"), ticks=5)      # volta: graça + 1 tick
    assert [e.kind for e in ev] == ["death"]      # contador foi congelado, não zerado

def test_wipe_total_nao_e_confundido_com_alt_tab():
    s = tracker.initial(["TioMad", "Kaus", "Korzis", "J4guar"])
    s, ev = feed(s, all_dead_ui_visible(), ticks=3)
    assert len(ev) == 4                            # âncora presente ⇒ 4 mortes, não cego
```
Toda regra do PROJECT.md vira um teste destes. É rápido, determinístico e cobre o que o olho não cobre olhando o jogo.

**2. Frames sintéticos:** desenhe uma party window falsa com numpy (retângulos em valores HSV conhecidos). Permite testar `hp_ratio` em 0%, 1 px, 50%, 100%, e simular o Gamma 1.16 aplicando a mesma transformação do cliente. Não substitui frames reais — cobre bordas que frames reais raramente contêm.

**3. Golden frames:** `fixtures/frames/*.png` com um `*.expected.json` irmão. Um `--record` na runtime gera os PNGs; a primeira `Observation` é revisada à mão uma vez e vira o golden. Quando o threshold mudar, o diff aparece na hora.

**4. Replay de sessão — o teste que fecha o loop.** `ReplaySource` + `FakeClock` + `RecordingNotifier` sobre uma pasta de sessão gravada, comparando com `events.expected.json`. Roda o pipeline inteiro, na ordem real, em segundos. Uma morte real gravada uma vez protege o projeto para sempre.

**5. Contrato do notifier:** `requests-mock`/`responses` — assert que 500 gera 3 tentativas, que 401 gera exatamente 1, que o corpo tem `message_type: "outgoing"`, e que o token nunca aparece no log.

**Implicação de ordem de build, e é forte:** a infraestrutura de gravação (`--record` + `ReplaySource`) tem que existir **antes** da lógica de detecção. Não é polimento. É o que transforma "acho que o threshold tá bom" em "o teste passa". Construir detecção primeiro significa iterar às cegas contra o jogo ao vivo, com um evento raro, sem repetibilidade.

---

## Suggested Build Order

| # | Componente | Entrega | Depende de | Por que nesta posição |
|---|---|---|---|---|
| 0 | Skeleton + `contracts.py` + settings | dataclasses, `.gitignore`, `.env.example`, `--dry-run` | — | Contratos primeiro fixam as fronteiras; barato e evita retrabalho |
| 1 | **Capture + Recorder** | `--record` grava PNGs de uma região | 0 | **Desbloqueia tudo.** O usuário já pode farmar gravando e capturar uma morte real enquanto o resto é construído |
| 2 | Calibrator | `calibration.json` a partir de um frame gravado | 1 | Precisa de um frame para calibrar em cima; não precisa do jogo aberto |
| 3 | Vision/extract + âncora | `Observation` a partir de frame; golden tests | 1, 2 | Primeiro ponto onde há algo a validar contra fixtures |
| 4 | **Tracker (FSM)** + console | eventos no console; suíte unitária completa | 0, 3 | O coração. Já é *útil* aqui: avisa na tela sem WhatsApp |
| 5 | Replay harness | `python -m l2scanner.tools.replay <sessão>` | 1, 3, 4 | Fecha o loop de regressão antes de adicionar rede |
| 6 | Notifier Chatwoot + dispatcher + outbox | alerta chega no WhatsApp | 4 | Baixo risco e bem documentado; ligar cedo demais só adiciona ruído à depuração da detecção |
| 7 | RosterResolver + OCR | eventos com nome em vez de "Slot 2" | 4 | Parte mais flaky; com nomes vindos do config o v1 já está correto sem OCR |
| 8 | Console rico + robustez | tabela ao vivo, reconexão, tratamento de erro | tudo | Polimento sobre base testada |

**Racional da ordem, em uma frase por decisão:**
- **Gravação antes de detecção** porque o evento alvo é raro e irreprodutível — sem ground truth você não está desenvolvendo, está adivinhando.
- **Tracker antes de notifier** porque o produto tem valor com saída no console; a rede só adiciona variáveis a depurar em paralelo com a lógica.
- **OCR por último** porque a camada de nomes do config torna a correção independente dele; OCR vira ergonomia.
- **Replay antes de rede** porque a partir daí toda mudança de threshold é verificável em segundos.

**Sinalizações para pesquisa mais profunda por fase:**
- Fase 1 (captura): comportamento do dxcam com janela em segundo monitor e com o jogo em background — verificar cedo, pode forçar Windows Graphics Capture antes do previsto.
- Fase 3 (visão): valores HSV reais das barras sob Gamma 1.16 — só determinável com frame real.
- Fase 7 (OCR): Tesseract em fonte estilizada e pequena de UI de jogo é notoriamente ruim; pode exigir upscale + binarização, ou ser substituído por template matching contra um dicionário fechado dos nomes conhecidos da party (mais robusto e provavelmente melhor aqui, já que o conjunto de nomes é pequeno e conhecido).

---

## Scaling Considerations

"Usuários" não é a dimensão relevante. As dimensões que estressam esta arquitetura são outras:

| Dimensão | Situação | Ajuste arquitetural |
|---|---|---|
| **Tamanho da party** | 4 → 9 membros (party full de L2) | `slots` já é dado de calibração; nenhum código muda. Custo de extração cresce linear e continua desprezível |
| **Taxa de captura** | 1 Hz → 5 Hz | Sem mudança. A 5 Hz um tick usa ~5% do orçamento. Debounce em *contagem de observações* precisa virar debounce em *tempo* — ou os contadores viram um quinto do tempo pretendido |
| **Command channel (múltiplas parties)** | vários personagens/janelas | `FrameSource` + `Tracker` por janela, dispatcher compartilhado. A fila já desacopla. É a razão de o tracker ser puro e sem estado global |
| **Novos sinais** (OCR do chat de sistema) | sinal complementar | Novo produtor de `Observation` fundido antes do tracker; a FSM não muda. Vale desenhar `Observation` com espaço para isso desde já |
| **Novos canais** (Discord, Telegram) | além do WhatsApp | Novo adapter do `Notifier`; dispatcher faz fan-out. Zero mudança no core |
| **Volume de gravação** | horas de farm com `--record` | Recorte da região + PNG comprimido + gravar 1 em N frames + rotação por tamanho |

**Primeiro gargalo real:** OCR, se algum dia entrar no caminho por frame (50-300 ms por nome). Correção: manter sob demanda; se necessário, thread dedicada com fila.
**Segundo:** nada. Este sistema não tem problema de performance — tem problema de correção.

---

## Anti-Patterns

### Anti-Pattern 1: Chamar `time.time()` dentro da máquina de estados
**What people do:** o tracker pega o relógio sozinho para calcular debounce.
**Why it's wrong:** testar "confirma após 3 s" vira `sleep(3)`. Lento e flaky, então ninguém escreve o segundo teste — e o segundo teste é justamente o caso raro que o sistema existe para pegar.
**Do this instead:** injete `now: float`. `FakeClock` roda 10 minutos de cenário em 2 ms.

### Anti-Pattern 2: Derivar "cego" dos sinais dos membros
**What people do:** `if nenhum_membro_tem_mp: cego = True`.
**Why it's wrong:** um wipe da party inteira fica idêntico a um alt-tab. O sistema silencia exatamente no evento mais crítico.
**Do this instead:** âncora independente na moldura da UI. `ui_visible` nunca olha para os slots.

### Anti-Pattern 3: Chavear estado por índice de slot
**What people do:** `state[2].hp` porque a linha 2 é o Korzis.
**Why it's wrong:** a party window compacta linhas quando alguém sai. O slot 2 vira o antigo slot 3 e a morte é atribuída ao membro errado. Falha silenciosa e plausível — a pior categoria.
**Do this instead:** `RosterResolver` traduz slot→nome antes do tracker; o tracker é chaveado por nome.

### Anti-Pattern 4: POST HTTP inline no loop de captura
**What people do:** `requests.post(...)` direto onde o evento é detectado.
**Why it's wrong:** um timeout de 30 s congela a detecção por 30 s. Durante um wipe, os eventos seguintes são perdidos — o momento em que o alerta mais importa.
**Do this instead:** fila + thread dispatcher. `put_nowait`, nunca bloqueia.

### Anti-Pattern 5: Zerar os contadores de debounce ao entrar em cego
**What people do:** `if cego: reset_all()`.
**Why it's wrong:** morte 200 ms antes de um alt-tab desaparece.
**Do this instead:** congele os contadores; ao sair do cego, passe pela janela de graça e reavalie. Se ainda morto, emita.

### Anti-Pattern 6: Coordenadas e thresholds hardcoded no código
**What people do:** `frame[30:190, 10:230]` espalhado por `extract.py`.
**Why it's wrong:** o usuário não consegue recalibrar sem editar Python; mudar resolução exige mexer no código; testes não conseguem variar geometria.
**Do this instead:** `calibration.json` como entrada, com `schema_version` e validação de geometria na partida.

### Anti-Pattern 7: Threshold em RGB absoluto e em contagem de pixels
**What people do:** `if pixels_vermelhos < 5: morto`.
**Why it's wrong:** Gamma 1.16 e configurações de vídeo deslocam RGB; contagem absoluta quebra se a barra mudar de largura ou a resolução mudar.
**Do this instead:** HSV para a cor (imune a gamma) e **razão** — fração da largura própria da barra que está preenchida. Adimensional e portável.

### Anti-Pattern 8: Construir detecção antes da gravação
**What people do:** ir direto ao interessante — extrair HP e escrever a FSM — e "testar depois".
**Why it's wrong:** o evento alvo é raro e não reproduzível. Você itera contra o jogo ao vivo, sem repetibilidade, sem regressão, sem saber se o ajuste de hoje quebrou o de ontem.
**Do this instead:** `--record` na fase 1. Cada sessão gravada vira fixture permanente.

### Anti-Pattern 9: Cooldown implementado no notifier
**What people do:** o notifier guarda "já mandei sobre o TioMad há 30 s".
**Why it's wrong:** "um alerta por morte até ressuscitar" não é uma janela de tempo — é uma propriedade de estado. Cooldown por tempo alerta de novo aos 31 s com o membro ainda morto.
**Do this instead:** o cooldown é a própria FSM (já está em `DEAD`, já emitiu). Mantenha um rate-limit guard no dispatcher apenas como rede de segurança contra bug.

### Anti-Pattern 10: Ignorar `None` do `grab()`
**What people do:** `frame = camera.grab(); if frame is None: continue`.
**Why it's wrong:** o dxcam devolve `None` quando nada foi renderizado desde a última captura. Uma party window parada é exatamente isso. O loop pula todos os ticks, o debounce nunca avança e o scanner fica cego sem avisar.
**Do this instead:** `grab(new_frame_only=False)` no adapter e pipeline idempotente sobre frames repetidos.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Chatwoot** | `POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/messages`, header `api_access_token`, body `{content, message_type: "outgoing", private: false}` | Conversa precisa existir. Setup: `POST /contacts` (`inbox_id`, `phone_number` em E.164) → `POST /conversations` (`inbox_id`, `contact_id`, `source_id: ""`, `message`) → guarde o `conversation_id` no config. `message_type` aceita só `outgoing`/`incoming`. `template_params` existe para templates de WhatsApp. A referência oficial não documenta rate limits — trate 429 como retryable com `Retry-After` |
| **WhatsApp (via Chatwoot)** | indireto | Provedores de WhatsApp Business costumam ter janela de 24 h para mensagens livres, exigindo template fora dela. Se a party não interage no Chatwoot, alertas podem precisar ser template. **Não verificado para o setup específico do usuário — validar cedo, é o risco de integração nº 1 do projeto** |
| **Windows capture API** | Desktop Duplication via `dxcam` (v1); Windows Graphics Capture (evolução) | Duplication exige a janela visível. BitBlt/PrintWindow **não** servem para conteúdo acelerado por GPU — devolvem preto/corrompido, não capturam OpenGL nem fullscreen exclusivo. Para janela em background/ocluída o caminho é WGC (o que o OBS usa). Isolar atrás do port `FrameSource` deixa essa troca barata |
| **Tesseract OCR** | subprocess via `pytesseract` | Binário externo, precisa estar no PATH. 50-300 ms por chamada. Para um conjunto fechado e pequeno de nomes, template matching contra os nomes conhecidos tende a ser mais robusto e mais rápido |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| capture ↔ vision | `Frame` (dataclass frozen) | Vision nunca sabe de onde veio o frame — é o que permite replay |
| vision ↔ core | `Observation` (indexado por slot) | Vision nunca conhece nomes nem estados |
| roster ↔ tracker | `PartySnapshot` (chaveado por nome) | Onde a identidade é resolvida; único lugar que sabe de reshuffle |
| tracker → dispatcher | `queue.Queue`, one-way, não bloqueante | **Fronteira de thread.** Tracker nunca espera entrega |
| dispatcher ↔ notifier | Protocol `Notifier.send(str)` | Troca de adapter dá `--dry-run` e testes sem rede |
| calibration → runtime | JSON read-only, validado na partida | Runtime nunca escreve. Incompatibilidade = falha alta, não regiões silenciosamente erradas |
| core ↔ relógio | `Clock` protocol injetado | `FakeClock` nos testes; nenhum `import time` no core |

---

## Sources

- Chatwoot Developer Docs — Create New Message (endpoint, headers, `message_type`, `template_params`, ausência de rate limits documentados) — https://developers.chatwoot.com/api-reference/messages/create-new-message — **MEDIUM** (doc primária, verificada por fetch)
- Chatwoot GitHub Discussion #2198 — sequência contato → conversa → mensagem, reuso de `conversation_id`, E.164 — https://github.com/orgs/chatwoot/discussions/2198 — **MEDIUM**
- DXcam README — semântica de `grab()` retornando `None` sem frame novo, `new_frame_only=False`, `video_mode`, formato `(left, top, right, bottom)`, thread do `start()` — https://github.com/ra1nty/DXcam/blob/main/README.md — **MEDIUM** (doc primária, verificada por fetch)
- OBS Forums / Ryan's Blog — Windows Graphics Capture vs BitBlt vs PrintWindow para janelas DirectX e ocluídas — https://obsproject.com/forum/threads/for-capture-method-whats-the-difference-between-bitblt-and-windows-graphics-capture.127687/ · https://ryanai.dev/en/blog/pc-window-capture — **MEDIUM**
- Toolbox Spotter (arXiv 2105.10842) — padrão "Alert Pipeline" separado do nó de detecção, com política configurável de quais eventos alertam — https://arxiv.org/pdf/2105.10842 — **LOW-MEDIUM** (analogia de domínio, não implementação direta)
- Guias de pipeline de visão computacional em produção — desacoplamento ingestão/inferência/ação por fila para tolerância a falha e buffering — https://inferensys.com/guides/computer-vision-sensing-and-dynamic-interpretation/setting-up-a-real-time-defect-detection-system-with-computer-vision — **LOW** (o padrão é consensual; a escala descrita é muito maior que a deste projeto)
- pytest-goldie / pytest fixtures — golden testing como metodologia (comparar saída contra resultado pré-gravado) — https://pypi.org/project/pytest-goldie · https://docs.pytest.org/en/stable/how-to/fixtures.html — **MEDIUM**

**Gaps conhecidos:**
- Comportamento exato da party window do L2 XM Essence (barra de HP com membro fora de alcance/desconectado; se a linha some ou fica cinza; se há mensagem de sistema na morte) — **não verificável sem captura real**. Fase 1 (gravação) resolve.
- Regras de janela de 24 h / templates do provedor de WhatsApp no Chatwoot do usuário — precisa ser validado contra a instância dele, não contra doc genérica.
- Valores HSV reais das barras sob Gamma 1.16 — só determináveis a partir de um frame gravado.

---
*Architecture research for: monitor local de tela em tempo real com detecção de eventos e alerta externo*
*Researched: 2026-08-24*
