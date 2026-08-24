# Project Research Summary

**Project:** L2 Party Scanner
**Domain:** Passive screen-scanning game-state monitor (Windows 11) → outbound WhatsApp alerting via Chatwoot
**Researched:** 2026-08-24
**Confidence:** MEDIUM (HIGH on stack versions and WhatsApp/Chatwoot API constraints; the L2 client's party-window rendering was the load-bearing unknown and is now PARTIALLY RESOLVED by user testing — see Update below)

---

## ⚡ UPDATE — Gate B partially resolved by user test (2026-08-24)

**The user empirically tested out-of-range and teleport behavior after this research completed.** Result: teleporting and moving away from party members produces **no change to the party-window bars** — same color, normal fill. Distance does NOT blank or grey the HP bar.

**Impact:** The single largest project risk identified below ("out-of-range may be pixel-identical to death") is **eliminated for the range/teleport case**. The core detection rule (HP empty = death) stands. Phase 0 Gate B is reduced in scope — it no longer blocks detection design.

**New question opened by the same test (inverse failure mode):** if distant members' bars never change, is the client *updating HP live* for out-of-range members, or *freezing* the last known value? If frozen, a death that happens far away leaves the bar full forever — a **silent false negative**, which is worse than a false positive because the party believes they are covered. Test: have a distant member take damage and confirm the bar moves on the observer's screen. Mitigation if frozen: treat "bar byte-identical for N minutes" as a suspect/stale state.

**Still unresolved from Gate B:** link-dead/disconnect rendering, row-compaction on leave, and hue-shift-with-HP-level. These are cheap to capture in the same session and no longer block Phase 1.

---

## Executive Summary

This is an **alerting product wearing computer-vision clothing**. All four research tracks converged on the same conclusion from different directions: the pixel math (HSV masking, bar fill ratio) is a solved, three-line problem, while the hard parts are (a) whether the sensor's core signal is actually unambiguous, (b) whether the delivery channel can physically deliver, and (c) never crying wolf. Mature analogs in the space — Nagios, Alertmanager, Grafana, Uptime Kuma — spend the majority of their feature surface on debounce, hysteresis, inhibition, no-data states, dedup and test-notification affordances. That playbook should be adopted wholesale here, because unlike a WoW combat-log addon, our sensor is probabilistic and we own the false-positive problem ourselves. A scanner that is right 90% of the time is worse than no scanner: the party mutes the group and the one true alert is lost.

The recommended shape is a **functional core / imperative shell pipeline**: `FrameSource (port) → vision.extract (pure) → RosterResolver → Tracker FSM (pure, injected clock) → queue → Dispatcher thread → Notifier (port)`. Stack: Python 3.13 x64, `mss` for capture (not `dxcam` — see below), `opencv-python` 4.x + `numpy` 2.x for bar analysis, Windows built-in OCR via `winrt-*` bindings with `rapidfuzz` matching against a **configured roster** (never free-read), `requests` + `urllib3.Retry` for Chatwoot, `rich` for the live console, `uv` + a two-line `run.bat` for zero-ceremony launch. Config splits into human-owned `config.toml` and machine-owned `calibration.json` so the calibrator never clobbers hand-written settings. No input-synthesis library enters the dependency tree at all — that makes the read-only ban-risk invariant structural rather than a policy.

**One finding can still invalidate half the product and it is cheap to test, so it must be a Phase 0 hard gate before a line of delivery code is written.** The WhatsApp delivery path is unknown: if the user's Chatwoot inbox rides Meta's official Cloud API, business-initiated messages outside a user-opened 24-hour window require pre-approved templates, and groups are effectively unavailable — Chatwoot will return `200 OK` and Meta will silently drop the message. If it rides Evolution API/WAHA/Baileys, the constraint evaporates entirely. Prevention costs ~1 day; late discovery costs ~1 week and may force the output half to be redesigned or rechanneled.

## Key Findings

### Recommended Stack

Everything is pip-installable with no system installer, which preserves the "non-developer double-clicks `run.bat`" constraint. Versions were verified against canonical PyPI/python.org endpoints (HIGH); behavioural claims about Windows Graphics Capture and the Chatwoot→WhatsApp path are MEDIUM and spike-gated.

**Core technologies:**
- **Python 3.13.x, 64-bit** — every wheel we need exists; `numpy` 2.5 floors at 3.12, and 3.14 is where the optional OCR tail (`rapidocr`→`onnxruntime`) historically has wheel gaps. 32-bit is ruled out: WinRT/DXGI wheels are x64-only.
- **`mss` 10.2.0** — capture. Pure ctypes, zero binary deps. At 1 Hz we use ~2% of its throughput, and critically it **always returns pixels**.
- **`opencv-python>=4.14,<5` + `numpy` 2.5.2** — HSV masking, bar-fill ratio, template matching. Pin below 5: every health-bar recipe and `rapidocr`'s stated compatibility targets 4.x. Use full OpenCV, **not** `-headless` — the calibration tools need `imshow`/`selectROI`/`createTrackbar`.
- **Windows OCR (`winrt-Windows.Media.Ocr` 3.2.1 + 6 companion namespaces) + `rapidfuzz` 3.14.5** — name identification. The roster is a closed set of 4–8 known strings, so this is 4-way classification, not free-form recognition. `rapidocr` 3.9.2 is the pip-only fallback; `pytesseract` is plan C only, because its system installer contradicts the launch constraint.
- **`requests` 2.34.2 + `urllib3.Retry`** — one idempotent POST per event with backoff. `httpx`/async buys nothing here.
- **`rich` 15.0.0, `pydantic` 2.13.4, `python-dotenv` 1.2.3, `uv` 0.12.5** — live status table, fail-fast config validation, token isolation, launch without venv rituals.

**Resolved: `mss` over `dxcam` for v1.** STACK.md recommends `mss` on simplicity grounds; ARCHITECTURE.md and PITFALLS.md independently flag the `dxcam.grab()` → `None`-on-unchanged-frame trap (a static AFK party window is *exactly* that case, and a naive loop reads it as blind mode). These agree, and the conclusion is clean: **ship `mss`, which has no such semantics.** Keep `dxcam` behind a `capture_backend` config flag for the fullscreen-exclusive case only, and if it is ever enabled, it must use `new_frame_only=False` plus a `coordinate_space` field in calibration (dxcam regions are per-output `(l,t,r,b)`, not virtual-desktop). `windows-capture` (WGC) is v2 and spike-gated — its pass criterion must be *"HP values keep changing while the window is covered AND unfocused"*, not merely "a non-black frame arrived", because UE2 focus-throttling would otherwise deliver a frozen last frame forever.

### Expected Features

**Must have (table stakes) — missing any of these and the tool is switched off within one session:**
- **Named events** — "Kaus morreu", never "alguém morreu". An anonymous alert is unactionable.
- **N-consecutive-frame debounce** on death (Nagios `max_check_attempts` verbatim) and **asymmetric hysteresis** on recovery.
- **BLIND state that inhibits all dispatch**, evaluated *before* per-row checks — this is Alertmanager inhibition semantics, and ordering is a correctness property. Without it the first alt-tab produces a four-person false wipe.
- **Left-party detection via the MP-presence discriminator**, plus an independent window-level anchor.
- **Cooldown via an edge-triggered FSM** — one alert per event instance, not per tick.
- **Chatwoot POST with retry, backoff, and loud console failure** — silent delivery failure is worse than no tool.
- **`--test-alert` and `--dry-run`** — universal in the category (Datadog, Uptime Kuma, Healthchecks, Grafana all ship a test-notification button). Users will not trust an alerting tool they cannot verify before going AFK.
- **Drag-select ROI calibration persisted to config** — hand-edited pixel coordinates guarantee abandonment on the first window move.
- **Live console status block** — the pre-AFK glance check. This *is* the UI in v1.
- **Own-character HP monitoring** — the user's own death is the one they most need broadcast.

**Should have (competitive):**
- **Screenshot evidence attached to the alert** — nothing in the game-alert space does this; it makes every alert self-verifying and every false positive self-diagnosing. Requires a frame ring buffer, and should attach the frame that *started* the pending state, not the one that confirmed it. Keep the image inside Chatwoot — never upload the user's game screen to imgur/S3.
- **Resurrection alert with downtime duration** — nearly free once the death FSM exists (same edge inverted), but must use a *higher* confirmation count to exit DEAD than to enter it.
- **Frame recorder + offline replay harness** — highest-value maintainability feature; turns every real false positive into a permanent regression fixture.
- **Template-match auto-anchor** — the least painful recalibration is the one that never happens.
- **Structured JSONL event log + session summary on exit.**

**Defer (v2+):** Windows Graphics Capture background capture; autostart; chat-line OCR corroboration; WhatsApp heartbeat; wipe consolidation (unless the official-API path forces it earlier for billing reasons); per-member routing.

**Explicit anti-features:** any input injection or macro (the ban vector — enforce by keeping `pyautogui` out of the dependency tree entirely); memory reading/packet sniffing; low-HP "está morrendo" warnings (continuous threshold-crossing spam that gets the group muted); continuous per-frame OCR (both the CPU hot spot and the largest false-positive source); in-game graphical overlay (requires render hooking = ban territory); two-way WhatsApp commands; local sound alerts (the operator is AFK by premise).

### Architecture Approach

The domain has a canonical pipeline and this project should not deviate from it: **source → pure detection → decision FSM → queued delivery**, with the dependency rule pointing inward. The CORE imports no `time`, no `requests`, no `cv2.imshow`, and opens no files; it receives `Frame` + `now: float` and returns `Event`s. That single rule is what makes 30 seconds of debounce testable in 0.2 ms, and it is the difference between a project with one happy-path test and one with exhaustive coverage of the rare cases the tool exists to catch.

**Major components:**
1. **FrameSource (port)** — `grab() -> Frame`. Adapters: `MssSource`, `ReplaySource`, `SyntheticSource`, later `DxcamSource`/WGC. Isolating this now costs ~20 lines; retrofitting costs a rewrite when the capture backend must change.
2. **vision.extract + UI anchor (pure)** — `(Frame, Calibration) -> Observation`: per-slot HP/MP fill ratio, row presence, and — from an *independent* landmark on the party-window frame — `ui_visible`.
3. **RosterResolver** — resolves slot index to member identity; the only component that knows about row reshuffling.
4. **Tracker FSM (pure, injected clock)** — per-member `ALIVE/DEAD/GONE` inside a global `TRACKING/BLIND/REACQUIRE` gate; owns debounce, hysteresis and cooldown.
5. **Dispatcher (thread) + outbox + Notifier (port)** — bounded queue, append to durable JSONL *before* the POST, retry only on `ConnectionError`/`Timeout`/5xx/429 (never blind-retry 4xx), rate-limit guard as defence in depth. `--dry-run` swaps the adapter rather than sprinkling `if`s.
6. **Calibrator + Recorder (tools, outside the runtime)** — the runtime only *reads* `calibration.json`, and refuses to start if the stored screen geometry no longer matches.

Three architecture details are load-bearing and easy to lose in implementation: **BLIND freezes debounce counters rather than zeroing them** (a death 200 ms before an alt-tab must still alert on return); **REACQUIRE grants a ~2–3 s grace window** after vision returns, because the UI redraws partially and bars read zero for a frame or two; and **cooldown lives in the FSM, not the notifier** — "one alert until resurrection" is a property of *state*, not a time window.

### Critical Pitfalls

1. **~~Out-of-range / zoning / link-dead may be pixel-identical to death~~ — RANGE/TELEPORT CASE DISPROVEN BY USER TEST (see Update at top).** Distance and teleport leave the bars unchanged. Remaining sub-cases (link-dead, clean logout) still worth capturing but no longer block design. **Inverse risk now open:** frozen (non-updating) bars for distant members would cause silent missed deaths. Hedge the alert copy regardless: "HP zerado há 6s (possível morte)" survives a false positive; "MORREU" does not.
2. **The WhatsApp 24-hour session window may block every alert** — verified against Meta's primary docs. The window opens only when the *end user* messages the business; our alerts are by definition business-initiated and outside it. Official-API groups are also gated behind an Official Business Account, an 8-participant cap, and 100k+ monthly conversations — not achievable for a 4-person party. **The false-pass trap is decisive:** testing by first messaging the number opens the window and produces a misleading success. The test must use a number silent for >24h, and `200 OK` from Chatwoot is *not* delivery confirmation. **This is now the single remaining Phase 0 blocker.**
3. **Silent scanner death manufactures false confidence** — the process crashes, the window moves, or the PC sleeps; the console is hidden behind the game; the party farms on believing they are covered. This is strictly worse than no tool. Mitigate with a crash-proof main loop (an OCR exception must never kill capture), rotating file logging, a start/stop handshake message, an always-on-top liveness indicator positioned *outside* the game viewport (never an in-game overlay — that requires render hooking), and eventually an external heartbeat service to catch a frozen PC.
4. **The black-frame → total-wipe storm** — a black or corrupt frame reads as "all HP bars empty" and fires four death alerts. Guard with a mean-luminance floor that classifies as `CAPTURE_FAILED`, and keep the three capture states (`CAPTURE_FAILED` / `NO_UI` / `UI_PRESENT`) strictly separate, with detection permitted only in the third. Pair with a stale-frame check (N identical consecutive frames = frozen game, not a healthy one).
5. **DPI scaling and multi-monitor coordinates silently corrupt every crop** — the user's setup is the worst case (windowed on a second monitor at `GamePlayViewportStartX=1713`). Call `SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2)` as the literal first executable lines, in *both* the scanner and the calibrator, before importing `mss`/`cv2`. Store coordinates as signed ints (secondary monitors can be negative), and never hardcode a pixel rect in source.
6. **Red hue wraps around 0** — the HP bar needs two OR'd `inRange` masks (`H∈[0,10]` and `H∈[170,179]`). A single-range red mask is the classic cause of a bar reader "sometimes reading 0%", which here fires a false death alert.
7. **Never use `findContours` for fill measurement** — at 0% HP there is no contour, making the project's single most important event indistinguishable from "row missing". Use a fixed calibrated rect + leading-run column profile.

### Design Tension: how should member state be keyed?

Two researchers reached opposite conclusions, and the roadmap must not paper over this.

- **ARCHITECTURE.md:** key by **name**. The party window compacts rows when someone leaves, so slot 2 silently becomes the former slot 3 and Korzis's death is announced as Kaus's — a plausible, silent misattribution, the worst failure category.
- **PITFALLS.md:** key by **row index**, using OCR only as a display label. Keying on an OCR'd string means one glyph misread (`TioMad` → `T1oMad`) manufactures a phantom leave-plus-join pair and spurious alerts.

**Both are right about the failure they name, and the reconciliation is that neither OCR nor raw slot index should be the identity key.** The synthesis:

- **Row index is the within-frame tracking key.** It is stable and free between frames.
- **The user-configured roster in `config.toml` is the source of truth for identity.** The party is 4–8 known people listed in order; the mapping `slot → name` is established once at startup with zero OCR.
- **OCR is bootstrap and re-anchor only.** It runs at init and when `slot_count` or layout changes, and its output is `rapidfuzz`-matched against the closed roster before being trusted. An OCR result may never, by itself, trigger an alert.
- **When composition changes, re-anchor before naming the event.** The `left` event is emitted only after the roster has been reconciled, so it carries the correct name.

This gives ARCHITECTURE.md's correctness (events attributed to the right human even after rows compact) with PITFALLS.md's robustness (no identity drift, and the tool still works with OCR entirely absent, degrading to "Membro 2"). It also removes OCR from the critical path to first working alert, which both researchers wanted.

**The empirical fact that would settle the remaining ambiguity:** *does the L2 XM Essence party window preserve slot ordering when a member leaves, or does it compact rows?* One before/after screenshot pair answers it. If rows do **not** compact, row index alone is sufficient and the RosterResolver becomes trivial.

### Recommendation: revisit the "blind mode = console only" decision

This surfaced independently in FEATURES.md, ARCHITECTURE.md and PITFALLS.md, so it is flagged for the user rather than silently accepted. PROJECT.md currently decides that loss of vision produces no WhatsApp alert, and the reasoning is sound for the common case: alt-tabs, inventory screens and loading are constant during farming, and a naive blind alert would be the noisiest signal in the system by an order of magnitude.

But **silent coverage loss is precisely the worst failure mode in this domain** — the tool has trained the party to read silence as safety. The proposed reconciliation preserves the user's intent while closing the hole:

- Keep blind mode console-only for short blinds (the common case) — the decision is correct there.
- Add a **long-blind escalation**: if blind exceeds a generous threshold (~5 minutes), send exactly one WhatsApp message. A genuine 20-minute silent blind period defeats the product; alt-tabs never reach 5 minutes.
- On *exit* from a long blind, note it: "estive cego por 4min — pode ter perdido eventos."
- Corroborate the cause before deciding: game PID gone = game closed (say so, don't announce four departures at 2am); window minimized = known cause; window visible but landmark missing = loading/cutscene/UI hidden.
- Ship the **start/stop handshake** ("Scanner ativo — monitorando TioMad, Kaus, Korzis, J4guar" / "Scanner encerrado") regardless. This is what makes silence meaningful at all, and it costs nothing.

## Implications for Roadmap

### Phase 0: De-risking spike — WhatsApp delivery gate
**Rationale:** Gate A can invalidate the entire output half of the product, is cheap to test now and expensive to discover late (~1 day prevention vs ~1 week recovery), and requires no project code. Gate B was largely resolved by the user's own test; its residue folds into the Phase 1 recording session.
**Delivers:**
- **Gate A — WhatsApp delivery path.** Identify the provider (`GET /api/v1/accounts/{id}/inboxes` → read `channel_type`/`provider`, or Settings → Inboxes). Then run a **cold-window send test** to a number that has *not* messaged the business in >24h, and manually confirm the phone actually buzzed. Document the answer in the decision log. Branch: unofficial bridge → free-form text and group sends work, note the WhatsApp-number ban risk and use a secondary number; official API → budget a sub-phase for a **body-only** UTILITY template (header variables hit chatwoot#13851 → Meta `#132000`), drop the group requirement in favour of N 1:1 sends; neither → fall back to Telegram/ntfy/Discord and reopen the channel decision now, not in week six.
- **Gate B residue (folded into Phase 1 recording).** Capture link-dead/logout rendering, the leave-event before/after pair (row compaction), and the HP-level sweep (90/70/50/30/10/1%, to test hue shift). Plus the new live-vs-frozen check for distant members.
- **Gate C (recorded, not tested) — the safety invariant** written down as a hard architectural constraint: never inject, read memory, hook, send input, or intercept traffic. README + module docstring. Re-verified at every phase gate.

### Phase 1: Capture foundation + recorder
**Rationale:** ARCHITECTURE.md is emphatic and correct — **recording must exist before detection logic**. The target event is rare and irreproducible on demand; without ground truth every threshold change is a guess iterated against a live game. This phase also unblocks the user: they can farm with `--record` on and bank a real death while the rest is built.
**Delivers:** DPI-aware entrypoint; `mss` capture behind the `FrameSource` port; `--record` writing PNGs + `observations.jsonl`; the three-state capture model (`CAPTURE_FAILED` / `NO_UI` / `UI_PRESENT`) with black-frame luminance floor and stale-frame hashing; crash-proof main loop with rotating file logging; `.gitignore` + `.env.example` before the first commit.
**DoD:** correct crop verified at 100/125/150% scaling and after dragging the window; 60 s of a fully static screen survived without entering blind mode; zero literal screen coordinates in source.

### Phase 2: Calibration tooling
**Rationale:** Needs a recorded frame to calibrate against, and deliberately does not need the game running. With `Gamma=1.16` the correct HSV bounds are unknowable a priori.
**Delivers:** `pick_region.py` (drag-select via `cv2.selectROI`), `calibrate_hsv.py` (live trackbars), landmark/anchor selection, and a `calibration.json` carrying `schema_version` and the screen geometry it was made under. Plus a visual dump mode that draws every ROI on the frame so a human *looks at the picture* before any threshold is trusted.

### Phase 3: Vision extraction + UI anchor
**Delivers:** pure `(Frame, Calibration) -> Observation`; HSV fill-ratio via the leading-run column profile (**not** `findContours`); red-hue wraparound handled with two OR'd `inRange` masks; independent landmark anchor for `ui_visible`; golden-frame tests; a startup sanity check that refuses to run if all members read 0%.

### Phase 4: Tracker FSM + live console
**Rationale:** The heart of the product, and it is *already useful here* — it warns on screen with no network involved.
**Delivers:** per-member FSM inside the global `TRACKING/BLIND/REACQUIRE` gate; debounce, asymmetric hysteresis, edge-triggered cooldown, cold-start baseline suppression; injected clock; `rich` live status table; identity by **row index + configured roster** per the reconciliation above (no OCR yet). Exhaustive unit suite: alt-tab-during-death does not lose the alert, total wipe is not confused with alt-tab, a 5-minute corpse produces exactly one alert.

### Phase 5: Replay harness
**Delivers:** `ReplaySource` + `FakeClock` + `RecordingNotifier` over a recorded session, asserted against `events.expected.json`.

### Phase 6: Chatwoot notifier + dispatcher + outbox
**Rationale:** Low technical risk and well documented, **but its shape was decided in Phase 0**.
**Delivers:** bounded queue + daemon thread; durable JSONL outbox written before the POST; retry with jittered backoff on `ConnectionError`/`Timeout`/5xx/429-with-`Retry-After`, single loud failure on 4xx; explicit `timeout=(3,10)`; token from `.env`, never logged; pt-BR message templates with hedged copy and a local timestamp *with offset* plus relative age; `--test-alert`; `--dry-run` as an adapter swap; wipe aggregation window and a global rate cap; graceful-shutdown and game-PID-exit detection so closing the game does not announce four departures.

### Phase 7: Liveness, self-monitoring, and blind escalation
**Delivers:** always-on-top liveness indicator outside the game viewport; start/stop handshake alerts; long-blind escalation per the revisited decision above; own-character HP bar monitoring (reuses the same bar reader and FSM); `SetThreadExecutionState` so the display does not sleep mid-session; a pause hotkey with an obviously distinct paused state.

### Phase 8: OCR name labeling + screenshot evidence
**Rationale:** Deliberately last among v1 work. It is the flakiest component, and the roster-config layer makes correctness independent of it.
**Delivers:** Windows OCR via `winrt-*`, 3–4× `INTER_CUBIC` upscale **before** thresholding (documented 8.3% → 1.2% error reduction), `rapidfuzz` match against the roster; the `matchTemplate` name-crop cache as the likely-better steady state; frame ring buffer + screenshot crop attached to alerts.

### Phase Ordering Rationale

- **Recording precedes detection** because the target event is rare and irreproducible; without ground truth you are not developing, you are guessing. Unanimous across ARCHITECTURE.md and PITFALLS.md.
- **Phase 0 Gate A precedes everything** because it can force a redesign of the delivery half and is answerable in under a day.
- **Tracker precedes notifier** because the product has real value with console-only output, and because debugging detection and network simultaneously multiplies the variable count.
- **Replay precedes network** so that from Phase 5 onward every change is regression-checked.
- **OCR is last** because the configured roster removes it from the correctness path entirely.
- **The detection→transport seam is created in Phase 4, not retrofitted.** Wipe aggregation, dedup and rate limiting are impossible to add later if `send_alert()` is ever called inline from detection; the seam costs ~30 lines and is the project's most important boundary.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 0** — not conventional research but an **empirical spike with a hard gate**. Plan Gate A as an explicit deliverable with pass criteria.
- **Phase 3 (vision)** — real HSV values under `Gamma=1.16` are determinable only from a captured frame; the hue-shift question feeds directly in.
- **Phase 6 (notifier)** — needs re-planning *after* Phase 0 Gate A resolves. If the official API path is confirmed, insert a template-creation-and-approval sub-phase with external latency outside our control.
- **Phase 8 (OCR)** — Windows OCR accuracy on the L2 XM Essence font is unverifiable from documentation; a 20-minute spike against a real name crop should precede committing to the engine.
- **Any future WGC/background-capture phase (v2)** — spike first, with the pass criterion "HP values keep changing while covered AND unfocused".

Phases with standard patterns (skip `--research-phase`):
- **Phase 1 (capture)** — `mss` + DPI awareness is thoroughly documented; the traps are named and the mitigations are specified.
- **Phase 4 (tracker)** — the FSM/debounce/hysteresis/inhibition playbook is cross-corroborated across four mature alerting systems.
- **Phase 5 (replay)** — golden/replay testing is standard methodology.
- **Phase 7 (liveness)** — mechanisms are simple and fully specified in PITFALLS.md.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Versions, `requires_python` and declared deps read directly from canonical PyPI/python.org endpoints. Downgraded from HIGH because two behavioural claims — WGC occlusion behaviour and Windows OCR accuracy on the L2 font — are unverified and spike-gated. |
| Features | MEDIUM | No direct competitor exists; conclusions are drawn by analogy from four adjacent domains. The false-positive-suppression playbook is cross-corroborated across Nagios, Alertmanager, Grafana and Uptime Kuma (strong), while MMO-addon and AFK-watchdog prior art is from listing pages (weak). |
| Architecture | MEDIUM-HIGH | The pipeline shape is convergent and well established, and Chatwoot/dxcam specifics were verified against primary docs. Upgraded after the user's out-of-range test removed the largest modeling unknown. |
| Pitfalls | MEDIUM (HIGH on WhatsApp/Chatwoot) | Meta's 24-hour window and template rules were directly fetched and quoted from primary docs. Windows capture behaviour is community/issue-tracker sourced. |

**Overall confidence:** MEDIUM-HIGH — high on how to build the detection half (now that out-of-range is disproven as a confound), with one open question that determines the shape of the delivery half. Resolvable in Phase 0.

### Gaps to Address

1. ~~**How XM Essence renders out-of-range members.**~~ **RESOLVED by user test** — distance/teleport does not alter the bars.
2. **Which WhatsApp provider backs the user's Chatwoot inbox.** Determines whether templates are mandatory and whether group sends are possible. → Phase 0 Gate A, cold-window test to a >24h-silent number, manually confirmed on the phone. **Now the single blocking unknown.**
3. **Are distant members' HP bars updated live or frozen?** If frozen, deaths far from the observer are silently missed. → observe a distant member taking damage.
4. **Does the party window compact rows when a member leaves?** Settles the name-vs-index keying tension. → one before/after screenshot pair.
5. **Does the HP bar hue shift with HP level?** Determines whether hue thresholding is sound at all. → HP sweep at 90/70/50/30/10/1%.
6. **Does a party-member death produce a system-chat line?** If yes, it is an ideal corroborating signal. → observe during the recording session.
7. **Windows OCR accuracy on the L2 name font.** → 20-minute spike before Phase 8; `matchTemplate` on cached name crops is the fallback and may be strictly better.
8. **Does L2 anti-cheat (GameGuard/Frost) interact with desktop-level capture?** No source found either way. → run an extended capture session early at low stakes. Note honestly in project docs that "zero ban risk" should read "minimal risk, categorically lower than the alternatives".
9. **Does Chatwoot's configured WhatsApp flow forward media attachments?** Assumed by the screenshot-evidence feature. → confirm before committing to it; text-only fallback is to write the crop locally and reference the filename.

## Sources

### Primary (HIGH confidence)
- PyPI JSON API for all candidate packages — exact versions, release dates, `requires_python`, declared dependencies
- `devguide.python.org/versions` — Python release status
- `developers.chatwoot.com/api-reference/messages/create-new-message` — endpoint, `api_access_token` header, `message_type`, `template_params`; no documented rate limits
- Meta — WhatsApp Cloud API *Send Messages* guide — 24-hour customer service window, template requirement outside it (directly fetched and quoted)
- Meta for Developers — WhatsApp Groups API — Official Business Account requirement, 8-participant cap, 100k+ conversation gating
- Microsoft Learn — `SetProcessDpiAwarenessContext`, `Windows.Graphics.Capture`, `PrintWindow`/`PW_RENDERFULLCONTENT`
- DXcam README + GitHub — `grab()` `None` semantics, `new_frame_only`, per-output cameras, region format
- `github.com/NiiightmareXD/windows-capture` — WGC Python bindings API
- Lineage 2 User and License Agreement (4game, v10 Apr 2026) — third-party software and anti-circumvention clauses

### Secondary (MEDIUM confidence)
- Nagios Core docs (state types, `max_check_attempts`, flap detection); Prometheus Alertmanager (grouping, inhibition, silences); Grafana Alerting (pending period, No Data/Error states, best practices) — the false-positive-suppression playbook, cross-corroborated across four independent systems
- Chatwoot issues `#13851`, `#12699`, `#11789`; discussions `#12330`, `#2198`, `#7891` — template `#132000` header bug, contact→conversation→message sequence
- DXcam issues `#104` (`None` on consecutive grabs), `#31` (cv2 import order → black frames)
- OBS forums / Ryan's Blog — WGC vs BitBlt vs PrintWindow for DirectX and occluded windows; anti-cheat blocks injecting Game Capture, not Display Capture
- stb-tester — upscale-before-threshold OCR technique, 8.3% → 1.2% error reduction
- LearnOpenCV / GeeksforGeeks / `mint-lab/roi_picker` — `selectROI` and JSON-persisted ROI calibration UX
- Datadog / Dash0 / OneUptime — test-notification affordance as a category norm
- `libraries.io/pypi/winrt-Windows.Media.Ocr` — modular WinRT bindings since Sept 2023, required namespace list

### Tertiary (LOW confidence — needs validation)
- MMO death-addon listing pages (Death Alerts, DeathAlert, Deathlog, WeakAuras) — alert content expectations
- AFK watchdog projects (ED-AFK-Notifier, AFK Guard, telegram-watchdog-bot) — game→messenger pipeline shape
- OCR accuracy comparison blogs — none benchmarked on game fonts
- L2 anticheat vendor pages (SmartGuard, L2s-Guard) — vendor-adjacent, not neutral
- Healthchecks.io / Uptime Kuma comparison blogs — heartbeat patterns

### User-supplied empirical evidence (HIGH confidence for this client)
- Out-of-range / teleport party bar behavior — tested directly by the user on the live XM Essence client, 2026-08-24
- "You have left the party" system-chat message — observed by the user in-game
- Absence of any chat/event log file on disk — verified by filesystem inspection of the client install and AppData

---
*Research completed: 2026-08-24*
*Ready for roadmap: yes — conditional on Phase 0 Gate A (WhatsApp delivery) being planned as a hard gate, not a checklist item*
