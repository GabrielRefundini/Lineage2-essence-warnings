# Pitfalls Research

**Domain:** Passive screen-scanning game-state monitor (Lineage 2 XM Essence party window) with outbound WhatsApp alerting via Chatwoot, running on Windows 11
**Researched:** 2026-08-24
**Confidence:** MEDIUM overall (HIGH on WhatsApp/Chatwoot API constraints — verified against Meta and Chatwoot primary docs; MEDIUM on Windows capture; LOW on L2 client-specific UI behavior — requires empirical verification on the user's actual client)

---

## Executive Warning

Three findings dominate everything else in this document. If the roadmap addresses nothing else from this file, address these:

1. **The "out of range" problem (Pitfall 1) is unresolved and can invalidate the entire detection premise.** The project's core heuristic is "MP bar present + HP bar empty = death". If the XM Essence client blanks or greys a party member's HP bar when they are far away, zoning, or disconnected, that state is pixel-identical to death. No documentation resolves this. It must be tested on the real client **before** detection logic is written.

2. **The WhatsApp 24-hour session window may block the entire product** (Pitfall 2). Verified against Meta's official Cloud API docs: outside a 24-hour window opened *by the end user*, a business can only send **pre-approved template messages**. An unsolicited "TioMad morreu" push to an AFK party member is by definition a business-initiated message outside the window. Whether this blocks the project depends entirely on which WhatsApp provider the user's Chatwoot is wired to — an unknown that must be resolved in Phase 0.

3. **Silent death of the scanner is the worst possible outcome** (Pitfall 3). A monitoring tool that dies quietly while the user believes they are covered is strictly worse than no tool at all, because it manufactures false confidence. Everything in this domain must be built on the assumption that "no alert" is ambiguous between "nothing happened" and "I am dead".

---

## Critical Pitfalls

### Pitfall 1: "Out of range" is indistinguishable from death

**What goes wrong:**
The detection rule is `MP bar present + HP bar empty = member died`. Many MMO clients — L2 included, depending on version and UI mod — change how a party member's bars render when that member is outside broadcast/knownlist range, is loading a new zone, is in a different instance, or has disconnected but not yet timed out. Common client behaviors include: HP bar drawn empty, HP bar greyed out, the whole row dimmed while the frame stays visible, or last-known values frozen indefinitely. Any of the first three produce exactly the pixel signature the project has defined as "death".

Result: the tool blasts "Kaus morreu!" to the WhatsApp group every time Kaus runs 50 meters ahead to pull. After the third false alarm the party mutes the tool, and the one time it is right nobody reads it.

**Why it happens:**
Developers derive the detection rule from a single screenshot of a healthy party standing together, then generalize. The rule is validated against the state space they can easily observe, not against the state space the client actually produces. "Out of range" is invisible in a static screenshot — it only appears in motion.

**How to avoid:**
Run a deliberate state-capture experiment **before** writing any detection logic. Have a party member walk out of range, zone, log out, disconnect (pull the ethernet cable, not a clean exit), and actually die — capturing the party window PNG at each state. Build a labeled reference corpus of at least these 8 states per member row:

| State | HP bar | MP bar | Row frame | Name |
|-------|--------|--------|-----------|------|
| Alive, full HP | ? | ? | ? | ? |
| Alive, low HP | ? | ? | ? | ? |
| Dead | ? | ? | ? | ? |
| Out of range | ? | ? | ? | ? |
| Zoning / loading | ? | ? | ? | ? |
| Disconnected (link-dead) | ? | ? | ? | ? |
| Clean logout | ? | ? | ? | ? |
| Left party | ? | ? | ? | ? |

Fill this table with real pixel measurements. If out-of-range and dead are genuinely identical, the death signal from bars alone is unsound and the design must add a second, independent corroborating signal — most likely OCR of the system chat line, or the presence/absence of the resurrect-eligible indicator, or a "was I recently in range of this person" state machine. Decide this in the design phase, not after the first false alarm.

Additional hedge regardless of outcome: never claim certainty in the alert copy. "TioMad: HP zerado há 6s (possível morte)" is honest and survives a false positive; "TioMad MORREU" does not.

**Warning signs:**
- Detection logic written before any multi-state screenshot corpus exists
- A test plan that only covers "alive" and "dead"
- Any sentence in a plan of the form "if HP is empty then the member is dead" with no qualifier

**Phase to address:**
Phase 0 / Phase 1 — Empirical UI state characterization. This is a **prerequisite** to the detection phase, not part of it. Treat it as a spike with a hard gate: detection cannot be planned until the state table is filled in.

---

### Pitfall 2: The WhatsApp 24-hour session window blocks outbound alerts entirely

**What goes wrong:**
The project assumes "Chatwoot já está funcionando, o scanner só precisa dar POST na API." If the user's Chatwoot WhatsApp inbox is connected to the **official** WhatsApp Business Cloud API (or Twilio, or 360dialog — all of which sit on top of the official platform), then Meta's rules apply verbatim:

> "When the window closes, you can only send pre-approved template messages."
> "To message WhatsApp users outside of a customer service window, use template messages instead."
> — Meta Cloud API, *Send Messages* guide

The 24-hour timer opens **only when the end user messages or calls the business**, and resets on each new user message. An alert about a party death is a business-initiated message. If the recipient has not messaged the Chatwoot number in the last 24 hours — which is the *normal* case for an AFK party member — a free-form POST will be **rejected or silently dropped**. The tool appears to work in testing (because the developer just messaged the number while setting it up, opening a window) and fails silently in production the next day.

Two further official-API constraints compound this:
- **Chatwoot has no "send to arbitrary number" endpoint.** `POST /api/v1/accounts/{id}/conversations/{conversation_id}/messages` requires an existing `conversation_id`. Something must create or resolve the conversation first (contact + conversation creation APIs), and a conversation created by the business still does not open a customer service window.
- **Groups are effectively unavailable.** Meta's Groups API (Oct 2025+) requires an Official Business Account, caps groups at 8 participants, excludes WhatsApp Business app numbers, and is gated to businesses doing 100,000+ monthly business-initiated conversations. A 4-person Lineage 2 party will not qualify. The requirement "enviar para o grupo do WhatsApp da party" is **not achievable on the official API** and must be re-scoped to per-number 1:1 messages.

If instead the user's Chatwoot rides an **unofficial** bridge (Evolution API / WAHA / Baileys / Z-API, or the fazer.ai Chatwoot fork with native Baileys), none of the above applies: there is no 24-hour window, free-form messages work at any time, and group JIDs are addressable. The cost is that the bridge runs the unofficial WhatsApp Web protocol against WhatsApp's ToS, and account-ban risk on that number has risen sharply.

**Why it happens:**
"WhatsApp works" is treated as a solved dependency. Nobody asks *which* WhatsApp. The two possible answers have opposite architectural consequences, and the failure mode of the wrong assumption is invisible during development.

**How to avoid:**
Make provider identification the **first task of the first phase**, before any capture code. Concretely:

1. Inspect the Chatwoot inbox: Settings → Inboxes → the WhatsApp inbox → check `channel_type` / provider. Or hit `GET /api/v1/accounts/{id}/inboxes` and read `channel_type` and `provider` — `whatsapp` + `whatsapp_cloud`/`360dialog`/`twilio` means official; an API-channel inbox fed by Evolution/WAHA means unofficial.
2. Run a **cold-window send test**: pick a number that has not messaged the business in >24h and attempt a plain-text outgoing POST. Do not test with a number you just chatted with — that is the exact test that produces a false pass.
3. Branch the design on the result:
   - **Unofficial bridge** → free-form alerts, group sends work, no template machinery needed. Note the ban risk on the WhatsApp number in the risk register.
   - **Official API** → you must pre-register a UTILITY template (e.g. `l2_party_alert` with body `Alerta L2: {{1}} — {{2}} às {{3}}`), send via `template_params`, accept template approval latency and per-message cost, and drop the group requirement in favor of N individual sends. Budget an entire sub-phase for template creation and approval.
   - **Neither works** → fall back to a channel the project controls: a Telegram bot, ntfy.sh, Discord webhook, or Chatwoot's own web widget. Better to discover this in week one than in week six.

Also guard the known Chatwoot bug: templates with a required **header** named parameter fail with Meta error `#132000` because Chatwoot posts an empty `processed_params` (chatwoot/chatwoot#13851). **Design the template with a body-only structure — no header media, no header variables.** This sidesteps the bug entirely.

**Warning signs:**
- Any plan that says "POST to Chatwoot" without naming the provider
- Successful manual test messages sent to a number you were just chatting with
- HTTP 200 from Chatwoot with the message never arriving on the phone (Chatwoot accepts the message into its DB and the provider rejects it downstream — **200 is not delivery confirmation**)
- No delivery-status check anywhere in the design

**Phase to address:**
Phase 0 — Integration spike. Hard gate. Nothing else should be built until a real alert has landed on a real phone that has been silent for 24+ hours.

---

### Pitfall 3: The scanner dies silently and the party believes they are covered

**What goes wrong:**
The Python process crashes on an unhandled exception, the game window gets moved and the crop region now points at empty UI, the capture library starts returning `None`, Tesseract's binary path breaks after a Windows update, or the machine sleeps. The console window is behind the game and nobody looks at it. The party continues farming under the belief that deaths will be announced. Nothing is announced. Someone dies, stays dead for 40 minutes, and the tool's *entire value proposition* silently evaporated hours earlier.

This is the single worst outcome in the alerting domain: **absence of alert is ambiguous**, and the tool has trained its users to interpret silence as safety.

**Why it happens:**
Monitoring tools are built to detect *events*. Nobody builds the meta-monitor that detects the absence of the monitor. The developer's mental model is "it either works or I'd notice", which is false when the UI is a console window hidden behind a fullscreen game.

**How to avoid:**
Design silence out of the system. Four mechanisms, in priority order:

1. **Always-visible liveness indicator.** A small always-on-top Tk/PySide overlay window (green pulsing dot + last-successful-frame timestamp + per-member state) positioned outside the game viewport. The user must be able to confirm "it's alive" with a glance, without alt-tabbing. This is the highest-value UX decision in the project and it is cheap.
2. **Startup handshake alert.** On start, send one WhatsApp message: "Scanner L2 ativo — monitorando TioMad, Kaus, Korzis, J4guar." The party now knows coverage started. On clean shutdown (Ctrl-C / window close), send "Scanner L2 encerrado." Silence now means something.
3. **Heartbeat / dead-man's switch.** Periodic "still watching" — but do **not** send it to WhatsApp (that is spam and, on the official API, expensive). Write a heartbeat file with a timestamp, and/or ping a free external heartbeat service (healthchecks.io, cronitor). If the ping stops, the external service alerts. This is the only mechanism that catches "the whole PC froze".
4. **Crash-proof main loop.** Every iteration wrapped in try/except that logs and continues. An exception in OCR must never kill capture. An exception in the Chatwoot POST must never kill detection. Log to a rotating file, not just stdout — stdout in a closed console is gone forever.

Explicitly reject the temptation to skip this as "v2 polish". A monitoring tool without liveness signalling is not a smaller version of the product — it is a *different, worse* product that lies to its users.

**Warning signs:**
- The only status output is `print()` to a console window
- The main loop has no top-level exception handler
- No answer to "how would the user know if it stopped 20 minutes ago?"
- Log lines only on events, never on healthy ticks

**Phase to address:**
Phase 1 (crash-proof loop + file logging) and Phase 2 (visible liveness overlay + start/stop handshake alerts). Heartbeat service is Phase 3 or v2.

---

### Pitfall 4: DPI scaling and multi-monitor coordinates silently corrupt every crop

**What goes wrong:**
The user's setup is exactly the worst case: **windowed game at 1718x1360 on a second monitor** (`GamePlayViewportStartX=1713`). Two independent coordinate hazards apply.

*DPI:* a Python process is non-DPI-aware by default on Windows. `GetWindowRect` then returns **logical** (scaled) coordinates while `mss`/`dxcam` capture buffers are in **physical** pixels. At 125% scaling — a very common Windows 11 default on high-res laptop panels — every crop is off by 25%, and the "HP bar" region is actually sampling the MP bar or the row below. The bug does not throw; it just returns wrong colors forever.

*Multi-monitor:* on a virtual desktop, a secondary monitor positioned left of or above the primary has **negative** `left`/`top` values. `mss.monitors[0]` is the union of all monitors and its origin is not `(0,0)`. Code that assumes non-negative coordinates or that indexes `monitors[1]` expecting "the second monitor" (it is the *first*) crops the wrong screen.

**Why it happens:**
Both failures are silent. A wrong crop returns a valid image of the wrong thing. The developer tunes color thresholds against that wrong region, gets them "working", and has now baked the coordinate bug into the calibration.

**How to avoid:**
- Call `ctypes.windll.shcore.SetProcessDpiAwareness(2)` (or better, `SetProcessDpiAwarenessContext` with `PER_MONITOR_AWARE_V2`) as the **very first lines of the program**, before importing/initializing any capture or UI library. This is one line and eliminates an entire bug class.
- **Never hardcode absolute screen coordinates.** Locate the game window by title via `pygetwindow`/`win32gui`, read its rect, and express all regions of interest as **fractions of the client area**, not pixels. A window moved 200px right must not break anything.
- Add a `--calibrate` mode that dumps the captured crop of each region of interest to PNG with the bounding boxes drawn on. The developer and user *look at the picture* before trusting a single threshold. This is a 30-line tool that will save days.
- Guard on every tick: if the located window rect differs from the calibrated rect (moved/resized), **either re-derive the regions or enter blind mode and say so loudly** — do not keep scanning stale coordinates.

**Warning signs:**
- Literal pixel coordinates in source (`region = (1713, 240, 1900, 400)`)
- No DPI-awareness call anywhere
- Color thresholds that needed "weird" tuning to work — a strong signal you are sampling the wrong region
- The tool works on the dev's monitor arrangement and nowhere else

**Phase to address:**
Phase 1 — Capture foundation. The `--calibrate` visual dump is part of the definition-of-done for this phase.

---

### Pitfall 5: Black frames, stale frames, and `grab()` returning `None`

**What goes wrong:**
Three distinct capture failures that all look like "the party window disappeared", i.e. all trigger the project's blind mode or, worse, look like everyone left the party at once.

- **`dxcam.grab()` returns `None` when no new frame arrived since the last call.** During AFK farming the screen can be nearly static; a 1 Hz poller will get `None` frequently. Naive code reads `None` as "no vision" and either goes blind constantly or crashes on `None.shape`. (DXcam issue #104.)
- **Black frames.** Desktop Duplication cannot capture most fullscreen-**exclusive** D3D apps. `BitBlt`/`GetDC` on a minimized or hidden window returns black because there are no pixels. `PrintWindow` without the `PW_RENDERFULLCONTENT` (0x2) flag returns black for DirectX/DWM-composited content. Also documented: importing OpenCV before dxcam can produce black frames (DXcam issue #31) — import order matters.
- **Stale frames.** Some paths return the last good frame indefinitely after the source stops updating. The scanner then reports a frozen game as perfectly healthy — the exact inverse of the failure you want.

**Why it happens:**
Capture libraries are chosen for FPS benchmarks, not for their failure semantics. The docs lead with "240 FPS"; the `None`-on-unchanged-frame behavior is a footnote. Nobody tests the capture layer against a *degraded* source.

**How to avoid:**
- Use `camera.grab(new_frame_only=False)` — or better, drive dxcam in `start()`/`get_latest_frame()` mode which blocks for a real frame. Never treat `None` as evidence about game state; treat it as evidence about the *capture layer* and retry.
- **Separate three distinct conditions in code and never conflate them:**
  1. `CAPTURE_FAILED` — no frame / black frame / exception → capture problem, retry, escalate to user after N consecutive
  2. `NO_UI` — valid frame but party window not found → blind mode (loading, alt-tab, UI collapsed)
  3. `UI_PRESENT` — valid frame, party window found → the only state in which detection is allowed to run
  Only state 3 may produce death/leave alerts. This three-way split is the single most important structural decision in the detection design.
- **Detect stale frames** by hashing the frame (or a cheap checksum of a region that always animates, like the game clock or an HP number). N identical consecutive frames = game frozen or capture stalled → alert the user locally, do not report party state.
- **Black-frame guard:** if mean luminance of the game region is below a floor, classify as `CAPTURE_FAILED`, not as "everyone's HP is zero". Without this guard, a black frame reads as "all HP bars empty" — a *total party wipe alert storm* caused by a capture glitch. This is the most dangerous single failure in the project.
- Prefer **Windows.Graphics.Capture** (Win10 1803+) for per-window capture as the eventual target; it handles occluded/background windows and does not inject. Given the game runs windowed and visible, plain Desktop Duplication cropped to the window rect is the correct v1 choice — but write the capture layer behind an interface so the backend can be swapped without touching detection.
- Keep the game in **windowed or borderless windowed**, never fullscreen-exclusive. Document this as a hard operating requirement for the user.

**Warning signs:**
- `frame.shape` accessed without a `None` check
- No luminance floor check
- No frame-identity/staleness check
- "Everyone died simultaneously" appearing even once in testing

**Phase to address:**
Phase 1 — Capture foundation, with the three-state model as an explicit deliverable.

---

### Pitfall 6: Color thresholds tuned once, brittle forever

**What goes wrong:**
The HP bar is not a clean rectangle of one red. Reality includes: the client's `Gamma=1.16` shifting every value; damage flash overlays; buff/debuff icons and party-leader marks drawn over or adjacent to the row; targeting highlight tinting the row; semi-transparent UI letting the game world bleed through the bar; anti-aliased bar edges producing intermediate colors; and — critically — many MMO HP bars **change hue with HP level** (green→yellow→red, or red→dark red). A threshold calibrated on "red = alive" silently inverts meaning if the bar turns orange at 40%.

Then the user changes their in-game gamma, or a patch retextures the UI, and the tool is 100% wrong with no error message.

**Why it happens:**
Thresholds are tuned against one screenshot in one lighting condition and never revalidated. The tuning process feels like success ("it works!") which suppresses the instinct to test adversarially.

**How to avoid:**
- **HSV, not RGB** — already a good decision in PROJECT.md. Threshold primarily on **Hue** (stable under gamma/brightness) with generous Saturation/Value bands, rather than on absolute RGB values.
- **Measure fill fraction, not presence of color.** The signal should be "what fraction of the bar's length is filled", computed as the position of the fill/empty boundary along the bar's long axis. This is far more robust than counting red pixels, and it naturally survives hue shifts if you threshold on "saturated vs. dark background" rather than "is it red".
- **Sample a line, not a blob.** Read a 1-3px horizontal strip through the vertical center of the bar, and take the **median** along the strip's short axis. This rejects icon overlays and damage flashes that cover only part of the bar height.
- **Inset the sample region** from the bar's edges by a few pixels to skip anti-aliased borders and the frame.
- **Verify the "bar shifts color with HP" hypothesis explicitly** during the Pitfall 1 state-capture experiment. Have someone take damage down through 90/70/50/30/10/1% and record the hue at each level. If hue shifts, the detector must accept a hue *range*, and "empty" must be defined by *absence of any saturated fill*, not by absence of red specifically.
- **Store calibration in a config file, not in code**, and version it. When the game patches, recalibration is editing a JSON, not a code change.
- **Add a self-check on startup:** with the party alive, all HP fill fractions should be > 0. If any member reads 0% at startup, the calibration is probably wrong — refuse to start and tell the user to recalibrate, rather than immediately alerting four deaths.

**Warning signs:**
- Magic RGB tuples in source
- Thresholds that were arrived at by trial-and-error and are not explainable
- No test against screenshots taken at different gamma settings
- Detection accuracy that varies by zone (different background bleeding through transparent UI)

**Phase to address:**
Phase 2 — Detection logic, with calibration externalized to config as a definition-of-done item.

---

### Pitfall 7: Alert storms — the wipe scenario

**What goes wrong:**
A party wipe is the *most important* event and the one most likely to break the alerting. Four members die within 3 seconds. The naive implementation fires four separate WhatsApp messages. If the party is 8 members, eight. If a re-detection bug causes flapping (HP reads as 0, then as 5%, then 0), each transition fires again. On the official WhatsApp API this also burns four billable conversations and may hit provider rate limits, causing *some* alerts to be dropped — which means the tool is loudest exactly when it is least reliable.

Related flavors of the same bug:
- **Flapping.** HP hovering at the threshold boundary (a member being healed at 1-2% during a fight) oscillates the state and produces a contradictory alert stream.
- **Duplicate alerts.** A dead member stays dead. Without a latch, the "HP is 0" condition is true on every tick forever, generating an alert per tick.
- **Restart amplification.** The user restarts the scanner; state resets; everyone currently dead is re-reported as freshly dead.
- **Intentional shutdown.** The user closes the game to go to bed. The party window vanishes. Without distinguishing intentional exit from crash, the tool announces four departures at 2am.

**Why it happens:**
Alerting is treated as a per-event function call rather than a state machine with rate control. The wipe case is rarely tested because it is hard to stage.

**How to avoid:**
- **Model each member as an explicit state machine** — `ALIVE → SUSPECT_DEAD → DEAD → RESURRECTING → ALIVE`, plus `LEAVING → LEFT` and a global `BLIND` state that freezes all transitions. Alerts fire only on specific *edges*, never on state presence. This structurally eliminates duplicate alerts.
- **Hysteresis with asymmetric thresholds.** Death confirms only after N consecutive frames with fill < 1% (project says N frames — good). Recovery/resurrection requires fill > 5% for M frames. Different thresholds for entering and leaving a state is the standard cure for flapping.
- **Aggregation window.** Buffer alerts for 3-5 seconds before sending. If ≥3 members enter DEAD within the window, send **one** message: "WIPE — TioMad, Kaus, Korzis e J4guar morreram." One message, correct semantics, one billable conversation. This is not an optimization; it is the correct behavior.
- **Global rate cap.** Hard ceiling of e.g. 1 message per 10 seconds and N per hour, with overflow collapsed into a summary. Protects against both provider rate limits and a runaway bug.
- **Graceful shutdown detection.** Catch `SIGINT`/console-close and set an `INTENTIONAL_SHUTDOWN` flag before the party window disappears. Also: if the *game process* exits (check via `psutil` for the client PID), that is a clean "game closed", not a party wipe. Checking that the game process is still alive is a cheap and highly diagnostic signal the project should use everywhere — it disambiguates "game crashed" from "UI hidden" from "everyone left".
- **Cold-start suppression.** On startup, observe for K seconds and treat whatever it sees as the *baseline*, alerting only on changes from baseline. Someone already dead when the scanner starts is not news.

**Warning signs:**
- `send_alert()` called directly from the detection function
- No buffering layer between detection and transport
- Wipe scenario absent from the test plan
- No state machine — just `if hp == 0: alert()`

**Phase to address:**
Phase 3 — Alerting layer, built as a separate module with its own state machine and rate control, decoupled from detection.

---

### Pitfall 8: OCR of party member names is unreliable and over-trusted

**What goes wrong:**
Tesseract is poor at exactly the input this project feeds it: small, stylized, anti-aliased text over a semi-transparent, non-uniform background. It expects ~300dpi clean scans; game UI text is ~72dpi and anti-aliased. Expect confusions among `I/l/1`, `O/0`, `rn/m`, `5/S`, `8/B`. Lineage 2 names commonly contain mixed case, digits, and stylistic characters that amplify this.

The failure is not just a garbled name in a message — it is **identity drift**. If the OCR reads `TioMad` as `T1oMad` on the re-scan after a composition change, the tool believes a new member joined and the old one left, and fires spurious alerts. Names are also **truncated** by the UI when long, so the OCR string is not even the true name.

**Why it happens:**
OCR is trusted as an identity key because it returns a string and strings feel authoritative. The correct mental model is that OCR returns a *noisy observation*, not an identity.

**How to avoid:**
- **Decouple identity from OCR entirely.** The stable identity of a party member is their **row position** in the party window, not their name. Track state by row index. OCR is used only to attach a human-readable label to a row for the message text. If OCR fails, the tool still works and says "Membro 2 morreu" — degraded, not broken. This is the single most important design decision around OCR.
- **Anchor to a known roster.** Ask the user to enter the party's real names once (config file or a startup prompt). Then OCR output is **fuzzy-matched** (Levenshtein / `rapidfuzz`) against that small known set. Matching `T1oMad` to `TioMad` from a 4-name candidate list is trivially reliable; free-form recognition is not. This converts an open-vocabulary OCR problem into a 4-way classification problem.
- **Preprocess correctly: upscale *before* thresholding.** This is the highest-leverage OCR technique for screen text — it preserves anti-aliasing information until outline extraction. Documented error-rate improvement from 8.3% to 1.2%. Upscale 3-4x with `INTER_CUBIC`, then binarize.
- Use `--psm 7` (single text line) or `--psm 8` (single word), not the default full-page segmentation, and set `tessedit_char_whitelist` to the alphanumeric set the game actually permits.
- **OCR sparingly** — PROJECT.md already decided this (init + composition change only). Good. Add: also re-OCR on demand via a hotkey, and never let an OCR result *by itself* trigger an alert.
- Consider **skipping Tesseract for v1 entirely.** Row index + user-supplied roster covers 100% of the alerting requirement. OCR then becomes an optional enhancement rather than a critical path dependency with an external binary that can break on any Windows update. Seriously evaluate deferring it.

**Warning signs:**
- Member state dictionary keyed by OCR string
- No roster config; names discovered purely from pixels
- Tesseract invoked on the raw crop with no upscaling
- A plan where "OCR fails" has no defined degraded behavior

**Phase to address:**
Phase 2 (row-index identity model — the correct foundation) and Phase 4 (OCR name labeling as an enhancement). OCR should **not** be on the critical path to first working alert.

---

### Pitfall 9: Blind mode is too coarse, or not coarse enough

**What goes wrong:**
PROJECT.md correctly requires a blind mode when the party window vanishes. Two symmetric failure modes:

*Too permissive:* the blind check is "is the party window region entirely absent" — but a **loading screen** or **cutscene** may partially match, or a semi-transparent overlay may leave enough of the frame visible to pass the "UI present" check while the bars underneath are garbage. Result: a teleport produces a full-party death alert.

*Too aggressive:* the blind trigger is oversensitive and the tool spends most of its time blind, silently covering nothing. Since blind mode is (per PROJECT.md) console-only with no WhatsApp alert, the user has no idea their coverage went to zero. This is Pitfall 3 wearing a different hat.

*Also missed:* the user **collapses or hides the party window** with a hotkey, or drags it. The tool goes blind permanently and nobody notices.

**Why it happens:**
Blind mode is designed as a single boolean derived from one check. Real occlusion has many causes with different correct responses.

**How to avoid:**
- **Anchor on a stable UI landmark**, not on the bars themselves. Find a distinctive fixed element of the party window frame (a corner texture, the window border, a class icon slot) via template matching (`cv2.matchTemplate`). "Landmark found at expected position" is the gate for `UI_PRESENT`. This is far more robust than inferring presence from the bars you are trying to measure.
- **Require positive confirmation, not absence of negative.** Detection runs only when the landmark match score exceeds a confidence floor. Anything else is blind. Fail closed.
- **Track and surface time-in-blind.** If blind exceeds ~30 seconds, escalate the console message and flash the liveness overlay. If it exceeds a few minutes, this is worth breaking the "no WhatsApp alert for blindness" rule — reconsider that scoping decision with the user, because a 20-minute silent blind period defeats the product. At minimum, on *exit from* blind mode after a long gap, the tool should note "estive cego por 4min — pode ter perdido eventos."
- **Corroborate with the game process.** If the game PID is gone → game closed (not blind). If the game window is minimized → known cause. If the game window is visible but the landmark is missing → loading/cutscene/UI hidden. Different causes, different messages.
- **Never emit party-state alerts on the blind→visible transition.** Re-baseline instead: on regaining vision, adopt the observed state as the new baseline and alert only on subsequent changes. Without this, every zone load produces a burst of phantom events.

**Warning signs:**
- Blind detection based on "are there no red pixels"
- No landmark/template anchor
- No timer on blind duration
- Alerts firing immediately after a loading screen

**Phase to address:**
Phase 2 — Detection logic. Blind mode and the three-state capture model (Pitfall 5) should be designed together as one coherent state model.

---

### Pitfall 10: Terms-of-service and ban-risk assumptions taken on faith

**What goes wrong:**
The project's founding safety argument — "screen reading = zero ban risk" — is *directionally right but stated too strongly*. Lineage 2's User and License Agreement prohibits unauthorized third-party software that modifies the game experience, grants unfair advantage, or interferes with the service, and prohibits circumventing security/authentication technology (Frost). The client ships anti-cheat (GameGuard historically, Frost more recently) whose detection heuristics are undocumented and change without notice. Anti-cheat systems are known to block screen-capture tools when those tools **inject into the game process** (this is why OBS *Game Capture* is blocked by GameGuard/EAC while OBS *Display Capture* is not).

The real risk is not the current design — it is **scope creep into risk**. The moment someone adds "and auto-clicks the resurrect button" or "reads the HP from memory for accuracy," the risk profile changes categorically and irreversibly.

**Why it happens:**
The safety property is treated as an attribute of the project rather than an invariant that must be actively defended against future changes.

**How to avoid:**
- **Write the invariant down as a hard architectural constraint**, not a preference: *this software never injects into, reads memory from, hooks, sends input to, or intercepts network traffic of the game client. It reads the framebuffer of the desktop and nothing else.* Put it at the top of the README and in the code as a module-level docstring.
- **Choose the capture backend accordingly:** Desktop Duplication and Windows.Graphics.Capture read at the desktop/DWM level and do not touch the game process — the equivalent of OBS Display Capture. Avoid any approach requiring a hook or overlay injected into the game.
- Keep the liveness overlay (Pitfall 3) as a **separate top-level window positioned outside the game viewport**, never an in-game overlay. In-game overlays are drawn by hooking the render pipeline — exactly the thing anti-cheat blocks and the ToS prohibits.
- **Verify empirically at low stakes.** Run the capture loop for an extended session and confirm the client does not complain, before building the rest on top of it. If GameGuard/Frost objects to Desktop Duplication at all, better to know on day one.
- **Note honestly:** no source was found stating that screen reading is *explicitly permitted*. The design is defensible and categorically far safer than memory reading or input automation, but "zero risk" should be softened to "minimal risk, categorically lower than the alternatives" in the project's own documentation. Also relevant: private/unofficial servers set their own rules and may be stricter.
- **Secondary ToS risk:** if Chatwoot rides an unofficial WhatsApp bridge (Pitfall 2), the *WhatsApp account* carries real ban risk. Do not use the user's primary personal number for it.

**Warning signs:**
- Any proposal involving `ReadProcessMemory`, DLL injection, an in-game overlay, `SendInput`, or packet capture
- Framing the safety property as "we probably won't get banned" rather than as an enforced invariant
- A capture backend chosen for FPS that happens to require a game hook

**Phase to address:**
Phase 0 — recorded as an architectural constraint in the project's decision log; re-verified at every phase gate when new features are proposed.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded pixel coordinates for the party window | Working prototype in an hour | Breaks on any window move, resolution change, or DPI change; silently reads wrong pixels rather than erroring | Only inside a throwaway spike that is deleted, never in `main` |
| Alert sent directly from detection code (no queue/state machine) | One less module | Makes wipe aggregation, dedup, and rate limiting impossible to retrofit; every fix becomes a rewrite of detection | Never — the seam costs ~30 lines and is the project's most important boundary |
| Skipping the visible liveness overlay ("console is enough") | Saves a day | The tool can die silently and nobody knows — destroys the product's core value proposition | Never for a monitoring tool; this IS the product |
| Member state keyed by OCR'd name string | Human-readable debug output | Identity drift from a single glyph misread produces phantom join/leave alerts | Never — key by row index, label with OCR |
| Testing WhatsApp delivery only with a number you just messaged | Fast green test | Masks the 24-hour-window blocker completely until production | Never — this is the specific test that produces a false pass |
| Treating HTTP 200 from Chatwoot as delivery confirmation | Simple code | Messages accepted by Chatwoot and rejected by the provider are invisible; you believe you alerted and did not | Acceptable in v1 only if paired with a manual "did you get it?" check during the Phase 0 spike |
| Color thresholds as literals in source | Fast iteration during tuning | Every game patch, gamma change, or UI mod requires a code change and redeploy | Acceptable during the tuning spike; must be externalized to config before Phase 2 is done |
| No structured event log (console prints only) | Less code | Post-mortem debugging of "why didn't it alert when X died" is impossible; no way to tune thresholds from real data | Never — a rotating JSONL event log is ~15 lines and is the only way to improve accuracy over time |
| Tesseract on the critical path for v1 | "Complete" feature set | External binary dependency, brittle on stylized fonts, blocks first working alert on a hard problem | Never for v1 — ship row-index + roster config, add OCR later |
| Polling at high frequency to "not miss anything" | Feels more responsive | CPU contention with the game (which the user is actively playing); more frames = more chances to catch a transient artifact and false-positive | 1-2 Hz is correct for this domain; higher needs justification |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Chatwoot + official WhatsApp Cloud API | Sending free-form text and assuming it delivers | Outside the 24h user-initiated window only **pre-approved templates** deliver. Register a UTILITY template with a **body-only** structure and send via `template_params`. Verified against Meta docs. |
| Chatwoot template messages | Using a template with a header variable or header media | chatwoot/chatwoot#13851: Chatwoot posts empty `processed_params` for required header named params → Meta error `#132000`. Design body-only templates to sidestep entirely. |
| Chatwoot message API | Assuming a "send to phone number" endpoint exists | The endpoint requires an existing `conversation_id`. You must resolve/create contact → conversation first. Cache the mapping `phone → conversation_id` in config. |
| WhatsApp groups | Planning to post to the party's WhatsApp group via the official API | Not viable: Groups API needs an Official Business Account, caps at 8 members, and is gated to 100k+ monthly business-initiated conversations. Re-scope to N individual 1:1 sends, or use an unofficial bridge (accepting ban risk on the number). |
| Chatwoot rate limits | Assuming Chatwoot documents its limits | It does not — the API reference lists none. The real limits come from the downstream provider (Meta tiering / Twilio / 360dialog). Implement client-side rate limiting defensively regardless. |
| Chatwoot HTTP response | Treating `200 OK` as "the party member's phone buzzed" | 200 means Chatwoot accepted the message into its DB. Downstream provider rejection is asynchronous. Poll message status or subscribe to a webhook if delivery confirmation matters. |
| Chatwoot API token | Hardcoding `api_access_token` in the script | Env var or a gitignored config file. A leaked token gives full write access to the user's customer-communication platform. |
| dxcam / Desktop Duplication | Calling `grab()` and treating `None` as "screen is gone" | `None` means "no new frame since last call". Use `grab(new_frame_only=False)` or `start()`/`get_latest_frame()`. Never infer game state from `None`. |
| dxcam + OpenCV | Importing cv2 before dxcam | Documented black-frame interaction (DXcam issue #31). Fix import order; verify with a visual dump on startup. |
| `mss` multi-monitor | Assuming `monitors[1]` is the second monitor, or that coordinates are non-negative | `monitors[0]` is the all-monitor union; `monitors[1]` is the **first** monitor. A left/top-positioned secondary monitor yields negative coordinates on the virtual desktop. |
| Win32 `GetWindowRect` | Calling it from a non-DPI-aware Python process | Returns logical (scaled) coords while capture buffers are physical pixels. Call `SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2)` before anything else. |
| `PrintWindow` (if used for window capture) | Calling without flags on a DirectX window | Returns black. Requires `PW_RENDERFULLCONTENT` (0x2) on Win8.1+. Better: use Windows.Graphics.Capture. |
| Tesseract | Feeding it the raw small crop | Upscale 3-4x **before** thresholding (8.3% → 1.2% error), use `--psm 7/8`, set a char whitelist, fuzzy-match against a known roster. |
| Windows power management | Ignoring it | The PC sleeping or the display turning off kills capture. Call `SetThreadExecutionState(ES_CONTINUOUS \| ES_DISPLAY_REQUIRED)` while the scanner runs, and restore on exit. |

---

## Performance Traps

Scale here is tiny (one machine, ~8 rows, ~1 Hz). The traps are about **contention with the game**, not throughput.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Capturing the full desktop every tick, then cropping | Elevated CPU/GPU use; user notices FPS drop and blames the scanner; scanner gets uninstalled | Capture only the party-window sub-region (`dxcam` supports a `region` argument). Capture cost scales with pixel count. | Immediately noticeable on a machine already GPU-bound by the game |
| Running OCR on every frame | 100% of one core pinned; game stutters; alert latency climbs | OCR only on init and on detected composition change (already the plan — hold the line on it) | At >0.2 Hz OCR on a 4-8 row window |
| Synchronous HTTP POST inside the detection loop | Detection stalls for the duration of the request; a Chatwoot timeout freezes monitoring for 30s and events are missed during the freeze | Alert dispatch on a separate thread with a bounded queue; detection never blocks on I/O. Set an explicit `requests` timeout (never rely on the default). | The first time the network hiccups — guaranteed to happen |
| Unbounded in-memory frame history for debugging | Memory grows until the process is killed by the OS during a long farm session | Ring buffer of N frames (e.g. last 10), or write debug frames to disk with rotation | Multi-hour sessions — i.e. the actual use case |
| No log rotation | Disk fills over a long session; writes fail; scanner dies (silently — see Pitfall 3) | `RotatingFileHandler` with a size cap | Long unattended sessions |
| Polling faster than the game renders | More CPU, more duplicate frames, more `None` returns, no additional information | 1-2 Hz is correct. Death detection latency is dominated by the debounce window, not the poll rate. | Any rate above ~5 Hz is pure waste for this problem |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Chatwoot `api_access_token` committed to the repo or pasted in the script | Full write access to the user's customer-communication platform; a leaked token lets anyone message their WhatsApp contacts as them | Env var or gitignored `config.local.json`. Add a `.gitignore` entry before the first commit, not after. |
| Party members' phone numbers in a committed config file | Doxxing real people who did not consent to being in a repo | Keep the roster (names ↔ numbers) in a gitignored local config; ship a `config.example.json` with placeholders |
| Screenshots with the game UI committed as test fixtures | Leaks character names, guild, location, account state; potentially the user's real IP/region via UI elements | Crop fixtures to just the bars; scrub names; keep an eye on what a "helpful debug screenshot" reveals |
| Using an unofficial WhatsApp bridge on the user's primary personal number | WhatsApp bans the number; the user loses their personal WhatsApp account, not just the tool | If an unofficial bridge is used, use a dedicated secondary number. Make this an explicit, documented decision. |
| Sending alerts to people who did not opt in | Unsolicited messaging; on the official API this is also a policy violation that can get the WhatsApp Business account restricted | Explicit opt-in per party member, and a documented way to opt out. On the official API, the recipient must be a real contact. |
| Alert content containing more than necessary | Party location/composition leaked into a group chat that may include people outside the party | Alert body should be minimal: who, what, when. No coordinates, no loot, no zone. |
| Running the scanner as Administrator "to make capture work" | Unnecessary privilege escalation on a machine running an anti-cheat-protected game and third-party code | Desktop Duplication does not need admin for a normal desktop session. If something seems to require it, that is a signal the approach is wrong. |
| No timeout on the Chatwoot request | A hung connection blocks a thread indefinitely; combined with no retry cap this is a resource leak | Explicit `timeout=(3, 10)` on every `requests` call, with bounded exponential backoff |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Status only in a console window hidden behind a fullscreen game | The user cannot tell if the tool is alive without alt-tabbing out of combat — so they never check, and never notice it died | Always-on-top mini overlay outside the game viewport: green/red dot, last frame time, per-member state |
| Alerts that assert certainty ("TioMad MORREU") | One false positive destroys trust in every future alert; the party mutes the tool | Hedge the language: "TioMad: HP zerado há 6s (possível morte)". Honest uncertainty survives a false positive; false certainty does not. |
| No timestamp, or an ambiguous one, in the alert | An AFK member reads the message 15 minutes later and cannot tell if it is current | Include local time **and** relative age: "às 21:34 (há 2min)". Use `datetime.now().astimezone()` — never naive `datetime.now()` or UTC-without-offset. A message that says "20:34" when the phone shows 21:34 is worse than no timestamp. |
| Alerting the person who died | They know. It is noise, and on the official API it costs a conversation. | Exclude the subject from their own alert's recipient list where identity mapping allows |
| No resurrection / all-clear message | The party is left in suspense; the alert has no closing bracket and the thread reads as an unresolved emergency | Send an all-clear on resurrection (already a requirement — good). Also close the loop on "left party" if they rejoin. |
| Silent blind mode | The user believes they are covered while coverage is zero — the core betrayal of a monitoring tool | Loud local indication (overlay turns amber + duration counter). On exit from a long blind period, state "estive cego por Xmin, posso ter perdido eventos." |
| No way to pause | User goes to town / does a solo quest / alt-tabs to browse, and the tool spams the party | A pause hotkey and a visible paused state. Paused must look obviously different from running. |
| Requiring a code edit to change the roster or thresholds | Non-developer user cannot adapt the tool; every party change becomes a support request | Plain JSON config beside the executable, plus a `--calibrate` mode that shows what it is looking at |
| Alert text in English when the party speaks Portuguese | Friction; reduced comprehension under time pressure | Message templates in pt-BR, matching PROJECT.md's language |

---

## "Looks Done But Isn't" Checklist

- [ ] **WhatsApp alerting:** Often missing the 24-hour-window handling — verify a real alert lands on a phone that has **not** messaged the Chatwoot number in over 24 hours. Testing with a number you just chatted with produces a false pass.
- [ ] **WhatsApp alerting:** Often missing delivery confirmation — verify that a `200 OK` from Chatwoot actually corresponded to a phone that buzzed. Check at least once manually before trusting the status code.
- [ ] **Death detection:** Often missing the out-of-range / zoning / disconnect states — verify against captured screenshots of all 8 member states, not just alive and dead.
- [ ] **Death detection:** Often missing the black-frame guard — verify that a fully black or corrupt frame produces `CAPTURE_FAILED`, **not** a four-person wipe alert.
- [ ] **Capture:** Often missing DPI awareness — verify the crop is correct at 100%, 125%, and 150% Windows scaling, and after the game window is dragged to a different position.
- [ ] **Capture:** Often missing `None`-frame handling — verify the tool survives 60 seconds of a completely static screen without entering blind mode or crashing.
- [ ] **Capture:** Often missing stale-frame detection — verify that a frozen game (or a paused capture source) is reported as frozen, not as healthy.
- [ ] **Blind mode:** Often missing re-baselining on exit — verify that a zone change / loading screen produces **zero** alerts on the way in and on the way out.
- [ ] **Alerting:** Often missing wipe aggregation — verify that 4 simultaneous deaths produce **one** message, not four.
- [ ] **Alerting:** Often missing the death latch — verify that a member who stays dead for 5 minutes generates exactly one alert, not one per tick.
- [ ] **Alerting:** Often missing cold-start suppression — verify that starting the scanner while someone is already dead does not fire an alert.
- [ ] **Alerting:** Often missing intentional-shutdown handling — verify that closing the game does not produce four "left the party" alerts.
- [ ] **Liveness:** Often missing entirely — verify the user can tell the tool is alive **without** alt-tabbing, and that a `kill -9` of the process is noticeable within a minute.
- [ ] **Resilience:** Often missing the top-level exception guard — verify that an induced exception in the OCR path does not kill the capture loop.
- [ ] **Resilience:** Often missing power management — verify the display does not sleep during a long AFK session and kill capture.
- [ ] **Config:** Often missing externalization — verify that changing a color threshold or the roster requires zero code edits.
- [ ] **Logging:** Often missing structured event history — verify there is a rotating log with enough detail to answer "why didn't it alert at 21:34?" the next day.
- [ ] **Safety invariant:** Often missing enforcement — verify by inspection that nothing in the codebase touches the game process (no injection, memory reads, input synthesis, or packet capture).

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Out-of-range indistinguishable from death (discovered late) | **HIGH** | Requires a second corroborating signal (chat-line OCR, resurrect indicator, or range-state tracking) grafted onto a detection layer not designed for it. May force a redesign of the state machine. **Prevention via a Phase 0 spike is ~1 day; recovery is ~1 week.** |
| Official WhatsApp API blocks free-form alerts (discovered late) | **HIGH** | Register and get approval for a UTILITY template (days of latency, outside your control), rewrite the transport layer for `template_params`, drop the group requirement, re-scope to N 1:1 sends. Or switch channel entirely (Telegram/ntfy) — which is cheap in code but re-opens a settled product decision. |
| Group messaging not possible on official API | MEDIUM | Re-scope to individual sends; collect per-member numbers; increase per-alert cost N-fold. Or move the group notification to a channel that supports groups (Telegram) and keep WhatsApp for 1:1. |
| Alert storm during a wipe | LOW-MEDIUM | Retrofit an aggregation buffer between detection and transport. Cheap **if** the detection→transport seam exists; expensive if `send_alert()` is called inline from detection. Build the seam up front. |
| Wrong crop coordinates from DPI scaling | LOW | Add DPI awareness call, re-derive regions from the window rect, recalibrate. But **all previously tuned thresholds are invalid** and must be redone. |
| Color thresholds broken by a game patch | LOW | Recapture reference screenshots, retune, update config. Trivial **if** thresholds live in config; a code change and redeploy if they are literals. |
| OCR misreads causing phantom join/leave events | LOW | Switch identity key from OCR string to row index; add roster fuzzy-matching. Cheap if state was never keyed by name; a data-model migration if it was. |
| Silent scanner death in production | LOW (to fix) / **HIGH** (in trust) | Adding liveness signalling is a day of work. Rebuilding the party's trust after the tool failed them silently during a real wipe is the actual cost, and it is not recoverable by code. |
| Anti-cheat objects to the capture method | MEDIUM | Swap the capture backend behind the interface (Desktop Duplication ↔ Windows.Graphics.Capture ↔ window-targeted capture). Cheap **if** capture is behind an interface; a rewrite if `dxcam` calls are scattered through the codebase. |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 2. WhatsApp 24h window blocks alerts | **Phase 0 — Integration spike (hard gate)** | A real alert lands on a phone silent for >24h. Provider type documented in the decision log. |
| 1. Out-of-range == death | **Phase 0/1 — UI state characterization (hard gate)** | An 8-state labeled screenshot corpus exists with pixel measurements; out-of-range vs. dead is provably separable, or a second signal is designed in. |
| 10. ToS / ban risk | Phase 0 — architectural constraint recorded | Code inspection confirms no injection, memory read, input synthesis, or packet capture. Extended capture session runs without client complaint. |
| 4. DPI / multi-monitor coordinates | Phase 1 — Capture foundation | `--calibrate` visual dump shows correct regions at 100/125/150% scaling and after moving the window. Zero literal screen coordinates in source. |
| 5. Black / stale / `None` frames | Phase 1 — Capture foundation | Three-state model (`CAPTURE_FAILED` / `NO_UI` / `UI_PRESENT`) implemented. Black frame → `CAPTURE_FAILED`, never a wipe alert. 60s static screen survived. |
| 3. Silent death of the scanner | Phase 1 (crash-proof loop, rotating log) + Phase 2 (liveness overlay, start/stop handshake) | Kill the process; the user notices within 60s without alt-tabbing. Induced OCR exception does not stop capture. |
| 6. Color-threshold brittleness | Phase 2 — Detection logic | HSV hue-based fill-fraction measurement; thresholds in config; startup sanity check refuses to run if all members read 0%. Validated across gamma settings. |
| 9. Blind mode too coarse / too aggressive | Phase 2 — Detection logic | Landmark template match gates detection. Zone change produces zero alerts entering and exiting. Blind duration surfaced to the user. |
| 8. OCR unreliability | Phase 2 (row-index identity) + Phase 4 (OCR labeling) | Member state keyed by row index; tool fully functional with Tesseract absent. OCR results fuzzy-matched against a configured roster. |
| 7. Alert storms / duplicates / flapping | **Phase 3 — Alerting layer (separate module)** | 4 simultaneous deaths → 1 message. 5-minute death → 1 alert. Cold start with a corpse → 0 alerts. Game close → 0 departure alerts. |
| Performance contention with the game | Phase 3 | Sub-region capture only; HTTP off the detection thread; measured game FPS impact under 2%. |
| Secrets / PII leakage | Phase 1 | `.gitignore` covers the local config before the first commit; `config.example.json` ships with placeholders. |

**Suggested phase ordering consequence:** Phase 0 must be a **de-risking spike with two hard gates** (WhatsApp provider + UI state corpus), not a setup phase. Both gates can invalidate the product's core design, and both are cheap to test and expensive to discover late. Do not let roadmap momentum push either into a later phase.

---

## Open Questions Requiring Empirical Resolution

These could not be resolved from documentation and **must** be answered by testing on the user's actual machine and client:

1. **How does XM Essence render a party member who is out of range / zoning / link-dead?** (Blocks all detection design. LOW confidence from research — no authoritative source found.)
2. **Which WhatsApp provider backs the user's Chatwoot inbox — official Cloud API / Twilio / 360dialog, or an unofficial bridge?** (Determines whether templates are mandatory and whether group sends are possible.)
3. **Does the HP bar hue shift with HP level in this client's UI?** (Determines whether hue thresholding is sound.)
4. **Does the XM Essence client ship GameGuard/Frost, and does it interact with Desktop Duplication capture?** (Confirms the capture backend choice.)
5. **Does a party-member death produce a system-chat line?** (PROJECT.md flags this as unconfirmed. If yes, chat OCR becomes the ideal corroborating signal for pitfall 1 — this materially changes the design.)
6. **Are the party members willing to receive 1:1 WhatsApp messages, and is there a group at all?** (If the official API path is forced, the group requirement dies.)

---

## Sources

**Verified against primary documentation (MEDIUM-HIGH confidence):**
- [Meta — WhatsApp Cloud API, Send Messages guide](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages) — 24-hour customer service window rules, template requirement outside the window. **Directly fetched and quoted.**
- [Chatwoot Developer Docs — Create New Message](https://developers.chatwoot.com/api-reference/messages/create-new-message) — endpoint fields, `template_params` structure, auth, absence of documented rate limits. **Directly fetched.**
- [Meta for Developers — WhatsApp Groups API](https://developers.facebook.com/documentation/business-messaging/whatsapp/groups) — group messaging constraints
- [WhatsApp Business Messaging Policy](https://business.whatsapp.com/policy)
- [Microsoft Learn — SetProcessDpiAwareness](https://learn.microsoft.com/en-us/windows/win32/api/shellscalingapi/nf-shellscalingapi-setprocessdpiawareness) — DPI awareness must be set before coordinate APIs
- [Microsoft Learn — Screen capture (Windows.Graphics.Capture)](https://learn.microsoft.com/en-us/windows/uwp/audio-video-camera/screen-capture)
- [Microsoft Learn — Capturing a Window](https://learn.microsoft.com/en-us/answers/questions/801244/capturing-a-window) — BitBlt/PrintWindow/`PW_RENDERFULLCONTENT` behavior
- [Lineage 2 User and License Agreement (4game, v10 Apr 2026)](https://eu.4game.com/legal/lineage2/21/) — third-party software and anti-circumvention clauses

**Community / issue-tracker evidence (MEDIUM confidence):**
- [DXcam issue #104 — grab() returns None on consecutive calls](https://github.com/ra1nty/DXcam/issues/104)
- [DXcam issue #31 — importing OpenCV makes screenshots black](https://github.com/ra1nty/DXcam/issues/31)
- [DXcam README](https://github.com/ra1nty/DXcam) — Desktop Duplication behavior, per-output cameras, `new_frame_only`
- [chatwoot/chatwoot#13851 — WhatsApp templates with header named params fail (#132000)](https://github.com/chatwoot/chatwoot/issues/13851)
- [chatwoot discussion #7891 — sending templated WhatsApp messages via API](https://github.com/orgs/chatwoot/discussions/7891)
- [stb-tester — Improving OCR accuracy](https://stb-tester.com/blog/2014/04/14/improving-ocr-accuracy) — upscale-before-threshold, 8.3% → 1.2% error reduction
- [tesseract-ocr issue #161 — small font issue](https://github.com/tesseract-ocr/tesseract/issues/161)
- [OBS Forums — OBS GameGuard/HackShield problem](https://obsproject.com/forum/threads/obs-gameguard-hackshield-problem.22370/) — anti-cheat blocks injecting Game Capture, not Display Capture
- [PyAutoGUI coordinates on DPI-scaled multi-monitor setups](https://screencoordinates.com/pyautogui-screen-coordinates/)
- [Alert flapping: causes, detection, and fixes](https://web-alert.io/blog/alert-flapping-detection-taming-unstable-alerts) — hysteresis, consecutive-failure requirement
- [Heartbeat monitoring / dead man's switch](https://drumbeats.io/heartbeat-monitoring) — absence-of-signal alerting
- [Evolution API (unofficial WhatsApp bridge)](https://github.com/evolution-foundation/evolution-api)

**Unresolved (LOW confidence — no authoritative source found):**
- Lineage 2 / XM Essence party window rendering for out-of-range, zoning, and link-dead members — **must be verified empirically**
- Whether L2 anti-cheat interacts with Desktop Duplication capture specifically

---
*Pitfalls research for: passive screen-scanning game monitor with WhatsApp alerting*
*Researched: 2026-08-24*
