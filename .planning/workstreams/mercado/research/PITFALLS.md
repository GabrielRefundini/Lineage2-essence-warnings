# Pitfalls Research

**Domain:** Passive screen-read market-price capture (World Exchange) added to an existing 1 Hz game screen-reader (L2 Party Scanner)
**Researched:** 2026-08-27
**Confidence:** MEDIUM-HIGH overall — codebase-grounded claims HIGH; SQLite behavior HIGH (well-established engine semantics); World Exchange UI specifics UNVERIFIED (no public documentation exists for this private-server client; every UI claim below is gated on a recorder spike, same discipline v1 used)

This is not generic OCR/DB advice. Every pitfall below is checked against this project's real history:

| Historical incident | Lesson it encodes |
|---|---|
| Inventory/market panel covering the HP bar read as death **27x in one log** | Occlusion produces plausible-but-wrong readings; the market panel is *literally the trigger* of the project's worst false positive — and this milestone asks the user to open it MORE |
| `imwrite` silently returning `False` announced as success | Unchecked write returns lie; `gravador.py` still does not check `cv2.imwrite`'s return and increments `frames_gravados` regardless |
| Mid-transition frame produces a PLAUSIBLE-BUT-WRONG reading | Worse than no reading — the project already answered this once with the two-scale-agreement pattern in `ocr.py` (D-d) |
| Recorder counts frames it never verified were written | Counters must count confirmed outcomes, not attempts |
| v1 name identification: template-match beat OCR because the roster is a **closed set** | The party roster is 4-8 names; the market's item universe is NOT closed the same way — the transfer of this technique is partial, not free |

## Critical Pitfalls

### Pitfall 1: The market panel is the scanner's worst historical enemy — and this feature invites it on screen

**What goes wrong:**
The single worst false positive in v1 history was the inventory/market panel covering the party window's HP bar — read as death 27 times in one log. The mercado milestone *encourages* the user to open the World Exchange regularly. If market capture ships without teaching the death-detection side that "market panel open" is a known occlusion state, every price-checking session becomes a false-death-alert lottery. The two features will actively sabotage each other.

**Why it happens:**
The market reader and the party watcher will be built as separate pipelines by different plans, each seeing only its own frames. Nobody owns the interaction: "panel detected" is the market feature's *start* signal and should simultaneously be the death detector's *suppress/occlusion* signal, but nothing forces that wiring.

**How to avoid:**
Make panel detection ONE shared signal, produced once per tick, consumed by both sides. The detector that says "World Exchange is open, start reading prices" must be the same object that tells `presenca`/`rastreador` "the UI region may be occluded — treat per existing blind/occlusion rules." Build panel detection FIRST (it is cheap — a template anchor on the panel's title bar, same technique as `identidade`'s ornament anchoring), before any digit reading exists.

**Warning signs:**
Death alerts (or blind-mode flapping in the console) that correlate in time with market snapshots landing in the DB. Grep the log for death events within ±10 s of market-capture events — any hit is this pitfall.

**Phase to address:**
**Phase 1 (Detecção do painel + calibração)** — panel detection is the phase-1 deliverable precisely so it can be wired into the existing occlusion logic before reading exists. Verification: replay the v1 recording that produced the 27x incident; the panel detector must fire on those frames.

---

### Pitfall 2: A misread price is plausible-but-wrong, and the DB makes it permanent

**What goes wrong:**
A dropped leading digit turns 1,250,000 into 250,000; a missed digit-group turns 12,000,000 into 12,000. Both are *plausible prices* — adena prices legitimately span orders of magnitude, so no single reading is self-evidently wrong. Unlike v1's death alerts (transient, correctable by the next frame), a wrong price INSERT is permanent: it sits in the time series forever, and the analysis layer ("price dropped 80%!") amplifies it into a false conclusion days later. This is the project's known worst failure class (plausible-but-wrong > no reading) with a new property: **persistence**.

**Why it happens:**
Mid-transition frames: the panel opening, a scroll in progress, a row being hovered/highlighted, the list refreshing. At 1 Hz the odds of catching a transition frame are high. v1 already proved a mid-transition frame yields readable-but-wrong output; digits make it worse because *every* digit string parses to a valid number.

**How to avoid:**
Reuse the house pattern, already built and philosophically justified in `ocr.py` (D-d): **no reading enters the dataset unless two independent observations agree.** For prices: require the same (item, price) cell to read identically on two consecutive frames before it becomes a row. This also solves scroll-transition frames for free (a scrolling list never matches itself twice). Additionally: store per-row a read-confidence and the raw crop hash so a suspicious row can be audited against pixels later. Never repair a reading — abstain. Abstention costs one second (the next frame); a wrong row costs the dataset.

**Warning signs:**
Rows in the DB whose price differs from the same item's neighbors by exactly a power of 10 or 1000. Add this exact query as a health check in the analysis console.

**Phase to address:**
**Phase 2 (Leitura de dígitos)** owns two-frame agreement; **Phase 4 (Análise)** owns the power-of-10 outlier audit query. Verification: feed the reader a recorded scroll sequence; zero rows may be produced from transition frames.

---

### Pitfall 3: Thousands separators, kerning, and the digit closed-set that isn't quite closed

**What goes wrong:**
Per-digit template matching assumes the glyph inventory is `0-9`. Game price columns also render: thousands separators (`,` or `.` — locale-dependent, UNVERIFIED for this client), and possibly a currency icon or the word "Adena" adjacent to the number. A separator glyph is 2-4 px wide; naive segmentation either merges it into a neighboring digit (a `,3` blob matches nothing, or worse, weakly matches `1`) or the reader silently skips it and cannot verify digit-grouping. Anti-aliased digit pairs can touch, so connected-component segmentation fuses `11` into one blob that matches neither template.

**Why it happens:**
The v1 name-template success (`identidade.py`: tight-crop + text-mask → correlation 1.000) creates confidence that "template matching just works." It worked because names are matched as *whole images* against a roster of 4-8. Digits are matched *individually* after a segmentation step that names never needed — segmentation is the new, untested link, and separators/kerning attack exactly that link.

**How to avoid:**
1. Treat the separator as a **first-class glyph in the template set** (11 classes: 0-9 + separator), captured from real frames during calibration — do not strip it in preprocessing.
2. Prefer **sliding-window correlation over connected-component segmentation**: scan the row crop with each template and take non-overlapping peak matches, so touching glyphs never need to be split first. (Same reason v1 chose leading-run over contours for bars: the fragile "find the object first" step is deleted.)
3. **Validate structure after reading**: digit groups between separators must be exactly 3 (except the leading group). A reading that violates grouping is a misread — abstain, don't repair. This check is free and catches most dropped-glyph errors.

**Warning signs:**
Calibration-time: any digit template whose self-match score is below ~0.99 on a second frame of the same number. Runtime: structure-check abstention rate above a few percent means segmentation is fighting the font.

**Phase to address:**
**Phase 1** (capture real digit crops in the recorder; confirm separator character and whether glyphs touch — this is the spike that de-risks everything downstream). **Phase 2** (sliding-window reader + grouping validation).

---

### Pitfall 4: Right-aligned price columns shift every glyph position with number length

**What goes wrong:**
Price columns in game UIs are right-aligned (UNVERIFIED for World Exchange, but near-universal). A fixed left-anchored crop grid — the mental model inherited from the party window, where names start at a stable left edge after the ornament — reads the *tail* of long numbers and the *empty space* of short ones. The failure is not noise: it systematically truncates the most significant digits of expensive items, i.e., plausible-but-wrong again, biased toward cheap.

**Why it happens:**
v1's row geometry is left-anchored (`_inicio_do_nome_apos_ornamento`), and that code will be the template for the new reader. The habit transfers; the alignment doesn't.

**How to avoid:**
Anchor digit scanning at the **right edge of the price cell** and walk leftwards, terminating at the first column with no glyph match. The right edge of a right-aligned column is the stable landmark, exactly as the left edge was for names. Store the cell rect (not glyph positions) in `calibration.json`.

**Warning signs:**
Prices for known-expensive items reading suspiciously low and *round* (missing leading groups). The Phase 4 power-of-10 audit catches it after the fact; a Phase 2 unit test on synthetic short-vs-long numbers in the same cell catches it before.

**Phase to address:**
**Phase 2 (Leitura de dígitos)** — right-edge anchoring is a design decision, cheap now, a rewrite later.

---

### Pitfall 5: Templates silently die when the window size or UI scale changes

**What goes wrong:**
Both the v1 name templates and the new digit/item templates depend on the client rendering text pixel-deterministically at the current window size (1718x1360). If the user resizes the window, changes UI scale, or a patch changes the font, every template's correlation drops — not to zero, but to "weak match territory," where the closed-set matcher starts returning its *least-wrong* candidate instead of abstaining. For names, v1 had margin 0.546 to absorb this. For digits — ten templates that all look alike (3/8, 6/8, 1/7) — the inter-class margin is far thinner, so degraded rendering flips digits into each other silently.

**Why it happens:**
Digit glyphs are the most self-similar glyph family there is. The v1 margin evidence (`identidade.py` docstring: same-name 1.000 vs other-name 0.454) does NOT transfer; nobody re-measures the margin for digits, because "template matching is proven in this codebase."

**How to avoid:**
1. **Measure the digit confusion matrix at calibration time**: match every captured digit template against every other; record the worst inter-class score; set the acceptance threshold above it with real margin. This is one function and it turns an invisible risk into a number.
2. Store the **client window size and capture region dims inside the template cache**; at startup, if the live window size differs, refuse to read prices (loud console message: "recalibre o mercado") instead of reading with degraded templates. The v1 lesson generalizes: a feature must degrade to OFF, never to *quietly worse*.

**Warning signs:**
Runtime match scores drifting from ~1.0 toward the threshold (log the score distribution per session; a median below ~0.97 is the alarm).

**Phase to address:**
**Phase 1** (confusion matrix in the calibrator, window-size stamp in the cache). Verification: intentionally resize the window; the reader must refuse, not misread.

---

### Pitfall 6: "kk" abbreviations and per-unit vs. total price — unit confusion corrupts the series by 1000x

**What goes wrong:**
Two distinct unit traps: (1) If any UI surface abbreviates ("1.2kk" tooltip, own-listing summary) and another shows full digits, mixing them puts values differing by 10^6 in one column. (2) Listings for stackables may show *total* price for the stack, *per-unit* price, or both (UNVERIFIED which the World Exchange shows) — recording "price" without recording *which* means 100 Spirit Ore at 500k total pollutes the same series as 5k-per-unit rows. The analysis then reports garbage medians with full confidence.

**Why it happens:**
The reader is built against whatever surface was calibrated first; nobody re-derives semantics when a second surface (tooltip, detail pane, sell tab) gets added later. And "kk" is ambient in the L2 community (external markets quote adena in "kk" — HIGH confidence this notation surrounds the project), so it will leak into feature requests and possibly into UI text.

**How to avoid:**
1. The reader's glyph set is **digits + separator, nothing else**. Any `k` glyph in a price cell → abstain. Never parse abbreviations.
2. The schema stores `price_total`, `quantity`, and computes `price_per_unit` — quantity is read from its own column, and a row without a readable quantity is stored with `price_per_unit = NULL`, never guessed as 1.
3. Phase 1 spike answers empirically: what exactly does the price column show for a stack listing? One recorded screenshot settles it.

**Warning signs:**
Bimodal price distribution for a single stackable item (two clusters ~quantity apart) — add as a Phase 4 audit query.

**Phase to address:**
**Phase 1** (spike the stack-listing display), **Phase 3 (Persistência)** (schema separates total/unit/quantity).

---

### Pitfall 7: Item names are NOT a closed set the way party names were

**What goes wrong:**
v1's template identification works because the roster is 4-8 names configured by the user. Carrying the approach to the market means the user configures a **watchlist** of items — fine — but three new failure modes appear that party names never had: (1) the list UI likely **truncates long names with ellipsis** ("Spirit O..."), so the rendered pixels differ from the full name and two different items can truncate identically; (2) **variants look near-identical**: "+3 Weapon" vs "+4 Weapon", grade/enchant markers rendered as small overlays or prefixes; (3) an item NOT on the watchlist can weakly match a watchlist template and inject rows for the wrong item — the "membro fantasma" problem `identidade.py` explicitly avoided, reborn with a much bigger universe of impostors.

**Why it happens:**
The party window had no impostors: every line was one of N knowns. The market list is mostly items you *don't* watch — the matcher's job flips from "which of N?" to "is this one of N, or one of thousands of others?" — a rejection problem, which correlation-with-best-match is bad at unless the threshold is calibrated against real negatives.

**How to avoid:**
1. Calibrate the acceptance threshold against **real negative rows** (other items on screen), not just positives — record one full market page and measure watchlist-template scores against every non-watchlist row; threshold above the worst impostor with margin.
2. Template the name **as rendered in the list** (truncated form), captured by the calibrator from the live list — never synthesized from the full name.
3. If two watchlist items collide in truncated form, the calibrator must detect and refuse at calibration time (say it loudly), not at analysis time.
4. Enchant-level variants: either include the enchant glyph region in the template crop, or declare variants out of scope for v1-mercado and record only base-name matches — decide explicitly, don't discover it in the data.

**Warning signs:**
Rows for an item whose price distribution looks like two unrelated items merged; calibration-time impostor score within 0.1 of the acceptance threshold.

**Phase to address:**
**Phase 1** (calibrator captures rendered names + negative-row threshold calibration), **Phase 2** (rejection-first matching).

---

### Pitfall 8: Revisited pages create duplicate rows — and there is no listing ID to dedup on

**What goes wrong:**
The tool cannot drive the UI; the user scrolls and revisits freely. The same listing observed at 14:00, 14:01, and again at 14:30 becomes three rows. Naive dedup on (item, price) is wrong in the other direction: two *different* sellers legitimately list the same item at the same price, and collapsing them undercounts supply. Both errors corrupt the analysis: duplicates inflate apparent supply and weight the median toward whatever page the user lingered on; over-dedup erases real depth.

**Why it happens:**
The instinct is to model rows as **events** ("a listing appeared") because that's what v1's detector produces (deaths are events). But a passive reader of a scrollable list cannot observe listing identity, creation, or removal — it observes *presence at an instant*.

**How to avoid:**
Change the unit of storage: the row is an **observation within a snapshot**, not a listing-event. Schema: `snapshot(id, ts, item_filter_context)` + `observation(snapshot_id, item, price_total, quantity, row_position)`. Within one snapshot, identical (item, price, qty) rows are kept (real depth); across snapshots, nothing is deduped — analysis queries aggregate per-snapshot first (e.g., min ask per snapshot), then over time. Dedup becomes an analysis-time concern with full information, instead of a write-time guess that destroys information. Session-level: a snapshot is only opened when the two-frame-stable page differs from the previous accepted snapshot (cheap page-hash), which kills the "user idles on one page for 5 minutes → 300 identical snapshots" bloat.

**Warning signs:**
Row counts growing linearly with time-on-screen rather than with pages seen; min-ask time series that "changes" only when the user changes pages.

**Phase to address:**
**Phase 3 (Persistência)** — snapshot-centric schema is the load-bearing decision of the whole milestone; it cannot be retrofitted after data exists without migration pain.

---

### Pitfall 9: Partial page reads entering the dataset as truth

**What goes wrong:**
The panel is open but the list is mid-load, mid-scroll, or partially covered by a tooltip/another window. The reader sees 3 valid rows of 10 and records a snapshot; the analysis later computes "min ask" from a snapshot that never contained the actual cheapest listing. This is the market-flavored twin of the 27x incident: partial occlusion producing confident wrong output. A partial snapshot is strictly worse than none, because snapshots are the unit of truth for every aggregate.

**Why it happens:**
Row-level validation feels sufficient ("each row I read, I read correctly") — but correctness of rows says nothing about *completeness* of the page, and the aggregates assume completeness.

**How to avoid:**
Structural completeness gate before a snapshot is accepted: (1) panel anchor template matched (title bar), (2) expected row-grid geometry fully visible (the calibrator records how many row slots the panel shows), (3) every visible row slot either matched a row or matched the "empty slot" appearance — an *unreadable* slot (neither) vetoes the snapshot, (4) two-frame page stability (Pitfall 2's guard, shared). Mark vetoed captures in the log with the reason — that log is the debugging story, exactly like v1's false-positive forensics.

**Warning signs:**
Snapshots whose row count is below the panel's slot count without empty-slot matches; min-ask series with downward spikes that vanish on the next snapshot.

**Phase to address:**
**Phase 2** (completeness gate lives with the reader). Verification: replay a recorded scroll/partial-occlusion session; zero snapshots accepted from incomplete frames.

---

### Pitfall 10: Median of ASKS is not median of SALES — the metric will be read as "the price" and it isn't

**What goes wrong:**
The tool sees only listed (unsold) prices. Sold listings vanish — precisely the listings that were priced right. What remains visible skews high (overpriced items linger for days); so "current price" computed from visible asks is a biased estimator of what things actually trade at, and *stale* listings posted days ago at old prices drag the statistic toward the past. The user makes real trading decisions ("I'll list at the median") on a number that systematically misleads — and nothing in the console will look wrong.

**Why it happens:**
Survivor bias is invisible in the data itself; every individual row is *correct*. The bias lives in what's absent, and passive capture can never observe absence directly.

**How to avoid:**
1. **Name the metric honestly in the console**: "menor pedido visível" / "mediana dos pedidos" — never "preço". Wording is a real guard here; it sets every downstream expectation.
2. Prefer **min-ask and low-percentile asks** over median/mean — the cheap tail is where trades actually clear and where stale overpriced listings have least influence.
3. Exploit the one absence the tool CAN observe: a listing present in snapshot T and gone in T+1 (while the same page context is visible) *probably* sold or was cancelled — record these as `disappearance` events, labeled as the weak signal they are (sale vs. cancel is indistinguishable — say so in the schema comment and the console). This is the closest passive capture gets to transaction prices.
4. Staleness: the World Exchange may or may not display listing age (UNVERIFIED — Phase 1 spike). If it does, read it and let analysis down-weight old listings; if not, disappearance-rate per price band is the substitute.

**Warning signs:**
User messages/decisions phrased as "the price of X is Y" quoting the console verbatim — the wording failed. Median-ask stable for days while min-ask churns — staleness dominating.

**Phase to address:**
**Phase 4 (Análise e console)** — metric selection and wording. **Phase 3** — disappearance events need snapshot-pairing support in the schema, so the decision reaches back into persistence.

---

### Pitfall 11: Coverage bias — the series only exists when the user happens to look

**What goes wrong:**
Sampling cadence is a property of *user behavior*, not the tool: bursts of snapshots when the user shops, then 30-hour gaps. Naive analysis treats the series as regular: "price rose 20% today" compares a Tuesday-morning glance with a Wednesday-night session; per-day averages weight days by how bored the user was. Prices in MMOs have strong time-of-day and event-driven structure (TvT/Prime economies — this project literally has the event schedule in `config.toml`), so irregular sampling aliases directly into fake trends.

**Why it happens:**
Time-series tooling defaults (resampling, interpolation, moving averages) assume regular sampling; the person writing the analysis phase inherits those defaults.

**How to avoid:**
Never interpolate across gaps. Every aggregate in the console states its evidence: "menor pedido: 480k (visto 2x hoje, última 14:31)" — count and recency travel with every number. Comparisons only between snapshots, never between calendar buckets with unequal snapshot counts. And show a coverage line in the console (snapshots today / last seen) so sparse data *looks* sparse — this is also the structural defense for Pitfall 12.

**Warning signs:**
Any console output implying continuity ("subiu 20% hoje") without a sample count next to it.

**Phase to address:**
**Phase 4 (Análise)** — evidence-carrying output format is a phase requirement, not polish.

---

### Pitfall 12: The sparse-data pain becomes the pressure toward automation — and every "fix" sends input

**What goes wrong:**
The predictable arc: data is sparse (Pitfall 11) → "could the tool refresh the market page every hour?" → that requires sending a keypress → which violates the project's hardest constraint (read-only, zero ban risk) — a constraint the project restates in Out of Scope *twice* already because it drifted before. Other predictable requests in this milestone's gravity: "auto-open the exchange to sample prices," "buy automatically when below X," "snipe new cheap listings," "click the listing when alerting." Every one is input-synthesis. The danger isn't a dramatic decision to automate — it's a small "just one F10 keypress per hour, that's harmless" landing in a quick-task.

**Why it happens:**
Market data creates *utility gradients* death-alerts never had: money is on the table, latency and coverage translate to adena, and each marginal automation looks tiny. Unlike death detection (where the game pushes events at the screen), market capture is pull-shaped — the pull has to come from somewhere, and if not the user, then input.

**How to avoid — structurally, not by policy:**
1. **Dependency-tree enforcement (already house doctrine):** no input-synthesis library ever enters `requirements.txt` (v1 already bans `pyautogui` for exactly this reason). Extend it: a CI/test that greps the dependency tree and imports for input APIs (`pyautogui`, `pydirectinput`, `keyboard`, `SendInput` ctypes) and fails loudly. Make the violation impossible to commit quietly.
2. **PROJECT.md Out of Scope entries written NOW, pre-refusing the specific asks**: "auto-refresh/auto-open the market," "auto-buy/snipe," "any keypress or click for sampling" — with the one-line reason (input = ban risk = the constraint the whole project stands on). The v1 pattern of pre-refusing adjacent requests ("Enviar convite de party cai direto na linha acima") worked; reuse the wording style.
3. **Channel the demand into passive-legal outlets**: price-threshold *alerts* via the existing Chatwoot path ("Spirit Ore visto a 400k — abre o jogo") give the user the actionable moment without the tool acting. The coverage display (Pitfall 11) reframes sparse data as "open the market more when you care" — a human-behavior fix for a human-behavior limitation.

**Warning signs:**
Any feature request containing "automatically" + a verb the game must receive ("refresh," "open," "buy," "click"). Any spike evaluating input libraries "just to measure."

**Phase to address:**
**Phase 0/roadmap definition** — the Out of Scope entries and the dependency-tree test cost minutes and must exist before any market phase ships value (the pressure starts when the first sparse chart appears).

---

### Pitfall 13: SQLite shared by two long-running instances — the locked-database error lands inside the 1 Hz alert loop

**What goes wrong:**
The user runs two instances (Yazalaque and Faerlina) on the same machine — this is a standing fact of the project (it's why AGEN-07 exists). Both may open the World Exchange; both will write to the same DB. SQLite's defaults are hostile to this: rollback-journal mode + zero `busy_timeout` means a write colliding with the other instance's write (or a long-running read from the analysis console) raises `sqlite3.OperationalError: database is locked` immediately. If that exception escapes inside the shared 1 Hz tick, the *market* feature kills the *death-alert* core — the exact inversion of the project's priorities. Secondary Windows hazard: the DB living in a OneDrive-synced or AV-scanned folder produces sporadic mystery locks.

**Why it happens:**
SQLite works flawlessly in single-process tests; the two-instance collision only appears in the field, at 2 a.m., mid-farm — the project's canonical failure time. And Python's `sqlite3` defaults (`isolation_level` legacy behavior, no busy timeout) make the fragile configuration the path of least resistance.

**How to avoid:**
Set once, at connection open, both instances (HIGH confidence — core documented SQLite semantics):
- `PRAGMA journal_mode=WAL;` — readers never block the writer, writer never blocks readers; the two-instance read-while-write case stops being a collision at all. WAL is fine on local NTFS (it does not work on network filesystems — not this project's case).
- `PRAGMA busy_timeout=5000;` — the rare writer-writer collision waits instead of raising.
- `PRAGMA synchronous=NORMAL;` — the WAL-appropriate durability level; a power-cut loses at most the last snapshot, never corrupts.
- **One transaction per snapshot** (BEGIN … all observation rows … COMMIT): batching turns N row-writes into one lock acquisition and makes a snapshot atomic — no half-snapshot ever visible to the other instance's analysis query. Never hold a transaction across ticks.
- **All market persistence wrapped so no DB exception propagates to the scanner loop** — same doctrine as `ocr.py`'s "degrade the feature, never the product": on persistent DB failure the market feature turns itself off loudly and the death-watcher keeps running.
- DB path: local, non-synced folder; document it in config comments.
- Cross-instance duplicate work (both instances snapshot the same visible page): don't coordinate via check-then-insert (racy). Give `snapshot` a UNIQUE key (page-content hash + minute bucket) and use `INSERT OR IGNORE` — the same "exactly one wins, atomically" property `loot.py` gets from `O_CREAT|O_EXCL`, expressed in SQL.

**Warning signs:**
Any `database is locked` in the log (should be zero with the pragmas); `-wal` file growing beyond a few MB across a session (checkpoint starvation — some connection is holding a read transaction open; find the cursor that never finished).

**Phase to address:**
**Phase 3 (Persistência)** — pragmas, snapshot-transaction, UNIQUE dedup, and the exception firewall are all phase-3 acceptance criteria. Verification: an integration test spawning two writer processes hammering one DB file for 60 s with zero errors and zero lost snapshots.

---

### Pitfall 14: Writes counted as successes without checking — the recorder's sin, re-committed in new code

**What goes wrong:**
v1's exact incident, twice: `imwrite` returning `False` was announced as success, and `gravador.py` *to this day* increments `frames_gravados` without checking `cv2.imwrite`'s return. The mercado milestone multiplies the write surfaces: template cache images, debug crops, SQLite commits, snapshot counters shown in the console. Each is a fresh chance to count an attempt as an outcome. For market data the stakes are higher than for recordings: `loot.py`'s docstring states the principle — "registro perdido em silêncio é estatística errada para sempre."

**Why it happens:**
Write APIs that signal failure by return value instead of exception (`cv2.imwrite`) or that defer durability (`commit` not called, connection GC'd) make the happy path and the silent-failure path look identical in code.

**How to avoid:**
House rule for this milestone, enforced in review: **every counter counts confirmed outcomes.** `imwrite` return checked (and while in there, fix `gravador.py` — the known instance of the bug is still live); snapshot counter increments only after `COMMIT` returns; the console's "snapshots hoje: N" is a `SELECT COUNT(*)`, never an in-memory counter — the DB is the truth, the counter is a cache of it at best.

**Warning signs:**
Console counts disagreeing with `SELECT COUNT(*)`; any `cv2.imwrite(` call in a diff without its return value consumed.

**Phase to address:**
**Phase 3** for the DB counters; **Phase 1** inherits the `gravador.py` fix (it will be recording market sessions — fix the tool before relying on it for this milestone's spikes).

---

### Pitfall 15: The market reader's per-tick cost erodes the 1 Hz budget of the thing that matters

**What goes wrong:**
Sliding-window template matching of a watchlist (say 10 items × 10 rows) plus per-digit scanning of 10 price cells is orders of magnitude more compute than v1's bar measurement (3 numpy lines per member). Done unconditionally every tick, it can stretch the tick past 1 s on the user's machine — with two instances running — delaying the detection latency of death alerts, the product's core promise ("em segundos"). Slow degradation, invisible until someone measures.

**Why it happens:**
Each matcher is fast in isolation (ms); nobody sums the per-tick total across watchlist × rows × glyph positions, and the death-path and market-path share the same loop thread.

**How to avoid:**
Gate hard: the cheap panel-anchor check (one small template) is the ONLY market cost on ticks where the panel is closed — everything else runs only when the panel is confirmed open, and even then the page-hash short-circuit (Pitfall 8) skips re-reading an unchanged page. Log per-tick duration percentiles per subsystem (v1's measured-number culture — `ocr.py` keeps its cost tables in the docstring; keep the tradition). If reading a full page still threatens the budget, read it across 2-3 ticks — prices don't move at 1 Hz, deaths do.

**Warning signs:**
Tick-duration p95 rising when the market panel is open; alert latency complaints correlating with shopping sessions.

**Phase to address:**
**Phase 2** — gating and the per-tick cost log are reader-design requirements. Verification: measured tick p95 with panel open under the two-instance setup, recorded in the phase docs like every v1 measurement.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store rows as "listing events" instead of snapshot+observations | Simpler schema day 1 | Dedup becomes unsolvable retroactively; supply depth unrecoverable (Pitfall 8) | Never — this is the milestone's one-way door |
| Skip `PRAGMA user_version` + migration ladder | No migration code to write | First schema change (seller column, listing age, enchant) forces manual DB surgery or data loss on real accumulated history | Never — it's ~15 lines now |
| Parse prices with OCR instead of digit templates | No template calibration phase | Reintroduces the exact misread class v1 escaped by abandoning OCR for names; digits have the thinnest inter-class margins of any glyph set | Only as a bootstrap to label template crops during calibration |
| Single-frame reads (skip two-frame agreement) | Halves capture latency | Transition-frame plausible-wrong rows, permanent in DB (Pitfall 2) | Never — latency is irrelevant, prices don't move in 1 s |
| In-memory "already recorded" set instead of DB UNIQUE constraint | No schema thought | Breaks across restarts and across the two instances — the AGEN-07 lesson re-learned | Never in this two-instance project |
| Hardcode the panel geometry instead of calibrating | Skips calibrator work | Same as v1's banned hardcoded HSV: breaks on first layout/window change, silently | Never — `calibration.json` is the established home |
| One shared DB connection reused across console analysis and writer | Fewer connections | Long analysis reads inside the writer's connection starve WAL checkpointing (Pitfall 13 warning sign) | Fine if analysis opens its own read connection |

## Integration Gotchas

Mistakes specific to wiring the new feature into THIS system.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Death detector ↔ market panel | Two independent panel detectors (or none on the death side) — the 27x incident replays | One shared panel-open signal per tick; market reads when it fires, death logic treats it as known occlusion (Pitfall 1) |
| Scanner loop ↔ SQLite | Letting `OperationalError` escape into the tick loop | Exception firewall: market persistence failure disables the market feature loudly, never the scanner (`ocr.py` doctrine) |
| Two instances ↔ one DB | File-lock improvisation or check-then-insert dedup | WAL + busy_timeout + UNIQUE + `INSERT OR IGNORE`; disk-marker pattern (`loot.py`) only for non-relational flags |
| Calibrator ↔ template cache | Calibrator writes templates without recording window size / without a self-match + confusion-matrix check | Templates stamped with capture context; startup refuses on mismatch (Pitfall 5) |
| Console (rich Live) ↔ analysis queries | Running aggregate SQL inside the render tick | Analysis refreshes on snapshot-commit or on demand (`.preco <item>` command via the existing WhatsApp command path is a natural fit), not per render |
| Chatwoot alerts ↔ price thresholds | Price alert per snapshot → spam every time the panel opens below threshold | Reuse v1 cooldown/debounce machinery — one alert per threshold-crossing episode, exactly like one alert per death |
| Recorder ↔ market spikes | Trusting `frames_gravados` from the unfixed `gravador.py` while collecting spike evidence | Fix the imwrite check first (Pitfall 14); spike conclusions built on unverified recordings are the project's documented nightmare |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Unconditional per-tick template scan | Tick p95 creeps up; alert latency grows | Panel-anchor gate + page-hash short-circuit (Pitfall 15) | Immediately with 2 instances on one CPU |
| Snapshot per tick while user idles on a page | DB bloats with identical snapshots; analysis slows | Page-hash: new snapshot only when content changed | Hours into one shopping session |
| WAL file unbounded growth | `-wal` file tens of MB; disk churn | Short read transactions; separate read connection for console | Multi-hour farm sessions (the normal case) |
| Analysis full-table scans as history grows | `.preco` response latency grows over weeks | Index on `(item, snapshot_id)`; per-snapshot aggregates | Months of data — and this data is meant to live months (`loot.py` precedent: never pruned) |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Input-synthesis library entering the dependency tree "for a spike" | The read-only constraint dies structurally; ban risk becomes nonzero | Dependency-tree grep test failing CI on `pyautogui`/`pydirectinput`/`keyboard`/`SendInput` (Pitfall 12) |
| Market DB or debug crops in a cloud-synced folder | Locking flakiness; also leaks gameplay data | DB path in local non-synced dir, documented in config comments |
| Price-alert messages exposing full watchlist/strategy to a group chat | Party members front-run the user's trades | Threshold alerts to the user's own conversation by default, group only if explicitly configured |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Console says "preço" for visible asks | User trades on a biased number believing it's the market price | "menor pedido visível" / "mediana dos pedidos" — honest metric names (Pitfall 10) |
| Aggregates without evidence counts | "subiu 20%" from 2 snapshots reads as fact | Every number carries (n=…, última leitura …) (Pitfall 11) |
| Silent abstention (vetoed snapshots vanish) | User thinks capture is broken or thinks it worked | Console line per vetoed snapshot with reason — same visibility discipline as v1 blind mode |
| Reader silently degrading after window resize | Weeks of subtly-wrong data | Refuse + "recalibre o mercado" message (Pitfall 5) |

## "Looks Done But Isn't" Checklist

- [ ] **Digit reader:** reads clean fixtures perfectly — verify it *abstains* on a recorded scroll-transition sequence (zero accepted reads), and that grouping validation rejects a synthetically dropped separator
- [ ] **Item matcher:** matches watchlist items — verify the rejection side against a full recorded page of NON-watchlist rows (zero false accepts) and the truncated-name collision check fires in the calibrator
- [ ] **Snapshot gate:** accepts full pages — verify it *vetoes* the partial/tooltip-covered recording, and that the veto reason appears in the log
- [ ] **SQLite layer:** works single-instance — verify the two-process hammer test (60 s, zero `database is locked`, zero lost snapshots) and that a forced DB failure disables the market feature without touching death alerts
- [ ] **Counters:** console counts match `SELECT COUNT(*)` after a session; `gravador.py` imwrite return is checked (the known live bug)
- [ ] **Panel signal:** market detection works — verify the death detector consumed the same signal by replaying the 27x-incident recording with zero death flaps
- [ ] **Automation firewall:** Out of Scope entries for auto-refresh/auto-open/auto-buy exist in PROJECT.md and the input-library grep test is green

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Plausible-wrong prices already in DB | MEDIUM | Power-of-10 audit query; flag (don't delete) suspect rows via a `suspect` column; re-derive aggregates excluding flags; raw crop hashes allow pixel-level audit if crops were kept |
| Event-shaped schema shipped (no snapshots) | HIGH | Migration must *invent* snapshot boundaries from timestamps — lossy; this is why Phase 3 owns the schema decision up front |
| Unit confusion (total vs per-unit) in history | HIGH | Only recoverable if quantity was stored per row; if not, the affected item's history is unusable — mark epochs, start clean |
| `database is locked` crashes in the field | LOW | Add the three pragmas + firewall; data already committed is intact (SQLite atomicity holds) |
| Template drift after a game patch | LOW | Recalibrate (capture new templates); the window-size/margin stamps tell you *when* the break happened, bounding the tainted data range |

## Pitfall-to-Phase Mapping

Suggested phase skeleton for the roadmapper (names indicative):

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. Panel = shared occlusion signal | **F1 — Detecção do painel e calibração** | Replay 27x-incident recording: panel fires, zero death flaps |
| 3, 5, 6, 7 spikes (separator glyph, glyph touching, stack price semantics, truncation, confusion matrix) | **F1** (recorder spike, calibrator) | Recorded real pages answer each UNVERIFIED question; confusion-matrix margin documented as a measured number |
| 14 (`gravador.py` imwrite fix) | **F1** | Return value checked; counter counts confirmed writes |
| 2. Two-frame agreement | **F2 — Leitura (nomes e dígitos)** | Scroll recording produces zero accepted transition reads |
| 3, 4. Sliding-window digits, right-edge anchor, grouping validation | **F2** | Short/long number synthetic test; separator-drop rejection test |
| 7. Rejection-first item matching | **F2** | Zero false accepts on non-watchlist page |
| 9. Snapshot completeness gate | **F2** | Partial-page recording fully vetoed, reasons logged |
| 15. Tick-budget gating | **F2** | Tick p95 measured with panel open, two instances |
| 8. Snapshot-centric schema | **F3 — Persistência** | Schema review: observation rows reference snapshots; page-hash short-circuit test |
| 13. WAL/busy_timeout/txn-per-snapshot/UNIQUE/firewall | **F3** | Two-process hammer test; forced-failure test leaves scanner alive |
| 14. DB-truth counters, migration ladder (`user_version`) | **F3** | Count parity check; a v1→v2 dummy migration test |
| 6. total/unit/quantity columns | **F3** | Schema stores all three; NULL-not-guessed test |
| 10. Honest metrics, disappearance events | **F4 — Análise e console** | Console wording review; disappearance labeled as weak signal |
| 11. Evidence-carrying output, no interpolation | **F4** | Every number in console shows n and recency |
| 2 (audit side). Power-of-10 outlier query | **F4** | Query exists and runs in the health check |
| 12. Automation firewall | **F0 — Roadmap/scope definition** | Out of Scope entries written; input-library grep test green before F1 merges |

## Sources

- **This codebase (HIGH):** `l2scanner/gravador.py` (unchecked `cv2.imwrite`, counter-of-attempts — the live instance of Pitfall 14), `l2scanner/ocr.py` (two-scale agreement D-d, degrade-feature-not-product doctrine, measured-cost culture), `l2scanner/identidade.py` (closed-set template rationale, tight-crop/text-mask margins 1.000 vs 0.454, ornament re-anchoring), `l2scanner/loot.py` (two-instance O_CREAT|O_EXCL discipline, never-pruned statistics, tri-state failure handling), `.planning/PROJECT.md` (two instances as standing fact, Out of Scope pre-refusal style, read-only constraint stated twice)
- **Milestone context (HIGH, provided by orchestrator):** 27x market-panel false-positive incident; imwrite silent-failure incident; plausible-but-wrong mid-transition framing; recorder counting unverified frames
- **SQLite semantics (HIGH — established engine documentation: WAL mode, busy_timeout, synchronous=NORMAL, single-writer/multi-reader, checkpoint starvation, non-network-filesystem caveat):** sqlite.org/wal.html, sqlite.org/pragma.html (from training knowledge; behavior stable for a decade+)
- **L2 economy notation "kk" = million (HIGH — ambient community convention, corroborated by third-party adena marketplaces quoting per-kk):** [G2G L2 adena](https://www.g2g.com/categories/lineage-2-adena), [FunPay L2 Essence adena](https://funpay.com/en/chips/120/), [MMOAuctions L2 Essence](https://mmoauctions.com/lineage-2-essence/adena)
- **World Exchange UI specifics (UNVERIFIED — no public documentation for the XM Essence client found; searched 2026-08-27):** separator character, per-unit vs total display, listing-age visibility, row-slot count, right-alignment — all gated on the F1 recorder spike, listed explicitly in Pitfall-to-Phase Mapping

---
*Pitfalls research for: v1-mercado — market price capture on L2 Party Scanner*
*Researched: 2026-08-27*
