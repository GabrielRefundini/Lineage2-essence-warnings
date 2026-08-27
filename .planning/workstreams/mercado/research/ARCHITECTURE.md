# Architecture Research — Market Capture Integration

**Domain:** Passive market-price capture (World Exchange) added to an existing layered screen-reader
**Researched:** 2026-08-27
**Confidence:** HIGH for integration points (read from the real modules, cited by file:line); MEDIUM for market-UI specifics (no recorded World Exchange frames exist yet — the very first build step fixes that)

## The Questions This Answers

(a) same process vs `--mercado` mode · (b) where "market is open" detection lives · (c) where the 2-frame page-stability state machine lives · (d) where SQLite writing lives given `visao.py`'s no-disk rule · (e) how read-honesty counters reach the console · plus a build order that honors the fixture-first discipline.

---

## (a) Separate mode: `--mercado`. Not the party loop.

**Recommendation: a `--mercado` flag that builds a dedicated market loop in the same binary — the exact precedent of `--so-agenda` → `laco_da_agenda` (`l2scanner/__main__.py:1085`, flag at `__main__.py:1790`).** The user launches a third invocation when they sit down to read the market; the two party-watching instances stay untouched.

Four reasons, all grounded in the existing code:

1. **The two activities are mutually exclusive on screen.** The market panel is precisely the kind of overlay that trips `_bordas_da_barra_intactas` (`l2scanner/visao.py:477-510`) and the own-bar frame gate (`visao.py:244-307`). When the market is readable, the party session is *by design* blind (`ui_visivel=False`, blind-gate in `rastreador`). Bolting market reading onto `Sessao.tick` means the market feature only works while the party feature is degraded — two features sharing one tick but never both useful. Coupling buys nothing.

2. **The tick already documents why unrelated concerns must not share a failure path.** `sessao.py:211-215`: the maintenance check runs *before* extraction because "um erro de leitura da party engoliria o aviso de manutencao junto." Every concern added to `Sessao.tick` re-litigates that ordering. A market OCR pass (tens of ms per page, cf. the measured dialog search cost at `captura_janela.py:38-43` — ~45 ms of matchTemplate would be ~98% of the scanner's CPU) inside the alerting tick is risk with no compensation.

3. **Multi-process is already this project's normal.** The user runs two instances (PROJECT.md:68); the shared-disk discipline exists and is battle-tested: `O_CREAT|O_EXCL` markers and atomic `os.replace` in `loot.py:198-216, 260-284`. A third process is not an architectural novelty.

4. **Duty cycles differ.** Party watching is 1 Hz forever. Market capture is a short, *user-driven* session: open World Exchange, page through, close. `--intervalo` already exists (`__main__.py:1771-1776`) and the WGC source pushes ~38 fps and discards (`captura_janela.py:10-12`), so the market loop can poll at 2–4 Hz for free without touching the party instances.

**What `--mercado` reuses unchanged:** `JanelaSource` (same `FrameSource` port, `frames.py:109-113`) with `relativa=True` regions (`captura_janela.py:369-421`), `_ClassificadorDeSaude` (black/frozen frames, `frames.py:116-140`), `Gravador`/`ReplaySource` for `--record`/`--replay` (`gravador.py`, `frames.py:190-244`), `dpi.py`, `config.py`, `console.py` color plumbing.

**What `--mercado` does NOT construct:** `Rastreador`, `Despachante`, agenda/silêncio/loot/presença. Market capture sends nothing to WhatsApp in v1; it reads and records. (If a later milestone wants price alerts, the `Despachante` seam is there.)

**Rejected alternative — opportunistic capture inside the party loop** ("when the brightness gate says a panel is covering, try reading it as a market"): rejected because (i) the gate fires for inventory, character sheet, and loja too (`visao.py:279-299` measured all of them), so nearly every trip would be a wasted OCR pass; (ii) it makes market coverage a side effect of party blindness — untestable duty cycle, no user intent; (iii) it violates the "one loop, one purpose" lesson that produced `sessao.py` in the first place (`sessao.py:1-36`).

## (b) "Market window is open" — a new positive detector in the extraction layer; the brightness gate stays a negative signal

The existing gate `_moldura_da_barra_propria` (`visao.py:244-257`, thresholds `visao.py:220-241`) detects "*some* dark game panel covers the own HP bar." It cannot say *which* panel — inventory, ficha, loja and market all read the same (moldura 28.0–48.9 measured, `visao.py:230-234`). It is a **negative** signal (something is in the way), and its docstring explicitly warns that everything it certifies can be a partially-occluded crop (`visao.py:85-111`). Do not extend it into a market classifier.

**Recommendation:**

- **New module `mercado_visao.py`** (pure, same charter as `visao.py:1-7`: no clock, no net, no disk, no decisions). It exports `mercado_aberto(frame_pixels, cal) -> bool` — a positive anchor check on a fixed, always-present element of the World Exchange window (title strip / column headers), using the same techniques already proven here: structure-contrast (`_tem_contraste_de_icone`, `visao.py:181-206`) or a stored template like the disconnect dialog (`cliente.py`, wired at `captura_janela.py:391-415`). Which technique wins is decided against recorded frames, not a priori.
- **Anchor + grid regions live in `calibration.json`**, machine-written, optional-with-`.get` — the exact pattern of `banner_manutencao` (`calibracao.py:213, 276-282, 308-309, 357-362`): an old calibration without the keys keeps working, the market feature simply stays off.
- **In `--mercado` mode this detector is the loop's idle/active switch**: market closed → tick does nothing but count; market open → extract page. No blind-mode machinery needed — "market closed" is the normal state, not a failure.
- **Optional cheap cross-check, not a dependency:** the party instances *may* log "own bar covered by a panel" (they already compute the gate) but the market instance must not depend on the party instances running.

## (c) Page-stability gating — a new tracker-layer state machine (`mercado.py`), not in visão, not in sessão

The layering rule this codebase enforces: **memory across frames belongs to the tracker layer.** `visao.extrair` is pure — "mesmo frame, mesma saida, sempre" (`visao.py:534-535`); `rastreador.py` holds all cross-frame state with time by parameter (`rastreador.py:1-8`); `Sessao.tick` orchestrates and dispatches but delegates every decision (`sessao.py:217-243`).

"Accept a page only when 2 consecutive frames agree" needs memory of the previous frame's reading → it is a tracker.

**Recommendation: `mercado.py` with an `EstabilizadorDePagina` class**, mirroring `Rastreador`'s contract:

```
LeituraDePagina = extração pura de UM frame (mercado_visao.py)
        │
        ▼
EstabilizadorDePagina.observar(leitura, momento) -> PaginaAceita | None
```

- Pure: no clock (`momento` by parameter — the discipline stated at `loot.py:23-25` and `manutencao.py:21-27`), no disk, no OCR imports. Enforce it the way `manutencao.py` does — an `ast`-based import tripwire in the test suite (`manutencao.py:28-31`: "Uma regra de arquitetura que so vive num comentario e uma regra que ja quebrou").
- **Agreement is compared on PARSED ROWS (item, price, qty), never on raw pixels.** Two independent measurements in this repo prove pixel-identity is the wrong test: (i) game text sits on live scenery — the same name crop differs between frames 4 s apart (`identidade.py:27-36`); (ii) byte-identical frames are the *frozen-capture* signal, treated as a failure (`frames.py:31-35, 133-138`). If the market panel turns out to be fully opaque, row-level comparison still works; the reverse is not true. (Panel opacity: UNVERIFIED — settle it with the first recording.)
- Emits a structured `PaginaAceita` (rows + frame indices + why accepted), and counts the discards: page changed before confirming (lost), rows unparseable (illegible). These counts are the raw material for (e).
- Sits under a thin `SessaoDeMercado` (new, in `mercado_sessao.py` or inside `mercado.py`) that plays the role `Sessao` plays for the party loop: owns the per-run counters, calls extraction → stabilizer → registry, returns a `ResultadoDoTickDeMercado` so tests assert structure, not log text (the reason `ResultadoDoTick` exists, `sessao.py:53-60`).

## (d) SQLite lives in a new registry module, `mercado_registro.py` — the `loot.py` slot in the architecture

`visao.py`'s charter forbids disk (`visao.py:1-7`); the established home for durable state is a dedicated registry module: `RegistroDeLoot` owns `.loot/` (`loot.py:178-195`), `RegistroEmDisco` owns `.agenda/`. Follow it exactly:

- **New `mercado_registro.py`, class `RegistroDeMercado`,** sole owner of `mercado.sqlite`. Nothing else in the codebase imports `sqlite3`. Time by parameter throughout (`gravar_pagina(pagina, agora)`), called from `SessaoDeMercado.tick` the same way the party tick calls `self.loot.consumir(agora)` (`sessao.py:299-300`).
- **Never lose data silently — loot's tri-state failure design applies verbatim.** `loot.py:16-21, 198-216`: disk failure must *keep* the pending page for the next tick to retry, never drop it and report success. A failed INSERT returns "falhou" up to the session, which keeps the accepted page queued and increments a visible counter.
- **Idempotent writes.** The identity-in-the-key trick (`loot.py:56-57`: "A identidade do registro E o nome") translates to a `UNIQUE` constraint on a content key (e.g. `(captura_id, pagina_hash)` or `(item, preco, quantidade, pagina_hash)`) with `INSERT OR IGNORE` — re-reading the same page (user scrolls back) is a dedupe, not a duplicate.
- **Concurrency:** SQLite with `journal_mode=WAL` + `busy_timeout` handles the two-instances-one-disk reality that `.loot/` handles with `O_CREAT|O_EXCL`. In practice only the `--mercado` instance writes, but the registry must not corrupt if a second one is launched by mistake — WAL gives that for free. Append-only, no pruning: same reasoning as `.loot/` ("estatistica e para sempre", `loot.py:10-14, 187-189`) — price history is the product.
- **Why SQLite here and flat files there:** loot records are dozens of tiny independent facts raced by two writers — filesystem atomics fit. Market pages are thousands of rows queried by item/time — a query engine fits. Different shape, different store; the *boundary* (one module owns the disk, time by parameter, failure is tri-state and visible) is identical.

## (e) Read-honesty instrumentation — counters on the session object, rendered by the loop's status block

The pattern exists end to end today:

1. **Counters live on the session object**: `Sessao` keeps `contagem` per frame-health, `ticks_cego`, `ticks_sem_reconhecer` (`sessao.py:147-162`) — the last one born precisely because "a falha de identidade era estruturalmente invisivel" (`sessao.py:152-158`). Pages-lost is the same species of honesty: *I saw a page and could not keep it.* → `SessaoDeMercado` carries `paginas_aceitas`, `paginas_perdidas` (changed before 2-frame confirmation), `leituras_ilegiveis`, `duplicatas`, `gravacoes_falhadas`.
2. **Per-tick facts return structured** in `ResultadoDoTickDeMercado` (mirror of `ResultadoDoTick`, `sessao.py:53-95`) so tests assert what happened without parsing log text.
3. **The loop renders a status block on a cadence**: `desenhar_status(...)` is called every `--status-a-cada` seconds (`__main__.py:1676-1683`) and once more in `finally` so a fast replay still shows the outcome (`__main__.py:1692-1700`). Add `desenhar_status_do_mercado(sessao)` — market open/closed, current page fingerprint, and the counter line, e.g. `paginas: 41 aceitas · 3 perdidas · 2 ilegiveis · 5 repetidas`. The end-of-run summary extends the existing resumo pattern (`__main__.py:1717-1729`).
4. **Threshold warnings for silent failure**, mirroring `TICKS_SEM_RECONHECER_PARA_AVISAR` (`__main__.py:1652-1668`): N consecutive illegible pages with the market open ⇒ "estou vendo o mercado e nao consigo ler — recalibre", stating what the scanner sees, never asserting what the market contains.

## System Overview

```
                     ┌──────────────── same binary, third invocation ───────────────┐
  --mercado          │                                                              │
  ┌───────────────┐  │  ┌──────────────────┐   ┌──────────────────────┐             │
  │ JanelaSource  │──┼─▶│ mercado_visao.py │──▶│ mercado.py           │             │
  │ (REUSED)      │  │  │ NEW · pure       │   │ NEW · pure tracker   │             │
  │ frames.py     │  │  │ mercado_aberto() │   │ EstabilizadorDe-     │             │
  │ Gravador/     │  │  │ ler_pagina()     │   │ Pagina (2-frame gate)│             │
  │ ReplaySource  │  │  └──────────────────┘   └──────────┬───────────┘             │
  │ (REUSED)      │  │        ▲ calibration.json           │ PaginaAceita           │
  └───────────────┘  │        │ (EXTENDED: anchor,         ▼                        │
                     │        │  grid, price columns) ┌──────────────────────┐      │
                     │  ┌─────┴──────┐                │ SessaoDeMercado NEW  │      │
                     │  │ calibrar.py│                │ counters + tick      │      │
                     │  │ (EXTENDED) │                └───┬──────────────┬───┘      │
                     │  └────────────┘                    ▼              ▼          │
                     │                     ┌────────────────────┐  ┌─────────────┐  │
                     │                     │ mercado_registro.py│  │ console     │  │
                     │                     │ NEW · SQLite owner │  │ status block│  │
                     │                     └────────────────────┘  │ (EXTENDED)  │  │
                     │                                             └─────────────┘  │
                     └──────────────────────────────────────────────────────────────┘
  Party instances (Yazalaque, Faerlina): UNTOUCHED. Zero party-path files modified
  except __main__.py (new flag + new loop function) and calibracao.py (optional keys).
```

## New vs Modified — explicit

| File | Status | What |
|---|---|---|
| `l2scanner/mercado_visao.py` | **NEW** | Pure extraction: `mercado_aberto()`, `ler_pagina()` → `LeituraDePagina`. Same charter as `visao.py:1-7`. |
| `l2scanner/mercado.py` | **NEW** | `EstabilizadorDePagina` (2-frame agreement on parsed rows), pure, time by parameter; `SessaoDeMercado` + `ResultadoDoTickDeMercado`. |
| `l2scanner/mercado_registro.py` | **NEW** | `RegistroDeMercado`: only SQLite owner. WAL, `INSERT OR IGNORE` on content key, tri-state failure like `loot.py:198-216`. |
| `l2scanner/__main__.py` | **MODIFIED** | `--mercado` flag; `laco_do_mercado(args, cal)` alongside `laco_da_agenda` (`__main__.py:1085`); `desenhar_status_do_mercado`. |
| `l2scanner/calibracao.py` | **MODIFIED** | Optional regions `mercado_ancora`, `mercado_grade` (+ column geometry), loaded with `.get` like `banner_manutencao` (`calibracao.py:357-362`). |
| `l2scanner/calibrar.py` | **MODIFIED** | Calibration step to mark the market anchor/grid on a live or recorded frame. |
| `l2scanner/ocr.py` | **REUSED (maybe extended)** | If digits go through WinRT OCR, reuse the two-scale-agreement discipline (`ocr.py:34-80`). See open decision below. |
| `visao.py`, `sessao.py`, `rastreador.py`, `identidade.py`, `loot.py`, `agenda.py`, `notificador.py` | **UNTOUCHED** | The party path does not change byte-for-byte — the same guarantee the `hp_proprio_aparente` change made (`visao.py:693-696`). |

## Key Data Flow

```
frame (JanelaSource, region = market panel, relativa=True)
  → saude gate (frames.py:116-140; FALHA/CONGELADO → count, skip)
  → mercado_aberto(pixels, cal)?  ──no──▶ idle tick (counted)
  → ler_pagina(pixels, cal) → LeituraDePagina (rows or per-row "ilegivel")
  → estabilizador.observar(leitura, momento)
        rows == previous rows → PaginaAceita
        rows != previous      → previous page lost if it never confirmed (counted)
  → registro.gravar_pagina(aceita, agora)
        "criado" → paginas_aceitas += 1
        "ja_existia" → duplicatas += 1  (honest, not an error)
        "falhou" → keep queued, retry next tick, gravacoes_falhadas += 1
  → ResultadoDoTickDeMercado → loop logs / status block
```

## Open decision to settle with fixtures (not a priori)

**Digits: template matching vs OCR.** Prices are digits + separators — a *closed set of ~12 glyphs* rendered deterministically, which is exactly the argument that made `identidade.py` choose templates over OCR (`identidade.py:14-23`). Item *names*, however, are an open set (unlike the party roster) — if names must be read, `ocr.py`'s WinRT engine with the two-scale agreement guard (`ocr.py:34-80`) is the precedent; if only recognizing *configured watch-list items*, the `identidade.py` signature approach applies again. Record real frames first; measure both. The stabilizer's 2-frame agreement is itself a second guard in the same spirit as the two-scale OCR consensus — two independent chances to disagree before anything is recorded.

## Anti-Patterns (specific to this integration)

1. **Extending `barra_propria_legivel` into a market detector.** Its contract is a safety gate for the own-HP path; its false-accept/false-reject economics were tuned for death detection (`visao.py:260-307`) and the comment block at `visao.py:85-111` shows what happens when its signal gets a second consumer. New signal, new function, new module.
2. **Pixel-hash page stability.** Byte-identical frames mean frozen capture here (`frames.py:133-138`); scenery-behind-text means live frames never hash equal (`identidade.py:27-36`). Compare parsed rows.
3. **SQLite calls anywhere outside `mercado_registro.py`.** One module owns each durable store in this codebase (`loot.py:178-189`); enforce with the `ast` import-tripwire pattern (`manutencao.py:28-31`).
4. **Collapsing write failure into success.** `loot.py:199-216` documents why tri-state matters: a dropped page that reports "gravada" is price history that lies forever.
5. **Putting the market pass inside `Sessao.tick`.** Re-opens the swallowed-concern class of bug that `sessao.py:20-36` exists to document; couples a heavy read to the latency-critical alert path.

## Suggested Build Order (fixture-first, each step testable without the game)

1. **Record before building** — the project's own founding discipline (`gravador.py:1-14`). Run `--record` with the capture region set to the market panel; page through the World Exchange for real. Bank: market closed, market open idle, mid-scroll transition, every page of at least one full item listing, and a dark-scene backdrop. These frames answer the open questions (panel opacity, font, grid geometry) and become permanent fixtures. *Everything after this step runs against these frames.*
2. **Calibration keys + tool** (`calibracao.py`, `calibrar.py`): anchor + grid regions, written to `calibration.json`, optional-with-`.get`. Test: old calibration file still loads (the `banner_manutencao` regression pattern).
3. **`mercado_visao.py` detection**: `mercado_aberto()` against open/closed/covered fixtures. Measure the margin, write it in the module like every threshold here does (`visao.py:186-193` style).
4. **`mercado_visao.py` page extraction**: `ler_pagina()` rows from fixtures; settle template-vs-OCR with measurements; per-row "ilegivel" is a value, not an exception.
5. **`mercado.py` stabilizer**: pure state machine tested in milliseconds — same 2-frame scenarios as the party debounce tests (agree/disagree/flicker/mid-scroll), fabricated `LeituraDePagina` objects, time by parameter.
6. **`mercado_registro.py`**: SQLite in `tmp_path`; dedupe, WAL concurrency, tri-state failure (fault-injected write), append-only.
7. **`SessaoDeMercado` + `--mercado` loop + console block** (`__main__.py`): wire, counters, status, final summary. Test through `tick()` with fabricated frames — the whole reason the session layer exists (`sessao.py:30-36`).
8. **Replay harness**: `--mercado --replay <pasta>` over the step-1 recording must reproduce the same accepted pages and the same counters — the market's equivalent of the party's regression guarantee (`frames.py:190-197`, `Frame.momento` at `frames.py:52-58`).

Dependency spine: 1 → 2 → 3/4 → 5 → 7/8, with 6 parallel to 3–5 (it depends only on the `PaginaAceita` shape).

## Sources

- `l2scanner/visao.py` — purity charter (1-7), brightness gate + thresholds (220-307), `hp_proprio_aparente` single-consumer lesson (79-111)
- `l2scanner/sessao.py` — session/tick pattern and why it exists (1-36), structured results (53-95), counters (147-162), ordering of concerns (209-215)
- `l2scanner/rastreador.py` — tracker-layer contract (1-8), state-machine placement precedent
- `l2scanner/identidade.py` — closed-set templates over OCR (14-23), scenery-behind-text measurements (27-36)
- `l2scanner/loot.py` — durable-store module pattern, tri-state disk failure (16-21, 198-216), identity-in-the-key (56-57), no-pruning rationale (10-14)
- `l2scanner/manutencao.py` — optional-feature degradation, import tripwire (28-31), consensus guard
- `l2scanner/ocr.py` — two-scale OCR agreement (34-80)
- `l2scanner/frames.py` — FrameSource port (109-113), health classifier (116-140), ReplaySource + momento (52-58, 190-244)
- `l2scanner/captura_janela.py` — WGC push model (10-12), relative regions + extras (369-421), matchTemplate cost (38-43)
- `l2scanner/__main__.py` — `laco_da_agenda` separate-mode precedent (1085), extras wiring (1419-1443), status cadence + finally (1676-1700), honesty warnings (1652-1668)
- `l2scanner/calibracao.py` — optional region pattern (213, 276-282, 357-362)
- `.planning/PROJECT.md` — two-instance reality (68), passive-only constraint (74)

---
*Architecture research for: v1-mercado (World Exchange price capture)*
*Researched: 2026-08-27*
